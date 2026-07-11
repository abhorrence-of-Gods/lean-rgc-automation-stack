from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


__all__ = [
    "InMemoryFakeCasV10Error",
    "InMemoryFakeCasStateV10",
    "InMemoryFakeCasTransitionV10",
    "initial_in_memory_fake_cas_state_v1_0",
    "step_in_memory_fake_cas_v1_0",
]


_STATE_SCHEMA = "lean-rgc-uprime-u1-in-memory-fake-cas-state-v1.0"
_STATE_SCOPE = "one_anonymous_in_memory_value_cell"
_TRANSITION_SCHEMA = "lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1.0"
_TRANSITION_SCOPE = "pure_single_call_one_cell_cas_derivation"
_ORIGIN_STATUS = "unknown_may_be_synthetic"

_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_GENERATION = 9_223_372_036_854_775_807
_MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES = 3_145_728
_MAX_RETAINED_PAYLOAD_COPY_BYTES = 0

_D_STATE = b"lean-rgc-uprime-u1-in-memory-fake-cas-state-v1\0"
_D_INPUT = b"lean-rgc-uprime-u1-in-memory-fake-cas-input-v1\0"
_D_DELTA = b"lean-rgc-uprime-u1-in-memory-fake-cas-delta-v1\0"
_D_TRANSITION = b"lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1\0"

_MAX_STATE_HASH_PREIMAGE_BYTES = 1_048_640
_MAX_INPUT_HASH_PREIMAGE_BYTES = 2_097_249
_MAX_DELTA_HASH_PREIMAGE_BYTES = 1_048_695
_MAX_TRANSITION_HASH_PREIMAGE_BYTES = 467

_VERSION_SCOPE = "comparison_value_not_capability"
_RAW_EQUALITY_SCOPE = "exact_bytes_not_digest_only"
_STATE_PROVENANCE = "unauthenticated_forgeable_value_object"
_LINEAGE_ENFORCEMENT = "caller_must_thread_returned_state_not_enforced"
_FORK_HANDLING = "forks_allowed_no_global_linearity"
_DELETION_SUPPORT = "unsupported_proposals_are_exact_bytes"
_PERSISTENCE_SCOPE = "none_process_memory_only"
_CONCURRENCY_SCOPE = "none_pure_single_call_transition"
_REMOTE_CAS_AUTHENTICATION = "not_performed"
_AUTHORITY_SCOPE = "none"

_HASH_PREIMAGE_CONSTRUCTION = "payloads_streamed_no_full_preimage_materialization"
_DIRECTIVE_ORIGIN = "caller_supplied_repeatable_synthetic_choice"
_OUTCOME_SELECTION = (
    "input_validation_then_conflict_then_exact_identity_then_directive"
)
_CONFIRMATION_SCOPE = "same_call_same_kernel_not_independent"
_CAUSE_SCOPE = "not_modeled_no_causal_fault_claim"
_APPLICATION_ATTRIBUTION = "not_authenticated"
_IDEMPOTENCE_SCOPE = "not_provided_no_operation_identity"
_EXACTLY_ONCE_SCOPE = "not_provided"
_FILESYSTEM_STAGING = "not_performed"
_REMOTE_PUBLICATION = "not_performed"
_DURABILITY_SCOPE = "not_observed"
_MARKER_SCOPE = "not_created_or_observed"
_RECOVERY_SCOPE = "not_performed"
_WITNESS_SCOPE = "not_issued_or_verified"
_MANIFEST_SCOPE = "not_read_or_written"

_DIRECTIVES = (
    "apply_intended_acknowledge",
    "apply_intended_lose_ack_then_confirm",
    "apply_intended_lose_ack_confirmation_unavailable",
    "substitute_alternate_then_confirm_wrong_delta",
)
_OUTCOMES = (
    "conflict_no_change",
    "existing_identical_no_change",
    "intended_applied_acknowledged",
    "intended_applied_ack_lost_confirmed",
    "intended_applied_ack_lost_unconfirmed",
    "wrong_delta_confirmed",
)
_OUTCOME_ROWS = (
    (
        "expected_state_version_mismatch",
        "not_attempted",
        "no_change",
        "not_attempted",
        "not_attempted",
        "conflict",
        "unchanged",
    ),
    (
        "exact_payload_already_current",
        "not_attempted_existing_identical",
        "no_change_existing_identical",
        "not_attempted",
        "not_attempted",
        "existing_identical",
        "unchanged_existing_identical",
    ),
    (
        "matched_intended_apply_acknowledged",
        "applied",
        "intended_applied",
        "delivered",
        "not_attempted",
        "applied",
        "intended_applied",
    ),
    (
        "matched_intended_apply_ack_lost_confirmed",
        "applied",
        "intended_applied",
        "lost",
        "same_kernel_observed_intended",
        "applied_after_same_kernel_confirmation",
        "intended_applied",
    ),
    (
        "matched_intended_apply_ack_lost_confirmation_unavailable",
        "applied",
        "intended_applied",
        "lost",
        "unavailable",
        "ambiguous",
        "intended_applied",
    ),
    (
        "matched_alternate_substitution_confirmed_wrong_delta",
        "not_applied_alternate_substituted",
        "alternate_applied",
        "not_applicable_intended_not_applied",
        "same_kernel_observed_wrong_delta",
        "wrong_delta",
        "alternate_applied",
    ),
)

_UPPER_HEX64_RE = re.compile(r"[0-9A-F]{64}\Z", flags=re.ASCII)


class InMemoryFakeCasV10Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InMemoryFakeCasStateV10:
    state_schema_version: str
    state_scope: str
    origin_status: str
    generation: int
    cell_state: str
    cell_payload: bytes | None
    cell_payload_bytes: int | None
    cell_payload_sha256: str | None
    state_version_sha256: str
    payload_byte_limit: int
    generation_upper_bound: int
    version_scope: str
    raw_equality_scope: str
    state_provenance: str
    lineage_enforcement: str
    fork_handling: str
    deletion_support: str
    persistence_scope: str
    concurrency_scope: str
    remote_cas_authentication: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_state(self)


@dataclass(frozen=True, slots=True)
class InMemoryFakeCasTransitionV10:
    transition_schema_version: str
    transition_scope: str
    origin_status: str
    before_state: InMemoryFakeCasStateV10
    after_state: InMemoryFakeCasStateV10
    expected_state_version_sha256: str
    proposed_payload: bytes
    proposed_payload_bytes: int
    proposed_payload_sha256: str
    synthetic_directive: str
    alternate_payload: bytes | None
    alternate_payload_bytes: int | None
    alternate_payload_sha256: str | None
    input_sha256: str
    outcome: str
    reason_codes: tuple[str, ...]
    expected_version_match: bool
    proposed_equal_before: bool | None
    directive_reached: bool
    alternate_semantics_checked: bool
    state_changed: bool
    cell_mutation_count: int
    intended_apply_status: str
    intended_after_state_version_sha256: str | None
    intended_delta_sha256: str | None
    actual_delta_sha256: str | None
    transition_sha256: str
    effect_scope: str
    synthetic_acknowledgement_label: str
    same_kernel_confirmation_label: str
    synthetic_client_observation: str
    model_latent_effect: str
    payload_byte_limit: int
    generation_upper_bound: int
    unique_retained_payload_reference_upper_bound_bytes: int
    retained_payload_copy_upper_bound_bytes: int
    state_hash_preimage_upper_bound_bytes: int
    input_hash_preimage_upper_bound_bytes: int
    delta_hash_preimage_upper_bound_bytes: int
    transition_hash_preimage_upper_bound_bytes: int
    hash_preimage_construction: str
    directive_origin: str
    outcome_selection: str
    confirmation_scope: str
    cause_scope: str
    application_attribution: str
    state_provenance: str
    lineage_enforcement: str
    fork_handling: str
    idempotence_scope: str
    exactly_once_scope: str
    persistence_scope: str
    concurrency_scope: str
    filesystem_staging: str
    remote_publication: str
    durability_scope: str
    marker_scope: str
    recovery_scope: str
    witness_scope: str
    manifest_scope: str
    authority_scope: str
    canonical_remote_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_transition(self)


def _fail(message: str) -> None:
    raise InMemoryFakeCasV10Error(message) from None


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
    if not _require_exact_bool(value, name):
        return
    _fail(f"{name} must be exact false")


def _require_exact_bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes:
        _fail(f"{name} is not exact bytes")
    return value


def _require_none(value: object, name: str) -> None:
    if value is not None:
        _fail(f"{name} must be exact None")


def _require_hash(value: object, name: str) -> str:
    text = _require_exact_str(value, name)
    if _UPPER_HEX64_RE.fullmatch(text) is None:
        _fail(f"{name} is not exact uppercase hex64")
    return text


def _u16(value: int, /) -> bytes:
    number = _require_exact_int(value, "u16 value")
    if number < 0 or number > 65_535:
        _fail("u16 value is out of range")
    return number.to_bytes(2, "big")


def _u64(value: int, /) -> bytes:
    number = _require_exact_int(value, "u64 value")
    if number < 0 or number > 18_446_744_073_709_551_615:
        _fail("u64 value is out of range")
    return number.to_bytes(8, "big")


def _ascii_bytes(value: str, /) -> bytes:
    text = _require_exact_str(value, "ASCII value")
    try:
        encoded = text.encode("ascii")
    except UnicodeEncodeError:
        _fail("ASCII value is not ASCII")
    if len(encoded) > 65_535:
        _fail("ASCII value is too long")
    return encoded


def _update_ascii(digest: object, value: str, /) -> None:
    encoded = _ascii_bytes(value)
    digest.update(_u16(len(encoded)))
    digest.update(encoded)


def _finish_hash(digest: object, /) -> str:
    return digest.hexdigest().upper()


def _raw_payload_sha256(payload: bytes, /) -> str:
    raw = _require_exact_bytes(payload, "payload")
    return hashlib.sha256(raw).hexdigest().upper()


def _state_version_sha256(generation: int, payload: bytes | None, /) -> str:
    digest = hashlib.sha256()
    digest.update(_D_STATE)
    digest.update(_u64(generation))
    if payload is None:
        digest.update(b"\x00")
    else:
        raw = _require_exact_bytes(payload, "state payload")
        digest.update(b"\x01")
        digest.update(_u64(len(raw)))
        digest.update(raw)
    return _finish_hash(digest)


def _input_sha256(
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    directive_index: int,
    alternate_payload: bytes | None,
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_INPUT)
    digest.update(bytes.fromhex(expected_state_version_sha256))
    digest.update(_u64(len(proposed_payload)))
    digest.update(proposed_payload)
    digest.update(bytes((directive_index + 1,)))
    if alternate_payload is None:
        digest.update(b"\x00")
    else:
        digest.update(b"\x01")
        digest.update(_u64(len(alternate_payload)))
        digest.update(alternate_payload)
    return _finish_hash(digest)


def _delta_sha256(
    before_state_version_sha256: str,
    after_state_version_sha256: str,
    applied_payload: bytes,
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_DELTA)
    digest.update(bytes.fromhex(before_state_version_sha256))
    digest.update(bytes.fromhex(after_state_version_sha256))
    digest.update(_u64(len(applied_payload)))
    digest.update(applied_payload)
    return _finish_hash(digest)


def _update_optional_hash(digest: object, value: str | None, /) -> None:
    if value is None:
        digest.update(b"\x00")
    else:
        digest.update(b"\x01")
        digest.update(bytes.fromhex(value))


def _transition_sha256(
    input_sha256: str,
    outcome_index: int,
    before_state_version_sha256: str,
    intended_after_state_version_sha256: str | None,
    intended_delta_sha256: str | None,
    actual_delta_sha256: str | None,
    after_state_version_sha256: str,
    cell_mutation_count: int,
    outcome_row: tuple[str, str, str, str, str, str, str],
    /,
) -> str:
    digest = hashlib.sha256()
    digest.update(_D_TRANSITION)
    digest.update(bytes.fromhex(input_sha256))
    digest.update(bytes((outcome_index + 1,)))
    digest.update(bytes.fromhex(before_state_version_sha256))
    _update_optional_hash(digest, intended_after_state_version_sha256)
    _update_optional_hash(digest, intended_delta_sha256)
    _update_optional_hash(digest, actual_delta_sha256)
    digest.update(bytes.fromhex(after_state_version_sha256))
    digest.update(_u64(cell_mutation_count))
    for value in outcome_row:
        _update_ascii(digest, value)
    return _finish_hash(digest)


def _transition_preimage_lengths() -> tuple[int, int, int, int, int, int]:
    values = []
    for index, row in enumerate(_OUTCOME_ROWS):
        optional_hash_bytes = 3 if index < 2 else 99
        length = (
            len(_D_TRANSITION)
            + 32
            + 1
            + 32
            + optional_hash_bytes
            + 32
            + 8
        )
        for value in row:
            length += 2 + len(_ascii_bytes(value))
        values.append(length)
    return tuple(values)


def _validate_frozen_constants() -> None:
    static = (
        _STATE_SCHEMA,
        _STATE_SCOPE,
        _TRANSITION_SCHEMA,
        _TRANSITION_SCOPE,
        _ORIGIN_STATUS,
        _VERSION_SCOPE,
        _RAW_EQUALITY_SCOPE,
        _STATE_PROVENANCE,
        _LINEAGE_ENFORCEMENT,
        _FORK_HANDLING,
        _DELETION_SUPPORT,
        _PERSISTENCE_SCOPE,
        _CONCURRENCY_SCOPE,
        _REMOTE_CAS_AUTHENTICATION,
        _AUTHORITY_SCOPE,
        _HASH_PREIMAGE_CONSTRUCTION,
        _DIRECTIVE_ORIGIN,
        _OUTCOME_SELECTION,
        _CONFIRMATION_SCOPE,
        _CAUSE_SCOPE,
        _APPLICATION_ATTRIBUTION,
        _IDEMPOTENCE_SCOPE,
        _EXACTLY_ONCE_SCOPE,
        _FILESYSTEM_STAGING,
        _REMOTE_PUBLICATION,
        _DURABILITY_SCOPE,
        _MARKER_SCOPE,
        _RECOVERY_SCOPE,
        _WITNESS_SCOPE,
        _MANIFEST_SCOPE,
    )
    expected_static = (
        "lean-rgc-uprime-u1-in-memory-fake-cas-state-v1.0",
        "one_anonymous_in_memory_value_cell",
        "lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1.0",
        "pure_single_call_one_cell_cas_derivation",
        "unknown_may_be_synthetic",
        "comparison_value_not_capability",
        "exact_bytes_not_digest_only",
        "unauthenticated_forgeable_value_object",
        "caller_must_thread_returned_state_not_enforced",
        "forks_allowed_no_global_linearity",
        "unsupported_proposals_are_exact_bytes",
        "none_process_memory_only",
        "none_pure_single_call_transition",
        "not_performed",
        "none",
        "payloads_streamed_no_full_preimage_materialization",
        "caller_supplied_repeatable_synthetic_choice",
        "input_validation_then_conflict_then_exact_identity_then_directive",
        "same_call_same_kernel_not_independent",
        "not_modeled_no_causal_fault_claim",
        "not_authenticated",
        "not_provided_no_operation_identity",
        "not_provided",
        "not_performed",
        "not_performed",
        "not_observed",
        "not_created_or_observed",
        "not_performed",
        "not_issued_or_verified",
        "not_read_or_written",
    )
    if any(type(value) is not str for value in static) or static != expected_static:
        _fail("a frozen scope constant is invalid")
    if any(
        type(value) is not bytes
        for value in (_D_STATE, _D_INPUT, _D_DELTA, _D_TRANSITION)
    ):
        _fail("a frozen hash domain is not exact bytes")
    if (_D_STATE, _D_INPUT, _D_DELTA, _D_TRANSITION) != (
        b"lean-rgc-uprime-u1-in-memory-fake-cas-state-v1\0",
        b"lean-rgc-uprime-u1-in-memory-fake-cas-input-v1\0",
        b"lean-rgc-uprime-u1-in-memory-fake-cas-delta-v1\0",
        b"lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1\0",
    ):
        _fail("a frozen hash domain is invalid")
    if tuple(map(len, (_D_STATE, _D_INPUT, _D_DELTA, _D_TRANSITION))) != (
        47,
        47,
        47,
        52,
    ):
        _fail("a frozen hash domain length is invalid")
    resource_values = (
        _MAX_PAYLOAD_BYTES,
        _MAX_GENERATION,
        _MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES,
        _MAX_RETAINED_PAYLOAD_COPY_BYTES,
        _MAX_STATE_HASH_PREIMAGE_BYTES,
        _MAX_INPUT_HASH_PREIMAGE_BYTES,
        _MAX_DELTA_HASH_PREIMAGE_BYTES,
        _MAX_TRANSITION_HASH_PREIMAGE_BYTES,
    )
    if any(type(value) is not int or value < 0 for value in resource_values):
        _fail("a frozen resource constant is invalid")
    if _MAX_PAYLOAD_BYTES != 1_048_576:
        _fail("payload byte bound is invalid")
    if _MAX_GENERATION != 9_223_372_036_854_775_807:
        _fail("generation bound is invalid")
    if _MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES != 3 * _MAX_PAYLOAD_BYTES:
        _fail("retained reference bound formula is invalid")
    if _MAX_RETAINED_PAYLOAD_COPY_BYTES != 0:
        _fail("retained payload copy bound is invalid")
    if _MAX_STATE_HASH_PREIMAGE_BYTES != len(_D_STATE) + 8 + 1 + 8 + _MAX_PAYLOAD_BYTES:
        _fail("state preimage bound formula is invalid")
    if _MAX_INPUT_HASH_PREIMAGE_BYTES != (
        len(_D_INPUT) + 32 + 8 + _MAX_PAYLOAD_BYTES + 1 + 1 + 8 + _MAX_PAYLOAD_BYTES
    ):
        _fail("input preimage bound formula is invalid")
    if _MAX_DELTA_HASH_PREIMAGE_BYTES != (
        len(_D_DELTA) + 32 + 32 + 8 + _MAX_PAYLOAD_BYTES
    ):
        _fail("delta preimage bound formula is invalid")
    if type(_DIRECTIVES) is not tuple or any(
        type(value) is not str for value in _DIRECTIVES
    ):
        _fail("the directive table type is invalid")
    if _DIRECTIVES != (
        "apply_intended_acknowledge",
        "apply_intended_lose_ack_then_confirm",
        "apply_intended_lose_ack_confirmation_unavailable",
        "substitute_alternate_then_confirm_wrong_delta",
    ):
        _fail("the directive table is invalid")
    if type(_OUTCOMES) is not tuple or any(
        type(value) is not str for value in _OUTCOMES
    ):
        _fail("the outcome table type is invalid")
    if _OUTCOMES != (
        "conflict_no_change",
        "existing_identical_no_change",
        "intended_applied_acknowledged",
        "intended_applied_ack_lost_confirmed",
        "intended_applied_ack_lost_unconfirmed",
        "wrong_delta_confirmed",
    ):
        _fail("the outcome table is invalid")
    if type(_OUTCOME_ROWS) is not tuple or len(_OUTCOME_ROWS) != 6 or any(
        type(row) is not tuple
        or len(row) != 7
        or any(type(value) is not str for value in row)
        for row in _OUTCOME_ROWS
    ):
        _fail("the outcome semantic table is invalid")
    if _OUTCOME_ROWS != (
        (
            "expected_state_version_mismatch",
            "not_attempted",
            "no_change",
            "not_attempted",
            "not_attempted",
            "conflict",
            "unchanged",
        ),
        (
            "exact_payload_already_current",
            "not_attempted_existing_identical",
            "no_change_existing_identical",
            "not_attempted",
            "not_attempted",
            "existing_identical",
            "unchanged_existing_identical",
        ),
        (
            "matched_intended_apply_acknowledged",
            "applied",
            "intended_applied",
            "delivered",
            "not_attempted",
            "applied",
            "intended_applied",
        ),
        (
            "matched_intended_apply_ack_lost_confirmed",
            "applied",
            "intended_applied",
            "lost",
            "same_kernel_observed_intended",
            "applied_after_same_kernel_confirmation",
            "intended_applied",
        ),
        (
            "matched_intended_apply_ack_lost_confirmation_unavailable",
            "applied",
            "intended_applied",
            "lost",
            "unavailable",
            "ambiguous",
            "intended_applied",
        ),
        (
            "matched_alternate_substitution_confirmed_wrong_delta",
            "not_applied_alternate_substituted",
            "alternate_applied",
            "not_applicable_intended_not_applied",
            "same_kernel_observed_wrong_delta",
            "wrong_delta",
            "alternate_applied",
        ),
    ):
        _fail("the frozen outcome semantic cells are invalid")
    lengths = _transition_preimage_lengths()
    if lengths != (270, 335, 373, 421, 389, 467):
        _fail("transition preimage lengths are invalid")
    if _MAX_TRANSITION_HASH_PREIMAGE_BYTES != max(lengths):
        _fail("transition preimage bound formula is invalid")


def _validate_state(value: InMemoryFakeCasStateV10, /) -> None:
    _validate_frozen_constants()
    if type(value) is not InMemoryFakeCasStateV10:
        _fail("state is not the exact public state type")
    fixed_strings = (
        (value.state_schema_version, _STATE_SCHEMA, "state_schema_version"),
        (value.state_scope, _STATE_SCOPE, "state_scope"),
        (value.origin_status, _ORIGIN_STATUS, "origin_status"),
        (value.version_scope, _VERSION_SCOPE, "version_scope"),
        (value.raw_equality_scope, _RAW_EQUALITY_SCOPE, "raw_equality_scope"),
        (value.state_provenance, _STATE_PROVENANCE, "state_provenance"),
        (value.lineage_enforcement, _LINEAGE_ENFORCEMENT, "lineage_enforcement"),
        (value.fork_handling, _FORK_HANDLING, "fork_handling"),
        (value.deletion_support, _DELETION_SUPPORT, "deletion_support"),
        (value.persistence_scope, _PERSISTENCE_SCOPE, "persistence_scope"),
        (value.concurrency_scope, _CONCURRENCY_SCOPE, "concurrency_scope"),
        (
            value.remote_cas_authentication,
            _REMOTE_CAS_AUTHENTICATION,
            "remote_cas_authentication",
        ),
        (value.authority_scope, _AUTHORITY_SCOPE, "authority_scope"),
    )
    for actual, expected, name in fixed_strings:
        if _require_exact_str(actual, name) != expected:
            _fail(f"{name} is invalid")
    if _require_exact_int(value.payload_byte_limit, "payload_byte_limit") != _MAX_PAYLOAD_BYTES:
        _fail("payload_byte_limit is invalid")
    if _require_exact_int(value.generation_upper_bound, "generation_upper_bound") != _MAX_GENERATION:
        _fail("generation_upper_bound is invalid")
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        _require_false(getattr(value, name), name)
    generation = _require_exact_int(value.generation, "generation")
    if generation < 0 or generation > _MAX_GENERATION:
        _fail("generation is out of range")
    cell_state = _require_exact_str(value.cell_state, "cell_state")
    if cell_state == "absent":
        if generation != 0:
            _fail("absent state must have generation zero")
        _require_none(value.cell_payload, "absent cell_payload")
        _require_none(value.cell_payload_bytes, "absent cell_payload_bytes")
        _require_none(value.cell_payload_sha256, "absent cell_payload_sha256")
        payload = None
    elif cell_state == "present":
        if generation < 1:
            _fail("present state must have positive generation")
        payload = _require_exact_bytes(value.cell_payload, "cell_payload")
        if len(payload) > _MAX_PAYLOAD_BYTES:
            _fail("cell_payload exceeds the byte bound")
        if _require_exact_int(value.cell_payload_bytes, "cell_payload_bytes") != len(payload):
            _fail("cell_payload_bytes is invalid")
        supplied_payload_sha = _require_hash(
            value.cell_payload_sha256, "cell_payload_sha256"
        )
        computed_payload_sha = _require_hash(
            _raw_payload_sha256(payload), "computed cell payload hash"
        )
        if supplied_payload_sha != computed_payload_sha:
            _fail("cell_payload_sha256 is invalid")
    else:
        _fail("cell_state is invalid")
    supplied_version = _require_hash(value.state_version_sha256, "state_version_sha256")
    expected_version = _state_version_sha256(generation, payload)
    if supplied_version != expected_version:
        _fail("state_version_sha256 is invalid")


def _make_state(generation: int, payload: bytes | None, /) -> InMemoryFakeCasStateV10:
    _validate_frozen_constants()
    if payload is None:
        cell_state = "absent"
        payload_bytes = None
        payload_sha256 = None
    else:
        raw = _require_exact_bytes(payload, "cell payload")
        if len(raw) > _MAX_PAYLOAD_BYTES:
            _fail("cell payload exceeds the byte bound")
        cell_state = "present"
        payload_bytes = len(raw)
        payload_sha256 = _require_hash(
            _raw_payload_sha256(raw), "computed cell payload hash"
        )
    return InMemoryFakeCasStateV10(
        _STATE_SCHEMA,
        _STATE_SCOPE,
        _ORIGIN_STATUS,
        generation,
        cell_state,
        payload,
        payload_bytes,
        payload_sha256,
        _state_version_sha256(generation, payload),
        _MAX_PAYLOAD_BYTES,
        _MAX_GENERATION,
        _VERSION_SCOPE,
        _RAW_EQUALITY_SCOPE,
        _STATE_PROVENANCE,
        _LINEAGE_ENFORCEMENT,
        _FORK_HANDLING,
        _DELETION_SUPPORT,
        _PERSISTENCE_SCOPE,
        _CONCURRENCY_SCOPE,
        _REMOTE_CAS_AUTHENTICATION,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )


def _snapshot_state(value: object, /) -> InMemoryFakeCasStateV10:
    if type(value) is not InMemoryFakeCasStateV10:
        _fail("state is not the exact public state type")
    try:
        return InMemoryFakeCasStateV10(
            value.state_schema_version,
            value.state_scope,
            value.origin_status,
            value.generation,
            value.cell_state,
            value.cell_payload,
            value.cell_payload_bytes,
            value.cell_payload_sha256,
            value.state_version_sha256,
            value.payload_byte_limit,
            value.generation_upper_bound,
            value.version_scope,
            value.raw_equality_scope,
            value.state_provenance,
            value.lineage_enforcement,
            value.fork_handling,
            value.deletion_support,
            value.persistence_scope,
            value.concurrency_scope,
            value.remote_cas_authentication,
            value.authority_scope,
            value.canonical_remote_authority,
            value.licenses_execution,
            value.licenses_publication,
            value.licenses_recovery,
            value.licenses_later_stage,
        )
    except InMemoryFakeCasV10Error:
        raise
    except (AttributeError, TypeError):
        _fail("state fields are missing or unreadable")


def _derive_transition_values(
    snapshot: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    synthetic_directive: str,
    alternate_payload: bytes | None,
    /,
) -> tuple[object, ...]:
    _validate_frozen_constants()
    if type(snapshot) is not InMemoryFakeCasStateV10:
        _fail("snapshot is not the exact public state type")
    expected_version = _require_hash(
        expected_state_version_sha256, "expected_state_version_sha256"
    )
    proposal = _require_exact_bytes(proposed_payload, "proposed_payload")
    if len(proposal) > _MAX_PAYLOAD_BYTES:
        _fail("proposed_payload exceeds the byte bound")
    directive = _require_exact_str(synthetic_directive, "synthetic_directive")
    try:
        directive_index = _DIRECTIVES.index(directive)
    except ValueError:
        _fail("synthetic_directive is invalid")
    if directive_index < 3:
        if alternate_payload is not None:
            _fail("alternate_payload must be exact None for this directive")
        alternate = None
    else:
        alternate = _require_exact_bytes(alternate_payload, "alternate_payload")
        if len(alternate) > _MAX_PAYLOAD_BYTES:
            _fail("alternate_payload exceeds the byte bound")
    proposal_sha256 = _require_hash(
        _raw_payload_sha256(proposal), "computed proposed payload hash"
    )
    if alternate is None:
        alternate_bytes = None
        alternate_sha256 = None
    else:
        alternate_bytes = len(alternate)
        alternate_sha256 = _require_hash(
            _raw_payload_sha256(alternate), "computed alternate payload hash"
        )
    input_sha256 = _input_sha256(
        expected_version,
        proposal,
        directive_index,
        alternate,
    )

    if expected_version != snapshot.state_version_sha256:
        outcome_index = 0
        after_state = snapshot
        expected_version_match = False
        proposed_equal_before = None
        directive_reached = False
        alternate_semantics_checked = False
        state_changed = False
        mutation_count = 0
        intended_after_version = None
        intended_delta = None
        actual_delta = None
    elif (
        snapshot.cell_state == "present"
        and snapshot.cell_payload == proposed_payload
    ):
        outcome_index = 1
        after_state = snapshot
        expected_version_match = True
        proposed_equal_before = True
        directive_reached = False
        alternate_semantics_checked = False
        state_changed = False
        mutation_count = 0
        intended_after_version = None
        intended_delta = None
        actual_delta = None
    else:
        if directive_index == 3:
            if alternate_payload == proposed_payload:
                _fail("alternate_payload must differ from proposed_payload")
            if (
                snapshot.cell_state == "present"
                and alternate_payload == snapshot.cell_payload
            ):
                _fail("alternate_payload must differ from the current payload")
        if snapshot.generation == _MAX_GENERATION:
            _fail("a changed transition would exhaust generation")
        next_generation = snapshot.generation + 1
        intended_state = _make_state(next_generation, proposal)
        intended_after_version = intended_state.state_version_sha256
        intended_delta = _delta_sha256(
            snapshot.state_version_sha256,
            intended_after_version,
            proposal,
        )
        if directive_index == 3:
            outcome_index = 5
            after_state = _make_state(next_generation, alternate)
            actual_delta = _delta_sha256(
                snapshot.state_version_sha256,
                after_state.state_version_sha256,
                alternate,
            )
            alternate_semantics_checked = True
        else:
            outcome_index = directive_index + 2
            after_state = intended_state
            actual_delta = intended_delta
            alternate_semantics_checked = False
        expected_version_match = True
        proposed_equal_before = False
        directive_reached = True
        state_changed = True
        mutation_count = 1

    row = _OUTCOME_ROWS[outcome_index]
    transition_sha256 = _transition_sha256(
        input_sha256,
        outcome_index,
        snapshot.state_version_sha256,
        intended_after_version,
        intended_delta,
        actual_delta,
        after_state.state_version_sha256,
        mutation_count,
        row,
    )
    return (
        _TRANSITION_SCHEMA,
        _TRANSITION_SCOPE,
        _ORIGIN_STATUS,
        snapshot,
        after_state,
        expected_version,
        proposal,
        len(proposal),
        proposal_sha256,
        directive,
        alternate,
        alternate_bytes,
        alternate_sha256,
        input_sha256,
        _OUTCOMES[outcome_index],
        (row[0],),
        expected_version_match,
        proposed_equal_before,
        directive_reached,
        alternate_semantics_checked,
        state_changed,
        mutation_count,
        row[1],
        intended_after_version,
        intended_delta,
        actual_delta,
        transition_sha256,
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        _MAX_PAYLOAD_BYTES,
        _MAX_GENERATION,
        _MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES,
        _MAX_RETAINED_PAYLOAD_COPY_BYTES,
        _MAX_STATE_HASH_PREIMAGE_BYTES,
        _MAX_INPUT_HASH_PREIMAGE_BYTES,
        _MAX_DELTA_HASH_PREIMAGE_BYTES,
        _MAX_TRANSITION_HASH_PREIMAGE_BYTES,
        _HASH_PREIMAGE_CONSTRUCTION,
        _DIRECTIVE_ORIGIN,
        _OUTCOME_SELECTION,
        _CONFIRMATION_SCOPE,
        _CAUSE_SCOPE,
        _APPLICATION_ATTRIBUTION,
        _STATE_PROVENANCE,
        _LINEAGE_ENFORCEMENT,
        _FORK_HANDLING,
        _IDEMPOTENCE_SCOPE,
        _EXACTLY_ONCE_SCOPE,
        _PERSISTENCE_SCOPE,
        _CONCURRENCY_SCOPE,
        _FILESYSTEM_STAGING,
        _REMOTE_PUBLICATION,
        _DURABILITY_SCOPE,
        _MARKER_SCOPE,
        _RECOVERY_SCOPE,
        _WITNESS_SCOPE,
        _MANIFEST_SCOPE,
        _AUTHORITY_SCOPE,
        False,
        False,
        False,
        False,
        False,
    )


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


def _validate_transition_field_types(
    value: InMemoryFakeCasTransitionV10, /
) -> None:
    exact_strings = (
        (value.transition_schema_version, "transition_schema_version"),
        (value.transition_scope, "transition_scope"),
        (value.origin_status, "origin_status"),
        (value.synthetic_directive, "synthetic_directive"),
        (value.outcome, "outcome"),
        (value.intended_apply_status, "intended_apply_status"),
        (value.effect_scope, "effect_scope"),
        (
            value.synthetic_acknowledgement_label,
            "synthetic_acknowledgement_label",
        ),
        (
            value.same_kernel_confirmation_label,
            "same_kernel_confirmation_label",
        ),
        (value.synthetic_client_observation, "synthetic_client_observation"),
        (value.model_latent_effect, "model_latent_effect"),
        (value.hash_preimage_construction, "hash_preimage_construction"),
        (value.directive_origin, "directive_origin"),
        (value.outcome_selection, "outcome_selection"),
        (value.confirmation_scope, "confirmation_scope"),
        (value.cause_scope, "cause_scope"),
        (value.application_attribution, "application_attribution"),
        (value.state_provenance, "state_provenance"),
        (value.lineage_enforcement, "lineage_enforcement"),
        (value.fork_handling, "fork_handling"),
        (value.idempotence_scope, "idempotence_scope"),
        (value.exactly_once_scope, "exactly_once_scope"),
        (value.persistence_scope, "persistence_scope"),
        (value.concurrency_scope, "concurrency_scope"),
        (value.filesystem_staging, "filesystem_staging"),
        (value.remote_publication, "remote_publication"),
        (value.durability_scope, "durability_scope"),
        (value.marker_scope, "marker_scope"),
        (value.recovery_scope, "recovery_scope"),
        (value.witness_scope, "witness_scope"),
        (value.manifest_scope, "manifest_scope"),
        (value.authority_scope, "authority_scope"),
    )
    for field_value, name in exact_strings:
        _require_exact_str(field_value, name)
    exact_hashes = (
        (value.expected_state_version_sha256, "expected_state_version_sha256"),
        (value.proposed_payload_sha256, "proposed_payload_sha256"),
        (value.input_sha256, "input_sha256"),
        (value.transition_sha256, "transition_sha256"),
    )
    for field_value, name in exact_hashes:
        _require_hash(field_value, name)
    optional_hashes = (
        (value.alternate_payload_sha256, "alternate_payload_sha256"),
        (
            value.intended_after_state_version_sha256,
            "intended_after_state_version_sha256",
        ),
        (value.intended_delta_sha256, "intended_delta_sha256"),
        (value.actual_delta_sha256, "actual_delta_sha256"),
    )
    for field_value, name in optional_hashes:
        if field_value is not None:
            _require_hash(field_value, name)
    _require_exact_bytes(value.proposed_payload, "proposed_payload")
    if value.alternate_payload is not None:
        _require_exact_bytes(value.alternate_payload, "alternate_payload")
    exact_integers = (
        (value.proposed_payload_bytes, "proposed_payload_bytes"),
        (value.cell_mutation_count, "cell_mutation_count"),
        (value.payload_byte_limit, "payload_byte_limit"),
        (value.generation_upper_bound, "generation_upper_bound"),
        (
            value.unique_retained_payload_reference_upper_bound_bytes,
            "unique_retained_payload_reference_upper_bound_bytes",
        ),
        (
            value.retained_payload_copy_upper_bound_bytes,
            "retained_payload_copy_upper_bound_bytes",
        ),
        (
            value.state_hash_preimage_upper_bound_bytes,
            "state_hash_preimage_upper_bound_bytes",
        ),
        (
            value.input_hash_preimage_upper_bound_bytes,
            "input_hash_preimage_upper_bound_bytes",
        ),
        (
            value.delta_hash_preimage_upper_bound_bytes,
            "delta_hash_preimage_upper_bound_bytes",
        ),
        (
            value.transition_hash_preimage_upper_bound_bytes,
            "transition_hash_preimage_upper_bound_bytes",
        ),
    )
    for field_value, name in exact_integers:
        _require_exact_int(field_value, name)
    if value.alternate_payload_bytes is not None:
        _require_exact_int(value.alternate_payload_bytes, "alternate_payload_bytes")
    exact_booleans = (
        (value.expected_version_match, "expected_version_match"),
        (value.directive_reached, "directive_reached"),
        (value.alternate_semantics_checked, "alternate_semantics_checked"),
        (value.state_changed, "state_changed"),
        (value.canonical_remote_authority, "canonical_remote_authority"),
        (value.licenses_execution, "licenses_execution"),
        (value.licenses_publication, "licenses_publication"),
        (value.licenses_recovery, "licenses_recovery"),
        (value.licenses_later_stage, "licenses_later_stage"),
    )
    for field_value, name in exact_booleans:
        _require_exact_bool(field_value, name)
    if value.proposed_equal_before is not None:
        _require_exact_bool(value.proposed_equal_before, "proposed_equal_before")
    if type(value.reason_codes) is not tuple or len(value.reason_codes) != 1:
        _fail("reason_codes must be an exact one-element tuple")
    _require_exact_str(value.reason_codes[0], "reason code")


def _validate_transition(value: InMemoryFakeCasTransitionV10, /) -> None:
    _validate_frozen_constants()
    if type(value) is not InMemoryFakeCasTransitionV10:
        _fail("transition is not the exact public transition type")
    _validate_transition_field_types(value)
    before_snapshot = _snapshot_state(value.before_state)
    _snapshot_state(value.after_state)
    expected = _derive_transition_values(
        before_snapshot,
        value.expected_state_version_sha256,
        value.proposed_payload,
        value.synthetic_directive,
        value.alternate_payload,
    )
    if _transition_values(value) != expected:
        _fail("transition fields do not match their derivation")
    if value.outcome in _OUTCOMES[:2]:
        if value.after_state is not value.before_state:
            _fail("a no-change transition must retain the same State object")
    elif value.outcome == _OUTCOMES[5]:
        if value.after_state.cell_payload is not value.alternate_payload:
            _fail("wrong-delta after payload must retain the alternate object")
    elif value.after_state.cell_payload is not value.proposed_payload:
        _fail("intended after payload must retain the proposal object")


def initial_in_memory_fake_cas_state_v1_0() -> InMemoryFakeCasStateV10:
    return _make_state(0, None)


def step_in_memory_fake_cas_v1_0(
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    synthetic_directive: str,
    alternate_payload: bytes | None,
    /,
) -> InMemoryFakeCasTransitionV10:
    _validate_frozen_constants()
    snapshot = _snapshot_state(state)
    values = _derive_transition_values(
        snapshot,
        expected_state_version_sha256,
        proposed_payload,
        synthetic_directive,
        alternate_payload,
    )
    return InMemoryFakeCasTransitionV10(*values)
