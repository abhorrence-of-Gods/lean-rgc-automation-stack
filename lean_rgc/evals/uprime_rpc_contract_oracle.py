"""Independent M2b phase-1b2 raw-contract oracle.

The oracle deliberately accepts fully synthetic, internally consistent ledger
bytes.  It authenticates neither their runtime origin nor any surrounding
bundle, report, reservation token, or remote claim, and it grants no execution
or later-stage authority.

Only the strict JSON/chain snapshot substrate is shared with phase 1a.  Exact
49-record semantics and all eleven contract predicates are independently
revalidated in this module; in particular this module must not depend on the
phase-1b1 semantic verifier or the production diagnostic evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from lean_rgc.evals.uprime_rpc_ledger import (
    STRICT_JSON_CANONICALIZER_ID,
    StandaloneLedgerStructureError,
    canonical_json_bytes,
    load_standalone_closed_chain_snapshot,
    parse_canonical_json_bytes,
)


SCHEMA_UPRIME_RPC_EXACT_49_CONTRACT_ORACLE = (
    "lean-rgc-uprime-rpc-exact-49-contract-oracle-v0.1"
)
ORACLE_SCOPE = "standalone_exact_49_raw_contract_predicates_only"

CONTRACT_IDS = (
    "R0_request_id_echo",
    "B0_task_budget_init",
    "B1_action_budget_nonsticky",
    "B2_budget_telemetry",
    "B3_enforcement_reset",
    "B4_cache_budget_semantics",
    "D0_target_routing",
    "D1_transition_delta",
    "D2_all_goal_sweep",
    "R1_independent_replay",
    "E0_episode_budget",
)

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

RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
REPLAY_CERTIFICATE_VERSION = "lean-rgc-kernel-replay-certificate-v1"
REPLAY_VERIFICATION_METHOD = "same_before_state_independent_reexecution"
TASK_MAX_HEARTBEATS_OPTION = 731
EPISODE_MAX_HEARTBEATS_COUNTER = 1_000_000
CONSTRUCTOR_MAX_HEARTBEATS_OPTION = 123_456
BURN_MAX_HEARTBEATS_OPTION = 200_000
EXPECTED_PERSISTENT_STATE_COUNT = 13
EXPECTED_STATUS_REQUEST_COUNT = 22

SCHEMA_UPRIME_RPC_PARSED_LEDGER = "lean-rgc-uprime-rpc-parsed-ledger-v1.0"
SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD = (
    "lean-rgc-uprime-rpc-parsed-ledger-record-v1.0"
)
SCHEMA_UPRIME_RPC_BUNDLE_RESERVATION = (
    "lean-rgc-uprime-rpc-bundle-reservation-v1.1"
)
SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC = (
    "lean-rgc-uprime-u1-claim-receipt-public-v1.0"
)
SCHEMA_UPRIME_RPC_DIAGNOSTIC_REPORT = "lean-rgc-uprime-rpc-diagnostic-v1.2"
EVIDENCE_SCOPE = "parsed_json_objects_and_local_probe_not_raw_wire_octets"
EXPECTED_FRAME_COUNT = 23
EXPECTED_FRAME_MANIFEST_SHA256 = (
    "03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E"
)
REGISTERED_RUN_DIR = "runs/uprime_u1_rpc_20260710"
REMOTE_URL = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
REMOTE_BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"

ACTION_LABELS = (
    "primary_split",
    "primary_tail_close",
    "primary_head_close",
    "zero_split",
    "zero_child_close",
    "side_effect_close",
    "burn",
    "reset",
)
DELTA_LABELS = tuple(label for label in ACTION_LABELS if label != "burn")
INIT_LABELS = ("primary_init", "zero_init", "side_init", "burn_init", "reset_init")
REPLAY_PAIRS = (
    ("primary_split", "primary_split_replay"),
    ("primary_tail_close", "primary_tail_close_replay"),
    ("primary_head_close", "primary_head_close_replay"),
    ("zero_split", "zero_split_replay"),
    ("zero_child_close", "zero_child_close_replay"),
    ("side_effect_close", "side_effect_close_replay"),
    ("reset", "reset_replay"),
)
EPISODE_GROUPS = (
    ("primary_split", "primary_tail_close", "primary_head_close"),
    ("zero_split", "zero_child_close"),
    ("side_effect_close",),
    ("burn",),
    ("reset",),
)

_HEX12_LOWER_RE = re.compile(r"[0-9a-f]{12}\Z")
_HEX40_LOWER_RE = re.compile(r"[0-9a-f]{40}\Z")
_HEX64_LOWER_RE = re.compile(r"[0-9a-f]{64}\Z")
_HEX64_UPPER_RE = re.compile(r"[0-9A-F]{64}\Z")
_ASCII_DIGITS_RE = re.compile(r"[0-9]+\Z", flags=re.ASCII)
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
_BUDGET_KEYS = (
    "effective_max_heartbeats_option",
    "effective_max_heartbeats_counter",
    "unlimited",
    "source",
    "consumed_heartbeats_counter",
    "episode_max_heartbeats_counter",
    "episode_remaining_heartbeats_counter",
    "episode_source",
    "measurement_scope",
    "reset_scope",
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


class StandaloneExact49ContractOracleError(ValueError):
    """The snapshot cannot produce a phase-1b2 contract vector."""


@dataclass(frozen=True)
class StandaloneExact49ContractOracleAttestation:
    oracle_schema_version: str
    oracle_scope: str
    origin_status: str
    input_sha256: str
    input_bytes: int
    final_chain_head: str
    record_count: int
    contract_ids: tuple[str, ...]
    contract_passes: tuple[bool, ...]
    contract_failure_ids: tuple[str, ...]
    raw_all_contracts: bool
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


@dataclass(frozen=True)
class _Exact49Evidence:
    requests: dict[str, dict[str, Any]]
    responses: dict[str, dict[str, Any]]
    b4_raw_predicate: bool


def _fail(message: str) -> None:
    raise StandaloneExact49ContractOracleError(message)


def _exact_object(value: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(sorted(value)) != tuple(sorted(keys)):
        _fail(f"{label} field set is invalid")
    return value


def _string(value: Any, label: str, *, nonempty: bool = False) -> str:
    if type(value) is not str or (nonempty and not value):
        qualifier = " nonempty" if nonempty else ""
        _fail(f"{label} must be a{qualifier} string")
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
        raise StandaloneExact49ContractOracleError(
            f"{label} is not a real UTC instant"
        ) from exc
    return text


def _sha256_upper(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _strict_equal(actual: Any, expected: Any) -> bool:
    return canonical_json_bytes(actual) == canonical_json_bytes(expected)


def _expected_request_id(frame_index: int, label: str) -> str:
    return f"uprime-{frame_index:02d}-{label}"


def _claim_receipt(value: Any) -> dict[str, Any]:
    receipt = _exact_object(value, _CLAIM_KEYS, "claim receipt")
    if receipt["schema_version"] != SCHEMA_UPRIME_U1_CLAIM_RECEIPT_PUBLIC:
        _fail("claim receipt schema is invalid")
    candidate = _regex(receipt["candidate_commit"], _HEX40_LOWER_RE, "candidate commit")
    license_commit = _regex(
        receipt["license_commit"], _HEX40_LOWER_RE, "license commit"
    )
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
        reservation["license_commit"],
        _HEX40_LOWER_RE,
        "reservation license commit",
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
    receipt_digest = _sha256_upper(canonical_json_bytes(receipt))
    if reservation["claim_receipt_sha256"] != receipt_digest:
        _fail("reservation claim receipt digest is invalid")
    if reservation["registered_run_dir"] != REGISTERED_RUN_DIR:
        _fail("reservation run directory is invalid")
    if reservation["report_artifact_name"] != f"rpc_diagnostic_{anchor}.json":
        _fail("reservation report artifact name is invalid")
    if reservation["ledger_artifact_name"] != (
        f"rpc_diagnostic_{anchor}.responses.jsonl"
    ):
        _fail("reservation ledger artifact name is invalid")
    if reservation["reservation_artifact_name"] != (
        f"rpc_diagnostic_{anchor}.json.reservation"
    ):
        _fail("reservation artifact name is invalid")
    if reservation["report_schema_version"] != SCHEMA_UPRIME_RPC_DIAGNOSTIC_REPORT:
        _fail("reservation report schema is invalid")
    if reservation["ledger_schema_version"] != SCHEMA_UPRIME_RPC_PARSED_LEDGER:
        _fail("reservation ledger schema is invalid")
    if (
        reservation["record_schema_version"]
        != SCHEMA_UPRIME_RPC_PARSED_LEDGER_RECORD
    ):
        _fail("reservation record schema is invalid")
    if reservation["rpc_protocol_version"] != RPC_PROTOCOL_VERSION:
        _fail("reservation RPC protocol is invalid")
    _int(
        reservation["expected_frame_count"],
        "reservation frame count",
        minimum=EXPECTED_FRAME_COUNT,
        maximum=EXPECTED_FRAME_COUNT,
    )
    if reservation["expected_frame_manifest_sha256"] != (
        EXPECTED_FRAME_MANIFEST_SHA256
    ):
        _fail("reservation frame manifest is invalid")
    _regex(
        reservation["reservation_token_sha256"],
        _HEX64_UPPER_RE,
        "reservation token digest",
    )
    _utc(reservation["reserved_at_utc"], "reservation time")
    _int(reservation["process_id"], "reservation process id", minimum=1)
    return reservation


def _validate_header(value: Any) -> None:
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
    if body["reservation_sha256"] != _sha256_upper(
        canonical_json_bytes(reservation) + b"\n"
    ):
        _fail("header reservation digest is invalid")
    if not _strict_equal(body["expected_frame_labels"], list(EXPECTED_FRAME_LABELS)):
        _fail("header frame-label manifest is invalid")
    _utc(body["created_at_utc"], "header creation time")


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


def _validate_local_probe(value: Any) -> bool:
    body = _exact_object(value, _LOCAL_PROBE_KEYS, "local probe body")
    if body["probe_id"] != "B4_cache_budget_semantics":
        _fail("local probe id is invalid")
    if not _strict_equal(body["payloads"], _expected_b4_payloads()):
        _fail("local probe payloads differ from the frozen inputs")
    expected_kwargs = {
        "lean_version": "uprime-cache-probe",
        "workdir_fingerprint_value": "uprime-cache-probe",
        "import_mode": "preserve",
        "trace_state": False,
        "lane": "kernel_rpc",
    }
    if not _strict_equal(body["key_kwargs"], expected_kwargs):
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
        "max_heartbeats": TASK_MAX_HEARTBEATS_OPTION,
        "episode_max_heartbeats_counter": EPISODE_MAX_HEARTBEATS_COUNTER,
    }


def _response_state_id(response: dict[str, Any], *, after: bool = False) -> str:
    if after and type(response.get("after_state_id")) is str:
        return response["after_state_id"]
    state = response.get("state")
    if type(state) is not dict:
        _fail("response state is missing")
    return _string(state.get("state_id"), "response state_id", nonempty=True)


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
        payload: dict[str, Any] = {"cmd": "load_project", "imports": ["Lean"]}
    elif label == "primary_init":
        payload = {"cmd": "init_state", "task": _task("uprime_primary", "True ∧ True")}
    elif label == "primary_split":
        payload = {
            "cmd": "apply_tactic",
            "state_id": _response_state_id(responses["primary_init"]),
            "action": {
                "action_id": "primary_constructor",
                "tactic": "constructor",
                "max_heartbeats": CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
            },
        }
    elif label == "primary_split_replay":
        payload = {
            "cmd": "replay_transition",
            "before_state_id": _response_state_id(responses["primary_init"]),
            "expected_after_state_id": responses["primary_split"].get(
                "after_state_id"
            ),
            "action": {
                "action_id": "primary_constructor",
                "tactic": "constructor",
                "max_heartbeats": CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
            },
        }
    elif label in {"primary_tail_close", "primary_tail_close_replay"}:
        _head, tail = _filtered_response_goal_ids(responses["primary_split"], after=True)
        action = {"action_id": "primary_tail_exact", "tactic": "exact True.intro"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(
                    responses["primary_split"], after=True
                ),
                "expected_after_state_id": responses["primary_tail_close"].get(
                    "after_state_id"
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
        head, _tail = _filtered_response_goal_ids(responses["primary_split"], after=True)
        action = {"action_id": "primary_head_exact", "tactic": "exact True.intro"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(
                    responses["primary_tail_close"], after=True
                ),
                "expected_after_state_id": responses["primary_head_close"].get(
                    "after_state_id"
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
                "expected_after_state_id": responses["zero_split"].get(
                    "after_state_id"
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
                "before_state_id": _response_state_id(
                    responses["zero_split"], after=True
                ),
                "expected_after_state_id": responses["zero_child_close"].get(
                    "after_state_id"
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
        target = _side_effect_target(responses["side_init"])
        action = {"action_id": "side_effect_rfl", "tactic": "rfl"}
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["side_init"]),
                "expected_after_state_id": responses["side_effect_close"].get(
                    "after_state_id"
                ),
                "action": action,
                "target_mvar_id": target,
            }
        else:
            payload = {
                "cmd": "apply_tactic",
                "state_id": _response_state_id(responses["side_init"]),
                "action": action,
                "target_mvar_id": target,
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
                    "run_tac do IO.addHeartbeats 400000000; "
                    'Lean.Core.checkMaxHeartbeats "uprime-litmus"'
                ),
                "max_heartbeats": BURN_MAX_HEARTBEATS_OPTION,
            },
        }
    elif label == "reset_init":
        payload = {"cmd": "init_state", "task": _task("uprime_reset", "True")}
    elif label in {"reset", "reset_replay"}:
        action = {
            "action_id": "reset_trivial",
            "tactic": "trivial",
            "max_heartbeats": BURN_MAX_HEARTBEATS_OPTION,
        }
        if label.endswith("_replay"):
            payload = {
                "cmd": "replay_transition",
                "before_state_id": _response_state_id(responses["reset_init"]),
                "expected_after_state_id": responses["reset"].get("after_state_id"),
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


def _validate_request_body(
    value: Any,
    *,
    frame_index: int,
    label: str,
    responses: dict[str, dict[str, Any]],
    last_monotonic_ns: int,
) -> tuple[int, dict[str, Any]]:
    body = _exact_object(value, _REQUEST_KEYS, f"request {label}")
    request_id = _expected_request_id(frame_index, label)
    if _int(body["frame_index"], f"request {label} frame index") != frame_index:
        _fail(f"request {label} frame index is invalid")
    if body["frame_label"] != label:
        _fail(f"request {label} frame label is invalid")
    if body["expected_request_id"] != request_id:
        _fail(f"request {label} expected id is invalid")
    request = body["request"]
    if not _strict_equal(request, _expected_request(frame_index, label, responses)):
        _fail(f"request {label} object differs from the frozen dynamic request")
    _utc(body["intent_at_utc"], f"request {label} intent time")
    monotonic = _int(
        body["intent_monotonic_ns"], f"request {label} monotonic time", minimum=0
    )
    if monotonic < last_monotonic_ns:
        _fail(f"request {label} monotonic time moves backwards")
    if body["durability_marker"] != "durable_send_intent_before_stdin_write":
        _fail(f"request {label} durability marker is invalid")
    if type(request) is not dict:
        _fail(f"request {label} payload must be an object")
    return monotonic, request


def _validate_response_body(
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


def _validate_shutdown_transport(
    value: Any,
    *,
    shutdown_response: dict[str, Any],
    process_returncode: int | None,
    transport_overflow: bool,
    non_json_stdout_count: int,
    stdout_reader_quiesced: bool,
    stderr_reader_quiesced: bool,
) -> None:
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
    response_digest = _sha256_upper(canonical_json_bytes(shutdown_response))
    stored_digest = body["shutdown_response_sha256"]
    if stored_digest is not None:
        _regex(stored_digest, _HEX64_UPPER_RE, "shutdown response digest")
    if _int(body["post_response_timeout_ns"], "shutdown post-response timeout") != (
        10_000_000_000
    ):
        _fail("shutdown post-response timeout is invalid")
    if _int(body["natural_exit_grace_ns"], "shutdown natural-exit grace") != (
        5_000_000_000
    ):
        _fail("shutdown natural-exit grace is invalid")
    if _int(body["forced_reap_budget_ns"], "shutdown forced-reap budget") != (
        4_000_000_000
    ):
        _fail("shutdown forced-reap budget is invalid")
    if _int(body["reader_drain_reserve_ns"], "shutdown reader-drain reserve") != (
        1_000_000_000
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
    if body["terminal_eof_exact"] is not (
        stdout_eof_count == 1 and kinds == ["eof"]
    ):
        _fail("shutdown terminal EOF summary is inconsistent")
    _optional_int(
        body["post_response_elapsed_ns"],
        "shutdown post-response elapsed",
        minimum=0,
    )
    # The equality and clear-state implications are X0 predicates, not an
    # exact-body precondition.  The oracle intentionally computes no X0 gate.
    _ = (response_digest, process_returncode, transport_overflow, non_json_stdout_count)


def _validate_closure(
    value: Any,
    *,
    preclosure_record_sha256: str,
    shutdown_response: dict[str, Any],
    response_id_mismatch_count: int,
) -> None:
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
    if body["primary_reason_code"] != (reasons[0] if reasons else None):
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
        if not _strict_equal(body[key], expected):
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
    impossible = {
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
    if impossible.intersection(reasons):
        _fail("closure reason contradicts the complete exact-49 sequence")
    for reason, observed in {
        "INVALID_UTF8_STDOUT": invalid_utf8 > 0,
        "NON_JSON_STDOUT": json_decode_count > 0,
        "NON_OBJECT_STDOUT": non_object > 0,
    }.items():
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
    _validate_shutdown_transport(
        body["shutdown_transport"],
        shutdown_response=shutdown_response,
        process_returncode=process_returncode,
        transport_overflow=transport_overflow,
        non_json_stdout_count=non_json,
        stdout_reader_quiesced=stdout_quiesced,
        stderr_reader_quiesced=stderr_quiesced,
    )


def _extract_exact49(snapshot: Any) -> _Exact49Evidence:
    if len(snapshot.canonical_record_bytes) != 49:
        _fail("exact-49 contract oracle requires exactly 49 records")
    records: list[dict[str, Any]] = []
    for raw in snapshot.canonical_record_bytes:
        try:
            value = parse_canonical_json_bytes(raw)
        except StandaloneLedgerStructureError as exc:
            raise StandaloneExact49ContractOracleError(
                "retained ledger record is not strict canonical JSON"
            ) from exc
        if type(value) is not dict:
            _fail("ledger record is not an object")
        records.append(value)
    expected_types = ["header", "local_probe"]
    for _label in EXPECTED_FRAME_LABELS:
        expected_types.extend(("request_intent", "parsed_response"))
    expected_types.append("closure")
    if [record.get("record_type") for record in records] != expected_types:
        _fail("record type sequence is not the frozen exact-49 state machine")
    _validate_header(records[0].get("body"))
    b4_raw_predicate = _validate_local_probe(records[1].get("body"))
    requests: dict[str, dict[str, Any]] = {}
    responses: dict[str, dict[str, Any]] = {}
    last_monotonic_ns = 0
    response_id_mismatch_count = 0
    for frame_index, label in enumerate(EXPECTED_FRAME_LABELS, start=1):
        request_record = records[2 * frame_index]
        response_record = records[2 * frame_index + 1]
        request_monotonic_ns, request = _validate_request_body(
            request_record.get("body"),
            frame_index=frame_index,
            label=label,
            responses=responses,
            last_monotonic_ns=last_monotonic_ns,
        )
        received_monotonic_ns, response, id_mismatch = _validate_response_body(
            response_record.get("body"),
            frame_index=frame_index,
            label=label,
            request_monotonic_ns=request_monotonic_ns,
        )
        requests[label] = request
        responses[label] = response
        last_monotonic_ns = received_monotonic_ns
        response_id_mismatch_count += int(id_mismatch)
    _validate_closure(
        records[-1].get("body"),
        preclosure_record_sha256=records[-2].get("record_sha256"),
        shutdown_response=responses["shutdown"],
        response_id_mismatch_count=response_id_mismatch_count,
    )
    if tuple(requests) != EXPECTED_FRAME_LABELS or tuple(responses) != (
        EXPECTED_FRAME_LABELS
    ):
        raise AssertionError("exact-49 extraction registry drifted")
    return _Exact49Evidence(
        requests=requests,
        responses=responses,
        b4_raw_predicate=b4_raw_predicate,
    )


def _is_int(value: Any) -> bool:
    return type(value) is int


def _kernel(response: dict[str, Any], which: str = "current") -> dict[str, Any]:
    field = {
        "before": "kernel_state_before",
        "after": "kernel_state_after",
        "current": "kernel_state",
    }[which]
    value = response.get(field)
    return value if type(value) is dict else {}


def _state_view(kernel_state: Any) -> dict[str, Any]:
    kernel = kernel_state if type(kernel_state) is dict else {}
    goal_rows = kernel.get("goals") if type(kernel.get("goals")) is list else []
    mvar_rows = kernel.get("metavars") if type(kernel.get("metavars")) is list else []
    goals = [
        row.get("mvar_id")
        for row in goal_rows
        if type(row) is dict and type(row.get("mvar_id")) is str
    ]
    all_mvars = [
        row.get("mvar_id")
        for row in mvar_rows
        if type(row) is dict and type(row.get("mvar_id")) is str
    ]
    assigned = [
        row.get("mvar_id")
        for row in mvar_rows
        if type(row) is dict
        and type(row.get("mvar_id")) is str
        and row.get("assigned") is True
    ]
    return {
        "goals": goals,
        "assigned": assigned,
        "all_mvars": all_mvars,
        "duplicate_goals": len(goals) != len(set(goals)),
        "duplicate_assigned": len(assigned) != len(set(assigned)),
        "duplicate_mvars": len(all_mvars) != len(set(all_mvars)),
        "assigned_open_goals": sorted(set(goals) & set(assigned)),
    }


def _state_structure(kernel_state: Any) -> bool:
    if type(kernel_state) is not dict:
        return False
    goals = kernel_state.get("goals")
    metavars = kernel_state.get("metavars")
    goal_rows_valid = type(goals) is list and all(
        type(row) is dict
        and type(row.get("mvar_id")) is str
        and bool(row.get("mvar_id"))
        for row in (goals if type(goals) is list else [])
    )
    mvar_rows_valid = type(metavars) is list and all(
        type(row) is dict
        and type(row.get("mvar_id")) is str
        and bool(row.get("mvar_id"))
        and type(row.get("assigned")) is bool
        for row in (metavars if type(metavars) is list else [])
    )
    view = _state_view(kernel_state)
    checks = (
        type(kernel_state.get("schema_version")) is str
        and bool(kernel_state.get("schema_version")),
        type(kernel_state.get("state_id")) is str
        and bool(kernel_state.get("state_id")),
        type(kernel_state.get("state_hash_raw")) is str
        and bool(kernel_state.get("state_hash_raw")),
        type(kernel_state.get("state_hash_norm")) is str
        and bool(kernel_state.get("state_hash_norm")),
        goal_rows_valid,
        mvar_rows_valid,
        not view["duplicate_goals"],
        not view["duplicate_assigned"],
        not view["duplicate_mvars"],
        goal_rows_valid
        and mvar_rows_valid
        and set(view["goals"]) <= set(view["all_mvars"]),
        not view["assigned_open_goals"],
    )
    return all(check is True for check in checks)


def _independent_delta(before_kernel: Any, after_kernel: Any) -> dict[str, list[str]]:
    before = _state_view(before_kernel)
    after = _state_view(after_kernel)
    before_goals = set(before["goals"])
    after_goals = set(after["goals"])
    before_assigned = set(before["assigned"])
    after_assigned = set(after["assigned"])
    before_mvars = set(before["all_mvars"])
    after_mvars = set(after["all_mvars"])
    assigned = after_assigned - before_assigned
    return {
        "closed_goals": sorted(before_goals & assigned),
        "new_goals": sorted(after_goals - before_goals),
        "assigned_mvars": sorted(assigned),
        "new_mvars": sorted(after_mvars - before_mvars),
    }


def _delta_evidence(response: Any) -> tuple[bool, dict[str, list[str]]]:
    reply = response if type(response) is dict else {}
    before_kernel = reply.get("kernel_state_before")
    after_kernel = reply.get("kernel_state_after")
    expected = _independent_delta(before_kernel, after_kernel)
    reported_obj = reply.get("state_delta")
    if type(reported_obj) is not dict:
        reported_obj = {}
    reported: dict[str, list[str]] = {}
    fields_well_formed: list[bool] = []
    for field in expected:
        value = reported_obj.get(field)
        valid = type(value) is list and all(type(item) is str for item in value)
        items = list(value) if valid else []
        reported[field] = sorted(items)
        fields_well_formed.append(valid and len(items) == len(set(items)))
    before = _state_view(before_kernel)
    after = _state_view(after_kernel)
    removed_goals = sorted(set(before["goals"]) - set(after["goals"]))
    structural = (
        _state_structure(before_kernel),
        _state_structure(after_kernel),
        type(before_kernel) is dict
        and _strict_equal(before_kernel.get("state_id"), reply.get("before_state_id")),
        type(after_kernel) is dict
        and _strict_equal(after_kernel.get("state_id"), reply.get("after_state_id")),
        set(before["all_mvars"]) <= set(after["all_mvars"]),
        set(before["assigned"]) <= set(after["assigned"]),
        removed_goals == expected["closed_goals"],
    )
    matches = [
        fields_well_formed[index] and reported[field] == expected[field]
        for index, field in enumerate(expected)
    ]
    return all(matches) and all(structural), expected


def _parse_max_heartbeats_option(value: Any) -> int | None:
    if _is_int(value):
        return value
    if type(value) is not str or _ASCII_DIGITS_RE.fullmatch(value) is None:
        return None
    try:
        return int(value, 10)
    except (ValueError, OverflowError):
        return None


def _state_option(response: dict[str, Any], which: str = "current") -> int | None:
    kernel = _kernel(response, which)
    options = kernel.get("options")
    value = options.get("maxHeartbeats") if type(options) is dict else None
    return _parse_max_heartbeats_option(value)


def _status_ok(response: dict[str, Any]) -> bool:
    after = _kernel(response, "after")
    view = _state_view(after)
    status = response.get("status")
    status_matches = (status == "success" and not view["goals"]) or (
        status == "partial" and bool(view["goals"])
    )
    return response.get("ok") is True and _state_structure(after) and status_matches


def _budget_evidence(response: Any) -> dict[str, Any]:
    reply = response if type(response) is dict else {}
    budget = reply.get("budget") if type(reply.get("budget")) is dict else {}
    audit = reply.get("audit") if type(reply.get("audit")) is dict else {}
    flags = audit.get("audit_flags") if type(audit.get("audit_flags")) is dict else {}
    mirror = (
        flags.get("heartbeat_telemetry")
        if type(flags.get("heartbeat_telemetry")) is dict
        else {}
    )
    fields_present = all(key in budget and key in mirror for key in _BUDGET_KEYS)
    mirror_match = bool(budget) and fields_present and _strict_equal(budget, mirror)
    option = budget.get("effective_max_heartbeats_option")
    counter = budget.get("effective_max_heartbeats_counter")
    unlimited = budget.get("unlimited")
    consumed = budget.get("consumed_heartbeats_counter")
    episode_max = budget.get("episode_max_heartbeats_counter")
    episode_remaining = budget.get("episode_remaining_heartbeats_counter")
    source = budget.get("source")
    episode_source = budget.get("episode_source")
    measurement_scope = budget.get("measurement_scope")
    reset_scope = budget.get("reset_scope")
    if _is_int(option) and option == 0:
        cap_consistent = (
            "effective_max_heartbeats_counter" in budget
            and counter is None
            and unlimited is True
        )
    else:
        cap_consistent = (
            _is_int(option)
            and option > 0
            and _is_int(counter)
            and counter == option * 1000
            and unlimited is False
        )
    top_heartbeats = reply.get("heartbeats")
    audit_heartbeats = audit.get("heartbeats")
    heartbeats_match = (
        _is_int(consumed)
        and consumed >= 0
        and _is_int(top_heartbeats)
        and _is_int(audit_heartbeats)
        and top_heartbeats == consumed
        and audit_heartbeats == consumed
    )
    strings_and_scopes = (
        type(source) is str
        and bool(source.strip())
        and episode_source == "task"
        and measurement_scope == "action_corem_toio_counter"
        and reset_scope == "per_corem_toio_call"
    )
    episode_valid = (
        episode_max == EPISODE_MAX_HEARTBEATS_COUNTER
        and _is_int(episode_max)
        and _is_int(episode_remaining)
        and 0 <= episode_remaining <= EPISODE_MAX_HEARTBEATS_COUNTER
    )
    return {
        "passed": bool(
            mirror_match
            and cap_consistent
            and heartbeats_match
            and strings_and_scopes
            and episode_valid
        ),
        "effective_max_heartbeats_option": option,
        "effective_max_heartbeats_counter": counter,
        "unlimited": unlimited,
        "source": source,
        "consumed_heartbeats_counter": consumed,
        "episode_max_heartbeats_counter": episode_max,
        "episode_remaining_heartbeats_counter": episode_remaining,
        "episode_source": episode_source,
    }


def _replay_pass(
    primary_response: dict[str, Any],
    replay_response: dict[str, Any],
    primary_request: dict[str, Any],
    replay_request: dict[str, Any],
) -> bool:
    certificate = replay_response.get("replay_certificate")
    if type(certificate) is not dict:
        certificate = {}
    action = primary_request.get("action")
    action_id = action.get("action_id") if type(action) is dict else None
    target_expected = primary_request.get("target_mvar_id")
    actual_before = primary_response.get("kernel_state_before")
    actual_after = primary_response.get("kernel_state_after")
    actual_delta = primary_response.get("state_delta")
    checks = (
        _delta_evidence(primary_response)[0],
        replay_response.get("ok") is True,
        _strict_equal(
            replay_response.get("before_state_id"), primary_request.get("state_id")
        ),
        _strict_equal(
            replay_response.get("expected_after_state_id"),
            primary_response.get("after_state_id"),
        ),
        _strict_equal(replay_response.get("action_id"), action_id),
        "target_mvar_id" in replay_response
        and _strict_equal(replay_response["target_mvar_id"], target_expected),
        _is_int(replay_response.get("n_states_before"))
        and _is_int(replay_response.get("n_states_after"))
        and replay_response["n_states_before"] == replay_response["n_states_after"],
        replay_response.get("reexecution_performed") is True
        and _is_int(replay_response.get("reexecution_heartbeats_counter"))
        and replay_response["reexecution_heartbeats_counter"] > 0
        and replay_response.get("reexecution_scope")
        == "fresh_from_immutable_before_state",
        type(actual_before) is dict
        and _strict_equal(replay_response.get("kernel_state_before"), actual_before),
        type(actual_after) is dict
        and _strict_equal(replay_response.get("kernel_state_expected"), actual_after),
        type(replay_response.get("kernel_state_observed")) is dict
        and _strict_equal(replay_response["kernel_state_observed"], actual_after),
        type(actual_delta) is dict
        and _strict_equal(replay_response.get("state_delta_expected"), actual_delta),
        type(replay_response.get("state_delta_observed")) is dict
        and _strict_equal(replay_response["state_delta_observed"], actual_delta),
        certificate.get("schema_version") == REPLAY_CERTIFICATE_VERSION,
        certificate.get("verification_method") == REPLAY_VERIFICATION_METHOD,
        certificate.get("replay_status") == "verified",
        certificate.get("state_match") is True,
        certificate.get("delta_match") is True,
        "error" in certificate and certificate["error"] is None,
        # Bind the response against the independently revalidated raw replay request.
        _strict_equal(
            replay_response.get("before_state_id"),
            replay_request.get("before_state_id"),
        ),
        _strict_equal(
            replay_response.get("expected_after_state_id"),
            replay_request.get("expected_after_state_id"),
        ),
    )
    return all(check is True for check in checks)


def _contract_vector(evidence: _Exact49Evidence) -> tuple[bool, ...]:
    requests = evidence.requests
    responses = evidence.responses

    request_echo_checks = [
        responses[label].get("id") == requests[label].get("id")
        and responses[label].get("rpc_protocol_version") == RPC_PROTOCOL_VERSION
        for label in EXPECTED_FRAME_LABELS
    ]
    request_ids = [requests[label].get("id") for label in EXPECTED_FRAME_LABELS]
    controls = (
        tuple(requests) == EXPECTED_FRAME_LABELS,
        tuple(responses) == EXPECTED_FRAME_LABELS,
        len(set(request_ids)) == len(EXPECTED_FRAME_LABELS)
        and all(type(value) is str and bool(value) for value in request_ids),
        responses["load"].get("ok") is True
        and responses["load"].get("loaded") is True,
        responses["status"].get("ok") is True
        and responses["status"].get("loaded") is True
        and _is_int(responses["status"].get("n_states"))
        and responses["status"]["n_states"] == EXPECTED_PERSISTENT_STATE_COUNT
        and _is_int(responses["status"].get("n_requests"))
        and responses["status"]["n_requests"] == EXPECTED_STATUS_REQUEST_COUNT,
        responses["shutdown"].get("ok") is True
        and responses["shutdown"].get("shutdown") is True,
    )
    r0 = all(request_echo_checks) and all(controls)

    b0_rows: list[bool] = []
    for label in INIT_LABELS:
        response = responses[label]
        state_summary = response.get("state")
        kernel = _kernel(response)
        b0_rows.append(
            response.get("ok") is True
            and _state_structure(kernel)
            and type(state_summary) is dict
            and _strict_equal(state_summary.get("state_id"), kernel.get("state_id"))
            and _state_option(response) == TASK_MAX_HEARTBEATS_OPTION
        )
    b0 = len(b0_rows) == 5 and all(b0_rows)

    budget_rows = {label: _budget_evidence(responses[label]) for label in ACTION_LABELS}
    expected_budgets = {
        "primary_split": (CONSTRUCTOR_MAX_HEARTBEATS_OPTION, "action"),
        "primary_tail_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "primary_head_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "zero_split": (0, "action"),
        "zero_child_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "side_effect_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "burn": (BURN_MAX_HEARTBEATS_OPTION, "action"),
        "reset": (BURN_MAX_HEARTBEATS_OPTION, "action"),
    }
    budget_request_matches: dict[str, bool] = {}
    for label in ACTION_LABELS:
        expected_option, expected_source = expected_budgets[label]
        row = budget_rows[label]
        consumed = row["consumed_heartbeats_counter"]
        effective_counter = row["effective_max_heartbeats_counter"]
        if expected_option == 0:
            execution_bound_match = row["unlimited"] is True
        elif label == "burn":
            execution_bound_match = _is_int(consumed) and _is_int(effective_counter)
        else:
            execution_bound_match = (
                _is_int(consumed)
                and _is_int(effective_counter)
                and consumed <= effective_counter
            )
        budget_request_matches[label] = (
            _is_int(row["effective_max_heartbeats_option"])
            and row["effective_max_heartbeats_option"] == expected_option
            and row["source"] == expected_source
            and execution_bound_match
        )
    b2 = (
        tuple(budget_rows) == ACTION_LABELS
        and len(budget_rows) == 8
        and all(
            budget_rows[label]["passed"] and budget_request_matches[label]
            for label in ACTION_LABELS
        )
    )

    b1_checks = (
        budget_rows["primary_split"]["effective_max_heartbeats_option"]
        == CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
        _state_option(responses["primary_split"], "after")
        == TASK_MAX_HEARTBEATS_OPTION,
        budget_rows["primary_tail_close"]["effective_max_heartbeats_option"]
        == TASK_MAX_HEARTBEATS_OPTION
        and budget_rows["primary_tail_close"]["source"] == "task",
        budget_rows["zero_split"]["effective_max_heartbeats_option"] == 0
        and budget_rows["zero_split"]["unlimited"] is True,
        _state_option(responses["zero_split"], "after")
        == TASK_MAX_HEARTBEATS_OPTION,
        budget_rows["zero_child_close"]["effective_max_heartbeats_option"]
        == TASK_MAX_HEARTBEATS_OPTION
        and budget_rows["zero_child_close"]["source"] == "task",
    )
    b1 = all(check is True for check in b1_checks)

    predecessor_labels = {
        "primary_split": ("primary_init", "current"),
        "primary_tail_close": ("primary_split", "after"),
        "primary_head_close": ("primary_tail_close", "after"),
        "zero_split": ("zero_init", "current"),
        "zero_child_close": ("zero_split", "after"),
        "side_effect_close": ("side_init", "current"),
        "burn": ("burn_init", "current"),
        "reset": ("reset_init", "current"),
    }
    continuity: dict[str, bool] = {}
    for label in ACTION_LABELS:
        predecessor_label, predecessor_which = predecessor_labels[label]
        continuity[label] = (
            type(requests[label].get("state_id")) is str
            and _strict_equal(
                responses[label].get("before_state_id"), requests[label]["state_id"]
            )
            and _strict_equal(
                responses[label].get("kernel_state_before"),
                _kernel(responses[predecessor_label], predecessor_which),
            )
        )
    delta_rows = {
        label: _delta_evidence(responses[label]) for label in DELTA_LABELS
    }
    d1 = (
        tuple(delta_rows) == DELTA_LABELS
        and len(delta_rows) == 7
        and all(
            _status_ok(responses[label])
            and delta_rows[label][0]
            and continuity[label]
            for label in DELTA_LABELS
        )
    )

    primary_goals = _state_view(_kernel(responses["primary_split"], "after"))["goals"]
    zero_goals = _state_view(_kernel(responses["zero_split"], "after"))["goals"]
    primary_tail_expected = delta_rows["primary_tail_close"][1]
    zero_tail_expected = delta_rows["zero_child_close"][1]
    d0_checks = (
        len(primary_goals) == 2,
        _status_ok(responses["primary_tail_close"]),
        delta_rows["primary_tail_close"][0],
        _state_view(_kernel(responses["primary_tail_close"], "after"))["goals"]
        == primary_goals[:1],
        len(primary_goals) == 2
        and primary_goals[1] in primary_tail_expected["assigned_mvars"],
        len(primary_goals) == 2
        and primary_goals[1] in primary_tail_expected["closed_goals"],
        _status_ok(responses["primary_head_close"]),
        delta_rows["primary_head_close"][0],
        _state_view(_kernel(responses["primary_head_close"], "after"))["goals"]
        == [],
        len(zero_goals) == 2,
        _status_ok(responses["zero_child_close"]),
        _state_view(_kernel(responses["zero_child_close"], "after"))["goals"]
        == zero_goals[:1],
        len(zero_goals) == 2
        and zero_goals[1] in zero_tail_expected["assigned_mvars"],
        len(zero_goals) == 2
        and zero_goals[1] in zero_tail_expected["closed_goals"],
    )
    d0 = all(check is True for check in d0_checks)

    side_init_goals_raw = _kernel(responses["side_init"]).get("goals")
    side_goal_ids: list[str] = []
    side_raw_valid = (
        type(side_init_goals_raw) is list
        and len(side_init_goals_raw) == 2
        and all(
            type(row) is dict
            and type(row.get("mvar_id")) is str
            and bool(row["mvar_id"])
            for row in (side_init_goals_raw if type(side_init_goals_raw) is list else [])
        )
    )
    if side_raw_valid:
        side_goal_ids = [row["mvar_id"] for row in side_init_goals_raw]
        side_raw_valid = side_goal_ids[0] != side_goal_ids[1]
    side_request = requests["side_effect_close"]
    side_delta = _independent_delta(
        responses["side_effect_close"].get("kernel_state_before"),
        responses["side_effect_close"].get("kernel_state_after"),
    )
    d2_checks = (
        side_raw_valid,
        "target_mvar_id" in side_request
        and len(side_goal_ids) == 2
        and side_request["target_mvar_id"] == side_goal_ids[1],
        _status_ok(responses["side_effect_close"]),
        delta_rows["side_effect_close"][0],
        _state_view(_kernel(responses["side_effect_close"], "after"))["goals"]
        == [],
        len(side_goal_ids) == 2
        and set(side_delta["assigned_mvars"]) == set(side_goal_ids),
        len(side_goal_ids) == 2
        and set(side_delta["closed_goals"]) == set(side_goal_ids),
        len(ACTION_LABELS) == 8
        and all(
            _state_structure(_kernel(responses[label], "after"))
            for label in ACTION_LABELS
        ),
    )
    d2 = all(check is True for check in d2_checks)

    burn = responses["burn"]
    burn_audit = burn.get("audit") if type(burn.get("audit")) is dict else {}
    burn_consumed = budget_rows["burn"]["consumed_heartbeats_counter"]
    burn_delta_valid, _burn_delta = _delta_evidence(burn)
    b3_checks = (
        burn.get("ok") is True,
        burn.get("status") == "timeout",
        burn_audit.get("status") == "timeout",
        continuity["burn"],
        burn_delta_valid,
        _strict_equal(
            _state_view(_kernel(burn, "before")),
            _state_view(_kernel(burn, "after")),
        ),
        _strict_equal(
            _kernel(burn, "before").get("state_hash_norm"),
            _kernel(burn, "after").get("state_hash_norm"),
        ),
        _is_int(burn_consumed)
        and burn_consumed > BURN_MAX_HEARTBEATS_OPTION * 1000,
        budget_rows["burn"]["passed"] and budget_request_matches["burn"],
        _status_ok(responses["reset"]),
        budget_rows["reset"]["passed"] and budget_request_matches["reset"],
    )
    b3 = all(check is True for check in b3_checks)

    replay_passes = [
        _replay_pass(
            responses[primary_label],
            responses[replay_label],
            requests[primary_label],
            requests[replay_label],
        )
        for primary_label, replay_label in REPLAY_PAIRS
    ]
    r1 = len(replay_passes) == 7 and all(replay_passes)

    episode_passes: list[bool] = []
    for labels in EPISODE_GROUPS:
        rows = [budget_rows[label] for label in labels]
        consumed = [row["consumed_heartbeats_counter"] for row in rows]
        remaining = [row["episode_remaining_heartbeats_counter"] for row in rows]
        expected_remaining: list[int] = []
        running = EPISODE_MAX_HEARTBEATS_COUNTER
        consumed_valid = all(_is_int(value) and value >= 0 for value in consumed)
        if consumed_valid:
            for value in consumed:
                running = max(0, running - value)
                expected_remaining.append(running)
        episode_passes.append(
            len(rows) == len(labels)
            and all(
                _is_int(row["episode_max_heartbeats_counter"])
                and row["episode_max_heartbeats_counter"]
                == EPISODE_MAX_HEARTBEATS_COUNTER
                for row in rows
            )
            and all(row["episode_source"] == "task" for row in rows)
            and all(_is_int(value) for value in remaining)
            and all(
                left >= right
                for left, right in zip(remaining, remaining[1:], strict=False)
            )
            and consumed_valid
            and remaining == expected_remaining
        )
    e0 = [len(group) for group in EPISODE_GROUPS] == [3, 2, 1, 1, 1] and all(
        episode_passes
    )

    vector = (
        r0,
        b0,
        b1,
        b2,
        b3,
        evidence.b4_raw_predicate,
        d0,
        d1,
        d2,
        r1,
        e0,
    )
    if len(vector) != len(CONTRACT_IDS) or not all(type(item) is bool for item in vector):
        raise AssertionError("contract vector drifted from the frozen registry")
    return vector


def attest_standalone_exact_49_contracts(
    path: str | Path,
) -> StandaloneExact49ContractOracleAttestation:
    """Recompute the frozen eleven raw predicates from one path snapshot.

    A semantic precondition failure raises
    :class:`StandaloneExact49ContractOracleError` and returns no partial
    vector.  A valid exact-49 ledger with absent or malformed scientific
    telemetry instead receives false values in the affected predicates.
    """

    try:
        # Frozen phase boundary: exactly one path load, through the same-handle
        # nonsemantic chain snapshot substrate.
        snapshot = load_standalone_closed_chain_snapshot(path)
    except StandaloneLedgerStructureError as exc:
        raise StandaloneExact49ContractOracleError(
            "ledger chain structure is invalid"
        ) from exc
    evidence = _extract_exact49(snapshot)
    contract_passes = _contract_vector(evidence)
    failure_ids = tuple(
        contract_id
        for contract_id, passed in zip(
            CONTRACT_IDS, contract_passes, strict=True
        )
        if passed is False
    )
    chain = snapshot.attestation
    return StandaloneExact49ContractOracleAttestation(
        oracle_schema_version=SCHEMA_UPRIME_RPC_EXACT_49_CONTRACT_ORACLE,
        oracle_scope=ORACLE_SCOPE,
        origin_status="unknown_may_be_synthetic",
        input_sha256=chain.input_sha256,
        input_bytes=chain.input_bytes,
        final_chain_head=chain.final_chain_head,
        record_count=chain.record_count,
        contract_ids=CONTRACT_IDS,
        contract_passes=contract_passes,
        contract_failure_ids=failure_ids,
        raw_all_contracts=all(contract_passes),
    )


__all__ = [
    "CONTRACT_IDS",
    "ORACLE_SCOPE",
    "SCHEMA_UPRIME_RPC_EXACT_49_CONTRACT_ORACLE",
    "StandaloneExact49ContractOracleAttestation",
    "StandaloneExact49ContractOracleError",
    "attest_standalone_exact_49_contracts",
]
