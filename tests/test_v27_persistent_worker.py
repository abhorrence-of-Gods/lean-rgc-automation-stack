from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig
from lean_rgc.schemas import LeanTask, TacticAction
from lean_rgc.cli import main as cli_main


def test_persistent_adapter_state_branch_rollback_dry_run():
    task = LeanTask(task_id="p1", statement="∀ n : Nat, n = n", imports=["Init"])
    intro = TacticAction(action_id="intro_n", tactic="intro n", tactic_class="intro")
    rfl = TacticAction(action_id="rfl", tactic="rfl", tactic_class="rfl")
    cfg = LeanServerConfig(backend="persistent", dry_run=True, fallback_to_file=False, startup_timeout_s=5.0)
    with LeanServerAdapter(cfg) as server:
        base = server.register_task(task)["state"]
        rec1 = server.apply_tactic_to_state_id(task, intro, base["state_id"])
        assert rec1.audit_flags.get("stateful_apply") is True
        assert rec1.after_state is not None
        branch = server.branch_state(rec1.after_state.state_id)
        assert branch.get("branch_of") == rec1.after_state.state_id or branch.get("metadata", {}).get("branched_from") == rec1.after_state.state_id or branch.get("parent_state_id") == rec1.after_state.state_id
        rec2 = server.apply_tactic_to_state_id(task, rfl, branch["state_id"])
        assert rec2.after_state is not None
        rolled = server.rollback_state(rec2.after_state.state_id, steps=1)
        assert rolled["state_id"] == branch["state_id"]


def test_persistent_worker_jsonl_protocol_module(tmp_path: Path):
    reqs = [
        {"id": "load", "cmd": "load_project"},
        {"id": "init", "cmd": "init_state", "task": {"task_id": "p2", "statement": "True", "imports": ["Init"]}},
        {"id": "shutdown", "cmd": "shutdown"},
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "lean_rgc.persistent_lean_worker", "--backend", "dry_run"],
        input="\n".join(json.dumps(r) for r in reqs) + "\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert rows[0]["ok"] is True
    assert rows[1]["ok"] is True
    assert rows[1]["state"]["state_id"]


def test_cli_lean_persistent_probe(tmp_path: Path):
    out = tmp_path / "persistent_probe.json"
    rc = cli_main(["lean-persistent-probe", "--dry-run", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["n_states"] >= 2
    assert data["canonical_status"] == "persistent_worker_probe_chart_only_not_kernel_canonical"


def test_pipeline_server_mode_persistent_backend(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    actions = tmp_path / "actions.jsonl"
    tasks.write_text(json.dumps({"task_id": "p3", "statement": "True", "imports": ["Init"]}) + "\n")
    actions.write_text(json.dumps({"action_id": "trivial", "tactic": "trivial", "tactic_class": "trivial"}) + "\n")
    out = tmp_path / "pipe"
    rc = cli_main([
        "pipeline",
        "--tasks", str(tasks),
        "--actions", str(actions),
        "--out", str(out),
        "--dry-run",
        "--audit-mode", "server",
        "--server-backend", "persistent",
        "--max-actions", "2",
    ])
    assert rc == 0
    server_summary = json.loads((out / "audit" / "server_summary.json").read_text())
    assert server_summary["backend"] == "jsonl"
    rows = [json.loads(line) for line in (out / "audit" / "micro_audit.jsonl").read_text().splitlines() if line.strip()]
    assert rows and rows[0]["audit_flags"].get("persistent_lean_worker") is True
