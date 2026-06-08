from pathlib import Path
from lean_rgc.schemas import LeanTask, write_jsonl, read_jsonl
from lean_rgc.premise_index import build_premise_index, PremiseIndex, premise_actions_from_hits
from lean_rgc.defect_promotion import promote_defects
from lean_rgc.defect_registry import seed_defect_registry


def test_premise_index_roundtrip(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    write_jsonl(tasks, [
        LeanTask(task_id="foo_eq", imports=[], statement="∀ n : Nat, n = n").to_dict(),
        LeanTask(task_id="and_comm", imports=[], statement="∀ p q : Prop, p ∧ q → q ∧ p").to_dict(),
    ])
    out = tmp_path / "premise_index.json"
    idx = build_premise_index(tasks=tasks, actions=None, out=out)
    assert len(idx.docs) == 2
    hits = PremiseIndex.load(out).search("Nat equality n = n", k=2)
    assert hits
    acts = premise_actions_from_hits(hits)
    assert acts
    assert any("apply" in a["tactic"] or "rw" in a["tactic"] or "simp" in a["tactic"] for a in acts)


def test_defect_promotion(tmp_path: Path):
    reg = seed_defect_registry()
    reg_path = tmp_path / "reg.json"
    reg.save(reg_path)
    scores = tmp_path / "scores.jsonl"
    write_jsonl(scores, [{
        "atom_id": "unintroduced_forall",
        "support": 3,
        "response_contrast": 0.5,
        "intervention_success": 1.0,
        "coker_reduction_proxy": 0.2,
        "promotion_score": 1.4,
    }])
    out_reg = tmp_path / "promoted.json"
    out_report = tmp_path / "report.jsonl"
    new_reg, recs = promote_defects(reg_path, scores_path=scores, out_registry=out_reg, out_report=out_report, min_support=1, min_response_contrast=0.0, min_intervention_success=0.5, min_coker_reduction=0.0)
    assert out_reg.exists()
    assert out_report.exists()
    atoms = {a.atom_id: a for a in new_reg.atoms}
    assert atoms["unintroduced_forall"].status == "active"
    assert any(r.promoted for r in recs if r.atom_id == "unintroduced_forall")
