from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .action_quarantine import action_quarantine_report, export_quarantined_actions
from .active_audit_scheduler import SchedulerConfig, _read_json_or_file, active_audit_schedule_from_files
from .audit_env_profile import profile_audit_environment
from .audit_job_queue import audit_queue_status, enqueue_audit_jobs, init_audit_queue_db, project_fingerprint
from .batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW, run_micro_audit_batch
from .bulk_executor import BulkAuditConfig, bulk_audit_to_files
from .cli_common import (
    _actions_for_tasks,
    _executor_from_args,
    _load_actions_grouped,
    _load_tasks,
    _normalize_tasks_imports,
    _server_config_from_args,
    add_exec_args,
)
from .defects import ProofDefectExtractor
from .executor import LeanExecutorConfig
from .lean_server import audit_with_lean_server
from .lean_worker_supervisor import run_bulk_audit_queue, run_supervised_audit_queue
from .schemas import ProofState, ResponseRecord, read_jsonl, stable_hash, write_records
from .timeout_ledger import timeout_ledger_report


def summarize_responses(responses: list[dict[str, Any]]) -> dict[str, Any]:
    if not responses:
        return {"n": 0}
    statuses: dict[str, int] = {}
    norms: list[float] = []
    carrier_deltas: list[float] = []
    goal_responses: list[float] = []
    for row in responses:
        status = str(row.get("audit_status", row.get("status", "unknown")))
        statuses[status] = statuses.get(status, 0) + 1
        norms.append(float(np.linalg.norm(np.asarray(row.get("response_flat", []), dtype=float))))
        carrier_delta = row.get("carrier_delta", {}) or {}
        carrier_deltas.append(sum(float(v) for v in carrier_delta.values()))
        response = row.get("response", {}) or {}
        goal_responses.append(sum(float(v) for k, v in response.items() if str(k).startswith("goal.")))
    return {
        "n": len(responses),
        "statuses": statuses,
        "success_rate": statuses.get("success", 0) / max(1, len(responses)),
        "mean_response_norm": float(np.mean(norms)),
        "max_response_norm": float(np.max(norms)),
        "mean_goal_response": float(np.mean(goal_responses)),
        "mean_carrier_delta": float(np.mean(carrier_deltas)),
    }


def _audit_loop(tasks, actions_by_task, executor, extractor):
    audits = []
    responses = []
    defects = []
    for task in tasks:
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        defects.append({"state_id": state.state_id, "task_id": task.task_id, "target": task.statement, **before.to_dict()})
        actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
        for action in actions:
            rec = executor.run_tactic(task, action, state)
            after = extractor.extract(rec.after_state or state, rec)
            resp, flat, keys = extractor.response(before, after)
            rec.defect_before = before.to_dict()
            rec.defect_after = after.to_dict()
            rec.response = resp
            rec.carrier_delta = {
                k: before.carrier.get(k, 0.0) - after.carrier.get(k, 0.0)
                for k in sorted(set(before.carrier) | set(after.carrier))
            }
            audits.append(rec.to_dict())
            rr = ResponseRecord(
                state_id=state.state_id,
                action_id=action.action_id,
                response=resp,
                response_flat=flat,
                response_keys=keys,
                defect_before=before,
                defect_after=after,
                audit_status=rec.status,
                carrier_delta=rec.carrier_delta,
            ).to_dict()
            rr.update({"task_id": task.task_id, "target": task.statement, "action": action.to_dict()})
            responses.append(rr)
    return audits, responses, defects


def cmd_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    trimmed = {k: v[: args.max_actions] for k, v in acts.items()} if isinstance(acts, dict) else acts[: args.max_actions]
    if getattr(args, "lean_server", False):
        cfg = _server_config_from_args(args)
        summary = audit_with_lean_server(
            tasks,
            trimmed,
            out_dir=args.out,
            server_config=cfg,
            max_actions=args.max_actions,
            resume=args.resume,
            flush_every=args.flush_every,
            run_id=getattr(args, "run_id", None),
        )
        responses = read_jsonl(Path(args.out) / "responses.jsonl") if (Path(args.out) / "responses.jsonl").exists() else []
        summary.update(summarize_responses(responses))
        (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    audits, responses, defects = _audit_loop(tasks, trimmed, _executor_from_args(args), ProofDefectExtractor())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run_id = getattr(args, "run_id", None)
    write_records(out / "micro_audit.jsonl", audits, schema_version=SCHEMA_AUDIT_ROW, run_id=run_id)
    write_records(out / "responses.jsonl", responses, schema_version=SCHEMA_RESPONSE_ROW, run_id=run_id)
    write_records(out / "defects.jsonl", defects, schema_version=SCHEMA_DEFECT_ROW, run_id=run_id)
    summary = summarize_responses(responses)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_batch_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    cfg = LeanExecutorConfig(
        lean_cmd=args.lean_cmd,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
        keep_files=args.keep_files,
        workdir=args.workdir,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
    )
    summary = run_micro_audit_batch(
        tasks,
        acts,
        out_dir=args.out,
        executor_config=cfg,
        max_actions=args.max_actions,
        jobs=getattr(args, "jobs", 1),
        resume=args.resume,
        flush_every=args.flush_every,
        run_id=getattr(args, "run_id", None),
    )
    responses = read_jsonl(Path(args.out) / "responses.jsonl") if (Path(args.out) / "responses.jsonl").exists() else []
    summary.update(summarize_responses(responses))
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_bulk_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    trimmed = {k: v[: args.max_actions] for k, v in acts.items()}
    cfg = BulkAuditConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        batch_size=args.batch_size,
        keep_files=args.keep_files,
        trace_state=args.trace_state,
    )
    rep = bulk_audit_to_files(tasks, trimmed, args.out, cfg, run_id=getattr(args, "run_id", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_env_profile(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    keep_dir = getattr(args, "keep_files_dir", None)
    rep = profile_audit_environment(
        tasks=tasks,
        actions_by_task=acts,
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        out_json=args.out,
        keep_files_dir=keep_dir,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_server_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    cfg = _server_config_from_args(args)
    summary = audit_with_lean_server(
        tasks,
        acts,
        out_dir=args.out,
        server_config=cfg,
        max_actions=args.max_actions,
        resume=args.resume,
        flush_every=args.flush_every,
        run_id=getattr(args, "run_id", None),
    )
    responses = read_jsonl(Path(args.out) / "responses.jsonl") if (Path(args.out) / "responses.jsonl").exists() else []
    summary.update(summarize_responses(responses))
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_queue_init(args):
    rep = init_audit_queue_db(args.db)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_queue_enqueue(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    backend = args.backend or args.lane
    fp = project_fingerprint(lean_cmd=args.lean_cmd, workdir=args.workdir, backend=backend, import_mode=args.import_mode)
    rep = enqueue_audit_jobs(
        args.db,
        tasks,
        acts,
        run_id=args.run_id,
        backend=backend,
        import_mode=args.import_mode,
        project_fingerprint_value=fp,
        max_actions=args.max_actions,
        max_attempts=args.max_attempts,
        lane=args.lane,
        priority=args.priority,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_queue_run(args):
    run_id = args.run_id
    if getattr(args, "tasks", None) and getattr(args, "actions", None):
        run_id = run_id or ("run_" + stable_hash({"tasks": args.tasks, "actions": args.actions, "out": args.out}, 20))
        tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
        base, by_task = _load_actions_grouped(args.actions)
        acts = _actions_for_tasks(
            tasks,
            base,
            by_task,
            state_candidates=args.state_candidates or not (base or by_task),
            candidate_mode=args.candidate_mode,
            max_candidates=args.max_actions,
        )
        backend = args.backend or args.lane
        fp = project_fingerprint(lean_cmd=args.lean_cmd, workdir=args.workdir, backend=backend, import_mode=args.import_mode)
        enqueue_audit_jobs(
            args.db,
            tasks,
            acts,
            run_id=run_id,
            backend=backend,
            import_mode=args.import_mode,
            project_fingerprint_value=fp,
            max_actions=args.max_actions,
            max_attempts=args.max_attempts,
            lane=args.lane,
        )
    effective_queue_timeout_s = float(args.job_timeout_s or args.timeout_s)
    if getattr(args, "queue_backend", "file") == "bulk" and not args.keep_files and not args.dry_run:
        effective_queue_timeout_s = max(effective_queue_timeout_s, 60.0)
    cfg = LeanExecutorConfig(
        lean_cmd=args.lean_cmd,
        timeout_s=effective_queue_timeout_s,
        dry_run=args.dry_run,
        keep_files=args.keep_files,
        workdir=args.workdir,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
    )
    if getattr(args, "queue_backend", "file") == "bulk" and not args.keep_files and not args.dry_run:
        rep = run_bulk_audit_queue(
            db_path=args.db,
            out_dir=args.out,
            executor_config=cfg,
            run_id=run_id,
            workers=args.workers,
            job_timeout_s=effective_queue_timeout_s,
            max_jobs=args.max_jobs,
            lanes=[args.lane] if args.lane else None,
            batch_size=getattr(args, "bulk_batch_size", 32),
            import_mode=args.import_mode,
        )
    else:
        rep = run_supervised_audit_queue(
            db_path=args.db,
            out_dir=args.out,
            executor_config=cfg,
            run_id=run_id,
            workers=args.workers,
            job_timeout_s=effective_queue_timeout_s,
            max_jobs=args.max_jobs,
            continue_on_timeout=args.continue_on_timeout,
            lanes=[args.lane] if args.lane else None,
        )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_queue_status(args):
    rep = audit_queue_status(args.db, run_id=getattr(args, "run_id", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_timeout_ledger_report(args):
    rep = timeout_ledger_report(args.db, out_json=getattr(args, "out_json", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_action_quarantine_report(args):
    rep = action_quarantine_report(args.db, refresh=not getattr(args, "no_refresh", False), out_json=getattr(args, "out_json", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_action_quarantine_export(args):
    rep = export_quarantined_actions(args.db, args.out, refresh=not getattr(args, "no_refresh", False))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_schedule(args):
    response_normal = _read_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    carrier_normal = _read_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    cfg = SchedulerConfig(
        top_k=getattr(args, "top_k", None) or getattr(args, "budget", 32),
        per_task_cap=getattr(args, "max_per_task", None) or getattr(args, "per_task_cap", None),
        response_weight=getattr(args, "coker_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 0.5),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.25),
        novelty_weight=getattr(args, "novelty_weight", 0.25),
        success_weight=getattr(args, "success_weight", 0.25),
        cost_weight=getattr(args, "cost_weight", 0.10),
        timeout_weight=getattr(args, "audit_risk_weight", getattr(args, "timeout_weight", 0.5)),
        min_score=getattr(args, "min_score", None) or getattr(args, "min_priority", None),
    )
    report = active_audit_schedule_from_files(
        candidates_path=getattr(args, "candidates"),
        out_actions=getattr(args, "out", None) or getattr(args, "out_actions"),
        out_rows=getattr(args, "out_rows", None) or getattr(args, "out_schedule", None),
        out_report=getattr(args, "report_out", None) or getattr(args, "out_report", None),
        db_path=getattr(args, "db", None),
        response_paths=[getattr(args, "responses")] if getattr(args, "responses", None) else getattr(args, "history_responses", None),
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        config=cfg,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def register_audit_commands(sub) -> None:
    audit = sub.add_parser("audit")
    audit.add_argument("--tasks", required=True)
    audit.add_argument("--actions")
    audit.add_argument("--out", required=True)
    add_exec_args(audit)
    audit.set_defaults(func=cmd_audit)

    batch = sub.add_parser("batch-audit")
    batch.add_argument("--tasks", required=True)
    batch.add_argument("--actions")
    batch.add_argument("--out", required=True)
    batch.add_argument("--jobs", type=int, default=4)
    add_exec_args(batch)
    batch.set_defaults(func=cmd_batch_audit)

    bulk = sub.add_parser("bulk-audit")
    bulk.add_argument("--tasks", required=True)
    bulk.add_argument("--actions")
    bulk.add_argument("--out", required=True)
    bulk.add_argument("--batch-size", type=int, default=64)
    bulk.add_argument("--lean-cmd", default="lake env lean")
    bulk.add_argument("--workdir")
    bulk.add_argument("--timeout-s", type=float, default=120.0)
    bulk.add_argument("--keep-files", action="store_true")
    bulk.add_argument("--trace-state", action="store_true")
    bulk.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    bulk.add_argument("--max-actions", type=int, default=64)
    bulk.add_argument("--candidate-mode", choices=["basic", "state"], default="state")
    bulk.add_argument("--state-candidates", action="store_true")
    bulk.set_defaults(func=cmd_bulk_audit)

    profile = sub.add_parser("audit-env-profile")
    profile.add_argument("--tasks", required=True)
    profile.add_argument("--actions")
    profile.add_argument("--out", required=True)
    profile.add_argument("--lean-cmd", default="lake env lean")
    profile.add_argument("--workdir")
    profile.add_argument("--timeout-s", type=float, default=120.0)
    profile.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    profile.add_argument("--max-actions", type=int, default=64)
    profile.add_argument("--candidate-mode", choices=["basic", "state"], default="state")
    profile.add_argument("--state-candidates", action="store_true")
    profile.add_argument("--keep-files-dir")
    profile.set_defaults(func=cmd_audit_env_profile)

    server = sub.add_parser("server-audit")
    server.add_argument("--tasks", required=True)
    server.add_argument("--actions")
    server.add_argument("--out", required=True)
    server.add_argument("--jobs", type=int, default=1)
    add_exec_args(server)
    server.set_defaults(func=cmd_server_audit)

    aqinit = sub.add_parser("audit-queue-init")
    aqinit.add_argument("--db", required=True)
    aqinit.set_defaults(func=cmd_audit_queue_init)

    aqenq = sub.add_parser("audit-queue-enqueue")
    aqenq.add_argument("--db", required=True)
    aqenq.add_argument("--tasks", required=True)
    aqenq.add_argument("--actions")
    aqenq.add_argument("--run-id", required=True)
    aqenq.add_argument("--backend", default="source_check")
    aqenq.add_argument("--lane", choices=["source_check", "kernel_rpc", "heavy"], default="source_check")
    aqenq.add_argument("--lean-cmd", default="lake env lean")
    aqenq.add_argument("--workdir")
    aqenq.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    aqenq.add_argument("--max-actions", type=int, default=64)
    aqenq.add_argument("--max-attempts", type=int, default=1)
    aqenq.add_argument("--priority", type=float, default=0.0)
    aqenq.add_argument("--candidate-mode", choices=["basic", "state"], default="state")
    aqenq.add_argument("--state-candidates", action="store_true")
    aqenq.set_defaults(func=cmd_audit_queue_enqueue)

    aqrun = sub.add_parser("audit-queue-run")
    aqrun.add_argument("--db", required=True)
    aqrun.add_argument("--out", required=True)
    aqrun.add_argument("--run-id")
    aqrun.add_argument("--tasks")
    aqrun.add_argument("--actions")
    aqrun.add_argument("--backend", default="source_check")
    aqrun.add_argument("--lane", choices=["source_check", "kernel_rpc", "heavy"], default="source_check")
    aqrun.add_argument("--queue-backend", choices=["file", "bulk"], default="bulk")
    aqrun.add_argument("--bulk-batch-size", type=int, default=32)
    aqrun.add_argument("--workers", type=int, default=6)
    aqrun.add_argument("--job-timeout-s", type=float)
    aqrun.add_argument("--max-jobs", type=int)
    aqrun.add_argument("--max-actions", type=int, default=64)
    aqrun.add_argument("--max-attempts", type=int, default=1)
    aqrun.add_argument("--continue-on-timeout", action="store_true", default=True)
    aqrun.add_argument("--lean-cmd", default="lake env lean")
    aqrun.add_argument("--workdir")
    aqrun.add_argument("--timeout-s", type=float, default=20.0)
    aqrun.add_argument("--dry-run", action="store_true")
    aqrun.add_argument("--keep-files", action="store_true")
    aqrun.add_argument("--cache-dir")
    aqrun.add_argument("--trace-state", action="store_true")
    aqrun.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    aqrun.add_argument("--candidate-mode", choices=["basic", "state"], default="state")
    aqrun.add_argument("--state-candidates", action="store_true")
    aqrun.set_defaults(func=cmd_audit_queue_run)

    aqst = sub.add_parser("audit-queue-status")
    aqst.add_argument("--db", required=True)
    aqst.add_argument("--run-id")
    aqst.set_defaults(func=cmd_audit_queue_status)

    tlr = sub.add_parser("timeout-ledger-report")
    tlr.add_argument("--db", required=True)
    tlr.add_argument("--out-json")
    tlr.set_defaults(func=cmd_timeout_ledger_report)

    aqr = sub.add_parser("action-quarantine-report")
    aqr.add_argument("--db", required=True)
    aqr.add_argument("--out-json")
    aqr.add_argument("--no-refresh", action="store_true")
    aqr.set_defaults(func=cmd_action_quarantine_report)

    aqx = sub.add_parser("action-quarantine-export")
    aqx.add_argument("--db", required=True)
    aqx.add_argument("--out", required=True)
    aqx.add_argument("--no-refresh", action="store_true")
    aqx.set_defaults(func=cmd_action_quarantine_export)

    schedule = sub.add_parser("audit-schedule")
    schedule.add_argument("--db")
    schedule.add_argument("--candidates", required=True)
    schedule.add_argument("--out", dest="out", required=False)
    schedule.add_argument("--out-actions", dest="out_actions")
    schedule.add_argument("--out-rows")
    schedule.add_argument("--report-out")
    schedule.add_argument("--top-k", type=int, default=32)
    schedule.add_argument("--max-per-task", type=int)
    schedule.add_argument("--min-score", type=float)
    schedule.add_argument("--coker-weight", type=float, default=1.0)
    schedule.add_argument("--carrier-weight", type=float, default=0.5)
    schedule.add_argument("--novelty-weight", type=float, default=0.25)
    schedule.add_argument("--uncertainty-weight", type=float, default=0.25)
    schedule.add_argument("--success-weight", type=float, default=0.25)
    schedule.add_argument("--cost-weight", type=float, default=0.10)
    schedule.add_argument("--carrier-violation-weight", type=float, default=0.75)
    schedule.add_argument("--prior-weight", type=float, default=1.0)
    schedule.add_argument("--response-normal")
    schedule.add_argument("--carrier-normal")
    schedule.set_defaults(func=cmd_audit_schedule)


__all__ = [
    "cmd_action_quarantine_export",
    "cmd_action_quarantine_report",
    "cmd_audit",
    "cmd_audit_env_profile",
    "cmd_audit_queue_enqueue",
    "cmd_audit_queue_init",
    "cmd_audit_queue_run",
    "cmd_audit_queue_status",
    "cmd_audit_schedule",
    "cmd_batch_audit",
    "cmd_bulk_audit",
    "cmd_server_audit",
    "cmd_timeout_ledger_report",
    "register_audit_commands",
    "summarize_responses",
]
