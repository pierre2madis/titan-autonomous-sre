"""Read-only, evidence-bounded incident investigation; not a causal inference engine."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from api.database import database_connection

router = APIRouter(prefix="/api/v1")


def as_json(row):
    return {key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in row.items()}


@router.get("/incidents/{incident_id}/rca")
def incident_rca(incident_id: str, limit: int = Query(25, ge=1, le=50)):
    if not incident_id or len(incident_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid incident ID")
    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT incident_id, correlation_key, state, severity,
                           root_event_id, opened_at, updated_at, resolved_at
                    FROM titan.incident_states WHERE incident_id = %s
                """, (incident_id,))
                incident = cur.fetchone()
                if incident is None:
                    raise HTTPException(status_code=404, detail="Incident not found")
                # The root reference is retrieved independently; its presence is
                # evidence of a declared link, not of verified causation.
                cur.execute("""
                    SELECT event_id, source, event_type, host, correlation_key,
                           observed_at, received_at
                    FROM titan.events WHERE event_id = %s LIMIT 1
                """, (incident['root_event_id'],))
                root_event = cur.fetchone() if incident['root_event_id'] else None
                # Correlation key equality is association only, never proof.
                cur.execute("""
                    SELECT event_id, source, event_type, host, correlation_key,
                           observed_at, received_at
                    FROM titan.events
                    WHERE correlation_key = %s
                    ORDER BY observed_at DESC NULLS LAST, event_id DESC
                    LIMIT %s
                """, (incident['correlation_key'], limit + 1))
                event_rows = cur.fetchall()
                cur.execute("""
                    SELECT event_id, transition_id, incident_id, topic,
                           partition_id, kafka_offset, received_at
                    FROM titan.transition_inbox WHERE incident_id = %s
                    ORDER BY received_at DESC, event_id DESC LIMIT %s
                """, (incident_id, limit + 1))
                transition_rows = cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="RCA evidence unavailable") from exc

    root_id = incident['root_event_id']
    events = event_rows[:limit]
    transitions = transition_rows[:limit]
    root_found = root_event is not None
    limitations = ["Correlation key equality does not establish causality.",
                   "No independent causal verification is performed."]
    if root_id and not root_found:
        limitations.append("Declared root event was not found in titan.events.")
    if len(event_rows) > limit or len(transition_rows) > limit:
        limitations.append("Related evidence was truncated by the result limit.")
    if not events:
        limitations.append("No events match the incident correlation key.")
    return {
        "incident_id": incident_id,
        "mode": "READ_ONLY",
        "incident": as_json(incident),
        "observed_facts": {
            "declared_root_event_id": root_id,
            "root_event_found": root_found,
            "related_event_count_returned": len(events),
            "transition_count_returned": len(transitions),
        },
        "root_event": as_json(root_event) if root_event else None,
        "related_events": [as_json(row) for row in events],
        "transitions": [as_json(row) for row in transitions],
        "assessment": {
            "classification": "DECLARED_ROOT_EVENT_UNVERIFIED" if root_id else "NO_ROOT_EVENT_DECLARED",
            "confidence": "UNDETERMINED",
            "causality_verified": False,
            "limitations": limitations,
        },
        "limits": {"per_collection": limit,
                   "events_truncated": len(event_rows) > limit,
                   "transitions_truncated": len(transition_rows) > limit},
    }
