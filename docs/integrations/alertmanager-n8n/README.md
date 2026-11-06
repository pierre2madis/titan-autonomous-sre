# Alertmanager to n8n — Observe-Only Integration

## Purpose
TITAN integrates Prometheus Alertmanager with n8n to ingest,
validate, and normalize incident evidence for future RCA correlation.

## Architecture
Prometheus exporters → Prometheus → Alertmanager → n8n webhook
→ validation → normalization → future TITAN RCA correlation.

## Workflow Candidate v1.0.2
The candidate contains five nodes: webhook receiver, validation,
acceptance decision, HTTP 200 response, and HTTP 400 response.

## Validation Status
Fourteen isolated Node.js validation scenarios passed.
Live n8n runtime execution and Alertmanager delivery remain unverified.
The workflow has not been imported or activated.

## Safety
- Observe-only execution.
- Automatic remediation disabled.
- Authentication required before deployment.
- No credentials committed to Git.

## Next Steps
- Publish a sanitized workflow export.
- Validate authenticated webhook delivery.
- Integrate incident evidence correlation.
- Demonstrate Grafana incident dashboards.
