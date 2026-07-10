"""Noncollectable adversarial cases for the Phase-2a reservation oracle.

This support module is intentionally outside pytest's ``test_*.py`` discovery
pattern.  Run it explicitly when auditing the Phase-2a amendment:

    pytest -q tests/uprime_rpc_bundle_reservation_cases.py

Every fixture is synthetic and lives below ``tmp_path``.  The suite must never
use a registered evidence path, Lean, Git, a network endpoint, or a secret from
the environment.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import asdict, fields
import hashlib
import inspect
import json
import logging
import os
from pathlib import Path
import types
from typing import Any

import pytest

from lean_rgc.evals import uprime_rpc_bundle_reservation as bundle
from lean_rgc.evals import uprime_rpc_ledger as ledger


TOKEN = "1" * 64
CANDIDATE_COMMIT = "a" * 40
LICENSE_COMMIT = "b" * 40
LICENSE_ID = hashlib.sha256(
    b"lean-rgc-uprime-u1-attempt-v1\0" + CANDIDATE_COMMIT.encode("ascii")
).hexdigest()
ANCHOR = LICENSE_COMMIT[:12]
REMOTE_CLAIM_REF = f"refs/tags/uprime-u1-attempts/{LICENSE_ID}"
FIXED_UTC = "2026-07-11T00:00:00.000000Z"

RECEIPT_FIELDS = (
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
RESERVATION_FIELDS = (
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
PUBLIC_FIELDS = (
    "verifier_schema_version",
    "verifier_scope",
    "origin_status",
    "input_sha256",
    "input_bytes",
    "reservation_sha256",
    "reservation_artifact_name",
    "report_artifact_name",
    "ledger_artifact_name",
    "registered_run_dir",
    "candidate_commit",
    "license_commit",
    "license_id",
    "anchor",
    "remote_claim_ref",
    "claim_receipt_sha256",
    "receipt_schema_version",
    "reservation_schema_version",
    "reservation_token_verification",
    "remote_claim_authentication",
    "git_object_authentication",
    "claim_once_authentication",
    "manifest_binding",
    "ledger_binding",
    "report_binding",
    "privacy_scan",
    "archive_verification",
    "authority_scope",
    "canonical_run_authority",
    "licenses_execution",
    "licenses_later_stage",
)

# Frozen after construction from the literal fixture below.  These are kept as
# literals so an accidental change to the fixture or canonical encoder cannot
# silently bless itself.
GOLDEN_FILE_SHA256 = "2ECE05638F1F25A18D56391E5DC92E71DD1CB3101F0F9D3913C3CE40FE56E292"
GOLDEN_RECEIPT_SHA256 = "FB91FC31AF4E242F5E4ECD31718303641F3975A06EB357E78EE61020EA6F9CBE"
GOLDEN_TOKEN_SHA256 = "3138BB9BC78DF27C473ECFD1410F7BD45EBAC1F59CF3FF9CFE4DB77AAB7AEDD3"
GOLDEN_FILE_BYTES = 2273
GOLDEN_LITERAL = b'{"anchor":"bbbbbbbbbbbb","candidate_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","claim_receipt":{"candidate_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","candidate_tree_oid":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","claimed_at_utc":"2026-07-11T00:00:00.000000Z","input_manifest_sha256":"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF","license_commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","license_id":"e22ffb9f92e08af6ced16e3de16134f0a8c4e4dce8a621d8a92e52de2d60326b","registry_blob_oid":"cccccccccccccccccccccccccccccccccccccccc","registry_sha256":"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD","remote_branch_ref":"refs/heads/codex/uprime-odlrq-plan","remote_claim_oid":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","remote_claim_ref":"refs/tags/uprime-u1-attempts/e22ffb9f92e08af6ced16e3de16134f0a8c4e4dce8a621d8a92e52de2d60326b","remote_url":"https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git","schema_version":"lean-rgc-uprime-u1-claim-receipt-public-v1.0"},"claim_receipt_sha256":"FB91FC31AF4E242F5E4ECD31718303641F3975A06EB357E78EE61020EA6F9CBE","expected_frame_count":23,"expected_frame_manifest_sha256":"03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E","ledger_artifact_name":"rpc_diagnostic_bbbbbbbbbbbb.responses.jsonl","ledger_schema_version":"lean-rgc-uprime-rpc-parsed-ledger-v1.0","license_commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","license_id":"e22ffb9f92e08af6ced16e3de16134f0a8c4e4dce8a621d8a92e52de2d60326b","process_id":1234,"record_schema_version":"lean-rgc-uprime-rpc-parsed-ledger-record-v1.0","registered_run_dir":"runs/uprime_u1_rpc_20260710","remote_claim_ref":"refs/tags/uprime-u1-attempts/e22ffb9f92e08af6ced16e3de16134f0a8c4e4dce8a621d8a92e52de2d60326b","report_artifact_name":"rpc_diagnostic_bbbbbbbbbbbb.json","report_schema_version":"lean-rgc-uprime-rpc-diagnostic-v1.2","reservation_artifact_name":"rpc_diagnostic_bbbbbbbbbbbb.json.reservation","reservation_token_sha256":"3138BB9BC78DF27C473ECFD1410F7BD45EBAC1F59CF3FF9CFE4DB77AAB7AEDD3","reserved_at_utc":"2026-07-11T00:00:00.000000Z","rpc_protocol_version":"lean-rgc-jsonl-rpc-v2","schema_version":"lean-rgc-uprime-rpc-bundle-reservation-v1.1","status":"LIVE_EVIDENCE_BUNDLE_RESERVED"}\n'


def _receipt() -> dict[str, Any]:
    return {
        "schema_version": bundle.SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC,
        "candidate_commit": CANDIDATE_COMMIT,
        "license_commit": LICENSE_COMMIT,
        "license_id": LICENSE_ID,
        "remote_url": bundle.REMOTE_URL,
        "remote_branch_ref": bundle.REMOTE_BRANCH_REF,
        "remote_claim_ref": REMOTE_CLAIM_REF,
        "remote_claim_oid": LICENSE_COMMIT,
        "registry_blob_oid": "c" * 40,
        "registry_sha256": "D" * 64,
        "candidate_tree_oid": "e" * 40,
        "input_manifest_sha256": "F" * 64,
        "claimed_at_utc": FIXED_UTC,
    }


def _reservation(*, token: str = TOKEN) -> dict[str, Any]:
    receipt = _receipt()
    return {
        "schema_version": bundle.SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION,
        "status": "LIVE_EVIDENCE_BUNDLE_RESERVED",
        "anchor": ANCHOR,
        "candidate_commit": CANDIDATE_COMMIT,
        "license_commit": LICENSE_COMMIT,
        "license_id": LICENSE_ID,
        "remote_claim_ref": REMOTE_CLAIM_REF,
        "claim_receipt": receipt,
        "claim_receipt_sha256": hashlib.sha256(
            ledger.canonical_json_bytes(receipt)
        ).hexdigest().upper(),
        "registered_run_dir": bundle.REGISTERED_RUN_DIR,
        "report_artifact_name": f"rpc_diagnostic_{ANCHOR}.json",
        "ledger_artifact_name": f"rpc_diagnostic_{ANCHOR}.responses.jsonl",
        "reservation_artifact_name": f"rpc_diagnostic_{ANCHOR}.json.reservation",
        "report_schema_version": bundle.REPORT_SCHEMA_VERSION,
        "ledger_schema_version": bundle.LEDGER_SCHEMA_VERSION,
        "record_schema_version": bundle.RECORD_SCHEMA_VERSION,
        "rpc_protocol_version": bundle.RPC_PROTOCOL_VERSION,
        "expected_frame_count": bundle.EXPECTED_FRAME_COUNT,
        "expected_frame_manifest_sha256": bundle.EXPECTED_FRAME_MANIFEST_SHA256,
        "reservation_token_sha256": hashlib.sha256(
            token.encode("ascii")
        ).hexdigest().upper(),
        "reserved_at_utc": FIXED_UTC,
        "process_id": 1234,
    }


def _canonical_file_bytes(value: Any) -> bytes:
    return ledger.canonical_json_bytes(value) + b"\n"


def _reservation_path(tmp_path: Path, *, prefix: str = "synthetic-prefix") -> Path:
    return (
        tmp_path
        / prefix
        / "runs"
        / "uprime_u1_rpc_20260710"
        / f"rpc_diagnostic_{ANCHOR}.json.reservation"
    )


def _sync_receipt_digest(value: dict[str, Any]) -> None:
    receipt = value.get("claim_receipt")
    if type(receipt) is dict and "claim_receipt_sha256" in value:
        value["claim_receipt_sha256"] = hashlib.sha256(
            ledger.canonical_json_bytes(receipt)
        ).hexdigest().upper()


def _write(
    tmp_path: Path,
    *,
    value: dict[str, Any] | None = None,
    raw: bytes | None = None,
    path: Path | None = None,
    sync_receipt_digest: bool = True,
) -> tuple[Path, dict[str, Any]]:
    document = copy.deepcopy(_reservation() if value is None else value)
    if sync_receipt_digest:
        _sync_receipt_digest(document)
    destination = _reservation_path(tmp_path) if path is None else path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        _canonical_file_bytes(document) if raw is None else raw
    )
    return destination, document


def _assert_rejected(path: os.PathLike[str] | str, token: Any = TOKEN) -> None:
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, token)


def _fake_stat(value: os.stat_result, **changes: int) -> types.SimpleNamespace:
    names = (
        "st_mode",
        "st_ino",
        "st_dev",
        "st_nlink",
        "st_uid",
        "st_gid",
        "st_size",
        "st_atime",
        "st_mtime",
        "st_ctime",
        "st_atime_ns",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    values = {name: getattr(value, name) for name in names if hasattr(value, name)}
    values.update(changes)
    return types.SimpleNamespace(**values)


def test_golden_fixture_has_frozen_bytes_digest_and_exact_public_surface(
    tmp_path: Path,
) -> None:
    path, value = _write(tmp_path)
    raw = path.read_bytes()
    receipt_digest = hashlib.sha256(
        ledger.canonical_json_bytes(value["claim_receipt"])
    ).hexdigest().upper()
    assert raw == GOLDEN_LITERAL
    assert len(raw) == GOLDEN_FILE_BYTES
    assert hashlib.sha256(raw).hexdigest().upper() == GOLDEN_FILE_SHA256
    assert receipt_digest == GOLDEN_RECEIPT_SHA256
    assert value["claim_receipt_sha256"] == GOLDEN_RECEIPT_SHA256
    assert value["reservation_token_sha256"] == GOLDEN_TOKEN_SHA256
    assert hashlib.sha256(TOKEN.encode("ascii")).hexdigest().upper() == (
        GOLDEN_TOKEN_SHA256
    )

    inspected = bundle.inspect_standalone_bundle_reservation_v1_1(path)
    verified = bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert tuple(field.name for field in fields(inspected)) == PUBLIC_FIELDS
    assert type(inspected) is bundle.StandaloneBundleReservationV11Attestation
    expected = {
        "verifier_schema_version": (
            "lean-rgc-uprime-rpc-bundle-reservation-token-verifier-v0.1"
        ),
        "verifier_scope": "standalone_bundle_reservation_receipt_token_only",
        "origin_status": "unknown_may_be_synthetic",
        "input_sha256": GOLDEN_FILE_SHA256,
        "input_bytes": GOLDEN_FILE_BYTES,
        "reservation_sha256": GOLDEN_FILE_SHA256,
        "reservation_artifact_name": (
            "rpc_diagnostic_bbbbbbbbbbbb.json.reservation"
        ),
        "report_artifact_name": "rpc_diagnostic_bbbbbbbbbbbb.json",
        "ledger_artifact_name": (
            "rpc_diagnostic_bbbbbbbbbbbb.responses.jsonl"
        ),
        "registered_run_dir": "runs/uprime_u1_rpc_20260710",
        "candidate_commit": CANDIDATE_COMMIT,
        "license_commit": LICENSE_COMMIT,
        "license_id": LICENSE_ID,
        "anchor": ANCHOR,
        "remote_claim_ref": REMOTE_CLAIM_REF,
        "claim_receipt_sha256": GOLDEN_RECEIPT_SHA256,
        "receipt_schema_version": (
            "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
        ),
        "reservation_schema_version": (
            "lean-rgc-uprime-rpc-bundle-reservation-v1.1"
        ),
        "reservation_token_verification": "not_performed",
        "remote_claim_authentication": "not_performed",
        "git_object_authentication": "not_performed",
        "claim_once_authentication": "not_performed",
        "manifest_binding": "not_performed",
        "ledger_binding": "not_performed",
        "report_binding": "not_performed",
        "privacy_scan": "not_performed",
        "archive_verification": "not_performed",
        "authority_scope": "none",
        "canonical_run_authority": False,
        "licenses_execution": False,
        "licenses_later_stage": False,
    }
    assert asdict(inspected) == expected
    verified_expected = dict(expected)
    verified_expected["reservation_token_verification"] = "verified_ascii_sha256"
    assert asdict(verified) == verified_expected
    differing = {
        key for key in asdict(inspected) if asdict(inspected)[key] != asdict(verified)[key]
    }
    assert differing == {"reservation_token_verification"}
    for result in (inspected, verified):
        assert result.origin_status == "unknown_may_be_synthetic"
        assert result.authority_scope == "none"
        assert result.canonical_run_authority is False
        assert result.licenses_execution is False
        assert result.licenses_later_stage is False
        assert all(
            getattr(result, name) == "not_performed"
            for name in (
                "remote_claim_authentication",
                "git_object_authentication",
                "claim_once_authentication",
                "manifest_binding",
                "ledger_binding",
                "report_binding",
                "privacy_scan",
                "archive_verification",
            )
        )
        assert TOKEN not in repr(result)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("receipt", name) for name in RECEIPT_FIELDS]
    + [("reservation", name) for name in RESERVATION_FIELDS],
)
def test_every_required_field_is_rejected_when_missing(
    tmp_path: Path, scope: str, field: str
) -> None:
    value = _reservation()
    target = value["claim_receipt"] if scope == "receipt" else value
    del target[field]
    path, _ = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=(scope == "receipt"),
    )
    _assert_rejected(path)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("receipt", name) for name in RECEIPT_FIELDS]
    + [("reservation", name) for name in RESERVATION_FIELDS],
)
def test_every_required_field_rejects_wrong_container_type(
    tmp_path: Path, scope: str, field: str
) -> None:
    value = _reservation()
    target = value["claim_receipt"] if scope == "receipt" else value
    target[field] = []
    path, _ = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=(scope == "receipt"),
    )
    _assert_rejected(path)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("receipt", name) for name in RECEIPT_FIELDS]
    + [("reservation", name) for name in RESERVATION_FIELDS],
)
def test_every_required_field_rejects_bool_as_scalar(
    tmp_path: Path, scope: str, field: str
) -> None:
    value = _reservation()
    target = value["claim_receipt"] if scope == "receipt" else value
    target[field] = True
    path, _ = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=(scope == "receipt"),
    )
    _assert_rejected(path)


@pytest.mark.parametrize("scope", ["receipt", "reservation"])
def test_exact_objects_reject_extra_fields(tmp_path: Path, scope: str) -> None:
    value = _reservation()
    target = value["claim_receipt"] if scope == "receipt" else value
    target["attacker_extra"] = "ignored only by unsafe parsers"
    path, _ = _write(tmp_path, value=value)
    _assert_rejected(path)


def _set(value: dict[str, Any], path: str, replacement: Any) -> None:
    parts = path.split(".")
    target: dict[str, Any] = value
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = replacement


@pytest.mark.parametrize(
    ("field_path", "replacement", "sync_digest"),
    [
        ("candidate_commit", "2" * 40, True),
        ("license_commit", "2" * 40, True),
        ("license_id", "2" * 64, True),
        ("remote_claim_ref", "refs/tags/uprime-u1-attempts/" + "2" * 64, True),
        ("anchor", "2" * 12, True),
        ("claim_receipt_sha256", "2" * 64, False),
        ("claim_receipt.remote_claim_oid", "2" * 40, True),
        ("claim_receipt.remote_claim_ref", "refs/tags/uprime-u1-attempts/" + "2" * 64, True),
        ("claim_receipt.license_id", "2" * 64, True),
        ("claim_receipt.remote_url", "https://example.invalid/forged.git", True),
        ("claim_receipt.remote_branch_ref", "refs/heads/main", True),
        ("claim_receipt.schema_version", "claim-receipt-v9", True),
        ("schema_version", "bundle-reservation-v9", True),
        ("registered_run_dir", "runs/uprime_u1_rpc_20990101", True),
        ("report_artifact_name", "rpc_diagnostic_222222222222.json", True),
        ("ledger_artifact_name", "rpc_diagnostic_222222222222.responses.jsonl", True),
        ("reservation_artifact_name", "rpc_diagnostic_222222222222.json.reservation", True),
        ("report_schema_version", "lean-rgc-uprime-rpc-diagnostic-v9", True),
        ("ledger_schema_version", "lean-rgc-uprime-rpc-parsed-ledger-v9", True),
        ("record_schema_version", "lean-rgc-uprime-rpc-record-v9", True),
        ("rpc_protocol_version", "lean-rgc-jsonl-rpc-v9", True),
        ("expected_frame_count", 24, True),
        ("expected_frame_manifest_sha256", "2" * 64, True),
    ],
    ids=lambda item: str(item)[:70],
)
def test_identity_and_artifact_cross_bindings_are_fail_closed(
    tmp_path: Path,
    field_path: str,
    replacement: Any,
    sync_digest: bool,
) -> None:
    value = _reservation()
    _set(value, field_path, replacement)
    path, _ = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=sync_digest,
    )
    _assert_rejected(path)


@pytest.mark.parametrize(
    ("field_path", "replacement"),
    [
        ("claim_receipt.candidate_commit", "2" * 40),
        ("claim_receipt.license_commit", "2" * 40),
        ("claim_receipt.candidate_tree_oid", "2" * 40),
        ("claim_receipt.registry_blob_oid", "2" * 40),
        ("claim_receipt.registry_sha256", "2" * 64),
        ("claim_receipt.input_manifest_sha256", "2" * 64),
        ("claim_receipt.claimed_at_utc", "2026-07-12T00:00:00.000000Z"),
        ("reserved_at_utc", "2026-02-30T00:00:00.000000Z"),
        ("process_id", -1),
        ("process_id", 0),
    ],
)
def test_receipt_digest_and_scalar_bounds_do_not_admit_stale_or_invalid_values(
    tmp_path: Path, field_path: str, replacement: Any
) -> None:
    value = _reservation()
    _set(value, field_path, replacement)
    # Receipt changes are deliberately left with a stale digest.  Some of the
    # mutated values would otherwise be locally valid and must still fail the
    # byte-level receipt binding.
    path, _ = _write(tmp_path, value=value, sync_receipt_digest=False)
    _assert_rejected(path)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("candidate_tree_oid", "e" * 39),
        ("candidate_tree_oid", "E" * 40),
        ("candidate_tree_oid", "z" * 40),
        ("registry_blob_oid", "c" * 39),
        ("registry_blob_oid", "C" * 40),
        ("registry_blob_oid", "z" * 40),
        ("registry_sha256", "D" * 63),
        ("registry_sha256", "d" * 64),
        ("registry_sha256", "G" * 64),
        ("input_manifest_sha256", "F" * 63),
        ("input_manifest_sha256", "f" * 64),
        ("input_manifest_sha256", "G" * 64),
        ("claimed_at_utc", "2026-02-30T00:00:00.000000Z"),
        ("claimed_at_utc", "2026-07-11T00:00:00Z"),
    ],
)
def test_receipt_free_field_syntax_fails_with_a_recomputed_receipt_digest(
    tmp_path: Path, field: str, replacement: str
) -> None:
    value = _reservation()
    original_digest = value["claim_receipt_sha256"]
    value["claim_receipt"][field] = replacement
    path, written = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=True,
    )
    recomputed = hashlib.sha256(
        ledger.canonical_json_bytes(written["claim_receipt"])
    ).hexdigest().upper()
    assert written["claim_receipt_sha256"] == recomputed
    assert recomputed != original_digest
    _assert_rejected(path)


def test_correct_and_incorrect_token_paths_are_differential(tmp_path: Path) -> None:
    path, _ = _write(tmp_path)
    inspected = bundle.inspect_standalone_bundle_reservation_v1_1(path)
    verified = bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert inspected.reservation_token_verification == "not_performed"
    assert verified.reservation_token_verification == "verified_ascii_sha256"
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, "2" * 64)


@pytest.mark.parametrize(
    "token",
    [
        "",
        "1" * 63,
        "1" * 65,
        "G" * 64,
        "A" * 64,
        "é" * 64,
        b"1" * 64,
        1,
        True,
        None,
    ],
)
def test_token_syntax_is_exact_lowercase_ascii_hex64(
    tmp_path: Path, token: Any
) -> None:
    path, _ = _write(tmp_path)
    # Inspection intentionally has no token input and therefore remains valid.
    assert (
        bundle.inspect_standalone_bundle_reservation_v1_1(path).reservation_token_verification
        == "not_performed"
    )
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, token)


def test_token_digest_is_over_ascii_hex_not_decoded_bytes(tmp_path: Path) -> None:
    value = _reservation()
    value["reservation_token_sha256"] = hashlib.sha256(
        bytes.fromhex(TOKEN)
    ).hexdigest().upper()
    path, _ = _write(tmp_path, value=value)
    assert (
        bundle.inspect_standalone_bundle_reservation_v1_1(path).reservation_token_verification
        == "not_performed"
    )
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)


def test_inspect_accepts_well_formed_unknown_digest_but_verify_does_not(
    tmp_path: Path,
) -> None:
    value = _reservation()
    value["reservation_token_sha256"] = "2" * 64
    path, _ = _write(tmp_path, value=value)
    bundle.inspect_standalone_bundle_reservation_v1_1(path)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)


@pytest.mark.parametrize("stored", ["2" * 63, "2" * 65, "g" * 64, 7, True])
def test_malformed_stored_digest_is_rejected_by_both_entrypoints(
    tmp_path: Path, stored: Any
) -> None:
    value = _reservation()
    value["reservation_token_sha256"] = stored
    path, _ = _write(tmp_path, value=value)
    _assert_rejected(path)


def test_token_material_in_reservation_bytes_is_rejected(tmp_path: Path) -> None:
    token = LICENSE_ID
    value = _reservation(token=token)
    path, _ = _write(tmp_path, value=value)
    bundle.inspect_standalone_bundle_reservation_v1_1(path)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, token)


def test_token_material_in_lexical_prefix_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path, path=_reservation_path(tmp_path, prefix=TOKEN))
    real_open = bundle.os.open
    calls = 0

    def counted_open(*args: Any, **kwargs: Any) -> int:
        nonlocal calls
        calls += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr(bundle.os, "open", counted_open)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert calls == 0


def test_wrong_token_never_leaks_through_results_errors_logs_or_stdio(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, _ = _write(tmp_path)
    wrong = "23456789abcdef" * 4 + "23456789"
    assert len(wrong) == 64
    caplog.set_level(logging.DEBUG)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error) as caught:
        bundle.verify_standalone_bundle_reservation_v1_1(path, wrong)
    captured = capsys.readouterr()
    haystacks = (
        str(caught.value),
        repr(caught.value),
        captured.out,
        captured.err,
        caplog.text,
    )
    assert all(wrong not in text for text in haystacks)
    assert TOKEN not in repr(bundle.inspect_standalone_bundle_reservation_v1_1(path))


def _noncanonical_raw_cases(value: dict[str, Any]) -> list[tuple[str, bytes]]:
    canonical = ledger.canonical_json_bytes(value)
    parsed = json.loads(canonical)
    reversed_object = dict(reversed(list(parsed.items())))
    reverse_order = json.dumps(
        reversed_object,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    duplicate_key = b'{"anchor":"222222222222",' + canonical[1:] + b"\n"
    float_value = canonical.replace(b'"process_id":1234', b'"process_id":1.5') + b"\n"
    nan_value = canonical.replace(b'"process_id":1234', b'"process_id":NaN') + b"\n"
    infinity_value = canonical.replace(
        b'"process_id":1234', b'"process_id":Infinity'
    ) + b"\n"
    surrogate = canonical.replace(
        b'"status":"LIVE_EVIDENCE_BUNDLE_RESERVED"',
        b'"status":"\\ud800"',
    ) + b"\n"
    return [
        ("utf8-bom", b"\xef\xbb\xbf" + canonical + b"\n"),
        ("crlf", canonical + b"\r\n"),
        ("missing-terminal-lf", canonical),
        ("two-terminal-lf", canonical + b"\n\n"),
        ("leading-space", b" " + canonical + b"\n"),
        ("trailing-space", canonical + b" \n"),
        ("embedded-lf", canonical[:10] + b"\n" + canonical[10:] + b"\n"),
        ("reverse-key-order", reverse_order),
        ("duplicate-key", duplicate_key),
        ("multiple-json-values", canonical + b"{}\n"),
        ("float", float_value),
        ("nan", nan_value),
        ("infinity", infinity_value),
        ("surrogate", surrogate),
        ("trailing-nul", canonical + b"\x00\n"),
        ("invalid-utf8", canonical[:-1] + b"\xff}\n"),
    ]


@pytest.mark.parametrize("case_index", range(16))
def test_noncanonical_encodings_are_rejected(
    tmp_path: Path, case_index: int
) -> None:
    value = _reservation()
    name, raw = _noncanonical_raw_cases(value)[case_index]
    path, _ = _write(tmp_path, value=value, raw=raw)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        # Referencing the label makes a parametrized failure legible without
        # weakening the shared rejection assertion.
        assert name
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


@pytest.mark.parametrize("length", [31, 32, 33])
def test_bounded_reader_accepts_n_minus_one_and_n_but_rejects_n_plus_one(
    tmp_path: Path, length: int
) -> None:
    path = tmp_path / f"bounded-{length}.bin"
    path.write_bytes(b"x" * length)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        if length <= 32:
            assert bundle._read_bounded_fd(
                fd, expected_size=length, max_bytes=32
            ) == b"x" * length
        else:
            with pytest.raises(bundle.StandaloneBundleReservationV11Error):
                bundle._read_bounded_fd(fd, expected_size=length, max_bytes=32)
    finally:
        os.close(fd)


def test_process_id_accepts_the_positive_signed64_maximum(tmp_path: Path) -> None:
    value = _reservation()
    value["process_id"] = 2**63 - 1
    path, _ = _write(tmp_path, value=value)
    bundle.inspect_standalone_bundle_reservation_v1_1(path)
    bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)


def test_process_id_rejects_signed64_maximum_plus_one_from_raw_bytes(
    tmp_path: Path,
) -> None:
    raw = GOLDEN_LITERAL.replace(
        b'"process_id":1234',
        b'"process_id":9223372036854775808',
    )
    assert raw != GOLDEN_LITERAL
    path, _ = _write(tmp_path, raw=raw)
    _assert_rejected(path)


def test_preallocated_oversized_file_is_rejected_before_any_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _reservation_path(tmp_path)
    path.parent.mkdir(parents=True)
    with path.open("wb") as stream:
        stream.seek(bundle.MAX_RESERVATION_BYTES)
        stream.write(b"x")
    calls = 0

    def forbidden_read(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("oversized input must fail before read")

    monkeypatch.setattr(bundle.os, "read", forbidden_read)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)
    assert calls == 0


def test_canonical_suffix_accepts_native_and_forward_slash_lexemes(
    tmp_path: Path,
) -> None:
    path, _ = _write(tmp_path)
    bundle.inspect_standalone_bundle_reservation_v1_1(str(path))
    bundle.inspect_standalone_bundle_reservation_v1_1(str(path).replace("\\", "/"))


class _BytesReturningPath:
    def __init__(self, value: bytes) -> None:
        self.value = value

    def __fspath__(self) -> bytes:
        return self.value


@pytest.mark.parametrize("wrapped", [False, True])
def test_bytes_paths_and_pathlike_objects_returning_bytes_are_rejected(
    tmp_path: Path, wrapped: bool
) -> None:
    path, _ = _write(tmp_path)
    raw_bytes = os.fsencode(path)
    candidate: Any = _BytesReturningPath(raw_bytes) if wrapped else raw_bytes
    _assert_rejected(candidate)


@pytest.mark.parametrize(
    "variant",
    [
        "dot",
        "traversal",
        "duplicate-separator",
        "trailing-separator",
        "run-dir-case",
        "registered-dir-case",
        "filename-case",
        "trailing-dot-normalization",
        "trailing-space-normalization",
    ],
)
def test_lexical_path_variants_are_rejected_even_if_windows_resolves_them(
    tmp_path: Path, variant: str
) -> None:
    path, _ = _write(tmp_path)
    raw = str(path)
    separator = os.sep if os.sep in raw else ("\\" if "\\" in raw else "/")
    run_marker = f"{separator}runs{separator}"
    registered_marker = f"uprime_u1_rpc_20260710{separator}"
    assert run_marker in raw
    assert registered_marker in raw
    if variant == "dot":
        candidate = f"{path.parent}{separator}.{separator}{path.name}"
    elif variant == "traversal":
        junk = path.parent.parent / "junk"
        junk.mkdir()
        candidate = (
            f"{junk}{separator}..{separator}"
            f"uprime_u1_rpc_20260710{separator}{path.name}"
        )
    elif variant == "duplicate-separator":
        candidate = raw.replace(
            run_marker,
            f"{separator}runs{separator}{separator}",
        )
    elif variant == "trailing-separator":
        candidate = raw + separator
    elif variant == "run-dir-case":
        candidate = raw.replace(
            run_marker,
            f"{separator}Runs{separator}",
        )
    elif variant == "registered-dir-case":
        candidate = raw.replace("uprime_u1_rpc_20260710", "UPRIME_U1_RPC_20260710")
    elif variant == "trailing-dot-normalization":
        candidate = raw.replace(
            registered_marker,
            f"uprime_u1_rpc_20260710.{separator}",
        )
    elif variant == "trailing-space-normalization":
        candidate = raw.replace(
            registered_marker,
            f"uprime_u1_rpc_20260710 {separator}",
        )
    else:
        candidate = raw[:-1] + raw[-1].upper()
    assert candidate != raw
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(candidate)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("report_artifact_name", "sub/rpc.json"),
        ("report_artifact_name", "sub\\rpc.json"),
        ("report_artifact_name", "/rpc.json"),
        ("report_artifact_name", "C:rpc.json"),
        ("report_artifact_name", "\\\\server\\share\\rpc.json"),
        ("report_artifact_name", "RPC_DIAGNOSTIC_bbbbbbbbbbbb.json"),
        ("report_artifact_name", "rpc_diagnostic_bbbbbbbbbbbb-é.json"),
        ("ledger_artifact_name", "../responses.jsonl"),
        ("ledger_artifact_name", "responses.JSONL"),
        ("reservation_artifact_name", "./reservation"),
        ("reservation_artifact_name", "rpc_diagnostic_bbbbbbbbbbbb.json.RESERVATION"),
        ("reservation_artifact_name", "é.reservation"),
    ],
)
def test_artifact_fields_are_exact_ascii_basenames(
    tmp_path: Path, field: str, bad_value: str
) -> None:
    value = _reservation()
    value[field] = bad_value
    path, _ = _write(tmp_path, value=value)
    _assert_rejected(path)


def test_on_disk_filename_must_equal_embedded_reservation_name(
    tmp_path: Path,
) -> None:
    wrong_path = (
        _reservation_path(tmp_path).parent
        / f"rpc_diagnostic_{ANCHOR}.json.reservation.other"
    )
    path, _ = _write(tmp_path, path=wrong_path)
    _assert_rejected(path)


def test_on_disk_filename_anchor_must_equal_embedded_anchor(tmp_path: Path) -> None:
    wrong_path = (
        _reservation_path(tmp_path).parent
        / "rpc_diagnostic_222222222222.json.reservation"
    )
    path, _ = _write(tmp_path, path=wrong_path)
    _assert_rejected(path)


def test_final_component_identity_change_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_stat = bundle.os.stat

    def changed_final_stat(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        observed = real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if not follow_symlinks and os.fspath(target) == os.fspath(path):
            return _fake_stat(observed, st_ino=int(observed.st_ino) + 1)
        return observed

    monkeypatch.setattr(bundle.os, "stat", changed_final_stat)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


def test_final_component_nonregular_reparse_result_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_stat = bundle.os.stat

    def nonregular_final_stat(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        observed = real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if not follow_symlinks and os.fspath(target) == os.fspath(path):
            return _fake_stat(observed, st_mode=0o040755)
        return observed

    monkeypatch.setattr(bundle.os, "stat", nonregular_final_stat)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


def test_snapshot_uses_the_exact_frozen_observation_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_open = bundle.os.open
    real_lseek = bundle.os.lseek
    real_fstat = bundle.os.fstat
    real_close = bundle.os.close
    real_stat = bundle.os.stat
    expected_path = os.path.normcase(os.path.abspath(os.fspath(path)))
    expected_flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    tracked_fd: int | None = None
    calls = {
        "open": 0,
        "lseek": 0,
        "fstat": 0,
        "close": 0,
        "final_no_follow_stat": 0,
    }

    def counted_open(target: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal tracked_fd
        calls["open"] += 1
        assert os.path.normcase(os.path.abspath(os.fspath(target))) == expected_path
        assert flags == expected_flags
        tracked_fd = real_open(target, flags, *args, **kwargs)
        return tracked_fd

    def counted_lseek(fd: int, offset: int, whence: int) -> int:
        if fd == tracked_fd:
            calls["lseek"] += 1
            assert offset == 0
            assert whence == os.SEEK_SET
        return real_lseek(fd, offset, whence)

    def counted_fstat(fd: int) -> os.stat_result:
        if fd == tracked_fd:
            calls["fstat"] += 1
        return real_fstat(fd)

    def counted_close(fd: int) -> None:
        if fd == tracked_fd:
            calls["close"] += 1
        real_close(fd)

    def counted_stat(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> os.stat_result:
        if (
            os.path.normcase(os.path.abspath(os.fspath(target))) == expected_path
            and follow_symlinks is False
        ):
            calls["final_no_follow_stat"] += 1
        return real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(bundle.os, "open", counted_open)
    monkeypatch.setattr(bundle.os, "lseek", counted_lseek)
    monkeypatch.setattr(bundle.os, "fstat", counted_fstat)
    monkeypatch.setattr(bundle.os, "close", counted_close)
    monkeypatch.setattr(bundle.os, "stat", counted_stat)
    bundle.inspect_standalone_bundle_reservation_v1_1(path)
    assert calls == {
        "open": 1,
        "lseek": 2,
        "fstat": 3,
        "close": 1,
        "final_no_follow_stat": 1,
    }


@pytest.mark.parametrize(
    ("operation", "failure_call"),
    [
        ("open", 1),
        ("fstat", 1),
        ("fstat", 2),
        ("fstat", 3),
        ("lseek", 1),
        ("lseek", 2),
        ("read", 1),
        ("read", 2),
        ("read", 3),
        ("read", 4),
        ("close", 1),
        ("stat", 1),
    ],
)
def test_each_observation_io_failure_is_public_token_safe_and_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    operation: str,
    failure_call: int,
) -> None:
    path, _ = _write(tmp_path)
    original = getattr(bundle.os, operation)
    call_count = 0

    if operation == "stat":

        def injected_stat(
            target: Any,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> os.stat_result:
            nonlocal call_count
            if follow_symlinks is False:
                call_count += 1
                if call_count == failure_call:
                    raise OSError("injected final no-follow stat failure")
            return original(
                target,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )

        monkeypatch.setattr(bundle.os, operation, injected_stat)
    elif operation == "close":

        def injected_close(fd: int) -> None:
            nonlocal call_count
            call_count += 1
            original(fd)
            if call_count == failure_call:
                raise OSError("injected close failure")

        monkeypatch.setattr(bundle.os, operation, injected_close)
    else:

        def injected_call(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == failure_call:
                raise OSError(f"injected {operation} failure")
            return original(*args, **kwargs)

        monkeypatch.setattr(bundle.os, operation, injected_call)

    caplog.set_level(logging.DEBUG)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error) as caught:
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    captured = capsys.readouterr()
    assert call_count == failure_call
    assert TOKEN not in str(caught.value)
    assert TOKEN not in repr(caught.value)
    assert TOKEN not in caplog.text
    assert TOKEN not in captured.out
    assert TOKEN not in captured.err


def test_short_observation_is_rejected_by_the_bounded_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_read = bundle.os.read
    calls = 0

    def short_first_data_read(fd: int, count: int) -> bytes:
        nonlocal calls
        calls += 1
        chunk = real_read(fd, count)
        if calls == 1:
            assert chunk
            return chunk[:-1]
        return chunk

    monkeypatch.setattr(bundle.os, "read", short_first_data_read)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error) as caught:
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert calls == 2
    assert TOKEN not in str(caught.value)
    assert TOKEN not in repr(caught.value)


def test_same_size_mutation_between_same_fd_passes_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    original = path.read_bytes()
    mutated = original.replace(b'"process_id":1234', b'"process_id":4321')
    assert len(mutated) == len(original) and mutated != original
    real_reader = bundle._read_bounded_fd
    calls = 0

    def mutate_after_first_read(
        fd: int, *, expected_size: int, max_bytes: int = bundle.MAX_RESERVATION_BYTES
    ) -> bytes:
        nonlocal calls
        result = real_reader(fd, expected_size=expected_size, max_bytes=max_bytes)
        calls += 1
        if calls == 1:
            with path.open("r+b") as stream:
                stream.write(mutated)
                stream.flush()
                os.fsync(stream.fileno())
        return result

    monkeypatch.setattr(bundle, "_read_bounded_fd", mutate_after_first_read)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)
    assert calls == 2


def test_metadata_drift_during_same_fd_observation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_fstat = bundle.os.fstat
    calls = 0

    def drifting_fstat(fd: int) -> Any:
        nonlocal calls
        calls += 1
        observed = real_fstat(fd)
        if calls >= 2:
            return _fake_stat(observed, st_mtime_ns=int(observed.st_mtime_ns) + 1)
        return observed

    monkeypatch.setattr(bundle.os, "fstat", drifting_fstat)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


def test_path_disappearance_after_close_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    real_close = bundle.os.close

    def close_then_unlink(fd: int) -> None:
        real_close(fd)
        path.unlink()

    monkeypatch.setattr(bundle.os, "close", close_then_unlink)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


def test_path_replacement_after_close_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    replacement = tmp_path / "replacement.bin"
    replacement.write_bytes(path.read_bytes())
    real_close = bundle.os.close

    def close_then_replace(fd: int) -> None:
        real_close(fd)
        os.replace(replacement, path)

    monkeypatch.setattr(bundle.os, "close", close_then_replace)
    with pytest.raises(bundle.StandaloneBundleReservationV11Error):
        bundle.inspect_standalone_bundle_reservation_v1_1(path)


def _legacy_documents() -> list[tuple[str, dict[str, Any]]]:
    current = _reservation()
    version = copy.deepcopy(current)
    version["schema_version"] = "lean-rgc-uprime-rpc-bundle-reservation-v1.0"
    status = copy.deepcopy(current)
    status["status"] = "LIVE_EXECUTION_RESERVED"
    raw_token = copy.deepcopy(current)
    raw_token["token"] = TOKEN
    legacy_shape = {
        "schema_version": "lean-rgc-uprime-rpc-reservation-v1.0",
        "status": "LIVE_EXECUTION_RESERVED",
        "anchor": ANCHOR,
        "anchor_commit": LICENSE_COMMIT,
        "reserved_at_utc": FIXED_UTC,
        "process_id": 1234,
        "final_artifact_name": f"rpc_diagnostic_{ANCHOR}.json",
        "token": TOKEN,
    }
    migration = copy.deepcopy(current)
    migration["migrate_from"] = "v1.0"
    fallback = copy.deepcopy(current)
    fallback["accept_legacy_fallback"] = True
    autodetect = copy.deepcopy(current)
    autodetect["schema_version"] = [
        bundle.SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION,
        "lean-rgc-uprime-rpc-bundle-reservation-v1.0",
    ]
    return [
        ("v1.0-schema", version),
        ("legacy-status", status),
        ("raw-token-field", raw_token),
        ("legacy-shape", legacy_shape),
        ("migration", migration),
        ("fallback", fallback),
        ("schema-autodetection", autodetect),
    ]


@pytest.mark.parametrize("case_index", range(7))
def test_legacy_compatibility_migration_and_autodetection_are_hard_rejected(
    tmp_path: Path, case_index: int
) -> None:
    label, value = _legacy_documents()[case_index]
    path, _ = _write(
        tmp_path,
        value=value,
        sync_receipt_digest=False,
    )
    assert label
    _assert_rejected(path)


def test_public_signatures_expose_only_path_and_caller_held_token() -> None:
    inspect_signature = inspect.signature(
        bundle.inspect_standalone_bundle_reservation_v1_1
    )
    verify_signature = inspect.signature(
        bundle.verify_standalone_bundle_reservation_v1_1
    )
    assert tuple(inspect_signature.parameters) == ("path",)
    assert tuple(verify_signature.parameters) == ("path", "token_hex")
    assert all(
        parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for parameter in inspect_signature.parameters.values()
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in inspect_signature.parameters.values()
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in verify_signature.parameters.values()
    )
    assert bundle.__all__ == [
        "StandaloneBundleReservationV11Attestation",
        "StandaloneBundleReservationV11Error",
        "inspect_standalone_bundle_reservation_v1_1",
        "verify_standalone_bundle_reservation_v1_1",
    ]


@pytest.mark.parametrize(
    "forged",
    [
        {"receipt": _receipt()},
        {"expected_commit": CANDIDATE_COMMIT},
        {"expected_license_commit": LICENSE_COMMIT},
        {"report": {}},
        {"manifest": {}},
        {"authority": True},
        {"precomputed_digest": "2" * 64},
        {"remote_claim": {}},
        {"canonical_run_authority": True},
    ],
)
def test_public_api_rejects_caller_supplied_authority_or_evidence(
    tmp_path: Path, forged: dict[str, Any]
) -> None:
    path, _ = _write(tmp_path)
    with pytest.raises(TypeError):
        bundle.inspect_standalone_bundle_reservation_v1_1(path, **forged)
    with pytest.raises(TypeError):
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN, **forged)


def test_public_api_rejects_extra_positional_context(tmp_path: Path) -> None:
    path, _ = _write(tmp_path)
    with pytest.raises(TypeError):
        bundle.inspect_standalone_bundle_reservation_v1_1(path, _receipt())
    with pytest.raises(TypeError):
        bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN, {})


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            targets.add(node.module or "")
    return targets


def test_module_ast_has_only_the_frozen_read_only_dependency_set() -> None:
    source_path = Path(bundle.__file__).resolve()
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    assert _import_targets(tree) == {
        "__future__",
        "dataclasses",
        "datetime",
        "hashlib",
        "hmac",
        "os",
        "re",
        "stat",
        "typing",
        "lean_rgc.evals.uprime_rpc_ledger",
    }
    forbidden_import_roots = {
        "subprocess",
        "socket",
        "urllib",
        "http",
        "requests",
        "git",
        "pygit2",
        "paramiko",
        "secrets",
        "tempfile",
    }
    assert not {
        target.split(".", 1)[0] for target in _import_targets(tree)
    }.intersection(forbidden_import_roots)
    forbidden_os_calls = {
        "system",
        "popen",
        "spawnl",
        "spawnv",
        "write",
        "replace",
        "rename",
        "unlink",
        "remove",
        "mkdir",
        "makedirs",
        "fsync",
    }
    observed_os_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
    }
    assert not observed_os_calls.intersection(forbidden_os_calls)
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom))
        for node in ast.walk(tree)
    )


def test_production_and_phase1_raising_sentinels_are_never_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lean_rgc.evals import uprime_rpc_contract_oracle as contract_oracle
    from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics
    from lean_rgc.evals import uprime_rpc_litmus as litmus

    path, _ = _write(tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("production or phase-1 capability was reached")

    monkeypatch.setattr(litmus, "run_diagnostic", forbidden)
    monkeypatch.setattr(litmus, "_reserve_output", forbidden)
    monkeypatch.setattr(litmus, "_publish_reserved_json", forbidden)
    monkeypatch.setattr(contract_oracle, "attest_standalone_exact_49_contracts", forbidden)
    monkeypatch.setattr(semantics, "attest_standalone_nominal_49_semantics", forbidden)
    inspected = bundle.inspect_standalone_bundle_reservation_v1_1(path)
    verified = bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert inspected.licenses_execution is False
    assert verified.licenses_execution is False


def test_no_write_publication_process_or_registered_path_capability_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _write(tmp_path)
    before = {item: item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}
    real_open = bundle.os.open
    opened: list[Path] = []

    def read_only_tmp_open(target: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        candidate = Path(os.path.abspath(os.fspath(target)))
        opened.append(candidate)
        assert candidate.is_relative_to(tmp_path.resolve())
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT)
        return real_open(target, flags, *args, **kwargs)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("write/publication/process capability was reached")

    monkeypatch.setattr(bundle.os, "open", read_only_tmp_open)
    for name in (
        "write",
        "replace",
        "rename",
        "unlink",
        "remove",
        "mkdir",
        "makedirs",
        "fsync",
        "system",
        "popen",
    ):
        monkeypatch.setattr(bundle.os, name, forbidden, raising=False)
    result = bundle.verify_standalone_bundle_reservation_v1_1(path, TOKEN)
    assert result.licenses_execution is False
    assert opened == [path.resolve()]
    after = {item: item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}
    assert after == before
    assert TOKEN.encode("ascii") not in path.read_bytes()
    assert TOKEN not in repr(result)


def _write_default_deny_registry(root: Path) -> None:
    from lean_rgc.evals.uprime_rerun_license import (
        RERUN_REGISTRY_PATH,
        SCHEMA_UPRIME_RERUN_REGISTRY,
        canonical_registry_bytes,
    )

    target = root / RERUN_REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        canonical_registry_bytes(
            {
                "default_allow": False,
                "licenses": {},
                "schema_version": SCHEMA_UPRIME_RERUN_REGISTRY,
            }
        )
    )


def _mock_formal_git_preflight(
    monkeypatch: pytest.MonkeyPatch, litmus: Any, commit: str
) -> None:
    monkeypatch.setattr(litmus, "_assert_git_top_level", lambda _root: None)
    monkeypatch.setattr(litmus, "_git_commit", lambda _root: commit)
    monkeypatch.setattr(litmus, "_assert_anchor_inputs_clean", lambda _root: None)
    monkeypatch.setattr(
        litmus,
        "_assert_anchor_pushed",
        lambda _root, _commit: "origin/codex/uprime-odlrq-plan",
    )


def test_formal_main_and_runner_remain_default_denied_before_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lean_rgc.evals import uprime_rpc_litmus as litmus
    from lean_rgc.evals.uprime_rerun_license import UPrimeRerunLicenseError

    commit = "a" * 40
    anchor = commit[:12]
    _write_default_deny_registry(tmp_path)
    _mock_formal_git_preflight(monkeypatch, litmus, commit)
    out = tmp_path / litmus.REGISTERED_RUN_DIR / f"rpc_diagnostic_{anchor}.json"

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("reservation, verifier, or worker boundary was reached")

    monkeypatch.setattr(litmus, "_reserve_output", forbidden)
    monkeypatch.setattr(litmus, "_verify_reservation", forbidden)
    monkeypatch.setattr(litmus, "_RpcProcess", forbidden)
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus.main(
            [
                "--repo-root",
                str(tmp_path),
                "--anchor",
                anchor,
                "--out",
                str(out),
            ]
        )
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus.run_diagnostic(
            tmp_path,
            anchor=anchor,
            reservation_path=out,
            reservation_token="unused",
        )
    assert not out.exists()
    assert not litmus._reservation_file(out).exists()


def test_legacy_reservation_and_publication_helpers_remain_default_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lean_rgc.evals import uprime_rpc_litmus as litmus
    from lean_rgc.evals.uprime_rerun_license import UPrimeRerunLicenseError

    commit = "c" * 40
    anchor = commit[:12]
    _write_default_deny_registry(tmp_path)
    out = tmp_path / litmus.REGISTERED_RUN_DIR / f"rpc_diagnostic_{anchor}.json"
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus._reserve_output(
            out,
            repo_root=tmp_path,
            anchor=anchor,
            commit=commit,
        )

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("legacy verifier or publication write was reached")

    monkeypatch.setattr(litmus, "_verify_reservation", forbidden)
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus._publish_reserved_json(
            out,
            {"verdict": "fabricated"},
            repo_root=tmp_path,
            token="unused",
            anchor=anchor,
            commit=commit,
        )
    assert not out.parent.exists()
