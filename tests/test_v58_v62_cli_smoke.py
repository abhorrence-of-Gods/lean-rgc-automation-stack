from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import read_jsonl, write_jsonl


def test_crg_and_concept_subcommand_smoke(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    actions = tmp_path / "actions.jsonl"
    faces = tmp_path / "repair_faces.jsonl"
    duals = tmp_path / "tower_dual_components.jsonl"
    taxonomy = tmp_path / "taxonomy.jsonl"
    features = tmp_path / "selected_features.jsonl"

    completion = tmp_path / "response_completion.json"
    species = tmp_path / "relaxed_species.jsonl"
    registry = tmp_path / "repair_species_registry.jsonl"
    problems = tmp_path / "crg_problems.jsonl"
    candidates = tmp_path / "relaxed_candidates.jsonl"
    attempts = tmp_path / "hardening_attempts.jsonl"
    hard_actions = tmp_path / "hard_candidates.jsonl"
    audit_rows = tmp_path / "crg_audit_rows.jsonl"
    poms = tmp_path / "crg_poms_evidence.jsonl"
    gap = tmp_path / "hardening_gap_report.json"
    flow = tmp_path / "repair_flow_steps.jsonl"
    concept_dir = tmp_path / "concept_geometry"
    concept_search = tmp_path / "concept_search_rows.jsonl"
    concept_atoms = tmp_path / "concept_atoms.jsonl"

    write_jsonl(responses, [{"response": {"goal.eq": 1.0}, "audit_status": "success"}])
    write_jsonl(actions, [{"action_id": "simp", "tactic": "simp", "cost_estimate": 0.1}])
    write_jsonl(faces, [{"face_id": "face_eq", "positive_response_face": {"goal.eq": 1.0}}])
    write_jsonl(
        duals,
        [
            {
                "dual_component_id": "lambda_eq",
                "exposed_face_id": "face_eq",
                "normal_vector": {"response_weights": {"goal.eq": 1.0}},
            }
        ],
    )
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
    write_jsonl(features, [{"feature_id": "feature_eq"}])

    assert cli_main(["response-completion", "--responses", str(responses), "--out", str(completion)]) == 0
    assert cli_main(["relaxed-species-registry", "--out", str(species)]) == 0
    assert cli_main(["repair-species-registry", "--actions", str(actions), "--out", str(registry)]) == 0
    assert (
        cli_main(
            [
                "crg-build-problems",
                "--repair-faces",
                str(faces),
                "--tower-dual-components",
                str(duals),
                "--response-completion",
                str(completion),
                "--out",
                str(problems),
            ]
        )
        == 0
    )
    assert cli_main(["crg-optimize", "--problems", str(problems), "--registry", str(registry), "--response-completion", str(completion), "--out", str(candidates)]) == 0
    assert cli_main(["crg-harden", "--candidates", str(candidates), "--out-attempts", str(attempts), "--out-actions", str(hard_actions)]) == 0
    assert cli_main(["crg-audit", "--candidates", str(candidates), "--hardening-attempts", str(attempts), "--out", str(audit_rows), "--poms-out", str(poms), "--gap-report-out", str(gap)]) == 0
    assert cli_main(["repair-gradient-flow", "--problems", str(problems), "--registry", str(registry), "--response-completion", str(completion), "--out", str(flow)]) == 0
    assert cli_main(["concept-geometry", "--taxonomy", str(taxonomy), "--selected-features", str(features), "--out", str(concept_dir)]) == 0
    assert cli_main(["concept-search", "--concept-points", str(concept_dir / "concept_points.jsonl"), "--concept-edges", str(concept_dir / "concept_edges.jsonl"), "--problems", str(problems), "--out", str(concept_search), "--mode", "operation-graph expansion"]) == 0
    assert cli_main(["concept-decode", "--concept-search", str(concept_search), "--concept-points", str(concept_dir / "concept_points.jsonl"), "--out", str(concept_atoms)]) == 0

    assert read_jsonl(species)
    assert read_jsonl(registry)
    assert read_jsonl(problems)
    assert read_jsonl(candidates)
    assert read_jsonl(attempts)
    assert read_jsonl(hard_actions)
    assert read_jsonl(audit_rows)
    assert read_jsonl(poms)
    assert gap.exists()
    assert read_jsonl(flow)
    assert read_jsonl(concept_search)
    assert read_jsonl(concept_atoms)
