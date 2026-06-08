from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import read_jsonl


def test_iterate_qgen_writes_and_merges_accepted_actions(tmp_path: Path):
    out = tmp_path / "iter"
    rc = main([
        "iterate",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--rounds", "1",
        "--dry-run",
        "--max-actions", "2",
        "--import-mode", "core",
        "--qgen",
        "--qgen-merge-actions",
        "--qgen-margin-threshold", "-10",
        "--next-action-cap", "16",
    ])
    assert rc == 0
    qdir = out / "round_00" / "qgen"
    assert (qdir / "qgen_report.json").exists()
    assert (qdir / "qgen_accepted_actions.jsonl").exists()
    assert (out / "round_00_actions_next.jsonl").exists()
    assert len(read_jsonl(qdir / "qgen_accepted_actions.jsonl")) > 0
    assert len(read_jsonl(out / "round_00_actions_next.jsonl")) > 0
