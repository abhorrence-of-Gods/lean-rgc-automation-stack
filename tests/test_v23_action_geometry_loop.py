from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import read_jsonl


def test_pipeline_action_geometry_loop(tmp_path: Path):
    out = tmp_path / "ag_pipeline"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "3",
        "--import-mode", "core",
        "--qgen",
        "--action-geometry",
        "--action-geometry-use-qgen-normals",
        "--audit-action-geometry-candidates",
        "--action-geometry-accept-coker",
    ])
    assert rc == 0
    assert (out / "action_geometry" / "action_geometry.jsonl").exists()
    assert (out / "action_geometry" / "action_geometry_candidates.jsonl").exists()
    assert (out / "action_geometry_audit" / "responses.jsonl").exists()
    assert (out / "action_geometry_acceptance_report.json").exists()
    rows = read_jsonl(out / "action_geometry" / "action_geometry_candidates.jsonl")
    assert rows
    assert any((r.get("metadata") or {}).get("action_geometry") for r in rows)


def test_iterate_action_geometry_merge_raw_candidates(tmp_path: Path):
    out = tmp_path / "ag_iter"
    rc = main([
        "iterate",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--rounds", "1",
        "--max-actions", "3",
        "--import-mode", "core",
        "--qgen",
        "--action-geometry",
        "--action-geometry-use-qgen-normals",
        "--audit-action-geometry-candidates",
        "--action-geometry-accept-coker",
        "--action-geometry-merge-actions",
        "--action-geometry-merge-policy", "all",
    ])
    assert rc == 0
    r0 = out / "round_00"
    assert (r0 / "action_geometry" / "action_geometry_candidates.jsonl").exists()
    assert (r0 / "action_geometry_audit" / "responses.jsonl").exists()
    next_actions = out / "round_00_actions_next.jsonl"
    assert next_actions.exists()
    rows = read_jsonl(next_actions)
    assert rows
