import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.database import database_connection

router = APIRouter(prefix="/api/v1/platform")

DEFAULT_BACKLOG_THRESHOLD_SECONDS = 300


def iso(value):
    return value.isoformat() if value is not None else None


def collect_pipeline_evidence():
    now = datetime.now(timezone.utc)

    threshold = int(
        os.getenv(
            "TITAN_OUTBOX_BACKLOG_THRESHOLD_SECONDS",
            str(DEFAULT_BACKLOG_THRESHOLD_SECONDS),
        )
    )

    if threshold <= 0:
        raise ValueError("Invalid backlog threshold")

    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    count(*) AS total,
                    max(received_at) AS last_received_at
                FROM titan.events
            """)
            events = cur.fetchone()

            cur.execute("""
                SELECT
                    count(*) FILTER (
                        WHERE published_at IS NULL
                    ) AS pending,
                    count(*) FILTER (
                        WHERE published_at IS NULL
                          AND attempts > 0
                    ) AS pending_retried,
                    min(created_at) FILTER (
                        WHERE published_at IS NULL
                    ) AS oldest_pending_at,
                    max(published_at) AS last_published_at
                FROM titan.outbox
            """)
            outbox = cur.fetchone()

            cur.execute("""
                SELECT
                    count(*) AS total,
                    max(received_at) AS last_received_at
                FROM titan.transition_inbox
            """)
            inbox = cur.fetchone()

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (
                        WHERE state NOT IN ('RESOLVED', 'CLOSED')
                    ) AS unresolved
                FROM titan.incident_states
            """)
            incidents = cur.fetchone()

    pending = outbox["pending"]
    oldest = outbox["oldest_pending_at"]

    backlog_age = (
        max(0, int((now - oldest).total_seconds()))
        if oldest is not None
        else None
    )

    backlog_overdue = (
        pending > 0
        and backlog_age is not None
        and backlog_age >= threshold
    )

    if backlog_overdue:
        status = "DEGRADED"
        reason = "Outbox backlog exceeds configured threshold"
    else:
        status = "UNKNOWN"
        reason = (
            "No overdue outbox backlog; "
            "worker liveness not verified"
        )

    activity = (
        "BACKLOG"
        if pending > 0
        else "IDLE_OR_UNOBSERVED"
    )

    return {
        "service": "titan-core-pipeline",
        "status": status,
        "reason": reason,
        "activity": activity,
        "mode": "READ_ONLY",
        "checked_at": now.isoformat(),
        "thresholds": {
            "outbox_backlog_seconds": threshold,
        },
        "events": {
            "total": events["total"],
            "last_received_at": iso(events["last_received_at"]),
        },
        "outbox": {
            "pending": pending,
            "pending_retried": outbox["pending_retried"],
            "oldest_pending_at": iso(oldest),
            "oldest_pending_age_seconds": backlog_age,
            "last_published_at": iso(outbox["last_published_at"]),
            "backlog_overdue": backlog_overdue,
        },
        "transition_inbox": {
            "total": inbox["total"],
            "last_received_at": iso(inbox["last_received_at"]),
        },
        "incidents": {
            "total": incidents["total"],
            "unresolved": incidents["unresolved"],
        },
        "worker_liveness": "NOT_VERIFIED",
    }


@router.get("/pipeline")
def pipeline_evidence():
    try:
        return collect_pipeline_evidence()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Pipeline evidence unavailable",
        )
