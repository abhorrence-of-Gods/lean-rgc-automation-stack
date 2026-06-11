from __future__ import annotations

from pathlib import Path
from typing import Any
import copy
import json
import shlex
import sqlite3
import subprocess
import time

from .audit_job_queue import connect_queue, ensure_audit_queue_schema
from .schemas import stable_hash


SCHEMA_AUDIT_RESULT_CACHE = "lean-rgc-audit-result-cache-v85.0"

DEFAULT_CACHE_LANE = "source_check"


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _loads(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {"value": obj}


def connect_audit_cache(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db, timeout=60.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_audit_cache_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_result_cache (
            cache_key TEXT PRIMARY KEY,
            task_hash TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            tactic_hash TEXT NOT NULL,
            imports_hash TEXT NOT NULL,
            lean_version TEXT NOT NULL,
            workdir_fingerprint TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            max_heartbeats TEXT NOT NULL,
            trace_state INTEGER NOT NULL,
            lane TEXT NOT NULL DEFAULT 'source_check',
            audit_status TEXT,
            queue_status TEXT,
            result_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            last_hit_at REAL,
            hit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_audit_result_cache_task ON audit_result_cache(task_hash);
        CREATE INDEX IF NOT EXISTS idx_audit_result_cache_tactic ON audit_result_cache(tactic_hash);
        CREATE INDEX IF NOT EXISTS idx_audit_result_cache_lean ON audit_result_cache(lean_version);
        """
    )
    _migrate_cache_lane(conn)
    cur.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
        ("audit_result_cache_schema_version", SCHEMA_AUDIT_RESULT_CACHE),
    )
    conn.commit()


def _migrate_cache_lane(conn: sqlite3.Connection) -> None:
    # v65 cache rows predate kernel-lane backends, so every existing row is a
    # source_check observation; their primary keys must be recomputed because
    # the v85 key includes the lane.
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(audit_result_cache)")}
    if "lane" in columns:
        return
    conn.execute(
        "ALTER TABLE audit_result_cache ADD COLUMN lane TEXT NOT NULL DEFAULT 'source_check'"
    )
    rows = conn.execute(
        """
        SELECT cache_key, task_hash, state_hash, tactic_hash, imports_hash,
               lean_version, workdir_fingerprint, import_mode, max_heartbeats, trace_state
        FROM audit_result_cache
        """
    ).fetchall()
    for row in rows:
        fields = {
            "task_hash": str(row["task_hash"]),
            "state_hash": str(row["state_hash"]),
            "tactic_hash": str(row["tactic_hash"]),
            "imports_hash": str(row["imports_hash"]),
            "lean_version": str(row["lean_version"]),
            "workdir_fingerprint": str(row["workdir_fingerprint"]),
            "import_mode": str(row["import_mode"]),
            "max_heartbeats": str(row["max_heartbeats"]),
            "trace_state": int(row["trace_state"]),
            "lane": DEFAULT_CACHE_LANE,
        }
        new_key = stable_hash(fields, 48)
        conn.execute(
            "UPDATE OR REPLACE audit_result_cache SET cache_key=?, lane=? WHERE cache_key=?",
            (new_key, DEFAULT_CACHE_LANE, str(row["cache_key"])),
        )
    conn.commit()


def detect_lean_version(lean_cmd: str, *, workdir: str | None = None, timeout_s: float = 10.0) -> str:
    cmd = shlex.split(lean_cmd) + ["--version"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir or None,
            text=True,
            capture_output=True,
            timeout=max(1.0, float(timeout_s or 10.0)),
            check=False,
        )
    except BaseException as exc:
        return "unknown:" + type(exc).__name__
    out = (proc.stdout or proc.stderr or "").strip()
    if not out:
        return f"unknown:returncode={proc.returncode}"
    return out.splitlines()[0][:240]


def workdir_fingerprint(workdir: str | None) -> str:
    if not workdir:
        return stable_hash({"workdir": ""}, 24)
    root = Path(workdir)
    lake = root / "lake-manifest.json"
    lean = root / "lean-toolchain"
    payload: dict[str, Any] = {"workdir": str(root.resolve())}
    for p in (lake, lean):
        if p.exists():
            try:
                payload[p.name] = stable_hash(p.read_text(encoding="utf-8", errors="replace"), 24)
            except Exception:
                payload[p.name] = "unreadable"
        else:
            payload[p.name] = "missing"
    return stable_hash(payload, 24)


def _max_heartbeats(payload: dict[str, Any]) -> str:
    action = payload.get("action") if isinstance(payload.get("action"), dict) else {}
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    value = action.get("max_heartbeats")
    if value is None:
        value = task.get("max_heartbeats")
    return str(value if value is not None else "")


def make_audit_cache_key(
    payload: dict[str, Any],
    *,
    lean_version: str,
    workdir_fingerprint_value: str,
    import_mode: str,
    trace_state: bool,
    lane: str,
) -> tuple[str, dict[str, Any]]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    action = payload.get("action") if isinstance(payload.get("action"), dict) else {}
    imports = task.get("imports") if isinstance(task.get("imports"), list) else []
    max_hb = _max_heartbeats(payload)
    fields = {
        "task_hash": stable_hash(
            {
                "task_id": task.get("task_id"),
                "statement": task.get("statement"),
                "imports": imports,
                "prefix": task.get("prefix", ""),
                "namespace": task.get("namespace"),
                "allowed_axioms": task.get("allowed_axioms") or [],
            },
            32,
        ),
        "state_hash": stable_hash(
            {
                "state_id": state.get("state_id"),
                "task_id": state.get("task_id"),
                "target": state.get("target"),
                "goals_text": state.get("goals_text", ""),
                "local_context": state.get("local_context", ""),
                "features": state.get("features") or {},
            },
            32,
        ),
        "tactic_hash": stable_hash({"tactic": action.get("tactic", "")}, 32),
        "imports_hash": stable_hash({"imports": imports}, 32),
        "lean_version": str(lean_version or "unknown"),
        "workdir_fingerprint": str(workdir_fingerprint_value or ""),
        "import_mode": str(import_mode or "preserve"),
        "max_heartbeats": max_hb,
        "trace_state": 1 if trace_state else 0,
        "lane": str(lane or DEFAULT_CACHE_LANE),
    }
    cache_key = stable_hash(fields, 48)
    return cache_key, fields


def _result_with_cache_flags(result: dict[str, Any], *, cache_key: str) -> dict[str, Any]:
    out = copy.deepcopy(result)
    audit = out.get("audit") if isinstance(out.get("audit"), dict) else None
    if audit is not None:
        flags = audit.get("audit_flags") if isinstance(audit.get("audit_flags"), dict) else {}
        flags = dict(flags)
        flags.update({"cache_hit": True, "audit_cache_key": cache_key})
        audit["audit_flags"] = flags
    response = out.get("response") if isinstance(out.get("response"), dict) else None
    if response is not None:
        flags = response.get("audit_flags") if isinstance(response.get("audit_flags"), dict) else {}
        flags = dict(flags)
        flags.update({"cache_hit": True, "audit_cache_key": cache_key})
        response["audit_flags"] = flags
        response["cache_hit"] = True
        response["audit_cache_key"] = cache_key
    return out


def apply_cache_to_queue(
    *,
    cache_db: str | Path,
    queue_db: str | Path,
    run_id: str,
    lean_version: str,
    workdir_fingerprint_value: str,
    import_mode: str,
    trace_state: bool,
    readonly: bool = False,
) -> dict[str, Any]:
    qconn = connect_queue(queue_db)
    cconn: sqlite3.Connection | None = None
    try:
        ensure_audit_queue_schema(qconn)
        rows = qconn.execute(
            "SELECT job_id, payload_json, lane FROM audit_jobs WHERE run_id=? AND status='queued'",
            (run_id,),
        ).fetchall()
        if readonly and not Path(cache_db).exists():
            return {
                "schema_version": SCHEMA_AUDIT_RESULT_CACHE,
                "cache_db": str(cache_db),
                "readonly": True,
                "n_cache_lookup": len(rows),
                "n_cache_hit": 0,
                "n_cache_miss": len(rows),
            }
        if readonly:
            uri_path = Path(cache_db).resolve().as_posix()
            cconn = sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True, timeout=60.0)
            cconn.row_factory = sqlite3.Row
        else:
            cconn = connect_audit_cache(cache_db)
            ensure_audit_cache_schema(cconn)
        hits = 0
        misses = 0
        now = _now()
        for row in rows:
            payload = _loads(row["payload_json"])
            cache_key, _fields = make_audit_cache_key(
                payload,
                lean_version=lean_version,
                workdir_fingerprint_value=workdir_fingerprint_value,
                import_mode=import_mode,
                trace_state=trace_state,
                lane=str(row["lane"] or DEFAULT_CACHE_LANE),
            )
            try:
                cached = cconn.execute(
                    "SELECT result_json FROM audit_result_cache WHERE cache_key=?",
                    (cache_key,),
                ).fetchone()
            except sqlite3.OperationalError:
                cached = None
            if cached is None:
                misses += 1
                continue
            result = _result_with_cache_flags(_loads(cached["result_json"]), cache_key=cache_key)
            qconn.execute(
                """
                UPDATE audit_jobs
                SET status='succeeded_from_cache', result_json=?, last_error=NULL, leased_until=NULL, updated_at=?
                WHERE job_id=? AND status='queued'
                """,
                (_json(result), now, row["job_id"]),
            )
            if not readonly:
                cconn.execute(
                    """
                    UPDATE audit_result_cache
                    SET hit_count=hit_count+1, last_hit_at=?, updated_at=?
                    WHERE cache_key=?
                    """,
                    (now, now, cache_key),
                )
            hits += 1
        qconn.commit()
        if not readonly:
            cconn.commit()
        return {
            "schema_version": SCHEMA_AUDIT_RESULT_CACHE,
            "cache_db": str(cache_db),
            "readonly": bool(readonly),
            "n_cache_lookup": len(rows),
            "n_cache_hit": hits,
            "n_cache_miss": misses,
        }
    finally:
        qconn.close()
        if cconn is not None:
            cconn.close()


def store_queue_results_in_cache(
    *,
    cache_db: str | Path,
    queue_db: str | Path,
    run_id: str,
    lean_version: str,
    workdir_fingerprint_value: str,
    import_mode: str,
    trace_state: bool,
    readonly: bool = False,
) -> dict[str, Any]:
    if readonly:
        return {
            "schema_version": SCHEMA_AUDIT_RESULT_CACHE,
            "cache_db": str(cache_db),
            "readonly": True,
            "n_store_candidates": 0,
            "n_stored": 0,
            "n_store_skipped": 0,
        }
    qconn = connect_queue(queue_db)
    cconn = connect_audit_cache(cache_db)
    try:
        ensure_audit_queue_schema(qconn)
        ensure_audit_cache_schema(cconn)
        rows = qconn.execute(
            """
            SELECT payload_json, result_json, status, lane
            FROM audit_jobs
            WHERE run_id=? AND status='succeeded' AND result_json IS NOT NULL
            """,
            (run_id,),
        ).fetchall()
        stored = 0
        skipped = 0
        now = _now()
        for row in rows:
            result = _loads(row["result_json"])
            audit = result.get("audit") if isinstance(result.get("audit"), dict) else {}
            flags = audit.get("audit_flags") if isinstance(audit.get("audit_flags"), dict) else {}
            if flags.get("cache_hit"):
                skipped += 1
                continue
            payload = _loads(row["payload_json"])
            cache_key, fields = make_audit_cache_key(
                payload,
                lean_version=lean_version,
                workdir_fingerprint_value=workdir_fingerprint_value,
                import_mode=import_mode,
                trace_state=trace_state,
                lane=str(row["lane"] or DEFAULT_CACHE_LANE),
            )
            audit_status = str(audit.get("status") or "")
            cconn.execute(
                """
                INSERT INTO audit_result_cache(
                    cache_key, task_hash, state_hash, tactic_hash, imports_hash,
                    lean_version, workdir_fingerprint, import_mode, max_heartbeats,
                    trace_state, lane, audit_status, queue_status, result_json,
                    created_at, updated_at, last_hit_at, hit_count
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    audit_status=excluded.audit_status,
                    queue_status=excluded.queue_status,
                    result_json=excluded.result_json,
                    updated_at=excluded.updated_at
                """,
                (
                    cache_key,
                    fields["task_hash"],
                    fields["state_hash"],
                    fields["tactic_hash"],
                    fields["imports_hash"],
                    fields["lean_version"],
                    fields["workdir_fingerprint"],
                    fields["import_mode"],
                    fields["max_heartbeats"],
                    int(fields["trace_state"]),
                    fields["lane"],
                    audit_status,
                    str(row["status"]),
                    _json(result),
                    now,
                    now,
                    None,
                    0,
                ),
            )
            stored += 1
        cconn.commit()
        return {
            "schema_version": SCHEMA_AUDIT_RESULT_CACHE,
            "cache_db": str(cache_db),
            "readonly": False,
            "n_store_candidates": len(rows),
            "n_stored": stored,
            "n_store_skipped": skipped,
        }
    finally:
        qconn.close()
        cconn.close()


def audit_cache_report(db_path: str | Path) -> dict[str, Any]:
    conn = connect_audit_cache(db_path)
    try:
        ensure_audit_cache_schema(conn)
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS n_rows,
                COALESCE(SUM(hit_count), 0) AS n_hits,
                COALESCE(MAX(updated_at), 0) AS last_updated_at
            FROM audit_result_cache
            """
        ).fetchone()
        by_status = {
            str(status): int(n)
            for status, n in conn.execute(
                "SELECT COALESCE(audit_status,''), COUNT(*) FROM audit_result_cache GROUP BY audit_status ORDER BY audit_status"
            )
        }
        return {
            "schema_version": SCHEMA_AUDIT_RESULT_CACHE,
            "db_path": str(db_path),
            "n_rows": int(row["n_rows"] or 0),
            "n_hits": int(row["n_hits"] or 0),
            "last_updated_at": float(row["last_updated_at"] or 0.0),
            "by_audit_status": by_status,
        }
    finally:
        conn.close()


__all__ = [
    "DEFAULT_CACHE_LANE",
    "SCHEMA_AUDIT_RESULT_CACHE",
    "apply_cache_to_queue",
    "audit_cache_report",
    "connect_audit_cache",
    "detect_lean_version",
    "ensure_audit_cache_schema",
    "make_audit_cache_key",
    "store_queue_results_in_cache",
    "workdir_fingerprint",
]
