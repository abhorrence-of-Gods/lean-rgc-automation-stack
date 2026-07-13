from __future__ import annotations

import sys


# In the official process this is deliberately the only executable bootstrap
# before the parent proves Job membership and sends PROBE.  In particular no
# repository package, site package, path helper, or process module is loaded.
_INITIAL_PROBE_LINE: bytes | None = None
if __name__ == "__main__":
    if sys.argv[1:] != ["--official-child"] or __package__ not in {None, ""}:
        sys.stderr.write("uprime-official-transport: exact --official-child invocation required\n")
        raise SystemExit(64)
    _INITIAL_PROBE_LINE = sys.stdin.buffer.readline(193)


import builtins
import hashlib
import json
import os
import pathlib
import queue
import stat
import subprocess
import threading
import time


ARTIFACT_SCHEMA = "lean-rgc-uprime-official-transport-artifact-v2.0"
PROBE_SCHEMA = "lean-rgc-uprime-official-transport-probe-v2.0"
READY_SCHEMA = "lean-rgc-uprime-official-transport-ready-v2.0"
ARM_SCHEMA = "lean-rgc-uprime-official-transport-arm-v2.0"
CHILD_RESULT_SCHEMA = "lean-rgc-uprime-official-transport-child-result-v2.0"
RECEIPT_SCHEMA = "lean-rgc-uprime-official-transport-receipt-v2.0"
TIMING_SCHEMA = "lean-rgc-uprime-official-transport-timing-v2.0"
TRANSCRIPT_SCHEMA = "lean-rgc-uprime-official-transport-transcript-v2.0"
RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
U05_SEMANTICS_VERSION = "lean-rgc-u05-rpc-semantics-v1"
REPLAY_SCHEMA = "lean-rgc-u05-replay-v1"
KERNEL_BACKEND = "lean_kernel_rpc_in_memory_v1"
EXTERNAL_ATTESTATION_SCOPE = "EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER"

FIXED_PYTHON_VERSION = "3.13.7"
FIXED_PYTHON_SHA256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
FIXED_POWERSHELL_VERSION = "5.1.26100.8655"
FIXED_POWERSHELL_SHA256 = "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46"
FIXED_LEAN_VERSION = "4.31.0"
FIXED_LEAN_COMMIT = "68218e876d2a38b1985b8590fff244a83c321783"
FIXED_LEAN_SHA256 = "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
FIXED_WORKER_BLOB = "305509d9b89081a3d002734e09724b98e244a24c"
FIXED_WORKER_SHA256 = "741E19237C829BA5E76E895EDB20ECD26517804C5CEE4FF8C711946739AB3A14"

PROBE_PREFIX = PROBE_SCHEMA.encode("ascii")
PROBE_MAX_BYTES = 192
ARM_MAX_BYTES = 32 * 1024
ARTIFACT_MAX_BYTES = 1 * 1024 * 1024
RECEIPT_MAX_BYTES = 1 * 1024 * 1024
RESPONSE_MAX_BYTES = 4 * 1024 * 1024
STREAM_LIMIT_BYTES = 1 * 1024 * 1024
JOB_LIMIT_BYTES = 1 * 1024 * 1024 * 1024
MAX_NS = (1 << 63) - 1

I1_FILE_PATHS = frozenset(
    {
        "tools/uprime_official_transport_v2_smoke.py",
        "tools/run_uprime_official_transport_v2_smoke.ps1",
        "tools/run_uprime_official_transport_v2_tests.ps1",
        "tests/test_uprime_official_transport_v2_smoke.py",
        "tests/tier_manifest.json",
    }
)

IDENTITY_FIELDS = frozenset(
    {
        "accepted_commit",
        "accepted_tree",
        "accepted_run_id",
        "accepted_job_id",
        "candidate_run_id",
        "candidate_job_id",
        "attestation_scope",
        "i1_file_sha256",
        "powershell_version",
        "powershell_sha256",
        "python_version",
        "python_sha256",
        "lean_version",
        "lean_commit",
        "lean_sha256",
        "worker_blob",
        "worker_sha256",
    }
)

CHILD_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "nonce",
        "fixture_role",
        "process_ordinal",
        "run_state",
        "scientific_disposition",
        "failure_code",
        "identity_digest",
        "environment_digest",
        "leaf_sha256",
        "worker_blob",
        "worker_sha256",
        "timing_policy",
        "timing_policy_digest",
        "timing_frames",
        "transcript",
        "payload",
        "resource_evidence",
    }
)

SUCCESS_PAYLOAD_FIELDS = frozenset(
    {
        "closed",
        "final_n_states",
        "init_response_digest",
        "n_primary_executions",
        "n_replay_executions",
        "natural_lean_exit_code",
        "ownership_zero",
        "request_count",
        "rpc_protocol_version",
        "shutdown_ack_digest",
        "transition_response_digest",
    }
)

RESOURCE_EVIDENCE_FIELDS = frozenset(
    {"cap_name", "cap_value", "observed_value", "stage"}
)

RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "receipt_kind",
        "nonce",
        "fixture_role",
        "process_ordinal",
        "child_result_length",
        "child_result_sha256",
        "environment_digest",
        "identity_digest",
        "leaf_sha256",
        "worker_sha256",
        "timing_policy_digest",
    }
)

ARM_FIELDS = frozenset(
    {
        "schema_version",
        "nonce",
        "lean_executable",
        "lean_sha256",
        "worker_path",
        "worker_blob",
        "worker_sha256",
        "repo_root",
        "run_temp",
        "child_result_path",
        "child_receipt_path",
        "fixture_role",
        "process_ordinal",
        "environment_digest",
        "identity",
        "timing_policy",
        "timing_policy_digest",
        "response_limit_bytes",
        "stream_limit_bytes",
        "artifact_limit_bytes",
        "receipt_limit_bytes",
        "request_count",
        "task_count",
        "action_count",
        "max_open_states",
    }
)

READY_FIELDS = frozenset(
    {
        "schema_version",
        "nonce",
        "pid",
        "job_assignment_receipt_digest",
        "leaf_sha256",
        "python_flags_digest",
        "sys_path_digest",
        "import_fence_passed",
        "loaded_lean_rgc_modules",
    }
)

ORDINARY_FAILURES = {
    "SYNTHETIC_BATCH_EXECUTION_FAILED": "BATCH_EXECUTION_FAILED",
    "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED": "QUALIFICATION_MARGIN_BLOCKED",
    "SYNTHETIC_EXECUTION_FAILED": "EXECUTION_FAILED",
    "SYNTHETIC_IMPORT_BLOCKED": "IMPORT_BLOCKED",
    "SYNTHETIC_SCOPE_VIOLATION": "SCOPE_VIOLATION",
    "SYNTHETIC_RPC_BLOCKED": "RPC_BLOCKED",
    "SYNTHETIC_ARTIFACT_BLOCKED": "ARTIFACT_BLOCKED",
}

EXIT_BY_DISPOSITION = {
    "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED": 0,
    "SYNTHETIC_BATCH_EXECUTION_FAILED": 69,
    "SYNTHETIC_EXECUTION_FAILED": 70,
    "SYNTHETIC_IMPORT_BLOCKED": 71,
    "SYNTHETIC_SCOPE_VIOLATION": 72,
    "SYNTHETIC_RPC_BLOCKED": 73,
    "SYNTHETIC_RESOURCE_BLOCKED": 74,
    "SYNTHETIC_ARTIFACT_BLOCKED": 75,
    "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED": 76,
}

TASK = {
    "task_id": "synthetic_isolated_identity_v1",
    "imports": ["Lean"],
    "statement": "∀ (p : Prop), p → p",
    "prefix": "intro p\nintro h",
    "max_heartbeats": 20_000,
}

ACTION = {
    "action_id": "synthetic_exact_h",
    "tactic": "exact h",
    "target_selector": "first",
    "max_heartbeats": 20_000,
}

REQUEST_IDS = (
    "i1-v2-01-load",
    "i1-v2-02-status-initial",
    "i1-v2-03-init",
    "i1-v2-04-apply",
    "i1-v2-05-discard-child",
    "i1-v2-06-discard-source",
    "i1-v2-07-status-final",
    "i1-v2-08-shutdown",
)

TIMING_POLICY = {
    "action": {"authority": "child_monotonic_ns", "hard_wall_ns": 15_000_000_000, "success_margin_ns": 5_000_000_000},
    "artifact_publication": {"authority": "parent_stopwatch_ticks", "hard_wall_seconds": 30, "success_margin_seconds": 10},
    "batch_execution": {"authority": "parent_stopwatch_ticks", "hard_wall_seconds": 1_200, "success_margin_seconds": 400},
    "control": {"authority": "child_monotonic_ns", "hard_wall_ns": 30_000_000_000, "success_margin_ns": 10_000_000_000},
    "control_initialization": {"authority": "child_monotonic_ns", "hard_wall_ns": 30_000_000_000, "success_margin_ns": 10_000_000_000},
    "fixture_execution": {"authority": "parent_stopwatch_ticks", "hard_wall_seconds": 300, "success_margin_seconds": 100},
    "python_ready": {"authority": "parent_stopwatch_ticks", "hard_wall_seconds": 15, "success_margin_seconds": 5},
    "shutdown": {"authority": "child_monotonic_ns", "hard_wall_ns": 10_000_000_000, "success_margin_ns": 3_000_000_000},
    "startup_load": {"authority": "child_monotonic_ns", "hard_wall_ns": 120_000_000_000, "success_margin_ns": 40_000_000_000},
    "unit_whole": {"authority": "parent_stopwatch_ticks", "hard_wall_seconds": 30, "success_margin_seconds": 10},
}

REQUEST_TIMING_CLASSES = (
    "startup_load", "control", "control_initialization", "action",
    "control", "control", "control", "shutdown",
)

TIMING_FIELDS = frozenset(
    {"schema_version", "sequence", "request_id", "clock_class", "start_ns", "end_ns",
     "elapsed_ns", "hard_wall_ns", "success_margin_ns", "classification", "completed"}
)

TRANSCRIPT_FIELDS = frozenset(
    {"schema_version", "request_ids", "ordered_request_digests",
     "ordered_response_digests", "ordered_transcript_digest"}
)


class TransportError(RuntimeError):
    def __init__(self, message: str, *, timing_frames: list[dict[str, object]] | None = None):
        super().__init__(message)
        self.timing_frames = [] if timing_frames is None else timing_frames


class TransportResourceError(TransportError):
    def __init__(self, message: str, *, cap_name: str, cap_value: int, observed_value: int, stage: str, timing_frames: list[dict[str, object]] | None = None):
        super().__init__(message, timing_frames=timing_frames)
        self.evidence = {
            "cap_name": cap_name,
            "cap_value": cap_value,
            "observed_value": observed_value,
            "stage": stage,
        }


class TransportMarginError(TransportError):
    pass


class ScopeViolation(RuntimeError):
    pass


class ArtifactError(RuntimeError):
    pass


def timing_policy_digest() -> str:
    return _sha_value(TIMING_POLICY)


def checked_deadline_ns(start_ns: int, hard_wall_ns: int) -> int:
    if type(start_ns) is not int or type(hard_wall_ns) is not int:
        raise TransportResourceError(
            "timing value is not an integer", cap_name="monotonic_ns", cap_value=MAX_NS,
            observed_value=MAX_NS, stage="timing",
        )
    if start_ns < 0 or hard_wall_ns <= 0 or start_ns > MAX_NS - hard_wall_ns:
        raise TransportResourceError(
            "timing deadline overflows", cap_name="monotonic_ns", cap_value=MAX_NS,
            observed_value=max(start_ns, 0), stage="timing",
        )
    return start_ns + hard_wall_ns


def remaining_timeout_seconds(deadline_ns: int, clock_ns: object) -> float:
    now = clock_ns()
    if type(now) is not int or now < 0 or now > MAX_NS:
        raise TransportResourceError(
            "invalid monotonic clock", cap_name="monotonic_ns", cap_value=MAX_NS,
            observed_value=max(now, 0) if type(now) is int else MAX_NS, stage="timing",
        )
    remaining = deadline_ns - now
    if remaining <= 0:
        raise TransportResourceError(
            "absolute deadline exhausted", cap_name="absolute_deadline_ns", cap_value=deadline_ns,
            observed_value=now, stage="timing",
        )
    # This conversion is only a blocking-wait input.  Every scientific boundary
    # is decided later from the original integer timestamps.
    return remaining / 1_000_000_000


def _bounded_blocking_call(operation: object, *, deadline_ns: int, clock_ns: object, stage: str) -> object:
    """Run one potentially blocking OS call under the existing absolute deadline."""
    outcomes: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            outcome = (True, operation())
        except BaseException as exc:
            outcome = (False, exc)
        try:
            outcomes.put_nowait(outcome)
        except queue.Full:
            pass

    threading.Thread(target=invoke, daemon=True).start()
    try:
        ok, value = outcomes.get(timeout=remaining_timeout_seconds(deadline_ns, clock_ns))
    except queue.Empty as exc:
        now = clock_ns()
        raise TransportResourceError(
            f"{stage} exceeded its absolute deadline",
            cap_name="absolute_deadline_ns", cap_value=deadline_ns,
            observed_value=now if type(now) is int else deadline_ns + 1, stage=stage,
        ) from exc
    now = clock_ns()
    if type(now) is not int or now < 0 or now > deadline_ns:
        raise TransportResourceError(
            f"{stage} completed after its absolute deadline",
            cap_name="absolute_deadline_ns", cap_value=deadline_ns,
            observed_value=now if type(now) is int else deadline_ns + 1, stage=stage,
        )
    if not ok:
        assert isinstance(value, BaseException)
        raise value
    return value


def classify_elapsed_ns(elapsed_ns: int, *, hard_wall_ns: int, success_margin_ns: int) -> str:
    if type(elapsed_ns) is not int or elapsed_ns < 0:
        raise ValueError("elapsed nanoseconds must be a nonnegative integer")
    if elapsed_ns > hard_wall_ns:
        return "RESOURCE_BLOCKED"
    if elapsed_ns > success_margin_ns:
        return "QUALIFICATION_MARGIN_BLOCKED"
    return "PASS"


def _timing_frame(
    *, sequence: int, request_id: str, clock_class: str, start_ns: int, end_ns: int,
    completed: bool, failed: bool = False,
) -> dict[str, object]:
    if type(start_ns) is not int or type(end_ns) is not int or start_ns < 0 or end_ns < start_ns:
        raise ValueError("negative or decreasing child clock")
    policy = TIMING_POLICY[clock_class]
    if policy["authority"] != "child_monotonic_ns":
        raise ValueError("request timing class is not child-authoritative")
    hard = int(policy["hard_wall_ns"])
    margin = int(policy["success_margin_ns"])
    elapsed = end_ns - start_ns
    classification = classify_elapsed_ns(elapsed, hard_wall_ns=hard, success_margin_ns=margin)
    if failed and classification == "PASS":
        classification = "FAILED"
    frame = {
        "schema_version": TIMING_SCHEMA,
        "sequence": sequence,
        "request_id": request_id,
        "clock_class": clock_class,
        "start_ns": start_ns,
        "end_ns": end_ns,
        "elapsed_ns": elapsed,
        "hard_wall_ns": hard,
        "success_margin_ns": margin,
        "classification": classification,
        "completed": completed,
    }
    _exact(frame, TIMING_FIELDS, "timing frame")
    return frame


def validate_timing_frames(value: object, *, completed_process: bool) -> list[dict[str, object]]:
    if type(value) is not list or len(value) > len(REQUEST_IDS):
        raise ValueError("timing evidence is not a bounded list")
    if not value and not completed_process:
        return []
    if completed_process and len(value) != len(REQUEST_IDS):
        raise ValueError("completed process lacks all timing frames")
    frames: list[dict[str, object]] = []
    previous_end = -1
    for index, raw in enumerate(value):
        frame = _exact(raw, TIMING_FIELDS, "timing frame")
        if (
            frame["schema_version"] != TIMING_SCHEMA
            or frame["sequence"] != index + 1
            or frame["request_id"] != REQUEST_IDS[index]
            or frame["clock_class"] != REQUEST_TIMING_CLASSES[index]
        ):
            raise ValueError("timing prefix is reordered, gapped, or misclassified")
        start = _integer(frame["start_ns"], "timing start")
        end = _integer(frame["end_ns"], "timing end")
        elapsed = _integer(frame["elapsed_ns"], "timing elapsed")
        policy = TIMING_POLICY[REQUEST_TIMING_CLASSES[index]]
        if (
            start < previous_end or end < start or elapsed != end - start
            or frame["hard_wall_ns"] != policy["hard_wall_ns"]
            or frame["success_margin_ns"] != policy["success_margin_ns"]
        ):
            raise ValueError("timing values are negative, decreasing, or policy-mismatched")
        expected = classify_elapsed_ns(
            elapsed, hard_wall_ns=int(policy["hard_wall_ns"]),
            success_margin_ns=int(policy["success_margin_ns"]),
        )
        terminal = index == len(value) - 1
        if frame["completed"] is True:
            if frame["classification"] != expected:
                raise ValueError("completed timing classification mismatch")
        elif frame["completed"] is False:
            if not terminal or frame["classification"] not in {"FAILED", "RESOURCE_BLOCKED", "QUALIFICATION_MARGIN_BLOCKED"}:
                raise ValueError("failure timing must be the terminal frame")
            if expected != "PASS" and frame["classification"] != expected:
                raise ValueError("failure timing boundary classification mismatch")
        else:
            raise ValueError("timing completed flag is not Boolean")
        if not terminal and frame["completed"] is not True:
            raise ValueError("nonterminal timing frame is incomplete")
        previous_end = end
        frames.append(frame)
    if completed_process and any(frame["completed"] is not True for frame in frames):
        raise ValueError("completed process contains terminal failure timing")
    return frames


def _exact(value: object, fields: frozenset[str] | set[str], where: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"{where} field mismatch")
    return value


def _text(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{where} must be nonempty text")
    return value


def _integer(value: object, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{where} must be an integer >= {minimum}")
    return value


def _hex(value: object, where: str, length: int, *, uppercase: bool) -> str:
    text = _text(value, where)
    alphabet = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
    if len(text) != length or any(ch not in alphabet for ch in text):
        raise ValueError(f"{where} is malformed hexadecimal text")
    return text


def _positive_decimal(value: object, where: str) -> str:
    text = _text(value, where)
    if not text.isascii() or not text.isdigit() or text.startswith("0"):
        raise ValueError(f"{where} must be a canonical positive decimal")
    return text


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_float(_value: str) -> None:
    raise ValueError("floating-point JSON is forbidden")


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON is forbidden")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _parse_json_bytes(raw: bytes, *, where: str, maximum: int, line: bool) -> dict[str, object]:
    if type(raw) is not bytes or not raw or len(raw) > maximum:
        raise ValueError(f"{where} is empty or over cap")
    body = raw
    if line:
        if not raw.endswith(b"\n") or b"\r" in raw or b"\n" in raw[:-1]:
            raise ValueError(f"{where} is not one LF-terminated line")
        body = raw[:-1]
    elif raw.endswith((b"\n", b"\r")):
        raise ValueError(f"{where} has trailing bytes")
    try:
        text = body.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{where} is not strict JSON") from exc
    if type(value) is not dict or canonical_bytes(value) != body:
        raise ValueError(f"{where} is not canonical JSON")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _sha_value(value: object) -> str:
    return _sha256(canonical_bytes(value))


def _sha_file(path: pathlib.Path, *, maximum: int | None = None) -> str:
    size = path.stat().st_size
    if maximum is not None and size > maximum:
        raise ValueError("file exceeds its byte cap")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65_536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().upper()


def _git_blob_oid(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    framed = f"blob {len(raw)}\0".encode("ascii") + raw
    return hashlib.sha1(framed).hexdigest()


def parse_probe_line(raw: bytes) -> tuple[str, str]:
    if type(raw) is not bytes or not raw.endswith(b"\n") or len(raw) > PROBE_MAX_BYTES:
        raise ValueError("PROBE must be one bounded LF line")
    parts = raw[:-1].split(b"|")
    if len(parts) != 3 or parts[0] != PROBE_PREFIX:
        raise ValueError("PROBE framing changed")
    try:
        nonce = parts[1].decode("ascii")
        receipt = parts[2].decode("ascii")
    except UnicodeError as exc:
        raise ValueError("PROBE is not ASCII") from exc
    _hex(nonce, "PROBE nonce", 32, uppercase=False)
    _hex(receipt, "Job assignment receipt", 64, uppercase=True)
    return nonce, receipt


def validate_identity(value: object) -> dict[str, object]:
    identity = _exact(value, IDENTITY_FIELDS, "identity")
    for name in ("accepted_commit", "accepted_tree"):
        _hex(identity[name], name, 40, uppercase=False)
    for name in ("accepted_run_id", "accepted_job_id", "candidate_run_id", "candidate_job_id"):
        _positive_decimal(identity[name], name)
    if identity["attestation_scope"] != EXTERNAL_ATTESTATION_SCOPE:
        raise ValueError("attestation scope changed")
    files = identity["i1_file_sha256"]
    if type(files) is not dict or set(files) != I1_FILE_PATHS:
        raise ValueError("I1 file digest path set changed")
    for digest in files.values():
        _hex(digest, "I1 file SHA-256", 64, uppercase=True)
    fixed = {
        "powershell_version": FIXED_POWERSHELL_VERSION,
        "powershell_sha256": FIXED_POWERSHELL_SHA256,
        "python_version": FIXED_PYTHON_VERSION,
        "python_sha256": FIXED_PYTHON_SHA256,
        "lean_version": FIXED_LEAN_VERSION,
        "lean_commit": FIXED_LEAN_COMMIT,
        "lean_sha256": FIXED_LEAN_SHA256,
        "worker_blob": FIXED_WORKER_BLOB,
        "worker_sha256": FIXED_WORKER_SHA256,
    }
    if any(identity[name] != expected for name, expected in fixed.items()):
        raise ValueError("frozen identity changed")
    return identity


def _validate_success_payload(value: object) -> dict[str, object]:
    payload = _exact(value, SUCCESS_PAYLOAD_FIELDS, "success payload")
    if (
        payload["closed"] is not True
        or payload["final_n_states"] != 0
        or payload["n_primary_executions"] != 1
        or payload["n_replay_executions"] != 1
        or payload["natural_lean_exit_code"] != 0
        or payload["ownership_zero"] is not True
        or payload["request_count"] != 8
        or payload["rpc_protocol_version"] != RPC_PROTOCOL_VERSION
    ):
        raise ValueError("success payload invariant failed")
    for name in (
        "init_response_digest",
        "shutdown_ack_digest",
        "transition_response_digest",
    ):
        _hex(payload[name], name, 64, uppercase=True)
    return payload


def _validate_role(role: object, ordinal: object) -> tuple[str, int]:
    role_text = _text(role, "fixture role")
    number = _integer(ordinal, "process ordinal", minimum=1)
    if (role_text == "QUALIFICATION" and number in range(1, 6)) or (role_text == "ARCHIVAL" and number == 6):
        return role_text, number
    raise ValueError("fixture role/process ordinal mismatch")


def validate_transcript(value: object) -> dict[str, object]:
    transcript = _exact(value, TRANSCRIPT_FIELDS, "transcript")
    if transcript["schema_version"] != TRANSCRIPT_SCHEMA or transcript["request_ids"] != list(REQUEST_IDS):
        raise ValueError("transcript schema or request order changed")
    requests = transcript["ordered_request_digests"]
    responses = transcript["ordered_response_digests"]
    if type(requests) is not list or type(responses) is not list or len(requests) != 8 or len(responses) != 8:
        raise ValueError("transcript does not contain exactly eight frames")
    for digest in requests + responses:
        _hex(digest, "transcript digest", 64, uppercase=True)
    rows = [
        {"request_sha256": requests[index], "response_sha256": responses[index]}
        for index in range(8)
    ]
    if transcript["ordered_transcript_digest"] != _sha_value(rows):
        raise ValueError("transcript digest mismatch")
    return transcript


def parse_child_result(raw: bytes) -> dict[str, object]:
    value = _parse_json_bytes(raw, where="child result", maximum=ARTIFACT_MAX_BYTES, line=False)
    result = _exact(value, CHILD_RESULT_FIELDS, "child result")
    if result["schema_version"] != CHILD_RESULT_SCHEMA or result["run_state"] != "CHILD_RESULT_COMMITTED":
        raise ValueError("child-result schema or state changed")
    _validate_role(result["fixture_role"], result["process_ordinal"])
    _hex(result["nonce"], "child-result nonce", 32, uppercase=False)
    _hex(result["identity_digest"], "identity digest", 64, uppercase=True)
    _hex(result["environment_digest"], "environment digest", 64, uppercase=True)
    _hex(result["leaf_sha256"], "leaf SHA-256", 64, uppercase=True)
    if result["worker_blob"] != FIXED_WORKER_BLOB or result["worker_sha256"] != FIXED_WORKER_SHA256:
        raise ValueError("child-result worker identity changed")
    if result["timing_policy"] != TIMING_POLICY or result["timing_policy_digest"] != timing_policy_digest():
        raise ValueError("child-result timing policy changed")
    disposition = result["scientific_disposition"]
    success = disposition == "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED"
    frames = validate_timing_frames(result["timing_frames"], completed_process=success)
    if success:
        if result["failure_code"] is not None or result["resource_evidence"] is not None:
            raise ValueError("successful child result has failure evidence")
        _validate_success_payload(result["payload"])
        validate_transcript(result["transcript"])
        if any(frame["classification"] != "PASS" for frame in frames):
            raise ValueError("successful child result contains a blocked timing")
    else:
        expected = ORDINARY_FAILURES.get(disposition)
        if disposition == "SYNTHETIC_RESOURCE_BLOCKED":
            expected = "RESOURCE_BLOCKED"
        if expected is None or result["failure_code"] != expected or result["payload"] is not None:
            raise ValueError("child failure disposition is inconsistent")
        if result["transcript"] is not None:
            raise ValueError("child failure may not mint a complete transcript")
        if disposition == "SYNTHETIC_RESOURCE_BLOCKED":
            evidence = _exact(result["resource_evidence"], RESOURCE_EVIDENCE_FIELDS, "resource evidence")
            _text(evidence["cap_name"], "resource cap name")
            _integer(evidence["cap_value"], "resource cap")
            _integer(evidence["observed_value"], "resource observation")
            _text(evidence["stage"], "resource stage")
        elif result["resource_evidence"] is not None:
            raise ValueError("non-resource child result has resource evidence")
    return result


def validate_receipt(raw: bytes, child_result_raw: bytes, identity: dict[str, object]) -> dict[str, object]:
    receipt = _parse_json_bytes(raw, where="receipt", maximum=RECEIPT_MAX_BYTES, line=False)
    _exact(receipt, RECEIPT_FIELDS, "receipt")
    result = parse_child_result(child_result_raw)
    files = identity["i1_file_sha256"]
    assert type(files) is dict
    if (
        receipt["schema_version"] != RECEIPT_SCHEMA
        or receipt["receipt_kind"] != "CHILD_RESULT"
        or receipt["nonce"] != result["nonce"]
        or receipt["fixture_role"] != result["fixture_role"]
        or receipt["process_ordinal"] != result["process_ordinal"]
        or receipt["child_result_length"] != len(child_result_raw)
        or receipt["child_result_sha256"] != _sha256(child_result_raw)
        or receipt["environment_digest"] != result["environment_digest"]
        or receipt["identity_digest"] != _sha_value(identity)
        or receipt["identity_digest"] != result["identity_digest"]
        or receipt["leaf_sha256"] != files["tools/uprime_official_transport_v2_smoke.py"]
        or receipt["leaf_sha256"] != result["leaf_sha256"]
        or receipt["worker_sha256"] != result["worker_sha256"]
        or receipt["timing_policy_digest"] != timing_policy_digest()
    ):
        raise ValueError("receipt does not bind the child result")
    return receipt


def _state_summary(value: object, *, status: str, goal_count: int, task_id: str) -> dict[str, object]:
    fields = {
        "state_id",
        "task_id",
        "status",
        "goal_count",
        "parent_state_id",
        "proof_prefix",
        "canonical_status",
    }
    state = _exact(value, fields, "state summary")
    _text(state["state_id"], "state id")
    if (
        state["task_id"] != task_id
        or state["status"] != status
        or state["goal_count"] != goal_count
        or state["canonical_status"] != "lean_kernel_rpc_in_memory_state"
        or type(state["proof_prefix"]) is not str
    ):
        raise TransportError("state summary invariant failed")
    return state


def _target_binding(value: object) -> dict[str, object]:
    fields = {
        "requested_target_mvar_id",
        "requested_target_selector",
        "effective_target_mvar_id",
        "effective_target_goal_index",
        "source",
    }
    binding = _exact(value, fields, "target binding")
    if (
        binding["requested_target_mvar_id"] is not None
        or binding["requested_target_selector"] != "first"
        or type(binding["effective_target_mvar_id"]) is not str
        or binding["effective_target_goal_index"] != 0
        or type(binding["source"]) is not str
    ):
        raise TransportError("target binding invariant failed")
    return binding


def _replay(value: object) -> dict[str, object]:
    fields = {
        "schema_version",
        "replay_status",
        "reexecution_performed",
        "verification_method",
        "semantic_response_match",
        "post_state_match",
        "delta_match",
        "target_match",
        "cap_match",
        "error",
        "primary_comparable",
        "replay_comparable",
    }
    replay = _exact(value, fields, "replay witness")
    comparable_fields = {
        "semantic_status",
        "post_kernel_state",
        "state_delta",
        "action_id",
        "target_binding",
        "budget",
        "normalized_failure_class",
    }
    primary = _exact(replay["primary_comparable"], comparable_fields, "primary comparable")
    second = _exact(replay["replay_comparable"], comparable_fields, "replay comparable")
    flags = (
        replay["reexecution_performed"],
        replay["semantic_response_match"],
        replay["post_state_match"],
        replay["delta_match"],
        replay["target_match"],
        replay["cap_match"],
    )
    if (
        replay["schema_version"] != REPLAY_SCHEMA
        or replay["replay_status"] != "verified"
        or any(flag is not True for flag in flags)
        or replay["error"] is not None
        or canonical_bytes(primary) != canonical_bytes(second)
        or primary["action_id"] != ACTION["action_id"]
        or primary["semantic_status"] != "closed"
    ):
        raise TransportError("replay witness is not verified")
    return replay


def _response(raw: bytes, request_id: str, payload_fields: set[str]) -> dict[str, object]:
    value = _parse_json_bytes(raw, where=f"response {request_id}", maximum=RESPONSE_MAX_BYTES, line=True)
    response = _exact(value, payload_fields | {"id", "ok", "rpc_protocol_version"}, "RPC response")
    if (
        response["id"] != request_id
        or response["ok"] is not True
        or response["rpc_protocol_version"] != RPC_PROTOCOL_VERSION
    ):
        raise TransportError("RPC envelope invariant failed")
    return response


def _request(value: dict[str, object]) -> bytes:
    return canonical_bytes(value) + b"\n"


def run_synthetic_rpc_sequence(
    transport: object,
    *,
    clock_ns: object = time.monotonic_ns,
    startup_start_ns: int | None = None,
) -> dict[str, object]:
    responses: list[str] = []
    requests: list[str] = []
    transcript: list[dict[str, str]] = []
    timing_frames: list[dict[str, object]] = []

    def exchange(value: dict[str, object], fields: set[str], clock_class: str) -> dict[str, object]:
        request_id = _text(value.get("id"), "request id")
        sequence = len(timing_frames) + 1
        if sequence > len(REQUEST_IDS) or request_id != REQUEST_IDS[sequence - 1] or clock_class != REQUEST_TIMING_CLASSES[sequence - 1]:
            raise TransportError("request/timing order changed", timing_frames=list(timing_frames))
        start = startup_start_ns if sequence == 1 and startup_start_ns is not None else clock_ns()
        policy = TIMING_POLICY[clock_class]
        deadline = checked_deadline_ns(start, int(policy["hard_wall_ns"]))
        request_raw = _request(value)
        try:
            raw = transport.round_trip(request_raw, deadline_ns=deadline, clock_ns=clock_ns)
            if type(raw) is not bytes:
                raise TransportError("transport returned non-bytes")
            response = _response(raw, request_id, fields)
            if request_id == REQUEST_IDS[-1]:
                transport.finish_clean_shutdown(deadline_ns=deadline, clock_ns=clock_ns)
        except BaseException as exc:
            end = clock_ns()
            frame = _timing_frame(
                sequence=sequence, request_id=request_id, clock_class=clock_class,
                start_ns=start, end_ns=end, completed=False, failed=True,
            )
            timing_frames.append(frame)
            if isinstance(exc, TransportError):
                exc.timing_frames = list(timing_frames)
                raise
            wrapped = TransportError(str(exc), timing_frames=list(timing_frames))
            raise wrapped from exc
        end = clock_ns()
        frame = _timing_frame(
            sequence=sequence, request_id=request_id, clock_class=clock_class,
            start_ns=start, end_ns=end, completed=True,
        )
        timing_frames.append(frame)
        request_digest = _sha256(request_raw[:-1])
        response_digest = _sha256(raw[:-1])
        requests.append(request_digest)
        responses.append(response_digest)
        transcript.append({"request_sha256": request_digest, "response_sha256": response_digest})
        if frame["classification"] == "RESOURCE_BLOCKED":
            raise TransportResourceError(
                "request exceeded its absolute hard wall",
                cap_name=f"{clock_class}_hard_wall_ns",
                cap_value=int(frame["hard_wall_ns"]), observed_value=int(frame["elapsed_ns"]),
                stage=request_id, timing_frames=list(timing_frames),
            )
        return response

    def semantic_failure(message: str, cause: BaseException | None = None) -> None:
        if not timing_frames:
            raise TransportError(message) from cause
        prior = timing_frames[-1]
        end = clock_ns()
        terminal = _timing_frame(
            sequence=int(prior["sequence"]), request_id=str(prior["request_id"]),
            clock_class=str(prior["clock_class"]), start_ns=int(prior["start_ns"]),
            end_ns=end, completed=False, failed=True,
        )
        timing_frames[-1] = terminal
        if terminal["classification"] == "RESOURCE_BLOCKED":
            raise TransportResourceError(
                message, cap_name=f"{terminal['clock_class']}_hard_wall_ns",
                cap_value=int(terminal["hard_wall_ns"]), observed_value=int(terminal["elapsed_ns"]),
                stage=str(terminal["request_id"]), timing_frames=list(timing_frames),
            ) from cause
        if terminal["classification"] == "QUALIFICATION_MARGIN_BLOCKED":
            raise TransportMarginError(message, timing_frames=list(timing_frames)) from cause
        raise TransportError(message, timing_frames=list(timing_frames)) from cause

    def semantic_call(function: object, *args: object, **kwargs: object) -> object:
        try:
            return function(*args, **kwargs)
        except BaseException as exc:
            semantic_failure("RPC semantic validation failed", exc)
        raise AssertionError("unreachable")

    def semantic_success() -> None:
        prior = timing_frames[-1]
        end = clock_ns()
        completed = _timing_frame(
            sequence=int(prior["sequence"]), request_id=str(prior["request_id"]),
            clock_class=str(prior["clock_class"]), start_ns=int(prior["start_ns"]),
            end_ns=end, completed=True,
        )
        timing_frames[-1] = completed
        if completed["classification"] == "RESOURCE_BLOCKED":
            raise TransportResourceError(
                "semantic validation exceeded its absolute hard wall",
                cap_name=f"{completed['clock_class']}_hard_wall_ns",
                cap_value=int(completed["hard_wall_ns"]), observed_value=int(completed["elapsed_ns"]),
                stage=str(completed["request_id"]), timing_frames=list(timing_frames),
            )
        if completed["classification"] == "QUALIFICATION_MARGIN_BLOCKED":
            raise TransportMarginError(
                "semantic validation exceeded its qualification margin",
                timing_frames=list(timing_frames),
            )

    load = exchange(
        {"id": REQUEST_IDS[0], "cmd": "load_project", "imports": ["Lean"]},
        {"backend", "loaded", "imports", "session_id", "n_states"}, "startup_load",
    )
    if load["backend"] != KERNEL_BACKEND or load["loaded"] is not True or load["imports"] != ["Lean"] or load["n_states"] != 0:
        semantic_failure("load_project invariant failed")
    semantic_success()

    initial = exchange(
        {"id": REQUEST_IDS[1], "cmd": "status"},
        {"backend", "loaded", "session_id", "n_states", "n_requests", "n_failures", "n_primary_executions", "n_replay_executions", "imports"}, "control",
    )
    if (
        initial["n_states"] != 0
        or initial["loaded"] is not True
        or initial["backend"] != KERNEL_BACKEND
        or initial["session_id"] != load["session_id"]
        or initial["imports"] != ["Lean"]
    ):
        semantic_failure("initial status invariant failed")
    semantic_success()

    init = exchange(
        {"id": REQUEST_IDS[2], "cmd": "init_state", "task": TASK},
        {"state", "kernel_state"}, "control_initialization",
    )
    source = semantic_call(_state_summary, init["state"], status="open", goal_count=1, task_id=TASK["task_id"])
    assert type(source) is dict
    source_id = semantic_call(_text, source["state_id"], "source state id")
    assert type(source_id) is str
    kernel = init["kernel_state"]
    if type(kernel) is not dict or kernel.get("state_id") != source_id or kernel.get("status") != "open" or kernel.get("closed") is not False:
        semantic_failure("initial kernel witness invariant failed")
    semantic_success()

    apply = exchange(
        {"id": REQUEST_IDS[3], "cmd": "apply_tactic", "state_id": source_id, "action": ACTION},
        {
            "u05_semantics_version", "status", "censor_reason", "before_state_id", "after_state_id",
            "after_state_retained", "target_mvar_id", "target_binding", "budget", "state_delta",
            "kernel_state_before", "kernel_state_after", "kernel_state", "state", "audit", "replay",
            "replay_certificate", "messages", "elapsed_ms", "heartbeats",
        }, "action",
    )
    if (
        apply["u05_semantics_version"] != U05_SEMANTICS_VERSION
        or apply["status"] != "success"
        or apply["censor_reason"] is not None
        or apply["before_state_id"] != source_id
        or apply["after_state_retained"] is not True
        or apply["heartbeats"] is not None
        or canonical_bytes(apply["kernel_state_after"]) != canonical_bytes(apply["kernel_state"])
    ):
        semantic_failure("closed transition invariant failed")
    semantic_call(_target_binding, apply["target_binding"])
    replay = semantic_call(_replay, apply["replay"])
    assert type(replay) is dict
    if canonical_bytes(replay) != canonical_bytes(apply["replay_certificate"]):
        semantic_failure("replay aliases differ")
    child = semantic_call(_state_summary, apply["state"], status="closed", goal_count=0, task_id=TASK["task_id"])
    assert type(child) is dict
    child_id = semantic_call(_text, child["state_id"], "child state id")
    assert type(child_id) is str
    after = apply["kernel_state_after"]
    if (
        type(after) is not dict
        or after.get("state_id") != child_id
        or after.get("status") != "closed"
        or after.get("closed") is not True
        or after.get("goals") != []
    ):
        semantic_failure("closed kernel witness invariant failed")
    semantic_success()

    discard_child = exchange(
        {"id": REQUEST_IDS[4], "cmd": "discard_state", "state_id": child_id},
        {"u05_semantics_version", "state_id", "discarded", "n_states_before", "n_states_after"}, "control",
    )
    if (
        discard_child["u05_semantics_version"] != U05_SEMANTICS_VERSION
        or discard_child["state_id"] != child_id
        or discard_child["discarded"] is not True
        or discard_child["n_states_before"] != 2
        or discard_child["n_states_after"] != 1
    ):
        semantic_failure("closed child was not discarded exactly once")
    semantic_success()

    discard_source = exchange(
        {"id": REQUEST_IDS[5], "cmd": "discard_state", "state_id": source_id},
        {"u05_semantics_version", "state_id", "discarded", "n_states_before", "n_states_after"}, "control",
    )
    if (
        discard_source["u05_semantics_version"] != U05_SEMANTICS_VERSION
        or discard_source["state_id"] != source_id
        or discard_source["discarded"] is not True
        or discard_source["n_states_before"] != 1
        or discard_source["n_states_after"] != 0
    ):
        semantic_failure("source was not discarded exactly once")
    semantic_success()

    final = exchange(
        {"id": REQUEST_IDS[6], "cmd": "status"},
        {"backend", "loaded", "session_id", "n_states", "n_requests", "n_failures", "n_primary_executions", "n_replay_executions", "imports"}, "control",
    )
    if (
        final["n_states"] != 0
        or final["backend"] != KERNEL_BACKEND
        or final["loaded"] is not True
        or final["session_id"] != load["session_id"]
        or final["imports"] != ["Lean"]
        or final["n_primary_executions"] != 1
        or final["n_replay_executions"] != 1
        or final["n_requests"] != 7
        or final["n_failures"] != 0
    ):
        semantic_failure("final worker status invariant failed")
    semantic_success()

    shutdown = exchange(
        {"id": REQUEST_IDS[7], "cmd": "shutdown"},
        {"shutdown"}, "shutdown",
    )
    if shutdown["shutdown"] is not True:
        semantic_failure("shutdown was not acknowledged")
    semantic_success()
    validate_timing_frames(timing_frames, completed_process=True)
    return {
        "request_digests": requests,
        "response_digests": responses,
        "transcript_digest": _sha_value(transcript),
        "timing_frames": timing_frames,
        "init_response_digest": responses[2],
        "transition_response_digest": responses[3],
        "shutdown_ack_digest": responses[7],
        "final_n_states": final["n_states"],
        "n_primary_executions": final["n_primary_executions"],
        "n_replay_executions": final["n_replay_executions"],
        "closed": True,
        "ownership_zero": True,
    }


class JsonlLeanTransport:
    def __init__(
        self, argv: tuple[str, ...], *, cwd: str, env: dict[str, str], response_limit: int,
        clock_ns: object = time.monotonic_ns,
    ):
        # This is deliberately the first effect in the constructor.  The same
        # absolute startup deadline therefore covers Popen, load write/read,
        # parsing, and semantic validation.
        self.startup_start_ns = clock_ns()
        self.startup_deadline_ns = checked_deadline_ns(
            self.startup_start_ns, int(TIMING_POLICY["startup_load"]["hard_wall_ns"])
        )
        self._response_limit = response_limit
        self._process = _bounded_blocking_call(
            lambda: subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                bufsize=0,
            ),
            deadline_ns=self.startup_deadline_ns,
            clock_ns=clock_ns,
            stage="lean_popen",
        )
        if self._process.stdin is None or self._process.stdout is None or self._process.stderr is None:
            raise TransportError("Lean pipes were not created")
        self._responses: queue.Queue[bytes | BaseException | None] = queue.Queue()
        self._stderr_total = 0
        self._stderr_overflow = False
        self._closed = False
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        try:
            while True:
                line = self._process.stdout.readline(self._response_limit + 1)
                if not line:
                    self._responses.put(None)
                    return
                if len(line) > self._response_limit:
                    self._responses.put(
                        TransportResourceError(
                            "RPC response exceeded cap",
                            cap_name="single_rpc_response_bytes",
                            cap_value=self._response_limit,
                            observed_value=len(line),
                            stage="rpc_read",
                        )
                    )
                    return
                self._responses.put(line)
        except BaseException as exc:
            self._responses.put(exc)

    def _read_stderr(self) -> None:
        try:
            while True:
                block = self._process.stderr.read(65_536)
                if not block:
                    return
                self._stderr_total += len(block)
                if self._stderr_total > STREAM_LIMIT_BYTES:
                    self._stderr_overflow = True
                    return
        except BaseException:
            self._stderr_overflow = True

    def round_trip(self, request: bytes, *, deadline_ns: int, clock_ns: object) -> bytes:
        if self._closed or type(request) is not bytes or not request.endswith(b"\n") or b"\n" in request[:-1] or b"\r" in request:
            raise TransportError("invalid JSONL request")
        def write_request() -> None:
            self._process.stdin.write(request)
            self._process.stdin.flush()

        try:
            _bounded_blocking_call(
                write_request, deadline_ns=deadline_ns, clock_ns=clock_ns,
                stage="rpc_write",
            )
        except TransportResourceError:
            raise
        except (OSError, ValueError) as exc:
            raise TransportError("Lean stdin failed") from exc
        try:
            response = self._responses.get(timeout=remaining_timeout_seconds(deadline_ns, clock_ns))
        except queue.Empty as exc:
            self.close()
            raise TransportResourceError(
                "RPC response timeout",
                cap_name="absolute_deadline_ns",
                cap_value=deadline_ns,
                observed_value=clock_ns(),
                stage="rpc_wait",
            ) from exc
        if isinstance(response, BaseException):
            self.close()
            raise response
        if response is None:
            raise TransportError("Lean stdout closed before response")
        if self._stderr_overflow:
            raise TransportResourceError(
                "Lean stderr exceeded cap",
                cap_name="stderr_bytes",
                cap_value=STREAM_LIMIT_BYTES,
                observed_value=self._stderr_total,
                stage="lean_stderr",
            )
        return response

    def finish_clean_shutdown(self, *, deadline_ns: int, clock_ns: object) -> None:
        try:
            _bounded_blocking_call(
                self._process.stdin.close, deadline_ns=deadline_ns,
                clock_ns=clock_ns, stage="shutdown_stdin_close",
            )
        except (OSError, ValueError):
            pass
        try:
            code = self._process.wait(timeout=remaining_timeout_seconds(deadline_ns, clock_ns))
        except subprocess.TimeoutExpired as exc:
            self.close()
            raise TransportResourceError(
                "Lean shutdown timeout",
                cap_name="shutdown_deadline_ns",
                cap_value=deadline_ns,
                observed_value=clock_ns(),
                stage="shutdown",
            ) from exc
        self._closed = True
        if code != 0:
            raise TransportError("Lean exited nonzero after shutdown")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Never reacquire the pipe lock here: a deadline-expired daemon may
        # still be blocked in write/flush/close.  Job containment owns final
        # orphan cleanup after the nonblocking terminate/kill requests.
        if self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass
        if self._process.poll() is None:
            try:
                self._process.kill()
            except OSError:
                pass


class RuntimeFence:
    def __init__(self, *, leaf_path: pathlib.Path, python_path: pathlib.Path, repo_root: pathlib.Path):
        self.leaf_path = os.path.normcase(str(leaf_path))
        self.python_path = os.path.normcase(str(python_path))
        self.repo_root = repo_root
        self.armed = False
        self.allowed_files = {self.leaf_path, self.python_path}
        self.run_temp: str | None = None
        self.expected_argv: tuple[str, ...] | None = None
        self._original_import = builtins.__import__

    def install(self) -> None:
        builtins.__import__ = self.import_guard
        sys.addaudithook(self.audit)

    def authorize_validation(
        self, *, lean: pathlib.Path, worker: pathlib.Path, run_temp: pathlib.Path
    ) -> None:
        """Permit only syntactically prequalified capabilities to be hashed."""

        self.allowed_files.update(
            {os.path.normcase(str(lean)), os.path.normcase(str(worker))}
        )
        self.run_temp = os.path.normcase(str(run_temp))

    def import_guard(self, name: str, globals: object = None, locals: object = None, fromlist: object = (), level: int = 0) -> object:
        if name == "lean_rgc" or name.startswith("lean_rgc."):
            raise ScopeViolation("repository package import is forbidden")
        if self.armed:
            raise ScopeViolation("imports are forbidden after ARM")
        return self._original_import(name, globals, locals, fromlist, level)

    def arm(self, *, lean: pathlib.Path, worker: pathlib.Path, run_temp: pathlib.Path, argv: tuple[str, ...]) -> None:
        self.authorize_validation(lean=lean, worker=worker, run_temp=run_temp)
        self.expected_argv = argv
        self.armed = True

    def _within_temp(self, path: str) -> bool:
        return self.run_temp is not None and (path == self.run_temp or path.startswith(self.run_temp + os.sep))

    def audit(self, event: str, args: tuple[object, ...]) -> None:
        if event == "subprocess.Popen":
            if not self.armed or self.expected_argv is None:
                raise ScopeViolation("subprocess before ARM")
            executable = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
            argv = tuple(args[1]) if isinstance(args[1], (tuple, list)) else ()
            if executable != os.path.normcase(self.expected_argv[0]) or argv != self.expected_argv:
                raise ScopeViolation("unapproved subprocess")
            return
        if event in {"os.listdir", "os.scandir", "os.chdir"}:
            raise ScopeViolation("directory enumeration/change is forbidden")
        if event == "open" and args:
            raw = args[0]
            if isinstance(raw, int):
                return
            try:
                path = os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(raw))))
            except (TypeError, ValueError):
                return
            if path in self.allowed_files or self._within_temp(path):
                return
            raise ScopeViolation("unapproved Python file access")


def _path(value: object, where: str) -> pathlib.Path:
    text = _text(value, where)
    path = pathlib.Path(text)
    if not path.is_absolute():
        raise ValueError(f"{where} must be absolute")
    resolved = path.resolve(strict=True)
    item = resolved.stat()
    if hasattr(item, "st_file_attributes") and item.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"{where} is a reparse point")
    return resolved


def validate_arm(
    value: object,
    *,
    nonce: str,
    leaf_path: pathlib.Path,
    leaf_sha256: str,
    python_sha256: str,
) -> tuple[dict[str, object], dict[str, object]]:
    arm = _exact(value, ARM_FIELDS, "ARM")
    if arm["schema_version"] != ARM_SCHEMA or arm["nonce"] != nonce:
        raise ValueError("ARM identity changed")
    _validate_role(arm["fixture_role"], arm["process_ordinal"])
    fixed_caps = {
        "response_limit_bytes": RESPONSE_MAX_BYTES,
        "stream_limit_bytes": STREAM_LIMIT_BYTES,
        "artifact_limit_bytes": ARTIFACT_MAX_BYTES,
        "receipt_limit_bytes": RECEIPT_MAX_BYTES,
        "request_count": 8,
        "task_count": 1,
        "action_count": 1,
        "max_open_states": 2,
    }
    if any(arm[name] != expected for name, expected in fixed_caps.items()):
        raise ValueError("ARM cap changed")
    if arm["timing_policy"] != TIMING_POLICY or arm["timing_policy_digest"] != timing_policy_digest():
        raise ValueError("ARM timing policy changed")
    _hex(arm["environment_digest"], "ARM environment digest", 64, uppercase=True)
    identity = validate_identity(arm["identity"])
    if python_sha256 != FIXED_PYTHON_SHA256 or identity["python_sha256"] != python_sha256:
        raise ValueError("executed Python identity changed")
    repo = _path(arm["repo_root"], "repo root")
    if repo != leaf_path.parents[1] or leaf_path != repo / "tools/uprime_official_transport_v2_smoke.py":
        raise ValueError("leaf/repository location changed")
    lean = _path(arm["lean_executable"], "Lean executable")
    worker = _path(arm["worker_path"], "worker")
    if worker != repo / "lean_rgc/native_lean/RGCKernelRPC.lean":
        raise ValueError("worker location changed")
    run_temp = _path(arm["run_temp"], "run temp")
    if not run_temp.is_dir():
        raise ValueError("run temp is not a directory")
    stage = pathlib.Path(_text(arm["child_result_path"], "child result path"))
    receipt = pathlib.Path(_text(arm["child_receipt_path"], "child receipt path"))
    if (
        not stage.is_absolute()
        or not receipt.is_absolute()
        or stage.parent.resolve() != run_temp
        or receipt.parent.resolve() != run_temp
        or stage.name != f"uprime_transport_v2_child_result.{nonce}.json"
        or receipt.name != f"uprime_transport_v2_child_receipt.{nonce}.json"
        or stage.exists()
        or receipt.exists()
    ):
        raise ValueError("stage/receipt capability changed")
    if (
        arm["lean_sha256"] != FIXED_LEAN_SHA256
        or arm["worker_blob"] != FIXED_WORKER_BLOB
        or arm["worker_sha256"] != FIXED_WORKER_SHA256
        or _sha_file(lean) != FIXED_LEAN_SHA256
        or _sha_file(worker) != FIXED_WORKER_SHA256
        or _git_blob_oid(worker) != FIXED_WORKER_BLOB
    ):
        raise ValueError("Lean/worker byte identity changed")
    files = identity["i1_file_sha256"]
    assert type(files) is dict
    if files["tools/uprime_official_transport_v2_smoke.py"] != leaf_sha256:
        raise ValueError("leaf differs from accepted I1 identity")
    return arm, identity


def _write_exclusive(path: pathlib.Path, raw: bytes, *, maximum: int) -> None:
    if not raw or len(raw) > maximum:
        raise ArtifactError("output is empty or over cap")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _child_result(
    *, arm: dict[str, object], identity: dict[str, object], leaf_sha256: str,
    disposition: str, timing_frames: list[dict[str, object]],
    payload: dict[str, object] | None = None, transcript: dict[str, object] | None = None,
    resource_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    failure_code: str | None
    if disposition == "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED":
        failure_code = None
    elif disposition == "SYNTHETIC_RESOURCE_BLOCKED":
        failure_code = "RESOURCE_BLOCKED"
    else:
        failure_code = ORDINARY_FAILURES[disposition]
    result = {
        "schema_version": CHILD_RESULT_SCHEMA,
        "nonce": arm["nonce"],
        "fixture_role": arm["fixture_role"],
        "process_ordinal": arm["process_ordinal"],
        "run_state": "CHILD_RESULT_COMMITTED",
        "scientific_disposition": disposition,
        "failure_code": failure_code,
        "identity_digest": _sha_value(identity),
        "environment_digest": arm["environment_digest"],
        "leaf_sha256": leaf_sha256,
        "worker_blob": FIXED_WORKER_BLOB,
        "worker_sha256": FIXED_WORKER_SHA256,
        "timing_policy": TIMING_POLICY,
        "timing_policy_digest": timing_policy_digest(),
        "timing_frames": timing_frames,
        "transcript": transcript,
        "payload": payload,
        "resource_evidence": resource_evidence,
    }
    parse_child_result(canonical_bytes(result))
    return result


def _write_child_result_receipt(
    arm: dict[str, object], identity: dict[str, object], result: dict[str, object], leaf_sha256: str
) -> None:
    result_raw = canonical_bytes(result)
    parse_child_result(result_raw)
    stage = pathlib.Path(str(arm["child_result_path"]))
    receipt_path = pathlib.Path(str(arm["child_receipt_path"]))
    _write_exclusive(stage, result_raw, maximum=ARTIFACT_MAX_BYTES)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_kind": "CHILD_RESULT",
        "nonce": arm["nonce"],
        "fixture_role": arm["fixture_role"],
        "process_ordinal": arm["process_ordinal"],
        "child_result_length": len(result_raw),
        "child_result_sha256": _sha256(result_raw),
        "environment_digest": arm["environment_digest"],
        "identity_digest": _sha_value(identity),
        "leaf_sha256": leaf_sha256,
        "worker_sha256": FIXED_WORKER_SHA256,
        "timing_policy_digest": timing_policy_digest(),
    }
    receipt_raw = canonical_bytes(receipt)
    validate_receipt(receipt_raw, result_raw, identity)
    _write_exclusive(receipt_path, receipt_raw, maximum=RECEIPT_MAX_BYTES)


def _worker_environment(run_temp: pathlib.Path, lean: pathlib.Path) -> dict[str, str]:
    system_root = os.environ.get("SYSTEMROOT") or os.environ.get("SystemRoot")
    comspec = os.environ.get("COMSPEC") or os.environ.get("ComSpec")
    if not system_root or not comspec:
        raise ScopeViolation("minimal Windows environment is incomplete")
    return {
        "COMSPEC": comspec,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": str(lean.parent) + ";" + str(pathlib.Path(system_root) / "System32"),
        "SYSTEMROOT": system_root,
        "TEMP": str(run_temp),
        "TMP": str(run_temp),
        "WINDIR": system_root,
    }


def _flags_digest() -> str:
    return _sha_value(
        {
            "isolated": sys.flags.isolated,
            "no_site": sys.flags.no_site,
            "ignore_environment": sys.flags.ignore_environment,
            "safe_path": sys.flags.safe_path,
            "dont_write_bytecode": sys.flags.dont_write_bytecode,
        }
    )


def _official_child(probe_line: bytes) -> int:
    nonce, job_receipt = parse_probe_line(probe_line)
    if (
        sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.safe_path is not True
        or sys.flags.dont_write_bytecode != 1
        or __package__ not in {None, ""}
    ):
        raise ScopeViolation("frozen Python flags changed")
    loaded = sorted(name for name in sys.modules if name == "lean_rgc" or name.startswith("lean_rgc."))
    if loaded:
        raise ScopeViolation("repository package was loaded")
    leaf_path = pathlib.Path(__file__).resolve(strict=True)
    repo_root = leaf_path.parents[1]
    python_path = pathlib.Path(sys.executable).resolve(strict=True)
    leaf_sha256 = _sha_file(leaf_path)
    python_sha256 = _sha_file(python_path)
    flags_digest = _flags_digest()
    sys_path_digest = _sha_value(list(sys.path))
    fence = RuntimeFence(leaf_path=leaf_path, python_path=python_path, repo_root=repo_root)
    fence.install()
    ready = {
        "schema_version": READY_SCHEMA,
        "nonce": nonce,
        "pid": os.getpid(),
        "job_assignment_receipt_digest": job_receipt,
        "leaf_sha256": leaf_sha256,
        "python_flags_digest": flags_digest,
        "sys_path_digest": sys_path_digest,
        "import_fence_passed": True,
        "loaded_lean_rgc_modules": [],
    }
    _exact(ready, READY_FIELDS, "READY")
    sys.stdout.buffer.write(canonical_bytes(ready) + b"\n")
    sys.stdout.buffer.flush()
    arm_raw = sys.stdin.buffer.readline(ARM_MAX_BYTES + 1)
    arm_value = _parse_json_bytes(arm_raw, where="ARM", maximum=ARM_MAX_BYTES, line=True)
    arm_shape = _exact(arm_value, ARM_FIELDS, "ARM")
    raw_repo = pathlib.Path(_text(arm_shape["repo_root"], "repo root"))
    raw_worker = pathlib.Path(_text(arm_shape["worker_path"], "worker"))
    raw_lean = pathlib.Path(_text(arm_shape["lean_executable"], "Lean executable"))
    raw_temp = pathlib.Path(_text(arm_shape["run_temp"], "run temp"))
    path_head = os.environ.get("PATH", "").split(";", 1)[0]
    expected_lean = pathlib.Path(path_head) / "lean.exe"
    expected_temp = pathlib.Path(os.environ.get("TEMP", ""))
    if (
        not raw_repo.is_absolute()
        or os.path.normcase(os.path.abspath(raw_repo))
        != os.path.normcase(str(repo_root))
        or not raw_worker.is_absolute()
        or os.path.normcase(os.path.abspath(raw_worker))
        != os.path.normcase(str(repo_root / "lean_rgc/native_lean/RGCKernelRPC.lean"))
        or not raw_lean.is_absolute()
        or os.path.normcase(os.path.abspath(raw_lean))
        != os.path.normcase(os.path.abspath(expected_lean))
        or not raw_temp.is_absolute()
        or os.path.normcase(os.path.abspath(raw_temp))
        != os.path.normcase(os.path.abspath(expected_temp))
    ):
        raise ScopeViolation("ARM path capability escaped the minimal child environment")
    fence.authorize_validation(lean=raw_lean, worker=raw_worker, run_temp=raw_temp)
    arm, identity = validate_arm(
        arm_value,
        nonce=nonce,
        leaf_path=leaf_path,
        leaf_sha256=leaf_sha256,
        python_sha256=python_sha256,
    )
    lean = pathlib.Path(str(arm["lean_executable"])).resolve(strict=True)
    worker = pathlib.Path(str(arm["worker_path"])).resolve(strict=True)
    run_temp = pathlib.Path(str(arm["run_temp"])).resolve(strict=True)
    argv = (str(lean), "--run", str(worker), "--imports", "Lean")
    fence.arm(lean=lean, worker=worker, run_temp=run_temp, argv=argv)
    transport: JsonlLeanTransport | None = None
    disposition = "SYNTHETIC_EXECUTION_FAILED"
    exit_code = EXIT_BY_DISPOSITION[disposition]
    timing_frames: list[dict[str, object]] = []
    worker_env = _worker_environment(run_temp, lean)
    startup_start_ns = time.monotonic_ns()
    startup_began = True

    def ensure_startup_terminal() -> list[dict[str, object]]:
        if timing_frames or not startup_began:
            return timing_frames
        return [_timing_frame(
            sequence=1, request_id=REQUEST_IDS[0], clock_class="startup_load",
            start_ns=startup_start_ns, end_ns=time.monotonic_ns(), completed=False, failed=True,
        )]

    try:
        transport = JsonlLeanTransport(
            argv,
            cwd=str(repo_root),
            env=worker_env,
            response_limit=RESPONSE_MAX_BYTES,
            clock_ns=time.monotonic_ns,
        )
        evidence = run_synthetic_rpc_sequence(
            transport, clock_ns=time.monotonic_ns, startup_start_ns=transport.startup_start_ns
        )
        timing_frames = list(evidence["timing_frames"])
        loaded_after = sorted(name for name in sys.modules if name == "lean_rgc" or name.startswith("lean_rgc."))
        if loaded_after:
            raise ScopeViolation("repository package was loaded after READY")
        payload = {
            "closed": evidence["closed"],
            "final_n_states": evidence["final_n_states"],
            "init_response_digest": evidence["init_response_digest"],
            "n_primary_executions": evidence["n_primary_executions"],
            "n_replay_executions": evidence["n_replay_executions"],
            "natural_lean_exit_code": 0,
            "ownership_zero": evidence["ownership_zero"],
            "request_count": 8,
            "rpc_protocol_version": RPC_PROTOCOL_VERSION,
            "shutdown_ack_digest": evidence["shutdown_ack_digest"],
            "transition_response_digest": evidence["transition_response_digest"],
        }
        transcript = {
            "schema_version": TRANSCRIPT_SCHEMA,
            "request_ids": list(REQUEST_IDS),
            "ordered_request_digests": evidence["request_digests"],
            "ordered_response_digests": evidence["response_digests"],
            "ordered_transcript_digest": evidence["transcript_digest"],
        }
        disposition = "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED"
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition,
            timing_frames=timing_frames, payload=payload, transcript=transcript,
        )
        exit_code = 0
    except TransportResourceError as exc:
        disposition = "SYNTHETIC_RESOURCE_BLOCKED"
        timing_frames = list(exc.timing_frames)
        timing_frames = ensure_startup_terminal()
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition,
            timing_frames=timing_frames,
            resource_evidence=exc.evidence,
        )
        exit_code = EXIT_BY_DISPOSITION[disposition]
    except TransportMarginError as exc:
        disposition = "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED"
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition, timing_frames=list(exc.timing_frames),
        )
        exit_code = EXIT_BY_DISPOSITION[disposition]
    except ScopeViolation:
        disposition = "SYNTHETIC_SCOPE_VIOLATION"
        timing_frames = ensure_startup_terminal()
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition, timing_frames=timing_frames,
        )
        exit_code = EXIT_BY_DISPOSITION[disposition]
    except (TransportError, ValueError) as exc:
        disposition = "SYNTHETIC_RPC_BLOCKED"
        timing_frames = list(getattr(exc, "timing_frames", timing_frames))
        timing_frames = ensure_startup_terminal()
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition, timing_frames=timing_frames,
        )
        exit_code = EXIT_BY_DISPOSITION[disposition]
    except BaseException:
        disposition = "SYNTHETIC_EXECUTION_FAILED"
        timing_frames = ensure_startup_terminal()
        result = _child_result(
            arm=arm, identity=identity, leaf_sha256=leaf_sha256,
            disposition=disposition, timing_frames=timing_frames,
        )
        exit_code = EXIT_BY_DISPOSITION[disposition]
    finally:
        if transport is not None:
            transport.close()
    try:
        _write_child_result_receipt(arm, identity, result, leaf_sha256)
    except BaseException:
        return EXIT_BY_DISPOSITION["SYNTHETIC_ARTIFACT_BLOCKED"]
    return exit_code


__all__ = [
    "ACTION",
    "ARM_FIELDS",
    "ARM_SCHEMA",
    "ARTIFACT_SCHEMA",
    "CHILD_RESULT_FIELDS",
    "CHILD_RESULT_SCHEMA",
    "EXIT_BY_DISPOSITION",
    "FIXED_WORKER_BLOB",
    "FIXED_WORKER_SHA256",
    "IDENTITY_FIELDS",
    "ORDINARY_FAILURES",
    "I1_FILE_PATHS",
    "PROBE_SCHEMA",
    "READY_FIELDS",
    "READY_SCHEMA",
    "RECEIPT_FIELDS",
    "RECEIPT_SCHEMA",
    "REQUEST_TIMING_CLASSES",
    "REQUEST_IDS",
    "RESOURCE_EVIDENCE_FIELDS",
    "SUCCESS_PAYLOAD_FIELDS",
    "TASK",
    "TIMING_FIELDS",
    "TIMING_POLICY",
    "TIMING_SCHEMA",
    "TRANSCRIPT_FIELDS",
    "TRANSCRIPT_SCHEMA",
    "ArtifactError",
    "JsonlLeanTransport",
    "RuntimeFence",
    "ScopeViolation",
    "TransportError",
    "TransportMarginError",
    "TransportResourceError",
    "canonical_bytes",
    "checked_deadline_ns",
    "classify_elapsed_ns",
    "parse_child_result",
    "parse_probe_line",
    "remaining_timeout_seconds",
    "run_synthetic_rpc_sequence",
    "timing_policy_digest",
    "validate_arm",
    "validate_identity",
    "validate_receipt",
    "validate_timing_frames",
    "validate_transcript",
]


if __name__ == "__main__":
    assert _INITIAL_PROBE_LINE is not None
    try:
        raise SystemExit(_official_child(_INITIAL_PROBE_LINE))
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        sys.stderr.write("uprime-official-transport: child failed before a receipted result\n")
        raise SystemExit(70)
