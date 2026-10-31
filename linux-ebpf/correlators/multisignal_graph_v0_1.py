#!/usr/bin/env python3
"""Persistent synthetic incident graph with local locking."""

import argparse
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path

from multisignal_correlator_v0_1 import evaluate


def save_atomic(path, document):
    fd, temporary = tempfile.mkstemp(
        prefix=".graph-",
        suffix=".tmp",
        dir=str(path.parent)
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text())
    contract = json.loads(Path(args.contract).read_text())

    if contract.get("contract_version") != "0.1":
        raise ValueError("INVALID_POLICY_VERSION")

    if contract.get("synthetic") is not True:
        raise ValueError("NON_SYNTHETIC_POLICY")

    decision = evaluate(scenario, contract)

    if decision["action"] != "CORRELATE":
        print(json.dumps({
            "action": decision["action"],
            "state_modified": False,
            "synthetic": True
        }))
        return

    state_path = Path(args.state)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = Path(str(state_path) + ".lock")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)

        if state_path.exists():
            graph = json.loads(state_path.read_text())
        else:
            graph = {
                "graph_version": "0.1",
                "synthetic": True,
                "incidents": {}
            }

        if graph.get("graph_version") != "0.1":
            raise ValueError("INVALID_GRAPH_VERSION")

        if graph.get("synthetic") is not True:
            raise ValueError("INVALID_GRAPH_TYPE")

        incident_id = decision["incident_id"]
        child_id = decision["child_event_id"]
        parent = scenario["parent"]
        child = scenario["child"]

        incidents = graph["incidents"]

        if incident_id not in incidents:
            incidents[incident_id] = {
                "incident_id": incident_id,
                "host": parent["host"],
                "parent_event_id": parent["event_id"],
                "parent_signal": parent["signal"],
                "children": {}
            }

        incident = incidents[incident_id]

        if (
            incident["host"] != parent["host"]
            or incident["parent_event_id"] != parent["event_id"]
            or incident["parent_signal"] != parent["signal"]
        ):
            raise ValueError("PARENT_IDENTITY_CONFLICT")

        children = incident["children"]

        if child_id in children:
            existing = children[child_id]

            expected = {
                "event_id": child_id,
                "host": child["host"],
                "signal": child["signal"],
                "observed_at": child["observed_at"],
                "relationship": decision["relationship"],
                "causality_confirmed": False
            }

            if existing != expected:
                raise ValueError("CHILD_EVENT_CONFLICT")

            print(json.dumps({
                "action": "IGNORE_REPLAY",
                "incident_id": incident_id,
                "child_event_id": child_id,
                "state_modified": False,
                "synthetic": True
            }))
            return

        children[child_id] = {
            "event_id": child_id,
            "host": child["host"],
            "signal": child["signal"],
            "observed_at": child["observed_at"],
            "relationship": decision["relationship"],
            "causality_confirmed": False
        }

        save_atomic(state_path, graph)

        print(json.dumps({
            "action": "ATTACH_CHILD",
            "incident_id": incident_id,
            "child_event_id": child_id,
            "child_count": len(children),
            "state_modified": True,
            "synthetic": True
        }))

    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        sys.exit(1)
