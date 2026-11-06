# Alertmanager Ingestion Security

Webhook payloads are untrusted input.

## Required Controls
- Header authentication.
- Payload structure and size validation.
- Timestamp and fingerprint validation.
- Network ingress restrictions.
- No embedded credentials.
- No automatic remediation.

## Known Limitations
The candidate has not been validated end-to-end in n8n.
Raw HTTP request-body size enforcement is not established.
Network hardening remains pending.
