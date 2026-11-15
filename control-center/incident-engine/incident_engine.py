#!/usr/bin/env python3
"""TITAN offline incident lifecycle adapter."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def incident_event(payload):
    incident_id = payload["incident_id"]
    root_event_id = payload["root_event_id"]

    return {
        "contract_version": "1.0",
        "event_type": "INCIDENT_CREATED",
        "incident_id": incident_id,
        "correlation_key": payload["correlation_key"],
        "correlated_events": payload["correlated_events"],
        "root_event_id": root_event_id,
        "root_event_policy": payload.get(
            "root_event_policy", "DEMO_DECLARATION"
        ),
        "causality_verified": False,
        "rca_classification": "DECLARED_ROOT_EVENT_UNVERIFIED",
        "lifecycle_state": "INCIDENT",
        "source": "TITAN_CORRELATION_ENGINE",
        "delivery_mode": "OFFLINE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())

    required = (
        "incident_id",
        "correlation_key",
        "correlated_events",
        "root_event_id",
    )

    for key in required:
        if key not in payload:
            raise ValueError(f"missing required field: {key}")

    if (
        not isinstance(payload["correlated_events"], int)
        or isinstance(payload["correlated_events"], bool)
        or payload["correlated_events"] < 1
    ):
        raise ValueError("invalid correlated_events")

    event = incident_event(payload)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    serialized = json.dumps(
        event, sort_keys=True, indent=2
    ) + "\n"

    if output.exists():
        existing = output.read_text()
        if existing == serialized:
            print("IDEMPOTENT_REPLAY=PASS")
            return 0
        raise ValueError("incident output conflict")

    output.write_text(serialized)

    print("INCIDENT_EVENT=CREATED")
    print(f"INCIDENT_ID={event['incident_id']}")
    print(f"EVENT_TYPE={event['event_type']}")
    print("CAUSALITY_VERIFIED=NO")
    print("DATABASE_WRITE=NO")
    print("KAFKA_PUBLICATION=NO")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        sys.exit(1)
