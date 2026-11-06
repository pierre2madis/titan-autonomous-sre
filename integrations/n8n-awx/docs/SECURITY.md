# Security notes and guardrails

## Secrets

- Use n8n's credential manager for AWX API authentication.
- Restrict AWX API identity to minimum required rights; rotate and revoke credentials as appropriate.
- Never commit bearer tokens, Authorization headers, passwords, private keys, n8n credential exports, or runtime environment dumps.
- Scrub workflow exports, execution samples, screenshots, job environment, URLs, and logs before publication.

## Transport and host identity

- Require authenticated TLS or a reviewed encrypted tunnel for AWX API transport.
- Verify SSH host keys in production. A previous lab AWX job environment reported `ANSIBLE_HOST_KEY_CHECKING=False`; this is a known **hardening gap**, not a recommended setting.
- Do not disclose private overlay addresses, machine identifiers, or internal routing details in the public repo.

## Execution boundaries

- Allowlist approved inventories, job templates, and targets.
- Use a diagnostic-only playbook with read-only tasks and minimal remote privileges.
- `changed=0` is not a substitute for a code review or OS-level audit of side effects.
- Remediation must be gated by a separate approval/policy decision and must not be inferred from a successful diagnostic.
- Use bounded polling and explicit terminal failure paths. Do not automatically relaunch failed or timed-out jobs without an idempotency and duplicate-execution policy.

## Before public release

Review exported n8n JSON and all example artifacts for secrets, internal endpoints, credentials, real hostnames, and identifying metadata. Public publication requires explicit owner approval.
