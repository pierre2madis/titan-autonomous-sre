#!/usr/bin/env python3
import argparse
import fcntl
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "cpu_temporal_correlator_v0_4.py"

parser = argparse.ArgumentParser()
parser.add_argument("--decision", required=True)
parser.add_argument("--state", required=True)
parser.add_argument("--event-id", required=True)
parser.add_argument("--observed-at", required=True)
args = parser.parse_args()

state = Path(args.state)
state.parent.mkdir(parents=True, exist_ok=True)

lock_path = Path(str(state) + ".lock")

fd = os.open(
    str(lock_path),
    os.O_CREAT | os.O_RDWR,
    0o600
)

try:
    fcntl.flock(fd, fcntl.LOCK_EX)

    command = [
        sys.executable,
        str(ENGINE),
        "--decision", args.decision,
        "--state", str(state),
        "--event-id", args.event_id,
        "--observed-at", args.observed_at
    ]

    result = subprocess.run(command, check=False)

    sys.exit(result.returncode)

finally:
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
