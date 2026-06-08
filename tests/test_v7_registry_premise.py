from lean_rgc.schemas import write_jsonl
from lean_rgc.defect_registry import seed_defect_registry
from lean_rgc.registry_promotion import promote_registry_file
from lean_rgc.premise_index import build_premise_index, PremiseIndex, premise_actions_from_hits
from lean_rgc.ir_defects import ir_defects_file


def test_registry_promotion(tmp_path):
    reg = seed_defect_registry()
    reg_path = tmp_path / "registry.json"
    reg.save(reg_path)
    audits = tmp_path / "audits.jsonl"
    responses = tmp_path / "responses.jsonl"
    row = {
        "state_id": "s", "action_id": "a", "task_id": "t", "target": "∀ n : Nat, n = n",
        "status": "success",
        "action": {"action_id": "a", "tactic": "intros\nrfl", "tactic_class": "exact", "carrier_tags": ["intro", "rfl"], "metadata": {"exposure": {"expected_carrier_delta": {"unintroduced_forall": -1.0}}}},
        "carrier_delta": {"unintroduced_forall": 1.0},
        "response_flat": [1.0, 0.0],
    }
    write_jsonl(audits, [row])
    write_jsonl(responses, [row])
    out = tmp_path / "promoted.json"
    report = tmp_path / "report.json"
    new_reg, rep = promote_registry_file(reg_path, audits, out, responses_path=responses, report_out=report, min_intervention_success=0.1, min_coker_reduction=0.0)
    assert out.exists()
    assert rep.n_validated >= 1
    statuses = {a.atom_id: a.status for a in new_reg.atoms}
    assert statuses.get("unintroduced_forall") == "validated"


def test_premise_index_and_actions(tmp_path):
    tasks = tmp_path / "tasks.jsonl"
    actions = tmp_path / "actions.jsonl"
    write_jsonl(tasks, [{"task_id": "t1", "statement": "theorem add_zero (n : Nat) : n + 0 = n := by", "imports": []}])
    write_jsonl(actions, [{"action_id": "rw_add_zero", "tactic": "rw [Nat.add_zero]", "tactic_class": "rewrite", "carrier_tags": ["rewrite"]}])
    idx_path = tmp_path / "idx.json"
    idx = build_premise_index(tasks=tasks, actions=actions, out=idx_path)
    hits = idx.search("Nat add zero", k=3)
    assert hits
    acts = premise_actions_from_hits(hits)
    assert acts
    loaded = PremiseIndex.load(idx_path)
    assert loaded.search("add_zero")


def test_ir_defects(tmp_path):
    ir = tmp_path / "ir.jsonl"
    out = tmp_path / "defects.jsonl"
    write_jsonl(ir, [{"state_id": "s", "task_id": "t", "goals": [{"target": "n = n", "target_head": "eq", "hypotheses": [], "carrier_atoms": ["eq_reflexive_goal"], "features": {}}], "source": "test"}])
    rows = ir_defects_file(ir, out)
    assert rows
    assert rows[0]["carrier"]["eq_reflexive_goal"] == 1.0
