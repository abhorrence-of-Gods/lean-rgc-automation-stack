"""M2b phase-1a strict chain primitives.

This module does not authenticate a bundle, recompute contracts, or confer
canonical-run authority.  A synthetically constructed chain is intentionally
indistinguishable from runtime-origin bytes at this layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import threading
from typing import Any, BinaryIO


SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD = (
    "lean-rgc-uprime-rpc-parsed-ledger-record-v1.0"
)
SCHEMA_UPRIME_RPC_CHAIN_STRUCTURE_VERIFIER = (
    "lean-rgc-uprime-rpc-chain-structure-verifier-v0.1"
)
SCHEMA_UPRIME_RPC_CHAIN_PREFIX_INSPECTOR = (
    "lean-rgc-uprime-rpc-chain-prefix-inspector-v0.1"
)
STRICT_JSON_CANONICALIZER_ID = "lean-rgc-strict-json-int-v1"

MAX_LEDGER_BYTES = 134_217_728
MAX_EVENT_LINE_BYTES = 16_777_216
MAX_CLOSURE_LINE_BYTES = 1_048_576
MAX_LEDGER_RECORDS = 1_024
MAX_JSON_DEPTH = 128
MAX_CONTAINER_MEMBERS = 100_000
MAX_STRING_UTF8_BYTES = 8_388_608
MIN_SIGNED_64 = -(2**63)
MAX_SIGNED_64 = 2**63 - 1

_GENESIS_DOMAIN = b"lean-rgc-uprime-u1-parsed-ledger-genesis-v1\0"
_RECORD_DOMAIN = b"lean-rgc-uprime-u1-parsed-ledger-record-v1\0"
_HEX64_UPPER_RE = re.compile(r"[0-9A-F]{64}\Z")
_ENVELOPE_KEYS = (
    "body",
    "previous_record_sha256",
    "record_index",
    "record_sha256",
    "record_type",
    "schema_version",
)
_CORE_KEYS = (
    "body",
    "previous_record_sha256",
    "record_index",
    "record_type",
    "schema_version",
)
_EVENT_TYPES = ("local_probe", "request_intent", "parsed_response")
_RECORD_TYPES = ("header", *_EVENT_TYPES, "closure")


class StandaloneLedgerStructureError(ValueError):
    """The supplied bytes do not satisfy the standalone ledger structure."""


class StandaloneLedgerWriteError(RuntimeError):
    """A standalone writer failed and is permanently poisoned."""


def _reject_float(_text: str) -> Any:
    raise StandaloneLedgerStructureError("floating-point JSON is forbidden")


def _reject_constant(_text: str) -> Any:
    raise StandaloneLedgerStructureError("non-finite JSON is forbidden")


def _parse_int64(text: str) -> int:
    digits = text[1:] if text.startswith("-") else text
    if not digits or len(digits) > 19:
        raise StandaloneLedgerStructureError("JSON integer is outside signed-64")
    try:
        value = int(text, 10)
    except (ValueError, OverflowError) as exc:
        raise StandaloneLedgerStructureError("invalid JSON integer") from exc
    if value < MIN_SIGNED_64 or value > MAX_SIGNED_64:
        raise StandaloneLedgerStructureError("JSON integer is outside signed-64")
    return value


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len(pairs) > MAX_CONTAINER_MEMBERS:
        raise StandaloneLedgerStructureError("JSON object member limit exceeded")
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StandaloneLedgerStructureError("duplicate JSON key")
        value[key] = item
    return value


def _validate_string(value: str) -> None:
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StandaloneLedgerStructureError("JSON string contains a surrogate") from exc
    if len(encoded) > MAX_STRING_UTF8_BYTES:
        raise StandaloneLedgerStructureError("JSON string byte limit exceeded")


def _validate_json_value(value: Any, *, container_depth: int = 0) -> None:
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if value < MIN_SIGNED_64 or value > MAX_SIGNED_64:
            raise StandaloneLedgerStructureError("JSON integer is outside signed-64")
        return
    if type(value) is str:
        _validate_string(value)
        return
    if type(value) is list:
        depth = container_depth + 1
        if depth > MAX_JSON_DEPTH:
            raise StandaloneLedgerStructureError("JSON nesting depth exceeded")
        if len(value) > MAX_CONTAINER_MEMBERS:
            raise StandaloneLedgerStructureError("JSON array member limit exceeded")
        for item in value:
            _validate_json_value(item, container_depth=depth)
        return
    if type(value) is dict:
        depth = container_depth + 1
        if depth > MAX_JSON_DEPTH:
            raise StandaloneLedgerStructureError("JSON nesting depth exceeded")
        if len(value) > MAX_CONTAINER_MEMBERS:
            raise StandaloneLedgerStructureError("JSON object member limit exceeded")
        for key, item in value.items():
            if type(key) is not str:
                raise StandaloneLedgerStructureError("JSON object key is not a string")
            _validate_string(key)
            _validate_json_value(item, container_depth=depth)
        return
    raise StandaloneLedgerStructureError(
        f"value is outside the strict JSON algebra: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize the frozen integer-only JSON subset without a trailing LF."""

    _validate_json_value(value)
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return text.encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise StandaloneLedgerStructureError("strict JSON serialization failed") from exc


def parse_canonical_json_bytes(raw: bytes) -> Any:
    """Parse strict JSON and require byte-identical canonical serialization."""

    if raw.startswith(b"\xef\xbb\xbf"):
        raise StandaloneLedgerStructureError("UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_from_pairs,
            parse_float=_reject_float,
            parse_int=_parse_int64,
            parse_constant=_reject_constant,
        )
        _validate_json_value(value)
        canonical = canonical_json_bytes(value)
    except StandaloneLedgerStructureError:
        raise
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as exc:
        raise StandaloneLedgerStructureError("strict JSON parse failed") from exc
    if raw != canonical:
        raise StandaloneLedgerStructureError("JSON bytes are not canonical")
    return value


def _uppercase_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _framed_hash(domain: bytes, payload: bytes) -> str:
    if len(payload) > 2**64 - 1:
        raise StandaloneLedgerStructureError("hash payload length is out of range")
    return _uppercase_sha256(domain + struct.pack(">Q", len(payload)) + payload)


def compute_genesis_sha256(header_body: dict[str, Any]) -> str:
    return _framed_hash(_GENESIS_DOMAIN, canonical_json_bytes(header_body))


def _record_core(
    *,
    record_index: int,
    record_type: str,
    previous_record_sha256: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    if type(record_index) is not int or not (0 <= record_index <= MAX_SIGNED_64):
        raise StandaloneLedgerStructureError("record_index is invalid")
    if record_type not in _RECORD_TYPES:
        raise StandaloneLedgerStructureError("record_type is invalid")
    if _HEX64_UPPER_RE.fullmatch(previous_record_sha256) is None:
        raise StandaloneLedgerStructureError("previous record digest is invalid")
    if type(body) is not dict:
        raise StandaloneLedgerStructureError("record body must be an object")
    _validate_json_value(body)
    core = {
        "schema_version": SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD,
        "record_index": record_index,
        "record_type": record_type,
        "previous_record_sha256": previous_record_sha256,
        "body": body,
    }
    if tuple(sorted(core)) != _CORE_KEYS:
        raise AssertionError("record core field registry drifted")
    return core


def compute_record_sha256(
    *,
    record_index: int,
    record_type: str,
    previous_record_sha256: str,
    body: dict[str, Any],
) -> str:
    core = _record_core(
        record_index=record_index,
        record_type=record_type,
        previous_record_sha256=previous_record_sha256,
        body=body,
    )
    return _framed_hash(_RECORD_DOMAIN, canonical_json_bytes(core))


def build_chain_record(
    *,
    record_index: int,
    record_type: str,
    previous_record_sha256: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    core = _record_core(
        record_index=record_index,
        record_type=record_type,
        previous_record_sha256=previous_record_sha256,
        body=body,
    )
    record = {
        **core,
        "record_sha256": _framed_hash(_RECORD_DOMAIN, canonical_json_bytes(core)),
    }
    if tuple(sorted(record)) != _ENVELOPE_KEYS:
        raise AssertionError("record envelope field registry drifted")
    return record


def canonical_chain_record_line(record: dict[str, Any]) -> bytes:
    return canonical_json_bytes(record) + b"\n"


def _flush_raw_fd(_fd: int) -> None:
    """Raw os.write is unbuffered; this explicit hook freezes flush ordering."""


def _stat_identity(value: os.stat_result) -> tuple[int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
    )


def _stat_snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        *_stat_identity(value),
        int(getattr(value, "st_ctime_ns", round(value.st_ctime * 1_000_000_000))),
        int(value.st_size),
        int(getattr(value, "st_mtime_ns", round(value.st_mtime * 1_000_000_000))),
    )


def _path_binding(value: os.stat_result) -> tuple[int, int, int, int]:
    return (
        *_stat_identity(value),
        int(value.st_size),
        int(getattr(value, "st_mtime_ns", round(value.st_mtime * 1_000_000_000))),
    )


@dataclass(frozen=True)
class StandaloneChainAttestation:
    attestation_scope: str
    origin_status: str
    verifier_schema_version: str
    record_schema_version: str
    input_sha256: str
    input_bytes: int
    genesis_sha256: str
    header_record_sha256: str
    closure_record_sha256: str
    final_chain_head: str
    record_count: int
    closure_record_index: int
    authority_scope: str = "none"
    bundle_binding: str = "not_performed"
    remote_claim_authentication: str = "not_performed"
    report_binding: str = "not_performed"
    contract_recomputation: str = "not_performed"
    attempt_manifest_binding: str = "not_performed"
    privacy_scan: str = "not_performed"
    archive_verification: str = "not_performed"
    canonical_run_authority: bool = False
    licenses_execution: bool = False
    licenses_later_stage: bool = False


@dataclass(frozen=True)
class StandaloneChainInspection:
    inspection_scope: str
    inspector_schema_version: str
    status: str
    finalized: bool
    verified_prefix_bytes: int
    verified_record_count: int
    verified_chain_head: str | None
    error_code: str | None
    authority_scope: str = "none"
    canonical_run_authority: bool = False
    licenses_execution: bool = False
    licenses_later_stage: bool = False


@dataclass(frozen=True)
class _ScanResult:
    status: str
    verified_prefix_bytes: int
    record_count: int
    head: str | None
    genesis: str | None
    header_hash: str | None
    closure_hash: str | None
    closure_index: int | None
    input_sha256: str | None
    input_bytes: int
    error_code: str | None


def _validate_record_envelope(
    value: Any,
    *,
    expected_index: int,
    expected_previous: str | None,
) -> tuple[str, dict[str, Any], str, str]:
    if type(value) is not dict or tuple(sorted(value)) != _ENVELOPE_KEYS:
        raise StandaloneLedgerStructureError("record envelope field set is invalid")
    if value.get("schema_version") != SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD:
        raise StandaloneLedgerStructureError("record schema is invalid")
    if type(value.get("record_index")) is not int or value["record_index"] != expected_index:
        raise StandaloneLedgerStructureError("record index is not contiguous")
    record_type = value.get("record_type")
    if record_type not in _RECORD_TYPES:
        raise StandaloneLedgerStructureError("record type is invalid")
    previous = value.get("previous_record_sha256")
    stored = value.get("record_sha256")
    body = value.get("body")
    if type(previous) is not str or _HEX64_UPPER_RE.fullmatch(previous) is None:
        raise StandaloneLedgerStructureError("previous record digest is invalid")
    if type(stored) is not str or _HEX64_UPPER_RE.fullmatch(stored) is None:
        raise StandaloneLedgerStructureError("record digest is invalid")
    if type(body) is not dict:
        raise StandaloneLedgerStructureError("record body must be an object")
    if expected_index == 0:
        if record_type != "header":
            raise StandaloneLedgerStructureError("record zero is not the header")
        genesis = compute_genesis_sha256(body)
        if previous != genesis:
            raise StandaloneLedgerStructureError("header does not bind its genesis")
    elif previous != expected_previous:
        raise StandaloneLedgerStructureError("record chain predecessor mismatch")
    recomputed = compute_record_sha256(
        record_index=expected_index,
        record_type=record_type,
        previous_record_sha256=previous,
        body=body,
    )
    if stored != recomputed:
        raise StandaloneLedgerStructureError("record digest mismatch")
    return record_type, body, stored, previous


def _scan_error(code: str, *, input_bytes: int = 0) -> _ScanResult:
    return _ScanResult(
        "corrupt",
        0,
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        input_bytes,
        code,
    )


def _scan_open_handle(handle: BinaryIO, initial: os.stat_result) -> _ScanResult:
    if initial.st_size > MAX_LEDGER_BYTES:
        return _scan_error("FILE_SIZE_LIMIT", input_bytes=initial.st_size)
    digest = hashlib.sha256()
    total = 0
    index = 0
    head: str | None = None
    genesis: str | None = None
    header_hash: str | None = None
    closure_hash: str | None = None
    closure_index: int | None = None
    closure_seen = False
    while True:
        raw_line = handle.readline(MAX_EVENT_LINE_BYTES + 1)
        if not raw_line:
            break
        if closure_seen:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), "BYTES_AFTER_CLOSURE")
        if len(raw_line) > MAX_EVENT_LINE_BYTES:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, initial.st_size, "LINE_SIZE_LIMIT")
        if total + len(raw_line) > MAX_LEDGER_BYTES:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), "FILE_SIZE_LIMIT")
        if not raw_line.endswith(b"\n"):
            return _ScanResult("torn", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), "FINAL_LINE_WITHOUT_LF")
        try:
            value = parse_canonical_json_bytes(raw_line[:-1])
            record_type, body, record_hash, previous = _validate_record_envelope(
                value,
                expected_index=index,
                expected_previous=head,
            )
        except StandaloneLedgerStructureError as exc:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), type(exc).__name__)
        if record_type == "closure" and len(raw_line) > MAX_CLOSURE_LINE_BYTES:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), "CLOSURE_SIZE_LIMIT")
        if index == 0:
            genesis = previous
            header_hash = record_hash
        if record_type == "header" and index != 0:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total + len(raw_line), "SECOND_HEADER")
        if record_type == "closure":
            closure_seen = True
            closure_hash = record_hash
            closure_index = index
        digest.update(raw_line)
        total += len(raw_line)
        head = record_hash
        index += 1
        if index > MAX_LEDGER_RECORDS:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, total, "RECORD_LIMIT")

    first_final = os.fstat(handle.fileno())
    if _stat_snapshot(first_final) != _stat_snapshot(initial) or total != first_final.st_size:
        return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, first_final.st_size, "FILE_CHANGED_DURING_SCAN")

    first_sha = digest.hexdigest().upper()
    handle.seek(0, os.SEEK_SET)
    second_digest = hashlib.sha256()
    second_total = 0
    while True:
        chunk = handle.read(min(1024 * 1024, MAX_LEDGER_BYTES - second_total + 1))
        if not chunk:
            break
        second_total += len(chunk)
        if second_total > MAX_LEDGER_BYTES:
            return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, second_total, "FILE_SIZE_LIMIT")
        second_digest.update(chunk)
    second_final = os.fstat(handle.fileno())
    if (
        _stat_snapshot(second_final) != _stat_snapshot(initial)
        or second_total != initial.st_size
        or second_digest.hexdigest().upper() != first_sha
    ):
        return _ScanResult("corrupt", total, index, head, genesis, header_hash, closure_hash, closure_index, None, second_total, "FILE_CHANGED_DURING_SCAN")
    if index == 0 or not closure_seen:
        return _ScanResult("unclosed", total, index, head, genesis, header_hash, closure_hash, closure_index, first_sha, total, None)
    return _ScanResult("closed_chain", total, index, head, genesis, header_hash, closure_hash, closure_index, first_sha, total, None)


def _scan_chain(
    path: Path,
    *,
    expected_identity: tuple[int, int] | None = None,
) -> _ScanResult:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    except OSError as exc:
        return _scan_error(f"OPEN_{type(exc).__name__}")
    handle: BinaryIO | None = None
    initial: os.stat_result | None = None
    result: _ScanResult
    try:
        initial = os.fstat(fd)
        if expected_identity is not None and _stat_identity(initial) != expected_identity:
            result = _scan_error("FILE_IDENTITY_CHANGED", input_bytes=initial.st_size)
        else:
            handle = os.fdopen(fd, "rb", buffering=0)
            fd = -1
            result = _scan_open_handle(handle, initial)
    except BaseException as exc:
        result = _scan_error(f"SCAN_{type(exc).__name__}")
    close_error: BaseException | None = None
    try:
        if handle is not None:
            handle.close()
        elif fd >= 0:
            os.close(fd)
    except BaseException as exc:
        close_error = exc
    if close_error is not None:
        return _scan_error(
            f"SCAN_CLOSE_{type(close_error).__name__}", input_bytes=result.input_bytes
        )
    if initial is not None and result.status in {"closed_chain", "unclosed"}:
        try:
            current_path = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            return _scan_error(
                f"PATH_RESTAT_{type(exc).__name__}", input_bytes=result.input_bytes
            )
        if _path_binding(current_path) != _path_binding(initial):
            return _scan_error(
                "FILE_IDENTITY_CHANGED", input_bytes=result.input_bytes
            )
    return result


def inspect_standalone_chain_prefix(path: str | Path) -> StandaloneChainInspection:
    """Inspect an immutable prefix without granting authority or repairing it."""

    result = _scan_chain(Path(path))
    return StandaloneChainInspection(
        inspection_scope="standalone_chain_prefix_only",
        inspector_schema_version=SCHEMA_UPRIME_RPC_CHAIN_PREFIX_INSPECTOR,
        status=result.status,
        finalized=False,
        verified_prefix_bytes=result.verified_prefix_bytes,
        verified_record_count=result.record_count,
        verified_chain_head=result.head,
        error_code=result.error_code,
    )


def _attestation_from_scan(result: _ScanResult) -> StandaloneChainAttestation:
    if result.status != "closed_chain":
        raise StandaloneLedgerStructureError(
            f"standalone ledger chain is not closed: {result.status}"
        )
    assert result.input_sha256 is not None
    assert result.genesis is not None
    assert result.header_hash is not None
    assert result.closure_hash is not None
    assert result.closure_index is not None
    assert result.head is not None
    return StandaloneChainAttestation(
        attestation_scope="standalone_chain_structure_only",
        origin_status="unknown_may_be_synthetic",
        verifier_schema_version=SCHEMA_UPRIME_RPC_CHAIN_STRUCTURE_VERIFIER,
        record_schema_version=SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD,
        input_sha256=result.input_sha256,
        input_bytes=result.input_bytes,
        genesis_sha256=result.genesis,
        header_record_sha256=result.header_hash,
        closure_record_sha256=result.closure_hash,
        final_chain_head=result.head,
        record_count=result.record_count,
        closure_record_index=result.closure_index,
    )


def attest_standalone_closed_chain(
    path: str | Path,
) -> StandaloneChainAttestation:
    """Attest only canonical chain closure; no bundle or execution authority."""

    return _attestation_from_scan(_scan_chain(Path(path)))


class StandaloneChainWriter:
    """One-owner append-only chain writer with no canonical-run authority."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd = -1
        self._cleanup_fd = -1
        self._lock = threading.Lock()
        self._state = "open"
        self._tracked_bytes = 0
        self._record_count = 0
        self._head: str | None = None
        self._file_identity: tuple[int, int] | None = None

    @classmethod
    def create(
        cls, path: str | Path, *, header_body: dict[str, Any]
    ) -> "StandaloneChainWriter":
        target = Path(path)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_APPEND
        flags |= getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(target, flags, 0o600)
        except OSError as exc:
            raise StandaloneLedgerWriteError("exclusive ledger create failed") from exc
        try:
            opened = os.fstat(fd)
        except OSError as exc:
            try:
                os.close(fd)
            except OSError:
                pass
            raise StandaloneLedgerWriteError(
                "new ledger identity could not be read"
            ) from exc
        try:
            writer = cls(target)
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        writer._fd = fd
        writer._file_identity = _stat_identity(opened)
        fd = -1
        try:
            writer._append_record_locked("header", header_body)
            return writer
        except BaseException:
            if writer._fd >= 0:
                owned_fd, writer._fd = writer._fd, -1
                try:
                    os.close(owned_fd)
                except OSError:
                    writer._cleanup_fd = owned_fd
                writer._state = "poisoned"
            raise

    def __enter__(self) -> "StandaloneChainWriter":
        self._ensure_open()
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> bool:
        if self._state == "open":
            self.abandon_unfinalized()
        return False

    def __del__(self) -> None:
        fds = {getattr(self, "_fd", -1), getattr(self, "_cleanup_fd", -1)}
        self._fd = -1
        self._cleanup_fd = -1
        for fd in fds:
            if fd < 0:
                continue
            try:
                os.close(fd)
            except OSError:
                pass
        if fds != {-1}:
            self._state = "abandoned"

    @property
    def poisoned(self) -> bool:
        return self._state == "poisoned"

    @property
    def record_count(self) -> int:
        return self._record_count

    @property
    def chain_head(self) -> str | None:
        return self._head

    def _ensure_open(self) -> None:
        if self._state != "open" or self._fd < 0:
            raise StandaloneLedgerWriteError(
                f"ledger writer is not appendable: {self._state}"
            )

    def _poison(self, message: str, exc: BaseException | None = None) -> None:
        self._state = "poisoned"
        fd, self._fd = self._fd, -1
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                self._cleanup_fd = fd
        error = StandaloneLedgerWriteError(message)
        if exc is None:
            raise error
        raise error from exc

    def _append_record_locked(self, record_type: str, body: dict[str, Any]) -> None:
        self._ensure_open()
        if self._record_count >= MAX_LEDGER_RECORDS:
            raise StandaloneLedgerStructureError("ledger record limit exhausted")
        if self._record_count == 0:
            if record_type != "header":
                self._poison("first record must be header")
            previous = compute_genesis_sha256(body)
        else:
            if record_type == "header" or self._head is None:
                self._poison("header placement or chain state is invalid")
            previous = self._head
        record = build_chain_record(
            record_index=self._record_count,
            record_type=record_type,
            previous_record_sha256=previous,
            body=body,
        )
        line = canonical_chain_record_line(record)
        line_limit = (
            MAX_CLOSURE_LINE_BYTES
            if record_type == "closure"
            else MAX_EVENT_LINE_BYTES
        )
        if len(line) > line_limit:
            raise StandaloneLedgerStructureError("ledger record line limit exceeded")
        if record_type == "closure":
            if self._tracked_bytes + len(line) > MAX_LEDGER_BYTES:
                raise StandaloneLedgerStructureError(
                    "ledger file limit exceeded at closure"
                )
        else:
            if self._tracked_bytes + len(line) + MAX_CLOSURE_LINE_BYTES > MAX_LEDGER_BYTES:
                raise StandaloneLedgerStructureError(
                    "ledger closure byte reserve would be consumed"
                )
            if self._record_count + 2 > MAX_LEDGER_RECORDS:
                raise StandaloneLedgerStructureError(
                    "ledger closure record reserve would be consumed"
                )
        try:
            stat_before = os.fstat(self._fd)
            position = os.lseek(self._fd, 0, os.SEEK_CUR)
            if stat_before.st_size != self._tracked_bytes or position != self._tracked_bytes:
                self._poison("ledger file position or size drifted")
            written = os.write(self._fd, line)
            if written != len(line):
                self._poison("ledger raw write was short")
            _flush_raw_fd(self._fd)
            os.fsync(self._fd)
            stat_after = os.fstat(self._fd)
            position_after = os.lseek(self._fd, 0, os.SEEK_CUR)
            expected_size = self._tracked_bytes + len(line)
            if stat_after.st_size != expected_size or position_after != expected_size:
                self._poison("ledger durable size or position mismatch")
        except StandaloneLedgerWriteError:
            raise
        except BaseException as exc:
            self._poison("ledger append/flush/fsync failed", exc)
        self._tracked_bytes += len(line)
        self._record_count += 1
        self._head = record["record_sha256"]

    def append_event(self, record_type: str, body: dict[str, Any]) -> str:
        if record_type not in _EVENT_TYPES:
            raise StandaloneLedgerStructureError("append_event record type is invalid")
        with self._lock:
            self._append_record_locked(record_type, body)
            assert self._head is not None
            return self._head

    def close_with_closure(
        self, body: dict[str, Any]
    ) -> StandaloneChainAttestation:
        with self._lock:
            self._append_record_locked("closure", body)
            expected_head = self._head
            expected_count = self._record_count
            expected_bytes = self._tracked_bytes
            expected_identity = self._file_identity
            if expected_identity is None:
                self._poison("ledger file identity was unavailable")
            fd, self._fd = self._fd, -1
            try:
                os.close(fd)
            except OSError as exc:
                self._cleanup_fd = fd
                self._state = "poisoned"
                raise StandaloneLedgerWriteError("ledger close failed") from exc
            self._state = "closed"
        try:
            attestation = _attestation_from_scan(
                _scan_chain(self.path, expected_identity=expected_identity)
            )
        except StandaloneLedgerStructureError as exc:
            self._state = "poisoned"
            raise StandaloneLedgerWriteError(
                "closed ledger chain could not be reattested"
            ) from exc
        if (
            attestation.final_chain_head != expected_head
            or attestation.record_count != expected_count
            or attestation.input_bytes != expected_bytes
        ):
            self._state = "poisoned"
            raise StandaloneLedgerWriteError(
                "closed ledger attestation does not match the writer state"
            )
        return attestation

    def abandon_unfinalized(self) -> None:
        """Close without closure; the file remains immutable and non-resumable."""

        with self._lock:
            self._ensure_open()
            fd, self._fd = self._fd, -1
            try:
                os.close(fd)
            except OSError as exc:
                self._cleanup_fd = fd
                self._state = "poisoned"
                raise StandaloneLedgerWriteError("ledger abandon close failed") from exc
            self._state = "abandoned"


__all__ = [
    "MAX_CLOSURE_LINE_BYTES",
    "MAX_EVENT_LINE_BYTES",
    "MAX_LEDGER_BYTES",
    "MAX_LEDGER_RECORDS",
    "SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD",
    "SCHEMA_UPRIME_RPC_CHAIN_PREFIX_INSPECTOR",
    "SCHEMA_UPRIME_RPC_CHAIN_STRUCTURE_VERIFIER",
    "STRICT_JSON_CANONICALIZER_ID",
    "StandaloneChainAttestation",
    "StandaloneChainInspection",
    "StandaloneLedgerStructureError",
    "StandaloneLedgerWriteError",
    "StandaloneChainWriter",
    "attest_standalone_closed_chain",
    "build_chain_record",
    "canonical_json_bytes",
    "canonical_chain_record_line",
    "compute_genesis_sha256",
    "compute_record_sha256",
    "inspect_standalone_chain_prefix",
    "parse_canonical_json_bytes",
]
