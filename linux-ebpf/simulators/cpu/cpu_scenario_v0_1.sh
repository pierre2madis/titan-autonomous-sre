#!/usr/bin/env bash
set -euo pipefail

# TITAN CPU Scenario Simulator v0.1
# Synthetic evidence only; no actual CPU pressure.

OUTPUT="${1:-}"

if [[ -z "$OUTPUT" || -e "$OUTPUT" ]]; then
    echo "ERROR=OUTPUT_PATH_REQUIRED_AND_MUST_NOT_EXIST" >&2
    exit 2
fi

mkdir -p "$OUTPUT"

python3 - "$OUTPUT" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

output = pathlib.Path(sys.argv[1])
start = datetime.now(timezone.utc)

phases = [
    ("BASELINE", 12.0, 0.4, 1.5, 0, "NORMAL"),
    ("INJECTION", 38.0, 4.2, 65.0, 1, "DEGRADED"),
    ("RECOVERY", 14.0, 0.5, 2.0, 0, "NORMAL"),
]

for index, (phase, busy, runq, latency, contention, state) in enumerate(phases):
    event = {
        "schema_version": "0.1",
        "scenario_id": "CPU-02",
        "source": "TITAN_SYNTHETIC_REPLAY",
        "synthetic": True,
        "host": "titan-demo-cpu",
        "observed_at": (
            start + timedelta(seconds=index * 30)
        ).isoformat().replace("+00:00", "Z"),
        "phase": phase,
        "metrics": {
            "cpu_busy_percent": busy,
            "runq_per_cpu_p95": runq,
            "runqlat_p99_ms": latency,
            "scheduler_contention": contention
        },
        "expected_evidence_state": state,
        "root_cause": "UNVERIFIED",
        "service_impact": "NOT_MEASURED"
    }

    path = output / f"{index + 1:02d}_{phase.lower()}.json"
    path.write_text(json.dumps(event, indent=2) + "\n")

manifest = {
    "scenario_id": "CPU-02",
    "synthetic": True,
    "phases": [p[0] for p in phases],
    "expected_transitions": [
        "NORMAL",
        "DEGRADED",
        "NORMAL"
    ]
}

(output / "manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)

print("scenario=CPU-02")
print("mode=SYNTHETIC_REPLAY")
print("phases=3")
print("RESULT=CPU_SCENARIO_GENERATED")
PY
