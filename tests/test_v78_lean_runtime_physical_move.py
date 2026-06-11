from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_state_parser_implementation_lives_under_lean_package():
    canonical = importlib.import_module("lean_rgc.lean.state_parser")
    compat = importlib.import_module("lean_rgc.state_parser")

    assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / "state_parser.py"
    assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / "state_parser.py"
    assert compat.LeanMessageParser is canonical.LeanMessageParser
    assert compat.ParsedGoal is canonical.ParsedGoal
    assert compat.ParsedLeanState is canonical.ParsedLeanState
    assert compat.ParsedProofState is canonical.ParsedProofState
    assert compat.parse_proof_state is canonical.parse_proof_state


def test_native_worker_implementation_lives_under_lean_package():
    canonical = importlib.import_module("lean_rgc.lean.native_worker")
    compat = importlib.import_module("lean_rgc.native_worker")

    assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / "native_worker.py"
    assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / "native_worker.py"
    assert compat.NativeWorkerInstall is canonical.NativeWorkerInstall
    assert compat.native_worker_command is canonical.native_worker_command
    assert compat.native_worker_manifest is canonical.native_worker_manifest
    assert compat.packaged_worker_path is canonical.packaged_worker_path
    assert compat.main is canonical.main


def test_native_worker_packaged_source_paths_stay_at_package_root():
    from lean_rgc.lean.native_worker import packaged_kernel_rpc_worker_path, packaged_worker_path

    worker = packaged_worker_path()
    kernel_rpc = packaged_kernel_rpc_worker_path()
    assert worker == ROOT / "lean_rgc" / "native_lean" / "RGCKernelWorker.lean"
    assert kernel_rpc == ROOT / "lean_rgc" / "native_lean" / "RGCKernelRPC.lean"
    assert worker.exists()
    assert kernel_rpc.exists()


def test_native_worker_compat_and_canonical_module_entrypoints():
    for module in ["lean_rgc.native_worker", "lean_rgc.lean.native_worker"]:
        proc = subprocess.run(
            [sys.executable, "-m", module, "--print-command"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "--run" in proc.stdout
        assert "RGCKernelWorker.lean" in proc.stdout


def test_runtime_modules_import_canonical_helpers():
    executor_text = (ROOT / "lean_rgc" / "lean" / "executor.py").read_text(encoding="utf-8")
    server_text = (ROOT / "lean_rgc" / "lean" / "server.py").read_text(encoding="utf-8")
    assert "from .state_parser import LeanMessageParser" in executor_text
    assert "from .native_worker import native_worker_command, native_worker_manifest" in server_text
    assert '"lean_rgc.native_worker"' in server_text
