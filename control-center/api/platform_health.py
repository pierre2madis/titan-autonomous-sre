from api.core_pipeline import collect_pipeline_evidence
import os
from datetime import datetime, timezone

from confluent_kafka.admin import AdminClient
from fastapi import APIRouter

from api.database import database_connection

router = APIRouter(prefix="/api/v1/platform")


def now():
    return datetime.now(timezone.utc).isoformat()


def component(name, status, check, reason):
    return {
        "name": name,
        "status": status,
        "check": check,
        "reason": reason,
        "checked_at": now(),
    }


@router.get("/health")
def platform_health():
    components = []

    components.append(
        component(
            "FastAPI",
            "UP",
            "HTTP_REQUEST",
            "Platform health endpoint responding",
        )
    )

    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        components.append(
            component(
                "PostgreSQL",
                "UP",
                "SQL_SELECT_1",
                "Read-only database query succeeded",
            )
        )
    except Exception:
        components.append(
            component(
                "PostgreSQL",
                "DOWN",
                "SQL_SELECT_1",
                "Database query failed",
            )
        )

    broker = os.getenv(
        "TITAN_KAFKA_BROKER", ""
    ).strip()

    if not broker:
        components.append(
            component(
                "Redpanda",
                "UNKNOWN",
                "KAFKA_METADATA",
                "Broker configuration unavailable",
            )
        )
    else:
        try:
            client = AdminClient({
                "bootstrap.servers": broker,
                "socket.timeout.ms": 3000,
                "request.timeout.ms": 3000,
            })

            metadata = client.list_topics(timeout=3)

            if metadata.brokers:
                components.append(
                    component(
                        "Redpanda",
                        "UP",
                        "KAFKA_METADATA",
                        "Broker metadata available",
                    )
                )
            else:
                components.append(
                    component(
                        "Redpanda",
                        "DEGRADED",
                        "KAFKA_METADATA",
                        "No brokers returned in metadata",
                    )
                )

        except Exception:
            components.append(
                component(
                    "Redpanda",
                    "DOWN",
                    "KAFKA_METADATA",
                    "Kafka metadata request failed",
                )
            )

    try:
        evidence = collect_pipeline_evidence()

        components.append(
            component(
                "Core Pipeline",
                evidence["status"],
                "POSTGRES_PIPELINE_EVIDENCE",
                evidence["reason"],
            )
        )
    except Exception:
        components.append(
            component(
                "Core Pipeline",
                "UNKNOWN",
                "POSTGRES_PIPELINE_EVIDENCE",
                "Pipeline evidence query unavailable",
            )
        )

    statuses = [item["status"] for item in components]

    if "DOWN" in statuses:
        overall = "DEGRADED"
    elif "DEGRADED" in statuses:
        overall = "DEGRADED"
    elif "UNKNOWN" in statuses:
        overall = "UNKNOWN"
    else:
        overall = "UP"

    return {
        "service": "titan-control-center",
        "status": overall,
        "mode": "READ_ONLY",
        "checked_at": now(),
        "components": components,
    }
