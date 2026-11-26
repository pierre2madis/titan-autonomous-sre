# TITAN Control Center

Unified observability and incident investigation interface for
the TITAN Autonomous SRE platform.

## Components

- React / TypeScript frontend
- FastAPI backend
- PostgreSQL incident persistence
- Kafka integration evidence
- Splunk evidence integration
- Incident lifecycle and RCA presentation

## Current status

This is a local distribution candidate, not a production release.

The validated laboratory preview uses an isolated unified API
and React frontend.

## Safety and evidence limitations

- Read-only preview
- No automatic remediation
- RCA causality may remain unverified
- UNKNOWN and DEGRADED states must not be presented as healthy
- Worker and correlation evidence may be unavailable

## Configuration

See `deploy/.env.example`.

Environment-specific network addresses, credentials, paths
and service endpoints must be supplied externally.

## Validation

Run:

    bash scripts/validate-package.sh

## Deployment

Docker deployment files and runtime dependency locks are
pending validation.

Do not assume this candidate is production-ready.

## Vite proxy configuration

TITAN Control Center separates development proxy destinations from
container build configuration.

### Local development

The Vite development configurations require explicit HTTP(S) targets:

| Variable | Purpose |
|---|---|
| `TITAN_VITE_GENERAL_API_TARGET` | General FastAPI backend |
| `TITAN_VITE_SPLUNK_API_TARGET` | Splunk evidence API |
| `TITAN_VITE_LIFECYCLE_API_TARGET` | Incident lifecycle API in demo mode |

Example (replace the placeholders with environment-specific URLs):

```bash
export TITAN_VITE_GENERAL_API_TARGET="http://general-api.example.invalid:8080"
export TITAN_VITE_SPLUNK_API_TARGET="http://splunk-api.example.invalid:8080"
export TITAN_VITE_LIFECYCLE_API_TARGET="http://lifecycle-api.example.invalid:8080"
```

The `.invalid` domain is illustrative and is not a reachable endpoint.

### Portable Docker build

The portable Vite configuration uses:

| Variable | Purpose |
|---|---|
| `TITAN_API_PROXY_TARGET` | General API target for Vite proxy configuration |
| `TITAN_SPLUNK_PROXY_TARGET` | Splunk API target for Vite proxy configuration |

The Docker frontend build supplies these variables using configurable
build arguments. They are build-time placeholders, not operational
backend destinations.

Runtime API routing is handled separately by the Nginx configuration
and deployment environment.

Do not store passwords, tokens, or private keys in build arguments.
