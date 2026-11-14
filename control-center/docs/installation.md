# TITAN Control Center — Development Installation

## Prerequisites

- Linux
- Python 3 and virtual environment support
- Node.js and npm compatible with the frontend lockfile
- PostgreSQL
- Redpanda or another Kafka-compatible broker

## Backend

From the control-center directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Configure PostgreSQL and Kafka connection settings.

Store the PostgreSQL password in a protected local file.
Set TITAN_POSTGRES_PASSWORD_FILE to its absolute path.

Do not commit credentials or environment files.

## Database

The file sql/schema.sql is a candidate minimal schema.

Review it against the actual ingestion and incident-processing
components before applying it.

The Control Center is read-only and does not initialize
the event-processing pipeline.

## Start FastAPI

```bash
set -a
source .env
set +a

source .venv/bin/activate

python -m uvicorn api.main:app \
  --host 127.0.0.1 \
  --port 8088 \
  --no-access-log
```

## Start React

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

## Verify

```bash
curl -fsS http://127.0.0.1:8088/api/v1/health
curl -fsS http://127.0.0.1:8088/api/v1/platform/correlation
```

## Operational limitations

- Development deployment only
- No production authentication or RBAC
- No production TLS configuration
- No automatic remediation
- Kafka consumer lag does not prove worker liveness
- Zero backlog does not prove operational readiness
