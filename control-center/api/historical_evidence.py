"""Read-only historical evidence API for TITAN Control Center."""

from fastapi import APIRouter, HTTPException
from psycopg import Error as PostgresError

from api.database import database_connection


router = APIRouter(
    prefix="/api/v1/evidence/historical",
    tags=["Historical Evidence"],
)


@router.get("/{event_id}")
def get_historical_evidence(event_id: str):
    if not event_id.startswith("EVT-") or len(event_id) > 256:
        raise HTTPException(
            status_code=400,
            detail="Invalid event identifier",
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
            detail="Historical evidence unavailable",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Historical evidence not found",
        )

    payload = row["payload"]

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=409,
            detail="Invalid historical evidence payload",
        )

    provenance = payload.get("provenance")

    if not isinstance(provenance, dict):
        raise HTTPException(
            status_code=409,
            detail="Historical provenance missing",
        )

    required = (
        row["source"] == "LINUX_CPU_HISTORICAL_IMPORT"
        and row["event_type"] == "CPU_EVIDENCE_OBSERVATION"
        and provenance.get("kind") == "UNVERIFIED"
        and provenance.get("verified") is False
        and provenance.get("historical") is True
        and provenance.get("synthetic_status") == "NOT_ESTABLISHED"
        and payload.get("historical") is True
        and payload.get("review_only") is True
        and payload.get("causality_verified") is False
        and payload.get("remediation_allowed") is False
    )

    if not required:
        raise HTTPException(
            status_code=409,
            detail="Historical evidence policy violation",
        )

    return {
        "event_id": row["event_id"],
        "source": row["source"],
        "event_type": row["event_type"],
        "host": row["host"],
        "correlation_key": row["correlation_key"],
        "observed_at": row["observed_at"],
        "received_at": row["received_at"],
        "classification": "HISTORICAL_UNVERIFIED",
        "verification_status": "UNVERIFIED",
        "review_only": True,
        "causality_verified": False,
        "remediation_allowed": False,
        "provenance": provenance,
        "payload": payload,
    }
