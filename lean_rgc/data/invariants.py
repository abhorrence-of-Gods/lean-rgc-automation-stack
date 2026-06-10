from __future__ import annotations

from typing import Any
import sqlite3


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def check_run_db_invariants(conn: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    if _table_exists(conn, "artifacts"):
        checks["artifacts_missing_identity"] = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM artifacts
                WHERE COALESCE(run_id,'')='' OR COALESCE(schema_version,'')='' OR COALESCE(sha256,'')=''
                """
            ).fetchone()[0]
        )
    canonical_id_checks = {
        "tasks_missing_id": ("tasks", "task_id"),
        "actions_missing_id": ("actions", "action_id"),
        "responses_missing_id": ("responses", "response_id"),
        "repair_faces_missing_id": ("repair_faces", "face_id"),
        "crg_problems_missing_id": ("crg_problems", "problem_id"),
        "relaxed_candidates_missing_id": ("relaxed_candidates", "candidate_id"),
        "hardening_attempts_missing_id": ("hardening_attempts", "hardening_id"),
        "hard_candidates_missing_id": ("hard_candidates", "action_id"),
        "poms_evidence_missing_id": ("poms_evidence", "evidence_id"),
        "poms_promotion_decisions_missing_id": ("poms_promotion_decisions", "decision_id"),
        "concept_points_missing_id": ("concept_points", "concept_id"),
        "concept_search_rows_missing_id": ("concept_search_rows", "concept_id"),
    }
    for key, (table, column) in canonical_id_checks.items():
        if _table_exists(conn, table) and column in _columns(conn, table):
            checks[key] = int(
                conn.execute(f"SELECT COUNT(*) FROM {table} WHERE COALESCE({column},'')=''").fetchone()[0]
            )
    if _table_exists(conn, "lineage_edges"):
        checks["lineage_edges_missing_typed_endpoint"] = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM lineage_edges
                WHERE COALESCE(edge_id,'')='' OR COALESCE(run_id,'')=''
                   OR COALESCE(src_type,'')='' OR COALESCE(src_id,'')=''
                   OR COALESCE(dst_type,'')='' OR COALESCE(dst_id,'')=''
                   OR COALESCE(edge_type,'')=''
                """
            ).fetchone()[0]
        )
    checks["ok"] = all(int(v) == 0 for k, v in checks.items() if k != "ok")
    return checks


__all__ = ["check_run_db_invariants"]
