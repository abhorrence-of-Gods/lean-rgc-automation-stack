from pathlib import Path

from lean_rgc.action_quarantine import action_quarantine_report
from lean_rgc.audit_job_queue import audit_queue_status, enqueue_audit_jobs, project_fingerprint
from lean_rgc.executor import LeanExecutorConfig
from lean_rgc.lean_worker_supervisor import run_supervised_audit_queue
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl


def _tasks(n: int = 1) -> list[LeanTask]:
    return [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(n)]


def test_audit_queue_idempotent_and_materializes_legacy_outputs(tmp_path: Path):
    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    tasks = _tasks(1)
    actions = [TacticAction(action_id="trivial", tactic="trivial")]
    fp = project_fingerprint(lean_cmd="lean", workdir=None, backend="source_check", import_mode="preserve")

    first = enqueue_audit_jobs(
        db,
        tasks,
        actions,
        run_id="r1",
        backend="source_check",
        import_mode="preserve",
        project_fingerprint_value=fp,
    )
    second = enqueue_audit_jobs(
        db,
        tasks,
        actions,
        run_id="r1",
        backend="source_check",
        import_mode="preserve",
        project_fingerprint_value=fp,
    )

    assert first["n_inserted"] == 1
    assert second["n_inserted"] == 0
    assert second["n_reused"] == 1

    summary = run_supervised_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(dry_run=True, timeout_s=5.0),
        run_id="r1",
        job_timeout_s=5.0,
    )

    assert summary["n_jobs"] == 1
    assert summary["n_succeeded"] == 1
    assert (out / "responses.jsonl").exists()
    assert (out / "micro_audit.jsonl").exists()
    assert (out / "summary.json").exists()
    responses = read_jsonl(out / "responses.jsonl")
    assert responses[0]["action_id"] == "trivial"
    assert audit_queue_status(db, run_id="r1")["by_status"]["succeeded"] == 1


def test_supervisor_timeout_continues_and_quarantines_repeated_action(tmp_path: Path):
    db = tmp_path / "audit.sqlite"
    out = tmp_path / "audit"
    tasks = _tasks(4)
    hang = TacticAction(
        action_id="slow_bad",
        tactic="trivial",
        metadata={"supervisor": {"simulate_hang_s": 3.0}},
    )
    fp = project_fingerprint(lean_cmd="lean", workdir=None, backend="source_check", import_mode="preserve")
    enqueue_audit_jobs(
        db,
        tasks,
        [hang],
        run_id="r_timeout",
        backend="source_check",
        import_mode="preserve",
        project_fingerprint_value=fp,
        max_attempts=1,
    )

    summary = run_supervised_audit_queue(
        db_path=db,
        out_dir=out,
        executor_config=LeanExecutorConfig(dry_run=True, timeout_s=10.0),
        run_id="r_timeout",
        job_timeout_s=0.25,
        continue_on_timeout=True,
    )

    assert summary["n_timeout"] >= 3
    assert summary["n_quarantined"] >= 1
    statuses = audit_queue_status(db, run_id="r_timeout")["by_status"]
    assert statuses["timeout"] >= 3
    assert statuses["quarantined"] >= 1
    qrep = action_quarantine_report(db)
    assert any(r["key_value"] == "slow_bad" and r["status"] == "quarantined" for r in qrep["rows"])
    responses = read_jsonl(out / "responses.jsonl")
    assert any(r["audit_status"] == "timeout" for r in responses)
    assert any(r["audit_status"] == "quarantined" for r in responses)
