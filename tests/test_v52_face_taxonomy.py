from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.face_taxonomy import build_dual_face_taxonomy
from lean_rgc.schemas import read_jsonl, write_jsonl


def _write_taxonomy_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
                "fingerprint": {
                    "ctx:eq|pre:__id__|post:ctx_rfl::resp::goal.eq": 1.0,
                    "ctx:eq|pre:__id__|post:ctx_rfl::carrier::hidden_obligations": 0.0,
                },
                "domain_support": ["ctx:eq|pre:__id__|post:ctx_rfl"],
                "status_counts": {"success": 3},
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
                "fingerprint": {
                    "ctx:eq|pre:__id__|post:ctx_rfl::resp::goal.eq": 0.9,
                    "ctx:eq|pre:__id__|post:ctx_rfl::carrier::hidden_obligations": 0.0,
                },
                "domain_support": ["ctx:eq|pre:__id__|post:ctx_rfl"],
                "status_counts": {"success": 2},
                "response_summary": {"goal.eq": 0.9},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 1.2},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_simp",
                "premise_id": "simp",
                "use_mode": "simp",
                "fingerprint": {
                    "ctx:simp|pre:ctx_intro|post:ctx_simp::resp::goal.simp": 1.1,
                },
                "domain_support": ["ctx:simp|pre:ctx_intro|post:ctx_simp"],
                "status_counts": {"partial": 1},
                "response_summary": {"goal.simp": 1.1},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 2.0},
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
            {"premise_class_id": "q_simp_bad", "member_premise_use_ids": ["u_simp", "u_bad"]},
        ],
    )
    write_jsonl(
        validation,
        [
            {"premise_class_id": "q_rfl", "validation_status": "heldout_validated_premise_class"},
            {"premise_class_id": "q_simp_bad", "validation_status": "carrier_unsafe_mixed_class"},
        ],
    )
    write_jsonl(
        faces,
        [
            {"face_id": "face_rfl", "source_class_id": "q_rfl"},
            {"face_id": "face_simp_bad", "source_class_id": "q_simp_bad"},
        ],
    )
    return fingerprints, classes, validation, faces


def test_dual_face_taxonomy_builds_concepts_and_retrieval_gate(tmp_path: Path):
    fingerprints, classes, validation, faces = _write_taxonomy_inputs(tmp_path)
    out = tmp_path / "taxonomy"
    report = build_dual_face_taxonomy(
        fingerprints_path=fingerprints,
        classes_path=classes,
        validation_rows_path=validation,
        repair_faces_path=faces,
        out_dir=out,
        min_support=1,
        min_retrieval_support=2,
    )

    assert report["n_rows"] == 4
    assert report["n_concepts"] > 0
    assert report["n_taxonomy_faces"] > 0
    assert (out / "face_concept_lattice.jsonl").exists()
    assert (out / "row_face_memberships.jsonl").exists()
    assert (out / "taxonomy_name_suggestions.jsonl").exists()

    allowed = read_jsonl(out / "retrieval_allowed_faces.jsonl")
    assert allowed
    assert any({"u_rfl", "u_exact_rfl"} <= set((row["minimal_support"] or {}).get("rows") or []) for row in allowed)
    assert all((row["status"] or {}).get("carrier_safe") is True for row in allowed)

    blocked = [
        row
        for row in read_jsonl(out / "dual_face_taxonomy.jsonl")
        if "u_bad" in ((row.get("minimal_support") or {}).get("rows") or [])
    ]
    assert blocked
    assert any("carrier" in " ".join((row.get("status") or {}).get("retrieval_blockers") or []) for row in blocked)


def test_face_taxonomy_cli_subcommand(tmp_path: Path):
    fingerprints, classes, validation, faces = _write_taxonomy_inputs(tmp_path)
    out = tmp_path / "taxonomy_cli"
    assert (
        cli_main(
            [
                "face-taxonomy",
                "--fingerprints",
                str(fingerprints),
                "--classes",
                str(classes),
                "--validation",
                str(validation),
                "--repair-faces",
                str(faces),
                "--out",
                str(out),
                "--min-retrieval-support",
                "2",
            ]
        )
        == 0
    )
    assert read_jsonl(out / "dual_face_taxonomy.jsonl")
    assert read_jsonl(out / "retrieval_allowed_faces.jsonl")
