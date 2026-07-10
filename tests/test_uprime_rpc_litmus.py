from __future__ import annotations

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
