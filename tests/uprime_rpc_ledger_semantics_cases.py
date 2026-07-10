"""Imported M2b semantic cases for the frozen test_uprime_rpc_ledger profile."""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
from pathlib import Path
from typing import Any, Callable

import pytest

from lean_rgc.evals import uprime_rpc_ledger as chain
from lean_rgc.evals import uprime_rpc_ledger_semantics as semantics


LABELS = (
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
FRAME_MANIFEST_SHA256 = (
    "03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E"
)
RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
LEDGER_SCHEMA_VERSION = "lean-rgc-uprime-rpc-parsed-ledger-v1.0"
RECORD_SCHEMA_VERSION = "lean-rgc-uprime-rpc-parsed-ledger-record-v1.0"
SCOPE = "parsed_json_objects_and_local_probe_not_raw_wire_octets"
UTC = "2026-07-11T00:00:00.000000Z"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _request_id(frame_index: int, label: str) -> str:
    return f"uprime-{frame_index:02d}-{label}"


def _task(task_id: str, statement: str, *, prefix: str = "") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "statement": statement,
        "imports": ["Lean"],
        "prefix": prefix,
        "max_heartbeats": 731,
        "episode_max_heartbeats_counter": 1_000_000,
    }


def _claim_receipt() -> dict[str, Any]:
    candidate = "a" * 40
    license_commit = "b" * 40
    license_id = hashlib.sha256(
        b"lean-rgc-uprime-u1-attempt-v1\0" + candidate.encode("ascii")
    ).hexdigest()
    return {
        "schema_version": "lean-rgc-uprime-u1-claim-receipt-public-v1.0",
        "candidate_commit": candidate,
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
        "claimed_at_utc": UTC,
    }


def _reservation() -> dict[str, Any]:
    receipt = _claim_receipt()
    anchor = receipt["license_commit"][:12]
    report = f"rpc_diagnostic_{anchor}.json"
    return {
        "schema_version": "lean-rgc-uprime-rpc-bundle-reservation-v1.1",
        "status": "LIVE_EVIDENCE_BUNDLE_RESERVED",
        "anchor": anchor,
        "candidate_commit": receipt["candidate_commit"],
        "license_commit": receipt["license_commit"],
        "license_id": receipt["license_id"],
        "remote_claim_ref": receipt["remote_claim_ref"],
        "claim_receipt": receipt,
        "claim_receipt_sha256": _sha256(chain.canonical_json_bytes(receipt)),
        "registered_run_dir": "runs/uprime_u1_rpc_20260710",
        "report_artifact_name": report,
        "ledger_artifact_name": f"rpc_diagnostic_{anchor}.responses.jsonl",
        "reservation_artifact_name": f"{report}.reservation",
        "report_schema_version": "lean-rgc-uprime-rpc-diagnostic-v1.2",
        "ledger_schema_version": LEDGER_SCHEMA_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "rpc_protocol_version": RPC_PROTOCOL_VERSION,
        "expected_frame_count": 23,
        "expected_frame_manifest_sha256": FRAME_MANIFEST_SHA256,
        "reservation_token_sha256": "1" * 64,
        "reserved_at_utc": UTC,
        "process_id": 1234,
    }


def _header_body() -> dict[str, Any]:
    reservation = _reservation()
    reservation_bytes = chain.canonical_json_bytes(reservation) + b"\n"
    return {
        "ledger_schema_version": LEDGER_SCHEMA_VERSION,
        "canonicalizer_id": "lean-rgc-strict-json-int-v1",
        "hash_algorithm": "SHA-256",
        "evidence_scope": SCOPE,
        "wire_exact": False,
        "reservation": reservation,
        "reservation_sha256": _sha256(reservation_bytes),
        "expected_frame_labels": list(LABELS),
        "created_at_utc": UTC,
    }


def _cache_payloads() -> dict[str, Any]:
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


def _local_probe_body() -> dict[str, Any]:
    source_blobs = {
        path: {"git_blob_oid": "2" * 40, "head_blob_sha256": "3" * 64}
        for path in (
            "lean_rgc/audit_result_cache.py",
            "lean_rgc/schemas.py",
            "lean_rgc/core/ids.py",
            "lean_rgc/evals/uprime_rpc_litmus.py",
        )
    }
    return {
        "probe_id": "B4_cache_budget_semantics",
        "payloads": _cache_payloads(),
        "key_kwargs": {
            "lean_version": "uprime-cache-probe",
            "workdir_fingerprint_value": "uprime-cache-probe",
            "import_mode": "preserve",
            "trace_state": False,
            "lane": "kernel_rpc",
        },
        "resolved": {
            "task_fallback": "731",
            "explicit_zero": "0",
            "explicit_nonzero": "123456",
            "omitted_default": "200000",
            "explicit_default": "200000",
        },
        "omitted_key": "synthetic-equal-cache-key",
        "omitted_fields": {"max_heartbeats": "200000", "scope": "synthetic"},
        "explicit_key": "synthetic-equal-cache-key",
        "explicit_fields": {"max_heartbeats": "200000", "scope": "synthetic"},
        "source_blobs": source_blobs,
        "observed_at_utc": UTC,
    }


def _goal_rows(*mvar_ids: str) -> list[dict[str, Any]]:
    return [{"mvar_id": mvar_id} for mvar_id in mvar_ids]


def _response(label: str, frame_index: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": _request_id(frame_index, label),
        "rpc_protocol_version": RPC_PROTOCOL_VERSION,
        "ok": True,
        **extra,
    }


def _event_bodies() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    def pair(label: str, request: dict[str, Any], response: dict[str, Any]) -> None:
        frame_index = LABELS.index(label) + 1
        expected_id = _request_id(frame_index, label)
        assert request["id"] == expected_id
        events.append(
            {
                "record_type": "request_intent",
                "body": {
                    "frame_index": frame_index,
                    "frame_label": label,
                    "expected_request_id": expected_id,
                    "request": request,
                    "intent_at_utc": UTC,
                    "intent_monotonic_ns": frame_index * 10,
                    "durability_marker": (
                        "durable_send_intent_before_stdin_write"
                    ),
                },
            }
        )
        events.append(
            {
                "record_type": "parsed_response",
                "body": {
                    "arrival_index": frame_index,
                    "association": "active_frame",
                    "frame_index": frame_index,
                    "frame_label": label,
                    "expected_request_id": expected_id,
                    "response": response,
                    "received_at_utc": UTC,
                    "received_monotonic_ns": frame_index * 10 + 1,
                },
            }
        )

    pair(
        "load",
        {"id": _request_id(1, "load"), "cmd": "load_project", "imports": ["Lean"]},
        _response("load", 1, loaded=True),
    )
    pair(
        "primary_init",
        {
            "id": _request_id(2, "primary_init"),
            "cmd": "init_state",
            "task": _task("uprime_primary", "True ∧ True"),
        },
        _response(
            "primary_init",
            2,
            state={"state_id": "state-primary-init"},
            kernel_state={"goals": _goal_rows("primary-root")},
        ),
    )
    primary_action = {
        "action_id": "primary_constructor",
        "tactic": "constructor",
        "max_heartbeats": 123_456,
    }
    pair(
        "primary_split",
        {
            "id": _request_id(3, "primary_split"),
            "cmd": "apply_tactic",
            "state_id": "state-primary-init",
            "action": primary_action,
        },
        _response(
            "primary_split",
            3,
            after_state_id="state-primary-split",
            kernel_state_after={"goals": _goal_rows("primary-head", "primary-tail")},
        ),
    )
    pair(
        "primary_split_replay",
        {
            "id": _request_id(4, "primary_split_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-primary-init",
            "expected_after_state_id": "state-primary-split",
            "action": primary_action,
        },
        _response("primary_split_replay", 4),
    )
    primary_tail_action = {
        "action_id": "primary_tail_exact",
        "tactic": "exact True.intro",
    }
    pair(
        "primary_tail_close",
        {
            "id": _request_id(5, "primary_tail_close"),
            "cmd": "apply_tactic",
            "state_id": "state-primary-split",
            "target_mvar_id": "primary-tail",
            "action": primary_tail_action,
        },
        _response(
            "primary_tail_close",
            5,
            after_state_id="state-primary-tail-closed",
            kernel_state_after={"goals": _goal_rows("primary-head")},
        ),
    )
    pair(
        "primary_tail_close_replay",
        {
            "id": _request_id(6, "primary_tail_close_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-primary-split",
            "expected_after_state_id": "state-primary-tail-closed",
            "target_mvar_id": "primary-tail",
            "action": primary_tail_action,
        },
        _response("primary_tail_close_replay", 6),
    )
    primary_head_action = {
        "action_id": "primary_head_exact",
        "tactic": "exact True.intro",
    }
    pair(
        "primary_head_close",
        {
            "id": _request_id(7, "primary_head_close"),
            "cmd": "apply_tactic",
            "state_id": "state-primary-tail-closed",
            "target_mvar_id": "primary-head",
            "action": primary_head_action,
        },
        _response(
            "primary_head_close",
            7,
            after_state_id="state-primary-closed",
            kernel_state_after={"goals": []},
        ),
    )
    pair(
        "primary_head_close_replay",
        {
            "id": _request_id(8, "primary_head_close_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-primary-tail-closed",
            "expected_after_state_id": "state-primary-closed",
            "target_mvar_id": "primary-head",
            "action": primary_head_action,
        },
        _response("primary_head_close_replay", 8),
    )
    pair(
        "zero_init",
        {
            "id": _request_id(9, "zero_init"),
            "cmd": "init_state",
            "task": _task("uprime_zero", "True ∧ True"),
        },
        _response(
            "zero_init",
            9,
            state={"state_id": "state-zero-init"},
            kernel_state={"goals": _goal_rows("zero-root")},
        ),
    )
    zero_action = {
        "action_id": "zero_constructor",
        "tactic": "constructor",
        "max_heartbeats": 0,
    }
    pair(
        "zero_split",
        {
            "id": _request_id(10, "zero_split"),
            "cmd": "apply_tactic",
            "state_id": "state-zero-init",
            "action": zero_action,
        },
        _response(
            "zero_split",
            10,
            after_state_id="state-zero-split",
            kernel_state_after={"goals": _goal_rows("zero-head", "zero-tail")},
        ),
    )
    pair(
        "zero_split_replay",
        {
            "id": _request_id(11, "zero_split_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-zero-init",
            "expected_after_state_id": "state-zero-split",
            "action": zero_action,
        },
        _response("zero_split_replay", 11),
    )
    zero_child_action = {
        "action_id": "zero_child_exact",
        "tactic": "exact True.intro",
    }
    pair(
        "zero_child_close",
        {
            "id": _request_id(12, "zero_child_close"),
            "cmd": "apply_tactic",
            "state_id": "state-zero-split",
            "target_mvar_id": "zero-tail",
            "action": zero_child_action,
        },
        _response(
            "zero_child_close",
            12,
            after_state_id="state-zero-tail-closed",
            kernel_state_after={"goals": _goal_rows("zero-head")},
        ),
    )
    pair(
        "zero_child_close_replay",
        {
            "id": _request_id(13, "zero_child_close_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-zero-split",
            "expected_after_state_id": "state-zero-tail-closed",
            "target_mvar_id": "zero-tail",
            "action": zero_child_action,
        },
        _response("zero_child_close_replay", 13),
    )
    pair(
        "side_init",
        {
            "id": _request_id(14, "side_init"),
            "cmd": "init_state",
            "task": _task(
                "uprime_side_effect",
                "∃ n : Nat, n = 0",
                prefix="refine ⟨?_, ?_⟩",
            ),
        },
        _response(
            "side_init",
            14,
            state={"state_id": "state-side-init"},
            kernel_state={"goals": _goal_rows("side-witness", "side-equality")},
        ),
    )
    side_action = {"action_id": "side_effect_rfl", "tactic": "rfl"}
    pair(
        "side_effect_close",
        {
            "id": _request_id(15, "side_effect_close"),
            "cmd": "apply_tactic",
            "state_id": "state-side-init",
            "target_mvar_id": "side-equality",
            "action": side_action,
        },
        _response(
            "side_effect_close",
            15,
            after_state_id="state-side-closed",
            kernel_state_after={"goals": []},
        ),
    )
    pair(
        "side_effect_close_replay",
        {
            "id": _request_id(16, "side_effect_close_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-side-init",
            "expected_after_state_id": "state-side-closed",
            "target_mvar_id": "side-equality",
            "action": side_action,
        },
        _response("side_effect_close_replay", 16),
    )
    pair(
        "burn_init",
        {
            "id": _request_id(17, "burn_init"),
            "cmd": "init_state",
            "task": _task("uprime_burn", "True"),
        },
        _response(
            "burn_init",
            17,
            state={"state_id": "state-burn-init"},
            kernel_state={"goals": _goal_rows("burn-goal")},
        ),
    )
    pair(
        "burn",
        {
            "id": _request_id(18, "burn"),
            "cmd": "apply_tactic",
            "state_id": "state-burn-init",
            "action": {
                "action_id": "burn",
                "tactic": (
                    "run_tac do IO.addHeartbeats 400000000; "
                    'Lean.Core.checkMaxHeartbeats "uprime-litmus"'
                ),
                "max_heartbeats": 200_000,
            },
        },
        _response("burn", 18, status="timeout"),
    )
    pair(
        "reset_init",
        {
            "id": _request_id(19, "reset_init"),
            "cmd": "init_state",
            "task": _task("uprime_reset", "True"),
        },
        _response(
            "reset_init",
            19,
            state={"state_id": "state-reset-init"},
            kernel_state={"goals": _goal_rows("reset-goal")},
        ),
    )
    reset_action = {
        "action_id": "reset_trivial",
        "tactic": "trivial",
        "max_heartbeats": 200_000,
    }
    pair(
        "reset",
        {
            "id": _request_id(20, "reset"),
            "cmd": "apply_tactic",
            "state_id": "state-reset-init",
            "action": reset_action,
        },
        _response(
            "reset",
            20,
            after_state_id="state-reset-closed",
            kernel_state_after={"goals": []},
        ),
    )
    pair(
        "reset_replay",
        {
            "id": _request_id(21, "reset_replay"),
            "cmd": "replay_transition",
            "before_state_id": "state-reset-init",
            "expected_after_state_id": "state-reset-closed",
            "action": reset_action,
        },
        _response("reset_replay", 21),
    )
    pair(
        "status",
        {"id": _request_id(22, "status"), "cmd": "status"},
        _response("status", 22, loaded=True, n_states=13, n_requests=22),
    )
    pair(
        "shutdown",
        {"id": _request_id(23, "shutdown"), "cmd": "shutdown"},
        _response("shutdown", 23, shutdown=True, error=None),
    )
    assert len(events) == 46
    return events


def _response_event(events: list[dict[str, Any]], label: str) -> dict[str, Any]:
    return next(
        event
        for event in events
        if event["record_type"] == "parsed_response"
        and event["body"].get("frame_label") == label
    )


def _request_event(events: list[dict[str, Any]], label: str) -> dict[str, Any]:
    return next(
        event
        for event in events
        if event["record_type"] == "request_intent"
        and event["body"].get("frame_label") == label
    )


def _shutdown_transport(shutdown_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "stream_complete": True,
        "shutdown_ack_ok": (
            shutdown_response.get("ok") is True
            and shutdown_response.get("shutdown") is True
            and shutdown_response.get("error") is None
        ),
        "shutdown_response_sha256": _sha256(
            chain.canonical_json_bytes(shutdown_response)
        ),
        "post_response_timeout_ns": 10_000_000_000,
        "natural_exit_grace_ns": 5_000_000_000,
        "forced_reap_budget_ns": 4_000_000_000,
        "reader_drain_reserve_ns": 1_000_000_000,
        "exit_mode": "natural",
        "graceful_exit": True,
        "termination_signal_attempted": False,
        "kill_signal_attempted": False,
        "forced_reap": False,
        "forced_reap_succeeded": None,
        "reader_threads_drained": True,
        "stdout_eof_count": 1,
        "residual_response_count": 0,
        "residual_frame_kinds": ["eof"],
        "terminal_eof_exact": True,
        "transport_finalized": True,
        "post_response_elapsed_ns": 1,
    }


def _closure_body(
    *,
    preclosure_head: str,
    probe: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    requests = [event["body"] for event in events if event["record_type"] == "request_intent"]
    responses = [event["body"] for event in events if event["record_type"] == "parsed_response"]
    request_indices = [body["frame_index"] for body in requests]
    response_indices = [
        body["frame_index"] for body in responses if type(body.get("frame_index")) is int
    ]
    request_counts = Counter(request_indices)
    response_counts = Counter(response_indices)
    expected = set(range(1, 24))
    shutdown = next(
        body["response"]
        for body in responses
        if body.get("frame_label") == "shutdown"
    )
    response_id_mismatches = sum(
        body["response"].get("id") != body.get("expected_request_id")
        for body in responses
        if body.get("association") == "active_frame"
    )
    return {
        "sequence_status": "complete",
        "primary_reason_code": None,
        "reason_codes": [],
        "closed_at_utc": UTC,
        "preclosure_record_sha256": preclosure_head,
        "local_probe_count": 1 if probe else 0,
        "request_intent_count": len(requests),
        "parsed_response_count": len(responses),
        "expected_frame_count": 23,
        "expected_frame_manifest_sha256": FRAME_MANIFEST_SHA256,
        "observed_request_frame_indices": request_indices,
        "observed_response_frame_indices": response_indices,
        "missing_request_frame_indices": sorted(expected - set(request_indices)),
        "missing_response_frame_indices": sorted(expected - set(response_indices)),
        "duplicate_request_frame_indices": sorted(
            index for index, count in request_counts.items() if count > 1
        ),
        "duplicate_response_frame_indices": sorted(
            index for index, count in response_counts.items() if count > 1
        ),
        "unsolicited_response_count": sum(
            body.get("association") == "unsolicited" for body in responses
        ),
        "late_response_count": sum(
            body.get("association") == "late_for_frame" for body in responses
        ),
        "response_id_mismatch_count": response_id_mismatches,
        "invalid_utf8_stdout_count": 0,
        "non_json_stdout_count": 0,
        "non_object_stdout_count": 0,
        "stderr_line_count": 0,
        "transport_overflow": False,
        "process_returncode": 0,
        "process_quiesced": True,
        "stdout_reader_quiesced": True,
        "stderr_reader_quiesced": True,
        "writer_healthy": True,
        "shutdown_transport": _shutdown_transport(shutdown),
    }


EventMutation = Callable[[dict[str, Any], dict[str, Any], list[dict[str, Any]]], None]
ClosureMutation = Callable[[dict[str, Any]], None]


def _write_fixture(
    path: Path,
    *,
    mutate: EventMutation | None = None,
    mutate_closure: ClosureMutation | None = None,
) -> None:
    header = _header_body()
    probe = _local_probe_body()
    events = _event_bodies()
    if mutate is not None:
        mutate(header, probe, events)
    writer = chain.StandaloneChainWriter.create(path, header_body=header)
    writer.append_event("local_probe", probe)
    for event in events:
        writer.append_event(event["record_type"], event["body"])
    assert writer.record_count == 48
    assert writer.chain_head is not None
    closure = _closure_body(
        preclosure_head=writer.chain_head,
        probe=probe,
        events=events,
    )
    if mutate_closure is not None:
        mutate_closure(closure)
    writer.close_with_closure(closure)


def _attest(path: Path):
    return semantics.attest_standalone_nominal_49_semantics(path)


def _false_x0_ids(result: Any) -> set[str]:
    return {
        key
        for key, value in zip(
            result.x0_predicate_ids, result.x0_predicates, strict=True
        )
        if value is False
    }


def _set_reservation_field_and_rehash(
    header: dict[str, Any], key: str, value: Any
) -> None:
    header["reservation"][key] = value
    _rehash_header_reservation(header)


def _rehash_header_reservation(header: dict[str, Any]) -> None:
    header["reservation_sha256"] = _sha256(
        chain.canonical_json_bytes(header["reservation"]) + b"\n"
    )


def _rehash_receipt_and_reservation(header: dict[str, Any]) -> None:
    reservation = header["reservation"]
    reservation["claim_receipt_sha256"] = _sha256(
        chain.canonical_json_bytes(reservation["claim_receipt"])
    )
    _rehash_header_reservation(header)


def _mutate_derived_license_identity(header: dict[str, Any]) -> None:
    reservation = header["reservation"]
    receipt = reservation["claim_receipt"]
    wrong = "f" * 64
    wrong_ref = f"refs/tags/uprime-u1-attempts/{wrong}"
    receipt["license_id"] = wrong
    receipt["remote_claim_ref"] = wrong_ref
    reservation["license_id"] = wrong
    reservation["remote_claim_ref"] = wrong_ref
    _rehash_receipt_and_reservation(header)


def _mutate_remote_claim_oid(header: dict[str, Any]) -> None:
    header["reservation"]["claim_receipt"]["remote_claim_oid"] = "e" * 40
    _rehash_receipt_and_reservation(header)


def _mutate_reservation_anchor_with_matching_names(header: dict[str, Any]) -> None:
    reservation = header["reservation"]
    anchor = "f" * 12
    reservation.update(
        {
            "anchor": anchor,
            "report_artifact_name": f"rpc_diagnostic_{anchor}.json",
            "ledger_artifact_name": f"rpc_diagnostic_{anchor}.responses.jsonl",
            "reservation_artifact_name": f"rpc_diagnostic_{anchor}.json.reservation",
        }
    )
    _rehash_header_reservation(header)


def _mutate_reservation_candidate_only(header: dict[str, Any]) -> None:
    header["reservation"]["candidate_commit"] = "d" * 40
    _rehash_header_reservation(header)


def _mutate_remote_claim_ref_everywhere(header: dict[str, Any]) -> None:
    reservation = header["reservation"]
    wrong_ref = f"refs/tags/uprime-u1-attempts/{'0' * 64}"
    reservation["claim_receipt"]["remote_claim_ref"] = wrong_ref
    reservation["remote_claim_ref"] = wrong_ref
    _rehash_receipt_and_reservation(header)


def _mutate_claim_receipt_digest(header: dict[str, Any]) -> None:
    header["reservation"]["claim_receipt_sha256"] = "0" * 64
    _rehash_header_reservation(header)


def _mutate_ledger_artifact_name(header: dict[str, Any]) -> None:
    header["reservation"]["ledger_artifact_name"] = "../transplanted.jsonl"
    _rehash_header_reservation(header)


def _must_reject(
    tmp_path: Path,
    *,
    mutate: EventMutation | None = None,
    mutate_closure: ClosureMutation | None = None,
) -> None:
    path = tmp_path / "rehashed-invalid.responses.jsonl"
    _write_fixture(path, mutate=mutate, mutate_closure=mutate_closure)
    # The standalone chain layer accepts this fixture: every adversarial edit
    # was made before the writer recomputed the full chain.
    assert chain.attest_standalone_closed_chain(path).record_count == 49
    with pytest.raises(semantics.StandaloneLedgerSemanticError):
        _attest(path)


def test_nominal_49_semantics_is_valid_but_never_confers_authority(tmp_path):
    path = tmp_path / "nominal.responses.jsonl"
    _write_fixture(path)

    result = _attest(path)

    assert result.verifier_schema_version == (
        semantics.SCHEMA_UPRIME_RPC_NOMINAL_49_SEMANTICS_VERIFIER
    )
    assert result.semantic_scope == "standalone_exact_49_sequence_semantics_only"
    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.origin_status == "unknown_may_be_synthetic"
    assert result.record_count == 49
    assert result.b4_raw_predicate is True
    assert len(result.x0_predicate_ids) == len(result.x0_predicates) == 12
    assert result.x0_predicate_ids == (
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
    assert all(result.x0_predicates)
    assert result.x0_raw_predicate_all is True
    assert result.response_id_mismatch_count == 0
    assert result.closure_primary_reason_code is None
    assert result.closure_reason_codes == ()
    assert result.full_contract_recomputation == "not_performed"
    assert result.scientific_disposition == "not_computed"
    assert result.reservation_token_verification == "not_performed"
    assert result.source_blob_authentication == "not_performed"
    assert result.remote_claim_authentication == "not_performed"
    assert result.bundle_binding == "not_performed"
    assert result.report_binding == "not_performed"
    assert result.attempt_manifest_binding == "not_performed"
    assert result.privacy_scan == "not_performed"
    assert result.archive_verification == "not_performed"
    assert result.authority_scope == "none"
    assert result.canonical_run_authority is False
    assert result.licenses_execution is False
    assert result.licenses_later_stage is False


def test_rehashed_response_echo_mismatch_is_valid_evidence_with_r0_false(tmp_path):
    def mutate(_header, _probe, events):
        _response_event(events, "primary_split")["body"]["response"]["id"] = (
            "wrong-echo-id"
        )

    path = tmp_path / "echo-mismatch.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.response_id_mismatch_count == 1
    assert result.b4_raw_predicate is True
    assert result.x0_raw_predicate_all is True
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "probe_mutation",
    [
        lambda probe: probe["resolved"].__setitem__("task_fallback", "732"),
        lambda probe: probe["resolved"].__setitem__("explicit_zero", "1"),
        lambda probe: probe["resolved"].__setitem__("explicit_nonzero", "123455"),
        lambda probe: probe["resolved"].__setitem__("omitted_default", "199999"),
        lambda probe: probe.__setitem__("explicit_key", "different-cache-key"),
        lambda probe: probe["omitted_fields"].__setitem__(
            "max_heartbeats", "199999"
        ),
        lambda probe: probe["explicit_fields"].__setitem__(
            "max_heartbeats", "199999"
        ),
    ],
    ids=(
        "task-fallback",
        "explicit-zero",
        "explicit-nonzero",
        "omitted-default",
        "key-equality",
        "omitted-key-field",
        "explicit-key-field",
    ),
)
def test_rehashed_b4_failure_is_valid_evidence_not_semantic_corruption(
    tmp_path, probe_mutation
):
    def mutate(_header, probe, _events):
        probe_mutation(probe)

    path = tmp_path / "b4-blocked.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.b4_raw_predicate is False
    assert result.x0_raw_predicate_all is True
    assert result.authority_scope == "none"


def test_rehashed_nonzero_returncode_is_valid_evidence_with_x0_false(tmp_path):
    path = tmp_path / "x0-blocked.responses.jsonl"
    _write_fixture(
        path,
        mutate_closure=lambda closure: closure.__setitem__("process_returncode", 7),
    )

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    assert _false_x0_ids(result) == {"returncode_zero"}
    assert result.b4_raw_predicate is True
    assert result.authority_scope == "none"


def test_rehashed_bad_shutdown_response_is_valid_evidence_with_x0_false(tmp_path):
    def mutate(_header, _probe, events):
        _response_event(events, "shutdown")["body"]["response"]["ok"] = False

    path = tmp_path / "bad-shutdown.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    assert _false_x0_ids(result) == {"shutdown_ack_ok"}
    assert result.authority_scope == "none"


def test_rehashed_protocol_mismatch_is_valid_for_later_contract_review(tmp_path):
    def mutate(_header, _probe, events):
        _response_event(events, "primary_split")["body"]["response"][
            "rpc_protocol_version"
        ] = "wrong-protocol"

    path = tmp_path / "protocol-mismatch.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.full_contract_recomputation == "not_performed"
    assert result.x0_raw_predicate_all is True
    assert result.authority_scope == "none"


def test_rehashed_paired_dynamic_state_change_is_self_consistent_but_unauthorized(
    tmp_path,
):
    def mutate(_header, _probe, events):
        _response_event(events, "primary_init")["body"]["response"]["state"][
            "state_id"
        ] = "synthetic-alternate-state"
        _request_event(events, "primary_split")["body"]["request"]["state_id"] = (
            "synthetic-alternate-state"
        )
        _request_event(events, "primary_split_replay")["body"]["request"][
            "before_state_id"
        ] = "synthetic-alternate-state"

    path = tmp_path / "paired-state-change.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.origin_status == "unknown_may_be_synthetic"
    assert result.remote_claim_authentication == "not_performed"
    assert result.authority_scope == "none"
    assert result.canonical_run_authority is False


def test_producer_fallback_for_missing_after_state_remains_valid_evidence(tmp_path):
    def mutate(_header, _probe, events):
        split_response = _response_event(events, "primary_split")["body"]["response"]
        split_response.pop("after_state_id")
        split_response["state"] = {"state_id": "fallback-primary-split"}
        _request_event(events, "primary_split_replay")["body"]["request"][
            "expected_after_state_id"
        ] = None
        _request_event(events, "primary_tail_close")["body"]["request"]["state_id"] = (
            "fallback-primary-split"
        )
        _request_event(events, "primary_tail_close_replay")["body"]["request"][
            "before_state_id"
        ] = "fallback-primary-split"

    path = tmp_path / "after-state-fallback.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.authority_scope == "none"


def test_producer_goal_filtering_remains_valid_but_unauthorized(tmp_path):
    def mutate(_header, _probe, events):
        goals = _response_event(events, "primary_split")["body"]["response"][
            "kernel_state_after"
        ]["goals"]
        goals.insert(1, {"mvar_id": 7, "ignored": "non-string id"})

    path = tmp_path / "filtered-goal-row.responses.jsonl"
    _write_fixture(path, mutate=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.origin_status == "unknown_may_be_synthetic"
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "closure_mutation,failed_predicate",
    [
        (
            lambda closure: closure["shutdown_transport"].__setitem__(
                "stream_complete", False
            ),
            "stream_complete",
        ),
        (
            lambda closure: closure["shutdown_transport"].__setitem__(
                "shutdown_response_sha256", "0" * 64
            ),
            "response_sha256_bound",
        ),
        (
            lambda closure: closure["shutdown_transport"].update(
                {
                    "stdout_eof_count": 0,
                    "residual_frame_kinds": [],
                    "terminal_eof_exact": False,
                }
            ),
            "terminal_eof_exact",
        ),
        (
            lambda closure: closure["shutdown_transport"].__setitem__(
                "transport_finalized", False
            ),
            "transport_finalized",
        ),
        (
            lambda closure: closure["shutdown_transport"].__setitem__(
                "post_response_elapsed_ns", None
            ),
            "post_response_elapsed_bounded",
        ),
        (
            lambda closure: closure["shutdown_transport"].update(
                {"exit_mode": None, "graceful_exit": None}
            ),
            "natural_exit_within_grace",
        ),
    ],
    ids=(
        "stream-incomplete",
        "response-hash",
        "missing-eof",
        "not-finalized",
        "missing-elapsed",
        "missing-exit-mode",
    ),
)
def test_rehashed_x0_observation_failures_remain_valid_evidence(
    tmp_path, closure_mutation, failed_predicate
):
    path = tmp_path / "x0-observation-failure.responses.jsonl"
    _write_fixture(path, mutate_closure=closure_mutation)

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    checks = dict(zip(result.x0_predicate_ids, result.x0_predicates, strict=True))
    assert checks[failed_predicate] is False
    assert all(value for key, value in checks.items() if key != failed_predicate)
    assert result.authority_scope == "none"


def test_rehashed_consistent_forced_reap_is_valid_evidence_with_x0_false(tmp_path):
    def mutate(closure):
        closure["process_returncode"] = -15
        closure["shutdown_transport"].update(
            {
                "exit_mode": "forced_terminate",
                "graceful_exit": False,
                "termination_signal_attempted": True,
                "forced_reap": True,
                "forced_reap_succeeded": True,
            }
        )

    path = tmp_path / "forced-reap.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    assert _false_x0_ids(result) == {
        "natural_exit_within_grace",
        "no_forced_reap",
        "returncode_zero",
    }
    assert result.authority_scope == "none"


def test_rehashed_non_json_observation_is_valid_evidence_with_x0_false(tmp_path):
    def mutate(closure):
        closure.update(
            {
                "non_json_stdout_count": 1,
                "reason_codes": ["NON_JSON_STDOUT"],
                "primary_reason_code": "NON_JSON_STDOUT",
            }
        )

    path = tmp_path / "non-json-observation.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    assert _false_x0_ids(result) == {"json_stdout_only"}
    assert result.authority_scope == "none"


def test_rehashed_transport_overflow_is_valid_evidence_with_x0_false(tmp_path):
    def mutate(closure):
        closure.update(
            {
                "transport_overflow": True,
                "reason_codes": ["TRANSPORT_OVERFLOW"],
                "primary_reason_code": "TRANSPORT_OVERFLOW",
            }
        )

    path = tmp_path / "transport-overflow.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert result.x0_raw_predicate_all is False
    assert _false_x0_ids(result) == {"no_transport_overflow"}
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "reason",
    (
        "CLEANUP_ERROR",
        "OTHER_HARNESS_ERROR",
        "READER_ERROR",
        "SHUTDOWN_FINALIZATION_ERROR",
    ),
)
def test_post_pair_harness_reason_is_preserved_without_scientific_disposition(
    tmp_path, reason
):
    def mutate(closure):
        closure["reason_codes"] = [reason]
        closure["primary_reason_code"] = reason

    path = tmp_path / f"post-pair-{reason.lower()}.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.closure_primary_reason_code == reason
    assert result.closure_reason_codes == (reason,)
    assert result.x0_raw_predicate_all is True
    assert result.scientific_disposition == "not_computed"
    assert result.authority_scope == "none"


@pytest.mark.parametrize("record_count", (48, 50))
def test_rehashed_closed_non_49_chain_is_rejected_by_semantic_scope(
    tmp_path, record_count
):
    path = tmp_path / f"closed-{record_count}.responses.jsonl"
    writer = chain.StandaloneChainWriter.create(path, header_body=_header_body())
    writer.append_event("local_probe", _local_probe_body())
    events = _event_bodies()
    selected = events[:45] if record_count == 48 else [*events, {
        "record_type": "request_intent",
        "body": {"synthetic_extra": True},
    }]
    for event in selected:
        writer.append_event(event["record_type"], event["body"])
    writer.close_with_closure({"sequence_status": "complete"})
    assert chain.attest_standalone_closed_chain(path).record_count == record_count

    with pytest.raises(semantics.StandaloneLedgerSemanticError):
        _attest(path)


def test_forced_reap_race_without_exit_mode_is_preserved_as_failure_evidence(
    tmp_path,
):
    def mutate(closure):
        closure["process_returncode"] = -15
        closure["shutdown_transport"].update(
            {
                "exit_mode": None,
                "graceful_exit": False,
                "termination_signal_attempted": True,
                "forced_reap": True,
                "forced_reap_succeeded": True,
                "transport_finalized": False,
            }
        )

    path = tmp_path / "forced-reap-race.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert result.semantic_status == "valid_exact_49_sequence"
    assert _false_x0_ids(result) == {
        "natural_exit_within_grace",
        "no_forced_reap",
        "returncode_zero",
        "transport_finalized",
    }
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "process_returncode,transport_updates,expected_false",
    [
        (
            0,
            {"exit_mode": "natural_after_grace", "graceful_exit": False},
            {"natural_exit_within_grace"},
        ),
        (
            -9,
            {
                "exit_mode": "forced_kill",
                "graceful_exit": False,
                "termination_signal_attempted": True,
                "kill_signal_attempted": True,
                "forced_reap": True,
                "forced_reap_succeeded": True,
            },
            {
                "natural_exit_within_grace",
                "no_forced_reap",
                "returncode_zero",
            },
        ),
        (
            -9,
            {
                "exit_mode": None,
                "graceful_exit": False,
                "termination_signal_attempted": True,
                "kill_signal_attempted": True,
                "forced_reap": True,
                "forced_reap_succeeded": False,
                "transport_finalized": False,
            },
            {
                "natural_exit_within_grace",
                "no_forced_reap",
                "returncode_zero",
                "transport_finalized",
            },
        ),
    ],
    ids=("natural-after-grace", "forced-kill", "failed-forced-reap"),
)
def test_additional_consistent_shutdown_failures_remain_valid_evidence(
    tmp_path, process_returncode, transport_updates, expected_false
):
    def mutate(closure):
        closure["process_returncode"] = process_returncode
        closure["shutdown_transport"].update(transport_updates)

    path = tmp_path / "additional-shutdown-failure.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert _false_x0_ids(result) == expected_false
    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.authority_scope == "none"


def test_bad_ack_with_consistent_forced_reap_remains_valid_evidence(tmp_path):
    def mutate_events(_header, _probe, events):
        _response_event(events, "shutdown")["body"]["response"]["ok"] = False

    def mutate_closure(closure):
        closure["process_returncode"] = -15
        closure["shutdown_transport"].update(
            {
                "exit_mode": "forced_terminate",
                "graceful_exit": False,
                "termination_signal_attempted": True,
                "forced_reap": True,
                "forced_reap_succeeded": True,
            }
        )

    path = tmp_path / "bad-ack-forced-reap.responses.jsonl"
    _write_fixture(path, mutate=mutate_events, mutate_closure=mutate_closure)

    result = _attest(path)

    assert _false_x0_ids(result) == {
        "shutdown_ack_ok",
        "natural_exit_within_grace",
        "no_forced_reap",
        "returncode_zero",
    }
    assert result.semantic_status == "valid_exact_49_sequence"
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "counter_field,reason",
    (
        ("invalid_utf8_stdout_count", "INVALID_UTF8_STDOUT"),
        ("non_object_stdout_count", "NON_OBJECT_STDOUT"),
    ),
)
def test_causal_stdout_failure_reason_pairs_remain_valid_evidence(
    tmp_path, counter_field, reason
):
    def mutate(closure):
        closure["non_json_stdout_count"] = 1
        closure[counter_field] = 1
        closure["reason_codes"] = [reason]
        closure["primary_reason_code"] = reason

    path = tmp_path / f"causal-{reason.lower()}.responses.jsonl"
    _write_fixture(path, mutate_closure=mutate)

    result = _attest(path)

    assert _false_x0_ids(result) == {"json_stdout_only"}
    assert result.closure_reason_codes == (reason,)
    assert result.authority_scope == "none"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda _h, _p, events: _request_event(events, "primary_init")[
            "body"
        ].__setitem__("intent_at_utc", "2026-13-11T00:00:00.000000Z"),
        lambda _h, _p, events: _response_event(events, "load")["body"].__setitem__(
            "received_monotonic_ns", 9
        ),
        lambda _h, _p, events: _request_event(events, "primary_init")[
            "body"
        ].__setitem__("intent_monotonic_ns", 5),
        lambda _h, _p, events: _response_event(events, "primary_init")[
            "body"
        ].__setitem__("received_monotonic_ns", -1),
    ],
    ids=("invalid-utc", "response-before-intent", "global-backwards", "negative"),
)
def test_rehashed_timestamp_and_monotonic_drift_is_rejected(tmp_path, mutation):
    _must_reject(tmp_path, mutate=mutation)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda header, _p, _e: header["expected_frame_labels"].__setitem__(0, "status"),
        lambda header, _p, _e: header.__setitem__("reservation_sha256", "0" * 64),
        lambda header, _p, _e: _set_reservation_field_and_rehash(
            header, "expected_frame_count", 22
        ),
        lambda _h, probe, _e: probe["payloads"]["explicit_zero"]["action"].__setitem__("max_heartbeats", 1),
        lambda _h, probe, _e: probe["payloads"]["explicit_zero"]["action"].__setitem__("max_heartbeats", False),
        lambda _h, probe, _e: probe["key_kwargs"].__setitem__("trace_state", 0),
        lambda _h, probe, _e: probe.__setitem__("passed", True),
        lambda _h, probe, _e: probe["source_blobs"].pop("lean_rgc/schemas.py"),
    ],
    ids=(
        "header-label-manifest",
        "reservation-digest",
        "reservation-frame-count",
        "frozen-probe-input",
        "probe-bool-for-zero",
        "probe-int-for-bool",
        "probe-derived-boolean",
        "probe-source-set",
    ),
)
def test_rehashed_frozen_header_and_probe_schema_drift_is_rejected(
    tmp_path, mutation
):
    _must_reject(tmp_path, mutate=mutation)


@pytest.mark.parametrize(
    "header_mutation",
    [
        _mutate_derived_license_identity,
        _mutate_remote_claim_oid,
        _mutate_reservation_anchor_with_matching_names,
        _mutate_reservation_candidate_only,
        _mutate_remote_claim_ref_everywhere,
        _mutate_claim_receipt_digest,
        _mutate_ledger_artifact_name,
        lambda header: (
            header["reservation"]["claim_receipt"].__setitem__("extra", True),
            _rehash_receipt_and_reservation(header),
        ),
        lambda header: (
            header["reservation"].__setitem__("extra", True),
            _rehash_header_reservation(header),
        ),
    ],
    ids=(
        "license-id-derivation",
        "remote-oid-license-binding",
        "anchor-license-prefix",
        "candidate-cross-binding",
        "derived-claim-ref",
        "claim-receipt-digest",
        "artifact-basename",
        "receipt-extra-field",
        "reservation-extra-field",
    ),
)
def test_rehashed_receipt_and_reservation_relation_drift_is_rejected(
    tmp_path, header_mutation
):
    def mutate(header, _probe, _events):
        header_mutation(header)

    _must_reject(tmp_path, mutate=mutate)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda _h, _p, events: _request_event(events, "primary_split")["body"].__setitem__("frame_index", 4),
        lambda _h, _p, events: _request_event(events, "primary_split")["body"].__setitem__("frame_label", "zero_split"),
        lambda _h, _p, events: _request_event(events, "primary_split")["body"].__setitem__("expected_request_id", "wrong-metadata-id"),
        lambda _h, _p, events: _request_event(events, "primary_split")["body"].__setitem__("durability_marker", "written_after_stdin"),
        lambda _h, _p, events: _request_event(events, "primary_split")["body"].__setitem__("unexpected", True),
        lambda _h, _p, events: _request_event(events, "load")["body"].__setitem__("frame_index", True),
    ],
    ids=(
        "frame-index",
        "frame-label",
        "expected-id",
        "durability",
        "extra-metadata",
        "bool-for-frame-one",
    ),
)
def test_rehashed_request_metadata_drift_is_semantically_rejected(tmp_path, mutation):
    _must_reject(tmp_path, mutate=mutation)


@pytest.mark.parametrize(
    "label,request_mutation",
    [
        ("load", lambda request: request.__setitem__("imports", ["Mathlib"])),
        ("primary_init", lambda request: request["task"].__setitem__("max_heartbeats", 732)),
        ("primary_split", lambda request: request["action"].__setitem__("max_heartbeats", 123_455)),
        ("primary_tail_close", lambda request: request.__setitem__("state_id", "wrong-state")),
        ("primary_tail_close", lambda request: request.__setitem__("target_mvar_id", "primary-head")),
        ("primary_split_replay", lambda request: request.__setitem__("expected_after_state_id", "wrong-after")),
        ("side_effect_close", lambda request: request.__setitem__("target_mvar_id", "side-witness")),
        ("status", lambda request: request.__setitem__("extra_operational_key", True)),
        ("zero_split", lambda request: request["action"].__setitem__("max_heartbeats", False)),
    ],
    ids=(
        "load-imports",
        "task-budget",
        "action-budget",
        "state-continuity",
        "target-routing",
        "replay-after",
        "side-selector",
        "extra-request-key",
        "bool-for-zero-budget",
    ),
)
def test_rehashed_full_request_object_drift_is_semantically_rejected(
    tmp_path, label, request_mutation
):
    def mutate(_header, _probe, events):
        request_mutation(_request_event(events, label)["body"]["request"])

    _must_reject(tmp_path, mutate=mutate)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda _h, _p, events: events.__setitem__(2, copy.deepcopy(events[3])),
        lambda _h, _p, events: events.__setitem__(slice(2, 4), [events[3], events[2]]),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("arrival_index", 2),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("frame_index", 4),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("frame_label", "primary_init"),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("expected_request_id", "wrong-association-id"),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("association", "duplicate_for_frame"),
        lambda _h, _p, events: _response_event(events, "primary_split")["body"].__setitem__("frame_index", None),
        lambda _h, _p, events: _response_event(events, "load")["body"].__setitem__("arrival_index", True),
    ],
    ids=(
        "response-in-request-slot",
        "response-before-request",
        "arrival-index-gap",
        "response-frame-index",
        "response-frame-label",
        "response-expected-id",
        "non-active-association",
        "association-triad",
        "bool-for-arrival-one",
    ),
)
def test_rehashed_order_frame_arrival_and_association_drift_is_rejected(
    tmp_path, mutation
):
    _must_reject(tmp_path, mutate=mutation)


@pytest.mark.parametrize(
    "closure_mutation",
    [
        lambda closure: closure.__setitem__("local_probe_count", 0),
        lambda closure: closure.__setitem__("request_intent_count", 22),
        lambda closure: closure.__setitem__("parsed_response_count", 22),
        lambda closure: closure.__setitem__("expected_frame_count", 22),
        lambda closure: closure.__setitem__("expected_frame_manifest_sha256", "0" * 64),
        lambda closure: closure.__setitem__("observed_request_frame_indices", list(range(23, 0, -1))),
        lambda closure: closure.__setitem__("observed_response_frame_indices", list(range(1, 23))),
        lambda closure: closure.__setitem__("missing_request_frame_indices", [23]),
        lambda closure: closure.__setitem__("missing_response_frame_indices", [23]),
        lambda closure: closure.__setitem__("duplicate_request_frame_indices", [1]),
        lambda closure: closure.__setitem__("duplicate_response_frame_indices", [1]),
        lambda closure: closure.__setitem__("response_id_mismatch_count", 1),
        lambda closure: closure.__setitem__("local_probe_count", True),
    ],
    ids=(
        "probe-count",
        "request-count",
        "response-count",
        "expected-count",
        "manifest",
        "request-order",
        "response-order",
        "missing-request",
        "missing-response",
        "duplicate-request",
        "duplicate-response",
        "id-mismatch-count",
        "bool-for-probe-count-one",
    ),
)
def test_rehashed_closure_accounting_contradictions_are_rejected(
    tmp_path, closure_mutation
):
    _must_reject(tmp_path, mutate_closure=closure_mutation)


@pytest.mark.parametrize(
    "closure_mutation",
    [
        lambda closure: closure.__setitem__("preclosure_record_sha256", "0" * 64),
        lambda closure: closure["shutdown_transport"].__setitem__(
            "shutdown_ack_ok", False
        ),
    ],
    ids=("preclosure-head", "shutdown-ack"),
)
def test_rehashed_head_and_shutdown_binding_contradictions_are_rejected(
    tmp_path, closure_mutation
):
    _must_reject(tmp_path, mutate_closure=closure_mutation)


@pytest.mark.parametrize(
    "closure_mutation",
    [
        lambda closure: closure["shutdown_transport"].__setitem__(
            "termination_signal_attempted", True
        ),
        lambda closure: closure["shutdown_transport"].__setitem__(
            "forced_reap_succeeded", True
        ),
        lambda closure: closure["shutdown_transport"].__setitem__(
            "reader_threads_drained", False
        ),
        lambda closure: closure.__setitem__("invalid_utf8_stdout_count", 1),
        lambda closure: closure.__setitem__("non_object_stdout_count", 1),
        lambda closure: closure["shutdown_transport"].update(
            {"residual_response_count": 1, "residual_frame_kinds": ["eof"]}
        ),
        lambda closure: closure["shutdown_transport"].__setitem__(
            "stdout_eof_count", 0
        ),
        lambda closure: closure.update(
            {
                "reason_codes": ["REQUEST_TIMEOUT"],
                "primary_reason_code": "REQUEST_TIMEOUT",
            }
        ),
    ],
    ids=(
        "natural-with-terminate",
        "success-without-forced-reap",
        "reader-flag-disagreement",
        "invalid-utf8-subcount",
        "non-object-subcount",
        "residual-count-kinds",
        "terminal-eof-count",
        "impossible-complete-reason",
    ),
)
def test_rehashed_lifecycle_contradictions_are_rejected(tmp_path, closure_mutation):
    _must_reject(tmp_path, mutate_closure=closure_mutation)
