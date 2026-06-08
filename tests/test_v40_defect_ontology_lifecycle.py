from pathlib import Path
import json

from lean_rgc.schemas import write_jsonl
from lean_rgc.defect_ontology_lifecycle import run_defect_ontology_lifecycle
from lean_rgc.cli import main


def test_defect_ontology_lifecycle_validates_and_deprecates(tmp_path: Path):
    rec = tmp_path / "defect_ontology_rows.jsonl"
    rows = [
        {
            "candidate_atom_id": "qgen_goal_eq",
            "candidate_source": "qgen",
            "relation": "merge",
            "nearest_atom_id": "eq_goal",
            "similarity": 0.88,
            "evidence": {"candidate": {"atom_id": "qgen_goal_eq", "group": "goal.eq", "evidence": {"residual_key": "goal.eq", "support_count": 2}}},
        },
        {
            "candidate_atom_id": "new_tail_atom",
            "candidate_source": "qcoord",
            "relation": "novel",
            "nearest_atom_id": None,
            "similarity": 0.05,
            "evidence": {"candidate": {"atom_id": "new_tail_atom", "group": "search.tail", "description": "new tail", "evidence": {"residual_key": "search.tail", "support_count": 3}}},
        },
    ]
    write_jsonl(rec, rows)
    promo = tmp_path / "poms_promotion_rows.jsonl"
    write_jsonl(promo, [
        {"action_id": "a_new", "residual_key": "search.tail", "parent_nonpaid": True, "dual_certificate": True, "least_repair": True, "promoted_status": "canonical_candidate"},
        {"action_id": "a_eq", "residual_key": "goal.eq", "parent_nonpaid": True, "dual_certificate": True, "least_repair": False, "promoted_status": "forced_candidate"},
    ])
    val = tmp_path / "validation_rows.jsonl"
    write_jsonl(val, [{"coordinate_id": "search.tail", "validated": True, "validation_score": 1.0}])
    out = tmp_path / "life"
    res = run_defect_ontology_lifecycle(reconciliation_rows=rec, promotion_rows=[promo], validation_rows=[val], out_dir=out)
    assert Path(res["files"]["rows"]).exists()
    life = [json.loads(x) for x in (out / "defect_ontology_lifecycle_rows.jsonl").read_text().splitlines() if x.strip()]
    by = {r["atom_id"]: r for r in life}
    assert by["qgen_goal_eq"]["lifecycle_status"].startswith("merge")
    assert by["qgen_goal_eq"]["evidence"]["deprecated_candidate_alias"] is True
    assert by["new_tail_atom"]["lifecycle_status"] == "validated_novel_atom"
    reg = json.loads((out / "defect_registry_lifecycle.json").read_text())
    assert any(a["atom_id"] == "new_tail_atom" for a in reg["atoms"])


def test_defect_ontology_lifecycle_cli(tmp_path: Path):
    rec = tmp_path / "rows.jsonl"
    write_jsonl(rec, [{"candidate_atom_id": "foo_atom", "candidate_source": "qgen", "relation": "novel", "similarity": 0.0, "evidence": {"candidate": {"atom_id": "foo_atom", "group": "foo"}}}])
    out = tmp_path / "out"
    code = main(["defect-ontology-lifecycle", "--reconciliation-rows", str(rec), "--out", str(out)])
    assert code == 0
    assert (out / "defect_ontology_lifecycle_report.json").exists()
