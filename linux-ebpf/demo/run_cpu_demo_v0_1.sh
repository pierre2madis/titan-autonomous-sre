#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INTEGRATOR="/usr/local/bin/cpu_evidence_decision_integrator_v1_0_0.sh"
BRIDGE="/usr/local/bin/cpu_decision_bridge_v1_0_0_candidate.sh"
MODEL="/usr/local/bin/cpu_decision_model_v1_0_2_candidate.sh"

for component in "$INTEGRATOR" "$BRIDGE" "$MODEL"; do
    [[ -x "$component" ]] || {
        echo "ERROR=MISSING_COMPONENT:$component" >&2
        exit 1
    }
done

OUTPUT="$(mktemp -d /tmp/titan-cpu-demo.XXXXXXXX)"

echo "============================================================"
echo " TITAN CPU-02 — SYNTHETIC INCIDENT DEMONSTRATION"
echo "============================================================"
echo "output=$OUTPUT"

bash "$ROOT/simulators/cpu/cpu_scenario_v0_1.sh" \
    "$OUTPUT/scenario"

for item in "01:baseline" "02:injection" "03:recovery"; do
    number="${item%%:*}"
    phase="${item#*:}"

    python3 "$ROOT/simulators/cpu/cpu_enrich_v0_1.py" \
        "$OUTPUT/scenario/${number}_${phase}.json" \
        "$OUTPUT/${phase}_enriched.json"

    python3 "$ROOT/adapters/cpu_scenario_adapter_v0_2.py" \
        --input "$OUTPUT/${phase}_enriched.json" \
        --output "$OUTPUT/${phase}_native.json"

    "$INTEGRATOR" \
        --input "$OUTPUT/${phase}_native.json" \
        --output "$OUTPUT/${phase}_decision.json" \
        --bridge "$BRIDGE" \
        --model "$MODEL" \
        >/dev/null

    jq -r --arg phase "$phase" '
        .operational_conclusion |
        "\($phase | ascii_upcase): " +
        "status=\(.problem_status) " +
        "severity=\(.severity) " +
        "incident=\(.incident_recommended)"
    ' "$OUTPUT/${phase}_decision.json"
done

python3 "$ROOT/reports/cpu_demo_report_v0_1.py" \
    --directory "$OUTPUT" \
    --output "$OUTPUT/cpu_demo_report.json"

echo
echo "=== FINAL REPORT ==="
echo "$OUTPUT/cpu_demo_report.json"

echo
echo "RESULT=LINUX_RELEASE_04B_DEMO_COMPLETE"
