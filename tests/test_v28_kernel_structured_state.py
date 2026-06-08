from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.structured_state import extract_structured_state_from_kernel_json
from lean_rgc.schemas import LeanTask, TacticAction
from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig


def sample_kernel_state():
    return {
        "schema_version": "lean-rgc-kernel-state-v28.0",
        "task_id": "k1",
        "state_id": "s1",
        "goals": [
            {
                "mvar_id": "?m.1",
                "target": {"text": "n = n", "kind": "app", "head": "Eq"},
                "local_deps": ["fvar_n"],
            }
        ],
        "local_context": {
            "nodes": [
                {"fvar_id": "fvar_n", "user_name": "n", "type": {"text": "Nat", "head": "Nat"}, "binder_kind": "default"}
            ]
        },
        "metavars": [{"mvar_id": "?m.1", "type_text": "n = n"}],
        "typeclasses": [{"mvar_id": "?m.tc", "text": "DecidableEq Nat"}],
        "messages": ["kernel payload"],
    }


def test_kernel_json_normalizes_to_structured_state():
    row = extract_structured_state_from_kernel_json(sample_kernel_state()).to_dict()
    assert row["schema_version"].startswith("lean-rgc-structured-state-v28")
    assert row["extraction_backend"] == "kernel_json_v28"
    assert row["kernel_state_hash"]
    assert row["canonical_status"] == "kernel_backed_structured_state_chart_not_canonical"
    assert row["goals"][0]["target_head"] == "Eq"
    assert row["goals"][0]["mvar_id"] == "?m.1"
    assert row["local_context"]["nodes"][0]["fvar_id"] == "fvar_n"
    assert row["typeclasses"]["n_obligations"] == 1


def test_structured_state_cli_accepts_kernel_jsonl(tmp_path: Path):
    kernel = tmp_path / "kernel.jsonl"
    kernel.write_text(json.dumps(sample_kernel_state()) + "\n")
    out = tmp_path / "structured.jsonl"
    summary = tmp_path / "summary.json"
    rc = cli_main(["structured-state-extract", "--kernel-jsonl", str(kernel), "--out", str(out), "--summary-out", str(summary)])
    assert rc == 0
    rows = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    assert rows and rows[0]["extraction_backend"] == "kernel_jsonl_v28"
    rep = json.loads(summary.read_text())
    assert rep["n_states"] == 1


def test_persistent_worker_returns_kernel_structured_state():
    reqs = [
        {"id": "load", "cmd": "load_project"},
        {"id": "init", "cmd": "init_state", "task": {"task_id": "p", "statement": "∀ n : Nat, n = n", "imports": ["Init"]}},
        {"id": "ss", "cmd": "structured_state", "state_id": None},
        {"id": "shutdown", "cmd": "shutdown"},
    ]
    # Fill state_id from init response with an explicit two-step session.
    proc = subprocess.Popen([sys.executable, "-m", "lean_rgc.persistent_lean_worker", "--backend", "dry_run"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(reqs[0]) + "\n"); proc.stdin.flush(); json.loads(proc.stdout.readline())
    proc.stdin.write(json.dumps(reqs[1]) + "\n"); proc.stdin.flush(); init = json.loads(proc.stdout.readline())
    sid = init["state"]["state_id"]
    proc.stdin.write(json.dumps({"id": "ks", "cmd": "kernel_state", "state_id": sid}) + "\n"); proc.stdin.flush(); ks = json.loads(proc.stdout.readline())
    proc.stdin.write(json.dumps({"id": "ss", "cmd": "structured_state", "state_id": sid}) + "\n"); proc.stdin.flush(); ss = json.loads(proc.stdout.readline())
    proc.stdin.write(json.dumps({"id": "shutdown", "cmd": "shutdown"}) + "\n"); proc.stdin.flush(); json.loads(proc.stdout.readline())
    proc.wait(timeout=5)
    assert ks["ok"] is True and ks["kernel_state"]["schema_version"].startswith("lean-rgc-kernel-state")
    assert ss["ok"] is True
    assert ss["structured_state"]["extraction_backend"].startswith("persistent_worker_kernel_json_v28")


def test_server_adapter_prefers_kernel_payload_from_persistent_worker(tmp_path: Path):
    task = LeanTask(task_id="k2", statement="∀ n : Nat, n = n", imports=["Init"])
    action = TacticAction(action_id="intro", tactic="intro n", tactic_class="intro")
    cfg = LeanServerConfig(backend="persistent", dry_run=True, fallback_to_file=False, startup_timeout_s=5.0, workdir=str(tmp_path))
    with LeanServerAdapter(cfg) as server:
        base = server.register_task(task)["state"]
        rec = server.apply_tactic_to_state_id(task, action, base["state_id"])
        row = server.structured_state(task, rec.after_state, rec)
    assert rec.audit_flags.get("kernel_state_hash")
    assert row["extraction_backend"] == "kernel_json_v28"
    assert row["canonical_status"] == "kernel_backed_structured_state_chart_not_canonical"
