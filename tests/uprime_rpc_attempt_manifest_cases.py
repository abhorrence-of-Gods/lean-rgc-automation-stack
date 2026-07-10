"""Noncollectable Phase-2b1 local attempt-manifest acceptance cases.

The anchored collector imports only the ``test_uprime_attempt_manifest_*``
callables exported by ``__all__``.  Every filesystem fixture is synthetic and
is created below pytest's ``tmp_path``.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError, asdict, fields
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import types
from typing import Any

import pytest

from lean_rgc.evals import uprime_rpc_attempt_manifest as manifest
from lean_rgc.evals import uprime_rpc_ledger as ledger


CANDIDATE_COMMIT = "a" * 40
LICENSE_COMMIT = "b" * 40
LICENSE_ID = hashlib.sha256(
    b"lean-rgc-uprime-u1-attempt-v1\0" + CANDIDATE_COMMIT.encode("ascii")
).hexdigest()
REMOTE_CLAIM_REF = f"refs/tags/uprime-u1-attempts/{LICENSE_ID}"
RECEIPT_UTC = "2026-07-11T00:00:00.000000Z"
CLAIM_UTC = "2026-07-11T00:00:01.000000Z"
TERMINAL_UTC = "2026-07-11T00:00:02.000000Z"

GOLDEN_RECEIPT_BYTES = 934
GOLDEN_RECEIPT_SHA256 = "FB91FC31AF4E242F5E4ECD31718303641F3975A06EB357E78EE61020EA6F9CBE"
GOLDEN_RECEIPT_WITH_LF_SHA256 = (
    "50E55663B9DBC132E61DAB9476BC32E1DDD8B9E5039218B48A1B76D922CAA1CE"
)
GOLDEN_CLAIM_FILE_BYTES = 1972
GOLDEN_CLAIM_SHA256 = "140355436BCE449D602253E7DB9EFD428BF4E90AAF07DDBE31AF019991C73A92"
GOLDEN_CLAIM_WITHOUT_LF_SHA256 = (
    "7438AEE6B5A4C248B65BAEA86015A6E954ABAAFD1E217EC0B76214C3BA6BE52E"
)

RECEIPT_FIELDS = (
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
EVENT_FIELDS = (
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
EVENT_FILE_FIELDS = (
    "repository_path",
    "event_sha256",
    "event_bytes",
    "event",
)
INSPECTION_FIELDS = (
    "inspector_schema_version",
    "inspector_scope",
    "origin_status",
    "license_id",
    "chain_state",
    "event_files",
    "event_count",
    "first_event_sha256",
    "last_event_index",
    "last_event_sha256",
    "last_event_type",
    "terminal_event",
    "recorded_verdict",
    "next_event_index",
    "claim_receipt",
    "claim_receipt_sha256",
)
ATTESTATION_FIELDS = (
    "verifier_schema_version",
    "verifier_scope",
    "origin_status",
    "license_id",
    "candidate_commit",
    "license_commit",
    "remote_claim_ref",
    "claim_receipt_sha256",
    "event_count",
    "first_event_sha256",
    "last_event_index",
    "last_event_sha256",
    "chain_state",
    "terminal_event",
    "last_event_type",
    "recorded_verdict",
    "failure_codes",
    "preartifact_profile",
    "artifact_observation",
    "remote_claim_authentication",
    "git_object_authentication",
    "real_remote_publication",
    "claim_once_authentication",
    "reservation_token_verification",
    "artifact_binding",
    "verifier_binding",
    "scanner_binding",
    "privacy_scan",
    "archive_verification",
    "authority_scope",
    "canonical_run_authority",
    "licenses_execution",
    "licenses_later_stage",
)
FROZEN_FAILURE_CODES = (
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


def _receipt_mapping(
    *,
    candidate_commit: str = CANDIDATE_COMMIT,
    license_commit: str = LICENSE_COMMIT,
    claimed_at_utc: str = RECEIPT_UTC,
) -> dict[str, Any]:
    license_id = hashlib.sha256(
        b"lean-rgc-uprime-u1-attempt-v1\0" + candidate_commit.encode("ascii")
    ).hexdigest()
    return {
        "schema_version": "lean-rgc-uprime-u1-claim-receipt-public-v1.0",
        "candidate_commit": candidate_commit,
        "license_commit": license_commit,
        "license_id": license_id,
        "remote_url": (
            "https://github.com/abhorrence-of-Gods/"
            "lean-rgc-automation-stack.git"
        ),
        "remote_branch_ref": "refs/heads/codex/uprime-odlrq-plan",
        "remote_claim_ref": f"refs/tags/uprime-u1-attempts/{license_id}",
        "remote_claim_oid": license_commit,
        "registry_blob_oid": "c" * 40,
        "registry_sha256": "D" * 64,
        "candidate_tree_oid": "e" * 40,
        "input_manifest_sha256": "F" * 64,
        "claimed_at_utc": claimed_at_utc,
    }


def _receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(ledger.canonical_json_bytes(receipt)).hexdigest().upper()


def _event_mapping(
    event_type: str = "claim_started",
    *,
    event_index: int = 1,
    created_at_utc: str = CLAIM_UTC,
    receipt: dict[str, Any] | None = None,
    prior_event_sha256: str | None = None,
    terminal_event: bool | None = None,
    failure_codes: list[str] | None = None,
) -> dict[str, Any]:
    public_receipt = copy.deepcopy(_receipt_mapping() if receipt is None else receipt)
    if event_type == "claim_started":
        terminal = False if terminal_event is None else terminal_event
        failures = [] if failure_codes is None else list(failure_codes)
        verdict: str | None = None
    elif event_type == "attempt_finished":
        terminal = True if terminal_event is None else terminal_event
        failures = ["WORKER_TIMEOUT"] if failure_codes is None else list(failure_codes)
        verdict = "HARNESS_ERROR"
    elif event_type == "recovery":
        terminal = True if terminal_event is None else terminal_event
        failures = ["POWER_LOSS"] if failure_codes is None else list(failure_codes)
        verdict = None
    else:
        terminal = False if terminal_event is None else terminal_event
        failures = [] if failure_codes is None else list(failure_codes)
        verdict = None
    if event_index > 1 and prior_event_sha256 is None:
        prior_event_sha256 = "A" * 64
    return {
        "schema_version": "lean-rgc-uprime-u1-attempt-manifest-v1.0",
        "event_type": event_type,
        "event_index": event_index,
        "created_at_utc": created_at_utc,
        "license_id": public_receipt["license_id"],
        "candidate_commit": public_receipt["candidate_commit"],
        "license_commit": public_receipt["license_commit"],
        "remote_claim_ref": public_receipt["remote_claim_ref"],
        "claim_receipt": public_receipt,
        "claim_receipt_sha256": _receipt_sha256(public_receipt),
        "prior_event_sha256": prior_event_sha256,
        "reservation_exists": False,
        "ledger_exists": False,
        "report_exists": False,
        "reservation_sha256": None,
        "reservation_bytes": None,
        "ledger_sha256": None,
        "ledger_bytes": None,
        "report_sha256": None,
        "report_bytes": None,
        "ledger_inspection_status": "absent",
        "ledger_sequence_status": None,
        "verifier_status": "not_run",
        "scanner_status": "not_run",
        "scanner_rule_ids": [],
        "verdict": verdict,
        "failure_codes": failures,
        "full_ledger_published": False,
        "terminal_event": terminal,
    }


def _canonical_event_file(value: dict[str, Any]) -> bytes:
    return ledger.canonical_json_bytes(value) + b"\n"


def _event_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _repository_path(license_id: str, event_index: int) -> str:
    return (
        "docs/experiments/artifacts/uprime_u1_rpc_attempts/"
        f"{license_id}/{event_index:04d}.json"
    )


def _host_event_path(root: Path, license_id: str, event_index: int) -> Path:
    return (
        root
        / "docs"
        / "experiments"
        / "artifacts"
        / "uprime_u1_rpc_attempts"
        / license_id
        / f"{event_index:04d}.json"
    )


def _receipt_record(receipt: dict[str, Any] | None = None) -> Any:
    return manifest.PublicClaimReceiptV10(
        **copy.deepcopy(_receipt_mapping() if receipt is None else receipt)
    )


def _event_record(value: dict[str, Any] | None = None) -> Any:
    mapping = copy.deepcopy(_event_mapping() if value is None else value)
    mapping["claim_receipt"] = _receipt_record(mapping["claim_receipt"])
    mapping["scanner_rule_ids"] = tuple(mapping["scanner_rule_ids"])
    mapping["failure_codes"] = tuple(mapping["failure_codes"])
    return manifest.AttemptManifestEventV10(**mapping)


def _write_chain(
    tmp_path: Path,
    values: list[dict[str, Any]],
    *,
    root_name: str = "synthetic-sandbox",
) -> tuple[Path, list[dict[str, Any]], list[bytes]]:
    root = (tmp_path / root_name).absolute()
    documents: list[dict[str, Any]] = []
    raws: list[bytes] = []
    previous_sha: str | None = None
    for original in values:
        value = copy.deepcopy(original)
        value["claim_receipt_sha256"] = _receipt_sha256(value["claim_receipt"])
        value["prior_event_sha256"] = previous_sha
        raw = _canonical_event_file(value)
        destination = _host_event_path(
            root,
            value["license_id"],
            value["event_index"],
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        documents.append(value)
        raws.append(raw)
        previous_sha = _event_sha256(raw)
    return root, documents, raws


def _valid_chain_values(count: int) -> list[dict[str, Any]]:
    assert count >= 1
    values = [_event_mapping()]
    for index in range(2, count + 1):
        terminal = index == count
        values.append(
            _event_mapping(
                "recovery",
                event_index=index,
                created_at_utc=f"2026-07-11T00:00:{index:02d}.000000Z",
                terminal_event=terminal,
                failure_codes=["POWER_LOSS" if terminal else "READER_ERROR"],
            )
        )
    return values


def _assert_parse_rejected(
    value: dict[str, Any],
    *,
    repository_path: str | None = None,
) -> None:
    path = _repository_path(LICENSE_ID, 1)
    if repository_path is not None:
        path = repository_path
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.parse_attempt_manifest_event_file_v1_0(
            path,
            _canonical_event_file(value),
        )


def _fake_stat(value: os.stat_result, **changes: int) -> types.SimpleNamespace:
    names = (
        "st_mode",
        "st_ino",
        "st_dev",
        "st_size",
        "st_mtime",
        "st_ctime",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_file_attributes",
    )
    data = {name: getattr(value, name) for name in names if hasattr(value, name)}
    data.update(changes)
    return types.SimpleNamespace(**data)


def test_uprime_attempt_manifest_golden_claim_schema_path_and_hash() -> None:
    receipt = _receipt_mapping()
    value = _event_mapping()
    receipt_bytes = ledger.canonical_json_bytes(receipt)
    raw = _canonical_event_file(value)
    repository_path = _repository_path(LICENSE_ID, 1)

    assert len(receipt_bytes) == GOLDEN_RECEIPT_BYTES
    assert _receipt_sha256(receipt) == GOLDEN_RECEIPT_SHA256
    assert hashlib.sha256(receipt_bytes + b"\n").hexdigest().upper() == (
        GOLDEN_RECEIPT_WITH_LF_SHA256
    )
    assert len(raw) == GOLDEN_CLAIM_FILE_BYTES
    assert _event_sha256(raw) == GOLDEN_CLAIM_SHA256
    assert hashlib.sha256(raw[:-1]).hexdigest().upper() == (
        GOLDEN_CLAIM_WITHOUT_LF_SHA256
    )
    assert repository_path == (
        "docs/experiments/artifacts/uprime_u1_rpc_attempts/"
        f"{LICENSE_ID}/0001.json"
    )

    event = _event_record(value)
    assert manifest.encode_attempt_manifest_event_v1_0(event) == raw
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(repository_path, raw)
    assert tuple(field.name for field in fields(parsed)) == EVENT_FILE_FIELDS
    assert tuple(field.name for field in fields(parsed.event)) == EVENT_FIELDS
    assert tuple(field.name for field in fields(parsed.event.claim_receipt)) == (
        RECEIPT_FIELDS
    )
    assert parsed.repository_path == repository_path
    assert parsed.event_sha256 == GOLDEN_CLAIM_SHA256
    assert parsed.event_bytes == raw
    assert parsed.event.scanner_rule_ids == ()
    assert parsed.event.failure_codes == ()
    assert manifest.encode_attempt_manifest_event_v1_0(parsed.event) == raw


def test_uprime_attempt_manifest_records_are_frozen_slotted_and_validate_early() -> None:
    receipt = _receipt_record()
    event = _event_record()
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        _repository_path(LICENSE_ID, 1),
        _canonical_event_file(_event_mapping()),
    )
    for value, field_name in (
        (receipt, "schema_version"),
        (event, "schema_version"),
        (parsed, "repository_path"),
    ):
        assert not hasattr(value, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            setattr(value, field_name, "forged")

    bad_receipt = _receipt_mapping()
    bad_receipt["claimed_at_utc"] = "2026-02-30T00:00:00.000000Z"
    with pytest.raises(manifest.AttemptManifestV10Error):
        _receipt_record(bad_receipt)
    bad_event = _event_mapping()
    bad_event["event_index"] = True
    with pytest.raises(manifest.AttemptManifestV10Error):
        _event_record(bad_event)


def test_uprime_attempt_manifest_missing_and_empty_directories_are_exact_missing(
    tmp_path: Path,
) -> None:
    for suffix in ("missing", "empty"):
        root = (tmp_path / suffix).absolute()
        if suffix == "empty":
            (
                root
                / "docs"
                / "experiments"
                / "artifacts"
                / "uprime_u1_rpc_attempts"
                / LICENSE_ID
            ).mkdir(parents=True)
        inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(
            root,
            LICENSE_ID,
        )
        assert tuple(field.name for field in fields(inspection)) == INSPECTION_FIELDS
        assert asdict(inspection) == {
            "inspector_schema_version": (
                "lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1"
            ),
            "inspector_scope": "local_preartifact_chain_structure_only",
            "origin_status": "unknown_may_be_synthetic",
            "license_id": LICENSE_ID,
            "chain_state": "missing",
            "event_files": (),
            "event_count": 0,
            "first_event_sha256": None,
            "last_event_index": None,
            "last_event_sha256": None,
            "last_event_type": None,
            "terminal_event": False,
            "recorded_verdict": None,
            "next_event_index": 1,
            "claim_receipt": None,
            "claim_receipt_sha256": None,
        }
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
                root,
                LICENSE_ID,
            )


def test_uprime_attempt_manifest_golden_nonterminal_inspection(tmp_path: Path) -> None:
    root, documents, raws = _write_chain(tmp_path, [_event_mapping()])
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert tuple(field.name for field in fields(inspection)) == INSPECTION_FIELDS
    assert inspection.inspector_schema_version == (
        "lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1"
    )
    assert inspection.inspector_scope == "local_preartifact_chain_structure_only"
    assert inspection.origin_status == "unknown_may_be_synthetic"
    assert inspection.chain_state == "valid_nonterminal"
    assert inspection.event_count == 1
    assert type(inspection.event_files) is tuple
    assert inspection.first_event_sha256 == GOLDEN_CLAIM_SHA256
    assert inspection.last_event_sha256 == GOLDEN_CLAIM_SHA256
    assert inspection.last_event_index == 1
    assert inspection.last_event_type == "claim_started"
    assert inspection.terminal_event is False
    assert inspection.recorded_verdict is None
    assert inspection.next_event_index == 2
    assert asdict(inspection.claim_receipt) == documents[0]["claim_receipt"]
    assert inspection.claim_receipt_sha256 == GOLDEN_RECEIPT_SHA256
    assert inspection.event_files[0].event_bytes == raws[0]


@pytest.mark.parametrize(
    ("terminal_type", "expected_sha", "expected_verdict", "expected_codes"),
    [
        (
            "attempt_finished",
            "CF94AC882C5ED46D74F1438A460661444E9EF81C2BFA1D9E82CF5EBB8390A1C9",
            "HARNESS_ERROR",
            ("OTHER_HARNESS_ERROR",),
        ),
        (
            "recovery",
            "F5BB5A7ECB1758E8DE9A422E70417BACC447FABEA9DECBC4ADD98312422646FE",
            None,
            ("POWER_LOSS",),
        ),
    ],
)
def test_uprime_attempt_manifest_golden_terminal_attestation_and_negative_authority(
    tmp_path: Path,
    terminal_type: str,
    expected_sha: str,
    expected_verdict: str | None,
    expected_codes: tuple[str, ...],
) -> None:
    terminal = _event_mapping(
        terminal_type,
        event_index=2,
        created_at_utc=TERMINAL_UTC,
        failure_codes=list(expected_codes),
    )
    root, _documents, raws = _write_chain(tmp_path, [_event_mapping(), terminal])
    assert _event_sha256(raws[0]) == GOLDEN_CLAIM_SHA256
    assert _event_sha256(raws[1]) == expected_sha
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    )
    assert tuple(field.name for field in fields(attestation)) == ATTESTATION_FIELDS
    assert asdict(attestation) == {
        "verifier_schema_version": (
            "lean-rgc-uprime-u1-local-attempt-chain-verifier-v0.1"
        ),
        "verifier_scope": "local_preartifact_chain_structure_only",
        "origin_status": "unknown_may_be_synthetic",
        "license_id": LICENSE_ID,
        "candidate_commit": CANDIDATE_COMMIT,
        "license_commit": LICENSE_COMMIT,
        "remote_claim_ref": REMOTE_CLAIM_REF,
        "claim_receipt_sha256": GOLDEN_RECEIPT_SHA256,
        "event_count": 2,
        "first_event_sha256": GOLDEN_CLAIM_SHA256,
        "last_event_index": 2,
        "last_event_sha256": expected_sha,
        "chain_state": "valid_terminal",
        "terminal_event": True,
        "last_event_type": terminal_type,
        "recorded_verdict": expected_verdict,
        "failure_codes": expected_codes,
        "preartifact_profile": True,
        "artifact_observation": "not_performed",
        "remote_claim_authentication": "not_performed",
        "git_object_authentication": "not_performed",
        "real_remote_publication": "not_performed",
        "claim_once_authentication": "not_performed",
        "reservation_token_verification": "not_performed",
        "artifact_binding": "not_performed",
        "verifier_binding": "not_performed",
        "scanner_binding": "not_performed",
        "privacy_scan": "not_performed",
        "archive_verification": "not_performed",
        "authority_scope": "none",
        "canonical_run_authority": False,
        "licenses_execution": False,
        "licenses_later_stage": False,
    }
    assert not hasattr(attestation, "__dict__")


def test_uprime_attempt_manifest_prestart_terminal_recovery_golden(
    tmp_path: Path,
) -> None:
    recovery = _event_mapping(
        "recovery",
        event_index=1,
        failure_codes=["CLAIM_STARTED_MANIFEST_ERROR"],
    )
    root, _documents, raws = _write_chain(tmp_path, [recovery])
    assert len(raws[0]) == 1996
    assert _event_sha256(raws[0]) == (
        "76DE33ED2BED8EF740B49A5C277E99022C0DE65DE13B67BF9D832ED2C8E1756B"
    )
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    )
    assert attestation.event_count == 1
    assert attestation.last_event_type == "recovery"
    assert attestation.failure_codes == ("CLAIM_STARTED_MANIFEST_ERROR",)
    assert attestation.recorded_verdict is None


def test_uprime_attempt_manifest_nonterminal_recovery_prefix_then_terminal(
    tmp_path: Path,
) -> None:
    prefix = _event_mapping(
        "recovery",
        event_index=2,
        created_at_utc=TERMINAL_UTC,
        terminal_event=False,
        failure_codes=["READER_ERROR"],
    )
    terminal = _event_mapping(
        "recovery",
        event_index=3,
        created_at_utc="2026-07-11T00:00:03.000000Z",
        failure_codes=["POWER_LOSS"],
    )
    root, _documents, _raws = _write_chain(
        tmp_path,
        [_event_mapping(), prefix, terminal],
    )
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    )
    assert attestation.event_count == 3
    assert attestation.last_event_index == 3
    assert attestation.failure_codes == ("POWER_LOSS",)
    assert "READER_ERROR" not in attestation.failure_codes


@pytest.mark.parametrize("invalid_kind", ["sticky-attempt", "terminal-tail", "gap"])
def test_uprime_attempt_manifest_invalid_chain_shapes_fail_closed(
    tmp_path: Path, invalid_kind: str
) -> None:
    if invalid_kind == "sticky-attempt":
        values = [
            _event_mapping(),
            _event_mapping(
                "recovery",
                event_index=2,
                created_at_utc=TERMINAL_UTC,
                terminal_event=False,
            ),
            _event_mapping(
                "attempt_finished",
                event_index=3,
                created_at_utc="2026-07-11T00:00:03.000000Z",
            ),
        ]
    elif invalid_kind == "terminal-tail":
        values = [
            _event_mapping(),
            _event_mapping(
                "recovery",
                event_index=2,
                created_at_utc=TERMINAL_UTC,
            ),
            _event_mapping(
                "recovery",
                event_index=3,
                created_at_utc="2026-07-11T00:00:03.000000Z",
            ),
        ]
    else:
        values = [
            _event_mapping(),
            _event_mapping(
                "recovery",
                event_index=3,
                created_at_utc=TERMINAL_UTC,
            ),
        ]
    root, _documents, _raws = _write_chain(tmp_path, values)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_backwards_chain_time_is_rejected(
    tmp_path: Path,
) -> None:
    terminal = _event_mapping(
        "recovery",
        event_index=2,
        created_at_utc="2026-07-10T23:59:59.000000Z",
    )
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping(), terminal])
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("event", field) for field in EVENT_FIELDS]
    + [("receipt", field) for field in RECEIPT_FIELDS],
)
def test_uprime_attempt_manifest_every_field_is_required(
    scope: str, field: str
) -> None:
    value = _event_mapping()
    target = value if scope == "event" else value["claim_receipt"]
    del target[field]
    if scope == "receipt":
        value["claim_receipt_sha256"] = _receipt_sha256(target)
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("event", field) for field in EVENT_FIELDS]
    + [("receipt", field) for field in RECEIPT_FIELDS],
)
def test_uprime_attempt_manifest_every_field_rejects_wrong_primitive_type(
    scope: str, field: str
) -> None:
    value = _event_mapping()
    target = value if scope == "event" else value["claim_receipt"]
    if field in {"scanner_rule_ids", "failure_codes"}:
        replacement: Any = "not-an-array"
    elif field in {
        "reservation_exists",
        "ledger_exists",
        "report_exists",
        "full_ledger_published",
        "terminal_event",
    }:
        replacement = 0
    elif field == "event_index":
        replacement = "1"
    elif field == "claim_receipt":
        replacement = "not-an-object"
    else:
        replacement = []
    target[field] = replacement
    if scope == "receipt":
        value["claim_receipt_sha256"] = _receipt_sha256(target)
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    ("scope", "field"),
    [("event", field) for field in EVENT_FIELDS]
    + [("receipt", field) for field in RECEIPT_FIELDS],
)
def test_uprime_attempt_manifest_every_field_rejects_bool_confusion(
    scope: str, field: str
) -> None:
    value = _event_mapping()
    target = value if scope == "event" else value["claim_receipt"]
    target[field] = True
    if scope == "receipt":
        value["claim_receipt_sha256"] = _receipt_sha256(target)
    _assert_parse_rejected(value)


@pytest.mark.parametrize("scope", ["event", "receipt"])
def test_uprime_attempt_manifest_exact_objects_reject_extra_keys(scope: str) -> None:
    value = _event_mapping()
    target = value if scope == "event" else value["claim_receipt"]
    target["attacker_extra"] = "must not be ignored"
    if scope == "receipt":
        value["claim_receipt_sha256"] = _receipt_sha256(target)
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("candidate_commit", "A" * 40),
        ("license_commit", "B" * 40),
        ("remote_claim_oid", "a" * 40),
        ("registry_blob_oid", "c" * 39),
        ("registry_blob_oid", "C" * 40),
        ("registry_blob_oid", "z" * 40),
        ("candidate_tree_oid", "e" * 39),
        ("candidate_tree_oid", "E" * 40),
        ("candidate_tree_oid", "z" * 40),
        ("registry_sha256", "D" * 63),
        ("registry_sha256", "d" * 64),
        ("registry_sha256", "G" * 64),
        ("input_manifest_sha256", "F" * 63),
        ("input_manifest_sha256", "f" * 64),
        ("input_manifest_sha256", "G" * 64),
        ("claimed_at_utc", "2026-02-30T00:00:00.000000Z"),
        ("claimed_at_utc", "2026-13-01T00:00:00.000000Z"),
        ("claimed_at_utc", "2026-07-11T00:00:00Z"),
        ("remote_url", "https://example.invalid/forged.git"),
        ("remote_branch_ref", "refs/heads/main"),
        ("remote_claim_ref", "refs/tags/uprime-u1-attempts/" + "0" * 64),
    ],
)
def test_uprime_attempt_manifest_receipt_syntax_rejects_after_digest_recompute(
    field: str, replacement: str
) -> None:
    value = _event_mapping()
    original_digest = value["claim_receipt_sha256"]
    value["claim_receipt"][field] = replacement
    value["claim_receipt_sha256"] = _receipt_sha256(value["claim_receipt"])
    assert value["claim_receipt_sha256"] != original_digest
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema_version", "lean-rgc-uprime-u1-attempt-manifest-v9"),
        ("event_type", "finished"),
        ("created_at_utc", "2026-02-30T00:00:01.000000Z"),
        ("created_at_utc", "2026-13-01T00:00:01.000000Z"),
        ("license_id", "E" * 64),
        ("candidate_commit", "A" * 40),
        ("license_commit", "B" * 40),
        ("remote_claim_ref", "refs/tags/uprime-u1-attempts/" + "0" * 64),
        ("claim_receipt_sha256", "f" * 64),
        ("claim_receipt_sha256", "0" * 64),
    ],
)
def test_uprime_attempt_manifest_event_same_type_invalid_values_reject(
    field: str, replacement: str
) -> None:
    value = _event_mapping()
    value[field] = replacement
    _assert_parse_rejected(value)


@pytest.mark.parametrize("mask", range(1, 8))
def test_uprime_attempt_manifest_seven_nonempty_artifact_subsets_reject(
    mask: int,
) -> None:
    value = _event_mapping()
    for bit, prefix in enumerate(("reservation", "ledger", "report")):
        if mask & (1 << bit):
            value[f"{prefix}_exists"] = True
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("reservation_sha256", "A" * 64),
        ("reservation_bytes", 1),
        ("ledger_sha256", "A" * 64),
        ("ledger_bytes", 1),
        ("report_sha256", "A" * 64),
        ("report_bytes", 1),
        ("ledger_inspection_status", "finalized"),
        ("ledger_sequence_status", "complete"),
        ("verifier_status", "passed"),
        ("scanner_status", "clear"),
        ("scanner_rule_ids", ["RULE"]),
        ("full_ledger_published", True),
        ("verdict", "U1_DIAGNOSTIC_CLEAR"),
        ("verdict", "U1_DIAGNOSTIC_BLOCKED"),
    ],
)
def test_uprime_attempt_manifest_preartifact_profile_fields_reject_individually(
    field: str, replacement: Any
) -> None:
    value = _event_mapping()
    value[field] = replacement
    _assert_parse_rejected(value)


@pytest.mark.parametrize(
    "failure_codes",
    [
        ["WORKER_TIMEOUT", "READER_ERROR"],
        ["WORKER_TIMEOUT", "WORKER_TIMEOUT"],
        ["UNKNOWN_CODE"],
        ["SCANNER_ERROR"],
        ["PRIVACY_DENIED"],
        ["ARCHIVE_ERROR"],
        ["PUBLICATION_ERROR"],
    ],
)
def test_uprime_attempt_manifest_failure_code_registry_order_and_context(
    failure_codes: list[str],
) -> None:
    value = _event_mapping(
        "recovery",
        event_index=1,
        failure_codes=failure_codes,
    )
    _assert_parse_rejected(value)


def test_uprime_attempt_manifest_failure_code_registry_is_exact() -> None:
    assert type(manifest._FAILURE_CODES) is frozenset
    assert tuple(sorted(manifest._FAILURE_CODES)) == FROZEN_FAILURE_CODES
    assert manifest._PROFILE_FORBIDDEN_CODES == frozenset(
        {"ARCHIVE_ERROR", "PRIVACY_DENIED", "PUBLICATION_ERROR", "SCANNER_ERROR"}
    )
    assert manifest._RECOVERY_ONLY_CODES == frozenset(
        {"CLAIM_STARTED_MANIFEST_ERROR", "FINAL_MANIFEST_ERROR", "POWER_LOSS"}
    )


@pytest.mark.parametrize(
    "code",
    [
        code
        for code in FROZEN_FAILURE_CODES
        if code
        not in {
            "ARCHIVE_ERROR",
            "PRIVACY_DENIED",
            "PUBLICATION_ERROR",
            "SCANNER_ERROR",
        }
    ],
)
def test_uprime_attempt_manifest_every_allowed_failure_code_has_a_valid_context(
    code: str,
) -> None:
    if code in {
        "CLAIM_STARTED_MANIFEST_ERROR",
        "FINAL_MANIFEST_ERROR",
        "POWER_LOSS",
    }:
        value = _event_mapping(
            "recovery",
            event_index=1,
            failure_codes=[code],
        )
        repository_path = _repository_path(LICENSE_ID, 1)
    else:
        value = _event_mapping(
            "attempt_finished",
            event_index=2,
            failure_codes=[code],
        )
        repository_path = _repository_path(LICENSE_ID, 2)
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        repository_path,
        _canonical_event_file(value),
    )
    assert parsed.event.failure_codes == (code,)


def _noncanonical_event_cases() -> list[tuple[str, bytes]]:
    value = _event_mapping()
    canonical = ledger.canonical_json_bytes(value)
    reversed_mapping = dict(reversed(list(json.loads(canonical).items())))
    reverse_order = json.dumps(
        reversed_mapping,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    duplicate_top = b'{"candidate_commit":"0",' + canonical[1:] + b"\n"
    duplicate_nested = canonical.replace(
        b'"claim_receipt":{"candidate_commit":',
        b'"claim_receipt":{"candidate_commit":"0","candidate_commit":',
        1,
    ) + b"\n"
    float_value = canonical.replace(b'"event_index":1', b'"event_index":1.5') + b"\n"
    nan_value = canonical.replace(b'"event_index":1', b'"event_index":NaN') + b"\n"
    infinity = canonical.replace(
        b'"event_index":1', b'"event_index":Infinity'
    ) + b"\n"
    surrogate = canonical.replace(
        b'"event_type":"claim_started"',
        b'"event_type":"\\ud800"',
    ) + b"\n"
    return [
        ("bom", b"\xef\xbb\xbf" + canonical + b"\n"),
        ("crlf", canonical + b"\r\n"),
        ("missing-lf", canonical),
        ("extra-lf", canonical + b"\n\n"),
        ("leading-space", b" " + canonical + b"\n"),
        ("trailing-space", canonical + b" \n"),
        ("reverse-order", reverse_order),
        ("duplicate-top", duplicate_top),
        ("duplicate-nested", duplicate_nested),
        ("invalid-utf8", canonical[:-1] + b"\xff}\n"),
        ("float", float_value),
        ("nan", nan_value),
        ("infinity", infinity),
        ("surrogate", surrogate),
        ("trailing-object", canonical + b"{}\n"),
    ]


@pytest.mark.parametrize("case_index", range(15))
def test_uprime_attempt_manifest_noncanonical_wire_encodings_reject(
    case_index: int,
) -> None:
    label, raw = _noncanonical_event_cases()[case_index]
    assert label
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.parse_attempt_manifest_event_file_v1_0(
            _repository_path(LICENSE_ID, 1),
            raw,
        )


@pytest.mark.parametrize(
    "variant",
    [
        "absolute",
        "backslash",
        "case",
        "dot",
        "dotdot",
        "empty-component",
        "extra-component",
        "wrong-license",
        "wrong-index",
        "zero",
        "unpadded",
        "unicode-digit",
        "five-digit",
    ],
)
def test_uprime_attempt_manifest_repository_path_is_exact(variant: str) -> None:
    raw = _canonical_event_file(_event_mapping())
    canonical = _repository_path(LICENSE_ID, 1)
    if variant == "absolute":
        candidate = "/" + canonical
    elif variant == "backslash":
        candidate = canonical.replace("/", "\\")
    elif variant == "case":
        candidate = canonical.replace("docs", "Docs", 1)
    elif variant == "dot":
        candidate = canonical.replace("artifacts/", "artifacts/./", 1)
    elif variant == "dotdot":
        candidate = canonical.replace("artifacts/", "artifacts/x/../", 1)
    elif variant == "empty-component":
        candidate = canonical.replace("artifacts/", "artifacts//", 1)
    elif variant == "extra-component":
        candidate = canonical.replace("artifacts/", "artifacts/extra/", 1)
    elif variant == "wrong-license":
        candidate = canonical.replace(LICENSE_ID, "0" * 64)
    elif variant == "wrong-index":
        candidate = canonical[:-9] + "0002.json"
    elif variant == "zero":
        candidate = canonical[:-9] + "0000.json"
    elif variant == "unpadded":
        candidate = canonical[:-9] + "1.json"
    elif variant == "unicode-digit":
        candidate = canonical[:-9] + "０００１.json"
    else:
        candidate = canonical[:-9] + "10000.json"
    assert candidate != canonical
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.parse_attempt_manifest_event_file_v1_0(candidate, raw)


@pytest.mark.parametrize(
    ("mutation", "replacement"),
    [
        ("receipt-lf-digest", GOLDEN_RECEIPT_WITH_LF_SHA256),
        ("receipt-wrong-digest", "0" * 64),
        ("receipt-lower-digest", GOLDEN_RECEIPT_SHA256.lower()),
    ],
)
def test_uprime_attempt_manifest_receipt_hash_formula_is_lf_free(
    mutation: str, replacement: str
) -> None:
    value = _event_mapping()
    value["claim_receipt_sha256"] = replacement
    assert mutation
    _assert_parse_rejected(value)


@pytest.mark.parametrize("prior", ["0" * 64, GOLDEN_CLAIM_SHA256.lower()])
def test_uprime_attempt_manifest_prior_hash_mismatch_and_case_reject(
    tmp_path: Path, prior: str
) -> None:
    root, _documents, _raws = _write_chain(
        tmp_path,
        [
            _event_mapping(),
            _event_mapping(
                "recovery",
                event_index=2,
                created_at_utc=TERMINAL_UTC,
            ),
        ],
    )
    second = _host_event_path(root, LICENSE_ID, 2)
    value = json.loads(second.read_bytes())
    value["prior_event_sha256"] = prior
    second.write_bytes(_canonical_event_file(value))
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_self_consistent_whole_chain_rewrite_is_structural_only(
    tmp_path: Path,
) -> None:
    alternate_receipt = _receipt_mapping(candidate_commit="d" * 40)
    alternate_license_id = alternate_receipt["license_id"]
    claim = _event_mapping(receipt=alternate_receipt)
    terminal = _event_mapping(
        "recovery",
        event_index=2,
        created_at_utc=TERMINAL_UTC,
        receipt=alternate_receipt,
    )
    root, _documents, _raws = _write_chain(
        tmp_path,
        [claim, terminal],
        root_name="rewritten-sandbox",
    )
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        alternate_license_id,
    )
    assert attestation.license_id == alternate_license_id
    assert attestation.candidate_commit == "d" * 40
    assert attestation.origin_status == "unknown_may_be_synthetic"
    assert attestation.remote_claim_authentication == "not_performed"
    assert attestation.git_object_authentication == "not_performed"
    assert attestation.real_remote_publication == "not_performed"
    assert attestation.licenses_execution is False


def test_uprime_attempt_manifest_literal_index_9999_and_private_classifier() -> None:
    value = _event_mapping(
        "recovery",
        event_index=9999,
        terminal_event=False,
    )
    raw = _canonical_event_file(value)
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        _repository_path(LICENSE_ID, 9999),
        raw,
    )
    assert parsed.event.event_index == 9999
    assert manifest._classify_chain_suffix(9999, False) == (
        "valid_nonterminal_index_exhausted",
        None,
    )


@pytest.mark.parametrize(
    ("event_index", "terminal_event", "expected"),
    [
        (7, True, ("valid_terminal", None)),
        (9_999, False, ("valid_nonterminal_index_exhausted", None)),
        (7, False, ("valid_nonterminal", 8)),
    ],
)
def test_uprime_attempt_manifest_private_classifier_exact_tuple_contract(
    event_index: int,
    terminal_event: bool,
    expected: tuple[str, int | None],
) -> None:
    assert manifest._classify_chain_suffix(event_index, terminal_event) == expected


def test_uprime_attempt_manifest_literal_index_10000_rejects() -> None:
    value = _event_mapping(
        "recovery",
        event_index=10_000,
        terminal_event=False,
    )
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.parse_attempt_manifest_event_file_v1_0(
            (
                "docs/experiments/artifacts/uprime_u1_rpc_attempts/"
                f"{LICENSE_ID}/10000.json"
            ),
            _canonical_event_file(value),
        )


class _BytesRoot:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __fspath__(self) -> bytes:
        return self.raw


@pytest.mark.parametrize("kind", ["empty", "relative", "bytes", "bytes-pathlike"])
def test_uprime_attempt_manifest_root_must_be_nonempty_absolute_text(
    tmp_path: Path, kind: str
) -> None:
    if kind == "empty":
        root: Any = ""
    elif kind == "relative":
        root = "relative-synthetic-root"
    elif kind == "bytes":
        root = os.fsencode(tmp_path)
    else:
        root = _BytesRoot(os.fsencode(tmp_path))
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_unexpected_directory_entry_rejects(
    tmp_path: Path,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    directory = _host_event_path(root, LICENSE_ID, 1).parent
    (directory / "unexpected.tmp").write_bytes(b"x")
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_oversize_file_rejects_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "oversize").absolute()
    target = _host_event_path(root, LICENSE_ID, 1)
    target.parent.mkdir(parents=True)
    with target.open("wb") as stream:
        stream.seek(manifest._MAX_EVENT_BYTES)
        stream.write(b"x")
    calls = 0

    def forbidden_read(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("oversize file must reject before payload read")

    monkeypatch.setattr(manifest, "_os_read", forbidden_read)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 0


def test_uprime_attempt_manifest_positive_partial_reads_are_looped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_read = manifest._os_read
    calls = 0

    def partial_read(fd: int, count: int) -> bytes:
        nonlocal calls
        calls += 1
        return real_read(fd, min(count, 17))

    monkeypatch.setattr(manifest, "_os_read", partial_read)
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert inspection.chain_state == "valid_nonterminal"
    assert calls > 4


def test_uprime_attempt_manifest_early_eof_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_read = manifest._os_read
    calls = 0

    def short_first_read(fd: int, count: int) -> bytes:
        nonlocal calls
        calls += 1
        chunk = real_read(fd, count)
        if calls == 1:
            assert chunk
            return chunk[:-1]
        return chunk

    monkeypatch.setattr(manifest, "_os_read", short_first_read)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


def test_uprime_attempt_manifest_descriptor_metadata_drift_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_fstat = manifest._os_fstat
    calls = 0

    def drifting_fstat(fd: int) -> Any:
        nonlocal calls
        calls += 1
        observed = real_fstat(fd)
        if calls == 2:
            return _fake_stat(
                observed,
                st_mtime_ns=int(observed.st_mtime_ns) + 1,
            )
        return observed

    monkeypatch.setattr(manifest, "_os_fstat", drifting_fstat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


def test_uprime_attempt_manifest_cross_family_mode_ctime_difference_with_equal_b_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    event_key = os.path.normcase(os.path.abspath(event_path))

    path_observed = manifest._os_stat(event_path, follow_symlinks=False)
    fd = manifest._os_open(
        event_path,
        os.O_RDONLY | getattr(os, "O_BINARY", 0),
    )
    try:
        descriptor_observed = manifest._os_fstat(fd)
    finally:
        manifest._os_close(fd)
    assert manifest._path_binding(manifest._path_snapshot(path_observed)) == (
        manifest._descriptor_binding(
            manifest._descriptor_snapshot(descriptor_observed)
        )
    )
    real_stat = manifest._os_stat

    def cross_family_different_stat(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if (
            follow_symlinks is False
            and os.path.normcase(os.path.abspath(os.fspath(target))) == event_key
        ):
            return _fake_stat(
                observed,
                st_mode=int(observed.st_mode) ^ 0o200,
                st_ctime_ns=int(observed.st_ctime_ns) + 1_000_000,
            )
        return observed

    monkeypatch.setattr(manifest, "_os_stat", cross_family_different_stat)
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert inspection.chain_state == "valid_nonterminal"


@pytest.mark.parametrize("side", ["path", "descriptor"])
@pytest.mark.parametrize(
    "field",
    ["st_dev", "st_ino", "st_size", "st_mtime_ns"],
)
def test_uprime_attempt_manifest_each_cross_family_b_component_mismatch_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    side: str,
    field: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    event_key = os.path.normcase(os.path.abspath(event_path))
    if side == "path":
        real_stat = manifest._os_stat

        def mismatching_stat(
            target: Any,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> Any:
            observed = real_stat(
                target,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )
            if (
                follow_symlinks is False
                and os.path.normcase(os.path.abspath(os.fspath(target)))
                == event_key
            ):
                return _fake_stat(
                    observed,
                    **{field: int(getattr(observed, field)) + 1},
                )
            return observed

        monkeypatch.setattr(manifest, "_os_stat", mismatching_stat)
    else:
        real_fstat = manifest._os_fstat

        def mismatching_fstat(fd: int) -> Any:
            observed = real_fstat(fd)
            return _fake_stat(
                observed,
                **{field: int(getattr(observed, field)) + 1},
            )

        monkeypatch.setattr(manifest, "_os_fstat", mismatching_fstat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_final_directory_identity_drift_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    directory = _host_event_path(root, LICENSE_ID, 1).parent
    normalized_directory = os.path.normcase(os.path.abspath(directory))
    real_stat = manifest._os_stat
    directory_calls = 0

    def drifting_stat(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        nonlocal directory_calls
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if (
            os.path.normcase(os.path.abspath(os.fspath(target)))
            == normalized_directory
            and follow_symlinks is False
        ):
            directory_calls += 1
            if directory_calls == 2:
                return _fake_stat(observed, st_ino=int(observed.st_ino) + 1)
        return observed

    monkeypatch.setattr(manifest, "_os_stat", drifting_stat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert directory_calls == 2


@pytest.mark.parametrize("kind", ["nonregular", "symlink", "reparse"])
def test_uprime_attempt_manifest_final_directory_type_sentinels_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    directory = _host_event_path(root, LICENSE_ID, 1).parent
    directory_key = os.path.normcase(os.path.abspath(directory))
    real_stat = manifest._os_stat
    if kind == "reparse":
        monkeypatch.setattr(
            manifest.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
            raising=False,
        )

    def sentinel_stat(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        key = os.path.normcase(os.path.abspath(os.fspath(target)))
        if key != directory_key or follow_symlinks is not False:
            return observed
        if kind == "nonregular":
            return _fake_stat(observed, st_mode=manifest.stat.S_IFREG | 0o644)
        if kind == "symlink":
            return _fake_stat(observed, st_mode=manifest.stat.S_IFLNK | 0o777)
        return _fake_stat(observed, st_file_attributes=0x400)

    monkeypatch.setattr(manifest, "_os_stat", sentinel_stat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_second_scan_name_mutation_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, raws = _write_chain(tmp_path, [_event_mapping()])
    directory = _host_event_path(root, LICENSE_ID, 1).parent
    real_scandir = manifest._os_scandir
    calls = 0

    def mutate_before_second_scan(target: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            (directory / "0002.json").write_bytes(raws[0])
        return real_scandir(target)

    monkeypatch.setattr(manifest, "_os_scandir", mutate_before_second_scan)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


def test_uprime_attempt_manifest_second_scan_entry_metadata_mutation_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    event_key = os.path.normcase(os.path.abspath(event_path))
    real_stat = manifest._os_stat
    calls = 0

    def mutate_s2(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        nonlocal calls
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if os.path.normcase(os.path.abspath(os.fspath(target))) == event_key:
            calls += 1
            if calls == 3:
                return _fake_stat(
                    observed,
                    st_mtime_ns=int(observed.st_mtime_ns) + 1,
                )
        return observed

    monkeypatch.setattr(manifest, "_os_stat", mutate_s2)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 3


@pytest.mark.parametrize("mutation", ["disappear", "replace"])
def test_uprime_attempt_manifest_post_close_path_disappearance_or_replacement_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    replacement = tmp_path / "replacement-event.bin"
    replacement.write_bytes(event_path.read_bytes())
    real_close = manifest._os_close
    calls = 0

    def close_then_mutate(fd: int) -> None:
        nonlocal calls
        calls += 1
        real_close(fd)
        if mutation == "disappear":
            event_path.unlink()
        else:
            os.replace(replacement, event_path)

    monkeypatch.setattr(manifest, "_os_close", close_then_mutate)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 1


@pytest.mark.parametrize("kind", ["nonregular", "symlink", "reparse"])
def test_uprime_attempt_manifest_path_nonregular_symlink_reparse_sentinels_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    event_key = os.path.normcase(os.path.abspath(event_path))
    real_stat = manifest._os_stat
    if kind == "reparse":
        monkeypatch.setattr(
            manifest.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
            raising=False,
        )

    def sentinel_stat(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if os.path.normcase(os.path.abspath(os.fspath(target))) != event_key:
            return observed
        if kind == "nonregular":
            return _fake_stat(
                observed,
                st_mode=manifest.stat.S_IFDIR | 0o755,
            )
        if kind == "symlink":
            return _fake_stat(
                observed,
                st_mode=manifest.stat.S_IFLNK | 0o777,
            )
        return _fake_stat(observed, st_file_attributes=0x400)

    monkeypatch.setattr(manifest, "_os_stat", sentinel_stat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


@pytest.mark.parametrize("mode_kind", ["directory", "symlink"])
def test_uprime_attempt_manifest_nonregular_descriptor_sentinels_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode_kind: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_fstat = manifest._os_fstat

    def nonregular_fstat(fd: int) -> Any:
        observed = real_fstat(fd)
        mode = (
            manifest.stat.S_IFDIR | 0o755
            if mode_kind == "directory"
            else manifest.stat.S_IFLNK | 0o777
        )
        return _fake_stat(observed, st_mode=mode)

    monkeypatch.setattr(manifest, "_os_fstat", nonregular_fstat)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


@pytest.mark.parametrize("field", ["st_mode", "st_ctime_ns"])
def test_uprime_attempt_manifest_path_family_s0_s1_mode_ctime_drift_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    event_key = os.path.normcase(os.path.abspath(event_path))
    real_stat = manifest._os_stat
    calls = 0

    def drift_s1(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        nonlocal calls
        observed = real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if os.path.normcase(os.path.abspath(os.fspath(target))) == event_key:
            calls += 1
            if calls == 2:
                replacement = (
                    int(observed.st_mode) ^ 0o200
                    if field == "st_mode"
                    else int(observed.st_ctime_ns) + 1
                )
                return _fake_stat(observed, **{field: replacement})
        return observed

    monkeypatch.setattr(manifest, "_os_stat", drift_s1)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


@pytest.mark.parametrize("failure_call", [2, 3])
@pytest.mark.parametrize("field", ["st_mode", "st_ctime_ns"])
def test_uprime_attempt_manifest_descriptor_family_f_mode_ctime_drift_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
    field: str,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_fstat = manifest._os_fstat
    calls = 0

    def drift_descriptor(fd: int) -> Any:
        nonlocal calls
        calls += 1
        observed = real_fstat(fd)
        if calls == failure_call:
            replacement = (
                int(observed.st_mode) ^ 0o200
                if field == "st_mode"
                else int(observed.st_ctime_ns) + 1
            )
            return _fake_stat(observed, **{field: replacement})
        return observed

    monkeypatch.setattr(manifest, "_os_fstat", drift_descriptor)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == failure_call


def test_uprime_attempt_manifest_post_close_redundant_b_binding_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_binding = manifest._path_binding
    calls = 0

    def mismatch_only_post_close(
        value: tuple[int, int, int, bool, int, int, int],
    ) -> tuple[int, int, int, int]:
        nonlocal calls
        calls += 1
        binding = real_binding(value)
        if calls == 2:
            return (binding[0] + 1, binding[1], binding[2], binding[3])
        return binding

    monkeypatch.setattr(manifest, "_path_binding", mismatch_only_post_close)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


def test_uprime_attempt_manifest_private_bounds_have_frozen_defaults() -> None:
    assert manifest._MAX_EVENT_BYTES == 1_048_576
    assert manifest._MAX_EVENT_COUNT == 9_999
    assert manifest._MAX_CHAIN_BYTES == 67_108_864


@pytest.mark.parametrize(("length", "accepted"), [(31, True), (32, True), (33, False)])
def test_uprime_attempt_manifest_private_reader_bound_n_minus_one_n_n_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    length: int,
    accepted: bool,
) -> None:
    path = tmp_path / f"reader-bound-{length}.bin"
    path.write_bytes(b"x" * length)
    monkeypatch.setattr(manifest, "_MAX_EVENT_BYTES", 32)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        if accepted:
            assert manifest._read_bounded_pass(fd, length) == b"x" * length
        else:
            with pytest.raises(manifest.AttemptManifestV10Error):
                manifest._read_bounded_pass(fd, length)
    finally:
        os.close(fd)


def test_uprime_attempt_manifest_private_reader_extra_byte_growth_probe_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "reader-growth.bin"
    path.write_bytes(b"x" * 33)
    monkeypatch.setattr(manifest, "_MAX_EVENT_BYTES", 64)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest._read_bounded_pass(fd, 32)
    finally:
        os.close(fd)


@pytest.mark.parametrize(("event_count", "accepted"), [(2, True), (3, True), (4, False)])
def test_uprime_attempt_manifest_reduced_count_bound_n_minus_one_n_n_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_count: int,
    accepted: bool,
) -> None:
    root, _documents, _raws = _write_chain(
        tmp_path,
        _valid_chain_values(event_count),
        root_name=f"count-{event_count}",
    )
    monkeypatch.setattr(manifest, "_MAX_EVENT_COUNT", 3)
    if accepted:
        inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(
            root,
            LICENSE_ID,
        )
        assert inspection.chain_state == "valid_terminal"
        assert inspection.event_count == event_count
    else:
        event_stats = 0
        opens = 0
        real_stat = manifest._os_stat
        real_open = manifest._os_open

        def counted_stat(
            target: Any,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> Any:
            nonlocal event_stats
            if os.fspath(target).endswith(".json"):
                event_stats += 1
            return real_stat(
                target,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )

        def counted_open(*args: Any, **kwargs: Any) -> int:
            nonlocal opens
            opens += 1
            return real_open(*args, **kwargs)

        monkeypatch.setattr(manifest, "_os_stat", counted_stat)
        monkeypatch.setattr(manifest, "_os_open", counted_open)
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
        assert event_stats == 0
        assert opens == 0


class _MaxPlusOneGuardedScandir:
    def __init__(self, entries: list[Any], max_count: int) -> None:
        self._entries = entries
        self._max_count = max_count
        self.yielded = 0
        self.closed = False

    def __iter__(self) -> "_MaxPlusOneGuardedScandir":
        return self

    def __next__(self) -> Any:
        if self.yielded >= self._max_count + 1:
            raise AssertionError("scandir consumed beyond max+1")
        value = self._entries[self.yielded]
        self.yielded += 1
        return value

    def close(self) -> None:
        self.closed = True


def test_uprime_attempt_manifest_count_scan_stops_at_max_plus_one_before_stat_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _documents, _raws = _write_chain(
        tmp_path,
        _valid_chain_values(5),
        root_name="stream-count",
    )
    directory = _host_event_path(root, LICENSE_ID, 1).parent
    with os.scandir(directory) as iterator:
        entries = sorted(list(iterator), key=lambda entry: entry.name)
    guarded = _MaxPlusOneGuardedScandir(entries, 3)
    event_stats = 0
    opens = 0
    real_stat = manifest._os_stat
    real_open = manifest._os_open

    def guarded_scandir(target: Any) -> _MaxPlusOneGuardedScandir:
        assert os.path.normcase(os.path.abspath(os.fspath(target))) == (
            os.path.normcase(os.path.abspath(directory))
        )
        return guarded

    def counted_stat(
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> Any:
        nonlocal event_stats
        if os.fspath(target).endswith(".json"):
            event_stats += 1
        return real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )

    def counted_open(*args: Any, **kwargs: Any) -> int:
        nonlocal opens
        opens += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr(manifest, "_MAX_EVENT_COUNT", 3)
    monkeypatch.setattr(manifest, "_os_scandir", guarded_scandir)
    monkeypatch.setattr(manifest, "_os_stat", counted_stat)
    monkeypatch.setattr(manifest, "_os_open", counted_open)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert guarded.yielded == 4
    assert guarded.closed is True
    assert event_stats == 0
    assert opens == 0


def test_uprime_attempt_manifest_injected_aggregate_bound_rejects_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, raws = _write_chain(tmp_path, [_event_mapping()])
    monkeypatch.setattr(manifest, "_MAX_CHAIN_BYTES", len(raws[0]) - 1)
    calls = 0
    real_open = manifest._os_open

    def counted_open(*args: Any, **kwargs: Any) -> int:
        nonlocal calls
        calls += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr(manifest, "_os_open", counted_open)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 0


def test_uprime_attempt_manifest_same_size_between_pass_mutation_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_pass = manifest._read_bounded_pass
    calls = 0

    def altered_second_pass(fd: int, expected_size: int) -> bytes:
        nonlocal calls
        calls += 1
        raw = real_pass(fd, expected_size)
        if calls == 2:
            assert len(raw) > 1
            return bytes([raw[0] ^ 1]) + raw[1:]
        return raw

    monkeypatch.setattr(manifest, "_read_bounded_pass", altered_second_pass)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 2


def test_uprime_attempt_manifest_close_failure_is_public_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_close = manifest._os_close
    calls = 0

    def failing_close(fd: int) -> None:
        nonlocal calls
        calls += 1
        real_close(fd)
        raise OSError("injected close failure")

    monkeypatch.setattr(manifest, "_os_close", failing_close)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert calls == 1


def test_uprime_attempt_manifest_exact_single_file_snapshot_call_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    directory = event_path.parent
    event_key = os.path.normcase(os.path.abspath(event_path))
    directory_key = os.path.normcase(os.path.abspath(directory))
    real_open = manifest._os_open
    real_lseek = manifest._os_lseek
    real_fstat = manifest._os_fstat
    real_close = manifest._os_close
    real_stat = manifest._os_stat
    real_scandir = manifest._os_scandir
    tracked_fd: int | None = None
    calls = {
        "open": 0,
        "lseek": 0,
        "fstat": 0,
        "close": 0,
        "file_path_stat": 0,
        "directory_stat": 0,
        "scandir": 0,
    }

    def counted_open(target: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal tracked_fd
        if os.path.normcase(os.path.abspath(os.fspath(target))) == event_key:
            calls["open"] += 1
            assert flags == os.O_RDONLY | getattr(os, "O_BINARY", 0)
        tracked_fd = real_open(target, flags, *args, **kwargs)
        return tracked_fd

    def counted_lseek(fd: int, offset: int, whence: int) -> int:
        if fd == tracked_fd:
            calls["lseek"] += 1
            assert offset == 0 and whence == os.SEEK_SET
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
        target: Any,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        key = os.path.normcase(os.path.abspath(os.fspath(target)))
        if follow_symlinks is False and key == event_key:
            calls["file_path_stat"] += 1
        if follow_symlinks is False and key == directory_key:
            calls["directory_stat"] += 1
        return real_stat(
            target,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )

    def counted_scandir(target: Any) -> Any:
        if os.path.normcase(os.path.abspath(os.fspath(target))) == directory_key:
            calls["scandir"] += 1
        return real_scandir(target)

    monkeypatch.setattr(manifest, "_os_open", counted_open)
    monkeypatch.setattr(manifest, "_os_lseek", counted_lseek)
    monkeypatch.setattr(manifest, "_os_fstat", counted_fstat)
    monkeypatch.setattr(manifest, "_os_close", counted_close)
    monkeypatch.setattr(manifest, "_os_stat", counted_stat)
    monkeypatch.setattr(manifest, "_os_scandir", counted_scandir)
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert inspection.chain_state == "valid_nonterminal"
    assert calls == {
        "open": 1,
        "lseek": 2,
        "fstat": 3,
        "close": 1,
        "file_path_stat": 3,
        "directory_stat": 2,
        "scandir": 2,
    }


@pytest.mark.parametrize(
    ("operation", "failure_call"),
    [
        ("directory_stat", 1),
        ("directory_stat", 2),
        ("scandir", 1),
        ("scandir", 2),
        ("entry_stat", 1),
        ("entry_stat", 2),
        ("entry_stat", 3),
        ("open", 1),
        ("lseek", 1),
        ("lseek", 2),
        ("fstat", 1),
        ("fstat", 2),
        ("fstat", 3),
        ("read", 1),
        ("read", 2),
        ("read", 3),
        ("read", 4),
    ],
)
def test_uprime_attempt_manifest_each_snapshot_io_stage_failure_is_public(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    failure_call: int,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    event_path = _host_event_path(root, LICENSE_ID, 1)
    directory = event_path.parent
    event_key = os.path.normcase(os.path.abspath(event_path))
    directory_key = os.path.normcase(os.path.abspath(directory))
    call_count = 0

    if operation in {"directory_stat", "entry_stat"}:
        real_stat = manifest._os_stat

        def failing_stat(
            target: Any,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> Any:
            nonlocal call_count
            key = os.path.normcase(os.path.abspath(os.fspath(target)))
            selected = (
                operation == "directory_stat" and key == directory_key
            ) or (operation == "entry_stat" and key == event_key)
            if selected:
                call_count += 1
                if call_count == failure_call:
                    raise OSError(f"injected {operation} failure")
            return real_stat(
                target,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )

        monkeypatch.setattr(manifest, "_os_stat", failing_stat)
    elif operation == "scandir":
        real_scandir = manifest._os_scandir

        def failing_scandir(target: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == failure_call:
                raise OSError("injected scandir failure")
            return real_scandir(target)

        monkeypatch.setattr(manifest, "_os_scandir", failing_scandir)
    else:
        attribute = f"_os_{operation}"
        original = getattr(manifest, attribute)

        def failing_call(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == failure_call:
                raise OSError(f"injected {operation} failure")
            return original(*args, **kwargs)

        monkeypatch.setattr(manifest, attribute, failing_call)

    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert call_count == failure_call


def test_uprime_attempt_manifest_close_failure_overrides_prior_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _documents, _raws = _write_chain(tmp_path, [_event_mapping()])
    real_close = manifest._os_close
    reads = 0
    closes = 0

    def failing_read(fd: int, count: int) -> bytes:
        nonlocal reads
        reads += 1
        raise OSError("injected prior read failure")

    def failing_close(fd: int) -> None:
        nonlocal closes
        closes += 1
        real_close(fd)
        raise OSError("injected close failure")

    monkeypatch.setattr(manifest, "_os_read", failing_read)
    monkeypatch.setattr(manifest, "_os_close", failing_close)
    with pytest.raises(
        manifest.AttemptManifestV10Error,
        match="descriptor close failed",
    ):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert reads == 1
    assert closes == 1


def _parsed_chain_files(
    values: list[dict[str, Any]],
) -> tuple[manifest.AttemptManifestEventFileV10, ...]:
    parsed: list[manifest.AttemptManifestEventFileV10] = []
    previous_sha: str | None = None
    for original in values:
        value = copy.deepcopy(original)
        value["claim_receipt_sha256"] = _receipt_sha256(value["claim_receipt"])
        value["prior_event_sha256"] = previous_sha
        raw = _canonical_event_file(value)
        parsed.append(
            manifest.parse_attempt_manifest_event_file_v1_0(
                _repository_path(value["license_id"], value["event_index"]),
                raw,
            )
        )
        previous_sha = _event_sha256(raw)
    return tuple(parsed)


@pytest.mark.parametrize("drift_kind", ["receipt", "license", "candidate_identity"])
def test_uprime_attempt_manifest_individually_valid_midchain_drift_rejects(
    drift_kind: str,
) -> None:
    claim = _event_mapping()
    if drift_kind == "receipt":
        receipt = _receipt_mapping()
        receipt["registry_blob_oid"] = "9" * 40
    elif drift_kind == "license":
        receipt = _receipt_mapping(license_commit="8" * 40)
    else:
        receipt = _receipt_mapping(candidate_commit="7" * 40)
    terminal = _event_mapping(
        "recovery",
        event_index=2,
        created_at_utc=TERMINAL_UTC,
        receipt=receipt,
    )
    files = _parsed_chain_files([claim, terminal])
    assert files[0].event.claim_receipt != files[1].event.claim_receipt
    with pytest.raises(manifest.AttemptManifestV10Error, match="drift"):
        manifest._validate_chain(files)


@pytest.mark.parametrize("terminal_type", ["recovery", "attempt_finished"])
def test_uprime_attempt_manifest_equal_event_timestamps_are_allowed(
    tmp_path: Path,
    terminal_type: str,
) -> None:
    terminal = _event_mapping(
        terminal_type,
        event_index=2,
        created_at_utc=CLAIM_UTC,
    )
    root, _documents, _raws = _write_chain(
        tmp_path,
        [_event_mapping(), terminal],
        root_name=f"equal-time-{terminal_type}",
    )
    assert manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    ).chain_state == "valid_terminal"


@pytest.mark.parametrize("invalid_start", ["attempt_finished", "nonterminal_recovery"])
def test_uprime_attempt_manifest_individually_valid_invalid_start_rejects(
    tmp_path: Path,
    invalid_start: str,
) -> None:
    if invalid_start == "attempt_finished":
        value = _event_mapping("attempt_finished", event_index=1)
    else:
        value = _event_mapping("recovery", event_index=1, terminal_event=False)
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        _repository_path(LICENSE_ID, 1),
        _canonical_event_file(value),
    )
    assert parsed.event.event_index == 1
    root, _documents, _raws = _write_chain(
        tmp_path,
        [value],
        root_name=f"invalid-start-{invalid_start}",
    )
    with pytest.raises(manifest.AttemptManifestV10Error, match="start"):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def _assert_rebound_parse_rejected(value: dict[str, Any]) -> None:
    value["claim_receipt_sha256"] = _receipt_sha256(value["claim_receipt"])
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.parse_attempt_manifest_event_file_v1_0(
            _repository_path(value["license_id"], value["event_index"]),
            _canonical_event_file(value),
        )


def test_uprime_attempt_manifest_dependent_receipt_mutations_isolate_validation() -> None:
    positive_receipts = [
        _receipt_mapping(candidate_commit="7" * 40),
        _receipt_mapping(license_commit="8" * 40),
        _receipt_mapping(),
    ]
    positive_receipts[2]["registry_blob_oid"] = "9" * 40
    for receipt in positive_receipts:
        value = _event_mapping(receipt=receipt)
        parsed = manifest.parse_attempt_manifest_event_file_v1_0(
            _repository_path(value["license_id"], 1),
            _canonical_event_file(value),
        )
        assert parsed.event.claim_receipt.registry_blob_oid == receipt["registry_blob_oid"]

    wrong_id = _event_mapping()
    wrong_id["claim_receipt"]["license_id"] = "0" * 64
    wrong_id["claim_receipt"]["remote_claim_ref"] = (
        "refs/tags/uprime-u1-attempts/" + "0" * 64
    )
    wrong_id["license_id"] = "0" * 64
    wrong_id["remote_claim_ref"] = wrong_id["claim_receipt"]["remote_claim_ref"]
    _assert_rebound_parse_rejected(wrong_id)

    wrong_l = _event_mapping()
    wrong_l["claim_receipt"]["license_commit"] = "8" * 40
    wrong_l["license_commit"] = "8" * 40
    _assert_rebound_parse_rejected(wrong_l)

    wrong_oid = _event_mapping()
    wrong_oid["claim_receipt"]["remote_claim_oid"] = "8" * 40
    _assert_rebound_parse_rejected(wrong_oid)

    wrong_ref = _event_mapping()
    wrong_ref["claim_receipt"]["remote_claim_ref"] = (
        "refs/tags/uprime-u1-attempts/" + "0" * 64
    )
    wrong_ref["remote_claim_ref"] = wrong_ref["claim_receipt"]["remote_claim_ref"]
    _assert_rebound_parse_rejected(wrong_ref)

    malformed_c = _event_mapping()
    malformed_c["claim_receipt"]["candidate_commit"] = "7" * 39
    derived = hashlib.sha256(
        b"lean-rgc-uprime-u1-attempt-v1\0" + b"7" * 39
    ).hexdigest()
    malformed_c["claim_receipt"]["license_id"] = derived
    malformed_c["claim_receipt"]["remote_claim_ref"] = (
        f"refs/tags/uprime-u1-attempts/{derived}"
    )
    malformed_c["candidate_commit"] = "7" * 39
    malformed_c["license_id"] = derived
    malformed_c["remote_claim_ref"] = malformed_c["claim_receipt"]["remote_claim_ref"]
    _assert_rebound_parse_rejected(malformed_c)


def test_uprime_attempt_manifest_encode_revalidates_bypass_mutated_records() -> None:
    event = _event_record()
    object.__setattr__(event, "event_index", True)
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.encode_attempt_manifest_event_v1_0(event)

    event = _event_record()
    object.__setattr__(event.claim_receipt, "remote_url", "https://invalid.example/")
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.encode_attempt_manifest_event_v1_0(event)

    event = _event_record(
        _event_mapping("attempt_finished", event_index=2)
    )
    object.__setattr__(event, "failure_codes", ("WORKER_TIMEOUT", "READER_ERROR"))
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.encode_attempt_manifest_event_v1_0(event)


def test_uprime_attempt_manifest_same_type_event_semantic_negatives() -> None:
    cases: list[dict[str, Any]] = []
    for field, replacement in (
        ("terminal_event", True),
        ("verdict", "HARNESS_ERROR"),
        ("failure_codes", ["READER_ERROR"]),
    ):
        value = _event_mapping()
        value[field] = replacement
        cases.append(value)

    value = _event_mapping()
    value["event_index"] = 2
    value["prior_event_sha256"] = "A" * 64
    cases.append(value)

    for field, replacement in (
        ("failure_codes", []),
        ("verdict", "HARNESS_ERROR"),
    ):
        value = _event_mapping("recovery", event_index=1)
        value[field] = replacement
        cases.append(value)

    for field, replacement in (
        ("terminal_event", False),
        ("verdict", None),
        ("verdict", "U1_DIAGNOSTIC_CLEAR"),
        ("verdict", "U1_DIAGNOSTIC_BLOCKED"),
        ("failure_codes", []),
    ):
        value = _event_mapping("attempt_finished", event_index=2)
        value[field] = replacement
        cases.append(value)
    for code in (
        "CLAIM_STARTED_MANIFEST_ERROR",
        "FINAL_MANIFEST_ERROR",
        "POWER_LOSS",
    ):
        cases.append(
            _event_mapping(
                "attempt_finished",
                event_index=2,
                failure_codes=[code],
            )
        )

    prior_cases = [
        (1, "A" * 64),
        (2, None),
        (2, "a" * 64),
        (2, "A" * 63),
    ]
    for index, prior in prior_cases:
        value = _event_mapping(
            "attempt_finished" if index == 2 else "recovery",
            event_index=index,
        )
        value["prior_event_sha256"] = prior
        cases.append(value)

    for value in cases:
        _assert_rebound_parse_rejected(value)

    for invalid_index in (0, 10_000):
        value = _event_mapping()
        value["event_index"] = invalid_index
        with pytest.raises(manifest.AttemptManifestV10Error):
            _event_record(value)


def test_uprime_attempt_manifest_runtime_annotations_are_exact() -> None:
    assert manifest.PublicClaimReceiptV10.__annotations__ == {
        name: str for name in RECEIPT_FIELDS
    }
    expected_event_types = (
        str, str, int, str, str, str, str, str,
        manifest.PublicClaimReceiptV10, str, str | None,
        bool, bool, bool, str | None, int | None, str | None, int | None,
        str | None, int | None, str, str | None, str, str,
        tuple[str, ...], str | None, tuple[str, ...], bool, bool,
    )
    assert manifest.AttemptManifestEventV10.__annotations__ == dict(
        zip(EVENT_FIELDS, expected_event_types, strict=True)
    )
    assert manifest.AttemptManifestEventFileV10.__annotations__ == dict(
        zip(
            EVENT_FILE_FIELDS,
            (str, str, bytes, manifest.AttemptManifestEventV10),
            strict=True,
        )
    )
    expected_inspection_types = (
        str, str, str, str, str,
        tuple[manifest.AttemptManifestEventFileV10, ...], int,
        str | None, int | None, str | None, str | None, bool,
        str | None, int | None, manifest.PublicClaimReceiptV10 | None,
        str | None,
    )
    assert manifest.AttemptManifestChainInspectionV10.__annotations__ == dict(
        zip(INSPECTION_FIELDS, expected_inspection_types, strict=True)
    )
    expected_attestation_types = (
        str, str, str, str, str, str, str, str, int, str, int, str, str,
        bool, str, str | None, tuple[str, ...], bool, str, str, str, str, str,
        str, str, str, str, str, str, str, bool, bool, bool,
    )
    assert manifest.AttemptManifestChainAttestationV10.__annotations__ == dict(
        zip(ATTESTATION_FIELDS, expected_attestation_types, strict=True)
    )

    signatures = {
        "encode_attempt_manifest_event_v1_0": (
            (manifest.AttemptManifestEventV10,), bytes
        ),
        "parse_attempt_manifest_event_file_v1_0": (
            (str, bytes), manifest.AttemptManifestEventFileV10
        ),
        "inspect_local_attempt_manifest_chain_v1_0": (
            (str | os.PathLike[str], str),
            manifest.AttemptManifestChainInspectionV10,
        ),
        "verify_local_attempt_manifest_terminal_chain_v1_0": (
            (str | os.PathLike[str], str),
            manifest.AttemptManifestChainAttestationV10,
        ),
    }
    for name, (parameter_types, return_type) in signatures.items():
        signature = inspect.signature(getattr(manifest, name))
        assert tuple(p.annotation for p in signature.parameters.values()) == parameter_types
        assert signature.return_annotation == return_type


def test_uprime_attempt_manifest_outputs_are_frozen_slotted(
    tmp_path: Path,
) -> None:
    terminal = _event_mapping("recovery", event_index=2, created_at_utc=TERMINAL_UTC)
    root, _documents, _raws = _write_chain(
        tmp_path,
        [_event_mapping(), terminal],
        root_name="frozen-outputs",
    )
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    )
    for value, field_name in (
        (inspection, "origin_status"),
        (attestation, "authority_scope"),
    ):
        assert not hasattr(value, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            setattr(value, field_name, "forged")


def test_uprime_attempt_manifest_sorts_entries_and_keeps_selection_local(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = _event_mapping("recovery", event_index=2, created_at_utc=TERMINAL_UTC)
    root, _documents, _raws = _write_chain(
        tmp_path,
        [_event_mapping(), terminal],
        root_name="ordering-selection",
    )
    real_scandir = manifest._os_scandir

    class ReverseScan:
        def __init__(self, target: Any) -> None:
            self._real = real_scandir(target)
            self._entries = iter(reversed(list(self._real)))

        def __iter__(self) -> "ReverseScan":
            return self

        def __next__(self) -> Any:
            return next(self._entries)

        def close(self) -> None:
            self._real.close()

    monkeypatch.setattr(manifest, "_os_scandir", ReverseScan)
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    assert tuple(item.event.event_index for item in inspection.event_files) == (1, 2)

    alternate_id = _receipt_mapping(candidate_commit="7" * 40)["license_id"]
    assert manifest.inspect_local_attempt_manifest_chain_v1_0(
        root,
        alternate_id,
    ).chain_state == "missing"
    orphan = _host_event_path(root, alternate_id, 1).parent
    orphan.mkdir(parents=True)
    (orphan / "unexpected.txt").write_text("synthetic", encoding="utf-8")
    assert manifest.inspect_local_attempt_manifest_chain_v1_0(
        root,
        LICENSE_ID,
    ).chain_state == "valid_terminal"


def test_uprime_attempt_manifest_selected_directory_identity_mismatch_rejects(
    tmp_path: Path,
) -> None:
    receipt = _receipt_mapping(candidate_commit="7" * 40)
    value = _event_mapping(receipt=receipt)
    root = (tmp_path / "selected-mismatch").absolute()
    target = _host_event_path(root, LICENSE_ID, 1)
    target.parent.mkdir(parents=True)
    target.write_bytes(_canonical_event_file(value))
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)


def test_uprime_attempt_manifest_recovery_only_nonterminal_self_loop_is_valid(
    tmp_path: Path,
) -> None:
    values = [
        _event_mapping(),
        _event_mapping(
            "recovery",
            event_index=2,
            created_at_utc="2026-07-11T00:00:02.000000Z",
            terminal_event=False,
            failure_codes=["READER_ERROR"],
        ),
        _event_mapping(
            "recovery",
            event_index=3,
            created_at_utc="2026-07-11T00:00:03.000000Z",
            terminal_event=False,
            failure_codes=["OTHER_ATTEMPT_ERROR"],
        ),
        _event_mapping(
            "recovery",
            event_index=4,
            created_at_utc="2026-07-11T00:00:04.000000Z",
            failure_codes=["POWER_LOSS"],
        ),
    ]
    root, _documents, _raws = _write_chain(
        tmp_path,
        values,
        root_name="recovery-self-loop",
    )
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        root,
        LICENSE_ID,
    )
    assert attestation.event_count == 4
    assert attestation.failure_codes == ("POWER_LOSS",)


@pytest.mark.parametrize("invalid_kind", ["candidate_case", "license_case", "schema"])
def test_uprime_attempt_manifest_fully_rebound_receipt_invalidity_rejects(
    invalid_kind: str,
) -> None:
    if invalid_kind == "candidate_case":
        receipt = _receipt_mapping(candidate_commit="A" * 40)
    elif invalid_kind == "license_case":
        receipt = _receipt_mapping(license_commit="B" * 40)
    else:
        receipt = _receipt_mapping()
        receipt["schema_version"] = "lean-rgc-uprime-u1-claim-receipt-public-v9"
    value = _event_mapping(receipt=receipt)
    _assert_rebound_parse_rejected(value)


def test_uprime_attempt_manifest_public_runtime_argument_types_are_exact(
    tmp_path: Path,
) -> None:
    raw = _canonical_event_file(_event_mapping())
    path = _repository_path(LICENSE_ID, 1)

    class StringSubclass(str):
        pass

    for invalid_path in (Path(path), StringSubclass(path)):
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.parse_attempt_manifest_event_file_v1_0(invalid_path, raw)  # type: ignore[arg-type]
    for invalid_raw in (bytearray(raw), memoryview(raw)):
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.parse_attempt_manifest_event_file_v1_0(path, invalid_raw)  # type: ignore[arg-type]
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.encode_attempt_manifest_event_v1_0(_event_mapping())  # type: ignore[arg-type]

    root = (tmp_path / "runtime-types").absolute()
    for invalid_license in (Path(LICENSE_ID), b"0" * 64, "A" * 64, "0" * 63):
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.inspect_local_attempt_manifest_chain_v1_0(
                root,
                invalid_license,  # type: ignore[arg-type]
            )
        with pytest.raises(manifest.AttemptManifestV10Error):
            manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
                root,
                invalid_license,  # type: ignore[arg-type]
            )
    with pytest.raises(manifest.AttemptManifestV10Error):
        manifest.inspect_local_attempt_manifest_chain_v1_0(b"absolute", LICENSE_ID)  # type: ignore[arg-type]


def _source_import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            targets.add(node.module or "")
    return targets


def test_uprime_attempt_manifest_public_signatures_and_all_are_exact() -> None:
    expected = {
        "encode_attempt_manifest_event_v1_0": ("event",),
        "parse_attempt_manifest_event_file_v1_0": ("repository_path", "raw"),
        "inspect_local_attempt_manifest_chain_v1_0": ("root", "license_id"),
        "verify_local_attempt_manifest_terminal_chain_v1_0": (
            "root",
            "license_id",
        ),
    }
    for name, parameter_names in expected.items():
        signature = inspect.signature(getattr(manifest, name))
        assert tuple(signature.parameters) == parameter_names
        assert all(
            parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            for parameter in signature.parameters.values()
        )
        assert all(
            parameter.default is inspect.Parameter.empty
            for parameter in signature.parameters.values()
        )
    assert type(manifest.__all__) is list
    assert manifest.__all__ == [
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


def test_uprime_attempt_manifest_source_import_ast_is_exact_and_read_only() -> None:
    source_path = Path(manifest.__file__).resolve()
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    assert _source_import_targets(tree) == {
        "dataclasses",
        "datetime",
        "hashlib",
        "os",
        "re",
        "stat",
        "lean_rgc.evals.uprime_rpc_ledger",
    }
    forbidden_os_calls = {
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


def test_uprime_attempt_manifest_production_raising_sentinels_are_unreached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lean_rgc.evals import uprime_rpc_bundle_reservation as reservation
    from lean_rgc.evals import uprime_rpc_contract_oracle as contract_oracle
    from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics
    from lean_rgc.evals import uprime_rpc_litmus as litmus

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("production or prior-phase capability was reached")

    monkeypatch.setattr(litmus, "run_diagnostic", forbidden)
    monkeypatch.setattr(litmus, "_reserve_output", forbidden)
    monkeypatch.setattr(litmus, "_publish_reserved_json", forbidden)
    monkeypatch.setattr(reservation, "inspect_standalone_bundle_reservation_v1_1", forbidden)
    monkeypatch.setattr(contract_oracle, "attest_standalone_exact_49_contracts", forbidden)
    monkeypatch.setattr(semantics, "attest_standalone_nominal_49_semantics", forbidden)
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        _repository_path(LICENSE_ID, 1),
        _canonical_event_file(_event_mapping()),
    )
    missing = manifest.inspect_local_attempt_manifest_chain_v1_0(
        (tmp_path / "missing").absolute(),
        LICENSE_ID,
    )
    assert parsed.event.event_type == "claim_started"
    assert missing.chain_state == "missing"


def test_uprime_attempt_manifest_default_deny_registry_remains_byte_identical() -> None:
    from lean_rgc.evals.uprime_rerun_license import (
        RERUN_REGISTRY_PATH,
        UPrimeRerunLicenseError,
        load_rerun_registry,
        reject_canonical_rerun_bootstrap,
    )

    registry_path = Path(RERUN_REGISTRY_PATH)
    expected = (
        b'{"default_allow":false,"licenses":{},"schema_version":'
        b'"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n'
    )
    before = registry_path.read_bytes()
    assert before == expected
    assert len(before) == 96
    assert before[-1:] == b"\n"
    assert hashlib.sha256(before).hexdigest().upper() == (
        "ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B"
    )
    registry = load_rerun_registry(registry_path)
    assert registry["default_allow"] is False
    assert registry["licenses"] == {}
    with pytest.raises(UPrimeRerunLicenseError):
        reject_canonical_rerun_bootstrap(Path.cwd(), "0" * 40)
    assert registry_path.read_bytes() == before

    expected_blob = "13ffca6de484effc66f0e628d2e46823277271c6"
    local_blob = subprocess.run(
        ["git", "hash-object", os.fspath(registry_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    head_blob = subprocess.run(
        ["git", "rev-parse", f"HEAD:{registry_path.as_posix()}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    assert local_blob == head_blob == expected_blob
    committed = subprocess.run(
        ["git", "cat-file", "-p", expected_blob],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    assert committed == expected
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", os.fspath(registry_path)],
        check=True,
    )


def test_uprime_attempt_manifest_read_only_api_creates_no_files(tmp_path: Path) -> None:
    root = (tmp_path / "never-created").absolute()
    before = tuple(tmp_path.rglob("*"))
    inspection = manifest.inspect_local_attempt_manifest_chain_v1_0(root, LICENSE_ID)
    after = tuple(tmp_path.rglob("*"))
    assert inspection.chain_state == "missing"
    assert after == before


def test_uprime_attempt_manifest_support_all_exports_each_test_once() -> None:
    expected = sorted(
        name
        for name, value in globals().items()
        if name.startswith("test_uprime_attempt_manifest_")
        and inspect.isfunction(value)
        and value.__module__ == __name__
    )
    assert __all__ == expected
    assert len(__all__) == len(set(__all__))


__all__ = sorted(
    name
    for name, value in globals().items()
    if name.startswith("test_uprime_attempt_manifest_")
    and inspect.isfunction(value)
    and value.__module__ == __name__
)
