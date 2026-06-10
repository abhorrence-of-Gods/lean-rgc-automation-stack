from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from ..data.store import check_run_db_invariants
from ..pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "benchmarks"
SMOKE_TASKS = BENCHMARK_ROOT / "smoke" / "tasks.jsonl"
SMOKE_ACTIONS = BENCHMARK_ROOT / "smoke" / "actions.jsonl"


def _check_run_db(db_path: Path) -> dict:
    if not db_path.exists():
        return {"ok": False, "error": "missing_db", "db": str(db_path)}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        invariants = check_run_db_invariants(conn)
    finally:
        conn.close()
    return {"ok": bool(invariants.get("ok")), "db": str(db_path), "invariants": invariants}


def cmd_benchmark_smoke(args: argparse.Namespace) -> int:
    out = Path(args.out)
    pipeline_args = {
        "tasks": str(SMOKE_TASKS),
        "actions": str(SMOKE_ACTIONS),
        "out": str(out),
        "dry_run": bool(args.dry_run),
        "run_db": bool(args.run_db),
        "jobs": args.jobs,
        "max_actions": args.max_actions,
        "import_mode": args.import_mode,
        "lean_cmd": args.lean_cmd,
        "workdir": args.workdir,
        "timeout_s": args.timeout_s,
    }
    report = run_pipeline(pipeline_args, emit_stage=not args.quiet)
    result = {
        "benchmark": "smoke",
        "tasks": str(SMOKE_TASKS),
        "actions": str(SMOKE_ACTIONS),
        "out": str(out),
        "pipeline_report": str(out / "pipeline_report.json"),
        "run_db_check": None,
    }
    if args.run_db:
        result["run_db_check"] = _check_run_db(out / "runs.db")
    result["ok"] = bool(not result["run_db_check"] or result["run_db_check"].get("ok"))
    result["pipeline"] = {
        "run_id": report.get("run_id"),
        "pipeline_files": report.get("pipeline_files", {}),
    }
    (out / "benchmark_smoke_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


def register_benchmark_commands(sub) -> None:
    bench = sub.add_parser("benchmark")
    bench_sub = bench.add_subparsers(dest="benchmark_cmd", required=True)
    smoke = bench_sub.add_parser("smoke")
    smoke.add_argument("--out", required=True)
    smoke.add_argument("--dry-run", action="store_true")
    smoke.add_argument("--run-db", action="store_true")
    smoke.add_argument("--jobs", type=int, default=1)
    smoke.add_argument("--max-actions", type=int, default=8)
    smoke.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="preserve")
    smoke.add_argument("--lean-cmd", default="lake env lean")
    smoke.add_argument("--workdir")
    smoke.add_argument("--timeout-s", type=float, default=20.0)
    smoke.add_argument("--quiet", action="store_true")
    smoke.set_defaults(func=cmd_benchmark_smoke)


__all__ = ["cmd_benchmark_smoke", "register_benchmark_commands"]

