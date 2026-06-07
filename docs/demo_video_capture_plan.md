# RuleMemory 3-Minute Demo Capture Plan

Updated: 2026-06-07 KST

## Goal

Show that RuleMemory is a real MemoryAgent: it uses Qwen, remembers rules across
sessions, flags stale source risk, and produces a practical readiness packet.

## Required Captures

1. Terminal setup with secret-safe environment placeholders.
2. `scripts/qwen_rule_memory_demo.sh` running successfully.
3. `docs/qwen_rule_memory_demo_trace.md` showing `HTTP 200` and Qwen output.
4. `docs/rule_memory_live_seed_20260607.json` showing persisted memory entries.
5. `docs/rule_memory_readiness_packet.md` showing refreshed packet output.
6. Public package checklist showing remaining Devpost/Alibaba proof items.

## Timeline

### 0:00-0:20 Problem

Competition teams lose rules, deadlines, source provenance, and stale
assumptions across chat sessions.

### 0:20-0:45 Memory Seed

Show `rule_memory_live_seed_20260607.json`.

Narration:

```text
RuleMemory stores deadline, track choice, Qwen API proof, and next package
decision as persistent memory entries with source references.
```

### 0:45-1:25 Live Qwen Call

Run:

```bash
QWEN_API_KEY=... \
QWEN_OPENAI_BASE_URL=https://<workspace-host>/compatible-mode/v1 \
./scripts/qwen_rule_memory_demo.sh
```

Narration:

```text
The demo calls Qwen through the workspace MaaS OpenAI-compatible endpoint.
Qwen reads the memory seed and returns remembered facts, stale-risk warning,
and next builder action.
```

### 1:25-2:05 Output Trace

Show `qwen_rule_memory_demo_trace.md`.

Highlight:

- `status: HTTP 200`
- remembered deadline
- MemoryAgent track
- stale source warning
- next builder action

### 2:05-2:35 Readiness Packet

Show `rule_memory_readiness_packet.md`.

Narration:

```text
The readiness packet is the artifact a builder or submitter can continue from
without rereading the whole chat history.
```

### 2:35-3:00 Submission Fit

Show `public_package_checklist.md`.

Narration:

```text
The next package steps are public README, architecture diagram, Alibaba Cloud
deployment proof, license, and Devpost track submission.
```

## Capture Rules

- Never show real API keys.
- Blur terminal history if a secret was visible earlier.
- Use placeholders for environment variables.
- Do not show private workspace paths outside sanitized docs.
- Keep final video public-safe and under about 3 minutes.

## Current Evidence

- `docs/demo_terminal_capture_bundle.md`
- `docs/qwen_rule_memory_demo_trace.md`
- `docs/qwen_api_smoke_report.md`
- `docs/rule_memory_readiness_packet.md`
- `docs/public_package_checklist.md`
