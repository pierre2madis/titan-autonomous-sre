#!/usr/bin/env python3
"""Deterministic synthetic multi-signal correlation engine."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("INVALID_TIMESTAMP")

    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")

    return timestamp.astimezone(timezone.utc)


def evaluate(document, contract):
    if document.get("contract_version") != "0.1":
        raise ValueError("INVALID_CONTRACT_VERSION")

    parent = document["parent"]
    child = document["child"]
    policy = contract["correlation"]

    if parent.get("synthetic") is not True:
        raise ValueError("NON_SYNTHETIC_PARENT")

    if child.get("synthetic") is not True:
        raise ValueError("NON_SYNTHETIC_CHILD")

    if parent.get("signal") != policy["parent_signal"]:
        raise ValueError("INVALID_PARENT_SIGNAL")

    if child.get("signal") != policy["child_signal"]:
        raise ValueError("INVALID_CHILD_SIGNAL")

    for event in (parent, child):
        if not isinstance(event.get("event_id"), str) or not event["event_id"]:
            raise ValueError("MISSING_EVENT_ID")

        if not isinstance(event.get("host"), str) or not event["host"]:
            raise ValueError("MISSING_HOST")

    if not isinstance(parent.get("incident_id"), str) or not parent["incident_id"]:
        raise ValueError("MISSING_PARENT_INCIDENT_ID")

    parent_time = parse_timestamp(parent["observed_at"])
    child_time = parse_timestamp(child["observed_at"])

    delta = (child_time - parent_time).total_seconds()

    if parent.get("incident_state") != "OPEN":
        action = "REJECT_INACTIVE"
    elif policy["same_host_required"] and parent["host"] != child["host"]:
        action = "REJECT_HOST"
    elif delta < 0:
        action = "REJECT_ORDER"
    elif delta > policy["window_seconds"]:
        action = "REJECT_WINDOW"
    else:
        action = "CORRELATE"

    return {
        "scenario_id": document["scenario_id"],
        "action": action,
        "parent_event_id": parent["event_id"],
        "child_event_id": child["event_id"],
        "parent_incident_id": parent["incident_id"],
        "incident_id": parent["incident_id"] if action == "CORRELATE" else None,
        "delta_seconds": delta,
        "relationship": policy["relationship"] if action == "CORRELATE" else None,
        "causality_confirmed": False,
        "synthetic": True
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()

    document = json.loads(Path(args.scenario).read_text())
    contract = json.loads(Path(args.contract).read_text())

    if contract.get("contract_version") != "0.1":
        raise ValueError("INVALID_POLICY_VERSION")

    if contract.get("synthetic") is not True:
        raise ValueError("NON_SYNTHETIC_POLICY")

    result = evaluate(document, contract)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        sys.exit(1)
