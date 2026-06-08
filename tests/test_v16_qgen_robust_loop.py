from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import read_jsonl


def test_pipeline_qgen_robust_coker_accept(tmp_path: Path):
    out = tmp_path / "run"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "3",
        "--import-mode", "core",
        "--qgen",
        "--qgen-margin-threshold", "-10",
        "--audit-qgen-candidates",
        "--qgen-audit-max-actions", "4",
        "--qgen-accept-coker",
        "--qgen-robust-coker-accept",
        "--qgen-accept-margin", "-1000",
    ])
    assert rc == 0
    assert (out / "qgen_audit" / "responses.jsonl").exists()
    assert (out / "qgen_robust_acceptance_report.json").exists()
    assert (out / "qgen_robust_acceptance_rows.jsonl").exists()
    assert (out / "qgen_robust_accepted_actions.jsonl").exists()
    # Legacy accepted path is also populated so older merge code and reports remain compatible.
    assert (out / "qgen_accepted_actions.jsonl").exists()
    assert isinstance(read_jsonl(out / "qgen_robust_accepted_actions.jsonl"), list)


def test_iterate_merges_qgen_robust_coker_actions(tmp_path: Path):
    out = tmp_path / "iter"
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
        "--qgen-margin-threshold", "-10",
        "--audit-qgen-candidates",
        "--qgen-audit-max-actions", "4",
        "--qgen-accept-coker",
        "--qgen-robust-coker-accept",
        "--qgen-accept-margin", "-1000",
        "--next-action-cap", "16",
    ])
    assert rc == 0
    r0 = out / "round_00"
    assert (r0 / "qgen_robust_accepted_actions.jsonl").exists()
    assert (out / "round_00_actions_next.jsonl").exists()
    # The robust accepted artifact should be one of the merge sources in the summary.
    summary = (out / "iterate_summary.json").read_text(encoding="utf-8")
    assert "qgen_robust_accepted_actions.jsonl" in summary
