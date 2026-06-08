from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

from lean_rgc.native_worker import packaged_worker_path, native_worker_command, native_worker_manifest
from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig


def _lean_bin() -> str | None:
    found = shutil.which("lean")
    if found:
        return found
    home = Path.home()
    for candidate in [
        home / ".elan" / "bin" / "lean.exe",
        home / ".elan" / "bin" / "lean",
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def test_native_worker_v30_source_contains_source_check():
    src = packaged_worker_path().read_text(encoding="utf-8")
    assert src.startswith("import Lean\n")
    assert "experimental v30" in src
    assert "runSourceCheck" in src
    assert "renderCandidateSource" in src
    assert "native_lean_source_check_v30" in src
    assert "--exec-mode" in src


def test_native_worker_command_passes_exec_mode(tmp_path: Path):
    manifest = native_worker_manifest(tmp_path, exec_mode="heuristic", force=True)
    assert manifest["version"].startswith("lean-rgc-native-worker-v30")
    assert manifest["exec_mode"] == "heuristic"
    cmd = native_worker_command(worker_path=manifest["worker_path"], workdir=tmp_path, exec_mode="heuristic")
    assert "--exec-mode heuristic" in cmd


def test_native_worker_cli_print_command_exec_mode(tmp_path: Path):
    out = tmp_path / "worker.lean"
    p = subprocess.run([
        sys.executable, "-m", "lean_rgc.cli", "lean-native-worker",
        "--source-out", str(out),
    ], cwd=Path(__file__).resolve().parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.returncode == 0, p.stderr
    assert out.exists()
    p2 = subprocess.run([
        sys.executable, "-m", "lean_rgc.cli", "lean-native-worker",
        "--worker-path", str(out), "--print-command", "--exec-mode", "heuristic",
    ], cwd=Path(__file__).resolve().parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p2.returncode == 0, p2.stderr
    assert "--exec-mode heuristic" in p2.stdout


def test_lean_server_native_config_carries_exec_mode(tmp_path: Path):
    cfg = LeanServerConfig(backend="native", lean_cmd="lake env lean", workdir=str(tmp_path), native_exec_mode="heuristic")
    server = LeanServerAdapter(cfg)
    assert server.config.native_exec_mode == "heuristic"
    assert server.status.backend == "jsonl"
    assert server.status.server_cmd is not None
    assert "--exec-mode heuristic" in server.status.server_cmd


@pytest.mark.skipif(_lean_bin() is None, reason="Lean binary is not installed")
def test_native_worker_v30_load_project_jsonl_protocol():
    lean = _lean_bin()
    assert lean is not None
    payload = "\n".join([
        json.dumps({"id": "load", "cmd": "load_project", "workdir": ".", "lean_cmd": "lean", "native_exec_mode": "source_check", "timeout_s": 20}),
        json.dumps({"id": "stop", "cmd": "shutdown"}),
    ]) + "\n"
    proc = subprocess.run(
        [lean, "--run", str(packaged_worker_path()), "--exec-mode", "source_check", "--lean-cmd", "lean", "--workdir", "."],
        input=payload,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rows = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        rows.append(json.loads(line))
    assert rows[0]["ok"] is True
    assert rows[0]["backend"] == "native_lean_jsonl_worker_v30"
    assert rows[-1]["shutdown"] is True
