import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient
from confluent_kafka._model import ConsumerGroupTopicPartitions

router = APIRouter(prefix="/api/v1/platform")

TARGETS = [
    ("titan-consumer-v1", "titan.events.v1"),
    ("titan-transition-inbox-v3", "titan.incidents.v1"),
]


def collect_worker_health():
    broker = os.environ["TITAN_KAFKA_BROKER"]

    admin = AdminClient({
        "bootstrap.servers": broker,
        "socket.timeout.ms": 3000,
        "allow.auto.create.topics": False,
    })

    # Metadata only: no subscribe, poll, assign or commit.
    probe = Consumer({
        "bootstrap.servers": broker,
        "group.id": "titan-readonly-health-probe",
        "enable.auto.commit": False,
        "allow.auto.create.topics": False,
    })

    groups = []

    try:
        metadata = admin.list_topics(timeout=5)

        listed = admin.list_consumer_groups(
            request_timeout=5
        ).result(timeout=7)

        group_states = {
            group.group_id: group.state.name
            for group in listed.valid
        }

        for group_id, topic in TARGETS:
            topic_info = metadata.topics.get(topic)

            if topic_info is None or topic_info.error:
                groups.append({
                    "group_id": group_id,
                    "topic": topic,
                    "status": "UNKNOWN",
                    "reason": "Topic metadata unavailable",
                    "lag": None,
                    "partitions": [],
                })
                continue

            partitions = sorted(topic_info.partitions)

            request = ConsumerGroupTopicPartitions(
                group_id,
                [
                    TopicPartition(topic, p)
                    for p in partitions
                ],
            )

            result = admin.list_consumer_group_offsets(
                [request],
                request_timeout=5,
            )[group_id].result(timeout=7)

            total_lag = 0
            lag_known = True
            partition_results = []

            for tp in result.topic_partitions:
                if tp.error is not None:
                    lag_known = False
                    partition_results.append({
                        "partition": tp.partition,
                        "error": str(tp.error),
                    })
                    continue

                low, high = probe.get_watermark_offsets(
                    TopicPartition(tp.topic, tp.partition),
                    timeout=5,
                    cached=False,
                )

                committed = tp.offset

                lag = (
                    max(0, high - committed)
                    if committed >= 0
                    else None
                )

                if lag is None:
                    lag_known = False
                else:
                    total_lag += lag

                partition_results.append({
                    "partition": tp.partition,
                    "committed": committed,
                    "low": low,
                    "high": high,
                    "lag": lag,
                })

            lag_value = total_lag if lag_known else None
            group_state = group_states.get(group_id, "UNKNOWN")

            if lag_value is None:
                status = "UNKNOWN"
                reason = "Consumer lag unavailable"
            elif group_state == "STABLE" and lag_value == 0:
                status = "UP"
                reason = "Active group with zero consumer lag"
            elif group_state == "STABLE":
                status = "DEGRADED"
                reason = "Active group with pending messages"
            elif group_state == "EMPTY" and lag_value == 0:
                status = "UNKNOWN"
                reason = "No active members; zero backlog"
            elif group_state == "EMPTY":
                status = "DEGRADED"
                reason = "No active members; messages pending"
            else:
                status = "UNKNOWN"
                reason = "Consumer group state not established"

            groups.append({
                "group_id": group_id,
                "topic": topic,
                "group_state": group_state,
                "status": status,
                "reason": reason,
                "lag": lag_value,
                "partitions": partition_results,
            })

    finally:
        probe.close()

    statuses = [group["status"] for group in groups]

    if "DEGRADED" in statuses:
        overall = "DEGRADED"
    elif "UNKNOWN" in statuses:
        overall = "UNKNOWN"
    elif statuses and all(s == "UP" for s in statuses):
        overall = "UP"
    else:
        overall = "UNKNOWN"

    return {
        "service": "titan-worker-health",
        "status": overall,
        "mode": "READ_ONLY",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "groups": groups,
    }


@router.get("/workers")
def worker_health():
    try:
        return collect_worker_health()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Worker evidence unavailable",
        )
