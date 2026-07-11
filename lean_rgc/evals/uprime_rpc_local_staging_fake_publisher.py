from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_fake_cas_kernel import (
    InMemoryFakeCasStateV10,
    InMemoryFakeCasTransitionV10,
    InMemoryFakeCasV10Error,
    step_in_memory_fake_cas_v1_0,
)


__all__ = [
    "LocalStagingFakePublisherV10Error",
    "LocalStagingFakePublishResultV10",
    "stage_and_fake_publish_normal_v1_0",
]


_RESULT_SCHEMA = "lean-rgc-uprime-u1-local-staging-fake-publish-result-v1.0"
_RESULT_SCOPE = (
    "one_call_changed_branch_nonce_stage_before_pure_normal_fake_cas_return"
)
_ORIGIN_STATUS = "unknown_may_be_synthetic"

_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_STAGING_PARENT_UTF8_BYTES = 4_096
_MAX_STAGE_PATH_UTF8_BYTES = 4_162
_COLLISION_NONCE_CHARS = 32
_COLLISION_NONCE_BYTES = 16
_IO_CHUNK_BYTES = 65_536
_MAX_WRITE_CALLS = 1_048_576
_MAX_READ_CALLS = 17
_MAX_FILESYSTEM_PAYLOAD_WORK_BYTES = 2_097_152
_MAX_PEAK_TRANSIENT_BUFFER_BYTES = 65_536
_MAX_RETAINED_PAYLOAD_COPY_BYTES = 0
_MAX_STAGE_FILE_CREATES = 1
_MAX_RETAINED_STAGE_BYTES = 1_048_576
_MAX_OPERATION_HASH_PREIMAGE_BYTES = 1_052_813

_D_OPERATION = (
    b"lean-rgc-uprime-u1-local-staging-fake-publisher-operation-v1\0"
)
_HASH_PREIMAGE_CONSTRUCTION = "payload_streamed_no_full_preimage_materialization"

_STAGE_BASENAME_PREFIX = "uprime-rpc-fake-cas-stage-v1-"
_STAGE_BASENAME_SUFFIX = ".bin"
_STAGE_BASENAME_BYTES = 65
_FIXED_DIRECTIVE = "apply_intended_acknowledge"
_OPEN_MODE = 0o600
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_OPEN_FLAGS = (
    os.O_CREAT
    | os.O_EXCL
    | os.O_RDWR
    | getattr(os, "O_BINARY", 0)
    | getattr(os, "O_NOINHERIT", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)

_LOWER_HEX32_PATTERN = r"[0-9a-f]{32}\Z"
_UPPER_HEX64_PATTERN = r"[0-9A-F]{64}\Z"
_WINDOWS_DRIVE_ROOT_PATTERN = r"[A-Za-z]:\\"

_OUTCOME_ROWS = (
    (
        "cas_conflict_no_stage",
        "expected_state_version_mismatch",
        "conflict_no_change",
        "conflict",
        "not_attempted",
        "not_attempted",
        False,
    ),
    (
        "cas_existing_identical_no_stage",
        "exact_payload_already_current",
        "existing_identical_no_change",
        "existing_identical",
        "not_attempted",
        "not_attempted",
        False,
    ),
    (
        "staged_intended_fake_publish_acknowledged",
        "exact_stage_retained_before_exposing_synthetic_acknowledged_transition",
        "intended_applied_acknowledged",
        "intended_acknowledged",
        "stable_at_endpoint",
        "retained_stable_at_endpoint",
        True,
    ),
)

_RESULT_PROVENANCE = "unauthenticated_forgeable_value_object_not_io_attestation"
_COLLISION_NONCE_SCOPE = (
    "caller_supplied_collision_separator_not_identity_or_entropy_evidence"
)
_STAGING_PARENT_AUTHORITY = (
    "caller_supplied_write_location_not_authenticated_namespace"
)
_PATH_DERIVATION_SCOPE = "lexical_native_join_no_resolution_or_canonical_binding"
_ANCESTOR_REPARSE_CHECK_SCOPE = (
    "not_performed_only_final_parent_entry_observed"
)
_BACKING_STORE_SCOPE = "unauthenticated_may_be_remote_virtual_or_overlay"
_HOSTILE_CONCURRENT_REPARSE_PREVENTION = "not_provided"
_STAGE_EXCLUSIVITY_SCOPE = (
    "changed_branch_one_native_path_exclusive_create_only"
)
_STAGE_READBACK_SCOPE = (
    "changed_branch_same_descriptor_exact_bytes_at_one_observation_interval"
)
_STAGE_RETENTION_SCOPE = "any_created_stage_retained_no_post_return_lifetime_claim"
_DURABILITY_SCOPE = "fsync_not_called_crash_and_power_loss_not_observed"
_CLEANUP_SCOPE = "not_performed_any_created_stage_may_remain_after_success_or_error"
_PUBLISHER_SCOPE = (
    "pure_fake_cas_value_return_changed_branch_stage_gated_not_real_publication"
)
_STATE_LINEARITY = "caller_threaded_not_enforced"
_CONCURRENCY_SCOPE = "no_exclusion_or_cross_process_atomicity"
_IDEMPOTENCE_SCOPE = "not_provided_distinct_nonce_is_explicit_new_attempt"
_EXACTLY_ONCE_SCOPE = "not_provided"
_PAYLOAD_CONFIDENTIALITY = (
    "not_provided_any_staged_bytes_written_to_caller_location"
)
_ATTEMPT_COMPLETENESS = "successful_returns_only_errors_unjournaled"
_MARKER_SCOPE = "not_created_or_observed"
_RECOVERY_SCOPE = "not_performed"
_EPOCH_SCOPE = "none"
_WITNESS_SCOPE = "none"
_MANIFEST_SCOPE = "not_read_or_written"
_REMOTE_PUBLICATION = "not_performed"
_AUTHORITY_SCOPE = "none"


_os_path_isabs = os.path.isabs
_os_path_normpath = os.path.normpath
_os_path_join = os.path.join
_os_stat = os.stat
_os_open = os.open
_os_fstat = os.fstat
_os_write = os.write
_os_lseek = os.lseek
_os_read = os.read
_os_close = os.close


class LocalStagingFakePublisherV10Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LocalStagingFakePublishResultV10:
    result_schema_version: str
    result_scope: str
    origin_status: str
    staging_parent: str
    collision_nonce: str
    stage_basename: str
    stage_path: str
    cas_transition: InMemoryFakeCasTransitionV10
    outcome: str
    reason_codes: tuple[str, ...]
    cas_gate_status: str
    parent_observation_status: str
    stage_status: str
    stage_payload_bytes: int | None
    stage_payload_sha256: str | None
    write_call_count: int
    read_call_count: int
    operation_sha256: str
    payload_byte_limit: int
    staging_parent_utf8_byte_limit: int
    stage_path_utf8_byte_limit: int
    collision_nonce_chars: int
    io_chunk_bytes: int
    write_call_upper_bound: int
    read_call_upper_bound: int
    filesystem_payload_work_upper_bound_bytes: int
    peak_transient_buffer_upper_bound_bytes: int
    retained_payload_copy_upper_bound_bytes: int
    stage_file_create_upper_bound: int
    retained_stage_byte_upper_bound: int
    operation_hash_preimage_upper_bound_bytes: int
    hash_preimage_construction: str
    result_provenance: str
    collision_nonce_scope: str
    staging_parent_authority: str
    path_derivation_scope: str
    ancestor_reparse_check_scope: str
    backing_store_scope: str
    hostile_concurrent_reparse_prevention: str
    stage_exclusivity_scope: str
    stage_readback_scope: str
    stage_retention_scope: str
    durability_scope: str
    cleanup_scope: str
    publisher_scope: str
    state_linearity: str
    concurrency_scope: str
    idempotence_scope: str
    exactly_once_scope: str
    payload_confidentiality: str
    attempt_completeness: str
    marker_scope: str
    recovery_scope: str
    epoch_scope: str
    witness_scope: str
    manifest_scope: str
    remote_publication: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_result(self)


def _fail(message: str) -> None:
    raise LocalStagingFakePublisherV10Error(message) from None


def _require_exact_str(value: object, name: str) -> str:
    if type(value) is not str:
        _fail(f"{name} is not an exact string")
    return value


def _require_exact_int(value: object, name: str) -> int:
    if type(value) is not int:
        _fail(f"{name} is not an exact integer")
    return value


def _require_exact_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        _fail(f"{name} is not an exact boolean")
    return value


def _require_false(value: object, name: str) -> None:
    if _require_exact_bool(value, name):
        _fail(f"{name} must be exact false")


def _require_exact_bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes:
        _fail(f"{name} is not exact bytes")
    return value


def _require_hash(value: object, name: str) -> str:
    text = _require_exact_str(value, name)
    if re.fullmatch(_UPPER_HEX64_PATTERN, text, flags=re.ASCII) is None:
        _fail(f"{name} is not exact uppercase hex64")
    return text


def _u32(value: int, /) -> bytes:
    number = _require_exact_int(value, "u32 value")
    if number < 0 or number > 4_294_967_295:
        _fail("u32 value is out of range")
    return number.to_bytes(4, "big")


def _u64(value: int, /) -> bytes:
    number = _require_exact_int(value, "u64 value")
    if number < 0 or number > 18_446_744_073_709_551_615:
        _fail("u64 value is out of range")
    return number.to_bytes(8, "big")


def _finish_hash(digest: object, /) -> str:
    try:
        value = digest.hexdigest()
    except Exception:
        _fail("SHA-256 finalization failed")
    text = _require_exact_str(value, "computed SHA-256")
    return _require_hash(text.upper(), "computed SHA-256")


def _raw_payload_sha256(payload: bytes, /) -> str:
    raw = _require_exact_bytes(payload, "payload")
    try:
        digest = hashlib.sha256()
        digest.update(raw)
    except Exception:
        _fail("payload SHA-256 failed")
    return _finish_hash(digest)


def _validate_frozen_constants() -> None:
    static = (
        _RESULT_SCHEMA,
        _RESULT_SCOPE,
        _ORIGIN_STATUS,
        _HASH_PREIMAGE_CONSTRUCTION,
        _STAGE_BASENAME_PREFIX,
        _STAGE_BASENAME_SUFFIX,
        _FIXED_DIRECTIVE,
        _LOWER_HEX32_PATTERN,
        _UPPER_HEX64_PATTERN,
        _WINDOWS_DRIVE_ROOT_PATTERN,
        _RESULT_PROVENANCE,
        _COLLISION_NONCE_SCOPE,
        _STAGING_PARENT_AUTHORITY,
        _PATH_DERIVATION_SCOPE,
        _ANCESTOR_REPARSE_CHECK_SCOPE,
        _BACKING_STORE_SCOPE,
        _HOSTILE_CONCURRENT_REPARSE_PREVENTION,
        _STAGE_EXCLUSIVITY_SCOPE,
        _STAGE_READBACK_SCOPE,
        _STAGE_RETENTION_SCOPE,
        _DURABILITY_SCOPE,
        _CLEANUP_SCOPE,
        _PUBLISHER_SCOPE,
        _STATE_LINEARITY,
        _CONCURRENCY_SCOPE,
        _IDEMPOTENCE_SCOPE,
        _EXACTLY_ONCE_SCOPE,
        _PAYLOAD_CONFIDENTIALITY,
        _ATTEMPT_COMPLETENESS,
        _MARKER_SCOPE,
        _RECOVERY_SCOPE,
        _EPOCH_SCOPE,
        _WITNESS_SCOPE,
        _MANIFEST_SCOPE,
        _REMOTE_PUBLICATION,
        _AUTHORITY_SCOPE,
    )
    expected_static = (
        "lean-rgc-uprime-u1-local-staging-fake-publish-result-v1.0",
        "one_call_changed_branch_nonce_stage_before_pure_normal_fake_cas_return",
        "unknown_may_be_synthetic",
        "payload_streamed_no_full_preimage_materialization",
        "uprime-rpc-fake-cas-stage-v1-",
        ".bin",
        "apply_intended_acknowledge",
        r"[0-9a-f]{32}\Z",
        r"[0-9A-F]{64}\Z",
        r"[A-Za-z]:\\",
        "unauthenticated_forgeable_value_object_not_io_attestation",
        "caller_supplied_collision_separator_not_identity_or_entropy_evidence",
        "caller_supplied_write_location_not_authenticated_namespace",
        "lexical_native_join_no_resolution_or_canonical_binding",
        "not_performed_only_final_parent_entry_observed",
        "unauthenticated_may_be_remote_virtual_or_overlay",
        "not_provided",
        "changed_branch_one_native_path_exclusive_create_only",
        "changed_branch_same_descriptor_exact_bytes_at_one_observation_interval",
        "any_created_stage_retained_no_post_return_lifetime_claim",
        "fsync_not_called_crash_and_power_loss_not_observed",
        "not_performed_any_created_stage_may_remain_after_success_or_error",
        "pure_fake_cas_value_return_changed_branch_stage_gated_not_real_publication",
        "caller_threaded_not_enforced",
        "no_exclusion_or_cross_process_atomicity",
        "not_provided_distinct_nonce_is_explicit_new_attempt",
        "not_provided",
        "not_provided_any_staged_bytes_written_to_caller_location",
        "successful_returns_only_errors_unjournaled",
        "not_created_or_observed",
        "not_performed",
        "none",
        "none",
        "not_read_or_written",
        "not_performed",
        "none",
    )
    if any(type(value) is not str for value in static) or static != expected_static:
        _fail("a frozen string constant is invalid")

    resources = (
        _MAX_PAYLOAD_BYTES,
        _MAX_STAGING_PARENT_UTF8_BYTES,
        _MAX_STAGE_PATH_UTF8_BYTES,
        _COLLISION_NONCE_CHARS,
        _COLLISION_NONCE_BYTES,
        _IO_CHUNK_BYTES,
        _MAX_WRITE_CALLS,
        _MAX_READ_CALLS,
        _MAX_FILESYSTEM_PAYLOAD_WORK_BYTES,
        _MAX_PEAK_TRANSIENT_BUFFER_BYTES,
        _MAX_RETAINED_PAYLOAD_COPY_BYTES,
        _MAX_STAGE_FILE_CREATES,
        _MAX_RETAINED_STAGE_BYTES,
        _MAX_OPERATION_HASH_PREIMAGE_BYTES,
        _STAGE_BASENAME_BYTES,
        _OPEN_MODE,
        _FILE_ATTRIBUTE_REPARSE_POINT,
        _OPEN_FLAGS,
    )
    if any(type(value) is not int or value < 0 for value in resources):
        _fail("a frozen resource constant is invalid")
    if _MAX_PAYLOAD_BYTES != 1_048_576:
        _fail("payload byte bound is invalid")
    if _MAX_STAGING_PARENT_UTF8_BYTES != 4_096:
        _fail("staging parent byte bound is invalid")
    if _COLLISION_NONCE_CHARS != 32 or _COLLISION_NONCE_BYTES != 16:
        _fail("collision nonce dimensions are invalid")
    if _IO_CHUNK_BYTES != 65_536:
        _fail("I/O chunk bound is invalid")
    if _STAGE_BASENAME_BYTES != (
        len(_STAGE_BASENAME_PREFIX.encode("ascii"))
        + _COLLISION_NONCE_CHARS
        + len(_STAGE_BASENAME_SUFFIX.encode("ascii"))
    ):
        _fail("stage basename byte formula is invalid")
    if _STAGE_BASENAME_BYTES != 65:
        _fail("stage basename byte bound is invalid")
    if _MAX_STAGE_PATH_UTF8_BYTES != (
        _MAX_STAGING_PARENT_UTF8_BYTES + 1 + _STAGE_BASENAME_BYTES
    ):
        _fail("stage path byte formula is invalid")
    if _MAX_WRITE_CALLS != _MAX_PAYLOAD_BYTES:
        _fail("write call bound formula is invalid")
    if _MAX_READ_CALLS != (
        (_MAX_PAYLOAD_BYTES + _IO_CHUNK_BYTES - 1) // _IO_CHUNK_BYTES + 1
    ):
        _fail("read call bound formula is invalid")
    if _MAX_FILESYSTEM_PAYLOAD_WORK_BYTES != 2 * _MAX_PAYLOAD_BYTES:
        _fail("filesystem payload work formula is invalid")
    if _MAX_PEAK_TRANSIENT_BUFFER_BYTES != _IO_CHUNK_BYTES:
        _fail("peak transient buffer bound is invalid")
    if _MAX_RETAINED_PAYLOAD_COPY_BYTES != 0:
        _fail("retained payload copy bound is invalid")
    if _MAX_STAGE_FILE_CREATES != 1:
        _fail("stage create bound is invalid")
    if _MAX_RETAINED_STAGE_BYTES != _MAX_PAYLOAD_BYTES:
        _fail("retained stage byte bound is invalid")
    if _OPEN_MODE != 0o600:
        _fail("open mode is invalid")
    if _FILE_ATTRIBUTE_REPARSE_POINT != 0x400:
        _fail("reparse mask is invalid")
    required_open_flags = (os.O_CREAT, os.O_EXCL, os.O_RDWR)
    optional_open_flags = tuple(
        getattr(os, name)
        for name in ("O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_NOFOLLOW")
        if hasattr(os, name)
    )
    if any(
        type(value) is not int or value < 0
        for value in required_open_flags + optional_open_flags
    ):
        _fail("a host open flag is invalid")
    expected_open_flags = 0
    for value in required_open_flags + optional_open_flags:
        expected_open_flags |= value
    if _OPEN_FLAGS != expected_open_flags:
        _fail("the frozen host open flag snapshot is invalid")
    if type(_D_OPERATION) is not bytes or _D_OPERATION != (
        b"lean-rgc-uprime-u1-local-staging-fake-publisher-operation-v1\0"
    ):
        _fail("operation hash domain is invalid")
    if len(_D_OPERATION) != 61:
        _fail("operation hash domain length is invalid")
    expected_preimage_bound = (
        len(_D_OPERATION)
        + 4
        + _MAX_STAGING_PARENT_UTF8_BYTES
        + _COLLISION_NONCE_BYTES
        + 32
        + 4
        + 8
        + _MAX_PAYLOAD_BYTES
        + 8
        + 8
    )
    if _MAX_OPERATION_HASH_PREIMAGE_BYTES != expected_preimage_bound:
        _fail("operation preimage bound formula is invalid")

    if type(_OUTCOME_ROWS) is not tuple or len(_OUTCOME_ROWS) != 3 or any(
        type(row) is not tuple
        or len(row) != 7
        or any(type(cell) is not str for cell in row[:6])
        or type(row[6]) is not bool
        for row in _OUTCOME_ROWS
    ):
        _fail("the outcome table type is invalid")
    if _OUTCOME_ROWS != (
        (
            "cas_conflict_no_stage",
            "expected_state_version_mismatch",
            "conflict_no_change",
            "conflict",
            "not_attempted",
            "not_attempted",
            False,
        ),
        (
            "cas_existing_identical_no_stage",
            "exact_payload_already_current",
            "existing_identical_no_change",
            "existing_identical",
            "not_attempted",
            "not_attempted",
            False,
        ),
        (
            "staged_intended_fake_publish_acknowledged",
            "exact_stage_retained_before_exposing_synthetic_acknowledged_transition",
            "intended_applied_acknowledged",
            "intended_acknowledged",
            "stable_at_endpoint",
            "retained_stable_at_endpoint",
            True,
        ),
    ):
        _fail("the frozen outcome cells are invalid")


def _validate_lexical_inputs(
    staging_parent: object,
    collision_nonce: object,
    /,
) -> tuple[str, bytes, str, bytes, str, str]:
    parent = _require_exact_str(staging_parent, "staging_parent")
    try:
        parent_bytes = parent.encode("utf-8")
    except UnicodeEncodeError:
        _fail("staging_parent is not strict UTF-8")
    if not 1 <= len(parent_bytes) <= _MAX_STAGING_PARENT_UTF8_BYTES:
        _fail("staging_parent UTF-8 length is out of range")
    if any(ord(character) <= 0x1F or ord(character) == 0x7F for character in parent):
        _fail("staging_parent contains a forbidden control character")
    try:
        absolute = _os_path_isabs(parent)
    except Exception:
        _fail("staging_parent absolute-path validation failed")
    if type(absolute) is not bool or absolute is not True:
        _fail("staging_parent is not an absolute path")
    try:
        normalized = _os_path_normpath(parent)
    except Exception:
        _fail("staging_parent normalization failed")
    if type(normalized) is not str or normalized != parent:
        _fail("staging_parent is not in exact normalized lexical form")
    if os.name == "nt":
        if parent.startswith("\\\\") or parent.startswith("//"):
            _fail("Windows UNC and device paths are forbidden")
        if re.match(_WINDOWS_DRIVE_ROOT_PATTERN, parent, flags=re.ASCII) is None:
            _fail("Windows staging_parent must have an explicit drive root")

    nonce = _require_exact_str(collision_nonce, "collision_nonce")
    if re.fullmatch(_LOWER_HEX32_PATTERN, nonce, flags=re.ASCII) is None:
        _fail("collision_nonce is not exact lowercase hex32")
    try:
        nonce_bytes = bytes.fromhex(nonce)
    except (TypeError, ValueError):
        _fail("collision_nonce decoding failed")
    if type(nonce_bytes) is not bytes or len(nonce_bytes) != _COLLISION_NONCE_BYTES:
        _fail("collision_nonce decoded length is invalid")

    basename = _STAGE_BASENAME_PREFIX + nonce + _STAGE_BASENAME_SUFFIX
    try:
        basename_bytes = basename.encode("ascii")
    except UnicodeEncodeError:
        _fail("stage basename is not ASCII")
    if type(basename) is not str or len(basename_bytes) != _STAGE_BASENAME_BYTES:
        _fail("stage basename is invalid")
    try:
        stage_path = _os_path_join(parent, basename)
    except Exception:
        _fail("stage path join failed")
    if type(stage_path) is not str or stage_path == parent:
        _fail("stage path derivation is invalid")
    try:
        stage_path_bytes = stage_path.encode("utf-8")
    except UnicodeEncodeError:
        _fail("stage path is not strict UTF-8")
    if len(stage_path_bytes) > _MAX_STAGE_PATH_UTF8_BYTES:
        _fail("stage path UTF-8 length exceeds its bound")
    return parent, parent_bytes, nonce, nonce_bytes, basename, stage_path


def _normal_transition(
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    /,
) -> InMemoryFakeCasTransitionV10:
    try:
        transition = step_in_memory_fake_cas_v1_0(
            state,
            expected_state_version_sha256,
            proposed_payload,
            "apply_intended_acknowledge",
            None,
        )
    except InMemoryFakeCasV10Error:
        _fail("normal fake-CAS derivation failed")
    except Exception:
        _fail("normal fake-CAS derivation failed")
    if type(transition) is not InMemoryFakeCasTransitionV10:
        _fail("normal fake-CAS derivation returned an invalid type")
    return transition


def _transition_values(value: InMemoryFakeCasTransitionV10, /) -> tuple[object, ...]:
    return (
        value.transition_schema_version,
        value.transition_scope,
        value.origin_status,
        value.before_state,
        value.after_state,
        value.expected_state_version_sha256,
        value.proposed_payload,
        value.proposed_payload_bytes,
        value.proposed_payload_sha256,
        value.synthetic_directive,
        value.alternate_payload,
        value.alternate_payload_bytes,
        value.alternate_payload_sha256,
        value.input_sha256,
        value.outcome,
        value.reason_codes,
        value.expected_version_match,
        value.proposed_equal_before,
        value.directive_reached,
        value.alternate_semantics_checked,
        value.state_changed,
        value.cell_mutation_count,
        value.intended_apply_status,
        value.intended_after_state_version_sha256,
        value.intended_delta_sha256,
        value.actual_delta_sha256,
        value.transition_sha256,
        value.effect_scope,
        value.synthetic_acknowledgement_label,
        value.same_kernel_confirmation_label,
        value.synthetic_client_observation,
        value.model_latent_effect,
        value.payload_byte_limit,
        value.generation_upper_bound,
        value.unique_retained_payload_reference_upper_bound_bytes,
        value.retained_payload_copy_upper_bound_bytes,
        value.state_hash_preimage_upper_bound_bytes,
        value.input_hash_preimage_upper_bound_bytes,
        value.delta_hash_preimage_upper_bound_bytes,
        value.transition_hash_preimage_upper_bound_bytes,
        value.hash_preimage_construction,
        value.directive_origin,
        value.outcome_selection,
        value.confirmation_scope,
        value.cause_scope,
        value.application_attribution,
        value.state_provenance,
        value.lineage_enforcement,
        value.fork_handling,
        value.idempotence_scope,
        value.exactly_once_scope,
        value.persistence_scope,
        value.concurrency_scope,
        value.filesystem_staging,
        value.remote_publication,
        value.durability_scope,
        value.marker_scope,
        value.recovery_scope,
        value.witness_scope,
        value.manifest_scope,
        value.authority_scope,
        value.canonical_remote_authority,
        value.licenses_execution,
        value.licenses_publication,
        value.licenses_recovery,
        value.licenses_later_stage,
    )


def _snapshot_transition(
    value: object,
    /,
) -> InMemoryFakeCasTransitionV10:
    if type(value) is not InMemoryFakeCasTransitionV10:
        _fail("cas_transition is not the exact public Transition type")
    try:
        snapshot = InMemoryFakeCasTransitionV10(*_transition_values(value))
    except InMemoryFakeCasV10Error:
        _fail("cas_transition is structurally invalid")
    except Exception:
        _fail("cas_transition fields are missing or invalid")
    return snapshot


def _validated_transition(
    value: object,
    /,
) -> InMemoryFakeCasTransitionV10:
    snapshot = _snapshot_transition(value)
    expected = _normal_transition(
        snapshot.before_state,
        snapshot.expected_state_version_sha256,
        snapshot.proposed_payload,
    )
    if _transition_values(snapshot) != _transition_values(expected):
        _fail("cas_transition fields do not match the fixed normal derivation")
    return snapshot


def _operation_sha256(
    parent_bytes: bytes,
    nonce_bytes: bytes,
    transition_sha256: str,
    outcome_index: int,
    parent_observation_index: int,
    stage_status_index: int,
    stage_payload: bytes | None,
    write_call_count: int,
    read_call_count: int,
    /,
) -> str:
    parent_raw = _require_exact_bytes(parent_bytes, "parent UTF-8 bytes")
    nonce_raw = _require_exact_bytes(nonce_bytes, "collision nonce bytes")
    if len(parent_raw) > _MAX_STAGING_PARENT_UTF8_BYTES:
        _fail("parent UTF-8 bytes exceed their bound")
    if len(nonce_raw) != _COLLISION_NONCE_BYTES:
        _fail("collision nonce bytes have an invalid length")
    transition_hash = _require_hash(transition_sha256, "transition_sha256")
    indices = (
        _require_exact_int(outcome_index, "outcome index"),
        _require_exact_int(parent_observation_index, "parent observation index"),
        _require_exact_int(stage_status_index, "stage status index"),
    )
    if not 1 <= indices[0] <= 3 or not 1 <= indices[1] <= 2 or not 1 <= indices[2] <= 2:
        _fail("an operation tag index is out of range")
    writes = _require_exact_int(write_call_count, "write_call_count")
    reads = _require_exact_int(read_call_count, "read_call_count")
    if writes < 0 or reads < 0:
        _fail("an operation call count is negative")
    if stage_payload is None:
        optional_tag = 0
        payload = None
    else:
        optional_tag = 1
        payload = _require_exact_bytes(stage_payload, "stage payload")
        if len(payload) > _MAX_PAYLOAD_BYTES:
            _fail("stage payload exceeds its byte bound")
    try:
        digest = hashlib.sha256()
        digest.update(_D_OPERATION)
        digest.update(_u32(len(parent_raw)))
        digest.update(parent_raw)
        digest.update(nonce_raw)
        digest.update(bytes.fromhex(transition_hash))
        digest.update(bytes((indices[0], indices[1], indices[2], optional_tag)))
        if payload is not None:
            digest.update(_u64(len(payload)))
            digest.update(payload)
        digest.update(_u64(writes))
        digest.update(_u64(reads))
    except LocalStagingFakePublisherV10Error:
        raise
    except Exception:
        _fail("operation SHA-256 failed")
    return _finish_hash(digest)


def _row_for_transition(
    transition: InMemoryFakeCasTransitionV10,
    /,
) -> tuple[int, tuple[str, str, str, str, str, str, bool]]:
    for index, row in enumerate(_OUTCOME_ROWS):
        if transition.outcome == row[2]:
            return index, row
    _fail("the fixed normal fake-CAS outcome is invalid")


def _derive_result_values(
    staging_parent: object,
    collision_nonce: object,
    cas_transition: object,
    write_call_count: object,
    /,
) -> tuple[object, ...]:
    _validate_frozen_constants()
    parent, parent_bytes, nonce, nonce_bytes, basename, stage_path = (
        _validate_lexical_inputs(staging_parent, collision_nonce)
    )
    transition = _validated_transition(cas_transition)
    writes = _require_exact_int(write_call_count, "write_call_count")
    outcome_index, row = _row_for_transition(transition)
    has_stage = row[6]
    if has_stage:
        payload = transition.proposed_payload
        payload_bytes = len(payload)
        if payload_bytes == 0:
            if writes != 0:
                _fail("empty staged payload must have zero writes")
        else:
            minimum_writes = (
                payload_bytes + _IO_CHUNK_BYTES - 1
            ) // _IO_CHUNK_BYTES
            if writes < minimum_writes or writes > payload_bytes:
                _fail("write_call_count is impossible for the staged payload")
        if writes > _MAX_WRITE_CALLS:
            _fail("write_call_count exceeds its bound")
        reads = (payload_bytes + _IO_CHUNK_BYTES - 1) // _IO_CHUNK_BYTES + 1
        payload_sha256 = _raw_payload_sha256(payload)
        parent_index = 2
        stage_index = 2
    else:
        if writes != 0:
            _fail("a no-stage outcome must have zero writes")
        payload = None
        payload_bytes = None
        payload_sha256 = None
        reads = 0
        parent_index = 1
        stage_index = 1
    if reads > _MAX_READ_CALLS:
        _fail("read_call_count exceeds its bound")
    operation_sha256 = _operation_sha256(
        parent_bytes,
        nonce_bytes,
        transition.transition_sha256,
        outcome_index + 1,
        parent_index,
        stage_index,
        payload,
        writes,
        reads,
    )
    return (
        _RESULT_SCHEMA,
        _RESULT_SCOPE,
        _ORIGIN_STATUS,
        parent,
        nonce,
        basename,
        stage_path,
        cas_transition,
        row[0],
        (row[1],),
        row[3],
        row[4],
        row[5],
        payload_bytes,
        payload_sha256,
        writes,
        reads,
        operation_sha256,
        _MAX_PAYLOAD_BYTES,
        _MAX_STAGING_PARENT_UTF8_BYTES,
        _MAX_STAGE_PATH_UTF8_BYTES,
        _COLLISION_NONCE_CHARS,
        _IO_CHUNK_BYTES,
        _MAX_WRITE_CALLS,
        _MAX_READ_CALLS,
        _MAX_FILESYSTEM_PAYLOAD_WORK_BYTES,
        _MAX_PEAK_TRANSIENT_BUFFER_BYTES,
        _MAX_RETAINED_PAYLOAD_COPY_BYTES,
        _MAX_STAGE_FILE_CREATES,
        _MAX_RETAINED_STAGE_BYTES,
        _MAX_OPERATION_HASH_PREIMAGE_BYTES,
        _HASH_PREIMAGE_CONSTRUCTION,
        _RESULT_PROVENANCE,
        _COLLISION_NONCE_SCOPE,
        _STAGING_PARENT_AUTHORITY,
        _PATH_DERIVATION_SCOPE,
        _ANCESTOR_REPARSE_CHECK_SCOPE,
        _BACKING_STORE_SCOPE,
        _HOSTILE_CONCURRENT_REPARSE_PREVENTION,
        _STAGE_EXCLUSIVITY_SCOPE,
        _STAGE_READBACK_SCOPE,
        _STAGE_RETENTION_SCOPE,
        _DURABILITY_SCOPE,
        _CLEANUP_SCOPE,
        _PUBLISHER_SCOPE,
        _STATE_LINEARITY,
        _CONCURRENCY_SCOPE,
        _IDEMPOTENCE_SCOPE,
        _EXACTLY_ONCE_SCOPE,
        _PAYLOAD_CONFIDENTIALITY,
        _ATTEMPT_COMPLETENESS,
        _MARKER_SCOPE,
        _RECOVERY_SCOPE,
        _EPOCH_SCOPE,
        _WITNESS_SCOPE,
        _MANIFEST_SCOPE,
        _REMOTE_PUBLICATION,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )


def _result_values(value: LocalStagingFakePublishResultV10, /) -> tuple[object, ...]:
    return (
        value.result_schema_version,
        value.result_scope,
        value.origin_status,
        value.staging_parent,
        value.collision_nonce,
        value.stage_basename,
        value.stage_path,
        value.cas_transition,
        value.outcome,
        value.reason_codes,
        value.cas_gate_status,
        value.parent_observation_status,
        value.stage_status,
        value.stage_payload_bytes,
        value.stage_payload_sha256,
        value.write_call_count,
        value.read_call_count,
        value.operation_sha256,
        value.payload_byte_limit,
        value.staging_parent_utf8_byte_limit,
        value.stage_path_utf8_byte_limit,
        value.collision_nonce_chars,
        value.io_chunk_bytes,
        value.write_call_upper_bound,
        value.read_call_upper_bound,
        value.filesystem_payload_work_upper_bound_bytes,
        value.peak_transient_buffer_upper_bound_bytes,
        value.retained_payload_copy_upper_bound_bytes,
        value.stage_file_create_upper_bound,
        value.retained_stage_byte_upper_bound,
        value.operation_hash_preimage_upper_bound_bytes,
        value.hash_preimage_construction,
        value.result_provenance,
        value.collision_nonce_scope,
        value.staging_parent_authority,
        value.path_derivation_scope,
        value.ancestor_reparse_check_scope,
        value.backing_store_scope,
        value.hostile_concurrent_reparse_prevention,
        value.stage_exclusivity_scope,
        value.stage_readback_scope,
        value.stage_retention_scope,
        value.durability_scope,
        value.cleanup_scope,
        value.publisher_scope,
        value.state_linearity,
        value.concurrency_scope,
        value.idempotence_scope,
        value.exactly_once_scope,
        value.payload_confidentiality,
        value.attempt_completeness,
        value.marker_scope,
        value.recovery_scope,
        value.epoch_scope,
        value.witness_scope,
        value.manifest_scope,
        value.remote_publication,
        value.authority_scope,
        value.canonical_remote_authority,
        value.licenses_execution,
        value.licenses_publication,
        value.licenses_recovery,
        value.licenses_later_stage,
    )


def _validate_result_field_types(value: LocalStagingFakePublishResultV10, /) -> None:
    string_names = (
        "result_schema_version",
        "result_scope",
        "origin_status",
        "staging_parent",
        "collision_nonce",
        "stage_basename",
        "stage_path",
        "outcome",
        "cas_gate_status",
        "parent_observation_status",
        "stage_status",
        "hash_preimage_construction",
        "result_provenance",
        "collision_nonce_scope",
        "staging_parent_authority",
        "path_derivation_scope",
        "ancestor_reparse_check_scope",
        "backing_store_scope",
        "hostile_concurrent_reparse_prevention",
        "stage_exclusivity_scope",
        "stage_readback_scope",
        "stage_retention_scope",
        "durability_scope",
        "cleanup_scope",
        "publisher_scope",
        "state_linearity",
        "concurrency_scope",
        "idempotence_scope",
        "exactly_once_scope",
        "payload_confidentiality",
        "attempt_completeness",
        "marker_scope",
        "recovery_scope",
        "epoch_scope",
        "witness_scope",
        "manifest_scope",
        "remote_publication",
        "authority_scope",
    )
    for name in string_names:
        _require_exact_str(getattr(value, name), name)
    if type(value.cas_transition) is not InMemoryFakeCasTransitionV10:
        _fail("cas_transition is not the exact public Transition type")
    if type(value.reason_codes) is not tuple or len(value.reason_codes) != 1:
        _fail("reason_codes must be an exact one-element tuple")
    _require_exact_str(value.reason_codes[0], "reason code")
    integer_names = (
        "write_call_count",
        "read_call_count",
        "payload_byte_limit",
        "staging_parent_utf8_byte_limit",
        "stage_path_utf8_byte_limit",
        "collision_nonce_chars",
        "io_chunk_bytes",
        "write_call_upper_bound",
        "read_call_upper_bound",
        "filesystem_payload_work_upper_bound_bytes",
        "peak_transient_buffer_upper_bound_bytes",
        "retained_payload_copy_upper_bound_bytes",
        "stage_file_create_upper_bound",
        "retained_stage_byte_upper_bound",
        "operation_hash_preimage_upper_bound_bytes",
    )
    for name in integer_names:
        _require_exact_int(getattr(value, name), name)
    if value.stage_payload_bytes is not None:
        _require_exact_int(value.stage_payload_bytes, "stage_payload_bytes")
    _require_hash(value.operation_sha256, "operation_sha256")
    if value.stage_payload_sha256 is not None:
        _require_hash(value.stage_payload_sha256, "stage_payload_sha256")
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        _require_exact_bool(getattr(value, name), name)


def _validate_result(value: LocalStagingFakePublishResultV10, /) -> None:
    try:
        _validate_frozen_constants()
        if type(value) is not LocalStagingFakePublishResultV10:
            _fail("result is not the exact public Result type")
        _validate_result_field_types(value)
        expected = _derive_result_values(
            value.staging_parent,
            value.collision_nonce,
            value.cas_transition,
            value.write_call_count,
        )
        if _result_values(value) != expected:
            _fail("result fields do not match their derivation")
    except LocalStagingFakePublisherV10Error:
        raise
    except InMemoryFakeCasV10Error:
        _fail("result fake-CAS revalidation failed")
    except Exception:
        _fail("result fields are missing or invalid")


def _stat_integer(value: object, name: str, /) -> int:
    try:
        component = getattr(value, name)
    except Exception:
        _fail(f"{name} is missing or unreadable")
    number = _require_exact_int(component, name)
    if number < 0:
        _fail(f"{name} is negative")
    return number


def _reparse_status(value: object, mode: int, /) -> bool:
    try:
        attributes = getattr(value, "st_file_attributes")
    except AttributeError:
        attributes = 0
    except Exception:
        _fail("st_file_attributes is unreadable")
    attributes_value = _require_exact_int(attributes, "st_file_attributes")
    if attributes_value < 0:
        _fail("st_file_attributes is negative")
    return bool(
        stat.S_ISLNK(mode)
        or (attributes_value & _FILE_ATTRIBUTE_REPARSE_POINT)
    )


def _directory_snapshot(value: object, context: str, /) -> tuple[int, int, int, bool]:
    device = _stat_integer(value, "st_dev")
    inode = _stat_integer(value, "st_ino")
    mode = _stat_integer(value, "st_mode")
    reparse = _reparse_status(value, mode)
    if reparse:
        _fail(f"{context} is a symlink or reparse entry")
    if not stat.S_ISDIR(mode):
        _fail(f"{context} is not a directory")
    return device, inode, mode, reparse


def _descriptor_snapshot(
    value: object,
    context: str,
    /,
) -> tuple[int, int, int, int, int, int]:
    device = _stat_integer(value, "st_dev")
    inode = _stat_integer(value, "st_ino")
    mode = _stat_integer(value, "st_mode")
    ctime_ns = _stat_integer(value, "st_ctime_ns")
    size = _stat_integer(value, "st_size")
    mtime_ns = _stat_integer(value, "st_mtime_ns")
    if _reparse_status(value, mode):
        _fail(f"{context} is a symlink or reparse entry")
    if not stat.S_ISREG(mode):
        _fail(f"{context} is not a regular file")
    return device, inode, mode, ctime_ns, size, mtime_ns


def _path_snapshot(
    value: object,
    context: str,
    /,
) -> tuple[int, int, int, bool, int, int, int]:
    device = _stat_integer(value, "st_dev")
    inode = _stat_integer(value, "st_ino")
    mode = _stat_integer(value, "st_mode")
    reparse = _reparse_status(value, mode)
    ctime_ns = _stat_integer(value, "st_ctime_ns")
    size = _stat_integer(value, "st_size")
    mtime_ns = _stat_integer(value, "st_mtime_ns")
    if reparse:
        _fail(f"{context} is a symlink or reparse entry")
    if not stat.S_ISREG(mode):
        _fail(f"{context} is not a regular file")
    return device, inode, mode, reparse, ctime_ns, size, mtime_ns


def _nofollow_stat(path: str, context: str, /) -> object:
    try:
        return _os_stat(path, follow_symlinks=False)
    except Exception:
        _fail(f"{context} no-follow stat failed")


def _descriptor_stat(fd: int, context: str, /) -> object:
    try:
        return _os_fstat(fd)
    except Exception:
        _fail(f"{context} descriptor stat failed")


def _exclusive_open(stage_path: str, /) -> int:
    try:
        fd = _os_open(stage_path, _OPEN_FLAGS, _OPEN_MODE)
    except FileExistsError:
        _fail("the supplied collision nonce path is occupied")
    except Exception:
        _fail("exclusive stage create failed")
    descriptor = _require_exact_int(fd, "stage descriptor")
    if descriptor < 0:
        _fail("stage descriptor is negative")
    return descriptor


def _descriptor_owner(fd: int, /) -> object:
    class _DescriptorOwner:
        __slots__ = ("_fd",)

        def __init__(self, descriptor: int, /) -> None:
            self._fd = descriptor

        def __enter__(self) -> int:
            return self._fd

        def __exit__(
            self,
            exc_type: object,
            exc_value: BaseException | None,
            traceback: object,
        ) -> bool:
            del exc_type, traceback
            try:
                result = _os_close(self._fd)
            except Exception:
                if exc_value is not None and not isinstance(exc_value, Exception):
                    return False
                _fail("stage descriptor close failed")
            if result is not None:
                if exc_value is not None and not isinstance(exc_value, Exception):
                    return False
                _fail("stage descriptor close returned a non-None value")
            return False

    return _DescriptorOwner(fd)


def _write_payload(fd: int, payload: bytes, /) -> int:
    view = memoryview(payload)
    offset = 0
    calls = 0
    while offset < len(view):
        if calls >= _MAX_WRITE_CALLS:
            _fail("write call bound would be exceeded")
        request_size = min(_IO_CHUNK_BYTES, len(view) - offset)
        request = view[offset : offset + request_size]
        try:
            written = _os_write(fd, request)
        except Exception:
            _fail("stage write failed")
        count = _require_exact_int(written, "write return")
        if count < 1 or count > request_size:
            _fail("stage write returned invalid progress")
        calls += 1
        offset += count
    return calls


def _readback_payload(fd: int, payload: bytes, /) -> tuple[int, str]:
    try:
        seek_result = _os_lseek(fd, 0, os.SEEK_SET)
    except Exception:
        _fail("stage seek failed")
    if _require_exact_int(seek_result, "seek return") != 0:
        _fail("stage seek did not return exact zero")
    view = memoryview(payload)
    offset = 0
    calls = 0
    try:
        digest = hashlib.sha256()
    except Exception:
        _fail("readback SHA-256 initialization failed")
    while offset < len(view):
        request_size = min(_IO_CHUNK_BYTES, len(view) - offset)
        try:
            chunk = _os_read(fd, request_size)
        except Exception:
            _fail("stage readback failed")
        calls += 1
        if calls > _MAX_READ_CALLS:
            _fail("read call bound was exceeded")
        raw = _require_exact_bytes(chunk, "read return")
        if len(raw) != request_size:
            _fail("stage readback was short or overlong")
        if raw != view[offset : offset + request_size]:
            _fail("stage raw readback differs from the proposal")
        try:
            digest.update(raw)
        except Exception:
            _fail("readback SHA-256 update failed")
        del raw
        del chunk
        offset += request_size
    try:
        eof = _os_read(fd, 1)
    except Exception:
        _fail("stage EOF probe failed")
    calls += 1
    if calls > _MAX_READ_CALLS:
        _fail("read call bound was exceeded")
    if type(eof) is not bytes or eof != b"":
        _fail("stage EOF probe detected growth or an invalid return")
    return calls, _finish_hash(digest)


def _stage_payload(
    staging_parent: str,
    stage_path: str,
    payload: bytes,
    /,
) -> tuple[int, int, str]:
    d0 = _directory_snapshot(
        _nofollow_stat(staging_parent, "initial parent"),
        "initial parent",
    )
    fd = _exclusive_open(stage_path)
    with _descriptor_owner(fd):
        try:
            f0 = _descriptor_snapshot(
                _descriptor_stat(fd, "initial stage"),
                "initial stage",
            )
            if f0[4] != 0:
                _fail("the newly created stage is not empty")
            write_calls = _write_payload(fd, payload)
            f1 = _descriptor_snapshot(
                _descriptor_stat(fd, "post-write stage"),
                "post-write stage",
            )
            if (f1[0], f1[1], stat.S_IFMT(f1[2])) != (
                f0[0],
                f0[1],
                stat.S_IFMT(f0[2]),
            ):
                _fail("stage descriptor identity changed after writing")
            if f1[4] != len(payload):
                _fail("stage size does not equal the proposal length")
            read_calls, readback_sha256 = _readback_payload(fd, payload)
            f2 = _descriptor_snapshot(
                _descriptor_stat(fd, "post-readback stage"),
                "post-readback stage",
            )
            if f2 != f1:
                _fail("stage descriptor metadata drifted during readback")
            if readback_sha256 != _raw_payload_sha256(payload):
                _fail("stage readback SHA-256 differs from the proposal")
        except LocalStagingFakePublisherV10Error:
            raise
        except Exception:
            _fail("changed-branch staging failed")

    path_snapshot = _path_snapshot(
        _nofollow_stat(stage_path, "retained stage"),
        "retained stage",
    )
    if (path_snapshot[0], path_snapshot[1], path_snapshot[5]) != (
        f2[0],
        f2[1],
        f2[4],
    ):
        _fail("retained path does not match the closed stage descriptor")
    d1 = _directory_snapshot(
        _nofollow_stat(staging_parent, "final parent"),
        "final parent",
    )
    if d1 != d0:
        _fail("staging parent drifted during the observation interval")
    return write_calls, read_calls, readback_sha256


def stage_and_fake_publish_normal_v1_0(
    staging_parent: str,
    collision_nonce: str,
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    /,
) -> LocalStagingFakePublishResultV10:
    _validate_frozen_constants()
    if type(state) is not InMemoryFakeCasStateV10:
        _fail("state is not the exact public State type")
    _require_exact_str(expected_state_version_sha256, "expected_state_version_sha256")
    _require_exact_bytes(proposed_payload, "proposed_payload")
    parent, _, nonce, _, _, stage_path = _validate_lexical_inputs(
        staging_parent,
        collision_nonce,
    )
    transition = _normal_transition(
        state,
        expected_state_version_sha256,
        proposed_payload,
    )
    _, row = _row_for_transition(transition)
    if not row[6]:
        values = _derive_result_values(parent, nonce, transition, 0)
        return LocalStagingFakePublishResultV10(*values)

    write_calls, read_calls, readback_sha256 = _stage_payload(
        parent,
        stage_path,
        proposed_payload,
    )
    expected_reads = (
        len(proposed_payload) + _IO_CHUNK_BYTES - 1
    ) // _IO_CHUNK_BYTES + 1
    if read_calls != expected_reads:
        _fail("actual read call count is inconsistent")
    if readback_sha256 != _raw_payload_sha256(proposed_payload):
        _fail("actual staged payload hash is inconsistent")
    values = _derive_result_values(parent, nonce, transition, write_calls)
    return LocalStagingFakePublishResultV10(*values)
