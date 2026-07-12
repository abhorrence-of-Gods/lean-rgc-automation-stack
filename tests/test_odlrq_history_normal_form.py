from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
from types import MappingProxyType

import pytest

import lean_rgc.odlrq.history_normal_form as hnf
from lean_rgc.odlrq.history_normal_form import (
    CONDITIONAL_KSTATE_MARKOV,
    MAX_ACTIONS,
    MAX_REPORT_BYTES,
    MAX_TASK_SEEDS,
    UNCONDITIONAL_FINITE_DOMAIN,
    BehavioralClassKey,
    CanonicalKStateMarkovContract,
    CanonicalHistoryChart,
    ExactOccurrenceResponse,
    ExactOpenState,
    ExactOutcomeKind,
    FiniteTotalActionDomain,
    HistoryContractError,
    HistoryGrammar,
    IndependentDomainWalker,
    SealedTransitionRow,
    TaskSeed,
    TerminalOccurrence,
    TerminalTransitionKind,
    build_batch_reference,
    build_finite_total_action_domain,
    independent_walk,
    preflight_report_bound,
    verify_flow_conservation,
    verify_generation_time_equals_batch,
    verify_raw_normalized_equality,
)


WIDE_DOMAIN_DIGEST = "AC6321FD6E20ACA8700BE715FE66F449561879BA627771CA62DC936CE3B4FA0A"
WIDE_CHART_D3_DIGEST = "A7BB224700087D177CBC1509463FA3A566342FB6099CB323F671E0D2CA5CAAB1"
WIDE_RAW_D3_DIGEST = "C119359A3A955CF789EA867D4731F1DF38B34A30E3022CF81B5078E0033BB4BA"
RICH_FLOW_DIGEST = "313237587A97C69E37F195A8A2B9B35CBD132C251E8B4F2397ED4E2A533DC57A"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest().upper()


def _state(name: str, debt: tuple[int, int, int, int, int]) -> ExactOpenState:
    return ExactOpenState(
        f"id:{name}".encode(),
        f"full:{name}".encode(),
        debt,
        f"response:{name}".encode(),
    )


def _row(
    source: ExactOpenState,
    action: str,
    target: ExactOpenState | ExactOutcomeKind,
) -> SealedTransitionRow:
    if isinstance(target, ExactOpenState):
        kind = ExactOutcomeKind.OPEN
        target_key = target.identity_key
    else:
        kind = target
        target_key = None
    return SealedTransitionRow(
        source.identity_key,
        action,
        kind,
        target_key,
        _digest(f"{source.identity_key!r}:{action}:{kind.value}:{target_key!r}"),
    )


def _rich_domain(*, reverse: bool = False) -> FiniteTotalActionDomain:
    # a;b and b;a do not commute.  g is a seven-channel no-op at one step but
    # changes the later z outcome.  Two task histories meet at m.
    s0 = _state("s0", (4, 0, 0, 0, 0))
    x = _state("x", (3, 1, 0, 0, 0))
    y = _state("y", (3, 0, 1, 0, 0))
    m = _state("m", (2, 1, 1, 0, 0))
    n = _state("n", (2, 2, 0, 0, 0))
    # Same projected response as s0, but not the same exact state/response.
    ghost = ExactOpenState(
        b"id:ghost", b"full:ghost", s0.debt, s0.response_signature
    )
    states = (s0, x, y, m, n, ghost)
    actions = ("a", "b", "g", "z")
    targets: dict[tuple[bytes, str], ExactOpenState | ExactOutcomeKind] = {
        (s0.identity_key, "a"): x,
        (s0.identity_key, "b"): y,
        (s0.identity_key, "g"): ghost,
        (s0.identity_key, "z"): ExactOutcomeKind.SINK,
        (x.identity_key, "a"): x,
        (x.identity_key, "b"): m,
        (x.identity_key, "g"): x,
        (x.identity_key, "z"): m,
        (y.identity_key, "a"): n,
        (y.identity_key, "b"): y,
        (y.identity_key, "g"): y,
        (y.identity_key, "z"): y,
        (m.identity_key, "a"): m,
        (m.identity_key, "b"): m,
        (m.identity_key, "g"): m,
        (m.identity_key, "z"): ExactOutcomeKind.CLOSED,
        (n.identity_key, "a"): n,
        (n.identity_key, "b"): n,
        (n.identity_key, "g"): n,
        (n.identity_key, "z"): ExactOutcomeKind.SINK,
        (ghost.identity_key, "a"): ghost,
        (ghost.identity_key, "b"): ghost,
        (ghost.identity_key, "g"): ghost,
        (ghost.identity_key, "z"): ExactOutcomeKind.CLOSED,
    }
    rows = tuple(
        _row(state, action, targets[(state.identity_key, action)])
        for state in states
        for action in actions
    )
    tasks = (TaskSeed("unit_kp3d4_left", s0.identity_key), TaskSeed("unit_kp3d4_right", x.identity_key))
    if reverse:
        states, actions, rows, tasks = (
            tuple(reversed(states)),
            tuple(reversed(actions)),
            tuple(reversed(rows)),
            tuple(reversed(tasks)),
        )
    return build_finite_total_action_domain(
        source_authority="unit_kp3d4_rich_v1",
        expected_source_authority="unit_kp3d4_rich_v1",
        semantics_digest=_digest("rich-semantics"),
        task_seeds=tasks,
        action_ids=actions,
        open_states=states,
        transition_rows=rows,
    )


def _wide_domain(*, reverse: bool = False) -> FiniteTotalActionDomain:
    s0 = _state("wide0", (2, 0, 0, 0, 0))
    s1 = _state("wide1", (1, 0, 0, 0, 0))
    actions = tuple(f"a{i:02d}" for i in range(12))
    rows: list[SealedTransitionRow] = []
    for state in (s0, s1):
        for action in actions:
            if state is s0 and action == "a00":
                target: ExactOpenState | ExactOutcomeKind = s1
            elif state is s0 and action == "a01":
                target = ExactOutcomeKind.CLOSED
            elif state is s1 and action == "a02":
                target = ExactOutcomeKind.SINK
            else:
                target = state
            rows.append(_row(state, action, target))
    tasks = tuple(
        TaskSeed(f"unit_kp3d4_task_{index}", (s0, s1)[index % 2].identity_key)
        for index in range(5)
    )
    states: tuple[ExactOpenState, ...] = (s0, s1)
    row_tuple = tuple(rows)
    if reverse:
        tasks, actions, states, row_tuple = (
            tuple(reversed(tasks)),
            tuple(reversed(actions)),
            tuple(reversed(states)),
            tuple(reversed(row_tuple)),
        )
    return build_finite_total_action_domain(
        source_authority="unit_kp3d4_wide_v1",
        semantics_digest=_digest("wide-semantics"),
        task_seeds=tasks,
        action_ids=actions,
        open_states=states,
        transition_rows=row_tuple,
    )


def test_domain_is_strict_immutable_total_canonical_and_json_bound() -> None:
    left = _rich_domain()
    right = _rich_domain(reverse=True)
    assert left == right
    assert left.digest == right.digest
    assert left.sealed
    assert len(left.transition_rows) == len(left.open_states) * len(left.action_ids)
    assert FiniteTotalActionDomain.from_json_bytes(
        left.to_canonical_json_bytes(),
        expected_source_authority="unit_kp3d4_rich_v1",
    ) == left
    with pytest.raises(FrozenInstanceError):
        left.source_authority = "changed"  # type: ignore[misc]

    payload = json.loads(left.to_canonical_json_bytes())
    payload["unknown"] = True
    with pytest.raises(HistoryContractError, match="field mismatch"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority="unit_kp3d4_rich_v1",
        )
    with pytest.raises(HistoryContractError, match="duplicate"):
        FiniteTotalActionDomain.from_json_bytes(
            b'{"schema_version":"x","schema_version":"y"}',
            expected_source_authority="unit_kp3d4_rich_v1",
        )
    with pytest.raises(HistoryContractError, match="UTF-8"):
        FiniteTotalActionDomain.from_json_bytes(
            b"\xff", expected_source_authority="unit_kp3d4_rich_v1"
        )
    payload = json.loads(left.to_canonical_json_bytes())
    payload["states"][0]["debt"][0] = True
    with pytest.raises(HistoryContractError, match="signed-64"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority="unit_kp3d4_rich_v1",
        )
    payload = json.loads(left.to_canonical_json_bytes())
    payload["states"][0]["identity_key"] = payload["states"][0]["identity_key"].lower()
    with pytest.raises(HistoryContractError, match="uppercase hexadecimal"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority="unit_kp3d4_rich_v1",
        )
    with pytest.raises(HistoryContractError, match="authority"):
        FiniteTotalActionDomain.from_json_bytes(
            left.to_canonical_json_bytes(), expected_source_authority="wrong"
        )
    with pytest.raises(HistoryContractError, match="strict UTF-8"):
        ExactOpenState(b"identity", b"\xff", (0, 0, 0, 0, 0), b"response")
    with pytest.raises(HistoryContractError, match="strict UTF-8"):
        TaskSeed("\ud800", b"identity")

    class DomainSubclass(FiniteTotalActionDomain):
        pass

    with pytest.raises(HistoryContractError, match="subclass"):
        DomainSubclass.from_json_bytes(
            left.to_canonical_json_bytes(),
            expected_source_authority="unit_kp3d4_rich_v1",
        )


def test_source_authority_requires_exact_runtime_string_and_digest_match() -> None:
    class LyingAuthorityComparator:
        def __eq__(self, _other: object) -> bool:
            return True

        def __ne__(self, _other: object) -> bool:
            return False

    domain = _rich_domain()
    impostor = LyingAuthorityComparator()
    with pytest.raises(HistoryContractError, match="source authority.*string"):
        FiniteTotalActionDomain.from_json_bytes(
            domain.to_canonical_json_bytes(),
            expected_source_authority=impostor,  # type: ignore[arg-type]
        )
    with pytest.raises(HistoryContractError, match="source authority.*string"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            expected_source_authority=impostor,  # type: ignore[arg-type]
            semantics_digest=domain.semantics_digest,
            task_seeds=domain.task_seeds,
            action_ids=domain.action_ids,
            open_states=domain.open_states,
            transition_rows=domain.transition_rows,
        )


def test_domain_rejects_identity_aliases_frontiers_and_post_init_mutation() -> None:
    domain = _rich_domain()
    original = domain.open_states[0]
    variants = (
        replace(original, full_signature=b"different-full"),
        replace(original, debt=(9, 0, 0, 0, 0)),
        replace(original, response_signature=b"different-response"),
    )
    messages = ("full signature", "different debt", "different response")
    for variant, message in zip(variants, messages, strict=True):
        with pytest.raises(HistoryContractError, match=message):
            build_finite_total_action_domain(
                source_authority=domain.source_authority,
                semantics_digest=domain.semantics_digest,
                task_seeds=domain.task_seeds,
                action_ids=domain.action_ids,
                open_states=(*domain.open_states, variant),
                transition_rows=domain.transition_rows,
            )
    with pytest.raises(HistoryContractError, match="not total"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=domain.task_seeds,
            action_ids=domain.action_ids,
            open_states=domain.open_states,
            transition_rows=domain.transition_rows[:-1],
        )

    attacked = copy.copy(domain)
    object.__setattr__(attacked, "open_states", tuple(reversed(attacked.open_states)))
    assert not attacked.sealed
    response = ExactOccurrenceResponse.open(domain.open_states[0])
    object.__setattr__(response.open_state, "debt", (True, 0, 0, 0, 0))
    with pytest.raises(HistoryContractError, match="signed-64"):
        response.hankel_channels()

    content_attacked = _rich_domain()
    object.__setattr__(
        content_attacked.open_states[0], "debt", (7, 0, 0, 0, 0)
    )
    with pytest.raises(HistoryContractError, match="content seal"):
        content_attacked.validate()


def test_domain_exactness_floor_is_digest_bound_and_requires_markov_contract() -> None:
    from lean_rgc.odlrq.hankel_depth4 import build_exact_raw_coordinate_hankel

    base = _rich_domain()
    assert base.exactness_floor == UNCONDITIONAL_FINITE_DOMAIN
    CanonicalHistoryChart.build(base, max_depth=1)

    conditional = build_finite_total_action_domain(
        source_authority=base.source_authority,
        expected_source_authority=base.source_authority,
        semantics_digest=base.semantics_digest,
        task_seeds=base.task_seeds,
        action_ids=base.action_ids,
        open_states=base.open_states,
        transition_rows=base.transition_rows,
        exactness_floor=CONDITIONAL_KSTATE_MARKOV,
    )
    assert conditional.exactness_floor == CONDITIONAL_KSTATE_MARKOV
    assert conditional.digest != base.digest
    restored = FiniteTotalActionDomain.from_json_bytes(
        conditional.to_canonical_json_bytes(),
        expected_source_authority=conditional.source_authority,
    )
    assert restored.exactness_floor == CONDITIONAL_KSTATE_MARKOV
    assert restored.digest == conditional.digest

    with pytest.raises(HistoryContractError, match="exactness floor.*Markov contract"):
        CanonicalHistoryChart.build(conditional, max_depth=1)
    contract = CanonicalKStateMarkovContract(
        frame_digest=_digest("conditional-floor-frame"),
        transition_semantics_digest=conditional.semantics_digest,
        action_grammar_digest=conditional.action_grammar_digest,
    )
    chart = CanonicalHistoryChart.build(
        conditional, max_depth=1, markov_contract=contract
    )
    assert chart.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert (
        build_exact_raw_coordinate_hankel(chart, cutoff=1).exactness_scope
        == CONDITIONAL_KSTATE_MARKOV
    )

    reminted_default = build_finite_total_action_domain(
        source_authority=conditional.source_authority,
        semantics_digest=conditional.semantics_digest,
        task_seeds=conditional.task_seeds,
        action_ids=conditional.action_ids,
        open_states=conditional.open_states,
        transition_rows=conditional.transition_rows,
    )
    assert reminted_default.exactness_floor == UNCONDITIONAL_FINITE_DOMAIN
    assert reminted_default.digest != conditional.digest

    payload = json.loads(conditional.to_canonical_json_bytes())
    del payload["exactness_floor"]
    with pytest.raises(HistoryContractError, match="field mismatch"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority=conditional.source_authority,
        )
    payload = json.loads(conditional.to_canonical_json_bytes())
    payload["exactness_floor"] = "NOMINAL_SCOPE_IS_FORBIDDEN"
    with pytest.raises(HistoryContractError, match="exactness floor"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority=conditional.source_authority,
        )

    object.__setattr__(conditional, "exactness_floor", UNCONDITIONAL_FINITE_DOMAIN)
    with pytest.raises(HistoryContractError, match="content seal"):
        conditional.validate()

    scope_attacked = CanonicalHistoryChart.build(base, max_depth=1)
    object.__setattr__(
        scope_attacked.domain,
        "exactness_floor",
        CONDITIONAL_KSTATE_MARKOV,
    )
    with pytest.raises(HistoryContractError, match="content seal"):
        _ = scope_attacked.exactness_scope


def test_domain_accessors_reject_subclasses_and_equality_objects_before_lookup() -> None:
    class BytesSubclass(bytes):
        pass

    class StringSubclass(str):
        pass

    class EqualityBytes:
        def __init__(self, value: bytes) -> None:
            self.value = value

        def __hash__(self) -> int:
            return hash(self.value)

        def __eq__(self, _other: object) -> bool:
            return True

    class EqualityString:
        def __init__(self, value: str) -> None:
            self.value = value

        def __hash__(self) -> int:
            return hash(self.value)

        def __eq__(self, _other: object) -> bool:
            return True

    domain = _rich_domain()
    identity = domain.task_seeds[0].source_identity_key
    task_id = domain.task_ids[0]
    action_id = domain.action_ids[0]
    for candidate in (BytesSubclass(identity), EqualityBytes(identity)):
        with pytest.raises(HistoryContractError, match="exact nonempty bytes"):
            domain.state(candidate)  # type: ignore[arg-type]
        with pytest.raises(HistoryContractError, match="exact nonempty bytes"):
            domain.transition(candidate, action_id)  # type: ignore[arg-type]
    for candidate in (StringSubclass(task_id), EqualityString(task_id)):
        with pytest.raises(HistoryContractError, match="exact nonempty string"):
            domain.seed_state(candidate)  # type: ignore[arg-type]
    for candidate in (StringSubclass(action_id), EqualityString(action_id)):
        with pytest.raises(HistoryContractError, match="exact nonempty string"):
            domain.transition(identity, candidate)  # type: ignore[arg-type]

    class KeySubclass(BehavioralClassKey):
        pass

    class EqualityKey:
        def __eq__(self, _other: object) -> bool:
            return True

    layer = CanonicalHistoryChart.build(domain, max_depth=1).layers[0]
    key = layer.classes[0].key
    for candidate in (
        KeySubclass(key.kind, key.state_identity_key),
        EqualityKey(),
    ):
        with pytest.raises(HistoryContractError, match="exact BehavioralClassKey"):
            layer.class_for(candidate)  # type: ignore[arg-type]


def test_generation_normal_form_flow_and_batch_reference_are_exact() -> None:
    domain = _rich_domain()
    chart = CanonicalHistoryChart.build(domain, max_depth=4)
    reverse = CanonicalHistoryChart.build(_rich_domain(reverse=True), max_depth=4)
    assert chart.digest == reverse.digest
    verify_generation_time_equals_batch(chart)
    flow = verify_flow_conservation(chart)
    assert flow.layer_totals == (2, 8, 32, 128, 512)
    assert flow.streamed_occurrences_checked == sum(flow.layer_totals)
    assert flow.exact_raw_histogram_coverage is True
    assert flow.streamed_histogram_digest == RICH_FLOW_DIGEST
    assert build_batch_reference(domain, max_depth=4).layers == tuple(
        layer.classes for layer in chart.layers
    )

    grammar = HistoryGrammar(chart)
    normal = grammar.normalize("unit_kp3d4_left", ("a", "b", "z", "a"))
    grammar.verify_witness(
        "unit_kp3d4_left", ("a", "b", "z", "a"), normal
    )
    assert grammar.normalize(
        normal.representative_task_id, normal.representative_word
    ) == normal
    grammar.reconstruct(normal)
    mutated = replace(normal, representative_word=("b", "a"))
    with pytest.raises(HistoryContractError, match="mutation|mismatch"):
        grammar.verify_witness(
            "unit_kp3d4_left", ("a", "b", "z", "a"), mutated
        )


def test_noncommuting_ghost_and_terminal_occurrence_provenance_survive() -> None:
    domain = _rich_domain()
    chart = CanonicalHistoryChart.build(domain, max_depth=4)
    ab = chart.lookup("unit_kp3d4_left", ("a", "b"))
    ba = chart.lookup("unit_kp3d4_left", ("b", "a"))
    assert ab != ba
    assert ab.open_state.identity_key == b"id:m"  # type: ignore[union-attr]
    assert ba.open_state.identity_key == b"id:n"  # type: ignore[union-attr]

    before = chart.lookup("unit_kp3d4_left", ())
    ghost = chart.lookup("unit_kp3d4_left", ("g",))
    assert before.hankel_channels() == ghost.hankel_channels()
    assert before != ghost
    assert chart.lookup("unit_kp3d4_left", ("z",)).kind is ExactOutcomeKind.SINK
    assert chart.lookup("unit_kp3d4_left", ("g", "z")).kind is ExactOutcomeKind.CLOSED

    layer_two = chart.layers[2]
    assert all(not hasattr(row.key, "task_id") for row in layer_two.classes)
    assert sum(
        row.key == BehavioralClassKey(ExactOutcomeKind.OPEN, b"id:m")
        for row in layer_two.classes
    ) == 1
    assert sum(
        row.key == BehavioralClassKey(ExactOutcomeKind.CLOSED)
        for row in layer_two.classes
    ) == 1

    left = chart.lookup("unit_kp3d4_left", ("a", "b", "z", "a"))
    right = chart.lookup("unit_kp3d4_right", ("b", "z", "g", "a"))
    assert left.kind is right.kind is ExactOutcomeKind.CLOSED
    assert left.terminal.kind is TerminalTransitionKind.CLOSED  # type: ignore[union-attr]
    assert left.terminal.entry_task_id == "unit_kp3d4_left"  # type: ignore[union-attr]
    assert left.terminal.entry_word == ("a", "b", "z")  # type: ignore[union-attr]
    assert right.terminal.entry_task_id == "unit_kp3d4_right"  # type: ignore[union-attr]
    assert right.terminal.entry_word == ("b", "z")  # type: ignore[union-attr]
    assert left.terminal != right.terminal
    assert independent_walk(domain, "unit_kp3d4_left", ("a", "b", "z", "a")) == left


def test_first_occurrence_uses_length_task_word_and_terminal_rep_persists() -> None:
    seed = _state("representative_seed", (2, 0, 0, 0, 0))
    child = _state("representative_child", (1, 0, 0, 0, 0))
    actions = ("a", "z")
    domain = build_finite_total_action_domain(
        source_authority="unit_kp3d4_representative_v1",
        semantics_digest=_digest("representative-semantics"),
        task_seeds=(
            TaskSeed("unit_kp3d4_rep_b", seed.identity_key),
            TaskSeed("unit_kp3d4_rep_a", seed.identity_key),
        ),
        action_ids=actions,
        open_states=(seed, child),
        transition_rows=(
            _row(seed, "a", child),
            _row(seed, "z", ExactOutcomeKind.CLOSED),
            _row(child, "a", ExactOutcomeKind.CLOSED),
            _row(child, "z", ExactOutcomeKind.SINK),
        ),
    )
    chart = CanonicalHistoryChart.build(domain, max_depth=3)
    verify_generation_time_equals_batch(chart)
    seed_class = chart.layers[0].classes[0]
    assert seed_class.raw_multiplicity == 2
    assert seed_class.representative_task_id == "unit_kp3d4_rep_a"
    closed_two = chart.layers[2].class_for(
        BehavioralClassKey(ExactOutcomeKind.CLOSED)
    )
    # Lexicographic tuple order would prefer ("a", "a"); the frozen order
    # prefers the shorter first-entry word and keeps it across terminal tails.
    assert closed_two.representative_word == ("z",)
    assert closed_two.representative_task_id == "unit_kp3d4_rep_a"
    closed_three = chart.layers[3].class_for(
        BehavioralClassKey(ExactOutcomeKind.CLOSED)
    )
    assert (
        closed_three.representative_task_id,
        closed_three.representative_word,
    ) == (
        closed_two.representative_task_id,
        closed_two.representative_word,
    )


def test_all_9425_depth_three_occurrences_match_field_by_field() -> None:
    domain = _wide_domain()
    chart = CanonicalHistoryChart.build(domain, max_depth=3)
    report = verify_raw_normalized_equality(chart, max_depth=3)
    assert report.occurrence_count == 9_425
    assert report.equal is True
    assert domain.digest == WIDE_DOMAIN_DIGEST
    assert chart.digest == WIDE_CHART_D3_DIGEST
    assert report.complete_response_digest == WIDE_RAW_D3_DIGEST
    assert chart.digest == CanonicalHistoryChart.build(
        _wide_domain(reverse=True), max_depth=3
    ).digest


def test_markov_scope_report_preflight_and_mutation_firewalls() -> None:
    domain = _rich_domain()
    pure = CanonicalHistoryChart.build(domain, max_depth=3)
    assert pure.exactness_scope == UNCONDITIONAL_FINITE_DOMAIN
    assert pure.report_preflight == preflight_report_bound(domain, max_depth=3)
    assert pure.report_preflight.report_byte_upper < MAX_REPORT_BYTES  # type: ignore[union-attr]
    assert pure.report_preflight.source_domain_digest == domain.digest  # type: ignore[union-attr]
    assert pure.report_preflight.max_depth == 3  # type: ignore[union-attr]

    contract = CanonicalKStateMarkovContract(
        frame_digest=_digest("frame"),
        transition_semantics_digest=domain.semantics_digest,
        action_grammar_digest=domain.action_grammar_digest,
    )
    conditional = CanonicalHistoryChart.build(
        domain, max_depth=3, markov_contract=contract, duplicate_row_checks=12
    )
    assert conditional.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert conditional.markov_contract.proof_status == "UNPROVED_ASSUMPTION"  # type: ignore[union-attr]
    assert conditional.report_preflight.duplicate_row_checks == 12  # type: ignore[union-attr]
    with pytest.raises(HistoryContractError, match="conditional"):
        replace(contract, exactness_scope=UNCONDITIONAL_FINITE_DOMAIN)
    with pytest.raises(HistoryContractError, match="semantics mismatch"):
        CanonicalHistoryChart.build(
            domain,
            max_depth=1,
            markov_contract=replace(
                contract, transition_semantics_digest=_digest("different")
            ),
        )
    with pytest.raises(HistoryContractError, match="action grammar mismatch"):
        CanonicalHistoryChart.build(
            domain,
            max_depth=1,
            markov_contract=replace(
                contract, action_grammar_digest=_digest("different-grammar")
            ),
        )

    attacked = CanonicalHistoryChart.build(domain, max_depth=2)
    object.__setattr__(
        attacked.layers[1].classes[0],
        "raw_multiplicity",
        attacked.layers[1].classes[0].raw_multiplicity + 1,
    )
    with pytest.raises(HistoryContractError, match="state-derived|layer-total"):
        attacked.validate()
    flow = verify_flow_conservation(pure)
    object.__setattr__(flow, "layer_totals", (True, *flow.layer_totals[1:]))
    with pytest.raises(HistoryContractError, match="signed-64"):
        flow.validate()

    bound = CanonicalHistoryChart.build(
        domain, max_depth=2, duplicate_row_checks=12
    )
    other = CanonicalHistoryChart.build(
        domain, max_depth=2, duplicate_row_checks=11
    )
    assert bound.digest != other.digest
    object.__setattr__(
        bound,
        "report_preflight",
        preflight_report_bound(domain, max_depth=2, duplicate_row_checks=11),
    )
    with pytest.raises(
            HistoryContractError,
            match=(
                "preflight.*seal|preflight.*mutation|preflight.*source-derived|"
                "semantic provenance"
            ),
        ):
        bound.validate()

    class ChartSubclass(CanonicalHistoryChart):
        pass

    with pytest.raises(HistoryContractError, match="subclass"):
        ChartSubclass.build(domain, max_depth=1)


def test_conditional_chart_cannot_be_downgraded_to_unconditional_after_admission() -> None:
    from lean_rgc.odlrq.hankel_depth4 import build_exact_raw_coordinate_hankel

    domain = _rich_domain()
    contract = CanonicalKStateMarkovContract(
        frame_digest=_digest("conditional-frame"),
        transition_semantics_digest=domain.semantics_digest,
        action_grammar_digest=domain.action_grammar_digest,
    )
    chart = CanonicalHistoryChart.build(
        domain, max_depth=2, markov_contract=contract
    )
    assert chart.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert (
        build_exact_raw_coordinate_hankel(chart, cutoff=1).exactness_scope
        == CONDITIONAL_KSTATE_MARKOV
    )

    object.__setattr__(chart, "markov_contract", None)
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        chart.validate()
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        _ = chart.exactness_scope
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        build_exact_raw_coordinate_hankel(chart, cutoff=1)


def test_chart_snapshots_markov_contract_and_rejects_valid_nested_mutation() -> None:
    domain = _rich_domain()
    external = CanonicalKStateMarkovContract(
        frame_digest=_digest("markov-external-frame"),
        transition_semantics_digest=domain.semantics_digest,
        action_grammar_digest=domain.action_grammar_digest,
    )
    original_frame = external.frame_digest
    chart = CanonicalHistoryChart.build(
        domain, max_depth=2, markov_contract=external
    )
    assert chart.markov_contract is not external
    object.__setattr__(external, "frame_digest", _digest("mutated-external-frame"))
    chart.validate()
    assert chart.markov_contract.frame_digest == original_frame  # type: ignore[union-attr]

    assert chart.markov_contract is not None
    object.__setattr__(
        chart.markov_contract,
        "frame_digest",
        _digest("valid-internal-frame-mutation"),
    )
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        chart.validate()
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        chart.lookup("unit_kp3d4_left", ())


def test_chart_snapshots_and_identity_binds_report_preflight() -> None:
    domain = _rich_domain()
    baseline = CanonicalHistoryChart.build(
        domain, max_depth=2, duplicate_row_checks=12
    )
    external = preflight_report_bound(
        domain, max_depth=2, duplicate_row_checks=12
    )
    admitted = CanonicalHistoryChart(
        domain,
        2,
        baseline.layers,
        None,
        external,
        12,
    )
    assert admitted.report_preflight is not external
    object.__setattr__(external, "report_byte_upper", external.report_byte_upper + 1)
    admitted.validate()

    equal_replacement = preflight_report_bound(
        admitted.domain, max_depth=2, duplicate_row_checks=12
    )
    assert equal_replacement == admitted.report_preflight
    object.__setattr__(admitted, "report_preflight", equal_replacement)
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        admitted.validate()
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        admitted.lookup("unit_kp3d4_left", ())

    nested = CanonicalHistoryChart.build(
        _rich_domain(), max_depth=2, duplicate_row_checks=12
    )
    assert nested.report_preflight is not None
    object.__setattr__(
        nested.report_preflight,
        "report_byte_upper",
        nested.report_preflight.report_byte_upper + 1,
    )
    with pytest.raises(HistoryContractError, match="semantic provenance"):
        nested.lookup("unit_kp3d4_left", ())


def test_chart_deep_snapshots_caller_layers_classes_edges_and_keys() -> None:
    baseline = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    admitted = CanonicalHistoryChart(
        baseline.domain,
        baseline.max_depth,
        baseline.layers,
        baseline.markov_contract,
        baseline.report_preflight,
        baseline.duplicate_row_checks,
    )
    assert admitted.layers is not baseline.layers
    assert admitted.layers[1] is not baseline.layers[1]
    assert admitted.layers[1].classes[0] is not baseline.layers[1].classes[0]
    assert admitted.layers[1].classes[0].key is not baseline.layers[1].classes[0].key
    assert admitted.layers[1].incoming_edges[0] is not baseline.layers[1].incoming_edges[0]
    assert (
        admitted.layers[1].incoming_edges[0].source_key
        is not baseline.layers[1].incoming_edges[0].source_key
    )
    assert (
        admitted.layers[1].incoming_edges[0].target_key
        is not baseline.layers[1].incoming_edges[0].target_key
    )

    before_digest = admitted.digest
    before_lookup = admitted.lookup("unit_kp3d4_left", ("a",))
    external_class = next(
        row
        for row in baseline.layers[1].classes
        if row.key.kind is ExactOutcomeKind.OPEN
    )
    external_edge = baseline.layers[1].incoming_edges[0]
    object.__setattr__(
        external_class.key, "state_identity_key", b"caller-mutated-class-key"
    )
    object.__setattr__(external_class, "raw_multiplicity", external_class.raw_multiplicity + 1)
    object.__setattr__(external_edge, "flow", external_edge.flow + 1)

    admitted.validate()
    assert admitted.digest == before_digest
    assert admitted.lookup("unit_kp3d4_left", ("a",)) == before_lookup


def test_chart_layer_shell_caps_and_shapes_fail_before_any_deep_snapshot(
    monkeypatch,
) -> None:
    baseline = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    total_classes = sum(len(layer.classes) for layer in baseline.layers)
    total_edges = sum(len(layer.incoming_edges) for layer in baseline.layers)
    original_class_cap = hnf.MAX_CANONICAL_CLASSES
    original_edge_cap = hnf.MAX_CONTRIBUTION_EDGES

    def forbidden_snapshot(*_args, **_kwargs):
        raise AssertionError("layer shell preflight must precede every deep snapshot")

    monkeypatch.setattr(hnf, "_snapshot_finite_domain", forbidden_snapshot)
    monkeypatch.setattr(hnf, "_snapshot_history_layer", forbidden_snapshot)
    monkeypatch.setattr(hnf, "MAX_CANONICAL_CLASSES", total_classes - 1)
    with pytest.raises(HistoryContractError, match="class preflight.*cap"):
        CanonicalHistoryChart(
            baseline.domain,
            baseline.max_depth,
            baseline.layers,
            baseline.markov_contract,
            baseline.report_preflight,
            baseline.duplicate_row_checks,
        )

    monkeypatch.setattr(hnf, "MAX_CANONICAL_CLASSES", original_class_cap)
    monkeypatch.setattr(hnf, "MAX_CONTRIBUTION_EDGES", total_edges - 1)
    with pytest.raises(HistoryContractError, match="edge preflight.*cap"):
        CanonicalHistoryChart(
            baseline.domain,
            baseline.max_depth,
            baseline.layers,
            baseline.markov_contract,
            baseline.report_preflight,
            baseline.duplicate_row_checks,
        )

    monkeypatch.setattr(hnf, "MAX_CONTRIBUTION_EDGES", original_edge_cap)
    with pytest.raises(HistoryContractError, match="duplicate row checks.*cap"):
        CanonicalHistoryChart(
            baseline.domain,
            baseline.max_depth,
            baseline.layers,
            baseline.markov_contract,
            baseline.report_preflight,
            hnf.MAX_DUPLICATE_ROW_CHECKS + 1,
        )

    malformed = copy.copy(baseline.layers[0])
    object.__setattr__(malformed, "classes", list(malformed.classes))
    malformed_layers = (malformed, *baseline.layers[1:])
    with pytest.raises(HistoryContractError, match="classes.*exact immutable tuple"):
        CanonicalHistoryChart(
            baseline.domain,
            baseline.max_depth,
            malformed_layers,
            baseline.markov_contract,
            baseline.report_preflight,
            baseline.duplicate_row_checks,
        )


def test_cap_preflight_stops_before_sequence_iteration() -> None:
    class PoisonActions:
        def __len__(self) -> int:
            return MAX_ACTIONS + 1

        def __iter__(self):
            raise AssertionError("cap failure must precede iteration")

    class PoisonTasks:
        def __len__(self) -> int:
            return MAX_TASK_SEEDS + 1

        def __iter__(self):
            raise AssertionError("task cap failure must precede iteration")

    domain = _rich_domain()
    with pytest.raises(HistoryContractError, match="cap"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=domain.task_seeds,
            action_ids=PoisonActions(),  # type: ignore[arg-type]
            open_states=domain.open_states,
            transition_rows=domain.transition_rows,
        )
    with pytest.raises(HistoryContractError, match="cap"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=PoisonTasks(),  # type: ignore[arg-type]
            action_ids=domain.action_ids,
            open_states=domain.open_states,
            transition_rows=domain.transition_rows,
        )


def test_direct_domain_and_json_caps_fail_before_item_construction(
    monkeypatch,
) -> None:
    domain = _rich_domain()

    def forbidden_snapshot(_value):
        raise AssertionError("direct cap failure must precede item snapshot")

    monkeypatch.setattr(hnf, "_snapshot_open_state", forbidden_snapshot)
    with pytest.raises(HistoryContractError, match="OPEN state domain.*cap"):
        FiniteTotalActionDomain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=domain.task_seeds,
            action_ids=domain.action_ids,
            open_states=(domain.open_states[0],) * (hnf.MAX_OPEN_STATES + 1),
            transition_rows=domain.transition_rows,
        )

    monkeypatch.undo()
    payload = domain.to_wire()
    payload["tasks"] = [{"malformed": True}]
    payload["action_ids"] = [f"overflow-{index}" for index in range(MAX_ACTIONS + 1)]

    def forbidden_task_seed(*_args, **_kwargs):
        raise AssertionError("JSON cap failure must precede item construction")

    monkeypatch.setattr(hnf, "TaskSeed", forbidden_task_seed)
    with pytest.raises(HistoryContractError, match="action_ids.*cap"):
        FiniteTotalActionDomain.from_json_bytes(
            json.dumps(payload).encode(),
            expected_source_authority=domain.source_authority,
        )


def test_json_payload_and_word_depth_caps_fail_before_parse_or_arithmetic(
    monkeypatch,
) -> None:
    def forbidden_parse(_payload):
        raise AssertionError("payload cap must precede JSON parsing")

    monkeypatch.setattr(hnf, "MAX_REPORT_BYTES", 8)
    monkeypatch.setattr(hnf, "_strict_json_object", forbidden_parse)
    with pytest.raises(HistoryContractError, match="payload byte cap"):
        FiniteTotalActionDomain.from_json_bytes(
            b"12345678", expected_source_authority="unit-cap-authority"
        )

    def forbidden_multiply(*_args, **_kwargs):
        raise AssertionError("depth cap must precede arithmetic")

    monkeypatch.setattr(hnf, "_checked_mul", forbidden_multiply)
    with pytest.raises(HistoryContractError, match="depth-four"):
        hnf.checked_word_count(1, 1, hnf.MAX_CANONICAL_DEPTH + 1)


def test_underreported_sequences_are_materialized_only_through_cap_plus_one(
    monkeypatch,
) -> None:
    domain = _rich_domain()
    monkeypatch.setattr(hnf, "MAX_ACTIONS", 2)
    monkeypatch.setattr(hnf, "MAX_TASK_SEEDS", 2)

    class UnderreportedActions:
        consumed = 0

        def __len__(self) -> int:
            return 1

        def __iter__(self):
            while True:
                type(self).consumed += 1
                if type(self).consumed > 2:
                    raise AssertionError("action materialization exceeded cap+1")
                yield f"underreported_action_{type(self).consumed}"

    class UnderreportedTasks:
        consumed = 0

        def __len__(self) -> int:
            return 1

        def __iter__(self):
            while True:
                type(self).consumed += 1
                if type(self).consumed > 2:
                    raise AssertionError("task materialization exceeded cap+1")
                yield domain.task_seeds[0]

    with pytest.raises(HistoryContractError, match="action_ids.*length mismatch"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=domain.task_seeds,
            action_ids=UnderreportedActions(),  # type: ignore[arg-type]
            open_states=domain.open_states,
            transition_rows=domain.transition_rows,
        )
    assert UnderreportedActions.consumed == 2

    monkeypatch.setattr(hnf, "MAX_ACTIONS", len(domain.action_ids))
    with pytest.raises(HistoryContractError, match="task_seeds.*length mismatch"):
        build_finite_total_action_domain(
            source_authority=domain.source_authority,
            semantics_digest=domain.semantics_digest,
            task_seeds=UnderreportedTasks(),  # type: ignore[arg-type]
            action_ids=domain.action_ids,
            open_states=domain.open_states,
            transition_rows=domain.transition_rows,
        )
    assert UnderreportedTasks.consumed == 2


def test_prepared_walker_is_unforgeable_and_deeply_snapshots_domain_aliases() -> None:
    domain = _rich_domain()
    walker = IndependentDomainWalker.prepare(domain)
    assert not hasattr(walker, "_seal")
    with pytest.raises((HistoryContractError, TypeError)):
        IndependentDomainWalker(
            walker.domain_digest,
            walker.task_ids,
            walker.action_ids,
            frozenset(walker.task_ids),
            frozenset(walker.action_ids),
            MappingProxyType({b"forged": "FORGED"}),
            MappingProxyType({walker.task_ids[0]: b"forged"}),
            MappingProxyType({}),
            object(),
        )

    copied_fields = object.__new__(IndependentDomainWalker)
    for name, value in vars(walker).items():
        object.__setattr__(copied_fields, name, value)
    with pytest.raises(HistoryContractError, match="factory provenance"):
        copied_fields.validate()
    with pytest.raises(HistoryContractError, match="factory provenance"):
        copied_fields.lookup("unit_kp3d4_left", ())

    replacement_attacked = IndependentDomainWalker.prepare(_rich_domain())
    object.__setattr__(
        replacement_attacked,
        "_rows",
        MappingProxyType(dict(replacement_attacked._rows)),
    )
    with pytest.raises(HistoryContractError, match="factory provenance"):
        replacement_attacked.lookup("unit_kp3d4_left", ("a",))

    primitive_walker = IndependentDomainWalker.prepare(_rich_domain())
    assert all(type(payload) is tuple for payload in primitive_walker._rows.values())
    assert all(
        type(payload) is tuple for payload in primitive_walker._open_responses.values()
    )

    seed_alias = domain.seed_state("unit_kp3d4_left")
    seed_before = walker.lookup("unit_kp3d4_left", ())
    row_alias = domain.transition(seed_alias.identity_key, "a")
    successor_before = walker.lookup("unit_kp3d4_left", ("a",))
    digest_before = walker.domain_digest

    object.__setattr__(seed_alias, "debt", (99, 0, 0, 0, 0))
    object.__setattr__(row_alias, "target_identity_key", b"id:y")

    assert walker.domain_digest == digest_before
    assert walker.lookup("unit_kp3d4_left", ()) == seed_before
    assert walker.lookup("unit_kp3d4_left", ("a",)) == successor_before


def test_verification_reports_require_source_bound_producer_seals() -> None:
    chart = CanonicalHistoryChart.build(_rich_domain(), max_depth=3)
    with pytest.raises(HistoryContractError, match="only.*verifier|producer"):
        hnf.RawNormalizedEqualityReport(3, 1, "0" * 64)
    with pytest.raises(HistoryContractError, match="only.*verifier|producer"):
        hnf.FlowVerificationReport(0, (1,), 1, True, "0" * 64)

    equality = verify_raw_normalized_equality(chart, max_depth=3)
    flow = verify_flow_conservation(chart)
    assert equality.source_digest == chart.digest
    assert flow.source_digest == chart.digest

    copied_equality = object.__new__(hnf.RawNormalizedEqualityReport)
    for name, value in vars(equality).items():
        object.__setattr__(copied_equality, name, value)
    with pytest.raises(HistoryContractError, match="verifier provenance"):
        copied_equality.validate()
    copied_flow = object.__new__(hnf.FlowVerificationReport)
    for name, value in vars(flow).items():
        object.__setattr__(copied_flow, name, value)
    with pytest.raises(HistoryContractError, match="verifier provenance"):
        copied_flow.validate()

    object.__setattr__(equality, "complete_response_digest", "0" * 64)
    object.__setattr__(equality, "_source_bound_seal", hnf._sha(equality._seal_wire()))
    with pytest.raises(HistoryContractError, match="source-bound.*seal"):
        equality.validate()
    object.__setattr__(flow, "streamed_histogram_digest", "0" * 64)
    object.__setattr__(flow, "_source_bound_seal", hnf._sha(flow._seal_wire()))
    with pytest.raises(HistoryContractError, match="source-bound.*seal"):
        flow.validate()


def test_terminal_occurrence_rejects_non_utf8_nonfinal_prefix_action() -> None:
    with pytest.raises(HistoryContractError, match="strict UTF-8"):
        TerminalOccurrence(
            TerminalTransitionKind.CLOSED,
            "unit_kp3d4_terminal_utf8",
            b"terminal-source",
            "a",
            ("\ud800", "a"),
        )
    with pytest.raises(HistoryContractError, match="strict UTF-8"):
        hnf._word(("\ud800",), "surrogate action word")


def test_domain_chart_and_public_lookup_detach_all_mutable_object_aliases() -> None:
    source = _rich_domain()
    admitted = build_finite_total_action_domain(
        source_authority=source.source_authority,
        semantics_digest=source.semantics_digest,
        task_seeds=source.task_seeds,
        action_ids=source.action_ids,
        open_states=source.open_states,
        transition_rows=source.transition_rows,
    )
    admitted_digest = admitted.digest
    source_seed = source.seed_state("unit_kp3d4_left")
    source_row = source.transition(source_seed.identity_key, "a")
    admitted_seed_before = admitted.seed_state("unit_kp3d4_left")
    admitted_row_before = admitted.transition(admitted_seed_before.identity_key, "a")
    object.__setattr__(source_seed, "debt", (88, 0, 0, 0, 0))
    object.__setattr__(source_row, "target_identity_key", b"id:y")
    assert admitted.digest == admitted_digest
    assert admitted.seed_state("unit_kp3d4_left") == admitted_seed_before
    assert admitted.transition(admitted_seed_before.identity_key, "a") == admitted_row_before

    chart_source = _rich_domain()
    chart = CanonicalHistoryChart.build(chart_source, max_depth=2)
    chart_digest = chart.digest
    chart_before = chart.lookup("unit_kp3d4_left", ("a",))
    chart_source_seed = chart_source.seed_state("unit_kp3d4_left")
    object.__setattr__(chart_source_seed, "debt", (77, 0, 0, 0, 0))
    object.__setattr__(
        chart_source.transition(chart_source_seed.identity_key, "a"),
        "target_identity_key",
        b"id:y",
    )
    assert chart.digest == chart_digest
    assert chart.lookup("unit_kp3d4_left", ("a",)) == chart_before

    exposed_chart_response = chart.lookup("unit_kp3d4_left", ())
    assert exposed_chart_response.open_state is not None
    object.__setattr__(exposed_chart_response.open_state, "debt", (66, 0, 0, 0, 0))
    assert chart.lookup("unit_kp3d4_left", ()).open_state.debt != (66, 0, 0, 0, 0)  # type: ignore[union-attr]

    walker = IndependentDomainWalker.prepare(_rich_domain())
    exposed_walker_response = walker.lookup("unit_kp3d4_left", ())
    assert exposed_walker_response.open_state is not None
    object.__setattr__(exposed_walker_response.open_state, "debt", (55, 0, 0, 0, 0))
    assert walker.lookup("unit_kp3d4_left", ()).open_state.debt != (55, 0, 0, 0, 0)  # type: ignore[union-attr]


def test_chart_lookup_detaches_private_open_payload_from_public_domain_state() -> None:
    chart = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    before = chart.lookup("unit_kp3d4_left", ())
    exposed = chart.domain.seed_state("unit_kp3d4_left")
    object.__setattr__(exposed, "debt", (91, 0, 0, 0, 0))

    assert chart.lookup("unit_kp3d4_left", ()) == before
    with pytest.raises(HistoryContractError, match="content seal|sealed exact finite domain"):
        chart.validate()


def test_chart_lookup_detaches_private_edge_payload_from_public_layer_edge() -> None:
    chart = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    seed_key = BehavioralClassKey(ExactOutcomeKind.OPEN, b"id:s0")
    victim = next(
        edge
        for edge in chart.layers[1].incoming_edges
        if edge.source_key == seed_key and edge.action_id == "a"
    )
    replacement = next(
        edge
        for edge in chart.layers[1].incoming_edges
        if edge.source_key == seed_key and edge.action_id == "b"
    )
    before = chart.lookup("unit_kp3d4_left", ("a",))
    assert victim.target_key != replacement.target_key
    object.__setattr__(victim, "target_key", replacement.target_key)

    assert chart.lookup("unit_kp3d4_left", ("a",)) == before
    with pytest.raises(HistoryContractError, match="state-derived"):
        chart.validate()

    replacement_attacked = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    object.__setattr__(
        replacement_attacked,
        "_edge_index",
        MappingProxyType(dict(replacement_attacked._edge_index)),
    )
    with pytest.raises(HistoryContractError, match="factory provenance"):
        replacement_attacked.lookup("unit_kp3d4_left", ("a",))
    primitive = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    assert all(type(value) is tuple for value in primitive._edge_index.values())
    assert all(type(value) is tuple for value in primitive._open_response_index.values())


def test_history_grammar_uses_private_representative_snapshot_not_public_layer() -> None:
    chart = CanonicalHistoryChart.build(_rich_domain(), max_depth=2)
    grammar = HistoryGrammar(chart)
    before = grammar.normalize("unit_kp3d4_left", ("a",))
    public_row = chart.layers[1].class_for(
        BehavioralClassKey(ExactOutcomeKind.OPEN, b"id:x")
    )
    assert public_row.representative_word != ("b",)
    object.__setattr__(public_row, "representative_word", ("b",))

    assert grammar.normalize("unit_kp3d4_left", ("a",)) == before
    with pytest.raises(HistoryContractError, match="state-derived"):
        chart.validate()


def test_public_chart_and_walker_reject_task_id_string_subclasses() -> None:
    class TaskIdSubclass(str):
        pass

    task_id = TaskIdSubclass("unit_kp3d4_left")
    domain = _rich_domain()
    chart = CanonicalHistoryChart.build(domain, max_depth=1)
    walker = IndependentDomainWalker.prepare(domain)
    with pytest.raises(HistoryContractError, match="exact nonempty string"):
        chart.lookup(task_id, ())
    with pytest.raises(HistoryContractError, match="exact nonempty string"):
        walker.lookup(task_id, ())


def test_registered_private_lookups_return_detached_open_responses() -> None:
    token = hnf._REGISTERED_LOOKUP_TOKEN
    domain = _rich_domain()
    chart = CanonicalHistoryChart.build(domain, max_depth=1)
    chart_digest = chart.digest
    first_chart = chart._lookup_registered("unit_kp3d4_left", (), token)
    assert first_chart.open_state is not None
    original_chart_debt = first_chart.open_state.debt
    object.__setattr__(first_chart.open_state, "debt", (93, 0, 0, 0, 0))
    second_chart = chart._lookup_registered("unit_kp3d4_left", (), token)
    assert second_chart.open_state is not None
    assert second_chart.open_state.debt == original_chart_debt
    assert chart.lookup("unit_kp3d4_left", ()).open_state.debt == original_chart_debt  # type: ignore[union-attr]
    chart.validate()
    assert chart.digest == chart_digest

    walker = IndependentDomainWalker.prepare(domain)
    walker_digest = walker.domain_digest
    first_raw = walker._lookup_registered("unit_kp3d4_left", (), token)
    assert first_raw.open_state is not None
    original_raw_debt = first_raw.open_state.debt
    object.__setattr__(first_raw.open_state, "debt", (94, 0, 0, 0, 0))
    second_raw = walker._lookup_registered("unit_kp3d4_left", (), token)
    assert second_raw.open_state is not None
    assert second_raw.open_state.debt == original_raw_debt
    assert walker.lookup("unit_kp3d4_left", ()).open_state.debt == original_raw_debt  # type: ignore[union-attr]
    walker.validate()
    assert walker.domain_digest == walker_digest


def test_history_export_surface_retains_caps_and_hides_batch_test_helpers() -> None:
    import lean_rgc.odlrq as odlrq

    assert hnf.MAX_SIGNATURE_BYTES == 64 * 1024
    assert hnf.MAX_TOTAL_SIGNATURE_BYTES == 8 * 1024 * 1024
    assert "MAX_SIGNATURE_BYTES" in hnf.__all__
    assert "MAX_TOTAL_SIGNATURE_BYTES" in hnf.__all__
    assert odlrq.MAX_SIGNATURE_BYTES == hnf.MAX_SIGNATURE_BYTES
    assert odlrq.MAX_TOTAL_SIGNATURE_BYTES == hnf.MAX_TOTAL_SIGNATURE_BYTES
    assert "BatchHistoryReference" not in hnf.__all__
    assert "build_batch_reference" not in hnf.__all__
    assert "BatchHistoryReference" not in odlrq.__all__
    assert "build_batch_reference" not in odlrq.__all__
    assert not hasattr(odlrq, "BatchHistoryReference")
    assert not hasattr(odlrq, "build_batch_reference")
    assert callable(hnf.build_batch_reference)


def test_prepared_independent_walker_validates_once_and_batch_depth_fails_first(
    monkeypatch,
) -> None:
    domain = _rich_domain()
    calls = 0
    original_validate = FiniteTotalActionDomain.validate

    def counted_validate(self) -> None:
        nonlocal calls
        calls += 1
        original_validate(self)

    monkeypatch.setattr(FiniteTotalActionDomain, "validate", counted_validate)
    walker = IndependentDomainWalker.prepare(domain)
    left = walker.lookup("unit_kp3d4_left", ("a", "b"))
    right = walker.lookup("unit_kp3d4_left", ("a", "b"))
    assert left == right
    assert left is not right
    for _ in range(500):
        assert walker.lookup("unit_kp3d4_left", ("a", "b")) == walker.lookup(
            "unit_kp3d4_left", ("a", "b")
        )
    assert calls == 1

    chart = CanonicalHistoryChart.build(domain, max_depth=2)
    with pytest.raises(HistoryContractError, match="authority"):
        chart._lookup_registered("unit_kp3d4_left", ("a",), object())
    with pytest.raises(HistoryContractError, match="authority"):
        walker._lookup_registered("unit_kp3d4_left", ("a",), object())

    def forbidden_arithmetic(*_args, **_kwargs):
        raise AssertionError("depth cap must precede arithmetic")

    monkeypatch.setattr(hnf, "checked_word_count", forbidden_arithmetic)
    with pytest.raises(HistoryContractError, match="depth-four"):
        build_batch_reference(domain, max_depth=5)


def test_runner_forbids_external_channels_when_policy_is_active() -> None:
    if os.environ.get("UPRIME_KP3_D4_C1_POLICY") != "forbid":
        pytest.skip("asserted by the fixed C1 runner")
    assert "UPRIME_KP3_D4_C1_EXIT_RECEIPT" not in os.environ
    import subprocess
    import nt

    with pytest.raises(RuntimeError, match="may not spawn"):
        subprocess.run(["cmd", "/c", "exit", "0"])
    with pytest.raises(RuntimeError, match="may not spawn"):
        os._exit(0)
    with pytest.raises(RuntimeError, match="may not spawn"):
        os.execv("forbidden.exe", ("forbidden.exe",))
    with pytest.raises(RuntimeError, match="may not spawn"):
        nt._exit(0)
    with pytest.raises(RuntimeError, match="network"):
        socket.create_connection(("127.0.0.1", 1))
    repo = Path.cwd()
    with pytest.raises((PermissionError, RuntimeError), match="forbidden|may not"):
        (repo / "docs/experiments/inputs/uprime_kp3_d4_fresh_tasks.json").read_bytes()
    with pytest.raises((PermissionError, RuntimeError), match="forbidden|may not"):
        (repo / "lean_rgc/native_lean/RGCKernelRPC.lean").read_bytes()
