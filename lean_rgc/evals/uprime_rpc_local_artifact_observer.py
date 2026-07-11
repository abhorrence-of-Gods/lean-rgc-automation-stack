"""Bounded read-only Phase-2b2b observation of three receipt-derived paths.

The observer reports physical raw-byte/path observations only.  It does not
parse the artifacts, authenticate their origin, write files, or grant any
execution, publication, recovery, or later-stage authority.
"""

from dataclasses import dataclass
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_attempt_manifest import (
    AttemptManifestV10Error,
    PublicClaimReceiptV10,
)
from lean_rgc.evals.uprime_rpc_ledger import canonical_json_bytes


_OBSERVER_SCHEMA = "lean-rgc-uprime-u1-local-artifact-set-observer-v0.1"
_OBSERVER_SCOPE = "three_receipt_derived_local_paths_raw_bytes_only"
_ORIGIN_STATUS = "unknown_may_be_synthetic"
_SELECTOR_SCOPE = "one_caller_supplied_public_receipt"
_REGISTERED_RUN_DIR = "runs/uprime_u1_rpc_20260710"

_KINDS = ("reservation", "ledger", "report")
_SUFFIXES = (".json.reservation", ".responses.jsonl", ".json")
_RECEIPT_FIELD_NAMES = (
    "schema_version",
    "candidate_commit",
    "license_commit",
    "license_id",
    "remote_url",
    "remote_branch_ref",
    "remote_claim_ref",
    "remote_claim_oid",
    "registry_blob_oid",
    "registry_sha256",
    "candidate_tree_oid",
    "input_manifest_sha256",
    "claimed_at_utc",
)

_MAX_RESERVATION_BYTES = 1_048_576
_MAX_LEDGER_BYTES = 134_217_728
_MAX_REPORT_BYTES = 16_777_216
_READ_CHUNK_BYTES = 65_536
_MAX_TOTAL_ACCEPTED_BYTES = 152_043_520
_MAX_RETURNED_PAYLOAD_WORK_BYTES = 304_087_043
_MAX_READ_CALLS = 4_646
_MAX_PEAK_BUFFER_BYTES = 65_536

_UPPER_HEX64_RE = re.compile(r"[0-9A-F]{64}\Z", flags=re.ASCII)
_LOWER_HEX12_RE = re.compile(r"[0-9a-f]{12}\Z", flags=re.ASCII)
_REPOSITORY_PATH_RE = re.compile(
    r"runs/uprime_u1_rpc_20260710/rpc_diagnostic_"
    r"([0-9a-f]{12})(\.json\.reservation|\.responses\.jsonl|\.json)\Z",
    flags=re.ASCII,
)

_PRESENT_REASON = "stable_bounded_regular_file"
_DIRECT_ABSENT_REASON = "absent_at_both_points"
_PARENT_PRESENT_REASON = "stable_parent_directory"
_PARENT_ABSENT_REASON = "stable_parent_absence"
_PARENT_INDETERMINATE_REASONS = (
    "parent_initial_stat_error",
    "parent_absence_recheck_error",
    "parent_absence_changed",
    "parent_metadata_invalid",
    "parent_reparse_entry",
    "parent_nondirectory",
    "parent_final_stat_error",
    "parent_final_entry_invalid",
    "parent_drift",
)
_LOCAL_INDETERMINATE_REASONS = (
    "initial_stat_error",
    "absence_recheck_error",
    "absence_changed",
    "metadata_invalid",
    "reparse_entry",
    "nonregular_entry",
    "size_limit",
    "open_error",
    "fstat_error",
    "path_descriptor_mismatch",
    "seek_error",
    "read_error",
    "early_eof",
    "growth",
    "descriptor_drift",
    "content_drift",
    "final_stat_error",
    "final_entry_invalid",
    "path_drift",
    "close_error",
)
_PRECLOSE_REASONS = (
    "fstat_error",
    "path_descriptor_mismatch",
    "seek_error",
    "read_error",
    "early_eof",
    "growth",
    "descriptor_drift",
    "content_drift",
)
_PARENT_ROW_REASONS = (_PARENT_ABSENT_REASON,) + _PARENT_INDETERMINATE_REASONS

_os_path_isabs = os.path.isabs
_os_path_join = os.path.join
_os_stat = os.stat
_os_open = os.open
_os_fstat = os.fstat
_os_lseek = os.lseek
_os_read = os.read
_os_close = os.close

_FILESYSTEM_ERRORS = (Exception,)
_MISSING = object()


class LocalArtifactObservationV10Error(ValueError):
    """The bounded local observation input or invariant was invalid."""


class _MetadataError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class LocalArtifactObservationV10:
    artifact_kind: str
    repository_path: str
    observation_state: str
    reason_codes: tuple[str, ...]
    artifact_sha256: str | None
    artifact_bytes: int | None
    byte_limit: int
    content_validation: str
    authority_scope: str
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_row(self)


@dataclass(frozen=True, slots=True)
class LocalArtifactSetObservationV10:
    observer_schema_version: str
    observer_scope: str
    origin_status: str
    selector_scope: str
    claim_receipt: PublicClaimReceiptV10
    claim_receipt_sha256: str
    anchor: str
    registered_run_dir: str
    parent_namespace_state: str
    parent_reason_codes: tuple[str, ...]
    reservation: LocalArtifactObservationV10
    ledger: LocalArtifactObservationV10
    report: LocalArtifactObservationV10
    state_vector: tuple[str, str, str]
    present_count: int
    absent_count: int
    indeterminate_count: int
    total_present_bytes: int
    accepted_byte_upper_bound: int
    read_work_upper_bound_bytes: int
    read_call_upper_bound: int
    peak_buffer_upper_bound_bytes: int
    hash_algorithm: str
    snapshot_scope: str
    root_scope: str
    selector_binding: str
    basename_spelling_verification: str
    hostile_concurrent_reparse_prevention: str
    ancestor_link_containment: str
    reservation_validation: str
    ledger_validation: str
    report_validation: str
    cross_artifact_binding: str
    manifest_binding: str
    inventory_binding: str
    anchor_uniqueness: str
    artifact_claim_binding: str
    durability_observation: str
    cas_observation: str
    publication_observation: str
    recovery_observation: str
    witness_observation: str
    remote_claim_authentication: str
    git_object_authentication: str
    authority_scope: str
    canonical_run_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool

    def __post_init__(self) -> None:
        _validate_set(self)


def _fail(message: str) -> None:
    raise LocalArtifactObservationV10Error(message) from None


def _require_exact_str(value: object, name: str) -> str:
    if type(value) is not str:
        _fail(f"{name} is not an exact string")
    return value


def _require_exact_int(value: object, name: str) -> int:
    if type(value) is not int:
        _fail(f"{name} is not an exact integer")
    return value


def _require_false(value: object, name: str) -> None:
    if type(value) is not bool or value:
        _fail(f"{name} must be exact false")


def _resource_bounds() -> tuple[tuple[int, int, int], int, int, int, int]:
    limits = (
        _MAX_RESERVATION_BYTES,
        _MAX_LEDGER_BYTES,
        _MAX_REPORT_BYTES,
    )
    for value, name in zip(limits, _KINDS):
        if type(value) is not int or value < 0:
            _fail(f"{name} byte bound is invalid")
    if type(_READ_CHUNK_BYTES) is not int or _READ_CHUNK_BYTES <= 0:
        _fail("read chunk bound is invalid")
    derived = (
        _MAX_TOTAL_ACCEPTED_BYTES,
        _MAX_RETURNED_PAYLOAD_WORK_BYTES,
        _MAX_READ_CALLS,
        _MAX_PEAK_BUFFER_BYTES,
    )
    if any(type(value) is not int or value < 0 for value in derived):
        _fail("derived resource bound is invalid")
    total = sum(limits)
    work = 2 * total + len(limits)
    calls = 2 * sum(
        (limit + _READ_CHUNK_BYTES - 1) // _READ_CHUNK_BYTES + 1
        for limit in limits
    )
    if _MAX_TOTAL_ACCEPTED_BYTES != total:
        _fail("accepted-byte bound does not match its formula")
    if _MAX_RETURNED_PAYLOAD_WORK_BYTES != work:
        _fail("payload-work bound does not match its formula")
    if _MAX_READ_CALLS != calls:
        _fail("read-call bound does not match its formula")
    if _MAX_PEAK_BUFFER_BYTES != _READ_CHUNK_BYTES:
        _fail("peak-buffer bound does not match its formula")
    return (limits, total, work, calls, _MAX_PEAK_BUFFER_BYTES)


def _receipt_mapping(receipt: PublicClaimReceiptV10) -> dict[str, object]:
    return {name: getattr(receipt, name) for name in _RECEIPT_FIELD_NAMES}


def _reconstruct_receipt(value: object) -> PublicClaimReceiptV10:
    if type(value) is not PublicClaimReceiptV10:
        _fail("claim_receipt has the wrong record type")
    try:
        mapping = _receipt_mapping(value)
        return PublicClaimReceiptV10(
            **{name: mapping[name] for name in _RECEIPT_FIELD_NAMES}
        )
    except (AttributeError, AttemptManifestV10Error, TypeError, ValueError):
        _fail("claim_receipt failed public reconstruction")


def _receipt_digest(receipt: PublicClaimReceiptV10) -> str:
    try:
        raw = canonical_json_bytes(_receipt_mapping(receipt))
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        _fail("claim_receipt is outside canonical JSON")
    return hashlib.sha256(raw).hexdigest().upper()


def _repository_paths(anchor: str) -> tuple[str, str, str]:
    prefix = f"{_REGISTERED_RUN_DIR}/rpc_diagnostic_{anchor}"
    return (
        prefix + _SUFFIXES[0],
        prefix + _SUFFIXES[1],
        prefix + _SUFFIXES[2],
    )


def _join_path(*parts: str) -> str:
    try:
        value = _os_path_join(*parts)
    except _FILESYSTEM_ERRORS:
        _fail("path construction failed")
    if type(value) is not str or not value:
        _fail("path construction returned an invalid value")
    return value


def _validate_reason_tuple(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        _fail("reason_codes must be a nonempty exact tuple")
    if any(type(item) is not str for item in value):
        _fail("reason_codes contains a non-string")
    if len(set(value)) != len(value):
        _fail("reason_codes must be unique")
    return value


def _validate_row(value: LocalArtifactObservationV10) -> None:
    limits, _total, _work, _calls, _peak = _resource_bounds()
    kind = _require_exact_str(value.artifact_kind, "artifact_kind")
    if kind not in _KINDS:
        _fail("artifact_kind is invalid")
    index = _KINDS.index(kind)
    path = _require_exact_str(value.repository_path, "repository_path")
    match = _REPOSITORY_PATH_RE.fullmatch(path)
    if match is None or match.group(2) != _SUFFIXES[index]:
        _fail("repository_path does not match artifact_kind")
    byte_limit = _require_exact_int(value.byte_limit, "byte_limit")
    if byte_limit != limits[index]:
        _fail("byte_limit does not match artifact_kind")
    state = _require_exact_str(value.observation_state, "observation_state")
    if state not in ("present", "absent", "indeterminate"):
        _fail("observation_state is invalid")
    reasons = _validate_reason_tuple(value.reason_codes)

    if state == "present":
        if reasons != (_PRESENT_REASON,):
            _fail("present reason_codes is invalid")
        digest = _require_exact_str(value.artifact_sha256, "artifact_sha256")
        if _UPPER_HEX64_RE.fullmatch(digest) is None:
            _fail("artifact_sha256 is invalid")
        count = _require_exact_int(value.artifact_bytes, "artifact_bytes")
        if not 0 <= count <= byte_limit:
            _fail("artifact_bytes is outside byte_limit")
    elif state == "absent":
        if reasons not in ((_DIRECT_ABSENT_REASON,), (_PARENT_ABSENT_REASON,)):
            _fail("absent reason_codes is invalid")
        if value.artifact_sha256 is not None or value.artifact_bytes is not None:
            _fail("absent row must clear byte evidence")
    else:
        valid = False
        if len(reasons) == 1:
            valid = reasons[0] in (
                _LOCAL_INDETERMINATE_REASONS + _PARENT_INDETERMINATE_REASONS
            )
        elif len(reasons) == 2:
            valid = reasons[0] in _PRECLOSE_REASONS and reasons[1] == "close_error"
        if not valid:
            _fail("indeterminate reason_codes is invalid")
        if value.artifact_sha256 is not None or value.artifact_bytes is not None:
            _fail("indeterminate row must clear byte evidence")

    if _require_exact_str(value.content_validation, "content_validation") != "not_performed":
        _fail("content_validation is invalid")
    if _require_exact_str(value.authority_scope, "authority_scope") != "none":
        _fail("authority_scope is invalid")
    for name in (
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        _require_false(getattr(value, name), name)


def _validate_set(value: LocalArtifactSetObservationV10) -> None:
    limits, total, work, calls, peak = _resource_bounds()
    fixed_strings = (
        ("observer_schema_version", _OBSERVER_SCHEMA),
        ("observer_scope", _OBSERVER_SCOPE),
        ("origin_status", _ORIGIN_STATUS),
        ("selector_scope", _SELECTOR_SCOPE),
        ("registered_run_dir", _REGISTERED_RUN_DIR),
        ("hash_algorithm", "SHA-256"),
        ("snapshot_scope", "sequential_per_artifact_not_atomic_bundle"),
        ("root_scope", "one_caller_supplied_unauthenticated_prefix"),
        ("selector_binding", "caller_supplied_receipt_to_paths_only"),
        ("basename_spelling_verification", "not_performed"),
        ("hostile_concurrent_reparse_prevention", "not_provided"),
        ("ancestor_link_containment", "not_authenticated"),
        ("reservation_validation", "not_performed"),
        ("ledger_validation", "not_performed"),
        ("report_validation", "not_performed"),
        ("cross_artifact_binding", "not_performed"),
        ("manifest_binding", "not_performed"),
        ("inventory_binding", "not_performed"),
        ("anchor_uniqueness", "not_performed"),
        ("artifact_claim_binding", "not_performed"),
        ("durability_observation", "not_performed"),
        ("cas_observation", "not_performed"),
        ("publication_observation", "not_performed"),
        ("recovery_observation", "not_performed"),
        ("witness_observation", "not_performed"),
        ("remote_claim_authentication", "not_performed"),
        ("git_object_authentication", "not_performed"),
        ("authority_scope", "none"),
    )
    for name, expected in fixed_strings:
        if _require_exact_str(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")

    receipt = _reconstruct_receipt(value.claim_receipt)
    if receipt != value.claim_receipt:
        _fail("claim_receipt differs from its reconstruction")
    expected_digest = _receipt_digest(receipt)
    digest = _require_exact_str(value.claim_receipt_sha256, "claim_receipt_sha256")
    if digest != expected_digest:
        _fail("claim_receipt_sha256 is invalid")
    anchor = _require_exact_str(value.anchor, "anchor")
    if _LOWER_HEX12_RE.fullmatch(anchor) is None or anchor != receipt.license_commit[:12]:
        _fail("anchor is invalid")

    rows = (value.reservation, value.ledger, value.report)
    paths = _repository_paths(anchor)
    for index, row in enumerate(rows):
        if type(row) is not LocalArtifactObservationV10:
            _fail("artifact row has the wrong record type")
        _validate_row(row)
        if row.artifact_kind != _KINDS[index]:
            _fail("artifact rows are out of order")
        if row.repository_path != paths[index] or row.byte_limit != limits[index]:
            _fail("artifact row identity is invalid")

    parent_state = _require_exact_str(value.parent_namespace_state, "parent_namespace_state")
    parent_reasons = _validate_reason_tuple(value.parent_reason_codes)
    if len(parent_reasons) != 1:
        _fail("parent_reason_codes must be a singleton")
    if parent_state == "present":
        if parent_reasons != (_PARENT_PRESENT_REASON,):
            _fail("present parent reason is invalid")
        if any(row.reason_codes[0] in _PARENT_ROW_REASONS for row in rows):
            _fail("present parent contains a parent-derived child reason")
    elif parent_state == "absent":
        if parent_reasons != (_PARENT_ABSENT_REASON,):
            _fail("absent parent reason is invalid")
        if any(
            row.observation_state != "absent"
            or row.reason_codes != (_PARENT_ABSENT_REASON,)
            for row in rows
        ):
            _fail("absent parent rows are inconsistent")
    elif parent_state == "indeterminate":
        if parent_reasons[0] not in _PARENT_INDETERMINATE_REASONS:
            _fail("indeterminate parent reason is invalid")
        if any(
            row.observation_state != "indeterminate"
            or row.reason_codes != parent_reasons
            for row in rows
        ):
            _fail("indeterminate parent rows are inconsistent")
    else:
        _fail("parent_namespace_state is invalid")

    states = tuple(row.observation_state for row in rows)
    if type(value.state_vector) is not tuple or value.state_vector != states:
        _fail("state_vector is invalid")
    expected_counts = (
        states.count("present"),
        states.count("absent"),
        states.count("indeterminate"),
    )
    for name, expected in zip(
        ("present_count", "absent_count", "indeterminate_count"),
        expected_counts,
    ):
        if _require_exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    present_bytes = sum(
        row.artifact_bytes
        for row in rows
        if row.observation_state == "present" and row.artifact_bytes is not None
    )
    if _require_exact_int(value.total_present_bytes, "total_present_bytes") != present_bytes:
        _fail("total_present_bytes is invalid")
    for name, expected in (
        ("accepted_byte_upper_bound", total),
        ("read_work_upper_bound_bytes", work),
        ("read_call_upper_bound", calls),
        ("peak_buffer_upper_bound_bytes", peak),
    ):
        if _require_exact_int(getattr(value, name), name) != expected:
            _fail(f"{name} is invalid")
    for name in (
        "canonical_run_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        _require_false(getattr(value, name), name)


def _metadata_integer(value: object, name: str) -> int:
    try:
        item = getattr(value, name)
    except Exception:
        raise _MetadataError from None
    if type(item) is not int:
        raise _MetadataError from None
    return item


def _reparse_bit(value: object, mode: int) -> bool:
    result = stat.S_ISLNK(mode)
    try:
        attributes = getattr(value, "st_file_attributes")
    except AttributeError:
        attributes = _MISSING
    except Exception:
        raise _MetadataError from None
    if attributes is not _MISSING:
        if type(attributes) is not int:
            raise _MetadataError from None
        result = result or bool(
            attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
    return bool(result)


def _directory_snapshot(value: object) -> tuple[int, int, int, bool]:
    mode = _metadata_integer(value, "st_mode")
    return (
        _metadata_integer(value, "st_dev"),
        _metadata_integer(value, "st_ino"),
        mode,
        _reparse_bit(value, mode),
    )


def _path_snapshot(value: object) -> tuple[int, int, int, bool, int, int, int]:
    mode = _metadata_integer(value, "st_mode")
    return (
        _metadata_integer(value, "st_dev"),
        _metadata_integer(value, "st_ino"),
        mode,
        _reparse_bit(value, mode),
        _metadata_integer(value, "st_ctime_ns"),
        _metadata_integer(value, "st_size"),
        _metadata_integer(value, "st_mtime_ns"),
    )


def _descriptor_snapshot(value: object) -> tuple[int, int, int, int, int, int]:
    return (
        _metadata_integer(value, "st_dev"),
        _metadata_integer(value, "st_ino"),
        _metadata_integer(value, "st_mode"),
        _metadata_integer(value, "st_ctime_ns"),
        _metadata_integer(value, "st_size"),
        _metadata_integer(value, "st_mtime_ns"),
    )


def _path_binding(value: tuple[int, int, int, bool, int, int, int]) -> tuple[int, int, int, int]:
    return (value[0], value[1], value[5], value[6])


def _descriptor_binding(value: tuple[int, int, int, int, int, int]) -> tuple[int, int, int, int]:
    return (value[0], value[1], value[4], value[5])


def _row_record(
    kind_index: int,
    repository_path: str,
    state: str,
    reasons: tuple[str, ...],
    *,
    digest: str | None = None,
    count: int | None = None,
) -> LocalArtifactObservationV10:
    limits, _total, _work, _calls, _peak = _resource_bounds()
    return LocalArtifactObservationV10(
        artifact_kind=_KINDS[kind_index],
        repository_path=repository_path,
        observation_state=state,
        reason_codes=reasons,
        artifact_sha256=digest,
        artifact_bytes=count,
        byte_limit=limits[kind_index],
        content_validation="not_performed",
        authority_scope="none",
        licenses_execution=False,
        licenses_publication=False,
        licenses_recovery=False,
        licenses_later_stage=False,
    )


def _parent_rows(
    repository_paths: tuple[str, str, str],
    state: str,
    reason: str,
) -> tuple[LocalArtifactObservationV10, LocalArtifactObservationV10, LocalArtifactObservationV10]:
    return (
        _row_record(0, repository_paths[0], state, (reason,)),
        _row_record(1, repository_paths[1], state, (reason,)),
        _row_record(2, repository_paths[2], state, (reason,)),
    )


def _read_pass(fd: int, expected_size: int) -> tuple[str | None, str | None, int | None]:
    try:
        position = _os_lseek(fd, 0, os.SEEK_SET)
    except _FILESYSTEM_ERRORS:
        return ("seek_error", None, None)
    if type(position) is not int or position != 0:
        return ("seek_error", None, None)
    hasher = hashlib.sha256()
    total = 0
    while total < expected_size:
        request_size = min(_READ_CHUNK_BYTES, expected_size - total)
        try:
            chunk = _os_read(fd, request_size)
        except _FILESYSTEM_ERRORS:
            return ("read_error", None, None)
        if type(chunk) is not bytes:
            del chunk
            return ("read_error", None, None)
        length = len(chunk)
        if length > request_size:
            del chunk
            return ("read_error", None, None)
        if length < request_size:
            del chunk
            return ("early_eof", None, None)
        hasher.update(chunk)
        total += length
        del chunk
    try:
        probe = _os_read(fd, 1)
    except _FILESYSTEM_ERRORS:
        return ("read_error", None, None)
    if type(probe) is not bytes:
        del probe
        return ("read_error", None, None)
    probe_length = len(probe)
    del probe
    if probe_length > 1:
        return ("read_error", None, None)
    if probe_length == 1:
        return ("growth", None, None)
    return (None, hasher.hexdigest().upper(), total)


def _checked_fstat(fd: int) -> tuple[int, int, int, int, int, int] | None:
    try:
        observed = _os_fstat(fd)
        snapshot = _descriptor_snapshot(observed)
    except (_MetadataError,) + _FILESYSTEM_ERRORS:
        return None
    if not stat.S_ISREG(snapshot[2]):
        return None
    return snapshot


def _descriptor_body(
    fd: int,
    snapshot0: tuple[int, int, int, bool, int, int, int],
) -> tuple[str | None, str | None, int | None]:
    f0 = _checked_fstat(fd)
    if f0 is None:
        return ("fstat_error", None, None)
    if _path_binding(snapshot0) != _descriptor_binding(f0):
        return ("path_descriptor_mismatch", None, None)
    reason, first_digest, first_count = _read_pass(fd, snapshot0[5])
    if reason is not None:
        return (reason, None, None)
    f1 = _checked_fstat(fd)
    if f1 is None:
        return ("fstat_error", None, None)
    if f1 != f0:
        return ("descriptor_drift", None, None)
    reason, second_digest, second_count = _read_pass(fd, snapshot0[5])
    if reason is not None:
        return (reason, None, None)
    f2 = _checked_fstat(fd)
    if f2 is None:
        return ("fstat_error", None, None)
    if f2 != f0:
        return ("descriptor_drift", None, None)
    if first_count != second_count or first_digest != second_digest:
        return ("content_drift", None, None)
    if first_digest is None or first_count is None:
        _fail("descriptor observation produced no digest")
    return (None, first_digest, first_count)


def _observe_artifact(
    kind_index: int,
    host_path: str,
    repository_path: str,
) -> LocalArtifactObservationV10:
    limits, _total, _work, _calls, _peak = _resource_bounds()
    try:
        initial = _os_stat(host_path, follow_symlinks=False)
    except FileNotFoundError:
        try:
            _os_stat(host_path, follow_symlinks=False)
        except FileNotFoundError:
            return _row_record(
                kind_index,
                repository_path,
                "absent",
                (_DIRECT_ABSENT_REASON,),
            )
        except _FILESYSTEM_ERRORS:
            return _row_record(
                kind_index,
                repository_path,
                "indeterminate",
                ("absence_recheck_error",),
            )
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("absence_changed",),
        )
    except _FILESYSTEM_ERRORS:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("initial_stat_error",),
        )
    try:
        snapshot0 = _path_snapshot(initial)
    except _MetadataError:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("metadata_invalid",),
        )
    if snapshot0[3]:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("reparse_entry",),
        )
    if not stat.S_ISREG(snapshot0[2]):
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("nonregular_entry",),
        )
    if not 0 <= snapshot0[5] <= limits[kind_index]:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("size_limit",),
        )

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = _os_open(host_path, flags)
    except _FILESYSTEM_ERRORS:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("open_error",),
        )
    if type(fd) is not int or fd < 0:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("open_error",),
        )

    try:
        reason, digest, count = _descriptor_body(fd, snapshot0)
    except BaseException:
        try:
            _os_close(fd)
        except BaseException:
            pass
        raise
    try:
        close_result = _os_close(fd)
        close_failed = close_result is not None
    except _FILESYSTEM_ERRORS:
        close_failed = True
    if close_failed:
        reasons = ("close_error",) if reason is None else (reason, "close_error")
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            reasons,
        )
    if reason is not None:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            (reason,),
        )

    try:
        final = _os_stat(host_path, follow_symlinks=False)
    except _FILESYSTEM_ERRORS:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("final_stat_error",),
        )
    try:
        snapshot1 = _path_snapshot(final)
    except _MetadataError:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("final_entry_invalid",),
        )
    if snapshot1[3] or not stat.S_ISREG(snapshot1[2]):
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("final_entry_invalid",),
        )
    if snapshot1 != snapshot0:
        return _row_record(
            kind_index,
            repository_path,
            "indeterminate",
            ("path_drift",),
        )
    if digest is None or count is None:
        _fail("successful descriptor observation lost its digest")
    return _row_record(
        kind_index,
        repository_path,
        "present",
        (_PRESENT_REASON,),
        digest=digest,
        count=count,
    )


def _set_record(
    receipt: PublicClaimReceiptV10,
    receipt_digest: str,
    anchor: str,
    parent_state: str,
    parent_reason: str,
    rows: tuple[
        LocalArtifactObservationV10,
        LocalArtifactObservationV10,
        LocalArtifactObservationV10,
    ],
) -> LocalArtifactSetObservationV10:
    _limits, total, work, calls, peak = _resource_bounds()
    states = tuple(row.observation_state for row in rows)
    present_bytes = sum(
        row.artifact_bytes
        for row in rows
        if row.observation_state == "present" and row.artifact_bytes is not None
    )
    return LocalArtifactSetObservationV10(
        observer_schema_version=_OBSERVER_SCHEMA,
        observer_scope=_OBSERVER_SCOPE,
        origin_status=_ORIGIN_STATUS,
        selector_scope=_SELECTOR_SCOPE,
        claim_receipt=receipt,
        claim_receipt_sha256=receipt_digest,
        anchor=anchor,
        registered_run_dir=_REGISTERED_RUN_DIR,
        parent_namespace_state=parent_state,
        parent_reason_codes=(parent_reason,),
        reservation=rows[0],
        ledger=rows[1],
        report=rows[2],
        state_vector=states,
        present_count=states.count("present"),
        absent_count=states.count("absent"),
        indeterminate_count=states.count("indeterminate"),
        total_present_bytes=present_bytes,
        accepted_byte_upper_bound=total,
        read_work_upper_bound_bytes=work,
        read_call_upper_bound=calls,
        peak_buffer_upper_bound_bytes=peak,
        hash_algorithm="SHA-256",
        snapshot_scope="sequential_per_artifact_not_atomic_bundle",
        root_scope="one_caller_supplied_unauthenticated_prefix",
        selector_binding="caller_supplied_receipt_to_paths_only",
        basename_spelling_verification="not_performed",
        hostile_concurrent_reparse_prevention="not_provided",
        ancestor_link_containment="not_authenticated",
        reservation_validation="not_performed",
        ledger_validation="not_performed",
        report_validation="not_performed",
        cross_artifact_binding="not_performed",
        manifest_binding="not_performed",
        inventory_binding="not_performed",
        anchor_uniqueness="not_performed",
        artifact_claim_binding="not_performed",
        durability_observation="not_performed",
        cas_observation="not_performed",
        publication_observation="not_performed",
        recovery_observation="not_performed",
        witness_observation="not_performed",
        remote_claim_authentication="not_performed",
        git_object_authentication="not_performed",
        authority_scope="none",
        canonical_run_authority=False,
        licenses_execution=False,
        licenses_publication=False,
        licenses_recovery=False,
        licenses_later_stage=False,
    )


def observe_local_rpc_artifact_set_v1_0(
    root: str,
    claim_receipt: PublicClaimReceiptV10,
    /,
) -> LocalArtifactSetObservationV10:
    """Observe three receipt-derived raw artifacts without parsing or writing."""

    _resource_bounds()
    receipt = _reconstruct_receipt(claim_receipt)
    receipt_digest = _receipt_digest(receipt)
    if type(root) is not str or not root:
        _fail("root must be an exact nonempty string")
    try:
        absolute = _os_path_isabs(root)
    except _FILESYSTEM_ERRORS:
        _fail("root absolute-path check failed")
    if absolute is not True:
        _fail("root must be lexically absolute")
    anchor = receipt.license_commit[:12]
    repository_paths = _repository_paths(anchor)
    parent_path = _join_path(root, "runs", "uprime_u1_rpc_20260710")

    try:
        parent_initial = _os_stat(parent_path, follow_symlinks=False)
    except FileNotFoundError:
        try:
            _os_stat(parent_path, follow_symlinks=False)
        except FileNotFoundError:
            rows = _parent_rows(repository_paths, "absent", _PARENT_ABSENT_REASON)
            return _set_record(
                receipt,
                receipt_digest,
                anchor,
                "absent",
                _PARENT_ABSENT_REASON,
                rows,
            )
        except _FILESYSTEM_ERRORS:
            reason = "parent_absence_recheck_error"
        else:
            reason = "parent_absence_changed"
        rows = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, rows
        )
    except _FILESYSTEM_ERRORS:
        reason = "parent_initial_stat_error"
        rows = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, rows
        )

    try:
        directory0 = _directory_snapshot(parent_initial)
    except _MetadataError:
        reason = "parent_metadata_invalid"
        rows = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, rows
        )
    if directory0[3]:
        reason = "parent_reparse_entry"
        rows = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, rows
        )
    if not stat.S_ISDIR(directory0[2]):
        reason = "parent_nondirectory"
        rows = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, rows
        )

    observed_rows: list[LocalArtifactObservationV10] = []
    for index, repository_path in enumerate(repository_paths):
        host_path = _join_path(root, *repository_path.split("/"))
        observed_rows.append(_observe_artifact(index, host_path, repository_path))
    rows = (observed_rows[0], observed_rows[1], observed_rows[2])

    try:
        parent_final = _os_stat(parent_path, follow_symlinks=False)
    except _FILESYSTEM_ERRORS:
        reason = "parent_final_stat_error"
        cleared = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, cleared
        )
    try:
        directory1 = _directory_snapshot(parent_final)
    except _MetadataError:
        reason = "parent_final_entry_invalid"
        cleared = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, cleared
        )
    if directory1[3] or not stat.S_ISDIR(directory1[2]):
        reason = "parent_final_entry_invalid"
        cleared = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, cleared
        )
    if directory1 != directory0:
        reason = "parent_drift"
        cleared = _parent_rows(repository_paths, "indeterminate", reason)
        return _set_record(
            receipt, receipt_digest, anchor, "indeterminate", reason, cleared
        )
    return _set_record(
        receipt,
        receipt_digest,
        anchor,
        "present",
        _PARENT_PRESENT_REASON,
        rows,
    )


__all__ = [
    "LocalArtifactObservationV10Error",
    "LocalArtifactObservationV10",
    "LocalArtifactSetObservationV10",
    "observe_local_rpc_artifact_set_v1_0",
]
