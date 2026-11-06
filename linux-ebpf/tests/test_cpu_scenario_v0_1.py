#!/usr/bin/env python3
import json
import pathlib
import subprocess
import tempfile
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "simulators/cpu/cpu_scenario_v0_1.sh"

EXPECTED = [
    ("BASELINE", "NORMAL", 0),
    ("INJECTION", "DEGRADED", 1),
    ("RECOVERY", "NORMAL", 0),
]

with tempfile.TemporaryDirectory(prefix="titan-cpu-test-") as tmp:
    output = pathlib.Path(tmp) / "replay"

    subprocess.run(
        ["bash", str(SCRIPT), str(output)],
        check=True,
    )

    manifest = json.loads(
        (output / "manifest.json").read_text()
    )

    assert manifest["scenario_id"] == "CPU-02"
    assert manifest["synthetic"] is True
    assert manifest["phases"] == [x[0] for x in EXPECTED]

    timestamps = []

    for index, (phase, state, contention) in enumerate(EXPECTED, 1):
        path = output / f"{index:02d}_{phase.lower()}.json"
        event = json.loads(path.read_text())

        assert event["scenario_id"] == "CPU-02"
        assert event["synthetic"] is True
        assert event["phase"] == phase
        assert event["expected_evidence_state"] == state
        assert event["metrics"]["scheduler_contention"] == contention
        assert event["root_cause"] == "UNVERIFIED"
        assert event["service_impact"] == "NOT_MEASURED"

        timestamps.append(
            datetime.fromisoformat(
                event["observed_at"].replace("Z", "+00:00")
            )
        )

    assert timestamps[0] < timestamps[1] < timestamps[2]
    assert (timestamps[1] - timestamps[0]).total_seconds() == 30
    assert (timestamps[2] - timestamps[1]).total_seconds() == 30

print("scenario=CPU-02")
print("synthetic_contract=PASS")
print("phase_sequence=PASS")
print("timeline=PASS")
print("expected_recovery=PASS")
print("RESULT=LINUX_RELEASE_02B_TEST_PASS")
