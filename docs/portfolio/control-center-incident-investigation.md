# TITAN Control Center — End-to-End Incident Investigation

## Overview

TITAN Control Center provides a read-only investigation
interface for operational incidents.

The demonstrated workflow connects incident discovery,
timeline inspection, and explainable root-cause analysis
(RCA) through a React/TypeScript frontend and FastAPI.

## Architecture

- Frontend: React and TypeScript
- Backend: FastAPI
- Investigation mode: READ_ONLY
- Incident discovery: GET /api/v1/incidents
- Timeline: GET /api/v1/incidents/{id}/timeline
- RCA: GET /api/v1/incidents/{id}/rca

## Verified End-to-End Scenario

Validation: TITAN-PORTFOLIO-08I-22B-FIX-02

Incident: INC-TITAN-E2E-PUBLISH-001

| Check | Result |
|---|---|
| Incident discovery | PASS |
| Timeline incident identity | PASS |
| RCA response contract | PASS |
| Investigation mode | READ_ONLY |
| Timeline transitions | 1 |
| RCA classification | DECLARED_ROOT_EVENT_UNVERIFIED |
| Causality verified | false |

The RCA assessment distinguishes declared root events
from independently verified causal explanations.

The reported observed-facts count was UNKNOWN because
the validation script did not identify an array at the
expected JSON location. This does not establish that
no observed facts exist.

## Graceful Degradation Demonstration

Validation: TITAN-PORTFOLIO-08I-21G-06

Five browser checks were manually confirmed:

1. Incident list remains available.
2. Timeline failure is displayed.
3. RCA remains available.
4. Navigation remains functional.
5. Timeline recovers in normal mode.

The failure was injected in an isolated frontend copy
using the URL parameter:

    ?titan_demo_timeline_failure=1

The demonstration did not require backend modification
or interruption of existing services.

## Reliability and Evidence Boundaries

- A declared root event is not proof of causality.
- The browser failure was simulated client-side.
- No backend outage was induced.
- The scenario does not establish high availability.
- Load testing and distributed failure recovery were
  outside the validation scope.
- Browser checks were manually confirmed rather than
  independently captured by automated browser tests.

## Operational Value

The Control Center demonstrates:

- Consistent incident identity across investigation views.
- Explicit RCA classifications and evidence limitations.
- Isolation of partial frontend API failures.
- Continued access to investigation capabilities.
- Read-only investigation without automated remediation.

## Portfolio Summary

Designed and validated an incident investigation
interface integrating React, TypeScript, and FastAPI.

Demonstrated explainable RCA semantics, consistent
incident identity, and graceful degradation during
a simulated timeline API failure.

The implementation emphasizes operational transparency,
evidence provenance, and separation between observed
correlation and verified causality.
