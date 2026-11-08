#!/usr/bin/env bash
set -euo pipefail
umask 077

VERSION="0.1.1-candidate"

PROPOSAL=""
REGISTRY=""
AUTH=""

usage() {
  echo "Usage: $0 --proposal FILE --registry FILE --authorization FILE"
}

while (($#)); do
  case "$1" in
    --proposal)
      (($# >= 2)) || exit 2
      PROPOSAL="$2"; shift 2 ;;
    --registry)
      (($# >= 2)) || exit 2
      REGISTRY="$2"; shift 2 ;;
    --authorization)
      (($# >= 2)) || exit 2
      AUTH="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      usage >&2; exit 2 ;;
  esac
done

for f in "$PROPOSAL" "$REGISTRY" "$AUTH"; do
  [[ -n "$f" && -f "$f" && -r "$f" ]] || {
    echo "INPUT_UNREADABLE" >&2
    exit 3
  }
done

WORK="$(mktemp -d /tmp/titan-admission-v011.XXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT

cp -- "$PROPOSAL" "$WORK/proposal.json"
cp -- "$REGISTRY" "$WORK/registry.json"
cp -- "$AUTH" "$WORK/authorization.json"

P="$WORK/proposal.json"
R="$WORK/registry.json"
A="$WORK/authorization.json"

for f in "$P" "$R" "$A"; do
  jq -e 'type=="object"' "$f" >/dev/null || {
    echo "INVALID_JSON_OBJECT" >&2
    exit 3
  }
done

PSHA="$(sha256sum "$P" | awk '{print $1}')"
RSHA="$(sha256sum "$R" | awk '{print $1}')"
ASHA="$(sha256sum "$A" | awk '{print $1}')"

jq -n \
  --slurpfile p "$P" \
  --slurpfile r "$R" \
  --slurpfile a "$A" \
  --arg psha "$PSHA" \
  --arg rsha "$RSHA" \
  --arg asha "$ASHA" \
  --arg version "$VERSION" '

  ($p[0]) as $p |
  ($r[0]) as $r |
  ($a[0]) as $a |

  ($p.proposal.parent_incident_id // null) as $parent |
  ($p.proposal.child_incident_id // null) as $child |
  ($p.proposal.root_incident_id // null) as $root |

  def incident_id:
    type == "string" and test("^INC-[A-F0-9]{24}$");

  def sha256:
    type == "string" and test("^[a-f0-9]{64}$");

  (
    $p.proposal.action == "ATTACH_CHILD"
    and $p.proposal.status == "PROPOSED"
    and $p.proposal.advisory_only == true
    and $p.controls.incident_write_allowed == false
    and $p.controls.remediation_allowed == false
    and $p.controls.notification_allowed == false
    and $p.preconditions.requires_fresh_registry_validation == true
    and $p.preconditions.requires_authorization == true
    and ($parent | incident_id)
    and ($child | incident_id)
    and ($root | incident_id)
    and $parent != $child
    and $root != $child
    and ($p.provenance.proposal_fingerprint | sha256)
    and ($p.provenance.source_decision_sha256 | sha256)
    and ($p.provenance.engine_sha256.correlation | sha256)
    and ($p.provenance.engine_sha256.dedup | sha256)
    and ($p.provenance.engine_sha256.graph | sha256)
  ) as $valid |

  (
    $r.schema_version == "0.1"
    and ($r.snapshot_id | type == "string" and test("^IRS-[A-F0-9]{24}$"))
    and $r.snapshot_id == $p.preconditions.registry_snapshot_id
    and $r.fresh == true
    and $r.parent_incident_id == $parent
    and $r.parent_exists == true
    and $r.child_incident_id == $child
    and ($r.child_exists | type == "boolean")
    and ($r.relationship_exists | type == "boolean")
    and (if $r.relationship_exists then $r.child_exists else true end)
  ) as $registry_valid |

  (
    $a.schema_version == "0.1"
    and $a.action == "ATTACH_CHILD"
    and $a.parent_incident_id == $parent
    and $a.child_incident_id == $child
    and $a.proposal_fingerprint == $p.provenance.proposal_fingerprint
    and ($a.authorized | type == "boolean")
  ) as $authorization_contract_valid |

  (
    if ($valid | not) then
      {status:"REJECT", reason:"INVALID_PROPOSAL"}
    elif ($registry_valid | not) then
      {status:"DEFER", reason:"REGISTRY_REVALIDATION_REQUIRED"}
    elif $r.relationship_exists then
      {status:"NOOP", reason:"RELATIONSHIP_ALREADY_PRESENT"}
    elif ($authorization_contract_valid | not) then
      {status:"DEFER", reason:"AUTHORIZATION_CONTRACT_INVALID"}
    elif $a.authorized != true then
      {status:"DEFER", reason:"AUTHORIZATION_REQUIRED"}
    else
      {
        status:"ADMIT",
        reason:"DECLARATIVE_ADMISSION_ONLY",
        authorization_verified:false
      }
    end
  ) as $decision |

  {
    schema_version:"0.1",
    engine:{
      name:"incident_admission_gate",
      version:$version
    },
    decision:($decision + {
      advisory_only:true,
      persisted:false,
      operationally_authorized:false
    }),
    relationship:{
      action:"ATTACH_CHILD",
      parent_incident_id:$parent,
      child_incident_id:$child,
      root_incident_id:$root
    },
    provenance:{
      proposal_sha256:$psha,
      registry_sha256:$rsha,
      authorization_sha256:$asha,
      proposal_fingerprint:$p.provenance.proposal_fingerprint,
      registry_snapshot_id:$r.snapshot_id
    },
    controls:{
      incident_write_allowed:false,
      lifecycle_transition_allowed:false,
      remediation_allowed:false,
      notification_allowed:false
    }
  }
'
