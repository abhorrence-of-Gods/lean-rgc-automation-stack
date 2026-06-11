from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_server_and_persistent_implementations_live_under_lean_package():
    checks = {
        "server": ("lean_rgc.lean_server", ["LeanServerConfig", "LeanServerAdapter", "audit_with_lean_server", "project_fingerprint"]),
        "persistent_lean_worker": ("lean_rgc.persistent_lean_worker", ["PersistentLeanWorker", "WorkerConfig", "PersistentStateRecord", "main"]),
        "persistent_worker": ("lean_rgc.persistent_worker", ["PersistentLeanWorker", "WorkerConfig", "run_persistent_worker", "main"]),
    }
    for module_name, (compat_name, attrs) in checks.items():
        canonical = importlib.import_module(f"lean_rgc.lean.{module_name}")
        compat = importlib.import_module(compat_name)

        assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / f"{module_name}.py"
        assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / (
            "lean_server.py" if module_name == "server" else f"{module_name}.py"
        )
        assert canonical.__all__
        for attr in attrs:
            assert getattr(compat, attr) is getattr(canonical, attr)


def test_top_level_server_and_persistent_modules_are_shims():
    expected = {
        "lean_server.py": "from .lean.server import *",
        "persistent_lean_worker.py": "from .lean.persistent_lean_worker import *",
        "persistent_worker.py": "from .lean.persistent_worker import *",
    }
    forbidden = {
        "lean_server.py": ["class LeanServerAdapter", "def audit_with_lean_server"],
        "persistent_lean_worker.py": ["class PersistentLeanWorker", "def make_worker_from_args"],
        "persistent_worker.py": ["class PersistentLeanWorker", "def serve_jsonl"],
    }
    for filename, needle in expected.items():
        text = (ROOT / "lean_rgc" / filename).read_text(encoding="utf-8")
        assert needle in text
        for blocked in forbidden[filename]:
            assert blocked not in text


def test_canonical_server_and_persistent_imports_use_canonical_runtime_paths():
    server_text = (ROOT / "lean_rgc" / "lean" / "server.py").read_text(encoding="utf-8")
    worker_text = (ROOT / "lean_rgc" / "lean" / "persistent_lean_worker.py").read_text(encoding="utf-8")
    wrapper_text = (ROOT / "lean_rgc" / "lean" / "persistent_worker.py").read_text(encoding="utf-8")
    cli_text = (ROOT / "lean_rgc" / "cli" / "lean.py").read_text(encoding="utf-8")

    assert "from .executor import LeanExecutor, LeanExecutorConfig" in server_text
    assert "from .structured_state import extract_structured_state, extract_structured_state_from_kernel_json" in server_text
    assert "from .native_worker import native_worker_command, native_worker_manifest" in server_text
    assert "from .server import project_fingerprint" in worker_text
    assert "from .persistent_lean_worker import (" in wrapper_text
    assert "from ..lean.persistent_lean_worker import main as worker_main" in cli_text


def test_server_keeps_compatibility_subprocess_module_string():
    server_text = (ROOT / "lean_rgc" / "lean" / "server.py").read_text(encoding="utf-8")
    assert '"lean_rgc.persistent_lean_worker"' in server_text
    assert '"lean_rgc.lean.persistent_lean_worker"' not in server_text


def test_persistent_worker_module_entrypoints_remain_supported():
    for module in [
        "lean_rgc.persistent_lean_worker",
        "lean_rgc.lean.persistent_lean_worker",
        "lean_rgc.persistent_worker",
        "lean_rgc.lean.persistent_worker",
    ]:
        proc = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "usage:" in proc.stdout


def test_canonical_persistent_worker_jsonl_protocol_smoke():
    payload = "\n".join(
        [
            json.dumps({"id": "status", "cmd": "status"}),
            json.dumps({"id": "shutdown", "cmd": "shutdown"}),
            "",
        ]
    )
    for module in ["lean_rgc.persistent_lean_worker", "lean_rgc.lean.persistent_lean_worker"]:
        proc = subprocess.run(
            [sys.executable, "-m", module, "--backend", "dry_run"],
            cwd=ROOT,
            input=payload,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip().startswith("{")]
        assert rows[0]["id"] == "status"
        assert rows[0]["ok"] is True
        assert rows[-1]["shutdown"] is True


def test_fresh_server_persistent_imports_do_not_reintroduce_circular_imports():
    code = """
import lean_rgc
import lean_rgc.lean_server
import lean_rgc.lean.server
import lean_rgc.persistent_lean_worker
import lean_rgc.lean.persistent_lean_worker
import lean_rgc.persistent_worker
import lean_rgc.lean.persistent_worker
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr
