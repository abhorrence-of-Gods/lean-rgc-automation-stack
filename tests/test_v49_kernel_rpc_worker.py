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
from lean_rgc.lean.kernel_rpc_client import U05_BASELINE_OPTIONS
from lean_rgc.lean.kernel_state_identity import state_identity_from_kernel_state


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
    assert 'def failureTransitionStatus (failedStatus replayStatus : String) : String :=' in text
    assert 'if replayStatus != "verified" then "censor"' in text
    assert "def u05MaxHeartbeatsOption : Nat := 20000" in text
    assert 'ensureHeartbeatCapInvariant "prefix step" next' in text
    assert "ensureU05ActionCap base action" in text
    assert "firstHeartbeatCapInvariantError? st.states.toList" in text
    failure_branch = text.split("| .error (failed, msg, replay, targetBinding, budget) =>", 1)[1]
    failure_branch = failure_branch.split('| "shutdown" =>', 1)[0]
    assert "let status := failureTransitionStatus failed.status replayStatus" in failure_branch
    assert '[("normalized_failure_class", Json.str (normalizedFailureClass msg))]' in failure_branch
    assert '[("censor_reason", Json.str "replay_mismatch")]' in failure_branch
    assert "states := stExec.states.insert failed.id failed" not in failure_branch
    assert "let rep ← handleLine ref line" in text
    assert text.count("stdout.putStrLn") == 1

    manifest = native_worker_manifest(tmp_path, exec_mode="kernel_rpc", force=True)
    assert manifest["version"].startswith("lean-rgc-native-worker-v51")
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
    # A legacy task with no declared cap still uses the historical default.
    assert replies[3]["kernel_state"]["options"] == {"maxHeartbeats": "200000"}

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


@pytest.mark.skipif(_lean_bin() is None, reason="Lean binary is not installed")
def test_u05_task_prefix_and_actions_share_the_frozen_heartbeat_cap():
    lean = _lean_bin()
    assert lean is not None
    worker = packaged_kernel_rpc_worker_path()
    proc = subprocess.Popen(
        [lean, "--run", str(worker), "--imports", "Lean"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        encoding="utf-8",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    request_index = 0

    def rpc(cmd: str, **payload: object) -> dict[str, object]:
        nonlocal request_index
        request_index += 1
        request = {"id": f"unit-cap-{request_index}", "cmd": cmd, **payload}
        proc.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
        proc.stdin.flush()
        raw = proc.stdout.readline()
        assert raw, proc.stderr.read() if proc.stderr is not None else "worker exited"
        reply = json.loads(raw)
        assert reply["id"] == request["id"]
        assert reply["rpc_protocol_version"] == "lean-rgc-jsonl-rpc-v2"
        return reply

    try:
        init = rpc(
            "register_task",
            task={
                "task_id": "unit_u05_frozen_cap",
                "statement": "forall n : Nat, n = n",
                "prefix": "intro n",
                "imports": ["Lean"],
                "max_heartbeats": 20_000,
            },
        )
        assert init["ok"] is True
        assert init["state"]["proof_prefix"] == "intro n"
        assert init["kernel_state"]["proof_prefix"] == "intro n"
        assert init["kernel_state"]["options"] == {"maxHeartbeats": "20000"}
        # A prefix-created local can occur in the open target.  Every Expr-DAG
        # free-FVar reference must resolve to the same opaque local-declaration
        # ID namespace before this native payload can enter strict U05 identity.
        strict_identity = state_identity_from_kernel_state(
            init["kernel_state"],
            environment_content_digest="A" * 64,
            baseline_semantic_options=U05_BASELINE_OPTIONS,
        )
        assert strict_identity.status == "open"
        root_state_id = init["state"]["state_id"]

        # A different explicit action cap is rejected before the tactic can
        # mutate or retain a state.  The effective cap remains the task cap.
        bad = rpc(
            "apply_tactic",
            state_id=root_state_id,
            action={
                "action_id": "unit_u05_bad_cap",
                "tactic": "rfl",
                "max_heartbeats": 19_999,
            },
        )
        assert bad["status"] == "failure"
        assert bad["after_state_retained"] is False
        assert bad["replay"]["replay_status"] == "verified"
        assert "U05 cap mismatch" in bad["messages"][0]
        assert bad["budget"]["requested_max_heartbeats_option"] == 19_999
        assert bad["budget"]["effective_max_heartbeats_option"] == 20_000
        assert bad["kernel_state_after"]["options"] == {"maxHeartbeats": "20000"}

        after_bad = rpc("status")
        assert after_bad["ok"] is True
        assert after_bad["n_states"] == 1

        # Omitting the action field exercises inheritance from the stored task
        # option; primary execution and replay therefore use the same cap.
        inherited = rpc(
            "apply_tactic",
            state_id=root_state_id,
            action={"action_id": "unit_u05_inherited_cap", "tactic": "rfl"},
        )
        assert inherited["status"] == "success"
        assert inherited["replay"]["replay_status"] == "verified"
        assert inherited["budget"]["requested_max_heartbeats_option"] is None
        assert inherited["budget"]["effective_max_heartbeats_option"] == 20_000
        assert inherited["budget"]["effective_max_heartbeats_counter"] == 20_000_000
        assert inherited["budget"]["source"] == "inherited_state"
        assert inherited["kernel_state_before"]["options"] == {
            "maxHeartbeats": "20000"
        }
        assert inherited["kernel_state_after"]["options"] == {
            "maxHeartbeats": "20000"
        }

        final_status = rpc("status")
        assert final_status["ok"] is True
        assert final_status["n_states"] == 2
        assert rpc("shutdown")["shutdown"] is True
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=30)


@pytest.mark.skipif(_lean_bin() is None, reason="Lean binary is not installed")
def test_u05_rpc_routes_non_head_deltas_replays_and_discards():
    lean = _lean_bin()
    assert lean is not None
    worker = packaged_kernel_rpc_worker_path()
    proc = subprocess.Popen(
        [lean, "--run", str(worker), "--imports", "Lean"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        encoding="utf-8",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    request_index = 0

    def rpc(cmd: str, **payload: object) -> dict[str, object]:
        nonlocal request_index
        request_index += 1
        request = {"id": f"u05-{request_index}", "cmd": cmd, **payload}
        proc.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
        proc.stdin.flush()
        raw = proc.stdout.readline()
        assert raw, proc.stderr.read() if proc.stderr is not None else "worker exited"
        reply = json.loads(raw)
        assert reply["id"] == request["id"]
        assert reply["rpc_protocol_version"] == "lean-rgc-jsonl-rpc-v2"
        return reply

    try:
        init = rpc(
            "init_state",
            task={
                "task_id": "unit_u05_non_head",
                "statement": "True ∧ True",
                "imports": ["Lean"],
                "max_heartbeats": 20_000,
            },
        )
        root_state_id = init["state"]["state_id"]
        root_goal_id = init["kernel_state"]["goals"][0]["mvar_id"]
        split = rpc(
            "apply_tactic",
            state_id=root_state_id,
            action={
                "action_id": "unit_u05_constructor_first",
                "tactic": "constructor",
                "target_selector": "first",
                "max_heartbeats": 20_000,
            },
        )
        assert split["status"] == "partial"
        assert split["after_state_retained"] is True
        split_goals = [row["mvar_id"] for row in split["kernel_state_after"]["goals"]]
        assert len(split_goals) == 2
        assert root_goal_id in split["state_delta"]["assigned_mvars"]
        assert split["replay"]["replay_status"] == "verified"
        assert split["replay"]["reexecution_performed"] is True
        assert split["replay"]["primary_comparable"] == split["replay"]["replay_comparable"]
        assert split["budget"] == {
            "requested_max_heartbeats_option": 20_000,
            "effective_max_heartbeats_option": 20_000,
            "effective_max_heartbeats_counter": 20_000_000,
            "unlimited": False,
            "source": "explicit_action",
            "cache_policy": "bypass",
            "cache_lookup_performed": False,
            "consumption_reported": False,
            "episode_budget": "NOT_ENFORCED_DEVELOPMENT_ONLY",
        }

        head_goal, tail_goal = split_goals
        tail = rpc(
            "apply_tactic",
            state_id=split["after_state_id"],
            action={
                "action_id": "unit_u05_exact_tail",
                "tactic": "exact True.intro",
                "target_selector": "last",
                "max_heartbeats": 20_000,
            },
        )
        assert tail["status"] == "partial"
        assert tail["target_binding"]["effective_target_goal_index"] == 1
        assert tail["target_binding"]["effective_target_mvar_id"] == tail_goal
        assert tail["target_binding"]["source"] == "action_target_selector"
        assert [row["mvar_id"] for row in tail["kernel_state_after"]["goals"]] == [head_goal]
        # The assigned root remains in the mctx, but the transition delta is a
        # true before/after difference and therefore reports only this tail.
        assert tail_goal in tail["state_delta"]["assigned_mvars"]
        assert root_goal_id not in tail["state_delta"]["assigned_mvars"]
        assert root_goal_id in tail["state_delta"]["before_assigned_mvars"]
        assert root_goal_id in tail["state_delta"]["after_assigned_mvars"]
        assert tail["replay"]["replay_status"] == "verified"

        side_init = rpc(
            "init_state",
            task={
                "task_id": "unit_u05_tail_sweep",
                "statement": "∃ n : Nat, n = 0",
                "prefix": "refine ⟨?_, ?_⟩",
                "imports": ["Lean"],
                "max_heartbeats": 20_000,
            },
        )
        side_goals = [row["mvar_id"] for row in side_init["kernel_state"]["goals"]]
        assert len(side_goals) == 2
        side = rpc(
            "apply_tactic",
            state_id=side_init["state"]["state_id"],
            target_mvar_id=side_goals[1],
            action={
                "action_id": "unit_u05_side_effect_rfl",
                "tactic": "rfl",
                "max_heartbeats": 20_000,
            },
        )
        assert side["status"] == "success"
        assert side["kernel_state_after"]["goals"] == []
        assert set(side["state_delta"]["assigned_mvars"]) == set(side_goals)
        assert set(side["state_delta"]["closed_goals"]) == set(side_goals)

        before_failure = rpc("status")
        failed = rpc(
            "apply_tactic",
            state_id=tail["after_state_id"],
            action={
                "action_id": "unit_u05_inapplicable",
                "tactic": "exact False.elim",
                "target_selector": "first",
                "max_heartbeats": 20_000,
            },
        )
        assert failed["status"] == "failure"
        assert failed["normalized_failure_class"] == "ordinary_failure"
        assert failed["after_state_retained"] is False
        assert failed["replay"]["replay_status"] == "verified"
        assert rpc("status")["n_states"] == before_failure["n_states"]

        before_discard = rpc("status")
        assert before_discard["n_primary_executions"] == 4
        assert before_discard["n_replay_executions"] == 4
        # Every replay is transient: only initial/primary states are live.
        assert before_discard["n_states"] == 5
        discarded = rpc("discard_state", state_id=tail["after_state_id"])
        assert discarded["discarded"] is True
        assert discarded["n_states_after"] == discarded["n_states_before"] - 1
        missing = rpc("get_state", state_id=tail["after_state_id"])
        assert missing["ok"] is False
        assert rpc("status")["n_states"] == 4
        assert rpc("shutdown")["shutdown"] is True
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=30)
