from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import sqlite3
import time

from ..audit_db import build_audit_db, query_audit_db
from ..repair_db import import_repair_artifacts as import_legacy_repair_artifacts
from ..repair_db import summarize_execution_metrics, summarize_repair_db
from ..schemas import stable_hash
from .importers import (
    AuditStore,
    LineageStore,
    RepairStore,
    import_audit_artifacts as import_audit_store_artifacts,
    import_poms_artifacts as import_poms_store_artifacts,
    import_repair_artifacts as import_repair_store_artifacts,
    materialize_canonical_run_tables,
    materialize_lineage as materialize_lineage_store,
)
from .invariants import check_run_db_invariants
from .migrations import record_migration


SCHEMA_RUN_DB = "lean-rgc-run-db-v1.1"
CANONICAL_RECORD_SCHEMA = "lean-rgc.canonical.v1"


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


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


def _artifact_uri(path: Path) -> str:
    try:
        return path.resolve().as_uri()
    except Exception:
        return str(path)


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
        CREATE TABLE IF NOT EXISTS responses (
            response_id TEXT PRIMARY KEY,
            schema_version TEXT,
            run_id TEXT,
            artifact_id INTEGER,
            row_index INTEGER,
            task_id TEXT,
            action_id TEXT,
            status TEXT,
            elapsed_ms REAL,
            state_before_id TEXT,
            state_after_id TEXT,
            response_json TEXT,
            carrier_delta_json TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_responses_run_action ON responses(run_id, action_id);
        CREATE INDEX IF NOT EXISTS idx_run_responses_task ON responses(run_id, task_id);
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            schema_version TEXT,
            run_id TEXT,
            artifact_id INTEGER,
            row_index INTEGER,
            task_id TEXT,
            action_id TEXT,
            status TEXT,
            elapsed_ms REAL,
            heartbeats REAL,
            response_id TEXT,
            payload_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_run_audit_events_run_action ON audit_events(run_id, action_id);
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
        CREATE TABLE IF NOT EXISTS worker_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            run_id TEXT,
            worker_id TEXT,
            event_type TEXT,
            job_id TEXT,
            backend TEXT,
            lane TEXT,
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
    record_migration(conn, version=SCHEMA_RUN_DB, name="run_db_v1_1_canonical_tables")
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
    if _table_exists(conn, "worker_events"):
        _ensure_column(conn, "worker_events", "run_id", "TEXT")
        _ensure_column(conn, "worker_events", "event_type", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_worker_events_type "
            "ON worker_events(run_id, event_type)"
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
    if _table_exists(conn, "responses"):
        _ensure_column(conn, "responses", "schema_version", "TEXT")
        _ensure_column(conn, "responses", "payload_json", "TEXT")
    if _table_exists(conn, "audit_events"):
        _ensure_column(conn, "audit_events", "schema_version", "TEXT")
        _ensure_column(conn, "audit_events", "payload_json", "TEXT")
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
                (self.run_id, artifact_type, schema, _artifact_uri(path), _now(), _json(payload), row["artifact_id"]),
            )

    def artifact_rows(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT artifact_id, abs_path, rel_path, artifact_type, kind FROM artifacts ORDER BY artifact_id"))


def summarize_run_db(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_run_schema(conn)
    tables = [
        "runs",
        "artifacts",
        "schema_migrations",
        "tasks",
        "action_rows",
        "responses",
        "audit_events",
        "audit_rows",
        "response_rows",
        "response_values",
        "carrier_values",
        "audit_jobs",
        "timeout_events",
        "worker_events",
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
    dominant = ""
    if _table_exists(conn, "relaxed_candidates"):
        row = conn.execute(
            "SELECT repair_species, MAX(relaxed_score) AS score FROM relaxed_candidates GROUP BY repair_species ORDER BY score DESC LIMIT 1"
        ).fetchone()
        dominant = str(row["repair_species"]) if row else ""
    execution = summarize_execution_metrics(conn)
    summary = {
        "schema_version": SCHEMA_RUN_DB,
        "tables": counts,
        "V_relaxed": v_relaxed,
        "V_concept": v_concept,
        "V_hard": v_hard,
        "V_audit": v_hard,
        "hardening_gap": hardening_gap,
        "dominant_species": dominant,
    }
    summary.update(execution)
    summary["invariants"] = check_run_db_invariants(conn)
    return summary


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
            import_legacy_repair_artifacts(conn, root)
        ensure_run_schema(conn)
        artifacts = ArtifactStore(conn, root, rid)
        artifacts.refresh_artifact_metadata()
        rows = artifacts.artifact_rows()
        audit = AuditStore(conn, root, rid)
        import_audit_store_artifacts(audit, rows)
        import_repair_store_artifacts(RepairStore(conn, root, rid), rows)
        import_poms_store_artifacts(conn, root, rid, rows)
        materialize_canonical_run_tables(conn, rid)
        if materialize_lineage:
            materialize_lineage_store(LineageStore(conn, rid))
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
