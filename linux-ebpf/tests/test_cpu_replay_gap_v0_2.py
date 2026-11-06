#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENGINE = ROOT / "correlators/cpu_persistent_correlator_v0_2.py"
SOURCE = pathlib.Path("/tmp/titan-cpu-demo.LCDCSNSg")
DECISION = SOURCE / "injection_decision.json"

if not DECISION.is_file():
    raise SystemExit("ERROR=MISSING_INJECTION_DECISION")

with tempfile.TemporaryDirectory(prefix="titan-05f-") as tmp:
    state = pathlib.Path(tmp) / "state.json"

    for attempt in (1, 2):
        result = subprocess.run(
            [
                sys.executable,
                str(ENGINE),
                "--decision", str(DECISION),
                "--state", str(state)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise SystemExit(result.stderr)

        current = json.loads(state.read_text())
        count = current["incident"]["observation_count"]

        print(f"attempt={attempt} observation_count={count}")

    if count == 2:
        print("RESULT=REPLAY_GAP_CONFIRMED")
    else:
        raise SystemExit("ERROR=UNEXPECTED_REPLAY_BEHAVIOR")
