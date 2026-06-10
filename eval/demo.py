#!/usr/bin/env python3
"""Multi-session RuleMemory demo proving persistence + recall + stale detection.

Session 1 (process A): ingest contest rules incl. a STALE "use Python 2"
assumption + a deadline; the agent extracts facts with Qwen and stores them.

Session 2 (process B, after a simulated restart): the agent reloads memory from
disk, ingests a correction that SUPERSEDES the Python-2 assumption, flags the
stale entry, and answers deadline / version / membership questions grounded on
semantically-recalled memory.

Backend selection (make_reasoner): Qwen Cloud if QWEN_API_KEY/DASHSCOPE_API_KEY
is set, else local Qwen2.5-VL-7B via transformers, else the rule-based fallback.
Force a backend with --backend {cloud,local,rule-based}.

    python eval/demo.py --backend local       # real local Qwen
    python eval/demo.py --backend rule-based   # GPU-free
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rulememory_qwen import RuleMemoryAgent, Memory, make_reasoner  # noqa: E402
from rulememory_qwen.embedder import make_embedder  # noqa: E402

sys.path.insert(0, str(ROOT / "eval"))
from scenario import SESSION1_RULES, SESSION2_UPDATE, QUESTIONS  # noqa: E402


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show_facts(facts):
    for f in facts:
        flag = " [STALE]" if f.get("stale") else ""
        due = f"  due={f['due_at']}" if f.get("due_at") else ""
        print(f"  - ({f['type']:>10}) {f['statement']}{flag}{due}")


def make_agent(backend: str, mem_path: str, transcript_path: str) -> RuleMemoryAgent:
    reasoner = make_reasoner(prefer=None if backend == "auto" else backend)
    embedder = make_embedder("hashing" if backend == "rule-based" else None)
    memory = Memory(path=mem_path, embedder=embedder)
    return RuleMemoryAgent(reasoner=reasoner, memory=memory, transcript_path=transcript_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="auto", choices=["auto", "cloud", "local", "rule-based"])
    ap.add_argument("--store", default=str(ROOT / "eval" / "_demo_run"))
    args = ap.parse_args()

    store = Path(args.store)
    store.mkdir(parents=True, exist_ok=True)
    mem_path = str(store / "memory.jsonl")
    transcript_path = str(store / "transcript.jsonl")
    # fresh run
    for p in (mem_path, transcript_path):
        Path(p).unlink(missing_ok=True)

    # ---------------- SESSION 1 ---------------- #
    rule("SESSION 1  —  ingest contest rules (real Qwen fact extraction)")
    agent1 = make_agent(args.backend, mem_path, transcript_path)
    print(f"reasoner backend : {agent1.reasoner.name}")
    print(f"embedder         : {agent1.memory.embedder.name}")
    print(f"\nSOURCE TEXT:\n  {SESSION1_RULES}\n")
    res1 = agent1.ingest(SESSION1_RULES, source_id="contest-rules-v1", session_id="s1")
    print(f"Qwen extracted {res1['added_count']} facts:")
    show_facts(res1["facts"])
    print(f"\nStale flagged after session 1: {[s['statement'] for s in res1['stale']]}")
    print(f"Memory persisted to {mem_path}  ({len(agent1.memory)} entries)")
    del agent1  # simulate process exit

    # ---------------- SESSION 2 (RESTART) ---------------- #
    rule("SESSION 2  —  RESTART: reload from disk, ingest correction, answer")
    agent2 = make_agent(args.backend, mem_path, transcript_path)
    print(f"reloaded {len(agent2.memory)} entries from disk (cross-session memory).")

    print(f"\nCORRECTION SOURCE:\n  {SESSION2_UPDATE}\n")
    res2 = agent2.ingest(SESSION2_UPDATE, source_id="organizer-update-v2", session_id="s2")
    print(f"Qwen extracted {res2['added_count']} facts from the correction:")
    show_facts(res2["facts"])
    if res2["conflicts"]:
        rule("CONFLICT / SUPERSEDE detected")
        for c in res2["conflicts"]:
            print(f"  topic={c['topic']}: '{c['superseded_statement']}'")
            print(f"     -> SUPERSEDED BY '{c['by_statement']}'  ({c['reason']})")

    rule("STALE REPORT (now)")
    for s in agent2.stale_report():
        print(f"  - {s['type']}: {s['statement']}  ::  {s['reason']}")

    rule("DEADLINES DUE WITHIN 45 DAYS (1080h)")
    for d in agent2.due_within(1080):
        print(f"  - {d['statement']}  (in {d['hours_until_due']}h, due {d['due_at']})")

    # ---------------- GROUNDED Q&A ---------------- #
    rule("GROUNDED Q&A  (semantic recall -> Qwen answer)")
    for q in QUESTIONS:
        out = agent2.answer(q, k=4)
        print(f"\nQ: {q}")
        print("  recall hits:")
        for h in out["recalled"]:
            tag = " [STALE]" if h["stale"] else ""
            print(f"    {h['score']:.3f}  ({h['type']}){tag} {h['statement']}")
        print(f"  A: {out['answer']}")
        if out["warnings"]:
            for w in out["warnings"]:
                print(f"  ! warning: {w}")
        if out["citations"]:
            cites = ", ".join(f"#{c['n']}->{c['source_id']}[{c['char_span'][0]}:{c['char_span'][1]}]"
                              for c in out["citations"])
            print(f"  provenance: {cites}")

    rule("MEMORY TABLE (final, with provenance + status)")
    for r in agent2.memory_table():
        st = r["status"].upper()
        stale = "stale" if r["stale"] else "fresh"
        print(f"  [{st:>10}|{stale:>5}] ({r['type']:>10}) {r['statement']}")
        print(f"               prov: {r['source']['source_id']}"
              f"[{r['source']['char_start']}:{r['source']['char_end']}] "
              f"sess={r['session_id']}")

    rule("TRANSCRIPT (replayable) — step summary")
    for ev in agent2.transcript:
        print(f"  {ev['ts']}  {ev['step']:>16}  ({ev['reasoner']})")

    print(f"\nFull transcript JSONL: {transcript_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
