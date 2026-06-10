from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import time

from .poms_promotion import _action, _load_evidence, _merge_evidence, _promote_status
from .schemas import read_jsonl, stable_hash, write_records


SCHEMA_POMS_PROMOTION_SERVICE = "lean-rgc-poms-promotion-service-v63.0"


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _now() -> float:
    return float(time.time())


def connect_poms_service_db(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    ensure_poms_service_schema(conn)
    return conn


def ensure_poms_service_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS poms_promotion_decisions (
            decision_id TEXT PRIMARY KEY,
            ts REAL NOT NULL,
            candidate_id TEXT,
            action_id TEXT,
            parent_nonpaid INTEGER NOT NULL,
            dual_certificate INTEGER NOT NULL,
            least_repair INTEGER NOT NULL,
            promotion_status TEXT NOT NULL,
            canonical_status TEXT NOT NULL,
            reason TEXT NOT NULL,
            row_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_poms_decisions_action ON poms_promotion_decisions(action_id, promotion_status);
        CREATE INDEX IF NOT EXISTS idx_poms_decisions_status ON poms_promotion_decisions(promotion_status, canonical_status);
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("poms_promotion_service_schema_version", SCHEMA_POMS_PROMOTION_SERVICE))
    conn.commit()


def _read_poms_rows_from_db(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='poms_rows'").fetchone()
    if table is None:
        return rows
    for r in conn.execute("SELECT row_json FROM poms_rows ORDER BY artifact_id, row_index"):
        try:
            obj = json.loads(r["row_json"] or "{}")
        except Exception:
            obj = {}
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _read_status_rows(run_dir: str | Path, *, poms_rows: str | Path | None, db_path: str | Path | None) -> list[dict[str, Any]]:
    if poms_rows:
        p = Path(poms_rows)
        return read_jsonl(p) if p.exists() else []
    if db_path and Path(db_path).exists():
        conn = connect_poms_service_db(db_path)
        try:
            rows = _read_poms_rows_from_db(conn)
            if rows:
                return rows
        finally:
            conn.close()
    p = Path(run_dir) / "poms_status_rows.jsonl"
    return read_jsonl(p) if p.exists() else []


def _decision_from_row(row: dict[str, Any], evs: list[dict[str, Any]], *, declare_canonical: bool, global_parent_nonpaid: bool, global_dual_certificate: bool, global_least_repair: bool) -> dict[str, Any]:
    ev = _merge_evidence(
        row,
        evs,
        global_parent_nonpaid=global_parent_nonpaid,
        global_dual_certificate=global_dual_certificate,
        global_least_repair=global_least_repair,
    )
    promoted, reason, canonical_status = _promote_status(row, ev, declare_canonical=declare_canonical)
    action = _action(row)
    action_id = str(row.get("action_id") or action.get("action_id") or "")
    candidate_id = str(row.get("candidate_id") or row.get("id") or row.get("record_id") or action_id or stable_hash(row, 14))
    decision = dict(row)
    decision.update(ev)
    decision.update(
        {
            "schema_version": SCHEMA_POMS_PROMOTION_SERVICE,
            "candidate_id": candidate_id,
            "action_id": action_id,
            "promotion_status": promoted,
            "poms_promoted_status": promoted,
            "reason": reason,
            "promotion_reason": reason,
            "canonical_status": canonical_status,
            "canonical_declaration": bool(declare_canonical and canonical_status.startswith("canonical_declared")),
            "canonical_boundary": "poms_parent_nonpaid_dual_certificate_least_repair",
        }
    )
    decision["decision_id"] = "poms_dec_" + stable_hash(
        {
            "candidate_id": candidate_id,
            "action_id": action_id,
            "promotion_status": promoted,
            "canonical_status": canonical_status,
            "evidence": ev,
        },
        24,
    )
    return decision


def store_poms_decisions(db_path: str | Path, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    conn = connect_poms_service_db(db_path)
    try:
        inserted = 0
        for d in decisions:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO poms_promotion_decisions(
                    decision_id, ts, candidate_id, action_id, parent_nonpaid,
                    dual_certificate, least_repair, promotion_status,
                    canonical_status, reason, row_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(d.get("decision_id")),
                    _now(),
                    str(d.get("candidate_id") or ""),
                    str(d.get("action_id") or ""),
                    1 if bool(d.get("parent_nonpaid")) else 0,
                    1 if bool(d.get("dual_certificate")) else 0,
                    1 if bool(d.get("least_repair")) else 0,
                    str(d.get("promotion_status") or ""),
                    str(d.get("canonical_status") or ""),
                    str(d.get("reason") or d.get("promotion_reason") or ""),
                    _json(d),
                ),
            )
            inserted += int(cur.rowcount or 0)
        conn.commit()
        return {"db_path": str(db_path), "n_decisions": len(decisions), "n_inserted": inserted}
    finally:
        conn.close()


def run_poms_promotion_service(
    run_dir: str | Path,
    *,
    db_path: str | Path | None = None,
    poms_rows: str | Path | None = None,
    evidence: list[str | Path] | None = None,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    global_parent_nonpaid: bool = False,
    global_dual_certificate: bool = False,
    global_least_repair: bool = False,
    declare_canonical: bool = False,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    rows = _read_status_rows(run_dir, poms_rows=poms_rows, db_path=db_path)
    evs = _load_evidence(evidence)
    decisions = [
        _decision_from_row(
            row,
            evs,
            declare_canonical=declare_canonical,
            global_parent_nonpaid=global_parent_nonpaid,
            global_dual_certificate=global_dual_certificate,
            global_least_repair=global_least_repair,
        )
        for row in rows
    ]
    by_status: dict[str, int] = {}
    for d in decisions:
        s = str(d.get("promotion_status") or "")
        by_status[s] = by_status.get(s, 0) + 1
    store_summary = store_poms_decisions(db_path, decisions) if db_path else {"db_path": None, "n_decisions": len(decisions), "n_inserted": 0}
    rep = {
        "schema_version": SCHEMA_POMS_PROMOTION_SERVICE,
        "run_dir": str(run_dir),
        "db_path": str(db_path) if db_path else None,
        "n_status_rows": len(rows),
        "n_evidence": len(evs),
        "n_decisions": len(decisions),
        "by_promotion_status": by_status,
        "canonical_status": "promotion_service_decisions_append_only_canonical_only_if_explicitly_declared",
        "store": store_summary,
        "rows": decisions,
    }
    if out_jsonl:
        write_records(out_jsonl, decisions, schema_version=SCHEMA_POMS_PROMOTION_SERVICE, run_id=run_id, parent_ids=parent_ids)
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return rep


def poms_promotion_decisions(
    db_path: str | Path,
    *,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    max_rows: int = 1000,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    conn = connect_poms_service_db(db_path)
    try:
        rows = []
        for r in conn.execute(
            "SELECT * FROM poms_promotion_decisions ORDER BY ts DESC LIMIT ?",
            (int(max_rows),),
        ):
            obj = {
                "decision_id": str(r["decision_id"]),
                "candidate_id": str(r["candidate_id"]),
                "action_id": str(r["action_id"]),
                "parent_nonpaid": bool(r["parent_nonpaid"]),
                "dual_certificate": bool(r["dual_certificate"]),
                "least_repair": bool(r["least_repair"]),
                "promotion_status": str(r["promotion_status"]),
                "canonical_status": str(r["canonical_status"]),
                "reason": str(r["reason"]),
            }
            rows.append(obj)
        by_status: dict[str, int] = {}
        for r in rows:
            by_status[r["promotion_status"]] = by_status.get(r["promotion_status"], 0) + 1
        rep = {
            "schema_version": SCHEMA_POMS_PROMOTION_SERVICE,
            "db_path": str(db_path),
            "n_rows": len(rows),
            "by_promotion_status": by_status,
            "rows": rows,
        }
        if out_jsonl:
            write_records(out_jsonl, rows, schema_version=SCHEMA_POMS_PROMOTION_SERVICE, run_id=run_id, parent_ids=parent_ids)
        if out_json:
            p = Path(out_json)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return rep
    finally:
        conn.close()


__all__ = [
    "SCHEMA_POMS_PROMOTION_SERVICE",
    "connect_poms_service_db",
    "ensure_poms_service_schema",
    "poms_promotion_decisions",
    "run_poms_promotion_service",
    "store_poms_decisions",
]
