#!/usr/bin/env python3
import argparse
import json
import math
import pathlib
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

source = pathlib.Path(args.input)
target = pathlib.Path(args.output)

if target.exists() or source.resolve() == target.resolve():
    sys.exit("ERROR=OUTPUT_COLLISION")

event = json.loads(source.read_text())

if event.get("synthetic") is not True:
    sys.exit("ERROR=NON_SYNTHETIC_INPUT")

if event.get("scenario_id") != "CPU-02":
    sys.exit("ERROR=UNSUPPORTED_SCENARIO")

if event.get("synthetic_profile_provenance") != "SCENARIO_AUTHORED":
    sys.exit("ERROR=INVALID_PROVENANCE")

m = event["metrics"]
s = event["synthetic_observations"]

def numeric(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        sys.exit(f"ERROR=INVALID_NUMERIC:{name}")
    if not math.isfinite(value):
        sys.exit(f"ERROR=NON_FINITE:{name}")
    if value < minimum or (maximum is not None and value > maximum):
        sys.exit(f"ERROR=OUT_OF_RANGE:{name}")
    return value

cores = s["cpu_cores"]

if isinstance(cores, bool) or not isinstance(cores, int) or cores < 1:
    sys.exit("ERROR=INVALID_CPU_CORES")

busy = numeric(m["cpu_busy_percent"], "cpu_busy", 0, 100)
system = numeric(s["system_pct"], "system_pct", 0, 100)
psi = numeric(s["psi_some_avg10"], "psi", 0, 100)

if system > busy:
    sys.exit("ERROR=SYSTEM_CPU_EXCEEDS_BUSY")

if s["psi_capable"] is not True:
    sys.exit("ERROR=PSI_CAPABILITY_REQUIRED")

rq = s["run_queue_percentiles"]
rl = s["runqlat_percentiles_ms"]

keys = ["p50", "p90", "p95", "p99"]

for name, values in [("run_queue", rq), ("runqlat", rl)]:
    series = [numeric(values[k], f"{name}.{k}") for k in keys]
    if series != sorted(series):
        sys.exit(f"ERROR=NON_MONOTONIC:{name}")

expected_rq = numeric(m["runq_per_cpu_p95"], "runq_per_cpu_p95") * cores
expected_rl = numeric(m["runqlat_p99_ms"], "runqlat_p99_ms")

if not math.isclose(rq["p95"], expected_rq, abs_tol=0.0001):
    sys.exit("ERROR=RUN_QUEUE_P95_MISMATCH")

if not math.isclose(rl["p99"], expected_rl, abs_tol=0.0001):
    sys.exit("ERROR=RUNQLAT_P99_MISMATCH")

collector = s["runqlat_collector"]

if (
    collector["available"] is not True
    or collector["ready"] is not True
    or collector["status"] != "SUCCESS"
    or collector["lifecycle_state"] != "COMPLETE"
):
    sys.exit("ERROR=INVALID_COLLECTOR_STATE")

native = {
    "schema_version": "3.18.3",
    "engine": "cpu",
    "synthetic": True,
    "source": "TITAN_SYNTHETIC_REPLAY",
    "scenario_id": "CPU-02",
    "host": event["host"],
    "observed_at": event["observed_at"],
    "phase": event["phase"],
    "metrics": {
        "cpu_busy_pct": busy,
        "system_pct": system,
        "cpu_cores": cores,
        "psi_some_avg10": psi
    },
    "capabilities": {
        "psi": True
    },
    "run_queue": {
        **rq,
        "per_cpu_p95": m["runq_per_cpu_p95"]
    },
    "runqlat": {
        **collector,
        **{k + "_ms": rl[k] for k in keys}
    },
    "simulation_contract": {
        "complete": True,
        "decision_ready": True,
        "synthetic": True,
        "profile_provenance": "SCENARIO_AUTHORED",
        "expected_state_not_forwarded": True,
        "real_host_telemetry": False
    }
}

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(native, indent=2) + "\n")

print(f"phase={event['phase']}")
print("native_contract=COMPLETE")
print("decision_ready=true")
print("RESULT=CPU_ADAPTER_V02_PASS")
