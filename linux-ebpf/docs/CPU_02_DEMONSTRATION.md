# TITAN CPU-02 — Evidence-Driven Incident Demonstration

## Overview

CPU-02 is a deterministic synthetic CPU pressure scenario.

It exercises three independent decision evaluations:

- BASELINE: normal operating conditions
- INJECTION: CPU scheduling pressure
- RECOVERY: return to normal conditions

All observations are synthetic and scenario-authored.

## Architecture

Synthetic CPU Scenario
  -> Evidence Enrichment
  -> Native CPU Evidence Adapter
  -> CPU Decision Integrator
  -> CPU Decision Bridge
  -> CPU Decision Model
  -> Operational Conclusion
  -> JSON Demonstration Report

## Evidence and Results

| Metric | Baseline | Injection | Recovery |
|---|---:|---:|---:|
| CPU utilization | 12% | 38% | 14% |
| CPU PSI some avg10 | 0.5% | 35% | 1% |
| Run queue p95/core | 0.4 | 4.2 | 0.5 |
| Scheduler latency p99 | 1.5 ms | 65 ms | 2 ms |

| Phase | Severity | Problem Type | Incident Recommended |
|---|---|---|---|
| BASELINE | NORMAL | NONE | No |
| INJECTION | DEGRADED | CPU_PSI_PRESSURE | Yes |
| RECOVERY | NORMAL | NONE | No |

## Reproduction

Run from the repository root:

    bash linux-ebpf/demo/run_cpu_demo_v0_1.sh

The launcher creates an isolated temporary directory containing
synthetic observations, native evidence, calculated decisions,
and a JSON demonstration report.

## Dependencies

- Bash
- Python 3
- jq
- TITAN CPU Decision Integrator v1.0.0 candidate
- TITAN CPU Decision Bridge v1.0.0 candidate
- TITAN CPU Decision Model v1.0.2 candidate

The decision components are currently expected under
/usr/local/bin and are not bundled in this mini-project.

The full demonstration therefore requires a compatible
TITAN environment.

## Validation

- Synthetic scenario contract: PASS
- Native evidence adapter: PASS
- Real decision engine integration: PASS
- JSON demonstration report: PASS

Observed decision sequence:

    NORMAL -> DEGRADED -> NORMAL

## Scope and Limitations

This demonstration validates independent CPU decision
classifications using synthetic evidence.

It does not demonstrate:

- A production CPU incident
- Persistent incident lifecycle management
- Root cause confirmation from live telemetry
- Automated remediation
- Application SLO recovery

The RECOVERY phase means that the decision model classified
the final synthetic observation as NORMAL.

It does not prove that a persistent incident was resolved.

## Safety

The demonstration does not intentionally generate CPU load,
restart Splunk, or publish synthetic metrics to node_exporter.

It invokes local TITAN decision components with temporary
synthetic evidence.

## Engineering Value

CPU-02 demonstrates why CPU utilization alone is insufficient
for identifying scheduling pressure.

The decision engine combines CPU PSI, run queue depth,
and scheduler latency to classify operational pressure.
