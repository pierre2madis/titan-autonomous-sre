# TITAN Incident Engine

Offline incident lifecycle adapter.

## Input

A normalized correlation result containing:

- incident_id
- correlation_key
- correlated_events
- root_event_id

## Output

A deterministic INCIDENT_CREATED JSON event.

## Guarantees

- Stable incident identity
- Idempotent replay against the same output file
- No automatic causal verification
- No database writes
- No Kafka publication
- No service restart

## Execution

python3 incident_engine.py \
  --input correlation.json \
  --output incident_event.json
