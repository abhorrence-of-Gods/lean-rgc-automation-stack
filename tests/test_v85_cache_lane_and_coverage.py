import json
import sqlite3
from pathlib import Path

from lean_rgc.audit_job_queue import connect_queue, enqueue_audit_jobs, lease_next_job, mark_job_result
from lean_rgc.audit_result_cache import (
    DEFAULT_CACHE_LANE,
    apply_cache_to_queue,
    connect_audit_cache,
    ensure_audit_cache_schema,
    make_audit_cache_key,
    store_queue_results_in_cache,
)
from lean_rgc.crg_audit import audit_crg_candidates
from lean_rgc.hardening_gap_report import build_hardening_gap_report
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl, stable_hash


def _payload() -> dict:
    return {
        "task": {"task_id": "t0", "statement": "True", "imports": [], "prefix": ""},
        "state": {"state_id": "s0", "task_id": "t0", "target": "True"},
        "action": {"action_id": "a0", "tactic": "trivial"},
    }


def _key_kwargs() -> dict:
    return {
        "lean_version": "Lean fake",
        "workdir_fingerprint_value": "wd",
        "import_mode": "preserve",
        "trace_state": False,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_cache_key_differs_by_lane():
    key_source, fields_source = make_audit_cache_key(_payload(), lane="source_check", **_key_kwargs())
    key_kernel, fields_kernel = make_audit_cache_key(_payload(), lane="kernel", **_key_kwargs())

    assert key_source != key_kernel
    assert fields_source["lane"] == "source_check"
    assert fields_kernel["lane"] == "kernel"


def test_cache_lookup_never_crosses_lanes(tmp_path: Path):
    cache = tmp_path / "cache.sqlite"
    task = LeanTask(task_id="t0", statement="True", imports=[])
    action = TacticAction(action_id="a0", tactic="trivial")
    result = {
        "audit": {"status": "ok", "audit_flags": {}},
        "response": {"response": {"goal.eq": 1.0}},
    }

    source_queue = tmp_path / "q_source.sqlite"
    enqueue_audit_jobs(
        source_queue,
        [task],
        [action],
        run_id="r_source",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value="fp",
        lane="source_check",
    )
    conn = connect_queue(source_queue)
    job = lease_next_job(conn, worker_id="w0")
    assert job is not None
    mark_job_result(conn, job.job_id, status="succeeded", result=result)
    conn.close()
    stored = store_queue_results_in_cache(
        cache_db=cache,
        queue_db=source_queue,
        run_id="r_source",
        **_key_kwargs(),
    )
    assert stored["n_stored"] == 1

    kernel_queue = tmp_path / "q_kernel.sqlite"
    enqueue_audit_jobs(
        kernel_queue,
        [task],
        [action],
        run_id="r_kernel",
        backend="kernel_rpc",
        import_mode="preserve",
        project_fingerprint_value="fp",
        lane="kernel",
    )
    kernel_apply = apply_cache_to_queue(
        cache_db=cache,
        queue_db=kernel_queue,
        run_id="r_kernel",
        **_key_kwargs(),
    )
    assert kernel_apply["n_cache_hit"] == 0
    assert kernel_apply["n_cache_miss"] == 1

    source_queue2 = tmp_path / "q_source2.sqlite"
    enqueue_audit_jobs(
        source_queue2,
        [task],
        [action],
        run_id="r_source2",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value="fp",
        lane="source_check",
    )
    source_apply = apply_cache_to_queue(
        cache_db=cache,
        queue_db=source_queue2,
        run_id="r_source2",
        **_key_kwargs(),
    )
    assert source_apply["n_cache_hit"] == 1


def test_v65_cache_rows_migrate_with_source_check_backfill(tmp_path: Path):
    db = tmp_path / "old_cache.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE audit_result_cache (
            cache_key TEXT PRIMARY KEY,
            task_hash TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            tactic_hash TEXT NOT NULL,
            imports_hash TEXT NOT NULL,
            lean_version TEXT NOT NULL,
            workdir_fingerprint TEXT NOT NULL,
            import_mode TEXT NOT NULL,
            max_heartbeats TEXT NOT NULL,
            trace_state INTEGER NOT NULL,
            audit_status TEXT,
            queue_status TEXT,
            result_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            last_hit_at REAL,
            hit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    fields_v65 = {
        "task_hash": "th",
        "state_hash": "sh",
        "tactic_hash": "ah",
        "imports_hash": "ih",
        "lean_version": "Lean fake",
        "workdir_fingerprint": "wd",
        "import_mode": "preserve",
        "max_heartbeats": "",
        "trace_state": 0,
    }
    old_key = stable_hash(fields_v65, 48)
    conn.execute(
        """
        INSERT INTO audit_result_cache(
            cache_key, task_hash, state_hash, tactic_hash, imports_hash,
            lean_version, workdir_fingerprint, import_mode, max_heartbeats,
            trace_state, audit_status, queue_status, result_json,
            created_at, updated_at, last_hit_at, hit_count
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (old_key, "th", "sh", "ah", "ih", "Lean fake", "wd", "preserve", "", 0, "ok", "succeeded", "{}", 0.0, 0.0, None, 0),
    )
    conn.commit()
    conn.close()

    conn = connect_audit_cache(db)
    ensure_audit_cache_schema(conn)
    new_key = stable_hash({**fields_v65, "lane": DEFAULT_CACHE_LANE}, 48)
    migrated = conn.execute(
        "SELECT lane FROM audit_result_cache WHERE cache_key=?", (new_key,)
    ).fetchone()
    stale = conn.execute(
        "SELECT cache_key FROM audit_result_cache WHERE cache_key=?", (old_key,)
    ).fetchone()
    conn.close()

    assert migrated is not None
    assert migrated["lane"] == DEFAULT_CACHE_LANE
    assert stale is None


def test_crg_audit_coverage_caps_promotion_readiness(tmp_path: Path):
    candidates = [
        {
            "candidate_id": "c_partial",
            "problem_id": "p1",
            "objective": {"lambda_normal": {"goal.eq": 1.0}},
            "scores": {"lambda_response": 0.8},
        },
        {
            "candidate_id": "c_full",
            "problem_id": "p2",
            "objective": {"lambda_normal": {"goal.eq": 1.0}},
            "scores": {"lambda_response": 0.8},
        },
    ]
    attempts = [
        {"candidate_id": "c_partial", "hard_candidates": [{"action_id": "h1"}, {"action_id": "h2"}]},
        {"candidate_id": "c_full", "hard_candidates": [{"action_id": "h3"}]},
    ]
    responses = [
        {"action_id": "h1", "status": "ok", "response": {"goal.eq": 0.9}},
        {"action_id": "h3", "status": "ok", "response": {"goal.eq": 0.9}},
    ]
    candidates_path = tmp_path / "candidates.jsonl"
    attempts_path = tmp_path / "attempts.jsonl"
    responses_path = tmp_path / "responses.jsonl"
    out_rows = tmp_path / "crg_audit_rows.jsonl"
    _write_jsonl(candidates_path, candidates)
    _write_jsonl(attempts_path, attempts)
    _write_jsonl(responses_path, responses)

    summary = audit_crg_candidates(
        candidates_path=candidates_path,
        hardening_attempts_path=attempts_path,
        out_rows=out_rows,
        audited_responses_path=responses_path,
    )
    rows = {row["candidate_id"]: row for row in read_jsonl(out_rows)}

    partial = rows["c_partial"]
    assert partial["audit_coverage"] == "partial"
    assert partial["n_hard_actions_total"] == 2
    assert partial["n_hard_actions_audited"] == 1
    assert partial["audited_score"] > 0.0
    assert partial["promotion_readiness"] == "paid_witness"

    full = rows["c_full"]
    assert full["audit_coverage"] == "full"
    assert full["promotion_readiness"] == "promotion_candidate"

    assert summary["coverage_counts"]["partial"] == 1
    assert summary["coverage_counts"]["full"] == 1
    assert summary["n_promotion_candidates"] == 1


def test_hardening_gap_report_separates_underaudited(tmp_path: Path):
    rows = [
        {"candidate_id": "c_full", "relaxed_score": 0.7, "audited_score": 0.0, "hardening_gap": 0.7, "audit_coverage": "full"},
        {"candidate_id": "c_skipped", "relaxed_score": 0.7, "audited_score": 0.0, "hardening_gap": 0.7, "audit_coverage": "none"},
        {"candidate_id": "c_partial", "relaxed_score": 0.7, "audited_score": 0.0, "hardening_gap": 0.7, "audit_coverage": "partial"},
        {"candidate_id": "c_legacy", "relaxed_score": 0.7, "audited_score": 0.0, "hardening_gap": 0.7},
    ]
    rows_path = tmp_path / "crg_audit_rows.jsonl"
    out = tmp_path / "hardening_gap_report.json"
    _write_jsonl(rows_path, rows)

    report = build_hardening_gap_report(crg_audit_rows_path=rows_path, out=out)

    assert report["classification_counts"]["grammar_defect_candidate"] == 2
    assert report["classification_counts"]["underaudited"] == 2
    defect_ids = {case["candidate_id"] for case in report["grammar_defect_candidates"]}
    assert defect_ids == {"c_full", "c_legacy"}
