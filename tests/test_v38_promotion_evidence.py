from pathlib import Path

from lean_rgc.promotion_evidence import generate_promotion_evidence
from lean_rgc.poms_promotion import collect_poms_promotion
from lean_rgc.schemas import write_jsonl


def test_promotion_evidence_generates_poms_ready_rows(tmp_path: Path):
    root = tmp_path
    r0 = root / "round_00" / "quotient_coordinates"
    r0.mkdir(parents=True)
    write_jsonl(root / "poms_status_rows.jsonl", [
        {
            "kind": "context_action", "source": "qgen", "action_id": "a1", "tactic": "simp", "poms_status": "accepted_witness",
            "action": {"action_id": "a1", "tactic": "simp", "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"]}}},
        },
        {
            "kind": "context_action", "source": "qgen", "action_id": "a2", "tactic": "rw", "poms_status": "accepted_witness",
            "action": {"action_id": "a2", "tactic": "rw", "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"]}}},
        },
    ])
    write_jsonl(r0 / "state_coker_normals.jsonl", [
        {"state_id": "s", "residual_norm": 0.5, "relative_residual": 0.7, "support_state_ids": ["s"], "top_loadings": [{"key": "goal.eq", "weight": 0.8}]}
    ])
    write_jsonl(root / "round_00" / "qgen_robust_acceptance_rows.jsonl", [
        {"action_id": "a1", "tactic": "simp", "accepted": True, "robust_margin": 0.4, "margin": 0.4, "score": 0.4, "action": {"action_id": "a1", "tactic": "simp", "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"]}}}},
        {"action_id": "a2", "tactic": "rw", "accepted": True, "robust_margin": 0.1, "margin": 0.1, "score": 0.1, "action": {"action_id": "a2", "tactic": "rw", "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"]}}}},
    ])
    rep = generate_promotion_evidence(root, out_poms=root / "promotion_evidence_for_poms.jsonl")
    assert rep["summary"]["n_parent_nonpaid_keys"] == 1
    assert rep["summary"]["n_dual_actions"] == 2
    assert rep["summary"]["n_least_repair_actions"] == 1
    prom = collect_poms_promotion(root, evidence=[root / "promotion_evidence_for_poms.jsonl"], out_jsonl=root / "promoted.jsonl")
    rows = prom["rows"]
    by_id = {r["action_id"]: r for r in rows}
    assert by_id["a1"]["poms_promoted_status"] == "canonical_candidate"
    assert by_id["a2"]["poms_promoted_status"] == "forced_candidate"


def test_promotion_evidence_cli(tmp_path: Path):
    from lean_rgc.cli import main
    root = tmp_path
    (root / "round_00" / "carrier_quotient").mkdir(parents=True)
    write_jsonl(root / "poms_status_rows.jsonl", [
        {"kind": "carrier_incidence_patch", "source": "carrier_quotient", "action_id": "a", "carrier_atom": "carrier.x", "poms_status": "carrier_patch_witness"}
    ])
    write_jsonl(root / "round_00" / "carrier_quotient" / "carrier_state_coker_normals.jsonl", [
        {"state_id": "s", "residual_norm": 1.0, "relative_residual": 1.0, "top_loadings": [{"key": "carrier.x"}]}
    ])
    write_jsonl(root / "round_00" / "qgen_carrier_incidence_audited.jsonl", [
        {"action_id": "a", "carrier_atom": "carrier.x", "accepted_by_patch_audit": True, "observed_mean_delta": 0.3}
    ])
    rc = main([
        "poms-evidence", "--run-dir", str(root), "--out-json", str(root / "ev.json"), "--out-poms", str(root / "ev_poms.jsonl")
    ])
    assert rc == 0
    assert (root / "ev.json").exists()
    assert (root / "ev_poms.jsonl").exists()
