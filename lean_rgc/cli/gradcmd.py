from __future__ import annotations

import json

from ..schemas import LeanTask, read_jsonl


def cmd_grad_smoke(args):
    from ..grad.config import GradInvariants
    from ..grad.engine import RolloutEngine

    inv = GradInvariants(model_name=args.model) if args.model else GradInvariants()
    engine = RolloutEngine(inv)
    report = engine.smoke(batch_sizes=tuple(args.batch_sizes))
    report["invariants"] = inv.to_dict()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def cmd_grad_loop(args):
    from ..grad.config import GradInvariants
    from ..grad.engine import run_grad_loop
    from ..lean.executor import LeanExecutorConfig

    tasks = [LeanTask.from_dict(r) for r in read_jsonl(args.tasks) if isinstance(r, dict)]
    inv = GradInvariants(model_name=args.model) if args.model else GradInvariants()
    summary = run_grad_loop(
        tasks=tasks,
        out_dir=args.out_dir,
        run_id=args.run_id,
        invariants=inv,
        n_waves=args.n_waves,
        executor_config=LeanExecutorConfig(
            lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.task_timeout_s
        ),
        backend=args.backend,
        import_mode=args.import_mode,
        queue_backend="bulk",
        workers=args.workers,
        job_timeout_s=args.job_timeout_s,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_grad_collect(args):
    from ..grad.collect import archive_run_artifacts, collect_wave_rows

    summary = collect_wave_rows(args.run_dir, out_path=args.out)
    if not args.no_archive:
        summary["archive"] = archive_run_artifacts(args.run_dir, archive_path=args.archive)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def register_grad_commands(sub) -> None:
    gsm = sub.add_parser("grad-smoke")
    gsm.add_argument("--model")
    gsm.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 8, 16])
    gsm.add_argument("--out")
    gsm.set_defaults(func=cmd_grad_smoke)

    glp = sub.add_parser("grad-loop")
    glp.add_argument("--tasks", required=True)
    glp.add_argument("--out-dir", required=True)
    glp.add_argument("--run-id", required=True)
    glp.add_argument("--model")
    glp.add_argument("--n-waves", type=int, default=4)
    glp.add_argument("--lean-cmd", default="lake env lean")
    glp.add_argument("--workdir")
    glp.add_argument("--task-timeout-s", type=float, default=60.0)
    glp.add_argument("--backend", default="source_check_bulk")
    glp.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="preserve")
    glp.add_argument("--workers", type=int, default=4)
    glp.add_argument("--job-timeout-s", type=float, default=300.0)
    glp.set_defaults(func=cmd_grad_loop)

    gcl = sub.add_parser("grad-collect")
    gcl.add_argument("--run-dir", required=True)
    gcl.add_argument("--out")
    gcl.add_argument("--archive")
    gcl.add_argument("--no-archive", action="store_true")
    gcl.set_defaults(func=cmd_grad_collect)
