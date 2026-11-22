"""Read-only Splunk cluster evidence endpoint for TITAN."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/splunk", tags=["Splunk Evidence"])

MAX_ARTIFACT_BYTES = 1024 * 1024
CLASSIFICATIONS = {
    "HEALTHY",
    "EXPECTED_DOWN",
    "UNEXPECTED_DOWN",
    "UNKNOWN",
}


def _read_evidence(path):
    if not path.is_file():
        raise ValueError("Evidence artifact unavailable")

    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("Evidence artifact exceeds size limit")

    with path.open("rb") as stream:
        raw = stream.read(MAX_ARTIFACT_BYTES + 1)

    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Evidence artifact exceeds size limit")

    payload = json.loads(raw)

    if not isinstance(payload, dict):
        raise ValueError("Invalid evidence structure")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("Missing evidence metadata")

    if evidence.get("contract_version") != "0.2":
        raise ValueError("Unsupported evidence contract")

    if payload.get("classification") not in CLASSIFICATIONS:
        raise ValueError("Unsupported classification")

    if type(payload.get("incident_candidate")) is not bool:
        raise ValueError("Invalid incident candidate")

    if type(evidence.get("fresh")) is not bool:
        raise ValueError("Invalid freshness flag")

    if type(evidence.get("complete")) is not bool:
        raise ValueError("Invalid completeness flag")

    if type(evidence.get("recognized")) is not bool:
        raise ValueError("Invalid recognition flag")

    if not isinstance(payload.get("event_id"), str):
        raise ValueError("Missing event ID")

    return payload


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Invalid observation timestamp")

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        raise ValueError("Observation timestamp lacks timezone")

    return parsed.astimezone(timezone.utc)


@router.get("/cluster/evidence")
def splunk_cluster_evidence():
    configured = os.environ.get("TITAN_SPLUNK_EVIDENCE_FILE")

    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Splunk evidence artifact not configured",
        )

    try:
        payload = _read_evidence(Path(configured))
        metadata = payload["evidence"]

        max_age = int(
            os.environ.get("TITAN_SPLUNK_MAX_EVIDENCE_AGE_SECONDS", "120")
        )
        if not 1 <= max_age <= 86400:
            raise ValueError("Invalid evidence age policy")

        observed_at = _timestamp(metadata.get("observed_at"))
        now = datetime.now(timezone.utc)
        age_seconds = (now - observed_at).total_seconds()

        current = (
            0 <= age_seconds <= max_age
            and metadata["fresh"]
            and metadata["complete"]
            and metadata["recognized"]
        )

        observed_classification = payload["classification"]

        effective_classification = (
            observed_classification if current else "UNKNOWN"
        )

        return {
            "mode": "OFFLINE_READ_ONLY",
            "source": "SPLUNK",
            "event_id": payload["event_id"],
            "observed_at": metadata["observed_at"],
            "evaluated_at": now.isoformat(),
            "age_seconds": round(age_seconds, 3),
            "max_age_seconds": max_age,
            "fresh": current,
            "observed_classification": observed_classification,
            "classification": effective_classification,
            "incident_candidate": (
                payload["incident_candidate"] if current else False
            ),
            "evidence": metadata,
            "limitations": [
                "Artifact is a snapshot, not a live Splunk query.",
                "Freshness is recalculated for each API request.",
                "No incident creation or remediation is performed.",
            ],
        }

    except (OSError, ValueError, TypeError, UnicodeError,
            json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Splunk evidence unavailable or invalid",
        ) from exc
