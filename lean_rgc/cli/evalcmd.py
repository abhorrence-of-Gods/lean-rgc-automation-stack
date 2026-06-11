from __future__ import annotations

from pathlib import Path
import json

from ..evals.harness import run_eval, select_task_subset
from ..evals.report import build_eval_report
from ..pbct.episode_store import import_prompt_artifacts, summarize_prompt_db
from ..pbct.llm_client import LLMClient, LLMClientConfig
from ..pbct.proposals import make_llm_proposal_fn
from ..pbct.signal_bridge import make_signal_packet_fn
from ..schemas import LeanTask, read_jsonl, write_jsonl


def cmd_eval_subset(args):
    rows = [r for r in read_jsonl(args.tasks) if isinstance(r, dict)]
    subset = select_task_subset(rows, n=args.n, seed=args.seed)
    write_jsonl(args.out, subset)
    summary = {
        "tasks": str(args.tasks),
        "out": str(args.out),
        "n_input": len(rows),
        "n_selected": len(subset),
        "seed": int(args.seed),
        "task_ids": [str(r.get("task_id")) for r in subset[:10]],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_eval_report(args):
    episodes_paths: dict[str, str] = {}
    for spec in args.episodes:
        if "=" not in spec:
            raise SystemExit(f"--episodes expects arm=path, got: {spec}")
        arm, path = spec.split("=", 1)
        episodes_paths[arm.strip()] = path.strip()
    report = build_eval_report(
        episodes_paths=episodes_paths,
        out=args.out,
        n_bootstrap=args.n_bootstrap,
        seed=args.seed,
    )
    print(json.dumps({k: report[k] for k in ("n_tasks", "arms", "paired_comparisons")}, indent=2, ensure_ascii=False))
    return 0


def cmd_eval_run(args):
    from ..lean.executor import LeanExecutorConfig

    out_dir = Path(args.out_dir)
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(args.tasks) if isinstance(r, dict)]
    config = LLMClientConfig.from_file(args.llm_config)
    if not config.ledger_path:
        config.ledger_path = str(out_dir / "llm_calls.jsonl")
    client = LLMClient(config)
    proposal_fn = make_llm_proposal_fn(
        client=client,
        max_proposals=args.max_proposals,
        boundaries_out=out_dir / "boundaries.jsonl",
    )
    signal_packet_fn = make_signal_packet_fn() if args.arm == "a2_typed_packet" else None
    executor_config = LeanExecutorConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.task_timeout_s,
        dry_run=args.dry_run,
    )
    summary = run_eval(
        tasks=tasks,
        arm=args.arm,
        proposal_fn=proposal_fn,
        signal_packet_fn=signal_packet_fn,
        out_dir=out_dir,
        run_id=args.run_id,
        budget_calls=args.budget_calls,
        summary_out=out_dir / "eval_summary.json",
        executor_config=executor_config,
        backend=args.backend,
        import_mode=args.import_mode,
        queue_backend=args.queue_backend,
        workers=args.workers,
        job_timeout_s=args.job_timeout_s,
        audit_cache_db=args.audit_cache_db,
    )
    store = import_prompt_artifacts(
        db_path=out_dir / "prompt.sqlite",
        boundaries_path=out_dir / "boundaries.jsonl",
        episodes_path=out_dir / "episodes.jsonl",
    )
    summary["prompt_store"] = summarize_prompt_db(out_dir / "prompt.sqlite")
    summary["prompt_store_import"] = store
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def register_eval_commands(sub) -> None:
    esub = sub.add_parser("eval-subset")
    esub.add_argument("--tasks", required=True)
    esub.add_argument("--out", required=True)
    esub.add_argument("--n", type=int, required=True)
    esub.add_argument("--seed", type=int, default=0)
    esub.set_defaults(func=cmd_eval_subset)

    erep = sub.add_parser("eval-report")
    erep.add_argument("--episodes", nargs="+", required=True, help="arm=episodes.jsonl pairs")
    erep.add_argument("--out", required=True)
    erep.add_argument("--n-bootstrap", type=int, default=10000)
    erep.add_argument("--seed", type=int, default=0)
    erep.set_defaults(func=cmd_eval_report)

    erun = sub.add_parser("eval-run")
    erun.add_argument("--tasks", required=True)
    erun.add_argument("--arm", required=True, choices=["a0_onebit", "a1_raw_error", "a2_typed_packet"])
    erun.add_argument("--llm-config", required=True)
    erun.add_argument("--out-dir", required=True)
    erun.add_argument("--run-id", required=True)
    erun.add_argument("--budget-calls", type=int, default=8)
    erun.add_argument("--max-proposals", type=int, default=4)
    erun.add_argument("--lean-cmd", default="lake env lean")
    erun.add_argument("--workdir")
    erun.add_argument("--task-timeout-s", type=float, default=60.0)
    erun.add_argument("--dry-run", action="store_true")
    erun.add_argument("--backend", default="source_check_bulk")
    erun.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="preserve")
    erun.add_argument("--queue-backend", choices=["bulk", "file"], default="bulk")
    erun.add_argument("--workers", type=int, default=1)
    erun.add_argument("--job-timeout-s", type=float, default=120.0)
    erun.add_argument("--audit-cache-db")
    erun.set_defaults(func=cmd_eval_run)
