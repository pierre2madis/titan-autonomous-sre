#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--decision", required=True)
p.add_argument("--state", required=True)
p.add_argument("--event-id", required=True)
args = p.parse_args()

if not args.event_id.strip():
    raise SystemExit("ERROR=EMPTY_EVENT_ID")

data = json.loads(Path(args.decision).read_text())
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
state_path = Path(args.state)

payload = {
    "phase": data.get("phase"),
    "operational_conclusion": conclusion,
    "simulation_contract": contract
}
digest = hashlib.sha256(
    json.dumps(payload, sort_keys=True).encode()
).hexdigest()

if state_path.exists():
    state = json.loads(state_path.read_text())
    if (
        state.get("contract_version") != "0.3"
        or state.get("fingerprint") != fingerprint
    ):
        raise SystemExit("ERROR=STATE_CONTRACT_MISMATCH")
else:
    state = {
        "contract_version": "0.3",
        "synthetic": True,
        "fingerprint": fingerprint,
        "incident": {
            "incident_id": None,
            "occurrence": 0,
            "state": "NO_INCIDENT",
            "active": False,
            "observation_count": 0
        },
        "processed_events": {}
    }

processed = state["processed_events"]

if args.event_id in processed:
    if processed[args.event_id] != digest:
        raise SystemExit("ERROR=EVENT_ID_CONFLICT")
    print("action=IGNORE_REPLAY")
    print("RESULT=LINUX_RELEASE_05F_REPLAY_IGNORED")
    raise SystemExit(0)

incident = state["incident"]
active = incident["active"]

if recommended and not active:
    incident["occurrence"] += 1
    identity = f"{fingerprint}:{incident['occurrence']}"
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

processed[args.event_id] = digest

# Bounded replay history: oldest entries removed first.
while len(processed) > 1000:
    del processed[next(iter(processed))]

state_path.parent.mkdir(parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(
    prefix=".cpu-idempotent-",
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

print(f"event_id={args.event_id}")
print(f"action={action}")
print(f"state={incident['state']}")
print(f"occurrence={incident['occurrence']}")
print(f"observation_count={incident['observation_count']}")
print(f"incident_id={incident['incident_id']}")
print("RESULT=LINUX_RELEASE_05F_CORRELATOR_PASS")
