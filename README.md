# RuleMemory — a Qwen-powered MemoryAgent

> **Global AI Hackathon Series with Qwen Cloud · Track: MemoryAgent**

RuleMemory is a real, runnable memory agent. It reads free-form notes
(contest rules, deadlines, working assumptions), uses **Qwen** to extract
atomic typed facts, stores them in a **typed, provenance-tracked,
semantically-recallable** memory that **persists across sessions**, and then
answers questions grounded strictly on what it remembers — flagging stale
assumptions and superseding facts that conflict with newer information.

It is not a cached trace. The reasoning path runs **real Qwen inference**: a
local `Qwen2.5-VL-7B-Instruct` (text chat, via transformers) by default, or the
**Qwen Cloud MaaS** OpenAI-compatible endpoint when an API key is present —
behind a single interface.

---

## What makes it a real MemoryAgent

| Capability | Where | How it's real |
|---|---|---|
| **Qwen fact extraction** | `reasoner.py` | Real local Qwen2.5-VL-7B inference (or Qwen Cloud); robust JSON parsing |
| **Typed memory** | `memory.py` | `rule` / `deadline` / `assumption` / `fact` entries |
| **Provenance** | `memory.py` | Every entry stores `source_id` + char-span + verbatim quote |
| **Semantic recall** | `embedder.py` | Real embeddings (sentence-transformers) or deterministic hashing-TF-IDF fallback; cosine ranking |
| **Cross-session persistence** | `memory.py` | JSONL store; restart reloads every entry, status, provenance |
| **Conflict / supersede** | `agent.py` | New fact conflicting with an older one (same topic *or* semantically close) supersedes it — append-only, old entry kept and marked |
| **Temporal reasoning** | `memory.py` | `due_within(hours)`, `stale_now()`, deadline-passed detection, TTL |
| **Replayable transcript** | `agent.py` | Every step (`ingest_start → facts_extracted → … → answer`) recorded to JSONL |
| **Web UI** | `webapp/` | FastAPI + vanilla JS; ingest, ask, memory table, recall hits, transcript |

---

## Architecture

```
                       ┌─────────────────────────────────────────┐
  free-form notes ───► │  RuleMemoryAgent.ingest()               │
  (rules/deadlines)    │    1. Qwen extract_facts() ── typed +    │
                       │       provenance spans                   │
                       │    2. store in Memory (JSONL, persistent)│
                       │    3. conflict_candidates() → Qwen        │
                       │       detect_conflicts() → supersede      │
                       │    4. flag stale / passed deadlines       │
                       └───────────────┬──────────────────────────┘
                                       │  (every step → transcript.jsonl)
   question ──────────────────────────▼──────────────────────────
                       ┌─────────────────────────────────────────┐
                       │  RuleMemoryAgent.answer()               │
                       │    1. Memory.recall() — embed query,     │
                       │       cosine over entry embeddings        │
                       │    2. Qwen answer() grounded on hits,     │
                       │       warns on stale/superseded, cites    │
                       │       [#n] → source char-span             │
                       └──────────────────────────────────────────┘

  Reasoner backends (one interface):
    QwenCloudReasoner  ──  Qwen Cloud MaaS / DashScope (OpenAI-compatible)   [production]
    QwenLocalReasoner  ──  Qwen2.5-VL-7B-Instruct via transformers (text)    [default here]
    RuleBasedReasoner  ──  deterministic, model-free                          [CI / fallback]
```

`make_reasoner()` picks **Cloud** if `QWEN_API_KEY`/`DASHSCOPE_API_KEY` is set,
else **Local** if a CUDA GPU + transformers are available, else the
**rule-based** fallback. The agent, memory, UI and demo are identical across
backends — only the reasoner swaps.

---

## Quickstart

### 1. Multi-session demo with REAL local Qwen

Requires a GPU + transformers (the `dacon_vlm` conda env here has torch 2.8+cu128,
transformers 5.10, 2× RTX 5090):

```bash
RULEMEMORY_FORCE_HASH_EMBED=1 \
  /home/user/miniconda3/envs/dacon_vlm/bin/python eval/demo.py --backend local
```

This runs the full scenario: session 1 ingests contest rules (incl. a stale
"use Python 2" assumption + a deadline), the process exits, then session 2
reloads memory from disk, ingests a correction, supersedes/flags the stale
assumption, and answers deadline / version / membership questions — all with
real Qwen. The verbatim output of one such run is committed at
[`eval/SAMPLE_RUN_qwen_local.txt`](eval/SAMPLE_RUN_qwen_local.txt).

### 2. GPU-free demo (rule-based fallback)

```bash
RULEMEMORY_FORCE_HASH_EMBED=1 python eval/demo.py --backend rule-based
```

### 3. Qwen Cloud MaaS (production path)

```bash
export QWEN_API_KEY="sk-..."                 # or DASHSCOPE_API_KEY
export QWEN_MODEL="qwen-plus"                 # optional
# export QWEN_OPENAI_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
python eval/demo.py --backend cloud
```

### 4. Web UI

```bash
# GPU-free demo:
RULEMEMORY_BACKEND=rule-based RULEMEMORY_FORCE_HASH_EMBED=1 \
  python webapp/server.py
# or real local Qwen:
RULEMEMORY_BACKEND=local \
  /home/user/miniconda3/envs/dacon_vlm/bin/python webapp/server.py
```

Open <http://127.0.0.1:8000>. Click **Load session-1 sample → Ingest with
Qwen**, ask "what python version should we use?", then **Load correction sample
→ Ingest** and watch the Python-2 assumption get superseded. The memory table,
recall scores, provenance spans, and transcript update live.

---

## Tests

GPU/credential-free (uses the rule-based reasoner + hashing embedder):

```bash
RULEMEMORY_FORCE_FALLBACK=1 RULEMEMORY_FORCE_HASH_EMBED=1 python -m pytest tests/ -q
# 11 passed, 1 skipped (GPU test)
```

Real Qwen GPU smoke test (opt-in):

```bash
RULEMEMORY_RUN_GPU=1 /home/user/miniconda3/envs/dacon_vlm/bin/python \
  -m pytest tests/test_local_qwen_gpu.py -v -s
```

---

## Verified run (real Qwen2.5-VL-7B-Instruct, text mode)

From [`eval/SAMPLE_RUN_qwen_local.txt`](eval/SAMPLE_RUN_qwen_local.txt) —
Qwen extracted these from session 1's rules:

```
  - (  deadline) The final submission deadline is 2026-07-10T23:59:00+00:00 on Devpost.  due=2026-07-10T23:59:00Z
  - (      rule) Teams may have at most 4 members.
  - (      rule) Teams must register before kickoff.
  - (      rule) Submissions must use a Qwen model via Qwen Cloud MaaS.
  - (assumption) We should still use Python 2 for the build scripts ...  [STALE]
  - (      fact) The grand prize is 10000 USD.
```

After restart + correction, grounded answers (real Qwen):

```
Q: What Python version should we use for the build scripts?
  A: The toolchain now requires Python 3.11.
  ! warning: The assumption in fact #1 is marked as STALE.

Q: How many members can a team have, and which model must we use?
  A: A team can have at most 4 members, and submissions must use a Qwen model via Qwen Cloud MaaS.
```

---

## Honest framing

- The live reasoning path is **real Qwen** — no fabricated/cached LLM text.
- **Default backend here is local `Qwen2.5-VL-7B-Instruct`** (text chat) because
  no Qwen Cloud API key is provisioned in this environment. `QwenCloudReasoner`
  is fully implemented (real HTTP to the DashScope OpenAI-compatible endpoint);
  setting `QWEN_API_KEY` swaps the production Qwen Cloud MaaS path in with **zero
  other changes** — same agent, memory, UI, and demo.
- The semantic embedder prefers `sentence-transformers`; if unavailable it falls
  back to a **deterministic hashing-TF-IDF** vectorizer so recall is still real
  (cosine over hashed n-grams), and CI stays dependency-light.
- The rule-based reasoner is a transparent heuristic for credential/GPU-free CI;
  it is never used when a Qwen backend is available.

## Layout

```
src/rulememory_qwen/
  reasoner.py   # Qwen Local / Qwen Cloud / rule-based behind one interface
  memory.py     # typed entries, provenance, TTL, supersede, semantic recall, persistence
  embedder.py   # sentence-transformers or deterministic hashing-TFIDF
  agent.py      # ingest→extract→store→conflict→answer loop + transcript
webapp/         # FastAPI server + vanilla-JS UI
eval/           # multi-session demo + scenario + committed real-Qwen sample run
tests/          # GPU-free pytest suite + opt-in GPU smoke test
```

License: MIT.
