"""Read-only integration evidence API for TITAN Control Center."""

import re

from fastapi import APIRouter, HTTPException
from psycopg import Error as PostgresError

from api.database import database_connection


router = APIRouter(
    prefix="/api/v1/evidence/integration",
    tags=["Integration Evidence"],
)

EVENT_ID_PATTERN = re.compile(r"TITAN-[A-Za-z0-9-]{1,250}\Z")


@router.get("/{event_id}")
def get_integration_evidence(event_id: str):
    if not EVENT_ID_PATTERN.fullmatch(event_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid integration event identifier",
        )

    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        event_id,
                        source,
                        event_type,
                        host,
                        correlation_key,
                        observed_at,
                        received_at,
                        payload
                    FROM titan.events
                    WHERE event_id = %s
                    """,
                    (event_id,),
                )
                row = cur.fetchone()

    except (PostgresError, OSError, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Integration evidence unavailable",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Integration event not found",
        )

    if row["source"] != "TITAN":
        raise HTTPException(
            status_code=409,
            detail="Integration evidence source mismatch",
        )

    if not isinstance(row["payload"], dict):
        raise HTTPException(
            status_code=409,
            detail="Invalid integration evidence payload",
        )

    return {
        "event_id": row["event_id"],
        "source": row["source"],
        "event_type": row["event_type"],
        "host": row["host"],
        "correlation_key": row["correlation_key"],
        "observed_at": row["observed_at"],
        "received_at": row["received_at"],
        "classification": "TEST_UNVERIFIED",
        "verification_status": "UNVERIFIED",
        "review_only": True,
        "causality_verified": False,
        "remediation_allowed": False,
        "payload": row["payload"],
    }
