from __future__ import annotations

import copy
from dataclasses import replace
import inspect
import os

import pytest

import lean_rgc.odlrq.componentwise_window as componentwise_module
import lean_rgc.odlrq as odlrq_package
from lean_rgc.odlrq.adapters import (
    admit_synthetic_finite_snapshot,
    build_synthetic_finite_snapshot,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
)
from lean_rgc.odlrq.componentwise_window import (
    CONTINUATION_HORIZON,
    DEBT_COORDINATE_NAMES,
    D_START,
    ComponentwiseTaskSeed,
    ComponentwiseWindowReport,
    analyze_componentwise_window,
)
from lean_rgc.odlrq.contracts import (
    NOT_APPLICABLE,
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    canonical_contract_bytes,
)


ENVIRONMENT_DIGEST = "71" * 32
PLACEHOLDER_FRAME_DIGEST = "72" * 32
PLACEHOLDER_SEMANTICS_DIGEST = "73" * 32
PREFIX = "unit_cpu_survivor_window_"
ZERO_DEBT = (0, 0, 0, 0, 0)


def _id(name: str) -> str:
    return f"{PREFIX}{name}"


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value(
        {"fixture": "componentwise_window", "kind": kind, "name": name}
    )


def _state(
    name: str,
    kind: TotalizedStatus,
    debt: tuple[int | ExactRational, ...],
) -> SyntheticTotalizedState:
    return SyntheticTotalizedState(
        state_id=_id(name),
        payload=_payload("state", name),
        totalized_kind=kind,
        response_coordinates=tuple(
            value if type(value) is ExactRational else ExactRational(value)
            for value in debt
        ),
        frame_digest=PLACEHOLDER_FRAME_DIGEST,
    )


def _action(name: str) -> SyntheticAction:
    return SyntheticAction(
        action_id=_id(name),
        payload=_payload("action", name),
    )


def _row(source: str, action: str, target: str) -> SyntheticTransitionRow:
    return SyntheticTransitionRow(
        source_state_id=_id(source),
        action_id=_id(action),
        target_state_id=_id(target),
        transition_semantics_digest=PLACEHOLDER_SEMANTICS_DIGEST,
    )


def _admitted(
    *,
    open_debts: dict[str, tuple[int | ExactRational, ...]],
    action_names: tuple[str, ...],
    edges: dict[tuple[str, str], str],
    snapshot_seeds: tuple[str, ...],
    coordinate_names: tuple[str, ...] = DEBT_COORDINATE_NAMES,
    action_payload_names: dict[str, str] | None = None,
    reverse_source: bool = False,
) -> AdmittedExactFiniteSnapshot:
    """Build a source-embedded, gate-admitted exact total transition table.

    Unspecified OPEN rows enter SINK.  CLOSED and SINK rows are filled with
    their mandatory absorbing transitions.  Callers therefore spell only the
    graph edges material to the diagnostic under test.
    """

    states = tuple(
        _state(name, TotalizedStatus.OPEN, debt)
        for name, debt in open_debts.items()
    ) + (
        _state("closed", TotalizedStatus.CLOSED, (0,) * len(coordinate_names)),
        _state("sink", TotalizedStatus.SINK, (0,) * len(coordinate_names)),
    )
    actions = tuple(
        SyntheticAction(
            action_id=_id(name),
            payload=_payload(
                "action",
                name if action_payload_names is None else action_payload_names[name],
            ),
        )
        for name in action_names
    )
    rows = tuple(
        _row(
            source,
            action,
            (
                source
                if source in {"closed", "sink"}
                else edges.get((source, action), "sink")
            ),
        )
        for source in (*open_debts, "closed", "sink")
        for action in action_names
    )

    vocabulary = ResponseVocabularyId.from_coordinate_names(coordinate_names)
    frame = make_synthetic_observation_frame_id(
        environment_digest=ENVIRONMENT_DIGEST,
        response_vocabulary_id=vocabulary,
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=actions,
        response_vocabulary_id=vocabulary,
    )
    states = tuple(
        replace(state, frame_digest=observation_frame_digest(frame))
        for state in states
    )
    rows = tuple(
        replace(row, transition_semantics_digest=semantics.semantics_digest)
        for row in rows
    )
    if reverse_source:
        states = tuple(reversed(states))
        actions = tuple(reversed(actions))
        rows = tuple(reversed(rows))

    snapshot = build_synthetic_finite_snapshot(
        environment_digest=ENVIRONMENT_DIGEST,
        coordinate_names=coordinate_names,
        seed_state_ids=tuple(_id(name) for name in snapshot_seeds),
        states=states,
        actions=actions,
        transitions=rows,
    )
    return admit_synthetic_finite_snapshot(snapshot)


def _seed(task: str, state: str) -> ComponentwiseTaskSeed:
    return ComponentwiseTaskSeed(_id(task), _id(state))


def _qvector(*values: int) -> list[dict[str, object]]:
    return [ExactRational(value).to_dict() for value in values]


def _expand_then_contract(
    *, reverse_source: bool = False
) -> tuple[AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]]:
    admitted = _admitted(
        open_debts={
            "start": (5, 5, 5, 5, 5),
            "peak": (8, 5, 5, 5, 5),
            "contracted": (4, 5, 5, 5, 5),
        },
        action_names=("advance",),
        edges={
            ("start", "advance"): "peak",
            ("peak", "advance"): "contracted",
            ("contracted", "advance"): "closed",
        },
        snapshot_seeds=("start",),
        reverse_source=reverse_source,
    )
    return admitted, (_seed("task_expand", "start"),)


def _mixed_good_and_bad(
    *, reverse_source: bool = False
) -> tuple[AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]]:
    admitted = _admitted(
        open_debts={
            "start": (5, 5, 5, 5, 5),
            "good": (4, 5, 5, 5, 5),
            "bad": (12, 5, 5, 5, 5),
        },
        action_names=("bad_step", "finish", "good_step"),
        edges={
            ("start", "bad_step"): "bad",
            ("start", "good_step"): "good",
            ("bad", "finish"): "closed",
            ("good", "finish"): "closed",
        },
        snapshot_seeds=("start",),
        reverse_source=reverse_source,
    )
    return admitted, (_seed("task_mixed", "start"),)


def _many_words_one_state(
    *, reverse_source: bool = False
) -> tuple[AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]]:
    admitted = _admitted(
        open_debts={"loop": (5, 5, 5, 5, 5)},
        action_names=("finish", "loop_a", "loop_b"),
        edges={
            ("loop", "finish"): "closed",
            ("loop", "loop_a"): "loop",
            ("loop", "loop_b"): "loop",
        },
        snapshot_seeds=("loop",),
        reverse_source=reverse_source,
    )
    return admitted, (_seed("task_alias", "loop"),)


def _immediate_terminal() -> tuple[
    AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]
]:
    admitted = _admitted(
        open_debts={"start": (5, 5, 5, 5, 5)},
        action_names=("finish",),
        edges={("start", "finish"): "closed"},
        snapshot_seeds=("start",),
    )
    return admitted, (_seed("task_immediate", "start"),)


def _beyond_horizon() -> tuple[
    AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]
]:
    # The first strict decrease is the fourth open step, but closure needs a
    # fifth action.  A length-K OPEN endpoint has CanClose_0=False, so the
    # starting occurrence must remain in the K+1 unresolved bin.
    admitted = _admitted(
        open_debts={
            "s0": (5, 5, 5, 5, 5),
            "s1": (5, 5, 5, 5, 5),
            "s2": (5, 5, 5, 5, 5),
            "s3": (5, 5, 5, 5, 5),
            "s4": (4, 5, 5, 5, 5),
        },
        action_names=("advance",),
        edges={
            ("s0", "advance"): "s1",
            ("s1", "advance"): "s2",
            ("s2", "advance"): "s3",
            ("s3", "advance"): "s4",
            ("s4", "advance"): "closed",
        },
        snapshot_seeds=("s0",),
    )
    return admitted, (_seed("task_beyond", "s0"),)


def _sixteen_action_cap_fixture() -> tuple[
    AdmittedExactFiniteSnapshot, tuple[ComponentwiseTaskSeed, ...]
]:
    actions = tuple(f"a{index:02d}" for index in range(16))
    admitted = _admitted(
        open_debts={"start": (5, 5, 5, 5, 5)},
        action_names=actions,
        edges={("start", action): "closed" for action in actions},
        snapshot_seeds=("start",),
    )
    # With A=16, one seed has 69,905 start words through D_start.  Two seeds
    # have S=139,810, over the frozen 100,000 occurrence cap.  The analyzer
    # must reject from integer arithmetic before opening a word population.
    return admitted, (
        _seed("task_cap_a", "start"),
        _seed("task_cap_b", "start"),
    )


# Frozen kill-test inventory below is intentionally one semantic case per
# test: expand/contract overshoot; existential versus universal populations;
# occurrence versus immutable-state denominators; immediate terminal
# nonmanufacture; equality without strict decrease; K+1 unresolved; inclusion
# of noncontracting overshoot; permutation canonicality; coordinate mismatch;
# post-admission censor/oracle mutation; pre-materialization caps; and strict,
# source-bound report/seed deserialization.


def test_frozen_constants_and_debt_coordinate_order_are_exact() -> None:
    assert D_START == 4
    assert CONTINUATION_HORIZON == 4
    assert DEBT_COORDINATE_NAMES == (
        "open_goal_count",
        "open_unassigned_mvar_count",
        "pending_typeclass_count",
        "carrier_atom_count",
        "expression_node_count",
    )


def test_task_seed_is_strict_canonical_and_nonpolymorphic() -> None:
    seed = _seed("task_seed", "start")
    wire = seed.to_dict()
    assert ComponentwiseTaskSeed.from_dict(copy.deepcopy(wire)) == seed
    assert canonical_contract_bytes(ComponentwiseTaskSeed.from_dict(wire)) == (
        canonical_contract_bytes(seed)
    )

    unknown = copy.deepcopy(wire)
    unknown["unknown"] = "forbidden"
    with pytest.raises(StrictContractError, match="field|unknown"):
        ComponentwiseTaskSeed.from_dict(unknown)

    wrong_schema = copy.deepcopy(wire)
    wrong_schema["schema_version"] = "wrong"
    with pytest.raises(StrictContractError, match="schema"):
        ComponentwiseTaskSeed.from_dict(wrong_schema)

    wrong_type = copy.deepcopy(wire)
    wrong_type["task_id"] = True
    with pytest.raises(StrictContractError, match="task_id|string"):
        ComponentwiseTaskSeed.from_dict(wrong_type)

    with pytest.raises(StrictContractError, match="strict UTF-8"):
        ComponentwiseTaskSeed(f"{PREFIX}\ud800", _id("start"))
    non_utf8 = copy.deepcopy(wire)
    non_utf8["state_id"] = f"{PREFIX}\ud800"
    with pytest.raises(StrictContractError, match="strict UTF-8"):
        ComponentwiseTaskSeed.from_dict(non_utf8)

    class TaskSeedSubclass(ComponentwiseTaskSeed):
        pass

    with pytest.raises(StrictContractError, match="subclass"):
        TaskSeedSubclass(_id("task_seed"), _id("start"))
    with pytest.raises(StrictContractError, match="polymorphic"):
        TaskSeedSubclass.from_dict(wire)

    with pytest.raises(StrictContractError, match="UTF-8"):
        ComponentwiseTaskSeed(
            f"{PREFIX}\ud800",
            _id("start"),
        )
    surrogate_wire = copy.deepcopy(wire)
    surrogate_wire["state_id"] = f"{PREFIX}\udfff"
    with pytest.raises(StrictContractError, match="UTF-8"):
        ComponentwiseTaskSeed.from_dict(surrogate_wire)


def test_raw_caps_fire_before_after_preflight_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admitted, seeds = _sixteen_action_cap_fixture()

    def forbidden_after_preflight(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("post-preflight materialization was entered")

    monkeypatch.setattr(
        componentwise_module,
        "_derive_report_after_preflight",
        forbidden_after_preflight,
    )
    with pytest.raises(
        StrictContractError,
        match=r"PREREQUISITE_BLOCKED.*S=139810.*100000",
    ):
        analyze_componentwise_window(admitted, seeds)


def _wire(
    admitted: AdmittedExactFiniteSnapshot,
    seeds: tuple[ComponentwiseTaskSeed, ...],
) -> tuple[ComponentwiseWindowReport, dict[str, object]]:
    report = analyze_componentwise_window(admitted, seeds)
    return report, report.to_dict()


def _state_index(wire: dict[str, object], name: str) -> int:
    rows = wire["state_dictionary"]
    assert type(rows) is list
    row = next(
        item
        for item in rows
        if type(item) is dict and item["state_id"] == _id(name)
    )
    index = row["state_index"]
    assert type(index) is int
    return index


def _state_summary(wire: dict[str, object], name: str) -> dict[str, object]:
    state_index = _state_index(wire, name)
    rows = wire["state_summaries"]
    assert type(rows) is list
    return next(
        item
        for item in rows
        if type(item) is dict and item["state_index"] == state_index
    )


def _continuations(wire: dict[str, object], name: str) -> list[dict[str, object]]:
    state_index = _state_index(wire, name)
    rows = wire["registered_continuations"]
    assert type(rows) is list
    return [
        item
        for item in rows
        if type(item) is dict and item["state_index"] == state_index
    ]


def _action_index(wire: dict[str, object], name: str) -> int:
    rows = wire["action_dictionary"]
    assert type(rows) is list
    row = next(
        item
        for item in rows
        if type(item) is dict and item["action_id"] == _id(name)
    )
    index = row["action_index"]
    assert type(index) is int
    return index


def test_expand_then_contract_retains_intermediate_peak_and_strict_window() -> None:
    admitted, seeds = _expand_then_contract()
    report, wire = _wire(admitted, seeds)

    assert report.coordinate_names == DEBT_COORDINATE_NAMES
    assert report.canonical_report_bytes == len(canonical_contract_bytes(wire))
    assert wire["canonical_report_bytes"] == report.canonical_report_bytes
    assert wire["coordinate_api"] == {
        "schema_version": "lean-rgc-odlrq-componentwise-coordinate-api-v1",
        "coordinate_names": list(DEBT_COORDINATE_NAMES),
        "vector_length": 5,
        "value_domain": "nonnegative_exact_integer",
        "wire_encoding": "exact_rational_denominator_one",
        "contraction_rule": "coordinatewise_nonincrease_and_at_least_one_strict",
        "overshoot_rule": "maximum_positive_increase_over_all_open_prefixes_from_start",
    }
    assert set(wire) == {
        "schema_version",
        "evidence_scope",
        "diagnostic_tier",
        "qualification",
        "scientific_disposition",
        "snapshot_sha256",
        "task_seed_set_sha256",
        "source_binding",
        "coordinate_api",
        "d_start",
        "continuation_horizon",
        "resource_preflight",
        "task_dictionary",
        "action_dictionary",
        "state_dictionary",
        "can_close_layers",
        "registered_continuations",
        "state_summaries",
        "occurrences",
        "occurrence_population",
        "unique_state_population",
        "per_task_populations",
        "canonical_report_bytes",
    }

    preflight = wire["resource_preflight"]
    assert type(preflight) is dict
    assert {
        key: preflight[key]
        for key in (
            "task_count",
            "action_count",
            "raw_start_occurrences",
            "raw_continuation_pairs",
            "transition_work_units",
        )
    } == {
        "task_count": 1,
        "action_count": 1,
        "raw_start_occurrences": 5,
        "raw_continuation_pairs": 20,
        "transition_work_units": 100,
    }

    start = _state_summary(wire, "start")
    assert start == {
        "state_index": _state_index(wire, "start"),
        "occurrence_count": 1,
        "task_count": 1,
        "start_coordinates": _qvector(5, 5, 5, 5, 5),
        "continuation_count": 2,
        "contractive_count": 1,
        "minimum_resolving_window": 2,
        "resolved": True,
        "existential_contracts": True,
        "universal_status": "has_noncontracting",
        "maximum_overshoot_coordinates": _qvector(3, 0, 0, 0, 0),
    }
    rows = _continuations(wire, "start")
    assert [len(row["action_word"]) for row in rows] == [1, 2]  # type: ignore[arg-type]
    assert rows[0]["contracts"] is False
    assert rows[0]["overshoot_coordinates"] == _qvector(3, 0, 0, 0, 0)
    assert rows[1]["contracts"] is True
    assert rows[1]["endpoint_coordinates"] == _qvector(4, 5, 5, 5, 5)
    assert rows[1]["peak_coordinates"] == _qvector(8, 5, 5, 5, 5)
    assert rows[1]["overshoot_coordinates"] == _qvector(3, 0, 0, 0, 0)
    assert _state_summary(wire, "peak")["universal_status"] == "all_contracts"

    occurrence = wire["occurrence_population"]
    assert type(occurrence) is dict
    assert occurrence["start_count"] == 3
    assert occurrence["registered_continuation_count"] == 3
    assert occurrence["contractive_continuation_count"] == 2
    assert occurrence["minimum_resolving_window_histogram"] == [1, 1, 0, 0, 1]
    assert occurrence["population_maximum_overshoot_coordinates"] == _qvector(
        3, 0, 0, 0, 0
    )
    assert wire["scientific_disposition"] == "U05_KP2_EVENTUAL_WINDOW"


def test_good_and_bad_continuations_separate_existential_from_universal() -> None:
    admitted, seeds = _mixed_good_and_bad()
    _, wire = _wire(admitted, seeds)

    start = _state_summary(wire, "start")
    assert start["continuation_count"] == 2
    assert start["contractive_count"] == 1
    assert start["minimum_resolving_window"] == 1
    assert start["existential_contracts"] is True
    assert start["universal_status"] == "has_noncontracting"

    by_word = {
        tuple(row["action_word"]): row  # type: ignore[arg-type]
        for row in _continuations(wire, "start")
    }
    good = by_word[(_action_index(wire, "good_step"),)]
    bad = by_word[(_action_index(wire, "bad_step"),)]
    assert good["contracts"] is True
    assert good["overshoot_coordinates"] == _qvector(*ZERO_DEBT)
    assert bad["contracts"] is False
    assert bad["overshoot_coordinates"] == _qvector(7, 0, 0, 0, 0)

    for population_name in ("occurrence_population", "unique_state_population"):
        population = wire[population_name]
        assert type(population) is dict
        assert population["start_count"] == 3
        assert population["nonempty_start_count"] == 1
        assert population["empty_start_count"] == 2
        assert population["registered_continuation_count"] == 2
        assert population["contractive_continuation_count"] == 1
        assert population["existential_numerator"] == 1
        assert population["existential_denominator"] == 3
        assert population["universal_numerator"] == 0
        assert population["universal_denominator"] == 1
        # The only positive overshoot belongs to the bad, noncontracting row.
        assert population["population_maximum_overshoot_coordinates"] == _qvector(
            7, 0, 0, 0, 0
        )


def test_many_words_to_one_state_keep_occurrence_and_state_denominators() -> None:
    admitted, seeds = _many_words_one_state()
    _, wire = _wire(admitted, seeds)

    summary = _state_summary(wire, "loop")
    assert summary["occurrence_count"] == 31
    assert summary["task_count"] == 1
    assert summary["continuation_count"] == 14
    assert summary["contractive_count"] == 0
    assert summary["minimum_resolving_window"] == CONTINUATION_HORIZON + 1
    assert summary["resolved"] is False
    assert summary["existential_contracts"] is False
    assert summary["universal_status"] == "has_noncontracting"

    rows = _continuations(wire, "loop")
    assert len(rows) == 14
    assert sum(len(row["action_word"]) == 1 for row in rows) == 2  # type: ignore[arg-type]
    assert sum(len(row["action_word"]) == 2 for row in rows) == 4  # type: ignore[arg-type]
    assert sum(len(row["action_word"]) == 3 for row in rows) == 8  # type: ignore[arg-type]
    assert not any(len(row["action_word"]) == 4 for row in rows)  # type: ignore[arg-type]
    assert all(row["contracts"] is False for row in rows)

    occurrence = wire["occurrence_population"]
    unique = wire["unique_state_population"]
    assert type(occurrence) is dict and type(unique) is dict
    assert (occurrence["start_count"], unique["start_count"]) == (31, 1)
    assert (
        occurrence["registered_continuation_count"],
        unique["registered_continuation_count"],
    ) == (434, 14)
    assert (
        occurrence["existential_denominator"],
        unique["existential_denominator"],
    ) == (31, 1)
    assert (
        occurrence["universal_denominator"],
        unique["universal_denominator"],
    ) == (31, 1)
    assert occurrence["minimum_resolving_window_histogram"] == [0, 0, 0, 0, 31]
    assert unique["minimum_resolving_window_histogram"] == [0, 0, 0, 0, 1]
    assert wire["scientific_disposition"] == (
        "U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT"
    )

    per_task = wire["per_task_populations"]
    assert type(per_task) is list and len(per_task) == 1
    task_occurrence = per_task[0]["occurrence_population"]  # type: ignore[index]
    task_unique = per_task[0]["unique_state_population"]  # type: ignore[index]
    assert task_occurrence == {
        **occurrence,
        "population_kind": "task_occurrence",
    }
    assert task_unique == {
        **unique,
        "population_kind": "task_unique_state",
    }


def test_immediate_terminal_closure_cannot_manufacture_open_block() -> None:
    admitted, seeds = _immediate_terminal()
    _, wire = _wire(admitted, seeds)

    assert len(wire["occurrences"]) == 1  # type: ignore[arg-type]
    assert wire["registered_continuations"] == []
    summary = _state_summary(wire, "start")
    assert summary["continuation_count"] == 0
    assert summary["contractive_count"] == 0
    assert summary["existential_contracts"] is False
    assert summary["universal_status"] == "not_applicable_empty"
    assert summary["minimum_resolving_window"] == CONTINUATION_HORIZON + 1

    population = wire["occurrence_population"]
    assert type(population) is dict
    assert population["start_count"] == 1
    assert population["nonempty_start_count"] == 0
    assert population["empty_start_count"] == 1
    assert population["universal_numerator"] == 0
    assert population["universal_denominator"] == 0
    assert population["minimum_resolving_window_histogram"] == [0, 0, 0, 0, 1]
    assert wire["scientific_disposition"] == "U05_KP2_FRAGMENT_INCONCLUSIVE"


def test_k_plus_one_bin_means_unresolved_not_length_k_registration() -> None:
    admitted, seeds = _beyond_horizon()
    _, wire = _wire(admitted, seeds)

    start = _state_summary(wire, "s0")
    assert start["continuation_count"] == 0
    assert start["contractive_count"] == 0
    assert start["resolved"] is False
    assert start["universal_status"] == "not_applicable_empty"
    assert start["minimum_resolving_window"] == CONTINUATION_HORIZON + 1
    assert _continuations(wire, "s0") == []
    # CanClose_4 excludes s0: its strict open endpoint is four actions away,
    # but that endpoint still needs the fifth, terminal-closing action.
    layers = wire["can_close_layers"]
    assert type(layers) is list
    assert _state_index(wire, "s0") not in layers[CONTINUATION_HORIZON][  # type: ignore[index]
        "closable_open_state_indices"
    ]


def test_source_and_action_permutations_have_identical_canonical_report() -> None:
    left_admitted, left_seeds = _mixed_good_and_bad()
    right_admitted, right_seeds = _mixed_good_and_bad(reverse_source=True)

    left = analyze_componentwise_window(left_admitted, left_seeds).to_dict()
    right = analyze_componentwise_window(right_admitted, right_seeds).to_dict()
    assert left_admitted == right_admitted
    assert canonical_contract_bytes(left) == canonical_contract_bytes(right)


def test_task_seed_permutation_has_identical_canonical_report() -> None:
    admitted, _ = _expand_then_contract()
    left_seeds = (
        _seed("task_z", "start"),
        _seed("task_a", "start"),
    )
    right_seeds = tuple(reversed(left_seeds))

    left = analyze_componentwise_window(admitted, left_seeds).to_dict()
    right = analyze_componentwise_window(admitted, right_seeds).to_dict()
    assert canonical_contract_bytes(left) == canonical_contract_bytes(right)
    task_rows = left["task_dictionary"]
    assert [row["task_id"] for row in task_rows] == [  # type: ignore[index]
        _id("task_a"),
        _id("task_z"),
    ]


def test_action_order_is_payload_semantic_and_words_keep_boundaries() -> None:
    admitted = _admitted(
        open_debts={
            "start": (5, 5, 5, 5, 5),
            "x": (5, 5, 5, 5, 5),
            "y": (5, 5, 5, 5, 5),
            "z": (5, 5, 5, 5, 5),
            "g": (4, 5, 5, 5, 5),
            "h": (6, 5, 5, 5, 5),
        },
        action_names=("a", "b", "ab"),
        action_payload_names={"a": "z_payload", "b": "a_payload", "ab": "m_payload"},
        edges={
            ("start", "a"): "x",
            ("x", "b"): "g",
            ("g", "a"): "closed",
            ("start", "b"): "y",
            ("y", "a"): "h",
            ("h", "b"): "closed",
            ("start", "ab"): "z",
            ("z", "a"): "closed",
        },
        snapshot_seeds=("start",),
    )
    _, wire = _wire(admitted, (_seed("task_words", "start"),))
    action_rows = wire["action_dictionary"]
    assert [row["action_id"].removeprefix(PREFIX) for row in action_rows] == [
        "b",
        "ab",
        "a",
    ]
    action_names = {
        row["action_index"]: row["action_id"].removeprefix(PREFIX)
        for row in action_rows
    }
    words = {
        tuple(action_names[index] for index in row["action_word"])
        for row in _continuations(wire, "start")
    }
    assert ("a", "b") in words
    assert ("b", "a") in words
    assert ("ab",) in words
    assert ("a", "b") != ("ab",)


@pytest.mark.parametrize(
    ("coordinate_names", "debt"),
    (
        (tuple(reversed(DEBT_COORDINATE_NAMES)), (5, 5, 5, 5, 5)),
        (DEBT_COORDINATE_NAMES[:-1], (5, 5, 5, 5)),
    ),
)
def test_coordinate_api_mismatch_and_silent_truncation_are_rejected(
    coordinate_names: tuple[str, ...],
    debt: tuple[int, ...],
) -> None:
    admitted = _admitted(
        open_debts={"start": debt},
        action_names=("finish",),
        edges={("start", "finish"): "closed"},
        snapshot_seeds=("start",),
        coordinate_names=coordinate_names,
    )
    with pytest.raises(StrictContractError, match="exact frozen five-coordinate API"):
        analyze_componentwise_window(admitted, (_seed("task_coordinates", "start"),))


def test_fractional_debt_cannot_broaden_the_frozen_count_domain() -> None:
    admitted = _admitted(
        open_debts={
            "start": (ExactRational(1, 2), 5, 5, 5, 5),
        },
        action_names=("finish",),
        edges={("start", "finish"): "closed"},
        snapshot_seeds=("start",),
    )
    with pytest.raises(StrictContractError, match="nonnegative exact integers"):
        analyze_componentwise_window(admitted, (_seed("task_fraction", "start"),))


@pytest.mark.parametrize("mutation", ("censor", "oracle", "coordinate_arity"))
def test_post_admission_censor_and_non_not_applicable_oracle_mutations_fail_closed(
    mutation: str,
) -> None:
    admitted, seeds = _immediate_terminal()
    if mutation == "censor":
        row = next(
            row
            for row in admitted.snapshot.transitions
            if row.source_state_id == _id("start")
        )
        object.__setattr__(row, "censor", "MUTATED_CENSOR")
        assert row.censor != NOT_APPLICABLE
    elif mutation == "oracle":
        object.__setattr__(admitted.snapshot.evidence_profile, "delta", "MUTATED_ORACLE")
        assert admitted.snapshot.evidence_profile.delta != NOT_APPLICABLE
    else:
        state = next(
            state
            for state in admitted.snapshot.states
            if state.state_id == _id("start")
        )
        object.__setattr__(state, "response_coordinates", state.response_coordinates[:-1])
        assert len(state.response_coordinates) == 4

    with pytest.raises(StrictContractError, match="malformed|censor|NOT_APPLICABLE"):
        analyze_componentwise_window(admitted, seeds)


def test_near_exact_integer_cap_roundtrips_with_one_action() -> None:
    huge_count = 1 << 8191
    admitted = _admitted(
        open_debts={
            "start": (ExactRational(huge_count), 5, 5, 5, 5),
        },
        action_names=("finish",),
        edges={("start", "finish"): "closed"},
        snapshot_seeds=("start",),
    )
    seeds = (_seed("task_large_roundtrip", "start"),)
    report, wire = _wire(admitted, seeds)

    expected = _qvector(huge_count, 5, 5, 5, 5)
    assert _state_summary(wire, "start")["start_coordinates"] == expected
    state_rows = wire["state_dictionary"]
    assert type(state_rows) is list
    state_row = next(row for row in state_rows if row["state_id"] == _id("start"))
    assert state_row["coordinates"] == expected
    preflight = wire["resource_preflight"]
    assert type(preflight) is dict
    assert preflight["conservative_report_upper_bound"] <= preflight["report_byte_cap"]
    assert ComponentwiseWindowReport.from_dict(wire, admitted, seeds).to_dict() == (
        report.to_dict()
    )


def test_near_exact_integer_cap_fails_report_preflight_before_words(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    huge = ExactRational(1 << 8191)
    admitted = _admitted(
        open_debts={"start": (huge, 5, 5, 5, 5)},
        action_names=("finish_a", "finish_b", "finish_c"),
        edges={
            ("start", action): "closed"
            for action in ("finish_a", "finish_b", "finish_c")
        },
        snapshot_seeds=("start",),
    )

    def forbidden_word_materialization(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("word materialization was entered")

    monkeypatch.setattr(
        componentwise_module,
        "_enumerate_open_occurrences",
        forbidden_word_materialization,
    )
    with pytest.raises(
        StrictContractError,
        match=r"PREREQUISITE_BLOCKED.*report upper bound.*67108864",
    ):
        analyze_componentwise_window(
            admitted,
            (_seed("task_large_coordinate", "start"),),
        )


def test_report_roundtrip_is_strict_nonpolymorphic_and_authority_bound() -> None:
    admitted, seeds = _expand_then_contract()
    report, wire = _wire(admitted, seeds)
    restored = ComponentwiseWindowReport.from_dict(
        copy.deepcopy(wire), admitted, seeds
    )
    assert restored.to_dict() == wire
    assert restored.coordinate_names == DEBT_COORDINATE_NAMES

    unknown = copy.deepcopy(wire)
    unknown["unknown"] = "forbidden"
    with pytest.raises(StrictContractError, match="does not match"):
        ComponentwiseWindowReport.from_dict(unknown, admitted, seeds)

    mutated = copy.deepcopy(wire)
    mutated["resource_preflight"]["task_count"] = 99
    with pytest.raises(StrictContractError, match="does not match"):
        ComponentwiseWindowReport.from_dict(mutated, admitted, seeds)

    other_admitted, _ = _immediate_terminal()
    with pytest.raises(StrictContractError, match="does not match"):
        ComponentwiseWindowReport.from_dict(wire, other_admitted, seeds)

    class ReportSubclass(ComponentwiseWindowReport):
        pass

    with pytest.raises(StrictContractError, match="polymorphic"):
        ReportSubclass.from_dict(wire, admitted, seeds)
    with pytest.raises(StrictContractError, match="analysis gate"):
        ComponentwiseWindowReport(admitted, seeds, "A" * 64, "B" * 64)

    # Returned wires are detached derivations, not mutable report storage.
    detached = report.to_dict()
    detached["scientific_disposition"] = "MUTATED"
    assert report.to_dict() == wire


def test_sealed_report_detects_retained_snapshot_and_task_seed_mutation() -> None:
    admitted, seeds = _expand_then_contract()
    report = analyze_componentwise_window(admitted, seeds)
    row = next(
        row
        for row in admitted.snapshot.transitions
        if row.source_state_id == _id("start")
    )
    object.__setattr__(row, "censor", "MUTATED_AFTER_ANALYSIS")
    with pytest.raises(StrictContractError, match="malformed|censor"):
        report.to_dict()

    admitted, seeds = _expand_then_contract()
    report = analyze_componentwise_window(admitted, seeds)
    object.__setattr__(seeds[0], "task_id", _id("task_mutated_after_analysis"))
    with pytest.raises(StrictContractError, match="retained task seeds changed"):
        report.to_dict()


def test_componentwise_lane_has_no_hard_or_cross_lane_promotion_surface() -> None:
    source = inspect.getsource(componentwise_module)
    assert "from .quotient_generator import" not in source
    assert "from .hankel_predictive import" not in source
    forbidden = {
        "ExactFiniteOperator",
        "CertifiedIntervalOperator",
        "BoundedRationalRealization",
        "FiberEnvelope",
        "promote_to_exact",
        "promote_to_certified",
    }
    assert forbidden.isdisjoint(componentwise_module.__all__)
    assert forbidden.isdisjoint(dir(componentwise_module))
    assert set(componentwise_module.__all__) <= set(odlrq_package.__all__)


def test_runner_hides_receipt_and_denies_process_exit() -> None:
    if os.environ.get("UPRIME_WP4W_SUBPROCESS_POLICY") == "forbid":
        assert "UPRIME_WP4W_EXIT_RECEIPT" not in os.environ
        with pytest.raises(RuntimeError, match="may not spawn subprocesses"):
            os._exit(0)
