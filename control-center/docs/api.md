# Control Center API

Development API prefix:

/api/v1

## Incidents

GET /api/v1/incidents

GET /api/v1/incidents/{incident_id}

GET /api/v1/incidents/{incident_id}/timeline

## Platform

GET /api/v1/platform/health

GET /api/v1/platform/pipeline

GET /api/v1/platform/workers

GET /api/v1/platform/correlation

## Health

GET /api/v1/health

## Operational classification

HEALTHY:
Required operational evidence is available and healthy.

DEGRADED:
Collected evidence identifies a measurable degradation.

UNKNOWN:
Available evidence is insufficient to establish health.

Activity and confidence are reported separately from health.

## Limitations

These endpoints are intended for a controlled development
environment. Production authentication and authorization
are not yet implemented.
