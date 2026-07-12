"""Bounded componentwise-window diagnostics over admitted synthetic tables.

The lane is deliberately development-only.  It consumes one revalidated
``AdmittedExactFiniteSnapshot`` plus explicit synthetic task/seed bindings,
uses the frozen ``D_START=4`` and ``CONTINUATION_HORIZON=4``, and emits a
source-rederived report.  No scalar envelope or hard Lean claim is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, Sequence

from .contracts import (
    NOT_APPLICABLE,
    SYNTHETIC_EVIDENCE_SCOPE,
    SYNTHETIC_FIXTURE_ID_PREFIX,
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactRational,
    StrictContractError,
    SyntheticAction,
    SyntheticFiniteSnapshot,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    canonical_contract_bytes,
)


D_START = 4
CONTINUATION_HORIZON = 4
DEBT_COORDINATE_NAMES = (
    "open_goal_count",
    "open_unassigned_mvar_count",
    "pending_typeclass_count",
    "carrier_atom_count",
    "expression_node_count",
)

MAX_START_OCCURRENCES = 100_000
MAX_CONTINUATION_PAIRS = 250_000
MAX_TRANSITION_WORK_UNITS = 2_000_000
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_SIGNED_64 = (1 << 63) - 1

COMPONENTWISE_DIAGNOSTIC_TIER = "bounded_componentwise_synthetic_development"
COMPONENTWISE_QUALIFICATION = "CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED"

TASK_SEED_SCHEMA = "lean-rgc-odlrq-componentwise-task-seed-v1"
REPORT_SCHEMA = "lean-rgc-odlrq-componentwise-window-report-v1"
COORDINATE_API_SCHEMA = "lean-rgc-odlrq-componentwise-coordinate-api-v1"

_REPORT_SEAL = object()


def _object(value: Any, fields: tuple[str, ...], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(value) != len(fields) or any(name not in value for name in fields):
        raise StrictContractError(f"{where} field set mismatch")
    if any(type(name) is not str or name not in fields for name in value):
        raise StrictContractError(f"{where} has an unknown field")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an exact array")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} is not strict UTF-8") from exc
    return value


def _integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > MAX_SIGNED_64:
        raise StrictContractError(
            f"{where} must be a signed-64 integer >= {minimum}"
        )
    return value


def _digest(value: Any, where: str) -> str:
    result = _string(value, where)
    if len(result) != 64 or any(ch not in "0123456789ABCDEF" for ch in result):
        raise StrictContractError(f"{where} must be an uppercase SHA-256 digest")
    return result


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _blocked(message: str) -> StrictContractError:
    return StrictContractError(f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {message}")


def _checked_add(left: int, right: int, where: str) -> int:
    _integer(left, f"{where} left")
    _integer(right, f"{where} right")
    if right > MAX_SIGNED_64 - left:
        raise _blocked(f"{where} exceeds signed-64 arithmetic")
    return left + right


def _checked_mul(left: int, right: int, where: str) -> int:
    _integer(left, f"{where} left")
    _integer(right, f"{where} right")
    if left and right > MAX_SIGNED_64 // left:
        raise _blocked(f"{where} exceeds signed-64 arithmetic")
    return left * right


def _power_sum(base: int, first: int, last: int, where: str) -> int:
    _integer(base, f"{where} base", minimum=1)
    total = 0
    power = 1
    for exponent in range(last + 1):
        if exponent >= first:
            total = _checked_add(total, power, where)
        if exponent != last:
            power = _checked_mul(power, base, where)
    return total


@dataclass(frozen=True)
class ComponentwiseTaskSeed:
    """An explicit synthetic task identifier bound to one admitted seed state."""

    task_id: str
    state_id: str

    def __post_init__(self) -> None:
        if type(self) is not ComponentwiseTaskSeed:
            raise StrictContractError("componentwise task-seed subclasses are forbidden")
        for name in ("task_id", "state_id"):
            value = _string(getattr(self, name), f"task seed {name}")
            if not value.startswith(SYNTHETIC_FIXTURE_ID_PREFIX):
                raise StrictContractError(
                    f"task seed {name} is outside the synthetic fixture namespace"
                )

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": TASK_SEED_SCHEMA,
            "task_id": self.task_id,
            "state_id": self.state_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ComponentwiseTaskSeed":
        if cls is not ComponentwiseTaskSeed:
            raise StrictContractError("polymorphic task-seed parsing is forbidden")
        obj = _object(value, ("schema_version", "task_id", "state_id"), "task seed")
        if _string(obj["schema_version"], "task seed schema") != TASK_SEED_SCHEMA:
            raise StrictContractError("task seed schema mismatch")
        result = cls(
            _string(obj["task_id"], "task_id"),
            _string(obj["state_id"], "state_id"),
        )
        if result.to_dict() != obj:
            raise StrictContractError("task seed is not canonical")
        return result


@dataclass(frozen=True)
class _RawPreflight:
    task_count: int
    action_count: int
    raw_start_occurrences: int
    raw_continuation_pairs: int
    transition_work_units: int

    def to_dict(self) -> dict[str, int]:
        return {
            "task_count": self.task_count,
            "action_count": self.action_count,
            "raw_start_occurrences": self.raw_start_occurrences,
            "raw_continuation_pairs": self.raw_continuation_pairs,
            "transition_work_units": self.transition_work_units,
        }


def _raw_preflight(
    admitted: AdmittedExactFiniteSnapshot,
    task_seeds: tuple[ComponentwiseTaskSeed, ...],
) -> _RawPreflight:
    """Check only exact container types/counts before reading semantic payloads."""

    if type(admitted) is not AdmittedExactFiniteSnapshot:
        raise StrictContractError(
            "componentwise analysis requires an exact AdmittedExactFiniteSnapshot"
        )
    if type(task_seeds) is not tuple:
        raise StrictContractError("componentwise task seeds must be an exact tuple")
    n_tasks = len(task_seeds)
    if n_tasks < 1:
        raise StrictContractError("componentwise task seeds must be nonempty")
    if type(admitted.snapshot) is not SyntheticFiniteSnapshot:
        raise StrictContractError("admitted componentwise snapshot is not exact")
    actions = admitted.snapshot.actions
    if type(actions) is not tuple:
        raise StrictContractError("admitted action container is not an exact tuple")
    action_count = len(actions)
    if action_count < 1:
        raise StrictContractError("componentwise action alphabet must be nonempty")

    start_words = _power_sum(action_count, 0, D_START, "start-word upper bound")
    continuation_words = _power_sum(
        action_count, 1, CONTINUATION_HORIZON, "continuation-word upper bound"
    )
    start_count = _checked_mul(n_tasks, start_words, "S start occurrences")
    pair_count = _checked_mul(
        start_count, continuation_words, "P continuation pairs"
    )
    work = _checked_mul(
        pair_count, CONTINUATION_HORIZON + 1, "P*(K+1) transition work"
    )
    if start_count > MAX_START_OCCURRENCES:
        raise _blocked(f"S={start_count} exceeds {MAX_START_OCCURRENCES}")
    if pair_count > MAX_CONTINUATION_PAIRS:
        raise _blocked(f"P={pair_count} exceeds {MAX_CONTINUATION_PAIRS}")
    if work > MAX_TRANSITION_WORK_UNITS:
        raise _blocked(
            f"P*(K+1)={work} exceeds {MAX_TRANSITION_WORK_UNITS}"
        )
    return _RawPreflight(n_tasks, action_count, start_count, pair_count, work)


class UniversalStatus(str, Enum):
    ALL_CONTRACTS = "all_contracts"
    HAS_NONCONTRACTING = "has_noncontracting"
    NOT_APPLICABLE_EMPTY = "not_applicable_empty"


@dataclass(frozen=True)
class ComponentwiseWindowReport:
    """Factory-only report rederived from retained external authorities."""

    _admitted: AdmittedExactFiniteSnapshot = field(repr=False)
    _task_seeds: tuple[ComponentwiseTaskSeed, ...] = field(repr=False)
    _snapshot_seal: str = field(repr=False)
    _seed_seal: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not ComponentwiseWindowReport or self._construction_seal is not _REPORT_SEAL:
            raise StrictContractError("componentwise report requires its analysis gate")
        if type(self._admitted) is not AdmittedExactFiniteSnapshot:
            raise StrictContractError("componentwise report source is not exact")
        if type(self._task_seeds) is not tuple:
            raise StrictContractError("componentwise report seed authority is not exact")
        _digest(self._snapshot_seal, "componentwise snapshot seal")
        _digest(self._seed_seal, "componentwise task-seed seal")

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _REPORT_SEAL:
            raise StrictContractError("componentwise report construction seal changed")
        wire = _derive_report(self._admitted, self._task_seeds)
        if wire["snapshot_sha256"] != self._snapshot_seal:
            raise StrictContractError("componentwise retained snapshot changed")
        if wire["task_seed_set_sha256"] != self._seed_seal:
            raise StrictContractError("componentwise retained task seeds changed")
        return wire

    @property
    def coordinate_names(self) -> tuple[str, ...]:
        return DEBT_COORDINATE_NAMES

    @property
    def canonical_report_bytes(self) -> int:
        return _integer(
            self.to_dict()["canonical_report_bytes"], "canonical report bytes"
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        admitted: AdmittedExactFiniteSnapshot,
        task_seeds: tuple[ComponentwiseTaskSeed, ...],
    ) -> "ComponentwiseWindowReport":
        if cls is not ComponentwiseWindowReport:
            raise StrictContractError("polymorphic componentwise report parsing is forbidden")
        expected = analyze_componentwise_window(admitted, task_seeds)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError(
                "componentwise report wire does not match external authorities"
            )
        return expected


def _derive_report(
    admitted: AdmittedExactFiniteSnapshot,
    task_seeds: tuple[ComponentwiseTaskSeed, ...],
) -> dict[str, Any]:
    """Full derivation; filled incrementally below the preflight boundary."""

    preflight = _raw_preflight(admitted, task_seeds)
    return _derive_report_after_preflight(admitted, task_seeds, preflight)


@dataclass(frozen=True)
class _SourceContext:
    admitted: AdmittedExactFiniteSnapshot
    task_seeds: tuple[ComponentwiseTaskSeed, ...]
    states: tuple[SyntheticTotalizedState, ...]
    actions: tuple[SyntheticAction, ...]
    state_index: dict[str, int]
    action_index: dict[str, int]
    transition_target: dict[tuple[str, str], str]
    coordinates: dict[str, tuple[int, ...]]
    admitted_wire_bytes: int
    report_upper_bound: int


def _payload_key(value: CanonicalPayload) -> bytes:
    if type(value) is not CanonicalPayload:
        raise StrictContractError("semantic payload key is not exact")
    try:
        return value.canonical_json.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError("semantic payload is not strict UTF-8") from exc


def _strict_coordinate_vector(
    state: SyntheticTotalizedState,
) -> tuple[int, ...]:
    """Recover the frozen five debt *counts* from the generic rational carrier.

    The lane amendment says "exact five coordinates" by reference to the
    upper-plan section 10 debt API: open goals, open unassigned metavariables,
    pending typeclasses, carrier atoms, and expression nodes are all counts.
    ``ExactRational`` is the shared snapshot storage type, not a licence to
    widen this particular diagnostic to fractional or negative debt.
    """

    values = state.response_coordinates
    if type(values) is not tuple or len(values) != len(DEBT_COORDINATE_NAMES):
        raise StrictContractError(
            "componentwise state must have exactly five response coordinates"
        )
    result: list[int] = []
    for index in range(len(DEBT_COORDINATE_NAMES)):
        value = values[index]
        if type(value) is not ExactRational:
            raise StrictContractError("componentwise coordinate is not exact rational")
        restored = ExactRational.from_dict(ExactRational.to_dict(value))
        if restored != value:
            raise StrictContractError("componentwise coordinate source changed")
        if value.denominator != 1 or value.numerator < 0:
            raise StrictContractError(
                "componentwise debt coordinates must be nonnegative exact integers"
            )
        result.append(value.numerator)
    return tuple(result)


def _conservative_report_upper_bound(
    *,
    preflight: _RawPreflight,
    input_wire_bytes: int,
    state_count: int,
    coordinate_decimal_digits: int,
) -> int:
    """Bound the final compact-index wire before any word is materialized.

    The row constants dominate every fixed schema key, punctuation byte, bool,
    null, and signed-64 count in the corresponding object.  Variable debt
    coordinates use the maximum decimal width revalidated from the source.
    Identifiers and payload hashes occur only in dictionaries/root bindings and
    are charged by twelve complete copies of the admitted+seed authority wire.
    """

    index_digits = 19
    count_digits = 19
    # ExactRational count wires use quoted decimal numerators.  For the fixed
    # v1 schema and denominator ``1``, canonical size is exactly 86 bytes plus
    # the nonnegative numerator width.
    rational_wire_bytes = 86 + coordinate_decimal_digits
    vector_bytes = 2 + len(DEBT_COORDINATE_NAMES) * rational_wire_bytes + (
        len(DEBT_COORDINATE_NAMES) - 1
    )
    word_bytes = 2 + CONTINUATION_HORIZON * index_digits + (
        CONTINUATION_HORIZON - 1
    )
    occurrence_row = 512 + word_bytes + 3 * index_digits
    # A continuation object with four empty vector arrays and signed-64-max
    # compact indices is 395 bytes.  Replacing each two-byte ``[]`` by the
    # bounded vector gives this exact conservative row formula.
    continuation_row = 400 + 4 * (vector_bytes - 2)
    state_summary_row = 768 + 2 * (vector_bytes - 2) + 12 * count_digits
    task_population_row = 3072 + 2 * vector_bytes + 40 * count_digits
    dictionary_and_root = _checked_mul(
        input_wire_bytes, 12, "report dictionary/root upper bound"
    )
    total = _checked_add(65_536, dictionary_and_root, "report upper bound")
    for count, row_size, label in (
        (preflight.raw_start_occurrences, occurrence_row, "occurrence report rows"),
        (
            preflight.raw_continuation_pairs,
            continuation_row,
            "continuation report rows",
        ),
        (preflight.raw_start_occurrences, state_summary_row, "state summaries"),
        (preflight.task_count, task_population_row, "task populations"),
        (
            _checked_mul(
                state_count,
                CONTINUATION_HORIZON + 2,
                "CanClose state references",
            ),
            index_digits + 2,
            "CanClose wire",
        ),
    ):
        total = _checked_add(
            total,
            _checked_mul(count, row_size, label),
            "report upper bound",
        )
    return total


def _validate_sources(
    admitted: AdmittedExactFiniteSnapshot,
    task_seeds: tuple[ComponentwiseTaskSeed, ...],
    preflight: _RawPreflight,
) -> _SourceContext:
    """Revalidate authorities and preflight report size before word creation."""

    try:
        admitted_wire = AdmittedExactFiniteSnapshot.to_dict(admitted)
        restored = AdmittedExactFiniteSnapshot.from_dict(admitted_wire)
    except (AttributeError, TypeError, ValueError) as exc:
        raise StrictContractError("componentwise admitted source is malformed") from exc
    admitted_bytes = canonical_contract_bytes(admitted_wire)
    if canonical_contract_bytes(restored.to_dict()) != admitted_bytes:
        raise StrictContractError("componentwise admitted source is not canonical")

    if not all(type(seed) is ComponentwiseTaskSeed for seed in task_seeds):
        raise StrictContractError("componentwise task seed tuple has a wrong member")
    parsed_seeds: list[ComponentwiseTaskSeed] = []
    for seed in task_seeds:
        parsed = ComponentwiseTaskSeed.from_dict(seed.to_dict())
        if parsed != seed:
            raise StrictContractError("componentwise task seed source changed")
        parsed_seeds.append(parsed)
    if len({seed.task_id for seed in parsed_seeds}) != len(parsed_seeds):
        raise StrictContractError("componentwise task IDs must be unique")

    snapshot = restored.snapshot
    vocabulary = snapshot.response_vocabulary_id
    if vocabulary.coordinate_names != DEBT_COORDINATE_NAMES:
        raise StrictContractError(
            "componentwise diagnostic requires the exact frozen five-coordinate API"
        )
    if snapshot.evidence_profile.evidence_scope != SYNTHETIC_EVIDENCE_SCOPE:
        raise StrictContractError("componentwise evidence scope changed")
    for field_name in ("target_binding", "delta", "replay", "cap", "m3"):
        if getattr(snapshot.evidence_profile, field_name) != NOT_APPLICABLE:
            raise StrictContractError(
                "componentwise synthetic oracle fields must be NOT_APPLICABLE"
            )
    if snapshot.evidence_profile.locality_claim is not False:
        raise StrictContractError("componentwise synthetic source claims locality")

    seed_ids = set(snapshot.seed_state_ids)
    for seed in parsed_seeds:
        if seed.state_id not in seed_ids:
            raise StrictContractError(
                "componentwise task seed does not name an admitted snapshot seed"
            )

    states = tuple(
        sorted(
            snapshot.states,
            key=lambda state: (
                _payload_key(state.payload),
                state.state_id.encode("utf-8", errors="strict"),
            ),
        )
    )
    actions = tuple(
        sorted(
            snapshot.actions,
            key=lambda action: (
                _payload_key(action.payload),
                action.action_id.encode("utf-8", errors="strict"),
            ),
        )
    )
    if len(actions) != preflight.action_count:
        raise StrictContractError("componentwise action count changed after preflight")
    state_index = {state.state_id: index for index, state in enumerate(states)}
    action_index = {action.action_id: index for index, action in enumerate(actions)}
    if len(state_index) != len(states) or len(action_index) != len(actions):
        raise StrictContractError("componentwise semantic dictionaries contain aliases")

    coordinates: dict[str, tuple[int, ...]] = {}
    max_decimal_digits = 1
    for state in states:
        vector = _strict_coordinate_vector(state)
        coordinates[state.state_id] = vector
        for coordinate in vector:
            max_decimal_digits = max(max_decimal_digits, len(str(coordinate)))

    transition_target: dict[tuple[str, str], str] = {}
    for row in snapshot.transitions:
        if type(row) is not SyntheticTransitionRow or row.censor != NOT_APPLICABLE:
            raise StrictContractError(
                "componentwise transition source is censored or non-exact"
            )
        key = (row.source_state_id, row.action_id)
        if key in transition_target:
            raise StrictContractError("componentwise transition table has duplicates")
        transition_target[key] = row.target_state_id
    expected_row_count = len(states) * len(actions)
    if len(transition_target) != expected_row_count:
        raise StrictContractError("componentwise transition table is not total")

    ordered_seeds = tuple(
        sorted(
            parsed_seeds,
            key=lambda seed: (
                seed.task_id.encode("utf-8", errors="strict"),
                _payload_key(states[state_index[seed.state_id]].payload),
            ),
        )
    )
    seed_bytes = canonical_contract_bytes([seed.to_dict() for seed in ordered_seeds])
    input_wire_bytes = _checked_add(
        len(admitted_bytes), len(seed_bytes), "componentwise authority wire bytes"
    )
    report_upper = _conservative_report_upper_bound(
        preflight=preflight,
        input_wire_bytes=input_wire_bytes,
        state_count=len(states),
        coordinate_decimal_digits=max_decimal_digits,
    )
    if report_upper > MAX_REPORT_BYTES:
        raise _blocked(
            f"conservative canonical report upper bound {report_upper} exceeds {MAX_REPORT_BYTES}"
        )

    return _SourceContext(
        restored,
        ordered_seeds,
        states,
        actions,
        state_index,
        action_index,
        transition_target,
        coordinates,
        input_wire_bytes,
        report_upper,
    )


@dataclass(frozen=True)
class _Continuation:
    state_index: int
    action_word: tuple[int, ...]
    endpoint_state_index: int
    prefix_state_indices: tuple[int, ...]
    start_coordinates: tuple[int, ...]
    endpoint_coordinates: tuple[int, ...]
    peak_coordinates: tuple[int, ...]
    overshoot_coordinates: tuple[int, ...]
    contracts: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_index": self.state_index,
            "action_word": list(self.action_word),
            "endpoint_state_index": self.endpoint_state_index,
            "prefix_state_indices": list(self.prefix_state_indices),
            "start_coordinates": _coordinate_vector_wire(self.start_coordinates),
            "endpoint_coordinates": _coordinate_vector_wire(
                self.endpoint_coordinates
            ),
            "peak_coordinates": _coordinate_vector_wire(self.peak_coordinates),
            "overshoot_coordinates": _coordinate_vector_wire(
                self.overshoot_coordinates
            ),
            "contracts": self.contracts,
        }


def _compute_can_close(context: _SourceContext) -> tuple[frozenset[str], ...]:
    kind = {state.state_id: state.totalized_kind for state in context.states}
    closed = frozenset(
        state.state_id
        for state in context.states
        if state.totalized_kind is TotalizedStatus.CLOSED
    )
    layers: list[frozenset[str]] = [closed]
    for _horizon in range(1, CONTINUATION_HORIZON + 1):
        previous = layers[-1]
        current = set(previous)
        for state in context.states:
            if state.totalized_kind is not TotalizedStatus.OPEN:
                continue
            for action in context.actions:
                target = context.transition_target[(state.state_id, action.action_id)]
                if target in previous and kind[target] is not TotalizedStatus.SINK:
                    current.add(state.state_id)
                    break
        layers.append(frozenset(current))
    return tuple(layers)


def _contracts(start: tuple[int, ...], endpoint: tuple[int, ...]) -> bool:
    if len(start) != len(DEBT_COORDINATE_NAMES) or len(endpoint) != len(
        DEBT_COORDINATE_NAMES
    ):
        raise StrictContractError("componentwise comparison dimension mismatch")
    nonincrease = True
    strict = False
    for index in range(len(DEBT_COORDINATE_NAMES)):
        if endpoint[index] > start[index]:
            nonincrease = False
        if endpoint[index] < start[index]:
            strict = True
    return nonincrease and strict


def _maximum_vectors(vectors: Sequence[tuple[int, ...]]) -> tuple[int, ...]:
    maximum = [0] * len(DEBT_COORDINATE_NAMES)
    for vector in vectors:
        if len(vector) != len(DEBT_COORDINATE_NAMES):
            raise StrictContractError("componentwise maximum dimension mismatch")
        for index in range(len(DEBT_COORDINATE_NAMES)):
            maximum[index] = max(maximum[index], vector[index])
    return tuple(maximum)


def _coordinate_vector_wire(values: Sequence[int]) -> list[dict[str, Any]]:
    if len(values) != len(DEBT_COORDINATE_NAMES):
        raise StrictContractError("componentwise coordinate wire dimension mismatch")
    result: list[dict[str, Any]] = []
    for index in range(len(DEBT_COORDINATE_NAMES)):
        value = values[index]
        if type(value) is not int or value < 0:
            raise StrictContractError(
                "componentwise coordinate wire requires a nonnegative integer"
            )
        # Quoted ExactRational decimals avoid silently adding signed-64 JSON
        # limits to the shared 8192-bit exact count contract.
        result.append(ExactRational(value).to_dict())
    return result


def _enumerate_open_occurrences(
    context: _SourceContext,
) -> tuple[tuple[int, tuple[int, ...], int], ...]:
    kind = {state.state_id: state.totalized_kind for state in context.states}
    occurrences: list[tuple[int, tuple[int, ...], int]] = []
    for task_index, seed in enumerate(context.task_seeds):
        frontier: list[tuple[tuple[int, ...], str]] = [((), seed.state_id)]
        for depth in range(D_START + 1):
            next_frontier: list[tuple[tuple[int, ...], str]] = []
            for word, state_id in frontier:
                if kind[state_id] is not TotalizedStatus.OPEN:
                    raise StrictContractError("terminal occurrence entered OPEN frontier")
                occurrences.append((task_index, word, context.state_index[state_id]))
                if depth == D_START:
                    continue
                for action in context.actions:
                    target = context.transition_target[(state_id, action.action_id)]
                    if kind[target] is TotalizedStatus.OPEN:
                        next_frontier.append(
                            (word + (context.action_index[action.action_id],), target)
                        )
            frontier = next_frontier
    occurrences.sort(key=lambda row: (row[0], len(row[1]), row[1], row[2]))
    return tuple(occurrences)


def _enumerate_continuations(
    context: _SourceContext,
    start_state_indices: tuple[int, ...],
    can_close: tuple[frozenset[str], ...],
) -> tuple[_Continuation, ...]:
    kind = {state.state_id: state.totalized_kind for state in context.states}
    records: list[_Continuation] = []
    for start_index in start_state_indices:
        start_state = context.states[start_index]
        if start_state.totalized_kind is not TotalizedStatus.OPEN:
            raise StrictContractError("continuation start is not OPEN")
        start = context.coordinates[start_state.state_id]
        frontier: list[
            tuple[tuple[int, ...], str, tuple[int, ...], tuple[int, ...]]
        ] = [((), start_state.state_id, (), start)]
        for depth in range(1, CONTINUATION_HORIZON + 1):
            next_frontier: list[
                tuple[tuple[int, ...], str, tuple[int, ...], tuple[int, ...]]
            ] = []
            for word, state_id, prefix_indices, peak in frontier:
                for action in context.actions:
                    target = context.transition_target[(state_id, action.action_id)]
                    if kind[target] is not TotalizedStatus.OPEN:
                        # CLOSED/SINK is never a registered OPEN-to-OPEN block
                        # and absorbing extensions cannot multiply evidence.
                        continue
                    target_index = context.state_index[target]
                    target_coordinates = context.coordinates[target]
                    new_peak = tuple(
                        max(peak[index], target_coordinates[index])
                        for index in range(len(DEBT_COORDINATE_NAMES))
                    )
                    new_word = word + (context.action_index[action.action_id],)
                    new_prefix = prefix_indices + (target_index,)
                    next_frontier.append((new_word, target, new_prefix, new_peak))
                    remaining = CONTINUATION_HORIZON - depth
                    if target not in can_close[remaining]:
                        continue
                    overshoot = tuple(
                        new_peak[index] - start[index]
                        for index in range(len(DEBT_COORDINATE_NAMES))
                    )
                    records.append(
                        _Continuation(
                            start_index,
                            new_word,
                            target_index,
                            new_prefix,
                            start,
                            target_coordinates,
                            new_peak,
                            overshoot,
                            _contracts(start, target_coordinates),
                        )
                    )
            frontier = next_frontier
    records.sort(key=lambda row: (row.state_index, len(row.action_word), row.action_word))
    return tuple(records)


def _continuation_summary(
    rows: Sequence[_Continuation],
) -> dict[str, Any]:
    contractive = [row for row in rows if row.contracts]
    if not rows:
        universal = UniversalStatus.NOT_APPLICABLE_EMPTY
    elif len(contractive) == len(rows):
        universal = UniversalStatus.ALL_CONTRACTS
    else:
        universal = UniversalStatus.HAS_NONCONTRACTING
    minimum = (
        min(len(row.action_word) for row in contractive)
        if contractive
        else CONTINUATION_HORIZON + 1
    )
    maximum_overshoot = _maximum_vectors(
        tuple(row.overshoot_coordinates for row in rows)
    )
    return {
        "continuation_count": len(rows),
        "contractive_count": len(contractive),
        "minimum_resolving_window": minimum,
        "resolved": bool(contractive),
        "existential_contracts": bool(contractive),
        "universal_status": universal.value,
        "maximum_overshoot_coordinates": _coordinate_vector_wire(
            maximum_overshoot
        ),
    }


def _population_summary(
    population_kind: str,
    state_indices: Sequence[int],
    continuations_by_state: Mapping[int, tuple[_Continuation, ...]],
) -> dict[str, Any]:
    start_count = len(state_indices)
    nonempty = 0
    registered = 0
    contractive = 0
    existential = 0
    universal = 0
    unresolved = 0
    histogram = [0] * (CONTINUATION_HORIZON + 1)
    overshoots: list[tuple[int, ...]] = []
    for state_index in state_indices:
        rows = continuations_by_state[state_index]
        summary = _continuation_summary(rows)
        count = summary["continuation_count"]
        contracting_count = summary["contractive_count"]
        registered += count
        contractive += contracting_count
        if count:
            nonempty += 1
            if summary["universal_status"] == UniversalStatus.ALL_CONTRACTS.value:
                universal += 1
        if summary["existential_contracts"]:
            existential += 1
        else:
            unresolved += 1
        minimum = summary["minimum_resolving_window"]
        if type(minimum) is not int or not 1 <= minimum <= CONTINUATION_HORIZON + 1:
            raise StrictContractError("minimum resolving window is outside frozen bins")
        histogram[minimum - 1] += 1
        overshoots.extend(row.overshoot_coordinates for row in rows)
    return {
        "population_kind": population_kind,
        "start_count": start_count,
        "nonempty_start_count": nonempty,
        "empty_start_count": start_count - nonempty,
        "registered_continuation_count": registered,
        "contractive_continuation_count": contractive,
        "existential_numerator": existential,
        "existential_denominator": start_count,
        "universal_numerator": universal,
        "universal_denominator": nonempty,
        "unresolved_start_count": unresolved,
        "minimum_resolving_window_histogram": histogram,
        "population_maximum_overshoot_coordinates": _coordinate_vector_wire(
            _maximum_vectors(tuple(overshoots))
        ),
    }


def _sized_wire(wire: dict[str, Any]) -> dict[str, Any]:
    size = 0
    for _attempt in range(8):
        wire["canonical_report_bytes"] = size
        actual = len(canonical_contract_bytes(wire))
        if actual == size:
            break
        size = actual
    else:
        raise StrictContractError("canonical report byte count did not stabilize")
    wire["canonical_report_bytes"] = size
    encoded = canonical_contract_bytes(wire)
    if len(encoded) != size:
        raise StrictContractError("canonical report byte count is inconsistent")
    if size > MAX_REPORT_BYTES:
        raise _blocked(f"canonical report bytes {size} exceed {MAX_REPORT_BYTES}")
    return wire


def _derive_report_after_preflight(
    admitted: AdmittedExactFiniteSnapshot,
    task_seeds: tuple[ComponentwiseTaskSeed, ...],
    preflight: _RawPreflight,
) -> dict[str, Any]:
    context = _validate_sources(admitted, task_seeds, preflight)
    state_kind = {state.state_id: state.totalized_kind for state in context.states}
    can_close = _compute_can_close(context)
    occurrences = _enumerate_open_occurrences(context)
    unique_state_indices = tuple(sorted({row[2] for row in occurrences}))
    continuations = _enumerate_continuations(
        context, unique_state_indices, can_close
    )
    continuation_lists: dict[int, list[_Continuation]] = {
        state_index: [] for state_index in unique_state_indices
    }
    for row in continuations:
        continuation_lists[row.state_index].append(row)
    continuations_by_state = {
        state_index: tuple(rows)
        for state_index, rows in continuation_lists.items()
    }

    occurrence_count_by_state = {state_index: 0 for state_index in unique_state_indices}
    task_sets_by_state = {state_index: set() for state_index in unique_state_indices}
    occurrences_by_task: list[list[int]] = [
        [] for _seed in context.task_seeds
    ]
    for task_index, _word, state_index in occurrences:
        occurrence_count_by_state[state_index] += 1
        task_sets_by_state[state_index].add(task_index)
        occurrences_by_task[task_index].append(state_index)
    task_count_by_state = {
        state_index: len(task_sets_by_state[state_index])
        for state_index in unique_state_indices
    }
    state_summaries: list[dict[str, Any]] = []
    for state_index in unique_state_indices:
        state = context.states[state_index]
        summary = {
            "state_index": state_index,
            "occurrence_count": occurrence_count_by_state[state_index],
            "task_count": task_count_by_state[state_index],
            "start_coordinates": _coordinate_vector_wire(
                context.coordinates[state.state_id]
            ),
        }
        summary.update(_continuation_summary(continuations_by_state[state_index]))
        state_summaries.append(summary)

    occurrence_state_indices = tuple(row[2] for row in occurrences)
    occurrence_population = _population_summary(
        "occurrence", occurrence_state_indices, continuations_by_state
    )
    unique_population = _population_summary(
        "unique_state", unique_state_indices, continuations_by_state
    )
    per_task: list[dict[str, Any]] = []
    for task_index, _seed in enumerate(context.task_seeds):
        indices = tuple(occurrences_by_task[task_index])
        occurrence_summary = _population_summary(
            "task_occurrence", indices, continuations_by_state
        )
        unique_indices = tuple(sorted(set(indices)))
        unique_summary = _population_summary(
            "task_unique_state", unique_indices, continuations_by_state
        )
        per_task.append(
            {
                "task_index": task_index,
                "occurrence_population": occurrence_summary,
                "unique_state_population": unique_summary,
            }
        )

    if occurrence_population["existential_numerator"]:
        disposition = "U05_KP2_EVENTUAL_WINDOW"
    elif occurrence_population["nonempty_start_count"]:
        disposition = "U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT"
    else:
        disposition = "U05_KP2_FRAGMENT_INCONCLUSIVE"

    task_wire = [
        {
            "task_index": index,
            "task_id": seed.task_id,
            "seed_state_index": context.state_index[seed.state_id],
        }
        for index, seed in enumerate(context.task_seeds)
    ]
    action_wire = [
        {
            "action_index": index,
            "action_id": action.action_id,
            "payload_sha256": _sha256(action.payload.to_dict()),
        }
        for index, action in enumerate(context.actions)
    ]
    state_wire = [
        {
            "state_index": index,
            "state_id": state.state_id,
            "payload_sha256": _sha256(state.payload.to_dict()),
            "totalized_kind": state.totalized_kind.value,
            "coordinates": _coordinate_vector_wire(
                context.coordinates[state.state_id]
            ),
        }
        for index, state in enumerate(context.states)
    ]
    snapshot = context.admitted.snapshot
    wire: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "diagnostic_tier": COMPONENTWISE_DIAGNOSTIC_TIER,
        "qualification": COMPONENTWISE_QUALIFICATION,
        "scientific_disposition": disposition,
        "snapshot_sha256": context.admitted.admission_report.snapshot_sha256,
        "task_seed_set_sha256": _sha256(
            [seed.to_dict() for seed in context.task_seeds]
        ),
        "source_binding": {
            "environment_digest": snapshot.domain_id.environment_digest,
            "frame_digest": snapshot.domain_id.frame_digest,
            "transition_semantics_digest": snapshot.domain_id.transition_semantics_digest,
            "domain_payload_digest": snapshot.domain_id.domain_payload_digest,
            "response_vocabulary_digest": snapshot.response_vocabulary_id.vocabulary_digest,
        },
        "coordinate_api": {
            "schema_version": COORDINATE_API_SCHEMA,
            "coordinate_names": list(DEBT_COORDINATE_NAMES),
            "vector_length": len(DEBT_COORDINATE_NAMES),
            "value_domain": "nonnegative_exact_integer",
            "wire_encoding": "exact_rational_denominator_one",
            "contraction_rule": "coordinatewise_nonincrease_and_at_least_one_strict",
            "overshoot_rule": "maximum_positive_increase_over_all_open_prefixes_from_start",
        },
        "d_start": D_START,
        "continuation_horizon": CONTINUATION_HORIZON,
        "resource_preflight": {
            **preflight.to_dict(),
            "start_occurrence_cap": MAX_START_OCCURRENCES,
            "continuation_pair_cap": MAX_CONTINUATION_PAIRS,
            "transition_work_cap": MAX_TRANSITION_WORK_UNITS,
            "report_byte_cap": MAX_REPORT_BYTES,
            "authority_wire_bytes": context.admitted_wire_bytes,
            "conservative_report_upper_bound": context.report_upper_bound,
        },
        "task_dictionary": task_wire,
        "action_dictionary": action_wire,
        "state_dictionary": state_wire,
        "can_close_layers": [
            {
                "remaining_horizon": horizon,
                "closable_open_state_indices": [
                    context.state_index[state_id]
                    for state_id in sorted(
                        (
                            state_id
                            for state_id in layer
                            if state_kind[state_id] is TotalizedStatus.OPEN
                        ),
                        key=lambda state_id: context.state_index[state_id],
                    )
                ],
            }
            for horizon, layer in enumerate(can_close)
        ],
        "registered_continuations": [row.to_dict() for row in continuations],
        "state_summaries": state_summaries,
        "occurrences": [
            {
                "task_index": task_index,
                "start_word": list(word),
                "state_index": state_index,
            }
            for task_index, word, state_index in occurrences
        ],
        "occurrence_population": occurrence_population,
        "unique_state_population": unique_population,
        "per_task_populations": per_task,
        "canonical_report_bytes": 0,
    }
    result = _sized_wire(wire)
    if result["canonical_report_bytes"] > context.report_upper_bound:
        raise StrictContractError(
            "conservative canonical report upper bound was unsound"
        )
    return result


def analyze_componentwise_window(
    admitted: AdmittedExactFiniteSnapshot,
    task_seeds: tuple[ComponentwiseTaskSeed, ...],
) -> ComponentwiseWindowReport:
    wire = _derive_report(admitted, task_seeds)
    return ComponentwiseWindowReport(
        admitted,
        task_seeds,
        wire["snapshot_sha256"],
        wire["task_seed_set_sha256"],
        _construction_seal=_REPORT_SEAL,
    )


__all__ = [
    "D_START",
    "CONTINUATION_HORIZON",
    "DEBT_COORDINATE_NAMES",
    "MAX_START_OCCURRENCES",
    "MAX_CONTINUATION_PAIRS",
    "MAX_TRANSITION_WORK_UNITS",
    "MAX_REPORT_BYTES",
    "COMPONENTWISE_DIAGNOSTIC_TIER",
    "COMPONENTWISE_QUALIFICATION",
    "UniversalStatus",
    "ComponentwiseTaskSeed",
    "ComponentwiseWindowReport",
    "analyze_componentwise_window",
]
