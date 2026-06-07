# Public Repo Safety Review

Updated: 2026-06-07 KST

## Decision

- release_posture: prepare public repo
- license: MIT (`LICENSE`)
- status: safe with exclusions below

## Include

- `README.md`
- `LICENSE`
- `.gitignore`
- `scripts/qwen_api_smoke.sh`
- `scripts/qwen_rule_memory_demo.sh`
- `scripts/rule_memory_local_demo.py`
- `scripts/capture_demo_bundle.sh`
- `deploy/alibaba_cloud/qwen_maas_client.py`
- `docs/competition_brief_20260606.md`
- `docs/public_readme_draft.md`
- `docs/public_package_checklist.md`
- `docs/architecture_diagram.md`
- `docs/alibaba_cloud_deployment_proof.md`
- `docs/demo_video_capture_plan.md`
- `docs/demo_terminal_capture_bundle.md`
- `docs/devpost_submission_answers.md`
- `docs/final_submission_checklist.md`
- `docs/public_repo_safety_review.md`
- `docs/qwen_api_smoke_report.md`
- `docs/qwen_rule_memory_demo_trace.md`
- `docs/rule_memory_schema.json`
- `docs/rule_memory_live_seed_20260607.json`
- `docs/rule_memory_readiness_packet.md`
- `docs/FOUNDER_SHIP_STEPS.md`

## Exclude

- `.env`
- shell history
- provider auth files
- account exports
- raw private logs
- temporary files under `/tmp`
- workspace-level control tower internals unless summarized
- files containing API keys, tokens, cookies, private keys, or personal account credentials
- Korean/internal baseline drafts that are superseded by public docs:
  - `docs/rule_memory_infrastructure.md`
  - `docs/rule_memory_readiness_checklist.md`

## Secret Scan

The staging bundle was scanned for raw key/token/private-key material and for
private workspace endpoints. The private workspace MaaS host that appeared in
cached traces was replaced with the placeholder
`your-workspace-id.ap-southeast-1.maas.aliyuncs.com`. Internal workspace paths
(`control_tower/...`, `qwen_cloud_hackathon_2026/...`) were rewritten to
repo-relative paths. No raw secret material remains.

Before publish, run from the staging repo root:

```bash
grep -REn "sk-[A-Za-z0-9]|Authorization: Bearer [A-Za-z0-9._-]{8}|-----BEGIN|client_secret|ws-[a-z0-9]{16}\.[a-z0-9-]+\.maas" . \
  --include='*.md' --include='*.json' --include='*.sh' --include='*.py'
```

Expected result: no matches containing real secrets or private workspace hosts.
(The placeholder `your-workspace-id` is safe and expected.)

## Devpost Risk Notes

- The package has Qwen API proof and a Qwen-backed demo trace.
- The package has code-file proof for Qwen/Alibaba Cloud API usage.
- The final Devpost submission still needs a deployed-runtime recording and public repo URL.
- The architecture diagram is currently text/Mermaid; convert to PNG/SVG if the submission form expects an image upload.

## Public Repo Name

Recommended: `rulememory-qwen-agent`

Reason:

- short
- track-aligned
- not tied to private workspace names
- clearly signals Qwen MemoryAgent purpose
