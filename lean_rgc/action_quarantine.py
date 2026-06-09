from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import time

from .schemas import write_jsonl


SCHEMA_ACTION_QUARANTINE = "lean-rgc-action-quarantine-v63.0"


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def ensure_quarantine_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS action_quarantine (
            key_type TEXT NOT NULL,
            key_value TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            n_attempts INTEGER NOT NULL DEFAULT 0,
            n_timeouts INTEGER NOT NULL DEFAULT 0,
            timeout_rate REAL NOT NULL DEFAULT 0.0,
            first_seen REAL NOT NULL,
            updated_at REAL NOT NULL,
            detail_json TEXT,
            PRIMARY KEY(key_type, key_value)
        );
        CREATE INDEX IF NOT EXISTS idx_action_quarantine_status ON action_quarantine(status, key_type);
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("action_quarantine_schema_version", SCHEMA_ACTION_QUARANTINE))
    conn.commit()


def connect_quarantine_db(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    ensure_quarantine_schema(conn)
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def _upsert(
    conn: sqlite3.Connection,
    *,
    key_type: str,
    key_value: str,
    status: str,
    reason: str,
    n_attempts: int,
    n_timeouts: int,
    timeout_rate: float,
    detail: dict[str, Any] | None = None,
) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO action_quarantine(
            key_type, key_value, status, reason, n_attempts, n_timeouts,
            timeout_rate, first_seen, updated_at, detail_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(key_type, key_value) DO UPDATE SET
            status=excluded.status,
            reason=excluded.reason,
            n_attempts=excluded.n_attempts,
            n_timeouts=excluded.n_timeouts,
            timeout_rate=excluded.timeout_rate,
            updated_at=excluded.updated_at,
            detail_json=excluded.detail_json
        """,
        (key_type, key_value, status, reason, n_attempts, n_timeouts, float(timeout_rate), now, now, _json(detail or {})),
    )


def refresh_action_quarantine(
    db_path: str | Path,
    *,
    action_timeout_threshold: int = 3,
    probation_min_attempts: int = 5,
    probation_timeout_rate: float = 0.50,
) -> dict[str, Any]:
    conn = connect_quarantine_db(db_path)
    try:
        ensure_quarantine_schema(conn)
        if not _table_exists(conn, "audit_jobs"):
            return quarantine_report_from_conn(conn, db_path=db_path)
        rows = conn.execute(
            """
            SELECT action_id,
                   COUNT(*) AS n_attempts,
                   SUM(CASE WHEN status='timeout' THEN 1 ELSE 0 END) AS n_timeouts
            FROM audit_jobs
            GROUP BY action_id
            """
        ).fetchall()
        for r in rows:
            n_attempts = int(r["n_attempts"] or 0)
            n_timeouts = int(r["n_timeouts"] or 0)
            rate = float(n_timeouts / n_attempts) if n_attempts else 0.0
            if n_timeouts >= action_timeout_threshold:
                _upsert(
                    conn,
                    key_type="action_id",
                    key_value=str(r["action_id"]),
                    status="quarantined",
                    reason=f"same action_id timed out {n_timeouts} times",
                    n_attempts=n_attempts,
                    n_timeouts=n_timeouts,
                    timeout_rate=rate,
                )
        hash_rows = conn.execute(
            """
            SELECT tactic_hash,
                   COUNT(*) AS n_attempts,
                   SUM(CASE WHEN status='timeout' THEN 1 ELSE 0 END) AS n_timeouts
            FROM audit_jobs
            GROUP BY tactic_hash
            """
        ).fetchall()
        for r in hash_rows:
            n_attempts = int(r["n_attempts"] or 0)
            n_timeouts = int(r["n_timeouts"] or 0)
            rate = float(n_timeouts / n_attempts) if n_attempts else 0.0
            if n_attempts >= probation_min_attempts and rate >= probation_timeout_rate:
                _upsert(
                    conn,
                    key_type="tactic_hash",
                    key_value=str(r["tactic_hash"]),
                    status="probation",
                    reason=f"tactic_hash timeout rate {rate:.3f} over {n_attempts} attempts",
                    n_attempts=n_attempts,
                    n_timeouts=n_timeouts,
                    timeout_rate=rate,
                )
        conn.commit()
        return quarantine_report_from_conn(conn, db_path=db_path)
    finally:
        conn.close()


def is_action_quarantined(conn: sqlite3.Connection, *, action_id: str, tactic_hash: str) -> tuple[bool, str]:
    ensure_quarantine_schema(conn)
    row = conn.execute(
        "SELECT status, reason FROM action_quarantine WHERE key_type='action_id' AND key_value=?",
        (action_id,),
    ).fetchone()
    if row is not None and str(row["status"]) == "quarantined":
        return True, str(row["reason"])
    row = conn.execute(
        "SELECT status, reason FROM action_quarantine WHERE key_type='tactic_hash' AND key_value=?",
        (tactic_hash,),
    ).fetchone()
    if row is not None and str(row["status"]) == "quarantined":
        return True, str(row["reason"])
    return False, ""


def quarantine_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_quarantine_schema(conn)
    return [
        {
            "key_type": str(r["key_type"]),
            "key_value": str(r["key_value"]),
            "status": str(r["status"]),
            "reason": str(r["reason"]),
            "n_attempts": int(r["n_attempts"] or 0),
            "n_timeouts": int(r["n_timeouts"] or 0),
            "timeout_rate": float(r["timeout_rate"] or 0.0),
        }
        for r in conn.execute(
            "SELECT * FROM action_quarantine ORDER BY status DESC, n_timeouts DESC, key_type, key_value"
        )
    ]


def quarantine_report_from_conn(conn: sqlite3.Connection, *, db_path: str | Path | None = None) -> dict[str, Any]:
    rows = quarantine_rows(conn)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {
        "schema_version": SCHEMA_ACTION_QUARANTINE,
        "db_path": str(db_path) if db_path else None,
        "n_rows": len(rows),
        "by_status": by_status,
        "rows": rows,
    }


def action_quarantine_report(db_path: str | Path, *, refresh: bool = True, out_json: str | Path | None = None) -> dict[str, Any]:
    rep = refresh_action_quarantine(db_path) if refresh else None
    if rep is None:
        conn = connect_quarantine_db(db_path)
        try:
            rep = quarantine_report_from_conn(conn, db_path=db_path)
        finally:
            conn.close()
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return rep


def export_quarantined_actions(db_path: str | Path, out: str | Path, *, refresh: bool = True) -> dict[str, Any]:
    rep = action_quarantine_report(db_path, refresh=refresh)
    rows = [r for r in rep.get("rows", []) if r.get("status") == "quarantined" and r.get("key_type") == "action_id"]
    write_jsonl(out, rows)
    return {"schema_version": SCHEMA_ACTION_QUARANTINE, "out": str(out), "n_exported": len(rows)}


__all__ = [
    "SCHEMA_ACTION_QUARANTINE",
    "action_quarantine_report",
    "connect_quarantine_db",
    "ensure_quarantine_schema",
    "export_quarantined_actions",
    "is_action_quarantined",
    "quarantine_rows",
    "refresh_action_quarantine",
]
