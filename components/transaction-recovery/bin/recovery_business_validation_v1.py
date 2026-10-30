#!/usr/bin/env python3
"""TITAN synthetic recovery business validation."""

import re

class IntegrityError(Exception):
    pass

GEN = re.compile(r"GEN-[0-9]{16}")

def reject(reason):
    raise IntegrityError(reason)


def unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            reject("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def reject_constant(value):
    reject("INVALID_JSON_CONSTANT")


def generation_number(name):
    if not GEN.fullmatch(name):
        reject("INVALID_GENERATION_NAME")
    return int(name[4:])


def validate_generation_artifacts(
    incident, registry, incident_sha, registry_sha, expected
):

    if not isinstance(incident, dict) or not isinstance(registry, dict):
        reject("INVALID_ARTIFACT_STRUCTURE")

    identity = incident.get("identity")
    lifecycle = incident.get("lifecycle")
    dedup = incident.get("deduplication")
    incidents = registry.get("incidents")
    indexes = registry.get("indexes")

    if not all(isinstance(x, dict) for x in
               (identity, lifecycle, dedup, incidents, indexes)):
        reject("INVALID_INCIDENT_REGISTRY_STRUCTURE")

    incident_id = identity.get("incident_id")
    fingerprint = identity.get("incident_fingerprint")
    events = dedup.get("event_ids")
    active = incidents.get("active")
    event_owners = indexes.get("event_owners")
    fingerprint_owners = indexes.get("fingerprint_owners")

    if (
        not isinstance(incident_id, str)
        or not incident_id
        or not isinstance(fingerprint, str)
        or not fingerprint
        or not isinstance(events, list)
        or not isinstance(active, list)
        or not isinstance(event_owners, dict)
        or not isinstance(fingerprint_owners, dict)
    ):
        reject("INVALID_REFERENCE_STRUCTURE")

    if type(lifecycle.get("generation")) is not int or (
        lifecycle["generation"] != expected
    ):
        reject("GENERATION_INCONSISTENT")

    matches = [
        item for item in active
        if isinstance(item, dict)
        and item.get("incident_id") == incident_id
    ]

    if len(matches) != 1:
        reject("ACTIVE_INCIDENT_REFERENCE_INVALID")

    owner = matches[0]

    if (
        owner.get("generation") != expected
        or owner.get("incident_fingerprint") != fingerprint
        or owner.get("state") != lifecycle.get("state")
    ):
        reject("ACTIVE_INCIDENT_METADATA_MISMATCH")

    if len(events) != len(set(
        str(item) for item in events
    )):
        reject("DUPLICATE_EVENT_REFERENCE")

    for event in events:
        if not isinstance(event, str) or (
            event_owners.get(event) != incident_id
        ):
            reject("EVENT_OWNER_MISMATCH")

    owners = fingerprint_owners.get(fingerprint)
    if not isinstance(owners, list):
        reject("FINGERPRINT_OWNER_MISSING")

    matches = [
        item for item in owners
        if isinstance(item, dict)
        and item.get("incident_id") == incident_id
        and item.get("generation") == expected
    ]

    if len(matches) != 1:
        reject("FINGERPRINT_OWNER_MISMATCH")

    return {
        "incident_id": incident_id,
        "incident_sha256": incident_sha,
        "registry_sha256": registry_sha
    }
