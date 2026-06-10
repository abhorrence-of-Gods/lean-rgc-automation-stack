import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from lean_rgc.action_quarantine import ensure_quarantine_schema
from lean_rgc.audit_job_queue import connect_queue, ensure_audit_queue_schema
from lean_rgc.batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW
from lean_rgc.cli import main
from lean_rgc.concept_geometry import SCHEMA_CONCEPT_EDGE, SCHEMA_CONCEPT_POINT, build_concept_geometry
from lean_rgc.crg_hardening import SCHEMA_CRG_HARDENING, harden_crg_candidates
from lean_rgc.crg_optimizer import SCHEMA_CRG_CANDIDATE, optimize_crg_candidates
from lean_rgc.crg_problem import SCHEMA_CRG_PROBLEM, build_crg_problems
from lean_rgc.crg_registry import SCHEMA_REPAIR_SPECIES_REGISTRY, build_repair_species_registry
from lean_rgc.data.store import RunStore, build_run_db, check_run_db_invariants, summarize_run_db
from lean_rgc.lean_server import LeanServerConfig, audit_with_lean_server
from lean_rgc.poms_promotion_service import SCHEMA_POMS_PROMOTION_SERVICE, run_poms_promotion_service
from lean_rgc.relaxed_species import SCHEMA_RELAXED_SPECIES
from lean_rgc.repair_db import failure_attribution_report
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl, write_jsonl, write_records
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
        invariants = check_run_db_invariants(conn)
    finally:
        conn.close()

    required = {
        "runs",
        "artifacts",
        "schema_migrations",
        "tasks",
        "actions",
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
    }
    assert required <= tables
    assert invariants["ok"] is True


def test_write_records_stamps_canonical_metadata(tmp_path: Path):
    out = tmp_path / "records.jsonl"
    write_records(out, [{"response_id": "r1", "status": "success"}], schema_version="lean-rgc.response.v1", run_id="run_1", parent_ids=["p0"], artifact_ref="artifact://responses")
    rows = read_jsonl(out)
    assert rows == [
        {
            "artifact_ref": "artifact://responses",
            "parent_ids": ["p0"],
            "response_id": "r1",
            "run_id": "run_1",
            "schema_version": "lean-rgc.response.v1",
            "status": "success",
        }
    ]


def test_write_records_preserves_existing_metadata_and_handles_empty_files(tmp_path: Path):
    out = tmp_path / "preserve.jsonl"
    write_records(
        out,
        [{"schema_version": "custom.v0", "run_id": "run_existing", "parent_ids": ["old"], "artifact_ref": "old", "value": 1}],
        schema_version="new.v1",
        run_id="run_new",
        parent_ids=["new"],
        artifact_ref="new",
    )
    assert read_jsonl(out) == [{"schema_version": "custom.v0", "run_id": "run_existing", "parent_ids": ["old"], "artifact_ref": "old", "value": 1}]
    empty = tmp_path / "empty.jsonl"
    write_records(empty, [], schema_version="empty.v1", run_id="run_empty")
    assert empty.exists()
    assert empty.read_text(encoding="utf-8") == ""


def test_data_importers_import_without_cli_process():
    code = """
import sys
import lean_rgc.data.store
import lean_rgc.data.importers.audit
import lean_rgc.data.importers.lineage
import lean_rgc.data.importers.poms
import lean_rgc.data.importers.repair
assert 'lean_rgc.cli' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_high_value_writers_emit_canonical_rows_and_db_artifacts(tmp_path: Path):
    run_id = "run_writer"
    parent_ids = ["parent_0"]

    audit_dir = tmp_path / "audit"
    audit_with_lean_server(
        [LeanTask(task_id="t_true", statement="True", imports=[])],
        [TacticAction(action_id="trivial", tactic="trivial")],
        out_dir=audit_dir,
        server_config=LeanServerConfig(dry_run=True, backend="dry_run"),
        max_actions=1,
        run_id=run_id,
        parent_ids=parent_ids,
    )

    actions_path = tmp_path / "inputs" / "actions.jsonl"
    write_jsonl(actions_path, [{"action_id": "simp", "tactic": "simp", "response_embedding": {"goal.closed": 1.0}, "cost_estimate": 0.1}])
    registry = tmp_path / "crg" / "repair_species_registry.jsonl"
    build_repair_species_registry(out=registry, actions_path=actions_path, run_id=run_id, parent_ids=parent_ids)

    faces = tmp_path / "inputs" / "repair_faces.jsonl"
    write_jsonl(faces, [{"face_id": "face_1", "positive_response_face": {"goal.closed": 1.0}}])
    problems = tmp_path / "crg" / "crg_problems.jsonl"
    build_crg_problems(out=problems, repair_faces_path=faces, run_id=run_id, parent_ids=parent_ids)

    candidates = tmp_path / "crg" / "relaxed_candidates.jsonl"
    optimize_crg_candidates(problems_path=problems, registry_path=registry, out=candidates, run_id=run_id, parent_ids=parent_ids)

    attempts = tmp_path / "crg" / "hardening_attempts.jsonl"
    hard_actions = tmp_path / "crg" / "hard_candidates.jsonl"
    harden_crg_candidates(candidates_path=candidates, out_attempts=attempts, out_actions=hard_actions, run_id=run_id, parent_ids=parent_ids)

    taxonomy = tmp_path / "inputs" / "taxonomy.jsonl"
    features = tmp_path / "inputs" / "features.jsonl"
    write_jsonl(taxonomy, [{"taxonomy_face_id": "tax_1", "positive_face": {"response_basis": ["summary::resp_pos::goal.closed"]}, "status": {"heldout_validated": True}}])
    write_jsonl(features, [{"feature_id": "feature_1"}])
    concept_dir = tmp_path / "concept_geometry"
    build_concept_geometry(out_dir=concept_dir, taxonomy_path=taxonomy, selected_features_path=features, run_id=run_id, parent_ids=parent_ids)

    poms_rows = tmp_path / "poms_status_rows.jsonl"
    evidence = tmp_path / "poms_evidence.jsonl"
    decisions = tmp_path / "poms_promotion_decisions.jsonl"
    write_jsonl(poms_rows, [{"action_id": "simp", "poms_status": "accepted_witness"}])
    write_jsonl(evidence, [{"action_id": "simp", "parent_nonpaid": True, "dual_certificate": True, "least_repair": True}])
    run_poms_promotion_service(tmp_path, poms_rows=poms_rows, evidence=[evidence], out_jsonl=decisions, run_id=run_id, parent_ids=parent_ids)

    expected = {
        audit_dir / "micro_audit.jsonl": SCHEMA_AUDIT_ROW,
        audit_dir / "responses.jsonl": SCHEMA_RESPONSE_ROW,
        audit_dir / "defects.jsonl": SCHEMA_DEFECT_ROW,
        registry: None,
        problems: SCHEMA_CRG_PROBLEM,
        candidates: SCHEMA_CRG_CANDIDATE,
        attempts: SCHEMA_CRG_HARDENING,
        hard_actions: SCHEMA_CRG_HARDENING,
        concept_dir / "concept_points.jsonl": SCHEMA_CONCEPT_POINT,
        concept_dir / "concept_edges.jsonl": SCHEMA_CONCEPT_EDGE,
        decisions: SCHEMA_POMS_PROMOTION_SERVICE,
    }
    for path, schema in expected.items():
        rows = read_jsonl(path)
        assert rows, path
        if schema is not None:
            assert all(row["schema_version"] == schema for row in rows)
        else:
            assert all(row.get("schema_version") for row in rows)
        assert all(row["run_id"] == run_id for row in rows)
        assert all(row["parent_ids"] == parent_ids for row in rows)
        assert all("payload_json" not in row for row in rows)

    summary = build_run_db(tmp_path, tmp_path / "runs.db", run_id=run_id)
    assert summary["invariants"]["ok"] is True
    con = sqlite3.connect(tmp_path / "runs.db")
    try:
        schemas = {
            row[0]
            for row in con.execute(
                "SELECT schema_version FROM artifacts WHERE schema_version IS NOT NULL AND schema_version <> 'legacy.unknown'"
            ).fetchall()
        }
    finally:
        con.close()
    assert {
        SCHEMA_RESPONSE_ROW,
        SCHEMA_RELAXED_SPECIES,
        SCHEMA_CRG_PROBLEM,
        SCHEMA_CRG_CANDIDATE,
        SCHEMA_CRG_HARDENING,
        SCHEMA_CONCEPT_POINT,
        SCHEMA_POMS_PROMOTION_SERVICE,
    } <= schemas


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
    assert summary["tables"]["responses"] == 2
    assert summary["tables"]["audit_events"] == 1
    assert summary["tables"]["schema_migrations"] >= 1
    assert summary["invariants"]["ok"] is True
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
        canonical = con.execute(
            "SELECT schema_version, run_id, response_id FROM responses WHERE action_id='simp' LIMIT 1"
        ).fetchone()
        assert canonical is not None
        assert canonical[0] == "lean-rgc.canonical.v1"
        assert canonical[1] == summary["run_id"]
    finally:
        con.close()


def test_cli_and_pipeline_run_db_smoke(tmp_path: Path):
    run = tmp_path / "run"
    write_jsonl(run / "audit" / "responses.jsonl", [{"state_id": "s", "action_id": "a", "audit_status": "fail", "response": {"x": -1.0}}])
    assert main(["run-db-build", "--run-dir", str(run), "--db", str(run / "runs.db")]) == 0
    assert main(["run-db-query", "--db", str(run / "runs.db"), "--sql", "SELECT COUNT(*) AS n FROM response_rows"]) == 0
    assert main(["data", "query", "--db", str(run / "runs.db"), "--sql", "SELECT COUNT(*) AS n FROM responses"]) == 0
    assert main(["data", "summarize", "--db", str(run / "runs.db")]) == 0
    assert main(["data", "lineage", "--db", str(run / "runs.db")]) == 0
    summary = build_run_db(run, run / "runs.db", append=True)
    assert summary["tables"]["responses"] == 1
    run2 = tmp_path / "run2"
    write_jsonl(run2 / "audit" / "responses.jsonl", [{"state_id": "s2", "action_id": "b", "audit_status": "success", "response": {"x": 1.0}}])
    assert main(["data", "build", "--run-dir", str(run2), "--db", str(run2 / "runs.db")]) == 0
    con2 = sqlite3.connect(run2 / "runs.db")
    try:
        assert con2.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 1
    finally:
        con2.close()

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
