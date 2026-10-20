#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENGINE="$ROOT/src/correlation/cross_domain_correlation_engine_v1_0_0_final.sh"
RULES="$ROOT/config/causal_rules_v1_0_0.json"
FIXTURES="$ROOT/tests/correlation"

command -v jq >/dev/null
command -v sha256sum >/dev/null

for file in \
  "$ENGINE" \
  "$RULES" \
  "$FIXTURES/input_corr_cpu_linux.json" \
  "$FIXTURES/input_corr_splunk_target.json" \
  "$FIXTURES/input_corr_block_io_source.json" \
  "$FIXTURES/golden_direct_cause_of.json"; do

    [[ -f "$file" && ! -L "$file" ]] || {
        echo "ERROR: Required file unavailable"
        exit 1
    }
done

echo "============================================================"
echo " TITAN v0.1.0 — OFFLINE CAUSAL CORRELATION DEMO"
echo "============================================================"

run_engine() {
    bash "$ENGINE" \
        --source-event "$1" \
        --target-event "$2" \
        --rules "$RULES"
}

echo
echo "=== SCENARIO A — INVALID CAUSAL DIRECTION ==="

NEGATIVE="$(
    run_engine \
      "$FIXTURES/input_corr_cpu_linux.json" \
      "$FIXTURES/input_corr_splunk_target.json"
)"

printf '%s\n' "$NEGATIVE" | jq '{
  relationship,
  temporal,
  causal_rule,
  incident_recommendation
}'

printf '%s\n' "$NEGATIVE" | jq -e '
  .relationship.type == "CORRELATED_WITH" and
  .relationship.direction == "NONE" and
  .causal_rule.matched == true and
  .causal_rule.eligible == false and
  .temporal.direction_valid == false and
  .incident_recommendation.advisory_only == true
' >/dev/null

echo "negative_causal_gate=PASS"

echo
echo "=== SCENARIO B — POSITIVE CAUSAL RELATIONSHIP ==="

POSITIVE="$(
    run_engine \
      "$FIXTURES/input_corr_block_io_source.json" \
      "$FIXTURES/input_corr_splunk_target.json"
)"

printf '%s\n' "$POSITIVE" | jq '{
  relationship,
  causal_rule,
  temporal,
  scores,
  incident_recommendation
}'

printf '%s\n' "$POSITIVE" | jq -e \
  --slurpfile golden "$FIXTURES/golden_direct_cause_of.json" '
    . as $actual |
    $golden[0] as $expected |
    ($actual.relationship == $expected.relationship) and
    ($actual.causal_rule == $expected.causal_rule) and
    ($actual.scores == $expected.scores) and
    ($actual.temporal == $expected.temporal) and
    ($actual.topology == $expected.topology) and
    ($actual.incident_recommendation ==
     $expected.incident_recommendation)
  ' >/dev/null

echo "positive_causal_golden=PASS"

echo
echo "============================================================"
echo " TITAN OFFLINE DEMO — PASS"
echo "============================================================"
