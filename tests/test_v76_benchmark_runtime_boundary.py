import argparse
import json
from pathlib import Path

from lean_rgc.cli import build_parser, main
from lean_rgc.schemas import read_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEAD_CANDIDATES = [
    "lean_rgc.acceptance_report",
    "lean_rgc.active_scheduler",
    "lean_rgc.audit_scheduler",
    "lean_rgc.defect_promotion",
    "lean_rgc.response_learner",
    "lean_rgc.response_quotient_registry",
    "lean_rgc.state_ir",
    "lean_rgc.trajectory_runner",
]


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def test_smoke_benchmark_corpus_has_stable_metadata():
    tasks = read_jsonl(ROOT / "benchmarks" / "smoke" / "tasks.jsonl")
    actions = read_jsonl(ROOT / "benchmarks" / "smoke" / "actions.jsonl")
    assert 5 <= len(tasks) <= 20
    assert 3 <= len(actions) <= 20
    for row in [*tasks, *actions]:
        assert row["schema_version"].startswith("lean-rgc.benchmark-")
        assert row["run_id"] == "benchmark_smoke"
        assert row["parent_ids"] == []
    assert {row["task_id"] for row in tasks} >= {"smoke_true", "smoke_eq_refl"}
    assert {row["action_id"] for row in actions} >= {"trivial", "simp", "rfl"}


def test_benchmark_smoke_cli_builds_run_db_and_checks_it(tmp_path: Path):
    out = tmp_path / "benchmark_smoke"
    assert main(["benchmark", "smoke", "--out", str(out), "--dry-run", "--run-db", "--quiet"]) == 0
    db = out / "runs.db"
    summary = out / "benchmark_smoke_summary.json"
    assert db.exists()
    assert summary.exists()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["run_db_check"]["ok"] is True
    assert main(["data", "check", "--db", str(db), "--json"]) == 0


def test_benchmark_command_is_registered_under_cli_package():
    parser = build_parser()
    choices = _command_choices(parser)
    assert "benchmark" in choices
    ns = parser.parse_args(["benchmark", "smoke", "--out", "runs/benchmark_smoke", "--dry-run", "--run-db"])
    assert ns.func.__module__ == "lean_rgc.cli.benchmark"


def test_inventory_classification_doc_mentions_dead_candidates():
    text = (ROOT / "docs" / "inventory" / "classification.md").read_text(encoding="utf-8")
    assert "dead_candidate" in text
    assert "investigation targets" in text
    for module in DEAD_CANDIDATES:
        assert module in text


def test_lean_runtime_facade_covers_cli_and_pipeline_runtime_apis():
    import lean_rgc.lean as lean
    import lean_rgc.bulk_executor as bulk_executor
    import lean_rgc.executor as executor
    import lean_rgc.lean_worker_supervisor as supervisor

    assert lean.LeanExecutor is executor.LeanExecutor
    assert lean.LeanExecutorConfig is executor.LeanExecutorConfig
    assert lean.BulkAuditConfig is bulk_executor.BulkAuditConfig
    assert lean.bulk_audit_to_files is bulk_executor.bulk_audit_to_files
    assert lean.enqueue_and_run_supervised_audit is supervisor.enqueue_and_run_supervised_audit
    assert lean.run_bulk_audit_queue is supervisor.run_bulk_audit_queue
    assert lean.run_supervised_audit_queue is supervisor.run_supervised_audit_queue
    assert (ROOT / "docs" / "lean_runtime_boundary.md").exists()
