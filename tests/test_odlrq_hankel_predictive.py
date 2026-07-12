from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect
import os

import pytest

from lean_rgc.odlrq.contracts import (
    NOT_APPLICABLE,
    CanonicalPayload,
    ExactRational,
    StrictContractError,
    canonical_contract_bytes,
)
import lean_rgc.odlrq.hankel_predictive as hp
import lean_rgc.odlrq as odlrq_package
from lean_rgc.odlrq.hankel_predictive import (
    BoundedRationalRealization,
    ExactResponseAtom,
    ExactTargetResponseSet,
    HankelColumnKey,
    HankelRowKey,
    HankelTrainingSpec,
    PredictiveActionSymbol,
    PredictiveChannelClass,
    PredictiveResidualReport,
    ResponseAtomKey,
    ResponseChannelKey,
    TargetAtomDeclaration,
    TrainingHankelView,
    evaluate_predictive_residual,
    fit_bounded_rational_realization,
    make_response_atom_key,
    make_training_hankel_view,
)


def _payload(name: str, ordinal: int) -> CanonicalPayload:
    return CanonicalPayload.from_value(
        {"kind": "unit_cpu_hankel_action", "name": name, "ordinal": ordinal}
    )


def _q(value: int | Fraction) -> ExactRational:
    value = Fraction(value)
    return ExactRational(value.numerator, value.denominator)


def _as_fraction(value: ExactRational) -> Fraction:
    return Fraction(value.numerator, value.denominator)


def _row_times_matrix(
    row: tuple[Fraction, ...], matrix: tuple[tuple[Fraction, ...], ...]
) -> tuple[Fraction, ...]:
    return tuple(
        sum((row[i] * matrix[i][j] for i in range(len(row))), Fraction())
        for j in range(len(matrix[0]))
    )


def _dot(left: tuple[Fraction, ...], right: tuple[Fraction, ...]) -> Fraction:
    return sum((a * b for a, b in zip(left, right, strict=True)), Fraction())


def _weighted_response(
    task: str,
    word: tuple[str, ...],
    channel_id: str,
) -> Fraction:
    alpha = {
        "unit_cpu_task_0": (Fraction(1), Fraction(0)),
        "unit_cpu_task_1": (Fraction(0), Fraction(1)),
    }[task]
    matrices = {
        "unit_cpu_a": (
            (Fraction(1), Fraction(1)),
            (Fraction(0), Fraction(1)),
        ),
        "unit_cpu_b": (
            (Fraction(1), Fraction(0)),
            (Fraction(1), Fraction(1)),
        ),
    }
    beta = {
        "unit_cpu_nonterminal": (Fraction(1), Fraction(0)),
        "unit_cpu_closed": (Fraction(0), Fraction(1)),
        "unit_cpu_sink": (Fraction(1), Fraction(1)),
    }[channel_id]
    state = alpha
    for action in word:
        state = _row_times_matrix(state, matrices[action])
    return _dot(state, beta)


def _rank_two_bundle(*, reverse: bool = False):
    actions = (
        PredictiveActionSymbol("unit_cpu_a", _payload("a", 0)),
        PredictiveActionSymbol("unit_cpu_b", _payload("b", 1)),
    )
    channels = (
        ResponseChannelKey(
            "unit_cpu_nonterminal", PredictiveChannelClass.NONTERMINAL
        ),
        ResponseChannelKey(
            "unit_cpu_closed", PredictiveChannelClass.CLOSED_TERMINAL
        ),
        ResponseChannelKey("unit_cpu_sink", PredictiveChannelClass.SINK_TERMINAL),
    )
    rows = tuple(
        HankelRowKey(task, word)
        for task, word in (
            ("unit_cpu_task_0", ()),
            ("unit_cpu_task_0", ("unit_cpu_a",)),
            ("unit_cpu_task_0", ("unit_cpu_b",)),
            ("unit_cpu_task_0", ("unit_cpu_a", "unit_cpu_a")),
            ("unit_cpu_task_0", ("unit_cpu_a", "unit_cpu_b")),
            ("unit_cpu_task_1", ()),
            ("unit_cpu_task_1", ("unit_cpu_a",)),
            ("unit_cpu_task_1", ("unit_cpu_b",)),
        )
    )
    columns = tuple(HankelColumnKey((), channel) for channel in channels)
    if reverse:
        actions, channels, rows, columns = tuple(
            reversed(actions)
        ), tuple(reversed(channels)), tuple(reversed(rows)), tuple(reversed(columns))
    spec = HankelTrainingSpec(
        actions,
        ("unit_cpu_task_1", "unit_cpu_task_0") if reverse else (
            "unit_cpu_task_0",
            "unit_cpu_task_1",
        ),
        channels,
        rows,
        columns,
        2,
    )
    atoms = tuple(
        ExactResponseAtom(
            make_response_atom_key(row, column),
            _q(
                _weighted_response(
                    row.task_id,
                    row.prefix_word + column.suffix_word,
                    column.channel.channel_id,
                )
            ),
        )
        for row in spec.rows
        for column in spec.columns
    )
    target_keys = tuple(
        ResponseAtomKey(task, word, channel)
        for task, word in (
            ("unit_cpu_task_0", ("unit_cpu_b", "unit_cpu_a", "unit_cpu_b")),
            ("unit_cpu_task_1", ("unit_cpu_b", "unit_cpu_b", "unit_cpu_a")),
        )
        for channel in spec.channels
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_targets", spec.taxonomy_sha256, target_keys
    )
    view = make_training_hankel_view(
        spec, tuple(reversed(atoms)) if reverse else atoms, declaration
    )
    return spec, atoms, declaration, view


def _target_set(spec: HankelTrainingSpec, declaration: TargetAtomDeclaration):
    atoms = tuple(
        ExactResponseAtom(
            key,
            _q(_weighted_response(key.task_id, key.action_word, key.channel.channel_id)),
        )
        for key in declaration.keys
    )
    return ExactTargetResponseSet(
        "unit_cpu_target_values", spec.taxonomy_sha256, atoms
    )


def _wire(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def _fraction_from_wire(value: dict) -> Fraction:
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _matrix_from_wire(values: list[list[dict]]) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        tuple(_fraction_from_wire(value) for value in row) for row in values
    )


def _matrix_product(
    left: tuple[tuple[Fraction, ...], ...],
    right: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        tuple(
            sum(
                (left[i][k] * right[k][j] for k in range(len(right))),
                Fraction(),
            )
            for j in range(len(right[0]))
        )
        for i in range(len(left))
    )


def _contains_float(value) -> bool:
    if type(value) is float:
        return True
    if type(value) is dict:
        return any(_contains_float(item) for item in value.values())
    if type(value) in {tuple, list}:
        return any(_contains_float(item) for item in value)
    return False


def test_response_atom_key_aliases_splits_but_not_word_order_or_tokenization() -> None:
    channel = ResponseChannelKey(
        "unit_cpu_nonterminal", PredictiveChannelClass.NONTERMINAL
    )
    split_left = make_response_atom_key(
        HankelRowKey("unit_cpu_task", ("a",)),
        HankelColumnKey(("b", "c"), channel),
    )
    split_right = make_response_atom_key(
        HankelRowKey("unit_cpu_task", ()),
        HankelColumnKey(("a", "b", "c"), channel),
    )
    assert split_left == split_right
    assert ResponseAtomKey("unit_cpu_task", ("a", "b"), channel) != ResponseAtomKey(
        "unit_cpu_task", ("b", "a"), channel
    )
    assert ResponseAtomKey("unit_cpu_task", ("ab", "c"), channel) != ResponseAtomKey(
        "unit_cpu_task", ("a", "bc"), channel
    )


def test_action_identity_binds_id_and_payload_and_is_permutation_canonical() -> None:
    # Payload ordering is deliberately inverse to ID ordering.  Input order may
    # change, but ID/payload association may not be silently swapped.
    a = PredictiveActionSymbol("unit_cpu_a", _payload("a", 9))
    b = PredictiveActionSymbol("unit_cpu_b", _payload("b", 1))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    row = HankelRowKey("unit_cpu_task", ())
    column = HankelColumnKey((), channel)
    left = HankelTrainingSpec((a, b), ("unit_cpu_task",), (channel,), (row,), (column,), 1)
    right = HankelTrainingSpec((b, a), ("unit_cpu_task",), (channel,), (row,), (column,), 1)
    assert canonical_contract_bytes(left.to_dict()) == canonical_contract_bytes(
        right.to_dict()
    )
    swapped = HankelTrainingSpec(
        (
            PredictiveActionSymbol(a.action_id, b.payload),
            PredictiveActionSymbol(b.action_id, a.payload),
        ),
        ("unit_cpu_task",),
        (channel,),
        (row,),
        (column,),
        1,
    )
    assert canonical_contract_bytes(left.to_dict()) != canonical_contract_bytes(
        swapped.to_dict()
    )


def test_training_spec_rejects_missing_row_prefix_and_column_tail_closure() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    with pytest.raises(StrictContractError, match="closure"):
        HankelTrainingSpec(
            (action,),
            ("unit_cpu_task",),
            (channel,),
            (HankelRowKey("unit_cpu_task", ("unit_cpu_a",)),),
            (HankelColumnKey((), channel),),
            1,
        )
    with pytest.raises(StrictContractError, match="closure"):
        HankelTrainingSpec(
            (action,),
            ("unit_cpu_task",),
            (channel,),
            (HankelRowKey("unit_cpu_task", ()),),
            (HankelColumnKey(("unit_cpu_a",), channel),),
            1,
        )

    action_b = PredictiveActionSymbol("unit_cpu_b", _payload("b", 1))
    # A column is a right suffix: `a.b` requires its tail `b`, not its left
    # prefix `a`.  This direction is what preserves A_a A_b for noncommuting
    # action matrices.
    accepted = HankelTrainingSpec(
        (action, action_b),
        ("unit_cpu_task",),
        (channel,),
        (HankelRowKey("unit_cpu_task", ()),),
        (
            HankelColumnKey((), channel),
            HankelColumnKey(("unit_cpu_b",), channel),
            HankelColumnKey(("unit_cpu_a", "unit_cpu_b"), channel),
        ),
        1,
    )
    assert ("unit_cpu_a", "unit_cpu_b") in {
        column.suffix_word for column in accepted.columns
    }
    with pytest.raises(StrictContractError, match="suffix/tail closure"):
        HankelTrainingSpec(
            (action, action_b),
            ("unit_cpu_task",),
            (channel,),
            (HankelRowKey("unit_cpu_task", ()),),
            (
                HankelColumnKey((), channel),
                HankelColumnKey(("unit_cpu_a",), channel),
                HankelColumnKey(("unit_cpu_a", "unit_cpu_b"), channel),
            ),
            1,
        )


def test_target_alias_is_rejected_before_the_training_view_is_sealed() -> None:
    spec, atoms, declaration, _ = _rank_two_bundle()
    leaked = replace(atoms[0], key=declaration.keys[0])
    with pytest.raises(StrictContractError, match="target atom leaked"):
        make_training_hankel_view(spec, (leaked,) + atoms[1:], declaration)


def test_target_read_sentinel_fires_on_an_alternate_split_before_lookup() -> None:
    _, _, declaration, view = _rank_two_bundle()
    target = declaration.keys[0]
    reader = hp._TrackedReader(view)

    class BombMap(dict):
        def get(self, _key, _default=None):
            raise AssertionError("target guard ran after training-store lookup")

    reader.atom_map = BombMap()
    row = HankelRowKey(target.task_id, target.action_word[:1])
    column = HankelColumnKey(target.action_word[1:], target.channel)
    assert make_response_atom_key(row, column) == target
    with pytest.raises(StrictContractError, match="target atom read"):
        reader.read(row, column, "adversarial_alias")


def test_training_view_is_source_bound_and_permutation_canonical() -> None:
    spec, atoms, declaration, view = _rank_two_bundle()
    reverse_spec, _, reverse_declaration, reverse_view = _rank_two_bundle(reverse=True)
    assert canonical_contract_bytes(view.to_dict()) == canonical_contract_bytes(
        reverse_view.to_dict()
    )
    assert spec.taxonomy_sha256 == reverse_spec.taxonomy_sha256
    assert declaration.to_dict() == reverse_declaration.to_dict()
    object.__setattr__(atoms[0], "value", _q(999))
    with pytest.raises(StrictContractError, match="authority changed"):
        view.to_dict()


def test_rank_two_cross_is_lexicographic_exact_and_noncommutative() -> None:
    spec, _, declaration, view = _rank_two_bundle()
    realization = fit_bounded_rational_realization(view)
    wire = realization.to_dict()
    assert realization.r_train == 2
    assert realization.basis_rows == spec.rows[:2]
    assert realization.basis_columns == spec.columns[:2]
    assert wire["r_train"] == 2
    assert not _contains_float(wire)
    assert BoundedRationalRealization.from_dict(wire, view).to_dict() == wire

    action_matrices = {
        row["action_id"]: _matrix_from_wire(row["values"])
        for row in wire["action_matrices"]
    }
    a = action_matrices["unit_cpu_a"]
    b = action_matrices["unit_cpu_b"]
    assert _matrix_product(a, b) != _matrix_product(b, a)

    footprint = realization.training_footprint
    purposes = {event.purpose for event in footprint.reads}
    assert {
        "rank_candidate",
        "column_basis_candidate",
        "core_C",
        "alpha",
        "action_shift",
        "beta",
    } <= purposes
    assert len(
        [event for event in footprint.reads if event.purpose == "rank_candidate"]
    ) == len(spec.rows) * len(spec.columns)
    target_wires = {
        canonical_contract_bytes(key.to_dict()) for key in declaration.keys
    }
    assert target_wires.isdisjoint(
        canonical_contract_bytes(event.atom_key.to_dict())
        for event in footprint.reads
    )
    assert any(
        not decision.accepted for decision in footprint.basis_decisions
    ), "rejected basis candidates must remain visible"
    for decision in footprint.basis_decisions:
        assert isinstance(
            decision.candidate_key, (HankelRowKey, HankelColumnKey)
        )
        assert "candidate_index" not in decision.to_dict()
        assert "pivot_index" not in decision.to_dict()


def test_fit_and_evaluation_factories_each_run_one_bounded_fit(monkeypatch) -> None:
    spec, _, declaration, view = _rank_two_bundle()
    original = hp._derive_fit
    calls = 0

    def counted_fit(source):
        nonlocal calls
        calls += 1
        return original(source)

    monkeypatch.setattr(hp, "_derive_fit", counted_fit)
    realization = fit_bounded_rational_realization(view)
    assert calls == 1

    calls = 0
    evaluate_predictive_residual(realization, _target_set(spec, declaration))
    assert calls == 1


def test_rank_one_cross_and_realization_are_not_promoted_to_exact_authority() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = (
        HankelRowKey("unit_cpu_task", ()),
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",)),
    )
    columns = (HankelColumnKey((), channel),)
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (channel,), rows, columns, 1
    )
    atoms = (
        ExactResponseAtom(make_response_atom_key(rows[0], columns[0]), _q(1)),
        ExactResponseAtom(make_response_atom_key(rows[1], columns[0]), _q(2)),
    )
    target = ResponseAtomKey(
        "unit_cpu_task", ("unit_cpu_a", "unit_cpu_a"), channel
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_rank_one_target", spec.taxonomy_sha256, (target,)
    )
    realization = fit_bounded_rational_realization(
        make_training_hankel_view(spec, atoms, declaration)
    )
    assert realization.r_train == 1
    assert realization.basis_rows == (spec.rows[0],)
    assert realization.basis_columns == (spec.columns[0],)
    assert realization.to_dict()["predictive_tier"] == hp.PREDICTIVE_TIER
    assert "exact_operator" not in realization.to_dict()


def test_prefix_shift_consistency_rejects_finite_rank_nonrealization() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = tuple(
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",) * length)
        for length in range(3)
    )
    column = HankelColumnKey((), channel)
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (channel,), rows, (column,), 1
    )
    atoms = tuple(
        ExactResponseAtom(make_response_atom_key(row, column), _q(value))
        for row, value in zip(rows, (1, 2, 99), strict=True)
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_shift_inconsistent",
        spec.taxonomy_sha256,
        (
            ResponseAtomKey(
                "unit_cpu_task", ("unit_cpu_a",) * 3, channel
            ),
        ),
    )
    with pytest.raises(StrictContractError, match="shift consistency"):
        fit_bounded_rational_realization(
            make_training_hankel_view(spec, atoms, declaration)
        )


def test_column_shift_consistency_rejects_finite_rank_nonrealization() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    row = HankelRowKey("unit_cpu_task", ())
    columns = tuple(
        HankelColumnKey(("unit_cpu_a",) * length, channel)
        for length in range(3)
    )
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (channel,), (row,), columns, 1
    )
    atoms = tuple(
        ExactResponseAtom(make_response_atom_key(row, column), _q(value))
        for column, value in zip(columns, (1, 2, 99), strict=True)
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_column_shift_inconsistent",
        spec.taxonomy_sha256,
        (
            ResponseAtomKey(
                "unit_cpu_task", ("unit_cpu_a",) * 4, channel
            ),
        ),
    )
    with pytest.raises(StrictContractError, match="column shift consistency"):
        fit_bounded_rational_realization(
            make_training_hankel_view(spec, atoms, declaration)
        )


def test_noncommutative_column_tail_shift_rejects_wrong_order() -> None:
    actions = (
        PredictiveActionSymbol("unit_cpu_a", _payload("a", 0)),
        PredictiveActionSymbol("unit_cpu_b", _payload("b", 1)),
    )
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = (
        HankelRowKey("unit_cpu_task", ()),
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",)),
    )
    columns = (
        HankelColumnKey((), channel),
        HankelColumnKey(("unit_cpu_a",), channel),
        HankelColumnKey(("unit_cpu_b",), channel),
        HankelColumnKey(("unit_cpu_a", "unit_cpu_b"), channel),
    )
    spec = HankelTrainingSpec(
        actions, ("unit_cpu_task",), (channel,), rows, columns, 2
    )
    values = {
        (): 1,
        ("unit_cpu_a",): 0,
        ("unit_cpu_b",): 0,
        ("unit_cpu_a", "unit_cpu_a"): 1,
        ("unit_cpu_a", "unit_cpu_b"): 1,
        ("unit_cpu_a", "unit_cpu_a", "unit_cpu_b"): 7,
        ("unit_cpu_a", "unit_cpu_a", "unit_cpu_a"): 0,
        ("unit_cpu_b", "unit_cpu_a"): 0,
        ("unit_cpu_a", "unit_cpu_b", "unit_cpu_a"): 0,
    }
    atoms = tuple(
        ExactResponseAtom(
            ResponseAtomKey("unit_cpu_task", word, channel), _q(value)
        )
        for word, value in values.items()
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_noncommutative_column",
        spec.taxonomy_sha256,
        (
            ResponseAtomKey(
                "unit_cpu_task",
                ("unit_cpu_b", "unit_cpu_b"),
                channel,
            ),
        ),
    )
    with pytest.raises(StrictContractError, match="column shift consistency"):
        fit_bounded_rational_realization(
            make_training_hankel_view(spec, atoms, declaration)
        )


def test_nonempty_suffix_realization_and_present_class_ablation() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = tuple(
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",) * length)
        for length in range(3)
    )
    columns = (
        HankelColumnKey((), channel),
        HankelColumnKey(("unit_cpu_a",), channel),
    )
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (channel,), rows, columns, 1
    )
    atoms_by_key = {}
    for row in rows:
        for column in columns:
            key = make_response_atom_key(row, column)
            atoms_by_key[key] = ExactResponseAtom(
                key, _q(1 << len(key.action_word))
            )
    target_key = ResponseAtomKey(
        "unit_cpu_task", ("unit_cpu_a",) * 4, channel
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_nonempty_suffix", spec.taxonomy_sha256, (target_key,)
    )
    realization = fit_bounded_rational_realization(
        make_training_hankel_view(
            spec, tuple(atoms_by_key.values()), declaration
        )
    )
    report = evaluate_predictive_residual(
        realization,
        ExactTargetResponseSet(
            "unit_cpu_nonterminal_only",
            spec.taxonomy_sha256,
            (ExactResponseAtom(target_key, _q(16)),),
        ),
    )
    assert report.overall.exact_match_count == 1
    assert tuple(row.scope for row in report.ablations) == ("nonterminal",)


def test_rank_above_frozen_r_cap_blocks_without_partial_realization() -> None:
    spec, atoms, declaration, _ = _rank_two_bundle()
    capped = HankelTrainingSpec(
        spec.actions,
        spec.task_ids,
        spec.channels,
        spec.rows,
        spec.columns,
        1,
    )
    view = make_training_hankel_view(capped, atoms, declaration)
    with pytest.raises(StrictContractError, match="exceeds r_cap"):
        fit_bounded_rational_realization(view)


def test_missing_basis_shift_and_censor_fail_closed() -> None:
    spec, atoms, declaration, _ = _rank_two_bundle()
    # Keep a complete, rank-two base rectangle whose lexicographic basis is
    # epsilon/a, but omit aa/ab from the declared row universe.  The shift read
    # must fail instead of manufacturing a partial action matrix.
    short_rows = (
        HankelRowKey("unit_cpu_task_0", ()),
        HankelRowKey("unit_cpu_task_0", ("unit_cpu_a",)),
    )
    short_spec = HankelTrainingSpec(
        spec.actions,
        spec.task_ids[:1],
        spec.channels,
        short_rows,
        spec.columns,
        2,
    )
    short_atoms = tuple(
        atom
        for atom in atoms
        if atom.key.task_id == "unit_cpu_task_0"
        and atom.key.action_word in {(), ("unit_cpu_a",)}
    )
    short_targets = TargetAtomDeclaration(
        "unit_cpu_short_targets",
        short_spec.taxonomy_sha256,
        tuple(
            key
            for key in declaration.keys
            if key.task_id == "unit_cpu_task_0"
        ),
    )
    with pytest.raises(StrictContractError, match="missing training atom"):
        fit_bounded_rational_realization(
            make_training_hankel_view(short_spec, short_atoms, short_targets)
        )

    with pytest.raises(StrictContractError, match="censor"):
        ExactResponseAtom(short_atoms[0].key, short_atoms[0].value, "timeout")


def test_intermediate_rational_growth_blocks_exact_fit() -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    c0 = ResponseChannelKey("unit_cpu_c0", PredictiveChannelClass.NONTERMINAL)
    c1 = ResponseChannelKey("unit_cpu_c1", PredictiveChannelClass.NONTERMINAL)
    rows = (
        HankelRowKey("unit_cpu_task", ()),
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",)),
    )
    columns = (HankelColumnKey((), c0), HankelColumnKey((), c1))
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (c0, c1), rows, columns, 2
    )
    huge = 1 << 5000
    values = ((huge, 1), (1, huge))
    atoms = tuple(
        ExactResponseAtom(make_response_atom_key(row, column), _q(values[i][j]))
        for i, row in enumerate(spec.rows)
        for j, column in enumerate(spec.columns)
    )
    target = ResponseAtomKey(
        "unit_cpu_task", ("unit_cpu_a", "unit_cpu_a"), c0
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_growth_target", spec.taxonomy_sha256, (target,)
    )
    with pytest.raises(StrictContractError, match="bit cap"):
        fit_bounded_rational_realization(
            make_training_hankel_view(spec, atoms, declaration)
        )


def test_work_preflight_rejects_before_response_atom_serialization(monkeypatch) -> None:
    action = PredictiveActionSymbol("unit_cpu_a", _payload("a", 0))
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = tuple(
        HankelRowKey("unit_cpu_task", ("unit_cpu_a",) * length)
        for length in range(128)
    )
    columns = tuple(
        HankelColumnKey(("unit_cpu_a",) * length, channel)
        for length in range(128)
    )
    spec = HankelTrainingSpec(
        (action,), ("unit_cpu_task",), (channel,), rows, columns, 64
    )
    atom = ExactResponseAtom(make_response_atom_key(rows[0], columns[0]), _q(1))
    target = ResponseAtomKey(
        "unit_cpu_task", ("unit_cpu_a",) * 129, channel
    )
    declaration = TargetAtomDeclaration(
        "unit_cpu_preflight_target", spec.taxonomy_sha256, (target,)
    )

    def forbidden_to_dict(_self):
        raise AssertionError("response value serialized before W_H_pre passed")

    monkeypatch.setattr(ExactResponseAtom, "to_dict", forbidden_to_dict)
    with pytest.raises(StrictContractError, match="Hankel work"):
        make_training_hankel_view(spec, (atom,), declaration)


def test_cell_and_key_byte_caps_fire_before_response_serialization(monkeypatch) -> None:
    actions = tuple(
        PredictiveActionSymbol(f"unit_cpu_a{index:03d}", _payload("a", index))
        for index in range(500)
    )
    channel = ResponseChannelKey("unit_cpu_y", PredictiveChannelClass.NONTERMINAL)
    rows = (HankelRowKey("unit_cpu_task", ()),) + tuple(
        HankelRowKey("unit_cpu_task", (action.action_id,)) for action in actions
    )
    columns = (HankelColumnKey((), channel),) + tuple(
        HankelColumnKey((action.action_id,), channel) for action in actions[:499]
    )
    spec = HankelTrainingSpec(
        actions, ("unit_cpu_task",), (channel,), rows, columns, 1
    )
    atom = ExactResponseAtom(make_response_atom_key(rows[0], columns[0]), _q(1))
    declaration = TargetAtomDeclaration(
        "unit_cpu_cell_cap",
        spec.taxonomy_sha256,
        (
            ResponseAtomKey(
                "unit_cpu_task",
                (actions[0].action_id, actions[1].action_id),
                channel,
            ),
        ),
    )

    def forbidden_to_dict(_self):
        raise AssertionError("response serialized before structural cap")

    monkeypatch.setattr(ExactResponseAtom, "to_dict", forbidden_to_dict)
    with pytest.raises(StrictContractError, match="cell cap"):
        make_training_hankel_view(spec, (atom,), declaration)

    huge_action_id = "界" * 200_000
    huge_action = PredictiveActionSymbol(huge_action_id, _payload("huge", 0))
    small_row = HankelRowKey("unit_cpu_task", ())
    small_column = HankelColumnKey((), channel)
    huge_spec = HankelTrainingSpec(
        (huge_action,),
        ("unit_cpu_task",),
        (channel,),
        (small_row,),
        (small_column,),
        1,
    )
    huge_atom = ExactResponseAtom(
        make_response_atom_key(small_row, small_column), _q(1)
    )
    huge_declaration = TargetAtomDeclaration(
        "unit_cpu_key_cap",
        huge_spec.taxonomy_sha256,
        (ResponseAtomKey("unit_cpu_task", (huge_action_id,), channel),),
    )
    with pytest.raises(StrictContractError, match="semantic key bytes"):
        make_training_hankel_view(huge_spec, (huge_atom,), huge_declaration)


def test_realization_rederives_view_authority_and_is_permutation_canonical() -> None:
    _, atoms, _, view = _rank_two_bundle()
    _, _, _, reverse_view = _rank_two_bundle(reverse=True)
    realization = fit_bounded_rational_realization(view)
    reverse = fit_bounded_rational_realization(reverse_view)
    assert canonical_contract_bytes(realization.to_dict()) == canonical_contract_bytes(
        reverse.to_dict()
    )
    object.__setattr__(atoms[-1], "value", _q(31337))
    with pytest.raises(StrictContractError):
        realization.to_dict()


def test_capability_constructors_are_not_public_bypasses() -> None:
    _, _, _, view = _rank_two_bundle()
    with pytest.raises(StrictContractError):
        TrainingHankelView(
            view._spec,
            view._training_atoms,
            view._target_declaration,
            view._source_seal_sha256,
        )
    with pytest.raises(StrictContractError):
        BoundedRationalRealization(view, "00" * 32)


def test_external_authority_parsers_reject_unknown_and_wrong_sources() -> None:
    spec, atoms, declaration, view = _rank_two_bundle()
    assert HankelTrainingSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()
    assert TrainingHankelView.from_dict(
        view.to_dict(), spec, atoms, declaration
    ).to_dict() == view.to_dict()
    unknown = view.to_dict()
    unknown["unknown"] = True
    with pytest.raises(StrictContractError):
        TrainingHankelView.from_dict(unknown, spec, atoms, declaration)

    wrong_atoms = tuple(atoms[:-1]) + (
        ExactResponseAtom(atoms[-1].key, _q(_as_fraction(atoms[-1].value) + 1)),
    )
    with pytest.raises(StrictContractError, match="external authority"):
        TrainingHankelView.from_dict(view.to_dict(), spec, wrong_atoms, declaration)

    class BadView(TrainingHankelView):
        pass

    with pytest.raises(StrictContractError, match="polymorphic"):
        BadView.from_dict(view.to_dict(), spec, atoms, declaration)


def test_exact_target_residual_and_typed_ablations_roundtrip() -> None:
    spec, _, declaration, view = _rank_two_bundle()
    realization = fit_bounded_rational_realization(view)
    targets = _target_set(spec, declaration)
    report = evaluate_predictive_residual(realization, targets)
    wire = report.to_dict()
    assert wire["target_count"] == 6
    assert wire["prediction_count"] == 6
    assert wire["abstention_count"] == 0
    assert wire["exact_match_count"] == 6
    assert _fraction_from_wire(wire["coverage"]) == 1
    assert _fraction_from_wire(wire["exact_match_fraction"]) == 1
    assert _fraction_from_wire(wire["l1_error"]) == 0
    assert _fraction_from_wire(wire["max_absolute_error"]) == 0
    assert not _contains_float(wire)
    assert {row["scope"] for row in wire["per_channel"]} == {
        f"channel:{channel.channel_id}" for channel in spec.channels
    }
    assert set(wire["ablations"]) == {
        "nonterminal",
        "closed_terminal",
        "sink_terminal",
        "terminal_all",
    }
    assert all(row["covered"] for row in wire["responses"])
    assert all(
        row["abstention_reason"] == NOT_APPLICABLE for row in wire["responses"]
    )
    assert ExactTargetResponseSet.from_dict(targets.to_dict()).to_dict() == targets.to_dict()
    assert PredictiveResidualReport.from_dict(
        wire, realization, targets
    ).to_dict() == wire


def test_exact_residual_errors_keep_all_target_denominators() -> None:
    spec, _, declaration, view = _rank_two_bundle()
    realization = fit_bounded_rational_realization(view)
    exact = _target_set(spec, declaration)
    perturbed_atoms = []
    for atom in exact.atoms:
        delta = Fraction()
        if (
            atom.key.task_id == "unit_cpu_task_0"
            and atom.key.channel.channel_class is PredictiveChannelClass.NONTERMINAL
        ):
            delta = Fraction(1, 2)
        elif (
            atom.key.task_id == "unit_cpu_task_0"
            and atom.key.channel.channel_class
            is PredictiveChannelClass.CLOSED_TERMINAL
        ):
            delta = Fraction(2)
        elif (
            atom.key.task_id == "unit_cpu_task_1"
            and atom.key.channel.channel_class is PredictiveChannelClass.SINK_TERMINAL
        ):
            delta = Fraction(-3, 2)
        perturbed_atoms.append(
            ExactResponseAtom(
                atom.key, _q(_as_fraction(atom.value) + delta), atom.censor
            )
        )
    targets = ExactTargetResponseSet(
        "unit_cpu_perturbed_targets", spec.taxonomy_sha256, tuple(perturbed_atoms)
    )
    report = evaluate_predictive_residual(realization, targets)
    overall = report.overall
    assert overall.target_count == 6
    assert overall.prediction_count == 6
    assert overall.abstention_count == 0
    assert overall.exact_match_count == 3
    assert _as_fraction(overall.coverage) == 1
    assert _as_fraction(overall.exact_match_fraction) == Fraction(1, 2)
    assert _as_fraction(overall.l1_error) == 4
    assert _as_fraction(overall.max_absolute_error) == 2

    per_channel = {
        row.channel.channel_class: row for row in report.per_channel
    }
    expected = {
        PredictiveChannelClass.NONTERMINAL: (Fraction(1, 2), Fraction(1, 2)),
        PredictiveChannelClass.CLOSED_TERMINAL: (Fraction(2), Fraction(2)),
        PredictiveChannelClass.SINK_TERMINAL: (Fraction(3, 2), Fraction(3, 2)),
    }
    for kind, (l1, maximum) in expected.items():
        row = per_channel[kind]
        assert row.target_count == 2
        assert row.exact_match_count == 1
        assert _as_fraction(row.l1_error) == l1
        assert _as_fraction(row.max_absolute_error) == maximum

    ablations = {row.scope: row for row in report.ablations}
    terminal = ablations["terminal_all"]
    assert terminal.target_count == 4
    assert terminal.exact_match_count == 2
    assert _as_fraction(terminal.l1_error) == Fraction(7, 2)
    assert _as_fraction(terminal.max_absolute_error) == 2


def test_target_response_set_must_exactly_match_frozen_declaration() -> None:
    spec, _, declaration, view = _rank_two_bundle()
    realization = fit_bounded_rational_realization(view)
    exact = _target_set(spec, declaration)
    missing = ExactTargetResponseSet(
        "unit_cpu_missing_target", spec.taxonomy_sha256, exact.atoms[:-1]
    )
    with pytest.raises(StrictContractError, match="does not exactly equal"):
        evaluate_predictive_residual(realization, missing)

    extra_key = ResponseAtomKey(
        "unit_cpu_task_0",
        ("unit_cpu_a", "unit_cpu_a", "unit_cpu_a"),
        spec.channels[0],
    )
    extra = ExactTargetResponseSet(
        "unit_cpu_extra_target",
        spec.taxonomy_sha256,
        exact.atoms + (ExactResponseAtom(extra_key, _q(0)),),
    )
    with pytest.raises(StrictContractError, match="does not exactly equal"):
        evaluate_predictive_residual(realization, extra)

    wrong_taxonomy = ExactTargetResponseSet(
        "unit_cpu_wrong_taxonomy", "AA" * 32, exact.atoms
    )
    with pytest.raises(StrictContractError, match="taxonomy"):
        evaluate_predictive_residual(realization, wrong_taxonomy)


def test_residual_report_rederives_realization_and_target_authorities() -> None:
    spec, _, declaration, view = _rank_two_bundle()
    realization = fit_bounded_rational_realization(view)
    targets = _target_set(spec, declaration)
    report = evaluate_predictive_residual(realization, targets)
    object.__setattr__(targets.atoms[0], "value", _q(12345))
    with pytest.raises(StrictContractError, match="target"):
        report.to_dict()

    targets = _target_set(spec, declaration)
    report = evaluate_predictive_residual(realization, targets)
    object.__setattr__(realization, "_construction_seal", None)
    with pytest.raises(StrictContractError, match="construction seal"):
        report.to_dict()
    with pytest.raises(StrictContractError):
        PredictiveResidualReport(
            realization, targets, "00" * 32, "00" * 32
        )


def test_forbidden_historical_and_hard_tier_surfaces_are_absent() -> None:
    source = inspect.getsource(hp)
    assert "from .hankel import" not in source
    assert "quotient_generator" not in source
    forbidden = {
        "ExactFiniteOperator",
        "CertifiedIntervalOperator",
        "FiberEnvelope",
        "promote_to_exact",
        "promote_to_certified",
    }
    assert forbidden.isdisjoint(hp.__all__)
    assert forbidden.isdisjoint(dir(hp))
    assert set(hp.__all__) <= set(odlrq_package.__all__)


def test_runner_hides_receipt_and_denies_process_exit() -> None:
    if os.environ.get("UPRIME_WP4H_SUBPROCESS_POLICY") == "forbid":
        assert "UPRIME_WP4H_EXIT_RECEIPT" not in os.environ
        with pytest.raises(RuntimeError, match="may not spawn subprocesses"):
            os._exit(0)
