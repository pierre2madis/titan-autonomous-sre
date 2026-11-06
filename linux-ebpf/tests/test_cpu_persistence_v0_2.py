#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/cpu_persistent_correlator_v0_2.py"

SOURCE = pathlib.Path(
    "/tmp/titan-cpu-demo.LCDCSNSg"
)

def execute(phase, state):
    return subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "--decision",
            str(SOURCE / f"{phase}_decision.json"),
            "--state",
            str(state)
        ],
        capture_output=True,
        text=True
    )

def read_state(path):
    return json.loads(path.read_text())

for phase in ("baseline", "injection", "recovery"):
    if not (SOURCE / f"{phase}_decision.json").is_file():
        raise SystemExit(f"ERROR=MISSING_SOURCE:{phase}")

with tempfile.TemporaryDirectory(prefix="titan-05e-") as tmp:
    state = pathlib.Path(tmp) / "incident_state.json"

    # First occurrence
    assert execute("injection", state).returncode == 0
    first = read_state(state)
    first_id = first["incident"]["incident_id"]

    assert first["incident"]["active"] is True
    assert first["incident"]["occurrence"] == 1

    # Deduplication
    assert execute("injection", state).returncode == 0
    duplicate = read_state(state)

    assert duplicate["incident"]["incident_id"] == first_id
    assert duplicate["incident"]["occurrence"] == 1
    assert duplicate["incident"]["observation_count"] == 2

    print("RESULT=INCIDENT_ID_STABILITY_PASS")

    # Resolution
    assert execute("recovery", state).returncode == 0
    resolved = read_state(state)

    assert resolved["incident"]["active"] is False
    assert resolved["incident"]["state"] == "RESOLVED"
    assert resolved["incident"]["incident_id"] == first_id

    # New occurrence
    assert execute("injection", state).returncode == 0
    second = read_state(state)
    second_id = second["incident"]["incident_id"]

    assert second["incident"]["occurrence"] == 2
    assert second_id != first_id

    print("RESULT=NEW_OCCURRENCE_PASS")

    # Corrupted state must be rejected
    state.write_text("{invalid-json")
    original = state.read_bytes()

    result = execute("injection", state)

    assert result.returncode != 0
    assert state.read_bytes() == original

    print("RESULT=CORRUPTED_STATE_REJECTED_PASS")

    # Wrong fingerprint must be rejected
    state.write_text(json.dumps({
        "fingerprint": "linux:disk:IO_PRESSURE",
        "incident": {
            "active": False,
            "occurrence": 0
        }
    }))

    original = state.read_bytes()
    result = execute("injection", state)

    assert result.returncode != 0
    assert state.read_bytes() == original

    print("RESULT=FINGERPRINT_MISMATCH_REJECTED_PASS")

print("RESULT=LINUX_RELEASE_05E_INTEGRITY_PASS")
