from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

import pytest

from tools import uprime_official_transport_v2_smoke as smoke


ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / "tools" / "uprime_official_transport_v2_smoke.py"
PARENT = ROOT / "tools" / "run_uprime_official_transport_v2_smoke.ps1"
UNIT_RUNNER = ROOT / "tools" / "run_uprime_official_transport_v2_tests.ps1"


@pytest.fixture(autouse=True)
def _no_process_can_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """The precommit suite is structurally fake-only; even Popen is poisoned."""

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("precommit fake/fault tests may not start any process")

    monkeypatch.setattr(smoke.subprocess, "Popen", forbidden)


def _hex(char: str = "A", length: int = 64) -> str:
    return char * length


def _leaf_sha256() -> str:
    return hashlib.sha256(LEAF.read_bytes()).hexdigest().upper()


def _identity() -> dict[str, object]:
    files = {path: _hex(chr(65 + index)) for index, path in enumerate(sorted(smoke.I1_FILE_PATHS))}
    files["tools/uprime_official_transport_v2_smoke.py"] = _leaf_sha256()
    return {
        "accepted_commit": "a" * 40,
        "accepted_tree": "b" * 40,
        "accepted_run_id": "101",
        "accepted_job_id": "102",
        "candidate_run_id": "103",
        "candidate_job_id": "104",
        "attestation_scope": smoke.EXTERNAL_ATTESTATION_SCOPE,
        "i1_file_sha256": files,
        "powershell_version": smoke.FIXED_POWERSHELL_VERSION,
        "powershell_sha256": smoke.FIXED_POWERSHELL_SHA256,
        "python_version": smoke.FIXED_PYTHON_VERSION,
        "python_sha256": smoke.FIXED_PYTHON_SHA256,
        "lean_version": smoke.FIXED_LEAN_VERSION,
        "lean_commit": smoke.FIXED_LEAN_COMMIT,
        "lean_sha256": smoke.FIXED_LEAN_SHA256,
        "worker_blob": smoke.FIXED_WORKER_BLOB,
        "worker_sha256": smoke.FIXED_WORKER_SHA256,
    }


def _envelope(request_id: str, **payload: object) -> bytes:
    return smoke.canonical_bytes(
        {"id": request_id, "ok": True, "rpc_protocol_version": smoke.RPC_PROTOCOL_VERSION, **payload}
    ) + b"\n"


def _summary(state_id: str, *, status: str, goals: int, parent: str | None) -> dict[str, object]:
    return {
        "state_id": state_id,
        "task_id": smoke.TASK["task_id"],
        "status": status,
        "goal_count": goals,
        "parent_state_id": parent,
        "proof_prefix": smoke.TASK["prefix"],
        "canonical_status": "lean_kernel_rpc_in_memory_state",
    }


def _target() -> dict[str, object]:
    return {
        "requested_target_mvar_id": None,
        "requested_target_selector": "first",
        "effective_target_mvar_id": "mvar-0",
        "effective_target_goal_index": 0,
        "source": "selector:first",
    }


def _replay() -> dict[str, object]:
    comparable = {
        "semantic_status": "closed",
        "post_kernel_state": {"status": "closed"},
        "state_delta": {"closed_goals": ["mvar-0"]},
        "action_id": smoke.ACTION["action_id"],
        "target_binding": _target(),
        "budget": {"max": 20_000},
        "normalized_failure_class": None,
    }
    return {
        "schema_version": smoke.REPLAY_SCHEMA,
        "replay_status": "verified",
        "reexecution_performed": True,
        "verification_method": "independent_reexecution",
        "semantic_response_match": True,
        "post_state_match": True,
        "delta_match": True,
        "target_match": True,
        "cap_match": True,
        "error": None,
        "primary_comparable": comparable,
        "replay_comparable": dict(comparable),
    }


def _fake_responses() -> list[bytes]:
    source = "krpc_state_0"
    child = "krpc_state_1"
    session = "lean_kernel_rpc_test"
    before = {"state_id": source, "status": "open", "closed": False, "goals": [{"mvar_id": "mvar-0"}]}
    after = {"state_id": child, "status": "closed", "closed": True, "goals": []}
    replay = _replay()
    return [
        _envelope(smoke.REQUEST_IDS[0], backend=smoke.KERNEL_BACKEND, loaded=True, imports=["Lean"], session_id=session, n_states=0),
        _envelope(smoke.REQUEST_IDS[1], backend=smoke.KERNEL_BACKEND, loaded=True, session_id=session, n_states=0, n_requests=2, n_failures=0, n_primary_executions=0, n_replay_executions=0, imports=["Lean"]),
        _envelope(smoke.REQUEST_IDS[2], state=_summary(source, status="open", goals=1, parent=None), kernel_state=before),
        _envelope(
            smoke.REQUEST_IDS[3], u05_semantics_version=smoke.U05_SEMANTICS_VERSION,
            status="success", censor_reason=None, before_state_id=source, after_state_id=child,
            after_state_retained=True, target_mvar_id="mvar-0", target_binding=_target(),
            budget={"max": 20_000}, state_delta={"closed_goals": ["mvar-0"]},
            kernel_state_before=before, kernel_state_after=after, kernel_state=after,
            state=_summary(child, status="closed", goals=0, parent=source), audit={},
            replay=replay, replay_certificate=replay, messages=[], elapsed_ms=1, heartbeats=None,
        ),
        _envelope(smoke.REQUEST_IDS[4], u05_semantics_version=smoke.U05_SEMANTICS_VERSION, state_id=child, discarded=True, n_states_before=2, n_states_after=1),
        _envelope(smoke.REQUEST_IDS[5], u05_semantics_version=smoke.U05_SEMANTICS_VERSION, state_id=source, discarded=True, n_states_before=1, n_states_after=0),
        _envelope(smoke.REQUEST_IDS[6], backend=smoke.KERNEL_BACKEND, loaded=True, session_id=session, n_states=0, n_requests=7, n_failures=0, n_primary_executions=1, n_replay_executions=1, imports=["Lean"]),
        _envelope(smoke.REQUEST_IDS[7], shutdown=True),
    ]


class FakeClock:
    def __init__(self, elapsed: list[int], start: int = 1_000_000):
        values: list[int] = []
        cursor = start
        values.append(cursor)  # constructor/startup capture when requested directly
        for duration in elapsed:
            values.append(cursor + duration)
            cursor += duration + 1
            values.append(cursor)
        self._values = iter(values)

    def __call__(self) -> int:
        return next(self._values)


def _sequence_clock(elapsed: list[int], start: int = 1_000_000) -> tuple[object, int]:
    # Each successful interval clocks after bounded I/O and again after strict
    # semantic validation; later intervals additionally clock their own start.
    values: list[int] = []
    cursor = start
    for index, duration in enumerate(elapsed):
        if index:
            values.append(cursor)
        values.extend((cursor + duration // 2, cursor + duration))
        cursor += duration + 1
    iterator = iter(values)
    return (lambda: next(iterator)), start


class FakeTransport:
    def __init__(self, responses: list[bytes] | None = None, *, fail_at: int | None = None):
        self.responses = list(_fake_responses() if responses is None else responses)
        self.requests: list[dict[str, object]] = []
        self.deadlines: list[int] = []
        self.fail_at = fail_at
        self.finished = False

    def round_trip(self, request: bytes, *, deadline_ns: int, clock_ns: object) -> bytes:
        del clock_ns
        value = json.loads(request[:-1].decode("utf-8"))
        self.requests.append(value)
        self.deadlines.append(deadline_ns)
        if self.fail_at == len(self.requests) - 1:
            raise smoke.TransportError("injected transport fault")
        return self.responses.pop(0)

    def finish_clean_shutdown(self, *, deadline_ns: int, clock_ns: object) -> None:
        del deadline_ns, clock_ns
        self.finished = True


def _run(elapsed: list[int] | None = None, transport: FakeTransport | None = None) -> tuple[dict[str, object], FakeTransport]:
    durations = [1] * 8 if elapsed is None else elapsed
    clock, start = _sequence_clock(durations)
    fake = FakeTransport() if transport is None else transport
    return smoke.run_synthetic_rpc_sequence(fake, clock_ns=clock, startup_start_ns=start), fake


def _success_child_result(evidence: dict[str, object], identity: dict[str, object]) -> dict[str, object]:
    request_digests = evidence["request_digests"]
    response_digests = evidence["response_digests"]
    assert isinstance(request_digests, list) and isinstance(response_digests, list)
    return {
        "schema_version": smoke.CHILD_RESULT_SCHEMA,
        "nonce": "c" * 32,
        "fixture_role": "ARCHIVAL",
        "process_ordinal": 6,
        "run_state": "CHILD_RESULT_COMMITTED",
        "scientific_disposition": "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED",
        "failure_code": None,
        "identity_digest": hashlib.sha256(smoke.canonical_bytes(identity)).hexdigest().upper(),
        "environment_digest": _hex("E"),
        "leaf_sha256": _leaf_sha256(),
        "worker_blob": smoke.FIXED_WORKER_BLOB,
        "worker_sha256": smoke.FIXED_WORKER_SHA256,
        "timing_policy": smoke.TIMING_POLICY,
        "timing_policy_digest": smoke.timing_policy_digest(),
        "timing_frames": evidence["timing_frames"],
        "transcript": {
            "schema_version": smoke.TRANSCRIPT_SCHEMA,
            "request_ids": list(smoke.REQUEST_IDS),
            "ordered_request_digests": request_digests,
            "ordered_response_digests": response_digests,
            "ordered_transcript_digest": evidence["transcript_digest"],
        },
        "payload": {
            "closed": True,
            "final_n_states": 0,
            "init_response_digest": evidence["init_response_digest"],
            "n_primary_executions": 1,
            "n_replay_executions": 1,
            "natural_lean_exit_code": 0,
            "ownership_zero": True,
            "request_count": 8,
            "rpc_protocol_version": smoke.RPC_PROTOCOL_VERSION,
            "shutdown_ack_digest": evidence["shutdown_ack_digest"],
            "transition_response_digest": evidence["transition_response_digest"],
        },
        "resource_evidence": None,
    }


def test_leaf_import_surface_preprobe_gate_and_no_live_lane_are_static() -> None:
    source = LEAF.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imports.append((node.module or "").split(".", 1)[0])
    assert set(imports) == {"sys", "builtins", "hashlib", "json", "os", "pathlib", "queue", "stat", "subprocess", "threading", "time"}
    assert not ({"lean_rgc", "importlib", "runpy", "site", "numpy"} & set(imports))
    top_imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    first_gate = next(index for index, node in enumerate(tree.body) if isinstance(node, ast.If))
    assert tree.body.index(top_imports[2]) > first_gate
    for forbidden in ("sys.path.insert", "sys.path.append", "shell=True", "run_real_worker_fixture_for_test", "UPRIME_Q1_RUN_LIVE_WORKER", "PROBE_V1", "run_uprime_official_transport_tests.ps1"):
        assert forbidden not in source
    assert source.count("subprocess.Popen(") == 1
    constructor = source.index("self.startup_start_ns = clock_ns()")
    assert constructor < source.index("subprocess.Popen(", constructor)


def test_all_protocol_schemas_are_v2_and_probe_is_exact_bounded_ascii() -> None:
    schemas = (
        smoke.PROBE_SCHEMA, smoke.READY_SCHEMA, smoke.ARM_SCHEMA, smoke.ARTIFACT_SCHEMA,
        smoke.CHILD_RESULT_SCHEMA, smoke.RECEIPT_SCHEMA, smoke.TIMING_SCHEMA, smoke.TRANSCRIPT_SCHEMA,
    )
    assert all(value.endswith("-v2.0") for value in schemas)
    nonce = "a" * 32
    receipt = _hex("B")
    line = f"{smoke.PROBE_SCHEMA}|{nonce}|{receipt}\n".encode("ascii")
    assert smoke.parse_probe_line(line) == (nonce, receipt)
    for bad in (
        line.replace(b"-v2.0", b"-v1.0"), line[:-1],
        f"{smoke.PROBE_SCHEMA}|short|{receipt}\n".encode("ascii"),
        f"{smoke.PROBE_SCHEMA}|{nonce}|{'b' * 64}\n".encode("ascii"),
    ):
        with pytest.raises(ValueError):
            smoke.parse_probe_line(bad)


def test_exact_fixture_sequence_and_timing_policy_are_frozen() -> None:
    assert smoke.TASK == {"task_id": "synthetic_isolated_identity_v1", "imports": ["Lean"], "statement": "∀ (p : Prop), p → p", "prefix": "intro p\nintro h", "max_heartbeats": 20_000}
    assert smoke.ACTION == {"action_id": "synthetic_exact_h", "tactic": "exact h", "target_selector": "first", "max_heartbeats": 20_000}
    assert smoke.REQUEST_TIMING_CLASSES == ("startup_load", "control", "control_initialization", "action", "control", "control", "control", "shutdown")
    expected = {"startup_load": (120, 40), "control": (30, 10), "control_initialization": (30, 10), "action": (15, 5), "shutdown": (10, 3)}
    for name, (hard, margin) in expected.items():
        assert smoke.TIMING_POLICY[name] == {"authority": "child_monotonic_ns", "hard_wall_ns": hard * 1_000_000_000, "success_margin_ns": margin * 1_000_000_000}
    assert smoke.TIMING_POLICY["python_ready"]["hard_wall_seconds"] == 15
    assert smoke.TIMING_POLICY["fixture_execution"]["success_margin_seconds"] == 100
    assert smoke.TIMING_POLICY["batch_execution"]["hard_wall_seconds"] == 1_200
    assert smoke.TIMING_POLICY["artifact_publication"]["success_margin_seconds"] == 10


@pytest.mark.parametrize("clock_class", ["startup_load", "control", "control_initialization", "action", "shutdown"])
def test_integer_boundary_equality_plus_one_and_hard_wall(clock_class: str) -> None:
    policy = smoke.TIMING_POLICY[clock_class]
    hard = int(policy["hard_wall_ns"])
    margin = int(policy["success_margin_ns"])
    assert smoke.classify_elapsed_ns(margin, hard_wall_ns=hard, success_margin_ns=margin) == "PASS"
    assert smoke.classify_elapsed_ns(margin + 1, hard_wall_ns=hard, success_margin_ns=margin) == "QUALIFICATION_MARGIN_BLOCKED"
    assert smoke.classify_elapsed_ns(hard, hard_wall_ns=hard, success_margin_ns=margin) == "QUALIFICATION_MARGIN_BLOCKED"
    assert smoke.classify_elapsed_ns(hard + 1, hard_wall_ns=hard, success_margin_ns=margin) == "RESOURCE_BLOCKED"


def test_deadline_negative_decreasing_overflow_and_exhaustion_fail_closed() -> None:
    assert smoke.checked_deadline_ns(10, 20) == 30
    for start, wall in ((-1, 1), (0, 0), (smoke.MAX_NS, 1)):
        with pytest.raises(smoke.TransportResourceError):
            smoke.checked_deadline_ns(start, wall)
    with pytest.raises(smoke.TransportResourceError):
        smoke.remaining_timeout_seconds(10, lambda: 10)
    with pytest.raises(ValueError, match="decreasing"):
        smoke.validate_timing_frames([{
            "schema_version": smoke.TIMING_SCHEMA, "sequence": 1, "request_id": smoke.REQUEST_IDS[0],
            "clock_class": "startup_load", "start_ns": 2, "end_ns": 1, "elapsed_ns": 0,
            "hard_wall_ns": 120_000_000_000, "success_margin_ns": 40_000_000_000,
            "classification": "PASS", "completed": True,
        }], completed_process=False)


def test_fake_rpc_sequence_is_exact_closed_eight_frame_transcript() -> None:
    evidence, transport = _run()
    assert [row["cmd"] for row in transport.requests] == ["load_project", "status", "init_state", "apply_tactic", "discard_state", "discard_state", "status", "shutdown"]
    assert transport.requests[4]["state_id"] == "krpc_state_1"
    assert transport.requests[5]["state_id"] == "krpc_state_0"
    assert evidence["final_n_states"] == 0 and evidence["ownership_zero"] is True
    assert transport.finished is True
    frames = smoke.validate_timing_frames(evidence["timing_frames"], completed_process=True)
    assert [frame["clock_class"] for frame in frames] == list(smoke.REQUEST_TIMING_CLASSES)
    assert all(frame["classification"] == "PASS" for frame in frames)
    assert len(evidence["request_digests"]) == len(evidence["response_digests"]) == 8


def test_startup_and_shutdown_margin_and_resource_boundaries_are_enforced() -> None:
    startup_margin = int(smoke.TIMING_POLICY["startup_load"]["success_margin_ns"])
    with pytest.raises(smoke.TransportMarginError) as margin:
        _run([startup_margin + 1] + [1] * 7)
    assert margin.value.timing_frames[-1]["request_id"] == smoke.REQUEST_IDS[0]
    assert margin.value.timing_frames[-1]["classification"] == "QUALIFICATION_MARGIN_BLOCKED"

    startup_hard = int(smoke.TIMING_POLICY["startup_load"]["hard_wall_ns"])
    with pytest.raises(smoke.TransportResourceError) as resource:
        _run([startup_hard + 1] + [1] * 7)
    assert resource.value.timing_frames[-1]["classification"] == "RESOURCE_BLOCKED"

    shutdown_margin = int(smoke.TIMING_POLICY["shutdown"]["success_margin_ns"])
    with pytest.raises(smoke.TransportMarginError) as shutdown:
        _run([1] * 7 + [shutdown_margin + 1])
    assert shutdown.value.timing_frames[-1]["request_id"] == smoke.REQUEST_IDS[-1]


def test_fault_emits_exact_gap_free_terminal_prefix_and_no_later_frames() -> None:
    clock, start = _sequence_clock([1] * 8)
    transport = FakeTransport(fail_at=3)
    with pytest.raises(smoke.TransportError) as captured:
        smoke.run_synthetic_rpc_sequence(transport, clock_ns=clock, startup_start_ns=start)
    frames = captured.value.timing_frames
    assert len(frames) == 4
    assert [frame["sequence"] for frame in frames] == [1, 2, 3, 4]
    assert [frame["completed"] for frame in frames] == [True, True, True, False]
    smoke.validate_timing_frames(frames, completed_process=False)
    assert len(transport.requests) == 4


def test_timing_prefix_reorder_missing_and_classification_mismatch_are_rejected() -> None:
    evidence, _ = _run()
    frames = evidence["timing_frames"]
    missing = list(frames)
    del missing[2]
    reordered = list(frames)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    mismatch = [dict(frame) for frame in frames]
    mismatch[3]["clock_class"] = "control"
    for mutant in (missing, reordered, mismatch):
        with pytest.raises(ValueError):
            smoke.validate_timing_frames(mutant, completed_process=True)


def test_child_result_and_receipt_are_nonce_scoped_transient_and_strict() -> None:
    evidence, _ = _run()
    identity = _identity()
    result = _success_child_result(evidence, identity)
    result_raw = smoke.canonical_bytes(result)
    assert smoke.parse_child_result(result_raw) == result
    receipt = {
        "schema_version": smoke.RECEIPT_SCHEMA,
        "receipt_kind": "CHILD_RESULT",
        "nonce": result["nonce"],
        "fixture_role": "ARCHIVAL",
        "process_ordinal": 6,
        "child_result_length": len(result_raw),
        "child_result_sha256": hashlib.sha256(result_raw).hexdigest().upper(),
        "environment_digest": result["environment_digest"],
        "identity_digest": result["identity_digest"],
        "leaf_sha256": _leaf_sha256(),
        "worker_sha256": smoke.FIXED_WORKER_SHA256,
        "timing_policy_digest": smoke.timing_policy_digest(),
    }
    assert smoke.validate_receipt(smoke.canonical_bytes(receipt), result_raw, identity) == receipt
    assert "SYNTHETIC_OFFICIAL_TRANSPORT_V2_QUALIFIED" not in result_raw.decode("utf-8")


def test_child_success_cannot_hide_margin_or_mint_v1_or_upper_stack_claims() -> None:
    evidence, _ = _run()
    result = _success_child_result(evidence, _identity())
    result["timing_frames"] = [dict(frame) for frame in result["timing_frames"]]
    frame = result["timing_frames"][3]
    frame["end_ns"] = frame["start_ns"] + frame["success_margin_ns"] + 1
    frame["elapsed_ns"] = frame["success_margin_ns"] + 1
    frame["classification"] = "QUALIFICATION_MARGIN_BLOCKED"
    with pytest.raises(ValueError):
        smoke.parse_child_result(smoke.canonical_bytes(result))
    result["schema_version"] = "lean-rgc-uprime-official-transport-child-result-v1.0"
    with pytest.raises(ValueError):
        smoke.parse_child_result(smoke.canonical_bytes(result))
    result = _success_child_result(evidence, _identity())
    result["gpu_qualified"] = True
    with pytest.raises(ValueError, match="field"):
        smoke.parse_child_result(smoke.canonical_bytes(result))


def test_child_parser_rejects_floats_duplicates_noncanonical_and_mixed_roles() -> None:
    evidence, _ = _run()
    result = _success_child_result(evidence, _identity())
    raw = smoke.canonical_bytes(result)
    with pytest.raises(ValueError, match="canonical"):
        smoke.parse_child_result(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    with pytest.raises(ValueError):
        smoke.parse_child_result(raw[:-1] + b',"schema_version":"duplicate"}')
    result["process_ordinal"] = 1
    with pytest.raises(ValueError, match="role"):
        smoke.parse_child_result(smoke.canonical_bytes(result))
    result = _success_child_result(evidence, _identity())
    result["payload"]["final_n_states"] = 0.0
    with pytest.raises(ValueError, match="floating"):
        smoke.parse_child_result(smoke.canonical_bytes(result))


def test_runtime_fence_denies_prearm_process_and_arbitrary_file() -> None:
    fence = smoke.RuntimeFence(leaf_path=LEAF, python_path=Path(sys.executable), repo_root=ROOT)
    with pytest.raises(smoke.ScopeViolation, match="before ARM"):
        fence.audit("subprocess.Popen", (sys.executable, [sys.executable], None, None))
    with pytest.raises(smoke.ScopeViolation, match="file access"):
        fence.audit("open", (str(ROOT / "docs" / "experiments" / "inputs" / "forbidden.json"), "rb", 0))
    with pytest.raises(smoke.ScopeViolation, match="package import"):
        fence.import_guard("lean_rgc")


def test_arm_policy_and_caps_fail_before_paths_are_opened() -> None:
    arm = {
        "schema_version": smoke.ARM_SCHEMA,
        "nonce": "c" * 32,
        "fixture_role": "QUALIFICATION",
        "process_ordinal": 1,
        "lean_executable": "Z:/missing/lean.exe",
        "lean_sha256": smoke.FIXED_LEAN_SHA256,
        "worker_path": "Z:/missing/worker.lean",
        "worker_blob": smoke.FIXED_WORKER_BLOB,
        "worker_sha256": smoke.FIXED_WORKER_SHA256,
        "repo_root": "Z:/missing",
        "run_temp": "Z:/missing/temp",
        "child_result_path": "Z:/missing/temp/uprime_transport_v2_child_result." + "c" * 32 + ".json",
        "child_receipt_path": "Z:/missing/temp/uprime_transport_v2_child_receipt." + "c" * 32 + ".json",
        "environment_digest": _hex("E"),
        "identity": _identity(),
        "timing_policy": smoke.TIMING_POLICY,
        "timing_policy_digest": smoke.timing_policy_digest(),
        "response_limit_bytes": smoke.RESPONSE_MAX_BYTES,
        "stream_limit_bytes": smoke.STREAM_LIMIT_BYTES,
        "artifact_limit_bytes": smoke.ARTIFACT_MAX_BYTES,
        "receipt_limit_bytes": smoke.RECEIPT_MAX_BYTES,
        "request_count": 9,
        "task_count": 1,
        "action_count": 1,
        "max_open_states": 2,
    }
    with pytest.raises(ValueError, match="cap"):
        smoke.validate_arm(arm, nonce="c" * 32, leaf_path=LEAF, leaf_sha256=_leaf_sha256(), python_sha256=smoke.FIXED_PYTHON_SHA256)


def test_parent_and_child_clock_units_never_share_a_value_shape() -> None:
    child = {name: policy for name, policy in smoke.TIMING_POLICY.items() if policy["authority"] == "child_monotonic_ns"}
    parent = {name: policy for name, policy in smoke.TIMING_POLICY.items() if policy["authority"] == "parent_stopwatch_ticks"}
    assert child and parent
    assert all(set(policy) == {"authority", "hard_wall_ns", "success_margin_ns"} for policy in child.values())
    assert all(set(policy) == {"authority", "hard_wall_seconds", "success_margin_seconds"} for policy in parent.values())
    evidence, _ = _run()
    result = _success_child_result(evidence, _identity())
    assert not ({"fixture_elapsed_ticks", "batch_elapsed_ticks", "publication_elapsed_ticks", "stopwatch_frequency"} & set(result))


def test_parent_canonical_root_ref_and_i1_identity_are_frozen() -> None:
    source = PARENT.read_text(encoding="utf-8")
    assert r'C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live' in source
    assert 'codex/uprime-official-transport-v2-precommit-recovery-result' in source
    for suffix in (
        "ACCEPTED_COMMIT", "ACCEPTED_TREE", "ACCEPTED_RUN_ID", "ACCEPTED_JOB_ID",
        "CANDIDATE_RUN_ID", "CANDIDATE_JOB_ID", "EXPECTED_FILE_DIGESTS_JSON",
    ):
        assert f"UPRIME_OFFICIAL_TRANSPORT_V2_I1_{suffix}" in source
    assert 'UPRIME_OFFICIAL_TRANSPORT_Q1*' in source  # explicit legacy rejection only


def test_parent_marker_and_process_order_is_exact_five_then_one() -> None:
    source = PARENT.read_text(encoding="utf-8")
    batch = source.index("$markerJson = New-BatchMarkerJson")
    loop = source.index("for ($ordinal = 1; $ordinal -le 5; $ordinal++)")
    run = source.index("$runMarkerJson = New-RunMarkerJson")
    archive = source.index('Invoke-V2Fixture -Role "ARCHIVAL" -Ordinal 6')
    assert batch < loop < run < archive
    assert source.count('Invoke-V2Fixture -Role "ARCHIVAL" -Ordinal 6') == 1
    assert "-Ordinal 7" not in source
    assert 'if (-not $fixture["success"]) { $terminal = $fixture; break }' in source
    loop_body = source[loop:run]
    assert loop_body.index("New-BatchBlockResult") < loop_body.index('Invoke-V2Fixture -Role "QUALIFICATION"')
    run_to_archive = source[run:archive]
    assert "New-BatchBlockResult" in run_to_archive


def test_parent_all_blocking_edges_consume_absolute_deadlines() -> None:
    source = PARENT.read_text(encoding="utf-8")
    for token in (
        "StartAndAssignAsync", "Get-RemainingMilliseconds", "Read-BoundedUtf8LineUntil",
        "Write-ChildFrameUntil", "PublicationDeadlineTicks", "Assert-Deadline",
    ):
        assert token in source
    assert "Elapsed.TotalSeconds" not in source
    assert "WaitForExit()" not in source
    invocation = source.index("[UPrimeOfficialTransportV2Job]::StartAndAssignAsync")
    assert source.index("$readyStart = Get-NowTicks") < invocation


def test_parent_publication_is_two_layer_and_not_self_attributed() -> None:
    source = PARENT.read_text(encoding="utf-8")
    start = source.index("$publicationStart = Get-NowTicks")
    serialize = source.index("$envelopeJson = New-FinalEnvelopeJson", start)
    publish = source.index("Publish-ParentEnvelope", serialize)
    assert start < serialize < publish
    envelope_builder = source[source.index("function New-FinalEnvelopeJson"):source.index("function Assert-HexDigest")]
    assert "artifact_publication" not in envelope_builder
    assert '$closeout["artifact_publication"]' in source
    assert "archival_child_result" in envelope_builder
    assert "qualification_result_digests" in envelope_builder


def test_parent_failure_topology_is_marker_owned_r_else_f_and_zero_diagnostics() -> None:
    source = PARENT.read_text(encoding="utf-8")
    assert '$route = if ($markerOwned) { "R" } else { "F" }' in source
    assert '$failure["additional_live_worker_diagnostics"] = 0' in source
    assert '$markerOwned = $true' in source
    assert source.index('$markerOwned = $true') < source.index('for ($ordinal = 1; $ordinal -le 5; $ordinal++)')


def test_unit_runner_is_fake_only_and_uses_one_integer_parent_clock() -> None:
    source = UNIT_RUNNER.read_text(encoding="utf-8")
    assert "leanprover" not in source
    assert "lean.exe" not in source
    assert "RUN_LIVE_WORKER" not in source
    assert "Elapsed.TotalSeconds" not in source
    assert "_deadline = time.monotonic" not in source
    assert "StartAssigned" in source
    assert "$startRemainingTicks =" in source
    assert source.index("[Diagnostics.Stopwatch]::StartNew()") < source.index("::StartAssigned(")


def test_parent_marker_and_final_envelope_field_sets_are_disjoint() -> None:
    source = PARENT.read_text(encoding="utf-8")
    batch = source[source.index("function New-BatchMarkerJson"):source.index("function New-RunMarkerJson")]
    run = source[source.index("function New-RunMarkerJson"):source.index("function New-FinalEnvelopeJson")]
    final = source[source.index("function New-FinalEnvelopeJson"):source.index("function Assert-HexDigest")]
    assert "qualification_result_digests" not in batch
    assert "fixture_summaries" not in batch
    assert "qualification_result_digests" in run
    assert "fixture_summaries" in run
    assert "identity" in final and "process_graph" in final and "batch_execution" in final


def test_orphan_zero_is_integrated_into_each_fixed_fixture_not_a_seventh_process() -> None:
    source = PARENT.read_text(encoding="utf-8")
    fixture = source[source.index("function Invoke-V2Fixture"):source.index("function Publish-ParentEnvelope")]
    assert "Job orphan-zero assertion failed" in fixture
    assert '$summary["job_orphan_zero"] = $true' in fixture
    assert '$node["job_orphan_zero"] = $true' in fixture
    assert "process 7" not in source.lower()


def test_parent_artifact_contains_execution_not_final_qualification() -> None:
    source = PARENT.read_text(encoding="utf-8")
    builder = source[source.index("function New-FinalEnvelopeJson"):source.index("function Assert-HexDigest")]
    assert "execution_disposition" in builder
    assert "SYNTHETIC_OFFICIAL_TRANSPORT_V2_QUALIFIED" not in builder
    assert source.index("SYNTHETIC_OFFICIAL_TRANSPORT_V2_QUALIFIED") > source.index("$publicationClass =")


def test_v1_and_forensic_q1_names_have_no_runtime_fallback() -> None:
    leaf = LEAF.read_text(encoding="utf-8")
    parent = PARENT.read_text(encoding="utf-8")
    unit = UNIT_RUNNER.read_text(encoding="utf-8")
    for forbidden in ("PROBE_V1", "official-transport-artifact-v1.0", "run_uprime_official_transport_tests.ps1"):
        assert forbidden not in leaf
        assert forbidden not in parent
        assert forbidden not in unit
