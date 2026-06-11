import json
import sys
from pathlib import Path

from lean_rgc.audit_staging import rank_action_rows, run_staged_audit, should_escalate
from lean_rgc.executor import LeanExecutorConfig
from lean_rgc.schemas import LeanTask, read_jsonl


def _row(action_id: str, score: float) -> dict:
    return {"action_id": action_id, "tactic": "simp", "metadata": {"score": score}}


def _runner_with_status(status: str):
    def runner(*, stage_index, tasks, actions, stage_dir, run_id, **kwargs):
        return [{"action_id": a.action_id, "status": status} for a in actions]

    return runner


def _fake_lean(tmp_path: Path) -> str:
    script = tmp_path / "fake_lean.py"
    script.write_text(
        "\n".join(
            [
                "import sys",
                "if '--version' in sys.argv:",
                "    print('Lean (fake staged test)')",
                "    raise SystemExit(0)",
                "print('ok')",
                "raise SystemExit(0)",
            ]
        ),
        encoding="utf-8",
    )
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def test_ranking_is_deterministic_with_score_ties():
    rows = [_row("b_tied", 0.5), _row("a_tied", 0.5), _row("c_top", 0.9)]
    ranked = rank_action_rows(rows)
    assert [e["action_id"] for e in ranked] == ["c_top", "a_tied", "b_tied"]


def test_plan_hash_is_stable_across_runs(tmp_path: Path):
    rows = [_row("a1", 0.9), _row("a2", 0.5)]
    task = LeanTask(task_id="t0", statement="True", imports=[])
    summaries = []
    for name in ("run_a", "run_b"):
        summaries.append(
            run_staged_audit(
                tasks=[task],
                action_rows=rows,
                out_dir=tmp_path / name,
                run_id=name,
                stage_caps=(1, 2),
                audit_runner=_runner_with_status("failed"),
            )
        )
    assert summaries[0]["plan_hash"] == summaries[1]["plan_hash"]


def test_stops_when_predicted_upper_bound_below_realized(tmp_path: Path):
    rows = [_row("a_top1", 0.9), _row("a_top2", 0.8)] + [_row(f"a_low{i}", 0.3) for i in range(4)]
    task = LeanTask(task_id="t0", statement="True", imports=[])

    summary = run_staged_audit(
        tasks=[task],
        action_rows=rows,
        out_dir=tmp_path,
        run_id="r0",
        stage_caps=(2, 6),
        audit_runner=_runner_with_status("proved"),
    )

    assert summary["n_audited_actions"] == 2
    assert summary["n_skipped_actions"] == 4
    assert summary["stop_reason"] == "predicted_upper_bound_below_realized"
    assert summary["accounting_ok"] is True
    assert summary["best_audited"] == 1.0
    # success at audited 1.0 against predicted 0.9/0.8 must register as
    # underprediction so escalation soundness stays observable
    assert summary["calibration"]["n_underpredicted"] == 2
    assert abs(summary["calibration"]["max_underprediction"] - 0.2) < 1e-9

    stage_rows = read_jsonl(tmp_path / "audit_stage_rows.jsonl")
    skipped = [r for r in stage_rows if r["state"] == "stage_skipped"]
    assert len(skipped) == 4
    assert all(r["reason"] == "predicted_upper_bound_below_realized" for r in skipped)
    plan = json.loads((tmp_path / "audit_stage_plan.json").read_text(encoding="utf-8"))
    assert [e["action_id"] for e in plan["ranking"][:2]] == ["a_top1", "a_top2"]


def test_budget_jobs_never_exceeded_while_escalating(tmp_path: Path):
    rows = [_row(f"a{i}", 0.5) for i in range(8)]
    tasks = [
        LeanTask(task_id="t0", statement="True", imports=[]),
        LeanTask(task_id="t1", statement="True", imports=[]),
    ]

    summary = run_staged_audit(
        tasks=tasks,
        action_rows=rows,
        out_dir=tmp_path,
        run_id="r0",
        stage_caps=(2, 4, 8),
        budget_jobs=10,
        audit_runner=_runner_with_status("failed"),
    )

    assert summary["n_jobs_audited"] == 10
    assert summary["n_jobs_audited"] <= summary["budget_jobs"]
    assert summary["stop_reason"] == "budget_exhausted"
    assert summary["n_audited_actions"] == 5
    assert summary["n_skipped_actions"] == 3
    assert summary["accounting_ok"] is True


def test_escalation_decision_reasons():
    no_candidates = should_escalate(best_audited=0.0, max_predicted_unaudited=None, budget_remaining=10)
    assert no_candidates == {**no_candidates, "escalate": False, "reason": "no_candidates_remaining"}

    no_budget = should_escalate(best_audited=0.0, max_predicted_unaudited=0.9, budget_remaining=0)
    assert no_budget["reason"] == "budget_exhausted"

    bound = should_escalate(best_audited=0.8, max_predicted_unaudited=0.8, budget_remaining=10)
    assert bound["reason"] == "predicted_upper_bound_below_realized"

    gap = should_escalate(
        best_audited=0.7, max_predicted_unaudited=0.9, budget_remaining=10, relaxed_value=0.75, gap_min=0.1
    )
    assert gap["reason"] == "relaxed_gap_closed"

    go = should_escalate(best_audited=0.1, max_predicted_unaudited=0.9, budget_remaining=10)
    assert go == {**go, "escalate": True, "reason": "upper_bound_above_realized"}


def test_default_runner_smoke_with_fake_lean(tmp_path: Path):
    task = LeanTask(task_id="t0", statement="True", imports=[])
    rows = [_row("trivial", 0.5)]

    summary = run_staged_audit(
        tasks=[task],
        action_rows=rows,
        out_dir=tmp_path / "staged",
        run_id="smoke",
        stage_caps=(1,),
        executor_config=LeanExecutorConfig(lean_cmd=_fake_lean(tmp_path), timeout_s=5.0),
        backend="source_check_bulk",
        import_mode="preserve",
        queue_backend="bulk",
        workers=1,
        job_timeout_s=5.0,
    )

    assert summary["n_audited_actions"] == 1
    assert summary["n_jobs_audited"] == 1
    assert (tmp_path / "staged" / "audit_stage_plan.json").exists()
    assert (tmp_path / "staged" / "audit_stage_rows.jsonl").exists()
    assert (tmp_path / "staged" / "stage_0" / "responses.jsonl").exists()
