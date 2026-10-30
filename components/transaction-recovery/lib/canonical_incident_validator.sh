#!/usr/bin/env bash
set -u
set -o pipefail

VERSION="1.0.0-final"

RC_OK=0
RC_USAGE=2
RC_INPUT=20
RC_JSON=21
RC_SCHEMA=22
RC_CONTRACT=24

usage() {
  cat <<'EOF'
Usage:
  canonical_incident_validator_v1_0_0_0_candidate.sh --input FILE [--pretty]
  canonical_incident_validator_v1_0_0_0_candidate.sh --version
EOF
}

die() {
  local rc="$1"; shift
  echo "ERROR: $*" >&2
  exit "$rc"
}

INPUT=""
PRETTY=false

while (($#)); do
  case "$1" in
    --input)
      [[ $# -ge 2 ]] || die "$RC_USAGE" "--input requires FILE"
      INPUT="$2"; shift 2 ;;
    --pretty)
      PRETTY=true; shift ;;
    --version)
      echo "$VERSION"; exit 0 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "$RC_USAGE" "Unknown argument: $1" ;;
  esac
done

[[ -n "$INPUT" ]] || die "$RC_USAGE" "--input is required"
[[ -r "$INPUT" ]] || die "$RC_INPUT" "Input not readable: $INPUT"
jq -e . "$INPUT" >/dev/null 2>&1 || die "$RC_JSON" "Malformed JSON"

# Top-level structure.
jq -e '
  .schema_version == "1.0" and
  (.identity|type)=="object" and
  (.classification|type)=="object" and
  (.lifecycle|type)=="object" and
  (.scope|type)=="object" and
  (.causality|type)=="object" and
  (.evidence|type)=="object" and
  (.impact|type)=="object" and
  (.slo|type)=="object" and
  (.deduplication|type)=="object" and
  (.automation|type)=="object" and
  (.audit|type)=="object"
' "$INPUT" >/dev/null || die "$RC_SCHEMA" "Unsupported or incomplete canonical incident schema"

# Identity contract.
jq -e '
  (.identity.incident_id|type)=="string" and
  (.identity.incident_id|test("^INC-[A-F0-9]{24}$")) and
  (.identity.incident_fingerprint|type)=="string" and
  (.identity.incident_fingerprint|length)>=3 and
  (
    .identity.correlation_group_id == null or
    ((.identity.correlation_group_id|type)=="string" and
     (.identity.correlation_group_id|test("^CG-[A-F0-9]{24}$")))
  ) and
  (
    .identity.parent_incident_id == null or
    ((.identity.parent_incident_id|type)=="string" and
     (.identity.parent_incident_id|test("^INC-[A-F0-9]{24}$")))
  ) and
  (.identity.root_incident_id|type)=="string" and
  (.identity.root_incident_id|test("^INC-[A-F0-9]{24}$")) and
  (.identity.incident_sequence|type)=="number" and
  (.identity.incident_sequence|floor)==.identity.incident_sequence and
  .identity.incident_sequence >= 1
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid incident identity"

# No self-parenting.
jq -e '
  (.identity.parent_incident_id == null) or
  (.identity.parent_incident_id != .identity.incident_id)
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Incident cannot be its own parent"

# Root consistency: root incident points to itself when no parent.
jq -e '
  if .identity.parent_incident_id == null
  then .identity.root_incident_id == .identity.incident_id
  else .identity.root_incident_id != .identity.incident_id
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid root/parent incident relationship"

# Classification.
jq -e '
  (.classification.incident_type |
    IN("RESOURCE_CONTENTION","SERVICE_DEGRADATION","AVAILABILITY","INGESTION","SEARCH","NETWORK","STORAGE","APPLICATION","SECURITY","UNKNOWN")) and
  (.classification.severity | IN("NONE","INFO","WARNING","CRITICAL")) and
  (.classification.priority | IN("P1","P2","P3","P4","NONE")) and
  (.classification.confidence | IN("NONE","LOW","MEDIUM","HIGH","UNKNOWN")) and
  (.classification.rca_state | IN("UNKNOWN","CANDIDATE","IDENTIFIED","VALIDATED"))
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid classification"

# Lifecycle.
jq -e '
  (.lifecycle.state |
    IN("INCIDENT","ACKNOWLEDGED","INVESTIGATING","RCA_IDENTIFIED","MITIGATING","RECOVERING","RESOLVED","CLOSED")) and
  (
    .lifecycle.previous_state == null or
    (.lifecycle.previous_state |
      IN("INCIDENT","ACKNOWLEDGED","INVESTIGATING","RCA_IDENTIFIED","MITIGATING","RECOVERING","RESOLVED","CLOSED"))
  ) and
  (.lifecycle.transition_reason|type)=="string" and
  (.lifecycle.transition_reason|length)>=3 and
  (
    [.lifecycle.generation,.lifecycle.reopen_count,.lifecycle.bad_windows,.lifecycle.good_windows]
    | all(type=="number" and floor==.)
  )
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid lifecycle structure"

jq -e '
  .lifecycle.generation >= 1 and
  .lifecycle.reopen_count >= 0 and
  .lifecycle.bad_windows >= 0 and
  .lifecycle.good_windows >= 0
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid lifecycle counters"

# RCA semantic gate.
jq -e '
  if .lifecycle.state == "RCA_IDENTIFIED"
  then (.classification.rca_state | IN("IDENTIFIED","VALIDATED"))
  else true
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "RCA_IDENTIFIED lifecycle requires identified/validated RCA state"

# Causality.
jq -e '
  (.causality.root_cause_domain |
    IN("CPU","MEMORY","BLOCK_IO","NETWORK","APPLICATION","SPLUNK","DYNATRACE","PROMETHEUS","UNKNOWN")) and
  (.causality.root_cause_class|type)=="string" and
  (.causality.relationship |
    IN("SAME_EVENT","CAUSE_OF","SYMPTOM_OF","CORRELATED_WITH","UNRELATED","UNKNOWN")) and
  (.causality.correlation_score|type)=="number" and
  (.causality.correlation_score|floor)==.causality.correlation_score and
  .causality.correlation_score >= 0 and .causality.correlation_score <= 100 and
  (.causality.correlation_classification |
    IN("UNRELATED","WEAK","PLAUSIBLE","STRONG","VERY_STRONG","UNKNOWN"))
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid causality section"

# Evidence buckets and semantic contribution alignment.
jq -e '
  (.evidence.supporting|type)=="array" and
  (.evidence.exonerating|type)=="array" and
  (.evidence.indeterminate|type)=="array" and
  (.evidence.unavailable|type)=="array" and
  ([.evidence.supporting[]?.contribution]   | all(.=="SUPPORTS")) and
  ([.evidence.exonerating[]?.contribution] | all(.=="CONTRADICTS")) and
  ([.evidence.indeterminate[]?.contribution] | all(.=="INDETERMINATE")) and
  ([.evidence.unavailable[]?.contribution] | all(.=="UNAVAILABLE"))
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Evidence bucket/contribution mismatch"

# Evidence refs.
jq -e '
  [
    .evidence.supporting[],
    .evidence.exonerating[],
    .evidence.indeterminate[],
    .evidence.unavailable[]
  ] |
  all(
    (.event_id|type)=="string" and
    (.event_id|test("^EVT-[A-F0-9]{24}$")) and
    (.evidence_id|type)=="string" and
    (.evidence_id|length)>=3 and
    (.domain|IN("CPU","MEMORY","BLOCK_IO","NETWORK","APPLICATION","SPLUNK","DYNATRACE","PROMETHEUS")) and
    (.diagnostic_type|type)=="string" and
    (.diagnostic_type|length)>=1 and
    (.contribution|IN("SUPPORTS","CONTRADICTS","INDETERMINATE","UNAVAILABLE"))
  )
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid evidence reference"

# Same event must not appear in more than one evidence bucket.
jq -e '
  [
    .evidence.supporting[]?.event_id,
    .evidence.exonerating[]?.event_id,
    .evidence.indeterminate[]?.event_id,
    .evidence.unavailable[]?.event_id
  ] as $ids |
  ($ids|length) == ($ids|unique|length)
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Duplicate event across evidence buckets"

# SLO consistency.
jq -e '
  if .slo.impacted == false
  then (
    .slo.fast_burn == false and
    .slo.slow_burn == false and
    (.slo.burn_rate == null or .slo.burn_rate >= 0)
  )
  else (.slo.slo_id != null)
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid SLO semantics"

# Dedup uniqueness and no self-merge.
jq -e '
  . as $root |
  (.deduplication.event_ids|type)=="array" and
  (.deduplication.correlation_ids|type)=="array" and
  (.deduplication.merged_incident_ids|type)=="array" and
  (.deduplication.event_ids|length)==(.deduplication.event_ids|unique|length) and
  (.deduplication.correlation_ids|length)==(.deduplication.correlation_ids|unique|length) and
  (.deduplication.merged_incident_ids|length)==(.deduplication.merged_incident_ids|unique|length) and
  ((.deduplication.merged_incident_ids|index($root.identity.incident_id)) == null)
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid deduplication section"

# CLOSED immutability guard at model level.
jq -e '
  if .lifecycle.state == "CLOSED"
  then .deduplication.reopen_eligible == false
  else true
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "CLOSED incident cannot remain reopen-eligible"

# Remediation gate: no remediation before sufficient RCA.
jq -e '
  if .automation.remediation_allowed == true
  then (.classification.rca_state | IN("IDENTIFIED","VALIDATED"))
  else true
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Remediation requires identified/validated RCA"

# Audit sequence must be contiguous 1..N, and terminal audit state must match lifecycle state.
jq -e '
  (.audit.transitions|type)=="array" and
  if (.audit.transitions|length)==0 then
    false
  else
    ([.audit.transitions[].sequence] == [range(1; (.audit.transitions|length)+1)]) and
    (.audit.transitions[-1].to == .lifecycle.state)
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Invalid audit transition sequence or terminal state"

# First transition must create INCIDENT.
jq -e '
  (.audit.transitions[0].sequence == 1) and
  (.audit.transitions[0].from == null) and
  (.audit.transitions[0].to == "INCIDENT")
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Audit must begin with null -> INCIDENT"

# Transition chain continuity.
jq -e '
  .audit.transitions as $t |
  if ($t|length) <= 1 then true
  else
    [range(1; $t|length) as $i | ($t[$i].from == $t[$i-1].to)] | all
  end
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Audit transition chain is discontinuous"

# Allowed lifecycle transitions.
jq -e '
  def allowed($f;$t):
    ($f==null and $t=="INCIDENT") or
    ($f=="INCIDENT" and ($t=="ACKNOWLEDGED" or $t=="RESOLVED")) or
    ($f=="ACKNOWLEDGED" and ($t=="INVESTIGATING" or $t=="RESOLVED")) or
    ($f=="INVESTIGATING" and ($t=="RCA_IDENTIFIED" or $t=="MITIGATING" or $t=="RESOLVED")) or
    ($f=="RCA_IDENTIFIED" and ($t=="MITIGATING" or $t=="RESOLVED")) or
    ($f=="MITIGATING" and ($t=="RECOVERING" or $t=="INVESTIGATING")) or
    ($f=="RECOVERING" and ($t=="RESOLVED" or $t=="MITIGATING" or $t=="INVESTIGATING")) or
    ($f=="RESOLVED" and ($t=="CLOSED" or $t=="INCIDENT"));
  [.audit.transitions[] | allowed(.from;.to)] | all
' "$INPUT" >/dev/null || die "$RC_CONTRACT" "Forbidden lifecycle transition"

if $PRETTY; then
  jq . "$INPUT"
else
  jq -c . "$INPUT"
fi

exit "$RC_OK"
