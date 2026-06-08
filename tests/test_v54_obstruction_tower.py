from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.face_taxonomy import build_dual_face_taxonomy
from lean_rgc.obstruction_tower import build_canonical_obstruction_tower
from lean_rgc.schemas import read_jsonl, write_jsonl


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    fingerprints = tmp_path / "fingerprints.jsonl"
    classes = tmp_path / "classes.jsonl"
    validation = tmp_path / "validation.jsonl"
    faces = tmp_path / "repair_faces.jsonl"
    write_jsonl(
        fingerprints,
        [
            {
                "premise_use_id": "u_rfl",
                "premise_id": "rfl",
                "use_mode": "exact",
                "fingerprint": {"ctx:eq|pre:__id__|post:ctx_rfl::resp::goal.eq": 1.0},
                "domain_support": ["ctx:eq|pre:__id__|post:ctx_rfl"],
                "status_counts": {"success": 2},
                "response_summary": {"goal.eq": 1.0},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 1.0},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_exact_rfl",
                "premise_id": "rfl",
                "use_mode": "exact",
                "fingerprint": {"ctx:eq|pre:__id__|post:ctx_rfl::resp::goal.eq": 0.9},
                "domain_support": ["ctx:eq|pre:__id__|post:ctx_rfl"],
                "status_counts": {"success": 2},
                "response_summary": {"goal.eq": 0.9},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 1.1},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_bad",
                "premise_id": "bad",
                "use_mode": "macro",
                "fingerprint": {
                    "ctx:simp|pre:ctx_intro|post:ctx_simp::resp::goal.simp": 1.0,
                    "ctx:simp|pre:ctx_intro|post:ctx_simp::carrier::hidden_obligations": -1.0,
                },
                "domain_support": ["ctx:simp|pre:ctx_intro|post:ctx_simp"],
                "status_counts": {"success": 1},
                "response_summary": {"goal.simp": 1.0},
                "carrier_summary": {"hidden_obligations": -1.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 3.0},
                "audit_summary": {"unsafe": 1.0},
            },
        ],
    )
    write_jsonl(
        classes,
        [
            {"premise_class_id": "q_rfl", "member_premise_use_ids": ["u_rfl", "u_exact_rfl"]},
            {"premise_class_id": "q_bad", "member_premise_use_ids": ["u_bad"]},
        ],
    )
    write_jsonl(
        validation,
        [
            {"premise_class_id": "q_rfl", "validation_status": "heldout_validated_premise_class"},
            {"premise_class_id": "q_bad", "validation_status": "carrier_unsafe_mixed_class"},
        ],
    )
    write_jsonl(
        faces,
        [
            {"face_id": "face_rfl", "source_class_id": "q_rfl"},
            {"face_id": "face_bad", "source_class_id": "q_bad"},
        ],
    )
    return fingerprints, classes, validation, faces


def test_obstruction_tower_builds_artifacts_and_next_actions(tmp_path: Path):
    fingerprints, classes, validation, faces = _write_inputs(tmp_path)
    taxonomy_dir = tmp_path / "taxonomy"
    build_dual_face_taxonomy(
        fingerprints_path=fingerprints,
        classes_path=classes,
        validation_rows_path=validation,
        repair_faces_path=faces,
        out_dir=taxonomy_dir,
        min_retrieval_support=2,
    )
    out = tmp_path / "tower"
    summary = build_canonical_obstruction_tower(
        out_dir=out,
        fingerprints_path=fingerprints,
        taxonomy_dir=taxonomy_dir,
        repair_faces_path=faces,
        validation_rows_path=validation,
        min_retrieval_support=2,
    )
    assert summary["n_objects"] >= 3
    assert summary["n_faces"] > 0
    assert summary["n_dual_components"] == summary["n_faces"]
    assert summary["n_transcripts"] >= 3
    assert read_jsonl(out / "tower_faces.jsonl")
    assert read_jsonl(out / "tower_dual_components.jsonl")
    assert read_jsonl(out / "tower_boundaries.jsonl")
    assert read_jsonl(out / "tower_promotions.jsonl")
    next_actions = read_jsonl(out / "tower_next_actions.jsonl")
    assert next_actions
    assert any(row["action_kind"] == "hard_split_face" for row in next_actions)
    retrieval = read_jsonl(out / "tower_retrieval_candidates.jsonl")
    assert retrieval


def test_obstruction_tower_cli(tmp_path: Path):
    fingerprints, classes, validation, faces = _write_inputs(tmp_path)
    taxonomy_dir = tmp_path / "taxonomy"
    build_dual_face_taxonomy(
        fingerprints_path=fingerprints,
        classes_path=classes,
        validation_rows_path=validation,
        repair_faces_path=faces,
        out_dir=taxonomy_dir,
        min_retrieval_support=2,
    )
    out = tmp_path / "tower_cli"
    assert (
        cli_main(
            [
                "obstruction-tower",
                "--out",
                str(out),
                "--fingerprints",
                str(fingerprints),
                "--taxonomy-dir",
                str(taxonomy_dir),
                "--repair-faces",
                str(faces),
                "--validation",
                str(validation),
            ]
        )
        == 0
    )
    assert read_jsonl(out / "tower_faces.jsonl")
    assert (out / "tower_summary.json").exists()
