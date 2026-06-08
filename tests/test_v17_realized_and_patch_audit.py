from pathlib import Path

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.realized_response import collect_qgen_realized_calibration
from lean_rgc.carrier_patch_audit import audit_carrier_incidence_patches


def test_qgen_realized_calibration(tmp_path: Path):
    r0 = tmp_path / "round_00"
    r1 = tmp_path / "round_01" / "audit"
    r0.mkdir(parents=True)
    r1.mkdir(parents=True)
    accepted = {
        "action_id": "a1",
        "tactic": "simp",
        "metadata": {"task_id": "t1", "qgen": {"lineage_id": "L1", "parent_residual_keys": ["goal.eq"]}},
    }
    write_jsonl(r0 / "qgen_robust_accepted_actions.jsonl", [accepted])
    write_jsonl(r1 / "responses.jsonl", [{
        "task_id": "t1",
        "state_id": "s1",
        "action": accepted,
        "audit_status": "success",
        "response": {"goal.eq": 0.7},
        "carrier_delta": {"missing_simp_lemma": 0.1},
    }])
    rep = collect_qgen_realized_calibration(tmp_path, out_json=tmp_path / "cal.json", out_csv=tmp_path / "cal.csv")
    assert rep["summary"]["n_accepted_records"] == 1
    assert rep["summary"]["n_reaudited_records"] == 1
    assert rep["summary"]["mean_goal_response_next"] == 0.7
    assert (tmp_path / "cal.json").exists()
    assert (tmp_path / "cal.csv").exists()


def test_carrier_patch_audit(tmp_path: Path):
    patches = tmp_path / "patches.jsonl"
    responses = tmp_path / "responses.jsonl"
    write_jsonl(patches, [{"action_id": "a1", "carrier_atom": "missing_simp_lemma", "mean_delta": 0.3, "count": 1, "safe_direction": True}])
    write_jsonl(responses, [{
        "action": {"action_id": "a1", "tactic": "simp"},
        "carrier_delta": {"missing_simp_lemma": 0.25},
        "audit_status": "success",
    }])
    rep = audit_carrier_incidence_patches(patches, responses, out_report=tmp_path / "rep.json", out_patches=tmp_path / "accepted.jsonl")
    assert rep["n_accepted"] == 1
    rows = read_jsonl(tmp_path / "accepted.jsonl")
    assert rows[0]["accepted_by_patch_audit"] is True
