from __future__ import annotations

from dataclasses import replace
import json

import pytest

import lean_rgc.odlrq.contracts as odlrq_contracts
from lean_rgc.odlrq import (
    EXACT_ADMISSION_CHECKS,
    EXACT_PARTITION_VERIFICATION_CHECKS,
    MAX_EXACT_RATIONAL_BITS,
    MAX_EXACT_PARTITION_WORK_UNITS,
    MAX_SYNTHETIC_ACTIONS,
    MAX_SYNTHETIC_TOTALIZED_STATES,
    MAX_SYNTHETIC_TRANSITION_ROWS,
    NOT_APPLICABLE,
    SYNTHETIC_EVIDENCE_SCOPE,
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactAdmissionCompletionGate,
    ExactAdmissionReport,
    ExactDistinguishingWitness,
    ExactKernelTransitionCore,
    ExactPartitionBlock,
    ExactPartitionCertificate,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticEvidenceProfile,
    SyntheticExpansionStatus,
    SyntheticFiniteSnapshot,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    U05ProbeTransition,
    VerifiedExactPartition,
    admit_synthetic_finite_snapshot,
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
    refine_exact_partition,
    verify_exact_partition,
)
from lean_rgc.odlrq.reachable_chart import ReachableChart


ENV = "11" * 32
FRAME = "22" * 32
SEMANTICS = "33" * 32
COORDINATES = ("debt", "mass")


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


def _state(
    name: str,
    kind: TotalizedStatus,
    coordinates: tuple[int, int],
    **changes: object,
) -> SyntheticTotalizedState:
    values: dict[str, object] = {
        "state_id": f"unit_cpu_survivor_{name}",
        "payload": _payload("state", name),
        "totalized_kind": kind,
        "response_coordinates": tuple(ExactRational(value) for value in coordinates),
        "frame_digest": FRAME,
    }
    values.update(changes)
    return SyntheticTotalizedState(**values)  # type: ignore[arg-type]


def _action(name: str, **changes: object) -> SyntheticAction:
    values: dict[str, object] = {
        "action_id": f"unit_cpu_survivor_{name}",
        "payload": _payload("action", name),
    }
    values.update(changes)
    return SyntheticAction(**values)  # type: ignore[arg-type]


def _row(source: str, action: str, target: str, **changes: object) -> SyntheticTransitionRow:
    values: dict[str, object] = {
        "source_state_id": f"unit_cpu_survivor_{source}",
        "action_id": f"unit_cpu_survivor_{action}",
        "target_state_id": f"unit_cpu_survivor_{target}",
        "transition_semantics_digest": SEMANTICS,
    }
    values.update(changes)
    return SyntheticTransitionRow(**values)  # type: ignore[arg-type]


def _parts() -> tuple[
    tuple[SyntheticTotalizedState, ...],
    tuple[SyntheticAction, ...],
    tuple[SyntheticTransitionRow, ...],
]:
    states = (
        _state("s0", TotalizedStatus.OPEN, (2, 1)),
        _state("s1", TotalizedStatus.OPEN, (1, 1)),
        _state("closed", TotalizedStatus.CLOSED, (0, 0)),
        _state("sink", TotalizedStatus.SINK, (0, 0)),
    )
    actions = (_action("a"), _action("b"))
    rows = (
        _row("s0", "a", "s1"),
        _row("s0", "b", "sink"),
        _row("s1", "a", "closed"),
        _row("s1", "b", "s1"),
        _row("closed", "a", "closed"),
        _row("closed", "b", "closed"),
        _row("sink", "a", "sink"),
        _row("sink", "b", "sink"),
    )
    return states, actions, rows


def _candidate(
    *,
    states: tuple[SyntheticTotalizedState, ...] | None = None,
    actions: tuple[SyntheticAction, ...] | None = None,
    rows: tuple[SyntheticTransitionRow, ...] | None = None,
    seeds: tuple[str, ...] = ("unit_cpu_survivor_s0",),
    coordinates: tuple[str, ...] = COORDINATES,
) -> SyntheticFiniteSnapshot:
    original_states, original_actions, original_rows = _parts()
    selected_states = original_states if states is None else states
    selected_actions = original_actions if actions is None else actions
    selected_rows = original_rows if rows is None else rows
    if (
        len(selected_states) > MAX_SYNTHETIC_TOTALIZED_STATES
        or len(selected_actions) > MAX_SYNTHETIC_ACTIONS
        or len(selected_rows) > MAX_SYNTHETIC_TRANSITION_ROWS
        or len(selected_states) * len(selected_actions)
        > MAX_SYNTHETIC_TRANSITION_ROWS
    ):
        # Exercise the production preflight without inspecting or normalizing
        # any member beyond its Sequence length.
        return build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=coordinates,
            seed_state_ids=seeds,
            states=selected_states,
            actions=selected_actions,
            transitions=selected_rows,
        )
    vocabulary = ResponseVocabularyId.from_coordinate_names(coordinates)
    frame = make_synthetic_observation_frame_id(
        environment_digest=ENV,
        response_vocabulary_id=vocabulary,
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=selected_actions,
        response_vocabulary_id=vocabulary,
    )
    derived_frame = observation_frame_digest(frame)
    selected_states = tuple(
        replace(state, frame_digest=derived_frame)
        if state.frame_digest == FRAME
        else state
        for state in selected_states
    )
    selected_rows = tuple(
        replace(row, transition_semantics_digest=semantics.semantics_digest)
        if row.transition_semantics_digest == SEMANTICS
        else row
        for row in selected_rows
    )
    return build_synthetic_finite_snapshot(
        environment_digest=ENV,
        coordinate_names=coordinates,
        seed_state_ids=seeds,
        states=selected_states,
        actions=selected_actions,
        transitions=selected_rows,
    )


def test_synthetic_admission_is_permutation_canonical_and_kind_separating() -> None:
    states, actions, rows = _parts()
    left = _candidate(states=states, actions=actions, rows=rows)
    right = _candidate(
        states=tuple(reversed(states)),
        actions=tuple(reversed(actions)),
        rows=tuple(reversed(rows)),
    )
    assert left == right
    assert canonical_contract_bytes(left) == canonical_contract_bytes(right)

    admitted = admit_synthetic_finite_snapshot(left)
    assert admitted == ExactAdmissionCompletionGate.admit(right)
    assert admitted.evidence_scope == SYNTHETIC_EVIDENCE_SCOPE
    assert admitted.snapshot.evidence_profile == SyntheticEvidenceProfile()
    assert admitted.admission_report.checks == EXACT_ADMISSION_CHECKS
    assert admitted.admission_report.totalized_state_count == 4
    assert admitted.admission_report.concrete_state_count == 2
    assert admitted.admission_report.action_count == 2
    assert admitted.admission_report.transition_row_count == 8

    by_kind = {state.totalized_kind: state for state in admitted.snapshot.states}
    # User coordinates are identical, but the mandatory totalized tag differs.
    assert (
        by_kind[TotalizedStatus.CLOSED].response_coordinates
        == by_kind[TotalizedStatus.SINK].response_coordinates
    )
    assert (
        by_kind[TotalizedStatus.CLOSED].response_key
        != by_kind[TotalizedStatus.SINK].response_key
    )


def test_admitted_snapshot_strict_roundtrip_recomputes_the_gate() -> None:
    admitted = admit_synthetic_finite_snapshot(_candidate())
    payload = admitted.to_dict()
    decoded = json.loads(canonical_contract_bytes(admitted).decode("utf-8"))
    restored = AdmittedExactFiniteSnapshot.from_dict(decoded)
    assert restored == admitted
    assert canonical_contract_bytes(restored) == canonical_contract_bytes(admitted)

    with pytest.raises(StrictContractError, match="admission gate"):
        AdmittedExactFiniteSnapshot(admitted.snapshot, admitted.admission_report)

    wrong_scope = json.loads(json.dumps(payload))
    wrong_scope["evidence_scope"] = "lean_exact"
    with pytest.raises(StrictContractError, match="evidence[_ ]scope"):
        AdmittedExactFiniteSnapshot.from_dict(wrong_scope)

    wrong_report = json.loads(json.dumps(payload))
    wrong_report["admission_report"]["transition_row_count"] = 7
    with pytest.raises(StrictContractError, match="recomputed gate"):
        AdmittedExactFiniteSnapshot.from_dict(wrong_report)

    unknown = json.loads(json.dumps(payload))
    unknown["unknown"] = True
    with pytest.raises(StrictContractError, match="field mismatch"):
        AdmittedExactFiniteSnapshot.from_dict(unknown)

    _, _, rows = _parts()
    nontotal = _candidate(rows=rows[:-1])
    with pytest.raises(StrictContractError, match="not total"):
        # The private constructor/token is not a soundness bypass: __post_init__
        # independently recomputes the pure validator.
        AdmittedExactFiniteSnapshot._from_gate(
            nontotal, admitted.admission_report
        )


def test_typed_frame_and_semantics_are_content_bound() -> None:
    candidate = _candidate()
    assert (
        candidate.observation_frame_id.coordinate_schema_digest
        == candidate.response_vocabulary_id.coordinate_schema_digest
    )
    assert candidate.observation_frame_id.source_lane == SYNTHETIC_EVIDENCE_SCOPE
    assert (
        candidate.transition_semantics_id.action_alphabet_digest
        == candidate.domain_id.action_alphabet_digest
    )
    assert (
        candidate.transition_semantics_id.response_vocabulary_digest
        == candidate.response_vocabulary_id.vocabulary_digest
    )

    changed_vocabulary = ResponseVocabularyId.from_coordinate_names(
        ("different_debt", "mass")
    )
    with pytest.raises(StrictContractError, match="typed observation frame"):
        admit_synthetic_finite_snapshot(
            replace(candidate, response_vocabulary_id=changed_vocabulary)
        )

    changed_action = replace(
        candidate.actions[0], payload=_payload("action", "changed_payload")
    )
    with pytest.raises(StrictContractError, match="typed transition semantics"):
        admit_synthetic_finite_snapshot(
            replace(candidate, actions=(changed_action, *candidate.actions[1:]))
        )


def test_profile_and_vocabulary_cannot_shed_synthetic_provenance() -> None:
    with pytest.raises(StrictContractError, match="replay.*NOT_APPLICABLE"):
        SyntheticEvidenceProfile(replay="verified")
    with pytest.raises(StrictContractError, match="locality claim"):
        SyntheticEvidenceProfile(locality_claim=True)

    vocabulary = ResponseVocabularyId.from_coordinate_names(COORDINATES)
    bad = vocabulary.to_dict()
    bad["totalized_kind_in_key"] = False
    with pytest.raises(StrictContractError, match="totalized kind"):
        ResponseVocabularyId.from_dict(bad)

    bad = vocabulary.to_dict()
    bad["vocabulary_digest"] = "44" * 32
    with pytest.raises(StrictContractError, match="vocabulary digest"):
        ResponseVocabularyId.from_dict(bad)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"expansion_status": SyntheticExpansionStatus.QUEUED}, "queued/live"),
        ({"boundary_complete": False}, "queued/live"),
        ({"truncated": True}, "queued/live"),
        ({"live_handle": "rpc-state-1"}, "queued/live"),
        ({"frame_digest": "55" * 32}, "mixed observation frames"),
    ],
)
def test_state_admission_defects_fail_closed(
    changes: dict[str, object], message: str
) -> None:
    states, _, _ = _parts()
    broken = (replace(states[0], **changes), *states[1:])
    with pytest.raises(StrictContractError, match=message):
        admit_synthetic_finite_snapshot(_candidate(states=broken))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda rows: rows[:-1], "not total"),
        (lambda rows: (*rows, rows[0]), "duplicate rows"),
        (
            lambda rows: (
                replace(rows[0], target_state_id="unit_cpu_survivor_outside"),
                *rows[1:],
            ),
            "successor is outside",
        ),
        (
            lambda rows: (replace(rows[0], censor="wall_timeout"), *rows[1:]),
            "censored row",
        ),
        (
            lambda rows: (
                *rows[:4],
                replace(rows[4], target_state_id="unit_cpu_survivor_sink"),
                *rows[5:],
            ),
            "must be absorbing",
        ),
        (
            lambda rows: (
                replace(rows[0], transition_semantics_digest="66" * 32),
                *rows[1:],
            ),
            "mixed transition semantics",
        ),
    ],
)
def test_transition_admission_defects_fail_closed(mutate, message: str) -> None:
    _, _, rows = _parts()
    with pytest.raises(StrictContractError, match=message):
        admit_synthetic_finite_snapshot(_candidate(rows=tuple(mutate(rows))))


def test_identity_membership_response_and_digest_defects_fail_closed() -> None:
    states, actions, _ = _parts()

    duplicate_state_id = (states[0], replace(states[1], state_id=states[0].state_id), *states[2:])
    with pytest.raises(StrictContractError, match="state IDs contain duplicates"):
        admit_synthetic_finite_snapshot(_candidate(states=duplicate_state_id))

    wrong_prefix = (replace(states[0], state_id="u05_production_state"), *states[1:])
    with pytest.raises(StrictContractError, match="outside the frozen prefix"):
        admit_synthetic_finite_snapshot(_candidate(states=wrong_prefix))

    duplicate_payload = (states[0], replace(states[1], payload=states[0].payload), *states[2:])
    with pytest.raises(StrictContractError, match="state payloads contain duplicates"):
        admit_synthetic_finite_snapshot(_candidate(states=duplicate_payload))

    duplicate_action_id = (actions[0], replace(actions[1], action_id=actions[0].action_id))
    with pytest.raises(StrictContractError, match="action IDs contain duplicates"):
        admit_synthetic_finite_snapshot(_candidate(actions=duplicate_action_id))

    duplicate_action_payload = (actions[0], replace(actions[1], payload=actions[0].payload))
    with pytest.raises(StrictContractError, match="action payloads contain duplicates"):
        admit_synthetic_finite_snapshot(_candidate(actions=duplicate_action_payload))

    with pytest.raises(StrictContractError, match="every seed"):
        admit_synthetic_finite_snapshot(
            _candidate(seeds=("unit_cpu_survivor_closed",))
        )
    with pytest.raises(StrictContractError, match="nonempty and unique"):
        admit_synthetic_finite_snapshot(
            _candidate(seeds=("unit_cpu_survivor_s0", "unit_cpu_survivor_s0"))
        )
    states_for_empty, actions_for_empty, rows_for_empty = _parts()
    with pytest.raises(StrictContractError, match="seed-count"):
        build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=COORDINATES,
            seed_state_ids=(),
            states=states_for_empty,
            actions=actions_for_empty,
            transitions=rows_for_empty,
        )

    wrong_arity = (replace(states[0], response_coordinates=(ExactRational(1),)), *states[1:])
    with pytest.raises(StrictContractError, match="arity"):
        admit_synthetic_finite_snapshot(_candidate(states=wrong_arity))

    candidate = _candidate()
    forged_domain = replace(candidate.domain_id, domain_payload_digest="77" * 32)
    with pytest.raises(StrictContractError, match="digests do not match"):
        admit_synthetic_finite_snapshot(replace(candidate, domain_id=forged_domain))


def test_terminal_and_resource_caps_fail_closed() -> None:
    states, _, _ = _parts()
    without_sink = tuple(
        state for state in states if state.totalized_kind is not TotalizedStatus.SINK
    )
    with pytest.raises(StrictContractError, match="exactly one CLOSED and SINK"):
        admit_synthetic_finite_snapshot(_candidate(states=without_sink, rows=()))

    too_many_actions = tuple(_action(f"cap_{index}") for index in range(17))
    with pytest.raises(StrictContractError, match="action cap"):
        admit_synthetic_finite_snapshot(_candidate(actions=too_many_actions, rows=()))

    many_open = tuple(
        _state(f"cap_state_{index}", TotalizedStatus.OPEN, (index, 0))
        for index in range(127)
    )
    terminal_states = (
        _state("cap_closed", TotalizedStatus.CLOSED, (0, 0)),
        _state("cap_sink", TotalizedStatus.SINK, (0, 0)),
    )
    with pytest.raises(StrictContractError, match="state cap"):
        admit_synthetic_finite_snapshot(
            _candidate(states=(*many_open, *terminal_states), rows=())
        )


def test_every_open_state_must_be_reachable_from_a_seed() -> None:
    states, actions, rows = _parts()
    orphan = _state("orphan", TotalizedStatus.OPEN, (9, 9))
    orphan_rows = (
        _row("orphan", "a", "orphan"),
        _row("orphan", "b", "orphan"),
    )
    with pytest.raises(StrictContractError, match="reachable from a seed"):
        admit_synthetic_finite_snapshot(
            _candidate(
                states=(*states, orphan),
                actions=actions,
                rows=(*rows, *orphan_rows),
            )
        )


class _ExplodingSequence:
    def __len__(self) -> int:
        return MAX_SYNTHETIC_TOTALIZED_STATES + 1

    def __iter__(self):
        raise AssertionError("cap preflight read a payload")

    def __getitem__(self, index):
        raise AssertionError("cap preflight read a payload")


class _ExplodingPayload:
    def to_dict(self):
        raise AssertionError("snapshot cap validation serialized a payload")


class _LyingSequence:
    def __init__(self, value) -> None:
        self.value = value

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        while True:
            yield self.value


class _ExplodingCoordinates:
    def __len__(self) -> int:
        raise AssertionError("coordinate factory inspected a custom Sequence")

    def __iter__(self):
        raise AssertionError("coordinate factory iterated a custom Sequence")

    def __getitem__(self, index):
        raise AssertionError("coordinate factory indexed a custom Sequence")


class _InfiniteCoordinates:
    def __len__(self) -> int:
        return 2

    def __iter__(self):
        while True:
            yield "coordinate"


@pytest.mark.parametrize(
    "coordinates",
    ["debt", ["debt"], _ExplodingCoordinates(), _InfiniteCoordinates()],
)
def test_coordinate_factory_rejects_non_tuple_sources_without_iteration(
    coordinates,
) -> None:
    with pytest.raises(StrictContractError, match="exact tuple"):
        ResponseVocabularyId.from_coordinate_names(coordinates)

    states, actions, rows = _parts()
    with pytest.raises(StrictContractError, match="exact tuple"):
        build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=coordinates,
            seed_state_ids=("unit_cpu_survivor_s0",),
            states=states,
            actions=actions,
            transitions=rows,
        )


def test_resource_caps_precede_materialization_sort_and_hash() -> None:
    with pytest.raises(StrictContractError, match="before payload access"):
        build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=COORDINATES,
            seed_state_ids=("unit_cpu_survivor_s0",),
            states=_ExplodingSequence(),  # type: ignore[arg-type]
            actions=(),
            transitions=(),
        )

    states, actions, rows = _parts()
    with pytest.raises(StrictContractError, match="seed-count.*before payload"):
        build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=COORDINATES,
            seed_state_ids=_ExplodingSequence(),  # type: ignore[arg-type]
            states=states,
            actions=actions,
            transitions=rows,
        )

    valid = _candidate()
    with pytest.raises(StrictContractError, match="before materialization"):
        replace(
            valid,
            states=tuple(
                _ExplodingPayload()
                for _ in range(MAX_SYNTHETIC_TOTALIZED_STATES + 1)
            ),
        )
    with pytest.raises(StrictContractError, match="seed-count.*before materialization"):
        replace(
            valid,
            seed_state_ids=tuple(_ExplodingPayload() for _ in range(5)),
        )
    encoded = valid.to_dict()
    encoded["states"] = [
        _ExplodingPayload() for _ in range(MAX_SYNTHETIC_TOTALIZED_STATES + 1)
    ]
    with pytest.raises(StrictContractError, match="before parsing"):
        SyntheticFiniteSnapshot.from_dict(encoded)
    encoded = valid.to_dict()
    encoded["seed_state_ids"] = [_ExplodingPayload() for _ in range(5)]
    with pytest.raises(StrictContractError, match="seed-count.*before parsing"):
        SyntheticFiniteSnapshot.from_dict(encoded)

    with pytest.raises(StrictContractError, match="exceeds its cap"):
        build_synthetic_finite_snapshot(
            environment_digest=ENV,
            coordinate_names=COORDINATES,
            seed_state_ids=("unit_cpu_survivor_s0",),
            states=_LyingSequence(states[0]),  # type: ignore[arg-type]
            actions=actions,
            transitions=rows[:2],
        )


class _EvilReport(ExactAdmissionReport):
    def __eq__(self, other) -> bool:
        return True

    def __ne__(self, other) -> bool:
        return False

    def to_dict(self):
        return ExactAdmissionReport.to_dict(self)


class _EvilState(SyntheticTotalizedState):
    @property
    def response_key(self):
        return (TotalizedStatus.CLOSED.value, ())

    def __eq__(self, other) -> bool:
        return True


class _EvilAdmitted(AdmittedExactFiniteSnapshot):
    def to_dict(self):
        return {"forged": True}


class _EvilScope(str):
    def __new__(cls):
        return str.__new__(cls, "lean_exact")

    def __eq__(self, other) -> bool:
        return True

    def __ne__(self, other) -> bool:
        return False


class _EqualityForgingObject:
    def __eq__(self, other) -> bool:
        return True

    def __ne__(self, other) -> bool:
        return False


class _EqualityForgingKey:
    def __init__(self, target: str) -> None:
        self.target = target

    def __hash__(self) -> int:
        return hash(self.target)

    def __eq__(self, other) -> bool:
        return other == self.target


def test_strict_boundaries_reject_polymorphic_equality_and_response_members() -> None:
    admitted = admit_synthetic_finite_snapshot(_candidate())
    report = admitted.admission_report
    evil_report = _EvilReport(
        snapshot_sha256=report.snapshot_sha256,
        totalized_state_count=report.totalized_state_count,
        concrete_state_count=report.concrete_state_count,
        action_count=report.action_count,
        transition_row_count=report.transition_row_count,
        checks=report.checks,
    )
    with pytest.raises(StrictContractError, match="admission report payload"):
        AdmittedExactFiniteSnapshot._from_gate(admitted.snapshot, evil_report)
    with pytest.raises(StrictContractError, match="polymorphic exact admission"):
        _EvilAdmitted._from_gate(admitted.snapshot, report)
    with pytest.raises(StrictContractError, match="evidence_scope.*exact literal"):
        AdmittedExactFiniteSnapshot(
            admitted.snapshot,
            report,
            evidence_scope=_EvilScope(),
            _gate_token=odlrq_contracts._EXACT_ADMISSION_TOKEN,
        )

    forged_top = admitted.to_dict()
    forged_top["evidence_scope"] = _EqualityForgingObject()
    with pytest.raises(StrictContractError, match="evidence_scope.*exact literal"):
        AdmittedExactFiniteSnapshot.from_dict(forged_top)

    forged_nested = admitted.to_dict()
    forged_nested["snapshot"]["domain_id"]["schema_version"] = (
        _EqualityForgingObject()
    )
    with pytest.raises(StrictContractError, match="strict canonical JSON"):
        AdmittedExactFiniteSnapshot.from_dict(forged_nested)

    forged_frame = admitted.to_dict()
    forged_frame["snapshot"]["observation_frame_id"]["schema_version"] = (
        _EqualityForgingObject()
    )
    with pytest.raises(StrictContractError, match="strict canonical JSON"):
        AdmittedExactFiniteSnapshot.from_dict(forged_frame)

    forged_top_key = admitted.to_dict()
    scope_value = forged_top_key.pop("evidence_scope")
    forged_top_key[_EqualityForgingKey("evidence_scope")] = scope_value
    with pytest.raises(StrictContractError, match="keys must be exact strings"):
        AdmittedExactFiniteSnapshot.from_dict(forged_top_key)

    forged_nested_key = admitted.to_dict()
    domain = forged_nested_key["snapshot"]["domain_id"]
    schema_value = domain.pop("schema_version")
    domain[_EqualityForgingKey("schema_version")] = schema_value
    with pytest.raises(StrictContractError, match="strict canonical JSON"):
        AdmittedExactFiniteSnapshot.from_dict(forged_nested_key)

    state = admitted.snapshot.states[0]
    evil_state = _EvilState(
        state_id=state.state_id,
        payload=state.payload,
        totalized_kind=state.totalized_kind,
        response_coordinates=state.response_coordinates,
        frame_digest=state.frame_digest,
        expansion_status=state.expansion_status,
        boundary_complete=state.boundary_complete,
        truncated=state.truncated,
        live_handle=state.live_handle,
    )
    with pytest.raises(StrictContractError, match="wrong type"):
        replace(
            admitted.snapshot,
            states=(evil_state, *admitted.snapshot.states[1:]),
        )


def test_canonical_payload_rational_and_array_forms_are_strict() -> None:
    with pytest.raises(StrictContractError, match="canonical JSON"):
        CanonicalPayload('{"z":1, "a":2}')
    assert ExactRational(2, 4) == ExactRational(1, 2)
    with pytest.raises(StrictContractError, match="reduced canonical"):
        ExactRational.from_dict(
            {
                "schema_version": "lean-rgc-odlrq-exact-rational-v1",
                "numerator": "2",
                "denominator": "4",
            }
        )

    payload = _candidate().to_dict()
    payload["states"] = list(reversed(payload["states"]))
    with pytest.raises(StrictContractError, match="arrays are not canonical"):
        SyntheticFiniteSnapshot.from_dict(payload)


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        ("+1", "1"),
        ("01", "1"),
        ("-0", "1"),
        ("1", "+1"),
        ("1", "01"),
        ("1", "0"),
        ("1", "-1"),
    ],
)
def test_exact_rational_rejects_noncanonical_decimal_strings(
    numerator: str, denominator: str
) -> None:
    with pytest.raises(StrictContractError, match="canonical decimal"):
        ExactRational.from_dict(
            {
                "schema_version": "lean-rgc-odlrq-exact-rational-v1",
                "numerator": numerator,
                "denominator": denominator,
            }
        )


def test_exact_rational_bit_cap_is_checked_before_reduction() -> None:
    boundary = (1 << MAX_EXACT_RATIONAL_BITS) - 1
    value = ExactRational(boundary, boundary - 2)
    assert ExactRational.from_dict(value.to_dict()) == value
    assert value.to_dict()["numerator"] == str(boundary)

    with pytest.raises(StrictContractError, match="pre-reduction cap"):
        ExactRational(1 << MAX_EXACT_RATIONAL_BITS, 1)
    with pytest.raises(StrictContractError, match="pre-reduction cap"):
        # This would reduce to 1, but both inputs are over the frozen cap.
        ExactRational(1 << MAX_EXACT_RATIONAL_BITS, 1 << MAX_EXACT_RATIONAL_BITS)
    with pytest.raises(StrictContractError, match="pre-reduction cap"):
        ExactRational.from_dict(
            {
                "schema_version": "lean-rgc-odlrq-exact-rational-v1",
                "numerator": "1" + "0" * 3_000,
                "denominator": "1",
            }
        )


@pytest.mark.parametrize(
    "source",
    [
        object.__new__(ExactKernelTransitionCore),
        object.__new__(U05ProbeTransition),
        object.__new__(ReachableChart),
    ],
)
def test_lean_u05_and_reachable_chart_promotions_are_explicitly_rejected(source) -> None:
    with pytest.raises(StrictContractError, match="cannot be promoted"):
        admit_synthetic_finite_snapshot(source)


def test_report_schema_cannot_drop_checks() -> None:
    report = admit_synthetic_finite_snapshot(_candidate()).admission_report
    assert ExactAdmissionReport.from_dict(report.to_dict()) == report
    bad = report.to_dict()
    bad["checks"] = bad["checks"][:-1]
    with pytest.raises(StrictContractError, match="incomplete or reordered"):
        ExactAdmissionReport.from_dict(bad)

    assert NOT_APPLICABLE == "NOT_APPLICABLE"


SEMANTIC_A_ID = "unit_cpu_survivor_locator_z"
SEMANTIC_Z_ID = "unit_cpu_survivor_locator_a"


def _delayed_partition_candidate() -> SyntheticFiniteSnapshot:
    states = (
        _state("u", TotalizedStatus.OPEN, (2, 2)),
        _state("v", TotalizedStatus.OPEN, (2, 2)),
        _state("m", TotalizedStatus.OPEN, (1, 1)),
        _state("n", TotalizedStatus.OPEN, (1, 1)),
        _state("closed", TotalizedStatus.CLOSED, (0, 0)),
        _state("sink", TotalizedStatus.SINK, (0, 0)),
    )
    # Locator order intentionally opposes semantic payload order.
    actions = (
        _action("semantic-z", action_id=SEMANTIC_Z_ID),
        _action("semantic-a", action_id=SEMANTIC_A_ID),
    )

    def delayed_row(source: str, action_id: str, target: str) -> SyntheticTransitionRow:
        return SyntheticTransitionRow(
            source_state_id=f"unit_cpu_survivor_{source}",
            action_id=action_id,
            target_state_id=f"unit_cpu_survivor_{target}",
            transition_semantics_digest=SEMANTICS,
        )

    rows = (
        delayed_row("u", SEMANTIC_A_ID, "m"),
        delayed_row("u", SEMANTIC_Z_ID, "m"),
        delayed_row("v", SEMANTIC_A_ID, "n"),
        delayed_row("v", SEMANTIC_Z_ID, "n"),
        delayed_row("m", SEMANTIC_A_ID, "closed"),
        delayed_row("m", SEMANTIC_Z_ID, "m"),
        delayed_row("n", SEMANTIC_A_ID, "sink"),
        delayed_row("n", SEMANTIC_Z_ID, "n"),
        delayed_row("closed", SEMANTIC_A_ID, "closed"),
        delayed_row("closed", SEMANTIC_Z_ID, "closed"),
        delayed_row("sink", SEMANTIC_A_ID, "sink"),
        delayed_row("sink", SEMANTIC_Z_ID, "sink"),
    )
    return _candidate(
        states=states,
        actions=actions,
        rows=rows,
        seeds=("unit_cpu_survivor_u", "unit_cpu_survivor_v"),
    )


def _block_index_for(certificate: ExactPartitionCertificate, state: str) -> int:
    state_id = f"unit_cpu_survivor_{state}"
    return next(
        block.block_index
        for block in certificate.final_blocks
        if state_id in block.member_state_ids
    )


def test_exact_partition_delayed_separator_semantic_word_and_roundtrip() -> None:
    admitted = admit_synthetic_finite_snapshot(_delayed_partition_candidate())
    certificate = refine_exact_partition(admitted)

    assert certificate.evidence_scope == SYNTHETIC_EVIDENCE_SCOPE
    assert certificate.canonical_action_ids == (SEMANTIC_A_ID, SEMANTIC_Z_ID)
    assert [stage.changed_from_previous for stage in certificate.refinement_trace] == [
        False,
        True,
        True,
    ]
    assert certificate.strict_refinement_passes == 2
    assert certificate.fixed_point_passes == 1
    assert len(certificate.quotient_rows) == (
        len(certificate.final_blocks) * len(certificate.canonical_action_ids)
    )
    assert certificate.work_counters.total_units <= MAX_EXACT_PARTITION_WORK_UNITS

    p0_members = {
        frozenset(block.member_state_ids)
        for block in certificate.refinement_trace[0].blocks
    }
    assert frozenset(
        {"unit_cpu_survivor_u", "unit_cpu_survivor_v"}
    ) in p0_members
    assert frozenset(
        {"unit_cpu_survivor_m", "unit_cpu_survivor_n"}
    ) in p0_members

    u_pair = tuple(
        sorted((_block_index_for(certificate, "u"), _block_index_for(certificate, "v")))
    )
    m_pair = tuple(
        sorted((_block_index_for(certificate, "m"), _block_index_for(certificate, "n")))
    )
    words = {
        (witness.left_block_index, witness.right_block_index): witness.action_ids
        for witness in certificate.distinguishing_witnesses
    }
    assert words[u_pair] == (SEMANTIC_A_ID, SEMANTIC_A_ID)
    assert words[m_pair] == (SEMANTIC_A_ID,)
    terminal_pair = tuple(
        sorted(
            (
                _block_index_for(certificate, "closed"),
                _block_index_for(certificate, "sink"),
            )
        )
    )
    assert words[terminal_pair] == ()

    assert ExactPartitionCertificate.from_dict(certificate.to_dict()) == certificate
    verified = verify_exact_partition(admitted, certificate)
    assert verified.admitted is admitted
    assert verified.verification_report.checks == EXACT_PARTITION_VERIFICATION_CHECKS
    assert verified.verification_report.final_block_count == len(
        certificate.final_blocks
    )
    assert "admitted" not in verified.to_dict()
    assert VerifiedExactPartition.from_dict(verified.to_dict(), admitted) == verified


def test_independent_partition_verifier_rejects_stable_and_witness_tampering() -> None:
    admitted = admit_synthetic_finite_snapshot(_delayed_partition_candidate())
    certificate = refine_exact_partition(admitted)
    block_count = len(certificate.final_blocks)

    bad_binding = replace(certificate, domain_payload_digest="00" * 32)
    with pytest.raises(StrictContractError, match="source binding"):
        verify_exact_partition(admitted, bad_binding)

    quotient_rows = list(certificate.quotient_rows)
    quotient_rows[0] = replace(
        quotient_rows[0],
        target_block_index=(quotient_rows[0].target_block_index + 1) % block_count,
    )
    bad_quotient = replace(certificate, quotient_rows=tuple(quotient_rows))
    with pytest.raises(StrictContractError, match="quotient"):
        verify_exact_partition(admitted, bad_quotient)

    u_pair = tuple(
        sorted((_block_index_for(certificate, "u"), _block_index_for(certificate, "v")))
    )
    witnesses = list(certificate.distinguishing_witnesses)
    witness_index = next(
        index
        for index, witness in enumerate(witnesses)
        if (witness.left_block_index, witness.right_block_index) == u_pair
    )
    witnesses[witness_index] = replace(
        witnesses[witness_index], action_ids=(SEMANTIC_Z_ID, SEMANTIC_A_ID)
    )
    bad_word = replace(certificate, distinguishing_witnesses=tuple(witnesses))
    with pytest.raises(StrictContractError, match="shortest semantic-action-lexicographic"):
        verify_exact_partition(admitted, bad_word)

    identity_p0 = replace(
        certificate.refinement_trace[0], blocks=certificate.final_blocks
    )
    stable_but_not_coarsest = replace(
        certificate, refinement_trace=(identity_p0,)
    )
    with pytest.raises(StrictContractError, match="P0"):
        verify_exact_partition(admitted, stable_but_not_coarsest)


def test_partition_resource_and_public_type_boundaries_fail_closed() -> None:
    states, actions, rows = _parts()
    huge_state = replace(
        states[0],
        payload=CanonicalPayload.from_value(
            {"kind": "state", "name": "x" * MAX_EXACT_PARTITION_WORK_UNITS}
        ),
    )
    admitted_huge = admit_synthetic_finite_snapshot(
        _candidate(states=(huge_state, *states[1:]), actions=actions, rows=rows)
    )
    with pytest.raises(StrictContractError, match="CPU_SURVIVOR_PREREQUISITE_BLOCKED"):
        refine_exact_partition(admitted_huge)

    admitted = admit_synthetic_finite_snapshot(_delayed_partition_candidate())
    certificate = refine_exact_partition(admitted)
    forged = ExactPartitionCertificate.from_dict(certificate.to_dict())
    long_word = ExactDistinguishingWitness(
        0, 1, (certificate.canonical_action_ids[0],) * 127
    )
    object.__setattr__(forged, "distinguishing_witnesses", (long_word,) * 2_000)
    with pytest.raises(StrictContractError, match="CPU_SURVIVOR_PREREQUISITE_BLOCKED"):
        verify_exact_partition(admitted, forged)

    class EvilBlock(ExactPartitionBlock):
        pass

    class EvilCertificate(ExactPartitionCertificate):
        pass

    with pytest.raises(StrictContractError, match="subclasses are forbidden"):
        EvilBlock(0, ("unit_cpu_survivor_x",))
    with pytest.raises(StrictContractError, match="polymorphic"):
        EvilCertificate.from_dict(certificate.to_dict())

    evil_schema = certificate.final_blocks[0].to_dict()

    class EvilString(str):
        pass

    evil_schema["schema_version"] = EvilString(evil_schema["schema_version"])
    with pytest.raises(StrictContractError, match="exact literal"):
        ExactPartitionBlock.from_dict(evil_schema)
