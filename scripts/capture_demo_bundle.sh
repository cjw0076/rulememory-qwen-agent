#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/docs/demo_terminal_capture_bundle.md"
PROOF_OUT="$(mktemp /tmp/qwen-proof-output-XXXXXX.json)"
trap 'rm -f "$PROOF_OUT"' EXIT

if [[ -z "${QWEN_API_KEY:-}${DASHSCOPE_API_KEY:-}" ]]; then
  echo "blocked: set QWEN_API_KEY or DASHSCOPE_API_KEY"
  exit 10
fi

if [[ -z "${QWEN_OPENAI_BASE_URL:-}${DASHSCOPE_OPENAI_BASE_URL:-}" ]]; then
  echo "blocked: set QWEN_OPENAI_BASE_URL or DASHSCOPE_OPENAI_BASE_URL"
  exit 11
fi

demo_trace="$("${ROOT}/scripts/qwen_rule_memory_demo.sh")"

(
  cd "$ROOT"
  python3 deploy/alibaba_cloud/qwen_maas_client.py \
    --seed docs/rule_memory_live_seed_20260607.json >"$PROOF_OUT"
)

status="$(python3 - "$PROOF_OUT" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["http_status"])
PY
)"

if [[ "$status" != "200" ]]; then
  echo "proof_client_status=${status}"
  cat "$PROOF_OUT"
  exit 20
fi

{
  echo "# RuleMemory Terminal Capture Bundle"
  echo
  echo "- generated_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "- package: RuleMemory"
  echo "- track: MemoryAgent"
  echo "- capture_status: ready"
  echo
  echo "## Screen 1: Secret-Safe Setup"
  echo
  echo '```bash'
  echo 'export QWEN_API_KEY="<redacted>"'
  echo 'export QWEN_OPENAI_BASE_URL="https://<workspace-host>/compatible-mode/v1"'
  echo '```'
  echo
  echo "## Screen 2: Qwen-Backed RuleMemory Demo"
  echo
  echo '```bash'
  echo './scripts/qwen_rule_memory_demo.sh'
  echo '```'
  echo
  echo "- generated_trace: ${demo_trace#$ROOT/}"
  echo
  echo "Trace excerpt:"
  echo
  echo '```text'
  sed -n '1,38p' "$ROOT/docs/qwen_rule_memory_demo_trace.md"
  echo '```'
  echo
  echo "## Screen 3: Alibaba/Qwen Cloud Code-File Proof"
  echo
  echo '```bash'
  echo 'python3 deploy/alibaba_cloud/qwen_maas_client.py --seed docs/rule_memory_live_seed_20260607.json'
  echo '```'
  echo
  echo "Proof output:"
  echo
  echo '```json'
  cat "$PROOF_OUT"
  echo
  echo '```'
  echo
  echo "## Screen 4: Submission Package Status"
  echo
  echo '```text'
  sed -n '1,70p' "$ROOT/docs/public_package_checklist.md"
  echo '```'
  echo
  echo "## Capture Rules"
  echo
  echo "- Do not show real API keys."
  echo "- Do not show shell history."
  echo "- Keep the final video under about 3 minutes."
  echo "- Use this bundle as the terminal script for the recording."
} >"$OUT"

echo "$OUT"
