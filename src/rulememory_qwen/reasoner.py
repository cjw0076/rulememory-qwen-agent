"""Qwen reasoners behind one interface.

Three backends, one ``Reasoner`` contract:

* ``QwenLocalReasoner`` — loads ``Qwen/Qwen2.5-VL-7B-Instruct`` (text chat) via
  transformers and runs **real** local inference. Model is loaded once.
* ``QwenCloudReasoner`` — calls the Qwen Cloud MaaS / DashScope
  OpenAI-compatible chat endpoint over HTTP. This is the production path.
* ``RuleBasedReasoner`` — a tiny deterministic heuristic backend with no model
  dependency, used for credential/GPU-free CI tests and as a last-resort
  fallback.

``make_reasoner()`` selects Cloud if an API key is present, else Local if a
GPU + transformers stack is available, else the rule-based fallback.

Every backend implements:

    extract_facts(text)            -> list[dict]   (structured facts)
    answer(question, context)      -> dict         (grounded answer)
    detect_conflicts(a, b)         -> dict         (do two facts conflict?)
    summarize(facts)               -> str

The extraction contract returns facts shaped like::

    {"type": "rule|deadline|assumption|fact",
     "topic": "<short topic slug>",
     "statement": "<one-sentence normalized statement>",
     "char_start": <int>, "char_end": <int>,   # provenance span in source text
     "due_at": "<ISO8601 or null>",             # for deadlines
     "stale": <bool>, "confidence": <float>}
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

EXTRACT_SYSTEM = """You are RuleMemory, a precise fact-extraction engine for a memory agent.
Given a block of free-form notes (contest rules, deadlines, assumptions), extract every
atomic, self-contained fact. Output ONLY a JSON array, no prose, no markdown fences.

Each element MUST be an object with these keys:
- "type": one of "rule", "deadline", "assumption", "fact".
    * "deadline"  : anything with a date/time the team must hit.
    * "assumption": a belief that could become wrong/stale (e.g. tooling/version guesses).
    * "rule"      : a binding constraint/requirement.
    * "fact"      : any other durable fact.
- "topic": a short lowercase slug naming the subject (e.g. "submission_deadline",
    "python_version", "team_size", "track"). Facts about the SAME subject MUST share a topic.
- "statement": one normalized declarative sentence capturing the fact.
- "due_at": ISO-8601 timestamp if this is a dated deadline, else null.
- "stale": true if the statement reads like an outdated/likely-wrong assumption
    (e.g. "we should still use Python 2"), else false.
- "confidence": float 0..1, your confidence this is a real, useful fact.

Be exhaustive but do not invent facts. Return [] if there are none."""

ANSWER_SYSTEM = """You are RuleMemory, a memory agent that answers ONLY from the supplied memory facts.
Rules:
- Use ONLY the numbered MEMORY facts as ground truth. Do not use outside knowledge.
- If a relevant fact is flagged STALE or SUPERSEDED, warn the user explicitly and prefer the active fact.
- If the memory does not contain the answer, say so plainly.
- Be concise. Cite the fact numbers you used like [#2].
Return ONLY a JSON object: {"answer": "<text with [#n] citations>", "used_facts": [<ints>], "warnings": ["<text>", ...]}"""

CONFLICT_SYSTEM = """You decide whether two memory facts about the same topic CONFLICT (cannot both be currently true).
Return ONLY a JSON object: {"conflict": true|false, "reason": "<short>"}.
Two facts conflict when one supersedes/contradicts the other (e.g. a version change, a moved deadline,
a reversed rule). Facts that simply add detail do NOT conflict."""


_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str, want_array: bool) -> Any:
    """Robustly pull the first JSON array/object out of an LLM reply."""
    text = text.strip()
    # strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    # direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    pat = _JSON_ARRAY_RE if want_array else _JSON_OBJ_RE
    m = pat.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return [] if want_array else {}


def _normalize_facts(raw: Any, source_text: str) -> List[Dict[str, Any]]:
    """Coerce model output into the fact contract and repair provenance spans."""
    if isinstance(raw, dict):
        raw = raw.get("facts") or raw.get("entries") or [raw]
    if not isinstance(raw, list):
        return []
    valid_types = {"rule", "deadline", "assumption", "fact"}
    out: List[Dict[str, Any]] = []
    low_src = source_text.lower()
    for item in raw:
        if not isinstance(item, dict):
            continue
        stmt = str(item.get("statement", "")).strip()
        if not stmt:
            continue
        ftype = str(item.get("type", "fact")).lower().strip()
        if ftype not in valid_types:
            ftype = "fact"
        topic = str(item.get("topic", "")).strip().lower().replace(" ", "_") or "general"
        # Repair / locate provenance span against the real source text.
        cs = item.get("char_start")
        ce = item.get("char_end")
        if not (isinstance(cs, int) and isinstance(ce, int) and 0 <= cs < ce <= len(source_text)):
            cs, ce = _locate_span(stmt, source_text, low_src)
        out.append(
            {
                "type": ftype,
                "topic": topic,
                "statement": stmt,
                "due_at": item.get("due_at") or None,
                "stale": bool(item.get("stale", False)),
                "confidence": float(item.get("confidence", 0.8) or 0.8),
                "char_start": cs,
                "char_end": ce,
            }
        )
    return out


def _locate_span(statement: str, source_text: str, low_src: str) -> tuple[int, int]:
    """Best-effort char span of a fact inside the source (for provenance)."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", statement.lower()) if len(w) > 3]
    best_pos, best_len = -1, 0
    # try contiguous trigrams of distinctive words
    for w in words:
        pos = low_src.find(w)
        if pos >= 0:
            if best_pos < 0:
                best_pos = pos
            best_len = max(best_len, pos + len(w) - best_pos)
    if best_pos >= 0:
        return best_pos, min(len(source_text), best_pos + max(best_len, len(words and words[0] or "")))
    return 0, min(len(source_text), len(statement))


# --------------------------------------------------------------------------- #
# Base interface
# --------------------------------------------------------------------------- #

class Reasoner:
    """Abstract reasoner interface. Subclasses implement ``_chat``."""

    name = "base"

    def _chat(self, system: str, user: str, max_new_tokens: int = 768) -> str:
        raise NotImplementedError

    # -- public contract ---------------------------------------------------- #

    def extract_facts(self, text: str) -> List[Dict[str, Any]]:
        reply = self._chat(EXTRACT_SYSTEM, text, max_new_tokens=900)
        return _normalize_facts(_extract_json(reply, want_array=True), text)

    def answer(self, question: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = []
        for i, f in enumerate(facts, 1):
            tags = []
            if f.get("status") == "superseded":
                tags.append("SUPERSEDED")
            if f.get("stale"):
                tags.append("STALE")
            tag = (" [" + ",".join(tags) + "]") if tags else ""
            due = f" (due {f['due_at']})" if f.get("due_at") else ""
            lines.append(f"#{i} ({f.get('type','fact')}){tag} {f['statement']}{due}")
        ctx = "\n".join(lines) if lines else "(memory is empty)"
        user = f"MEMORY:\n{ctx}\n\nQUESTION: {question}"
        reply = self._chat(ANSWER_SYSTEM, user, max_new_tokens=400)
        obj = _extract_json(reply, want_array=False)
        if not isinstance(obj, dict) or "answer" not in obj:
            obj = {"answer": reply.strip(), "used_facts": [], "warnings": []}
        obj.setdefault("used_facts", [])
        obj.setdefault("warnings", [])
        return obj

    def detect_conflicts(self, fact_a: Dict[str, Any], fact_b: Dict[str, Any]) -> Dict[str, Any]:
        user = (
            f"Topic: {fact_a.get('topic')}\n"
            f"Fact A: {fact_a['statement']}\n"
            f"Fact B: {fact_b['statement']}"
        )
        reply = self._chat(CONFLICT_SYSTEM, user, max_new_tokens=120)
        obj = _extract_json(reply, want_array=False)
        if not isinstance(obj, dict) or "conflict" not in obj:
            return {"conflict": False, "reason": "unparseable"}
        return {"conflict": bool(obj["conflict"]), "reason": str(obj.get("reason", ""))}

    def summarize(self, facts: List[Dict[str, Any]]) -> str:
        if not facts:
            return "Memory is empty."
        lines = [f"- ({f.get('type','fact')}) {f['statement']}" for f in facts[:40]]
        user = "Summarize the current state of this memory in 2-4 sentences:\n" + "\n".join(lines)
        return self._chat(
            "You are RuleMemory. Summarize the memory faithfully and concisely.",
            user,
            max_new_tokens=220,
        ).strip()


# --------------------------------------------------------------------------- #
# Local Qwen via transformers
# --------------------------------------------------------------------------- #

class QwenLocalReasoner(Reasoner):
    """Real local Qwen inference via transformers (text chat).

    Uses Qwen2.5-VL-7B-Instruct in text-only mode. The model is loaded once on
    first use and reused. Generation is greedy/low-temp for determinism.
    """

    name = "qwen-local"

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        max_memory_gib: str = "16,16",
        temperature: float = 0.0,
        dtype: str = "bfloat16",
    ) -> None:
        self.model_id = model_id
        self.max_memory_gib = max_memory_gib
        self.temperature = temperature
        self.dtype = dtype
        self._model = None
        self._processor = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch  # noqa
        from transformers import AutoProcessor

        caps = {i: f"{c.strip()}GiB" for i, c in enumerate(self.max_memory_gib.split(","))}
        caps["cpu"] = "0GiB"
        torch_dtype = getattr(__import__("torch"), self.dtype)

        # Qwen2.5-VL exposes a conditional-generation class; we drive it text-only.
        try:
            from transformers import Qwen2_5_VLForConditionalGeneration as _Model
        except Exception:  # pragma: no cover - version drift
            from transformers import AutoModelForVision2Seq as _Model

        self._model = _Model.from_pretrained(
            self.model_id,
            dtype=torch_dtype,
            device_map="auto",
            max_memory=caps,
        ).eval()
        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._tokenizer = self._processor.tokenizer

    def _chat(self, system: str, user: str, max_new_tokens: int = 768) -> str:
        import torch

        self._ensure_loaded()
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system}]},
            {"role": "user", "content": [{"type": "text", "text": user}]},
        ]
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(text=[text], return_tensors="pt").to(self._model.device)
        do_sample = self.temperature > 0
        gen_kwargs = dict(
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            pad_token_id=self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
        )
        if do_sample:
            gen_kwargs["temperature"] = self.temperature
        with torch.inference_mode():
            out = self._model.generate(**inputs, **gen_kwargs)
        gen = out[:, inputs["input_ids"].shape[1]:]
        return self._processor.batch_decode(gen, skip_special_tokens=True)[0]


# --------------------------------------------------------------------------- #
# Qwen Cloud MaaS (DashScope OpenAI-compatible)
# --------------------------------------------------------------------------- #

class QwenCloudReasoner(Reasoner):
    """Production path: Qwen Cloud MaaS via the OpenAI-compatible chat endpoint."""

    name = "qwen-cloud"

    DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-plus",
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("QwenCloudReasoner requires QWEN_API_KEY or DASHSCOPE_API_KEY")
        self.model = os.environ.get("QWEN_MODEL", model)
        self.base_url = (
            base_url
            or os.environ.get("QWEN_OPENAI_BASE_URL")
            or os.environ.get("DASHSCOPE_OPENAI_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def _chat(self, system: str, user: str, max_new_tokens: int = 768) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": max_new_tokens,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"Qwen Cloud HTTP {exc.code}: {detail}") from exc


# --------------------------------------------------------------------------- #
# Rule-based fallback (no model, deterministic, for CI)
# --------------------------------------------------------------------------- #

_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)\b"
)
_STALE_HINTS = re.compile(
    r"\b(python\s*2|deprecated|legacy|old|outdated|no longer|used to|previously|"
    r"we (?:should )?still use)\b",
    re.I,
)


class RuleBasedReasoner(Reasoner):
    """Deterministic, model-free reasoner. Good enough for CI smoke tests."""

    name = "rule-based"

    def extract_facts(self, text: str) -> List[Dict[str, Any]]:
        facts: List[Dict[str, Any]] = []
        for m in re.finditer(r"[^.\n;]+[.\n;]?", text):
            seg = m.group(0).strip()
            if len(seg) < 8:
                continue
            cs, ce = m.start(), m.start() + len(m.group(0).rstrip())
            date_m = _DATE_RE.search(seg)
            stale = bool(_STALE_HINTS.search(seg))
            if date_m:
                ftype, topic, due = "deadline", _topic_of(seg), _iso(date_m.group(1))
            elif stale:
                ftype, topic, due = "assumption", _topic_of(seg), None
            elif re.search(r"\b(must|required|shall|may not|cannot|only|max(?:imum)?|min(?:imum)?)\b", seg, re.I):
                ftype, topic, due = "rule", _topic_of(seg), None
            else:
                ftype, topic, due = "fact", _topic_of(seg), None
            facts.append(
                {
                    "type": ftype,
                    "topic": topic,
                    "statement": seg.rstrip(".;"),
                    "due_at": due,
                    "stale": stale,
                    "confidence": 0.6,
                    "char_start": cs,
                    "char_end": ce,
                }
            )
        return facts

    def answer(self, question: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        q_words = set(re.findall(r"[a-z0-9]+", question.lower()))
        scored = []
        for i, f in enumerate(facts, 1):
            fw = set(re.findall(r"[a-z0-9]+", f["statement"].lower()))
            overlap = len(q_words & fw)
            if overlap:
                scored.append((overlap, i, f))
        scored.sort(reverse=True)
        warnings = []
        used = []
        parts = []
        for _, i, f in scored[:3]:
            used.append(i)
            parts.append(f"{f['statement']} [#{i}]")
            if f.get("stale"):
                warnings.append(f"Fact [#{i}] is flagged STALE: {f['statement']}")
            if f.get("status") == "superseded":
                warnings.append(f"Fact [#{i}] was SUPERSEDED.")
        ans = " ".join(parts) if parts else "I don't have that in memory."
        return {"answer": ans, "used_facts": used, "warnings": warnings}

    def detect_conflicts(self, fact_a: Dict[str, Any], fact_b: Dict[str, Any]) -> Dict[str, Any]:
        # Same topic with a numeric/version/date difference => conflict.
        if fact_a.get("topic") != fact_b.get("topic"):
            return {"conflict": False, "reason": "different topic"}
        na = set(re.findall(r"\d+(?:\.\d+)?", fact_a["statement"]))
        nb = set(re.findall(r"\d+(?:\.\d+)?", fact_b["statement"]))
        if na and nb and na != nb:
            return {"conflict": True, "reason": "same topic, differing numbers/versions"}
        if fact_a["statement"].strip().lower() != fact_b["statement"].strip().lower():
            return {"conflict": True, "reason": "same topic, differing statements"}
        return {"conflict": False, "reason": "identical"}

    def summarize(self, facts: List[Dict[str, Any]]) -> str:
        if not facts:
            return "Memory is empty."
        by_type: Dict[str, int] = {}
        for f in facts:
            by_type[f.get("type", "fact")] = by_type.get(f.get("type", "fact"), 0) + 1
        parts = ", ".join(f"{v} {k}(s)" for k, v in sorted(by_type.items()))
        return f"Memory holds {len(facts)} facts: {parts}."


def _topic_of(seg: str) -> str:
    seg_l = seg.lower()
    # Order matters: most specific subjects first so a sentence is bucketed by
    # its dominant subject rather than an incidental keyword.
    keymap = [
        ("python_version", r"\bpython\b"),
        ("team_size", r"\bteam\b|member|people|register"),
        ("prize", r"prize|reward|\$|usd|dollar"),
        ("deadline", r"deadline|\bdue\b|freeze"),
        ("model", r"qwen|\bmodel\b"),
        ("track", r"\btrack\b"),
        ("eligibility", r"eligib|region|country"),
        ("submission", r"submit|submission"),
    ]
    for topic, pat in keymap:
        if re.search(pat, seg_l):
            return topic
    words = [w for w in re.findall(r"[a-z]+", seg_l) if len(w) > 4]
    return (words[0] if words else "general")


def _iso(s: str) -> str:
    s = s.strip().replace(" ", "T")
    if "T" not in s:
        s += "T00:00:00"
    return s


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def make_reasoner(prefer: Optional[str] = None, **kwargs) -> Reasoner:
    """Pick a reasoner backend.

    Selection order (unless ``prefer`` forces one of
    "cloud"/"local"/"rule-based"):
      1. Qwen Cloud   if QWEN_API_KEY / DASHSCOPE_API_KEY is set.
      2. Qwen Local   if torch + a CUDA GPU + transformers are importable.
      3. Rule-based   otherwise (credential/GPU-free).
    """
    if prefer == "cloud":
        return QwenCloudReasoner(**kwargs)
    if prefer == "local":
        return QwenLocalReasoner(**kwargs)
    if prefer == "rule-based":
        return RuleBasedReasoner()

    if os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"):
        try:
            return QwenCloudReasoner(**kwargs)
        except Exception:
            pass

    if os.environ.get("RULEMEMORY_FORCE_FALLBACK") != "1":
        try:
            import torch  # noqa
            import transformers  # noqa

            if torch.cuda.is_available():
                return QwenLocalReasoner(**{k: v for k, v in kwargs.items()
                                            if k in {"model_id", "max_memory_gib",
                                                     "temperature", "dtype"}})
        except Exception:
            pass

    return RuleBasedReasoner()
