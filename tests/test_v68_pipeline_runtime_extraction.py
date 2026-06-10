import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import build_parser, main as cli_main
from lean_rgc.pipeline import PipelineConfig, run_basic_pipeline


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def test_pipeline_modules_import_without_root_cli():
    code = """
import importlib
import sys
for name in ['lean_rgc.pipeline', 'lean_rgc.cli_pipeline']:
    importlib.import_module(name)
assert 'lean_rgc.cli' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_pipeline_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    for rel in ["lean_rgc/pipeline.py", "lean_rgc/cli_pipeline.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_pipeline_commands_remain_registered_with_pipeline_handlers():
    choices = _command_choices(build_parser())
    expected = {
        "pipeline",
        "frontier-pipeline",
        "rgc-loop",
        "iterate",
        "stage-report",
        "compare-runs",
        "iterate-report",
    }
    assert expected <= set(choices)

    for name in expected:
        func = choices[name].get_default("func")
        assert func is not None
        assert func.__module__ == "lean_rgc.cli_pipeline"


def test_run_basic_pipeline_dry_run_smoke(tmp_path: Path):
    out = tmp_path / "basic"
    report = run_basic_pipeline(
        PipelineConfig(
            tasks="examples/minimal_theorems.jsonl",
            actions="examples/core_tactics.jsonl",
            out=str(out),
            dry_run=True,
            max_actions=1,
            import_mode="core",
        )
    )
    assert report["pipeline_files"]["audit_dir"] == str(out / "audit")
    assert (out / "pipeline_report.json").exists()
    assert (out / "pipeline_summary.json").exists()
    assert (out / "audit" / "responses.jsonl").exists()


def test_pipeline_cli_dry_run_run_db_smoke(tmp_path: Path):
    out = tmp_path / "pipe"
    rc = cli_main(
        [
            "pipeline",
            "--tasks",
            "examples/minimal_theorems.jsonl",
            "--actions",
            "examples/core_tactics.jsonl",
            "--out",
            str(out),
            "--dry-run",
            "--run-db",
            "--max-actions",
            "1",
            "--import-mode",
            "core",
        ]
    )
    assert rc == 0
    assert (out / "pipeline_summary.json").exists()
    assert (out / "runs.db").exists()

    con = sqlite3.connect(out / "runs.db")
    try:
        assert con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM responses").fetchone()[0] > 0
    finally:
        con.close()
