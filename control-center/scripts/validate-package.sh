#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo " TITAN CONTROL CENTER — PACKAGE VALIDATION"
echo "============================================================"

test -f "$ROOT/api/main.py"
test -f "$ROOT/api/database.py"
test -f "$ROOT/frontend/package.json"
test -f "$ROOT/frontend/package-lock.json"
test -f "$ROOT/deploy/.env.example"
test -f "$ROOT/deploy/requirements.txt"
test -f "$ROOT/deploy/vite.portable.config.mjs"

echo "FILES=PASS"

python3 - "$ROOT" <<'PY'
import ast
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])

for source in (root / "api").glob("*.py"):
    ast.parse(source.read_text(encoding="utf-8"))

package = json.loads(
    (root / "frontend/package.json").read_text(encoding="utf-8")
)

lock = json.loads(
    (root / "frontend/package-lock.json").read_text(encoding="utf-8")
)

if package.get("name") != lock.get("name"):
    raise SystemExit("PACKAGE_LOCK_NAME_MISMATCH")

print("PYTHON_SYNTAX=PASS")
print("PACKAGE_JSON=PASS")
PY

if grep -RIlE \
    '(/home/vagrant|/home/ansible|/opt/splunk)' \
    "$ROOT/deploy" \
    --exclude='*.example'; then
    echo "PORTABILITY=FAIL"
    exit 1
fi

echo "PORTABILITY=PASS"
echo "PACKAGE_VALIDATION=PASS"
