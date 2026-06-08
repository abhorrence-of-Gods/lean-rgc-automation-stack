import json
from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.schemas import write_jsonl, read_jsonl


def test_audit_schedule_cli(tmp_path):
    candidates = tmp_path / "candidates.jsonl"
    write_jsonl(candidates, [
        {"action_id": "a", "tactic": "simp", "metadata": {"score": 0.7}},
        {"action_id": "b", "tactic": "rfl", "metadata": {"score": 0.1}},
        {"action_id": "c", "tactic": "omega", "metadata": {"score": 0.4}},
    ])
    out = tmp_path / "scheduled.jsonl"
    rows = tmp_path / "schedule_rows.jsonl"
    rep = tmp_path / "schedule_report.json"
    rc = main([
        "audit-schedule",
        "--candidates", str(candidates),
        "--out", str(out),
        "--out-rows", str(rows),
        "--report-out", str(rep),
        "--top-k", "2",
    ])
    assert rc == 0
    assert out.exists() and rows.exists() and rep.exists()
    scheduled = read_jsonl(out)
    assert len(scheduled) == 2
    assert all((r.get("metadata") or {}).get("active_audit_scheduler") for r in scheduled)


def test_pipeline_active_audit_scheduler(tmp_path):
    out = tmp_path / "pipe"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--audit-scheduler",
        "--audit-db",
    ])
    assert rc == 0
    assert (out / "audit" / "audit_scheduler" / "scheduled_actions.jsonl").exists()
    assert (out / "audit" / "audit_scheduler" / "audit_schedule_report.json").exists()
    assert (out / "audit.db").exists()
