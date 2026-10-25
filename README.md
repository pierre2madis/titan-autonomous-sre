# TITAN — Autonomous SRE RCA Platform

**Evidence-Driven Incident Correlation & Causal Analysis**

**Release:** v0.1.0 — Initial Public Preview
**License:** Apache 2.0
**Status:** Offline engineering preview — Not production-ready

[GitHub Repository](https://github.com/pierre2madis/titan-autonomous-sre) |
[v0.1.0 Release](https://github.com/pierre2madis/titan-autonomous-sre/releases/tag/v0.1.0)

## Why TITAN?

Modern observability platforms can generate multiple alerts from a
single underlying infrastructure problem.

CPU contention, storage latency, and downstream service degradation
may appear as separate incidents even when they are related.

Investigating these symptoms independently can increase alert noise,
complicate incident triage, and delay recovery.

**TITAN explores how SRE teams can move beyond alert correlation
toward evidence-driven causal analysis.**

The approach combines temporal ordering, infrastructure topology,
configurable causal rules, and evidence confidence.

The goal is to distinguish plausible causal relationships from
coincidental or temporally invalid correlations.

## What Is Available in v0.1.0?

The initial public release provides two Bash-based components.

### Cross-Domain Event Normalizer

Transforms validated observability inputs into canonical event JSON.

Capabilities include:

- Canonical cross-domain event representation
- Evidence state and confidence metadata
- Infrastructure and application domain classification
- Incident contribution hints
- Input contract validation
- Deterministic processing

### Cross-Domain Correlation Engine

Evaluates relationships between canonical events using:

- Temporal ordering and propagation constraints
- Topology-aware relationship assessment
- Configurable causal rules
- Evidence-based scoring
- Rule eligibility validation
- Advisory incident relationship recommendations

The engine produces explainable relationship assessments.

It does not establish definitive root cause or execute remediation.

## Architecture

```text
Infrastructure / Service Evidence
               |
               v
       Domain Adapter Output
               |
               v
    Cross-Domain Event Normalizer
               |
               v
       Canonical Event JSON
               |
               v
     Causal Correlation Engine <--- Causal Rule Registry
               |
               v
    Relationship Assessment JSON
               |
               v
     Advisory Incident Decision
```

The normalizer and correlation engine are included in v0.1.0.

Upstream production adapters and the complete incident-management
pipeline are outside the scope of this release.

## Quick Start

### Requirements

- Linux
- Bash
- jq
- GNU-compatible command-line utilities, including:
  - sha256sum
  - date
  - awk
  - sed
  - tr

### Clone the repository

```bash
git clone https://github.com/pierre2madis/titan-autonomous-sre.git
cd titan-autonomous-sre
git checkout v0.1.0
```

### Run the offline demonstration

```bash
bash scripts/demo_causal_correlation.sh
```

The demonstration evaluates two predefined scenarios and validates
their expected outcomes.

No Splunk, Dynatrace, Prometheus, n8n, AWX, ServiceNow, or PagerDuty
installation is required.

## Demonstration Scenarios

### Scenario A — Invalid Causal Direction

CPU scheduler contention and Splunk indexing degradation are
correlated, but their temporal relationship does not support
the proposed causal direction.

Expected relationship:

```text
CORRELATED_WITH
```

This demonstrates that temporal correlation alone is insufficient
to establish a directional causal relationship.

### Scenario B — Eligible Causal Relationship

Block I/O queue contention precedes Splunk indexing degradation
by 60 seconds.

The configured rule, temporal constraints, topology, and evidence
assessment support an eligible directional relationship.

Expected relationship:

```text
CAUSE_OF
```

This is an advisory classification, not definitive root-cause proof.

## Verification and Testing

The initial public release has undergone independent verification:

- Nine correlation golden fixtures reproduced successfully
- 58 semantic assertions passed across correlation scenarios
- Deterministic normalizer processing checks
- Offline demonstration successfully executed
- Bash syntax and JSON fixture validation
- Repository integrity and dependency availability reviews

These results describe the verified preview behavior.

They do not establish production readiness or comprehensive
security assurance.

## Safety Model

TITAN distinguishes correlation from causal eligibility.

The v0.1.0 correlation engine provides advisory recommendations only.

The release does not automatically:

- Create production incidents
- Trigger remediation playbooks
- Modify monitored infrastructure
- Execute production notification workflows

No autonomous remediation pipeline is included in this preview.

## Roadmap

The broader TITAN architecture is intended to incorporate:

### Observability and Evidence

- Prometheus and Alertmanager
- Splunk and Dynatrace integrations
- Linux and eBPF evidence collection
- Cross-domain evidence normalization

### Incident Intelligence

- Event correlation and deduplication
- Incident lifecycle management
- Causal relationship assessment
- SLI/SLO-based decision gates

### Automation

- n8n orchestration
- ServiceNow incident management
- PagerDuty and Slack notifications
- Ansible AWX remediation workflows

These are future integration objectives and are not represented
as operational capabilities of the v0.1.0 public release.

## Engineering Provenance

TITAN is an independently directed engineering project developed
through iterative requirements definition, architecture design,
Bash implementation, debugging, deterministic testing,
evidence validation, and release verification.

ChatGPT has been used as an AI-assisted engineering tool
throughout development.

The project owner directs engineering requirements, architecture
and integration decisions, validation activities, and publication.

## Project Status

**Current public release:** v0.1.0 — Initial Public Preview

The next milestone focuses on security hardening, robustness,
documentation improvements, and preparation for broader
observability integrations.

## License

Licensed under the Apache License, Version 2.0.

See [LICENSE](LICENSE).

Component provenance and third-party redistribution obligations
remain subject to review. The presence of an Apache 2.0 license
does not independently establish rights over third-party materials.
