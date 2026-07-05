"""R5: state-level RLOO baselines + difficulty-stratified grouping wiring."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from lean_rgc.grad.config import GradInvariants, assert_rollout_batch
from lean_rgc.grad.difficulty import load_difficulty_table, task_difficulty_from_micro_rows
from lean_rgc.grad.engine import run_grad_loop
from lean_rgc.grad.estimators import grouped_rloo, rloo_advantages
from lean_rgc.schemas import LeanTask, read_jsonl, stable_hash


# ---------------- estimator math ----------------

def test_baselines_none_is_identical_to_legacy():
    r = [1.0, 0.0, 0.0, 1.0]
    assert np.allclose(rloo_advantages(r), rloo_advantages(r, baselines=None))


def test_constant_baseline_cancels_exactly():
    r = [1.0, 0.0, 0.0]
    assert np.array_equal(rloo_advantages(r), rloo_advantages(r, baselines=[0.4, 0.4, 0.4]))


def test_all_fail_group_with_varying_baselines_carries_signal():
    # Both fail; failing on the easy state (b=0.8) must be punished harder
    # than failing on the hard one (b=0.1).
    adv = rloo_advantages([0.0, 0.0], baselines=[0.8, 0.1])
    assert adv[0] < 0.0 < adv[1]
    # Raw-degenerate group without baselines stays exactly zero.
    assert np.array_equal(rloo_advantages([0.0, 0.0]), np.zeros(2))


def test_grouped_rloo_baselines_and_raw_degeneracy_stats():
    groups = {"g": [0.0, 0.0], "h": [1.0, 0.0]}
    baselines = {"g": [0.9, 0.1]}
    advantages, stats = grouped_rloo(groups, baselines=baselines)
    assert advantages["g"][0] < 0.0 < advantages["g"][1]
    # Degeneracy is counted on raw rewards for cross-mode comparability.
    assert stats.n_degenerate == 1


# ---------------- difficulty table ----------------

def test_task_difficulty_orders_and_shrinks():
    rows = (
        [{"task_id": "easy", "status": "success"}] * 6
        + [{"task_id": "easy", "status": "fail"}] * 2
        + [{"task_id": "hard", "status": "fail"}] * 8
    )
    table = task_difficulty_from_micro_rows(rows, shrinkage=4.0)
    assert table["easy"] > table["hard"] > 0.0  # shrinkage keeps hard above 0


def test_load_difficulty_table_accepts_both_formats(tmp_path: Path):
    (tmp_path / "bare.json").write_text('{"t": 0.25}', encoding="utf-8")
    (tmp_path / "report.json").write_text('{"schema_version": "x", "table": {"t": 0.25}}', encoding="utf-8")
    assert load_difficulty_table(tmp_path / "bare.json") == {"t": 0.25}
    assert load_difficulty_table(tmp_path / "report.json") == {"t": 0.25}


# ---------------- loop wiring (FakeEngine integration) ----------------

class _Engine:
    def __init__(self, invariants: GradInvariants):
        self.inv = invariants
        self._last_rollout = {"tokens_per_second": 1.0, "peak_gb": 1.0, "batch": 0}

    def render_prompts(self, tasks, feedback, attempt_index):
        return [
            {"task_id": t.task_id, "boundary": {"boundary_id": "pb_" + stable_hash({"t": t.task_id, "w": attempt_index}, 8)}, "system": "s", "user": "u"}
            for t in tasks
        ]

    def generate(self, prompts, *, n_samples, seed=0, allow_small_batch=False):
        assert_rollout_batch(len(prompts) * n_samples, invariants=self.inv, allow_small=allow_small_batch)
        out = []
        for p in prompts:
            for i in range(n_samples):
                out.append({**p, "text": f"x{i}", "tactic": f"x{i}", "completion_ids": [1], "rollout_logprob_sum": -1.0, "n_completion_tokens": 1})
        self._last_rollout["batch"] = len(out)
        return out

    def train_step(self, *, rft_samples, rloo_samples):
        self.last_rloo = list(rloo_samples)
        return {"losses": {"rft": 0.0, "rloo": 0.0, "kl_per_seq": 0.0}, "grad_norm": 0.0, "n_terms": len(rloo_samples), "n_kl_gated": 0, "n_rft_in": len(rft_samples), "n_rloo_in": len(rloo_samples), "train_peak_gb": 1.0}


def _audit_all_fail(*, tasks, actions_by_task, wave_dir, run_id, **kw):
    rows = []
    for t in tasks:
        for a in actions_by_task.get(t.task_id, []):
            if t.task_id == "t1" and a["tactic"] == "x0":
                # One row never comes back (unaudited): makes per-task counts
                # ragged so bucket chunking crosses task boundaries — the
                # situation stratified grouping exists for.
                continue
            ok = t.task_id == "__positive_control__" and a["tactic"] == "trivial"
            rows.append({
                "task_id": t.task_id,
                "action_id": a["action_id"],
                "status": "success" if ok else "fail",
                "messages": [] if ok else ["error"],
                "action": {"action_id": a["action_id"], "tactic": a["tactic"], "metadata": a.get("metadata", {})},
            })
    return rows


def test_run_grad_loop_stratified_mixes_same_bucket_tasks(tmp_path: Path):
    inv = GradInvariants(group_size=4)
    engine = _Engine(inv)
    tasks = [LeanTask(task_id=f"t{i}", statement="True", imports=[]) for i in range(3)]
    # t0 easy bucket; t1/t2 share the hard bucket. The audit drops one t1 row
    # (unaudited), so the hard bucket has 7 records and its first chunk of 4
    # mixes t1 and t2 — baselines then vary within the group.
    difficulty = {"t0": 0.9, "t1": 0.15, "t2": 0.1}

    run_grad_loop(
        tasks=tasks,
        out_dir=tmp_path,
        run_id="strat",
        invariants=inv,
        engine=engine,
        wave_audit_runner=_audit_all_fail,
        n_waves=1,
        difficulty=difficulty,
    )
    updates = read_jsonl(tmp_path / "grad_run.jsonl")
    assert updates[0]["rloo_grouping"] == "stratified"
    # All rewards are 0, but mixed-difficulty groups + baselines still emit
    # nonzero advantages (the all-fail rescue).
    assert any(abs(adv) > 1e-9 for _, adv in engine.last_rloo)


def test_run_grad_loop_default_grouping_unchanged(tmp_path: Path):
    inv = GradInvariants(group_size=4)
    engine = _Engine(inv)
    tasks = [LeanTask(task_id="t0", statement="True", imports=[])]
    run_grad_loop(
        tasks=tasks,
        out_dir=tmp_path,
        run_id="plain",
        invariants=inv,
        engine=engine,
        wave_audit_runner=_audit_all_fail,
        n_waves=1,
    )
    updates = read_jsonl(tmp_path / "grad_run.jsonl")
    assert updates[0]["rloo_grouping"] == "task"
    # Per-task all-fail group is degenerate: advantages exactly zero.
    assert all(abs(adv) < 1e-12 for _, adv in engine.last_rloo)
