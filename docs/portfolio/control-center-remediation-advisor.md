# TITAN Control Center — Explainable Remediation Advisor

## Overview

The TITAN Remediation Advisor extends incident investigation
with deterministic, evidence-aware recommendations.

It is currently a frontend-only, read-only capability.

No remediation is executed, and no approval workflow
is activated.

## Architecture

The advisor consumes the existing Incident RCA response:

- Incident identity
- RCA classification
- Causality verification status
- Confidence assessment
- Evidence limitations

The decision logic is implemented in:

`control-center/frontend/src/remediationAdvisor.ts`

The React presentation component is:

`control-center/frontend/src/RemediationAdvisor.tsx`

It is integrated into:

`control-center/frontend/src/IncidentRCA.tsx`

## Safety Model

The current recommendation type is:

`FURTHER_INVESTIGATION`

The advisor does not infer that correlation establishes
causality.

For unverified causality, it recommends validating
the declared root event and reviewing independent evidence.

Even when causality is reported as verified, remediation
execution remains blocked.

The current execution policy is:

- Execution allowed: false
- Approval status: NOT_REQUESTED
- Confidence: UNDETERMINED
- No n8n or AWX execution calls

The LOW risk label applies only to the non-intrusive
investigation recommendation.

## Validation

The following checks have passed:

- TypeScript and Vite production build
- Unverified causality recommendation
- Verified causality execution guard
- No automatic remediation

Browser rendering remains to be confirmed separately.

## Limitations

This release does not implement:

- Independent causal verification
- Automated remediation
- Human approval workflow
- n8n/AWX execution
- Remediation outcome tracking
- Production-grade risk assessment

## Portfolio Value

This feature demonstrates a guarded transition from
incident investigation toward evidence-aware operational
decision support, without overstating RCA certainty
or enabling unsafe automation.
