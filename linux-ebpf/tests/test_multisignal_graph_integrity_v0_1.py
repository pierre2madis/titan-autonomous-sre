#!/usr/bin/env python3
"""Integrity tests for synthetic persistent incident graphs."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/multisignal_graph_v0_1.py"
CONTRACT = ROOT / "contracts/multisignal_correlation_v0_1.json"
FIXTURES = ROOT / "simulators/multisignal/fixtures"

POSITIVE = FIXTURES / "06B-01_same_host.json"

NEGATIVE = {
    "06B-02_different_host": "REJECT_HOST",
    "06B-03_outside_window": "REJECT_WINDOW",
    "06B-04_child_before_parent": "REJECT_ORDER",
    "06B-05_resolved_parent": "REJECT_INACTIVE",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(scenario, state):
    result = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "--scenario", str(scenario),
            "--contract", str(CONTRACT),
            "--state", str(state),
        ],
        capture_output=True,
        text=True,
    )

    return result


def write_scenario(path, document):
    path.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8",
    )


with tempfile.TemporaryDirectory(prefix="titan-06d2-") as tmp:
    directory = Path(tmp)
    state = directory / "incident_graph.json"

    # Test 1: Initial attachment and identical replay.
    first = run(POSITIVE, state)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["action"] == "ATTACH_CHILD"

    initial_hash = digest(state)

    replay = run(POSITIVE, state)
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["action"] == "IGNORE_REPLAY"
    assert digest(state) == initial_hash

    print("RESULT=GRAPH_REPLAY_IMMUTABILITY_PASS")

    # Test 2: Same child event ID, changed content.
    original = json.loads(POSITIVE.read_text())
    conflict = copy.deepcopy(original)

    conflict["child"]["observed_at"] = (
        "2026-10-30T10:09:00Z"
    )

    conflict_path = directory / "child_conflict.json"
    write_scenario(conflict_path, conflict)

    result = run(conflict_path, state)

    assert result.returncode != 0
    assert "CHILD_EVENT_CONFLICT" in result.stderr
    assert digest(state) == initial_hash

    print("RESULT=CHILD_EVENT_CONFLICT_REJECTED_PASS")

    # Test 3: Negative scenarios must not modify state.
    for scenario_name, expected_action in NEGATIVE.items():
        scenario = FIXTURES / f"{scenario_name}.json"

        result = run(scenario, state)

        assert result.returncode == 0, result.stderr

        output = json.loads(result.stdout)

        assert output["action"] == expected_action
        assert output["state_modified"] is False
        assert digest(state) == initial_hash

        print(f"RESULT={scenario_name}:IMMUTABLE:PASS")

    print("RESULT=NEGATIVE_SCENARIO_IMMUTABILITY_PASS")

    # Test 4: Parent identity conflict.
    parent_conflict = copy.deepcopy(original)

    parent_conflict["parent"]["event_id"] = (
        "CPU-T1-DIFFERENT"
    )

    conflict_path = directory / "parent_conflict.json"
    write_scenario(conflict_path, parent_conflict)

    result = run(conflict_path, state)

    assert result.returncode != 0
    assert "PARENT_IDENTITY_CONFLICT" in result.stderr
    assert digest(state) == initial_hash

    print("RESULT=PARENT_IDENTITY_CONFLICT_REJECTED_PASS")

    # Final graph invariant.
    graph = json.loads(state.read_text())

    assert graph["graph_version"] == "0.1"
    assert graph["synthetic"] is True
    assert len(graph["incidents"]) == 1

    incident = graph["incidents"]["TITAN-SYNTHETIC-CPU-001"]

    assert len(incident["children"]) == 1
    assert incident["children"]["INGESTION-06B-01"][
        "causality_confirmed"
    ] is False

    print("RESULT=LINUX_RELEASE_06D_GRAPH_INTEGRITY_SUITE_PASS")
