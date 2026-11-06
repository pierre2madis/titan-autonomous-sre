# TITAN Multi-Signal Incident Correlation v0.1

## Purpose

Demonstrate synthetic temporal association between an upstream
CPU pressure incident (T1) and a downstream Splunk ingestion
pressure event (T2).

The prototype attaches the downstream event to the existing
parent incident rather than creating a second independent incident.

## Correlation policy

- Parent signal: CPU_PSI_PRESSURE
- Child signal: SPLUNK_INGESTION_PRESSURE
- Correlation window: 300 seconds
- Host identity must match
- Parent observation must precede the child
- Parent incident must be active
- Relationship: TEMPORALLY_ASSOCIATED
- Causality confirmed: false

## Components

- multisignal_correlation_v0_1.json:
  correlation policy contract
- generate_scenarios_v0_1.py:
  synthetic scenario generator
- multisignal_correlator_v0_1.py:
  stateless correlation evaluation
- multisignal_graph_v0_1.py:
  persistent parent-child incident graph
- multisignal_parent_guard_v0_1.py:
  authoritative CPU parent-state validation

## Verified behavior

- Same-host correlation within the configured window
- Rejection of different-host and out-of-window events
- Rejection of events preceding the parent
- Rejection of resolved parents
- Child-event replay deduplication
- Parent and child identity conflict rejection
- Persistent graph integrity
- Concurrent child attachment without lost updates
- Parent-state verification under a cooperative CPU lock
- Rejection after parent resolution without graph mutation

## Concurrency model

The parent guard acquires the CPU state lock before invoking
the graph engine, which acquires the graph state lock.

Required lock order:

CPU_STATE_LOCK -> GRAPH_STATE_LOCK

All participating writers must respect this protocol.

## Limitations

This is a synthetic, local proof of concept.

It does not establish CPU-to-ingestion causality.

It does not collect real Splunk ingestion telemetry or require
Splunk, Dynatrace, n8n, AWX, or Prometheus services.

The implementation does not yet provide:

- Distributed locking
- A global child-event identity index across incidents
- End-to-end crash-consistent multi-file transactions
- Production-grade state schema migration
- Full TITAN incident lifecycle integration
- Automated remediation

The race test simulates parent resolution while holding the
CPU lock. It does not exercise the complete CPU decision
engine during that concurrent transition.

## Safety

- Synthetic evidence only
- No Splunk API calls
- No automatic remediation
- No service start or stop
- No external publication

## Engineering statement

Designed and validated a persistent synthetic multi-signal
incident correlation prototype with temporal association,
idempotency, parent-state consistency, and cooperative
concurrency safeguards.

## Global Child Identity Integrity

The incident graph enforces global child-event ownership within a
single persistent graph file.

### Ownership rules

- A child event ID can belong to only one parent incident.
- An identical child ID under another incident is rejected with
  `GLOBAL_CHILD_EVENT_CONFLICT`.
- Ownership validation executes while holding the graph file lock.
- Rejected ownership conflicts do not modify the persisted graph.
- Existing replay idempotence and parent identity checks remain active.

### Validation

- 06G-1: Cross-incident collision reproduced.
- 06G-2: Global ownership enforcement and regression tests passed.
- 06G-3: Concurrent competing attachments resulted in one accepted
  attachment and one rejected attachment.
- 06G-4: Rejected collision preserved the graph SHA-256.

### Scope and limitations

This implementation provides local graph-level uniqueness.

It does not provide:

- Distributed uniqueness across independent graph files or hosts.
- Distributed locking or consensus.
- Atomic transactions spanning CPU state and graph state.
- Confirmed causality between CPU pressure and ingestion pressure.
- Production telemetry ingestion or automatic remediation.

The relationship remains `TEMPORALLY_ASSOCIATED`, with
`causality_confirmed=false`.
