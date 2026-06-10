"""RuleMemory store: typed, provenance-tracked, semantically-recallable memory.

Features
--------
* **Typed entries** — rule / deadline / assumption / fact.
* **Provenance** — every entry records its source id and the character span
  ``(char_start, char_end)`` it was extracted from, plus the verbatim quote.
* **Timestamps + TTL** — ``created_at`` / ``updated_at`` and a per-entry
  ``stale_after_hours``; ``is_stale(now)`` combines TTL expiry, explicit stale
  flags, and passed deadlines.
* **Status lifecycle** — ``active`` / ``superseded``; a newer fact on the same
  topic that conflicts supersedes the older one (append-only: old entries are
  never deleted, only marked superseded with a pointer).
* **Semantic recall** — entries are embedded; ``recall(query, k)`` returns the
  top-k by cosine similarity (real embeddings, see ``embedder.py``).
* **Temporal reasoning** — ``due_within(hours)`` and ``stale_now()``.
* **Cross-session persistence** — JSONL store on disk; reopening the same path
  restores every entry, status, and provenance datum.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .embedder import Embedder, make_embedder, cosine


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


@dataclass
class SourceRef:
    source_id: str
    char_start: int = 0
    char_end: int = 0
    quote: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SourceRef":
        return cls(
            source_id=d.get("source_id", ""),
            char_start=int(d.get("char_start", 0)),
            char_end=int(d.get("char_end", 0)),
            quote=d.get("quote", ""),
        )


@dataclass
class MemoryEntry:
    entry_id: str
    type: str  # rule | deadline | assumption | fact
    topic: str
    statement: str
    source: SourceRef
    session_id: str = "default"
    created_at: str = field(default_factory=lambda: _iso(_now()))
    updated_at: str = field(default_factory=lambda: _iso(_now()))
    due_at: Optional[str] = None
    stale_after_hours: Optional[float] = None
    stale_flag: bool = False  # model/heuristic says this is an outdated assumption
    status: str = "active"  # active | superseded
    superseded_by: Optional[str] = None
    confidence: float = 0.8

    # -- staleness / temporal ---------------------------------------------- #

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        now = now or _now()
        if self.stale_flag:
            return True
        if self.status == "superseded":
            return True
        due = _parse_dt(self.due_at)
        if due is not None and due < now:
            return True
        if self.stale_after_hours is not None:
            created = _parse_dt(self.created_at) or now
            if now > created + timedelta(hours=self.stale_after_hours):
                return True
        return False

    def stale_reason(self, now: Optional[datetime] = None) -> Optional[str]:
        now = now or _now()
        if self.status == "superseded":
            return "superseded by a newer fact"
        if self.stale_flag:
            return "flagged as an outdated assumption"
        due = _parse_dt(self.due_at)
        if due is not None and due < now:
            return f"deadline passed ({self.due_at})"
        if self.stale_after_hours is not None:
            created = _parse_dt(self.created_at) or now
            if now > created + timedelta(hours=self.stale_after_hours):
                return f"TTL of {self.stale_after_hours}h expired"
        return None

    def hours_until_due(self, now: Optional[datetime] = None) -> Optional[float]:
        due = _parse_dt(self.due_at)
        if due is None:
            return None
        now = now or _now()
        return (due - now).total_seconds() / 3600.0

    # -- serialization ------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source"] = self.source.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryEntry":
        src = d.get("source", {})
        return cls(
            entry_id=d["entry_id"],
            type=d.get("type", "fact"),
            topic=d.get("topic", "general"),
            statement=d["statement"],
            source=SourceRef.from_dict(src) if isinstance(src, dict) else SourceRef(""),
            session_id=d.get("session_id", "default"),
            created_at=d.get("created_at", _iso(_now())),
            updated_at=d.get("updated_at", _iso(_now())),
            due_at=d.get("due_at"),
            stale_after_hours=d.get("stale_after_hours"),
            stale_flag=bool(d.get("stale_flag", False)),
            status=d.get("status", "active"),
            superseded_by=d.get("superseded_by"),
            confidence=float(d.get("confidence", 0.8)),
        )

    def for_reasoner(self) -> Dict[str, Any]:
        """Shape used by the reasoner's answer()/conflict APIs."""
        return {
            "type": self.type,
            "topic": self.topic,
            "statement": self.statement,
            "due_at": self.due_at,
            "stale": self.is_stale(),
            "status": self.status,
            "confidence": self.confidence,
        }


class Memory:
    """A persistent, semantically-recallable memory store."""

    def __init__(self, path: Optional[str] = None, embedder: Optional[Embedder] = None) -> None:
        self.path = Path(path) if path else None
        self.embedder = embedder or make_embedder()
        self.entries: List[MemoryEntry] = []
        self._emb: Optional[np.ndarray] = None  # cached embedding matrix
        self._emb_dirty = True
        if self.path and self.path.exists():
            self._load()

    # -- persistence -------------------------------------------------------- #

    def _load(self) -> None:
        self.entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            self.entries.append(MemoryEntry.from_dict(json.loads(line)))
        self._emb_dirty = True

    def _persist(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for e in self.entries:
                fh.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

    # -- embedding index ---------------------------------------------------- #

    def _embed_text(self, e: MemoryEntry) -> str:
        return f"{e.topic}: {e.statement}"

    def _ensure_index(self) -> None:
        if not self._emb_dirty and self._emb is not None and len(self._emb) == len(self.entries):
            return
        texts = [self._embed_text(e) for e in self.entries]
        self._emb = self.embedder.encode(texts) if texts else np.zeros((0, self.embedder.dim), np.float32)
        self._emb_dirty = False

    # -- mutation ----------------------------------------------------------- #

    def add(
        self,
        *,
        type: str,
        topic: str,
        statement: str,
        source: SourceRef,
        session_id: str = "default",
        due_at: Optional[str] = None,
        stale_after_hours: Optional[float] = None,
        stale_flag: bool = False,
        confidence: float = 0.8,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            entry_id="rm-" + uuid.uuid4().hex[:12],
            type=type,
            topic=topic,
            statement=statement,
            source=source,
            session_id=session_id,
            due_at=due_at,
            stale_after_hours=stale_after_hours,
            stale_flag=stale_flag,
            confidence=confidence,
        )
        self.entries.append(entry)
        self._emb_dirty = True
        self._persist()
        return entry

    def supersede(self, old: MemoryEntry, new: MemoryEntry) -> None:
        old.status = "superseded"
        old.superseded_by = new.entry_id
        old.updated_at = _iso(_now())
        self._persist()

    # -- queries ------------------------------------------------------------ #

    def active(self) -> List[MemoryEntry]:
        return [e for e in self.entries if e.status == "active"]

    def by_topic(self, topic: str, active_only: bool = True) -> List[MemoryEntry]:
        return [
            e for e in self.entries
            if e.topic == topic and (not active_only or e.status == "active")
        ]

    def recall(self, query: str, k: int = 5, active_only: bool = True) -> List[Dict[str, Any]]:
        """Top-k semantic recall. Returns list of {entry, score}."""
        self._ensure_index()
        if not self.entries:
            return []
        qv = self.embedder.encode([query])[0]
        sims = cosine(qv, self._emb)
        order = np.argsort(-sims)
        out: List[Dict[str, Any]] = []
        for idx in order:
            e = self.entries[int(idx)]
            if active_only and e.status != "active":
                continue
            out.append({"entry": e, "score": float(sims[int(idx)])})
            if len(out) >= k:
                break
        return out

    def conflict_candidates(
        self, entry: MemoryEntry, sim_threshold: float = 0.45, k: int = 4
    ) -> List[MemoryEntry]:
        """Prior active entries that might conflict with ``entry``.

        Combines exact-topic matches with the top semantically-similar entries
        (so a supersede fires even when the reasoner assigns slightly different
        topic slugs to the old and new fact, e.g. ``python_version`` vs
        ``toolchain``).
        """
        cands: Dict[str, MemoryEntry] = {}
        for e in self.by_topic(entry.topic, active_only=True):
            if e.entry_id != entry.entry_id:
                cands[e.entry_id] = e
        for hit in self.recall(self._embed_text(entry), k=k + 1, active_only=True):
            e = hit["entry"]
            if e.entry_id != entry.entry_id and hit["score"] >= sim_threshold:
                cands[e.entry_id] = e
        return list(cands.values())

    def due_within(self, hours: float, now: Optional[datetime] = None) -> List[MemoryEntry]:
        now = now or _now()
        out = []
        for e in self.active():
            h = e.hours_until_due(now)
            if h is not None and 0 <= h <= hours:
                out.append(e)
        out.sort(key=lambda e: e.hours_until_due(now) or 0)
        return out

    def stale_now(self, now: Optional[datetime] = None) -> List[MemoryEntry]:
        now = now or _now()
        return [e for e in self.entries if e.status == "active" and e.is_stale(now)]

    def __len__(self) -> int:
        return len(self.entries)
