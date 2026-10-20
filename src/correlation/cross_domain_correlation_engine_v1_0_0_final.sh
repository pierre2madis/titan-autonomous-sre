#!/usr/bin/env bash
set -u
set -o pipefail

VERSION="1.0.0-final"
SCHEMA_VERSION="1.0"
ENGINE_NAME="cross_domain_correlation_engine"

RC_OK=0
RC_USAGE=2
RC_INPUT=20
RC_JSON=21
RC_SCHEMA=22
RC_RULES=23
RC_CONTRACT=24
RC_PROCESSING=25

SOURCE_EVENT=""
TARGET_EVENT=""
RULES_FILE=""
PRETTY=false

usage() {
  cat <<'EOF'
Usage:
  cross_domain_correlation_engine_v1_0_0_2_candidate.sh \
    --source-event FILE \
    --target-event FILE \
    --rules FILE \
    [--pretty]

Options:
  --source-event FILE   Canonical source event JSON
  --target-event FILE   Canonical target event JSON
  --rules FILE          Causal rule registry JSON
  --pretty              Pretty-print JSON output
  --version             Print version
  -h, --help            Show help
EOF
}

die() {
  local rc="$1"; shift
  printf 'ERROR: %s\n' "$*" >&2
  exit "$rc"
}

while (($#)); do
  case "$1" in
    --source-event)
      [[ $# -ge 2 ]] || die "$RC_USAGE" "Missing value for --source-event"
      SOURCE_EVENT="$2"; shift 2 ;;
    --target-event)
      [[ $# -ge 2 ]] || die "$RC_USAGE" "Missing value for --target-event"
      TARGET_EVENT="$2"; shift 2 ;;
    --rules)
      [[ $# -ge 2 ]] || die "$RC_USAGE" "Missing value for --rules"
      RULES_FILE="$2"; shift 2 ;;
    --pretty)
      PRETTY=true; shift ;;
    --version)
      printf '%s\n' "$VERSION"; exit 0 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "$RC_USAGE" "Unknown argument: $1" ;;
  esac
done

[[ -n "$SOURCE_EVENT" && -n "$TARGET_EVENT" && -n "$RULES_FILE" ]] || {
  usage >&2
  exit "$RC_USAGE"
}

for f in "$SOURCE_EVENT" "$TARGET_EVENT" "$RULES_FILE"; do
  [[ -r "$f" ]] || die "$RC_INPUT" "Input not readable: $f"
done

jq -e . "$SOURCE_EVENT" >/dev/null 2>&1 || die "$RC_JSON" "Malformed JSON: $SOURCE_EVENT"
jq -e . "$TARGET_EVENT" >/dev/null 2>&1 || die "$RC_JSON" "Malformed JSON: $TARGET_EVENT"
jq -e . "$RULES_FILE" >/dev/null 2>&1 || die "$RC_JSON" "Malformed JSON: $RULES_FILE"

sha24() {
  printf '%s' "$1" | sha256sum | awk '{print toupper(substr($1,1,24))}'
}

json_get() {
  local file="$1" expr="$2"
  jq -r "$expr // empty" "$file"
}

bool_get() {
  local file="$1" expr="$2"
  jq -r "$expr" "$file"
}

is_supported_domain() {
  case "$1" in
    CPU|MEMORY|BLOCK_IO|NETWORK|APPLICATION|SPLUNK|DYNATRACE|PROMETHEUS) return 0 ;;
    *) return 1 ;;
  esac
}

confidence_points() {
  case "$1" in
    HIGH) echo 6 ;;
    MEDIUM) echo 4 ;;
    LOW) echo 2 ;;
    NONE|UNKNOWN|"") echo 0 ;;
    *) echo 0 ;;
  esac
}

severity_points() {
  case "$1" in
    CRITICAL) echo 4 ;;
    WARNING) echo 2 ;;
    INFO) echo 1 ;;
    NONE|UNKNOWN|"") echo 0 ;;
    *) echo 0 ;;
  esac
}

topology_points() {
  case "$1" in
    SAME_DEVICE) echo 20 ;;
    SAME_HOST|SAME_SERVICE|UPSTREAM_DEPENDENCY|DOWNSTREAM_DEPENDENCY) echo 18 ;;
    SAME_CLUSTER) echo 14 ;;
    SHARED_DEPENDENCY) echo 12 ;;
    UNKNOWN_TOPOLOGY) echo 3 ;;
    NO_TOPOLOGY_RELATION|"") echo 0 ;;
    *) echo 0 ;;
  esac
}

classify_score() {
  local s="$1"
  if (( s >= 85 )); then echo VERY_STRONG
  elif (( s >= 70 )); then echo STRONG
  elif (( s >= 50 )); then echo PLAUSIBLE
  elif (( s >= 30 )); then echo WEAK
  else echo UNRELATED
  fi
}

temporal_score_and_class() {
  local lag="$1"
  local abs="$lag"
  (( abs < 0 )) && abs=$(( -abs ))
  if (( abs <= 30 )); then TEMPORAL_SCORE=25; TEMPORAL_CLASS="SIMULTANEOUS"
  elif (( abs <= 60 )); then TEMPORAL_SCORE=22; TEMPORAL_CLASS="PROPAGATION"
  elif (( abs <= 120 )); then TEMPORAL_SCORE=18; TEMPORAL_CLASS="PROPAGATION"
  elif (( abs <= 300 )); then TEMPORAL_SCORE=14; TEMPORAL_CLASS="PROPAGATION"
  elif (( abs <= 600 )); then TEMPORAL_SCORE=8; TEMPORAL_CLASS="EXTENDED_CAUSAL"
  elif (( abs <= 900 )); then TEMPORAL_SCORE=4; TEMPORAL_CLASS="EXTENDED_CAUSAL"
  else TEMPORAL_SCORE=0; TEMPORAL_CLASS="OUTSIDE_CAUSAL_WINDOW"
  fi
}

validate_event() {
  local f="$1"

  jq -e '
    .schema_version == "1.0" and
    (.identity.event_id|type=="string" and length>0) and
    (.identity.evidence_id|type=="string" and length>0) and
    (.identity.correlation_key|type=="string" and length>0) and
    (.identity.fingerprint|type=="string" and length>0) and
    (.source.domain|type=="string" and length>0) and
    (.source.host|type=="string" and length>0) and
    (.observation.observed_at|type=="string" and length>0) and
    (.evidence.state|type=="string" and length>0) and
    (.evidence.diagnostic_type|type=="string" and length>0) and
    (.evidence.severity|type=="string" and length>0) and
    (.evidence.confidence|type=="string" and length>0) and
    (.correlation.contribution|type=="string" and length>0) and
    (.correlation.evidence_role|type=="string" and length>0) and
    (.correlation.cause_class|type=="string" and length>0) and
    (.correlation.weight|type=="number") and
    (.incident_hints.create_incident == false)
  ' "$f" >/dev/null || return 1

  local domain state sev conf contrib role cause weight
  domain="$(json_get "$f" '.source.domain')"
  state="$(json_get "$f" '.evidence.state')"
  sev="$(json_get "$f" '.evidence.severity')"
  conf="$(json_get "$f" '.evidence.confidence')"
  contrib="$(json_get "$f" '.correlation.contribution')"
  role="$(json_get "$f" '.correlation.evidence_role')"
  cause="$(json_get "$f" '.correlation.cause_class')"
  weight="$(json_get "$f" '.correlation.weight')"

  is_supported_domain "$domain" || return 1
  [[ "$state" =~ ^(AVAILABLE|INSUFFICIENT|UNAVAILABLE)$ ]] || return 1
  [[ "$sev" =~ ^(NONE|INFO|WARNING|CRITICAL|UNKNOWN)$ ]] || return 1
  [[ "$conf" =~ ^(NONE|LOW|MEDIUM|HIGH|UNKNOWN)$ ]] || return 1
  [[ "$contrib" =~ ^(SUPPORTS|CONTRADICTS|INDETERMINATE|UNAVAILABLE)$ ]] || return 1
  [[ "$weight" =~ ^[0-9]+$ ]] || return 1
  (( weight >= 0 && weight <= 100 )) || return 1

  case "$state" in
    AVAILABLE)
      [[ "$contrib" == "SUPPORTS" || "$contrib" == "CONTRADICTS" ]] || return 1
      [[ "$sev" != "UNKNOWN" ]] || return 1
      ;;
    INSUFFICIENT)
      [[ "$contrib" == "INDETERMINATE" ]] || return 1
      ;;
    UNAVAILABLE)
      [[ "$contrib" == "UNAVAILABLE" ]] || return 1
      ;;
  esac

  case "$contrib" in
    SUPPORTS)
      [[ "$role" == "CAUSAL_CANDIDATE" ]] || return 1
      [[ "$cause" != "NONE" && "$cause" != "UNKNOWN" && -n "$cause" ]] || return 1
      (( weight > 0 )) || return 1
      ;;
    CONTRADICTS)
      [[ "$role" == "EXONERATING" ]] || return 1
      [[ "$weight" == "0" ]] || return 1
      ;;
    INDETERMINATE|UNAVAILABLE)
      [[ "$role" == "NON_DECISIVE" ]] || return 1
      [[ "$weight" == "0" ]] || return 1
      ;;
  esac

  return 0
}

registry_strength_points() {
  local strength="$1"

  jq -er --arg s "$strength" '
    [
      .. | objects |
      select(
        (.EXACT?   | type) == "number" and
        (.GENERIC? | type) == "number" and
        (.DOMAIN?  | type) == "number" and
        .EXACT == 20 and
        .GENERIC == 14 and
        .DOMAIN == 8
      ) |
      .[$s]
    ]
    | map(select(type == "number"))
    | unique
    | if length == 1 then .[0] else empty end
  ' "$RULES_FILE" 2>/dev/null
}

validate_rules() {
  jq -e '
    .schema_version == "1.0" and
    .registry.name == "cross_domain_causal_rule_registry" and
    (.rules|type=="array" and length>0) and
    ([.rules[].rule_id] | length == (unique|length)) and
    (
      [
        .. | objects |
        select(
          (.EXACT?   | type) == "number" and
          (.GENERIC? | type) == "number" and
          (.DOMAIN?  | type) == "number" and
          .EXACT == 20 and
          .GENERIC == 14 and
          .DOMAIN == 8
        )
      ] | length >= 1
    )
  ' "$RULES_FILE" >/dev/null || return 1
  return 0
}

validate_event "$SOURCE_EVENT" || die "$RC_CONTRACT" "Invalid canonical source event contract"
validate_event "$TARGET_EVENT" || die "$RC_CONTRACT" "Invalid canonical target event contract"
validate_rules || die "$RC_RULES" "Invalid causal rule registry"

SOURCE_EVENT_ID="$(json_get "$SOURCE_EVENT" '.identity.event_id')"
TARGET_EVENT_ID="$(json_get "$TARGET_EVENT" '.identity.event_id')"
SOURCE_FP="$(json_get "$SOURCE_EVENT" '.identity.fingerprint')"
TARGET_FP="$(json_get "$TARGET_EVENT" '.identity.fingerprint')"

SOURCE_DOMAIN="$(json_get "$SOURCE_EVENT" '.source.domain')"
TARGET_DOMAIN="$(json_get "$TARGET_EVENT" '.source.domain')"
SOURCE_PROVIDER="$(json_get "$SOURCE_EVENT" '.source.provider')"
TARGET_PROVIDER="$(json_get "$TARGET_EVENT" '.source.provider')"
SOURCE_HOST="$(json_get "$SOURCE_EVENT" '.source.host')"
TARGET_HOST="$(json_get "$TARGET_EVENT" '.source.host')"
SOURCE_SERVICE="$(json_get "$SOURCE_EVENT" '.source.service')"
TARGET_SERVICE="$(json_get "$TARGET_EVENT" '.source.service')"
SOURCE_CLUSTER="$(json_get "$SOURCE_EVENT" '.source.cluster')"
TARGET_CLUSTER="$(json_get "$TARGET_EVENT" '.source.cluster')"
SOURCE_DEVICE="$(json_get "$SOURCE_EVENT" '.source.device')"
TARGET_DEVICE="$(json_get "$TARGET_EVENT" '.source.device')"

SOURCE_OBSERVED="$(json_get "$SOURCE_EVENT" '.observation.observed_at')"
TARGET_OBSERVED="$(json_get "$TARGET_EVENT" '.observation.observed_at')"

SOURCE_STATE="$(json_get "$SOURCE_EVENT" '.evidence.state')"
TARGET_STATE="$(json_get "$TARGET_EVENT" '.evidence.state')"
SOURCE_DIAG="$(json_get "$SOURCE_EVENT" '.evidence.diagnostic_type')"
TARGET_DIAG="$(json_get "$TARGET_EVENT" '.evidence.diagnostic_type')"
SOURCE_SEVERITY="$(json_get "$SOURCE_EVENT" '.evidence.severity')"
TARGET_SEVERITY="$(json_get "$TARGET_EVENT" '.evidence.severity')"
SOURCE_CONFIDENCE="$(json_get "$SOURCE_EVENT" '.evidence.confidence')"
TARGET_CONFIDENCE="$(json_get "$TARGET_EVENT" '.evidence.confidence')"

SOURCE_CONTRIBUTION="$(json_get "$SOURCE_EVENT" '.correlation.contribution')"
TARGET_CONTRIBUTION="$(json_get "$TARGET_EVENT" '.correlation.contribution')"
SOURCE_CAUSE="$(json_get "$SOURCE_EVENT" '.correlation.cause_class')"
TARGET_CAUSE="$(json_get "$TARGET_EVENT" '.correlation.cause_class')"
SOURCE_WEIGHT="$(json_get "$SOURCE_EVENT" '.correlation.weight')"
TARGET_WEIGHT="$(json_get "$TARGET_EVENT" '.correlation.weight')"

SOURCE_EPOCH="$(date -u -d "$SOURCE_OBSERVED" +%s 2>/dev/null)" || die "$RC_CONTRACT" "Invalid source observed_at"
TARGET_EPOCH="$(date -u -d "$TARGET_OBSERVED" +%s 2>/dev/null)" || die "$RC_CONTRACT" "Invalid target observed_at"
LAG_SECONDS=$(( TARGET_EPOCH - SOURCE_EPOCH ))

temporal_score_and_class "$LAG_SECONDS"

OBSERVED_TOPOLOGIES=()

if [[ -n "$SOURCE_DEVICE" && -n "$TARGET_DEVICE" &&
      "$SOURCE_DEVICE" == "$TARGET_DEVICE" &&
      "$SOURCE_HOST" == "$TARGET_HOST" ]]; then
  OBSERVED_TOPOLOGIES+=("SAME_DEVICE")
fi
if [[ -n "$SOURCE_HOST" && "$SOURCE_HOST" == "$TARGET_HOST" ]]; then
  OBSERVED_TOPOLOGIES+=("SAME_HOST")
fi
if [[ -n "$SOURCE_SERVICE" && -n "$TARGET_SERVICE" &&
      "$SOURCE_SERVICE" == "$TARGET_SERVICE" ]]; then
  OBSERVED_TOPOLOGIES+=("SAME_SERVICE")
fi
if [[ -n "$SOURCE_CLUSTER" && -n "$TARGET_CLUSTER" &&
      "$SOURCE_CLUSTER" == "$TARGET_CLUSTER" ]]; then
  OBSERVED_TOPOLOGIES+=("SAME_CLUSTER")
fi
if ((${#OBSERVED_TOPOLOGIES[@]} == 0)); then
  OBSERVED_TOPOLOGIES+=("UNKNOWN_TOPOLOGY")
fi

SELECTED_TOPOLOGY="UNKNOWN_TOPOLOGY"
TOPOLOGY_SCORE=-1
for topo in "${OBSERVED_TOPOLOGIES[@]}"; do
  pts="$(topology_points "$topo")"
  if (( pts > TOPOLOGY_SCORE )); then
    SELECTED_TOPOLOGY="$topo"
    TOPOLOGY_SCORE="$pts"
  fi
done

OBSERVED_TOPOLOGIES_JSON="$(printf '%s\n' "${OBSERVED_TOPOLOGIES[@]}" | jq -R . | jq -s .)"

min2() {
  if (( $1 < $2 )); then echo "$1"; else echo "$2"; fi
}

WEIGHT_MIN="$(min2 "$SOURCE_WEIGHT" "$TARGET_WEIGHT")"
WEIGHT_POINTS=$(( WEIGHT_MIN * 20 / 100 ))
CONF_MIN="$(min2 "$(confidence_points "$SOURCE_CONFIDENCE")" "$(confidence_points "$TARGET_CONFIDENCE")")"
SEV_MIN="$(min2 "$(severity_points "$SOURCE_SEVERITY")" "$(severity_points "$TARGET_SEVERITY")")"
EVIDENCE_SCORE=$(( WEIGHT_POINTS + CONF_MIN + SEV_MIN ))
(( EVIDENCE_SCORE > 30 )) && EVIDENCE_SCORE=30

CORROBORATION_SCORE=0
if [[ "$SOURCE_PROVIDER" != "$TARGET_PROVIDER" &&
      "$SOURCE_CONTRIBUTION" == "SUPPORTS" &&
      "$TARGET_CONTRIBUTION" == "SUPPORTS" ]]; then
  CORROBORATION_SCORE=3
fi

NEGATIVE_PENALTY=0
NON_DECISIVE=false
BLOCKING_FACTORS=()

if [[ "$SOURCE_STATE" != "AVAILABLE" || "$TARGET_STATE" != "AVAILABLE" ]]; then
  NON_DECISIVE=true
  BLOCKING_FACTORS+=("NON_DECISIVE_EVIDENCE_PRESENT")
fi

if [[ "$SOURCE_CONTRIBUTION" == "CONTRADICTS" ||
      "$TARGET_CONTRIBUTION" == "CONTRADICTS" ]]; then
  NEGATIVE_PENALTY=20
  BLOCKING_FACTORS+=("EXONERATING_EVIDENCE_PRESENT")
fi

# SAME_EVENT detection is independent from the causal registry.
SAME_EVENT=false
if [[ "$SOURCE_EVENT_ID" == "$TARGET_EVENT_ID" ||
      "$SOURCE_FP" == "$TARGET_FP" ]]; then
  SAME_EVENT=true
else
  abs_lag="$LAG_SECONDS"; (( abs_lag < 0 )) && abs_lag=$(( -abs_lag ))
  if [[ "$SOURCE_DOMAIN" == "$TARGET_DOMAIN" &&
        "$SOURCE_HOST" == "$TARGET_HOST" &&
        "$SOURCE_DIAG" == "$TARGET_DIAG" ]] &&
     (( abs_lag <= 30 )); then
    SAME_EVENT=true
  fi
fi

# Registry matches: direct source cause -> target diagnostic.
DIRECT_MATCHES="$(jq -c \
  --arg sd "$SOURCE_DOMAIN" \
  --arg sc "$SOURCE_CAUSE" \
  --arg td "$TARGET_DOMAIN" \
  --arg tg "$TARGET_DIAG" \
  '[.rules[] | select(
      .enabled == true and
      .source.domain == $sd and
      .source.cause_class == $sc and
      .target.domain == $td and
      .target.diagnostic_type == $tg and
      .relationship == "CAUSE_OF"
  )]' "$RULES_FILE")"

INVERSE_MATCHES="$(jq -c \
  --arg sd "$TARGET_DOMAIN" \
  --arg sc "$TARGET_CAUSE" \
  --arg td "$SOURCE_DOMAIN" \
  --arg tg "$SOURCE_DIAG" \
  '[.rules[] | select(
      .enabled == true and
      .source.domain == $sd and
      .source.cause_class == $sc and
      .target.domain == $td and
      .target.diagnostic_type == $tg and
      .relationship == "CAUSE_OF"
  )]' "$RULES_FILE")"

DIRECT_COUNT="$(jq 'length' <<<"$DIRECT_MATCHES")"
INVERSE_COUNT="$(jq 'length' <<<"$INVERSE_MATCHES")"

(( DIRECT_COUNT <= 1 )) || die "$RC_RULES" "Multiple matching direct causal rules"
(( INVERSE_COUNT <= 1 )) || die "$RC_RULES" "Multiple matching inverse causal rules"

RULE_MATCHED=false
RULE_ELIGIBLE=false
RULE_ID="NONE"
RULE_STRENGTH="NONE"
RULE_DEFINED_POINTS=0
RULE_POINTS=0
RULE_MIN_LAG=0
RULE_MAX_LAG=0
DIRECTION_VALID=false
TOPOLOGY_ALLOWED=false
RELATIONSHIP_DIRECTION="NONE"
RULE_SELECTED_TOPOLOGY=""
RULE_SELECTED_TOPOLOGY_SCORE=0
RULE_ORIENTATION="NONE"

select_rule_topology() {
  local rule_json="$1"
  local allowed
  allowed="$(jq -c '.topology.allowed' <<<"$rule_json")"

  local best="" best_score=-1 t p
  for t in "${OBSERVED_TOPOLOGIES[@]}"; do
    if jq -e --arg t "$t" 'index($t) != null' <<<"$allowed" >/dev/null 2>&1; then
      p="$(topology_points "$t")"
      if (( p > best_score )); then
        best="$t"; best_score="$p"
      fi
    fi
  done

  if [[ -n "$best" ]]; then
    RULE_SELECTED_TOPOLOGY="$best"
    RULE_SELECTED_TOPOLOGY_SCORE="$best_score"
    TOPOLOGY_ALLOWED=true
  else
    RULE_SELECTED_TOPOLOGY=""
    RULE_SELECTED_TOPOLOGY_SCORE=0
    TOPOLOGY_ALLOWED=false
  fi
}

if (( DIRECT_COUNT == 1 )); then
  RULE_MATCHED=true
  RULE_ORIENTATION="DIRECT"
  RULE_JSON="$(jq -c '.[0]' <<<"$DIRECT_MATCHES")"
  RULE_ID="$(jq -r '.rule_id' <<<"$RULE_JSON")"
  RULE_STRENGTH="$(jq -r '
    if (.strength|type) == "string" then .strength
    elif (.strength|type) == "object" then (.strength.class // empty)
    else empty end
  ' <<<"$RULE_JSON")"

  RULE_DEFINED_POINTS="$(jq -r '
    if (.points|type) == "number" then .points
    elif ((.strength|type) == "object" and (.strength.points|type) == "number") then .strength.points
    else empty end
  ' <<<"$RULE_JSON")"

  if [[ -z "$RULE_DEFINED_POINTS" ]]; then
    RULE_DEFINED_POINTS="$(registry_strength_points "$RULE_STRENGTH" || true)"
  fi

  RULE_MIN_LAG="$(jq -r '.temporal.min_lag_seconds' <<<"$RULE_JSON")"
  RULE_MAX_LAG="$(jq -r '.temporal.max_lag_seconds' <<<"$RULE_JSON")"

  [[ "$RULE_STRENGTH" =~ ^(EXACT|GENERIC|DOMAIN)$ ]] || die "$RC_RULES" "Invalid rule strength for $RULE_ID"
  [[ "$RULE_DEFINED_POINTS" =~ ^[0-9]+$ ]] || die "$RC_RULES" "Invalid rule points for $RULE_ID"
  case "$RULE_STRENGTH" in
    EXACT)   (( RULE_DEFINED_POINTS == 20 )) || die "$RC_RULES" "EXACT rule must score 20 points: $RULE_ID" ;;
    GENERIC) (( RULE_DEFINED_POINTS == 14 )) || die "$RC_RULES" "GENERIC rule must score 14 points: $RULE_ID" ;;
    DOMAIN)  (( RULE_DEFINED_POINTS == 8 ))  || die "$RC_RULES" "DOMAIN rule must score 8 points: $RULE_ID" ;;
  esac
  [[ "$RULE_MIN_LAG" =~ ^[0-9]+$ && "$RULE_MAX_LAG" =~ ^[0-9]+$ ]] || die "$RC_RULES" "Invalid temporal rule fields for $RULE_ID"

  CAUSE_TO_EFFECT_LAG=$(( TARGET_EPOCH - SOURCE_EPOCH ))
  if (( CAUSE_TO_EFFECT_LAG >= RULE_MIN_LAG && CAUSE_TO_EFFECT_LAG <= RULE_MAX_LAG )); then
    DIRECTION_VALID=true
  fi

  select_rule_topology "$RULE_JSON"

elif (( INVERSE_COUNT == 1 )); then
  RULE_MATCHED=true
  RULE_ORIENTATION="INVERSE"
  RULE_JSON="$(jq -c '.[0]' <<<"$INVERSE_MATCHES")"
  RULE_ID="$(jq -r '.rule_id' <<<"$RULE_JSON")"
  RULE_STRENGTH="$(jq -r '
    if (.strength|type) == "string" then .strength
    elif (.strength|type) == "object" then (.strength.class // empty)
    else empty end
  ' <<<"$RULE_JSON")"

  RULE_DEFINED_POINTS="$(jq -r '
    if (.points|type) == "number" then .points
    elif ((.strength|type) == "object" and (.strength.points|type) == "number") then .strength.points
    else empty end
  ' <<<"$RULE_JSON")"

  if [[ -z "$RULE_DEFINED_POINTS" ]]; then
    RULE_DEFINED_POINTS="$(registry_strength_points "$RULE_STRENGTH" || true)"
  fi

  RULE_MIN_LAG="$(jq -r '.temporal.min_lag_seconds' <<<"$RULE_JSON")"
  RULE_MAX_LAG="$(jq -r '.temporal.max_lag_seconds' <<<"$RULE_JSON")"

  [[ "$RULE_STRENGTH" =~ ^(EXACT|GENERIC|DOMAIN)$ ]] || die "$RC_RULES" "Invalid rule strength for $RULE_ID"
  [[ "$RULE_DEFINED_POINTS" =~ ^[0-9]+$ ]] || die "$RC_RULES" "Invalid rule points for $RULE_ID"
  case "$RULE_STRENGTH" in
    EXACT)   (( RULE_DEFINED_POINTS == 20 )) || die "$RC_RULES" "EXACT rule must score 20 points: $RULE_ID" ;;
    GENERIC) (( RULE_DEFINED_POINTS == 14 )) || die "$RC_RULES" "GENERIC rule must score 14 points: $RULE_ID" ;;
    DOMAIN)  (( RULE_DEFINED_POINTS == 8 ))  || die "$RC_RULES" "DOMAIN rule must score 8 points: $RULE_ID" ;;
  esac
  [[ "$RULE_MIN_LAG" =~ ^[0-9]+$ && "$RULE_MAX_LAG" =~ ^[0-9]+$ ]] || die "$RC_RULES" "Invalid temporal rule fields for $RULE_ID"

  CAUSE_TO_EFFECT_LAG=$(( SOURCE_EPOCH - TARGET_EPOCH ))
  if (( CAUSE_TO_EFFECT_LAG >= RULE_MIN_LAG && CAUSE_TO_EFFECT_LAG <= RULE_MAX_LAG )); then
    DIRECTION_VALID=true
  fi

  select_rule_topology "$RULE_JSON"
fi

if [[ "$RULE_MATCHED" == "true" ]]; then
  [[ "$DIRECTION_VALID" == "true" ]] || BLOCKING_FACTORS+=("INVALID_TEMPORAL_DIRECTION")
  [[ "$TOPOLOGY_ALLOWED" == "true" ]] || BLOCKING_FACTORS+=("TOPOLOGY_NOT_ALLOWED")
fi

if [[ "$RULE_MATCHED" == "true" &&
      "$DIRECTION_VALID" == "true" &&
      "$TOPOLOGY_ALLOWED" == "true" &&
      "$SOURCE_STATE" == "AVAILABLE" &&
      "$TARGET_STATE" == "AVAILABLE" &&
      "$SOURCE_CONTRIBUTION" == "SUPPORTS" &&
      "$TARGET_CONTRIBUTION" == "SUPPORTS" ]]; then
  RULE_ELIGIBLE=true
  RULE_POINTS="$RULE_DEFINED_POINTS"
  SELECTED_TOPOLOGY="$RULE_SELECTED_TOPOLOGY"
  TOPOLOGY_SCORE="$RULE_SELECTED_TOPOLOGY_SCORE"
fi

RAW_TOTAL=$((
  EVIDENCE_SCORE +
  TEMPORAL_SCORE +
  TOPOLOGY_SCORE +
  RULE_POINTS +
  CORROBORATION_SCORE
))
(( RAW_TOTAL > 100 )) && RAW_TOTAL=100

EFFECTIVE_TOTAL=$(( RAW_TOTAL - NEGATIVE_PENALTY ))
(( EFFECTIVE_TOTAL < 0 )) && EFFECTIVE_TOTAL=0
(( EFFECTIVE_TOTAL > 100 )) && EFFECTIVE_TOTAL=100

CLASSIFICATION="$(classify_score "$EFFECTIVE_TOTAL")"

RELATIONSHIP="UNRELATED"
RELATIONSHIP_DIRECTION="NONE"

if [[ "$SAME_EVENT" == "true" &&
      "$NON_DECISIVE" == "false" ]] &&
   (( EFFECTIVE_TOTAL >= 70 )); then
  RELATIONSHIP="SAME_EVENT"

elif [[ "$RULE_ELIGIBLE" == "true" &&
        "$RULE_ORIENTATION" == "DIRECT" &&
        "$NEGATIVE_PENALTY" -eq 0 ]] &&
     (( EFFECTIVE_TOTAL >= 70 )); then
  RELATIONSHIP="CAUSE_OF"
  RELATIONSHIP_DIRECTION="SOURCE_TO_TARGET"

elif [[ "$RULE_ELIGIBLE" == "true" &&
        "$RULE_ORIENTATION" == "INVERSE" &&
        "$NEGATIVE_PENALTY" -eq 0 ]] &&
     (( EFFECTIVE_TOTAL >= 70 )); then
  RELATIONSHIP="SYMPTOM_OF"
  RELATIONSHIP_DIRECTION="TARGET_TO_SOURCE"

elif [[ "$NON_DECISIVE" == "false" ]] &&
     (( EFFECTIVE_TOTAL >= 50 )); then
  RELATIONSHIP="CORRELATED_WITH"
fi

ACTION="NONE"
ACTION_CONFIDENCE="LOW"
SUMMARY="Available evidence does not establish a sufficiently strong relationship."

case "$RELATIONSHIP" in
  SAME_EVENT)
    ACTION="MERGE"
    ACTION_CONFIDENCE="HIGH"
    SUMMARY="Events are consistent with independent observations of the same phenomenon."
    ;;
  CAUSE_OF)
    ACTION="ATTACH_CHILD"
    if (( EFFECTIVE_TOTAL >= 85 )); then ACTION_CONFIDENCE="HIGH"; else ACTION_CONFIDENCE="MEDIUM"; fi
    SUMMARY="Source event is a credible directional causal candidate for target event."
    ;;
  SYMPTOM_OF)
    ACTION="ATTACH_CHILD"
    if (( EFFECTIVE_TOTAL >= 85 )); then ACTION_CONFIDENCE="HIGH"; else ACTION_CONFIDENCE="MEDIUM"; fi
    SUMMARY="Source event is a credible symptom of a causal target-side event."
    ;;
  CORRELATED_WITH)
    ACTION="ATTACH_EVIDENCE"
    ACTION_CONFIDENCE="MEDIUM"
    SUMMARY="Events are plausibly related, but directional causality is not established."
    ;;
esac

SUPPORTING_FACTORS=()
(( EVIDENCE_SCORE > 0 )) && SUPPORTING_FACTORS+=("EVIDENCE_STRENGTH")
(( TEMPORAL_SCORE > 0 )) && SUPPORTING_FACTORS+=("TEMPORAL_PROXIMITY")
(( TOPOLOGY_SCORE > 0 )) && SUPPORTING_FACTORS+=("TOPOLOGY_RELATIONSHIP")
(( RULE_POINTS > 0 )) && SUPPORTING_FACTORS+=("EXPLICIT_CAUSAL_RULE")
(( CORROBORATION_SCORE > 0 )) && SUPPORTING_FACTORS+=("CROSS_SOURCE_CORROBORATION")

SUPPORTING_JSON="$(printf '%s\n' "${SUPPORTING_FACTORS[@]:-}" | sed '/^$/d' | jq -R . | jq -s .)"
BLOCKING_JSON="$(printf '%s\n' "${BLOCKING_FACTORS[@]:-}" | sed '/^$/d' | jq -R . | jq -s .)"

PAIR_FP_A="$SOURCE_FP"
PAIR_FP_B="$TARGET_FP"
if [[ "$PAIR_FP_A" > "$PAIR_FP_B" ]]; then
  tmp="$PAIR_FP_A"; PAIR_FP_A="$PAIR_FP_B"; PAIR_FP_B="$tmp"
fi

CORRELATION_ID="CORR-$(sha24 "${SOURCE_EVENT_ID}|${TARGET_EVENT_ID}|${RELATIONSHIP}|${RULE_ID}")"
CANDIDATE_GROUP_ID="CG-$(sha24 "${PAIR_FP_A}|${PAIR_FP_B}|${RELATIONSHIP}|${RULE_ID}")"

OUTPUT="$(
jq -n \
  --arg schema "$SCHEMA_VERSION" \
  --arg engine_name "$ENGINE_NAME" \
  --arg engine_version "$VERSION" \
  --arg correlation_id "$CORRELATION_ID" \
  --arg candidate_group_id "$CANDIDATE_GROUP_ID" \
  --arg source_event_id "$SOURCE_EVENT_ID" \
  --arg target_event_id "$TARGET_EVENT_ID" \
  --arg rel "$RELATIONSHIP" \
  --arg dir "$RELATIONSHIP_DIRECTION" \
  --argjson evidence_score "$EVIDENCE_SCORE" \
  --argjson temporal_score "$TEMPORAL_SCORE" \
  --argjson topology_score "$TOPOLOGY_SCORE" \
  --argjson rule_points "$RULE_POINTS" \
  --argjson corroboration "$CORROBORATION_SCORE" \
  --argjson raw_total "$RAW_TOTAL" \
  --argjson negative_penalty "$NEGATIVE_PENALTY" \
  --argjson effective_total "$EFFECTIVE_TOTAL" \
  --arg classification "$CLASSIFICATION" \
  --argjson lag_seconds "$LAG_SECONDS" \
  --arg window_class "$TEMPORAL_CLASS" \
  --argjson direction_valid "$DIRECTION_VALID" \
  --arg topology_relationship "$SELECTED_TOPOLOGY" \
  --argjson observed_topologies "$OBSERVED_TOPOLOGIES_JSON" \
  --argjson topology_allowed "$TOPOLOGY_ALLOWED" \
  --argjson rule_matched "$RULE_MATCHED" \
  --argjson rule_eligible "$RULE_ELIGIBLE" \
  --arg rule_id "$RULE_ID" \
  --arg rule_strength "$RULE_STRENGTH" \
  --argjson rule_min_lag "$RULE_MIN_LAG" \
  --argjson rule_max_lag "$RULE_MAX_LAG" \
  --arg summary "$SUMMARY" \
  --argjson supporting "$SUPPORTING_JSON" \
  --argjson blocking "$BLOCKING_JSON" \
  --arg action "$ACTION" \
  --arg action_confidence "$ACTION_CONFIDENCE" \
  '{
    schema_version: $schema,
    engine: {
      name: $engine_name,
      version: $engine_version
    },
    identity: {
      correlation_id: $correlation_id,
      candidate_group_id: $candidate_group_id
    },
    events: {
      source_event_id: $source_event_id,
      target_event_id: $target_event_id
    },
    relationship: {
      type: $rel,
      direction: $dir
    },
    scores: {
      evidence_strength: $evidence_score,
      temporal: $temporal_score,
      topology: $topology_score,
      causal_rule: $rule_points,
      corroboration: $corroboration,
      raw_total: $raw_total,
      negative_penalty: $negative_penalty,
      effective_total: $effective_total,
      classification: $classification
    },
    temporal: {
      lag_seconds: $lag_seconds,
      window_class: $window_class,
      direction_valid: $direction_valid
    },
    topology: {
      relationship: $topology_relationship,
      observed_relationships: $observed_topologies,
      causal_rule_allows_topology: $topology_allowed
    },
    causal_rule: {
      matched: $rule_matched,
      eligible: $rule_eligible,
      rule_id: $rule_id,
      strength: $rule_strength,
      min_lag_seconds: $rule_min_lag,
      max_lag_seconds: $rule_max_lag
    },
    explanation: {
      summary: $summary,
      supporting_factors: $supporting,
      blocking_factors: $blocking
    },
    incident_recommendation: {
      action: $action,
      confidence: $action_confidence,
      advisory_only: true
    },
    ownership: {
      creates_incident: false,
      owns_lifecycle: false,
      establishes_root_cause: false
    }
  }'
)" || die "$RC_PROCESSING" "Unable to construct correlation result"

if [[ "$PRETTY" == "true" ]]; then
  jq . <<<"$OUTPUT"
else
  jq -c . <<<"$OUTPUT"
fi

exit "$RC_OK"
