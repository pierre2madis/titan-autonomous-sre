# TITAN — n8n / AWX Remote Diagnostic Integration

**Status:** Technical preview — nominal execution validated; failure handling and resilience hardening in progress.
**Scope:** Phase 1 Linux diagnostic orchestration; read-only intent.
**Publication:** Draft only. No deployment or public release is implied.

## Purpose

This integration connects TITAN's evidence-oriented SRE workflow with n8n orchestration, AWX job execution, and Ansible execution statistics. It produces structured, correlated JSON for downstream incident analysis. It is **not** an automated root-cause determination or a remediation authorization mechanism.

## Architecture

```text
Manual Trigger (n8n)
  -> AWX Job Template Launch (HTTP POST)
  -> AWX Job Status (HTTP GET)
  -> Wait / bounded polling
  -> terminal-state decision
     -> successful + event processing complete
        -> normalize job metadata
        -> fetch playbook_on_stats event
        -> correlate and enrich evidence
     -> failed/error/canceled: failure handling [NOT YET COMPLETE]
     -> polling limit: Stop and Error [configured; negative test pending]
  -> TITAN JSON evidence (downstream ingestion not yet claimed)
```

TITAN remains **Bash-first** for Linux/eBPF evidence collection. n8n/AWX is an optional orchestration and remote-diagnostics layer; monitored hosts do not require Splunk or Dynatrace.

## Validated observations

- AWX Job **9**, template **8**: `successful`; elapsed 6.343 seconds; one host OK, two tasks; event **77** (`playbook_on_stats`), `ok=2`, `changed=0`, `failures=0`, `dark=0`.
- AWX Job **10**, template **8**: `successful`; elapsed 6.651 seconds; one host OK, two tasks; event **87** (`playbook_on_stats`), `ok=2`, `changed=0`, `failures=0`, `dark=0`.
- Correlated evidence JSON returned `quality=VALID` and `ansible_stats_verified=true` for the nominal path.
- An earlier run was interrupted while the n8n server was unresponsive; the server was restarted and the task rerun. The cause and exact failure mode were **not established**. Do not classify this as an AWX or Ansible failure without further evidence.
- `changed=0` means Ansible reported no changes; it does **not** independently prove the absence of side effects.

## Contents

- `docs/ARCHITECTURE.md` — workflow, dependencies, and data flow
- `docs/SECURITY.md` — credential, transport, and read-only controls
- `docs/VALIDATION.md` — observations, limitations, and next gates
- `docs/SETUP.md` — safe, environment-neutral configuration guide
- `contracts/awx-evidence-v1.schema.json` — draft JSON Schema
- `examples/awx-evidence-success.json` — sanitized sample (fictional IDs/timestamps)
- `tests/validate-evidence.sh` — local schema/example sanity checks (jq; no network)

## Reproduction overview

1. Provision n8n and AWX separately; ensure the network path is secured.
2. Configure a least-privilege AWX API identity and n8n credential store; never paste secrets into exported workflows.
3. Create a diagnostic-only AWX job template and inventory with approved SSH host verification.
4. Build the polling and evidence-normalization nodes described in `docs/ARCHITECTURE.md`.
5. Validate a nominal job and `playbook_on_stats` event, then exercise negative cases **without launching additional jobs** where feasible.

**Not included:** live workflow export, credentials, IP addresses, SSH keys, host inventories, private URLs, or public publication approval. An n8n export should be added only after manual secret/metadata review.

## Release gate

This preview is suitable for review as a **draft**. Before calling it production-ready: complete failure/timeout branches, verify restart/retry behavior, enforce target allowlists and task-level read-only policy, and independently assess security configuration.
