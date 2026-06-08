from pathlib import Path
from lean_rgc.schemas import write_jsonl
from lean_rgc.proof_replay import scripts_from_trajectories, export_proof_file, replay_proof_scripts
from lean_rgc.executor import LeanExecutorConfig


def test_extract_export_replay_dry(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    traj = tmp_path / "traj.jsonl"
    scripts = tmp_path / "scripts.jsonl"
    write_jsonl(tasks, [{"task_id":"t1","statement":"∀ (n : Nat), n = n","imports":[],"max_heartbeats":200000}])
    write_jsonl(traj, [{"task_id":"t1","final_status":"proved","prefix":"intros\nrfl","steps":[{"step":0}]}])
    meta = scripts_from_trajectories(traj, tasks, scripts)
    assert meta["n_scripts"] == 1
    lean_file = tmp_path / "proofs.lean"
    exp = export_proof_file(scripts, lean_file)
    assert exp["n_scripts"] == 1
    assert "intros" in lean_file.read_text()
    rep = replay_proof_scripts(scripts, tmp_path / "replay", LeanExecutorConfig(dry_run=True))
    assert rep["n"] == 1
    # dry-run heuristic should consider intro+rfl as success for forall equality.
    assert rep["replayed"] == 1
