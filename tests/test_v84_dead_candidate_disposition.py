from __future__ import annotations

import importlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_dead_candidate_ledger.py"
LEDGER = ROOT / "docs" / "inventory" / "dead_candidates.md"
IMPORTS = ROOT / "docs" / "inventory" / "imports.json"


def _run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )


def _checker_module():
    spec = importlib.util.spec_from_file_location("check_dead_candidate_ledger", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _dead_candidates() -> list[str]:
    payload = json.loads(IMPORTS.read_text(encoding="utf-8"))
    return [
        row["module"]
        for row in payload["modules"]
        if row["classification"] == "dead_candidate"
    ]


def _ledger_headings() -> set[str]:
    text = LEDGER.read_text(encoding="utf-8")
    return set(re.findall(r"^##\s+(lean_rgc(?:\.[A-Za-z0-9_]+)+)\s*$", text, flags=re.MULTILINE))


def test_dead_candidate_ledger_script_passes_current_tree():
    proc = _run_checker()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "dead candidate ledger ok:" in proc.stdout


def test_dead_candidate_ledger_json_shape_and_zero_violations():
    proc = _run_checker("--json")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)

    assert payload["schema_version"] == "lean-rgc.dead-candidate-ledger-check.v1"
    assert payload["ok"] is True
    assert payload["violations"] == []
    assert payload["missing"] == []
    assert payload["stale"] == []
    assert payload["n_checked_modules"] == len(payload["checked_modules"]) == 8
    assert {row["module"] for row in payload["checked_modules"]} == set(_dead_candidates())
    for row in payload["checked_modules"]:
        assert row["ledger_entry"] is True
        assert row["deletion_blocked"] is True
        if row["compile_status"] != "ok" or row["import_status"] != "ok":
            assert row["risk_documented"] is True


def test_dead_candidate_ledger_mentions_every_generated_candidate():
    candidates = set(_dead_candidates())
    headings = _ledger_headings()
    assert candidates == headings
    text = LEDGER.read_text(encoding="utf-8").lower()
    for module in candidates:
        section = text.split(f"## {module}".lower(), 1)[1]
        section = section.split("\n## ", 1)[0]
        assert "not approved for deletion" in section
        assert "reachability evidence" in section


def test_response_quotient_registry_remains_compatibility_wrapper():
    canonical = importlib.import_module("lean_rgc.response_quotient")
    compatibility = importlib.import_module("lean_rgc.response_quotient_registry")

    assert compatibility.build_response_quotient_registry is canonical.build_response_quotient_registry
    assert compatibility.project_actions_by_response_quotient is canonical.project_actions_by_response_quotient
    assert compatibility.response_quotient_from_congruence_dir is canonical.response_quotient_from_congruence_dir
    assert compatibility.response_quotient_registry_from_files is canonical.build_response_quotient_registry
    assert compatibility.apply_response_quotient_to_actions is canonical.project_actions_by_response_quotient


def test_dead_candidate_checker_module_api_matches_cli():
    checker = _checker_module()
    result = checker.run_check()
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["stale"] == []
    assert {row["module"] for row in result["checked_modules"]} == set(_dead_candidates())
