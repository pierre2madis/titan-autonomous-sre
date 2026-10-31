#!/usr/bin/env python3
"""Guard multi-signal graph writes with authoritative CPU state."""

import argparse
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRAPH_ENGINE = ROOT / "multisignal_graph_v0_1.py"

EXPECTED_FINGERPRINT = "linux:cpu:CPU_PSI_PRESSURE"


def validate_parent(cpu_state, scenario):
    if cpu_state.get("contract_version") != "0.4":
        raise ValueError("INVALID_CPU_STATE_VERSION")

    if cpu_state.get("synthetic") is not True:
        raise ValueError("NON_SYNTHETIC_CPU_STATE")

    if cpu_state.get("fingerprint") != EXPECTED_FINGERPRINT:
        raise ValueError("CPU_FINGERPRINT_MISMATCH")

    incident = cpu_state.get("incident")

    if not isinstance(incident, dict):
        raise ValueError("MISSING_CPU_INCIDENT")

    if incident.get("active") is not True:
        raise ValueError("PARENT_NOT_ACTIVE")

    if incident.get("state") != "OPEN":
        raise ValueError("PARENT_NOT_OPEN")

    parent = scenario["parent"]

    if incident.get("incident_id") != parent.get("incident_id"):
        raise ValueError("PARENT_INCIDENT_ID_MISMATCH")

    if parent.get("incident_state") != "OPEN":
        raise ValueError("FIXTURE_PARENT_NOT_OPEN")

    return incident["incident_id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--cpu-state", required=True)
    parser.add_argument("--graph-state", required=True)
    args = parser.parse_args()

    cpu_path = Path(args.cpu_state)

    if not cpu_path.is_file():
        raise ValueError("CPU_STATE_MISSING")

    lock_path = Path(str(cpu_path) + ".lock")

    fd = os.open(
        str(lock_path),
        os.O_CREAT | os.O_RDWR,
        0o600
    )

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)

        cpu_state = json.loads(cpu_path.read_text())
        scenario = json.loads(Path(args.scenario).read_text())

        incident_id = validate_parent(cpu_state, scenario)

        command = [
            sys.executable,
            str(GRAPH_ENGINE),
            "--scenario", args.scenario,
            "--contract", args.contract,
            "--state", args.graph_state
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )

        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        if result.returncode != 0:
            raise ValueError("GRAPH_ENGINE_FAILED")

        print(f"parent_incident_id={incident_id}")
        print("RESULT=LINUX_RELEASE_06E_PARENT_GUARD_PASS")

    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        json.JSONDecodeError
    ) as error:
        print(f"ERROR={error}", file=sys.stderr)
        sys.exit(1)
