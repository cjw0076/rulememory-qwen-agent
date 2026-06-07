# Founder Ship Steps (RuleMemory -> Qwen Cloud Hackathon)

Everything else is done. This file is the only thing you need to follow.
Three founder-only gates remain: (A) publish the public GitHub repo,
(B) record the demo video, (C) submit on Devpost.

All commands assume you start from this staging directory:

```bash
cd /home/user/workspaces/jaewon/dacon/competitions/qwen_cloud_hackathon_2026/public_repo_staging/rulememory-qwen-agent
```

---

## 0. 30-second pre-flight (optional but recommended)

```bash
# code compiles, JSON valid, shell valid
python3 -m py_compile deploy/alibaba_cloud/qwen_maas_client.py scripts/rule_memory_local_demo.py
python3 -m json.tool docs/rule_memory_live_seed_20260607.json >/dev/null && echo "json ok"
bash -n scripts/*.sh && echo "shell ok"

# no real secrets / no private workspace host (placeholder your-workspace-id is fine)
grep -REn "sk-[A-Za-z0-9]{8}|-----BEGIN|client_secret|ws-[a-z0-9]{16}\.[a-z0-9-]+\.maas" . \
  --include='*.md' --include='*.json' --include='*.sh' --include='*.py' \
  | grep -v "your-workspace-id" || echo "secret scan clean"

# no stray python caches
find . -name '__pycache__' -o -name '*.pyc' | grep . && echo "REMOVE THESE" || echo "no caches"
```

Expected: `json ok`, `shell ok`, `secret scan clean`, `no caches`.

---

## A. Publish the public GitHub repo

`gh` 2.45 is installed and the git identity is already
`cjw0076 <cjw070690@gmail.com>`. Copy-paste this whole block:

```bash
cd /home/user/workspaces/jaewon/dacon/competitions/qwen_cloud_hackathon_2026/public_repo_staging/rulememory-qwen-agent

# 1. init a fresh, isolated repo for ONLY this bundle
rm -rf .git
git init -b main

# 2. stage + commit (.gitignore already excludes caches/.env)
git add .
git commit -m "RuleMemory: Qwen-powered MemoryAgent for Qwen Cloud Hackathon"

# 3. create the PUBLIC repo on GitHub and push in one shot
gh repo create rulememory-qwen-agent \
  --public \
  --source=. \
  --remote=origin \
  --description "RuleMemory: a Qwen Cloud MemoryAgent that remembers contest rules, deadlines, source evidence, and stale assumptions across sessions." \
  --push
```

Then capture the URL (you will paste it into Devpost):

```bash
gh repo view --json url -q .url
# -> https://github.com/<your-username>/rulememory-qwen-agent
```

Confirm it is public and the MIT LICENSE renders at the repo root:

```bash
gh repo view --json visibility,name -q '.visibility + " " + .name'   # expect: PUBLIC rulememory-qwen-agent
```

Open the URL in a browser and verify the README renders and `LICENSE` shows
"MIT" in GitHub's license badge.

---

## B. Runtime-proof URL steps (Qwen Cloud usage proof)

The repo already ships cached, verified proof (`docs/qwen_api_smoke_report.md`,
`docs/qwen_rule_memory_demo_trace.md`) marked as cached. To produce a FRESH,
linkable runtime proof for judges, run the live demo once with your own key and
let it write a new trace, then either (i) point Devpost at the committed trace
file URL, or (ii) capture it in the video (Section C).

```bash
# use YOUR Qwen Cloud key + YOUR workspace MaaS base URL (never commit these)
export QWEN_API_KEY="<your-qwen-cloud-key>"
export QWEN_OPENAI_BASE_URL="https://<your-workspace-id>.<region>.maas.aliyuncs.com/compatible-mode/v1"

# 1. smoke: prove the endpoint answers HTTP 200
./scripts/qwen_api_smoke.sh        # expect status=200 on both models + chat

# 2. live RuleMemory demo: Qwen reads the seed, writes a fresh trace
./scripts/qwen_rule_memory_demo.sh # prints path to docs/qwen_rule_memory_demo_trace.md

# 3. code-file proof client (Alibaba Cloud / Qwen MaaS)
python3 deploy/alibaba_cloud/qwen_maas_client.py --seed docs/rule_memory_live_seed_20260607.json
# expect "http_status": 200
```

If you regenerated the trace and want the fresh one public, re-run the
pre-flight secret scan (Section 0) to confirm your real host did NOT get written
(the script sanitizes, but verify), then:

```bash
git add docs/qwen_rule_memory_demo_trace.md docs/rule_memory_readiness_packet.md
git commit -m "Refresh live Qwen runtime proof"
git push
```

Runtime-proof URLs to use on Devpost:

- Smoke proof: `https://github.com/<your-username>/rulememory-qwen-agent/blob/main/docs/qwen_api_smoke_report.md`
- Live trace:  `https://github.com/<your-username>/rulememory-qwen-agent/blob/main/docs/qwen_rule_memory_demo_trace.md`
- Code-file proof: `https://github.com/<your-username>/rulememory-qwen-agent/blob/main/deploy/alibaba_cloud/qwen_maas_client.py`

IMPORTANT: if the live trace was regenerated, double-check it does NOT contain
your real `ws-...maas.aliyuncs.com` host before pushing. The script translates
non-ASCII but does not redact the host you export, so blur/redact it in the
video or revert to the cached placeholder trace before committing.

---

## C. Demo video recording script (<= 3 minutes, read off directly)

Setup before you hit record:
- Open one clean terminal in this directory. Clear scrollback (`clear`).
- Have your key already exported in THIS shell, but do NOT echo it on screen.
- Have these files open in a viewer/editor in separate tabs ready to switch to:
  `docs/rule_memory_live_seed_20260607.json`,
  `docs/qwen_rule_memory_demo_trace.md`,
  `docs/rule_memory_readiness_packet.md`.

Shot list (timecodes are targets):

| Time | On screen | Say (verbatim) |
|---|---|---|
| 0:00-0:15 | README.md title | "This is RuleMemory, a MemoryAgent built on Qwen Cloud. It remembers competition rules, deadlines, source evidence, and stale assumptions across sessions, so teams stop re-reading chat history." |
| 0:15-0:40 | `rule_memory_live_seed_20260607.json` | "Memory is stored as auditable entries: a deadline, the chosen track, the Qwen API proof, and the next decision. Each entry carries source references, a confidence score, and a stale-after window." |
| 0:40-1:15 | Terminal: type `./scripts/qwen_rule_memory_demo.sh` and run | "Now I run the demo. It sends the memory seed to a Qwen model through Qwen Cloud's OpenAI-compatible endpoint. Qwen is the core runtime here, not decoration." |
| 1:15-1:55 | `qwen_rule_memory_demo_trace.md` (HTTP 200 + Qwen output) | "Qwen returns three things: the remembered facts, a stale-risk warning that this source expires within twenty-four hours, and the next builder action. That stale warning is the memory payoff: the agent catches drift a human would miss." |
| 1:55-2:25 | `rule_memory_readiness_packet.md` | "The agent then writes a readiness packet. This is the hand-off artifact: the next session, or the next teammate, continues from here instead of re-deriving everything." |
| 2:25-2:50 | Terminal: `python3 deploy/alibaba_cloud/qwen_maas_client.py --seed docs/rule_memory_live_seed_20260607.json` showing `"http_status": 200` | "And here is the same Qwen Cloud call from the deployable client file, returning HTTP 200, with no secrets written." |
| 2:50-3:00 | GitHub repo page (public, MIT) | "Everything is open source under MIT at this repo. RuleMemory: persistent, source-linked, Qwen-powered memory for shipping teams." |

Recording rules:
- Never show the API key. If you exported it earlier in the same shell, do NOT
  scroll up. Keep `export QWEN_API_KEY=...` off-screen.
- If your real workspace host appears in any trace, blur it or use the cached
  placeholder trace instead.
- Keep it under 3:00. Upload to YouTube (unlisted is acceptable for Devpost) or
  the Devpost video field, and copy the URL.

---

## D. Devpost submission (final gate)

1. Log in to https://qwencloud-hackathon.devpost.com/ and start a submission.
2. Fill every field from `docs/devpost_submission_answers.md` (title, tagline,
   description, what-it-does, how-built, Qwen usage, challenges, etc.).
3. Track: **MemoryAgent**.
4. Paste the links you collected:
   - Public repo URL (Section A)
   - Demo video URL (Section C)
   - Runtime-proof file URLs (Section B)
5. If Devpost requires an image upload, render `docs/architecture_diagram.md`
   (the Mermaid block) to PNG/SVG and attach it.
6. Verify every link opens in a logged-out/incognito window (proves public).
7. Submit before the freeze: internal target **2026-07-08 KST**, hard deadline
   **2026-07-09 14:00 PT**.

---

## Status snapshot

- Build, schema, scripts, docs, proofs: DONE and validated.
- Bundle is secret-safe and self-contained (no internal workspace paths/hosts).
- Founder-only remaining: create the public repo (A), record the video (C),
  submit on Devpost (D). Optional fresh runtime proof (B).
