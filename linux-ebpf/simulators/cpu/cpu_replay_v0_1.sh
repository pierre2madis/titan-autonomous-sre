#!/usr/bin/env bash
set -euo pipefail

# TITAN CPU Evidence Replay v0.1
# Synthetic data only.
# Does not generate CPU load or modify operational metrics.

OUTPUT="${1:-}"

if [[ -z "$OUTPUT" ]]; then
  echo "Usage: $0 OUTPUT_DIRECTORY" >&2
  exit 2
fi

if [[ -e "$OUTPUT" ]]; then
  echo "ERROR=OUTPUT_ALREADY_EXISTS" >&2
  exit 3
fi

mkdir -p "$OUTPUT"

cat > "$OUTPUT/cpu_evidence.json" <<JSON
{
  "schema_version": "0.1",
  "scenario_id": "CPU-01",
  "source": "TITAN_SYNTHETIC_REPLAY",
  "synthetic": true,
  "observed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "host": "titan-demo-cpu",
  "metrics": {
    "cpu_busy_percent": 15.87,
    "runq_per_cpu_p95": 3.50,
    "runqlat_p99_ms": 8.191,
    "scheduler_contention": 0,
    "rca_confidence": 0.20,
    "direct_evidence_quality": 0,
    "incident_recommended": 1
  },
  "assessment": {
    "problem_type": "CPU_PSI_PRESSURE",
    "root_cause": "UNDETERMINED",
    "service_impact": "NOT_MEASURED",
    "error_budget_consumed": null
  }
}
JSON

cat > "$OUTPUT/cpu_replay.prom" <<'PROM'
# HELP titan_demo_cpu_busy_percent Synthetic CPU utilization.
# TYPE titan_demo_cpu_busy_percent gauge
titan_demo_cpu_busy_percent{scenario="CPU-01",synthetic="true"} 15.87

# HELP titan_demo_cpu_runq_per_cpu_p95 Synthetic run queue p95.
# TYPE titan_demo_cpu_runq_per_cpu_p95 gauge
titan_demo_cpu_runq_per_cpu_p95{scenario="CPU-01",synthetic="true"} 3.50

# HELP titan_demo_cpu_runqlat_p99_ms Synthetic scheduler latency p99.
# TYPE titan_demo_cpu_runqlat_p99_ms gauge
titan_demo_cpu_runqlat_p99_ms{scenario="CPU-01",synthetic="true"} 8.191

# HELP titan_demo_cpu_scheduler_contention Synthetic corroborated contention.
# TYPE titan_demo_cpu_scheduler_contention gauge
titan_demo_cpu_scheduler_contention{scenario="CPU-01",synthetic="true"} 0

# HELP titan_demo_cpu_rca_confidence Synthetic RCA confidence.
# TYPE titan_demo_cpu_rca_confidence gauge
titan_demo_cpu_rca_confidence{scenario="CPU-01",synthetic="true"} 0.20

# HELP titan_demo_cpu_incident_recommended Synthetic incident recommendation.
# TYPE titan_demo_cpu_incident_recommended gauge
titan_demo_cpu_incident_recommended{scenario="CPU-01",synthetic="true"} 1
PROM

echo "scenario=CPU-01"
echo "mode=SYNTHETIC_REPLAY"
echo "output=$OUTPUT"
echo "RESULT=CPU_REPLAY_GENERATED"
