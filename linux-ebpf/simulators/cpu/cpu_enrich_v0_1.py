#!/usr/bin/env python3
import json
import pathlib
import sys

if len(sys.argv) != 3:
    sys.exit("Usage: cpu_enrich_v0_1.py INPUT OUTPUT")

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])

if target.exists():
    sys.exit("ERROR=OUTPUT_ALREADY_EXISTS")

event = json.loads(source.read_text())

if event.get("scenario_id") != "CPU-02" or event.get("synthetic") is not True:
    sys.exit("ERROR=INVALID_SYNTHETIC_SCENARIO")

profiles = {
    "BASELINE": {
        "system_pct": 4.0,
        "psi_some_avg10": 0.5,
        "run_queue": [0, 0, 0.8, 2],
        "runqlat": [0.1, 0.5, 0.8, 1.5]
    },
    "INJECTION": {
        "system_pct": 12.0,
        "psi_some_avg10": 35.0,
        "run_queue": [2, 5, 8.4, 12],
        "runqlat": [2.0, 15.0, 35.0, 65.0]
    },
    "RECOVERY": {
        "system_pct": 4.5,
        "psi_some_avg10": 1.0,
        "run_queue": [0, 0.5, 1, 2],
        "runqlat": [0.2, 0.6, 1.0, 2.0]
    }
}

phase = event.get("phase")

if phase not in profiles:
    sys.exit("ERROR=UNSUPPORTED_PHASE")

profile = profiles[phase]

event["synthetic_observations"] = {
    "cpu_cores": 2,
    "system_pct": profile["system_pct"],
    "psi_some_avg10": profile["psi_some_avg10"],
    "psi_capable": True,
    "run_queue_percentiles": {
        key: value
        for key, value in zip(
            ["p50", "p90", "p95", "p99"],
            profile["run_queue"]
        )
    },
    "runqlat_percentiles_ms": {
        key: value
        for key, value in zip(
            ["p50", "p90", "p95", "p99"],
            profile["runqlat"]
        )
    },
    "runqlat_collector": {
        "available": True,
        "ready": True,
        "status": "SUCCESS",
        "lifecycle_state": "COMPLETE"
    }
}

event["synthetic_profile_version"] = "0.1"
event["synthetic_profile_provenance"] = "SCENARIO_AUTHORED"

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(event, indent=2) + "\n")

print(f"phase={phase}")
print("synthetic_profile=COMPLETE")
print("RESULT=CPU_ENRICH_PASS")
