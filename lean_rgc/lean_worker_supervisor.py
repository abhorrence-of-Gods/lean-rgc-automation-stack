from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
import json
import multiprocessing as mp
import os
import queue
import threading
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
from .audit_result_cache import (
    apply_cache_to_queue,
    detect_lean_version,
    store_queue_results_in_cache,
    workdir_fingerprint,
)
from .batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW, _pair_key
from .lean.bulk_executor import BulkAuditConfig, LeanBulkAuditor
from .dataset import summarize_response_rows
from .defects import ProofDefectExtractor
from .lean.executor import LeanExecutor, LeanExecutorConfig
from .schemas import AuditRecord, LeanTask, ProofState, ResponseRecord, TacticAction, write_records
from .timeout_ledger import ensure_timeout_schema, record_timeout_event, record_worker_event, timeout_ledger_report


SCHEMA_LEAN_WORKER_SUPERVISOR = "lean-rgc-lean-worker-supervisor-v63.0"


def _timeout_scope_for_run(*, import_wall_s: float | None, timeout_s: float, killed: bool = False, bulk: bool = False) -> str:
    if import_wall_s is not None and import_wall_s >= float(timeout_s) * 0.5:
        return "import_timeout"
    if bulk:
        return "batch_timeout"
    if killed:
        return "tactic_timeout"
    return "worker_timeout"


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


def _result_from_audit_record(
    *,
    task: LeanTask,
    action: TacticAction,
    state: ProofState,
    rec: AuditRecord,
    audit_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extractor = ProofDefectExtractor()
    before = extractor.extract(state)
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
    rec.audit_flags = dict(rec.audit_flags or {})
    rec.audit_flags.update(audit_flags or {})
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
        clauses = ["result_json IS NOT NULL", "status IN ('succeeded','succeeded_from_cache','failed','timeout','quarantined')"]
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
        write_records(out / "micro_audit.jsonl", dedup_audits, schema_version=SCHEMA_AUDIT_ROW, run_id=run_id)
        write_records(out / "responses.jsonl", dedup_responses, schema_version=SCHEMA_RESPONSE_ROW, run_id=run_id)
        write_records(out / "defects.jsonl", defects, schema_version=SCHEMA_DEFECT_ROW, run_id=run_id)
        summary = summarize_response_rows(dedup_responses).to_dict()
        queue_summary = audit_queue_status(conn, run_id=run_id)
        timeout_report = timeout_ledger_report(db_path)
        summary.update(
            {
                "schema_version": SCHEMA_LEAN_WORKER_SUPERVISOR,
                "audit_queue": True,
                "db_path": str(db_path),
                "run_id": run_id,
                "n_jobs": queue_summary.get("n_jobs", 0),
                "n_succeeded": queue_summary.get("n_succeeded", 0),
                "n_cache_hit": queue_summary.get("n_cache_hit", 0),
                "n_failed": queue_summary.get("n_failed", 0),
                "n_timeout": queue_summary.get("n_timeout", 0),
                "n_quarantined": queue_summary.get("n_quarantined", 0),
                "n_tactic_timeout": timeout_report.get("n_tactic_timeout", 0),
                "n_infra_timeout": timeout_report.get("n_infra_timeout", 0),
                "n_quarantine_suppressed_by_import_cost": timeout_report.get("n_quarantine_suppressed_by_import_cost", 0),
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
    import_wall_s: float | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    worker_restarts = 0
    executed = 0

    counter_lock = threading.Lock()
    remaining_jobs = {"n": int(max_jobs) if max_jobs is not None else None}

    def take_slot() -> bool:
        if remaining_jobs["n"] is None:
            return True
        with counter_lock:
            if remaining_jobs["n"] <= 0:
                return False
            remaining_jobs["n"] -= 1
            return True

    def give_back_slot() -> None:
        if remaining_jobs["n"] is not None:
            with counter_lock:
                remaining_jobs["n"] += 1

    def worker_loop(worker_index: int) -> dict[str, int]:
        conn = connect_queue(db_path)
        local_executed = 0
        local_restarts = 0
        try:
            ensure_timeout_schema(conn)
            ensure_quarantine_schema(conn)
            timeout_s = float(job_timeout_s or executor_config.timeout_s or 20.0)
            lane_set = lanes or ["source_check", "kernel_rpc", "heavy"]
            worker_id = f"lean-worker-{os.getpid()}-{worker_index}"
            while True:
                if not take_slot():
                    break
                refresh_action_quarantine(db_path)
                job = lease_next_job(
                    conn,
                    worker_id=worker_id,
                    lease_seconds=timeout_s + 60.0,
                    lanes=lane_set,
                    include_quarantined=("heavy" in lane_set and heavy_lane_allows_quarantine),
                )
                if job is None:
                    give_back_slot()
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
                    local_executed += 1
                    continue
                mark_job_running(conn, job.job_id, worker_id=worker_id)
                record_worker_event(conn, worker_id=worker_id, event_type="start", job_id=job.job_id, backend=job.backend, lane=job.lane)
                queue_status, result, elapsed_s, killed = _run_job_process(job, executor_config=executor_config, timeout_s=timeout_s, worker_id=worker_id)
                if killed:
                    local_restarts += 1
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
                    timeout_scope = _timeout_scope_for_run(import_wall_s=import_wall_s, timeout_s=timeout_s, killed=killed)
                    if isinstance(audit, dict):
                        audit_flags = audit.get("audit_flags") if isinstance(audit.get("audit_flags"), dict) else {}
                        audit_flags["timeout_scope"] = timeout_scope
                        audit["audit_flags"] = audit_flags
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
                        timeout_scope=timeout_scope,
                        detail={"killed": killed, "import_wall_s": import_wall_s},
                    )
                mark_job_result(conn, job.job_id, status=queue_status, result=result, error=result.get("error"))
                record_worker_event(conn, worker_id=worker_id, event_type="finish", job_id=job.job_id, backend=job.backend, lane=job.lane, detail={"status": queue_status})
                local_executed += 1
                if queue_status == "timeout" and not continue_on_timeout:
                    break
            return {"executed": local_executed, "worker_restarts": local_restarts}
        finally:
            conn.close()

    conn = connect_queue(db_path)
    try:
        ensure_timeout_schema(conn)
        ensure_quarantine_schema(conn)
        n_workers = max(1, int(workers or 1))
        if n_workers == 1:
            res = worker_loop(0)
            executed += int(res.get("executed", 0))
            worker_restarts += int(res.get("worker_restarts", 0))
        else:
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                futures = [pool.submit(worker_loop, i) for i in range(n_workers)]
                for fut in as_completed(futures):
                    res = fut.result()
                    executed += int(res.get("executed", 0))
                    worker_restarts += int(res.get("worker_restarts", 0))
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


def _bulk_group_key(job: AuditJob, *, executor_config: LeanExecutorConfig, import_mode: str) -> tuple[Any, ...]:
    task = LeanTask.from_dict(job.payload["task"])
    return (
        tuple(task.imports or []),
        executor_config.workdir or "",
        executor_config.lean_cmd or "",
        import_mode or job.import_mode,
        bool(executor_config.trace_state),
    )


def _run_bulk_chunk(
    jobs: list[AuditJob],
    *,
    executor_config: LeanExecutorConfig,
    timeout_s: float,
    batch_size: int,
    import_wall_s: float | None,
    worker_id: str,
) -> list[tuple[AuditJob, str, dict[str, Any], float, str | None]]:
    tasks: list[LeanTask] = [LeanTask.from_dict(job.payload["task"]) for job in jobs]
    states: list[ProofState] = [ProofState.from_dict(job.payload["state"]) for job in jobs]
    actions: list[TacticAction] = [TacticAction.from_dict(job.payload["action"]) for job in jobs]
    pairs = list(zip(tasks, actions))
    try:
        auditor = LeanBulkAuditor(
            BulkAuditConfig(
                lean_cmd=executor_config.lean_cmd,
                workdir=executor_config.workdir,
                timeout_s=float(timeout_s),
                batch_size=max(1, int(batch_size or len(jobs) or 1)),
                keep_files=executor_config.keep_files,
                trace_state=executor_config.trace_state,
            )
        )
        records, report = auditor.run_pairs(pairs)
    except BaseException as exc:
        elapsed_ms = 0.0
        out: list[tuple[AuditJob, str, dict[str, Any], float, str | None]] = []
        for job in jobs:
            result = _synthetic_result(job, status="fail", elapsed_ms=elapsed_ms, message=repr(exc), worker_id=worker_id)
            result["worker_error"] = {"error": repr(exc), "error_type": type(exc).__name__, "bulk_worker": True}
            out.append((job, "failed", result, 0.0, None))
        return out
    elapsed_s = float(report.elapsed_ms or 0.0) / 1000.0
    out = []
    for job, task, state, action, rec in zip(jobs, tasks, states, actions, records):
        timeout_scope: str | None = None
        if str(rec.status) == "timeout":
            timeout_scope = _timeout_scope_for_run(import_wall_s=import_wall_s, timeout_s=timeout_s, bulk=True)
        result = _result_from_audit_record(
            task=task,
            action=action,
            state=state,
            rec=rec,
            audit_flags={
                "audit_queue": True,
                "audit_queue_backend": "bulk",
                "worker_id": worker_id,
                "bulk_batch_size": len(jobs),
                "bulk_timeout_s": float(timeout_s),
                **({"timeout_scope": timeout_scope} if timeout_scope else {}),
            },
        )
        queue_status = "timeout" if str(rec.status) == "timeout" else "succeeded"
        out.append((job, queue_status, result, elapsed_s, timeout_scope))
    return out


def _bulk_timed_out(results: list[tuple[AuditJob, str, dict[str, Any], float, str | None]]) -> bool:
    return any(queue_status == "timeout" for _job, queue_status, _result, _elapsed_s, _timeout_scope in results)


def _run_bulk_chunk_with_retry(
    jobs: list[AuditJob],
    *,
    executor_config: LeanExecutorConfig,
    timeout_s: float,
    batch_size: int,
    import_wall_s: float | None,
    worker_id: str,
    depth: int = 0,
) -> dict[str, Any]:
    results = _run_bulk_chunk(
        jobs,
        executor_config=executor_config,
        timeout_s=timeout_s,
        batch_size=batch_size,
        import_wall_s=import_wall_s,
        worker_id=worker_id,
    )
    stats = {
        "results": results,
        "bulk_attempts": 1,
        "bulk_retry_batches": 0,
        "bulk_retry_singletons": 0,
    }
    if len(jobs) <= 1 or not _bulk_timed_out(results):
        return stats

    mid = max(1, len(jobs) // 2)
    parts = [jobs[:mid], jobs[mid:]]
    retry_results: list[tuple[AuditJob, str, dict[str, Any], float, str | None]] = []
    stats["bulk_retry_batches"] += 1
    for part_index, part in enumerate(part for part in parts if part):
        sub = _run_bulk_chunk_with_retry(
            part,
            executor_config=executor_config,
            timeout_s=timeout_s,
            batch_size=len(part),
            import_wall_s=import_wall_s,
            worker_id=f"{worker_id}.retry{depth}.{part_index}",
            depth=depth + 1,
        )
        retry_results.extend(sub["results"])
        stats["bulk_attempts"] += int(sub.get("bulk_attempts", 0))
        stats["bulk_retry_batches"] += int(sub.get("bulk_retry_batches", 0))
        stats["bulk_retry_singletons"] += int(sub.get("bulk_retry_singletons", 0))
    final_timeout_ids = {job.job_id for job, queue_status, _result, _elapsed_s, _scope in retry_results if queue_status == "timeout"}
    stats["bulk_retry_singletons"] += len(final_timeout_ids)
    stats["results"] = retry_results
    return stats


def run_bulk_audit_queue(
    *,
    db_path: str | Path,
    out_dir: str | Path,
    executor_config: LeanExecutorConfig,
    run_id: str | None = None,
    workers: int = 1,
    job_timeout_s: float | None = None,
    max_jobs: int | None = None,
    lanes: list[str] | None = None,
    batch_size: int = 32,
    import_mode: str = "preserve",
    import_wall_s: float | None = None,
    heavy_lane_allows_quarantine: bool = True,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    timeout_s = float(job_timeout_s or executor_config.timeout_s or 60.0)
    lane_set = lanes or ["source_check", "kernel_rpc", "heavy"]
    conn = connect_queue(db_path)
    executed = 0
    try:
        ensure_timeout_schema(conn)
        ensure_quarantine_schema(conn)
        refresh_action_quarantine(db_path)
        now = time.time()
        clauses = [
            "(status='queued' OR (status IN ('leased','running') AND COALESCE(leased_until,0) < ?) OR (status='failed' AND attempt_count < max_attempts))"
        ]
        params: list[Any] = [now]
        if run_id:
            clauses.append("run_id=?")
            params.append(run_id)
        lane_list = [str(x) for x in lane_set if str(x)]
        if lane_list:
            clauses.append("lane IN (%s)" % ",".join("?" for _ in lane_list))
            params.extend(lane_list)
        sql = "SELECT * FROM audit_jobs WHERE " + " AND ".join(clauses) + " ORDER BY priority DESC, created_at ASC"
        if max_jobs is not None:
            sql += f" LIMIT {max(0, int(max_jobs))}"
        jobs = [AuditJob.from_row(r) for r in conn.execute(sql, params).fetchall()]
        runnable: list[AuditJob] = []
        for job in jobs:
            allow_heavy = job.lane == "heavy" and heavy_lane_allows_quarantine
            quarantined, reason = is_action_quarantined(conn, action_id=job.action_id, tactic_hash=job.tactic_hash)
            if quarantined and not allow_heavy:
                worker_id = f"lean-bulk-{os.getpid()}-quarantine"
                result = _synthetic_result(
                    job,
                    status="quarantined",
                    elapsed_ms=0.0,
                    message=reason or "action quarantined by timeout ledger",
                    worker_id=worker_id,
                )
                mark_job_result(conn, job.job_id, status="quarantined", result=result, error=reason)
                executed += 1
            else:
                runnable.append(job)
        groups: dict[tuple[Any, ...], list[AuditJob]] = {}
        for job in runnable:
            groups.setdefault(_bulk_group_key(job, executor_config=executor_config, import_mode=import_mode), []).append(job)
        chunks: list[list[AuditJob]] = []
        bs = max(1, int(batch_size or 32))
        for group_jobs in groups.values():
            for i in range(0, len(group_jobs), bs):
                chunks.append(group_jobs[i : i + bs])
        for idx, chunk in enumerate(chunks):
            worker_id = f"lean-bulk-{os.getpid()}-{idx}"
            for job in chunk:
                mark_job_running(conn, job.job_id, worker_id=worker_id)
                record_worker_event(conn, worker_id=worker_id, event_type="start", job_id=job.job_id, backend=job.backend, lane=job.lane, detail={"bulk": True, "batch_size": len(chunk)})
        def run_one(index_and_chunk: tuple[int, list[AuditJob]]) -> dict[str, Any]:
            idx, chunk = index_and_chunk
            worker_id = f"lean-bulk-{os.getpid()}-{idx}"
            return _run_bulk_chunk_with_retry(
                chunk,
                executor_config=executor_config,
                timeout_s=timeout_s,
                batch_size=len(chunk),
                import_wall_s=import_wall_s,
                worker_id=worker_id,
            )
        max_workers = max(1, int(workers or 1))
        if max_workers == 1:
            all_results = [run_one((i, c)) for i, c in enumerate(chunks)]
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                all_results = [f.result() for f in as_completed([pool.submit(run_one, (i, c)) for i, c in enumerate(chunks)])]
        bulk_attempts = 0
        bulk_retry_batches = 0
        bulk_retry_singletons = 0
        for batch_run in all_results:
            bulk_attempts += int(batch_run.get("bulk_attempts", 0))
            bulk_retry_batches += int(batch_run.get("bulk_retry_batches", 0))
            bulk_retry_singletons += int(batch_run.get("bulk_retry_singletons", 0))
            batch_results = batch_run.get("results", [])
            for job, queue_status, result, elapsed_s, timeout_scope in batch_results:
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
                        worker_id=str((audit.get("audit_flags") or {}).get("worker_id") if isinstance(audit.get("audit_flags"), dict) else ""),
                        timeout_scope=timeout_scope or "batch_timeout",
                        detail={"bulk": True, "import_wall_s": import_wall_s},
                    )
                mark_job_result(conn, job.job_id, status=queue_status, result=result, error=result.get("error"))
                audit = result.get("audit") if isinstance(result.get("audit"), dict) else {}
                flags = audit.get("audit_flags") if isinstance(audit.get("audit_flags"), dict) else {}
                record_worker_event(conn, worker_id=str(flags.get("worker_id") or "lean-bulk"), event_type="finish", job_id=job.job_id, backend=job.backend, lane=job.lane, detail={"status": queue_status, "bulk": True})
                executed += 1
        refresh_action_quarantine(db_path)
        summary = materialize_queue_results(db_path, out, run_id=run_id)
        timeout_report = timeout_ledger_report(db_path)
        quarantine_report = refresh_action_quarantine(db_path)
        summary.update(
            {
                "audit_queue_backend": "bulk",
                "bulk_batch_size": bs,
                "bulk_attempts": bulk_attempts,
                "bulk_initial_batches": len(chunks),
                "bulk_retry_batches": bulk_retry_batches,
                "bulk_retry_singletons": bulk_retry_singletons,
                "n_executed_this_run": executed,
                "worker_restarts": int(timeout_report.get("worker_restarts", 0)),
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
    queue_backend: str = "file",
    bulk_batch_size: int = 32,
    import_wall_s: float | None = None,
    audit_cache_db: str | Path | None = None,
    audit_cache_readonly: bool = False,
    audit_cache_lean_version: str | None = None,
) -> dict[str, Any]:
    project_fp = project_fingerprint(
        lean_cmd=executor_config.lean_cmd,
        workdir=executor_config.workdir,
        backend=backend,
        import_mode=import_mode,
    )
    enqueue = enqueue_audit_jobs(
        db_path,
        tasks,
        actions_by_task,
        run_id=run_id,
        backend=backend,
        import_mode=import_mode,
        project_fingerprint_value=project_fp,
        max_actions=max_actions,
        max_attempts=max_attempts,
        lane=lane,
    )
    cache_apply: dict[str, Any] | None = None
    cache_store: dict[str, Any] | None = None
    lean_version = audit_cache_lean_version
    workdir_fp = workdir_fingerprint(executor_config.workdir)
    if audit_cache_db:
        if not lean_version:
            lean_version = detect_lean_version(executor_config.lean_cmd, workdir=executor_config.workdir)
        cache_apply = apply_cache_to_queue(
            cache_db=audit_cache_db,
            queue_db=db_path,
            run_id=run_id,
            lean_version=lean_version,
            workdir_fingerprint_value=workdir_fp,
            import_mode=import_mode,
            trace_state=executor_config.trace_state,
            readonly=audit_cache_readonly,
        )
    actual_queue_backend = "bulk" if queue_backend == "bulk" and not executor_config.keep_files and not executor_config.dry_run else "file"
    if actual_queue_backend == "bulk":
        summary = run_bulk_audit_queue(
            db_path=db_path,
            out_dir=out_dir,
            executor_config=executor_config,
            run_id=run_id,
            workers=workers,
            job_timeout_s=job_timeout_s,
            lanes=[lane] if lane else None,
            batch_size=bulk_batch_size,
            import_mode=import_mode,
            import_wall_s=import_wall_s,
        )
    else:
        summary = run_supervised_audit_queue(
            db_path=db_path,
            out_dir=out_dir,
            executor_config=executor_config,
            run_id=run_id,
            workers=workers,
            job_timeout_s=job_timeout_s,
            continue_on_timeout=continue_on_timeout,
            lanes=[lane] if lane else None,
            import_wall_s=import_wall_s,
        )
    if audit_cache_db:
        cache_store = store_queue_results_in_cache(
            cache_db=audit_cache_db,
            queue_db=db_path,
            run_id=run_id,
            lean_version=lean_version or "unknown",
            workdir_fingerprint_value=workdir_fp,
            import_mode=import_mode,
            trace_state=executor_config.trace_state,
            readonly=audit_cache_readonly,
        )
        run_summary = dict(summary)
        summary = materialize_queue_results(db_path, out_dir, run_id=run_id)
        for key in (
            "n_executed_this_run",
            "worker_restarts",
            "timeout_report",
            "quarantine_report",
            "bulk_batch_size",
            "bulk_attempts",
            "bulk_initial_batches",
            "bulk_retry_batches",
            "bulk_retry_singletons",
        ):
            if key in run_summary:
                summary[key] = run_summary[key]
    summary["audit_queue_backend"] = actual_queue_backend
    summary["enqueue"] = enqueue
    if cache_apply or cache_store:
        summary["audit_cache"] = {
            "enabled": True,
            "cache_db": str(audit_cache_db),
            "readonly": bool(audit_cache_readonly),
            "lean_version": lean_version,
            "workdir_fingerprint": workdir_fp,
            "apply": cache_apply,
            "store": cache_store,
        }
        summary["n_cache_hit"] = int((cache_apply or {}).get("n_cache_hit", summary.get("n_cache_hit", 0)) or 0)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (out / "server_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return summary


__all__ = [
    "SCHEMA_LEAN_WORKER_SUPERVISOR",
    "enqueue_and_run_supervised_audit",
    "materialize_queue_results",
    "run_bulk_audit_queue",
    "run_supervised_audit_queue",
]
