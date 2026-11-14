from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.core_pipeline import collect_pipeline_evidence
from api.worker_health import collect_worker_health

router = APIRouter(prefix="/api/v1/platform")


def correlate_pipeline():
    pipeline = collect_pipeline_evidence()
    workers = collect_worker_health()

    reasons = []
    evidence = []
    degraded = False
    unknown = False

    outbox = pipeline.get("outbox", {})

    if outbox.get("backlog_overdue") is True:
        degraded = True
        reasons.append("Outbox backlog exceeds threshold")
        evidence.append("POSTGRES_OUTBOX_OVERDUE")
    elif outbox.get("backlog_overdue") is False:
        evidence.append("POSTGRES_OUTBOX_WITHIN_THRESHOLD")
    else:
        unknown = True
        reasons.append("Outbox backlog state unavailable")

    for group in workers.get("groups", []):
        group_id = group.get("group_id", "unknown")
        group_state = group.get("group_state", "UNKNOWN")
        lag = group.get("lag")
        status = group.get("status", "UNKNOWN")

        if status == "DEGRADED":
            degraded = True
            reasons.append(
                f"{group_id}: {group.get('reason', 'Degraded')}"
            )
            evidence.append(
                f"KAFKA_GROUP_DEGRADED:{group_id}"
            )

        elif status == "UNKNOWN":
            unknown = True
            reasons.append(
                f"{group_id}: {group.get('reason', 'Unknown')}"
            )
            evidence.append(
                f"KAFKA_GROUP_UNKNOWN:{group_id}"
            )

        elif status == "UP":
            evidence.append(
                f"KAFKA_GROUP_UP:{group_id}"
            )

        if lag is not None and lag > 0:
            evidence.append(
                f"KAFKA_LAG:{group_id}:{lag}"
            )

    if degraded:
        status = "DEGRADED"
    elif unknown:
        status = "UNKNOWN"
    else:
        # No observed backlog is not sufficient proof
        # that every pipeline worker is operational.
        if pipeline.get("worker_liveness") == "NOT_VERIFIED":
            status = "UNKNOWN"
            reasons.append(
                "End-to-end worker liveness not verified"
            )
        else:
            status = "HEALTHY"

    if not reasons:
        reasons.append(
            "No degradation detected in collected evidence"
        )


    # Activity and confidence are independent of health.
    outbox_pending = outbox.get("pending")
    group_list = workers.get("groups", [])

    known_lags = [
        group.get("lag")
        for group in group_list
    ]

    all_lags_known = bool(group_list) and all(
        isinstance(lag, int) and lag >= 0
        for lag in known_lags
    )

    if isinstance(outbox_pending, int) and all_lags_known:
        if outbox_pending == 0 and all(
            lag == 0 for lag in known_lags
        ):
            activity_state = "NO_BACKLOG_OBSERVED"
        else:
            activity_state = "BACKLOG_OBSERVED"
    else:
        activity_state = "UNKNOWN"

    if degraded:
        confidence = "HIGH"
    elif unknown or pipeline.get("worker_liveness") == "NOT_VERIFIED":
        confidence = "LIMITED"
    else:
        confidence = "MODERATE"

    assessment = {
        "health_status": status,
        "activity_state": activity_state,
        "confidence": confidence,
        "worker_liveness": pipeline.get(
            "worker_liveness",
            "NOT_VERIFIED",
        ),
        "summary": (
            "Measured degradation requires attention"
            if status == "DEGRADED"
            else
            "No backlog observed; operational readiness not fully verified"
            if status == "UNKNOWN"
            else
            "Required pipeline evidence is healthy"
        ),
    }

    return {
        "service": "titan-pipeline-correlation",
        "assessment": assessment,
        "status": status,
        "mode": "READ_ONLY",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reasons": reasons,
        "evidence": evidence,
        "pipeline": pipeline,
        "workers": workers,
    }


@router.get("/correlation")
def pipeline_correlation():
    try:
        return correlate_pipeline()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Pipeline correlation evidence unavailable",
        )
