#!/usr/bin/env python3
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

SCENARIO = ROOT / "simulators/cpu/cpu_scenario_v0_1.sh"
ENRICH = ROOT / "simulators/cpu/cpu_enrich_v0_1.py"
ADAPTER = ROOT / "adapters/cpu_scenario_adapter_v0_2.py"

INTEGRATOR = pathlib.Path(
    "/usr/local/bin/cpu_evidence_decision_integrator_v1_0_0.sh"
)
BRIDGE = pathlib.Path(
    "/usr/local/bin/cpu_decision_bridge_v1_0_0_candidate.sh"
)
MODEL = pathlib.Path(
    "/usr/local/bin/cpu_decision_model_v1_0_2_candidate.sh"
)

EXPECTED = [
    ("baseline", "NONE", "NORMAL", False),
    ("injection", "CONFIRMED", "DEGRADED", True),
    ("recovery", "NONE", "NORMAL", False),
]

def run(*args):
    subprocess.run(
        [str(x) for x in args],
        check=True,
        stdout=subprocess.DEVNULL
    )

for path in [INTEGRATOR, BRIDGE, MODEL]:
    assert path.is_file(), f"Missing engine component: {path}"

with tempfile.TemporaryDirectory(prefix="titan-cpu-ci-") as tmp:
    output = pathlib.Path(tmp)
    scenario_dir = output / "scenario"

    run("bash", SCENARIO, scenario_dir)

    for index, (phase, status, severity, incident) in enumerate(
        EXPECTED, 1
    ):
        source = scenario_dir / f"{index:02d}_{phase}.json"
        enriched = output / f"{phase}_enriched.json"
        native = output / f"{phase}_native.json"
        decision = output / f"{phase}_decision.json"

        run("python3", ENRICH, source, enriched)
        run(
            "python3", ADAPTER,
            "--input", enriched,
            "--output", native
        )

        native_data = json.loads(native.read_text())

        assert native_data["synthetic"] is True
        assert native_data["simulation_contract"]["decision_ready"] is True
        assert "expected_evidence_state" not in native_data

        run(
            INTEGRATOR,
            "--input", native,
            "--output", decision,
            "--bridge", BRIDGE,
            "--model", MODEL
        )

        result = json.loads(decision.read_text())
        conclusion = result["operational_conclusion"]

        assert conclusion["problem_status"] == status
        assert conclusion["severity"] == severity
        assert conclusion["incident_recommended"] is incident

        print(
            f"{phase.upper()}: "
            f"status={conclusion['problem_status']} "
            f"severity={conclusion['severity']} "
            f"incident={conclusion['incident_recommended']} "
            "PASS"
        )

print("RESULT=LINUX_RELEASE_03F_DECISION_PIPELINE_PASS")
