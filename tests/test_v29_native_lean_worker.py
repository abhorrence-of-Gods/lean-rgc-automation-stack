from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.native_worker import install_native_worker, native_worker_command, native_worker_manifest, packaged_worker_path
from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig


def test_native_worker_source_packaged_and_installable(tmp_path: Path):
    src = packaged_worker_path()
    assert src.exists()
    text = src.read_text(encoding="utf-8")
    assert "Native Lean-side JSONL worker" in text
    assert "kernel_state" in text
    inst = install_native_worker(tmp_path)
    assert Path(inst.worker_path).exists()
    assert "--run" in inst.command
    assert "RGCKernelWorker.lean" in inst.command


def test_native_worker_command_and_manifest(tmp_path: Path):
    inst = install_native_worker(tmp_path)
    cmd = native_worker_command(worker_path=inst.worker_path, workdir=tmp_path, lean_cmd="lake env lean")
    assert cmd.startswith("lake env lean --run")
    manifest = native_worker_manifest(tmp_path, force=True)
    assert manifest["version"].startswith("lean-rgc-native-worker")
    assert manifest["canonical_status"] == "native_worker_protocol_chart_not_canonical"
    assert Path(manifest["worker_path"]).exists()


def test_native_worker_cli_print_command_and_source(tmp_path: Path):
    out = tmp_path / "worker.lean"
    p = subprocess.run([
        sys.executable, "-m", "lean_rgc.cli", "lean-native-worker",
        "--source-out", str(out),
    ], cwd=Path(__file__).resolve().parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.returncode == 0, p.stderr
    assert out.exists()
    assert "Native Lean-side" in out.read_text(encoding="utf-8")
    p2 = subprocess.run([
        sys.executable, "-m", "lean_rgc.cli", "lean-native-worker",
        "--worker-path", str(out), "--print-command",
    ], cwd=Path(__file__).resolve().parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p2.returncode == 0, p2.stderr
    assert "--run" in p2.stdout


def test_lean_server_native_backend_builds_jsonl_command(tmp_path: Path):
    cfg = LeanServerConfig(backend="native", lean_cmd="lake env lean", workdir=str(tmp_path), dry_run=False)
    server = LeanServerAdapter(cfg)
    # Construction should install a native Lean JSONL worker command and expose it as a jsonl backend.
    assert server.status.requested_backend == "native"
    assert server.status.backend == "jsonl"
    assert server.status.server_cmd is not None
    assert "lean_rgc.native_worker" in server.status.server_cmd
