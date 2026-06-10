import json
import sqlite3
from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.data.store import RunStore, build_run_db, summarize_run_db
from lean_rgc.repair_db import failure_attribution_report
from lean_rgc.schemas import write_jsonl


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def test_run_db_schema_initializes_all_required_tables(tmp_path: Path):
    db = tmp_path / "runs.db"
    store = RunStore(db)
    conn = store.connect()
    try:
        # Idempotency.
        summarize_run_db(conn)
        summarize_run_db(conn)
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()

    required = {
        "runs",
        "artifacts",
        "tasks",
        "actions",
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
    }
    assert required <= tables


def test_run_db_imports_audit_crg_poms_and_lineage(tmp_path: Path):
    run = tmp_path / "run"
    write_jsonl(
        run / "audit" / "responses.jsonl",
        [
            {
                "task_id": "t0",
                "state_id": "s0",
                "action_id": "simp",
                "audit_status": "success",
                "response": {"goal.eq": 1.0},
                "carrier_delta": {"missing_simp": 0.25},
                "audit_flags": {"cache_hit": True},
            }
        ],
    )
    write_jsonl(
        run / "audit" / "micro_audit.jsonl",
        [
            {
                "task_id": "t0",
                "state_id": "s0",
                "action_id": "simp",
                "status": "success",
                "elapsed_ms": 3.0,
                "response": {"goal.eq": 1.0},
            }
        ],
    )
    _write_json(
        run / "audit" / "summary.json",
        {
            "audit_cache": {
                "cache_db": str(tmp_path / "audit_cache.sqlite"),
                "apply": {"n_cache_lookup": 2, "n_cache_hit": 1, "n_cache_miss": 1},
                "store": {"n_stored": 1},
            },
            "n_cache_hit": 1,
        },
    )
    write_jsonl(
        run / "crg" / "repair_species_registry.jsonl",
        [{"repair_atom_id": "atom_1", "species_id": "action_distribution", "source": "actions"}],
    )
    write_jsonl(
        run / "crg" / "crg_problems.jsonl",
        [{"problem_id": "crg_1", "parent_face_id": "face_1", "obstruction_id": "obs_1"}],
    )
    write_jsonl(
        run / "crg" / "relaxed_candidates.jsonl",
        [{"candidate_id": "cand_1", "problem_id": "crg_1", "repair_species": "action_distribution", "scores": {"lambda_response": 0.7}}],
    )
    write_jsonl(
        run / "crg" / "hardening_attempts.jsonl",
        [{"hardening_id": "hard_1", "candidate_id": "cand_1", "hardening_gap": 0.4, "hard_candidates": [{"action_id": "h1"}]}],
    )
    write_jsonl(
        run / "crg" / "hard_candidates.jsonl",
        [{"action_id": "h1", "tactic": "simp", "metadata": {"candidate_id": "cand_1", "hardening_id": "hard_1"}}],
    )
    write_jsonl(
        run / "crg" / "crg_audit_rows.jsonl",
        [{"candidate_id": "cand_1", "problem_id": "crg_1", "relaxed_score": 0.7, "audited_score": 0.0, "hardening_gap": 0.7}],
    )
    write_jsonl(
        run / "poms_evidence.jsonl",
        [{"evidence_id": "ev1", "action_id": "h1", "parent_nonpaid": True, "dual_certificate": True}],
    )
    write_jsonl(
        run / "poms_promotion_decisions.jsonl",
        [{"decision_id": "pd1", "action_id": "h1", "promotion_status": "forced_candidate", "canonical_status": "not_declared"}],
    )

    summary = build_run_db(run, run / "runs.db")
    report = failure_attribution_report(db_path=run / "runs.db")

    assert summary["tables"]["artifacts"] >= 8
    # Existing audit_db compatibility imports both responses.jsonl and
    # micro_audit.jsonl into response_rows when response values are present.
    assert summary["tables"]["response_rows"] == 2
    assert summary["tables"]["relaxed_candidates"] == 1
    assert summary["tables"]["hard_candidates"] == 1
    assert summary["tables"]["poms_evidence"] >= 1
    assert summary["tables"]["poms_promotion_decisions"] >= 1
    assert summary["tables"]["lineage_edges"] > 0
    assert summary["V_relaxed"] == 0.7
    assert summary["n_cache_hit"] == 1
    assert report["evidence"]["n_cache_hit"] == 1

    con = sqlite3.connect(run / "runs.db")
    try:
        legacy = con.execute("SELECT schema_version FROM artifacts WHERE schema_version='legacy.unknown' LIMIT 1").fetchone()
        assert legacy is not None
    finally:
        con.close()


def test_cli_and_pipeline_run_db_smoke(tmp_path: Path):
    run = tmp_path / "run"
    write_jsonl(run / "audit" / "responses.jsonl", [{"state_id": "s", "action_id": "a", "audit_status": "fail", "response": {"x": -1.0}}])
    assert main(["run-db-build", "--run-dir", str(run), "--db", str(run / "runs.db")]) == 0
    assert main(["run-db-query", "--db", str(run / "runs.db"), "--sql", "SELECT COUNT(*) AS n FROM response_rows"]) == 0

    out = tmp_path / "pipe"
    assert main(
        [
            "pipeline",
            "--tasks",
            "examples/minimal_theorems.jsonl",
            "--actions",
            "examples/core_tactics.jsonl",
            "--out",
            str(out),
            "--dry-run",
            "--max-actions",
            "2",
            "--run-db",
        ]
    ) == 0
    assert (out / "runs.db").exists()
    con = sqlite3.connect(out / "runs.db")
    try:
        assert con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM lineage_edges").fetchone()[0] > 0
    finally:
        con.close()
