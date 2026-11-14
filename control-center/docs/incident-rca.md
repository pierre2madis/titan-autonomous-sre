# TITAN Control Center — Incident RCA View

## Overview

The Incident RCA View provides a read-only, evidence-bounded
investigation interface for incidents recorded by TITAN.

The feature supports operational investigation but does not
claim to establish independently verified root cause.

## Architecture

Incident data flows through:

1. Event ingestion
2. Incident state persistence
3. Transition persistence
4. Read-only PostgreSQL queries
5. FastAPI RCA endpoint
6. React incident investigation view

## API

```http
GET /api/v1/incidents/{incident_id}/rca
```

Optional query parameter:

- `limit`: number of records per evidence collection,
  from 1 to 50, default 25.

The endpoint retrieves:

- Incident state and severity
- Declared root event reference
- Root event record, when available
- Events sharing the incident correlation key
- Recorded incident transitions
- Evidence availability and truncation indicators

## Evidence interpretation

A declared root event is not automatically a verified root cause.

The current assessment intentionally reports:

- `confidence: UNDETERMINED`
- `causality_verified: false`

Correlation-key equality establishes association only.

## Read-only behavior

Database access uses a read-only PostgreSQL transaction
configuration and a statement timeout.

The endpoint does not:

- Modify incident states
- Write evidence records
- Trigger remediation
- Acknowledge or close incidents
- Execute automation workflows

## Known limitations

- No independent causal verification
- Correlation does not prove causation
- Related evidence may be absent
- Evidence collections are subject to result limits
- RCA conclusions depend on the available persisted evidence

## Example response

```json
{
  "incident_id": "INC-EXAMPLE-001",
  "mode": "READ_ONLY",
  "observed_facts": {
    "declared_root_event_id": "EVENT-001",
    "root_event_found": true,
    "related_event_count_returned": 0,
    "transition_count_returned": 1
  },
  "assessment": {
    "classification": "DECLARED_ROOT_EVENT_UNVERIFIED",
    "confidence": "UNDETERMINED",
    "causality_verified": false,
    "limitations": [
      "Correlation key equality does not establish causality.",
      "No independent causal verification is performed.",
      "No events match the incident correlation key."
    ]
  }
}
```

The example uses synthetic identifiers.

## Future development

Potential future enhancements include:

- Evidence freshness assessment
- Multi-source evidence correlation
- Splunk enrichment when available
- Dynatrace enrichment when available
- Causal hypothesis tracking
- Human-reviewed RCA conclusions

These enhancements are not part of the current implementation.
