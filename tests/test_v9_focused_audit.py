from pathlib import Path
from lean_rgc.focused import run_focused_micro_audit
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl
from lean_rgc.executor import LeanExecutorConfig


def test_focused_audit_dry_run(tmp_path: Path):
    tasks = [LeanTask(task_id='t_forall', statement='∀ (n : Nat), n = n', imports=[])]
    actions = [TacticAction(action_id='rfl', tactic='rfl', tactic_class='exact', carrier_tags=['eq'])]
    rep = run_focused_micro_audit(tasks, out_dir=tmp_path, executor_config=LeanExecutorConfig(dry_run=True), base_actions=actions, max_exposures=4, max_core_actions=4)
    assert rep['n_tasks'] == 1
    assert (tmp_path/'responses.jsonl').exists()
    rows = read_jsonl(tmp_path/'responses.jsonl')
    assert any(r.get('phase') == 'core_after_exposure' for r in rows)
    tactics = [r.get('action', {}).get('tactic','') for r in rows]
    assert any('rfl' in t for t in tactics)
    assert (tmp_path/'frontier_tasks.jsonl').exists()
