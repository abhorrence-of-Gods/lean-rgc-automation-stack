from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import time

from ..schemas import read_jsonl


SCHEMA_PROMPT_EPISODE_STORE = "lean-rgc-prompt-episode-store-v90.0"


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def connect_prompt_db(db_path: str | Path) -> sqlite3.Connection:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db, timeout=60.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_prompt_store_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS prompt_boundaries (
            boundary_id TEXT PRIMARY KEY,
            task_id TEXT,
            boundary_kind TEXT,
            attempt_index INTEGER,
            prompt_hash TEXT,
            output_hash TEXT,
            model_id TEXT,
            model_version TEXT,
            cached INTEGER,
            n_proposals INTEGER,
            boundary_json TEXT,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS prompt_episodes (
            episode_id TEXT PRIMARY KEY,
            run_id TEXT,
            arm TEXT,
            task_id TEXT,
            solved INTEGER,
            attempts_used INTEGER,
            llm_calls INTEGER,
            audit_pass_count INTEGER,
            first_solve_attempt INTEGER,
            budget_calls INTEGER,
            episode_json TEXT,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS prompt_mutations (
            mutation_id TEXT PRIMARY KEY,
            parent_boundary_id TEXT,
            child_boundary_id TEXT,
            mutation_kind TEXT,
            signal_basis_json TEXT,
            expected_effect_json TEXT,
            observed_effect_json TEXT,
            created_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_prompt_boundaries_task ON prompt_boundaries(task_id);
        CREATE INDEX IF NOT EXISTS idx_prompt_episodes_arm ON prompt_episodes(arm);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
        ("prompt_episode_store_schema_version", SCHEMA_PROMPT_EPISODE_STORE),
    )
    conn.commit()


def import_prompt_artifacts(
    *,
    db_path: str | Path,
    boundaries_path: str | Path | None = None,
    episodes_path: str | Path | None = None,
    mutations_path: str | Path | None = None,
) -> dict[str, Any]:
    conn = connect_prompt_db(db_path)
    try:
        ensure_prompt_store_schema(conn)
        now = float(time.time())
        n_boundaries = 0
        n_episodes = 0
        n_mutations = 0
        if boundaries_path and Path(boundaries_path).exists():
            for row in read_jsonl(boundaries_path):
                if not isinstance(row, dict) or not row.get("boundary_id"):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prompt_boundaries(
                        boundary_id, task_id, boundary_kind, attempt_index, prompt_hash,
                        output_hash, model_id, model_version, cached, n_proposals,
                        boundary_json, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(row.get("boundary_id")),
                        str(row.get("task_id") or ""),
                        str(row.get("boundary_kind") or ""),
                        int(row.get("attempt_index") or 0),
                        str(row.get("prompt_hash") or ""),
                        str(row.get("output_hash") or ""),
                        str(row.get("model_id") or ""),
                        str(row.get("model_version") or "") or None,
                        1 if row.get("cached") else 0,
                        int(row.get("n_proposals") or 0),
                        _json(row),
                        now,
                    ),
                )
                n_boundaries += 1
        if episodes_path and Path(episodes_path).exists():
            for row in read_jsonl(episodes_path):
                if not isinstance(row, dict) or not row.get("episode_id"):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prompt_episodes(
                        episode_id, run_id, arm, task_id, solved, attempts_used,
                        llm_calls, audit_pass_count, first_solve_attempt, budget_calls,
                        episode_json, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(row.get("episode_id")),
                        str(row.get("run_id") or ""),
                        str(row.get("arm") or ""),
                        str(row.get("task_id") or ""),
                        1 if row.get("solved") else 0,
                        int(row.get("attempts_used") or 0),
                        int(row.get("llm_calls") or 0),
                        int(row.get("audit_pass_count") or 0),
                        int(row["first_solve_attempt"]) if row.get("first_solve_attempt") is not None else None,
                        int(row.get("budget_calls") or 0),
                        _json(row),
                        now,
                    ),
                )
                n_episodes += 1
        if mutations_path and Path(mutations_path).exists():
            for row in read_jsonl(mutations_path):
                if not isinstance(row, dict) or not row.get("mutation_id"):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prompt_mutations(
                        mutation_id, parent_boundary_id, child_boundary_id, mutation_kind,
                        signal_basis_json, expected_effect_json, observed_effect_json, created_at
                    ) VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(row.get("mutation_id")),
                        str(row.get("parent_boundary_id") or ""),
                        str(row.get("child_boundary_id") or ""),
                        str(row.get("mutation_kind") or ""),
                        _json(row.get("signal_basis") or {}),
                        _json(row.get("expected_effect") or {}),
                        _json(row.get("observed_effect") or {}),
                        now,
                    ),
                )
                n_mutations += 1
        conn.commit()
        return {
            "schema_version": SCHEMA_PROMPT_EPISODE_STORE,
            "db_path": str(db_path),
            "n_boundaries_imported": n_boundaries,
            "n_episodes_imported": n_episodes,
            "n_mutations_imported": n_mutations,
        }
    finally:
        conn.close()


def summarize_prompt_db(db_path: str | Path) -> dict[str, Any]:
    conn = connect_prompt_db(db_path)
    try:
        ensure_prompt_store_schema(conn)
        counts = {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("prompt_boundaries", "prompt_episodes", "prompt_mutations")
        }
        by_arm = {
            str(arm): {"n_episodes": int(n), "n_solved": int(solved), "solve_rate": (int(solved) / int(n)) if n else 0.0}
            for arm, n, solved in conn.execute(
                "SELECT arm, COUNT(*), COALESCE(SUM(solved),0) FROM prompt_episodes GROUP BY arm ORDER BY arm"
            )
        }
        cached = conn.execute(
            "SELECT COALESCE(SUM(cached),0), COUNT(*) FROM prompt_boundaries"
        ).fetchone()
        n_cached, n_total = int(cached[0] or 0), int(cached[1] or 0)
        return {
            "schema_version": SCHEMA_PROMPT_EPISODE_STORE,
            "db_path": str(db_path),
            "counts": counts,
            "episodes_by_arm": by_arm,
            "boundary_cache_rate": (n_cached / n_total) if n_total else 0.0,
        }
    finally:
        conn.close()


__all__ = [
    "SCHEMA_PROMPT_EPISODE_STORE",
    "connect_prompt_db",
    "ensure_prompt_store_schema",
    "import_prompt_artifacts",
    "summarize_prompt_db",
]
