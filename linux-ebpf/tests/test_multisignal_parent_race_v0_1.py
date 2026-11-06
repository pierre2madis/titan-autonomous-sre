#!/usr/bin/env python3
"""Deterministic CPU parent resolution versus child attachment test."""

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPU_ENGINE = ROOT / "correlators/cpu_locked_correlator_v0_5.py"
GUARD = ROOT / "correlators/multisignal_parent_guard_v0_1.py"
CONTRACT = ROOT / "contracts/multisignal_correlation_v0_1.json"
FIXTURE = ROOT / "simulators/multisignal/fixtures/06B-01_same_host.json"

DECISION_DIR = Path("/tmp/titan-cpu-demo.LCDCSNSg")
INJECTION = DECISION_DIR / "injection_decision.json"
RECOVERY = DECISION_DIR / "recovery_decision.json"


def run(command):
    return subprocess.run(
        command, capture_output=True, text=True, timeout=15
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for required in (INJECTION, RECOVERY):
    if not required.is_file():
        raise SystemExit(f"ERROR=MISSING_SYNTHETIC_DECISION:{required}")

with tempfile.TemporaryDirectory(prefix="titan-06e4-") as tmp:
    directory = Path(tmp)
    cpu_state = directory / "cpu_state.json"
    graph_state = directory / "graph_state.json"
    scenario_path = directory / "scenario.json"

    # Create a fresh synthetic CPU incident.
    result = run([
        sys.executable, str(CPU_ENGINE),
        "--decision", str(INJECTION),
        "--state", str(cpu_state),
        "--event-id", "CPU-06E4-CREATE",
        "--observed-at", "2026-10-30T10:05:00Z",
    ])
    assert result.returncode == 0, result.stderr

    cpu_document = json.loads(cpu_state.read_text())
    incident_id = cpu_document["incident"]["incident_id"]
    assert cpu_document["incident"]["active"] is True

    scenario = json.loads(FIXTURE.read_text())
    scenario["parent"]["incident_id"] = incident_id
    scenario["child"]["event_id"] = "INGESTION-06E4-RACE"

    scenario_path.write_text(
        json.dumps(scenario, indent=2) + "\n"
    )

    # Establish a valid graph baseline while parent is OPEN.
    baseline = run([
        sys.executable, str(GUARD),
        "--scenario", str(scenario_path),
        "--contract", str(CONTRACT),
        "--cpu-state", str(cpu_state),
        "--graph-state", str(graph_state),
    ])
    assert baseline.returncode == 0, baseline.stderr

    original_sha = sha256(graph_state)

    # A distinct child will attempt to attach during resolution.
    scenario["child"]["event_id"] = "INGESTION-06E4-LATE"
    scenario["child"]["observed_at"] = "2026-10-30T10:09:00Z"
    scenario_path.write_text(
        json.dumps(scenario, indent=2) + "\n"
    )

    lock_path = Path(str(cpu_state) + ".lock")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    child = None

    try:
        # Hold the CPU lock so the guard cannot read parent state.
        fcntl.flock(fd, fcntl.LOCK_EX)

        child = subprocess.Popen(
            [
                sys.executable, str(GUARD),
                "--scenario", str(scenario_path),
                "--contract", str(CONTRACT),
                "--cpu-state", str(cpu_state),
                "--graph-state", str(graph_state),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Allow the guard to start while the CPU lock is held.
        time.sleep(0.3)

        assert child.poll() is None, (
            "GUARD_COMPLETED_WHILE_CPU_LOCK_HELD"
        )

        assert sha256(graph_state) == original_sha

        print("RESULT=GUARD_BLOCKED_BY_CPU_LOCK_PASS", flush=True)

        # The parent must be resolved before the guard gets the lock.
        # Since CPU_ENGINE also uses this lock, update the state here
        # while holding it, preserving the CPU state structure.
        updated = json.loads(cpu_state.read_text())
        updated["incident"]["state"] = "RESOLVED"
        updated["incident"]["active"] = False
        updated["incident"]["resolved_at"] = (
            "2026-10-30T10:10:00Z"
        )

        temporary = directory / "cpu_state.pending.json"
        temporary.write_text(json.dumps(updated, indent=2) + "\n")
        os.replace(temporary, cpu_state)

    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    stdout, stderr = child.communicate(timeout=15)

    assert child.returncode != 0, stdout
    assert "PARENT_NOT_ACTIVE" in stderr, stderr

    print("RESULT=RACE_PARENT_RESOLUTION_REJECTED_PASS")

    assert sha256(graph_state) == original_sha

    print("RESULT=RACE_GRAPH_IMMUTABILITY_PASS")

    final_cpu = json.loads(cpu_state.read_text())
    assert final_cpu["incident"]["active"] is False

    final_graph = json.loads(graph_state.read_text())
    assert len(final_graph["incidents"][incident_id]["children"]) == 1

    print("RESULT=LINUX_RELEASE_06E4_PARENT_RACE_PASS")
