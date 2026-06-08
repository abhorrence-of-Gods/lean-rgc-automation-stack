from pathlib import Path
from lean_rgc.schemas import LeanTask, write_jsonl, read_jsonl
from lean_rgc.executor import LeanExecutor, LeanExecutorConfig
from lean_rgc.exposure_frontier import build_exposure_frontiers


def test_exposure_frontier_selects_intro_on_forall():
    tasks=[LeanTask(task_id="t1", statement="∀ (n : Nat), n = n", imports=[])]
    executor=LeanExecutor(LeanExecutorConfig(dry_run=True))
    frontier, report, audits = build_exposure_frontiers(tasks, executor, max_exposures=4)
    assert len(frontier)==1
    assert "intro" in (frontier[0].get("prefix") or "")
    assert report[0]["score"] >= 0
