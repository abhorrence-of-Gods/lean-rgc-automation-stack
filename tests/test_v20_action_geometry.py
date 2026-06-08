from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.action_geometry import build_action_geometry_registry, score_action_geometry_registry, audit_action_cocycles, teacher_constraints_from_arithmetic_actions


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def test_action_geometry_registry_and_retrieve(tmp_path: Path):
    responses = tmp_path / 'responses.jsonl'
    actions = tmp_path / 'actions.jsonl'
    transitions = tmp_path / 'transitions.jsonl'
    _write_jsonl(actions, [
        {'action_id': 'simp', 'tactic': 'simp', 'tactic_class': 'simp', 'carrier_tags': ['missing_simp_lemma'], 'cost_estimate': 0.4},
        {'action_id': 'omega', 'tactic': 'omega', 'tactic_class': 'arith', 'carrier_tags': ['nat_arith_goal'], 'cost_estimate': 0.8},
    ])
    _write_jsonl(responses, [
        {'state_id': 's1', 'action_id': 'simp', 'response_flat': [1.0, 0.0], 'response_keys': ['goal.eq','carrier.simp'], 'response': {'goal.eq': 1.0}, 'carrier_delta': {'missing_simp_lemma': 0.5}, 'audit_status': 'success', 'action': {'action_id': 'simp', 'tactic': 'simp'}},
        {'state_id': 's2', 'action_id': 'simp', 'response_flat': [0.8, 0.1], 'response_keys': ['goal.eq','carrier.simp'], 'response': {'goal.eq': 0.8}, 'carrier_delta': {'missing_simp_lemma': 0.2}, 'audit_status': 'partial', 'action': {'action_id': 'simp', 'tactic': 'simp'}},
        {'state_id': 's1', 'action_id': 'omega', 'response_flat': [0.1, 1.0], 'response_keys': ['goal.eq','carrier.simp'], 'response': {'goal.eq': 0.1}, 'carrier_delta': {'nat_arith_goal': 0.7}, 'audit_status': 'success', 'action': {'action_id': 'omega', 'tactic': 'omega'}},
    ])
    _write_jsonl(transitions, [
        {'action_id': 'simp', 'defect': [1.0, 0.0], 'pred_response': [0.5, 0.0], 'next_defect': [0.2, 0.0]},
        {'action_id': 'omega', 'defect': [0.0, 1.0], 'pred_response': [0.0, 0.4], 'next_defect': [0.0, 0.3]},
    ])
    out = tmp_path / 'registry.jsonl'
    summary = build_action_geometry_registry(responses, out, summary_out=tmp_path/'summary.json', actions_path=actions, transitions_path=transitions)
    assert summary['n_embeddings'] == 2
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert {r['action_id'] for r in rows} == {'simp', 'omega'}
    assert rows[0]['canonical_status'].endswith('not_canonical')
    scored = tmp_path / 'scored.jsonl'
    s2 = score_action_geometry_registry(out, scored, response_normal={'goal.eq': 1.0}, carrier_normal={'missing_simp_lemma': 0.2}, top_k=1)
    assert s2['n_scored'] == 1
    top = json.loads(scored.read_text().splitlines()[0])
    assert top['action_id'] == 'simp'
    assert 'action_geometry_score' in top


def test_action_cocycle_and_teacher_constraints(tmp_path: Path):
    reg = tmp_path / 'reg.jsonl'
    comps = tmp_path / 'comps.jsonl'
    _write_jsonl(reg, [
        {'action_id': 'a', 'response_embedding': [1.0], 'carrier_embedding': {'c': 0.1}, 'gamma_scalar': 0.5, 'affine_bias': [0.1]},
        {'action_id': 'b', 'response_embedding': [2.0], 'carrier_embedding': {'c': 0.2}, 'gamma_scalar': 0.5, 'affine_bias': [0.2]},
        {'action_id': 'ba', 'response_embedding': [3.0], 'carrier_embedding': {'c': 0.3}, 'gamma_scalar': 0.25, 'affine_bias': [0.25]},
    ])
    _write_jsonl(comps, [{'a': 'a', 'b': 'b', 'ab': 'ba'}])
    out = tmp_path / 'cocycle.jsonl'
    summary = audit_action_cocycles(reg, comps, out, summary_out=tmp_path/'cocycle_summary.json', accept_threshold=0.2)
    assert summary['n_compositions'] == 1
    row = json.loads(out.read_text().splitlines()[0])
    assert row['cocycle_accept'] is True
    actions = tmp_path / 'actions.jsonl'
    _write_jsonl(actions, [
        {'action_id': 'x1', 'tactic': 'simp', 'metadata': {'arith': {'expr': 'a*(b+c)'}}},
        {'action_id': 'x2', 'tactic': 'ring_nf', 'metadata': {'arith': {'expr': 'a*(b+c)'}}},
        {'action_id': 'x3', 'tactic': 'omega', 'metadata': {'teacher_equiv': ['x4']}},
    ])
    tout = tmp_path / 'teacher.jsonl'
    ts = teacher_constraints_from_arithmetic_actions(actions, tout, summary_out=tmp_path/'teacher_summary.json')
    assert ts['n_constraints'] == 2
