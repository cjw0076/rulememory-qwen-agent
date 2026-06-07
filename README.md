# RuleMemory

RuleMemory is a Qwen-powered MemoryAgent for competition and launch teams that
must keep rules, deadlines, source evidence, stale assumptions, and submission
readiness synchronized across sessions.

## Track

- Hackathon: Global AI Hackathon Series with Qwen Cloud
- Track: MemoryAgent
- Core model route: Qwen Cloud MaaS OpenAI-compatible endpoint
- Recommended public repo name: `rulememory-qwen-agent`
- License: MIT

## Why It Matters

Teams lose time and make bad submission decisions when rules, deadlines,
eligibility constraints, and platform requirements live only in chat context.
RuleMemory turns those facts into auditable memory entries with source
references, stale-check policy, and repeatable readiness packets.

## Current Demo

The demo proves three things:

1. A live Qwen model call succeeds from the target environment.
2. Qwen reads the live RuleMemory seed and summarizes remembered facts, stale
   risks, and next builder action.
3. The local RuleMemory pipeline emits a refreshed readiness packet without
   writing secrets.

Run:

```bash
export QWEN_API_KEY="<your key>"
export QWEN_OPENAI_BASE_URL="https://<your-workspace-host>/compatible-mode/v1"
./scripts/qwen_rule_memory_demo.sh
```

Generated evidence:

- `docs/qwen_rule_memory_demo_trace.md`
- `docs/rule_memory_readiness_packet.md`
- `docs/rule_memory_live_seed_20260607.json`

## Architecture

```text
Official sources / operator receipts
  -> RuleMemory seed entries
  -> Qwen model call
  -> remembered facts + stale-risk warning + next action
  -> readiness packet and demo trace
```

Next architecture diagram should show:

- Qwen Cloud MaaS endpoint
- RuleMemory JSON store
- source freshness monitor
- readiness packet generator
- public submission package

Architecture and deployment proof assets:

- `docs/architecture_diagram.md`
- `deploy/alibaba_cloud/qwen_maas_client.py`
- `docs/alibaba_cloud_deployment_proof.md`
- `docs/devpost_submission_answers.md`
- `docs/final_submission_checklist.md`

## What Is Remembered

- submission deadline and internal freeze target
- selected track and rationale
- Qwen cloud API proof
- next package decision
- stale source window and refresh policy

## Privacy

No API keys, provider credentials, account exports, cookies, raw private logs,
or private workspace history are written to generated docs. Public examples use
environment variable placeholders only.

## Shipping

To publish this repo, record the demo video, and submit on Devpost, follow
`docs/FOUNDER_SHIP_STEPS.md` (exact copy-paste commands and a shot-by-shot
video script).

## Status

- Qwen cloud smoke: verified (cached trace in `docs/qwen_api_smoke_report.md`)
- Qwen-backed demo call: verified (cached trace in `docs/qwen_rule_memory_demo_trace.md`)
- Live RuleMemory seed: ready
- Architecture diagram: ready
- Alibaba Cloud/Qwen code-file proof: ready and locally verified
- Public repo safety review: complete (secret-safe, hosts/paths sanitized)
- Devpost answer draft: ready
- Final submission checklist: ready
- Ship steps: `docs/FOUNDER_SHIP_STEPS.md`
- Remaining founder-only gates: create public repo, record 3-min video, submit on Devpost
