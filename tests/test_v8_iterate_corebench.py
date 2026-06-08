from pathlib import Path
from lean_rgc.corebench import write_corebench
from lean_rgc.schemas import read_jsonl
from lean_rgc.iterative import run_iterative_pipeline


def test_make_corebench(tmp_path):
    out = tmp_path / 'core.jsonl'
    summary = write_corebench(out, n_nat=3, n_prop=3, n_bool=2, n_eq=2)
    rows = read_jsonl(out)
    assert summary['n_tasks'] == len(rows)
    assert len(rows) >= 8
    assert any('∀' in r['statement'] for r in rows)


def test_iterative_dry_pipeline(tmp_path):
    tasks = tmp_path / 'tasks.jsonl'
    write_corebench(tasks, n_nat=1, n_prop=1, n_bool=0, n_eq=1)
    rep = run_iterative_pipeline(tasks=str(tasks), actions=None, out=str(tmp_path / 'iter'), rounds=1, dry_run=True, jobs=1, max_actions=4, import_mode='core', fit_gamma=True)
    assert rep['rounds']
    assert Path(rep['rounds'][0]['out_dir']).exists()
    assert (tmp_path / 'iter' / 'iterate_summary.json').exists()


def test_iterative_qgen_round(tmp_path):
    tasks = tmp_path / 'tasks_qgen.jsonl'
    write_corebench(tasks, n_nat=1, n_prop=1, n_bool=0, n_eq=1)
    rep = run_iterative_pipeline(
        tasks=str(tasks),
        actions=None,
        out=str(tmp_path / 'iter_qgen'),
        rounds=1,
        dry_run=True,
        jobs=1,
        max_actions=4,
        import_mode='core',
        fit_gamma=True,
        qgen=True,
        qgen_merge_actions=True,
        qgen_top_contexts=4,
    )
    r0 = Path(rep['rounds'][0]['out_dir'])
    assert (r0 / 'qgen' / 'qgen_report.json').exists()
    assert (r0 / 'qgen' / 'qgen_context_candidates.jsonl').exists()
    assert rep['rounds'][0].get('qgen_contexts') is not None


def test_iterative_qgen_audit_accept_round(tmp_path):
    tasks = tmp_path / 'tasks_qgen_audit.jsonl'
    write_corebench(tasks, n_nat=1, n_prop=1, n_bool=0, n_eq=1)
    rep = run_iterative_pipeline(
        tasks=str(tasks),
        actions=None,
        out=str(tmp_path / 'iter_qgen_audit'),
        rounds=1,
        dry_run=True,
        jobs=1,
        max_actions=4,
        import_mode='core',
        fit_gamma=True,
        qgen=True,
        audit_qgen_candidates=True,
        qgen_accept_coker=True,
        qgen_merge_actions=True,
        qgen_top_contexts=4,
        qgen_audit_max_actions=4,
    )
    r0 = Path(rep['rounds'][0]['out_dir'])
    assert (r0 / 'qgen_audit' / 'responses.jsonl').exists()
    assert (r0 / 'qgen_accepted_actions.jsonl').exists()
    assert (r0 / 'qgen_acceptance_report.json').exists()
    assert rep['rounds'][0]['n_actions_next'] >= 0
