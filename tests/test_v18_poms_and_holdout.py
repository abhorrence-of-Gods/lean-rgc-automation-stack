from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl
from lean_rgc.carrier_patch_audit import audit_carrier_incidence_patches
from lean_rgc.poms_status import collect_poms_status
from lean_rgc.quality import quality_gates_for_run


def test_carrier_patch_audit_holdout(tmp_path: Path):
    patches = tmp_path / "patches.jsonl"
    responses = tmp_path / "responses.jsonl"
    out_patches = tmp_path / "accepted.jsonl"
    out_report = tmp_path / "report.json"
    write_jsonl(patches, [{"action_id": "a1", "carrier_atom": "easy", "mean_delta": 1.0}])
    rows = []
    # Enough repeated rows that stable hash split almost surely has both train/holdout.
    for i in range(40):
        rows.append({"task_id": f"t{i}", "action_id": "a1", "status": "success", "carrier_delta": {"easy": 1.0}})
    write_jsonl(responses, rows)
    rep = audit_carrier_incidence_patches(
        patches,
        responses,
        out_report=out_report,
        out_patches=out_patches,
        min_count=1,
        min_mean_delta=0.1,
        holdout_fraction=0.5,
        heldout_min_count=1,
        heldout_min_mean_delta=0.1,
        require_heldout=True,
    )
    assert rep["n_accepted"] == 1
    accepted = [json.loads(line) for line in out_patches.read_text().splitlines() if line.strip()]
    assert accepted and accepted[0]["accepted_by_patch_audit"] is True
    assert accepted[0]["holdout_patch_audit_pass"] is True


def test_poms_status_from_iterate_artifacts(tmp_path: Path):
    root = tmp_path / "run"
    r0 = root / "round_00"
    r1 = root / "round_01"
    (r0 / "qgen").mkdir(parents=True)
    (r1 / "audit").mkdir(parents=True)
    action = {"action_id": "a_q", "tactic": "simp", "metadata": {"qgen": {"lineage_id": "lin1", "parent_residual_keys": ["goal.eq"]}}}
    write_jsonl(r0 / "qgen_accepted_actions.jsonl", [action])
    write_jsonl(r0 / "qgen" / "qgen_context_candidates.jsonl", [action, {"action_id": "a_raw", "tactic": "rfl"}])
    write_jsonl(r0 / "qgen_carrier_incidence_audited.jsonl", [{"action_id": "a_q", "carrier_atom": "simp", "accepted_by_patch_audit": True, "holdout_patch_audit_pass": True, "observed_mean_delta": 1.0}])
    write_jsonl(r1 / "audit" / "responses.jsonl", [{"task_id": "t", "action_id": "a_q", "tactic": "simp", "status": "success", "response": {"goal.closed": 1.0}, "carrier_delta": {"simp": 1.0}}])
    # Build realized calibration first.
    from lean_rgc.realized_response import collect_qgen_realized_calibration
    collect_qgen_realized_calibration(root, out_json=root / "qgen_realized_calibration.json")
    rep = collect_poms_status(root, out_json=root / "poms_status_report.json", out_jsonl=root / "poms_status_rows.jsonl")
    statuses = {r["poms_status"] for r in rep["rows"]}
    assert "paid_witness" in statuses
    assert "witness_candidate" in statuses
    assert "paid_carrier_patch_witness" in statuses
    assert rep["summary"]["canonical_status"] == "poms_status_chart_only_no_canonical_promotion"


def test_quality_gates_include_qgen_realized_and_patch(tmp_path: Path):
    rd = tmp_path / "run"
    (rd / "audit").mkdir(parents=True)
    (rd / "qgen_acceptance_lineage.json").write_text(json.dumps({"summary": {"n_accepted_contexts": 1}}))
    (rd / "qgen_realized_calibration.json").write_text(json.dumps({"summary": {"match_rate": 1.0, "success_rate_next": 1.0, "mean_goal_response_next": 0.5}}))
    (rd / "qgen_carrier_patch_audit_report.json").write_text(json.dumps({"accept_rate": 1.0}))
    rep = quality_gates_for_run(
        rd,
        min_audits=0,
        min_registry_accept=0,
        min_qgen_realized_match_rate=0.9,
        min_qgen_realized_success_rate=0.9,
        min_qgen_realized_goal_response=0.0,
        min_qgen_patch_audit_accept_rate=0.9,
    )
    names = {g.name: g.passed for g in rep.gates}
    assert names["qgen_realized_match_rate"] is True
    assert names["qgen_carrier_patch_audit_accept_rate"] is True
