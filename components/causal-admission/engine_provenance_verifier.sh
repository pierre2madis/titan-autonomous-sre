#!/usr/bin/env bash
set -euo pipefail
umask 077

usage() {
  echo "Usage: $0 --proposal FILE --baseline FILE"
}

PROPOSAL=""
BASELINE=""

while (($#)); do
  case "$1" in
    --proposal)
      (($# >= 2)) || { usage >&2; exit 2; }
      PROPOSAL="$2"; shift 2 ;;
    --baseline)
      (($# >= 2)) || { usage >&2; exit 2; }
      BASELINE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      usage >&2; exit 2 ;;
  esac
done

for f in "$PROPOSAL" "$BASELINE"; do
  [[ -n "$f" && -f "$f" && -r "$f" ]] || {
    echo "INPUT_UNREADABLE" >&2
    exit 3
  }
done

WORK="$(mktemp -d /tmp/titan-provenance.XXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT

cp -- "$PROPOSAL" "$WORK/proposal.json"
cp -- "$BASELINE" "$WORK/baseline.json"

P="$WORK/proposal.json"
B="$WORK/baseline.json"

for f in "$P" "$B"; do
  jq -e 'type=="object"' "$f" >/dev/null || {
    echo "INVALID_JSON_OBJECT" >&2
    exit 3
  }
done

PSHA="$(sha256sum "$P" | awk '{print $1}')"
BSHA="$(sha256sum "$B" | awk '{print $1}')"

jq -n \
  --slurpfile p "$P" \
  --slurpfile b "$B" \
  --arg psha "$PSHA" \
  --arg bsha "$BSHA" '
  ($p[0]) as $p |
  ($b[0]) as $b |

  def valid_sha:
    type=="string" and test("^[a-f0-9]{64}$");

  ($p.provenance.engine_sha256 // {}) as $declared |
  ($b.engine_sha256 // {}) as $expected |

  (
    $b.schema_version == "0.1"
    and $b.baseline_id == "TITAN-ENGINE-BASELINE-V1"
    and ($expected.correlation | valid_sha)
    and ($expected.dedup | valid_sha)
    and ($expected.graph | valid_sha)
  ) as $baseline_valid |

  (
    ($declared.correlation | valid_sha)
    and ($declared.dedup | valid_sha)
    and ($declared.graph | valid_sha)
  ) as $declaration_valid |

  (
    $baseline_valid
    and $declaration_valid
    and $declared.correlation == $expected.correlation
    and $declared.dedup == $expected.dedup
    and $declared.graph == $expected.graph
  ) as $match |

  {
    schema_version:"0.1",
    engine:{
      name:"titan_engine_provenance_verifier",
      version:"0.1.0-candidate"
    },
    verification:{
      status:(
        if ($baseline_valid | not) then "REJECT"
        elif ($declaration_valid | not) then "REJECT"
        elif $match then "MATCH"
        else "MISMATCH"
        end
      ),
      baseline_contract_valid:$baseline_valid,
      declaration_valid:$declaration_valid,
      engine_hashes_match:$match,
      baseline_authenticity_verified:false,
      installed_artifacts_verified:false
    },
    provenance:{
      proposal_sha256:$psha,
      baseline_sha256:$bsha,
      baseline_id:$b.baseline_id
    },
    controls:{
      advisory_only:true,
      incident_write_allowed:false,
      remediation_allowed:false,
      notification_allowed:false
    }
  }
'
