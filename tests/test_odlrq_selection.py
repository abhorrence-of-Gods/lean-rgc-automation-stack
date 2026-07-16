from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
from math import gcd

import pytest

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
from lean_rgc.odlrq import certificates as e2_certificates
from lean_rgc.odlrq import selection as e2_selection


E2_AUTHORITY_COMMIT_SHA = "28c5a29000dddadcaf3e9ad9dd5534554dd67f32"
E2_AUTHORITY_TREE_SHA = "1a71fc6ff774dd0bcf7e4ab551bd737a7a9dab14"
E2_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_e2_endpoint_semantics_authority_amendment_2026-07-16.md"
)
E2_AUTHORITY_DOCUMENT_BLOB_SHA = "139a5992a38269974068858ef00f47f43ef5fca4"

_COORDINATE_IDS = ("OPEN_0", "OPEN_1", "CLOSED", "SINK")
_PARENT_SELECTORS = ("M0", "M1", "MRET", "NONNORMAL", "NILPOTENT")
_PARENT_MATRICES = {
    "M0": (
        (Fraction(1), Fraction(2), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1, 2), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
    ),
    "M1": (
        (Fraction(1, 2), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(3), Fraction(1), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
    ),
    "MRET": (
        (Fraction(0), Fraction(2), Fraction(0), Fraction(0)),
        (Fraction(3), Fraction(1, 2), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
    ),
    "NONNORMAL": (
        (Fraction(1), Fraction(10), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
    ),
    "NILPOTENT": (
        (Fraction(0), Fraction(1), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
    ),
}

_FIXTURE_CACHE: dict[str, dict] = {}
_IDENTIFICATION_CACHE: dict[tuple[str, str], object] = {}
_RESTRICTION_CACHE: dict[tuple[str, str], object] = {}
_SAFETY_CACHE: dict[tuple[str, str], object] = {}
_COCYCLE_CACHE: dict[str, object] = {}
_RETURN_CACHE: dict[str, object] = {}
_SELECTION_CACHE: dict[str, object] = {}

_RATIONAL_KEYS = {"schema_version", "numerator", "denominator"}
_IDENTIFICATION_KEYS = {
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "basis_convention",
    "parent_envelope_sha256",
    "layer_sha256",
    "source_generator_sha256",
    "target_generator_sha256",
    "source_weights_sha256",
    "target_weights_sha256",
    "source_law_sha256",
    "source_completeness_sha256",
    "target_completeness_sha256",
    "full_coordinate_ids",
    "source_block_count",
    "target_block_count",
    "coordinate_rows",
    "coordinate_core_sha256",
    "verification_disposition",
}
_COORDINATE_ROW_KEYS = {
    "coordinate_id",
    "coordinate_role",
    "source_block_index",
    "target_block_index",
    "source_member_ids",
    "target_member_ids",
    "source_member_set_sha256",
    "target_member_set_sha256",
    "source_weight",
    "target_weight",
}
_RESTRICTION_KEYS = {
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "basis_convention",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "coordinate_core_sha256",
    "full_coordinate_ids",
    "retained_coordinate_ids",
    "complement_coordinate_ids",
    "full_matrix",
    "restricted_matrix",
    "restricted_matrix_sha256",
    "restricted_source_weights",
    "restricted_source_weights_sha256",
    "restricted_target_weights",
    "restricted_target_weights_sha256",
    "omitted_cells",
    "omitted_cells_sha256",
    "omitted_cell_count",
    "replayed_cell_count",
    "restriction_core_sha256",
    "replay_pass",
    "verification_disposition",
}
_OMITTED_CELL_KEYS = {"target_coordinate_id", "source_coordinate_id", "value"}
_SAFETY_KEYS = {
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "scope",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "envelope_restriction_sha256",
    "source_law_sha256",
    "coordinate_core_sha256",
    "restriction_core_sha256",
    "ordered_candidate_loads",
    "majorant_matrix",
    "candidate_load_count",
    "matrix_cell_count",
    "theorem_core_sha256",
    "law_uniform",
    "cancellation_free",
    "verification_disposition",
}
_CANDIDATE_LOAD_KEYS = {
    "target_coordinate_id",
    "source_coordinate_id",
    "source_member_id",
    "source_member_sha256",
    "load",
}
_SPLIT_KEYS = {
    "schema_version",
    "endpoint_id",
    "envelope_restriction_sha256",
    "basis_convention",
    "retained_coordinate_ids",
    "p_coordinate_ids",
    "q_coordinate_ids",
    "m_pp",
    "m_pq",
    "m_qp",
    "m_qq",
    "split_exhaustive",
    "split_core_sha256",
    "verification_disposition",
}
_COCYCLE_KEYS = {
    "schema_version",
    "endpoint_id",
    "channel",
    "channel_derivation",
    "composition_scope",
    "product_order",
    "factor_restriction_sha256s",
    "ordered_source_basis",
    "ordered_intermediate_basis",
    "ordered_target_basis",
    "source_weights",
    "intermediate_weights",
    "target_weights",
    "source_weights_sha256",
    "intermediate_weights_sha256",
    "target_weights_sha256",
    "layer_matrices",
    "theta_values",
    "componentwise_lhs_rows",
    "product_matrix",
    "product_weighted_norm",
    "theta_product",
    "finite_horizon",
    "inequality_pass",
    "verification_disposition",
}
_RETURN_KEYS = {
    "schema_version",
    "endpoint_id",
    "envelope_restriction_sha256",
    "resolved_memory_split_sha256",
    "iteration_scope",
    "finite_only",
    "horizon",
    "m_pp",
    "m_pq",
    "m_qp",
    "m_qq",
    "qq_powers",
    "return_terms",
    "return_sum",
    "p_source_weights",
    "p_source_weights_sha256",
    "p_target_weights",
    "p_target_weights_sha256",
    "weighted_norm",
    "operation_count",
    "direct_zero_memory_positive",
    "verification_disposition",
}
_POWER_TERM_KEYS = {"k", "matrix"}
_MANIFEST_KEYS = {
    "schema_version",
    "endpoint_id",
    "universe_id",
    "sealed_before_threshold",
    "candidate_rows",
    "candidate_count",
    "canonical_candidate_ids",
    "pre_gate_complete",
    "manifest_core_sha256",
    "verification_disposition",
}
_CANDIDATE_ROW_KEYS = {
    "candidate_id",
    "candidate_payload_sha256",
    "source_coordinate_ids",
    "membership_core_sha256",
    "parent_id",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "envelope_restriction_sha256",
    "lifting_uniform_safety_sha256",
    "target_coordinate_id",
    "source_coordinate_id",
    "bound",
    "utility",
}
_TOKEN_KEYS = {
    "schema_version",
    "endpoint_id",
    "candidate_universe_manifest_sha256",
    "p1_cocycle_sha256",
    "p2_cocycle_sha256",
    "return_memory_bound_sha256",
    "comparator",
    "threshold",
    "decision_rows",
    "denominator",
    "numerator",
    "coverage",
    "ungated_ranking",
    "gated_ranking",
    "support_candidate_ids",
    "rejected_candidate_ids",
    "abstained_candidate_ids",
    "ranking_changed",
    "invalidation_sha256",
    "verification_disposition",
}
_DECISION_ROW_KEYS = {
    "candidate_id",
    "bound",
    "threshold",
    "decision",
    "reason",
    "authority_bundle_sha256",
}


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


def _make_literal_side(side: str):
    if side == "source":
        environment = "53" * 32
        action_id = "u24_e2_source_a"
        specifications = (
            ("u24_e2_source_open0_a", TotalizedStatus.OPEN, 0),
            ("u24_e2_source_open0_b", TotalizedStatus.OPEN, 0),
            ("u24_e2_source_open1", TotalizedStatus.OPEN, 1),
            ("u24_e2_source_closed", TotalizedStatus.CLOSED, 2),
            ("u24_e2_source_sink", TotalizedStatus.SINK, 3),
        )
    elif side == "target":
        environment = "54" * 32
        action_id = "u24_e2_target_a"
        specifications = (
            ("u24_e2_target_open0", TotalizedStatus.OPEN, 0),
            ("u24_e2_target_open1", TotalizedStatus.OPEN, 1),
            ("u24_e2_target_closed", TotalizedStatus.CLOSED, 2),
            ("u24_e2_target_sink", TotalizedStatus.SINK, 3),
        )
    else:
        raise AssertionError("literal E2 side is not frozen")

    action = SyntheticAction(action_id, _payload("action", action_id))
    vocabulary = ResponseVocabularyId.from_coordinate_names(("e2_coordinate",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment,
        response_vocabulary_id=vocabulary,
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,),
        response_vocabulary_id=vocabulary,
    )
    frame_sha256 = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=state_id,
            payload=_payload("state", state_id),
            totalized_kind=status,
            response_coordinates=(ExactRational(coordinate),),
            frame_digest=frame_sha256,
        )
        for state_id, status, coordinate in specifications
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
        coordinate_names=("e2_coordinate",),
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
    refined = refine_exact_partition(admitted)
    verified = verify_exact_partition(admitted, refined)
    return build_exact_quotient_coordinate_generator(verified), states


def _literal_e1_fixture(selector: str) -> dict:
    if type(selector) is not str or selector not in _PARENT_SELECTORS:
        raise AssertionError("literal E2 parent selector is not frozen")
    if selector in _FIXTURE_CACHE:
        return _FIXTURE_CACHE[selector]

    source, source_states = _make_literal_side("source")
    target, target_states = _make_literal_side("target")
    matrix = _PARENT_MATRICES[selector]
    source_open0_a = "u24_e2_source_open0_a"
    source_open0_b = "u24_e2_source_open0_b"
    source_open1 = "u24_e2_source_open1"
    target_open_ids = ("u24_e2_target_open0", "u24_e2_target_open1")
    coefficients = []
    for target_index, target_id in enumerate(target_open_ids):
        ordered_source_coefficients = (
            (source_open0_a, matrix[target_index][0]),
            (source_open0_b, -matrix[target_index][0]),
            (source_open1, matrix[target_index][1]),
        )
        for source_id, coefficient in ordered_source_coefficients:
            if coefficient != 0:
                coefficients.append(
                    (
                        target_id,
                        source_id,
                        ExactRational(coefficient.numerator, coefficient.denominator),
                    )
                )

    layer = declare_synthetic_transfer_layer(source, target, tuple(coefficients))
    source_weights = make_positive_fiber_weights(
        source,
        {state.state_id: ExactRational(1) for state in source_states},
    )
    target_weights = make_positive_fiber_weights(
        target,
        {state.state_id: ExactRational(1) for state in target_states},
    )
    primary_probabilities = {
        state.state_id: ExactRational(1) for state in source_states
    }
    primary_probabilities[source_open0_a] = ExactRational(1, 3)
    primary_probabilities[source_open0_b] = ExactRational(2, 3)
    primary_law = make_exact_finite_fiber_law(source, primary_probabilities)
    source_completeness = certify_fiber_completeness(layer, "source")
    target_completeness = certify_fiber_completeness(layer, "target")
    primary_envelope = build_fiber_envelope(
        layer,
        source_weights,
        target_weights,
        primary_law,
        source_completeness,
        target_completeness,
    )
    alternate_law = None
    alternate_envelope = None
    if selector == "M0":
        alternate_probabilities = dict(primary_probabilities)
        alternate_probabilities[source_open0_a] = ExactRational(2, 3)
        alternate_probabilities[source_open0_b] = ExactRational(1, 3)
        alternate_law = make_exact_finite_fiber_law(
            source, alternate_probabilities
        )
        alternate_envelope = build_fiber_envelope(
            layer,
            source_weights,
            target_weights,
            alternate_law,
            source_completeness,
            target_completeness,
        )

    result = {
        "selector": selector,
        "matrix": matrix,
        "source_generator": source,
        "target_generator": target,
        "layer": layer,
        "source_weights": source_weights,
        "target_weights": target_weights,
        "primary_law": primary_law,
        "primary_envelope": primary_envelope,
        "alternate_law": alternate_law,
        "alternate_envelope": alternate_envelope,
        "source_completeness": source_completeness,
        "target_completeness": target_completeness,
    }
    _FIXTURE_CACHE[selector] = result
    return result


def _fixture_authorities(selector: str, law_variant: str = "PRIMARY") -> dict:
    fixture = _literal_e1_fixture(selector)
    if law_variant == "PRIMARY":
        source_law = fixture["primary_law"]
        envelope = fixture["primary_envelope"]
    elif law_variant == "ALTERNATE_M0_DIAGNOSTIC" and selector == "M0":
        source_law = fixture["alternate_law"]
        envelope = fixture["alternate_envelope"]
    else:
        raise AssertionError("literal E2 law variant is not frozen")
    return {**fixture, "source_law": source_law, "envelope": envelope}


def _identification(selector: str, law_variant: str = "PRIMARY"):
    key = (selector, law_variant)
    if key not in _IDENTIFICATION_CACHE:
        authority = _fixture_authorities(selector, law_variant)
        _IDENTIFICATION_CACHE[key] = (
            e2_certificates.identify_e2_source_target_coordinates(
                envelope=authority["envelope"],
                layer=authority["layer"],
                source_generator=authority["source_generator"],
                target_generator=authority["target_generator"],
                source_weights=authority["source_weights"],
                target_weights=authority["target_weights"],
                source_law=authority["source_law"],
                source_completeness=authority["source_completeness"],
                target_completeness=authority["target_completeness"],
            )
        )
    return _IDENTIFICATION_CACHE[key]


def _identification_from_wire(wire: dict, selector: str, law_variant: str = "PRIMARY"):
    authority = _fixture_authorities(selector, law_variant)
    return e2_certificates.SourceTargetCoordinateIdentification.from_dict(
        wire,
        envelope=authority["envelope"],
        layer=authority["layer"],
        source_generator=authority["source_generator"],
        target_generator=authority["target_generator"],
        source_weights=authority["source_weights"],
        target_weights=authority["target_weights"],
        source_law=authority["source_law"],
        source_completeness=authority["source_completeness"],
        target_completeness=authority["target_completeness"],
    )


def _restriction(selector: str, law_variant: str = "PRIMARY"):
    key = (selector, law_variant)
    if key not in _RESTRICTION_CACHE:
        authority = _fixture_authorities(selector, law_variant)
        _RESTRICTION_CACHE[key] = e2_certificates.build_e2_envelope_restriction(
            envelope=authority["envelope"],
            identification=_identification(selector, law_variant),
        )
    return _RESTRICTION_CACHE[key]


def _restriction_from_wire(wire: dict, selector: str, law_variant: str = "PRIMARY"):
    authority = _fixture_authorities(selector, law_variant)
    return e2_certificates.EnvelopeRestrictionWitness.from_dict(
        wire,
        envelope=authority["envelope"],
        identification=_identification(selector, law_variant),
    )


def _safety(selector: str, law_variant: str = "PRIMARY"):
    key = (selector, law_variant)
    if key not in _SAFETY_CACHE:
        authority = _fixture_authorities(selector, law_variant)
        _SAFETY_CACHE[key] = e2_certificates.certify_e2_lifting_uniform_safety(
            envelope=authority["envelope"],
            identification=_identification(selector, law_variant),
            restriction=_restriction(selector, law_variant),
        )
    return _SAFETY_CACHE[key]


def _safety_from_wire(wire: dict, selector: str, law_variant: str = "PRIMARY"):
    authority = _fixture_authorities(selector, law_variant)
    return e2_certificates.LiftingUniformSafetyCertificate.from_dict(
        wire,
        envelope=authority["envelope"],
        identification=_identification(selector, law_variant),
        restriction=_restriction(selector, law_variant),
    )


def _cocycle(channel: str):
    if channel not in _COCYCLE_CACHE:
        _COCYCLE_CACHE[channel] = e2_certificates.certify_e2_cocycle(
            channel=channel,
            first=_restriction("M0"),
            second=_restriction("M1"),
        )
    return _COCYCLE_CACHE[channel]


def _cocycle_from_wire(wire: dict, channel: str):
    return e2_certificates.CocycleCertificate.from_dict(
        wire,
        channel=channel,
        first=_restriction("M0"),
        second=_restriction("M1"),
    )


def _memory_split():
    if "split" not in _RETURN_CACHE:
        _RETURN_CACHE["split"] = e2_certificates.resolve_e2_memory_split(
            restriction=_restriction("MRET")
        )
    return _RETURN_CACHE["split"]


def _memory_split_from_wire(wire: dict):
    return e2_certificates.ResolvedMemorySplit.from_dict(
        wire, restriction=_restriction("MRET")
    )


def _return_memory():
    if "return" not in _RETURN_CACHE:
        _RETURN_CACHE["return"] = e2_certificates.bound_e2_finite_return_memory(
            restriction=_restriction("MRET"), split=_memory_split()
        )
    return _RETURN_CACHE["return"]


def _return_memory_from_wire(wire: dict):
    return e2_certificates.ReturnMemoryBound.from_dict(
        wire, restriction=_restriction("MRET"), split=_memory_split()
    )


def _candidate_manifest():
    if "manifest" not in _SELECTION_CACHE:
        _SELECTION_CACHE["manifest"] = (
            e2_selection.build_declared_e2_candidate_universe(
                m0_identification=_identification("M0"),
                m0_restriction=_restriction("M0"),
                m0_safety=_safety("M0"),
                m1_identification=_identification("M1"),
                m1_restriction=_restriction("M1"),
                m1_safety=_safety("M1"),
            )
        )
    return _SELECTION_CACHE["manifest"]


def _candidate_manifest_from_wire(wire: dict):
    return e2_selection.CandidateUniverseManifest.from_dict(
        wire,
        m0_identification=_identification("M0"),
        m0_restriction=_restriction("M0"),
        m0_safety=_safety("M0"),
        m1_identification=_identification("M1"),
        m1_restriction=_restriction("M1"),
        m1_safety=_safety("M1"),
    )


def _support_token():
    if "token" not in _SELECTION_CACHE:
        _SELECTION_CACHE["token"] = e2_selection.apply_e2_binding_gate(
            manifest=_candidate_manifest(),
            p1_cocycle=_cocycle("P1_BRANCHING_ADJUSTED"),
            p2_cocycle=_cocycle("P2_BRANCHING_ADJUSTED"),
            return_memory=_return_memory(),
        )
    return _SELECTION_CACHE["token"]


def _support_token_from_wire(wire: dict):
    return e2_selection.CertifiedSupportToken.from_dict(
        wire,
        manifest=_candidate_manifest(),
        p1_cocycle=_cocycle("P1_BRANCHING_ADJUSTED"),
        p2_cocycle=_cocycle("P2_BRANCHING_ADJUSTED"),
        return_memory=_return_memory(),
    )


def _assert_rational_wire(value: dict, expected: Fraction | int | None = None) -> Fraction:
    assert type(value) is dict
    assert set(value) == _RATIONAL_KEYS
    assert value["schema_version"] == "lean-rgc-odlrq-exact-rational-v1"
    numerator_text = value["numerator"]
    denominator_text = value["denominator"]
    assert type(numerator_text) is str
    assert type(denominator_text) is str
    numerator = int(numerator_text)
    denominator = int(denominator_text)
    assert str(numerator) == numerator_text
    assert denominator > 0
    assert str(denominator) == denominator_text
    assert gcd(abs(numerator), denominator) == 1
    if numerator == 0:
        assert denominator == 1
    result = Fraction(numerator, denominator)
    if expected is not None:
        assert result == Fraction(expected)
    return result


def _fraction(value: dict) -> Fraction:
    return _assert_rational_wire(value)


def _fraction_matrix(value: list[list[dict]]) -> tuple[tuple[Fraction, ...], ...]:
    assert type(value) is list
    assert all(type(row) is list for row in value)
    if value:
        assert all(len(row) == len(value[0]) for row in value)
    return tuple(tuple(_fraction(cell) for cell in row) for row in value)


def _assert_matrix_wire(
    value: list[list[dict]],
    rows: int,
    columns: int,
    expected=None,
):
    assert type(value) is list
    assert len(value) == rows
    assert all(type(row) is list and len(row) == columns for row in value)
    result = _fraction_matrix(value)
    if expected is not None:
        assert result == expected
    return result


def _frame_block(frame: dict, member_ids: tuple[str, ...]) -> dict:
    matches = [
        block
        for block in frame["blocks"]
        if tuple(member["member_id"] for member in block["members"]) == member_ids
    ]
    assert len(matches) == 1
    return matches[0]


def _matrix_product(left, right):
    return tuple(
        tuple(
            sum(
                (left[row][middle] * right[middle][column] for middle in range(len(right))),
                Fraction(0),
            )
            for column in range(len(right[0]))
        )
        for row in range(len(left))
    )


def _weighted_one_norm(matrix, source_weights, target_weights):
    return max(
        sum(
            (target_weights[row] * matrix[row][column] for row in range(len(matrix))),
            Fraction(0),
        )
        / source_weights[column]
        for column in range(len(matrix[0]))
    )


def _r(numerator: int, denominator: int = 1) -> dict:
    return ExactRational(numerator, denominator).to_dict()


def _sha256(value) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis():
    assert e2_certificates.E2_AUTHORITY_COMMIT_SHA == E2_AUTHORITY_COMMIT_SHA
    assert e2_certificates.E2_AUTHORITY_TREE_SHA == E2_AUTHORITY_TREE_SHA
    assert e2_certificates.E2_AUTHORITY_DOCUMENT_PATH == E2_AUTHORITY_DOCUMENT_PATH
    assert (
        e2_certificates.E2_AUTHORITY_DOCUMENT_BLOB_SHA
        == E2_AUTHORITY_DOCUMENT_BLOB_SHA
    )

    expected_members = {
        "OPEN_0": (
            ("u24_e2_source_open0_a", "u24_e2_source_open0_b"),
            ("u24_e2_target_open0",),
        ),
        "OPEN_1": (("u24_e2_source_open1",), ("u24_e2_target_open1",)),
        "CLOSED": (("u24_e2_source_closed",), ("u24_e2_target_closed",)),
        "SINK": (("u24_e2_source_sink",), ("u24_e2_target_sink",)),
    }
    for selector in _PARENT_SELECTORS:
        fixture = _fixture_authorities(selector)
        identification = _identification(selector)
        assert type(identification) is e2_certificates.SourceTargetCoordinateIdentification
        wire = identification.to_dict()
        assert type(wire) is dict and set(wire) == _IDENTIFICATION_KEYS
        assert wire["endpoint_id"] == "u24_e2_declared_square_endpoint_v1"
        assert wire["parent_id"] == selector
        assert wire["source_law_variant"] == "PRIMARY"
        assert wire["basis_convention"] == "target_row_source_column_v1"
        assert wire["parent_envelope_sha256"] == fixture["envelope"].envelope_sha256
        assert wire["layer_sha256"] == _sha256(fixture["layer"].to_dict())
        assert wire["source_generator_sha256"] == _sha256(
            fixture["source_generator"].to_dict()
        )
        assert wire["target_generator_sha256"] == _sha256(
            fixture["target_generator"].to_dict()
        )
        assert wire["source_weights_sha256"] == _sha256(
            fixture["source_weights"].to_dict()
        )
        assert wire["target_weights_sha256"] == _sha256(
            fixture["target_weights"].to_dict()
        )
        assert wire["source_law_sha256"] == _sha256(fixture["source_law"].to_dict())
        assert wire["source_completeness_sha256"] == _sha256(
            fixture["source_completeness"].to_dict()
        )
        assert wire["target_completeness_sha256"] == _sha256(
            fixture["target_completeness"].to_dict()
        )
        assert wire["full_coordinate_ids"] == list(_COORDINATE_IDS)
        assert wire["source_block_count"] == 4
        assert wire["target_block_count"] == 4
        assert [row["coordinate_id"] for row in wire["coordinate_rows"]] == list(
            _COORDINATE_IDS
        )
        assert [row["coordinate_role"] for row in wire["coordinate_rows"]] == [
            "RETAINED_OPEN",
            "RETAINED_OPEN",
            "TERMINAL_CLOSED",
            "TERMINAL_SINK",
        ]
        assert {row["source_block_index"] for row in wire["coordinate_rows"]} == set(
            range(4)
        )
        assert {row["target_block_index"] for row in wire["coordinate_rows"]} == set(
            range(4)
        )
        source_frame = fixture["source_completeness"].to_dict()["frame"]
        target_frame = fixture["target_completeness"].to_dict()["frame"]
        for row in wire["coordinate_rows"]:
            assert type(row) is dict and set(row) == _COORDINATE_ROW_KEYS
            source_ids, target_ids = expected_members[row["coordinate_id"]]
            assert tuple(row["source_member_ids"]) == source_ids
            assert tuple(row["target_member_ids"]) == target_ids
            source_block = _frame_block(source_frame, source_ids)
            target_block = _frame_block(target_frame, target_ids)
            assert type(row["source_block_index"]) is int
            assert type(row["target_block_index"]) is int
            assert row["source_block_index"] == source_block["block_index"]
            assert row["target_block_index"] == target_block["block_index"]
            source_members = [
                {
                    "member_id": member["member_id"],
                    "member_sha256": member["member_sha256"],
                }
                for member in source_block["members"]
            ]
            target_members = [
                {
                    "member_id": member["member_id"],
                    "member_sha256": member["member_sha256"],
                }
                for member in target_block["members"]
            ]
            assert row["source_member_set_sha256"] == _sha256(
                {
                    "schema_version": "odlrq.e2.member-set-property.v1",
                    "side": "SOURCE",
                    "coordinate_id": row["coordinate_id"],
                    "members": source_members,
                }
            )
            assert row["target_member_set_sha256"] == _sha256(
                {
                    "schema_version": "odlrq.e2.member-set-property.v1",
                    "side": "TARGET",
                    "coordinate_id": row["coordinate_id"],
                    "members": target_members,
                }
            )
            _assert_rational_wire(row["source_weight"], 1)
            _assert_rational_wire(row["target_weight"], 1)
        coordinate_core = {
            "schema_version": "odlrq.e2.coordinate-core.v1",
            "endpoint_id": "u24_e2_declared_square_endpoint_v1",
            "basis_convention": "target_row_source_column_v1",
            "layer_sha256": wire["layer_sha256"],
            "source_generator_sha256": wire["source_generator_sha256"],
            "target_generator_sha256": wire["target_generator_sha256"],
            "source_weights_sha256": wire["source_weights_sha256"],
            "target_weights_sha256": wire["target_weights_sha256"],
            "source_completeness_sha256": wire["source_completeness_sha256"],
            "target_completeness_sha256": wire["target_completeness_sha256"],
            "full_coordinate_ids": wire["full_coordinate_ids"],
            "coordinate_rows": wire["coordinate_rows"],
        }
        assert wire["coordinate_core_sha256"] == _sha256(coordinate_core)

    m0 = _fixture_authorities("M0")
    with pytest.raises(StrictContractError):
        e2_certificates.identify_e2_source_target_coordinates(
            envelope=m0["envelope"],
            layer=m0["layer"],
            source_generator=m0["target_generator"],
            target_generator=m0["source_generator"],
            source_weights=m0["source_weights"],
            target_weights=m0["target_weights"],
            source_law=m0["source_law"],
            source_completeness=m0["source_completeness"],
            target_completeness=m0["target_completeness"],
        )
    stale_completeness = _fixture_authorities("M1")
    with pytest.raises(StrictContractError):
        e2_certificates.SourceTargetCoordinateIdentification.from_dict(
            _identification("M0").to_dict(),
            envelope=m0["envelope"],
            layer=m0["layer"],
            source_generator=m0["source_generator"],
            target_generator=m0["target_generator"],
            source_weights=m0["source_weights"],
            target_weights=m0["target_weights"],
            source_law=m0["source_law"],
            source_completeness=stale_completeness["source_completeness"],
            target_completeness=m0["target_completeness"],
        )
    non_bijection = copy.deepcopy(_identification("M0").to_dict())
    non_bijection["coordinate_rows"][1]["source_block_index"] = non_bijection[
        "coordinate_rows"
    ][0]["source_block_index"]
    with pytest.raises(StrictContractError):
        _identification_from_wire(non_bijection, "M0")


def test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights():
    for selector in _PARENT_SELECTORS:
        restriction = _restriction(selector)
        assert type(restriction) is e2_certificates.EnvelopeRestrictionWitness
        wire = restriction.to_dict()
        assert type(wire) is dict and set(wire) == _RESTRICTION_KEYS
        assert wire["endpoint_id"] == "u24_e2_declared_square_endpoint_v1"
        assert wire["parent_id"] == selector
        assert wire["source_law_variant"] == "PRIMARY"
        assert wire["basis_convention"] == "target_row_source_column_v1"
        assert wire["full_coordinate_ids"] == list(_COORDINATE_IDS)
        assert wire["parent_envelope_sha256"] == _fixture_authorities(selector)[
            "envelope"
        ].envelope_sha256
        assert wire["coordinate_identification_sha256"] == _identification(
            selector
        ).coordinate_identification_sha256
        assert wire["coordinate_core_sha256"] == _identification(selector).to_dict()[
            "coordinate_core_sha256"
        ]
        _assert_matrix_wire(wire["full_matrix"], 4, 4, _PARENT_MATRICES[selector])
        restricted_expected = tuple(
            tuple(value for value in row[:2])
            for row in _PARENT_MATRICES[selector][:2]
        )
        _assert_matrix_wire(wire["restricted_matrix"], 2, 2, restricted_expected)
        assert wire["retained_coordinate_ids"] == ["OPEN_0", "OPEN_1"]
        assert wire["complement_coordinate_ids"] == ["CLOSED", "SINK"]
        expected_omitted_cells = [
            {
                "target_coordinate_id": target_coordinate_id,
                "source_coordinate_id": source_coordinate_id,
                "value": _r(0),
            }
            for target_coordinate_id in _COORDINATE_IDS
            for source_coordinate_id in _COORDINATE_IDS
            if not (
                target_coordinate_id in {"OPEN_0", "OPEN_1"}
                and source_coordinate_id in {"OPEN_0", "OPEN_1"}
            )
        ]
        assert wire["omitted_cells"] == expected_omitted_cells
        assert all(
            type(row) is dict and set(row) == _OMITTED_CELL_KEYS
            for row in wire["omitted_cells"]
        )
        assert all(_assert_rational_wire(row["value"], 0) == 0 for row in wire["omitted_cells"])
        assert wire["omitted_cell_count"] == 12
        assert wire["replayed_cell_count"] == 16
        assert wire["replay_pass"] is True
        assert [
            _assert_rational_wire(value, 1)
            for value in wire["restricted_source_weights"]
        ] == [1, 1]
        assert [
            _assert_rational_wire(value, 1)
            for value in wire["restricted_target_weights"]
        ] == [1, 1]
        matrix_property = {
            "schema_version": "odlrq.e2.matrix-property.v1",
            "endpoint_id": "u24_e2_declared_square_endpoint_v1",
            "basis_convention": "target_row_source_column_v1",
            "target_coordinate_ids": ["OPEN_0", "OPEN_1"],
            "source_coordinate_ids": ["OPEN_0", "OPEN_1"],
            "rows": wire["restricted_matrix"],
        }
        assert wire["restricted_matrix_sha256"] == _sha256(matrix_property)
        for role in ("SOURCE", "TARGET"):
            key = f"restricted_{role.lower()}_weights"
            digest_key = f"{key}_sha256"
            assert wire[digest_key] == _sha256(
                {
                    "schema_version": "odlrq.e2.weight-vector-property.v1",
                    "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                    "role": role,
                    "coordinate_ids": ["OPEN_0", "OPEN_1"],
                    "values": wire[key],
                }
            )
        assert wire["omitted_cells_sha256"] == _sha256(
            {
                "schema_version": "odlrq.e2.omitted-cells-property.v1",
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "basis_convention": "target_row_source_column_v1",
                "full_coordinate_ids": list(_COORDINATE_IDS),
                "rows": expected_omitted_cells,
            }
        )
        restriction_core = {
            "schema_version": "odlrq.e2.restriction-core.v1",
            "endpoint_id": "u24_e2_declared_square_endpoint_v1",
            "parent_id": selector,
            "basis_convention": "target_row_source_column_v1",
            "coordinate_core_sha256": wire["coordinate_core_sha256"],
            "full_coordinate_ids": wire["full_coordinate_ids"],
            "retained_coordinate_ids": wire["retained_coordinate_ids"],
            "complement_coordinate_ids": wire["complement_coordinate_ids"],
            "full_matrix": wire["full_matrix"],
            "restricted_matrix": wire["restricted_matrix"],
            "restricted_matrix_sha256": wire["restricted_matrix_sha256"],
            "restricted_source_weights": wire["restricted_source_weights"],
            "restricted_source_weights_sha256": wire[
                "restricted_source_weights_sha256"
            ],
            "restricted_target_weights": wire["restricted_target_weights"],
            "restricted_target_weights_sha256": wire[
                "restricted_target_weights_sha256"
            ],
            "omitted_cells": wire["omitted_cells"],
            "omitted_cells_sha256": wire["omitted_cells_sha256"],
            "omitted_cell_count": 12,
            "replayed_cell_count": 16,
        }
        assert wire["restriction_core_sha256"] == _sha256(restriction_core)

    with pytest.raises(StrictContractError):
        e2_certificates.EnvelopeRestrictionWitness(
            [[_r(1), _r(2)], [_r(0), _r(1, 2)]]
        )
    terminal_nonzero = copy.deepcopy(_restriction("M0").to_dict())
    terminal_nonzero["full_matrix"][2][0] = _r(1)
    with pytest.raises(StrictContractError):
        _restriction_from_wire(terminal_nonzero, "M0")
    missing_full_terminal = copy.deepcopy(_restriction("M0").to_dict())
    missing_full_terminal["full_matrix"][2].pop()
    with pytest.raises(StrictContractError):
        _restriction_from_wire(missing_full_terminal, "M0")
    missing_terminal = copy.deepcopy(_restriction("M0").to_dict())
    missing_terminal["omitted_cells"].pop()
    missing_terminal["omitted_cell_count"] = 11
    with pytest.raises(StrictContractError):
        _restriction_from_wire(missing_terminal, "M0")
    reordered = copy.deepcopy(_restriction("M0").to_dict())
    reordered["retained_coordinate_ids"] = ["OPEN_1", "OPEN_0"]
    with pytest.raises(StrictContractError):
        _restriction_from_wire(reordered, "M0")
    stale_parent = copy.deepcopy(_restriction("M0").to_dict())
    stale_parent["parent_envelope_sha256"] = "00" * 32
    with pytest.raises(StrictContractError):
        _restriction_from_wire(stale_parent, "M0")
    stale_weight = copy.deepcopy(_restriction("M0").to_dict())
    stale_weight["restricted_source_weights"][0] = _r(2)
    with pytest.raises(StrictContractError):
        _restriction_from_wire(stale_weight, "M0")


def test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free():
    primary_identification = _identification("M0")
    alternate_identification = _identification("M0", "ALTERNATE_M0_DIAGNOSTIC")
    primary_restriction = _restriction("M0")
    alternate_restriction = _restriction("M0", "ALTERNATE_M0_DIAGNOSTIC")
    primary_safety = _safety("M0")
    alternate_safety = _safety("M0", "ALTERNATE_M0_DIAGNOSTIC")
    primary_wire = primary_safety.to_dict()
    alternate_wire = alternate_safety.to_dict()
    assert type(primary_wire) is dict and set(primary_wire) == _SAFETY_KEYS
    assert type(alternate_wire) is dict and set(alternate_wire) == _SAFETY_KEYS
    for wire, law_variant in (
        (primary_wire, "PRIMARY"),
        (alternate_wire, "ALTERNATE_M0_DIAGNOSTIC"),
    ):
        assert wire["endpoint_id"] == "u24_e2_declared_square_endpoint_v1"
        assert wire["parent_id"] == "M0"
        assert wire["source_law_variant"] == law_variant
        assert wire["scope"] == (
            "all_exact_nonnegative_block_probability_laws_on_complete_declared_"
            "source_blocks_v1"
        )
    assert all(
        type(row) is dict and set(row) == _CANDIDATE_LOAD_KEYS
        for row in primary_wire["ordered_candidate_loads"]
    )
    for row in primary_wire["ordered_candidate_loads"]:
        _assert_rational_wire(row["load"])
    assert primary_wire["parent_envelope_sha256"] == _fixture_authorities("M0")[
        "envelope"
    ].envelope_sha256
    assert primary_wire["coordinate_identification_sha256"] == (
        primary_identification.coordinate_identification_sha256
    )
    assert primary_wire["envelope_restriction_sha256"] == (
        primary_restriction.envelope_restriction_sha256
    )
    assert primary_wire["source_law_sha256"] == _sha256(
        _fixture_authorities("M0")["source_law"].to_dict()
    )

    primary_fixture = _fixture_authorities("M0")
    alternate_fixture = _fixture_authorities("M0", "ALTERNATE_M0_DIAGNOSTIC")
    literal_source_members = {
        "OPEN_0": ("u24_e2_source_open0_a", "u24_e2_source_open0_b"),
        "OPEN_1": ("u24_e2_source_open1",),
        "CLOSED": ("u24_e2_source_closed",),
        "SINK": ("u24_e2_source_sink",),
    }
    literal_target_members = {
        "OPEN_0": ("u24_e2_target_open0",),
        "OPEN_1": ("u24_e2_target_open1",),
        "CLOSED": ("u24_e2_target_closed",),
        "SINK": ("u24_e2_target_sink",),
    }
    source_frame = primary_fixture["source_completeness"].to_dict()["frame"]
    target_frame = primary_fixture["target_completeness"].to_dict()["frame"]
    source_member_sha256 = {
        member["member_id"]: member["member_sha256"]
        for coordinate_id in _COORDINATE_IDS
        for member in _frame_block(
            source_frame, literal_source_members[coordinate_id]
        )["members"]
    }
    for coordinate_id in _COORDINATE_IDS:
        _frame_block(target_frame, literal_target_members[coordinate_id])
    expected_candidate_loads = []
    for target_coordinate_id in _COORDINATE_IDS:
        for source_coordinate_id in _COORDINATE_IDS:
            for source_member_id in literal_source_members[source_coordinate_id]:
                source_weight = primary_fixture["source_weights"].weight_for(
                    source_member_id
                )
                assert type(source_weight) is ExactRational
                load = Fraction(0)
                for target_member_id in literal_target_members[target_coordinate_id]:
                    coefficient = primary_fixture["layer"].coefficient_for(
                        target_member_id, source_member_id
                    )
                    target_weight = primary_fixture["target_weights"].weight_for(
                        target_member_id
                    )
                    assert type(coefficient) is ExactRational
                    assert type(target_weight) is ExactRational
                    load += (
                        abs(Fraction(coefficient.numerator, coefficient.denominator))
                        * Fraction(target_weight.numerator, target_weight.denominator)
                        / Fraction(source_weight.numerator, source_weight.denominator)
                    )
                expected_candidate_loads.append(
                    {
                        "target_coordinate_id": target_coordinate_id,
                        "source_coordinate_id": source_coordinate_id,
                        "source_member_id": source_member_id,
                        "source_member_sha256": source_member_sha256[source_member_id],
                        "load": _r(load.numerator, load.denominator),
                    }
                )
    assert len(expected_candidate_loads) == 20
    assert primary_wire["ordered_candidate_loads"] == expected_candidate_loads
    assert alternate_wire["ordered_candidate_loads"] == expected_candidate_loads
    assert canonical_contract_bytes(primary_wire["ordered_candidate_loads"]) == (
        canonical_contract_bytes(expected_candidate_loads)
    )
    assert canonical_contract_bytes(alternate_wire["ordered_candidate_loads"]) == (
        canonical_contract_bytes(expected_candidate_loads)
    )
    identification_wire = primary_identification.to_dict()
    restriction_wire = primary_restriction.to_dict()
    theorem_core = {
        "schema_version": "odlrq.e2.lifting_uniform_theorem_core.v1",
        "endpoint_id": "u24_e2_declared_square_endpoint_v1",
        "parent_id": "M0",
        "basis_convention": "target_row_source_column_v1",
        "layer_sha256": identification_wire["layer_sha256"],
        "source_generator_sha256": identification_wire["source_generator_sha256"],
        "target_generator_sha256": identification_wire["target_generator_sha256"],
        "source_weights_sha256": identification_wire["source_weights_sha256"],
        "target_weights_sha256": identification_wire["target_weights_sha256"],
        "source_completeness_sha256": identification_wire[
            "source_completeness_sha256"
        ],
        "target_completeness_sha256": identification_wire[
            "target_completeness_sha256"
        ],
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
        "restriction_core_sha256": restriction_wire["restriction_core_sha256"],
        "ordered_candidate_loads": expected_candidate_loads,
        "majorant_matrix": restriction_wire["full_matrix"],
        "scope": (
            "all_exact_nonnegative_block_probability_laws_on_complete_declared_"
            "source_blocks_v1"
        ),
    }
    assert primary_wire["theorem_core_sha256"] == _sha256(theorem_core)
    assert alternate_wire["theorem_core_sha256"] == _sha256(theorem_core)
    assert primary_fixture["envelope"].envelope_sha256 != alternate_fixture[
        "envelope"
    ].envelope_sha256
    assert (
        primary_identification.coordinate_identification_sha256
        != alternate_identification.coordinate_identification_sha256
    )
    assert (
        primary_restriction.envelope_restriction_sha256
        != alternate_restriction.envelope_restriction_sha256
    )
    assert (
        primary_safety.lifting_uniform_safety_sha256
        != alternate_safety.lifting_uniform_safety_sha256
    )
    assert primary_identification.to_dict()["coordinate_core_sha256"] == (
        alternate_identification.to_dict()["coordinate_core_sha256"]
    )
    assert primary_restriction.to_dict()["restriction_core_sha256"] == (
        alternate_restriction.to_dict()["restriction_core_sha256"]
    )
    assert primary_wire["theorem_core_sha256"] == alternate_wire[
        "theorem_core_sha256"
    ]
    assert primary_wire["ordered_candidate_loads"] == alternate_wire[
        "ordered_candidate_loads"
    ]
    assert canonical_contract_bytes(primary_wire["ordered_candidate_loads"]) == (
        canonical_contract_bytes(alternate_wire["ordered_candidate_loads"])
    )
    _assert_matrix_wire(
        primary_wire["majorant_matrix"], 4, 4, _PARENT_MATRICES["M0"]
    )
    assert primary_wire["candidate_load_count"] == 20
    assert primary_wire["matrix_cell_count"] == 16
    assert primary_wire["law_uniform"] is True
    assert primary_wire["cancellation_free"] is True

    signed_substitution = copy.deepcopy(primary_wire)
    signed_substitution["ordered_candidate_loads"][0]["load"] = _r(-1)
    with pytest.raises(StrictContractError):
        _safety_from_wire(signed_substitution, "M0")
    compressed_majorant_substitution = copy.deepcopy(primary_wire)
    compressed_majorant_substitution["majorant_matrix"][0][0] = _r(1, 3)
    with pytest.raises(StrictContractError):
        _safety_from_wire(compressed_majorant_substitution, "M0")
    law_specific_core = copy.deepcopy(primary_wire)
    law_specific_core["theorem_core_sha256"] = primary_wire["source_law_sha256"]
    with pytest.raises(StrictContractError):
        _safety_from_wire(law_specific_core, "M0")


def test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations():
    p1 = _cocycle("P1_BRANCHING_ADJUSTED")
    p2 = _cocycle("P2_BRANCHING_ADJUSTED")
    assert type(p1) is e2_certificates.CocycleCertificate
    assert type(p2) is e2_certificates.CocycleCertificate
    p1_wire = p1.to_dict()
    p2_wire = p2.to_dict()
    assert type(p1_wire) is dict and set(p1_wire) == _COCYCLE_KEYS
    assert type(p2_wire) is dict and set(p2_wire) == _COCYCLE_KEYS
    assert p1_wire["channel"] == "P1_BRANCHING_ADJUSTED"
    assert p2_wire["channel"] == "P2_BRANCHING_ADJUSTED"
    for wire in (p1_wire, p2_wire):
        assert wire["endpoint_id"] == "u24_e2_declared_square_endpoint_v1"
        assert (
            wire["composition_scope"]
            == "declared_abstract_coordinate_composition_v1"
        )
        assert wire["product_order"] == (
            "rightmost_earliest_M_hminus1_dotdot_M0_v1"
        )

    m0 = tuple(tuple(value for value in row[:2]) for row in _PARENT_MATRICES["M0"][:2])
    m1 = tuple(tuple(value for value in row[:2]) for row in _PARENT_MATRICES["M1"][:2])
    factor_sha256s = [
        _restriction("M0").envelope_restriction_sha256,
        _restriction("M1").envelope_restriction_sha256,
    ]
    for wire in (p1_wire, p2_wire):
        assert wire["factor_restriction_sha256s"] == factor_sha256s
        assert wire["ordered_source_basis"] == ["OPEN_0", "OPEN_1"]
        assert wire["ordered_intermediate_basis"] == ["OPEN_0", "OPEN_1"]
        assert wire["ordered_target_basis"] == ["OPEN_0", "OPEN_1"]
        for role, key in (
            ("SOURCE", "source_weights"),
            ("INTERMEDIATE", "intermediate_weights"),
            ("TARGET", "target_weights"),
        ):
            assert [_assert_rational_wire(value, 1) for value in wire[key]] == [1, 1]
            assert wire[f"{key}_sha256"] == _sha256(
                {
                    "schema_version": "odlrq.e2.weight-vector-property.v1",
                    "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                    "role": role,
                    "coordinate_ids": ["OPEN_0", "OPEN_1"],
                    "values": wire[key],
                }
            )
        for matrix in wire["layer_matrices"]:
            _assert_matrix_wire(matrix, 2, 2)
        _assert_matrix_wire(wire["product_matrix"], 2, 2)
        for value in wire["theta_values"]:
            _assert_rational_wire(value)
        for row in wire["componentwise_lhs_rows"]:
            assert type(row) is list and len(row) == 2
            for value in row:
                _assert_rational_wire(value)
        _assert_rational_wire(wire["product_weighted_norm"])
        _assert_rational_wire(wire["theta_product"])
    assert [_fraction_matrix(matrix) for matrix in p1_wire["layer_matrices"]] == [
        m0,
        m1,
    ]
    p1_product = _matrix_product(m1, m0)
    assert p1_product == ((Fraction(1, 2), Fraction(1)), (Fraction(3), Fraction(13, 2)))
    assert _fraction_matrix(p1_wire["product_matrix"]) == p1_product
    assert _weighted_one_norm(p1_product, (Fraction(1), Fraction(1)), (Fraction(1), Fraction(1))) == Fraction(15, 2)
    assert _fraction(p1_wire["product_weighted_norm"]) == Fraction(15, 2)
    assert _fraction(p1_wire["theta_product"]) == Fraction(35, 4)
    assert [_fraction(value) for value in p1_wire["theta_values"]] == [Fraction(5, 2), Fraction(7, 2)]
    assert [
        [_fraction(value) for value in row]
        for row in p1_wire["componentwise_lhs_rows"]
    ] == [[Fraction(1), Fraction(5, 2)], [Fraction(7, 2), Fraction(1)]]
    assert p1_wire["channel_derivation"] == "identity_positive_majorant_v1"

    m0_squared = tuple(tuple(value * value for value in row) for row in m0)
    m1_squared = tuple(tuple(value * value for value in row) for row in m1)
    assert [_fraction_matrix(matrix) for matrix in p2_wire["layer_matrices"]] == [
        m0_squared,
        m1_squared,
    ]
    p2_product = _matrix_product(m1_squared, m0_squared)
    assert p2_product == ((Fraction(1, 4), Fraction(1)), (Fraction(9), Fraction(145, 4)))
    assert _fraction_matrix(p2_wire["product_matrix"]) == p2_product
    assert _weighted_one_norm(p2_product, (Fraction(1), Fraction(1)), (Fraction(1), Fraction(1))) == Fraction(149, 4)
    assert _fraction(p2_wire["product_weighted_norm"]) == Fraction(149, 4)
    assert _fraction(p2_wire["theta_product"]) == Fraction(629, 16)
    assert [_fraction(value) for value in p2_wire["theta_values"]] == [Fraction(17, 4), Fraction(37, 4)]
    assert [
        [_fraction(value) for value in row]
        for row in p2_wire["componentwise_lhs_rows"]
    ] == [[Fraction(1), Fraction(17, 4)], [Fraction(37, 4), Fraction(1)]]
    assert p2_wire["channel_derivation"] == "entrywise_square_no_cross_terms_synthetic_v1"
    assert p1_wire["product_order"] == "rightmost_earliest_M_hminus1_dotdot_M0_v1"
    assert p2_wire["product_order"] == "rightmost_earliest_M_hminus1_dotdot_M0_v1"
    assert p1_wire["finite_horizon"] == 2
    assert p2_wire["finite_horizon"] == 2
    assert p1_wire["inequality_pass"] is True
    assert p2_wire["inequality_pass"] is True

    with pytest.raises(StrictContractError):
        e2_certificates.certify_e2_cocycle(
            channel="P1_BRANCHING_ADJUSTED",
            first=_restriction("M1"),
            second=_restriction("M0"),
        )
    wrong_derivation = copy.deepcopy(p1_wire)
    wrong_derivation["channel_derivation"] = p2_wire["channel_derivation"]
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(wrong_derivation, "P1_BRANCHING_ADJUSTED")
    p2_substitution = copy.deepcopy(p1_wire)
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(p2_substitution, "P2_BRANCHING_ADJUSTED")
    nonpositive_weight = copy.deepcopy(p1_wire)
    nonpositive_weight["intermediate_weights"][0] = _r(0)
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(nonpositive_weight, "P1_BRANCHING_ADJUSTED")
    float_weight = copy.deepcopy(p1_wire)
    float_weight["intermediate_weights"][0] = 1.0
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(float_weight, "P1_BRANCHING_ADJUSTED")


def test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact():
    split = _memory_split()
    bound = _return_memory()
    assert type(split) is e2_certificates.ResolvedMemorySplit
    assert type(bound) is e2_certificates.ReturnMemoryBound
    split_wire = split.to_dict()
    bound_wire = bound.to_dict()
    assert type(split_wire) is dict and set(split_wire) == _SPLIT_KEYS
    assert type(bound_wire) is dict and set(bound_wire) == _RETURN_KEYS
    assert split_wire["envelope_restriction_sha256"] == _restriction(
        "MRET"
    ).envelope_restriction_sha256
    assert bound_wire["envelope_restriction_sha256"] == _restriction(
        "MRET"
    ).envelope_restriction_sha256
    assert bound_wire["resolved_memory_split_sha256"] == (
        split.resolved_memory_split_sha256
    )
    assert split_wire["retained_coordinate_ids"] == ["OPEN_0", "OPEN_1"]
    assert split_wire["p_coordinate_ids"] == ["OPEN_0"]
    assert split_wire["q_coordinate_ids"] == ["OPEN_1"]
    assert _fraction_matrix(split_wire["m_pp"]) == ((Fraction(0),),)
    assert _fraction_matrix(split_wire["m_pq"]) == ((Fraction(2),),)
    assert _fraction_matrix(split_wire["m_qp"]) == ((Fraction(3),),)
    assert _fraction_matrix(split_wire["m_qq"]) == ((Fraction(1, 2),),)
    assert split_wire["split_exhaustive"] is True
    for name in ("m_pp", "m_pq", "m_qp", "m_qq"):
        _assert_matrix_wire(split_wire[name], 1, 1)
    split_core = {
        "schema_version": "odlrq.e2.memory-split-core.v1",
        "endpoint_id": "u24_e2_declared_square_endpoint_v1",
        "envelope_restriction_sha256": split_wire[
            "envelope_restriction_sha256"
        ],
        "basis_convention": "target_row_source_column_v1",
        "retained_coordinate_ids": ["OPEN_0", "OPEN_1"],
        "p_coordinate_ids": ["OPEN_0"],
        "q_coordinate_ids": ["OPEN_1"],
        "m_pp": split_wire["m_pp"],
        "m_pq": split_wire["m_pq"],
        "m_qp": split_wire["m_qp"],
        "m_qq": split_wire["m_qq"],
    }
    assert split_wire["split_core_sha256"] == _sha256(split_core)
    assert bound_wire["iteration_scope"] == "stationary_reuse_of_restricted_abstract_majorant_v1"
    assert bound_wire["finite_only"] is True
    assert bound_wire["horizon"] == 3
    for name in ("m_pp", "m_pq", "m_qp", "m_qq", "return_sum"):
        _assert_matrix_wire(bound_wire[name], 1, 1)
    assert all(
        type(row) is dict and set(row) == _POWER_TERM_KEYS
        for row in bound_wire["qq_powers"]
    )
    assert all(
        type(row) is dict and set(row) == _POWER_TERM_KEYS
        for row in bound_wire["return_terms"]
    )
    assert all(type(row["k"]) is int for row in bound_wire["qq_powers"])
    assert all(type(row["k"]) is int for row in bound_wire["return_terms"])
    assert [row["k"] for row in bound_wire["qq_powers"]] == [0, 1, 2]
    assert [row["k"] for row in bound_wire["return_terms"]] == [0, 1, 2]
    assert [_fraction_matrix(row["matrix"]) for row in bound_wire["qq_powers"]] == [
        ((Fraction(1),),),
        ((Fraction(1, 2),),),
        ((Fraction(1, 4),),),
    ]
    assert [_fraction_matrix(row["matrix"]) for row in bound_wire["return_terms"]] == [
        ((Fraction(6),),),
        ((Fraction(3),),),
        ((Fraction(3, 2),),),
    ]
    assert _fraction_matrix(bound_wire["return_sum"]) == ((Fraction(21, 2),),)
    assert _fraction(bound_wire["weighted_norm"]) == Fraction(21, 2)
    for role, key in (("SOURCE", "p_source_weights"), ("TARGET", "p_target_weights")):
        assert [_assert_rational_wire(value, 1) for value in bound_wire[key]] == [1]
        assert bound_wire[f"{key}_sha256"] == _sha256(
            {
                "schema_version": "odlrq.e2.weight-vector-property.v1",
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "role": role,
                "coordinate_ids": ["OPEN_0"],
                "values": bound_wire[key],
            }
        )
    assert bound_wire["operation_count"] == 10
    assert bound_wire["direct_zero_memory_positive"] is True

    for p_ids, q_ids in (
        ([], ["OPEN_0", "OPEN_1"]),
        (["OPEN_0"], ["OPEN_0"]),
        (["OPEN_0"], []),
        (["OPEN_1"], ["OPEN_0"]),
    ):
        invalid_split = copy.deepcopy(split_wire)
        invalid_split["p_coordinate_ids"] = p_ids
        invalid_split["q_coordinate_ids"] = q_ids
        with pytest.raises(StrictContractError):
            _memory_split_from_wire(invalid_split)
    missing_iteration = copy.deepcopy(bound_wire)
    missing_iteration["iteration_scope"] = ""
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(missing_iteration)
    unequal_stationary_weights = copy.deepcopy(bound_wire)
    unequal_stationary_weights["p_target_weights"][0] = _r(2)
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(unequal_stationary_weights)
    infinite_scope = copy.deepcopy(bound_wire)
    infinite_scope["finite_only"] = False
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(infinite_scope)


def test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed():
    transposed = copy.deepcopy(_restriction("M0").to_dict())
    matrix = transposed["restricted_matrix"]
    transposed["restricted_matrix"] = [list(row) for row in zip(*matrix)]
    with pytest.raises(StrictContractError):
        _restriction_from_wire(transposed, "M0")

    reversed_product = copy.deepcopy(_cocycle("P1_BRANCHING_ADJUSTED").to_dict())
    reversed_product["factor_restriction_sha256s"].reverse()
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(reversed_product, "P1_BRANCHING_ADJUSTED")
    basis_mismatch = copy.deepcopy(_cocycle("P1_BRANCHING_ADJUSTED").to_dict())
    basis_mismatch["ordered_intermediate_basis"] = ["OPEN_1", "OPEN_0"]
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(basis_mismatch, "P1_BRANCHING_ADJUSTED")
    weight_mismatch = copy.deepcopy(_cocycle("P1_BRANCHING_ADJUSTED").to_dict())
    weight_mismatch["intermediate_weights"][1] = _r(2)
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(weight_mismatch, "P1_BRANCHING_ADJUSTED")
    transport_substitution = copy.deepcopy(_cocycle("P1_BRANCHING_ADJUSTED").to_dict())
    transport_substitution["composition_scope"] = "raw_generator_composition_v1"
    with pytest.raises(StrictContractError):
        _cocycle_from_wire(transport_substitution, "P1_BRANCHING_ADJUSTED")
    split_reorder = copy.deepcopy(_memory_split().to_dict())
    split_reorder["retained_coordinate_ids"] = ["OPEN_1", "OPEN_0"]
    with pytest.raises(StrictContractError):
        _memory_split_from_wire(split_reorder)
    missing_stationary_tag = copy.deepcopy(_return_memory().to_dict())
    missing_stationary_tag["iteration_scope"] = "raw_e1_iteration_v1"
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(missing_stationary_tag)


def test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority():
    class _BombList(list):
        def __iter__(self):
            raise AssertionError("preflight iterated a non-exact list subtype")

    def _exact_tripwire(authority, label):
        result = copy.copy(authority)
        assert result is not authority
        assert type(result) is type(authority)

        def _authority_was_touched():
            raise AssertionError(f"authority was touched before preflight: {label}")

        object.__setattr__(result, "to_dict", _authority_was_touched)
        return result

    m0_authorities = _fixture_authorities("M0")
    identification_tripwires = {
        name: _exact_tripwire(m0_authorities[name], f"identification {name}")
        for name in (
            "envelope",
            "layer",
            "source_generator",
            "target_generator",
            "source_weights",
            "target_weights",
            "source_law",
            "source_completeness",
            "target_completeness",
        )
    }
    restriction_tripwires = {
        "envelope": _exact_tripwire(m0_authorities["envelope"], "restriction envelope"),
        "identification": _exact_tripwire(
            _identification("M0"), "restriction identification"
        ),
    }
    cocycle_tripwires = {
        "first": _exact_tripwire(_restriction("M0"), "cocycle M0 restriction"),
        "second": _exact_tripwire(_restriction("M1"), "cocycle M1 restriction"),
    }
    return_tripwires = {
        "restriction": _exact_tripwire(
            _restriction("MRET"), "return MRET restriction"
        ),
        "split": _exact_tripwire(_memory_split(), "return MRET split"),
    }
    manifest_tripwires = {
        "m0_identification": _exact_tripwire(
            _identification("M0"), "manifest M0 identification"
        ),
        "m0_restriction": _exact_tripwire(
            _restriction("M0"), "manifest M0 restriction"
        ),
        "m0_safety": _exact_tripwire(_safety("M0"), "manifest M0 safety"),
        "m1_identification": _exact_tripwire(
            _identification("M1"), "manifest M1 identification"
        ),
        "m1_restriction": _exact_tripwire(
            _restriction("M1"), "manifest M1 restriction"
        ),
        "m1_safety": _exact_tripwire(_safety("M1"), "manifest M1 safety"),
    }
    token_tripwires = {
        "manifest": _exact_tripwire(_candidate_manifest(), "token manifest"),
        "p1_cocycle": _exact_tripwire(
            _cocycle("P1_BRANCHING_ADJUSTED"), "token P1 cocycle"
        ),
        "p2_cocycle": _exact_tripwire(
            _cocycle("P2_BRANCHING_ADJUSTED"), "token P2 cocycle"
        ),
        "return_memory": _exact_tripwire(_return_memory(), "token return memory"),
    }

    def _preflight_identification(value):
        return e2_certificates.SourceTargetCoordinateIdentification.from_dict(
            value,
            envelope=identification_tripwires["envelope"],
            layer=identification_tripwires["layer"],
            source_generator=identification_tripwires["source_generator"],
            target_generator=identification_tripwires["target_generator"],
            source_weights=identification_tripwires["source_weights"],
            target_weights=identification_tripwires["target_weights"],
            source_law=identification_tripwires["source_law"],
            source_completeness=identification_tripwires["source_completeness"],
            target_completeness=identification_tripwires["target_completeness"],
        )

    def _preflight_restriction(value):
        return e2_certificates.EnvelopeRestrictionWitness.from_dict(
            value,
            envelope=restriction_tripwires["envelope"],
            identification=restriction_tripwires["identification"],
        )

    def _preflight_cocycle(value):
        return e2_certificates.CocycleCertificate.from_dict(
            value,
            channel="P1_BRANCHING_ADJUSTED",
            first=cocycle_tripwires["first"],
            second=cocycle_tripwires["second"],
        )

    def _preflight_return(value):
        return e2_certificates.ReturnMemoryBound.from_dict(
            value,
            restriction=return_tripwires["restriction"],
            split=return_tripwires["split"],
        )

    def _preflight_manifest(value):
        return e2_selection.CandidateUniverseManifest.from_dict(
            value,
            **manifest_tripwires,
        )

    def _preflight_token(value):
        return e2_selection.CertifiedSupportToken.from_dict(
            value,
            **token_tripwires,
        )

    bomb = copy.deepcopy(_identification("M0").to_dict())
    bomb["coordinate_rows"] = _BombList()
    with pytest.raises(StrictContractError):
        _preflight_identification(bomb)

    too_many_nodes = copy.deepcopy(_identification("M0").to_dict())
    too_many_nodes["parent_id"] = list(range(4097))
    with pytest.raises(StrictContractError):
        _preflight_identification(too_many_nodes)
    cardinality_bomb = copy.deepcopy(_identification("M0").to_dict())
    cardinality_bomb["coordinate_rows"].append(
        copy.deepcopy(cardinality_bomb["coordinate_rows"][0])
    )
    with pytest.raises(StrictContractError):
        _preflight_identification(cardinality_bomb)
    scalar_bomb = copy.deepcopy(_identification("M0").to_dict())
    scalar_bomb["parent_id"] = "X" * 262_145
    with pytest.raises(StrictContractError):
        _preflight_identification(scalar_bomb)
    aggregate_scalar_bomb = copy.deepcopy(_identification("M0").to_dict())
    aggregate_scalar_bomb["parent_id"] = "P" * 90_000
    aggregate_scalar_bomb["source_law_variant"] = "L" * 90_000
    aggregate_scalar_bomb["basis_convention"] = "B" * 90_000
    with pytest.raises(StrictContractError):
        _preflight_identification(aggregate_scalar_bomb)
    depth_bomb = copy.deepcopy(_identification("M0").to_dict())
    nested = "leaf"
    for _ in range(13):
        nested = [nested]
    depth_bomb["parent_id"] = nested
    with pytest.raises(StrictContractError):
        _preflight_identification(depth_bomb)
    cycle_bomb = copy.deepcopy(_identification("M0").to_dict())
    cycle = []
    cycle.append(cycle)
    cycle_bomb["parent_id"] = cycle
    with pytest.raises(StrictContractError):
        _preflight_identification(cycle_bomb)
    matrix_cell_bomb = copy.deepcopy(_restriction("M0").to_dict())
    matrix_cell_bomb["full_matrix"].append([_r(0), _r(0), _r(0), _r(0)])
    with pytest.raises(StrictContractError):
        _preflight_restriction(matrix_cell_bomb)
    horizon_bomb = copy.deepcopy(_return_memory().to_dict())
    horizon_bomb["horizon"] = 4
    with pytest.raises(StrictContractError):
        _preflight_return(horizon_bomb)
    return_term_bomb = copy.deepcopy(_return_memory().to_dict())
    return_term_bomb["return_terms"].append({"k": 3, "matrix": [[_r(1)]]})
    with pytest.raises(StrictContractError):
        _preflight_return(return_term_bomb)
    work_substitution = copy.deepcopy(_cocycle("P1_BRANCHING_ADJUSTED").to_dict())
    work_substitution["layer_matrices"].append(copy.deepcopy(work_substitution["layer_matrices"][0]))
    with pytest.raises(StrictContractError):
        _preflight_cocycle(work_substitution)
    manifest_cardinality_bomb = copy.deepcopy(_candidate_manifest().to_dict())
    manifest_cardinality_bomb["candidate_rows"].append(
        copy.deepcopy(manifest_cardinality_bomb["candidate_rows"][0])
    )
    with pytest.raises(StrictContractError):
        _preflight_manifest(manifest_cardinality_bomb)
    token_cardinality_bomb = copy.deepcopy(_support_token().to_dict())
    token_cardinality_bomb["decision_rows"].append(
        copy.deepcopy(token_cardinality_bomb["decision_rows"][0])
    )
    with pytest.raises(StrictContractError):
        _preflight_token(token_cardinality_bomb)


def test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary():
    manifest = _candidate_manifest()
    assert type(manifest) is e2_selection.CandidateUniverseManifest
    wire = manifest.to_dict()
    assert type(wire) is dict and set(wire) == _MANIFEST_KEYS
    assert wire["universe_id"] == "u24_e2_literal_three_candidate_universe_v1"
    assert wire["sealed_before_threshold"] is True
    assert wire["pre_gate_complete"] is True
    assert wire["candidate_count"] == 3
    assert wire["canonical_candidate_ids"] == ["c0", "c1", "c2"]
    assert [row["candidate_id"] for row in wire["candidate_rows"]] == ["c0", "c1", "c2"]
    assert [_fraction(row["bound"]) for row in wire["candidate_rows"]] == [1, 3, 2]
    assert [_fraction(row["utility"]) for row in wire["candidate_rows"]] == [1, 9, 4]
    assert [row["source_coordinate_ids"] for row in wire["candidate_rows"]] == [
        ["OPEN_0"],
        ["OPEN_0"],
        ["OPEN_1"],
    ]
    expected_candidates = (
        {
            "candidate_id": "c0",
            "action_id": "E2_SYNTHETIC_C0",
            "parent_id": "M0",
            "target_coordinate_id": "OPEN_0",
            "source_coordinate_id": "OPEN_0",
            "source_coordinate_ids": ["OPEN_0"],
        },
        {
            "candidate_id": "c1",
            "action_id": "E2_SYNTHETIC_C1",
            "parent_id": "M1",
            "target_coordinate_id": "OPEN_1",
            "source_coordinate_id": "OPEN_0",
            "source_coordinate_ids": ["OPEN_0"],
        },
        {
            "candidate_id": "c2",
            "action_id": "E2_SYNTHETIC_C2",
            "parent_id": "M0",
            "target_coordinate_id": "OPEN_0",
            "source_coordinate_id": "OPEN_1",
            "source_coordinate_ids": ["OPEN_1"],
        },
    )
    for row, expected in zip(wire["candidate_rows"], expected_candidates, strict=True):
        assert type(row) is dict and set(row) == _CANDIDATE_ROW_KEYS
        assert row["candidate_id"] == expected["candidate_id"]
        assert row["parent_id"] == expected["parent_id"]
        assert row["target_coordinate_id"] == expected["target_coordinate_id"]
        assert row["source_coordinate_id"] == expected["source_coordinate_id"]
        assert row["source_coordinate_ids"] == expected["source_coordinate_ids"]
        parent_id = expected["parent_id"]
        assert row["parent_envelope_sha256"] == _fixture_authorities(parent_id)[
            "envelope"
        ].envelope_sha256
        assert row["coordinate_identification_sha256"] == _identification(
            parent_id
        ).coordinate_identification_sha256
        assert row["envelope_restriction_sha256"] == _restriction(
            parent_id
        ).envelope_restriction_sha256
        assert row["lifting_uniform_safety_sha256"] == _safety(
            parent_id
        ).lifting_uniform_safety_sha256
        expected_payload = {
            "schema_version": "odlrq.e2.synthetic-candidate.v1",
            "candidate_id": expected["candidate_id"],
            "declared_action_id": expected["action_id"],
        }
        assert row["candidate_payload_sha256"] == _sha256(expected_payload)
        coordinate_core_sha256 = _identification(parent_id).to_dict()[
            "coordinate_core_sha256"
        ]
        expected_membership = {
            "endpoint_id": "u24_e2_declared_square_endpoint_v1",
            "candidate_id": expected["candidate_id"],
            "candidate_payload_sha256": row["candidate_payload_sha256"],
            "parent_id": parent_id,
            "source_coordinate_ids": expected["source_coordinate_ids"],
            "source_coordinate_id": expected["source_coordinate_id"],
            "coordinate_core_sha256": coordinate_core_sha256,
        }
        assert row["membership_core_sha256"] == _sha256(expected_membership)
    manifest_core = {
        key: value
        for key, value in wire.items()
        if key not in {"manifest_core_sha256", "verification_disposition"}
    }
    manifest_core["schema_version"] = "odlrq.e2.candidate-universe-core.v1"
    assert wire["manifest_core_sha256"] == _sha256(manifest_core)

    with pytest.raises(StrictContractError):
        e2_selection.CandidateUniverseManifest()
    for mutation in ("missing", "duplicate", "reordered", "generic", "unrelated"):
        invalid = copy.deepcopy(wire)
        if mutation == "missing":
            invalid["candidate_rows"].pop(1)
        elif mutation == "duplicate":
            invalid["candidate_rows"][1] = copy.deepcopy(invalid["candidate_rows"][0])
        elif mutation == "reordered":
            invalid["candidate_rows"][0], invalid["candidate_rows"][1] = (
                invalid["candidate_rows"][1],
                invalid["candidate_rows"][0],
            )
        elif mutation == "generic":
            invalid["candidate_rows"][0]["candidate_id"] = "c3"
        else:
            invalid["candidate_rows"][0]["source_coordinate_ids"] = ["OPEN_1"]
        with pytest.raises(StrictContractError):
            _candidate_manifest_from_wire(invalid)

    token_wire = _support_token().to_dict()
    boundary_row = next(row for row in token_wire["decision_rows"] if row["candidate_id"] == "c2")
    assert _fraction(boundary_row["bound"]) == _fraction(boundary_row["threshold"]) == 2
    assert boundary_row["decision"] == "ACCEPT"


def test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding():
    token = _support_token()
    assert type(token) is e2_selection.CertifiedSupportToken
    wire = token.to_dict()
    assert type(wire) is dict and set(wire) == _TOKEN_KEYS
    assert all(
        type(row) is dict and set(row) == _DECISION_ROW_KEYS
        for row in wire["decision_rows"]
    )
    for row in wire["decision_rows"]:
        _assert_rational_wire(row["bound"])
        _assert_rational_wire(row["threshold"], 2)
    assert wire["candidate_universe_manifest_sha256"] == (
        _candidate_manifest().candidate_universe_manifest_sha256
    )
    assert wire["p1_cocycle_sha256"] == _cocycle(
        "P1_BRANCHING_ADJUSTED"
    ).cocycle_certificate_sha256
    assert wire["p2_cocycle_sha256"] == _cocycle(
        "P2_BRANCHING_ADJUSTED"
    ).cocycle_certificate_sha256
    assert wire["return_memory_bound_sha256"] == (
        _return_memory().return_memory_bound_sha256
    )
    assert wire["comparator"] == "exact_rational_less_equal_v1"
    assert _fraction(wire["threshold"]) == 2
    assert wire["denominator"] == 3
    assert wire["numerator"] == 2
    assert _fraction(wire["coverage"]) == Fraction(2, 3)
    assert wire["ungated_ranking"] == ["c1", "c2", "c0"]
    assert wire["gated_ranking"] == ["c2", "c0"]
    assert wire["support_candidate_ids"] == ["c0", "c2"]
    assert wire["rejected_candidate_ids"] == ["c1"]
    assert wire["abstained_candidate_ids"] == []
    assert wire["ranking_changed"] is True
    assert wire["ungated_ranking"][0] == "c1"
    assert wire["gated_ranking"][0] == "c2"
    assert [row["decision"] for row in wire["decision_rows"]] == [
        "ACCEPT",
        "REJECT",
        "ACCEPT",
    ]
    assert [row["reason"] for row in wire["decision_rows"]] == [
        "BOUND_LE_THRESHOLD",
        "BOUND_GT_THRESHOLD",
        "BOUND_LE_THRESHOLD",
    ]
    candidate_rows = {
        row["candidate_id"]: row for row in _candidate_manifest().to_dict()["candidate_rows"]
    }
    for row in wire["decision_rows"]:
        expected_bundle = {
            "schema_version": "odlrq.e2.decision-authority-bundle.v1",
            "candidate_row": candidate_rows[row["candidate_id"]],
            "p1_cocycle_sha256": _cocycle(
                "P1_BRANCHING_ADJUSTED"
            ).cocycle_certificate_sha256,
            "p2_cocycle_sha256": _cocycle(
                "P2_BRANCHING_ADJUSTED"
            ).cocycle_certificate_sha256,
            "return_memory_bound_sha256": _return_memory().return_memory_bound_sha256,
        }
        assert row["authority_bundle_sha256"] == _sha256(expected_bundle)
    invalidation = {
        key: value
        for key, value in wire.items()
        if key not in {"invalidation_sha256", "verification_disposition"}
    }
    invalidation["schema_version"] = "odlrq.e2.support-invalidation.v1"
    assert wire["invalidation_sha256"] == _sha256(invalidation)

    with pytest.raises(StrictContractError):
        e2_selection.CertifiedSupportToken()
    invalid_variants = []
    strict_less = copy.deepcopy(wire)
    strict_less["comparator"] = "exact_rational_less_than_v1"
    invalid_variants.append(strict_less)
    denominator_two = copy.deepcopy(wire)
    denominator_two["denominator"] = 2
    invalid_variants.append(denominator_two)
    dropped_reject = copy.deepcopy(wire)
    dropped_reject["decision_rows"].pop(1)
    invalid_variants.append(dropped_reject)
    abstain = copy.deepcopy(wire)
    abstain["decision_rows"][1]["decision"] = "ABSTAIN"
    invalid_variants.append(abstain)
    empty_support = copy.deepcopy(wire)
    empty_support["support_candidate_ids"] = []
    empty_support["gated_ranking"] = []
    invalid_variants.append(empty_support)
    stale_digest = copy.deepcopy(wire)
    stale_digest["invalidation_sha256"] = "00" * 32
    invalid_variants.append(stale_digest)
    for invalid in invalid_variants:
        with pytest.raises(StrictContractError):
            _support_token_from_wire(invalid)

    with pytest.raises(StrictContractError):
        e2_selection.apply_e2_binding_gate(
            manifest=_candidate_manifest(),
            p1_cocycle=_cocycle("P2_BRANCHING_ADJUSTED"),
            p2_cocycle=_cocycle("P1_BRANCHING_ADJUSTED"),
            return_memory=_return_memory(),
        )


def test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback():
    identification = _identification("M0")
    restriction = _restriction("M0")
    safety = _safety("M0")
    split = _memory_split()
    cocycle = _cocycle("P1_BRANCHING_ADJUSTED")
    return_memory = _return_memory()
    manifest = _candidate_manifest()
    token = _support_token()

    digest_and_disposition_checks = (
        (
            identification,
            "coordinate_identification_sha256",
            "E2_SOURCE_TARGET_COORDINATES_IDENTIFIED",
        ),
        (
            restriction,
            "envelope_restriction_sha256",
            "E2_ENVELOPE_RESTRICTION_REPLAYED",
        ),
        (
            safety,
            "lifting_uniform_safety_sha256",
            "E2_DECLARED_FINITE_LIFTING_UNIFORM_VERIFIED",
        ),
        (split, "resolved_memory_split_sha256", "E2_MEMORY_SPLIT_RESOLVED"),
        (
            cocycle,
            "cocycle_certificate_sha256",
            "E2_FINITE_ABSTRACT_COCYCLE_VERIFIED",
        ),
        (
            return_memory,
            "return_memory_bound_sha256",
            "E2_FINITE_RETURN_MEMORY_BOUNDED",
        ),
        (
            manifest,
            "candidate_universe_manifest_sha256",
            "E2_DECLARED_CANDIDATE_UNIVERSE_SEALED",
        ),
        (
            token,
            "certified_support_token_sha256",
            "E2_BINDING_SUPPORT_CERTIFIED",
        ),
    )
    for value, digest_property, disposition in digest_and_disposition_checks:
        full_wire = value.to_dict()
        assert getattr(value, digest_property) == _sha256(full_wire)
        assert full_wire["verification_disposition"] == disposition

    fixed_outer_literals = (
        (
            identification,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "parent_id": "M0",
                "source_law_variant": "PRIMARY",
                "basis_convention": "target_row_source_column_v1",
                "full_coordinate_ids": ["OPEN_0", "OPEN_1", "CLOSED", "SINK"],
            },
        ),
        (
            restriction,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "parent_id": "M0",
                "source_law_variant": "PRIMARY",
                "basis_convention": "target_row_source_column_v1",
                "full_coordinate_ids": ["OPEN_0", "OPEN_1", "CLOSED", "SINK"],
                "retained_coordinate_ids": ["OPEN_0", "OPEN_1"],
                "complement_coordinate_ids": ["CLOSED", "SINK"],
            },
        ),
        (
            safety,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "parent_id": "M0",
                "source_law_variant": "PRIMARY",
                "scope": (
                    "all_exact_nonnegative_block_probability_laws_on_complete_"
                    "declared_source_blocks_v1"
                ),
                "coordinate_core_sha256": identification.to_dict()[
                    "coordinate_core_sha256"
                ],
                "restriction_core_sha256": restriction.to_dict()[
                    "restriction_core_sha256"
                ],
            },
        ),
        (
            split,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "basis_convention": "target_row_source_column_v1",
                "retained_coordinate_ids": ["OPEN_0", "OPEN_1"],
                "p_coordinate_ids": ["OPEN_0"],
                "q_coordinate_ids": ["OPEN_1"],
                "split_exhaustive": True,
            },
        ),
        (
            cocycle,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "channel": "P1_BRANCHING_ADJUSTED",
                "channel_derivation": "identity_positive_majorant_v1",
                "composition_scope": "declared_abstract_coordinate_composition_v1",
                "product_order": "rightmost_earliest_M_hminus1_dotdot_M0_v1",
                "ordered_source_basis": ["OPEN_0", "OPEN_1"],
                "ordered_intermediate_basis": ["OPEN_0", "OPEN_1"],
                "ordered_target_basis": ["OPEN_0", "OPEN_1"],
            },
        ),
        (
            return_memory,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "iteration_scope": "stationary_reuse_of_restricted_abstract_majorant_v1",
                "finite_only": True,
                "horizon": 3,
                "operation_count": 10,
                "direct_zero_memory_positive": True,
            },
        ),
        (
            manifest,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "universe_id": "u24_e2_literal_three_candidate_universe_v1",
                "sealed_before_threshold": True,
                "candidate_count": 3,
                "canonical_candidate_ids": ["c0", "c1", "c2"],
                "pre_gate_complete": True,
            },
        ),
        (
            token,
            {
                "endpoint_id": "u24_e2_declared_square_endpoint_v1",
                "comparator": "exact_rational_less_equal_v1",
                "denominator": 3,
                "numerator": 2,
                "ranking_changed": True,
            },
        ),
    )
    for value, expected_literals in fixed_outer_literals:
        full_wire = value.to_dict()
        for name, expected in expected_literals.items():
            assert full_wire[name] == expected

    roundtrips = (
        (
            _identification_from_wire,
            identification,
            ("M0",),
            _IDENTIFICATION_KEYS,
            "odlrq.e2.source-target-coordinate-identification.v1",
            ("coordinate_rows", 0, "coordinate_id"),
        ),
        (
            _restriction_from_wire,
            restriction,
            ("M0",),
            _RESTRICTION_KEYS,
            "odlrq.e2.envelope-restriction.v1",
            ("full_matrix", 0, 0, "numerator"),
        ),
        (
            _safety_from_wire,
            safety,
            ("M0",),
            _SAFETY_KEYS,
            "odlrq.e2.lifting-uniform-safety.v1",
            ("ordered_candidate_loads", 0, "load", "numerator"),
        ),
        (
            _memory_split_from_wire,
            split,
            (),
            _SPLIT_KEYS,
            "odlrq.e2.resolved-memory-split.v1",
            ("m_pp", 0, 0, "numerator"),
        ),
        (
            _cocycle_from_wire,
            cocycle,
            ("P1_BRANCHING_ADJUSTED",),
            _COCYCLE_KEYS,
            "odlrq.e2.cocycle-certificate.v1",
            ("layer_matrices", 0, 0, 0, "numerator"),
        ),
        (
            _return_memory_from_wire,
            return_memory,
            (),
            _RETURN_KEYS,
            "odlrq.e2.finite-return-memory.v1",
            ("qq_powers", 0, "matrix", 0, 0, "numerator"),
        ),
        (
            _candidate_manifest_from_wire,
            manifest,
            (),
            _MANIFEST_KEYS,
            "odlrq.e2.candidate-universe-manifest.v1",
            ("candidate_rows", 0, "candidate_id"),
        ),
        (
            _support_token_from_wire,
            token,
            (),
            _TOKEN_KEYS,
            "odlrq.e2.certified-support-token.v1",
            ("decision_rows", 0, "decision"),
        ),
    )
    for parser, value, arguments, exact_keys, schema, nested_path in roundtrips:
        wire = value.to_dict()
        baseline = copy.deepcopy(wire)
        assert type(wire) is dict and set(wire) == exact_keys
        assert wire["schema_version"] == schema
        parsed = parser(copy.deepcopy(wire), *arguments)
        assert type(parsed) is type(value)
        assert parsed.to_dict() == wire
        permissive = copy.deepcopy(wire)
        permissive["extra"] = "forbidden"
        with pytest.raises(StrictContractError):
            parser(permissive, *arguments)
        wire["schema_version"] = "MUTATED_RETURNED_TOP_LEVEL"
        assert value.to_dict() == baseline
        nested_return = value.to_dict()
        cursor = nested_return
        for component in nested_path[:-1]:
            cursor = cursor[component]
        cursor[nested_path[-1]] = "MUTATED_RETURNED_NESTED_VALUE"
        assert value.to_dict() == baseline

    unreduced_rational = restriction.to_dict()
    unreduced_rational["restricted_matrix"][0][0] = {
        "schema_version": "lean-rgc-odlrq-exact-rational-v1",
        "numerator": "2",
        "denominator": "2",
    }
    with pytest.raises(StrictContractError):
        _restriction_from_wire(unreduced_rational, "M0")
    permissive_rational = restriction.to_dict()
    permissive_rational["restricted_matrix"][0][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _restriction_from_wire(permissive_rational, "M0")
    noncanonical_rational = restriction.to_dict()
    noncanonical_rational["restricted_matrix"][0][0]["numerator"] = "01"
    with pytest.raises(StrictContractError):
        _restriction_from_wire(noncanonical_rational, "M0")
    manifest_rational_extra = manifest.to_dict()
    manifest_rational_extra["candidate_rows"][0]["bound"]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _candidate_manifest_from_wire(manifest_rational_extra)
    token_unreduced_rational = token.to_dict()
    token_unreduced_rational["threshold"] = {
        "schema_version": "lean-rgc-odlrq-exact-rational-v1",
        "numerator": "4",
        "denominator": "2",
    }
    with pytest.raises(StrictContractError):
        _support_token_from_wire(token_unreduced_rational)

    coordinate_row_extra = identification.to_dict()
    coordinate_row_extra["coordinate_rows"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _identification_from_wire(coordinate_row_extra, "M0")
    omitted_row_extra = restriction.to_dict()
    omitted_row_extra["omitted_cells"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _restriction_from_wire(omitted_row_extra, "M0")
    candidate_load_extra = safety.to_dict()
    candidate_load_extra["ordered_candidate_loads"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _safety_from_wire(candidate_load_extra, "M0")
    qq_power_extra = return_memory.to_dict()
    qq_power_extra["qq_powers"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(qq_power_extra)
    return_term_extra = return_memory.to_dict()
    return_term_extra["return_terms"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _return_memory_from_wire(return_term_extra)
    candidate_row_extra = manifest.to_dict()
    candidate_row_extra["candidate_rows"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _candidate_manifest_from_wire(candidate_row_extra)
    decision_row_extra = token.to_dict()
    decision_row_extra["decision_rows"][0]["extra"] = "forbidden"
    with pytest.raises(StrictContractError):
        _support_token_from_wire(decision_row_extra)

    public_types = (
        e2_certificates.SourceTargetCoordinateIdentification,
        e2_certificates.EnvelopeRestrictionWitness,
        e2_certificates.LiftingUniformSafetyCertificate,
        e2_certificates.ResolvedMemorySplit,
        e2_certificates.CocycleCertificate,
        e2_certificates.ReturnMemoryBound,
        e2_selection.CandidateUniverseManifest,
        e2_selection.CertifiedSupportToken,
    )
    for public_type in public_types:
        with pytest.raises(StrictContractError):
            public_type()

    m0_authorities = _fixture_authorities("M0")
    subclass_cases = (
        (
            e2_certificates.SourceTargetCoordinateIdentification,
            identification.to_dict(),
            {
                "envelope": m0_authorities["envelope"],
                "layer": m0_authorities["layer"],
                "source_generator": m0_authorities["source_generator"],
                "target_generator": m0_authorities["target_generator"],
                "source_weights": m0_authorities["source_weights"],
                "target_weights": m0_authorities["target_weights"],
                "source_law": m0_authorities["source_law"],
                "source_completeness": m0_authorities["source_completeness"],
                "target_completeness": m0_authorities["target_completeness"],
            },
        ),
        (
            e2_certificates.EnvelopeRestrictionWitness,
            restriction.to_dict(),
            {
                "envelope": m0_authorities["envelope"],
                "identification": identification,
            },
        ),
        (
            e2_certificates.LiftingUniformSafetyCertificate,
            safety.to_dict(),
            {
                "envelope": m0_authorities["envelope"],
                "identification": identification,
                "restriction": restriction,
            },
        ),
        (
            e2_certificates.ResolvedMemorySplit,
            split.to_dict(),
            {"restriction": _restriction("MRET")},
        ),
        (
            e2_certificates.CocycleCertificate,
            cocycle.to_dict(),
            {
                "channel": "P1_BRANCHING_ADJUSTED",
                "first": _restriction("M0"),
                "second": _restriction("M1"),
            },
        ),
        (
            e2_certificates.ReturnMemoryBound,
            return_memory.to_dict(),
            {"restriction": _restriction("MRET"), "split": split},
        ),
        (
            e2_selection.CandidateUniverseManifest,
            manifest.to_dict(),
            {
                "m0_identification": _identification("M0"),
                "m0_restriction": _restriction("M0"),
                "m0_safety": _safety("M0"),
                "m1_identification": _identification("M1"),
                "m1_restriction": _restriction("M1"),
                "m1_safety": _safety("M1"),
            },
        ),
        (
            e2_selection.CertifiedSupportToken,
            token.to_dict(),
            {
                "manifest": manifest,
                "p1_cocycle": _cocycle("P1_BRANCHING_ADJUSTED"),
                "p2_cocycle": _cocycle("P2_BRANCHING_ADJUSTED"),
                "return_memory": return_memory,
            },
        ),
    )
    exact_values_by_type = {
        type(value): value
        for value in (
            identification,
            restriction,
            safety,
            split,
            cocycle,
            return_memory,
            manifest,
            token,
        )
    }
    for public_type, wire, retained_authorities in subclass_cases:
        forbidden_subclass = type(
            f"_Forbidden{public_type.__name__}", (public_type,), {}
        )
        with pytest.raises(StrictContractError):
            forbidden_subclass()
        with pytest.raises(StrictContractError):
            forbidden_subclass.from_dict(
                copy.deepcopy(wire), **retained_authorities
            )
        forged_subclass_value = object.__new__(forbidden_subclass)
        for name, retained_value in exact_values_by_type[public_type].__dict__.items():
            object.__setattr__(forged_subclass_value, name, retained_value)
        with pytest.raises(StrictContractError):
            forged_subclass_value.to_dict()

    stale_bundle = copy.deepcopy(token.to_dict())
    stale_bundle["decision_rows"][0]["authority_bundle_sha256"] = "00" * 32
    with pytest.raises(StrictContractError):
        _support_token_from_wire(stale_bundle)
    with pytest.raises(StrictContractError):
        e2_certificates.build_e2_envelope_restriction(
            envelope=_fixture_authorities("M0")["envelope"],
            identification=object(),
        )
    with pytest.raises(StrictContractError):
        e2_selection.build_declared_e2_candidate_universe(
            m0_identification=_identification("M0"),
            m0_restriction=_restriction("M0"),
            m0_safety=_safety("M1"),
            m1_identification=_identification("M1"),
            m1_restriction=_restriction("M1"),
            m1_safety=_safety("M1"),
        )

    support = token.to_dict()["support_candidate_ids"]
    nominal_failure_fallback = min(support)
    assert nominal_failure_fallback == "c0"
    assert nominal_failure_fallback in support
    assert "c1" not in support
