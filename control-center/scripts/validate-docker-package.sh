#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo " TITAN CONTROL CENTER — DOCKER PACKAGE VALIDATION"
echo "============================================================"

for file in \
    "$ROOT/deploy/Dockerfile.api" \
    "$ROOT/deploy/Dockerfile.frontend" \
    "$ROOT/deploy/compose.yaml" \
    "$ROOT/deploy/nginx.conf.template"; do
    test -s "$file"
done

echo "DOCKER_FILES=PASS"

if command -v docker >/dev/null 2>&1; then
    echo "DOCKER_CLI=AVAILABLE"
else
    echo "DOCKER_CLI=UNAVAILABLE"
fi

echo "DOCKER_PACKAGE_STATIC_VALIDATION=PASS"
