#!/usr/bin/env bash
set -Eeuo pipefail

required=(
  TITAN_TEST_API_IMAGE
  TITAN_TEST_FRONTEND_IMAGE
  TITAN_TEST_HTTP_IMAGE
  TITAN_TEST_PORT
  TITAN_TEST_TIMEOUT_SECONDS
  TITAN_TEST_POLL_SECONDS
  TITAN_TEST_POSTGRES_HOST
  TITAN_TEST_POSTGRES_PORT
  TITAN_TEST_POSTGRES_DB
  TITAN_TEST_POSTGRES_USER
)

for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]] || {
    echo "ERROR: missing $name" >&2
    exit 1
  }
done

for name in TITAN_TEST_PORT TITAN_TEST_TIMEOUT_SECONDS \
            TITAN_TEST_POLL_SECONDS TITAN_TEST_POSTGRES_PORT; do
  [[ "${!name}" =~ ^[1-9][0-9]*$ ]] || {
    echo "ERROR: invalid $name" >&2
    exit 1
  }
done

RUN_SUFFIX="${GITHUB_RUN_ID:-$$}-${GITHUB_RUN_ATTEMPT:-1}"
PREFIX="titan-smoke-${RUN_SUFFIX}"
NETWORK="${PREFIX}-network"
API="${PREFIX}-api"
FRONTEND="${PREFIX}-frontend"

SECRET_DIR="$(mktemp -d)"
SECRET_FILE="$SECRET_DIR/postgres_password"
printf '%s\n' "ci-placeholder-not-a-real-password" > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"

cleanup() {
  local rc=$?

  if (( rc != 0 )); then
    echo "=== FAILURE LOGS ==="
    docker logs "$API" 2>&1 || true
    docker logs "$FRONTEND" 2>&1 || true
  fi

  docker rm -f "$FRONTEND" "$API" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf -- "$SECRET_DIR"
}

trap cleanup EXIT

docker network create "$NETWORK" >/dev/null

docker run -d \
  --name "$API" \
  --network "$NETWORK" \
  --network-alias api \
  --network-alias titan-api \
  --mount "type=bind,src=$SECRET_FILE,dst=/run/secrets/titan_postgres_password,readonly" \
  -e TITAN_POSTGRES_PASSWORD_FILE=/run/secrets/titan_postgres_password \
  -e TITAN_POSTGRES_HOST="$TITAN_TEST_POSTGRES_HOST" \
  -e TITAN_POSTGRES_PORT="$TITAN_TEST_POSTGRES_PORT" \
  -e TITAN_POSTGRES_DB="$TITAN_TEST_POSTGRES_DB" \
  -e TITAN_POSTGRES_USER="$TITAN_TEST_POSTGRES_USER" \
  -e TITAN_KAFKA_BROKER= \
  "$TITAN_TEST_API_IMAGE" >/dev/null

docker run -d \
  --name "$FRONTEND" \
  --network "$NETWORK" \
  --network-alias titan-frontend \
  "$TITAN_TEST_FRONTEND_IMAGE" >/dev/null

http_code() {
  local target="$1"
  local path="$2"

  docker run --rm \
    --network "$NETWORK" \
    "$TITAN_TEST_HTTP_IMAGE" \
    -sS -o /dev/null -w '%{http_code}' \
    --max-time 3 \
    "http://${target}:${TITAN_TEST_PORT}${path}"
}

wait_for_status() {
  local target="$1"
  local path="$2"
  local expected="$3"
  local actual=""
  local deadline=$((SECONDS + TITAN_TEST_TIMEOUT_SECONDS))

  while (( SECONDS < deadline )); do
    actual="$(http_code "$target" "$path" 2>/dev/null || true)"

    if [[ "$actual" == "$expected" ]]; then
      return 0
    fi

    if [[ "$(docker inspect -f '{{.State.Running}}' "$API")" != "true" ]]; then
      echo "FAIL: API container stopped" >&2
      return 1
    fi

    sleep "$TITAN_TEST_POLL_SECONDS"
  done

  echo "FAIL: $target$path expected=$expected actual=$actual" >&2
  return 1
}

echo "=== API READINESS ==="
wait_for_status titan-api /api/v1/health 503
echo "API_HTTP_503_EXPECTED=PASS"

echo "=== FRONTEND READINESS ==="
wait_for_status titan-frontend / 200
echo "FRONTEND_HTTP_200=PASS"

frontend_html="$(
  docker run --rm \
    --network "$NETWORK" \
    "$TITAN_TEST_HTTP_IMAGE" \
    -fsS --max-time 3 \
    "http://titan-frontend:${TITAN_TEST_PORT}/"
)"

grep -Eiq '<!doctype html|<html' <<< "$frontend_html"
echo "FRONTEND_HTML=PASS"

[[ "$(docker inspect -f '{{.State.Running}}' "$FRONTEND")" == "true" ]]
echo "FRONTEND_CONTAINER_RUNNING=PASS"

echo "=== REVERSE PROXY ==="
wait_for_status titan-frontend /api/v1/health 503
echo "API_PROXY_HTTP_503_EXPECTED=PASS"

echo "=== RESPONSE VALIDATION ==="
response="$(
  docker run --rm \
    --network "$NETWORK" \
    "$TITAN_TEST_HTTP_IMAGE" \
    -sS --max-time 3 \
    "http://titan-frontend:${TITAN_TEST_PORT}/api/v1/health"
)"

grep -Fq '"detail":"Database unavailable"' <<< "$response"
echo "DATABASE_UNAVAILABLE_RESPONSE=PASS"

[[ "$(docker inspect -f '{{.State.Running}}' "$API")" == "true" ]]
[[ "$(docker inspect -f '{{.State.Running}}' "$FRONTEND")" == "true" ]]
echo "CONTAINERS_RUNNING=PASS"

echo "TITAN_RUNTIME_SMOKE_TEST=PASS"
