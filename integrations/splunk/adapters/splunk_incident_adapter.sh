#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
  echo "Usage: $0 INPUT_JSON OUTPUT_JSON" >&2
  exit 2
fi

input=$1
output=$2

command -v jq >/dev/null || {
  echo "ERROR=jq_not_installed" >&2
  exit 2
}

[[ -f "$input" ]] || {
  echo "ERROR=input_not_found" >&2
  exit 2
}

# Validate the complete supported evidence contract.
jq -e '
  type == "object"
  and .source == "SPLUNK"
  and .domain == "INDEXER_CLUSTER"
  and (.target | type) == "string"
  and (.target | test("^[A-Za-z0-9._-]{1,128}$"))
  and (.event_id | type) == "string"
  and (.event_id | test("^TITAN-[A-Za-z0-9-]{1,250}$"))
  and (.classification |
       IN("HEALTHY", "EXPECTED_DOWN", "UNEXPECTED_DOWN", "UNKNOWN"))
  and (.incident_candidate | type) == "boolean"
  and (.expected_state | type) == "object"
  and (.expected_state.expected_down_peers | type) == "array"
  and (.expected_state.unexpected_down_peers | type) == "array"
  and all(.expected_state.expected_down_peers[];
          type == "string" and test("^[A-Za-z0-9._-]+$"))
  and all(.expected_state.unexpected_down_peers[];
          type == "string" and test("^[A-Za-z0-9._-]+$"))
  and (
    if .classification == "EXPECTED_DOWN" then
      .incident_candidate == false
      and (.expected_state.expected_down_peers | length) > 0
      and (.expected_state.unexpected_down_peers | length) == 0
    elif .classification == "UNEXPECTED_DOWN" then
      .incident_candidate == true
      and (.expected_state.unexpected_down_peers | length) > 0
    elif .classification == "HEALTHY" then
      .incident_candidate == false
      and (.expected_state.expected_down_peers | length) == 0
      and (.expected_state.unexpected_down_peers | length) == 0
    else
      .incident_candidate == false
      and (.expected_state.unexpected_down_peers | length) == 0
    end
  )
' "$input" >/dev/null || {
  echo "ERROR=invalid_evidence_contract" >&2
  exit 2
}

classification=$(jq -r '.classification' "$input")

case "$classification" in
  HEALTHY)
    echo "INCIDENT_CANDIDATE=NO"
    echo "REASON=HEALTHY"
    exit 0
    ;;
  EXPECTED_DOWN)
    echo "INCIDENT_CANDIDATE=NO"
    echo "REASON=EXPECTED_DOWN"
    exit 0
    ;;
  UNKNOWN)
    echo "INCIDENT_CANDIDATE=NO"
    echo "REASON=INSUFFICIENT_EVIDENCE"
    exit 0
    ;;
esac

# Never overwrite an existing incident input.
if [[ -e "$output" || -L "$output" ]]; then
  echo "ERROR=output_already_exists" >&2
  exit 2
fi

output_dir=$(dirname -- "$output")
[[ -d "$output_dir" ]] || {
  echo "ERROR=output_directory_missing" >&2
  exit 2
}

tmp=$(mktemp "$output_dir/.splunk-incident.XXXXXXXX")
trap 'rm -f -- "$tmp"' EXIT

jq -S '{
  incident_id: ("INC-" + .event_id[6:]),
  correlation_key: (.target + ":" + .domain),
  correlated_events: 1,
  root_event_id: .event_id,
  root_event_policy: "DEMO_DECLARATION"
}' "$input" > "$tmp"

# Atomic no-clobber publication using a hard link.
if ! ln -- "$tmp" "$output"; then
  echo "ERROR=output_publication_failed" >&2
  exit 2
fi

echo "INCIDENT_CANDIDATE=YES"
echo "INCIDENT_INPUT=$output"
