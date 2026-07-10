"""Imported adversarial cases for the phase-1b2 exact-49 contract oracle.

The filename intentionally does not match pytest's default collection pattern.
``tests/test_uprime_rpc_ledger.py`` is the frozen, anchored collector for this
support module.  It may also be run explicitly while phase 1b2 is developed.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import fields
import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any, Callable

import pytest

from lean_rgc.evals import uprime_rpc_contract_oracle as oracle
from lean_rgc.evals import uprime_rpc_ledger as ledger
from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics
from lean_rgc.evals import uprime_rpc_litmus as production
import uprime_rpc_ledger_semantics_cases as fixture


CONTRACT_IDS = (
    "R0_request_id_echo",
    "B0_task_budget_init",
    "B1_action_budget_nonsticky",
    "B2_budget_telemetry",
    "B3_enforcement_reset",
    "B4_cache_budget_semantics",
    "D0_target_routing",
    "D1_transition_delta",
    "D2_all_goal_sweep",
    "R1_independent_replay",
    "E0_episode_budget",
)

PUBLIC_FIELDS = (
    "oracle_schema_version",
    "oracle_scope",
    "origin_status",
    "input_sha256",
    "input_bytes",
    "final_chain_head",
    "record_count",
    "contract_ids",
    "contract_passes",
    "contract_failure_ids",
    "raw_all_contracts",
    "reservation_token_verification",
    "source_blob_authentication",
    "remote_claim_authentication",
    "bundle_binding",
    "report_binding",
    "attempt_manifest_binding",
    "privacy_scan",
    "archive_verification",
    "authority_scope",
    "canonical_run_authority",
    "licenses_execution",
    "licenses_later_stage",
)

EventMutation = Callable[
    [dict[str, Any], dict[str, Any], list[dict[str, Any]]], None
]

BUDGET_KEYS = (
    "effective_max_heartbeats_option",
    "effective_max_heartbeats_counter",
    "unlimited",
    "source",
    "consumed_heartbeats_counter",
    "episode_max_heartbeats_counter",
    "episode_remaining_heartbeats_counter",
    "episode_source",
    "measurement_scope",
    "reset_scope",
)

REPLAY_LABELS = {
    "primary_split": "primary_split_replay",
    "primary_tail_close": "primary_tail_close_replay",
    "primary_head_close": "primary_head_close_replay",
    "zero_split": "zero_split_replay",
    "zero_child_close": "zero_child_close_replay",
    "side_effect_close": "side_effect_close_replay",
    "reset": "reset_replay",
}


def _response(events: list[dict[str, Any]], label: str) -> dict[str, Any]:
    return fixture._response_event(events, label)["body"]["response"]


def _request(events: list[dict[str, Any]], label: str) -> dict[str, Any]:
    return fixture._request_event(events, label)["body"]["request"]


def _kernel_ids(kernel: dict[str, Any], field: str) -> set[str]:
    rows = kernel[field]
    if field == "goals":
        return {row["mvar_id"] for row in rows}
    return {
        row["mvar_id"]
        for row in rows
        if row.get("assigned") is True
    }


def _independent_delta(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, list[str]]:
    before_goals = _kernel_ids(before, "goals")
    after_goals = _kernel_ids(after, "goals")
    before_assigned = _kernel_ids(before, "metavars")
    after_assigned = _kernel_ids(after, "metavars")
    before_mvars = {row["mvar_id"] for row in before["metavars"]}
    after_mvars = {row["mvar_id"] for row in after["metavars"]}
    newly_assigned = after_assigned - before_assigned
    return {
        "closed_goals": sorted(before_goals & newly_assigned),
        "new_goals": sorted(after_goals - before_goals),
        "assigned_mvars": sorted(newly_assigned),
        "new_mvars": sorted(after_mvars - before_mvars),
    }


def _sync_replay(
    events: list[dict[str, Any]], primary_label: str
) -> None:
    primary = _response(events, primary_label)
    replay = _response(events, REPLAY_LABELS[primary_label])
    replay["before_state_id"] = primary["before_state_id"]
    replay["expected_after_state_id"] = primary["after_state_id"]
    replay["kernel_state_before"] = copy.deepcopy(primary["kernel_state_before"])
    replay["kernel_state_expected"] = copy.deepcopy(primary["kernel_state_after"])
    replay["kernel_state_observed"] = copy.deepcopy(primary["kernel_state_after"])
    replay["state_delta_expected"] = copy.deepcopy(primary["state_delta"])
    replay["state_delta_observed"] = copy.deepcopy(primary["state_delta"])


def _replace_transition(
    events: list[dict[str, Any]],
    label: str,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    response = _response(events, label)
    if before is not None:
        response["kernel_state_before"] = copy.deepcopy(before)
        response["before_state_id"] = before["state_id"]
    if after is not None:
        response["kernel_state_after"] = copy.deepcopy(after)
        response["after_state_id"] = after["state_id"]
    response["state_delta"] = _independent_delta(
        response["kernel_state_before"], response["kernel_state_after"]
    )
    _sync_replay(events, label)


def _budget(response: dict[str, Any]) -> dict[str, Any]:
    return response["budget"]


def _budget_mirror(response: dict[str, Any]) -> dict[str, Any]:
    return response["audit"]["audit_flags"]["heartbeat_telemetry"]


def _set_budget_field(
    response: dict[str, Any], key: str, value: Any, *, mirror: bool = True
) -> None:
    _budget(response)[key] = value
    if mirror:
        _budget_mirror(response)[key] = copy.deepcopy(value)


def _set_consumed(
    response: dict[str, Any], consumed: Any, *, remaining: Any | None = None
) -> None:
    _set_budget_field(response, "consumed_heartbeats_counter", consumed)
    response["heartbeats"] = consumed
    response["audit"]["heartbeats"] = consumed
    if remaining is not None:
        _set_budget_field(
            response, "episode_remaining_heartbeats_counter", remaining
        )


def _set_reset_init_option(
    events: list[dict[str, Any]], value: Any
) -> None:
    init_kernel = _response(events, "reset_init")["kernel_state"]
    init_kernel["options"]["maxHeartbeats"] = value
    reset = _response(events, "reset")
    reset["kernel_state_before"]["options"]["maxHeartbeats"] = value
    _sync_replay(events, "reset")


def _reverse_dicts(value: Any) -> Any:
    if type(value) is dict:
        return {
            key: _reverse_dicts(item)
            for key, item in reversed(tuple(value.items()))
        }
    if type(value) is list:
        return [_reverse_dicts(item) for item in value]
    return value


def _write(
    path: Path,
    mutation: EventMutation | None = None,
) -> None:
    fixture._write_fixture(path, mutate=mutation)


def _write_custom_event_sequence(
    path: Path, events: list[dict[str, Any]]
) -> None:
    writer = ledger.StandaloneChainWriter.create(
        path, header_body=fixture._header_body()
    )
    writer.append_event("local_probe", fixture._local_probe_body())
    for event in events:
        writer.append_event(event["record_type"], event["body"])
    writer.close_with_closure({"synthetic_wrong_shape": True})


def _attest(path: Path):
    return oracle.attest_standalone_exact_49_contracts(path)


def _passes(result: Any) -> dict[str, bool]:
    return dict(zip(result.contract_ids, result.contract_passes, strict=True))


def _assert_only_failure(result: Any, contract_id: str) -> None:
    expected = {key: key != contract_id for key in CONTRACT_IDS}
    assert _passes(result) == expected
    assert result.contract_failure_ids == (contract_id,)
    assert result.raw_all_contracts is False
    assert result.authority_scope == "none"
    assert result.canonical_run_authority is False
    assert result.licenses_execution is False
    assert result.licenses_later_stage is False


def _assert_failures(result: Any, expected: set[str]) -> None:
    ordered = tuple(item for item in CONTRACT_IDS if item in expected)
    assert result.contract_failure_ids == ordered
    assert {
        item
        for item, passed in _passes(result).items()
        if passed is False
    } == expected
    assert result.raw_all_contracts is (not expected)


def _remove_shutdown_protocol(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _response(events, "shutdown").pop("rpc_protocol_version")


def _fail_b4(
    _header: dict[str, Any],
    probe: dict[str, Any],
    _events: list[dict[str, Any]],
) -> None:
    probe["resolved"]["explicit_zero"] = "1"


def _remove_primary_split_replay_target(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _response(events, "primary_split_replay").pop("target_mvar_id")


def _remove_primary_split_replay_certificate_error(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _response(events, "primary_split_replay")["replay_certificate"].pop("error")


def _remove_zero_budget_counter(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "zero_split")
    response["budget"].pop("effective_max_heartbeats_counter")
    response["audit"]["audit_flags"]["heartbeat_telemetry"].pop(
        "effective_max_heartbeats_counter"
    )


def _break_episode_accounting(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "primary_tail_close")
    response["budget"]["episode_remaining_heartbeats_counter"] += 1
    response["audit"]["audit_flags"]["heartbeat_telemetry"][
        "episode_remaining_heartbeats_counter"
    ] += 1


def _put_burn_exactly_on_cap(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "burn")
    consumed = 200_000 * 1000
    response["heartbeats"] = consumed
    response["audit"]["heartbeats"] = consumed
    response["budget"]["consumed_heartbeats_counter"] = consumed
    response["audit"]["audit_flags"]["heartbeat_telemetry"][
        "consumed_heartbeats_counter"
    ] = consumed


def _fail_b0_option(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _set_reset_init_option(events, "732")


def _fail_b1_nonsticky(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    changed = copy.deepcopy(
        _response(events, "primary_split")["kernel_state_after"]
    )
    changed["options"]["maxHeartbeats"] = "732"
    _replace_transition(events, "primary_split", after=changed)
    _replace_transition(events, "primary_tail_close", before=changed)


def _fail_d0_routing_only(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    changed = copy.deepcopy(
        _response(events, "primary_tail_close")["kernel_state_after"]
    )
    changed["goals"] = [{"mvar_id": "primary-tail"}]
    for row in changed["metavars"]:
        if row["mvar_id"] == "primary-head":
            row["assigned"] = True
        elif row["mvar_id"] == "primary-tail":
            row["assigned"] = False
    _replace_transition(events, "primary_tail_close", after=changed)
    _replace_transition(events, "primary_head_close", before=changed)


def _fail_d1_continuity_only(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    foreign = copy.deepcopy(
        _response(events, "primary_tail_close")["kernel_state_before"]
    )
    foreign["state_hash_raw"] = "raw-foreign-predecessor"
    _replace_transition(events, "primary_tail_close", before=foreign)


def _fail_d2_sweep_only(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    changed = copy.deepcopy(
        _response(events, "side_effect_close")["kernel_state_after"]
    )
    changed["goals"] = [{"mvar_id": "side-witness"}]
    for row in changed["metavars"]:
        if row["mvar_id"] == "side-witness":
            row["assigned"] = False
    response = _response(events, "side_effect_close")
    response["status"] = "partial"
    response["audit"]["status"] = "partial"
    _replace_transition(events, "side_effect_close", after=changed)


def _fail_budget_mirror(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _budget_mirror(_response(events, "primary_split"))["source"] = "task"


def _fail_budget_mirror_bool_int(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    # Ordinary Python equality aliases ``0`` and ``False``.  The oracle's
    # strict JSON comparison must distinguish them.
    response = _response(events, "zero_split")
    assert _budget(response)["effective_max_heartbeats_option"] == 0
    _budget_mirror(response)["effective_max_heartbeats_option"] = False


def _fail_predecessor_strict_bool_int_alias(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    predecessor = copy.deepcopy(
        _response(events, "primary_split")["kernel_state_after"]
    )
    predecessor["strict_json_alias_probe"] = 0
    _replace_transition(events, "primary_split", after=predecessor)
    successor_before = copy.deepcopy(predecessor)
    successor_before["strict_json_alias_probe"] = False
    assert predecessor == successor_before
    assert ledger.canonical_json_bytes(predecessor) != ledger.canonical_json_bytes(
        successor_before
    )
    _replace_transition(
        events,
        "primary_tail_close",
        before=successor_before,
    )


def _fail_replay_state_strict_bool_int_alias(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    actual_after = copy.deepcopy(_response(events, "reset")["kernel_state_after"])
    actual_after["strict_json_alias_probe"] = 0
    _replace_transition(events, "reset", after=actual_after)
    observed = _response(events, "reset_replay")["kernel_state_observed"]
    observed["strict_json_alias_probe"] = False
    assert actual_after == observed
    assert ledger.canonical_json_bytes(actual_after) != ledger.canonical_json_bytes(
        observed
    )


def _fail_replay_delta_strict_bool_int_alias(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "reset")
    response["state_delta"]["strict_json_alias_probe"] = 0
    replay = _response(events, "reset_replay")
    replay["state_delta_expected"] = copy.deepcopy(response["state_delta"])
    replay["state_delta_observed"] = copy.deepcopy(response["state_delta"])
    replay["state_delta_observed"]["strict_json_alias_probe"] = False
    assert response["state_delta"] == replay["state_delta_observed"]
    assert ledger.canonical_json_bytes(
        response["state_delta"]
    ) != ledger.canonical_json_bytes(replay["state_delta_observed"])


def _zero_counter_is_numeric_zero(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _set_budget_field(
        _response(events, "zero_split"),
        "effective_max_heartbeats_counter",
        0,
    )


def _zero_unlimited_is_false(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _set_budget_field(_response(events, "zero_split"), "unlimited", False)


def _fail_nonburn_cap_only(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    # Keep episode arithmetic valid while exceeding the per-action cap.
    _set_consumed(
        _response(events, "primary_head_close"),
        731_001,
        remaining=268_978,
    )


def _fail_top_heartbeat_type(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _response(events, "primary_split")["heartbeats"] = True


def _fail_option_bool(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "primary_split")
    _set_budget_field(response, "effective_max_heartbeats_option", True)


def _burn_under_cap(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _set_consumed(_response(events, "burn"), 199_999_999, remaining=0)


def _forge_cumulative_delta(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "reset")
    response["state_delta"]["assigned_mvars"] = [
        "foreign-cumulative",
        "reset-goal",
    ]


def _assigned_open_goal(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    response = _response(events, "primary_split")
    for row in response["kernel_state_after"]["metavars"]:
        if row["mvar_id"] == "primary-head":
            row["assigned"] = True
    response["state_delta"] = _independent_delta(
        response["kernel_state_before"], response["kernel_state_after"]
    )


def _wrong_side_target(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _request(events, "side_effect_close")["target_mvar_id"] = "side-witness"


def _response_echo_mismatch(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    _response(events, "primary_split")["id"] = "wrong-response-id"


def _reuse_primary_mvar_names_in_zero_trajectory(
    _header: dict[str, Any],
    _probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    replacements = {
        "zero-root": "primary-root",
        "zero-head": "primary-head",
        "zero-tail": "primary-tail",
    }

    def rename(value: Any) -> Any:
        if type(value) is str:
            return replacements.get(value, value)
        if type(value) is list:
            return [rename(item) for item in value]
        if type(value) is dict:
            return {key: rename(item) for key, item in value.items()}
        return value

    for label in (
        "zero_init",
        "zero_split",
        "zero_split_replay",
        "zero_child_close",
        "zero_child_close_replay",
    ):
        response_event = fixture._response_event(events, label)
        response_event["body"]["response"] = rename(
            response_event["body"]["response"]
        )
        request_event = fixture._request_event(events, label)
        request_event["body"]["request"] = rename(
            request_event["body"]["request"]
        )


def test_exact_49_oracle_all_true_has_exact_nonauthoritative_public_surface(
    tmp_path,
):
    path = tmp_path / "all-true.responses.jsonl"
    _write(path)

    result = _attest(path)

    assert tuple(field.name for field in fields(result)) == PUBLIC_FIELDS
    assert result.oracle_schema_version == (
        "lean-rgc-uprime-rpc-exact-49-contract-oracle-v0.1"
    )
    assert result.oracle_scope == (
        "standalone_exact_49_raw_contract_predicates_only"
    )
    assert result.origin_status == "unknown_may_be_synthetic"
    assert result.record_count == 49
    assert result.contract_ids == CONTRACT_IDS
    assert result.contract_passes == (True,) * len(CONTRACT_IDS)
    assert result.contract_failure_ids == ()
    assert result.raw_all_contracts is True

    for name in (
        "reservation_token_verification",
        "source_blob_authentication",
        "remote_claim_authentication",
        "bundle_binding",
        "report_binding",
        "attempt_manifest_binding",
        "privacy_scan",
        "archive_verification",
    ):
        assert getattr(result, name) == "not_performed"
    assert result.authority_scope == "none"
    assert result.canonical_run_authority is False
    assert result.licenses_execution is False
    assert result.licenses_later_stage is False

    forbidden = {
        "CLEAR",
        "BLOCKED",
        "verdict",
        "finalized",
        "verifier_passed",
        "scientific_disposition",
    }
    public_names = {field.name for field in fields(result)}
    assert public_names.isdisjoint(forbidden)
    assert all(not hasattr(result, name) for name in forbidden)


def test_contract_oracle_does_not_call_phase1b1_or_production_helpers(
    tmp_path, monkeypatch
):
    path = tmp_path / "independent.responses.jsonl"
    _write(path)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("phase-1b2 oracle called a forbidden helper")

    monkeypatch.setattr(
        semantics,
        "attest_standalone_nominal_49_semantics",
        forbidden,
    )
    for name in (
        "evaluate_contracts",
        "diagnostic_disposition",
        "_response_summary",
        "cache_budget_probe",
    ):
        monkeypatch.setattr(production, name, forbidden)

    result = _attest(path)

    assert result.contract_passes == (True,) * len(CONTRACT_IDS)
    assert result.raw_all_contracts is True
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    ("contract_id", "mutation"),
    (
        ("R0_request_id_echo", _remove_shutdown_protocol),
        ("B0_task_budget_init", _fail_b0_option),
        ("B1_action_budget_nonsticky", _fail_b1_nonsticky),
        ("B4_cache_budget_semantics", _fail_b4),
        ("D0_target_routing", _fail_d0_routing_only),
        ("D1_transition_delta", _fail_d1_continuity_only),
        ("D2_all_goal_sweep", _fail_d2_sweep_only),
        ("R1_independent_replay", _remove_primary_split_replay_target),
        ("B2_budget_telemetry", _remove_zero_budget_counter),
        ("E0_episode_budget", _break_episode_accounting),
        ("B3_enforcement_reset", _put_burn_exactly_on_cap),
    ),
    ids=("R0", "B0", "B1", "B4", "D0", "D1", "D2", "R1", "B2", "E0", "B3"),
)
def test_rehashed_contract_failure_is_isolated_when_cross_contract_division_allows(
    tmp_path,
    contract_id: str,
    mutation: EventMutation,
):
    path = tmp_path / f"isolated-{contract_id}.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    _assert_only_failure(result, contract_id)


@pytest.mark.parametrize(
    "mutation",
    (
        _remove_primary_split_replay_target,
        _remove_primary_split_replay_certificate_error,
    ),
    ids=("target", "certificate-error"),
)
def test_r1_explicit_null_passes_but_missing_key_fails(
    tmp_path,
    mutation: EventMutation,
):
    explicit_path = tmp_path / "explicit-null.responses.jsonl"
    missing_path = tmp_path / "missing.responses.jsonl"
    _write(explicit_path)
    _write(missing_path, mutation)

    explicit = _attest(explicit_path)
    missing = _attest(missing_path)

    assert _passes(explicit)["R1_independent_replay"] is True
    _assert_only_failure(missing, "R1_independent_replay")


def test_b2_zero_option_counter_explicit_null_passes_but_missing_key_fails(
    tmp_path,
):
    explicit_path = tmp_path / "zero-counter-null.responses.jsonl"
    missing_path = tmp_path / "zero-counter-missing.responses.jsonl"
    _write(explicit_path)
    _write(missing_path, _remove_zero_budget_counter)

    explicit = _attest(explicit_path)
    missing = _attest(missing_path)

    assert _passes(explicit)["B2_budget_telemetry"] is True
    _assert_only_failure(missing, "B2_budget_telemetry")


def test_dynamic_request_semantic_failure_returns_no_contract_vector(tmp_path):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _request(events, "primary_split")["state_id"] = "forged-state"

    path = tmp_path / "semantic-invalid.responses.jsonl"
    _write(path, mutation)

    with pytest.raises(oracle.StandaloneExact49ContractOracleError):
        _attest(path)


def test_public_api_accepts_only_a_ledger_path(tmp_path):
    parameters = tuple(
        inspect.signature(
            oracle.attest_standalone_exact_49_contracts
        ).parameters.values()
    )
    assert len(parameters) == 1
    assert parameters[0].name == "path"

    path = tmp_path / "path-only.responses.jsonl"
    _write(path)
    with pytest.raises(TypeError):
        oracle.attest_standalone_exact_49_contracts(  # type: ignore[call-arg]
            path,
            context={"forged": True},
        )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    (
        (_fail_budget_mirror, {"B2_budget_telemetry"}),
        (_fail_budget_mirror_bool_int, {"B2_budget_telemetry"}),
        (_fail_nonburn_cap_only, {"B2_budget_telemetry"}),
        (_fail_top_heartbeat_type, {"B2_budget_telemetry"}),
        (
            _fail_option_bool,
            {"B1_action_budget_nonsticky", "B2_budget_telemetry"},
        ),
        (_zero_counter_is_numeric_zero, {"B2_budget_telemetry"}),
        (
            _zero_unlimited_is_false,
            {"B1_action_budget_nonsticky", "B2_budget_telemetry"},
        ),
        (_break_episode_accounting, {"E0_episode_budget"}),
        (_burn_under_cap, {"B3_enforcement_reset"}),
    ),
    ids=(
        "mirror",
        "strict-bool-int-mirror",
        "nonburn-cap",
        "top-heartbeat-type",
        "bool-option",
        "zero-counter-is-zero",
        "zero-unlimited-is-false",
        "episode-accounting",
        "burn-under-cap",
    ),
)
def test_budget_cross_contract_divisions_remain_frozen(
    tmp_path,
    mutation: EventMutation,
    expected: set[str],
):
    path = tmp_path / "budget-division.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    _assert_failures(result, expected)


@pytest.mark.parametrize("surface", ("budget", "mirror"))
@pytest.mark.parametrize("key", BUDGET_KEYS)
def test_b2_requires_every_budget_key_on_both_surfaces(
    tmp_path,
    key: str,
    surface: str,
):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        response = _response(events, "side_effect_close")
        target = _budget(response) if surface == "budget" else _budget_mirror(response)
        target.pop(key)

    path = tmp_path / f"missing-{surface}-{key}.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    assert _passes(result)["B2_budget_telemetry"] is False
    assert result.raw_all_contracts is False


@pytest.mark.parametrize("surface", ("top", "audit"))
def test_b2_requires_both_heartbeat_scalars(tmp_path, surface: str):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        response = _response(events, "side_effect_close")
        if surface == "top":
            response.pop("heartbeats")
        else:
            response["audit"].pop("heartbeats")

    path = tmp_path / f"missing-{surface}-heartbeats.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    assert _passes(result)["B2_budget_telemetry"] is False


def test_cumulative_delta_is_computed_false_not_semantic_rejection(tmp_path):
    path = tmp_path / "cumulative-delta.responses.jsonl"
    _write(path, _forge_cumulative_delta)

    result = _attest(path)

    _assert_failures(result, {"D1_transition_delta", "R1_independent_replay"})


def test_assigned_open_goal_is_computed_false_not_semantic_rejection(tmp_path):
    path = tmp_path / "assigned-open.responses.jsonl"
    _write(path, _assigned_open_goal)

    result = _attest(path)

    assert _passes(result)["D1_transition_delta"] is False
    assert _passes(result)["D2_all_goal_sweep"] is False
    assert _passes(result)["R1_independent_replay"] is False
    assert result.raw_all_contracts is False


def test_predecessor_strict_bool_int_alias_fails_only_d1(tmp_path):
    path = tmp_path / "predecessor-strict-alias.responses.jsonl"
    _write(path, _fail_predecessor_strict_bool_int_alias)

    result = _attest(path)

    _assert_only_failure(result, "D1_transition_delta")


@pytest.mark.parametrize(
    "mutation",
    (
        _fail_replay_state_strict_bool_int_alias,
        _fail_replay_delta_strict_bool_int_alias,
    ),
    ids=("state", "delta"),
)
def test_replay_strict_bool_int_alias_fails_only_r1(
    tmp_path,
    mutation: EventMutation,
):
    path = tmp_path / "replay-strict-alias.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    _assert_only_failure(result, "R1_independent_replay")


@pytest.mark.parametrize(
    ("part", "value"),
    (
        (("action_id",), "forged-action"),
        (("before_state_id",), "forged-before"),
        (("kernel_state_observed", "state_hash_raw"), "forged-state"),
        (("state_delta_observed", "assigned_mvars"), ["forged-delta"]),
        (("replay_certificate", "replay_status"), "pending"),
        (("replay_certificate", "error"), "forged-error"),
    ),
    ids=("action", "state-id", "state", "delta", "certificate", "error"),
)
def test_replay_action_state_delta_and_certificate_fail_only_r1(
    tmp_path,
    part: tuple[str, ...],
    value: Any,
):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        cursor = _response(events, "reset_replay")
        for key in part[:-1]:
            cursor = cursor[key]
        cursor[part[-1]] = value

    path = tmp_path / f"replay-{part[-1]}.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    _assert_only_failure(result, "R1_independent_replay")


def test_chain_local_mvar_name_reuse_is_not_globally_rejected(tmp_path):
    path = tmp_path / "chain-local-name-reuse.responses.jsonl"
    _write(path, _reuse_primary_mvar_names_in_zero_trajectory)

    result = _attest(path)

    assert result.contract_passes == (True,) * len(CONTRACT_IDS)
    assert result.raw_all_contracts is True


def test_response_id_echo_mismatch_is_computed_r0_false(tmp_path):
    path = tmp_path / "echo-mismatch.responses.jsonl"
    _write(path, _response_echo_mismatch)

    result = _attest(path)

    _assert_only_failure(result, "R0_request_id_echo")


@pytest.mark.parametrize(
    "case",
    ("torn", "wrong-count", "wrong-order", "frame-index", "association", "target"),
)
def test_chain_and_exact_state_machine_failures_return_no_vector(
    tmp_path,
    case: str,
):
    path = tmp_path / f"invalid-{case}.responses.jsonl"
    if case == "torn":
        _write(path)
        path.write_bytes(path.read_bytes()[:-1])
    elif case == "wrong-count":
        _write_custom_event_sequence(path, fixture._event_bodies()[:-2])
    elif case == "wrong-order":
        events = fixture._event_bodies()
        events[0], events[1] = events[1], events[0]
        _write_custom_event_sequence(path, events)
    elif case == "frame-index":
        def mutation(
            _header: dict[str, Any],
            _probe: dict[str, Any],
            events: list[dict[str, Any]],
        ) -> None:
            fixture._request_event(events, "primary_split")["body"][
                "frame_index"
            ] = 4

        _write(path, mutation)
    elif case == "association":
        def mutation(
            _header: dict[str, Any],
            _probe: dict[str, Any],
            events: list[dict[str, Any]],
        ) -> None:
            fixture._response_event(events, "primary_split")["body"][
                "association"
            ] = "unsolicited"

        _write(path, mutation)
    else:
        _write(path, _wrong_side_target)

    with pytest.raises(oracle.StandaloneExact49ContractOracleError):
        _attest(path)


def test_raw_noncanonical_key_order_returns_no_vector(tmp_path):
    path = tmp_path / "noncanonical-order.responses.jsonl"
    _write(path)
    lines = path.read_bytes().splitlines(keepends=True)
    value = json.loads(lines[0])
    reversed_value = dict(reversed(tuple(value.items())))
    noncanonical = json.dumps(
        reversed_value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    assert noncanonical != lines[0]
    lines[0] = noncanonical
    path.write_bytes(b"".join(lines))

    with pytest.raises(oracle.StandaloneExact49ContractOracleError):
        _attest(path)


@pytest.mark.parametrize(
    "value",
    (True, "\u0667\u0663\u0661", "9" * 5000),
    ids=("bool", "non-ascii-digits", "ascii-conversion-failure"),
)
def test_b0_bool_nonascii_and_failed_digit_conversion_are_false_not_errors(
    tmp_path,
    value: Any,
):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _set_reset_init_option(events, value)

    path = tmp_path / "bad-option.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    _assert_only_failure(result, "B0_task_budget_init")


def test_ascii_leading_zero_option_retains_numeric_interpretation(tmp_path):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _set_reset_init_option(events, "000731")

    path = tmp_path / "leading-zero.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    assert result.contract_passes == (True,) * len(CONTRACT_IDS)


def test_b0_accepts_integer_731_option(tmp_path):
    def mutation(
        _header: dict[str, Any],
        _probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _set_reset_init_option(events, 731)

    path = tmp_path / "integer-option.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    assert result.contract_passes == (True,) * len(CONTRACT_IDS)


def test_b4_explicit_default_resolved_value_is_intentionally_nonbinding(tmp_path):
    def mutation(
        _header: dict[str, Any],
        probe: dict[str, Any],
        _events: list[dict[str, Any]],
    ) -> None:
        probe["resolved"]["explicit_default"] = "intentionally-unchecked"

    path = tmp_path / "b4-explicit-default-nonbinding.responses.jsonl"
    _write(path, mutation)

    result = _attest(path)

    assert _passes(result)["B4_cache_budget_semantics"] is True
    assert result.contract_passes == (True,) * len(CONTRACT_IDS)


def test_canonical_output_is_independent_of_input_dict_insertion_order(tmp_path):
    baseline = tmp_path / "baseline.responses.jsonl"
    reordered = tmp_path / "reordered.responses.jsonl"
    _write(baseline)

    def mutation(
        header: dict[str, Any],
        probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        for target in (header, probe, *events):
            replacement = _reverse_dicts(target)
            target.clear()
            target.update(replacement)

    _write(reordered, mutation)

    assert baseline.read_bytes() == reordered.read_bytes()
    assert _attest(baseline) == _attest(reordered)


def test_public_binding_uses_actual_path_digest_size_and_chain_head(tmp_path):
    path = tmp_path / "binding.responses.jsonl"
    _write(path)
    raw = path.read_bytes()
    final_record = json.loads(raw.splitlines()[-1])

    result = _attest(path)

    assert result.input_sha256 == hashlib.sha256(raw).hexdigest().upper()
    assert result.input_bytes == len(raw)
    assert result.final_chain_head == final_record["record_sha256"]
    assert result.record_count == len(raw.splitlines()) == 49


def test_failure_order_and_digest_are_deterministic(tmp_path):
    def mutation(
        header: dict[str, Any],
        probe: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _fail_option_bool(header, probe, events)
        _break_episode_accounting(header, probe, events)

    first_path = tmp_path / "failure-order-1.responses.jsonl"
    second_path = tmp_path / "failure-order-2.responses.jsonl"
    _write(first_path, mutation)
    _write(second_path, mutation)

    first = _attest(first_path)
    second = _attest(second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert first == second
    assert first.contract_failure_ids == (
        "B1_action_budget_nonsticky",
        "B2_budget_telemetry",
        "E0_episode_budget",
    )
    assert first.input_sha256 == hashlib.sha256(
        first_path.read_bytes()
    ).hexdigest().upper()


def test_exactly_one_snapshot_call_and_target_path_open(tmp_path, monkeypatch):
    path = tmp_path / "one-open.responses.jsonl"
    _write(path)
    real_load = oracle.load_standalone_closed_chain_snapshot
    real_open = ledger.os.open
    load_count = 0
    target_open_count = 0

    def counted_load(candidate: Any):
        nonlocal load_count
        load_count += 1
        return real_load(candidate)

    def counted_open(candidate: Any, *args: Any, **kwargs: Any):
        nonlocal target_open_count
        if Path(candidate) == path:
            target_open_count += 1
        return real_open(candidate, *args, **kwargs)

    monkeypatch.setattr(oracle, "load_standalone_closed_chain_snapshot", counted_load)
    monkeypatch.setattr(ledger.os, "open", counted_open)

    result = _attest(path)

    assert result.raw_all_contracts is True
    assert load_count == 1
    assert target_open_count == 1


def test_same_size_mutation_during_retained_scan_returns_no_vector(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "same-size-mutation.responses.jsonl"
    _write(path)
    real_parse = ledger.parse_canonical_json_bytes
    mutated = False

    def parse_then_mutate(raw: bytes):
        nonlocal mutated
        value = real_parse(raw)
        if not mutated:
            mutated = True
            original = path.read_bytes()
            marker = original.index(b"synthetic")
            changed = original[:marker] + b"S" + original[marker + 1 :]
            assert len(changed) == len(original)
            with path.open("r+b", buffering=0) as handle:
                handle.write(changed)
                handle.flush()
                os.fsync(handle.fileno())
        return value

    monkeypatch.setattr(ledger, "parse_canonical_json_bytes", parse_then_mutate)

    with pytest.raises(oracle.StandaloneExact49ContractOracleError):
        _attest(path)
    assert mutated is True


def test_path_replacement_when_snapshot_handle_closes_returns_no_vector(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "path-target.responses.jsonl"
    replacement = tmp_path / "path-replacement.responses.jsonl"
    _write(target)
    _write(replacement, _fail_b4)
    real_fdopen = ledger.os.fdopen
    swapped = False

    class SwapOnClose:
        def __init__(self, wrapped: Any) -> None:
            self.wrapped = wrapped

        def __getattr__(self, name: str) -> Any:
            return getattr(self.wrapped, name)

        def close(self) -> None:
            nonlocal swapped
            self.wrapped.close()
            if not swapped:
                swapped = True
                os.replace(replacement, target)

    def swapping_fdopen(fd: int, *args: Any, **kwargs: Any) -> SwapOnClose:
        return SwapOnClose(real_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(ledger.os, "fdopen", swapping_fdopen)

    with pytest.raises(oracle.StandaloneExact49ContractOracleError):
        _attest(target)
    assert swapped is True


@pytest.mark.parametrize(
    "forged_keyword",
    (
        "context",
        "responses",
        "request_ids",
        "report",
        "contract_summary",
        "phase1b1_predicate",
        "x0",
    ),
)
def test_public_api_rejects_every_forged_caller_side_channel(
    tmp_path,
    forged_keyword: str,
):
    path = tmp_path / "path-only-forged.responses.jsonl"
    _write(path)

    with pytest.raises(TypeError):
        oracle.attest_standalone_exact_49_contracts(
            path,
            **{forged_keyword: {"forged": True}},
        )


ALLOWED_ORACLE_IMPORTS = (
    ("from", 0, "__future__", (("annotations", None),)),
    ("from", 0, "dataclasses", (("dataclass", None),)),
    ("from", 0, "datetime", (("datetime", None),)),
    ("import", 0, "", (("hashlib", None),)),
    ("from", 0, "pathlib", (("Path", None),)),
    ("import", 0, "", (("re", None),)),
    ("from", 0, "typing", (("Any", None),)),
    (
        "from",
        0,
        "lean_rgc.evals.uprime_rpc_ledger",
        (
            ("STRICT_JSON_CANONICALIZER_ID", None),
            ("StandaloneLedgerStructureError", None),
            ("canonical_json_bytes", None),
            ("load_standalone_closed_chain_snapshot", None),
            ("parse_canonical_json_bytes", None),
        ),
    ),
)

FORBIDDEN_ORACLE_NAMES = {
    "__builtins__",
    "__import__",
    "builtins",
    "eval",
    "exec",
    "getattr",
    "globals",
    "import_module",
    "importlib",
    "locals",
    "open",
    "os",
    "vars",
}
FORBIDDEN_ORACLE_ATTRIBUTES = {
    "import_module",
    "open",
    "read",
    "read1",
    "readall",
    "readinto",
    "readline",
    "readlines",
    "read_bytes",
    "read_text",
}
FORBIDDEN_ORACLE_STRINGS = {
    "__import__",
    "eval",
    "exec",
    "import_module",
    "open",
    "read",
    "read1",
    "readall",
    "readinto",
    "readline",
    "readlines",
    "read_bytes",
    "read_text",
}


def _normalized_import(node: ast.Import | ast.ImportFrom) -> tuple[Any, ...]:
    names = tuple((alias.name, alias.asname) for alias in node.names)
    if isinstance(node, ast.Import):
        return ("import", 0, "", names)
    return ("from", node.level, node.module or "", names)


def _oracle_import_policy_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []
    imports = tuple(
        _normalized_import(node)
        for node in sorted(
            (
                item
                for item in ast.walk(tree)
                if isinstance(item, (ast.Import, ast.ImportFrom))
            ),
            key=lambda item: (item.lineno, item.col_offset),
        )
    )
    if imports != ALLOWED_ORACLE_IMPORTS:
        violations.append(f"complete import allowlist mismatch: {imports!r}")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            violations.append(f"relative import at {node.lineno}")
        if isinstance(node, ast.Name) and node.id in {
            "__import__",
            "eval",
            "exec",
            "import_module",
        }:
            violations.append(f"dynamic primitive {node.id} at {node.lineno}")
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "import_module"
        ):
            violations.append(f"dynamic import attribute at {node.lineno}")
    return violations


def _assignment_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        return {
            name
            for item in node.elts
            for name in _assignment_names(item)
        }
    return set()


def _expression_references_tainted_io(
    node: ast.AST,
    tainted: set[str],
) -> bool:
    for item in ast.walk(node):
        if isinstance(item, ast.Name) and item.id in tainted:
            return True
        if (
            isinstance(item, ast.Attribute)
            and item.attr in FORBIDDEN_ORACLE_ATTRIBUTES
        ):
            return True
        if (
            isinstance(item, ast.Constant)
            and type(item.value) is str
            and item.value in FORBIDDEN_ORACLE_STRINGS
        ):
            return True
    return False


def _oracle_direct_io_policy_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    tainted = set(FORBIDDEN_ORACLE_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "builtins":
            for alias in node.names:
                if alias.name in {"open", "eval", "exec", "__import__"}:
                    imported_name = alias.asname or alias.name
                    tainted.add(imported_name)
                    violations.append(
                        f"tainted import alias {imported_name} at {node.lineno}"
                    )

    assignments: list[tuple[set[str], ast.AST, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = {
                name
                for target in node.targets
                for name in _assignment_names(target)
            }
            assignments.append((targets, node.value, node.lineno))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            assignments.append(
                (_assignment_names(node.target), node.value, node.lineno)
            )
        elif isinstance(node, ast.NamedExpr):
            assignments.append(
                (_assignment_names(node.target), node.value, node.lineno)
            )

    changed = True
    while changed:
        changed = False
        for targets, value, lineno in assignments:
            new_names = targets - tainted
            if new_names and _expression_references_tainted_io(value, tainted):
                tainted.update(new_names)
                changed = True
                for name in sorted(new_names):
                    violations.append(f"tainted alias {name} at {lineno}")

    snapshot_names = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "load_standalone_closed_chain_snapshot"
        and isinstance(node.ctx, ast.Load)
    ]
    snapshot_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_ORACLE_NAMES:
            violations.append(f"forbidden identifier {node.id} at {node.lineno}")
        elif (
            isinstance(node, ast.Attribute)
            and node.attr in FORBIDDEN_ORACLE_ATTRIBUTES
        ):
            violations.append(f"forbidden attribute {node.attr} at {node.lineno}")
        elif (
            isinstance(node, ast.Constant)
            and type(node.value) is str
            and node.value in FORBIDDEN_ORACLE_STRINGS
        ):
            violations.append(f"forbidden string {node.value!r} at {node.lineno}")
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            if node.func.id == "load_standalone_closed_chain_snapshot":
                snapshot_calls.append(node)
            elif node.func.id in tainted:
                violations.append(f"tainted call {node.func.id} at {node.lineno}")
        elif _expression_references_tainted_io(node.func, tainted):
            violations.append(f"tainted indirect call at {node.lineno}")
    if len(snapshot_names) != 1:
        violations.append(
            f"snapshot capability occurrence count is {len(snapshot_names)}"
        )
    if len(snapshot_calls) != 1:
        violations.append(f"snapshot call count is {len(snapshot_calls)}")
    elif len(snapshot_names) == 1 and snapshot_calls[0].func is not snapshot_names[0]:
        violations.append("snapshot capability is not the sole direct call target")

    all_attest_defs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "attest_standalone_exact_49_contracts"
    ]
    module_attest_refs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "attest_standalone_exact_49_contracts"
        and isinstance(node.ctx, ast.Load)
    ]
    if module_attest_refs:
        violations.append(
            "module attest capability occurrence count is "
            f"{len(module_attest_refs)}"
        )
    top_level_attest_defs = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "attest_standalone_exact_49_contracts"
    ]
    if len(all_attest_defs) != 1 or len(top_level_attest_defs) != 1:
        violations.append(
            "attest function is not one sole top-level synchronous FunctionDef"
        )
    else:
        attest_def = top_level_attest_defs[0]
        recursive_refs = [
            node
            for node in ast.walk(attest_def)
            if isinstance(node, ast.Name)
            and node.id == "attest_standalone_exact_49_contracts"
            and isinstance(node.ctx, ast.Load)
        ]
        recursive_calls = [
            node
            for node in ast.walk(attest_def)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "attest_standalone_exact_49_contracts"
        ]
        if recursive_refs:
            violations.append(
                f"attest recursive capability occurrence count is {len(recursive_refs)}"
            )
        if recursive_calls:
            violations.append(
                f"direct attest recursion call count is {len(recursive_calls)}"
            )

        if len(snapshot_calls) == 1 and len(snapshot_names) == 1:
            snapshot_call = snapshot_calls[0]
            call_shape = (
                len(snapshot_call.args) == 1
                and isinstance(snapshot_call.args[0], ast.Name)
                and snapshot_call.args[0].id == "path"
                and isinstance(snapshot_call.args[0].ctx, ast.Load)
                and not snapshot_call.keywords
            )
            if not call_shape:
                violations.append(
                    "snapshot call arguments differ from the frozen path call"
                )

            assignment = parents.get(snapshot_call)
            assignment_shape = (
                isinstance(assignment, ast.Assign)
                and assignment.value is snapshot_call
                and len(assignment.targets) == 1
                and isinstance(assignment.targets[0], ast.Name)
                and assignment.targets[0].id == "snapshot"
                and isinstance(assignment.targets[0].ctx, ast.Store)
            )
            if not assignment_shape:
                violations.append(
                    "snapshot call is not the value of direct snapshot assignment"
                )
            else:
                try_node = parents.get(assignment)
                try_shape = (
                    isinstance(try_node, ast.Try)
                    and assignment in try_node.body
                )
                if not try_shape:
                    violations.append(
                        "snapshot assignment is not a direct Try.body statement"
                    )
                else:
                    try_parent = parents.get(try_node)
                    if try_parent is not attest_def or try_node not in attest_def.body:
                        violations.append(
                            "snapshot Try is not a direct attest-function statement"
                        )
    return violations


def test_oracle_source_imports_only_the_frozen_ledger_substrate():
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8")

    assert _oracle_import_policy_violations(source) == []
    for forbidden_module in (
        "lean_rgc.evals.uprime_rpc_ledger_semantics",
        "lean_rgc.evals.uprime_rpc_litmus",
    ):
        assert forbidden_module not in source


@pytest.mark.parametrize(
    "bypass",
    (
        "from .uprime_rpc_litmus import evaluate_contracts\n",
        "from ..evals import uprime_rpc_litmus\n",
        "from importlib import import_module\nimport_module('forged')\n",
        "import importlib\nimportlib.import_module('forged')\n",
        "from builtins import __import__ as loader\nloader('forged')\n",
        "runner = __import__\nrunner('forged')\n",
        "runner = eval\nrunner('1 + 1')\n",
        "runner = exec\nrunner('pass')\n",
    ),
    ids=(
        "sibling-relative",
        "parent-relative",
        "dynamic-name",
        "dynamic-attribute",
        "builtins-import-alias",
        "dunder-import-alias",
        "eval-alias",
        "exec-alias",
    ),
)
def test_oracle_import_policy_rejects_relative_and_dynamic_bypasses(bypass: str):
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8") + "\n" + bypass

    assert _oracle_import_policy_violations(source)


def test_oracle_source_has_no_direct_path_io_bypass():
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8")

    assert _oracle_direct_io_policy_violations(source) == []


@pytest.mark.parametrize(
    ("bypass", "required_fragments"),
    (
        (
            "from builtins import open as read\nread('x')\n",
            ("tainted import alias read", "tainted call read"),
        ),
        (
            "reader = open\nreader('x')\n",
            ("tainted alias reader", "tainted call reader"),
        ),
        (
            "first = open\nreader = first\nreader('x')\n",
            ("tainted alias first", "tainted alias reader", "tainted call reader"),
        ),
        (
            "def forged(path):\n    return getattr(path, 'read_bytes')()\n",
            ("forbidden identifier getattr", "forbidden string 'read_bytes'"),
        ),
        (
            "reader = Path.read_bytes\nreader(Path('x'))\n",
            ("forbidden attribute read_bytes", "tainted call reader"),
        ),
        (
            "runner = eval\nrunner('1 + 1')\n",
            ("forbidden identifier eval", "tainted call runner"),
        ),
        (
            "runner = exec\nrunner('pass')\n",
            ("forbidden identifier exec", "tainted call runner"),
        ),
        (
            "second_snapshot = load_standalone_closed_chain_snapshot\n"
            "second_snapshot(Path('x'))\n",
            ("snapshot capability occurrence count is 2",),
        ),
        (
            "[load_standalone_closed_chain_snapshot][0](Path('x'))\n",
            ("snapshot capability occurrence count is 2",),
        ),
        (
            "runner = lambda path: load_standalone_closed_chain_snapshot(path)\n"
            "runner(Path('x'))\n",
            (
                "snapshot capability occurrence count is 2",
                "snapshot call count is 2",
            ),
        ),
        (
            "(load_standalone_closed_chain_snapshot,)[0](Path('x'))\n",
            ("snapshot capability occurrence count is 2",),
        ),
        (
            "globals()['attest_standalone_exact_49_contracts'](Path('x'))\n",
            ("forbidden identifier globals",),
        ),
        (
            "locals()['attest_standalone_exact_49_contracts'](Path('x'))\n",
            ("forbidden identifier locals",),
        ),
    ),
    ids=(
        "builtins-open-alias",
        "name-alias",
        "transitive-name-alias",
        "getattr-read-bytes",
        "attribute-alias",
        "eval-alias",
        "exec-alias",
        "snapshot-name-alias",
        "snapshot-list-container",
        "snapshot-lambda",
        "snapshot-tuple-container",
        "globals-reflection",
        "locals-reflection",
    ),
)
def test_direct_io_policy_rejects_reflection_and_alias_bypasses(
    bypass: str,
    required_fragments: tuple[str, ...],
):
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8") + "\n" + bypass

    violations = _oracle_direct_io_policy_violations(source)

    for fragment in required_fragments:
        assert any(fragment in violation for violation in violations)


@pytest.mark.parametrize(
    "replacement",
    (
        (
            "        for _ in range(1):\n"
            "            snapshot = load_standalone_closed_chain_snapshot(path)\n"
        ),
        (
            "        while True:\n"
            "            snapshot = load_standalone_closed_chain_snapshot(path)\n"
            "            break\n"
        ),
        (
            "        if path:\n"
            "            snapshot = load_standalone_closed_chain_snapshot(path)\n"
        ),
        (
            "        with forged_context:\n"
            "            snapshot = load_standalone_closed_chain_snapshot(path)\n"
        ),
        (
            "        snapshot = [\n"
            "            load_standalone_closed_chain_snapshot(path)\n"
            "            for _ in (0,)\n"
            "        ][0]\n"
        ),
        (
            "        def nested_snapshot():\n"
            "            return load_standalone_closed_chain_snapshot(path)\n"
            "        snapshot = nested_snapshot()\n"
        ),
        (
            "        async def nested_snapshot():\n"
            "            async for _ in forged_async_iter:\n"
            "                snapshot = "
            "load_standalone_closed_chain_snapshot(path)\n"
            "        snapshot = None\n"
        ),
    ),
    ids=(
        "for",
        "while",
        "if",
        "with",
        "comprehension",
        "nested-function",
        "async-for",
    ),
)
def test_snapshot_call_must_be_direct_try_assignment(replacement: str):
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8")
    frozen_line = (
        "        snapshot = load_standalone_closed_chain_snapshot(path)\n"
    )
    assert source.count(frozen_line) == 1
    mutated = source.replace(frozen_line, replacement)

    violations = _oracle_direct_io_policy_violations(mutated)

    assert any(
        "snapshot call is not the value of direct snapshot assignment" in item
        or "snapshot assignment is not a direct Try.body statement" in item
        for item in violations
    )


def test_snapshot_try_cannot_itself_be_nested_under_a_loop():
    mutated = (
        "def attest_standalone_exact_49_contracts(path):\n"
        "    for _ in range(1):\n"
        "        try:\n"
        "            snapshot = load_standalone_closed_chain_snapshot(path)\n"
        "        except Exception:\n"
        "            raise\n"
        "    return snapshot\n"
    )

    violations = _oracle_direct_io_policy_violations(mutated)

    assert any(
        "snapshot Try is not a direct attest-function statement" in item
        for item in violations
    )


def test_direct_attest_recursion_is_rejected_inside_loader_try():
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8")
    frozen_line = (
        "        snapshot = load_standalone_closed_chain_snapshot(path)\n"
    )
    assert source.count(frozen_line) == 1
    mutated = source.replace(
        frozen_line,
        "        attest_standalone_exact_49_contracts(path)\n" + frozen_line,
    )

    violations = _oracle_direct_io_policy_violations(mutated)

    assert any("direct attest recursion call count is 1" in item for item in violations)
    assert any(
        "attest recursive capability occurrence count is 1" in item
        for item in violations
    )


def test_guarded_top_level_attest_alias_recursion_is_rejected():
    source_path = Path(inspect.getsourcefile(oracle) or "")
    source = source_path.read_text(encoding="utf-8")
    mutated = source + (
        "\nif False:\n"
        "    _attest_alias = attest_standalone_exact_49_contracts\n"
        "    _attest_alias(Path('guarded'))\n"
    )

    violations = _oracle_direct_io_policy_violations(mutated)

    assert any(
        "module attest capability occurrence count is 1" in item
        for item in violations
    )
