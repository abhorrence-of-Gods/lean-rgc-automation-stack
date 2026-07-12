from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import os

import pytest

import lean_rgc.odlrq as odlrq_package
import lean_rgc.odlrq.quotient_generator as qg
from lean_rgc.odlrq import (
    CanonicalPayload,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticFiniteSnapshot,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    admit_synthetic_finite_snapshot,
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
    refine_exact_partition,
    verify_exact_partition,
)
from lean_rgc.odlrq.quotient_generator import (
    CERTIFIED_OPERATOR_TIER,
    EXACT_OPERATOR_TIER,
    MAX_SIGNED_64,
    MAX_TIER_FIREWALL_WORK_UNITS,
    NOMINAL_OPERATOR_TIER,
    OBSERVED_OPERATOR_TIER,
    CertifiedIntervalOperator,
    ExactFiniteOperator,
    IntervalCandidate,
    IntervalTargetRow,
    NominalOperator,
    ObservedIntervalOperator,
    UppernessDomainEvidence,
    UppernessDomainWitness,
    UppernessEvidenceRow,
    certify_interval_operator,
    export_exact_finite_operator,
    extend_interval_candidate,
    make_interval_candidate,
    verify_upperness_domain,
)


ENV = "11" * 32
FRAME = "22" * 32
SEMANTICS = "33" * 32
COORDINATES = ("debt", "mass")
_VERIFIED_TEMPLATES = {}


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


def _state(
    name: str, kind: TotalizedStatus, coordinates: tuple[int, int]
) -> SyntheticTotalizedState:
    return SyntheticTotalizedState(
        state_id=f"unit_cpu_survivor_{name}",
        payload=_payload("state", name),
        totalized_kind=kind,
        response_coordinates=tuple(ExactRational(value) for value in coordinates),
        frame_digest=FRAME,
    )


def _action(name: str) -> SyntheticAction:
    return SyntheticAction(
        action_id=f"unit_cpu_survivor_{name}", payload=_payload("action", name)
    )


def _row(source: str, action: str, target: str) -> SyntheticTransitionRow:
    return SyntheticTransitionRow(
        source_state_id=f"unit_cpu_survivor_{source}",
        action_id=f"unit_cpu_survivor_{action}",
        target_state_id=f"unit_cpu_survivor_{target}",
        transition_semantics_digest=SEMANTICS,
    )


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


def _snapshot(*, reverse: bool = False, perturb: bool = False) -> SyntheticFiniteSnapshot:
    states, actions, rows = _parts()
    if perturb:
        states = tuple(
            replace(
                state,
                response_coordinates=(ExactRational(7), ExactRational(1)),
            )
            if state.state_id == "unit_cpu_survivor_s1"
            else state
            for state in states
        )
    vocabulary = ResponseVocabularyId.from_coordinate_names(COORDINATES)
    frame = make_synthetic_observation_frame_id(
        environment_digest=ENV, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=actions, response_vocabulary_id=vocabulary
    )
    frame_digest = observation_frame_digest(frame)
    states = tuple(replace(state, frame_digest=frame_digest) for state in states)
    rows = tuple(
        replace(row, transition_semantics_digest=semantics.semantics_digest)
        for row in rows
    )
    if reverse:
        states, actions, rows = (
            tuple(reversed(states)),
            tuple(reversed(actions)),
            tuple(reversed(rows)),
        )
    return build_synthetic_finite_snapshot(
        environment_digest=ENV,
        coordinate_names=COORDINATES,
        seed_state_ids=("unit_cpu_survivor_s0",),
        states=states,
        actions=actions,
        transitions=rows,
    )


def _verified(*, reverse: bool = False, perturb: bool = False):
    key = (reverse, perturb)
    if key not in _VERIFIED_TEMPLATES:
        admitted = admit_synthetic_finite_snapshot(
            _snapshot(reverse=reverse, perturb=perturb)
        )
        certificate = refine_exact_partition(admitted)
        _VERIFIED_TEMPLATES[key] = verify_exact_partition(admitted, certificate)
    return copy.deepcopy(_VERIFIED_TEMPLATES[key])


def _candidate_rows(
    exact: ExactFiniteOperator,
    *,
    overcover_first: bool = False,
    exact_wire: dict | None = None,
) -> tuple[IntervalTargetRow, ...]:
    wire = exact.to_dict() if exact_wire is None else exact_wire
    rows: list[IntervalTargetRow] = []
    for index, row in enumerate(wire["rows"]):
        targets = (row["target_block_index"],)
        if overcover_first and index == 0 and wire["block_count"] > 1:
            other = 0 if row["target_block_index"] != 0 else 1
            targets = tuple(sorted((row["target_block_index"], other)))
        rows.append(
            IntervalTargetRow(
                row["source_block_index"], row["action_id"], targets
            )
        )
    return tuple(rows)


def _evidence_rows(verified) -> tuple[UppernessEvidenceRow, ...]:
    owner = {
        state_id: block.block_index
        for block in verified.certificate.final_blocks
        for state_id in block.member_state_ids
    }
    rows = tuple(
        UppernessEvidenceRow(
            source_block_index=owner[row.source_state_id],
            member_state_id=row.source_state_id,
            action_id=row.action_id,
            concrete_target_block_index=owner[row.target_state_id],
        )
        for row in verified.admitted.snapshot.transitions
    )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.source_block_index,
                row.member_state_id,
                row.action_id,
            ),
        )
    )


def _make_evidence(
    verified,
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    *,
    rows: tuple[UppernessEvidenceRow, ...] | None = None,
    frame_digest: str | None = None,
    exact_wire: dict | None = None,
) -> UppernessDomainEvidence:
    exact_wire = exact.to_dict() if exact_wire is None else exact_wire
    exact_sha256 = hashlib.sha256(
        canonical_contract_bytes(exact_wire)
    ).hexdigest().upper()
    selected_rows = _evidence_rows(verified) if rows is None else rows
    fields = {
        "evidence_id": "unit_cpu_survivor_independent_upperness",
        "issuer": "unit_independent_table_auditor",
        "method": "full_totalized_member_action_enumeration",
        "exact_operator_sha256": exact_sha256,
        "candidate_sha256": candidate.candidate_sha256,
        "domain_payload_digest": exact_wire["domain_payload_digest"],
        "observation_frame_digest": (
            exact_wire["observation_frame_digest"]
            if frame_digest is None
            else frame_digest
        ),
        "transition_semantics_digest": exact_wire[
            "transition_semantics_digest"
        ],
        "rows": selected_rows,
    }
    digest = hashlib.sha256(
        canonical_contract_bytes(
            {
                **{key: value for key, value in fields.items() if key != "rows"},
                "rows": [row.to_dict() for row in selected_rows],
            }
        )
    ).hexdigest().upper()
    return UppernessDomainEvidence(**fields, evidence_payload_sha256=digest)


def _bundle(*, overcover_first: bool = False):
    verified = _verified()
    exact = export_exact_finite_operator(verified)
    exact_wire = exact.to_dict()
    candidate = make_interval_candidate(
        exact,
        _candidate_rows(
            exact,
            overcover_first=overcover_first,
            exact_wire=exact_wire,
        ),
        provenance_id="unit_cpu_survivor_interval_candidate",
    )
    evidence = _make_evidence(
        verified, exact, candidate, exact_wire=exact_wire
    )
    witness = verify_upperness_domain(exact, candidate, evidence)
    certified = certify_interval_operator(exact, candidate, witness)
    return verified, exact, candidate, evidence, witness, certified


def test_exact_export_rederives_complete_totalized_member_action_table() -> None:
    verified, exact, *_ = _bundle()
    wire = exact.to_dict()
    assert wire["operator_tier"] == EXACT_OPERATOR_TIER
    assert wire["evidence_scope"] == "synthetic_development"
    assert wire["totalized_state_count"] == 4
    assert len(wire["rows"]) == wire["block_count"] * wire["action_count"]
    assert sum(row["member_transition_count"] for row in wire["rows"]) == 8
    kinds = {
        member["totalized_kind"]
        for block in wire["blocks"]
        for member in block["members"]
    }
    assert kinds == {"open", "closed", "sink"}
    assert ExactFiniteOperator.from_dict(wire, verified).to_dict() == wire

    reverse = export_exact_finite_operator(_verified(reverse=True))
    assert canonical_contract_bytes(reverse.to_dict()) == canonical_contract_bytes(wire)


def test_exact_export_rejects_direct_subclass_unknown_and_wrong_authority() -> None:
    verified = _verified()
    seal = qg._fresh_verified_digest(verified)
    with pytest.raises(StrictContractError):
        ExactFiniteOperator(verified, seal)

    class BadExact(ExactFiniteOperator):
        pass

    with pytest.raises(StrictContractError):
        BadExact.from_verified(verified)

    exact = export_exact_finite_operator(verified)
    unknown = exact.to_dict()
    unknown["extra"] = 1
    with pytest.raises(StrictContractError):
        ExactFiniteOperator.from_dict(unknown, verified)
    with pytest.raises(StrictContractError):
        ExactFiniteOperator.from_dict(exact.to_dict(), _verified(perturb=True))


def test_exact_serializer_fails_closed_after_low_level_source_corruption() -> None:
    verified = _verified()
    exact = export_exact_finite_operator(verified)
    object.__setattr__(exact, "_source_seal_sha256", "00" * 32)
    with pytest.raises(StrictContractError):
        exact.to_dict()

    verified = _verified()
    exact = export_exact_finite_operator(verified)
    object.__setattr__(verified, "verification_report", object())
    with pytest.raises(StrictContractError):
        exact.to_dict()

    verified = _verified()
    exact = export_exact_finite_operator(verified)
    first = verified.certificate.quotient_rows[0]
    bad_target = (first.target_block_index + 1) % len(
        verified.certificate.final_blocks
    )
    object.__setattr__(
        verified.certificate,
        "quotient_rows",
        (replace(first, target_block_index=bad_target),)
        + verified.certificate.quotient_rows[1:],
    )
    with pytest.raises(StrictContractError):
        exact.to_dict()


@pytest.mark.parametrize("target", [True, False, -1, 2**63, 1.0, "1"])
def test_interval_target_rejects_non_signed64_before_domain_work(target) -> None:
    with pytest.raises(StrictContractError):
        IntervalTargetRow(0, "unit_cpu_survivor_a", (target,))  # type: ignore[arg-type]


def test_candidate_is_complete_source_bound_and_checks_known_blocks() -> None:
    _, exact, candidate, *_ = _bundle()
    assert IntervalCandidate.from_dict(candidate.to_dict(), exact) == candidate

    with pytest.raises(StrictContractError):
        make_interval_candidate(
            exact,
            candidate.rows[:-1],
            provenance_id="unit_cpu_survivor_missing_row",
        )
    with pytest.raises(StrictContractError):
        make_interval_candidate(
            exact,
            tuple(reversed(candidate.rows)),
            provenance_id="unit_cpu_survivor_reordered_rows",
        )
    first = candidate.rows[0]
    huge = replace(first, target_block_indices=(MAX_SIGNED_64,))
    with pytest.raises(StrictContractError, match="outside the exact domain"):
        make_interval_candidate(
            exact,
            (huge,) + candidate.rows[1:],
            provenance_id="unit_cpu_survivor_unknown_block",
        )


def test_candidate_wire_rejects_combined_preallocation_bomb_before_parsing() -> None:
    _, exact, candidate, *_ = _bundle()
    payload = candidate.to_dict()
    for row in payload["rows"]:
        row["target_block_indices"] = [0] * 20_000
    with pytest.raises(StrictContractError, match="work-unit cap"):
        IntervalCandidate.from_dict(payload, exact)


def _near_cap_context(*, exact_target: int) -> tuple[qg._ExactContext, list[dict]]:
    exact_rows: list[dict] = []
    raw_rows: list[dict] = []
    for index in range(2_048):
        source = index // 16
        action = f"unit_cpu_survivor_a{index % 16:02d}"
        target_count = 69 if index < 8 else 60
        exact_rows.append(
            {
                "source_block_index": source,
                "action_id": action,
                "target_block_index": exact_target,
            }
        )
        raw_rows.append(
            {
                "schema_version": qg.INTERVAL_TARGET_ROW_SCHEMA,
                "source_block_index": source,
                "action_id": action,
                "target_block_indices": list(range(target_count)),
            }
        )
    context = qg._ExactContext(
        wire={"rows": exact_rows},
        operator_sha256="AA" * 32,
        total_members=128,
        block_count=128,
        action_count=16,
    )
    return context, raw_rows


def test_candidate_wire_checks_exact_u_before_materializing_rows(monkeypatch) -> None:
    # M*A+B*A+2*T is exactly 250,000, but every row omits exact target 127,
    # hence U=T+2,048 and the frozen exact W_T is 252,048.
    context, raw_rows = _near_cap_context(exact_target=127)
    monkeypatch.setattr(qg, "_exact_context", lambda _exact: context)
    decoded = False

    def forbidden_decode(_value):
        nonlocal decoded
        decoded = True
        raise AssertionError("row materialized before exact W_T passed")

    monkeypatch.setattr(
        qg.IntervalTargetRow, "from_dict", staticmethod(forbidden_decode)
    )
    payload = {
        "schema_version": qg.INTERVAL_CANDIDATE_SCHEMA,
        "exact_operator_sha256": context.operator_sha256,
        "provenance_id": "unit_cpu_survivor_exact_u_bomb",
        "work_units": MAX_TIER_FIREWALL_WORK_UNITS,
        "rows": raw_rows,
    }
    with pytest.raises(StrictContractError, match="work-unit cap"):
        IntervalCandidate.from_dict(payload, object())  # type: ignore[arg-type]
    assert not decoded


def test_work_formula_accepts_boundary_and_rejects_boundary_plus_one() -> None:
    assert (
        qg._tier_work_units(
            total_members=125_000,
            block_count=0,
            action_count=2,
            target_cells=0,
            union_cells=0,
        )
        == MAX_TIER_FIREWALL_WORK_UNITS
    )
    with pytest.raises(StrictContractError, match="work-unit cap"):
        qg._tier_work_units(
            total_members=125_001,
            block_count=0,
            action_count=2,
            target_cells=0,
            union_cells=0,
        )


def test_independent_upperness_and_certified_roundtrips_rederive_authority() -> None:
    verified, exact, candidate, evidence, witness, certified = _bundle(
        overcover_first=True
    )
    assert len(evidence.rows) == 8
    assert witness.to_dict()["covered_member_action_count"] == 8
    assert certified.to_dict()["operator_tier"] == CERTIFIED_OPERATOR_TIER
    assert CertifiedIntervalOperator.from_dict(
        certified.to_dict(), exact, candidate, witness
    ).to_dict() == certified.to_dict()
    assert UppernessDomainWitness.from_dict(
        witness.to_dict(), exact, candidate, evidence
    ).to_dict() == witness.to_dict()
    assert "envelope" not in certified.to_dict()
    assert "contraction" not in certified.to_dict()
    assert _make_evidence(verified, exact, candidate).to_dict() == evidence.to_dict()


def test_upperness_kills_undercoverage_missing_rows_and_wrong_bindings() -> None:
    verified, exact, candidate, *_ = _bundle()
    exact_wire = exact.to_dict()
    first = candidate.rows[0]
    exact_target = exact_wire["rows"][0]["target_block_index"]
    other = 0 if exact_target != 0 else 1
    under_rows = (replace(first, target_block_indices=(other,)),) + candidate.rows[1:]
    under = make_interval_candidate(
        exact, under_rows, provenance_id="unit_cpu_survivor_undercoverage"
    )
    under_evidence = _make_evidence(verified, exact, under)
    with pytest.raises(StrictContractError, match="undercovers"):
        verify_upperness_domain(exact, under, under_evidence)

    missing_rows = _evidence_rows(verified)[:-1]
    missing = _make_evidence(
        verified, exact, candidate, rows=missing_rows
    )
    with pytest.raises(StrictContractError, match="every exact member/action"):
        verify_upperness_domain(exact, candidate, missing)

    wrong_frame = _make_evidence(
        verified, exact, candidate, frame_digest="AA" * 32
    )
    with pytest.raises(StrictContractError, match="frame"):
        verify_upperness_domain(exact, candidate, wrong_frame)


def test_candidate_extension_is_monotone_and_invalidates_old_witness() -> None:
    verified, exact, candidate, evidence, witness, _ = _bundle()
    first = candidate.rows[0]
    block_count = exact.to_dict()["block_count"]
    other = next(
        block for block in range(block_count) if block not in first.target_block_indices
    )
    extended = extend_interval_candidate(
        exact,
        candidate,
        (IntervalTargetRow(first.source_block_index, first.action_id, (other,)),),
        provenance_id="unit_cpu_survivor_extended_candidate",
    )
    assert set(candidate.rows[0].target_block_indices) < set(
        extended.rows[0].target_block_indices
    )
    with pytest.raises(StrictContractError, match="different candidate"):
        verify_upperness_domain(exact, extended, evidence)
    fresh_evidence = _make_evidence(verified, exact, extended)
    fresh_witness = verify_upperness_domain(exact, extended, fresh_evidence)
    assert fresh_witness.witness_sha256 != witness.witness_sha256


def test_candidate_extension_accepts_near_cap_noop_without_false_rejection(
    monkeypatch,
) -> None:
    context, raw_rows = _near_cap_context(exact_target=0)
    monkeypatch.setattr(qg, "_exact_context", lambda _exact: context)
    rows = tuple(
        IntervalTargetRow(
            row["source_block_index"],
            row["action_id"],
            tuple(row["target_block_indices"]),
        )
        for row in raw_rows
    )
    candidate = IntervalCandidate(
        context.operator_sha256,
        "unit_cpu_survivor_near_cap_candidate",
        rows,
        MAX_TIER_FIREWALL_WORK_UNITS,
    )
    noop = IntervalTargetRow(rows[0].source_block_index, rows[0].action_id, (0,))
    extended = extend_interval_candidate(
        object(),  # type: ignore[arg-type]
        candidate,
        (noop,),
        provenance_id="unit_cpu_survivor_near_cap_noop",
    )
    assert extended.work_units == MAX_TIER_FIREWALL_WORK_UNITS
    assert extended.rows == candidate.rows


def test_witness_and_certified_serializers_reject_low_level_mutation() -> None:
    _, exact, candidate, evidence, witness, certified = _bundle()
    object.__setattr__(witness, "_candidate_seal_sha256", "00" * 32)
    with pytest.raises(StrictContractError):
        witness.to_dict()

    witness = verify_upperness_domain(exact, candidate, evidence)
    certified = certify_interval_operator(exact, candidate, witness)
    object.__setattr__(certified, "_witness_seal_sha256", "00" * 32)
    with pytest.raises(StrictContractError):
        certified.to_dict()

    witness = verify_upperness_domain(exact, candidate, evidence)
    payload = witness.to_dict()
    payload["unknown"] = True
    with pytest.raises(StrictContractError):
        UppernessDomainWitness.from_dict(payload, exact, candidate, evidence)


def test_nested_candidate_mutation_cannot_cross_the_tier_firewall() -> None:
    _, exact, candidate, evidence, witness, _ = _bundle()
    row = candidate.rows[0]
    for field_name, mutated_value in (
        ("target_block_indices", (False,)),
        ("target_block_indices", (0, 0)),
        ("target_block_indices", (1, 0)),
        ("source_block_index", False),
    ):
        original = getattr(row, field_name)
        object.__setattr__(row, field_name, mutated_value)
        with pytest.raises(StrictContractError):
            candidate.to_dict()
        with pytest.raises(StrictContractError):
            verify_upperness_domain(exact, candidate, evidence)
        with pytest.raises(StrictContractError):
            certify_interval_operator(exact, candidate, witness)
        object.__setattr__(row, field_name, original)


def test_capability_seals_and_retained_witness_sources_are_rechecked() -> None:
    exact = export_exact_finite_operator(_verified())
    object.__setattr__(exact, "_construction_seal", None)
    with pytest.raises(StrictContractError, match="construction seal"):
        exact.to_dict()

    _, exact, candidate, evidence, witness, certified = _bundle()
    object.__setattr__(certified, "_construction_seal", None)
    with pytest.raises(StrictContractError, match="construction seal"):
        certified.to_dict()

    object.__setattr__(witness, "_construction_seal", None)
    with pytest.raises(StrictContractError, match="construction seal"):
        witness.to_dict()
    with pytest.raises(StrictContractError, match="construction seal"):
        certify_interval_operator(exact, candidate, witness)

    _, exact, candidate, evidence, witness, _ = _bundle()
    object.__setattr__(
        witness,
        "_exact_source",
        export_exact_finite_operator(_verified(perturb=True)),
    )
    with pytest.raises(StrictContractError):
        witness.to_dict()
    with pytest.raises(StrictContractError):
        certify_interval_operator(exact, candidate, witness)
    object.__setattr__(witness, "_exact_source", exact)

    other_candidate = make_interval_candidate(
        exact,
        _candidate_rows(exact, overcover_first=True),
        provenance_id="unit_cpu_survivor_other_candidate",
    )
    object.__setattr__(witness, "_candidate_source", other_candidate)
    with pytest.raises(StrictContractError):
        witness.to_dict()
    with pytest.raises(StrictContractError):
        certify_interval_operator(exact, candidate, witness)


def test_independent_evidence_serializer_rejects_low_level_mutation() -> None:
    _, _, _, evidence, _, _ = _bundle()
    row = evidence.rows[0]
    original_target = row.concrete_target_block_index
    object.__setattr__(row, "concrete_target_block_index", False)
    with pytest.raises(StrictContractError):
        evidence.to_dict()
    object.__setattr__(row, "concrete_target_block_index", original_target)

    original_issuer = evidence.issuer
    object.__setattr__(evidence, "issuer", "")
    with pytest.raises(StrictContractError):
        evidence.to_dict()
    object.__setattr__(evidence, "issuer", original_issuer)

    object.__setattr__(evidence, "rows", tuple(reversed(evidence.rows)))
    with pytest.raises(StrictContractError, match="canonical"):
        evidence.to_dict()


def test_runner_hides_the_exit_receipt_from_semantic_tests() -> None:
    if os.environ.get("UPRIME_WP6T_SUBPROCESS_POLICY") == "forbid":
        assert "UPRIME_WP6T_EXIT_RECEIPT" not in os.environ
        with pytest.raises(RuntimeError, match="may not spawn subprocesses"):
            os._exit(0)


def test_standalone_observed_and_nominal_tiers_have_no_promotion_surface() -> None:
    row = IntervalTargetRow(0, "unit_cpu_survivor_a", (0, 1))
    observed = ObservedIntervalOperator(
        "unit_cpu_survivor_observation", (row,)
    )
    nominal = NominalOperator("unit_cpu_survivor_model", (row,))
    assert observed.to_dict()["operator_tier"] == OBSERVED_OPERATOR_TIER
    assert nominal.to_dict()["operator_tier"] == NOMINAL_OPERATOR_TIER
    assert ObservedIntervalOperator.from_dict(observed.to_dict()) == observed
    assert NominalOperator.from_dict(nominal.to_dict()) == nominal

    forbidden = {
        "FiberEnvelope",
        "derive_upperness_evidence",
        "witness_from_exact",
        "promote_observed",
        "promote_nominal",
        "exact_to_observed",
        "certified_to_nominal",
    }
    assert forbidden.isdisjoint(qg.__all__)
    assert forbidden.isdisjoint(dir(qg))
    assert forbidden.isdisjoint(odlrq_package.__all__)
    assert forbidden.isdisjoint(dir(odlrq_package))
    assert set(qg.__all__) <= set(odlrq_package.__all__)
    _, exact, candidate, *_ = _bundle()
    assert not hasattr(exact, "to_observed")
    assert not hasattr(candidate, "certify")
    with pytest.raises(StrictContractError):
        ObservedIntervalOperator.from_dict(exact.to_dict())


def test_capability_constructors_and_external_authorities_are_mandatory() -> None:
    _, exact, candidate, evidence, witness, _ = _bundle()
    with pytest.raises(StrictContractError):
        UppernessDomainWitness(
            exact,
            candidate,
            evidence,
            exact.operator_sha256,
            candidate.candidate_sha256,
            hashlib.sha256(canonical_contract_bytes(evidence.to_dict())).hexdigest(),
        )
    with pytest.raises(StrictContractError):
        CertifiedIntervalOperator(
            exact,
            candidate,
            witness,
            exact.operator_sha256,
            candidate.candidate_sha256,
            witness.witness_sha256,
        )
