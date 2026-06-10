#!/usr/bin/env python3
"""FastAPI server for the RuleMemory web UI.

Demonstrates cross-session memory: ingest rules, ask questions, inspect Qwen's
extracted facts, the full memory table (provenance / stale / superseded), the
semantic-recall hits for a query, and the replayable transcript.

Run (GPU-free demo backend):
    RULEMEMORY_BACKEND=rule-based RULEMEMORY_FORCE_HASH_EMBED=1 \
        python webapp/server.py

Run with real local Qwen:
    RULEMEMORY_BACKEND=local /home/user/miniconda3/envs/dacon_vlm/bin/python \
        webapp/server.py

Then open http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rulememory_qwen import RuleMemoryAgent, Memory, make_reasoner  # noqa: E402
from rulememory_qwen.embedder import make_embedder  # noqa: E402

STORE = Path(os.environ.get("RULEMEMORY_STORE", str(ROOT / "webapp" / "_store")))
STORE.mkdir(parents=True, exist_ok=True)
BACKEND = os.environ.get("RULEMEMORY_BACKEND", "rule-based")

app = FastAPI(title="RuleMemory — Qwen Cloud MemoryAgent")

_agent: Optional[RuleMemoryAgent] = None


def get_agent() -> RuleMemoryAgent:
    """Lazily build the agent (loads Qwen on first ingest/answer if backend=local)."""
    global _agent
    if _agent is None:
        reasoner = make_reasoner(prefer=None if BACKEND == "auto" else BACKEND)
        embedder = make_embedder("hashing" if BACKEND == "rule-based" else None)
        memory = Memory(path=str(STORE / "memory.jsonl"), embedder=embedder)
        _agent = RuleMemoryAgent(
            reasoner=reasoner,
            memory=memory,
            transcript_path=str(STORE / "transcript.jsonl"),
        )
    return _agent


class IngestReq(BaseModel):
    text: str
    source_id: str = "ui-input"
    session_id: str = "ui"


class AskReq(BaseModel):
    question: str
    k: int = 5


@app.get("/api/status")
def status():
    a = get_agent()
    return {
        "backend": a.reasoner.name,
        "embedder": a.memory.embedder.name,
        "entries": len(a.memory),
        "store": str(STORE),
    }


@app.post("/api/ingest")
def ingest(req: IngestReq):
    a = get_agent()
    res = a.ingest(req.text, source_id=req.source_id, session_id=req.session_id)
    return JSONResponse(res)


@app.post("/api/ask")
def ask(req: AskReq):
    a = get_agent()
    return JSONResponse(a.answer(req.question, k=req.k))


@app.post("/api/recall")
def recall(req: AskReq):
    a = get_agent()
    hits = a.memory.recall(req.question, k=req.k, active_only=True)
    return JSONResponse(
        {
            "query": req.question,
            "hits": [
                {
                    "entry_id": h["entry"].entry_id,
                    "score": round(h["score"], 4),
                    "type": h["entry"].type,
                    "statement": h["entry"].statement,
                    "stale": h["entry"].is_stale(),
                }
                for h in hits
            ],
        }
    )


@app.get("/api/memory")
def memory():
    a = get_agent()
    return JSONResponse(
        {
            "table": a.memory_table(),
            "stale": a.stale_report(),
            "due_72h": a.due_within(72),
            "summary": a.reasoner.summarize([e.for_reasoner() for e in a.memory.active()]),
        }
    )


@app.get("/api/transcript")
def transcript():
    a = get_agent()
    return JSONResponse({"transcript": a.transcript})


@app.post("/api/reset")
def reset():
    global _agent
    for f in ("memory.jsonl", "transcript.jsonl"):
        (STORE / f).unlink(missing_ok=True)
    _agent = None
    return {"ok": True}


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")), log_level="info")
