"""Read-only Phase-2b1 parser for synthetic local attempt manifests.

This module validates exact event bytes and a bounded local chain snapshot.  It
does not authenticate origin, observe sibling artifacts, contact a remote, or
grant execution, publication, or later-stage authority.
"""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_ledger import (
    canonical_json_bytes,
    parse_canonical_json_bytes,
)


_RECEIPT_SCHEMA = "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
_EVENT_SCHEMA = "lean-rgc-uprime-u1-attempt-manifest-v1.0"
_INSPECTOR_SCHEMA = "lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1"
_VERIFIER_SCHEMA = "lean-rgc-uprime-u1-local-attempt-chain-verifier-v0.1"
_LOCAL_SCOPE = "local_preartifact_chain_structure_only"
_ORIGIN_STATUS = "unknown_may_be_synthetic"

_REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
_REMOTE_BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"
_CLAIM_REF_PREFIX = "refs/tags/uprime-u1-attempts/"
_LICENSE_DOMAIN = b"lean-rgc-uprime-u1-attempt-v1\0"

_MAX_EVENT_BYTES = 1_048_576
_MAX_EVENT_COUNT = 9_999
_MAX_CHAIN_BYTES = 67_108_864

_HEX40_LOWER_RE = re.compile(r"[0-9a-f]{40}\Z", flags=re.ASCII)
_HEX64_LOWER_RE = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)
_HEX64_UPPER_RE = re.compile(r"[0-9A-F]{64}\Z", flags=re.ASCII)
_UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z",
    flags=re.ASCII,
)
_ENTRY_NAME_RE = re.compile(r"([0-9]{4})\.json\Z", flags=re.ASCII)
_REPOSITORY_PATH_RE = re.compile(
    r"docs/experiments/artifacts/uprime_u1_rpc_attempts/"
    r"([0-9a-f]{64})/([0-9]{4})\.json\Z",
    flags=re.ASCII,
)

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
_EVENT_FIELD_NAMES = (
    "schema_version",
    "event_type",
    "event_index",
    "created_at_utc",
    "license_id",
    "candidate_commit",
    "license_commit",
    "remote_claim_ref",
    "claim_receipt",
    "claim_receipt_sha256",
    "prior_event_sha256",
    "reservation_exists",
    "ledger_exists",
    "report_exists",
    "reservation_sha256",
    "reservation_bytes",
    "ledger_sha256",
    "ledger_bytes",
    "report_sha256",
    "report_bytes",
    "ledger_inspection_status",
    "ledger_sequence_status",
    "verifier_status",
    "scanner_status",
    "scanner_rule_ids",
    "verdict",
    "failure_codes",
    "full_ledger_published",
    "terminal_event",
)
_RECEIPT_KEYS = tuple(sorted(_RECEIPT_FIELD_NAMES))
_EVENT_KEYS = tuple(sorted(_EVENT_FIELD_NAMES))

_FAILURE_CODES = frozenset(
    (
        "ARCHIVE_ERROR",
        "CLAIM_STARTED_MANIFEST_ERROR",
        "CLEANUP_ERROR",
        "EOF_BEFORE_EXPECTED_RESPONSE",
        "FINAL_MANIFEST_ERROR",
        "INVALID_UTF8_STDOUT",
        "LEDGER_APPEND_ERROR",
        "LEDGER_CLOSURE_ERROR",
        "LEDGER_FSYNC_ERROR",
        "LEDGER_OPEN_ERROR",
        "LEDGER_VERIFY_ERROR",
        "NON_JSON_STDOUT",
        "NON_OBJECT_STDOUT",
        "OTHER_ATTEMPT_ERROR",
        "OTHER_HARNESS_ERROR",
        "POWER_LOSS",
        "PRIVACY_DENIED",
        "PROCESS_EXIT_BEFORE_REQUEST",
        "PUBLICATION_ERROR",
        "READER_ERROR",
        "READER_NOT_QUIESCED",
        "REPORT_FSYNC_ERROR",
        "REPORT_HARDLINK_ERROR",
        "REPORT_REVALIDATION_ERROR",
        "REPORT_TEMP_CREATE_ERROR",
        "REPORT_WRITE_ERROR",
        "REQUEST_TIMEOUT",
        "REQUEST_VALIDATION_ERROR",
        "REQUEST_WRITE_ERROR",
        "RESERVATION_CREATE_ERROR",
        "RESERVATION_FSYNC_ERROR",
        "RESERVATION_WRITE_ERROR",
        "RESPONSE_DUPLICATE",
        "RESPONSE_LATE",
        "RESPONSE_UNSOLICITED",
        "SCANNER_ERROR",
        "SHUTDOWN_FINALIZATION_ERROR",
        "STDIN_UNAVAILABLE",
        "TRANSPORT_OVERFLOW",
        "WORKER_START_ERROR",
        "WORKER_TIMEOUT",
    )
)
_PROFILE_FORBIDDEN_CODES = frozenset(
    ("SCANNER_ERROR", "PRIVACY_DENIED", "ARCHIVE_ERROR", "PUBLICATION_ERROR")
)
_RECOVERY_ONLY_CODES = frozenset(
    ("CLAIM_STARTED_MANIFEST_ERROR", "FINAL_MANIFEST_ERROR", "POWER_LOSS")
)

_REPOSITORY_COMPONENTS = (
    "docs",
    "experiments",
    "artifacts",
    "uprime_u1_rpc_attempts",
)

# These bindings make the complete local observation call table injectable
# without changing a public signature or supplying an alternate reader.
_os_fspath = os.fspath
_os_path_isabs = os.path.isabs
_os_path_join = os.path.join
_os_stat = os.stat
_os_scandir = os.scandir
_os_open = os.open
_os_fstat = os.fstat
_os_lseek = os.lseek
_os_read = os.read
_os_close = os.close


class AttemptManifestV10Error(ValueError):
    """The supplied bytes or local snapshot violate the Phase-2b1 contract."""


def _fail(message: str) -> None:
    raise AttemptManifestV10Error(message) from None


def _require_exact_str(value: object, field: str) -> str:
    if type(value) is not str:
        _fail(f"{field} must be an exact string")
    return value


def _require_exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        _fail(f"{field} must be an exact boolean")
    return value


def _require_exact_int(value: object, field: str) -> int:
    if type(value) is not int:
        _fail(f"{field} must be an exact integer")
    return value


def _require_nullable_str(value: object, field: str) -> str | None:
    if value is not None and type(value) is not str:
        _fail(f"{field} must be null or an exact string")
    return value


def _validate_utc(value: object, field: str) -> str:
    text = _require_exact_str(value, field)
    if _UTC_RE.fullmatch(text) is None:
        _fail(f"{field} is not an exact six-digit UTC timestamp")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, OverflowError):
        _fail(f"{field} is not a real UTC instant")
    return text


def _validate_lower_hex40(value: object, field: str) -> str:
    text = _require_exact_str(value, field)
    if _HEX40_LOWER_RE.fullmatch(text) is None:
        _fail(f"{field} must be 40 lowercase hexadecimal characters")
    return text


def _validate_lower_hex64(value: object, field: str) -> str:
    text = _require_exact_str(value, field)
    if _HEX64_LOWER_RE.fullmatch(text) is None:
        _fail(f"{field} must be 64 lowercase hexadecimal characters")
    return text


def _validate_upper_hex64(value: object, field: str) -> str:
    text = _require_exact_str(value, field)
    if _HEX64_UPPER_RE.fullmatch(text) is None:
        _fail(f"{field} must be 64 uppercase hexadecimal characters")
    return text


def _uppercase_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical_bytes(value: object, context: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        _fail(f"{context} cannot be encoded as strict canonical JSON")


def _parse_canonical_bytes(raw: bytes) -> object:
    try:
        return parse_canonical_json_bytes(raw)
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        _fail("event payload is not strict canonical JSON")


@dataclass(frozen=True, slots=True)
class PublicClaimReceiptV10:
    schema_version: str
    candidate_commit: str
    license_commit: str
    license_id: str
    remote_url: str
    remote_branch_ref: str
    remote_claim_ref: str
    remote_claim_oid: str
    registry_blob_oid: str
    registry_sha256: str
    candidate_tree_oid: str
    input_manifest_sha256: str
    claimed_at_utc: str

    def __post_init__(self) -> None:
        _validate_receipt(self)


@dataclass(frozen=True, slots=True)
class AttemptManifestEventV10:
    schema_version: str
    event_type: str
    event_index: int
    created_at_utc: str
    license_id: str
    candidate_commit: str
    license_commit: str
    remote_claim_ref: str
    claim_receipt: PublicClaimReceiptV10
    claim_receipt_sha256: str
    prior_event_sha256: str | None
    reservation_exists: bool
    ledger_exists: bool
    report_exists: bool
    reservation_sha256: str | None
    reservation_bytes: int | None
    ledger_sha256: str | None
    ledger_bytes: int | None
    report_sha256: str | None
    report_bytes: int | None
    ledger_inspection_status: str
    ledger_sequence_status: str | None
    verifier_status: str
    scanner_status: str
    scanner_rule_ids: tuple[str, ...]
    verdict: str | None
    failure_codes: tuple[str, ...]
    full_ledger_published: bool
    terminal_event: bool

    def __post_init__(self) -> None:
        _validate_event(self)


@dataclass(frozen=True, slots=True)
class AttemptManifestEventFileV10:
    repository_path: str
    event_sha256: str
    event_bytes: bytes
    event: AttemptManifestEventV10


@dataclass(frozen=True, slots=True)
class AttemptManifestChainInspectionV10:
    inspector_schema_version: str
    inspector_scope: str
    origin_status: str
    license_id: str
    chain_state: str
    event_files: tuple[AttemptManifestEventFileV10, ...]
    event_count: int
    first_event_sha256: str | None
    last_event_index: int | None
    last_event_sha256: str | None
    last_event_type: str | None
    terminal_event: bool
    recorded_verdict: str | None
    next_event_index: int | None
    claim_receipt: PublicClaimReceiptV10 | None
    claim_receipt_sha256: str | None


@dataclass(frozen=True, slots=True)
class AttemptManifestChainAttestationV10:
    verifier_schema_version: str
    verifier_scope: str
    origin_status: str
    license_id: str
    candidate_commit: str
    license_commit: str
    remote_claim_ref: str
    claim_receipt_sha256: str
    event_count: int
    first_event_sha256: str
    last_event_index: int
    last_event_sha256: str
    chain_state: str
    terminal_event: bool
    last_event_type: str
    recorded_verdict: str | None
    failure_codes: tuple[str, ...]
    preartifact_profile: bool
    artifact_observation: str
    remote_claim_authentication: str
    git_object_authentication: str
    real_remote_publication: str
    claim_once_authentication: str
    reservation_token_verification: str
    artifact_binding: str
    verifier_binding: str
    scanner_binding: str
    privacy_scan: str
    archive_verification: str
    authority_scope: str
    canonical_run_authority: bool
    licenses_execution: bool
    licenses_later_stage: bool


def _receipt_mapping(receipt: PublicClaimReceiptV10) -> dict[str, object]:
    _validate_receipt(receipt)
    return {name: getattr(receipt, name) for name in _RECEIPT_FIELD_NAMES}


def _receipt_bytes(receipt: PublicClaimReceiptV10) -> bytes:
    return _canonical_bytes(_receipt_mapping(receipt), "claim receipt")


def _validate_receipt(receipt: object) -> None:
    if type(receipt) is not PublicClaimReceiptV10:
        _fail("claim_receipt has the wrong record type")
    if _require_exact_str(receipt.schema_version, "receipt schema_version") != _RECEIPT_SCHEMA:
        _fail("receipt schema_version is invalid")
    candidate_commit = _validate_lower_hex40(
        receipt.candidate_commit, "receipt candidate_commit"
    )
    license_commit = _validate_lower_hex40(
        receipt.license_commit, "receipt license_commit"
    )
    license_id = _validate_lower_hex64(receipt.license_id, "receipt license_id")
    expected_license = hashlib.sha256(
        _LICENSE_DOMAIN + candidate_commit.encode("ascii")
    ).hexdigest()
    if license_id != expected_license:
        _fail("receipt license_id does not match candidate_commit")
    if _require_exact_str(receipt.remote_url, "receipt remote_url") != _REMOTE_URL:
        _fail("receipt remote_url is invalid")
    if (
        _require_exact_str(receipt.remote_branch_ref, "receipt remote_branch_ref")
        != _REMOTE_BRANCH_REF
    ):
        _fail("receipt remote_branch_ref is invalid")
    expected_ref = _CLAIM_REF_PREFIX + license_id
    if _require_exact_str(receipt.remote_claim_ref, "receipt remote_claim_ref") != expected_ref:
        _fail("receipt remote_claim_ref is invalid")
    remote_claim_oid = _validate_lower_hex40(
        receipt.remote_claim_oid, "receipt remote_claim_oid"
    )
    if remote_claim_oid != license_commit:
        _fail("receipt remote_claim_oid does not equal license_commit")
    _validate_lower_hex40(receipt.registry_blob_oid, "receipt registry_blob_oid")
    _validate_upper_hex64(receipt.registry_sha256, "receipt registry_sha256")
    _validate_lower_hex40(receipt.candidate_tree_oid, "receipt candidate_tree_oid")
    _validate_upper_hex64(
        receipt.input_manifest_sha256, "receipt input_manifest_sha256"
    )
    _validate_utc(receipt.claimed_at_utc, "receipt claimed_at_utc")


def _validate_failure_codes(codes: object) -> tuple[str, ...]:
    if type(codes) is not tuple:
        _fail("failure_codes must be an exact tuple")
    for code in codes:
        if type(code) is not str or code not in _FAILURE_CODES:
            _fail("failure_codes contains an unknown or non-string code")
    if tuple(sorted(codes)) != codes or len(set(codes)) != len(codes):
        _fail("failure_codes must be ASCII-sorted and unique")
    if _PROFILE_FORBIDDEN_CODES.intersection(codes):
        _fail("failure_codes conflicts with the pre-artifact profile")
    return codes


def _validate_event(event: object) -> None:
    if type(event) is not AttemptManifestEventV10:
        _fail("event has the wrong record type")
    if _require_exact_str(event.schema_version, "event schema_version") != _EVENT_SCHEMA:
        _fail("event schema_version is invalid")
    event_type = _require_exact_str(event.event_type, "event_type")
    if event_type not in ("claim_started", "attempt_finished", "recovery"):
        _fail("event_type is invalid")
    event_index = _require_exact_int(event.event_index, "event_index")
    if not 1 <= event_index <= 9_999:
        _fail("event_index is outside the literal 1..9999 domain")
    _validate_utc(event.created_at_utc, "created_at_utc")

    _validate_receipt(event.claim_receipt)
    receipt = event.claim_receipt
    license_id = _validate_lower_hex64(event.license_id, "event license_id")
    candidate_commit = _validate_lower_hex40(
        event.candidate_commit, "event candidate_commit"
    )
    license_commit = _validate_lower_hex40(event.license_commit, "event license_commit")
    remote_claim_ref = _require_exact_str(event.remote_claim_ref, "event remote_claim_ref")
    if (
        license_id != receipt.license_id
        or candidate_commit != receipt.candidate_commit
        or license_commit != receipt.license_commit
        or remote_claim_ref != receipt.remote_claim_ref
    ):
        _fail("event identity does not exactly repeat its claim receipt")
    receipt_digest = _validate_upper_hex64(
        event.claim_receipt_sha256, "claim_receipt_sha256"
    )
    if receipt_digest != _uppercase_sha256(_receipt_bytes(receipt)):
        _fail("claim_receipt_sha256 is invalid")

    if event_index == 1:
        if event.prior_event_sha256 is not None:
            _fail("prior_event_sha256 must be null at index 1")
    else:
        _validate_upper_hex64(event.prior_event_sha256, "prior_event_sha256")

    for field in ("reservation_exists", "ledger_exists", "report_exists"):
        if _require_exact_bool(getattr(event, field), field):
            _fail(f"{field} must be false in the pre-artifact profile")
    for field in (
        "reservation_sha256",
        "reservation_bytes",
        "ledger_sha256",
        "ledger_bytes",
        "report_sha256",
        "report_bytes",
    ):
        if getattr(event, field) is not None:
            _fail(f"{field} must be null in the pre-artifact profile")
    if (
        _require_exact_str(event.ledger_inspection_status, "ledger_inspection_status")
        != "absent"
    ):
        _fail("ledger_inspection_status must be absent")
    if event.ledger_sequence_status is not None:
        _fail("ledger_sequence_status must be null")
    if _require_exact_str(event.verifier_status, "verifier_status") != "not_run":
        _fail("verifier_status must be not_run")
    if _require_exact_str(event.scanner_status, "scanner_status") != "not_run":
        _fail("scanner_status must be not_run")
    if type(event.scanner_rule_ids) is not tuple:
        _fail("scanner_rule_ids must be an exact tuple")
    if event.scanner_rule_ids:
        _fail("scanner_rule_ids must be empty")
    if event.verdict is not None and type(event.verdict) is not str:
        _fail("verdict must be null or an exact string")
    codes = _validate_failure_codes(event.failure_codes)
    if _require_exact_bool(event.full_ledger_published, "full_ledger_published"):
        _fail("full_ledger_published must be false")
    terminal = _require_exact_bool(event.terminal_event, "terminal_event")

    if event_type == "claim_started":
        if event_index != 1 or terminal or event.verdict is not None or codes:
            _fail("claim_started fields are invalid")
    elif event_type == "recovery":
        if not codes or event.verdict is not None:
            _fail("recovery fields are invalid")
    else:
        if not terminal or event.verdict != "HARNESS_ERROR" or not codes:
            _fail("attempt_finished fields are invalid")
        if _RECOVERY_ONLY_CODES.intersection(codes):
            _fail("attempt_finished contains a recovery-only failure code")

    if event_type != "recovery" and _RECOVERY_ONLY_CODES.intersection(codes):
        _fail("recovery-only failure code occurs outside recovery")


def _event_mapping(event: AttemptManifestEventV10) -> dict[str, object]:
    _validate_event(event)
    result: dict[str, object] = {}
    for name in _EVENT_FIELD_NAMES:
        value = getattr(event, name)
        if name == "claim_receipt":
            value = _receipt_mapping(event.claim_receipt)
        elif name in ("scanner_rule_ids", "failure_codes"):
            value = list(value)
        result[name] = value
    return result


def _require_exact_keys(value: object, expected: tuple[str, ...], context: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"{context} must be an exact JSON object")
    if tuple(sorted(value.keys())) != expected:
        _fail(f"{context} has missing or extra fields")
    return value


def _receipt_from_mapping(value: object) -> PublicClaimReceiptV10:
    mapping = _require_exact_keys(value, _RECEIPT_KEYS, "claim_receipt")
    return PublicClaimReceiptV10(**{name: mapping[name] for name in _RECEIPT_FIELD_NAMES})


def _event_from_mapping(value: object) -> AttemptManifestEventV10:
    mapping = _require_exact_keys(value, _EVENT_KEYS, "event")
    scanner_rule_ids = mapping["scanner_rule_ids"]
    failure_codes = mapping["failure_codes"]
    if type(scanner_rule_ids) is not list:
        _fail("scanner_rule_ids wire value must be an array")
    if type(failure_codes) is not list:
        _fail("failure_codes wire value must be an array")
    fields = {name: mapping[name] for name in _EVENT_FIELD_NAMES}
    fields["claim_receipt"] = _receipt_from_mapping(mapping["claim_receipt"])
    fields["scanner_rule_ids"] = tuple(scanner_rule_ids)
    fields["failure_codes"] = tuple(failure_codes)
    return AttemptManifestEventV10(**fields)


def _event_byte_limit() -> int:
    if type(_MAX_EVENT_BYTES) is not int or _MAX_EVENT_BYTES < 1:
        _fail("event byte bound is invalid")
    return _MAX_EVENT_BYTES


def encode_attempt_manifest_event_v1_0(
    event: AttemptManifestEventV10, /
) -> bytes:
    """Encode one validated event as exact canonical JSON plus one LF."""

    payload = _canonical_bytes(_event_mapping(event), "attempt manifest event")
    result = payload + b"\n"
    if len(result) > _event_byte_limit():
        _fail("event bytes exceed the inclusive byte limit")
    return result


def parse_attempt_manifest_event_file_v1_0(
    repository_path: str, raw: bytes, /
) -> AttemptManifestEventFileV10:
    """Parse one exact repository-relative event file without I/O."""

    path = _require_exact_str(repository_path, "repository_path")
    match = _REPOSITORY_PATH_RE.fullmatch(path)
    if match is None:
        _fail("repository_path is outside the exact attempt-manifest namespace")
    path_license_id, index_text = match.groups()
    event_index = int(index_text, 10)
    if not 1 <= event_index <= 9_999:
        _fail("repository_path index is outside 1..9999")
    if type(raw) is not bytes:
        _fail("raw must have exact type bytes")
    if not 1 <= len(raw) <= _event_byte_limit():
        _fail("event file size is outside the inclusive byte limit")
    if raw[-1:] != b"\n" or b"\n" in raw[:-1]:
        _fail("event bytes must contain exactly one final LF")
    value = _parse_canonical_bytes(raw[:-1])
    event = _event_from_mapping(value)
    if event.license_id != path_license_id or event.event_index != event_index:
        _fail("repository_path identity or index does not match the event")
    if encode_attempt_manifest_event_v1_0(event) != raw:
        _fail("event bytes do not round-trip byte-identically")
    return AttemptManifestEventFileV10(
        repository_path=path,
        event_sha256=_uppercase_sha256(raw),
        event_bytes=raw,
        event=event,
    )


def _stat_integer(value: os.stat_result, name: str) -> int:
    try:
        item = getattr(value, name)
    except (AttributeError, TypeError, ValueError):
        _fail(f"filesystem metadata lacks {name}")
    if type(item) is not int:
        _fail(f"filesystem metadata {name} is not an exact integer")
    return item


def _reparse_bit(value: os.stat_result) -> bool:
    mode = _stat_integer(value, "st_mode")
    result = stat.S_ISLNK(mode)
    if hasattr(value, "st_file_attributes") and hasattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT"
    ):
        attributes = _stat_integer(value, "st_file_attributes")
        result = result or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return bool(result)


def _directory_snapshot(value: os.stat_result) -> tuple[int, int, int, bool, int, int]:
    return (
        _stat_integer(value, "st_dev"),
        _stat_integer(value, "st_ino"),
        _stat_integer(value, "st_mode"),
        _reparse_bit(value),
        _stat_integer(value, "st_ctime_ns"),
        _stat_integer(value, "st_mtime_ns"),
    )


def _path_snapshot(
    value: os.stat_result,
) -> tuple[int, int, int, bool, int, int, int]:
    return (
        _stat_integer(value, "st_dev"),
        _stat_integer(value, "st_ino"),
        _stat_integer(value, "st_mode"),
        _reparse_bit(value),
        _stat_integer(value, "st_ctime_ns"),
        _stat_integer(value, "st_size"),
        _stat_integer(value, "st_mtime_ns"),
    )


def _descriptor_snapshot(
    value: os.stat_result,
) -> tuple[int, int, int, int, int, int]:
    return (
        _stat_integer(value, "st_dev"),
        _stat_integer(value, "st_ino"),
        _stat_integer(value, "st_mode"),
        _stat_integer(value, "st_ctime_ns"),
        _stat_integer(value, "st_size"),
        _stat_integer(value, "st_mtime_ns"),
    )


def _path_binding(
    value: tuple[int, int, int, bool, int, int, int],
) -> tuple[int, int, int, int]:
    return (value[0], value[1], value[5], value[6])


def _descriptor_binding(
    value: tuple[int, int, int, int, int, int],
) -> tuple[int, int, int, int]:
    return (value[0], value[1], value[4], value[5])


def _nofollow_stat(path: str, context: str) -> os.stat_result:
    try:
        return _os_stat(path, follow_symlinks=False)
    except (OSError, TypeError, ValueError):
        _fail(f"{context} no-follow stat failed")


def _descriptor_stat(fd: int, context: str) -> os.stat_result:
    try:
        return _os_fstat(fd)
    except (OSError, TypeError, ValueError):
        _fail(f"{context} descriptor stat failed")


def _read_bounded_pass(fd: int, expected_size: int) -> bytes:
    """Read one exact-size pass from offset zero and perform one EOF probe."""

    size = _require_exact_int(expected_size, "expected_size")
    if size < 0 or size > _event_byte_limit():
        _fail("expected_size is outside the event byte bound")
    try:
        _os_lseek(fd, 0, os.SEEK_SET)
    except (OSError, TypeError, ValueError):
        _fail("event descriptor seek failed")
    chunks: list[bytes] = []
    total = 0
    while total < size:
        request_size = min(65_536, size - total)
        try:
            chunk = _os_read(fd, request_size)
        except (OSError, TypeError, ValueError):
            _fail("event descriptor read failed")
        if type(chunk) is not bytes:
            _fail("event descriptor read did not return exact bytes")
        if not chunk:
            _fail("event descriptor reached EOF before its declared size")
        if len(chunk) > size - total:
            _fail("event descriptor grew beyond its declared size")
        chunks.append(chunk)
        total += len(chunk)
    try:
        extra = _os_read(fd, 1)
    except (OSError, TypeError, ValueError):
        _fail("event descriptor EOF probe failed")
    if type(extra) is not bytes:
        _fail("event descriptor EOF probe did not return exact bytes")
    if extra:
        _fail("event descriptor grew beyond its declared size")
    return b"".join(chunks)


def _resource_bounds() -> tuple[int, int, int]:
    for value, name in (
        (_MAX_EVENT_BYTES, "event byte"),
        (_MAX_EVENT_COUNT, "event count"),
        (_MAX_CHAIN_BYTES, "chain byte"),
    ):
        if type(value) is not int or value < 0:
            _fail(f"{name} bound is invalid")
    if _MAX_EVENT_BYTES < 1:
        _fail("event byte bound is invalid")
    return (_MAX_EVENT_BYTES, _MAX_EVENT_COUNT, _MAX_CHAIN_BYTES)


def _scan_once(
    directory: str,
) -> tuple[tuple[str, ...], tuple[tuple[int, int, int, bool, int, int, int], ...]]:
    _, max_count, max_chain_bytes = _resource_bounds()
    iterator = None
    entries: list[object] = []
    pending_error: AttemptManifestV10Error | None = None
    try:
        iterator = _os_scandir(directory)
        for entry in iterator:
            entries.append(entry)
            if len(entries) > max_count:
                pending_error = AttemptManifestV10Error(
                    "attempt directory exceeds the event-count bound"
                )
                break
    except AttemptManifestV10Error as exc:
        pending_error = exc
    except (OSError, TypeError, ValueError) as exc:
        pending_error = AttemptManifestV10Error("attempt directory scan failed")
    if iterator is not None:
        close = getattr(iterator, "close", None)
        if close is not None:
            try:
                close()
            except (OSError, TypeError, ValueError):
                _fail("attempt directory scan close failed")
    if pending_error is not None:
        raise pending_error from None

    named_entries: list[tuple[str, object]] = []
    for entry in entries:
        try:
            name = entry.name
        except (AttributeError, TypeError, ValueError):
            _fail("attempt directory entry has no valid name")
        if type(name) is not str or _ENTRY_NAME_RE.fullmatch(name) is None:
            _fail("attempt directory contains an unexpected entry")
        index = int(name[:4], 10)
        if not 1 <= index <= 9_999:
            _fail("attempt directory filename index is outside 1..9999")
        named_entries.append((name, entry))
    names = [item[0] for item in named_entries]
    if len(set(names)) != len(names):
        _fail("attempt directory scan contains duplicate names")
    named_entries.sort(key=lambda item: item[0])
    names = [item[0] for item in named_entries]

    snapshots: list[tuple[int, int, int, bool, int, int, int]] = []
    aggregate = 0
    for name, entry in named_entries:
        # Windows DirEntry.stat can report zero device/inode values even when
        # os.stat(path) and os.fstat(fd) expose the matching file identity.
        # S is therefore the frozen full-path, no-follow path observation.
        path = _os_path_join(directory, name)
        observed = _nofollow_stat(path, "attempt event entry")
        snapshot = _path_snapshot(observed)
        if snapshot[3] or not stat.S_ISREG(snapshot[2]):
            _fail("attempt directory entry is not a real non-reparse regular file")
        size = snapshot[5]
        if not 1 <= size <= _MAX_EVENT_BYTES:
            _fail("attempt event entry size is outside the byte bound")
        aggregate += size
        if aggregate > max_chain_bytes:
            _fail("attempt directory exceeds the aggregate byte bound")
        snapshots.append(snapshot)
    return (tuple(names), tuple(snapshots))


def _read_stable_entry(
    path: str, snapshot0: tuple[int, int, int, bool, int, int, int]
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = _os_open(path, flags)
    except (OSError, TypeError, ValueError):
        _fail("attempt event entry open failed")

    pending_error: AttemptManifestV10Error | None = None
    first_bytes: bytes | None = None
    final_descriptor_snapshot: tuple[int, int, int, int, int, int] | None = None
    try:
        f0 = _descriptor_snapshot(_descriptor_stat(fd, "initial event"))
        if not stat.S_ISREG(f0[2]):
            _fail("initial attempt event descriptor is not a regular file")
        if _path_binding(snapshot0) != _descriptor_binding(f0):
            _fail("attempt event path and descriptor identities differ")
        first_bytes = _read_bounded_pass(fd, snapshot0[5])
        f1 = _descriptor_snapshot(_descriptor_stat(fd, "post-pass-one event"))
        if not stat.S_ISREG(f1[2]):
            _fail("post-pass-one attempt event descriptor is not a regular file")
        if f1 != f0:
            _fail("attempt event descriptor metadata changed after pass one")
        second_bytes = _read_bounded_pass(fd, snapshot0[5])
        f2 = _descriptor_snapshot(_descriptor_stat(fd, "post-pass-two event"))
        if not stat.S_ISREG(f2[2]):
            _fail("post-pass-two attempt event descriptor is not a regular file")
        if f2 != f0:
            _fail("attempt event descriptor metadata changed after pass two")
        final_descriptor_snapshot = f2
        if len(first_bytes) != len(second_bytes) or len(first_bytes) != snapshot0[5]:
            _fail("attempt event pass byte counts differ")
        if _uppercase_sha256(first_bytes) != _uppercase_sha256(second_bytes):
            _fail("attempt event bytes changed between descriptor passes")
    except AttemptManifestV10Error as exc:
        pending_error = exc
    except (OSError, TypeError, ValueError) as exc:
        pending_error = AttemptManifestV10Error("attempt event descriptor observation failed")

    try:
        _os_close(fd)
    except (OSError, TypeError, ValueError):
        _fail("attempt event descriptor close failed")
    if pending_error is not None:
        raise pending_error from None
    if first_bytes is None or final_descriptor_snapshot is None:
        _fail("attempt event descriptor produced no retained bytes")

    snapshot1 = _path_snapshot(_nofollow_stat(path, "post-close attempt event entry"))
    if snapshot1[3] or not stat.S_ISREG(snapshot1[2]):
        _fail("post-close attempt event entry is not a real regular file")
    if snapshot1 != snapshot0:
        _fail("attempt event path metadata changed after close")
    if _path_binding(snapshot1) != _descriptor_binding(final_descriptor_snapshot):
        _fail("post-close event path and descriptor identities differ")
    return first_bytes


def _validate_license_input(license_id: object) -> str:
    return _validate_lower_hex64(license_id, "license_id")


def _lexical_root(root: str | os.PathLike[str]) -> str:
    try:
        value = _os_fspath(root)
    except (OSError, TypeError, ValueError):
        _fail("root is not a valid lexical filesystem prefix")
    if type(value) is not str or not value:
        _fail("root must yield an exact nonempty string")
    try:
        absolute = _os_path_isabs(value)
    except (OSError, TypeError, ValueError):
        _fail("root lexical absoluteness check failed")
    if absolute is not True:
        _fail("root must be lexically absolute")
    return value


def _classify_chain_suffix(
    event_index: int, terminal_event: bool
) -> tuple[str, int | None]:
    index = _require_exact_int(event_index, "event_index")
    if not 1 <= index <= 9_999:
        _fail("event_index is outside the literal 1..9999 domain")
    terminal = _require_exact_bool(terminal_event, "terminal_event")
    if terminal:
        return ("valid_terminal", None)
    if index == 9_999:
        return ("valid_nonterminal_index_exhausted", None)
    return ("valid_nonterminal", index + 1)


def _validate_chain(
    files: tuple[AttemptManifestEventFileV10, ...],
) -> AttemptManifestChainInspectionV10:
    first = files[0]
    receipt = first.event.claim_receipt
    receipt_sha256 = first.event.claim_receipt_sha256
    prior_file: AttemptManifestEventFileV10 | None = None
    prior_time: str | None = None
    state = "START"

    for expected_index, event_file in enumerate(files, start=1):
        event = event_file.event
        _validate_event(event)
        if event.event_index != expected_index:
            _fail("attempt manifest chain is not contiguous from index 1")
        if event.claim_receipt != receipt or event.claim_receipt_sha256 != receipt_sha256:
            _fail("attempt manifest receipt drifts within the chain")
        if (
            event.license_id != receipt.license_id
            or event.candidate_commit != receipt.candidate_commit
            or event.license_commit != receipt.license_commit
            or event.remote_claim_ref != receipt.remote_claim_ref
        ):
            _fail("attempt manifest identity drifts within the chain")
        if prior_file is None:
            if event.prior_event_sha256 is not None:
                _fail("first attempt event has a prior digest")
        elif event.prior_event_sha256 != prior_file.event_sha256:
            _fail("attempt manifest prior digest does not match exact prior bytes")
        if prior_time is not None and event.created_at_utc < prior_time:
            _fail("attempt manifest event time moves backwards")

        if state == "TERMINAL":
            _fail("an attempt manifest event follows a terminal event")
        if state == "START":
            if event.event_type == "claim_started" and not event.terminal_event:
                state = "ACTIVE"
            elif event.event_type == "recovery" and event.terminal_event:
                state = "TERMINAL"
            else:
                _fail("attempt manifest has an invalid start transition")
        elif state == "ACTIVE":
            if event.event_type == "attempt_finished" and event.terminal_event:
                state = "TERMINAL"
            elif event.event_type == "recovery" and event.terminal_event:
                state = "TERMINAL"
            elif event.event_type == "recovery" and not event.terminal_event:
                state = "RECOVERY_ONLY"
            else:
                _fail("attempt manifest has an invalid active transition")
        elif state == "RECOVERY_ONLY":
            if event.event_type != "recovery":
                _fail("attempt manifest violates recovery stickiness")
            if event.terminal_event:
                state = "TERMINAL"
        else:
            _fail("attempt manifest state machine is invalid")

        prior_file = event_file
        prior_time = event.created_at_utc

    last = files[-1]
    chain_state, next_index = _classify_chain_suffix(
        last.event.event_index, last.event.terminal_event
    )
    return AttemptManifestChainInspectionV10(
        inspector_schema_version=_INSPECTOR_SCHEMA,
        inspector_scope=_LOCAL_SCOPE,
        origin_status=_ORIGIN_STATUS,
        license_id=receipt.license_id,
        chain_state=chain_state,
        event_files=files,
        event_count=len(files),
        first_event_sha256=first.event_sha256,
        last_event_index=last.event.event_index,
        last_event_sha256=last.event_sha256,
        last_event_type=last.event.event_type,
        terminal_event=last.event.terminal_event,
        recorded_verdict=last.event.verdict,
        next_event_index=next_index,
        claim_receipt=receipt,
        claim_receipt_sha256=receipt_sha256,
    )


def _missing_inspection(license_id: str) -> AttemptManifestChainInspectionV10:
    return AttemptManifestChainInspectionV10(
        inspector_schema_version=_INSPECTOR_SCHEMA,
        inspector_scope=_LOCAL_SCOPE,
        origin_status=_ORIGIN_STATUS,
        license_id=license_id,
        chain_state="missing",
        event_files=(),
        event_count=0,
        first_event_sha256=None,
        last_event_index=None,
        last_event_sha256=None,
        last_event_type=None,
        terminal_event=False,
        recorded_verdict=None,
        next_event_index=1,
        claim_receipt=None,
        claim_receipt_sha256=None,
    )


def inspect_local_attempt_manifest_chain_v1_0(
    root: str | os.PathLike[str], license_id: str, /
) -> AttemptManifestChainInspectionV10:
    """Inspect one caller-selected synthetic license directory read-only."""

    root_text = _lexical_root(root)
    selected_license = _validate_license_input(license_id)
    directory = _os_path_join(root_text, *_REPOSITORY_COMPONENTS, selected_license)

    try:
        initial_directory_stat = _os_stat(directory, follow_symlinks=False)
    except FileNotFoundError:
        return _missing_inspection(selected_license)
    except (OSError, TypeError, ValueError):
        _fail("final attempt license directory stat failed")
    directory0 = _directory_snapshot(initial_directory_stat)
    if directory0[3] or not stat.S_ISDIR(directory0[2]):
        _fail("final attempt license path is not a real non-reparse directory")

    names0, snapshots0 = _scan_once(directory)
    retained: list[bytes] = []
    for name, snapshot0 in zip(names0, snapshots0):
        retained.append(_read_stable_entry(_os_path_join(directory, name), snapshot0))

    names1, snapshots1 = _scan_once(directory)
    if names1 != names0 or snapshots1 != snapshots0:
        _fail("attempt directory entries changed during observation")

    final_directory_stat = _nofollow_stat(directory, "final attempt license directory")
    directory1 = _directory_snapshot(final_directory_stat)
    if directory1[3] or not stat.S_ISDIR(directory1[2]):
        _fail("final attempt license path ceased to be a real directory")
    if directory1 != directory0:
        _fail("final attempt license directory metadata changed")

    if not names0:
        return _missing_inspection(selected_license)

    parsed: list[AttemptManifestEventFileV10] = []
    for name, raw in zip(names0, retained):
        repository_path = (
            "docs/experiments/artifacts/uprime_u1_rpc_attempts/"
            + selected_license
            + "/"
            + name
        )
        parsed.append(parse_attempt_manifest_event_file_v1_0(repository_path, raw))
    inspection = _validate_chain(tuple(parsed))
    if inspection.license_id != selected_license:
        _fail("selected license directory does not match the validated chain")
    return inspection


def verify_local_attempt_manifest_terminal_chain_v1_0(
    root: str | os.PathLike[str], license_id: str, /
) -> AttemptManifestChainAttestationV10:
    """Require a terminal local structural chain and return negative authority."""

    inspection = inspect_local_attempt_manifest_chain_v1_0(root, license_id)
    if inspection.chain_state != "valid_terminal":
        _fail("local attempt manifest chain is not valid_terminal")
    if (
        not inspection.event_files
        or inspection.claim_receipt is None
        or inspection.claim_receipt_sha256 is None
        or inspection.first_event_sha256 is None
        or inspection.last_event_index is None
        or inspection.last_event_sha256 is None
        or inspection.last_event_type is None
    ):
        _fail("terminal inspection is missing a required endpoint")
    receipt = inspection.claim_receipt
    terminal_event = inspection.event_files[-1].event
    return AttemptManifestChainAttestationV10(
        verifier_schema_version=_VERIFIER_SCHEMA,
        verifier_scope=_LOCAL_SCOPE,
        origin_status=_ORIGIN_STATUS,
        license_id=inspection.license_id,
        candidate_commit=receipt.candidate_commit,
        license_commit=receipt.license_commit,
        remote_claim_ref=receipt.remote_claim_ref,
        claim_receipt_sha256=inspection.claim_receipt_sha256,
        event_count=inspection.event_count,
        first_event_sha256=inspection.first_event_sha256,
        last_event_index=inspection.last_event_index,
        last_event_sha256=inspection.last_event_sha256,
        chain_state="valid_terminal",
        terminal_event=True,
        last_event_type=inspection.last_event_type,
        recorded_verdict=inspection.recorded_verdict,
        failure_codes=terminal_event.failure_codes,
        preartifact_profile=True,
        artifact_observation="not_performed",
        remote_claim_authentication="not_performed",
        git_object_authentication="not_performed",
        real_remote_publication="not_performed",
        claim_once_authentication="not_performed",
        reservation_token_verification="not_performed",
        artifact_binding="not_performed",
        verifier_binding="not_performed",
        scanner_binding="not_performed",
        privacy_scan="not_performed",
        archive_verification="not_performed",
        authority_scope="none",
        canonical_run_authority=False,
        licenses_execution=False,
        licenses_later_stage=False,
    )


__all__ = [
    "AttemptManifestV10Error",
    "PublicClaimReceiptV10",
    "AttemptManifestEventV10",
    "AttemptManifestEventFileV10",
    "AttemptManifestChainInspectionV10",
    "AttemptManifestChainAttestationV10",
    "encode_attempt_manifest_event_v1_0",
    "parse_attempt_manifest_event_file_v1_0",
    "inspect_local_attempt_manifest_chain_v1_0",
    "verify_local_attempt_manifest_terminal_chain_v1_0",
]
