from pathlib import Path

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.contextual_congruence import generate_contextual_candidates, contextual_congruence_from_files


def test_contextual_candidates_and_congruence(tmp_path: Path):
    actions = [
        {"action_id": "simp_a", "tactic": "simp", "tactic_class": "simp", "carrier_tags": ["simp"], "cost_estimate": 1.0},
        {"action_id": "simp_b", "tactic": "simp_all", "tactic_class": "simp", "carrier_tags": ["simp"], "cost_estimate": 1.0},
        {"action_id": "omega", "tactic": "omega", "tactic_class": "arith", "carrier_tags": ["arith"], "cost_estimate": 1.0},
    ]
    actions_p = tmp_path / "actions.jsonl"
    write_jsonl(actions_p, actions)
    ctx_p = tmp_path / "ctx_actions.jsonl"
    rows, summary = generate_contextual_candidates(actions_p, ctx_p, max_left=2, max_right=2, max_core=3)
    assert rows
    assert summary["n_actions"] == len(rows)

    resp_rows = []
    for row in rows:
        base = row["metadata"]["core_action_id"]
        if base in {"simp_a", "simp_b"}:
            response = {"goal.eq": 1.0, "carrier.simp": 0.2}
        else:
            response = {"goal.eq": -0.1, "carrier.simp": 0.0, "goal.arith": 1.0}
        resp_rows.append({
            "state_id": "s0",
            "action_id": row["action_id"],
            "audit_status": "success",
            "response": response,
            "response_flat": list(response.values()),
            "response_keys": list(response.keys()),
            "carrier_delta": {"simp": response.get("carrier.simp", 0.0)},
            "action": row,
        })
    resp_p = tmp_path / "responses.jsonl"
    write_jsonl(resp_p, resp_rows)
    out = tmp_path / "ctx_cong"
    rep = contextual_congruence_from_files(resp_p, out, actions_path=ctx_p, cosine_threshold=0.98)
    assert rep["classes"]["n_classes"] >= 2
    classes = read_jsonl(out / "response_congruence_classes.jsonl")
    simp_class = [c for c in classes if {"simp_a", "simp_b"}.issubset(set(c["member_action_ids"]))]
    assert simp_class, classes
    assert (out / "response_congruence_representatives.jsonl").exists()
