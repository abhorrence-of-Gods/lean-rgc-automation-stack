from pathlib import Path
import json

from lean_rgc.qgen import qgen_from_files
from lean_rgc.lineage import build_qgen_lineage
from lean_rgc.schemas import write_jsonl
from lean_rgc.registry_acceptance import run_registry_acceptance


def _row(state, action_id, resp, defect, carrier=None, status='success'):
    return {
        'state_id': state,
        'task_id': state,
        'action_id': action_id,
        'audit_status': status,
        'response_flat': resp,
        'response_keys': ['goal.eq', 'carrier.missing_simp'],
        'defect_before': {'flat': defect, 'flat_keys': ['goal.eq', 'carrier.missing_simp']},
        'carrier_delta': carrier or {},
        'action': {
            'action_id': action_id,
            'tactic': 'simp' if 'simp' in action_id else 'rfl',
            'tactic_class': 'test',
            'carrier_tags': [],
            'cost_estimate': 1.0,
            'metadata': {},
        },
    }


def test_qgen_lineage_and_parent_residuals(tmp_path: Path):
    responses = tmp_path / 'responses.jsonl'
    write_jsonl(responses, [
        _row('s0', 'a_simp', [0.2, 0.6], [0.1, 1.0], {'missing_simp': 0.4}),
        _row('s0', 'a_rfl', [0.1, 0.0], [0.1, 1.0], {}),
    ])
    qdir = tmp_path / 'qgen'
    rep = qgen_from_files(responses, out_dir=qdir, top_defects=2, top_contexts=2)
    candidates = [json.loads(line) for line in (qdir / 'qgen_context_candidates.jsonl').read_text().splitlines() if line.strip()]
    assert candidates
    qmeta = candidates[0]['metadata']['qgen']
    assert qmeta['lineage_id']
    assert qmeta['parent_residual_keys']
    graph = build_qgen_lineage(qdir, out=qdir / 'qgen_lineage.json')
    assert graph['summary']['n_context_candidates'] == len(candidates)
    assert any(e['kind'] == 'coker_normal_generates_context' for e in graph['edges'])
    assert (qdir / 'qgen_lineage.json').exists()


def test_registry_acceptance_robust_margin(tmp_path: Path):
    base = tmp_path / 'base.jsonl'
    cand = tmp_path / 'cand.jsonl'
    write_jsonl(base, [_row('s0', 'base0', [0.1, 0.0], [1.0, 0.0])])
    write_jsonl(cand, [_row('s0', 'cand0', [1.0, 0.0], [1.0, 0.0])])
    rows, summary = run_registry_acceptance(
        base,
        cand,
        tmp_path / 'rows.jsonl',
        accepted_actions_out=tmp_path / 'accepted.jsonl',
        robust_radius=0.5,
        accept_on_robust=True,
    )
    assert 'mean_robust_margin' in summary
    assert rows[0]['robust_penalty'] > 0
    assert rows[0]['robust_margin'] < rows[0]['margin']
    accepted = [json.loads(line) for line in (tmp_path / 'accepted.jsonl').read_text().splitlines() if line.strip()]
    if accepted:
        meta = accepted[0]['metadata']
        assert 'acceptance_robust_margin' in meta
