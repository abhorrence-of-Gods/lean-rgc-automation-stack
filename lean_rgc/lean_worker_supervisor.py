from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import multiprocessing as mp
import os
import queue
import time

from .action_quarantine import ensure_quarantine_schema, is_action_quarantined, refresh_action_quarantine
from .audit_job_queue import (
    AuditJob,
    audit_queue_status,
    connect_queue,
    enqueue_audit_jobs,
    lease_next_job,
    mark_job_result,
    mark_job_running,
    project_fingerprint,
)
from .batch import _pair_key
from .dataset import summarize_response_rows
from .defects import ProofDefectExtractor
from .executor import LeanExecutor, LeanExecutorConfig
from .schemas import AuditRecord, LeanTask, ProofState, ResponseRecord, TacticAction, write_jsonl
from .timeout_ledger import ensure_timeout_schema, record_timeout_event, record_worker_event, timeout_ledger_report


SCHEMA_LEAN_WORKER_SUPERVISOR = "lean-rgc-lean-worker-supervisor-v63.0"


def _tail(text: str | None, n: int = 4000) -> str:
    return (text or "")[-n:]


def _executor_config_dict(config: LeanExecutorConfig) -> dict[str, Any]:
    return {
        "lean_cmd": config.lean_cmd,
        "workdir": config.workdir,
        "timeout_s": float(config.timeout_s),
        "keep_files": bool(config.keep_files),
        "dry_run": bool(config.dry_run),
        "extra_set_options": config.extra_set_options,
        "cache_dir": config.cache_dir,
        "trace_state": bool(config.trace_state),
    }


def _execute_job_payload(payload: dict[str, Any], executor_config: dict[str, Any]) -> dict[str, Any]:
    task = LeanTask.from_dict(payload["task"])
    state = ProofState.from_dict(payload["state"])
    action = TacticAction.from_dict(payload["action"])
    meta = action.metadata if isinstance(action.metadata, dict) else {}
    sim = meta.get("supervisor") if isinstance(meta.get("supervisor"), dict) else {}
    sleep_s = float(sim.get("simulate_hang_s", 0.0) or 0.0)
    if sleep_s > 0:
        time.sleep(sleep_s)
    extractor = ProofDefectExtractor()
    before = extractor.extract(state)
    rec = LeanExecutor(LeanExecutorConfig(**executor_config)).run_tactic(task, action, state)
    after_state = rec.after_state or state
    after = extractor.extract(after_state, rec)
    resp, resp_flat, resp_keys = extractor.response(before, after)
    rec.defect_before = before.to_dict()
    rec.defect_after = after.to_dict()
    rec.response = resp
    rec.carrier_delta = {
        k: before.carrier.get(k, 0.0) - after.carrier.get(k, 0.0)
        for k in sorted(set(before.carrier) | set(after.carrier))
    }
    ad = rec.to_dict()
    ad["action"] = action.to_dict()
    ad["task_id"] = task.task_id
    ad["target"] = task.statement
    rr = ResponseRecord(
        state_id=state.state_id,
        action_id=action.action_id,
        response=resp,
        response_flat=resp_flat,
        response_keys=resp_keys,
        defect_before=before,
        defect_after=after,
        audit_status=str(rec.status),
        carrier_delta=rec.carrier_delta or {},
    ).to_dict()
    rr["task_id"] = task.task_id
    rr["target"] = task.statement
    rr["action"] = action.to_dict()
    return {"ok": True, "audit": ad, "response": rr}


def _child_run_job(payload: dict[str, Any], executor_config: dict[str, Any], result_q: mp.Queue) -> None:
    try:
        result_q.put(_execute_job_payload(payload, executor_config))
    except BaseException as exc:  # child boundary: serialize every failure
        result_q.put({"ok": False, "error": repr(exc), "error_type": type(exc).__name__})


def _synthetic_result(job: AuditJob, *, status: str, elapsed_ms: float, message: str, worker_id: str) -> dict[str, Any]:
    task = LeanTask.from_dict(job.payload["task"])
    state = ProofState.from_dict(job.payload["state"])
    action = TacticAction.from_dict(job.payload["action"])
    extractor = ProofDefectExtractor()
    before = extractor.extract(state)
    after = extractor.extract(state)
    resp, flat, keys = extractor.response(before, after)
    rec = AuditRecord(
        task_id=task.task_id,
        state_id=state.state_id,
        action_id=action.action_id,
        status=status,  # type: ignore[arg-type]
        elapsed_ms=float(elapsed_ms),
        stdout="",
        stderr=message,
        messages=[message] if message else [],
        after_state=state,
        defect_before=before.to_dict(),
        defect_after=after.to_dict(),
        response=resp,
        carrier_delta={},
        audit_flags={
            "audit_queue": True,
            "synthetic": True,
            "worker_id": worker_id,
            "supervisor_status": status,
        },
    )
    ad = rec.to_dict()
    ad["action"] = action.to_dict()
    ad["task_id"] = task.task_id
    ad["target"] = task.statement
    rr = ResponseRecord(
        state_id=state.state_id,
        action_id=action.action_id,
        response=resp,
        response_flat=flat,
        response_keys=keys,
        defect_before=before,
        defect_after=after,
        audit_status=status,
        carrier_delta={},
    ).to_dict()
    rr["task_id"] = task.task_id
    rr["target"] = task.statement
    rr["action"] = action.to_dict()
    return {"ok": True, "audit": ad, "response": rr}


def _run_job_process(job: AuditJob, *, executor_config: LeanExecutorConfig, timeout_s: float, worker_id: str) -> tuple[str, dict[str, Any], float, bool]:
    action = TacticAction.from_dict(job.payload["action"])
    meta = action.metadata if isinstance(action.metadata, dict) else {}
    sim = meta.get("supervisor") if isinstance(meta.get("supervisor"), dict) else {}
    if executor_config.dry_run and not float(sim.get("simulate_hang_s", 0.0) or 0.0):
        t0_inline = time.time()
        try:
            result = _execute_job_payload(job.payload, _executor_config_dict(executor_config))
        except BaseException as exc:
            syn = _synthetic_result(job, status="fail", elapsed_ms=(time.time() - t0_inline) * 1000.0, message=repr(exc), worker_id=worker_id)
            syn["worker_error"] = {"error": repr(exc), "error_type": type(exc).__name__}
            return "failed", syn, time.time() - t0_inline, False
        audit_status = str((result.get("audit") or {}).get("status") or "")
        return ("timeout" if audit_status == "timeout" else "succeeded"), result, time.time() - t0_inline, False
    ctx = mp.get_context("spawn" if os.name == "nt" else "fork")
    result_q: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_child_run_job, args=(job.payload, _executor_config_dict(executor_config), result_q))
    t0 = time.time()
    proc.start()
    proc.join(max(0.1, float(timeout_s or executor_config.timeout_s or 20.0)))
    elapsed_s = time.time() - t0
    killed = False
    if proc.is_alive():
        killed = True
        proc.terminate()
        proc.join(3.0)
        if proc.is_alive():
            proc.kill()
            proc.join(3.0)
        result = _synthetic_result(
            job,
            status="timeout",
            elapsed_ms=elapsed_s * 1000.0,
            message=f"Lean worker job timed out after {timeout_s}s and was terminated",
            worker_id=worker_id,
        )
        return "timeout", result, elapsed_s, killed
    try:
        result = result_q.get_nowait()
    except queue.Empty:
        result = {"ok": False, "error": f"worker exited without result; exitcode={proc.exitcode}", "error_type": "WorkerNoResult"}
    if not result.get("ok"):
        syn = _synthetic_result(
            job,
            status="fail",
            elapsed_ms=elapsed_s * 1000.0,
            message=str(result.get("error") or "worker failed"),
            worker_id=worker_id,
        )
        syn["worker_error"] = result
        return "failed", syn, elapsed_s, killed
    audit_status = str((result.get("audit") or {}).get("status") or "")
    if audit_status == "timeout":
        return "timeout", result, elapsed_s, killed
    return "succeeded", result, elapsed_s, killed


def materialize_queue_results(db_path: str | Path, out_dir: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    conn = connect_queue(db_path)
    try:
        clauses = ["result_json IS NOT NULL", "status IN ('succeeded','failed','timeout','quarantined')"]
        params: list[Any] = []
        if run_id:
            clauses.append("run_id=?")
            params.append(run_id)
        rows = conn.execute(
            "SELECT * FROM audit_jobs WHERE " + " AND ".join(clauses) + " ORDER BY created_at ASC",
            params,
        ).fetchall()
        audits: list[dict[str, Any]] = []
        responses: list[dict[str, Any]] = []
        for r in rows:
            try:
                result = json.loads(r["result_json"] or "{}")
            except Exception:
                continue
            audit = result.get("audit")
            response = result.get("response")
            if isinstance(audit, dict):
                audit.setdefault("audit_queue_job_id", r["job_id"])
                audit.setdefault("queue_status", r["status"])
                audits.append(audit)
            if isinstance(response, dict):
                response.setdefault("audit_queue_job_id", r["job_id"])
                response.setdefault("queue_status", r["status"])
                responses.append(response)
        seen: set[tuple[str, str]] = set()
        dedup_audits: list[dict[str, Any]] = []
        dedup_responses: list[dict[str, Any]] = []
        for audit, response in zip(audits, responses):
            key = _pair_key(str(response.get("state_id")), str(response.get("action_id")))
            if key in seen:
                continue
            seen.add(key)
            dedup_audits.append(audit)
            dedup_responses.append(response)
        defects: list[dict[str, Any]] = []
        seen_states: set[str] = set()
        for r in dedup_responses:
            sid = str(r.get("state_id") or "")
            if not sid or sid in seen_states:
                continue
            seen_states.add(sid)
            db = r.get("defect_before")
            if isinstance(db, dict):
                row = dict(db)
                row["state_id"] = sid
                row["task_id"] = r.get("task_id") or db.get("task_id")
                defects.append(row)
        write_jsonl(out / "micro_audit.jsonl", dedup_audits)
        write_jsonl(out / "responses.jsonl", dedup_responses)
        write_jsonl(out / "defects.jsonl", defects)
        summary = summarize_response_rows(dedup_responses).to_dict()
        queue_summary = audit_queue_status(conn, run_id=run_id)
        summary.update(
            {
                "schema_version": SCHEMA_LEAN_WORKER_SUPERVISOR,
                "audit_queue": True,
                "db_path": str(db_path),
                "run_id": run_id,
                "n_jobs": queue_summary.get("n_jobs", 0),
                "n_succeeded": queue_summary.get("n_succeeded", 0),
                "n_failed": queue_summary.get("n_failed", 0),
                "n_timeout": queue_summary.get("n_timeout", 0),
                "n_quarantined": queue_summary.get("n_quarantined", 0),
                "queue_status": queue_summary,
            }
        )
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        (out / "server_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return summary
    finally:
        conn.close()


def run_supervised_audit_queue(
    *,
    db_path: str | Path,
    out_dir: str | Path,
    executor_config: LeanExecutorConfig,
    run_id: str | None = None,
    workers: int = 1,
    job_timeout_s: float | None = None,
    max_jobs: int | None = None,
    continue_on_timeout: bool = True,
    lanes: list[str] | None = None,
    heavy_lane_allows_quarantine: bool = True,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    conn = connect_queue(db_path)
    worker_restarts = 0
    executed = 0
    try:
        ensure_timeout_schema(conn)
        ensure_quarantine_schema(conn)
        timeout_s = float(job_timeout_s or executor_config.timeout_s or 20.0)
        lane_set = lanes or ["source_check", "kernel_rpc", "heavy"]
        while max_jobs is None or executed < max_jobs:
            refresh_action_quarantine(db_path)
            worker_id = f"lean-worker-{os.getpid()}-{executed % max(1, int(workers or 1))}"
            job = lease_next_job(
                conn,
                worker_id=worker_id,
                lease_seconds=timeout_s + 60.0,
                lanes=lane_set,
                include_quarantined=("heavy" in lane_set and heavy_lane_allows_quarantine),
            )
            if job is None:
                break
            allow_heavy = job.lane == "heavy" and heavy_lane_allows_quarantine
            quarantined, reason = is_action_quarantined(conn, action_id=job.action_id, tactic_hash=job.tactic_hash)
            if quarantined and not allow_heavy:
                result = _synthetic_result(
                    job,
                    status="quarantined",
                    elapsed_ms=0.0,
                    message=reason or "action quarantined by timeout ledger",
                    worker_id=worker_id,
                )
                mark_job_result(conn, job.job_id, status="quarantined", result=result, error=reason)
                executed += 1
                continue
            mark_job_running(conn, job.job_id, worker_id=worker_id)
            record_worker_event(conn, worker_id=worker_id, event_type="start", job_id=job.job_id, backend=job.backend, lane=job.lane)
            queue_status, result, elapsed_s, killed = _run_job_process(job, executor_config=executor_config, timeout_s=timeout_s, worker_id=worker_id)
            if killed:
                worker_restarts += 1
                record_worker_event(
                    conn,
                    worker_id=worker_id,
                    event_type="killed_timeout",
                    job_id=job.job_id,
                    backend=job.backend,
                    lane=job.lane,
                    detail={"elapsed_s": elapsed_s, "timeout_s": timeout_s},
                )
            if queue_status == "timeout":
                audit = result.get("audit") if isinstance(result.get("audit"), dict) else {}
                record_timeout_event(
                    conn,
                    job_id=job.job_id,
                    task_id=job.task_id,
                    action_id=job.action_id,
                    tactic_hash=job.tactic_hash,
                    backend=job.backend,
                    lane=job.lane,
                    timeout_s=timeout_s,
                    elapsed_s=elapsed_s,
                    stdout_tail=_tail(audit.get("stdout")),
                    stderr_tail=_tail(audit.get("stderr")),
                    worker_id=worker_id,
                    detail={"killed": killed},
                )
            mark_job_result(conn, job.job_id, status=queue_status, result=result, error=result.get("error"))
            record_worker_event(conn, worker_id=worker_id, event_type="finish", job_id=job.job_id, backend=job.backend, lane=job.lane, detail={"status": queue_status})
            executed += 1
            if queue_status == "timeout" and not continue_on_timeout:
                break
        refresh_action_quarantine(db_path)
        summary = materialize_queue_results(db_path, out, run_id=run_id)
        timeout_report = timeout_ledger_report(db_path)
        quarantine_report = refresh_action_quarantine(db_path)
        summary.update(
            {
                "n_executed_this_run": executed,
                "worker_restarts": int(timeout_report.get("worker_restarts", worker_restarts)),
                "timeout_report": timeout_report,
                "quarantine_report": quarantine_report,
            }
        )
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        (out / "server_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return summary
    finally:
        conn.close()


def enqueue_and_run_supervised_audit(
    *,
    db_path: str | Path,
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    out_dir: str | Path,
    executor_config: LeanExecutorConfig,
    run_id: str,
    backend: str,
    import_mode: str,
    max_actions: int = 64,
    max_attempts: int = 1,
    workers: int = 1,
    job_timeout_s: float | None = None,
    continue_on_timeout: bool = True,
    lane: str = "source_check",
) -> dict[str, Any]:
    enqueue = enqueue_audit_jobs(
        db_path,
        tasks,
        actions_by_task,
        run_id=run_id,
        backend=backend,
        import_mode=import_mode,
        project_fingerprint_value=project_fingerprint(
            lean_cmd=executor_config.lean_cmd,
            workdir=executor_config.workdir,
            backend=backend,
            import_mode=import_mode,
        ),
        max_actions=max_actions,
        max_attempts=max_attempts,
        lane=lane,
    )
    summary = run_supervised_audit_queue(
        db_path=db_path,
        out_dir=out_dir,
        executor_config=executor_config,
        run_id=run_id,
        workers=workers,
        job_timeout_s=job_timeout_s,
        continue_on_timeout=continue_on_timeout,
        lanes=[lane] if lane else None,
    )
    summary["enqueue"] = enqueue
    return summary


__all__ = [
    "SCHEMA_LEAN_WORKER_SUPERVISOR",
    "enqueue_and_run_supervised_audit",
    "materialize_queue_results",
    "run_supervised_audit_queue",
]
