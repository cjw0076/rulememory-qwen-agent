# Qwen Final Submission Checklist

Updated: 2026-06-07 KST

## Ready

- [x] Track selected: MemoryAgent
- [x] Project title: RuleMemory
- [x] Public repo name selected: `rulememory-qwen-agent`
- [x] License selected: MIT
- [x] Qwen Cloud API proof: `docs/qwen_api_smoke_report.md`
- [x] Qwen-backed demo trace: `docs/qwen_rule_memory_demo_trace.md`
- [x] Terminal capture bundle: `docs/demo_terminal_capture_bundle.md`
- [x] Architecture diagram: `docs/architecture_diagram.md`
- [x] Alibaba/Qwen code-file proof: `deploy/alibaba_cloud/qwen_maas_client.py`
- [x] Deployment proof note: `docs/alibaba_cloud_deployment_proof.md`
- [x] Public README draft: `docs/public_readme_draft.md`
- [x] Devpost answers draft: `docs/devpost_submission_answers.md`
- [x] Public repo safety review: `docs/public_repo_safety_review.md`

## Needs External Upload Or Session

- [ ] Public GitHub repository URL
- [ ] Final deployed Alibaba Cloud runtime recording URL
- [ ] Final 3-minute public demo video URL
- [ ] Architecture diagram rendered image upload if Devpost requires image file
- [ ] Devpost login/session
- [ ] Final submit confirmation

## Pre-Submit Commands

Run from `qwen_cloud_hackathon_2026`:

```bash
python3 -m py_compile deploy/alibaba_cloud/qwen_maas_client.py
python3 -m json.tool docs/rule_memory_live_seed_20260607.json >/tmp/qwen_live_seed_validate.json
bash -n scripts/qwen_api_smoke.sh scripts/qwen_rule_memory_demo.sh scripts/capture_demo_bundle.sh
rg -n "sk-ws-H|Authorization: Bearer [A-Za-z0-9._-]+|private_key|client_secret|TOKEN=|SECRET=|COOKIE=" .
```

Expected result:

- compile passes
- JSON validates
- shell syntax passes
- secret scan has no real secret matches

## Submission Order

Follow `docs/FOUNDER_SHIP_STEPS.md` for exact copy-paste commands. Summary:

1. Create public repo and push this bundle (`gh repo create ... --public --push`).
2. Confirm MIT license renders at repo root.
3. Optionally regenerate fresh Qwen runtime proof with your own key.
4. Record final 3-minute demo video using the shot list in `docs/FOUNDER_SHIP_STEPS.md`.
5. Fill Devpost using `docs/devpost_submission_answers.md`.
6. Verify all links open in an incognito window (public).
7. Submit under MemoryAgent track before the 2026-07-09 14:00 PT deadline.
