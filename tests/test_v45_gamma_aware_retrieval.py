import json
from pathlib import Path

from lean_rgc.action_geometry import score_action_geometry_registry
from lean_rgc.schemas import write_jsonl, read_jsonl


def test_gamma_finite_horizon_changes_action_geometry_score(tmp_path: Path):
    reg = tmp_path / "ag.jsonl"
    rows = [
        {
            "action_id": "stable_good",
            "tactic": "simp",
            "response_keys": ["goal.eq"],
            "response_embedding": [1.0],
            "carrier_embedding": {},
            "gamma_scalar": 0.5,
            "gamma_diag": [0.5],
            "spectral_radius_proxy": 0.5,
            "affine_bias": [0.0],
            "success_rate": 1.0,
            "cost_estimate": 0.0,
            "uncertainty": {},
        },
        {
            "action_id": "unstable_bad",
            "tactic": "simp",
            "response_keys": ["goal.eq"],
            "response_embedding": [1.0],
            "carrier_embedding": {},
            "gamma_scalar": 1.2,
            "gamma_diag": [1.2],
            "spectral_radius_proxy": 1.2,
            "affine_bias": [0.0],
            "success_rate": 1.0,
            "cost_estimate": 0.0,
            "uncertainty": {},
        },
    ]
    write_jsonl(reg, rows)
    out = tmp_path / "scored.jsonl"
    rep = score_action_geometry_registry(
        reg,
        out,
        response_normal={"goal.eq": 1.0},
        tail_weight=10.0,
        gamma_aware=True,
        gamma_mode="finite_horizon",
        gamma_horizon=2,
        gamma_stability_delta=0.05,
        gamma_tail_risk_mode="spectral",
    )
    scored = read_jsonl(out)
    assert rep["gamma_aware"] is True
    by = {r["action_id"]: r for r in scored}
    assert by["stable_good"]["gamma_tail_value_embedding"][0] == 1.75
    assert by["unstable_bad"]["score_terms"]["tail_risk"] > 0
    assert by["stable_good"]["action_geometry_score"] > by["unstable_bad"]["action_geometry_score"]
