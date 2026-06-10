from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import (
    _executor_from_args,
    _load_tasks,
    _normalize_tasks_imports,
    _server_config_from_args,
    add_exec_args,
)
from ..defects import ProofDefectExtractor
from ..lean import (
    FrontierAuditor,
    KernelGoalStateServer,
    KernelGoalStateServerConfig,
    LeanServerAdapter,
    LeanServerConfig,
    PersistentLeanWorker,
    WorkerConfig,
    goal_state_transitions_from_audits,
    kernel_state_graphs_from_jsonl,
    normalize_kernel_state_v1,
    run_persistent_worker,
    structured_state_extract_cli,
)
from ..schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl


def _server_from_args(args: argparse.Namespace) -> LeanServerAdapter:
    return LeanServerAdapter(_server_config_from_args(args))


def cmd_lean_server_audit(args: argparse.Namespace) -> int:
    # Backward-compatible alias for v21 server-audit.
    from .audit import cmd_server_audit

    return cmd_server_audit(args)


def cmd_persistent_worker(args: argparse.Namespace) -> int:
    from ..persistent_lean_worker import main as worker_main

    argv = ["--backend", args.backend, "--lean-cmd", args.lean_cmd, "--timeout-s", str(args.timeout_s)]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if args.keep_files:
        argv += ["--keep-files"]
    if args.cache_dir:
        argv += ["--cache-dir", args.cache_dir]
    if args.trace_state:
        argv += ["--trace-state"]
    if args.no_warmup:
        argv += ["--no-warmup"]
    return worker_main(argv)


def cmd_persistent_state_demo(args: argparse.Namespace) -> int:
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    actions = [TacticAction.from_dict(r) for r in read_jsonl(args.actions)]
    worker = PersistentLeanWorker(
        WorkerConfig(
            backend="dry_run" if args.dry_run else "file",
            lean_cmd=args.lean_cmd,
            workdir=args.workdir,
            timeout_s=args.timeout_s,
            keep_files=args.keep_files,
            trace_state=args.trace_state,
        )
    )
    worker.load_project()
    base = worker.register_task(task)["state"]
    current = base["state_id"]
    rows = []
    for action in actions[: args.max_actions]:
        rep = worker.apply_tactic(action=action, state_id=current)
        rows.append(rep)
        after = rep.get("after_state") or {}
        if rep.get("audit", {}).get("status") in {"success", "partial", "dry_run"} and after.get("state_id"):
            current = after["state_id"]
        if rep.get("audit", {}).get("status") == "success":
            break
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "base_state": base,
                "final_state_id": current,
                "states": worker.list_states(),
                "steps": rows,
                "status": worker.status(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"out": str(out), "n_steps": len(rows), "n_states": len(worker.states)}, indent=2, ensure_ascii=False))
    return 0


def cmd_goal_state_transitions(args: argparse.Namespace) -> int:
    report = goal_state_transitions_from_audits(args.audits, out_path=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_graphs(args: argparse.Namespace) -> int:
    report = kernel_state_graphs_from_jsonl(args.kernel_jsonl, out_path=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_normalize(args: argparse.Namespace) -> int:
    rows = read_jsonl(args.kernel_jsonl)
    out_rows = []
    for row in rows:
        kernel = row.get("kernel_state") if isinstance(row, dict) and isinstance(row.get("kernel_state"), dict) else row
        if isinstance(kernel, dict):
            out_rows.append(normalize_kernel_state_v1(kernel))
    write_jsonl(args.out, out_rows)
    report = {
        "schema_version": "lean-rgc-kernel-state-normalize-v1",
        "n_input_rows": len(rows),
        "n_kernel_states": len(out_rows),
        "mean_expr_nodes": sum(int((r.get("expr_graph") or {}).get("n_nodes", 0) or 0) for r in out_rows) / max(1, len(out_rows)),
        "canonical_status": "kernel_state_normalize_report_not_canonical",
        "files": {"kernel_states": str(args.out)},
    }
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_probe(args: argparse.Namespace) -> int:
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    action = TacticAction.from_dict(json.loads(Path(args.action_json).read_text(encoding="utf-8")))
    cfg = KernelGoalStateServerConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        backend=args.backend,
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
        kernel_state_mode=getattr(args, "kernel_state_mode", "features"),
    )
    server = KernelGoalStateServer(cfg)
    init = server.register_task(task)
    transition = server.apply_tactic(init["state"]["state_id"], action)
    out = {"status": server.status(), "initial": init, "transition": transition}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_structured_state_extract(args: argparse.Namespace) -> int:
    summary = structured_state_extract_cli(
        tasks=getattr(args, "tasks", None),
        audits=getattr(args, "audits", None),
        kernel_jsonl=getattr(args, "kernel_jsonl", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_frontier_audit(args: argparse.Namespace) -> int:
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    executor = _executor_from_args(args)
    summary = FrontierAuditor(executor, ProofDefectExtractor()).run(
        tasks,
        out_dir=args.out,
        max_exposures=args.max_exposures,
        max_core_actions=args.max_core_actions,
        include_identity=not args.no_identity,
    )
    print(json.dumps(summary.to_dict() if hasattr(summary, "to_dict") else summary, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_worker(args: argparse.Namespace) -> int:
    # Backward-compatible alias for the v27 persistent JSONL worker.
    from ..persistent_lean_worker import main as worker_main

    argv = ["--backend", "dry_run" if args.dry_run else "file", "--lean-cmd", args.lean_cmd, "--timeout-s", str(args.timeout_s)]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if args.keep_files:
        argv += ["--keep-files"]
    if args.cache_dir:
        argv += ["--cache-dir", args.cache_dir]
    if args.trace_state:
        argv += ["--trace-state"]
    return worker_main(argv)


def cmd_lean_native_worker(args: argparse.Namespace) -> int:
    from ..native_worker import main as native_main

    argv = ["--lean-cmd", args.lean_cmd, "--exec-mode", getattr(args, "exec_mode", "source_check")]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if getattr(args, "worker_path", None):
        argv += ["--worker-path", args.worker_path]
    # Backward-compatible aliases from the previous source-emitting shim.
    if getattr(args, "source_path", None):
        argv += ["--worker-path", args.source_path]
    if getattr(args, "emit_source", None):
        argv += ["--source-out", args.emit_source]
    if getattr(args, "source_out", None):
        argv += ["--source-out", args.source_out]
    if getattr(args, "manifest_out", None):
        argv += ["--manifest-out", args.manifest_out]
    if getattr(args, "print_source", False):
        argv += ["--print-source"]
    if getattr(args, "print_command", False):
        argv += ["--print-command"]
    if getattr(args, "keep_source", False):
        argv += ["--keep-source"]
    if getattr(args, "force", False):
        argv += ["--force"]
    return native_main(argv)


def cmd_lean_server_probe(args: argparse.Namespace) -> int:
    with _server_from_args(args) as server:
        out = server.health()
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_server_health(args: argparse.Namespace) -> int:
    with _server_from_args(args) as server:
        out = {"health": server.health()}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_server_apply(args: argparse.Namespace) -> int:
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    action = TacticAction.from_dict(json.loads(Path(args.action_json).read_text(encoding="utf-8")))
    state = None
    if getattr(args, "state_json", None):
        state = ProofState.from_dict(json.loads(Path(args.state_json).read_text(encoding="utf-8")))
    with _server_from_args(args) as server:
        rec = server.run_tactic(task, action, state)
        structured_state = server.structured_state(task, rec.after_state or ProofState.from_task(task), rec)
        out = {"record": rec.to_dict(), "structured_state": structured_state, "health": server.info.to_dict()}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_persistent_worker(args: argparse.Namespace) -> int:
    cfg = LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
        backend="persistent",
    )
    return run_persistent_worker(cfg)


def cmd_lean_persistent_probe(args: argparse.Namespace) -> int:
    cfg = LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
    )
    worker = PersistentLeanWorker(cfg)
    status = worker.load_project()
    task = LeanTask.from_dict({"task_id": "persistent_probe", "statement": "\u0403\u041d n : Nat, n = n", "imports": ["Init"]})
    init = worker.init_state(task)
    intro = TacticAction(action_id="intro", tactic="intro n", tactic_class="intro")
    r1 = worker.apply_tactic(task, intro, state_id=init["state"]["state_id"])
    branch = worker.branch_state(r1.get("after_state", init["state"])["state_id"] if r1.get("after_state") else init["state"]["state_id"])
    rfl = TacticAction(action_id="rfl", tactic="rfl", tactic_class="rfl")
    r2 = worker.apply_tactic(task, rfl, state_id=branch["state"]["state_id"])
    out = {
        "status": status,
        "init_state": init["state"],
        "intro_status": (r1.get("audit") or {}).get("status"),
        "branch_state": branch.get("state"),
        "rfl_status": (r2.get("audit") or {}).get("status"),
        "n_states": len(worker.states),
        "canonical_status": "persistent_worker_probe_chart_only_not_kernel_canonical",
    }
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    else:
        print(json.dumps(out, ensure_ascii=True, indent=2))
    return 0


def register_lean_commands(subparsers: argparse._SubParsersAction) -> None:
    lsh = subparsers.add_parser("lean-server-health")
    lsh.add_argument("--out")
    lsh.add_argument("--lean-cmd", default="lake env lean")
    lsh.add_argument("--workdir")
    lsh.add_argument("--timeout-s", type=float, default=20.0)
    lsh.add_argument("--dry-run", action="store_true")
    lsh.add_argument("--keep-files", action="store_true")
    lsh.add_argument("--cache-dir")
    lsh.add_argument("--trace-state", action="store_true")
    lsh.add_argument("--server-cmd")
    lsh.add_argument("--server-no-fallback", action="store_true")
    lsh.add_argument("--lean-server-backend", choices=["file", "dry", "jsonl", "persistent", "native"], default=None)
    lsh.set_defaults(func=cmd_lean_server_health)

    lsa = subparsers.add_parser("lean-server-apply")
    lsa.add_argument("--task-json", required=True)
    lsa.add_argument("--action-json", required=True)
    lsa.add_argument("--state-json")
    lsa.add_argument("--out")
    lsa.add_argument("--lean-cmd", default="lake env lean")
    lsa.add_argument("--workdir")
    lsa.add_argument("--timeout-s", type=float, default=20.0)
    lsa.add_argument("--dry-run", action="store_true")
    lsa.add_argument("--keep-files", action="store_true")
    lsa.add_argument("--cache-dir")
    lsa.add_argument("--trace-state", action="store_true")
    lsa.add_argument("--server-cmd")
    lsa.add_argument("--server-no-fallback", action="store_true")
    lsa.add_argument("--native-exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    lsa.add_argument("--request-timeout-s", type=float)
    lsa.add_argument("--lean-server-backend", choices=["auto", "dry_run", "file_fallback", "file", "dry", "jsonl", "persistent", "native"], default=None)
    lsa.set_defaults(func=cmd_lean_server_apply)

    fa = subparsers.add_parser("frontier-audit")
    fa.add_argument("--tasks", required=True)
    fa.add_argument("--out", required=True)
    fa.add_argument("--lean-cmd", default="lake env lean")
    fa.add_argument("--workdir")
    fa.add_argument("--timeout-s", type=float, default=20.0)
    fa.add_argument("--dry-run", action="store_true")
    fa.add_argument("--keep-files", action="store_true")
    fa.add_argument("--cache-dir")
    fa.add_argument("--trace-state", action="store_true")
    fa.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    fa.add_argument("--max-exposures", type=int, default=4)
    fa.add_argument("--max-core-actions", type=int, default=12)
    fa.add_argument("--no-identity", action="store_true")
    fa.set_defaults(func=cmd_frontier_audit)

    lw = subparsers.add_parser("lean-worker")
    lw.add_argument("--lean-cmd", default="lake env lean")
    lw.add_argument("--workdir")
    lw.add_argument("--timeout-s", type=float, default=20.0)
    lw.add_argument("--dry-run", action="store_true")
    lw.add_argument("--keep-files", action="store_true")
    lw.add_argument("--cache-dir")
    lw.add_argument("--trace-state", action="store_true")
    lw.add_argument("--session-id")
    lw.set_defaults(func=cmd_lean_worker)

    lpw = subparsers.add_parser("lean-persistent-worker")
    lpw.add_argument("--lean-cmd", default="lake env lean")
    lpw.add_argument("--workdir")
    lpw.add_argument("--timeout-s", type=float, default=20.0)
    lpw.add_argument("--dry-run", action="store_true")
    lpw.add_argument("--keep-files", action="store_true")
    lpw.add_argument("--cache-dir")
    lpw.add_argument("--trace-state", action="store_true")
    lpw.set_defaults(func=cmd_lean_persistent_worker)

    lpp = subparsers.add_parser("lean-persistent-probe")
    lpp.add_argument("--out")
    lpp.add_argument("--lean-cmd", default="lake env lean")
    lpp.add_argument("--workdir")
    lpp.add_argument("--timeout-s", type=float, default=20.0)
    lpp.add_argument("--dry-run", action="store_true")
    lpp.add_argument("--keep-files", action="store_true")
    lpp.add_argument("--cache-dir")
    lpp.add_argument("--trace-state", action="store_true")
    lpp.set_defaults(func=cmd_lean_persistent_probe)

    lnw = subparsers.add_parser("lean-native-worker")
    lnw.add_argument("--lean-cmd", default="lake env lean")
    lnw.add_argument("--exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    lnw.add_argument("--workdir")
    lnw.add_argument("--worker-path")
    lnw.add_argument("--source-path")
    lnw.add_argument("--emit-source")
    lnw.add_argument("--source-out")
    lnw.add_argument("--manifest-out")
    lnw.add_argument("--print-source", action="store_true")
    lnw.add_argument("--print-command", action="store_true")
    lnw.add_argument("--keep-source", action="store_true")
    lnw.add_argument("--force", action="store_true")
    lnw.set_defaults(func=cmd_lean_native_worker)

    nlw = subparsers.add_parser("native-lean-worker")
    nlw.add_argument("--lean-cmd", default="lake env lean")
    nlw.add_argument("--exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    nlw.add_argument("--workdir")
    nlw.add_argument("--worker-path")
    nlw.add_argument("--source-out")
    nlw.add_argument("--manifest-out")
    nlw.add_argument("--print-source", action="store_true")
    nlw.add_argument("--print-command", action="store_true")
    nlw.add_argument("--keep-source", action="store_true")
    nlw.add_argument("--force", action="store_true")
    nlw.set_defaults(func=cmd_lean_native_worker)

    srvp = subparsers.add_parser("lean-server-probe")
    srvp.add_argument("--out")
    srvp.add_argument("--lean-cmd", default="lake env lean")
    srvp.add_argument("--workdir")
    srvp.add_argument("--timeout-s", type=float, default=20.0)
    srvp.add_argument("--dry-run", action="store_true")
    srvp.add_argument("--keep-files", action="store_true")
    srvp.add_argument("--cache-dir")
    srvp.add_argument("--trace-state", action="store_true")
    srvp.add_argument("--server-cmd")
    srvp.add_argument("--server-backend", choices=["auto", "dry_run", "file", "file_fallback", "jsonl", "persistent", "native"], default="auto")
    srvp.add_argument("--server-no-fallback", action="store_true")
    srvp.add_argument("--native-exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    srvp.set_defaults(func=cmd_lean_server_probe)

    lsa = subparsers.add_parser("lean-server-audit")
    lsa.add_argument("--tasks", required=True)
    lsa.add_argument("--actions")
    lsa.add_argument("--out", required=True)
    lsa.add_argument("--jobs", type=int, default=1, help="Reserved for future multi-worker server backend; current adapter is sequential.")
    lsa.add_argument("--server-backend", choices=["auto", "dry_run", "file_fallback", "file", "dry", "jsonl", "persistent", "native"], default=None)
    lsa.add_argument("--server-cmd")
    lsa.add_argument("--server-no-fallback", action="store_true")
    lsa.add_argument("--native-exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    lsa.add_argument("--request-timeout-s", type=float)
    lsa.add_argument("--no-warmup", action="store_true")
    add_exec_args(lsa)
    lsa.set_defaults(func=cmd_lean_server_audit)

    pw = subparsers.add_parser("persistent-worker")
    pw.add_argument("--backend", choices=["dry_run", "dry", "file"], default="dry_run")
    pw.add_argument("--lean-cmd", default="lake env lean")
    pw.add_argument("--workdir")
    pw.add_argument("--timeout-s", type=float, default=20.0)
    pw.add_argument("--keep-files", action="store_true")
    pw.add_argument("--cache-dir")
    pw.add_argument("--trace-state", action="store_true")
    pw.add_argument("--no-warmup", action="store_true")
    pw.set_defaults(func=cmd_persistent_worker)

    psd = subparsers.add_parser("persistent-state-demo")
    psd.add_argument("--task-json", required=True)
    psd.add_argument("--actions", required=True)
    psd.add_argument("--out", required=True)
    psd.add_argument("--lean-cmd", default="lake env lean")
    psd.add_argument("--workdir")
    psd.add_argument("--timeout-s", type=float, default=20.0)
    psd.add_argument("--dry-run", action="store_true")
    psd.add_argument("--keep-files", action="store_true")
    psd.add_argument("--trace-state", action="store_true")
    psd.add_argument("--max-actions", type=int, default=8)
    psd.set_defaults(func=cmd_persistent_state_demo)

    sse = subparsers.add_parser("structured-state-extract")
    sse.add_argument("--tasks")
    sse.add_argument("--audits")
    sse.add_argument("--kernel-jsonl")
    sse.add_argument("--out", required=True)
    sse.add_argument("--summary-out")
    sse.set_defaults(func=cmd_structured_state_extract)

    gst = subparsers.add_parser("goal-state-transitions")
    gst.add_argument("--audits", required=True)
    gst.add_argument("--out", required=True)
    gst.add_argument("--summary-out")
    gst.set_defaults(func=cmd_goal_state_transitions)

    ksg = subparsers.add_parser("kernel-state-graphs")
    ksg.add_argument("--kernel-jsonl", required=True)
    ksg.add_argument("--out", required=True)
    ksg.add_argument("--summary-out")
    ksg.set_defaults(func=cmd_kernel_state_graphs)

    ksn = subparsers.add_parser("kernel-state-normalize")
    ksn.add_argument("--kernel-jsonl", required=True)
    ksn.add_argument("--out", required=True)
    ksn.add_argument("--summary-out")
    ksn.set_defaults(func=cmd_kernel_state_normalize)

    ksp = subparsers.add_parser("kernel-state-probe")
    ksp.add_argument("--task-json", required=True)
    ksp.add_argument("--action-json", required=True)
    ksp.add_argument("--out")
    ksp.add_argument("--backend", choices=["dry_run", "file"], default="dry_run")
    ksp.add_argument("--lean-cmd", default="lake env lean")
    ksp.add_argument("--workdir")
    ksp.add_argument("--timeout-s", type=float, default=20.0)
    ksp.add_argument("--keep-files", action="store_true")
    ksp.add_argument("--cache-dir")
    ksp.add_argument("--trace-state", action="store_true")
    ksp.add_argument("--kernel-state-mode", choices=["none", "summary", "features", "full"], default="features")
    ksp.set_defaults(func=cmd_kernel_state_probe)


__all__ = [
    "cmd_frontier_audit",
    "cmd_goal_state_transitions",
    "cmd_kernel_state_graphs",
    "cmd_kernel_state_normalize",
    "cmd_kernel_state_probe",
    "cmd_lean_native_worker",
    "cmd_lean_persistent_probe",
    "cmd_lean_persistent_worker",
    "cmd_lean_server_apply",
    "cmd_lean_server_audit",
    "cmd_lean_server_health",
    "cmd_lean_server_probe",
    "cmd_lean_worker",
    "cmd_persistent_state_demo",
    "cmd_persistent_worker",
    "cmd_structured_state_extract",
    "register_lean_commands",
]
