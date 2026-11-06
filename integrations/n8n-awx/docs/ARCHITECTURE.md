# Architecture and evidence flow

## Components

- **n8n:** trigger, HTTP launch, bounded status polling, normalization, event retrieval, enrichment.
- **AWX:** authenticated Ansible job orchestration and REST event API.
- **Ansible:** approved remote diagnostic playbook; recap counters.
- **TITAN Evidence Layer:** structured JSON contract for later correlation (integration beyond this JSON output not asserted).

## Observed workflow node sequence

```text
Manual Trigger
  -> AWX — Launch Diagnostic
  -> AWX — Get Job Status
  -> Wait — 5 seconds
  -> AWX — Get Final Status
  -> AWX — Job Finished?
       false -> AWX — Polling Guard -> AWX — Polling Limit Reached?
                   false -> Wait — 5 seconds
                   true -> AWX — Polling Timeout (Stop and Error)
       true -> AWX — Job Successful?
                   true -> TITAN — Normalize AWX Evidence
                        -> AWX — Get Ansible Stats
                        -> TITAN — Enrich AWX Evidence
                   false -> failure branch [pending]
```

The successful terminal state requires `status=successful`, `failed=false`, and `event_processing_finished=true`. A terminal `failed`, `error`, or `canceled` status must be handled explicitly; silently ending a workflow is not acceptable.

## AWX REST requests

Use an authenticated HTTPS endpoint in production or an explicitly secured tunnel for lab traffic:

```text
POST /api/v2/job_templates/{template_id}/launch/
GET  /api/v2/jobs/{job_id}/
GET  /api/v2/jobs/{job_id}/job_events/?event=playbook_on_stats
```

The API event must belong to the same job ID as the normalized job record. A successful AWX job status alone does not establish valid task-level evidence.

## Evidence semantics

- `job.*`: job-level AWX metadata.
- `execution.*`: job-level summary reported by AWX.
- `ansible.recap.*`: task recap from `playbook_on_stats`.
- `evidence.ansible_stats_verified`: event was retrieved and correlated; **not** independent attestation.
- `evidence.non_intrusive_execution`: in this preview, an inference from `changed=0`, `failures=0`, and `dark=0`; **not** proof of no system side effects.
- `remediation_performed=false`: declared diagnostic-only workflow intent; do not treat as a forensic assertion.

## Known implementation limitations

- The prototype's evidence-enrichment code assumes a single target host. Generalization requires explicit target identity validation and aggregation across all hosts.
- The prototype may map absent AWX summary fields to zero. Strict completeness and missing-data semantics remain a hardening task.
- The nominal path was exercised; timeout and failure paths are not yet proven by negative tests.
- The exact impact of the n8n freeze/restart is not established; retry/idempotency and availability behavior need explicit validation.
