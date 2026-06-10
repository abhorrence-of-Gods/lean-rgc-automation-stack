from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import conftest


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


def test_tier_manifest_covers_every_test_file():
    manifest = conftest.load_tier_manifest()
    test_files = {path.name for path in TESTS_DIR.glob("test_*.py")}
    assert set(manifest) == test_files


def test_tier_manifest_uses_known_pytest_markers():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    marker_rows = pyproject["tool"]["pytest"]["ini_options"]["markers"]
    configured_markers = {row.split(":", 1)[0] for row in marker_rows}
    assert conftest.VALID_TIERS <= configured_markers

    manifest = conftest.load_tier_manifest()
    for name, tiers in manifest.items():
        assert tiers, name
        assert set(tiers) <= conftest.VALID_TIERS, name


def test_default_target_keeps_current_production_contract_tests():
    manifest = conftest.load_tier_manifest()
    default_files = {
        name
        for name, tiers in manifest.items()
        if "legacy" not in tiers and "slow" not in tiers
    }
    expected_default = {
        "test_core.py",
        "test_qgen.py",
        "test_v58_v62_cli_smoke.py",
        "test_v24_audit_db.py",
        "test_v66_run_db.py",
        "test_v71_lean_runtime_cli_split.py",
        "test_v73_cli_package_migration.py",
        "test_v74_test_tier_manifest.py",
    }
    assert expected_default <= default_files
    assert "test_v10_cli_integrity.py" not in default_files
    assert "test_v55_v57_dost_automation.py" not in default_files


def test_default_collection_excludes_legacy_tests():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert "test_v73_cli_package_migration.py" in proc.stdout
    assert "test_v10_cli_integrity.py" not in proc.stdout
    assert "test_v55_v57_dost_automation.py" not in proc.stdout


def test_legacy_or_slow_collection_selects_history_tests():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "legacy or slow", "--collect-only", "-q"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert "test_v10_cli_integrity.py" in proc.stdout
    assert "test_v55_v57_dost_automation.py" in proc.stdout
    assert "test_v73_cli_package_migration.py" not in proc.stdout
