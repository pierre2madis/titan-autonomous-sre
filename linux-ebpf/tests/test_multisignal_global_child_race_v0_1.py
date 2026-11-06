#!/usr/bin/env python3
"""Verify exclusive child ownership across concurrent parent incidents."""

import copy
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/multisignal_graph_v0_1.py"
CONTRACT = ROOT / "contracts/multisignal_correlation_v0_1.json"
FIXTURE = ROOT / "simulators/multisignal/fixtures/06B-01_same_host.json"

CHILD_ID = "INGESTION-06G3-SHARED"


def run_engine(scenario_path, state_path):
    return subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "--scenario", str(scenario_path),
            "--contract", str(CONTRACT),
            "--state", str(state_path),
        ],
        capture_output=True,
        text=True,
    )


def main():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="titan-06g3-") as tmp:
        directory = Path(tmp)
        state = directory / "incident_graph.json"

        scenarios = []

        for number, incident_id in enumerate(
            ("TITAN-SYNTHETIC-CPU-A", "TITAN-SYNTHETIC-CPU-B"),
            start=1,
        ):
            scenario = copy.deepcopy(original)
            scenario["parent"]["incident_id"] = incident_id
            scenario["parent"]["event_id"] = f"CPU-06G3-{number:03d}"
            scenario["child"]["event_id"] = CHILD_ID

            path = directory / f"scenario_{number}.json"
            path.write_text(
                json.dumps(scenario, indent=2) + "\n",
                encoding="utf-8",
            )
            scenarios.append(path)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(run_engine, scenario, state)
                for scenario in scenarios
            ]
            results = [future.result() for future in futures]

        if not state.exists():
            raise AssertionError("GRAPH_NOT_CREATED")

        graph = json.loads(state.read_text(encoding="utf-8"))

        owners = [
            incident_id
            for incident_id, incident in graph["incidents"].items()
            if CHILD_ID in incident.get("children", {})
        ]

        accepted = sum(
            '"ATTACH_CHILD"' in result.stdout
            for result in results
        )
        rejected = sum(
            "GLOBAL_CHILD_EVENT_CONFLICT"
            in (result.stdout + result.stderr)
            for result in results
        )

        print(f"ACCEPTED_COUNT={accepted}")
        print(f"REJECTED_COUNT={rejected}")
        print(f"CHILD_OWNER_COUNT={len(owners)}")
        print(f"CHILD_OWNERS={','.join(sorted(owners))}")

        assert accepted == 1, "EXPECTED_ONE_ACCEPTED_ATTACHMENT"
        assert rejected == 1, "EXPECTED_ONE_GLOBAL_CONFLICT"
        assert len(owners) == 1, "GLOBAL_CHILD_OWNERSHIP_VIOLATION"

        print("RESULT=CONCURRENT_GLOBAL_CHILD_OWNERSHIP_PASS")
        print("RESULT=LINUX_RELEASE_06G3_RACE_PASS")


if __name__ == "__main__":
    main()
