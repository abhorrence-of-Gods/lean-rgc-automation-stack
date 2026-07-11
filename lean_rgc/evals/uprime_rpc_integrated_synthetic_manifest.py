"""Bounded same-call synthetic manifest/recovery integration audit.

The returned records are deterministic, forgeable value projections.  This
module deliberately provides no durable, remote, execution, publication, or
real-recovery authority.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_attempt_manifest import (
    AttemptManifestV10Error,
    PublicClaimReceiptV10,
    AttemptManifestEventV10,
    AttemptManifestEventFileV10,
    AttemptManifestChainInspectionV10,
    AttemptManifestChainAttestationV10,
    encode_attempt_manifest_event_v1_0,
    parse_attempt_manifest_event_file_v1_0,
    inspect_local_attempt_manifest_chain_v1_0,
    verify_local_attempt_manifest_terminal_chain_v1_0,
)
from lean_rgc.evals.uprime_rpc_seed_inventory import (
    SyntheticSeedInventoryV10Error,
    SyntheticClaimSeedV10,
    SyntheticLocalClaimAuditV10,
    SyntheticSeedLocalInventoryAuditV10,
    parse_synthetic_claim_seed_v1_0,
    audit_synthetic_seed_local_inventory_v1_0,
)
from lean_rgc.evals.uprime_rpc_local_artifact_observer import (
    LocalArtifactObservationV10Error,
    LocalArtifactObservationV10,
    LocalArtifactSetObservationV10,
    observe_local_rpc_artifact_set_v1_0,
)
from lean_rgc.evals.uprime_rpc_fake_cas_kernel import (
    InMemoryFakeCasV10Error,
    InMemoryFakeCasStateV10,
    InMemoryFakeCasTransitionV10,
    initial_in_memory_fake_cas_state_v1_0,
)
from lean_rgc.evals.uprime_rpc_local_staging_fake_publisher import (
    LocalStagingFakePublishResultV10,
)
from lean_rgc.evals.uprime_rpc_synthetic_recovery_coordinator import (
    SyntheticRecoveryCoordinatorV10Error,
    SyntheticRecoveryMarkerV10,
    SyntheticRecoverySnapshotV10,
    SyntheticRecoveryActionV10,
    SyntheticRecoveryEpochV10,
    SyntheticRecoveryWitnessV10,
    SyntheticRecoveryCoordinatorV10,
    new_synthetic_recovery_coordinator_v1_0,
    snapshot_synthetic_recovery_coordinator_v1_0,
    publish_with_synthetic_recovery_coordinator_v1_0,
    acquire_synthetic_recovery_epoch_v1_0,
    replay_synthetic_recovery_epoch_v1_0,
    consume_synthetic_recovery_witness_v1_0,
)


__all__ = [
    "IntegratedSyntheticManifestV10Error",
    "SyntheticManifestResidueObservationV10",
    "SyntheticCoordinatorActionTraceV10",
    "SyntheticTerminalManifestAppendV10",
    "SyntheticConflictWithoutMarkerAuditV10",
    "IntegratedSyntheticRecoveryManifestAuditV10",
    "audit_synthetic_conflict_without_marker_v1_0",
    "append_integrated_synthetic_recovery_manifest_v1_0",
]


# Public dependency bindings are deliberately injectable without importing a
# dependency's private implementation surface.
_dep_parse_seed = parse_synthetic_claim_seed_v1_0
_dep_audit_inventory = audit_synthetic_seed_local_inventory_v1_0
_dep_inspect_chain = inspect_local_attempt_manifest_chain_v1_0
_dep_verify_terminal = verify_local_attempt_manifest_terminal_chain_v1_0
_dep_observe_artifacts = observe_local_rpc_artifact_set_v1_0
_dep_initial_state = initial_in_memory_fake_cas_state_v1_0
_dep_new_coordinator = new_synthetic_recovery_coordinator_v1_0
_dep_snapshot_coordinator = snapshot_synthetic_recovery_coordinator_v1_0
_dep_publish_coordinator = publish_with_synthetic_recovery_coordinator_v1_0
_dep_acquire_epoch = acquire_synthetic_recovery_epoch_v1_0
_dep_replay_epoch = replay_synthetic_recovery_epoch_v1_0
_dep_consume_witness = consume_synthetic_recovery_witness_v1_0
_dep_encode_event = encode_attempt_manifest_event_v1_0
_dep_parse_event_file = parse_attempt_manifest_event_file_v1_0

_os_stat = os.stat
_os_open = os.open
_os_fstat = os.fstat
_os_lseek = os.lseek
_os_read = os.read
_os_write = os.write
_os_close = os.close
_os_link = os.link
_os_path_join = os.path.join
_os_path_normpath = os.path.normpath
_os_path_isabs = os.path.isabs
_os_path_splitdrive = os.path.splitdrive


_OBSERVATION_SCHEMA = "lean-rgc-uprime-u1-synthetic-manifest-residue-observation-v1.0"
_OBSERVATION_SCOPE = "one_sequential_bounded_final_component_stage_observation"
_TRACE_SCHEMA = "lean-rgc-uprime-u1-integrated-coordinator-action-trace-v1.0"
_TRACE_SCOPE = "scalar_projection_of_one_internally_obtained_phase2b2e_action"
_APPEND_SCHEMA = "lean-rgc-uprime-u1-synthetic-terminal-manifest-append-v1.0"
_APPEND_SCOPE = "one_exclusive_temp_verified_local_hardlink_materialization"
_CONFLICT_SCHEMA = "lean-rgc-uprime-u1-synthetic-conflict-without-marker-audit-v1.0"
_CONFLICT_SCOPE = "one_internal_absent_g0_stale_expected_no_manifest_call"
_RECOVERY_SCHEMA = "lean-rgc-uprime-u1-integrated-synthetic-recovery-manifest-audit-v1.0"
_RECOVERY_SCOPE = "one_same_call_sequential_synthetic_terminal_append_and_consume"
_ORIGIN_STATUS = "unknown_may_be_synthetic"
_AUTHORITY_SCOPE = "none"

_PATH_DERIVATION_SCOPE = "lexical_native_join_from_one_retained_root_no_resolution"
_NOFOLLOW_SCOPE = "final_component_checks_and_descriptor_binding_platform_dependent"
_ANCESTOR_REPARSE_SCOPE = "not_performed"
_BACKING_STORE_SCOPE = "unauthenticated_may_be_remote_virtual_or_overlay"
_SNAPSHOT_SCOPE = "sequential_endpoint_not_atomic_or_current_after_return"
_STAGE_ATTRIBUTION_SCOPE = "expected_path_and_bytes_relation_not_origin_or_ownership"
_CLEANUP_SCOPE = "no_unlink_rename_replace_or_residue_cleanup"
_DETACHED_SCOPE = "forgeable_value_projection_not_capability_or_io_attestation"
_SAME_CALL_SCOPE = "same_live_call_sequential_transcript_only"
_PERSISTENT_BINDING = "not_encoded_in_phase2b1_event"
_MANIFEST_WITNESS_ATOMICITY = "not_provided_two_ordered_endpoints"
_ARTIFACT_SCOPE = "three_sequential_rows_only_not_atomic_bundle_or_content_validation"
_INVENTORY_SCOPE = "caller_seed_vs_bounded_local_namespace_not_real_claim_completeness"
_STAGE_RESIDUE_SCOPE = "epistemic_endpoint_classification_not_owned_durable_or_safe_to_remove"
_MANIFEST_ALIAS_SCOPE = "two_names_one_observed_file_object_no_immutability_or_lifetime_claim"
_ROOT_SCOPE = "one_caller_supplied_lexical_root_not_canonical_namespace_identity"
_ANCESTOR_LINK_CONTAINMENT = "not_authenticated"
_BASENAME_VERIFICATION = "not_performed"
_HOSTILE_REPARSE_PREVENTION = "not_provided"
_DURABILITY_SCOPE = "fsync_not_called_crash_and_power_loss_not_observed"
_REMOTE_PUBLICATION = "not_performed"
_REAL_RECOVERY_SCOPE = "not_performed_synthetic_same_process_state_machine_only"
_EXECUTION_SCOPE = "not_performed"
_TIMESTAMP_SCOPE = "copied_index1_value_nondecreasing_not_wall_clock_causality"

_WRITER_SCOPE = "exact_temp_write_readback_then_exclusive_final_hardlink"
_HARDLINK_SCOPE = "local_same_device_two_names_one_observed_file_identity"
_ALIAS_RETENTION_SCOPE = "both_alias_and_final_retained_no_lifetime_immutability_claim"
_APPEND_STATUS = "exclusive_temp_verified_hardlink_materialized"

_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_ROOT_BYTES = 4_096
_MAX_STAGING_PARENT_BYTES = 4_096
_MAX_STAGE_PATH_BYTES = 4_162
_MAX_MANIFEST_HOST_PATH_BYTES = 4_221
_IO_CHUNK_BYTES = 65_536
_OBS_READ_CALL_BOUND = 34
_OBS_WORK_BOUND = 2_097_153
_APPEND_WRITE_BOUND = 1_048_576
_APPEND_READ_BOUND = 17
_APPEND_WORK_BOUND = 2_097_153
_CONFLICT_AGGREGATE_WORK = 979_369_992
_RECOVERY_AGGREGATE_WORK = 1_423_966_222

_PROFILES = (
    "ack_loss_confirmed",
    "ack_loss_unavailable_then_confirmed",
    "ack_loss_unavailable_until_budget_block",
    "wrong_delta_confirmed",
)
_UPPER_HEX64_RE = re.compile(r"[0-9A-F]{64}\Z", flags=re.ASCII)
_LOWER_HEX64_RE = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)
_LOWER_HEX32_RE = re.compile(r"[0-9a-f]{32}\Z", flags=re.ASCII)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]", flags=re.ASCII)
_WINDOWS_DRIVE_RE = re.compile(r"[A-Za-z]:\Z", flags=re.ASCII)
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400

_D_PUBLISHER_NONCE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-publisher-nonce-v1\0"
_D_MANIFEST_NONCE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-manifest-nonce-v1\0"
_D_RESIDUE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-residue-observation-v1\0"
_D_INVENTORY = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-inventory-projection-v1\0"
_D_ACTIVE_CHAIN = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-active-chain-projection-v1\0"
_D_ARTIFACT = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-artifact-projection-v1\0"
_D_TERMINAL_ATTESTATION = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-attestation-projection-v1\0"
_D_APPEND = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-append-v1\0"
_D_CAS = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-cas-binding-v1\0"
_D_CONFLICT = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-conflict-audit-v1\0"
_D_MANIFEST_BINDING = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-binding-v1\0"
_D_RECOVERY = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-recovery-audit-v1\0"

_OPEN_FLAGS = os.O_CREAT | os.O_EXCL | os.O_RDWR
for _open_flag_name in ("O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_NOFOLLOW"):
    _OPEN_FLAGS |= int(getattr(os, _open_flag_name, 0))
_OPEN_MODE = 0o600


class IntegratedSyntheticManifestV10Error(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class SyntheticManifestResidueObservationV10:
    observation_schema_version: str
    observation_scope: str
    origin_status: str
    observation_phase: str
    staging_parent: str
    collision_nonce: str
    stage_basename: str
    stage_path: str
    expected_payload_bytes: int
    expected_payload_sha256: str
    parent_namespace_state: str
    parent_reason_codes: tuple[str, ...]
    observation_state: str
    reason_codes: tuple[str, ...]
    observed_payload_bytes: int | None
    observed_payload_sha256: str | None
    payload_relation: str
    observation_sha256: str
    payload_byte_limit: int
    staging_parent_utf8_byte_limit: int
    stage_path_utf8_byte_limit: int
    io_chunk_bytes: int
    read_call_upper_bound: int
    payload_work_upper_bound_bytes: int
    peak_buffer_upper_bound_bytes: int
    retained_payload_copy_upper_bound_bytes: int
    path_derivation_scope: str
    nofollow_scope: str
    ancestor_reparse_check_scope: str
    backing_store_scope: str
    snapshot_scope: str
    stage_attribution_scope: str
    cleanup_scope: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_residue_record(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticManifestResidueObservationV10 cannot be subclassed")


@dataclasses.dataclass(frozen=True, slots=True)
class SyntheticCoordinatorActionTraceV10:
    trace_schema_version: str
    trace_scope: str
    origin_status: str
    operation: str
    outcome: str
    reason_codes: tuple[str, ...]
    action_sha256: str
    before_snapshot_sha256: str
    after_snapshot_sha256: str
    endpoint_state_changed: bool
    publisher_operation_sha256: str | None
    publisher_transition_sha256: str | None
    marker_sha256: str | None
    epoch_ordinal: int | None
    replay_observation: str | None
    terminal_sha256: str | None
    witness_purpose: str | None
    detached_record_scope: str
    authority_scope: str
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_trace_record(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticCoordinatorActionTraceV10 cannot be subclassed")


@dataclasses.dataclass(frozen=True, slots=True)
class SyntheticTerminalManifestAppendV10:
    append_schema_version: str
    append_scope: str
    origin_status: str
    license_id: str
    publisher_collision_nonce: str
    manifest_nonce: str
    repository_path: str
    host_final_path: str
    host_alias_path: str
    event_sha256: str
    event_bytes: int
    append_status: str
    write_call_count: int
    read_call_count: int
    file_create_count: int
    hardlink_create_count: int
    retained_path_alias_count: int
    append_sha256: str
    event_byte_limit: int
    host_path_utf8_byte_limit: int
    io_chunk_bytes: int
    write_call_upper_bound: int
    read_call_upper_bound: int
    file_create_upper_bound: int
    hardlink_create_upper_bound: int
    retained_path_alias_upper_bound: int
    payload_work_upper_bound_bytes: int
    peak_buffer_upper_bound_bytes: int
    writer_scope: str
    hardlink_scope: str
    alias_retention_scope: str
    durability_scope: str
    cleanup_scope: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_append_record(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticTerminalManifestAppendV10 cannot be subclassed")


@dataclasses.dataclass(frozen=True, slots=True)
class SyntheticConflictWithoutMarkerAuditV10:
    audit_schema_version: str
    audit_scope: str
    origin_status: str
    outcome: str
    reason_codes: tuple[str, ...]
    root: str
    seed_file_sha256: str
    seed_identity_sha256: str
    license_id: str
    claim_receipt_sha256: str
    constructor_profile: str
    publisher_collision_nonce: str
    staging_parent: str
    stage_basename: str
    stage_path: str
    proposed_payload_bytes: int
    proposed_payload_sha256: str
    alternate_payload_bytes: int | None
    alternate_payload_sha256: str | None
    initial_state_version_sha256: str
    conflict_expected_state_version_sha256: str
    initial_inventory_projection_sha256: str
    active_chain_projection_sha256: str
    pre_stage_observation: SyntheticManifestResidueObservationV10
    action_trace: SyntheticCoordinatorActionTraceV10
    final_snapshot_sha256: str
    final_lifecycle_state: str
    artifact_projection_sha256: str
    post_stage_observation: SyntheticManifestResidueObservationV10
    final_inventory_projection_sha256: str
    cas_binding_sha256: str
    audit_sha256: str
    manifest_event_delta: str
    conflict_without_marker_status: str
    stage_residue_classification: str
    same_call_binding_scope: str
    persistent_cross_binding: str
    artifact_scope: str
    inventory_scope: str
    detached_record_scope: str
    stage_residue_scope: str
    root_scope: str
    ancestor_link_containment: str
    basename_spelling_verification: str
    hostile_concurrent_reparse_prevention: str
    backing_store_scope: str
    durability_scope: str
    cleanup_scope: str
    remote_publication: str
    max_inventory_audits: int
    max_artifact_observations: int
    max_stage_observations: int
    aggregate_dependency_payload_work_upper_bound_bytes: int
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_conflict_record(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("SyntheticConflictWithoutMarkerAuditV10 cannot be subclassed")


@dataclasses.dataclass(frozen=True, slots=True)
class IntegratedSyntheticRecoveryManifestAuditV10:
    audit_schema_version: str
    audit_scope: str
    origin_status: str
    outcome: str
    reason_codes: tuple[str, ...]
    root: str
    seed_file_sha256: str
    seed_identity_sha256: str
    license_id: str
    claim_receipt_sha256: str
    constructor_profile: str
    publisher_collision_nonce: str
    manifest_nonce: str
    staging_parent: str
    stage_basename: str
    stage_path: str
    manifest_repository_path: str
    manifest_host_final_path: str
    manifest_host_alias_path: str
    proposed_payload_bytes: int
    proposed_payload_sha256: str
    alternate_payload_bytes: int | None
    alternate_payload_sha256: str | None
    initial_state_version_sha256: str
    expected_state_version_sha256: str
    initial_inventory_projection_sha256: str
    active_chain_projection_sha256: str
    pre_stage_observation: SyntheticManifestResidueObservationV10
    action_trace: tuple[SyntheticCoordinatorActionTraceV10, ...]
    action_count: int
    marker: SyntheticRecoveryMarkerV10
    witness_purpose: str
    witness_sha256: str
    preconsume_snapshot_sha256: str
    preconsume_lifecycle_state: str
    preappend_artifact_projection_sha256: str
    preappend_stage_observation: SyntheticManifestResidueObservationV10
    terminal_event_sha256: str
    manifest_append: SyntheticTerminalManifestAppendV10
    terminal_attestation_projection_sha256: str
    postappend_artifact_projection_sha256: str
    postappend_stage_observation: SyntheticManifestResidueObservationV10
    final_inventory_projection_sha256: str
    final_snapshot_sha256: str
    final_lifecycle_state: str
    cas_binding_sha256: str
    manifest_binding_sha256: str
    audit_sha256: str
    failure_code_binding: str
    stage_residue_classification: str
    phase2b1_event_binding: str
    publisher_operation_binding: str
    marker_plan_binding: str
    artifact_scope: str
    inventory_scope: str
    same_call_binding_scope: str
    persistent_cross_binding: str
    manifest_witness_atomicity: str
    timestamp_scope: str
    detached_record_scope: str
    stage_residue_scope: str
    manifest_alias_scope: str
    root_scope: str
    ancestor_link_containment: str
    basename_spelling_verification: str
    hostile_concurrent_reparse_prevention: str
    backing_store_scope: str
    durability_scope: str
    cleanup_scope: str
    remote_publication: str
    real_recovery_scope: str
    execution_scope: str
    max_seed_claims: int
    max_chain_events: int
    max_coordinator_actions: int
    max_recovery_epochs: int
    max_artifact_observations: int
    max_stage_observations: int
    max_inventory_audits: int
    max_manifest_appends: int
    aggregate_dependency_payload_work_upper_bound_bytes: int
    coordinator_payload_reference_upper_bound_bytes: int
    proposal_payload_copy_upper_bound_bytes: int
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_recovery_record(self)

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        _fail("IntegratedSyntheticRecoveryManifestAuditV10 cannot be subclassed")


def _fail(message: str) -> None:
    raise IntegratedSyntheticManifestV10Error(message) from None


def _exact_str(value: object, name: str) -> str:
    if type(value) is not str:
        _fail(f"{name} must be an exact string")
    return value


def _exact_bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes:
        _fail(f"{name} must be exact bytes")
    return value


def _exact_int(value: object, name: str) -> int:
    if type(value) is not int:
        _fail(f"{name} must be an exact integer")
    return value


def _exact_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        _fail(f"{name} must be an exact boolean")
    return value


def _false(value: object, name: str) -> None:
    if type(value) is not bool or value:
        _fail(f"{name} must be exact false")


def _hash(value: object, name: str) -> str:
    text = _exact_str(value, name)
    if _UPPER_HEX64_RE.fullmatch(text) is None:
        _fail(f"{name} must be uppercase hex64")
    return text


def _lower_hash(value: object, name: str) -> str:
    text = _exact_str(value, name)
    if _LOWER_HEX64_RE.fullmatch(text) is None:
        _fail(f"{name} must be lowercase hex64")
    return text


def _nonce(value: object, name: str) -> str:
    text = _exact_str(value, name)
    if _LOWER_HEX32_RE.fullmatch(text) is None:
        _fail(f"{name} must be lowercase hex32")
    return text


def _tuple_str(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple or any(type(item) is not str for item in value):
        _fail(f"{name} must be an exact tuple of strings")
    return value


def _utf8(value: str, name: str, maximum: int | None = None) -> bytes:
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError:
        _fail(f"{name} is not strict UTF-8")
    if maximum is not None and len(raw) > maximum:
        _fail(f"{name} exceeds its UTF-8 byte limit")
    return raw


def _u16(value: int) -> bytes:
    number = _exact_int(value, "U16 value")
    if not 0 <= number <= 0xFFFF:
        _fail("U16 value is outside range")
    return number.to_bytes(2, "big")


def _u32(value: int) -> bytes:
    number = _exact_int(value, "U32 value")
    if not 0 <= number <= 0xFFFFFFFF:
        _fail("U32 value is outside range")
    return number.to_bytes(4, "big")


def _u64(value: int) -> bytes:
    number = _exact_int(value, "U64 value")
    if not 0 <= number <= 0xFFFFFFFFFFFFFFFF:
        _fail("U64 value is outside range")
    return number.to_bytes(8, "big")


def _k(value: str) -> bytes:
    text = _exact_str(value, "K value")
    try:
        raw = text.encode("ascii")
    except UnicodeError:
        _fail("K value must be ASCII")
    return _u16(len(raw)) + raw


def _p(value: str) -> bytes:
    raw = _utf8(_exact_str(value, "P value"), "P value")
    return _u32(len(raw)) + raw


def _h(value: str) -> bytes:
    return bytes.fromhex(_hash(value, "H value"))


def _l(value: str) -> bytes:
    return bytes.fromhex(_lower_hash(value, "L value"))


def _n(value: str) -> bytes:
    return bytes.fromhex(_nonce(value, "N value"))


def _q(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _h(value)


def _j(value: int | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _u64(value)


def _s(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _k(value)


def _t(value: tuple[str, ...]) -> bytes:
    items = _tuple_str(value, "T value")
    return _u16(len(items)) + b"".join(_k(item) for item in items)


def _b(value: bool) -> bytes:
    return b"\x01" if _exact_bool(value, "B value") else b"\x00"


def _z(value: bool | None) -> bytes:
    if value is None:
        return b"\x00"
    return b"\x02" if _exact_bool(value, "Z value") else b"\x01"


def _sha(preimage: bytes) -> str:
    return hashlib.sha256(preimage).hexdigest().upper()


def _raw_sha(payload: bytes) -> str:
    return _sha(_exact_bytes(payload, "payload"))


def _publisher_nonce(
    seed_identity_sha256: str,
    profile: str,
    proposed_bytes: int,
    proposed_sha256: str,
    alternate_bytes: int | None,
    alternate_sha256: str | None,
) -> str:
    preimage = (
        _D_PUBLISHER_NONCE
        + _h(seed_identity_sha256)
        + _k(profile)
        + _u64(proposed_bytes)
        + _h(proposed_sha256)
        + _j(alternate_bytes)
        + _q(alternate_sha256)
    )
    return hashlib.sha256(preimage).digest()[:16].hex()


def _manifest_nonce(event_sha256: str, marker_sha256: str, terminal_sha256: str) -> str:
    preimage = (
        _D_MANIFEST_NONCE + _h(event_sha256) + _h(marker_sha256) + _h(terminal_sha256)
    )
    return hashlib.sha256(preimage).digest()[:16].hex()


def _residue_sha256(value: SyntheticManifestResidueObservationV10) -> str:
    return _sha(
        _D_RESIDUE
        + _k(value.observation_phase)
        + _p(value.staging_parent)
        + _n(value.collision_nonce)
        + _k(value.stage_basename)
        + _p(value.stage_path)
        + _u64(value.expected_payload_bytes)
        + _h(value.expected_payload_sha256)
        + _k(value.parent_namespace_state)
        + _t(value.parent_reason_codes)
        + _k(value.observation_state)
        + _t(value.reason_codes)
        + _j(value.observed_payload_bytes)
        + _q(value.observed_payload_sha256)
        + _k(value.payload_relation)
    )


def _trace_bytes(value: SyntheticCoordinatorActionTraceV10) -> bytes:
    return (
        _k(value.operation)
        + _k(value.outcome)
        + _t(value.reason_codes)
        + _h(value.action_sha256)
        + _h(value.before_snapshot_sha256)
        + _h(value.after_snapshot_sha256)
        + _b(value.endpoint_state_changed)
        + _q(value.publisher_operation_sha256)
        + _q(value.publisher_transition_sha256)
        + _q(value.marker_sha256)
        + _j(value.epoch_ordinal)
        + _s(value.replay_observation)
        + _q(value.terminal_sha256)
        + _s(value.witness_purpose)
    )


def _append_sha256(value: SyntheticTerminalManifestAppendV10) -> str:
    return _sha(
        _D_APPEND
        + _l(value.license_id)
        + _n(value.publisher_collision_nonce)
        + _n(value.manifest_nonce)
        + _p(value.repository_path)
        + _p(value.host_final_path)
        + _p(value.host_alias_path)
        + _h(value.event_sha256)
        + _u64(value.event_bytes)
        + _k(value.append_status)
        + _u64(value.write_call_count)
        + _u64(value.read_call_count)
        + _u64(value.file_create_count)
        + _u64(value.hardlink_create_count)
        + _u64(value.retained_path_alias_count)
    )


def _cas_sha256(
    endpoint_kind: str,
    initial_version: str,
    expected_version: str,
    proposed_bytes: int,
    proposed_sha256: str,
    alternate_bytes: int | None,
    alternate_sha256: str | None,
    publisher_operation_sha256: str | None,
    publisher_transition_sha256: str | None,
    synthetic_fault_transition_sha256: str | None,
    marker_sha256: str | None,
) -> str:
    if endpoint_kind not in ("conflict", "recovery"):
        _fail("endpoint_kind is invalid")
    return _sha(
        _D_CAS
        + _k(endpoint_kind)
        + _h(initial_version)
        + _h(expected_version)
        + _u64(proposed_bytes)
        + _h(proposed_sha256)
        + _j(alternate_bytes)
        + _q(alternate_sha256)
        + _q(publisher_operation_sha256)
        + _q(publisher_transition_sha256)
        + _q(synthetic_fault_transition_sha256)
        + _q(marker_sha256)
    )


def _inventory_sha256(value: SyntheticSeedLocalInventoryAuditV10) -> str:
    if type(value.claim_audits) is not tuple or len(value.claim_audits) != 1:
        _fail("inventory projection requires exactly one claim")
    claim = value.claim_audits[0]
    if type(claim) is not SyntheticLocalClaimAuditV10:
        _fail("inventory claim has the wrong type")
    return _sha(
        _D_INVENTORY
        + _h(value.seed_file_sha256)
        + _h(value.seed_identity_sha256)
        + _k(value.base_directory_status)
        + _u64(value.seed_count)
        + _u64(value.local_directory_count)
        + _u64(value.union_claim_count)
        + _u64(value.examined_claim_count)
        + _u64(value.total_observed_event_bytes)
        + _u64(value.unexpected_entry_count)
        + _k(value.coverage_status)
        + _b(value.set_equality)
        + _b(value.all_seeded_local_present)
        + _b(value.all_seeded_terminal)
        + _b(value.all_seeded_receipts_match)
        + _u16(1)
        + _l(claim.license_id)
        + _b(claim.seed_membership)
        + _b(claim.local_membership)
        + _k(claim.set_relation)
        + _k(claim.receipt_relation)
        + _q(claim.seed_receipt_sha256)
        + _q(claim.local_receipt_sha256)
        + _k(claim.chain_observation)
        + _j(claim.event_count)
        + _j(claim.last_event_index)
        + _q(claim.last_event_sha256)
        + _z(claim.terminal_event)
        + _s(claim.recorded_verdict)
    )


def _active_chain_sha256(
    inspection: AttemptManifestChainInspectionV10,
    event_file: AttemptManifestEventFileV10,
) -> str:
    event = event_file.event
    return _sha(
        _D_ACTIVE_CHAIN
        + _l(inspection.license_id)
        + _h(inspection.claim_receipt_sha256)
        + _h(inspection.first_event_sha256)
        + _h(inspection.last_event_sha256)
        + _u64(len(event_file.event_bytes))
        + _u64(inspection.event_count)
        + _u64(inspection.last_event_index)
        + _k(inspection.last_event_type)
        + _b(inspection.terminal_event)
        + _j(inspection.next_event_index)
        + _k(event.created_at_utc)
    )


def _artifact_sha256(value: LocalArtifactSetObservationV10) -> str:
    rows = (value.reservation, value.ledger, value.report)
    preimage = (
        _D_ARTIFACT
        + _h(value.claim_receipt_sha256)
        + _k(value.parent_namespace_state)
        + _t(value.parent_reason_codes)
        + _u16(3)
    )
    for row in rows:
        preimage += (
            _k(row.artifact_kind)
            + _p(row.repository_path)
            + _k(row.observation_state)
            + _t(row.reason_codes)
            + _q(row.artifact_sha256)
            + _j(row.artifact_bytes)
            + _u64(row.byte_limit)
        )
    preimage += (
        _u64(value.present_count)
        + _u64(value.absent_count)
        + _u64(value.indeterminate_count)
        + _u64(value.total_present_bytes)
        + _k(value.snapshot_scope)
    )
    return _sha(preimage)


def _terminal_attestation_sha256(value: AttemptManifestChainAttestationV10) -> str:
    return _sha(
        _D_TERMINAL_ATTESTATION
        + _l(value.license_id)
        + _h(value.claim_receipt_sha256)
        + _u64(value.event_count)
        + _h(value.first_event_sha256)
        + _u64(value.last_event_index)
        + _h(value.last_event_sha256)
        + _k(value.chain_state)
        + _b(value.terminal_event)
        + _k(value.last_event_type)
        + _s(value.recorded_verdict)
        + _t(value.failure_codes)
    )


def _conflict_audit_sha256(value: SyntheticConflictWithoutMarkerAuditV10) -> str:
    return _sha(
        _D_CONFLICT
        + _k(value.outcome)
        + _t(value.reason_codes)
        + _p(value.root)
        + _h(value.seed_file_sha256)
        + _h(value.seed_identity_sha256)
        + _l(value.license_id)
        + _h(value.claim_receipt_sha256)
        + _k(value.constructor_profile)
        + _n(value.publisher_collision_nonce)
        + _p(value.staging_parent)
        + _k(value.stage_basename)
        + _p(value.stage_path)
        + _u64(value.proposed_payload_bytes)
        + _h(value.proposed_payload_sha256)
        + _j(value.alternate_payload_bytes)
        + _q(value.alternate_payload_sha256)
        + _h(value.initial_state_version_sha256)
        + _h(value.conflict_expected_state_version_sha256)
        + _h(value.initial_inventory_projection_sha256)
        + _h(value.active_chain_projection_sha256)
        + _h(value.pre_stage_observation.observation_sha256)
        + _trace_bytes(value.action_trace)
        + _h(value.final_snapshot_sha256)
        + _k(value.final_lifecycle_state)
        + _h(value.artifact_projection_sha256)
        + _h(value.post_stage_observation.observation_sha256)
        + _h(value.final_inventory_projection_sha256)
        + _h(value.cas_binding_sha256)
        + _k(value.manifest_event_delta)
        + _k(value.conflict_without_marker_status)
        + _k(value.stage_residue_classification)
    )


def _manifest_binding_sha256(value: IntegratedSyntheticRecoveryManifestAuditV10) -> str:
    preimage = (
        _D_MANIFEST_BINDING
        + _h(value.active_chain_projection_sha256)
        + _h(value.marker.marker_sha256)
        + _h(value.cas_binding_sha256)
        + _h(value.terminal_event_sha256)
        + _h(value.manifest_append.append_sha256)
        + _h(value.terminal_attestation_projection_sha256)
        + _h(value.preappend_artifact_projection_sha256)
        + _h(value.pre_stage_observation.observation_sha256)
        + _h(value.preappend_stage_observation.observation_sha256)
        + _h(value.postappend_artifact_projection_sha256)
        + _h(value.postappend_stage_observation.observation_sha256)
        + _h(value.final_inventory_projection_sha256)
        + _h(value.preconsume_snapshot_sha256)
        + _h(value.final_snapshot_sha256)
        + _u16(value.action_count)
    )
    for trace in value.action_trace:
        preimage += _trace_bytes(trace)
    return _sha(preimage)


def _recovery_audit_sha256(value: IntegratedSyntheticRecoveryManifestAuditV10) -> str:
    preimage = (
        _D_RECOVERY
        + _k(value.outcome)
        + _t(value.reason_codes)
        + _p(value.root)
        + _h(value.seed_file_sha256)
        + _h(value.seed_identity_sha256)
        + _l(value.license_id)
        + _h(value.claim_receipt_sha256)
        + _k(value.constructor_profile)
        + _n(value.publisher_collision_nonce)
        + _n(value.manifest_nonce)
        + _p(value.staging_parent)
        + _k(value.stage_basename)
        + _p(value.stage_path)
        + _p(value.manifest_repository_path)
        + _p(value.manifest_host_final_path)
        + _p(value.manifest_host_alias_path)
        + _u64(value.proposed_payload_bytes)
        + _h(value.proposed_payload_sha256)
        + _j(value.alternate_payload_bytes)
        + _q(value.alternate_payload_sha256)
        + _h(value.initial_state_version_sha256)
        + _h(value.expected_state_version_sha256)
        + _h(value.initial_inventory_projection_sha256)
        + _h(value.active_chain_projection_sha256)
        + _h(value.pre_stage_observation.observation_sha256)
        + _u16(value.action_count)
    )
    for trace in value.action_trace:
        preimage += _trace_bytes(trace)
    preimage += (
        _h(value.marker.marker_sha256)
        + _k(value.witness_purpose)
        + _h(value.witness_sha256)
        + _h(value.preconsume_snapshot_sha256)
        + _k(value.preconsume_lifecycle_state)
        + _h(value.preappend_artifact_projection_sha256)
        + _h(value.preappend_stage_observation.observation_sha256)
        + _h(value.terminal_event_sha256)
        + _h(value.manifest_append.append_sha256)
        + _h(value.terminal_attestation_projection_sha256)
        + _h(value.postappend_artifact_projection_sha256)
        + _h(value.postappend_stage_observation.observation_sha256)
        + _h(value.final_inventory_projection_sha256)
        + _h(value.final_snapshot_sha256)
        + _k(value.final_lifecycle_state)
        + _h(value.cas_binding_sha256)
        + _h(value.manifest_binding_sha256)
        + _k(value.failure_code_binding)
        + _k(value.stage_residue_classification)
    )
    return _sha(preimage)


def _require_static_strings(value: object, rows: tuple[tuple[str, str], ...]) -> None:
    for name, expected in rows:
        if _exact_str(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")


def _require_false_authority(value: object, *, canonical: bool = False) -> None:
    if canonical:
        _false(getattr(value, "canonical_remote_authority"), "canonical_remote_authority")
    for name in (
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        _false(getattr(value, name), name)


def _validate_residue_record(value: SyntheticManifestResidueObservationV10) -> None:
    if type(value) is not SyntheticManifestResidueObservationV10:
        _fail("residue has the wrong record type")
    _require_static_strings(
        value,
        (
            ("observation_schema_version", _OBSERVATION_SCHEMA),
            ("observation_scope", _OBSERVATION_SCOPE),
            ("origin_status", _ORIGIN_STATUS),
            ("path_derivation_scope", _PATH_DERIVATION_SCOPE),
            ("nofollow_scope", _NOFOLLOW_SCOPE),
            ("ancestor_reparse_check_scope", _ANCESTOR_REPARSE_SCOPE),
            ("backing_store_scope", _BACKING_STORE_SCOPE),
            ("snapshot_scope", _SNAPSHOT_SCOPE),
            ("stage_attribution_scope", _STAGE_ATTRIBUTION_SCOPE),
            ("cleanup_scope", _CLEANUP_SCOPE),
            ("authority_scope", _AUTHORITY_SCOPE),
        ),
    )
    if value.observation_phase not in (
        "conflict_pre",
        "conflict_post",
        "pre_publish",
        "pre_append",
        "post_append",
    ):
        _fail("observation_phase is invalid")
    _utf8(_exact_str(value.staging_parent, "staging_parent"), "staging_parent", _MAX_STAGING_PARENT_BYTES)
    nonce = _nonce(value.collision_nonce, "collision_nonce")
    expected_basename = "uprime-rpc-fake-cas-stage-v1-" + nonce + ".bin"
    if value.stage_basename != expected_basename:
        _fail("stage_basename is invalid")
    expected_path = _os_path_join(value.staging_parent, expected_basename)
    if value.stage_path != expected_path or _os_path_normpath(value.stage_path) != value.stage_path:
        _fail("stage_path is invalid")
    _utf8(value.stage_path, "stage_path", _MAX_STAGE_PATH_BYTES)
    expected_bytes = _exact_int(value.expected_payload_bytes, "expected_payload_bytes")
    if not 0 <= expected_bytes <= _MAX_PAYLOAD_BYTES:
        _fail("expected_payload_bytes is outside bounds")
    _hash(value.expected_payload_sha256, "expected_payload_sha256")
    parent_reasons = _tuple_str(value.parent_reason_codes, "parent_reason_codes")
    reasons = _tuple_str(value.reason_codes, "reason_codes")
    if len(parent_reasons) != 1 or len(reasons) != 1:
        _fail("observation reasons must be singletons")
    if value.parent_namespace_state not in ("present", "absent", "indeterminate"):
        _fail("parent_namespace_state is invalid")
    if value.observation_state not in ("present", "absent", "indeterminate"):
        _fail("observation_state is invalid")
    if value.payload_relation not in ("exact", "different", "not_present", "indeterminate"):
        _fail("payload_relation is invalid")
    if value.observation_state == "present":
        observed = _exact_int(value.observed_payload_bytes, "observed_payload_bytes")
        if not 0 <= observed <= _MAX_PAYLOAD_BYTES:
            _fail("observed_payload_bytes is outside bounds")
        _hash(value.observed_payload_sha256, "observed_payload_sha256")
        if value.payload_relation == "exact":
            if observed != expected_bytes or value.observed_payload_sha256 != value.expected_payload_sha256:
                _fail("exact payload relation is inconsistent")
            expected_reason = "stable_bounded_regular_file_exact_payload"
        elif value.payload_relation == "different":
            expected_reason = "stable_bounded_regular_file_different_payload"
        else:
            _fail("present observation has an invalid relation")
        if reasons != (expected_reason,):
            _fail("present observation reason is invalid")
    else:
        if value.observed_payload_bytes is not None or value.observed_payload_sha256 is not None:
            _fail("nonpresent observation carries payload cells")
        expected_relation = "not_present" if value.observation_state == "absent" else "indeterminate"
        if value.payload_relation != expected_relation:
            _fail("nonpresent payload relation is invalid")
    if value.parent_namespace_state == "present":
        if parent_reasons != ("stable_parent_directory",):
            _fail("present parent reason is invalid")
        if value.observation_state == "absent" and reasons != ("absent_at_both_points",):
            _fail("present-parent absence reason is invalid")
        if value.observation_state == "indeterminate" and reasons[0] not in {
            "initial_stat_error",
            "absence_changed",
            "absence_recheck_error",
            "metadata_invalid",
            "reparse_entry",
            "nonregular_entry",
            "size_limit_exceeded",
            "open_error",
            "descriptor_metadata_invalid",
            "descriptor_nonregular",
            "descriptor_path_mismatch",
            "seek_error",
            "read_error",
            "short_read",
            "unexpected_eof_relation",
            "descriptor_drift",
            "close_error",
            "final_stat_error",
            "final_entry_invalid",
            "final_path_drift",
        }:
            _fail("present-parent indeterminate reason is invalid")
    elif value.parent_namespace_state == "absent":
        if parent_reasons != ("stable_parent_absence",) or value.observation_state != "absent" or reasons != parent_reasons:
            _fail("absent parent row is invalid")
    elif reasons != parent_reasons or value.observation_state != "indeterminate":
        _fail("indeterminate parent row is invalid")
    if value.parent_namespace_state == "indeterminate" and parent_reasons[0] not in {
        "parent_initial_stat_error",
        "parent_metadata_invalid",
        "parent_reparse_entry",
        "parent_nondirectory",
        "parent_absence_changed",
        "parent_absence_recheck_error",
        "parent_final_stat_error",
        "parent_final_entry_invalid",
        "parent_drift",
    }:
        _fail("indeterminate parent reason is invalid")
    constants = (
        ("payload_byte_limit", _MAX_PAYLOAD_BYTES),
        ("staging_parent_utf8_byte_limit", _MAX_STAGING_PARENT_BYTES),
        ("stage_path_utf8_byte_limit", _MAX_STAGE_PATH_BYTES),
        ("io_chunk_bytes", _IO_CHUNK_BYTES),
        ("read_call_upper_bound", _OBS_READ_CALL_BOUND),
        ("payload_work_upper_bound_bytes", _OBS_WORK_BOUND),
        ("peak_buffer_upper_bound_bytes", _IO_CHUNK_BYTES),
        ("retained_payload_copy_upper_bound_bytes", 0),
    )
    for name, expected in constants:
        if _exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    _false(value.canonical_remote_authority, "canonical_remote_authority")
    _require_false_authority(value)
    if _hash(value.observation_sha256, "observation_sha256") != _residue_sha256(value):
        _fail("observation_sha256 is invalid")


def _validate_nested_stage_binding(value: object, audit: object) -> None:
    if (
        getattr(value, "staging_parent") != getattr(audit, "staging_parent")
        or getattr(value, "collision_nonce") != getattr(audit, "publisher_collision_nonce")
        or getattr(value, "stage_basename") != getattr(audit, "stage_basename")
        or getattr(value, "stage_path") != getattr(audit, "stage_path")
        or getattr(value, "expected_payload_bytes") != getattr(audit, "proposed_payload_bytes")
        or getattr(value, "expected_payload_sha256") != getattr(audit, "proposed_payload_sha256")
    ):
        _fail("nested stage observation differs from audit cells")


def _validate_trace_record(value: SyntheticCoordinatorActionTraceV10) -> None:
    if type(value) is not SyntheticCoordinatorActionTraceV10:
        _fail("trace has the wrong record type")
    _require_static_strings(
        value,
        (
            ("trace_schema_version", _TRACE_SCHEMA),
            ("trace_scope", _TRACE_SCOPE),
            ("origin_status", _ORIGIN_STATUS),
            ("detached_record_scope", _DETACHED_SCOPE),
            ("authority_scope", _AUTHORITY_SCOPE),
        ),
    )
    operation = _exact_str(value.operation, "operation")
    outcome = _exact_str(value.outcome, "outcome")
    if operation not in ("publish", "acquire_epoch", "replay_epoch", "consume_witness"):
        _fail("trace operation is invalid")
    reasons = _tuple_str(value.reason_codes, "reason_codes")
    if len(reasons) != 1:
        _fail("trace reason_codes must be a singleton")
    for name in ("action_sha256", "before_snapshot_sha256", "after_snapshot_sha256"):
        _hash(getattr(value, name), name)
    changed = _exact_bool(value.endpoint_state_changed, "endpoint_state_changed")
    if changed != (value.before_snapshot_sha256 != value.after_snapshot_sha256):
        _fail("trace state-change relation is invalid")
    for name in (
        "publisher_operation_sha256",
        "publisher_transition_sha256",
        "marker_sha256",
        "terminal_sha256",
    ):
        item = getattr(value, name)
        if item is not None:
            _hash(item, name)
    if (value.publisher_operation_sha256 is None) != (value.publisher_transition_sha256 is None):
        _fail("publisher trace hashes have invalid nullability")
    if value.epoch_ordinal is not None:
        ordinal = _exact_int(value.epoch_ordinal, "epoch_ordinal")
        if not 1 <= ordinal <= 4:
            _fail("epoch_ordinal is invalid")
    for name in ("replay_observation", "witness_purpose"):
        item = getattr(value, name)
        if item is not None:
            _exact_str(item, name)
    row_map = {
        ("publish", "cas_conflict_no_marker"): ("expected_state_version_mismatch",),
        ("publish", "synthetic_marker_committed_result_withheld"): ("synthetic_marker_committed",),
        ("acquire_epoch", "epoch_issued"): ("recovery_marker_pending",),
        ("replay_epoch", "replay_unavailable_retry_pending"): ("same_kernel_replay_unavailable",),
        ("replay_epoch", "replay_unavailable_budget_permanent_block"): ("recovery_epoch_budget_exhausted_after_unavailable",),
        ("replay_epoch", "replay_confirmed_recovered"): ("synthetic_intended_transition_confirmed",),
        ("replay_epoch", "replay_wrong_delta_permanent_block"): ("synthetic_wrong_delta_confirmed",),
        ("consume_witness", "witness_consumed"): ("witness_consumed",),
    }
    if row_map.get((operation, outcome)) != reasons:
        _fail("trace outcome/reason row is invalid")
    if operation == "publish" and outcome == "cas_conflict_no_marker":
        if (
            changed
            or value.publisher_operation_sha256 is None
            or value.publisher_transition_sha256 is None
            or value.marker_sha256 is not None
            or value.epoch_ordinal is not None
            or value.replay_observation is not None
            or value.terminal_sha256 is not None
            or value.witness_purpose is not None
        ):
            _fail("conflict trace nullability is invalid")
    elif operation == "publish":
        if (
            not changed
            or value.publisher_operation_sha256 is not None
            or value.publisher_transition_sha256 is not None
            or value.marker_sha256 is None
            or value.epoch_ordinal is not None
            or value.replay_observation is not None
            or value.terminal_sha256 is not None
            or value.witness_purpose is not None
        ):
            _fail("recovery publish trace nullability is invalid")
    elif operation == "acquire_epoch":
        if (
            not changed
            or value.publisher_operation_sha256 is not None
            or value.marker_sha256 is None
            or value.epoch_ordinal is None
            or value.replay_observation is not None
            or value.terminal_sha256 is not None
            or value.witness_purpose is not None
        ):
            _fail("acquire trace nullability is invalid")
    elif operation == "replay_epoch":
        terminal = outcome != "replay_unavailable_retry_pending"
        expected_observation = {
            "replay_unavailable_retry_pending": "unavailable",
            "replay_unavailable_budget_permanent_block": "unavailable",
            "replay_confirmed_recovered": "confirmed_intended",
            "replay_wrong_delta_permanent_block": "confirmed_wrong_delta",
        }[outcome]
        expected_purpose = {
            "replay_unavailable_retry_pending": None,
            "replay_unavailable_budget_permanent_block": "record_permanent_block",
            "replay_confirmed_recovered": "record_recovered_terminal",
            "replay_wrong_delta_permanent_block": "record_permanent_block",
        }[outcome]
        if (
            not changed
            or value.publisher_operation_sha256 is not None
            or value.marker_sha256 is None
            or value.epoch_ordinal is None
            or value.replay_observation != expected_observation
            or (value.terminal_sha256 is not None) != terminal
            or value.witness_purpose != expected_purpose
        ):
            _fail("replay trace nullability is invalid")
    else:
        if (
            not changed
            or value.publisher_operation_sha256 is not None
            or value.marker_sha256 is None
            or value.epoch_ordinal is None
            or value.replay_observation is not None
            or value.terminal_sha256 is None
            or value.witness_purpose is None
        ):
            _fail("consume trace nullability is invalid")
        if value.witness_purpose not in (
            "record_recovered_terminal",
            "record_permanent_block",
        ):
            _fail("consume trace witness_purpose is invalid")
    _require_false_authority(value)


def _validate_append_record(value: SyntheticTerminalManifestAppendV10) -> None:
    if type(value) is not SyntheticTerminalManifestAppendV10:
        _fail("manifest append has the wrong record type")
    _require_static_strings(
        value,
        (
            ("append_schema_version", _APPEND_SCHEMA),
            ("append_scope", _APPEND_SCOPE),
            ("origin_status", _ORIGIN_STATUS),
            ("append_status", _APPEND_STATUS),
            ("writer_scope", _WRITER_SCOPE),
            ("hardlink_scope", _HARDLINK_SCOPE),
            ("alias_retention_scope", _ALIAS_RETENTION_SCOPE),
            ("durability_scope", _DURABILITY_SCOPE),
            ("cleanup_scope", _CLEANUP_SCOPE),
            ("authority_scope", _AUTHORITY_SCOPE),
        ),
    )
    _lower_hash(value.license_id, "license_id")
    _nonce(value.publisher_collision_nonce, "publisher_collision_nonce")
    _nonce(value.manifest_nonce, "manifest_nonce")
    for name in ("repository_path", "host_final_path", "host_alias_path"):
        _utf8(_exact_str(getattr(value, name), name), name, _MAX_MANIFEST_HOST_PATH_BYTES)
    expected_repository = (
        "docs/experiments/artifacts/uprime_u1_rpc_attempts/" + value.license_id + "/0002.json"
    )
    if value.repository_path != expected_repository:
        _fail("append repository_path is invalid")
    if _os_path_normpath(value.host_final_path) != value.host_final_path or _os_path_normpath(value.host_alias_path) != value.host_alias_path:
        _fail("append host path is not normalized")
    final_suffix = _os_path_join(
        "docs", "experiments", "artifacts", "uprime_u1_rpc_attempts", value.license_id, "0002.json"
    )
    alias_basename = "uprime-rpc-attempt-manifest-stage-v1-" + value.manifest_nonce + ".json"
    alias_suffix = _os_path_join(
        "docs", "experiments", "artifacts", "uprime_u1_rpc_staging", value.license_id, alias_basename
    )
    final_tail = os.sep + final_suffix
    alias_tail = os.sep + alias_suffix
    if not value.host_final_path.endswith(final_tail) or not value.host_alias_path.endswith(alias_tail):
        _fail("append host path suffix is invalid")
    if value.host_final_path[: -len(final_tail)] != value.host_alias_path[: -len(alias_tail)]:
        _fail("append aliases do not share one lexical root")
    _hash(value.event_sha256, "event_sha256")
    event_bytes = _exact_int(value.event_bytes, "event_bytes")
    if not 1 <= event_bytes <= _MAX_PAYLOAD_BYTES:
        _fail("event_bytes is outside bounds")
    actuals = (
        ("write_call_count", 1, _APPEND_WRITE_BOUND),
        ("read_call_count", 2, _APPEND_READ_BOUND),
    )
    for name, low, high in actuals:
        number = _exact_int(getattr(value, name), name)
        if not low <= number <= high:
            _fail(f"{name} is outside bounds")
    for name, expected in (
        ("file_create_count", 1),
        ("hardlink_create_count", 1),
        ("retained_path_alias_count", 2),
        ("event_byte_limit", _MAX_PAYLOAD_BYTES),
        ("host_path_utf8_byte_limit", _MAX_MANIFEST_HOST_PATH_BYTES),
        ("io_chunk_bytes", _IO_CHUNK_BYTES),
        ("write_call_upper_bound", _APPEND_WRITE_BOUND),
        ("read_call_upper_bound", _APPEND_READ_BOUND),
        ("file_create_upper_bound", 1),
        ("hardlink_create_upper_bound", 1),
        ("retained_path_alias_upper_bound", 2),
        ("payload_work_upper_bound_bytes", _APPEND_WORK_BOUND),
        ("peak_buffer_upper_bound_bytes", _IO_CHUNK_BYTES),
    ):
        if _exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    _false(value.canonical_remote_authority, "canonical_remote_authority")
    _require_false_authority(value)
    if _hash(value.append_sha256, "append_sha256") != _append_sha256(value):
        _fail("append_sha256 is invalid")


def _validate_conflict_record(value: SyntheticConflictWithoutMarkerAuditV10) -> None:
    if type(value) is not SyntheticConflictWithoutMarkerAuditV10:
        _fail("conflict audit has the wrong record type")
    _require_static_strings(
        value,
        (
            ("audit_schema_version", _CONFLICT_SCHEMA),
            ("audit_scope", _CONFLICT_SCOPE),
            ("origin_status", _ORIGIN_STATUS),
            ("outcome", "conflict_without_marker_confirmed"),
            ("final_lifecycle_state", "OPEN"),
            ("manifest_event_delta", "zero"),
            ("conflict_without_marker_status", "exact_no_marker_no_stage_no_manifest"),
            ("stage_residue_classification", "exact_absent_at_two_sequential_endpoints"),
            ("same_call_binding_scope", _SAME_CALL_SCOPE),
            ("persistent_cross_binding", _PERSISTENT_BINDING),
            ("artifact_scope", _ARTIFACT_SCOPE),
            ("inventory_scope", _INVENTORY_SCOPE),
            ("detached_record_scope", _DETACHED_SCOPE),
            ("stage_residue_scope", _STAGE_RESIDUE_SCOPE),
            ("root_scope", _ROOT_SCOPE),
            ("ancestor_link_containment", _ANCESTOR_LINK_CONTAINMENT),
            ("basename_spelling_verification", _BASENAME_VERIFICATION),
            ("hostile_concurrent_reparse_prevention", _HOSTILE_REPARSE_PREVENTION),
            ("backing_store_scope", _BACKING_STORE_SCOPE),
            ("durability_scope", _DURABILITY_SCOPE),
            ("cleanup_scope", _CLEANUP_SCOPE),
            ("remote_publication", _REMOTE_PUBLICATION),
        ),
    )
    if _tuple_str(value.reason_codes, "reason_codes") != ("expected_state_version_mismatch",):
        _fail("conflict reason_codes are invalid")
    _validate_common_audit_cells(value)
    if value.conflict_expected_state_version_sha256 == value.initial_state_version_sha256:
        _fail("conflict expected version is not stale")
    expected_stale = (
        ("1" if value.initial_state_version_sha256[0] == "0" else "0")
        + value.initial_state_version_sha256[1:]
    )
    if value.conflict_expected_state_version_sha256 != expected_stale:
        _fail("conflict expected version derivation is invalid")
    if type(value.pre_stage_observation) is not SyntheticManifestResidueObservationV10:
        _fail("pre_stage_observation has the wrong type")
    if type(value.post_stage_observation) is not SyntheticManifestResidueObservationV10:
        _fail("post_stage_observation has the wrong type")
    _validate_residue_record(value.pre_stage_observation)
    _validate_residue_record(value.post_stage_observation)
    if (
        value.pre_stage_observation.observation_phase != "conflict_pre"
        or value.post_stage_observation.observation_phase != "conflict_post"
        or value.pre_stage_observation.observation_state != "absent"
        or value.post_stage_observation.observation_state != "absent"
        or value.pre_stage_observation.payload_relation != "not_present"
        or value.post_stage_observation.payload_relation != "not_present"
    ):
        _fail("conflict stage observations are invalid")
    _validate_nested_stage_binding(value.pre_stage_observation, value)
    _validate_nested_stage_binding(value.post_stage_observation, value)
    if type(value.action_trace) is not SyntheticCoordinatorActionTraceV10:
        _fail("action_trace has the wrong type")
    _validate_trace_record(value.action_trace)
    if (
        value.action_trace.operation != "publish"
        or value.action_trace.outcome != "cas_conflict_no_marker"
        or value.action_trace.reason_codes != ("expected_state_version_mismatch",)
        or value.action_trace.publisher_operation_sha256 is None
        or value.action_trace.publisher_transition_sha256 is None
        or value.action_trace.marker_sha256 is not None
        or value.action_trace.endpoint_state_changed
    ):
        _fail("conflict action trace is invalid")
    if value.final_snapshot_sha256 != value.action_trace.after_snapshot_sha256:
        _fail("conflict final snapshot does not match the action")
    for name in (
        "initial_inventory_projection_sha256",
        "active_chain_projection_sha256",
        "final_snapshot_sha256",
        "artifact_projection_sha256",
        "final_inventory_projection_sha256",
        "cas_binding_sha256",
    ):
        _hash(getattr(value, name), name)
    if value.final_inventory_projection_sha256 != value.initial_inventory_projection_sha256:
        _fail("conflict inventory changed")
    expected_cas = _cas_sha256(
        "conflict",
        value.initial_state_version_sha256,
        value.conflict_expected_state_version_sha256,
        value.proposed_payload_bytes,
        value.proposed_payload_sha256,
        value.alternate_payload_bytes,
        value.alternate_payload_sha256,
        value.action_trace.publisher_operation_sha256,
        value.action_trace.publisher_transition_sha256,
        None,
        None,
    )
    if value.cas_binding_sha256 != expected_cas:
        _fail("conflict cas_binding_sha256 is invalid")
    for name, expected in (
        ("max_inventory_audits", 2),
        ("max_artifact_observations", 1),
        ("max_stage_observations", 2),
        ("aggregate_dependency_payload_work_upper_bound_bytes", _CONFLICT_AGGREGATE_WORK),
    ):
        if _exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    _false(value.canonical_remote_authority, "canonical_remote_authority")
    _require_false_authority(value)
    if _hash(value.audit_sha256, "audit_sha256") != _conflict_audit_sha256(value):
        _fail("conflict audit_sha256 is invalid")


def _validate_recovery_record(value: IntegratedSyntheticRecoveryManifestAuditV10) -> None:
    if type(value) is not IntegratedSyntheticRecoveryManifestAuditV10:
        _fail("recovery audit has the wrong record type")
    _require_static_strings(
        value,
        (
            ("audit_schema_version", _RECOVERY_SCHEMA),
            ("audit_scope", _RECOVERY_SCOPE),
            ("origin_status", _ORIGIN_STATUS),
            ("outcome", "integrated_synthetic_terminal_manifest_appended_and_witness_spent"),
            ("failure_code_binding", "exact_phase2b2e_marker_tuple_no_inference"),
            ("stage_residue_classification", "absent_before_publish_exact_proposal_at_two_later_endpoints"),
            ("phase2b1_event_binding", "exact_index2_recovery_bytes_and_terminal_attestation"),
            ("publisher_operation_binding", "marker_hashes_plus_same_call_stage_byte_observations"),
            ("marker_plan_binding", "exact_phase2b2e_profile_plan_and_live_handle_sequence"),
            ("artifact_scope", _ARTIFACT_SCOPE),
            ("inventory_scope", _INVENTORY_SCOPE),
            ("same_call_binding_scope", _SAME_CALL_SCOPE),
            ("persistent_cross_binding", _PERSISTENT_BINDING),
            ("manifest_witness_atomicity", _MANIFEST_WITNESS_ATOMICITY),
            ("timestamp_scope", _TIMESTAMP_SCOPE),
            ("detached_record_scope", _DETACHED_SCOPE),
            ("stage_residue_scope", _STAGE_RESIDUE_SCOPE),
            ("manifest_alias_scope", _MANIFEST_ALIAS_SCOPE),
            ("root_scope", _ROOT_SCOPE),
            ("ancestor_link_containment", _ANCESTOR_LINK_CONTAINMENT),
            ("basename_spelling_verification", _BASENAME_VERIFICATION),
            ("hostile_concurrent_reparse_prevention", _HOSTILE_REPARSE_PREVENTION),
            ("backing_store_scope", _BACKING_STORE_SCOPE),
            ("durability_scope", _DURABILITY_SCOPE),
            ("cleanup_scope", _CLEANUP_SCOPE),
            ("remote_publication", _REMOTE_PUBLICATION),
            ("real_recovery_scope", _REAL_RECOVERY_SCOPE),
            ("execution_scope", _EXECUTION_SCOPE),
        ),
    )
    _validate_common_audit_cells(value)
    if value.expected_state_version_sha256 != value.initial_state_version_sha256:
        _fail("recovery expected version is invalid")
    expected_repository = (
        "docs/experiments/artifacts/uprime_u1_rpc_attempts/" + value.license_id + "/0002.json"
    )
    expected_final = _os_path_join(
        value.root,
        "docs",
        "experiments",
        "artifacts",
        "uprime_u1_rpc_attempts",
        value.license_id,
        "0002.json",
    )
    expected_alias = _os_path_join(
        value.staging_parent,
        "uprime-rpc-attempt-manifest-stage-v1-" + _nonce(value.manifest_nonce, "manifest_nonce") + ".json",
    )
    if (
        value.manifest_repository_path != expected_repository
        or value.manifest_host_final_path != expected_final
        or value.manifest_host_alias_path != expected_alias
    ):
        _fail("recovery manifest path derivation is invalid")
    if type(value.marker) is not SyntheticRecoveryMarkerV10:
        _fail("marker has the wrong record type")
    marker = _reconstruct_marker(value.marker)
    if (
        marker.constructor_profile != value.constructor_profile
        or marker.before_state_version_sha256 != value.initial_state_version_sha256
        or marker.stage_payload_bytes != value.proposed_payload_bytes
        or marker.stage_payload_sha256 != value.proposed_payload_sha256
    ):
        _fail("marker differs from audit cells")
    expected_purpose = (
        "record_recovered_terminal"
        if value.constructor_profile in _PROFILES[:2]
        else "record_permanent_block"
    )
    if value.witness_purpose != expected_purpose:
        _fail("witness_purpose is invalid")
    _hash(value.witness_sha256, "witness_sha256")
    for name in (
        "initial_inventory_projection_sha256",
        "active_chain_projection_sha256",
        "preconsume_snapshot_sha256",
        "preappend_artifact_projection_sha256",
        "terminal_event_sha256",
        "terminal_attestation_projection_sha256",
        "postappend_artifact_projection_sha256",
        "final_inventory_projection_sha256",
        "final_snapshot_sha256",
        "cas_binding_sha256",
        "manifest_binding_sha256",
    ):
        _hash(getattr(value, name), name)
    if type(value.action_trace) is not tuple:
        _fail("action_trace must be an exact tuple")
    expected_count = {
        "ack_loss_confirmed": 4,
        "ack_loss_unavailable_then_confirmed": 6,
        "ack_loss_unavailable_until_budget_block": 10,
        "wrong_delta_confirmed": 4,
    }[value.constructor_profile]
    if _exact_int(value.action_count, "action_count") != expected_count or len(value.action_trace) != expected_count:
        _fail("action_count is invalid")
    for index, trace in enumerate(value.action_trace):
        if type(trace) is not SyntheticCoordinatorActionTraceV10:
            _fail("action trace row has the wrong type")
        _validate_trace_record(trace)
        if index and trace.before_snapshot_sha256 != value.action_trace[index - 1].after_snapshot_sha256:
            _fail("action trace snapshots are not contiguous")
    if value.action_trace[0].operation != "publish" or value.action_trace[-1].operation != "consume_witness":
        _fail("action trace endpoints are invalid")
    expected_operations = {
        "ack_loss_confirmed": ("publish", "acquire_epoch", "replay_epoch", "consume_witness"),
        "ack_loss_unavailable_then_confirmed": (
            "publish", "acquire_epoch", "replay_epoch", "acquire_epoch", "replay_epoch", "consume_witness"
        ),
        "ack_loss_unavailable_until_budget_block": (
            "publish", "acquire_epoch", "replay_epoch", "acquire_epoch", "replay_epoch",
            "acquire_epoch", "replay_epoch", "acquire_epoch", "replay_epoch", "consume_witness"
        ),
        "wrong_delta_confirmed": ("publish", "acquire_epoch", "replay_epoch", "consume_witness"),
    }[value.constructor_profile]
    if tuple(row.operation for row in value.action_trace) != expected_operations:
        _fail("action trace operation schedule is invalid")
    expected_epochs = {
        "ack_loss_confirmed": (None, 1, 1, 1),
        "ack_loss_unavailable_then_confirmed": (None, 1, 1, 2, 2, 2),
        "ack_loss_unavailable_until_budget_block": (
            None, 1, 1, 2, 2, 3, 3, 4, 4, 4
        ),
        "wrong_delta_confirmed": (None, 1, 1, 1),
    }[value.constructor_profile]
    if tuple(row.epoch_ordinal for row in value.action_trace) != expected_epochs:
        _fail("action trace epoch schedule is invalid")
    replay_rows = tuple(row.outcome for row in value.action_trace if row.operation == "replay_epoch")
    expected_replays = {
        "ack_loss_confirmed": ("replay_confirmed_recovered",),
        "ack_loss_unavailable_then_confirmed": (
            "replay_unavailable_retry_pending", "replay_confirmed_recovered"
        ),
        "ack_loss_unavailable_until_budget_block": (
            "replay_unavailable_retry_pending", "replay_unavailable_retry_pending",
            "replay_unavailable_retry_pending", "replay_unavailable_budget_permanent_block"
        ),
        "wrong_delta_confirmed": ("replay_wrong_delta_permanent_block",),
    }[value.constructor_profile]
    if replay_rows != expected_replays:
        _fail("action trace replay schedule is invalid")
    for index, row in enumerate(value.action_trace):
        if row.marker_sha256 != marker.marker_sha256:
            _fail("action trace marker binding is invalid")
        terminal_row = index >= len(value.action_trace) - 2
        if terminal_row:
            if (
                row.terminal_sha256 is None
                or row.terminal_sha256 != value.action_trace[-1].terminal_sha256
                or row.witness_purpose != expected_purpose
            ):
                _fail("terminal trace witness binding is invalid")
        elif row.terminal_sha256 is not None or row.witness_purpose is not None:
            _fail("nonterminal trace carries terminal cells")
    if value.action_trace[-1].outcome != "witness_consumed":
        _fail("witness was not consumed")
    if value.action_trace[-2].after_snapshot_sha256 != value.preconsume_snapshot_sha256:
        _fail("preconsume snapshot is invalid")
    if value.action_trace[-1].before_snapshot_sha256 != value.preconsume_snapshot_sha256:
        _fail("consume before snapshot is invalid")
    if value.action_trace[-1].after_snapshot_sha256 != value.final_snapshot_sha256:
        _fail("final snapshot is invalid")
    live_prefix = "RECOVERED" if expected_purpose == "record_recovered_terminal" else "BLOCKED"
    if value.preconsume_lifecycle_state != live_prefix + "_WITNESS_LIVE":
        _fail("preconsume lifecycle is invalid")
    if value.final_lifecycle_state != live_prefix + "_WITNESS_SPENT":
        _fail("final lifecycle is invalid")
    terminal_reason = value.action_trace[-2].reason_codes[0]
    if value.reason_codes != (terminal_reason,):
        _fail("recovery reason_codes are invalid")
    for row, phase in (
        (value.pre_stage_observation, "pre_publish"),
        (value.preappend_stage_observation, "pre_append"),
        (value.postappend_stage_observation, "post_append"),
    ):
        if type(row) is not SyntheticManifestResidueObservationV10:
            _fail("stage observation has the wrong type")
        _validate_residue_record(row)
        if row.observation_phase != phase:
            _fail("stage observation phase is invalid")
        _validate_nested_stage_binding(row, value)
    if value.pre_stage_observation.observation_state != "absent":
        _fail("pre-publish stage is not absent")
    for row in (value.preappend_stage_observation, value.postappend_stage_observation):
        if row.observation_state != "present" or row.payload_relation != "exact":
            _fail("post-publish stage is not exact")
    if type(value.manifest_append) is not SyntheticTerminalManifestAppendV10:
        _fail("manifest_append has the wrong type")
    _validate_append_record(value.manifest_append)
    if (
        value.manifest_append.license_id != value.license_id
        or value.manifest_append.publisher_collision_nonce != value.publisher_collision_nonce
        or value.manifest_append.manifest_nonce != value.manifest_nonce
        or value.manifest_append.repository_path != value.manifest_repository_path
        or value.manifest_append.host_final_path != value.manifest_host_final_path
        or value.manifest_append.host_alias_path != value.manifest_host_alias_path
        or value.manifest_append.event_sha256 != value.terminal_event_sha256
    ):
        _fail("manifest append differs from audit cells")
    expected_cas = _cas_sha256(
        "recovery",
        value.initial_state_version_sha256,
        value.expected_state_version_sha256,
        value.proposed_payload_bytes,
        value.proposed_payload_sha256,
        value.alternate_payload_bytes,
        value.alternate_payload_sha256,
        marker.publisher_operation_sha256,
        marker.publisher_transition_sha256,
        marker.synthetic_fault_transition_sha256,
        marker.marker_sha256,
    )
    if value.cas_binding_sha256 != expected_cas:
        _fail("recovery cas_binding_sha256 is invalid")
    if value.manifest_binding_sha256 != _manifest_binding_sha256(value):
        _fail("manifest_binding_sha256 is invalid")
    terminal_sha = value.action_trace[-1].terminal_sha256
    if terminal_sha is None or value.manifest_nonce != _manifest_nonce(
        value.terminal_event_sha256, marker.marker_sha256, terminal_sha
    ):
        _fail("manifest_nonce is invalid")
    for name, expected in (
        ("max_seed_claims", 1),
        ("max_chain_events", 2),
        ("max_coordinator_actions", 10),
        ("max_recovery_epochs", 4),
        ("max_artifact_observations", 2),
        ("max_stage_observations", 3),
        ("max_inventory_audits", 2),
        ("max_manifest_appends", 1),
        ("aggregate_dependency_payload_work_upper_bound_bytes", _RECOVERY_AGGREGATE_WORK),
        ("coordinator_payload_reference_upper_bound_bytes", 3_145_728),
        ("proposal_payload_copy_upper_bound_bytes", 0),
    ):
        if _exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    _false(value.canonical_remote_authority, "canonical_remote_authority")
    _require_false_authority(value)
    if _hash(value.audit_sha256, "audit_sha256") != _recovery_audit_sha256(value):
        _fail("recovery audit_sha256 is invalid")


def _validate_common_audit_cells(value: object) -> None:
    root = _exact_str(getattr(value, "root"), "root")
    raw_root = _utf8(root, "root", _MAX_ROOT_BYTES)
    if not raw_root or _CONTROL_RE.search(root) is not None:
        _fail("root is empty or contains C0/DEL")
    try:
        if _os_path_isabs(root) is not True or _os_path_normpath(root) != root:
            _fail("root is not exact normalized absolute text")
    except IntegratedSyntheticManifestV10Error:
        raise
    except Exception:
        _fail("root lexical validation failed")
    if os.name == "nt":
        lowered = root.replace("/", "\\").lower()
        drive, tail = _os_path_splitdrive(root)
        if (
            lowered.startswith("\\\\")
            or lowered.startswith("\\?\\")
            or lowered.startswith("\\.\\")
            or _WINDOWS_DRIVE_RE.fullmatch(drive) is None
            or not tail.startswith(("\\", "/"))
        ):
            _fail("root has invalid Windows spelling")
    _hash(getattr(value, "seed_file_sha256"), "seed_file_sha256")
    _hash(getattr(value, "seed_identity_sha256"), "seed_identity_sha256")
    _lower_hash(getattr(value, "license_id"), "license_id")
    _hash(getattr(value, "claim_receipt_sha256"), "claim_receipt_sha256")
    profile = _exact_str(getattr(value, "constructor_profile"), "constructor_profile")
    if profile not in _PROFILES:
        _fail("constructor_profile is invalid")
    nonce = _nonce(getattr(value, "publisher_collision_nonce"), "publisher_collision_nonce")
    staging_parent = _exact_str(getattr(value, "staging_parent"), "staging_parent")
    stage_basename = _exact_str(getattr(value, "stage_basename"), "stage_basename")
    stage_path = _exact_str(getattr(value, "stage_path"), "stage_path")
    if stage_basename != "uprime-rpc-fake-cas-stage-v1-" + nonce + ".bin":
        _fail("stage_basename is invalid")
    if stage_path != _os_path_join(staging_parent, stage_basename):
        _fail("stage_path is invalid")
    expected_staging = _os_path_join(
        root,
        "docs",
        "experiments",
        "artifacts",
        "uprime_u1_rpc_staging",
        getattr(value, "license_id"),
    )
    if staging_parent != expected_staging:
        _fail("staging_parent is not derived from root")
    proposed_bytes = _exact_int(getattr(value, "proposed_payload_bytes"), "proposed_payload_bytes")
    if not 0 <= proposed_bytes <= _MAX_PAYLOAD_BYTES:
        _fail("proposed_payload_bytes is outside bounds")
    _hash(getattr(value, "proposed_payload_sha256"), "proposed_payload_sha256")
    alternate_bytes = getattr(value, "alternate_payload_bytes")
    alternate_sha = getattr(value, "alternate_payload_sha256")
    if profile == "wrong_delta_confirmed":
        if type(alternate_bytes) is not int or not 0 <= alternate_bytes <= _MAX_PAYLOAD_BYTES:
            _fail("alternate_payload_bytes is invalid")
        _hash(alternate_sha, "alternate_payload_sha256")
    elif alternate_bytes is not None or alternate_sha is not None:
        _fail("alternate payload cells must be null")
    _hash(getattr(value, "initial_state_version_sha256"), "initial_state_version_sha256")
    expected_nonce = _publisher_nonce(
        getattr(value, "seed_identity_sha256"),
        profile,
        proposed_bytes,
        getattr(value, "proposed_payload_sha256"),
        alternate_bytes,
        alternate_sha,
    )
    if nonce != expected_nonce:
        _fail("publisher_collision_nonce is invalid")


def _validate_inputs(
    root: object,
    seed_raw: object,
    constructor_profile: object,
    alternate_payload: object,
    proposed_payload: object,
) -> tuple[str, bytes, str, bytes | None, bytes]:
    root_text = _exact_str(root, "root")
    raw_root = _utf8(root_text, "root", _MAX_ROOT_BYTES)
    if not raw_root or _CONTROL_RE.search(root_text) is not None:
        _fail("root is empty or contains C0/DEL")
    try:
        absolute = _os_path_isabs(root_text)
        normalized = _os_path_normpath(root_text)
    except Exception:
        _fail("root lexical validation failed")
    if absolute is not True or type(normalized) is not str or normalized != root_text:
        _fail("root is not exact normalized absolute text")
    if os.name == "nt":
        lowered = root_text.replace("/", "\\").lower()
        if lowered.startswith("\\\\") or lowered.startswith("\\?\\") or lowered.startswith("\\.\\"):
            _fail("UNC and device roots are forbidden")
        drive, tail = _os_path_splitdrive(root_text)
        if _WINDOWS_DRIVE_RE.fullmatch(drive) is None or not tail.startswith(("\\", "/")):
            _fail("root lacks an explicit Windows drive root")
    raw_seed = _exact_bytes(seed_raw, "seed_raw")
    profile = _exact_str(constructor_profile, "constructor_profile")
    if profile not in _PROFILES:
        _fail("constructor_profile is invalid")
    proposal = _exact_bytes(proposed_payload, "proposed_payload")
    if len(proposal) > _MAX_PAYLOAD_BYTES:
        _fail("proposed_payload exceeds its byte limit")
    if profile == "wrong_delta_confirmed":
        alternate = _exact_bytes(alternate_payload, "alternate_payload")
        if len(alternate) > _MAX_PAYLOAD_BYTES or alternate == proposal:
            _fail("wrong-delta alternate payload is invalid")
    else:
        if alternate_payload is not None:
            _fail("alternate_payload must be null for this profile")
        alternate = None
    return root_text, raw_seed, profile, alternate, proposal


@dataclasses.dataclass(frozen=True, slots=True)
class _PathPlan:
    root: str
    license_id: str
    attempt_directory: str
    staging_parent: str
    publisher_nonce: str
    stage_basename: str
    stage_path: str
    manifest_repository_path: str
    manifest_final_path: str


def _early_path_plan(root: str, license_id: str, publisher_nonce: str) -> _PathPlan:
    attempt = _os_path_join(
        root, "docs", "experiments", "artifacts", "uprime_u1_rpc_attempts", license_id
    )
    staging = _os_path_join(
        root, "docs", "experiments", "artifacts", "uprime_u1_rpc_staging", license_id
    )
    basename = "uprime-rpc-fake-cas-stage-v1-" + publisher_nonce + ".bin"
    stage_path = _os_path_join(staging, basename)
    repository = "docs/experiments/artifacts/uprime_u1_rpc_attempts/" + license_id + "/0002.json"
    final_path = _os_path_join(attempt, "0002.json")
    for name, path, maximum in (
        ("attempt_directory", attempt, _MAX_MANIFEST_HOST_PATH_BYTES),
        ("staging_parent", staging, _MAX_STAGING_PARENT_BYTES),
        ("stage_path", stage_path, _MAX_STAGE_PATH_BYTES),
        ("manifest_final_path", final_path, _MAX_MANIFEST_HOST_PATH_BYTES),
    ):
        _utf8(path, name, maximum)
        if _os_path_normpath(path) != path:
            _fail(f"{name} is not normalized")
    _utf8(repository, "manifest_repository_path", _MAX_MANIFEST_HOST_PATH_BYTES)
    return _PathPlan(root, license_id, attempt, staging, publisher_nonce, basename, stage_path, repository, final_path)


def _late_alias_path(plan: _PathPlan, manifest_nonce: str) -> str:
    alias = _os_path_join(
        plan.staging_parent,
        "uprime-rpc-attempt-manifest-stage-v1-" + manifest_nonce + ".json",
    )
    _utf8(alias, "manifest_host_alias_path", _MAX_MANIFEST_HOST_PATH_BYTES)
    if _os_path_normpath(alias) != alias:
        _fail("manifest_host_alias_path is not normalized")
    return alias


def _copy_dataclass(record_type: type, value: object, name: str) -> object:
    if type(value) is not record_type:
        _fail(f"{name} has the wrong exact type")
    try:
        copied = record_type(*(getattr(value, field.name) for field in dataclasses.fields(record_type)))
    except BaseException as error:
        if isinstance(error, Exception):
            _fail(f"{name} does not reconstruct")
        raise
    if copied != value:
        _fail(f"{name} differs from its reconstruction")
    return copied


def _reconstruct_receipt(value: object) -> PublicClaimReceiptV10:
    return _copy_dataclass(PublicClaimReceiptV10, value, "claim receipt")


def _reconstruct_state(value: object) -> InMemoryFakeCasStateV10:
    return _copy_dataclass(InMemoryFakeCasStateV10, value, "CAS state")


def _reconstruct_transition(value: object) -> InMemoryFakeCasTransitionV10:
    if type(value) is not InMemoryFakeCasTransitionV10:
        _fail("CAS transition has the wrong exact type")
    before = _reconstruct_state(value.before_state)
    if type(value.state_changed) is not bool:
        _fail("CAS transition state_changed has the wrong exact type")
    if not value.state_changed:
        if value.after_state is not value.before_state:
            _fail("no-change CAS transition does not retain one State object")
        after = before
    else:
        after = _reconstruct_state(value.after_state)
    values = [getattr(value, field.name) for field in dataclasses.fields(InMemoryFakeCasTransitionV10)]
    values[3] = before
    values[4] = after
    copied = InMemoryFakeCasTransitionV10(*values)
    if copied != value:
        _fail("CAS transition differs from its reconstruction")
    return copied


def _reconstruct_publish_result(value: object) -> LocalStagingFakePublishResultV10:
    if type(value) is not LocalStagingFakePublishResultV10:
        _fail("publisher Result has the wrong exact type")
    transition = _reconstruct_transition(value.cas_transition)
    values = [getattr(value, field.name) for field in dataclasses.fields(LocalStagingFakePublishResultV10)]
    values[7] = transition
    copied = LocalStagingFakePublishResultV10(*values)
    if copied != value:
        _fail("publisher Result differs from its reconstruction")
    return copied


def _reconstruct_marker(value: object) -> SyntheticRecoveryMarkerV10:
    return _copy_dataclass(SyntheticRecoveryMarkerV10, value, "recovery marker")


def _reconstruct_snapshot(value: object) -> SyntheticRecoverySnapshotV10:
    if type(value) is not SyntheticRecoverySnapshotV10:
        _fail("recovery snapshot has the wrong exact type")
    marker = None if value.marker is None else _reconstruct_marker(value.marker)
    values = [getattr(value, field.name) for field in dataclasses.fields(SyntheticRecoverySnapshotV10)]
    values[9] = marker
    copied = SyntheticRecoverySnapshotV10(*values)
    if copied != value:
        _fail("recovery snapshot differs from its reconstruction")
    return copied


def _reconstruct_action(value: object) -> SyntheticRecoveryActionV10:
    if type(value) is not SyntheticRecoveryActionV10:
        _fail("recovery Action has the wrong exact type")
    after = _reconstruct_snapshot(value.after_snapshot)
    result = None if value.publish_result is None else _reconstruct_publish_result(value.publish_result)
    marker = None if value.marker is None else _reconstruct_marker(value.marker)
    if value.issued_epoch is not None and type(value.issued_epoch) is not SyntheticRecoveryEpochV10:
        _fail("issued_epoch has the wrong exact type")
    if value.issued_witness is not None and type(value.issued_witness) is not SyntheticRecoveryWitnessV10:
        _fail("issued_witness has the wrong exact type")
    values = [getattr(value, field.name) for field in dataclasses.fields(SyntheticRecoveryActionV10)]
    values[7] = after
    values[9] = result
    values[10] = marker
    copied = SyntheticRecoveryActionV10(*values)
    if copied != value:
        _fail("recovery Action differs from its reconstruction")
    return copied


def _validate_seed(raw: bytes, value: object) -> tuple[SyntheticClaimSeedV10, PublicClaimReceiptV10]:
    if type(value) is not SyntheticClaimSeedV10:
        _fail("seed parser returned the wrong exact type")
    receipt_values = value.claim_receipts
    if type(receipt_values) is not tuple or len(receipt_values) != 1:
        _fail("seed must contain exactly one receipt")
    receipt = _reconstruct_receipt(receipt_values[0])
    expected_seed_file = _raw_sha(raw)
    expected_seed_identity = _sha(
        b"lean-rgc-uprime-u1-synthetic-claim-seed-v1\0" + _u64(len(raw)) + raw
    )
    expected = (
        ("schema_version", "lean-rgc-uprime-u1-synthetic-claim-seed-v1.0"),
        ("seed_scope", "caller_supplied_synthetic_claims_only"),
        ("origin_status", _ORIGIN_STATUS),
        ("seed_file_sha256", expected_seed_file),
        ("seed_identity_sha256", expected_seed_identity),
        ("inventory_completeness", "not_authenticated_may_omit_claims"),
        ("omitted_claim_detectability", "none_outside_supplied_seed"),
        ("remote_inventory_observation", "not_performed"),
        ("seed_temporal_commitment", "not_authenticated"),
        ("authority_scope", "none"),
    )
    _require_static_strings(value, expected)
    if _exact_int(value.seed_bytes, "seed_bytes") != len(raw) or _exact_int(value.claim_count, "claim_count") != 1:
        _fail("seed counts are invalid")
    for name in ("licenses_execution", "licenses_publication", "licenses_later_stage"):
        _false(getattr(value, name), name)
    copied = SyntheticClaimSeedV10(
        value.schema_version,
        value.seed_scope,
        value.origin_status,
        value.seed_file_sha256,
        value.seed_identity_sha256,
        value.seed_bytes,
        (receipt,),
        value.claim_count,
        value.inventory_completeness,
        value.omitted_claim_detectability,
        value.remote_inventory_observation,
        value.seed_temporal_commitment,
        value.authority_scope,
        value.licenses_execution,
        value.licenses_publication,
        value.licenses_later_stage,
    )
    if copied != value:
        _fail("seed differs from its reconstruction")
    return copied, receipt


def _stat_int(value: object, name: str) -> int:
    try:
        result = getattr(value, name)
    except Exception:
        _fail(f"{name} is unavailable")
    number = _exact_int(result, name)
    if number < 0:
        _fail(f"{name} is negative")
    return number


def _is_reparse(value: object, mode: int) -> bool:
    try:
        attributes = getattr(value, "st_file_attributes")
    except AttributeError:
        attributes = 0
    except Exception:
        _fail("st_file_attributes is unreadable")
    attributes = _exact_int(attributes, "st_file_attributes")
    if attributes < 0:
        _fail("st_file_attributes is negative")
    return stat.S_ISLNK(mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _directory_snapshot(value: object, name: str) -> tuple[int, int, int, bool, int, int]:
    device = _stat_int(value, "st_dev")
    inode = _stat_int(value, "st_ino")
    mode = _stat_int(value, "st_mode")
    reparse = _is_reparse(value, mode)
    ctime = _stat_int(value, "st_ctime_ns")
    mtime = _stat_int(value, "st_mtime_ns")
    if reparse or not stat.S_ISDIR(mode):
        _fail(f"{name} is not a real non-reparse directory")
    return device, inode, mode, reparse, ctime, mtime


def _file_snapshot(value: object, name: str) -> tuple[int, int, int, bool, int, int, int]:
    device = _stat_int(value, "st_dev")
    inode = _stat_int(value, "st_ino")
    mode = _stat_int(value, "st_mode")
    reparse = _is_reparse(value, mode)
    ctime = _stat_int(value, "st_ctime_ns")
    size = _stat_int(value, "st_size")
    mtime = _stat_int(value, "st_mtime_ns")
    if reparse or not stat.S_ISREG(mode):
        _fail(f"{name} is not a real non-reparse regular file")
    return device, inode, mode, reparse, ctime, size, mtime


def _nofollow_stat(path: str) -> object:
    return _os_stat(path, follow_symlinks=False)


def _stable_directory_pair(plan: _PathPlan) -> tuple[tuple[int, int, int, bool, int, int], tuple[int, int, int, bool, int, int]]:
    try:
        attempt0 = _directory_snapshot(_nofollow_stat(plan.attempt_directory), "attempt directory")
        staging0 = _directory_snapshot(_nofollow_stat(plan.staging_parent), "staging parent")
        attempt1 = _directory_snapshot(_nofollow_stat(plan.attempt_directory), "attempt directory")
        staging1 = _directory_snapshot(_nofollow_stat(plan.staging_parent), "staging parent")
    except BaseException as error:
        if isinstance(error, Exception):
            _fail("directory preflight failed")
        raise
    if attempt0 != attempt1 or staging0 != staging1:
        _fail("directory metadata drifted during preflight")
    if attempt0[0] != staging0[0]:
        _fail("attempt and staging parents are on different devices")
    return attempt0, staging0


def _accepted_inventory_projection(
    value: object,
    seed: SyntheticClaimSeedV10,
    receipt: PublicClaimReceiptV10,
    terminal: bool,
) -> tuple[SyntheticSeedLocalInventoryAuditV10, str, SyntheticLocalClaimAuditV10]:
    if type(value) is not SyntheticSeedLocalInventoryAuditV10:
        _fail("inventory audit has the wrong exact type")
    if type(value.claim_audits) is not tuple or len(value.claim_audits) != 1:
        _fail("inventory must contain one claim audit")
    claim = value.claim_audits[0]
    if type(claim) is not SyntheticLocalClaimAuditV10:
        _fail("inventory claim audit has the wrong exact type")
    _require_static_strings(
        value,
        (
            ("auditor_schema_version", "lean-rgc-uprime-u1-seed-local-inventory-auditor-v0.1"),
            ("auditor_scope", "caller_seed_vs_entire_local_attempt_namespace"),
            ("origin_status", _ORIGIN_STATUS),
            ("base_directory_status", "present"),
            ("seed_file_sha256", seed.seed_file_sha256),
            ("seed_identity_sha256", seed.seed_identity_sha256),
            ("coverage_status", "matched_terminal" if terminal else "mismatched"),
            ("seed_origin", "caller_supplied_synthetic_bytes"),
            ("seed_binding", "exact_bytes_within_call"),
            ("seed_temporal_commitment", "not_authenticated"),
            ("remote_inventory_observation", "not_performed"),
            ("real_claim_completeness", "not_authenticated"),
            ("omitted_claim_detectability", "local_orphans_only_none_if_absent_from_both"),
            ("coordinated_omission_detectability", "none"),
            ("root_scope", "one_caller_supplied_synthetic_root"),
            ("snapshot_scope", "sequential_per_claim_observations_not_atomic_inventory"),
            ("resource_status", "within_frozen_bounds"),
            ("authority_scope", "none"),
        ),
    )
    for name in ("seed_count", "local_directory_count", "union_claim_count", "examined_claim_count"):
        if _exact_int(getattr(value, name), name) != 1:
            _fail(f"inventory {name} is invalid")
    total_bytes = _exact_int(value.total_observed_event_bytes, "total_observed_event_bytes")
    if total_bytes <= 0 or total_bytes > 67_108_864:
        _fail("inventory total event bytes is invalid")
    if _exact_int(value.read_work_upper_bound_bytes, "read_work_upper_bound_bytes") != 268_435_457:
        _fail("inventory read-work bound is invalid")
    if _exact_int(value.event_file_admission_upper_bound, "event_file_admission_upper_bound") != 159_984:
        _fail("inventory admission bound is invalid")
    empty_tuples = (
        "unexpected_entry_names",
        "seeded_missing_ids",
        "local_orphan_ids",
        "receipt_mismatch_ids",
        "empty_chain_ids",
    )
    for name in empty_tuples:
        if getattr(value, name) != () or type(getattr(value, name)) is not tuple:
            _fail(f"inventory {name} is invalid")
    if _exact_int(value.unexpected_entry_count, "unexpected_entry_count") != 0:
        _fail("inventory unexpected entry count is invalid")
    expected_terminal_ids = (receipt.license_id,) if terminal else ()
    expected_nonterminal_ids = () if terminal else (receipt.license_id,)
    if value.terminal_ids != expected_terminal_ids or value.nonterminal_ids != expected_nonterminal_ids:
        _fail("inventory terminal partition is invalid")
    booleans = {
        "set_equality": True,
        "all_seeded_local_present": True,
        "all_seeded_terminal": terminal,
        "all_seeded_receipts_match": True,
    }
    for name, expected in booleans.items():
        if _exact_bool(getattr(value, name), name) is not expected:
            _fail(f"inventory {name} is invalid")
    _require_static_strings(
        claim,
        (
            ("license_id", receipt.license_id),
            ("set_relation", "seed_and_local"),
            ("receipt_relation", "exact_match"),
            ("chain_observation", "valid_terminal" if terminal else "valid_nonterminal"),
            ("authority_scope", "none"),
        ),
    )
    if not _exact_bool(claim.seed_membership, "seed_membership") or not _exact_bool(claim.local_membership, "local_membership"):
        _fail("inventory membership is invalid")
    for name in ("seed_receipt_sha256", "local_receipt_sha256", "last_event_sha256"):
        _hash(getattr(claim, name), name)
    if claim.seed_receipt_sha256 != claim.local_receipt_sha256:
        _fail("inventory receipt hashes differ")
    expected_count = 2 if terminal else 1
    if claim.event_count != expected_count or claim.last_event_index != expected_count:
        _fail("inventory claim endpoint is invalid")
    if _exact_bool(claim.terminal_event, "terminal_event") is not terminal or claim.recorded_verdict is not None:
        _fail("inventory claim terminal cells are invalid")
    for name in ("licenses_execution", "licenses_later_stage"):
        _false(getattr(claim, name), name)
    _false(value.canonical_run_authority, "canonical_run_authority")
    _require_false_authority(value)
    projection = _inventory_sha256(value)
    return value, projection, claim


def _accepted_active_chain_projection(
    value: object,
    receipt: PublicClaimReceiptV10,
    claim_receipt_sha256: str,
) -> tuple[AttemptManifestChainInspectionV10, AttemptManifestEventFileV10, str]:
    if type(value) is not AttemptManifestChainInspectionV10:
        _fail("active chain inspection has the wrong exact type")
    _require_static_strings(
        value,
        (
            ("inspector_schema_version", "lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1"),
            ("inspector_scope", "local_preartifact_chain_structure_only"),
            ("origin_status", _ORIGIN_STATUS),
            ("license_id", receipt.license_id),
            ("chain_state", "valid_nonterminal"),
            ("last_event_type", "claim_started"),
        ),
    )
    if type(value.event_files) is not tuple or len(value.event_files) != 1:
        _fail("active chain must contain one event file")
    if value.event_count != 1 or value.last_event_index != 1 or value.next_event_index != 2:
        _fail("active chain indexes are invalid")
    if value.terminal_event is not False or type(value.terminal_event) is not bool or value.recorded_verdict is not None:
        _fail("active chain terminal cells are invalid")
    if value.first_event_sha256 != value.last_event_sha256:
        _fail("active chain endpoint digests differ")
    _hash(value.first_event_sha256, "first_event_sha256")
    if value.claim_receipt != receipt or value.claim_receipt_sha256 != claim_receipt_sha256:
        _fail("active chain receipt differs from inventory")
    file_value = value.event_files[0]
    if type(file_value) is not AttemptManifestEventFileV10:
        _fail("active event file has the wrong exact type")
    expected_repository = (
        "docs/experiments/artifacts/uprime_u1_rpc_attempts/" + receipt.license_id + "/0001.json"
    )
    if file_value.repository_path != expected_repository:
        _fail("active event repository path is invalid")
    raw = _exact_bytes(file_value.event_bytes, "index1 event bytes")
    if not raw or len(raw) > _MAX_PAYLOAD_BYTES or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail("index1 event bytes are not canonical LF-terminated bytes")
    if _hash(file_value.event_sha256, "index1 event_sha256") != _raw_sha(raw):
        _fail("index1 event_sha256 is invalid")
    if file_value.event_sha256 != value.first_event_sha256:
        _fail("active event digest differs from chain endpoint")
    parsed = _dep_parse_event_file(expected_repository, raw)
    if type(parsed) is not AttemptManifestEventFileV10 or parsed != file_value:
        _fail("index1 event does not pure-parse byte-identically")
    event = file_value.event
    if type(event) is not AttemptManifestEventV10:
        _fail("index1 event has the wrong exact type")
    reconstructed_event = _copy_dataclass(AttemptManifestEventV10, event, "index1 event")
    if reconstructed_event != event:
        _fail("index1 event differs from reconstruction")
    if (
        event.event_type != "claim_started"
        or event.event_index != 1
        or event.prior_event_sha256 is not None
        or event.terminal_event
        or event.failure_codes != ()
        or event.claim_receipt != receipt
        or event.claim_receipt_sha256 != claim_receipt_sha256
    ):
        _fail("index1 claim_started event mapping is invalid")
    projection = _active_chain_sha256(value, file_value)
    return value, file_value, projection


def _accepted_artifact_projection(
    value: object,
    receipt: PublicClaimReceiptV10,
    receipt_sha256: str,
) -> tuple[LocalArtifactSetObservationV10, str]:
    if type(value) is not LocalArtifactSetObservationV10:
        _fail("artifact observation has the wrong exact type")
    copied = _copy_dataclass(LocalArtifactSetObservationV10, value, "artifact observation")
    if copied.claim_receipt != receipt or copied.claim_receipt_sha256 != receipt_sha256:
        _fail("artifact receipt binding is invalid")
    if copied.state_vector != ("absent", "absent", "absent"):
        _fail("artifact state vector is not exact all-absent")
    if (
        copied.present_count != 0
        or copied.absent_count != 3
        or copied.indeterminate_count != 0
        or copied.total_present_bytes != 0
    ):
        _fail("artifact aggregate is not exact all-absent")
    if copied.parent_namespace_state not in ("present", "absent"):
        _fail("artifact parent is not an admissible determinate endpoint")
    expected_parent_reason = (
        ("stable_parent_directory",)
        if copied.parent_namespace_state == "present"
        else ("stable_parent_absence",)
    )
    if copied.parent_reason_codes != expected_parent_reason:
        _fail("artifact parent reason is invalid")
    for row in (copied.reservation, copied.ledger, copied.report):
        if row.observation_state != "absent" or row.artifact_sha256 is not None or row.artifact_bytes is not None:
            _fail("artifact row is not absent")
        expected_reason = (
            ("absent_at_both_points",)
            if copied.parent_namespace_state == "present"
            else ("stable_parent_absence",)
        )
        if row.reason_codes != expected_reason:
            _fail("artifact absent reason is invalid")
    return copied, _artifact_sha256(copied)


def _accepted_terminal_attestation_projection(
    value: object,
    receipt: PublicClaimReceiptV10,
    receipt_sha256: str,
    first_event_sha256: str,
    terminal_event_sha256: str,
    failure_codes: tuple[str, ...],
) -> tuple[AttemptManifestChainAttestationV10, str]:
    if type(value) is not AttemptManifestChainAttestationV10:
        _fail("terminal attestation has the wrong exact type")
    _require_static_strings(
        value,
        (
            ("verifier_schema_version", "lean-rgc-uprime-u1-local-attempt-chain-verifier-v0.1"),
            ("verifier_scope", "local_preartifact_chain_structure_only"),
            ("origin_status", _ORIGIN_STATUS),
            ("license_id", receipt.license_id),
            ("candidate_commit", receipt.candidate_commit),
            ("license_commit", receipt.license_commit),
            ("remote_claim_ref", receipt.remote_claim_ref),
            ("claim_receipt_sha256", receipt_sha256),
            ("first_event_sha256", first_event_sha256),
            ("last_event_sha256", terminal_event_sha256),
            ("chain_state", "valid_terminal"),
            ("last_event_type", "recovery"),
            ("artifact_observation", "not_performed"),
            ("remote_claim_authentication", "not_performed"),
            ("git_object_authentication", "not_performed"),
            ("real_remote_publication", "not_performed"),
            ("claim_once_authentication", "not_performed"),
            ("reservation_token_verification", "not_performed"),
            ("artifact_binding", "not_performed"),
            ("verifier_binding", "not_performed"),
            ("scanner_binding", "not_performed"),
            ("privacy_scan", "not_performed"),
            ("archive_verification", "not_performed"),
            ("authority_scope", "none"),
        ),
    )
    if value.event_count != 2 or value.last_event_index != 2:
        _fail("terminal attestation indexes are invalid")
    if type(value.terminal_event) is not bool or not value.terminal_event:
        _fail("terminal attestation is not terminal")
    if value.recorded_verdict is not None or value.failure_codes != failure_codes:
        _fail("terminal attestation result cells are invalid")
    if type(value.preartifact_profile) is not bool or not value.preartifact_profile:
        _fail("terminal attestation profile is invalid")
    _false(value.canonical_run_authority, "canonical_run_authority")
    _false(value.licenses_execution, "licenses_execution")
    _false(value.licenses_later_stage, "licenses_later_stage")
    copied = AttemptManifestChainAttestationV10(
        *(getattr(value, field.name) for field in dataclasses.fields(AttemptManifestChainAttestationV10))
    )
    if copied != value:
        _fail("terminal attestation differs from reconstruction")
    return copied, _terminal_attestation_sha256(copied)


def _trace_from_action(value: object) -> tuple[SyntheticRecoveryActionV10, SyntheticCoordinatorActionTraceV10]:
    action = _reconstruct_action(value)
    result = action.publish_result
    publisher_operation = result.operation_sha256 if result is not None else None
    publisher_transition = result.cas_transition.transition_sha256 if result is not None else None
    marker_sha = action.marker.marker_sha256 if action.marker is not None else None
    trace = SyntheticCoordinatorActionTraceV10(
        trace_schema_version=_TRACE_SCHEMA,
        trace_scope=_TRACE_SCOPE,
        origin_status=_ORIGIN_STATUS,
        operation=action.operation,
        outcome=action.outcome,
        reason_codes=action.reason_codes,
        action_sha256=action.action_sha256,
        before_snapshot_sha256=action.before_snapshot_sha256,
        after_snapshot_sha256=action.after_snapshot.snapshot_sha256,
        endpoint_state_changed=action.endpoint_state_changed,
        publisher_operation_sha256=publisher_operation,
        publisher_transition_sha256=publisher_transition,
        marker_sha256=marker_sha,
        epoch_ordinal=action.epoch_ordinal,
        replay_observation=action.replay_observation,
        terminal_sha256=action.terminal_sha256,
        witness_purpose=action.after_snapshot.witness_purpose,
        detached_record_scope=_DETACHED_SCOPE,
        authority_scope=_AUTHORITY_SCOPE,
        licenses_execution=False,
        licenses_publication=False,
        licenses_recovery=False,
        licenses_later_stage=False,
    )
    return action, trace


def _residue_digest(
    phase: str,
    staging_parent: str,
    collision_nonce: str,
    stage_basename: str,
    stage_path: str,
    expected_payload_bytes: int,
    expected_payload_sha256: str,
    parent_state: str,
    parent_reasons: tuple[str, ...],
    observation_state: str,
    reasons: tuple[str, ...],
    observed_bytes: int | None,
    observed_sha256: str | None,
    relation: str,
) -> str:
    return _sha(
        _D_RESIDUE
        + _k(phase)
        + _p(staging_parent)
        + _n(collision_nonce)
        + _k(stage_basename)
        + _p(stage_path)
        + _u64(expected_payload_bytes)
        + _h(expected_payload_sha256)
        + _k(parent_state)
        + _t(parent_reasons)
        + _k(observation_state)
        + _t(reasons)
        + _j(observed_bytes)
        + _q(observed_sha256)
        + _k(relation)
    )


def _make_residue(
    plan: _PathPlan,
    proposal: bytes,
    phase: str,
    parent_state: str,
    parent_reasons: tuple[str, ...],
    observation_state: str,
    reasons: tuple[str, ...],
    observed_bytes: int | None,
    observed_sha256: str | None,
    relation: str,
) -> SyntheticManifestResidueObservationV10:
    expected_sha = _raw_sha(proposal)
    digest = _residue_digest(
        phase,
        plan.staging_parent,
        plan.publisher_nonce,
        plan.stage_basename,
        plan.stage_path,
        len(proposal),
        expected_sha,
        parent_state,
        parent_reasons,
        observation_state,
        reasons,
        observed_bytes,
        observed_sha256,
        relation,
    )
    return SyntheticManifestResidueObservationV10(
        _OBSERVATION_SCHEMA,
        _OBSERVATION_SCOPE,
        _ORIGIN_STATUS,
        phase,
        plan.staging_parent,
        plan.publisher_nonce,
        plan.stage_basename,
        plan.stage_path,
        len(proposal),
        expected_sha,
        parent_state,
        parent_reasons,
        observation_state,
        reasons,
        observed_bytes,
        observed_sha256,
        relation,
        digest,
        _MAX_PAYLOAD_BYTES,
        _MAX_STAGING_PARENT_BYTES,
        _MAX_STAGE_PATH_BYTES,
        _IO_CHUNK_BYTES,
        _OBS_READ_CALL_BOUND,
        _OBS_WORK_BOUND,
        _IO_CHUNK_BYTES,
        0,
        _PATH_DERIVATION_SCOPE,
        _NOFOLLOW_SCOPE,
        _ANCESTOR_REPARSE_SCOPE,
        _BACKING_STORE_SCOPE,
        _SNAPSHOT_SCOPE,
        _STAGE_ATTRIBUTION_SCOPE,
        _CLEANUP_SCOPE,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )


def _classify_directory_metadata(value: object) -> tuple[tuple[int, int, int, bool, int, int] | None, str | None]:
    try:
        device = _stat_int(value, "st_dev")
        inode = _stat_int(value, "st_ino")
        mode = _stat_int(value, "st_mode")
        reparse = _is_reparse(value, mode)
        ctime = _stat_int(value, "st_ctime_ns")
        mtime = _stat_int(value, "st_mtime_ns")
    except IntegratedSyntheticManifestV10Error:
        return None, "parent_metadata_invalid"
    if reparse:
        return None, "parent_reparse_entry"
    if not stat.S_ISDIR(mode):
        return None, "parent_nondirectory"
    return (device, inode, mode, reparse, ctime, mtime), None


def _classify_file_metadata(
    value: object,
    *,
    descriptor: bool,
) -> tuple[tuple[int, int, int, bool, int, int, int] | None, str | None]:
    try:
        device = _stat_int(value, "st_dev")
        inode = _stat_int(value, "st_ino")
        mode = _stat_int(value, "st_mode")
        reparse = _is_reparse(value, mode)
        ctime = _stat_int(value, "st_ctime_ns")
        size = _stat_int(value, "st_size")
        mtime = _stat_int(value, "st_mtime_ns")
    except IntegratedSyntheticManifestV10Error:
        return None, "descriptor_metadata_invalid" if descriptor else "metadata_invalid"
    if reparse:
        return None, "descriptor_metadata_invalid" if descriptor else "reparse_entry"
    if not stat.S_ISREG(mode):
        return None, "descriptor_nonregular" if descriptor else "nonregular_entry"
    return (device, inode, mode, reparse, ctime, size, mtime), None


def _read_stage_pass(fd: int, size: int, proposal: bytes) -> tuple[str | None, str | None, bool]:
    try:
        seek_result = _os_lseek(fd, 0, os.SEEK_SET)
    except Exception:
        return "seek_error", None, False
    if type(seek_result) is not int or seek_result != 0:
        return "seek_error", None, False
    digest = hashlib.sha256()
    offset = 0
    raw_equal = size == len(proposal)
    while offset < size:
        request = min(_IO_CHUNK_BYTES, size - offset)
        try:
            chunk = _os_read(fd, request)
        except Exception:
            return "read_error", None, False
        if type(chunk) is not bytes or len(chunk) != request:
            return "short_read", None, False
        if chunk != proposal[offset : offset + request]:
            raw_equal = False
        digest.update(chunk)
        offset += request
    try:
        eof = _os_read(fd, 1)
    except Exception:
        return "read_error", None, False
    if type(eof) is not bytes or eof != b"":
        return "unexpected_eof_relation", None, False
    return None, digest.hexdigest().upper(), raw_equal


def _observe_stage_residue(
    plan: _PathPlan,
    proposal: bytes,
    phase: str,
    /,
) -> SyntheticManifestResidueObservationV10:
    try:
        parent_initial_raw = _nofollow_stat(plan.staging_parent)
    except FileNotFoundError:
        try:
            _nofollow_stat(plan.staging_parent)
        except FileNotFoundError:
            return _make_residue(
                plan,
                proposal,
                phase,
                "absent",
                ("stable_parent_absence",),
                "absent",
                ("stable_parent_absence",),
                None,
                None,
                "not_present",
            )
        except Exception:
            parent_reason = "parent_absence_recheck_error"
        else:
            parent_reason = "parent_absence_changed"
        return _make_residue(
            plan, proposal, phase, "indeterminate", (parent_reason,), "indeterminate", (parent_reason,), None, None, "indeterminate"
        )
    except Exception:
        return _make_residue(
            plan,
            proposal,
            phase,
            "indeterminate",
            ("parent_initial_stat_error",),
            "indeterminate",
            ("parent_initial_stat_error",),
            None,
            None,
            "indeterminate",
        )
    parent0, parent_error = _classify_directory_metadata(parent_initial_raw)
    if parent_error is not None:
        return _make_residue(
            plan, proposal, phase, "indeterminate", (parent_error,), "indeterminate", (parent_error,), None, None, "indeterminate"
        )

    child_state = "indeterminate"
    child_reason = "initial_stat_error"
    observed_bytes: int | None = None
    observed_sha: str | None = None
    relation = "indeterminate"
    try:
        initial_path_raw = _nofollow_stat(plan.stage_path)
    except FileNotFoundError:
        try:
            _nofollow_stat(plan.stage_path)
        except FileNotFoundError:
            child_state = "absent"
            child_reason = "absent_at_both_points"
            relation = "not_present"
        except Exception:
            child_reason = "absence_recheck_error"
        else:
            child_reason = "absence_changed"
    except Exception:
        child_reason = "initial_stat_error"
    else:
        path0, path_error = _classify_file_metadata(initial_path_raw, descriptor=False)
        if path_error is not None:
            child_reason = path_error
        elif path0 is None:
            child_reason = "metadata_invalid"
        elif path0[5] > _MAX_PAYLOAD_BYTES:
            child_reason = "size_limit_exceeded"
        else:
            fd: int | None = None
            primary_reason: str | None = None
            primary_base: BaseException | None = None
            pass_sha: str | None = None
            raw_equal = False
            descriptor_final: tuple[int, int, int, bool, int, int, int] | None = None
            try:
                flags = os.O_RDONLY
                for flag_name in ("O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_NOFOLLOW"):
                    flags |= int(getattr(os, flag_name, 0))
                try:
                    opened = _os_open(plan.stage_path, flags)
                except Exception:
                    primary_reason = "open_error"
                else:
                    if type(opened) is not int or opened < 0:
                        primary_reason = "open_error"
                    else:
                        fd = opened
                if primary_reason is None and fd is not None:
                    try:
                        descriptor_raw = _os_fstat(fd)
                    except Exception:
                        primary_reason = "descriptor_metadata_invalid"
                    else:
                        descriptor0, descriptor_error = _classify_file_metadata(descriptor_raw, descriptor=True)
                        if descriptor_error is not None:
                            primary_reason = descriptor_error
                        elif descriptor0 is None:
                            primary_reason = "descriptor_metadata_invalid"
                        elif (descriptor0[0], descriptor0[1], stat.S_IFMT(descriptor0[2]), descriptor0[5]) != (
                            path0[0], path0[1], stat.S_IFMT(path0[2]), path0[5]
                        ):
                            primary_reason = "descriptor_path_mismatch"
                if primary_reason is None and fd is not None and descriptor0 is not None:
                    reason1, sha1, equal1 = _read_stage_pass(fd, descriptor0[5], proposal)
                    if reason1 is not None:
                        primary_reason = reason1
                    else:
                        try:
                            middle_raw = _os_fstat(fd)
                        except Exception:
                            primary_reason = "descriptor_metadata_invalid"
                        else:
                            middle, middle_error = _classify_file_metadata(middle_raw, descriptor=True)
                            if middle_error is not None:
                                primary_reason = middle_error
                            elif middle != descriptor0:
                                primary_reason = "descriptor_drift"
                    if primary_reason is None:
                        reason2, sha2, equal2 = _read_stage_pass(fd, descriptor0[5], proposal)
                        if reason2 is not None:
                            primary_reason = reason2
                        elif sha1 != sha2:
                            primary_reason = "descriptor_drift"
                        else:
                            try:
                                final_descriptor_raw = _os_fstat(fd)
                            except Exception:
                                primary_reason = "descriptor_metadata_invalid"
                            else:
                                descriptor_final, final_descriptor_error = _classify_file_metadata(final_descriptor_raw, descriptor=True)
                                if final_descriptor_error is not None:
                                    primary_reason = final_descriptor_error
                                elif descriptor_final != descriptor0:
                                    primary_reason = "descriptor_drift"
                                else:
                                    pass_sha = sha2
                                    raw_equal = equal1 and equal2
            except BaseException as error:
                primary_base = error
            finally:
                if fd is not None:
                    try:
                        closed = _os_close(fd)
                    except BaseException as close_error:
                        if primary_base is None:
                            if isinstance(close_error, Exception):
                                primary_reason = primary_reason or "close_error"
                            else:
                                primary_base = close_error
                    else:
                        if closed is not None and primary_base is None:
                            primary_reason = primary_reason or "close_error"
            if primary_base is not None:
                raise primary_base
            if primary_reason is not None:
                child_reason = primary_reason
            else:
                try:
                    final_path_raw = _nofollow_stat(plan.stage_path)
                except Exception:
                    child_reason = "final_stat_error"
                else:
                    path1, path1_error = _classify_file_metadata(final_path_raw, descriptor=False)
                    if path1_error is not None or path1 is None:
                        child_reason = "final_entry_invalid"
                    elif path1 != path0 or descriptor_final is None or (
                        path1[0], path1[1], stat.S_IFMT(path1[2]), path1[5]
                    ) != (
                        descriptor_final[0], descriptor_final[1], stat.S_IFMT(descriptor_final[2]), descriptor_final[5]
                    ):
                        child_reason = "final_path_drift"
                    else:
                        child_state = "present"
                        observed_bytes = path1[5]
                        observed_sha = pass_sha
                        relation = "exact" if raw_equal else "different"
                        child_reason = (
                            "stable_bounded_regular_file_exact_payload"
                            if raw_equal
                            else "stable_bounded_regular_file_different_payload"
                        )

    # The final parent endpoint always wins over a favorable child result.
    try:
        parent_final_raw = _nofollow_stat(plan.staging_parent)
    except Exception:
        return _make_residue(
            plan,
            proposal,
            phase,
            "indeterminate",
            ("parent_final_stat_error",),
            "indeterminate",
            ("parent_final_stat_error",),
            None,
            None,
            "indeterminate",
        )
    parent1, parent1_error = _classify_directory_metadata(parent_final_raw)
    if parent1_error is not None or parent1 is None:
        return _make_residue(
            plan,
            proposal,
            phase,
            "indeterminate",
            ("parent_final_entry_invalid",),
            "indeterminate",
            ("parent_final_entry_invalid",),
            None,
            None,
            "indeterminate",
        )
    if parent1 != parent0:
        return _make_residue(
            plan,
            proposal,
            phase,
            "indeterminate",
            ("parent_drift",),
            "indeterminate",
            ("parent_drift",),
            None,
            None,
            "indeterminate",
        )
    return _make_residue(
        plan,
        proposal,
        phase,
        "present",
        ("stable_parent_directory",),
        child_state,
        (child_reason,),
        observed_bytes,
        observed_sha,
        relation,
    )


class _FailureCut:
    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value


def _require_absent_path(path: str, name: str) -> None:
    try:
        _nofollow_stat(path)
    except FileNotFoundError:
        return
    except BaseException as error:
        if isinstance(error, Exception):
            _fail(f"{name} absence check failed")
        raise
    _fail(f"{name} already exists")


def _append_digest(
    license_id: str,
    publisher_nonce: str,
    manifest_nonce: str,
    repository_path: str,
    final_path: str,
    alias_path: str,
    event_sha256: str,
    event_bytes: int,
    write_calls: int,
    read_calls: int,
) -> str:
    return _sha(
        _D_APPEND
        + _l(license_id)
        + _n(publisher_nonce)
        + _n(manifest_nonce)
        + _p(repository_path)
        + _p(final_path)
        + _p(alias_path)
        + _h(event_sha256)
        + _u64(event_bytes)
        + _k(_APPEND_STATUS)
        + _u64(write_calls)
        + _u64(read_calls)
        + _u64(1)
        + _u64(1)
        + _u64(2)
    )


def _append_terminal_manifest(
    plan: _PathPlan,
    manifest_nonce: str,
    alias_path: str,
    event_raw: bytes,
    event_sha256: str,
    cut: _FailureCut,
    /,
) -> SyntheticTerminalManifestAppendV10:
    _utf8(alias_path, "manifest alias path", _MAX_MANIFEST_HOST_PATH_BYTES)
    _utf8(plan.manifest_final_path, "manifest final path", _MAX_MANIFEST_HOST_PATH_BYTES)
    _stable_directory_pair(plan)
    _require_absent_path(alias_path, "manifest alias")
    _require_absent_path(plan.manifest_final_path, "manifest final")
    try:
        opened = _os_open(alias_path, _OPEN_FLAGS, _OPEN_MODE)
    except BaseException:
        raise
    if type(opened) is not int or opened < 0:
        _fail("manifest temp create returned an invalid descriptor")
    fd = opened
    cut.value = "after_create"
    write_calls = 0
    read_calls = 0
    descriptor_final: tuple[int, int, int, bool, int, int, int] | None = None
    primary: BaseException | None = None
    try:
        initial_raw = _os_fstat(fd)
        initial = _file_snapshot(initial_raw, "initial manifest alias descriptor")
        if initial[5] != 0:
            _fail("new manifest alias descriptor is not empty")
        offset = 0
        view = memoryview(event_raw)
        while offset < len(view):
            if write_calls >= _APPEND_WRITE_BOUND:
                _fail("manifest write call bound would be exceeded")
            request_size = min(_IO_CHUNK_BYTES, len(view) - offset)
            result = _os_write(fd, view[offset : offset + request_size])
            if type(result) is not int or not 1 <= result <= request_size:
                _fail("manifest write made invalid progress")
            write_calls += 1
            offset += result
        written = _file_snapshot(_os_fstat(fd), "written manifest alias descriptor")
        if (written[0], written[1], stat.S_IFMT(written[2])) != (
            initial[0], initial[1], stat.S_IFMT(initial[2])
        ) or written[5] != len(event_raw):
            _fail("manifest descriptor identity or final size is invalid")
        seek_result = _os_lseek(fd, 0, os.SEEK_SET)
        if type(seek_result) is not int or seek_result != 0:
            _fail("manifest readback seek failed")
        digest = hashlib.sha256()
        offset = 0
        while offset < len(event_raw):
            request_size = min(_IO_CHUNK_BYTES, len(event_raw) - offset)
            chunk = _os_read(fd, request_size)
            read_calls += 1
            if read_calls > _APPEND_READ_BOUND or type(chunk) is not bytes or len(chunk) != request_size:
                _fail("manifest readback was short, overlong, or over bound")
            if chunk != event_raw[offset : offset + request_size]:
                _fail("manifest raw readback differs from event bytes")
            digest.update(chunk)
            offset += request_size
        eof = _os_read(fd, 1)
        read_calls += 1
        if read_calls > _APPEND_READ_BOUND or type(eof) is not bytes or eof != b"":
            _fail("manifest EOF probe failed")
        if digest.hexdigest().upper() != event_sha256:
            _fail("manifest readback digest differs from event digest")
        descriptor_final = _file_snapshot(_os_fstat(fd), "read manifest alias descriptor")
        if descriptor_final != written:
            _fail("manifest descriptor drifted during readback")
    except BaseException as error:
        primary = error
    try:
        close_result = _os_close(fd)
    except BaseException as close_error:
        if primary is None:
            primary = close_error
    else:
        if close_result is not None and primary is None:
            primary = IntegratedSyntheticManifestV10Error("manifest descriptor close returned non-None")
    if primary is not None:
        raise primary
    if descriptor_final is None:
        _fail("manifest descriptor endpoint is missing")
    alias_before_link = _file_snapshot(_nofollow_stat(alias_path), "closed manifest alias")
    if (alias_before_link[0], alias_before_link[1], stat.S_IFMT(alias_before_link[2]), alias_before_link[5]) != (
        descriptor_final[0],
        descriptor_final[1],
        stat.S_IFMT(descriptor_final[2]),
        descriptor_final[5],
    ):
        _fail("closed manifest alias differs from descriptor")
    _require_absent_path(plan.manifest_final_path, "manifest final")
    cut.value = "link_unconfirmed"
    link_result = _os_link(alias_path, plan.manifest_final_path, follow_symlinks=False)
    if link_result is not None:
        _fail("manifest hardlink returned non-None")
    cut.value = "after_link"
    alias_after_link = _file_snapshot(_nofollow_stat(alias_path), "postlink manifest alias")
    final_after_link = _file_snapshot(_nofollow_stat(plan.manifest_final_path), "postlink manifest final")
    comparator = lambda item: (item[0], item[1], stat.S_IFMT(item[2]), item[5])
    if comparator(alias_after_link) != comparator(final_after_link) or comparator(alias_after_link) != comparator(descriptor_final):
        _fail("manifest aliases do not denote one observed file identity")
    append_digest = _append_digest(
        plan.license_id,
        plan.publisher_nonce,
        manifest_nonce,
        plan.manifest_repository_path,
        plan.manifest_final_path,
        alias_path,
        event_sha256,
        len(event_raw),
        write_calls,
        read_calls,
    )
    return SyntheticTerminalManifestAppendV10(
        _APPEND_SCHEMA,
        _APPEND_SCOPE,
        _ORIGIN_STATUS,
        plan.license_id,
        plan.publisher_nonce,
        manifest_nonce,
        plan.manifest_repository_path,
        plan.manifest_final_path,
        alias_path,
        event_sha256,
        len(event_raw),
        _APPEND_STATUS,
        write_calls,
        read_calls,
        1,
        1,
        2,
        append_digest,
        _MAX_PAYLOAD_BYTES,
        _MAX_MANIFEST_HOST_PATH_BYTES,
        _IO_CHUNK_BYTES,
        _APPEND_WRITE_BOUND,
        _APPEND_READ_BOUND,
        1,
        1,
        2,
        _APPEND_WORK_BOUND,
        _IO_CHUNK_BYTES,
        _WRITER_SCOPE,
        _HARDLINK_SCOPE,
        _ALIAS_RETENTION_SCOPE,
        _DURABILITY_SCOPE,
        _CLEANUP_SCOPE,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _Preflight:
    root: str
    seed_raw: bytes
    profile: str
    alternate: bytes | None
    proposal: bytes
    seed: SyntheticClaimSeedV10
    receipt: PublicClaimReceiptV10
    receipt_sha256: str
    plan: _PathPlan
    initial_inventory: SyntheticSeedLocalInventoryAuditV10
    initial_inventory_sha256: str
    active_inspection: AttemptManifestChainInspectionV10
    index1_file: AttemptManifestEventFileV10
    active_chain_sha256: str
    pre_stage: SyntheticManifestResidueObservationV10


def _common_preflight(
    root: object,
    seed_raw: object,
    constructor_profile: object,
    alternate_payload: object,
    proposed_payload: object,
    phase: str,
) -> _Preflight:
    root_text, raw_seed, profile, alternate, proposal = _validate_inputs(
        root, seed_raw, constructor_profile, alternate_payload, proposed_payload
    )
    parsed_seed = _dep_parse_seed(raw_seed)
    seed, receipt = _validate_seed(raw_seed, parsed_seed)
    proposal_sha = _raw_sha(proposal)
    alternate_sha = None if alternate is None else _raw_sha(alternate)
    nonce = _publisher_nonce(
        seed.seed_identity_sha256,
        profile,
        len(proposal),
        proposal_sha,
        None if alternate is None else len(alternate),
        alternate_sha,
    )
    plan = _early_path_plan(root_text, receipt.license_id, nonce)
    _stable_directory_pair(plan)
    inventory_raw = _dep_audit_inventory(root_text, raw_seed)
    inventory, inventory_sha, claim = _accepted_inventory_projection(
        inventory_raw, seed, receipt, False
    )
    receipt_sha = claim.seed_receipt_sha256
    inspection_raw = _dep_inspect_chain(root_text, receipt.license_id)
    inspection, event_file, chain_sha = _accepted_active_chain_projection(
        inspection_raw, receipt, receipt_sha
    )
    if (
        claim.last_event_sha256 != inspection.last_event_sha256
        or inventory.total_observed_event_bytes != len(event_file.event_bytes)
    ):
        _fail("inventory and direct active-chain endpoints disagree")
    pre_stage = _observe_stage_residue(plan, proposal, phase)
    if pre_stage.observation_state != "absent" or pre_stage.payload_relation != "not_present":
        _fail("publisher stage is not stable absent at preflight")
    return _Preflight(
        root_text,
        raw_seed,
        profile,
        alternate,
        proposal,
        seed,
        receipt,
        receipt_sha,
        plan,
        inventory,
        inventory_sha,
        inspection,
        event_file,
        chain_sha,
        pre_stage,
    )


def _initial_state_exact() -> InMemoryFakeCasStateV10:
    state = _reconstruct_state(_dep_initial_state())
    if (
        state.generation != 0
        or state.cell_state != "absent"
        or state.cell_payload is not None
        or state.cell_payload_bytes is not None
        or state.cell_payload_sha256 is not None
    ):
        _fail("initial CAS state is not exact absent@g0")
    return state


class _DigestView:
    pass


def _view(values: dict[str, object]) -> _DigestView:
    result = _DigestView()
    for name, value in values.items():
        setattr(result, name, value)
    return result


def _conflict_values(
    preflight: _Preflight,
    initial_state: InMemoryFakeCasStateV10,
    stale_version: str,
    trace: SyntheticCoordinatorActionTraceV10,
    artifact_sha: str,
    post_stage: SyntheticManifestResidueObservationV10,
    final_inventory_sha: str,
    cas_sha: str,
) -> dict[str, object]:
    proposal_sha = _raw_sha(preflight.proposal)
    alternate_sha = None if preflight.alternate is None else _raw_sha(preflight.alternate)
    return {
        "audit_schema_version": _CONFLICT_SCHEMA,
        "audit_scope": _CONFLICT_SCOPE,
        "origin_status": _ORIGIN_STATUS,
        "outcome": "conflict_without_marker_confirmed",
        "reason_codes": ("expected_state_version_mismatch",),
        "root": preflight.root,
        "seed_file_sha256": preflight.seed.seed_file_sha256,
        "seed_identity_sha256": preflight.seed.seed_identity_sha256,
        "license_id": preflight.receipt.license_id,
        "claim_receipt_sha256": preflight.receipt_sha256,
        "constructor_profile": preflight.profile,
        "publisher_collision_nonce": preflight.plan.publisher_nonce,
        "staging_parent": preflight.plan.staging_parent,
        "stage_basename": preflight.plan.stage_basename,
        "stage_path": preflight.plan.stage_path,
        "proposed_payload_bytes": len(preflight.proposal),
        "proposed_payload_sha256": proposal_sha,
        "alternate_payload_bytes": None if preflight.alternate is None else len(preflight.alternate),
        "alternate_payload_sha256": alternate_sha,
        "initial_state_version_sha256": initial_state.state_version_sha256,
        "conflict_expected_state_version_sha256": stale_version,
        "initial_inventory_projection_sha256": preflight.initial_inventory_sha256,
        "active_chain_projection_sha256": preflight.active_chain_sha256,
        "pre_stage_observation": preflight.pre_stage,
        "action_trace": trace,
        "final_snapshot_sha256": trace.after_snapshot_sha256,
        "final_lifecycle_state": "OPEN",
        "artifact_projection_sha256": artifact_sha,
        "post_stage_observation": post_stage,
        "final_inventory_projection_sha256": final_inventory_sha,
        "cas_binding_sha256": cas_sha,
        "manifest_event_delta": "zero",
        "conflict_without_marker_status": "exact_no_marker_no_stage_no_manifest",
        "stage_residue_classification": "exact_absent_at_two_sequential_endpoints",
        "same_call_binding_scope": _SAME_CALL_SCOPE,
        "persistent_cross_binding": _PERSISTENT_BINDING,
        "artifact_scope": _ARTIFACT_SCOPE,
        "inventory_scope": _INVENTORY_SCOPE,
        "detached_record_scope": _DETACHED_SCOPE,
        "stage_residue_scope": _STAGE_RESIDUE_SCOPE,
        "root_scope": _ROOT_SCOPE,
        "ancestor_link_containment": _ANCESTOR_LINK_CONTAINMENT,
        "basename_spelling_verification": _BASENAME_VERIFICATION,
        "hostile_concurrent_reparse_prevention": _HOSTILE_REPARSE_PREVENTION,
        "backing_store_scope": _BACKING_STORE_SCOPE,
        "durability_scope": _DURABILITY_SCOPE,
        "cleanup_scope": _CLEANUP_SCOPE,
        "remote_publication": _REMOTE_PUBLICATION,
        "max_inventory_audits": 2,
        "max_artifact_observations": 1,
        "max_stage_observations": 2,
        "aggregate_dependency_payload_work_upper_bound_bytes": _CONFLICT_AGGREGATE_WORK,
        "canonical_remote_authority": False,
        "licenses_execution": False,
        "licenses_publication": False,
        "licenses_recovery": False,
        "licenses_later_stage": False,
    }


def _audit_conflict_impl(
    root: object,
    seed_raw: object,
    constructor_profile: object,
    alternate_payload: object,
    proposed_payload: object,
    cut: _FailureCut,
) -> SyntheticConflictWithoutMarkerAuditV10:
    preflight = _common_preflight(
        root, seed_raw, constructor_profile, alternate_payload, proposed_payload, "conflict_pre"
    )
    cut.value = "conflict"
    initial = _initial_state_exact()
    first = initial.state_version_sha256[0]
    stale = ("1" if first == "0" else "0") + initial.state_version_sha256[1:]
    coordinator = _dep_new_coordinator(preflight.profile, preflight.alternate)
    if type(coordinator) is not SyntheticRecoveryCoordinatorV10:
        _fail("coordinator factory returned the wrong exact type")
    action_raw = _dep_publish_coordinator(
        coordinator,
        preflight.plan.staging_parent,
        preflight.plan.publisher_nonce,
        initial,
        stale,
        preflight.proposal,
    )
    action, trace = _trace_from_action(action_raw)
    if (
        action.operation != "publish"
        or action.outcome != "cas_conflict_no_marker"
        or action.reason_codes != ("expected_state_version_mismatch",)
        or action.endpoint_state_changed
        or action.publish_result is None
        or action.marker is not None
        or action.issued_epoch is not None
        or action.issued_witness is not None
        or action.after_snapshot.lifecycle_state != "OPEN"
        or action.after_snapshot.constructor_profile != preflight.profile
    ):
        _fail("conflict coordinator endpoint is invalid")
    result = action.publish_result
    transition = result.cas_transition
    if (
        result.outcome != "cas_conflict_no_stage"
        or result.staging_parent != preflight.plan.staging_parent
        or result.collision_nonce != preflight.plan.publisher_nonce
        or result.stage_basename != preflight.plan.stage_basename
        or result.stage_path != preflight.plan.stage_path
        or result.stage_payload_bytes is not None
        or result.stage_payload_sha256 is not None
        or result.write_call_count != 0
        or result.read_call_count != 0
        or transition.before_state != initial
        or transition.after_state != initial
        or transition.expected_state_version_sha256 != stale
        or transition.proposed_payload != preflight.proposal
        or transition.outcome != "conflict_no_change"
        or transition.state_changed
    ):
        _fail("conflict publisher Result is invalid")
    post_stage = _observe_stage_residue(preflight.plan, preflight.proposal, "conflict_post")
    if post_stage.observation_state != "absent" or post_stage.payload_relation != "not_present":
        _fail("conflict publisher stage changed")
    artifact_raw = _dep_observe_artifacts(preflight.root, preflight.receipt)
    _, artifact_sha = _accepted_artifact_projection(
        artifact_raw, preflight.receipt, preflight.receipt_sha256
    )
    final_inventory_raw = _dep_audit_inventory(preflight.root, preflight.seed_raw)
    _, final_inventory_sha, final_claim = _accepted_inventory_projection(
        final_inventory_raw, preflight.seed, preflight.receipt, False
    )
    if final_inventory_sha != preflight.initial_inventory_sha256 or final_claim.last_event_sha256 != preflight.active_inspection.last_event_sha256:
        _fail("conflict final inventory differs from preflight")
    cas_sha = _cas_sha256(
        "conflict",
        initial.state_version_sha256,
        stale,
        len(preflight.proposal),
        _raw_sha(preflight.proposal),
        None if preflight.alternate is None else len(preflight.alternate),
        None if preflight.alternate is None else _raw_sha(preflight.alternate),
        result.operation_sha256,
        transition.transition_sha256,
        None,
        None,
    )
    values = _conflict_values(
        preflight, initial, stale, trace, artifact_sha, post_stage, final_inventory_sha, cas_sha
    )
    values["audit_sha256"] = _conflict_audit_sha256(_view(values))
    return SyntheticConflictWithoutMarkerAuditV10(**values)


def audit_synthetic_conflict_without_marker_v1_0(
    root: str,
    seed_raw: bytes,
    constructor_profile: str,
    alternate_payload: bytes | None,
    proposed_payload: bytes,
    /,
) -> SyntheticConflictWithoutMarkerAuditV10:
    cut = _FailureCut("preflight")
    try:
        return _audit_conflict_impl(
            root, seed_raw, constructor_profile, alternate_payload, proposed_payload, cut
        )
    except BaseException as error:
        if not isinstance(error, Exception):
            raise
        message = (
            "integrated synthetic preflight failed"
            if cut.value == "preflight"
            else "integrated synthetic conflict audit failed"
        )
        raise IntegratedSyntheticManifestV10Error(message) from None


def _validate_recovery_publish(
    preflight: _Preflight,
    initial: InMemoryFakeCasStateV10,
    value: object,
) -> tuple[SyntheticRecoveryActionV10, SyntheticCoordinatorActionTraceV10, SyntheticRecoveryMarkerV10]:
    action, trace = _trace_from_action(value)
    if (
        action.operation != "publish"
        or action.outcome != "synthetic_marker_committed_result_withheld"
        or action.reason_codes != ("synthetic_marker_committed",)
        or not action.endpoint_state_changed
        or action.publish_result is not None
        or action.marker is None
        or action.issued_epoch is not None
        or action.issued_witness is not None
        or action.after_snapshot.lifecycle_state != "RECOVERY_PENDING"
        or action.after_snapshot.profile_status != "spent_marker_committed"
        or action.after_snapshot.constructor_profile != preflight.profile
        or trace.publisher_operation_sha256 is not None
        or trace.publisher_transition_sha256 is not None
    ):
        _fail("recovery publish Action is invalid")
    marker = _reconstruct_marker(action.marker)
    expected_kind = {
        "ack_loss_confirmed": "synthetic_ack_loss_confirmed",
        "ack_loss_unavailable_then_confirmed": "synthetic_ack_loss_unavailable",
        "ack_loss_unavailable_until_budget_block": "synthetic_ack_loss_unavailable",
        "wrong_delta_confirmed": "synthetic_wrong_delta_confirmed",
    }[preflight.profile]
    expected_fault = {
        "ack_loss_confirmed": "intended_applied_ack_lost_confirmed",
        "ack_loss_unavailable_then_confirmed": "intended_applied_ack_lost_unconfirmed",
        "ack_loss_unavailable_until_budget_block": "intended_applied_ack_lost_unconfirmed",
        "wrong_delta_confirmed": "wrong_delta_confirmed",
    }[preflight.profile]
    expected_rows = {
        "ack_loss_confirmed": 1,
        "ack_loss_unavailable_then_confirmed": 2,
        "ack_loss_unavailable_until_budget_block": 4,
        "wrong_delta_confirmed": 1,
    }[preflight.profile]
    if (
        marker.constructor_profile != preflight.profile
        or marker.marker_kind != expected_kind
        or marker.synthetic_fault_outcome != expected_fault
        or marker.replay_plan_row_count != expected_rows
        or marker.marker_ordinal != 1
        or marker.phase2b1_failure_codes != ("OTHER_HARNESS_ERROR",)
        or marker.publisher_outcome != "staged_intended_fake_publish_acknowledged"
        or marker.before_state_version_sha256 != initial.state_version_sha256
        or marker.stage_payload_bytes != len(preflight.proposal)
        or marker.stage_payload_sha256 != _raw_sha(preflight.proposal)
        or trace.marker_sha256 != marker.marker_sha256
    ):
        _fail("recovery marker is invalid")
    return action, trace, marker


def _run_recovery_plan(
    coordinator: SyntheticRecoveryCoordinatorV10,
    profile: str,
    traces: list[SyntheticCoordinatorActionTraceV10],
) -> tuple[SyntheticRecoveryWitnessV10, SyntheticRecoverySnapshotV10]:
    replay_count = {
        "ack_loss_confirmed": 1,
        "ack_loss_unavailable_then_confirmed": 2,
        "ack_loss_unavailable_until_budget_block": 4,
        "wrong_delta_confirmed": 1,
    }[profile]
    terminal_action: SyntheticRecoveryActionV10 | None = None
    witness: SyntheticRecoveryWitnessV10 | None = None
    for ordinal in range(1, replay_count + 1):
        acquire_raw = _dep_acquire_epoch(coordinator)
        acquire, acquire_trace = _trace_from_action(acquire_raw)
        if (
            acquire.operation != "acquire_epoch"
            or acquire.outcome != "epoch_issued"
            or acquire.reason_codes != ("recovery_marker_pending",)
            or not acquire.endpoint_state_changed
            or acquire.issued_epoch is None
            or type(acquire.issued_epoch) is not SyntheticRecoveryEpochV10
            or acquire.epoch_ordinal != ordinal
            or acquire.issued_epoch.epoch_ordinal != ordinal
            or acquire.issued_witness is not None
            or acquire.after_snapshot.lifecycle_state != "RECOVERY_ACTIVE"
        ):
            _fail("recovery acquire Action is invalid")
        if acquire_trace.before_snapshot_sha256 != traces[-1].after_snapshot_sha256:
            _fail("recovery acquire snapshot is not contiguous")
        traces.append(acquire_trace)
        epoch = acquire.issued_epoch
        replay_raw = _dep_replay_epoch(coordinator, epoch)
        replay, replay_trace = _trace_from_action(replay_raw)
        if replay_trace.before_snapshot_sha256 != traces[-1].after_snapshot_sha256:
            _fail("recovery replay snapshot is not contiguous")
        expected_outcome: str
        expected_reason: str
        expected_observation: str
        terminal = ordinal == replay_count
        if profile == "ack_loss_confirmed" or (
            profile == "ack_loss_unavailable_then_confirmed" and terminal
        ):
            expected_outcome = "replay_confirmed_recovered"
            expected_reason = "synthetic_intended_transition_confirmed"
            expected_observation = "confirmed_intended"
        elif profile == "wrong_delta_confirmed":
            expected_outcome = "replay_wrong_delta_permanent_block"
            expected_reason = "synthetic_wrong_delta_confirmed"
            expected_observation = "confirmed_wrong_delta"
        elif profile == "ack_loss_unavailable_until_budget_block" and terminal:
            expected_outcome = "replay_unavailable_budget_permanent_block"
            expected_reason = "recovery_epoch_budget_exhausted_after_unavailable"
            expected_observation = "unavailable"
        else:
            expected_outcome = "replay_unavailable_retry_pending"
            expected_reason = "same_kernel_replay_unavailable"
            expected_observation = "unavailable"
        if (
            replay.operation != "replay_epoch"
            or replay.outcome != expected_outcome
            or replay.reason_codes != (expected_reason,)
            or replay.replay_observation != expected_observation
            or replay.epoch_ordinal != ordinal
            or not replay.endpoint_state_changed
        ):
            _fail("recovery replay Action is invalid")
        if terminal:
            if replay.issued_witness is None or type(replay.issued_witness) is not SyntheticRecoveryWitnessV10:
                _fail("terminal replay did not issue the exact witness type")
            expected_purpose = (
                "record_recovered_terminal"
                if profile in _PROFILES[:2]
                else "record_permanent_block"
            )
            if (
                replay.after_snapshot.witness_purpose != expected_purpose
                or replay.after_snapshot.terminal_reason != expected_reason
                or replay.after_snapshot.terminal_sha256 is None
                or replay.issued_witness.purpose != expected_purpose
                or replay.issued_witness.terminal_sha256 != replay.after_snapshot.terminal_sha256
            ):
                _fail("terminal replay witness binding is invalid")
            witness = replay.issued_witness
            terminal_action = replay
        elif replay.issued_witness is not None or replay.after_snapshot.lifecycle_state != "RECOVERY_PENDING":
            _fail("nonterminal replay incorrectly issued a witness")
        traces.append(replay_trace)
    if witness is None or terminal_action is None:
        _fail("recovery plan did not reach a terminal witness")
    snapshot = _reconstruct_snapshot(_dep_snapshot_coordinator(coordinator))
    if snapshot != terminal_action.after_snapshot:
        _fail("preconsume snapshot differs from terminal replay")
    return witness, snapshot


def _terminal_event(
    preflight: _Preflight,
    marker: SyntheticRecoveryMarkerV10,
) -> AttemptManifestEventV10:
    index1 = preflight.index1_file.event
    return AttemptManifestEventV10(
        schema_version="lean-rgc-uprime-u1-attempt-manifest-v1.0",
        event_type="recovery",
        event_index=2,
        created_at_utc=index1.created_at_utc,
        license_id=preflight.receipt.license_id,
        candidate_commit=preflight.receipt.candidate_commit,
        license_commit=preflight.receipt.license_commit,
        remote_claim_ref=preflight.receipt.remote_claim_ref,
        claim_receipt=preflight.receipt,
        claim_receipt_sha256=preflight.receipt_sha256,
        prior_event_sha256=preflight.index1_file.event_sha256,
        reservation_exists=False,
        ledger_exists=False,
        report_exists=False,
        reservation_sha256=None,
        reservation_bytes=None,
        ledger_sha256=None,
        ledger_bytes=None,
        report_sha256=None,
        report_bytes=None,
        ledger_inspection_status="absent",
        ledger_sequence_status=None,
        verifier_status="not_run",
        scanner_status="not_run",
        scanner_rule_ids=(),
        verdict=None,
        failure_codes=marker.phase2b1_failure_codes,
        full_ledger_published=False,
        terminal_event=True,
    )


def _recovery_values(
    preflight: _Preflight,
    initial: InMemoryFakeCasStateV10,
    marker: SyntheticRecoveryMarkerV10,
    witness: SyntheticRecoveryWitnessV10,
    preconsume: SyntheticRecoverySnapshotV10,
    traces: tuple[SyntheticCoordinatorActionTraceV10, ...],
    preartifact_sha: str,
    preappend_stage: SyntheticManifestResidueObservationV10,
    event_sha: str,
    append: SyntheticTerminalManifestAppendV10,
    attestation_sha: str,
    postartifact_sha: str,
    postappend_stage: SyntheticManifestResidueObservationV10,
    final_inventory_sha: str,
    final_trace: SyntheticCoordinatorActionTraceV10,
    manifest_nonce: str,
) -> dict[str, object]:
    all_traces = traces + (final_trace,)
    purpose = witness.purpose
    final_snapshot = final_trace.after_snapshot_sha256
    cas_sha = _cas_sha256(
        "recovery",
        initial.state_version_sha256,
        initial.state_version_sha256,
        len(preflight.proposal),
        _raw_sha(preflight.proposal),
        None if preflight.alternate is None else len(preflight.alternate),
        None if preflight.alternate is None else _raw_sha(preflight.alternate),
        marker.publisher_operation_sha256,
        marker.publisher_transition_sha256,
        marker.synthetic_fault_transition_sha256,
        marker.marker_sha256,
    )
    values: dict[str, object] = {
        "audit_schema_version": _RECOVERY_SCHEMA,
        "audit_scope": _RECOVERY_SCOPE,
        "origin_status": _ORIGIN_STATUS,
        "outcome": "integrated_synthetic_terminal_manifest_appended_and_witness_spent",
        "reason_codes": (preconsume.terminal_reason,),
        "root": preflight.root,
        "seed_file_sha256": preflight.seed.seed_file_sha256,
        "seed_identity_sha256": preflight.seed.seed_identity_sha256,
        "license_id": preflight.receipt.license_id,
        "claim_receipt_sha256": preflight.receipt_sha256,
        "constructor_profile": preflight.profile,
        "publisher_collision_nonce": preflight.plan.publisher_nonce,
        "manifest_nonce": manifest_nonce,
        "staging_parent": preflight.plan.staging_parent,
        "stage_basename": preflight.plan.stage_basename,
        "stage_path": preflight.plan.stage_path,
        "manifest_repository_path": preflight.plan.manifest_repository_path,
        "manifest_host_final_path": preflight.plan.manifest_final_path,
        "manifest_host_alias_path": append.host_alias_path,
        "proposed_payload_bytes": len(preflight.proposal),
        "proposed_payload_sha256": _raw_sha(preflight.proposal),
        "alternate_payload_bytes": None if preflight.alternate is None else len(preflight.alternate),
        "alternate_payload_sha256": None if preflight.alternate is None else _raw_sha(preflight.alternate),
        "initial_state_version_sha256": initial.state_version_sha256,
        "expected_state_version_sha256": initial.state_version_sha256,
        "initial_inventory_projection_sha256": preflight.initial_inventory_sha256,
        "active_chain_projection_sha256": preflight.active_chain_sha256,
        "pre_stage_observation": preflight.pre_stage,
        "action_trace": all_traces,
        "action_count": len(all_traces),
        "marker": marker,
        "witness_purpose": purpose,
        "witness_sha256": witness.witness_sha256,
        "preconsume_snapshot_sha256": preconsume.snapshot_sha256,
        "preconsume_lifecycle_state": preconsume.lifecycle_state,
        "preappend_artifact_projection_sha256": preartifact_sha,
        "preappend_stage_observation": preappend_stage,
        "terminal_event_sha256": event_sha,
        "manifest_append": append,
        "terminal_attestation_projection_sha256": attestation_sha,
        "postappend_artifact_projection_sha256": postartifact_sha,
        "postappend_stage_observation": postappend_stage,
        "final_inventory_projection_sha256": final_inventory_sha,
        "final_snapshot_sha256": final_snapshot,
        "final_lifecycle_state": final_trace.outcome and (
            "RECOVERED_WITNESS_SPENT" if purpose == "record_recovered_terminal" else "BLOCKED_WITNESS_SPENT"
        ),
        "cas_binding_sha256": cas_sha,
        "failure_code_binding": "exact_phase2b2e_marker_tuple_no_inference",
        "stage_residue_classification": "absent_before_publish_exact_proposal_at_two_later_endpoints",
        "phase2b1_event_binding": "exact_index2_recovery_bytes_and_terminal_attestation",
        "publisher_operation_binding": "marker_hashes_plus_same_call_stage_byte_observations",
        "marker_plan_binding": "exact_phase2b2e_profile_plan_and_live_handle_sequence",
        "artifact_scope": _ARTIFACT_SCOPE,
        "inventory_scope": _INVENTORY_SCOPE,
        "same_call_binding_scope": _SAME_CALL_SCOPE,
        "persistent_cross_binding": _PERSISTENT_BINDING,
        "manifest_witness_atomicity": _MANIFEST_WITNESS_ATOMICITY,
        "timestamp_scope": _TIMESTAMP_SCOPE,
        "detached_record_scope": _DETACHED_SCOPE,
        "stage_residue_scope": _STAGE_RESIDUE_SCOPE,
        "manifest_alias_scope": _MANIFEST_ALIAS_SCOPE,
        "root_scope": _ROOT_SCOPE,
        "ancestor_link_containment": _ANCESTOR_LINK_CONTAINMENT,
        "basename_spelling_verification": _BASENAME_VERIFICATION,
        "hostile_concurrent_reparse_prevention": _HOSTILE_REPARSE_PREVENTION,
        "backing_store_scope": _BACKING_STORE_SCOPE,
        "durability_scope": _DURABILITY_SCOPE,
        "cleanup_scope": _CLEANUP_SCOPE,
        "remote_publication": _REMOTE_PUBLICATION,
        "real_recovery_scope": _REAL_RECOVERY_SCOPE,
        "execution_scope": _EXECUTION_SCOPE,
        "max_seed_claims": 1,
        "max_chain_events": 2,
        "max_coordinator_actions": 10,
        "max_recovery_epochs": 4,
        "max_artifact_observations": 2,
        "max_stage_observations": 3,
        "max_inventory_audits": 2,
        "max_manifest_appends": 1,
        "aggregate_dependency_payload_work_upper_bound_bytes": _RECOVERY_AGGREGATE_WORK,
        "coordinator_payload_reference_upper_bound_bytes": 3_145_728,
        "proposal_payload_copy_upper_bound_bytes": 0,
        "canonical_remote_authority": False,
        "licenses_execution": False,
        "licenses_publication": False,
        "licenses_recovery": False,
        "licenses_later_stage": False,
    }
    return values


def _append_recovery_impl(
    root: object,
    seed_raw: object,
    constructor_profile: object,
    alternate_payload: object,
    proposed_payload: object,
    cut: _FailureCut,
) -> IntegratedSyntheticRecoveryManifestAuditV10:
    preflight = _common_preflight(
        root, seed_raw, constructor_profile, alternate_payload, proposed_payload, "pre_publish"
    )
    cut.value = "before_create"
    initial = _initial_state_exact()
    coordinator = _dep_new_coordinator(preflight.profile, preflight.alternate)
    if type(coordinator) is not SyntheticRecoveryCoordinatorV10:
        _fail("coordinator factory returned the wrong exact type")
    publish_raw = _dep_publish_coordinator(
        coordinator,
        preflight.plan.staging_parent,
        preflight.plan.publisher_nonce,
        initial,
        initial.state_version_sha256,
        preflight.proposal,
    )
    _, publish_trace, marker = _validate_recovery_publish(preflight, initial, publish_raw)
    trace_list = [publish_trace]
    witness, preconsume = _run_recovery_plan(coordinator, preflight.profile, trace_list)
    preartifact_raw = _dep_observe_artifacts(preflight.root, preflight.receipt)
    _, preartifact_sha = _accepted_artifact_projection(
        preartifact_raw, preflight.receipt, preflight.receipt_sha256
    )
    preappend_stage = _observe_stage_residue(preflight.plan, preflight.proposal, "pre_append")
    if preappend_stage.observation_state != "present" or preappend_stage.payload_relation != "exact":
        _fail("pre-append publisher stage is not exact proposal bytes")
    event = _terminal_event(preflight, marker)
    event_raw = _dep_encode_event(event)
    if type(event_raw) is not bytes or not event_raw or len(event_raw) > _MAX_PAYLOAD_BYTES:
        _fail("terminal event encoder returned invalid bytes")
    if not event_raw.endswith(b"\n") or event_raw.count(b"\n") != 1:
        _fail("terminal event bytes do not have exactly one final LF")
    event_sha = _raw_sha(event_raw)
    parsed_event = _dep_parse_event_file(preflight.plan.manifest_repository_path, event_raw)
    if (
        type(parsed_event) is not AttemptManifestEventFileV10
        or parsed_event.repository_path != preflight.plan.manifest_repository_path
        or parsed_event.event_sha256 != event_sha
        or parsed_event.event_bytes != event_raw
        or parsed_event.event != event
    ):
        _fail("terminal event does not pure-parse byte-identically")
    terminal_sha = preconsume.terminal_sha256
    if terminal_sha is None:
        _fail("preconsume snapshot lacks terminal_sha256")
    manifest_nonce = _manifest_nonce(event_sha, marker.marker_sha256, terminal_sha)
    alias_path = _late_alias_path(preflight.plan, manifest_nonce)
    append = _append_terminal_manifest(
        preflight.plan, manifest_nonce, alias_path, event_raw, event_sha, cut
    )
    attestation_raw = _dep_verify_terminal(preflight.root, preflight.receipt.license_id)
    _, attestation_sha = _accepted_terminal_attestation_projection(
        attestation_raw,
        preflight.receipt,
        preflight.receipt_sha256,
        preflight.index1_file.event_sha256,
        event_sha,
        marker.phase2b1_failure_codes,
    )
    postartifact_raw = _dep_observe_artifacts(preflight.root, preflight.receipt)
    _, postartifact_sha = _accepted_artifact_projection(
        postartifact_raw, preflight.receipt, preflight.receipt_sha256
    )
    postappend_stage = _observe_stage_residue(preflight.plan, preflight.proposal, "post_append")
    if postappend_stage.observation_state != "present" or postappend_stage.payload_relation != "exact":
        _fail("post-append publisher stage is not exact proposal bytes")
    final_inventory_raw = _dep_audit_inventory(preflight.root, preflight.seed_raw)
    _, final_inventory_sha, final_claim = _accepted_inventory_projection(
        final_inventory_raw, preflight.seed, preflight.receipt, True
    )
    if final_claim.last_event_sha256 != event_sha:
        _fail("final inventory does not end at the terminal event")
    # Every read, verification, projection prerequisite, and output cell not
    # depending on consumption is complete before this last mutation.
    consume_raw = _dep_consume_witness(
        coordinator, witness, witness.purpose, witness.terminal_sha256
    )
    cut.value = "after_consume"
    consume, consume_trace = _trace_from_action(consume_raw)
    if (
        consume.operation != "consume_witness"
        or consume.outcome != "witness_consumed"
        or consume.reason_codes != ("witness_consumed",)
        or not consume.endpoint_state_changed
        or consume.before_snapshot_sha256 != preconsume.snapshot_sha256
        or consume.after_snapshot.witness_status != "spent"
        or consume.after_snapshot.terminal_sha256 != witness.terminal_sha256
        or consume_trace.before_snapshot_sha256 != trace_list[-1].after_snapshot_sha256
    ):
        _fail("witness consume Action is invalid")
    values = _recovery_values(
        preflight,
        initial,
        marker,
        witness,
        preconsume,
        tuple(trace_list),
        preartifact_sha,
        preappend_stage,
        event_sha,
        append,
        attestation_sha,
        postartifact_sha,
        postappend_stage,
        final_inventory_sha,
        consume_trace,
        manifest_nonce,
    )
    values["manifest_binding_sha256"] = _manifest_binding_sha256(_view(values))
    values["audit_sha256"] = _recovery_audit_sha256(_view(values))
    return IntegratedSyntheticRecoveryManifestAuditV10(**values)


def append_integrated_synthetic_recovery_manifest_v1_0(
    root: str,
    seed_raw: bytes,
    constructor_profile: str,
    alternate_payload: bytes | None,
    proposed_payload: bytes,
    /,
) -> IntegratedSyntheticRecoveryManifestAuditV10:
    cut = _FailureCut("preflight")
    try:
        return _append_recovery_impl(
            root, seed_raw, constructor_profile, alternate_payload, proposed_payload, cut
        )
    except BaseException as error:
        if not isinstance(error, Exception):
            raise
        message = {
            "preflight": "integrated synthetic preflight failed",
            "before_create": "integrated synthetic recovery failed before manifest temp create",
            "after_create": "integrated synthetic recovery failed after manifest temp create",
            "link_unconfirmed": "integrated synthetic recovery failed after manifest hardlink",
            "after_link": "integrated synthetic recovery failed after manifest hardlink",
            "after_consume": "integrated synthetic recovery failed after witness consumption",
        }.get(cut.value, "integrated synthetic recovery failed before manifest temp create")
        raise IntegratedSyntheticManifestV10Error(message) from None
