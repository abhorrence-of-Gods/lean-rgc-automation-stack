"""Noncollectable Phase-2b2d local-staging fake-publisher acceptance cases.

Only the test functions named by ``__all__`` are imported by the frozen
collector.  Every real filesystem object used here is created below
``tmp_path``; all other filesystem behavior is supplied through the frozen
private native seams.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import os
from pathlib import Path
import stat
import types
from typing import Any, get_type_hints

import pytest

from lean_rgc.evals import uprime_rpc_fake_cas_kernel as cas
from lean_rgc.evals import uprime_rpc_local_staging_fake_publisher as publisher
from lean_rgc.evals import uprime_rpc_litmus as litmus


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "lean_rgc/evals/uprime_rpc_local_staging_fake_publisher.py"
SUPPORT_PATH = ROOT / "tests/uprime_rpc_local_staging_fake_publisher_cases.py"
COLLECTOR_PATH = ROOT / "tests/test_uprime_rpc_ledger.py"

A = bytes.fromhex("11" * 32)
B = bytes.fromhex("22" * 32)
MAX_PAYLOAD_BYTES = 1_048_576
MAX_GENERATION = 9_223_372_036_854_775_807
CHUNK_BYTES = 65_536
STAGE_PREFIX = "uprime-rpc-fake-cas-stage-v1-"
STAGE_SUFFIX = ".bin"
D_STATE = b"lean-rgc-uprime-u1-in-memory-fake-cas-state-v1\0"
D_OPERATION = b"lean-rgc-uprime-u1-local-staging-fake-publisher-operation-v1\0"

RESULT_FIELDS = (
    "result_schema_version",
    "result_scope",
    "origin_status",
    "staging_parent",
    "collision_nonce",
    "stage_basename",
    "stage_path",
    "cas_transition",
    "outcome",
    "reason_codes",
    "cas_gate_status",
    "parent_observation_status",
    "stage_status",
    "stage_payload_bytes",
    "stage_payload_sha256",
    "write_call_count",
    "read_call_count",
    "operation_sha256",
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
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

FIXED_FIELDS = {
    "result_schema_version": "lean-rgc-uprime-u1-local-staging-fake-publish-result-v1.0",
    "result_scope": "one_call_changed_branch_nonce_stage_before_pure_normal_fake_cas_return",
    "origin_status": "unknown_may_be_synthetic",
    "payload_byte_limit": MAX_PAYLOAD_BYTES,
    "staging_parent_utf8_byte_limit": 4096,
    "stage_path_utf8_byte_limit": 4162,
    "collision_nonce_chars": 32,
    "io_chunk_bytes": CHUNK_BYTES,
    "write_call_upper_bound": MAX_PAYLOAD_BYTES,
    "read_call_upper_bound": 17,
    "filesystem_payload_work_upper_bound_bytes": 2_097_152,
    "peak_transient_buffer_upper_bound_bytes": CHUNK_BYTES,
    "retained_payload_copy_upper_bound_bytes": 0,
    "stage_file_create_upper_bound": 1,
    "retained_stage_byte_upper_bound": MAX_PAYLOAD_BYTES,
    "operation_hash_preimage_upper_bound_bytes": 1_052_813,
    "hash_preimage_construction": "payload_streamed_no_full_preimage_materialization",
    "result_provenance": "unauthenticated_forgeable_value_object_not_io_attestation",
    "collision_nonce_scope": "caller_supplied_collision_separator_not_identity_or_entropy_evidence",
    "staging_parent_authority": "caller_supplied_write_location_not_authenticated_namespace",
    "path_derivation_scope": "lexical_native_join_no_resolution_or_canonical_binding",
    "ancestor_reparse_check_scope": "not_performed_only_final_parent_entry_observed",
    "backing_store_scope": "unauthenticated_may_be_remote_virtual_or_overlay",
    "hostile_concurrent_reparse_prevention": "not_provided",
    "stage_exclusivity_scope": "changed_branch_one_native_path_exclusive_create_only",
    "stage_readback_scope": "changed_branch_same_descriptor_exact_bytes_at_one_observation_interval",
    "stage_retention_scope": "any_created_stage_retained_no_post_return_lifetime_claim",
    "durability_scope": "fsync_not_called_crash_and_power_loss_not_observed",
    "cleanup_scope": "not_performed_any_created_stage_may_remain_after_success_or_error",
    "publisher_scope": "pure_fake_cas_value_return_changed_branch_stage_gated_not_real_publication",
    "state_linearity": "caller_threaded_not_enforced",
    "concurrency_scope": "no_exclusion_or_cross_process_atomicity",
    "idempotence_scope": "not_provided_distinct_nonce_is_explicit_new_attempt",
    "exactly_once_scope": "not_provided",
    "payload_confidentiality": "not_provided_any_staged_bytes_written_to_caller_location",
    "attempt_completeness": "successful_returns_only_errors_unjournaled",
    "marker_scope": "not_created_or_observed",
    "recovery_scope": "not_performed",
    "epoch_scope": "none",
    "witness_scope": "none",
    "manifest_scope": "not_read_or_written",
    "remote_publication": "not_performed",
    "authority_scope": "none",
    "canonical_remote_authority": False,
    "licenses_execution": False,
    "licenses_publication": False,
    "licenses_recovery": False,
    "licenses_later_stage": False,
}

OUTCOME_ROWS = {
    "cas_conflict_no_stage": (
        "expected_state_version_mismatch",
        "conflict_no_change",
        "conflict",
        "not_attempted",
        "not_attempted",
        None,
        None,
        0,
        0,
    ),
    "cas_existing_identical_no_stage": (
        "exact_payload_already_current",
        "existing_identical_no_change",
        "existing_identical",
        "not_attempted",
        "not_attempted",
        None,
        None,
        0,
        0,
    ),
    "staged_intended_fake_publish_acknowledged": (
        "exact_stage_retained_before_exposing_synthetic_acknowledged_transition",
        "intended_applied_acknowledged",
        "intended_acknowledged",
        "stable_at_endpoint",
        "retained_stable_at_endpoint",
        "payload",
        "digest",
        "writes",
        "reads",
    ),
}
OUTCOME_TAGS = {
    "cas_conflict_no_stage": b"\x01",
    "cas_existing_identical_no_stage": b"\x02",
    "staged_intended_fake_publish_acknowledged": b"\x03",
}
PARENT_TAGS = {"not_attempted": b"\x01", "stable_at_endpoint": b"\x02"}
STAGE_TAGS = {
    "not_attempted": b"\x01",
    "retained_stable_at_endpoint": b"\x02",
}

GOLDENS = (
    (
        r"C:\uprime-stage",
        "00" * 16,
        "60D25236487695725CF5C6AAE03B8BD5426085D3B6A89DB8527843E79E3C4F3F",
        "cas_conflict_no_stage",
        "not_attempted",
        "not_attempted",
        None,
        0,
        0,
        148,
        "94AEB8A5436ECFB6F92636FF5F1F3FE54F017B97DBC2BFEA2D4B8CAFFEDAD29B",
    ),
    (
        "/tmp/uprime-stage",
        "11" * 16,
        "E3293691B197ED371747C098EF462850846705282FBD449BAD8D321FD6E742BC",
        "cas_existing_identical_no_stage",
        "not_attempted",
        "not_attempted",
        None,
        0,
        0,
        150,
        "4034FA2EB322E027EBAD97F1403E2FA834FFAF1A1AB2A67190FA52BFCCCF71A1",
    ),
    (
        r"C:\uprime-stage",
        "22" * 16,
        "029C6ECD6148EDC6736727E780DE474C7D760B63E650EA22744800547208C44C",
        "staged_intended_fake_publish_acknowledged",
        "stable_at_endpoint",
        "retained_stable_at_endpoint",
        B,
        1,
        2,
        188,
        "1977C339326297C3FA8A13F85236DF22643DA662D5CDF9619513A05B40AF49D1",
    ),
    (
        "/tmp/uprime-stage",
        "33" * 16,
        "194FC9297D81669BDE36952C414D47F013FD0DBF4A51DA175B2649447DEE1AAF",
        "staged_intended_fake_publish_acknowledged",
        "stable_at_endpoint",
        "retained_stable_at_endpoint",
        b"",
        0,
        1,
        158,
        "29BA2F61DB81D4030988BEAEBF123B1031C5C06B60E2C3EC92ECBCDB311E366F",
    ),
)

PHYSICAL_SEAMS = (
    "_os_stat",
    "_os_open",
    "_os_fstat",
    "_os_write",
    "_os_lseek",
    "_os_read",
    "_os_close",
)

FROZEN_CONSTANT_NAMES = (
    "_RESULT_SCHEMA",
    "_RESULT_SCOPE",
    "_ORIGIN_STATUS",
    "_MAX_PAYLOAD_BYTES",
    "_MAX_STAGING_PARENT_UTF8_BYTES",
    "_MAX_STAGE_PATH_UTF8_BYTES",
    "_COLLISION_NONCE_CHARS",
    "_COLLISION_NONCE_BYTES",
    "_IO_CHUNK_BYTES",
    "_MAX_WRITE_CALLS",
    "_MAX_READ_CALLS",
    "_MAX_FILESYSTEM_PAYLOAD_WORK_BYTES",
    "_MAX_PEAK_TRANSIENT_BUFFER_BYTES",
    "_MAX_RETAINED_PAYLOAD_COPY_BYTES",
    "_MAX_STAGE_FILE_CREATES",
    "_MAX_RETAINED_STAGE_BYTES",
    "_MAX_OPERATION_HASH_PREIMAGE_BYTES",
    "_D_OPERATION",
    "_HASH_PREIMAGE_CONSTRUCTION",
    "_STAGE_BASENAME_PREFIX",
    "_STAGE_BASENAME_SUFFIX",
    "_STAGE_BASENAME_BYTES",
    "_FIXED_DIRECTIVE",
    "_OPEN_MODE",
    "_FILE_ATTRIBUTE_REPARSE_POINT",
    "_OPEN_FLAGS",
    "_LOWER_HEX32_PATTERN",
    "_UPPER_HEX64_PATTERN",
    "_WINDOWS_DRIVE_ROOT_PATTERN",
    "_OUTCOME_ROWS",
    "_RESULT_PROVENANCE",
    "_COLLISION_NONCE_SCOPE",
    "_STAGING_PARENT_AUTHORITY",
    "_PATH_DERIVATION_SCOPE",
    "_ANCESTOR_REPARSE_CHECK_SCOPE",
    "_BACKING_STORE_SCOPE",
    "_HOSTILE_CONCURRENT_REPARSE_PREVENTION",
    "_STAGE_EXCLUSIVITY_SCOPE",
    "_STAGE_READBACK_SCOPE",
    "_STAGE_RETENTION_SCOPE",
    "_DURABILITY_SCOPE",
    "_CLEANUP_SCOPE",
    "_PUBLISHER_SCOPE",
    "_STATE_LINEARITY",
    "_CONCURRENCY_SCOPE",
    "_IDEMPOTENCE_SCOPE",
    "_EXACTLY_ONCE_SCOPE",
    "_PAYLOAD_CONFIDENTIALITY",
    "_ATTEMPT_COMPLETENESS",
    "_MARKER_SCOPE",
    "_RECOVERY_SCOPE",
    "_EPOCH_SCOPE",
    "_WITNESS_SCOPE",
    "_MANIFEST_SCOPE",
    "_REMOTE_PUBLICATION",
    "_AUTHORITY_SCOPE",
)


def _h(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _operation_preimage(
    parent: str,
    nonce: str,
    transition_sha256: str,
    outcome: str,
    parent_status: str,
    stage_status: str,
    payload: bytes | None,
    writes: int,
    reads: int,
) -> bytes:
    parent_raw = parent.encode("utf-8")
    result = (
        D_OPERATION
        + _u32(len(parent_raw))
        + parent_raw
        + bytes.fromhex(nonce)
        + bytes.fromhex(transition_sha256)
        + OUTCOME_TAGS[outcome]
        + PARENT_TAGS[parent_status]
        + STAGE_TAGS[stage_status]
        + (b"\x00" if payload is None else b"\x01" + _u64(len(payload)) + payload)
        + _u64(writes)
        + _u64(reads)
    )
    return result


def _mapping(record: Any) -> dict[str, Any]:
    return {field.name: getattr(record, field.name) for field in fields(record)}


def _absent_state() -> cas.InMemoryFakeCasStateV10:
    return cas.initial_in_memory_fake_cas_state_v1_0()


def _state_with(payload: bytes) -> cas.InMemoryFakeCasStateV10:
    before = _absent_state()
    return cas.step_in_memory_fake_cas_v1_0(
        before,
        before.state_version_sha256,
        payload,
        "apply_intended_acknowledge",
        None,
    ).after_state


def _max_state(payload: bytes) -> cas.InMemoryFakeCasStateV10:
    mapping = _mapping(_state_with(payload))
    mapping["generation"] = MAX_GENERATION
    mapping["state_version_sha256"] = _h(
        D_STATE + _u64(MAX_GENERATION) + b"\x01" + _u64(len(payload)) + payload
    )
    return cas.InMemoryFakeCasStateV10(**mapping)


def _normal_transition(
    state: cas.InMemoryFakeCasStateV10,
    expected: str,
    payload: bytes,
) -> cas.InMemoryFakeCasTransitionV10:
    return cas.step_in_memory_fake_cas_v1_0(
        state,
        expected,
        payload,
        "apply_intended_acknowledge",
        None,
    )


def _stage_basename(nonce: str) -> str:
    return STAGE_PREFIX + nonce + STAGE_SUFFIX


def _call(
    parent: str,
    nonce: str,
    state: cas.InMemoryFakeCasStateV10,
    expected: str,
    payload: bytes,
) -> publisher.LocalStagingFakePublishResultV10:
    return publisher.stage_and_fake_publish_normal_v1_0(
        parent, nonce, state, expected, payload
    )


def _changed(
    parent: Path,
    nonce: str = "22" * 16,
    payload: bytes = B,
) -> publisher.LocalStagingFakePublishResultV10:
    state = _state_with(A)
    return _call(str(parent.absolute()), nonce, state, state.state_version_sha256, payload)


def _forbid_physical(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        calls.append("physical")
        raise AssertionError("physical filesystem seam reached")

    for name in PHYSICAL_SEAMS:
        monkeypatch.setattr(publisher, name, forbidden)
    return calls


def _fake_stat(value: Any | None = None, *, include_attributes: bool = True, **changes: Any) -> types.SimpleNamespace:
    names = ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_size", "st_mtime_ns")
    data = {
        name: getattr(value, name)
        for name in names
        if value is not None and hasattr(value, name)
    }
    if include_attributes:
        data["st_file_attributes"] = (
            getattr(value, "st_file_attributes", 0) if value is not None else 0
        )
    data.update(changes)
    return types.SimpleNamespace(**data)


def _assert_result(result: publisher.LocalStagingFakePublishResultV10, payload: bytes | None) -> None:
    for name, value in FIXED_FIELDS.items():
        assert getattr(result, name) == value, name
    row = OUTCOME_ROWS[result.outcome]
    assert result.reason_codes == (row[0],)
    assert result.cas_transition.outcome == row[1]
    assert result.cas_gate_status == row[2]
    assert result.parent_observation_status == row[3]
    assert result.stage_status == row[4]
    if payload is None:
        assert result.stage_payload_bytes is None
        assert result.stage_payload_sha256 is None
    else:
        assert result.stage_payload_bytes == len(payload)
        assert result.stage_payload_sha256 == _h(payload)
    assert result.stage_basename == _stage_basename(result.collision_nonce)
    assert result.stage_path == os.path.join(result.staging_parent, result.stage_basename)
    preimage = _operation_preimage(
        result.staging_parent,
        result.collision_nonce,
        result.cas_transition.transition_sha256,
        result.outcome,
        result.parent_observation_status,
        result.stage_status,
        payload,
        result.write_call_count,
        result.read_call_count,
    )
    assert result.operation_sha256 == _h(preimage)


def _source_tree() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))


def _same_type_forgery(value: Any) -> Any:
    if type(value) is str:
        return value + "_forged"
    if type(value) is int:
        return value + 1
    if type(value) is bool:
        return not value
    if type(value) is tuple:
        return value + ("forged",)
    if value is None:
        return 0
    if type(value) is cas.InMemoryFakeCasTransitionV10:
        state = _state_with(A)
        return _normal_transition(state, state.state_version_sha256, B)
    return object()


def _wrong_type_forgery(value: Any) -> Any:
    if type(value) is str:
        return None
    if type(value) is int:
        return True
    if type(value) is bool:
        return 1
    if type(value) is tuple:
        return list(value)
    if value is None:
        return object()
    return object()


def _mutated_constant(value: Any) -> Any:
    if type(value) is str:
        return value + "_mutant"
    if type(value) is int:
        return value + 1
    if type(value) is bytes:
        return value + b"x"
    if type(value) is tuple:
        rows = list(value)
        first = list(rows[0])
        first[0] = first[0] + "_mutant"
        rows[0] = tuple(first)
        return tuple(rows)
    raise AssertionError(f"unsupported frozen constant type {type(value)!r}")


def test_uprime_local_staging_fake_publisher_exact_surface_imports_fields_and_signatures() -> None:
    assert publisher.__all__ == [
        "LocalStagingFakePublisherV10Error",
        "LocalStagingFakePublishResultV10",
        "stage_and_fake_publish_normal_v1_0",
    ]
    assert publisher.LocalStagingFakePublisherV10Error.__bases__ == (ValueError,)
    record = publisher.LocalStagingFakePublishResultV10
    assert tuple(field.name for field in fields(record)) == RESULT_FIELDS
    assert tuple(record.__slots__) == RESULT_FIELDS
    assert len(record.__annotations__) == 63
    expected_annotations = {name: "str" for name in RESULT_FIELDS}
    expected_annotations["cas_transition"] = "InMemoryFakeCasTransitionV10"
    expected_annotations["reason_codes"] = "tuple[str, ...]"
    for name in ("stage_payload_bytes",):
        expected_annotations[name] = "int | None"
    expected_annotations["stage_payload_sha256"] = "str | None"
    for name in (
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
    ):
        expected_annotations[name] = "int"
    for name in (
        "canonical_remote_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        expected_annotations[name] = "bool"
    assert record.__annotations__ == expected_annotations
    resolved = get_type_hints(record)
    assert resolved["cas_transition"] is cas.InMemoryFakeCasTransitionV10
    assert resolved["reason_codes"] == tuple[str, ...]

    signature = inspect.signature(publisher.stage_and_fake_publish_normal_v1_0)
    assert tuple(signature.parameters) == (
        "staging_parent",
        "collision_nonce",
        "state",
        "expected_state_version_sha256",
        "proposed_payload",
    )
    assert all(
        value.kind is inspect.Parameter.POSITIONAL_ONLY
        and value.default is inspect.Parameter.empty
        for value in signature.parameters.values()
    )
    assert tuple(value.annotation for value in signature.parameters.values()) == (
        "str",
        "str",
        "InMemoryFakeCasStateV10",
        "str",
        "bytes",
    )
    assert signature.return_annotation == "LocalStagingFakePublishResultV10"
    with pytest.raises(TypeError):
        publisher.stage_and_fake_publish_normal_v1_0()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        publisher.stage_and_fake_publish_normal_v1_0(  # type: ignore[call-arg]
            staging_parent="/tmp",
            collision_nonce="00" * 16,
            state=_absent_state(),
            expected_state_version_sha256="0" * 64,
            proposed_payload=b"",
        )

    tree = _source_tree()
    imports = [
        ast.unparse(node)
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert imports == [
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "import hashlib",
        "import os",
        "import re",
        "import stat",
        "from lean_rgc.evals.uprime_rpc_fake_cas_kernel import InMemoryFakeCasStateV10, InMemoryFakeCasTransitionV10, InMemoryFakeCasV10Error, step_in_memory_fake_cas_v1_0",
    ]


def test_uprime_local_staging_fake_publisher_record_is_frozen_slotted() -> None:
    state = _state_with(A)
    result = _call(
        str((ROOT / "nonexistent-phase2b2d-parent").absolute()),
        "01" * 16,
        state,
        _absent_state().state_version_sha256,
        B,
    )
    assert not hasattr(result, "__dict__")
    assert result.__class__.__dataclass_params__.frozen is True
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.outcome = "forged"  # type: ignore[misc]
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        replace(result, licenses_execution=True)

    class ResultSubclass(publisher.LocalStagingFakePublishResultV10):
        __slots__ = ()

    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        ResultSubclass(**_mapping(result))


@pytest.mark.parametrize(
    "bad_parent",
    (
        "",
        "relative",
        ".",
        "..",
        "relative/../path",
        "relative/./path",
        "bad\x00path",
        "bad\x01path",
        "bad\x1fpath",
        "bad\x7fpath",
        "bad\ud800path",
    ),
)
def test_uprime_local_staging_fake_publisher_parent_grammar_rejects_without_io(
    bad_parent: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _forbid_physical(monkeypatch)
    state = _state_with(A)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(bad_parent, "00" * 16, state, _absent_state().state_version_sha256, B)
    assert calls == []


def test_uprime_local_staging_fake_publisher_native_absolute_normalization_spellings_reject_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = str(tmp_path.absolute())
    spellings = (
        parent + os.sep + ".",
        parent + os.sep + "child" + os.sep + "..",
        parent + os.sep,
    )
    assert all(os.path.isabs(value) is True for value in spellings)
    assert all(os.path.normpath(value) != value for value in spellings)
    physical = _forbid_physical(monkeypatch)
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    for value in spellings:
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            _call(value, "0f" * 16, state, stale, B)
    assert physical == []


@pytest.mark.parametrize(
    "bad_nonce",
    (
        "",
        "0" * 31,
        "0" * 33,
        "A" * 32,
        "g" * 32,
        "-" * 32,
        "00" * 16 + "00",
    ),
)
def test_uprime_local_staging_fake_publisher_nonce_grammar_rejects_without_io(
    tmp_path: Path,
    bad_nonce: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _forbid_physical(monkeypatch)
    state = _state_with(A)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(str(tmp_path.absolute()), bad_nonce, state, state.state_version_sha256, B)
    assert calls == []


def test_uprime_local_staging_fake_publisher_exact_types_and_hostile_coercions_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched: list[str] = []

    class HostilePath:
        def __fspath__(self) -> str:
            touched.append("fspath")
            raise AssertionError

        def __str__(self) -> str:
            touched.append("str")
            raise AssertionError

    class StrSubclass(str):
        pass

    class BytesSubclass(bytes):
        pass

    class StateSubclass(cas.InMemoryFakeCasStateV10):
        __slots__ = ()

    state = _state_with(A)
    state_subclass = object.__new__(StateSubclass)
    for name, value in _mapping(state).items():
        object.__setattr__(state_subclass, name, value)

    parent = str(tmp_path.absolute())
    invalid_calls = (
        (Path(parent), "00" * 16, state, state.state_version_sha256, B),
        (os.fsencode(parent), "00" * 16, state, state.state_version_sha256, B),
        (HostilePath(), "00" * 16, state, state.state_version_sha256, B),
        (StrSubclass(parent), "00" * 16, state, state.state_version_sha256, B),
        (parent, StrSubclass("00" * 16), state, state.state_version_sha256, B),
        (parent, "00" * 16, state, StrSubclass(state.state_version_sha256), B),
        (parent, "00" * 16, state, state.state_version_sha256, bytearray(B)),
        (parent, "00" * 16, state, state.state_version_sha256, memoryview(B)),
        (parent, "00" * 16, state, state.state_version_sha256, BytesSubclass(B)),
        (parent, "00" * 16, object(), state.state_version_sha256, B),
        (
            parent,
            "00" * 16,
            state_subclass,
            state.state_version_sha256,
            B,
        ),
    )
    calls = _forbid_physical(monkeypatch)
    for args in invalid_calls:
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            publisher.stage_and_fake_publish_normal_v1_0(*args)
    assert touched == []
    assert calls == []


def test_uprime_local_staging_fake_publisher_utf8_parent_bounds_and_exact_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    nonce = "ab" * 16
    calls = _forbid_physical(monkeypatch)
    if os.name == "nt":
        prefix = "C:\\"
    else:
        prefix = "/"
    for bound in (4095, 4096):
        parent = prefix + "a" * (bound - len(prefix.encode("utf-8")))
        result = _call(parent, nonce, state, stale, B)
        assert result.staging_parent == parent
        assert result.stage_basename == _stage_basename(nonce)
        assert len(result.stage_basename.encode("ascii")) == 65
        assert result.stage_path == os.path.join(parent, result.stage_basename)
        assert len(result.stage_path.encode("utf-8")) == bound + 66
    over = prefix + "a" * (4097 - len(prefix.encode("utf-8")))
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(over, nonce, state, stale, B)
    multi_prefix = prefix + "e"
    remaining = 4096 - len(multi_prefix.encode("utf-8"))
    multi = multi_prefix + "é" * (remaining // 2) + ("a" if remaining % 2 else "")
    assert len(multi.encode("utf-8")) == 4096
    assert _call(multi, nonce, state, stale, B).staging_parent == multi
    assert calls == []


def test_uprime_local_staging_fake_publisher_lexical_seam_returns_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = str(tmp_path.absolute())
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    physical = _forbid_physical(monkeypatch)
    originals = {
        "_os_path_isabs": publisher._os_path_isabs,
        "_os_path_normpath": publisher._os_path_normpath,
        "_os_path_join": publisher._os_path_join,
    }
    cases = (
        ("_os_path_isabs", lambda value: 1),
        ("_os_path_isabs", lambda value: False),
        ("_os_path_normpath", lambda value: value + os.sep + "."),
        ("_os_path_normpath", lambda value: 1),
        ("_os_path_join", lambda *values: values[0]),
        ("_os_path_join", lambda *values: 1),
        ("_os_path_join", lambda *values: values[0] + "x" * 5000),
    )
    for name, replacement in cases:
        monkeypatch.setattr(publisher, name, replacement)
        try:
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(parent, "00" * 16, state, stale, B)
        finally:
            monkeypatch.setattr(publisher, name, originals[name])
    for name in originals:
        def failed(*args: Any, **kwargs: Any) -> Any:
            del args, kwargs
            raise OSError("injected lexical failure")

        monkeypatch.setattr(publisher, name, failed)
        try:
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(parent, "00" * 16, state, stale, B)
        finally:
            monkeypatch.setattr(publisher, name, originals[name])
    assert physical == []


def test_uprime_local_staging_fake_publisher_windows_path_spellings_are_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert publisher._WINDOWS_DRIVE_ROOT_PATTERN == r"[A-Za-z]:\\"
    assert "re.match(_WINDOWS_DRIVE_ROOT_PATTERN" in source
    assert "startswith" in source
    if os.name == "nt":
        state = _state_with(A)
        stale = _absent_state().state_version_sha256
        _forbid_physical(monkeypatch)
        for value in (
            r"\\server\share",
            r"\\?\C:\stage",
            r"\\.\C:\stage",
            r"\current-drive-rooted",
            r"C:drive-relative",
            "//server/share",
        ):
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(value, "00" * 16, state, stale, B)
    else:
        # Ubuntu executes the same assertion family without a platform skip;
        # native POSIX lexical acceptance remains separately covered above.
        assert _call(
            str((tmp_path / "missing").absolute()),
            "00" * 16,
            _state_with(A),
            _absent_state().state_version_sha256,
            B,
        ).outcome == "cas_conflict_no_stage"


def test_uprime_local_staging_fake_publisher_fake_cas_precedence_and_no_stage_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    physical = _forbid_physical(monkeypatch)
    parent = str((tmp_path / "physically-absent").absolute())

    conflict = _call(parent, "10" * 16, state, stale, B)
    identical = _call(parent, "11" * 16, state, state.state_version_sha256, A)
    assert conflict.outcome == "cas_conflict_no_stage"
    assert identical.outcome == "cas_existing_identical_no_stage"
    _assert_result(conflict, None)
    _assert_result(identical, None)
    assert physical == []
    assert not Path(parent).exists()

    malformed_state = copy.copy(state)
    object.__setattr__(malformed_state, "state_version_sha256", "0" * 64)
    invalids = (
        (state, "not-a-hash", B),
        (state, stale.lower(), B),
        (state, stale, bytearray(B)),
        (state, stale, memoryview(B)),
        (malformed_state, stale, B),
    )
    for candidate_state, expected, payload in invalids:
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            _call(parent, "12" * 16, candidate_state, expected, payload)  # type: ignore[arg-type]
    assert physical == []

    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call("relative", "12" * 16, state, stale, B)
    assert physical == []


def test_uprime_local_staging_fake_publisher_fake_cas_errors_types_and_baseexception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = str((tmp_path / "fake-cas-seam").absolute())
    state = _state_with(A)
    physical = _forbid_physical(monkeypatch)

    for failure in (
        cas.InMemoryFakeCasV10Error("injected kernel error"),
        RuntimeError("injected ordinary error"),
    ):
        with monkeypatch.context() as scoped:
            def failed(*args: Any, _failure: Exception = failure) -> Any:
                del args
                raise _failure

            scoped.setattr(publisher, "step_in_memory_fake_cas_v1_0", failed)
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(parent, "17" * 16, state, state.state_version_sha256, B)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            publisher,
            "step_in_memory_fake_cas_v1_0",
            lambda *args: object(),
        )
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            _call(parent, "18" * 16, state, state.state_version_sha256, B)

    class KernelBaseException(BaseException):
        pass

    with monkeypatch.context() as scoped:
        def catastrophic(*args: Any) -> Any:
            del args
            raise KernelBaseException("must propagate")

        scoped.setattr(publisher, "step_in_memory_fake_cas_v1_0", catastrophic)
        with pytest.raises(KernelBaseException):
            _call(parent, "19" * 16, state, state.state_version_sha256, B)
    assert physical == []


def test_uprime_local_staging_fake_publisher_payload_bounds_and_max_generation_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = str((tmp_path / "absent").absolute())
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    physical = _forbid_physical(monkeypatch)
    for payload in (b"x" * (MAX_PAYLOAD_BYTES - 1), b"x" * MAX_PAYLOAD_BYTES):
        result = _call(parent, "13" * 16, state, stale, payload)
        assert result.outcome == "cas_conflict_no_stage"
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(parent, "13" * 16, state, stale, b"x" * (MAX_PAYLOAD_BYTES + 1))

    maximum = _max_state(A)
    max_stale = _call(parent, "14" * 16, maximum, stale, B)
    max_identical = _call(
        parent, "15" * 16, maximum, maximum.state_version_sha256, A
    )
    assert max_stale.outcome == "cas_conflict_no_stage"
    assert max_identical.outcome == "cas_existing_identical_no_stage"
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(parent, "16" * 16, maximum, maximum.state_version_sha256, B)
    assert physical == []


def test_uprime_local_staging_fake_publisher_three_rows_every_dynamic_cell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    absent = _absent_state()
    missing = str((tmp_path / "missing-parent").absolute())
    original_physical = {name: getattr(publisher, name) for name in PHYSICAL_SEAMS}
    physical = _forbid_physical(monkeypatch)
    conflict = _call(missing, "20" * 16, state, absent.state_version_sha256, B)
    identical = _call(missing, "21" * 16, state, state.state_version_sha256, A)
    assert physical == []
    for name, value in original_physical.items():
        monkeypatch.setattr(publisher, name, value)

    parent = tmp_path / "changed"
    parent.mkdir()
    changed = _changed(parent, "22" * 16, B)
    rows = ((conflict, None), (identical, None), (changed, B))
    assert tuple(result.outcome for result, _ in rows) == tuple(OUTCOME_ROWS)
    for result, payload in rows:
        _assert_result(result, payload)
        assert result.cas_transition.synthetic_directive == "apply_intended_acknowledge"
        assert result.cas_transition.alternate_payload is None
    assert changed.write_call_count == 1
    assert changed.read_call_count == 2
    assert Path(changed.stage_path).read_bytes() == B


@pytest.mark.parametrize(
    ("size", "expected_writes", "expected_reads"),
    (
        (0, 0, 1),
        (1, 1, 2),
        (CHUNK_BYTES - 1, 1, 2),
        (CHUNK_BYTES, 1, 2),
        (CHUNK_BYTES + 1, 2, 3),
        (MAX_PAYLOAD_BYTES, 16, 17),
    ),
)
def test_uprime_local_staging_fake_publisher_real_payload_boundaries(
    tmp_path: Path,
    size: int,
    expected_writes: int,
    expected_reads: int,
) -> None:
    parent = tmp_path / f"payload-{size}"
    parent.mkdir()
    payload = bytes((index % 251 for index in range(size)))
    nonce = f"{size:032x}"
    result = _changed(parent, nonce, payload)
    _assert_result(result, payload)
    assert result.write_call_count == expected_writes
    assert result.read_call_count == expected_reads
    stage = Path(result.stage_path)
    assert stage.parent == parent.absolute()
    assert stage.read_bytes() == payload
    assert tuple(parent.iterdir()) == (stage,)


def test_uprime_local_staging_fake_publisher_partial_writes_memoryviews_and_io_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "partial-write"
    parent.mkdir()
    payload = bytes((index % 239 for index in range(CHUNK_BYTES + 17)))
    events: list[tuple[str, Any]] = []
    originals = {name: getattr(publisher, name) for name in PHYSICAL_SEAMS}

    def tracked_stat(path: str, **kwargs: Any) -> Any:
        events.append(("stat", (path, kwargs)))
        return originals["_os_stat"](path, **kwargs)

    def tracked_open(path: str, flags: int, mode: int) -> int:
        events.append(("open", (path, flags, mode)))
        return originals["_os_open"](path, flags, mode)

    def partial_write(fd: int, data: Any) -> int:
        events.append(("write", (type(data), len(data))))
        assert type(data) is memoryview
        assert 1 <= len(data) <= CHUNK_BYTES
        count = max(1, len(data) // 2)
        return originals["_os_write"](fd, data[:count])

    def tracked_fstat(fd: int) -> Any:
        events.append(("fstat", fd))
        return originals["_os_fstat"](fd)

    def tracked_lseek(fd: int, offset: int, whence: int) -> int:
        events.append(("lseek", (offset, whence)))
        return originals["_os_lseek"](fd, offset, whence)

    def tracked_read(fd: int, count: int) -> bytes:
        events.append(("read", count))
        return originals["_os_read"](fd, count)

    def tracked_close(fd: int) -> None:
        events.append(("close", fd))
        return originals["_os_close"](fd)

    for name, replacement in (
        ("_os_stat", tracked_stat),
        ("_os_open", tracked_open),
        ("_os_write", partial_write),
        ("_os_fstat", tracked_fstat),
        ("_os_lseek", tracked_lseek),
        ("_os_read", tracked_read),
        ("_os_close", tracked_close),
    ):
        monkeypatch.setattr(publisher, name, replacement)

    result = _changed(parent, "23" * 16, payload)
    assert Path(result.stage_path).read_bytes() == payload
    write_events = [value for name, value in events if name == "write"]
    read_events = [value for name, value in events if name == "read"]
    assert len(write_events) > 2
    assert read_events == [CHUNK_BYTES, 17, 1]
    names = [name for name, _value in events]
    assert names[0] == "stat"
    assert names[1] == "open"
    assert names[2] == "fstat"
    assert names.count("fstat") == 3
    assert names.count("close") == 1
    close_index = names.index("close")
    assert names[close_index + 1 :] == ["stat", "stat"]
    stat_events = [value for name, value in events if name == "stat"]
    assert len(stat_events) == 3
    assert stat_events[0][0] == str(parent.absolute())
    assert stat_events[2][0] == str(parent.absolute())
    assert all(value[1] == {"follow_symlinks": False} for value in stat_events)


def test_uprime_local_staging_fake_publisher_prior_full_read_chunk_is_released_before_next_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "read-frame-lifetime"
    parent.mkdir()
    payload = bytes((index % 241 for index in range(2 * CHUNK_BYTES + 1)))
    original_read = publisher._os_read
    probes: list[tuple[int, dict[str, int]]] = []
    calls = 0

    def probing_read(fd: int, count: int) -> bytes:
        nonlocal calls
        calls += 1
        frame = inspect.currentframe()
        assert frame is not None
        caller = frame.f_back
        assert caller is not None
        assert caller.f_code.co_name == "_readback_payload"
        survivors = {
            name: len(value)
            for name, value in caller.f_locals.items()
            if name in {"raw", "chunk"}
            and type(value) is bytes
            and len(value) == CHUNK_BYTES
        }
        probes.append((count, survivors))
        del caller, frame
        return original_read(fd, count)

    monkeypatch.setattr(publisher, "_os_read", probing_read)
    result = _changed(parent, "24" * 16, payload)
    assert Path(result.stage_path).read_bytes() == payload
    assert [count for count, _ in probes] == [CHUNK_BYTES, CHUNK_BYTES, 1, 1]
    assert probes[0][1] == {}
    assert all(survivors == {} for _count, survivors in probes[1:])


def test_uprime_local_staging_fake_publisher_operation_framing_goldens_and_mutations() -> None:
    assert len(D_OPERATION) == 61
    for case in GOLDENS:
        (
            parent,
            nonce,
            transition,
            outcome,
            parent_status,
            stage_status,
            payload,
            writes,
            reads,
            expected_length,
            expected_hash,
        ) = case
        preimage = _operation_preimage(
            parent,
            nonce,
            transition,
            outcome,
            parent_status,
            stage_status,
            payload,
            writes,
            reads,
        )
        assert len(preimage) == expected_length
        assert _h(preimage) == expected_hash
    assert GOLDENS[0][0].encode("utf-8").hex().upper() == (
        "433A5C757072696D652D7374616765"
    )
    maximum = _operation_preimage(
        "/" + "x" * 4095,
        "ff" * 16,
        "F" * 64,
        "staged_intended_fake_publish_acknowledged",
        "stable_at_endpoint",
        "retained_stable_at_endpoint",
        b"z" * MAX_PAYLOAD_BYTES,
        MAX_PAYLOAD_BYTES,
        17,
    )
    assert len(maximum) == 1_052_813

    baseline = GOLDENS[2]
    baseline_preimage = _operation_preimage(*baseline[:9])
    mutations = (
        (r"C:\other", *baseline[1:9]),
        (baseline[0], "23" * 16, *baseline[2:9]),
        (baseline[0], baseline[1], "F" * 64, *baseline[3:9]),
        (*baseline[:3], "cas_existing_identical_no_stage", "not_attempted", "not_attempted", None, 0, 0),
        (*baseline[:6], B + b"x", baseline[7], baseline[8]),
        (*baseline[:7], 2, baseline[8]),
        (*baseline[:8], 3),
    )
    for mutation in mutations:
        assert _h(_operation_preimage(*mutation)) != _h(baseline_preimage)
    digest_substitution = _operation_preimage(
        *baseline[:6], hashlib.sha256(B).digest(), baseline[7], baseline[8]
    )
    assert digest_substitution != baseline_preimage


def test_uprime_local_staging_fake_publisher_parent_missing_error_and_nondirectory(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(missing, "30" * 16)
    assert not missing.exists()

    nondirectory = tmp_path / "not-a-directory"
    nondirectory.write_bytes(b"fixture")
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(nondirectory, "31" * 16)
    assert nondirectory.read_bytes() == b"fixture"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("st_dev", True),
        ("st_ino", True),
        ("st_mode", True),
        ("st_dev", -1),
        ("st_ino", -1),
        ("st_mode", -1),
        ("st_dev", 1.0),
        ("st_ino", "1"),
        ("st_mode", None),
        ("st_file_attributes", True),
        ("st_file_attributes", -1),
        ("st_file_attributes", 1.0),
        ("st_file_attributes", None),
    ),
)
def test_uprime_local_staging_fake_publisher_parent_metadata_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    parent = tmp_path / f"parent-metadata-{field}-{value!r}"
    parent.mkdir()
    observed = os.stat(parent, follow_symlinks=False)
    fake = _fake_stat(observed, **{field: value})
    open_calls: list[Any] = []
    monkeypatch.setattr(publisher, "_os_stat", lambda *args, **kwargs: fake)
    monkeypatch.setattr(
        publisher,
        "_os_open",
        lambda *args, **kwargs: open_calls.append((args, kwargs)),
    )
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, "32" * 16)
    assert open_calls == []
    assert tuple(parent.iterdir()) == ()


@pytest.mark.parametrize(
    ("mode", "attributes"),
    (
        (stat.S_IFLNK | 0o777, 0),
        (stat.S_IFDIR | 0o755, 0x400),
        (stat.S_IFREG | 0o644, 0),
    ),
)
def test_uprime_local_staging_fake_publisher_parent_kind_and_reparse_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: int,
    attributes: int,
) -> None:
    parent = tmp_path / f"parent-kind-{mode}-{attributes}"
    parent.mkdir()
    observed = os.stat(parent, follow_symlinks=False)
    fake = _fake_stat(observed, st_mode=mode, st_file_attributes=attributes)
    opened: list[Any] = []
    monkeypatch.setattr(publisher, "_os_stat", lambda *args, **kwargs: fake)
    monkeypatch.setattr(publisher, "_os_open", lambda *args, **kwargs: opened.append(args))
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, "33" * 16)
    assert opened == []


def test_uprime_local_staging_fake_publisher_absent_parent_file_attributes_is_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "parent-no-file-attributes"
    parent.mkdir()
    original = publisher._os_stat

    def without_attributes(path: str, **kwargs: Any) -> Any:
        value = original(path, **kwargs)
        if os.path.normcase(path) == os.path.normcase(str(parent.absolute())):
            return _fake_stat(value, include_attributes=False)
        return value

    monkeypatch.setattr(publisher, "_os_stat", without_attributes)
    result = _changed(parent, "34" * 16)
    assert Path(result.stage_path).read_bytes() == B


def test_uprime_local_staging_fake_publisher_open_flags_mode_collision_and_no_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "collision"
    parent.mkdir()
    nonce = "35" * 16
    stage = parent / _stage_basename(nonce)
    stage.write_bytes(b"preexisting-collision")
    original_open = publisher._os_open
    original_stat = publisher._os_stat
    opens: list[tuple[str, int, int]] = []
    stats: list[str] = []

    def tracked_open(path: str, flags: int, mode: int) -> int:
        opens.append((path, flags, mode))
        return original_open(path, flags, mode)

    def tracked_stat(path: str, **kwargs: Any) -> Any:
        stats.append(path)
        assert os.path.normcase(path) != os.path.normcase(str(stage.absolute()))
        return original_stat(path, **kwargs)

    monkeypatch.setattr(publisher, "_os_open", tracked_open)
    monkeypatch.setattr(publisher, "_os_stat", tracked_stat)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce)
    assert len(opens) == 1
    path, flags, mode = opens[0]
    expected_flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    for optional in ("O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_NOFOLLOW"):
        expected_flags |= getattr(os, optional, 0)
    assert path == str(stage.absolute())
    assert flags == expected_flags
    assert mode == 0o600
    assert flags & getattr(os, "O_TRUNC", 0) == 0
    assert flags & getattr(os, "O_APPEND", 0) == 0
    assert stage.read_bytes() == b"preexisting-collision"
    assert stats == [str(parent.absolute())]
    assert tuple(parent.iterdir()) == (stage,)


@pytest.mark.parametrize("bad_fd", (-1, True, 1.0, None, "3"))
def test_uprime_local_staging_fake_publisher_invalid_open_descriptor_is_not_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_fd: Any,
) -> None:
    parent = tmp_path / f"invalid-fd-{bad_fd!r}"
    parent.mkdir()
    closed: list[Any] = []
    monkeypatch.setattr(publisher, "_os_open", lambda *args: bad_fd)
    monkeypatch.setattr(publisher, "_os_close", lambda fd: closed.append(fd))
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, "36" * 16)
    assert closed == []
    assert tuple(parent.iterdir()) == ()


def test_uprime_local_staging_fake_publisher_open_error_is_mapped_without_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "open-error"
    parent.mkdir()
    closed: list[int] = []

    def failed_open(*args: Any) -> int:
        del args
        raise OSError("injected open error")

    monkeypatch.setattr(publisher, "_os_open", failed_open)
    monkeypatch.setattr(publisher, "_os_close", lambda fd: closed.append(fd))
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, "37" * 16)
    assert closed == []
    assert tuple(parent.iterdir()) == ()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("st_dev", True),
        ("st_ino", True),
        ("st_mode", True),
        ("st_ctime_ns", True),
        ("st_size", True),
        ("st_mtime_ns", True),
        ("st_file_attributes", True),
        ("st_dev", -1),
        ("st_size", -1),
        ("st_file_attributes", -1),
        ("st_mode", stat.S_IFDIR | 0o755),
        ("st_size", 1),
        ("st_file_attributes", 0x400),
    ),
)
def test_uprime_local_staging_fake_publisher_f0_metadata_failure_closes_once_and_retains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    parent = tmp_path / f"f0-{field}-{value!r}"
    parent.mkdir()
    original_fstat = publisher._os_fstat
    original_close = publisher._os_close
    fstats = 0
    closes: list[int] = []

    def injected_fstat(fd: int) -> Any:
        nonlocal fstats
        fstats += 1
        observed = original_fstat(fd)
        assert fstats == 1
        return _fake_stat(observed, **{field: value})

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_fstat", injected_fstat)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "38" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce)
    assert fstats == 1
    assert len(closes) == 1
    stage = parent / _stage_basename(nonce)
    assert stage.exists()
    assert stage.read_bytes() == b""


@pytest.mark.parametrize("failure", ("zero", "negative", "bool", "over", "error"))
def test_uprime_local_staging_fake_publisher_write_failures_close_once_and_retain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    parent = tmp_path / f"write-{failure}"
    parent.mkdir()
    original_close = publisher._os_close
    writes: list[int] = []
    closes: list[int] = []

    def injected_write(fd: int, data: Any) -> int:
        del fd
        writes.append(len(data))
        if failure == "zero":
            return 0
        if failure == "negative":
            return -1
        if failure == "bool":
            return True
        if failure == "over":
            return len(data) + 1
        raise OSError("injected write error")

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_write", injected_write)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "40" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert writes == [7]
    assert len(closes) == 1
    stage = parent / _stage_basename(nonce)
    assert stage.exists()
    assert stage.read_bytes() == b""


@pytest.mark.parametrize("bad_seek", (True, None, -1, 1, 1.0, "0", "error"))
def test_uprime_local_staging_fake_publisher_seek_failures_close_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_seek: Any,
) -> None:
    parent = tmp_path / f"seek-{bad_seek!r}"
    parent.mkdir()
    original_close = publisher._os_close
    closes: list[int] = []

    def injected_seek(fd: int, offset: int, whence: int) -> Any:
        del fd
        assert (offset, whence) == (0, os.SEEK_SET)
        if bad_seek == "error":
            raise OSError("injected seek error")
        return bad_seek

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_lseek", injected_seek)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "41" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


@pytest.mark.parametrize(
    "failure",
    ("short", "early_eof", "nonbytes", "overlong", "growth", "error", "raw_mismatch"),
)
def test_uprime_local_staging_fake_publisher_readback_failures_reject_digest_only_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    parent = tmp_path / f"read-{failure}"
    parent.mkdir()
    original_read = publisher._os_read
    original_close = publisher._os_close
    calls: list[int] = []
    closes: list[int] = []

    def injected_read(fd: int, count: int) -> Any:
        calls.append(count)
        if failure == "error":
            raise OSError("injected read error")
        if failure == "early_eof":
            return b""
        if failure == "nonbytes":
            return bytearray(original_read(fd, count))
        if failure == "short":
            return original_read(fd, max(0, count - 1))
        raw = original_read(fd, count)
        if failure == "overlong":
            return raw + b"x"
        if failure == "growth" and len(calls) >= 2:
            assert count == 1
            return b"x"
        if failure == "raw_mismatch" and raw:
            return bytes((raw[0] ^ 0xFF,)) + raw[1:]
        return raw

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_read", injected_read)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "42" * 16
    payload = b"exact-raw-payload"
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, payload)
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).read_bytes() == payload
    assert 1 <= len(calls) <= 2


def test_uprime_local_staging_fake_publisher_constant_digest_cannot_mask_raw_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "constant-digest-wrong-raw.bin"
    path.write_bytes(B)
    fd = os.open(path, os.O_RDWR)
    updates: list[bytes] = []

    class ConstantDigest:
        def update(self, raw: bytes) -> None:
            updates.append(raw)

        def hexdigest(self) -> str:
            return "A" * 64

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(publisher.hashlib, "sha256", lambda *args: ConstantDigest())
            with pytest.raises(
                publisher.LocalStagingFakePublisherV10Error,
                match="raw readback differs",
            ):
                publisher._readback_payload(fd, A)
    finally:
        os.close(fd)
    # The direct raw comparison fires before either constant-digest update or
    # final comparison can hide the same-length wrong bytes.
    assert updates == []


@pytest.mark.parametrize("bound_site", ("write", "read_data", "read_eof"))
def test_uprime_local_staging_fake_publisher_lowered_call_bounds_reject_at_exact_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bound_site: str,
) -> None:
    path = tmp_path / f"lowered-bound-{bound_site}.bin"
    path.write_bytes(b"" if bound_site == "write" else b"ab")
    fd = os.open(path, os.O_RDWR)
    calls: list[int] = []
    original_write = publisher._os_write
    original_read = publisher._os_read
    try:
        with monkeypatch.context() as scoped:
            if bound_site == "write":
                scoped.setattr(publisher, "_MAX_WRITE_CALLS", 1)

                def one_byte_write(descriptor: int, data: Any) -> int:
                    calls.append(len(data))
                    return original_write(descriptor, data[:1])

                scoped.setattr(publisher, "_os_write", one_byte_write)
                with pytest.raises(
                    publisher.LocalStagingFakePublisherV10Error,
                    match="write call bound",
                ):
                    publisher._write_payload(fd, b"ab")
                assert calls == [2]
            else:
                scoped.setattr(publisher, "_IO_CHUNK_BYTES", 1)
                scoped.setattr(publisher, "_MAX_READ_CALLS", 1)

                def tracked_read(descriptor: int, count: int) -> bytes:
                    calls.append(count)
                    return original_read(descriptor, count)

                scoped.setattr(publisher, "_os_read", tracked_read)
                proposal = b"ab" if bound_site == "read_data" else b"a"
                with pytest.raises(
                    publisher.LocalStagingFakePublisherV10Error,
                    match="read call bound",
                ):
                    publisher._readback_payload(fd, proposal)
                assert calls == [1, 1]
    finally:
        os.close(fd)


@pytest.mark.parametrize(
    ("call_index", "field", "value_kind"),
    (
        (2, "st_dev", "increment"),
        (2, "st_ino", "increment"),
        (2, "st_mode", "directory"),
        (2, "st_size", "increment"),
        (2, "st_file_attributes", "reparse"),
        (3, "st_dev", "increment"),
        (3, "st_ino", "increment"),
        (3, "st_mode", "permission"),
        (3, "st_ctime_ns", "increment"),
        (3, "st_size", "increment"),
        (3, "st_mtime_ns", "increment"),
        (3, "st_file_attributes", "reparse"),
    )
    + tuple(
        (call_index, field, "bool")
        for call_index in (2, 3)
        for field in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_ctime_ns",
            "st_size",
            "st_mtime_ns",
            "st_file_attributes",
        )
    )
    + (
        (2, "st_file_attributes", "negative"),
        (3, "st_file_attributes", "negative"),
    ),
)
def test_uprime_local_staging_fake_publisher_f1_f2_identity_size_and_stability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    call_index: int,
    field: str,
    value_kind: str,
) -> None:
    parent = tmp_path / f"fstat-{call_index}-{field}-{value_kind}"
    parent.mkdir()
    original_fstat = publisher._os_fstat
    original_close = publisher._os_close
    calls = 0
    closes: list[int] = []

    def injected_fstat(fd: int) -> Any:
        nonlocal calls
        calls += 1
        observed = original_fstat(fd)
        if calls != call_index:
            return observed
        current = getattr(observed, field, 0)
        if value_kind == "increment":
            value = int(current) + 1
        elif value_kind == "directory":
            value = stat.S_IFDIR | 0o755
        elif value_kind == "permission":
            value = stat.S_IFREG | 0o777
        elif value_kind == "reparse":
            value = 0x400
        elif value_kind == "bool":
            value = True
        else:
            value = -1
        return _fake_stat(observed, **{field: value})

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_fstat", injected_fstat)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "43" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert calls == call_index
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


@pytest.mark.parametrize("field", ("st_mode", "st_ctime_ns", "st_mtime_ns"))
def test_uprime_local_staging_fake_publisher_f1_may_change_from_f0_but_f2_must_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    parent = tmp_path / f"f1-allowed-{field}"
    parent.mkdir()
    original_fstat = publisher._os_fstat
    calls = 0
    frozen_value: int | None = None

    def changed_times(fd: int) -> Any:
        nonlocal calls, frozen_value
        calls += 1
        observed = original_fstat(fd)
        if calls == 1:
            return observed
        if calls == 2:
            frozen_value = (
                stat.S_IFREG | 0o777
                if field == "st_mode"
                else int(getattr(observed, field)) + 1000
            )
        assert frozen_value is not None
        return _fake_stat(observed, **{field: frozen_value})

    monkeypatch.setattr(publisher, "_os_fstat", changed_times)
    result = _changed(parent, "44" * 16, b"payload")
    assert result.outcome == "staged_intended_fake_publish_acknowledged"
    assert calls == 3


@pytest.mark.parametrize("bad_close", (0, False, True, "none", "error"))
def test_uprime_local_staging_fake_publisher_close_exact_once_return_and_error_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_close: Any,
) -> None:
    parent = tmp_path / f"close-{bad_close!r}"
    parent.mkdir()
    original_close = publisher._os_close
    calls: list[int] = []

    def injected_close(fd: int) -> Any:
        calls.append(fd)
        original_close(fd)
        if bad_close == "error":
            raise OSError("injected close error")
        return bad_close

    monkeypatch.setattr(publisher, "_os_close", injected_close)
    nonce = "45" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert len(calls) == 1
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


def test_uprime_local_staging_fake_publisher_baseexception_propagates_after_one_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "baseexception"
    parent.mkdir()
    original_close = publisher._os_close
    closes: list[int] = []

    class InjectedBaseException(BaseException):
        pass

    def catastrophic_write(*args: Any) -> int:
        del args
        raise InjectedBaseException("must not be mapped")

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, "_os_write", catastrophic_write)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = "4a" * 16
    with pytest.raises(InjectedBaseException):
        _changed(parent, nonce, b"payload")
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).exists()


@pytest.mark.parametrize("close_failure", ("exception", "non_none"))
def test_uprime_local_staging_fake_publisher_primary_baseexception_survives_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_failure: str,
) -> None:
    parent = tmp_path / f"primary-base-close-{close_failure}"
    parent.mkdir()
    original_close = publisher._os_close
    closes: list[int] = []

    class InjectedPrimary(BaseException):
        pass

    def catastrophic_write(*args: Any) -> int:
        del args
        raise InjectedPrimary("primary BaseException must survive close")

    def failing_close(fd: int) -> Any:
        closes.append(fd)
        original_close(fd)
        if close_failure == "exception":
            raise RuntimeError("ordinary close exception")
        return 0

    monkeypatch.setattr(publisher, "_os_write", catastrophic_write)
    monkeypatch.setattr(publisher, "_os_close", failing_close)
    nonce = "4b" * 16
    with pytest.raises(InjectedPrimary, match="primary BaseException must survive close"):
        _changed(parent, nonce, b"payload")
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).exists()


def test_uprime_local_staging_fake_publisher_primary_and_close_failure_attempts_close_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "primary-and-close-failure"
    parent.mkdir()
    original_close = publisher._os_close
    closes: list[int] = []

    def failed_read(*args: Any) -> bytes:
        del args
        raise OSError("primary read error")

    def failed_close(fd: int) -> None:
        closes.append(fd)
        original_close(fd)
        raise OSError("secondary close error")

    monkeypatch.setattr(publisher, "_os_read", failed_read)
    monkeypatch.setattr(publisher, "_os_close", failed_close)
    nonce = "46" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert len(closes) == 1
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


@pytest.mark.parametrize(
    ("field", "value_kind"),
    (
        ("st_dev", "increment"),
        ("st_ino", "increment"),
        ("st_size", "increment"),
        ("st_mode", "directory"),
        ("st_file_attributes", "reparse"),
        ("st_dev", "bool"),
        ("st_ino", "bool"),
        ("st_mode", "bool"),
        ("st_ctime_ns", "bool"),
        ("st_size", "bool"),
        ("st_mtime_ns", "bool"),
        ("st_file_attributes", "bool"),
        ("st_file_attributes", "negative"),
    ),
)
def test_uprime_local_staging_fake_publisher_postclose_path_validation_and_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value_kind: str,
) -> None:
    parent = tmp_path / f"path-{field}-{value_kind}"
    parent.mkdir()
    original_stat = publisher._os_stat
    calls = 0

    def injected_stat(path: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        observed = original_stat(path, **kwargs)
        if calls != 2:
            return observed
        current = getattr(observed, field, 0)
        if value_kind == "increment":
            value = int(current) + 1
        elif value_kind == "directory":
            value = stat.S_IFDIR | 0o755
        elif value_kind == "reparse":
            value = 0x400
        elif value_kind == "negative":
            value = -1
        else:
            value = True
        return _fake_stat(observed, **{field: value})

    monkeypatch.setattr(publisher, "_os_stat", injected_stat)
    nonce = "47" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert calls == 2
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


@pytest.mark.parametrize("field", ("st_mode", "st_ctime_ns", "st_mtime_ns"))
def test_uprime_local_staging_fake_publisher_crossclose_nonbinding_metadata_may_finalize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    parent = tmp_path / f"postclose-allowed-{field}"
    parent.mkdir()
    original_stat = publisher._os_stat
    calls = 0

    def finalized(path: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        observed = original_stat(path, **kwargs)
        if calls != 2:
            return observed
        if field == "st_mode":
            value = stat.S_IFREG | 0o777
        else:
            value = int(getattr(observed, field)) + 10_000
        return _fake_stat(observed, **{field: value})

    monkeypatch.setattr(publisher, "_os_stat", finalized)
    result = _changed(parent, "48" * 16, b"payload")
    assert result.outcome == "staged_intended_fake_publish_acknowledged"
    assert calls == 3


@pytest.mark.parametrize("field", ("st_dev", "st_ino", "st_mode", "reparse"))
def test_uprime_local_staging_fake_publisher_final_parent_drift_fails_after_retention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    parent = tmp_path / f"parent-drift-{field}"
    parent.mkdir()
    original_stat = publisher._os_stat
    calls = 0

    def drifting(path: str, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        observed = original_stat(path, **kwargs)
        if calls != 3:
            return observed
        if field == "reparse":
            return _fake_stat(observed, st_file_attributes=0x400)
        if field == "st_mode":
            return _fake_stat(observed, st_mode=stat.S_IFDIR | 0o700)
        return _fake_stat(observed, **{field: int(getattr(observed, field)) + 1})

    monkeypatch.setattr(publisher, "_os_stat", drifting)
    nonce = "49" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert calls == 3
    assert (parent / _stage_basename(nonce)).read_bytes() == b"payload"


@pytest.mark.parametrize(
    ("seam", "failure_index"),
    (
        ("_os_stat", 1),
        ("_os_stat", 2),
        ("_os_stat", 3),
        ("_os_fstat", 1),
        ("_os_fstat", 2),
        ("_os_fstat", 3),
    ),
)
def test_uprime_local_staging_fake_publisher_every_stat_endpoint_error_is_mapped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    seam: str,
    failure_index: int,
) -> None:
    parent = tmp_path / f"endpoint-error-{seam}-{failure_index}"
    parent.mkdir()
    original = getattr(publisher, seam)
    original_close = publisher._os_close
    calls = 0
    closes: list[int] = []

    def injected(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == failure_index:
            raise RuntimeError("injected metadata endpoint failure")
        return original(*args, **kwargs)

    def tracked_close(fd: int) -> None:
        closes.append(fd)
        return original_close(fd)

    monkeypatch.setattr(publisher, seam, injected)
    monkeypatch.setattr(publisher, "_os_close", tracked_close)
    nonce = f"{0x60 + failure_index:02x}" * 16
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _changed(parent, nonce, b"payload")
    assert calls == failure_index
    stage = parent / _stage_basename(nonce)
    if seam == "_os_stat" and failure_index == 1:
        assert closes == []
        assert not stage.exists()
    else:
        assert len(closes) == 1
        assert stage.exists()


def test_uprime_local_staging_fake_publisher_failure_residue_same_nonce_collision_distinct_nonce_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "residue-retry"
    parent.mkdir()
    original_write = publisher._os_write
    calls = 0

    def prefix_then_fail(fd: int, data: Any) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_write(fd, data[:3])
        raise OSError("injected after prefix")

    nonce = "50" * 16
    state = _state_with(A)
    state_before = _mapping(state)
    monkeypatch.setattr(publisher, "_os_write", prefix_then_fail)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(
            str(parent.absolute()),
            nonce,
            state,
            state.state_version_sha256,
            b"longer-payload",
        )
    stage = parent / _stage_basename(nonce)
    assert stage.read_bytes() == b"lon"
    assert _mapping(state) == state_before

    monkeypatch.setattr(publisher, "_os_write", original_write)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(
            str(parent.absolute()),
            nonce,
            state,
            state.state_version_sha256,
            B,
        )
    assert stage.read_bytes() == b"lon"
    distinct = _call(
        str(parent.absolute()),
        "51" * 16,
        state,
        state.state_version_sha256,
        B,
    )
    assert Path(distinct.stage_path).read_bytes() == B
    assert sorted(path.name for path in parent.iterdir()) == sorted(
        (_stage_basename(nonce), _stage_basename("51" * 16))
    )


def test_uprime_local_staging_fake_publisher_constructor_every_field_revalidates_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    missing = str((tmp_path / "never-created-conflict-parent").absolute())
    result = _call(
        missing,
        "52" * 16,
        state,
        _absent_state().state_version_sha256,
        B,
    )
    physical = _forbid_physical(monkeypatch)
    mapping = _mapping(result)
    assert publisher.LocalStagingFakePublishResultV10(**mapping) == result
    for field in RESULT_FIELDS:
        forged = dict(mapping)
        forged[field] = _same_type_forgery(mapping[field])
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            publisher.LocalStagingFakePublishResultV10(**forged)
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            replace(result, **{field: forged[field]})
        wrong_type = dict(mapping)
        wrong_type[field] = _wrong_type_forgery(mapping[field])
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            publisher.LocalStagingFakePublishResultV10(**wrong_type)
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            replace(result, **{field: wrong_type[field]})
    assert physical == []


def test_uprime_local_staging_fake_publisher_constructor_compares_every_transition_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    result = _call(
        str((tmp_path / "missing-transition-parent").absolute()),
        "53" * 16,
        state,
        _absent_state().state_version_sha256,
        B,
    )
    mapping = _mapping(result)
    transition = result.cas_transition
    physical = _forbid_physical(monkeypatch)
    monkeypatch.setattr(
        cas.InMemoryFakeCasTransitionV10,
        "__eq__",
        lambda self, other: True,
    )
    monkeypatch.setattr(
        cas.InMemoryFakeCasStateV10,
        "__eq__",
        lambda self, other: True,
    )
    for field in fields(transition):
        forged_transition = copy.copy(transition)
        original = getattr(forged_transition, field.name)
        object.__setattr__(forged_transition, field.name, _same_type_forgery(original))
        # Keep the original digest unless the digest itself is the selected
        # mutation; a digest-only validator and dataclass equality mutant must
        # still die.
        if field.name != "transition_sha256":
            assert forged_transition.transition_sha256 == transition.transition_sha256
        forged = dict(mapping, cas_transition=forged_transition)
        with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
            publisher.LocalStagingFakePublishResultV10(**forged)
    assert physical == []


def test_uprime_local_staging_fake_publisher_staged_record_is_forgeable_nonattestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_parent = tmp_path / "real-stage-for-value"
    real_parent.mkdir()
    result = _changed(real_parent, "54" * 16, B)
    imaginary_parent = str((tmp_path / "never-created-stage-parent").absolute())
    imaginary_stage = os.path.join(imaginary_parent, result.stage_basename)
    mapping = _mapping(result)
    mapping["staging_parent"] = imaginary_parent
    mapping["stage_path"] = imaginary_stage
    mapping["operation_sha256"] = _h(
        _operation_preimage(
            imaginary_parent,
            result.collision_nonce,
            result.cas_transition.transition_sha256,
            result.outcome,
            result.parent_observation_status,
            result.stage_status,
            B,
            result.write_call_count,
            result.read_call_count,
        )
    )
    physical = _forbid_physical(monkeypatch)
    forged = publisher.LocalStagingFakePublishResultV10(**mapping)
    assert forged.stage_path == imaginary_stage
    assert not Path(imaginary_parent).exists()
    assert physical == []


def test_uprime_local_staging_fake_publisher_bypass_mutated_state_rejects_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    malformed = copy.copy(state)
    object.__setattr__(malformed, "cell_payload_sha256", "0" * 64)
    physical = _forbid_physical(monkeypatch)
    with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
        _call(
            str((tmp_path / "missing-bypass-parent").absolute()),
            "55" * 16,
            malformed,
            malformed.state_version_sha256,
            B,
        )
    assert physical == []


def test_uprime_local_staging_fake_publisher_resource_arithmetic_and_open_flag_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MAX_PAYLOAD_BYTES * 2 == 2_097_152
    assert CHUNK_BYTES == 65_536
    assert (MAX_PAYLOAD_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES + 1 == 17
    assert (
        len(D_OPERATION)
        + 4
        + 4096
        + 16
        + 32
        + 4
        + 8
        + MAX_PAYLOAD_BYTES
        + 8
        + 8
        == 1_052_813
    )
    expected_flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    for optional in ("O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_NOFOLLOW"):
        expected_flags |= getattr(os, optional, 0)
    assert publisher._OPEN_FLAGS == expected_flags

    constant_expectations = {
        "_MAX_PAYLOAD_BYTES": MAX_PAYLOAD_BYTES,
        "_MAX_STAGING_PARENT_UTF8_BYTES": 4096,
        "_MAX_STAGE_PATH_UTF8_BYTES": 4162,
        "_COLLISION_NONCE_CHARS": 32,
        "_IO_CHUNK_BYTES": CHUNK_BYTES,
        "_MAX_WRITE_CALLS": MAX_PAYLOAD_BYTES,
        "_MAX_READ_CALLS": 17,
        "_MAX_FILESYSTEM_PAYLOAD_WORK_BYTES": 2_097_152,
        "_MAX_PEAK_TRANSIENT_BUFFER_BYTES": CHUNK_BYTES,
        "_MAX_RETAINED_PAYLOAD_COPY_BYTES": 0,
        "_MAX_STAGE_FILE_CREATES": 1,
        "_MAX_RETAINED_STAGE_BYTES": MAX_PAYLOAD_BYTES,
        "_MAX_OPERATION_HASH_PREIMAGE_BYTES": 1_052_813,
        "_OPEN_FLAGS": expected_flags,
        "_OPEN_MODE": 0o600,
    }
    state = _state_with(A)
    stale = _absent_state().state_version_sha256
    parent = str((tmp_path / "constant-precedence").absolute())
    for name, expected in constant_expectations.items():
        assert getattr(publisher, name) == expected
        with monkeypatch.context() as scoped:
            scoped.setattr(publisher, name, expected + 1)
            physical = _forbid_physical(scoped)
            fake_cas_calls: list[Any] = []
            scoped.setattr(
                publisher,
                "step_in_memory_fake_cas_v1_0",
                lambda *args, **kwargs: fake_cas_calls.append((args, kwargs)),
            )
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(parent, "56" * 16, state, stale, B)
            assert fake_cas_calls == []
            assert physical == []


def test_uprime_local_staging_fake_publisher_every_frozen_constant_fails_before_cas_and_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_with(A)
    parent = str((tmp_path / "all-frozen-constants").absolute())
    for name in FROZEN_CONSTANT_NAMES:
        original = getattr(publisher, name)
        with monkeypatch.context() as scoped:
            scoped.setattr(publisher, name, _mutated_constant(original))
            physical = _forbid_physical(scoped)
            fake_cas_calls: list[Any] = []
            scoped.setattr(
                publisher,
                "step_in_memory_fake_cas_v1_0",
                lambda *args, **kwargs: fake_cas_calls.append((args, kwargs)),
            )
            with pytest.raises(publisher.LocalStagingFakePublisherV10Error):
                _call(
                    parent,
                    "57" * 16,
                    state,
                    state.state_version_sha256,
                    B,
                )
            assert fake_cas_calls == [], name
            assert physical == [], name


def test_uprime_local_staging_fake_publisher_ast_forbids_expanded_capabilities() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = _source_tree()
    assert not any(
        isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
    )
    public_functions = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    assert public_functions == ["stage_and_fake_publish_normal_v1_0"]
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == [
        "LocalStagingFakePublisherV10Error",
        "LocalStagingFakePublishResultV10",
    ]
    forbidden_calls = {
        "__import__",
        "eval",
        "exec",
        "input",
        "resolve",
        "realpath",
        "abspath",
        "casefold",
        "mkdir",
        "makedirs",
        "link",
        "rename",
        "replace",
        "unlink",
        "remove",
        "fsync",
        "flush",
        "listdir",
        "scandir",
        "walk",
        "glob",
        "rglob",
        "sleep",
        "time",
        "perf_counter",
        "random",
        "randint",
        "uuid4",
        "Popen",
        "run",
        "Thread",
        "Process",
        "connect",
        "send",
        "recv",
        "read_text",
        "read_bytes",
        "write_text",
        "write_bytes",
    }
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    assert forbidden_calls.isdisjoint(calls)
    forbidden_tokens = (
        "attempt_manifest",
        "claim_receipt",
        "seed_inventory",
        "artifact_observer",
        "bundle_reservation",
        "rerun_license",
        "rpc_ledger",
        "canonical_json",
        "socket",
        "subprocess",
        "requests",
        "registered_run",
        "worker",
        "scanner",
        "writer",
        "recovery_marker",
    )
    assert all(token not in source for token in forbidden_tokens)
    assert "except BaseException" not in source
    assert "memoryview" in source
    assert ".update(" in source
    assert "tobytes" not in source
    assert "O_EXCL" in source and "O_NOFOLLOW" in source
    assert "follow_symlinks=False" in source


def test_uprime_local_staging_fake_publisher_anchors_registry_and_collection() -> None:
    required = {
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2D_AMENDMENT_PATH,
        litmus.LOCAL_STAGING_FAKE_PUBLISHER_SOURCE_PATH,
        litmus.LOCAL_STAGING_FAKE_PUBLISHER_TEST_SUPPORT_PATH,
    }
    assert required <= set(litmus.ANCHOR_PATHS)
    collector = COLLECTOR_PATH.read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_local_staging_fake_publisher_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_local_staging_fake_publisher_cases") == 1
    registry = ROOT / "docs/experiments/uprime_odlrq_u1_rerun_license_registry.json"
    raw = registry.read_bytes()
    assert raw == (
        b'{"default_allow":false,"licenses":{},"schema_version":'
        b'"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n'
    )
    assert _h(raw) == "ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B"
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "runs/" not in source


def test_uprime_local_staging_fake_publisher_support_exports_exact_ordered_tests_only() -> None:
    assert __all__ == EXPECTED_TEST_EXPORTS
    assert len(__all__) == len(set(__all__))
    actual = [
        name
        for name, value in globals().items()
        if name.startswith("test_uprime_local_staging_fake_publisher_")
        and inspect.isfunction(value)
        and value.__module__ == __name__
    ]
    assert actual == EXPECTED_TEST_EXPORTS
    assert all(
        name.startswith("test_uprime_local_staging_fake_publisher_")
        and inspect.isfunction(globals()[name])
        and globals()[name].__module__ == __name__
        for name in __all__
    )


EXPECTED_TEST_EXPORTS = [
    "test_uprime_local_staging_fake_publisher_exact_surface_imports_fields_and_signatures",
    "test_uprime_local_staging_fake_publisher_record_is_frozen_slotted",
    "test_uprime_local_staging_fake_publisher_parent_grammar_rejects_without_io",
    "test_uprime_local_staging_fake_publisher_native_absolute_normalization_spellings_reject_before_io",
    "test_uprime_local_staging_fake_publisher_nonce_grammar_rejects_without_io",
    "test_uprime_local_staging_fake_publisher_exact_types_and_hostile_coercions_reject",
    "test_uprime_local_staging_fake_publisher_utf8_parent_bounds_and_exact_join",
    "test_uprime_local_staging_fake_publisher_lexical_seam_returns_fail_closed",
    "test_uprime_local_staging_fake_publisher_windows_path_spellings_are_explicit",
    "test_uprime_local_staging_fake_publisher_fake_cas_precedence_and_no_stage_io",
    "test_uprime_local_staging_fake_publisher_fake_cas_errors_types_and_baseexception",
    "test_uprime_local_staging_fake_publisher_payload_bounds_and_max_generation_precedence",
    "test_uprime_local_staging_fake_publisher_three_rows_every_dynamic_cell",
    "test_uprime_local_staging_fake_publisher_real_payload_boundaries",
    "test_uprime_local_staging_fake_publisher_partial_writes_memoryviews_and_io_order",
    "test_uprime_local_staging_fake_publisher_prior_full_read_chunk_is_released_before_next_read",
    "test_uprime_local_staging_fake_publisher_operation_framing_goldens_and_mutations",
    "test_uprime_local_staging_fake_publisher_parent_missing_error_and_nondirectory",
    "test_uprime_local_staging_fake_publisher_parent_metadata_fail_closed",
    "test_uprime_local_staging_fake_publisher_parent_kind_and_reparse_reject",
    "test_uprime_local_staging_fake_publisher_absent_parent_file_attributes_is_zero",
    "test_uprime_local_staging_fake_publisher_open_flags_mode_collision_and_no_retry",
    "test_uprime_local_staging_fake_publisher_invalid_open_descriptor_is_not_closed",
    "test_uprime_local_staging_fake_publisher_open_error_is_mapped_without_close",
    "test_uprime_local_staging_fake_publisher_f0_metadata_failure_closes_once_and_retains",
    "test_uprime_local_staging_fake_publisher_write_failures_close_once_and_retain",
    "test_uprime_local_staging_fake_publisher_seek_failures_close_once",
    "test_uprime_local_staging_fake_publisher_readback_failures_reject_digest_only_semantics",
    "test_uprime_local_staging_fake_publisher_constant_digest_cannot_mask_raw_mismatch",
    "test_uprime_local_staging_fake_publisher_lowered_call_bounds_reject_at_exact_site",
    "test_uprime_local_staging_fake_publisher_f1_f2_identity_size_and_stability",
    "test_uprime_local_staging_fake_publisher_f1_may_change_from_f0_but_f2_must_match",
    "test_uprime_local_staging_fake_publisher_close_exact_once_return_and_error_behavior",
    "test_uprime_local_staging_fake_publisher_baseexception_propagates_after_one_close",
    "test_uprime_local_staging_fake_publisher_primary_baseexception_survives_close_failure",
    "test_uprime_local_staging_fake_publisher_primary_and_close_failure_attempts_close_once",
    "test_uprime_local_staging_fake_publisher_postclose_path_validation_and_binding",
    "test_uprime_local_staging_fake_publisher_crossclose_nonbinding_metadata_may_finalize",
    "test_uprime_local_staging_fake_publisher_final_parent_drift_fails_after_retention",
    "test_uprime_local_staging_fake_publisher_every_stat_endpoint_error_is_mapped",
    "test_uprime_local_staging_fake_publisher_failure_residue_same_nonce_collision_distinct_nonce_succeeds",
    "test_uprime_local_staging_fake_publisher_constructor_every_field_revalidates_without_io",
    "test_uprime_local_staging_fake_publisher_constructor_compares_every_transition_field",
    "test_uprime_local_staging_fake_publisher_staged_record_is_forgeable_nonattestation",
    "test_uprime_local_staging_fake_publisher_bypass_mutated_state_rejects_before_io",
    "test_uprime_local_staging_fake_publisher_resource_arithmetic_and_open_flag_snapshot",
    "test_uprime_local_staging_fake_publisher_every_frozen_constant_fails_before_cas_and_io",
    "test_uprime_local_staging_fake_publisher_ast_forbids_expanded_capabilities",
    "test_uprime_local_staging_fake_publisher_anchors_registry_and_collection",
    "test_uprime_local_staging_fake_publisher_support_exports_exact_ordered_tests_only",
]

__all__ = list(EXPECTED_TEST_EXPORTS)
