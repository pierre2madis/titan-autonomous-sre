#!/usr/bin/env bash
set -euo pipefail

PROPOSAL=""
REGISTRY=""
GRAPH=""
GENERATION=""

while (($#)); do
  case "$1" in
    --proposal) PROPOSAL="${2:?}"; shift 2 ;;
    --registry) REGISTRY="${2:?}"; shift 2 ;;
    --graph) GRAPH="${2:?}"; shift 2 ;;
    --generation) GENERATION="${2:?}"; shift 2 ;;
    *) echo "Unsupported argument" >&2; exit 2 ;;
  esac
done

[[ -r "$PROPOSAL" && -r "$REGISTRY" &&
   -r "$GRAPH" && "$GENERATION" =~ ^GEN-[0-9]{16}$ ]] || exit 2

A="/tmp/titan_causal_attachment_validator_v0_1_1_candidate.sh"
G="/tmp/titan_graph_consistency_gate_v0_1_0_candidate.sh"

printf '%s  %s\n' \
  "6342bf5e6c3e2e932c3ba098d7e7f2c38e2d2b9108389474b2b12bc0873f8220" "$A" \
  "fbc2731c6bf3443e0636ec6b4703bcc198436da1a07115a9462f97863da34916" "$G" |
  sha256sum -c >/dev/null || exit 2

ATTACH="$(bash "$A" \
  --proposal "$PROPOSAL" \
  --registry "$REGISTRY" \
  --generation "$GENERATION")"

GRAPH_RESULT="$(bash "$G" \
  --registry "$REGISTRY" \
  --graph "$GRAPH")"

jq -n \
  --argjson a "$ATTACH" \
  --argjson g "$GRAPH_RESULT" \
  --arg gen "$GENERATION" '
  ($a.decision.status) as $ad |
  ($g.decision.status) as $gd |

  (
    if $ad=="REJECT" then
      ["REJECT","ATTACHMENT_REJECTED"]
    elif $gd=="INCONSISTENT" then
      ["REJECT","GRAPH_REGISTRY_INCONSISTENT"]
    elif $ad=="DEFER" or $gd=="DEFER" then
      ["DEFER","PREREQUISITE_UNVERIFIED"]
    elif $ad=="NOOP" and $gd=="CONSISTENT" then
      ["NOOP","ALREADY_ATTACHED"]
    elif $ad=="ADMIT" and $gd=="CONSISTENT" then
      ["PROPOSED","ATTACHMENT_PLAN_ELIGIBLE"]
    else
      ["DEFER","UNRECOGNIZED_DECISION_COMBINATION"]
    end
  ) as $result |

  {
    engine:{
      name:"advisory_causal_attachment_planner",
      version:"0.1.0-candidate"
    },
    source:{
      expected_generation:$gen,
      canonical_provenance_verified:false,
      authorization_verified:false
    },
    prerequisites:{
      attachment_decision:$ad,
      graph_consistency:$gd
    },
    decision:{
      status:$result[0],
      reason:$result[1],
      advisory_only:true,
      persisted:false,
      operationally_authorized:false
    },
    controls:{
      incident_write_allowed:false,
      lifecycle_transition_allowed:false,
      remediation_allowed:false,
      notification_allowed:false
    }
  }
'
