#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PACKAGE_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
BASE="${TITAN_TEST_ROOT:-$PACKAGE_ROOT/tests}"
VALIDATOR="$PACKAGE_ROOT/lib/canonical_incident_validator.sh"
CHECKER="$PACKAGE_ROOT/lib/strict_json_integrity.py"
MUTATION_GATE="$PACKAGE_ROOT/lib/mutation_integrity_gate.py"

usage() {
  echo "Usage: $0 --lab DIR --candidate FILE --expected-generation N --expected-incident-sha SHA256 --expected-registry-sha SHA256" >&2
  exit 2
}

LAB=""
CANDIDATE=""
EXPECTED=""
EXPECTED_INC_SHA=""
EXPECTED_REG_SHA=""

while (($#)); do
  case "$1" in
    --lab)
      (($# >= 2)) || usage
      LAB="$2"; shift 2 ;;
    --candidate)
      (($# >= 2)) || usage
      CANDIDATE="$2"; shift 2 ;;
    --expected-generation)
      (($# >= 2)) || usage
      EXPECTED="$2"; shift 2 ;;
    --expected-incident-sha)
      (($# >= 2)) || usage
      EXPECTED_INC_SHA="$2"; shift 2 ;;
    --expected-registry-sha)
      (($# >= 2)) || usage
      EXPECTED_REG_SHA="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$LAB" && -n "$CANDIDATE" &&
   -n "$EXPECTED" && -n "$EXPECTED_INC_SHA" &&
   -n "$EXPECTED_REG_SHA" ]] || usage

[[ "$EXPECTED" =~ ^(0|[1-9][0-9]*)$ &&
   ${#EXPECTED} -le 15 ]] || {
  echo "ERROR=INVALID_GENERATION" >&2
  exit 1
}

for SHA in "$EXPECTED_INC_SHA" "$EXPECTED_REG_SHA"; do
  [[ "$SHA" =~ ^[0-9a-f]{64}$ ]] || {
    echo "ERROR=INVALID_SHA256" >&2
    exit 1
  }
done

[[ -d "$BASE" && ! -L "$BASE" ]] || exit 1

# The lab must be an immediate child of the synthetic test root.
LAB_NAME="${LAB##*/}"

[[ "$LAB" == "$BASE/$LAB_NAME" &&
   "$LAB_NAME" =~ ^transaction-lab\.[a-zA-Z0-9_-]+$ &&
   -d "$LAB" && ! -L "$LAB" ]] || {
  echo "ERROR=UNSAFE_LAB_PATH" >&2
  exit 1
}

[[ -f "$CANDIDATE" && ! -L "$CANDIDATE" ]] || {
  echo "ERROR=INVALID_CANDIDATE" >&2
  exit 1
}

# Only candidates directly under this synthetic lab are accepted.
[[ "${CANDIDATE%/*}" == "$LAB" ]] || {
  echo "ERROR=CANDIDATE_OUTSIDE_LAB" >&2
  exit 1
}

[[ -x "$VALIDATOR" && -r "$CHECKER" && -r "$MUTATION_GATE" ]] || {
  echo "ERROR=REQUIRED_VALIDATOR_UNAVAILABLE" >&2
  exit 1
}

[[ -d "$LAB/generations" &&
   ! -L "$LAB/generations" &&
   -f "$LAB/CURRENT" &&
   ! -L "$LAB/CURRENT" ]] || {
  echo "ERROR=INVALID_LAB_STRUCTURE" >&2
  exit 1
}

# Lock before examining any transaction state.
exec 9>"$LAB/lock"
flock -x 9

CURRENT="$(cat "$LAB/CURRENT")"

[[ "$CURRENT" =~ ^GEN-[0-9]{16}$ ]] || {
  echo "ERROR=INVALID_CURRENT_POINTER" >&2
  exit 1
}

CURRENT_GEN="${CURRENT#GEN-}"
CURRENT_GEN="$((10#$CURRENT_GEN))"

[[ "$CURRENT_GEN" -eq "$EXPECTED" ]] || {
  echo "ERROR=STALE_GENERATION"
  exit 1
}

CURRENT_DIR="$LAB/generations/$CURRENT"

[[ -d "$CURRENT_DIR" &&
   ! -L "$CURRENT_DIR" &&
   -f "$CURRENT_DIR/incident.json" &&
   -f "$CURRENT_DIR/registry.json" ]] || {
  echo "ERROR=INVALID_CURRENT_GENERATION"
  exit 1
}

INC_SHA="$(sha256sum "$CURRENT_DIR/incident.json" | awk '{print $1}')"
REG_SHA="$(sha256sum "$CURRENT_DIR/registry.json" | awk '{print $1}')"

[[ "$INC_SHA" == "$EXPECTED_INC_SHA" &&
   "$REG_SHA" == "$EXPECTED_REG_SHA" ]] || {
  echo "ERROR=BASELINE_SNAPSHOT_MISMATCH"
  exit 1
}

# Copy candidate while holding the lock.
TMP_CANDIDATE="$(mktemp "$LAB/.candidate.XXXXXXXX")"
TMP_INCIDENT="$(mktemp "$LAB/.incident.XXXXXXXX")"
TMP_REGISTRY="$(mktemp "$LAB/.registry.XXXXXXXX")"
TMP_CURRENT=""
STAGING=""

cleanup() {
  [[ -z "$TMP_CANDIDATE" ]] ||
    command rm -f -- "$TMP_CANDIDATE"

  [[ -z "$TMP_INCIDENT" ]] ||
    command rm -f -- "$TMP_INCIDENT"

  [[ -z "$TMP_REGISTRY" ]] ||
    command rm -f -- "$TMP_REGISTRY"

  [[ -z "$TMP_CURRENT" ]] ||
    command rm -f -- "$TMP_CURRENT"

  # Preserve staging for forensic review on publication failure.
  if [[ -n "$STAGING" ]]; then
    echo "staging_preserved_for_review=$STAGING" >&2
  fi
}
trap cleanup EXIT

command cp -f -- "$CANDIDATE" "$TMP_CANDIDATE"
command cp -f -- "$CURRENT_DIR/incident.json" "$TMP_INCIDENT"
command cp -f -- "$CURRENT_DIR/registry.json" "$TMP_REGISTRY"

[[ "$(sha256sum "$TMP_INCIDENT" | awk '{print $1}')" == "$EXPECTED_INC_SHA" &&
   "$(sha256sum "$TMP_REGISTRY" | awk '{print $1}')" == "$EXPECTED_REG_SHA" ]] || {
  echo "ERROR=BASELINE_SNAPSHOT_MISMATCH"
  exit 1
}

python3 "$CHECKER" "$TMP_CANDIDATE" || exit 1
python3 "$CHECKER" "$TMP_INCIDENT" || exit 1
python3 "$CHECKER" "$TMP_REGISTRY" || exit 1

jq -e '
  type == "object"
  and (.incident | type == "object")
  and (.registry | type == "object")
' "$TMP_CANDIDATE" >/dev/null || {
  echo "ERROR=INVALID_MUTATION_STRUCTURE"
  exit 1
}

NEXT_GEN=$((EXPECTED + 1))
printf -v NEXT "GEN-%016d" "$NEXT_GEN"

[[ ! -e "$LAB/generations/$NEXT" &&
   ! -L "$LAB/generations/$NEXT" ]] || {
  echo "ERROR=NEXT_GENERATION_EXISTS"
  exit 1
}

STAGING="$(mktemp -d "$LAB/generations/.staging.XXXXXXXX")"

jq -e '.incident' "$TMP_CANDIDATE" \
  > "$STAGING/incident.json"

jq -e '.registry' "$TMP_CANDIDATE" \
  > "$STAGING/registry.json"

python3 "$CHECKER" "$STAGING/incident.json"
python3 "$CHECKER" "$STAGING/registry.json"

"$VALIDATOR" --input "$STAGING/incident.json" >/dev/null || {
  echo "ERROR=CANONICAL_VALIDATION_FAILED"
  exit 1
}

python3 "$MUTATION_GATE" \
  --incident "$TMP_INCIDENT" \
  --registry "$TMP_REGISTRY" \
  --mutation "$TMP_CANDIDATE" || {
  echo "ERROR=MUTATION_INTEGRITY_FAILED"
  exit 1
}

jq -e --argjson expected "$EXPECTED" '
  .incident as $i |
  .registry as $r |
  $i.identity.incident_id as $id |
  $i.identity.incident_fingerprint as $fp |

  ($i.lifecycle.generation == ($expected + 1))
  and (
    [
      $r.incidents.active[]
      | select(.incident_id == $id)
    ] | length == 1
  )
  and (
    [
      $r.incidents.active[]
      | select(.incident_id == $id)
    ][0].generation == ($expected + 1)
  )
  and (
    $r.indexes.fingerprint_owners[$fp][0].generation
    == ($expected + 1)
  )
' "$TMP_CANDIDATE" >/dev/null || {
  echo "ERROR=GENERATION_CONSISTENCY_FAILED"
  exit 1
}

# Publish a complete generation directory first.
python3 -B "$SCRIPT_DIR/durable_publication_helper_v2_2.py" \
  --lab "$LAB" \
  --staging "$STAGING" \
  --next-generation "$NEXT"

STAGING=""
TMP_CURRENT=""

echo "mutation_integrity=PASS"
echo "transaction_status=COMMITTED"
echo "previous_generation=$CURRENT"
echo "current_generation=$NEXT"
echo "atomic_pointer_publication=YES"
echo "durability_protocol=FSYNC_ENABLED"
echo "durability_after_power_loss=NOT_TESTED"
echo "operational_mutation=NONE"
echo "RESULT=TRANSACTION_COMMIT_PASS"
