from __future__ import annotations

import sys

import pytest

from lean_rgc.evals import uprime_rpc_litmus as litmus
from lean_rgc.evals.uprime_rpc_litmus import (
    _publish_reserved_json,
    _reserve_output,
    budget_evidence,
    cache_budget_probe,
    delta_evidence,
    independent_delta,
    replay_evidence,
    select_side_effect_target,
    state_view,
)
from lean_rgc.lean.worker_supervisor import audit_cache_eligibility
from lean_rgc.lean.executor import LeanExecutorConfig
from lean_rgc.lean import worker_supervisor


def _kernel(goals, rows, state_id="state"):
    return {
        "schema_version": "synthetic-kernel-state-v1",
        "state_id": state_id,
        "state_hash_raw": f"raw-{state_id}",
        "state_hash_norm": f"norm-{state_id}",
        "options": {"maxHeartbeats": "731"},
        "goals": [{"mvar_id": goal} for goal in goals],
        "metavars": [
            {"mvar_id": mvar_id, "assigned": assigned}
            for mvar_id, assigned in rows
        ],
    }


def test_independent_delta_rejects_cumulative_assignment_reporting():
    before = _kernel(
        ["?a", "?b"],
        [("?root", True), ("?a", False), ("?b", False)],
        "before",
    )
    after = _kernel(
        ["?b"],
        [("?root", True), ("?a", True), ("?b", False), ("?fresh", False)],
        "after",
    )
    expected = {
        "closed_goals": ["?a"],
        "new_goals": [],
        "assigned_mvars": ["?a"],
        "new_mvars": ["?fresh"],
    }
    assert independent_delta(before, after) == expected

    correct = {
        "before_state_id": "before",
        "after_state_id": "after",
        "kernel_state_before": before,
        "kernel_state_after": after,
        "state_delta": expected,
    }
    assert delta_evidence(correct)["passed"] is True

    cumulative = {
        **correct,
        "state_delta": {**expected, "assigned_mvars": ["?root", "?a"]},
    }
    evidence = delta_evidence(cumulative)
    assert evidence["passed"] is False
    assert evidence["matches"]["assigned_mvars"] is False


def test_delta_oracle_rejects_assigned_goal_left_open():
    view = state_view(_kernel(["?a"], [("?a", True)]))
    assert view["assigned_open_goals"] == ["?a"]

    response = {
        "before_state_id": "before",
        "after_state_id": "after",
        "kernel_state_before": _kernel(["?a"], [("?a", False)], "before"),
        "kernel_state_after": _kernel(["?a"], [("?a", True)], "after"),
        "state_delta": {
            "closed_goals": ["?a"],
            "new_goals": [],
            "assigned_mvars": ["?a"],
            "new_mvars": [],
        },
    }
    assert delta_evidence(response)["passed"] is False


def test_delta_oracle_rejects_missing_kernel_states():
    response = {
        "before_state_id": "before",
        "after_state_id": "after",
        "state_delta": {
            "closed_goals": [],
            "new_goals": [],
            "assigned_mvars": [],
            "new_mvars": [],
        },
    }
    assert delta_evidence(response)["passed"] is False


def test_side_effect_selector_uses_frozen_second_refine_goal_not_relation_marker():
    kernel = _kernel(
        ["?witness", "?proof"],
        [("?witness", False), ("?proof", False)],
        "side",
    )
    kernel["goals"][0]["relation"] = ""
    kernel["goals"][1]["relation"] = ""
    assert select_side_effect_target(kernel) == "?proof"

    kernel["goals"] = kernel["goals"][:1]
    with pytest.raises(RuntimeError, match="exactly two distinct ordered goal rows"):
        select_side_effect_target(kernel)

    kernel["goals"] = [
        {"bad": "filtered-by-state-view"},
        {"mvar_id": "?witness"},
        {"mvar_id": "?proof"},
    ]
    with pytest.raises(RuntimeError, match="exactly two distinct ordered goal rows"):
        select_side_effect_target(kernel)

    kernel["goals"] = [{"mvar_id": "?witness"}, {"bad": "missing-id"}]
    with pytest.raises(RuntimeError, match="exactly two distinct ordered goal rows"):
        select_side_effect_target(kernel)


def _budget_response(
    option=731,
    counter=731000,
    unlimited=False,
    *,
    source="task",
    consumed=17,
    remaining=999_983,
):
    budget = {
        "effective_max_heartbeats_option": option,
        "effective_max_heartbeats_counter": counter,
        "unlimited": unlimited,
        "source": source,
        "consumed_heartbeats_counter": consumed,
        "episode_max_heartbeats_counter": 1_000_000,
        "episode_remaining_heartbeats_counter": remaining,
        "episode_source": "task",
        "measurement_scope": "action_corem_toio_counter",
        "reset_scope": "per_corem_toio_call",
    }
    return {
        "budget": budget,
        "heartbeats": consumed,
        "audit": {
            "heartbeats": consumed,
            "audit_flags": {"heartbeat_telemetry": dict(budget)},
        },
    }


def test_budget_oracle_requires_dual_units_and_mirrored_counter():
    assert budget_evidence(_budget_response())["passed"] is True
    assert budget_evidence(
        _budget_response(option=0, counter=None, unlimited=True)
    )["passed"] is True

    wrong_scale = _budget_response(counter=731)
    evidence = budget_evidence(wrong_scale)
    assert evidence["passed"] is False
    assert evidence["cap_consistent"] is False

    wrong_scale["audit"]["audit_flags"]["heartbeat_telemetry"] = {
        **wrong_scale["budget"],
        "consumed_heartbeats_counter": 18,
    }
    evidence = budget_evidence(wrong_scale)
    assert evidence["mirror_match"] is False


def test_replay_oracle_rejects_bare_verified_claim():
    before = _kernel(["?goal"], [("?goal", False)], "before")
    after = _kernel([], [("?goal", True)], "after")
    delta = {
        "closed_goals": ["?goal"],
        "new_goals": [],
        "assigned_mvars": ["?goal"],
        "new_mvars": [],
    }
    certificate = {
        "schema_version": "lean-rgc-kernel-replay-certificate-v1",
        "verification_method": "same_before_state_independent_reexecution",
        "replay_status": "verified",
        "state_match": True,
        "delta_match": True,
        "error": None,
    }
    primary = {
        "before_state_id": "before",
        "after_state_id": "after",
        "kernel_state_before": before,
        "kernel_state_after": after,
        "state_delta": delta,
    }
    kwargs = {
        "before_state_id": "before",
        "expected_after_state_id": "after",
        "action_id": "close",
        "target_mvar_id": "?goal",
    }
    bare = {"replay_certificate": {"replay_status": "verified"}}
    assert replay_evidence(primary, bare, **kwargs)["passed"] is False

    replay = {
        "ok": True,
        "before_state_id": "before",
        "expected_after_state_id": "after",
        "action_id": "close",
        "target_mvar_id": "?goal",
        "n_states_before": 2,
        "n_states_after": 2,
        "reexecution_performed": True,
        "reexecution_heartbeats_counter": 3,
        "reexecution_scope": "fresh_from_immutable_before_state",
        "kernel_state_before": before,
        "kernel_state_expected": after,
        "kernel_state_observed": after,
        "state_delta_expected": delta,
        "state_delta_observed": delta,
        "replay_certificate": certificate,
    }
    assert replay_evidence(primary, replay, **kwargs)["passed"] is True

    replay["kernel_state_observed"] = {**after, "state_hash_raw": "different"}
    assert replay_evidence(primary, replay, **kwargs)["passed"] is False


def test_cache_probe_preserves_zero_and_exposes_missing_default_alignment():
    probe = cache_budget_probe()
    assert probe["checks"]["task_fallback"] is True
    assert probe["checks"]["explicit_zero"] is True
    assert probe["checks"]["explicit_nonzero"] is True
    assert probe["resolved"]["omitted_default"] == ""
    assert probe["checks"]["omitted_runtime_default"] is False
    assert probe["passed"] is False


def test_stateful_kernel_rpc_cache_is_hard_disabled():
    by_lane = audit_cache_eligibility(
        backend="kernel_rpc_file",
        lane="kernel_rpc",
    )
    assert by_lane == {
        "eligible": False,
        "reason": "stateful_kernel_rpc_key_lacks_before_frame_target_and_protocol",
        "backend": "kernel_rpc_file",
        "lane": "kernel_rpc",
    }
    assert audit_cache_eligibility(
        backend="source_check_bulk",
        lane="source_check",
    )["eligible"] is True


def test_stateful_kernel_rpc_supervisor_never_calls_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_supervisor, "project_fingerprint", lambda **_kwargs: "fp")
    monkeypatch.setattr(worker_supervisor, "workdir_fingerprint", lambda _path: "wd")
    monkeypatch.setattr(
        worker_supervisor,
        "enqueue_audit_jobs",
        lambda *_args, **_kwargs: {"n_enqueued": 0},
    )
    monkeypatch.setattr(
        worker_supervisor,
        "run_supervised_audit_queue",
        lambda **_kwargs: {"n_succeeded": 0, "n_cache_hit": 99},
    )

    def forbidden(**_kwargs):
        raise AssertionError("stateful kernel RPC touched the legacy audit cache")

    monkeypatch.setattr(worker_supervisor, "apply_cache_to_queue", forbidden)
    monkeypatch.setattr(worker_supervisor, "store_queue_results_in_cache", forbidden)
    summary = worker_supervisor.enqueue_and_run_supervised_audit(
        db_path=tmp_path / "queue.sqlite",
        tasks=[],
        actions_by_task=[],
        out_dir=tmp_path / "out",
        executor_config=LeanExecutorConfig(),
        run_id="uprime-cache-guard",
        backend="kernel_rpc_file",
        import_mode="preserve",
        lane="kernel_rpc",
        audit_cache_db=tmp_path / "cache.sqlite",
    )
    assert summary["audit_cache"]["enabled"] is False
    assert summary["audit_cache"]["cache_eligible"] is False
    assert summary["n_cache_hit"] == 0
    assert not (tmp_path / "cache.sqlite").exists()


def test_canonical_artifact_is_reserved_before_atomic_publication(tmp_path):
    path = tmp_path / "rpc_diagnostic_0123456789ab.json"
    reservation_path = path.with_name(f"{path.name}.reservation")
    commit = "0123456789abcdef0123456789abcdef01234567"
    token = _reserve_output(path, anchor="0123456789ab", commit=commit)
    reservation = reservation_path.read_text(encoding="utf-8")
    assert "LIVE_EXECUTION_RESERVED" in reservation
    with pytest.raises(FileExistsError):
        _reserve_output(path, anchor="0123456789ab", commit=commit)

    report = {"verdict": "U1_DIAGNOSTIC_BLOCKED", "licenses_later_stage": False}
    _publish_reserved_json(
        path,
        report,
        token=token,
        anchor="0123456789ab",
        commit=commit,
    )
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert "U1_DIAGNOSTIC_BLOCKED" in path.read_text(encoding="utf-8")
    assert reservation_path.exists()
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("timeout_s", [0.0, 899.0, 901.0, float("nan"), float("inf")])
def test_live_diagnostic_rejects_nonfrozen_timeout_before_preflight(timeout_s):
    with pytest.raises(ValueError, match="frozen value 900"):
        litmus.run_diagnostic(".", anchor="000000000000", timeout_s=timeout_s)


class _FinishedReader:
    def __init__(self, *, alive=False):
        self.alive = alive
        self.join_timeouts = []

    def join(self, timeout=None):
        self.join_timeouts.append(timeout)

    def is_alive(self):
        return self.alive


class _ScriptedProcess:
    def __init__(
        self,
        *,
        natural_returncode=0,
        require_terminate=False,
        require_kill=False,
        survive_kill=False,
    ):
        self.returncode = None
        self.natural_returncode = natural_returncode
        self.require_terminate = require_terminate
        self.require_kill = require_kill
        self.survive_kill = survive_kill
        self.terminated = False
        self.killed = False
        self.wait_timeouts = []

    def wait(self, timeout=None):
        self.wait_timeouts.append(timeout)
        if self.require_terminate:
            may_exit = self.killed or (self.terminated and not self.require_kill)
            if self.survive_kill or not may_exit:
                raise litmus.subprocess.TimeoutExpired("fake-uprime-worker", timeout)
        self.returncode = 1 if self.require_terminate else self.natural_returncode
        return self.returncode

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def _rpc_finalize_shell(process, *, reader_alive=False):
    rpc = object.__new__(litmus._RpcProcess)
    rpc.process = process
    rpc.stdout_queue = litmus.queue.Queue(maxsize=32)
    rpc.stdout_queue.put_nowait(("eof", None, None))
    rpc.non_json_stdout = litmus.deque(maxlen=20)
    rpc.non_json_stdout_count = 0
    rpc.stderr_lines = litmus.deque(maxlen=40)
    rpc.stderr_count = 0
    rpc.transport_overflow = False
    rpc._cleanup_deadline = None
    rpc._post_response_started = None
    rpc._post_response_deadline = None
    rpc.shutdown_lifecycle = litmus._new_shutdown_lifecycle()
    rpc._stdout_thread = _FinishedReader(alive=reader_alive)
    rpc._stderr_thread = _FinishedReader()
    return rpc


def _finalize(rpc, response, *, received_monotonic_s=None):
    if received_monotonic_s is None:
        received_monotonic_s = litmus.time.monotonic()
    return rpc.finalize_after_shutdown(
        response,
        received_monotonic_s=received_monotonic_s,
    )


def test_shutdown_transport_graceful_exit_is_clear_eligible_and_auditable():
    process = _ScriptedProcess()
    rpc = _rpc_finalize_shell(process)
    shutdown = {"id": "uprime-23-shutdown", "ok": True, "shutdown": True}
    _finalize(rpc, shutdown)
    transport = rpc.transport_summary()
    gate = litmus.shutdown_transport_clear_gate(shutdown, transport)
    assert gate["passed"] is True
    assert len(process.wait_timeouts) == 1
    assert 0 < process.wait_timeouts[0] <= litmus.NATURAL_EXIT_GRACE_S
    assert transport["shutdown_lifecycle"]["transport_finalized"] is True
    assert transport["shutdown_lifecycle"]["stdout_eof_count"] == 1
    assert (
        litmus.NATURAL_EXIT_GRACE_S
        + litmus.FORCED_REAP_BUDGET_S
        + litmus.READER_DRAIN_RESERVE_S
        == litmus.POST_RESPONSE_TIMEOUT_S
    )

    status_summary = litmus._response_summary(
        {"ok": True, "loaded": True, "n_states": 13, "n_requests": 22},
        {
            "frame_index": 22,
            "received_at_utc": "2026-07-10T00:00:00+00:00",
            "response_sha256": "deliberately-different",
        },
    )
    shutdown_summary = litmus._response_summary(
        shutdown,
        {
            "frame_index": 23,
            "received_at_utc": "2026-07-10T00:00:01+00:00",
            "response_sha256": litmus._stable_json_sha256(shutdown),
        },
    )
    assert status_summary["loaded"] is True
    assert status_summary["n_states"] == 13
    assert status_summary["n_requests"] == 22
    assert status_summary["frame_index"] == 22
    assert status_summary["receipt_sha256_match"] is False
    assert shutdown_summary["shutdown"] is True
    assert shutdown_summary["frame_index"] == 23
    assert shutdown_summary["receipt_sha256_match"] is True

    transport["shutdown_lifecycle"]["post_response_elapsed_s"] = 10.1
    late_gate = litmus.shutdown_transport_clear_gate(shutdown, transport)
    assert late_gate["checks"]["post_response_elapsed_bounded"] is False
    assert late_gate["passed"] is False


def test_real_reader_queue_receipt_and_graceful_shutdown(tmp_path):
    child = (
        "import json,sys\n"
        "request=json.loads(sys.stdin.readline())\n"
        "reply={'id':request.get('id'),'ok':True,'shutdown':True}\n"
        "sys.stdout.write(json.dumps(reply,separators=(',',':'))+'\\n')\n"
        "sys.stdout.flush()\n"
    )
    rpc = litmus._RpcProcess(
        [sys.executable, "-c", child],
        cwd=tmp_path,
        timeout_s=30.0,
    )
    try:
        response, receipt = rpc.request({"id": "real-reader", "cmd": "shutdown"})
        assert response == {"id": "real-reader", "ok": True, "shutdown": True}
        assert receipt["received_monotonic_s"] <= litmus.time.monotonic()
        assert receipt["received_at_utc"].endswith("+00:00")
        rpc.finalize_after_shutdown(
            response,
            received_monotonic_s=receipt["received_monotonic_s"],
        )
        transport = rpc.transport_summary()
        assert transport["shutdown_lifecycle"]["terminal_eof_exact"] is True
        assert litmus.shutdown_transport_clear_gate(response, transport)["passed"] is True
    finally:
        if rpc.process.poll() is None:
            rpc.abort()


def test_forced_reap_allows_contract_aggregation_but_never_clear():
    process = _ScriptedProcess(require_terminate=True)
    rpc = _rpc_finalize_shell(process)
    shutdown = {"ok": True, "shutdown": True, "error": None}
    _finalize(rpc, shutdown)
    transport = rpc.transport_summary()
    lifecycle = transport["shutdown_lifecycle"]
    assert lifecycle["forced_reap"] is True
    assert lifecycle["forced_reap_succeeded"] is True
    assert lifecycle["exit_mode"] == "forced_terminate"
    assert transport["returncode"] == 1

    gate = litmus.shutdown_transport_clear_gate(shutdown, transport)
    assert gate["passed"] is False
    contracts = {name: {"passed": True} for name in litmus.CONTRACT_IDS}
    disposition = litmus.diagnostic_disposition(contracts, gate)
    assert disposition["contract_failures"] == []
    assert disposition["failures"] == [litmus.TRANSPORT_CLEAR_GATE_ID]
    assert disposition["verdict"] == "U1_DIAGNOSTIC_BLOCKED"
    lifecycle_before_abort = dict(lifecycle)
    rpc.abort()
    assert rpc.shutdown_lifecycle == lifecycle_before_abort


def test_forced_reap_escalates_to_kill_inside_registered_budget():
    process = _ScriptedProcess(require_terminate=True, require_kill=True)
    rpc = _rpc_finalize_shell(process)
    shutdown = {"ok": True, "shutdown": True}
    _finalize(rpc, shutdown)
    lifecycle = rpc.shutdown_lifecycle
    assert lifecycle["termination_signal_attempted"] is True
    assert lifecycle["kill_signal_attempted"] is True
    assert lifecycle["exit_mode"] == "forced_kill"
    assert lifecycle["forced_reap_succeeded"] is True


def test_forced_reap_failure_is_harness_error():
    process = _ScriptedProcess(
        require_terminate=True,
        require_kill=True,
        survive_kill=True,
    )
    rpc = _rpc_finalize_shell(process)
    with pytest.raises(TimeoutError, match="survived bounded"):
        _finalize(rpc, {"ok": True, "shutdown": True})
    assert rpc.shutdown_lifecycle["forced_reap"] is True
    assert rpc.shutdown_lifecycle["forced_reap_succeeded"] is False
    assert rpc.shutdown_lifecycle["transport_finalized"] is False


def test_invalid_shutdown_that_requires_force_is_harness_error():
    rpc = _rpc_finalize_shell(_ScriptedProcess(require_terminate=True))
    with pytest.raises(RuntimeError, match="invalid shutdown response"):
        _finalize(rpc, {"ok": True, "shutdown": False})
    assert rpc.shutdown_lifecycle["forced_reap"] is True
    assert rpc.shutdown_lifecycle["transport_finalized"] is False


def test_invalid_shutdown_with_natural_exit_is_evaluated_but_cannot_clear():
    rpc = _rpc_finalize_shell(_ScriptedProcess())
    shutdown = {"ok": True, "shutdown": False}
    _finalize(rpc, shutdown)
    gate = litmus.shutdown_transport_clear_gate(shutdown, rpc.transport_summary())
    assert gate["checks"]["shutdown_ack_ok"] is False
    assert gate["passed"] is False


def test_shutdown_transport_rejects_nonzero_natural_exit_after_drain():
    rpc = _rpc_finalize_shell(_ScriptedProcess(natural_returncode=7))
    with pytest.raises(RuntimeError, match="naturally with return code 7"):
        _finalize(rpc, {"ok": True, "shutdown": True})
    assert rpc.shutdown_lifecycle["terminal_eof_exact"] is True
    assert rpc.shutdown_lifecycle["transport_finalized"] is False


@pytest.mark.parametrize(
    "pollution", ["extra_response", "duplicate_eof", "overflow", "non_json"]
)
def test_shutdown_transport_pollution_is_harness_error(pollution):
    rpc = _rpc_finalize_shell(_ScriptedProcess())
    if pollution == "extra_response":
        rpc.stdout_queue.put_nowait(
            ("response", {"unexpected": True}, {"received_monotonic_s": 0.0})
        )
    elif pollution == "duplicate_eof":
        rpc.stdout_queue.put_nowait(("eof", None, None))
    elif pollution == "overflow":
        rpc.transport_overflow = True
    else:
        rpc.non_json_stdout_count += 1
        rpc.non_json_stdout.append("pollution")
    with pytest.raises(RuntimeError):
        _finalize(rpc, {"ok": True, "shutdown": True})
    assert rpc.shutdown_lifecycle["transport_finalized"] is False


def test_shutdown_transport_reader_survival_is_harness_error():
    rpc = _rpc_finalize_shell(_ScriptedProcess(), reader_alive=True)
    with pytest.raises(RuntimeError, match="reader did not terminate"):
        _finalize(rpc, {"ok": True, "shutdown": True})
    assert rpc.shutdown_lifecycle["reader_threads_drained"] is False


def test_shutdown_receipt_clock_prevents_late_natural_false_clear():
    process = _ScriptedProcess()
    process.returncode = 0
    rpc = _rpc_finalize_shell(process)
    shutdown = {"ok": True, "shutdown": True}
    _finalize(
        rpc,
        shutdown,
        received_monotonic_s=litmus.time.monotonic() - 6.0,
    )
    lifecycle = rpc.shutdown_lifecycle
    assert lifecycle["exit_mode"] == "natural_after_grace"
    assert lifecycle["graceful_exit"] is False
    gate = litmus.shutdown_transport_clear_gate(shutdown, rpc.transport_summary())
    assert gate["checks"]["natural_exit_within_grace"] is False
    assert gate["passed"] is False


def test_post_response_elapsed_is_measured_before_finalization(monkeypatch):
    ticks = iter([0.0, 0.0, 0.0, 0.0, 0.0, 11.0])
    monkeypatch.setattr(litmus.time, "monotonic", lambda: next(ticks))
    rpc = _rpc_finalize_shell(_ScriptedProcess())
    with pytest.raises(TimeoutError, match="post-response deadline expired"):
        _finalize(
            rpc,
            {"ok": True, "shutdown": True},
            received_monotonic_s=0.0,
        )
    assert rpc.shutdown_lifecycle["post_response_elapsed_s"] == 11.0
    assert rpc.shutdown_lifecycle["transport_finalized"] is False


@pytest.mark.parametrize("variant", ["empty", "missing", "extra", "reordered"])
def test_diagnostic_disposition_rejects_contract_registry_drift(variant):
    contracts = {name: {"passed": True} for name in litmus.CONTRACT_IDS}
    if variant == "empty":
        contracts = {}
    elif variant == "missing":
        contracts.pop(litmus.CONTRACT_IDS[-1])
    elif variant == "extra":
        contracts["unexpected"] = {"passed": True}
    else:
        contracts = dict(reversed(list(contracts.items())))
    with pytest.raises(ValueError, match="contract registry"):
        litmus.diagnostic_disposition(contracts, {"passed": True})


def test_diagnostic_disposition_rejects_nonobject_contract_row():
    contracts = {name: {"passed": True} for name in litmus.CONTRACT_IDS}
    contracts[litmus.CONTRACT_IDS[0]] = True
    with pytest.raises(TypeError, match="contract rows"):
        litmus.diagnostic_disposition(contracts, {"passed": True})


@pytest.mark.parametrize(
    "variant", ["wrong_id", "missing", "extra", "reordered", "contradiction"]
)
def test_diagnostic_disposition_rejects_transport_gate_drift(variant):
    contracts = {name: {"passed": True} for name in litmus.CONTRACT_IDS}
    checks = {name: True for name in litmus.TRANSPORT_CLEAR_CHECK_IDS}
    gate = {
        "gate_id": litmus.TRANSPORT_CLEAR_GATE_ID,
        "passed": True,
        "checks": checks,
    }
    if variant == "wrong_id":
        gate["gate_id"] = "wrong"
    elif variant == "missing":
        checks.pop(litmus.TRANSPORT_CLEAR_CHECK_IDS[-1])
    elif variant == "extra":
        checks["unexpected"] = True
    elif variant == "reordered":
        gate["checks"] = dict(reversed(list(checks.items())))
    else:
        checks[litmus.TRANSPORT_CLEAR_CHECK_IDS[0]] = False
    with pytest.raises(ValueError, match="transport clear gate"):
        litmus.diagnostic_disposition(contracts, gate)


def test_all_contracts_have_a_reachable_clear_fixture(monkeypatch):
    def transition(
        before,
        after,
        *,
        status,
        option,
        source,
        consumed,
        remaining,
    ):
        budget = _budget_response(
            option=option,
            counter=None if option == 0 else option * 1000,
            unlimited=option == 0,
            source=source,
            consumed=consumed,
            remaining=remaining,
        )
        delta = independent_delta(before, after)
        budget.update(
            {
                "ok": True,
                "status": status,
                "before_state_id": before["state_id"],
                "after_state_id": after["state_id"],
                "kernel_state_before": before,
                "kernel_state_after": after,
                "state_delta": delta,
            }
        )
        budget["audit"]["status"] = "timeout" if status == "timeout" else status
        return budget

    def replay(primary, *, action_id, target):
        return {
            "ok": True,
            "before_state_id": primary["before_state_id"],
            "expected_after_state_id": primary["after_state_id"],
            "action_id": action_id,
            "target_mvar_id": target,
            "n_states_before": 7,
            "n_states_after": 7,
            "reexecution_performed": True,
            "reexecution_heartbeats_counter": 5,
            "reexecution_scope": "fresh_from_immutable_before_state",
            "kernel_state_before": primary["kernel_state_before"],
            "kernel_state_expected": primary["kernel_state_after"],
            "kernel_state_observed": primary["kernel_state_after"],
            "state_delta_expected": primary["state_delta"],
            "state_delta_observed": primary["state_delta"],
            "replay_certificate": {
                "schema_version": "lean-rgc-kernel-replay-certificate-v1",
                "verification_method": "same_before_state_independent_reexecution",
                "replay_status": "verified",
                "state_match": True,
                "delta_match": True,
                "error": None,
            },
        }

    p0 = _kernel(["?pr"], [("?pr", False)], "p0")
    p1 = _kernel(
        ["?ph", "?pt"],
        [("?pr", True), ("?ph", False), ("?pt", False)],
        "p1",
    )
    p2 = _kernel(
        ["?ph"],
        [("?pr", True), ("?ph", False), ("?pt", True)],
        "p2",
    )
    p3 = _kernel(
        [],
        [("?pr", True), ("?ph", True), ("?pt", True)],
        "p3",
    )
    z0 = _kernel(["?zr"], [("?zr", False)], "z0")
    z1 = _kernel(
        ["?zh", "?zt"],
        [("?zr", True), ("?zh", False), ("?zt", False)],
        "z1",
    )
    z2 = _kernel(
        ["?zh"],
        [("?zr", True), ("?zh", False), ("?zt", True)],
        "z2",
    )
    s0 = _kernel(
        ["?sw", "?se"],
        [("?sr", True), ("?sw", False), ("?se", False)],
        "s0",
    )
    s1 = _kernel(
        [],
        [("?sr", True), ("?sw", True), ("?se", True)],
        "s1",
    )
    b0 = _kernel(["?b"], [("?b", False)], "b0")
    b1 = _kernel(["?b"], [("?b", False)], "b1")
    b1["state_hash_norm"] = b0["state_hash_norm"]
    r0 = _kernel(["?r"], [("?r", False)], "r0")
    r1 = _kernel([], [("?r", True)], "r1")

    responses = {
        "load": {"ok": True, "loaded": True},
        "primary_init": {"ok": True, "state": {"state_id": "p0"}, "kernel_state": p0},
        "primary_split": transition(
            p0,
            p1,
            status="partial",
            option=123_456,
            source="action",
            consumed=10,
            remaining=999_990,
        ),
        "primary_tail_close": transition(
            p1,
            p2,
            status="partial",
            option=731,
            source="task",
            consumed=11,
            remaining=999_979,
        ),
        "primary_head_close": transition(
            p2,
            p3,
            status="success",
            option=731,
            source="task",
            consumed=12,
            remaining=999_967,
        ),
        "zero_init": {"ok": True, "state": {"state_id": "z0"}, "kernel_state": z0},
        "zero_split": transition(
            z0,
            z1,
            status="partial",
            option=0,
            source="action",
            consumed=13,
            remaining=999_987,
        ),
        "zero_child_close": transition(
            z1,
            z2,
            status="partial",
            option=731,
            source="task",
            consumed=14,
            remaining=999_973,
        ),
        "side_init": {"ok": True, "state": {"state_id": "s0"}, "kernel_state": s0},
        "side_effect_close": transition(
            s0,
            s1,
            status="success",
            option=731,
            source="task",
            consumed=15,
            remaining=999_985,
        ),
        "burn_init": {"ok": True, "state": {"state_id": "b0"}, "kernel_state": b0},
        "burn": transition(
            b0,
            b1,
            status="timeout",
            option=200_000,
            source="action",
            consumed=400_000_000,
            remaining=0,
        ),
        "reset_init": {"ok": True, "state": {"state_id": "r0"}, "kernel_state": r0},
        "reset": transition(
            r0,
            r1,
            status="success",
            option=200_000,
            source="action",
            consumed=16,
            remaining=999_984,
        ),
        "status": {
            "ok": True,
            "loaded": True,
            "n_states": 13,
            "n_requests": 22,
        },
        "shutdown": {"ok": True, "shutdown": True},
    }
    action_specs = {
        "primary_split": ("primary_constructor", None),
        "primary_tail_close": ("primary_tail_exact", "?pt"),
        "primary_head_close": ("primary_head_exact", "?ph"),
        "zero_split": ("zero_constructor", None),
        "zero_child_close": ("zero_child_exact", "?zt"),
        "side_effect_close": ("side_effect_rfl", "?se"),
        "reset": ("reset_trivial", None),
    }
    replay_specs = {}
    for label, (action_id, target) in action_specs.items():
        replay_label = f"{label}_replay"
        responses[replay_label] = replay(
            responses[label],
            action_id=action_id,
            target=target,
        )
        replay_specs[label] = {
            "replay_label": replay_label,
            "before_state_id": responses[label]["before_state_id"],
            "expected_after_state_id": responses[label]["after_state_id"],
            "action_id": action_id,
            "target_mvar_id": target,
        }

    request_ids = {}
    for index, (label, response) in enumerate(responses.items(), start=1):
        request_id = f"synthetic-{index:02d}-{label}"
        request_ids[label] = request_id
        response["id"] = request_id
        response["rpc_protocol_version"] = "lean-rgc-jsonl-rpc-v2"
    context = {
        "primary_head": "?ph",
        "primary_tail": "?pt",
        "zero_goals": ["?zh", "?zt"],
        "side_goals": ["?sw", "?se"],
        "side_equality_goal": "?se",
        "side_target_selector": "refine_tuple_position_1",
        "requested_state_ids": {
            label: responses[label]["before_state_id"]
            for label in (
                "primary_split",
                "primary_tail_close",
                "primary_head_close",
                "zero_split",
                "zero_child_close",
                "side_effect_close",
                "burn",
                "reset",
            )
        },
        "replay_specs": replay_specs,
    }
    monkeypatch.setattr(
        litmus,
        "cache_budget_probe",
        lambda: {"passed": True, "resolved": {}, "checks": {}},
    )
    contracts = litmus.evaluate_contracts(responses, request_ids, context)
    assert {name: row["passed"] for name, row in contracts.items()} == {
        name: True for name in litmus.CONTRACT_IDS
    }
