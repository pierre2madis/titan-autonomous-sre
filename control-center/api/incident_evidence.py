"""Read-only offline incident evidence API."""

import hashlib
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1")

INCIDENT_ID_PATTERN = re.compile(
    r"^INC-[A-Za-z0-9-]{1,128}$"
)

MAX_ARTIFACT_BYTES = 1024 * 1024


def read_artifact(path: Path):
    try:
        if not path.is_file():
            raise ValueError("Artifact is not a regular file")

        with path.open("rb") as stream:
            raw = stream.read(MAX_ARTIFACT_BYTES + 1)

        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("Artifact exceeds size limit")

        payload = json.loads(raw)

        if not isinstance(payload, dict):
            raise ValueError("Artifact must be a JSON object")

        digest = hashlib.sha256(raw).hexdigest()

        return payload, digest, len(raw)

    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Offline evidence artifact unavailable",
        ) from exc


@router.get("/incidents/{incident_id}/evidence")
def incident_evidence(incident_id: str):
    if not INCIDENT_ID_PATTERN.fullmatch(incident_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid incident ID",
        )

    event_file = os.environ.get(
        "TITAN_OFFLINE_INCIDENT_FILE"
    )
    input_file = os.environ.get(
        "TITAN_OFFLINE_CORRELATION_INPUT_FILE"
    )

    if not event_file or not input_file:
        raise HTTPException(
            status_code=503,
            detail="Offline evidence artifacts not configured",
        )

    event, event_sha, event_size = read_artifact(
        Path(event_file)
    )
    source, source_sha, source_size = read_artifact(
        Path(input_file)
    )

    if (
        event.get("incident_id") != incident_id
        or source.get("incident_id") != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found in offline artifacts",
        )

    required_fields = (
        "correlation_key",
        "correlated_events",
        "root_event_id",
        "root_event_policy",
    )

    if any(
        event.get(field) != source.get(field)
        for field in required_fields
    ):
        raise HTTPException(
            status_code=409,
            detail="Offline evidence artifacts disagree",
        )

    if (
        event.get("event_type") != "INCIDENT_CREATED"
        or event.get("delivery_mode") != "OFFLINE"
        or event.get("causality_verified") is not False
        or event.get("rca_classification")
        != "DECLARED_ROOT_EVENT_UNVERIFIED"
        or source.get("root_event_policy")
        != "DEMO_DECLARATION"
        or type(source.get("correlated_events")) is not int
        or source["correlated_events"] < 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Unsupported offline evidence contract",
        )

    return {
        "mode": "OFFLINE_READ_ONLY",
        "incident_id": incident_id,
        "verification_status": "UNVERIFIED",
        "review_only": True,
        "causality_verified": False,
        "remediation_allowed": False,
        "correlation": {
            "correlation_key": source["correlation_key"],
            "declared_event_count": source["correlated_events"],
            "individual_event_records_available": False,
            "root_event_id": source["root_event_id"],
            "root_event_policy": source["root_event_policy"],
            "independent_corroboration": False,
        },
        "artifacts": [
            {
                "role": "CORRELATION_INPUT",
                "sha256": source_sha,
                "size_bytes": source_size,
                "verification_status": "UNVERIFIED",
            },
            {
                "role": "LIFECYCLE_EVENT",
                "sha256": event_sha,
                "size_bytes": event_size,
                "verification_status": "UNVERIFIED",
            },
        ],
        "limitations": [
            "Correlation input contains references, not individual event records.",
            "The declared root event is not causally verified.",
            "No independent corroboration is established.",
            "No database or Kafka evidence is consulted.",
            "Offline artifacts do not establish live incident state.",
        ],
    }
