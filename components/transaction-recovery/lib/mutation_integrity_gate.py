#!/usr/bin/env python3
import argparse
import copy
import json
import re
import sys
from pathlib import Path

EVENT_PATTERN = re.compile(r"EVT-[A-F0-9]{24}\Z")


def reject(reason):
    print(f"ERROR={reason}")
    sys.exit(1)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=unique_pairs)
    except (OSError, ValueError) as exc:
        reject(f"INVALID_JSON:{type(exc).__name__}")


def get(obj, *path):
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            reject("MISSING_REQUIRED_FIELD")
        obj = obj[key]
    return obj


def check(before, registry, mutation):
    if not isinstance(mutation, dict):
        reject("INVALID_MUTATION")

    if set(mutation) != {"incident", "registry"}:
        reject("INVALID_MUTATION_KEYS")

    after = mutation["incident"]
    new_registry = mutation["registry"]

    if not all(isinstance(x, dict) for x in
               (before, registry, after, new_registry)):
        reject("INVALID_DOCUMENT_TYPE")

    identity = get(before, "identity")
    incident_id = get(identity, "incident_id")
    fingerprint = get(identity, "incident_fingerprint")

    if get(after, "identity") != identity:
        reject("INCIDENT_IDENTITY_CHANGED")

    generation = get(before, "lifecycle", "generation")

    if type(generation) is not int or generation < 0:
        reject("INVALID_BASE_GENERATION")

    if get(after, "lifecycle", "generation") != generation + 1:
        reject("INCIDENT_GENERATION_MISMATCH")

    old_ids = get(before, "deduplication", "event_ids")
    new_ids = get(after, "deduplication", "event_ids")

    if not isinstance(old_ids, list) or not isinstance(new_ids, list):
        reject("INVALID_EVENT_LIST")

    if len(old_ids) != len(set(old_ids)):
        reject("INVALID_BASE_EVENT_LIST")

    if len(new_ids) != len(old_ids) + 1:
        reject("INVALID_EVENT_DELTA")

    if new_ids[:len(old_ids)] != old_ids:
        reject("EXISTING_EVENTS_CHANGED")

    event_id = new_ids[-1]

    if not isinstance(event_id, str) or not EVENT_PATTERN.fullmatch(event_id):
        reject("INVALID_NEW_EVENT_ID")

    buckets = ("supporting", "exonerating",
               "indeterminate", "unavailable")

    old_evidence = get(before, "evidence")
    new_evidence = get(after, "evidence")

    if set(old_evidence) != set(buckets) or \
       set(new_evidence) != set(buckets):
        reject("EVIDENCE_BUCKETS_CHANGED")

    additions = []

    for bucket in buckets:
        old_items = old_evidence[bucket]
        new_items = new_evidence[bucket]

        if not isinstance(old_items, list) or \
           not isinstance(new_items, list):
            reject("INVALID_EVIDENCE_BUCKET")

        if new_items[:len(old_items)] != old_items:
            reject("EXISTING_EVIDENCE_CHANGED")

        additions.extend(new_items[len(old_items):])

    if len(additions) != 1:
        reject("INVALID_EVIDENCE_DELTA")

    event = additions[0]

    if not isinstance(event, dict) or event.get("event_id") != event_id:
        reject("EVIDENCE_EVENT_MISMATCH")

    # Reconstruct the only permitted incident mutation.
    expected_incident = copy.deepcopy(before)
    expected_incident["lifecycle"]["generation"] = generation + 1
    expected_incident["deduplication"]["event_ids"].append(event_id)

    for bucket in buckets:
        expected_incident["evidence"][bucket] = copy.deepcopy(
            old_evidence[bucket]
        )

    for bucket in buckets:
        if len(new_evidence[bucket]) > len(old_evidence[bucket]):
            expected_incident["evidence"][bucket].append(event)

    if after != expected_incident:
        reject("UNAUTHORIZED_INCIDENT_MUTATION")

    old_active = get(registry, "incidents", "active")
    new_active = get(new_registry, "incidents", "active")

    if not isinstance(old_active, list) or not isinstance(new_active, list):
        reject("INVALID_ACTIVE_INCIDENTS")

    matches = [
        i for i, item in enumerate(old_active)
        if isinstance(item, dict) and
        item.get("incident_id") == incident_id
    ]

    if len(matches) != 1:
        reject("BASE_INCIDENT_NOT_UNIQUE")

    position = matches[0]
    expected_registry = copy.deepcopy(registry)

    expected_registry["incidents"]["active"][position]["generation"] = (
        generation + 1
    )

    owners = get(expected_registry, "indexes", "event_owners")

    if not isinstance(owners, dict) or event_id in owners:
        reject("EVENT_ALREADY_OWNED")

    owners[event_id] = incident_id

    fingerprint_owners = get(
        expected_registry, "indexes", "fingerprint_owners"
    )

    if not isinstance(fingerprint_owners, dict):
        reject("INVALID_FINGERPRINT_INDEX")

    entries = fingerprint_owners.get(fingerprint)

    if not isinstance(entries, list):
        reject("MISSING_FINGERPRINT_OWNER")

    matching = [
        item for item in entries
        if isinstance(item, dict) and
        item.get("incident_id") == incident_id
    ]

    if len(matching) != 1:
        reject("FINGERPRINT_OWNER_NOT_UNIQUE")

    matching[0]["generation"] = generation + 1

    if new_registry != expected_registry:
        reject("UNAUTHORIZED_REGISTRY_MUTATION")

    print("mutation_type=ATTACH_EVIDENCE")
    print(f"incident_id={incident_id}")
    print(f"attached_event_id={event_id}")
    print(f"previous_generation={generation}")
    print(f"next_generation={generation + 1}")
    print("incident_integrity=PASS")
    print("registry_integrity=PASS")
    print("RESULT=MUTATION_INTEGRITY_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--mutation", required=True)
    args = parser.parse_args()

    before = load(Path(args.incident))
    registry = load(Path(args.registry))
    mutation = load(Path(args.mutation))

    check(before, registry, mutation)


if __name__ == "__main__":
    main()
