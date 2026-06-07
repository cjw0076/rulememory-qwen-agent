#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_MODEL = "qwen-plus"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def build_prompt(seed_path: Path) -> str:
    seed = seed_path.read_text(encoding="utf-8")
    return (
        "You are RuleMemory running on Qwen Cloud. "
        "Return JSON with keys remembered_facts, stale_risk, next_action. "
        "Use this RuleMemory seed as the only source.\n\n"
        f"{seed[:6000]}"
    )


def post_chat(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 220,
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return {
                "http_status": response.status,
                "body": json.loads(response.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"http_status": exc.code, "body": body}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RuleMemory against Qwen MaaS")
    parser.add_argument(
        "--seed",
        default="docs/rule_memory_live_seed_20260607.json",
        help="Path to sanitized RuleMemory seed JSON",
    )
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "QWEN_OPENAI_BASE_URL",
            os.environ.get("DASHSCOPE_OPENAI_BASE_URL", DEFAULT_BASE_URL),
        ),
    )
    args = parser.parse_args()

    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("missing QWEN_API_KEY or DASHSCOPE_API_KEY")

    seed_path = Path(args.seed)
    if not seed_path.exists():
        raise SystemExit(f"missing seed file: {seed_path}")

    result = post_chat(args.base_url, api_key, args.model, build_prompt(seed_path))
    output = {
        "service": "qwen-cloud-maas-openai-compatible",
        "base_url": args.base_url,
        "model": args.model,
        "seed_path": str(seed_path),
        "http_status": result["http_status"],
        "secret_written": False,
    }
    if result["http_status"] == 200:
        message = result["body"]["choices"][0]["message"]["content"]
        output["assistant_preview"] = message[:500]
    else:
        output["error_preview"] = str(result["body"])[:500]

    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0 if result["http_status"] == 200 else 20


if __name__ == "__main__":
    sys.exit(main())
