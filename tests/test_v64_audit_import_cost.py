import json
import sys
from pathlib import Path

from lean_rgc.action_quarantine import action_quarantine_report
from lean_rgc.audit_env_profile import profile_audit_environment
from lean_rgc.audit_job_queue import audit_queue_status, enqueue_audit_jobs, project_fingerprint
from lean_rgc.cli import _load_actions_grouped, _actions_for_tasks, _materialize_total_budget_task_actions
from lean_rgc.executor import LeanExecutorConfig
from lean_rgc.lean_worker_supervisor import run_bulk_audit_queue, run_supervised_audit_queue
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl
from lean_rgc.timeout_ledger import timeout_ledger_report


def _fake_lean(tmp_path: Path, *, sleep_s: float = 0.0, returncode: int = 0) -> str:
    script = tmp_path / "fake_lean.py"
    script.write_text(
        "\n".join(
            [
                "import sys, time",
                f"time.sleep({float(sleep_s)!r})",
                "print('Lean (fake)')" if returncode == 0 else "print('fake lean error')",
                f"raise SystemExit({int(returncode)})",
            ]
        ),
        encoding="utf-8",
    )
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def _fake_lean_timeout_multi_theorem(tmp_path: Path) -> str:
    script = tmp_path / "fake_lean_timeout_multi.py"
    script.write_text(
        "\n".join(
            [
                "import sys, time",
                "src = open(sys.argv[-1], encoding='utf-8').read() if len(sys.argv) > 1 else ''",
                "n = sum(1 for line in src.splitlines() if line.startswith('theorem '))",
                "if n > 1:",
                "    time.sleep(2.0)",
                "print('ok')",
            ]
        ),
        encoding="utf-8",
    )
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def test_audit_env_profile_writes_recommendations_without_real_lean(tmp_path: Path):
    task = LeanTask(task_id="t0", statement="True", imports=[])
    action = TacticAction(action_id="trivial", tactic="trivial")
    out = tmp_path / "profile.json"

    rep = profile_audit_environment(
        tasks=[task],
        actions_by_task=[action],
        lean_cmd=_fake_lean(tmp_path),
        timeout_s=5.0,
        out_json=out,
    )

    assert out.exists()
    assert rep["schema_version"] == "lean-rgc-audit-env-profile-v64.0"
    assert rep["recommended_timeout_s"] >= 30
    assert rep["recommended_workers"] >= 1
    assert {c["name"] for c in rep["cases"]} >= {"imports_only", "statement_fail", "exact_job"}


def test_bulk_queue_materializes_legacy_outputs_with_fake_lean(tmp_path: Path):
    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    tasks = [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(4)]
    actions = [TacticAction(action_id="trivial", tactic="trivial")]
    lean_cmd = _fake_lean(tmp_path)
    fp = project_fingerprint(lean_cmd=lean_cmd, workdir=None, backend="source_check_bulk", import_mode="preserve")

    enqueue_audit_jobs(
        db,
        tasks,
        actions,
        run_id="bulk_r1",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp,
    )
    summary = run_bulk_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(lean_cmd=lean_cmd, timeout_s=5.0),
        run_id="bulk_r1",
        workers=2,
        job_timeout_s=5.0,
        batch_size=2,
    )

    assert summary["audit_queue_backend"] == "bulk"
    assert summary["n_succeeded"] == 4
    assert audit_queue_status(db, run_id="bulk_r1")["by_status"]["succeeded"] == 4
    responses = read_jsonl(out / "responses.jsonl")
    audits = read_jsonl(out / "micro_audit.jsonl")
    assert len(responses) == 4
    assert len(audits) == 4
    assert all(a["audit_flags"]["audit_queue_backend"] == "bulk" for a in audits)


def test_bulk_queue_retries_timed_out_batches_as_smaller_chunks(tmp_path: Path):
    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    tasks = [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(4)]
    actions = [TacticAction(action_id="trivial", tactic="trivial")]
    lean_cmd = _fake_lean_timeout_multi_theorem(tmp_path)
    fp = project_fingerprint(lean_cmd=lean_cmd, workdir=None, backend="source_check_bulk", import_mode="preserve")

    enqueue_audit_jobs(
        db,
        tasks,
        actions,
        run_id="bulk_retry",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp,
    )
    summary = run_bulk_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(lean_cmd=lean_cmd, timeout_s=0.75),
        run_id="bulk_retry",
        workers=1,
        job_timeout_s=0.75,
        batch_size=4,
    )

    assert summary["n_succeeded"] == 4
    assert summary["n_timeout"] == 0
    assert summary["bulk_retry_batches"] > 0
    assert summary["bulk_attempts"] > summary["bulk_initial_batches"]


def test_total_budget_materialized_actions_do_not_expand_per_task(tmp_path: Path):
    tasks = [LeanTask(task_id=f"task{i}", statement="True", imports=[]) for i in range(8)]
    actions_path = tmp_path / "scheduled.jsonl"
    out_path = tmp_path / "task_budgeted.jsonl"
    rows = []
    for i in range(20):
        rows.append(
                {
                    "action_id": f"a{i}",
                    "tactic": f"trivial -- {i}",
                "metadata": {
                    "source": "bivariate_contextual_probe_v51",
                    "premise_contextual_probe": True,
                    "baseline_required_for_incremental_response": False,
                },
            }
        )
    actions_path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    summary = _materialize_total_budget_task_actions(actions_path, tasks, out_path, budget=10)
    assert summary["n_actions"] == 10
    base, by_task = _load_actions_grouped(out_path)
    assert base == []
    acts = _actions_for_tasks(tasks, base, by_task, max_candidates=10)
    assert sum(len(v) for v in acts.values()) == 10


def test_import_scoped_timeouts_do_not_quarantine_core_action(tmp_path: Path):
    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    tasks = [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(4)]
    action = TacticAction(action_id="rfl", tactic="rfl", metadata={"supervisor": {"simulate_hang_s": 2.0}})
    fp = project_fingerprint(lean_cmd="lean", workdir=None, backend="source_check", import_mode="preserve")

    enqueue_audit_jobs(
        db,
        tasks,
        [action],
        run_id="import_timeout",
        backend="source_check",
        import_mode="preserve",
        project_fingerprint_value=fp,
        max_attempts=1,
    )
    summary = run_supervised_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(dry_run=True, timeout_s=10.0),
        run_id="import_timeout",
        job_timeout_s=0.25,
        continue_on_timeout=True,
        import_wall_s=0.20,
    )

    assert summary["n_timeout"] == 4
    assert summary["n_quarantined"] == 0
    timeout_report = timeout_ledger_report(db)
    assert timeout_report["by_scope"]["import_timeout"] == 4
    assert timeout_report["n_tactic_timeout"] == 0
    qrep = action_quarantine_report(db)
    assert not any(r["key_value"] == "rfl" and r["status"] == "quarantined" for r in qrep["rows"])
