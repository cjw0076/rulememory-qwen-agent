# Devpost Submission Answers Draft

Updated: 2026-06-07 KST

## Track Selection

- Track: MemoryAgent
- Rationale: RuleMemory persists rules, deadlines, stale assumptions, Qwen proof,
  and submission readiness across sessions, then uses Qwen to recall and update
  those memories.

## Project Title

RuleMemory

## Tagline

A Qwen-powered MemoryAgent that remembers rules, deadlines, stale assumptions,
and source evidence so teams can submit with fewer missed requirements.

## Short Description

RuleMemory is a MemoryAgent for competition and launch teams. It stores
deadline, eligibility, track, source freshness, and package-readiness facts as
auditable memory entries, then uses Qwen Cloud to recall key facts, identify
stale-risk warnings, and produce a handoff-ready readiness packet.

## What It Does

RuleMemory turns fragile chat context into persistent operational memory. It:

- stores official-source facts and operator receipts as RuleMemory entries
- keeps source references, confidence, status, and stale-check policy per entry
- calls Qwen through the Qwen Cloud MaaS OpenAI-compatible endpoint
- asks Qwen to recall remembered facts, stale-risk warnings, and next actions
- emits a refreshed readiness packet and terminal demo trace
- keeps public package assets secret-free

## How We Built It

- Qwen Cloud MaaS OpenAI-compatible endpoint for model calls
- `qwen-plus` for the current demo path
- JSON RuleMemory seed/store
- shell demo runner for Qwen-backed terminal proof
- Python Qwen MaaS client as Alibaba/Qwen code-file proof
- Markdown readiness packet, architecture diagram, and public package checklist

Core artifacts:

- `scripts/qwen_rule_memory_demo.sh`
- `deploy/alibaba_cloud/qwen_maas_client.py`
- `docs/rule_memory_live_seed_20260607.json`
- `docs/rule_memory_readiness_packet.md`
- `docs/qwen_rule_memory_demo_trace.md`
- `docs/architecture_diagram.md`
- `docs/alibaba_cloud_deployment_proof.md`

## Qwen Cloud Usage

The project uses Qwen Cloud as a central runtime dependency, not a decorative
call. The demo runner sends a compact RuleMemory seed to Qwen and receives:

- remembered facts
- stale-risk warning
- next builder action

The code-file proof client also calls the Qwen Cloud MaaS OpenAI-compatible
chat completion endpoint with the same live memory seed.

## MemoryAgent Fit

RuleMemory matches the MemoryAgent track because the product focus is persistent
memory over cross-session operation:

- remembers deadlines and track choices
- remembers cloud proof status and package decisions
- flags stale official-source assumptions
- allows a future builder or submitter to continue from a readiness packet
  instead of rereading prior chat history

## What Is New

RuleMemory is not a generic checklist. It uses source-linked memory entries and
Qwen recall to keep submission state current across sessions. The key novelty
is the operational memory loop: ingest source facts, persist memory, call Qwen
to recall and warn, then emit an auditable readiness packet for the next agent.

## Challenges

- The first Qwen smoke path failed because the default endpoint did not match
  the operator-provided workspace key.
- The working route required the workspace MaaS OpenAI-compatible endpoint.
- Public packaging needed strict secret boundaries because API keys, provider
  credentials, raw logs, and private workspace paths must stay out of public
  artifacts.

## Accomplishments

- Verified live Qwen model access with `HTTP 200` models and chat probes.
- Built a Qwen-backed RuleMemory demo runner.
- Created a live RuleMemory seed and readiness packet.
- Added a public package checklist, architecture diagram, MIT license, and
  public repo safety review.
- Added Alibaba/Qwen Cloud code-file proof client.
- Generated a secret-safe terminal capture bundle for the demo video.

## What We Learned

Qwen workspace keys may require the workspace-specific MaaS base URL. Once the
correct endpoint is used, a small RuleMemory seed is enough for Qwen to produce
useful remembered facts, stale-risk warnings, and next actions.

## What's Next

- Capture final deployed Alibaba Cloud runtime recording.
- Publish the public repository as `rulememory-qwen-agent`.
- Record/upload the final 3-minute demo video.
- Submit to Devpost under the MemoryAgent track.
- Extend RuleMemory from JSON seed to a small service with source refresh jobs.

## Links To Fill Before Submit

- Public repository URL: `TODO`
- Demo video URL: `TODO`
- Alibaba Cloud deployed runtime recording/proof URL: `TODO`
- Architecture diagram image URL or upload: `TODO`
- Blog/social post URL: optional

## Judging Criteria Mapping

| Criterion | RuleMemory evidence |
|---|---|
| Technical Depth & Engineering | Qwen MaaS client, RuleMemory schema, source freshness, readiness packet pipeline |
| Innovation & AI Creativity | Qwen recall over persistent operational memory and stale-risk warnings |
| Problem Value & Impact | Prevents missed requirements and stale assumptions in real competition/package workflows |
| Presentation & Documentation | Public README draft, architecture diagram, demo capture bundle, Devpost answer draft |
