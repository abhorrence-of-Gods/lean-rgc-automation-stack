from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl
from lean_rgc.poms_promotion import collect_poms_promotion
from lean_rgc.cli import main


def test_poms_promotion_requires_full_certificate(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    rows = [
        {
            "kind": "context_action",
            "action_id": "a1",
            "tactic": "simp",
            "poms_status": "paid_witness",
            "canonical_status": "not_canonical_parent_nonpaid_least_repair_required",
            "action": {"action_id": "a1", "tactic": "simp", "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"]}}},
        },
        {
            "kind": "carrier_incidence_patch",
            "action_id": "a2",
            "carrier_atom": "simp",
            "poms_status": "paid_carrier_patch_witness",
            "canonical_status": "not_canonical_carrier_patch_witness_only",
        },
    ]
    status = run / "poms_status_rows.jsonl"
    write_jsonl(status, rows)
    cert = run / "certs.jsonl"
    write_jsonl(cert, [
        {
            "id": "cert_goal_eq",
            "parent_id": "goal.eq",
            "parent_status": "non_paid",
            "dual_certificate": True,
            "least_repair": True,
            "modal_safety": True,
        }
    ])
    rep = collect_poms_promotion(run, poms_rows=status, evidence=[cert], declare_canonical=False)
    statuses = {r["action_id"]: r["poms_promoted_status"] for r in rep["rows"]}
    assert statuses["a1"] == "canonical_candidate"
    assert statuses["a2"] == "paid_witness"
    rep2 = collect_poms_promotion(run, poms_rows=status, evidence=[cert], declare_canonical=True)
    statuses2 = {r["action_id"]: r["poms_promoted_status"] for r in rep2["rows"]}
    assert statuses2["a1"] == "canonical_observable"


def test_poms_promote_cli(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    status = run / "poms_status_rows.jsonl"
    cert = run / "certs.jsonl"
    out_json = run / "poms_promotion_report.json"
    write_jsonl(status, [{"kind": "context_action", "action_id": "a1", "poms_status": "accepted_witness"}])
    write_jsonl(cert, [{"action_id": "a1", "parent_status": "paid"}])
    rc = main([
        "poms-promote",
        "--run-dir", str(run),
        "--poms-rows", str(status),
        "--evidence", str(cert),
        "--out-json", str(out_json),
    ])
    assert rc == 0
    rep = json.loads(out_json.read_text())
    assert rep["rows"][0]["poms_promoted_status"] == "witness_only_parent_paid"
