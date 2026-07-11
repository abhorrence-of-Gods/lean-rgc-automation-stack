"""Non-default Phase-2b2e synthetic-recovery coordinator acceptance cases.

Only the functions named by ``__all__`` are collected by the frozen ledger
collector.  Real filesystem writes are restricted to pytest ``tmp_path``
directories.  Recovery itself is exercised entirely in one live process.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
from pathlib import Path
import pickle
import threading
from types import SimpleNamespace
from typing import get_type_hints

import pytest

from lean_rgc.evals import uprime_rpc_fake_cas_kernel as cas
from lean_rgc.evals import uprime_rpc_litmus as litmus
from lean_rgc.evals import uprime_rpc_local_staging_fake_publisher as publisher
from lean_rgc.evals import uprime_rpc_synthetic_recovery_coordinator as recovery


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "lean_rgc/evals/uprime_rpc_synthetic_recovery_coordinator.py"
SUPPORT_PATH = ROOT / "tests/uprime_rpc_synthetic_recovery_coordinator_cases.py"
COLLECTOR_PATH = ROOT / "tests/test_uprime_rpc_ledger.py"
REGISTRY_PATH = ROOT / "docs/experiments/uprime_odlrq_u1_rerun_license_registry.json"

A = bytes.fromhex("11" * 32)
B = bytes.fromhex("22" * 32)
C = bytes.fromhex("33" * 32)
MAX_PAYLOAD_BYTES = 1_048_576

PROFILES = (
    "normal",
    "ack_loss_confirmed",
    "ack_loss_unavailable_then_confirmed",
    "ack_loss_unavailable_until_budget_block",
    "wrong_delta_confirmed",
)
LIFECYCLES = (
    "OPEN",
    "PUBLISHING",
    "RECOVERY_PENDING",
    "RECOVERY_ACTIVE",
    "RECOVERED_WITNESS_LIVE",
    "RECOVERED_WITNESS_SPENT",
    "BLOCKED_WITNESS_LIVE",
    "BLOCKED_WITNESS_SPENT",
    "POISONED_NO_MARKER",
)
OPERATIONS = (
    "publish",
    "acquire_epoch",
    "release_epoch",
    "abandon_epoch",
    "replay_epoch",
    "consume_witness",
)

PUBLIC_ALL = [
    "SyntheticRecoveryCoordinatorV10Error",
    "SyntheticRecoveryMarkerV10",
    "SyntheticRecoverySnapshotV10",
    "SyntheticRecoveryActionV10",
    "SyntheticRecoveryEpochV10",
    "SyntheticRecoveryWitnessV10",
    "SyntheticRecoveryCoordinatorV10",
    "new_synthetic_recovery_coordinator_v1_0",
    "snapshot_synthetic_recovery_coordinator_v1_0",
    "publish_with_synthetic_recovery_coordinator_v1_0",
    "acquire_synthetic_recovery_epoch_v1_0",
    "release_synthetic_recovery_epoch_v1_0",
    "abandon_synthetic_recovery_epoch_v1_0",
    "replay_synthetic_recovery_epoch_v1_0",
    "consume_synthetic_recovery_witness_v1_0",
]

MARKER_FIELDS = (
    "marker_schema_version",
    "marker_scope",
    "origin_status",
    "constructor_profile",
    "coordinator_config_sha256",
    "marker_kind",
    "marker_ordinal",
    "phase2b1_failure_codes",
    "publisher_outcome",
    "publisher_operation_sha256",
    "publisher_transition_sha256",
    "synthetic_fault_outcome",
    "synthetic_fault_transition_sha256",
    "replay_plan_sha256",
    "replay_plan_row_count",
    "before_state_version_sha256",
    "intended_after_state_version_sha256",
    "actual_after_state_version_sha256",
    "intended_delta_sha256",
    "actual_delta_sha256",
    "stage_payload_bytes",
    "stage_payload_sha256",
    "marker_sha256",
    "caller_profile_scope",
    "cause_scope",
    "journal_scope",
    "stage_binding_scope",
    "failure_code_scope",
    "cleanup_scope",
    "marker_provenance",
    "authority_scope",
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)
SNAPSHOT_FIELDS = (
    "snapshot_schema_version",
    "snapshot_scope",
    "origin_status",
    "constructor_profile",
    "profile_status",
    "alternate_payload_bytes",
    "alternate_payload_sha256",
    "coordinator_config_sha256",
    "lifecycle_state",
    "marker",
    "marker_count",
    "epoch_issue_count",
    "replay_attempt_count",
    "active_epoch_ordinal",
    "active_epoch_nonce_sha256",
    "terminal_epoch_ordinal",
    "terminal_epoch_nonce_sha256",
    "witness_status",
    "witness_purpose",
    "witness_nonce_sha256",
    "terminal_kind",
    "terminal_reason",
    "terminal_sha256",
    "snapshot_sha256",
    "marker_count_upper_bound",
    "active_epoch_upper_bound",
    "recovery_epoch_upper_bound",
    "witness_count_upper_bound",
    "retained_payload_reference_upper_bound_bytes",
    "retained_payload_copy_upper_bound_bytes",
    "fixed_profile_scope",
    "coordinator_ownership_scope",
    "concurrency_scope",
    "raw_bypass_scope",
    "collision_nonce_scope",
    "replay_scope",
    "witness_scope",
    "detached_record_scope",
    "tamper_scope",
    "pre_marker_error_scope",
    "stage_residue_scope",
    "cleanup_scope",
    "journal_scope",
    "process_restart_scope",
    "manifest_scope",
    "remote_publication",
    "authority_scope",
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)
ACTION_FIELDS = (
    "action_schema_version",
    "action_scope",
    "origin_status",
    "operation",
    "outcome",
    "reason_codes",
    "before_snapshot_sha256",
    "after_snapshot",
    "endpoint_state_changed",
    "publish_result",
    "marker",
    "issued_epoch",
    "issued_witness",
    "terminal_sha256",
    "epoch_ordinal",
    "replay_observation",
    "action_sha256",
    "exclusion_scope",
    "action_record_scope",
    "opaque_handle_scope",
    "hash_authority_scope",
    "cleanup_scope",
    "stage_residue_scope",
    "journal_scope",
    "process_scope",
    "remote_reobservation_scope",
    "manifest_scope",
    "authority_scope",
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

NEGATIVE_SNAPSHOT_FIELDS = {
    "fixed_profile_scope": "immutable_caller_selected_five_row_synthetic_profile",
    "coordinator_ownership_scope": "same_live_coordinator_owned_phase2b2d_call_only",
    "concurrency_scope": "same_live_coordinator_exclusion_only",
    "raw_bypass_scope": "raw_phase2b2d_and_cross_process_bypass_not_prevented",
    "collision_nonce_scope": "phase2b2d_collision_nonce_not_epoch_identity",
    "replay_scope": "bounded_same_kernel_replay_no_stage_or_remote_reobservation",
    "witness_scope": "same_instance_object_identity_single_use_witness",
    "detached_record_scope": "detached_records_and_hashes_forgeable_not_capabilities",
    "tamper_scope": "private_slot_reflection_or_module_monkeypatch_tampering_not_prevented",
    "pre_marker_error_scope": "pre_marker_errors_and_outside_calls_unjournaled",
    "stage_residue_scope": "stage_residue_may_remain_not_owned_current_durable_or_safe_to_remove",
    "cleanup_scope": "not_performed_unsafe_without_later_artifact_archive_binding",
    "journal_scope": "single_slot_in_memory_marker_not_durable_journal",
    "process_restart_scope": "no_restart_reconstruction_or_crash_recovery",
    "manifest_scope": "not_read_or_written",
    "remote_publication": "not_performed",
    "authority_scope": "none",
}

D_CONFIG = b"lean-rgc-uprime-u1-synthetic-recovery-config-v1\0"
D_PLAN = b"lean-rgc-uprime-u1-synthetic-recovery-plan-v1\0"
D_MARKER = b"lean-rgc-uprime-u1-synthetic-recovery-marker-v1\0"
D_EPOCH_NONCE = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-nonce-v1\0"
D_EPOCH = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-v1\0"
D_TERMINAL = b"lean-rgc-uprime-u1-synthetic-recovery-terminal-v1\0"
D_WITNESS_NONCE = b"lean-rgc-uprime-u1-synthetic-recovery-witness-nonce-v1\0"
D_WITNESS = b"lean-rgc-uprime-u1-synthetic-recovery-witness-v1\0"
D_SNAPSHOT = b"lean-rgc-uprime-u1-synthetic-recovery-snapshot-v1\0"
D_ACTION = b"lean-rgc-uprime-u1-synthetic-recovery-action-v1\0"


def _h(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _u8(value: int) -> bytes:
    return bytes((value,))


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _k(value: str) -> bytes:
    raw = value.encode("ascii")
    return _u16(len(raw)) + raw


def _rh(value: str) -> bytes:
    return bytes.fromhex(value)


def _q(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _rh(value)


def _j(value: int | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _u64(value)


def _s(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _k(value)


def _t(values: tuple[str, ...]) -> bytes:
    return _u16(len(values)) + b"".join(_k(value) for value in values)


def _n(value: bytes | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _u64(len(value)) + value


def _config(profile: str, alternate: bytes | None) -> str:
    return _h(D_CONFIG + _k(profile) + _n(alternate))


def _plan(profile: str, rows: tuple[tuple[str, str], ...]) -> str:
    return _h(
        D_PLAN
        + _k(profile)
        + _u16(len(rows))
        + b"".join(_k(observation) + _rh(digest) for observation, digest in rows)
    )


def _marker_digest(marker: recovery.SyntheticRecoveryMarkerV10) -> str:
    return _h(
        D_MARKER
        + _rh(marker.coordinator_config_sha256)
        + _u64(marker.marker_ordinal)
        + _k(marker.marker_kind)
        + _t(marker.phase2b1_failure_codes)
        + _k(marker.publisher_outcome)
        + _rh(marker.publisher_operation_sha256)
        + _rh(marker.publisher_transition_sha256)
        + _k(marker.synthetic_fault_outcome)
        + _rh(marker.synthetic_fault_transition_sha256)
        + _rh(marker.replay_plan_sha256)
        + _u16(marker.replay_plan_row_count)
        + _rh(marker.before_state_version_sha256)
        + _rh(marker.intended_after_state_version_sha256)
        + _rh(marker.actual_after_state_version_sha256)
        + _rh(marker.intended_delta_sha256)
        + _rh(marker.actual_delta_sha256)
        + _u64(marker.stage_payload_bytes)
        + _rh(marker.stage_payload_sha256)
    )


def _epoch_nonce(config: str, marker: str, ordinal: int) -> str:
    return _h(D_EPOCH_NONCE + _rh(config) + _rh(marker) + _u64(ordinal))


def _epoch_digest(config: str, marker: str, ordinal: int, nonce: str) -> str:
    return _h(
        D_EPOCH + _rh(config) + _rh(marker) + _u64(ordinal) + _rh(nonce)
    )


def _terminal_digest(snapshot: recovery.SyntheticRecoverySnapshotV10) -> str:
    assert snapshot.marker is not None
    assert snapshot.terminal_kind is not None
    assert snapshot.terminal_reason is not None
    assert snapshot.terminal_epoch_ordinal is not None
    assert snapshot.terminal_epoch_nonce_sha256 is not None
    return _h(
        D_TERMINAL
        + _rh(snapshot.coordinator_config_sha256)
        + _rh(snapshot.marker.marker_sha256)
        + _k(snapshot.terminal_kind)
        + _k(snapshot.terminal_reason)
        + _u64(snapshot.terminal_epoch_ordinal)
        + _rh(snapshot.terminal_epoch_nonce_sha256)
        + _u64(snapshot.epoch_issue_count)
        + _u64(snapshot.replay_attempt_count)
    )


def _witness_nonce(config: str, terminal: str, purpose: str) -> str:
    return _h(D_WITNESS_NONCE + _rh(config) + _rh(terminal) + _k(purpose))


def _witness_digest(config: str, terminal: str, purpose: str, nonce: str) -> str:
    return _h(
        D_WITNESS
        + _rh(config)
        + _rh(terminal)
        + _k(purpose)
        + _rh(nonce)
    )


def _snapshot_digest(snapshot: recovery.SyntheticRecoverySnapshotV10) -> str:
    return _h(
        D_SNAPSHOT
        + _k(snapshot.constructor_profile)
        + _k(snapshot.profile_status)
        + _j(snapshot.alternate_payload_bytes)
        + _q(snapshot.alternate_payload_sha256)
        + _rh(snapshot.coordinator_config_sha256)
        + _k(snapshot.lifecycle_state)
        + _q(None if snapshot.marker is None else snapshot.marker.marker_sha256)
        + _u64(snapshot.marker_count)
        + _u64(snapshot.epoch_issue_count)
        + _u64(snapshot.replay_attempt_count)
        + _j(snapshot.active_epoch_ordinal)
        + _q(snapshot.active_epoch_nonce_sha256)
        + _j(snapshot.terminal_epoch_ordinal)
        + _q(snapshot.terminal_epoch_nonce_sha256)
        + _k(snapshot.witness_status)
        + _s(snapshot.witness_purpose)
        + _q(snapshot.witness_nonce_sha256)
        + _s(snapshot.terminal_kind)
        + _s(snapshot.terminal_reason)
        + _q(snapshot.terminal_sha256)
    )


def _action_digest(action: recovery.SyntheticRecoveryActionV10) -> str:
    return _h(
        D_ACTION
        + _k(action.operation)
        + _k(action.outcome)
        + _t(action.reason_codes)
        + _rh(action.before_snapshot_sha256)
        + _rh(action.after_snapshot.snapshot_sha256)
        + _u8(1 if action.endpoint_state_changed else 0)
        + _q(
            None
            if action.publish_result is None
            else action.publish_result.operation_sha256
        )
        + _q(None if action.marker is None else action.marker.marker_sha256)
        + _j(action.epoch_ordinal)
        + _s(action.replay_observation)
        + _q(action.terminal_sha256)
        + _s(action.after_snapshot.witness_purpose)
    )


def _state(payload: bytes | None = A) -> cas.InMemoryFakeCasStateV10:
    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    if payload is None:
        return initial
    return cas.step_in_memory_fake_cas_v1_0(
        initial,
        initial.state_version_sha256,
        payload,
        "apply_intended_acknowledge",
        None,
    ).after_state


def _new(profile: str) -> recovery.SyntheticRecoveryCoordinatorV10:
    return recovery.new_synthetic_recovery_coordinator_v1_0(
        profile,
        C if profile == "wrong_delta_confirmed" else None,
    )


def _publish(
    coordinator: recovery.SyntheticRecoveryCoordinatorV10,
    parent: Path,
    *,
    nonce: str = "10" * 16,
    state: cas.InMemoryFakeCasStateV10 | None = None,
    expected: str | None = None,
    proposal: bytes = B,
) -> recovery.SyntheticRecoveryActionV10:
    before = _state() if state is None else state
    expected_hash = before.state_version_sha256 if expected is None else expected
    action = recovery.publish_with_synthetic_recovery_coordinator_v1_0(
        coordinator,
        str(parent),
        nonce,
        before,
        expected_hash,
        proposal,
    )
    _assert_lifecycle_shape(action.after_snapshot)
    return action


def _arm(
    profile: str,
    parent: Path,
    *,
    nonce: str = "10" * 16,
) -> tuple[recovery.SyntheticRecoveryCoordinatorV10, recovery.SyntheticRecoveryActionV10]:
    coordinator = _new(profile)
    action = _publish(coordinator, parent, nonce=nonce)
    assert action.outcome == "synthetic_marker_committed_result_withheld"
    assert action.after_snapshot.lifecycle_state == "RECOVERY_PENDING"
    return coordinator, action


def _snapshot(
    coordinator: recovery.SyntheticRecoveryCoordinatorV10,
) -> recovery.SyntheticRecoverySnapshotV10:
    snapshot = recovery.snapshot_synthetic_recovery_coordinator_v1_0(coordinator)
    _assert_lifecycle_shape(snapshot)
    return snapshot


def _values(value: object) -> tuple[object, ...]:
    return tuple(getattr(value, item.name) for item in fields(value))


def _rehashed_marker_values(
    marker: recovery.SyntheticRecoveryMarkerV10,
    **changes: object,
) -> tuple[object, ...]:
    cells = {item.name: getattr(marker, item.name) for item in fields(marker)}
    cells.update(changes)
    cells["marker_sha256"] = _marker_digest(SimpleNamespace(**cells))
    return tuple(cells[name] for name in MARKER_FIELDS)


def _rehashed_snapshot_values(
    snapshot: recovery.SyntheticRecoverySnapshotV10,
    **changes: object,
) -> tuple[object, ...]:
    cells = {item.name: getattr(snapshot, item.name) for item in fields(snapshot)}
    cells.update(changes)
    cells["snapshot_sha256"] = _snapshot_digest(SimpleNamespace(**cells))
    return tuple(cells[name] for name in SNAPSHOT_FIELDS)


def _rehashed_terminal_snapshot_values(
    snapshot: recovery.SyntheticRecoverySnapshotV10,
    **changes: object,
) -> tuple[object, ...]:
    cells = {item.name: getattr(snapshot, item.name) for item in fields(snapshot)}
    cells.update(changes)
    cells["terminal_sha256"] = _terminal_digest(SimpleNamespace(**cells))
    cells["witness_nonce_sha256"] = _witness_nonce(
        cells["coordinator_config_sha256"],
        cells["terminal_sha256"],
        cells["witness_purpose"],
    )
    cells["snapshot_sha256"] = _snapshot_digest(SimpleNamespace(**cells))
    return tuple(cells[name] for name in SNAPSHOT_FIELDS)


def _rehashed_action_values(
    action: recovery.SyntheticRecoveryActionV10,
    **changes: object,
) -> tuple[object, ...]:
    cells = {item.name: getattr(action, item.name) for item in fields(action)}
    cells.update(changes)
    cells["action_sha256"] = _action_digest(SimpleNamespace(**cells))
    return tuple(cells[name] for name in ACTION_FIELDS)


def _changed(value: object) -> object:
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        if len(value) == 64 and all(char in "0123456789ABCDEF" for char in value):
            return ("0" if value[0] != "0" else "1") + value[1:]
        return value + "_mutant"
    if type(value) is tuple:
        return value + ("mutant",)
    if value is None:
        return "mutant"
    return None


def _assert_no_authority(value: object) -> None:
    assert value.authority_scope == "none"
    assert value.canonical_remote_authority is False
    assert value.licenses_execution is False
    assert value.licenses_publication is False
    assert value.licenses_recovery is False
    assert value.licenses_later_stage is False


def _assert_lifecycle_shape(
    snapshot: recovery.SyntheticRecoverySnapshotV10,
) -> None:
    state = snapshot.lifecycle_state
    assert state in LIFECYCLES
    assert 0 <= snapshot.marker_count <= 1
    assert 0 <= snapshot.replay_attempt_count <= snapshot.epoch_issue_count <= 4
    if state in {"OPEN", "PUBLISHING", "POISONED_NO_MARKER"}:
        assert snapshot.marker is None and snapshot.marker_count == 0
        assert snapshot.epoch_issue_count == snapshot.replay_attempt_count == 0
    else:
        assert snapshot.marker is not None and snapshot.marker_count == 1
    if state == "OPEN":
        assert snapshot.profile_status in {"normal_no_fault_profile", "armed"}
    elif state == "PUBLISHING":
        assert snapshot.profile_status == "owned_call_in_progress"
    elif state == "POISONED_NO_MARKER":
        assert snapshot.profile_status == "spent_without_marker"
    else:
        assert snapshot.profile_status == "spent_marker_committed"

    if state == "RECOVERY_ACTIVE":
        assert snapshot.active_epoch_ordinal == snapshot.epoch_issue_count
        assert snapshot.active_epoch_nonce_sha256 is not None
    else:
        assert snapshot.active_epoch_ordinal is None
        assert snapshot.active_epoch_nonce_sha256 is None

    terminal = state in {
        "RECOVERED_WITNESS_LIVE",
        "RECOVERED_WITNESS_SPENT",
        "BLOCKED_WITNESS_LIVE",
        "BLOCKED_WITNESS_SPENT",
    }
    if terminal:
        assert snapshot.terminal_epoch_ordinal == snapshot.epoch_issue_count
        assert snapshot.terminal_epoch_nonce_sha256 is not None
        assert snapshot.terminal_kind is not None
        assert snapshot.terminal_reason is not None
        assert snapshot.terminal_sha256 is not None
        assert snapshot.witness_purpose is not None
        assert snapshot.witness_nonce_sha256 is not None
        if state.startswith("RECOVERED_"):
            assert snapshot.terminal_kind == "recovered_terminal"
            assert snapshot.witness_purpose == "record_recovered_terminal"
        else:
            assert snapshot.terminal_kind == "permanent_block"
            assert snapshot.witness_purpose == "record_permanent_block"
        assert snapshot.witness_status == (
            "live" if state.endswith("_LIVE") else "spent"
        )
    else:
        assert snapshot.terminal_epoch_ordinal is None
        assert snapshot.terminal_epoch_nonce_sha256 is None
        assert snapshot.terminal_kind is None
        assert snapshot.terminal_reason is None
        assert snapshot.terminal_sha256 is None
        assert snapshot.witness_status == "none"
        assert snapshot.witness_purpose is None
        assert snapshot.witness_nonce_sha256 is None


def _tree() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))


def test_uprime_synthetic_recovery_coordinator_exact_surface_fields_and_signatures() -> None:
    assert recovery.__all__ == PUBLIC_ALL
    assert issubclass(recovery.SyntheticRecoveryCoordinatorV10Error, RuntimeError)
    assert tuple(item.name for item in fields(recovery.SyntheticRecoveryMarkerV10)) == MARKER_FIELDS
    assert tuple(item.name for item in fields(recovery.SyntheticRecoverySnapshotV10)) == SNAPSHOT_FIELDS
    assert tuple(item.name for item in fields(recovery.SyntheticRecoveryActionV10)) == ACTION_FIELDS
    expected = {
        "new_synthetic_recovery_coordinator_v1_0": (
            ("constructor_profile", "alternate_payload"),
            recovery.SyntheticRecoveryCoordinatorV10,
        ),
        "snapshot_synthetic_recovery_coordinator_v1_0": (
            ("coordinator",),
            recovery.SyntheticRecoverySnapshotV10,
        ),
        "publish_with_synthetic_recovery_coordinator_v1_0": (
            (
                "coordinator",
                "staging_parent",
                "collision_nonce",
                "state",
                "expected_state_version_sha256",
                "proposed_payload",
            ),
            recovery.SyntheticRecoveryActionV10,
        ),
        "acquire_synthetic_recovery_epoch_v1_0": (
            ("coordinator",),
            recovery.SyntheticRecoveryActionV10,
        ),
        "release_synthetic_recovery_epoch_v1_0": (
            ("coordinator", "epoch"),
            recovery.SyntheticRecoveryActionV10,
        ),
        "abandon_synthetic_recovery_epoch_v1_0": (
            ("coordinator", "epoch"),
            recovery.SyntheticRecoveryActionV10,
        ),
        "replay_synthetic_recovery_epoch_v1_0": (
            ("coordinator", "epoch"),
            recovery.SyntheticRecoveryActionV10,
        ),
        "consume_synthetic_recovery_witness_v1_0": (
            ("coordinator", "witness", "expected_purpose", "expected_terminal_sha256"),
            recovery.SyntheticRecoveryActionV10,
        ),
    }
    raw_annotations = {
        "new_synthetic_recovery_coordinator_v1_0": {
            "constructor_profile": "str",
            "alternate_payload": "bytes | None",
            "return": "SyntheticRecoveryCoordinatorV10",
        },
        "snapshot_synthetic_recovery_coordinator_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "return": "SyntheticRecoverySnapshotV10",
        },
        "publish_with_synthetic_recovery_coordinator_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "staging_parent": "str",
            "collision_nonce": "str",
            "state": "InMemoryFakeCasStateV10",
            "expected_state_version_sha256": "str",
            "proposed_payload": "bytes",
            "return": "SyntheticRecoveryActionV10",
        },
        "acquire_synthetic_recovery_epoch_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "return": "SyntheticRecoveryActionV10",
        },
        "release_synthetic_recovery_epoch_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "epoch": "SyntheticRecoveryEpochV10",
            "return": "SyntheticRecoveryActionV10",
        },
        "abandon_synthetic_recovery_epoch_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "epoch": "SyntheticRecoveryEpochV10",
            "return": "SyntheticRecoveryActionV10",
        },
        "replay_synthetic_recovery_epoch_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "epoch": "SyntheticRecoveryEpochV10",
            "return": "SyntheticRecoveryActionV10",
        },
        "consume_synthetic_recovery_witness_v1_0": {
            "coordinator": "SyntheticRecoveryCoordinatorV10",
            "witness": "SyntheticRecoveryWitnessV10",
            "expected_purpose": "str",
            "expected_terminal_sha256": "str",
            "return": "SyntheticRecoveryActionV10",
        },
    }
    for name, (names, return_type) in expected.items():
        function = getattr(recovery, name)
        signature = inspect.signature(function)
        assert tuple(signature.parameters) == names
        assert all(
            parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            and parameter.default is inspect.Parameter.empty
            for parameter in signature.parameters.values()
        )
        assert function.__annotations__ == raw_annotations[name]
        assert get_type_hints(function)["return"] is return_type


def test_uprime_synthetic_recovery_coordinator_exact_import_ast_and_public_count() -> None:
    tree = _tree()
    imports: list[tuple[str, tuple[str, ...] | None]] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            imports.append((node.module or "", tuple(alias.name for alias in node.names)))
        elif isinstance(node, ast.Import):
            imports.extend((alias.name, None) for alias in node.names)
    assert imports == [
        ("__future__", ("annotations",)),
        ("dataclasses", ("dataclass",)),
        ("hashlib", None),
        ("re", None),
        ("threading", None),
        (
            "lean_rgc.evals.uprime_rpc_fake_cas_kernel",
            (
                "InMemoryFakeCasStateV10",
                "InMemoryFakeCasTransitionV10",
                "InMemoryFakeCasV10Error",
                "step_in_memory_fake_cas_v1_0",
            ),
        ),
        (
            "lean_rgc.evals.uprime_rpc_local_staging_fake_publisher",
            (
                "LocalStagingFakePublishResultV10",
                "LocalStagingFakePublisherV10Error",
                "stage_and_fake_publish_normal_v1_0",
            ),
        ),
    ]
    public_exceptions = [
        getattr(recovery, name)
        for name in recovery.__all__
        if inspect.isclass(getattr(recovery, name))
        and issubclass(getattr(recovery, name), BaseException)
    ]
    assert public_exceptions == [recovery.SyntheticRecoveryCoordinatorV10Error]


def test_uprime_synthetic_recovery_coordinator_records_are_frozen_slotted() -> None:
    coordinator = _new("normal")
    snapshot = _snapshot(coordinator)
    assert snapshot.__slots__ == SNAPSHOT_FIELDS
    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.lifecycle_state = "mutant"  # type: ignore[misc]
    clone = recovery.SyntheticRecoverySnapshotV10(*_values(snapshot))
    assert clone == snapshot and clone is not snapshot
    assert not hasattr(snapshot, "__dict__")
    assert recovery.SyntheticRecoveryMarkerV10.__slots__ == MARKER_FIELDS
    assert recovery.SyntheticRecoveryActionV10.__slots__ == ACTION_FIELDS
    for cls in (
        recovery.SyntheticRecoveryMarkerV10,
        recovery.SyntheticRecoverySnapshotV10,
        recovery.SyntheticRecoveryActionV10,
    ):
        with pytest.raises(Exception):
            type(f"Forbidden{cls.__name__}", (cls,), {})


def test_uprime_synthetic_recovery_coordinator_live_classes_slots_and_factory_only() -> None:
    assert recovery.SyntheticRecoveryEpochV10.__slots__ == (
        "_issuer",
        "_epoch_ordinal",
        "_epoch_nonce_sha256",
        "_epoch_sha256",
    )
    assert tuple(
        name
        for name, value in recovery.SyntheticRecoveryEpochV10.__dict__.items()
        if isinstance(value, property)
    ) == ("epoch_ordinal", "epoch_nonce_sha256", "epoch_sha256")
    assert recovery.SyntheticRecoveryWitnessV10.__slots__ == (
        "_issuer",
        "_purpose",
        "_terminal_sha256",
        "_witness_nonce_sha256",
        "_witness_sha256",
    )
    assert tuple(
        name
        for name, value in recovery.SyntheticRecoveryWitnessV10.__dict__.items()
        if isinstance(value, property)
    ) == (
        "purpose",
        "terminal_sha256",
        "witness_nonce_sha256",
        "witness_sha256",
    )
    assert recovery.SyntheticRecoveryCoordinatorV10.__slots__ == (
        "_lock",
        "_issuer",
        "_profile",
        "_alternate_payload",
        "_config_sha256",
        "_publishing_state",
        "_poisoned_state",
        "_state",
    )
    for cls in (
        recovery.SyntheticRecoveryEpochV10,
        recovery.SyntheticRecoveryWitnessV10,
        recovery.SyntheticRecoveryCoordinatorV10,
    ):
        with pytest.raises(Exception):
            cls()  # type: ignore[call-arg]
        with pytest.raises(Exception):
            type("ForbiddenSubclass", (cls,), {})
    coordinator = _new("normal")
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(Exception):
            operation(coordinator)


def test_uprime_synthetic_recovery_coordinator_profile_and_alternate_boundaries() -> None:
    for profile in PROFILES[:4]:
        coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(profile, None)
        assert _snapshot(coordinator).constructor_profile == profile
        for alternate in (b"", C, bytearray(), memoryview(b"x"), "x", False):
            with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
                recovery.new_synthetic_recovery_coordinator_v1_0(profile, alternate)  # type: ignore[arg-type]
    for alternate in (b"", C, b"x" * MAX_PAYLOAD_BYTES):
        coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
            "wrong_delta_confirmed", alternate
        )
        snapshot = _snapshot(coordinator)
        assert coordinator._alternate_payload is alternate
        assert snapshot.alternate_payload_bytes == len(alternate)
        assert snapshot.alternate_payload_sha256 == _h(alternate)
    for alternate in (None, bytearray(C), memoryview(C), b"x" * (MAX_PAYLOAD_BYTES + 1)):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            recovery.new_synthetic_recovery_coordinator_v1_0(
                "wrong_delta_confirmed", alternate  # type: ignore[arg-type]
            )
    for profile in ("", "Normal", "normal\x00", False, 1, None):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            recovery.new_synthetic_recovery_coordinator_v1_0(profile, None)  # type: ignore[arg-type]


def test_uprime_synthetic_recovery_coordinator_initial_snapshots_and_negative_labels() -> None:
    for profile in PROFILES:
        snapshot = _snapshot(_new(profile))
        assert snapshot.lifecycle_state == "OPEN"
        assert snapshot.profile_status == (
            "normal_no_fault_profile" if profile == "normal" else "armed"
        )
        assert snapshot.marker is None and snapshot.marker_count == 0
        assert snapshot.epoch_issue_count == snapshot.replay_attempt_count == 0
        assert snapshot.active_epoch_ordinal is None
        assert snapshot.terminal_epoch_ordinal is None
        assert snapshot.witness_status == "none"
        assert snapshot.witness_purpose is snapshot.witness_nonce_sha256 is None
        assert snapshot.terminal_kind is snapshot.terminal_reason is None
        assert snapshot.terminal_sha256 is None
        assert snapshot.marker_count_upper_bound == 1
        assert snapshot.active_epoch_upper_bound == 1
        assert snapshot.recovery_epoch_upper_bound == 4
        assert snapshot.witness_count_upper_bound == 1
        assert snapshot.retained_payload_reference_upper_bound_bytes == 3_145_728
        assert snapshot.retained_payload_copy_upper_bound_bytes == 0
        for name, expected in NEGATIVE_SNAPSHOT_FIELDS.items():
            assert getattr(snapshot, name) == expected
        _assert_no_authority(snapshot)


def test_uprime_synthetic_recovery_coordinator_config_goldens_and_maximum() -> None:
    normal = _snapshot(_new("normal"))
    wrong = _snapshot(
        recovery.new_synthetic_recovery_coordinator_v1_0(
            "wrong_delta_confirmed", b"C"
        )
    )
    assert normal.coordinator_config_sha256 == _config("normal", None)
    assert normal.coordinator_config_sha256 == (
        "0D68B8B1D6B42C8F4B997C2FE7DF5A5C20202AD122B3D14BFAECE54E25F64AF6"
    )
    assert wrong.coordinator_config_sha256 == _config("wrong_delta_confirmed", b"C")
    assert wrong.coordinator_config_sha256 == (
        "5A34577883038E7C9DFA57FF7A9756A37AD626E826DDAB81A8C2BDF7BF5F4298"
    )
    assert len(D_CONFIG) + len(_k("wrong_delta_confirmed")) + 1 + 8 + MAX_PAYLOAD_BYTES == 1_048_656
    assert _plan(
        "ack_loss_unavailable_then_confirmed",
        (("unavailable", "11" * 32), ("confirmed_intended", "22" * 32)),
    ) == "6BC4CDF9E2E901BDC799198CCC81443188C0D07C68599D34FE7584F1BB33AAE5"
    assert _plan(
        "wrong_delta_confirmed", (("confirmed_wrong_delta", "CC" * 32),)
    ) == "F754028D8E353EA09F32320B39FC651D5B20FE29A9C004456663FA0D100368E5"


def test_uprime_synthetic_recovery_coordinator_publish_conflict_and_identical_no_stage(
    tmp_path: Path,
) -> None:
    state = _state()
    absent = _state(None)
    for profile in PROFILES:
        coordinator = _new(profile)
        missing = tmp_path / f"missing-{profile}"
        conflict = _publish(
            coordinator,
            missing,
            nonce="20" * 16,
            state=state,
            expected=absent.state_version_sha256,
        )
        assert conflict.operation == "publish"
        assert conflict.outcome == "cas_conflict_no_marker"
        assert conflict.reason_codes == ("expected_state_version_mismatch",)
        assert conflict.publish_result is not None
        assert conflict.publish_result.outcome == "cas_conflict_no_stage"
        assert conflict.marker is None
        assert conflict.endpoint_state_changed is False
        assert conflict.after_snapshot.lifecycle_state == "OPEN"
        assert not missing.exists()

        identical = _publish(
            coordinator,
            missing,
            nonce="21" * 16,
            state=state,
            proposal=A,
        )
        assert identical.outcome == "cas_existing_identical_no_marker"
        assert identical.reason_codes == ("exact_payload_already_current",)
        assert identical.publish_result is not None
        assert identical.publish_result.outcome == "cas_existing_identical_no_stage"
        assert identical.marker is None
        assert identical.after_snapshot.profile_status == (
            "normal_no_fault_profile" if profile == "normal" else "armed"
        )
        assert not missing.exists()

    # Wrong-delta equality is inspected only on a reached changed branch.
    eager = recovery.new_synthetic_recovery_coordinator_v1_0(
        "wrong_delta_confirmed", A
    )
    conflict = _publish(
        eager,
        tmp_path / "eager-precedence",
        nonce="22" * 16,
        state=state,
        expected=absent.state_version_sha256,
        proposal=B,
    )
    assert conflict.outcome == "cas_conflict_no_marker"
    identical = _publish(
        eager,
        tmp_path / "eager-precedence",
        nonce="23" * 16,
        state=state,
        proposal=A,
    )
    assert identical.outcome == "cas_existing_identical_no_marker"
    assert _snapshot(eager).profile_status == "armed"


def test_uprime_synthetic_recovery_coordinator_normal_changed_result_and_reuse(
    tmp_path: Path,
) -> None:
    coordinator = _new("normal")
    before = _snapshot(coordinator)
    first = _publish(coordinator, tmp_path, nonce="30" * 16)
    assert first.operation == "publish"
    assert first.outcome == "normal_staged_result_exposed_no_marker"
    assert first.reason_codes == (
        "exact_stage_retained_before_exposing_synthetic_acknowledged_transition",
    )
    assert first.publish_result is not None
    assert first.publish_result.outcome == "staged_intended_fake_publish_acknowledged"
    assert first.marker is None and first.after_snapshot.marker is None
    assert first.after_snapshot.lifecycle_state == "OPEN"
    assert first.endpoint_state_changed is False
    assert first.before_snapshot_sha256 == before.snapshot_sha256
    assert first.after_snapshot.snapshot_sha256 == before.snapshot_sha256
    assert Path(first.publish_result.stage_path).read_bytes() == B
    second = _publish(coordinator, tmp_path, nonce="31" * 16)
    assert second.outcome == first.outcome
    assert Path(second.publish_result.stage_path).read_bytes() == B  # type: ignore[union-attr]
    assert first.publish_result.stage_path != second.publish_result.stage_path  # type: ignore[union-attr]


def test_uprime_synthetic_recovery_coordinator_nonnormal_marker_rows_and_codes(
    tmp_path: Path,
) -> None:
    expected = {
        "ack_loss_confirmed": (
            "synthetic_ack_loss_confirmed",
            "intended_applied_ack_lost_confirmed",
            1,
        ),
        "ack_loss_unavailable_then_confirmed": (
            "synthetic_ack_loss_unavailable",
            "intended_applied_ack_lost_unconfirmed",
            2,
        ),
        "ack_loss_unavailable_until_budget_block": (
            "synthetic_ack_loss_unavailable",
            "intended_applied_ack_lost_unconfirmed",
            4,
        ),
        "wrong_delta_confirmed": (
            "synthetic_wrong_delta_confirmed",
            "wrong_delta_confirmed",
            1,
        ),
    }
    for index, (profile, row) in enumerate(expected.items(), 1):
        parent = tmp_path / profile
        parent.mkdir()
        coordinator, action = _arm(profile, parent, nonce=f"{index + 40:02x}" * 16)
        marker = action.marker
        assert action.operation == "publish"
        assert action.publish_result is None
        assert action.outcome == "synthetic_marker_committed_result_withheld"
        assert action.reason_codes == ("synthetic_marker_committed",)
        assert action.endpoint_state_changed is True
        assert marker is action.after_snapshot.marker and marker is not None
        assert marker.constructor_profile == profile
        assert marker.marker_kind == row[0]
        assert marker.synthetic_fault_outcome == row[1]
        assert marker.replay_plan_row_count == row[2]
        assert marker.marker_ordinal == action.after_snapshot.marker_count == 1
        assert marker.phase2b1_failure_codes == ("OTHER_HARNESS_ERROR",)
        assert marker.publisher_outcome == "staged_intended_fake_publish_acknowledged"
        assert marker.stage_payload_bytes == len(B)
        assert marker.stage_payload_sha256 == _h(B)
        assert action.after_snapshot.profile_status == "spent_marker_committed"
        assert action.after_snapshot.lifecycle_state == "RECOVERY_PENDING"
        assert action.after_snapshot.coordinator_config_sha256 == marker.coordinator_config_sha256
        retained = list(parent.iterdir())
        assert len(retained) == 1
        assert retained[0].read_bytes() == B
        _assert_no_authority(marker)
        _assert_no_authority(action)
        assert _snapshot(coordinator) == action.after_snapshot


def test_uprime_synthetic_recovery_coordinator_wrong_delta_relational_precedence(
    tmp_path: Path,
) -> None:
    state_a = _state(A)
    absent = _state(None)
    # Stale version dominates an alternate equal to the proposal.
    conflict_coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
        "wrong_delta_confirmed", B
    )
    conflict = _publish(
        conflict_coordinator,
        tmp_path / "missing-conflict",
        state=state_a,
        expected=absent.state_version_sha256,
        proposal=B,
    )
    assert conflict.outcome == "cas_conflict_no_marker"
    assert _snapshot(conflict_coordinator).profile_status == "armed"
    # Exact identity dominates an alternate equal to current/proposal.
    identical_coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
        "wrong_delta_confirmed", A
    )
    identical = _publish(
        identical_coordinator,
        tmp_path / "missing-identical",
        state=state_a,
        proposal=A,
    )
    assert identical.outcome == "cas_existing_identical_no_marker"
    assert _snapshot(identical_coordinator).profile_status == "armed"
    # A reached changed branch rejects equality before the physical call.
    for current, proposal, alternate in ((A, B, B), (A, B, A)):
        coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
            "wrong_delta_confirmed", alternate
        )
        parent = tmp_path / f"invalid-{alternate[0]}"
        parent.mkdir()
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            _publish(coordinator, parent, state=_state(current), proposal=proposal)
        assert _snapshot(coordinator).lifecycle_state == "OPEN"
        assert list(parent.iterdir()) == []


def test_uprime_synthetic_recovery_coordinator_publish_excluded_in_every_nonopen_state(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="50" * 16)
    pending = _snapshot(coordinator)
    action = _publish(
        coordinator,
        tmp_path / "not-touched",
        nonce="not-a-nonce",
        state="not-a-state",  # type: ignore[arg-type]
        expected="bad",
        proposal=b"",
    )
    assert action.outcome == "publisher_excluded_non_open"
    assert action.reason_codes == ("coordinator_not_open",)
    assert action.endpoint_state_changed is False
    assert action.after_snapshot == pending
    acquired = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    assert acquired.outcome == "epoch_issued"
    active = _snapshot(coordinator)
    excluded = _publish(
        coordinator,
        tmp_path / "still-not-touched",
        nonce="bad",
        state="bad",  # type: ignore[arg-type]
        expected="bad",
    )
    assert excluded.outcome == "publisher_excluded_non_open"
    assert excluded.after_snapshot == active


def test_uprime_synthetic_recovery_coordinator_marker_constructor_revalidates_every_field(
    tmp_path: Path,
) -> None:
    _, action = _arm("wrong_delta_confirmed", tmp_path, nonce="51" * 16)
    marker = action.marker
    assert marker is not None
    assert recovery.SyntheticRecoveryMarkerV10(*_values(marker)) == marker
    for item in fields(marker):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            replace(marker, **{item.name: _changed(getattr(marker, item.name))})


def test_uprime_synthetic_recovery_coordinator_marker_rejects_coherently_rehashed_row_mutants(
    tmp_path: Path,
) -> None:
    ack_parent = tmp_path / "marker-ack"
    ack_parent.mkdir()
    _, ack_action = _arm("ack_loss_confirmed", ack_parent, nonce="5c" * 16)
    ack = ack_action.marker
    wrong_parent = tmp_path / "marker-wrong"
    wrong_parent.mkdir()
    _, wrong_action = _arm(
        "wrong_delta_confirmed", wrong_parent, nonce="5d" * 16
    )
    wrong = wrong_action.marker
    assert ack is not None and wrong is not None
    mutants = (
        _rehashed_marker_values(
            ack,
            marker_kind="synthetic_wrong_delta_confirmed",
        ),
        _rehashed_marker_values(ack, replay_plan_row_count=2),
        _rehashed_marker_values(
            ack,
            actual_after_state_version_sha256="A0" * 32,
        ),
        _rehashed_marker_values(
            ack,
            before_state_version_sha256=ack.intended_after_state_version_sha256,
        ),
        _rehashed_marker_values(
            wrong,
            actual_after_state_version_sha256=wrong.intended_after_state_version_sha256,
            actual_delta_sha256=wrong.intended_delta_sha256,
        ),
        _rehashed_marker_values(ack, marker_ordinal=True),
        _rehashed_marker_values(
            ack,
            phase2b1_failure_codes=("POWER_LOSS",),
        ),
    )
    for index, values in enumerate(mutants):
        try:
            recovery.SyntheticRecoveryMarkerV10(*values)
        except recovery.SyntheticRecoveryCoordinatorV10Error:
            continue
        pytest.fail(f"coherently rehashed marker mutant {index} was accepted")


def test_uprime_synthetic_recovery_coordinator_snapshot_constructor_revalidates_every_field(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="52" * 16)
    epoch_action = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    terminal_action = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, epoch_action.issued_epoch
    )
    snapshot = terminal_action.after_snapshot
    assert recovery.SyntheticRecoverySnapshotV10(*_values(snapshot)) == snapshot
    for item in fields(snapshot):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            replace(snapshot, **{item.name: _changed(getattr(snapshot, item.name))})


def test_uprime_synthetic_recovery_coordinator_snapshot_rejects_rehashed_unreachable_terminal_rows(
    tmp_path: Path,
) -> None:
    ack_parent = tmp_path / "ack"
    ack_parent.mkdir()
    ack, _ = _arm("ack_loss_confirmed", ack_parent, nonce="52" * 16)
    ack_issue = recovery.acquire_synthetic_recovery_epoch_v1_0(ack)
    ack_active = ack_issue.after_snapshot
    ack_epoch = ack_issue.issued_epoch
    ack_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        ack, ack_epoch
    ).after_snapshot

    wrong_parent = tmp_path / "wrong"
    wrong_parent.mkdir()
    wrong, _ = _arm("wrong_delta_confirmed", wrong_parent, nonce="55" * 16)
    wrong_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(wrong).issued_epoch
    wrong_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        wrong, wrong_epoch
    ).after_snapshot

    two_row_parent = tmp_path / "two-row"
    two_row_parent.mkdir()
    two_row, _ = _arm(
        "ack_loss_unavailable_then_confirmed",
        two_row_parent,
        nonce="56" * 16,
    )
    first = recovery.acquire_synthetic_recovery_epoch_v1_0(two_row).issued_epoch
    recovery.replay_synthetic_recovery_epoch_v1_0(two_row, first)
    second = recovery.acquire_synthetic_recovery_epoch_v1_0(two_row).issued_epoch
    two_row_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        two_row, second
    ).after_snapshot

    four_row_parent = tmp_path / "four-row"
    four_row_parent.mkdir()
    four_row, _ = _arm(
        "ack_loss_unavailable_until_budget_block",
        four_row_parent,
        nonce="57" * 16,
    )
    four_row_terminal = None
    for _ in range(4):
        epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(four_row).issued_epoch
        four_row_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
            four_row, epoch
        ).after_snapshot
    assert four_row_terminal is not None

    mutants = (
        # Active and terminal nonce labels are derived, not arbitrary hex64 cells.
        _rehashed_snapshot_values(
            ack_active,
            active_epoch_nonce_sha256="F0" * 32,
        ),
        _rehashed_terminal_snapshot_values(
            ack_terminal,
            terminal_epoch_nonce_sha256="F1" * 32,
        ),
        # The one-row confirmed profile cannot recover without one replay.
        _rehashed_terminal_snapshot_values(
            ack_terminal,
            replay_attempt_count=0,
        ),
        # A release/abandon budget block is reachable only at epoch ordinal four.
        _rehashed_terminal_snapshot_values(
            wrong_terminal,
            replay_attempt_count=0,
            terminal_reason="recovery_epoch_budget_exhausted_after_release",
        ),
        # The second row cannot confirm until both fixed replay rows are consumed.
        _rehashed_terminal_snapshot_values(
            two_row_terminal,
            replay_attempt_count=1,
        ),
        # The unavailable-until-block profile has no recovered terminal row.
        _rehashed_terminal_snapshot_values(
            four_row_terminal,
            lifecycle_state="RECOVERED_WITNESS_LIVE",
            terminal_kind="recovered_terminal",
            terminal_reason="synthetic_intended_transition_confirmed",
            witness_purpose="record_recovered_terminal",
        ),
    )
    for values in mutants:
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            recovery.SyntheticRecoverySnapshotV10(*values)


def test_uprime_synthetic_recovery_coordinator_action_constructor_and_nullability(
    tmp_path: Path,
) -> None:
    coordinator, marker_action = _arm(
        "ack_loss_confirmed", tmp_path, nonce="53" * 16
    )
    epoch_action = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    terminal_action = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, epoch_action.issued_epoch
    )
    for action in (marker_action, epoch_action, terminal_action):
        _assert_lifecycle_shape(action.after_snapshot)
        assert recovery.SyntheticRecoveryActionV10(*_values(action)) == action
        assert action.marker is action.after_snapshot.marker
        assert action.action_sha256 == action.action_sha256.upper()
        _assert_no_authority(action)
    assert marker_action.publish_result is None
    assert marker_action.issued_epoch is marker_action.issued_witness is None
    assert epoch_action.issued_epoch is not None and epoch_action.issued_witness is None
    assert epoch_action.epoch_ordinal == 1
    assert terminal_action.issued_epoch is None
    assert terminal_action.issued_witness is not None
    assert terminal_action.terminal_sha256 == terminal_action.after_snapshot.terminal_sha256
    assert terminal_action.replay_observation == "confirmed_intended"
    for item in fields(terminal_action):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            replace(
                terminal_action,
                **{item.name: _changed(getattr(terminal_action, item.name))},
            )

    normal_action = _publish(_new("normal"), tmp_path, nonce="54" * 16)
    exact_result = normal_action.publish_result
    assert type(exact_result) is publisher.LocalStagingFakePublishResultV10
    object.__setattr__(exact_result, "outcome", "bypass-mutated-detached-value")
    # The detached Action boundary is deliberately exact-type/reference-hash only;
    # production performs the deeper Result reconstruction before Action exposure.
    assert recovery.SyntheticRecoveryActionV10(*_values(normal_action)) == normal_action
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        replace(
            normal_action,
            publish_result=SimpleNamespace(
                operation_sha256=exact_result.operation_sha256
            ),
        )


def test_uprime_synthetic_recovery_coordinator_action_rejects_rehashed_row_and_ordinal_mismatch(
    tmp_path: Path,
) -> None:
    open_noop = recovery.acquire_synthetic_recovery_epoch_v1_0(_new("normal"))
    parent = tmp_path / "action-row"
    parent.mkdir()
    coordinator, _ = _arm("ack_loss_confirmed", parent, nonce="58" * 16)
    issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, issued.issued_epoch
    )
    terminal_noop = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)

    later_parent = tmp_path / "later-pending"
    later_parent.mkdir()
    later, marker_commit = _arm(
        "ack_loss_confirmed", later_parent, nonce="59" * 16
    )
    later_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(
        later
    ).issued_epoch
    later_pending = recovery.release_synthetic_recovery_epoch_v1_0(
        later, later_epoch
    ).after_snapshot

    retry_parent = tmp_path / "unavailable-retry"
    retry_parent.mkdir()
    retry_coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed",
        retry_parent,
        nonce="5a" * 16,
    )
    retry_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(
        retry_coordinator
    ).issued_epoch
    retry_action = recovery.replay_synthetic_recovery_epoch_v1_0(
        retry_coordinator, retry_epoch
    )

    zero_parent = tmp_path / "unavailable-zero-cursor"
    zero_parent.mkdir()
    zero_coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed",
        zero_parent,
        nonce="5b" * 16,
    )
    zero_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(
        zero_coordinator
    ).issued_epoch
    zero_pending = recovery.release_synthetic_recovery_epoch_v1_0(
        zero_coordinator, zero_epoch
    ).after_snapshot
    mutants = (
        _rehashed_action_values(
            open_noop,
            outcome="publisher_active_excluded",
            reason_codes=("owned_publisher_active",),
        ),
        _rehashed_action_values(issued, epoch_ordinal=2),
        _rehashed_action_values(
            terminal_noop,
            outcome="no_marker_noop",
            reason_codes=("marker_absent",),
        ),
        _rehashed_action_values(
            marker_commit,
            after_snapshot=later_pending,
            marker=later_pending.marker,
        ),
        _rehashed_action_values(
            retry_action,
            after_snapshot=zero_pending,
            marker=zero_pending.marker,
        ),
    )
    assert terminal.after_snapshot.lifecycle_state == "RECOVERED_WITNESS_LIVE"
    for index, values in enumerate(mutants):
        try:
            recovery.SyntheticRecoveryActionV10(*values)
        except recovery.SyntheticRecoveryCoordinatorV10Error:
            continue
        pytest.fail(f"coherently rehashed Action mutant {index} was accepted")


def test_uprime_synthetic_recovery_coordinator_ack_confirmed_recovery_and_terminal_noops(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="60" * 16)
    issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    epoch = issued.issued_epoch
    assert isinstance(epoch, recovery.SyntheticRecoveryEpochV10)
    assert issued.operation == "acquire_epoch"
    assert issued.outcome == "epoch_issued"
    assert issued.reason_codes == ("recovery_marker_pending",)
    assert issued.after_snapshot.lifecycle_state == "RECOVERY_ACTIVE"
    assert issued.after_snapshot.active_epoch_ordinal == 1
    recovered = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    assert recovered.operation == "replay_epoch"
    assert recovered.outcome == "replay_confirmed_recovered"
    assert recovered.reason_codes == ("synthetic_intended_transition_confirmed",)
    assert recovered.replay_observation == "confirmed_intended"
    assert recovered.after_snapshot.lifecycle_state == "RECOVERED_WITNESS_LIVE"
    assert recovered.after_snapshot.terminal_kind == "recovered_terminal"
    assert recovered.after_snapshot.terminal_reason == (
        "synthetic_intended_transition_confirmed"
    )
    assert recovered.after_snapshot.witness_purpose == "record_recovered_terminal"
    assert recovered.issued_witness is not None
    acquire_noop = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    assert acquire_noop.outcome == "recovered_terminal_noop"
    assert acquire_noop.issued_epoch is acquire_noop.issued_witness is None
    replay_noop = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    assert replay_noop.outcome == "recovered_terminal_noop"
    assert replay_noop.replay_observation == "terminal_noop"
    assert replay_noop.endpoint_state_changed is False


def test_uprime_synthetic_recovery_coordinator_unavailable_then_confirmed_schedule(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed", tmp_path, nonce="61" * 16
    )
    first = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    first_epoch = first.issued_epoch
    retry = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, first_epoch)
    assert retry.outcome == "replay_unavailable_retry_pending"
    assert retry.replay_observation == "unavailable"
    assert retry.after_snapshot.lifecycle_state == "RECOVERY_PENDING"
    assert retry.after_snapshot.epoch_issue_count == 1
    assert retry.after_snapshot.replay_attempt_count == 1
    second = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    assert second.epoch_ordinal == 2
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, second.issued_epoch
    )
    assert terminal.outcome == "replay_confirmed_recovered"
    assert terminal.after_snapshot.lifecycle_state == "RECOVERED_WITNESS_LIVE"
    assert terminal.after_snapshot.epoch_issue_count == 2
    assert terminal.after_snapshot.replay_attempt_count == 2
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, first_epoch)


def test_uprime_synthetic_recovery_coordinator_unavailable_fourth_replay_blocks(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm(
        "ack_loss_unavailable_until_budget_block", tmp_path, nonce="62" * 16
    )
    epochs: list[recovery.SyntheticRecoveryEpochV10] = []
    for ordinal in range(1, 5):
        issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
        assert issued.epoch_ordinal == ordinal
        epoch = issued.issued_epoch
        epochs.append(epoch)
        replay = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
        if ordinal < 4:
            assert replay.outcome == "replay_unavailable_retry_pending"
            assert replay.after_snapshot.lifecycle_state == "RECOVERY_PENDING"
        else:
            assert replay.outcome == "replay_unavailable_budget_permanent_block"
            assert replay.after_snapshot.lifecycle_state == "BLOCKED_WITNESS_LIVE"
            assert replay.after_snapshot.terminal_reason == (
                "recovery_epoch_budget_exhausted_after_unavailable"
            )
            assert replay.after_snapshot.replay_attempt_count == 4
            assert replay.issued_witness is not None
    terminal = _snapshot(coordinator)
    assert terminal.epoch_issue_count == terminal.replay_attempt_count == 4
    assert recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).outcome == (
        "blocked_terminal_noop"
    )
    for old in epochs[:-1]:
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, old)


def test_uprime_synthetic_recovery_coordinator_wrong_delta_replay_blocks(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("wrong_delta_confirmed", tmp_path, nonce="63" * 16)
    issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    blocked = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, issued.issued_epoch
    )
    assert blocked.outcome == "replay_wrong_delta_permanent_block"
    assert blocked.reason_codes == ("synthetic_wrong_delta_confirmed",)
    assert blocked.replay_observation == "confirmed_wrong_delta"
    assert blocked.after_snapshot.lifecycle_state == "BLOCKED_WITNESS_LIVE"
    assert blocked.after_snapshot.terminal_kind == "permanent_block"
    assert blocked.after_snapshot.terminal_reason == "synthetic_wrong_delta_confirmed"
    assert blocked.after_snapshot.witness_purpose == "record_permanent_block"
    assert blocked.issued_witness is not None


def test_uprime_synthetic_recovery_coordinator_release_consumes_ordinals_and_blocks_fourth(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="64" * 16)
    prior_epochs: list[recovery.SyntheticRecoveryEpochV10] = []
    for ordinal in range(1, 5):
        issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
        epoch = issued.issued_epoch
        prior_epochs.append(epoch)
        action = recovery.release_synthetic_recovery_epoch_v1_0(coordinator, epoch)
        assert action.operation == "release_epoch"
        assert action.epoch_ordinal == ordinal
        if ordinal < 4:
            assert action.outcome == "epoch_released_retry_pending"
            assert action.reason_codes == ("epoch_released_replay_cursor_unchanged",)
            assert action.after_snapshot.lifecycle_state == "RECOVERY_PENDING"
            assert action.after_snapshot.replay_attempt_count == 0
        else:
            assert action.outcome == "epoch_release_budget_permanent_block"
            assert action.after_snapshot.lifecycle_state == "BLOCKED_WITNESS_LIVE"
            assert action.after_snapshot.terminal_reason == (
                "recovery_epoch_budget_exhausted_after_release"
            )
            assert action.issued_witness is not None
    terminal_snapshot = _snapshot(coordinator)
    for stale in prior_epochs[:-1]:
        for operation in (
            recovery.release_synthetic_recovery_epoch_v1_0,
            recovery.abandon_synthetic_recovery_epoch_v1_0,
            recovery.replay_synthetic_recovery_epoch_v1_0,
        ):
            with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
                operation(coordinator, stale)
            assert _snapshot(coordinator) == terminal_snapshot
    for operation in (
        recovery.release_synthetic_recovery_epoch_v1_0,
        recovery.abandon_synthetic_recovery_epoch_v1_0,
    ):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            operation(coordinator, prior_epochs[-1])
        assert _snapshot(coordinator) == terminal_snapshot
    terminal_noop = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, prior_epochs[-1]
    )
    assert terminal_noop.outcome == "blocked_terminal_noop"
    assert terminal_noop.replay_observation == "terminal_noop"


def test_uprime_synthetic_recovery_coordinator_abandon_consumes_ordinals_and_blocks_fourth(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="65" * 16)
    for ordinal in range(1, 5):
        issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
        action = recovery.abandon_synthetic_recovery_epoch_v1_0(
            coordinator, issued.issued_epoch
        )
        assert action.operation == "abandon_epoch"
        assert action.epoch_ordinal == ordinal
        if ordinal < 4:
            assert action.outcome == "epoch_abandoned_retry_pending"
            assert action.reason_codes == (
                "epoch_abandoned_replay_cursor_unchanged",
            )
            assert action.after_snapshot.replay_attempt_count == 0
        else:
            assert action.outcome == "epoch_abandon_budget_permanent_block"
            assert action.after_snapshot.terminal_reason == (
                "recovery_epoch_budget_exhausted_after_abandon"
            )
            assert action.issued_witness is not None
    assert _snapshot(coordinator).epoch_issue_count == 4


def test_uprime_synthetic_recovery_coordinator_release_and_abandon_preserve_replay_cursor(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed", tmp_path, nonce="66" * 16
    )
    first = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, first.issued_epoch)
    assert _snapshot(coordinator).replay_attempt_count == 1
    second = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    release = recovery.release_synthetic_recovery_epoch_v1_0(
        coordinator, second.issued_epoch
    )
    assert release.after_snapshot.replay_attempt_count == 1
    third = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    abandon = recovery.abandon_synthetic_recovery_epoch_v1_0(
        coordinator, third.issued_epoch
    )
    assert abandon.after_snapshot.replay_attempt_count == 1
    fourth = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, fourth.issued_epoch
    )
    assert terminal.outcome == "replay_confirmed_recovered"
    assert terminal.after_snapshot.epoch_issue_count == 4
    assert terminal.after_snapshot.replay_attempt_count == 2


def test_uprime_synthetic_recovery_coordinator_acquire_noops_and_active_exclusion(
    tmp_path: Path,
) -> None:
    normal = _new("normal")
    open_action = recovery.acquire_synthetic_recovery_epoch_v1_0(normal)
    assert open_action.operation == "acquire_epoch"
    assert open_action.outcome == "no_marker_noop"
    assert open_action.reason_codes == ("marker_absent",)
    assert open_action.endpoint_state_changed is False
    assert open_action.issued_epoch is None
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="67" * 16)
    first = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    second = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    assert second.outcome == "recovery_active_excluded"
    assert second.reason_codes == ("active_epoch_exists",)
    assert second.issued_epoch is None
    assert second.after_snapshot.active_epoch_ordinal == first.epoch_ordinal


def test_uprime_synthetic_recovery_coordinator_epoch_exact_identity_and_cross_instance(
    tmp_path: Path,
) -> None:
    first_parent = tmp_path / "first"
    second_parent = tmp_path / "second"
    first_parent.mkdir()
    second_parent.mkdir()
    first, _ = _arm("ack_loss_confirmed", first_parent, nonce="68" * 16)
    second, _ = _arm("ack_loss_confirmed", second_parent, nonce="69" * 16)
    epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(first).issued_epoch
    foreign = recovery.acquire_synthetic_recovery_epoch_v1_0(second).issued_epoch
    for operation in (
        recovery.release_synthetic_recovery_epoch_v1_0,
        recovery.abandon_synthetic_recovery_epoch_v1_0,
        recovery.replay_synthetic_recovery_epoch_v1_0,
    ):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            operation(first, foreign)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(Exception):
            operation(epoch)
    assert epoch.epoch_ordinal == 1
    assert len(epoch.epoch_nonce_sha256) == len(epoch.epoch_sha256) == 64
    recovery.release_synthetic_recovery_epoch_v1_0(first, epoch)
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.replay_synthetic_recovery_epoch_v1_0(first, epoch)


def test_uprime_synthetic_recovery_coordinator_witness_validation_single_use_and_properties(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="70" * 16)
    epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).issued_epoch
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    witness = terminal.issued_witness
    assert isinstance(witness, recovery.SyntheticRecoveryWitnessV10)
    assert witness.purpose == "record_recovered_terminal"
    assert witness.terminal_sha256 == terminal.terminal_sha256
    assert len(witness.witness_nonce_sha256) == len(witness.witness_sha256) == 64
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(Exception):
            operation(witness)
    live = _snapshot(coordinator)
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.consume_synthetic_recovery_witness_v1_0(
            coordinator, witness, "record_permanent_block", witness.terminal_sha256
        )
    assert _snapshot(coordinator) == live
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.consume_synthetic_recovery_witness_v1_0(
            coordinator, witness, witness.purpose, "00" * 32
        )
    assert _snapshot(coordinator) == live
    consumed = recovery.consume_synthetic_recovery_witness_v1_0(
        coordinator, witness, witness.purpose, witness.terminal_sha256
    )
    assert consumed.operation == "consume_witness"
    assert consumed.outcome == "witness_consumed"
    assert consumed.after_snapshot.lifecycle_state == "RECOVERED_WITNESS_SPENT"
    assert consumed.after_snapshot.witness_status == "spent"
    again = recovery.consume_synthetic_recovery_witness_v1_0(
        coordinator, witness, witness.purpose, witness.terminal_sha256
    )
    assert again.outcome == "witness_already_spent_noop"
    assert again.endpoint_state_changed is False
    assert again.issued_witness is None


def test_uprime_synthetic_recovery_coordinator_block_witness_never_consumes_as_recovered(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("wrong_delta_confirmed", tmp_path, nonce="71" * 16)
    epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).issued_epoch
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    witness = terminal.issued_witness
    before = _snapshot(coordinator)
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.consume_synthetic_recovery_witness_v1_0(
            coordinator,
            witness,
            "record_recovered_terminal",
            witness.terminal_sha256,
        )
    assert _snapshot(coordinator) == before
    consumed = recovery.consume_synthetic_recovery_witness_v1_0(
        coordinator,
        witness,
        "record_permanent_block",
        witness.terminal_sha256,
    )
    assert consumed.after_snapshot.lifecycle_state == "BLOCKED_WITNESS_SPENT"
    _assert_lifecycle_shape(consumed.after_snapshot)
    _assert_no_authority(consumed)


def test_uprime_synthetic_recovery_coordinator_cross_instance_equal_hash_witness_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    nonce = "72" * 16
    result = publisher.stage_and_fake_publish_normal_v1_0(
        str(tmp_path), nonce, state, state.state_version_sha256, B
    )
    monkeypatch.setattr(
        recovery,
        "stage_and_fake_publish_normal_v1_0",
        lambda *args: result,
    )
    first = _new("ack_loss_confirmed")
    second = _new("ack_loss_confirmed")
    first_marker = _publish(first, tmp_path, nonce=nonce, state=state).marker
    second_marker = _publish(second, tmp_path, nonce=nonce, state=state).marker
    assert first_marker.marker_sha256 == second_marker.marker_sha256
    first_issue = recovery.acquire_synthetic_recovery_epoch_v1_0(first)
    second_issue = recovery.acquire_synthetic_recovery_epoch_v1_0(second)
    first_epoch = first_issue.issued_epoch
    second_epoch = second_issue.issued_epoch
    assert first_epoch.epoch_sha256 == second_epoch.epoch_sha256
    assert first_issue.action_sha256 == second_issue.action_sha256
    first_active = _snapshot(first)
    for operation in (
        recovery.release_synthetic_recovery_epoch_v1_0,
        recovery.abandon_synthetic_recovery_epoch_v1_0,
        recovery.replay_synthetic_recovery_epoch_v1_0,
    ):
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            operation(first, second_epoch)
        assert _snapshot(first) == first_active
    first_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(first, first_epoch)
    second_terminal = recovery.replay_synthetic_recovery_epoch_v1_0(second, second_epoch)
    first_witness = first_terminal.issued_witness
    second_witness = second_terminal.issued_witness
    assert first_witness.witness_sha256 == second_witness.witness_sha256
    assert first_terminal.action_sha256 == second_terminal.action_sha256
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.consume_synthetic_recovery_witness_v1_0(
            first,
            second_witness,
            second_witness.purpose,
            second_witness.terminal_sha256,
        )
    assert _snapshot(first).witness_status == "live"


class _SentinelBaseException(BaseException):
    pass


def test_uprime_synthetic_recovery_coordinator_pre_call_profile_error_restores_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def forbidden(*args: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("Phase-2b2d must not be reached")

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", forbidden)
    for alternate in (A, B):
        coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
            "wrong_delta_confirmed", alternate
        )
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            _publish(coordinator, tmp_path, proposal=B)
        assert called is False
        snapshot = _snapshot(coordinator)
        assert snapshot.lifecycle_state == "OPEN"
        assert snapshot.profile_status == "armed"


def test_uprime_synthetic_recovery_coordinator_changed_call_error_poison_and_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _new("normal")

    def boom(*args: object) -> object:
        raise ValueError("private detail")

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", boom)
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned changed publish failed without exact changed endpoint$",
    ) as caught:
        _publish(coordinator, tmp_path)
    assert caught.value.__cause__ is None
    snapshot = _snapshot(coordinator)
    assert snapshot.lifecycle_state == "POISONED_NO_MARKER"
    assert snapshot.profile_status == "spent_without_marker"
    assert snapshot.marker is None and snapshot.marker_count == 0
    acquire = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    assert acquire.outcome == "poisoned_no_marker_noop"


def test_uprime_synthetic_recovery_coordinator_changed_call_baseexception_poison_preserves_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _new("ack_loss_confirmed")
    sentinel = _SentinelBaseException("primary")

    def boom(*args: object) -> object:
        raise sentinel

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", boom)
    with pytest.raises(_SentinelBaseException) as caught:
        _publish(coordinator, tmp_path)
    assert caught.value is sentinel
    assert _snapshot(coordinator).lifecycle_state == "POISONED_NO_MARKER"


def test_uprime_synthetic_recovery_coordinator_post_exact_result_action_cut_poison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_action_type = recovery.SyntheticRecoveryActionV10
    coordinator = _new("normal")

    def cut(*args: object) -> object:
        raise ValueError("post-result cut")

    monkeypatch.setattr(recovery, "SyntheticRecoveryActionV10", cut)
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned publish endpoint failed after exact changed result$",
    ):
        _publish(coordinator, tmp_path, nonce="6f" * 16)
    snapshot = _snapshot(coordinator)
    assert snapshot.lifecycle_state == "POISONED_NO_MARKER"
    assert snapshot.marker is None

    sentinel = _SentinelBaseException("post-result-primary")

    def base_cut(*args: object) -> object:
        raise sentinel

    monkeypatch.setattr(recovery, "SyntheticRecoveryActionV10", base_cut)
    base_coordinator = _new("normal")
    with pytest.raises(_SentinelBaseException) as caught:
        _publish(base_coordinator, tmp_path, nonce="6e" * 16)
    assert caught.value is sentinel
    assert _snapshot(base_coordinator).lifecycle_state == "POISONED_NO_MARKER"

    exact_primary = recovery.SyntheticRecoveryCoordinatorV10Error(
        "exact post-result primary"
    )

    def exact_cut(*args: object) -> object:
        raise exact_primary

    monkeypatch.setattr(recovery, "SyntheticRecoveryActionV10", exact_cut)
    exact_coordinator = _new("normal")
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error) as caught:
        _publish(exact_coordinator, tmp_path, nonce="6d" * 16)
    assert caught.value is exact_primary
    assert _snapshot(exact_coordinator).lifecycle_state == "POISONED_NO_MARKER"

    monkeypatch.setattr(recovery, "SyntheticRecoveryActionV10", cut)
    state = _state()
    absent = _state(None)
    for index, (expected, proposal) in enumerate(
        ((absent.state_version_sha256, B), (state.state_version_sha256, A))
    ):
        no_stage = _new("ack_loss_confirmed")
        with pytest.raises(
            recovery.SyntheticRecoveryCoordinatorV10Error,
            match="^owned publish failed before changed call$",
        ):
            _publish(
                no_stage,
                tmp_path / f"no-stage-cut-{index}",
                nonce=f"{107 + index:02x}" * 16,
                state=state,
                expected=expected,
                proposal=proposal,
            )
        restored = _snapshot(no_stage)
        assert restored.lifecycle_state == "OPEN"
        assert restored.profile_status == "armed"

    monkeypatch.setattr(recovery, "SyntheticRecoveryActionV10", original_action_type)

    def marker_cut(*args: object) -> object:
        raise ValueError("post-result marker cut")

    monkeypatch.setattr(recovery, "_make_marker", marker_cut)
    nonnormal = _new("ack_loss_confirmed")
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned publish endpoint failed after exact changed result$",
    ):
        _publish(nonnormal, tmp_path, nonce="6c" * 16)
    poisoned = _snapshot(nonnormal)
    assert poisoned.lifecycle_state == "POISONED_NO_MARKER"
    assert poisoned.marker is None


def test_uprime_synthetic_recovery_coordinator_proven_no_stage_error_restores_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _new("ack_loss_confirmed")
    state = _state()
    absent = _state(None)

    def boom(*args: object) -> object:
        raise RuntimeError("no-stage seam failure")

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", boom)
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned publish failed before changed call$",
    ):
        _publish(
            coordinator,
            tmp_path / "missing",
            state=state,
            expected=absent.state_version_sha256,
        )
    snapshot = _snapshot(coordinator)
    assert snapshot.lifecycle_state == "OPEN"
    assert snapshot.profile_status == "armed"

    sentinel = _SentinelBaseException("no-stage-primary")

    def base_boom(*args: object) -> object:
        raise sentinel

    monkeypatch.setattr(
        recovery, "stage_and_fake_publish_normal_v1_0", base_boom
    )
    base_coordinator = _new("normal")
    with pytest.raises(_SentinelBaseException) as caught:
        _publish(
            base_coordinator,
            tmp_path / "still-missing",
            state=state,
            expected=absent.state_version_sha256,
        )
    assert caught.value is sentinel
    assert _snapshot(base_coordinator).lifecycle_state == "OPEN"


def test_uprime_synthetic_recovery_coordinator_public_input_failure_precedence(
    tmp_path: Path,
) -> None:
    for bad_state, bad_expected, bad_proposal in (
        ("bad", "00" * 32, B),
        (_state(), "bad", B),
        (_state(), _state().state_version_sha256, bytearray(B)),
    ):
        coordinator = _new("normal")
        with pytest.raises(
            recovery.SyntheticRecoveryCoordinatorV10Error,
            match="^owned publish failed before changed call$",
        ):
            recovery.publish_with_synthetic_recovery_coordinator_v1_0(
                coordinator,
                str(tmp_path),
                "79" * 16,
                bad_state,  # type: ignore[arg-type]
                bad_expected,
                bad_proposal,  # type: ignore[arg-type]
            )
        assert _snapshot(coordinator).lifecycle_state == "OPEN"

    # Invalid path/nonce is inside an already classified changed call and poisons.
    changed = _new("normal")
    state = _state()
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned changed publish failed without exact changed endpoint$",
    ):
        recovery.publish_with_synthetic_recovery_coordinator_v1_0(
            changed, "relative", "bad", state, state.state_version_sha256, B
        )
    assert _snapshot(changed).lifecycle_state == "POISONED_NO_MARKER"

    # The same invalid lexical inputs on a preclassified conflict are proven no-stage.
    conflict = _new("normal")
    absent = _state(None)
    with pytest.raises(
        recovery.SyntheticRecoveryCoordinatorV10Error,
        match="^owned publish failed before changed call$",
    ):
        recovery.publish_with_synthetic_recovery_coordinator_v1_0(
            conflict, "relative", "bad", state, absent.state_version_sha256, B
        )
    assert _snapshot(conflict).lifecycle_state == "OPEN"


def test_uprime_synthetic_recovery_coordinator_max_generation_precedence(
    tmp_path: Path,
) -> None:
    maximum = cas._make_state(9_223_372_036_854_775_807, A)
    absent = _state(None)
    missing = tmp_path / "missing-max"
    conflict_coordinator = _new("normal")
    conflict = _publish(
        conflict_coordinator,
        missing,
        state=maximum,
        expected=absent.state_version_sha256,
        proposal=B,
    )
    assert conflict.outcome == "cas_conflict_no_marker"
    identical_coordinator = _new("normal")
    identical = _publish(
        identical_coordinator, missing, state=maximum, proposal=A, nonce="7a" * 16
    )
    assert identical.outcome == "cas_existing_identical_no_marker"
    changed_coordinator = _new("normal")
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        _publish(
            changed_coordinator,
            tmp_path,
            state=maximum,
            proposal=B,
            nonce="7b" * 16,
        )
    assert _snapshot(changed_coordinator).lifecycle_state == "OPEN"


def test_uprime_synthetic_recovery_coordinator_preclassification_result_mismatch_poison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    absent = _state(None)
    changed_result = publisher.stage_and_fake_publish_normal_v1_0(
        str(tmp_path), "73" * 16, state, state.state_version_sha256, B
    )
    conflict_result = publisher.stage_and_fake_publish_normal_v1_0(
        str(tmp_path / "does-not-exist"),
        "74" * 16,
        state,
        absent.state_version_sha256,
        B,
    )
    identical_result = publisher.stage_and_fake_publish_normal_v1_0(
        str(tmp_path / "also-does-not-exist"),
        "7f" * 16,
        state,
        state.state_version_sha256,
        A,
    )
    for index, (result, expected, proposal) in enumerate(
        (
            (changed_result, absent.state_version_sha256, B),
            (conflict_result, state.state_version_sha256, B),
            (identical_result, absent.state_version_sha256, B),
            (conflict_result, state.state_version_sha256, A),
        )
    ):
        coordinator = _new("normal")
        monkeypatch.setattr(
            recovery,
            "stage_and_fake_publish_normal_v1_0",
            lambda *args, result=result: result,
        )
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            _publish(
                coordinator,
                tmp_path,
                nonce=f"{75 + index:02x}" * 16,
                state=state,
                expected=expected,
                proposal=proposal,
            )
        assert _snapshot(coordinator).lifecycle_state == "POISONED_NO_MARKER"


def test_uprime_synthetic_recovery_coordinator_bypass_mutated_result_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state()
    result = publisher.stage_and_fake_publish_normal_v1_0(
        str(tmp_path), "77" * 16, state, state.state_version_sha256, B
    )
    object.__setattr__(result, "outcome", "cas_conflict_no_stage")
    monkeypatch.setattr(
        recovery, "stage_and_fake_publish_normal_v1_0", lambda *args: result
    )
    coordinator = _new("normal")
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        _publish(coordinator, tmp_path, nonce="77" * 16, state=state)
    assert _snapshot(coordinator).lifecycle_state == "POISONED_NO_MARKER"


def test_uprime_synthetic_recovery_coordinator_private_state_snapshot_shared_by_classification_and_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller_state = _state()
    expected = caller_state.state_version_sha256
    original_step = recovery.step_in_memory_fake_cas_v1_0
    original_publish = recovery.stage_and_fake_publish_normal_v1_0
    original_getattribute = cas.InMemoryFakeCasStateV10.__getattribute__
    seen: list[cas.InMemoryFakeCasStateV10] = []
    caller_reads: list[str] = []

    def tracked_getattribute(self: object, name: str) -> object:
        if self is caller_state and name in cas.InMemoryFakeCasStateV10.__slots__:
            caller_reads.append(name)
        return original_getattribute(self, name)

    def step_wrapper(state: cas.InMemoryFakeCasStateV10, *args: object) -> object:
        if not seen:
            assert state is not caller_state
            seen.append(state)
            object.__setattr__(caller_state, "generation", 999)
        else:
            assert state is seen[0]
        return original_step(state, *args)

    def publish_wrapper(
        parent: str,
        nonce: str,
        state: cas.InMemoryFakeCasStateV10,
        expected: str,
        proposal: bytes,
    ) -> object:
        assert state is seen[0]
        return original_publish(parent, nonce, state, expected, proposal)

    monkeypatch.setattr(
        cas.InMemoryFakeCasStateV10,
        "__getattribute__",
        tracked_getattribute,
    )
    monkeypatch.setattr(recovery, "step_in_memory_fake_cas_v1_0", step_wrapper)
    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", publish_wrapper)
    coordinator = _new("normal")
    action = _publish(
        coordinator,
        tmp_path,
        nonce="78" * 16,
        state=caller_state,
        expected=expected,
    )
    assert action.outcome == "normal_staged_result_exposed_no_marker"
    assert action.publish_result.cas_transition.before_state is not caller_state
    assert action.publish_result.cas_transition.before_state == seen[0]
    assert caller_reads == list(cas.InMemoryFakeCasStateV10.__slots__)


def test_uprime_synthetic_recovery_coordinator_publishing_lock_oracle_and_exclusions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle_parent = tmp_path / "foreign-handles"
    handle_parent.mkdir()
    handle_coordinator, _ = _arm(
        "ack_loss_confirmed", handle_parent, nonce="79" * 16
    )
    foreign_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(
        handle_coordinator
    ).issued_epoch
    foreign_witness = recovery.replay_synthetic_recovery_epoch_v1_0(
        handle_coordinator, foreign_epoch
    ).issued_witness
    coordinator = _new("ack_loss_confirmed")
    original = recovery.stage_and_fake_publish_normal_v1_0
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    results: list[object] = []
    failures: list[BaseException] = []

    def blocked(*args: object) -> object:
        assert coordinator._lock.locked() is False
        entered.set()
        if not release.wait(5):
            raise AssertionError("deadlock guard expired")
        return original(*args)

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", blocked)

    def worker() -> None:
        try:
            results.append(_publish(coordinator, tmp_path, nonce="80" * 16))
        except BaseException as exc:  # pragma: no cover - assertion reports it
            failures.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        assert entered.wait(5)
        publishing = _snapshot(coordinator)
        assert publishing.lifecycle_state == "PUBLISHING"
        second = recovery.publish_with_synthetic_recovery_coordinator_v1_0(
            coordinator,
            "not-even-a-path",
            "bad",
            "bad",  # type: ignore[arg-type]
            "bad",
            b"",
        )
        assert second.outcome == "publisher_excluded_non_open"
        assert second.after_snapshot == publishing
        acquire = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
        assert acquire.outcome == "publisher_active_excluded"
        assert acquire.issued_epoch is None
        for operation in (
            recovery.release_synthetic_recovery_epoch_v1_0,
            recovery.abandon_synthetic_recovery_epoch_v1_0,
            recovery.replay_synthetic_recovery_epoch_v1_0,
        ):
            excluded = operation(coordinator, foreign_epoch)
            assert excluded.outcome == "publisher_active_excluded"
            assert excluded.reason_codes == ("owned_publisher_active",)
            assert excluded.endpoint_state_changed is False
            assert excluded.after_snapshot == publishing
        consume = recovery.consume_synthetic_recovery_witness_v1_0(
            coordinator,
            foreign_witness,
            foreign_witness.purpose,
            foreign_witness.terminal_sha256,
        )
        assert consume.outcome == "publisher_active_excluded"
        assert consume.reason_codes == ("owned_publisher_active",)
        assert consume.endpoint_state_changed is False
        assert consume.after_snapshot == publishing
        release.set()
        assert finished.wait(5)
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert failures == []
    assert len(results) == 1
    assert results[0].outcome == "synthetic_marker_committed_result_withheld"


def test_uprime_synthetic_recovery_coordinator_cross_instance_has_no_global_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_parent = tmp_path / "first"
    second_parent = tmp_path / "second"
    first_parent.mkdir()
    second_parent.mkdir()
    first = _new("normal")
    second = _new("normal")
    original = recovery.stage_and_fake_publish_normal_v1_0
    entered = threading.Event()
    release = threading.Event()
    done = threading.Event()
    result: list[object] = []

    def selective(parent: str, nonce: str, *args: object) -> object:
        if nonce == "81" * 16:
            entered.set()
            if not release.wait(5):
                raise AssertionError("deadlock guard expired")
        return original(parent, nonce, *args)

    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", selective)
    first_thread = threading.Thread(
        target=lambda: (_publish(first, first_parent, nonce="81" * 16), done.set())
    )
    first_thread.start()
    try:
        assert entered.wait(5)
        second_action = _publish(second, second_parent, nonce="82" * 16)
        result.append(second_action)
        assert second_action.outcome == "normal_staged_result_exposed_no_marker"
    finally:
        release.set()
        first_thread.join(5)
    assert not first_thread.is_alive()
    assert done.is_set()
    assert result


def test_uprime_synthetic_recovery_coordinator_simultaneous_acquire_exactly_one_epoch(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="83" * 16)
    barrier = threading.Barrier(3)
    actions: list[recovery.SyntheticRecoveryActionV10] = []
    failures: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait()
            actions.append(recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator))
        except BaseException as exc:  # pragma: no cover
            failures.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(5)
    assert all(not thread.is_alive() for thread in threads)
    assert failures == []
    assert sorted(action.outcome for action in actions) == [
        "epoch_issued",
        "recovery_active_excluded",
    ]
    assert sum(action.issued_epoch is not None for action in actions) == 1
    assert _snapshot(coordinator).epoch_issue_count == 1


def test_uprime_synthetic_recovery_coordinator_simultaneous_witness_consume_once(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="84" * 16)
    epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).issued_epoch
    witness = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, epoch
    ).issued_witness
    barrier = threading.Barrier(3)
    actions: list[recovery.SyntheticRecoveryActionV10] = []

    def worker() -> None:
        barrier.wait()
        actions.append(
            recovery.consume_synthetic_recovery_witness_v1_0(
                coordinator, witness, witness.purpose, witness.terminal_sha256
            )
        )

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(5)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(action.outcome for action in actions) == [
        "witness_already_spent_noop",
        "witness_consumed",
    ]
    assert _snapshot(coordinator).lifecycle_state == "RECOVERED_WITNESS_SPENT"


def test_uprime_synthetic_recovery_coordinator_recovery_never_reenters_cas_or_publisher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed", tmp_path, nonce="85" * 16
    )

    def forbidden(*args: object) -> object:
        raise AssertionError("recovery re-entered an owned publishing dependency")

    monkeypatch.setattr(recovery, "step_in_memory_fake_cas_v1_0", forbidden)
    monkeypatch.setattr(recovery, "stage_and_fake_publish_normal_v1_0", forbidden)
    first = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, first.issued_epoch)
    second = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(
        coordinator, second.issued_epoch
    )
    assert terminal.outcome == "replay_confirmed_recovered"


def test_uprime_synthetic_recovery_coordinator_direct_step_call_bounds_and_lock_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _new("ack_loss_unavailable_then_confirmed")
    caller_state = _state()
    original = recovery.step_in_memory_fake_cas_v1_0
    original_publish = recovery.stage_and_fake_publish_normal_v1_0
    original_nested = publisher.step_in_memory_fake_cas_v1_0
    original_payload_hash = cas._raw_payload_sha256
    calls: list[str] = []
    nested_phases: list[str] = []
    payload_hash_calls: list[int] = []
    inside_owned_publish = False

    def wrapped(
        state: cas.InMemoryFakeCasStateV10,
        expected: str,
        proposal: bytes,
        directive: str,
        alternate: bytes | None,
    ) -> object:
        assert coordinator._lock.locked() is False
        calls.append(directive)
        return original(state, expected, proposal, directive, alternate)

    def publish_wrapped(*args: object) -> object:
        nonlocal inside_owned_publish
        assert coordinator._lock.locked() is False
        inside_owned_publish = True
        try:
            return original_publish(*args)
        finally:
            inside_owned_publish = False

    def nested_wrapped(*args: object) -> object:
        assert coordinator._lock.locked() is False
        nested_phases.append(
            "inside_owned_phase2b2d"
            if inside_owned_publish
            else "result_reconstruction"
        )
        return original_nested(*args)

    def payload_hash_wrapped(payload: bytes, /) -> str:
        assert coordinator._lock.locked() is False
        payload_hash_calls.append(len(payload))
        return original_payload_hash(payload)

    monkeypatch.setattr(recovery, "step_in_memory_fake_cas_v1_0", wrapped)
    monkeypatch.setattr(
        recovery, "stage_and_fake_publish_normal_v1_0", publish_wrapped
    )
    monkeypatch.setattr(publisher, "step_in_memory_fake_cas_v1_0", nested_wrapped)
    monkeypatch.setattr(cas, "_raw_payload_sha256", payload_hash_wrapped)
    action = _publish(
        coordinator,
        tmp_path,
        nonce="86" * 16,
        state=caller_state,
    )
    assert action.outcome == "synthetic_marker_committed_result_withheld"
    assert calls == [
        "apply_intended_acknowledge",
        "apply_intended_lose_ack_confirmation_unavailable",
        "apply_intended_lose_ack_then_confirm",
    ]
    assert nested_phases.count("result_reconstruction") == 1
    assert nested_phases[-1] == "result_reconstruction"
    assert set(nested_phases[:-1]) == {"inside_owned_phase2b2d"}
    assert payload_hash_calls


def test_uprime_synthetic_recovery_coordinator_normal_residue_is_per_call_not_lifetime(
    tmp_path: Path,
) -> None:
    coordinator = _new("normal")
    paths: list[Path] = []
    for index in range(3):
        action = _publish(coordinator, tmp_path, nonce=f"{90 + index:02x}" * 16)
        paths.append(Path(action.publish_result.stage_path))
    assert len(set(paths)) == 3
    assert all(path.read_bytes() == B for path in paths)
    assert _snapshot(coordinator).lifecycle_state == "OPEN"


def test_uprime_synthetic_recovery_coordinator_dynamic_transcripts_recompute(
    tmp_path: Path,
) -> None:
    coordinator, marker_action = _arm(
        "wrong_delta_confirmed", tmp_path, nonce="93" * 16
    )
    marker = marker_action.marker
    assert marker.marker_sha256 == _marker_digest(marker)
    assert marker_action.action_sha256 == _action_digest(marker_action)
    assert marker_action.after_snapshot.snapshot_sha256 == _snapshot_digest(
        marker_action.after_snapshot
    )
    issued = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator)
    epoch = issued.issued_epoch
    expected_nonce = _epoch_nonce(
        issued.after_snapshot.coordinator_config_sha256,
        marker.marker_sha256,
        1,
    )
    assert epoch.epoch_nonce_sha256 == expected_nonce
    assert epoch.epoch_sha256 == _epoch_digest(
        issued.after_snapshot.coordinator_config_sha256,
        marker.marker_sha256,
        1,
        expected_nonce,
    )
    assert issued.after_snapshot.snapshot_sha256 == _snapshot_digest(issued.after_snapshot)
    assert issued.action_sha256 == _action_digest(issued)
    terminal = recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    snapshot = terminal.after_snapshot
    assert snapshot.terminal_sha256 == _terminal_digest(snapshot)
    witness = terminal.issued_witness
    expected_witness_nonce = _witness_nonce(
        snapshot.coordinator_config_sha256,
        snapshot.terminal_sha256,
        snapshot.witness_purpose,
    )
    assert witness.witness_nonce_sha256 == expected_witness_nonce
    assert witness.witness_sha256 == _witness_digest(
        snapshot.coordinator_config_sha256,
        snapshot.terminal_sha256,
        snapshot.witness_purpose,
        expected_witness_nonce,
    )
    assert snapshot.snapshot_sha256 == _snapshot_digest(snapshot)
    assert terminal.action_sha256 == _action_digest(terminal)


def test_uprime_synthetic_recovery_coordinator_all_preregistered_numeric_goldens() -> None:
    config = _config("wrong_delta_confirmed", b"C")
    plan = _plan(
        "wrong_delta_confirmed", (("confirmed_wrong_delta", "CC" * 32),)
    )
    fixture = SimpleNamespace(
        coordinator_config_sha256=config,
        marker_ordinal=1,
        marker_kind="synthetic_wrong_delta_confirmed",
        phase2b1_failure_codes=("OTHER_HARNESS_ERROR",),
        publisher_outcome="staged_intended_fake_publish_acknowledged",
        publisher_operation_sha256="AA" * 32,
        publisher_transition_sha256="BB" * 32,
        synthetic_fault_outcome="wrong_delta_confirmed",
        synthetic_fault_transition_sha256="CC" * 32,
        replay_plan_sha256=plan,
        replay_plan_row_count=1,
        before_state_version_sha256="01" * 32,
        intended_after_state_version_sha256="02" * 32,
        actual_after_state_version_sha256="03" * 32,
        intended_delta_sha256="04" * 32,
        actual_delta_sha256="05" * 32,
        stage_payload_bytes=1,
        stage_payload_sha256=_h(b"B"),
    )
    marker = _marker_digest(fixture)
    assert marker == "541246B7A32A2FE90823D3A1E64EDE4AB4FA28A627B2CB7C989E7A8D669D8D12"
    epoch_nonce = _epoch_nonce(config, marker, 1)
    assert epoch_nonce == "8A930B2031BC188FBD8AC99FF60BF5AE30DD0EDC8969035D3B2BF8C133B2402C"
    assert _epoch_digest(config, marker, 1, epoch_nonce) == (
        "AF2990CD863064FAC8EF53ED47B0107DCEF499ADF99E1B7B551E3DE24B341C4A"
    )
    terminal = _h(
        D_TERMINAL
        + _rh(config)
        + _rh(marker)
        + _k("permanent_block")
        + _k("synthetic_wrong_delta_confirmed")
        + _u64(1)
        + _rh(epoch_nonce)
        + _u64(1)
        + _u64(1)
    )
    assert terminal == "2F8EB9FFC70DBF4D4DDE9E6F04843DDAE6A7390F5EB846B89FD30F44CF5BFA00"
    witness_nonce = _witness_nonce(config, terminal, "record_permanent_block")
    assert witness_nonce == "8101AE2086953536B63F0BEA184C90811DA249C7671BF0668812A4C8C3D0D73C"
    assert _witness_digest(
        config, terminal, "record_permanent_block", witness_nonce
    ) == "2A66126FB24A405129734382D1BA40D0B71DAF5D85236AF6E0738D3853022C55"
    normal = SimpleNamespace(
        constructor_profile="normal",
        profile_status="normal_no_fault_profile",
        alternate_payload_bytes=None,
        alternate_payload_sha256=None,
        coordinator_config_sha256=_config("normal", None),
        lifecycle_state="OPEN",
        marker=None,
        marker_count=0,
        epoch_issue_count=0,
        replay_attempt_count=0,
        active_epoch_ordinal=None,
        active_epoch_nonce_sha256=None,
        terminal_epoch_ordinal=None,
        terminal_epoch_nonce_sha256=None,
        witness_status="none",
        witness_purpose=None,
        witness_nonce_sha256=None,
        terminal_kind=None,
        terminal_reason=None,
        terminal_sha256=None,
    )
    assert _snapshot_digest(normal) == (
        "FA9664700ABA3A3EDCDDE86F680C0F7F11F3766F10D3442DD4B98A3573B702B1"
    )


def test_uprime_synthetic_recovery_coordinator_exact_negative_labels_and_false_authority(
    tmp_path: Path,
) -> None:
    coordinator, marker_action = _arm(
        "wrong_delta_confirmed", tmp_path, nonce="94" * 16
    )
    marker = marker_action.marker
    assert marker.caller_profile_scope == (
        "caller_selected_constructor_profile_not_observed_cause"
    )
    assert marker.cause_scope == (
        "same_kernel_synthetic_scenario_not_environmental_causality"
    )
    assert marker.journal_scope == "single_slot_in_memory_marker_not_durable_journal"
    assert marker.stage_binding_scope == (
        "publisher_operation_hash_only_no_current_stage_reobservation"
    )
    assert marker.failure_code_scope == (
        "internal_fixed_mapping_not_caller_supplied_cause_evidence"
    )
    assert marker.marker_provenance == (
        "internally_derived_after_owned_exact_changed_result"
    )
    for value in (marker, marker_action, marker_action.after_snapshot):
        _assert_no_authority(value)
    for name, expected in NEGATIVE_SNAPSHOT_FIELDS.items():
        assert getattr(marker_action.after_snapshot, name) == expected
    assert marker_action.exclusion_scope == (
        "coordinator_methods_only_no_global_or_cross_process_lock"
    )
    assert marker_action.action_record_scope == (
        "lock_linearization_value_not_return_time_history_or_attestation"
    )
    assert marker_action.opaque_handle_scope == (
        "exact_same_instance_object_reference_is_only_live_authority"
    )
    assert marker_action.hash_authority_scope == (
        "deterministic_digest_not_identity_freshness_or_capability"
    )
    assert marker_action.remote_reobservation_scope == "not_performed"


def test_uprime_synthetic_recovery_coordinator_detectable_private_tampering_fails_closed(
    tmp_path: Path,
) -> None:
    coordinator = _new("normal")
    object.__setattr__(coordinator, "_state", object())
    with pytest.raises(Exception):
        _snapshot(coordinator)
    coordinator = _new("normal")
    object.__setattr__(coordinator, "_issuer", object())
    with pytest.raises(Exception):
        _snapshot(coordinator)
    coordinator = _new("normal")
    object.__setattr__(coordinator, "_config_sha256", "00" * 32)
    with pytest.raises(Exception):
        _snapshot(coordinator)

    coordinator = recovery.new_synthetic_recovery_coordinator_v1_0(
        "wrong_delta_confirmed", C
    )
    state = coordinator._state
    altered = list(state)
    altered[recovery._S_ALTERNATE_BYTES] = 0
    altered[recovery._S_ALTERNATE_SHA] = "00" * 32
    object.__setattr__(coordinator, "_state", tuple(altered))
    with pytest.raises(Exception):
        _snapshot(coordinator)

    repeat_parent = tmp_path / "replay-repeat-tamper"
    repeat_parent.mkdir()
    coordinator, _ = _arm(
        "ack_loss_unavailable_until_budget_block",
        repeat_parent,
        nonce="9a" * 16,
    )
    state = coordinator._state
    rows = state[recovery._S_REPLAY_ROWS]
    assert len(rows) == 4 and len({id(row[1]) for row in rows}) == 1
    distinct_clones = tuple(
        (
            observation,
            cas.InMemoryFakeCasTransitionV10(*_values(transition)),
        )
        for observation, transition in rows
    )
    assert len({id(row[1]) for row in distinct_clones}) == 4
    altered = list(state)
    altered[recovery._S_REPLAY_ROWS] = distinct_clones
    object.__setattr__(coordinator, "_state", tuple(altered))
    with pytest.raises(Exception):
        _snapshot(coordinator)

    parent = tmp_path / "replay-plan-tamper"
    parent.mkdir()
    coordinator, _ = _arm(
        "ack_loss_unavailable_then_confirmed", parent, nonce="94" * 16
    )
    state = coordinator._state
    rows = state[recovery._S_REPLAY_ROWS]
    assert len(rows) == 2
    altered = list(state)
    altered[recovery._S_REPLAY_ROWS] = (
        (rows[0][0], rows[1][1]),
        rows[1],
    )
    object.__setattr__(coordinator, "_state", tuple(altered))
    with pytest.raises(Exception):
        _snapshot(coordinator)


def test_uprime_synthetic_recovery_coordinator_handle_issuer_tamper_rejects(
    tmp_path: Path,
) -> None:
    coordinator, _ = _arm("ack_loss_confirmed", tmp_path, nonce="95" * 16)
    epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).issued_epoch
    _snapshot(coordinator)
    private_before = coordinator._state
    object.__setattr__(epoch, "_issuer", object())
    with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
        recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    assert coordinator._state is private_before

    for index, slot in enumerate(("_issuer", "_witness_sha256")):
        parent = tmp_path / f"witness-{index}"
        parent.mkdir()
        witness_coordinator, _ = _arm(
            "ack_loss_confirmed", parent, nonce=f"{97 + index:02x}" * 16
        )
        witness_epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(
            witness_coordinator
        ).issued_epoch
        witness = recovery.replay_synthetic_recovery_epoch_v1_0(
            witness_coordinator, witness_epoch
        ).issued_witness
        _snapshot(witness_coordinator)
        private_before = witness_coordinator._state
        object.__setattr__(
            witness,
            slot,
            object() if slot == "_issuer" else "00" * 32,
        )
        with pytest.raises(recovery.SyntheticRecoveryCoordinatorV10Error):
            recovery.consume_synthetic_recovery_witness_v1_0(
                witness_coordinator,
                witness,
                witness.purpose,
                witness.terminal_sha256,
            )
        assert witness_coordinator._state is private_before


def test_uprime_synthetic_recovery_coordinator_resource_slots_are_bounded(
    tmp_path: Path,
) -> None:
    first = _new("normal")
    second = _new("normal")
    assert first._lock is not second._lock
    coordinator, _ = _arm(
        "ack_loss_unavailable_until_budget_block", tmp_path, nonce="96" * 16
    )
    for _ in range(3):
        epoch = recovery.acquire_synthetic_recovery_epoch_v1_0(coordinator).issued_epoch
        recovery.replay_synthetic_recovery_epoch_v1_0(coordinator, epoch)
    state = coordinator._state
    rows = state[recovery._S_REPLAY_ROWS]
    assert len(rows) == 4
    assert len({id(row[1]) for row in rows}) == 1
    assert all(row[1].proposed_payload is B for row in rows)
    assert all(row[1].before_state.cell_payload is A for row in rows)
    assert type(state) is tuple and len(state) == recovery._STATE_LENGTH
    assert not any(isinstance(value, (dict, list, set)) for value in state)
    assert all(
        not isinstance(value, (dict, list, set))
        for row in rows
        for value in row
    )
    snapshot = _snapshot(coordinator)
    assert snapshot.marker_count <= snapshot.marker_count_upper_bound == 1
    assert snapshot.epoch_issue_count <= snapshot.recovery_epoch_upper_bound == 4
    assert snapshot.retained_payload_reference_upper_bound_bytes == 3 * MAX_PAYLOAD_BYTES
    assert snapshot.retained_payload_copy_upper_bound_bytes == 0

    wrong_parent = tmp_path / "wrong-payload-references"
    wrong_parent.mkdir()
    wrong, _ = _arm("wrong_delta_confirmed", wrong_parent, nonce="99" * 16)
    wrong_transition = wrong._state[recovery._S_REPLAY_ROWS][0][1]
    assert wrong_transition.before_state.cell_payload is A
    assert wrong_transition.proposed_payload is B
    assert wrong_transition.alternate_payload is C


def test_uprime_synthetic_recovery_coordinator_ast_forbids_expanded_capabilities() -> None:
    tree = _tree()
    forbidden_import_roots = {
        "os",
        "pathlib",
        "secrets",
        "random",
        "time",
        "uuid",
        "subprocess",
        "socket",
        "requests",
        "pickle",
        "git",
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "threading"
        ):
            assert node.attr == "Lock"
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in forbidden_import_roots for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.Call):
            target = node.func
            name = target.attr if isinstance(target, ast.Attribute) else (
                target.id if isinstance(target, ast.Name) else ""
            )
            assert name not in {
                "open",
                "__import__",
                "eval",
                "exec",
                "compile",
                "hash",
                "id",
                "unlink",
                "remove",
                "rename",
                "replace",
                "link",
                "fsync",
                "mkdir",
                "makedirs",
                "rmdir",
                "stat",
                "lstat",
                "scandir",
                "listdir",
                "read_text",
                "write_text",
                "read_bytes",
                "write_bytes",
                "system",
                "Popen",
                "run",
                "Thread",
                "Timer",
                "Event",
                "Barrier",
                "sleep",
                "monotonic",
                "perf_counter",
                "get_ident",
                "get_native_id",
                "current_thread",
            }
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "POWER_LOSS" not in source
    assert "CLAIM_STARTED_MANIFEST_ERROR" not in source
    assert "FINAL_MANIFEST_ERROR" not in source
    assert "OTHER_ATTEMPT_ERROR" not in source
    assert "stage_and_fake_publish_normal_v1_0" in source
    assert ".unlink(" not in source and "os." not in source


def test_uprime_synthetic_recovery_coordinator_anchors_registry_and_collection() -> None:
    required = {
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2E_AMENDMENT_PATH,
        litmus.SYNTHETIC_RECOVERY_COORDINATOR_SOURCE_PATH,
        litmus.SYNTHETIC_RECOVERY_COORDINATOR_TEST_SUPPORT_PATH,
    }
    assert required <= set(litmus.ANCHOR_PATHS)
    assert litmus.SYNTHETIC_RECOVERY_COORDINATOR_SOURCE_PATH == SOURCE_PATH.relative_to(ROOT)
    assert litmus.SYNTHETIC_RECOVERY_COORDINATOR_TEST_SUPPORT_PATH == SUPPORT_PATH.relative_to(ROOT)
    collector = COLLECTOR_PATH.read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_synthetic_recovery_coordinator_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_synthetic_recovery_coordinator_cases") == 1
    raw = REGISTRY_PATH.read_bytes()
    assert raw == (
        b'{"default_allow":false,"licenses":{},"schema_version":'
        b'"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n'
    )
    assert _h(raw) == "ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B"
    assert "runs/" not in SOURCE_PATH.read_text(encoding="utf-8")


def test_uprime_synthetic_recovery_coordinator_support_exports_exact_ordered_tests_only() -> None:
    assert __all__ == EXPECTED_TEST_EXPORTS
    assert len(__all__) == len(set(__all__))
    actual = [
        name
        for name, value in globals().items()
        if name.startswith("test_uprime_synthetic_recovery_coordinator_")
        and inspect.isfunction(value)
        and value.__module__ == __name__
    ]
    assert actual == EXPECTED_TEST_EXPORTS
    assert all(
        inspect.isfunction(globals()[name]) and globals()[name].__module__ == __name__
        for name in __all__
    )


EXPECTED_TEST_EXPORTS = [
    "test_uprime_synthetic_recovery_coordinator_exact_surface_fields_and_signatures",
    "test_uprime_synthetic_recovery_coordinator_exact_import_ast_and_public_count",
    "test_uprime_synthetic_recovery_coordinator_records_are_frozen_slotted",
    "test_uprime_synthetic_recovery_coordinator_live_classes_slots_and_factory_only",
    "test_uprime_synthetic_recovery_coordinator_profile_and_alternate_boundaries",
    "test_uprime_synthetic_recovery_coordinator_initial_snapshots_and_negative_labels",
    "test_uprime_synthetic_recovery_coordinator_config_goldens_and_maximum",
    "test_uprime_synthetic_recovery_coordinator_publish_conflict_and_identical_no_stage",
    "test_uprime_synthetic_recovery_coordinator_normal_changed_result_and_reuse",
    "test_uprime_synthetic_recovery_coordinator_nonnormal_marker_rows_and_codes",
    "test_uprime_synthetic_recovery_coordinator_wrong_delta_relational_precedence",
    "test_uprime_synthetic_recovery_coordinator_publish_excluded_in_every_nonopen_state",
    "test_uprime_synthetic_recovery_coordinator_marker_constructor_revalidates_every_field",
    "test_uprime_synthetic_recovery_coordinator_marker_rejects_coherently_rehashed_row_mutants",
    "test_uprime_synthetic_recovery_coordinator_snapshot_constructor_revalidates_every_field",
    "test_uprime_synthetic_recovery_coordinator_snapshot_rejects_rehashed_unreachable_terminal_rows",
    "test_uprime_synthetic_recovery_coordinator_action_constructor_and_nullability",
    "test_uprime_synthetic_recovery_coordinator_action_rejects_rehashed_row_and_ordinal_mismatch",
    "test_uprime_synthetic_recovery_coordinator_ack_confirmed_recovery_and_terminal_noops",
    "test_uprime_synthetic_recovery_coordinator_unavailable_then_confirmed_schedule",
    "test_uprime_synthetic_recovery_coordinator_unavailable_fourth_replay_blocks",
    "test_uprime_synthetic_recovery_coordinator_wrong_delta_replay_blocks",
    "test_uprime_synthetic_recovery_coordinator_release_consumes_ordinals_and_blocks_fourth",
    "test_uprime_synthetic_recovery_coordinator_abandon_consumes_ordinals_and_blocks_fourth",
    "test_uprime_synthetic_recovery_coordinator_release_and_abandon_preserve_replay_cursor",
    "test_uprime_synthetic_recovery_coordinator_acquire_noops_and_active_exclusion",
    "test_uprime_synthetic_recovery_coordinator_epoch_exact_identity_and_cross_instance",
    "test_uprime_synthetic_recovery_coordinator_witness_validation_single_use_and_properties",
    "test_uprime_synthetic_recovery_coordinator_block_witness_never_consumes_as_recovered",
    "test_uprime_synthetic_recovery_coordinator_cross_instance_equal_hash_witness_rejects",
    "test_uprime_synthetic_recovery_coordinator_pre_call_profile_error_restores_open",
    "test_uprime_synthetic_recovery_coordinator_changed_call_error_poison_and_mapping",
    "test_uprime_synthetic_recovery_coordinator_changed_call_baseexception_poison_preserves_identity",
    "test_uprime_synthetic_recovery_coordinator_post_exact_result_action_cut_poison",
    "test_uprime_synthetic_recovery_coordinator_proven_no_stage_error_restores_open",
    "test_uprime_synthetic_recovery_coordinator_public_input_failure_precedence",
    "test_uprime_synthetic_recovery_coordinator_max_generation_precedence",
    "test_uprime_synthetic_recovery_coordinator_preclassification_result_mismatch_poison",
    "test_uprime_synthetic_recovery_coordinator_bypass_mutated_result_fails_closed",
    "test_uprime_synthetic_recovery_coordinator_private_state_snapshot_shared_by_classification_and_publish",
    "test_uprime_synthetic_recovery_coordinator_publishing_lock_oracle_and_exclusions",
    "test_uprime_synthetic_recovery_coordinator_cross_instance_has_no_global_lock",
    "test_uprime_synthetic_recovery_coordinator_simultaneous_acquire_exactly_one_epoch",
    "test_uprime_synthetic_recovery_coordinator_simultaneous_witness_consume_once",
    "test_uprime_synthetic_recovery_coordinator_recovery_never_reenters_cas_or_publisher",
    "test_uprime_synthetic_recovery_coordinator_direct_step_call_bounds_and_lock_state",
    "test_uprime_synthetic_recovery_coordinator_normal_residue_is_per_call_not_lifetime",
    "test_uprime_synthetic_recovery_coordinator_dynamic_transcripts_recompute",
    "test_uprime_synthetic_recovery_coordinator_all_preregistered_numeric_goldens",
    "test_uprime_synthetic_recovery_coordinator_exact_negative_labels_and_false_authority",
    "test_uprime_synthetic_recovery_coordinator_detectable_private_tampering_fails_closed",
    "test_uprime_synthetic_recovery_coordinator_handle_issuer_tamper_rejects",
    "test_uprime_synthetic_recovery_coordinator_resource_slots_are_bounded",
    "test_uprime_synthetic_recovery_coordinator_ast_forbids_expanded_capabilities",
    "test_uprime_synthetic_recovery_coordinator_anchors_registry_and_collection",
    "test_uprime_synthetic_recovery_coordinator_support_exports_exact_ordered_tests_only",
]

__all__ = list(EXPECTED_TEST_EXPORTS)
