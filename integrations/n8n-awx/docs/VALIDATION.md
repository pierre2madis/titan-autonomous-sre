# Validation record

## Nominal runs

| Observation | Job 9 | Job 10 |
|---|---:|---:|
| AWX template | 8 | 8 |
| Job status | successful | successful |
| Elapsed (s) | 6.343 | 6.651 |
| Hosts OK | 1 | 1 |
| Tasks | 2 | 2 |
| Stats event ID | 77 | 87 |
| Ansible `ok` | 2 | 2 |
| Ansible `changed` | 0 | 0 |
| Ansible `failures` | 0 | 0 |
| Ansible `dark` | 0 | 0 |
| Enriched quality | VALID | VALID |

The user reported that an earlier attempt failed when the n8n server was frozen. After restarting the server, a rerun succeeded. This report is an availability observation, **not** a confirmed root cause.

## Gates

| Gate | Status | Evidence needed |
|---|---|---|
| Successful AWX launch and status polling | PASS (nominal) | Job 9/10 metadata |
| Ansible stats API retrieval | PASS (nominal) | Events 77/87 |
| Job/event correlation | PASS (nominal) | Enriched JSON |
| No changes declared by Ansible | PASS (reported) | `changed=0` recap |
| Negative test: AWX failed/error/canceled | NOT TESTED | Mocked terminal responses |
| Negative test: polling timeout | NOT TESTED | Controlled synthetic polling |
| Negative test: missing/duplicate/mismatched stats | NOT TESTED | Synthetic event payloads |
| n8n restart and retry/idempotency | NOT TESTED | Controlled restart/retry experiment |
| Independent non-intrusiveness | NOT VERIFIED | Playbook review and independent state checks |
| Production SSH host-key verification | HARDENING REQUIRED | Reviewed AWX configuration |

## Next engineering milestones

1. Complete explicit failure branch; preserve failed job metadata as a structured outcome.
2. Test timeout and malformed/missing evidence with synthetic fixtures; avoid unnecessary AWX job launches.
3. Define `UNKNOWN`/`REVIEW_REQUIRED` for missing counters rather than defaulting all missing data to zero.
4. Harden restart behavior, job idempotency, credentials, TLS, and SSH host verification.
5. Review sanitized workflow export and only then request approval to publish.
