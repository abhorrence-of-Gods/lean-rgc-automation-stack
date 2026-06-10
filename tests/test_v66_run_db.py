import json
import sqlite3
import time
from pathlib import Path

from lean_rgc.action_quarantine import ensure_quarantine_schema
from lean_rgc.audit_job_queue import connect_queue, ensure_audit_queue_schema
from lean_rgc.cli import main
from lean_rgc.data.store import RunStore, build_run_db, summarize_run_db
from lean_rgc.repair_db import failure_attribution_report
from lean_rgc.schemas import write_jsonl
from lean_rgc.timeout_ledger import ensure_timeout_schema, record_timeout_event, record_worker_event


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_queue_fixture(db_path: Path) -> None:
    conn = connect_queue(db_path)
    try:
        ensure_audit_queue_schema(conn)
        ensure_timeout_schema(conn)
        ensure_quarantine_schema(conn)
        now = time.time()
        for idx, status in enumerate(["succeeded", "succeeded_from_cache", "failed", "timeout", "quarantined"]):
            conn.execute(
                """
                INSERT INTO audit_jobs(
                    job_id, run_id, task_id, state_id, action_id, tactic_hash, backend, lane,
                    import_mode, project_fingerprint, status, priority, attempt_count, max_attempts,
                    leased_until, worker_id, created_at, updated_at, payload_json, result_json, last_error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"job_{idx}",
                    "source_run",
                    f"task_{idx}",
                    f"state_{idx}",
                    f"action_{idx}",
                    f"hash_{idx}",
                    "source_check",
                    "source_check",
                    "preserve",
                    "project",
                    status,
                    0.0,
                    1,
                    1,
                    None,
                    "worker_0",
                    now,
                    now,
                    "{}",
                    "{}",
                    "",
                ),
            )
        record_timeout_event(
            conn,
            job_id="job_3",
            task_id="task_3",
            action_id="action_3",
            tactic_hash="hash_3",
            backend="source_check",
            lane="source_check",
            timeout_s=30.0,
            elapsed_s=30.0,
            stdout_tail="",
            stderr_tail="timeout",
            worker_id="worker_0",
            timeout_scope="tactic_timeout",
        )
        record_timeout_event(
            conn,
            job_id="job_import",
            task_id="task_import",
            action_id="action_import",
            tactic_hash="hash_import",
            backend="source_check",
            lane="source_check",
            timeout_s=30.0,
            elapsed_s=30.0,
            stdout_tail="",
            stderr_tail="import timeout",
            worker_id="worker_0",
            timeout_scope="import_timeout",
        )
        record_worker_event(conn, worker_id="worker_0", event_type="killed_timeout", job_id="job_3", backend="source_check", lane="source_check")
        conn.execute(
            """
            INSERT INTO action_quarantine(
                key_type, key_value, status, reason, n_attempts, n_timeouts,
                timeout_rate, first_seen, updated_at, detail_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            ("action_id", "action_3", "quarantined", "test quarantine", 3, 3, 1.0, now, now, "{}"),
        )
        conn.commit()
    finally:
        conn.close()


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
    _write_queue_fixture(run / "audit" / "audit_queue.sqlite")
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
        run / "concept_geometry" / "concept_points.jsonl",
        [
            {
                "concept_id": "concept_eq",
                "concept_species": "kernel_like",
                "origin": "feature",
                "cost_embedding": {"audit_risk": 0.1, "hardening_risk": 0.2},
                "canonical_status": "concept_chart_not_canonical",
            }
        ],
    )
    write_jsonl(
        run / "concept_geometry" / "concept_search_rows.jsonl",
        [
            {
                "search_row_id": "csearch_eq",
                "concept_id": "concept_eq",
                "repair_score": 0.9,
                "search_method": "response-nearest-neighbor",
                "decoder": {"target_species": "concept_latent"},
                "canonical_status": "concept_search_witness_not_canonical",
            }
        ],
    )
    write_jsonl(
        run / "concept_geometry" / "concept_decoded_repair_atoms.jsonl",
        [
            {
                "repair_atom_id": "rel_atom_concept_eq",
                "species_id": "concept_latent",
                "repair_species": "concept_latent",
                "source": "concept_search",
                "source_id": "concept_eq",
                "cost_vector": {"cost": 1.0, "audit_risk": 0.1},
                "provenance": {
                    "source_row": {
                        "metadata": {
                            "concept_id": "concept_eq",
                            "concept_search_row_id": "csearch_eq",
                        }
                    }
                },
                "canonical_status": "repair_witness_not_canonical",
            }
        ],
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
    assert summary["tables"]["concept_points"] == 1
    assert summary["tables"]["concept_search_rows"] == 1
    assert summary["tables"]["repair_atoms"] >= 2
    assert summary["tables"]["relaxed_candidates"] == 1
    assert summary["tables"]["hard_candidates"] == 1
    assert summary["tables"]["poms_evidence"] >= 1
    assert summary["tables"]["poms_promotion_decisions"] >= 1
    assert summary["tables"]["lineage_edges"] > 0
    assert summary["V_relaxed"] == 0.7
    assert summary["V_concept"] == 0.9
    assert summary["n_jobs"] == 5
    assert summary["n_succeeded"] == 2
    assert summary["n_failed"] == 1
    assert summary["n_timeout"] == 2
    assert summary["n_timeout_jobs"] == 1
    assert summary["n_tactic_timeout"] == 1
    assert summary["n_infra_timeout"] == 1
    assert summary["n_quarantined"] == 1
    assert summary["worker_restarts"] == 1
    assert summary["job_by_status"]["succeeded_from_cache"] == 1
    assert summary["timeout_by_scope"]["import_timeout"] == 1
    assert summary["n_cache_hit"] == 1
    assert report["evidence"]["V_concept"] == 0.9
    assert report["evidence"]["n_jobs"] == 5
    assert report["evidence"]["n_infra_timeout"] == 1
    assert report["evidence"]["n_quarantined"] == 1
    assert report["evidence"]["n_cache_hit"] == 1
    assert report["evidence"]["worker_restarts"] == 1
    assert report["evidence"]["timeout_by_scope"]["tactic_timeout"] == 1
    assert report["evidence"]["job_by_status"]["timeout"] == 1

    con = sqlite3.connect(run / "runs.db")
    try:
        legacy = con.execute("SELECT schema_version FROM artifacts WHERE schema_version='legacy.unknown' LIMIT 1").fetchone()
        assert legacy is not None
        concept_edge = con.execute(
            "SELECT 1 FROM lineage_edges WHERE edge_type='concept_search_yields_repair_atom' LIMIT 1"
        ).fetchone()
        assert concept_edge is not None
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
