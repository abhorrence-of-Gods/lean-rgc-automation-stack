from pathlib import Path

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.carrier_promotion import write_accepted_carrier_actions


def test_carrier_promotion_writes_actions(tmp_path: Path):
    accepted = tmp_path / "accepted.jsonl"
    out = tmp_path / "actions.jsonl"
    rep = tmp_path / "rep.json"
    write_jsonl(accepted, [
        {
            "task_id": "t1",
            "context_kind": "carrier_exposure",
            "action_id": "a0",
            "tactic": "intros\nrfl",
            "accepted": True,
            "coker_margin_proxy": 0.7,
            "carrier_delta_l1": 1.0,
            "carrier_residual_l1_before": 1.0,
            "carrier_residual_l1_after": 0.0,
            "cost": 0.2,
            "status": "success",
            "residual_atoms": ["unintroduced_forall"],
        },
        {
            "task_id": "t1",
            "context_kind": "carrier_exposure",
            "action_id": "a1",
            "tactic": "intros\nsimp",
            "accepted": False,
            "coker_margin_proxy": -0.1,
            "cost": 0.2,
            "status": "fail",
            "residual_atoms": ["unintroduced_forall"],
        },
    ])
    summary = write_accepted_carrier_actions(accepted, out, report_out=rep)
    rows = read_jsonl(out)
    assert summary["n_actions"] == 1
    assert len(rows) == 1
    assert rows[0]["task_id"] == "t1"
    assert "unintroduced_forall" in rows[0]["carrier_tags"]
    assert rows[0]["metadata"]["carrier_acceptance_margin"] == 0.7
