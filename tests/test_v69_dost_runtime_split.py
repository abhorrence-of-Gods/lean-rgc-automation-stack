import argparse
import importlib
import subprocess
import sys
from pathlib import Path

from lean_rgc.schemas import read_jsonl, write_jsonl


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def _fingerprints(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "premise_use_id": "u_rfl",
                "premise_id": "rfl",
                "use_mode": "exact",
                "fingerprint": {"ctx:eq::resp::goal.eq": 1.0},
                "domain_support": ["ctx:eq"],
                "status_counts": {"success": 2},
                "response_summary": {"goal.eq": 1.0},
                "carrier_summary": {"hidden_obligations": 0.0},
                "cost_summary": {"elapsed_ms": 1.0},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_simp",
                "premise_id": "simp",
                "use_mode": "simp",
                "fingerprint": {"ctx:simp::resp::goal.simp": 1.2},
                "domain_support": ["ctx:simp"],
                "status_counts": {"partial": 1},
                "response_summary": {"goal.simp": 1.2},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {"tail": 0.2},
                "cost_summary": {"elapsed_ms": 4.0},
                "audit_summary": {"unsafe": 0.0},
            },
        ],
    )
    return path


def test_dost_modules_import_without_root_cli():
    code = """
import importlib
import sys
for name in [
    'lean_rgc.dost',
    'lean_rgc.dost.transcripts',
    'lean_rgc.dost.features',
    'lean_rgc.dost.dual_select',
    'lean_rgc.dost.autoplan',
    'lean_rgc.dost.compile_experiment',
    'lean_rgc.dost.reports',
    'lean_rgc.dost.runtime',
    'lean_rgc.cli_dost',
]:
    importlib.import_module(name)
assert 'lean_rgc.cli.main' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_dost_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    rels = [
        "lean_rgc/cli_dost.py",
        "lean_rgc/dost/__init__.py",
        "lean_rgc/dost/transcripts.py",
        "lean_rgc/dost/features.py",
        "lean_rgc/dost/dual_select.py",
        "lean_rgc/dost/autoplan.py",
        "lean_rgc/dost/compile_experiment.py",
        "lean_rgc/dost/reports.py",
        "lean_rgc/dost/runtime.py",
    ]
    for rel in rels:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "from ..cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_dost_automation_shim_reexports_public_contract():
    legacy = importlib.import_module("lean_rgc.dost_automation")
    dost = importlib.import_module("lean_rgc.dost")
    for name in [
        "SCHEMA_PRIMITIVE_OBSERVABLE",
        "SCHEMA_BOUNDED_TRANSCRIPT",
        "SCHEMA_FEATURE_CLOSURE",
        "SCHEMA_FEATURE_VALUE",
        "SCHEMA_FEATURE_SELECTION",
        "SCHEMA_AUTO_PLAN",
        "SCHEMA_DOST_AUDIT",
        "write_primitive_observables",
        "build_bounded_transcripts",
        "build_feature_closure",
        "select_features_for_dual_obstructions",
        "build_dost_auto_plan",
        "compile_experiment_from_auto_plan",
        "build_dost_audit_reports",
        "run_dost_automation_stack",
    ]:
        assert getattr(legacy, name) is getattr(dost, name)


def test_dost_commands_remain_registered_and_live_in_cli_dost():
    from lean_rgc.cli import build_parser

    parser = build_parser()
    choices = _command_choices(parser)
    expected = {
        "dost-primitive-observables",
        "dost-bounded-transcripts",
        "dost-feature-closure",
        "dost-feature-select",
        "dost-autoplan",
        "dost-compile-experiment",
        "dost-audit-reports",
        "dost-stack",
    }
    assert expected <= set(choices)

    cases = {
        "dost-primitive-observables": ["dost-primitive-observables", "--out", "primitive.jsonl"],
        "dost-bounded-transcripts": ["dost-bounded-transcripts", "--input", "in.jsonl", "--out", "transcripts.jsonl"],
        "dost-feature-closure": ["dost-feature-closure", "--transcripts", "transcripts.jsonl", "--out", "features.jsonl"],
        "dost-feature-select": ["dost-feature-select", "--features", "features.jsonl", "--feature-values", "values.jsonl", "--out", "selected.jsonl"],
        "dost-autoplan": ["dost-autoplan", "--out", "plan.json"],
        "dost-compile-experiment": ["dost-compile-experiment", "--auto-plan", "plan.json", "--out", "experiment.sh"],
        "dost-audit-reports": ["dost-audit-reports", "--out", "audit"],
        "dost-stack": ["dost-stack", "--input", "in.jsonl", "--out", "dost"],
    }
    for argv in cases.values():
        ns = parser.parse_args(argv)
        assert ns.func.__module__ == "lean_rgc.cli.dost"


def test_dost_runtime_stack_writes_key_artifacts(tmp_path: Path):
    from lean_rgc.dost import run_dost_automation_stack

    fingerprints = _fingerprints(tmp_path / "fingerprints.jsonl")
    out = tmp_path / "dost"
    summary = run_dost_automation_stack(fingerprints, out, max_features=128)

    artifacts = summary["artifacts"]
    assert read_jsonl(out / "primitive_observables.jsonl")
    assert read_jsonl(out / "bounded_transcripts.jsonl")
    assert read_jsonl(out / "feature_closure.jsonl")
    assert read_jsonl(out / "selected_features.jsonl")
    assert Path(artifacts["auto_plan"]).exists()
    assert Path(artifacts["compiled_experiment"]).exists()
    assert Path(artifacts["compiled_notebook_cells"]).exists()
    assert Path(artifacts["audit_dashboard"]).exists()
