from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import threading

from lean_rgc.evals.uprime_rpc_fake_cas_kernel import (
    InMemoryFakeCasStateV10,
    InMemoryFakeCasTransitionV10,
    InMemoryFakeCasV10Error,
    step_in_memory_fake_cas_v1_0,
)
from lean_rgc.evals.uprime_rpc_local_staging_fake_publisher import (
    LocalStagingFakePublishResultV10,
    LocalStagingFakePublisherV10Error,
    stage_and_fake_publish_normal_v1_0,
)


__all__ = [
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


_MARKER_SCHEMA = "lean-rgc-uprime-u1-synthetic-recovery-marker-v1.0"
_MARKER_SCOPE = "one_live_coordinator_single_slot_synthetic_marker"
_SNAPSHOT_SCHEMA = "lean-rgc-uprime-u1-synthetic-recovery-snapshot-v1.0"
_SNAPSHOT_SCOPE = "same_process_same_live_coordinator_value_snapshot"
_ACTION_SCHEMA = "lean-rgc-uprime-u1-synthetic-recovery-action-v1.0"
_ACTION_SCOPE = "one_coordinator_operation_lock_linearization_observation"
_ORIGIN_STATUS = "unknown_may_be_synthetic"

_CALLER_PROFILE_SCOPE = "caller_selected_constructor_profile_not_observed_cause"
_CAUSE_SCOPE = "same_kernel_synthetic_scenario_not_environmental_causality"
_JOURNAL_SCOPE = "single_slot_in_memory_marker_not_durable_journal"
_STAGE_BINDING_SCOPE = "publisher_operation_hash_only_no_current_stage_reobservation"
_FAILURE_CODE_SCOPE = "internal_fixed_mapping_not_caller_supplied_cause_evidence"
_CLEANUP_SCOPE = "not_performed_unsafe_without_later_artifact_archive_binding"
_MARKER_PROVENANCE = "internally_derived_after_owned_exact_changed_result"
_FIXED_PROFILE_SCOPE = "immutable_caller_selected_five_row_synthetic_profile"
_COORDINATOR_OWNERSHIP_SCOPE = "same_live_coordinator_owned_phase2b2d_call_only"
_CONCURRENCY_SCOPE = "same_live_coordinator_exclusion_only"
_RAW_BYPASS_SCOPE = "raw_phase2b2d_and_cross_process_bypass_not_prevented"
_COLLISION_NONCE_SCOPE = "phase2b2d_collision_nonce_not_epoch_identity"
_REPLAY_SCOPE = "bounded_same_kernel_replay_no_stage_or_remote_reobservation"
_WITNESS_SCOPE = "same_instance_object_identity_single_use_witness"
_DETACHED_RECORD_SCOPE = "detached_records_and_hashes_forgeable_not_capabilities"
_TAMPER_SCOPE = "private_slot_reflection_or_module_monkeypatch_tampering_not_prevented"
_PRE_MARKER_ERROR_SCOPE = "pre_marker_errors_and_outside_calls_unjournaled"
_STAGE_RESIDUE_SCOPE = "stage_residue_may_remain_not_owned_current_durable_or_safe_to_remove"
_PROCESS_RESTART_SCOPE = "no_restart_reconstruction_or_crash_recovery"
_MANIFEST_SCOPE = "not_read_or_written"
_REMOTE_PUBLICATION = "not_performed"
_AUTHORITY_SCOPE = "none"
_EXCLUSION_SCOPE = "coordinator_methods_only_no_global_or_cross_process_lock"
_ACTION_RECORD_SCOPE = "lock_linearization_value_not_return_time_history_or_attestation"
_OPAQUE_HANDLE_SCOPE = "exact_same_instance_object_reference_is_only_live_authority"
_HASH_AUTHORITY_SCOPE = "deterministic_digest_not_identity_freshness_or_capability"
_REMOTE_REOBSERVATION_SCOPE = "not_performed"

_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_MARKERS = 1
_MAX_ACTIVE_EPOCHS = 1
_MAX_RECOVERY_EPOCHS = 4
_MAX_WITNESSES = 1
_MAX_RETAINED_PAYLOAD_REFERENCES = 3_145_728
_MAX_RETAINED_PAYLOAD_COPIES = 0

_PROFILES = (
    "normal",
    "ack_loss_confirmed",
    "ack_loss_unavailable_then_confirmed",
    "ack_loss_unavailable_until_budget_block",
    "wrong_delta_confirmed",
)
_LIFECYCLES = (
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
_OPERATIONS = (
    "publish",
    "acquire_epoch",
    "release_epoch",
    "abandon_epoch",
    "replay_epoch",
    "consume_witness",
)
_D_CONFIG = b"lean-rgc-uprime-u1-synthetic-recovery-config-v1\0"
_D_PLAN = b"lean-rgc-uprime-u1-synthetic-recovery-plan-v1\0"
_D_MARKER = b"lean-rgc-uprime-u1-synthetic-recovery-marker-v1\0"
_D_EPOCH_NONCE = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-nonce-v1\0"
_D_EPOCH = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-v1\0"
_D_TERMINAL = b"lean-rgc-uprime-u1-synthetic-recovery-terminal-v1\0"
_D_WITNESS_NONCE = b"lean-rgc-uprime-u1-synthetic-recovery-witness-nonce-v1\0"
_D_WITNESS = b"lean-rgc-uprime-u1-synthetic-recovery-witness-v1\0"
_D_SNAPSHOT = b"lean-rgc-uprime-u1-synthetic-recovery-snapshot-v1\0"
_D_ACTION = b"lean-rgc-uprime-u1-synthetic-recovery-action-v1\0"
_UPPER_HEX64_PATTERN = r"[0-9A-F]{64}\Z"
_LOCK_TYPE = type(threading.Lock())

_S_ISSUER = 0
_S_CONFIG = 1
_S_PROFILE = 2
_S_ALTERNATE = 3
_S_ALTERNATE_BYTES = 4
_S_ALTERNATE_SHA = 5
_S_LIFECYCLE = 6
_S_MARKER = 7
_S_ISSUE_COUNT = 8
_S_REPLAY_COUNT = 9
_S_ACTIVE_EPOCH = 10
_S_TERMINAL_EPOCH = 11
_S_TERMINAL_KIND = 12
_S_TERMINAL_REASON = 13
_S_TERMINAL_SHA = 14
_S_WITNESS = 15
_S_WITNESS_STATUS = 16
_S_REPLAY_ROWS = 17
_STATE_LENGTH = 18


class SyntheticRecoveryCoordinatorV10Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SyntheticRecoveryMarkerV10:
    marker_schema_version: str
    marker_scope: str
    origin_status: str
    constructor_profile: str
    coordinator_config_sha256: str
    marker_kind: str
    marker_ordinal: int
    phase2b1_failure_codes: tuple[str, ...]
    publisher_outcome: str
    publisher_operation_sha256: str
    publisher_transition_sha256: str
    synthetic_fault_outcome: str
    synthetic_fault_transition_sha256: str
    replay_plan_sha256: str
    replay_plan_row_count: int
    before_state_version_sha256: str
    intended_after_state_version_sha256: str
    actual_after_state_version_sha256: str
    intended_delta_sha256: str
    actual_delta_sha256: str
    stage_payload_bytes: int
    stage_payload_sha256: str
    marker_sha256: str
    caller_profile_scope: str
    cause_scope: str
    journal_scope: str
    stage_binding_scope: str
    failure_code_scope: str
    cleanup_scope: str
    marker_provenance: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_marker(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoveryMarkerV10 cannot be subclassed")


@dataclass(frozen=True, slots=True)
class SyntheticRecoverySnapshotV10:
    snapshot_schema_version: str
    snapshot_scope: str
    origin_status: str
    constructor_profile: str
    profile_status: str
    alternate_payload_bytes: int | None
    alternate_payload_sha256: str | None
    coordinator_config_sha256: str
    lifecycle_state: str
    marker: SyntheticRecoveryMarkerV10 | None
    marker_count: int
    epoch_issue_count: int
    replay_attempt_count: int
    active_epoch_ordinal: int | None
    active_epoch_nonce_sha256: str | None
    terminal_epoch_ordinal: int | None
    terminal_epoch_nonce_sha256: str | None
    witness_status: str
    witness_purpose: str | None
    witness_nonce_sha256: str | None
    terminal_kind: str | None
    terminal_reason: str | None
    terminal_sha256: str | None
    snapshot_sha256: str
    marker_count_upper_bound: int
    active_epoch_upper_bound: int
    recovery_epoch_upper_bound: int
    witness_count_upper_bound: int
    retained_payload_reference_upper_bound_bytes: int
    retained_payload_copy_upper_bound_bytes: int
    fixed_profile_scope: str
    coordinator_ownership_scope: str
    concurrency_scope: str
    raw_bypass_scope: str
    collision_nonce_scope: str
    replay_scope: str
    witness_scope: str
    detached_record_scope: str
    tamper_scope: str
    pre_marker_error_scope: str
    stage_residue_scope: str
    cleanup_scope: str
    journal_scope: str
    process_restart_scope: str
    manifest_scope: str
    remote_publication: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_snapshot(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoverySnapshotV10 cannot be subclassed")


@dataclass(frozen=True, slots=True)
class SyntheticRecoveryActionV10:
    action_schema_version: str
    action_scope: str
    origin_status: str
    operation: str
    outcome: str
    reason_codes: tuple[str, ...]
    before_snapshot_sha256: str
    after_snapshot: SyntheticRecoverySnapshotV10
    endpoint_state_changed: bool
    publish_result: LocalStagingFakePublishResultV10 | None
    marker: SyntheticRecoveryMarkerV10 | None
    issued_epoch: SyntheticRecoveryEpochV10 | None
    issued_witness: SyntheticRecoveryWitnessV10 | None
    terminal_sha256: str | None
    epoch_ordinal: int | None
    replay_observation: str | None
    action_sha256: str
    exclusion_scope: str
    action_record_scope: str
    opaque_handle_scope: str
    hash_authority_scope: str
    cleanup_scope: str
    stage_residue_scope: str
    journal_scope: str
    process_scope: str
    remote_reobservation_scope: str
    manifest_scope: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_action(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoveryActionV10 cannot be subclassed")


_ACTION_RECORD_TYPE = SyntheticRecoveryActionV10
_FACTORY_SENTINEL = object()


class SyntheticRecoveryEpochV10:
    __slots__ = (
        "_issuer",
        "_epoch_ordinal",
        "_epoch_nonce_sha256",
        "_epoch_sha256",
    )

    def __new__(cls, token: object = None, /) -> SyntheticRecoveryEpochV10:
        if cls is not SyntheticRecoveryEpochV10 or token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryEpochV10 is factory-only")
        return object.__new__(cls)

    def __init__(self, token: object = None, /) -> None:
        if token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryEpochV10 is factory-only")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoveryEpochV10 cannot be subclassed")

    def __copy__(self) -> object:
        _fail("SyntheticRecoveryEpochV10 cannot be copied")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        _fail("SyntheticRecoveryEpochV10 cannot be deep-copied")

    def __reduce__(self) -> object:
        _fail("SyntheticRecoveryEpochV10 cannot be pickled")

    def __reduce_ex__(self, protocol: object) -> object:
        del protocol
        _fail("SyntheticRecoveryEpochV10 cannot be pickled")

    @property
    def epoch_ordinal(self) -> int:
        return self._epoch_ordinal

    @property
    def epoch_nonce_sha256(self) -> str:
        return self._epoch_nonce_sha256

    @property
    def epoch_sha256(self) -> str:
        return self._epoch_sha256


class SyntheticRecoveryWitnessV10:
    __slots__ = (
        "_issuer",
        "_purpose",
        "_terminal_sha256",
        "_witness_nonce_sha256",
        "_witness_sha256",
    )

    def __new__(cls, token: object = None, /) -> SyntheticRecoveryWitnessV10:
        if cls is not SyntheticRecoveryWitnessV10 or token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryWitnessV10 is factory-only")
        return object.__new__(cls)

    def __init__(self, token: object = None, /) -> None:
        if token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryWitnessV10 is factory-only")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoveryWitnessV10 cannot be subclassed")

    def __copy__(self) -> object:
        _fail("SyntheticRecoveryWitnessV10 cannot be copied")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        _fail("SyntheticRecoveryWitnessV10 cannot be deep-copied")

    def __reduce__(self) -> object:
        _fail("SyntheticRecoveryWitnessV10 cannot be pickled")

    def __reduce_ex__(self, protocol: object) -> object:
        del protocol
        _fail("SyntheticRecoveryWitnessV10 cannot be pickled")

    @property
    def purpose(self) -> str:
        return self._purpose

    @property
    def terminal_sha256(self) -> str:
        return self._terminal_sha256

    @property
    def witness_nonce_sha256(self) -> str:
        return self._witness_nonce_sha256

    @property
    def witness_sha256(self) -> str:
        return self._witness_sha256


class SyntheticRecoveryCoordinatorV10:
    __slots__ = (
        "_lock",
        "_issuer",
        "_profile",
        "_alternate_payload",
        "_config_sha256",
        "_publishing_state",
        "_poisoned_state",
        "_state",
    )

    def __new__(cls, token: object = None, /) -> SyntheticRecoveryCoordinatorV10:
        if cls is not SyntheticRecoveryCoordinatorV10 or token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryCoordinatorV10 is factory-only")
        return object.__new__(cls)

    def __init__(self, token: object = None, /) -> None:
        if token is not _FACTORY_SENTINEL:
            _fail("SyntheticRecoveryCoordinatorV10 is factory-only")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticRecoveryCoordinatorV10 cannot be subclassed")

    def __copy__(self) -> object:
        _fail("SyntheticRecoveryCoordinatorV10 cannot be copied")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        _fail("SyntheticRecoveryCoordinatorV10 cannot be deep-copied")

    def __reduce__(self) -> object:
        _fail("SyntheticRecoveryCoordinatorV10 cannot be pickled")

    def __reduce_ex__(self, protocol: object) -> object:
        del protocol
        _fail("SyntheticRecoveryCoordinatorV10 cannot be pickled")


def _fail(message: str) -> None:
    raise SyntheticRecoveryCoordinatorV10Error(message) from None


def _require_str(value: object, name: str) -> str:
    if type(value) is not str:
        _fail(f"{name} is not an exact string")
    return value


def _require_int(value: object, name: str) -> int:
    if type(value) is not int:
        _fail(f"{name} is not an exact integer")
    return value


def _require_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        _fail(f"{name} is not an exact boolean")
    return value


def _require_bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes:
        _fail(f"{name} is not exact bytes")
    return value


def _require_hash(value: object, name: str) -> str:
    text = _require_str(value, name)
    if re.fullmatch(_UPPER_HEX64_PATTERN, text, flags=re.ASCII) is None:
        _fail(f"{name} is not exact uppercase hex64")
    return text


def _u8(value: int, /) -> bytes:
    number = _require_int(value, "u8 value")
    if number < 0 or number > 255:
        _fail("u8 value is out of range")
    return bytes((number,))


def _u16(value: int, /) -> bytes:
    number = _require_int(value, "u16 value")
    if number < 0 or number > 65_535:
        _fail("u16 value is out of range")
    return number.to_bytes(2, "big")


def _u64(value: int, /) -> bytes:
    number = _require_int(value, "u64 value")
    if number < 0 or number > 18_446_744_073_709_551_615:
        _fail("u64 value is out of range")
    return number.to_bytes(8, "big")


def _ascii(value: str, /) -> bytes:
    text = _require_str(value, "ASCII value")
    try:
        raw = text.encode("ascii")
    except UnicodeEncodeError:
        _fail("ASCII value is not ASCII")
    if len(raw) > 65_535:
        _fail("ASCII value is too long")
    return raw


def _update_k(digest: object, value: str, /) -> None:
    raw = _ascii(value)
    digest.update(_u16(len(raw)))
    digest.update(raw)


def _update_h(digest: object, value: str, /) -> None:
    digest.update(bytes.fromhex(_require_hash(value, "hash value")))


def _update_q(digest: object, value: str | None, /) -> None:
    if value is None:
        digest.update(b"\x00")
    else:
        digest.update(b"\x01")
        _update_h(digest, value)


def _update_j(digest: object, value: int | None, /) -> None:
    if value is None:
        digest.update(b"\x00")
    else:
        digest.update(b"\x01")
        digest.update(_u64(value))


def _update_s(digest: object, value: str | None, /) -> None:
    if value is None:
        digest.update(b"\x00")
    else:
        digest.update(b"\x01")
        _update_k(digest, value)


def _update_t(digest: object, values: tuple[str, ...], /) -> None:
    if type(values) is not tuple or len(values) > 65_535:
        _fail("string tuple is invalid")
    digest.update(_u16(len(values)))
    for value in values:
        _update_k(digest, value)


def _finish(digest: object, /) -> str:
    value = digest.hexdigest()
    text = _require_str(value, "computed SHA-256")
    return _require_hash(text.upper(), "computed SHA-256")


def _raw_sha256(value: bytes, /) -> str:
    digest = hashlib.sha256()
    digest.update(_require_bytes(value, "payload"))
    return _finish(digest)


def _config_sha256(profile: str, alternate: bytes | None, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_CONFIG)
    _update_k(digest, profile)
    if alternate is None:
        digest.update(b"\x00")
    else:
        raw = _require_bytes(alternate, "alternate_payload")
        digest.update(b"\x01")
        digest.update(_u64(len(raw)))
        digest.update(raw)
    return _finish(digest)


def _plan_sha256(
    profile: str,
    rows: tuple[tuple[str, InMemoryFakeCasTransitionV10], ...],
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_PLAN)
    _update_k(digest, profile)
    digest.update(_u16(len(rows)))
    for observation, transition in rows:
        _update_k(digest, observation)
        _update_h(digest, transition.transition_sha256)
    return _finish(digest)


def _marker_sha256(value: SyntheticRecoveryMarkerV10, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_MARKER)
    _update_h(digest, value.coordinator_config_sha256)
    digest.update(_u64(value.marker_ordinal))
    _update_k(digest, value.marker_kind)
    _update_t(digest, value.phase2b1_failure_codes)
    _update_k(digest, value.publisher_outcome)
    _update_h(digest, value.publisher_operation_sha256)
    _update_h(digest, value.publisher_transition_sha256)
    _update_k(digest, value.synthetic_fault_outcome)
    _update_h(digest, value.synthetic_fault_transition_sha256)
    _update_h(digest, value.replay_plan_sha256)
    digest.update(_u16(value.replay_plan_row_count))
    _update_h(digest, value.before_state_version_sha256)
    _update_h(digest, value.intended_after_state_version_sha256)
    _update_h(digest, value.actual_after_state_version_sha256)
    _update_h(digest, value.intended_delta_sha256)
    _update_h(digest, value.actual_delta_sha256)
    digest.update(_u64(value.stage_payload_bytes))
    _update_h(digest, value.stage_payload_sha256)
    return _finish(digest)


def _epoch_nonce_sha256(config: str, marker: str, ordinal: int, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_EPOCH_NONCE)
    _update_h(digest, config)
    _update_h(digest, marker)
    digest.update(_u64(ordinal))
    return _finish(digest)


def _epoch_sha256(config: str, marker: str, ordinal: int, nonce: str, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_EPOCH)
    _update_h(digest, config)
    _update_h(digest, marker)
    digest.update(_u64(ordinal))
    _update_h(digest, nonce)
    return _finish(digest)


def _terminal_sha256(
    config: str,
    marker: str,
    kind: str,
    reason: str,
    ordinal: int,
    nonce: str,
    issue_count: int,
    replay_count: int,
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_TERMINAL)
    _update_h(digest, config)
    _update_h(digest, marker)
    _update_k(digest, kind)
    _update_k(digest, reason)
    digest.update(_u64(ordinal))
    _update_h(digest, nonce)
    digest.update(_u64(issue_count))
    digest.update(_u64(replay_count))
    return _finish(digest)


def _witness_nonce_sha256(config: str, terminal: str, purpose: str, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_WITNESS_NONCE)
    _update_h(digest, config)
    _update_h(digest, terminal)
    _update_k(digest, purpose)
    return _finish(digest)


def _witness_sha256(
    config: str,
    terminal: str,
    purpose: str,
    nonce: str,
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_WITNESS)
    _update_h(digest, config)
    _update_h(digest, terminal)
    _update_k(digest, purpose)
    _update_h(digest, nonce)
    return _finish(digest)


def _snapshot_sha256(value: SyntheticRecoverySnapshotV10, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_SNAPSHOT)
    _update_k(digest, value.constructor_profile)
    _update_k(digest, value.profile_status)
    _update_j(digest, value.alternate_payload_bytes)
    _update_q(digest, value.alternate_payload_sha256)
    _update_h(digest, value.coordinator_config_sha256)
    _update_k(digest, value.lifecycle_state)
    _update_q(digest, None if value.marker is None else value.marker.marker_sha256)
    digest.update(_u64(value.marker_count))
    digest.update(_u64(value.epoch_issue_count))
    digest.update(_u64(value.replay_attempt_count))
    _update_j(digest, value.active_epoch_ordinal)
    _update_q(digest, value.active_epoch_nonce_sha256)
    _update_j(digest, value.terminal_epoch_ordinal)
    _update_q(digest, value.terminal_epoch_nonce_sha256)
    _update_k(digest, value.witness_status)
    _update_s(digest, value.witness_purpose)
    _update_q(digest, value.witness_nonce_sha256)
    _update_s(digest, value.terminal_kind)
    _update_s(digest, value.terminal_reason)
    _update_q(digest, value.terminal_sha256)
    return _finish(digest)


def _action_sha256(value: SyntheticRecoveryActionV10, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_ACTION)
    _update_k(digest, value.operation)
    _update_k(digest, value.outcome)
    _update_t(digest, value.reason_codes)
    _update_h(digest, value.before_snapshot_sha256)
    _update_h(digest, value.after_snapshot.snapshot_sha256)
    digest.update(_u8(1 if value.endpoint_state_changed else 0))
    _update_q(
        digest,
        None if value.publish_result is None else value.publish_result.operation_sha256,
    )
    _update_q(digest, None if value.marker is None else value.marker.marker_sha256)
    _update_j(digest, value.epoch_ordinal)
    _update_s(digest, value.replay_observation)
    _update_q(digest, value.terminal_sha256)
    _update_s(digest, value.after_snapshot.witness_purpose)
    return _finish(digest)


def _validate_marker(value: SyntheticRecoveryMarkerV10, /) -> None:
    if type(value) is not SyntheticRecoveryMarkerV10:
        _fail("marker is not the exact public marker type")
    fixed = (
        (value.marker_schema_version, _MARKER_SCHEMA, "marker_schema_version"),
        (value.marker_scope, _MARKER_SCOPE, "marker_scope"),
        (value.origin_status, _ORIGIN_STATUS, "origin_status"),
        (value.caller_profile_scope, _CALLER_PROFILE_SCOPE, "caller_profile_scope"),
        (value.cause_scope, _CAUSE_SCOPE, "cause_scope"),
        (value.journal_scope, _JOURNAL_SCOPE, "journal_scope"),
        (value.stage_binding_scope, _STAGE_BINDING_SCOPE, "stage_binding_scope"),
        (value.failure_code_scope, _FAILURE_CODE_SCOPE, "failure_code_scope"),
        (value.cleanup_scope, _CLEANUP_SCOPE, "cleanup_scope"),
        (value.marker_provenance, _MARKER_PROVENANCE, "marker_provenance"),
        (value.authority_scope, _AUTHORITY_SCOPE, "authority_scope"),
    )
    for actual, expected, name in fixed:
        if _require_str(actual, name) != expected:
            _fail(f"{name} is invalid")
    profile = _require_str(value.constructor_profile, "constructor_profile")
    if profile not in _PROFILES[1:]:
        _fail("marker constructor_profile is invalid")
    for name in (
        "coordinator_config_sha256",
        "publisher_operation_sha256",
        "publisher_transition_sha256",
        "synthetic_fault_transition_sha256",
        "replay_plan_sha256",
        "before_state_version_sha256",
        "intended_after_state_version_sha256",
        "actual_after_state_version_sha256",
        "intended_delta_sha256",
        "actual_delta_sha256",
        "stage_payload_sha256",
        "marker_sha256",
    ):
        _require_hash(getattr(value, name), name)
    if _require_int(value.marker_ordinal, "marker_ordinal") != 1:
        _fail("marker_ordinal is invalid")
    if type(value.phase2b1_failure_codes) is not tuple or value.phase2b1_failure_codes != (
        "OTHER_HARNESS_ERROR",
    ):
        _fail("phase2b1_failure_codes is invalid")
    if _require_str(value.publisher_outcome, "publisher_outcome") != (
        "staged_intended_fake_publish_acknowledged"
    ):
        _fail("publisher_outcome is invalid")
    if profile == "ack_loss_confirmed":
        expected_kind = "synthetic_ack_loss_confirmed"
        expected_fault = "intended_applied_ack_lost_confirmed"
        expected_rows = 1
    elif profile in (
        "ack_loss_unavailable_then_confirmed",
        "ack_loss_unavailable_until_budget_block",
    ):
        expected_kind = "synthetic_ack_loss_unavailable"
        expected_fault = "intended_applied_ack_lost_unconfirmed"
        expected_rows = 2 if profile.endswith("then_confirmed") else 4
    else:
        expected_kind = "synthetic_wrong_delta_confirmed"
        expected_fault = "wrong_delta_confirmed"
        expected_rows = 1
    if _require_str(value.marker_kind, "marker_kind") != expected_kind:
        _fail("marker_kind is invalid")
    if _require_str(value.synthetic_fault_outcome, "synthetic_fault_outcome") != expected_fault:
        _fail("synthetic_fault_outcome is invalid")
    if _require_int(value.replay_plan_row_count, "replay_plan_row_count") != expected_rows:
        _fail("replay_plan_row_count is invalid")
    stage_bytes = _require_int(value.stage_payload_bytes, "stage_payload_bytes")
    if stage_bytes < 0 or stage_bytes > _MAX_PAYLOAD_BYTES:
        _fail("stage_payload_bytes is out of range")
    if (
        value.before_state_version_sha256
        == value.intended_after_state_version_sha256
        or value.before_state_version_sha256
        == value.actual_after_state_version_sha256
    ):
        _fail("marker state versions do not encode a changed transition")
    if profile == "wrong_delta_confirmed":
        if value.actual_after_state_version_sha256 == value.intended_after_state_version_sha256:
            _fail("wrong-delta state versions must differ")
        if value.actual_delta_sha256 == value.intended_delta_sha256:
            _fail("wrong-delta digests must differ")
    else:
        if value.actual_after_state_version_sha256 != value.intended_after_state_version_sha256:
            _fail("intended state versions must agree")
        if value.actual_delta_sha256 != value.intended_delta_sha256:
            _fail("intended delta digests must agree")
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        if _require_bool(getattr(value, name), name):
            _fail(f"{name} must be false")
    if value.marker_sha256 != _marker_sha256(value):
        _fail("marker_sha256 is invalid")


def _terminal_row_is_reachable(
    profile: str,
    kind: str,
    reason: str,
    issue_count: int,
    replay_count: int,
    /,
) -> bool:
    if kind == "recovered_terminal":
        if reason != "synthetic_intended_transition_confirmed":
            return False
        if profile == "ack_loss_confirmed":
            return replay_count == 1 and 1 <= issue_count <= 4
        if profile == "ack_loss_unavailable_then_confirmed":
            return replay_count == 2 and 2 <= issue_count <= 4
        return False
    if kind != "permanent_block":
        return False
    if reason == "synthetic_wrong_delta_confirmed":
        return (
            profile == "wrong_delta_confirmed"
            and replay_count == 1
            and 1 <= issue_count <= 4
        )
    if reason == "recovery_epoch_budget_exhausted_after_unavailable":
        if issue_count != 4:
            return False
        if profile == "ack_loss_unavailable_then_confirmed":
            return replay_count == 1
        if profile == "ack_loss_unavailable_until_budget_block":
            return 1 <= replay_count <= 4
        return False
    if reason not in (
        "recovery_epoch_budget_exhausted_after_release",
        "recovery_epoch_budget_exhausted_after_abandon",
    ) or issue_count != 4:
        return False
    if profile in ("ack_loss_confirmed", "wrong_delta_confirmed"):
        return replay_count == 0
    if profile == "ack_loss_unavailable_then_confirmed":
        return replay_count in (0, 1)
    if profile == "ack_loss_unavailable_until_budget_block":
        return 0 <= replay_count <= 3
    return False


def _validate_snapshot(value: SyntheticRecoverySnapshotV10, /) -> None:
    if type(value) is not SyntheticRecoverySnapshotV10:
        _fail("snapshot is not the exact public snapshot type")
    fixed = (
        (value.snapshot_schema_version, _SNAPSHOT_SCHEMA, "snapshot_schema_version"),
        (value.snapshot_scope, _SNAPSHOT_SCOPE, "snapshot_scope"),
        (value.origin_status, _ORIGIN_STATUS, "origin_status"),
        (value.fixed_profile_scope, _FIXED_PROFILE_SCOPE, "fixed_profile_scope"),
        (value.coordinator_ownership_scope, _COORDINATOR_OWNERSHIP_SCOPE, "coordinator_ownership_scope"),
        (value.concurrency_scope, _CONCURRENCY_SCOPE, "concurrency_scope"),
        (value.raw_bypass_scope, _RAW_BYPASS_SCOPE, "raw_bypass_scope"),
        (value.collision_nonce_scope, _COLLISION_NONCE_SCOPE, "collision_nonce_scope"),
        (value.replay_scope, _REPLAY_SCOPE, "replay_scope"),
        (value.witness_scope, _WITNESS_SCOPE, "witness_scope"),
        (value.detached_record_scope, _DETACHED_RECORD_SCOPE, "detached_record_scope"),
        (value.tamper_scope, _TAMPER_SCOPE, "tamper_scope"),
        (value.pre_marker_error_scope, _PRE_MARKER_ERROR_SCOPE, "pre_marker_error_scope"),
        (value.stage_residue_scope, _STAGE_RESIDUE_SCOPE, "stage_residue_scope"),
        (value.cleanup_scope, _CLEANUP_SCOPE, "cleanup_scope"),
        (value.journal_scope, _JOURNAL_SCOPE, "journal_scope"),
        (value.process_restart_scope, _PROCESS_RESTART_SCOPE, "process_restart_scope"),
        (value.manifest_scope, _MANIFEST_SCOPE, "manifest_scope"),
        (value.remote_publication, _REMOTE_PUBLICATION, "remote_publication"),
        (value.authority_scope, _AUTHORITY_SCOPE, "authority_scope"),
    )
    for actual, expected, name in fixed:
        if _require_str(actual, name) != expected:
            _fail(f"{name} is invalid")
    bounds = (
        (value.marker_count_upper_bound, _MAX_MARKERS, "marker_count_upper_bound"),
        (value.active_epoch_upper_bound, _MAX_ACTIVE_EPOCHS, "active_epoch_upper_bound"),
        (value.recovery_epoch_upper_bound, _MAX_RECOVERY_EPOCHS, "recovery_epoch_upper_bound"),
        (value.witness_count_upper_bound, _MAX_WITNESSES, "witness_count_upper_bound"),
        (value.retained_payload_reference_upper_bound_bytes, _MAX_RETAINED_PAYLOAD_REFERENCES, "retained_payload_reference_upper_bound_bytes"),
        (value.retained_payload_copy_upper_bound_bytes, _MAX_RETAINED_PAYLOAD_COPIES, "retained_payload_copy_upper_bound_bytes"),
    )
    for actual, expected, name in bounds:
        if _require_int(actual, name) != expected:
            _fail(f"{name} is invalid")
    profile = _require_str(value.constructor_profile, "constructor_profile")
    if profile not in _PROFILES:
        _fail("constructor_profile is invalid")
    if profile == "wrong_delta_confirmed":
        alternate_bytes = _require_int(value.alternate_payload_bytes, "alternate_payload_bytes")
        if alternate_bytes < 0 or alternate_bytes > _MAX_PAYLOAD_BYTES:
            _fail("alternate_payload_bytes is out of range")
        _require_hash(value.alternate_payload_sha256, "alternate_payload_sha256")
    elif value.alternate_payload_bytes is not None or value.alternate_payload_sha256 is not None:
        _fail("alternate payload cells must be null for this profile")
    _require_hash(value.coordinator_config_sha256, "coordinator_config_sha256")
    lifecycle = _require_str(value.lifecycle_state, "lifecycle_state")
    if lifecycle not in _LIFECYCLES:
        _fail("lifecycle_state is invalid")
    if lifecycle == "OPEN":
        expected_status = "normal_no_fault_profile" if profile == "normal" else "armed"
    elif lifecycle == "PUBLISHING":
        expected_status = "owned_call_in_progress"
    elif lifecycle == "POISONED_NO_MARKER":
        expected_status = "spent_without_marker"
    else:
        expected_status = "spent_marker_committed"
    if _require_str(value.profile_status, "profile_status") != expected_status:
        _fail("profile_status is invalid")
    marker = value.marker
    if marker is not None:
        _validate_marker(marker)
        if marker.constructor_profile != profile or marker.coordinator_config_sha256 != value.coordinator_config_sha256:
            _fail("snapshot marker binding is invalid")
    marker_count = _require_int(value.marker_count, "marker_count")
    if marker_count != (0 if marker is None else 1):
        _fail("marker_count is invalid")
    issue_count = _require_int(value.epoch_issue_count, "epoch_issue_count")
    replay_count = _require_int(value.replay_attempt_count, "replay_attempt_count")
    if not 0 <= issue_count <= 4 or not 0 <= replay_count <= issue_count:
        _fail("epoch/replay counts are invalid")
    for name in (
        "active_epoch_ordinal",
        "terminal_epoch_ordinal",
    ):
        cell = getattr(value, name)
        if cell is not None:
            number = _require_int(cell, name)
            if not 1 <= number <= 4:
                _fail(f"{name} is out of range")
    for name in (
        "active_epoch_nonce_sha256",
        "terminal_epoch_nonce_sha256",
        "witness_nonce_sha256",
        "terminal_sha256",
        "snapshot_sha256",
    ):
        cell = getattr(value, name)
        if cell is not None:
            _require_hash(cell, name)
    nonterminal = lifecycle in _LIFECYCLES[:4] or lifecycle == "POISONED_NO_MARKER"
    if nonterminal:
        if value.witness_status != "none":
            _fail("nonterminal witness_status is invalid")
        if any(
            cell is not None
            for cell in (
                value.terminal_epoch_ordinal,
                value.terminal_epoch_nonce_sha256,
                value.witness_purpose,
                value.witness_nonce_sha256,
                value.terminal_kind,
                value.terminal_reason,
                value.terminal_sha256,
            )
        ):
            _fail("nonterminal terminal cells must be null")
    else:
        live = lifecycle.endswith("_LIVE")
        expected_witness_status = "live" if live else "spent"
        if value.witness_status != expected_witness_status:
            _fail("terminal witness_status is invalid")
        terminal_ordinal = _require_int(value.terminal_epoch_ordinal, "terminal_epoch_ordinal")
        if terminal_ordinal != issue_count:
            _fail("terminal epoch ordinal is invalid")
        terminal_nonce = _require_hash(value.terminal_epoch_nonce_sha256, "terminal_epoch_nonce_sha256")
        purpose = _require_str(value.witness_purpose, "witness_purpose")
        witness_nonce = _require_hash(value.witness_nonce_sha256, "witness_nonce_sha256")
        kind = _require_str(value.terminal_kind, "terminal_kind")
        reason = _require_str(value.terminal_reason, "terminal_reason")
        terminal_hash = _require_hash(value.terminal_sha256, "terminal_sha256")
        if kind == "recovered_terminal":
            if reason != "synthetic_intended_transition_confirmed" or purpose != "record_recovered_terminal":
                _fail("recovered terminal mapping is invalid")
            if lifecycle not in _LIFECYCLES[4:6]:
                _fail("recovered terminal lifecycle is invalid")
        elif kind == "permanent_block":
            if reason not in (
                "synthetic_wrong_delta_confirmed",
                "recovery_epoch_budget_exhausted_after_unavailable",
                "recovery_epoch_budget_exhausted_after_release",
                "recovery_epoch_budget_exhausted_after_abandon",
            ) or purpose != "record_permanent_block":
                _fail("blocked terminal mapping is invalid")
            if lifecycle not in _LIFECYCLES[6:8]:
                _fail("blocked terminal lifecycle is invalid")
        else:
            _fail("terminal_kind is invalid")
        if marker is None:
            _fail("terminal snapshot requires a marker")
        if terminal_nonce != _epoch_nonce_sha256(
            value.coordinator_config_sha256,
            marker.marker_sha256,
            terminal_ordinal,
        ):
            _fail("terminal_epoch_nonce_sha256 is invalid")
        if not _terminal_row_is_reachable(
            profile,
            kind,
            reason,
            issue_count,
            replay_count,
        ):
            _fail("terminal profile/cursor row is unreachable")
        expected_terminal = _terminal_sha256(
            value.coordinator_config_sha256,
            marker.marker_sha256,
            kind,
            reason,
            terminal_ordinal,
            terminal_nonce,
            issue_count,
            replay_count,
        )
        if terminal_hash != expected_terminal:
            _fail("terminal_sha256 is invalid")
        if witness_nonce != _witness_nonce_sha256(value.coordinator_config_sha256, terminal_hash, purpose):
            _fail("witness_nonce_sha256 is invalid")
    if lifecycle in ("OPEN", "PUBLISHING", "POISONED_NO_MARKER"):
        if marker is not None or issue_count != 0 or replay_count != 0:
            _fail("marker-free lifecycle counters are invalid")
        if value.active_epoch_ordinal is not None or value.active_epoch_nonce_sha256 is not None:
            _fail("marker-free active epoch cells must be null")
    elif lifecycle == "RECOVERY_PENDING":
        if marker is None or issue_count > 3:
            _fail("pending lifecycle cells are invalid")
        if value.active_epoch_ordinal is not None or value.active_epoch_nonce_sha256 is not None:
            _fail("pending active epoch cells must be null")
    elif lifecycle == "RECOVERY_ACTIVE":
        if marker is None:
            _fail("active lifecycle requires a marker")
        if _require_int(value.active_epoch_ordinal, "active_epoch_ordinal") != issue_count:
            _fail("active epoch ordinal is invalid")
        active_nonce = _require_hash(
            value.active_epoch_nonce_sha256,
            "active_epoch_nonce_sha256",
        )
        if active_nonce != _epoch_nonce_sha256(
            value.coordinator_config_sha256,
            marker.marker_sha256,
            issue_count,
        ):
            _fail("active_epoch_nonce_sha256 is invalid")
        if replay_count > issue_count - 1:
            _fail("active replay cursor is invalid")
    else:
        if value.active_epoch_ordinal is not None or value.active_epoch_nonce_sha256 is not None:
            _fail("terminal active epoch cells must be null")
    if marker is not None:
        if profile in ("ack_loss_confirmed", "wrong_delta_confirmed") and lifecycle in (
            "RECOVERY_PENDING",
            "RECOVERY_ACTIVE",
        ) and replay_count != 0:
            _fail("profile replay cursor is unreachable")
        if profile == "ack_loss_unavailable_then_confirmed" and lifecycle in (
            "RECOVERY_PENDING",
            "RECOVERY_ACTIVE",
        ) and replay_count not in (0, 1):
            _fail("profile replay cursor is unreachable")
        if profile == "normal":
            _fail("normal profile cannot carry a marker")
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        if _require_bool(getattr(value, name), name):
            _fail(f"{name} must be false")
    if value.snapshot_sha256 != _snapshot_sha256(value):
        _fail("snapshot_sha256 is invalid")


def _validate_action_epoch_binding(value: SyntheticRecoveryActionV10, /) -> None:
    epoch = value.issued_epoch
    if epoch is None:
        return
    after = value.after_snapshot
    marker = after.marker
    if marker is None:
        _fail("issued_epoch requires an after-snapshot marker")
    try:
        issuer = epoch._issuer
        ordinal = _require_int(epoch._epoch_ordinal, "issued epoch ordinal")
        nonce = _require_hash(epoch._epoch_nonce_sha256, "issued epoch nonce")
        digest = _require_hash(epoch._epoch_sha256, "issued epoch hash")
    except SyntheticRecoveryCoordinatorV10Error:
        raise
    except Exception:
        _fail("issued_epoch private slots are invalid")
    if type(issuer) is not object:
        _fail("issued_epoch issuer is invalid")
    if (
        ordinal != value.epoch_ordinal
        or ordinal != after.epoch_issue_count
        or ordinal != after.active_epoch_ordinal
        or nonce != after.active_epoch_nonce_sha256
    ):
        _fail("issued_epoch ordinal/snapshot binding is invalid")
    expected_nonce = _epoch_nonce_sha256(
        after.coordinator_config_sha256,
        marker.marker_sha256,
        ordinal,
    )
    if nonce != expected_nonce or digest != _epoch_sha256(
        after.coordinator_config_sha256,
        marker.marker_sha256,
        ordinal,
        nonce,
    ):
        _fail("issued_epoch digest binding is invalid")


def _validate_action_witness_binding(value: SyntheticRecoveryActionV10, /) -> None:
    witness = value.issued_witness
    if witness is None:
        return
    after = value.after_snapshot
    try:
        issuer = witness._issuer
        purpose = _require_str(witness._purpose, "issued witness purpose")
        terminal = _require_hash(
            witness._terminal_sha256,
            "issued witness terminal",
        )
        nonce = _require_hash(
            witness._witness_nonce_sha256,
            "issued witness nonce",
        )
        digest = _require_hash(witness._witness_sha256, "issued witness hash")
    except SyntheticRecoveryCoordinatorV10Error:
        raise
    except Exception:
        _fail("issued_witness private slots are invalid")
    if type(issuer) is not object:
        _fail("issued_witness issuer is invalid")
    if (
        after.witness_status != "live"
        or purpose != after.witness_purpose
        or terminal != after.terminal_sha256
        or nonce != after.witness_nonce_sha256
    ):
        _fail("issued_witness snapshot binding is invalid")
    expected_nonce = _witness_nonce_sha256(
        after.coordinator_config_sha256,
        terminal,
        purpose,
    )
    if nonce != expected_nonce or digest != _witness_sha256(
        after.coordinator_config_sha256,
        terminal,
        purpose,
        nonce,
    ):
        _fail("issued_witness digest binding is invalid")


def _validate_action_row_coherence(
    value: SyntheticRecoveryActionV10,
    changed: bool,
    /,
) -> None:
    operation = value.operation
    outcome = value.outcome
    after = value.after_snapshot
    lifecycle = after.lifecycle_state
    ordinal = value.epoch_ordinal
    row = (operation, outcome)
    valid = False
    expected_changed = False

    if row in (
        ("publish", "cas_conflict_no_marker"),
        ("publish", "cas_existing_identical_no_marker"),
    ):
        valid = lifecycle == "OPEN" and value.publish_result is not None
    elif row == ("publish", "normal_staged_result_exposed_no_marker"):
        valid = (
            lifecycle == "OPEN"
            and after.constructor_profile == "normal"
            and value.publish_result is not None
        )
    elif row == ("publish", "synthetic_marker_committed_result_withheld"):
        valid = (
            lifecycle == "RECOVERY_PENDING"
            and after.epoch_issue_count == 0
            and after.replay_attempt_count == 0
        )
        expected_changed = True
    elif row == ("publish", "publisher_excluded_non_open"):
        valid = lifecycle != "OPEN"
    elif row == ("acquire_epoch", "no_marker_noop"):
        valid = lifecycle == "OPEN"
    elif row == ("acquire_epoch", "publisher_active_excluded"):
        valid = lifecycle == "PUBLISHING"
    elif row == ("acquire_epoch", "epoch_issued"):
        valid = lifecycle == "RECOVERY_ACTIVE"
        expected_changed = True
    elif row == ("acquire_epoch", "recovery_active_excluded"):
        valid = lifecycle == "RECOVERY_ACTIVE"
    elif row == ("acquire_epoch", "recovered_terminal_noop"):
        valid = lifecycle.startswith("RECOVERED_")
    elif row == ("acquire_epoch", "blocked_terminal_noop"):
        valid = lifecycle.startswith("BLOCKED_")
    elif row == ("acquire_epoch", "poisoned_no_marker_noop"):
        valid = lifecycle == "POISONED_NO_MARKER"
    elif row in (
        ("release_epoch", "publisher_active_excluded"),
        ("abandon_epoch", "publisher_active_excluded"),
        ("replay_epoch", "publisher_active_excluded"),
        ("consume_witness", "publisher_active_excluded"),
    ):
        valid = lifecycle == "PUBLISHING"
    elif row in (
        ("release_epoch", "epoch_released_retry_pending"),
        ("abandon_epoch", "epoch_abandoned_retry_pending"),
        ("replay_epoch", "replay_unavailable_retry_pending"),
    ):
        valid = (
            lifecycle == "RECOVERY_PENDING"
            and ordinal == after.epoch_issue_count
            and ordinal is not None
            and 1 <= ordinal < _MAX_RECOVERY_EPOCHS
        )
        expected_changed = True
        if row == ("replay_epoch", "replay_unavailable_retry_pending"):
            valid = valid and (
                (
                    after.constructor_profile
                    == "ack_loss_unavailable_then_confirmed"
                    and after.replay_attempt_count == 1
                )
                or (
                    after.constructor_profile
                    == "ack_loss_unavailable_until_budget_block"
                    and 1
                    <= after.replay_attempt_count
                    < _MAX_RECOVERY_EPOCHS
                )
            )
    elif row in (
        ("release_epoch", "epoch_release_budget_permanent_block"),
        ("abandon_epoch", "epoch_abandon_budget_permanent_block"),
        ("replay_epoch", "replay_unavailable_budget_permanent_block"),
    ):
        expected_reason = {
            "epoch_release_budget_permanent_block": (
                "recovery_epoch_budget_exhausted_after_release"
            ),
            "epoch_abandon_budget_permanent_block": (
                "recovery_epoch_budget_exhausted_after_abandon"
            ),
            "replay_unavailable_budget_permanent_block": (
                "recovery_epoch_budget_exhausted_after_unavailable"
            ),
        }[outcome]
        valid = (
            lifecycle == "BLOCKED_WITNESS_LIVE"
            and after.terminal_reason == expected_reason
            and ordinal == _MAX_RECOVERY_EPOCHS
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )
        expected_changed = True
    elif row == ("replay_epoch", "replay_confirmed_recovered"):
        valid = (
            lifecycle == "RECOVERED_WITNESS_LIVE"
            and after.terminal_reason
            == "synthetic_intended_transition_confirmed"
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )
        expected_changed = True
    elif row == ("replay_epoch", "replay_wrong_delta_permanent_block"):
        valid = (
            lifecycle == "BLOCKED_WITNESS_LIVE"
            and after.terminal_reason == "synthetic_wrong_delta_confirmed"
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )
        expected_changed = True
    elif row in (
        ("replay_epoch", "recovered_terminal_noop"),
        ("replay_epoch", "blocked_terminal_noop"),
    ):
        expected_prefix = (
            "RECOVERED_" if outcome == "recovered_terminal_noop" else "BLOCKED_"
        )
        valid = (
            lifecycle.startswith(expected_prefix)
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )
    elif row == ("consume_witness", "witness_consumed"):
        valid = (
            lifecycle
            in ("RECOVERED_WITNESS_SPENT", "BLOCKED_WITNESS_SPENT")
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )
        expected_changed = True
    elif row == ("consume_witness", "witness_already_spent_noop"):
        valid = (
            lifecycle
            in ("RECOVERED_WITNESS_SPENT", "BLOCKED_WITNESS_SPENT")
            and ordinal == after.epoch_issue_count
            and ordinal == after.terminal_epoch_ordinal
        )

    if not valid or changed is not expected_changed:
        _fail("action row/after_snapshot coherence is invalid")
    _validate_action_epoch_binding(value)
    _validate_action_witness_binding(value)


def _validate_action(value: SyntheticRecoveryActionV10, /) -> None:
    if type(value) is not SyntheticRecoveryActionV10:
        _fail("action is not the exact public action type")
    fixed = (
        (value.action_schema_version, _ACTION_SCHEMA, "action_schema_version"),
        (value.action_scope, _ACTION_SCOPE, "action_scope"),
        (value.origin_status, _ORIGIN_STATUS, "origin_status"),
        (value.exclusion_scope, _EXCLUSION_SCOPE, "exclusion_scope"),
        (value.action_record_scope, _ACTION_RECORD_SCOPE, "action_record_scope"),
        (value.opaque_handle_scope, _OPAQUE_HANDLE_SCOPE, "opaque_handle_scope"),
        (value.hash_authority_scope, _HASH_AUTHORITY_SCOPE, "hash_authority_scope"),
        (value.cleanup_scope, _CLEANUP_SCOPE, "cleanup_scope"),
        (value.stage_residue_scope, _STAGE_RESIDUE_SCOPE, "stage_residue_scope"),
        (value.journal_scope, _JOURNAL_SCOPE, "journal_scope"),
        (value.process_scope, _PROCESS_RESTART_SCOPE, "process_scope"),
        (value.remote_reobservation_scope, _REMOTE_REOBSERVATION_SCOPE, "remote_reobservation_scope"),
        (value.manifest_scope, _MANIFEST_SCOPE, "manifest_scope"),
        (value.authority_scope, _AUTHORITY_SCOPE, "authority_scope"),
    )
    for actual, expected, name in fixed:
        if _require_str(actual, name) != expected:
            _fail(f"{name} is invalid")
    operation = _require_str(value.operation, "operation")
    if operation not in _OPERATIONS:
        _fail("operation is invalid")
    outcome = _require_str(value.outcome, "outcome")
    if type(value.reason_codes) is not tuple or len(value.reason_codes) != 1:
        _fail("reason_codes must be an exact one-element tuple")
    reason = _require_str(value.reason_codes[0], "reason code")
    _require_hash(value.before_snapshot_sha256, "before_snapshot_sha256")
    if type(value.after_snapshot) is not SyntheticRecoverySnapshotV10:
        _fail("after_snapshot is not the exact public snapshot type")
    _validate_snapshot(value.after_snapshot)
    changed = _require_bool(value.endpoint_state_changed, "endpoint_state_changed")
    if changed != (value.before_snapshot_sha256 != value.after_snapshot.snapshot_sha256):
        _fail("endpoint_state_changed is invalid")
    if value.publish_result is not None:
        if type(value.publish_result) is not LocalStagingFakePublishResultV10:
            _fail("publish_result is not the exact dependency Result type")
        _require_hash(value.publish_result.operation_sha256, "publish_result.operation_sha256")
    if value.marker != value.after_snapshot.marker:
        _fail("action marker does not match after_snapshot")
    if value.marker is not None:
        _validate_marker(value.marker)
    if value.issued_epoch is not None and type(value.issued_epoch) is not SyntheticRecoveryEpochV10:
        _fail("issued_epoch type is invalid")
    if value.issued_witness is not None and type(value.issued_witness) is not SyntheticRecoveryWitnessV10:
        _fail("issued_witness type is invalid")
    if value.terminal_sha256 != value.after_snapshot.terminal_sha256:
        _fail("action terminal_sha256 is invalid")
    if value.epoch_ordinal is not None:
        number = _require_int(value.epoch_ordinal, "epoch_ordinal")
        if not 1 <= number <= 4:
            _fail("epoch_ordinal is out of range")
    if value.replay_observation is not None and value.replay_observation not in (
        "unavailable",
        "confirmed_intended",
        "confirmed_wrong_delta",
        "terminal_noop",
    ):
        _fail("replay_observation is invalid")
    expected_reason: str | None = None
    if operation == "publish":
        rows = (
            ("cas_conflict_no_marker", "expected_state_version_mismatch"),
            ("cas_existing_identical_no_marker", "exact_payload_already_current"),
            ("normal_staged_result_exposed_no_marker", "exact_stage_retained_before_exposing_synthetic_acknowledged_transition"),
            ("synthetic_marker_committed_result_withheld", "synthetic_marker_committed"),
            ("publisher_excluded_non_open", "coordinator_not_open"),
        )
    elif operation == "acquire_epoch":
        rows = (
            ("no_marker_noop", "marker_absent"),
            ("publisher_active_excluded", "owned_publisher_active"),
            ("epoch_issued", "recovery_marker_pending"),
            ("recovery_active_excluded", "active_epoch_exists"),
            ("recovered_terminal_noop", "recovered_terminal"),
            ("blocked_terminal_noop", "permanent_block"),
            ("poisoned_no_marker_noop", "poisoned_no_marker"),
        )
    elif operation == "release_epoch":
        rows = (
            ("epoch_released_retry_pending", "epoch_released_replay_cursor_unchanged"),
            ("epoch_release_budget_permanent_block", "recovery_epoch_budget_exhausted_after_release"),
            ("publisher_active_excluded", "owned_publisher_active"),
        )
    elif operation == "abandon_epoch":
        rows = (
            ("epoch_abandoned_retry_pending", "epoch_abandoned_replay_cursor_unchanged"),
            ("epoch_abandon_budget_permanent_block", "recovery_epoch_budget_exhausted_after_abandon"),
            ("publisher_active_excluded", "owned_publisher_active"),
        )
    elif operation == "replay_epoch":
        rows = (
            ("publisher_active_excluded", "owned_publisher_active"),
            ("replay_unavailable_retry_pending", "same_kernel_replay_unavailable"),
            ("replay_unavailable_budget_permanent_block", "recovery_epoch_budget_exhausted_after_unavailable"),
            ("replay_confirmed_recovered", "synthetic_intended_transition_confirmed"),
            ("replay_wrong_delta_permanent_block", "synthetic_wrong_delta_confirmed"),
            ("recovered_terminal_noop", "recovered_terminal"),
            ("blocked_terminal_noop", "permanent_block"),
        )
    else:
        rows = (
            ("publisher_active_excluded", "owned_publisher_active"),
            ("witness_consumed", "witness_consumed"),
            ("witness_already_spent_noop", "witness_already_spent"),
        )
    for row_outcome, row_reason in rows:
        if outcome == row_outcome:
            expected_reason = row_reason
            break
    if expected_reason is None or reason != expected_reason:
        _fail("action outcome/reason row is invalid")
    publish_rows = (
        "cas_conflict_no_marker",
        "cas_existing_identical_no_marker",
        "normal_staged_result_exposed_no_marker",
    )
    if (value.publish_result is not None) != (outcome in publish_rows):
        _fail("publish_result nullability is invalid")
    if (value.issued_epoch is not None) != (outcome == "epoch_issued"):
        _fail("issued_epoch nullability is invalid")
    witness_outcomes = (
        "epoch_release_budget_permanent_block",
        "epoch_abandon_budget_permanent_block",
        "replay_unavailable_budget_permanent_block",
        "replay_confirmed_recovered",
        "replay_wrong_delta_permanent_block",
    )
    if (value.issued_witness is not None) != (outcome in witness_outcomes):
        _fail("issued_witness nullability is invalid")
    replay_values = {
        "replay_unavailable_retry_pending": "unavailable",
        "replay_unavailable_budget_permanent_block": "unavailable",
        "replay_confirmed_recovered": "confirmed_intended",
        "replay_wrong_delta_permanent_block": "confirmed_wrong_delta",
        "recovered_terminal_noop": "terminal_noop" if operation == "replay_epoch" else None,
        "blocked_terminal_noop": "terminal_noop" if operation == "replay_epoch" else None,
    }
    if value.replay_observation != replay_values.get(outcome):
        _fail("replay_observation nullability is invalid")
    needs_ordinal = outcome in (
        "epoch_issued",
        "epoch_released_retry_pending",
        "epoch_release_budget_permanent_block",
        "epoch_abandoned_retry_pending",
        "epoch_abandon_budget_permanent_block",
        "replay_unavailable_retry_pending",
        "replay_unavailable_budget_permanent_block",
        "replay_confirmed_recovered",
        "replay_wrong_delta_permanent_block",
        "witness_consumed",
        "witness_already_spent_noop",
    ) or (operation == "replay_epoch" and outcome in ("recovered_terminal_noop", "blocked_terminal_noop"))
    if (value.epoch_ordinal is not None) != needs_ordinal:
        _fail("epoch_ordinal nullability is invalid")
    _validate_action_row_coherence(value, changed)
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        if _require_bool(getattr(value, name), name):
            _fail(f"{name} must be false")
    _require_hash(value.action_sha256, "action_sha256")
    if value.action_sha256 != _action_sha256(value):
        _fail("action_sha256 is invalid")


def _unchecked_record(record_type: type, values: tuple[object, ...], /) -> object:
    if len(record_type.__slots__) != len(values):
        _fail("internal record arity is invalid")
    record = object.__new__(record_type)
    for name, value in zip(record_type.__slots__, values):
        object.__setattr__(record, name, value)
    return record


def _new_state_tuple(
    issuer: object,
    config: str,
    profile: str,
    alternate: bytes | None,
    alternate_bytes: int | None,
    alternate_sha: str | None,
    lifecycle: str,
    marker: SyntheticRecoveryMarkerV10 | None,
    issue_count: int,
    replay_count: int,
    active_epoch: SyntheticRecoveryEpochV10 | None,
    terminal_epoch: SyntheticRecoveryEpochV10 | None,
    terminal_kind: str | None,
    terminal_reason: str | None,
    terminal_sha: str | None,
    witness: SyntheticRecoveryWitnessV10 | None,
    witness_status: str,
    replay_rows: tuple[tuple[str, InMemoryFakeCasTransitionV10], ...],
    /,
) -> tuple[object, ...]:
    return (
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        lifecycle,
        marker,
        issue_count,
        replay_count,
        active_epoch,
        terminal_epoch,
        terminal_kind,
        terminal_reason,
        terminal_sha,
        witness,
        witness_status,
        replay_rows,
    )


def _base_state_tuple(
    issuer: object,
    config: str,
    profile: str,
    alternate: bytes | None,
    alternate_bytes: int | None,
    alternate_sha: str | None,
    lifecycle: str,
    /,
) -> tuple[object, ...]:
    return _new_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        lifecycle,
        None,
        0,
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        "none",
        (),
    )


def _validate_private_replay_rows(state: tuple[object, ...], /) -> None:
    lifecycle = state[_S_LIFECYCLE]
    rows = state[_S_REPLAY_ROWS]
    if type(rows) is not tuple:
        _fail("coordinator replay rows are invalid")
    if lifecycle not in ("RECOVERY_PENDING", "RECOVERY_ACTIVE"):
        if rows:
            _fail("coordinator replay rows survived outside recovery")
        return
    marker = state[_S_MARKER]
    if type(marker) is not SyntheticRecoveryMarkerV10:
        _fail("coordinator replay marker is invalid")
    profile = state[_S_PROFILE]
    expected_observations = {
        "ack_loss_confirmed": ("confirmed_intended",),
        "ack_loss_unavailable_then_confirmed": (
            "unavailable",
            "confirmed_intended",
        ),
        "ack_loss_unavailable_until_budget_block": (
            "unavailable",
            "unavailable",
            "unavailable",
            "unavailable",
        ),
        "wrong_delta_confirmed": ("confirmed_wrong_delta",),
    }.get(profile)
    if expected_observations is None or len(rows) != len(expected_observations):
        _fail("coordinator replay profile rows are invalid")
    expected_outcomes = {
        "unavailable": "intended_applied_ack_lost_unconfirmed",
        "confirmed_intended": "intended_applied_ack_lost_confirmed",
        "confirmed_wrong_delta": "wrong_delta_confirmed",
    }
    for index, row in enumerate(rows):
        if type(row) is not tuple or len(row) != 2:
            _fail("coordinator replay row is invalid")
        observation, transition = row
        if observation != expected_observations[index]:
            _fail("coordinator replay observation is invalid")
        if type(transition) is not InMemoryFakeCasTransitionV10:
            _fail("coordinator replay transition type is invalid")
        if transition.outcome != expected_outcomes[observation]:
            _fail("coordinator replay transition outcome is invalid")
        _require_hash(
            transition.transition_sha256,
            "coordinator replay transition hash",
        )
    if profile == "ack_loss_unavailable_until_budget_block" and any(
        row[1] is not rows[0][1] for row in rows[1:]
    ):
        _fail("coordinator repeated replay transition identity is invalid")
    first_transition = rows[0][1]
    if (
        marker.replay_plan_row_count != len(rows)
        or marker.replay_plan_sha256 != _plan_sha256(profile, rows)
        or marker.synthetic_fault_outcome != first_transition.outcome
        or marker.synthetic_fault_transition_sha256
        != first_transition.transition_sha256
    ):
        _fail("coordinator replay plan binding is invalid")


def _validate_private_state(
    coordinator: SyntheticRecoveryCoordinatorV10,
    state: tuple[object, ...],
    alternate_bytes: int | None,
    alternate_sha: str | None,
    /,
) -> None:
    if type(state) is not tuple or len(state) != _STATE_LENGTH:
        _fail("coordinator private state is invalid")
    if state[_S_ISSUER] is not coordinator._issuer:
        _fail("coordinator issuer binding is invalid")
    if (
        state[_S_CONFIG] != coordinator._config_sha256
        or state[_S_PROFILE] != coordinator._profile
    ):
        _fail("coordinator config binding is invalid")
    if state[_S_ALTERNATE] is not coordinator._alternate_payload:
        _fail("coordinator alternate binding is invalid")
    if (
        state[_S_ALTERNATE_BYTES] != alternate_bytes
        or state[_S_ALTERNATE_SHA] != alternate_sha
    ):
        _fail("coordinator alternate summary binding is invalid")

    snapshot = _snapshot_from_state(coordinator, state)
    lifecycle = snapshot.lifecycle_state
    active = state[_S_ACTIVE_EPOCH]
    terminal = state[_S_TERMINAL_EPOCH]
    witness = state[_S_WITNESS]
    if lifecycle == "RECOVERY_ACTIVE":
        if (
            type(active) is not SyntheticRecoveryEpochV10
            or active._issuer is not state[_S_ISSUER]
        ):
            _fail("coordinator active epoch identity is invalid")
        _validate_epoch_for_state(state, active)
    elif active is not None:
        _fail("coordinator active epoch lifecycle is invalid")
    if lifecycle.startswith("RECOVERED_") or lifecycle.startswith("BLOCKED_"):
        if (
            type(terminal) is not SyntheticRecoveryEpochV10
            or terminal._issuer is not state[_S_ISSUER]
        ):
            _fail("coordinator terminal epoch identity is invalid")
        _validate_epoch_for_state(state, terminal)
        if (
            type(witness) is not SyntheticRecoveryWitnessV10
            or witness._issuer is not state[_S_ISSUER]
        ):
            _fail("coordinator witness identity is invalid")
        _validate_witness_for_state(state, witness)
    elif terminal is not None or witness is not None:
        _fail("coordinator terminal handle lifecycle is invalid")
    _validate_private_replay_rows(state)


def _require_coordinator(value: object, /) -> SyntheticRecoveryCoordinatorV10:
    if type(value) is not SyntheticRecoveryCoordinatorV10:
        _fail("coordinator is not the exact public coordinator type")
    try:
        lock = value._lock
        issuer = value._issuer
        profile = value._profile
        alternate = value._alternate_payload
        config = value._config_sha256
        publishing = value._publishing_state
        poisoned = value._poisoned_state
        state = value._state
    except Exception:
        _fail("coordinator private slots are invalid")
    if type(lock) is not _LOCK_TYPE:
        _fail("coordinator Lock is invalid")
    if type(profile) is not str or profile not in _PROFILES:
        _fail("coordinator profile is invalid")
    if profile == "wrong_delta_confirmed":
        if type(alternate) is not bytes or len(alternate) > _MAX_PAYLOAD_BYTES:
            _fail("coordinator alternate payload is invalid")
    elif alternate is not None:
        _fail("coordinator alternate payload is invalid")
    _require_hash(config, "coordinator config")
    if type(publishing) is not tuple or len(publishing) != _STATE_LENGTH:
        _fail("coordinator publishing state is invalid")
    if profile == "wrong_delta_confirmed":
        alternate_bytes: int | None = _require_int(
            publishing[_S_ALTERNATE_BYTES],
            "coordinator alternate bytes",
        )
        if alternate_bytes != len(alternate):
            _fail("coordinator alternate byte count is invalid")
        alternate_sha: str | None = _require_hash(
            publishing[_S_ALTERNATE_SHA],
            "coordinator alternate hash",
        )
    else:
        alternate_bytes = None
        alternate_sha = None
    expected_publishing = _base_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        "PUBLISHING",
    )
    expected_poisoned = _base_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        "POISONED_NO_MARKER",
    )
    if publishing != expected_publishing or poisoned != expected_poisoned:
        _fail("coordinator prebuilt state is invalid")
    try:
        _validate_private_state(value, publishing, alternate_bytes, alternate_sha)
        _validate_private_state(value, poisoned, alternate_bytes, alternate_sha)
        _validate_private_state(value, state, alternate_bytes, alternate_sha)
    except SyntheticRecoveryCoordinatorV10Error:
        raise
    except Exception:
        _fail("coordinator private state fields are invalid")
    return value


def _make_epoch(
    issuer: object,
    config: str,
    marker_sha: str,
    ordinal: int,
    /,
) -> SyntheticRecoveryEpochV10:
    nonce = _epoch_nonce_sha256(config, marker_sha, ordinal)
    digest = _epoch_sha256(config, marker_sha, ordinal, nonce)
    epoch = SyntheticRecoveryEpochV10(_FACTORY_SENTINEL)
    object.__setattr__(epoch, "_issuer", issuer)
    object.__setattr__(epoch, "_epoch_ordinal", ordinal)
    object.__setattr__(epoch, "_epoch_nonce_sha256", nonce)
    object.__setattr__(epoch, "_epoch_sha256", digest)
    return epoch


def _make_witness(
    issuer: object,
    config: str,
    terminal: str,
    purpose: str,
    /,
) -> SyntheticRecoveryWitnessV10:
    nonce = _witness_nonce_sha256(config, terminal, purpose)
    digest = _witness_sha256(config, terminal, purpose, nonce)
    witness = SyntheticRecoveryWitnessV10(_FACTORY_SENTINEL)
    object.__setattr__(witness, "_issuer", issuer)
    object.__setattr__(witness, "_purpose", purpose)
    object.__setattr__(witness, "_terminal_sha256", terminal)
    object.__setattr__(witness, "_witness_nonce_sha256", nonce)
    object.__setattr__(witness, "_witness_sha256", digest)
    return witness


def _snapshot_from_state(
    coordinator: SyntheticRecoveryCoordinatorV10,
    state: tuple[object, ...],
    /,
) -> SyntheticRecoverySnapshotV10:
    lifecycle = state[_S_LIFECYCLE]
    profile = coordinator._profile
    if lifecycle == "OPEN":
        profile_status = "normal_no_fault_profile" if profile == "normal" else "armed"
    elif lifecycle == "PUBLISHING":
        profile_status = "owned_call_in_progress"
    elif lifecycle == "POISONED_NO_MARKER":
        profile_status = "spent_without_marker"
    else:
        profile_status = "spent_marker_committed"
    marker = state[_S_MARKER]
    active = state[_S_ACTIVE_EPOCH]
    terminal = state[_S_TERMINAL_EPOCH]
    witness = state[_S_WITNESS]
    values = (
        _SNAPSHOT_SCHEMA,
        _SNAPSHOT_SCOPE,
        _ORIGIN_STATUS,
        profile,
        profile_status,
        state[_S_ALTERNATE_BYTES],
        state[_S_ALTERNATE_SHA],
        coordinator._config_sha256,
        lifecycle,
        marker,
        0 if marker is None else 1,
        state[_S_ISSUE_COUNT],
        state[_S_REPLAY_COUNT],
        None if active is None else active.epoch_ordinal,
        None if active is None else active.epoch_nonce_sha256,
        None if terminal is None else terminal.epoch_ordinal,
        None if terminal is None else terminal.epoch_nonce_sha256,
        state[_S_WITNESS_STATUS],
        None if witness is None else witness.purpose,
        None if witness is None else witness.witness_nonce_sha256,
        state[_S_TERMINAL_KIND],
        state[_S_TERMINAL_REASON],
        state[_S_TERMINAL_SHA],
        "0" * 64,
        _MAX_MARKERS,
        _MAX_ACTIVE_EPOCHS,
        _MAX_RECOVERY_EPOCHS,
        _MAX_WITNESSES,
        _MAX_RETAINED_PAYLOAD_REFERENCES,
        _MAX_RETAINED_PAYLOAD_COPIES,
        _FIXED_PROFILE_SCOPE,
        _COORDINATOR_OWNERSHIP_SCOPE,
        _CONCURRENCY_SCOPE,
        _RAW_BYPASS_SCOPE,
        _COLLISION_NONCE_SCOPE,
        _REPLAY_SCOPE,
        _WITNESS_SCOPE,
        _DETACHED_RECORD_SCOPE,
        _TAMPER_SCOPE,
        _PRE_MARKER_ERROR_SCOPE,
        _STAGE_RESIDUE_SCOPE,
        _CLEANUP_SCOPE,
        _JOURNAL_SCOPE,
        _PROCESS_RESTART_SCOPE,
        _MANIFEST_SCOPE,
        _REMOTE_PUBLICATION,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )
    unchecked = _unchecked_record(SyntheticRecoverySnapshotV10, values)
    digest = _snapshot_sha256(unchecked)
    final_values = values[:23] + (digest,) + values[24:]
    return SyntheticRecoverySnapshotV10(*final_values)


def _make_action(
    coordinator: SyntheticRecoveryCoordinatorV10,
    operation: str,
    outcome: str,
    reason: str,
    before: SyntheticRecoverySnapshotV10,
    after_state: tuple[object, ...],
    publish_result: LocalStagingFakePublishResultV10 | None,
    issued_epoch: SyntheticRecoveryEpochV10 | None,
    issued_witness: SyntheticRecoveryWitnessV10 | None,
    epoch_ordinal: int | None,
    replay_observation: str | None,
    /,
) -> SyntheticRecoveryActionV10:
    after = _snapshot_from_state(coordinator, after_state)
    values = (
        _ACTION_SCHEMA,
        _ACTION_SCOPE,
        _ORIGIN_STATUS,
        operation,
        outcome,
        (reason,),
        before.snapshot_sha256,
        after,
        before.snapshot_sha256 != after.snapshot_sha256,
        publish_result,
        after.marker,
        issued_epoch,
        issued_witness,
        after.terminal_sha256,
        epoch_ordinal,
        replay_observation,
        "0" * 64,
        _EXCLUSION_SCOPE,
        _ACTION_RECORD_SCOPE,
        _OPAQUE_HANDLE_SCOPE,
        _HASH_AUTHORITY_SCOPE,
        _CLEANUP_SCOPE,
        _STAGE_RESIDUE_SCOPE,
        _JOURNAL_SCOPE,
        _PROCESS_RESTART_SCOPE,
        _REMOTE_REOBSERVATION_SCOPE,
        _MANIFEST_SCOPE,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )
    unchecked = _unchecked_record(_ACTION_RECORD_TYPE, values)
    digest = _action_sha256(unchecked)
    final_values = values[:16] + (digest,) + values[17:]
    return SyntheticRecoveryActionV10(*final_values)


def _snapshot_input_state(value: object, /) -> InMemoryFakeCasStateV10:
    if type(value) is not InMemoryFakeCasStateV10:
        raise InMemoryFakeCasV10Error("state is not the exact public State type") from None
    try:
        values = tuple(getattr(value, name) for name in InMemoryFakeCasStateV10.__slots__)
        return InMemoryFakeCasStateV10(*values)
    except InMemoryFakeCasV10Error:
        raise
    except Exception:
        raise InMemoryFakeCasV10Error("state fields are invalid") from None


def _snapshot_publish_result(value: object, /) -> LocalStagingFakePublishResultV10:
    if type(value) is not LocalStagingFakePublishResultV10:
        _fail("Phase-2b2d returned an invalid Result type")
    try:
        values = tuple(
            getattr(value, name) for name in LocalStagingFakePublishResultV10.__slots__
        )
        return LocalStagingFakePublishResultV10(*values)
    except LocalStagingFakePublisherV10Error:
        _fail("Phase-2b2d Result reconstruction failed")
    except Exception:
        _fail("Phase-2b2d Result fields are invalid")


def _derive_publish_plan(
    state: InMemoryFakeCasStateV10,
    expected: str,
    proposal: bytes,
    profile: str,
    alternate: bytes | None,
    /,
) -> tuple[
    InMemoryFakeCasTransitionV10,
    tuple[tuple[str, InMemoryFakeCasTransitionV10], ...],
]:
    normal = step_in_memory_fake_cas_v1_0(
        state,
        expected,
        proposal,
        "apply_intended_acknowledge",
        None,
    )
    if normal.outcome in ("conflict_no_change", "existing_identical_no_change"):
        return normal, ()
    if normal.outcome != "intended_applied_acknowledged":
        _fail("normal preclassification row is invalid")
    if profile == "normal":
        return normal, ()
    if profile == "ack_loss_confirmed":
        confirmed = step_in_memory_fake_cas_v1_0(
            state,
            expected,
            proposal,
            "apply_intended_lose_ack_then_confirm",
            None,
        )
        return normal, (("confirmed_intended", confirmed),)
    if profile == "ack_loss_unavailable_then_confirmed":
        unavailable = step_in_memory_fake_cas_v1_0(
            state,
            expected,
            proposal,
            "apply_intended_lose_ack_confirmation_unavailable",
            None,
        )
        confirmed = step_in_memory_fake_cas_v1_0(
            state,
            expected,
            proposal,
            "apply_intended_lose_ack_then_confirm",
            None,
        )
        return normal, (
            ("unavailable", unavailable),
            ("confirmed_intended", confirmed),
        )
    if profile == "ack_loss_unavailable_until_budget_block":
        unavailable = step_in_memory_fake_cas_v1_0(
            state,
            expected,
            proposal,
            "apply_intended_lose_ack_confirmation_unavailable",
            None,
        )
        return normal, (
            ("unavailable", unavailable),
            ("unavailable", unavailable),
            ("unavailable", unavailable),
            ("unavailable", unavailable),
        )
    wrong = step_in_memory_fake_cas_v1_0(
        state,
        expected,
        proposal,
        "substitute_alternate_then_confirm_wrong_delta",
        alternate,
    )
    return normal, (("confirmed_wrong_delta", wrong),)


def _make_marker(
    coordinator: SyntheticRecoveryCoordinatorV10,
    result: LocalStagingFakePublishResultV10,
    rows: tuple[tuple[str, InMemoryFakeCasTransitionV10], ...],
    /,
) -> SyntheticRecoveryMarkerV10:
    profile = coordinator._profile
    if not rows:
        _fail("marker replay plan is empty")
    fault = rows[0][1]
    if profile == "ack_loss_confirmed":
        marker_kind = "synthetic_ack_loss_confirmed"
    elif profile in (
        "ack_loss_unavailable_then_confirmed",
        "ack_loss_unavailable_until_budget_block",
    ):
        marker_kind = "synthetic_ack_loss_unavailable"
    elif profile == "wrong_delta_confirmed":
        marker_kind = "synthetic_wrong_delta_confirmed"
    else:
        _fail("normal profile cannot create a marker")
    transition = result.cas_transition
    intended_after = transition.intended_after_state_version_sha256
    intended_delta = transition.intended_delta_sha256
    actual_delta = fault.actual_delta_sha256
    if intended_after is None or intended_delta is None or actual_delta is None:
        _fail("changed transition digests are missing")
    stage_bytes = result.stage_payload_bytes
    stage_sha = result.stage_payload_sha256
    if stage_bytes is None or stage_sha is None:
        _fail("changed publisher stage cells are missing")
    values = (
        _MARKER_SCHEMA,
        _MARKER_SCOPE,
        _ORIGIN_STATUS,
        profile,
        coordinator._config_sha256,
        marker_kind,
        1,
        ("OTHER_HARNESS_ERROR",),
        result.outcome,
        result.operation_sha256,
        transition.transition_sha256,
        fault.outcome,
        fault.transition_sha256,
        _plan_sha256(profile, rows),
        len(rows),
        transition.before_state.state_version_sha256,
        intended_after,
        fault.after_state.state_version_sha256,
        intended_delta,
        actual_delta,
        stage_bytes,
        stage_sha,
        "0" * 64,
        _CALLER_PROFILE_SCOPE,
        _CAUSE_SCOPE,
        _JOURNAL_SCOPE,
        _STAGE_BINDING_SCOPE,
        _FAILURE_CODE_SCOPE,
        _CLEANUP_SCOPE,
        _MARKER_PROVENANCE,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )
    unchecked = _unchecked_record(SyntheticRecoveryMarkerV10, values)
    digest = _marker_sha256(unchecked)
    return SyntheticRecoveryMarkerV10(*(values[:22] + (digest,) + values[23:]))


def _pending_state(
    state: tuple[object, ...],
    replay_count: int,
    /,
) -> tuple[object, ...]:
    return _new_state_tuple(
        state[_S_ISSUER],
        state[_S_CONFIG],
        state[_S_PROFILE],
        state[_S_ALTERNATE],
        state[_S_ALTERNATE_BYTES],
        state[_S_ALTERNATE_SHA],
        "RECOVERY_PENDING",
        state[_S_MARKER],
        state[_S_ISSUE_COUNT],
        replay_count,
        None,
        None,
        None,
        None,
        None,
        None,
        "none",
        state[_S_REPLAY_ROWS],
    )


def _terminal_state(
    state: tuple[object, ...],
    epoch: SyntheticRecoveryEpochV10,
    replay_count: int,
    kind: str,
    reason: str,
    /,
) -> tuple[tuple[object, ...], SyntheticRecoveryWitnessV10]:
    marker = state[_S_MARKER]
    if type(marker) is not SyntheticRecoveryMarkerV10:
        _fail("terminal transition requires a marker")
    purpose = (
        "record_recovered_terminal"
        if kind == "recovered_terminal"
        else "record_permanent_block"
    )
    terminal = _terminal_sha256(
        state[_S_CONFIG],
        marker.marker_sha256,
        kind,
        reason,
        epoch.epoch_ordinal,
        epoch.epoch_nonce_sha256,
        state[_S_ISSUE_COUNT],
        replay_count,
    )
    witness = _make_witness(state[_S_ISSUER], state[_S_CONFIG], terminal, purpose)
    lifecycle = (
        "RECOVERED_WITNESS_LIVE"
        if kind == "recovered_terminal"
        else "BLOCKED_WITNESS_LIVE"
    )
    terminal_state = _new_state_tuple(
        state[_S_ISSUER],
        state[_S_CONFIG],
        state[_S_PROFILE],
        state[_S_ALTERNATE],
        state[_S_ALTERNATE_BYTES],
        state[_S_ALTERNATE_SHA],
        lifecycle,
        marker,
        state[_S_ISSUE_COUNT],
        replay_count,
        None,
        epoch,
        kind,
        reason,
        terminal,
        witness,
        "live",
        (),
    )
    return terminal_state, witness


def _require_outer_epoch(value: object, /) -> SyntheticRecoveryEpochV10:
    if type(value) is not SyntheticRecoveryEpochV10:
        _fail("epoch is not the exact public epoch type")
    return value


def _require_outer_witness(value: object, /) -> SyntheticRecoveryWitnessV10:
    if type(value) is not SyntheticRecoveryWitnessV10:
        _fail("witness is not the exact public witness type")
    return value


def _require_active_epoch(
    state: tuple[object, ...],
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> None:
    if state[_S_ACTIVE_EPOCH] is not epoch or epoch._issuer is not state[_S_ISSUER]:
        _fail("epoch is not the exact active coordinator epoch")
    _validate_epoch_for_state(state, epoch)


def _validate_epoch_for_state(
    state: tuple[object, ...],
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> None:
    marker = state[_S_MARKER]
    if type(marker) is not SyntheticRecoveryMarkerV10:
        _fail("epoch state marker is invalid")
    ordinal = _require_int(epoch._epoch_ordinal, "epoch ordinal")
    nonce = _require_hash(epoch._epoch_nonce_sha256, "epoch nonce")
    digest = _require_hash(epoch._epoch_sha256, "epoch hash")
    if ordinal != state[_S_ISSUE_COUNT]:
        _fail("epoch ordinal is not current")
    if nonce != _epoch_nonce_sha256(state[_S_CONFIG], marker.marker_sha256, ordinal):
        _fail("epoch nonce is invalid")
    if digest != _epoch_sha256(
        state[_S_CONFIG], marker.marker_sha256, ordinal, nonce
    ):
        _fail("epoch hash is invalid")


def _validate_witness_for_state(
    state: tuple[object, ...],
    witness: SyntheticRecoveryWitnessV10,
    /,
) -> None:
    purpose = _require_str(witness._purpose, "witness purpose")
    terminal = _require_hash(witness._terminal_sha256, "witness terminal")
    nonce = _require_hash(witness._witness_nonce_sha256, "witness nonce")
    digest = _require_hash(witness._witness_sha256, "witness hash")
    if purpose != (
        "record_recovered_terminal"
        if state[_S_TERMINAL_KIND] == "recovered_terminal"
        else "record_permanent_block"
    ) or terminal != state[_S_TERMINAL_SHA]:
        _fail("witness terminal binding is invalid")
    if nonce != _witness_nonce_sha256(state[_S_CONFIG], terminal, purpose):
        _fail("witness nonce is invalid")
    if digest != _witness_sha256(state[_S_CONFIG], terminal, purpose, nonce):
        _fail("witness hash is invalid")


def _same_transition(
    left: InMemoryFakeCasTransitionV10,
    right: InMemoryFakeCasTransitionV10,
    /,
) -> bool:
    return type(right) is InMemoryFakeCasTransitionV10 and left == right


def new_synthetic_recovery_coordinator_v1_0(
    constructor_profile: str,
    alternate_payload: bytes | None,
    /,
) -> SyntheticRecoveryCoordinatorV10:
    profile = _require_str(constructor_profile, "constructor_profile")
    if profile not in _PROFILES:
        _fail("constructor_profile is invalid")
    if profile == "wrong_delta_confirmed":
        alternate = _require_bytes(alternate_payload, "alternate_payload")
        if len(alternate) > _MAX_PAYLOAD_BYTES:
            _fail("alternate_payload exceeds the byte limit")
        alternate_bytes: int | None = len(alternate)
        alternate_sha: str | None = _raw_sha256(alternate)
    else:
        if alternate_payload is not None:
            _fail("alternate_payload must be null for this profile")
        alternate = None
        alternate_bytes = None
        alternate_sha = None
    config = _config_sha256(profile, alternate)
    issuer = object()
    coordinator = SyntheticRecoveryCoordinatorV10(_FACTORY_SENTINEL)
    object.__setattr__(coordinator, "_lock", threading.Lock())
    object.__setattr__(coordinator, "_issuer", issuer)
    object.__setattr__(coordinator, "_profile", profile)
    object.__setattr__(coordinator, "_alternate_payload", alternate)
    object.__setattr__(coordinator, "_config_sha256", config)
    publishing = _base_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        "PUBLISHING",
    )
    poisoned = _base_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        "POISONED_NO_MARKER",
    )
    opened = _base_state_tuple(
        issuer,
        config,
        profile,
        alternate,
        alternate_bytes,
        alternate_sha,
        "OPEN",
    )
    object.__setattr__(coordinator, "_publishing_state", publishing)
    object.__setattr__(coordinator, "_poisoned_state", poisoned)
    object.__setattr__(coordinator, "_state", opened)
    return coordinator


def snapshot_synthetic_recovery_coordinator_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    /,
) -> SyntheticRecoverySnapshotV10:
    owned = _require_coordinator(coordinator)
    with owned._lock:
        _require_coordinator(owned)
        return _snapshot_from_state(owned, owned._state)


def publish_with_synthetic_recovery_coordinator_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    staging_parent: str,
    collision_nonce: str,
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    with owned._lock:
        _require_coordinator(owned)
        old_state = owned._state
        before = _snapshot_from_state(owned, old_state)
        if old_state[_S_LIFECYCLE] != "OPEN":
            return _make_action(
                owned,
                "publish",
                "publisher_excluded_non_open",
                "coordinator_not_open",
                before,
                old_state,
                None,
                None,
                None,
                None,
                None,
            )
        owned._state = owned._publishing_state

    changed_call_started = False
    valid_result_changed = False
    valid_result_returned = False
    result_rows_agree = False
    exact_changed_result = False
    committed = False
    action: SyntheticRecoveryActionV10 | None = None
    primary: BaseException | None = None
    try:
        private_state = _snapshot_input_state(state)
        normal, rows = _derive_publish_plan(
            private_state,
            expected_state_version_sha256,
            proposed_payload,
            owned._profile,
            owned._alternate_payload,
        )
        normal_changed = normal.outcome == "intended_applied_acknowledged"
        changed_call_started = normal_changed
        returned = stage_and_fake_publish_normal_v1_0(
            staging_parent,
            collision_nonce,
            private_state,
            expected_state_version_sha256,
            proposed_payload,
        )
        result = _snapshot_publish_result(returned)
        valid_result_returned = True
        valid_result_changed = result.outcome == (
            "staged_intended_fake_publish_acknowledged"
        )
        if normal.outcome == "conflict_no_change":
            expected_result_outcome = "cas_conflict_no_stage"
        elif normal.outcome == "existing_identical_no_change":
            expected_result_outcome = "cas_existing_identical_no_stage"
        else:
            expected_result_outcome = "staged_intended_fake_publish_acknowledged"
        if (
            result.outcome != expected_result_outcome
            or not _same_transition(normal, result.cas_transition)
        ):
            _fail("preclassification and exact Result disagree")
        result_rows_agree = True
        if normal_changed:
            exact_changed_result = True
            if owned._profile == "normal":
                prospective = old_state
                action = _make_action(
                    owned,
                    "publish",
                    "normal_staged_result_exposed_no_marker",
                    "exact_stage_retained_before_exposing_synthetic_acknowledged_transition",
                    before,
                    prospective,
                    result,
                    None,
                    None,
                    None,
                    None,
                )
            else:
                marker = _make_marker(owned, result, rows)
                prospective = _new_state_tuple(
                    old_state[_S_ISSUER],
                    old_state[_S_CONFIG],
                    old_state[_S_PROFILE],
                    old_state[_S_ALTERNATE],
                    old_state[_S_ALTERNATE_BYTES],
                    old_state[_S_ALTERNATE_SHA],
                    "RECOVERY_PENDING",
                    marker,
                    0,
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "none",
                    rows,
                )
                action = _make_action(
                    owned,
                    "publish",
                    "synthetic_marker_committed_result_withheld",
                    "synthetic_marker_committed",
                    before,
                    prospective,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
        elif normal.outcome == "conflict_no_change":
            prospective = old_state
            action = _make_action(
                owned,
                "publish",
                "cas_conflict_no_marker",
                "expected_state_version_mismatch",
                before,
                prospective,
                result,
                None,
                None,
                None,
                None,
            )
        else:
            prospective = old_state
            action = _make_action(
                owned,
                "publish",
                "cas_existing_identical_no_marker",
                "exact_payload_already_current",
                before,
                prospective,
                result,
                None,
                None,
                None,
                None,
            )
        with owned._lock:
            if owned._state is not owned._publishing_state:
                _fail("owned publishing state was replaced")
            owned._state = prospective
            committed = True
    except BaseException as error:
        primary = error
    finally:
        if not committed:
            owned._lock.acquire()
            try:
                owned._state = (
                    owned._poisoned_state
                    if (
                        changed_call_started
                        or valid_result_changed
                        or (valid_result_returned and not result_rows_agree)
                    )
                    else old_state
                )
            finally:
                owned._lock.release()
    if primary is not None:
        if type(primary) is SyntheticRecoveryCoordinatorV10Error:
            raise primary
        if isinstance(primary, Exception):
            if exact_changed_result:
                _fail("owned publish endpoint failed after exact changed result")
            if changed_call_started or valid_result_changed:
                _fail("owned changed publish failed without exact changed endpoint")
            _fail("owned publish failed before changed call")
        raise primary
    if action is None:
        _fail("owned publish endpoint is missing")
    return action


def acquire_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    with owned._lock:
        _require_coordinator(owned)
        state = owned._state
        before = _snapshot_from_state(owned, state)
        lifecycle = state[_S_LIFECYCLE]
        if lifecycle == "RECOVERY_PENDING":
            marker = state[_S_MARKER]
            if type(marker) is not SyntheticRecoveryMarkerV10:
                _fail("pending marker is invalid")
            ordinal = state[_S_ISSUE_COUNT] + 1
            if ordinal > _MAX_RECOVERY_EPOCHS:
                _fail("recovery epoch budget is exhausted")
            epoch = _make_epoch(
                state[_S_ISSUER],
                state[_S_CONFIG],
                marker.marker_sha256,
                ordinal,
            )
            prospective = _new_state_tuple(
                state[_S_ISSUER],
                state[_S_CONFIG],
                state[_S_PROFILE],
                state[_S_ALTERNATE],
                state[_S_ALTERNATE_BYTES],
                state[_S_ALTERNATE_SHA],
                "RECOVERY_ACTIVE",
                marker,
                ordinal,
                state[_S_REPLAY_COUNT],
                epoch,
                None,
                None,
                None,
                None,
                None,
                "none",
                state[_S_REPLAY_ROWS],
            )
            action = _make_action(
                owned,
                "acquire_epoch",
                "epoch_issued",
                "recovery_marker_pending",
                before,
                prospective,
                None,
                epoch,
                None,
                ordinal,
                None,
            )
            owned._state = prospective
            return action
        if lifecycle == "OPEN":
            outcome, reason = "no_marker_noop", "marker_absent"
        elif lifecycle == "PUBLISHING":
            outcome, reason = "publisher_active_excluded", "owned_publisher_active"
        elif lifecycle == "RECOVERY_ACTIVE":
            outcome, reason = "recovery_active_excluded", "active_epoch_exists"
        elif lifecycle.startswith("RECOVERED_"):
            outcome, reason = "recovered_terminal_noop", "recovered_terminal"
        elif lifecycle.startswith("BLOCKED_"):
            outcome, reason = "blocked_terminal_noop", "permanent_block"
        elif lifecycle == "POISONED_NO_MARKER":
            outcome, reason = "poisoned_no_marker_noop", "poisoned_no_marker"
        else:
            _fail("acquire lifecycle is invalid")
        return _make_action(
            owned,
            "acquire_epoch",
            outcome,
            reason,
            before,
            state,
            None,
            None,
            None,
            None,
            None,
        )


def release_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    handle = _require_outer_epoch(epoch)
    with owned._lock:
        _require_coordinator(owned)
        state = owned._state
        before = _snapshot_from_state(owned, state)
        if state[_S_LIFECYCLE] == "PUBLISHING":
            return _make_action(
                owned,
                "release_epoch",
                "publisher_active_excluded",
                "owned_publisher_active",
                before,
                state,
                None,
                None,
                None,
                None,
                None,
            )
        if state[_S_LIFECYCLE] != "RECOVERY_ACTIVE":
            _fail("release is not eligible in this lifecycle")
        _require_active_epoch(state, handle)
        ordinal = handle.epoch_ordinal
        if ordinal < _MAX_RECOVERY_EPOCHS:
            prospective = _pending_state(state, state[_S_REPLAY_COUNT])
            outcome = "epoch_released_retry_pending"
            reason = "epoch_released_replay_cursor_unchanged"
            witness = None
        else:
            prospective, witness = _terminal_state(
                state,
                handle,
                state[_S_REPLAY_COUNT],
                "permanent_block",
                "recovery_epoch_budget_exhausted_after_release",
            )
            outcome = "epoch_release_budget_permanent_block"
            reason = "recovery_epoch_budget_exhausted_after_release"
        action = _make_action(
            owned,
            "release_epoch",
            outcome,
            reason,
            before,
            prospective,
            None,
            None,
            witness,
            ordinal,
            None,
        )
        owned._state = prospective
        return action


def abandon_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    handle = _require_outer_epoch(epoch)
    with owned._lock:
        _require_coordinator(owned)
        state = owned._state
        before = _snapshot_from_state(owned, state)
        if state[_S_LIFECYCLE] == "PUBLISHING":
            return _make_action(
                owned,
                "abandon_epoch",
                "publisher_active_excluded",
                "owned_publisher_active",
                before,
                state,
                None,
                None,
                None,
                None,
                None,
            )
        if state[_S_LIFECYCLE] != "RECOVERY_ACTIVE":
            _fail("abandon is not eligible in this lifecycle")
        _require_active_epoch(state, handle)
        ordinal = handle.epoch_ordinal
        if ordinal < _MAX_RECOVERY_EPOCHS:
            prospective = _pending_state(state, state[_S_REPLAY_COUNT])
            outcome = "epoch_abandoned_retry_pending"
            reason = "epoch_abandoned_replay_cursor_unchanged"
            witness = None
        else:
            prospective, witness = _terminal_state(
                state,
                handle,
                state[_S_REPLAY_COUNT],
                "permanent_block",
                "recovery_epoch_budget_exhausted_after_abandon",
            )
            outcome = "epoch_abandon_budget_permanent_block"
            reason = "recovery_epoch_budget_exhausted_after_abandon"
        action = _make_action(
            owned,
            "abandon_epoch",
            outcome,
            reason,
            before,
            prospective,
            None,
            None,
            witness,
            ordinal,
            None,
        )
        owned._state = prospective
        return action


def replay_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    handle = _require_outer_epoch(epoch)
    with owned._lock:
        _require_coordinator(owned)
        state = owned._state
        before = _snapshot_from_state(owned, state)
        lifecycle = state[_S_LIFECYCLE]
        if lifecycle == "PUBLISHING":
            return _make_action(
                owned,
                "replay_epoch",
                "publisher_active_excluded",
                "owned_publisher_active",
                before,
                state,
                None,
                None,
                None,
                None,
                None,
            )
        if lifecycle.startswith("RECOVERED_") or lifecycle.startswith("BLOCKED_"):
            if state[_S_TERMINAL_EPOCH] is not handle or handle._issuer is not state[_S_ISSUER]:
                _fail("epoch is not the exact terminal coordinator epoch")
            _validate_epoch_for_state(state, handle)
            recovered = lifecycle.startswith("RECOVERED_")
            return _make_action(
                owned,
                "replay_epoch",
                "recovered_terminal_noop" if recovered else "blocked_terminal_noop",
                "recovered_terminal" if recovered else "permanent_block",
                before,
                state,
                None,
                None,
                None,
                handle.epoch_ordinal,
                "terminal_noop",
            )
        if lifecycle != "RECOVERY_ACTIVE":
            _fail("replay is not eligible in this lifecycle")
        _require_active_epoch(state, handle)
        rows = state[_S_REPLAY_ROWS]
        cursor = state[_S_REPLAY_COUNT]
        if type(rows) is not tuple or cursor >= len(rows):
            _fail("replay plan cursor is invalid")
        observation, transition = rows[cursor]
        if type(transition) is not InMemoryFakeCasTransitionV10:
            _fail("replay transition is invalid")
        replay_count = cursor + 1
        ordinal = handle.epoch_ordinal
        if observation == "unavailable":
            if ordinal < _MAX_RECOVERY_EPOCHS:
                prospective = _pending_state(state, replay_count)
                outcome = "replay_unavailable_retry_pending"
                reason = "same_kernel_replay_unavailable"
                witness = None
            else:
                prospective, witness = _terminal_state(
                    state,
                    handle,
                    replay_count,
                    "permanent_block",
                    "recovery_epoch_budget_exhausted_after_unavailable",
                )
                outcome = "replay_unavailable_budget_permanent_block"
                reason = "recovery_epoch_budget_exhausted_after_unavailable"
        elif observation == "confirmed_intended":
            prospective, witness = _terminal_state(
                state,
                handle,
                replay_count,
                "recovered_terminal",
                "synthetic_intended_transition_confirmed",
            )
            outcome = "replay_confirmed_recovered"
            reason = "synthetic_intended_transition_confirmed"
        elif observation == "confirmed_wrong_delta":
            prospective, witness = _terminal_state(
                state,
                handle,
                replay_count,
                "permanent_block",
                "synthetic_wrong_delta_confirmed",
            )
            outcome = "replay_wrong_delta_permanent_block"
            reason = "synthetic_wrong_delta_confirmed"
        else:
            _fail("replay observation is invalid")
        action = _make_action(
            owned,
            "replay_epoch",
            outcome,
            reason,
            before,
            prospective,
            None,
            None,
            witness,
            ordinal,
            observation,
        )
        owned._state = prospective
        return action


def consume_synthetic_recovery_witness_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    witness: SyntheticRecoveryWitnessV10,
    expected_purpose: str,
    expected_terminal_sha256: str,
    /,
) -> SyntheticRecoveryActionV10:
    owned = _require_coordinator(coordinator)
    handle = _require_outer_witness(witness)
    with owned._lock:
        _require_coordinator(owned)
        state = owned._state
        before = _snapshot_from_state(owned, state)
        lifecycle = state[_S_LIFECYCLE]
        if lifecycle == "PUBLISHING":
            return _make_action(
                owned,
                "consume_witness",
                "publisher_active_excluded",
                "owned_publisher_active",
                before,
                state,
                None,
                None,
                None,
                None,
                None,
            )
        if not (lifecycle.startswith("RECOVERED_") or lifecycle.startswith("BLOCKED_")):
            _fail("witness consumption is not eligible in this lifecycle")
        if state[_S_WITNESS] is not handle or handle._issuer is not state[_S_ISSUER]:
            _fail("witness is not the exact retained coordinator witness")
        _validate_witness_for_state(state, handle)
        purpose = _require_str(expected_purpose, "expected_purpose")
        if purpose != handle.purpose:
            _fail("expected_purpose does not match the retained witness")
        terminal = _require_hash(
            expected_terminal_sha256,
            "expected_terminal_sha256",
        )
        if terminal != handle.terminal_sha256:
            _fail("expected_terminal_sha256 does not match the retained witness")
        terminal_epoch = state[_S_TERMINAL_EPOCH]
        if type(terminal_epoch) is not SyntheticRecoveryEpochV10:
            _fail("terminal epoch is invalid")
        if lifecycle.endswith("_LIVE"):
            prospective = _new_state_tuple(
                state[_S_ISSUER],
                state[_S_CONFIG],
                state[_S_PROFILE],
                state[_S_ALTERNATE],
                state[_S_ALTERNATE_BYTES],
                state[_S_ALTERNATE_SHA],
                (
                    "RECOVERED_WITNESS_SPENT"
                    if lifecycle == "RECOVERED_WITNESS_LIVE"
                    else "BLOCKED_WITNESS_SPENT"
                ),
                state[_S_MARKER],
                state[_S_ISSUE_COUNT],
                state[_S_REPLAY_COUNT],
                None,
                terminal_epoch,
                state[_S_TERMINAL_KIND],
                state[_S_TERMINAL_REASON],
                state[_S_TERMINAL_SHA],
                handle,
                "spent",
                (),
            )
            outcome = "witness_consumed"
            reason = "witness_consumed"
        else:
            prospective = state
            outcome = "witness_already_spent_noop"
            reason = "witness_already_spent"
        action = _make_action(
            owned,
            "consume_witness",
            outcome,
            reason,
            before,
            prospective,
            None,
            None,
            None,
            terminal_epoch.epoch_ordinal,
            None,
        )
        owned._state = prospective
        return action
