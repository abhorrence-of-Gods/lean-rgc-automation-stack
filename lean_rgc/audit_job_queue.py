from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import sqlite3
import time

from .schemas import LeanTask, ProofState, TacticAction, stable_hash


SCHEMA_AUDIT_QUEUE = "lean-rgc-audit-job-queue-v63.0"

JOB_STATUSES = {
    "queued",
    "leased",
    "running",
    "succeeded",
    "failed",
    "timeout",
    "quarantined",
    "cancelled",
}


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


def connect_queue(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_audit_queue_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_jobs (
            job_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            state_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            tactic_hash TEXT NOT NULL,
            backend TEXT NOT NULL,
            lane TEXT NOT NULL DEFAULT 'source_check',
            import_mode TEXT NOT NULL DEFAULT 'preserve',
            project_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            priority REAL NOT NULL DEFAULT 0.0,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 1,
            leased_until REAL,
            worker_id TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            payload_json TEXT NOT NULL,
            result_json TEXT,
            last_error TEXT,
            UNIQUE(run_id, task_id, state_id, action_id, backend, import_mode, project_fingerprint)
        );
        CREATE INDEX IF NOT EXISTS idx_audit_jobs_status ON audit_jobs(status, priority DESC, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_jobs_action ON audit_jobs(action_id, tactic_hash);
        CREATE INDEX IF NOT EXISTS idx_audit_jobs_run ON audit_jobs(run_id, status);
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("audit_queue_schema_version", SCHEMA_AUDIT_QUEUE))
    conn.commit()


def init_audit_queue_db(db_path: str | Path) -> dict[str, Any]:
    conn = connect_queue(db_path)
    try:
        ensure_audit_queue_schema(conn)
        return audit_queue_status(conn)
    finally:
        conn.close()


def project_fingerprint(*, lean_cmd: str | None = None, workdir: str | None = None, backend: str | None = None, import_mode: str | None = None) -> str:
    return stable_hash(
        {
            "lean_cmd": lean_cmd or "",
            "workdir": str(Path(workdir).resolve()) if workdir else "",
            "backend": backend or "",
            "import_mode": import_mode or "",
        },
        24,
    )


def make_job_id(
    *,
    run_id: str,
    task_id: str,
    state_id: str,
    action_id: str,
    backend: str,
    import_mode: str,
    project_fingerprint: str,
) -> str:
    return "audjob_" + stable_hash(
        {
            "run_id": run_id,
            "task_id": task_id,
            "state_id": state_id,
            "action_id": action_id,
            "backend": backend,
            "import_mode": import_mode,
            "project_fingerprint": project_fingerprint,
        },
        24,
    )


@dataclass
class AuditJob:
    job_id: str
    run_id: str
    task_id: str
    state_id: str
    action_id: str
    tactic_hash: str
    backend: str
    lane: str
    import_mode: str
    project_fingerprint: str
    status: str
    attempt_count: int
    max_attempts: int
    payload: dict[str, Any]
    worker_id: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> "AuditJob":
        get = row.__getitem__ if isinstance(row, sqlite3.Row) else row.get
        return cls(
            job_id=str(get("job_id")),
            run_id=str(get("run_id")),
            task_id=str(get("task_id")),
            state_id=str(get("state_id")),
            action_id=str(get("action_id")),
            tactic_hash=str(get("tactic_hash")),
            backend=str(get("backend")),
            lane=str(get("lane")),
            import_mode=str(get("import_mode")),
            project_fingerprint=str(get("project_fingerprint")),
            status=str(get("status")),
            attempt_count=int(get("attempt_count") or 0),
            max_attempts=int(get("max_attempts") or 1),
            payload=_loads(str(get("payload_json") or "")),
            worker_id=str(get("worker_id")) if get("worker_id") is not None else None,
        )


def build_job_payload(task: LeanTask, action: TacticAction, *, state: ProofState | None = None, lane: str = "source_check") -> dict[str, Any]:
    st = state or ProofState.from_task(task)
    return {
        "task": task.to_dict(),
        "state": st.to_dict(),
        "action": action.to_dict(),
        "lane": lane,
    }


def enqueue_audit_jobs(
    db_path: str | Path,
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    *,
    run_id: str,
    backend: str,
    import_mode: str,
    project_fingerprint_value: str,
    max_actions: int = 64,
    max_attempts: int = 1,
    lane: str = "source_check",
    priority: float = 0.0,
) -> dict[str, Any]:
    conn = connect_queue(db_path)
    try:
        ensure_audit_queue_schema(conn)
        inserted = 0
        reused = 0
        now = _now()
        for task in tasks:
            state = ProofState.from_task(task)
            actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
            for action in list(actions)[: max(0, int(max_actions or 0))]:
                tactic_hash = stable_hash({"tactic": action.tactic}, 24)
                jid = make_job_id(
                    run_id=run_id,
                    task_id=task.task_id,
                    state_id=state.state_id,
                    action_id=action.action_id,
                    backend=backend,
                    import_mode=import_mode,
                    project_fingerprint=project_fingerprint_value,
                )
                payload = build_job_payload(task, action, state=state, lane=lane)
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO audit_jobs(
                        job_id, run_id, task_id, state_id, action_id, tactic_hash,
                        backend, lane, import_mode, project_fingerprint, status,
                        priority, attempt_count, max_attempts, created_at, updated_at,
                        payload_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        jid,
                        run_id,
                        task.task_id,
                        state.state_id,
                        action.action_id,
                        tactic_hash,
                        backend,
                        lane,
                        import_mode,
                        project_fingerprint_value,
                        "queued",
                        float(priority),
                        0,
                        int(max_attempts or 1),
                        now,
                        now,
                        _json(payload),
                    ),
                )
                if cur.rowcount:
                    inserted += 1
                else:
                    reused += 1
        conn.commit()
        rep = audit_queue_status(conn)
        rep.update({"n_inserted": inserted, "n_reused": reused, "db_path": str(db_path), "run_id": run_id})
        return rep
    finally:
        conn.close()


def lease_next_job(
    conn: sqlite3.Connection,
    *,
    worker_id: str,
    lease_seconds: float = 300.0,
    lanes: Iterable[str] | None = None,
    include_quarantined: bool = False,
) -> AuditJob | None:
    ensure_audit_queue_schema(conn)
    now = _now()
    lane_list = [str(x) for x in (lanes or []) if str(x)]
    lane_sql = ""
    params: list[Any] = [now]
    if lane_list:
        lane_sql = " AND lane IN (%s)" % ",".join("?" for _ in lane_list)
        params.extend(lane_list)
    quarantine_sql = "" if include_quarantined else " AND status != 'quarantined'"
    row = conn.execute(
        f"""
        SELECT * FROM audit_jobs
        WHERE (
            status = 'queued'
            OR (status IN ('leased','running') AND COALESCE(leased_until, 0) < ?)
            OR (status = 'failed' AND attempt_count < max_attempts)
        )
        {lane_sql}
        {quarantine_sql}
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        """,
        params,
    ).fetchone()
    if row is None:
        return None
    leased_until = now + max(1.0, float(lease_seconds or 300.0))
    conn.execute(
        """
        UPDATE audit_jobs
        SET status='leased', leased_until=?, worker_id=?, updated_at=?
        WHERE job_id=?
        """,
        (leased_until, worker_id, now, row["job_id"]),
    )
    conn.commit()
    fresh = conn.execute("SELECT * FROM audit_jobs WHERE job_id=?", (row["job_id"],)).fetchone()
    return AuditJob.from_row(fresh)


def mark_job_running(conn: sqlite3.Connection, job_id: str, *, worker_id: str) -> None:
    now = _now()
    conn.execute(
        """
        UPDATE audit_jobs
        SET status='running', worker_id=?, attempt_count=attempt_count+1, updated_at=?
        WHERE job_id=?
        """,
        (worker_id, now, job_id),
    )
    conn.commit()


def mark_job_result(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    if status not in JOB_STATUSES:
        raise ValueError(f"unknown audit job status: {status}")
    now = _now()
    conn.execute(
        """
        UPDATE audit_jobs
        SET status=?, result_json=?, last_error=?, leased_until=NULL, updated_at=?
        WHERE job_id=?
        """,
        (status, _json(result or {}), error, now, job_id),
    )
    conn.commit()


def cancel_jobs(db_path: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    conn = connect_queue(db_path)
    try:
        ensure_audit_queue_schema(conn)
        now = _now()
        if run_id:
            cur = conn.execute(
                "UPDATE audit_jobs SET status='cancelled', updated_at=? WHERE run_id=? AND status IN ('queued','leased','running','failed')",
                (now, run_id),
            )
        else:
            cur = conn.execute(
                "UPDATE audit_jobs SET status='cancelled', updated_at=? WHERE status IN ('queued','leased','running','failed')",
                (now,),
            )
        conn.commit()
        rep = audit_queue_status(conn, run_id=run_id)
        rep["n_cancelled_now"] = int(cur.rowcount or 0)
        return rep
    finally:
        conn.close()


def audit_queue_status(conn_or_path: sqlite3.Connection | str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    owns = not isinstance(conn_or_path, sqlite3.Connection)
    conn = connect_queue(conn_or_path) if owns else conn_or_path
    try:
        ensure_audit_queue_schema(conn)
        params: list[Any] = []
        where = ""
        if run_id:
            where = "WHERE run_id=?"
            params.append(run_id)
        by_status = {
            str(status): int(n)
            for status, n in conn.execute(f"SELECT status, COUNT(*) FROM audit_jobs {where} GROUP BY status ORDER BY status", params)
        }
        n_jobs = sum(by_status.values())
        by_lane = {
            str(lane): int(n)
            for lane, n in conn.execute(f"SELECT lane, COUNT(*) FROM audit_jobs {where} GROUP BY lane ORDER BY lane", params)
        }
        return {
            "schema_version": SCHEMA_AUDIT_QUEUE,
            "run_id": run_id,
            "n_jobs": n_jobs,
            "by_status": by_status,
            "by_lane": by_lane,
            "n_succeeded": by_status.get("succeeded", 0),
            "n_failed": by_status.get("failed", 0),
            "n_timeout": by_status.get("timeout", 0),
            "n_quarantined": by_status.get("quarantined", 0),
        }
    finally:
        if owns:
            conn.close()


def iter_jobs(db_path: str | Path, *, run_id: str | None = None, status: str | None = None, limit: int | None = None) -> list[AuditJob]:
    conn = connect_queue(db_path)
    try:
        ensure_audit_queue_schema(conn)
        clauses: list[str] = []
        params: list[Any] = []
        if run_id:
            clauses.append("run_id=?")
            params.append(run_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM audit_jobs {where} ORDER BY created_at ASC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [AuditJob.from_row(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


__all__ = [
    "SCHEMA_AUDIT_QUEUE",
    "AuditJob",
    "audit_queue_status",
    "build_job_payload",
    "cancel_jobs",
    "connect_queue",
    "enqueue_audit_jobs",
    "ensure_audit_queue_schema",
    "init_audit_queue_db",
    "iter_jobs",
    "lease_next_job",
    "make_job_id",
    "mark_job_result",
    "mark_job_running",
    "project_fingerprint",
]
