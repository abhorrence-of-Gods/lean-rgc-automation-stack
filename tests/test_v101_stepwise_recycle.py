"""S'1 rider acceptance: the stepwise driver recycles its Lean worker.

The kernel_rpc worker retains every KState (each pinning an Environment)
with no eviction op, so a whole-corpus single-worker run OOMs. Chains
never span scripts, so recycling at script boundaries must be
behavior-preserving: same transitions, ceil(n_scripts / recycle_every)
worker instances.
"""
from types import SimpleNamespace

import lean_rgc.lean.server as server_mod
from lean_rgc.evals.stepwise_replay import replay_scripts

CREATED = []


class FakeAdapter:
    def __init__(self, cfg):
        CREATED.append(self)
        self.registered = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def load_project(self):
        pass

    def register_task(self, task):
        self.registered += 1
        return {"state": {"state_id": f"{task.task_id}_s0"}}

    def apply_tactic_to_state_id(self, task, action, sid, create_state=True):
        return SimpleNamespace(
            status="success",
            elapsed_ms=1.0,
            messages=[],
            after_state=None,
            audit_flags={"kernel_state": {"state_id": sid + "x"}},
        )


def test_recycle_preserves_transitions_and_bounds_worker_lifetime(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "LeanServerAdapter", FakeAdapter)
    CREATED.clear()
    scripts = [
        {"task_id": f"t{i}", "script": "intro x; ring", "source": "success_script"}
        for i in range(10)
    ]
    task_defs = {
        f"t{i}": {"task_id": f"t{i}", "statement": "theorem x : True := by trivial", "imports": []}
        for i in range(10)
    }
    summary = replay_scripts(
        scripts, task_defs, out_dir=tmp_path, lean_cmd="fake", timeout_s=1.0,
        recycle_every=3,
    )
    counts = summary["counts"]
    assert counts["scripts"] == 10
    assert counts["transitions"] == 20  # 2 steps per script, none broken
    assert counts["broken_chains"] == 0
    assert len(CREATED) == 4  # ceil(10/3) workers
    assert counts["worker_recycles"] == 3
    assert sum(a.registered for a in CREATED) == 10


def test_recycle_every_one_is_a_fresh_worker_per_script(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "LeanServerAdapter", FakeAdapter)
    CREATED.clear()
    scripts = [{"task_id": "t0", "script": "ring", "source": "success_script"}] * 3
    task_defs = {"t0": {"task_id": "t0", "statement": "theorem x : True := by trivial", "imports": []}}
    replay_scripts(scripts, task_defs, out_dir=tmp_path, lean_cmd="fake", timeout_s=1.0, recycle_every=1)
    assert len(CREATED) == 3
