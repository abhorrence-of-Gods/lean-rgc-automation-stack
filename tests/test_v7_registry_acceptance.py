import numpy as np
from lean_rgc.registry_acceptance import RegistryCokerAcceptor, summarize_acceptance


def row(state, action, resp, defect, status="success", tactic="tac", cost=1.0):
    return {
        "state_id": state,
        "task_id": state,
        "action_id": action,
        "audit_status": status,
        "response_flat": resp,
        "defect_before": {"flat": defect},
        "carrier_delta": {"unintroduced_forall": 1.0},
        "response": {"goal.num_goals": resp[0]},
        "action": {"action_id": action, "tactic": tactic, "cost_estimate": cost, "metadata": {"generated_by": "test"}},
    }


def test_registry_coker_acceptor_accepts_margin_positive():
    base = [row("s", "base", [0.1, 0.0], [1.0, 0.0], tactic="base")]
    cand = [row("s", "cand", [2.0, 0.0], [1.0, 0.0], tactic="intros\nrfl")]
    acc = RegistryCokerAcceptor(margin_threshold=0.0, cost_weight=0.0, carrier_bonus=0.0).accept(base, cand)
    assert len(acc) == 1
    assert acc[0].accepted
    assert acc[0].margin > 0
    summary = summarize_acceptance(acc).to_dict()
    assert summary["n_accepted"] == 1
