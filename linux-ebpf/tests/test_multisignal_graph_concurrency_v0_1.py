#!/usr/bin/env python3
"""Concurrent child attachment test for TITAN synthetic incident graph."""

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

with tempfile.TemporaryDirectory(prefix="titan-06d3-") as tmp:
    directory = Path(tmp)
    state = directory / "incident_graph.json"

    original = json.loads(SOURCE.read_text())

    processes = []

    for number, observed_at in (
        (1, "2026-10-30T10:08:00Z"),
        (2, "2026-10-30T10:09:00Z"),
    ):
        scenario = copy.deepcopy(original)

        scenario["child"]["event_id"] = (
            f"INGESTION-CONCURRENT-{number:03d}"
        )
        scenario["child"]["observed_at"] = observed_at

        path = directory / f"scenario_{number}.json"

        path.write_text(
            json.dumps(scenario, indent=2) + "\n",
            encoding="utf-8",
        )

        command = [
            sys.executable,
            str(ENGINE),
            "--scenario", str(path),
            "--contract", str(CONTRACT),
            "--state", str(state),
        ]

        processes.append(
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    for number, process in enumerate(processes, start=1):
        stdout, stderr = process.communicate(timeout=15)

        assert process.returncode == 0, stderr

        result = json.loads(stdout)

        assert result["action"] == "ATTACH_CHILD"

        print(f"RESULT=CONCURRENT_CHILD_{number}_PASS")

    graph = json.loads(state.read_text())

    assert graph["graph_version"] == "0.1"
    assert graph["synthetic"] is True

    incidents = graph["incidents"]

    assert len(incidents) == 1

    incident = incidents["TITAN-SYNTHETIC-CPU-001"]

    children = incident["children"]

    assert len(children) == 2

    assert set(children) == {
        "INGESTION-CONCURRENT-001",
        "INGESTION-CONCURRENT-002",
    }

    assert all(
        child["causality_confirmed"] is False
        for child in children.values()
    )

    print("RESULT=NO_LOST_UPDATE_PASS")
    print("RESULT=SINGLE_PARENT_INCIDENT_PASS")
    print("RESULT=LINUX_RELEASE_06D3_CONCURRENCY_PASS")
