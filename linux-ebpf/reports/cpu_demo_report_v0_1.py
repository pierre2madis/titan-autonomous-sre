#!/usr/bin/env python3
import argparse
import json
import pathlib
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

root = pathlib.Path(args.directory)
output = pathlib.Path(args.output)

if output.exists():
    raise SystemExit("ERROR=OUTPUT_ALREADY_EXISTS")

phases = []

for phase in ["baseline", "injection", "recovery"]:
    path = root / f"{phase}_decision.json"

    if not path.is_file():
        raise SystemExit(f"ERROR=MISSING_DECISION:{phase}")

    data = json.loads(path.read_text())

    if data.get("synthetic") is not True:
        raise SystemExit(f"ERROR=NON_SYNTHETIC_DECISION:{phase}")

    conclusion = data["operational_conclusion"]
    evidence = data["decision_evidence"]

    phases.append({
        "phase": phase.upper(),
        "problem_status": conclusion["problem_status"],
        "problem_type": conclusion["problem_type"],
        "severity": conclusion["severity"],
        "confidence": conclusion["confidence"],
        "incident_recommended": conclusion["incident_recommended"],
        "recommended_action": conclusion["recommended_action"],
        "evidence": {
            "cpu_busy_pct": evidence["utilization"]["value_pct"],
            "psi_some_avg10": evidence["psi_some_avg10"]["value_pct"],
            "runq_per_core_p95": evidence["run_queue_per_core"]["p95"],
            "runqlat_p99_ms": evidence["scheduler_latency_ms"]["p99"]
        }
    })

expected = [
    ("NORMAL", False),
    ("DEGRADED", True),
    ("NORMAL", False)
]

for item, (severity, incident) in zip(phases, expected):
    if item["severity"] != severity:
        raise SystemExit("ERROR=UNEXPECTED_SEVERITY")
    if item["incident_recommended"] is not incident:
        raise SystemExit("ERROR=UNEXPECTED_INCIDENT_DECISION")

report = {
    "report_version": "0.1",
    "project": "TITAN Autonomous SRE",
    "scenario_id": "CPU-02",
    "synthetic": True,
    "real_incident": False,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "validation": {
        "decision_pipeline": "PASS",
        "expected_transition": [
            "NORMAL",
            "DEGRADED",
            "NORMAL"
        ],
        "actual_transition": [
            item["severity"] for item in phases
        ],
        "recovery_observed_in_decision": True
    },
    "phases": phases
}

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")

print("scenario=CPU-02")
print("decision_pipeline=PASS")
print("transition=NORMAL->DEGRADED->NORMAL")
print("RESULT=LINUX_RELEASE_04A_REPORT_PASS")
