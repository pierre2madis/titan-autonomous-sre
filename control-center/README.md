# TITAN Autonomous SRE — Control Center

## Overview

TITAN Control Center is a read-only operational interface
for exploring incidents, observing event-processing health,
and correlating evidence across PostgreSQL and Redpanda.

The project demonstrates evidence-driven SRE engineering:
operational health is not inferred solely from empty queues
or zero consumer lag.

## Architecture

- Frontend: React, TypeScript, Vite
- Backend: FastAPI
- Database: PostgreSQL
- Event streaming: Redpanda (Kafka API)
- Evidence model: read-only health collectors
- Correlation: health, activity and confidence

## Implemented capabilities

- Incident list and incident details
- Incident timeline
- Platform health
- Core pipeline evidence
- Kafka consumer group health
- Consumer lag monitoring
- Pipeline health correlation
- Operational assessment

## Operational assessment

The platform distinguishes:

- Health: HEALTHY, DEGRADED, UNKNOWN
- Activity: NO_BACKLOG_OBSERVED, BACKLOG_OBSERVED, UNKNOWN
- Confidence: HIGH, MODERATE, LIMITED

A zero backlog does not automatically imply operational readiness.

## Security model

The current development environment uses loopback-bound
API and frontend services.

Database evidence queries use read-only sessions.

Kafka health collectors inspect metadata and offsets
without consuming messages or committing offsets.

Production authentication, authorization, TLS and
deployment hardening are not yet implemented.

## Project status

Control Center v0.1.0 is a development-stage
technical portfolio increment.

It is not presented as a production-ready
incident management platform.
