from __future__ import annotations

from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import read_jsonl


def test_pipeline_quotient_coordinate_loop_and_action_geometry(tmp_path: Path):
    out = tmp_path / "qcoord_pipe"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "3",
        "--import-mode", "core",
        "--quotient-coordinates",
        "--quotient-coordinate-validate",
        "--audit-quotient-coordinate-candidates",
        "--quotient-coordinate-accept-coker",
        "--quotient-coordinate-robust-coker-accept",
        "--action-geometry",
        "--action-geometry-use-quotient-normals",
        "--audit-action-geometry-candidates",
        "--action-geometry-accept-coker",
        "--action-geometry-robust-coker-accept",
    ])
    assert rc == 0
    assert (out / "quotient_coordinates" / "quotient_coordinates.jsonl").exists()
    assert (out / "quotient_coordinates" / "quotient_coordinate_defect_registry.json").exists()
    assert (out / "quotient_coordinates" / "quotient_coordinate_response_normal.json").exists()
    assert (out / "quotient_coordinates" / "quotient_coordinate_validation_report.json").exists()
    assert (out / "quotient_coordinate_audit" / "responses.jsonl").exists()
    assert (out / "quotient_coordinate_robust_accepted_actions.jsonl").exists()
    assert (out / "action_geometry" / "action_geometry_candidates.jsonl").exists()
    assert (out / "action_geometry" / "quotient_coordinate_response_normal_for_action_geometry.json").exists()

