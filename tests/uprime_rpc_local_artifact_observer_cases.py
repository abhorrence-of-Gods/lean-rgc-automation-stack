"""Noncollectable Phase-2b2b local artifact observer acceptance cases.

The frozen collector imports only the test functions exported by ``__all__``.
Every filesystem fixture is a small synthetic object below ``tmp_path``.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError, asdict, fields, replace
import hashlib
import inspect
import itertools
import os
from pathlib import Path
import stat
import subprocess
import types
from typing import Any

import pytest

from lean_rgc.evals import uprime_rpc_attempt_manifest as manifest
from lean_rgc.evals import uprime_rpc_ledger as ledger
from lean_rgc.evals import uprime_rpc_local_artifact_observer as observer


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
ROW_FIELDS = (
    "artifact_kind",
    "repository_path",
    "observation_state",
    "reason_codes",
    "artifact_sha256",
    "artifact_bytes",
    "byte_limit",
    "content_validation",
    "authority_scope",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)
SET_FIELDS = (
    "observer_schema_version",
    "observer_scope",
    "origin_status",
    "selector_scope",
    "claim_receipt",
    "claim_receipt_sha256",
    "anchor",
    "registered_run_dir",
    "parent_namespace_state",
    "parent_reason_codes",
    "reservation",
    "ledger",
    "report",
    "state_vector",
    "present_count",
    "absent_count",
    "indeterminate_count",
    "total_present_bytes",
    "accepted_byte_upper_bound",
    "read_work_upper_bound_bytes",
    "read_call_upper_bound",
    "peak_buffer_upper_bound_bytes",
    "hash_algorithm",
    "snapshot_scope",
    "root_scope",
    "selector_binding",
    "basename_spelling_verification",
    "hostile_concurrent_reparse_prevention",
    "ancestor_link_containment",
    "reservation_validation",
    "ledger_validation",
    "report_validation",
    "cross_artifact_binding",
    "manifest_binding",
    "inventory_binding",
    "anchor_uniqueness",
    "artifact_claim_binding",
    "durability_observation",
    "cas_observation",
    "publication_observation",
    "recovery_observation",
    "witness_observation",
    "remote_claim_authentication",
    "git_object_authentication",
    "authority_scope",
    "canonical_run_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

KINDS = ("reservation", "ledger", "report")
LIMITS = (1_048_576, 134_217_728, 16_777_216)
SUFFIXES = (
    ".json.reservation",
    ".responses.jsonl",
    ".json",
)
REGISTERED_RUN_DIR = "runs/uprime_u1_rpc_20260710"
SCHEMA = "lean-rgc-uprime-u1-local-artifact-set-observer-v0.1"
RECEIPT_SCHEMA = "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
RECEIPT_DOMAIN = b"lean-rgc-uprime-u1-attempt-v1\0"
REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
REMOTE_BRANCH = "refs/heads/codex/uprime-odlrq-plan"
CLAIM_PREFIX = "refs/tags/uprime-u1-attempts/"

PARENT_REASONS = (
    "stable_parent_directory",
    "stable_parent_absence",
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
INDETERMINATE_REASONS = (
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
PRE_CLOSE_REASONS = (
    "fstat_error",
    "path_descriptor_mismatch",
    "seek_error",
    "read_error",
    "early_eof",
    "growth",
    "descriptor_drift",
    "content_drift",
)


def _receipt_mapping(
    *,
    candidate_commit: str = "a" * 40,
    license_commit: str = "123456789abc" + "b" * 28,
) -> dict[str, Any]:
    license_id = hashlib.sha256(
        RECEIPT_DOMAIN + candidate_commit.encode("ascii")
    ).hexdigest()
    return {
        "schema_version": RECEIPT_SCHEMA,
        "candidate_commit": candidate_commit,
        "license_commit": license_commit,
        "license_id": license_id,
        "remote_url": REMOTE_URL,
        "remote_branch_ref": REMOTE_BRANCH,
        "remote_claim_ref": CLAIM_PREFIX + license_id,
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


def _receipt_digest(value: manifest.PublicClaimReceiptV10 | None = None) -> str:
    receipt = _receipt_record() if value is None else value
    mapping = {name: getattr(receipt, name) for name in RECEIPT_FIELDS}
    raw = ledger.canonical_json_bytes(mapping)
    assert not raw.endswith(b"\n")
    return hashlib.sha256(raw).hexdigest().upper()


def _repository_paths(receipt: manifest.PublicClaimReceiptV10 | None = None) -> tuple[str, ...]:
    value = _receipt_record() if receipt is None else receipt
    prefix = f"{REGISTERED_RUN_DIR}/rpc_diagnostic_{value.license_commit[:12]}"
    return tuple(prefix + suffix for suffix in SUFFIXES)


def _host_paths(root: Path, receipt: manifest.PublicClaimReceiptV10 | None = None) -> tuple[Path, ...]:
    return tuple(root.joinpath(*path.split("/")) for path in _repository_paths(receipt))


def _write_artifacts(
    root: Path,
    payloads: tuple[bytes | None, bytes | None, bytes | None],
    receipt: manifest.PublicClaimReceiptV10 | None = None,
) -> tuple[Path, ...]:
    paths = _host_paths(root, receipt)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(paths, payloads, strict=True):
        if payload is not None:
            path.write_bytes(payload)
    return paths


def _three_present(
    tmp_path: Path,
    name: str,
    payloads: tuple[bytes, bytes, bytes] = (b"abc", b"ledger", b"report"),
) -> tuple[Path, tuple[Path, ...], tuple[bytes, bytes, bytes]]:
    root = (tmp_path / name).absolute()
    paths = _write_artifacts(root, payloads)
    return root, paths, payloads


def _path_key(path: Any) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _set_small_limits(
    monkeypatch: pytest.MonkeyPatch,
    limits: tuple[int, int, int] = (3, 5, 7),
    chunk: int = 2,
) -> None:
    for name, value in zip(
        ("_MAX_RESERVATION_BYTES", "_MAX_LEDGER_BYTES", "_MAX_REPORT_BYTES"),
        limits,
        strict=True,
    ):
        monkeypatch.setattr(observer, name, value)
    monkeypatch.setattr(observer, "_READ_CHUNK_BYTES", chunk)
    monkeypatch.setattr(observer, "_MAX_TOTAL_ACCEPTED_BYTES", sum(limits))
    monkeypatch.setattr(observer, "_MAX_RETURNED_PAYLOAD_WORK_BYTES", 2 * sum(limits) + 3)
    monkeypatch.setattr(
        observer,
        "_MAX_READ_CALLS",
        2 * sum((limit + chunk - 1) // chunk + 1 for limit in limits),
    )
    monkeypatch.setattr(observer, "_MAX_PEAK_BUFFER_BYTES", chunk)


def _row(
    kind_index: int,
    state: str,
    *,
    receipt: manifest.PublicClaimReceiptV10 | None = None,
    payload: bytes = b"x",
    reason: str | None = None,
) -> observer.LocalArtifactObservationV10:
    value = _receipt_record() if receipt is None else receipt
    if state == "present":
        reasons = ("stable_bounded_regular_file",)
        digest: str | None = hashlib.sha256(payload).hexdigest().upper()
        byte_count: int | None = len(payload)
    elif state == "absent":
        reasons = ("absent_at_both_points",)
        digest = None
        byte_count = None
    else:
        reasons = ("initial_stat_error" if reason is None else reason,)
        digest = None
        byte_count = None
    return observer.LocalArtifactObservationV10(
        artifact_kind=KINDS[kind_index],
        repository_path=_repository_paths(value)[kind_index],
        observation_state=state,
        reason_codes=reasons,
        artifact_sha256=digest,
        artifact_bytes=byte_count,
        byte_limit=LIMITS[kind_index],
        content_validation="not_performed",
        authority_scope="none",
        licenses_execution=False,
        licenses_publication=False,
        licenses_recovery=False,
        licenses_later_stage=False,
    )


def _set_record(
    states: tuple[str, str, str] = ("present", "absent", "indeterminate"),
    *,
    receipt: manifest.PublicClaimReceiptV10 | None = None,
) -> observer.LocalArtifactSetObservationV10:
    value = _receipt_record() if receipt is None else receipt
    rows = tuple(_row(index, state, receipt=value) for index, state in enumerate(states))
    return observer.LocalArtifactSetObservationV10(
        observer_schema_version=SCHEMA,
        observer_scope="three_receipt_derived_local_paths_raw_bytes_only",
        origin_status="unknown_may_be_synthetic",
        selector_scope="one_caller_supplied_public_receipt",
        claim_receipt=value,
        claim_receipt_sha256=_receipt_digest(value),
        anchor=value.license_commit[:12],
        registered_run_dir=REGISTERED_RUN_DIR,
        parent_namespace_state="present",
        parent_reason_codes=("stable_parent_directory",),
        reservation=rows[0],
        ledger=rows[1],
        report=rows[2],
        state_vector=states,
        present_count=states.count("present"),
        absent_count=states.count("absent"),
        indeterminate_count=states.count("indeterminate"),
        total_present_bytes=sum(
            row.artifact_bytes or 0 for row in rows if row.observation_state == "present"
        ),
        accepted_byte_upper_bound=152_043_520,
        read_work_upper_bound_bytes=304_087_043,
        read_call_upper_bound=4_646,
        peak_buffer_upper_bound_bytes=65_536,
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


def _as_constructor_mapping(value: Any) -> dict[str, Any]:
    return {field.name: getattr(value, field.name) for field in fields(value)}


def _invalid_value(value: Any) -> Any:
    if type(value) is str:
        return None
    if type(value) is int:
        return True
    if type(value) is bool:
        return 1
    if type(value) is tuple:
        return list(value)
    return object()


def _fake_stat(value: Any | None = None, **changes: Any) -> types.SimpleNamespace:
    names = (
        "st_mode",
        "st_ino",
        "st_dev",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_file_attributes",
    )
    data = {
        name: getattr(value, name)
        for name in names
        if value is not None and hasattr(value, name)
    }
    data.update(changes)
    return types.SimpleNamespace(**data)


def _parent_stat(
    *,
    mode: int = stat.S_IFDIR | 0o755,
    dev: int = 1,
    ino: int = 2,
    attributes: int = 0,
) -> types.SimpleNamespace:
    return _fake_stat(
        st_mode=mode,
        st_dev=dev,
        st_ino=ino,
        st_file_attributes=attributes,
    )


def _artifact_stat(
    *,
    mode: int = stat.S_IFREG | 0o644,
    dev: int = 1,
    ino: int = 2,
    ctime_ns: int = 3,
    size: int = 1,
    mtime_ns: int = 4,
    attributes: int = 0,
) -> types.SimpleNamespace:
    return _fake_stat(
        st_mode=mode,
        st_dev=dev,
        st_ino=ino,
        st_ctime_ns=ctime_ns,
        st_size=size,
        st_mtime_ns=mtime_ns,
        st_file_attributes=attributes,
    )


def _source_tree() -> ast.Module:
    path = Path(observer.__file__).resolve()
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


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
                stat.S_IFMT(int(observed.st_mode)),
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
            if any(
                token in folded
                for token in ("exposure", "burn", "retir", "read_ledger")
            ):
                markers.append(path.as_posix())
    return tuple(sorted(markers))


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        if prefix is not None:
            return prefix + "." + node.attr
    return None


def test_uprime_local_artifact_observer_literal_receipt_digest_anchor_and_paths() -> None:
    receipt = _receipt_record()
    mapping = _receipt_mapping()
    raw = ledger.canonical_json_bytes(mapping)
    assert tuple(mapping) == RECEIPT_FIELDS
    assert raw == ledger.canonical_json_bytes(
        {name: getattr(receipt, name) for name in RECEIPT_FIELDS}
    )
    assert b"\n" not in raw
    assert len(raw) == 934
    assert _receipt_digest(receipt) == hashlib.sha256(raw).hexdigest().upper() == (
        "63647F30BD5F126226EEA45CA958A2F7A58FE24208F0B7B7CE1A242B738041AA"
    )
    assert receipt.license_commit[:12] == "123456789abc"
    assert _repository_paths(receipt) == (
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_123456789abc.json.reservation",
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_123456789abc.responses.jsonl",
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_123456789abc.json",
    )


def test_uprime_local_artifact_observer_receipt_selector_is_free_and_anchor_can_collide(
    tmp_path: Path,
) -> None:
    root = str((tmp_path / "free-selector").absolute())
    first = _receipt_record(_receipt_mapping(candidate_commit="1" * 40))
    second = _receipt_record(_receipt_mapping(candidate_commit="2" * 40))
    assert first.license_id != second.license_id
    assert first.license_commit[:12] == second.license_commit[:12] == "123456789abc"
    observed_first = observer.observe_local_rpc_artifact_set_v1_0(root, first)
    observed_second = observer.observe_local_rpc_artifact_set_v1_0(root, second)
    assert observed_first.anchor == observed_second.anchor == "123456789abc"
    assert observed_first.claim_receipt_sha256 != observed_second.claim_receipt_sha256
    assert observed_first.inventory_binding == observed_second.inventory_binding == "not_performed"
    assert observed_first.anchor_uniqueness == observed_second.anchor_uniqueness == "not_performed"
    assert observed_first.artifact_claim_binding == observed_second.artifact_claim_binding == "not_performed"


def test_uprime_local_artifact_observer_public_surface_records_signature_and_all() -> None:
    assert observer.LocalArtifactObservationV10Error.__bases__ == (ValueError,)
    assert tuple(field.name for field in fields(observer.LocalArtifactObservationV10)) == ROW_FIELDS
    assert tuple(field.name for field in fields(observer.LocalArtifactSetObservationV10)) == SET_FIELDS
    assert observer.LocalArtifactObservationV10.__annotations__ == dict(
        zip(
            ROW_FIELDS,
            (
                str,
                str,
                str,
                tuple[str, ...],
                str | None,
                int | None,
                int,
                str,
                str,
                bool,
                bool,
                bool,
                bool,
            ),
            strict=True,
        )
    )
    set_annotations: dict[str, Any] = {name: str for name in SET_FIELDS}
    set_annotations["claim_receipt"] = manifest.PublicClaimReceiptV10
    set_annotations["parent_reason_codes"] = tuple[str, ...]
    set_annotations["reservation"] = observer.LocalArtifactObservationV10
    set_annotations["ledger"] = observer.LocalArtifactObservationV10
    set_annotations["report"] = observer.LocalArtifactObservationV10
    set_annotations["state_vector"] = tuple[str, str, str]
    for name in (
        "present_count",
        "absent_count",
        "indeterminate_count",
        "total_present_bytes",
        "accepted_byte_upper_bound",
        "read_work_upper_bound_bytes",
        "read_call_upper_bound",
        "peak_buffer_upper_bound_bytes",
    ):
        set_annotations[name] = int
    for name in (
        "canonical_run_authority",
        "licenses_execution",
        "licenses_publication",
        "licenses_recovery",
        "licenses_later_stage",
    ):
        set_annotations[name] = bool
    assert observer.LocalArtifactSetObservationV10.__annotations__ == {
        name: set_annotations[name] for name in SET_FIELDS
    }
    for record_type in (
        observer.LocalArtifactObservationV10,
        observer.LocalArtifactSetObservationV10,
    ):
        assert record_type.__dataclass_params__.frozen is True
        assert "__slots__" in record_type.__dict__
        assert "__dict__" not in record_type.__dict__

    signature = inspect.signature(observer.observe_local_rpc_artifact_set_v1_0)
    assert tuple(signature.parameters) == ("root", "claim_receipt")
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert tuple(
        (parameter.name, parameter.annotation)
        for parameter in signature.parameters.values()
    ) == (("root", str), ("claim_receipt", manifest.PublicClaimReceiptV10))
    assert signature.return_annotation is observer.LocalArtifactSetObservationV10
    assert type(observer.__all__) is list
    assert observer.__all__ == [
        "LocalArtifactObservationV10Error",
        "LocalArtifactObservationV10",
        "LocalArtifactSetObservationV10",
        "observe_local_rpc_artifact_set_v1_0",
    ]


def test_uprime_local_artifact_observer_records_are_frozen_slotted_and_replace_revalidates() -> None:
    result = _set_record()
    assert not hasattr(result, "__dict__")
    assert not hasattr(result.reservation, "__dict__")
    assert type(result.state_vector) is tuple
    assert type(result.parent_reason_codes) is tuple
    assert type(result.reservation.reason_codes) is tuple
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.anchor = "forged"  # type: ignore[misc]
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        replace(result.reservation, licenses_execution=True)
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        replace(result, present_count=99)


@pytest.mark.parametrize("field", ROW_FIELDS)
def test_uprime_local_artifact_observer_row_constructor_rejects_every_wrong_field_type(
    field: str,
) -> None:
    mapping = _as_constructor_mapping(_row(0, "present"))
    mapping[field] = _invalid_value(mapping[field])
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactObservationV10(**mapping)


@pytest.mark.parametrize("field", SET_FIELDS)
def test_uprime_local_artifact_observer_set_constructor_rejects_every_wrong_field_type(
    field: str,
) -> None:
    mapping = _as_constructor_mapping(_set_record())
    mapping[field] = _invalid_value(mapping[field])
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactSetObservationV10(**mapping)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("observer_schema_version", "v2"),
        ("observer_scope", "bundle"),
        ("origin_status", "authenticated"),
        ("selector_scope", "inventory"),
        ("claim_receipt_sha256", "0" * 64),
        ("anchor", "0" * 12),
        ("registered_run_dir", "runs"),
        ("parent_namespace_state", "absent"),
        ("parent_reason_codes", ("stable_parent_absence",)),
        ("state_vector", ("present", "present", "present")),
        ("present_count", 2),
        ("absent_count", 2),
        ("indeterminate_count", 2),
        ("total_present_bytes", 999),
        ("accepted_byte_upper_bound", 152_043_519),
        ("read_work_upper_bound_bytes", 304_087_042),
        ("read_call_upper_bound", 4_645),
        ("peak_buffer_upper_bound_bytes", 65_535),
        ("hash_algorithm", "sha256"),
        ("snapshot_scope", "atomic"),
        ("root_scope", "authenticated"),
        ("selector_binding", "authenticated"),
        ("basename_spelling_verification", "performed"),
        ("hostile_concurrent_reparse_prevention", "provided"),
        ("ancestor_link_containment", "authenticated"),
        ("reservation_validation", "performed"),
        ("ledger_validation", "performed"),
        ("report_validation", "performed"),
        ("cross_artifact_binding", "performed"),
        ("manifest_binding", "performed"),
        ("inventory_binding", "performed"),
        ("anchor_uniqueness", "performed"),
        ("artifact_claim_binding", "performed"),
        ("durability_observation", "performed"),
        ("cas_observation", "performed"),
        ("publication_observation", "performed"),
        ("recovery_observation", "performed"),
        ("witness_observation", "performed"),
        ("remote_claim_authentication", "performed"),
        ("git_object_authentication", "performed"),
        ("authority_scope", "local"),
        ("canonical_run_authority", True),
        ("licenses_execution", True),
        ("licenses_publication", True),
        ("licenses_recovery", True),
        ("licenses_later_stage", True),
    ),
)
def test_uprime_local_artifact_observer_set_constructor_rejects_cross_field_forgery(
    field: str,
    bad_value: Any,
) -> None:
    mapping = _as_constructor_mapping(_set_record())
    mapping[field] = bad_value
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactSetObservationV10(**mapping)


@pytest.mark.parametrize("row_field", ("reservation", "ledger", "report"))
def test_uprime_local_artifact_observer_set_constructor_rejects_row_identity_or_order_forgery(
    row_field: str,
) -> None:
    mapping = _as_constructor_mapping(_set_record())
    replacement_index = {"reservation": 1, "ledger": 2, "report": 0}[row_field]
    mapping[row_field] = _row(replacement_index, "present")
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactSetObservationV10(**mapping)


@pytest.mark.parametrize("states", tuple(itertools.product(("present", "absent", "indeterminate"), repeat=3)))
def test_uprime_local_artifact_observer_all_27_vectors_construct_and_derive(
    states: tuple[str, str, str],
) -> None:
    result = _set_record(states)
    assert result.state_vector == states
    assert result.present_count == states.count("present")
    assert result.absent_count == states.count("absent")
    assert result.indeterminate_count == states.count("indeterminate")
    assert result.total_present_bytes == states.count("present")
    assert tuple(
        (row.artifact_kind, row.observation_state)
        for row in (result.reservation, result.ledger, result.report)
    ) == tuple(zip(KINDS, states, strict=True))


@pytest.mark.parametrize("reason", INDETERMINATE_REASONS)
def test_uprime_local_artifact_observer_every_local_indeterminate_reason_constructs(
    reason: str,
) -> None:
    row = _row(0, "indeterminate", reason=reason)
    assert row.reason_codes == (reason,)
    if reason in PRE_CLOSE_REASONS:
        mapping = _as_constructor_mapping(row)
        mapping["reason_codes"] = (reason, "close_error")
        assert observer.LocalArtifactObservationV10(**mapping).reason_codes == (
            reason,
            "close_error",
        )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("artifact_kind", "ledger"),
        ("repository_path", "runs/uprime_u1_rpc_20260710/forged"),
        ("observation_state", "unknown"),
        ("reason_codes", ()),
        ("reason_codes", ("stable_bounded_regular_file", "close_error")),
        ("reason_codes", ("initial_stat_error", "close_error")),
        ("reason_codes", ("read_error", "read_error")),
        ("artifact_sha256", "a" * 64),
        ("artifact_sha256", "A" * 63),
        ("artifact_bytes", -1),
        ("artifact_bytes", LIMITS[0] + 1),
        ("byte_limit", LIMITS[1]),
        ("content_validation", "performed"),
        ("authority_scope", "local"),
        ("licenses_execution", True),
        ("licenses_publication", True),
        ("licenses_recovery", True),
        ("licenses_later_stage", True),
    ),
)
def test_uprime_local_artifact_observer_row_constructor_rejects_cross_field_forgery(
    field: str,
    bad_value: Any,
) -> None:
    mapping = _as_constructor_mapping(_row(0, "present"))
    mapping[field] = bad_value
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactObservationV10(**mapping)


@pytest.mark.parametrize(
    "bad_reasons",
    tuple(
        (reason, "close_error")
        for reason in INDETERMINATE_REASONS
        if reason not in PRE_CLOSE_REASONS
    )
    + (
        ("close_error", "close_error"),
        ("read_error", "growth"),
        ("close_error", "read_error"),
    ),
)
def test_uprime_local_artifact_observer_row_constructor_rejects_unreachable_reason_pairs(
    bad_reasons: tuple[str, ...],
) -> None:
    mapping = _as_constructor_mapping(_row(0, "indeterminate"))
    mapping["reason_codes"] = bad_reasons
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.LocalArtifactObservationV10(**mapping)


@pytest.mark.parametrize(
    ("state", "parent_reason"),
    (("absent", "stable_parent_absence"),)
    + tuple(("indeterminate", reason) for reason in PARENT_REASONS[2:]),
)
def test_uprime_local_artifact_observer_parent_derived_rows_and_aggregate_construct(
    state: str,
    parent_reason: str,
) -> None:
    receipt = _receipt_record()
    rows = []
    for index in range(3):
        mapping = _as_constructor_mapping(_row(index, "indeterminate", receipt=receipt))
        mapping.update(
            observation_state=state,
            reason_codes=(parent_reason,),
            artifact_sha256=None,
            artifact_bytes=None,
        )
        rows.append(observer.LocalArtifactObservationV10(**mapping))
    base = _as_constructor_mapping(_set_record(receipt=receipt))
    base.update(
        parent_namespace_state=state,
        parent_reason_codes=(parent_reason,),
        reservation=rows[0],
        ledger=rows[1],
        report=rows[2],
        state_vector=(state, state, state),
        present_count=0,
        absent_count=3 if state == "absent" else 0,
        indeterminate_count=3 if state == "indeterminate" else 0,
        total_present_bytes=0,
    )
    result = observer.LocalArtifactSetObservationV10(**base)
    assert result.parent_reason_codes == (parent_reason,)
    assert result.state_vector == (state, state, state)


def test_uprime_local_artifact_observer_real_parent_absence_has_zero_child_creation(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "missing-root").absolute()
    before = tuple(tmp_path.rglob("*"))
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.parent_namespace_state == "absent"
    assert result.parent_reason_codes == ("stable_parent_absence",)
    assert result.state_vector == ("absent", "absent", "absent")
    assert all(
        row.reason_codes == ("stable_parent_absence",)
        and row.artifact_sha256 is None
        and row.artifact_bytes is None
        for row in (result.reservation, result.ledger, result.report)
    )
    assert tuple(tmp_path.rglob("*")) == before


def test_uprime_local_artifact_observer_parent_absence_does_not_join_or_touch_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = str((tmp_path / "join-absence").absolute())
    real_join = observer._os_path_join
    joins: list[tuple[tuple[Any, ...], str]] = []
    stat_calls: list[str] = []
    open_calls: list[Any] = []

    def tracked_join(*parts: Any) -> str:
        result = real_join(*parts)
        joins.append((parts, result))
        return result

    def absent(path: Any, **kwargs: Any) -> Any:
        stat_calls.append(os.fspath(path))
        raise FileNotFoundError

    def forbidden_open(*args: Any, **kwargs: Any) -> Any:
        open_calls.append((args, kwargs))
        raise AssertionError("child open reached")

    monkeypatch.setattr(observer, "_os_path_join", tracked_join)
    monkeypatch.setattr(observer, "_os_stat", absent)
    monkeypatch.setattr(observer, "_os_open", forbidden_open)
    result = observer.observe_local_rpc_artifact_set_v1_0(root, _receipt_record())
    assert result.parent_reason_codes == ("stable_parent_absence",)
    assert len(stat_calls) == 2
    assert stat_calls[0] == stat_calls[1]
    assert all("rpc_diagnostic_" not in joined for _parts, joined in joins)
    assert open_calls == []


def test_uprime_local_artifact_observer_real_parent_present_direct_absence(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "direct-absence").absolute()
    _host_paths(root)[0].parent.mkdir(parents=True)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.parent_namespace_state == "present"
    assert result.parent_reason_codes == ("stable_parent_directory",)
    assert result.state_vector == ("absent", "absent", "absent")
    assert all(
        row.reason_codes == ("absent_at_both_points",)
        for row in (result.reservation, result.ledger, result.report)
    )


def test_uprime_local_artifact_observer_each_direct_absence_uses_exactly_two_nofollow_stats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "direct-absence-counts").absolute()
    paths = _host_paths(root)
    paths[0].parent.mkdir(parents=True)
    keys = tuple(map(_path_key, paths))
    real_stat = observer._os_stat
    calls = {key: [] for key in keys}

    def tracked_stat(path: Any, **kwargs: Any) -> Any:
        key = _path_key(path)
        if key in calls:
            calls[key].append(kwargs)
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", tracked_stat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.state_vector == ("absent",) * 3
    assert calls == {
        key: [{"follow_symlinks": False}, {"follow_symlinks": False}]
        for key in keys
    }


@pytest.mark.parametrize(
    ("script", "reason", "expected_calls"),
    (
        ((PermissionError(),), "parent_initial_stat_error", 1),
        ((OSError("generic"),), "parent_initial_stat_error", 1),
        ((FileNotFoundError(), PermissionError()), "parent_absence_recheck_error", 2),
        ((FileNotFoundError(), OSError("generic")), "parent_absence_recheck_error", 2),
        ((FileNotFoundError(), _parent_stat()), "parent_absence_changed", 2),
        ((_parent_stat(dev=True),), "parent_metadata_invalid", 1),
        ((_parent_stat(mode=stat.S_IFLNK | 0o777),), "parent_reparse_entry", 1),
        ((_parent_stat(mode=stat.S_IFREG | 0o644),), "parent_nondirectory", 1),
        (
            (_parent_stat(attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),),
            "parent_reparse_entry",
            1,
        ),
    ),
)
def test_uprime_local_artifact_observer_parent_initial_and_absence_failures_clear_all_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: tuple[Any, ...],
    reason: str,
    expected_calls: int,
) -> None:
    root = str((tmp_path / f"parent-{reason}").absolute())
    queue = list(script)
    calls: list[tuple[Any, dict[str, Any]]] = []
    child_calls: list[Any] = []

    def scripted_stat(path: Any, **kwargs: Any) -> Any:
        calls.append((path, kwargs))
        assert queue
        value = queue.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def forbidden_open(*args: Any, **kwargs: Any) -> Any:
        child_calls.append((args, kwargs))
        raise AssertionError("unsafe/absent parent must not open a child")

    monkeypatch.setattr(observer, "_os_stat", scripted_stat)
    monkeypatch.setattr(observer, "_os_open", forbidden_open)
    result = observer.observe_local_rpc_artifact_set_v1_0(root, _receipt_record())
    assert len(calls) == expected_calls
    assert queue == []
    assert all(kwargs == {"follow_symlinks": False} for _path, kwargs in calls)
    assert result.parent_namespace_state == "indeterminate"
    assert result.parent_reason_codes == (reason,)
    assert result.state_vector == ("indeterminate",) * 3
    assert all(
        row.reason_codes == (reason,)
        and row.artifact_sha256 is None
        and row.artifact_bytes is None
        for row in (result.reservation, result.ledger, result.report)
    )
    assert child_calls == []


@pytest.mark.parametrize("field", ("st_dev", "st_ino", "st_mode", "st_file_attributes"))
def test_uprime_local_artifact_observer_every_parent_metadata_input_rejects_bool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root = str((tmp_path / f"parent-bool-{field}").absolute())
    parent = _parent_stat()
    setattr(parent, field, True)
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: parent)
    result = observer.observe_local_rpc_artifact_set_v1_0(root, _receipt_record())
    assert result.parent_reason_codes == ("parent_metadata_invalid",)
    assert result.state_vector == ("indeterminate",) * 3


@pytest.mark.parametrize("error_type", (RuntimeError, ValueError))
def test_uprime_local_artifact_observer_parent_ordinary_exception_is_classified_not_leaked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    def failed_parent_stat(*args: Any, **kwargs: Any) -> Any:
        raise error_type("injected ordinary filesystem seam failure")

    monkeypatch.setattr(observer, "_os_stat", failed_parent_stat)
    result = observer.observe_local_rpc_artifact_set_v1_0(
        str((tmp_path / "parent-runtime").absolute()),
        _receipt_record(),
    )
    assert result.parent_namespace_state == "indeterminate"
    assert result.parent_reason_codes == ("parent_initial_stat_error",)
    assert result.state_vector == ("indeterminate",) * 3
    assert all(
        row.reason_codes == ("parent_initial_stat_error",)
        for row in (result.reservation, result.ledger, result.report)
    )


def test_uprime_local_artifact_observer_parent_exposed_file_attributes_none_is_metadata_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _parent_stat()
    parent.st_file_attributes = None
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: parent)
    result = observer.observe_local_rpc_artifact_set_v1_0(
        str((tmp_path / "parent-attributes-none").absolute()),
        _receipt_record(),
    )
    assert result.parent_reason_codes == ("parent_metadata_invalid",)
    assert result.state_vector == ("indeterminate",) * 3


@pytest.mark.parametrize(
    ("final_value", "reason"),
    (
        (FileNotFoundError(), "parent_final_stat_error"),
        (_parent_stat(ino=True), "parent_final_entry_invalid"),
        (_parent_stat(mode=stat.S_IFLNK | 0o777), "parent_final_entry_invalid"),
        (_parent_stat(mode=stat.S_IFREG | 0o644), "parent_final_entry_invalid"),
        (_parent_stat(dev=3), "parent_drift"),
        (_parent_stat(ino=3), "parent_drift"),
        (_parent_stat(mode=stat.S_IFDIR | 0o700), "parent_drift"),
    ),
)
def test_uprime_local_artifact_observer_final_parent_failure_replaces_child_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_value: Any,
    reason: str,
) -> None:
    root = (tmp_path / f"parent-final-{reason}").absolute()
    parent = _host_paths(root)[0].parent
    parent.mkdir(parents=True)
    real_stat = observer._os_stat
    parent_calls = 0

    def final_parent_failure(path: Any, **kwargs: Any) -> Any:
        nonlocal parent_calls
        if os.path.normcase(os.path.abspath(os.fspath(path))) == os.path.normcase(os.path.abspath(parent)):
            parent_calls += 1
            if parent_calls == 2:
                if isinstance(final_value, BaseException):
                    raise final_value
                return final_value
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", final_parent_failure)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert parent_calls == 2
    assert result.parent_namespace_state == "indeterminate"
    assert result.parent_reason_codes == (reason,)
    assert result.state_vector == ("indeterminate",) * 3
    assert all(
        row.reason_codes == (reason,)
        and row.artifact_sha256 is None
        and row.artifact_bytes is None
        for row in (result.reservation, result.ledger, result.report)
    )


@pytest.mark.parametrize("field", ("st_dev", "st_ino", "st_mode"))
def test_uprime_local_artifact_observer_each_parent_d_component_drift_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root = (tmp_path / f"parent-drift-{field}").absolute()
    parent = _host_paths(root)[0].parent
    parent.mkdir(parents=True)
    parent_key = _path_key(parent)
    real_stat = observer._os_stat
    calls = 0

    def drifting_parent(path: Any, **kwargs: Any) -> Any:
        nonlocal calls
        observed = real_stat(path, **kwargs)
        if _path_key(path) == parent_key:
            calls += 1
            if calls == 2:
                old = int(getattr(observed, field))
                if field == "st_mode":
                    return _fake_stat(observed, st_mode=old ^ 0o077)
                return _fake_stat(observed, **{field: old + 1})
        return observed

    monkeypatch.setattr(observer, "_os_stat", drifting_parent)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == 2
    assert result.parent_reason_codes == ("parent_drift",)
    assert result.state_vector == ("indeterminate",) * 3


def test_uprime_local_artifact_observer_real_empty_malformed_and_arbitrary_bytes_present(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "present-three").absolute()
    payloads = (b"", b"not-json\n{torn", bytes(range(256)) + b"\x00\xff")
    _write_artifacts(root, payloads)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.state_vector == ("present", "present", "present")
    assert result.total_present_bytes == sum(map(len, payloads))
    for row, payload, kind, limit, path in zip(
        (result.reservation, result.ledger, result.report),
        payloads,
        KINDS,
        LIMITS,
        _repository_paths(),
        strict=True,
    ):
        assert asdict(row) == {
            "artifact_kind": kind,
            "repository_path": path,
            "observation_state": "present",
            "reason_codes": ("stable_bounded_regular_file",),
            "artifact_sha256": hashlib.sha256(payload).hexdigest().upper(),
            "artifact_bytes": len(payload),
            "byte_limit": limit,
            "content_validation": "not_performed",
            "authority_scope": "none",
            "licenses_execution": False,
            "licenses_publication": False,
            "licenses_recovery": False,
            "licenses_later_stage": False,
        }


def test_uprime_local_artifact_observer_real_mixed_pai_keeps_fixed_order_and_labels(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "mixed-pai").absolute()
    paths = _write_artifacts(root, (b"reservation", None, None))
    paths[2].mkdir()
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.state_vector == ("present", "absent", "indeterminate")
    assert result.present_count == result.absent_count == result.indeterminate_count == 1
    assert result.total_present_bytes == len(b"reservation")
    assert result.reservation.reason_codes == ("stable_bounded_regular_file",)
    assert result.ledger.reason_codes == ("absent_at_both_points",)
    assert result.report.reason_codes == ("nonregular_entry",)
    assert (
        result.snapshot_scope,
        result.cross_artifact_binding,
        result.durability_observation,
        result.authority_scope,
    ) == (
        "sequential_per_artifact_not_atomic_bundle",
        "not_performed",
        "not_performed",
        "none",
    )


@pytest.mark.parametrize(
    ("script", "reason"),
    (
        ((PermissionError(),), "initial_stat_error"),
        ((OSError("generic"),), "initial_stat_error"),
        ((FileNotFoundError(), PermissionError()), "absence_recheck_error"),
        ((FileNotFoundError(), OSError("generic")), "absence_recheck_error"),
        ((FileNotFoundError(), _artifact_stat()), "absence_changed"),
        ((_artifact_stat(dev=True),), "metadata_invalid"),
        ((_artifact_stat(mode=stat.S_IFLNK | 0o777),), "reparse_entry"),
        ((_artifact_stat(mode=stat.S_IFDIR | 0o755),), "nonregular_entry"),
        (
            (_artifact_stat(attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),),
            "reparse_entry",
        ),
        ((_artifact_stat(size=LIMITS[0] + 1),), "size_limit"),
    ),
)
def test_uprime_local_artifact_observer_artifact_path_classification_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: tuple[Any, ...],
    reason: str,
) -> None:
    root = (tmp_path / f"artifact-{reason}").absolute()
    target = _host_paths(root)[0]
    target.parent.mkdir(parents=True)
    target_key = os.path.normcase(os.path.abspath(target))
    real_stat = observer._os_stat
    queue = list(script)
    target_calls: list[dict[str, Any]] = []
    open_calls: list[Any] = []

    def scripted_target(path: Any, **kwargs: Any) -> Any:
        if os.path.normcase(os.path.abspath(os.fspath(path))) == target_key:
            target_calls.append(kwargs)
            assert queue
            value = queue.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        return real_stat(path, **kwargs)

    def forbidden_open(*args: Any, **kwargs: Any) -> Any:
        open_calls.append((args, kwargs))
        raise AssertionError("path-classification failure must precede open")

    monkeypatch.setattr(observer, "_os_stat", scripted_target)
    monkeypatch.setattr(observer, "_os_open", forbidden_open)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert queue == []
    assert all(kwargs == {"follow_symlinks": False} for kwargs in target_calls)
    assert result.reservation.observation_state == "indeterminate"
    assert result.reservation.reason_codes == (reason,)
    assert result.ledger.observation_state == result.report.observation_state == "absent"
    assert open_calls == []


@pytest.mark.parametrize(
    "field",
    (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_ctime_ns",
        "st_size",
        "st_mtime_ns",
        "st_file_attributes",
    ),
)
def test_uprime_local_artifact_observer_every_initial_path_metadata_input_rejects_bool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root = (tmp_path / f"path-bool-{field}").absolute()
    target = _host_paths(root)[0]
    target.parent.mkdir(parents=True)
    target_key = _path_key(target)
    real_stat = observer._os_stat

    def malformed(path: Any, **kwargs: Any) -> Any:
        if _path_key(path) == target_key:
            value = _artifact_stat()
            setattr(value, field, True)
            return value
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", malformed)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("metadata_invalid",)
    assert result.ledger.observation_state == result.report.observation_state == "absent"


def test_uprime_local_artifact_observer_artifact_exposed_file_attributes_none_is_metadata_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "artifact-attributes-none").absolute()
    target = _host_paths(root)[0]
    target.parent.mkdir(parents=True)
    target_key = _path_key(target)
    real_stat = observer._os_stat

    def malformed(path: Any, **kwargs: Any) -> Any:
        if _path_key(path) == target_key:
            return _artifact_stat(attributes=None)  # type: ignore[arg-type]
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", malformed)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("metadata_invalid",)
    assert result.ledger.observation_state == result.report.observation_state == "absent"


@pytest.mark.parametrize("kind_index", range(3))
@pytest.mark.parametrize("delta", (-1, 0, 1))
def test_uprime_local_artifact_observer_actual_small_kind_boundaries_under_injected_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind_index: int,
    delta: int,
) -> None:
    limits = (3, 5, 7)
    _set_small_limits(monkeypatch, limits)
    root = (tmp_path / f"boundary-{kind_index}-{delta}").absolute()
    payloads: list[bytes | None] = [None, None, None]
    payloads[kind_index] = b"x" * (limits[kind_index] + delta)
    _write_artifacts(root, tuple(payloads))  # type: ignore[arg-type]
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    row = (result.reservation, result.ledger, result.report)[kind_index]
    assert row.byte_limit == limits[kind_index]
    if delta <= 0:
        assert row.observation_state == "present"
        assert row.artifact_bytes == limits[kind_index] + delta
    else:
        assert row.observation_state == "indeterminate"
        assert row.reason_codes == ("size_limit",)
        assert row.artifact_sha256 is row.artifact_bytes is None
    assert result.accepted_byte_upper_bound == sum(limits)
    assert result.read_work_upper_bound_bytes == 2 * sum(limits) + 3
    assert result.read_call_upper_bound == 2 * (
        (3 + 1) // 2 + 1 + (5 + 1) // 2 + 1 + (7 + 1) // 2 + 1
    )
    assert result.peak_buffer_upper_bound_bytes == 2


def test_uprime_local_artifact_observer_open_flags_two_pass_calls_and_close_are_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_small_limits(monkeypatch)
    root, paths, _payloads = _three_present(
        tmp_path,
        "exact-io",
        (b"abc", b"12345", b"1234567"),
    )
    real_open = observer._os_open
    real_fstat = observer._os_fstat
    real_lseek = observer._os_lseek
    real_read = observer._os_read
    real_close = observer._os_close
    fd_kinds: dict[int, int] = {}
    open_calls: list[tuple[str, int]] = []
    fstat_calls: dict[int, int] = {0: 0, 1: 0, 2: 0}
    seek_calls: dict[int, list[tuple[int, int]]] = {0: [], 1: [], 2: []}
    read_calls: dict[int, list[int]] = {0: [], 1: [], 2: []}
    close_calls: dict[int, int] = {0: 0, 1: 0, 2: 0}
    keys = tuple(map(_path_key, paths))

    def tracked_open(path: Any, flags: int) -> int:
        key = _path_key(path)
        index = keys.index(key)
        open_calls.append((key, flags))
        fd = real_open(path, flags)
        fd_kinds[fd] = index
        return fd

    def tracked_fstat(fd: int) -> Any:
        fstat_calls[fd_kinds[fd]] += 1
        return real_fstat(fd)

    def tracked_lseek(fd: int, offset: int, whence: int) -> int:
        seek_calls[fd_kinds[fd]].append((offset, whence))
        return real_lseek(fd, offset, whence)

    def tracked_read(fd: int, count: int) -> bytes:
        read_calls[fd_kinds[fd]].append(count)
        return real_read(fd, count)

    def tracked_close(fd: int) -> None:
        index = fd_kinds[fd]
        close_calls[index] += 1
        return real_close(fd)

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_fstat", tracked_fstat)
    monkeypatch.setattr(observer, "_os_lseek", tracked_lseek)
    monkeypatch.setattr(observer, "_os_read", tracked_read)
    monkeypatch.setattr(observer, "_os_close", tracked_close)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.state_vector == ("present", "present", "present")
    expected_flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    assert open_calls == list(zip(keys, (expected_flags,) * 3, strict=True))
    forbidden_flags = sum(
        getattr(os, name, 0)
        for name in ("O_CREAT", "O_WRONLY", "O_RDWR", "O_APPEND", "O_TRUNC")
    )
    assert all(flags & forbidden_flags == 0 for _path, flags in open_calls)
    assert fstat_calls == {0: 3, 1: 3, 2: 3}
    assert seek_calls == {
        0: [(0, os.SEEK_SET), (0, os.SEEK_SET)],
        1: [(0, os.SEEK_SET), (0, os.SEEK_SET)],
        2: [(0, os.SEEK_SET), (0, os.SEEK_SET)],
    }
    assert read_calls == {
        0: [2, 1, 1, 2, 1, 1],
        1: [2, 2, 1, 1, 2, 2, 1, 1],
        2: [2, 2, 2, 1, 1, 2, 2, 2, 1, 1],
    }
    assert close_calls == {0: 1, 1: 1, 2: 1}


@pytest.mark.parametrize("bad_fd", (True, False, -1, -9, None, "3"))
def test_uprime_local_artifact_observer_open_return_requires_exact_nonnegative_int_and_is_not_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_fd: Any,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"open-return-{bad_fd!r}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_close = observer._os_close
    close_calls: list[int] = []

    def injected_open(path: Any, flags: int) -> Any:
        if _path_key(path) == target_key:
            return bad_fd
        return real_open(path, flags)

    def tracked_close(fd: int) -> None:
        close_calls.append(fd)
        return real_close(fd)

    monkeypatch.setattr(observer, "_os_open", injected_open)
    monkeypatch.setattr(observer, "_os_close", tracked_close)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("open_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"
    assert len(close_calls) == 2


def test_uprime_local_artifact_observer_open_exception_maps_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, "open-exception")
    target_key = _path_key(paths[0])
    real_open = observer._os_open

    def failed_open(path: Any, flags: int) -> int:
        if _path_key(path) == target_key:
            raise OSError("injected")
        return real_open(path, flags)

    monkeypatch.setattr(observer, "_os_open", failed_open)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("open_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize(
    ("stage", "reason", "error_type"),
    (
        ("open", "open_error", RuntimeError),
        ("fstat", "fstat_error", RuntimeError),
        ("seek", "seek_error", RuntimeError),
        ("read", "read_error", RuntimeError),
        ("close", "close_error", RuntimeError),
        ("final_stat", "final_stat_error", RuntimeError),
        ("read", "read_error", ValueError),
        ("close", "close_error", ValueError),
    ),
)
def test_uprime_local_artifact_observer_ordinary_exception_at_representative_io_stage_maps_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    reason: str,
    error_type: type[Exception],
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"runtime-{stage}")
    target_key = _path_key(paths[0])
    real_stat = observer._os_stat
    real_open = observer._os_open
    real_fstat = observer._os_fstat
    real_lseek = observer._os_lseek
    real_read = observer._os_read
    real_close = observer._os_close
    fd_is_target: dict[int, bool] = {}
    target_path_stats = 0
    injected_calls = 0

    def tracked_stat(path: Any, **kwargs: Any) -> Any:
        nonlocal target_path_stats, injected_calls
        if _path_key(path) == target_key:
            target_path_stats += 1
            if stage == "final_stat" and target_path_stats == 2:
                injected_calls += 1
                raise error_type("injected ordinary final-stat failure")
        return real_stat(path, **kwargs)

    def tracked_open(path: Any, flags: int) -> int:
        nonlocal injected_calls
        is_target = _path_key(path) == target_key
        if is_target and stage == "open":
            injected_calls += 1
            raise error_type("injected ordinary open failure")
        fd = real_open(path, flags)
        fd_is_target[fd] = is_target
        return fd

    def tracked_fstat(fd: int) -> Any:
        nonlocal injected_calls
        if fd_is_target.get(fd, False) and stage == "fstat":
            injected_calls += 1
            raise error_type("injected ordinary fstat failure")
        return real_fstat(fd)

    def tracked_lseek(fd: int, offset: int, whence: int) -> int:
        nonlocal injected_calls
        if fd_is_target.get(fd, False) and stage == "seek":
            injected_calls += 1
            raise error_type("injected ordinary seek failure")
        return real_lseek(fd, offset, whence)

    def tracked_read(fd: int, count: int) -> bytes:
        nonlocal injected_calls
        if fd_is_target.get(fd, False) and stage == "read":
            injected_calls += 1
            raise error_type("injected ordinary read failure")
        return real_read(fd, count)

    def tracked_close(fd: int) -> None:
        nonlocal injected_calls
        result = real_close(fd)
        if fd_is_target.get(fd, False) and stage == "close":
            injected_calls += 1
            raise error_type("injected ordinary close failure")
        return result

    monkeypatch.setattr(observer, "_os_stat", tracked_stat)
    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_fstat", tracked_fstat)
    monkeypatch.setattr(observer, "_os_lseek", tracked_lseek)
    monkeypatch.setattr(observer, "_os_read", tracked_read)
    monkeypatch.setattr(observer, "_os_close", tracked_close)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert injected_calls == 1
    assert result.parent_namespace_state == "present"
    assert result.reservation.observation_state == "indeterminate"
    assert result.reservation.reason_codes == (reason,)
    assert result.reservation.artifact_sha256 is result.reservation.artifact_bytes is None
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize("stage", (1, 2, 3))
@pytest.mark.parametrize("failure", ("exception", "malformed", "nonregular"))
def test_uprime_local_artifact_observer_each_fstat_stage_failure_maps_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: int,
    failure: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"fstat-{stage}-{failure}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_fstat = observer._os_fstat
    fd_is_target: dict[int, bool] = {}
    target_calls = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def injected_fstat(fd: int) -> Any:
        nonlocal target_calls
        observed = real_fstat(fd)
        if fd_is_target.get(fd, False):
            target_calls += 1
            if target_calls == stage:
                if failure == "exception":
                    raise OSError("injected")
                if failure == "malformed":
                    return _fake_stat(observed, st_mtime_ns=True)
                return _fake_stat(observed, st_mode=stat.S_IFDIR | 0o755)
        return observed

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_fstat", injected_fstat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert target_calls == stage
    assert result.reservation.reason_codes == ("fstat_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize(
    "field",
    ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_size", "st_mtime_ns"),
)
def test_uprime_local_artifact_observer_every_descriptor_numeric_component_rejects_bool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"fstat-bool-{field}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_fstat = observer._os_fstat
    fd_is_target: dict[int, bool] = {}

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def malformed_fstat(fd: int) -> Any:
        observed = real_fstat(fd)
        if fd_is_target.get(fd, False):
            return _fake_stat(observed, **{field: True})
        return observed

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_fstat", malformed_fstat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("fstat_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize("stage", (2, 3))
@pytest.mark.parametrize(
    "field",
    ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_size", "st_mtime_ns"),
)
def test_uprime_local_artifact_observer_each_f_family_component_drift_maps_descriptor_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: int,
    field: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"f-drift-{stage}-{field}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_fstat = observer._os_fstat
    fd_is_target: dict[int, bool] = {}
    calls = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def drifting_fstat(fd: int) -> Any:
        nonlocal calls
        observed = real_fstat(fd)
        if not fd_is_target.get(fd, False):
            return observed
        calls += 1
        if calls != stage:
            return observed
        old = int(getattr(observed, field))
        if field == "st_mode":
            return _fake_stat(observed, st_mode=old ^ 0o200)
        return _fake_stat(observed, **{field: old + 1})

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_fstat", drifting_fstat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == stage
    assert result.reservation.reason_codes == ("descriptor_drift",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize("side", ("path", "descriptor"))
@pytest.mark.parametrize("field", ("st_dev", "st_ino", "st_size", "st_mtime_ns"))
def test_uprime_local_artifact_observer_every_initial_b_component_mismatch_maps_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    side: str,
    field: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"binding-{side}-{field}")
    target_key = _path_key(paths[0])
    if side == "path":
        real_stat = observer._os_stat

        def mismatching_stat(path: Any, **kwargs: Any) -> Any:
            observed = real_stat(path, **kwargs)
            if _path_key(path) == target_key:
                return _fake_stat(observed, **{field: int(getattr(observed, field)) + 1})
            return observed

        monkeypatch.setattr(observer, "_os_stat", mismatching_stat)
    else:
        real_open = observer._os_open
        real_fstat = observer._os_fstat
        fd_is_target: dict[int, bool] = {}

        def tracked_open(path: Any, flags: int) -> int:
            fd = real_open(path, flags)
            fd_is_target[fd] = _path_key(path) == target_key
            return fd

        def mismatching_fstat(fd: int) -> Any:
            observed = real_fstat(fd)
            if fd_is_target.get(fd, False):
                return _fake_stat(observed, **{field: int(getattr(observed, field)) + 1})
            return observed

        monkeypatch.setattr(observer, "_os_open", tracked_open)
        monkeypatch.setattr(observer, "_os_fstat", mismatching_fstat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.reason_codes == ("path_descriptor_mismatch",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


def test_uprime_local_artifact_observer_cross_family_mode_and_ctime_difference_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, paths, payloads = _three_present(tmp_path, "cross-family-mode-ctime")
    target_key = _path_key(paths[0])
    real_stat = observer._os_stat

    def differing_path_stat(path: Any, **kwargs: Any) -> Any:
        observed = real_stat(path, **kwargs)
        if _path_key(path) == target_key:
            return _fake_stat(
                observed,
                st_mode=int(observed.st_mode) ^ 0o200,
                st_ctime_ns=int(observed.st_ctime_ns) + 99,
            )
        return observed

    monkeypatch.setattr(observer, "_os_stat", differing_path_stat)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert result.reservation.observation_state == "present"
    assert result.reservation.artifact_sha256 == hashlib.sha256(payloads[0]).hexdigest().upper()


@pytest.mark.parametrize("stage", (1, 2))
@pytest.mark.parametrize("bad_return", ("exception", True, False, 1, -1, None, "0"))
def test_uprime_local_artifact_observer_each_seek_requires_exact_integer_zero_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: int,
    bad_return: Any,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"seek-{stage}-{bad_return!r}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_lseek = observer._os_lseek
    fd_is_target: dict[int, bool] = {}
    calls = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def injected_seek(fd: int, offset: int, whence: int) -> Any:
        nonlocal calls
        if fd_is_target.get(fd, False):
            calls += 1
            if calls == stage:
                if bad_return == "exception":
                    raise OSError("injected")
                return bad_return
        return real_lseek(fd, offset, whence)

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_lseek", injected_seek)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == stage
    assert result.reservation.reason_codes == ("seek_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize(
    ("stage", "failure", "reason"),
    (
        (1, "exception", "read_error"),
        (4, "exception", "read_error"),
        (1, "wrong_type", "read_error"),
        (3, "wrong_type", "read_error"),
        (1, "overlong", "read_error"),
        (3, "probe_overlong", "read_error"),
        (1, "short", "early_eof"),
        (1, "zero", "early_eof"),
        (3, "growth", "growth"),
        (6, "growth", "growth"),
    ),
)
def test_uprime_local_artifact_observer_read_and_probe_failure_matrix_is_exact_and_no_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: int,
    failure: str,
    reason: str,
) -> None:
    _set_small_limits(monkeypatch)
    root, paths, _payloads = _three_present(
        tmp_path,
        f"read-{stage}-{failure}",
        (b"abc", b"12345", b"1234567"),
    )
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_read = observer._os_read
    fd_is_target: dict[int, bool] = {}
    calls: list[int] = []

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def injected_read(fd: int, count: int) -> Any:
        if not fd_is_target.get(fd, False):
            return real_read(fd, count)
        calls.append(count)
        if len(calls) != stage:
            return real_read(fd, count)
        if failure == "exception":
            raise OSError("injected")
        if failure == "wrong_type":
            return bytearray(count)
        if failure == "overlong":
            return b"x" * (count + 1)
        if failure == "probe_overlong":
            return b"xx"
        if failure == "short":
            real_read(fd, count)
            return b"x" * (count - 1)
        if failure == "zero":
            real_read(fd, count)
            return b""
        if failure == "growth":
            real_read(fd, count)
            return b"x"
        raise AssertionError(failure)

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_read", injected_read)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert len(calls) == stage
    assert result.reservation.reason_codes == (reason,)
    assert result.reservation.artifact_sha256 is result.reservation.artifact_bytes is None
    assert result.ledger.observation_state == result.report.observation_state == "present"


def test_uprime_local_artifact_observer_same_size_second_pass_content_drift_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_small_limits(monkeypatch)
    root, paths, _payloads = _three_present(
        tmp_path,
        "content-drift",
        (b"abc", b"12345", b"1234567"),
    )
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_read = observer._os_read
    fd_is_target: dict[int, bool] = {}
    calls = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def drifting_read(fd: int, count: int) -> bytes:
        nonlocal calls
        chunk = real_read(fd, count)
        if not fd_is_target.get(fd, False):
            return chunk
        calls += 1
        if calls == 4:
            assert len(chunk) == count == 2
            return b"z" + chunk[1:]
        return chunk

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_read", drifting_read)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == 6
    assert result.reservation.reason_codes == ("content_drift",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


def test_uprime_local_artifact_observer_earlier_row_endpoint_is_not_extended_by_later_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = b"old"
    replacement = b"new"
    root, paths, _payloads = _three_present(
        tmp_path,
        "sequential-endpoint",
        (original, b"ledger", b"report"),
    )
    ledger_key = _path_key(paths[1])
    real_stat = observer._os_stat
    mutated = False

    def mutate_after_reservation_endpoint(path: Any, **kwargs: Any) -> Any:
        nonlocal mutated
        if _path_key(path) == ledger_key and not mutated:
            paths[0].write_bytes(replacement)
            mutated = True
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", mutate_after_reservation_endpoint)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert mutated is True
    assert paths[0].read_bytes() == replacement
    assert result.state_vector == ("present", "present", "present")
    assert result.reservation.artifact_sha256 == hashlib.sha256(original).hexdigest().upper()
    assert result.reservation.artifact_bytes == len(original)
    assert result.snapshot_scope == "sequential_per_artifact_not_atomic_bundle"
    assert result.cross_artifact_binding == "not_performed"
    assert result.durability_observation == "not_performed"
    assert result.cas_observation == "not_performed"


@pytest.mark.parametrize("bad_close", ("exception", True, False, 0, 1, "none"))
def test_uprime_local_artifact_observer_close_requires_none_is_once_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_close: Any,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"close-{bad_close!r}")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_close = observer._os_close
    fd_is_target: dict[int, bool] = {}
    target_close_calls = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def injected_close(fd: int) -> Any:
        nonlocal target_close_calls
        result = real_close(fd)
        if fd_is_target.get(fd, False):
            target_close_calls += 1
            assert result is None
            if bad_close == "exception":
                raise OSError("injected")
            if bad_close == "none":
                return "not-none"
            return bad_close
        return result

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_close", injected_close)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert target_close_calls == 1
    assert result.reservation.reason_codes == ("close_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


def test_uprime_local_artifact_observer_close_failure_appends_after_pending_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, "primary-close-order")
    target_key = _path_key(paths[0])
    real_open = observer._os_open
    real_read = observer._os_read
    real_close = observer._os_close
    fd_is_target: dict[int, bool] = {}
    target_reads = 0
    target_closes = 0

    def tracked_open(path: Any, flags: int) -> int:
        fd = real_open(path, flags)
        fd_is_target[fd] = _path_key(path) == target_key
        return fd

    def failed_read(fd: int, count: int) -> Any:
        nonlocal target_reads
        if fd_is_target.get(fd, False):
            target_reads += 1
            return bytearray(count)
        return real_read(fd, count)

    def failed_close(fd: int) -> None:
        nonlocal target_closes
        result = real_close(fd)
        if fd_is_target.get(fd, False):
            target_closes += 1
            assert result is None
            raise OSError("injected close")
        return result

    monkeypatch.setattr(observer, "_os_open", tracked_open)
    monkeypatch.setattr(observer, "_os_read", failed_read)
    monkeypatch.setattr(observer, "_os_close", failed_close)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert target_reads == target_closes == 1
    assert result.reservation.reason_codes == ("read_error", "close_error")
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize("failure", ("missing", "error"))
def test_uprime_local_artifact_observer_final_path_stat_failure_maps_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"final-stat-{failure}")
    target_key = _path_key(paths[0])
    real_stat = observer._os_stat
    calls = 0

    def final_failure(path: Any, **kwargs: Any) -> Any:
        nonlocal calls
        if _path_key(path) == target_key:
            calls += 1
            if calls == 2:
                if failure == "missing":
                    raise FileNotFoundError
                raise PermissionError
        return real_stat(path, **kwargs)

    monkeypatch.setattr(observer, "_os_stat", final_failure)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == 2
    assert result.reservation.reason_codes == ("final_stat_error",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize(
    ("mutation", "value"),
    (
        ("st_dev", True),
        ("st_ino", True),
        ("st_mode", True),
        ("st_ctime_ns", True),
        ("st_size", True),
        ("st_mtime_ns", True),
        ("st_mode", stat.S_IFDIR | 0o755),
        ("st_mode", stat.S_IFLNK | 0o777),
        ("st_file_attributes", getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),
    ),
)
def test_uprime_local_artifact_observer_final_path_invalid_metadata_or_type_maps_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    value: Any,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"final-invalid-{mutation}-{value}")
    target_key = _path_key(paths[0])
    real_stat = observer._os_stat
    calls = 0

    def final_invalid(path: Any, **kwargs: Any) -> Any:
        nonlocal calls
        observed = real_stat(path, **kwargs)
        if _path_key(path) == target_key:
            calls += 1
            if calls == 2:
                return _fake_stat(observed, **{mutation: value})
        return observed

    monkeypatch.setattr(observer, "_os_stat", final_invalid)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == 2
    assert result.reservation.reason_codes == ("final_entry_invalid",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


@pytest.mark.parametrize(
    "field",
    ("st_dev", "st_ino", "st_mode", "st_ctime_ns", "st_size", "st_mtime_ns"),
)
def test_uprime_local_artifact_observer_each_valid_path_family_component_drift_maps_path_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    root, paths, _payloads = _three_present(tmp_path, f"path-drift-{field}")
    target_key = _path_key(paths[0])
    real_stat = observer._os_stat
    calls = 0

    def final_drift(path: Any, **kwargs: Any) -> Any:
        nonlocal calls
        observed = real_stat(path, **kwargs)
        if _path_key(path) == target_key:
            calls += 1
            if calls == 2:
                old = int(getattr(observed, field))
                if field == "st_mode":
                    return _fake_stat(observed, st_mode=old ^ 0o200)
                return _fake_stat(observed, **{field: old + 1})
        return observed

    monkeypatch.setattr(observer, "_os_stat", final_drift)
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    assert calls == 2
    assert result.reservation.reason_codes == ("path_drift",)
    assert result.ledger.observation_state == result.report.observation_state == "present"


class _HostilePathLike:
    def __init__(self) -> None:
        self.calls = 0

    def __fspath__(self) -> str:
        self.calls += 1
        raise AssertionError("__fspath__ must not be called")


class _RootSubclass(str):
    pass


class _ReceiptSubclass(manifest.PublicClaimReceiptV10):
    pass


@pytest.mark.parametrize("root", ("", "relative", b"C:\\x", _RootSubclass("C:\\x")))
def test_uprime_local_artifact_observer_root_invalid_before_filesystem(
    monkeypatch: pytest.MonkeyPatch,
    root: Any,
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(root, _receipt_record())
    assert calls == []


def test_uprime_local_artifact_observer_hostile_pathlike_rejects_without_callback_or_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = _HostilePathLike()
    calls: list[Any] = []
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(hostile, _receipt_record())  # type: ignore[arg-type]
    assert hostile.calls == 0
    assert calls == []


def test_uprime_local_artifact_observer_receipt_exact_type_reconstruction_and_bypass_reject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = str((tmp_path / "receipt-types").absolute())
    mapping = _receipt_mapping()
    subclass = object.__new__(_ReceiptSubclass)
    for field, value in mapping.items():
        object.__setattr__(subclass, field, copy.deepcopy(value))
    invalid = _receipt_record(mapping)
    object.__setattr__(invalid, "license_commit", "0" * 40)
    for value in (None, object(), subclass, invalid):
        calls: list[Any] = []
        monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
        with pytest.raises(observer.LocalArtifactObservationV10Error):
            observer.observe_local_rpc_artifact_set_v1_0(root, value)  # type: ignore[arg-type]
        assert calls == []

    monkeypatch.undo()
    original = _receipt_record(mapping)
    result = observer.observe_local_rpc_artifact_set_v1_0(root, original)
    assert result.claim_receipt == original
    assert result.claim_receipt is not original
    assert result.claim_receipt_sha256 == _receipt_digest(original)
    object.__setattr__(original, "license_commit", "0" * 40)
    assert result.claim_receipt.license_commit == mapping["license_commit"]
    assert result.anchor == "123456789abc"


@pytest.mark.parametrize("field", RECEIPT_FIELDS)
def test_uprime_local_artifact_observer_every_bypass_mutated_receipt_field_rejects_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    receipt = _receipt_record()
    object.__setattr__(receipt, field, None)
    calls: list[Any] = []
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(
            str((tmp_path / field).absolute()),
            receipt,
        )
    assert calls == []


def test_uprime_local_artifact_observer_lexical_root_is_joined_without_normalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lexical = str(tmp_path.absolute()) + os.sep + "Case" + os.sep + ".." + os.sep + "ROOT"
    calls: list[tuple[Any, dict[str, Any]]] = []

    def missing(path: Any, **kwargs: Any) -> Any:
        calls.append((path, kwargs))
        raise FileNotFoundError

    monkeypatch.setattr(observer, "_os_stat", missing)
    result = observer.observe_local_rpc_artifact_set_v1_0(lexical, _receipt_record())
    expected_parent = os.path.join(lexical, "runs", "uprime_u1_rpc_20260710")
    assert calls == [
        (expected_parent, {"follow_symlinks": False}),
        (expected_parent, {"follow_symlinks": False}),
    ]
    assert result.parent_reason_codes == ("stable_parent_absence",)


def test_uprime_local_artifact_observer_path_construction_failure_is_public_and_pre_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stat_calls: list[Any] = []

    def failed_join(*args: Any) -> str:
        raise OSError("injected join")

    monkeypatch.setattr(observer, "_os_path_join", failed_join)
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: stat_calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(
            str((tmp_path / "join-failure").absolute()),
            _receipt_record(),
        )
    assert stat_calls == []


@pytest.mark.parametrize(
    ("constant", "bad_value"),
    (
        ("_MAX_RESERVATION_BYTES", True),
        ("_MAX_LEDGER_BYTES", -1),
        ("_MAX_REPORT_BYTES", None),
        ("_READ_CHUNK_BYTES", 0),
        ("_MAX_TOTAL_ACCEPTED_BYTES", -1),
        ("_MAX_RETURNED_PAYLOAD_WORK_BYTES", False),
        ("_MAX_READ_CALLS", -1),
        ("_MAX_PEAK_BUFFER_BYTES", 0),
    ),
)
def test_uprime_local_artifact_observer_invalid_resource_constant_rejects_before_io(
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    bad_value: Any,
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(observer, constant, bad_value)
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(os.path.abspath("synthetic"), _receipt_record())
    assert calls == []


@pytest.mark.parametrize(
    "constant",
    (
        "_MAX_TOTAL_ACCEPTED_BYTES",
        "_MAX_RETURNED_PAYLOAD_WORK_BYTES",
        "_MAX_READ_CALLS",
        "_MAX_PEAK_BUFFER_BYTES",
    ),
)
def test_uprime_local_artifact_observer_inconsistent_derived_resource_rejects_before_io(
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(observer, constant, getattr(observer, constant) + 1)
    monkeypatch.setattr(observer, "_os_stat", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(observer.LocalArtifactObservationV10Error):
        observer.observe_local_rpc_artifact_set_v1_0(os.path.abspath("synthetic"), _receipt_record())
    assert calls == []


def test_uprime_local_artifact_observer_exact_resource_formulas_and_negative_suffix() -> None:
    assert observer._MAX_RESERVATION_BYTES == 1_048_576
    assert observer._MAX_LEDGER_BYTES == 134_217_728
    assert observer._MAX_REPORT_BYTES == 16_777_216
    assert observer._READ_CHUNK_BYTES == 65_536
    assert observer._MAX_TOTAL_ACCEPTED_BYTES == sum(LIMITS) == 152_043_520
    assert observer._MAX_RETURNED_PAYLOAD_WORK_BYTES == 2 * sum(LIMITS) + 3 == 304_087_043
    assert observer._MAX_READ_CALLS == 2 * (16 + 2_048 + 256 + 3) == 4_646
    assert observer._MAX_PEAK_BUFFER_BYTES == observer._READ_CHUNK_BYTES == 65_536
    result = _set_record()
    suffix = asdict(result)
    assert suffix["basename_spelling_verification"] == "not_performed"
    assert suffix["hostile_concurrent_reparse_prevention"] == "not_provided"
    assert suffix["ancestor_link_containment"] == "not_authenticated"
    assert all(
        suffix[name] == "not_performed"
        for name in (
            "reservation_validation",
            "ledger_validation",
            "report_validation",
            "cross_artifact_binding",
            "manifest_binding",
            "inventory_binding",
            "anchor_uniqueness",
            "artifact_claim_binding",
            "durability_observation",
            "cas_observation",
            "publication_observation",
            "recovery_observation",
            "witness_observation",
            "remote_claim_authentication",
            "git_object_authentication",
        )
    )
    assert suffix["canonical_run_authority"] is False
    assert all(suffix[name] is False for name in SET_FIELDS if name.startswith("licenses_"))


def test_uprime_local_artifact_observer_source_imports_and_os_seams_are_exact() -> None:
    tree = _source_tree()
    assert observer._FILESYSTEM_ERRORS == (Exception,)
    modules: set[str] = set()
    imported: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.add(module)
            imported.setdefault(module, set()).update(alias.name for alias in node.names)
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
    }
    assert imported["lean_rgc.evals.uprime_rpc_ledger"] == {"canonical_json_bytes"}
    expected_seams = {
        "_os_path_isabs": "os.path.isabs",
        "_os_path_join": "os.path.join",
        "_os_stat": "os.stat",
        "_os_open": "os.open",
        "_os_fstat": "os.fstat",
        "_os_lseek": "os.lseek",
        "_os_read": "os.read",
        "_os_close": "os.close",
    }
    observed_seams: dict[str, str | None] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.startswith("_os_"):
                assert target.id not in observed_seams
                observed_seams[target.id] = _qualified_name(node.value)
    assert observed_seams == expected_seams
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    qualified_calls = tuple(_qualified_name(node.func) for node in calls)
    assert {name for name in qualified_calls if (name or "").startswith("_os_")} == set(
        expected_seams
    )
    assert not any((name or "").startswith("os.path.") for name in qualified_calls)
    assert not any(name == "open" or (name or "").startswith("builtins.") for name in qualified_calls)
    assert not any(name == "os.scandir" or (name or "").endswith("_scandir") for name in qualified_calls)
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom))
        for node in ast.walk(tree)
    )


def test_uprime_local_artifact_observer_source_has_no_write_or_expansive_capability() -> None:
    tree = _source_tree()
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = tuple(_qualified_name(node.func) for node in calls)
    forbidden = {
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
        "link",
        "symlink",
        "mknod",
        "mkfifo",
        "fsync",
        "system",
        "popen",
        "startfile",
        "resolve",
        "abspath",
        "realpath",
        "normcase",
        "fspath",
        "sleep",
    }
    assert not any(name is not None and name.rsplit(".", 1)[-1] in forbidden for name in names)
    forbidden_status_names = {
        "bundle_status",
        "complete",
        "verified",
        "all_present",
        "mixed",
        "published",
        "durable",
    }
    assert forbidden_status_names.isdisjoint(SET_FIELDS)
    assert not any(
        isinstance(node, ast.Constant)
        and type(node.value) is str
        and node.value in forbidden_status_names
        for node in ast.walk(tree)
    )


def test_uprime_local_artifact_observer_source_payload_lifetime_and_open_flags_ast() -> None:
    tree = _source_tree()
    read_pass = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_read_pass"
    )
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        and node is not read_pass
        for node in ast.walk(read_pass)
    )
    module_read_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _qualified_name(node.func) == "_os_read"
    ]
    pass_read_calls = [
        node
        for node in ast.walk(read_pass)
        if isinstance(node, ast.Call) and _qualified_name(node.func) == "_os_read"
    ]
    assert module_read_calls == pass_read_calls
    assert len(pass_read_calls) == 2

    loop = next(node for node in read_pass.body if isinstance(node, ast.While))
    assert tuple(type(node) for node in loop.body) == (
        ast.Assign,
        ast.Try,
        ast.If,
        ast.Assign,
        ast.If,
        ast.If,
        ast.Expr,
        ast.AugAssign,
        ast.Delete,
    )
    chunk_try = loop.body[1]
    assert isinstance(chunk_try, ast.Try)
    assert len(chunk_try.body) == 1 and isinstance(chunk_try.body[0], ast.Assign)
    chunk_assignment = chunk_try.body[0]
    assert len(chunk_assignment.targets) == 1
    assert isinstance(chunk_assignment.targets[0], ast.Name)
    assert chunk_assignment.targets[0].id == "chunk"
    assert isinstance(chunk_assignment.value, ast.Call)
    assert _qualified_name(chunk_assignment.value.func) == "_os_read"
    assert len(chunk_try.handlers) == 1
    assert tuple(type(node) for node in chunk_try.handlers[0].body) == (ast.Return,)

    for branch in (loop.body[2], loop.body[4], loop.body[5]):
        assert isinstance(branch, ast.If)
        assert tuple(type(node) for node in branch.body) == (ast.Delete, ast.Return)
        deletion = branch.body[0]
        assert isinstance(deletion, ast.Delete)
        assert len(deletion.targets) == 1
        assert isinstance(deletion.targets[0], ast.Name)
        assert deletion.targets[0].id == "chunk"
    update = loop.body[6]
    assert isinstance(update, ast.Expr) and isinstance(update.value, ast.Call)
    assert _qualified_name(update.value.func) == "hasher.update"
    assert len(update.value.args) == 1
    assert isinstance(update.value.args[0], ast.Name) and update.value.args[0].id == "chunk"
    final_chunk_delete = loop.body[8]
    assert isinstance(final_chunk_delete, ast.Delete)
    assert len(final_chunk_delete.targets) == 1
    assert isinstance(final_chunk_delete.targets[0], ast.Name)
    assert final_chunk_delete.targets[0].id == "chunk"

    loop_index = read_pass.body.index(loop)
    probe_try = read_pass.body[loop_index + 1]
    assert isinstance(probe_try, ast.Try)
    assert len(probe_try.body) == 1 and isinstance(probe_try.body[0], ast.Assign)
    probe_assignment = probe_try.body[0]
    assert len(probe_assignment.targets) == 1
    assert isinstance(probe_assignment.targets[0], ast.Name)
    assert probe_assignment.targets[0].id == "probe"
    assert isinstance(probe_assignment.value, ast.Call)
    assert _qualified_name(probe_assignment.value.func) == "_os_read"
    assert len(probe_try.handlers) == 1
    assert tuple(type(node) for node in probe_try.handlers[0].body) == (ast.Return,)
    probe_type_branch = read_pass.body[loop_index + 2]
    assert isinstance(probe_type_branch, ast.If)
    assert tuple(type(node) for node in probe_type_branch.body) == (ast.Delete, ast.Return)
    probe_length_assignment = read_pass.body[loop_index + 3]
    assert isinstance(probe_length_assignment, ast.Assign)
    assert isinstance(probe_length_assignment.value, ast.Call)
    assert _qualified_name(probe_length_assignment.value.func) == "len"
    assert isinstance(probe_length_assignment.value.args[0], ast.Name)
    assert probe_length_assignment.value.args[0].id == "probe"
    probe_delete = read_pass.body[loop_index + 4]
    assert isinstance(probe_delete, ast.Delete)
    assert isinstance(probe_delete.targets[0], ast.Name)
    assert probe_delete.targets[0].id == "probe"

    payload_loads = {
        name: [
            node
            for node in ast.walk(read_pass)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id == name
        ]
        for name in ("chunk", "probe")
    }
    assert len(payload_loads["chunk"]) == 3
    assert len(payload_loads["probe"]) == 2
    assert not any(
        isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Lambda))
        and any(
            isinstance(descendant, ast.Name)
            and descendant.id in {"chunk", "probe"}
            for descendant in ast.walk(node)
        )
        for node in ast.walk(read_pass)
    )
    assert not any(
        isinstance(node, ast.Return)
        and any(
            isinstance(descendant, ast.Name)
            and descendant.id in {"chunk", "probe"}
            for descendant in ast.walk(node)
        )
        for node in ast.walk(read_pass)
    )
    source = Path(observer.__file__).read_text(encoding="utf-8")
    assert "O_RDONLY" in source
    assert "O_BINARY" in source
    assert "O_NOFOLLOW" in source
    for token in ("O_CREAT", "O_WRONLY", "O_RDWR", "O_APPEND", "O_TRUNC"):
        assert token not in source


def test_uprime_local_artifact_observer_read_only_call_creates_no_files(tmp_path: Path) -> None:
    root = (tmp_path / "never-created").absolute()
    before = tuple(tmp_path.rglob("*"))
    result = observer.observe_local_rpc_artifact_set_v1_0(str(root), _receipt_record())
    after = tuple(tmp_path.rglob("*"))
    assert result.state_vector == ("absent", "absent", "absent")
    assert after == before


def test_uprime_local_artifact_observer_production_capabilities_exposure_and_runs_are_unreached(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lean_rgc.evals import uprime_rpc_bundle_reservation as reservation
    from lean_rgc.evals import uprime_rpc_contract_oracle as contract_oracle
    from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics
    from lean_rgc.evals import uprime_rpc_litmus as litmus
    from lean_rgc.evals import uprime_rpc_seed_inventory as seed_inventory

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
    monkeypatch.setattr(
        manifest,
        "inspect_local_attempt_manifest_chain_v1_0",
        forbidden,
    )
    monkeypatch.setattr(
        seed_inventory,
        "audit_synthetic_seed_local_inventory_v1_0",
        forbidden,
    )
    monkeypatch.setattr(ledger, "parse_canonical_json_bytes", forbidden)

    root = (tmp_path / "production-unreached").absolute()
    result = observer.observe_local_rpc_artifact_set_v1_0(
        str(root),
        _receipt_record(),
    )
    assert result.parent_namespace_state == "absent"
    assert result.parent_reason_codes == ("stable_parent_absence",)
    assert result.state_vector == ("absent", "absent", "absent")
    assert calls == []
    assert not root.exists()
    assert _tree_metadata_snapshot(runs_root) == before_runs
    assert _exposure_marker_paths() == before_markers == ()


def test_uprime_local_artifact_observer_default_deny_registry_is_still_head_bound() -> None:
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
    committed = subprocess.run(
        ["git", "cat-file", "-p", expected_blob],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    assert committed == expected
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", path.as_posix()],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_uprime_local_artifact_observer_support_all_exports_each_test_once() -> None:
    expected = sorted(
        name
        for name, value in globals().items()
        if name.startswith("test_uprime_local_artifact_observer_")
        and inspect.isfunction(value)
        and value.__module__ == __name__
    )
    assert __all__ == expected
    assert len(__all__) == len(set(__all__))


__all__ = sorted(
    name
    for name, value in globals().items()
    if name.startswith("test_uprime_local_artifact_observer_")
    and inspect.isfunction(value)
    and value.__module__ == __name__
)
