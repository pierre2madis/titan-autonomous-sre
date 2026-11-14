from api.pipeline_correlation import router as correlation_router
from api.worker_health import router as worker_router
from api.core_pipeline import router as pipeline_router
from api.platform_health import router as platform_router
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from psycopg import OperationalError

from api.database import database_connection


app = FastAPI(
    title="TITAN Control Center API",
    version="0.1.0",
    description="Read-only operational API for TITAN Autonomous SRE",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


app.include_router(platform_router)
app.include_router(pipeline_router)
app.include_router(worker_router)
app.include_router(correlation_router)

@app.get("/api/v1/health")
def health():
    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return {
            "service": "titan-control-center-api",
            "status": "UP",
            "database": "AVAILABLE",
            "mode": "READ_ONLY",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


@app.get("/api/v1/incidents")
def list_incidents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    state: Optional[str] = Query(default=None, max_length=64),
):
    query = """
        SELECT
            incident_id,
            correlation_key,
            state,
            severity,
            root_event_id,
            opened_at,
            updated_at,
            resolved_at
        FROM titan.incident_states
    """

    params = []

    if state:
        query += " WHERE state = %s"
        params.append(state)

    query += """
        ORDER BY updated_at DESC, incident_id
        LIMIT %s OFFSET %s
    """

    params.extend([limit, offset])

    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return {
            "items": [
                {
                    key: serialize_datetime(value)
                    for key, value in row.items()
                }
                for row in rows
            ],
            "limit": limit,
            "offset": offset,
            "mode": "READ_ONLY",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Incident data unavailable",
        )


@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    if len(incident_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid incident ID")

    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        incident_id,
                        correlation_key,
                        state,
                        severity,
                        root_event_id,
                        opened_at,
                        updated_at,
                        resolved_at
                    FROM titan.incident_states
                    WHERE incident_id = %s
                    """,
                    (incident_id,),
                )
                row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Incident not found",
            )

        return {
            key: serialize_datetime(value)
            for key, value in row.items()
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Incident data unavailable",
        )


@app.get("/api/v1/incidents/{incident_id}/timeline")
def incident_timeline(
    incident_id: str,
    limit: int = Query(default=50, ge=1, le=100),
):
    if len(incident_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid incident ID")

    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        event_id,
                        transition_id,
                        incident_id,
                        topic,
                        partition_id,
                        kafka_offset,
                        received_at
                    FROM titan.transition_inbox
                    WHERE incident_id = %s
                    ORDER BY received_at ASC, event_id ASC
                    LIMIT %s
                    """,
                    (incident_id, limit),
                )
                rows = cur.fetchall()

        return {
            "incident_id": incident_id,
            "items": [
                {
                    key: serialize_datetime(value)
                    for key, value in row.items()
                }
                for row in rows
            ],
            "count": len(rows),
            "mode": "READ_ONLY",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Timeline unavailable",
        )
