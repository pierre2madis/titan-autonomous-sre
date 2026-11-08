#!/usr/bin/env bash
set -euo pipefail

REGISTRY=""
GRAPH=""

while (($#)); do
  case "$1" in
    --registry)
      (($# >= 2)) || exit 2
      REGISTRY="$2"; shift 2 ;;
    --graph)
      (($# >= 2)) || exit 2
      GRAPH="$2"; shift 2 ;;
    *)
      echo "Unsupported argument" >&2
      exit 2 ;;
  esac
done

for F in "$REGISTRY" "$GRAPH"; do
  [[ -n "$F" && -f "$F" && -r "$F" ]] || exit 2
  jq -es 'length==1 and (.[0]|type=="object")' \
    "$F" >/dev/null || exit 2
done

jq -n \
  --slurpfile r "$REGISTRY" \
  --slurpfile g "$GRAPH" '
  ($r[0]) as $r |
  ($g[0]) as $g |

  (
    $r.schema_version=="1.0"
    and ($r.incidents|type)=="object"
    and ($r.incidents.active|type)=="array"
    and ($r.incidents.resolved|type)=="array"
    and ($r.incidents.closed|type)=="array"
  ) as $registry_valid |

  (
    $g.schema_version=="1.0"
    and ($g.graph|type)=="object"
    and ($g.graph.version|type)=="number"
    and ($g.nodes|type)=="object"
    and ($g.edges|type)=="array"
  ) as $graph_valid |

  (
    if $registry_valid then
      [
        $r.incidents.active[],
        $r.incidents.resolved[],
        $r.incidents.closed[]
      ]
    else
      []
    end
  ) as $incidents |

  (
    if $registry_valid then
      [$incidents[] |
        select(
          type=="object"
          and .parent_incident_id!=null
        )
      ] | length
    else
      null
    end
  ) as $parent_count |

  (
    if $registry_valid and $graph_valid then
      if ($g.nodes|length)==0
         and ($g.edges|length)==0 then
        if $parent_count==0 then
          ["CONSISTENT","EMPTY_GRAPH_EMPTY_HIERARCHY"]
        else
          ["INCONSISTENT","PARENT_RELATION_WITH_EMPTY_GRAPH"]
        end
      else
        ["DEFER","NONEMPTY_GRAPH_SCHEMA_NOT_ESTABLISHED"]
      end
    else
      ["DEFER","GRAPH_OR_REGISTRY_CONTRACT_UNVERIFIED"]
    end
  ) as $result |

  {
    engine:{
      name:"canonical_graph_consistency_gate",
      version:"0.1.0-candidate"
    },
    decision:{
      status:$result[0],
      reason:$result[1],
      advisory_only:true,
      operationally_authorized:false
    },
    evidence:{
      incident_count:($incidents|length),
      parent_relation_count:$parent_count,
      graph_node_count:
        (if $graph_valid then ($g.nodes|length) else null end),
      graph_edge_count:
        (if $graph_valid then ($g.edges|length) else null end)
    },
    controls:{
      incident_write_allowed:false,
      lifecycle_transition_allowed:false,
      remediation_allowed:false
    }
  }
'
