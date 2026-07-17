from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import inspect
import json
import math

import pytest

from lean_rgc.odlrq import maxent as me
from lean_rgc.odlrq.contracts import (
    ExactRational,
    StrictContractError,
    canonical_contract_bytes,
)


ME0_AUTHORITY_COMMIT_SHA = "0ff63861a2957b53f4c0b5f2948d561d936337ca"
ME0_AUTHORITY_PARENT_SHA = "7a8b28872439dd61d40174c2500c5990790002be"
ME0_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md"
)
ME0_AUTHORITY_DOCUMENT_BLOB_SHA = "831c226a2b25ae367b288a8fb18d7cb7afb42124"
ME0_AUTHORITY_CI_RUN_ID = "29551068987"
ME0_AUTHORITY_CI_JOB_ID = "87793466452"
ACCEPTED_E2_COMMIT_SHA = "7a8b28872439dd61d40174c2500c5990790002be"
ACCEPTED_E2_TREE_SHA = "d54ed9fab52da4929843fabdeb3c1e1920994f6a"
WINDOWS_RUNTIME_MANIFEST_SHA256 = (
    "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
)
TOKEN_SHA256 = "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"


_TOKEN_JSON = r'''{"abstained_candidate_ids":[],"candidate_universe_manifest_sha256":"327DDC3DBD63C049A1B16B570B81F5DDECCE1B8C3C7F83734609C83B12501D9A","comparator":"exact_rational_less_equal_v1","coverage":{"denominator":"3","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"decision_rows":[{"authority_bundle_sha256":"6B29E9EC02EBBC4C36A1AD4B9A485E54954D05345E4DCB8BE2135A3D61B6BF2C","bound":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c0","decision":"ACCEPT","reason":"BOUND_LE_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"authority_bundle_sha256":"AF2491D9640434CFD7798465887A28138F2879C7C31608C204F12A4E53E6630E","bound":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c1","decision":"REJECT","reason":"BOUND_GT_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"authority_bundle_sha256":"FF2C37D9A917559DC759512162EA82E72A5CED7F558EF624A577876F152F97C4","bound":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_id":"c2","decision":"ACCEPT","reason":"BOUND_LE_THRESHOLD","threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"denominator":3,"endpoint_id":"u24_e2_declared_square_endpoint_v1","gated_ranking":["c2","c0"],"invalidation_sha256":"B83E0F2608123C8EAC140332DA5F00E5B2F293229EC44D6087628B93DBF591EB","numerator":2,"p1_cocycle_sha256":"6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11","p2_cocycle_sha256":"BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D","ranking_changed":true,"rejected_candidate_ids":["c1"],"return_memory_bound_sha256":"95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46","schema_version":"odlrq.e2.certified-support-token.v1","support_candidate_ids":["c0","c2"],"threshold":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"ungated_ranking":["c1","c2","c0"],"verification_disposition":"E2_BINDING_SUPPORT_CERTIFIED"}'''


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return ExactRational(numerator, denominator)


def _token_wire() -> dict:
    return json.loads(_TOKEN_JSON)


def _reference() -> me.DeclaredE2SupportReference:
    return me.make_declared_e2_support_reference(
        _token_wire(),
        accepted_e2_commit_sha=ACCEPTED_E2_COMMIT_SHA,
        accepted_e2_tree_sha=ACCEPTED_E2_TREE_SHA,
    )


def _problem(
    *,
    target: ExactRational = ExactRational(1),
    statistics: tuple[ExactRational, ExactRational] = (
        ExactRational(0),
        ExactRational(2),
    ),
    orbit_sizes: tuple[int, int] = (1, 1),
    reference_mass: tuple[ExactRational, ExactRational] = (
        ExactRational(1, 2),
        ExactRational(1, 2),
    ),
    kl_radius: ExactRational = ExactRational(1, 20),
    input_rational_override: ExactRational | None = None,
    statistic_dimension: int = 1,
    exact_rule_column_count: int = 1,
) -> me.MaxEntProblem:
    if input_rational_override is not None:
        reference_mass = (input_rational_override, _r(1, 2))
    statistic_c0 = (statistics[0],) + tuple(
        _r(0) for _ in range(statistic_dimension - 1)
    )
    statistic_c2 = (statistics[1],) + tuple(
        _r(0) for _ in range(statistic_dimension - 1)
    )
    column_ids = tuple(f"g{index}" for index in range(exact_rule_column_count))
    rule_c0 = tuple(_r(1) for _ in range(exact_rule_column_count))
    rule_c2 = tuple(_r(2) for _ in range(exact_rule_column_count))
    return me.MaxEntProblem.create(
        _reference(),
        reference_mass_rows=(
            ("c0", reference_mass[0]),
            ("c2", reference_mass[1]),
        ),
        statistic_rows=(
            ("c0", statistic_c0),
            ("c2", statistic_c2),
        ),
        orbit_size_rows=(("c0", orbit_sizes[0]), ("c2", orbit_sizes[1])),
        target=(target,) + tuple(_r(0) for _ in range(statistic_dimension - 1)),
        kl_radius=kl_radius,
        row_load_rows=(("c0", _r(1)), ("c2", _r(3))),
        nominal_operator_rows=(("c0", _r(2)), ("c2", _r(4))),
        exact_rule_column_ids=column_ids,
        exact_rule_rows=(("c0", rule_c0), ("c2", rule_c2)),
    )


def _status(value: object) -> me.MaxEntStatus:
    status = getattr(value, "status")
    assert type(status) is me.MaxEntStatus
    return status


def _floats(wire_values: list[str] | tuple[str, ...]) -> tuple[float, ...]:
    return tuple(float(value) for value in wire_values)


def test_me0_frozen_token_wire_rehashes_and_live_binding_rejects_counterfeit_rows():
    wire = _token_wire()
    encoded = canonical_contract_bytes(wire)
    assert len(encoded) == 2185
    assert hashlib.sha256(encoded).hexdigest().upper() == TOKEN_SHA256
    assert wire["support_candidate_ids"] == ["c0", "c2"]

    assert me.ME0_AUTHORITY_COMMIT_SHA == ME0_AUTHORITY_COMMIT_SHA
    assert me.ME0_AUTHORITY_PARENT_SHA == ME0_AUTHORITY_PARENT_SHA
    assert me.ME0_AUTHORITY_DOCUMENT_PATH == ME0_AUTHORITY_DOCUMENT_PATH
    assert me.ME0_AUTHORITY_DOCUMENT_BLOB_SHA == ME0_AUTHORITY_DOCUMENT_BLOB_SHA
    assert me.ME0_AUTHORITY_CI_RUN_ID == ME0_AUTHORITY_CI_RUN_ID
    assert me.ME0_AUTHORITY_CI_JOB_ID == ME0_AUTHORITY_CI_JOB_ID

    reference = _reference()
    reference_wire = reference.to_dict()
    assert reference_wire["accepted_e2_commit_sha"] == ACCEPTED_E2_COMMIT_SHA
    assert reference_wire["accepted_e2_tree_sha"] == ACCEPTED_E2_TREE_SHA
    assert reference_wire["certified_support_token_sha256"] == TOKEN_SHA256
    assert reference_wire["support_candidate_ids"] == ["c0", "c2"]
    assert reference_wire["runtime_manifest_sha256"] == WINDOWS_RUNTIME_MANIFEST_SHA256
    assert reference_wire["me0_authority_commit_sha"] == ME0_AUTHORITY_COMMIT_SHA
    assert (
        reference_wire["me0_authority_document_blob_sha"]
        == ME0_AUTHORITY_DOCUMENT_BLOB_SHA
    )
    assert type(me.DeclaredE2SupportReference.from_dict(reference_wire)) is type(reference)
    stale_reference_authority = copy.deepcopy(reference_wire)
    stale_reference_authority["me0_authority_document_blob_sha"] = "0" * 64
    with pytest.raises(StrictContractError):
        me.DeclaredE2SupportReference.from_dict(stale_reference_authority)

    mutated_token_wire = copy.deepcopy(wire)
    mutated_token_wire["gated_ranking"] = ["c0", "c2"]
    with pytest.raises(StrictContractError):
        me.make_declared_e2_support_reference(
            mutated_token_wire,
            accepted_e2_commit_sha=ACCEPTED_E2_COMMIT_SHA,
            accepted_e2_tree_sha=ACCEPTED_E2_TREE_SHA,
        )
    with pytest.raises(StrictContractError):
        me.make_declared_e2_support_reference(
            wire,
            accepted_e2_commit_sha="0" * 40,
            accepted_e2_tree_sha=ACCEPTED_E2_TREE_SHA,
        )
    with pytest.raises(StrictContractError):
        me.make_declared_e2_support_reference(
            wire,
            accepted_e2_commit_sha=ACCEPTED_E2_COMMIT_SHA,
            accepted_e2_tree_sha="0" * 40,
        )

    class CounterfeitToken:
        def to_dict(self):
            return copy.deepcopy(wire)

    with pytest.raises(StrictContractError):
        me.bind_e2_support(
            CounterfeitToken(),
            accepted_e2_commit_sha=ACCEPTED_E2_COMMIT_SHA,
            accepted_e2_tree_sha=ACCEPTED_E2_TREE_SHA,
        )

    reversed_rows = (("c2", _r(1, 2)), ("c0", _r(1, 2)))
    with pytest.raises(StrictContractError):
        me.MaxEntProblem.create(
            reference,
            reference_mass_rows=reversed_rows,
            statistic_rows=(("c0", (_r(0),)), ("c2", (_r(2),))),
            orbit_size_rows=(("c0", 1), ("c2", 1)),
            target=(_r(1),),
            kl_radius=_r(1, 20),
            row_load_rows=(("c0", _r(1)), ("c2", _r(3))),
            nominal_operator_rows=(("c0", _r(2)), ("c2", _r(4))),
            exact_rule_column_ids=("g0",),
            exact_rule_rows=(("c0", (_r(1),)), ("c2", (_r(2),))),
        )


def test_me0_exact_geometry_classifies_singular_outside_boundary_and_square_center(
    monkeypatch,
):
    singular_problem = _problem(target=_r(1), statistics=(_r(1), _r(1)))
    outside_problem = _problem(target=_r(3))
    boundary_problem = _problem(target=_r(0))
    interior_problem = _problem(target=_r(1))
    singular = me.classify_exact_moment_geometry(singular_problem)
    outside = me.classify_exact_moment_geometry(outside_problem)
    boundary = me.classify_exact_moment_geometry(boundary_problem)
    interior = me.classify_exact_moment_geometry(interior_problem)
    assert _status(singular) is me.MaxEntStatus.SINGULAR_STATISTICS
    assert _status(outside) is me.MaxEntStatus.OUTSIDE_HULL
    assert _status(boundary) is me.MaxEntStatus.BOUNDARY_NO_FINITE_PARAMETER
    assert _status(interior) is me.MaxEntStatus.INTERIOR_SOLVED

    square = me._classify_exact_points(
        statistics=(
            (_r(0), _r(0)),
            (_r(1), _r(0)),
            (_r(0), _r(1)),
            (_r(1), _r(1)),
        ),
        target=(_r(1, 2), _r(1, 2)),
        declared_dimension=2,
    )
    assert _status(square) is me.MaxEntStatus.INTERIOR_SOLVED

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "numpy" or name.startswith("numpy."):
            raise AssertionError("noninterior geometry reached NumPy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    for problem, expected_status in (
        (singular_problem, me.MaxEntStatus.SINGULAR_STATISTICS),
        (outside_problem, me.MaxEntStatus.OUTSIDE_HULL),
        (boundary_problem, me.MaxEntStatus.BOUNDARY_NO_FINITE_PARAMETER),
    ):
        result = me.solve_finite_fiber_maxent(problem)
        wire = result.to_dict()
        assert _status(result) is expected_status
        assert wire["probabilities"] == []
        assert wire["dual_parameter"] == []
        assert wire["pinsker_upper"] is None
        assert wire["operator_span"] is None
        assert wire["fallback_candidate_id"] == "c0"
        assert wire["verification_disposition"] != "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
        assert me.verify_maxent_result(problem, result) is result


def test_me0_primary_fixture_solves_and_preserves_the_fixed_support():
    problem = _problem()
    problem_wire = problem.to_dict()
    geometry = me.classify_exact_moment_geometry(problem)
    result = me.solve_finite_fiber_maxent(problem)
    assert _status(geometry) is me.MaxEntStatus.INTERIOR_SOLVED
    assert _status(result) is me.MaxEntStatus.INTERIOR_SOLVED
    wire = result.to_dict()
    assert wire["operator_tier"] == "NOMINAL_MODEL_SELECTION_ONLY"
    assert wire["support_candidate_ids"] == ["c0", "c2"]
    assert wire["certified_support_token_sha256"] == TOKEN_SHA256
    for authority_wire in (problem_wire, wire):
        assert authority_wire["me0_authority_commit_sha"] == ME0_AUTHORITY_COMMIT_SHA
        assert (
            authority_wire["me0_authority_document_blob_sha"]
            == ME0_AUTHORITY_DOCUMENT_BLOB_SHA
        )
        assert authority_wire["runtime_manifest_sha256"] == WINDOWS_RUNTIME_MANIFEST_SHA256
    probabilities = _floats(wire["probabilities"])
    assert probabilities == pytest.approx((0.5, 0.5), abs=1e-12)
    assert sum(probabilities) == pytest.approx(1.0, abs=1e-12)
    assert wire["fallback_candidate_id"] is None
    assert wire["verification_disposition"] == "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
    assert me.verify_maxent_result(problem, result) is result


def test_me0_nontrivial_orbit_fixture_requires_nonzero_lambda_and_meets_residuals():
    problem = _problem(target=_r(4, 5), orbit_sizes=(1, 2))
    result = me.solve_finite_fiber_maxent(problem)
    assert _status(result) is me.MaxEntStatus.INTERIOR_SOLVED
    wire = result.to_dict()
    orbit = _floats(wire["orbit_reference_probabilities"])
    probabilities = _floats(wire["probabilities"])
    dual = _floats(wire["dual_parameter"])
    assert orbit == pytest.approx((2 / 3, 1 / 3), abs=1e-12)
    assert probabilities == pytest.approx((3 / 5, 2 / 5), abs=1e-10)
    assert abs(dual[0]) > 1e-6
    assert float(wire["moment_residual_inf"]) <= 1e-10
    assert float(wire["simplex_residual"]) <= 1e-12
    assert float(wire["dual_residual_inf"]) <= 1e-10
    assert wire["kl_within_radius"] is True
    assert float(wire["operator_span_residual"]) <= 1e-10
    assert me.verify_maxent_result(problem, result) is result


def test_me0_kl_radius_is_separate_from_geometry_and_uses_within_support_fallback():
    problem = _problem(target=_r(1, 5), orbit_sizes=(1, 2))
    geometry = me.classify_exact_moment_geometry(problem)
    result = me.solve_finite_fiber_maxent(problem)
    assert _status(geometry) is me.MaxEntStatus.INTERIOR_SOLVED
    assert _status(result) is me.MaxEntStatus.INTERIOR_SOLVED
    wire = result.to_dict()
    assert wire["kl_within_radius"] is False
    assert wire["pinsker_upper"] is None
    assert wire["fallback_candidate_id"] == "c0"
    assert wire["support_candidate_ids"] == ["c0", "c2"]
    assert "c1" not in wire["support_candidate_ids"]
    assert wire["selected_candidate_id"] != "c1"
    assert wire["fallback_candidate_id"] != "c1"


def test_me0_numeric_failure_is_never_relabelled_or_promoted():
    problem = _problem(target=_r(4, 5), orbit_sizes=(1, 2))
    assert "max_iterations" not in inspect.signature(
        me.solve_finite_fiber_maxent
    ).parameters
    result = me._solve_finite_fiber_maxent(problem, max_iterations=0)
    assert _status(result) is me.MaxEntStatus.NUMERIC_FAILURE
    wire = result.to_dict()
    assert wire["probabilities"] == []
    assert wire["pinsker_upper"] is None
    assert wire["fallback_candidate_id"] == "c0"
    assert wire["operator_tier"] == "NOMINAL_MODEL_SELECTION_ONLY"
    assert wire["verification_disposition"] != "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
    assert me.verify_maxent_result(problem, result) is result


def test_me0_operator_span_and_pinsker_outputs_are_nominal_diagnostics_only():
    problem = _problem(target=_r(4, 5), orbit_sizes=(1, 2))
    result = me.solve_finite_fiber_maxent(problem)
    wire = result.to_dict()
    q = _floats(wire["orbit_reference_probabilities"])
    p = _floats(wire["probabilities"])
    expected_q_load = q[0] * 1.0 + q[1] * 3.0
    observed_p_load = p[0] * 1.0 + p[1] * 3.0
    expected_upper = expected_q_load + 2.0 * math.sqrt((1 / 20) / 2)
    assert float(wire["reference_expected_load"]) == pytest.approx(expected_q_load)
    assert float(wire["fitted_expected_load"]) == pytest.approx(observed_p_load)
    assert float(wire["pinsker_upper"]) == pytest.approx(expected_upper)
    assert observed_p_load <= expected_upper
    assert float(wire["operator_span_residual"]) <= 1e-10
    assert wire["operator_tier"] == "NOMINAL_MODEL_SELECTION_ONLY"
    assert not any(
        key in wire
        for key in (
            "certificate_token",
            "fiber_envelope",
            "safety_majorant",
            "positive_distance",
        )
    )


def test_me0_strict_wire_roundtrip_rejects_raw_float_nonfinite_negative_zero_and_mutation():
    problem = _problem(target=_r(4, 5), orbit_sizes=(1, 2))
    result = me.solve_finite_fiber_maxent(problem)
    problem_wire = problem.to_dict()
    result_wire = result.to_dict()
    assert type(me.MaxEntProblem.from_dict(problem_wire, reference=_reference())) is type(
        problem
    )
    assert type(me.MaxEntResult.from_dict(result_wire, problem=problem)) is type(result)

    alternate_runtime_wire = copy.deepcopy(result_wire)
    alternate_dual = math.nextafter(
        float(alternate_runtime_wire["dual_parameter"][0]), math.inf
    )
    alternate_runtime_wire["dual_parameter"][0] = format(
        alternate_dual, ".17g"
    ).replace("E", "e")
    alternate_runtime_result = me.MaxEntResult.from_dict(
        alternate_runtime_wire, problem=problem
    )
    assert canonical_contract_bytes(alternate_runtime_result.to_dict()) == (
        canonical_contract_bytes(alternate_runtime_wire)
    )

    equation_breaking_wire = copy.deepcopy(result_wire)
    equation_breaking_wire["probabilities"] = [
        format(0.7, ".17g"),
        format(0.3, ".17g"),
    ]
    with pytest.raises(StrictContractError):
        me.MaxEntResult.from_dict(equation_breaking_wire, problem=problem)

    raw_float = copy.deepcopy(result_wire)
    raw_float["probabilities"][0] = 0.6
    with pytest.raises(StrictContractError):
        me.MaxEntResult.from_dict(raw_float, problem=problem)

    for bad in ("nan", "inf", "-inf", "-0", "0.6000000000000000"):
        mutated = copy.deepcopy(result_wire)
        mutated["probabilities"][0] = bad
        with pytest.raises(StrictContractError):
            me.MaxEntResult.from_dict(mutated, problem=problem)

    extra = copy.deepcopy(result_wire)
    extra["unexpected"] = True
    with pytest.raises(StrictContractError):
        me.MaxEntResult.from_dict(extra, problem=problem)

    stale_support = copy.deepcopy(problem_wire)
    stale_support["support_candidate_ids"] = ["c0", "c1"]
    with pytest.raises(StrictContractError):
        me.MaxEntProblem.from_dict(stale_support, reference=_reference())

    stale_problem_authority = copy.deepcopy(problem_wire)
    stale_problem_authority["me0_authority_commit_sha"] = "0" * 40
    with pytest.raises(StrictContractError):
        me.MaxEntProblem.from_dict(stale_problem_authority, reference=_reference())

    stale_result_authority = copy.deepcopy(result_wire)
    stale_result_authority["me0_authority_document_blob_sha"] = "0" * 64
    with pytest.raises(StrictContractError):
        me.MaxEntResult.from_dict(stale_result_authority, problem=problem)

    geometry_wire = me.classify_exact_moment_geometry(problem).to_dict()
    geometry_wire["membership_subset_indices"] = [0, 1, 2]
    geometry_wire["membership_weights"] = [_r(1, 3).to_dict()] * 3
    with pytest.raises(StrictContractError):
        me.MomentGeometry.from_dict(geometry_wire)

    orbit_wire = result.orbit_reference.to_dict()
    orbit_wire["support_candidate_ids"] = ["c0", "c0"]
    with pytest.raises(StrictContractError):
        me.OrbitReferenceLaw.from_dict(orbit_wire)

    operator_wire = result.operator_span.to_dict()
    operator_wire["residual_l2"] = "-1"
    with pytest.raises(StrictContractError):
        me.OperatorSpanResidual.from_dict(operator_wire)


def test_me0_caps_fire_before_subset_materialization_or_numpy_and_no_safety_surface_exists(
    monkeypatch,
):
    module_tree = ast.parse(inspect.getsource(me))
    top_level_imports = {
        alias.name
        for node in module_tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in module_tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name == "numpy" or name.startswith("numpy.") for name in top_level_imports)

    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name == "numpy" or name.startswith("numpy."):
            raise AssertionError("NumPy imported before ME0 exact preflight completed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    oversized = _r(1 << 256)
    with pytest.raises(StrictContractError):
        _problem(input_rational_override=oversized)
    with pytest.raises(StrictContractError):
        _problem(statistic_dimension=5)
    with pytest.raises(StrictContractError):
        _problem(orbit_sizes=(1, 33))
    with pytest.raises(StrictContractError):
        _problem(exact_rule_column_count=33)
    with pytest.raises(StrictContractError):
        me._classify_exact_points(
            statistics=tuple((_r(index),) for index in range(33)),
            target=(_r(0),),
            declared_dimension=1,
        )

    # The independent subset/cell ceilings are saturated, rather than
    # exceeded, by their already-frozen component caps.  This guards the
    # arithmetic that the production preflight must use without inventing an
    # impossible non-E2 support reference merely to cross the derived bound.
    assert sum(math.comb(32, size) for size in range(1, 6)) == 242_824
    assert 32 * 32 == 1_024

    primary_wire = _problem().to_dict()
    nominal_rows = primary_wire["nominal_operator_rows"]
    assert [row["candidate_id"] for row in nominal_rows] == ["c0", "c2"]
    assert all(type(row["value"]) is dict for row in nominal_rows)

    preflight_mutations = []
    overlong_target = copy.deepcopy(primary_wire)
    overlong_target["target"] = [_r(0).to_dict()] * 5
    preflight_mutations.append(overlong_target)
    overlong_columns = copy.deepcopy(primary_wire)
    overlong_columns["exact_rule_column_ids"] = [f"g{i}" for i in range(33)]
    preflight_mutations.append(overlong_columns)
    extra_outer_row = copy.deepcopy(primary_wire)
    extra_outer_row["reference_mass_rows"].append(
        copy.deepcopy(extra_outer_row["reference_mass_rows"][0])
    )
    preflight_mutations.append(extra_outer_row)
    overwide_statistic = copy.deepcopy(primary_wire)
    overwide_statistic["statistic_rows"][0]["value"].append(_r(0).to_dict())
    preflight_mutations.append(overwide_statistic)
    overwide_rule = copy.deepcopy(primary_wire)
    overwide_rule["exact_rule_rows"][0]["value"].append(_r(0).to_dict())
    preflight_mutations.append(overwide_rule)

    def decoder_bomb(*_args, **_kwargs):
        raise AssertionError("wire decoder ran before ME0 shape preflight")

    with monkeypatch.context() as preflight_guard:
        preflight_guard.setattr(me, "_rows_from_wire", decoder_bomb)
        for malformed_wire in preflight_mutations:
            with pytest.raises(StrictContractError):
                me.MaxEntProblem.from_dict(malformed_wire, reference=_reference())

    oversized_token = _token_wire()
    oversized_token["threshold"]["numerator"] = "9" * 1_301

    def serializer_bomb(*_args, **_kwargs):
        raise AssertionError("canonical serializer ran before bounded preflight")

    with monkeypatch.context() as token_guard:
        token_guard.setattr(me, "canonical_contract_bytes", serializer_bomb)
        with pytest.raises(StrictContractError):
            me.make_declared_e2_support_reference(oversized_token)

    boundary_problem = _problem(target=_r(0))
    oversized_result_wire = me.solve_finite_fiber_maxent(boundary_problem).to_dict()
    oversized_result_wire["probabilities"] = ["9" * 1_301]
    with monkeypatch.context() as result_guard:
        result_guard.setattr(me, "canonical_contract_bytes", serializer_bomb)
        with pytest.raises(StrictContractError):
            me.MaxEntResult.from_dict(oversized_result_wire, problem=boundary_problem)

    public = set(me.__all__)
    assert public == {
        "MaxEntStatus",
        "DeclaredE2SupportReference",
        "MaxEntProblem",
        "MomentGeometry",
        "OrbitReferenceLaw",
        "OperatorSpanResidual",
        "MaxEntResult",
        "bind_e2_support",
        "make_declared_e2_support_reference",
        "classify_exact_moment_geometry",
        "solve_finite_fiber_maxent",
        "verify_maxent_result",
    }
    assert not hasattr(me, "CertifiedSupportToken")
    forbidden = (
        "Envelope",
        "Safety",
        "CertificateToken",
        "PositiveDistance",
        "SelectionGate",
    )
    assert not any(any(term in name for term in forbidden) for name in dir(me))
