# TITAN — Autonomous SRE RCA Platform

**Public Preview v0.1.0**

TITAN is an evidence-driven Site Reliability Engineering project
focused on cross-domain event normalization, causal correlation,
and incident relationship assessment.

This initial public preview provides two portable Bash components:

- Cross-Domain Event Normalizer
- Cross-Domain Correlation Engine

The project demonstrates how infrastructure evidence can be
correlated with downstream service degradation while respecting
temporal ordering, topology constraints, and causal rule eligibility.

## Key Capabilities

- Canonical cross-domain event representation
- Rule-based causal correlation
- Temporal propagation validation
- Topology-aware relationship assessment
- Evidence-based scoring
- Incident relationship recommendations
- Deterministic JSON fixtures
- Offline demonstrations without production monitoring services

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
     Causal Correlation Engine
                |
                +---- Causal Rule Registry
                |
                v
    Relationship Assessment JSON
                |
                v
     Advisory Incident Decision
```

The initial preview includes the normalizer and correlation engine.
It does not include every upstream adapter or a complete
production incident-management pipeline.

## Requirements

- Linux
- Bash
- jq
- sha256sum
- date

## Offline Demonstration

Run:

```bash
bash scripts/demo_causal_correlation.sh
```

The demonstration evaluates two scenarios:

### Scenario A — Temporal Causality Rejected

CPU scheduler contention is correlated with Splunk indexing
degradation, but the causal direction is invalid.

Expected relationship:

```text
CORRELATED_WITH
```

### Scenario B — Positive Causal Relationship

Block I/O queue contention precedes Splunk indexing degradation
by 60 seconds.

Expected relationship:

```text
CAUSE_OF
```

The positive scenario is checked against an existing golden
contract for the causal relationship, rule eligibility, scoring,
temporal validation, topology, and incident recommendation.

## Safety Model

TITAN distinguishes evidence correlation from causal eligibility.

Incident recommendations in this preview are advisory only.

The offline demonstration does not require Splunk, Dynatrace,
n8n, AWX, ServiceNow, or PagerDuty.

No production remediation workflow is included in this release.

## Project Status

Version: 0.1.0

Release type: Public Preview

Scope: Offline normalization and causal correlation components.

This release is not represented as a production-ready
autonomous remediation platform.

## Engineering Provenance

This project was developed through an iterative engineering
process involving requirements definition, Bash implementation,
testing, debugging, evidence validation, and release verification,
with assistance from ChatGPT.

The project owner directed the engineering requirements,
integration decisions, testing, and validation activities.

## License

Apache License 2.0.

See [LICENSE](LICENSE).

Redistribution rights for all included materials must be
confirmed before public publication.
