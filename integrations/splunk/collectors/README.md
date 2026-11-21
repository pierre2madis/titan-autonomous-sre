# TITAN Splunk Cluster Evidence Collector

## Overview

Offline Splunk indexer-cluster evidence integration for TITAN Autonomous SRE.

Pipeline: Splunk CLI capture -> Bash collector -> Incident Adapter -> Incident Engine.

## Components

- collectors/splunk_cluster_evidence_collector.sh
- config/cluster_policy.example.json
- contracts/splunk_cluster_capture_v0_2.schema.json
- adapters/splunk_incident_adapter.sh

## Classifications

| Classification | Incident candidate |
| --- | --- |
| HEALTHY | No |
| EXPECTED_DOWN | No |
| UNEXPECTED_DOWN | Yes |
| UNKNOWN | No |

## Execution

Run the collector from the repository root:

    bash integrations/splunk/collectors/splunk_cluster_evidence_collector.sh POLICY_JSON CAPTURE_JSON OUTPUT_JSON

The capture must contain capture_version, source, cluster_manager,
captured_at, collection_status and peers.

## Safety

- Offline read-only processing
- No Splunk configuration changes
- No PostgreSQL or Kafka writes
- No automatic remediation
- Existing output files are never overwritten
- Missing, stale or unrecognized evidence cannot trigger incidents

## Current limitations

- The collector consumes JSON captures; it does not query Splunk directly.
- Capture provenance depends on the upstream collection mechanism.
- JSON Schema validation is not yet enforced by a dedicated validator.
- Deterministic event identity does not replace cross-capture deduplication.
- RCA causality remains unverified.
- Continuous collection and production deployment are not implemented.

## Validation

- HEALTHY: PASS
- EXPECTED_DOWN: PASS
- UNEXPECTED_DOWN: PASS
- UNKNOWN (missing peer): PASS
- UNKNOWN (stale capture): PASS
- Deterministic replay: PASS
- Offline Incident Engine: PASS

## Status

TITAN-12C offline integration candidate.
