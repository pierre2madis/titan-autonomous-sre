# Incident Evidence — Offline Read-Only Preview

## Overview

TITAN Control Center provides an incident evidence view for
reviewing artifacts associated with an incident.

The current implementation is an offline demonstration.
It does not establish verified root-cause causality.

## API

`GET /api/v1/incidents/{incident_id}/evidence`

The endpoint is implemented in:

`control-center/api/incident_evidence.py`

The router is registered in:

`control-center/api/main.py`

## Evidence contract

The demonstrated response includes the following safeguards:

- `mode`: `OFFLINE_READ_ONLY`
- `verification_status`: `UNVERIFIED`
- `review_only`: `true`
- `causality_verified`: `false`
- `remediation_allowed`: `false`

These values must not be interpreted as proof of causality
or authorization to execute remediation.

## Frontend

The Incident Evidence interface is implemented in:

`control-center/frontend/src/IncidentEvidence.tsx`

It is integrated into:

`control-center/frontend/src/App.tsx`

## Demonstration scope

The validated demonstration uses an offline incident with
associated evidence artifacts.

The interface supports evidence review and displays
verification limitations.

The current demonstration does not prove:

- Automated causal inference
- Production incident coverage
- Autonomous remediation
- End-to-end production reliability

## Operational constraints

This feature must remain read-only in the current preview.

No database mutation, Kafka publication, or remediation
execution is authorized by this evidence view.

Any future transition toward automated remediation requires
separate validation, explicit governance, and approval gates.
