#!/usr/bin/env python3

import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "fixtures"
OUTPUT.mkdir(parents=True, exist_ok=True)

PARENT = {
    "event_id": "CPU-T1-001",
    "host": "us02",
    "signal": "CPU_PSI_PRESSURE",
    "observed_at": "2026-10-30T10:05:00Z",
    "incident_id": "TITAN-SYNTHETIC-CPU-001",
    "incident_state": "OPEN",
    "synthetic": True
}

SCENARIOS = {
    "06B-01_same_host": {
        "host": "us02",
        "observed_at": "2026-10-30T10:08:00Z",
        "expected": "CORRELATE"
    },
    "06B-02_different_host": {
        "host": "idx01",
        "observed_at": "2026-10-30T10:08:00Z",
        "expected": "REJECT_HOST"
    },
    "06B-03_outside_window": {
        "host": "us02",
        "observed_at": "2026-10-30T10:12:00Z",
        "expected": "REJECT_WINDOW"
    },
    "06B-04_child_before_parent": {
        "host": "us02",
        "observed_at": "2026-10-30T10:04:00Z",
        "expected": "REJECT_ORDER"
    },
    "06B-05_resolved_parent": {
        "host": "us02",
        "observed_at": "2026-10-30T10:08:00Z",
        "expected": "REJECT_INACTIVE"
    }
}

for name, configuration in SCENARIOS.items():
    parent = dict(PARENT)

    if name == "06B-05_resolved_parent":
        parent["incident_state"] = "RESOLVED"

    child = {
        "event_id": f"INGESTION-{name[:6]}",
        "host": configuration["host"],
        "signal": "SPLUNK_INGESTION_PRESSURE",
        "observed_at": configuration["observed_at"],
        "synthetic": True
    }

    document = {
        "scenario_id": name,
        "contract_version": "0.1",
        "parent": parent,
        "child": child,
        "expected_action": configuration["expected"]
    }

    destination = OUTPUT / f"{name}.json"

    destination.write_text(
        json.dumps(document, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"GENERATED={destination.name}")

print("RESULT=LINUX_RELEASE_06B_FIXTURES_GENERATED")
