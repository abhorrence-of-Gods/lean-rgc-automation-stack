from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import time


SCHEMA_TIMEOUT_LEDGER = "lean-rgc-timeout-ledger-v63.0"
TIMEOUT_SCOPES = {
    "import_timeout",
    "batch_timeout",
    "tactic_timeout",
    "worker_timeout",
    "unknown_timeout",
}


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def ensure_timeout_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS worker_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            worker_id TEXT,
            event_type TEXT NOT NULL,
            job_id TEXT,
            backend TEXT,
            lane TEXT,
            detail_json TEXT
        );
        CREATE TABLE IF NOT EXISTS timeout_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            job_id TEXT,
            task_id TEXT,
            action_id TEXT,
            tactic_hash TEXT,
            backend TEXT,
            lane TEXT,
            timeout_s REAL,
            elapsed_s REAL,
            stdout_tail TEXT,
            stderr_tail TEXT,
            worker_id TEXT,
            timeout_scope TEXT NOT NULL DEFAULT 'unknown_timeout',
            detail_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_timeout_events_action ON timeout_events(action_id, tactic_hash);
        CREATE INDEX IF NOT EXISTS idx_timeout_events_job ON timeout_events(job_id);
        CREATE INDEX IF NOT EXISTS idx_worker_events_worker ON worker_events(worker_id, event_type, ts);
        """
    )
    cols = {str(r[1]) for r in cur.execute("PRAGMA table_info(timeout_events)").fetchall()}
    if "timeout_scope" not in cols:
        cur.execute("ALTER TABLE timeout_events ADD COLUMN timeout_scope TEXT NOT NULL DEFAULT 'unknown_timeout'")
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("timeout_ledger_schema_version", SCHEMA_TIMEOUT_LEDGER))
    conn.commit()


def connect_timeout_db(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    ensure_timeout_schema(conn)
    return conn


def record_worker_event(
    conn: sqlite3.Connection,
    *,
    worker_id: str,
    event_type: str,
    job_id: str | None = None,
    backend: str | None = None,
    lane: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    ensure_timeout_schema(conn)
    conn.execute(
        "INSERT INTO worker_events(ts, worker_id, event_type, job_id, backend, lane, detail_json) VALUES (?,?,?,?,?,?,?)",
        (_now(), worker_id, event_type, job_id, backend, lane, _json(detail or {})),
    )
    conn.commit()


def record_timeout_event(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    task_id: str,
    action_id: str,
    tactic_hash: str,
    backend: str,
    lane: str,
    timeout_s: float,
    elapsed_s: float,
    stdout_tail: str = "",
    stderr_tail: str = "",
    worker_id: str = "",
    timeout_scope: str = "tactic_timeout",
    detail: dict[str, Any] | None = None,
) -> None:
    ensure_timeout_schema(conn)
    scope = timeout_scope if timeout_scope in TIMEOUT_SCOPES else "unknown_timeout"
    conn.execute(
        """
        INSERT INTO timeout_events(
            ts, job_id, task_id, action_id, tactic_hash, backend, lane,
            timeout_s, elapsed_s, stdout_tail, stderr_tail, worker_id, timeout_scope, detail_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            _now(),
            job_id,
            task_id,
            action_id,
            tactic_hash,
            backend,
            lane,
            float(timeout_s),
            float(elapsed_s),
            (stdout_tail or "")[-4000:],
            (stderr_tail or "")[-4000:],
            worker_id,
            scope,
            _json(detail or {}),
        ),
    )
    conn.commit()


def timeout_ledger_report(db_path: str | Path, *, out_json: str | Path | None = None) -> dict[str, Any]:
    conn = connect_timeout_db(db_path)
    try:
        by_action = [
            {"action_id": str(r["action_id"]), "n_timeout": int(r["n"])}
            for r in conn.execute(
                "SELECT action_id, COUNT(*) AS n FROM timeout_events GROUP BY action_id ORDER BY n DESC, action_id LIMIT 100"
            )
        ]
        by_hash = [
            {"tactic_hash": str(r["tactic_hash"]), "n_timeout": int(r["n"])}
            for r in conn.execute(
                "SELECT tactic_hash, COUNT(*) AS n FROM timeout_events GROUP BY tactic_hash ORDER BY n DESC, tactic_hash LIMIT 100"
            )
        ]
        by_backend = {
            str(r["backend"]): int(r["n"])
            for r in conn.execute("SELECT backend, COUNT(*) AS n FROM timeout_events GROUP BY backend ORDER BY backend")
        }
        by_scope = {
            str(r["timeout_scope"] or "unknown_timeout"): int(r["n"])
            for r in conn.execute("SELECT timeout_scope, COUNT(*) AS n FROM timeout_events GROUP BY timeout_scope ORDER BY timeout_scope")
        }
        worker_restarts = int(
            conn.execute("SELECT COUNT(*) FROM worker_events WHERE event_type IN ('restart','killed_timeout')").fetchone()[0]
        )
        n_timeout = int(conn.execute("SELECT COUNT(*) FROM timeout_events").fetchone()[0])
        n_tactic_timeout = int(by_scope.get("tactic_timeout", 0))
        n_infra_timeout = int(n_timeout - n_tactic_timeout)
        rep = {
            "schema_version": SCHEMA_TIMEOUT_LEDGER,
            "db_path": str(db_path),
            "n_timeout": n_timeout,
            "n_tactic_timeout": n_tactic_timeout,
            "n_infra_timeout": n_infra_timeout,
            "n_quarantine_suppressed_by_import_cost": n_infra_timeout,
            "worker_restarts": worker_restarts,
            "by_backend": by_backend,
            "by_scope": by_scope,
            "top_actions": by_action,
            "top_tactic_hashes": by_hash,
        }
        if out_json:
            p = Path(out_json)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return rep
    finally:
        conn.close()


__all__ = [
    "SCHEMA_TIMEOUT_LEDGER",
    "TIMEOUT_SCOPES",
    "connect_timeout_db",
    "ensure_timeout_schema",
    "record_timeout_event",
    "record_worker_event",
    "timeout_ledger_report",
]
