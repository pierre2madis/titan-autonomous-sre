# TITAN Splunk Evidence Integration

## Purpose

Transform normalized Splunk indexer-cluster observations into
offline incident events using the existing TITAN Incident Engine.

## Components

- `ansible/`: distributed-search configuration automation
- `contracts/`: Splunk Evidence JSON Schema
- `adapters/`: Bash evidence-to-incident adapter
- `examples/`: synthetic demonstration evidence

## Classification

| Classification | Incident candidate |
|---|---|
| EXPECTED_DOWN | No |
| UNEXPECTED_DOWN | Yes |
| UNKNOWN | No |

Only explicitly classified unexpected peer outages become
incident candidates.

## Offline demonstration

Requirements: Bash, jq and Python 3.

From the repository root:

    bash integrations/splunk/adapters/splunk_incident_adapter.sh \
      integrations/splunk/examples/unexpected_down.json \
      /tmp/titan_splunk_incident_input.json

    python3 control-center/incident-engine/incident_engine.py \
      --input /tmp/titan_splunk_incident_input.json \
      --output /tmp/titan_splunk_incident_event.json

Use unique output paths or remove previous demonstration
artifacts before repeating this example.

## Safety

- Synthetic evidence only
- No Splunk REST API calls
- No PostgreSQL writes
- No Kafka publication
- No automatic remediation
- Causality is not verified
- Root-event declaration is not proof of root cause

## Limitations

This is an offline integration demonstration.

The JSON Schema documents the supported evidence structure.
The Bash adapter performs its own validation; it does not
execute a JSON Schema validator.

Live telemetry provenance, freshness checks, authentication,
persistent incident state and production-grade correlation
are not implemented in this component.
