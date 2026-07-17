from __future__ import annotations

import copy
from fractions import Fraction
from functools import lru_cache
import hashlib
import inspect
import json

import pytest

import lean_rgc.odlrq as odlrq
from lean_rgc.odlrq import (
    CanonicalPayload,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    admit_synthetic_finite_snapshot,
    build_exact_quotient_coordinate_generator,
    build_fiber_envelope,
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    certify_fiber_completeness,
    declare_synthetic_transfer_layer,
    make_exact_finite_fiber_law,
    make_positive_fiber_weights,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
    refine_exact_partition,
    verify_exact_partition,
)
from lean_rgc.odlrq import certificates as e2c
from lean_rgc.odlrq import maxent as me
from lean_rgc.odlrq import selection as e2s
from lean_rgc.odlrq import similarity as s0


ACCEPTED_E1_ENVELOPE_SHA256 = (
    "D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6"
)
E2_M0_ENVELOPE_SHA256 = (
    "9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C"
)
E2_TOKEN_SHA256 = (
    "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"
)
ME0_PROBLEM_SHA256 = (
    "F055C10309DB4AFCA1A140ECFE3FAAF3AF2BF11F7B25F6366F92667446899B7B"
)
ME0_RESULT_SHA256 = (
    "DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3"
)
PRIMITIVE_UNIVERSE_SHA256 = (
    "9FA1D0431DF67EEDD0661EE70A0836A60ECF6153488EDE21699DD24867722FEC"
)

# This is the accepted public E2 contract wire, not a test-helper import.  It is
# parsed and rebound through ME0's public production constructor below.  The
# expensive E2 proof-object construction is tested at E2; rebuilding all three
# parents here would violate S0's frozen 30-second lane.
_E2_TOKEN_JSON = r'''{"abstained_candidate_ids":[],"candidate_universe_manifest_sha256":"327DDC3DBD63C049A1B16B570B81F5DDECCE1B8C3C7F83734609C83B12501D9A","comparator":"exact_rational_less_equal_v1","coverage":{"denominator":"3","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"decision_rows":[{"authority_bundle_sha256":"6B29E9EC02EBBC4C36A1AD4B9A485E54954D05345E4DCB8BE2135A3D61B6BF2C","bound":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c0","decision":"ACCEPT","reason":"BOUND_LE_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"authority_bundle_sha256":"AF2491D9640434CFD7798465887A28138F2879C7C31608C204F12A4E53E6630E","bound":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c1","decision":"REJECT","reason":"BOUND_GT_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"authority_bundle_sha256":"FF2C37D9A917559DC759512162EA82E72A5CED7F558EF624A577876F152F97C4","bound":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c2","decision":"ACCEPT","reason":"BOUND_LE_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"denominator":3,"endpoint_id":"u24_e2_declared_square_endpoint_v1","gated_ranking":["c2","c0"],"invalidation_sha256":"B83E0F2608123C8EAC140332DA5F00E5B2F293229EC44D6087628B93DBF591EB","numerator":2,"p1_cocycle_sha256":"6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11","p2_cocycle_sha256":"BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D","ranking_changed":true,"rejected_candidate_ids":["c1"],"return_memory_bound_sha256":"95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46","schema_version":"odlrq.e2.certified-support-token.v1","support_candidate_ids":["c0","c2"],"threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"ungated_ranking":["c1","c2","c0"],"verification_disposition":"E2_BINDING_SUPPORT_CERTIFIED"}'''

_NODE_IDS = ("n0", "n1")
_EDGE_IDS = (("n0", "n0"), ("n0", "n1"), ("n1", "n1"))
_PRIMITIVE_IDS = (
    "u24_s0_t0_node0",
    "u24_s0_t1_node1_edge01",
    "u24_s0_t2_edge11",
    "u24_s0_t3_ghost_return",
)

_S0_PUBLIC_TYPES = (
    "ApproximationLevelId",
    "PrimitiveTargetRow",
    "CountedCoverageWitness",
    "DeclaredS0HardAuthorityReference",
    "LiveS0HardAuthorityBinding",
    "DeclaredME0ResultReference",
    "LiveME0ResultBinding",
    "DeclaredSyntheticLPlusToken",
    "TargetResidualBound",
    "GlobalMeasure",
    "PredictiveDistance",
    "PositiveDistance",
    "RadiusMorphism",
    "WordDepthMorphism",
    "GranularityMorphism",
    "LocalTower",
    "PredictiveTransportCertificate",
    "PositiveTransportCertificate",
    "FiniteRemainderCertificate",
    "SimilarityCertificate",
    "DeclaredSyntheticSimilarityFixture",
)
_S0_PUBLIC_ENDPOINTS = (
    "make_declared_s0_hard_authority_reference",
    "bind_s0_hard_authorities",
    "make_declared_me0_result_reference",
    "bind_me0_result",
    "declare_synthetic_l_plus",
    "make_counted_coverage_witness",
    "make_target_residual_bound",
    "make_global_measure",
    "compute_predictive_distance",
    "compute_positive_distance",
    "make_radius_morphism",
    "make_word_depth_morphism",
    "make_granularity_morphism",
    "build_local_tower",
    "verify_predictive_transport",
    "verify_positive_transport",
    "certify_finite_remainder",
    "build_declared_synthetic_similarity_fixture",
    "verify_similarity_certificate",
    "verify_similarity_certificate_live",
)
_S0_PUBLIC_SURFACE = _S0_PUBLIC_TYPES + _S0_PUBLIC_ENDPOINTS


def _r(n: int, d: int = 1) -> ExactRational:
    return ExactRational(n, d)


def _sha(value: object) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


@lru_cache(maxsize=2)
def _e1_generator(role: str, coordinates: tuple[tuple[str, int], ...]):
    environment = ({"source": "A1", "target": "B2"}[role]) * 32
    action = SyntheticAction(
        f"unit_cpu_survivor_e1_{role}_a", _payload("action", f"{role}_a")
    )
    vocabulary = ResponseVocabularyId.from_coordinate_names(("block_index",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_sha = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_{name}",
            payload=_payload("state", f"{role}_{name}"),
            totalized_kind=TotalizedStatus.OPEN,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for name, coordinate in coordinates
    ) + tuple(
        SyntheticTotalizedState(
            state_id=f"unit_cpu_survivor_e1_{role}_{name}",
            payload=_payload("state", f"{role}_{name}"),
            totalized_kind=status,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for name, status, coordinate in (
            ("CLOSED", TotalizedStatus.CLOSED, 2),
            ("SINK", TotalizedStatus.SINK, 3),
        )
    )
    transitions = tuple(
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
        coordinate_names=("block_index",),
        seed_state_ids=tuple(
            state.state_id
            for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=transitions,
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    return build_exact_quotient_coordinate_generator(
        verify_exact_partition(admitted, refine_exact_partition(admitted))
    )


def _e1_id(role: str, name: str) -> str:
    return f"unit_cpu_survivor_e1_{role}_{name}"


@lru_cache(maxsize=1)
def _accepted_e1_envelope():
    source = _e1_generator("source", (("s0", 0), ("s1", 0), ("s2", 1)))
    target = _e1_generator("target", (("t0", 0), ("t1", 0), ("t2", 1)))
    layer = declare_synthetic_transfer_layer(
        source,
        target,
        (
            (_e1_id("target", "t0"), _e1_id("source", "s0"), _r(1)),
            (_e1_id("target", "t0"), _e1_id("source", "s1"), _r(-2)),
            (_e1_id("target", "t1"), _e1_id("source", "s1"), _r(1)),
            (_e1_id("target", "t1"), _e1_id("source", "s2"), _r(1, 2)),
            (_e1_id("target", "t2"), _e1_id("source", "s0"), _r(3)),
            (_e1_id("target", "t2"), _e1_id("source", "s2"), _r(-1)),
        ),
    )
    source_weights = make_positive_fiber_weights(
        source,
        {
            _e1_id("source", "s0"): _r(1),
            _e1_id("source", "s1"): _r(2),
            _e1_id("source", "s2"): _r(1),
            _e1_id("source", "CLOSED"): _r(1),
            _e1_id("source", "SINK"): _r(1),
        },
    )
    target_weights = make_positive_fiber_weights(
        target,
        {
            _e1_id("target", "t0"): _r(2),
            _e1_id("target", "t1"): _r(1),
            _e1_id("target", "t2"): _r(3),
            _e1_id("target", "CLOSED"): _r(1),
            _e1_id("target", "SINK"): _r(1),
        },
    )
    law = make_exact_finite_fiber_law(
        source,
        {
            _e1_id("source", "s0"): _r(1, 3),
            _e1_id("source", "s1"): _r(2, 3),
            _e1_id("source", "s2"): _r(1),
            _e1_id("source", "CLOSED"): _r(1),
            _e1_id("source", "SINK"): _r(1),
        },
    )
    result = build_fiber_envelope(
        layer,
        source_weights,
        target_weights,
        law,
        certify_fiber_completeness(layer, "source"),
        certify_fiber_completeness(layer, "target"),
    )
    assert len(canonical_contract_bytes(result)) == 16351
    assert _sha(result) == ACCEPTED_E1_ENVELOPE_SHA256
    return result


_E2_MATRICES = {
    "M0": ((1, 2), (0, Fraction(1, 2))),
    "M1": ((Fraction(1, 2), 0), (3, 1)),
    "MRET": ((0, 2), (3, Fraction(1, 2))),
}
_E2_CACHE: dict[object, object] = {}


@lru_cache(maxsize=2)
def _e2_side(side: str):
    if side == "source":
        environment = "53" * 32
        action_id = "unit_cpu_survivor_u24_e2_source_a"
        specs = (
            ("unit_cpu_survivor_u24_e2_source_open0_a", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open0_b", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_source_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_source_sink", TotalizedStatus.SINK, 3),
        )
    else:
        environment = "54" * 32
        action_id = "unit_cpu_survivor_u24_e2_target_a"
        specs = (
            ("unit_cpu_survivor_u24_e2_target_open0", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_target_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_target_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_target_sink", TotalizedStatus.SINK, 3),
        )
    action = SyntheticAction(action_id, _payload("action", action_id))
    vocabulary = ResponseVocabularyId.from_coordinate_names(("e2_coordinate",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_sha = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=state_id,
            payload=_payload("state", state_id),
            totalized_kind=status,
            response_coordinates=(_r(coordinate),),
            frame_digest=frame_sha,
        )
        for state_id, status, coordinate in specs
    )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=("e2_coordinate",),
        seed_state_ids=tuple(
            state.state_id
            for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=tuple(
            SyntheticTransitionRow(
                source_state_id=state.state_id,
                action_id=action.action_id,
                target_state_id=state.state_id,
                transition_semantics_digest=semantics.semantics_digest,
            )
            for state in states
        ),
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    generator = build_exact_quotient_coordinate_generator(
        verify_exact_partition(admitted, refine_exact_partition(admitted))
    )
    return generator, states


def _e2_parent(selector: str) -> dict[str, object]:
    if selector in _E2_CACHE:
        return _E2_CACHE[selector]  # type: ignore[return-value]
    source, source_states = _e2_side("source")
    target, target_states = _e2_side("target")
    matrix = _E2_MATRICES[selector]
    coefficients = []
    source_ids = (
        "unit_cpu_survivor_u24_e2_source_open0_a",
        "unit_cpu_survivor_u24_e2_source_open0_b",
        "unit_cpu_survivor_u24_e2_source_open1",
    )
    target_ids = (
        "unit_cpu_survivor_u24_e2_target_open0",
        "unit_cpu_survivor_u24_e2_target_open1",
    )
    for target_index, target_id in enumerate(target_ids):
        for source_id, coefficient in (
            (source_ids[0], matrix[target_index][0]),
            (source_ids[1], -matrix[target_index][0]),
            (source_ids[2], matrix[target_index][1]),
        ):
            coefficient = Fraction(coefficient)
            if coefficient:
                coefficients.append(
                    (target_id, source_id, _r(coefficient.numerator, coefficient.denominator))
                )
    layer = declare_synthetic_transfer_layer(source, target, tuple(coefficients))
    sw = make_positive_fiber_weights(
        source, {state.state_id: _r(1) for state in source_states}
    )
    tw = make_positive_fiber_weights(
        target, {state.state_id: _r(1) for state in target_states}
    )
    probabilities = {state.state_id: _r(1) for state in source_states}
    probabilities[source_ids[0]] = _r(1, 3)
    probabilities[source_ids[1]] = _r(2, 3)
    law = make_exact_finite_fiber_law(source, probabilities)
    sc = certify_fiber_completeness(layer, "source")
    tc = certify_fiber_completeness(layer, "target")
    envelope = build_fiber_envelope(layer, sw, tw, law, sc, tc)
    result = {
        "source_generator": source,
        "target_generator": target,
        "layer": layer,
        "source_weights": sw,
        "target_weights": tw,
        "source_law": law,
        "source_completeness": sc,
        "target_completeness": tc,
        "envelope": envelope,
    }
    _E2_CACHE[selector] = result
    return result


def _e2_identification(selector: str):
    key = ("identification", selector)
    if key not in _E2_CACHE:
        p = _e2_parent(selector)
        _E2_CACHE[key] = e2c.identify_e2_source_target_coordinates(
            envelope=p["envelope"],
            layer=p["layer"],
            source_generator=p["source_generator"],
            target_generator=p["target_generator"],
            source_weights=p["source_weights"],
            target_weights=p["target_weights"],
            source_law=p["source_law"],
            source_completeness=p["source_completeness"],
            target_completeness=p["target_completeness"],
        )
    return _E2_CACHE[key]


def _e2_restriction(selector: str):
    key = ("restriction", selector)
    if key not in _E2_CACHE:
        _E2_CACHE[key] = e2c.build_e2_envelope_restriction(
            envelope=_e2_parent(selector)["envelope"],
            identification=_e2_identification(selector),
        )
    return _E2_CACHE[key]


def _e2_safety(selector: str):
    key = ("safety", selector)
    if key not in _E2_CACHE:
        p = _e2_parent(selector)
        _E2_CACHE[key] = e2c.certify_e2_lifting_uniform_safety(
            envelope=p["envelope"],
            identification=_e2_identification(selector),
            restriction=_e2_restriction(selector),
        )
    return _E2_CACHE[key]


def _e2_cocycle(channel: str):
    key = ("cocycle", channel)
    if key not in _E2_CACHE:
        _E2_CACHE[key] = e2c.certify_e2_cocycle(
            channel=channel,
            first=_e2_restriction("M0"),
            second=_e2_restriction("M1"),
        )
    return _E2_CACHE[key]


def _e2_return_memory():
    if "return" not in _E2_CACHE:
        split = e2c.resolve_e2_memory_split(restriction=_e2_restriction("MRET"))
        _E2_CACHE["return"] = e2c.bound_e2_finite_return_memory(
            restriction=_e2_restriction("MRET"), split=split
        )
    return _E2_CACHE["return"]


@lru_cache(maxsize=1)
def _e2_token():
    manifest = e2s.build_declared_e2_candidate_universe(
        m0_identification=_e2_identification("M0"),
        m0_restriction=_e2_restriction("M0"),
        m0_safety=_e2_safety("M0"),
        m1_identification=_e2_identification("M1"),
        m1_restriction=_e2_restriction("M1"),
        m1_safety=_e2_safety("M1"),
    )
    token = e2s.apply_e2_binding_gate(
        manifest=manifest,
        p1_cocycle=_e2_cocycle("P1_BRANCHING_ADJUSTED"),
        p2_cocycle=_e2_cocycle("P2_BRANCHING_ADJUSTED"),
        return_memory=_e2_return_memory(),
    )
    assert _sha(_e2_parent("M0")["envelope"]) == E2_M0_ENVELOPE_SHA256
    assert _sha(token) == E2_TOKEN_SHA256
    return token


@lru_cache(maxsize=1)
def _me0_objects():
    reference = me.make_declared_e2_support_reference(
        json.loads(_E2_TOKEN_JSON),
        accepted_e2_commit_sha="7a8b28872439dd61d40174c2500c5990790002be",
        accepted_e2_tree_sha="d54ed9fab52da4929843fabdeb3c1e1920994f6a",
    )
    problem = me.MaxEntProblem.create(
        reference,
        reference_mass_rows=(("c0", _r(1, 2)), ("c2", _r(1, 2))),
        statistic_rows=(("c0", (_r(0),)), ("c2", (_r(2),))),
        orbit_size_rows=(("c0", 1), ("c2", 2)),
        target=(_r(4, 5),),
        kl_radius=_r(1, 20),
        row_load_rows=(("c0", _r(1)), ("c2", _r(3))),
        nominal_operator_rows=(("c0", _r(2)), ("c2", _r(4))),
        exact_rule_column_ids=("g0",),
        exact_rule_rows=(("c0", (_r(1),)), ("c2", (_r(2),))),
    )
    result = me.solve_finite_fiber_maxent(problem)
    assert _sha(problem) == ME0_PROBLEM_SHA256
    assert _sha(result) == ME0_RESULT_SHA256
    return problem, result


def _primitive_rows():
    return (
        s0.PrimitiveTargetRow(
            primitive_id=_PRIMITIVE_IDS[0],
            node_load=(_r(1), _r(0)),
            edge_load=(_r(1), _r(0), _r(0)),
            target_residual=_r(1, 8),
        ),
        s0.PrimitiveTargetRow(
            primitive_id=_PRIMITIVE_IDS[1],
            node_load=(_r(0), _r(2)),
            edge_load=(_r(0), _r(1), _r(0)),
            target_residual=_r(1, 8),
        ),
        s0.PrimitiveTargetRow(
            primitive_id=_PRIMITIVE_IDS[2],
            node_load=(_r(0), _r(0)),
            edge_load=(_r(0), _r(0), _r(2)),
            target_residual=_r(1, 8),
        ),
        s0.PrimitiveTargetRow(
            primitive_id=_PRIMITIVE_IDS[3],
            node_load=(_r(0), _r(0)),
            edge_load=(_r(0), _r(0), _r(0)),
            target_residual=_r(1, 8),
        ),
    )


@lru_cache(maxsize=1)
def _s0_fixture():
    hard_reference = s0.make_declared_s0_hard_authority_reference(
        primitive_rows=_primitive_rows()
    )
    problem, result = _me0_objects()
    me0_reference = s0.make_declared_me0_result_reference(
        problem_wire=problem.to_dict(), result_wire=result.to_dict()
    )
    fixture = s0.build_declared_synthetic_similarity_fixture(
        hard_reference=hard_reference, me0_reference=me0_reference
    )
    assert _sha({
        "schema_version": "odlrq.s0.primitive-universe.v2",
        "node_ids": list(_NODE_IDS),
        "edge_ids": [list(edge) for edge in _EDGE_IDS],
        "edge_orientation": "unordered_canonical_pair_v1",
        "rows": [row.to_dict() for row in _primitive_rows()],
    }) == PRIMITIVE_UNIVERSE_SHA256
    return fixture


def _wire_rows_by_id(rows: list[dict], key: str) -> dict[str, dict]:
    return {row[key]: row for row in rows}


def _rat_wire(value: dict) -> Fraction:
    rational = ExactRational.from_dict(value)
    return Fraction(rational.numerator, rational.denominator)


def _level(r: int, n: int, g: int) -> s0.ApproximationLevelId:
    return s0.ApproximationLevelId(
        frame_id="u24.e2.declared_square.observation_frame.v1",
        domain_id="u24.s0.declared_finite_similarity_domain.v1",
        radius=r,
        word_depth=n,
        granularity=g,
    )


def _complete_coverage():
    return s0.make_counted_coverage_witness(
        ordered_universe_ids=_PRIMITIVE_IDS, covered_ids=_PRIMITIVE_IDS
    )


def _morphism_kwargs(source, target, matrix):
    return dict(
        source_level=source,
        target_level=target,
        node_matrix=matrix,
        coverage=_complete_coverage(),
        commutator_l1=_r(0),
        target_residual_transport=_r(0),
        cross_covariance_budget="0",
        numeric_residual_budget="0",
        remainder_e=_r(1, 4),
    )


def test_s0_authority_references_distinguish_live_and_digest_bindings_and_firewall_me0():
    assert tuple(s0.__all__) == _S0_PUBLIC_SURFACE
    package_s0_exports = {
        name
        for name in odlrq.__all__
        if getattr(getattr(odlrq, name, None), "__module__", None) == s0.__name__
    }
    assert package_s0_exports == set(_S0_PUBLIC_SURFACE)
    for name in _S0_PUBLIC_SURFACE:
        assert getattr(odlrq, name) is getattr(s0, name)
    for name in _S0_PUBLIC_ENDPOINTS:
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(getattr(s0, name)).parameters.values()
        )

    e1 = _accepted_e1_envelope()
    e2 = _e2_parent("M0")["envelope"]
    token = _e2_token()
    hard_reference = s0.make_declared_s0_hard_authority_reference(
        primitive_rows=_primitive_rows()
    )
    hard_binding = s0.bind_s0_hard_authorities(
        accepted_e1_qualification_envelope=e1,
        e2_m0_parent_envelope=e2,
        e2_support_token=token,
    )
    assert type(hard_reference) is s0.DeclaredS0HardAuthorityReference
    assert type(hard_binding) is s0.LiveS0HardAuthorityBinding
    assert hasattr(hard_reference, "to_dict") and not hasattr(hard_binding, "to_dict")
    assert hard_reference.to_dict()["accepted_e1_qualification_envelope_sha256"] == ACCEPTED_E1_ENVELOPE_SHA256
    assert hard_reference.to_dict()["e2_m0_parent_envelope_sha256"] == E2_M0_ENVELOPE_SHA256
    assert ACCEPTED_E1_ENVELOPE_SHA256 != E2_M0_ENVELOPE_SHA256

    problem, result = _me0_objects()
    me0_reference = s0.make_declared_me0_result_reference(
        problem_wire=problem.to_dict(), result_wire=result.to_dict()
    )
    me0_binding = s0.bind_me0_result(problem=problem, result=result)
    assert type(me0_reference) is s0.DeclaredME0ResultReference
    assert type(me0_binding) is s0.LiveME0ResultBinding
    assert me0_reference.to_dict()["predictive_only"] is True
    assert not hasattr(me0_binding, "to_dict")
    certificate = _s0_fixture().similarity_certificate
    live_verified = s0.verify_similarity_certificate_live(
        certificate=certificate,
        hard_binding=hard_binding,
        me0_binding=me0_binding,
    )
    assert canonical_contract_bytes(live_verified) == canonical_contract_bytes(certificate)
    with pytest.raises((StrictContractError, TypeError)):
        s0.bind_s0_hard_authorities(
            accepted_e1_qualification_envelope=e2,
            e2_m0_parent_envelope=e1,
            e2_support_token=token,
        )
    with pytest.raises((StrictContractError, TypeError)):
        s0.declare_synthetic_l_plus(
            hard_reference=me0_reference,
            primitive_rows=_primitive_rows(),
            coverage=_complete_coverage(),
        )


def test_s0_global_measure_rows_recompute_normalization_and_zero_mass_rules():
    wire = _s0_fixture().to_dict()
    measures = wire["measures"]
    assert [row["measure_id"] for row in measures] == [
        "u24_s0_s_id_m", "u24_s0_s_node_x", "u24_s0_s_node_y",
        "u24_s0_s_edge_x", "u24_s0_s_edge_y", "u24_s0_s_cross_x",
        "u24_s0_s_cross_y", "u24_s0_s_cover_x", "u24_s0_s_cover_y",
        "u24_s0_s_zero_m", "u24_s0_s_compose_l3_x",
        "u24_s0_s_compose_l3_y", "u24_s0_s_compose_l2_m",
        "u24_s0_s_compose_l1_m", "u24_s0_s_compose_l0_m",
        "u24_s0_s_numeric_x", "u24_s0_s_numeric_y",
    ]
    by_id = _wire_rows_by_id(measures, "measure_id")
    for measure_id, row in by_id.items():
        expected = Fraction(0) if measure_id == "u24_s0_s_zero_m" else Fraction(1)
        assert _rat_wire(row["rho1"]) == expected
        assert _rat_wire(row["rho2"]) == expected
        assert row["normalization_mode"] == ("ZERO_BOTH" if expected == 0 else "UNIT_BOTH")
    assert [_rat_wire(x) for x in by_id["u24_s0_s_node_y"]["node_mass"]] == [0, 1]
    assert [_rat_wire(x) for x in by_id["u24_s0_s_edge_y"]["edge_mass"]] == [0, 0, 1]
    assert by_id["u24_s0_s_cross_x"]["cross_covariance_residual"] == "0.125"
    assert by_id["u24_s0_s_numeric_x"]["numeric_residual"] == "0.0625"
    with pytest.raises(StrictContractError):
        s0.make_global_measure(
            measure_id="bad-total", level=_level(2, 2, 2),
            node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
            node_mass=(_r(1), _r(1)), edge_mass=(_r(1), _r(0), _r(0)),
            cross_covariance_residual="0", numeric_residual="0",
        )
    with pytest.raises(StrictContractError):
        s0.make_global_measure(
            measure_id="negative", level=_level(2, 2, 2),
            node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
            node_mass=(_r(-1), _r(2)), edge_mass=(_r(1), _r(0), _r(0)),
            cross_covariance_residual="0", numeric_residual="0",
        )


def test_s0_predictive_distance_separates_node_edge_cross_and_numeric_terms():
    rows = _wire_rows_by_id(
        _s0_fixture().similarity_certificate.to_dict()["predictive_case_results"],
        "case_id",
    )
    expected = {
        "s-id": ("0", "0"), "s-node": ("1", "1"),
        "s-edge": ("1", "1"), "s-cross": ("0", "0.125"),
        "s-cover": ("0", "0"), "s-zero": ("0", "0"),
        "s-compose": ("1", "1"), "s-numeric": ("0", "0.0625"),
    }
    for case_id, (metric, upper) in expected.items():
        distance = rows[case_id]["predictive_distance"]
        assert distance["predictive_metric"] == metric
        assert distance["discrepancy_upper_bound"] == upper
        assert distance["evidence_tier"] == "PREDICTIVE_NOMINAL_ONLY"
    assert rows["s-zero-kill"]["predictive_distance"] is None
    assert rows["s-zero-kill"]["expected_error"] == "ZERO_NONZERO_NORMALIZATION_MISMATCH"
    assert rows["s-cross"]["predictive_distance"]["predictive_metric"] == "0"
    assert rows["s-numeric"]["predictive_distance"]["predictive_metric"] == "0"


def test_s0_declared_lplus_enumerates_complete_primitive_universe_and_builds_exact_positive_majorant():
    fixture = _s0_fixture().to_dict()
    token = fixture["similarity_certificate"]["l_plus_token"]
    assert token["primitive_universe"]["rows"][-1]["primitive_id"] == _PRIMITIVE_IDS[-1]
    assert [_rat_wire(x) for x in token["node_l_plus"]] == [1, 2]
    assert [_rat_wire(x) for x in token["edge_l_plus"]] == [1, 1, 2]
    assert _rat_wire(token["target_residual_upper_bound"]) == Fraction(1, 8)
    rows = _wire_rows_by_id(
        fixture["similarity_certificate"]["positive_case_results"], "case_id"
    )
    expected = {
        "s-id": (0, Fraction(1, 4)), "s-node": (3, Fraction(13, 4)),
        "s-edge": (3, Fraction(13, 4)), "s-cross": (0, Fraction(1, 4)),
        "s-zero": (0, Fraction(1, 4)),
        "s-compose": (Fraction(5, 2), Fraction(11, 4)),
        "s-numeric": (0, Fraction(1, 4)),
    }
    for case_id, (distance, majorant) in expected.items():
        value = rows[case_id]["positive_distance"]
        assert _rat_wire(value["positive_representation_distance"]) == distance
        assert _rat_wire(value["safety_majorant"]) == majorant
        assert value["disposition"] == "POSITIVE_SAFETY_MAJORANT_VERIFIED"
    missing_ghost = _primitive_rows()[:-1]
    with pytest.raises(StrictContractError):
        s0.make_declared_s0_hard_authority_reference(primitive_rows=missing_ghost)


def test_s0_counted_coverage_and_target_residuals_abstain_without_four_of_four():
    complete = _complete_coverage()
    incomplete = s0.make_counted_coverage_witness(
        ordered_universe_ids=_PRIMITIVE_IDS, covered_ids=_PRIMITIVE_IDS[:-1]
    )
    assert complete.to_dict()["covered_count"] == complete.to_dict()["universe_count"] == 4
    assert complete.to_dict()["complete"] is True
    assert incomplete.to_dict()["covered_count"] == 3
    assert incomplete.to_dict()["universe_count"] == 4
    assert incomplete.to_dict()["complete"] is False
    lplus = _s0_fixture().similarity_certificate.l_plus_token
    complete_bound = s0.make_target_residual_bound(
        l_plus_token=lplus, measure_id="measure", coverage=complete
    )
    incomplete_bound = s0.make_target_residual_bound(
        l_plus_token=lplus, measure_id="measure", coverage=incomplete
    )
    assert complete_bound.to_dict()["hard_eligible"] is True
    assert incomplete_bound.to_dict()["hard_eligible"] is False
    assert incomplete_bound.to_dict()["disposition"] == "ABSTAIN_INCOMPLETE_COVERAGE"
    forged_complete = s0.make_counted_coverage_witness(
        ordered_universe_ids=("a", "b", "c", "d"),
        covered_ids=("a", "b", "c", "d"),
    )
    with pytest.raises(StrictContractError):
        s0.declare_synthetic_l_plus(
            hard_reference=_s0_fixture().hard_authority_reference,
            primitive_rows=_primitive_rows(), coverage=forged_complete,
        )
    with pytest.raises(StrictContractError):
        s0.make_target_residual_bound(
            l_plus_token=lplus, measure_id="measure", coverage=forged_complete
        )
    rows = _wire_rows_by_id(
        _s0_fixture().similarity_certificate.to_dict()["positive_case_results"],
        "case_id",
    )
    cover = rows["s-cover"]["positive_distance"]
    assert _rat_wire(cover["positive_representation_distance"]) == 0
    assert cover["safety_majorant"] is None
    assert cover["disposition"] == "ABSTAIN_INCOMPLETE_COVERAGE"
    measure = _s0_fixture().measures[0]
    mismatched_residual = s0.make_target_residual_bound(
        l_plus_token=lplus, measure_id=measure.measure_id, coverage=incomplete
    )
    with pytest.raises(StrictContractError):
        s0.compute_positive_distance(
            l_plus_token=lplus, coverage=complete,
            x_target_residual=mismatched_residual,
            y_target_residual=mismatched_residual,
            x=measure, y=measure,
        )
    for covered in ((_PRIMITIVE_IDS[0],) * 2, tuple(reversed(_PRIMITIVE_IDS)), ("unknown",)):
        with pytest.raises(StrictContractError):
            s0.make_counted_coverage_witness(
                ordered_universe_ids=_PRIMITIVE_IDS, covered_ids=covered
            )


def test_s0_radius_morphism_is_typed_fine_to_coarse_column_stochastic():
    morphism = s0.make_radius_morphism(
        **_morphism_kwargs(_level(2, 1, 1), _level(1, 1, 1), ((_r(1), _r(0)), (_r(0), _r(1))))
    )
    wire = morphism.to_dict()
    assert wire["axis"] == "RADIUS"
    assert [[_rat_wire(x) for x in row] for row in wire["node_matrix"]] == [[1, 0], [0, 1]]
    assert [[_rat_wire(x) for x in row] for row in wire["edge_matrix"]] == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    with pytest.raises(StrictContractError):
        s0.make_radius_morphism(
            **_morphism_kwargs(_level(1, 1, 1), _level(2, 1, 1), ((_r(1), _r(0)), (_r(0), _r(1))))
        )
    with pytest.raises(StrictContractError):
        s0.make_radius_morphism(
            **_morphism_kwargs(_level(2, 1, 1), _level(1, 1, 1), ((_r(1), _r(1)), (_r(0), _r(1))))
        )
    morphism_factories = (
        (s0.make_radius_morphism, _level(2, 1, 1), _level(1, 1, 1)),
        (s0.make_word_depth_morphism, _level(2, 2, 1), _level(2, 1, 1)),
        (s0.make_granularity_morphism, _level(2, 2, 2), _level(2, 2, 1)),
    )
    scalar_attacks = (
        ("commutator_l1", _r(1, 8)),
        ("target_residual_transport", _r(1, 8)),
        ("cross_covariance_budget", "0.125"),
        ("numeric_residual_budget", "0.125"),
        ("remainder_e", _r(1, 2)),
    )
    identity = ((_r(1), _r(0)), (_r(0), _r(1)))
    for factory, source, target in morphism_factories:
        for field, replacement in scalar_attacks:
            changed = _morphism_kwargs(source, target, identity)
            changed[field] = replacement
            with pytest.raises(StrictContractError):
                factory(**changed)
    fixture = _s0_fixture()
    by_id = {measure.measure_id: measure for measure in fixture.measures}
    wrong_coarse = s0.make_global_measure(
        measure_id="u24_s0_wrong_l0", level=_level(1, 1, 1),
        node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
        node_mass=(_r(0), _r(1)), edge_mass=(_r(0), _r(0), _r(1)),
        cross_covariance_residual="0", numeric_residual="0",
    )
    # A zero distance is not enough: the explicitly supplied coarse measures
    # must be the actual P-image of the fine measures.
    with pytest.raises(StrictContractError):
        s0.verify_predictive_transport(
            me0_reference=fixture.predictive_me0_result_reference,
            morphism=morphism,
            x_fine=by_id["u24_s0_s_compose_l1_m"],
            y_fine=by_id["u24_s0_s_compose_l1_m"],
            x_coarse=wrong_coarse, y_coarse=wrong_coarse,
        )
    base_fine = s0.make_global_measure(
        measure_id="pair-base-fine", level=_level(2, 1, 1),
        node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
        node_mass=(_r(1), _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
        cross_covariance_residual="0", numeric_residual="0",
    )
    changed_fine = s0.make_global_measure(
        measure_id="pair-base-fine", level=_level(2, 1, 1),
        node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
        node_mass=(_r(1), _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
        cross_covariance_residual="0.125", numeric_residual="0",
    )
    base_coarse = s0.make_global_measure(
        measure_id="pair-base-coarse", level=_level(1, 1, 1),
        node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
        node_mass=(_r(1), _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
        cross_covariance_residual="0", numeric_residual="0",
    )
    changed_coarse = s0.make_global_measure(
        measure_id="pair-base-coarse", level=_level(1, 1, 1),
        node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
        node_mass=(_r(1), _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
        cross_covariance_residual="0.125", numeric_residual="0",
    )
    lplus = fixture.similarity_certificate.l_plus_token
    fine_residual = s0.make_target_residual_bound(
        l_plus_token=lplus, measure_id=base_fine.measure_id,
        coverage=_complete_coverage(),
    )
    coarse_residual = s0.make_target_residual_bound(
        l_plus_token=lplus, measure_id=base_coarse.measure_id,
        coverage=_complete_coverage(),
    )
    positive_base = s0.verify_positive_transport(
        l_plus_token=lplus, coverage=_complete_coverage(), morphism=morphism,
        x_fine_target_residual=fine_residual,
        y_fine_target_residual=fine_residual,
        x_coarse_target_residual=coarse_residual,
        y_coarse_target_residual=coarse_residual,
        x_fine=base_fine, y_fine=base_fine,
        x_coarse=base_coarse, y_coarse=base_coarse,
    )
    positive_changed = s0.verify_positive_transport(
        l_plus_token=lplus, coverage=_complete_coverage(), morphism=morphism,
        x_fine_target_residual=fine_residual,
        y_fine_target_residual=fine_residual,
        x_coarse_target_residual=coarse_residual,
        y_coarse_target_residual=coarse_residual,
        x_fine=changed_fine, y_fine=base_fine,
        x_coarse=changed_coarse, y_coarse=base_coarse,
    )
    assert positive_base.source_pair_sha256 == positive_changed.source_pair_sha256
    assert positive_base.target_pair_sha256 == positive_changed.target_pair_sha256
    predictive_base = s0.verify_predictive_transport(
        me0_reference=fixture.predictive_me0_result_reference,
        morphism=morphism, x_fine=base_fine, y_fine=base_fine,
        x_coarse=base_coarse, y_coarse=base_coarse,
    )
    predictive_changed = s0.verify_predictive_transport(
        me0_reference=fixture.predictive_me0_result_reference,
        morphism=morphism, x_fine=changed_fine, y_fine=base_fine,
        x_coarse=changed_coarse, y_coarse=base_coarse,
    )
    assert predictive_base.source_pair_sha256 != predictive_changed.source_pair_sha256
    assert predictive_base.target_pair_sha256 != predictive_changed.target_pair_sha256


def test_s0_word_depth_morphism_is_typed_fine_to_coarse_column_stochastic():
    morphism = s0.make_word_depth_morphism(
        **_morphism_kwargs(_level(2, 2, 1), _level(2, 1, 1), ((_r(1), _r(0)), (_r(0), _r(1))))
    )
    assert morphism.to_dict()["axis"] == "WORD_DEPTH"
    assert morphism.to_dict()["norm_id"] == "weighted_l1_exact_rational_v1"
    with pytest.raises(StrictContractError):
        s0.make_word_depth_morphism(
            **_morphism_kwargs(_level(2, 2, 2), _level(2, 1, 1), ((_r(1), _r(0)), (_r(0), _r(1))))
        )
    with pytest.raises(StrictContractError):
        s0.make_word_depth_morphism(
            **_morphism_kwargs(_level(2, 2, 1), _level(2, 1, 1), ((_r(1), _r(-1)), (_r(0), _r(2))))
        )


def test_s0_granularity_morphism_derives_edge_map_and_composes_in_frozen_order():
    g = s0.make_granularity_morphism(
        **_morphism_kwargs(_level(2, 2, 2), _level(2, 2, 1), ((_r(1), _r(1)), (_r(0), _r(0))))
    )
    assert [[_rat_wire(x) for x in row] for row in g.to_dict()["edge_matrix"]] == [[1, 1, 1], [0, 0, 0], [0, 0, 0]]
    nondegenerate = s0.make_granularity_morphism(
        **_morphism_kwargs(
            _level(2, 2, 2), _level(2, 2, 1),
            ((_r(1, 2), _r(1, 3)), (_r(1, 2), _r(2, 3))),
        )
    )
    assert [[_rat_wire(x) for x in row] for row in nondegenerate.to_dict()["edge_matrix"]] == [
        [Fraction(1, 4), Fraction(1, 6), Fraction(1, 9)],
        [Fraction(1, 2), Fraction(1, 2), Fraction(4, 9)],
        [Fraction(1, 4), Fraction(1, 3), Fraction(4, 9)],
    ]
    forged_edge_map = copy.deepcopy(nondegenerate.to_dict())
    forged_edge_map["edge_matrix"] = [
        [_r(1).to_dict(), _r(0).to_dict(), _r(0).to_dict()],
        [_r(0).to_dict(), _r(1).to_dict(), _r(0).to_dict()],
        [_r(0).to_dict(), _r(0).to_dict(), _r(1).to_dict()],
    ]
    with pytest.raises(StrictContractError):
        s0.GranularityMorphism.from_dict(forged_edge_map)
    tower = _s0_fixture().similarity_certificate.local_tower.to_dict()
    assert tower["composition_order"] == ["GRANULARITY", "WORD_DEPTH", "RADIUS"]
    leaked = copy.deepcopy(nondegenerate.to_dict())
    leaked["edge_matrix"].pop(1)
    with pytest.raises(StrictContractError):
        s0.GranularityMorphism.from_dict(leaked)


def test_s0_finite_remainder_recomputes_all_six_composites_without_infinite_claim():
    certificate = _s0_fixture().similarity_certificate
    finite = certificate.to_dict()["finite_remainder_certificate"]
    assert finite["finite_level_count"] == 4
    assert [_rat_wire(x) for x in finite["adjacent_remainders"]] == [Fraction(1, 4)] * 3
    assert [_rat_wire(x) for x in finite["suffix_majorants"]] == [Fraction(3, 4), Fraction(1, 2), Fraction(1, 4), 0]
    assert [_rat_wire(x) for x in finite["composite_remainders"]] == [
        Fraction(1, 4), Fraction(1, 4), Fraction(1, 4),
        Fraction(1, 2), Fraction(1, 2), Fraction(3, 4),
    ]
    assert finite["infinite_cutoff_claim"] is False
    assert len(finite["predictive_transport_certificates"]) == 6
    assert len(finite["positive_transport_certificates"]) == 6
    assert [(x["fine_upper"], x["coarse_upper"]) for x in finite["predictive_transport_certificates"]] == [
        ("0", "0"), ("0", "0"), ("1", "0"),
        ("0", "0"), ("1", "0"), ("1", "0"),
    ]
    positive_pairs = [
        (_rat_wire(x["fine_upper"]), _rat_wire(x["coarse_upper"]))
        for x in finite["positive_transport_certificates"]
    ]
    assert positive_pairs == [
        (Fraction(1, 4), Fraction(1, 4)),
        (Fraction(1, 4), Fraction(1, 4)),
        (Fraction(11, 4), Fraction(1, 4)),
        (Fraction(1, 4), Fraction(1, 4)),
        (Fraction(11, 4), Fraction(1, 4)),
        (Fraction(11, 4), Fraction(1, 4)),
    ]
    forged_predictive = copy.deepcopy(finite["predictive_transport_certificates"][0])
    forged_predictive["fine_upper"] = "0"
    forged_predictive["coarse_upper"] = "1"
    forged_predictive["inequality_holds"] = True
    with pytest.raises(StrictContractError):
        s0.PredictiveTransportCertificate.from_dict(forged_predictive)
    forged_positive = copy.deepcopy(finite["positive_transport_certificates"][0])
    forged_positive["fine_upper"] = _r(1, 4).to_dict()
    forged_positive["coarse_upper"] = _r(1).to_dict()
    forged_positive["inequality_holds"] = True
    with pytest.raises(StrictContractError):
        s0.PositiveTransportCertificate.from_dict(forged_positive)
    reordered_finite = copy.deepcopy(finite)
    reordered_finite["predictive_transport_certificates"][0:2] = reversed(
        reordered_finite["predictive_transport_certificates"][0:2]
    )
    reordered_finite["predictive_projection_sha256"] = _sha(
        reordered_finite["predictive_transport_certificates"]
    )
    with pytest.raises(StrictContractError):
        s0.FiniteRemainderCertificate.from_dict(reordered_finite)
    arbitrary_digest = copy.deepcopy(finite)
    arbitrary_digest["positive_projection_sha256"] = "0" * 64
    with pytest.raises(StrictContractError):
        s0.FiniteRemainderCertificate.from_dict(arbitrary_digest)
    for field, index, replacement in (
        ("suffix_majorants", 1, _r(3, 4).to_dict()),
        ("composite_remainders", 3, _r(3, 4).to_dict()),
    ):
        bad = copy.deepcopy(certificate.to_dict())
        bad["finite_remainder_certificate"][field][index] = replacement
        with pytest.raises(StrictContractError):
            s0.SimilarityCertificate.from_dict(bad)
    broken_inequality = copy.deepcopy(certificate.to_dict())
    broken_inequality["finite_remainder_certificate"][
        "positive_transport_certificates"
    ][0]["coarse_upper"] = _r(1).to_dict()
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(broken_inequality)
    bad_transport_disposition = copy.deepcopy(certificate.to_dict())
    bad_transport_disposition["finite_remainder_certificate"][
        "predictive_transport_certificates"
    ][0]["disposition"] = "POSITIVE_TRANSPORT_VERIFIED"
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(bad_transport_disposition)
    bad_remainder_disposition = copy.deepcopy(certificate.to_dict())
    bad_remainder_disposition["finite_remainder_certificate"]["disposition"] = "PREDICTIVE_TRANSPORT_VERIFIED"
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(bad_remainder_disposition)
    infinite = copy.deepcopy(certificate.to_dict())
    infinite["finite_remainder_certificate"]["infinite_cutoff_claim"] = True
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(infinite)


def test_s0_strict_wire_caps_type_substitution_and_mutation_fail_closed():
    fixture = _s0_fixture()
    certificate = fixture.similarity_certificate
    verified = s0.verify_similarity_certificate(certificate=certificate)
    assert verified is certificate
    wire = certificate.to_dict()
    baseline_bytes = canonical_contract_bytes(certificate)
    detached_wire = certificate.to_dict()
    detached_wire["predictive_case_results"][0]["case_id"] = "tampered-copy"
    assert canonical_contract_bytes(certificate) == baseline_bytes
    isolated = s0.SimilarityCertificate.from_dict(copy.deepcopy(wire))
    isolated.predictive_case_results[0]["case_id"] = "tampered-live-row"
    with pytest.raises(StrictContractError):
        isolated.to_dict()
    malformed_case = copy.deepcopy(wire)
    malformed_case["predictive_case_results"][0]["predictive_distance"][
        "predictive_metric"
    ] = 0.0
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(malformed_case)
    assert wire["disposition"] == "CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED"
    positive_hash = wire["positive_core_sha256"]
    predictive_hash = wire["predictive_core_sha256"]
    assert positive_hash != predictive_hash
    assert wire["runtime_manifest_sha256"] == "88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9"
    for mutate in (
        lambda value: value.update({"unknown": 1}),
        lambda value: value.pop("coverage"),
        lambda value: value.update({"positive_core_sha256": "0" * 64}),
        lambda value: value.update({"predictive_core_sha256": "0" * 64}),
    ):
        changed = copy.deepcopy(wire)
        mutate(changed)
        with pytest.raises(StrictContractError):
            s0.SimilarityCertificate.from_dict(changed)
    reordered = copy.deepcopy(wire)
    reordered["measures"] = list(reversed(reordered["measures"]))
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(reordered)
    with pytest.raises(StrictContractError):
        s0.make_global_measure(
            measure_id="x" * 129, level=_level(2, 2, 2),
            node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
            node_mass=(_r(1), _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
            cross_covariance_residual="0", numeric_residual="0",
        )
    oversized = ExactRational(1 << 256)
    with pytest.raises(StrictContractError):
        s0.make_global_measure(
            measure_id="oversized", level=_level(2, 2, 2),
            node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
            node_mass=(oversized, _r(0)), edge_mass=(_r(1), _r(0), _r(0)),
            cross_covariance_residual="0", numeric_residual="0",
        )
    for cross, numeric in ((0.0, "0"), ("0", 0.0), ("-0", "0")):
        with pytest.raises(StrictContractError):
            s0.make_global_measure(
                measure_id="raw-float", level=_level(2, 2, 2),
                node_ids=_NODE_IDS, edge_ids=_EDGE_IDS,
                node_mass=(_r(1), _r(0)),
                edge_mass=(_r(1), _r(0), _r(0)),
                cross_covariance_residual=cross, numeric_residual=numeric,
            )
    raw_budget = _morphism_kwargs(
        _level(2, 1, 1), _level(1, 1, 1),
        ((_r(1), _r(0)), (_r(0), _r(1))),
    )
    raw_budget["cross_covariance_budget"] = 0.0
    with pytest.raises(StrictContractError):
        s0.make_radius_morphism(**raw_budget)
    negative_budget = _morphism_kwargs(
        _level(2, 1, 1), _level(1, 1, 1),
        ((_r(1), _r(0)), (_r(0), _r(1))),
    )
    negative_budget["numeric_residual_budget"] = "-0.5"
    with pytest.raises(StrictContractError):
        s0.make_radius_morphism(**negative_budget)
    oversized_morphism = copy.deepcopy(
        fixture.local_tower.radius_morphism.to_dict()
    )
    valid_row = oversized_morphism["node_matrix"][0]
    oversized_morphism["node_matrix"] = [
        copy.deepcopy(valid_row) for _ in range(16_385)
    ]
    with pytest.raises(StrictContractError):
        s0.RadiusMorphism.from_dict(oversized_morphism)
    class FakeMeasure:
        def to_dict(self):
            return copy.deepcopy(fixture.measures[0].to_dict())
    with pytest.raises((StrictContractError, TypeError)):
        s0.compute_predictive_distance(
            me0_reference=fixture.predictive_me0_result_reference,
            x=FakeMeasure(), y=fixture.measures[0],
        )
    mixed = copy.deepcopy(wire)
    mixed["positive_case_results"][0]["positive_distance"] = copy.deepcopy(
        mixed["predictive_case_results"][0]["predictive_distance"]
    )
    with pytest.raises(StrictContractError):
        s0.SimilarityCertificate.from_dict(mixed)
    changed_cross = s0.make_global_measure(
        measure_id=fixture.measures[5].measure_id,
        level=fixture.measures[5].level,
        node_ids=fixture.measures[5].node_ids,
        edge_ids=fixture.measures[5].edge_ids,
        node_mass=fixture.measures[5].node_mass,
        edge_mass=fixture.measures[5].edge_mass,
        cross_covariance_residual="0", numeric_residual="0",
    )
    changed_measures = list(fixture.measures)
    changed_measures[5] = changed_cross
    changed_predictive_rows = copy.deepcopy(
        list(certificate.predictive_case_results)
    )
    changed_predictive_rows[3]["predictive_distance"] = (
        s0.compute_predictive_distance(
            me0_reference=certificate.predictive_me0_result_reference,
            x=changed_cross, y=fixture.measures[6],
        ).to_dict()
    )
    residual_variant = s0.SimilarityCertificate(
        hard_authority_reference=certificate.hard_authority_reference,
        predictive_me0_result_reference=certificate.predictive_me0_result_reference,
        primitive_universe_sha256=certificate.primitive_universe_sha256,
        l_plus_token=certificate.l_plus_token,
        measures=tuple(changed_measures), local_tower=certificate.local_tower,
        predictive_case_results=tuple(changed_predictive_rows),
        positive_case_results=certificate.positive_case_results,
        finite_remainder_certificate=certificate.finite_remainder_certificate,
        coverage=certificate.coverage,
        target_residuals=certificate.target_residuals,
        runtime_manifest_sha256=certificate.runtime_manifest_sha256,
        disposition=certificate.disposition,
    )
    assert residual_variant.positive_core_sha256 == certificate.positive_core_sha256
    assert residual_variant.predictive_core_sha256 != certificate.predictive_core_sha256
