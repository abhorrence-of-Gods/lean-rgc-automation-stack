"""Read-only Phase-2b2a seed/local attempt-manifest inventory audit.

This module compares caller-supplied synthetic receipt bytes with one bounded
local namespace.  It does not authenticate either source, observe artifacts,
write files, contact a remote, or grant execution or publication authority.
"""

from dataclasses import dataclass
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_attempt_manifest import (
    AttemptManifestV10Error,
    PublicClaimReceiptV10,
    AttemptManifestChainInspectionV10,
    inspect_local_attempt_manifest_chain_v1_0,
)
from lean_rgc.evals.uprime_rpc_ledger import (
    canonical_json_bytes,
    parse_canonical_json_bytes,
)


_SEED_SCHEMA = "lean-rgc-uprime-u1-synthetic-claim-seed-v1.0"
_SEED_SCOPE = "caller_supplied_synthetic_claims_only"
_AUDITOR_SCHEMA = "lean-rgc-uprime-u1-seed-local-inventory-auditor-v0.1"
_AUDITOR_SCOPE = "caller_seed_vs_entire_local_attempt_namespace"
_ORIGIN_STATUS = "unknown_may_be_synthetic"
_SEED_DOMAIN = b"lean-rgc-uprime-u1-synthetic-claim-seed-v1\0"
_BASE_COMPONENTS = (
    "docs",
    "experiments",
    "artifacts",
    "uprime_u1_rpc_attempts",
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
_SEED_FIELD_NAMES = (
    "schema_version",
    "seed_scope",
    "claim_receipts",
)

_MAX_SEED_BYTES = 16_777_216
_MAX_SEEDED_CLAIMS = 16
_MAX_LOCAL_CLAIM_DIRS = 16
_MAX_BASE_ENTRIES = 32
_MAX_UNEXPECTED_NAMES = 16
_MAX_UNEXPECTED_NAME_UTF8_BYTES = 4_096
_MAX_UNION_CLAIMS = 32
_MAX_TOTAL_ACCEPTED_EVENT_BYTES = 67_108_864
_MAX_TOTAL_EVENT_READ_WORK_BYTES = 268_435_457
_MAX_EVENT_FILE_ADMISSIONS = 159_984

_HEX64_LOWER_RE = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)

_os_fspath = os.fspath
_os_path_isabs = os.path.isabs
_os_path_join = os.path.join
_os_stat = os.stat
_os_scandir = os.scandir


class SyntheticSeedInventoryV10Error(ValueError):
    """The bounded synthetic seed/local observation was not well formed."""


@dataclass(frozen=True, slots=True)
class SyntheticClaimSeedV10:
    schema_version: str
    seed_scope: str
    origin_status: str
    seed_file_sha256: str
    seed_identity_sha256: str
    seed_bytes: int
    claim_receipts: tuple[PublicClaimReceiptV10, ...]
    claim_count: int
    inventory_completeness: str
    omitted_claim_detectability: str
    remote_inventory_observation: str
    seed_temporal_commitment: str
    authority_scope: str
    licenses_execution: bool
    licenses_publication: bool
    licenses_later_stage: bool


@dataclass(frozen=True, slots=True)
class SyntheticLocalClaimAuditV10:
    license_id: str
    seed_membership: bool
    local_membership: bool
    set_relation: str
    receipt_relation: str
    seed_receipt_sha256: str | None
    local_receipt_sha256: str | None
    chain_observation: str
    event_count: int | None
    last_event_index: int | None
    last_event_sha256: str | None
    terminal_event: bool | None
    recorded_verdict: str | None
    authority_scope: str
    licenses_execution: bool
    licenses_later_stage: bool


@dataclass(frozen=True, slots=True)
class SyntheticSeedLocalInventoryAuditV10:
    auditor_schema_version: str
    auditor_scope: str
    origin_status: str
    base_directory_status: str
    seed_file_sha256: str
    seed_identity_sha256: str
    seed_count: int
    local_directory_count: int
    union_claim_count: int
    examined_claim_count: int
    total_observed_event_bytes: int
    read_work_upper_bound_bytes: int
    event_file_admission_upper_bound: int
    claim_audits: tuple[SyntheticLocalClaimAuditV10, ...]
    unexpected_entry_names: tuple[str, ...]
    unexpected_entry_count: int
    seeded_missing_ids: tuple[str, ...]
    local_orphan_ids: tuple[str, ...]
    receipt_mismatch_ids: tuple[str, ...]
    terminal_ids: tuple[str, ...]
    nonterminal_ids: tuple[str, ...]
    empty_chain_ids: tuple[str, ...]
    coverage_status: str
    set_equality: bool
    all_seeded_local_present: bool
    all_seeded_terminal: bool
    all_seeded_receipts_match: bool
    seed_origin: str
    seed_binding: str
    seed_temporal_commitment: str
    remote_inventory_observation: str
    real_claim_completeness: str
    omitted_claim_detectability: str
    coordinated_omission_detectability: str
    root_scope: str
    snapshot_scope: str
    resource_status: str
    authority_scope: str
    canonical_run_authority: bool
    licenses_execution: bool
    licenses_publication: bool
    licenses_recovery: bool
    licenses_later_stage: bool


def _fail(message: str) -> None:
    raise SyntheticSeedInventoryV10Error(message) from None


def _require_exact_int(value: object, name: str) -> int:
    if type(value) is not int:
        _fail(f"{name} is not an exact integer")
    return value


def _resource_bounds() -> tuple[int, int, int, int, int, int, int, int, int, int]:
    values = (
        _MAX_SEED_BYTES,
        _MAX_SEEDED_CLAIMS,
        _MAX_LOCAL_CLAIM_DIRS,
        _MAX_BASE_ENTRIES,
        _MAX_UNEXPECTED_NAMES,
        _MAX_UNEXPECTED_NAME_UTF8_BYTES,
        _MAX_UNION_CLAIMS,
        _MAX_TOTAL_ACCEPTED_EVENT_BYTES,
        _MAX_TOTAL_EVENT_READ_WORK_BYTES,
        _MAX_EVENT_FILE_ADMISSIONS,
    )
    names = (
        "seed byte",
        "seeded claim",
        "local claim directory",
        "base entry",
        "unexpected name",
        "unexpected name UTF-8 byte",
        "union claim",
        "accepted event byte",
        "event read-work byte",
        "event file admission",
    )
    for value, name in zip(values, names):
        if type(value) is not int or value < 0:
            _fail(f"{name} bound is invalid")
    return values


def _canonical_bytes(value: object, context: str) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        _fail(f"{context} is outside strict canonical JSON")


def _parse_canonical_bytes(raw: bytes) -> object:
    try:
        return parse_canonical_json_bytes(raw)
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        _fail("seed payload is not strict canonical JSON")


def _uppercase_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _uint64_be(value: object) -> bytes:
    number = _require_exact_int(value, "uint64 value")
    if not 0 <= number <= (1 << 64) - 1:
        _fail("uint64 value is outside its domain")
    return number.to_bytes(8, "big")


def _require_exact_mapping(
    value: object, fields: tuple[str, ...], context: str
) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"{context} is not an exact object")
    if len(value) != len(fields) or set(value) != set(fields):
        _fail(f"{context} fields are not exact")
    return value


def _receipt_mapping(receipt: PublicClaimReceiptV10) -> dict[str, object]:
    if type(receipt) is not PublicClaimReceiptV10:
        _fail("seed receipt has the wrong record type")
    return {name: getattr(receipt, name) for name in _RECEIPT_FIELD_NAMES}


def _receipt_from_mapping(value: object) -> PublicClaimReceiptV10:
    mapping = _require_exact_mapping(value, _RECEIPT_FIELD_NAMES, "seed receipt")
    try:
        return PublicClaimReceiptV10(
            **{name: mapping[name] for name in _RECEIPT_FIELD_NAMES}
        )
    except (AttemptManifestV10Error, TypeError):
        _fail("seed receipt failed public validation")


def _receipt_sha256(receipt: PublicClaimReceiptV10) -> str:
    return _uppercase_sha256(_canonical_bytes(_receipt_mapping(receipt), "seed receipt"))


def parse_synthetic_claim_seed_v1_0(raw: bytes, /) -> SyntheticClaimSeedV10:
    """Parse exact caller-supplied synthetic receipt seed bytes."""

    if type(raw) is not bytes:
        _fail("seed raw input must be exact bytes")
    if type(_MAX_SEED_BYTES) is not int or _MAX_SEED_BYTES < 0:
        _fail("seed byte bound is invalid")
    if type(_MAX_SEEDED_CLAIMS) is not int or _MAX_SEEDED_CLAIMS < 0:
        _fail("seeded claim bound is invalid")
    if len(raw) > _MAX_SEED_BYTES:
        _fail("seed exceeds the inclusive byte bound")
    if raw[-1:] != b"\n" or b"\n" in raw[:-1]:
        _fail("seed bytes must contain exactly one final LF")

    parsed = _parse_canonical_bytes(raw[:-1])
    mapping = _require_exact_mapping(parsed, _SEED_FIELD_NAMES, "seed")
    if type(mapping["schema_version"]) is not str or mapping["schema_version"] != _SEED_SCHEMA:
        _fail("seed schema_version is invalid")
    if type(mapping["seed_scope"]) is not str or mapping["seed_scope"] != _SEED_SCOPE:
        _fail("seed_scope is invalid")
    values = mapping["claim_receipts"]
    if type(values) is not list:
        _fail("claim_receipts is not an exact array")
    if len(values) > _MAX_SEEDED_CLAIMS:
        _fail("claim_receipts exceeds the claim-count bound")

    receipts: list[PublicClaimReceiptV10] = []
    remote_refs: set[str] = set()
    prior_license_id: str | None = None
    for value in values:
        receipt = _receipt_from_mapping(value)
        if prior_license_id is not None and receipt.license_id <= prior_license_id:
            _fail("seed receipts are not strictly ASCII sorted and unique")
        if receipt.remote_claim_ref in remote_refs:
            _fail("seed receipts contain a duplicate remote claim ref")
        prior_license_id = receipt.license_id
        remote_refs.add(receipt.remote_claim_ref)
        receipts.append(receipt)

    rebuilt = _canonical_bytes(
        {
            "schema_version": _SEED_SCHEMA,
            "seed_scope": _SEED_SCOPE,
            "claim_receipts": [_receipt_mapping(receipt) for receipt in receipts],
        },
        "seed",
    ) + b"\n"
    if rebuilt != raw:
        _fail("seed bytes do not round-trip byte-identically")

    receipt_tuple = tuple(receipts)
    return SyntheticClaimSeedV10(
        schema_version=_SEED_SCHEMA,
        seed_scope=_SEED_SCOPE,
        origin_status=_ORIGIN_STATUS,
        seed_file_sha256=_uppercase_sha256(raw),
        seed_identity_sha256=_uppercase_sha256(
            _SEED_DOMAIN + _uint64_be(len(raw)) + raw
        ),
        seed_bytes=len(raw),
        claim_receipts=receipt_tuple,
        claim_count=len(receipt_tuple),
        inventory_completeness="not_authenticated_may_omit_claims",
        omitted_claim_detectability="none_outside_supplied_seed",
        remote_inventory_observation="not_performed",
        seed_temporal_commitment="not_authenticated",
        authority_scope="none",
        licenses_execution=False,
        licenses_publication=False,
        licenses_later_stage=False,
    )


def _root_text_once(root: object) -> str:
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


def _join_path(*parts: str) -> str:
    try:
        value = _os_path_join(*parts)
    except (OSError, TypeError, ValueError):
        _fail("lexical path construction failed")
    if type(value) is not str:
        _fail("lexical path construction did not return exact text")
    return value


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


def _directory_snapshot(
    value: os.stat_result,
) -> tuple[int, int, int, bool, int, int]:
    return (
        _stat_integer(value, "st_dev"),
        _stat_integer(value, "st_ino"),
        _stat_integer(value, "st_mode"),
        _reparse_bit(value),
        _stat_integer(value, "st_ctime_ns"),
        _stat_integer(value, "st_mtime_ns"),
    )


def _entry_snapshot(
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


def _initial_base_snapshot(
    base: str,
) -> tuple[int, int, int, bool, int, int] | None:
    try:
        observed = _os_stat(base, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except (OSError, TypeError, ValueError):
        _fail("initial local base stat failed")
    snapshot = _directory_snapshot(observed)
    if snapshot[3] or not stat.S_ISDIR(snapshot[2]):
        _fail("local base is not a real non-reparse directory")
    return snapshot


def _final_base_snapshot(base: str) -> tuple[int, int, int, bool, int, int]:
    try:
        observed = _os_stat(base, follow_symlinks=False)
    except (OSError, TypeError, ValueError):
        _fail("final local base stat failed")
    snapshot = _directory_snapshot(observed)
    if snapshot[3] or not stat.S_ISDIR(snapshot[2]):
        _fail("local base ceased to be a real non-reparse directory")
    return snapshot


def _require_base_still_absent(base: str) -> None:
    try:
        _os_stat(base, follow_symlinks=False)
    except FileNotFoundError:
        return
    except (OSError, TypeError, ValueError):
        _fail("final absent-base observation failed")
    _fail("local base appeared between absence observations")


def _entry_name(entry: object, max_utf8_bytes: int) -> tuple[str, bytes]:
    try:
        name = entry.name
    except (AttributeError, TypeError, ValueError):
        _fail("local base entry has no valid name")
    if type(name) is not str or not name or name in {".", ".."}:
        _fail("local base entry name is unsafe")
    if "\x00" in name or "/" in name or "\\" in name:
        _fail("local base entry name is unsafe")
    try:
        encoded = name.encode("utf-8", errors="strict")
    except UnicodeError:
        _fail("local base entry name is not strict UTF-8")
    if len(encoded) > max_utf8_bytes:
        _fail("local base entry name exceeds the UTF-8 byte bound")
    return name, encoded


def _scan_base_once(
    base: str,
    *,
    max_entries: int,
    max_local_claims: int,
    max_unexpected_names: int,
    max_name_utf8_bytes: int,
) -> tuple[
    tuple[tuple[str, str, tuple[int, int, int, bool, int, int, int] | None], ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    iterator = None
    entries: list[object] = []
    pending_error: str | None = None
    try:
        iterator = _os_scandir(base)
        for entry in iterator:
            entries.append(entry)
            if len(entries) > max_entries:
                pending_error = "local base exceeds the entry-count bound"
                break
    except (OSError, TypeError, ValueError):
        pending_error = "local base scan failed"

    if iterator is not None:
        try:
            close = getattr(iterator, "close")
            close()
        except (AttributeError, OSError, TypeError, ValueError):
            _fail("local base scan close failed")
    if pending_error is not None:
        _fail(pending_error)

    named: list[tuple[str, bytes]] = []
    observed_names: set[str] = set()
    for entry in entries:
        name, encoded = _entry_name(entry, max_name_utf8_bytes)
        if name in observed_names:
            _fail("local base scan contains duplicate names")
        observed_names.add(name)
        named.append((name, encoded))
    named.sort(key=lambda item: item[1])

    signature: list[
        tuple[str, str, tuple[int, int, int, bool, int, int, int] | None]
    ] = []
    local_ids: list[str] = []
    unexpected_names: list[str] = []
    for name, _encoded in named:
        if _HEX64_LOWER_RE.fullmatch(name) is None:
            signature.append((name, "unexpected_name", None))
            unexpected_names.append(name)
            continue
        path = _join_path(base, name)
        try:
            observed = _os_stat(path, follow_symlinks=False)
        except (OSError, TypeError, ValueError):
            _fail("local claim candidate stat failed")
        snapshot = _entry_snapshot(observed)
        if not snapshot[3] and stat.S_ISDIR(snapshot[2]):
            classification = "local_claim"
            local_ids.append(name)
        else:
            classification = "unexpected_claim_candidate"
            unexpected_names.append(name)
        signature.append((name, classification, snapshot))

    if len(local_ids) > max_local_claims:
        _fail("local claim directory count exceeds the bound")
    if len(unexpected_names) > max_unexpected_names:
        _fail("unexpected local entry count exceeds the bound")
    return tuple(signature), tuple(local_ids), tuple(unexpected_names)


def _seed_only_claim(
    license_id: str, seed_receipt: PublicClaimReceiptV10
) -> SyntheticLocalClaimAuditV10:
    return SyntheticLocalClaimAuditV10(
        license_id=license_id,
        seed_membership=True,
        local_membership=False,
        set_relation="seeded_missing_local",
        receipt_relation="seed_only",
        seed_receipt_sha256=_receipt_sha256(seed_receipt),
        local_receipt_sha256=None,
        chain_observation="not_present",
        event_count=None,
        last_event_index=None,
        last_event_sha256=None,
        terminal_event=None,
        recorded_verdict=None,
        authority_scope="none",
        licenses_execution=False,
        licenses_later_stage=False,
    )


def _inspection_payload_bytes(inspection: AttemptManifestChainInspectionV10) -> int:
    if type(inspection.event_files) is not tuple:
        _fail("Phase-2b1 inspection event_files is not an exact tuple")
    total = 0
    for event_file in inspection.event_files:
        try:
            raw = event_file.event_bytes
        except (AttributeError, TypeError, ValueError):
            _fail("Phase-2b1 inspection event file is invalid")
        if type(raw) is not bytes:
            _fail("Phase-2b1 inspection event bytes are not exact bytes")
        total += len(raw)
    return total


def _reduce_local_claim(
    root_text: str,
    license_id: str,
    seed_receipt: PublicClaimReceiptV10 | None,
) -> tuple[SyntheticLocalClaimAuditV10, int]:
    try:
        inspection = inspect_local_attempt_manifest_chain_v1_0(root_text, license_id)
    except AttemptManifestV10Error:
        _fail("local attempt-manifest inspection failed")
    if type(inspection) is not AttemptManifestChainInspectionV10:
        _fail("local attempt-manifest inspection returned the wrong type")
    if inspection.license_id != license_id:
        _fail("local attempt-manifest inspection returned the wrong license")
    if inspection.chain_state not in {
        "missing",
        "valid_nonterminal",
        "valid_nonterminal_index_exhausted",
        "valid_terminal",
    }:
        _fail("local attempt-manifest inspection returned an invalid state")

    payload_bytes = _inspection_payload_bytes(inspection)
    seed_membership = seed_receipt is not None
    set_relation = "seed_and_local" if seed_membership else "local_orphan"
    seed_sha = _receipt_sha256(seed_receipt) if seed_receipt is not None else None

    if inspection.chain_state == "missing":
        receipt_relation = "not_observed"
        local_sha = None
    else:
        if (
            type(inspection.claim_receipt) is not PublicClaimReceiptV10
            or type(inspection.claim_receipt_sha256) is not str
        ):
            _fail("valid local inspection lacks a public receipt")
        local_sha = inspection.claim_receipt_sha256
        if seed_receipt is None:
            receipt_relation = "local_only"
        elif inspection.claim_receipt == seed_receipt:
            receipt_relation = "exact_match"
        else:
            receipt_relation = "mismatch"

    return (
        SyntheticLocalClaimAuditV10(
            license_id=license_id,
            seed_membership=seed_membership,
            local_membership=True,
            set_relation=set_relation,
            receipt_relation=receipt_relation,
            seed_receipt_sha256=seed_sha,
            local_receipt_sha256=local_sha,
            chain_observation=inspection.chain_state,
            event_count=inspection.event_count,
            last_event_index=inspection.last_event_index,
            last_event_sha256=inspection.last_event_sha256,
            terminal_event=inspection.terminal_event,
            recorded_verdict=inspection.recorded_verdict,
            authority_scope="none",
            licenses_execution=False,
            licenses_later_stage=False,
        ),
        payload_bytes,
    )


def _build_aggregate(
    *,
    seed: SyntheticClaimSeedV10,
    base_directory_status: str,
    local_ids: tuple[str, ...],
    unexpected_names: tuple[str, ...],
    claim_audits: tuple[SyntheticLocalClaimAuditV10, ...],
    total_event_bytes: int,
    read_work_upper_bound: int,
    admission_upper_bound: int,
) -> SyntheticSeedLocalInventoryAuditV10:
    seed_ids = tuple(receipt.license_id for receipt in seed.claim_receipts)
    seed_set = set(seed_ids)
    local_set = set(local_ids)
    seeded_missing_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.set_relation == "seeded_missing_local"
    )
    local_orphan_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.set_relation == "local_orphan"
    )
    receipt_mismatch_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.receipt_relation == "mismatch"
    )
    terminal_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.chain_observation == "valid_terminal"
    )
    nonterminal_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.chain_observation
        in {"valid_nonterminal", "valid_nonterminal_index_exhausted"}
    )
    empty_chain_ids = tuple(
        item.license_id
        for item in claim_audits
        if item.local_membership and item.chain_observation == "missing"
    )

    set_equality = seed_set == local_set
    all_seeded_local_present = seed.claim_count > 0 and not seeded_missing_ids
    all_seeded_terminal = seed.claim_count > 0 and seed_set.issubset(terminal_ids)
    all_seeded_receipts_match = seed.claim_count > 0 and all(
        item.receipt_relation == "exact_match"
        for item in claim_audits
        if item.seed_membership
    )
    if seed.claim_count == 0 and not local_ids and not unexpected_names:
        coverage_status = "empty_seed"
    elif (
        seed.claim_count > 0
        and not unexpected_names
        and set_equality
        and all_seeded_terminal
        and all_seeded_receipts_match
    ):
        coverage_status = "matched_terminal"
    else:
        coverage_status = "mismatched"

    return SyntheticSeedLocalInventoryAuditV10(
        auditor_schema_version=_AUDITOR_SCHEMA,
        auditor_scope=_AUDITOR_SCOPE,
        origin_status=_ORIGIN_STATUS,
        base_directory_status=base_directory_status,
        seed_file_sha256=seed.seed_file_sha256,
        seed_identity_sha256=seed.seed_identity_sha256,
        seed_count=seed.claim_count,
        local_directory_count=len(local_ids),
        union_claim_count=len(claim_audits),
        examined_claim_count=len(claim_audits),
        total_observed_event_bytes=total_event_bytes,
        read_work_upper_bound_bytes=read_work_upper_bound,
        event_file_admission_upper_bound=admission_upper_bound,
        claim_audits=claim_audits,
        unexpected_entry_names=unexpected_names,
        unexpected_entry_count=len(unexpected_names),
        seeded_missing_ids=seeded_missing_ids,
        local_orphan_ids=local_orphan_ids,
        receipt_mismatch_ids=receipt_mismatch_ids,
        terminal_ids=terminal_ids,
        nonterminal_ids=nonterminal_ids,
        empty_chain_ids=empty_chain_ids,
        coverage_status=coverage_status,
        set_equality=set_equality,
        all_seeded_local_present=all_seeded_local_present,
        all_seeded_terminal=all_seeded_terminal,
        all_seeded_receipts_match=all_seeded_receipts_match,
        seed_origin="caller_supplied_synthetic_bytes",
        seed_binding="exact_bytes_within_call",
        seed_temporal_commitment="not_authenticated",
        remote_inventory_observation="not_performed",
        real_claim_completeness="not_authenticated",
        omitted_claim_detectability="local_orphans_only_none_if_absent_from_both",
        coordinated_omission_detectability="none",
        root_scope="one_caller_supplied_synthetic_root",
        snapshot_scope="sequential_per_claim_observations_not_atomic_inventory",
        resource_status="within_frozen_bounds",
        authority_scope="none",
        canonical_run_authority=False,
        licenses_execution=False,
        licenses_publication=False,
        licenses_recovery=False,
        licenses_later_stage=False,
    )


def audit_synthetic_seed_local_inventory_v1_0(
    root: str | os.PathLike[str], seed_raw: bytes, /
) -> SyntheticSeedLocalInventoryAuditV10:
    """Compare one exact synthetic seed with one complete bounded local base."""

    bounds = _resource_bounds()
    seed = parse_synthetic_claim_seed_v1_0(seed_raw)
    root_text = _root_text_once(root)
    base = _join_path(root_text, *_BASE_COMPONENTS)
    initial_base = _initial_base_snapshot(base)

    seed_by_id = {receipt.license_id: receipt for receipt in seed.claim_receipts}
    if initial_base is None:
        local_ids: tuple[str, ...] = ()
        unexpected_names: tuple[str, ...] = ()
        union_ids = tuple(sorted(seed_by_id))
        if len(union_ids) > bounds[6]:
            _fail("seed/local union exceeds the claim-count bound")
        rows = tuple(_seed_only_claim(item, seed_by_id[item]) for item in union_ids)
        _require_base_still_absent(base)
        return _build_aggregate(
            seed=seed,
            base_directory_status="absent",
            local_ids=local_ids,
            unexpected_names=unexpected_names,
            claim_audits=rows,
            total_event_bytes=0,
            read_work_upper_bound=bounds[8],
            admission_upper_bound=bounds[9],
        )

    scan0, local_ids, unexpected_names = _scan_base_once(
        base,
        max_entries=bounds[3],
        max_local_claims=bounds[2],
        max_unexpected_names=bounds[4],
        max_name_utf8_bytes=bounds[5],
    )
    local_set = set(local_ids)
    union_ids = tuple(sorted(set(seed_by_id).union(local_set)))
    if len(union_ids) > bounds[6]:
        _fail("seed/local union exceeds the claim-count bound")

    rows_list: list[SyntheticLocalClaimAuditV10] = []
    total_event_bytes = 0
    for license_id in union_ids:
        seed_receipt = seed_by_id.get(license_id)
        if license_id not in local_set:
            if seed_receipt is None:
                _fail("seed/local union accounting is inconsistent")
            row = _seed_only_claim(license_id, seed_receipt)
            observed_bytes = 0
        else:
            row, observed_bytes = _reduce_local_claim(
                root_text, license_id, seed_receipt
            )
        total_event_bytes += observed_bytes
        if total_event_bytes > bounds[7]:
            _fail("accepted event bytes exceed the aggregate bound")
        rows_list.append(row)

    scan1, local_ids1, unexpected_names1 = _scan_base_once(
        base,
        max_entries=bounds[3],
        max_local_claims=bounds[2],
        max_unexpected_names=bounds[4],
        max_name_utf8_bytes=bounds[5],
    )
    if (
        scan1 != scan0
        or local_ids1 != local_ids
        or unexpected_names1 != unexpected_names
    ):
        _fail("local base entries changed during observation")
    final_base = _final_base_snapshot(base)
    if final_base != initial_base:
        _fail("local base metadata changed during observation")

    return _build_aggregate(
        seed=seed,
        base_directory_status="present",
        local_ids=local_ids,
        unexpected_names=unexpected_names,
        claim_audits=tuple(rows_list),
        total_event_bytes=total_event_bytes,
        read_work_upper_bound=bounds[8],
        admission_upper_bound=bounds[9],
    )


__all__ = [
    "SyntheticSeedInventoryV10Error",
    "SyntheticClaimSeedV10",
    "SyntheticLocalClaimAuditV10",
    "SyntheticSeedLocalInventoryAuditV10",
    "parse_synthetic_claim_seed_v1_0",
    "audit_synthetic_seed_local_inventory_v1_0",
]
