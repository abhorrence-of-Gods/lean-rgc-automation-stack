"""Read-only Phase-2a verifier for a standalone bundle reservation.

This module deliberately authenticates neither a remote claim nor any Git
object.  It accepts self-consistent synthetic reservation bytes, grants no
execution authority, and has no writer or compatibility path for the legacy
v1.0 reservation format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import os
import re
import stat
from typing import Any

from lean_rgc.evals.uprime_rpc_ledger import (
    StandaloneLedgerStructureError,
    canonical_json_bytes,
    parse_canonical_json_bytes,
)


SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC = (
    "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
)
SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION = (
    "lean-rgc-uprime-rpc-bundle-reservation-v1.1"
)
SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION_VERIFIER = (
    "lean-rgc-uprime-rpc-bundle-reservation-token-verifier-v0.1"
)
VERIFIER_SCOPE = "standalone_bundle_reservation_receipt_token_only"

REGISTERED_RUN_DIR = "runs/uprime_u1_rpc_20260710"
REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
REMOTE_BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"
REPORT_SCHEMA_VERSION = "lean-rgc-uprime-rpc-diagnostic-v1.2"
LEDGER_SCHEMA_VERSION = "lean-rgc-uprime-rpc-parsed-ledger-v1.0"
RECORD_SCHEMA_VERSION = "lean-rgc-uprime-rpc-parsed-ledger-record-v1.0"
RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
EXPECTED_FRAME_COUNT = 23
EXPECTED_FRAME_MANIFEST_SHA256 = (
    "03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E"
)
MAX_RESERVATION_BYTES = 1_048_576
MAX_SIGNED_64 = 2**63 - 1
_READ_CHUNK_BYTES = 64 * 1024
_LICENSE_DOMAIN = b"lean-rgc-uprime-u1-attempt-v1\0"

_HEX40_LOWER_RE = re.compile(r"[0-9a-f]{40}\Z", flags=re.ASCII)
_HEX64_LOWER_RE = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)
_HEX64_UPPER_RE = re.compile(r"[0-9A-F]{64}\Z", flags=re.ASCII)
_ANCHOR_RE = re.compile(r"[0-9a-f]{12}\Z", flags=re.ASCII)
_UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z",
    flags=re.ASCII,
)
_LEXICAL_SEPARATOR_RE = re.compile(r"[\\/]")
_ASCII_DRIVE_RE = re.compile(r"[A-Za-z]:")

_CLAIM_RECEIPT_KEYS = (
    "candidate_commit",
    "candidate_tree_oid",
    "claimed_at_utc",
    "input_manifest_sha256",
    "license_commit",
    "license_id",
    "registry_blob_oid",
    "registry_sha256",
    "remote_branch_ref",
    "remote_claim_oid",
    "remote_claim_ref",
    "remote_url",
    "schema_version",
)
_RESERVATION_KEYS = (
    "anchor",
    "candidate_commit",
    "claim_receipt",
    "claim_receipt_sha256",
    "expected_frame_count",
    "expected_frame_manifest_sha256",
    "ledger_artifact_name",
    "ledger_schema_version",
    "license_commit",
    "license_id",
    "process_id",
    "record_schema_version",
    "registered_run_dir",
    "remote_claim_ref",
    "report_artifact_name",
    "report_schema_version",
    "reservation_artifact_name",
    "reservation_token_sha256",
    "reserved_at_utc",
    "rpc_protocol_version",
    "schema_version",
    "status",
)


class StandaloneBundleReservationV11Error(ValueError):
    """The supplied path cannot produce a Phase-2a attestation."""


@dataclass(frozen=True)
class StandaloneBundleReservationV11Attestation:
    verifier_schema_version: str
    verifier_scope: str
    origin_status: str
    input_sha256: str
    input_bytes: int
    reservation_sha256: str
    reservation_artifact_name: str
    report_artifact_name: str
    ledger_artifact_name: str
    registered_run_dir: str
    candidate_commit: str
    license_commit: str
    license_id: str
    anchor: str
    remote_claim_ref: str
    claim_receipt_sha256: str
    receipt_schema_version: str
    reservation_schema_version: str
    reservation_token_verification: str
    remote_claim_authentication: str
    git_object_authentication: str
    claim_once_authentication: str
    manifest_binding: str
    ledger_binding: str
    report_binding: str
    privacy_scan: str
    archive_verification: str
    authority_scope: str
    canonical_run_authority: bool
    licenses_execution: bool
    licenses_later_stage: bool


@dataclass(frozen=True)
class _ReservationSnapshot:
    raw_path: str
    file_bytes: bytes
    input_sha256: str
    input_bytes: int


def _fail(message: str) -> None:
    raise StandaloneBundleReservationV11Error(message) from None


def _stat_nanoseconds(value: os.stat_result, name: str) -> int:
    nanosecond_name = f"{name}_ns"
    if hasattr(value, nanosecond_name):
        return int(getattr(value, nanosecond_name))
    return round(float(getattr(value, name)) * 1_000_000_000)


def _stat_snapshot(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        _stat_nanoseconds(value, "st_ctime"),
        int(value.st_size),
        _stat_nanoseconds(value, "st_mtime"),
    )


def _path_binding(value: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_size),
        _stat_nanoseconds(value, "st_mtime"),
    )


def _snapshot_binding(
    value: tuple[int, int, int, int, int],
) -> tuple[int, int, int, int]:
    return (value[0], value[1], value[3], value[4])


def _read_bounded_fd(
    fd: int,
    *,
    expected_size: int,
    max_bytes: int = MAX_RESERVATION_BYTES,
) -> bytes:
    """Read one pass from offset zero without exceeding an injected bound."""

    if type(expected_size) is not int or expected_size < 0:
        _fail("reservation observation size is invalid")
    if type(max_bytes) is not int or max_bytes < 0:
        _fail("reservation observation bound is invalid")
    if expected_size > max_bytes:
        _fail("reservation exceeds the byte limit")
    try:
        os.lseek(fd, 0, os.SEEK_SET)
    except OSError:
        _fail("reservation seek failed")
    chunks: list[bytes] = []
    total = 0
    while True:
        read_size = min(_READ_CHUNK_BYTES, max_bytes - total + 1)
        try:
            chunk = os.read(fd, read_size)
        except OSError:
            _fail("reservation read failed")
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            _fail("reservation exceeds the byte limit")
        chunks.append(chunk)
    if total != expected_size:
        _fail("reservation byte count changed during observation")
    return b"".join(chunks)


def _lexical_path(path: str | os.PathLike[str]) -> str:
    try:
        raw_path = os.fspath(path)
    except (TypeError, ValueError, OSError):
        _fail("reservation path is invalid")
    if type(raw_path) is not str or not raw_path:
        _fail("reservation path must be a nonempty lexical string")
    return raw_path


def _load_reservation_snapshot(
    path: str | os.PathLike[str],
) -> _ReservationSnapshot:
    """Retain two matching passes from one descriptor and bind its path."""

    raw_path = _lexical_path(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(raw_path, flags)
    except (OSError, ValueError, TypeError):
        _fail("reservation open failed")

    pending_error: StandaloneBundleReservationV11Error | None = None
    first_bytes: bytes | None = None
    first_digest: str | None = None
    snapshot0: tuple[int, int, int, int, int] | None = None
    try:
        try:
            opened = os.fstat(fd)
        except OSError:
            _fail("reservation descriptor stat failed")
        if not stat.S_ISREG(opened.st_mode):
            _fail("reservation path is not a regular file")
        snapshot0 = _stat_snapshot(opened)
        if snapshot0[3] > MAX_RESERVATION_BYTES:
            _fail("reservation exceeds the byte limit")

        first_bytes = _read_bounded_fd(fd, expected_size=snapshot0[3])
        try:
            snapshot1 = _stat_snapshot(os.fstat(fd))
        except OSError:
            _fail("reservation descriptor stat failed")
        first_digest = hashlib.sha256(first_bytes).hexdigest().upper()

        second_bytes = _read_bounded_fd(fd, expected_size=snapshot0[3])
        try:
            snapshot2 = _stat_snapshot(os.fstat(fd))
        except OSError:
            _fail("reservation descriptor stat failed")
        second_digest = hashlib.sha256(second_bytes).hexdigest().upper()
        if snapshot0 != snapshot1 or snapshot0 != snapshot2:
            _fail("reservation metadata changed during observation")
        if len(first_bytes) != len(second_bytes) or first_digest != second_digest:
            _fail("reservation content changed during observation")
    except StandaloneBundleReservationV11Error as exc:
        pending_error = exc
    except Exception:
        pending_error = StandaloneBundleReservationV11Error(
            "reservation observation failed"
        )

    try:
        os.close(fd)
    except OSError:
        pending_error = StandaloneBundleReservationV11Error(
            "reservation close failed"
        )
    if pending_error is not None:
        raise pending_error from None

    if first_bytes is None or first_digest is None or snapshot0 is None:
        _fail("reservation observation did not produce a complete snapshot")
    try:
        final_path = os.stat(raw_path, follow_symlinks=False)
    except (OSError, ValueError, TypeError):
        _fail("reservation path binding failed")
    if not stat.S_ISREG(final_path.st_mode):
        _fail("reservation path binding is not a regular file")
    if _path_binding(final_path) != _snapshot_binding(snapshot0):
        _fail("reservation path identity changed during observation")
    return _ReservationSnapshot(
        raw_path=raw_path,
        file_bytes=first_bytes,
        input_sha256=first_digest,
        input_bytes=len(first_bytes),
    )


def _exact_object(value: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(sorted(value)) != tuple(sorted(keys)):
        _fail(f"{label} field set is invalid")
    return value


def _string(value: Any, label: str, *, nonempty: bool = False) -> str:
    if type(value) is not str or (nonempty and not value):
        _fail(f"{label} must be a string")
    return value


def _regex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    text = _string(value, label)
    if pattern.fullmatch(text) is None:
        _fail(f"{label} has invalid syntax")
    return text


def _utc(value: Any, label: str) -> str:
    text = _regex(value, _UTC_RE, label)
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        _fail(f"{label} is not a real UTC instant")
    return text


def _positive_int64(value: Any, label: str) -> int:
    if type(value) is not int or not (1 <= value <= MAX_SIGNED_64):
        _fail(f"{label} must be a positive signed-64 integer")
    return value


def _exact_int(value: Any, expected: int, label: str) -> int:
    if type(value) is not int or value != expected:
        _fail(f"{label} is invalid")
    return value


def _ascii_basename(value: Any, label: str) -> str:
    text = _string(value, label, nonempty=True)
    try:
        text.encode("ascii", errors="strict")
    except UnicodeEncodeError:
        _fail(f"{label} must be ASCII")
    if (
        text in {".", ".."}
        or "/" in text
        or "\\" in text
        or text.startswith(("/", "\\"))
        or _ASCII_DRIVE_RE.match(text) is not None
    ):
        _fail(f"{label} is not a canonical basename")
    return text


def _validate_claim_receipt(value: Any) -> dict[str, Any]:
    receipt = _exact_object(value, _CLAIM_RECEIPT_KEYS, "claim receipt")
    if receipt["schema_version"] != SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC:
        _fail("claim receipt schema is invalid")
    candidate = _regex(
        receipt["candidate_commit"], _HEX40_LOWER_RE, "candidate commit"
    )
    license_commit = _regex(
        receipt["license_commit"], _HEX40_LOWER_RE, "license commit"
    )
    license_id = _regex(receipt["license_id"], _HEX64_LOWER_RE, "license id")
    expected_license_id = hashlib.sha256(
        _LICENSE_DOMAIN + candidate.encode("ascii")
    ).hexdigest()
    if license_id != expected_license_id:
        _fail("license id does not derive from the candidate commit")
    if receipt["remote_url"] != REMOTE_URL:
        _fail("claim receipt remote URL is invalid")
    if receipt["remote_branch_ref"] != REMOTE_BRANCH_REF:
        _fail("claim receipt branch ref is invalid")
    expected_claim_ref = f"refs/tags/uprime-u1-attempts/{license_id}"
    if receipt["remote_claim_ref"] != expected_claim_ref:
        _fail("claim receipt tag ref is invalid")
    remote_claim_oid = _regex(
        receipt["remote_claim_oid"], _HEX40_LOWER_RE, "remote claim oid"
    )
    if remote_claim_oid != license_commit:
        _fail("claim receipt remote oid differs from the license commit")
    _regex(receipt["registry_blob_oid"], _HEX40_LOWER_RE, "registry blob oid")
    _regex(receipt["registry_sha256"], _HEX64_UPPER_RE, "registry sha256")
    _regex(receipt["candidate_tree_oid"], _HEX40_LOWER_RE, "candidate tree oid")
    _regex(
        receipt["input_manifest_sha256"],
        _HEX64_UPPER_RE,
        "input manifest sha256",
    )
    _utc(receipt["claimed_at_utc"], "claim time")
    return receipt


def _validate_reservation_object(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    reservation = _exact_object(value, _RESERVATION_KEYS, "reservation")
    if reservation["schema_version"] != SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION:
        _fail("reservation schema is invalid")
    if reservation["status"] != "LIVE_EVIDENCE_BUNDLE_RESERVED":
        _fail("reservation status is invalid")

    receipt = _validate_claim_receipt(reservation["claim_receipt"])
    candidate = _regex(
        reservation["candidate_commit"],
        _HEX40_LOWER_RE,
        "reservation candidate commit",
    )
    license_commit = _regex(
        reservation["license_commit"],
        _HEX40_LOWER_RE,
        "reservation license commit",
    )
    license_id = _regex(
        reservation["license_id"], _HEX64_LOWER_RE, "reservation license id"
    )
    remote_claim_ref = _string(
        reservation["remote_claim_ref"], "reservation remote claim ref"
    )
    if (
        candidate != receipt["candidate_commit"]
        or license_commit != receipt["license_commit"]
        or license_id != receipt["license_id"]
        or remote_claim_ref != receipt["remote_claim_ref"]
    ):
        _fail("reservation identity differs from its claim receipt")

    anchor = _regex(reservation["anchor"], _ANCHOR_RE, "anchor")
    if anchor != license_commit[:12]:
        _fail("reservation anchor is not the license-commit prefix")
    receipt_digest = hashlib.sha256(canonical_json_bytes(receipt)).hexdigest().upper()
    stored_receipt_digest = _regex(
        reservation["claim_receipt_sha256"],
        _HEX64_UPPER_RE,
        "claim receipt sha256",
    )
    if stored_receipt_digest != receipt_digest:
        _fail("reservation claim receipt digest is invalid")

    if reservation["registered_run_dir"] != REGISTERED_RUN_DIR:
        _fail("reservation run directory is invalid")
    report_name = _ascii_basename(
        reservation["report_artifact_name"], "report artifact name"
    )
    ledger_name = _ascii_basename(
        reservation["ledger_artifact_name"], "ledger artifact name"
    )
    reservation_name = _ascii_basename(
        reservation["reservation_artifact_name"], "reservation artifact name"
    )
    expected_report = f"rpc_diagnostic_{anchor}.json"
    if report_name != expected_report:
        _fail("report artifact name is invalid")
    if ledger_name != f"rpc_diagnostic_{anchor}.responses.jsonl":
        _fail("ledger artifact name is invalid")
    if reservation_name != f"{expected_report}.reservation":
        _fail("reservation artifact name is invalid")
    if reservation["report_schema_version"] != REPORT_SCHEMA_VERSION:
        _fail("reservation report schema is invalid")
    if reservation["ledger_schema_version"] != LEDGER_SCHEMA_VERSION:
        _fail("reservation ledger schema is invalid")
    if reservation["record_schema_version"] != RECORD_SCHEMA_VERSION:
        _fail("reservation record schema is invalid")
    if reservation["rpc_protocol_version"] != RPC_PROTOCOL_VERSION:
        _fail("reservation RPC protocol is invalid")
    _exact_int(
        reservation["expected_frame_count"],
        EXPECTED_FRAME_COUNT,
        "reservation frame count",
    )
    if reservation["expected_frame_manifest_sha256"] != (
        EXPECTED_FRAME_MANIFEST_SHA256
    ):
        _fail("reservation frame manifest is invalid")
    _regex(
        reservation["reservation_token_sha256"],
        _HEX64_UPPER_RE,
        "reservation token sha256",
    )
    _utc(reservation["reserved_at_utc"], "reservation time")
    _positive_int64(reservation["process_id"], "reservation process id")
    return reservation, receipt


def _split_lexical_components(raw_path: str) -> list[str]:
    return _LEXICAL_SEPARATOR_RE.split(raw_path)


def _validate_reservation_path(
    raw_path: str,
    reservation: dict[str, Any],
) -> None:
    parts = _split_lexical_components(raw_path)
    if any(part in {".", ".."} for part in parts):
        _fail("reservation path contains a visible dot component")
    if len(parts) < 3:
        _fail("reservation path lacks the canonical suffix")
    expected = [
        "runs",
        "uprime_u1_rpc_20260710",
        reservation["reservation_artifact_name"],
    ]
    if parts[-3:] != expected or any(not item for item in parts[-3:]):
        _fail("reservation path suffix is invalid")


def _parse_reservation_file(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    if not raw or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail("reservation file must have exactly one terminal LF")
    payload = raw[:-1]
    if not payload or b"\n" in payload or b"\r" in raw:
        _fail("reservation file contains noncanonical line bytes")
    try:
        value = parse_canonical_json_bytes(payload)
    except StandaloneLedgerStructureError:
        _fail("reservation file is not strict canonical JSON")
    return _validate_reservation_object(value)


def _token_digest(token_hex: Any) -> str:
    if type(token_hex) is not str or _HEX64_LOWER_RE.fullmatch(token_hex) is None:
        _fail("reservation token syntax is invalid")
    try:
        token_bytes = token_hex.encode("ascii", errors="strict")
    except UnicodeEncodeError:
        _fail("reservation token syntax is invalid")
    return hashlib.sha256(token_bytes).hexdigest().upper()


def _attest(
    path: str | os.PathLike[str],
    *,
    token_hex: str | None,
) -> StandaloneBundleReservationV11Attestation:
    raw_path = _lexical_path(path)
    if token_hex is not None:
        token_digest = _token_digest(token_hex)
        if token_hex in raw_path:
            _fail("reservation token appears in the lexical path")
    else:
        token_digest = None

    snapshot = _load_reservation_snapshot(raw_path)
    if token_hex is not None and token_hex.encode("ascii") in snapshot.file_bytes:
        _fail("reservation token appears in reservation bytes")
    reservation, receipt = _parse_reservation_file(snapshot.file_bytes)
    _validate_reservation_path(snapshot.raw_path, reservation)

    if token_digest is None:
        token_status = "not_performed"
    else:
        stored_digest = reservation["reservation_token_sha256"]
        if not hmac.compare_digest(stored_digest, token_digest):
            _fail("reservation token does not match the stored digest")
        token_status = "verified_ascii_sha256"

    return StandaloneBundleReservationV11Attestation(
        verifier_schema_version=SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION_VERIFIER,
        verifier_scope=VERIFIER_SCOPE,
        origin_status="unknown_may_be_synthetic",
        input_sha256=snapshot.input_sha256,
        input_bytes=snapshot.input_bytes,
        reservation_sha256=snapshot.input_sha256,
        reservation_artifact_name=reservation["reservation_artifact_name"],
        report_artifact_name=reservation["report_artifact_name"],
        ledger_artifact_name=reservation["ledger_artifact_name"],
        registered_run_dir=reservation["registered_run_dir"],
        candidate_commit=reservation["candidate_commit"],
        license_commit=reservation["license_commit"],
        license_id=reservation["license_id"],
        anchor=reservation["anchor"],
        remote_claim_ref=reservation["remote_claim_ref"],
        claim_receipt_sha256=reservation["claim_receipt_sha256"],
        receipt_schema_version=receipt["schema_version"],
        reservation_schema_version=reservation["schema_version"],
        reservation_token_verification=token_status,
        remote_claim_authentication="not_performed",
        git_object_authentication="not_performed",
        claim_once_authentication="not_performed",
        manifest_binding="not_performed",
        ledger_binding="not_performed",
        report_binding="not_performed",
        privacy_scan="not_performed",
        archive_verification="not_performed",
        authority_scope="none",
        canonical_run_authority=False,
        licenses_execution=False,
        licenses_later_stage=False,
    )


def inspect_standalone_bundle_reservation_v1_1(
    path: str | os.PathLike[str],
) -> StandaloneBundleReservationV11Attestation:
    """Inspect structural receipt/reservation consistency without a token."""

    try:
        return _attest(path, token_hex=None)
    except StandaloneBundleReservationV11Error:
        raise
    except Exception:
        raise StandaloneBundleReservationV11Error(
            "standalone reservation inspection failed"
        ) from None


def verify_standalone_bundle_reservation_v1_1(
    path: str | os.PathLike[str],
    token_hex: str,
) -> StandaloneBundleReservationV11Attestation:
    """Verify structural consistency plus one caller-held token capability."""

    try:
        if type(token_hex) is not str:
            _fail("reservation token syntax is invalid")
        return _attest(path, token_hex=token_hex)
    except StandaloneBundleReservationV11Error:
        raise
    except Exception:
        raise StandaloneBundleReservationV11Error(
            "standalone reservation verification failed"
        ) from None


__all__ = [
    "StandaloneBundleReservationV11Attestation",
    "StandaloneBundleReservationV11Error",
    "inspect_standalone_bundle_reservation_v1_1",
    "verify_standalone_bundle_reservation_v1_1",
]
