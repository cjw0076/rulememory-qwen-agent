# Alibaba Cloud Deployment Proof Asset

Updated: 2026-06-07 KST

## Purpose

Devpost asks for proof that the project backend runs on Alibaba Cloud and uses
Alibaba Cloud services/APIs. This package currently provides a code-file proof
for the Qwen Cloud MaaS OpenAI-compatible API path and identifies the remaining
runtime recording step.

## Code-File Proof

- proof file: `deploy/alibaba_cloud/qwen_maas_client.py`
- service: Qwen Cloud MaaS OpenAI-compatible API
- model: `qwen-plus`
- seed input: `docs/rule_memory_live_seed_20260607.json`
- secret handling: environment variables only; no secrets written to output

## Verified Local Runtime Result

Command shape:

```bash
QWEN_API_KEY=... \
QWEN_OPENAI_BASE_URL=https://<workspace-host>/compatible-mode/v1 \
python3 deploy/alibaba_cloud/qwen_maas_client.py \
  --seed docs/rule_memory_live_seed_20260607.json
```

Observed result:

- `http_status`: `200`
- `service`: `qwen-cloud-maas-openai-compatible`
- `model`: `qwen-plus`
- `secret_written`: `false`

## Remaining Devpost Proof Step

For final submission, capture a short recording from the deployed Alibaba Cloud
runtime showing:

- the public repository code file
- the deployed backend/runtime shell or logs
- the same client returning `http_status: 200`
- no API key, shell history, cookies, or provider credentials visible

## Evidence Links

- `deploy/alibaba_cloud/qwen_maas_client.py`
- `docs/qwen_api_smoke_report.md`
- `docs/qwen_rule_memory_demo_trace.md`
- `docs/public_package_checklist.md`
