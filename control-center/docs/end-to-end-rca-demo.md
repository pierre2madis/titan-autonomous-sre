# TITAN Control Center — Evidence-Bounded Incident RCA Demonstration

## Purpose

This reproducible, read-only demonstration shows how TITAN Control Center presents an incident, its persisted Kafka transition, the declared root event, and a bounded root-cause assessment. **The demonstration does not establish a verified root cause.**

## Environment and scope

- API base URL (local lab): `http://127.0.0.1:8088/api/v1`
- Incident: `INC-TITAN-E2E-PUBLISH-001`
- Incident source: `TITAN` integration test
- Host: `titan-core01`
- Access mode: `READ_ONLY`
- Evidence: API responses observed during the November 2026 lab demonstration

The commands below query existing data only. They do not inject incidents, modify PostgreSQL, publish Kafka messages, or invoke remediation.

## Reproduce the demonstration

Prerequisites: the TITAN API must be reachable locally; `curl` and `jq` must be installed.

```bash
set -euo pipefail
API="http://127.0.0.1:8088/api/v1"
INCIDENT="INC-TITAN-E2E-PUBLISH-001"

printf '\n=== INCIDENT ===\n'
curl -fsS --max-time 10 "$API/incidents" |
  jq --arg id "$INCIDENT" '.items[]? | select(.incident_id == $id)'

printf '\n=== TIMELINE ===\n'
curl -fsS --max-time 10 "$API/incidents/$INCIDENT/timeline" |
  jq '{incident_id, transition_count: (.items | length), transitions: .items}'

printf '\n=== RCA ===\n'
curl -fsS --max-time 10 "$API/incidents/$INCIDENT/rca" |
  jq '{incident_id, mode, incident, observed_facts, root_event, related_events, transitions, assessment, limits}'
```

## Observed results

The following values were returned by the lab API; they are a **recorded snapshot**, not guarantees about future runs.

| Field | Observed value |
|---|---|
| Incident ID | `INC-TITAN-E2E-PUBLISH-001` |
| Incident state / severity | `WATCH` / `warning` |
| Incident correlation key | `titan-core01:INTEGRATION_TEST` |
| Declared root event | `TITAN-E2E-001` |
| Root event found | `true` |
| Root event type / host | `INTEGRATION_TEST` / `titan-core01` |
| Root event correlation key | `TITAN-TEST-001` |
| Related events returned | `0` |
| Transitions returned | `1` |
| Transition ID | `INC-TITAN-E2E-PUBLISH-001:publish-test-1` |
| Kafka topic | `titan.incidents.v1` |
| Partition / offset | `0` / `0` |
| RCA classification | `DECLARED_ROOT_EVENT_UNVERIFIED` |
| RCA confidence | `UNDETERMINED` |
| Causality verified | `false` |
| RCA mode | `READ_ONLY` |
| Collection limit | `25` per collection |
| Truncation flags | `events_truncated=false`, `transitions_truncated=false` |

### Event timestamps (UTC)

- Incident opened: `2026-11-11T21:30:00+00:00`
- Root event observed: `2026-11-11T21:30:00+00:00`
- Root event received: `2026-11-11T22:57:21.565102+00:00`
- Incident updated: `2026-11-13T01:49:58.540549+00:00`
- Kafka transition received: `2026-11-13T03:30:24.366317+00:00`

These timestamps describe different fields and stages; they must not be treated as a single causal sequence without additional evidence.

## RCA interpretation and limitations

The API found the **declared** root event, but its correlation key (`TITAN-TEST-001`) differs from the incident correlation key (`titan-core01:INTEGRATION_TEST`). No related events were returned for the incident correlation key. The persisted Kafka transition establishes that one transition record is available for inspection; it does **not** independently prove the cause of the incident.

The API returned these assessment limitations:

- Correlation key equality does not establish causality.
- No independent causal verification is performed.
- No events match the incident correlation key.

Accordingly, the correct conclusion is **`DECLARED_ROOT_EVENT_UNVERIFIED` with `UNDETERMINED` confidence and `causality_verified=false`**. The platform intentionally avoids promoting an asserted root event into a verified RCA.

The absence of related events in this bounded response is not proof that no related events exist anywhere. This is a single integration-test scenario, not evidence of completed Linux/eBPF, Splunk, or Dynatrace end-to-end ingestion.

## Control Center walkthrough

1. Open **Incidents** and select `INC-TITAN-E2E-PUBLISH-001`.
2. Inspect its state (`WATCH`), severity (`warning`), declared root event, and timeline.
3. Inspect the RCA panel and verify that the classification, confidence, and causal-verification flag agree with the API.
4. Inspect the evidence limitations before drawing any causal conclusion.
5. Use the EN/FR interface switch and theme controls without altering underlying event identifiers or evidence.

The Control Center is an observability and investigation interface in this scenario; no automated remediation is exercised.

## Engineering takeaway

> TITAN separates observed incident facts, persisted transitions, declared root-event metadata, and causal assessment. Its evidence-bounded RCA deliberately returns an unverified classification when independent causal proof is unavailable.

## Next demonstration improvement

For a stronger multi-event correlation demonstration, prepare a **separate, explicitly labeled test scenario** with consistently populated correlation keys and independently verifiable evidence. Do not rewrite this recorded snapshot or claim causality from key matching alone.
