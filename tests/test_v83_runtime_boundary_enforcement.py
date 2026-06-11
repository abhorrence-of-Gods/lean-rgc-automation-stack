from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_runtime_boundary.py"


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
    spec = importlib.util.spec_from_file_location("check_runtime_boundary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_boundary_script_passes_current_tree():
    proc = _run_checker()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "runtime boundary ok:" in proc.stdout


def test_runtime_boundary_json_shape_and_zero_violations():
    proc = _run_checker("--json")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)

    assert payload["schema_version"] == "lean-rgc.runtime-boundary-check.v1"
    assert payload["ok"] is True
    assert payload["violations"] == []
    assert payload["n_checked_modules"] == len(payload["checked_modules"]) >= 12
    assert payload["n_checked_files"] == len(payload["checked_files"])
    assert "lean_rgc/lean/server.py" in payload["checked_files"]
    assert any(row["compatibility"] == "lean_rgc.lean_server" for row in payload["checked_modules"])


def test_runtime_boundary_mapping_preserves_identity():
    checker = _checker_module()
    for row in checker.RUNTIME_MODULES:
        canonical = importlib.import_module(row.canonical)
        compatibility = importlib.import_module(row.compatibility)
        for attr in row.attrs:
            assert getattr(compatibility, attr) is getattr(canonical, attr)


def test_runtime_boundary_production_files_use_canonical_imports():
    checker = _checker_module()
    result = checker.run_check()
    assert result["ok"] is True
    assert result["violations"] == []

    text_by_file = {
        rel: (ROOT / rel).read_text(encoding="utf-8")
        for rel in [
            "lean_rgc/pipeline.py",
            "lean_rgc/cli/audit.py",
            "lean_rgc/cli/experiment.py",
            "lean_rgc/cli/lean.py",
            "lean_rgc/arithmetic_teacher_kernel_audit.py",
            "lean_rgc/kernel_context_cache.py",
        ]
    }
    forbidden = [
        "from .executor import",
        "from .lean_server import",
        "from .frontier import",
        "from ..executor import",
        "from ..lean_server import",
        "from ..frontier import",
        "import lean_rgc.executor",
        "import lean_rgc.lean_server",
    ]
    for rel, text in text_by_file.items():
        for needle in forbidden:
            assert needle not in text, f"{rel} imports compatibility runtime surface via {needle!r}"


def test_runtime_boundary_keeps_persistent_subprocess_compatibility_string():
    server_text = (ROOT / "lean_rgc" / "lean" / "server.py").read_text(encoding="utf-8")
    assert '"lean_rgc.persistent_lean_worker"' in server_text
    assert '"lean_rgc.lean.persistent_lean_worker"' not in server_text
