# Configuration guide (environment-neutral)

This is a **configuration outline**, not a ready-to-import n8n workflow. No live n8n export was provided for this package.

1. Create an AWX inventory and a job template bound to an approved read-only diagnostic playbook.
2. Create a least-privilege AWX API identity; store its token only in the n8n credential manager.
3. Configure a secured API endpoint reachable from n8n. Avoid committing literal IPs, ports, or bearer tokens.
4. Add HTTP Request nodes for launch, status, and `playbook_on_stats` retrieval. Parameterize template/job IDs.
5. Add a bounded polling loop with wait, terminal-state decision, and Stop and Error for timeout.
6. Add an explicit error path for `failed`, `error`, and `canceled`; do not silently mark these as successful.
7. Normalize AWX metadata, correlate the stats event by job ID, validate counters, and output the evidence contract.
8. Test success and synthetic failures before enabling unattended use.

The prototype used a single lab host and a single stats event. Multi-host use requires validated inventory identity and per-host aggregation. Avoid blindly copying lab-specific assumptions.

## Local contract check

Run `bash tests/validate-evidence.sh` from the repository root. This is a **static** example check only; it does not contact AWX or execute Ansible.
