# Qwen API Smoke Report (2026-06-07 01:28 KST)

> Cached report from a verified live run on 2026-06-07. The workspace host is a
> sanitized placeholder. Re-run `./scripts/qwen_api_smoke.sh` with your own key
> and `QWEN_OPENAI_BASE_URL` to reproduce.

## Command run

- `./scripts/qwen_api_smoke.sh` with provided `QWEN_API_KEY`
- `QWEN_OPENAI_BASE_URL` pointed at the operator-provided MaaS OpenAI-compatible endpoint:
  - `https://your-workspace-id.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`

## Observed result

- `models` endpoint: `HTTP 200`
- `chat completion` endpoint: `HTTP 200`
- Response body confirms model list access and a minimal `qwen-plus` chat completion.

## Conclusion

- Qwen workspace MaaS endpoint is reachable from this workspace.
- API credential is valid for the operator-provided OpenAI-compatible endpoint.
- The prior `invalid_api_key` blocker was tied to using the wrong/default endpoint or an older invalid key.
- No secret values were persisted in repository.
- Latest revalidation artifact:
  - `docs/rule_memory_readiness_packet.md`

## Next required operator step

- Keep using the workspace-specific `QWEN_OPENAI_BASE_URL` together with `QWEN_API_KEY`.
- Proceed to seed first `memory_entry` records for deadline / eligibility / submission requirements.
