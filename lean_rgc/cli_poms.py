from __future__ import annotations

import json
from pathlib import Path

from .poms_promotion import collect_poms_promotion
from .poms_promotion_service import poms_promotion_decisions, run_poms_promotion_service
from .poms_status import collect_poms_status
from .promotion_evidence import generate_promotion_evidence
from .repair_db import failure_attribution_report


def cmd_poms_status(args):
    rep = collect_poms_status(
        args.run_dir,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_csv=args.out_csv,
        min_realized_goal_response=args.min_realized_goal_response,
        require_realized_success=args.require_realized_success,
    )
    print(
        json.dumps(
            {
                "run_dir": args.run_dir,
                "summary": rep.get("summary", {}),
                "out_json": args.out_json,
                "out_jsonl": args.out_jsonl,
                "out_csv": args.out_csv,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_poms_evidence(args):
    rep = generate_promotion_evidence(
        args.run_dir,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_poms=args.out_poms,
        out_csv=args.out_csv,
        min_relative_residual=args.min_relative_residual,
        min_residual_norm=args.min_residual_norm,
        min_support_count=args.min_support_count,
        min_margin=args.min_margin,
        min_robust_margin=args.min_robust_margin,
        least_repair_epsilon=args.least_repair_epsilon,
    )
    print(
        json.dumps(
            {
                "run_dir": args.run_dir,
                "summary": rep.get("summary", {}),
                "out_json": args.out_json,
                "out_jsonl": args.out_jsonl,
                "out_poms": args.out_poms,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_poms_promote(args):
    rep = collect_poms_promotion(
        args.run_dir,
        poms_rows=args.poms_rows,
        evidence=args.evidence,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_csv=args.out_csv,
        out_promoted_actions=args.out_promoted_actions,
        global_parent_nonpaid=args.parent_nonpaid,
        global_dual_certificate=args.dual_certificate,
        global_least_repair=args.least_repair,
        declare_canonical=args.declare_canonical,
    )
    print(
        json.dumps(
            {
                "run_dir": args.run_dir,
                "summary": rep.get("summary", {}),
                "out_json": args.out_json,
                "out_jsonl": args.out_jsonl,
                "out_csv": args.out_csv,
                "out_promoted_actions": args.out_promoted_actions,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_failure_attribution_report(args):
    sql = args.sql
    if getattr(args, "sql_file", None):
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    rep = failure_attribution_report(db_path=args.db, out_json=args.out_json, sql=sql, max_rows=args.max_rows)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_poms_promotion_service(args):
    rep = run_poms_promotion_service(
        args.run_dir,
        db_path=args.db,
        poms_rows=args.poms_rows,
        evidence=args.evidence,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        global_parent_nonpaid=args.parent_nonpaid,
        global_dual_certificate=args.dual_certificate,
        global_least_repair=args.least_repair,
        declare_canonical=args.declare_canonical,
    )
    print(json.dumps({"summary": {k: v for k, v in rep.items() if k != "rows"}, "n_rows": len(rep.get("rows", []))}, indent=2, ensure_ascii=False))
    return 0


def cmd_poms_promotion_decisions(args):
    rep = poms_promotion_decisions(args.db, out_json=args.out_json, out_jsonl=args.out_jsonl, max_rows=args.max_rows)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def register_poms_commands(sub) -> None:
    poms = sub.add_parser("poms-status")
    poms.add_argument("--run-dir", required=True)
    poms.add_argument("--out-json")
    poms.add_argument("--out-jsonl")
    poms.add_argument("--out-csv")
    poms.add_argument("--min-realized-goal-response", type=float, default=0.0)
    poms.add_argument("--require-realized-success", action="store_true")
    poms.set_defaults(func=cmd_poms_status)

    pe = sub.add_parser("poms-evidence")
    pe.add_argument("--run-dir", required=True)
    pe.add_argument("--out-json")
    pe.add_argument("--out-jsonl")
    pe.add_argument("--out-poms")
    pe.add_argument("--out-csv")
    pe.add_argument("--min-relative-residual", type=float, default=0.05)
    pe.add_argument("--min-residual-norm", type=float, default=1e-6)
    pe.add_argument("--min-support-count", type=int, default=1)
    pe.add_argument("--min-margin", type=float, default=0.0)
    pe.add_argument("--min-robust-margin", type=float, default=0.0)
    pe.add_argument("--least-repair-epsilon", type=float, default=1e-9)
    pe.set_defaults(func=cmd_poms_evidence)

    pp = sub.add_parser("poms-promote")
    pp.add_argument("--run-dir", required=True)
    pp.add_argument("--poms-rows")
    pp.add_argument("--evidence", action="append")
    pp.add_argument("--out-json")
    pp.add_argument("--out-jsonl")
    pp.add_argument("--out-csv")
    pp.add_argument("--out-promoted-actions")
    pp.add_argument("--parent-nonpaid", action="store_true")
    pp.add_argument("--dual-certificate", action="store_true")
    pp.add_argument("--least-repair", action="store_true")
    pp.add_argument("--declare-canonical", action="store_true")
    pp.set_defaults(func=cmd_poms_promote)

    far = sub.add_parser("failure-attribution-report")
    far.add_argument("--db", required=True)
    far.add_argument("--out-json")
    far.add_argument("--sql")
    far.add_argument("--sql-file")
    far.add_argument("--max-rows", type=int, default=1000)
    far.set_defaults(func=cmd_failure_attribution_report)

    pps = sub.add_parser("poms-promotion-service")
    pps.add_argument("--run-dir", required=True)
    pps.add_argument("--db")
    pps.add_argument("--poms-rows")
    pps.add_argument("--evidence", action="append")
    pps.add_argument("--out-json")
    pps.add_argument("--out-jsonl")
    pps.add_argument("--parent-nonpaid", action="store_true")
    pps.add_argument("--dual-certificate", action="store_true")
    pps.add_argument("--least-repair", action="store_true")
    pps.add_argument("--declare-canonical", action="store_true")
    pps.set_defaults(func=cmd_poms_promotion_service)

    ppd = sub.add_parser("poms-promotion-decisions")
    ppd.add_argument("--db", required=True)
    ppd.add_argument("--out-json")
    ppd.add_argument("--out-jsonl")
    ppd.add_argument("--max-rows", type=int, default=1000)
    ppd.set_defaults(func=cmd_poms_promotion_decisions)


__all__ = [
    "cmd_failure_attribution_report",
    "cmd_poms_evidence",
    "cmd_poms_promote",
    "cmd_poms_promotion_decisions",
    "cmd_poms_promotion_service",
    "cmd_poms_status",
    "register_poms_commands",
]
