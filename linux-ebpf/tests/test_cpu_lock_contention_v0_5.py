#!/usr/bin/env python3
import fcntl
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/cpu_locked_correlator_v0_5.py"
DECISION = pathlib.Path(
    "/tmp/titan-cpu-demo.LCDCSNSg/injection_decision.json"
)

if not DECISION.is_file():
    raise SystemExit("ERROR=MISSING_DECISION")

with tempfile.TemporaryDirectory(prefix="titan-05h2-") as tmp:
    state = pathlib.Path(tmp) / "state.json"
    lock = pathlib.Path(str(state) + ".lock")

    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o600)

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        print("RESULT=LOCK_HOLDER_ACQUIRED", flush=True)

        command = [
            sys.executable, str(ENGINE),
            "--decision", str(DECISION),
            "--state", str(state),
            "--event-id", "E202",
            "--observed-at", "2026-10-30T10:08:00Z"
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(2)

        if process.poll() is not None:
            raise AssertionError(
                "Correlator exited while lock was held"
            )

        if state.exists():
            raise AssertionError(
                "State was written before lock release"
            )

        print("RESULT=LOCK_CONTENTION_CONFIRMED", flush=True)

    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    stdout, stderr = process.communicate(timeout=15)

    if process.returncode != 0:
        raise AssertionError(stderr)

    data = json.loads(state.read_text())
    incident = data["incident"]

    assert incident["active"] is True
    assert incident["occurrence"] == 1
    assert incident["observation_count"] == 1
    assert "E202" in data["processed_events"]
    assert "action=CREATE" in stdout

    print("RESULT=LOCK_RELEASE_PROCESSING_PASS")
    print("RESULT=LINUX_RELEASE_05H_DETERMINISTIC_LOCK_PASS")
