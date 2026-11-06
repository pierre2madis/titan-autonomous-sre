#!/usr/bin/env python3
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "simulators/cpu/cpu_scenario_v0_1.sh"
ENRICH = ROOT / "simulators/cpu/cpu_enrich_v0_1.py"
ADAPTER = ROOT / "adapters/cpu_scenario_adapter_v0_2.py"

EXPECTED = [
    ("baseline", 0.8, 1.5),
    ("injection", 8.4, 65.0),
    ("recovery", 1.0, 2.0),
]

with tempfile.TemporaryDirectory(prefix="titan-cpu-portable-") as tmp:
    root = pathlib.Path(tmp)
    scenario = root / "scenario"

    subprocess.run(["bash", str(SCENARIO), str(scenario)], check=True)

    for index, (phase, runq, latency) in enumerate(EXPECTED, 1):
        enriched = root / f"{phase}_enriched.json"
        native = root / f"{phase}_native.json"

        subprocess.run(
            ["python3", str(ENRICH),
             str(scenario / f"{index:02d}_{phase}.json"),
             str(enriched)],
            check=True
        )

        subprocess.run(
            ["python3", str(ADAPTER),
             "--input", str(enriched),
             "--output", str(native)],
            check=True
        )

        data = json.loads(native.read_text())

        assert data["synthetic"] is True
        assert data["simulation_contract"]["decision_ready"] is True
        assert data["simulation_contract"]["real_host_telemetry"] is False
        assert "expected_evidence_state" not in data
        assert data["run_queue"]["p95"] == runq
        assert data["runqlat"]["p99_ms"] == latency

        print(f"{phase.upper()}=PASS")

print("RESULT=LINUX_RELEASE_03G_PORTABLE_TEST_PASS")
