import json
from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import write_jsonl, read_jsonl


def test_source_budget_schedule_cli(tmp_path):
    qgen = tmp_path / "qgen.jsonl"
    prem = tmp_path / "premise.jsonl"
    write_jsonl(qgen, [
        {"action_id": "q1", "tactic": "simp", "metadata": {"score": 1.0, "source": "qgen"}, "response_embedding": {"goal.eq": 1.0}},
        {"action_id": "q2", "tactic": "rfl", "metadata": {"score": 0.2, "source": "qgen"}, "response_embedding": {"goal.eq": 0.2}},
    ])
    write_jsonl(prem, [
        {"action_id": "p1", "tactic": "omega", "metadata": {"score": 0.7, "source": "premise"}, "response_embedding": {"goal.eq": 0.7}},
        {"action_id": "p2", "tactic": "constructor", "metadata": {"score": 0.1, "source": "premise"}, "response_embedding": {"goal.eq": 0.1}},
    ])
    out = tmp_path / "scheduled.jsonl"
    rows = tmp_path / "rows.jsonl"
    report = tmp_path / "report.json"
    rc = main([
        "source-budget-schedule",
        "--source", f"qgen@min:1={qgen}",
        "--source", f"premise@min:1={prem}",
        "--out-actions", str(out),
        "--out-rows", str(rows),
        "--out-report", str(report),
        "--budget", "3",
        "--min-per-source", "1",
    ])
    assert rc == 0
    assert out.exists() and rows.exists() and report.exists()
    selected = read_jsonl(out)
    assert len(selected) == 3
    by_src = {}
    for r in selected:
        src = (r.get("metadata") or {}).get("source_budget_source") or r.get("source_budget_source")
        by_src[src] = by_src.get(src, 0) + 1
    assert by_src.get("qgen", 0) >= 1
    assert by_src.get("premise", 0) >= 1
    rep = json.loads(report.read_text())
    assert rep["n_sources"] == 2
    assert rep["n_selected"] == 3


def test_pipeline_source_budget_scheduler(tmp_path):
    out = tmp_path / "pipe"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--qgen",
        "--qgen-registry-candidates",
        "--action-geometry",
        "--action-geometry-retrieve",
        "--source-budget",
        "--audit-source-budget-candidates",
        "--source-budget-budget", "4",
        "--source-budget-min-per-source", "1",
    ])
    assert rc == 0
    assert (out / "source_budget" / "source_budget_actions.jsonl").exists()
    assert (out / "source_budget" / "source_budget_report.json").exists()
    assert (out / "source_budget_audit" / "responses.jsonl").exists()
    pipe_report = json.loads((out / "pipeline_report.json").read_text())
    assert pipe_report["pipeline_files"].get("source_budget_report")
