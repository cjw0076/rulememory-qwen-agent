"""The RuleMemory agent loop.

``ingest(text)``  -> Qwen extracts facts -> store each with provenance ->
                     detect conflicts on shared topics (supersede the older) ->
                     flag stale assumptions / passed deadlines.
``answer(q)``     -> semantic recall over memory -> Qwen answers grounded on the
                     recalled facts, surfacing stale/superseded warnings.

Every step is appended to a replayable transcript (``agent.transcript``), and
optionally mirrored to a JSONL file for cross-session audit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory import Memory, MemoryEntry, SourceRef
from .reasoner import Reasoner, make_reasoner


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RuleMemoryAgent:
    def __init__(
        self,
        reasoner: Optional[Reasoner] = None,
        memory: Optional[Memory] = None,
        transcript_path: Optional[str] = None,
        default_stale_after_hours: Optional[float] = None,
    ) -> None:
        self.reasoner = reasoner if reasoner is not None else make_reasoner()
        self.memory = memory if memory is not None else Memory()
        self.transcript: List[Dict[str, Any]] = []
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.default_stale_after_hours = default_stale_after_hours

    # -- transcript --------------------------------------------------------- #

    def _record(self, step: str, **payload: Any) -> Dict[str, Any]:
        event = {"ts": _now_iso(), "step": step, "reasoner": self.reasoner.name, **payload}
        self.transcript.append(event)
        if self.transcript_path:
            self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
            with self.transcript_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    # -- ingest ------------------------------------------------------------- #

    def ingest(self, text: str, source_id: str, session_id: str = "default") -> Dict[str, Any]:
        self._record("ingest_start", source_id=source_id, session_id=session_id, chars=len(text))
        facts = self.reasoner.extract_facts(text)
        self._record("facts_extracted", source_id=source_id, count=len(facts), facts=facts)

        added: List[MemoryEntry] = []
        conflicts: List[Dict[str, Any]] = []
        for f in facts:
            cs = int(f.get("char_start", 0) or 0)
            ce = int(f.get("char_end", 0) or 0)
            ce = max(ce, cs)
            quote = text[cs:ce][:240]
            entry = self.memory.add(
                type=f["type"],
                topic=f["topic"],
                statement=f["statement"],
                source=SourceRef(source_id=source_id, char_start=cs, char_end=ce, quote=quote),
                session_id=session_id,
                due_at=f.get("due_at"),
                stale_after_hours=self.default_stale_after_hours,
                stale_flag=bool(f.get("stale", False)),
                confidence=float(f.get("confidence", 0.8)),
            )
            added.append(entry)

            # conflict / supersede against prior facts on the same topic OR that
            # are semantically close (handles topic-slug drift between sessions).
            for prior in self.memory.conflict_candidates(entry):
                if prior.entry_id == entry.entry_id or prior.status != "active":
                    continue
                verdict = self.reasoner.detect_conflicts(prior.for_reasoner(), entry.for_reasoner())
                if verdict.get("conflict"):
                    self.memory.supersede(prior, entry)
                    conflicts.append(
                        {
                            "superseded": prior.entry_id,
                            "superseded_statement": prior.statement,
                            "by": entry.entry_id,
                            "by_statement": entry.statement,
                            "topic": entry.topic,
                            "reason": verdict.get("reason", ""),
                        }
                    )

        stale = [
            {"entry_id": e.entry_id, "statement": e.statement, "reason": e.stale_reason()}
            for e in self.memory.stale_now()
        ]
        result = {
            "source_id": source_id,
            "added": [e.entry_id for e in added],
            "added_count": len(added),
            "conflicts": conflicts,
            "stale": stale,
            "facts": facts,
        }
        self._record("ingest_done", **{k: v for k, v in result.items() if k != "facts"})
        return result

    # -- answer ------------------------------------------------------------- #

    def answer(self, question: str, k: int = 5) -> Dict[str, Any]:
        self._record("question", question=question)
        hits = self.memory.recall(question, k=k, active_only=True)
        recalled = [
            {
                "entry_id": h["entry"].entry_id,
                "score": round(h["score"], 4),
                "type": h["entry"].type,
                "statement": h["entry"].statement,
                "stale": h["entry"].is_stale(),
                "due_at": h["entry"].due_at,
            }
            for h in hits
        ]
        self._record("recall", question=question, hits=recalled)

        facts = [h["entry"].for_reasoner() for h in hits]
        ans = self.reasoner.answer(question, facts)

        # attach provenance for the cited facts
        citations = []
        for n in ans.get("used_facts", []) or []:
            if isinstance(n, int) and 1 <= n <= len(hits):
                e = hits[n - 1]["entry"]
                citations.append(
                    {
                        "n": n,
                        "entry_id": e.entry_id,
                        "source_id": e.source.source_id,
                        "char_span": [e.source.char_start, e.source.char_end],
                        "quote": e.source.quote,
                    }
                )
        result = {
            "question": question,
            "answer": ans.get("answer", ""),
            "warnings": ans.get("warnings", []),
            "recalled": recalled,
            "citations": citations,
        }
        self._record("answer", **result)
        return result

    # -- temporal helpers --------------------------------------------------- #

    def due_within(self, hours: float) -> List[Dict[str, Any]]:
        return [
            {"entry_id": e.entry_id, "statement": e.statement, "due_at": e.due_at,
             "hours_until_due": round(e.hours_until_due() or 0, 2)}
            for e in self.memory.due_within(hours)
        ]

    def stale_report(self) -> List[Dict[str, Any]]:
        return [
            {"entry_id": e.entry_id, "type": e.type, "statement": e.statement,
             "reason": e.stale_reason()}
            for e in self.memory.stale_now()
        ]

    def memory_table(self) -> List[Dict[str, Any]]:
        rows = []
        for e in self.memory.entries:
            rows.append(
                {
                    "entry_id": e.entry_id,
                    "type": e.type,
                    "topic": e.topic,
                    "statement": e.statement,
                    "status": e.status,
                    "stale": e.is_stale(),
                    "stale_reason": e.stale_reason(),
                    "due_at": e.due_at,
                    "session_id": e.session_id,
                    "created_at": e.created_at,
                    "superseded_by": e.superseded_by,
                    "source": e.source.to_dict(),
                    "confidence": e.confidence,
                }
            )
        return rows
