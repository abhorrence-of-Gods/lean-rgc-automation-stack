from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.audit_job_queue import enqueue_audit_jobs, project_fingerprint
from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import LeanTask, TacticAction


ROOT = Path(__file__).resolve().parents[1]


def test_frontier_and_supervisor_implementations_live_under_lean_package():
    checks = {
        "frontier": [
            "FrontierRecord",
            "FrontierAuditor",
            "build_frontiers",
            "exposure_actions_for_task",
            "expose_frontier_files",
        ],
        "worker_supervisor": [
            "SCHEMA_LEAN_WORKER_SUPERVISOR",
            "enqueue_and_run_supervised_audit",
            "run_bulk_audit_queue",
            "run_supervised_audit_queue",
        ],
    }
    compat_names = {
        "frontier": "lean_rgc.frontier",
        "worker_supervisor": "lean_rgc.lean_worker_supervisor",
    }

    for module_name, attrs in checks.items():
        canonical = importlib.import_module(f"lean_rgc.lean.{module_name}")
        compat = importlib.import_module(compat_names[module_name])

        assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / f"{module_name}.py"
        assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / (
            "frontier.py" if module_name == "frontier" else "lean_worker_supervisor.py"
        )
        for attr in attrs:
            assert getattr(compat, attr) is getattr(canonical, attr)


def test_top_level_orchestration_modules_are_shims():
    expected = {
        "frontier.py": "from .lean.frontier import *",
        "lean_worker_supervisor.py": "from .lean.worker_supervisor import *",
    }
    forbidden = {
        "frontier.py": ["class FrontierRecord", "def build_frontiers"],
        "lean_worker_supervisor.py": ["def run_supervised_audit_queue", "class _WorkerResult"],
    }
    for filename, needle in expected.items():
        text = (ROOT / "lean_rgc" / filename).read_text(encoding="utf-8")
        assert needle in text
        for blocked in forbidden[filename]:
            assert blocked not in text


def test_orchestration_canonical_modules_use_canonical_runtime_imports():
    frontier_text = (ROOT / "lean_rgc" / "lean" / "frontier.py").read_text(encoding="utf-8")
    supervisor_text = (ROOT / "lean_rgc" / "lean" / "worker_supervisor.py").read_text(encoding="utf-8")
    init_text = (ROOT / "lean_rgc" / "__init__.py").read_text(encoding="utf-8")

    assert "from .executor import LeanExecutor, LeanExecutorConfig" in frontier_text
    assert "from .bulk_executor import BulkAuditConfig, LeanBulkAuditor" in supervisor_text
    assert "from .executor import LeanExecutor, LeanExecutorConfig" in supervisor_text
    assert "from .lean.frontier import build_frontiers" in init_text
    assert "from .frontier import build_frontiers" not in init_text


def test_fresh_orchestration_imports_do_not_reintroduce_circular_imports():
    code = """
import lean_rgc
import lean_rgc.frontier
import lean_rgc.lean.frontier
import lean_rgc.lean_worker_supervisor
import lean_rgc.lean.worker_supervisor
import lean_rgc.lean.executor
import lean_rgc.lean.bulk_executor
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr


def test_frontier_audit_cli_still_works_with_canonical_frontier(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(json.dumps({"task_id": "t_true", "statement": "True", "imports": []}) + "\n", encoding="utf-8")
    out = tmp_path / "frontier"

    assert cli_main(["frontier-audit", "--tasks", str(tasks), "--out", str(out), "--dry-run"]) == 0
    assert out.exists()


def test_supervisor_queue_smoke_uses_canonical_worker_supervisor(tmp_path: Path):
    from lean_rgc.lean.executor import LeanExecutorConfig
    from lean_rgc.lean.worker_supervisor import run_supervised_audit_queue

    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    task = LeanTask(task_id="t_true", statement="True", imports=[])
    action = TacticAction(action_id="trivial", tactic="trivial")
    fp = project_fingerprint(lean_cmd="lean", workdir=None, backend="source_check", import_mode="preserve")
    enqueue_audit_jobs(
        db,
        [task],
        [action],
        run_id="r_v81",
        backend="source_check",
        import_mode="preserve",
        project_fingerprint_value=fp,
    )

    summary = run_supervised_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(dry_run=True, timeout_s=5.0),
        run_id="r_v81",
        job_timeout_s=5.0,
    )

    assert summary["n_jobs"] == 1
    assert summary["n_succeeded"] == 1
    assert (out / "responses.jsonl").exists()
