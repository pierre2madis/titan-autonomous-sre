#!/usr/bin/env bash
set -euo pipefail

PROPOSAL=""
REGISTRY=""
GENERATION=""

while (($#)); do
  case "$1" in
    --proposal)
      (($# >= 2)) || exit 2
      PROPOSAL="$2"
      shift 2 ;;
    --registry)
      (($# >= 2)) || exit 2
      REGISTRY="$2"
      shift 2 ;;
    --generation)
      (($# >= 2)) || exit 2
      GENERATION="$2"
      shift 2 ;;
    *)
      echo "Unsupported argument" >&2
      exit 2 ;;
  esac
done

for F in "$PROPOSAL" "$REGISTRY"; do
  [[ -n "$F" && -f "$F" && -r "$F" ]] || exit 2
  jq -es 'length==1 and (.[0]|type=="object")' \
    "$F" >/dev/null || exit 2
done

[[ "$GENERATION" =~ ^GEN-[0-9]{16}$ ]] || exit 2

jq -n \
  --slurpfile p "$PROPOSAL" \
  --slurpfile r "$REGISTRY" \
  --arg expected "$GENERATION" '

  def valid_id:
    type=="string"
    and test("^INC-[A-F0-9]{24}$");

  def valid_entry:
    type=="object"
    and (.incident_id | valid_id)
    and (.root_incident_id | valid_id)
    and (
      .parent_incident_id==null
      or (.parent_incident_id | valid_id)
    );

  def graph_valid($items):
    ($items | map(.incident_id)) as $ids
    | ($ids | unique | length)==($ids | length)
      and
      (
        all($items[]; valid_entry)
      )
      and
      (
        all($items[];
          . as $item
          | if .parent_incident_id==null then
              .root_incident_id==.incident_id
            else
              (.parent_incident_id != .incident_id)
              and ($ids | index($item.parent_incident_id))!=null
            end
        )
      )
      and
      (
        all($items[];
          . as $start
          | {
              current:$start.incident_id,
              seen:[],
              valid:true
            }
          | until(
              .current==null or .valid==false;
              . as $state
              | if ($state.seen | index($state.current))!=null then
                  .valid=false
                else
                  ($items |
                    map(select(.incident_id==$state.current))
                    | .[0]) as $node
                  | if $node==null then
                      .valid=false
                    elif $node.parent_incident_id==null then
                      .valid=($node.incident_id==$start.root_incident_id)
                      | .current=null
                    else
                      .seen += [$state.current]
                      | .current=$node.parent_incident_id
                    end
                end
            )
          | .valid
        )
      );

  ($p[0]) as $p |
  ($r[0]) as $r |

  ($p.proposal.parent_incident_id // null) as $parent |
  ($p.proposal.child_incident_id // null) as $child |

  (
    if (
      $r.schema_version!="1.0"
      or ($r.incidents|type)!="object"
      or ($r.incidents.active|type)!="array"
      or ($r.incidents.resolved|type)!="array"
      or ($r.incidents.closed|type)!="array"
    ) then
      null
    else
      [
        $r.incidents.active[],
        $r.incidents.resolved[],
        $r.incidents.closed[]
      ]
    end
  ) as $items |

  (
    if ($r.generation_id // null)!=$expected then
      ["DEFER","GENERATION_MISMATCH"]

    elif $items==null then
      ["DEFER","REGISTRY_CONTRACT_UNVERIFIED"]

    elif (graph_valid($items) | not) then
      ["REJECT","REGISTRY_GRAPH_INVARIANT_VIOLATION"]

    elif (
      $p.proposal.action!="ATTACH_CHILD"
      or ($parent|valid_id|not)
      or ($child|valid_id|not)
    ) then
      ["REJECT","INVALID_PROPOSAL"]

    elif $parent==$child then
      ["REJECT","SELF_PARENT"]

    else
      ([$items[] | select(.incident_id==$parent)] | .[0]) as $pe |
      ([$items[] | select(.incident_id==$child)] | .[0]) as $ce |

      if $pe==null or $ce==null then
        ["DEFER","INCIDENT_NOT_RESOLVED"]

      elif $ce.parent_incident_id==$parent then
        ["NOOP","RELATION_ALREADY_PRESENT"]

      elif $ce.parent_incident_id!=null then
        ["REJECT","CHILD_ALREADY_HAS_PARENT"]

      elif $pe.parent_incident_id!=null then
        ["DEFER","PARENT_NOT_ROOT"]

      elif $pe.root_incident_id!=$parent
        or $ce.root_incident_id!=$child then
        ["REJECT","ROOT_INCONSISTENCY"]

      else
        ["ADMIT","ROOT_TO_ROOT_ATTACHMENT_ELIGIBLE"]
      end
    end
  ) as $result |

  {
    engine:{
      name:"canonical_causal_attachment_validator",
      version:"0.1.1-candidate"
    },
    source:{
      expected_generation:$expected,
      declared_generation:($r.generation_id // null),
      registry_authenticity_verified:false,
      canonical_files_verified:false,
      causal_graph_verified:false
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
