"""Noncollectable Phase-2b2a seeded/local inventory acceptance cases.

The frozen collector imports only the test functions exported by ``__all__``.
All filesystem fixtures are small synthetic objects below ``tmp_path``.
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
from lean_rgc.evals import uprime_rpc_seed_inventory as inventory
from uprime_rpc_attempt_manifest_cases import (
    _event_mapping as _attempt_event_mapping,
    _event_record as _attempt_event_record,
    _fake_stat as _attempt_fake_stat,
    _host_event_path as _attempt_host_event_path,
    _write_chain as _attempt_write_chain,
)


SEED_SCHEMA = "lean-rgc-uprime-u1-synthetic-claim-seed-v1.0"
SEED_SCOPE = "caller_supplied_synthetic_claims_only"
RECEIPT_SCHEMA = "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
RECEIPT_DOMAIN = b"lean-rgc-uprime-u1-attempt-v1\0"
SEED_DOMAIN = b"lean-rgc-uprime-u1-synthetic-claim-seed-v1\0"
REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
REMOTE_BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"
CLAIM_REF_PREFIX = "refs/tags/uprime-u1-attempts/"

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
SEED_FIELDS = (
    "schema_version",
    "seed_scope",
    "origin_status",
    "seed_file_sha256",
    "seed_identity_sha256",
    "seed_bytes",
    "claim_receipts",
    "claim_count",
    "inventory_completeness",
    "omitted_claim_detectability",
    "remote_inventory_observation",
    "seed_temporal_commitment",
    "authority_scope",
    "licenses_execution",
    "licenses_publication",
    "licenses_later_stage",
)
CLAIM_AUDIT_FIELDS = (
    "license_id",
    "seed_membership",
    "local_membership",
    "set_relation",
    "receipt_relation",
    "seed_receipt_sha256",
    "local_receipt_sha256",
    "chain_observation",
    "event_count",
    "last_event_index",
    "last_event_sha256",
    "terminal_event",
    "recorded_verdict",
    "authority_scope",
    "licenses_execution",
    "licenses_later_stage",
)
AUDIT_FIELDS = (
    "auditor_schema_version",
    "auditor_scope",
    "origin_status",
    "base_directory_status",
    "seed_file_sha256",
    "seed_identity_sha256",
    "seed_count",
    "local_directory_count",
    "union_claim_count",
    "examined_claim_count",
    "total_observed_event_bytes",
    "read_work_upper_bound_bytes",
    "event_file_admission_upper_bound",
    "claim_audits",
    "unexpected_entry_names",
    "unexpected_entry_count",
    "seeded_missing_ids",
    "local_orphan_ids",
    "receipt_mismatch_ids",
    "terminal_ids",
    "nonterminal_ids",
    "empty_chain_ids",
    "coverage_status",
    "set_equality",
    "all_seeded_local_present",
    "all_seeded_terminal",
    "all_seeded_receipts_match",
    "seed_origin",
    "seed_binding",
    "seed_temporal_commitment",
    "remote_inventory_observation",
    "real_claim_completeness",
    "omitted_claim_detectability",
    "coordinated_omission_detectability",
    "root_scope",
    "snapshot_scope",
    "resource_status",
    "authority_scope",
    "canonical_run_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

EMPTY_SEED_RAW = (
    b'{"claim_receipts":[],"schema_version":'
    b'"lean-rgc-uprime-u1-synthetic-claim-seed-v1.0",'
    b'"seed_scope":"caller_supplied_synthetic_claims_only"}\n'
)
EMPTY_SEED_SHA256 = "6282E9A084AF7D2B0EC416944D9A45B26F53356EE9A64D221775D5F3B28E0785"
EMPTY_SEED_IDENTITY = "0D216ACBFD064E018B96C1F6FE7CD0291E649876E5DC24F5BBF0D14686F8CC8D"
ONE_SEED_BYTES = 1073
ONE_SEED_SHA256 = "B26EEE7631C9C18B965AEC8D4D85A0DEEDFFA154C548BAC63FC5DE0F06376BBE"
ONE_SEED_IDENTITY = "BBA6C161772138B8078679E21CBC59DECFC1BD84B8E190AD4B8D49AA637B2AB0"


def _license_id(candidate_commit: str) -> str:
    return hashlib.sha256(
        RECEIPT_DOMAIN + candidate_commit.encode("ascii")
    ).hexdigest()


def _receipt_mapping(
    candidate_commit: str = "a" * 40,
    license_commit: str = "b" * 40,
) -> dict[str, Any]:
    license_id = _license_id(candidate_commit)
    return {
        "schema_version": RECEIPT_SCHEMA,
        "candidate_commit": candidate_commit,
        "license_commit": license_commit,
        "license_id": license_id,
        "remote_url": REMOTE_URL,
        "remote_branch_ref": REMOTE_BRANCH_REF,
        "remote_claim_ref": CLAIM_REF_PREFIX + license_id,
        "remote_claim_oid": license_commit,
        "registry_blob_oid": "c" * 40,
        "registry_sha256": "D" * 64,
        "candidate_tree_oid": "e" * 40,
        "input_manifest_sha256": "F" * 64,
        "claimed_at_utc": "2026-07-11T00:00:00.000000Z",
    }


def _receipt_record(value: dict[str, Any] | None = None) -> manifest.PublicClaimReceiptV10:
    return manifest.PublicClaimReceiptV10(
        **copy.deepcopy(_receipt_mapping() if value is None else value)
    )


def _receipt_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(ledger.canonical_json_bytes(value)).hexdigest().upper()


def _seed_mapping(
    receipts: list[dict[str, Any]] | None = None,
    *,
    sort_receipts: bool = True,
) -> dict[str, Any]:
    values = copy.deepcopy([] if receipts is None else receipts)
    if sort_receipts:
        values.sort(key=lambda item: item["license_id"])
    return {
        "schema_version": SEED_SCHEMA,
        "seed_scope": SEED_SCOPE,
        "claim_receipts": values,
    }


def _seed_raw(
    receipts: list[dict[str, Any]] | None = None,
    *,
    sort_receipts: bool = True,
) -> bytes:
    return ledger.canonical_json_bytes(
        _seed_mapping(receipts, sort_receipts=sort_receipts)
    ) + b"\n"


def _seed_hashes(raw: bytes) -> tuple[str, str]:
    file_sha = hashlib.sha256(raw).hexdigest().upper()
    identity = hashlib.sha256(
        SEED_DOMAIN + len(raw).to_bytes(8, "big") + raw
    ).hexdigest().upper()
    return file_sha, identity


def _base(root: Path) -> Path:
    return root / "docs" / "experiments" / "artifacts" / "uprime_u1_rpc_attempts"


def _claim_dir(root: Path, license_id: str) -> Path:
    return _base(root) / license_id


def _write_chain_for_receipt(
    tmp_path: Path,
    receipt: dict[str, Any],
    *,
    terminal: bool,
    root_name: str,
) -> Path:
    values = [_attempt_event_mapping(receipt=receipt)]
    if terminal:
        values.append(
            _attempt_event_mapping(
                "recovery",
                event_index=2,
                created_at_utc="2026-07-11T00:00:02.000000Z",
                receipt=receipt,
                failure_codes=["POWER_LOSS"],
            )
        )
    root, _documents, _raws = _attempt_write_chain(
        tmp_path,
        values,
        root_name=root_name,
    )
    return root


def _fake_event_file(length: int, receipt: dict[str, Any]) -> manifest.AttemptManifestEventFileV10:
    event = _attempt_event_record(_attempt_event_mapping(receipt=receipt))
    return manifest.AttemptManifestEventFileV10(
        repository_path=(
            "docs/experiments/artifacts/uprime_u1_rpc_attempts/"
            f"{receipt['license_id']}/0001.json"
        ),
        event_sha256="A" * 64,
        event_bytes=b"x" * length,
        event=event,
    )


def _fake_inspection(
    receipt: dict[str, Any],
    *,
    chain_state: str = "valid_terminal",
    payload_lengths: tuple[int, ...] = (),
) -> manifest.AttemptManifestChainInspectionV10:
    missing = chain_state == "missing"
    terminal = chain_state == "valid_terminal"
    event_files = tuple(_fake_event_file(n, receipt) for n in payload_lengths)
    if not missing and not event_files:
        event_files = (_fake_event_file(1, receipt),)
    count = 0 if missing else (9_999 if chain_state == "valid_nonterminal_index_exhausted" else len(event_files))
    last_index = None if missing else (9_999 if chain_state == "valid_nonterminal_index_exhausted" else count)
    return manifest.AttemptManifestChainInspectionV10(
        inspector_schema_version="lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1",
        inspector_scope="local_preartifact_chain_structure_only",
        origin_status="unknown_may_be_synthetic",
        license_id=receipt["license_id"],
        chain_state=chain_state,
        event_files=event_files,
        event_count=count,
        first_event_sha256=None if missing else "A" * 64,
        last_event_index=last_index,
        last_event_sha256=None if missing else "B" * 64,
        last_event_type=None if missing else ("recovery" if terminal else "claim_started"),
        terminal_event=False if missing else terminal,
        recorded_verdict=None,
        next_event_index=(
            1
            if missing
            else (
                None
                if terminal or chain_state == "valid_nonterminal_index_exhausted"
                else count + 1
            )
        ),
        claim_receipt=None if missing else _receipt_record(receipt),
        claim_receipt_sha256=None if missing else _receipt_sha256(receipt),
    )


class _FakeDirEntry:
    def __init__(self, name: Any) -> None:
        self.name = name


class _GuardedScandir:
    def __init__(
        self,
        names: list[Any],
        *,
        fail_at: int | None = None,
        close_error: bool = False,
        hard_limit: int | None = None,
    ) -> None:
        self._entries = [_FakeDirEntry(name) for name in names]
        self._index = 0
        self.fail_at = fail_at
        self.close_error = close_error
        self.hard_limit = hard_limit
        self.closed = 0

    def __iter__(self) -> "_GuardedScandir":
        return self

    def __next__(self) -> _FakeDirEntry:
        if self.hard_limit is not None and self._index >= self.hard_limit:
            raise AssertionError("scandir consumed beyond the frozen max+1")
        if self.fail_at is not None and self._index + 1 == self.fail_at:
            raise OSError("injected scandir iteration failure")
        if self._index >= len(self._entries):
            raise StopIteration
        entry = self._entries[self._index]
        self._index += 1
        return entry

    @property
    def yielded(self) -> int:
        return self._index

    def close(self) -> None:
        self.closed += 1
        if self.close_error:
            raise OSError("injected scandir close failure")


class _ScandirSequence:
    def __init__(self, scans: list[_GuardedScandir]) -> None:
        self.scans = scans
        self.calls = 0

    def __call__(self, _path: Any) -> _GuardedScandir:
        if self.calls >= len(self.scans):
            raise AssertionError("unexpected extra scandir call")
        result = self.scans[self.calls]
        self.calls += 1
        return result


class _StatefulRoot:
    def __init__(self, first: str, second: str) -> None:
        self.first = first
        self.second = second
        self.calls = 0

    def __fspath__(self) -> str:
        self.calls += 1
        return self.first if self.calls == 1 else self.second


def _source_imports(tree: ast.AST) -> tuple[set[str], dict[str, set[str]]]:
    modules: set[str] = set()
    names: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.add(module)
            names.setdefault(module, set()).update(alias.name for alias in node.names)
    return modules, names


def _ast_qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _ast_qualified_name(node.value)
        if prefix is not None:
            return f"{prefix}.{node.attr}"
    return None


def _ast_bound_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(
            name for item in node.elts for name in _ast_bound_names(item)
        )
    return ()


def _tree_metadata_snapshot(root: Path) -> tuple[tuple[str, int, int, int], ...]:
    if not root.exists():
        return (("<absent>", 0, 0, 0),)
    result: list[tuple[str, int, int, int]] = []
    paths = [root, *root.rglob("*")]
    paths.sort(key=lambda path: os.fspath(path.relative_to(root)).encode("utf-8"))
    for path in paths:
        observed = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        result.append(
            (
                relative,
                inventory.stat.S_IFMT(int(observed.st_mode)),
                int(observed.st_size),
                int(observed.st_mtime_ns),
            )
        )
    return tuple(result)


def _exposure_marker_paths() -> tuple[str, ...]:
    markers: list[str] = []
    for root in (
        Path("docs/experiments"),
        Path("runs/uprime_u1_rpc_20260710"),
    ):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            folded = path.name.casefold()
            if any(token in folded for token in ("exposure", "burn", "retir", "read_ledger")):
                markers.append(path.as_posix())
    return tuple(sorted(markers))


def test_uprime_seed_inventory_independent_golden_seed_bytes_and_hashes() -> None:
    assert len(EMPTY_SEED_RAW) == 139
    assert _seed_hashes(EMPTY_SEED_RAW) == (EMPTY_SEED_SHA256, EMPTY_SEED_IDENTITY)
    empty = inventory.parse_synthetic_claim_seed_v1_0(EMPTY_SEED_RAW)
    assert tuple(field.name for field in fields(empty)) == SEED_FIELDS
    assert asdict(empty) == {
        "schema_version": SEED_SCHEMA,
        "seed_scope": SEED_SCOPE,
        "origin_status": "unknown_may_be_synthetic",
        "seed_file_sha256": EMPTY_SEED_SHA256,
        "seed_identity_sha256": EMPTY_SEED_IDENTITY,
        "seed_bytes": 139,
        "claim_receipts": (),
        "claim_count": 0,
        "inventory_completeness": "not_authenticated_may_omit_claims",
        "omitted_claim_detectability": "none_outside_supplied_seed",
        "remote_inventory_observation": "not_performed",
        "seed_temporal_commitment": "not_authenticated",
        "authority_scope": "none",
        "licenses_execution": False,
        "licenses_publication": False,
        "licenses_later_stage": False,
    }

    raw = _seed_raw([_receipt_mapping()])
    assert len(raw) == ONE_SEED_BYTES
    assert _seed_hashes(raw) == (ONE_SEED_SHA256, ONE_SEED_IDENTITY)
    parsed = inventory.parse_synthetic_claim_seed_v1_0(raw)
    assert parsed.seed_file_sha256 == ONE_SEED_SHA256
    assert parsed.seed_identity_sha256 == ONE_SEED_IDENTITY
    assert parsed.claim_count == 1
    assert parsed.claim_receipts[0].license_id == _license_id("a" * 40)


def test_uprime_seed_inventory_two_receipt_order_and_domain_formula() -> None:
    receipts = [_receipt_mapping("a" * 40), _receipt_mapping("7" * 40)]
    raw = _seed_raw(receipts)
    parsed = inventory.parse_synthetic_claim_seed_v1_0(raw)
    assert tuple(item.license_id for item in parsed.claim_receipts) == tuple(
        sorted(item["license_id"] for item in receipts)
    )
    assert len(raw) == 2008
    assert parsed.seed_file_sha256 == (
        "604AACA104B73A391F8E2242D2DB6DA0A03365244D6BED510429DF835798BF62"
    )
    assert parsed.seed_identity_sha256 == (
        "E090FACB32B30FF96408BDA9E4760EA2954D391567D3E9548529890D74626F25"
    )


def test_uprime_seed_inventory_seed_record_is_frozen_slotted_and_immutable() -> None:
    source = _receipt_mapping()
    raw = _seed_raw([source])
    parsed = inventory.parse_synthetic_claim_seed_v1_0(raw)
    source["license_commit"] = "8" * 40
    assert parsed.claim_receipts[0].license_commit == "b" * 40
    assert type(parsed.claim_receipts) is tuple
    assert not hasattr(parsed, "__dict__")
    assert not hasattr(parsed.claim_receipts[0], "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        parsed.seed_scope = "forged"  # type: ignore[misc]


def _noncanonical_seed_cases() -> list[tuple[str, bytes]]:
    raw = _seed_raw([_receipt_mapping()])
    canonical = raw[:-1]
    mapping = json.loads(canonical)
    reversed_raw = json.dumps(
        dict(reversed(list(mapping.items()))),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    duplicate_top = b'{"claim_receipts":[],' + canonical[1:] + b"\n"
    duplicate_nested = canonical.replace(
        b'"candidate_commit":',
        b'"candidate_commit":"0","candidate_commit":',
        1,
    ) + b"\n"
    float_raw = canonical.replace(b'"candidate_commit":"' + b"a" * 40 + b'"', b'"candidate_commit":1.5') + b"\n"
    nan_raw = canonical.replace(b'"candidate_commit":"' + b"a" * 40 + b'"', b'"candidate_commit":NaN') + b"\n"
    inf_raw = canonical.replace(b'"candidate_commit":"' + b"a" * 40 + b'"', b'"candidate_commit":Infinity') + b"\n"
    surrogate = canonical.replace(
        b'"seed_scope":"caller_supplied_synthetic_claims_only"',
        b'"seed_scope":"\\ud800"',
    ) + b"\n"
    return [
        ("bom", b"\xef\xbb\xbf" + raw),
        ("crlf", canonical + b"\r\n"),
        ("missing-lf", canonical),
        ("extra-lf", raw + b"\n"),
        ("leading-space", b" " + raw),
        ("trailing-space", canonical + b" \n"),
        ("key-order", reversed_raw),
        ("duplicate-top", duplicate_top),
        ("duplicate-nested", duplicate_nested),
        ("invalid-utf8", canonical[:-1] + b"\xff}\n"),
        ("float", float_raw),
        ("nan", nan_raw),
        ("infinity", inf_raw),
        ("surrogate", surrogate),
        ("trailing-object", canonical + b"{}\n"),
    ]


@pytest.mark.parametrize("case_index", range(15))
def test_uprime_seed_inventory_noncanonical_seed_wire_rejects(case_index: int) -> None:
    label, raw = _noncanonical_seed_cases()[case_index]
    assert label
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(raw)


@pytest.mark.parametrize("field", ("schema_version", "seed_scope", "claim_receipts"))
def test_uprime_seed_inventory_every_top_field_is_required(field: str) -> None:
    value = _seed_mapping([_receipt_mapping()])
    del value[field]
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(ledger.canonical_json_bytes(value) + b"\n")


@pytest.mark.parametrize("field", RECEIPT_FIELDS)
def test_uprime_seed_inventory_every_receipt_field_is_required(field: str) -> None:
    value = _seed_mapping([_receipt_mapping()])
    del value["claim_receipts"][0][field]
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(ledger.canonical_json_bytes(value) + b"\n")


@pytest.mark.parametrize(
    ("scope", "field"),
    [("top", item) for item in ("schema_version", "seed_scope", "claim_receipts")]
    + [("receipt", item) for item in RECEIPT_FIELDS],
)
def test_uprime_seed_inventory_wrong_primitive_types_reject(
    scope: str, field: str
) -> None:
    value = _seed_mapping([_receipt_mapping()])
    target = value if scope == "top" else value["claim_receipts"][0]
    if field == "claim_receipts":
        replacement: Any = "not-an-array"
    else:
        replacement = []
    target[field] = replacement
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(ledger.canonical_json_bytes(value) + b"\n")


@pytest.mark.parametrize(
    ("scope", "field"),
    [("top", item) for item in ("schema_version", "seed_scope", "claim_receipts")]
    + [("receipt", item) for item in RECEIPT_FIELDS],
)
def test_uprime_seed_inventory_bool_confusion_rejects(scope: str, field: str) -> None:
    value = _seed_mapping([_receipt_mapping()])
    target = value if scope == "top" else value["claim_receipts"][0]
    target[field] = True
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(ledger.canonical_json_bytes(value) + b"\n")


@pytest.mark.parametrize("scope", ("top", "receipt"))
def test_uprime_seed_inventory_extra_seed_keys_reject(scope: str) -> None:
    value = _seed_mapping([_receipt_mapping()])
    target = value if scope == "top" else value["claim_receipts"][0]
    target["attacker_extra"] = "not-ignored"
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(ledger.canonical_json_bytes(value) + b"\n")


@pytest.mark.parametrize("kind", ("str", "bytearray", "memoryview", "subclass"))
def test_uprime_seed_inventory_raw_requires_exact_bytes(kind: str) -> None:
    raw = _seed_raw([_receipt_mapping()])
    if kind == "str":
        invalid: Any = raw.decode("utf-8")
    elif kind == "bytearray":
        invalid = bytearray(raw)
    elif kind == "memoryview":
        invalid = memoryview(raw)
    else:
        class BytesSubclass(bytes):
            pass

        invalid = BytesSubclass(raw)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(invalid)


@pytest.mark.parametrize(("delta", "accepted"), [(1, True), (0, True), (-1, False)])
def test_uprime_seed_inventory_injected_seed_byte_bound_is_inclusive(
    monkeypatch: pytest.MonkeyPatch, delta: int, accepted: bool
) -> None:
    raw = _seed_raw([_receipt_mapping()])
    monkeypatch.setattr(inventory, "_MAX_SEED_BYTES", len(raw) + delta)
    if accepted:
        assert inventory.parse_synthetic_claim_seed_v1_0(raw).claim_count == 1
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.parse_synthetic_claim_seed_v1_0(raw)


@pytest.mark.parametrize(("count", "accepted"), [(1, True), (2, True), (3, False)])
def test_uprime_seed_inventory_injected_claim_count_bound(
    monkeypatch: pytest.MonkeyPatch, count: int, accepted: bool
) -> None:
    receipts = [_receipt_mapping(f"{digit:x}" * 40) for digit in range(1, count + 1)]
    monkeypatch.setattr(inventory, "_MAX_SEEDED_CLAIMS", 2)
    raw = _seed_raw(receipts)
    if accepted:
        assert inventory.parse_synthetic_claim_seed_v1_0(raw).claim_count == count
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.parse_synthetic_claim_seed_v1_0(raw)


def test_uprime_seed_inventory_unsorted_and_duplicate_receipts_reject() -> None:
    receipts = [_receipt_mapping("a" * 40), _receipt_mapping("7" * 40)]
    sorted_receipts = sorted(receipts, key=lambda value: value["license_id"])
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(
            _seed_raw(list(reversed(sorted_receipts)), sort_receipts=False)
        )
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.parse_synthetic_claim_seed_v1_0(
            _seed_raw([receipts[0], copy.deepcopy(receipts[0])], sort_receipts=False)
        )


@pytest.mark.parametrize("mutation", ("candidate", "license", "ref", "utc"))
def test_uprime_seed_inventory_receipt_constructor_errors_are_wrapped(mutation: str) -> None:
    receipt = _receipt_mapping()
    if mutation == "candidate":
        receipt["candidate_commit"] = "A" * 40
    elif mutation == "license":
        receipt["license_commit"] = "B" * 40
        receipt["remote_claim_oid"] = "B" * 40
    elif mutation == "ref":
        receipt["remote_claim_ref"] = CLAIM_REF_PREFIX + "0" * 64
    else:
        receipt["claimed_at_utc"] = "2026-02-30T00:00:00.000000Z"
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error) as exc:
        inventory.parse_synthetic_claim_seed_v1_0(_seed_raw([receipt]))
    assert type(exc.value) is inventory.SyntheticSeedInventoryV10Error


def test_uprime_seed_inventory_missing_and_empty_base_statuses(tmp_path: Path) -> None:
    missing_root = (tmp_path / "missing-root").absolute()
    missing = inventory.audit_synthetic_seed_local_inventory_v1_0(
        missing_root, EMPTY_SEED_RAW
    )
    assert tuple(field.name for field in fields(missing)) == AUDIT_FIELDS
    assert missing.base_directory_status == "absent"
    assert missing.coverage_status == "empty_seed"
    assert missing.seed_count == missing.local_directory_count == 0
    assert missing.examined_claim_count == missing.union_claim_count == 0

    empty_root = (tmp_path / "empty-root").absolute()
    _base(empty_root).mkdir(parents=True)
    present = inventory.audit_synthetic_seed_local_inventory_v1_0(
        empty_root, EMPTY_SEED_RAW
    )
    assert present.base_directory_status == "present"
    assert present.coverage_status == "empty_seed"
    assert present.claim_audits == ()
    assert present.unexpected_entry_names == ()


def test_uprime_seed_inventory_exact_negative_aggregate_suffix(tmp_path: Path) -> None:
    root = (tmp_path / "negative-suffix").absolute()
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert result.auditor_schema_version == (
        "lean-rgc-uprime-u1-seed-local-inventory-auditor-v0.1"
    )
    assert result.auditor_scope == "caller_seed_vs_entire_local_attempt_namespace"
    assert result.origin_status == "unknown_may_be_synthetic"
    assert result.seed_origin == "caller_supplied_synthetic_bytes"
    assert result.seed_binding == "exact_bytes_within_call"
    assert result.seed_temporal_commitment == "not_authenticated"
    assert result.remote_inventory_observation == "not_performed"
    assert result.real_claim_completeness == "not_authenticated"
    assert result.omitted_claim_detectability == (
        "local_orphans_only_none_if_absent_from_both"
    )
    assert result.coordinated_omission_detectability == "none"
    assert result.root_scope == "one_caller_supplied_synthetic_root"
    assert result.snapshot_scope == (
        "sequential_per_claim_observations_not_atomic_inventory"
    )
    assert result.resource_status == "within_frozen_bounds"
    assert result.authority_scope == "none"
    assert result.canonical_run_authority is False
    assert result.licenses_execution is False
    assert result.licenses_publication is False
    assert result.licenses_recovery is False
    assert result.licenses_later_stage is False


@pytest.mark.parametrize("kind", ("empty", "relative", "bytes", "bytes-pathlike"))
def test_uprime_seed_inventory_root_requires_absolute_exact_text(
    tmp_path: Path, kind: str
) -> None:
    if kind == "empty":
        root: Any = ""
    elif kind == "relative":
        root = "relative-sandbox"
    elif kind == "bytes":
        root = os.fsencode(tmp_path)
    else:
        class BytesPath:
            def __fspath__(self) -> bytes:
                return os.fsencode(tmp_path)

        root = BytesPath()
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)


def test_uprime_seed_inventory_root_pathlike_is_evaluated_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = os.fspath((tmp_path / "first").absolute())
    second = os.fspath((tmp_path / "poison").absolute())
    receipt = _receipt_mapping()
    _claim_dir(Path(first), receipt["license_id"]).mkdir(parents=True)
    root = _StatefulRoot(first, second)
    calls: list[tuple[Any, str]] = []

    def inspect(retained_root: Any, license_id: str) -> manifest.AttemptManifestChainInspectionV10:
        calls.append((retained_root, license_id))
        return _fake_inspection(receipt)

    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    assert result.base_directory_status == "present"
    assert result.coverage_status == "matched_terminal"
    assert root.calls == 1
    assert calls == [(first, receipt["license_id"])]
    assert not Path(second).exists()


def test_uprime_seed_inventory_preserves_absolute_lexical_root_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt_mapping()
    actual_root = tmp_path.absolute() / "MiXeD-Root"
    lexical_component = actual_root / "Retained-DotDot"
    lexical_component.mkdir(parents=True)
    root_text = os.fspath(lexical_component / "..")
    assert os.path.isabs(root_text)
    assert ".." in Path(root_text).parts
    _claim_dir(actual_root, receipt["license_id"]).mkdir(parents=True)
    real_join = inventory._os_path_join
    joins: list[tuple[Any, ...]] = []
    inspections: list[tuple[Any, str]] = []

    def observed_join(*parts: Any) -> str:
        joins.append(parts)
        return real_join(*parts)

    def inspect(
        retained_root: Any, license_id: str
    ) -> manifest.AttemptManifestChainInspectionV10:
        inspections.append((retained_root, license_id))
        return _fake_inspection(receipt)

    monkeypatch.setattr(inventory, "_os_path_join", observed_join)
    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root_text, _seed_raw([receipt])
    )
    assert result.coverage_status == "matched_terminal"
    assert joins[0] == (root_text, "docs", "experiments", "artifacts", "uprime_u1_rpc_attempts")
    assert inspections == [(root_text, receipt["license_id"])]


def test_uprime_seed_inventory_audit_reparses_raw_not_mutated_seed(
    tmp_path: Path,
) -> None:
    raw = _seed_raw([_receipt_mapping()])
    parsed = inventory.parse_synthetic_claim_seed_v1_0(raw)
    object.__setattr__(parsed, "seed_identity_sha256", "0" * 64)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        (tmp_path / "reparse").absolute(), raw
    )
    assert result.seed_identity_sha256 == ONE_SEED_IDENTITY
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(
            (tmp_path / "wrong-object").absolute(), parsed  # type: ignore[arg-type]
        )


def test_uprime_seed_inventory_base_appearance_between_absent_observations_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "appearing").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    calls = 0

    def first_absent_then_present(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise FileNotFoundError("injected first absence")
        return real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(inventory, "_os_stat", first_absent_then_present)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert calls == 2


@pytest.mark.parametrize(
    "field", ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_mtime_ns")
)
def test_uprime_seed_inventory_base_drift_between_observations_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    root = (tmp_path / "base-drift").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    calls = 0

    def drift_final_base(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal calls
        observed = real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(target))) == os.path.normcase(
            os.path.abspath(base)
        ):
            calls += 1
            if calls == 2:
                value = int(getattr(observed, field))
                changed = value ^ 0o200 if field == "st_mode" else value + 1
                return _attempt_fake_stat(observed, **{field: changed})
        return observed

    monkeypatch.setattr(inventory, "_os_stat", drift_final_base)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert calls == 2


@pytest.mark.parametrize("kind", ("non-directory", "symlink", "reparse"))
def test_uprime_seed_inventory_initial_base_type_sentinels_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    root = (tmp_path / f"base-{kind}").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    if kind == "reparse":
        monkeypatch.setattr(inventory.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400, raising=False)

    def sentinel(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        observed = real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(target))) != os.path.normcase(
            os.path.abspath(base)
        ):
            return observed
        if kind == "non-directory":
            return _attempt_fake_stat(observed, st_mode=inventory.stat.S_IFREG | 0o644)
        if kind == "symlink":
            return _attempt_fake_stat(observed, st_mode=inventory.stat.S_IFLNK | 0o777)
        return _attempt_fake_stat(observed, st_file_attributes=0x400)

    monkeypatch.setattr(inventory, "_os_stat", sentinel)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)


@pytest.mark.parametrize(
    ("scope", "field"),
    tuple(
        ("base", field)
        for field in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_ctime_ns",
            "st_mtime_ns",
            "st_file_attributes",
        )
    )
    + tuple(
        ("candidate", field)
        for field in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_ctime_ns",
            "st_size",
            "st_mtime_ns",
            "st_file_attributes",
        )
    ),
)
def test_uprime_seed_inventory_metadata_components_reject_bool_as_nonexact_int(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
    field: str,
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "mb").absolute()
    target = _claim_dir(root, receipt["license_id"])
    target.mkdir(parents=True)
    selected = _base(root) if scope == "base" else target
    selected_key = os.path.normcase(os.path.abspath(selected))
    real_stat = inventory._os_stat
    if field == "st_file_attributes":
        monkeypatch.setattr(
            inventory.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
            raising=False,
        )

    def bool_metadata(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        observed = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(path))) == selected_key:
            return _attempt_fake_stat(observed, **{field: True})
        return observed

    monkeypatch.setattr(inventory, "_os_stat", bool_metadata)
    raw = EMPTY_SEED_RAW if scope == "base" else _seed_raw([receipt])
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error) as exc:
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, raw)
    assert type(exc.value) is inventory.SyntheticSeedInventoryV10Error


def test_uprime_seed_inventory_reversed_enumeration_is_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "reverse").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    names = ["zeta", "Alpha", "éclair"]
    scans = [_GuardedScandir(list(reversed(names))), _GuardedScandir(names)]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert result.unexpected_entry_names == tuple(
        sorted(names, key=lambda value: value.encode("utf-8"))
    )
    assert result.coverage_status == "mismatched"
    assert [scan.closed for scan in scans] == [1, 1]


@pytest.mark.parametrize(
    "name",
    (
        "A" * 64,
        "０" * 64,
        "short",
        "x" * 240,
        "NUL",
        "CON",
        "file:stream",
        "trailing.",
        "trailing ",
    ),
)
def test_uprime_seed_inventory_safe_noncandidate_names_are_never_joined_or_statted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    root = (tmp_path / "safe-noncandidate").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    real_join = inventory._os_path_join
    child_stats = 0
    child_joins = 0

    def base_only_stat(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal child_stats
        if os.path.normcase(os.path.abspath(os.fspath(target))) != os.path.normcase(
            os.path.abspath(base)
        ):
            child_stats += 1
            raise AssertionError("noncandidate child path was statted")
        return real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def counted_join(*parts: Any) -> str:
        nonlocal child_joins
        if parts and parts[-1] == name:
            child_joins += 1
            raise AssertionError("noncandidate child path was joined")
        return real_join(*parts)

    scans = [_GuardedScandir([name]), _GuardedScandir([name])]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    monkeypatch.setattr(inventory, "_os_stat", base_only_stat)
    monkeypatch.setattr(inventory, "_os_path_join", counted_join)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert result.unexpected_entry_names == (name,)
    assert child_stats == 0
    assert child_joins == 0


@pytest.mark.parametrize("name", ("", ".", "..", "a/b", "a\\b", "nul\x00name", "\udcff"))
def test_uprime_seed_inventory_unsafe_names_reject_before_child_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    root = (tmp_path / "unsafe-name").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    real_join = inventory._os_path_join
    child_stats = 0
    child_joins = 0

    def counted_stat(
        target: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal child_stats
        if os.path.normcase(os.path.abspath(os.fspath(target))) != os.path.normcase(
            os.path.abspath(base)
        ):
            child_stats += 1
        return real_stat(target, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def counted_join(*parts: Any) -> str:
        nonlocal child_joins
        if parts and parts[-1] == name:
            child_joins += 1
        return real_join(*parts)

    scan = _GuardedScandir([name])
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence([scan]))
    monkeypatch.setattr(inventory, "_os_stat", counted_stat)
    monkeypatch.setattr(inventory, "_os_path_join", counted_join)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert scan.closed == 1
    assert child_stats == 0
    assert child_joins == 0


def test_uprime_seed_inventory_duplicate_scan_names_reject_before_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "duplicate-name").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    name = _receipt_mapping()["license_id"]
    scan = _GuardedScandir([name, name])
    real_join = inventory._os_path_join
    real_stat = inventory._os_stat
    child_joins = 0
    child_stats = 0

    def counted_join(*parts: Any) -> str:
        nonlocal child_joins
        if parts and parts[-1] == name:
            child_joins += 1
        return real_join(*parts)

    def counted_stat(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal child_stats
        if os.path.normcase(os.path.abspath(os.fspath(path))) != os.path.normcase(
            os.path.abspath(base)
        ):
            child_stats += 1
        return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence([scan]))
    monkeypatch.setattr(inventory, "_os_path_join", counted_join)
    monkeypatch.setattr(inventory, "_os_stat", counted_stat)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert scan.closed == 1
    assert child_joins == 0
    assert child_stats == 0


def test_uprime_seed_inventory_success_stats_each_candidate_once_per_scan_nofollow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "candidate-stat-count").absolute()
    target = _claim_dir(root, receipt["license_id"])
    target.mkdir(parents=True)
    base = _base(root)
    base_key = os.path.normcase(os.path.abspath(base))
    target_key = os.path.normcase(os.path.abspath(target))
    real_join = inventory._os_path_join
    real_stat = inventory._os_stat
    base_calls = 0
    candidate_calls = 0
    candidate_joins = 0

    def counted_join(*parts: Any) -> str:
        nonlocal candidate_joins
        if parts and parts[-1] == receipt["license_id"]:
            candidate_joins += 1
        return real_join(*parts)

    def counted_stat(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal base_calls, candidate_calls
        key = os.path.normcase(os.path.abspath(os.fspath(path)))
        if key == base_key:
            base_calls += 1
            assert follow_symlinks is False
        elif key == target_key:
            candidate_calls += 1
            assert follow_symlinks is False
        else:
            raise AssertionError(f"unexpected inventory stat path: {path!r}")
        return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(inventory, "_os_path_join", counted_join)
    monkeypatch.setattr(inventory, "_os_stat", counted_stat)
    monkeypatch.setattr(
        inventory,
        "inspect_local_attempt_manifest_chain_v1_0",
        lambda retained_root, license_id: _fake_inspection(receipt),
    )
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    assert result.coverage_status == "matched_terminal"
    assert base_calls == 2
    assert candidate_calls == 2
    assert candidate_joins == 2


def test_uprime_seed_inventory_streaming_max_plus_one_stops_before_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "max-plus-one").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    names = [
        _receipt_mapping(f"{index:x}" * 40)["license_id"]
        for index in range(1, 5)
    ]
    assert len(set(names)) == 4
    assert all(len(name) == 64 and name == name.lower() for name in names)
    scan = _GuardedScandir(names, hard_limit=3)
    real_join = inventory._os_path_join
    real_stat = inventory._os_stat
    child_joins = 0
    child_stats = 0

    def counted_join(*parts: Any) -> str:
        nonlocal child_joins
        if parts and parts[-1] in names:
            child_joins += 1
        return real_join(*parts)

    def counted_stat(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal child_stats
        if os.path.normcase(os.path.abspath(os.fspath(path))) != os.path.normcase(
            os.path.abspath(base)
        ):
            child_stats += 1
        return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(inventory, "_MAX_BASE_ENTRIES", 2)
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence([scan]))
    monkeypatch.setattr(inventory, "_os_path_join", counted_join)
    monkeypatch.setattr(inventory, "_os_stat", counted_stat)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert scan.yielded == 3
    assert scan.closed == 1
    assert child_joins == 0
    assert child_stats == 0


@pytest.mark.parametrize("kind", ("file", "symlink", "reparse"))
def test_uprime_seed_inventory_hex_candidate_nonclaim_types_are_unexpected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    receipt = _receipt_mapping()
    name = receipt["license_id"]
    root = (tmp_path / f"candidate-{kind}").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    target = base / name
    target.write_bytes(b"x")
    real_stat = inventory._os_stat
    if kind == "reparse":
        monkeypatch.setattr(inventory.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400, raising=False)

    def candidate_sentinel(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        observed = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(path))) != os.path.normcase(
            os.path.abspath(target)
        ):
            return observed
        if kind == "symlink":
            return _attempt_fake_stat(observed, st_mode=inventory.stat.S_IFLNK | 0o777)
        if kind == "reparse":
            return _attempt_fake_stat(observed, st_file_attributes=0x400)
        return observed

    monkeypatch.setattr(inventory, "_os_stat", candidate_sentinel)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert result.local_directory_count == 0
    assert result.unexpected_entry_names == (name,)
    assert result.coverage_status == "mismatched"


@pytest.mark.parametrize(
    "field",
    ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_size", "st_mtime_ns"),
)
def test_uprime_seed_inventory_second_scan_candidate_metadata_drift_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "candidate-drift").absolute()
    target = _claim_dir(root, receipt["license_id"])
    target.mkdir(parents=True)
    real_stat = inventory._os_stat
    calls = 0

    def drift_second_candidate(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal calls
        observed = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(path))) == os.path.normcase(
            os.path.abspath(target)
        ):
            calls += 1
            if calls == 2:
                value = int(getattr(observed, field))
                changed = value ^ 0o200 if field == "st_mode" else value + 1
                return _attempt_fake_stat(observed, **{field: changed})
        return observed

    monkeypatch.setattr(inventory, "_os_stat", drift_second_candidate)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, _seed_raw([receipt])
        )
    assert calls == 2


@pytest.mark.parametrize(
    ("first_names", "second_names"),
    (
        (("stable",), ("stable", "inserted")),
        (("stable", "deleted"), ("stable",)),
        (("before",), ("after",)),
    ),
)
def test_uprime_seed_inventory_second_scan_namespace_change_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    first_names: tuple[str, ...],
    second_names: tuple[str, ...],
) -> None:
    root = (tmp_path / "namespace-drift").absolute()
    _base(root).mkdir(parents=True)
    scans = [
        _GuardedScandir(list(first_names)),
        _GuardedScandir(list(second_names)),
    ]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert [scan.closed for scan in scans] == [1, 1]


@pytest.mark.parametrize("kind", ("non-directory", "symlink", "reparse"))
def test_uprime_seed_inventory_final_base_type_sentinels_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    root = (tmp_path / f"final-base-{kind}").absolute()
    base = _base(root)
    base.mkdir(parents=True)
    real_stat = inventory._os_stat
    calls = 0
    if kind == "reparse":
        monkeypatch.setattr(
            inventory.stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            0x400,
            raising=False,
        )

    def final_sentinel(
        path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
    ) -> Any:
        nonlocal calls
        observed = real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if os.path.normcase(os.path.abspath(os.fspath(path))) != os.path.normcase(
            os.path.abspath(base)
        ):
            return observed
        calls += 1
        if calls == 1:
            return observed
        if kind == "non-directory":
            return _attempt_fake_stat(
                observed, st_mode=inventory.stat.S_IFREG | 0o644
            )
        if kind == "symlink":
            return _attempt_fake_stat(
                observed, st_mode=inventory.stat.S_IFLNK | 0o777
            )
        return _attempt_fake_stat(observed, st_file_attributes=0x400)

    monkeypatch.setattr(inventory, "_os_stat", final_sentinel)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert calls == 2


@pytest.mark.parametrize(("count", "accepted"), [(1, True), (2, True), (3, False)])
def test_uprime_seed_inventory_unexpected_count_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    accepted: bool,
) -> None:
    root = (tmp_path / f"unexpected-{count}").absolute()
    _base(root).mkdir(parents=True)
    names = [f"unexpected-{index}" for index in range(count)]
    monkeypatch.setattr(inventory, "_MAX_UNEXPECTED_NAMES", 2)
    scans = [_GuardedScandir(names), _GuardedScandir(names)]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
        assert result.unexpected_entry_count == count
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)


@pytest.mark.parametrize(("count", "accepted"), [(1, True), (2, True), (3, False)])
def test_uprime_seed_inventory_base_entry_count_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    accepted: bool,
) -> None:
    root = (tmp_path / f"base-entry-{count}").absolute()
    _base(root).mkdir(parents=True)
    names = [f"entry-{index}" for index in range(count)]
    monkeypatch.setattr(inventory, "_MAX_BASE_ENTRIES", 2)
    scans = [_GuardedScandir(names), _GuardedScandir(names)]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, EMPTY_SEED_RAW
        )
        assert result.unexpected_entry_count == count
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(
                root, EMPTY_SEED_RAW
            )
        assert scans[0].yielded == 3


@pytest.mark.parametrize(("count", "accepted"), [(1, True), (2, True), (3, False)])
def test_uprime_seed_inventory_local_claim_count_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    accepted: bool,
) -> None:
    receipts = [_receipt_mapping(f"{index:x}" * 40) for index in range(1, count + 1)]
    root = (tmp_path / f"local-count-{count}").absolute()
    for receipt in receipts:
        _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    monkeypatch.setattr(inventory, "_MAX_LOCAL_CLAIM_DIRS", 2)
    inspector_calls = 0
    if not accepted:
        def forbidden_inspector(*args: Any, **kwargs: Any) -> Any:
            nonlocal inspector_calls
            inspector_calls += 1
            raise AssertionError("local-count rejection must precede inspection")

        monkeypatch.setattr(
            inventory,
            "inspect_local_attempt_manifest_chain_v1_0",
            forbidden_inspector,
        )
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, EMPTY_SEED_RAW
        )
        assert result.local_directory_count == count
        assert result.union_claim_count == count
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(
                root, EMPTY_SEED_RAW
            )
        assert inspector_calls == 0


@pytest.mark.parametrize(("count", "accepted"), [(1, True), (2, True), (3, False)])
def test_uprime_seed_inventory_union_claim_count_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    accepted: bool,
) -> None:
    receipts = [_receipt_mapping(f"{index:x}" * 40) for index in range(1, 4)]
    if count == 1:
        seeded = receipts[:1]
        local: list[dict[str, Any]] = []
    elif count == 2:
        seeded = receipts[:1]
        local = receipts[1:2]
    else:
        seeded = receipts[:2]
        local = receipts[2:3]
    root = (tmp_path / f"union-count-{count}").absolute()
    for receipt in local:
        _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    monkeypatch.setattr(inventory, "_MAX_UNION_CLAIMS", 2)
    raw = _seed_raw(seeded)
    inspector_calls = 0
    if not accepted:
        def forbidden_inspector(*args: Any, **kwargs: Any) -> Any:
            nonlocal inspector_calls
            inspector_calls += 1
            raise AssertionError("union-count rejection must precede inspection")

        monkeypatch.setattr(
            inventory,
            "inspect_local_attempt_manifest_chain_v1_0",
            forbidden_inspector,
        )
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, raw)
        assert result.union_claim_count == count
        assert result.examined_claim_count == count
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(root, raw)
        assert inspector_calls == 0


@pytest.mark.parametrize(("name", "accepted"), [("é", True), ("€", True), ("éé", False)])
def test_uprime_seed_inventory_unexpected_utf8_name_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    accepted: bool,
) -> None:
    root = (tmp_path / "utf8-bound").absolute()
    _base(root).mkdir(parents=True)
    monkeypatch.setattr(inventory, "_MAX_UNEXPECTED_NAME_UTF8_BYTES", 3)
    scans = [_GuardedScandir([name]), _GuardedScandir([name])]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    if accepted:
        assert inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, EMPTY_SEED_RAW
        ).unexpected_entry_names == (name,)
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)


def test_uprime_seed_inventory_real_terminal_exact_match(tmp_path: Path) -> None:
    receipt = _receipt_mapping()
    root = _write_chain_for_receipt(
        tmp_path, receipt, terminal=True, root_name="terminal-match"
    )
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    assert result.coverage_status == "matched_terminal"
    assert result.set_equality is True
    assert result.all_seeded_local_present is True
    assert result.all_seeded_terminal is True
    assert result.all_seeded_receipts_match is True
    assert result.seeded_missing_ids == ()
    assert result.local_orphan_ids == ()
    assert result.receipt_mismatch_ids == ()
    assert result.terminal_ids == (receipt["license_id"],)
    claim = result.claim_audits[0]
    assert tuple(field.name for field in fields(claim)) == CLAIM_AUDIT_FIELDS
    assert claim.set_relation == "seed_and_local"
    assert claim.receipt_relation == "exact_match"
    assert claim.chain_observation == "valid_terminal"
    assert claim.event_count == 2
    assert claim.last_event_index == 2
    assert claim.terminal_event is True
    assert claim.authority_scope == "none"
    assert claim.licenses_execution is False
    assert claim.licenses_later_stage is False


def test_uprime_seed_inventory_real_attempt_finished_preserves_verdict_and_hash(
    tmp_path: Path,
) -> None:
    receipt = _receipt_mapping()
    values = [
        _attempt_event_mapping(receipt=receipt),
        _attempt_event_mapping(
            "attempt_finished",
            event_index=2,
            created_at_utc="2026-07-11T00:00:02.000000Z",
            receipt=receipt,
            failure_codes=["OTHER_HARNESS_ERROR"],
        ),
    ]
    root, _documents, raws = _attempt_write_chain(
        tmp_path, values, root_name="attempt-finished-row"
    )
    expected_last_sha = hashlib.sha256(raws[-1]).hexdigest().upper()
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    claim = result.claim_audits[0]
    assert result.coverage_status == "matched_terminal"
    assert result.all_seeded_local_present is True
    assert result.all_seeded_terminal is True
    assert result.all_seeded_receipts_match is True
    assert claim.receipt_relation == "exact_match"
    assert claim.chain_observation == "valid_terminal"
    assert claim.last_event_index == 2
    assert claim.last_event_sha256 == expected_last_sha
    assert claim.terminal_event is True
    assert claim.recorded_verdict == "HARNESS_ERROR"


def test_uprime_seed_inventory_real_nonterminal_and_empty_chain_mappings(
    tmp_path: Path,
) -> None:
    receipt = _receipt_mapping()
    root = _write_chain_for_receipt(
        tmp_path, receipt, terminal=False, root_name="nonterminal"
    )
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    assert result.coverage_status == "mismatched"
    assert result.all_seeded_local_present is True
    assert result.all_seeded_terminal is False
    assert result.all_seeded_receipts_match is True
    assert result.nonterminal_ids == (receipt["license_id"],)
    assert result.claim_audits[0].chain_observation == "valid_nonterminal"

    empty_root = (tmp_path / "empty-chain").absolute()
    _claim_dir(empty_root, receipt["license_id"]).mkdir(parents=True)
    empty = inventory.audit_synthetic_seed_local_inventory_v1_0(
        empty_root, _seed_raw([receipt])
    )
    claim = empty.claim_audits[0]
    assert empty.empty_chain_ids == (receipt["license_id"],)
    assert asdict(claim) == {
        "license_id": receipt["license_id"],
        "seed_membership": True,
        "local_membership": True,
        "set_relation": "seed_and_local",
        "receipt_relation": "not_observed",
        "seed_receipt_sha256": _receipt_sha256(receipt),
        "local_receipt_sha256": None,
        "chain_observation": "missing",
        "event_count": 0,
        "last_event_index": None,
        "last_event_sha256": None,
        "terminal_event": False,
        "recorded_verdict": None,
        "authority_scope": "none",
        "licenses_execution": False,
        "licenses_later_stage": False,
    }


def test_uprime_seed_inventory_seeded_missing_and_local_orphan_mappings(
    tmp_path: Path,
) -> None:
    receipt_a = _receipt_mapping("a" * 40)
    missing = inventory.audit_synthetic_seed_local_inventory_v1_0(
        (tmp_path / "seeded-missing").absolute(), _seed_raw([receipt_a])
    )
    claim = missing.claim_audits[0]
    assert asdict(claim) == {
        "license_id": receipt_a["license_id"],
        "seed_membership": True,
        "local_membership": False,
        "set_relation": "seeded_missing_local",
        "receipt_relation": "seed_only",
        "seed_receipt_sha256": _receipt_sha256(receipt_a),
        "local_receipt_sha256": None,
        "chain_observation": "not_present",
        "event_count": None,
        "last_event_index": None,
        "last_event_sha256": None,
        "terminal_event": None,
        "recorded_verdict": None,
        "authority_scope": "none",
        "licenses_execution": False,
        "licenses_later_stage": False,
    }
    assert missing.seeded_missing_ids == (receipt_a["license_id"],)

    receipt_b = _receipt_mapping("7" * 40)
    root = _write_chain_for_receipt(
        tmp_path, receipt_b, terminal=True, root_name="local-orphan"
    )
    orphan = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, EMPTY_SEED_RAW
    )
    claim = orphan.claim_audits[0]
    assert orphan.coverage_status == "mismatched"
    assert claim.set_relation == "local_orphan"
    assert claim.receipt_relation == "local_only"
    assert claim.chain_observation == "valid_terminal"
    assert orphan.local_orphan_ids == (receipt_b["license_id"],)


def test_uprime_seed_inventory_local_orphan_missing_has_exact_null_endpoints(
    tmp_path: Path,
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "local-orphan-missing").absolute()
    _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, EMPTY_SEED_RAW
    )
    assert result.local_orphan_ids == (receipt["license_id"],)
    assert result.empty_chain_ids == (receipt["license_id"],)
    assert asdict(result.claim_audits[0]) == {
        "license_id": receipt["license_id"],
        "seed_membership": False,
        "local_membership": True,
        "set_relation": "local_orphan",
        "receipt_relation": "not_observed",
        "seed_receipt_sha256": None,
        "local_receipt_sha256": None,
        "chain_observation": "missing",
        "event_count": 0,
        "last_event_index": None,
        "last_event_sha256": None,
        "terminal_event": False,
        "recorded_verdict": None,
        "authority_scope": "none",
        "licenses_execution": False,
        "licenses_later_stage": False,
    }


def test_uprime_seed_inventory_separately_valid_receipt_mismatch(tmp_path: Path) -> None:
    seed_receipt = _receipt_mapping()
    local_receipt = _receipt_mapping(license_commit="8" * 40)
    root = _write_chain_for_receipt(
        tmp_path, local_receipt, terminal=True, root_name="receipt-mismatch"
    )
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([seed_receipt])
    )
    claim = result.claim_audits[0]
    assert claim.receipt_relation == "mismatch"
    assert claim.seed_receipt_sha256 == _receipt_sha256(seed_receipt)
    assert claim.local_receipt_sha256 == _receipt_sha256(local_receipt)
    assert result.receipt_mismatch_ids == (seed_receipt["license_id"],)
    assert result.coverage_status == "mismatched"
    assert result.all_seeded_local_present is True
    assert result.all_seeded_terminal is True
    assert result.all_seeded_receipts_match is False


def test_uprime_seed_inventory_corrupt_chain_wraps_without_partial_result(
    tmp_path: Path,
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "corrupt-chain").absolute()
    path = _attempt_host_event_path(root, receipt["license_id"], 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"{}\n")
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error) as exc:
        inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, _seed_raw([receipt])
        )
    assert type(exc.value) is inventory.SyntheticSeedInventoryV10Error


def test_uprime_seed_inventory_injected_index_exhausted_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / "index-exhausted").absolute()
    _claim_dir(root, receipt["license_id"]).mkdir(parents=True)

    def inspect(_root: Any, _license: str) -> manifest.AttemptManifestChainInspectionV10:
        return _fake_inspection(receipt, chain_state="valid_nonterminal_index_exhausted")

    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([receipt])
    )
    assert result.nonterminal_ids == (receipt["license_id"],)
    assert result.claim_audits[0].last_event_index == 9_999
    assert result.claim_audits[0].chain_observation == (
        "valid_nonterminal_index_exhausted"
    )


def test_uprime_seed_inventory_phase2b1_error_aborts_before_later_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = sorted(
        [_receipt_mapping("1" * 40), _receipt_mapping("2" * 40)],
        key=lambda value: value["license_id"],
    )
    root = (tmp_path / "phase1-error").absolute()
    for receipt in receipts:
        _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    calls: list[str] = []

    def inspect(_root: Any, license_id: str) -> manifest.AttemptManifestChainInspectionV10:
        calls.append(license_id)
        raise manifest.AttemptManifestV10Error("sensitive detail")

    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error) as exc:
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, _seed_raw(receipts))
    assert calls == [receipts[0]["license_id"]]
    assert "sensitive detail" not in str(exc.value)


def test_uprime_seed_inventory_empty_seed_with_unexpected_is_mismatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "empty-with-evidence").absolute()
    _base(root).mkdir(parents=True)
    scans = [_GuardedScandir(["unexpected"]), _GuardedScandir(["unexpected"])]
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert result.coverage_status == "mismatched"
    assert result.set_equality is True
    assert result.all_seeded_local_present is False
    assert result.all_seeded_terminal is False
    assert result.all_seeded_receipts_match is False


def test_uprime_seed_inventory_set_combinations_are_complete_and_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = {
        value["license_id"]: value
        for value in (_receipt_mapping("1" * 40), _receipt_mapping("2" * 40))
    }
    ordered = sorted(receipts)
    seed_receipt = receipts[ordered[0]]
    local_receipt = receipts[ordered[1]]
    root = (tmp_path / "disjoint").absolute()
    _claim_dir(root, local_receipt["license_id"]).mkdir(parents=True)

    def inspect(_root: Any, license_id: str) -> manifest.AttemptManifestChainInspectionV10:
        return _fake_inspection(receipts[license_id])

    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([seed_receipt])
    )
    assert result.coverage_status == "mismatched"
    assert result.set_equality is False
    assert result.union_claim_count == result.examined_claim_count == 2
    assert tuple(item.license_id for item in result.claim_audits) == tuple(ordered)
    relations = {item.license_id: item.set_relation for item in result.claim_audits}
    assert relations[seed_receipt["license_id"]] == "seeded_missing_local"
    assert relations[local_receipt["license_id"]] == "local_orphan"


@pytest.mark.parametrize("direction", ("seed_proper_subset", "local_proper_subset"))
def test_uprime_seed_inventory_nonempty_overlap_proper_subset_directions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    direction: str,
) -> None:
    by_id = {
        receipt["license_id"]: receipt
        for receipt in (_receipt_mapping("1" * 40), _receipt_mapping("2" * 40))
    }
    ordered = tuple(sorted(by_id))
    common_id, extra_id = ordered
    if direction == "seed_proper_subset":
        seed_ids = (common_id,)
        local_ids = (common_id, extra_id)
        expected_relations = {
            common_id: "seed_and_local",
            extra_id: "local_orphan",
        }
    else:
        seed_ids = (common_id, extra_id)
        local_ids = (common_id,)
        expected_relations = {
            common_id: "seed_and_local",
            extra_id: "seeded_missing_local",
        }
    assert set(seed_ids).intersection(local_ids) == {common_id}
    assert set(seed_ids) != set(local_ids)
    root = (tmp_path / direction).absolute()
    for license_id in local_ids:
        _claim_dir(root, license_id).mkdir(parents=True)

    def inspect(
        retained_root: Any, license_id: str
    ) -> manifest.AttemptManifestChainInspectionV10:
        return _fake_inspection(by_id[license_id])

    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, _seed_raw([by_id[item] for item in seed_ids])
    )
    assert result.coverage_status == "mismatched"
    assert result.set_equality is False
    assert result.seed_count == len(seed_ids)
    assert result.local_directory_count == len(local_ids)
    assert result.union_claim_count == result.examined_claim_count == 2
    assert tuple(item.license_id for item in result.claim_audits) == ordered
    assert {
        item.license_id: item.set_relation for item in result.claim_audits
    } == expected_relations
    if direction == "seed_proper_subset":
        assert result.local_orphan_ids == (extra_id,)
        assert result.seeded_missing_ids == ()
        assert result.all_seeded_local_present is True
        assert result.all_seeded_terminal is True
        assert result.all_seeded_receipts_match is True
    else:
        assert result.seeded_missing_ids == (extra_id,)
        assert result.local_orphan_ids == ()
        assert result.all_seeded_local_present is False
        assert result.all_seeded_terminal is False
        assert result.all_seeded_receipts_match is False


def test_uprime_seed_inventory_coordinated_omission_is_indistinguishable(
    tmp_path: Path,
) -> None:
    receipt_a = _receipt_mapping("a" * 40)
    external_only_b = _receipt_mapping("7" * 40)
    root = _write_chain_for_receipt(
        tmp_path, receipt_a, terminal=True, root_name="coordinated-omission"
    )
    raw = _seed_raw([receipt_a])
    universe_without_b = inventory.audit_synthetic_seed_local_inventory_v1_0(root, raw)
    assert external_only_b["license_id"] not in {
        item.license_id for item in universe_without_b.claim_audits
    }
    universe_with_external_b = inventory.audit_synthetic_seed_local_inventory_v1_0(
        root, raw
    )
    assert universe_with_external_b == universe_without_b
    assert universe_with_external_b.coverage_status == "matched_terminal"
    assert universe_with_external_b.coordinated_omission_detectability == "none"
    assert universe_with_external_b.real_claim_completeness == "not_authenticated"


def test_uprime_seed_inventory_resource_defaults_and_formulas_are_exact() -> None:
    assert inventory._MAX_SEED_BYTES == 16_777_216
    assert inventory._MAX_SEEDED_CLAIMS == 16
    assert inventory._MAX_LOCAL_CLAIM_DIRS == 16
    assert inventory._MAX_BASE_ENTRIES == 32
    assert inventory._MAX_UNEXPECTED_NAMES == 16
    assert inventory._MAX_UNEXPECTED_NAME_UTF8_BYTES == 4_096
    assert inventory._MAX_UNION_CLAIMS == 32
    assert inventory._MAX_TOTAL_ACCEPTED_EVENT_BYTES == 67_108_864
    assert inventory._MAX_TOTAL_EVENT_READ_WORK_BYTES == 268_435_457
    assert inventory._MAX_EVENT_FILE_ADMISSIONS == 159_984
    assert 2 * (67_108_864 + 67_108_864) + 1 == 268_435_457
    assert 16 * 9_999 == 159_984


@pytest.mark.parametrize(("payload", "accepted"), [(31, True), (32, True), (33, False)])
def test_uprime_seed_inventory_injected_total_event_byte_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: int,
    accepted: bool,
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / f"payload-{payload}").absolute()
    _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    monkeypatch.setattr(inventory, "_MAX_TOTAL_ACCEPTED_EVENT_BYTES", 32)
    monkeypatch.setattr(
        inventory,
        "inspect_local_attempt_manifest_chain_v1_0",
        lambda _root, _license: _fake_inspection(
            receipt, payload_lengths=(payload,)
        ),
    )
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, _seed_raw([receipt])
        )
        assert result.total_observed_event_bytes == payload
        assert result.read_work_upper_bound_bytes == 268_435_457
        assert result.event_file_admission_upper_bound == 159_984
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(
                root, _seed_raw([receipt])
            )


@pytest.mark.parametrize(
    ("payload_lengths", "accepted"),
    (
        ((15, 16), True),
        ((16, 16), True),
        ((16, 17), False),
    ),
)
def test_uprime_seed_inventory_multi_event_lengths_are_summed_at_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload_lengths: tuple[int, ...],
    accepted: bool,
) -> None:
    receipt = _receipt_mapping()
    total = sum(payload_lengths)
    root = (tmp_path / f"multi-event-sum-{total}").absolute()
    _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    monkeypatch.setattr(inventory, "_MAX_TOTAL_ACCEPTED_EVENT_BYTES", 32)
    monkeypatch.setattr(
        inventory,
        "inspect_local_attempt_manifest_chain_v1_0",
        lambda retained_root, license_id: _fake_inspection(
            receipt, payload_lengths=payload_lengths
        ),
    )
    if accepted:
        result = inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, _seed_raw([receipt])
        )
        assert result.total_observed_event_bytes == total
    else:
        with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
            inventory.audit_synthetic_seed_local_inventory_v1_0(
                root, _seed_raw([receipt])
            )


def test_uprime_seed_inventory_prefix_overshoot_stops_before_later_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = sorted(
        [_receipt_mapping("1" * 40), _receipt_mapping("2" * 40), _receipt_mapping("3" * 40)],
        key=lambda value: value["license_id"],
    )
    by_id = {item["license_id"]: item for item in receipts}
    root = (tmp_path / "overshoot-prefix").absolute()
    for receipt in receipts:
        _claim_dir(root, receipt["license_id"]).mkdir(parents=True)
    calls: list[str] = []

    def inspect(_root: Any, license_id: str) -> manifest.AttemptManifestChainInspectionV10:
        calls.append(license_id)
        return _fake_inspection(by_id[license_id], payload_lengths=(20,))

    monkeypatch.setattr(inventory, "_MAX_TOTAL_ACCEPTED_EVENT_BYTES", 32)
    monkeypatch.setattr(inventory, "inspect_local_attempt_manifest_chain_v1_0", inspect)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, _seed_raw(receipts))
    assert calls == [receipts[0]["license_id"], receipts[1]["license_id"]]


@pytest.mark.parametrize(
    "constant",
    (
        "_MAX_SEED_BYTES",
        "_MAX_SEEDED_CLAIMS",
        "_MAX_LOCAL_CLAIM_DIRS",
        "_MAX_BASE_ENTRIES",
        "_MAX_UNEXPECTED_NAMES",
        "_MAX_UNEXPECTED_NAME_UTF8_BYTES",
        "_MAX_UNION_CLAIMS",
        "_MAX_TOTAL_ACCEPTED_EVENT_BYTES",
        "_MAX_TOTAL_EVENT_READ_WORK_BYTES",
        "_MAX_EVENT_FILE_ADMISSIONS",
    ),
)
@pytest.mark.parametrize("invalid", (True, -1))
def test_uprime_seed_inventory_invalid_resource_constants_reject_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    invalid: Any,
) -> None:
    monkeypatch.setattr(inventory, constant, invalid)
    calls = 0

    def forbidden_fspath(_value: Any) -> str:
        nonlocal calls
        calls += 1
        raise AssertionError("resource validation must precede root I/O")

    monkeypatch.setattr(inventory, "_os_fspath", forbidden_fspath)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(
            (tmp_path / "invalid-bound").absolute(), EMPTY_SEED_RAW
        )
    assert calls == 0


@pytest.mark.parametrize(
    ("operation", "failure_call"),
    (
        ("base_stat", 1),
        ("base_stat", 2),
        ("scandir", 1),
        ("scandir", 2),
        ("candidate_stat", 1),
        ("candidate_stat", 2),
    ),
)
def test_uprime_seed_inventory_base_io_failures_are_public(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    failure_call: int,
) -> None:
    receipt = _receipt_mapping()
    root = (tmp_path / f"io-{operation}-{failure_call}").absolute()
    target = _claim_dir(root, receipt["license_id"])
    target.mkdir(parents=True)
    base = _base(root)
    calls = 0
    if operation == "scandir":
        real_scandir = inventory._os_scandir

        def failing_scandir(path: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == failure_call:
                raise OSError("injected scan failure")
            return real_scandir(path)

        monkeypatch.setattr(inventory, "_os_scandir", failing_scandir)
    else:
        real_stat = inventory._os_stat

        def failing_stat(
            path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
        ) -> Any:
            nonlocal calls
            key = os.path.normcase(os.path.abspath(os.fspath(path)))
            selected = (
                operation == "base_stat"
                and key == os.path.normcase(os.path.abspath(base))
            ) or (
                operation == "candidate_stat"
                and key == os.path.normcase(os.path.abspath(target))
            )
            if selected:
                calls += 1
                if calls == failure_call:
                    raise OSError("injected stat failure")
            return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

        monkeypatch.setattr(inventory, "_os_stat", failing_stat)
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(
            root, _seed_raw([receipt])
        )
    assert calls == failure_call


@pytest.mark.parametrize(("failure", "scan_index"), (("iterate", 0), ("close", 0), ("iterate", 1), ("close", 1)))
def test_uprime_seed_inventory_scandir_iteration_and_close_failures_are_public(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    scan_index: int,
) -> None:
    root = (tmp_path / f"scan-{failure}-{scan_index}").absolute()
    _base(root).mkdir(parents=True)
    scans = [_GuardedScandir([]), _GuardedScandir([])]
    if failure == "iterate":
        scans[scan_index] = _GuardedScandir(["x"], fail_at=1)
    else:
        scans[scan_index] = _GuardedScandir([], close_error=True)
    monkeypatch.setattr(inventory, "_os_scandir", _ScandirSequence(scans))
    with pytest.raises(inventory.SyntheticSeedInventoryV10Error):
        inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    assert scans[scan_index].closed == 1


def test_uprime_seed_inventory_public_surface_annotations_and_all_are_exact() -> None:
    assert inventory.SyntheticSeedInventoryV10Error.__bases__ == (ValueError,)
    assert tuple(field.name for field in fields(inventory.SyntheticClaimSeedV10)) == SEED_FIELDS
    assert tuple(field.name for field in fields(inventory.SyntheticLocalClaimAuditV10)) == CLAIM_AUDIT_FIELDS
    assert tuple(field.name for field in fields(inventory.SyntheticSeedLocalInventoryAuditV10)) == AUDIT_FIELDS
    assert inventory.SyntheticClaimSeedV10.__annotations__ == dict(
        zip(
            SEED_FIELDS,
            (
                str,
                str,
                str,
                str,
                str,
                int,
                tuple[manifest.PublicClaimReceiptV10, ...],
                int,
                str,
                str,
                str,
                str,
                str,
                bool,
                bool,
                bool,
            ),
            strict=True,
        )
    )
    assert inventory.SyntheticLocalClaimAuditV10.__annotations__ == dict(
        zip(
            CLAIM_AUDIT_FIELDS,
            (
                str,
                bool,
                bool,
                str,
                str,
                str | None,
                str | None,
                str,
                int | None,
                int | None,
                str | None,
                bool | None,
                str | None,
                str,
                bool,
                bool,
            ),
            strict=True,
        )
    )
    expected_aggregate_annotations: dict[str, Any] = {
        name: str
        for name in (
            "auditor_schema_version",
            "auditor_scope",
            "origin_status",
            "base_directory_status",
            "seed_file_sha256",
            "seed_identity_sha256",
            "coverage_status",
            "seed_origin",
            "seed_binding",
            "seed_temporal_commitment",
            "remote_inventory_observation",
            "real_claim_completeness",
            "omitted_claim_detectability",
            "coordinated_omission_detectability",
            "root_scope",
            "snapshot_scope",
            "resource_status",
            "authority_scope",
        )
    }
    expected_aggregate_annotations.update(
        {
            name: int
            for name in (
                "seed_count",
                "local_directory_count",
                "union_claim_count",
                "examined_claim_count",
                "total_observed_event_bytes",
                "read_work_upper_bound_bytes",
                "event_file_admission_upper_bound",
                "unexpected_entry_count",
            )
        }
    )
    expected_aggregate_annotations["claim_audits"] = tuple[
        inventory.SyntheticLocalClaimAuditV10, ...
    ]
    expected_aggregate_annotations.update(
        {
            name: tuple[str, ...]
            for name in (
                "unexpected_entry_names",
                "seeded_missing_ids",
                "local_orphan_ids",
                "receipt_mismatch_ids",
                "terminal_ids",
                "nonterminal_ids",
                "empty_chain_ids",
            )
        }
    )
    expected_aggregate_annotations.update(
        {
            name: bool
            for name in (
                "set_equality",
                "all_seeded_local_present",
                "all_seeded_terminal",
                "all_seeded_receipts_match",
                "canonical_run_authority",
                "licenses_execution",
                "licenses_publication",
                "licenses_recovery",
                "licenses_later_stage",
            )
        }
    )
    assert inventory.SyntheticSeedLocalInventoryAuditV10.__annotations__ == {
        name: expected_aggregate_annotations[name] for name in AUDIT_FIELDS
    }
    for record_type in (
        inventory.SyntheticClaimSeedV10,
        inventory.SyntheticLocalClaimAuditV10,
        inventory.SyntheticSeedLocalInventoryAuditV10,
    ):
        assert record_type.__dataclass_params__.frozen is True
        assert "__slots__" in record_type.__dict__
        assert "__dict__" not in record_type.__dict__
    signatures = {
        "parse_synthetic_claim_seed_v1_0": (
            (("raw", bytes),),
            inventory.SyntheticClaimSeedV10,
        ),
        "audit_synthetic_seed_local_inventory_v1_0": (
            (
                ("root", str | os.PathLike[str]),
                ("seed_raw", bytes),
            ),
            inventory.SyntheticSeedLocalInventoryAuditV10,
        ),
    }
    for name, (parameters, return_type) in signatures.items():
        signature = inspect.signature(getattr(inventory, name))
        assert tuple(signature.parameters) == tuple(item[0] for item in parameters)
        assert all(
            item.kind is inspect.Parameter.POSITIONAL_ONLY
            for item in signature.parameters.values()
        )
        assert all(item.default is inspect.Parameter.empty for item in signature.parameters.values())
        assert tuple(
            (item.name, item.annotation) for item in signature.parameters.values()
        ) == parameters
        assert signature.return_annotation == return_type
    assert type(inventory.__all__) is list
    assert inventory.__all__ == [
        "SyntheticSeedInventoryV10Error",
        "SyntheticClaimSeedV10",
        "SyntheticLocalClaimAuditV10",
        "SyntheticSeedLocalInventoryAuditV10",
        "parse_synthetic_claim_seed_v1_0",
        "audit_synthetic_seed_local_inventory_v1_0",
    ]


def test_uprime_seed_inventory_source_ast_imports_and_read_only_calls_are_exact() -> None:
    source_path = Path(inventory.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    modules, imported = _source_imports(tree)
    assert modules == {
        "dataclasses",
        "hashlib",
        "os",
        "re",
        "stat",
        "lean_rgc.evals.uprime_rpc_attempt_manifest",
        "lean_rgc.evals.uprime_rpc_ledger",
    }
    assert imported["lean_rgc.evals.uprime_rpc_attempt_manifest"] == {
        "AttemptManifestV10Error",
        "PublicClaimReceiptV10",
        "AttemptManifestChainInspectionV10",
        "inspect_local_attempt_manifest_chain_v1_0",
    }
    assert imported["lean_rgc.evals.uprime_rpc_ledger"] == {
        "canonical_json_bytes",
        "parse_canonical_json_bytes",
    }
    assert imported.get("dataclasses") == {"dataclass"}
    assert "os" not in imported
    assert all(
        alias.asname is None
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(
        isinstance(node, ast.ImportFrom) and node.module in {"os", "builtins"}
        for node in ast.walk(tree)
    )

    expected_os_aliases = {
        "_os_fspath": "os.fspath",
        "_os_path_isabs": "os.path.isabs",
        "_os_path_join": "os.path.join",
        "_os_stat": "os.stat",
        "_os_scandir": "os.scandir",
    }
    observed_os_aliases: list[tuple[str, str | None]] = []
    assignment_values: list[str | None] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assignment_values.append(_ast_qualified_name(node.value))
            for target in node.targets:
                observed_os_aliases.extend(
                    (name, _ast_qualified_name(node.value))
                    for name in _ast_bound_names(target)
                    if name.startswith("_os_")
                )
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                assignment_values.append(_ast_qualified_name(node.value))
            observed_os_aliases.extend(
                (name, _ast_qualified_name(node.value))
                for name in _ast_bound_names(node.target)
                if name.startswith("_os_")
            )
        elif isinstance(node, ast.NamedExpr):
            assignment_values.append(_ast_qualified_name(node.value))
            observed_os_aliases.extend(
                (name, _ast_qualified_name(node.value))
                for name in _ast_bound_names(node.target)
                if name.startswith("_os_")
            )
    assert len(observed_os_aliases) == len(expected_os_aliases)
    assert dict(observed_os_aliases) == expected_os_aliases

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    qualified_calls = tuple(_ast_qualified_name(node.func) for node in calls)
    observed_os_alias_calls = {
        name for name in qualified_calls if name is not None and name.startswith("_os_")
    }
    assert observed_os_alias_calls == set(expected_os_aliases)
    assert not any(
        name is not None and name.startswith("os.") for name in qualified_calls
    )

    forbidden_builtins = {"open", "__import__", "eval", "exec", "compile"}
    assert not any(
        name in forbidden_builtins
        or (
            name is not None
            and name.startswith("builtins.")
            and name.rsplit(".", 1)[-1] in forbidden_builtins
        )
        for name in qualified_calls
    )
    write_capability_names = {
        "open",
        "fdopen",
        "write",
        "writelines",
        "write_text",
        "write_bytes",
        "touch",
        "replace",
        "rename",
        "unlink",
        "remove",
        "mkdir",
        "makedirs",
        "truncate",
        "chmod",
        "chown",
        "lchmod",
        "link",
        "symlink",
        "link_to",
        "symlink_to",
        "hardlink_to",
        "mknod",
        "mkfifo",
        "fsync",
        "system",
        "popen",
        "startfile",
    }
    assert not any(
        name is not None and name.rsplit(".", 1)[-1] in write_capability_names
        for name in qualified_calls
    )
    assert not any(
        value is not None
        and value.rsplit(".", 1)[-1]
        in write_capability_names.union(forbidden_builtins)
        for value in assignment_values
    )
    assert not any(
        _ast_qualified_name(node.func) == "getattr"
        and len(node.args) >= 2
        and _ast_qualified_name(node.args[0]) in {"os", "builtins"}
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
        and node.args[1].value
        in write_capability_names.union(forbidden_builtins)
        for node in calls
    )
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom))
        for node in ast.walk(tree)
    )


def test_uprime_seed_inventory_production_capabilities_and_exposure_are_unreached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lean_rgc.evals import uprime_rpc_bundle_reservation as reservation
    from lean_rgc.evals import uprime_rpc_contract_oracle as contract_oracle
    from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics
    from lean_rgc.evals import uprime_rpc_litmus as litmus

    runs_root = Path("runs")
    before_runs = _tree_metadata_snapshot(runs_root)
    before_markers = _exposure_marker_paths()
    assert before_markers == ()
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("production")
        raise AssertionError("production or exposure capability was reached")

    monkeypatch.setattr(litmus, "run_diagnostic", forbidden)
    monkeypatch.setattr(litmus, "_reserve_output", forbidden)
    monkeypatch.setattr(litmus, "_publish_reserved_json", forbidden)
    monkeypatch.setattr(
        reservation,
        "inspect_standalone_bundle_reservation_v1_1",
        forbidden,
    )
    monkeypatch.setattr(
        contract_oracle,
        "attest_standalone_exact_49_contracts",
        forbidden,
    )
    monkeypatch.setattr(
        semantics,
        "attest_standalone_nominal_49_semantics",
        forbidden,
    )
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(
        (tmp_path / "production-unreached").absolute(), EMPTY_SEED_RAW
    )
    assert result.coverage_status == "empty_seed"
    assert calls == []
    assert _tree_metadata_snapshot(runs_root) == before_runs
    assert _exposure_marker_paths() == before_markers == ()


def test_uprime_seed_inventory_read_only_api_creates_no_files(tmp_path: Path) -> None:
    root = (tmp_path / "never-created").absolute()
    before = tuple(tmp_path.rglob("*"))
    result = inventory.audit_synthetic_seed_local_inventory_v1_0(root, EMPTY_SEED_RAW)
    after = tuple(tmp_path.rglob("*"))
    assert result.base_directory_status == "absent"
    assert after == before


def test_uprime_seed_inventory_default_deny_registry_is_still_head_bound() -> None:
    path = Path("docs/experiments/uprime_odlrq_u1_rerun_license_registry.json")
    expected = (
        b'{"default_allow":false,"licenses":{},"schema_version":'
        b'"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n'
    )
    raw = path.read_bytes()
    assert raw == expected
    assert len(raw) == 96
    assert hashlib.sha256(raw).hexdigest().upper() == (
        "ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B"
    )
    expected_blob = "13ffca6de484effc66f0e628d2e46823277271c6"
    work = subprocess.run(
        ["git", "hash-object", os.fspath(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path.as_posix()}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    assert work == head == expected_blob


def test_uprime_seed_inventory_support_all_exports_each_test_once() -> None:
    expected = sorted(
        name
        for name, value in globals().items()
        if name.startswith("test_uprime_seed_inventory_")
        and inspect.isfunction(value)
        and value.__module__ == __name__
    )
    assert __all__ == expected
    assert len(__all__) == len(set(__all__))


__all__ = sorted(
    name
    for name, value in globals().items()
    if name.startswith("test_uprime_seed_inventory_")
    and inspect.isfunction(value)
    and value.__module__ == __name__
)
