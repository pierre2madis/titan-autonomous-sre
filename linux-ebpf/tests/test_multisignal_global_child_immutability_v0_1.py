#!/usr/bin/env python3
"""Verify rejected cross-incident child ownership preserves graph bytes."""

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
FIXTURE = ROOT / "simulators/multisignal/fixtures/06B-01_same_host.json"

CHILD_ID = "INGESTION-06G4-SHARED"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_engine(scenario, state):
    return subprocess.run(
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


def main():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="titan-06g4-") as tmp:
        directory = Path(tmp)
        state = directory / "incident_graph.json"

        scenarios = []

        for number, incident_id in enumerate(
            ("TITAN-SYNTHETIC-CPU-A", "TITAN-SYNTHETIC-CPU-B"),
            start=1,
        ):
            scenario = copy.deepcopy(original)
            scenario["parent"]["incident_id"] = incident_id
            scenario["parent"]["event_id"] = f"CPU-06G4-{number:03d}"
            scenario["child"]["event_id"] = CHILD_ID

            path = directory / f"scenario_{number}.json"
            path.write_text(
                json.dumps(scenario, indent=2) + "\n",
                encoding="utf-8",
            )
            scenarios.append(path)

        first = run_engine(scenarios[0], state)

        assert first.returncode == 0, (
            "INITIAL_ATTACHMENT_FAILED\n"
            + first.stdout + first.stderr
        )

        assert state.exists(), "INITIAL_GRAPH_MISSING"

        before = sha256(state)

        second = run_engine(scenarios[1], state)

        combined = second.stdout + second.stderr

        assert "GLOBAL_CHILD_EVENT_CONFLICT" in combined, (
            "GLOBAL_CONFLICT_NOT_REPORTED\n" + combined
        )

        after = sha256(state)

        assert before == after, "GRAPH_MUTATED_AFTER_REJECTION"

        graph = json.loads(state.read_text(encoding="utf-8"))

        owners = [
            incident_id
            for incident_id, incident in graph["incidents"].items()
            if CHILD_ID in incident.get("children", {})
        ]

        assert owners == ["TITAN-SYNTHETIC-CPU-A"], (
            f"UNEXPECTED_CHILD_OWNERS={owners}"
        )

        print("RESULT=GLOBAL_CHILD_CONFLICT_REJECTED_PASS")
        print("RESULT=GLOBAL_CHILD_GRAPH_SHA256_IMMUTABLE_PASS")
        print("RESULT=GLOBAL_CHILD_SINGLE_OWNER_PASS")
        print("RESULT=LINUX_RELEASE_06G4_IMMUTABILITY_PASS")


if __name__ == "__main__":
    main()
