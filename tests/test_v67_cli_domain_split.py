import argparse
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import build_parser


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def test_domain_cli_modules_import_without_root_cli():
    code = """
import importlib
import sys
for name in [
    'lean_rgc.cli_common',
    'lean_rgc.cli_audit',
    'lean_rgc.cli_crg',
    'lean_rgc.cli_poms',
]:
    importlib.import_module(name)
assert 'lean_rgc.cli' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_domain_cli_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    for rel in ["lean_rgc/cli_common.py", "lean_rgc/cli_audit.py", "lean_rgc/cli_crg.py", "lean_rgc/cli_poms.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_domain_split_commands_remain_registered():
    choices = _command_choices(build_parser())
    expected = {
        "audit",
        "batch-audit",
        "repair-species-registry",
        "crg-build-problems",
        "concept-geometry",
        "poms-status",
        "poms-promotion-decisions",
        "failure-attribution-report",
    }
    assert expected <= set(choices)


def test_domain_split_command_handlers_live_in_domain_modules():
    parser = build_parser()
    cases = {
        "audit": (["audit", "--tasks", "tasks.jsonl", "--out", "out"], "lean_rgc.cli_audit"),
        "batch-audit": (["batch-audit", "--tasks", "tasks.jsonl", "--out", "out"], "lean_rgc.cli_audit"),
        "server-audit": (["server-audit", "--tasks", "tasks.jsonl", "--out", "out"], "lean_rgc.cli_audit"),
        "repair-species-registry": (["repair-species-registry", "--out", "registry.jsonl"], "lean_rgc.cli_crg"),
        "crg-build-problems": (["crg-build-problems", "--out", "problems.jsonl"], "lean_rgc.cli_crg"),
        "concept-geometry": (["concept-geometry", "--out", "concepts"], "lean_rgc.cli_crg"),
        "poms-status": (["poms-status", "--run-dir", "run"], "lean_rgc.cli_poms"),
        "failure-attribution-report": (["failure-attribution-report", "--db", "runs.db"], "lean_rgc.cli_poms"),
    }
    for _name, (argv, module_name) in cases.items():
        ns = parser.parse_args(argv)
        assert ns.func.__module__ == module_name
