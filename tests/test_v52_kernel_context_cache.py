from __future__ import annotations

import json
import sys
from pathlib import Path

from lean_rgc.kernel_context_cache import audit_contextual_candidates_with_kernel_cache
from lean_rgc.lean_server import LeanServerConfig
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl


def _contextual_actions() -> list[TacticAction]:
    pre = {
        "action_id": "ctx_intro",
        "tactic": "intro n",
        "tactic_class": "intro",
        "context_kind": "intro",
    }
    post = {
        "action_id": "ctx_simp",
        "tactic": "simp",
        "tactic_class": "simp",
        "context_kind": "simp",
    }
    p1 = {"action_id": "p_add_zero", "tactic": "simp [Nat.add_zero]", "tactic_class": "simp"}
    p2 = {"action_id": "p_zero_add", "tactic": "simp [Nat.zero_add]", "tactic_class": "simp"}
    return [
        TacticAction(
            action_id="base_intro_simp",
            tactic="intro n\nsimp",
            tactic_class="premise_contextual_baseline",
            metadata={
                "bivariate_contextual": True,
                "is_contextual_baseline": True,
                "context_pair": "ctx_intro::ctx_simp",
                "pre_context_id": "ctx_intro",
                "post_context_id": "ctx_simp",
                "pre_context_action": pre,
                "post_context_action": post,
                "premise_core_action": None,
            },
        ),
        TacticAction(
            action_id="probe_add_zero",
            tactic="intro n\nsimp [Nat.add_zero]\nsimp",
            tactic_class="premise_contextual_probe",
            metadata={
                "bivariate_contextual": True,
                "premise_contextual_probe": True,
                "premise_use_id": "u_add_zero",
                "premise_id": "Nat.add_zero",
                "context_pair": "ctx_intro::ctx_simp",
                "pre_context_id": "ctx_intro",
                "post_context_id": "ctx_simp",
                "baseline_action_id": "base_intro_simp",
                "pre_context_action": pre,
                "post_context_action": post,
                "premise_core_action": p1,
            },
        ),
        TacticAction(
            action_id="probe_zero_add",
            tactic="intro n\nsimp [Nat.zero_add]\nsimp",
            tactic_class="premise_contextual_probe",
            metadata={
                "bivariate_contextual": True,
                "premise_contextual_probe": True,
                "premise_use_id": "u_zero_add",
                "premise_id": "Nat.zero_add",
                "context_pair": "ctx_intro::ctx_simp",
                "pre_context_id": "ctx_intro",
                "post_context_id": "ctx_simp",
                "baseline_action_id": "base_intro_simp",
                "pre_context_action": pre,
                "post_context_action": post,
                "premise_core_action": p2,
            },
        ),
    ]


def test_kernel_context_cache_reuses_pre_context_and_writes_compatible_audits(tmp_path: Path):
    worker_py = tmp_path / "fake_kernel_worker.py"
    log = tmp_path / "worker_log.jsonl"
    worker_py.write_text(
        r'''
import json, sys
from pathlib import Path

log = Path(sys.argv[1])
next_id = 0

def emit(obj):
    print(json.dumps(obj), flush=True)

def kstate(sid, closed=False):
    return {
        "schema_version": "lean-rgc-kernel-state-v1",
        "state_id": sid,
        "status": "closed" if closed else "open",
        "closed": closed,
        "goals": [] if closed else [{"goal_id": "g0", "target_expr_id": "expr_t", "target_head": "Eq", "relation": "="}],
        "expr_graph": {"nodes": [], "roots": []},
        "local_contexts": [],
        "metavars": [],
        "typeclasses": [],
    }

for line in sys.stdin:
    req = json.loads(line)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"cmd": req.get("cmd"), "state_id": req.get("state_id"), "action": (req.get("action") or {}).get("action_id")}) + "\n")
    cmd = req.get("cmd")
    if cmd == "load_project":
        emit({"ok": True, "loaded": True, "backend": "lean_kernel_rpc_in_memory_v1"})
    elif cmd in {"register_task", "init_state"}:
        task = req["task"]
        emit({"ok": True, "state": {"state_id": "root_0", "task_id": task["task_id"], "status": "open"}, "kernel_state": kstate("root_0")})
    elif cmd == "apply_tactic":
        next_id += 1
        task = req["task"]
        action = req["action"]
        aid = action["action_id"]
        closed = aid == "ctx_simp"
        sid = f"{req['state_id']}__{aid}_{next_id}"
        status = "success" if closed else "partial"
        after = {"state_id": sid, "task_id": task["task_id"], "goals_text": "" if closed else "unsolved goals", "target": task["statement"], "raw_messages": []}
        kernel = kstate(sid, closed=closed)
        audit = {
            "task_id": task["task_id"],
            "state_id": req["state_id"],
            "action_id": aid,
            "status": status,
            "elapsed_ms": 1.0,
            "messages": [],
            "after_state": after,
            "audit_flags": {
                "execution_backend": "lean_kernel_rpc_in_memory_v1",
                "after_persistent_state_id": sid,
                "kernel_state": kernel,
            },
        }
        emit({"ok": True, "status": status, "audit": audit, "kernel_state": kernel, "kernel_state_after": kernel, "after_state_id": sid})
    elif cmd == "structured_state":
        emit({"ok": False, "error": "not implemented"})
    elif cmd == "shutdown":
        emit({"ok": True, "shutdown": True})
        break
    else:
        emit({"ok": False, "error": "unknown"})
''',
        encoding="utf-8",
    )
    task = LeanTask(task_id="t_forall", statement="forall n : Nat, n = n", imports=["Lean"])
    cfg = LeanServerConfig(
        backend="jsonl",
        server_cmd=f'"{sys.executable}" "{worker_py}" "{log}"',
        native_exec_mode="kernel_rpc",
        fallback_to_file=False,
        startup_timeout_s=2.0,
    )
    out = tmp_path / "audit"
    summary = audit_contextual_candidates_with_kernel_cache(
        [task],
        _contextual_actions(),
        out_dir=out,
        server_config=cfg,
        max_actions=8,
    )

    assert summary["kernel_context_cache"] is True
    assert summary["source_check_calls"] == 0
    assert summary["context_cache_hits"] >= 2
    assert summary["context_cache_misses"] >= 5

    responses = read_jsonl(out / "responses.jsonl")
    assert [r["action_id"] for r in responses] == ["base_intro_simp", "probe_add_zero", "probe_zero_add"]
    assert all((r["audit_flags"] or {}).get("kernel_context_cache") is True for r in responses)
    assert all((r["audit_flags"] or {}).get("domain_status") == "success" for r in responses)

    plans = read_jsonl(out / "contextual_plan_transitions.jsonl")
    assert len(plans) == 3
    assert any(step["cache_hit"] for row in plans for step in row["plan_steps"])
    cache_rows = read_jsonl(out / "kernel_context_state_cache.jsonl")
    assert cache_rows

    worker_rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    apply_rows = [r for r in worker_rows if r["cmd"] == "apply_tactic"]
    pre_applies = [r for r in apply_rows if r["action"] == "ctx_intro"]
    assert len(pre_applies) == 1
