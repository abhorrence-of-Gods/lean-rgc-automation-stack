import json
import sys
from pathlib import Path

from lean_rgc.audit_job_queue import audit_queue_status
from lean_rgc.audit_pruning import normalize_tactic, prune_actions_file
from lean_rgc.audit_result_cache import make_audit_cache_key
from lean_rgc.executor import LeanExecutorConfig
from lean_rgc.lean_worker_supervisor import enqueue_and_run_supervised_audit
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl


def _fake_lean(tmp_path: Path) -> str:
    script = tmp_path / "fake_lean.py"
    script.write_text(
        "\n".join(
            [
                "import sys",
                "if '--version' in sys.argv:",
                "    print('Lean (fake cache test)')",
                "    raise SystemExit(0)",
                "print('ok')",
                "raise SystemExit(0)",
            ]
        ),
        encoding="utf-8",
    )
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def test_audit_cache_reuses_result_across_runs(tmp_path: Path):
    cache = tmp_path / "audit_cache.sqlite"
    task = LeanTask(task_id="t0", statement="True", imports=[])
    action = TacticAction(action_id="trivial", tactic="trivial")
    lean_cmd = _fake_lean(tmp_path)

    first = enqueue_and_run_supervised_audit(
        db_path=tmp_path / "run1.sqlite",
        tasks=[task],
        actions_by_task=[action],
        out_dir=tmp_path / "run1",
        executor_config=LeanExecutorConfig(lean_cmd=lean_cmd, timeout_s=5.0),
        run_id="run1",
        backend="source_check_bulk",
        import_mode="preserve",
        queue_backend="bulk",
        workers=1,
        job_timeout_s=5.0,
        audit_cache_db=cache,
    )
    second = enqueue_and_run_supervised_audit(
        db_path=tmp_path / "run2.sqlite",
        tasks=[task],
        actions_by_task=[action],
        out_dir=tmp_path / "run2",
        executor_config=LeanExecutorConfig(lean_cmd=lean_cmd, timeout_s=5.0),
        run_id="run2",
        backend="source_check_bulk",
        import_mode="preserve",
        queue_backend="bulk",
        workers=1,
        job_timeout_s=5.0,
        audit_cache_db=cache,
    )

    assert first["n_succeeded"] == 1
    assert second["n_succeeded"] == 1
    assert second["n_cache_hit"] == 1
    assert second["n_executed_this_run"] == 0
    assert audit_queue_status(tmp_path / "run2.sqlite", run_id="run2")["by_status"]["succeeded_from_cache"] == 1
    responses = read_jsonl(tmp_path / "run2" / "responses.jsonl")
    audits = read_jsonl(tmp_path / "run2" / "micro_audit.jsonl")
    assert responses[0]["cache_hit"] is True
    assert audits[0]["audit_flags"]["cache_hit"] is True


def test_audit_cache_key_misses_when_imports_change():
    base_payload = {
        "task": {"task_id": "t0", "statement": "True", "imports": ["A"], "prefix": ""},
        "state": {"state_id": "s0", "task_id": "t0", "target": "True"},
        "action": {"action_id": "a0", "tactic": "trivial"},
    }
    changed = json.loads(json.dumps(base_payload))
    changed["task"]["imports"] = ["B"]

    key_a, _ = make_audit_cache_key(
        base_payload,
        lean_version="Lean fake",
        workdir_fingerprint_value="wd",
        import_mode="preserve",
        trace_state=False,
    )
    key_b, _ = make_audit_cache_key(
        changed,
        lean_version="Lean fake",
        workdir_fingerprint_value="wd",
        import_mode="preserve",
        trace_state=False,
    )

    assert key_a != key_b


def test_prune_actions_file_dedups_normalized_tactics_and_preserves_baseline(tmp_path: Path):
    actions = tmp_path / "actions.jsonl"
    out = tmp_path / "pruned.jsonl"
    report = tmp_path / "report.json"
    rows = [
        {"action_id": "baseline", "tactic": "simp", "metadata": {"score": 0.1}},
        {"action_id": "probe1", "tactic": "  simp   -- same tactic", "metadata": {"baseline_action_id": "baseline", "score": 0.5}},
        {"action_id": "probe2", "tactic": "simp", "metadata": {"score": 0.4}},
        {"action_id": "better", "tactic": "exact True.intro", "cost_estimate": 2.0, "metadata": {"score": 1.0}},
        {"action_id": "worse", "tactic": "exact True.intro", "cost_estimate": 5.0, "metadata": {"score": 1.0}},
    ]
    actions.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    rep = prune_actions_file(actions, out, report_out=report, n_tasks=8)
    pruned = read_jsonl(out)
    ids = {r["action_id"] for r in pruned}

    assert normalize_tactic("  simp   -- comment\n") == "simp"
    assert "probe1" in ids
    assert "baseline" in ids
    assert "probe2" not in ids
    assert "better" in ids
    assert "worse" not in ids
    assert rep["n_pruned"] == 2
    assert rep["estimated_jobs_saved"] == 16
    assert report.exists()
