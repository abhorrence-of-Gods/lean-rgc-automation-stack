from pathlib import Path
from lean_rgc.schemas import LeanTask
from lean_rgc.executor import LeanExecutorConfig
from lean_rgc.frontier import exposure_actions_for_task, build_frontiers


def test_exposure_actions_for_forall():
    task = LeanTask(task_id="t", statement="∀ (n : Nat), n = n", imports=[])
    acts = exposure_actions_for_task(task, max_prefixes=8)
    assert any("intro" in a.tactic for a in acts)


def test_build_frontiers_dry(tmp_path: Path):
    tasks = [LeanTask(task_id="t", statement="∀ (n : Nat), n = n", imports=[])]
    rep = build_frontiers(tasks, executor_config=LeanExecutorConfig(dry_run=True), out_dir=tmp_path, max_prefixes=4)
    assert (tmp_path / "frontier_tasks.jsonl").exists()
    assert (tmp_path / "exposure_audit.jsonl").exists()
    assert rep["n_records"] >= 1
