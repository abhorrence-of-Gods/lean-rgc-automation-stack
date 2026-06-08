import json
from pathlib import Path

from lean_rgc.carrier_quotient import carrier_quotient_from_files, compute_carrier_state_coker_normals
from lean_rgc.cli import main as cli_main


def _write_rows(path: Path):
    rows = [
        {
            "state_id": "s1",
            "action_id": "simp_good",
            "tactic": "simp",
            "response": {"goal.eq": 0.1},
            "response_flat": [0.1],
            "response_keys": ["goal.eq"],
            "carrier_delta": {"simp_carrier": 0.75, "arith_carrier": 0.05},
            "defect_before": {"carrier": {"simp_carrier": 1.0, "arith_carrier": 0.2}, "flat": [0.1], "flat_keys": ["goal.eq"]},
            "defect_after": {"carrier": {"simp_carrier": 0.25, "arith_carrier": 0.15}},
            "audit_status": "success",
        },
        {
            "state_id": "s1",
            "action_id": "unsafe",
            "tactic": "skip",
            "response": {"goal.eq": 0.0},
            "response_flat": [0.0],
            "response_keys": ["goal.eq"],
            "carrier_delta": {"simp_carrier": -0.2, "arith_carrier": 0.0},
            "defect_before": {"carrier": {"simp_carrier": 1.0, "arith_carrier": 0.2}, "flat": [0.1], "flat_keys": ["goal.eq"]},
            "defect_after": {"carrier": {"simp_carrier": 1.2, "arith_carrier": 0.2}},
            "audit_status": "fail",
        },
        {
            "state_id": "s2",
            "action_id": "omega_good",
            "tactic": "omega",
            "response": {"goal.arith": 0.3},
            "response_flat": [0.3],
            "response_keys": ["goal.arith"],
            "carrier_delta": {"simp_carrier": 0.0, "arith_carrier": 0.8},
            "defect_before": {"carrier": {"simp_carrier": 0.0, "arith_carrier": 1.0}, "flat": [0.3], "flat_keys": ["goal.arith"]},
            "defect_after": {"carrier": {"arith_carrier": 0.2}},
            "audit_status": "success",
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_carrier_quotient_from_files(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    _write_rows(responses)
    normals, summary = compute_carrier_state_coker_normals(responses)
    assert summary["n_state_normals"] >= 1
    out = tmp_path / "carrier_quotient"
    rep = carrier_quotient_from_files(responses, out_dir=out, validate=True)
    assert rep["coordinate_summary"]["n_coordinates"] >= 1
    assert (out / "carrier_quotient_coordinates.jsonl").exists()
    assert (out / "carrier_quotient_candidates.jsonl").exists()
    assert (out / "carrier_quotient_defect_registry.json").exists()
    assert (out / "carrier_quotient_incidence_patches.jsonl").exists()
    coords = [json.loads(x) for x in (out / "carrier_quotient_coordinates.jsonl").read_text().splitlines()]
    assert any(c["top_loadings"] for c in coords)


def test_carrier_quotient_cli_and_pipeline(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    _write_rows(responses)
    out = tmp_path / "cq"
    assert cli_main(["carrier-quotient", "--responses", str(responses), "--out", str(out), "--validate"]) == 0
    assert (out / "carrier_quotient_validation_report.json").exists()

    run = tmp_path / "pipe"
    assert cli_main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(run),
        "--dry-run",
        "--max-actions", "3",
        "--carrier-quotient",
        "--carrier-quotient-validate",
    ]) == 0
    assert (run / "carrier_quotient" / "carrier_quotient_report.json").exists()
