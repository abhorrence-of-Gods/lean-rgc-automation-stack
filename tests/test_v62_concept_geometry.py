from pathlib import Path

from lean_rgc.concept_geometry import build_concept_geometry
from lean_rgc.concept_hardening import decode_concepts_to_repair_atoms
from lean_rgc.concept_search import search_concepts
from lean_rgc.crg_optimizer import optimize_crg_candidates
from lean_rgc.schemas import read_jsonl, write_jsonl


def test_concept_geometry_search_decode_connects_to_crg(tmp_path: Path):
    taxonomy = tmp_path / "dual_face_taxonomy.jsonl"
    selected = tmp_path / "selected_features.jsonl"
    concept_dir = tmp_path / "concept_geometry"
    problems = tmp_path / "crg_problems.jsonl"
    candidates = tmp_path / "relaxed_candidates.jsonl"

    write_jsonl(
        taxonomy,
        [
            {
                "concept_id": "concept_eq",
                "taxonomy_face_id": "face_eq",
                "dual_source": "row_coker",
                "positive_face": {"response_basis": ["goal.eq"]},
                "status": {"heldout_validated": True, "retrieval_allowed": True},
            }
        ],
    )
    write_jsonl(selected, [{"feature_id": "simp_feature", "description_cost": 0.5, "unsafe_weight": 0.0}])
    write_jsonl(
        problems,
        [
            {
                "problem_id": "crg_concept",
                "parent_face_id": "face_eq",
                "obstruction_id": "lambda_eq",
                "objective": {"lambda_normal": {"goal.eq": 1.0}},
                "budget": {
                    "cost_max": 4.0,
                    "audit_risk_max": 0.2,
                    "source_risk_max": 0.2,
                    "ghost_risk_max": 0.2,
                    "hardening_cost_max": 8.0,
                },
            }
        ],
    )

    gsummary = build_concept_geometry(out_dir=concept_dir, taxonomy_path=taxonomy, selected_features_path=selected)
    ssummary = search_concepts(
        concept_points_path=concept_dir / "concept_points.jsonl",
        concept_edges_path=concept_dir / "concept_edges.jsonl",
        problems_path=problems,
        out=concept_dir / "concept_search_rows.jsonl",
        mode="operation-graph expansion",
    )
    dsummary = decode_concepts_to_repair_atoms(
        concept_search_path=concept_dir / "concept_search_rows.jsonl",
        concept_points_path=concept_dir / "concept_points.jsonl",
        out=concept_dir / "concept_decoded_repair_atoms.jsonl",
    )
    optimize_crg_candidates(
        problems_path=problems,
        registry_path=concept_dir / "concept_decoded_repair_atoms.jsonl",
        out=candidates,
        optimizer="linear_support",
    )

    points = read_jsonl(concept_dir / "concept_points.jsonl")
    search_rows = read_jsonl(concept_dir / "concept_search_rows.jsonl")
    atoms = read_jsonl(concept_dir / "concept_decoded_repair_atoms.jsonl")
    relaxed = read_jsonl(candidates)

    assert gsummary["n_points"] == 2
    assert gsummary["n_edges"] == 1
    assert ssummary["n_rows"] >= 2
    assert dsummary["n_atoms"] >= 1
    assert any(point["canonical_status"] == "concept_chart_not_canonical" for point in points)
    assert search_rows[0]["canonical_status"] == "concept_search_witness_not_canonical"
    assert atoms[0]["repair_species"] == "concept_latent"
    assert atoms[0]["canonical_status"] == "repair_witness_not_canonical"
    assert relaxed[0]["status"] == "relaxed_optimizer_witness"
    assert relaxed[0]["relaxed_object"]["support"][0]["species_id"] == "concept_latent"
