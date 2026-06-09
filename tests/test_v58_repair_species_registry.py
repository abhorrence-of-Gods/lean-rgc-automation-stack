from pathlib import Path

from lean_rgc.crg_registry import build_repair_species_registry, load_repair_atoms
from lean_rgc.relaxed_species import DEFAULT_RELAXED_SPECIES, write_relaxed_species_registry
from lean_rgc.schemas import read_jsonl, write_jsonl


def test_repair_species_registry_collects_relaxed_atoms(tmp_path: Path):
    actions = tmp_path / "actions.jsonl"
    action_geometry = tmp_path / "action_geometry.jsonl"
    premise_registry = tmp_path / "premise_registry.jsonl"
    quotient = tmp_path / "quotient_coordinates.jsonl"
    carrier = tmp_path / "carrier_quotient.jsonl"
    tower = tmp_path / "tower_retrieval.jsonl"
    faces = tmp_path / "repair_faces.jsonl"
    out = tmp_path / "repair_species_registry.jsonl"

    write_jsonl(actions, [{"action_id": "rfl", "tactic": "rfl", "cost_estimate": 0.1}])
    write_jsonl(
        action_geometry,
        [
            {
                "action_id": "simp",
                "tactic": "simp",
                "response_keys": ["goal.eq"],
                "response_embedding": [0.8],
                "cost_estimate": 0.3,
            }
        ],
    )
    write_jsonl(
        premise_registry,
        [
            {
                "premise_id": "Nat.zero_eq",
                "tactic": "simp [Nat.zero_eq]",
                "response_embedding": {"goal.eq": 0.6},
            }
        ],
    )
    write_jsonl(quotient, [{"coordinate_id": "q0", "normal": {"goal.eq": 1.0}, "mass": 0.4}])
    write_jsonl(carrier, [{"carrier_patch_id": "c0", "carrier_embedding": {"carrier.missing": -1.0}}])
    write_jsonl(tower, [{"retrieval_id": "tw0", "tactic": "simp", "response_embedding": {"goal.eq": 0.2}}])
    write_jsonl(faces, [{"face_id": "face0", "positive_response_face": {"goal.eq": 1.0}}])

    summary = build_repair_species_registry(
        out=out,
        actions_path=actions,
        action_geometry_path=action_geometry,
        premise_registry_path=premise_registry,
        quotient_coordinates_path=quotient,
        carrier_quotient_path=carrier,
        tower_retrieval_path=tower,
        repair_faces_path=faces,
    )
    rows = read_jsonl(out)
    atoms = load_repair_atoms(out)

    assert summary["n_repair_atoms"] >= 7
    expected_species = {row["species_id"] for row in DEFAULT_RELAXED_SPECIES}
    assert {row["species_id"] for row in rows if row.get("row_kind") == "species"} >= expected_species
    assert {atom["repair_species"] for atom in atoms} >= {
        "action_distribution",
        "premise_distribution",
        "quotient_coordinate_cone",
        "carrier_patch_measure",
        "context_portfolio",
    }
    assert all(atom["canonical_status"] == "repair_witness_not_canonical" for atom in atoms)


def test_relaxed_species_registry_has_fixed_species(tmp_path: Path):
    out = tmp_path / "species.jsonl"

    summary = write_relaxed_species_registry(out)

    rows = read_jsonl(out)
    assert summary["n_species"] == len(DEFAULT_RELAXED_SPECIES)
    assert {row["species_id"] for row in rows} == {row["species_id"] for row in DEFAULT_RELAXED_SPECIES}
