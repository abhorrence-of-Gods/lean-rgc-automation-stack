from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3

from ...schemas import stable_hash


CANONICAL_RECORD_SCHEMA = "lean-rgc.canonical.v1"


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _loads(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                obj = {"_parse_error": True, "raw_line": line}
            rows.append(obj if isinstance(obj, dict) else {"value": obj})
    return rows


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _int_bool(value: Any) -> int:
    return 1 if bool(value) else 0


def _row_hash(*parts: Any) -> str:
    return stable_hash(parts, 40)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


class AuditStore:
    def __init__(self, conn: sqlite3.Connection, run_dir: Path, run_id: str):
        self.conn = conn
        self.run_dir = run_dir
        self.run_id = run_id

    def import_tasks_and_actions(self, artifacts: list[sqlite3.Row]) -> None:
        for artifact in artifacts:
            path = Path(str(artifact["abs_path"] or artifact["rel_path"] or ""))
            if path.suffix != ".jsonl":
                continue
            rows = _read_jsonl(path)
            atype = str(artifact["artifact_type"] or artifact["kind"] or "")
            if atype == "tasks":
                for row in rows:
                    task_id = str(row.get("task_id") or row.get("id") or "")
                    if not task_id:
                        continue
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "task", task_id, row)
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO tasks(row_hash, run_id, artifact_id, task_id, source, goal_hash, import_mode, payload_json)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            task_id,
                            str(row.get("source") or path.name),
                            stable_hash({"statement": row.get("statement"), "target": row.get("target")}, 32),
                            str(row.get("import_mode") or ""),
                            _json(row),
                        ),
                    )
            if atype in {"actions", "hard_candidates"} or any("tactic" in r or "action_id" in r for r in rows):
                for row in rows:
                    action_id = str(row.get("action_id") or row.get("id") or "")
                    tactic = str(row.get("tactic") or "")
                    if not action_id and not tactic:
                        continue
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "action", action_id, tactic, row)
                    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO actions(row_hash, run_id, artifact_id, action_id, tactic_hash, action_kind, source, canonical_status, payload_json)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            action_id or stable_hash(tactic, 16),
                            stable_hash({"tactic": tactic}, 24),
                            str(row.get("tactic_class") or row.get("class") or ""),
                            str(row.get("source") or meta.get("source") or ""),
                            str(row.get("canonical_status") or meta.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )

    def import_queue_ledgers(self) -> None:
        qdb = self.run_dir / "audit" / "audit_queue.sqlite"
        if not qdb.exists():
            return
        src = sqlite3.connect(qdb)
        src.row_factory = sqlite3.Row
        try:
            if _table_exists(src, "audit_jobs"):
                for r in src.execute("SELECT * FROM audit_jobs").fetchall():
                    self.conn.execute(
                        """
                        INSERT OR REPLACE INTO audit_jobs(
                            job_id, run_id, task_id, state_id, action_id, tactic_hash, backend, lane,
                            import_mode, project_fingerprint, status, priority, attempt_count, max_attempts,
                            leased_until, worker_id, created_at, updated_at, payload_json, result_json, last_error
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        tuple(r[k] if k in r.keys() else None for k in [
                            "job_id", "run_id", "task_id", "state_id", "action_id", "tactic_hash", "backend", "lane",
                            "import_mode", "project_fingerprint", "status", "priority", "attempt_count", "max_attempts",
                            "leased_until", "worker_id", "created_at", "updated_at", "payload_json", "result_json", "last_error",
                        ]),
                    )
            if _table_exists(src, "timeout_events"):
                for r in src.execute("SELECT * FROM timeout_events").fetchall():
                    keys = set(r.keys())
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO timeout_events(
                            ts, run_id, job_id, task_id, action_id, tactic_hash, backend, lane,
                            timeout_s, elapsed_s, stdout_tail, stderr_tail, worker_id, timeout_scope, detail_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            r["ts"] if "ts" in keys else None,
                            self.run_id,
                            r["job_id"] if "job_id" in keys else None,
                            r["task_id"] if "task_id" in keys else None,
                            r["action_id"] if "action_id" in keys else None,
                            r["tactic_hash"] if "tactic_hash" in keys else None,
                            r["backend"] if "backend" in keys else None,
                            r["lane"] if "lane" in keys else None,
                            r["timeout_s"] if "timeout_s" in keys else None,
                            r["elapsed_s"] if "elapsed_s" in keys else None,
                            r["stdout_tail"] if "stdout_tail" in keys else None,
                            r["stderr_tail"] if "stderr_tail" in keys else None,
                            r["worker_id"] if "worker_id" in keys else None,
                            r["timeout_scope"] if "timeout_scope" in keys else "unknown_timeout",
                            r["detail_json"] if "detail_json" in keys else None,
                        ),
                    )
            if _table_exists(src, "worker_events"):
                for r in src.execute("SELECT * FROM worker_events").fetchall():
                    keys = set(r.keys())
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO worker_events(
                            ts, run_id, worker_id, event_type, job_id, backend, lane, detail_json
                        ) VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            r["ts"] if "ts" in keys else None,
                            self.run_id,
                            r["worker_id"] if "worker_id" in keys else None,
                            r["event_type"] if "event_type" in keys else None,
                            r["job_id"] if "job_id" in keys else None,
                            r["backend"] if "backend" in keys else None,
                            r["lane"] if "lane" in keys else None,
                            r["detail_json"] if "detail_json" in keys else None,
                        ),
                    )
            if _table_exists(src, "action_quarantine"):
                for r in src.execute("SELECT * FROM action_quarantine").fetchall():
                    self.conn.execute(
                        """
                        INSERT OR REPLACE INTO action_quarantine(
                            key_type, key_value, run_id, status, reason, n_attempts, n_timeouts,
                            timeout_rate, first_seen, updated_at, detail_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            r["key_type"], r["key_value"], self.run_id, r["status"], r["reason"], r["n_attempts"],
                            r["n_timeouts"], r["timeout_rate"], r["first_seen"], r["updated_at"], r["detail_json"],
                        ),
                    )
        finally:
            src.close()

    def import_cache_summary(self) -> None:
        summary = _read_json(self.run_dir / "audit" / "summary.json")
        if not isinstance(summary, dict):
            return
        cache = summary.get("audit_cache") if isinstance(summary.get("audit_cache"), dict) else {}
        if not cache:
            return
        apply = cache.get("apply") if isinstance(cache.get("apply"), dict) else {}
        store = cache.get("store") if isinstance(cache.get("store"), dict) else {}
        row = {
            "cache": cache,
            "summary_path": str(self.run_dir / "audit" / "summary.json"),
        }
        rh = _row_hash(self.run_id, "audit_cache", row)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO audit_result_cache_index(
                row_hash, run_id, cache_db, n_cache_lookup, n_cache_hit, n_cache_miss, n_stored, readonly, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                rh,
                self.run_id,
                str(cache.get("cache_db") or summary.get("audit_cache_db") or ""),
                int(apply.get("n_cache_lookup") or 0),
                int(apply.get("n_cache_hit") or summary.get("n_cache_hit") or 0),
                int(apply.get("n_cache_miss") or 0),
                int(store.get("n_stored") or store.get("n_store_candidates") or 0),
                _int_bool(cache.get("readonly") or summary.get("audit_cache_readonly")),
                _json(row),
            ),
        )


def import_audit_artifacts(store: AuditStore, artifacts: list[Any]) -> None:
    store.import_tasks_and_actions(artifacts)
    store.import_queue_ledgers()
    store.import_cache_summary()


def materialize_canonical_run_tables(conn: sqlite3.Connection, run_id: str) -> None:
    if _table_exists(conn, "response_rows"):
        for r in conn.execute(
            """
            SELECT rr.artifact_id, rr.row_index, rr.state_id, rr.action_id, rr.audit_status,
                   rr.response_json, rr.carrier_delta_json, rr.defect_before_json,
                   rr.defect_after_json, rr.raw_json, a.run_id
            FROM response_rows rr
            LEFT JOIN artifacts a ON a.artifact_id=rr.artifact_id
            """
        ).fetchall():
            rid = str(r["run_id"] or run_id)
            raw = _loads(r["raw_json"]) if "raw_json" in r.keys() else None
            raw = raw if isinstance(raw, dict) else {}
            response_id = str(raw.get("response_id") or "response_" + stable_hash(
                {"run_id": rid, "artifact_id": r["artifact_id"], "row_index": r["row_index"], "state_id": r["state_id"], "action_id": r["action_id"]},
                32,
            ))
            task_id = str(raw.get("task_id") or r["state_id"] or "")
            after_state = raw.get("after_state") if isinstance(raw.get("after_state"), dict) else {}
            payload = {
                "response": _loads(r["response_json"]),
                "carrier_delta": _loads(r["carrier_delta_json"]),
                "defect_before": _loads(r["defect_before_json"]),
                "defect_after": _loads(r["defect_after_json"]),
            }
            conn.execute(
                """
                INSERT OR REPLACE INTO responses(
                    response_id, schema_version, run_id, artifact_id, row_index, task_id,
                    action_id, status, elapsed_ms, state_before_id, state_after_id,
                    response_json, carrier_delta_json, payload_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    response_id,
                    CANONICAL_RECORD_SCHEMA,
                    rid,
                    r["artifact_id"],
                    r["row_index"],
                    task_id,
                    str(r["action_id"] or raw.get("action_id") or ""),
                    str(r["audit_status"] or raw.get("status") or ""),
                    _float(raw.get("elapsed_ms"), 0.0),
                    str(r["state_id"] or raw.get("state_before_id") or ""),
                    str(after_state.get("state_id") or raw.get("state_after_id") or ""),
                    str(r["response_json"] or "{}"),
                    str(r["carrier_delta_json"] or "{}"),
                    _json(payload),
                ),
            )
    if _table_exists(conn, "audit_rows"):
        for r in conn.execute(
            """
            SELECT ar.artifact_id, ar.row_index, ar.task_id, ar.state_id, ar.action_id,
                   ar.status, ar.elapsed_ms, ar.heartbeats, ar.audit_flags_json, a.run_id
            FROM audit_rows ar
            LEFT JOIN artifacts a ON a.artifact_id=ar.artifact_id
            """
        ).fetchall():
            rid = str(r["run_id"] or run_id)
            response_id = "response_" + stable_hash(
                {"run_id": rid, "artifact_id": r["artifact_id"], "row_index": r["row_index"], "state_id": r["state_id"], "action_id": r["action_id"]},
                32,
            )
            event_id = "audit_event_" + stable_hash(
                {"run_id": rid, "artifact_id": r["artifact_id"], "row_index": r["row_index"], "task_id": r["task_id"], "action_id": r["action_id"]},
                32,
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_events(
                    event_id, schema_version, run_id, artifact_id, row_index, task_id,
                    action_id, status, elapsed_ms, heartbeats, response_id, payload_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_id,
                    CANONICAL_RECORD_SCHEMA,
                    rid,
                    r["artifact_id"],
                    r["row_index"],
                    str(r["task_id"] or r["state_id"] or ""),
                    str(r["action_id"] or ""),
                    str(r["status"] or ""),
                    _float(r["elapsed_ms"], 0.0),
                    _float(r["heartbeats"], 0.0),
                    response_id,
                    _json({"audit_flags": _loads(r["audit_flags_json"])}),
                ),
            )


__all__ = ["AuditStore", "import_audit_artifacts", "materialize_canonical_run_tables"]
