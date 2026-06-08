from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.source_budget_scheduler import source_budget_schedule_from_files
from lean_rgc.cli import main


def test_source_budget_scheduler_allocates_across_sources(tmp_path: Path):
    a = tmp_path / "qgen_candidates.jsonl"
    b = tmp_path / "premise_response_actions.jsonl"
    write_jsonl(a, [
        {"action_id": "q1", "tactic": "simp", "metadata": {"response_embedding": {"goal.eq": 1.0}}},
        {"action_id": "q2", "tactic": "rfl", "metadata": {"response_embedding": {"goal.eq": 0.8}}},
    ])
    write_jsonl(b, [
        {"action_id": "p1", "tactic": "rw [h]", "metadata": {"response_embedding": {"goal.eq": 0.4}, "carrier_embedding": {"missing_simp": 1.0}}},
    ])
    out = tmp_path / "scheduled.jsonl"
    rows = tmp_path / "rows.jsonl"
    report = tmp_path / "report.json"
    rep = source_budget_schedule_from_files(
        candidate_specs=[f"qgen={a}", f"premise@2.0={b}"],
        out_actions=out,
        out_rows=rows,
        out_report=report,
        response_normal={"goal.eq": 1.0},
        carrier_normal={"missing_simp": 0.5},
        config=None,
    )
    selected = read_jsonl(out)
    assert rep["n_sources"] == 2
    assert selected
    assert all("source_budget_scheduler" in (r.get("metadata") or {}) for r in selected)


def test_source_budget_cli_discovers_run_dir(tmp_path: Path):
    qdir = tmp_path / "qgen"
    qdir.mkdir()
    cand = qdir / "qgen_context_candidates.jsonl"
    write_jsonl(cand, [{"action_id": "a", "tactic": "simp", "metadata": {"response_embedding": {"goal.eq": 1.0}}}])
    out = tmp_path / "out.jsonl"
    code = main([
        "source-budget-schedule",
        "--run-dir", str(tmp_path),
        "--out-actions", str(out),
        "--out-report", str(tmp_path / "report.json"),
        "--budget", "1",
    ])
    assert code == 0
    assert len(read_jsonl(out)) == 1


def test_pipeline_source_budget_smoke(tmp_path: Path):
    out = tmp_path / "pipe"
    code = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "3",
        "--qgen",
        "--source-budget",
        "--audit-source-budget-candidates",
        "--source-budget-budget", "2",
        "--import-mode", "core",
    ])
    assert code == 0
    assert (out / "source_budget" / "source_budget_actions.jsonl").exists()
    assert (out / "source_budget" / "source_budget_report.json").exists()
    assert (out / "source_budget_audit" / "responses.jsonl").exists()
