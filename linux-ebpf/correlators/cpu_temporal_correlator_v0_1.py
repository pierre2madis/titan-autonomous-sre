#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

root = Path(args.directory)
output = Path(args.output)

if output.exists():
    raise SystemExit("ERROR=OUTPUT_ALREADY_EXISTS")

scenario = "CPU-02"
identity = f"synthetic:{scenario}:CPU_PSI_PRESSURE"
incident_id = "TITAN-" + hashlib.sha256(
    identity.encode()
).hexdigest()[:12].upper()

events = []
active = False
created = 0
resolved = 0

for phase in ("baseline", "injection", "recovery"):
    path = root / f"{phase}_decision.json"
    data = json.loads(path.read_text())

    contract = data.get("simulation_contract", {})

    if (
        data.get("synthetic") is not True
        or contract.get("complete") is not True
        or contract.get("real_host_telemetry") is not False
        or contract.get("expected_state_not_forwarded") is not True
    ):
        raise SystemExit(f"ERROR=INVALID_CONTRACT:{phase}")

    if data.get("phase") != phase.upper():
        raise SystemExit(f"ERROR=PHASE_MISMATCH:{phase}")

    conclusion = data["operational_conclusion"]
    recommended = conclusion["incident_recommended"]

    if type(recommended) is not bool:
        raise SystemExit(f"ERROR=INVALID_INCIDENT_FLAG:{phase}")

    if recommended and not active:
        active = True
        created += 1
        action = "CREATE"
        state = "OPEN"
    elif recommended and active:
        action = "DEDUPLICATE"
        state = "OPEN"
    elif not recommended and active:
        active = False
        resolved += 1
        action = "RESOLVE"
        state = "RESOLVED"
    else:
        action = "NONE"
        state = "NO_INCIDENT"

    events.append({
        "phase": phase.upper(),
        "incident_id": incident_id if action != "NONE" else None,
        "decision_severity": conclusion["severity"],
        "problem_type": conclusion["problem_type"],
        "incident_recommended": recommended,
        "action": action,
        "state": state
    })

result = {
    "contract_version": "0.1",
    "scenario_id": scenario,
    "synthetic": True,
    "persistent_state": False,
    "incident_id": incident_id,
    "created_count": created,
    "resolved_count": resolved,
    "active_at_end": active,
    "events": events
}

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + "\n")

print(f"incident_id={incident_id}")
for event in events:
    print(
        f"{event['phase']}: "
        f"action={event['action']} "
        f"state={event['state']}"
    )
print("RESULT=LINUX_RELEASE_05A_CORRELATION_COMPLETE")
