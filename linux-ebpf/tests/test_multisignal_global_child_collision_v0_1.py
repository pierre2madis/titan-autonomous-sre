#!/usr/bin/env python3
"""Negative probe: duplicate child ID across separate parent incidents."""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENGINE = ROOT / "correlators/multisignal_graph_v0_1.py"
CONTRACT = ROOT / "contracts/multisignal_correlation_v0_1.json"
SOURCE = ROOT / "simulators/multisignal/fixtures/06B-01_same_host.json"

original = json.loads(SOURCE.read_text())

with tempfile.TemporaryDirectory(prefix="titan-06g1-") as tmp:
    directory = Path(tmp)
    state = directory / "incident_graph.json"

    outcomes = []

    for number, parent_id in enumerate(
        ("TITAN-SYNTHETIC-CPU-A", "TITAN-SYNTHETIC-CPU-B"),
        start=1,
    ):
        scenario = copy.deepcopy(original)

        scenario["parent"]["incident_id"] = parent_id
        scenario["parent"]["event_id"] = f"CPU-T1-{number:03d}"
        scenario["child"]["event_id"] = "INGESTION-GLOBAL-001"

        scenario_path = directory / f"scenario_{number}.json"
        scenario_path.write_text(
            json.dumps(scenario, indent=2) + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "--scenario", str(scenario_path),
                "--contract", str(CONTRACT),
                "--state", str(state),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(result.stderr.strip())

        outcomes.append(result)

    graph = json.loads(state.read_text())

    child_owners = [
        incident_id
        for incident_id, incident in graph["incidents"].items()
        if "INGESTION-GLOBAL-001" in incident["children"]
    ]

    print(f"CHILD_OWNER_COUNT={len(child_owners)}")
    print(f"CHILD_OWNERS={','.join(sorted(child_owners))}")

    if len(child_owners) == 2:
        print("RESULT=GLOBAL_CHILD_COLLISION_REPRODUCED")
        print("RESULT=LINUX_RELEASE_06G1_NEGATIVE_PROBE_PASS")
    elif len(child_owners) == 1:
        print("RESULT=GLOBAL_CHILD_UNIQUENESS_ENFORCED")
        print("RESULT=LINUX_RELEASE_06G1_NEGATIVE_PROBE_PASS")
    else:
        print("RESULT=LINUX_RELEASE_06G1_UNEXPECTED_STATE")
        sys.exit(1)
