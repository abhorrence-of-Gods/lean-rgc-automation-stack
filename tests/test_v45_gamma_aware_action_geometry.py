from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.action_geometry import score_action_geometry_registry
from lean_rgc.action_geometry_loop import run_action_geometry_from_qgen


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _rows(path: Path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def test_gamma_aware_finite_horizon_scores_tail_value(tmp_path: Path):
    reg = tmp_path / "reg.jsonl"
    _write_jsonl(reg, [
        {
            "action_id": "stable",
            "tactic": "simp",
            "response_keys": ["goal.eq"],
            "response_embedding": [1.0],
            "carrier_embedding": {},
            "gamma_scalar": 0.5,
            "spectral_radius_proxy": 0.5,
            "success_rate": 1.0,
            "cost_estimate": 0.0,
            "uncertainty": {},
        },
        {
            "action_id": "unstable",
            "tactic": "bad",
            "response_keys": ["goal.eq"],
            "response_embedding": [1.0],
            "carrier_embedding": {},
            "gamma_scalar": 1.2,
            "spectral_radius_proxy": 1.2,
            "success_rate": 1.0,
            "cost_estimate": 0.0,
            "uncertainty": {},
        },
    ])
    out = tmp_path / "scored.jsonl"
    rep = score_action_geometry_registry(
        reg,
        out,
        response_normal={"goal.eq": 1.0},
        gamma_aware=True,
        gamma_mode="finite_horizon",
        gamma_horizon=2,
        gamma_value_weight=1.0,
        gamma_stability_delta=0.05,
        tail_weight=10.0,
        cost_weight=0.0,
        uncertainty_weight=0.0,
        audit_weight=0.0,
    )
    rows = {r["action_id"]: r for r in _rows(out)}
    assert rep["gamma_aware"] is True
    assert rows["stable"]["score_terms"]["gamma_tail_response_score"] == 1.75
    assert rows["stable"]["score_terms"]["tail_risk"] == 0.0
    assert rows["unstable"]["score_terms"]["tail_risk"] > 0.0
    assert rows["unstable"]["action_geometry_score"] < rows["stable"]["action_geometry_score"]


def test_action_geometry_loop_uses_gamma_transition_patches(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    actions = tmp_path / "actions.jsonl"
    qnormal = tmp_path / "normal.json"
    patches = tmp_path / "patches.jsonl"
    _write_jsonl(actions, [{"action_id": "simp", "tactic": "simp", "cost_estimate": 0.0}])
    _write_jsonl(responses, [
        {"state_id": "s", "action_id": "simp", "response_keys": ["goal.eq"], "response_flat": [1.0], "carrier_delta": {}, "audit_status": "success", "action": {"action_id": "simp", "tactic": "simp"}}
    ])
    qnormal.write_text(json.dumps({"response_normal": {"goal.eq": 1.0}}), encoding="utf-8")
    _write_jsonl(patches, [{"action_id": "simp", "gamma_scalar": 0.5, "gamma_diag": [0.5], "spectral_radius_proxy": 0.5, "affine_bias": [0.0]}])
    rep = run_action_geometry_from_qgen(
        responses=responses,
        actions=actions,
        qgen_report=qnormal,
        out_dir=tmp_path / "ag",
        gamma_transition_patches=patches,
        gamma_aware=True,
        gamma_mode="finite_horizon",
        gamma_horizon=2,
        gamma_value_weight=1.0,
        tail_weight=0.0,
        cost_weight=0.0,
        uncertainty_weight=0.0,
        audit_weight=0.0,
    )
    rows = _rows(tmp_path / "ag" / "action_geometry_candidates_scored.jsonl")
    assert rep["gamma_aware"] is True
    assert rep["gamma_patch_report"] is not None
    assert rows[0]["score_terms"]["gamma_tail_response_score"] == 1.75
    assert rows[0]["gamma_tail_value_embedding"] == [1.75]
