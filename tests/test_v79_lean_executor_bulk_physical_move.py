from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

from lean_rgc.schemas import LeanTask, TacticAction


ROOT = Path(__file__).resolve().parents[1]


def test_executor_implementation_lives_under_lean_package():
    canonical = importlib.import_module("lean_rgc.lean.executor")
    compat = importlib.import_module("lean_rgc.executor")

    assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / "executor.py"
    assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / "executor.py"
    assert compat.LeanExecutor is canonical.LeanExecutor
    assert compat.LeanExecutorConfig is canonical.LeanExecutorConfig


def test_bulk_executor_implementation_lives_under_lean_package():
    canonical = importlib.import_module("lean_rgc.lean.bulk_executor")
    compat = importlib.import_module("lean_rgc.bulk_executor")

    assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / "bulk_executor.py"
    assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / "bulk_executor.py"
    for attr in [
        "BulkAuditConfig",
        "BulkAuditReport",
        "BulkBlock",
        "LeanBulkAuditor",
        "bulk_audit_to_files",
        "_block_messages",
        "_classify_block_failure",
        "_errors_by_line",
        "_render_bulk_file",
        "_sanitize_ident",
    ]:
        assert getattr(compat, attr) is getattr(canonical, attr)


def test_bulk_private_helper_compatibility_still_works():
    from lean_rgc.bulk_executor import _block_messages, _errors_by_line, _render_bulk_file

    task = LeanTask(task_id="t1", statement="True", imports=[])
    action = TacticAction(action_id="bad", tactic="exact False.elim ?h", tactic_class="exact")
    src, blocks = _render_bulk_file([(task, action)])
    assert "RGC_AUDIT_BEGIN" in src
    fake = f"/tmp/x.lean:{blocks[0].start_line + 1}:3: error: unknown identifier 'h'\nmore detail"
    errs = _errors_by_line(fake)
    assert any("unknown identifier" in m for m in _block_messages(blocks[0], errs))


def test_bulk_executor_marks_global_lean_errors_as_failures(tmp_path: Path):
    from lean_rgc.lean.bulk_executor import BulkAuditConfig, LeanBulkAuditor

    fake_lean = tmp_path / "fake_lean.py"
    fake_lean.write_text(
        "\n".join(
            [
                "import sys",
                "print(f'{sys.argv[-1]}:1:0: error: unknown module prefix MiniF2F')",
                "raise SystemExit(1)",
            ]
        ),
        encoding="utf-8",
    )
    auditor = LeanBulkAuditor(
        BulkAuditConfig(
            lean_cmd=f"{Path(sys.executable).as_posix()} {fake_lean.as_posix()}",
            workdir=str(tmp_path),
            timeout_s=5,
            batch_size=1,
        )
    )
    records, report = auditor.run_pairs(
        [
            (
                LeanTask(task_id="t1", statement="True", imports=["MiniF2F.ProblemImports"]),
                TacticAction(action_id="trivial", tactic="trivial"),
            )
        ]
    )

    assert records[0].status == "elab_error"
    assert records[0].audit_flags["global_error"] is True
    assert report.status_counts == {"elab_error": 1}


def test_lean_executor_dry_run_still_audits_tiny_task():
    from lean_rgc.lean.executor import LeanExecutor, LeanExecutorConfig

    task = LeanTask(task_id="t_true", statement="True", imports=[])
    action = TacticAction(action_id="trivial", tactic="trivial", tactic_class="trivial")
    rec = LeanExecutor(LeanExecutorConfig(dry_run=True)).run_tactic(task, action)
    assert rec.status == "success"
    assert rec.after_state is not None
    assert rec.after_state.target == ""


def test_fresh_imports_do_not_reintroduce_circular_imports():
    code = """
import lean_rgc
import lean_rgc.executor
import lean_rgc.bulk_executor
import lean_rgc.lean.executor
import lean_rgc.lean.bulk_executor
import lean_rgc.lean_server
import lean_rgc.lean_worker_supervisor
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr


def test_runtime_imports_use_canonical_executor_and_bulk_paths():
    expected = {
        "audit_env_profile.py": "from .lean.executor import LeanExecutor, LeanExecutorConfig",
        "batch.py": "from .lean.executor import LeanExecutor, LeanExecutorConfig",
        "lean/frontier.py": "from .executor import LeanExecutor, LeanExecutorConfig",
        "lean/kernel_state.py": "from .executor import LeanExecutor, LeanExecutorConfig",
        "lean/server.py": "from .executor import LeanExecutor, LeanExecutorConfig",
        "lean/worker_supervisor.py": "from .bulk_executor import BulkAuditConfig, LeanBulkAuditor",
        "lean/persistent_lean_worker.py": "from .executor import LeanExecutor, LeanExecutorConfig",
        "proof_replay.py": "from .lean.executor import LeanExecutor, LeanExecutorConfig",
    }
    for filename, needle in expected.items():
        text = (ROOT / "lean_rgc" / filename).read_text(encoding="utf-8")
        assert needle in text

    for filename in ["audit_env_profile.py", "batch.py"]:
        text = (ROOT / "lean_rgc" / filename).read_text(encoding="utf-8")
        assert "from .executor import" not in text
        assert "from .bulk_executor import" not in text
