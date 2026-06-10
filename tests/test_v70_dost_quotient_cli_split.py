import argparse
import importlib
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import read_jsonl, write_jsonl


MOVED_COMMANDS = {
    "premise-contextual-generate": ["premise-contextual-generate", "--out", "candidates.jsonl"],
    "premise-contextual-fingerprints": ["premise-contextual-fingerprints", "--responses", "responses.jsonl", "--out", "fingerprints.jsonl"],
    "premise-contextual-mine": ["premise-contextual-mine", "--fingerprints", "fingerprints.jsonl", "--out", "quotient"],
    "premise-contextual-validate": ["premise-contextual-validate", "--fingerprints", "fingerprints.jsonl", "--classes", "classes.jsonl", "--out-rows", "rows.jsonl", "--out-report", "report.json"],
    "premise-quotient-retrieve": ["premise-quotient-retrieve", "--classes", "classes.jsonl", "--out", "retrieved.jsonl"],
    "premise-use-rows": ["premise-use-rows", "--actions", "actions.jsonl", "--out", "rows.jsonl"],
    "separator-contexts": ["separator-contexts", "--out", "contexts.jsonl"],
    "bivariate-contextual-generate": ["bivariate-contextual-generate", "--premise-rows", "rows.jsonl", "--contexts", "contexts.jsonl", "--out", "candidates.jsonl"],
    "bivariate-contextual-schedule": ["bivariate-contextual-schedule", "--candidates", "candidates.jsonl", "--out", "schedule.jsonl"],
    "repair-face-ledger": ["repair-face-ledger", "--fingerprints", "fingerprints.jsonl", "--classes", "classes.jsonl", "--out", "faces.jsonl"],
    "face-taxonomy": ["face-taxonomy", "--fingerprints", "fingerprints.jsonl", "--out", "taxonomy"],
    "obstruction-tower": ["obstruction-tower", "--out", "tower"],
    "response-completion": ["response-completion", "--out", "completion.json"],
    "contextual-candidates": ["contextual-candidates", "--actions", "actions.jsonl", "--out", "candidates.jsonl"],
    "contextual-congruence": ["contextual-congruence", "--responses", "responses.jsonl", "--out", "classes"],
    "contextual-response-congruence": ["contextual-response-congruence", "--responses", "responses.jsonl", "--out", "classes"],
    "response-quotient-registry": ["response-quotient-registry", "--out", "registry"],
    "response-quotient-project-actions": ["response-quotient-project-actions", "--actions", "actions.jsonl", "--registry", "registry.jsonl", "--out", "projected.jsonl"],
}


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def _write_face_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
                "cost_summary": {"elapsed_ms": 1.0},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_bad",
                "premise_id": "bad",
                "use_mode": "macro",
                "fingerprint": {"ctx:simp|pre:ctx_intro|post:ctx_simp::resp::goal.simp": 1.0},
                "domain_support": ["ctx:simp|pre:ctx_intro|post:ctx_simp"],
                "status_counts": {"success": 1},
                "response_summary": {"goal.simp": 1.0},
                "carrier_summary": {"hidden_obligations": -1.0},
                "cost_summary": {"elapsed_ms": 3.0},
                "audit_summary": {"unsafe": 1.0},
            },
        ],
    )
    write_jsonl(classes, [{"premise_class_id": "q_rfl", "member_premise_use_ids": ["u_rfl"]}, {"premise_class_id": "q_bad", "member_premise_use_ids": ["u_bad"]}])
    write_jsonl(validation, [{"premise_class_id": "q_rfl", "validation_status": "heldout_validated_premise_class"}, {"premise_class_id": "q_bad", "validation_status": "carrier_unsafe_mixed_class"}])
    write_jsonl(faces, [{"face_id": "face_rfl", "source_class_id": "q_rfl"}, {"face_id": "face_bad", "source_class_id": "q_bad"}])
    return fingerprints, classes, validation, faces


def test_dost_quotient_cli_imports_without_root_cli():
    code = """
import importlib
import sys
importlib.import_module('lean_rgc.dost')
importlib.import_module('lean_rgc.cli_dost')
assert 'lean_rgc.cli' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_dost_facade_reexports_quotient_face_runtime_apis():
    dost = importlib.import_module("lean_rgc.dost")
    checks = [
        ("build_response_completion", "lean_rgc.response_completion"),
        ("generate_contextual_candidates", "lean_rgc.contextual_congruence"),
        ("contextual_congruence_from_files", "lean_rgc.contextual_congruence"),
        ("contextual_response_congruence_from_files", "lean_rgc.contextual_congruence"),
        ("build_response_quotient_registry", "lean_rgc.response_quotient"),
        ("project_actions_by_response_quotient", "lean_rgc.response_quotient"),
        ("response_quotient_from_congruence_dir", "lean_rgc.response_quotient"),
        ("generate_premise_contextual_candidates", "lean_rgc.premise_contextual_quotient"),
        ("build_premise_contextual_fingerprints", "lean_rgc.premise_contextual_quotient"),
        ("mine_premise_contextual_quotient", "lean_rgc.premise_contextual_quotient"),
        ("validate_premise_contextual_quotient", "lean_rgc.premise_contextual_quotient"),
        ("retrieve_premise_quotient_classes", "lean_rgc.premise_contextual_quotient"),
        ("premise_quotient_retrieved_actions", "lean_rgc.premise_contextual_quotient"),
        ("build_premise_use_rows", "lean_rgc.bivariate_contextual_quotient"),
        ("write_separator_contexts", "lean_rgc.bivariate_contextual_quotient"),
        ("generate_bivariate_contextual_candidates", "lean_rgc.bivariate_contextual_quotient"),
        ("schedule_bivariate_candidates", "lean_rgc.bivariate_contextual_quotient"),
        ("build_repair_face_ledger", "lean_rgc.bivariate_contextual_quotient"),
        ("build_dual_face_taxonomy", "lean_rgc.face_taxonomy"),
        ("build_canonical_obstruction_tower", "lean_rgc.obstruction_tower"),
    ]
    for attr, module_name in checks:
        assert getattr(dost, attr) is getattr(importlib.import_module(module_name), attr)


def test_dost_quotient_commands_live_in_cli_dost():
    from lean_rgc.cli import build_parser

    parser = build_parser()
    choices = _command_choices(parser)
    assert set(MOVED_COMMANDS) <= set(choices)
    for argv in MOVED_COMMANDS.values():
        ns = parser.parse_args(argv)
        assert ns.func.__module__ == "lean_rgc.cli_dost"


def test_dost_quotient_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    for rel in ["lean_rgc/cli_dost.py", "lean_rgc/dost/__init__.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "from ..cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_response_completion_cli_after_dost_consolidation(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    out = tmp_path / "response_completion.json"
    write_jsonl(responses, [{"response": {"goal.eq": 1.0}, "audit_status": "success"}])
    assert cli_main(["response-completion", "--responses", str(responses), "--out", str(out)]) == 0
    assert out.exists()


def test_face_taxonomy_and_obstruction_tower_cli_after_dost_consolidation(tmp_path: Path):
    fingerprints, classes, validation, faces = _write_face_inputs(tmp_path)
    taxonomy = tmp_path / "taxonomy"
    tower = tmp_path / "tower"
    assert cli_main(["face-taxonomy", "--fingerprints", str(fingerprints), "--classes", str(classes), "--validation", str(validation), "--repair-faces", str(faces), "--out", str(taxonomy)]) == 0
    assert read_jsonl(taxonomy / "dual_face_taxonomy.jsonl")
    assert cli_main(["obstruction-tower", "--out", str(tower), "--fingerprints", str(fingerprints), "--taxonomy-dir", str(taxonomy), "--repair-faces", str(faces), "--validation", str(validation)]) == 0
    assert read_jsonl(tower / "tower_faces.jsonl")
