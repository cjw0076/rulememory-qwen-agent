#!/usr/bin/env python3
"""Create a local RuleMemory readiness artifact from baseline sources.

This helper intentionally does not call Qwen APIs.
It proves the local memory pipeline shape is valid before API credentials
unblock real submission execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


@dataclass
class Entry:
    entry_id: str
    entry_type: str
    title: str
    summary: str
    confidence: float
    status: str
    created_at_utc: str
    source_refs: List[Dict[str, str]]
    long_form: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "status": self.status,
            "created_at_utc": self.created_at_utc,
            "source_refs": self.source_refs,
        }
        if self.long_form:
            payload["long_form"] = self.long_form
        return payload


def build_payload() -> Dict[str, Any]:
    source_id = "qwen-dashscope-rules-20260606"
    source_time = now_utc()

    source_records = [
        {
            "source_id": source_id,
            "source_name": "Qwen Cloud Hackathon baseline briefs",
            "source_url": "https://qwencloud-hackathon.devpost.com/rules",
            "source_type": "official_rules",
            "fetched_at_utc": source_time,
            "content_hash": sha1_hex("qwen cloud hackathon rules snapshot") ,
            "http_status": 200,
            "license_scope": "public",
            "region": "global",
            "stale_after_hours": 24,
            "notes": "Local snapshot placeholder for local demo mode."
        }
    ]

    source_ref = {
        "source_id": source_id,
        "section_hint": "submission period and track section",
        "captured_at_utc": source_time,
    }

    entries = [
        Entry(
            entry_id="rm-20260606-001",
            entry_type="deadline",
            title="Qwen Cloud Hackathon submission window",
            summary="Submit period remains open in local baseline notes.",
            confidence=0.86,
            status="active",
            created_at_utc=source_time,
            source_refs=[source_ref],
            long_form=(
                "Local baseline records that the submission window is still open "
                "(check operator-provided latest official page before final freeze)."
            ),
        ),
        Entry(
            entry_id="rm-20260606-002",
            entry_type="rule",
            title="Track alignment",
            summary="MemoryAgent remains the target track for this workspace.",
            confidence=0.92,
            status="active",
            created_at_utc=source_time,
            source_refs=[source_ref],
            long_form="RuleMemory aligns with this workspace's evidence-first pipeline design.",
        ),
        Entry(
            entry_id="rm-20260606-003",
            entry_type="preference",
            title="Offline credential-free build path",
            summary=(
                "When key is unavailable, keep schema, smoke report, and synthetic "
                "ingest path ready as operator-gated artifact branch."
            ),
            confidence=0.81,
            status="active",
            created_at_utc=source_time,
            source_refs=[source_ref],
            long_form=(
                "This branch preserves evidence and allows quick transition once "
                "DASHSCOPE_API_KEY/QWEN_API_KEY is provided."
            ),
        ),
    ]

    smoke_endpoint = os.environ.get(
        "QWEN_SMOKE_ENDPOINT",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
    )
    smoke_status = int(os.environ.get("QWEN_SMOKE_HTTP_STATUS", "401"))
    smoke_result = os.environ.get("QWEN_SMOKE_RESULT", "blocked")
    smoke_error = os.environ.get("QWEN_SMOKE_ERROR_CODE", "missing_key")

    return {
        "version": "1.0",
        "updated_at_utc": source_time,
        "entries": [entry.to_dict() for entry in entries],
        "sources": source_records,
        "runbook": {
            "smoke_test": {
                "run_at_utc": source_time,
                "endpoint": smoke_endpoint,
                "http_status": smoke_status,
                "result": smoke_result,
                "error_code": smoke_error,
            },
            "stale_check_policy": "strict",
            "last_orchestrator": "codex.local_demo",
            "next_actions": [
                "Inject DASHSCOPE_API_KEY or QWEN_API_KEY",
                "Run scripts/qwen_api_smoke.sh",
                "Populate live source hashes with official fetch jobs",
            ],
        },
    }


def write_readiness_markdown(readiness: Dict[str, Any], out_path: Path) -> None:
    smoke = readiness["runbook"]["smoke_test"]
    smoke_line = f"{smoke['result']} (HTTP {smoke['http_status']})"
    operator_gate = "Live Qwen cloud proof exists; continue with builder artifacts."
    if smoke["result"] != "verified":
        operator_gate = "Provide DASHSCOPE_API_KEY or QWEN_API_KEY and rerun smoke test."

    lines = [
        "# RuleMemory Readiness Packet (Demo Mode)",
        "",
        f"generated_at_utc: {readiness['updated_at_utc']}",
        "",
        "## Entries",
        "",
    ]
    for entry in readiness["entries"]:
        lines.extend(
            [
                f"### {entry['entry_id']} | {entry['entry_type']} ({entry['status']})",
                f"- title: {entry['title']}",
                f"- summary: {entry['summary']}",
                f"- confidence: {entry['confidence']}",
                f"- source_ref_count: {len(entry['source_refs'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Readiness summary",
            "",
            "- schema_file: docs/rule_memory_schema.json",
            f"- smoke_result: {smoke_line}",
            f"- smoke_endpoint: {smoke['endpoint']}",
            "- next: build live RuleMemory seed entries and public package assets",
            "",
            "## Operator Gate",
            "",
            f"- {operator_gate}",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local RuleMemory readiness packet")
    parser.add_argument("--out", default="docs/rule_memory_readiness_packet.md")
    args = parser.parse_args()

    payload = build_payload()
    out_path = ROOT / args.out
    write_readiness_markdown(payload, out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
