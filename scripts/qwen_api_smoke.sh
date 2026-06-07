#!/usr/bin/env bash
set -euo pipefail

base_url="${QWEN_OPENAI_BASE_URL:-${DASHSCOPE_OPENAI_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}}"
base_url="${base_url%/}"
readonly ENDPOINT="${base_url}/models"
readonly MODEL_ENDPOINT="${base_url}/chat/completions"

if [[ -n "${DASHSCOPE_API_KEY:-}" ]]; then
  API_KEY="${DASHSCOPE_API_KEY}"
elif [[ -n "${QWEN_API_KEY:-}" ]]; then
  API_KEY="${QWEN_API_KEY}"
else
  echo "blocked: no DASHSCOPE_API_KEY or QWEN_API_KEY found in environment"
  echo "next_step: set key env then rerun this script"
  exit 10
fi

echo "running: models endpoint smoke"
echo "base_url: ${base_url}"
curl -sS -o /tmp/qwen_models.json -w "status=%{http_code}\\n" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  "${ENDPOINT}"

if [[ -s /tmp/qwen_models.json ]]; then
  echo "response_sample: $(cat /tmp/qwen_models.json | head -c 400)"
else
  echo "no_json_payload"
fi

echo "running: chat completion probe (minimal payload)"
curl -sS -o /tmp/qwen_chat.json -w "status=%{http_code}\\n" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  "${MODEL_ENDPOINT}"

if [[ -s /tmp/qwen_chat.json ]]; then
  echo "response_sample: $(cat /tmp/qwen_chat.json | head -c 400)"
fi
