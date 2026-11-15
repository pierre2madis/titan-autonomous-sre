"""Read-only offline incident lifecycle demonstration endpoint."""

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1")

INCIDENT_ID_PATTERN = re.compile(r"^INC-[A-Za-z0-9-]{1,128}$")


@router.get("/incidents/{incident_id}/lifecycle")
def incident_lifecycle(incident_id: str):
    if not INCIDENT_ID_PATTERN.fullmatch(incident_id):
        raise HTTPException(status_code=400, detail="Invalid incident ID")

    configured_path = os.environ.get("TITAN_OFFLINE_INCIDENT_FILE")
    if not configured_path:
        raise HTTPException(
            status_code=503,
            detail="Offline incident artifact not configured",
        )

    path = Path(configured_path)

    try:
        if not path.is_file():
            raise FileNotFoundError(str(path))

        payload = json.loads(path.read_text(encoding="utf-8"))

    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Offline incident artifact unavailable",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=503,
            detail="Invalid offline incident artifact",
        )

    if payload.get("incident_id") != incident_id:
        raise HTTPException(
            status_code=404,
            detail="Incident not found in configured offline artifact",
        )

    if (
        payload.get("event_type") != "INCIDENT_CREATED"
        or payload.get("delivery_mode") != "OFFLINE"
        or payload.get("causality_verified") is not False
        or payload.get("rca_classification")
        != "DECLARED_ROOT_EVENT_UNVERIFIED"
    ):
        raise HTTPException(
            status_code=503,
            detail="Unsupported offline incident contract",
        )

    return {
        "mode": "OFFLINE_READ_ONLY",
        "incident_id": incident_id,
        "event": payload,
        "assessment": {
            "causality_verified": False,
            "classification": "DECLARED_ROOT_EVENT_UNVERIFIED",
            "limitations": [
                "Root event is declared, not causally verified.",
                "Artifact is an offline demonstration, not live incident state.",
                "No database or Kafka evidence is consulted.",
            ],
        },
    }
