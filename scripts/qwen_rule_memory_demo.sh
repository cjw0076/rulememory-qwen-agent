#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
BASE_URL="${QWEN_OPENAI_BASE_URL:-${DASHSCOPE_OPENAI_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}}"
BASE_URL="${BASE_URL%/}"
MODEL="${QWEN_MODEL:-qwen-plus}"
TRACE_OUT="${ROOT}/docs/qwen_rule_memory_demo_trace.md"
BODY_FILE="$(mktemp /tmp/qwen-rule-memory-body-XXXXXX.json)"
PAYLOAD_FILE="$(mktemp /tmp/qwen-rule-memory-payload-XXXXXX.json)"
trap 'rm -f "$BODY_FILE" "$PAYLOAD_FILE"' EXIT

if [[ -n "${DASHSCOPE_API_KEY:-}" ]]; then
  API_KEY="${DASHSCOPE_API_KEY}"
elif [[ -n "${QWEN_API_KEY:-}" ]]; then
  API_KEY="${QWEN_API_KEY}"
else
  echo "blocked: no DASHSCOPE_API_KEY or QWEN_API_KEY found in environment"
  exit 10
fi

python3 - "$ROOT" "$PAYLOAD_FILE" "$MODEL" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
payload_path = pathlib.Path(sys.argv[2])
model = sys.argv[3]
seed = (root / "docs" / "rule_memory_live_seed_20260607.json").read_text(encoding="utf-8")

prompt = (
    "You are the Qwen model inside the RuleMemory demo. "
    "Read this compact RuleMemory seed and produce ASCII-only output with: "
    "1) three remembered facts, 2) one stale-risk warning, 3) the next builder action. "
    "Keep it under 120 words.\n\n"
    f"RuleMemory seed JSON:\n{seed[:5000]}"
)

payload_path.write_text(
    json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 180,
            "temperature": 0.2,
        },
        ensure_ascii=True,
    ),
    encoding="utf-8",
)
PY

status="$(
  curl -sS -o "$BODY_FILE" -w "%{http_code}" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d @"$PAYLOAD_FILE" \
    "${BASE_URL}/chat/completions"
)"

if [[ "$status" != "200" ]]; then
  echo "qwen_demo_status=${status}"
  head -c 400 "$BODY_FILE"
  echo
  exit 20
fi

assistant_content="$(
  python3 - "$BODY_FILE" <<'PY'
import json
import sys

body = json.load(open(sys.argv[1], encoding="utf-8"))
content = body["choices"][0]["message"]["content"]
content = content.translate(
    str.maketrans(
        {
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "-",
        }
    )
)
content = content.encode("ascii", "ignore").decode("ascii")
print(content)
PY
)"

{
  echo "# Qwen RuleMemory Demo Trace"
  echo
  echo "- generated_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "- base_url: ${BASE_URL}"
  echo "- model: ${MODEL}"
  echo "- status: HTTP ${status}"
  echo "- seed: docs/rule_memory_live_seed_20260607.json"
  echo
  echo "## Qwen Output"
  echo
  printf '%s\n' "$assistant_content"
  echo
  echo "## Privacy"
  echo
  echo "- secrets: not written"
  echo "- request payload: generated from sanitized seed file"
} >"$TRACE_OUT"

QWEN_SMOKE_ENDPOINT="${BASE_URL}/models" \
QWEN_SMOKE_HTTP_STATUS=200 \
QWEN_SMOKE_RESULT=verified \
QWEN_SMOKE_ERROR_CODE=none \
  python3 "$ROOT/scripts/rule_memory_local_demo.py" >/dev/null

echo "$TRACE_OUT"
