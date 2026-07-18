from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import hashlib

import pytest

import lean_rgc.odlrq as odlrq
from lean_rgc.odlrq import locality_cegar as locality_core
from lean_rgc.odlrq import (
    ActionSymbol,
    BeforeLocalRegion,
    CanonicalPayload,
    ExactRational,
    LocalityResultDisposition,
    PipelineEvidenceTier,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TargetSelector,
    TotalizedStatus,
    admit_synthetic_finite_snapshot,
    apply_exact_counterexample_split,
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    derive_exact_query_cost,
    extract_before_locality_features,
    find_exact_local_counterexample,
    make_before_local_region,
    make_exact_local_response_observation,
    make_locality_query,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
    propose_nominal_partition,
    rank_locality_queries,
    refine_exact_partition,
    run_synthetic_locality_cegar,
    verify_exact_partition,
    verify_locality_cegar_report,
)


_ENVIRONMENT = "A1" * 32
_OTHER_ENVIRONMENT = "B2" * 32
_COORDINATES = ("observable_delta", "return_memory")
_FAMILY_ID = "unit_family"
_INSTANCE_ID = "unit_instance"
_LEFT = "region_left"
_RIGHT = "region_right"
_ACTION_NAMES = ("a", "b", "ghost_store", "reveal", "close")
_QUERY_ROWS = (
    ("q_a", ("a",), ()),
    ("q_b", ("b",), ()),
    ("q_ghost_store", ("ghost_store",), ()),
    ("q_reveal", ("reveal",), ()),
    ("q_ghost_store_reveal", ("ghost_store", "reveal"), ()),
    ("q_a_b", ("a", "b"), ()),
    ("q_b_a", ("b", "a"), ()),
    ("q_close", ("close",), ()),
)
_RESPONSES = {
    "q_a": ((0, 0), (2, 0)),
    "q_b": ((0, 0), (2, 0)),
    "q_ghost_store": ((0, 0), (0, 0)),
    "q_reveal": ((0, 0), (0, 0)),
    "q_ghost_store_reveal": ((0, 0), (0, 4)),
    "q_a_b": ((0, 0), (1, 1)),
    "q_b_a": ((0, 0), (3, 0)),
    "q_close": ((0, 0), (0, 0)),
}
_L0_PUBLIC = (
    "BeforeLocalRegion",
    "LocalityFeatureVector",
    "LocalityQuery",
    "ExactLocalResponseObservation",
    "ExactLocalCounterexample",
    "ProposedNominalPartition",
    "LocalityQueryScore",
    "LocalityCEGARReport",
    "LocalityResultDisposition",
    "make_before_local_region",
    "extract_before_locality_features",
    "make_locality_query",
    "derive_exact_query_cost",
    "make_exact_local_response_observation",
    "find_exact_local_counterexample",
    "propose_nominal_partition",
    "rank_locality_queries",
    "apply_exact_counterexample_split",
    "run_synthetic_locality_cegar",
    "verify_locality_cegar_report",
)


def _action_symbol(name: str, selector: TargetSelector) -> ActionSymbol:
    return ActionSymbol(
        action_id=f"unit_cpu_survivor_u15_l0_{name}",
        opcode="constructor",
        target_selector=selector,
        premise_slot_rule_id=None,
        premise_selector_ordinal=None,
        expected_normalized_type_pattern=None,
        global_constant=None,
        opaque_hyperedge_source=None,
        opaque_hyperedge_digest=None,
        cap_profile_id="u05-hb-20000-cache-bypass-v1",
    )


def _action_catalog() -> tuple[SyntheticAction, ...]:
    symbols = tuple(
        _action_symbol(
            name,
            TargetSelector.FIRST if index % 2 == 0 else TargetSelector.LAST,
        )
        for index, name in enumerate(_ACTION_NAMES)
    )
    return tuple(
        SyntheticAction(symbol.action_id, CanonicalPayload.from_value(symbol.to_dict()))
        for symbol in symbols
    )


def _region(region_id: str, frame, semantics, *, relabel: bool = False):
    if relabel:
        nodes = (("root_x", "goal"), ("bridge_x", "shared_mvar"), ("leaf_x", "hypothesis"))
        edges = (("root_x", "bridge_x", "dependency"), ("bridge_x", "leaf_x", "dependency"))
        ports = (("outside_x", "shared_goal", "bridge_x"),)
        separators = ("bridge_x",)
        target = "root_x"
    else:
        nodes = (("root", "goal"), ("bridge", "shared_mvar"), ("leaf", "hypothesis"))
        edges = (("root", "bridge", "dependency"), ("bridge", "leaf", "dependency"))
        ports = (("outside", "shared_goal", "bridge"),)
        separators = ("bridge",)
        target = "root"
    return make_before_local_region(
        region_id=region_id,
        observation_frame_id=frame,
        transition_semantics_id=semantics,
        nodes=nodes,
        edges=edges,
        boundary_ports=ports,
        separator_node_ids=separators,
        target_node_id=target,
    )


def _terminal_state_id(region_id: str, query_id: str) -> str:
    return f"unit_cpu_survivor_u15_l0_{region_id}_{query_id}"


def _source_state_id(region_id: str, query_id: str) -> str:
    return f"unit_cpu_survivor_u15_l0_{region_id}_{query_id}_source"


def _intermediate_state_id(region_id: str, query_id: str, position: int) -> str:
    return f"unit_cpu_survivor_u15_l0_{region_id}_{query_id}_{position}"


@lru_cache(maxsize=1)
def _core_case():
    vocabulary = ResponseVocabularyId.from_coordinate_names(_COORDINATES)
    actions = _action_catalog()
    frame = make_synthetic_observation_frame_id(
        environment_digest=_ENVIRONMENT,
        response_vocabulary_id=vocabulary,
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=actions,
        response_vocabulary_id=vocabulary,
    )
    queries = tuple(
        make_locality_query(
            query_id=query_id,
            observation_frame_id=frame,
            transition_semantics_id=semantics,
            response_vocabulary_id=vocabulary,
            action_catalog=actions,
            action_word_ids=tuple(
                f"unit_cpu_survivor_u15_l0_{name}" for name in action_names
            ),
            closing_context_id="observe_two_coordinate_response",
            closing_action_ids=tuple(
                f"unit_cpu_survivor_u15_l0_{name}" for name in closing_names
            ),
            response_coordinate_ids=_COORDINATES,
        )
        for query_id, action_names, closing_names in _QUERY_ROWS
    )
    regions = (
        _region(_LEFT, frame, semantics),
        _region(_RIGHT, frame, semantics, relabel=True),
    )
    frame_digest = observation_frame_digest(frame)
    states = []
    transitions = []
    seed_state_ids = []
    closed_id = "unit_cpu_survivor_u15_l0_closed"
    sink_id = "unit_cpu_survivor_u15_l0_sink"
    for region_index, region_id in enumerate((_LEFT, _RIGHT)):
        for query in queries:
            raw_response = _RESPONSES[query.query_id][region_index]
            source_id = _source_state_id(region_id, query.query_id)
            terminal_id = _terminal_state_id(region_id, query.query_id)
            seed_state_ids.append(source_id)
            states.append(
                SyntheticTotalizedState(
                    state_id=source_id,
                    payload=CanonicalPayload.from_value(
                        {
                            "instance_id": _INSTANCE_ID,
                            "kind": "u15_l0_source",
                            "query_id": query.query_id,
                            "query_sha256": hashlib.sha256(
                                canonical_contract_bytes(query.to_dict())
                            ).hexdigest().upper(),
                            "region_id": region_id,
                        }
                    ),
                    totalized_kind=TotalizedStatus.OPEN,
                    response_coordinates=(ExactRational(0), ExactRational(0)),
                    frame_digest=frame_digest,
                )
            )
            complete_word = query.action_word + query.closing_action_word
            intermediate_ids = tuple(
                _intermediate_state_id(region_id, query.query_id, position)
                for position in range(1, len(complete_word))
            )
            for position, intermediate_id in enumerate(intermediate_ids, start=1):
                states.append(
                    SyntheticTotalizedState(
                        state_id=intermediate_id,
                        payload=CanonicalPayload.from_value(
                            {
                                "instance_id": _INSTANCE_ID,
                                "kind": "u15_l0_intermediate",
                                "query_id": query.query_id,
                                "region_id": region_id,
                                "word_position_decimal": str(position),
                            }
                        ),
                        totalized_kind=TotalizedStatus.OPEN,
                        response_coordinates=(ExactRational(0), ExactRational(0)),
                        frame_digest=frame_digest,
                    )
                )
            states.append(
                SyntheticTotalizedState(
                    state_id=terminal_id,
                    payload=CanonicalPayload.from_value(
                        {
                            "instance_id": _INSTANCE_ID,
                            "kind": "u15_l0_terminal",
                            "query_id": query.query_id,
                            "query_sha256": hashlib.sha256(
                                canonical_contract_bytes(query.to_dict())
                            ).hexdigest().upper(),
                            "region_id": region_id,
                        }
                    ),
                    totalized_kind=TotalizedStatus.OPEN,
                    response_coordinates=tuple(
                        ExactRational(value) for value in raw_response
                    ),
                    frame_digest=frame_digest,
                )
            )
            chain = (source_id, *intermediate_ids)
            for position, current_id in enumerate(chain):
                expected_action_id = complete_word[position].action_id
                target_id = (
                    intermediate_ids[position]
                    if position < len(intermediate_ids)
                    else terminal_id
                )
                for action in actions:
                    transitions.append(
                        SyntheticTransitionRow(
                            source_state_id=current_id,
                            action_id=action.action_id,
                            target_state_id=(
                                target_id
                                if action.action_id == expected_action_id
                                else sink_id
                            ),
                            transition_semantics_digest=semantics.semantics_digest,
                        )
                    )
            for action in actions:
                transitions.append(
                    SyntheticTransitionRow(
                        source_state_id=terminal_id,
                        action_id=action.action_id,
                        target_state_id=closed_id,
                        transition_semantics_digest=semantics.semantics_digest,
                    )
                )
    states.extend(
        (
            SyntheticTotalizedState(
                state_id=closed_id,
                payload=CanonicalPayload.from_value(
                    {"kind": "u15_l0_totalized", "status": "closed"}
                ),
                totalized_kind=TotalizedStatus.CLOSED,
                response_coordinates=(ExactRational(0), ExactRational(0)),
                frame_digest=frame_digest,
            ),
            SyntheticTotalizedState(
                state_id=sink_id,
                payload=CanonicalPayload.from_value(
                    {"kind": "u15_l0_totalized", "status": "sink"}
                ),
                totalized_kind=TotalizedStatus.SINK,
                response_coordinates=(ExactRational(0), ExactRational(0)),
                frame_digest=frame_digest,
            ),
        )
    )
    for absorber_id in (closed_id, sink_id):
        for action in actions:
            transitions.append(
                SyntheticTransitionRow(
                    source_state_id=absorber_id,
                    action_id=action.action_id,
                    target_state_id=absorber_id,
                    transition_semantics_digest=semantics.semantics_digest,
                )
            )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=_ENVIRONMENT,
        coordinate_names=_COORDINATES,
        seed_state_ids=tuple(seed_state_ids),
        states=tuple(states),
        actions=actions,
        transitions=tuple(transitions),
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    certificate = refine_exact_partition(admitted)
    verified = verify_exact_partition(admitted, certificate)
    observations = locality_core._make_exact_local_response_observation_batch(
        tuple(
            (
                _FAMILY_ID,
                _INSTANCE_ID,
                region_id,
                query,
                tuple(
                    ExactRational(value)
                    for value in _RESPONSES[query.query_id][region_index]
                ),
                _terminal_state_id(region_id, query.query_id),
            )
            for region_index, region_id in enumerate((_LEFT, _RIGHT))
            for query in queries
        ),
        verified_partition=verified,
    )
    partition = propose_nominal_partition(
        regions, action_catalog_digest=semantics.action_alphabet_digest
    )
    return {
        "vocabulary": vocabulary,
        "actions": actions,
        "frame": frame,
        "semantics": semantics,
        "queries": queries,
        "regions": regions,
        "snapshot": snapshot,
        "admitted": admitted,
        "certificate": certificate,
        "verified": verified,
        "observations": observations,
        "partition": partition,
    }


def _query(case, query_id: str):
    return next(query for query in case["queries"] if query.query_id == query_id)


def _observation(case, region_id: str, query_id: str):
    return next(
        row
        for row in case["observations"]
        if row.region_id == region_id and row.query.query_id == query_id
    )


class _OversizedRegions:
    def __init__(self, first):
        self.first = first
        self.reads = 0

    def __len__(self):
        return 17

    def __getitem__(self, index):
        self.reads += 1
        if index == 0:
            return self.first
        raise AssertionError("oversized carrier was materialized")


class _TooManyNodes:
    def __len__(self):
        return 13

    def __iter__(self):
        raise AssertionError("over-cap node payload was materialized")


class _UnderreportedSequence:
    def __init__(self, first, second):
        self.first = first
        self.second = second
        self.reads = 0

    def __len__(self):
        return 1

    def __iter__(self):
        self.reads += 1
        yield self.first
        self.reads += 1
        yield self.second
        raise AssertionError("lying sequence was read beyond cap plus one")


def test_l0_before_region_features_are_relabel_invariant_and_exact():
    case = _core_case()
    left, right = case["regions"]
    left_features = extract_before_locality_features(left)
    right_features = extract_before_locality_features(right)
    assert left_features == right_features
    assert left.to_dict() != right.to_dict()
    assert left_features.node_kind_count_rows == (
        ("goal", 1),
        ("hypothesis", 1),
        ("shared_mvar", 1),
    )
    assert left_features.shared_mvar_degree_multiset == (2,)
    assert case["partition"].blocks == ((_LEFT, _RIGHT),)


def test_l0_path_cycle_articulation_and_treewidth_features_are_known():
    case = _core_case()
    region = make_before_local_region(
        region_id="lollipop",
        observation_frame_id=case["frame"],
        transition_semantics_id=case["semantics"],
        nodes=(("t", "goal"), ("c", "shared_mvar"), ("u", "hypothesis"), ("v", "hypothesis")),
        edges=(("t", "c", "dependency"), ("c", "u", "dependency"), ("c", "v", "dependency"), ("u", "v", "dependency")),
        boundary_ports=(("boundary", "shared_goal", "c"),),
        separator_node_ids=("c",),
        target_node_id="t",
    )
    features = extract_before_locality_features(region)
    assert features.articulation_count == 1
    assert features.cycle_rank == 1
    assert features.exact_treewidth == 2
    assert features.radius == 2
    assert features.component_size_profile_after_separator_deletion == (1, 2)


def test_l0_after_audit_carrier_and_future_features_are_rejected():
    region = _core_case()["regions"][0]
    with_after_field = region.to_dict()
    with_after_field["assigned_mvars_after"] = []
    with pytest.raises(StrictContractError, match="missing, duplicate, or unknown"):
        BeforeLocalRegion.from_dict(with_after_field)
    mutated_node = region.to_dict()
    mutated_node["nodes"][0]["after_goal_hash"] = "00" * 32
    with pytest.raises(StrictContractError, match="node row"):
        BeforeLocalRegion.from_dict(mutated_node)


def test_l0_query_binds_complete_ordered_action_symbols_and_cost():
    case = _core_case()
    query = _query(case, "q_ghost_store_reveal")
    assert tuple(symbol.action_id for symbol in query.action_word) == (
        "unit_cpu_survivor_u15_l0_ghost_store",
        "unit_cpu_survivor_u15_l0_reveal",
    )
    assert query.action_catalog_digest == case["semantics"].action_alphabet_digest
    assert tuple(key.coordinate_key for key in query.response_keys) == _COORDINATES
    assert derive_exact_query_cost(query) == 8
    with pytest.raises(StrictContractError, match="complete action catalogue"):
        make_locality_query(
            query_id="q_incomplete",
            observation_frame_id=case["frame"],
            transition_semantics_id=case["semantics"],
            response_vocabulary_id=case["vocabulary"],
            action_catalog=case["actions"][:-1],
            action_word_ids=(case["actions"][0].action_id,),
            closing_context_id="observe_two_coordinate_response",
            closing_action_ids=(),
            response_coordinate_ids=_COORDINATES,
        )


def test_l0_cross_frame_query_and_response_splicing_reject():
    case = _core_case()
    other_frame = make_synthetic_observation_frame_id(
        environment_digest=_OTHER_ENVIRONMENT,
        response_vocabulary_id=case["vocabulary"],
    )
    foreign_query = make_locality_query(
        query_id="q_a",
        observation_frame_id=other_frame,
        transition_semantics_id=case["semantics"],
        response_vocabulary_id=case["vocabulary"],
        action_catalog=case["actions"],
        action_word_ids=(case["actions"][0].action_id,),
        closing_context_id="observe_two_coordinate_response",
        closing_action_ids=(),
        response_coordinate_ids=_COORDINATES,
    )
    with pytest.raises(StrictContractError, match="spliced"):
        make_exact_local_response_observation(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=foreign_query,
            response_vector=(ExactRational(0), ExactRational(0)),
            verified_partition=case["verified"],
            terminal_state_id=_terminal_state_id(_LEFT, "q_a"),
        )
    with pytest.raises(StrictContractError, match="splicing"):
        find_exact_local_counterexample(
            case["partition"],
            _observation(case, _LEFT, "q_a"),
            _observation(case, _RIGHT, "q_b"),
        )

    q_a = _query(case, "q_a")
    foreign_action_wire = q_a.to_dict()
    foreign_action_wire["action_word"][0]["action_id"] = "forbidden_foreign_action"
    with pytest.raises(StrictContractError, match="action words"):
        odlrq.LocalityQuery.from_dict(foreign_action_wire)

    different_word_wire = q_a.to_dict()
    different_word_wire["action_word"] = [
        _query(case, "q_b").action_word[0].to_dict()
    ]
    different_word = odlrq.LocalityQuery.from_dict(different_word_wire)
    assert different_word.query_id == q_a.query_id and different_word != q_a
    with pytest.raises(StrictContractError, match="payload binding"):
        make_exact_local_response_observation(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=different_word,
            response_vector=(ExactRational(0), ExactRational(0)),
            verified_partition=case["verified"],
            terminal_state_id=_terminal_state_id(_LEFT, "q_a"),
        )

    boundary_wire = _query(case, "q_ghost_store_reveal").to_dict()
    boundary_wire["action_word"] = boundary_wire["action_word"][:1]
    boundary_wire["closing_action_word"] = [
        _query(case, "q_ghost_store_reveal").action_word[1].to_dict()
    ]
    boundary_splice = odlrq.LocalityQuery.from_dict(boundary_wire)
    with pytest.raises(StrictContractError, match="payload binding"):
        make_exact_local_response_observation(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=boundary_splice,
            response_vector=(ExactRational(0), ExactRational(0)),
            verified_partition=case["verified"],
            terminal_state_id=_terminal_state_id(_LEFT, "q_ghost_store_reveal"),
        )

    spliced_grid = list(case["observations"])
    spliced_grid[0] = replace(spliced_grid[0], query=different_word)
    with pytest.raises(StrictContractError, match="complete catalogue row"):
        rank_locality_queries(
            case["partition"], case["queries"], tuple(spliced_grid)
        )

    independently_verified = verify_exact_partition(
        case["admitted"], case["certificate"]
    )
    mixed_source_grid = list(case["observations"])
    mixed_source_grid[0] = replace(
        mixed_source_grid[0], _verified_partition=independently_verified
    )
    with pytest.raises(StrictContractError, match="one verifier capability"):
        rank_locality_queries(
            case["partition"], case["queries"], tuple(mixed_source_grid)
        )

    source = locality_core._bind_verified_observation_source(case["verified"])
    assert locality_core._reverify_observation_batch(
        case["observations"], source=source
    ) == case["observations"]
    with pytest.raises(TypeError):
        source.state_by_id["forged"] = case["snapshot"].states[0]
    with pytest.raises(StrictContractError, match="private binder"):
        replace(source, _gate_token=object())
    with pytest.raises(StrictContractError, match="private issuance"):
        replace(source, snapshot_sha256="C" * 64, certificate_sha256="D" * 64)
    with pytest.raises(StrictContractError, match="issuance identity"):
        replace(source._issuance, verified_partition=independently_verified)
    locality_core._VERIFIED_OBSERVATION_SOURCE_MEMO[:] = [
        (case["verified"], object())
    ]
    with pytest.raises(StrictContractError, match="memo is corrupted"):
        make_exact_local_response_observation(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=q_a,
            response_vector=(ExactRational(0), ExactRational(0)),
            verified_partition=case["verified"],
            terminal_state_id=_terminal_state_id(_LEFT, q_a.query_id),
        )
    locality_core._clear_verified_observation_source_memo()
    foreign_source = locality_core._bind_verified_observation_source(
        independently_verified
    )
    with pytest.raises(StrictContractError, match="crossed its verifier capability"):
        locality_core._reverify_observation_batch(
            (case["observations"][0],), source=foreign_source
        )
    with pytest.raises(StrictContractError, match="private verified binding"):
        locality_core._make_exact_local_response_observation_core(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=q_a,
            response_vector=(ExactRational(0), ExactRational(0)),
            terminal_state_id=_terminal_state_id(_LEFT, q_a.query_id),
            source=object(),
            query_sha256=hashlib.sha256(
                canonical_contract_bytes(q_a.to_dict())
            ).hexdigest().upper(),
        )


def test_l0_exact_counterexample_adds_must_separate_and_splits_monotonically():
    case = _core_case()
    partition = case["partition"]
    witness = find_exact_local_counterexample(
        partition,
        _observation(case, _LEFT, "q_a"),
        _observation(case, _RIGHT, "q_a"),
    )
    assert witness is not None
    assert witness.first_differing_coordinate == 0
    refined = apply_exact_counterexample_split(partition, witness)
    assert len(refined.blocks) == len(partition.blocks) + 1
    assert refined.generation == partition.generation + 1
    assert refined.must_not_link_edges == ((_LEFT, _RIGHT),)
    assert set(refined.region_ids) == set(partition.region_ids)
    with pytest.raises(StrictContractError, match="no longer|stale"):
        apply_exact_counterexample_split(refined, witness)


def test_l0_equality_and_no_counterexample_never_merge_or_promote():
    case = _core_case()
    equal_witness = find_exact_local_counterexample(
        case["partition"],
        _observation(case, _LEFT, "q_close"),
        _observation(case, _RIGHT, "q_close"),
    )
    assert equal_witness is None
    split_witness = find_exact_local_counterexample(
        case["partition"],
        _observation(case, _LEFT, "q_a"),
        _observation(case, _RIGHT, "q_a"),
    )
    assert split_witness is not None
    refined = apply_exact_counterexample_split(case["partition"], split_witness)
    assert find_exact_local_counterexample(
        refined,
        _observation(case, _LEFT, "q_a"),
        _observation(case, _RIGHT, "q_a"),
    ) is None
    assert refined.evidence_tier is PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
    assert refined.hard_eligible is False


def test_l0_proposal_and_report_remain_nominal_and_hard_ineligible():
    case = _core_case()
    report = run_synthetic_locality_cegar(
        case["regions"],
        case["queries"],
        case["observations"],
        action_catalog_digest=case["semantics"].action_alphabet_digest,
    )
    locality_core._VERIFIED_OBSERVATION_SOURCE_MEMO[:] = [
        (case["verified"], object())
    ]
    verified_report = verify_locality_cegar_report(
        report,
        case["regions"],
        case["queries"],
        case["observations"],
        action_catalog_digest=case["semantics"].action_alphabet_digest,
    )
    assert verified_report == report
    assert report.evidence_tier is PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
    assert report.hard_eligible is False
    assert report.initial_partition is not None and report.final_partition is not None
    assert all(
        score.evidence_tier is PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
        and score.hard_eligible is False
        for score in report.selected_scores
    )


def test_l0_ghost_noop_is_retained_by_delayed_return_witness():
    case = _core_case()
    query = _query(case, "q_ghost_store_reveal")
    left = _observation(case, _LEFT, query.query_id)
    right = _observation(case, _RIGHT, query.query_id)
    assert left.response_vector[0] == right.response_vector[0] == ExactRational(0)
    assert left.response_vector[1] != right.response_vector[1]
    assert query.action_word[0].action_id.endswith("ghost_store")
    witness = find_exact_local_counterexample(case["partition"], left, right)
    assert witness is not None
    assert witness.first_differing_coordinate_key.coordinate_key == "return_memory"


def test_l0_ghost_omission_changes_catalog_digest_and_rejects():
    case = _core_case()
    without_ghost = tuple(
        action for action in case["actions"] if not action.action_id.endswith("ghost_store")
    )
    changed = make_synthetic_transition_semantics_id(
        actions=without_ghost,
        response_vocabulary_id=case["vocabulary"],
    )
    assert changed.action_alphabet_digest != case["semantics"].action_alphabet_digest
    with pytest.raises(StrictContractError, match="complete action catalogue"):
        make_locality_query(
            query_id="q_ghost_omitted",
            observation_frame_id=case["frame"],
            transition_semantics_id=case["semantics"],
            response_vocabulary_id=case["vocabulary"],
            action_catalog=without_ghost,
            action_word_ids=(without_ghost[0].action_id,),
            closing_context_id="observe_two_coordinate_response",
            closing_action_ids=(),
            response_coordinate_ids=_COORDINATES,
        )


def test_l0_full_conditional_covariance_reduction_is_exact_fraction():
    case = _core_case()
    scores = rank_locality_queries(
        case["partition"], case["queries"], case["observations"]
    )
    score = next(row for row in scores if row.query.query_id == "q_a")
    assert score.trace_before == ExactRational(35, 4)
    assert score.trace_after == ExactRational(0)
    assert score.gain == ExactRational(35, 4)
    assert score.score == ExactRational(35, 24)
    assert score.covariance_before_sha256 != score.covariance_after_sha256


def test_l0_query_cost_reverses_ranking_and_tie_break_is_canonical():
    case = _core_case()
    scores = rank_locality_queries(
        case["partition"], case["queries"], case["observations"]
    )
    by_query = {row.query.query_id: row for row in scores}
    assert by_query["q_a"].gain == by_query["q_ghost_store_reveal"].gain
    assert by_query["q_a"].derived_cost < by_query["q_ghost_store_reveal"].derived_cost
    short_score = by_query["q_a"].score
    long_score = by_query["q_ghost_store_reveal"].score
    assert short_score.numerator * long_score.denominator > (
        long_score.numerator * short_score.denominator
    )
    tied = tuple(
        row.canonical_candidate_json
        for row in scores
        if row.score == by_query["q_a"].score
    )
    assert tied == tuple(sorted(tied, key=lambda value: value.encode("utf-8")))
    assert len(tied) == 2


def test_l0_caps_apply_before_materialization_and_abstain():
    case = _core_case()
    oversized = _OversizedRegions(case["regions"][0])
    report = run_synthetic_locality_cegar(
        oversized,
        case["queries"],
        case["observations"],
        action_catalog_digest=case["semantics"].action_alphabet_digest,
    )
    assert report.terminal_status == "ABSTAIN"
    assert report.terminal_reason == "PRE_MATERIALIZATION_CAP_EXCEEDED"
    assert report.initial_partition is None and report.final_partition is None
    assert oversized.reads == 1

    lying_queries = _UnderreportedSequence(
        case["queries"][0], case["queries"][1]
    )
    with pytest.raises(StrictContractError, match="declared length"):
        run_synthetic_locality_cegar(
            case["regions"],
            lying_queries,
            case["observations"],
            action_catalog_digest=case["semantics"].action_alphabet_digest,
        )
    assert lying_queries.reads == 2

    lying_observations = _UnderreportedSequence(
        case["observations"][0], case["observations"][1]
    )
    with pytest.raises(StrictContractError, match="declared length"):
        run_synthetic_locality_cegar(
            case["regions"],
            case["queries"],
            lying_observations,
            action_catalog_digest=case["semantics"].action_alphabet_digest,
        )
    assert lying_observations.reads == 2

    with pytest.raises(StrictContractError, match="pre-materialization cap"):
        make_before_local_region(
            region_id="over_cap",
            observation_frame_id=case["frame"],
            transition_semantics_id=case["semantics"],
            nodes=_TooManyNodes(),
            edges=(),
            boundary_ports=(),
            separator_node_ids=(),
            target_node_id="unread",
        )


def test_l0_exact_partition_requires_independent_verifier():
    case = _core_case()
    query = _query(case, "q_a")
    with pytest.raises(StrictContractError, match="VerifiedExactPartition"):
        make_exact_local_response_observation(
            family_id=_FAMILY_ID,
            instance_id=_INSTANCE_ID,
            region_id=_LEFT,
            query=query,
            response_vector=(ExactRational(0), ExactRational(0)),
            verified_partition=case["certificate"],
            terminal_state_id=_terminal_state_id(_LEFT, query.query_id),
        )
    independently_verified = verify_exact_partition(
        case["admitted"], case["certificate"]
    )
    observation = make_exact_local_response_observation(
        family_id=_FAMILY_ID,
        instance_id=_INSTANCE_ID,
        region_id=_LEFT,
        query=query,
        response_vector=(ExactRational(0), ExactRational(0)),
        verified_partition=independently_verified,
        terminal_state_id=_terminal_state_id(_LEFT, query.query_id),
    )
    assert observation == _observation(case, _LEFT, query.query_id)


def test_l0_wire_caps_mutations_and_duplicate_keys_fail_closed():
    region = _core_case()["regions"][0]
    canonical = canonical_contract_bytes(region.to_dict())
    assert BeforeLocalRegion.from_json_bytes(canonical) == region
    duplicate = canonical.replace(
        b'"schema_version":',
        b'"schema_version":"wrong","schema_version":',
        1,
    )
    with pytest.raises(StrictContractError, match="duplicate"):
        BeforeLocalRegion.from_json_bytes(duplicate)
    with pytest.raises(StrictContractError, match="canonical"):
        BeforeLocalRegion.from_json_bytes(canonical + b" ")
    with pytest.raises(StrictContractError, match="byte cap"):
        BeforeLocalRegion.from_json_bytes(b"{" + b" " * (1 << 20) + b"}")
    changed = region.to_dict()
    changed["future_feature"] = {"after": True}
    with pytest.raises(StrictContractError, match="unknown fields"):
        BeforeLocalRegion.from_json_bytes(canonical_contract_bytes(changed))


def test_l0_public_surface_has_no_merge_hard_promotion_or_forbidden_import():
    exported = tuple(odlrq.__all__)
    assert set(_L0_PUBLIC).issubset(exported)
    assert len(exported) == len(set(exported))
    assert not any(
        ("locality" in name.lower() or "cegar" in name.lower())
        and ("merge" in name.lower() or "promote" in name.lower())
        for name in exported
    )
    partition_fields = odlrq.ProposedNominalPartition.__dataclass_fields__
    assert partition_fields["hard_eligible"].default is False
    assert partition_fields["evidence_tier"].default is (
        PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
    )
    assert set(LocalityResultDisposition) == {
        LocalityResultDisposition.L0_SYNTHETIC_CEGAR_GAIN_OBSERVED,
        LocalityResultDisposition.L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN,
        LocalityResultDisposition.L0_SYNTHETIC_CEGAR_DEGRADED,
        LocalityResultDisposition.L0_PREREQUISITE_BLOCKED,
        LocalityResultDisposition.L0_EXECUTION_FAILED,
    }
