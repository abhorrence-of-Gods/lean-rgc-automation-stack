from __future__ import annotations

import json

from ..evals.harness import select_task_subset
from ..evals.report import build_eval_report
from ..schemas import read_jsonl, write_jsonl


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
