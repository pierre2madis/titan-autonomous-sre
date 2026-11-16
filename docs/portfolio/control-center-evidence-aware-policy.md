# TITAN Control Center — Evidence-Aware Remediation Policy

## Overview

The Evidence-Aware Remediation Policy extends the
TITAN Control Center's read-only Remediation Advisor.

It evaluates evidence availability, completeness,
and RCA limitations before selecting an investigation
recommendation.

No remediation execution is supported.

## Architecture

The implementation contains three frontend modules:

- `evidenceQuality.ts`: structured evidence quality
- `remediationAdvisor.ts`: deterministic policy engine
- `RemediationAdvisor.tsx`: recommendation presentation

The policy consumes the existing Incident RCA API contract.

No backend API changes are required for this release.

## Evidence Quality

The following evidence quality states are defined:

- `MISSING`: declared root event unavailable
- `PARTIAL`: RCA evidence collections are truncated
- `UNVERIFIED`: independent corroboration is unavailable
- `CORROBORATED`: reserved for a future structured contract

The current implementation never assigns `CORROBORATED`.

An RCA declaration of verified causality does not
establish independent evidence corroboration.

## Policy Decisions

The deterministic policy distinguishes:

- `MISSING_ROOT_EVENT`
- `INCOMPLETE_EVIDENCE`
- `CONFLICTING_EVIDENCE`
- `UNVERIFIED_CAUSALITY`
- `REVIEW_REQUIRED`

Decision precedence favors missing or incomplete
evidence before evaluating causality.

Conflict detection currently uses text matching
against RCA limitations and is provisional.

## Safety Invariants

All recommendations retain:

- Recommendation type: `FURTHER_INVESTIGATION`
- Execution allowed: `false`
- Approval status: `NOT_REQUESTED`
- Confidence: `UNDETERMINED`

No n8n, AWX, or infrastructure remediation action
is triggered by this feature.

## Validation Evidence

Validated locally:

- TypeScript and Vite production build
- Five deterministic policy decisions
- Missing, partial, and unverified evidence quality
- Declared causality does not imply corroboration
- Execution remains blocked in all tested scenarios

## Limitations and Next Steps

The current API does not expose structured independent
corroboration or structured evidence conflicts.

Future work should introduce explicit provenance,
source independence, evidence freshness, and
contradiction indicators.

Human approval and remediation execution remain
out of scope.

## Portfolio Value

This increment demonstrates conservative,
explainable operational decision support,
with explicit evidence limitations and
fail-closed execution behavior.
