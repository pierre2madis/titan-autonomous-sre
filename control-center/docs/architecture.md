# TITAN Control Center Architecture

## Components

### React frontend

Displays incident information and operational evidence
retrieved from the FastAPI backend.

### FastAPI backend

Exposes read-only endpoints for incident exploration,
platform health, worker health and pipeline correlation.

### PostgreSQL

Stores event evidence, incident states,
transition inbox records and transactional outbox records.

### Redpanda

Provides Kafka-compatible event transport.

Consumer health evidence includes:

- Consumer group state
- Committed offsets
- Partition high watermarks
- Consumer lag

### Pipeline correlation

Combines PostgreSQL and Kafka evidence.

A pipeline with no pending messages but unverified
worker liveness is classified conservatively.

## Logical data flow

Event Producers
    |
    v
Redpanda Topics
    |
    v
Event Consumers
    |
    v
PostgreSQL Evidence and Incident State
    |
    v
FastAPI Read-Only API
    |
    v
React Control Center

## Operational guardrails

- No automatic remediation in Control Center
- No Kafka offset commits from health collectors
- No database mutations from evidence endpoints
- No production readiness claim without validation
