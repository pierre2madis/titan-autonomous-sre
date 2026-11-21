#!/usr/bin/env bash
set -euo pipefail
umask 077

if (( $# != 3 )); then
  echo "Usage: $0 POLICY_JSON CAPTURE_JSON OUTPUT_JSON" >&2
  exit 2
fi

policy=$1
capture=$2
output=$3

for cmd in jq date sha256sum mktemp ln; do
  command -v "$cmd" >/dev/null || exit 2
done

[[ -f "$policy" && -f "$capture" ]] || {
  echo "ERROR=missing_input" >&2
  exit 2
}

[[ ! -e "$output" && ! -L "$output" ]] || {
  echo "ERROR=output_exists" >&2
  exit 2
}

output_dir=$(dirname -- "$output")
[[ -d "$output_dir" ]] || exit 2

jq -e '
  type == "object"
  and .policy_version == "0.2"
  and (.cluster_manager | type) == "string"
  and (.cluster_manager | test("^[A-Za-z0-9._-]{1,128}$"))
  and (.expected_peers | type) == "array"
  and (.expected_peers | length) > 0
  and all(.expected_peers[];
      type == "string" and test("^[A-Za-z0-9._-]+$"))
  and (.expected_peers | unique | length) == (.expected_peers | length)
  and (.expected_down_peers | type) == "array"
  and all(.expected_down_peers[];
      type == "string" and test("^[A-Za-z0-9._-]+$"))
  and (.expected_down_peers | unique | length)
      == (.expected_down_peers | length)
  and ((.expected_down_peers - .expected_peers) | length) == 0
  and (.max_evidence_age_seconds | type) == "number"
  and .max_evidence_age_seconds > 0
  and .max_evidence_age_seconds == (.max_evidence_age_seconds | floor)
  and .unknown_state_incident_candidate == false
  and .execution_mode == "OFFLINE_READ_ONLY"
' "$policy" >/dev/null || {
  echo "ERROR=invalid_policy" >&2
  exit 2
}

jq -e --slurpfile p "$policy" '
  type == "object"
  and (.capture_version == "0.2")
  and (.source == "SPLUNK_CLI")
  and (.cluster_manager == $p[0].cluster_manager)
  and (.collection_status == "SUCCESS")
  and (.captured_at | type) == "string"
  and (.captured_at | test(
      "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
  ))
  and (.peers | type) == "array"
  and all(.peers[];
      type == "object"
      and (.label | type) == "string"
      and (.label | test("^[A-Za-z0-9._-]+$"))
      and (.status | type) == "string"
      and (
        .is_searchable == true
        or .is_searchable == false
        or .is_searchable == 0
        or .is_searchable == 1
        or .is_searchable == "0"
        or .is_searchable == "1"
      )
  )
' "$capture" >/dev/null || {
  echo "ERROR=invalid_capture" >&2
  exit 2
}

captured_at=$(jq -r '.captured_at' "$capture")

captured_epoch=$(date -u -d "$captured_at" +%s 2>/dev/null) || {
  echo "ERROR=invalid_capture_timestamp" >&2
  exit 2
}

canonical_time=$(date -u -d "@$captured_epoch" \
  +%Y-%m-%dT%H:%M:%SZ)

[[ "$canonical_time" == "$captured_at" ]] || {
  echo "ERROR=noncanonical_capture_timestamp" >&2
  exit 2
}

now=$(date -u +%s)
max_age=$(jq -r '.max_evidence_age_seconds' "$policy")
age=$((now - captured_epoch))

fresh=true
if (( age < 0 || age > max_age )); then
  fresh=false
fi

# Stable identity for the capture and classification policy.
identity=$(
  jq -n -cS \
    --slurpfile c "$capture" \
    --slurpfile p "$policy" \
    '{capture: $c[0], policy: $p[0]}' |
    sha256sum |
    cut -d ' ' -f1
)

tmp=$(mktemp "$output_dir/.splunk-evidence.XXXXXXXX")
trap 'rm -f -- "$tmp"' EXIT

jq -n -e \
  --slurpfile p "$policy" \
  --slurpfile c "$capture" \
  --arg identity "$identity" \
  --argjson fresh "$fresh" '
  $p[0] as $policy |
  $c[0] as $capture |
  $capture.peers as $rows |
  $policy.expected_peers as $expected |
  $policy.expected_down_peers as $allowed |

  [$rows[].label] as $names |

  (
    ($rows | length) == ($expected | length)
    and ($names | unique | length) == ($names | length)
    and (($expected - $names) | length) == 0
    and (($names - $expected) | length) == 0
  ) as $complete |

  (
    all($rows[];
      if .status == "Up" then
        (.is_searchable == true
         or .is_searchable == 1
         or .is_searchable == "1")
      elif .status == "Down" then
        (.is_searchable == false
         or .is_searchable == 0
         or .is_searchable == "0")
      else false end
    )
  ) as $recognized |

  [$rows[] | select(.status == "Down") | .label] as $down |
  ($down - $allowed) as $unexpected |
  ($down - $unexpected) as $expected_down |

  (
    if ($fresh | not) or ($complete | not) or ($recognized | not)
    then "UNKNOWN"
    elif ($unexpected | length) > 0
    then "UNEXPECTED_DOWN"
    elif ($expected_down | length) > 0
    then "EXPECTED_DOWN"
    else "HEALTHY"
    end
  ) as $classification |

  {
    source: "SPLUNK",
    target: $policy.cluster_manager,
    domain: "INDEXER_CLUSTER",
    event_id: ("TITAN-SPLUNK-CLUSTER-" + $identity),
    classification: $classification,
    incident_candidate: ($classification == "UNEXPECTED_DOWN"),
    expected_state: {
      expected_down_peers:
        (if $classification == "UNKNOWN" then [] else $expected_down end),
      unexpected_down_peers:
        (if $classification == "UNKNOWN" then [] else $unexpected end)
    },
    evidence: {
      contract_version: "0.2",
      observed_at: $capture.captured_at,
      capture_sha256: $identity,
      fresh: $fresh,
      complete: $complete,
      recognized: $recognized,
      expected_peer_count: ($expected | length),
      observed_peer_count: ($rows | length),
      missing_peers: ($expected - $names)
    }
  }
' > "$tmp" || {
  echo "ERROR=normalization_failed" >&2
  exit 2
}

ln -- "$tmp" "$output" || {
  echo "ERROR=publication_failed" >&2
  exit 2
}

echo "EVIDENCE_CREATED=$output"
jq -r '
  "CLASSIFICATION=\(.classification)",
  "INCIDENT_CANDIDATE=\(.incident_candidate)",
  "EVIDENCE_FRESH=\(.evidence.fresh)"
' "$output"
