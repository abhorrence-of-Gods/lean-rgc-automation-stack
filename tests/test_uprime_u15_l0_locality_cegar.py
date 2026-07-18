from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

import pytest

import lean_rgc.evals.uprime_u15_l0_locality_cegar as l0_eval
from lean_rgc.odlrq import (
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactRational,
    StrictContractError,
    VerifiedExactPartition,
    admit_synthetic_finite_snapshot,
    build_synthetic_finite_snapshot,
    make_synthetic_observation_frame_id,
    observation_frame_digest,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_RESULT_PATH = _REPO_ROOT / (
    "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/"
    "locality_cegar_result.json"
)
_CLOSEOUT_PATH = _REPO_ROOT / (
    "docs/experiments/"
    "uprime_odlrq_u15_l0_locality_cegar_closeout_2026-07-17.md"
)


def _fraction(row):
    value = ExactRational.from_dict(row)
    return Fraction(value.numerator, value.denominator)


def _fresh_runtime():
    matrix = l0_eval._load_frozen_matrix()
    locality, baseline, verified_train = l0_eval._build_train_schedules(matrix)
    barrier = l0_eval._seal_schedules(locality, baseline)
    opened = l0_eval._open_heldout(matrix, barrier)
    p0, verified_heldout = l0_eval._seal_p0(matrix, opened)
    return matrix, locality, baseline, verified_train, opened, p0, verified_heldout


def test_u15_l0_matrix_identity_families_and_seeded_witnesses_are_exact():
    raw = l0_eval._MATRIX_PATH.read_bytes()
    assert len(raw) == 73_723
    assert hashlib.sha256(raw).hexdigest().upper() == l0_eval._MATRIX_SHA256
    matrix = l0_eval._load_frozen_matrix()
    assert matrix.canonical_sha256 == l0_eval._MATRIX_CANONICAL_SHA256
    assert tuple(action.action_id for action in matrix.actions) == l0_eval._ACTION_IDS
    assert tuple(query.query_id for query in matrix.queries) == l0_eval._QUERY_IDS
    assert tuple(family.family_id for family in matrix.families) == l0_eval._FAMILY_IDS
    assert len(matrix.actions) == 5 and len(matrix.queries) == 8
    with pytest.raises(StrictContractError):
        l0_eval._ScheduleBarrier(b"{}", hashlib.sha256(b"{}").hexdigest().upper(), object())

    locality, baseline, verified_train = l0_eval._build_train_schedules(matrix)
    barrier = l0_eval._seal_schedules(locality, baseline)
    opened = l0_eval._open_heldout(matrix, barrier)
    p0, verified_heldout = l0_eval._seal_p0(matrix, opened)
    assert len(verified_train) == 8 and len(verified_heldout) == 16
    assert len(p0.rows) == 16 and p0._token is l0_eval._P0_TOKEN
    all_verified = (*verified_train, *verified_heldout)
    assert all(
        type(row.admitted) is AdmittedExactFiniteSnapshot
        and type(row.verified) is VerifiedExactPartition
        for row in all_verified
    )
    assert sum(len(row.spec.seeds) for row in all_verified) == 21
    assert all(
        row.terminal_block(left, query) != row.terminal_block(right, query)
        and row.spec.response(left, query) != row.spec.response(right, query)
        for row in all_verified
        for left, right, query in row.spec.seeds
    )


def test_u15_l0_family_stratified_paired_curves_use_fixed_denominator():
    raw = l0_eval.build_u15_l0_result_bytes()
    result = l0_eval._strict_json_object(raw, "test result", require_canonical=True)
    assert result["disposition"] == "L0_SYNTHETIC_CEGAR_DEGRADED"
    assert result["global_p0_barrier"]["sealed_instance_count"] == 16
    assert result["overall_curves"]["coverage_numerators"] == [16] * 17
    locality = tuple(_fraction(row) for row in result["overall_curves"]["locality"])
    baseline = tuple(_fraction(row) for row in result["overall_curves"]["baseline"])
    assert tuple(t for t in range(17) if locality[t] < baseline[t]) == (1, 2, 3, 4)
    assert tuple(t for t in range(17) if locality[t] > baseline[t]) == tuple(range(5, 17))
    assert _fraction(result["aulc"]["baseline_minus_locality"]) == Fraction(
        -86_333, 6_773_760
    )
    assert tuple(
        _fraction(row) for row in result["aulc"]["family_baseline_minus_locality"]
    ) == (
        Fraction(115, 16),
        Fraction(-22_163, 52_920),
        Fraction(-397, 48),
        Fraction(-11, 6),
        Fraction(3_725, 1_152),
        Fraction(0),
        Fraction(0),
        Fraction(0),
    )
    assert _fraction(result["cluster_bootstrap_diagnostic"]["lower"]) == Fraction(
        -26_107, 9_216
    )
    assert _fraction(result["cluster_bootstrap_diagnostic"]["upper"]) == Fraction(
        2_847, 1_024
    )

    matrix, locality_schedules, baseline_schedules, _train, _opened, p0, heldout = _fresh_runtime()
    alpha, beta = tuple(
        row for row in heldout if row.spec.family_id == "separator_rank0"
    )
    local_schedule = next(
        row for row in locality_schedules if row.family_id == "separator_rank0"
    )
    alpha_curve = l0_eval._evaluate_instance(alpha, local_schedule, p0)
    beta_curve = l0_eval._evaluate_instance(beta, local_schedule, p0)
    family_covariance = l0_eval._mean_covariances(
        alpha_curve.covariances[0], beta_curve.covariances[0]
    )
    assert family_covariance.trace == (
        alpha_curve.covariances[0].trace + beta_curve.covariances[0].trace
    ) / 2
    assert family_covariance.cells[0][0] == (
        alpha_curve.covariances[0].cells[0][0]
        + beta_curve.covariances[0].cells[0][0]
    ) / 2
    assert all(len(schedule.candidates) <= 16 for schedule in (*locality_schedules, *baseline_schedules))


def test_u15_l0_dispositions_cover_gain_no_gain_degraded_blocked_and_failed():
    controls, valid_results = l0_eval._reachability_control_audit()
    matrix = l0_eval._load_frozen_matrix()
    reachability_case, _registered = l0_eval._strict_reachability_fixture(matrix)
    with pytest.raises(StrictContractError, match="preceded its barrier"):
        l0_eval._control_heldout_specs(
            reachability_case, "gain_reachable", "q_reveal", None
        )
    preflight_only_fixture = dict(reachability_case)
    preflight_only_fixture["heldout_alpha_right_override_vector"] = object()
    preflight_only_fixture["heldout_beta_right_override_vector"] = object()
    with pytest.raises(
        StrictContractError,
        match="GLOBAL_PREFLIGHT_FROZEN_FIXTURE_SNAPSHOT_ROW_CAP_INCOMPATIBILITY",
    ):
        l0_eval._control_global_preflight(
            matrix, preflight_only_fixture, max_transition_rows=199
        )
    control_orbits = tuple(l0_eval._CONTROL_ORBIT_CACHE.values())
    assert len(control_orbits) == 9
    control_members = tuple(
        member for orbit in control_orbits for member in orbit.members
    )
    assert len(control_members) == 72
    assert all(
        len(set(orbit.isomorphism_sha256s)) == 8
        and all(
            member.admitted.admission_report.snapshot_sha256
            == hashlib.sha256(
                l0_eval.canonical_contract_bytes(member.admitted.snapshot.to_dict())
            ).hexdigest().upper()
            and all(
                state.state_id.startswith(l0_eval._STATE_ID_PREFIX)
                and json.loads(state.payload.canonical_json).get("instance_id")
                == member.spec.instance_id
                for state in member.admitted.snapshot.states
            )
            for member in orbit.members
        )
        for orbit in control_orbits
    )
    orbit = control_orbits[0]
    source_member, target_member = orbit.members[:2]
    target_snapshot = target_member.admitted.snapshot
    mutated_states = list(target_snapshot.states)
    source_index = next(
        index
        for index, state in enumerate(mutated_states)
        if json.loads(state.payload.canonical_json).get("kind")
        == "u15_l0_source"
    )
    mutated_payload = json.loads(
        mutated_states[source_index].payload.canonical_json
    )
    digest = mutated_payload["query_sha256"]
    mutated_payload["query_sha256"] = (
        ("0" if digest[0] != "0" else "1") + digest[1:]
    )
    mutated_states[source_index] = replace(
        mutated_states[source_index],
        payload=CanonicalPayload.from_value(mutated_payload),
    )
    query_mutated_member = l0_eval._AdmittedControlMember(
        target_member.spec,
        admit_synthetic_finite_snapshot(
            build_synthetic_finite_snapshot(
                environment_digest=target_snapshot.domain_id.environment_digest,
                coordinate_names=(
                    target_snapshot.response_vocabulary_id.coordinate_names
                ),
                seed_state_ids=target_snapshot.seed_state_ids,
                states=tuple(mutated_states),
                actions=target_snapshot.actions,
                transitions=target_snapshot.transitions,
                frame_digest=target_snapshot.domain_id.frame_digest,
                transition_semantics_digest=(
                    target_snapshot.transition_semantics_id.semantics_digest
                ),
            )
        ),
    )
    with pytest.raises(StrictContractError, match="full query binding"):
        l0_eval._control_snapshot_isomorphism_sha256(
            l0_eval._load_frozen_matrix(), source_member, query_mutated_member
        )

    foreign_frame = make_synthetic_observation_frame_id(
        environment_digest="CD" * 32,
        response_vocabulary_id=target_snapshot.response_vocabulary_id,
    )
    foreign_frame_digest = observation_frame_digest(foreign_frame)
    foreign_snapshot = build_synthetic_finite_snapshot(
        environment_digest="CD" * 32,
        coordinate_names=target_snapshot.response_vocabulary_id.coordinate_names,
        seed_state_ids=target_snapshot.seed_state_ids,
        states=tuple(
            replace(state, frame_digest=foreign_frame_digest)
            for state in target_snapshot.states
        ),
        actions=target_snapshot.actions,
        transitions=target_snapshot.transitions,
        frame_digest=foreign_frame_digest,
        transition_semantics_digest=(
            target_snapshot.transition_semantics_id.semantics_digest
        ),
    )
    frame_mutated_member = l0_eval._AdmittedControlMember(
        target_member.spec,
        admit_synthetic_finite_snapshot(foreign_snapshot),
    )
    with pytest.raises(StrictContractError, match="environment/frame binding"):
        l0_eval._control_snapshot_isomorphism_sha256(
            l0_eval._load_frozen_matrix(), source_member, frame_mutated_member
        )
    assert {name: row[0] for name, row in controls.items()} == {
        "gain_reachable": "L0_SYNTHETIC_CEGAR_GAIN_OBSERVED",
        "no_clear_gain_reachable": "L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN",
        "degraded_reachable": "L0_SYNTHETIC_CEGAR_DEGRADED",
        "prerequisite_blocked_reachable": "L0_PREREQUISITE_BLOCKED",
        "execution_failed_reachable": "L0_EXECUTION_FAILED",
    }
    gain_locality = (Fraction(1),) + (Fraction(0),) * 16
    gain_baseline = (Fraction(1),) * 8 + (Fraction(0),) * 9
    assert l0_eval._classify_disposition(
        locality=gain_locality, baseline=gain_baseline, seed_miss_count=1
    )[0] == "L0_SYNTHETIC_CEGAR_DEGRADED"
    zero = (Fraction(0),) * 17
    assert l0_eval._classify_disposition(
        locality=zero, baseline=zero, seed_miss_count=1
    )[0] == "L0_SYNTHETIC_CEGAR_DEGRADED"
    blocked = controls["prerequisite_blocked_reachable"]
    assert blocked == (
        "L0_PREREQUISITE_BLOCKED",
        "GLOBAL_PREFLIGHT_FROZEN_FIXTURE_SNAPSHOT_ROW_CAP_INCOMPATIBILITY",
    )
    assert controls["execution_failed_reachable"] == (
        "L0_EXECUTION_FAILED",
        "RESULT_COVARIANCE_SHA256_MISMATCH",
    )
    gain_raw = valid_results["gain_reachable"]
    gain = l0_eval._strict_json_object(
        gain_raw, "gain control", require_canonical=True
    )
    assert gain["preflight"] == {
        "declared_max_snapshot_transition_rows": 200,
        "mechanically_required_snapshot_states": 40,
        "mechanically_required_snapshot_transition_rows": 200,
    }
    assert gain["p0_fixed_denominator"] == 16
    gain_locality = tuple(_fraction(row) for row in gain["overall_curves"]["locality"])
    gain_baseline = tuple(_fraction(row) for row in gain["overall_curves"]["baseline"])
    assert all(gain_locality[t] <= gain_baseline[t] for t in range(17))
    assert tuple(t for t in range(17) if gain_locality[t] < gain_baseline[t]) == tuple(
        range(1, 8)
    )
    assert l0_eval._classify_disposition(
        locality=(),
        baseline=(),
        seed_miss_count=0,
        locality_abstentions=1,
        prerequisite_failure="PRE_P0",
    )[0] == "L0_PREREQUISITE_BLOCKED"
    primary = l0_eval._strict_json_object(
        l0_eval.build_u15_l0_result_bytes(), "primary", require_canonical=True
    )
    assert primary["seed_audit"]["misses"] == [
        {
            "family_id": "separator_rank2",
            "instance_id": "separator_rank2__heldout_alpha",
            "left_region_id": "sr2_zero",
            "right_region_id": "sr2_one",
            "query_id": "q_b_a",
        },
        {
            "family_id": "separator_rank2",
            "instance_id": "separator_rank2__heldout_beta",
            "left_region_id": "sr2_zero",
            "right_region_id": "sr2_one",
            "query_id": "q_ghost_store_reveal",
        },
    ]


def test_u15_l0_repeated_evaluation_is_byte_identical_and_budget_bound():
    first = l0_eval.build_u15_l0_result_bytes()
    second = l0_eval.build_u15_l0_result_bytes()
    assert l0_eval._VERIFIED_INSTANCE_CACHE
    l0_eval._VERIFIED_INSTANCE_CACHE.update(
        {
            instance_id: replace(
                verified,
                terminal_blocks=tuple(
                    (region_id, query_id, block_index + 1_000)
                    for region_id, query_id, block_index in verified.terminal_blocks
                ),
            )
            for instance_id, verified in l0_eval._VERIFIED_INSTANCE_CACHE.items()
        }
    )
    cache_before_verify = l0_eval.build_u15_l0_result_bytes.cache_info()
    l0_eval._CONTROL_QUERY_TEMPLATE_BYTES["poison"] = b"{}"
    l0_eval._CONTROL_QUERY_TEMPLATE_ENVIRONMENTS[:] = ["0" * 64, "1" * 64]
    l0_eval._CONTROL_EXPECTED_VOCABULARIES[:] = [object()]
    l0_eval._CONTROL_EXPECTED_SEMANTICS[:] = [object()]
    l0_eval._CONTROL_QUERY_BINDING_CACHE[("poison", "poison")] = (
        ("q_a", "0" * 64),
    )
    l0_eval._CONTROL_ORBIT_CACHE[("poison", "poison")] = object()
    l0_eval._locality_cegar_core._VERIFIED_OBSERVATION_SOURCE_MEMO[:] = [
        (object(), object())
    ]
    verified = l0_eval.verify_u15_l0_result_bytes(first)
    cache_after_verify = l0_eval.build_u15_l0_result_bytes.cache_info()
    assert first == second == verified
    assert cache_after_verify == cache_before_verify
    assert "poison" not in l0_eval._CONTROL_QUERY_TEMPLATE_BYTES
    assert ("poison", "poison") not in l0_eval._CONTROL_QUERY_BINDING_CACHE
    assert ("poison", "poison") not in l0_eval._CONTROL_ORBIT_CACHE
    assert all(
        type(row[0]) is l0_eval._locality_cegar_core.VerifiedExactPartition
        for row in l0_eval._locality_cegar_core._VERIFIED_OBSERVATION_SOURCE_MEMO
    )
    assert len(first) <= 1_048_576
    result = l0_eval._strict_json_object(first, "result", require_canonical=True)
    assert all(
        row["schedule_length"] <= 16
        and row["schedule_length"] == len(row["candidate_sha256s"])
        and len(row["candidate_sha256s"]) == len(set(row["candidate_sha256s"]))
        for row in result["schedules"]
    )
    assert result["aulc"]["included_t_values"] == list(range(16))
    assert len(result["overall_curves"]["locality"]) == 17
    assert len(result["overall_curves"]["baseline"]) == 17

    assert _RESULT_PATH.exists() is _CLOSEOUT_PATH.exists()
    if _RESULT_PATH.exists():
        published = _RESULT_PATH.read_bytes()
        assert published == l0_eval.verify_u15_l0_result_bytes(published)
        assert tuple(
            sorted(
                path.relative_to(_REPO_ROOT).as_posix()
                for path in _RESULT_PATH.parent.rglob("*")
                if path.is_file()
            )
        ) == (
            "docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/"
            "locality_cegar_result.json",
        )
        closeout = _CLOSEOUT_PATH.read_text(encoding="utf-8")
        for field in ("accepted_c_commit", "accepted_c_tree", "matrix_blob"):
            assert len(
                re.findall(
                    rf"^- {field}: `([0-9a-f]{{40}})`$", closeout, flags=re.M
                )
            ) == 1
        assert re.search(
            rf"^- result_sha256: `{hashlib.sha256(published).hexdigest().upper()}`$",
            closeout,
            flags=re.M,
        )
        assert re.search(
            r"^- disposition: `L0_SYNTHETIC_CEGAR_DEGRADED`$", closeout, flags=re.M
        )
        assert re.search(r"^- heldout_fixed_denominator: `16`$", closeout, flags=re.M)
        assert re.search(r"^- p0_sealed_instance_count: `16`$", closeout, flags=re.M)
        assert re.search(r"^- execution_lane: `WINDOWS_CPU_ONLY`$", closeout, flags=re.M)
