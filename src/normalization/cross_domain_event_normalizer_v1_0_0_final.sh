#!/usr/bin/env bash

set -u
set -o pipefail

VERSION="1.0.0-final"
SCHEMA_VERSION="1.0"

RC_OK=0
RC_USAGE=2
RC_INPUT=20
RC_JSON=21
RC_CONTRACT=24

usage()
{
    cat <<USAGE
Usage:
  $0 --input FILE [--pretty]
  $0 --version

Purpose:
  Normalize a validated Domain Correlation Adapter output into the
  canonical Cross-Domain Correlation Event V1.0 contract.
USAGE
}

die()
{
    local rc="$1"
    shift

    printf 'ERROR: %s\n' "$*" >&2
    exit "$rc"
}

INPUT=""
PRETTY=false

while (($#))
do
    case "$1" in
        --input)
            (($# >= 2)) || die "$RC_USAGE" "--input requires a file"
            INPUT="$2"
            shift 2
            ;;

        --pretty)
            PRETTY=true
            shift
            ;;

        --version)
            printf '%s\n' "$VERSION"
            exit "$RC_OK"
            ;;

        -h|--help)
            usage
            exit "$RC_OK"
            ;;

        *)
            die "$RC_USAGE" "Unknown argument: $1"
            ;;
    esac
done

[[ -n "$INPUT" ]] || die "$RC_USAGE" "--input is required"
[[ -f "$INPUT" ]] || die "$RC_INPUT" "Input file not found: $INPUT"
[[ -r "$INPUT" ]] || die "$RC_INPUT" "Input file not readable: $INPUT"

jq -e . "$INPUT" >/dev/null 2>&1 \
    || die "$RC_JSON" "Malformed JSON input"

#
# ------------------------------------------------------------------
# Extract normalized source fields
# ------------------------------------------------------------------
#

DOMAIN="$(
    jq -r '
      .source.domain
      // .domain
      // empty
    ' "$INPUT"
)"

PROVIDER="$(
    jq -r '
      .source.provider
      // .source.type
      // .provider
      // "UNKNOWN"
    ' "$INPUT"
)"

HOST="$(
    jq -r '
      .source.host
      // .target.host
      // .identity.host
      // .host
      // "UNKNOWN"
    ' "$INPUT"
)"

SERVICE="$(
    jq -r '
      .source.service
      // .target.service
      // empty
    ' "$INPUT"
)"

CLUSTER="$(
    jq -r '
      .source.cluster
      // .target.cluster
      // empty
    ' "$INPUT"
)"

DEVICE="$(
    jq -r '
      .source.device
      // .target.device
      // empty
    ' "$INPUT"
)"

ROLE="$(
    jq -r '
      .source.role
      // .target.role
      // empty
    ' "$INPUT"
)"

#
# ------------------------------------------------------------------
# Observation
# ------------------------------------------------------------------
#

OBSERVED_AT="$(
    jq -r '
      .observation.observed_at
      // .observation.decided_at
      // empty
    ' "$INPUT"
)"

WINDOW_START="$(
    jq -r '
      .observation.window_start
      // .observation.start
      // empty
    ' "$INPUT"
)"

WINDOW_END="$(
    jq -r '
      .observation.window_end
      // .observation.end
      // .observation.decided_at
      // empty
    ' "$INPUT"
)"

#
# ------------------------------------------------------------------
# Evidence
# ------------------------------------------------------------------
#

STATE="$(jq -r '.evidence.state // empty' "$INPUT")"
DIAGNOSTIC="$(jq -r '.evidence.diagnostic_type // empty' "$INPUT")"
SEVERITY="$(jq -r '.evidence.severity // empty' "$INPUT")"
CONFIDENCE="$(jq -r '.evidence.confidence // empty' "$INPUT")"

#
# ------------------------------------------------------------------
# Correlation contribution
# ------------------------------------------------------------------
#

CONTRIBUTION="$(jq -r '.correlation.contribution // empty' "$INPUT")"
EVIDENCE_ROLE="$(jq -r '.correlation.evidence_role // empty' "$INPUT")"
CAUSE_CLASS="$(jq -r '.correlation.cause_class // empty' "$INPUT")"
WEIGHT="$(jq -r '.correlation.weight // empty' "$INPUT")"

#
# ------------------------------------------------------------------
# Incident hints
# ------------------------------------------------------------------
#

CREATE_INCIDENT="$(jq -r '.incident_contribution.create_incident // false' "$INPUT")"
MERGE_CANDIDATE="$(jq -r '.incident_contribution.merge_candidate // false' "$INPUT")"
PARENT_CANDIDATE="$(jq -r '.incident_contribution.parent_candidate // false' "$INPUT")"
PROPAGATION_CANDIDATE="$(jq -r '.incident_contribution.propagation_candidate // false' "$INPUT")"

#
# ------------------------------------------------------------------
# Existing identity / fingerprint fields when available
# ------------------------------------------------------------------
#

REQUEST_ID="$(
    jq -r '
      .identity.request_id
      // .upstream_contract.request_id
      // empty
    ' "$INPUT"
)"

UPSTREAM_EVENT_ID="$(
    jq -r '
      .identity.event_id
      // .upstream_contract.event_id
      // empty
    ' "$INPUT"
)"

UPSTREAM_EVIDENCE_ID="$(
    jq -r '
      .identity.evidence_id
      // .upstream_contract.evidence_id
      // .correlation.fingerprint
      // empty
    ' "$INPUT"
)"

CORRELATION_KEY="$(
    jq -r '
      .identity.correlation_key
      // .correlation.correlation_key
      // .correlation.key
      // empty
    ' "$INPUT"
)"

FINGERPRINT="$(
    jq -r '
      .correlation.fingerprint
      // .identity.fingerprint
      // empty
    ' "$INPUT"
)"

#
# ------------------------------------------------------------------
# Mandatory structural validation
# ------------------------------------------------------------------
#

[[ -n "$DOMAIN" ]] \
    || die "$RC_CONTRACT" "Missing source domain"

[[ -n "$OBSERVED_AT" ]] \
    || die "$RC_CONTRACT" "Missing observation timestamp"

[[ -n "$STATE" ]] \
    || die "$RC_CONTRACT" "Missing evidence state"

[[ -n "$DIAGNOSTIC" ]] \
    || die "$RC_CONTRACT" "Missing diagnostic type"

[[ -n "$SEVERITY" ]] \
    || die "$RC_CONTRACT" "Missing evidence severity"

[[ -n "$CONFIDENCE" ]] \
    || die "$RC_CONTRACT" "Missing evidence confidence"

[[ -n "$CONTRIBUTION" ]] \
    || die "$RC_CONTRACT" "Missing correlation contribution"

[[ -n "$EVIDENCE_ROLE" ]] \
    || die "$RC_CONTRACT" "Missing evidence role"

[[ -n "$CAUSE_CLASS" ]] \
    || die "$RC_CONTRACT" "Missing cause class"

[[ -n "$WEIGHT" ]] \
    || die "$RC_CONTRACT" "Missing correlation weight"

#
# ------------------------------------------------------------------
# Canonical domain validation
# ------------------------------------------------------------------
#

case "$DOMAIN" in
    CPU|MEMORY|BLOCK_IO|NETWORK|APPLICATION|SPLUNK|DYNATRACE|PROMETHEUS)
        ;;
    *)
        die "$RC_CONTRACT" "Unsupported source domain: $DOMAIN"
        ;;
esac

#
# ------------------------------------------------------------------
# Generic evidence validation
# ------------------------------------------------------------------
#

case "$STATE" in
    AVAILABLE|INSUFFICIENT|UNAVAILABLE)
        ;;
    *)
        die "$RC_CONTRACT" "Unsupported evidence state: $STATE"
        ;;
esac

case "$SEVERITY" in
    NONE|INFO|WARNING|CRITICAL)
        ;;

    UNKNOWN)
        case "$STATE" in
            INSUFFICIENT|UNAVAILABLE)
                ;;
            *)
                die "$RC_CONTRACT" \
                    "UNKNOWN severity requires INSUFFICIENT or UNAVAILABLE evidence"
                ;;
        esac
        ;;

    *)
        die "$RC_CONTRACT" "Unsupported evidence severity: $SEVERITY"
        ;;
esac

case "$CONFIDENCE" in
    NONE|LOW|MEDIUM|HIGH|UNKNOWN)
        ;;
    *)
        die "$RC_CONTRACT" "Unsupported evidence confidence: $CONFIDENCE"
        ;;
esac

#
# ------------------------------------------------------------------
# Contribution semantics
# ------------------------------------------------------------------
#

#
# ------------------------------------------------------------------
# Evidence-state / contribution semantic matrix
#
# AVAILABLE    -> SUPPORTS | CONTRADICTS
# INSUFFICIENT -> INDETERMINATE
# UNAVAILABLE  -> UNAVAILABLE
#
# Missing evidence is absence of knowledge, not evidence of absence.
# ------------------------------------------------------------------
#

case "$STATE" in
    AVAILABLE)
        case "$CONTRIBUTION" in
            SUPPORTS|CONTRADICTS)
                ;;
            *)
                die "$RC_CONTRACT" \
                    "AVAILABLE evidence requires correlation contribution=SUPPORTS or CONTRADICTS"
                ;;
        esac
        ;;

    INSUFFICIENT)
        [[ "$CONTRIBUTION" == "INDETERMINATE" ]] \
            || die "$RC_CONTRACT" \
                "INSUFFICIENT evidence requires correlation contribution=INDETERMINATE"
        ;;

    UNAVAILABLE)
        [[ "$CONTRIBUTION" == "UNAVAILABLE" ]] \
            || die "$RC_CONTRACT" \
                "UNAVAILABLE evidence requires correlation contribution=UNAVAILABLE"
        ;;
esac

case "$CONTRIBUTION" in
    SUPPORTS)
        [[ "$EVIDENCE_ROLE" == "CAUSAL_CANDIDATE" ]] \
            || die "$RC_CONTRACT" \
                "SUPPORTS requires evidence_role=CAUSAL_CANDIDATE"

        [[ "$WEIGHT" =~ ^[0-9]+$ ]] \
            || die "$RC_CONTRACT" "Correlation weight must be an integer"

        (( WEIGHT >= 1 && WEIGHT <= 100 )) \
            || die "$RC_CONTRACT" \
                "SUPPORTS weight must be between 1 and 100"

        [[ "$CAUSE_CLASS" != "NONE" &&
           "$CAUSE_CLASS" != "UNKNOWN" ]] \
            || die "$RC_CONTRACT" \
                "SUPPORTS requires a concrete cause_class"
        ;;

    CONTRADICTS)
        [[ "$EVIDENCE_ROLE" == "EXONERATING" ]] \
            || die "$RC_CONTRACT" \
                "CONTRADICTS requires evidence_role=EXONERATING"

        [[ "$WEIGHT" == "0" ]] \
            || die "$RC_CONTRACT" \
                "CONTRADICTS requires weight=0"
        ;;

    INDETERMINATE)
        [[ "$EVIDENCE_ROLE" == "NON_DECISIVE" ]] \
            || die "$RC_CONTRACT" \
                "INDETERMINATE requires evidence_role=NON_DECISIVE"

        [[ "$WEIGHT" == "0" ]] \
            || die "$RC_CONTRACT" \
                "INDETERMINATE requires weight=0"
        ;;

    UNAVAILABLE)
        [[ "$EVIDENCE_ROLE" == "NON_DECISIVE" ]] \
            || die "$RC_CONTRACT" \
                "UNAVAILABLE requires evidence_role=NON_DECISIVE"

        [[ "$WEIGHT" == "0" ]] \
            || die "$RC_CONTRACT" \
                "UNAVAILABLE requires weight=0"
        ;;

    *)
        die "$RC_CONTRACT" \
            "Unsupported correlation contribution: $CONTRIBUTION"
        ;;
esac

#
# ------------------------------------------------------------------
# Incident ownership boundary
# ------------------------------------------------------------------
#

[[ "$CREATE_INCIDENT" == "false" ]] \
    || die "$RC_CONTRACT" \
        "Domain evidence must not directly create incidents"

for v in \
    "$MERGE_CANDIDATE" \
    "$PARENT_CANDIDATE" \
    "$PROPAGATION_CANDIDATE"
do
    [[ "$v" == "true" || "$v" == "false" ]] \
        || die "$RC_CONTRACT" "Invalid incident candidate boolean"
done

#
# ------------------------------------------------------------------
# SUPPORTS is the only contribution allowed to propose causal actions.
# ------------------------------------------------------------------
#

if [[ "$CONTRIBUTION" != "SUPPORTS" ]]; then
    [[ "$MERGE_CANDIDATE" == "false" ]] \
        || die "$RC_CONTRACT" \
            "Non-SUPPORTS evidence cannot be merge_candidate"

    [[ "$PARENT_CANDIDATE" == "false" ]] \
        || die "$RC_CONTRACT" \
            "Non-SUPPORTS evidence cannot be parent_candidate"

    [[ "$PROPAGATION_CANDIDATE" == "false" ]] \
        || die "$RC_CONTRACT" \
            "Non-SUPPORTS evidence cannot be propagation_candidate"
fi

#
# ------------------------------------------------------------------
# Stable identity
#
# Never generate identity from wall-clock time or randomness.
# ------------------------------------------------------------------
#

CANONICAL_ID_MATERIAL="$(
    printf '%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$DOMAIN" \
        "$HOST" \
        "$SERVICE" \
        "$DEVICE" \
        "$OBSERVED_AT" \
        "$DIAGNOSTIC" \
        "$CAUSE_CLASS" \
        "$CONTRIBUTION"
)"

ID_HASH="$(
    printf '%s' "$CANONICAL_ID_MATERIAL" |
    sha256sum |
    awk '{print toupper(substr($1,1,24))}'
)"

if [[ -n "$UPSTREAM_EVENT_ID" ]]; then
    EVENT_ID="$UPSTREAM_EVENT_ID"
else
    EVENT_ID="EVT-$ID_HASH"
fi

if [[ -n "$UPSTREAM_EVIDENCE_ID" ]]; then
    EVIDENCE_ID="$UPSTREAM_EVIDENCE_ID"
else
    EVIDENCE_ID="$(
        printf '%s' "$CANONICAL_ID_MATERIAL" |
        sha256sum |
        awk '{print "evidence:" substr($1,1,32)}'
    )"
fi

#
# Canonical fallback correlation key.
#

if [[ -z "$CORRELATION_KEY" ]]; then
    host_key="$(
        printf '%s' "$HOST" |
        tr '[:upper:]' '[:lower:]' |
        tr -cs 'a-z0-9._-' '_'
    )"

    domain_key="$(
        printf '%s' "$DOMAIN" |
        tr '[:upper:]' '[:lower:]'
    )"

    if [[ -n "$DEVICE" ]]; then
        object_key="$(
            printf '%s' "$DEVICE" |
            tr '[:upper:]' '[:lower:]' |
            tr -cs 'a-z0-9._-' '_'
        )"
    elif [[ -n "$SERVICE" ]]; then
        object_key="$(
            printf '%s' "$SERVICE" |
            tr '[:upper:]' '[:lower:]' |
            tr -cs 'a-z0-9._-' '_'
        )"
    else
        object_key="host"
    fi

    CORRELATION_KEY="linux:${host_key}:${domain_key}:${object_key}"
fi

if [[ -z "$FINGERPRINT" ]]; then
    diag_key="$(
        printf '%s' "$DIAGNOSTIC" |
        tr '[:upper:]' '[:lower:]' |
        tr -cs 'a-z0-9._-' '_'
    )"

    FINGERPRINT="${CORRELATION_KEY}:${diag_key}"
fi

#
# ------------------------------------------------------------------
# Output
# ------------------------------------------------------------------
#

JQ_ARGS=()

$PRETTY || JQ_ARGS+=(-c)

jq -n "${JQ_ARGS[@]}" \
    --arg schema_version "$SCHEMA_VERSION" \
    --arg normalizer_version "$VERSION" \
    --arg event_id "$EVENT_ID" \
    --arg request_id "$REQUEST_ID" \
    --arg evidence_id "$EVIDENCE_ID" \
    --arg correlation_key "$CORRELATION_KEY" \
    --arg fingerprint "$FINGERPRINT" \
    --arg domain "$DOMAIN" \
    --arg provider "$PROVIDER" \
    --arg host "$HOST" \
    --arg service "$SERVICE" \
    --arg cluster "$CLUSTER" \
    --arg device "$DEVICE" \
    --arg role "$ROLE" \
    --arg observed_at "$OBSERVED_AT" \
    --arg window_start "$WINDOW_START" \
    --arg window_end "$WINDOW_END" \
    --arg state "$STATE" \
    --arg diagnostic "$DIAGNOSTIC" \
    --arg severity "$SEVERITY" \
    --arg confidence "$CONFIDENCE" \
    --arg contribution "$CONTRIBUTION" \
    --arg evidence_role "$EVIDENCE_ROLE" \
    --arg cause_class "$CAUSE_CLASS" \
    --argjson weight "$WEIGHT" \
    --argjson merge_candidate "$MERGE_CANDIDATE" \
    --argjson parent_candidate "$PARENT_CANDIDATE" \
    --argjson propagation_candidate "$PROPAGATION_CANDIDATE" \
'
def nullable($v):
  if $v == "" then null else $v end;

{
  schema_version: $schema_version,

  normalizer: {
    name: "cross_domain_event_normalizer",
    version: $normalizer_version
  },

  identity: {
    event_id: $event_id,
    request_id: nullable($request_id),
    evidence_id: $evidence_id,
    correlation_key: $correlation_key,
    fingerprint: $fingerprint
  },

  source: {
    domain: $domain,
    provider: $provider,
    host: $host,
    service: nullable($service),
    cluster: nullable($cluster),
    device: nullable($device),
    role: nullable($role)
  },

  observation: {
    observed_at: $observed_at,
    window_start: nullable($window_start),
    window_end: nullable($window_end)
  },

  evidence: {
    state: $state,
    diagnostic_type: $diagnostic,
    severity: $severity,
    confidence: $confidence
  },

  correlation: {
    contribution: $contribution,
    evidence_role: $evidence_role,
    cause_class: $cause_class,
    weight: $weight
  },

  incident_hints: {
    create_incident: false,
    merge_candidate: $merge_candidate,
    parent_candidate: $parent_candidate,
    propagation_candidate: $propagation_candidate
  },

  provenance: {
    source_contract: "DOMAIN_CORRELATION_ADAPTER",
    canonicalized: true
  }
}
'

exit "$RC_OK"
