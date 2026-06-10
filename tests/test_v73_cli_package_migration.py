import argparse
import importlib
from pathlib import Path

from lean_rgc.cli import build_parser, main


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def test_cli_resolves_to_package_and_exports_entrypoints():
    cli = importlib.import_module("lean_rgc.cli")
    assert Path(cli.__file__).name == "__init__.py"
    assert callable(main)
    assert callable(build_parser)
    assert callable(cli.main)
    assert callable(cli.build_parser)


def test_pyproject_entrypoint_stays_on_lean_rgc_cli_main():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'lean-rgc = "lean_rgc.cli:main"' in text


def test_legacy_top_level_cli_shims_reexport_register_functions():
    pairs = [
        ("lean_rgc.cli_audit", "lean_rgc.cli.audit", "register_audit_commands"),
        ("lean_rgc.cli_crg", "lean_rgc.cli.crg", "register_crg_commands"),
        ("lean_rgc.cli_data", "lean_rgc.cli.data", "register_data_commands"),
        ("lean_rgc.cli_dost", "lean_rgc.cli.dost", "register_dost_commands"),
        ("lean_rgc.cli_experiment", "lean_rgc.cli.experiment", "register_experiment_commands"),
        ("lean_rgc.cli_lean", "lean_rgc.cli.lean", "register_lean_commands"),
        ("lean_rgc.cli_pipeline", "lean_rgc.cli.pipeline", "register_pipeline_commands"),
        ("lean_rgc.cli_poms", "lean_rgc.cli.poms", "register_poms_commands"),
    ]
    for legacy_name, package_name, attr in pairs:
        legacy = importlib.import_module(legacy_name)
        package = importlib.import_module(package_name)
        assert getattr(legacy, attr) is getattr(package, attr)


def test_representative_command_handlers_live_in_cli_package_modules():
    parser = build_parser()
    cases = {
        "audit": (["audit", "--tasks", "tasks.jsonl", "--out", "out"], "lean_rgc.cli.audit"),
        "run-db-query": (["run-db-query", "--db", "runs.db", "--sql", "SELECT 1"], "lean_rgc.cli.data"),
        "data query": (["data", "query", "--db", "runs.db", "--sql", "SELECT 1"], "lean_rgc.cli.data"),
        "dost-stack": (["dost-stack", "--input", "in.jsonl", "--out", "dost"], "lean_rgc.cli.dost"),
        "crg-build-problems": (["crg-build-problems", "--out", "problems.jsonl"], "lean_rgc.cli.crg"),
        "lean-server-health": (["lean-server-health", "--dry-run"], "lean_rgc.cli.lean"),
        "pipeline": (["pipeline", "--tasks", "tasks.jsonl", "--actions", "actions.jsonl", "--out", "out", "--dry-run"], "lean_rgc.cli.pipeline"),
        "poms-status": (["poms-status", "--run-dir", "run"], "lean_rgc.cli.poms"),
        "candidates": (["candidates", "--tasks", "tasks.jsonl", "--out", "candidates.jsonl"], "lean_rgc.cli.experiment"),
    }
    choices = _command_choices(parser)
    for label, (argv, module_name) in cases.items():
        assert argv[0] in choices
        ns = parser.parse_args(argv)
        assert ns.func.__module__ == module_name, label


def test_cli_package_modules_do_not_import_legacy_cli_shims():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "lean_rgc" / "cli").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "cli_" not in text
        assert "from ..cli_" not in text
        assert "import lean_rgc.cli_" not in text
