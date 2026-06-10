import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import read_jsonl, write_jsonl


MOVED_COMMANDS = {
    "lean-server-health": ["lean-server-health", "--dry-run"],
    "lean-server-apply": ["lean-server-apply", "--task-json", "task.json", "--action-json", "action.json", "--dry-run"],
    "lean-server-probe": ["lean-server-probe", "--dry-run"],
    "lean-server-audit": ["lean-server-audit", "--tasks", "tasks.jsonl", "--out", "audit", "--dry-run"],
    "lean-worker": ["lean-worker", "--dry-run"],
    "lean-persistent-worker": ["lean-persistent-worker", "--dry-run"],
    "lean-persistent-probe": ["lean-persistent-probe", "--dry-run"],
    "persistent-worker": ["persistent-worker"],
    "persistent-state-demo": ["persistent-state-demo", "--task-json", "task.json", "--actions", "actions.jsonl", "--out", "demo.json", "--dry-run"],
    "lean-native-worker": ["lean-native-worker", "--print-command"],
    "native-lean-worker": ["native-lean-worker", "--print-command"],
    "frontier-audit": ["frontier-audit", "--tasks", "tasks.jsonl", "--out", "frontier", "--dry-run"],
    "structured-state-extract": ["structured-state-extract", "--tasks", "tasks.jsonl", "--out", "structured.jsonl"],
    "goal-state-transitions": ["goal-state-transitions", "--audits", "audits.jsonl", "--out", "transitions.jsonl"],
    "kernel-state-graphs": ["kernel-state-graphs", "--kernel-jsonl", "kernel.jsonl", "--out", "graphs.jsonl"],
    "kernel-state-normalize": ["kernel-state-normalize", "--kernel-jsonl", "kernel.jsonl", "--out", "normalized.jsonl"],
    "kernel-state-probe": ["kernel-state-probe", "--task-json", "task.json", "--action-json", "action.json"],
}


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def _write_task_action(tmp_path: Path) -> tuple[Path, Path, Path]:
    task = tmp_path / "task.json"
    action = tmp_path / "action.json"
    tasks = tmp_path / "tasks.jsonl"
    task_row = {"task_id": "t_refl", "statement": "theorem t_refl : True := by trivial", "imports": ["Init"]}
    action_row = {"action_id": "trivial", "tactic": "trivial", "tactic_class": "trivial"}
    task.write_text(json.dumps(task_row), encoding="utf-8")
    action.write_text(json.dumps(action_row), encoding="utf-8")
    write_jsonl(tasks, [task_row])
    return task, action, tasks


def test_lean_cli_modules_import_without_root_cli():
    code = """
import importlib
import sys
importlib.import_module('lean_rgc.lean')
importlib.import_module('lean_rgc.cli_lean')
assert 'lean_rgc.cli.main' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_lean_facade_reexports_runtime_apis():
    lean = importlib.import_module("lean_rgc.lean")
    checks = [
        ("LeanServerAdapter", "lean_rgc.lean_server"),
        ("LeanServerConfig", "lean_rgc.lean_server"),
        ("audit_with_lean_server", "lean_rgc.lean_server"),
        ("adapter_from_executor_args", "lean_rgc.lean_server"),
        ("PersistentLeanWorker", "lean_rgc.persistent_worker"),
        ("WorkerConfig", "lean_rgc.persistent_worker"),
        ("run_persistent_worker", "lean_rgc.persistent_worker"),
        ("install_native_worker", "lean_rgc.native_worker"),
        ("native_worker_manifest", "lean_rgc.native_worker"),
        ("KernelGoalStateServer", "lean_rgc.kernel_state"),
        ("KernelGoalStateServerConfig", "lean_rgc.kernel_state"),
        ("normalize_kernel_state_v1", "lean_rgc.kernel_state"),
        ("kernel_state_graphs_from_jsonl", "lean_rgc.goal_state_dynamics"),
        ("goal_state_transitions_from_audits", "lean_rgc.goal_state_dynamics"),
        ("structured_state_extract_cli", "lean_rgc.structured_state"),
        ("FrontierAuditor", "lean_rgc.frontier"),
    ]
    for attr, module_name in checks:
        assert getattr(lean, attr) is getattr(importlib.import_module(module_name), attr)


def test_lean_runtime_commands_live_in_cli_lean():
    from lean_rgc.cli import build_parser

    parser = build_parser()
    choices = _command_choices(parser)
    assert set(MOVED_COMMANDS) <= set(choices)
    for argv in MOVED_COMMANDS.values():
        ns = parser.parse_args(argv)
        assert ns.func.__module__ == "lean_rgc.cli.lean"


def test_lean_runtime_split_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    for rel in ["lean_rgc/cli_lean.py", "lean_rgc/lean/__init__.py", "lean_rgc/proof_ir.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "from ..cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_lean_server_health_and_apply_smoke(tmp_path: Path):
    task, action, _tasks = _write_task_action(tmp_path)
    health = tmp_path / "health.json"
    apply_out = tmp_path / "apply.json"
    assert cli_main(["lean-server-health", "--dry-run", "--out", str(health)]) == 0
    assert health.exists()
    assert cli_main(["lean-server-apply", "--task-json", str(task), "--action-json", str(action), "--dry-run", "--out", str(apply_out)]) == 0
    assert apply_out.exists()


def test_kernel_and_structured_state_smoke(tmp_path: Path):
    task, action, tasks = _write_task_action(tmp_path)
    probe = tmp_path / "kernel_probe.json"
    structured = tmp_path / "structured.jsonl"
    assert cli_main(["kernel-state-probe", "--task-json", str(task), "--action-json", str(action), "--out", str(probe)]) == 0
    assert probe.exists()
    assert cli_main(["structured-state-extract", "--tasks", str(tasks), "--out", str(structured)]) == 0
    assert read_jsonl(structured)


def test_frontier_audit_smoke(tmp_path: Path):
    _task, _action, tasks = _write_task_action(tmp_path)
    out = tmp_path / "frontier"
    assert cli_main(["frontier-audit", "--tasks", str(tasks), "--out", str(out), "--dry-run"]) == 0
    assert out.exists()
