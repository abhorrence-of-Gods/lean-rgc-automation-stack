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
    ExactQuotientCoordinateGenerator,
    ExactQuotientCoordinateTerm,
    ExactQuotientTransferRow,
    IntervalCandidate,
    IntervalTargetRow,
    NominalOperator,
    ObservedIntervalOperator,
    UppernessDomainEvidence,
    UppernessDomainWitness,
    UppernessEvidenceRow,
    build_exact_quotient_coordinate_generator,
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
_READ_ONLY_BUNDLE_TEMPLATES = {}


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


def _read_only_bundle(*, overcover_first: bool = False):
    if overcover_first not in _READ_ONLY_BUNDLE_TEMPLATES:
        _READ_ONLY_BUNDLE_TEMPLATES[overcover_first] = _bundle(
            overcover_first=overcover_first
        )
    return _READ_ONLY_BUNDLE_TEMPLATES[overcover_first]


def test_exact_export_rederives_complete_totalized_member_action_table() -> None:
    verified, exact, *_ = _read_only_bundle()
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
    _, exact, candidate, *_ = _read_only_bundle()
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
    _, exact, candidate, *_ = _read_only_bundle()
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
    verified, exact, candidate, evidence, witness, certified = _read_only_bundle(
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
    verified, exact, candidate, *_ = _read_only_bundle()
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
    verified, exact, candidate, evidence, witness, _ = _read_only_bundle()
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
    _, exact, candidate, *_ = _read_only_bundle()
    assert not hasattr(exact, "to_observed")
    assert not hasattr(candidate, "certify")
    with pytest.raises(StrictContractError):
        ObservedIntervalOperator.from_dict(exact.to_dict())


def test_capability_constructors_and_external_authorities_are_mandatory() -> None:
    _, exact, candidate, evidence, witness, _ = _read_only_bundle()
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


_E0_LITERAL_FIXTURES = {
    "g0-self": {
        "blocks": (("c0",), ("k0",), ("s0",)),
        "actions": ("a",),
        "seeds": ("s0",),
        "transitions": (
            ("c0", "a", "c0"),
            ("k0", "a", "k0"),
            ("s0", "a", "s0"),
        ),
        "counts": (3, 3, 0, 6),
    },
    "g0-move": {
        "blocks": (("c0",), ("k0",), ("s0",), ("s1",)),
        "actions": ("a",),
        "seeds": ("s0", "s1"),
        "transitions": (
            ("c0", "a", "c0"),
            ("k0", "a", "k0"),
            ("s0", "a", "s1"),
            ("s1", "a", "s1"),
        ),
        "counts": (4, 4, 2, 10),
    },
    "g0-diamond": {
        "blocks": (("c0",), ("k0",), ("s0",), ("s1",), ("s2",)),
        "actions": ("a", "b"),
        "seeds": ("s0", "s1", "s2"),
        "transitions": (
            ("c0", "a", "c0"),
            ("c0", "b", "c0"),
            ("k0", "a", "k0"),
            ("k0", "b", "k0"),
            ("s0", "a", "s1"),
            ("s0", "b", "s2"),
            ("s1", "a", "c0"),
            ("s1", "b", "c0"),
            ("s2", "a", "c0"),
            ("s2", "b", "c0"),
        ),
        "counts": (10, 10, 12, 32),
    },
    "g0-members": {
        "blocks": (("c0",), ("k0",), ("s0", "s1"), ("s2",)),
        "actions": ("a",),
        "seeds": ("s0", "s1", "s2"),
        "transitions": (
            ("c0", "a", "c0"),
            ("k0", "a", "k0"),
            ("s0", "a", "s2"),
            ("s1", "a", "s2"),
            ("s2", "a", "s2"),
        ),
        "counts": (4, 5, 2, 11),
    },
}

_E0_ENVIRONMENT_GOLDENS = {
    "g0-self": "283B385D4C4B94CCC95D78F3C00011A9A346D5849B672D9CE0EF573B6F355976",
    "g0-move": "93FF6D36128B71981E15328394F7F6A6BAB0ACACF61AD097FBBD30E2F22BADEF",
    "g0-diamond": "B1A382AE41D20CED55868F93EB6B08B1C9E977D2A63C8935C6264A3CEBFC991D",
    "g0-members": "58BE31966AFBDA28404F72F125CD293C6798E786070F8526051CAAF6C07FD3DA",
}
_E0_FRAME_GOLDENS = {
    "g0-self": "7F6A76BD673572C9F1888230220557D845B21AC80AAE54BC2CBD10490215F82C",
    "g0-move": "A5E11715182E1CD275ADAE0CC3C77456B73618EB08E4C2E5826861AF82AEC119",
    "g0-diamond": "7093C282CE605CA5D7B40E16D5ED19D283E251F4E80FCD6ED7A05F91019E5E98",
    "g0-members": "71847DA839E836027AFB1EB1F3EB89DB3ECB6382FC2F5ED3C814DD50F605EE0D",
}
_E0_SNAPSHOT_GOLDENS = {
    "g0-self": "9E0694A572EEFBF5C94EA2728C5C8CB5098BAB7048770D3F436FD4DD4F128E19",
    "g0-move": "5FCD68AE8156442DA6B10B25B2C9D7A4687735AEBF90E71234C3CA285D09638E",
    "g0-diamond": "DC4564C17FE33DFBC119B9DC841DEB36FE9DB5C0AF83BFF397B2B23637408ED5",
    "g0-members": "81C9582E8AAD94F3FB4F817C92D603A20D393B1BFFCCB82EC3AD6F935D98BD27",
}
_E0_EXACT_OPERATOR_GOLDENS = {
    "g0-self": "7153EDD8ADEC236FFBA616AFA60FF71EA70D173A9E655B1EB917FED262EA60D7",
    "g0-move": "6E2B32C950467EDDC9DDD269BF17457584689E32B08DF3AA051DCD188D2EB646",
    "g0-diamond": "E4128213F843BA492E9B3A67D3B71CFF1A4229491A1DF84984BFFE2F2D77E02D",
    "g0-members": "29D5E0CCC3254BF5B70EB56D033AAE71140B90B418FB3E2C1D43D71C8B06797A",
}
_E0_SOURCE_SEAL_GOLDENS = {
    "g0-self": "B4E1C7D7BB8FED314196151ABED55B464BA41B793B1F13494CF913FA11BEA87B",
    "g0-move": "68CCD648E42F7469CC275B0524FED1D8E79020CD2D6456AE85E528FE67EDD9AF",
    "g0-diamond": "624634570FF53154446B46C7945C399BA45146B1DED5DE9B13B62DB83B2BB3A2",
    "g0-members": "990CBCEF52531055E512EC8A78F4B0B5084BE1DBC111E9AE622273775BBE605A",
}
_E0_VERIFIED_TEMPLATES = {}
_E0_READ_ONLY_GENERATORS = {}


def _e0_sha(value) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _e0_full(atom: str) -> str:
    return f"unit_cpu_survivor_{atom}"


def _e0_fixture_snapshot(name: str, *, reverse: bool = False):
    spec = _E0_LITERAL_FIXTURES[name]
    environment_digest = _e0_sha({"bundle": "u24", "fixture": name})
    vocabulary = ResponseVocabularyId.from_coordinate_names(("block_index",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment_digest,
        response_vocabulary_id=vocabulary,
    )
    frame_digest = observation_frame_digest(frame)
    state_atoms = tuple(atom for block in spec["blocks"] for atom in block)
    open_coordinates = {
        atom: block_index - 2
        for block_index, block in enumerate(spec["blocks"])
        for atom in block
        if atom not in {"c0", "k0"}
    }
    states = tuple(
        SyntheticTotalizedState(
            state_id=_e0_full(atom),
            payload=CanonicalPayload.from_value(
                {"kind": "u24_state", "name": _e0_full(atom)}
            ),
            totalized_kind=(
                TotalizedStatus.CLOSED
                if atom == "c0"
                else TotalizedStatus.SINK
                if atom == "k0"
                else TotalizedStatus.OPEN
            ),
            response_coordinates=(
                ExactRational(
                    100
                    if atom == "c0"
                    else 101
                    if atom == "k0"
                    else open_coordinates[atom]
                ),
            ),
            frame_digest=frame_digest,
        )
        for atom in state_atoms
    )
    actions = tuple(
        SyntheticAction(
            action_id=_e0_full(atom),
            payload=CanonicalPayload.from_value(
                {"kind": "u24_action", "name": _e0_full(atom)}
            ),
        )
        for atom in spec["actions"]
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=actions, response_vocabulary_id=vocabulary
    )
    transitions = tuple(
        SyntheticTransitionRow(
            source_state_id=_e0_full(source),
            action_id=_e0_full(action),
            target_state_id=_e0_full(target),
            transition_semantics_digest=semantics.semantics_digest,
        )
        for source, action, target in spec["transitions"]
    )
    seeds = tuple(_e0_full(atom) for atom in spec["seeds"])
    if reverse:
        states = tuple(reversed(states))
        actions = tuple(reversed(actions))
        transitions = tuple(reversed(transitions))
        seeds = tuple(reversed(seeds))
    return build_synthetic_finite_snapshot(
        environment_digest=environment_digest,
        coordinate_names=("block_index",),
        seed_state_ids=seeds,
        states=states,
        actions=actions,
        transitions=transitions,
        frame_digest=frame_digest,
        transition_semantics_digest=semantics.semantics_digest,
    )


def _e0_verified(name: str, *, reverse: bool = False):
    key = (name, reverse)
    if key not in _E0_VERIFIED_TEMPLATES:
        admitted = admit_synthetic_finite_snapshot(
            _e0_fixture_snapshot(name, reverse=reverse)
        )
        certificate = refine_exact_partition(admitted)
        _E0_VERIFIED_TEMPLATES[key] = verify_exact_partition(
            admitted, certificate
        )
    return copy.deepcopy(_E0_VERIFIED_TEMPLATES[key])


def _e0_read_only_generator(name: str):
    if name not in _E0_READ_ONLY_GENERATORS:
        verified = _e0_verified(name)
        generator = build_exact_quotient_coordinate_generator(verified)
        _E0_READ_ONLY_GENERATORS[name] = (
            verified,
            generator,
            generator.to_dict(),
        )
    return _E0_READ_ONLY_GENERATORS[name]


def _e0_literal_oracle(name: str, verified):
    spec = _E0_LITERAL_FIXTURES[name]
    blocks = tuple(tuple(_e0_full(atom) for atom in block) for block in spec["blocks"])
    action_ids = tuple(_e0_full(atom) for atom in spec["actions"])
    block_owner = {
        member: block_index
        for block_index, block in enumerate(blocks)
        for member in block
    }
    literal_targets = {
        (_e0_full(source), _e0_full(action)): _e0_full(target)
        for source, action, target in spec["transitions"]
    }
    states = {state.state_id: state for state in verified.admitted.snapshot.states}
    actions = {
        action.action_id: action for action in verified.admitted.snapshot.actions
    }
    rows = []
    for source_block_index, members in enumerate(blocks):
        for action_id in action_ids:
            targets = {block_owner[literal_targets[(member, action_id)]] for member in members}
            assert len(targets) == 1
            target_block_index = targets.pop()
            terms = ()
            if target_block_index != source_block_index:
                terms = tuple(
                    sorted(
                        (
                            (source_block_index, -1, 1),
                            (target_block_index, 1, 1),
                        )
                    )
                )
            member_transitions = [
                {
                    "source_state_id": member,
                    "source_state_sha256": _e0_sha(states[member].to_dict()),
                    "target_state_id": literal_targets[(member, action_id)],
                    "target_state_sha256": _e0_sha(
                        states[literal_targets[(member, action_id)]].to_dict()
                    ),
                }
                for member in members
            ]
            precursor = {
                "source_block_index": source_block_index,
                "action_id": action_id,
                "action_sha256": _e0_sha(actions[action_id].to_dict()),
                "target_block_index": target_block_index,
                "member_transition_count": len(member_transitions),
                "member_transitions": member_transitions,
            }
            rows.append(
                {
                    "source_block_index": source_block_index,
                    "action_id": action_id,
                    "action_sha256": precursor["action_sha256"],
                    "target_block_index": target_block_index,
                    "member_transition_count": len(member_transitions),
                    "member_transition_sha256": _e0_sha(precursor),
                    "terms": terms,
                }
            )
    return blocks, action_ids, rows


def _e0_literal_source_seal(name: str, verified, blocks, action_ids) -> str:
    snapshot = verified.admitted.snapshot
    states = {state.state_id: state for state in snapshot.states}
    actions = {action.action_id: action for action in snapshot.actions}
    block_wires = [
        {
            "block_index": block_index,
            "member_count": len(members),
            "members": [states[member].to_dict() for member in members],
        }
        for block_index, members in enumerate(blocks)
    ]
    action_wires = [actions[action_id].to_dict() for action_id in action_ids]
    return _e0_sha(
        {
            "seal_version": "odlrq_exact_quotient_coordinate_source_seal_v1",
            "admission_report_sha256": _e0_sha(
                verified.admitted.admission_report.to_dict()
            ),
            "verified_partition_sha256": _e0_sha(verified.to_dict()),
            "exact_operator_sha256": _E0_EXACT_OPERATOR_GOLDENS[name],
            "canonical_block_order_sha256": _e0_sha({"blocks": block_wires}),
            "canonical_action_order_sha256": _e0_sha({"actions": action_wires}),
        }
    )


def test_e0_exact_coordinate_generator_matches_frozen_independent_oracle() -> None:
    generator_fields = {
        "schema_version", "evidence_scope", "domain_scope",
        "basis_convention", "generator_convention",
        "admission_report_sha256", "snapshot_sha256", "environment_digest",
        "reachable_domain_sha256", "domain_payload_digest", "seed_set_digest",
        "observation_frame_digest", "transition_semantics_digest",
        "response_vocabulary_digest", "action_alphabet_digest",
        "synthetic_evidence_profile_sha256", "verified_partition_sha256",
        "exact_operator_sha256", "canonical_block_order_sha256",
        "canonical_action_order_sha256", "source_seal_sha256",
        "totalized_state_count", "block_count", "action_count",
        "canonical_block_indices", "canonical_action_ids", "row_count",
        "term_count", "member_action_witness_count", "work_units", "rows",
    }
    for name, spec in _E0_LITERAL_FIXTURES.items():
        verified, generator, wire = _e0_read_only_generator(name)
        snapshot = verified.admitted.snapshot
        assert snapshot.domain_id.environment_digest == _E0_ENVIRONMENT_GOLDENS[name]
        assert snapshot.domain_id.frame_digest == _E0_FRAME_GOLDENS[name]
        assert (
            verified.admitted.admission_report.snapshot_sha256
            == _E0_SNAPSHOT_GOLDENS[name]
        )
        blocks, action_ids, expected_rows = _e0_literal_oracle(name, verified)
        literal_source_seal = _e0_literal_source_seal(
            name, verified, blocks, action_ids
        )
        assert literal_source_seal == _E0_SOURCE_SEAL_GOLDENS[name]
        assert wire["source_seal_sha256"] == literal_source_seal
        assert tuple(
            tuple(block.member_state_ids) for block in verified.certificate.final_blocks
        ) == blocks
        assert tuple(verified.certificate.canonical_action_ids) == action_ids
        assert tuple(
            (
                row.source_block_index,
                row.action_id,
                row.target_block_index,
            )
            for row in verified.certificate.quotient_rows
        ) == tuple(
            (
                row["source_block_index"],
                row["action_id"],
                row["target_block_index"],
            )
            for row in expected_rows
        )

        assert set(wire) == generator_fields
        assert wire["schema_version"] == "odlrq_exact_quotient_coordinate_generator_v1"
        assert wire["evidence_scope"] == "synthetic_development"
        assert wire["domain_scope"] == "declared_finite_totalized_snapshot_only"
        assert wire["basis_convention"] == "block_basis_column_source_v1"
        assert wire["generator_convention"] == "P_action_minus_identity_v1"
        assert wire["exact_operator_sha256"] == _E0_EXACT_OPERATOR_GOLDENS[name]
        assert wire["canonical_block_indices"] == list(range(len(blocks)))
        assert wire["canonical_action_ids"] == list(action_ids)
        assert (
            wire["row_count"],
            wire["member_action_witness_count"],
            wire["term_count"],
            wire["work_units"],
        ) == spec["counts"]
        if name == "g0-move":
            assert generator.generator_sha256 == _e0_sha(wire)

        for actual, expected in zip(wire["rows"], expected_rows, strict=True):
            assert set(actual) == {
                "schema_version", "evidence_scope", "domain_scope",
                "source_block_index", "action_id", "action_sha256",
                "structural_target_block_index", "member_transition_count",
                "member_transition_sha256", "terms",
            }
            assert actual["source_block_index"] == expected["source_block_index"]
            assert actual["action_id"] == expected["action_id"]
            assert actual["action_sha256"] == expected["action_sha256"]
            assert (
                actual["structural_target_block_index"]
                == expected["target_block_index"]
            )
            assert (
                actual["member_transition_count"]
                == expected["member_transition_count"]
            )
            assert (
                actual["member_transition_sha256"]
                == expected["member_transition_sha256"]
            )
            actual_terms = tuple(
                (
                    term["target_block_index"],
                    int(term["coefficient"]["numerator"]),
                    int(term["coefficient"]["denominator"]),
                )
                for term in actual["terms"]
            )
            assert actual_terms == expected["terms"]
            for term in actual["terms"]:
                assert set(term) == {
                    "schema_version", "evidence_scope", "domain_scope",
                    "target_block_index", "coefficient",
                }

        if name == "g0-members":
            member_row = wire["rows"][2]
            assert member_row["member_transition_count"] == 2
            assert [term["coefficient"]["numerator"] for term in member_row["terms"]] == [
                "-1", "1"
            ]


def test_e0_roundtrip_permutation_cancellation_and_terminal_rows() -> None:
    verified, _, wire = _e0_read_only_generator("g0-diamond")
    assert ExactQuotientCoordinateGenerator.from_dict(wire, verified).to_dict() == wire
    reversed_wire = build_exact_quotient_coordinate_generator(
        _e0_verified("g0-diamond", reverse=True)
    ).to_dict()
    assert canonical_contract_bytes(reversed_wire) == canonical_contract_bytes(wire)
    for row_wire in wire["rows"]:
        row = ExactQuotientTransferRow.from_dict(row_wire)
        assert row.to_dict() == row_wire
        if row.source_block_index in (0, 1):
            assert row.structural_target_block_index == row.source_block_index
            assert row.terms == ()
        for term in row.terms:
            assert ExactQuotientCoordinateTerm.from_dict(term.to_dict()) == term


def test_e0_scope_fields_fail_closed_at_every_wire_layer() -> None:
    verified, _, wire = _e0_read_only_generator("g0-diamond")
    row_wire = wire["rows"][4]
    term_wire = row_wire["terms"][0]
    layers = (
        (
            "generator",
            wire,
            lambda value: ExactQuotientCoordinateGenerator.from_dict(
                value, verified
            ),
        ),
        ("row", row_wire, ExactQuotientTransferRow.from_dict),
        ("term", term_wire, ExactQuotientCoordinateTerm.from_dict),
    )
    for layer_name, payload, parser in layers:
        attacks = []
        missing = copy.deepcopy(payload)
        del missing["schema_version"]
        attacks.append(("missing", missing))
        altered = copy.deepcopy(payload)
        altered["schema_version"] = "odlrq_promoted_schema_v999"
        attacks.append(("altered", altered))
        unknown = copy.deepcopy(payload)
        unknown["unknown"] = True
        attacks.append(("unknown", unknown))
        missing_evidence_scope = copy.deepcopy(payload)
        del missing_evidence_scope["evidence_scope"]
        attacks.append(("missing-evidence-scope", missing_evidence_scope))
        evidence_promotion = copy.deepcopy(payload)
        evidence_promotion["evidence_scope"] = "protected_evaluation"
        attacks.append(("evidence-promotion", evidence_promotion))
        missing_domain_scope = copy.deepcopy(payload)
        del missing_domain_scope["domain_scope"]
        attacks.append(("missing-domain-scope", missing_domain_scope))
        domain_promotion = copy.deepcopy(payload)
        domain_promotion["domain_scope"] = "unbounded_global_domain"
        attacks.append(("domain-promotion", domain_promotion))
        assert len(attacks) == 7
        for attack_name, attack in attacks:
            with pytest.raises(
                StrictContractError, match="|".join((layer_name, "schema", "field", "scope"))
            ):
                parser(attack)


def test_e0_wire_and_source_attacks_fail_closed(monkeypatch) -> None:
    verified, _, wire = _e0_read_only_generator("g0-diamond")

    attacks = []
    missing = copy.deepcopy(wire)
    del missing["source_seal_sha256"]
    attacks.append(missing)
    unknown = copy.deepcopy(wire)
    unknown["unknown"] = 1
    attacks.append(unknown)
    tuple_rows = copy.deepcopy(wire)
    tuple_rows["rows"] = tuple(tuple_rows["rows"])
    attacks.append(tuple_rows)
    bool_count = copy.deepcopy(wire)
    bool_count["row_count"] = True
    attacks.append(bool_count)
    float_index = copy.deepcopy(wire)
    float_index["canonical_block_indices"][0] = 0.0
    attacks.append(float_index)
    lowercase = copy.deepcopy(wire)
    lowercase["snapshot_sha256"] = lowercase["snapshot_sha256"].lower()
    attacks.append(lowercase)
    reordered = copy.deepcopy(wire)
    reordered["rows"][0], reordered["rows"][1] = (
        reordered["rows"][1], reordered["rows"][0]
    )
    attacks.append(reordered)
    duplicate = copy.deepcopy(wire)
    duplicate["rows"][1] = copy.deepcopy(duplicate["rows"][0])
    attacks.append(duplicate)
    bad_member = copy.deepcopy(wire)
    bad_member["rows"][0]["member_transition_count"] += 1
    attacks.append(bad_member)
    bad_digest = copy.deepcopy(wire)
    bad_digest["rows"][0]["member_transition_sha256"] = "00" * 32
    attacks.append(bad_digest)
    bad_target = copy.deepcopy(wire)
    bad_target["rows"][4]["structural_target_block_index"] = 0
    attacks.append(bad_target)
    reversed_terms = copy.deepcopy(wire)
    reversed_terms["rows"][6]["terms"].reverse()
    attacks.append(reversed_terms)
    unreduced = copy.deepcopy(wire)
    unreduced_coefficient = unreduced["rows"][4]["terms"][0]["coefficient"]
    unreduced_coefficient["numerator"] = "-2"
    unreduced_coefficient["denominator"] = "2"
    attacks.append(unreduced)
    with pytest.raises(StrictContractError):
        ExactQuotientCoordinateGenerator.from_dict(
            wire, _e0_verified("g0-move")
        )

    monkeypatch.setattr(
        qg,
        "_derive_exact_quotient_generator_wire",
        lambda _source: copy.deepcopy(wire),
    )
    for attack in attacks:
        with pytest.raises(StrictContractError):
            ExactQuotientCoordinateGenerator.from_dict(attack, verified)

    too_many_rows = copy.deepcopy(wire)
    too_many_rows["rows"] = [copy.deepcopy(wire["rows"][0]) for _ in range(2_049)]
    monkeypatch.setattr(
        qg,
        "_derive_exact_quotient_generator_wire",
        lambda _source: (_ for _ in ()).throw(
            AssertionError("authority was touched before raw cap preflight")
        ),
    )
    with pytest.raises(StrictContractError, match="row cap"):
        ExactQuotientCoordinateGenerator.from_dict(too_many_rows, verified)

    too_many_blocks = copy.deepcopy(wire)
    too_many_blocks["canonical_block_indices"] = list(range(129))
    with pytest.raises(StrictContractError, match="block-order cap"):
        ExactQuotientCoordinateGenerator.from_dict(too_many_blocks, verified)

    too_many_actions = copy.deepcopy(wire)
    too_many_actions["canonical_action_ids"] = [
        f"unit_cpu_survivor_a{index}" for index in range(17)
    ]
    with pytest.raises(StrictContractError, match="action-order cap"):
        ExactQuotientCoordinateGenerator.from_dict(too_many_actions, verified)

    too_many_terms = copy.deepcopy(wire)
    too_many_terms["rows"][4]["terms"].append(
        copy.deepcopy(too_many_terms["rows"][4]["terms"][0])
    )
    with pytest.raises(StrictContractError, match="more than two raw terms"):
        ExactQuotientCoordinateGenerator.from_dict(too_many_terms, verified)

    huge_rational = copy.deepcopy(wire)
    huge_rational["rows"][4]["terms"][0]["coefficient"]["numerator"] = (
        "1" * 2_468
    )
    with pytest.raises(StrictContractError, match="decimal preflight cap"):
        ExactQuotientCoordinateGenerator.from_dict(huge_rational, verified)


def test_e0_signed64_preflight_rejects_before_authority(monkeypatch) -> None:
    verified, _, wire = _e0_read_only_generator("g0-diamond")
    authority_touched = False

    def forbidden_authority(_source):
        nonlocal authority_touched
        authority_touched = True
        raise AssertionError("authority touched before raw signed-64 preflight")

    monkeypatch.setattr(
        qg, "_derive_exact_quotient_generator_wire", forbidden_authority
    )
    term_row_index = next(
        index for index, row in enumerate(wire["rows"]) if row["terms"]
    )
    for boundary in (-1, 2**63):
        attacks = []
        for field_name in (
            "totalized_state_count",
            "block_count",
            "action_count",
            "row_count",
            "term_count",
            "member_action_witness_count",
            "work_units",
        ):
            attack = copy.deepcopy(wire)
            attack[field_name] = boundary
            attacks.append((field_name, attack))

        block_index = copy.deepcopy(wire)
        block_index["canonical_block_indices"][0] = boundary
        attacks.append(("canonical_block_index", block_index))
        for field_name in (
            "source_block_index",
            "structural_target_block_index",
            "member_transition_count",
        ):
            attack = copy.deepcopy(wire)
            attack["rows"][0][field_name] = boundary
            attacks.append((field_name, attack))
        term_index = copy.deepcopy(wire)
        term_index["rows"][term_row_index]["terms"][0][
            "target_block_index"
        ] = boundary
        attacks.append(("target_block_index", term_index))

        assert len(attacks) == 12
        for _field_name, attack in attacks:
            with pytest.raises(StrictContractError, match="nonnegative integer"):
                ExactQuotientCoordinateGenerator.from_dict(attack, verified)
    assert not authority_touched


def test_e0_source_type_is_checked_before_attribute_access() -> None:
    _, _, wire = _e0_read_only_generator("g0-move")

    class SourceAttributeTrap:
        def __getattribute__(self, name):
            raise AssertionError(f"source attribute was touched: {name}")

    trap = SourceAttributeTrap()
    with pytest.raises(StrictContractError, match="VerifiedExactPartition"):
        build_exact_quotient_coordinate_generator(trap)  # type: ignore[arg-type]
    with pytest.raises(StrictContractError, match="verified source"):
        ExactQuotientCoordinateGenerator.from_dict(  # type: ignore[arg-type]
            wire, trap
        )


def test_e0_capability_types_and_later_tiers_are_rejected() -> None:
    verified, _, wire = _e0_read_only_generator("g0-move")
    generator = build_exact_quotient_coordinate_generator(verified)
    with pytest.raises(StrictContractError):
        ExactQuotientCoordinateGenerator(
            verified, wire["source_seal_sha256"]
        )
    with pytest.raises(StrictContractError, match="no public constructor"):
        ExactQuotientCoordinateGenerator()
    with pytest.raises(StrictContractError, match="no public constructor"):
        ExactQuotientCoordinateGenerator(
            verified,
            wire["source_seal_sha256"],
            _construction_seal=qg._EXACT_QUOTIENT_GENERATOR_SEAL,
        )
    with pytest.raises(StrictContractError):
        ExactQuotientCoordinateTerm(0, ExactRational(0))

    class BadTerm(ExactQuotientCoordinateTerm):
        pass

    class BadRow(ExactQuotientTransferRow):
        pass

    class BadGenerator(ExactQuotientCoordinateGenerator):
        pass

    with pytest.raises(StrictContractError):
        BadTerm(0, ExactRational(1))
    with pytest.raises(StrictContractError):
        BadRow.from_dict(wire["rows"][0])
    with pytest.raises(StrictContractError):
        BadGenerator.from_dict(wire, verified)

    _, exact, _, _, _, certified = _read_only_bundle()
    row = IntervalTargetRow(0, "unit_cpu_survivor_a", (0,))
    observed = ObservedIntervalOperator("unit_cpu_survivor_observation", (row,))
    nominal = NominalOperator("unit_cpu_survivor_model", (row,))
    for invalid_source in (exact, certified, observed, nominal):
        with pytest.raises(StrictContractError):
            build_exact_quotient_coordinate_generator(invalid_source)  # type: ignore[arg-type]
        with pytest.raises(StrictContractError):
            ExactQuotientCoordinateGenerator.from_dict(  # type: ignore[arg-type]
                wire, invalid_source
            )

    object.__setattr__(generator, "_source_seal_sha256", "00" * 32)
    with pytest.raises(StrictContractError):
        generator.to_dict()

    mutated_source = _e0_verified("g0-move")
    mutated_generator = build_exact_quotient_coordinate_generator(mutated_source)
    object.__setattr__(mutated_source, "verification_report", object())
    with pytest.raises(StrictContractError):
        mutated_generator.to_dict()

    row = ExactQuotientTransferRow.from_dict(wire["rows"][2])
    object.__setattr__(row, "member_transition_count", 0)
    with pytest.raises(StrictContractError):
        row.to_dict()

    term = ExactQuotientCoordinateTerm.from_dict(wire["rows"][2]["terms"][0])
    object.__setattr__(term, "target_block_index", False)
    with pytest.raises(StrictContractError):
        term.to_dict()


def test_e0_public_surface_has_no_later_tier_tokens() -> None:
    new_names = {
        "ExactQuotientCoordinateTerm",
        "ExactQuotientTransferRow",
        "ExactQuotientCoordinateGenerator",
        "build_exact_quotient_coordinate_generator",
    }
    assert new_names <= set(qg.__all__)
    assert new_names <= set(odlrq_package.__all__)
    forbidden = {
        "FiberEnvelope", "positive_majorant", "rate", "probability",
        "fiber_law", "nominal", "learner_score", "alpha",
    }
    tokens = set()
    for name in new_names:
        public = getattr(qg, name)
        tokens.add(name)
        tokens.update(str(value) for value in getattr(public, "__annotations__", {}).values())
        if callable(public) and hasattr(public, "__code__"):
            tokens.update(public.__code__.co_names)
        if isinstance(public, type):
            for member in public.__dict__.values():
                function = getattr(member, "__func__", member)
                if callable(function) and hasattr(function, "__code__"):
                    tokens.update(function.__code__.co_names)

    def collect_wire_tokens(value) -> None:
        if type(value) is dict:
            for key, member in value.items():
                tokens.add(key)
                collect_wire_tokens(member)
        elif type(value) is list:
            for member in value:
                collect_wire_tokens(member)
        elif type(value) is str:
            tokens.add(value)

    collect_wire_tokens(_e0_read_only_generator("g0-move")[2])
    assert forbidden.isdisjoint(tokens)


def test_read_only_bundle_cache_is_quarantined_from_mutation_tests() -> None:
    first = _read_only_bundle()
    second = _read_only_bundle()
    assert all(left is right for left, right in zip(first, second, strict=True))
    mutation_tests = (
        test_witness_and_certified_serializers_reject_low_level_mutation,
        test_nested_candidate_mutation_cannot_cross_the_tier_firewall,
        test_capability_seals_and_retained_witness_sources_are_rechecked,
        test_independent_evidence_serializer_rejects_low_level_mutation,
    )
    for test in mutation_tests:
        assert "_bundle" in test.__code__.co_names
        assert "_read_only_bundle" not in test.__code__.co_names
