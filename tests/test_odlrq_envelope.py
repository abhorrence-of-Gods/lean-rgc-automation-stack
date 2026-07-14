from __future__ import annotations

import copy
from dataclasses import replace
from functools import lru_cache
from fractions import Fraction

import pytest

from lean_rgc.odlrq import (
    CanonicalPayload,
    ExactFiniteFiberLaw,
    ExactQuotientCoordinateGenerator,
    ExactRational,
    FiberCompletenessWitness,
    FiberEnvelope,
    FiberInclusionWitness,
    IntervalTargetRow,
    NominalOperator,
    ObservedIntervalOperator,
    PositiveFiberWeights,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    WeightedCompression,
    WeightedLifting,
    admit_synthetic_finite_snapshot,
    build_exact_quotient_coordinate_generator,
    build_fiber_envelope,
    build_synthetic_finite_snapshot,
    certify_fiber_completeness,
    declare_synthetic_transfer_layer,
    make_exact_finite_fiber_law,
    make_positive_fiber_weights,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    make_weighted_compression,
    make_weighted_lifting,
    observation_frame_digest,
    refine_exact_partition,
    verify_exact_partition,
    verify_fiber_envelope,
    verify_fiber_inclusion,
    witness_domain_membership,
)


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


_GENERATOR_CACHE: dict[tuple[str, tuple[tuple[str, int], ...]], ExactQuotientCoordinateGenerator] = {}


def _generator(
    role: str,
    open_coordinates: dict[str, int],
) -> ExactQuotientCoordinateGenerator:
    cache_key = (role, tuple(sorted(open_coordinates.items())))
    if cache_key in _GENERATOR_CACHE:
        return _GENERATOR_CACHE[cache_key]
    environment = ({"source": "A1", "target": "B2"}[role]) * 32
    coordinate_names = ("block_index",)
    action = SyntheticAction(
        f"unit_cpu_survivor_e1_{role}_a", _payload("action", f"{role}_a")
    )
    vocabulary = ResponseVocabularyId.from_coordinate_names(coordinate_names)
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_digest = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_{name}",
            payload=_payload("state", f"{role}_{name}"),
            totalized_kind=TotalizedStatus.OPEN,
            response_coordinates=(ExactRational(coordinate),),
            frame_digest=frame_digest,
        )
        for name, coordinate in open_coordinates.items()
    ) + (
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_CLOSED",
            payload=_payload("state", f"{role}_CLOSED"),
            totalized_kind=TotalizedStatus.CLOSED,
            response_coordinates=(ExactRational(2),),
            frame_digest=frame_digest,
        ),
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_SINK",
            payload=_payload("state", f"{role}_SINK"),
            totalized_kind=TotalizedStatus.SINK,
            response_coordinates=(ExactRational(3),),
            frame_digest=frame_digest,
        ),
    )
    rows = tuple(
        SyntheticTransitionRow(
            source_state_id=state.state_id,
            action_id=action.action_id,
            target_state_id=state.state_id,
            transition_semantics_digest=semantics.semantics_digest,
        )
        for state in states
    )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=coordinate_names,
        seed_state_ids=tuple(
            state.state_id
            for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=rows,
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    certificate = refine_exact_partition(admitted)
    verified = verify_exact_partition(admitted, certificate)
    result = build_exact_quotient_coordinate_generator(verified)
    _GENERATOR_CACHE[cache_key] = result
    return result


def _id(role: str, name: str) -> str:
    return f"unit_cpu_survivor_e1_{role}_{name}"


@lru_cache(maxsize=2)
def _bundle(*, extension: bool = False):
    source_coordinates = {"s0": 0, "s1": 0, "s2": 1}
    if extension:
        source_coordinates["s3"] = 0
    source = _generator("source", source_coordinates)
    target = _generator("target", {"t0": 0, "t1": 0, "t2": 1})
    coefficients = [
        (_id("target", "t0"), _id("source", "s0"), ExactRational(1)),
        (_id("target", "t0"), _id("source", "s1"), ExactRational(-2)),
        (_id("target", "t1"), _id("source", "s1"), ExactRational(1)),
        (_id("target", "t1"), _id("source", "s2"), ExactRational(1, 2)),
        (_id("target", "t2"), _id("source", "s0"), ExactRational(3)),
        (_id("target", "t2"), _id("source", "s2"), ExactRational(-1)),
    ]
    if extension:
        coefficients.extend(
            (
                (_id("target", "t1"), _id("source", "s3"), ExactRational(4)),
                (_id("target", "t2"), _id("source", "s3"), ExactRational(1)),
            )
        )
    layer = declare_synthetic_transfer_layer(source, target, tuple(coefficients))
    source_weights = {
        _id("source", "s0"): ExactRational(1),
        _id("source", "s1"): ExactRational(2),
        _id("source", "s2"): ExactRational(1),
        _id("source", "CLOSED"): ExactRational(1),
        _id("source", "SINK"): ExactRational(1),
    }
    law = {
        _id("source", "s0"): ExactRational(1, 3),
        _id("source", "s1"): ExactRational(2, 3),
        _id("source", "s2"): ExactRational(1),
        _id("source", "CLOSED"): ExactRational(1),
        _id("source", "SINK"): ExactRational(1),
    }
    if extension:
        source_weights[_id("source", "s3")] = ExactRational(1)
        law.update(
            {
                _id("source", "s0"): ExactRational(1, 6),
                _id("source", "s1"): ExactRational(1, 3),
                _id("source", "s3"): ExactRational(1, 2),
            }
        )
    target_weights = {
        _id("target", "t0"): ExactRational(2),
        _id("target", "t1"): ExactRational(1),
        _id("target", "t2"): ExactRational(3),
        _id("target", "CLOSED"): ExactRational(1),
        _id("target", "SINK"): ExactRational(1),
    }
    sw = make_positive_fiber_weights(source, source_weights)
    tw = make_positive_fiber_weights(target, target_weights)
    mu = make_exact_finite_fiber_law(source, law)
    sc = certify_fiber_completeness(layer, "source")
    tc = certify_fiber_completeness(layer, "target")
    envelope = build_fiber_envelope(layer, sw, tw, mu, sc, tc)
    return source, target, layer, sw, tw, mu, sc, tc, envelope


@lru_cache(maxsize=2)
def _layer_wire(*, extension: bool = False) -> dict:
    return _bundle(extension=extension)[2].to_dict()


@lru_cache(maxsize=2)
def _envelope_wire(*, extension: bool = False) -> dict:
    return _bundle(extension=extension)[-1].to_dict()


@lru_cache(maxsize=2)
def _source_weights_wire(*, extension: bool = False) -> dict:
    return _bundle(extension=extension)[3].to_dict()


@lru_cache(maxsize=2)
def _source_law_wire(*, extension: bool = False) -> dict:
    return _bundle(extension=extension)[5].to_dict()


@lru_cache(maxsize=1)
def _t0_bundle():
    source = _generator("source", {"OPEN": 0})
    target = _generator("target", {"OPEN": 0})
    layer = declare_synthetic_transfer_layer(
        source,
        target,
        ((_id("target", "OPEN"), _id("source", "OPEN"), ExactRational(10)),),
    )
    sw = make_positive_fiber_weights(
        source,
        {
            _id("source", "OPEN"): ExactRational(100),
            _id("source", "CLOSED"): ExactRational(1),
            _id("source", "SINK"): ExactRational(1),
        },
    )
    tw = make_positive_fiber_weights(
        target,
        {
            _id("target", "OPEN"): ExactRational(1),
            _id("target", "CLOSED"): ExactRational(1),
            _id("target", "SINK"): ExactRational(1),
        },
    )
    mu = make_exact_finite_fiber_law(
        source,
        {
            member: ExactRational(1)
            for member in (
                _id("source", "OPEN"),
                _id("source", "CLOSED"),
                _id("source", "SINK"),
            )
        },
    )
    sc = certify_fiber_completeness(layer, "source")
    tc = certify_fiber_completeness(layer, "target")
    envelope = build_fiber_envelope(layer, sw, tw, mu, sc, tc)
    return source, target, layer, sw, tw, mu, sc, tc, envelope


@lru_cache(maxsize=1)
def _t0_layer_wire() -> dict:
    return _t0_bundle()[2].to_dict()


@lru_cache(maxsize=1)
def _t0_envelope_wire() -> dict:
    return _t0_bundle()[-1].to_dict()


@lru_cache(maxsize=1)
def _t0_source_weights_wire() -> dict:
    return _t0_bundle()[3].to_dict()


@lru_cache(maxsize=1)
def _t0_source_law_wire() -> dict:
    return _t0_bundle()[5].to_dict()


def _block(frame: dict, member: str) -> int:
    for block in frame["blocks"]:
        if member in {row["member_id"] for row in block["members"]}:
            return block["block_index"]
    raise AssertionError(member)


def _cell(wire: dict, target: int, source: int) -> dict:
    return next(
        row for row in wire["cells"]
        if row["target_block_index"] == target
        and row["source_block_index"] == source
    )


def _r(value: dict) -> ExactRational:
    return ExactRational.from_dict(value)


def test_t0_w_corrected_weighted_lifting_and_envelope() -> None:
    _source, _target, layer, sw, _tw, mu, _sc, _tc, _envelope = _t0_bundle()
    compression = make_weighted_compression(sw)
    lifting = make_weighted_lifting(sw, mu)
    assert compression.compress(lifting.lift((ExactRational(7), ExactRational(0), ExactRational(0)))) == (
        ExactRational(7), ExactRational(0), ExactRational(0)
    )
    wire = _t0_envelope_wire()
    layer_wire = _t0_layer_wire()
    q_open = _block(layer_wire["source_frame"], _id("source", "OPEN"))
    r_open = _block(layer_wire["target_frame"], _id("target", "OPEN"))
    cell = _cell(wire, r_open, q_open)
    assert _r(cell["majorant"]) == ExactRational(1, 10)
    assert _r(cell["compressed_coefficient"]) == ExactRational(1, 10)
    assert wire["block_pair_count"] == wire["candidate_load_count"] == wire["work_count"] == 9


def test_two_fiber_certificate_matches_frozen_independent_values() -> None:
    *_, layer, sw, tw, mu, sc, tc, envelope = _bundle(extension=False)
    wire = _envelope_wire()
    layer_wire = _layer_wire()
    source_frame = layer_wire["source_frame"]
    target_frame = layer_wire["target_frame"]
    q0 = _block(source_frame, _id("source", "s0"))
    q1 = _block(source_frame, _id("source", "s2"))
    r0 = _block(target_frame, _id("target", "t0"))
    r1 = _block(target_frame, _id("target", "t2"))
    lifting = make_weighted_lifting(sw, mu)
    compression = make_weighted_compression(sw)
    block_vector = {
        block["block_index"]: ExactRational(
            6 if block["block_index"] == q0 else 0
        )
        for block in source_frame["blocks"]
    }
    lifted = lifting.lift(block_vector)
    lifted_by_member = dict(zip(
        (
            row["member_id"]
            for block in source_frame["blocks"]
            for row in block["members"]
        ),
        lifted,
        strict=True,
    ))
    assert lifted_by_member[_id("source", "s0")] == ExactRational(2)
    assert lifted_by_member[_id("source", "s1")] == ExactRational(2)
    assert compression.compress(lifted)[q0] == ExactRational(6)
    expected = {
        (r0, q0): (ExactRational(5, 2), ExactRational(-1, 3), _id("source", "s1")),
        (r0, q1): (ExactRational(1, 2), ExactRational(1, 2), _id("source", "s2")),
        (r1, q0): (ExactRational(9), ExactRational(3), _id("source", "s0")),
        (r1, q1): (ExactRational(3), ExactRational(-3), _id("source", "s2")),
    }
    for key, (majorant, compressed, maximizer) in expected.items():
        cell = _cell(wire, *key)
        assert _r(cell["majorant"]) == majorant
        assert _r(cell["compressed_coefficient"]) == compressed
        assert cell["maximizing_source_member_id"] == maximizer
    assert layer_wire["sparse_cell_count"] == 6
    assert layer_wire["rectangular_key_universe_count"] == 25
    assert wire["block_pair_count"] == 16
    assert wire["candidate_load_count"] == 20
    assert wire["work_count"] == 25
    # Literal oracle: all 16 cells and all 20 candidate loads are recomputed
    # from the frozen table without calling any production envelope helper.
    a = {
        (_id("target", "t0"), _id("source", "s0")): Fraction(1),
        (_id("target", "t0"), _id("source", "s1")): Fraction(-2),
        (_id("target", "t1"), _id("source", "s1")): Fraction(1),
        (_id("target", "t1"), _id("source", "s2")): Fraction(1, 2),
        (_id("target", "t2"), _id("source", "s0")): Fraction(3),
        (_id("target", "t2"), _id("source", "s2")): Fraction(-1),
    }
    omega_s = dict(zip(
        (_id("source", name) for name in ("s0", "s1", "s2", "CLOSED", "SINK")),
        (Fraction(1), Fraction(2), Fraction(1), Fraction(1), Fraction(1)),
        strict=True,
    ))
    omega_t = dict(zip(
        (_id("target", name) for name in ("t0", "t1", "t2", "CLOSED", "SINK")),
        (Fraction(2), Fraction(1), Fraction(3), Fraction(1), Fraction(1)),
        strict=True,
    ))
    law = dict(zip(
        (_id("source", name) for name in ("s0", "s1", "s2", "CLOSED", "SINK")),
        (Fraction(1, 3), Fraction(2, 3), Fraction(1), Fraction(1), Fraction(1)),
        strict=True,
    ))
    source_blocks = {
        block["block_index"]: tuple(row["member_id"] for row in block["members"])
        for block in source_frame["blocks"]
    }
    target_blocks = {
        block["block_index"]: tuple(row["member_id"] for row in block["members"])
        for block in target_frame["blocks"]
    }
    checked_loads = 0
    for certificate in wire["cells"]:
        sources = tuple(sorted(source_blocks[certificate["source_block_index"]]))
        targets = target_blocks[certificate["target_block_index"]]
        loads = {
            source_member: sum(
                abs(a.get((target_member, source_member), Fraction(0)))
                * omega_t[target_member] / omega_s[source_member]
                for target_member in targets
            )
            for source_member in sources
        }
        compressed = sum(
            law[source_member]
            * sum(
                a.get((target_member, source_member), Fraction(0))
                * omega_t[target_member]
                for target_member in targets
            ) / omega_s[source_member]
            for source_member in sources
        )
        majorant = max(loads.values())
        maximizer = next(member for member in sources if loads[member] == majorant)
        assert _r(certificate["majorant"]) == ExactRational(
            majorant.numerator, majorant.denominator
        )
        assert _r(certificate["compressed_coefficient"]) == ExactRational(
            compressed.numerator, compressed.denominator
        )
        assert certificate["maximizing_source_member_id"] == maximizer
        assert {
            row["source_member_id"]: _r(row["load"])
            for row in certificate["candidate_loads"]
        } == {
            member: ExactRational(value.numerator, value.denominator)
            for member, value in loads.items()
        }
        assert abs(compressed) <= majorant
        checked_loads += len(loads)
    assert checked_loads == 20


def test_strict_roundtrips_rederive_every_retained_authority() -> None:
    source, target, layer, sw, tw, mu, sc, tc, _envelope = _t0_bundle()
    sw_wire = _t0_source_weights_wire()
    mu_wire = _t0_source_law_wire()
    assert type(PositiveFiberWeights.from_dict(sw_wire, source)) is PositiveFiberWeights
    assert type(ExactFiniteFiberLaw.from_dict(mu_wire, source)) is ExactFiniteFiberLaw
    compression = make_weighted_compression(sw)
    lifting = make_weighted_lifting(sw, mu)
    compression_wire = compression.to_dict()
    lifting_wire = lifting.to_dict()
    assert type(WeightedCompression.from_dict(compression_wire, sw)) is WeightedCompression
    assert type(WeightedLifting.from_dict(lifting_wire, sw, mu)) is WeightedLifting
    layer_wire = _t0_layer_wire()
    assert type(type(layer).from_dict(layer_wire, source, target)) is type(layer)
    sc_wire = sc.to_dict()
    assert type(FiberCompletenessWitness.from_dict(sc_wire, layer)) is FiberCompletenessWitness
    membership = witness_domain_membership(sc, _id("source", "OPEN"))
    assert type(type(membership).from_dict(membership.to_dict(), sc)) is type(membership)
    envelope_wire = _t0_envelope_wire()
    assert type(FiberEnvelope.from_dict(
        envelope_wire, layer, sw, tw, mu, sc, tc
    )) is FiberEnvelope


def test_sparse_authority_and_certificate_undercoverage_attacks_fail_closed() -> None:
    source, target, layer, sw, tw, mu, sc, tc, envelope = _bundle(extension=False)
    rows = tuple(reversed(layer._coefficients))
    layer_wire = _layer_wire()
    assert declare_synthetic_transfer_layer(source, target, rows).to_dict() == layer_wire
    with pytest.raises(StrictContractError, match="duplicate"):
        declare_synthetic_transfer_layer(source, target, rows + (rows[0],))
    with pytest.raises(StrictContractError, match="zero"):
        declare_synthetic_transfer_layer(
            source, target,
            ((_id("target", "t0"), _id("source", "s2"), ExactRational(0)),),
        )
    attacked_layer_wire = copy.deepcopy(layer_wire)
    attacked_layer_wire["coefficients"].pop()
    with pytest.raises(StrictContractError):
        type(layer).from_dict(attacked_layer_wire, source, target)
    base_envelope_wire = _envelope_wire()
    for mutation in ("candidate", "extremizer", "majorant"):
        wire = copy.deepcopy(base_envelope_wire)
        source_frame = layer_wire["source_frame"]
        target_frame = layer_wire["target_frame"]
        q0 = _block(source_frame, _id("source", "s0"))
        r0 = _block(target_frame, _id("target", "t0"))
        attacked = _cell(wire, r0, q0)
        if mutation == "candidate":
            attacked["candidate_loads"][-1] = copy.deepcopy(
                attacked["candidate_loads"][0]
            )
        elif mutation == "extremizer":
            nonmax = next(
                row for row in attacked["candidate_loads"]
                if row["source_member_id"]
                != attacked["maximizing_source_member_id"]
            )
            attacked["maximizing_source_member_id"] = nonmax["source_member_id"]
            attacked["maximizing_source_member_sha256"] = nonmax[
                "source_member_sha256"
            ]
        else:
            attacked["majorant"] = ExactRational(0).to_dict()
        with pytest.raises(StrictContractError):
            FiberEnvelope.from_dict(wire, layer, sw, tw, mu, sc, tc)
    with pytest.raises(StrictContractError, match="outside"):
        witness_domain_membership(sc, "outside")


def test_observed_nominal_and_unsealed_capabilities_cannot_cross_e1_boundary() -> None:
    import test_odlrq_quotient_generator as qg_fixtures

    source, target, layer, sw, tw, mu, sc, tc, envelope = _bundle(extension=False)
    row = IntervalTargetRow(0, "unit_cpu_survivor_e1_source_a", (0,))
    observed = ObservedIntervalOperator("e1_observed", (row,))
    nominal = NominalOperator("e1_nominal", (row,))
    _verified, exact_operator, _candidate, _evidence, _witness, certified = (
        qg_fixtures._read_only_bundle()
    )
    for invalid in (observed, nominal, exact_operator, certified):
        with pytest.raises(StrictContractError):
            declare_synthetic_transfer_layer(invalid, target, ())  # type: ignore[arg-type]
        with pytest.raises(StrictContractError):
            declare_synthetic_transfer_layer(source, invalid, ())  # type: ignore[arg-type]
    promoted = copy.deepcopy(sw.to_dict())
    promoted["evidence_scope"] = "observed_interval_development"
    with pytest.raises(StrictContractError, match="schema/scope"):
        PositiveFiberWeights.from_dict(promoted, source)
    membership = witness_domain_membership(sc, _id("source", "s0"))
    for capability in (
        PositiveFiberWeights, ExactFiniteFiberLaw, WeightedCompression,
        WeightedLifting, type(layer), FiberCompletenessWitness,
        type(membership),
        FiberEnvelope, FiberInclusionWitness,
    ):
        with pytest.raises(StrictContractError):
            capability()  # type: ignore[call-arg]
    attacked = copy.copy(sw)
    object.__setattr__(attacked, "_values", tuple(ExactRational(1) for _ in attacked._values))
    with pytest.raises(StrictContractError):
        attacked.to_dict()
    with pytest.raises(StrictContractError):
        attacked.weight_for(_id("source", "s1"))
    attacked_law = copy.copy(mu)
    object.__setattr__(
        attacked_law,
        "_probabilities",
        (ExactRational(0),) + attacked_law._probabilities[1:],
    )
    with pytest.raises(StrictContractError):
        attacked_law.probability_for(_id("source", "s0"))
    attacked_membership = copy.copy(membership)
    object.__setattr__(attacked_membership, "_member_id", _id("source", "s1"))
    with pytest.raises(StrictContractError):
        attacked_membership.to_dict()
    attacked_compression = copy.copy(make_weighted_compression(sw))
    object.__setattr__(attacked_compression, "_weights", tw)
    with pytest.raises(StrictContractError):
        attacked_compression.to_dict()
    attacked_lifting = copy.copy(make_weighted_lifting(sw, mu))
    object.__setattr__(attacked_lifting, "_weights", tw)
    with pytest.raises(StrictContractError):
        attacked_lifting.to_dict()
    attacked_envelope = copy.copy(envelope)
    object.__setattr__(attacked_envelope, "_source_weights", tw)
    with pytest.raises(StrictContractError):
        _ = attacked_envelope.source_compression
    with pytest.raises(StrictContractError):
        _ = attacked_envelope.target_compression
    with pytest.raises(StrictContractError):
        _ = attacked_envelope.source_lifting


def test_fiber_extension_is_typed_and_cellwise_monotone() -> None:
    old_bundle = _bundle(extension=False)
    new_bundle = _bundle(extension=True)
    old = old_bundle[-1]
    new = new_bundle[-1]
    old_layer_wire = _layer_wire()
    old_source_frame = old_layer_wire["source_frame"]
    old_target_frame = old_layer_wire["target_frame"]
    source_injection = {
        row["member_id"]: row["member_id"]
        for block in old_source_frame["blocks"] for row in block["members"]
    }
    target_injection = {
        row["member_id"]: row["member_id"]
        for block in old_target_frame["blocks"] for row in block["members"]
    }
    strict = verify_fiber_inclusion(old, new, source_injection, target_injection)
    wire = strict.to_dict()
    assert wire["strict_cell_count"] == 1
    assert len(wire["cell_comparisons"]) > wire["strict_cell_count"]
    assert type(FiberInclusionWitness.from_dict(wire, old, new)) is FiberInclusionWitness
    assert wire["injected_rectangle_count"] == 25
    new_layer_wire = _layer_wire(extension=True)
    q0 = _block(new_layer_wire["source_frame"], _id("source", "s0"))
    r0 = _block(new_layer_wire["target_frame"], _id("target", "t0"))
    r1 = _block(new_layer_wire["target_frame"], _id("target", "t2"))
    comparisons = {
        (row["target_block_index"], row["source_block_index"]): row
        for row in wire["cell_comparisons"]
    }
    assert _r(comparisons[(r0, q0)]["old_majorant"]) == ExactRational(5, 2)
    assert _r(comparisons[(r0, q0)]["new_majorant"]) == ExactRational(4)
    assert comparisons[(r0, q0)]["strictly_increased"] is True
    assert _r(comparisons[(r1, q0)]["old_majorant"]) == ExactRational(9)
    assert _r(comparisons[(r1, q0)]["new_majorant"]) == ExactRational(9)
    assert comparisons[(r1, q0)]["strictly_increased"] is False


def test_fiber_inclusion_rejects_weight_and_member_identity_substitution() -> None:
    old_bundle = _bundle(extension=False)
    new_bundle = _bundle(extension=True)
    old, new = old_bundle[-1], new_bundle[-1]
    old_layer_wire = _layer_wire()
    source_members = [
        row["member_id"] for block in old_layer_wire["source_frame"]["blocks"]
        for row in block["members"]
    ]
    target_members = [
        row["member_id"] for block in old_layer_wire["target_frame"]["blocks"]
        for row in block["members"]
    ]
    source_map = {member: member for member in source_members}
    target_map = {member: member for member in target_members}
    wrong_map = dict(source_map)
    wrong_map[_id("source", "s0")] = _id("source", "s1")
    wrong_map[_id("source", "s1")] = _id("source", "s0")
    with pytest.raises(StrictContractError):
        verify_fiber_inclusion(old, new, wrong_map, target_map)

    source, target, layer, sw, tw, mu, sc, tc, _ = new_bundle
    changed = {
        row["member_id"]: ExactRational.from_dict(row["weight"])
        for row in _source_weights_wire(extension=True)["rows"]
    }
    changed[_id("source", "s0")] = ExactRational(2)
    changed_weights = make_positive_fiber_weights(source, changed)
    changed_envelope = build_fiber_envelope(layer, changed_weights, tw, mu, sc, tc)
    with pytest.raises(StrictContractError, match="weight"):
        verify_fiber_inclusion(old, changed_envelope, source_map, target_map)


def test_declared_fiber_authority_negative_matrix_fails_closed() -> None:
    source, target, layer, sw, tw, mu, sc, tc, _t0_envelope = _t0_bundle()
    weight_values = {
        row["member_id"]: _r(row["weight"])
        for row in _t0_source_weights_wire()["rows"]
    }
    for replacement in (ExactRational(0), ExactRational(-1)):
        attacked = dict(weight_values)
        attacked[_id("source", "OPEN")] = replacement
        with pytest.raises(StrictContractError):
            make_positive_fiber_weights(source, attacked)
    missing_weights = dict(weight_values)
    missing_weights.pop(_id("source", "OPEN"))
    with pytest.raises(StrictContractError):
        make_positive_fiber_weights(source, missing_weights)

    law_values = {
        row["member_id"]: _r(row["probability"])
        for row in _t0_source_law_wire()["rows"]
    }
    negative_law = dict(law_values)
    negative_law[_id("source", "OPEN")] = ExactRational(-1)
    wrong_sum_law = dict(law_values)
    wrong_sum_law[_id("source", "OPEN")] = ExactRational(1, 2)
    missing_law = dict(law_values)
    missing_law.pop(_id("source", "OPEN"))
    for attacked in (negative_law, wrong_sum_law, missing_law):
        with pytest.raises(StrictContractError):
            make_exact_finite_fiber_law(source, attacked)

    with pytest.raises(StrictContractError, match="distinct"):
        declare_synthetic_transfer_layer(source, source, ())
    with pytest.raises(StrictContractError, match="outside"):
        declare_synthetic_transfer_layer(
            source,
            target,
            (("outside", _id("source", "OPEN"), ExactRational(1)),),
        )

    target_law_values: dict[str, ExactRational] = {}
    for block in _t0_layer_wire()["target_frame"]["blocks"]:
        for position, row in enumerate(block["members"]):
            target_law_values[row["member_id"]] = ExactRational(
                1 if position == 0 else 0
            )
    wrong_frame_law = make_exact_finite_fiber_law(target, target_law_values)
    for authorities in (
        (tw, tw, mu, sc, tc),
        (sw, tw, wrong_frame_law, sc, tc),
        (sw, tw, mu, tc, tc),
        (sw, tw, mu, sc, sc),
    ):
        with pytest.raises(StrictContractError):
            build_fiber_envelope(layer, *authorities)

    (
        _old_source,
        _old_target,
        _old_layer,
        _old_sw,
        _old_tw,
        _old_mu,
        _old_sc,
        _old_tc,
        old,
    ) = _bundle(extension=False)
    (
        new_source,
        new_target,
        new_layer,
        new_sw,
        new_tw,
        new_mu,
        _new_sc,
        _new_tc,
        _new_envelope,
    ) = _bundle(extension=True)
    modified_coefficients = list(new_layer._coefficients)
    modified_coefficients[modified_coefficients.index(
        (_id("target", "t0"), _id("source", "s0"), ExactRational(1))
    )] = (_id("target", "t0"), _id("source", "s0"), ExactRational(2))
    modified_layer = declare_synthetic_transfer_layer(
        new_source, new_target, tuple(modified_coefficients)
    )
    modified_sc = certify_fiber_completeness(modified_layer, "source")
    modified_tc = certify_fiber_completeness(modified_layer, "target")
    modified_envelope = build_fiber_envelope(
        modified_layer,
        new_sw,
        new_tw,
        new_mu,
        modified_sc,
        modified_tc,
    )
    old_layer_wire = _layer_wire()
    source_injection = {
        row["member_id"]: row["member_id"]
        for block in old_layer_wire["source_frame"]["blocks"]
        for row in block["members"]
    }
    target_injection = {
        row["member_id"]: row["member_id"]
        for block in old_layer_wire["target_frame"]["blocks"]
        for row in block["members"]
    }
    with pytest.raises(StrictContractError, match="transfer cell"):
        verify_fiber_inclusion(
            old, modified_envelope, source_injection, target_injection
        )


def test_nested_caps_reject_before_expensive_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import lean_rgc.odlrq.envelope as envelope_module
    import lean_rgc.odlrq.quotient_generator as quotient_module

    source, target, layer, sw, _tw, mu, sc, _tc, envelope = _t0_bundle()
    law_wire = copy.deepcopy(_t0_source_law_wire())
    law_wire["block_sums"] = [{}] * 65
    lifting_wire = copy.deepcopy(make_weighted_lifting(sw, mu).to_dict())
    lifting_wire["roundtrip_identity_checks"] = [{}] * 65
    layer_wire = copy.deepcopy(_t0_layer_wire())
    layer_wire["source_frame"]["block_count"] = 65
    layer_wire["source_frame"]["blocks"] = [{}] * 65
    completeness_wire = copy.deepcopy(sc.to_dict())
    completeness_wire["frame"]["block_count"] = 65
    completeness_wire["frame"]["blocks"] = [{}] * 65
    envelope_wire = copy.deepcopy(_t0_envelope_wire())
    envelope_wire["cells"][0]["candidate_loads"] = [{}] * 129
    inclusion_wire = {
        "schema_version": "odlrq_fiber_inclusion_witness_v1",
        "evidence_scope": "synthetic_development",
        "old_envelope_sha256": "A" * 64,
        "new_envelope_sha256": "B" * 64,
        "source_injection": [],
        "target_injection": [],
        "injected_rectangle_count": 0,
        "cell_comparisons": [{}] * 4_097,
        "strict_cell_count": 0,
        "monotone": True,
    }

    def authority_reached(*_args, **_kwargs):
        raise AssertionError("expensive authority reached before nested cap")

    monkeypatch.setattr(quotient_module, "_fresh_fiber_frame", authority_reached)
    monkeypatch.setattr(envelope_module, "_fresh_fiber_frame", authority_reached)
    monkeypatch.setattr(
        envelope_module, "_retained_frame_preflight", authority_reached
    )
    with pytest.raises(StrictContractError):
        make_positive_fiber_weights(source, [ExactRational(1)] * 129)
    with pytest.raises(StrictContractError):
        make_exact_finite_fiber_law(source, [ExactRational(1)] * 129)
    with pytest.raises(StrictContractError):
        declare_synthetic_transfer_layer(source, target, [()] * 4_097)
    with pytest.raises(StrictContractError):
        verify_fiber_inclusion(
            envelope,
            envelope,
            {f"oversized-{index}": "x" for index in range(129)},
            {},
        )
    with pytest.raises(StrictContractError):
        ExactFiniteFiberLaw.from_dict(law_wire, source)
    with pytest.raises(StrictContractError):
        WeightedLifting.from_dict(lifting_wire, sw, mu)
    with pytest.raises(StrictContractError):
        type(layer).from_dict(layer_wire, source, target)
    with pytest.raises(StrictContractError):
        FiberCompletenessWitness.from_dict(completeness_wire, layer)
    with pytest.raises(StrictContractError):
        FiberEnvelope.from_dict(envelope_wire, layer, sw, _tw, mu, sc, _tc)
    with pytest.raises(StrictContractError):
        FiberInclusionWitness.from_dict(inclusion_wire, envelope, envelope)
