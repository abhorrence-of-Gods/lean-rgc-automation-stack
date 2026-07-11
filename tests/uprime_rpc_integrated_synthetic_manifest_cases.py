"""Frozen Phase-2b2f integrated synthetic-manifest acceptance cases.

Only the 64 functions listed in :data:`__all__` are imported by the ledger
collector.  Every filesystem fixture is synthetic and lives below pytest's
``tmp_path``.  No test invokes a registered run, Lean, a worker, a network
endpoint, or a GPU.
"""

from __future__ import annotations

import ast
import copy
import ctypes
from dataclasses import FrozenInstanceError, dataclass, fields, replace
import hashlib
import inspect
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
from typing import Any, get_type_hints

import pytest

from lean_rgc.evals import uprime_rpc_attempt_manifest as manifest
from lean_rgc.evals import uprime_rpc_fake_cas_kernel as cas
from lean_rgc.evals import uprime_rpc_integrated_synthetic_manifest as integrated
from lean_rgc.evals import uprime_rpc_ledger as ledger
from lean_rgc.evals import uprime_rpc_litmus as litmus
from lean_rgc.evals import uprime_rpc_local_artifact_observer as artifacts
from lean_rgc.evals import uprime_rpc_local_staging_fake_publisher as publisher
from lean_rgc.evals import uprime_rpc_seed_inventory as inventory
from lean_rgc.evals import uprime_rpc_synthetic_recovery_coordinator as recovery


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py"
SUPPORT_PATH = ROOT / "tests/uprime_rpc_integrated_synthetic_manifest_cases.py"
COLLECTOR_PATH = ROOT / "tests/test_uprime_rpc_ledger.py"
PREREG_PATH = ROOT / (
    "docs/experiments/"
    "uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_"
    "integrated_synthetic_manifest_recovery_audit_amendment_2026-07-11.md"
)
PREREG_COMMIT = "8f1c0ba42b9c8568e802b79ee8bfc55ac3459a75"
PREREG_BLOB = "c72d18a17411071f1d1511581978d1b6792761e6"
MAX_PAYLOAD_BYTES = 1_048_576

PUBLIC_ALL = [
    "IntegratedSyntheticManifestV10Error",
    "SyntheticManifestResidueObservationV10",
    "SyntheticCoordinatorActionTraceV10",
    "SyntheticTerminalManifestAppendV10",
    "SyntheticConflictWithoutMarkerAuditV10",
    "IntegratedSyntheticRecoveryManifestAuditV10",
    "audit_synthetic_conflict_without_marker_v1_0",
    "append_integrated_synthetic_recovery_manifest_v1_0",
]

RESIDUE_FIELDS = (
    "observation_schema_version", "observation_scope", "origin_status",
    "observation_phase", "staging_parent", "collision_nonce",
    "stage_basename", "stage_path", "expected_payload_bytes",
    "expected_payload_sha256", "parent_namespace_state",
    "parent_reason_codes", "observation_state", "reason_codes",
    "observed_payload_bytes", "observed_payload_sha256", "payload_relation",
    "observation_sha256", "payload_byte_limit",
    "staging_parent_utf8_byte_limit", "stage_path_utf8_byte_limit",
    "io_chunk_bytes", "read_call_upper_bound", "payload_work_upper_bound_bytes",
    "peak_buffer_upper_bound_bytes", "retained_payload_copy_upper_bound_bytes",
    "path_derivation_scope", "nofollow_scope", "ancestor_reparse_check_scope",
    "backing_store_scope", "snapshot_scope", "stage_attribution_scope",
    "cleanup_scope", "authority_scope", "canonical_remote_authority",
    "licenses_execution", "licenses_publication", "licenses_recovery",
    "licenses_later_stage",
)
TRACE_FIELDS = (
    "trace_schema_version", "trace_scope", "origin_status", "operation",
    "outcome", "reason_codes", "action_sha256", "before_snapshot_sha256",
    "after_snapshot_sha256", "endpoint_state_changed",
    "publisher_operation_sha256", "publisher_transition_sha256",
    "marker_sha256", "epoch_ordinal", "replay_observation", "terminal_sha256",
    "witness_purpose", "detached_record_scope", "authority_scope",
    "licenses_execution", "licenses_publication", "licenses_recovery",
    "licenses_later_stage",
)
APPEND_FIELDS = (
    "append_schema_version", "append_scope", "origin_status", "license_id",
    "publisher_collision_nonce", "manifest_nonce", "repository_path",
    "host_final_path", "host_alias_path", "event_sha256", "event_bytes",
    "append_status", "write_call_count", "read_call_count", "file_create_count",
    "hardlink_create_count", "retained_path_alias_count", "append_sha256",
    "event_byte_limit", "host_path_utf8_byte_limit", "io_chunk_bytes",
    "write_call_upper_bound", "read_call_upper_bound", "file_create_upper_bound",
    "hardlink_create_upper_bound", "retained_path_alias_upper_bound",
    "payload_work_upper_bound_bytes", "peak_buffer_upper_bound_bytes",
    "writer_scope", "hardlink_scope", "alias_retention_scope",
    "durability_scope", "cleanup_scope", "authority_scope",
    "canonical_remote_authority", "licenses_execution", "licenses_publication",
    "licenses_recovery", "licenses_later_stage",
)
CONFLICT_FIELDS = (
    "audit_schema_version", "audit_scope", "origin_status", "outcome",
    "reason_codes", "root", "seed_file_sha256", "seed_identity_sha256",
    "license_id", "claim_receipt_sha256", "constructor_profile",
    "publisher_collision_nonce", "staging_parent", "stage_basename", "stage_path",
    "proposed_payload_bytes", "proposed_payload_sha256",
    "alternate_payload_bytes", "alternate_payload_sha256",
    "initial_state_version_sha256", "conflict_expected_state_version_sha256",
    "initial_inventory_projection_sha256", "active_chain_projection_sha256",
    "pre_stage_observation", "action_trace", "final_snapshot_sha256",
    "final_lifecycle_state", "artifact_projection_sha256",
    "post_stage_observation", "final_inventory_projection_sha256",
    "cas_binding_sha256", "audit_sha256", "manifest_event_delta",
    "conflict_without_marker_status", "stage_residue_classification",
    "same_call_binding_scope", "persistent_cross_binding", "artifact_scope",
    "inventory_scope", "detached_record_scope", "stage_residue_scope",
    "root_scope", "ancestor_link_containment", "basename_spelling_verification",
    "hostile_concurrent_reparse_prevention", "backing_store_scope",
    "durability_scope", "cleanup_scope", "remote_publication",
    "max_inventory_audits", "max_artifact_observations", "max_stage_observations",
    "aggregate_dependency_payload_work_upper_bound_bytes",
    "canonical_remote_authority", "licenses_execution", "licenses_publication",
    "licenses_recovery", "licenses_later_stage",
)
RECOVERY_FIELDS = (
    "audit_schema_version", "audit_scope", "origin_status", "outcome",
    "reason_codes", "root", "seed_file_sha256", "seed_identity_sha256",
    "license_id", "claim_receipt_sha256", "constructor_profile",
    "publisher_collision_nonce", "manifest_nonce", "staging_parent",
    "stage_basename", "stage_path", "manifest_repository_path",
    "manifest_host_final_path", "manifest_host_alias_path",
    "proposed_payload_bytes", "proposed_payload_sha256",
    "alternate_payload_bytes", "alternate_payload_sha256",
    "initial_state_version_sha256", "expected_state_version_sha256",
    "initial_inventory_projection_sha256", "active_chain_projection_sha256",
    "pre_stage_observation", "action_trace", "action_count", "marker",
    "witness_purpose", "witness_sha256", "preconsume_snapshot_sha256",
    "preconsume_lifecycle_state", "preappend_artifact_projection_sha256",
    "preappend_stage_observation", "terminal_event_sha256", "manifest_append",
    "terminal_attestation_projection_sha256",
    "postappend_artifact_projection_sha256", "postappend_stage_observation",
    "final_inventory_projection_sha256", "final_snapshot_sha256",
    "final_lifecycle_state", "cas_binding_sha256", "manifest_binding_sha256",
    "audit_sha256", "failure_code_binding", "stage_residue_classification",
    "phase2b1_event_binding", "publisher_operation_binding",
    "marker_plan_binding", "artifact_scope", "inventory_scope",
    "same_call_binding_scope", "persistent_cross_binding",
    "manifest_witness_atomicity", "timestamp_scope", "detached_record_scope",
    "stage_residue_scope", "manifest_alias_scope", "root_scope",
    "ancestor_link_containment", "basename_spelling_verification",
    "hostile_concurrent_reparse_prevention", "backing_store_scope",
    "durability_scope", "cleanup_scope", "remote_publication",
    "real_recovery_scope", "execution_scope", "max_seed_claims",
    "max_chain_events", "max_coordinator_actions", "max_recovery_epochs",
    "max_artifact_observations", "max_stage_observations",
    "max_inventory_audits", "max_manifest_appends",
    "aggregate_dependency_payload_work_upper_bound_bytes",
    "coordinator_payload_reference_upper_bound_bytes",
    "proposal_payload_copy_upper_bound_bytes", "canonical_remote_authority",
    "licenses_execution", "licenses_publication", "licenses_recovery",
    "licenses_later_stage",
)

CASE_MATRIX = (
    ("s01_public_surface", "exact ordered production surface", "extra_missing_or_reordered_export", "surface_exact", "none"),
    ("s02_positional_signatures", "two exact positional_only signatures", "caller_control_parameter_added", "signature_exact", "none"),
    ("s03_record_arities", "ordered fields 39_23_39_58_88", "field_added_removed_or_reordered", "arity_exact", "none"),
    ("s04_constructor_type_domains", "exact types nullable domains bool_not_int", "coercion_or_subclass_accepted", "typed_rejection", "none"),
    ("s05_false_authority_cells", "all authority and license booleans false", "authority_flag_upgraded", "constructor_rejection", "none"),
    ("s06_constructor_zero_io", "record constructors are pure", "constructor_stats_or_calls_dependency", "pure_construction", "none"),
    ("s07_import_allowlist", "only exact public symbol allowlist", "private_or_publisher_symbol_imported", "ast_rejection", "none"),
    ("s08_prereg_tree_absence_and_anchor", "prereg tree lacks future files and anchor occurs once", "implementation_preplayed_or_anchor_duplicated", "git_tree_gate_pass", "read_only"),
    ("p01_root_exact_utf8", "root exact normalized strict_utf8 absolute", "coerced_surrogate_or_relative_root", "preflight_rejection", "none"),
    ("p02_windows_path_grammar", "drive_root and no UNC_device_current_drive", "unsafe_windows_spelling_accepted", "preflight_rejection", "none"),
    ("p03_derived_path_bounds", "each early and late path checks own bound", "root_limit_substituted_for_derived_limit", "preflight_or_precreate_rejection", "none"),
    ("p04_parent_type_and_same_device", "attempt and staging parents real nonreparse same_device", "cross_device_or_reparse_parent_accepted", "preflight_rejection", "read_only"),
    ("p05_profile_alternate_matrix", "four profiles and wrong_delta alternate only", "normal_or_bad_alternate_accepted", "preflight_rejection", "none"),
    ("p06_payload_boundaries", "proposal and alternate inclusive 1MiB bounds", "oversize_or_nonbytes_payload_accepted", "preflight_rejection", "none"),
    ("p07_nonce_and_path_derivation", "nonces and paths use frozen inputs once", "caller_nonce_or_unbound_path_used", "derivation_exact", "none"),
    ("p08_no_caller_records_or_handles", "caller cannot supply receipt_state_action_marker_witness", "authority_parameter_added", "signature_rejection", "none"),
    ("h01_domain_lengths", "twelve exact NUL domains and lengths", "domain_swap_or_missing_NUL", "golden_match", "none"),
    ("h02_nonce_goldens", "publisher and manifest nonce formulas", "tag_length_order_or_case_mutated", "golden_match", "none"),
    ("h03_residue_golden", "residue projection exact order", "observation_cell_omitted_or_swapped", "golden_match", "none"),
    ("h04_inventory_chain_goldens", "one_claim inventory and chain projections", "claim_or_timestamp_cell_unbound", "golden_match", "none"),
    ("h05_artifact_terminal_goldens", "AAA artifact and terminal projections", "row_order_or_failure_tuple_unbound", "golden_match", "none"),
    ("h06_append_and_cas_goldens", "append plus conflict_recovery CAS domains", "endpoint_kind_or_path_count_unbound", "golden_match", "none"),
    ("h07_conflict_audit_golden", "conflict top_level dynamic order", "trace_or_stage_endpoint_omitted", "golden_match", "none"),
    ("h08_binding_recovery_goldens", "manifest binding and recovery audit order", "preappend_stage_or_consume_trace_omitted", "golden_match", "none"),
    ("i01_exact_one_seed_receipt", "seed parses canonically with one receipt", "zero_multiple_or_detached_receipt_accepted", "preflight_rejection", "read_only"),
    ("i02_active_inventory_endpoint", "exact one active nonterminal aggregate", "matched_terminal_required_prewrite", "active_endpoint_accept", "read_only"),
    ("i03_invalid_namespace_preflight", "orphan_unexpected_mismatch_drift reject", "invalid_namespace_reaches_mutation", "preflight_rejection", "read_only"),
    ("i04_exact_index1_chain", "sole canonical claim_started index1", "terminal_multi_event_or_bad_prior_accepted", "preflight_rejection", "read_only"),
    ("i05_stage_stable_absence", "prepublish and conflict rows stable absent", "one_point_absence_called_stable", "observation_rejection", "read_only"),
    ("i06_stage_stable_exact_payload", "two passes raw_equal and stable metadata", "digest_only_or_one_pass_acceptance", "exact_present_observation", "read_only"),
    ("i07_stage_indeterminate_and_raw_equality", "seek_read_eof_drift reasons fail_closed", "same_digest_distinct_bytes_or_drift_accepted", "indeterminate_or_different", "read_only"),
    ("i08_artifact_all_absent_only", "only exact AAA vector is write_admissible", "present_or_indeterminate_mapped_false", "append_gate_rejection", "read_only"),
    ("c01_conflict_exact_endpoint", "stale_expected gives exact conflict action", "conflict_relabelled_collision_or_poison", "conflict_audit_return", "read_only"),
    ("c02_conflict_physical_zero_write", "conflict reaches no stage or manifest writer", "physical_write_on_conflict", "conflict_audit_return", "stage_absent_manifest_absent"),
    ("c03_conflict_projection_binding", "result operation_transition and OPEN bind", "publisher_result_hashes_dropped", "binding_exact", "read_only"),
    ("c04_ack_loss_confirmed_trace", "exact publish_acquire_confirm_consume trace", "trace_row_skipped_or_reordered", "four_actions_exact", "stage_and_manifest_retained"),
    ("c05_unavailable_then_confirmed_trace", "exact two_epoch confirmation trace", "unavailable_cursor_or_ordinal_mutated", "six_actions_exact", "stage_and_manifest_retained"),
    ("c06_unavailable_budget_trace", "four unavailable epochs then block consume", "fifth_epoch_or_recovered_upgrade", "ten_actions_exact", "stage_and_manifest_retained"),
    ("c07_wrong_delta_trace", "confirmed wrong_delta yields block witness", "wrong_delta_called_recovered", "four_actions_exact", "stage_and_manifest_retained"),
    ("c08_snapshot_continuity_and_terminal_purpose", "adjacent snapshots and purposes chain", "detached_noncontiguous_trace_accepted", "continuity_exact", "none"),
    ("m01_terminal_event_mapping", "exact index2 recovery mapping", "code_timestamp_receipt_or_prior_relabelled", "event_exact", "none"),
    ("m02_canonical_encode_parse_lf", "public encoder parser and LF inclusive hash", "manual_JSON_or_LF_omitted", "canonical_roundtrip", "none"),
    ("m03_temp_exclusive_partial_writes", "O_EXCL mode600 positive bounded writes", "overwrite_or_zero_write_accepted", "append_progress_or_error", "alias_may_remain"),
    ("m04_readback_seek_eof", "seek0 exact chunks raw readback EOF", "short_read_growth_or_no_seek_accepted", "append_progress_or_error", "alias_may_remain"),
    ("m05_alias_close_and_identity", "close then nofollow alias identity", "close_error_or_alias_swap_ignored", "append_progress_or_error", "alias_may_remain"),
    ("m06_final_hardlink_endpoint", "one nooverwrite link and postlink comparator", "rename_copy_or_full_ctime_equality_used", "append_exact", "two_aliases_retained"),
    ("m07_preplay_and_concurrent_collision", "existing_or_concurrent final never adopted", "exact_preplay_adopted_or_overwritten", "hard_failure", "no_cleanup_no_consume"),
    ("m08_terminal_attestation_inventory", "verifier and final matched_terminal bind event2", "favorable_partial_endpoint_accepted", "terminal_endpoint_exact", "two_aliases_retained"),
    ("w01_witness_order_last_mutation", "consume follows every read and mutation", "consume_moved_before_endpoint", "ordered_success", "witness_spent_last"),
    ("w02_foreign_and_copied_witness", "only internal same_instance handle consumed", "hash_equal_foreign_witness_consumed", "hard_failure", "no_consume"),
    ("w03_block_is_not_success", "permanent_block purpose never recovered", "block_witness_upgraded", "block_record_only", "no_success_authority"),
    ("w04_precreate_failure_cuts", "failure before alias create appends nothing", "precreate_failure_retried_or_appended", "mapped_error", "stage_may_remain"),
    ("w05_temp_residue_failure_cuts", "temp failures retain residue without cleanup", "partial_alias_deleted_or_adopted", "mapped_error", "alias_may_remain_no_consume"),
    ("w06_link_perform_then_raise_cut", "link invoked unconfirmed never upgrades", "perform_then_raise_called_success", "mapped_error", "final_may_remain_no_consume"),
    ("w07_postlink_preconsume_cuts", "postlink verification failure does not consume", "terminal_or_inventory_failure_consumes", "mapped_error", "final_and_alias_may_remain"),
    ("w08_postconsume_construction_cut", "postconsume pure failure exposes no retry claim", "spent_witness_rolled_back_or_retry_enabled", "mapped_error", "final_retained_witness_spent"),
    ("g01_sanitized_errors_and_baseexception", "ordinary errors sanitized and BaseException identity kept", "same_class_secret_leak_or_primary_masked", "exact_error_policy", "no_cleanup"),
    ("g02_aggregate_resource_arithmetic", "exact 979369992 and 1423966222 aggregate bounds", "hidden_extra_call_or_off_by_one", "arithmetic_exact", "none"),
    ("g03_payload_reference_and_copy_scope", "coordinator refs 3MiB proposal copies zero", "global_memory_claim_or_payload_copy", "scope_exact", "none"),
    ("g04_no_cleanup_fsync_or_retry", "no unlink_rename_replace_fsync_retry", "destructive_or_durability_call", "ast_runtime_rejection", "residue_retained"),
    ("g05_forbidden_capability_sentinels", "no network_git_lean_worker_registry_gpu", "forbidden_import_or_call", "ast_runtime_rejection", "none"),
    ("g06_tmp_only_and_repo_unchanged", "fixtures only below tmp and protected trees identical", "repository_artifact_or_registry_write", "tree_gate_pass", "repo_unchanged"),
    ("g07_windows_real_filesystem_profiles", "all four profiles and conflict on Windows temp fs", "platform_skip_or_fake_only_evidence", "zero_skip_pass", "tmp_residue_only"),
    ("g08_gate_ancestry_allowed_diff_and_stop_rule", "exact parent_blobs_diff_CI_head_and_Phase2c_only", "retroactive_prereg_or_extra_diff_or_wrong_CI_head", "governance_gate_pass", "no_later_authority"),
)

PHASE2B2F_CASE_IDS = tuple(row[0] for row in CASE_MATRIX)


@dataclass(frozen=True)
class _Fixture:
    root: Path
    seed_raw: bytes
    receipt: dict[str, Any]
    claim_raw: bytes
    proposal: bytes
    alternate: bytes
    attempt_dir: Path
    staging_parent: Path


def _receipt_mapping(candidate_commit: str = "a" * 40) -> dict[str, Any]:
    license_id = hashlib.sha256(
        b"lean-rgc-uprime-u1-attempt-v1\0" + candidate_commit.encode("ascii")
    ).hexdigest()
    license_commit = "b" * 40
    return {
        "schema_version": "lean-rgc-uprime-u1-claim-receipt-public-v1.0",
        "candidate_commit": candidate_commit,
        "license_commit": license_commit,
        "license_id": license_id,
        "remote_url": "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git",
        "remote_branch_ref": "refs/heads/codex/uprime-odlrq-plan",
        "remote_claim_ref": f"refs/tags/uprime-u1-attempts/{license_id}",
        "remote_claim_oid": license_commit,
        "registry_blob_oid": "c" * 40,
        "registry_sha256": "D" * 64,
        "candidate_tree_oid": "e" * 40,
        "input_manifest_sha256": "F" * 64,
        "claimed_at_utc": "2026-07-11T00:00:00.000000Z",
    }


def _receipt_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(ledger.canonical_json_bytes(value)).hexdigest().upper()


def _claim_mapping(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lean-rgc-uprime-u1-attempt-manifest-v1.0",
        "event_type": "claim_started",
        "event_index": 1,
        "created_at_utc": "2026-07-11T00:00:00.000000Z",
        "license_id": receipt["license_id"],
        "candidate_commit": receipt["candidate_commit"],
        "license_commit": receipt["license_commit"],
        "remote_claim_ref": receipt["remote_claim_ref"],
        "claim_receipt": copy.deepcopy(receipt),
        "claim_receipt_sha256": _receipt_sha256(receipt),
        "prior_event_sha256": None,
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
        "verdict": None,
        "failure_codes": [],
        "full_ledger_published": False,
        "terminal_event": False,
    }


def _seed_raw(receipts: list[dict[str, Any]]) -> bytes:
    mapping = {
        "schema_version": "lean-rgc-uprime-u1-synthetic-claim-seed-v1.0",
        "seed_scope": "caller_supplied_synthetic_claims_only",
        "claim_receipts": sorted(copy.deepcopy(receipts), key=lambda row: row["license_id"]),
    }
    return ledger.canonical_json_bytes(mapping) + b"\n"


def _short_windows_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    buffer = ctypes.create_unicode_buffer(32_768)
    function = ctypes.windll.kernel32.GetShortPathNameW  # type: ignore[attr-defined]
    function.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    function.restype = ctypes.c_uint32
    length = function(str(path), buffer, len(buffer))
    assert 0 < length < len(buffer)
    result = Path(buffer.value)
    assert result.is_absolute() and result.exists()
    return result


def _fixture(tmp_path: Path, name: str = "case") -> _Fixture:
    short_tmp_path = _short_windows_path(tmp_path.absolute())
    safe_name = name
    if len(safe_name.encode("utf-8")) > 12:
        safe_name = "f-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    physical_root = short_tmp_path / safe_name
    physical_root.mkdir()
    root = _short_windows_path(physical_root)
    receipt = _receipt_mapping()
    claim = _claim_mapping(receipt)
    claim_raw = ledger.canonical_json_bytes(claim) + b"\n"
    attempt_dir = (
        root / "docs" / "experiments" / "artifacts" /
        "uprime_u1_rpc_attempts" / receipt["license_id"]
    )
    staging_parent = (
        root / "docs" / "experiments" / "artifacts" /
        "uprime_u1_rpc_staging" / receipt["license_id"]
    )
    attempt_dir.mkdir(parents=True)
    staging_parent.mkdir(parents=True)
    (attempt_dir / "0001.json").write_bytes(claim_raw)
    return _Fixture(
        root=root,
        seed_raw=_seed_raw([receipt]),
        receipt=receipt,
        claim_raw=claim_raw,
        proposal=b"phase2b2f-proposal",
        alternate=b"phase2b2f-alternate",
        attempt_dir=attempt_dir,
        staging_parent=staging_parent,
    )


def _conflict(fixture: _Fixture, profile: str = "ack_loss_confirmed") -> Any:
    return integrated.audit_synthetic_conflict_without_marker_v1_0(
        str(fixture.root), fixture.seed_raw, profile, None, fixture.proposal
    )


def _recover(fixture: _Fixture, profile: str = "ack_loss_confirmed") -> Any:
    alternate = fixture.alternate if profile == "wrong_delta_confirmed" else None
    return integrated.append_integrated_synthetic_recovery_manifest_v1_0(
        str(fixture.root), fixture.seed_raw, profile, alternate, fixture.proposal
    )


def _values(value: object) -> tuple[object, ...]:
    return tuple(getattr(value, item.name) for item in fields(value))


def _coherent_recovery_replace(value: object, **changes: object) -> object:
    values = {item.name: getattr(value, item.name) for item in fields(value)}
    values.update(changes)
    values["manifest_binding_sha256"] = integrated._manifest_binding_sha256(  # type: ignore[attr-defined]
        SimpleNamespace(**values)
    )
    values["audit_sha256"] = integrated._recovery_audit_sha256(  # type: ignore[attr-defined]
        SimpleNamespace(**values)
    )
    return integrated.IntegratedSyntheticRecoveryManifestAuditV10(**values)


def _coherent_append_replace(value: object, **changes: object) -> object:
    values = {item.name: getattr(value, item.name) for item in fields(value)}
    values.update(changes)
    values["append_sha256"] = integrated._append_sha256(  # type: ignore[attr-defined]
        SimpleNamespace(**values)
    )
    return integrated.SyntheticTerminalManifestAppendV10(**values)


def _assert_no_authority(value: object) -> None:
    if hasattr(value, "authority_scope"):
        assert value.authority_scope == "none"
    if hasattr(value, "canonical_remote_authority"):
        assert value.canonical_remote_authority is False
    assert value.licenses_execution is False
    assert value.licenses_publication is False
    assert value.licenses_recovery is False
    assert value.licenses_later_stage is False


def _expect_error(callable_: Any, message: str | None = None) -> integrated.IntegratedSyntheticManifestV10Error:
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error) as caught:
        callable_()
    assert caught.value.__cause__ is None
    if message is not None:
        assert str(caught.value) == message
    return caught.value


def _source_tree() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))


def _path_entry_payload(path: Path) -> bytes:
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return b"symlink\0" + os.fsencode(os.readlink(path))
    if stat.S_ISREG(mode):
        return b"regular\0" + hashlib.sha256(path.read_bytes()).digest()
    if stat.S_ISDIR(mode):
        return b"directory\0"
    return b"other\0" + stat.S_IFMT(mode).to_bytes(8, "big")


def _repo_tree_digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for base in paths:
        rel = base.relative_to(ROOT).as_posix().encode("utf-8")
        if not os.path.lexists(base):
            digest.update(rel + b"\0missing\0")
            continue
        digest.update(rel + b"\0" + _path_entry_payload(base))
        if not stat.S_ISDIR(os.lstat(base).st_mode):
            continue
        for item in sorted(base.rglob("*"), key=lambda p: str(p)):
            rel = item.relative_to(ROOT).as_posix().encode("utf-8")
            digest.update(rel + b"\0" + _path_entry_payload(item))
    return digest.hexdigest()


def _exposure_marker_inventory(paths: tuple[Path, ...]) -> tuple[tuple[str, str], ...]:
    tokens = ("exposure", "burn", "retir", "read_ledger")
    rows: list[tuple[str, str]] = []
    for base in paths:
        if not os.path.lexists(base):
            continue
        base_is_directory = stat.S_ISDIR(os.lstat(base).st_mode)
        candidates = (base, *tuple(base.rglob("*"))) if base_is_directory else (base,)
        for item in candidates:
            relative = item.relative_to(ROOT).as_posix()
            if any(token in relative.lower() for token in tokens):
                fingerprint = hashlib.sha256(_path_entry_payload(item)).hexdigest()
                rows.append((relative, fingerprint))
    return tuple(sorted(rows))


def _u8(value: int) -> bytes:
    return bytes((value,))


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _k(value: str) -> bytes:
    raw = value.encode("ascii")
    return _u16(len(raw)) + raw


def _p(value: str) -> bytes:
    raw = value.encode("utf-8", errors="strict")
    return _u32(len(raw)) + raw


def _h(value: str) -> bytes:
    return bytes.fromhex(value)


def _l(value: str) -> bytes:
    return bytes.fromhex(value)


def _n(value: str) -> bytes:
    return bytes.fromhex(value)


def _q(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _h(value)


def _j(value: int | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _u64(value)


def _s(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + _k(value)


def _t(values: tuple[str, ...]) -> bytes:
    return _u16(len(values)) + b"".join(_k(value) for value in values)


def _b(value: bool) -> bytes:
    return _u8(1 if value else 0)


def _z(value: bool | None) -> bytes:
    return _u8(0 if value is None else (2 if value else 1))


def _digest(domain: bytes, *parts: bytes) -> str:
    return hashlib.sha256(domain + b"".join(parts)).hexdigest().upper()


DOMAINS = (
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-publisher-nonce-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-manifest-nonce-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-residue-observation-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-inventory-projection-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-active-chain-projection-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-artifact-projection-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-attestation-projection-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-append-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-cas-binding-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-conflict-audit-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-binding-v1\0",
    b"lean-rgc-uprime-u1-integrated-synthetic-manifest-recovery-audit-v1\0",
)
(
    D_PUBLISHER_NONCE, D_MANIFEST_NONCE, D_RESIDUE, D_INVENTORY,
    D_ACTIVE_CHAIN, D_ARTIFACT, D_TERMINAL_ATTESTATION, D_APPEND, D_CAS,
    D_CONFLICT, D_MANIFEST_BINDING, D_RECOVERY,
) = DOMAINS


def _publisher_nonce(seed_identity: str, profile: str, proposed: bytes, alternate: bytes | None) -> tuple[str, str]:
    digest = _digest(
        D_PUBLISHER_NONCE,
        _h(seed_identity), _k(profile), _u64(len(proposed)),
        _h(hashlib.sha256(proposed).hexdigest().upper()),
        _j(None if alternate is None else len(alternate)),
        _q(None if alternate is None else hashlib.sha256(alternate).hexdigest().upper()),
    )
    return digest[:32].lower(), digest


def _manifest_nonce(event_sha: str, marker_sha: str, terminal_sha: str) -> tuple[str, str]:
    digest = _digest(D_MANIFEST_NONCE, _h(event_sha), _h(marker_sha), _h(terminal_sha))
    return digest[:32].lower(), digest


def _residue_digest(row: Any) -> str:
    return _digest(
        D_RESIDUE,
        _k(row.observation_phase), _p(row.staging_parent), _n(row.collision_nonce),
        _k(row.stage_basename), _p(row.stage_path), _u64(row.expected_payload_bytes),
        _h(row.expected_payload_sha256), _k(row.parent_namespace_state),
        _t(row.parent_reason_codes), _k(row.observation_state), _t(row.reason_codes),
        _j(row.observed_payload_bytes), _q(row.observed_payload_sha256),
        _k(row.payload_relation),
    )


def _inventory_digest(row: Any) -> str:
    assert len(row.claim_audits) == 1
    claim = row.claim_audits[0]
    return _digest(
        D_INVENTORY,
        _h(row.seed_file_sha256), _h(row.seed_identity_sha256),
        _k(row.base_directory_status), _u64(row.seed_count),
        _u64(row.local_directory_count), _u64(row.union_claim_count),
        _u64(row.examined_claim_count), _u64(row.total_observed_event_bytes),
        _u64(row.unexpected_entry_count), _k(row.coverage_status),
        _b(row.set_equality), _b(row.all_seeded_local_present),
        _b(row.all_seeded_terminal), _b(row.all_seeded_receipts_match), _u16(1),
        _l(claim.license_id), _b(claim.seed_membership),
        _b(claim.local_membership), _k(claim.set_relation),
        _k(claim.receipt_relation), _q(claim.seed_receipt_sha256),
        _q(claim.local_receipt_sha256), _k(claim.chain_observation),
        _j(claim.event_count), _j(claim.last_event_index),
        _q(claim.last_event_sha256), _z(claim.terminal_event),
        _s(claim.recorded_verdict),
    )


def _active_chain_digest(inspection: Any) -> str:
    event_file = inspection.event_files[0]
    return _digest(
        D_ACTIVE_CHAIN,
        _l(inspection.license_id), _h(inspection.claim_receipt_sha256),
        _h(inspection.first_event_sha256), _h(inspection.last_event_sha256),
        _u64(len(event_file.event_bytes)), _u64(inspection.event_count),
        _u64(inspection.last_event_index), _k(inspection.last_event_type),
        _b(inspection.terminal_event), _j(inspection.next_event_index),
        _k(event_file.event.created_at_utc),
    )


def _artifact_digest(row: Any) -> str:
    parts = [
        _h(row.claim_receipt_sha256), _k(row.parent_namespace_state),
        _t(row.parent_reason_codes), _u16(3),
    ]
    for item in (row.reservation, row.ledger, row.report):
        parts.extend((
            _k(item.artifact_kind), _p(item.repository_path),
            _k(item.observation_state), _t(item.reason_codes),
            _q(item.artifact_sha256), _j(item.artifact_bytes), _u64(item.byte_limit),
        ))
    parts.extend((
        _u64(row.present_count), _u64(row.absent_count),
        _u64(row.indeterminate_count), _u64(row.total_present_bytes),
        _k(row.snapshot_scope),
    ))
    return _digest(D_ARTIFACT, *parts)


def _terminal_attestation_digest(row: Any) -> str:
    return _digest(
        D_TERMINAL_ATTESTATION,
        _l(row.license_id), _h(row.claim_receipt_sha256), _u64(row.event_count),
        _h(row.first_event_sha256), _u64(row.last_event_index),
        _h(row.last_event_sha256), _k(row.chain_state), _b(row.terminal_event),
        _k(row.last_event_type), _s(row.recorded_verdict), _t(row.failure_codes),
    )


def _trace_bytes(row: Any) -> bytes:
    return b"".join((
        _k(row.operation), _k(row.outcome), _t(row.reason_codes),
        _h(row.action_sha256), _h(row.before_snapshot_sha256),
        _h(row.after_snapshot_sha256), _b(row.endpoint_state_changed),
        _q(row.publisher_operation_sha256), _q(row.publisher_transition_sha256),
        _q(row.marker_sha256), _j(row.epoch_ordinal), _s(row.replay_observation),
        _q(row.terminal_sha256), _s(row.witness_purpose),
    ))


def _append_digest(row: Any) -> str:
    return _digest(
        D_APPEND,
        _l(row.license_id), _n(row.publisher_collision_nonce), _n(row.manifest_nonce),
        _p(row.repository_path), _p(row.host_final_path), _p(row.host_alias_path),
        _h(row.event_sha256), _u64(row.event_bytes), _k(row.append_status),
        _u64(row.write_call_count), _u64(row.read_call_count),
        _u64(row.file_create_count), _u64(row.hardlink_create_count),
        _u64(row.retained_path_alias_count),
    )


def _cas_digest(row: Any, *, conflict: bool) -> str:
    trace = row.action_trace if conflict else row.action_trace[0]
    marker = None if conflict else row.marker
    return _digest(
        D_CAS,
        _k("conflict" if conflict else "recovery"),
        _h(row.initial_state_version_sha256),
        _h(row.conflict_expected_state_version_sha256 if conflict else row.expected_state_version_sha256),
        _u64(row.proposed_payload_bytes), _h(row.proposed_payload_sha256),
        _j(row.alternate_payload_bytes), _q(row.alternate_payload_sha256),
        _q(trace.publisher_operation_sha256 if conflict else marker.publisher_operation_sha256),
        _q(trace.publisher_transition_sha256 if conflict else marker.publisher_transition_sha256),
        _q(None if conflict else marker.synthetic_fault_transition_sha256),
        _q(None if conflict else marker.marker_sha256),
    )


def _conflict_audit_preimage(row: Any) -> bytes:
    return D_CONFLICT + b"".join((
        _k(row.outcome), _t(row.reason_codes), _p(row.root),
        _h(row.seed_file_sha256), _h(row.seed_identity_sha256), _l(row.license_id),
        _h(row.claim_receipt_sha256), _k(row.constructor_profile),
        _n(row.publisher_collision_nonce), _p(row.staging_parent),
        _k(row.stage_basename), _p(row.stage_path),
        _u64(row.proposed_payload_bytes), _h(row.proposed_payload_sha256),
        _j(row.alternate_payload_bytes), _q(row.alternate_payload_sha256),
        _h(row.initial_state_version_sha256), _h(row.conflict_expected_state_version_sha256),
        _h(row.initial_inventory_projection_sha256), _h(row.active_chain_projection_sha256),
        _h(row.pre_stage_observation.observation_sha256), _trace_bytes(row.action_trace),
        _h(row.final_snapshot_sha256), _k(row.final_lifecycle_state),
        _h(row.artifact_projection_sha256),
        _h(row.post_stage_observation.observation_sha256),
        _h(row.final_inventory_projection_sha256), _h(row.cas_binding_sha256),
        _k(row.manifest_event_delta), _k(row.conflict_without_marker_status),
        _k(row.stage_residue_classification),
    ))


def _conflict_audit_digest(row: Any) -> str:
    return hashlib.sha256(_conflict_audit_preimage(row)).hexdigest().upper()


def _manifest_binding_preimage(row: Any) -> bytes:
    return D_MANIFEST_BINDING + b"".join((
        _h(row.active_chain_projection_sha256), _h(row.marker.marker_sha256),
        _h(row.cas_binding_sha256), _h(row.terminal_event_sha256),
        _h(row.manifest_append.append_sha256),
        _h(row.terminal_attestation_projection_sha256),
        _h(row.preappend_artifact_projection_sha256),
        _h(row.pre_stage_observation.observation_sha256),
        _h(row.preappend_stage_observation.observation_sha256),
        _h(row.postappend_artifact_projection_sha256),
        _h(row.postappend_stage_observation.observation_sha256),
        _h(row.final_inventory_projection_sha256), _h(row.preconsume_snapshot_sha256),
        _h(row.final_snapshot_sha256), _u16(row.action_count),
        *(_trace_bytes(trace) for trace in row.action_trace),
    ))


def _manifest_binding_digest(row: Any) -> str:
    return hashlib.sha256(_manifest_binding_preimage(row)).hexdigest().upper()


def _recovery_audit_preimage(row: Any) -> bytes:
    return D_RECOVERY + b"".join((
        _k(row.outcome), _t(row.reason_codes), _p(row.root),
        _h(row.seed_file_sha256), _h(row.seed_identity_sha256), _l(row.license_id),
        _h(row.claim_receipt_sha256), _k(row.constructor_profile),
        _n(row.publisher_collision_nonce), _n(row.manifest_nonce),
        _p(row.staging_parent), _k(row.stage_basename), _p(row.stage_path),
        _p(row.manifest_repository_path), _p(row.manifest_host_final_path),
        _p(row.manifest_host_alias_path), _u64(row.proposed_payload_bytes),
        _h(row.proposed_payload_sha256), _j(row.alternate_payload_bytes),
        _q(row.alternate_payload_sha256), _h(row.initial_state_version_sha256),
        _h(row.expected_state_version_sha256),
        _h(row.initial_inventory_projection_sha256), _h(row.active_chain_projection_sha256),
        _h(row.pre_stage_observation.observation_sha256), _u16(row.action_count),
        *(_trace_bytes(trace) for trace in row.action_trace),
        _h(row.marker.marker_sha256), _k(row.witness_purpose), _h(row.witness_sha256),
        _h(row.preconsume_snapshot_sha256), _k(row.preconsume_lifecycle_state),
        _h(row.preappend_artifact_projection_sha256),
        _h(row.preappend_stage_observation.observation_sha256),
        _h(row.terminal_event_sha256), _h(row.manifest_append.append_sha256),
        _h(row.terminal_attestation_projection_sha256),
        _h(row.postappend_artifact_projection_sha256),
        _h(row.postappend_stage_observation.observation_sha256),
        _h(row.final_inventory_projection_sha256), _h(row.final_snapshot_sha256),
        _k(row.final_lifecycle_state), _h(row.cas_binding_sha256),
        _h(row.manifest_binding_sha256), _k(row.failure_code_binding),
        _k(row.stage_residue_classification),
    ))


def _recovery_audit_digest(row: Any) -> str:
    return hashlib.sha256(_recovery_audit_preimage(row)).hexdigest().upper()


def _rn(number: int) -> str:
    return bytes((number,)).hex().upper() * 32


def _framing_rows() -> tuple[Any, Any, Any]:
    root = "/tmp/uprime-2b2f"
    license_id = "ab" * 32
    publisher_nonce = "fd03ff359d185db3f748e046211c7c4a"
    manifest_nonce = "6a20df3130322cebadcc96df7c9d29c1"
    staging_parent = f"{root}/docs/experiments/artifacts/uprime_u1_rpc_staging/{license_id}"
    stage_basename = f"uprime-rpc-fake-cas-stage-v1-{publisher_nonce}.bin"
    stage_path = f"{staging_parent}/{stage_basename}"
    repository = f"docs/experiments/artifacts/uprime_u1_rpc_attempts/{license_id}/0002.json"
    final_path = f"{root}/{repository}"
    alias_path = f"{staging_parent}/uprime-rpc-attempt-manifest-stage-v1-{manifest_nonce}.json"
    initial = "D475431F78A252741905BD00E75E0E97A30326A91046BF9D4A827D4713BAEBB8"
    proposal_sha = hashlib.sha256(b"B").hexdigest().upper()
    inventory_sha = "1D233C9F36F64366BC2883C199AC7EFE05049B257B124F496A6C5A4CADDC1118"
    chain_sha = "4D8E3C26E565C0E74556E1F8BD9DC385696ABFD050DC5F78918FB78A23EC6B6C"
    artifact_sha = "03B14D6282B1E95BF4E8323AD3936FC5999CDBF63EA3EEC35CBAD23439CFA5F9"
    attestation_sha = "4C1DCEDEA89EB344ED49DD4306EDEE0C43C88F6EBBF0FBDE06FD37531304CC18"
    append_sha = "E3CDCD0A2220488C9023E645EB7B381D0EF058F877F988BAD4149359C3BA01DC"
    residue = SimpleNamespace(observation_sha256=_rn(60))
    residue_fixture = SimpleNamespace(
        observation_sha256="CFA7725FA3B5EE2144129C411207F2E58B25B2EED031EE2FF41A03F16C638009"
    )
    conflict_trace = SimpleNamespace(
        operation="publish", outcome="cas_conflict_no_marker",
        reason_codes=("expected_state_version_mismatch",), action_sha256=_rn(10),
        before_snapshot_sha256=_rn(11), after_snapshot_sha256=_rn(12),
        endpoint_state_changed=False, publisher_operation_sha256=_rn(13),
        publisher_transition_sha256=_rn(14), marker_sha256=None,
        epoch_ordinal=None, replay_observation=None, terminal_sha256=None,
        witness_purpose=None,
    )
    conflict = SimpleNamespace(
        outcome="conflict_without_marker_confirmed",
        reason_codes=("expected_state_version_mismatch",), root=root,
        seed_file_sha256=_rn(1), seed_identity_sha256=_rn(2),
        license_id=license_id, claim_receipt_sha256=_rn(3),
        constructor_profile="ack_loss_confirmed",
        publisher_collision_nonce=publisher_nonce, staging_parent=staging_parent,
        stage_basename=stage_basename, stage_path=stage_path,
        proposed_payload_bytes=1, proposed_payload_sha256=proposal_sha,
        alternate_payload_bytes=None, alternate_payload_sha256=None,
        initial_state_version_sha256=initial,
        conflict_expected_state_version_sha256="0" + initial[1:],
        initial_inventory_projection_sha256=inventory_sha,
        active_chain_projection_sha256=chain_sha,
        pre_stage_observation=residue_fixture, action_trace=conflict_trace,
        final_snapshot_sha256=_rn(15), final_lifecycle_state="OPEN",
        artifact_projection_sha256=artifact_sha,
        post_stage_observation=residue,
        final_inventory_projection_sha256=inventory_sha,
        cas_binding_sha256="43A905BC01DB88CD057FFC74BE2AA8A0B2AC87CAB3248205804F095A4C0700F7",
        manifest_event_delta="zero",
        conflict_without_marker_status="exact_no_marker_no_stage_no_manifest",
        stage_residue_classification="exact_absent_at_two_sequential_endpoints",
    )
    traces = (
        SimpleNamespace(
            operation="publish", outcome="synthetic_marker_committed_result_withheld",
            reason_codes=("synthetic_marker_committed",), action_sha256=_rn(20),
            before_snapshot_sha256=_rn(21), after_snapshot_sha256=_rn(22),
            endpoint_state_changed=True, publisher_operation_sha256=None,
            publisher_transition_sha256=None, marker_sha256=_rn(40),
            epoch_ordinal=None, replay_observation=None, terminal_sha256=None,
            witness_purpose=None,
        ),
        SimpleNamespace(
            operation="acquire_epoch", outcome="epoch_issued",
            reason_codes=("recovery_marker_pending",), action_sha256=_rn(23),
            before_snapshot_sha256=_rn(22), after_snapshot_sha256=_rn(24),
            endpoint_state_changed=True, publisher_operation_sha256=None,
            publisher_transition_sha256=None, marker_sha256=_rn(40),
            epoch_ordinal=1, replay_observation=None, terminal_sha256=None,
            witness_purpose=None,
        ),
        SimpleNamespace(
            operation="replay_epoch", outcome="replay_confirmed_recovered",
            reason_codes=("synthetic_intended_transition_confirmed",),
            action_sha256=_rn(25), before_snapshot_sha256=_rn(24),
            after_snapshot_sha256=_rn(26), endpoint_state_changed=True,
            publisher_operation_sha256=None, publisher_transition_sha256=None,
            marker_sha256=_rn(40), epoch_ordinal=1,
            replay_observation="confirmed_intended", terminal_sha256=_rn(50),
            witness_purpose="record_recovered_terminal",
        ),
        SimpleNamespace(
            operation="consume_witness", outcome="witness_consumed",
            reason_codes=("witness_consumed",), action_sha256=_rn(27),
            before_snapshot_sha256=_rn(26), after_snapshot_sha256=_rn(28),
            endpoint_state_changed=True, publisher_operation_sha256=None,
            publisher_transition_sha256=None, marker_sha256=_rn(40),
            epoch_ordinal=1, replay_observation=None, terminal_sha256=_rn(50),
            witness_purpose="record_recovered_terminal",
        ),
    )
    marker = SimpleNamespace(marker_sha256=_rn(40))
    append = SimpleNamespace(append_sha256=append_sha)
    recovery_row = SimpleNamespace(
        outcome="integrated_synthetic_terminal_manifest_appended_and_witness_spent",
        reason_codes=("synthetic_intended_transition_confirmed",), root=root,
        seed_file_sha256=_rn(1), seed_identity_sha256=_rn(2),
        license_id=license_id, claim_receipt_sha256=_rn(3),
        constructor_profile="ack_loss_confirmed",
        publisher_collision_nonce=publisher_nonce, manifest_nonce=manifest_nonce,
        staging_parent=staging_parent, stage_basename=stage_basename,
        stage_path=stage_path, manifest_repository_path=repository,
        manifest_host_final_path=final_path, manifest_host_alias_path=alias_path,
        proposed_payload_bytes=1, proposed_payload_sha256=proposal_sha,
        alternate_payload_bytes=None, alternate_payload_sha256=None,
        initial_state_version_sha256=initial, expected_state_version_sha256=initial,
        initial_inventory_projection_sha256=inventory_sha,
        active_chain_projection_sha256=chain_sha,
        pre_stage_observation=residue, action_trace=traces, action_count=4,
        marker=marker, witness_purpose="record_recovered_terminal",
        witness_sha256=_rn(29), preconsume_snapshot_sha256=_rn(26),
        preconsume_lifecycle_state="RECOVERED_WITNESS_LIVE",
        preappend_artifact_projection_sha256=artifact_sha,
        preappend_stage_observation=residue, terminal_event_sha256=_rn(30),
        manifest_append=append,
        terminal_attestation_projection_sha256=attestation_sha,
        postappend_artifact_projection_sha256=artifact_sha,
        postappend_stage_observation=residue,
        final_inventory_projection_sha256=inventory_sha,
        final_snapshot_sha256=_rn(28),
        final_lifecycle_state="RECOVERED_WITNESS_SPENT",
        cas_binding_sha256=_rn(61),
        manifest_binding_sha256="FF8D4C6F9D21C8BCFCD43FE0EA4033C44B7EFEFEC49EA2801803EE3A3CD9FFC0",
        failure_code_binding="exact_phase2b2e_marker_tuple_no_inference",
        stage_residue_classification="absent_before_publish_exact_proposal_at_two_later_endpoints",
    )
    recovery_audit_row = SimpleNamespace(**vars(recovery_row))
    recovery_audit_row.pre_stage_observation = residue_fixture
    return conflict, recovery_row, recovery_audit_row


def test_phase2b2f_s01_public_surface() -> None:
    assert integrated.__all__ == PUBLIC_ALL
    assert type(integrated.__all__) is list
    assert issubclass(integrated.IntegratedSyntheticManifestV10Error, RuntimeError)
    assert integrated.IntegratedSyntheticManifestV10Error.__bases__ == (RuntimeError,)


def test_phase2b2f_s02_positional_signatures() -> None:
    expected = {
        "audit_synthetic_conflict_without_marker_v1_0": integrated.SyntheticConflictWithoutMarkerAuditV10,
        "append_integrated_synthetic_recovery_manifest_v1_0": integrated.IntegratedSyntheticRecoveryManifestAuditV10,
    }
    raw = {
        "root": "str", "seed_raw": "bytes", "constructor_profile": "str",
        "alternate_payload": "bytes | None", "proposed_payload": "bytes",
    }
    for name, return_type in expected.items():
        function = getattr(integrated, name)
        signature = inspect.signature(function)
        assert tuple(signature.parameters) == tuple(raw)
        assert all(
            parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            for parameter in signature.parameters.values()
        )
        assert function.__annotations__ == {**raw, "return": return_type.__name__}
        hints = get_type_hints(function)
        assert hints["root"] is str and hints["seed_raw"] is bytes
        assert hints["constructor_profile"] is str and hints["proposed_payload"] is bytes
        assert hints["alternate_payload"] == bytes | None
        assert hints["return"] is return_type


def test_phase2b2f_s03_record_arities() -> None:
    expected = (
        (integrated.SyntheticManifestResidueObservationV10, RESIDUE_FIELDS),
        (integrated.SyntheticCoordinatorActionTraceV10, TRACE_FIELDS),
        (integrated.SyntheticTerminalManifestAppendV10, APPEND_FIELDS),
        (integrated.SyntheticConflictWithoutMarkerAuditV10, CONFLICT_FIELDS),
        (integrated.IntegratedSyntheticRecoveryManifestAuditV10, RECOVERY_FIELDS),
    )
    assert tuple(len(names) for _kind, names in expected) == (39, 23, 39, 58, 88)
    for kind, names in expected:
        assert tuple(item.name for item in fields(kind)) == names
        assert kind.__dataclass_params__.frozen is True
        assert "__dict__" not in kind.__slots__


def test_phase2b2f_s04_constructor_type_domains(tmp_path: Path) -> None:
    row = _conflict(_fixture(tmp_path))
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error):
        replace(row, proposed_payload_bytes=True)
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error):
        replace(row, alternate_payload_bytes=False)
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error):
        replace(row.action_trace, reason_codes=["expected_state_version_mismatch"])
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error):
        replace(row.pre_stage_observation, observation_sha256="a" * 64)
    with pytest.raises(integrated.IntegratedSyntheticManifestV10Error):
        type("ConflictSubclass", (integrated.SyntheticConflictWithoutMarkerAuditV10,), {})

    recovery_row = _recover(_fixture(tmp_path, "primary"))
    invalid_epochs = tuple(
        trace if trace.epoch_ordinal is None else replace(trace, epoch_ordinal=4)
        for trace in recovery_row.action_trace
    )
    with pytest.raises(
        integrated.IntegratedSyntheticManifestV10Error,
        match="action trace epoch schedule is invalid",
    ):
        _coherent_recovery_replace(recovery_row, action_trace=invalid_epochs)

    invalid_marker_rows = (
        replace(recovery_row.action_trace[0], marker_sha256="0" * 64),
        *recovery_row.action_trace[1:],
    )
    with pytest.raises(
        integrated.IntegratedSyntheticManifestV10Error,
        match="action trace marker binding is invalid",
    ):
        _coherent_recovery_replace(recovery_row, action_trace=invalid_marker_rows)

    foreign_row = _recover(_fixture(tmp_path, "foreign"))
    with pytest.raises(
        integrated.IntegratedSyntheticManifestV10Error,
        match="nested stage observation differs from audit cells",
    ):
        _coherent_recovery_replace(
            recovery_row,
            pre_stage_observation=foreign_row.pre_stage_observation,
        )

    foreign_marker_fixture = replace(
        _fixture(tmp_path, "marker"),
        proposal=b"phase2b2f-foreign-proposal",
    )
    foreign_marker = _recover(foreign_marker_fixture).marker
    marker_traces = tuple(
        replace(trace, marker_sha256=foreign_marker.marker_sha256)
        for trace in recovery_row.action_trace
    )
    terminal_sha256 = marker_traces[-1].terminal_sha256
    assert terminal_sha256 is not None
    manifest_nonce = integrated._manifest_nonce(  # type: ignore[attr-defined]
        recovery_row.terminal_event_sha256,
        foreign_marker.marker_sha256,
        terminal_sha256,
    )
    manifest_alias = os.path.join(
        recovery_row.staging_parent,
        "uprime-rpc-attempt-manifest-stage-v1-" + manifest_nonce + ".json",
    )
    manifest_append = _coherent_append_replace(
        recovery_row.manifest_append,
        manifest_nonce=manifest_nonce,
        host_alias_path=manifest_alias,
    )
    cas_binding = integrated._cas_sha256(  # type: ignore[attr-defined]
        "recovery",
        recovery_row.initial_state_version_sha256,
        recovery_row.expected_state_version_sha256,
        recovery_row.proposed_payload_bytes,
        recovery_row.proposed_payload_sha256,
        recovery_row.alternate_payload_bytes,
        recovery_row.alternate_payload_sha256,
        foreign_marker.publisher_operation_sha256,
        foreign_marker.publisher_transition_sha256,
        foreign_marker.synthetic_fault_transition_sha256,
        foreign_marker.marker_sha256,
    )
    with pytest.raises(
        integrated.IntegratedSyntheticManifestV10Error,
        match="marker differs from audit cells",
    ):
        _coherent_recovery_replace(
            recovery_row,
            marker=foreign_marker,
            action_trace=marker_traces,
            manifest_nonce=manifest_nonce,
            manifest_host_alias_path=manifest_alias,
            manifest_append=manifest_append,
            cas_binding_sha256=cas_binding,
        )


def test_phase2b2f_s05_false_authority_cells(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path))
    nested = (
        row, row.marker, row.manifest_append,
        row.pre_stage_observation, row.preappend_stage_observation,
        row.postappend_stage_observation, *row.action_trace,
    )
    for value in nested:
        _assert_no_authority(value)
        for name in (
            "canonical_remote_authority", "licenses_execution",
            "licenses_publication", "licenses_recovery", "licenses_later_stage",
        ):
            if hasattr(value, name):
                with pytest.raises(Exception):
                    replace(value, **{name: True})


def test_phase2b2f_s06_constructor_zero_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    row = _recover(_fixture(tmp_path))
    values = (
        row.pre_stage_observation, row.action_trace[0], row.manifest_append, row,
    )
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("record constructor performed I/O or dependency work")
    for name in (
        "_os_stat", "_os_open", "_os_fstat", "_os_lseek", "_os_read",
        "_os_write", "_os_close", "_os_link", "_dep_parse_seed",
        "_dep_audit_inventory", "_dep_inspect_chain", "_dep_verify_terminal",
        "_dep_observe_artifacts", "_dep_publish_coordinator",
    ):
        monkeypatch.setattr(integrated, name, forbidden)
    for value in values:
        rebuilt = type(value)(*_values(value))
        assert rebuilt == value
    with pytest.raises(FrozenInstanceError):
        row.outcome = "mutated"  # type: ignore[misc]


def test_phase2b2f_s07_import_allowlist() -> None:
    tree = _source_tree()
    allowed_modules = {"dataclasses", "hashlib", "os", "re", "stat"}
    allowed_symbols = {
        "AttemptManifestV10Error", "PublicClaimReceiptV10",
        "AttemptManifestEventV10", "AttemptManifestEventFileV10",
        "AttemptManifestChainInspectionV10", "AttemptManifestChainAttestationV10",
        "encode_attempt_manifest_event_v1_0", "parse_attempt_manifest_event_file_v1_0",
        "inspect_local_attempt_manifest_chain_v1_0",
        "verify_local_attempt_manifest_terminal_chain_v1_0",
        "SyntheticSeedInventoryV10Error", "SyntheticClaimSeedV10",
        "SyntheticLocalClaimAuditV10", "SyntheticSeedLocalInventoryAuditV10",
        "parse_synthetic_claim_seed_v1_0", "audit_synthetic_seed_local_inventory_v1_0",
        "LocalArtifactObservationV10Error", "LocalArtifactObservationV10",
        "LocalArtifactSetObservationV10", "observe_local_rpc_artifact_set_v1_0",
        "InMemoryFakeCasV10Error", "InMemoryFakeCasStateV10",
        "InMemoryFakeCasTransitionV10", "initial_in_memory_fake_cas_state_v1_0",
        "LocalStagingFakePublishResultV10", "SyntheticRecoveryCoordinatorV10Error",
        "SyntheticRecoveryMarkerV10", "SyntheticRecoverySnapshotV10",
        "SyntheticRecoveryActionV10", "SyntheticRecoveryEpochV10",
        "SyntheticRecoveryWitnessV10", "SyntheticRecoveryCoordinatorV10",
        "new_synthetic_recovery_coordinator_v1_0",
        "snapshot_synthetic_recovery_coordinator_v1_0",
        "publish_with_synthetic_recovery_coordinator_v1_0",
        "acquire_synthetic_recovery_epoch_v1_0",
        "replay_synthetic_recovery_epoch_v1_0",
        "consume_synthetic_recovery_witness_v1_0",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert {alias.name for alias in node.names} <= allowed_modules
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                assert {alias.name for alias in node.names} == {"annotations"}
                continue
            names = {alias.name for alias in node.names}
            assert names <= allowed_symbols
            assert not any(name.startswith("_") for name in names)
            imported |= names
    assert imported == allowed_symbols
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "publish_local_staging_fake_cas_v1_0" not in source


def test_phase2b2f_s08_prereg_tree_absence_and_anchor() -> None:
    current_blob = subprocess.run(
        ["git", "hash-object", str(PREREG_PATH)], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, text=True,
    ).stdout.strip()
    assert current_blob == PREREG_BLOB
    prereg_probe = subprocess.run(
        ["git", "cat-file", "-e", f"{PREREG_COMMIT}^{{commit}}"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if prereg_probe.returncode == 0:
        for relative in (
            "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py",
            "tests/uprime_rpc_integrated_synthetic_manifest_cases.py",
            "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_execution_2026-07-11.md",
        ):
            probe = subprocess.run(
                ["git", "cat-file", "-e", f"{PREREG_COMMIT}:{relative}"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            assert probe.returncode != 0
        prereg_blob = subprocess.run(
            ["git", "rev-parse", f"{PREREG_COMMIT}:{PREREG_PATH.relative_to(ROOT).as_posix()}"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        litmus_at_gate = subprocess.run(
            ["git", "show", f"{PREREG_COMMIT}:lean_rgc/evals/uprime_rpc_litmus.py"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True, encoding="utf-8",
        ).stdout
        tracked_paths = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", PREREG_COMMIT, "--",
             "docs/experiments", "runs/uprime_u1_rpc_20260710"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.splitlines()
        exposure_tokens = ("exposure", "burn", "retir", "read_ledger")
        assert prereg_blob == PREREG_BLOB
        assert litmus_at_gate.count("EVIDENCE_MILESTONE_2B_PHASE2B2F_AMENDMENT_PATH") == 2
        assert litmus_at_gate.count("integrated_synthetic_manifest_recovery_audit_amendment_2026-07-11.md") == 1
        assert not any(
            token in path.lower()
            for path in tracked_paths
            for token in exposure_tokens
        )
    else:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert shallow == "true"


def test_phase2b2f_p01_root_exact_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    calls = 0
    original = integrated._dep_parse_seed
    def counted(raw: bytes) -> object:
        nonlocal calls
        calls += 1
        return original(raw)
    monkeypatch.setattr(integrated, "_dep_parse_seed", counted)
    bad = (
        Path(fixture.root), "relative/root", str(fixture.root) + os.sep + ".",
        str(fixture.root) + "\x00", str(fixture.root) + "\x1f",
        str(fixture.root) + "\ud800",
    )
    for root in bad:
        _expect_error(lambda root=root: integrated.audit_synthetic_conflict_without_marker_v1_0(
            root, fixture.seed_raw, "ack_loss_confirmed", None, fixture.proposal  # type: ignore[arg-type]
        ), "integrated synthetic preflight failed")
    assert calls == 0


def test_phase2b2f_p02_windows_path_grammar(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    bad = (r"\\server\share", r"\\?\C:\unsafe", r"\??\C:\unsafe", "C:relative")
    for root in bad:
        _expect_error(lambda root=root: integrated.audit_synthetic_conflict_without_marker_v1_0(
            root, fixture.seed_raw, "ack_loss_confirmed", None, fixture.proposal
        ), "integrated synthetic preflight failed")


def test_phase2b2f_p03_derived_path_bounds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_path_join
    calls = 0
    def oversized(*parts: str) -> str:
        nonlocal calls
        calls += 1
        value = original(*parts)
        if "uprime_u1_rpc_staging" in parts:
            return value + "x" * 5000
        return value
    monkeypatch.setattr(integrated, "_os_path_join", oversized)
    _expect_error(lambda: _conflict(fixture), "integrated synthetic preflight failed")
    assert calls > 0


def test_phase2b2f_p04_parent_type_and_same_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    fixture.staging_parent.rmdir()
    fixture.staging_parent.write_bytes(b"not-a-directory")
    _expect_error(lambda: _conflict(fixture), "integrated synthetic preflight failed")
    fixture.staging_parent.unlink()
    fixture.staging_parent.mkdir()
    original = integrated._os_stat
    def cross_device(path: str, *args: object, **kwargs: object) -> os.stat_result:
        value = original(path, *args, **kwargs)
        if os.path.normpath(path).endswith(os.path.normpath(
            os.path.join("uprime_u1_rpc_staging", fixture.receipt["license_id"])
        )):
            cells = list(value)
            cells[2] = int(cells[2]) + 1
            return os.stat_result(cells)
        return value
    monkeypatch.setattr(integrated, "_os_stat", cross_device)
    _expect_error(lambda: _conflict(fixture), "integrated synthetic preflight failed")


def test_phase2b2f_p05_profile_alternate_matrix(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    for profile, alternate in (
        ("normal", None), ("unknown", None),
        ("ack_loss_confirmed", fixture.alternate),
        ("ack_loss_unavailable_then_confirmed", fixture.alternate),
        ("ack_loss_unavailable_until_budget_block", fixture.alternate),
        ("wrong_delta_confirmed", None),
        ("wrong_delta_confirmed", fixture.proposal),
    ):
        _expect_error(lambda profile=profile, alternate=alternate: integrated.audit_synthetic_conflict_without_marker_v1_0(
            str(fixture.root), fixture.seed_raw, profile, alternate, fixture.proposal
        ), "integrated synthetic preflight failed")


def test_phase2b2f_p06_payload_boundaries(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    boundary = b"x" * MAX_PAYLOAD_BYTES
    row = integrated.audit_synthetic_conflict_without_marker_v1_0(
        str(fixture.root), fixture.seed_raw, "ack_loss_confirmed", None, boundary
    )
    assert row.proposed_payload_bytes == MAX_PAYLOAD_BYTES
    for proposed in (bytearray(b"x"), memoryview(b"x"), b"x" * (MAX_PAYLOAD_BYTES + 1)):
        _expect_error(lambda proposed=proposed: integrated.audit_synthetic_conflict_without_marker_v1_0(
            str(fixture.root), fixture.seed_raw, "ack_loss_confirmed", None, proposed  # type: ignore[arg-type]
        ), "integrated synthetic preflight failed")
    _expect_error(lambda: integrated.audit_synthetic_conflict_without_marker_v1_0(
        str(fixture.root), fixture.seed_raw, "wrong_delta_confirmed",
        b"x" * (MAX_PAYLOAD_BYTES + 1), b"y"
    ), "integrated synthetic preflight failed")


def test_phase2b2f_p07_nonce_and_path_derivation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    row = _conflict(fixture)
    parsed = inventory.parse_synthetic_claim_seed_v1_0(fixture.seed_raw)
    expected_nonce, _full = _publisher_nonce(
        parsed.seed_identity_sha256, "ack_loss_confirmed", fixture.proposal, None
    )
    assert row.publisher_collision_nonce == expected_nonce
    expected_parent = os.path.join(
        str(fixture.root), "docs", "experiments", "artifacts",
        "uprime_u1_rpc_staging", fixture.receipt["license_id"],
    )
    assert row.staging_parent == expected_parent
    assert row.stage_basename == f"uprime-rpc-fake-cas-stage-v1-{expected_nonce}.bin"
    assert row.stage_path == os.path.join(row.staging_parent, row.stage_basename)


def test_phase2b2f_p08_no_caller_records_or_handles() -> None:
    for function in (
        integrated.audit_synthetic_conflict_without_marker_v1_0,
        integrated.append_integrated_synthetic_recovery_manifest_v1_0,
    ):
        assert tuple(inspect.signature(function).parameters) == (
            "root", "seed_raw", "constructor_profile", "alternate_payload",
            "proposed_payload",
        )
        with pytest.raises(TypeError):
            function(root="x")  # type: ignore[call-arg]


def test_phase2b2f_h01_domain_lengths() -> None:
    assert tuple(map(len, DOMAINS)) == (68, 67, 72, 73, 76, 72, 84, 68, 64, 67, 60, 67)
    assert all(domain.endswith(b"\0") and domain.count(b"\0") == 1 for domain in DOMAINS)
    production = tuple(getattr(integrated, name) for name in (
        "_D_PUBLISHER_NONCE", "_D_MANIFEST_NONCE", "_D_RESIDUE", "_D_INVENTORY",
        "_D_ACTIVE_CHAIN", "_D_ARTIFACT", "_D_TERMINAL_ATTESTATION", "_D_APPEND",
        "_D_CAS", "_D_CONFLICT", "_D_MANIFEST_BINDING", "_D_RECOVERY",
    ))
    assert production == DOMAINS


def test_phase2b2f_h02_nonce_goldens() -> None:
    r2 = bytes((2,)) * 32
    publisher_nonce, publisher_full = _publisher_nonce(
        r2.hex().upper(), "ack_loss_confirmed", b"B", None
    )
    manifest_nonce, manifest_full = _manifest_nonce("1E" * 32, "28" * 32, "32" * 32)
    assert publisher_full == "FD03FF359D185DB3F748E046211C7C4A0BC184C9E256CF87F3A03B9D37C0492E"
    assert publisher_nonce == "fd03ff359d185db3f748e046211c7c4a"
    assert manifest_full == "6A20DF3130322CEBADCC96DF7C9D29C19382D64DEF09D752AF43A5E3E2225CFA"
    assert manifest_nonce == "6a20df3130322cebadcc96df7c9d29c1"


def test_phase2b2f_h03_residue_golden() -> None:
    license_id = "ab" * 32
    parent = f"/tmp/uprime-2b2f/docs/experiments/artifacts/uprime_u1_rpc_staging/{license_id}"
    nonce = "fd03ff359d185db3f748e046211c7c4a"
    basename = f"uprime-rpc-fake-cas-stage-v1-{nonce}.bin"
    row = SimpleNamespace(
        observation_phase="conflict_pre", staging_parent=parent,
        collision_nonce=nonce, stage_basename=basename,
        stage_path=f"{parent}/{basename}", expected_payload_bytes=1,
        expected_payload_sha256=hashlib.sha256(b"B").hexdigest().upper(),
        parent_namespace_state="present",
        parent_reason_codes=("stable_parent_directory",),
        observation_state="absent", reason_codes=("absent_at_both_points",),
        observed_payload_bytes=None, observed_payload_sha256=None,
        payload_relation="not_present",
    )
    assert _residue_digest(row) == "CFA7725FA3B5EE2144129C411207F2E58B25B2EED031EE2FF41A03F16C638009"


def test_phase2b2f_h04_inventory_chain_goldens() -> None:
    r = lambda n: bytes((n,)) * 32
    license_id = "ab" * 32
    claim = SimpleNamespace(
        license_id=license_id, seed_membership=True, local_membership=True,
        set_relation="seed_and_local", receipt_relation="exact_match",
        seed_receipt_sha256=r(4).hex().upper(),
        local_receipt_sha256=r(4).hex().upper(),
        chain_observation="valid_nonterminal", event_count=1, last_event_index=1,
        last_event_sha256=r(5).hex().upper(), terminal_event=False,
        recorded_verdict=None,
    )
    inventory_row = SimpleNamespace(
        seed_file_sha256=r(1).hex().upper(), seed_identity_sha256=r(2).hex().upper(),
        base_directory_status="present", seed_count=1, local_directory_count=1,
        union_claim_count=1, examined_claim_count=1, total_observed_event_bytes=123,
        unexpected_entry_count=0, coverage_status="mismatched", set_equality=True,
        all_seeded_local_present=True, all_seeded_terminal=False,
        all_seeded_receipts_match=True, claim_audits=(claim,),
    )
    assert _inventory_digest(inventory_row) == "1D233C9F36F64366BC2883C199AC7EFE05049B257B124F496A6C5A4CADDC1118"
    event = SimpleNamespace(created_at_utc="2026-07-11T00:00:00.000000Z")
    event_file = SimpleNamespace(event_bytes=b"x" * 123, event=event)
    chain = SimpleNamespace(
        license_id=license_id, claim_receipt_sha256=r(3).hex().upper(),
        first_event_sha256=r(5).hex().upper(), last_event_sha256=r(5).hex().upper(),
        event_files=(event_file,), event_count=1, last_event_index=1,
        last_event_type="claim_started", terminal_event=False, next_event_index=2,
    )
    assert _active_chain_digest(chain) == "4D8E3C26E565C0E74556E1F8BD9DC385696ABFD050DC5F78918FB78A23EC6B6C"


def test_phase2b2f_h05_artifact_terminal_goldens() -> None:
    r = lambda n: bytes((n,)) * 32
    paths = (
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.json.reservation",
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.responses.jsonl",
        "runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.json",
    )
    rows = tuple(
        SimpleNamespace(
            artifact_kind=kind, repository_path=path, observation_state="absent",
            reason_codes=("stable_parent_absence",), artifact_sha256=None,
            artifact_bytes=None, byte_limit=limit,
        )
        for kind, path, limit in zip(
            ("reservation", "ledger", "report"), paths,
            (1_048_576, 134_217_728, 16_777_216), strict=True,
        )
    )
    artifact_row = SimpleNamespace(
        claim_receipt_sha256=r(3).hex().upper(), parent_namespace_state="absent",
        parent_reason_codes=("stable_parent_absence",), reservation=rows[0],
        ledger=rows[1], report=rows[2], present_count=0, absent_count=3,
        indeterminate_count=0, total_present_bytes=0,
        snapshot_scope="sequential_per_artifact_not_atomic_bundle",
    )
    assert _artifact_digest(artifact_row) == "03B14D6282B1E95BF4E8323AD3936FC5999CDBF63EA3EEC35CBAD23439CFA5F9"
    terminal = SimpleNamespace(
        license_id="ab" * 32, claim_receipt_sha256=r(3).hex().upper(),
        event_count=2, first_event_sha256=r(5).hex().upper(), last_event_index=2,
        last_event_sha256=r(30).hex().upper(), chain_state="valid_terminal",
        terminal_event=True, last_event_type="recovery", recorded_verdict=None,
        failure_codes=("OTHER_HARNESS_ERROR",),
    )
    assert _terminal_attestation_digest(terminal) == "4C1DCEDEA89EB344ED49DD4306EDEE0C43C88F6EBBF0FBDE06FD37531304CC18"


def test_phase2b2f_h06_append_and_cas_goldens() -> None:
    r = lambda n: bytes((n,)) * 32
    license_id = "ab" * 32
    publisher_nonce = "fd03ff359d185db3f748e046211c7c4a"
    manifest_nonce = "6a20df3130322cebadcc96df7c9d29c1"
    parent = f"/tmp/uprime-2b2f/docs/experiments/artifacts/uprime_u1_rpc_staging/{license_id}"
    repository = f"docs/experiments/artifacts/uprime_u1_rpc_attempts/{license_id}/0002.json"
    append = SimpleNamespace(
        license_id=license_id, publisher_collision_nonce=publisher_nonce,
        manifest_nonce=manifest_nonce, repository_path=repository,
        host_final_path=f"/tmp/uprime-2b2f/{repository}",
        host_alias_path=f"{parent}/uprime-rpc-attempt-manifest-stage-v1-{manifest_nonce}.json",
        event_sha256=r(30).hex().upper(), event_bytes=321,
        append_status="exclusive_temp_verified_hardlink_materialized",
        write_call_count=1, read_call_count=2, file_create_count=1,
        hardlink_create_count=1, retained_path_alias_count=2,
    )
    assert _append_digest(append) == "E3CDCD0A2220488C9023E645EB7B381D0EF058F877F988BAD4149359C3BA01DC"
    initial = "D475431F78A252741905BD00E75E0E97A30326A91046BF9D4A827D4713BAEBB8"
    expected = "0" + initial[1:]
    proposal_sha = hashlib.sha256(b"B").hexdigest().upper()
    conflict = _digest(
        D_CAS, _k("conflict"), _h(initial), _h(expected), _u64(1), _h(proposal_sha),
        _j(None), _q(None), _q(r(13).hex().upper()), _q(r(14).hex().upper()),
        _q(None), _q(None),
    )
    recovery_cas = _digest(
        D_CAS, _k("recovery"), _h(initial), _h(initial), _u64(1), _h(proposal_sha),
        _j(None), _q(None), _q(r(13).hex().upper()), _q(r(14).hex().upper()),
        _q(r(30).hex().upper()), _q(r(40).hex().upper()),
    )
    assert conflict == "43A905BC01DB88CD057FFC74BE2AA8A0B2AC87CAB3248205804F095A4C0700F7"
    assert recovery_cas == "87E9D0C659F6879AAF9B0420F3D4460B25317E5A62B732A9D1697BFC5FB14AD5"


def test_phase2b2f_h07_conflict_audit_golden(tmp_path: Path) -> None:
    framed, _binding, _recovery = _framing_rows()
    preimage = _conflict_audit_preimage(framed)
    assert len(preimage) == 1_412
    assert hashlib.sha256(preimage).hexdigest().upper() == "053361307795DD652C20CE91D295173352CF915D1F989C902D7795E980DB5ADB"
    row = _conflict(_fixture(tmp_path))
    assert _residue_digest(row.pre_stage_observation) == row.pre_stage_observation.observation_sha256
    assert _residue_digest(row.post_stage_observation) == row.post_stage_observation.observation_sha256
    assert _cas_digest(row, conflict=True) == row.cas_binding_sha256
    assert _conflict_audit_digest(row) == row.audit_sha256


def test_phase2b2f_h08_binding_recovery_goldens(tmp_path: Path) -> None:
    _conflict_row, binding_framed, recovery_framed = _framing_rows()
    binding_preimage = _manifest_binding_preimage(binding_framed)
    recovery_preimage = _recovery_audit_preimage(recovery_framed)
    assert len(binding_preimage) == 1_495
    assert hashlib.sha256(binding_preimage).hexdigest().upper() == "FF8D4C6F9D21C8BCFCD43FE0EA4033C44B7EFEFEC49EA2801803EE3A3CD9FFC0"
    assert len(recovery_preimage) == 3_077
    assert hashlib.sha256(recovery_preimage).hexdigest().upper() == "9A684A837778C33892D08C3C2014C26E7CA9E7237E6F4B116511681A4963CA4F"
    row = _recover(_fixture(tmp_path))
    expected_nonce, full = _manifest_nonce(
        row.terminal_event_sha256, row.marker.marker_sha256,
        row.action_trace[-1].terminal_sha256,
    )
    assert full == hashlib.sha256(
        D_MANIFEST_NONCE + _h(row.terminal_event_sha256) +
        _h(row.marker.marker_sha256) + _h(row.action_trace[-1].terminal_sha256)
    ).hexdigest().upper()
    assert row.manifest_nonce == expected_nonce
    assert _append_digest(row.manifest_append) == row.manifest_append.append_sha256
    assert _cas_digest(row, conflict=False) == row.cas_binding_sha256
    assert _manifest_binding_digest(row) == row.manifest_binding_sha256
    assert _recovery_audit_digest(row) == row.audit_sha256


def test_phase2b2f_i01_exact_one_seed_receipt(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    seeds = (_seed_raw([]), _seed_raw([fixture.receipt, _receipt_mapping("d" * 40)]))
    for raw in seeds:
        _expect_error(lambda raw=raw: integrated.audit_synthetic_conflict_without_marker_v1_0(
            str(fixture.root), raw, "ack_loss_confirmed", None, fixture.proposal
        ), "integrated synthetic preflight failed")
    noncanonical = fixture.seed_raw.replace(b"\n", b" \n")
    _expect_error(lambda: integrated.audit_synthetic_conflict_without_marker_v1_0(
        str(fixture.root), noncanonical, "ack_loss_confirmed", None, fixture.proposal
    ), "integrated synthetic preflight failed")


def test_phase2b2f_i02_active_inventory_endpoint(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    before = inventory.audit_synthetic_seed_local_inventory_v1_0(
        str(fixture.root), fixture.seed_raw
    )
    row = _conflict(fixture)
    assert before.coverage_status == "mismatched"
    assert before.nonterminal_ids == (fixture.receipt["license_id"],)
    assert before.terminal_ids == ()
    assert _inventory_digest(before) == row.initial_inventory_projection_sha256
    assert row.initial_inventory_projection_sha256 == row.final_inventory_projection_sha256


def test_phase2b2f_i03_invalid_namespace_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = [_fixture(tmp_path, f"invalid-{index}") for index in range(3)]
    base0 = fixtures[0].attempt_dir.parent
    (base0 / "unexpected.txt").write_bytes(b"x")
    orphan = "f" * 64
    (fixtures[1].attempt_dir.parent / orphan).mkdir()
    changed = copy.deepcopy(fixtures[2].receipt)
    changed["license_commit"] = "9" * 40
    bad_claim = _claim_mapping(changed)
    fixtures[2].attempt_dir.joinpath("0001.json").write_bytes(
        ledger.canonical_json_bytes(bad_claim) + b"\n"
    )
    calls = 0
    original = integrated._dep_publish_coordinator
    def counted(*args: object) -> object:
        nonlocal calls
        calls += 1
        return original(*args)
    monkeypatch.setattr(integrated, "_dep_publish_coordinator", counted)
    for fixture in fixtures:
        _expect_error(lambda fixture=fixture: _conflict(fixture), "integrated synthetic preflight failed")
    assert calls == 0


def test_phase2b2f_i04_exact_index1_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    terminal = _claim_mapping(fixture.receipt)
    terminal.update(
        event_type="recovery", event_index=2,
        prior_event_sha256=hashlib.sha256(fixture.claim_raw).hexdigest().upper(),
        failure_codes=["OTHER_HARNESS_ERROR"], terminal_event=True,
    )
    fixture.attempt_dir.joinpath("0002.json").write_bytes(
        ledger.canonical_json_bytes(terminal) + b"\n"
    )
    called = False
    def forbidden(*_args: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("publish reached")
    monkeypatch.setattr(integrated, "_dep_publish_coordinator", forbidden)
    _expect_error(lambda: _conflict(fixture), "integrated synthetic preflight failed")
    assert called is False


def test_phase2b2f_i05_stage_stable_absence(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    row = _conflict(fixture)
    for phase, observation in (
        ("conflict_pre", row.pre_stage_observation),
        ("conflict_post", row.post_stage_observation),
    ):
        assert observation.observation_phase == phase
        assert observation.parent_namespace_state == "present"
        assert observation.parent_reason_codes == ("stable_parent_directory",)
        assert observation.observation_state == "absent"
        assert observation.reason_codes == ("absent_at_both_points",)
        assert observation.payload_relation == "not_present"
        assert observation.observed_payload_bytes is None


def test_phase2b2f_i06_stage_stable_exact_payload(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    row = _recover(fixture)
    for phase, observation in (
        ("pre_append", row.preappend_stage_observation),
        ("post_append", row.postappend_stage_observation),
    ):
        assert observation.observation_phase == phase
        assert observation.observation_state == "present"
        assert observation.reason_codes == ("stable_bounded_regular_file_exact_payload",)
        assert observation.payload_relation == "exact"
        assert observation.observed_payload_bytes == len(fixture.proposal)
        assert observation.observed_payload_sha256 == hashlib.sha256(fixture.proposal).hexdigest().upper()


def test_phase2b2f_i07_stage_indeterminate_and_raw_equality(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_read
    reads = 0
    def corrupt_second_pass(fd: int, count: int) -> bytes:
        nonlocal reads
        raw = original(fd, count)
        reads += 1
        if reads == 3 and raw:
            return bytes((raw[0] ^ 1,)) + raw[1:]
        return raw
    monkeypatch.setattr(integrated, "_os_read", corrupt_second_pass)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed before manifest temp create")
    assert not fixture.attempt_dir.joinpath("0002.json").exists()

    collision_fixture = _fixture(tmp_path, "forced-collision")
    nonce = "10" * 16
    plan = integrated._early_path_plan(
        str(collision_fixture.root), collision_fixture.receipt["license_id"], nonce
    )
    Path(plan.stage_path).write_bytes(collision_fixture.proposal)
    real_read = os.read
    read_calls = 0
    def distinct_second_stream(fd: int, count: int) -> bytes:
        nonlocal read_calls
        raw = real_read(fd, count)
        read_calls += 1
        if read_calls == 3 and raw:
            return bytes((raw[0] ^ 1,)) + raw[1:]
        return raw
    class CollisionHash:
        def __init__(self, _raw: bytes = b"") -> None:
            pass
        def update(self, _raw: bytes) -> None:
            pass
        def hexdigest(self) -> str:
            return "A" * 64
        def digest(self) -> bytes:
            return b"\xAA" * 32
    with monkeypatch.context() as local:
        local.setattr(integrated, "_os_read", distinct_second_stream)
        local.setattr(integrated.hashlib, "sha256", CollisionHash)
        observed = integrated._observe_stage_residue(
            plan, collision_fixture.proposal, "conflict_pre"
        )
    assert observed.observation_state == "present"
    assert observed.payload_relation == "different"
    assert observed.reason_codes == ("stable_bounded_regular_file_different_payload",)


def test_phase2b2f_i08_artifact_all_absent_only(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    anchor = fixture.receipt["license_commit"][:12]
    path = fixture.root / "runs" / "uprime_u1_rpc_20260710" / f"rpc_diagnostic_{anchor}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"present")
    observed = artifacts.observe_local_rpc_artifact_set_v1_0(
        str(fixture.root), manifest.PublicClaimReceiptV10(**fixture.receipt)
    )
    assert observed.report.observation_state == "present"
    _expect_error(lambda: _conflict(fixture), "integrated synthetic conflict audit failed")
    assert not fixture.attempt_dir.joinpath("0002.json").exists()


def test_phase2b2f_c01_conflict_exact_endpoint(tmp_path: Path) -> None:
    row = _conflict(_fixture(tmp_path))
    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    expected = ("1" if initial.state_version_sha256[0] == "0" else "0") + initial.state_version_sha256[1:]
    assert row.outcome == "conflict_without_marker_confirmed"
    assert row.reason_codes == ("expected_state_version_mismatch",)
    assert row.initial_state_version_sha256 == initial.state_version_sha256
    assert row.conflict_expected_state_version_sha256 == expected
    assert row.action_trace.operation == "publish"
    assert row.action_trace.outcome == "cas_conflict_no_marker"
    assert row.action_trace.marker_sha256 is None
    assert row.final_lifecycle_state == "OPEN"


def test_phase2b2f_c02_conflict_physical_zero_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    calls: list[str] = []
    def forbidden(*_args: object, **_kwargs: object) -> object:
        calls.append("forbidden")
        raise AssertionError("conflict reached a write/manifest/recovery seam")
    for name in (
        "_os_open", "_os_write", "_os_link", "_append_terminal_manifest",
        "_dep_encode_event", "_dep_verify_terminal", "_dep_acquire_epoch",
        "_dep_replay_epoch", "_dep_consume_witness",
    ):
        monkeypatch.setattr(integrated, name, forbidden)
    row = _conflict(fixture)
    assert calls == []
    assert row.manifest_event_delta == "zero"
    assert row.conflict_without_marker_status == "exact_no_marker_no_stage_no_manifest"
    assert not any(fixture.staging_parent.iterdir())
    assert tuple(path.name for path in fixture.attempt_dir.iterdir()) == ("0001.json",)


def test_phase2b2f_c03_conflict_projection_binding(tmp_path: Path) -> None:
    row = _conflict(_fixture(tmp_path))
    trace = row.action_trace
    assert trace.publisher_operation_sha256 is not None
    assert trace.publisher_transition_sha256 is not None
    assert trace.marker_sha256 is None and trace.epoch_ordinal is None
    assert trace.replay_observation is None and trace.terminal_sha256 is None
    assert trace.endpoint_state_changed is False
    assert trace.before_snapshot_sha256 == trace.after_snapshot_sha256
    assert trace.after_snapshot_sha256 == row.final_snapshot_sha256
    assert _cas_digest(row, conflict=True) == row.cas_binding_sha256
    assert _conflict_audit_digest(row) == row.audit_sha256


def test_phase2b2f_c04_ack_loss_confirmed_trace(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path), "ack_loss_confirmed")
    assert tuple(trace.operation for trace in row.action_trace) == (
        "publish", "acquire_epoch", "replay_epoch", "consume_witness",
    )
    assert tuple(trace.outcome for trace in row.action_trace) == (
        "synthetic_marker_committed_result_withheld", "epoch_issued",
        "replay_confirmed_recovered", "witness_consumed",
    )
    assert row.action_count == 4
    assert row.witness_purpose == "record_recovered_terminal"
    assert row.final_lifecycle_state == "RECOVERED_WITNESS_SPENT"


def test_phase2b2f_c05_unavailable_then_confirmed_trace(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path), "ack_loss_unavailable_then_confirmed")
    assert tuple(trace.operation for trace in row.action_trace) == (
        "publish", "acquire_epoch", "replay_epoch", "acquire_epoch",
        "replay_epoch", "consume_witness",
    )
    assert tuple(trace.epoch_ordinal for trace in row.action_trace) == (
        None, 1, 1, 2, 2, 2,
    )
    assert row.action_trace[2].replay_observation == "unavailable"
    assert row.action_trace[4].replay_observation == "confirmed_intended"
    assert row.action_count == 6


def test_phase2b2f_c06_unavailable_budget_trace(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path), "ack_loss_unavailable_until_budget_block")
    assert row.action_count == 10
    assert tuple(trace.operation for trace in row.action_trace) == (
        "publish", "acquire_epoch", "replay_epoch", "acquire_epoch",
        "replay_epoch", "acquire_epoch", "replay_epoch", "acquire_epoch",
        "replay_epoch", "consume_witness",
    )
    assert tuple(row.action_trace[index].epoch_ordinal for index in (1, 3, 5, 7)) == (1, 2, 3, 4)
    assert row.action_trace[8].outcome == "replay_unavailable_budget_permanent_block"
    assert row.witness_purpose == "record_permanent_block"
    assert row.final_lifecycle_state == "BLOCKED_WITNESS_SPENT"


def test_phase2b2f_c07_wrong_delta_trace(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path), "wrong_delta_confirmed")
    assert row.action_count == 4
    assert row.alternate_payload_bytes is not None
    assert row.action_trace[2].replay_observation == "confirmed_wrong_delta"
    assert row.action_trace[2].outcome == "replay_wrong_delta_permanent_block"
    assert row.witness_purpose == "record_permanent_block"
    assert row.final_lifecycle_state == "BLOCKED_WITNESS_SPENT"


def test_phase2b2f_c08_snapshot_continuity_and_terminal_purpose(tmp_path: Path) -> None:
    for profile in (
        "ack_loss_confirmed", "ack_loss_unavailable_then_confirmed",
        "ack_loss_unavailable_until_budget_block", "wrong_delta_confirmed",
    ):
        row = _recover(_fixture(tmp_path, profile), profile)
        for before, after in zip(row.action_trace, row.action_trace[1:]):
            assert after.before_snapshot_sha256 == before.after_snapshot_sha256
        assert row.preconsume_snapshot_sha256 == row.action_trace[-2].after_snapshot_sha256
        assert row.action_trace[-1].before_snapshot_sha256 == row.preconsume_snapshot_sha256
        assert row.action_trace[-1].after_snapshot_sha256 == row.final_snapshot_sha256
        assert row.action_trace[-1].witness_purpose == row.witness_purpose
        assert row.action_trace[-1].terminal_sha256 == row.action_trace[-2].terminal_sha256


def test_phase2b2f_m01_terminal_event_mapping(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    row = _recover(fixture)
    raw = Path(row.manifest_host_final_path).read_bytes()
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        row.manifest_repository_path, raw,
    )
    event = parsed.event
    assert event.event_type == "recovery" and event.event_index == 2
    assert event.created_at_utc == "2026-07-11T00:00:00.000000Z"
    assert event.license_id == fixture.receipt["license_id"]
    assert event.claim_receipt_sha256 == _receipt_sha256(fixture.receipt)
    assert event.prior_event_sha256 == hashlib.sha256(fixture.claim_raw).hexdigest().upper()
    assert event.failure_codes == row.marker.phase2b1_failure_codes == ("OTHER_HARNESS_ERROR",)
    assert event.verdict is None and event.terminal_event is True
    assert event.reservation_exists is event.ledger_exists is event.report_exists is False


def test_phase2b2f_m02_canonical_encode_parse_lf(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path))
    raw = Path(row.manifest_host_final_path).read_bytes()
    parsed = manifest.parse_attempt_manifest_event_file_v1_0(
        row.manifest_repository_path, raw,
    )
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert manifest.encode_attempt_manifest_event_v1_0(parsed.event) == raw
    assert hashlib.sha256(raw).hexdigest().upper() == row.terminal_event_sha256
    assert len(raw) == row.manifest_append.event_bytes


def test_phase2b2f_m03_temp_exclusive_partial_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_write
    calls: list[int] = []
    original_open = integrated._os_open
    manifest_opens: list[tuple[int, int]] = []
    def tracked_open(path: str, flags: int, mode: int | None = None) -> int:
        if mode is not None:
            manifest_opens.append((flags, mode))
            return original_open(path, flags, mode)
        return original_open(path, flags)
    def partial(fd: int, payload: bytes) -> int:
        chunk = payload[:3]
        calls.append(len(chunk))
        return original(fd, chunk)
    monkeypatch.setattr(integrated, "_os_write", partial)
    monkeypatch.setattr(integrated, "_os_open", tracked_open)
    row = _recover(fixture)
    assert row.manifest_append.write_call_count == len(calls) > 1
    assert all(0 < count <= 3 for count in calls)
    assert manifest_opens == [(integrated._OPEN_FLAGS, 0o600)]
    assert integrated._OPEN_FLAGS & os.O_CREAT and integrated._OPEN_FLAGS & os.O_EXCL
    fixture2 = _fixture(tmp_path, "zero-write")
    monkeypatch.setattr(integrated, "_os_write", lambda _fd, _raw: 0)
    _expect_error(lambda: _recover(fixture2), "integrated synthetic recovery failed after manifest temp create")


def test_phase2b2f_m04_readback_seek_eof(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original_seek = integrated._os_lseek
    seeks: list[tuple[int, int]] = []
    def tracked_seek(fd: int, offset: int, whence: int) -> int:
        seeks.append((offset, whence))
        return original_seek(fd, offset, whence)
    monkeypatch.setattr(integrated, "_os_lseek", tracked_seek)
    row = _recover(fixture)
    assert seeks and all(item == (0, os.SEEK_SET) for item in seeks)
    assert 2 <= row.manifest_append.read_call_count <= 17
    fixture2 = _fixture(tmp_path, "short-read")
    original_read = integrated._os_read
    def short_manifest(fd: int, count: int) -> bytes:
        raw = original_read(fd, count)
        if count > len(fixture2.proposal) and raw:
            return raw[:-1]
        return raw
    monkeypatch.setattr(integrated, "_os_read", short_manifest)
    _expect_error(lambda: _recover(fixture2), "integrated synthetic recovery failed after manifest temp create")


def test_phase2b2f_m05_alias_close_and_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_close
    close_calls: list[int] = []
    def tracked(fd: int) -> None:
        close_calls.append(fd)
        return original(fd)
    monkeypatch.setattr(integrated, "_os_close", tracked)
    row = _recover(fixture)
    assert len(close_calls) == 3  # two stage-observer descriptors plus manifest descriptor
    assert os.path.samefile(row.manifest_host_alias_path, row.manifest_host_final_path)
    fixture2 = _fixture(tmp_path, "close-error")
    calls = 0
    def fail_last_close(fd: int) -> None:
        nonlocal calls
        calls += 1
        original(fd)
        if calls == 2:
            raise OSError("secret close")
    monkeypatch.setattr(integrated, "_os_close", fail_last_close)
    _expect_error(lambda: _recover(fixture2), "integrated synthetic recovery failed after manifest temp create")


def test_phase2b2f_m06_final_hardlink_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_link
    calls: list[tuple[str, str, bool]] = []
    def tracked(source: str, target: str, *, follow_symlinks: bool = True) -> None:
        calls.append((source, target, follow_symlinks))
        return original(source, target, follow_symlinks=follow_symlinks)
    monkeypatch.setattr(integrated, "_os_link", tracked)
    row = _recover(fixture)
    assert calls == [(row.manifest_host_alias_path, row.manifest_host_final_path, False)]
    assert os.path.samefile(row.manifest_host_alias_path, row.manifest_host_final_path)
    assert Path(row.manifest_host_alias_path).read_bytes() == Path(row.manifest_host_final_path).read_bytes()
    assert row.manifest_append.hardlink_create_count == 1
    assert row.manifest_append.retained_path_alias_count == 2


def test_phase2b2f_m07_preplay_and_concurrent_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_link
    def perform_then_raise(source: str, target: str, *, follow_symlinks: bool = True) -> None:
        original(source, target, follow_symlinks=follow_symlinks)
        raise FileExistsError("concurrent collision")
    monkeypatch.setattr(integrated, "_os_link", perform_then_raise)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed after manifest hardlink")
    assert fixture.attempt_dir.joinpath("0002.json").exists()
    assert len(tuple(fixture.staging_parent.iterdir())) == 2  # publisher stage and retained alias
    fixture2 = _fixture(tmp_path, "preplayed")
    final = fixture2.attempt_dir / "0002.json"
    final.write_bytes(fixture.attempt_dir.joinpath("0002.json").read_bytes())
    monkeypatch.setattr(integrated, "_os_link", original)
    _expect_error(lambda: _recover(fixture2), "integrated synthetic preflight failed")
    assert final.exists() and len(tuple(fixture2.staging_parent.iterdir())) == 0


def test_phase2b2f_m08_terminal_attestation_inventory(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    row = _recover(fixture)
    attestation = manifest.verify_local_attempt_manifest_terminal_chain_v1_0(
        str(fixture.root), fixture.receipt["license_id"]
    )
    final_inventory = inventory.audit_synthetic_seed_local_inventory_v1_0(
        str(fixture.root), fixture.seed_raw
    )
    assert _terminal_attestation_digest(attestation) == row.terminal_attestation_projection_sha256
    assert attestation.event_count == 2 and attestation.last_event_index == 2
    assert attestation.last_event_sha256 == row.terminal_event_sha256
    assert attestation.failure_codes == ("OTHER_HARNESS_ERROR",)
    assert final_inventory.coverage_status == "matched_terminal"
    assert final_inventory.terminal_ids == (fixture.receipt["license_id"],)
    assert _inventory_digest(final_inventory) == row.final_inventory_projection_sha256


def test_phase2b2f_w01_witness_order_last_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    log: list[str] = []
    seams = (
        "_dep_parse_seed", "_dep_audit_inventory", "_dep_inspect_chain",
        "_dep_verify_terminal", "_dep_observe_artifacts", "_dep_initial_state",
        "_dep_new_coordinator", "_dep_snapshot_coordinator",
        "_dep_publish_coordinator", "_dep_acquire_epoch", "_dep_replay_epoch",
        "_dep_consume_witness", "_dep_encode_event", "_dep_parse_event_file",
        "_observe_stage_residue", "_append_terminal_manifest",
    )
    for name in seams:
        original = getattr(integrated, name)
        def tracked(*args: object, _name: str = name, _original: Any = original, **kwargs: object) -> object:
            log.append(_name)
            return _original(*args, **kwargs)
        monkeypatch.setattr(integrated, name, tracked)
    row = _recover(fixture)
    assert log[-1] == "_dep_consume_witness"
    assert log.count("_dep_consume_witness") == 1
    assert log.count("_append_terminal_manifest") == 1
    assert log.index("_append_terminal_manifest") < log.index("_dep_verify_terminal")
    assert log.index("_dep_verify_terminal") < log.index("_dep_consume_witness")
    assert log.count("_dep_audit_inventory") == 2
    assert log.count("_dep_observe_artifacts") == 2
    assert row.action_trace[-1].operation == "consume_witness"


def test_phase2b2f_w02_foreign_and_copied_witness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._dep_replay_epoch
    copied = False
    def detached(*args: object, **kwargs: object) -> object:
        nonlocal copied
        action = original(*args, **kwargs)
        if action.issued_witness is not None:
            copied = True
            return replace(action, issued_witness=copy.copy(action.issued_witness))
        return action
    monkeypatch.setattr(integrated, "_dep_replay_epoch", detached)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed before manifest temp create")
    assert copied is True
    assert not fixture.attempt_dir.joinpath("0002.json").exists()


def test_phase2b2f_w03_block_is_not_success(tmp_path: Path) -> None:
    for profile in ("ack_loss_unavailable_until_budget_block", "wrong_delta_confirmed"):
        row = _recover(_fixture(tmp_path, profile), profile)
        assert row.witness_purpose == "record_permanent_block"
        assert row.preconsume_lifecycle_state == "BLOCKED_WITNESS_LIVE"
        assert row.final_lifecycle_state == "BLOCKED_WITNESS_SPENT"
        assert row.action_trace[-2].terminal_sha256 == row.action_trace[-1].terminal_sha256
        assert "recovered" not in row.reason_codes[0]
        _assert_no_authority(row)


def test_phase2b2f_w04_precreate_failure_cuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    calls = 0
    def fail_create(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise FileExistsError("secret precreate")
    monkeypatch.setattr(integrated, "_os_open", fail_create)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed before manifest temp create")
    assert calls == 1
    assert len(tuple(fixture.staging_parent.iterdir())) == 1  # publisher stage only
    assert not fixture.attempt_dir.joinpath("0002.json").exists()


def test_phase2b2f_w05_temp_residue_failure_cuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_write
    writes = 0
    consumed = False
    def partial_then_fail(fd: int, payload: bytes) -> int:
        nonlocal writes
        writes += 1
        if writes == 1:
            return original(fd, payload[:1])
        raise OSError("secret write")
    def consume(*_args: object, **_kwargs: object) -> object:
        nonlocal consumed
        consumed = True
        raise AssertionError("consume reached")
    monkeypatch.setattr(integrated, "_os_write", partial_then_fail)
    monkeypatch.setattr(integrated, "_dep_consume_witness", consume)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed after manifest temp create")
    assert writes == 2 and consumed is False
    residue = tuple(fixture.staging_parent.iterdir())
    assert len(residue) == 2
    assert any(path.stat().st_size == 1 for path in residue)
    assert not fixture.attempt_dir.joinpath("0002.json").exists()


def test_phase2b2f_w06_link_perform_then_raise_cut(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original = integrated._os_link
    consumed = False
    def link_then_raise(source: str, target: str, *, follow_symlinks: bool = True) -> None:
        original(source, target, follow_symlinks=follow_symlinks)
        raise OSError("secret after link")
    def consume(*_args: object, **_kwargs: object) -> object:
        nonlocal consumed
        consumed = True
        raise AssertionError("consume reached")
    monkeypatch.setattr(integrated, "_os_link", link_then_raise)
    monkeypatch.setattr(integrated, "_dep_consume_witness", consume)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed after manifest hardlink")
    assert consumed is False
    assert fixture.attempt_dir.joinpath("0002.json").exists()
    assert len(tuple(fixture.staging_parent.iterdir())) == 2


def test_phase2b2f_w07_postlink_preconsume_cuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    consumed = False
    def fail_verifier(*_args: object, **_kwargs: object) -> object:
        raise manifest.AttemptManifestV10Error("secret terminal")
    def consume(*_args: object, **_kwargs: object) -> object:
        nonlocal consumed
        consumed = True
        raise AssertionError("consume reached")
    monkeypatch.setattr(integrated, "_dep_verify_terminal", fail_verifier)
    monkeypatch.setattr(integrated, "_dep_consume_witness", consume)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed after manifest hardlink")
    assert consumed is False
    assert fixture.attempt_dir.joinpath("0002.json").exists()
    assert len(tuple(fixture.staging_parent.iterdir())) == 2


def test_phase2b2f_w08_postconsume_construction_cut(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    original_consume = integrated._dep_consume_witness
    consumed = 0
    def tracked_consume(*args: object, **kwargs: object) -> object:
        nonlocal consumed
        action = original_consume(*args, **kwargs)
        consumed += 1
        return action
    def fail_hash(_value: object) -> str:
        raise ValueError("secret postconsume hash")
    monkeypatch.setattr(integrated, "_dep_consume_witness", tracked_consume)
    monkeypatch.setattr(integrated, "_recovery_audit_sha256", fail_hash)
    _expect_error(lambda: _recover(fixture), "integrated synthetic recovery failed after witness consumption")
    assert consumed == 1
    assert fixture.attempt_dir.joinpath("0002.json").exists()
    assert len(tuple(fixture.staging_parent.iterdir())) == 2


def test_phase2b2f_g01_sanitized_errors_and_baseexception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    with monkeypatch.context() as local:
        local.setattr(integrated, "_dep_parse_seed", lambda _raw: (_ for _ in ()).throw(ValueError("SECRET_PATH")))
        error = _expect_error(lambda: _conflict(fixture), "integrated synthetic preflight failed")
        assert "SECRET" not in str(error)

    class Primary(BaseException):
        pass
    primary = Primary("primary identity")
    with monkeypatch.context() as local:
        def raise_primary(_raw: bytes) -> object:
            raise primary
        local.setattr(integrated, "_dep_parse_seed", raise_primary)
        with pytest.raises(Primary) as caught:
            _conflict(fixture)
        assert caught.value is primary

    fixture2 = _fixture(tmp_path, "close-mask")
    primary2 = Primary("write primary")
    with monkeypatch.context() as local:
        close_calls = 0
        def raise_write(_fd: int, _raw: bytes) -> int:
            raise primary2
        def raise_close(_fd: int) -> None:
            nonlocal close_calls
            close_calls += 1
            if close_calls == 2:
                raise OSError("close secondary")
            return os.close(_fd)
        local.setattr(integrated, "_os_write", raise_write)
        local.setattr(integrated, "_os_close", raise_close)
        with pytest.raises(Primary) as caught2:
            _recover(fixture2)
        assert caught2.value is primary2


def test_phase2b2f_g02_aggregate_resource_arithmetic(tmp_path: Path) -> None:
    conflict = _conflict(_fixture(tmp_path, "conflict"))
    recovery_row = _recover(_fixture(tmp_path, "recovery"))
    i, a, c, s, p, m = 268_435_457, 304_087_043, 134_217_729, 2_097_153, 2_097_152, 2_097_153
    assert 2 * i + a + c + 2 * s == 979_369_992
    assert 2 * i + 2 * a + 2 * c + 3 * s + p + m == 1_423_966_222
    assert conflict.aggregate_dependency_payload_work_upper_bound_bytes == 979_369_992
    assert recovery_row.aggregate_dependency_payload_work_upper_bound_bytes == 1_423_966_222
    assert (conflict.max_inventory_audits, conflict.max_artifact_observations, conflict.max_stage_observations) == (2, 1, 2)
    assert (recovery_row.max_inventory_audits, recovery_row.max_artifact_observations, recovery_row.max_stage_observations) == (2, 2, 3)


def test_phase2b2f_g03_payload_reference_and_copy_scope(tmp_path: Path) -> None:
    row = _recover(_fixture(tmp_path), "wrong_delta_confirmed")
    assert row.coordinator_payload_reference_upper_bound_bytes == 3_145_728
    assert row.proposal_payload_copy_upper_bound_bytes == 0
    assert row.max_seed_claims == 1 and row.max_chain_events == 2
    assert row.max_coordinator_actions == 10 and row.max_recovery_epochs == 4
    assert row.max_manifest_appends == 1
    forbidden_types = (
        bytes, cas.InMemoryFakeCasStateV10, cas.InMemoryFakeCasTransitionV10,
        publisher.LocalStagingFakePublishResultV10, recovery.SyntheticRecoveryActionV10,
        recovery.SyntheticRecoveryEpochV10, recovery.SyntheticRecoveryWitnessV10,
        recovery.SyntheticRecoveryCoordinatorV10,
    )
    assert not any(isinstance(getattr(row, item.name), forbidden_types) for item in fields(row))


def test_phase2b2f_g04_no_cleanup_fsync_or_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    tree = _source_tree()
    forbidden = {"unlink", "remove", "rename", "replace", "fsync", "fdatasync", "chmod", "mkdir", "makedirs", "sleep"}
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                assert node.func.attr not in forbidden
    def forbidden_call(*_args: object, **_kwargs: object) -> object:
        called.append("forbidden")
        raise AssertionError("cleanup/durability/retry capability reached")
    for name in forbidden:
        if hasattr(integrated.os, name):
            monkeypatch.setattr(integrated.os, name, forbidden_call)
    row = _recover(fixture)
    assert called == []
    assert row.cleanup_scope == "no_unlink_rename_replace_or_residue_cleanup"
    assert row.durability_scope == "fsync_not_called_crash_and_power_loss_not_observed"


def test_phase2b2f_g05_forbidden_capability_sentinels() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    forbidden_fragments = (
        "subprocess", "socket", "urllib", "requests", "http.client", "gitpython",
        "paramiko", "torch", "cuda", "ssh", "lean_worker", "rerun_license",
        "registry", "registered_run", "reservation_writer",
    )
    assert all(fragment not in lowered for fragment in forbidden_fragments)
    imports = [node for node in ast.walk(_source_tree()) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all(not any(
        token in (alias.name if isinstance(node, ast.Import) else (node.module or ""))
        for token in ("subprocess", "socket", "http", "gitpython", "worker")
        for alias in node.names
    ) for node in imports)


def test_phase2b2f_g06_tmp_only_and_repo_unchanged(tmp_path: Path) -> None:
    protected = (
        ROOT / "docs/experiments/artifacts", ROOT / "runs",
        ROOT / "docs/experiments/uprime_odlrq_u1_rerun_license_registry.json",
    )
    registry = protected[2]
    registry_preimage = (
        registry.relative_to(ROOT).as_posix().encode("utf-8")
        + b"\0"
        + b"regular\0"
        + hashlib.sha256(registry.read_bytes()).digest()
    )
    assert _repo_tree_digest((registry,)) == hashlib.sha256(
        registry_preimage
    ).hexdigest()
    exposure_roots = (
        ROOT / "docs/experiments",
        ROOT / "runs/uprime_u1_rpc_20260710",
    )
    exposure_before = _exposure_marker_inventory(exposure_roots)
    assert exposure_before == ()
    before = _repo_tree_digest(protected)
    _conflict(_fixture(tmp_path, "conflict"))
    _recover(_fixture(tmp_path, "recovery"))
    after = _repo_tree_digest(protected)
    assert before == after
    assert _exposure_marker_inventory(exposure_roots) == exposure_before
    assert str(tmp_path) not in str(ROOT)


def test_phase2b2f_g07_windows_real_filesystem_profiles(tmp_path: Path) -> None:
    conflict = _conflict(_fixture(tmp_path, "real-conflict"))
    assert conflict.outcome == "conflict_without_marker_confirmed"
    profiles = (
        "ack_loss_confirmed", "ack_loss_unavailable_then_confirmed",
        "ack_loss_unavailable_until_budget_block", "wrong_delta_confirmed",
    )
    for profile in profiles:
        row = _recover(_fixture(tmp_path, f"real-{profile}"), profile)
        assert Path(row.manifest_host_alias_path).is_file()
        assert Path(row.manifest_host_final_path).is_file()
        assert os.path.samefile(row.manifest_host_alias_path, row.manifest_host_final_path)
        assert Path(row.stage_path).read_bytes() == (fixture_payload := b"phase2b2f-proposal")
        assert row.proposed_payload_sha256 == hashlib.sha256(fixture_payload).hexdigest().upper()


def test_phase2b2f_g08_gate_ancestry_allowed_diff_and_stop_rule() -> None:
    allowed = {
        "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py",
        "tests/uprime_rpc_integrated_synthetic_manifest_cases.py",
        "tests/test_uprime_rpc_ledger.py", "lean_rgc/evals/uprime_rpc_litmus.py",
        "tests/test_uprime_rerun_license.py",
    }
    prereg_probe = subprocess.run(
        ["git", "cat-file", "-e", f"{PREREG_COMMIT}^{{commit}}"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if prereg_probe.returncode != 0:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert shallow == "true"
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        ancestry = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"], cwd=ROOT,
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.split()
        assert ancestry == [head]
        for relative in (
            "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py",
            "tests/uprime_rpc_integrated_synthetic_manifest_cases.py",
        ):
            tree_row = subprocess.run(
                ["git", "ls-tree", "HEAD", "--", relative], cwd=ROOT,
                check=True, stdout=subprocess.PIPE, text=True,
            ).stdout.split()
            assert len(tree_row) == 4
            assert tree_row[:2] == ["100644", "blob"]
            assert tree_row[3] == relative
    else:
        prereg = subprocess.run(
            ["git", "rev-parse", PREREG_COMMIT], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        assert prereg == PREREG_COMMIT
        add_commit = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%H", "--",
             "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.splitlines()
        if add_commit:
            implementation = add_commit[0]
            ancestry = subprocess.run(
                ["git", "rev-list", "--parents", "-n", "1", implementation],
                cwd=ROOT, check=True,
                stdout=subprocess.PIPE, text=True,
            ).stdout.split()
            assert ancestry == [implementation, PREREG_COMMIT]
            changed = tuple(sorted(subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "--no-renames",
                 "-r", implementation],
                cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
            ).stdout.splitlines()))
            assert changed == tuple(sorted(allowed))
            tracked_paths = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", implementation, "--",
                 "docs/experiments", "runs/uprime_u1_rpc_20260710"],
                cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True,
            ).stdout.splitlines()
            exposure_tokens = ("exposure", "burn", "retir", "read_ledger")
            assert not any(
                token in path.lower()
                for path in tracked_paths
                for token in exposure_tokens
            )
        else:
            status = subprocess.run(
                ["git", "status", "--porcelain", "--", *sorted(allowed)], cwd=ROOT,
                check=True, stdout=subprocess.PIPE, text=True,
            ).stdout
            assert "uprime_rpc_integrated_synthetic_manifest.py" in status
            assert "uprime_rpc_integrated_synthetic_manifest_cases.py" in status
    prereg_text = PREREG_PATH.read_text(encoding="utf-8")
    assert "license **Phase-2c preregistration\nonly**" in prereg_text
    assert "GPU, SSH, Lean, or registered-run execution is licensed" not in prereg_text


EXPECTED_TEST_EXPORTS = tuple(f"test_phase2b2f_{case_id}" for case_id in PHASE2B2F_CASE_IDS)
assert len(CASE_MATRIX) == len(PHASE2B2F_CASE_IDS) == len(EXPECTED_TEST_EXPORTS) == 64
assert tuple(row[0] for row in CASE_MATRIX) == PHASE2B2F_CASE_IDS
assert len(set(PHASE2B2F_CASE_IDS)) == 64
assert all(len(row) == 5 and all(type(cell) is str and cell for cell in row) for row in CASE_MATRIX)
assert tuple(name for name in globals() if name.startswith("test_phase2b2f_")) == EXPECTED_TEST_EXPORTS
assert all(callable(globals()[name]) for name in EXPECTED_TEST_EXPORTS)

__all__ = list(EXPECTED_TEST_EXPORTS)
