import json
from pathlib import Path

import numpy as np
import pytest

from lean_rgc.grad.config import GradInvariantError, GradInvariants, assert_rollout_batch, assert_train_memory
from lean_rgc.grad.engine import RolloutEngine, run_grad_loop
from lean_rgc.grad.estimators import (
    degenerate_groups,
    grouped_rloo,
    rft_trace_selection,
    rloo_advantages,
    stratified_groups,
)
from lean_rgc.schemas import LeanTask, read_jsonl, stable_hash


# ---------- invariants -------------------------------------------------


def test_invariants_reject_verified_violations():
    with pytest.raises(GradInvariantError, match="batched decode"):
        GradInvariants(min_rollout_batch=4).validate()
    with pytest.raises(GradInvariantError, match="checkpointing"):
        GradInvariants(gradient_checkpointing=False).validate()
    with pytest.raises(GradInvariantError, match="inner_epochs"):
        GradInvariants(inner_epochs=2).validate()
    with pytest.raises(GradInvariantError, match="NF4"):
        GradInvariants(load_in_4bit=False).validate()
    with pytest.raises(GradInvariantError, match="batch floor"):
        GradInvariants(rollout_chunk=4).validate()
    with pytest.raises(GradInvariantError, match="output_logits"):
        GradInvariants(rollout_chunk=128).validate()
    GradInvariants().validate()  # defaults are the verified operating point


def test_assert_helpers_check_measured_values():
    assert_rollout_batch(16)
    with pytest.raises(GradInvariantError):
        assert_rollout_batch(2)
    assert_rollout_batch(2, allow_small=True)
    assert_train_memory(12.0, checkpointing_enabled=True)
    with pytest.raises(GradInvariantError):
        assert_train_memory(23.0, checkpointing_enabled=True)
    with pytest.raises(GradInvariantError):
        assert_train_memory(5.0, checkpointing_enabled=False)


# ---------- RLOO arithmetic --------------------------------------------


def test_rloo_advantages_leave_one_out_exact():
    adv = rloo_advantages([1.0, 0.0, 0.0, 0.0])
    assert adv[0] == pytest.approx(1.0)
    assert adv[1] == pytest.approx(-1.0 / 3.0)
    assert adv.sum() == pytest.approx(0.0)


def test_rloo_degenerate_groups_give_zero_gradient():
    assert np.allclose(rloo_advantages([1.0, 1.0, 1.0]), 0.0)
    groups = {"g0": [0.0, 0.0], "g1": [1.0, 0.0], "g2": [1.0, 1.0]}
    assert set(degenerate_groups(groups)) == {"g0", "g2"}
    advantages, stats = grouped_rloo(groups)
    assert stats.n_degenerate == 2
    assert stats.fraction_degenerate == pytest.approx(2.0 / 3.0)
    assert np.allclose(advantages["g0"], 0.0)
    assert not np.allclose(advantages["g1"], 0.0)


def test_stratified_groups_bucket_by_difficulty_and_keep_singletons():
    records = [{"task_id": f"t{i}", "action_id": f"a{i}", "reward": 0.0} for i in range(9)]
    difficulty = {f"t{i}": 0.05 for i in range(9)}  # all in one 'hard' bucket
    groups = stratified_groups(records, group_size=4, difficulty=difficulty)

    grouped = sum(len(v) for v in groups.values())
    assert grouped == 9, "trailing singleton must be merged, not dropped"
    assert sorted(len(v) for v in groups.values()) == [4, 5]


# ---------- RFT trace join ---------------------------------------------


def test_rft_trace_selection_joins_success_rows_to_boundaries():
    boundary = {"boundary_id": "pb_1", "statement": "True", "feedback_text": ""}
    micro = [
        {"task_id": "t0", "status": "success", "action": {"tactic": "exact trivial", "metadata": {"boundary_id": "pb_1"}}},
        {"task_id": "t0", "status": "fail", "action": {"tactic": "simp", "metadata": {"boundary_id": "pb_1"}}},
        {"task_id": "t0", "status": "success", "action": {"tactic": "rfl", "metadata": {"boundary_id": "pb_missing"}}},
        {"task_id": "t0", "status": "success", "action": {"tactic": "   ", "metadata": {"boundary_id": "pb_1"}}},
    ]
    traces = rft_trace_selection(micro, [boundary], success_statuses=("success",))
    assert len(traces) == 1
    assert traces[0]["tactic"] == "exact trivial"


# ---------- alternating loop with fakes ---------------------------------


class FakeEngine:
    """Mirrors the real engine contract: the batch floor is enforced with
    allow_small only when the caller passes it (which run_grad_loop must
    make unnecessary by topping up n_samples)."""

    def __init__(self, invariants: GradInvariants):
        self.inv = invariants
        self.train_calls: list[dict] = []
        self.last_feedback: dict[str, str] = {}
        self._last_rollout = {"tokens_per_second": 100.0, "peak_gb": 1.0, "batch": 0}

    def render_prompts(self, tasks, feedback, attempt_index):
        self.last_feedback = dict(feedback)
        return [
            {
                "task_id": t.task_id,
                "boundary": {"boundary_id": "pb_" + stable_hash({"t": t.task_id, "w": attempt_index}, 8)},
                "system": "s",
                "user": "u",
            }
            for t in tasks
        ]

    def generate(self, prompts, *, n_samples, seed=0, allow_small_batch=False):
        assert_rollout_batch(len(prompts) * n_samples, invariants=self.inv, allow_small=allow_small_batch)
        samples = []
        for p in prompts:
            for i in range(n_samples):
                if p["task_id"] == "t0" and i == 0 and self.last_feedback:
                    tactic = "win"
                elif p["task_id"] == "t1" and i == 1:
                    tactic = ""  # unparseable output: must stay in the RLOO group
                else:
                    tactic = f"lose{i}"
                samples.append(
                    {
                        **p,
                        "text": tactic,
                        "tactic": tactic,
                        "completion_ids": [1, 2],
                        "rollout_logprob_sum": -1.0,
                        "n_completion_tokens": 2,
                    }
                )
        self._last_rollout["batch"] = len(samples)
        return samples

    def train_step(self, *, rft_samples, rloo_samples):
        self.train_calls.append({"n_rft": len(rft_samples), "n_rloo": len(rloo_samples)})
        return {
            "losses": {"rft": 0.0, "rloo": 0.0, "kl_per_seq": 0.0},
            "n_terms": len(rft_samples) + len(rloo_samples),
            "n_kl_gated": 0,
            "grad_norm": 0.0,
            "train_peak_gb": 1.0,
        }


def _fake_audit(*, tasks, actions_by_task, wave_dir, run_id, drop_action_ids=frozenset(), **kw):
    rows = []
    for t in tasks:
        for a in actions_by_task.get(t.task_id, []):
            if a["action_id"] in drop_action_ids:
                continue
            ok = a["tactic"] == "win" or (t.task_id == "__positive_control__" and a["tactic"] == "trivial")
            rows.append(
                {
                    "task_id": t.task_id,
                    "action_id": a["action_id"],
                    "status": "success" if ok else "elab_error",
                    "messages": [] if ok else [f"error {t.task_id}"],
                    "action": {"action_id": a["action_id"], "tactic": a["tactic"], "metadata": a.get("metadata", {})},
                }
            )
    return rows


def test_run_grad_loop_alternates_tops_up_and_logs(tmp_path: Path):
    inv = GradInvariants(group_size=4)
    engine = FakeEngine(inv)
    tasks = [LeanTask(task_id="t0", statement="True", imports=[]), LeanTask(task_id="t1", statement="False", imports=[])]

    summary = run_grad_loop(
        tasks=tasks,
        out_dir=tmp_path,
        run_id="g0",
        invariants=inv,
        engine=engine,
        wave_audit_runner=_fake_audit,
        n_waves=3,
    )

    updates = read_jsonl(tmp_path / "grad_run.jsonl")
    assert summary["n_solved"] == 1  # t0 solves at wave 1 (feedback-dependent)
    assert summary["n_waves_run"] == 3
    assert engine.last_feedback.get("t1", "").startswith("Lean error:")
    # wavefront shrinks but the batch floor holds via per-task top-up:
    # wave 2 has 1 live task -> n_samples must rise to min_rollout_batch
    assert updates[0]["n_live_tasks"] == 2 and updates[0]["n_samples_per_task"] == 4
    assert updates[2]["n_live_tasks"] == 1 and updates[2]["n_samples_per_task"] == 8
    # empty tactics are visible and kept in the RLOO group with reward 0
    assert updates[0]["n_empty_tactic"] == 1
    assert updates[0]["audit_anomaly"] is False
    # RFT traces record the raw text actually reinforced
    traces = read_jsonl(tmp_path / "rft_traces.jsonl")
    assert len(traces) == 1 and traces[0]["tactic"] == "win" and traces[0]["text"] == "win"
    for row in updates:
        for field in ("rollout", "update", "rloo", "n_unaudited", "n_empty_tactic"):
            assert field in row


def test_run_grad_loop_excludes_unaudited_from_rloo(tmp_path: Path):
    inv = GradInvariants(group_size=8)
    engine = FakeEngine(inv)
    tasks = [LeanTask(task_id="t1", statement="False", imports=[])]
    dropped: set[str] = set()

    def audit(*, tasks, actions_by_task, wave_dir, run_id, **kw):
        # drop the first action's row: it must be excluded, not counted as failed
        # (the positive control run is left intact — it must pass to reach waves)
        if not run_id.endswith("_control"):
            for acts in actions_by_task.values():
                if acts:
                    dropped.add(acts[0]["action_id"])
        return _fake_audit(
            tasks=tasks, actions_by_task=actions_by_task, wave_dir=wave_dir, run_id=run_id,
            drop_action_ids=frozenset(dropped),
        )

    run_grad_loop(
        tasks=tasks, out_dir=tmp_path, run_id="g1", invariants=inv,
        engine=engine, wave_audit_runner=audit, n_waves=1,
    )
    updates = read_jsonl(tmp_path / "grad_run.jsonl")
    assert updates[0]["n_unaudited"] == 1


def test_clean_tactic_extracts_from_proposal_json():
    from lean_rgc.grad.engine import _clean_tactic

    js = '{"proposals": [{"proposal_kind": "tactic", "lean_tactic": "rw [h₁]; ring", "confidence": 0.9}]};'
    assert _clean_tactic(js) == "rw [h₁]; ring"
    assert _clean_tactic("norm_num") == "norm_num"
    assert _clean_tactic("```lean\nsimp\n```") == "simp"
    # truncated JSON falls back to the first line (fails Lean, reward 0)
    assert _clean_tactic('{"proposals": [{"lean_ta').startswith("{")


def test_run_grad_loop_positive_control_gate(tmp_path: Path):
    from lean_rgc.grad.config import GradInvariantError

    inv = GradInvariants(group_size=4)
    tasks = [LeanTask(task_id="t0", statement="True", imports=[])]

    def broken_audit(*, tasks, actions_by_task, wave_dir, run_id, **kw):
        return [
            {
                "task_id": t.task_id,
                "action_id": a["action_id"],
                "status": "fail",
                "messages": ["FileNotFoundError(2, 'No such file or directory')"],
                "action": a,
            }
            for t in tasks
            for a in actions_by_task.get(t.task_id, [])
        ]

    engine = FakeEngine(inv)
    with pytest.raises(GradInvariantError, match="positive control"):
        run_grad_loop(
            tasks=tasks, out_dir=tmp_path, run_id="gc", invariants=inv,
            engine=engine, wave_audit_runner=broken_audit, n_waves=1,
        )
    assert engine.train_calls == [], "no gradient step may run behind a failed control"


def test_run_grad_loop_aborts_on_majority_infra_failures(tmp_path: Path):
    from lean_rgc.grad.config import GradInvariantError

    inv = GradInvariants(group_size=8)
    tasks = [LeanTask(task_id="t1", statement="False", imports=[])]

    def audit(*, tasks, actions_by_task, wave_dir, run_id, **kw):
        rows = _fake_audit(tasks=tasks, actions_by_task=actions_by_task, wave_dir=wave_dir, run_id=run_id)
        if run_id.endswith("_control"):
            return rows
        for row in rows:  # Lean breaks mid-run: every wave row is an OS error
            row["status"] = "fail"
            row["messages"] = ["FileNotFoundError(2, 'No such file or directory')"]
        return rows

    with pytest.raises(GradInvariantError, match="infrastructure"):
        run_grad_loop(
            tasks=tasks, out_dir=tmp_path, run_id="gi", invariants=inv,
            engine=FakeEngine(inv), wave_audit_runner=audit, n_waves=1,
        )


def test_real_engine_requires_torch_lazily():
    engine = RolloutEngine(GradInvariants())
    prompts = engine.render_prompts([LeanTask(task_id="t0", statement="True", imports=[])], {}, 0)
    assert prompts[0]["system"].endswith("no code fences.")
    try:
        import torch  # noqa: F401

        pytest.skip("torch installed; lazy-import guard not testable here")
    except ImportError:
        with pytest.raises(ImportError, match="grad"):
            engine.generate(prompts, n_samples=8)
