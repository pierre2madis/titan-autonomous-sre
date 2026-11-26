#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MIN_MEMORY_KIB="${TITAN_BUILD_MIN_MEMORY_KIB:-4194304}"
MIN_DISK_KIB="${TITAN_BUILD_MIN_DISK_KIB:-5242880}"

API_IMAGE="${TITAN_API_IMAGE:-titan-control-center-api:local}"
FRONTEND_IMAGE="${TITAN_FRONTEND_IMAGE:-titan-control-center-frontend:local}"

echo "============================================================"
echo " TITAN CONTROL CENTER — PORTABLE IMAGE BUILD"
echo "============================================================"

echo
echo "=== 1. RESOURCE CHECK ==="

TOTAL_MEMORY_KIB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
AVAILABLE_DISK_KIB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"

echo "MEMORY_TOTAL_KIB=$TOTAL_MEMORY_KIB"
echo "DISK_AVAILABLE_KIB=$AVAILABLE_DISK_KIB"

if (( TOTAL_MEMORY_KIB < MIN_MEMORY_KIB )); then
    echo "BUILD_BLOCKED=INSUFFICIENT_MEMORY"
    exit 1
fi

if (( AVAILABLE_DISK_KIB < MIN_DISK_KIB )); then
    echo "BUILD_BLOCKED=INSUFFICIENT_DISK"
    exit 1
fi

echo "RESOURCE_CHECK=PASS"

echo
echo "=== 2. DOCKER CHECK ==="

docker info >/dev/null
echo "DOCKER_ENGINE=PASS"

echo
echo "=== 3. API IMAGE BUILD ==="

docker build \
    --file "$ROOT/deploy/Dockerfile.api" \
    --tag "$API_IMAGE" \
    "$ROOT"

echo "API_BUILD=PASS"

echo
echo "=== 4. FRONTEND IMAGE BUILD ==="

docker build \
    --file "$ROOT/deploy/Dockerfile.frontend" \
    --tag "$FRONTEND_IMAGE" \
    "$ROOT"

echo "FRONTEND_BUILD=PASS"

echo
echo "=== 5. IMAGE INVENTORY ==="

docker image inspect \
    "$API_IMAGE" \
    "$FRONTEND_IMAGE" \
    --format '{{.RepoTags}} {{.Id}}'

echo
echo "TITAN_IMAGE_BUILD=COMPLETE"
