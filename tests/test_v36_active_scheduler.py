from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.active_scheduler import AuditScheduleConfig, schedule_candidates_from_files
from lean_rgc.cli import main


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_active_scheduler_scores_and_selects(tmp_path: Path):
    cands = tmp_path / "candidates.jsonl"
    _write_jsonl(cands, [
        {"action_id":"low", "tactic":"trivial", "metadata":{"response_embedding":{"goal.eq":0.1}, "source":"base"}, "cost_estimate":1.0},
        {"action_id":"high", "tactic":"simp", "metadata":{"response_embedding":{"goal.eq":0.9}, "source":"qgen", "parent_residual_keys":["goal.eq"]}, "cost_estimate":1.0},
    ])
    out = tmp_path / "scheduled.jsonl"
    report = tmp_path / "report.json"
    scores = tmp_path / "scores.jsonl"
    summary = schedule_candidates_from_files(
        candidates_path=cands,
        out_actions=out,
        out_report=report,
        out_scores=scores,
        response_normal='{"goal.eq":1.0}',
        config=AuditScheduleConfig(top_k=1),
    )
    assert summary["n_selected"] == 1
    row = json.loads(out.read_text().splitlines()[0])
    assert row["action_id"] == "high"
    assert (row["metadata"] or {})["active_audit_scheduler"]["selected"] is True
    assert report.exists() and scores.exists()


def test_active_scheduler_cli(tmp_path: Path):
    cands = tmp_path / "candidates.jsonl"
    _write_jsonl(cands, [
        {"action_id":"a", "tactic":"simp", "metadata":{"response_embedding":{"goal.eq":0.5}}},
        {"action_id":"b", "tactic":"omega", "metadata":{"response_embedding":{"goal.eq":0.2}}},
    ])
    out = tmp_path / "scheduled.jsonl"
    rc = main([
        "audit-schedule",
        "--candidates", str(cands),
        "--out-actions", str(out),
        "--response-normal", '{"goal.eq":1.0}',
        "--top-k", "1",
    ])
    assert rc == 0
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["action_id"] == "a"


def test_pipeline_active_scheduler_dry_run(tmp_path: Path):
    out = tmp_path / "pipe"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--import-mode", "core",
        "--max-actions", "3",
        "--active-audit-scheduler",
        "--audit-scheduler-top-k", "2",
    ])
    assert rc == 0
    assert (out / "audit_schedules" / "audit_scheduled_actions.jsonl").exists()
    assert (out / "audit_schedules" / "audit_schedule_report.json").exists()
