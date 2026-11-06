#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--decision", required=True)
parser.add_argument("--state", required=True)
args = parser.parse_args()

decision_path = Path(args.decision)
state_path = Path(args.state)

data = json.loads(decision_path.read_text())
contract = data.get("simulation_contract", {})

if not (
    data.get("synthetic") is True
    and contract.get("complete") is True
    and contract.get("decision_ready") is True
    and contract.get("real_host_telemetry") is False
    and contract.get("expected_state_not_forwarded") is True
):
    raise SystemExit("ERROR=INVALID_SYNTHETIC_CONTRACT")

conclusion = data["operational_conclusion"]
recommended = conclusion["incident_recommended"]

if type(recommended) is not bool:
    raise SystemExit("ERROR=INVALID_INCIDENT_FLAG")

fingerprint = "linux:cpu:CPU_PSI_PRESSURE"

if state_path.exists():
    state = json.loads(state_path.read_text())
    if state.get("fingerprint") != fingerprint:
        raise SystemExit("ERROR=FINGERPRINT_MISMATCH")
else:
    state = {
        "contract_version": "0.2",
        "scenario_id": "CPU-02",
        "synthetic": True,
        "fingerprint": fingerprint,
        "incident": {
            "incident_id": None,
            "occurrence": 0,
            "state": "NO_INCIDENT",
            "active": False,
            "created_at": None,
            "last_observed_at": None,
            "resolved_at": None,
            "observation_count": 0
        },
        "policy": {
            "deduplication": "SAME_FINGERPRINT_WHILE_ACTIVE",
            "new_occurrence_after_resolution": True,
            "recovery_consecutive_normal": 1,
            "persistence": "LOCAL_JSON"
        }
    }

incident = state["incident"]
active = incident["active"]

if recommended and not active:
    incident["occurrence"] += 1
    identity = (
        f"{fingerprint}:{incident['occurrence']}"
    )
    incident["incident_id"] = "TITAN-" + hashlib.sha256(
        identity.encode()
    ).hexdigest()[:12].upper()
    incident["state"] = "OPEN"
    incident["active"] = True
    incident["observation_count"] = 1
    action = "CREATE"

elif recommended and active:
    incident["observation_count"] += 1
    action = "DEDUPLICATE"

elif not recommended and active:
    incident["state"] = "RESOLVED"
    incident["active"] = False
    action = "RESOLVE"

else:
    action = "NONE"

state_path.parent.mkdir(parents=True, exist_ok=True)

fd, temporary = tempfile.mkstemp(
    prefix=".cpu-incident-",
    suffix=".json",
    dir=str(state_path.parent)
)

try:
    with os.fdopen(fd, "w") as stream:
        json.dump(state, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, state_path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)

print(f"phase={data.get('phase')}")
print(f"action={action}")
print(f"state={incident['state']}")
print(f"occurrence={incident['occurrence']}")
print(f"incident_id={incident['incident_id']}")
print("RESULT=LINUX_RELEASE_05D_CORRELATOR_PASS")
