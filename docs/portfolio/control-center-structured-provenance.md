# TITAN Control Center — Structured Evidence Provenance

## Overview

Structured Evidence Provenance provides a read-only
summary of event metadata returned by the Incident RCA API.

The feature helps operators evaluate evidence coverage,
source diversity, and metadata completeness.

## Implementation

- `evidenceProvenance.ts`: deterministic provenance summary
- `EvidenceProvenance.tsx`: operator-facing presentation
- Existing RCA API contract: unchanged

## Capabilities

- Counts returned evidence records
- Groups records by reported source
- Summarizes event types and host identities
- Identifies missing host metadata
- Identifies missing or invalid observation timestamps
- Identifies missing reception timestamps
- Displays explicit provenance limitations

## Safety and Explainability

Multiple reported sources do not prove independent
corroboration.

Matching correlation keys do not prove causality.

The feature does not execute remediation actions.

## Current Limitations

Evidence source names are supplied by the RCA API.

The current contract does not expose source independence,
evidence freshness guarantees, or independent causal
verification.

Counts represent returned records, not necessarily
unique events.

## Validation

- TypeScript/Vite production build: PASS
- Deterministic provenance test: PASS
- Independent corroboration guard: PASS

## Next Steps

Introduce structured provenance attributes from actual
Linux/eBPF and Splunk evidence producers.

Add backend-supported freshness and source independence
indicators without inferring causality from correlation.
