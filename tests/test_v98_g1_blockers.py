"""G1 launch blockers: RFT dedup/cap, drift-guard config, concentration gauge, eval mode."""

from __future__ import annotations

from pathlib import Path

from lean_rgc.grad.config import GradInvariants, assert_rollout_batch
from lean_rgc.grad.engine import _gini, run_grad_loop
from lean_rgc.schemas import LeanTask, read_jsonl, stable_hash


def test_gini_even_and_concentrated():
    assert _gini([]) == 0.0
    assert _gini([3, 3, 3]) == 0.0
    assert _gini([10, 0, 0]) > 0.6
    assert 0.0 <= _gini([5, 3, 1]) <= 1.0


def test_config_carries_g1_blocker_fields():
    d = GradInvariants().to_dict()
    assert d["rft_kl_beta"] == 0.05
    assert d["rft_max_traces_per_task"] == 2
    assert d["adapter_path"] is None


class _Engine:
    def __init__(self, invariants: GradInvariants, *, winner_task: str | None = None):
        self.inv = invariants
        self.winner_task = winner_task
        self.train_calls: list[dict] = []
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
                if p["task_id"] == self.winner_task:
                    tactic = f"win{i // 2}"  # duplicates AND >cap distinct winners
                else:
                    tactic = f"lose{i}"
                out.append({**p, "text": tactic, "tactic": tactic, "completion_ids": [1], "rollout_logprob_sum": -1.0, "n_completion_tokens": 1})
        self._last_rollout["batch"] = len(out)
        return out

    def train_step(self, *, rft_samples, rloo_samples):
        self.train_calls.append({"rft": list(rft_samples), "rloo": list(rloo_samples)})
        return {"losses": {"rft": 0.0, "rloo": 0.0, "kl_per_seq": 0.0, "rft_kl_per_seq": 0.0}, "grad_norm": 0.0, "n_terms": 0, "n_kl_gated": 0, "n_rft_in": len(rft_samples), "n_rloo_in": len(rloo_samples), "train_peak_gb": 1.0}


def _audit(*, tasks, actions_by_task, wave_dir, run_id, **kw):
    rows = []
    for t in tasks:
        for a in actions_by_task.get(t.task_id, []):
            ok = a["tactic"].startswith("win") or (t.task_id == "__positive_control__" and a["tactic"] == "trivial")
            rows.append({
                "task_id": t.task_id, "action_id": a["action_id"],
                "status": "success" if ok else "fail",
                "messages": [] if ok else ["error"],
                "action": {"action_id": a["action_id"], "tactic": a["tactic"], "metadata": a.get("metadata", {})},
            })
    return rows


def test_rft_dedup_and_cap(tmp_path: Path):
    inv = GradInvariants(group_size=8)
    engine = _Engine(inv, winner_task="t0")
    tasks = [LeanTask(task_id="t0", statement="True", imports=[])]
    run_grad_loop(
        tasks=tasks, out_dir=tmp_path, run_id="dc", invariants=inv,
        engine=engine, wave_audit_runner=_audit, n_waves=1,
    )
    row = read_jsonl(tmp_path / "grad_run.jsonl")[0]
    # 8 winning samples -> 4 distinct tactics (each twice): 4 dedup-dropped,
    # cap=2 keeps 2, 2 cap-dropped.
    assert row["n_rft_dedup_dropped"] == 4
    assert row["n_rft_cap_dropped"] == 2
    assert row["n_rft_traces"] == 2
    assert row["trace_concentration"]["n_tasks_with_traces"] == 1
    assert row["trace_concentration"]["top1_share"] == 1.0
    assert engine.train_calls and len(engine.train_calls[0]["rft"]) == 2


def test_eval_mode_skips_training_and_emits_episodes(tmp_path: Path):
    inv = GradInvariants(group_size=8)
    engine = _Engine(inv, winner_task="t0")
    tasks = [
        LeanTask(task_id="t0", statement="True", imports=[]),
        LeanTask(task_id="t1", statement="False", imports=[]),
    ]
    summary = run_grad_loop(
        tasks=tasks, out_dir=tmp_path, run_id="ev", invariants=inv,
        engine=engine, wave_audit_runner=_audit, n_waves=3,
        train=False, samples_per_task=1,
    )
    assert engine.train_calls == []
    rows = read_jsonl(tmp_path / "grad_run.jsonl")
    assert rows[0]["train_enabled"] is False
    assert rows[0]["update"] == {"skipped": "eval_mode"}
    assert rows[0]["n_samples_per_task"] == 1
    episodes = {e["task_id"]: e for e in read_jsonl(tmp_path / "episodes.jsonl")}
    assert episodes["t0"]["solved"] is True and episodes["t0"]["first_solve_wave"] == 0
    assert episodes["t1"]["solved"] is False and episodes["t1"]["first_solve_wave"] is None
    assert summary["n_solved"] == 1


def test_online_difficulty_wave0_unstratified_then_stratified(tmp_path: Path):
    inv = GradInvariants(group_size=8)
    engine = _Engine(inv, winner_task=None)  # nobody solves: 2 full waves
    tasks = [
        LeanTask(task_id="t0", statement="True", imports=[]),
        LeanTask(task_id="t1", statement="False", imports=[]),
    ]
    run_grad_loop(
        tasks=tasks, out_dir=tmp_path, run_id="od", invariants=inv,
        engine=engine, wave_audit_runner=_audit, n_waves=2,
        online_difficulty=True,
    )
    rows = read_jsonl(tmp_path / "grad_run.jsonl")
    # Wave 0 has no prior counts -> unstratified; wave 1 uses wave 0's rows.
    assert rows[0]["rloo_grouping"] == "task"
    assert rows[1]["rloo_grouping"] == "stratified"


def test_train_mode_still_writes_episodes(tmp_path: Path):
    inv = GradInvariants(group_size=8)
    engine = _Engine(inv, winner_task=None)
    tasks = [LeanTask(task_id="t0", statement="True", imports=[])]
    run_grad_loop(
        tasks=tasks, out_dir=tmp_path, run_id="tr", invariants=inv,
        engine=engine, wave_audit_runner=_audit, n_waves=1,
    )
    episodes = read_jsonl(tmp_path / "episodes.jsonl")
    assert len(episodes) == 1 and episodes[0]["train_enabled"] is True
