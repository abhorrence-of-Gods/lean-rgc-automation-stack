from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3

from .audit_db import build_audit_db, query_audit_db, write_query_outputs
from .repair_space import safe_float
from .schemas import read_jsonl, stable_hash


SCHEMA_REPAIR_DB = "lean-rgc-repair-db-v63.0"


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return [r for r in read_jsonl(path) if isinstance(r, dict)]
    except Exception:
        return []


def _row_hash(row: dict[str, Any]) -> str:
    return stable_hash(row, 32)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _count_by(conn: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    if not _table_exists(conn, table):
        return {}
    try:
        return {
            str(r[column] or ""): int(r["n"] or 0)
            for r in conn.execute(
                f"SELECT {column}, COUNT(*) AS n FROM {table} GROUP BY {column} ORDER BY {column}"
            ).fetchall()
        }
    except Exception:
        return {}


def _sum_int(conn: sqlite3.Connection, table: str, column: str) -> int:
    if not _table_exists(conn, table):
        return 0
    try:
        return int(conn.execute(f"SELECT COALESCE(SUM({column}), 0) FROM {table}").fetchone()[0] or 0)
    except Exception:
        return 0


def summarize_execution_metrics(conn: sqlite3.Connection) -> dict[str, Any]:
    """Compact audit execution metrics shared by repair DB and unified run DB."""
    job_by_status = _count_by(conn, "audit_jobs", "status")
    job_by_lane = _count_by(conn, "audit_jobs", "lane")
    timeout_by_scope = _count_by(conn, "timeout_events", "timeout_scope")
    quarantine_by_status = _count_by(conn, "action_quarantine", "status")
    worker_event_by_type = _count_by(conn, "worker_events", "event_type")
    promotion_by_status = _count_by(conn, "poms_promotion_decisions", "promotion_status")
    readiness_by_status = _count_by(conn, "crg_audit_rows", "promotion_readiness")
    n_jobs = sum(job_by_status.values())
    n_timeout_events = sum(timeout_by_scope.values())
    n_timeout_jobs = int(job_by_status.get("timeout", 0))
    n_tactic_timeout = int(timeout_by_scope.get("tactic_timeout", 0))
    n_timeout = max(n_timeout_events, n_timeout_jobs)
    n_infra_timeout = max(0, n_timeout - n_tactic_timeout)
    n_cache_lookup = _sum_int(conn, "audit_result_cache_index", "n_cache_lookup")
    n_cache_hit = max(_sum_int(conn, "audit_result_cache_index", "n_cache_hit"), int(job_by_status.get("succeeded_from_cache", 0)))
    n_cache_miss = _sum_int(conn, "audit_result_cache_index", "n_cache_miss")
    n_cache_stored = _sum_int(conn, "audit_result_cache_index", "n_stored")
    denom = n_cache_lookup if n_cache_lookup > 0 else (n_cache_hit + n_cache_miss)
    cache_hit_rate = float(n_cache_hit / denom) if denom else 0.0
    n_quarantined = max(int(job_by_status.get("quarantined", 0)), int(quarantine_by_status.get("quarantined", 0)))
    promotion_readiness = ""
    for key in ("promotion_candidate", "paid_witness", "witness_only"):
        if readiness_by_status.get(key, 0) > 0:
            promotion_readiness = key
            break
    source_safe = True
    carrier_safe = True
    if _table_exists(conn, "crg_audit_rows"):
        try:
            source_safe = int(conn.execute("SELECT COUNT(*) FROM crg_audit_rows WHERE COALESCE(source_safe, 1)=0").fetchone()[0] or 0) == 0
            carrier_safe = int(conn.execute("SELECT COUNT(*) FROM crg_audit_rows WHERE COALESCE(carrier_safe, 1)=0").fetchone()[0] or 0) == 0
        except Exception:
            source_safe = True
            carrier_safe = True
    return {
        "n_jobs": n_jobs,
        "job_by_status": job_by_status,
        "job_by_lane": job_by_lane,
        "n_succeeded": int(job_by_status.get("succeeded", 0) + job_by_status.get("succeeded_from_cache", 0)),
        "n_failed": int(job_by_status.get("failed", 0)),
        "n_running": int(job_by_status.get("running", 0)),
        "n_queued": int(job_by_status.get("queued", 0)),
        "n_timeout_jobs": n_timeout_jobs,
        "n_timeout": n_timeout,
        "n_tactic_timeout": n_tactic_timeout,
        "n_infra_timeout": n_infra_timeout,
        "n_quarantine_suppressed_by_import_cost": n_infra_timeout,
        "timeout_by_scope": timeout_by_scope,
        "n_quarantined": n_quarantined,
        "quarantine_by_status": quarantine_by_status,
        "worker_event_by_type": worker_event_by_type,
        "worker_restarts": int(worker_event_by_type.get("restart", 0) + worker_event_by_type.get("killed_timeout", 0)),
        "n_cache_lookup": n_cache_lookup,
        "n_cache_hit": n_cache_hit,
        "n_cache_miss": n_cache_miss,
        "n_cache_stored": n_cache_stored,
        "cache_hit_rate": cache_hit_rate,
        "promotion_by_status": promotion_by_status,
        "promotion_readiness_by_status": readiness_by_status,
        "promotion_readiness": promotion_readiness,
        "poms_promoted": bool(promotion_by_status.get("canonical_candidate", 0) or promotion_by_status.get("canonical_observable", 0)),
        "source_safe": source_safe,
        "carrier_safe": carrier_safe,
    }


def connect_repair_db(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    ensure_repair_schema(conn)
    return conn


def ensure_repair_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
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
        CREATE INDEX IF NOT EXISTS idx_repair_atoms_species ON repair_atoms(species_id, source);

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
        CREATE INDEX IF NOT EXISTS idx_crg_problems_problem ON crg_problems(problem_id);

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
        CREATE INDEX IF NOT EXISTS idx_relaxed_candidates_problem ON relaxed_candidates(problem_id, relaxed_score DESC);

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
        CREATE INDEX IF NOT EXISTS idx_hardening_attempts_candidate ON hardening_attempts(candidate_id);

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
        CREATE INDEX IF NOT EXISTS idx_crg_audit_rows_candidate ON crg_audit_rows(candidate_id);

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
        CREATE INDEX IF NOT EXISTS idx_concept_points_species ON concept_points(concept_species);

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
        CREATE INDEX IF NOT EXISTS idx_concept_search_score ON concept_search_rows(score DESC);
        """
    )
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("repair_db_schema_version", SCHEMA_REPAIR_DB))
    conn.commit()


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "repair_atoms": root / "crg" / "repair_species_registry.jsonl",
        "crg_problems": root / "crg" / "crg_problems.jsonl",
        "relaxed_candidates": root / "crg" / "relaxed_candidates.jsonl",
        "hardening_attempts": root / "crg" / "hardening_attempts.jsonl",
        "crg_audit_rows": root / "crg" / "crg_audit_rows.jsonl",
        "concept_points": root / "concept_geometry" / "concept_points.jsonl",
        "concept_search_rows": root / "concept_geometry" / "concept_search_rows.jsonl",
    }


def _cost(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    cv = row.get("cost_vector") if isinstance(row.get("cost_vector"), dict) else {}
    scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
    return safe_float(row.get(key), safe_float(cv.get(key), safe_float(scores.get(key), default)))


def import_repair_artifacts(conn: sqlite3.Connection, run_dir: str | Path) -> dict[str, Any]:
    ensure_repair_schema(conn)
    root = Path(run_dir)
    counts: dict[str, int] = {}
    for table, path in _artifact_paths(root).items():
        rows = _read_rows(path)
        counts[table] = 0
        for row in rows:
            rh = _row_hash({"table": table, "path": str(path), "row": row})
            if table == "repair_atoms":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO repair_atoms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("repair_atom_id") or row.get("atom_id") or rh),
                        str(row.get("species_id") or row.get("repair_species") or ""),
                        str(row.get("source") or ""),
                        str(row.get("source_id") or ""),
                        _cost(row, "cost", 1.0),
                        _cost(row, "audit_risk", 0.0),
                        _cost(row, "source_risk", 0.0),
                        _cost(row, "ghost_risk", 0.0),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "crg_problems":
                conn.execute(
                    "INSERT OR IGNORE INTO crg_problems VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("problem_id") or rh),
                        str(row.get("parent_face_id") or ""),
                        str(row.get("obstruction_id") or ""),
                        str(row.get("repair_space_scope") or ""),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "relaxed_candidates":
                scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
                conn.execute(
                    """
                    INSERT OR IGNORE INTO relaxed_candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("candidate_id") or rh),
                        str(row.get("problem_id") or ""),
                        str(row.get("repair_species") or row.get("species_id") or ""),
                        safe_float(scores.get("lambda_response"), safe_float(row.get("relaxed_score"), 0.0)),
                        safe_float(scores.get("cost"), _cost(row, "cost", 0.0)),
                        safe_float(scores.get("audit_risk"), _cost(row, "audit_risk", 0.0)),
                        safe_float(scores.get("source_risk"), _cost(row, "source_risk", 0.0)),
                        safe_float(scores.get("ghost_risk"), _cost(row, "ghost_risk", 0.0)),
                        safe_float(scores.get("net_score"), safe_float(row.get("net_score"), 0.0)),
                        int(scores.get("n_feasible_atoms") or row.get("n_feasible_atoms") or 0),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "hardening_attempts":
                hards = row.get("hard_candidates") if isinstance(row.get("hard_candidates"), list) else []
                conn.execute(
                    "INSERT OR IGNORE INTO hardening_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("hardening_id") or rh),
                        str(row.get("candidate_id") or ""),
                        str(row.get("hardening_method") or ""),
                        str(row.get("hardening_status") or row.get("status") or ""),
                        safe_float(row.get("hardening_gap"), 0.0),
                        len(hards),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "crg_audit_rows":
                conn.execute(
                    "INSERT OR IGNORE INTO crg_audit_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("candidate_id") or rh),
                        str(row.get("problem_id") or ""),
                        safe_float(row.get("relaxed_score"), 0.0),
                        safe_float(row.get("audited_score"), 0.0),
                        safe_float(row.get("hardening_gap"), 0.0),
                        safe_float(row.get("heldout_score"), 0.0),
                        safe_float(row.get("ghost_risk"), 0.0),
                        1 if bool(row.get("source_safe")) else 0,
                        1 if bool(row.get("carrier_safe")) else 0,
                        str(row.get("promotion_readiness") or ""),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "concept_points":
                cost = row.get("cost_embedding") if isinstance(row.get("cost_embedding"), dict) else {}
                conn.execute(
                    "INSERT OR IGNORE INTO concept_points VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("concept_id") or rh),
                        str(row.get("concept_species") or ""),
                        str(row.get("origin") or ""),
                        safe_float(cost.get("audit_risk"), safe_float(row.get("audit_risk"), 0.0)),
                        safe_float(cost.get("hardening_risk"), safe_float(row.get("hardening_risk"), 0.0)),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            elif table == "concept_search_rows":
                decoder = row.get("decoder") if isinstance(row.get("decoder"), dict) else {}
                conn.execute(
                    "INSERT OR IGNORE INTO concept_search_rows VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        rh,
                        str(root),
                        str(path),
                        str(row.get("concept_id") or row.get("target_concept_id") or rh),
                        safe_float(row.get("repair_score"), safe_float(row.get("score"), safe_float((row.get("scores") or {}).get("score") if isinstance(row.get("scores"), dict) else 0.0, 0.0))),
                        str(row.get("mode") or row.get("search_mode") or row.get("search_method") or ""),
                        str(row.get("target_species") or decoder.get("target_species") or ""),
                        str(row.get("canonical_status") or ""),
                        _json(row),
                    ),
                )
            counts[table] += 1
    conn.commit()
    return counts


def summarize_repair_db(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_repair_schema(conn)
    tables = [
        "repair_atoms",
        "crg_problems",
        "relaxed_candidates",
        "hardening_attempts",
        "crg_audit_rows",
        "concept_points",
        "concept_search_rows",
    ]
    counts = {}
    for t in tables:
        counts[t] = int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    v_relaxed = safe_float(conn.execute("SELECT COALESCE(MAX(relaxed_score), 0.0) FROM relaxed_candidates").fetchone()[0], 0.0)
    v_concept = safe_float(conn.execute("SELECT COALESCE(MAX(score), 0.0) FROM concept_search_rows").fetchone()[0], 0.0)
    v_hard = safe_float(conn.execute("SELECT COALESCE(MAX(audited_score), 0.0) FROM crg_audit_rows").fetchone()[0], 0.0)
    v_audit = v_hard
    hardening_gap = safe_float(conn.execute("SELECT COALESCE(MAX(hardening_gap), 0.0) FROM crg_audit_rows").fetchone()[0], 0.0)
    execution = summarize_execution_metrics(conn)
    species_row = conn.execute(
        """
        SELECT repair_species, MAX(relaxed_score) AS score
        FROM relaxed_candidates
        GROUP BY repair_species
        ORDER BY score DESC
        LIMIT 1
        """
    ).fetchone()
    dominant_species = str(species_row["repair_species"]) if species_row else ""
    summary = {
        "schema_version": SCHEMA_REPAIR_DB,
        "tables": counts,
        "V_relaxed": v_relaxed,
        "V_concept": v_concept,
        "V_hard": v_hard,
        "V_audit": v_audit,
        "hardening_gap": hardening_gap,
        "dominant_species": dominant_species,
    }
    summary.update(execution)
    return summary


def classify_failure_from_summary(summary: dict[str, Any]) -> str:
    v_active = safe_float(summary.get("V_active"), 0.0)
    v_known = safe_float(summary.get("V_known"), safe_float(summary.get("V_relaxed"), 0.0))
    v_concept = safe_float(summary.get("V_concept"), 0.0)
    v_relaxed = safe_float(summary.get("V_relaxed"), 0.0)
    v_hard = safe_float(summary.get("V_hard"), 0.0)
    v_audit = safe_float(summary.get("V_audit"), v_hard)
    v_robust = safe_float(summary.get("V_robust"), v_audit)
    dominant = str(summary.get("dominant_species") or "")
    source_safe = bool(summary.get("source_safe", True))
    carrier_safe = bool(summary.get("carrier_safe", True))
    readiness = str(summary.get("promotion_readiness") or "")
    poms_promoted = bool(summary.get("poms_promoted", False))
    if v_relaxed > 0 and v_hard <= 0:
        return "hardening_or_grammar_defect"
    if v_active <= 0 and v_known <= 0 and v_concept <= 0:
        return "action_or_universe_insufficient"
    if v_active <= 0 and v_known > 0:
        if dominant in {"premise_distribution", "tower_retrieval", "context_portfolio"}:
            return "premise_retrieval_insufficient"
        return "activation_scheduler_insufficient"
    if v_known <= 0 and v_concept > 0:
        return "concept_space_needed"
    if v_hard > 0 and v_audit <= 0:
        if not source_safe:
            return "source_safety_failure"
        if not carrier_safe:
            return "carrier_safety_failure"
        return "lean_replay_or_audit_failure"
    if v_audit > 0 and v_robust <= 0:
        return "finite_chart_artifact_or_ghost"
    if readiness == "promotion_candidate" and not poms_promoted:
        return "poms_parent_or_least_repair_gate"
    return "open_mixed"


def build_repair_db(run_dir: str | Path, db_path: str | Path | None = None, *, append: bool = False, include_audit_db: bool = True) -> dict[str, Any]:
    root = Path(run_dir)
    db = Path(db_path) if db_path else root / "audit.db"
    if include_audit_db:
        build_audit_db(root, db, reset=not append)
    conn = connect_repair_db(db)
    try:
        imported = import_repair_artifacts(conn, root)
        summary = summarize_repair_db(conn)
        summary.update({"db_path": str(db), "run_dir": str(root), "imported": imported})
        (db.parent / "repair_db_summary.json").write_text(_json(summary), encoding="utf-8")
        return summary
    finally:
        conn.close()


def repair_db_query(db_path: str | Path, sql: str | None = None, *, max_rows: int = 1000) -> dict[str, Any]:
    if sql:
        return {"db_path": str(db_path), "rows": query_audit_db(db_path, sql, max_rows=max_rows)}
    conn = connect_repair_db(db_path)
    try:
        summary = summarize_repair_db(conn)
        summary["diagnosis"] = classify_failure_from_summary(summary)
        return summary
    finally:
        conn.close()


def failure_attribution_report(
    *,
    db_path: str | Path,
    out_json: str | Path | None = None,
    sql: str | None = None,
    max_rows: int = 1000,
) -> dict[str, Any]:
    rep = repair_db_query(db_path, sql=sql, max_rows=max_rows)
    if not sql:
        rep = {
            "schema_version": SCHEMA_REPAIR_DB,
            "task_id": "aggregate",
            "diagnosis": rep.get("diagnosis"),
            "evidence": {
                "V_relaxed": rep.get("V_relaxed", 0.0),
                "V_concept": rep.get("V_concept", 0.0),
                "V_hard": rep.get("V_hard", 0.0),
                "V_audit": rep.get("V_audit", 0.0),
                "hardening_gap": rep.get("hardening_gap", 0.0),
                "n_jobs": rep.get("n_jobs", 0),
                "n_succeeded": rep.get("n_succeeded", 0),
                "n_failed": rep.get("n_failed", 0),
                "n_timeout": rep.get("n_timeout", 0),
                "n_tactic_timeout": rep.get("n_tactic_timeout", 0),
                "n_infra_timeout": rep.get("n_infra_timeout", 0),
                "n_quarantined": rep.get("n_quarantined", 0),
                "worker_restarts": rep.get("worker_restarts", 0),
                "n_cache_lookup": rep.get("n_cache_lookup", 0),
                "n_cache_hit": rep.get("n_cache_hit", 0),
                "n_cache_miss": rep.get("n_cache_miss", 0),
                "n_cache_stored": rep.get("n_cache_stored", 0),
                "cache_hit_rate": rep.get("cache_hit_rate", 0.0),
                "dominant_species": rep.get("dominant_species", ""),
                "promotion_readiness": rep.get("promotion_readiness", ""),
                "source_safe": rep.get("source_safe", True),
                "carrier_safe": rep.get("carrier_safe", True),
                "job_by_status": rep.get("job_by_status", {}),
                "timeout_by_scope": rep.get("timeout_by_scope", {}),
                "quarantine_by_status": rep.get("quarantine_by_status", {}),
                "promotion_by_status": rep.get("promotion_by_status", {}),
            },
            "recommended_next": _recommend_next(str(rep.get("diagnosis") or "")),
            "db_summary": rep,
        }
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return rep


def _recommend_next(diagnosis: str) -> str:
    return {
        "action_or_universe_insufficient": "expand_action_grammar_or_candidate_universe",
        "activation_scheduler_insufficient": "improve_scheduler_or_retrieval_activation",
        "premise_retrieval_insufficient": "increase_premise_index_quality_and_top_k",
        "concept_space_needed": "promote_concept_search_to_hardening_experiments",
        "hardening_or_grammar_defect": "improve_hardening_decoder_or_tactic_grammar",
        "lean_replay_or_audit_failure": "inspect_lean_worker_imports_timeouts_and_replay",
        "source_safety_failure": "tighten_source_safety_and_hidden_word_gate",
        "carrier_safety_failure": "repair_carrier_patch_or_quotient_atlas",
        "finite_chart_artifact_or_ghost": "increase_response_completion_and_holdout_probes",
        "poms_parent_or_least_repair_gate": "establish_parent_nonpaid_dual_certificate_least_repair",
    }.get(diagnosis, "inspect_mixed_evidence")


def write_repair_query_outputs(rows_or_report: Any, *, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> None:
    if isinstance(rows_or_report, dict) and isinstance(rows_or_report.get("rows"), list):
        write_query_outputs(rows_or_report["rows"], out_json=out_json, out_csv=out_csv)
        return
    if out_json:
        p = Path(out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rows_or_report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


__all__ = [
    "SCHEMA_REPAIR_DB",
    "build_repair_db",
    "classify_failure_from_summary",
    "connect_repair_db",
    "ensure_repair_schema",
    "failure_attribution_report",
    "repair_db_query",
    "summarize_execution_metrics",
    "summarize_repair_db",
    "write_repair_query_outputs",
]
