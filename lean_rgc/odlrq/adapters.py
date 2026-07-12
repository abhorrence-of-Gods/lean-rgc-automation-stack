"""Fail-closed admission for finite synthetic ODLRQ development systems.

This module intentionally exposes no adapter from Lean/U05 transitions or from
the depth-bounded ``ReachableChart``.  Milestone 1 admits only source-embedded,
complete synthetic tables and preserves that evidence scope in the result.
"""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
from typing import Any

from lean_rgc.lean.kernel_state_identity import canonical_json_bytes

from .contracts import (
    EXACT_ADMISSION_CHECKS,
    MAX_SYNTHETIC_ACTIONS,
    MAX_SYNTHETIC_TOTALIZED_STATES,
    MAX_SYNTHETIC_TRANSITION_ROWS,
    NOT_APPLICABLE,
    SYNTHETIC_CLOSURE_POLICY,
    SYNTHETIC_EVIDENCE_SCOPE,
    SYNTHETIC_FRAME_EXTRACTOR_VERSION,
    SYNTHETIC_FRAME_GRANULARITY,
    SYNTHETIC_FRAME_NORMALIZATION,
    SYNTHETIC_FIXTURE_ID_PREFIX,
    AdmittedExactFiniteSnapshot,
    ExactAdmissionReport,
    ExactKernelTransitionCore,
    ObservationFrameId,
    ReachableDomainId,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticEvidenceProfile,
    SyntheticExpansionStatus,
    SyntheticFiniteSnapshot,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    SyntheticTransitionSemanticsId,
    TotalizedStatus,
    U05ProbeTransition,
)
from .reachable_chart import ReachableChart


def _sha256_upper(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def _preflight_lengths(
    seed_state_ids: Sequence[Any],
    states: Sequence[Any],
    actions: Sequence[Any],
    transitions: Sequence[Any],
) -> tuple[int, int, int, int]:
    """Reject resource caps using only ``len`` before reading a payload."""

    n_states = len(states)
    if n_states > MAX_SYNTHETIC_TOTALIZED_STATES:
        raise StrictContractError("totalized state cap is violated before payload access")
    n_seeds = len(seed_state_ids)
    if (
        n_seeds < 1
        or n_seeds > n_states
        or n_seeds > MAX_SYNTHETIC_TOTALIZED_STATES
    ):
        raise StrictContractError("seed-count cap is violated before payload access")
    n_actions = len(actions)
    if n_actions > MAX_SYNTHETIC_ACTIONS:
        raise StrictContractError("synthetic action cap is violated before payload access")
    n_rows = len(transitions)
    if (
        n_rows > MAX_SYNTHETIC_TRANSITION_ROWS
        or n_states * n_actions > MAX_SYNTHETIC_TRANSITION_ROWS
    ):
        raise StrictContractError(
            "synthetic transition-row cap is violated before payload access"
        )
    return n_states, n_seeds, n_actions, n_rows


def _bounded_tuple(
    values: Sequence[Any], *, declared: int, limit: int, label: str
) -> tuple[Any, ...]:
    """Materialize at most ``limit + 1`` items and distrust polymorphic len."""

    result: list[Any] = []
    iterator = iter(values)
    for _ in range(limit + 1):
        try:
            result.append(next(iterator))
        except StopIteration:
            break
    if len(result) > limit:
        raise StrictContractError(f"{label} exceeds its cap during materialization")
    if len(result) != declared:
        raise StrictContractError(f"{label} declared and materialized lengths disagree")
    return tuple(result)


def _require_exact_members(
    values: Sequence[Any], expected_type: type[Any], label: str
) -> None:
    if not all(type(value) is expected_type for value in values):
        raise StrictContractError(f"{label} contain a non-exact member type")


def _sorted_payloads(values: Sequence[Any]) -> list[dict[str, Any]]:
    payloads = [value.to_dict() for value in values]
    return sorted(payloads, key=canonical_json_bytes)


def _action_alphabet_digest(actions: Sequence[SyntheticAction]) -> str:
    return _sha256_upper({"actions": _sorted_payloads(actions)})


def make_synthetic_observation_frame_id(
    *,
    environment_digest: str,
    response_vocabulary_id: ResponseVocabularyId,
) -> ObservationFrameId:
    return ObservationFrameId(
        environment_content_digest=environment_digest,
        source_lane=SYNTHETIC_EVIDENCE_SCOPE,
        granularity=SYNTHETIC_FRAME_GRANULARITY,
        coordinate_schema_digest=response_vocabulary_id.coordinate_schema_digest,
        normalization_id=SYNTHETIC_FRAME_NORMALIZATION,
        extractor_version=SYNTHETIC_FRAME_EXTRACTOR_VERSION,
    )


def observation_frame_digest(frame: ObservationFrameId) -> str:
    return _sha256_upper(frame.to_dict())


def make_synthetic_transition_semantics_id(
    *,
    actions: Sequence[SyntheticAction],
    response_vocabulary_id: ResponseVocabularyId,
) -> SyntheticTransitionSemanticsId:
    declared = len(actions)
    if declared > MAX_SYNTHETIC_ACTIONS:
        raise StrictContractError("synthetic action cap is violated before payload access")
    action_tuple = _bounded_tuple(
        actions,
        declared=declared,
        limit=MAX_SYNTHETIC_ACTIONS,
        label="synthetic actions",
    )
    _require_exact_members(action_tuple, SyntheticAction, "synthetic actions")
    return SyntheticTransitionSemanticsId.from_bindings(
        _action_alphabet_digest(action_tuple),
        response_vocabulary_id.vocabulary_digest,
    )


def _domain_material(
    *,
    seed_state_ids: Sequence[str],
    states: Sequence[SyntheticTotalizedState],
    actions: Sequence[SyntheticAction],
    transitions: Sequence[SyntheticTransitionRow],
) -> dict[str, Any]:
    return {
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "closure_policy": SYNTHETIC_CLOSURE_POLICY,
        "seed_state_ids": sorted(seed_state_ids),
        "states": _sorted_payloads(states),
        "actions": _sorted_payloads(actions),
        "transitions": _sorted_payloads(transitions),
    }


def make_reachable_domain_id(
    *,
    environment_digest: str,
    observation_frame_id: ObservationFrameId,
    transition_semantics_id: SyntheticTransitionSemanticsId,
    seed_state_ids: Sequence[str],
    states: Sequence[SyntheticTotalizedState],
    actions: Sequence[SyntheticAction],
    transitions: Sequence[SyntheticTransitionRow],
    frame_digest: str | None = None,
    transition_semantics_digest: str | None = None,
) -> ReachableDomainId:
    """Create the content-bound ID used by one synthetic candidate."""

    n_states, n_seeds, n_actions, n_rows = _preflight_lengths(
        seed_state_ids, states, actions, transitions
    )
    seed_tuple = _bounded_tuple(
        seed_state_ids,
        declared=n_seeds,
        limit=MAX_SYNTHETIC_TOTALIZED_STATES,
        label="seed_state_ids",
    )
    state_tuple = _bounded_tuple(
        states,
        declared=n_states,
        limit=MAX_SYNTHETIC_TOTALIZED_STATES,
        label="synthetic states",
    )
    action_tuple = _bounded_tuple(
        actions,
        declared=n_actions,
        limit=MAX_SYNTHETIC_ACTIONS,
        label="synthetic actions",
    )
    transition_tuple = _bounded_tuple(
        transitions,
        declared=n_rows,
        limit=MAX_SYNTHETIC_TRANSITION_ROWS,
        label="synthetic transitions",
    )
    if not all(type(seed) is str and seed for seed in seed_tuple):
        raise StrictContractError("seed_state_ids contain a non-exact string")
    _require_exact_members(state_tuple, SyntheticTotalizedState, "synthetic states")
    _require_exact_members(action_tuple, SyntheticAction, "synthetic actions")
    _require_exact_members(
        transition_tuple, SyntheticTransitionRow, "synthetic transitions"
    )
    seeds = sorted(seed_tuple)
    action_payloads = _sorted_payloads(action_tuple)
    derived_frame_digest = observation_frame_digest(observation_frame_id)
    derived_semantics_digest = transition_semantics_id.semantics_digest
    if frame_digest is not None and frame_digest.upper() != derived_frame_digest:
        raise StrictContractError("caller frame digest is not the derived typed frame")
    if (
        transition_semantics_digest is not None
        and transition_semantics_digest.upper() != derived_semantics_digest
    ):
        raise StrictContractError(
            "caller semantics digest is not the derived typed semantics"
        )
    return ReachableDomainId(
        environment_digest=environment_digest,
        frame_digest=derived_frame_digest,
        transition_semantics_digest=derived_semantics_digest,
        seed_set_digest=_sha256_upper({"seed_state_ids": seeds}),
        action_alphabet_digest=_sha256_upper({"actions": action_payloads}),
        domain_payload_digest=_sha256_upper(
            _domain_material(
                seed_state_ids=seed_tuple,
                states=state_tuple,
                actions=action_tuple,
                transitions=transition_tuple,
            )
        ),
    )


def build_synthetic_finite_snapshot(
    *,
    environment_digest: str,
    coordinate_names: Sequence[str],
    seed_state_ids: Sequence[str],
    states: Sequence[SyntheticTotalizedState],
    actions: Sequence[SyntheticAction],
    transitions: Sequence[SyntheticTransitionRow],
    frame_digest: str | None = None,
    transition_semantics_digest: str | None = None,
) -> SyntheticFiniteSnapshot:
    """Normalize a source-embedded synthetic table without declaring it exact."""

    n_states, n_seeds, n_actions, n_rows = _preflight_lengths(
        seed_state_ids, states, actions, transitions
    )
    # Coordinate vocabulary is an exact tuple-only boundary.  Reject strings
    # and polymorphic/infinite Sequences before any table payload is read.
    vocabulary = ResponseVocabularyId.from_coordinate_names(coordinate_names)
    seed_tuple = _bounded_tuple(
        seed_state_ids,
        declared=n_seeds,
        limit=MAX_SYNTHETIC_TOTALIZED_STATES,
        label="seed_state_ids",
    )
    state_tuple = _bounded_tuple(
        states,
        declared=n_states,
        limit=MAX_SYNTHETIC_TOTALIZED_STATES,
        label="synthetic states",
    )
    action_tuple = _bounded_tuple(
        actions,
        declared=n_actions,
        limit=MAX_SYNTHETIC_ACTIONS,
        label="synthetic actions",
    )
    transition_tuple = _bounded_tuple(
        transitions,
        declared=n_rows,
        limit=MAX_SYNTHETIC_TRANSITION_ROWS,
        label="synthetic transitions",
    )
    if not all(type(seed) is str and seed for seed in seed_tuple):
        raise StrictContractError("seed_state_ids contain a non-exact string")
    _require_exact_members(state_tuple, SyntheticTotalizedState, "synthetic states")
    _require_exact_members(action_tuple, SyntheticAction, "synthetic actions")
    _require_exact_members(
        transition_tuple, SyntheticTransitionRow, "synthetic transitions"
    )
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment_digest,
        response_vocabulary_id=vocabulary,
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=action_tuple,
        response_vocabulary_id=vocabulary,
    )
    domain_id = make_reachable_domain_id(
        environment_digest=environment_digest,
        observation_frame_id=frame,
        transition_semantics_id=semantics,
        seed_state_ids=seed_tuple,
        states=state_tuple,
        actions=action_tuple,
        transitions=transition_tuple,
        frame_digest=frame_digest,
        transition_semantics_digest=transition_semantics_digest,
    )
    return SyntheticFiniteSnapshot(
        domain_id=domain_id,
        response_vocabulary_id=vocabulary,
        observation_frame_id=frame,
        transition_semantics_id=semantics,
        evidence_profile=SyntheticEvidenceProfile(),
        seed_state_ids=seed_tuple,
        states=state_tuple,
        actions=action_tuple,
        transitions=transition_tuple,
    )


def validate_synthetic_finite_snapshot(
    snapshot: SyntheticFiniteSnapshot,
) -> ExactAdmissionReport:
    """Purely validate one snapshot and return its uniquely derived report."""

    if type(snapshot) is not SyntheticFiniteSnapshot:
        raise StrictContractError("pure admission validation requires a strict snapshot")

    def _validate() -> ExactAdmissionReport:

        if snapshot.evidence_profile != SyntheticEvidenceProfile():
            raise StrictContractError("synthetic evidence profile is not frozen")
        if (
            snapshot.domain_id.evidence_scope != SYNTHETIC_EVIDENCE_SCOPE
            or snapshot.response_vocabulary_id.evidence_scope
            != SYNTHETIC_EVIDENCE_SCOPE
        ):
            raise StrictContractError("snapshot evidence scopes disagree")
        frame = snapshot.observation_frame_id
        if (
            frame.environment_content_digest
            != snapshot.domain_id.environment_digest
            or frame.source_lane != SYNTHETIC_EVIDENCE_SCOPE
            or frame.granularity != SYNTHETIC_FRAME_GRANULARITY
            or frame.normalization_id != SYNTHETIC_FRAME_NORMALIZATION
            or frame.extractor_version != SYNTHETIC_FRAME_EXTRACTOR_VERSION
            or frame.coordinate_schema_digest
            != snapshot.response_vocabulary_id.coordinate_schema_digest
            or observation_frame_digest(frame) != snapshot.domain_id.frame_digest
        ):
            raise StrictContractError(
                "typed observation frame is not bound to the response schema"
            )
        expected_semantics = make_synthetic_transition_semantics_id(
            actions=snapshot.actions,
            response_vocabulary_id=snapshot.response_vocabulary_id,
        )
        if (
            snapshot.transition_semantics_id != expected_semantics
            or expected_semantics.semantics_digest
            != snapshot.domain_id.transition_semantics_digest
        ):
            raise StrictContractError(
                "typed transition semantics are not bound to actions/vocabulary"
            )

        n_states = len(snapshot.states)
        n_actions = len(snapshot.actions)
        n_rows = len(snapshot.transitions)
        if n_states < 3 or n_states > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("totalized state cap or minimum is violated")
        if n_actions < 1 or n_actions > MAX_SYNTHETIC_ACTIONS:
            raise StrictContractError("synthetic action cap or minimum is violated")
        expected_rows = n_states * n_actions
        if (
            expected_rows > MAX_SYNTHETIC_TRANSITION_ROWS
            or n_rows > MAX_SYNTHETIC_TRANSITION_ROWS
        ):
            raise StrictContractError("synthetic transition-row cap is violated")

        state_ids = [state.state_id for state in snapshot.states]
        state_payloads = [state.payload.canonical_json for state in snapshot.states]
        if len(state_ids) != len(set(state_ids)):
            raise StrictContractError("synthetic state IDs contain duplicates")
        if any(
            not state_id.startswith(SYNTHETIC_FIXTURE_ID_PREFIX)
            for state_id in state_ids
        ):
            raise StrictContractError("synthetic state ID is outside the frozen prefix")
        if len(state_payloads) != len(set(state_payloads)):
            raise StrictContractError("synthetic state payloads contain duplicates")
        action_ids = [action.action_id for action in snapshot.actions]
        action_payloads = [action.payload.canonical_json for action in snapshot.actions]
        if len(action_ids) != len(set(action_ids)):
            raise StrictContractError("synthetic action IDs contain duplicates")
        if any(
            not action_id.startswith(SYNTHETIC_FIXTURE_ID_PREFIX)
            for action_id in action_ids
        ):
            raise StrictContractError("synthetic action ID is outside the frozen prefix")
        if len(action_payloads) != len(set(action_payloads)):
            raise StrictContractError("synthetic action payloads contain duplicates")

        closed = [
            state
            for state in snapshot.states
            if state.totalized_kind is TotalizedStatus.CLOSED
        ]
        sinks = [
            state
            for state in snapshot.states
            if state.totalized_kind is TotalizedStatus.SINK
        ]
        concrete = [
            state
            for state in snapshot.states
            if state.totalized_kind is TotalizedStatus.OPEN
        ]
        if len(closed) != 1 or len(sinks) != 1 or not concrete:
            raise StrictContractError(
                "snapshot requires concrete states and exactly one CLOSED and SINK"
            )
        if len(concrete) > MAX_SYNTHETIC_TOTALIZED_STATES - 2:
            raise StrictContractError("synthetic concrete-state cap is violated")

        seeds = snapshot.seed_state_ids
        if not seeds or len(seeds) != len(set(seeds)):
            raise StrictContractError("seed membership must be nonempty and unique")
        concrete_ids = {state.state_id for state in concrete}
        if not set(seeds) <= concrete_ids:
            raise StrictContractError("every seed must name a concrete domain state")

        coordinate_count = snapshot.response_vocabulary_id.coordinate_count
        for state in snapshot.states:
            if len(state.response_coordinates) != coordinate_count:
                raise StrictContractError("response coordinate arity mismatch")
            if state.frame_digest != snapshot.domain_id.frame_digest:
                raise StrictContractError("mixed observation frames are forbidden")
            if (
                state.expansion_status is not SyntheticExpansionStatus.SEALED
                or not state.boundary_complete
                or state.truncated
                or state.live_handle != NOT_APPLICABLE
            ):
                raise StrictContractError(
                    "queued/live/boundary/truncated state cannot enter exact admission"
                )

        state_id_set = set(state_ids)
        action_id_set = set(action_ids)
        row_keys: list[tuple[str, str]] = []
        row_map: dict[tuple[str, str], SyntheticTransitionRow] = {}
        for row in snapshot.transitions:
            if row.censor != NOT_APPLICABLE:
                raise StrictContractError("a censored row cannot enter exact admission")
            if (
                row.transition_semantics_digest
                != snapshot.domain_id.transition_semantics_digest
            ):
                raise StrictContractError("mixed transition semantics are forbidden")
            if row.source_state_id not in state_id_set:
                raise StrictContractError("transition source is outside the domain")
            if row.action_id not in action_id_set:
                raise StrictContractError("transition action is outside the alphabet")
            if row.target_state_id not in state_id_set:
                raise StrictContractError("transition successor is outside the domain")
            key = (row.source_state_id, row.action_id)
            row_keys.append(key)
            row_map[key] = row
        if len(row_keys) != len(set(row_keys)):
            raise StrictContractError("transition table contains duplicate rows")
        expected_keys = {
            (state_id, action_id)
            for state_id in state_ids
            for action_id in action_ids
        }
        if n_rows != expected_rows or set(row_keys) != expected_keys:
            raise StrictContractError("transition table is not total")

        for terminal in (*closed, *sinks):
            for action_id in action_ids:
                if row_map[(terminal.state_id, action_id)].target_state_id != terminal.state_id:
                    raise StrictContractError("CLOSED and SINK must be absorbing")

        kind_by_id = {
            state.state_id: state.totalized_kind for state in snapshot.states
        }
        reachable_open = set(seeds)
        frontier = list(seeds)
        while frontier:
            source_id = frontier.pop()
            for action_id in action_ids:
                target_id = row_map[(source_id, action_id)].target_state_id
                if (
                    kind_by_id[target_id] is TotalizedStatus.OPEN
                    and target_id not in reachable_open
                ):
                    reachable_open.add(target_id)
                    frontier.append(target_id)
        if reachable_open != concrete_ids:
            raise StrictContractError("not every OPEN state is reachable from a seed")

        expected_domain = make_reachable_domain_id(
            environment_digest=snapshot.domain_id.environment_digest,
            observation_frame_id=snapshot.observation_frame_id,
            transition_semantics_id=snapshot.transition_semantics_id,
            seed_state_ids=snapshot.seed_state_ids,
            states=snapshot.states,
            actions=snapshot.actions,
            transitions=snapshot.transitions,
        )
        if expected_domain != snapshot.domain_id:
            raise StrictContractError("reachable domain digests do not match the table")

        # This also proves that every serialized member uses its canonical order
        # and reduced exact-rational form.
        if SyntheticFiniteSnapshot.from_dict(snapshot.to_dict()) != snapshot:
            raise StrictContractError("snapshot failed its strict canonical roundtrip")

        snapshot_sha256 = hashlib.sha256(
            canonical_json_bytes(snapshot.to_dict())
        ).hexdigest().upper()
        report = ExactAdmissionReport(
            snapshot_sha256=snapshot_sha256,
            totalized_state_count=n_states,
            concrete_state_count=len(concrete),
            action_count=n_actions,
            transition_row_count=n_rows,
            checks=EXACT_ADMISSION_CHECKS,
        )
        return report

    return _validate()


class ExactAdmissionCompletionGate:
    """The only public constructor for an admitted exact finite table."""

    @classmethod
    def admit(cls, source: object) -> AdmittedExactFiniteSnapshot:
        if isinstance(
            source,
            (ExactKernelTransitionCore, U05ProbeTransition, ReachableChart),
        ):
            raise StrictContractError(
                f"{type(source).__name__} cannot be promoted into synthetic exact evidence"
            )
        if type(source) is not SyntheticFiniteSnapshot:
            raise StrictContractError(
                "exact admission accepts only a SyntheticFiniteSnapshot candidate"
            )
        report = validate_synthetic_finite_snapshot(source)
        return AdmittedExactFiniteSnapshot._from_gate(source, report)


def admit_synthetic_finite_snapshot(
    source: object,
) -> AdmittedExactFiniteSnapshot:
    return ExactAdmissionCompletionGate.admit(source)


__all__ = [
    "ExactAdmissionCompletionGate",
    "admit_synthetic_finite_snapshot",
    "build_synthetic_finite_snapshot",
    "make_reachable_domain_id",
    "make_synthetic_observation_frame_id",
    "make_synthetic_transition_semantics_id",
    "observation_frame_digest",
    "validate_synthetic_finite_snapshot",
]
