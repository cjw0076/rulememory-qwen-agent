"""GPU/credential-free tests using the rule-based reasoner + hashing embedder."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("RULEMEMORY_FORCE_FALLBACK", "1")
os.environ.setdefault("RULEMEMORY_FORCE_HASH_EMBED", "1")

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from rulememory_qwen import RuleMemoryAgent, Memory, make_reasoner  # noqa: E402
from rulememory_qwen.reasoner import RuleBasedReasoner  # noqa: E402
from rulememory_qwen.embedder import make_embedder, HashingTfidfEmbedder  # noqa: E402


def make_agent(tmp_path, **kw):
    mem = Memory(path=str(tmp_path / "mem.jsonl"), embedder=make_embedder("hashing"))
    return RuleMemoryAgent(reasoner=RuleBasedReasoner(), memory=mem,
                           transcript_path=str(tmp_path / "t.jsonl"), **kw)


def test_factory_returns_fallback_when_forced():
    assert isinstance(make_reasoner(), RuleBasedReasoner)


def test_embedder_fallback_is_hashing():
    assert isinstance(make_embedder("hashing"), HashingTfidfEmbedder)


def test_ingest_extracts_typed_facts(tmp_path):
    agent = make_agent(tmp_path)
    text = ("The submission deadline is 2026-07-10. Teams must have at most 4 members. "
            "We should still use Python 2 for the toolchain.")
    res = agent.ingest(text, source_id="rules-v1")
    assert res["added_count"] >= 3
    types = {r["type"] for r in agent.memory_table()}
    assert "deadline" in types
    assert "rule" in types
    # the python-2 line should be flagged stale
    assert any("python 2" in s.lower() for s in
               [e["statement"] for e in agent.stale_report()])


def test_provenance_span_recorded(tmp_path):
    agent = make_agent(tmp_path)
    text = "Teams must register before the kickoff."
    agent.ingest(text, source_id="src")
    row = agent.memory_table()[0]
    s, e = row["source"]["char_start"], row["source"]["char_end"]
    assert 0 <= s < e <= len(text)
    assert row["source"]["quote"]


def test_semantic_recall_orders_by_relevance(tmp_path):
    agent = make_agent(tmp_path)
    agent.ingest("The submission deadline is 2026-07-10. "
                 "The grand prize is 10000 dollars. "
                 "Teams may use any Qwen model.", source_id="s")
    hits = agent.memory.recall("when is the deadline to submit", k=3)
    assert hits
    assert "deadline" in hits[0]["entry"].statement.lower()


def test_conflict_supersede(tmp_path):
    agent = make_agent(tmp_path)
    agent.ingest("We should still use Python 2 for the toolchain.", source_id="s1")
    agent.ingest("The toolchain now requires Python 3.11.", source_id="s2")
    rows = agent.memory_table()
    superseded = [r for r in rows if r["status"] == "superseded"]
    assert superseded, "older python fact should be superseded"


def test_deadline_due_within(tmp_path):
    agent = make_agent(tmp_path)
    from datetime import datetime, timezone, timedelta
    soon = (datetime.now(timezone.utc) + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%S")
    agent.ingest(f"The internal freeze is {soon}.", source_id="s")
    due = agent.due_within(48)
    assert due and due[0]["hours_until_due"] <= 48


def test_passed_deadline_is_stale(tmp_path):
    agent = make_agent(tmp_path)
    agent.ingest("The early-bird deadline was 2020-01-01.", source_id="s")
    assert any("deadline passed" in (r["reason"] or "") for r in agent.stale_report())


def test_cross_session_persistence(tmp_path):
    p = str(tmp_path / "mem.jsonl")
    m1 = Memory(path=p, embedder=make_embedder("hashing"))
    a1 = RuleMemoryAgent(reasoner=RuleBasedReasoner(), memory=m1)
    a1.ingest("The deadline is 2026-07-10. Use Python 2.", source_id="s1")
    n = len(m1)
    # simulate restart
    m2 = Memory(path=p, embedder=make_embedder("hashing"))
    assert len(m2) == n
    a2 = RuleMemoryAgent(reasoner=RuleBasedReasoner(), memory=m2)
    res = a2.answer("what is the deadline?")
    assert res["recalled"]


def test_answer_grounded_and_warns_stale(tmp_path):
    agent = make_agent(tmp_path)
    agent.ingest("We should still use Python 2.", source_id="s")
    res = agent.answer("what python version should we use?")
    assert res["recalled"]
    assert res["warnings"]


def test_transcript_is_replayable(tmp_path):
    agent = make_agent(tmp_path)
    agent.ingest("The deadline is 2026-07-10.", source_id="s")
    agent.answer("deadline?")
    steps = [e["step"] for e in agent.transcript]
    for required in ["ingest_start", "facts_extracted", "ingest_done", "question", "recall", "answer"]:
        assert required in steps


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
