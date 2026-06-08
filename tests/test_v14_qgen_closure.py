from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.multicarrier import build_carrier_matrix_from_responses, merge_carrier_incidence_patches
from lean_rgc.schemas import read_jsonl, write_jsonl


def test_carrier_matrix_merge_qgen_patches(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, [
        {"action_id": "a", "carrier_delta": {"k": 0.2}, "response_flat": [0.1], "defect_before": {"flat": [1.0]}},
    ])
    base = tmp_path / "carrier.json"
    cm = build_carrier_matrix_from_responses(responses, base)
    assert "k" in cm.atoms
    patches = tmp_path / "patches.jsonl"
    write_jsonl(patches, [
        {"action_id": "b", "carrier_atom": "k", "mean_delta": 0.7, "count": 2, "safe_direction": True},
        {"action_id": "b", "carrier_atom": "new_k", "mean_delta": -0.3, "count": 1, "safe_direction": False},
    ])
    out = tmp_path / "merged.json"
    merged = merge_carrier_incidence_patches(base, patches, out, patch_weight=1.0)
    assert out.exists()
    assert "b" in merged.action_ids
    assert "new_k" in merged.atoms
    arr = merged.as_array()
    assert arr[merged.atoms.index("k"), merged.action_ids.index("b")] > 0
    assert arr[merged.atoms.index("new_k"), merged.action_ids.index("b")] < 0


def test_pipeline_qgen_registry_and_carrier_patch_loop(tmp_path: Path):
    out = tmp_path / "run"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--import-mode", "core",
        "--qgen",
        "--qgen-margin-threshold", "-10",
        "--qgen-registry-candidates",
        "--audit-qgen-registry-candidates",
        "--qgen-registry-accept-coker",
        "--carrier-matrix",
        "--carrier-matrix-merge-qgen",
        "--carrier-matrix-keep-unsafe",
    ])
    assert rc == 0
    assert (out / "qgen" / "qgen_defect_registry.json").exists()
    assert (out / "qgen_registry_candidates.jsonl").exists()
    assert (out / "qgen_registry_audit" / "responses.jsonl").exists()
    assert (out / "qgen_registry_acceptance_report.json").exists()
    assert (out / "carrier_matrix_qgen.json").exists()
    assert (out / "qgen_carrier_patch_report.json").exists()
    # In dry-run this may be empty if the registry chart yields no state matches, but the closed-loop artifacts must exist.
    assert isinstance(read_jsonl(out / "qgen_registry_candidates.jsonl"), list)
