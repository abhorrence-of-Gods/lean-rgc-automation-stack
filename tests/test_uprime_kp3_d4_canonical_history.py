from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path

import pytest

from lean_rgc.evals.uprime_kp3_d4_canonical_history import (
    MAX_OPEN_STATES,
    MAX_TRANSITION_ROWS,
    ConditionalNativeHistoryResult,
    DuplicateAuditReport,
    KernelRPCNativeSession,
    KernelRPCNativeFactory,
    NativeAction,
    NativeClosureError,
    NativeOpenObservation,
    NativeTask,
    NativeTransition,
    NativeResourceError,
    NativeDomainError,
    NativeExecutionError,
    NativeNormalizationError,
    _parse_frozen_input_bytes,
    _failure_record,
    _validate_persisted_domain_wire,
    _validate_persisted_hankel_authority,
    _enforce_row_cap,
    _enforce_state_cap,
    build_conditional_native_history,
    build_official_artifact,
    validate_official_artifact,
    parse_registered_input_bytes,
)
from lean_rgc.odlrq.history_normal_form import (
    CONDITIONAL_KSTATE_MARKOV,
    ExactOutcomeKind,
)
from lean_rgc.odlrq.contracts import StrictContractError
from lean_rgc.lean.kernel_rpc_client import (
    KernelRPCTransportTimeout,
    StrictKernelRPCOracleAdapter,
)


def _sha_bytes(label: str) -> bytes:
    return hashlib.sha256(label.encode()).digest()


def _sha_text(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest().upper()


class Handle:
    def __init__(self, state: str, path: tuple[str, ...]) -> None:
        self.state = state
        self.path = path


def _observation(handle: Handle, *, key_label: str | None = None) -> NativeOpenObservation:
    state = handle.state
    return NativeOpenObservation(
        handle=handle,
        index_sha256=_sha_bytes(state if key_label is None else key_label),
        full_signature=f"full:{state}".encode(),
        debt=(len(state), 0, 0, 0, 0),
        response_signature=f"response:{state}".encode(),
    )


class FakeSession:
    def __init__(
        self,
        graph: dict[tuple[str, str], tuple[str, str | None]],
        *,
        collision: bool = False,
        mismatch_duplicate: bool = False,
        delayed_dependency: bool = False,
        censor: bool = False,
    ) -> None:
        self.graph = graph
        self.collision = collision
        self.mismatch_duplicate = mismatch_duplicate
        self.delayed_dependency = delayed_dependency
        self.censor = censor
        self.closed: set[int] = set()
        self.session_closed = False

    def initialize(self, task: NativeTask) -> NativeOpenObservation:
        state = task.payload["seed"]
        handle = Handle(state, (task.task_id,))
        value = _observation(handle)
        if self.collision and task.task_id == "t1":
            value = replace(value, full_signature=b"full:collision")
        return value

    def apply(self, source_handle: object, action: NativeAction) -> NativeTransition:
        assert type(source_handle) is Handle
        source = source_handle
        if self.censor:
            return NativeTransition(
                kind="censor",
                replay_verified=False,
                replay_digest=_sha_text("censor"),
                semantic_signature=b"censor",
                verification_mode="rpc_censor",
                censor_reason="rpc_censor",
            )
        kind, target_name = self.graph[(source.state, action.action_id)]
        semantic = f"{source.state}:{action.action_id}:{kind}:{target_name}"
        if self.mismatch_duplicate and source.path[0] == "t1":
            semantic += ":hidden-handle"
        if self.delayed_dependency and len(source.path) > 2:
            semantic += ":delayed"
        target = None
        enum_kind = ExactOutcomeKind(kind)
        if enum_kind is ExactOutcomeKind.OPEN:
            assert target_name is not None
            target_handle = Handle(target_name, source.path + (action.action_id,))
            target = _observation(target_handle)
        return NativeTransition(
            kind=enum_kind,
            replay_verified=True,
            replay_digest=_sha_text(semantic),
            semantic_signature=semantic.encode(),
            target=target,
            verification_mode=(
                "replay_verified_failure"
                if enum_kind is ExactOutcomeKind.SINK
                else "replay_verified_success"
            ),
        )

    def close_handle(self, handle: object) -> None:
        assert id(handle) not in self.closed
        self.closed.add(id(handle))

    def close(self) -> None:
        self.session_closed = True


class FakeFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.opened = 0
        self.tasks: tuple[NativeTask, ...] | None = None

    def open(self, tasks: tuple[NativeTask, ...]) -> FakeSession:
        self.opened += 1
        self.tasks = tasks
        return self.session


def _inputs(*, two_tasks: bool = True) -> tuple[tuple[NativeTask, ...], tuple[NativeAction, ...]]:
    tasks = [NativeTask("t0", {"seed": "s0"})]
    if two_tasks:
        tasks.append(NativeTask("t1", {"seed": "s0"}))
    return tuple(tasks), (NativeAction("a", {"syntax": "exact True.intro"}),)


def _clock() -> callable:
    values = iter(index / 10_000 for index in range(100_000))
    return lambda: next(values)


def _run(session: FakeSession, *, two_tasks: bool = True):
    tasks, actions = _inputs(two_tasks=two_tasks)
    return build_conditional_native_history(
        tasks=tasks,
        actions=actions,
        factory=FakeFactory(session),
        source_authority="registered-native-fresh-family",
        frame_digest=_sha_text("frame"),
        clock=_clock(),
    )


def test_happy_fixed_point_is_conditional_and_builds_h1_through_h4() -> None:
    session = FakeSession({("s0", "a"): ("sink", None)})
    result = _run(session)
    assert result.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert result.chart.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert len(result.chart.domain.open_states) == 1
    assert len(result.chart.domain.transition_rows) == 1
    assert tuple(item.cutoff for item in result.hankels) == (1, 2, 3, 4)
    assert tuple(item.exactness_scope for item in result.hankels) == (
        CONDITIONAL_KSTATE_MARKOV,
    ) * 4
    assert result.duplicate_audit.rows_checked >= 1
    assert session.session_closed
    encoded = result.to_canonical_json_bytes()
    assert json.loads(encoded)["exactness_scope"] == CONDITIONAL_KSTATE_MARKOV


def test_immediate_hidden_handle_dependency_is_rejected() -> None:
    session = FakeSession(
        {("s0", "a"): ("sink", None)}, mismatch_duplicate=True
    )
    with pytest.raises(NativeClosureError, match="duplicate handle changed"):
        _run(session)
    assert session.session_closed


def test_delayed_dependency_does_not_become_an_unconditional_theorem() -> None:
    # Duplicate rows agree at the admitted bounded audit surface.  A facade may
    # still hide a dependency beyond it; therefore a passing result is labelled
    # conditional rather than sold as a Markov proof.
    session = FakeSession(
        {("s0", "a"): ("sink", None)}, delayed_dependency=True
    )
    result = _run(session)
    assert result.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    with pytest.raises(NativeClosureError, match="scope must remain conditional"):
        replace(result, exactness_scope="UNCONDITIONAL_FINITE_DOMAIN")


def test_canonical_index_collision_is_rejected_before_expansion() -> None:
    session = FakeSession({("s0", "a"): ("closed", None)}, collision=True)
    with pytest.raises(NativeClosureError, match="collision changed"):
        _run(session)
    assert session.session_closed


def test_rpc_censor_is_fail_closed() -> None:
    session = FakeSession({("s0", "a"): ("closed", None)}, censor=True)
    with pytest.raises(NativeDomainError, match="domain censor"):
        _run(session, two_tasks=False)


def test_state_and_transition_caps_are_independent_fail_closed_checks() -> None:
    _enforce_state_cap(MAX_OPEN_STATES)
    _enforce_row_cap(MAX_TRANSITION_ROWS)
    with pytest.raises(NativeClosureError, match="1024-state"):
        _enforce_state_cap(MAX_OPEN_STATES + 1)
    with pytest.raises(NativeClosureError, match="12288-row"):
        _enforce_row_cap(MAX_TRANSITION_ROWS + 1)


def test_timeout_is_checked_independently_of_cardinality() -> None:
    tasks, actions = _inputs(two_tasks=False)
    session = FakeSession({("s0", "a"): ("closed", None)})
    times = iter((0.0, 3_601.0))
    with pytest.raises(NativeClosureError, match="3600-second"):
        build_conditional_native_history(
            tasks=tasks,
            actions=actions,
            factory=FakeFactory(session),
            source_authority="registered-native-fresh-family",
            frame_digest=_sha_text("frame"),
            clock=lambda: next(times),
        )


def test_strict_input_parser_rejects_unknown_duplicate_and_float_fields() -> None:
    tasks = {
        "schema": "unit-task-matrix-v1",
        "tasks": [
            {
                "task_id": "t0",
                "statement": "True",
                "imports": ["Mathlib"],
                "prefix": "",
                "max_heartbeats": 20_000,
            }
        ],
    }
    actions = {
        "schema": "unit-action-matrix-v1",
        "actions": [
            {
                "action_id": "a",
                "opcode": "constructor",
                "target_selector": "first",
                "premise_slot_rule_id": None,
                "premise_selector_ordinal": None,
                "expected_normalized_type_signature": None,
                "global_constant": None,
                "opaque_hyperedge_source": None,
                "opaque_hyperedge_digest": None,
                "max_heartbeats": 20_000,
            }
        ],
    }
    parsed_tasks, parsed_actions, _, _ = _parse_frozen_input_bytes(
        json.dumps(tasks, separators=(",", ":")).encode(),
        json.dumps(actions, separators=(",", ":")).encode(),
    )
    assert parsed_tasks[0].task_id == "t0"
    assert parsed_actions[0].action_id == "a"

    bad_unknown = dict(tasks, extra=True)
    with pytest.raises(NativeClosureError, match="fields mismatch"):
        _parse_frozen_input_bytes(json.dumps(bad_unknown).encode(), json.dumps(actions).encode())
    duplicate = b'{"schema":"unit-task-matrix-v1","tasks":[],"tasks":[]}'
    with pytest.raises(NativeClosureError, match="duplicate"):
        _parse_frozen_input_bytes(duplicate, json.dumps(actions).encode())
    bad_float = json.dumps(tasks).replace("20000", "1.5").encode()
    with pytest.raises(NativeClosureError, match="floats"):
        _parse_frozen_input_bytes(bad_float, json.dumps(actions).encode())


def test_result_schema_validates_exact_nested_types() -> None:
    result = _run(FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False)
    with pytest.raises(NativeClosureError, match="Hankel family"):
        ConditionalNativeHistoryResult(
            chart=result.chart,
            raw_normalized_equality=result.raw_normalized_equality,
            flow_verification=result.flow_verification,
            hankels=tuple(reversed(result.hankels)),
            certificates=result.certificates,
            rank_verifications=result.rank_verifications,
            duplicate_audit=result.duplicate_audit,
            native_semantics_digest=result.native_semantics_digest,
            elapsed_ms=result.elapsed_ms,
        )


def test_open_fixed_point_expands_each_unique_representative_over_every_action() -> None:
    session = FakeSession(
        {
            ("s0", "a"): ("open", "s1"),
            ("s1", "a"): ("closed", None),
        }
    )
    result = _run(session, two_tasks=False)
    assert len(result.chart.domain.open_states) == 2
    assert len(result.chart.domain.transition_rows) == 2
    assert {row.outcome_kind for row in result.chart.domain.transition_rows} == {
        ExactOutcomeKind.OPEN,
        ExactOutcomeKind.CLOSED,
    }


def test_result_rejects_cross_source_splices_reordering_and_elapsed_overrun() -> None:
    closed = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    sink = _run(FakeSession({("s0", "a"): ("sink", None)}), two_tasks=False)
    with pytest.raises(NativeClosureError, match="source binding"):
        replace(closed, raw_normalized_equality=sink.raw_normalized_equality)
    with pytest.raises(NativeClosureError, match="Hankel family"):
        replace(closed, hankels=tuple(reversed(closed.hankels)))
    with pytest.raises(NativeClosureError, match="certificate/Hankel splice"):
        replace(closed, certificates=tuple(reversed(closed.certificates)))
    with pytest.raises(NativeClosureError, match="verification/certificate splice"):
        replace(
            closed,
            rank_verifications=tuple(reversed(closed.rank_verifications)),
        )
    with pytest.raises(NativeClosureError, match="semantics digest mismatch"):
        replace(closed, native_semantics_digest=_sha_text("foreign semantics"))
    with pytest.raises(NativeClosureError, match="whole-run wall"):
        replace(closed, elapsed_ms=3_600_001)
    with pytest.raises(Exception):
        replace(closed.chart, max_depth=3)


def test_result_rejects_duplicate_audit_splice() -> None:
    result = _run(FakeSession({("s0", "a"): ("closed", None)}))
    forged = DuplicateAuditReport(
        retained_occurrences=result.duplicate_audit.retained_occurrences,
        rows_checked=result.duplicate_audit.rows_checked + 1,
        saturated=result.duplicate_audit.saturated,
        digest=result.duplicate_audit.digest,
    )
    with pytest.raises(NativeClosureError, match="duplicate audit/chart"):
        replace(result, duplicate_audit=forged)


class AliasingSeedSession(FakeSession):
    def __init__(self) -> None:
        super().__init__({("s0", "a"): ("closed", None)})
        self.shared = _observation(Handle("s0", ("shared",)))

    def initialize(self, task: NativeTask) -> NativeOpenObservation:
        return self.shared


def test_initializer_handle_alias_is_rejected_on_second_acquire() -> None:
    session = AliasingSeedSession()
    with pytest.raises(NativeClosureError, match="aliased an already-owned"):
        _run(session)
    assert session.session_closed


def test_exact_128_of_129_duplicate_occurrences_are_audited_then_saturated() -> None:
    tasks = tuple(
        NativeTask(f"t{index:03d}", {"seed": "s0"}) for index in range(130)
    )
    result = build_conditional_native_history(
        tasks=tasks,
        actions=(NativeAction("a", {"syntax": "unit"}),),
        factory=FakeFactory(FakeSession({("s0", "a"): ("closed", None)})),
        source_authority="registered-native-fresh-family",
        frame_digest=_sha_text("frame"),
        clock=_clock(),
    )
    assert result.duplicate_audit.retained_occurrences == 128
    assert result.duplicate_audit.rows_checked == 128
    assert result.duplicate_audit.saturated is True
    assert result.chart.duplicate_row_checks == 128


def _official_identity_fixture() -> dict[str, object]:
    return {
        "c2_commit": "1" * 40,
        "c2_tree": "2" * 40,
        "c2_candidate_run_id": "1",
        "c2_candidate_job_id": "2",
        "c2_accepted_run_id": "3",
        "c2_accepted_job_id": "4",
        "environment_digest": _sha_text("environment"),
        "platform_record": "Windows_NT|X64|64-bit|PowerShell-5.1.26100.8655",
        "c2_allowlist_file_sha256": {
            "lean_rgc/evals/uprime_kp3_d4_canonical_history.py": _sha_text("a"),
            "tests/test_uprime_kp3_d4_canonical_history.py": _sha_text("b"),
            "tools/run_uprime_kp3_d4_native_tests.ps1": _sha_text("c"),
            "tools/run_uprime_kp3_d4_fresh_execution.ps1": _sha_text("d"),
            "tests/tier_manifest.json": _sha_text("e"),
        },
        "c2_control_attestation_scope": "EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER",
        "c2_file_digest_match": True,
    }


def test_fake_facade_result_cannot_mint_successful_official_artifact() -> None:
    fake = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    with pytest.raises(NativeClosureError, match="production provenance"):
        build_official_artifact(_official_identity_fixture(), result=fake)


def test_kernel_rpc_native_session_exercises_strict_jsonl_ownership_and_shutdown() -> None:
    from tests.test_uprime_u05_identity import (
        ENVIRONMENT_DIGEST,
        _AdapterScript,
        _ScriptedLineTransport,
        _synthetic_u05_task,
    )

    task = _synthetic_u05_task()
    native_task = NativeTask(
        task.task_id,
        {
            "task_id": task.task_id,
            "statement": task.statement,
            "imports": list(task.imports),
            "prefix": task.prefix,
            "max_heartbeats": 20_000,
        },
    )
    action = NativeAction(
        "a00_constructor_first",
        {
            "action_id": "a00_constructor_first",
            "opcode": "constructor",
            "target_selector": "first",
            "premise_slot_rule_id": None,
            "premise_selector_ordinal": None,
            "expected_normalized_type_signature": None,
            "global_constant": None,
            "opaque_hyperedge_source": None,
            "opaque_hyperedge_digest": None,
            "max_heartbeats": 20_000,
        },
    )
    transport = _ScriptedLineTransport(_AdapterScript(task, close_on_apply=True))
    transport.close = lambda: None
    adapter = StrictKernelRPCOracleAdapter(
        transport, environment_content_digest=ENVIRONMENT_DIGEST
    )
    session = KernelRPCNativeSession(
        transport, adapter, (native_task,), task.imports
    )
    source = session.initialize(native_task)
    transition = session.apply(source.handle, action)
    assert transition.kind is ExactOutcomeKind.CLOSED
    assert transition.replay_verified is True
    session.close_handle(source.handle)
    session.close()
    assert transport.finished is True
    assert session._clean_closeout_receipt is not None


def test_failure_record_is_typed_cause_traversal_without_raw_exception_text() -> None:
    cases = (
        (NativeResourceError("secret timeout path"), "D4_RESOURCE_BLOCKED", "RESOURCE_BLOCKED"),
        (NativeDomainError("secret replay bytes"), "D4_DOMAIN_INCOMPLETE", "DOMAIN_INCOMPLETE"),
        (NativeNormalizationError("secret collision"), "D4_NORMALIZATION_UNSOUND", "NORMALIZATION_UNSOUND"),
        (NativeExecutionError("secret transport path"), "D4_EXECUTION_FAILED", "EXECUTION_FAILED"),
    )
    for error, disposition, code in cases:
        observed, reason = _failure_record(error)
        assert observed == disposition
        assert reason.startswith(code + ":")
        assert "secret" not in reason
    try:
        try:
            raise NativeResourceError("inner heartbeat timeout")
        except NativeResourceError as exc:
            raise NativeExecutionError("outer transport") from exc
    except NativeExecutionError as nested:
        assert _failure_record(nested)[0] == "D4_RESOURCE_BLOCKED"


def test_arbitrary_five_by_twelve_inputs_cannot_activate_real_factory() -> None:
    tasks = tuple(NativeTask(f"t{index}", {"seed": "s0"}) for index in range(5))
    actions = tuple(NativeAction(f"a{index:02d}", {"unit": index}) for index in range(12))
    root = Path.cwd().resolve()
    factory = KernelRPCNativeFactory(
        repo_root=root,
        lean_binary=(root / "synthetic-lean.exe").resolve(),
        worker_source=(root / "synthetic-worker.lean").resolve(),
        environment_content_digest=_sha_text("environment"),
        worker_environment={"PATH": "synthetic"},
    )
    with pytest.raises(NativeDomainError, match="registered input authority"):
        build_conditional_native_history(
            tasks=tasks,
            actions=actions,
            factory=factory,
            source_authority="registered-native-fresh-family",
            frame_digest=_sha_text("frame"),
            clock=_clock(),
        )


def test_hankel_persisted_authority_rejects_matrix_conditioning_and_rank_mutations() -> None:
    result = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    wire = result.to_wire()
    original = (wire["hankels"][3], wire["certificates"][3], wire["rank_verifications"][3])
    _validate_persisted_hankel_authority(
        *original,
        cutoff=4,
        source_digest=wire["chart_digest"],
        task_ids=("t0",),
        action_ids=("a",),
    )
    mutations = []
    for target in ("matrix", "conditioning", "kind", "basis", "transcript", "verifier"):
        hankel, certificate, verification = copy.deepcopy(original)
        if target == "matrix":
            hankel["matrix"][0][0] += 1
        elif target == "conditioning":
            hankel["conditioning"] = 0
        elif target == "kind":
            certificate["kind"] = "RANK_AT_LEAST_65"
        elif target == "basis":
            certificate["basis_row_indices"] = [999]
        elif target == "transcript":
            certificate["elimination_transcript_digest"] = _sha_text("forged")
        else:
            verification["certificate_digest"] = _sha_text("forged verifier")
        mutations.append((hankel, certificate, verification))
    for mutated in mutations:
        with pytest.raises(NativeClosureError):
            _validate_persisted_hankel_authority(
                *mutated,
                cutoff=4,
                source_digest=wire["chart_digest"],
                task_ids=("t0",),
                action_ids=("a",),
            )


def test_persisted_hankel_rejects_foreign_duplicate_or_reordered_coordinates() -> None:
    result = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    wire = result.to_wire()
    original = (
        wire["hankels"][3],
        wire["certificates"][3],
        wire["rank_verifications"][3],
    )
    mutations = []
    reordered = copy.deepcopy(original)
    reordered[0]["suffix_words"][0], reordered[0]["suffix_words"][1] = (
        reordered[0]["suffix_words"][1],
        reordered[0]["suffix_words"][0],
    )
    mutations.append(reordered)
    foreign = copy.deepcopy(original)
    foreign[0]["suffix_words"][1] = ["foreign_action"]
    mutations.append(foreign)
    duplicated = copy.deepcopy(original)
    duplicated[0]["row_keys"][1] = copy.deepcopy(duplicated[0]["row_keys"][0])
    mutations.append(duplicated)
    for mutated in mutations:
        with pytest.raises(NativeClosureError, match="coordinate universe/order"):
            _validate_persisted_hankel_authority(
                *mutated,
                cutoff=4,
                source_digest=wire["chart_digest"],
                task_ids=("t0",),
                action_ids=("a",),
            )


def test_persisted_domain_reconstruction_rejects_duplicate_and_missing_rows() -> None:
    result = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    domain = result.to_wire()["domain"]
    reconstructed = _validate_persisted_domain_wire(
        domain, expected_digest=result.chart.domain.digest
    )
    assert reconstructed.digest == result.chart.domain.digest
    duplicate = copy.deepcopy(domain)
    duplicate["transitions"].append(copy.deepcopy(duplicate["transitions"][0]))
    missing = copy.deepcopy(domain)
    missing["transitions"].pop()
    for mutated in (duplicate, missing):
        with pytest.raises(NativeClosureError, match="failed reconstruction"):
            _validate_persisted_domain_wire(mutated)


def test_ordinary_failure_artifact_rejects_nonnull_or_bad_conditioning_censor() -> None:
    artifact = build_official_artifact(
        _official_identity_fixture(),
        result=None,
        failure_disposition="D4_RESOURCE_BLOCKED",
        failure_reason="RESOURCE_BLOCKED:" + _sha_text("resource"),
    )
    validate_official_artifact(artifact)
    nonnull = copy.deepcopy(artifact)
    nonnull["conditioning"] = 0
    bad_censor = copy.deepcopy(artifact)
    bad_censor["conditioning_censor"] = "ATTEMPTED"
    for mutated in (nonnull, bad_censor):
        with pytest.raises(NativeClosureError, match="conditioning"):
            validate_official_artifact(mutated)


def test_hankel_strict_contract_cap_is_typed_resource(monkeypatch) -> None:
    import lean_rgc.evals.uprime_kp3_d4_canonical_history as module

    def blocked(*_args, **_kwargs):
        raise StrictContractError("D4_RESOURCE_BLOCKED: coefficient bit cap exceeded")

    monkeypatch.setattr(module, "build_exact_raw_coordinate_hankel", blocked)
    with pytest.raises(NativeResourceError, match="resource-blocked") as caught:
        _run(FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False)
    assert _failure_record(caught.value)[0] == "D4_RESOURCE_BLOCKED"


def test_transport_normalization_and_byte_caps_have_typed_dispositions(monkeypatch) -> None:
    assert _failure_record(KernelRPCTransportTimeout("deadline"))[0] == (
        "D4_RESOURCE_BLOCKED"
    )
    normalization = StrictContractError(
        "D4_NORMALIZATION_UNSOUND: projected raw-coordinate cell mismatch"
    )
    assert _failure_record(normalization)[0] == "D4_NORMALIZATION_UNSOUND"

    import lean_rgc.evals.uprime_kp3_d4_canonical_history as module

    result = _run(
        FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False
    )
    artifact = build_official_artifact(
        _official_identity_fixture(),
        result=None,
        failure_disposition="D4_RESOURCE_BLOCKED",
        failure_reason="RESOURCE_BLOCKED:" + _sha_text("resource"),
    )
    monkeypatch.setattr(module, "MAX_RESULT_BYTES", 1)
    with pytest.raises(NativeResourceError, match="native result exceeds"):
        result.to_canonical_json_bytes()
    with pytest.raises(NativeResourceError, match="official artifact exceeds"):
        validate_official_artifact(artifact)


def test_hankel_normalization_prefix_is_not_laundered_as_resource(monkeypatch) -> None:
    import lean_rgc.evals.uprime_kp3_d4_canonical_history as module

    def unsound(*_args, **_kwargs):
        raise StrictContractError(
            "D4_NORMALIZATION_UNSOUND: exact raw-coordinate response mismatch"
        )

    monkeypatch.setattr(module, "build_exact_raw_coordinate_hankel", unsound)
    with pytest.raises(NativeNormalizationError, match="normalization was unsound"):
        _run(FakeSession({("s0", "a"): ("closed", None)}), two_tasks=False)


def test_official_runner_contains_external_digest_broker_and_receipt_policy() -> None:
    source = Path("tools/run_uprime_kp3_d4_fresh_execution.ps1").read_text(
        encoding="utf-8"
    )
    for token in (
        "UPRIME_KP3_D4_C2_EXPECTED_FILE_DIGESTS_JSON",
        "UPRIME_KP3_D4_C2_FILE_DIGEST_MATCH",
        "c2_file_digest_match",
        "UPRIME_KP3_D4_OUTPUT_RECEIPT",
        "UPRIME_KP3_D4_FIXED_IDENTITY_DIGEST",
        "artifact_canonical",
    ):
        assert token in source
