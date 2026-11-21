#!/usr/bin/env bash
# TITAN-13A-04B — Splunk CLI capture producer v0.1
set -Eeuo pipefail
umask 077

usage() {
  printf 'Usage: %s POLICY_JSON OUTPUT_JSON [SPLUNK_CLI]\n' "$0" >&2
  printf 'Requires an existing authenticated Splunk CLI session (no password arguments).\n' >&2
  exit 2
}
[[ $# -ge 2 && $# -le 3 ]] || usage
policy=$1
output=$2
splunk=${3:-/opt/splunk/bin/splunk}
[[ -r "$policy" && -x "$splunk" ]] || { echo 'INPUT_OR_SPLUNK_CLI_UNAVAILABLE' >&2; exit 2; }
command -v jq >/dev/null && command -v date >/dev/null || { echo 'DEPENDENCY_MISSING' >&2; exit 2; }
[[ ! -e "$output" ]] || { echo 'OUTPUT_ALREADY_EXISTS' >&2; exit 2; }

# Only a constrained, valid policy may define the expected peer set.
jq -e '
  .cluster_manager == "us02" and
  (.expected_peers | type == "array" and length > 0 and length == (unique | length)) and
  all(.expected_peers[]; type == "string" and length > 0)
' "$policy" >/dev/null || { echo 'INVALID_POLICY' >&2; exit 2; }

outdir=$(dirname -- "$output")
[[ -d "$outdir" ]] || { echo 'OUTPUT_DIRECTORY_MISSING' >&2; exit 2; }
work=$(mktemp -d "$outdir/.titan-splunk-capture.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT

# No -auth argument: relies on the Splunk CLI's pre-existing session.
# If authentication is unavailable, the command fails closed.
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if ! "$splunk" search \
  '| rest splunk_server=local /services/cluster/manager/peers | fields label status is_searchable | table label status is_searchable' \
  -output json > "$work/raw.json" 2> "$work/cli.stderr"; then
  echo 'SPLUNK_QUERY_FAILED (check CLI authentication and permissions)' >&2
  exit 1
fi

# Splunk emits concatenated JSON documents. Every document must be valid,
# have an explicit result and contain a non-preview, uniquely named peer.
if ! jq -s -e --slurpfile policy "$policy" '
  def valid_doc:
    type == "object" and
    (.preview == false or .preview == "false" or .preview == 0) and
    (.result | type == "object") and
    (.result.label | type == "string" and length > 0) and
    (.result.status | type == "string" and length > 0) and
    (.result.is_searchable | tostring | IN("0", "1"));
  length > 0 and
  all(.[]; valid_doc) and
  ([.[].result.label] | length == (unique | length)) and
  ([.[].result.label] | sort) == ($policy[0].expected_peers | sort) and
  (.[-1].lastrow == true or .[-1].lastrow == "true" or .[-1].lastrow == 1)
' "$work/raw.json" >/dev/null; then
  echo 'INVALID_OR_INCOMPLETE_SPLUNK_RESPONSE' >&2
  exit 1
fi

# Capture time is the start of query; do not substitute file mtime.
jq -n --arg at "$started" --slurpfile raw "$work/raw.json" '
  {
    capture_version: "0.2",
    source: "SPLUNK_CLI",
    cluster_manager: "us02",
    captured_at: $at,
    collection_status: "SUCCESS",
    peers: ($raw | map(.result | {
      label: .label,
      status: .status,
      is_searchable: (.is_searchable | tostring)
    }) | sort_by(.label))
  }
' > "$work/capture.json"

chmod 600 "$work/capture.json"
# Hard link fails if destination exists; never overwrite prior evidence.
ln -- "$work/capture.json" "$output"
printf 'CAPTURE_CREATED=%s\n' "$output"
printf 'PEER_COUNT=%s\n' "$(jq '.peers | length' "$output")"
printf 'TITAN_13A_04B=PASS\n'
