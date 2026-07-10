from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lean_rgc.native_worker import (
    native_worker_command,
    native_worker_manifest,
    packaged_kernel_rpc_worker_path,
)


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


def test_kernel_rpc_worker_is_packaged_and_selectable(tmp_path: Path):
    src = packaged_kernel_rpc_worker_path()
    assert src.exists()
    text = src.read_text(encoding="utf-8")
    assert text.startswith("import Lean\n")
    assert "Lean.Elab.runTactic" in text
    assert "lean_kernel_rpc_in_memory_v1" in text
    assert 'def rpcProtocolVersion : String := "lean-rgc-jsonl-rpc-v2"' in text
    assert "let rep ← handleLine ref line" in text
    assert text.count("stdout.putStrLn") == 1

    manifest = native_worker_manifest(tmp_path, exec_mode="kernel_rpc", force=True)
    assert manifest["version"].startswith("lean-rgc-native-worker-v50")
    assert manifest["exec_mode"] == "kernel_rpc"
    assert Path(manifest["worker_path"]).name == "RGCKernelRPC.lean"

    cmd = native_worker_command(
        worker_path=manifest["worker_path"],
        workdir=tmp_path,
        lean_cmd="lean",
        exec_mode="kernel_rpc",
    )
    assert "--exec-mode kernel_rpc" in cmd
    assert "RGCKernelRPC.lean" in cmd


@pytest.mark.skipif(_lean_bin() is None, reason="Lean binary is not installed")
def test_kernel_rpc_worker_applies_intro_and_rfl_in_memory():
    lean = _lean_bin()
    assert lean is not None
    worker = packaged_kernel_rpc_worker_path()
    lines = [
        {"id": "unknown", "cmd": "no_such_cmd"},
        {"id": "load", "cmd": "load_project", "imports": ["Lean"]},
        {
            "id": "init",
            "cmd": "init_state",
            "task": {
                "task_id": "t_forall",
                "statement": "forall n : Nat, n = n",
                "imports": ["Lean"],
            },
        },
        {
            "id": "intro",
            "cmd": "apply_tactic",
            "state_id": "krpc_state_0",
            "action": {"action_id": "intro", "tactic": "intro n"},
        },
        {
            "id": "rfl",
            "cmd": "apply_tactic",
            "state_id": "krpc_state_1",
            "action": {"action_id": "rfl", "tactic": "rfl"},
        },
        {"id": "stop", "cmd": "shutdown"},
    ]
    payload = "{not-json\n" + "\n".join(
        json.dumps(x, ensure_ascii=True) for x in lines
    ) + "\n"
    proc = subprocess.run(
        [lean, "--run", str(worker), "--imports", "Lean"],
        input=payload,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert len(replies) == len(lines) + 1
    parse_error = replies[0]
    assert parse_error["id"] is None
    assert parse_error["rpc_protocol_version"] == "lean-rgc-jsonl-rpc-v2"
    assert parse_error["ok"] is False
    assert "json parse error" in parse_error["error"]

    for request, reply in zip(lines, replies[1:]):
        assert reply["id"] == request["id"]
        assert reply["rpc_protocol_version"] == "lean-rgc-jsonl-rpc-v2"

    unknown = replies[1]
    assert unknown["ok"] is False
    assert unknown["error"] == "unknown cmd: no_such_cmd"

    assert replies[2]["ok"] is True
    assert replies[3]["kernel_state"]["object_coverage"]["expr_ast"] is True

    intro = replies[4]
    assert intro["status"] == "partial"
    after_intro = intro["kernel_state_after"]
    assert after_intro["goals"][0]["relation"] == "="
    assert after_intro["local_contexts"][0]["nodes"][0]["user_name"] == "n"
    assert after_intro["object_coverage"]["local_decl_graph"] is True

    rfl = replies[5]
    assert rfl["status"] == "success"
    assert rfl["kernel_state_after"]["goals"] == []
    assert rfl["state_delta"]["closed_goals"]
    assert rfl["audit"]["audit_flags"]["execution_backend"] == "lean_kernel_rpc_in_memory_v1"
    assert replies[6]["ok"] is True
    assert replies[6]["shutdown"] is True
