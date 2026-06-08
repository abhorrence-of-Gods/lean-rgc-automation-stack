from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.kernel_state import (
    KERNEL_STATE_SCHEMA_VERSION,
    KernelGoalStateServer,
    KernelGoalStateServerConfig,
    normalize_kernel_state_v1,
    structural_kernel_response,
)
from lean_rgc.persistent_lean_worker import PersistentLeanWorker, WorkerConfig
from lean_rgc.schemas import LeanTask, TacticAction, write_jsonl


def _alpha_kernel(state_id: str, name: str, mid: str) -> dict:
    return {
        "schema_version": "lean-rgc-kernel-state-v1",
        "state_id": state_id,
        "task_id": "alpha",
        "env_fingerprint": "env",
        "goals": [{
            "goal_id": "g0",
            "mvar_id": mid,
            "target": {"text": f"{name} = {name}", "kind": "app", "head": "Eq"},
            "local_deps": [f"fvar_{name}"],
        }],
        "local_context": {
            "nodes": [{"fvar_id": f"fvar_{name}", "user_name": name, "type_text": "Nat"}],
            "edges": [],
        },
        "metavars": [{"mvar_id": mid, "type_text": f"{name} = {name}", "local_deps": [f"fvar_{name}"]}],
        "typeclasses": [],
    }


def test_kernel_state_v1_normalized_hash_quotients_names():
    x = normalize_kernel_state_v1(_alpha_kernel("s_x", "x", "?m.1"))
    n = normalize_kernel_state_v1(_alpha_kernel("s_n", "n", "?m.99"))
    assert x["schema_version"] == KERNEL_STATE_SCHEMA_VERSION
    assert x["state_hash_raw"] != n["state_hash_raw"]
    assert x["state_hash_norm"] == n["state_hash_norm"]
    assert x["goals"][0]["norm_hash"] == n["goals"][0]["norm_hash"]
    assert x["local_contexts"][0]["nodes"][0]["depends_on_fvars"] == []
    assert x["canonical_status"] == "kernel_structured_state_chart_not_canonical"


def test_kernel_goal_state_server_applies_transition_dry_run():
    server = KernelGoalStateServer(KernelGoalStateServerConfig(backend="dry_run"))
    task = LeanTask(task_id="rfl_task", statement="n = n", imports=[])
    action = TacticAction(action_id="rfl", tactic="rfl")
    base = server.register_task(task)
    transition = server.apply_tactic(base["state"]["state_id"], action)
    assert transition["schema_version"] == "lean-rgc-kernel-transition-v1"
    assert transition["status"] == "success"
    assert transition["kernel_state_before"]["goals"]
    assert transition["kernel_state_after"]["goals"] == []
    assert transition["state_delta"]["progress_status"] == "closed"
    assert transition["response"]["response"]["mvar_measure"] > 0
    assert transition["replay"]["replay_status"] in {"verified", "pending"}
    assert transition["safety"]["source_safety"]["ok"] is True


def test_structural_kernel_response_uses_v1_payloads():
    before = normalize_kernel_state_v1(_alpha_kernel("s0", "x", "?m.1"))
    after = normalize_kernel_state_v1({
        "schema_version": "lean-rgc-kernel-state-v1",
        "state_id": "s1",
        "task_id": "alpha",
        "env_fingerprint": "env",
        "status": "closed",
        "closed": True,
        "goals": [],
        "local_context": {"nodes": [], "edges": []},
        "metavars": [],
        "typeclasses": [],
    })
    response = structural_kernel_response(before, after, action={"action_id": "rfl", "tactic": "rfl"})
    assert response["response"]["goal_count"] == 1.0
    assert response["state_delta"]["goal_count_after"] == 0


def test_persistent_worker_kernel_state_is_strict_v1():
    worker = PersistentLeanWorker(WorkerConfig(backend="dry_run"))
    task = LeanTask(task_id="p", statement="n = n", imports=[])
    state = worker.register_task(task)["state"]
    kernel = worker.kernel_state(state["state_id"])
    assert kernel["schema_version"] == KERNEL_STATE_SCHEMA_VERSION
    assert kernel["env_fingerprint"]
    assert kernel["state_hash_raw"]
    assert kernel["state_hash_norm"]
    assert isinstance(kernel["local_contexts"], list)
    assert kernel["object_coverage"]["tactic_transition_api"] is True


def test_kernel_state_normalize_cli(tmp_path: Path):
    src = tmp_path / "kernel.jsonl"
    out = tmp_path / "strict.jsonl"
    report = tmp_path / "report.json"
    write_jsonl(src, [_alpha_kernel("s_x", "x", "?m.1")])
    assert main(["kernel-state-normalize", "--kernel-jsonl", str(src), "--out", str(out), "--summary-out", str(report)]) == 0
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["schema_version"] == KERNEL_STATE_SCHEMA_VERSION
    assert rows[0]["expr_graph"]["nodes"]
    assert json.loads(report.read_text(encoding="utf-8"))["n_kernel_states"] == 1
