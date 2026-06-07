# Qwen Public Package Checklist

Updated: 2026-06-07 KST

## Package State

- package_name: RuleMemory
- target_track: MemoryAgent
- cloud_proof: verified (`HTTP 200` models + chat through workspace MaaS OpenAI-compatible endpoint)
- current_stage: builder package prep
- official_deadline: 2026-07-09 14:00 PDT
- latest_official_check: 2026-06-07 KST

## Required Assets

- [x] Qwen API smoke proof: `docs/qwen_api_smoke_report.md`
- [x] RuleMemory schema: `docs/rule_memory_schema.json`
- [x] Live RuleMemory seed: `docs/rule_memory_live_seed_20260607.json`
- [x] Readiness packet: `docs/rule_memory_readiness_packet.md`
- [x] Demo script draft: `docs/demo_script_3min.md`
- [x] Source freshness report: `docs/source_freshness_report_20260606.md`
- [x] Minimal runnable demo command that calls Qwen and emits a readiness packet: `scripts/qwen_rule_memory_demo.sh`
- [x] Demo trace for video capture: `docs/qwen_rule_memory_demo_trace.md`
- [x] Public README with install/run/demo sections: `docs/public_readme_draft.md`
- [x] Architecture diagram showing Qwen Cloud, RuleMemory store, source monitor, and readiness packet output: `docs/architecture_diagram.md`
- [x] Alibaba Cloud deployment proof code-file asset: `deploy/alibaba_cloud/qwen_maas_client.py`, `docs/alibaba_cloud_deployment_proof.md`
- [x] Demo-video capture plan: `docs/demo_video_capture_plan.md`
- [x] Terminal capture bundle for demo video: `docs/demo_terminal_capture_bundle.md`
- [ ] Final deployed Alibaba Cloud runtime recording
- [x] License decision: MIT (`LICENSE`)
- [x] Public repo safety review: `docs/public_repo_safety_review.md`
- [x] Devpost form answers and track selection: `docs/devpost_submission_answers.md`
- [x] Final submission checklist: `docs/final_submission_checklist.md`

## Judge-Facing Claims

- Qwen is central because the demo must use a Qwen model call before producing or updating the RuleMemory packet.
- Memory is central because the output changes across sessions as deadlines, stale assumptions, and source proofs are persisted.
- Provenance is central because every memory entry carries source references and stale-check policy metadata.
- The package maps to Devpost judging: technical depth, innovation, problem value, and presentation/documentation.

## Privacy Gate

- No API keys, tokens, account exports, cookies, raw private logs, or private workspace history can enter the public repo.
- Public artifacts should reference sanitized evidence paths, not secret-bearing shell commands.

## Next Builder Slice

Create screen/video captures and final deployed runtime proof:

```bash
QWEN_API_KEY=... \
QWEN_OPENAI_BASE_URL=https://your-workspace-id.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1 \
./scripts/qwen_rule_memory_demo.sh
```

For public documentation, replace secret values with environment variable placeholders only.

## Official Source Pointers

- https://qwencloud-hackathon.devpost.com/
- https://qwencloud-hackathon.devpost.com/rules
- https://qwencloud-hackathon.devpost.com/resources
