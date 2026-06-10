from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import sqlite3
import time

from ..audit_db import build_audit_db, discover_artifacts, query_audit_db
from ..repair_db import import_repair_artifacts, summarize_repair_db
from ..schemas import stable_hash


SCHEMA_RUN_DB = "lean-rgc-run-db-v1.0"


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _loads(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _schema_version(path: Path, rows: list[dict[str, Any]] | None = None) -> str:
    if path.suffix == ".json":
        obj = _read_json(path)
        if isinstance(obj, dict) and obj.get("schema_version"):
            return str(obj.get("schema_version"))
    for row in rows or []:
        if isinstance(row, dict) and row.get("schema_version"):
            return str(row.get("schema_version"))
    return "legacy.unknown"


def _artifact_type(path: Path) -> str:
    name = path.name
    parent = path.parent.name
    if name == "micro_audit.jsonl":
        return "audit_rows"
    if name == "responses.jsonl":
        return "response_rows"
    if name.endswith("_tasks.jsonl") or name in {"tasks.jsonl", "frontier_tasks.jsonl"}:
        return "tasks"
    if name == "hard_candidates.jsonl":
        return "hard_candidates"
    if name.endswith("actions.jsonl"):
        return "actions"
    if name == "repair_faces.jsonl" or "repair_face" in name or name == "tower_faces.jsonl":
        return "repair_faces"
    if name == "concept_decoded_repair_atoms.jsonl":
        return "concept_decoded_repair_atoms"
    if parent == "crg":
        return name.removesuffix(".jsonl").removesuffix(".json")
    if parent == "concept_geometry":
        return name.removesuffix(".jsonl").removesuffix(".json")
    if "poms" in name and "evidence" in name:
        return "poms_evidence"
    if "promotion_decision" in name or "decisions" in name:
        return "poms_promotion_decisions"
    if "lineage" in name:
        return "lineage"
    if name.endswith(".json"):
        return "json_report"
    return "jsonl"


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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if table in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")} and column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def ensure_run_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            run_dir TEXT,
            git_sha TEXT,
            config_hash TEXT,
            status TEXT,
            started_at REAL,
            finished_at REAL,
            artifact_store_root TEXT,
            payload_json TEXT
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_dir TEXT,
            rel_path TEXT,
            abs_path TEXT,
            kind TEXT,
            round INTEGER,
            sha256 TEXT,
            n_rows INTEGER,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
            run_id TEXT,
            artifact_type TEXT,
            schema_version TEXT,
            uri TEXT,
            created_at REAL,
            payload_json TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_run_artifacts_unique ON artifacts(abs_path, sha256);
        CREATE TABLE IF NOT EXISTS tasks (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            artifact_id INTEGER,
            task_id TEXT,
            source TEXT,
            goal_hash TEXT,
            import_mode TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_tasks_task ON tasks(task_id);
        CREATE TABLE IF NOT EXISTS actions (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            artifact_id INTEGER,
            action_id TEXT,
            tactic_hash TEXT,
            action_kind TEXT,
            source TEXT,
            canonical_status TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_actions_action ON actions(action_id);
        CREATE TABLE IF NOT EXISTS audit_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            task_id TEXT,
            state_id TEXT,
            action_id TEXT,
            status TEXT,
            elapsed_ms REAL,
            heartbeats REAL,
            response_json TEXT,
            carrier_delta_json TEXT,
            defect_before_json TEXT,
            defect_after_json TEXT,
            audit_flags_json TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_run_audit_task_action ON audit_rows(task_id, action_id);
        CREATE TABLE IF NOT EXISTS response_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            audit_status TEXT,
            success INTEGER,
            response_json TEXT,
            carrier_delta_json TEXT,
            defect_before_json TEXT,
            defect_after_json TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE INDEX IF NOT EXISTS idx_run_response_state_action ON response_rows(state_id, action_id);
        CREATE TABLE IF NOT EXISTS response_values (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            response_key TEXT,
            value REAL
        );
        CREATE TABLE IF NOT EXISTS carrier_values (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            state_id TEXT,
            action_id TEXT,
            carrier_key TEXT,
            value REAL
        );
        CREATE TABLE IF NOT EXISTS action_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            action_id TEXT,
            tactic TEXT,
            tactic_class TEXT,
            source TEXT,
            canonical_status TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE TABLE IF NOT EXISTS acceptance_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            action_id TEXT,
            state_id TEXT,
            accepted INTEGER,
            margin REAL,
            robust_margin REAL,
            score REAL,
            accepted_by TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE TABLE IF NOT EXISTS poms_rows (
            artifact_id INTEGER,
            row_index INTEGER,
            round INTEGER,
            record_id TEXT,
            kind TEXT,
            status TEXT,
            promoted_status TEXT,
            canonical_status TEXT,
            action_id TEXT,
            carrier_atom TEXT,
            residual_key TEXT,
            raw_json TEXT,
            PRIMARY KEY (artifact_id, row_index)
        );
        CREATE TABLE IF NOT EXISTS json_reports (
            artifact_id INTEGER PRIMARY KEY,
            round INTEGER,
            kind TEXT,
            raw_json TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_jobs (
            job_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            task_id TEXT,
            state_id TEXT,
            action_id TEXT,
            tactic_hash TEXT,
            backend TEXT,
            lane TEXT,
            import_mode TEXT,
            project_fingerprint TEXT,
            status TEXT,
            priority REAL DEFAULT 0.0,
            attempt_count INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 1,
            leased_until REAL,
            worker_id TEXT,
            created_at REAL,
            updated_at REAL,
            payload_json TEXT,
            result_json TEXT,
            last_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_audit_jobs_status ON audit_jobs(run_id, status);
        CREATE TABLE IF NOT EXISTS timeout_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            run_id TEXT,
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
            timeout_scope TEXT,
            detail_json TEXT
        );
        CREATE TABLE IF NOT EXISTS action_quarantine (
            key_type TEXT NOT NULL,
            key_value TEXT NOT NULL,
            run_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            n_attempts INTEGER NOT NULL DEFAULT 0,
            n_timeouts INTEGER NOT NULL DEFAULT 0,
            timeout_rate REAL NOT NULL DEFAULT 0.0,
            first_seen REAL,
            updated_at REAL,
            detail_json TEXT,
            PRIMARY KEY(run_id, key_type, key_value)
        );
        CREATE TABLE IF NOT EXISTS audit_result_cache_index (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            cache_db TEXT,
            n_cache_lookup INTEGER DEFAULT 0,
            n_cache_hit INTEGER DEFAULT 0,
            n_cache_miss INTEGER DEFAULT 0,
            n_stored INTEGER DEFAULT 0,
            readonly INTEGER DEFAULT 0,
            payload_json TEXT
        );
        CREATE TABLE IF NOT EXISTS repair_faces (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            artifact_id INTEGER,
            face_id TEXT,
            obstruction_id TEXT,
            parent_face_id TEXT,
            canonical_status TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_repair_faces_face ON repair_faces(face_id);
        CREATE TABLE IF NOT EXISTS hard_candidates (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            artifact_id INTEGER,
            action_id TEXT,
            candidate_id TEXT,
            hardening_id TEXT,
            tactic TEXT,
            canonical_status TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_hard_candidates_action ON hard_candidates(action_id);
        CREATE TABLE IF NOT EXISTS repair_atoms (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            repair_atom_id TEXT,
            species_id TEXT,
            source TEXT,
            source_id TEXT,
            cost REAL,
            audit_risk REAL,
            source_risk REAL,
            ghost_risk REAL,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS crg_problems (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            problem_id TEXT,
            parent_face_id TEXT,
            obstruction_id TEXT,
            repair_space_scope TEXT,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS relaxed_candidates (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            candidate_id TEXT,
            problem_id TEXT,
            repair_species TEXT,
            relaxed_score REAL,
            cost REAL,
            audit_risk REAL,
            source_risk REAL,
            ghost_risk REAL,
            net_score REAL,
            n_feasible_atoms INTEGER,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS hardening_attempts (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            hardening_id TEXT,
            candidate_id TEXT,
            hardening_method TEXT,
            hardening_status TEXT,
            hardening_gap REAL,
            n_hard_candidates INTEGER,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS crg_audit_rows (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            candidate_id TEXT,
            problem_id TEXT,
            relaxed_score REAL,
            audited_score REAL,
            hardening_gap REAL,
            heldout_score REAL,
            ghost_risk REAL,
            source_safe INTEGER,
            carrier_safe INTEGER,
            promotion_readiness TEXT,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS concept_points (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            concept_id TEXT,
            concept_species TEXT,
            origin TEXT,
            audit_risk REAL,
            hardening_risk REAL,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS concept_search_rows (
            row_hash TEXT PRIMARY KEY,
            run_dir TEXT,
            artifact_path TEXT,
            concept_id TEXT,
            score REAL,
            mode TEXT,
            target_species TEXT,
            canonical_status TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS poms_evidence (
            row_hash TEXT PRIMARY KEY,
            run_id TEXT,
            artifact_id INTEGER,
            evidence_id TEXT,
            candidate_id TEXT,
            action_id TEXT,
            parent_nonpaid INTEGER,
            dual_certificate INTEGER,
            least_repair INTEGER,
            payload_json TEXT
        );
        CREATE TABLE IF NOT EXISTS poms_promotion_decisions (
            decision_id TEXT PRIMARY KEY,
            ts REAL,
            run_id TEXT,
            candidate_id TEXT,
            action_id TEXT,
            parent_nonpaid INTEGER,
            dual_certificate INTEGER,
            least_repair INTEGER,
            promotion_status TEXT,
            canonical_status TEXT,
            reason TEXT,
            row_json TEXT
        );
        CREATE TABLE IF NOT EXISTS lineage_edges (
            artifact_id INTEGER,
            edge_index INTEGER,
            src TEXT,
            dst TEXT,
            edge_type TEXT,
            raw_json TEXT,
            edge_id TEXT,
            run_id TEXT,
            src_type TEXT,
            src_id TEXT,
            dst_type TEXT,
            dst_id TEXT,
            payload_json TEXT,
            PRIMARY KEY (artifact_id, edge_index)
        );
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("run_db_schema_version", SCHEMA_RUN_DB))
    if _table_exists(conn, "artifacts"):
        _ensure_column(conn, "artifacts", "run_id", "TEXT")
        _ensure_column(conn, "artifacts", "artifact_type", "TEXT")
        _ensure_column(conn, "artifacts", "schema_version", "TEXT")
        _ensure_column(conn, "artifacts", "uri", "TEXT")
        _ensure_column(conn, "artifacts", "created_at", "REAL")
        _ensure_column(conn, "artifacts", "payload_json", "TEXT")
    if _table_exists(conn, "timeout_events"):
        _ensure_column(conn, "timeout_events", "run_id", "TEXT")
        _ensure_column(conn, "timeout_events", "timeout_scope", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_timeout_scope "
            "ON timeout_events(run_id, timeout_scope)"
        )
    if _table_exists(conn, "action_quarantine"):
        _ensure_column(conn, "action_quarantine", "run_id", "TEXT")
    if _table_exists(conn, "poms_promotion_decisions"):
        _ensure_column(conn, "poms_promotion_decisions", "run_id", "TEXT")
        _ensure_column(conn, "poms_promotion_decisions", "promotion_status", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_poms_decisions_status "
            "ON poms_promotion_decisions(run_id, promotion_status)"
        )
    if _table_exists(conn, "lineage_edges"):
        _ensure_column(conn, "lineage_edges", "edge_id", "TEXT")
        _ensure_column(conn, "lineage_edges", "run_id", "TEXT")
        _ensure_column(conn, "lineage_edges", "src_type", "TEXT")
        _ensure_column(conn, "lineage_edges", "src_id", "TEXT")
        _ensure_column(conn, "lineage_edges", "dst_type", "TEXT")
        _ensure_column(conn, "lineage_edges", "dst_id", "TEXT")
        _ensure_column(conn, "lineage_edges", "payload_json", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_lineage_edge_type "
            "ON lineage_edges(run_id, edge_type)"
        )
    conn.commit()


@dataclass
class RunStore:
    db_path: Path
    artifact_store_root: Path | None = None

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        ensure_run_schema(conn)
        return conn

    def upsert_run(self, conn: sqlite3.Connection, *, run_id: str, run_dir: Path, status: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        config_hash = stable_hash(payload.get("config", {}), 32)
        conn.execute(
            """
            INSERT INTO runs(run_id, run_dir, git_sha, config_hash, status, started_at, finished_at, artifact_store_root, payload_json)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_id) DO UPDATE SET
                run_dir=excluded.run_dir,
                config_hash=excluded.config_hash,
                status=excluded.status,
                finished_at=excluded.finished_at,
                artifact_store_root=excluded.artifact_store_root,
                payload_json=excluded.payload_json
            """,
            (
                run_id,
                str(run_dir),
                str(payload.get("git_sha") or ""),
                config_hash,
                status,
                _float(payload.get("started_at"), _now()),
                _now(),
                str(self.artifact_store_root or ""),
                _json(payload),
            ),
        )


class ArtifactStore:
    def __init__(self, conn: sqlite3.Connection, run_dir: Path, run_id: str):
        self.conn = conn
        self.run_dir = run_dir
        self.run_id = run_id

    def refresh_artifact_metadata(self) -> None:
        if not _table_exists(self.conn, "artifacts"):
            return
        for row in self.conn.execute("SELECT artifact_id, abs_path, rel_path, kind FROM artifacts").fetchall():
            path = Path(str(row["abs_path"] or row["rel_path"] or ""))
            rows = _read_jsonl(path) if path.suffix == ".jsonl" else None
            schema = _schema_version(path, rows)
            artifact_type = _artifact_type(path)
            payload = {"kind": row["kind"], "rel_path": row["rel_path"]}
            self.conn.execute(
                """
                UPDATE artifacts
                SET run_id=?, artifact_type=?, schema_version=?, uri=?, created_at=COALESCE(created_at, ?), payload_json=?
                WHERE artifact_id=?
                """,
                (self.run_id, artifact_type, schema, str(path), _now(), _json(payload), row["artifact_id"]),
            )

    def artifact_rows(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT artifact_id, abs_path, rel_path, artifact_type, kind FROM artifacts ORDER BY artifact_id"))


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
                            "leased_until", "worker_id", "created_at", "updated_at", "payload_json", "result_json", "last_error"
                        ]),
                    )
            if _table_exists(src, "timeout_events"):
                for r in src.execute("SELECT * FROM timeout_events").fetchall():
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO timeout_events(
                            ts, run_id, job_id, task_id, action_id, tactic_hash, backend, lane,
                            timeout_s, elapsed_s, stdout_tail, stderr_tail, worker_id, timeout_scope, detail_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            r["ts"], self.run_id, r["job_id"], r["task_id"], r["action_id"], r["tactic_hash"],
                            r["backend"], r["lane"], r["timeout_s"], r["elapsed_s"], r["stdout_tail"],
                            r["stderr_tail"], r["worker_id"], r["timeout_scope"], r["detail_json"],
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


class RepairStore:
    def __init__(self, conn: sqlite3.Connection, run_dir: Path, run_id: str):
        self.conn = conn
        self.run_dir = run_dir
        self.run_id = run_id

    def import_supplemental_repair_artifacts(self, artifacts: list[sqlite3.Row]) -> None:
        for artifact in artifacts:
            path = Path(str(artifact["abs_path"] or artifact["rel_path"] or ""))
            if path.suffix != ".jsonl":
                continue
            rows = _read_jsonl(path)
            atype = str(artifact["artifact_type"] or "")
            if atype == "repair_faces":
                for row in rows:
                    face_id = str(row.get("face_id") or row.get("repair_face_id") or row.get("tower_face_id") or "")
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "repair_face", face_id, row)
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO repair_faces(row_hash, run_id, artifact_id, face_id, obstruction_id, parent_face_id, canonical_status, payload_json)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            face_id or rh,
                            str(row.get("obstruction_id") or row.get("lambda_id") or ""),
                            str(row.get("parent_face_id") or ""),
                            str(row.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )
            if atype == "hard_candidates":
                for row in rows:
                    action_id = str(row.get("action_id") or row.get("id") or "")
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "hard_candidate", action_id, row)
                    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO hard_candidates(row_hash, run_id, artifact_id, action_id, candidate_id, hardening_id, tactic, canonical_status, payload_json)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            action_id or rh,
                            str(row.get("candidate_id") or meta.get("candidate_id") or ""),
                            str(row.get("hardening_id") or meta.get("hardening_id") or ""),
                            str(row.get("tactic") or ""),
                            str(row.get("canonical_status") or meta.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )
            if atype == "concept_decoded_repair_atoms":
                for row in rows:
                    atom_id = str(row.get("repair_atom_id") or row.get("atom_id") or "")
                    costs = row.get("cost_vector") if isinstance(row.get("cost_vector"), dict) else {}
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "concept_decoded_repair_atom", atom_id, row)
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO repair_atoms(
                            row_hash, run_dir, artifact_path, repair_atom_id, species_id, source, source_id,
                            cost, audit_risk, source_risk, ghost_risk, canonical_status, row_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            str(self.run_dir),
                            str(path),
                            atom_id or rh,
                            str(row.get("species_id") or row.get("repair_species") or "concept_latent"),
                            str(row.get("source") or "concept_search"),
                            str(row.get("source_id") or ""),
                            _float(costs.get("cost") or costs.get("cost_estimate"), 1.0),
                            _float(costs.get("audit_risk") or row.get("audit_risk"), 0.0),
                            _float(costs.get("source_risk") or row.get("source_risk"), 0.0),
                            _float(costs.get("ghost_risk") or row.get("ghost_risk"), 0.0),
                            str(row.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )


class LineageStore:
    def __init__(self, conn: sqlite3.Connection, run_id: str):
        self.conn = conn
        self.run_id = run_id
        self._edge_index = 10_000_000

    def add_edge(
        self,
        *,
        src_type: str,
        src_id: str,
        dst_type: str,
        dst_id: str,
        edge_type: str,
        artifact_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not src_id or not dst_id:
            return
        payload = payload or {}
        edge_id = "edge_" + stable_hash(
            {
                "run_id": self.run_id,
                "src_type": src_type,
                "src_id": src_id,
                "dst_type": dst_type,
                "dst_id": dst_id,
                "edge_type": edge_type,
                "payload": payload,
            },
            32,
        )
        self._edge_index += 1
        aid = int(artifact_id or 0)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO lineage_edges(
                artifact_id, edge_index, src, dst, edge_type, raw_json,
                edge_id, run_id, src_type, src_id, dst_type, dst_id, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                aid,
                self._edge_index,
                f"{src_type}:{src_id}",
                f"{dst_type}:{dst_id}",
                edge_type,
                _json(payload),
                edge_id,
                self.run_id,
                src_type,
                src_id,
                dst_type,
                dst_id,
                _json(payload),
            ),
        )

    def materialize_from_tables(self) -> None:
        if _table_exists(self.conn, "audit_rows"):
            for r in self.conn.execute("SELECT artifact_id, row_index, task_id, state_id, action_id FROM audit_rows").fetchall():
                audit_id = f"audit:{r['artifact_id']}:{r['row_index']}"
                self.add_edge(src_type="task", src_id=str(r["task_id"] or r["state_id"] or ""), dst_type="action", dst_id=str(r["action_id"] or ""), edge_type="task_audited_by_action", artifact_id=r["artifact_id"])
                self.add_edge(src_type="action", src_id=str(r["action_id"] or ""), dst_type="audit_response", dst_id=audit_id, edge_type="audit_yields_response", artifact_id=r["artifact_id"])
        if _table_exists(self.conn, "response_rows"):
            for r in self.conn.execute("SELECT artifact_id, row_index, state_id, action_id FROM response_rows").fetchall():
                response_id = f"response:{r['artifact_id']}:{r['row_index']}"
                self.add_edge(src_type="audit_response", src_id=f"audit:{r['artifact_id']}:{r['row_index']}", dst_type="response", dst_id=response_id, edge_type="audit_yields_response", artifact_id=r["artifact_id"])
                self.add_edge(src_type="response", src_id=response_id, dst_type="defect", dst_id=f"defect:{r['state_id']}", edge_type="response_yields_defect", artifact_id=r["artifact_id"])
        if _table_exists(self.conn, "repair_faces") and _table_exists(self.conn, "crg_problems"):
            for r in self.conn.execute("SELECT row_hash, face_id, obstruction_id FROM repair_faces").fetchall():
                self.add_edge(src_type="obstruction", src_id=str(r["obstruction_id"] or ""), dst_type="repair_face", dst_id=str(r["face_id"] or r["row_hash"]), edge_type="obstruction_yields_repair_face")
            for r in self.conn.execute("SELECT problem_id, parent_face_id FROM crg_problems").fetchall():
                self.add_edge(src_type="repair_face", src_id=str(r["parent_face_id"] or ""), dst_type="crg_problem", dst_id=str(r["problem_id"] or ""), edge_type="repair_face_yields_crg_problem")
        if _table_exists(self.conn, "relaxed_candidates"):
            for r in self.conn.execute("SELECT candidate_id, problem_id FROM relaxed_candidates").fetchall():
                self.add_edge(src_type="crg_problem", src_id=str(r["problem_id"] or ""), dst_type="relaxed_candidate", dst_id=str(r["candidate_id"] or ""), edge_type="crg_problem_yields_relaxed_candidate")
        if _table_exists(self.conn, "hardening_attempts"):
            for r in self.conn.execute("SELECT hardening_id, candidate_id FROM hardening_attempts").fetchall():
                self.add_edge(src_type="relaxed_candidate", src_id=str(r["candidate_id"] or ""), dst_type="hardening_attempt", dst_id=str(r["hardening_id"] or ""), edge_type="relaxed_candidate_yields_hardening_attempt")
        if _table_exists(self.conn, "hard_candidates"):
            for r in self.conn.execute("SELECT action_id, candidate_id, hardening_id FROM hard_candidates").fetchall():
                self.add_edge(src_type="hardening_attempt", src_id=str(r["hardening_id"] or r["candidate_id"] or ""), dst_type="hard_candidate", dst_id=str(r["action_id"] or ""), edge_type="hardening_attempt_yields_hard_candidate")
        if _table_exists(self.conn, "crg_audit_rows"):
            for r in self.conn.execute("SELECT candidate_id FROM crg_audit_rows").fetchall():
                self.add_edge(src_type="hard_candidate", src_id=str(r["candidate_id"] or ""), dst_type="audit_response", dst_id=f"crg_audit:{r['candidate_id']}", edge_type="hard_candidate_yields_audit")
        if _table_exists(self.conn, "poms_evidence"):
            for r in self.conn.execute("SELECT evidence_id, action_id FROM poms_evidence").fetchall():
                self.add_edge(src_type="audit_response", src_id=str(r["action_id"] or ""), dst_type="poms_evidence", dst_id=str(r["evidence_id"] or ""), edge_type="audit_yields_poms_evidence")
        if _table_exists(self.conn, "poms_promotion_decisions"):
            for r in self.conn.execute("SELECT decision_id, action_id FROM poms_promotion_decisions").fetchall():
                self.add_edge(src_type="poms_evidence", src_id=str(r["action_id"] or ""), dst_type="poms_promotion_decision", dst_id=str(r["decision_id"] or ""), edge_type="poms_evidence_yields_promotion_decision")
        if _table_exists(self.conn, "concept_search_rows"):
            for r in self.conn.execute("SELECT row_hash, concept_id, row_json FROM concept_search_rows").fetchall():
                payload = _loads(r["row_json"]) if "row_json" in r.keys() else None
                if not isinstance(payload, dict):
                    payload = {}
                search_id = str(payload.get("search_row_id") or r["row_hash"] or "")
                concept_id = str(r["concept_id"] or payload.get("concept_id") or "")
                self.add_edge(
                    src_type="concept_point",
                    src_id=concept_id,
                    dst_type="concept_search_row",
                    dst_id=search_id,
                    edge_type="concept_point_yields_search_witness",
                    payload={"row_hash": r["row_hash"]},
                )
        if _table_exists(self.conn, "repair_atoms"):
            for r in self.conn.execute("SELECT repair_atom_id, species_id, source, source_id, row_json FROM repair_atoms").fetchall():
                if str(r["species_id"] or "") != "concept_latent":
                    continue
                payload = _loads(r["row_json"]) if "row_json" in r.keys() else None
                if not isinstance(payload, dict):
                    payload = {}
                source_row = payload.get("provenance", {}).get("source_row") if isinstance(payload.get("provenance"), dict) else {}
                meta = source_row.get("metadata") if isinstance(source_row, dict) and isinstance(source_row.get("metadata"), dict) else {}
                search_id = str(meta.get("concept_search_row_id") or "")
                concept_id = str(meta.get("concept_id") or r["source_id"] or "")
                if search_id:
                    self.add_edge(
                        src_type="concept_search_row",
                        src_id=search_id,
                        dst_type="repair_atom",
                        dst_id=str(r["repair_atom_id"] or ""),
                        edge_type="concept_search_yields_repair_atom",
                    )
                elif concept_id:
                    self.add_edge(
                        src_type="concept_point",
                        src_id=concept_id,
                        dst_type="repair_atom",
                        dst_id=str(r["repair_atom_id"] or ""),
                        edge_type="concept_decode_yields_repair_atom",
                    )


def _import_poms_rows(conn: sqlite3.Connection, run_dir: Path, run_id: str, artifacts: list[sqlite3.Row]) -> None:
    for artifact in artifacts:
        path = Path(str(artifact["abs_path"] or artifact["rel_path"] or ""))
        if path.suffix != ".jsonl":
            continue
        rows = _read_jsonl(path)
        atype = str(artifact["artifact_type"] or "")
        for row in rows:
            if atype == "poms_evidence" or any(k in row for k in ("parent_nonpaid", "dual_certificate", "least_repair")):
                evidence_id = str(row.get("evidence_id") or row.get("id") or stable_hash(row, 16))
                rh = _row_hash(run_id, artifact["artifact_id"], "poms_evidence", evidence_id, row)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO poms_evidence(
                        row_hash, run_id, artifact_id, evidence_id, candidate_id, action_id,
                        parent_nonpaid, dual_certificate, least_repair, payload_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rh,
                        run_id,
                        artifact["artifact_id"],
                        evidence_id,
                        str(row.get("candidate_id") or ""),
                        str(row.get("action_id") or ""),
                        _int_bool(row.get("parent_nonpaid")),
                        _int_bool(row.get("dual_certificate")),
                        _int_bool(row.get("least_repair")),
                        _json(row),
                    ),
                )
            if atype == "poms_promotion_decisions" or "promotion_status" in row:
                decision_id = str(row.get("decision_id") or row.get("id") or "poms_decision_" + stable_hash(row, 16))
                conn.execute(
                    """
                    INSERT OR REPLACE INTO poms_promotion_decisions(
                        decision_id, ts, run_id, candidate_id, action_id, parent_nonpaid,
                        dual_certificate, least_repair, promotion_status, canonical_status, reason, row_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        decision_id,
                        _float(row.get("ts"), _now()),
                        run_id,
                        str(row.get("candidate_id") or ""),
                        str(row.get("action_id") or ""),
                        _int_bool(row.get("parent_nonpaid")),
                        _int_bool(row.get("dual_certificate")),
                        _int_bool(row.get("least_repair")),
                        str(row.get("promotion_status") or row.get("status") or ""),
                        str(row.get("canonical_status") or ""),
                        str(row.get("reason") or ""),
                        _json(row),
                    ),
                )


def summarize_run_db(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_run_schema(conn)
    tables = [
        "runs",
        "artifacts",
        "tasks",
        "action_rows",
        "audit_rows",
        "response_rows",
        "response_values",
        "carrier_values",
        "audit_jobs",
        "timeout_events",
        "action_quarantine",
        "audit_result_cache_index",
        "repair_atoms",
        "repair_faces",
        "crg_problems",
        "relaxed_candidates",
        "hardening_attempts",
        "hard_candidates",
        "crg_audit_rows",
        "concept_points",
        "concept_search_rows",
        "poms_evidence",
        "poms_promotion_decisions",
        "lineage_edges",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        if _table_exists(conn, table):
            counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        else:
            counts[table] = 0
    v_relaxed = _float(conn.execute("SELECT COALESCE(MAX(relaxed_score), 0.0) FROM relaxed_candidates").fetchone()[0] if _table_exists(conn, "relaxed_candidates") else 0.0)
    v_concept = _float(conn.execute("SELECT COALESCE(MAX(score), 0.0) FROM concept_search_rows").fetchone()[0] if _table_exists(conn, "concept_search_rows") else 0.0)
    v_hard = _float(conn.execute("SELECT COALESCE(MAX(audited_score), 0.0) FROM crg_audit_rows").fetchone()[0] if _table_exists(conn, "crg_audit_rows") else 0.0)
    hardening_gap = _float(conn.execute("SELECT COALESCE(MAX(hardening_gap), 0.0) FROM crg_audit_rows").fetchone()[0] if _table_exists(conn, "crg_audit_rows") else 0.0)
    cache_hit = int(conn.execute("SELECT COALESCE(SUM(n_cache_hit), 0) FROM audit_result_cache_index").fetchone()[0] if _table_exists(conn, "audit_result_cache_index") else 0)
    n_timeout = int(conn.execute("SELECT COUNT(*) FROM timeout_events").fetchone()[0] if _table_exists(conn, "timeout_events") else 0)
    dominant = ""
    if _table_exists(conn, "relaxed_candidates"):
        row = conn.execute(
            "SELECT repair_species, MAX(relaxed_score) AS score FROM relaxed_candidates GROUP BY repair_species ORDER BY score DESC LIMIT 1"
        ).fetchone()
        dominant = str(row["repair_species"]) if row else ""
    return {
        "schema_version": SCHEMA_RUN_DB,
        "tables": counts,
        "V_relaxed": v_relaxed,
        "V_concept": v_concept,
        "V_hard": v_hard,
        "V_audit": v_hard,
        "hardening_gap": hardening_gap,
        "n_cache_hit": cache_hit,
        "n_timeout": n_timeout,
        "dominant_species": dominant,
    }


def build_run_db(
    run_dir: str | Path,
    db_path: str | Path | None = None,
    *,
    append: bool = False,
    artifact_store_root: str | Path | None = None,
    import_artifacts: bool = True,
    materialize_lineage: bool = True,
    run_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(run_dir)
    db = Path(db_path) if db_path else root / "runs.db"
    if db.exists() and not append:
        db.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)
    if import_artifacts:
        build_audit_db(root, db, reset=False)
    store = RunStore(db, Path(artifact_store_root) if artifact_store_root else None)
    conn = store.connect()
    try:
        rid = run_id or ("run_" + stable_hash({"run_dir": str(root.resolve())}, 20))
        store.upsert_run(conn, run_id=rid, run_dir=root, status="imported", payload={"config": config or {}, "artifact_store_root": str(artifact_store_root or "")})
        if import_artifacts:
            import_repair_artifacts(conn, root)
        ensure_run_schema(conn)
        artifacts = ArtifactStore(conn, root, rid)
        artifacts.refresh_artifact_metadata()
        rows = artifacts.artifact_rows()
        audit = AuditStore(conn, root, rid)
        audit.import_tasks_and_actions(rows)
        audit.import_queue_ledgers()
        audit.import_cache_summary()
        RepairStore(conn, root, rid).import_supplemental_repair_artifacts(rows)
        _import_poms_rows(conn, root, rid, rows)
        if materialize_lineage:
            LineageStore(conn, rid).materialize_from_tables()
        conn.commit()
        summary = summarize_run_db(conn)
        summary.update({"db_path": str(db), "run_dir": str(root), "run_id": rid})
        (db.parent / "run_db_summary.json").write_text(_json(summary), encoding="utf-8")
        return summary
    finally:
        conn.close()


def query_run_db(db_path: str | Path, sql: str, *, max_rows: int = 1000) -> list[dict[str, Any]]:
    return query_audit_db(db_path, sql, max_rows=max_rows)


def write_query_outputs(rows: list[dict[str, Any]], *, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> None:
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_json({"rows": rows, "n_rows": len(rows)}), encoding="utf-8")
    if out_csv:
        p = Path(out_csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            if not rows:
                f.write("")
                return
            fields = sorted({k for row in rows for k in row.keys()})
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
