import json
from pathlib import Path

import pytest

from lean_rgc.evals.arms import render_feedback
from lean_rgc.evals.harness import run_eval, select_task_subset
from lean_rgc.evals.report import build_eval_report
from lean_rgc.schemas import LeanTask, read_jsonl


def _tasks(n: int) -> list[LeanTask]:
    return [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(n)]


def _proposal_fn_solving(solutions: dict[str, int]):
    """Propose the winning tactic for task t only at wave solutions[t]."""

    def proposal_fn(*, task, attempt_index, feedback):
        if solutions.get(task.task_id) == attempt_index:
            return [{"tactic": "winning"}]
        return [{"tactic": "losing"}]

    return proposal_fn


def _wave_runner(*, wave_index, tasks, actions_by_task, wave_dir, run_id, **kwargs):
    rows = []
    for task in tasks:
        for action in actions_by_task.get(task.task_id, []):
            status = "proved" if action.tactic == "winning" else "elab_error"
            rows.append(
                {
                    "task_id": task.task_id,
                    "action_id": action.action_id,
                    "status": status,
                    "messages": [f"error in {task.task_id} wave {wave_index}"],
                }
            )
    return rows


def test_wavefront_episodes_and_budget(tmp_path: Path):
    tasks = _tasks(3)
    # t0 solves on wave 0, t1 on wave 2, t2 never solves
    summary = run_eval(
        tasks=tasks,
        arm="a1_raw_error",
        proposal_fn=_proposal_fn_solving({"t0": 0, "t1": 2}),
        out_dir=tmp_path,
        run_id="r0",
        budget_calls=4,
        wave_audit_runner=_wave_runner,
    )
    episodes = {r["task_id"]: r for r in read_jsonl(tmp_path / "episodes.jsonl")}

    assert summary["n_solved"] == 2
    assert episodes["t0"]["solved"] is True
    assert episodes["t0"]["attempts_used"] == 1
    assert episodes["t0"]["first_solve_attempt"] == 1
    assert episodes["t1"]["attempts_used"] == 3
    assert episodes["t1"]["first_solve_attempt"] == 3
    assert episodes["t2"]["solved"] is False
    assert episodes["t2"]["attempts_used"] == 4
    assert summary["total_llm_calls"] == 1 + 3 + 4


def test_eval_harness_treats_lean_success_as_solved(tmp_path: Path):
    def proposal_fn(**kwargs):
        return [{"action_id": "a0", "tactic": "trivial"}]

    def runner(*, tasks, **kwargs):
        return [{"task_id": task.task_id, "audit_status": "success"} for task in tasks]

    summary = run_eval(
        tasks=[LeanTask(task_id="t0", statement="True", imports=[])],
        arm="a1_raw_error",
        proposal_fn=proposal_fn,
        out_dir=tmp_path,
        run_id="r0",
        budget_calls=1,
        wave_audit_runner=runner,
    )

    assert summary["n_solved"] == 1


def test_arm_feedback_isolation():
    state = {"n_failed": 2, "last_errors": ["unknown identifier foo", "type mismatch"]}
    a0 = render_feedback("a0_onebit", state)
    a1 = render_feedback("a1_raw_error", state)

    assert "Previous failed attempts: 2." in a0
    assert "unknown identifier" not in a0
    assert "unknown identifier foo" in a1
    with pytest.raises(NotImplementedError):
        render_feedback("a2_typed_packet", state)
    with pytest.raises(ValueError):
        render_feedback("a9_unknown", state)


def test_a1_feedback_reaches_proposal_fn(tmp_path: Path):
    seen: list[str] = []

    def proposal_fn(*, task, attempt_index, feedback):
        seen.append(feedback)
        return [{"tactic": "losing"}]

    run_eval(
        tasks=_tasks(1),
        arm="a1_raw_error",
        proposal_fn=proposal_fn,
        out_dir=tmp_path,
        run_id="r0",
        budget_calls=2,
        wave_audit_runner=_wave_runner,
    )

    assert "Previous failed attempts: 0." in seen[0]
    assert "Lean error: error in t0 wave 0" in seen[1]


def test_subset_selection_is_deterministic():
    rows = [{"task_id": f"t{i}"} for i in range(20)]
    first = select_task_subset(rows, n=5, seed=0)
    second = select_task_subset(rows, n=5, seed=0)
    other_seed = select_task_subset(rows, n=5, seed=1)

    assert first == second
    assert len(first) == 5
    assert first != other_seed


def _write_episodes(path: Path, solved_by_task: dict[str, bool]) -> None:
    rows = [
        {"task_id": tid, "solved": solved, "llm_calls": 4, "audit_pass_count": 1 if solved else 0}
        for tid, solved in solved_by_task.items()
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_report_paired_bootstrap_detects_dominant_arm(tmp_path: Path):
    task_ids = [f"t{i}" for i in range(40)]
    _write_episodes(tmp_path / "a_strong.jsonl", {tid: True for tid in task_ids})
    _write_episodes(tmp_path / "b_weak.jsonl", {tid: (i % 4 == 0) for i, tid in enumerate(task_ids)})

    report = build_eval_report(
        episodes_paths={"a_strong": tmp_path / "a_strong.jsonl", "b_weak": tmp_path / "b_weak.jsonl"},
        out=tmp_path / "report.json",
        n_bootstrap=2000,
        seed=0,
    )

    assert report["arms"]["a_strong"]["solve_rate"] == 1.0
    comparison = report["paired_comparisons"][0]
    assert comparison["arm_a"] == "a_strong"
    assert comparison["mean_delta"] == 0.75
    assert comparison["ci_excludes_zero"] is True
    assert (tmp_path / "report.json").exists()


def test_report_primary_comparison_uses_preregistered_direction(tmp_path: Path):
    task_ids = [f"t{i}" for i in range(40)]
    _write_episodes(tmp_path / "a1.jsonl", {tid: (i % 4 == 0) for i, tid in enumerate(task_ids)})
    _write_episodes(tmp_path / "a2.jsonl", {tid: True for tid in task_ids})

    report = build_eval_report(
        episodes_paths={"a1_raw_error": tmp_path / "a1.jsonl", "a2_typed_packet": tmp_path / "a2.jsonl"},
        out=tmp_path / "report.json",
        n_bootstrap=2000,
        seed=0,
    )

    primary = report["primary_comparison"]
    assert primary["arm_a"] == "a2_typed_packet"
    assert primary["arm_b"] == "a1_raw_error"
    assert primary["mean_delta"] == 0.75
    assert primary["ci_low"] > 0


def test_report_rejects_mismatched_task_sets(tmp_path: Path):
    _write_episodes(tmp_path / "a.jsonl", {"t0": True, "t1": False})
    _write_episodes(tmp_path / "b.jsonl", {"t0": True, "t2": False})

    with pytest.raises(ValueError, match="different task sets"):
        build_eval_report(
            episodes_paths={"a": tmp_path / "a.jsonl", "b": tmp_path / "b.jsonl"},
            out=tmp_path / "report.json",
        )
