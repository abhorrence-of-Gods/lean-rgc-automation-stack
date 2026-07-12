from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib
import inspect
import random

import pytest

import lean_rgc.odlrq.hankel_depth4 as hd4
from lean_rgc.odlrq.contracts import StrictContractError
from lean_rgc.odlrq.hankel_depth4 import (
    ExactRankCertificateKind,
    RawHankelRowKey,
    build_exact_raw_coordinate_hankel,
    certify_exact_rank,
    certify_hankel_family,
    preflight_hankel_dimensions,
    verify_exact_rank_certificate,
)
from lean_rgc.odlrq.history_normal_form import (
    CONDITIONAL_KSTATE_MARKOV,
    CanonicalHistoryChart,
    CanonicalKStateMarkovContract,
    ExactOccurrenceResponse,
    ExactOpenState,
    ExactOutcomeKind,
    IndependentDomainWalker,
    SealedTransitionRow,
    TaskSeed,
    build_finite_total_action_domain,
)


FULL_SOURCE_DIGEST = "C3DCE9E475524075AC909D43078E6A5D264D01D07A8F5985468FD42B00C8D567"
FULL_RESPONSE_DIGEST = "AF523D67F49E166B1DFA55C195532C65FB81B51CFDF1D3306AB88A83F9642164"
FULL_MATRIX_DIGEST = "B1ACD7FBF5A1A371352980135D250592A7E531A3F765E9C6131DE87FE42C6352"
SMALL_SOURCE_DIGEST = "C459EBA7D290D1FCB59BE166D4E494F4E2109DAC378AB91462EF66D94ED500A2"
SMALL_RESPONSE_DIGEST = "AF8421BD21B75C05817C22D29EC77CD25F5CDC198C4793894BA317D359E80251"
SMALL_MATRIX_DIGEST = "74F7D363DF5CE8FE21FEF3496B824250F634135B42028770EF6C20D10B822F8B"


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest().upper()


def _field_payload(instance: object) -> dict[str, object]:
    return {item.name: getattr(instance, item.name) for item in fields(instance)}


def _unregistered_field_copy(instance: object) -> object:
    copied = object.__new__(type(instance))
    for name, value in _field_payload(instance).items():
        object.__setattr__(copied, name, value)
    return copied


def _state(
    name: str,
    debt: tuple[int, int, int, int, int],
    *,
    response_variant: str = "",
) -> ExactOpenState:
    return ExactOpenState(
        f"unit_kp3d4_id:{name}".encode(),
        f"unit_kp3d4_full:{name}".encode(),
        debt,
        f"unit_kp3d4_response:{name}{response_variant}".encode(),
    )


def _row(
    source: ExactOpenState,
    action: str,
    target: ExactOpenState | ExactOutcomeKind,
) -> SealedTransitionRow:
    if type(target) is ExactOpenState:
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


def _small_domain(*, reverse: bool = False, response_variant: str = ""):
    s0 = _state("s0", (1, 0, 0, 3, 5), response_variant=response_variant)
    s1 = _state("s1", (2, 1, 0, 4, 7), response_variant=response_variant)
    s2 = _state("s2", (3, 0, 1, 6, 9), response_variant=response_variant)
    actions = ("unit_kp3d4_a", "unit_kp3d4_b")
    transitions = (
        (s0, actions[0], s1),
        (s0, actions[1], s2),
        (s1, actions[0], s1),
        (s1, actions[1], ExactOutcomeKind.CLOSED),
        (s2, actions[0], ExactOutcomeKind.SINK),
        (s2, actions[1], s0),
    )
    states: tuple[ExactOpenState, ...] = (s0, s1, s2)
    tasks = (
        TaskSeed("unit_kp3d4_t0", s0.identity_key),
        TaskSeed("unit_kp3d4_t1", s1.identity_key),
    )
    rows = tuple(_row(source, action, target) for source, action, target in transitions)
    if reverse:
        states = tuple(reversed(states))
        actions = tuple(reversed(actions))
        tasks = tuple(reversed(tasks))
        rows = tuple(reversed(rows))
    return build_finite_total_action_domain(
        source_authority="unit_kp3d4_small_exact",
        expected_source_authority="unit_kp3d4_small_exact",
        semantics_digest=_digest("unit_kp3d4_small_semantics"),
        task_seeds=tasks,
        action_ids=actions,
        open_states=states,
        transition_rows=rows,
    )


def _small_chart(
    *,
    reverse: bool = False,
    response_variant: str = "",
    conditional: bool = False,
) -> CanonicalHistoryChart:
    domain = _small_domain(reverse=reverse, response_variant=response_variant)
    contract = None
    if conditional:
        contract = CanonicalKStateMarkovContract(
            frame_digest=_digest("unit_kp3d4_frame"),
            transition_semantics_digest=domain.semantics_digest,
            action_grammar_digest=domain.action_grammar_digest,
        )
    return CanonicalHistoryChart.build(
        domain,
        max_depth=4,
        markov_contract=contract,
    )


def _full_domain(*, reverse: bool = False, task_count: int = 5):
    s0 = _state("wide0", (2, 0, 0, 2, 4))
    s1 = _state("wide1", (1, 1, 0, 3, 6))
    actions = tuple(f"unit_kp3d4_a{index:02d}" for index in range(12))
    rows: list[SealedTransitionRow] = []
    for state in (s0, s1):
        for action in actions:
            if state is s0 and action == actions[0]:
                target = s1
            elif state is s1 and action == actions[1]:
                target = s0
            else:
                target = state
            rows.append(_row(state, action, target))
    tasks = tuple(
        TaskSeed(
            f"unit_kp3d4_task_{index:02d}",
            (s0, s1)[index % 2].identity_key,
        )
        for index in range(task_count)
    )
    states: tuple[ExactOpenState, ...] = (s0, s1)
    row_tuple = tuple(rows)
    if reverse:
        tasks = tuple(reversed(tasks))
        actions = tuple(reversed(actions))
        states = tuple(reversed(states))
        row_tuple = tuple(reversed(row_tuple))
    return build_finite_total_action_domain(
        source_authority="unit_kp3d4_full_exact",
        semantics_digest=_digest("unit_kp3d4_full_semantics"),
        task_seeds=tasks,
        action_ids=actions,
        open_states=states,
        transition_rows=row_tuple,
    )


def test_frozen_dimension_preflight_d1_through_d4() -> None:
    expected = {
        1: (5, 13, 91, 65, 455),
        2: (65, 13, 91, 845, 5_915),
        3: (65, 157, 1_099, 10_205, 71_435),
        4: (785, 157, 1_099, 123_245, 862_715),
    }
    for cutoff, values in expected.items():
        dimensions = preflight_hankel_dimensions(
            n_tasks=5, n_actions=12, cutoff=cutoff
        )
        assert (
            dimensions.n_rows,
            dimensions.n_suffixes,
            dimensions.n_columns,
            dimensions.n_word_coordinates,
            dimensions.n_cells,
        ) == values
    assert preflight_hankel_dimensions(
        n_tasks=5, n_actions=12, cutoff=3
    ).raw_words_through_cutoff == 9_425
    assert preflight_hankel_dimensions(
        n_tasks=5, n_actions=12, cutoff=4
    ).raw_words_through_cutoff == 113_105


def test_public_authority_and_caps_are_not_caller_waivable(monkeypatch) -> None:
    with pytest.raises(StrictContractError, match="signed-64"):
        preflight_hankel_dimensions(n_tasks=True, n_actions=12, cutoff=4)
    with pytest.raises(StrictContractError, match="overflow"):
        preflight_hankel_dimensions(
            n_tasks=hd4.MAX_SIGNED_64,
            n_actions=hd4.MAX_SIGNED_64,
            cutoff=4,
        )
    with pytest.raises(StrictContractError, match="cell cap"):
        preflight_hankel_dimensions(n_tasks=6, n_actions=12, cutoff=4)
    with pytest.raises(StrictContractError, match="raw occurrence cap"):
        preflight_hankel_dimensions(n_tasks=7, n_actions=12, cutoff=4)

    for function, forbidden in (
        (preflight_hankel_dimensions, {"cell_cap", "raw_occurrence_cap"}),
        (build_exact_raw_coordinate_hankel, {"cell_cap", "raw_occurrence_cap", "exactness_scope"}),
        (certify_exact_rank, {"rank_cap", "coefficient_bit_cap"}),
        (verify_exact_rank_certificate, {"coefficient_bit_cap"}),
    ):
        assert forbidden.isdisjoint(inspect.signature(function).parameters)

    with pytest.raises(StrictContractError, match="CanonicalHistoryChart"):
        build_exact_raw_coordinate_hankel(lambda *_: None, cutoff=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        build_exact_raw_coordinate_hankel(
            task_ids=("unit_kp3d4_fake",),  # type: ignore[call-arg]
            action_ids=("unit_kp3d4_fake_a",),
            cutoff=1,
            canonical_lookup=lambda *_: None,
            independent_raw_lookup=lambda *_: None,
            source_digest=_digest("unit_kp3d4_fake"),
        )

    calls: list[str] = []

    def forbidden_prepare(_cls, _domain):
        calls.append("prepared")
        raise AssertionError("walker prepared before cell preflight")

    monkeypatch.setattr(
        IndependentDomainWalker,
        "prepare",
        classmethod(forbidden_prepare),
    )
    over_cell_chart = CanonicalHistoryChart.build(_full_domain(task_count=6), max_depth=4)
    with pytest.raises(StrictContractError, match="cell cap"):
        build_exact_raw_coordinate_hankel(over_cell_chart, cutoff=4)
    assert calls == []


def test_small_d1_d4_exact_history_coordinates_and_certificates() -> None:
    chart = _small_chart()
    family = tuple(
        build_exact_raw_coordinate_hankel(chart, cutoff=cutoff)
        for cutoff in (1, 2, 3, 4)
    )
    for hankel in family:
        expected = preflight_hankel_dimensions(
            n_tasks=len(chart.domain.task_ids),
            n_actions=len(chart.domain.action_ids),
            cutoff=hankel.cutoff,
        )
        assert hankel.dimensions == expected
        assert hankel.source_digest == chart.digest
        assert hankel.exactness_scope == chart.exactness_scope
        assert hankel.equality_report.word_coordinates_checked == expected.n_word_coordinates
        assert hankel.equality_report.channel_cells_checked == expected.n_cells
        assert hankel.equality_report.exact_response_records_equal is True
        assert hankel.conditioning is None
        assert hankel.conditioning_censor == "NOT_ATTEMPTED_IN_THIS_PHASE"

    certificates = certify_hankel_family(family)
    assert tuple(certificate.cutoff for certificate in certificates) == (1, 2, 3, 4)
    for hankel, certificate in zip(family, certificates, strict=True):
        assert certificate.kind is ExactRankCertificateKind.COMPLETE_SPAN
        verification = verify_exact_rank_certificate(hankel, certificate)
        assert verification.verified is True
        assert verification.complete_span_verified is True


def test_noncommuting_words_and_canonical_coordinate_order_are_retained() -> None:
    chart = _small_chart()
    actions = chart.domain.action_ids
    ab = chart.lookup("unit_kp3d4_t0", actions)
    ba = chart.lookup("unit_kp3d4_t0", tuple(reversed(actions)))
    assert ab != ba
    hankel = build_exact_raw_coordinate_hankel(chart, cutoff=2)
    assert tuple(row.task_id for row in hankel.row_keys[:3]) == (
        "unit_kp3d4_t0",
        "unit_kp3d4_t0",
        "unit_kp3d4_t0",
    )
    assert hankel.suffix_words == ((), (actions[0],), (actions[1],))


def test_canonical_and_raw_wires_are_serialized_separately(monkeypatch) -> None:
    chart = _small_chart()
    original = ExactOccurrenceResponse.to_wire
    calls = 0

    def alternating_wire(self: ExactOccurrenceResponse):
        nonlocal calls
        calls += 1
        wire = original(self)
        if calls % 2 == 0:
            wire = dict(wire)
            wire["kind"] = "controlled-raw-wire-mismatch"
        return wire

    monkeypatch.setattr(ExactOccurrenceResponse, "to_wire", alternating_wire)
    with pytest.raises(StrictContractError, match="exact raw-coordinate response mismatch"):
        build_exact_raw_coordinate_hankel(chart, cutoff=1)
    assert calls >= 2


def test_primitive_trie_matches_every_naive_small_coordinate_and_is_detached() -> None:
    chart = _small_chart()
    hankel = build_exact_raw_coordinate_hankel(chart, cutoff=4)
    walker = IndependentDomainWalker.prepare(chart.domain)
    canonical_cache: dict[hd4.OpenResponseCacheKey, tuple[bytes, str]] = {}
    raw_cache: dict[hd4.OpenResponseCacheKey, tuple[bytes, str]] = {}
    response_hasher = hd4._ResponseCoordinateHasher()
    naive_rows: list[tuple[int, ...]] = []
    checked = 0
    for row_key in hankel.row_keys:
        cells: list[int] = []
        for suffix in hankel.suffix_words:
            word = row_key.prefix_word + suffix
            canonical = chart._lookup_registered(
                row_key.task_id, word, hd4._REGISTERED_LOOKUP_TOKEN
            )
            raw = walker._lookup_registered(
                row_key.task_id, word, hd4._REGISTERED_LOOKUP_TOKEN
            )
            canonical_wire, response_digest = hd4._serialize_exact_response(
                canonical, canonical_cache, "naive canonical response"
            )
            raw_wire, _ = hd4._serialize_exact_response(
                raw, raw_cache, "naive raw response"
            )
            assert canonical == raw
            assert canonical_wire == raw_wire
            response_hasher.update(
                row_key.task_id,
                row_key.prefix_word,
                suffix,
                response_digest,
            )
            cells.extend(hd4._project_response(canonical, "naive canonical response"))
            checked += 1
        naive_rows.append(tuple(cells))
    assert checked == hankel.dimensions.n_word_coordinates == 98
    assert tuple(naive_rows) == hankel.matrix
    assert response_hasher.hexdigest() == hankel.response_coordinate_digest
    assert hankel.source_digest == SMALL_SOURCE_DIGEST
    assert hankel.response_coordinate_digest == SMALL_RESPONSE_DIGEST
    assert hankel.matrix_digest == SMALL_MATRIX_DIGEST

    canonical_oracle = hd4._CanonicalPrimitiveCursorOracle._prepare(
        chart, hd4._REGISTERED_LOOKUP_TOKEN
    )
    raw_oracle = hd4._RawPrimitiveCursorOracle._prepare(
        walker, max_depth=4, token=hd4._REGISTERED_LOOKUP_TOKEN
    )
    canonical_seed = canonical_oracle.seed("unit_kp3d4_t0")
    raw_seed = raw_oracle.seed("unit_kp3d4_t0")
    first_canonical = canonical_oracle.response(canonical_seed)
    first_raw = raw_oracle.response(raw_seed)
    assert first_canonical.open_state is not None
    assert first_raw.open_state is not None
    original_debt = first_canonical.open_state.debt
    object.__setattr__(first_canonical.open_state, "debt", (99, 0, 0, 0, 0))
    object.__setattr__(first_raw.open_state, "debt", (98, 0, 0, 0, 0))
    assert canonical_oracle.response(canonical_seed).open_state.debt == original_debt  # type: ignore[union-attr]
    assert raw_oracle.response(raw_seed).open_state.debt == original_debt  # type: ignore[union-attr]

    close_action = chart.domain.action_ids[1]
    tail_action = chart.domain.action_ids[0]
    canonical_terminal = canonical_oracle.advance(
        canonical_oracle.seed("unit_kp3d4_t1"),
        close_action,
        (),
        (close_action,),
    )
    raw_terminal = raw_oracle.advance(
        raw_oracle.seed("unit_kp3d4_t1"),
        close_action,
        (),
        (close_action,),
    )
    canonical_tail = canonical_oracle.advance(
        canonical_terminal,
        tail_action,
        (),
        (close_action, tail_action),
    )
    raw_tail = raw_oracle.advance(
        raw_terminal,
        tail_action,
        (),
        (close_action, tail_action),
    )
    tail_response = canonical_oracle.response(canonical_tail)
    assert tail_response == raw_oracle.response(raw_tail)
    assert tail_response.terminal is not None
    assert tail_response.terminal.entry_word == (close_action,)
    object.__setattr__(tail_response.terminal, "entry_word", (tail_action,))
    assert canonical_oracle.response(canonical_tail).terminal.entry_word == (close_action,)  # type: ignore[union-attr]


def test_full_5x12_depth4_uses_exact_history_chart_and_prepared_raw_walker() -> None:
    chart = CanonicalHistoryChart.build(_full_domain(), max_depth=4)
    hankel = build_exact_raw_coordinate_hankel(chart, cutoff=4)
    assert hankel.equality_report.word_coordinates_checked == 123_245
    assert hankel.equality_report.channel_cells_checked == 862_715
    assert len(hankel.row_keys) == 785
    assert len(hankel.column_keys) == 1_099
    assert hankel.source_digest == chart.digest
    assert hankel.row_keys[0] == RawHankelRowKey("unit_kp3d4_task_00", ())
    assert hankel.source_digest == FULL_SOURCE_DIGEST
    assert hankel.response_coordinate_digest == FULL_RESPONSE_DIGEST
    assert hankel.matrix_digest == FULL_MATRIX_DIGEST
    assert (
        hd4._primitive_trie_transition_count(hankel.dimensions, n_tasks=5)
        == 123_240
    )


def test_task_action_and_input_permutations_are_digest_invariant() -> None:
    left_chart = _small_chart()
    right_chart = _small_chart(reverse=True)
    assert left_chart.digest == right_chart.digest
    left = build_exact_raw_coordinate_hankel(left_chart, cutoff=3)
    right = build_exact_raw_coordinate_hankel(right_chart, cutoff=3)
    assert left.row_keys == right.row_keys
    assert left.suffix_words == right.suffix_words
    assert left.matrix == right.matrix
    assert left.response_coordinate_digest == right.response_coordinate_digest
    assert left.matrix_digest == right.matrix_digest


def _independent_fraction_rank(matrix: tuple[tuple[int, ...], ...]) -> int:
    rows = [[Fraction(value) for value in row] for row in matrix]
    rank = 0
    for column in range(len(rows[0])):
        pivot = next(
            (index for index in range(rank, len(rows)) if rows[index][column]),
            None,
        )
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_value = rows[rank][column]
        rows[rank] = [value / pivot_value for value in rows[rank]]
        for index in range(len(rows)):
            if index == rank:
                continue
            factor = rows[index][column]
            if factor:
                rows[index] = [
                    left - factor * right
                    for left, right in zip(rows[index], rows[rank], strict=True)
                ]
        rank += 1
        if rank == len(rows):
            break
    return rank


def test_fraction_free_producer_and_fraction_verifier_match_third_rank_oracle() -> None:
    generator = random.Random(0xD4C1)
    for trial in range(24):
        n_rows = 1 + trial % 9
        width = (1 + trial % 2) * len(hd4.RESPONSE_CHANNELS)
        matrix = tuple(
            tuple(generator.randrange(-3, 4) for _ in range(width))
            for _ in range(n_rows)
        )
        basis_indices, _, _, _, stopped = hd4._scan_exact_basis(
            enumerate(matrix),
            stop_after=hd4.RANK_LOWER_BOUND_SIZE,
            bit_cap=hd4.MAX_EXACT_COEFFICIENT_BITS,
        )
        verifier_indices, _, _, verifier_stopped = hd4._fraction_verifier_scan(
            matrix,
            stop_after=hd4.RANK_LOWER_BOUND_SIZE,
            bit_cap=hd4.MAX_EXACT_COEFFICIENT_BITS,
        )
        expected = _independent_fraction_rank(matrix)
        assert stopped is verifier_stopped is False
        assert len(basis_indices) == len(verifier_indices) == expected


def test_private_rank65_fixture_binds_basis_pivots_coordinates_and_matrix() -> None:
    hankel = hd4._materialize_private_rank65_algebra_fixture(
        hd4._PRIVATE_RANK_FIXTURE_TOKEN
    )
    certificate = certify_exact_rank(hankel)
    assert certificate.kind is ExactRankCertificateKind.RANK_AT_LEAST_65
    assert certificate.rank_or_lower_bound == 65
    assert certificate.basis_row_indices == tuple(range(65))
    assert certificate.pivot_columns == tuple(range(65))
    assert certificate.matrix_digest == hankel.matrix_digest
    assert certificate.response_coordinate_digest == hankel.response_coordinate_digest
    assert verify_exact_rank_certificate(hankel, certificate).verified is True


def test_affirmative_evidence_is_factory_only_and_immutably_bound() -> None:
    hankel = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=4)
    certificate = certify_exact_rank(hankel)
    verification = verify_exact_rank_certificate(hankel, certificate)
    assert verification.source_digest == hankel.source_digest
    assert verification.exactness_scope == hankel.exactness_scope
    assert len(verification.certificate_digest) == 64
    verification.validate()

    assert not hasattr(hankel, "_seal")
    assert not hasattr(certificate, "_seal")
    for retained, validator in (
        (hankel.equality_report, lambda value: value.validate()),
        (hankel, lambda value: value.validate()),
        (certificate, lambda value: value.validate()),
        (verification, lambda value: value.validate()),
    ):
        with pytest.raises(StrictContractError, match="factory provenance"):
            type(retained)(**_field_payload(retained))
        copied = _unregistered_field_copy(retained)
        with pytest.raises(StrictContractError, match="factory provenance"):
            validator(copied)

    mutated_report = build_exact_raw_coordinate_hankel(
        _small_chart(), cutoff=1
    ).equality_report
    object.__setattr__(mutated_report, "cutoff", 2)
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        mutated_report.validate()

    mutated_certificate = certify_exact_rank(
        build_exact_raw_coordinate_hankel(_small_chart(), cutoff=2)
    )
    object.__setattr__(
        mutated_certificate,
        "elimination_transcript_digest",
        _digest("unit_kp3d4_valid_but_rebound_transcript"),
    )
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        mutated_certificate.validate()

    mutated_verification = verify_exact_rank_certificate(hankel, certificate)
    object.__setattr__(
        mutated_verification,
        "rows_checked",
        mutated_verification.rows_checked + 1,
    )
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        mutated_verification.validate()

    matrix = [list(row) for row in hankel.matrix]
    matrix[0][0] += 1
    object.__setattr__(hankel, "matrix", tuple(tuple(row) for row in matrix))
    with pytest.raises(StrictContractError, match="matrix digest mismatch"):
        hankel.validate()

    nonnull = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=1)
    object.__setattr__(nonnull, "conditioning", 0)
    with pytest.raises(StrictContractError, match="conditioning must be exactly null"):
        nonnull.validate()

    nested = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=1)
    object.__setattr__(
        nested.dimensions,
        "raw_words_through_cutoff",
        nested.dimensions.raw_words_through_cutoff + 1,
    )
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        nested.validate()

    other = build_exact_raw_coordinate_hankel(
        _small_chart(response_variant="_verification_binding"), cutoff=4
    )
    other_certificate = certify_exact_rank(other)
    retained = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=4)
    rejected = verify_exact_rank_certificate(retained, other_certificate)
    assert rejected.verified is False
    assert rejected.source_digest == retained.source_digest
    assert rejected.exactness_scope == retained.exactness_scope
    rejected.validate()


def test_harvested_hankel_fields_cannot_rebind_fake_source_or_scope() -> None:
    real = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=1)
    fake_source = "0" * 64
    fake_matrix_digest = hd4._sha256(
        hd4._matrix_binding_wire(
            cutoff=real.cutoff,
            source_digest=fake_source,
            exactness_scope=real.exactness_scope,
            row_keys=real.row_keys,
            suffix_words=real.suffix_words,
            matrix=real.matrix,
            response_coordinate_digest=real.response_coordinate_digest,
        )
    )
    report_payload = _field_payload(real.equality_report)
    report_payload["matrix_digest"] = fake_matrix_digest
    with pytest.raises(StrictContractError, match="factory provenance"):
        hd4.RawCoordinateEqualityReport(**report_payload)

    forged_report = _unregistered_field_copy(real.equality_report)
    object.__setattr__(forged_report, "matrix_digest", fake_matrix_digest)
    forged_payload = _field_payload(real)
    forged_payload.update(
        source_digest=fake_source,
        matrix_digest=fake_matrix_digest,
        equality_report=forged_report,
    )
    with pytest.raises(StrictContractError, match="factory provenance"):
        hd4.ExactRawCoordinateHankel(**forged_payload)

    rebound = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=1)
    object.__setattr__(rebound, "source_digest", fake_source)
    object.__setattr__(rebound, "matrix_digest", fake_matrix_digest)
    object.__setattr__(rebound.equality_report, "matrix_digest", fake_matrix_digest)
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        rebound.validate()

    conditional = build_exact_raw_coordinate_hankel(
        _small_chart(conditional=True), cutoff=1
    )
    downgraded_scope = hd4.UNCONDITIONAL_FINITE_DOMAIN
    downgraded_digest = hd4._sha256(
        hd4._matrix_binding_wire(
            cutoff=conditional.cutoff,
            source_digest=conditional.source_digest,
            exactness_scope=downgraded_scope,
            row_keys=conditional.row_keys,
            suffix_words=conditional.suffix_words,
            matrix=conditional.matrix,
            response_coordinate_digest=conditional.response_coordinate_digest,
        )
    )
    object.__setattr__(conditional, "exactness_scope", downgraded_scope)
    object.__setattr__(conditional, "matrix_digest", downgraded_digest)
    object.__setattr__(
        conditional.equality_report, "matrix_digest", downgraded_digest
    )
    with pytest.raises(StrictContractError, match="immutable semantic binding"):
        conditional.validate()


def test_conditional_scope_is_derived_and_cannot_be_downgraded() -> None:
    chart = _small_chart(conditional=True)
    assert chart.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    hankel = build_exact_raw_coordinate_hankel(chart, cutoff=2)
    assert hankel.exactness_scope == CONDITIONAL_KSTATE_MARKOV
    assert hankel.source_digest == chart.digest
    certificate = certify_exact_rank(hankel)
    assert certificate.exactness_scope == CONDITIONAL_KSTATE_MARKOV

    with pytest.raises(TypeError):
        build_exact_raw_coordinate_hankel(
            chart,
            cutoff=2,
            exactness_scope=hd4.UNCONDITIONAL_FINITE_DOMAIN,  # type: ignore[call-arg]
        )
    with pytest.raises(StrictContractError, match="matrix digest mismatch"):
        replace(hankel, exactness_scope=hd4.UNCONDITIONAL_FINITE_DOMAIN)


def test_complete_response_digest_binds_nonchannel_exact_fields() -> None:
    ordinary = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=2)
    alternate = build_exact_raw_coordinate_hankel(
        _small_chart(response_variant="_alternate"), cutoff=2
    )
    assert alternate.matrix == ordinary.matrix
    assert alternate.response_coordinate_digest != ordinary.response_coordinate_digest
    assert alternate.matrix_digest != ordinary.matrix_digest


def test_independent_fraction_verifier_rejects_common_mode_producer_forgery(
    monkeypatch,
) -> None:
    hankel = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=2)

    def forged_scan(_rows, *, stop_after, bit_cap):
        assert stop_after == hd4.RANK_LOWER_BOUND_SIZE
        assert bit_cap == hd4.MAX_EXACT_COEFFICIENT_BITS
        return [], [], [], [[0, False, None]], False

    monkeypatch.setattr(hd4, "_scan_exact_basis", forged_scan)
    with pytest.raises(AssertionError, match="independent verification"):
        certify_exact_rank(hankel)


def test_exact_coefficient_cap_is_fixed_and_fail_closed() -> None:
    with pytest.raises(StrictContractError, match="coefficient bit cap"):
        hd4._scan_exact_basis(
            enumerate(((4, 0), (1, 1))),
            stop_after=hd4.RANK_LOWER_BOUND_SIZE,
            bit_cap=2,
        )
    hankel = build_exact_raw_coordinate_hankel(_small_chart(), cutoff=1)
    with pytest.raises(TypeError):
        certify_exact_rank(hankel, coefficient_bit_cap=2)  # type: ignore[call-arg]


def test_warm_rebuild_and_permutation_leave_exact_results_unchanged() -> None:
    chart = _small_chart()
    cold = build_exact_raw_coordinate_hankel(chart, cutoff=4)
    noise = {f"unit_kp3d4_noise_{index}": index for index in reversed(range(1_000))}
    assert len(noise) == 1_000
    warm = build_exact_raw_coordinate_hankel(chart, cutoff=4)
    assert warm.row_keys == cold.row_keys
    assert warm.suffix_words == cold.suffix_words
    assert warm.matrix == cold.matrix
    assert warm.matrix_digest == cold.matrix_digest
    assert certify_exact_rank(warm).to_wire() == certify_exact_rank(cold).to_wire()


def test_module_has_no_generic_native_float_or_process_surface() -> None:
    source = open(hd4.__file__, encoding="utf-8").read()
    assert "numpy" not in source
    assert "subprocess" not in source
    assert "native_lean" not in source
    assert "CanonicalLookup" not in source
    assert "canonical_lookup" not in source
    assert "independent_raw_lookup" not in source
    assert hd4.OFFICIAL_CONDITIONING is None
    assert hd4.OFFICIAL_CONDITIONING_CENSOR == "NOT_ATTEMPTED_IN_THIS_PHASE"
    assert not hasattr(hd4, "_HANKEL_SEAL")
    assert not hasattr(hd4, "_RANK_CERTIFICATE_SEAL")
    assert "_materialize_private_rank65_algebra_fixture" not in hd4.__all__
    assert "_PRIVATE_RANK_FIXTURE_TOKEN" not in hd4.__all__
