from pathlib import Path
from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.ir_candidates import ir_candidates_file
from lean_rgc.multicarrier import build_carrier_matrix_from_responses, annotate_actions_with_carrier_matrix, multi_carrier_report


def test_ir_candidates_from_structured_ir(tmp_path):
    ir = tmp_path / "ir.jsonl"
    write_jsonl(ir, [{
        "state_id": "s", "task_id": "t", "goals": [{
            "target": "∀ n : Nat, n = n", "target_head": "forall",
            "shape": {"has_forall": True, "target_is_eq": True, "has_arith": True},
            "carrier_atoms": ["unintroduced_forall", "eq_reflexive_goal", "nat_arith_goal"],
            "hypotheses": []
        }]
    }])
    out = tmp_path / "acts.jsonl"
    rows = ir_candidates_file(ir, out, max_candidates=20)
    tactics = [r["tactic"] for r in rows]
    assert any("intros" in t and "rfl" in t for t in tactics)
    assert any(r.get("task_id") == "t" for r in rows)


def test_multicarrier_matrix_and_safe_actions(tmp_path):
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, [
        {"action_id": "a", "carrier_delta": {"missing_intro": 1.0, "missing_simp": -0.2}},
        {"action_id": "a", "carrier_delta": {"missing_intro": 0.8, "missing_simp": -0.1}},
        {"action_id": "b", "carrier_delta": {"missing_intro": -0.5, "missing_simp": 1.0}},
    ])
    cm_path = tmp_path / "cm.json"
    cm = build_carrier_matrix_from_responses(responses, cm_path, shrink=0.0)
    assert set(cm.action_ids) == {"a", "b"}
    actions = tmp_path / "actions.jsonl"
    write_jsonl(actions, [
        {"action_id": "a", "tactic": "intros", "tactic_class": "intro", "carrier_tags": ["intro"]},
        {"action_id": "b", "tactic": "simp", "tactic_class": "simp", "carrier_tags": ["simp"]},
    ])
    safe = tmp_path / "safe.jsonl"
    rep = annotate_actions_with_carrier_matrix(actions, cm_path, safe, budget=0.25, keep_unsafe=False)
    rows = read_jsonl(safe)
    assert rep["n_out"] >= 1
    assert all(r["metadata"]["carrier_matrix"]["safe"] for r in rows)
    report = multi_carrier_report(cm_path)
    assert report["n_atoms"] == 2
