from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig, audit_with_lean_server
from lean_rgc.schemas import LeanTask, TacticAction
from lean_rgc.cli import main as cli_main


def test_lean_server_adapter_dry_run_apply_tactic(tmp_path: Path):
    task = LeanTask(task_id="t1", statement="1 + 1 = 2", imports=[])
    action = TacticAction(action_id="simp", tactic="norm_num", tactic_class="arith")
    cfg = LeanServerConfig(dry_run=True, workdir=str(tmp_path))
    with LeanServerAdapter(cfg) as server:
        status = server.load_project()
        rec = server.apply_tactic(task, action)
    assert status["backend"] == "dry_run"
    assert rec.audit_flags["lean_server_adapter"] is True
    assert rec.audit_flags["server_backend"] == "dry_run"
    assert rec.status in {"success", "dry_run"}


def test_server_audit_to_files_dry_run(tmp_path: Path):
    tasks = [LeanTask(task_id="t1", statement="1 + 1 = 2", imports=[])]
    actions = [TacticAction(action_id="simp", tactic="norm_num", tactic_class="arith")]
    out = tmp_path / "server_audit"
    summary = audit_with_lean_server(tasks, actions, out_dir=out, server_config=LeanServerConfig(dry_run=True, workdir=str(tmp_path)))
    assert summary["backend"] == "dry_run"
    assert (out / "micro_audit.jsonl").exists()
    assert (out / "responses.jsonl").exists()
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines() if line.strip()]
    assert rows
    assert rows[0]["audit_flags"]["lean_server_adapter"] is True


def test_cli_lean_server_probe_and_pipeline_server_mode(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    actions = tmp_path / "actions.jsonl"
    tasks.write_text(json.dumps({"task_id": "t1", "statement": "1 + 1 = 2", "imports": []}) + "\n", encoding="utf-8")
    actions.write_text(json.dumps({"action_id": "simp", "tactic": "norm_num", "tactic_class": "arith"}) + "\n", encoding="utf-8")
    probe = tmp_path / "probe.json"
    assert cli_main(["lean-server-probe", "--dry-run", "--workdir", str(tmp_path), "--out", str(probe)]) == 0
    rep = json.loads(probe.read_text())
    assert rep["backend"] == "dry_run"

    out = tmp_path / "pipe"
    assert cli_main([
        "pipeline",
        "--tasks", str(tasks),
        "--actions", str(actions),
        "--out", str(out),
        "--dry-run",
        "--audit-mode", "server",
        "--max-actions", "1",
        "--import-mode", "core",
    ]) == 0
    assert (out / "audit" / "server_summary.json").exists()
    summary = json.loads((out / "audit" / "server_summary.json").read_text())
    assert summary["backend"] == "dry_run"
