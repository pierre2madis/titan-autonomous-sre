#!/usr/bin/env python3
import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/cpu_temporal_correlator_v0_4.py"
SOURCE = pathlib.Path("/tmp/titan-cpu-demo.LCDCSNSg")

def run(phase, event_id, observed_at, state):
    return subprocess.run(
        [
            sys.executable, str(ENGINE),
            "--decision", str(SOURCE / f"{phase}_decision.json"),
            "--state", str(state),
            "--event-id", event_id,
            "--observed-at", observed_at
        ],
        capture_output=True,
        text=True
    )

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix="titan-05g2-") as tmp:
    state = pathlib.Path(tmp) / "state.json"

    first = run(
        "injection", "E100",
        "2026-10-30T10:05:00Z", state
    )
    assert first.returncode == 0, first.stderr
    assert "action=CREATE" in first.stdout

    before = digest(state)

    replay = run(
        "injection", "E100",
        "2026-10-30T10:05:00Z", state
    )
    assert replay.returncode == 0, replay.stderr
    assert "action=IGNORE_REPLAY" in replay.stdout
    assert digest(state) == before
    print("RESULT=TEMPORAL_REPLAY_PASS")

    equal = run(
        "injection", "E101",
        "2026-10-30T10:05:00Z", state
    )
    assert equal.returncode != 0
    assert "ERROR=AMBIGUOUS_TIMESTAMP" in equal.stderr
    assert digest(state) == before
    print("RESULT=AMBIGUOUS_TIMESTAMP_REJECTED_PASS")

    invalid = run(
        "recovery", "E102",
        "2026-10-30T10:06:00", state
    )
    assert invalid.returncode != 0
    assert "ERROR=INVALID_OBSERVED_AT" in invalid.stderr
    assert digest(state) == before
    print("RESULT=TIMEZONE_REQUIRED_PASS")

    stale = run(
        "recovery", "E103",
        "2026-10-30T10:02:00Z", state
    )
    assert stale.returncode == 0, stale.stderr
    assert "action=IGNORE_STALE" in stale.stdout
    assert digest(state) == before
    print("RESULT=STALE_STATE_IMMUTABILITY_PASS")

print("RESULT=LINUX_RELEASE_05G_TEMPORAL_INTEGRITY_PASS")
