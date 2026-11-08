#!/usr/bin/env bash
set -euo pipefail
umask 077

usage() {
  echo "Usage: $0 --proposal FILE --baseline FILE --registry FILE --authorization FILE"
}

PROPOSAL=""
BASELINE=""
REGISTRY=""
AUTH=""

while (($#)); do
  case "$1" in
    --proposal) PROPOSAL="${2:?}"; shift 2 ;;
    --baseline) BASELINE="${2:?}"; shift 2 ;;
    --registry) REGISTRY="${2:?}"; shift 2 ;;
    --authorization) AUTH="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFIER="$SCRIPT_DIR/engine_provenance_verifier.sh"
GATE="$SCRIPT_DIR/incident_admission_gate.sh"

VERIFIER_SHA="9f23a416a855973fcaedffafa17af2530ac97c035e2dd2fa6de981437f501176"
GATE_SHA="b57ca4f52638203e466ae96db811091b5727380d45b1c8477d4fe383a2a0fc67"

# Verify both component identities before execution.
printf '%s  %s\n' "$VERIFIER_SHA" "$VERIFIER" |
  sha256sum -c - >/dev/null || {
    echo "PROVENANCE_VERIFIER_INTEGRITY_FAILURE" >&2
    exit 4
  }

# Verify the admission gate identity.
printf '%s  %s\n' "$GATE_SHA" "$GATE" |
  sha256sum -c - >/dev/null || {
    echo "ADMISSION_GATE_INTEGRITY_FAILURE" >&2
    exit 4
  }

# The verifier identity must be explicitly supplied by a
# trusted local release manifest before operational use.
# This candidate remains advisory-only.

for f in "$PROPOSAL" "$BASELINE" "$REGISTRY" "$AUTH"; do
  [[ -n "$f" && -f "$f" && -r "$f" ]] || {
    echo "INPUT_UNREADABLE" >&2
    exit 3
  }
done

WORK="$(mktemp -d /tmp/titan-integrated-admission.XXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT

cp -- "$PROPOSAL" "$WORK/proposal.json"
cp -- "$BASELINE" "$WORK/baseline.json"
cp -- "$REGISTRY" "$WORK/registry.json"
cp -- "$AUTH" "$WORK/authorization.json"

bash "$VERIFIER" \
  --proposal "$WORK/proposal.json" \
  --baseline "$WORK/baseline.json" \
  > "$WORK/provenance.json"

PROVENANCE_STATUS="$(jq -r '.verification.status' "$WORK/provenance.json")"

if [[ "$PROVENANCE_STATUS" == "MATCH" ]]; then

  bash "$GATE" \
    --proposal "$WORK/proposal.json" \
    --registry "$WORK/registry.json" \
    --authorization "$WORK/authorization.json" \
    > "$WORK/admission.json"

  ADMISSION_STATUS="$(jq -r '.decision.status' "$WORK/admission.json")"
  ADMISSION_REASON="$(jq -r '.decision.reason' "$WORK/admission.json")"

else
  ADMISSION_STATUS="REJECT"
  ADMISSION_REASON="ENGINE_PROVENANCE_NOT_ACCEPTED"
fi

jq -n \
  --arg provenance "$PROVENANCE_STATUS" \
  --arg admission "$ADMISSION_STATUS" \
  --arg reason "$ADMISSION_REASON" \
  '{
    schema_version:"0.1",
    engine:{
      name:"titan_provenance_admission_integration",
      version:"0.1.1-candidate"
    },
    verification:{
      engine_provenance_status:$provenance
    },
    decision:{
      status:$admission,
      reason:$reason,
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
  }'
