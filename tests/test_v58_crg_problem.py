from pathlib import Path

from lean_rgc.crg_problem import build_crg_problems
from lean_rgc.schemas import read_jsonl, write_jsonl


def test_crg_problem_from_repair_face_and_tower_dual(tmp_path: Path):
    faces = tmp_path / "repair_faces.jsonl"
    duals = tmp_path / "tower_dual_components.jsonl"
    completion = tmp_path / "response_completion.json"
    out = tmp_path / "crg_problems.jsonl"

    write_jsonl(
        faces,
        [
            {
                "face_id": "face_eq",
                "positive_response_face": {"goal.eq": 1.0},
                "carrier_face": {"missing_simp": -0.5},
            }
        ],
    )
    write_jsonl(
        duals,
        [
            {
                "dual_component_id": "lambda_eq",
                "exposed_face_id": "face_eq",
                "normal_vector": {
                    "response_weights": {"goal.eq": 1.0},
                    "carrier_weights": {"missing_simp": 0.25},
                },
            }
        ],
    )
    completion.write_text(
        '{"probe_family_id":"completion_test","topology":"weighted_projective_response","response_keys":["goal.eq","carrier.missing_simp"],"weights":{"goal.eq":1.0,"carrier.missing_simp":1.0},"paid_cone_keys":[]}',
        encoding="utf-8",
    )

    summary = build_crg_problems(
        out=out,
        repair_faces_path=faces,
        tower_dual_components_path=duals,
        response_completion_path=completion,
    )
    rows = read_jsonl(out)

    assert summary["n_problems"] == 1
    problem = rows[0]
    assert problem["schema_version"] == "lean-rgc-crg-problem-v58.0"
    assert problem["parent_face_id"] == "face_eq"
    assert problem["obstruction_id"] == "lambda_eq"
    assert problem["objective"]["lambda_normal"]["goal.eq"] == 1.0
    assert problem["objective"]["lambda_normal"]["carrier.missing_simp"] == 0.25
    assert problem["canonical_status"] == "optimization_problem_canonical_candidate_not_generator"


def test_crg_problem_empty_inputs_emit_empty_ledger(tmp_path: Path):
    out = tmp_path / "crg_problems.jsonl"

    summary = build_crg_problems(out=out)

    assert summary["n_problems"] == 0
    assert read_jsonl(out) == []
