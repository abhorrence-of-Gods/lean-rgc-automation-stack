from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import sys

from ..audit_db import build_audit_db, query_audit_db, write_query_outputs
from ..data.store import build_run_db, check_run_db_invariants, query_run_db, summarize_run_db, write_query_outputs as write_run_query_outputs
from ..repair_db import build_repair_db, repair_db_query, write_repair_query_outputs


def _maybe_warn_deprecated(args) -> None:
    old = getattr(args, "deprecated_command", None)
    new = getattr(args, "replacement_command", None)
    if old and new:
        print(f"[DEPRECATED] use `lean-rgc {new}` instead of `lean-rgc {old}`.", file=sys.stderr)


def cmd_audit_db_build(args) -> int:
    _maybe_warn_deprecated(args)
    summary = build_audit_db(args.run_dir, args.db, reset=not getattr(args, "append", False))
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_db_query(args) -> int:
    _maybe_warn_deprecated(args)
    sql = args.sql
    if getattr(args, "sql_file", None):
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    rows = query_audit_db(args.db, sql, max_rows=args.max_rows)
    write_query_outputs(rows, out_json=getattr(args, "out_json", None), out_csv=getattr(args, "out_csv", None))
    print(json.dumps({"db": args.db, "n_rows": len(rows), "rows": rows[:args.print_rows]}, indent=2, ensure_ascii=False))
    return 0


def cmd_run_db_build(args) -> int:
    _maybe_warn_deprecated(args)
    summary = build_run_db(
        args.run_dir,
        args.db,
        append=getattr(args, "append", False),
        artifact_store_root=getattr(args, "artifact_store_root", None),
        import_artifacts=not getattr(args, "no_import_artifacts", False),
        materialize_lineage=not getattr(args, "no_lineage", False),
        run_id=getattr(args, "run_id", None),
    )
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_run_db_query(args) -> int:
    _maybe_warn_deprecated(args)
    sql = args.sql
    if getattr(args, "sql_file", None):
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    if not sql:
        conn = sqlite3.connect(args.db)
        conn.row_factory = sqlite3.Row
        try:
            rep = summarize_run_db(conn)
        finally:
            conn.close()
        if getattr(args, "out_json", None):
            Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0
    rows = query_run_db(args.db, sql, max_rows=args.max_rows)
    write_run_query_outputs(rows, out_json=getattr(args, "out_json", None), out_csv=getattr(args, "out_csv", None))
    print(json.dumps({"db": args.db, "n_rows": len(rows), "rows": rows[:args.print_rows]}, indent=2, ensure_ascii=False))
    return 0


def cmd_run_db_summarize(args) -> int:
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        rep = summarize_run_db(conn)
    finally:
        conn.close()
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_run_db_check(args) -> int:
    db = Path(args.db)
    if not db.exists():
        rep = {"db": str(db), "ok": False, "error": "missing_db"}
        print(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True) if getattr(args, "json", False) else f"FAIL {db}: missing_db")
        return 2
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        invariants = check_run_db_invariants(conn)
    finally:
        conn.close()
    rep = {"db": str(db), "ok": bool(invariants.get("ok")), "invariants": invariants}
    if getattr(args, "json", False):
        print(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        status = "OK" if rep["ok"] else "FAIL"
        print(f"{status} {db}")
        if not rep["ok"]:
            print(json.dumps(invariants, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if rep["ok"] else 1


def cmd_run_db_lineage(args) -> int:
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        where = ""
        params: list[Any] = []
        if getattr(args, "edge_type", None):
            where = "WHERE edge_type=?"
            params.append(args.edge_type)
        rows = [
            {k: row[k] for k in row.keys()}
            for row in conn.execute(
                f"""
                SELECT edge_type, src_type, dst_type, COUNT(*) AS n
                FROM lineage_edges
                {where}
                GROUP BY edge_type, src_type, dst_type
                ORDER BY n DESC, edge_type
                LIMIT ?
                """,
                [*params, int(args.max_rows)],
            )
        ]
        total = int(conn.execute(f"SELECT COUNT(*) FROM lineage_edges {where}", params).fetchone()[0])
    finally:
        conn.close()
    rep = {"db": args.db, "n_edges": total, "rows": rows}
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_repair_db_build(args) -> int:
    _maybe_warn_deprecated(args)
    rep = build_repair_db(args.run_dir, args.db, append=getattr(args, "append", False), include_audit_db=not getattr(args, "no_audit_db", False))
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_repair_db_query(args) -> int:
    _maybe_warn_deprecated(args)
    sql = args.sql
    if getattr(args, "sql_file", None):
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    rep = repair_db_query(args.db, sql=sql, max_rows=args.max_rows)
    write_repair_query_outputs(rep, out_json=getattr(args, "out_json", None), out_csv=getattr(args, "out_csv", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def register_data_commands(sub) -> None:
    data = sub.add_parser("data")
    data_sub = data.add_subparsers(dest="data_cmd", required=True)
    dbuild = data_sub.add_parser("build")
    dbuild.add_argument("--run-dir", required=True)
    dbuild.add_argument("--db")
    dbuild.add_argument("--append", action="store_true")
    dbuild.add_argument("--artifact-store-root")
    dbuild.add_argument("--no-import-artifacts", action="store_true")
    dbuild.add_argument("--no-lineage", action="store_true")
    dbuild.add_argument("--run-id")
    dbuild.add_argument("--out-json")
    dbuild.set_defaults(func=cmd_run_db_build)

    dquery = data_sub.add_parser("query")
    dquery.add_argument("--db", required=True)
    dquery.add_argument("--sql")
    dquery.add_argument("--sql-file")
    dquery.add_argument("--max-rows", type=int, default=1000)
    dquery.add_argument("--print-rows", type=int, default=20)
    dquery.add_argument("--out-json")
    dquery.add_argument("--out-csv")
    dquery.set_defaults(func=cmd_run_db_query)

    dsum = data_sub.add_parser("summarize")
    dsum.add_argument("--db", required=True)
    dsum.add_argument("--out-json")
    dsum.set_defaults(func=cmd_run_db_summarize)

    dcheck = data_sub.add_parser("check")
    dcheck.add_argument("--db", required=True)
    dcheck.add_argument("--json", action="store_true")
    dcheck.set_defaults(func=cmd_run_db_check)

    dlin = data_sub.add_parser("lineage")
    dlin.add_argument("--db", required=True)
    dlin.add_argument("--edge-type")
    dlin.add_argument("--max-rows", type=int, default=1000)
    dlin.add_argument("--out-json")
    dlin.set_defaults(func=cmd_run_db_lineage)

    adb = sub.add_parser("audit-db-build")
    adb.add_argument("--run-dir", required=True)
    adb.add_argument("--db")
    adb.add_argument("--append", action="store_true")
    adb.add_argument("--out-json")
    adb.set_defaults(func=cmd_audit_db_build, deprecated_command="audit-db-build", replacement_command="data build")

    adq = sub.add_parser("audit-db-query")
    adq.add_argument("--db", required=True)
    adq.add_argument("--sql")
    adq.add_argument("--sql-file")
    adq.add_argument("--max-rows", type=int, default=1000)
    adq.add_argument("--print-rows", type=int, default=20)
    adq.add_argument("--out-json")
    adq.add_argument("--out-csv")
    adq.set_defaults(func=cmd_audit_db_query, deprecated_command="audit-db-query", replacement_command="data query")

    rnb = sub.add_parser("run-db-build")
    rnb.add_argument("--run-dir", required=True)
    rnb.add_argument("--db")
    rnb.add_argument("--append", action="store_true")
    rnb.add_argument("--artifact-store-root")
    rnb.add_argument("--no-import-artifacts", action="store_true")
    rnb.add_argument("--no-lineage", action="store_true")
    rnb.add_argument("--run-id")
    rnb.add_argument("--out-json")
    rnb.set_defaults(func=cmd_run_db_build, deprecated_command="run-db-build", replacement_command="data build")

    rnq = sub.add_parser("run-db-query")
    rnq.add_argument("--db", required=True)
    rnq.add_argument("--sql")
    rnq.add_argument("--sql-file")
    rnq.add_argument("--max-rows", type=int, default=1000)
    rnq.add_argument("--print-rows", type=int, default=20)
    rnq.add_argument("--out-json")
    rnq.add_argument("--out-csv")
    rnq.set_defaults(func=cmd_run_db_query, deprecated_command="run-db-query", replacement_command="data query")

    rdb = sub.add_parser("repair-db-build")
    rdb.add_argument("--run-dir", required=True)
    rdb.add_argument("--db")
    rdb.add_argument("--append", action="store_true")
    rdb.add_argument("--no-audit-db", action="store_true")
    rdb.add_argument("--out-json")
    rdb.set_defaults(func=cmd_repair_db_build, deprecated_command="repair-db-build", replacement_command="data build")

    rdq = sub.add_parser("repair-db-query")
    rdq.add_argument("--db", required=True)
    rdq.add_argument("--sql")
    rdq.add_argument("--sql-file")
    rdq.add_argument("--max-rows", type=int, default=1000)
    rdq.add_argument("--out-json")
    rdq.add_argument("--out-csv")
    rdq.set_defaults(func=cmd_repair_db_query, deprecated_command="repair-db-query", replacement_command="data query")


__all__ = [
    "cmd_audit_db_build",
    "cmd_audit_db_query",
    "cmd_repair_db_build",
    "cmd_repair_db_query",
    "cmd_run_db_build",
    "cmd_run_db_check",
    "cmd_run_db_lineage",
    "cmd_run_db_query",
    "cmd_run_db_summarize",
    "register_data_commands",
]
