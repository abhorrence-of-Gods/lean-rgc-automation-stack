"""M2b phase-1b1 exact-49 schema and state validation.

This verifier accepts fully synthetic input by design.  It validates one
complete, alternating 23-frame sequence and its internally derived metadata,
but it does not authenticate a reservation token, Git object, remote claim,
runtime origin, report, or attempt manifest.  It therefore cannot confer
canonical-run or later-stage authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
from pathlib import Path
from typing import Any

from lean_rgc.evals.uprime_rpc_ledger import (
    SCHEMA_UPRIME_RPC_CHAIN_STRUCTURE_VERIFIER,
    SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD,
    STRICT_JSON_CANONICALIZER_ID,
    StandaloneLedgerStructureError,
    canonical_json_bytes,
    load_standalone_closed_chain_snapshot,
    parse_canonical_json_bytes,
)


SCHEMA_UPRIME_RPC_NOMINAL_49_SEMANTICS_VERIFIER = (
    "lean-rgc-uprime-rpc-exact-49-sequence-semantics-v0.1"
)
SCHEMA_UPRIME_RPC_PARSED_LEDGER = "lean-rgc-uprime-rpc-parsed-ledger-v1.0"
SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION = (
    "lean-rgc-uprime-rpc-bundle-reservation-v1.1"
)
SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC = (
    "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
)
SCHEMA_UPRIME_RPC_DIAGNOSTIC_REPORT = "lean-rgc-uprime-rpc-diagnostic-v1.2"
RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
EVIDENCE_SCOPE = "parsed_json_objects_and_local_probe_not_raw_wire_octets"
EXPECTED_FRAME_COUNT = 23
EXPECTED_FRAME_MANIFEST_SHA256 = (
    "03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E"
)
REGISTERED_RUN_DIR = "runs/uprime_u1_rpc_20260710"
REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
REMOTE_BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"

EXPECTED_FRAME_LABELS = (
    "load",
    "primary_init",
    "primary_split",
    "primary_split_replay",
    "primary_tail_close",
    "primary_tail_close_replay",
    "primary_head_close",
    "primary_head_close_replay",
    "zero_init",
    "zero_split",
    "zero_split_replay",
    "zero_child_close",
    "zero_child_close_replay",
    "side_init",
    "side_effect_close",
    "side_effect_close_replay",
    "burn_init",
    "burn",
    "reset_init",
    "reset",
    "reset_replay",
    "status",
    "shutdown",
)

X0_PREDICATE_IDS = (
    "stream_complete",
    "shutdown_ack_ok",
    "response_sha256_bound",
    "natural_exit_within_grace",
    "no_forced_reap",
    "returncode_zero",
    "reader_threads_drained",
    "terminal_eof_exact",
    "no_transport_overflow",
    "json_stdout_only",
    "post_response_elapsed_bounded",
    "transport_finalized",
)

CLOSURE_REASON_CODES = (
    "CLEANUP_ERROR",
    "EOF_BEFORE_EXPECTED_RESPONSE",
    "INVALID_UTF8_STDOUT",
    "NON_JSON_STDOUT",
    "NON_OBJECT_STDOUT",
    "OTHER_HARNESS_ERROR",
    "PROCESS_EXIT_BEFORE_REQUEST",
    "READER_ERROR",
    "REQUEST_TIMEOUT",
    "REQUEST_VALIDATION_ERROR",
    "REQUEST_WRITE_ERROR",
    "RESPONSE_DUPLICATE",
    "RESPONSE_LATE",
    "RESPONSE_UNSOLICITED",
    "SHUTDOWN_FINALIZATION_ERROR",
    "STDIN_UNAVAILABLE",
    "TRANSPORT_OVERFLOW",
    "WORKER_START_ERROR",
    "WORKER_TIMEOUT",
)

_HEX12_LOWER_RE = re.compile(r"[0-9a-f]{12}\Z")
_HEX40_LOWER_RE = re.compile(r"[0-9a-f]{40}\Z")
_HEX64_LOWER_RE = re.compile(r"[0-9a-f]{64}\Z")
_HEX64_UPPER_RE = re.compile(r"[0-9A-F]{64}\Z")
_UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z"
)

_CLAIM_KEYS = (
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
_HEADER_KEYS = (
    "canonicalizer_id",
    "created_at_utc",
    "evidence_scope",
    "expected_frame_labels",
    "hash_algorithm",
    "ledger_schema_version",
    "reservation",
    "reservation_sha256",
    "wire_exact",
)
_LOCAL_PROBE_KEYS = (
    "explicit_fields",
    "explicit_key",
    "key_kwargs",
    "observed_at_utc",
    "omitted_fields",
    "omitted_key",
    "payloads",
    "probe_id",
    "resolved",
    "source_blobs",
)
_REQUEST_KEYS = (
    "durability_marker",
    "expected_request_id",
    "frame_index",
    "frame_label",
    "intent_at_utc",
    "intent_monotonic_ns",
    "request",
)
_RESPONSE_KEYS = (
    "arrival_index",
    "association",
    "expected_request_id",
    "frame_index",
    "frame_label",
    "received_at_utc",
    "received_monotonic_ns",
    "response",
)
_CLOSURE_KEYS = (
    "closed_at_utc",
    "duplicate_request_frame_indices",
    "duplicate_response_frame_indices",
    "expected_frame_count",
    "expected_frame_manifest_sha256",
    "invalid_utf8_stdout_count",
    "late_response_count",
    "local_probe_count",
    "missing_request_frame_indices",
    "missing_response_frame_indices",
    "non_json_stdout_count",
    "non_object_stdout_count",
    "observed_request_frame_indices",
    "observed_response_frame_indices",
    "parsed_response_count",
    "preclosure_record_sha256",
    "primary_reason_code",
    "process_quiesced",
    "process_returncode",
    "reason_codes",
    "request_intent_count",
    "response_id_mismatch_count",
    "sequence_status",
    "shutdown_transport",
    "stderr_line_count",
    "stderr_reader_quiesced",
    "stdout_reader_quiesced",
    "transport_overflow",
    "unsolicited_response_count",
    "writer_healthy",
)
_SHUTDOWN_KEYS = (
    "exit_mode",
    "forced_reap",
    "forced_reap_budget_ns",
    "forced_reap_succeeded",
    "graceful_exit",
    "kill_signal_attempted",
    "natural_exit_grace_ns",
    "post_response_elapsed_ns",
    "post_response_timeout_ns",
    "reader_drain_reserve_ns",
    "reader_threads_drained",
    "residual_frame_kinds",
    "residual_response_count",
    "shutdown_ack_ok",
    "shutdown_response_sha256",
    "stdout_eof_count",
    "stream_complete",
    "terminal_eof_exact",
    "termination_signal_attempted",
    "transport_finalized",
)

_SOURCE_BLOB_KEYS = (
    "lean_rgc/audit_result_cache.py",
    "lean_rgc/core/ids.py",
    "lean_rgc/evals/uprime_rpc_litmus.py",
    "lean_rgc/schemas.py",
)
_B4_CASES = (
    "explicit_default",
    "explicit_nonzero",
    "explicit_zero",
    "omitted_default",
    "task_fallback",
)


class StandaloneLedgerSemanticError(ValueError):
    """The closed chain does not satisfy the phase-1b1 exact-49 semantics."""


@dataclass(frozen=True)
class StandaloneNominal49SemanticsAttestation:
    semantic_scope: str
    semantic_status: str
    origin_status: str
    verifier_schema_version: str
    chain_structure_verifier_schema_version: str
    ledger_schema_version: str
    record_schema_version: str
    input_sha256: str
    input_bytes: int
    final_chain_head: str
    record_count: int
    b4_raw_predicate: bool
    response_id_mismatch_count: int
    closure_primary_reason_code: str | None
    closure_reason_codes: tuple[str, ...]
    x0_predicate_ids: tuple[str, ...]
    x0_predicates: tuple[bool, ...]
    x0_raw_predicate_all: bool
    full_contract_recomputation: str = "not_performed"
    scientific_disposition: str = "not_computed"
    reservation_token_verification: str = "not_performed"
    source_blob_authentication: str = "not_performed"
    remote_claim_authentication: str = "not_performed"
    bundle_binding: str = "not_performed"
    report_binding: str = "not_performed"
    attempt_manifest_binding: str = "not_performed"
    privacy_scan: str = "not_performed"
    archive_verification: str = "not_performed"
    authority_scope: str = "none"
    canonical_run_authority: bool = False
    licenses_execution: bool = False
    licenses_later_stage: bool = False


def _fail(message: str) -> None:
    raise StandaloneLedgerSemanticError(message)


def _exact_object(value: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(sorted(value)) != tuple(sorted(keys)):
        _fail(f"{label} field set is invalid")
    return value


def _string(value: Any, label: str, *, nonempty: bool = False) -> str:
    if type(value) is not str or (nonempty and not value):
        _fail(f"{label} must be a{' nonempty' if nonempty else ''} string")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        _fail(f"{label} must be boolean")
    return value


def _int(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        _fail(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        _fail(f"{label} is below its minimum")
    if maximum is not None and value > maximum:
        _fail(f"{label} is above its maximum")
    return value


def _optional_int(value: Any, label: str, *, minimum: int = -(2**63)) -> int | None:
    if value is None:
        return None
    return _int(value, label, minimum=minimum, maximum=2**63 - 1)


def _regex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    text = _string(value, label)
    if pattern.fullmatch(text) is None:
        _fail(f"{label} has invalid syntax")
    return text


def _utc(value: Any, label: str) -> str:
    text = _regex(value, _UTC_RE, label)
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise StandaloneLedgerSemanticError(f"{label} is not a real UTC instant") from exc
    return text


def _uppercase_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _same_strict_json(actual: Any, expected: Any) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""

    return canonical_json_bytes(actual) == canonical_json_bytes(expected)


def _expected_request_id(frame_index: int, label: str) -> str:
    return f"uprime-{frame_index:02d}-{label}"


def _claim_receipt(value: Any) -> dict[str, Any]:
    receipt = _exact_object(value, _CLAIM_KEYS, "claim receipt")
    if receipt["schema_version"] != SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC:
        _fail("claim receipt schema is invalid")
    candidate = _regex(receipt["candidate_commit"], _HEX40_LOWER_RE, "candidate commit")
    license_commit = _regex(receipt["license_commit"], _HEX40_LOWER_RE, "license commit")
    license_id = _regex(receipt["license_id"], _HEX64_LOWER_RE, "license id")
    expected_license_id = hashlib.sha256(
        b"lean-rgc-uprime-u1-attempt-v1\0" + candidate.encode("ascii")
    ).hexdigest()
    if license_id != expected_license_id:
        _fail("license id does not derive from the candidate commit")
    if receipt["remote_url"] != REMOTE_URL:
        _fail("claim receipt remote URL is invalid")
    if receipt["remote_branch_ref"] != REMOTE_BRANCH_REF:
        _fail("claim receipt branch ref is invalid")
    if receipt["remote_claim_ref"] != f"refs/tags/uprime-u1-attempts/{license_id}":
        _fail("claim receipt tag ref is invalid")
    if receipt["remote_claim_oid"] != license_commit:
        _fail("claim receipt remote object is not the license commit")
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


def _reservation(value: Any) -> dict[str, Any]:
    reservation = _exact_object(value, _RESERVATION_KEYS, "reservation")
    if reservation["schema_version"] != SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION:
        _fail("reservation schema is invalid")
    if reservation["status"] != "LIVE_EVIDENCE_BUNDLE_RESERVED":
        _fail("reservation status is invalid")
    anchor = _regex(reservation["anchor"], _HEX12_LOWER_RE, "reservation anchor")
    candidate = _regex(
        reservation["candidate_commit"], _HEX40_LOWER_RE, "reservation candidate"
    )
    license_commit = _regex(
        reservation["license_commit"], _HEX40_LOWER_RE, "reservation license commit"
    )
    license_id = _regex(
        reservation["license_id"], _HEX64_LOWER_RE, "reservation license id"
    )
    if anchor != license_commit[:12]:
        _fail("reservation anchor is not the license-commit prefix")
    receipt = _claim_receipt(reservation["claim_receipt"])
    if (
        receipt["candidate_commit"] != candidate
        or receipt["license_commit"] != license_commit
        or receipt["license_id"] != license_id
        or receipt["remote_claim_ref"] != reservation["remote_claim_ref"]
    ):
        _fail("reservation identity differs from its claim receipt")
    receipt_digest = _uppercase_sha256(canonical_json_bytes(receipt))
    if reservation["claim_receipt_sha256"] != receipt_digest:
        _fail("reservation claim receipt digest is invalid")
    if reservation["registered_run_dir"] != REGISTERED_RUN_DIR:
        _fail("reservation run directory is invalid")
    if reservation["report_artifact_name"] != f"rpc_diagnostic_{anchor}.json":
        _fail("reservation report artifact name is invalid")
    if reservation["ledger_artifact_name"] != f"rpc_diagnostic_{anchor}.responses.jsonl":
        _fail("reservation ledger artifact name is invalid")
    if (
        reservation["reservation_artifact_name"]
        != f"rpc_diagnostic_{anchor}.json.reservation"
    ):
        _fail("reservation artifact name is invalid")
    if reservation["report_schema_version"] != SCHEMA_UPRIME_RPC_DIAGNOSTIC_REPORT:
        _fail("reservation report schema is invalid")
    if reservation["ledger_schema_version"] != SCHEMA_UPRIME_RPC_PARSED_LEDGER:
        _fail("reservation ledger schema is invalid")
    if reservation["record_schema_version"] != SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD:
        _fail("reservation record schema is invalid")
    if reservation["rpc_protocol_version"] != RPC_PROTOCOL_VERSION:
        _fail("reservation RPC protocol is invalid")
    if (
        _int(
            reservation["expected_frame_count"],
            "reservation frame count",
            minimum=EXPECTED_FRAME_COUNT,
            maximum=EXPECTED_FRAME_COUNT,
        )
        != EXPECTED_FRAME_COUNT
    ):
        _fail("reservation frame count is invalid")
    if reservation["expected_frame_manifest_sha256"] != EXPECTED_FRAME_MANIFEST_SHA256:
        _fail("reservation frame manifest is invalid")
    _regex(
        reservation["reservation_token_sha256"],
        _HEX64_UPPER_RE,
        "reservation token digest",
    )
    _utc(reservation["reserved_at_utc"], "reservation time")
    _int(reservation["process_id"], "reservation process id", minimum=1)
    return reservation


def _header(value: Any) -> dict[str, Any]:
    body = _exact_object(value, _HEADER_KEYS, "header body")
    if body["ledger_schema_version"] != SCHEMA_UPRIME_RPC_PARSED_LEDGER:
        _fail("header ledger schema is invalid")
    if body["canonicalizer_id"] != STRICT_JSON_CANONICALIZER_ID:
        _fail("header canonicalizer is invalid")
    if body["hash_algorithm"] != "SHA-256":
        _fail("header hash algorithm is invalid")
    if body["evidence_scope"] != EVIDENCE_SCOPE:
        _fail("header evidence scope is invalid")
    if body["wire_exact"] is not False:
        _fail("header must state wire_exact=false")
    reservation = _reservation(body["reservation"])
    reservation_digest = _uppercase_sha256(canonical_json_bytes(reservation) + b"\n")
    if body["reservation_sha256"] != reservation_digest:
        _fail("header reservation digest is invalid")
    if not _same_strict_json(
        body["expected_frame_labels"], list(EXPECTED_FRAME_LABELS)
    ):
        _fail("header frame-label manifest is invalid")
    _utc(body["created_at_utc"], "header creation time")
    return reservation


def _expected_b4_payloads() -> dict[str, Any]:
    base = {"task_id": "cache", "statement": "True", "imports": ["Lean"]}
    return {
        "task_fallback": {
            "task": {**base, "max_heartbeats": 731},
            "action": {"tactic": "trivial"},
        },
        "explicit_zero": {
            "task": {**base, "max_heartbeats": 731},
            "action": {"tactic": "trivial", "max_heartbeats": 0},
        },
        "explicit_nonzero": {
            "task": {**base, "max_heartbeats": 731},
            "action": {"tactic": "trivial", "max_heartbeats": 123_456},
        },
        "omitted_default": {
            "task": dict(base),
            "action": {"tactic": "trivial"},
        },
        "explicit_default": {
            "task": {**base, "max_heartbeats": 200_000},
            "action": {"tactic": "trivial"},
        },
    }


def _local_probe(value: Any) -> bool:
    body = _exact_object(value, _LOCAL_PROBE_KEYS, "local probe body")
    if body["probe_id"] != "B4_cache_budget_semantics":
        _fail("local probe id is invalid")
    if not _same_strict_json(body["payloads"], _expected_b4_payloads()):
        _fail("local probe payloads differ from the frozen inputs")
    expected_kwargs = {
        "lean_version": "uprime-cache-probe",
        "workdir_fingerprint_value": "uprime-cache-probe",
        "import_mode": "preserve",
        "trace_state": False,
        "lane": "kernel_rpc",
    }
    if not _same_strict_json(body["key_kwargs"], expected_kwargs):
        _fail("local probe key kwargs differ from the frozen inputs")
    resolved = _exact_object(body["resolved"], _B4_CASES, "local probe resolved")
    for name, item in resolved.items():
        if item is not None and type(item) is not str:
            _fail(f"local probe resolved value {name} has an invalid type")
    omitted_key = _string(body["omitted_key"], "omitted cache key")
    explicit_key = _string(body["explicit_key"], "explicit cache key")
    if type(body["omitted_fields"]) is not dict:
        _fail("omitted cache fields must be an object")
    if type(body["explicit_fields"]) is not dict:
        _fail("explicit cache fields must be an object")
    source_blobs = _exact_object(
        body["source_blobs"], _SOURCE_BLOB_KEYS, "local probe source blobs"
    )
    for source_path, row in source_blobs.items():
        item = _exact_object(
            row, ("git_blob_oid", "head_blob_sha256"), f"source blob {source_path}"
        )
        _regex(item["git_blob_oid"], _HEX40_LOWER_RE, f"{source_path} blob oid")
        _regex(
            item["head_blob_sha256"],
            _HEX64_UPPER_RE,
            f"{source_path} blob sha256",
        )
    _utc(body["observed_at_utc"], "local probe time")
    return bool(
        resolved["task_fallback"] == "731"
        and resolved["explicit_zero"] == "0"
        and resolved["explicit_nonzero"] == "123456"
        and resolved["omitted_default"] == "200000"
        and omitted_key == explicit_key
        and body["omitted_fields"].get("max_heartbeats") == "200000"
        and body["explicit_fields"].get("max_heartbeats") == "200000"
    )


def _task(task_id: str, statement: str, *, prefix: str = "") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "statement": statement,
        "imports": ["Lean"],
        "prefix": prefix,
        "max_heartbeats": 731,
        "episode_max_heartbeats_counter": 1_000_000,
    }


def _response_state_id(response: dict[str, Any], *, after: bool = False) -> str:
    if after and type(response.get("after_state_id")) is str:
        return response["after_state_id"]
    state = response.get("state")
    if type(state) is not dict:
        _fail("response state is missing")
    return _string(state.get("state_id"), "response state_id", nonempty=True)


def _raw_expected_after_state_id(response: dict[str, Any]) -> Any:
    return response.get("after_state_id")


def _filtered_response_goal_ids(
    response: dict[str, Any], *, after: bool = False
) -> tuple[str, str]:
    field = "kernel_state_after" if after else "kernel_state"
    kernel = response.get(field)
    goal_rows = kernel.get("goals") if type(kernel) is dict else None
    if type(goal_rows) is not list:
        goal_rows = []
    ids = [
        row["mvar_id"]
        for row in goal_rows
        if type(row) is dict and type(row.get("mvar_id")) is str
    ]
    if len(ids) != 2:
        _fail(f"response {field} must expose exactly two filtered goal ids")
    return ids[0], ids[1]


def _side_effect_target(response: dict[str, Any]) -> str:
    kernel = response.get("kernel_state")
    goals = kernel.get("goals") if type(kernel) is dict else None
    if not (
        type(goals) is list
        and len(goals) == 2
        and all(
            type(row) is dict
            and type(row.get("mvar_id")) is str
            and bool(row["mvar_id"])
            for row in goals
        )
        and goals[0]["mvar_id"] != goals[1]["mvar_id"]
    ):
        _fail("side-effect response does not satisfy the frozen target selector")
    return goals[1]["mvar_id"]


def _expected_request(
    frame_index: int,
    label: str,
    responses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    request_id = _expected_request_id(frame_index, label)
    if label == "load":
        payload = {"cmd": "load_project", "imports": ["Lean"]}
    elif label == "primary_init":
        payload = {"cmd": "init_state", "task": _task("uprime_primary", "True ∧ True")}
    elif label == "primary_split":
        payload = {
            "cmd": "apply_tactic",
            "state_id": _response_state_id(responses["primary_init"]),
            "action": {
                "action_id": "primary_constructor",
                "tactic": "constructor",
                "max_heartbeats": 123_456,
            },
        }
    elif label == "primary_split_replay":
        before = _response_state_id(responses["primary_init"])
        payload = {
            "cmd": "replay_transition",
            "before_state_id": before,
            "expected_after_state_id": _raw_expected_after_state_id(
                responses["primary_split"]
            ),
            "action": {
                "action_id": "primary_constructor",
                "tactic": "constructor",
                "max_heartbeats": 123_456,
            },
        }
    elif label in {"primary_tail_close", "primary_tail_close_replay"}:
        _head, tail = _filtered_response_goal_ids(
            responses["primary_split"], after=True
        )
        action = {"action_id": "primary_tail_exact", "tactic": "exact True.intro"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(
                    responses["primary_split"], after=True
                ),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["primary_tail_close"]
                ),
                "action": action,
                "target_mvar_id": tail,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["primary_split"], after=True),
                "action": action,
                "target_mvar_id": tail,
            }
    elif label in {"primary_head_close", "primary_head_close_replay"}:
        head, _tail = _filtered_response_goal_ids(
            responses["primary_split"], after=True
        )
        action = {"action_id": "primary_head_exact", "tactic": "exact True.intro"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(
                    responses["primary_tail_close"], after=True
                ),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["primary_head_close"]
                ),
                "action": action,
                "target_mvar_id": head,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(
                    responses["primary_tail_close"], after=True
                ),
                "action": action,
                "target_mvar_id": head,
            }
    elif label == "zero_init":
        payload = {"cmd": "init_state", "task": _task("uprime_zero", "True ∧ True")}
    elif label in {"zero_split", "zero_split_replay"}:
        action = {
            "action_id": "zero_constructor",
            "tactic": "constructor",
            "max_heartbeats": 0,
        }
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["zero_init"]),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["zero_split"]
                ),
                "action": action,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["zero_init"]),
                "action": action,
            }
    elif label in {"zero_child_close", "zero_child_close_replay"}:
        _head, tail = _filtered_response_goal_ids(responses["zero_split"], after=True)
        action = {"action_id": "zero_child_exact", "tactic": "exact True.intro"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["zero_split"], after=True),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["zero_child_close"]
                ),
                "action": action,
                "target_mvar_id": tail,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["zero_split"], after=True),
                "action": action,
                "target_mvar_id": tail,
            }
    elif label == "side_init":
        payload = {
            "cmd": "init_state",
            "task": _task(
                "uprime_side_effect", "∃ n : Nat, n = 0", prefix="refine ⟨?_, ?_⟩"
            ),
        }
    elif label in {"side_effect_close", "side_effect_close_replay"}:
        equality = _side_effect_target(responses["side_init"])
        action = {"action_id": "side_effect_rfl", "tactic": "rfl"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["side_init"]),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["side_effect_close"]
                ),
                "action": action,
                "target_mvar_id": equality,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["side_init"]),
                "action": action,
                "target_mvar_id": equality,
            }
    elif label == "burn_init":
        payload = {"cmd": "init_state", "task": _task("uprime_burn", "True")}
    elif label == "burn":
        payload = {
            "cmd": "apply_tactic",
            "state_id": _response_state_id(responses["burn_init"]),
            "action": {
                "action_id": "burn",
                "tactic": (
                    'run_tac do IO.addHeartbeats 400000000; '
                    'Lean.Core.checkMaxHeartbeats "uprime-litmus"'
                ),
                "max_heartbeats": 200_000,
            },
        }
    elif label == "reset_init":
        payload = {"cmd": "init_state", "task": _task("uprime_reset", "True")}
    elif label in {"reset", "reset_replay"}:
        action = {
            "action_id": "reset_trivial",
            "tactic": "trivial",
            "max_heartbeats": 200_000,
        }
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["reset_init"]),
                "expected_after_state_id": _raw_expected_after_state_id(
                    responses["reset"]
                ),
                "action": action,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["reset_init"]),
                "action": action,
            }
    elif label == "status":
        payload = {"cmd": "status"}
    elif label == "shutdown":
        payload = {"cmd": "shutdown"}
    else:
        raise AssertionError(f"unhandled frozen request label: {label}")
    return {"id": request_id, **payload}


def _request_body(
    value: Any,
    *,
    frame_index: int,
    label: str,
    responses: dict[str, dict[str, Any]],
    last_monotonic_ns: int,
) -> int:
    body = _exact_object(value, _REQUEST_KEYS, f"request {label}")
    request_id = _expected_request_id(frame_index, label)
    if _int(body["frame_index"], f"request {label} frame index") != frame_index:
        _fail(f"request {label} frame index is invalid")
    if body["frame_label"] != label:
        _fail(f"request {label} frame label is invalid")
    if body["expected_request_id"] != request_id:
        _fail(f"request {label} expected id is invalid")
    if not _same_strict_json(
        body["request"], _expected_request(frame_index, label, responses)
    ):
        _fail(f"request {label} object differs from the frozen dynamic request")
    _utc(body["intent_at_utc"], f"request {label} intent time")
    monotonic = _int(
        body["intent_monotonic_ns"], f"request {label} monotonic time", minimum=0
    )
    if monotonic < last_monotonic_ns:
        _fail(f"request {label} monotonic time moves backwards")
    if body["durability_marker"] != "durable_send_intent_before_stdin_write":
        _fail(f"request {label} durability marker is invalid")
    return monotonic


def _response_body(
    value: Any,
    *,
    frame_index: int,
    label: str,
    request_monotonic_ns: int,
) -> tuple[int, dict[str, Any], bool]:
    body = _exact_object(value, _RESPONSE_KEYS, f"response {label}")
    request_id = _expected_request_id(frame_index, label)
    if _int(body["arrival_index"], f"response {label} arrival index") != frame_index:
        _fail(f"response {label} arrival index is invalid")
    if body["association"] != "active_frame":
        _fail(f"response {label} is outside the exact-49 active-frame scope")
    if _int(body["frame_index"], f"response {label} frame index") != frame_index:
        _fail(f"response {label} frame index is invalid")
    if body["frame_label"] != label:
        _fail(f"response {label} frame label is invalid")
    if body["expected_request_id"] != request_id:
        _fail(f"response {label} expected id is invalid")
    response = body["response"]
    if type(response) is not dict:
        _fail(f"response {label} payload must be an object")
    _utc(body["received_at_utc"], f"response {label} receipt time")
    monotonic = _int(
        body["received_monotonic_ns"],
        f"response {label} monotonic time",
        minimum=0,
    )
    if monotonic < request_monotonic_ns:
        _fail(f"response {label} predates its durable request intent")
    return monotonic, response, response.get("id") != request_id


def _shutdown_transport(
    value: Any,
    *,
    shutdown_response: dict[str, Any],
    process_returncode: int | None,
    transport_overflow: bool,
    non_json_stdout_count: int,
    stdout_reader_quiesced: bool,
    stderr_reader_quiesced: bool,
) -> tuple[bool, ...]:
    body = _exact_object(value, _SHUTDOWN_KEYS, "shutdown transport")
    for key in (
        "stream_complete",
        "shutdown_ack_ok",
        "termination_signal_attempted",
        "kill_signal_attempted",
        "forced_reap",
        "reader_threads_drained",
        "terminal_eof_exact",
        "transport_finalized",
    ):
        _bool(body[key], f"shutdown {key}")
    expected_ack = bool(
        shutdown_response.get("ok") is True
        and shutdown_response.get("shutdown") is True
        and shutdown_response.get("error") is None
    )
    if body["shutdown_ack_ok"] is not expected_ack:
        _fail("shutdown acknowledgment summary contradicts the response")
    response_digest = _uppercase_sha256(canonical_json_bytes(shutdown_response))
    stored_response_digest = body["shutdown_response_sha256"]
    if stored_response_digest is not None:
        _regex(
            stored_response_digest,
            _HEX64_UPPER_RE,
            "shutdown response digest",
        )
    if (
        _int(body["post_response_timeout_ns"], "shutdown post-response timeout")
        != 10_000_000_000
    ):
        _fail("shutdown post-response timeout is invalid")
    if (
        _int(body["natural_exit_grace_ns"], "shutdown natural-exit grace")
        != 5_000_000_000
    ):
        _fail("shutdown natural-exit grace is invalid")
    if (
        _int(body["forced_reap_budget_ns"], "shutdown forced-reap budget")
        != 4_000_000_000
    ):
        _fail("shutdown forced-reap budget is invalid")
    if (
        _int(body["reader_drain_reserve_ns"], "shutdown reader-drain reserve")
        != 1_000_000_000
    ):
        _fail("shutdown reader-drain reserve is invalid")
    exit_mode = body["exit_mode"]
    if exit_mode not in {
        None,
        "natural",
        "natural_after_grace",
        "forced_terminate",
        "forced_kill",
    }:
        _fail("shutdown exit mode is invalid")
    graceful = body["graceful_exit"]
    if graceful is not None and type(graceful) is not bool:
        _fail("shutdown graceful_exit has an invalid type")
    forced_success = body["forced_reap_succeeded"]
    if forced_success is not None and type(forced_success) is not bool:
        _fail("shutdown forced_reap_succeeded has an invalid type")
    termination = body["termination_signal_attempted"]
    kill = body["kill_signal_attempted"]
    forced = body["forced_reap"]
    if kill and not termination:
        _fail("shutdown kill signal lacks a preceding termination signal")
    if forced:
        if not termination or graceful is not False or forced_success is None:
            _fail("shutdown forced-reap lifecycle is inconsistent")
        if exit_mode == "forced_terminate":
            if kill or forced_success is not True:
                _fail("forced-terminate lifecycle is inconsistent")
        elif exit_mode == "forced_kill":
            if not kill or forced_success is not True:
                _fail("forced-kill lifecycle is inconsistent")
        elif exit_mode in {"natural", "natural_after_grace"}:
            _fail("forced reap cannot have a natural exit mode")
    else:
        if termination or kill or forced_success is not None:
            _fail("non-forced shutdown carries forced-reap telemetry")
        if exit_mode in {"forced_terminate", "forced_kill"}:
            _fail("forced exit mode lacks forced-reap telemetry")
        if exit_mode == "natural" and graceful is not True:
            _fail("natural exit must be graceful")
        if exit_mode == "natural_after_grace" and graceful is not False:
            _fail("late natural exit cannot be graceful")
        if exit_mode is None and graceful not in {None, False}:
            _fail("unknown exit mode cannot claim graceful exit")
    if body["reader_threads_drained"] is not (
        stdout_reader_quiesced and stderr_reader_quiesced
    ):
        _fail("shutdown reader-drain summary contradicts closure quiescence")
    stdout_eof_count = _int(body["stdout_eof_count"], "stdout EOF count", minimum=0)
    residual_count = _int(
        body["residual_response_count"], "residual response count", minimum=0
    )
    kinds = body["residual_frame_kinds"]
    if type(kinds) is not list or not all(type(item) is str for item in kinds):
        _fail("residual frame kinds must be a string array")
    if residual_count != 0:
        _fail("exact-49 ledger cannot omit residual parsed-response records")
    if stdout_eof_count not in {0, 1} or kinds != (["eof"] if stdout_eof_count else []):
        _fail("shutdown EOF count and residual kinds are inconsistent")
    expected_terminal_eof = stdout_eof_count == 1 and kinds == ["eof"]
    if body["terminal_eof_exact"] is not expected_terminal_eof:
        _fail("shutdown terminal EOF summary is inconsistent")
    elapsed = _optional_int(
        body["post_response_elapsed_ns"],
        "shutdown post-response elapsed",
        minimum=0,
    )
    return (
        body["stream_complete"] is True,
        body["shutdown_ack_ok"] is True,
        stored_response_digest == response_digest,
        graceful is True and exit_mode == "natural",
        forced is False,
        process_returncode == 0,
        body["reader_threads_drained"] is True,
        body["terminal_eof_exact"] is True,
        transport_overflow is False,
        non_json_stdout_count == 0,
        elapsed is not None and 0 <= elapsed <= 10_000_000_000,
        body["transport_finalized"] is True,
    )


def _closure(
    value: Any,
    *,
    preclosure_record_sha256: str,
    shutdown_response: dict[str, Any],
    response_id_mismatch_count: int,
) -> tuple[tuple[bool, ...], str | None, tuple[str, ...]]:
    body = _exact_object(value, _CLOSURE_KEYS, "closure body")
    if body["sequence_status"] != "complete":
        _fail("exact-49 sequence must close as complete")
    reasons = body["reason_codes"]
    if (
        type(reasons) is not list
        or not all(type(item) is str and item in CLOSURE_REASON_CODES for item in reasons)
        or reasons != sorted(set(reasons))
    ):
        _fail("closure reason codes are not sorted unique frozen codes")
    expected_primary = reasons[0] if reasons else None
    if body["primary_reason_code"] != expected_primary:
        _fail("closure primary reason does not derive from reason codes")
    _utc(body["closed_at_utc"], "closure time")
    if body["preclosure_record_sha256"] != preclosure_record_sha256:
        _fail("closure preclosure digest is invalid")
    expected_indices = list(range(1, EXPECTED_FRAME_COUNT + 1))
    exact_values = {
        "local_probe_count": 1,
        "request_intent_count": EXPECTED_FRAME_COUNT,
        "parsed_response_count": EXPECTED_FRAME_COUNT,
        "expected_frame_count": EXPECTED_FRAME_COUNT,
        "expected_frame_manifest_sha256": EXPECTED_FRAME_MANIFEST_SHA256,
        "observed_request_frame_indices": expected_indices,
        "observed_response_frame_indices": expected_indices,
        "missing_request_frame_indices": [],
        "missing_response_frame_indices": [],
        "duplicate_request_frame_indices": [],
        "duplicate_response_frame_indices": [],
        "unsolicited_response_count": 0,
        "late_response_count": 0,
        "response_id_mismatch_count": response_id_mismatch_count,
    }
    for key, expected in exact_values.items():
        if not _same_strict_json(body[key], expected):
            _fail(f"closure {key} contradicts the exact-49 record sequence")
    invalid_utf8 = _int(
        body["invalid_utf8_stdout_count"], "invalid UTF-8 stdout count", minimum=0
    )
    non_json = _int(body["non_json_stdout_count"], "non-JSON stdout count", minimum=0)
    non_object = _int(
        body["non_object_stdout_count"], "non-object stdout count", minimum=0
    )
    if invalid_utf8 + non_object > non_json:
        _fail("closure stdout subcounts exceed the non-JSON aggregate")
    json_decode_count = non_json - invalid_utf8 - non_object
    impossible_complete_reasons = {
        "EOF_BEFORE_EXPECTED_RESPONSE",
        "PROCESS_EXIT_BEFORE_REQUEST",
        "REQUEST_TIMEOUT",
        "REQUEST_VALIDATION_ERROR",
        "REQUEST_WRITE_ERROR",
        "RESPONSE_DUPLICATE",
        "RESPONSE_LATE",
        "RESPONSE_UNSOLICITED",
        "STDIN_UNAVAILABLE",
        "WORKER_START_ERROR",
        "WORKER_TIMEOUT",
    }
    if impossible_complete_reasons.intersection(reasons):
        _fail("closure reason contradicts the complete exact-49 sequence")
    reason_counter_relations = {
        "INVALID_UTF8_STDOUT": invalid_utf8 > 0,
        "NON_JSON_STDOUT": json_decode_count > 0,
        "NON_OBJECT_STDOUT": non_object > 0,
    }
    for reason, observed in reason_counter_relations.items():
        if (reason in reasons) is not observed:
            _fail(f"closure reason {reason} contradicts its stdout counter")
    _int(body["stderr_line_count"], "stderr line count", minimum=0)
    transport_overflow = _bool(body["transport_overflow"], "transport overflow")
    if ("TRANSPORT_OVERFLOW" in reasons) is not transport_overflow:
        _fail("closure transport-overflow reason contradicts its flag")
    process_returncode = _optional_int(body["process_returncode"], "process returncode")
    process_quiesced = _bool(body["process_quiesced"], "process quiesced")
    stdout_quiesced = _bool(body["stdout_reader_quiesced"], "stdout reader quiesced")
    stderr_quiesced = _bool(body["stderr_reader_quiesced"], "stderr reader quiesced")
    if not (process_quiesced and stdout_quiesced and stderr_quiesced):
        _fail("structurally closed ledger is not fully quiesced")
    if body["writer_healthy"] is not True:
        _fail("structurally closed ledger does not have a healthy writer")
    return (
        _shutdown_transport(
            body["shutdown_transport"],
            shutdown_response=shutdown_response,
            process_returncode=process_returncode,
            transport_overflow=transport_overflow,
            non_json_stdout_count=non_json,
            stdout_reader_quiesced=stdout_quiesced,
            stderr_reader_quiesced=stderr_quiesced,
        ),
        expected_primary,
        tuple(reasons),
    )


def attest_standalone_nominal_49_semantics(
    path: str | Path,
) -> StandaloneNominal49SemanticsAttestation:
    """Validate one synthetic-capable exact-49 sequence without authority."""

    try:
        snapshot = load_standalone_closed_chain_snapshot(path)
    except StandaloneLedgerStructureError as exc:
        raise StandaloneLedgerSemanticError("ledger chain structure is invalid") from exc
    if len(snapshot.canonical_record_bytes) != 49:
        _fail("exact-49 semantic verifier requires exactly 49 records")
    records: list[dict[str, Any]] = []
    for raw in snapshot.canonical_record_bytes:
        value = parse_canonical_json_bytes(raw)
        if type(value) is not dict:
            _fail("ledger record is not an object")
        records.append(value)
    expected_types = ["header", "local_probe"]
    for _label in EXPECTED_FRAME_LABELS:
        expected_types.extend(("request_intent", "parsed_response"))
    expected_types.append("closure")
    if [record["record_type"] for record in records] != expected_types:
        _fail("record type sequence is not the frozen exact-49 state machine")

    _header(records[0]["body"])
    b4_raw_predicate = _local_probe(records[1]["body"])
    responses: dict[str, dict[str, Any]] = {}
    last_monotonic_ns = 0
    response_id_mismatch_count = 0
    for frame_index, label in enumerate(EXPECTED_FRAME_LABELS, start=1):
        request_record = records[2 * frame_index]
        response_record = records[2 * frame_index + 1]
        request_monotonic_ns = _request_body(
            request_record["body"],
            frame_index=frame_index,
            label=label,
            responses=responses,
            last_monotonic_ns=last_monotonic_ns,
        )
        received_monotonic_ns, response, id_mismatch = _response_body(
            response_record["body"],
            frame_index=frame_index,
            label=label,
            request_monotonic_ns=request_monotonic_ns,
        )
        last_monotonic_ns = received_monotonic_ns
        response_id_mismatch_count += int(id_mismatch)
        responses[label] = response
    x0_predicates, primary_reason_code, reason_codes = _closure(
        records[-1]["body"],
        preclosure_record_sha256=records[-2]["record_sha256"],
        shutdown_response=responses["shutdown"],
        response_id_mismatch_count=response_id_mismatch_count,
    )
    if len(x0_predicates) != len(X0_PREDICATE_IDS):
        raise AssertionError("X0 predicate registry drifted")
    chain = snapshot.attestation
    return StandaloneNominal49SemanticsAttestation(
        semantic_scope="standalone_exact_49_sequence_semantics_only",
        semantic_status="valid_exact_49_sequence",
        origin_status="unknown_may_be_synthetic",
        verifier_schema_version=SCHEMA_UPRIME_RPC_NOMINAL_49_SEMANTICS_VERIFIER,
        chain_structure_verifier_schema_version=(
            SCHEMA_UPRIME_RPC_CHAIN_STRUCTURE_VERIFIER
        ),
        ledger_schema_version=SCHEMA_UPRIME_RPC_PARSED_LEDGER,
        record_schema_version=SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD,
        input_sha256=chain.input_sha256,
        input_bytes=chain.input_bytes,
        final_chain_head=chain.final_chain_head,
        record_count=chain.record_count,
        b4_raw_predicate=b4_raw_predicate,
        response_id_mismatch_count=response_id_mismatch_count,
        closure_primary_reason_code=primary_reason_code,
        closure_reason_codes=reason_codes,
        x0_predicate_ids=X0_PREDICATE_IDS,
        x0_predicates=x0_predicates,
        x0_raw_predicate_all=all(x0_predicates),
    )


__all__ = [
    "CLOSURE_REASON_CODES",
    "EXPECTED_FRAME_COUNT",
    "EXPECTED_FRAME_LABELS",
    "EXPECTED_FRAME_MANIFEST_SHA256",
    "SCHEMA_UPRIME_RPC_NOMINAL_49_SEMANTICS_VERIFIER",
    "StandaloneLedgerSemanticError",
    "StandaloneNominal49SemanticsAttestation",
    "X0_PREDICATE_IDS",
    "attest_standalone_nominal_49_semantics",
]
