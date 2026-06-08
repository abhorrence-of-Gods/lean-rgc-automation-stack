from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from lean_rgc.defect_ontology import reconcile_defect_ontology, atom_similarity
from lean_rgc.defect_registry import seed_defect_registry

def test_defect_ontology_reconcile_shadow_and_novel(tmp_path: Path):
    cand = tmp_path / "candidate_atoms.jsonl"
    rows = [
        {
            "atom_id": "qgen_residual_goal_eq",
            "group": "goal",
            "detector": "qgen_coker_residual",
            "description": "eq goal residual",
            "evidence": {"source": "qgen", "residual_key": "goal.eq"},
        },
        {
            "atom_id": "brand_new_obstruction_alpha",
            "group": "new_group",
            "detector": "new_detector",
            "description": "brand new obstruction alpha beta",
            "evidence": {"source": "unit_test"},
        },
    ]
    cand.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "ontology"
    rep = reconcile_defect_ontology(candidate_atom_paths=[cand], out_dir=out)
    assert rep["report"]["n_candidate_atoms"] == 2
    out_rows = [json.loads(x) for x in (out / "defect_ontology_rows.jsonl").read_text().splitlines() if x]
    by_id = {r["candidate_atom_id"]: r for r in out_rows}
    assert by_id["qgen_residual_goal_eq"]["nearest_atom_id"] == "eq_reflexive_goal"
    assert by_id["qgen_residual_goal_eq"]["relation"] in {"shadow", "merge", "open"}
    assert by_id["brand_new_obstruction_alpha"]["relation"] == "novel"
    reg = json.loads((out / "defect_registry_reconciled.json").read_text())
    assert "atoms" in reg


def test_defect_ontology_cli_discovers_run_dir(tmp_path: Path):
    qdir = tmp_path / "run" / "qgen"
    qdir.mkdir(parents=True)
    (qdir / "qgen_defect_atoms.jsonl").write_text(json.dumps({
        "atom_id": "qgen_residual_goal_eq",
        "group": "goal",
        "detector": "qgen_coker_residual",
        "evidence": {"source": "qgen", "residual_key": "goal.eq"},
    }) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    res = subprocess.run([sys.executable, "-m", "lean_rgc.cli", "defect-ontology-reconcile", "--run-dir", str(tmp_path / "run"), "--out", str(out)], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert (out / "defect_ontology_report.json").exists()
    assert (out / "defect_ontology_rows.jsonl").exists()


def test_atom_similarity_alias_boost():
    seed = seed_defect_registry()
    eq_atom = next(a.to_dict() for a in seed.atoms if a.atom_id == "eq_reflexive_goal")
    cand = {"atom_id": "qgen_residual_goal_eq", "group": "goal", "evidence": {"residual_key": "goal.eq"}}
    sim = atom_similarity(cand, eq_atom)
    assert sim["similarity"] > 0.3
    assert "eq" in sim["shared_tokens"]
