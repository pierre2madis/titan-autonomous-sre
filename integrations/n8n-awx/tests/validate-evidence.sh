#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v jq >/dev/null || { echo 'ERROR: jq is required' >&2; exit 2; }
for f in contracts/awx-evidence-v1.schema.json examples/awx-evidence-success.json; do
  jq -e . "$f" >/dev/null
  echo "JSON_PARSE_PASS: $f"
done
jq -e '
  .schema_version == "1.0" and .source == "AWX" and
  .job.status == "successful" and .job.failed == false and
  .evidence.ansible_stats_verified == true and
  .ansible.event_type == "playbook_on_stats" and
  .ansible.recap.ok == 2 and .ansible.recap.changed == 0 and
  .ansible.recap.failures == 0 and .ansible.recap.dark == 0
' examples/awx-evidence-success.json >/dev/null
printf '%s\n' 'EXAMPLE_SANITY_PASS (not full JSON Schema validation)'
