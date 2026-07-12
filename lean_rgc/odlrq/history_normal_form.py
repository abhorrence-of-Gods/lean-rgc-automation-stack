"""Exact generation-time history aggregation on a sealed finite domain.

This module is deliberately independent of the native Lean transport.  C1
fixtures provide a complete immutable state/action table; a later adapter may
construct the same contracts only after it has sealed and replayed that table.
Terminal behavior is cached only by kind.  Occurrence provenance is always
reconstructed from the raw query word that first enters the terminal class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
from itertools import product
import json
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Sequence
import weakref


MAX_SIGNED_64 = (1 << 63) - 1
MAX_OPEN_STATES = 1_024
MAX_ACTIONS = 12
MAX_TRANSITION_ROWS = 12_288
MAX_RAW_DEPTH3_OCCURRENCES = 15_000
MAX_RAW_DEPTH4_OCCURRENCES = 150_000
MAX_CANONICAL_DEPTH = 4
MAX_TASK_SEEDS = MAX_RAW_DEPTH4_OCCURRENCES // (MAX_CANONICAL_DEPTH + 1)
MAX_CANONICAL_CLASSES = 50_000
MAX_CONTRIBUTION_EDGES = 300_000
MAX_SIGNATURE_BYTES = 64 * 1024
MAX_TOTAL_SIGNATURE_BYTES = 8 * 1024 * 1024
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_DUPLICATE_ROW_CHECKS = 1_536
UNCONDITIONAL_FINITE_DOMAIN = "UNCONDITIONAL_FINITE_DOMAIN"
CONDITIONAL_KSTATE_MARKOV = "CONDITIONAL_KSTATE_MARKOV"
_EXACTNESS_FLOORS = frozenset(
    {UNCONDITIONAL_FINITE_DOMAIN, CONDITIONAL_KSTATE_MARKOV}
)
UNPROVED_MARKOV_STATUS = "UNPROVED_ASSUMPTION"
FINITE_DOMAIN_SCHEMA = "lean-rgc-kp3d4-finite-total-domain-v2"
HISTORY_GRAMMAR_SCHEMA = "lean-rgc-kp3d4-history-normal-form-v1"
ACTION_GRAMMAR_SCHEMA = "lean-rgc-kp3d4-action-grammar-v1"
_REGISTERED_LOOKUP_TOKEN = object()
_CANONICAL_CHART_PROVENANCE: dict[int, tuple[Any, ...]] = {}
_PREPARED_WALKER_PROVENANCE: dict[int, tuple[Any, ...]] = {}
_RAW_EQUALITY_REPORT_PROVENANCE: dict[int, tuple[Any, ...]] = {}
_FLOW_REPORT_PROVENANCE: dict[int, tuple[Any, ...]] = {}


def _canonical_chart_identity_guard(instance: Any) -> tuple[int, ...]:
    markov = instance.markov_contract
    preflight = instance.report_preflight
    return (
        id(None if markov is None else markov.frame_digest),
        id(None if markov is None else markov.transition_semantics_digest),
        id(None if markov is None else markov.action_grammar_digest),
        id(None if markov is None else markov.exactness_scope),
        id(None if markov is None else markov.proof_status),
        id(None if preflight is None else preflight.source_domain_digest),
        id(None if preflight is None else preflight.max_depth),
        id(None if preflight is None else preflight.total_signature_utf8_bytes),
        id(None if preflight is None else preflight.transition_rows),
        id(None if preflight is None else preflight.duplicate_row_checks),
        id(None if preflight is None else preflight.canonical_class_upper),
        id(None if preflight is None else preflight.contribution_edge_upper),
        id(None if preflight is None else preflight.report_byte_upper),
        id(instance.duplicate_row_checks),
        id(instance._report_preflight_seal),
    )


def _register_canonical_chart(instance: Any) -> None:
    identity = id(instance)

    def remove(reference: weakref.ReferenceType[Any], *, key: int = identity) -> None:
        retained = _CANONICAL_CHART_PROVENANCE.get(key)
        if retained is not None and retained[0] is reference:
            _CANONICAL_CHART_PROVENANCE.pop(key, None)

    reference = weakref.ref(instance, remove)
    _CANONICAL_CHART_PROVENANCE[identity] = (
        reference,
        instance.domain,
        instance.max_depth,
        instance.layers,
        instance.markov_contract,
        instance.report_preflight,
        instance.duplicate_row_checks,
        instance._report_preflight_seal,
        _canonical_chart_identity_guard(instance),
        instance._task_id_set,
        instance._action_id_set,
        instance._edge_index,
        instance._seed_class_key_map,
        instance._open_response_index,
        instance._representative_index,
    )


def _canonical_chart_provenance_entry(instance: Any) -> tuple[Any, ...] | None:
    retained = _CANONICAL_CHART_PROVENANCE.get(id(instance))
    if retained is None or retained[0]() is not instance:
        return None
    if (
        instance.domain is retained[1]
        and instance.max_depth is retained[2]
        and instance.layers is retained[3]
        and instance.markov_contract is retained[4]
        and instance.report_preflight is retained[5]
        and instance.duplicate_row_checks is retained[6]
        and instance._report_preflight_seal is retained[7]
        and _canonical_chart_identity_guard(instance) == retained[8]
        and instance._task_id_set is retained[9]
        and instance._action_id_set is retained[10]
        and instance._edge_index is retained[11]
        and instance._seed_class_key_map is retained[12]
        and instance._open_response_index is retained[13]
        and instance._representative_index is retained[14]
    ):
        return retained
    return None


def _register_prepared_walker(instance: Any) -> None:
    identity = id(instance)

    def remove(reference: weakref.ReferenceType[Any], *, key: int = identity) -> None:
        retained = _PREPARED_WALKER_PROVENANCE.get(key)
        if retained is not None and retained[0] is reference:
            _PREPARED_WALKER_PROVENANCE.pop(key, None)

    reference = weakref.ref(instance, remove)
    _PREPARED_WALKER_PROVENANCE[identity] = (
        reference,
        instance.domain_digest,
        instance.task_ids,
        instance.action_ids,
        instance._task_id_set,
        instance._action_id_set,
        instance._open_responses,
        instance._seeds,
        instance._rows,
        instance._snapshot_digest,
    )


def _prepared_walker_provenance_entry(instance: Any) -> tuple[Any, ...] | None:
    retained = _PREPARED_WALKER_PROVENANCE.get(id(instance))
    if (
        retained is not None
        and retained[0]() is instance
        and instance.domain_digest is retained[1]
        and instance.task_ids is retained[2]
        and instance.action_ids is retained[3]
        and instance._task_id_set is retained[4]
        and instance._action_id_set is retained[5]
        and instance._open_responses is retained[6]
        and instance._seeds is retained[7]
        and instance._rows is retained[8]
        and instance._snapshot_digest is retained[9]
    ):
        return retained
    return None


def _has_prepared_walker_provenance(instance: Any) -> bool:
    return _prepared_walker_provenance_entry(instance) is not None


def _register_frozen_report(
    registry: dict[int, tuple[Any, ...]], instance: Any, fields: tuple[Any, ...]
) -> None:
    identity = id(instance)

    def remove(reference: weakref.ReferenceType[Any], *, key: int = identity) -> None:
        retained = registry.get(key)
        if retained is not None and retained[0] is reference:
            registry.pop(key, None)

    reference = weakref.ref(instance, remove)
    registry[identity] = (reference, *fields)


def _has_frozen_report_provenance(
    registry: dict[int, tuple[Any, ...]],
    instance: Any,
    fields: tuple[Any, ...],
) -> bool:
    retained = registry.get(id(instance))
    return bool(
        retained is not None
        and retained[0]() is instance
        and len(retained) == len(fields) + 1
        and all(current is frozen for current, frozen in zip(fields, retained[1:], strict=True))
    )


class HistoryContractError(ValueError):
    """A value is outside the frozen C1 history contract."""


class ExactOutcomeKind(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    SINK = "sink"


class TerminalTransitionKind(str, Enum):
    CLOSED = "closed"
    SINK = "sink"


@dataclass(frozen=True)
class CanonicalKStateMarkovContract:
    """Explicit unproved native merge assumption; never a proof certificate."""

    frame_digest: str
    transition_semantics_digest: str
    action_grammar_digest: str
    exactness_scope: str = CONDITIONAL_KSTATE_MARKOV
    proof_status: str = UNPROVED_MARKOV_STATUS

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self) is not CanonicalKStateMarkovContract:
            raise HistoryContractError("CanonicalKStateMarkovContract subclasses are forbidden")
        _digest(self.frame_digest, "Markov frame_digest")
        _digest(
            self.transition_semantics_digest,
            "Markov transition_semantics_digest",
        )
        _digest(self.action_grammar_digest, "Markov action_grammar_digest")
        if self.exactness_scope != CONDITIONAL_KSTATE_MARKOV:
            raise HistoryContractError("native Markov scope must remain conditional")
        if self.proof_status != UNPROVED_MARKOV_STATUS:
            raise HistoryContractError("native Markov contract must remain explicitly unproved")

    def to_wire(self) -> dict[str, str]:
        self.validate()
        return {
            "frame_digest": self.frame_digest,
            "transition_semantics_digest": self.transition_semantics_digest,
            "action_grammar_digest": self.action_grammar_digest,
            "exactness_scope": self.exactness_scope,
            "proof_status": self.proof_status,
        }


def _str(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise HistoryContractError(f"{where} must be an exact nonempty string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise HistoryContractError(f"{where} must be strict UTF-8") from exc
    return value


def _bytes(value: Any, where: str, *, max_bytes: int = MAX_SIGNATURE_BYTES) -> bytes:
    if type(value) is not bytes or not value:
        raise HistoryContractError(f"{where} must be exact nonempty bytes")
    if len(value) > max_bytes:
        raise HistoryContractError(f"{where} exceeds the frozen byte cap")
    return value


def _utf8_bytes(
    value: Any, where: str, *, max_bytes: int = MAX_SIGNATURE_BYTES
) -> bytes:
    raw = _bytes(value, where, max_bytes=max_bytes)
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise HistoryContractError(f"{where} must be strict UTF-8 bytes") from exc
    return raw


def _int(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > MAX_SIGNED_64:
        raise HistoryContractError(
            f"{where} must be an exact signed-64 integer >= {minimum}"
        )
    return value


def _digest(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(ch not in "0123456789ABCDEF" for ch in value)
    ):
        raise HistoryContractError(f"{where} must be an uppercase SHA-256 digest")
    return value


def _strict_exactness_floor(value: Any, where: str = "exactness floor") -> str:
    if type(value) is not str or value not in _EXACTNESS_FLOORS:
        raise HistoryContractError(
            f"{where} must be an exact registered exactness floor"
        )
    return value


def _require_source_authority(actual: Any, expected: Any) -> str:
    """Bind an authority without invoking caller-defined comparison methods."""

    actual_text = _str(actual, "source authority")
    expected_text = _str(expected, "expected source authority")
    actual_bytes = actual_text.encode("utf-8", errors="strict")
    expected_bytes = expected_text.encode("utf-8", errors="strict")
    actual_digest = hashlib.sha256(actual_bytes).digest()
    expected_digest = hashlib.sha256(expected_bytes).digest()
    if not hmac.compare_digest(actual_bytes, expected_bytes) or not hmac.compare_digest(
        actual_digest, expected_digest
    ):
        raise HistoryContractError("finite-domain source authority mismatch")
    return actual_text


def _checked_add(left: int, right: int, where: str) -> int:
    _int(left, where)
    _int(right, where)
    if left > MAX_SIGNED_64 - right:
        raise HistoryContractError(f"{where} exceeds signed-64 arithmetic")
    return left + right


def _checked_mul(left: int, right: int, where: str) -> int:
    _int(left, where)
    _int(right, where)
    if left and right > MAX_SIGNED_64 // left:
        raise HistoryContractError(f"{where} exceeds signed-64 arithmetic")
    return left * right


def checked_word_count(task_count: int, action_count: int, depth: int) -> int:
    """Preflight the geometric word count using signed-64 arithmetic only."""

    _int(task_count, "task_count", minimum=1)
    _int(action_count, "action_count", minimum=1)
    _int(depth, "depth")
    if depth > MAX_CANONICAL_DEPTH:
        raise HistoryContractError("word count depth exceeds the depth-four cap")
    power = 1
    subtotal = 1
    for _ in range(depth):
        power = _checked_mul(power, action_count, "word power")
        subtotal = _checked_add(subtotal, power, "word subtotal")
    return _checked_mul(task_count, subtotal, "raw occurrence count")


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise HistoryContractError("value is outside canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _strict_json_object(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes:
        raise HistoryContractError("domain JSON must be exact bytes")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise HistoryContractError("domain JSON is not strict UTF-8") from exc

    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in rows:
            if type(key) is not str or key in out:
                raise HistoryContractError("domain JSON has a duplicate/non-string key")
            out[key] = value
        return out

    def reject_float(_: str) -> Any:
        raise HistoryContractError("domain JSON forbids floating-point numbers")

    def reject_constant(_: str) -> Any:
        raise HistoryContractError("domain JSON forbids non-finite constants")

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except HistoryContractError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise HistoryContractError("domain JSON is malformed") from exc
    if type(value) is not dict:
        raise HistoryContractError("domain JSON root must be an object")
    return value


def _exact_fields(value: Mapping[str, Any], fields: set[str], where: str) -> None:
    if type(value) is not dict or set(value) != fields:
        actual = set(value) if isinstance(value, Mapping) else set()
        raise HistoryContractError(
            f"{where} field mismatch; missing={sorted(fields-actual)}, "
            f"unknown={sorted(actual-fields)}"
        )


def _hex_bytes(value: Any, where: str) -> bytes:
    text = _str(value, where)
    if (
        len(text) % 2
        or any(ch not in "0123456789ABCDEF" for ch in text)
    ):
        raise HistoryContractError(f"{where} must be canonical uppercase hexadecimal")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise HistoryContractError(f"{where} is invalid hexadecimal") from exc


@dataclass(frozen=True)
class ExactOpenState:
    identity_key: bytes
    full_signature: bytes
    debt: tuple[int, int, int, int, int]
    response_signature: bytes

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _bytes(self.identity_key, "ExactOpenState.identity_key")
        _utf8_bytes(self.full_signature, "ExactOpenState.full_signature")
        _utf8_bytes(self.response_signature, "ExactOpenState.response_signature")
        if type(self.debt) is not tuple or len(self.debt) != 5:
            raise HistoryContractError("ExactOpenState.debt must be an exact 5-tuple")
        for index, value in enumerate(self.debt):
            _int(value, f"ExactOpenState.debt[{index}]")

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return {
            "identity_key": self.identity_key.hex().upper(),
            "full_signature": self.full_signature.hex().upper(),
            "debt": list(self.debt),
            "response_signature": self.response_signature.hex().upper(),
        }


@dataclass(frozen=True)
class TaskSeed:
    task_id: str
    source_identity_key: bytes

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _str(self.task_id, "TaskSeed.task_id")
        _bytes(self.source_identity_key, "TaskSeed.source_identity_key")

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return {
            "task_id": self.task_id,
            "source_identity_key": self.source_identity_key.hex().upper(),
        }


@dataclass(frozen=True)
class SealedTransitionRow:
    source_identity_key: bytes
    action_id: str
    outcome_kind: ExactOutcomeKind
    target_identity_key: bytes | None
    replay_digest: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _bytes(self.source_identity_key, "SealedTransitionRow.source_identity_key")
        _str(self.action_id, "SealedTransitionRow.action_id")
        if type(self.outcome_kind) is not ExactOutcomeKind:
            raise HistoryContractError("transition outcome_kind must be exact ExactOutcomeKind")
        _digest(self.replay_digest, "SealedTransitionRow.replay_digest")
        if self.outcome_kind is ExactOutcomeKind.OPEN:
            _bytes(self.target_identity_key, "open transition target_identity_key")
        elif self.target_identity_key is not None:
            raise HistoryContractError("terminal transition cannot retain a target")

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return {
            "source_identity_key": self.source_identity_key.hex().upper(),
            "action_id": self.action_id,
            "outcome_kind": self.outcome_kind.value,
            "target_identity_key": (
                None
                if self.target_identity_key is None
                else self.target_identity_key.hex().upper()
            ),
            "replay_digest": self.replay_digest,
        }


@dataclass(frozen=True)
class TerminalOccurrence:
    kind: TerminalTransitionKind
    entry_task_id: str
    entry_source_identity_key: bytes
    entry_action_id: str
    entry_word: tuple[str, ...]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.kind) is not TerminalTransitionKind:
            raise HistoryContractError("terminal kind must be exact TerminalTransitionKind")
        _str(self.entry_task_id, "TerminalOccurrence.entry_task_id")
        _bytes(
            self.entry_source_identity_key,
            "TerminalOccurrence.entry_source_identity_key",
        )
        _str(self.entry_action_id, "TerminalOccurrence.entry_action_id")
        if type(self.entry_word) is not tuple or not self.entry_word:
            raise HistoryContractError("terminal entry word/action provenance mismatch")
        for index, action in enumerate(self.entry_word):
            _str(action, f"TerminalOccurrence.entry_word[{index}]")
        if self.entry_word[-1] != self.entry_action_id:
            raise HistoryContractError("terminal entry word/action provenance mismatch")

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return {
            "kind": self.kind.value,
            "entry_task_id": self.entry_task_id,
            "entry_source_identity_key": self.entry_source_identity_key.hex().upper(),
            "entry_action_id": self.entry_action_id,
            "entry_word": list(self.entry_word),
        }


@dataclass(frozen=True)
class ExactOccurrenceResponse:
    kind: ExactOutcomeKind
    open_state: ExactOpenState | None = None
    terminal: TerminalOccurrence | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.kind) is not ExactOutcomeKind:
            raise HistoryContractError("response kind must be exact ExactOutcomeKind")
        if self.kind is ExactOutcomeKind.OPEN:
            if type(self.open_state) is not ExactOpenState or self.terminal is not None:
                raise HistoryContractError("OPEN response requires only an exact open state")
            self.open_state.validate()
            return
        if self.open_state is not None or type(self.terminal) is not TerminalOccurrence:
            raise HistoryContractError("terminal response requires only exact provenance")
        self.terminal.validate()
        if self.terminal.kind.value != self.kind.value:
            raise HistoryContractError("terminal response kind/provenance mismatch")

    @classmethod
    def open(cls, state: ExactOpenState) -> "ExactOccurrenceResponse":
        return cls(ExactOutcomeKind.OPEN, open_state=state)

    @classmethod
    def terminal_response(
        cls, occurrence: TerminalOccurrence
    ) -> "ExactOccurrenceResponse":
        return cls(ExactOutcomeKind(occurrence.kind.value), terminal=occurrence)

    def hankel_channels(self) -> tuple[int, int, int, int, int, int, int]:
        self.validate()
        if self.kind is ExactOutcomeKind.CLOSED:
            return (1, 0, 0, 0, 0, 0, 0)
        if self.kind is ExactOutcomeKind.SINK:
            return (0, 1, 0, 0, 0, 0, 0)
        assert self.open_state is not None
        return (0, 0, *self.open_state.debt)

    def to_wire(self) -> dict[str, Any]:
        """Complete canonical-JSON tagged record, including raw provenance."""

        self.validate()
        return {
            "schema_version": "lean-rgc-kp3d4-exact-occurrence-response-v1",
            "kind": self.kind.value,
            "open": None if self.open_state is None else self.open_state.to_wire(),
            "terminal": None if self.terminal is None else self.terminal.to_wire(),
        }


def _fresh_open_response_from_primitive(
    identity_key: bytes,
    full_signature: bytes,
    debt: tuple[int, int, int, int, int],
    response_signature: bytes,
) -> ExactOccurrenceResponse:
    """Detach one response from an already-validated immutable index payload.

    The chart/walker factories validate every primitive before registering the
    immutable maps.  Re-running UTF-8 and signed-64 admission twice for every
    retained H4 coordinate adds no independent check; serializers validate a
    first occurrence on each side, and both authorities are revalidated after
    the exhaustive traversal.
    """

    state = object.__new__(ExactOpenState)
    object.__setattr__(state, "identity_key", identity_key)
    object.__setattr__(state, "full_signature", full_signature)
    object.__setattr__(state, "debt", tuple(debt))
    object.__setattr__(state, "response_signature", response_signature)
    response = object.__new__(ExactOccurrenceResponse)
    object.__setattr__(response, "kind", ExactOutcomeKind.OPEN)
    object.__setattr__(response, "open_state", state)
    object.__setattr__(response, "terminal", None)
    return response


def _snapshot_open_state(value: ExactOpenState) -> ExactOpenState:
    if type(value) is not ExactOpenState:
        raise HistoryContractError("OPEN state snapshot requires an exact state")
    value.validate()
    return ExactOpenState(
        value.identity_key,
        value.full_signature,
        tuple(value.debt),
        value.response_signature,
    )


def _snapshot_task_seed(value: TaskSeed) -> TaskSeed:
    if type(value) is not TaskSeed:
        raise HistoryContractError("task seed snapshot requires an exact seed")
    value.validate()
    return TaskSeed(value.task_id, value.source_identity_key)


def _snapshot_transition_row(value: SealedTransitionRow) -> SealedTransitionRow:
    if type(value) is not SealedTransitionRow:
        raise HistoryContractError("transition snapshot requires an exact row")
    value.validate()
    return SealedTransitionRow(
        value.source_identity_key,
        value.action_id,
        value.outcome_kind,
        value.target_identity_key,
        value.replay_digest,
    )


def _snapshot_occurrence_response(
    value: ExactOccurrenceResponse,
) -> ExactOccurrenceResponse:
    if type(value) is not ExactOccurrenceResponse:
        raise HistoryContractError("response snapshot requires an exact response")
    value.validate()
    if value.kind is ExactOutcomeKind.OPEN:
        assert value.open_state is not None
        return ExactOccurrenceResponse.open(_snapshot_open_state(value.open_state))
    assert value.terminal is not None
    terminal = value.terminal
    return ExactOccurrenceResponse.terminal_response(
        TerminalOccurrence(
            terminal.kind,
            terminal.entry_task_id,
            terminal.entry_source_identity_key,
            terminal.entry_action_id,
            tuple(terminal.entry_word),
        )
    )


@dataclass(frozen=True)
class FiniteTotalActionDomain:
    source_authority: str
    semantics_digest: str
    task_seeds: tuple[TaskSeed, ...]
    action_ids: tuple[str, ...]
    open_states: tuple[ExactOpenState, ...]
    transition_rows: tuple[SealedTransitionRow, ...]
    exactness_floor: str = UNCONDITIONAL_FINITE_DOMAIN

    def __post_init__(self) -> None:
        _str(self.source_authority, "source_authority")
        _digest(self.semantics_digest, "semantics_digest")
        _strict_exactness_floor(self.exactness_floor)
        for name, values in (
            ("task_seeds", self.task_seeds),
            ("action_ids", self.action_ids),
            ("open_states", self.open_states),
            ("transition_rows", self.transition_rows),
        ):
            if type(values) is not tuple:
                raise HistoryContractError(f"{name} must be an exact immutable tuple")
        for name, count, cap in (
            ("task seed count", len(self.task_seeds), MAX_TASK_SEEDS),
            ("action alphabet", len(self.action_ids), MAX_ACTIONS),
            ("OPEN state domain", len(self.open_states), MAX_OPEN_STATES),
            ("transition row count", len(self.transition_rows), MAX_TRANSITION_ROWS),
        ):
            if count > cap:
                raise HistoryContractError(f"{name} exceeds the frozen cap")
        for name, values, exact_type in (
            ("task_seeds", self.task_seeds, TaskSeed),
            ("open_states", self.open_states, ExactOpenState),
            ("transition_rows", self.transition_rows, SealedTransitionRow),
        ):
            if any(type(item) is not exact_type for item in values):
                raise HistoryContractError(f"{name} must be an exact immutable tuple")
        if any(type(action) is not str or not action for action in self.action_ids):
            raise HistoryContractError("action_ids must be an exact immutable string tuple")

        tasks = tuple(
            sorted(
                (_snapshot_task_seed(row) for row in self.task_seeds),
                key=lambda row: row.task_id,
            )
        )
        actions = tuple(sorted(self.action_ids))
        states = tuple(
            sorted(
                (_snapshot_open_state(row) for row in self.open_states),
                key=lambda row: row.identity_key,
            )
        )
        rows = tuple(
            sorted(
                (_snapshot_transition_row(row) for row in self.transition_rows),
                key=lambda row: (row.source_identity_key, row.action_id),
            )
        )
        object.__setattr__(self, "task_seeds", tasks)
        object.__setattr__(self, "action_ids", actions)
        object.__setattr__(self, "open_states", states)
        object.__setattr__(self, "transition_rows", rows)
        self.validate()
        state_map = MappingProxyType({state.identity_key: state for state in states})
        row_map = MappingProxyType(
            {(row.source_identity_key, row.action_id): row for row in rows}
        )
        seed_map = MappingProxyType(
            {seed.task_id: seed.source_identity_key for seed in tasks}
        )
        object.__setattr__(self, "_state_map", state_map)
        object.__setattr__(self, "_row_map", row_map)
        object.__setattr__(self, "_seed_map", seed_map)
        object.__setattr__(self, "_content_seal", _sha(self._content_wire()))

    @property
    def task_ids(self) -> tuple[str, ...]:
        return tuple(seed.task_id for seed in self.task_seeds)

    @property
    def digest(self) -> str:
        self.validate()
        return self._content_seal  # type: ignore[attr-defined]

    @property
    def action_grammar_digest(self) -> str:
        return _sha(
            {
                "schema_version": ACTION_GRAMMAR_SCHEMA,
                "action_ids": list(self.action_ids),
            }
        )

    @property
    def sealed(self) -> bool:
        try:
            self.validate()
        except HistoryContractError:
            return False
        return True

    def state(self, identity_key: bytes) -> ExactOpenState:
        _bytes(identity_key, "state identity key")
        try:
            return self._state_map[identity_key]  # type: ignore[attr-defined]
        except KeyError as exc:
            raise HistoryContractError("unknown OPEN state identity") from exc

    def seed_state(self, task_id: str) -> ExactOpenState:
        _str(task_id, "seed task ID")
        try:
            return self.state(self._seed_map[task_id])  # type: ignore[attr-defined]
        except KeyError as exc:
            raise HistoryContractError("unknown task ID") from exc

    def transition(self, identity_key: bytes, action_id: str) -> SealedTransitionRow:
        _bytes(identity_key, "transition state identity key")
        _str(action_id, "transition action ID")
        try:
            return self._row_map[(identity_key, action_id)]  # type: ignore[attr-defined]
        except KeyError as exc:
            raise HistoryContractError("unsealed state/action row") from exc

    def validate(self) -> None:
        _str(self.source_authority, "source_authority")
        _digest(self.semantics_digest, "semantics_digest")
        _strict_exactness_floor(self.exactness_floor)
        if type(self.task_seeds) is not tuple or any(
            type(seed) is not TaskSeed for seed in self.task_seeds
        ):
            raise HistoryContractError("task_seeds must be an exact immutable tuple")
        if type(self.action_ids) is not tuple or any(
            type(action) is not str or not action for action in self.action_ids
        ):
            raise HistoryContractError("action_ids must be an exact immutable string tuple")
        if type(self.open_states) is not tuple or any(
            type(state) is not ExactOpenState for state in self.open_states
        ):
            raise HistoryContractError("open_states must be an exact immutable tuple")
        if type(self.transition_rows) is not tuple or any(
            type(row) is not SealedTransitionRow for row in self.transition_rows
        ):
            raise HistoryContractError("transition_rows must be an exact immutable tuple")
        if self.task_seeds != tuple(sorted(self.task_seeds, key=lambda row: row.task_id)):
            raise HistoryContractError("task seeds lost canonical order")
        if self.action_ids != tuple(sorted(self.action_ids)):
            raise HistoryContractError("action IDs lost canonical order")
        if self.open_states != tuple(sorted(self.open_states, key=lambda row: row.identity_key)):
            raise HistoryContractError("OPEN states lost canonical order")
        if self.transition_rows != tuple(
            sorted(self.transition_rows, key=lambda row: (row.source_identity_key, row.action_id))
        ):
            raise HistoryContractError("transition rows lost canonical order")
        if not self.task_seeds or not self.action_ids or not self.open_states:
            raise HistoryContractError("finite domain components must be nonempty")
        if len(self.task_seeds) > MAX_TASK_SEEDS:
            raise HistoryContractError("task seed count exceeds the frozen raw-occurrence cap")
        if len(self.action_ids) > MAX_ACTIONS:
            raise HistoryContractError("action alphabet exceeds frozen cap")
        if len(self.open_states) > MAX_OPEN_STATES:
            raise HistoryContractError("OPEN state domain exceeds frozen cap")
        if len(self.task_ids) != len(set(self.task_ids)):
            raise HistoryContractError("task IDs contain duplicates")
        if len(self.action_ids) != len(set(self.action_ids)):
            raise HistoryContractError("action IDs contain duplicates")

        state_by_key: dict[bytes, ExactOpenState] = {}
        total_signature_bytes = 0
        for state in self.open_states:
            state.validate()
            old = state_by_key.get(state.identity_key)
            if old is not None:
                if old.full_signature != state.full_signature:
                    raise HistoryContractError("same identity key has different full signature")
                if old.debt != state.debt:
                    raise HistoryContractError("same identity key has different debt")
                if old.response_signature != state.response_signature:
                    raise HistoryContractError("same identity key has different response")
                raise HistoryContractError("duplicate OPEN state identity")
            state_by_key[state.identity_key] = state
            total_signature_bytes = _checked_add(
                total_signature_bytes,
                len(state.identity_key) + len(state.full_signature) + len(state.response_signature),
                "total signature bytes",
            )
        if total_signature_bytes > MAX_TOTAL_SIGNATURE_BYTES:
            raise HistoryContractError("all signatures exceed the frozen byte cap")

        expected_rows = _checked_mul(
            len(state_by_key), len(self.action_ids), "transition row count"
        )
        if expected_rows > MAX_TRANSITION_ROWS:
            raise HistoryContractError("transition row count exceeds frozen cap")
        if len(self.transition_rows) != expected_rows:
            raise HistoryContractError("finite domain is not total over state/action pairs")

        for seed in self.task_seeds:
            seed.validate()
            if seed.source_identity_key not in state_by_key:
                raise HistoryContractError("task seed references an unknown OPEN state")

        expected_pairs = {
            (state.identity_key, action)
            for state in self.open_states
            for action in self.action_ids
        }
        actual_pairs: set[tuple[bytes, str]] = set()
        for row in self.transition_rows:
            row.validate()
            pair = (row.source_identity_key, row.action_id)
            if pair in actual_pairs:
                raise HistoryContractError("duplicate state/action transition row")
            actual_pairs.add(pair)
            if row.source_identity_key not in state_by_key or row.action_id not in self.action_ids:
                raise HistoryContractError("transition row is outside the finite domain")
            if (
                row.outcome_kind is ExactOutcomeKind.OPEN
                and row.target_identity_key not in state_by_key
            ):
                raise HistoryContractError("OPEN successor is outside the finite domain")
        if actual_pairs != expected_pairs:
            raise HistoryContractError("finite domain has an unresolved state/action frontier")

        reachable = {seed.source_identity_key for seed in self.task_seeds}
        changed = True
        while changed:
            changed = False
            for row in self.transition_rows:
                if (
                    row.source_identity_key in reachable
                    and row.outcome_kind is ExactOutcomeKind.OPEN
                    and row.target_identity_key not in reachable
                ):
                    assert row.target_identity_key is not None
                    reachable.add(row.target_identity_key)
                    changed = True
        if reachable != set(state_by_key):
            raise HistoryContractError("finite domain contains an unreachable OPEN state")
        if hasattr(self, "_state_map"):
            expected_state_map = {state.identity_key: state for state in self.open_states}
            expected_row_map = {
                (row.source_identity_key, row.action_id): row
                for row in self.transition_rows
            }
            expected_seed_map = {
                seed.task_id: seed.source_identity_key for seed in self.task_seeds
            }
            if (
                dict(self._state_map) != expected_state_map  # type: ignore[attr-defined]
                or dict(self._row_map) != expected_row_map  # type: ignore[attr-defined]
                or dict(self._seed_map) != expected_seed_map  # type: ignore[attr-defined]
            ):
                raise HistoryContractError("finite-domain derived index mutation detected")
        if hasattr(self, "_content_seal"):
            if self._content_seal != _sha(self._content_wire()):  # type: ignore[attr-defined]
                raise HistoryContractError("finite-domain content seal mismatch")

    def _content_wire(self) -> dict[str, Any]:
        return {
            "schema_version": FINITE_DOMAIN_SCHEMA,
            "source_authority": self.source_authority,
            "semantics_digest": self.semantics_digest,
            "exactness_floor": self.exactness_floor,
            "tasks": [seed.to_wire() for seed in self.task_seeds],
            "action_ids": list(self.action_ids),
            "states": [state.to_wire() for state in self.open_states],
            "transitions": [row.to_wire() for row in self.transition_rows],
        }

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return self._content_wire()

    def to_canonical_json_bytes(self) -> bytes:
        return _canonical_bytes(self.to_wire())

    @classmethod
    def from_json_bytes(
        cls, payload: bytes, *, expected_source_authority: str
    ) -> "FiniteTotalActionDomain":
        if cls is not FiniteTotalActionDomain:
            raise HistoryContractError("finite-domain subclass construction is forbidden")
        _str(expected_source_authority, "expected source authority")
        if type(payload) is not bytes:
            raise HistoryContractError("domain JSON must be exact bytes")
        if len(payload) >= MAX_REPORT_BYTES:
            raise HistoryContractError("domain JSON exceeds the frozen payload byte cap")
        obj = _strict_json_object(payload)
        _exact_fields(
            obj,
            {
                "schema_version",
                "source_authority",
                "semantics_digest",
                "exactness_floor",
                "tasks",
                "action_ids",
                "states",
                "transitions",
            },
            "finite domain",
        )
        if obj["schema_version"] != FINITE_DOMAIN_SCHEMA:
            raise HistoryContractError("wrong finite-domain schema")
        _require_source_authority(obj["source_authority"], expected_source_authority)
        exactness_floor = _strict_exactness_floor(obj["exactness_floor"])

        def exact_list(value: Any, where: str) -> list[Any]:
            if type(value) is not list:
                raise HistoryContractError(f"{where} must be an exact array")
            return value

        tasks_payload = exact_list(obj["tasks"], "tasks")
        action_payload = exact_list(obj["action_ids"], "action_ids")
        states_payload = exact_list(obj["states"], "states")
        rows_payload = exact_list(obj["transitions"], "transitions")
        for name, count, cap in (
            ("tasks", len(tasks_payload), MAX_TASK_SEEDS),
            ("action_ids", len(action_payload), MAX_ACTIONS),
            ("states", len(states_payload), MAX_OPEN_STATES),
            ("transitions", len(rows_payload), MAX_TRANSITION_ROWS),
        ):
            if count > cap:
                raise HistoryContractError(f"{name} exceeds the frozen cap")

        tasks: list[TaskSeed] = []
        for item in tasks_payload:
            _exact_fields(item, {"task_id", "source_identity_key"}, "task")
            tasks.append(TaskSeed(_str(item["task_id"], "task_id"), _hex_bytes(item["source_identity_key"], "source_identity_key")))
        states: list[ExactOpenState] = []
        for item in states_payload:
            _exact_fields(item, {"identity_key", "full_signature", "debt", "response_signature"}, "state")
            debt = exact_list(item["debt"], "debt")
            states.append(ExactOpenState(_hex_bytes(item["identity_key"], "identity_key"), _hex_bytes(item["full_signature"], "full_signature"), tuple(debt), _hex_bytes(item["response_signature"], "response_signature")))  # type: ignore[arg-type]
        rows: list[SealedTransitionRow] = []
        for item in rows_payload:
            _exact_fields(item, {"source_identity_key", "action_id", "outcome_kind", "target_identity_key", "replay_digest"}, "transition")
            target = item["target_identity_key"]
            if target is not None:
                target = _hex_bytes(target, "target_identity_key")
            try:
                kind = ExactOutcomeKind(item["outcome_kind"])
            except (TypeError, ValueError) as exc:
                raise HistoryContractError("invalid transition outcome kind") from exc
            rows.append(SealedTransitionRow(_hex_bytes(item["source_identity_key"], "source_identity_key"), _str(item["action_id"], "action_id"), kind, target, _digest(item["replay_digest"], "replay_digest")))
        return cls(
            source_authority=_str(obj["source_authority"], "source_authority"),
            semantics_digest=_digest(obj["semantics_digest"], "semantics_digest"),
            exactness_floor=exactness_floor,
            task_seeds=tuple(tasks),
            action_ids=tuple(action_payload),
            open_states=tuple(states),
            transition_rows=tuple(rows),
        )


def build_finite_total_action_domain(
    *,
    source_authority: str,
    semantics_digest: str,
    task_seeds: Sequence[TaskSeed],
    action_ids: Sequence[str],
    open_states: Sequence[ExactOpenState],
    transition_rows: Sequence[SealedTransitionRow],
    expected_source_authority: str | None = None,
    exactness_floor: str = UNCONDITIONAL_FINITE_DOMAIN,
) -> FiniteTotalActionDomain:
    """Canonicalize caller order after structural cap checks."""

    _str(source_authority, "source authority")
    _strict_exactness_floor(exactness_floor)
    if expected_source_authority is not None:
        _require_source_authority(source_authority, expected_source_authority)
    declared_counts: dict[str, int] = {}
    for name, values, cap in (
        ("task_seeds", task_seeds, MAX_TASK_SEEDS),
        ("action_ids", action_ids, MAX_ACTIONS),
        ("open_states", open_states, MAX_OPEN_STATES),
        ("transition_rows", transition_rows, MAX_TRANSITION_ROWS),
    ):
        try:
            count = len(values)
        except Exception as exc:
            raise HistoryContractError(f"{name} must be a sized sequence") from exc
        _int(count, f"{name} count")
        if count > cap:
            raise HistoryContractError(f"{name} exceeds the frozen cap")
        declared_counts[name] = count

    materialized: dict[str, tuple[Any, ...]] = {}
    for name, values, cap in (
        ("task_seeds", task_seeds, MAX_TASK_SEEDS),
        ("action_ids", action_ids, MAX_ACTIONS),
        ("open_states", open_states, MAX_OPEN_STATES),
        ("transition_rows", transition_rows, MAX_TRANSITION_ROWS),
    ):
        try:
            iterator = iter(values)
            retained: list[Any] = []
            materialization_limit = min(declared_counts[name] + 1, cap + 1)
            for _ in range(materialization_limit):
                try:
                    retained.append(next(iterator))
                except StopIteration:
                    break
        except Exception as exc:
            raise HistoryContractError(f"{name} could not be boundedly materialized") from exc
        if len(retained) > cap:
            raise HistoryContractError(f"{name} exceeds the frozen cap")
        if len(retained) != declared_counts[name]:
            raise HistoryContractError(f"{name} declared/materialized length mismatch")
        materialized[name] = tuple(retained)

    return FiniteTotalActionDomain(
        source_authority=source_authority,
        semantics_digest=semantics_digest,
        exactness_floor=exactness_floor,
        task_seeds=materialized["task_seeds"],  # type: ignore[arg-type]
        action_ids=materialized["action_ids"],  # type: ignore[arg-type]
        open_states=materialized["open_states"],  # type: ignore[arg-type]
        transition_rows=materialized["transition_rows"],  # type: ignore[arg-type]
    )


def _snapshot_finite_domain(
    domain: FiniteTotalActionDomain,
) -> FiniteTotalActionDomain:
    if type(domain) is not FiniteTotalActionDomain:
        raise HistoryContractError("domain snapshot requires an exact finite domain")
    domain.validate()
    return FiniteTotalActionDomain(
        source_authority=domain.source_authority,
        semantics_digest=domain.semantics_digest,
        exactness_floor=domain.exactness_floor,
        task_seeds=domain.task_seeds,
        action_ids=domain.action_ids,
        open_states=domain.open_states,
        transition_rows=domain.transition_rows,
    )


def _word(value: Any, where: str = "action word") -> tuple[str, ...]:
    if type(value) is not tuple:
        raise HistoryContractError(f"{where} must be an exact tuple of action IDs")
    for index, action in enumerate(value):
        _str(action, f"{where}[{index}]")
    return value


def _registered_word(
    value: Any, action_ids: frozenset[str], where: str
) -> tuple[str, ...]:
    if type(value) is not tuple or any(
        type(action) is not str or action not in action_ids for action in value
    ):
        raise HistoryContractError(
            f"{where} must be an exact tuple of registered action IDs"
        )
    return value


def _words(action_ids: tuple[str, ...], depth: int) -> Iterator[tuple[str, ...]]:
    if depth == 0:
        yield ()
    else:
        yield from product(action_ids, repeat=depth)


def _terminal_kind(kind: ExactOutcomeKind) -> TerminalTransitionKind:
    if kind is ExactOutcomeKind.CLOSED:
        return TerminalTransitionKind.CLOSED
    if kind is ExactOutcomeKind.SINK:
        return TerminalTransitionKind.SINK
    raise HistoryContractError("OPEN is not a terminal kind")


@dataclass(frozen=True)
class BehavioralClassKey:
    kind: ExactOutcomeKind
    state_identity_key: bytes | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.kind) is not ExactOutcomeKind:
            raise HistoryContractError("behavioral kind must be exact ExactOutcomeKind")
        if self.kind is ExactOutcomeKind.OPEN:
            _bytes(self.state_identity_key, "OPEN behavioral state key")
        elif self.state_identity_key is not None:
            raise HistoryContractError("terminal behavioral key cannot retain state identity")

    def sort_key(self) -> tuple[str, bytes]:
        return (self.kind.value, self.state_identity_key or b"")

    def to_wire(self) -> list[Any]:
        self.validate()
        return [
            self.kind.value,
            None if self.state_identity_key is None else self.state_identity_key.hex().upper(),
        ]


BehavioralKeyPayload = tuple[str, bytes | None]
ChartEdgeIndexKey = tuple[int, str, bytes | None, str]
ChartRepresentativeIndexKey = tuple[int, str, bytes | None]
OpenStatePayload = tuple[bytes, tuple[int, int, int, int, int], bytes]


def _behavioral_key_payload(value: BehavioralClassKey) -> BehavioralKeyPayload:
    if type(value) is not BehavioralClassKey:
        raise HistoryContractError("behavioral snapshot requires an exact class key")
    value.validate()
    return (value.kind.value, value.state_identity_key)


def _response_key(response: ExactOccurrenceResponse) -> BehavioralClassKey:
    response.validate()
    if response.kind is ExactOutcomeKind.OPEN:
        assert response.open_state is not None
        return BehavioralClassKey(response.kind, response.open_state.identity_key)
    return BehavioralClassKey(response.kind)


def _representative_order(
    task_id: str, word: tuple[str, ...]
) -> tuple[int, str, tuple[str, ...]]:
    return (len(word), task_id, word)


@dataclass(frozen=True)
class CanonicalHistoryClass:
    key: BehavioralClassKey
    representative_task_id: str
    representative_word: tuple[str, ...]
    raw_multiplicity: int

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.key) is not BehavioralClassKey:
            raise HistoryContractError("class key must be exact BehavioralClassKey")
        _str(self.representative_task_id, "representative task ID")
        _word(self.representative_word, "representative word")
        _int(self.raw_multiplicity, "raw_multiplicity", minimum=1)
        self.key.validate()


@dataclass(frozen=True)
class ContributionEdge:
    source_key: BehavioralClassKey
    action_id: str
    target_key: BehavioralClassKey
    witness_digest: str
    flow: int

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.source_key) is not BehavioralClassKey or type(self.target_key) is not BehavioralClassKey:
            raise HistoryContractError("contribution endpoints must be exact class keys")
        _str(self.action_id, "ContributionEdge.action_id")
        _digest(self.witness_digest, "ContributionEdge.witness_digest")
        _int(self.flow, "ContributionEdge.flow", minimum=1)
        self.source_key.validate()
        self.target_key.validate()


@dataclass(frozen=True)
class CanonicalHistoryLayer:
    depth: int
    classes: tuple[CanonicalHistoryClass, ...]
    incoming_edges: tuple[ContributionEdge, ...]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _int(self.depth, "layer depth")
        if type(self.classes) is not tuple or any(type(row) is not CanonicalHistoryClass for row in self.classes):
            raise HistoryContractError("layer classes must be an exact immutable tuple")
        if type(self.incoming_edges) is not tuple or any(type(row) is not ContributionEdge for row in self.incoming_edges):
            raise HistoryContractError("layer edges must be an exact immutable tuple")
        if len({row.key for row in self.classes}) != len(self.classes):
            raise HistoryContractError("layer has duplicate behavioral classes")
        if self.depth == 0 and self.incoming_edges:
            raise HistoryContractError("depth-zero layer cannot have incoming edges")
        for row in self.classes:
            row.validate()
        for row in self.incoming_edges:
            row.validate()

    @property
    def raw_multiplicity(self) -> int:
        self.validate()
        total = 0
        for row in self.classes:
            total = _checked_add(total, row.raw_multiplicity, "layer raw multiplicity")
        return total

    def class_for(self, key: BehavioralClassKey) -> CanonicalHistoryClass:
        if type(key) is not BehavioralClassKey:
            raise HistoryContractError("class lookup requires an exact BehavioralClassKey")
        key.validate()
        for row in self.classes:
            if row.key == key:
                return row
        raise HistoryContractError("behavioral class is absent from layer")


def _snapshot_behavioral_key(value: BehavioralClassKey) -> BehavioralClassKey:
    if type(value) is not BehavioralClassKey:
        raise HistoryContractError("layer snapshot requires an exact class key")
    value.validate()
    return BehavioralClassKey(value.kind, value.state_identity_key)


def _snapshot_history_class(value: CanonicalHistoryClass) -> CanonicalHistoryClass:
    if type(value) is not CanonicalHistoryClass:
        raise HistoryContractError("layer snapshot requires an exact history class")
    value.validate()
    return CanonicalHistoryClass(
        _snapshot_behavioral_key(value.key),
        value.representative_task_id,
        tuple(action for action in value.representative_word),
        value.raw_multiplicity,
    )


def _snapshot_contribution_edge(value: ContributionEdge) -> ContributionEdge:
    if type(value) is not ContributionEdge:
        raise HistoryContractError("layer snapshot requires an exact contribution edge")
    value.validate()
    return ContributionEdge(
        _snapshot_behavioral_key(value.source_key),
        value.action_id,
        _snapshot_behavioral_key(value.target_key),
        value.witness_digest,
        value.flow,
    )


def _snapshot_history_layer(value: CanonicalHistoryLayer) -> CanonicalHistoryLayer:
    if type(value) is not CanonicalHistoryLayer:
        raise HistoryContractError("chart snapshot requires an exact history layer")
    value.validate()
    return CanonicalHistoryLayer(
        value.depth,
        tuple(_snapshot_history_class(row) for row in value.classes),
        tuple(_snapshot_contribution_edge(row) for row in value.incoming_edges),
    )


def _seed_layer(domain: FiniteTotalActionDomain) -> CanonicalHistoryLayer:
    counts: dict[BehavioralClassKey, int] = {}
    representatives: dict[BehavioralClassKey, str] = {}
    for task_id in domain.task_ids:
        key = BehavioralClassKey(
            ExactOutcomeKind.OPEN,
            domain.seed_state(task_id).identity_key,
        )
        counts[key] = _checked_add(counts.get(key, 0), 1, "seed multiplicity")
        current = representatives.get(key)
        if current is None or task_id < current:
            representatives[key] = task_id
    return CanonicalHistoryLayer(
        0,
        tuple(
            CanonicalHistoryClass(key, representatives[key], (), counts[key])
            for key in sorted(counts, key=lambda item: item.sort_key())
        ),
        (),
    )


def _derive_expected_layer(
    domain: FiniteTotalActionDomain,
    previous: CanonicalHistoryLayer,
    depth: int,
) -> CanonicalHistoryLayer:
    """Pure semantic rederivation used to reject forged/mutated charts."""

    multiplicities: dict[BehavioralClassKey, int] = {}
    representatives: dict[BehavioralClassKey, tuple[str, tuple[str, ...]]] = {}
    incoming: list[ContributionEdge] = []
    for source in previous.classes:
        for action in domain.action_ids:
            if source.key.kind is ExactOutcomeKind.OPEN:
                assert source.key.state_identity_key is not None
                row = domain.transition(source.key.state_identity_key, action)
                if row.outcome_kind is ExactOutcomeKind.OPEN:
                    assert row.target_identity_key is not None
                    target = BehavioralClassKey(
                        ExactOutcomeKind.OPEN,
                        row.target_identity_key,
                    )
                else:
                    target = BehavioralClassKey(row.outcome_kind)
                candidate = (
                    source.representative_task_id,
                    source.representative_word + (action,),
                )
                evidence = row.to_wire()
            else:
                target = source.key
                candidate = (
                    source.representative_task_id,
                    source.representative_word,
                )
                evidence = {
                    "terminal_tail_absorb": source.key.kind.value,
                    "action_id": action,
                }
            multiplicities[target] = _checked_add(
                multiplicities.get(target, 0),
                source.raw_multiplicity,
                "class flow",
            )
            current_rep = representatives.get(target)
            if current_rep is None or _representative_order(*candidate) < _representative_order(*current_rep):
                representatives[target] = candidate
            incoming.append(
                ContributionEdge(
                    source.key,
                    action,
                    target,
                    _sha(
                        {
                            "schema_version": HISTORY_GRAMMAR_SCHEMA,
                            "depth": depth,
                            "representative_task_id": source.representative_task_id,
                            "source": source.key.to_wire(),
                            "source_representative": list(source.representative_word),
                            "action_id": action,
                            "target": target.to_wire(),
                            "evidence": evidence,
                        }
                    ),
                    source.raw_multiplicity,
                )
            )
    return CanonicalHistoryLayer(
        depth,
        tuple(
            CanonicalHistoryClass(
                key,
                representatives[key][0],
                representatives[key][1],
                multiplicities[key],
            )
            for key in sorted(multiplicities, key=lambda item: item.sort_key())
        ),
        tuple(
            sorted(
                incoming,
                key=lambda row: (row.source_key.sort_key(), row.action_id),
            )
        ),
    )


@dataclass(frozen=True)
class ReportBytePreflight:
    source_domain_digest: str
    max_depth: int
    total_signature_utf8_bytes: int
    transition_rows: int
    duplicate_row_checks: int
    canonical_class_upper: int
    contribution_edge_upper: int
    report_byte_upper: int

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _digest(self.source_domain_digest, "ReportBytePreflight.source_domain_digest")
        _int(self.max_depth, "ReportBytePreflight.max_depth")
        if self.max_depth > MAX_CANONICAL_DEPTH:
            raise HistoryContractError("report preflight depth exceeds the frozen cap")
        for name in (
            "total_signature_utf8_bytes",
            "transition_rows",
            "duplicate_row_checks",
            "canonical_class_upper",
            "contribution_edge_upper",
            "report_byte_upper",
        ):
            _int(getattr(self, name), f"ReportBytePreflight.{name}")
        if self.total_signature_utf8_bytes > MAX_TOTAL_SIGNATURE_BYTES:
            raise HistoryContractError("report signatures exceed the frozen byte cap")
        if self.transition_rows > MAX_TRANSITION_ROWS:
            raise HistoryContractError("report transition rows exceed the frozen cap")
        if self.canonical_class_upper > MAX_CANONICAL_CLASSES:
            raise HistoryContractError("canonical class preflight exceeds the frozen cap")
        if self.contribution_edge_upper > MAX_CONTRIBUTION_EDGES:
            raise HistoryContractError("contribution edge preflight exceeds the frozen cap")
        if self.report_byte_upper >= MAX_REPORT_BYTES:
            raise HistoryContractError("source-bound report upper is not below 64 MiB")

    def to_wire(self) -> dict[str, int]:
        self.validate()
        return {
            "source_domain_digest": self.source_domain_digest,
            "max_depth": self.max_depth,
            "total_signature_utf8_bytes": self.total_signature_utf8_bytes,
            "transition_rows": self.transition_rows,
            "duplicate_row_checks": self.duplicate_row_checks,
            "canonical_class_upper": self.canonical_class_upper,
            "contribution_edge_upper": self.contribution_edge_upper,
            "report_byte_upper": self.report_byte_upper,
        }


def _snapshot_markov_contract(
    value: CanonicalKStateMarkovContract | None,
) -> CanonicalKStateMarkovContract | None:
    if value is None:
        return None
    if type(value) is not CanonicalKStateMarkovContract:
        raise HistoryContractError("chart Markov snapshot requires an exact contract")
    value.validate()
    return CanonicalKStateMarkovContract(
        frame_digest=value.frame_digest,
        transition_semantics_digest=value.transition_semantics_digest,
        action_grammar_digest=value.action_grammar_digest,
        exactness_scope=value.exactness_scope,
        proof_status=value.proof_status,
    )


def _snapshot_report_preflight(
    value: ReportBytePreflight | None,
) -> ReportBytePreflight | None:
    if value is None:
        return None
    if type(value) is not ReportBytePreflight:
        raise HistoryContractError("chart preflight snapshot requires an exact report")
    value.validate()
    return ReportBytePreflight(
        source_domain_digest=value.source_domain_digest,
        max_depth=value.max_depth,
        total_signature_utf8_bytes=value.total_signature_utf8_bytes,
        transition_rows=value.transition_rows,
        duplicate_row_checks=value.duplicate_row_checks,
        canonical_class_upper=value.canonical_class_upper,
        contribution_edge_upper=value.contribution_edge_upper,
        report_byte_upper=value.report_byte_upper,
    )


def _validate_chart_markov_binding(
    domain: FiniteTotalActionDomain,
    markov_contract: CanonicalKStateMarkovContract | None,
) -> None:
    if (
        domain.exactness_floor == CONDITIONAL_KSTATE_MARKOV
        and markov_contract is None
    ):
        raise HistoryContractError(
            "conditional exactness floor requires a valid Markov contract"
        )
    if markov_contract is None:
        return
    if type(markov_contract) is not CanonicalKStateMarkovContract:
        raise HistoryContractError("chart Markov contract has the wrong type")
    markov_contract.validate()
    if markov_contract.transition_semantics_digest != domain.semantics_digest:
        raise HistoryContractError("Markov/domain transition semantics mismatch")
    if markov_contract.action_grammar_digest != domain.action_grammar_digest:
        raise HistoryContractError("Markov/domain action grammar mismatch")


def _preflight_chart_layer_snapshot_shape(
    max_depth: int,
    layers: tuple[CanonicalHistoryLayer, ...],
) -> tuple[int, int]:
    """Reject oversized/nonsnapshotable layer shells before any deep copy."""

    _int(max_depth, "max_depth")
    if max_depth > MAX_CANONICAL_DEPTH:
        raise HistoryContractError("canonical depth exceeds frozen cap")
    if type(layers) is not tuple or len(layers) != max_depth + 1:
        raise HistoryContractError("chart layers are incomplete")
    class_count = 0
    edge_count = 0
    for index, layer in enumerate(layers):
        if type(layer) is not CanonicalHistoryLayer:
            raise HistoryContractError("chart requires exact history layers")
        _int(layer.depth, "layer depth")
        if layer.depth != index:
            raise HistoryContractError("chart layers are not canonical depth order")
        if type(layer.classes) is not tuple:
            raise HistoryContractError("layer classes must be an exact immutable tuple")
        if type(layer.incoming_edges) is not tuple:
            raise HistoryContractError("layer edges must be an exact immutable tuple")
        class_count = _checked_add(
            class_count, len(layer.classes), "canonical class preflight"
        )
        edge_count = _checked_add(
            edge_count, len(layer.incoming_edges), "contribution edge preflight"
        )
        if class_count > MAX_CANONICAL_CLASSES:
            raise HistoryContractError("canonical chart class preflight exceeds a frozen cap")
        if edge_count > MAX_CONTRIBUTION_EDGES:
            raise HistoryContractError(
                "canonical chart contribution-edge preflight exceeds a frozen cap"
            )
    return class_count, edge_count


def preflight_report_bound(
    domain: FiniteTotalActionDomain,
    *,
    max_depth: int,
    duplicate_row_checks: int = 0,
) -> ReportBytePreflight:
    """Compute the frozen conservative report bound before layer allocation."""

    if type(domain) is not FiniteTotalActionDomain:
        raise HistoryContractError("report preflight requires an exact finite domain")
    domain.validate()
    _int(max_depth, "report max_depth")
    _int(duplicate_row_checks, "duplicate row checks")
    if (
        max_depth > MAX_CANONICAL_DEPTH
        or duplicate_row_checks > MAX_DUPLICATE_ROW_CHECKS
    ):
        raise HistoryContractError("report preflight input exceeds a frozen cap")
    task_count = len(domain.task_ids)
    action_count = len(domain.action_ids)
    state_count = len(domain.open_states)
    class_upper = min(task_count, state_count)
    edge_upper = 0
    previous = class_upper
    power = 1
    for _depth in range(1, max_depth + 1):
        power = _checked_mul(power, action_count, "report word power")
        raw_at_depth = _checked_mul(task_count, power, "report raw layer")
        structural = _checked_add(state_count, 2, "structural class upper")
        current = min(raw_at_depth, structural)
        class_upper = _checked_add(class_upper, current, "canonical class upper")
        edge_upper = _checked_add(
            edge_upper,
            _checked_mul(previous, action_count, "contribution edge upper"),
            "contribution edge upper",
        )
        previous = current

    signature_bytes = 0
    text_values = (
        domain.source_authority,
        domain.semantics_digest,
        domain.exactness_floor,
        *domain.task_ids,
        *domain.action_ids,
        *(row.replay_digest for row in domain.transition_rows),
    )
    try:
        for value in text_values:
            signature_bytes = _checked_add(
                signature_bytes,
                len(value.encode("utf-8", errors="strict")),
                "report signature bytes",
            )
    except UnicodeEncodeError as exc:
        raise HistoryContractError("report strings are not strict UTF-8") from exc
    for state in domain.open_states:
        signature_bytes = _checked_add(
            signature_bytes,
            len(state.identity_key)
            + len(state.full_signature)
            + len(state.response_signature),
            "report signature bytes",
        )

    report_upper = 3 * 1024 * 1024
    for count, multiplier, where in (
        (signature_bytes, 1, "report signatures"),
        (len(domain.transition_rows), 256, "report transition rows"),
        (duplicate_row_checks, 256, "report duplicate rows"),
        (class_upper, 256, "report classes"),
        (edge_upper, 64, "report contribution edges"),
    ):
        report_upper = _checked_add(
            report_upper,
            _checked_mul(count, multiplier, where),
            "report byte upper",
        )
    return ReportBytePreflight(
        domain.digest,
        max_depth,
        signature_bytes,
        len(domain.transition_rows),
        duplicate_row_checks,
        class_upper,
        edge_upper,
        report_upper,
    )


@dataclass(frozen=True)
class CanonicalHistoryChart:
    domain: FiniteTotalActionDomain
    max_depth: int
    layers: tuple[CanonicalHistoryLayer, ...]
    markov_contract: CanonicalKStateMarkovContract | None = None
    report_preflight: ReportBytePreflight | None = None
    duplicate_row_checks: int = 0
    _report_preflight_seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _int(self.duplicate_row_checks, "chart duplicate row checks")
        if self.duplicate_row_checks > MAX_DUPLICATE_ROW_CHECKS:
            raise HistoryContractError(
                "chart duplicate row checks exceed the frozen cap"
            )
        _preflight_chart_layer_snapshot_shape(self.max_depth, self.layers)
        object.__setattr__(self, "domain", _snapshot_finite_domain(self.domain))
        object.__setattr__(
            self, "markov_contract", _snapshot_markov_contract(self.markov_contract)
        )
        _validate_chart_markov_binding(self.domain, self.markov_contract)
        object.__setattr__(
            self,
            "layers",
            tuple(_snapshot_history_layer(layer) for layer in self.layers),
        )
        object.__setattr__(
            self, "report_preflight", _snapshot_report_preflight(self.report_preflight)
        )
        self._validate_content()
        _register_canonical_chart(self)

    def validate(self) -> None:
        if _canonical_chart_provenance_entry(self) is None:
            raise HistoryContractError("canonical chart semantic provenance mismatch")
        self._validate_content()

    def _validate_content(self) -> None:
        if type(self) is not CanonicalHistoryChart:
            raise HistoryContractError("CanonicalHistoryChart subclasses are forbidden")
        if type(self.domain) is not FiniteTotalActionDomain or not self.domain.sealed:
            raise HistoryContractError("chart requires a sealed exact finite domain")
        _int(self.max_depth, "max_depth")
        if self.max_depth > MAX_CANONICAL_DEPTH:
            raise HistoryContractError("canonical depth exceeds frozen cap")
        _int(self.duplicate_row_checks, "chart duplicate row checks")
        if self.duplicate_row_checks > MAX_DUPLICATE_ROW_CHECKS:
            raise HistoryContractError("chart duplicate row checks exceed the frozen cap")
        if type(self.layers) is not tuple or len(self.layers) != self.max_depth + 1:
            raise HistoryContractError("chart layers are incomplete")
        if any(type(layer) is not CanonicalHistoryLayer or layer.depth != index for index, layer in enumerate(self.layers)):
            raise HistoryContractError("chart layers are not canonical depth order")
        for layer in self.layers:
            layer.validate()
        expected_zero = _seed_layer(self.domain)
        if self.layers[0] != expected_zero:
            raise HistoryContractError("depth-zero canonical layer was not seed-derived")
        expected_previous = expected_zero
        for depth in range(1, self.max_depth + 1):
            expected_current = _derive_expected_layer(
                self.domain, expected_previous, depth
            )
            if self.layers[depth] != expected_current:
                raise HistoryContractError(
                    "canonical layer was not generation-time state-derived"
                )
            expected_previous = expected_current
        class_count = sum(len(layer.classes) for layer in self.layers)
        edge_count = sum(len(layer.incoming_edges) for layer in self.layers)
        if class_count > MAX_CANONICAL_CLASSES or edge_count > MAX_CONTRIBUTION_EDGES:
            raise HistoryContractError("canonical chart exceeds a frozen cap")
        _validate_chart_markov_binding(self.domain, self.markov_contract)
        expected_preflight = preflight_report_bound(
            self.domain,
            max_depth=self.max_depth,
            duplicate_row_checks=self.duplicate_row_checks,
        )
        if self.report_preflight is None:
            object.__setattr__(self, "report_preflight", expected_preflight)
        elif type(self.report_preflight) is not ReportBytePreflight or self.report_preflight != expected_preflight:
            raise HistoryContractError("chart report preflight was not source-derived")
        assert self.report_preflight is not None
        preflight_seal = _sha(
            {
                "schema_version": "lean-rgc-kp3d4-report-preflight-binding-v1",
                "domain_digest": self.domain.digest,
                "max_depth": self.max_depth,
                "duplicate_row_checks": self.duplicate_row_checks,
                "report_preflight": self.report_preflight.to_wire(),
            }
        )
        if hasattr(self, "_report_preflight_seal"):
            if not hmac.compare_digest(self._report_preflight_seal, preflight_seal):
                raise HistoryContractError("chart report preflight seal mutation detected")
        else:
            object.__setattr__(self, "_report_preflight_seal", preflight_seal)
        edge_index: dict[ChartEdgeIndexKey, BehavioralKeyPayload] = {}
        for layer in self.layers[1:]:
            for edge in layer.incoming_edges:
                source_payload = _behavioral_key_payload(edge.source_key)
                target_payload = _behavioral_key_payload(edge.target_key)
                token = (
                    layer.depth,
                    source_payload[0],
                    source_payload[1],
                    edge.action_id,
                )
                if token in edge_index:
                    raise HistoryContractError("duplicate generation contribution edge")
                edge_index[token] = target_payload
        task_id_set = frozenset(self.domain.task_ids)
        action_id_set = frozenset(self.domain.action_ids)
        seed_class_key_map = {
            seed.task_id: (ExactOutcomeKind.OPEN.value, seed.source_identity_key)
            for seed in self.domain.task_seeds
        }
        open_response_index = {
            state.identity_key: (
                state.full_signature,
                tuple(state.debt),
                state.response_signature,
            )
            for state in self.domain.open_states
        }
        representative_index: dict[
            ChartRepresentativeIndexKey, tuple[str, tuple[str, ...]]
        ] = {}
        for layer in self.layers:
            for row in layer.classes:
                payload = _behavioral_key_payload(row.key)
                token = (layer.depth, payload[0], payload[1])
                if token in representative_index:
                    raise HistoryContractError("duplicate canonical representative key")
                representative_index[token] = (
                    row.representative_task_id,
                    tuple(row.representative_word),
                )
        if hasattr(self, "_edge_index"):
            if (
                dict(self._edge_index) != edge_index  # type: ignore[attr-defined]
                or self._task_id_set != task_id_set  # type: ignore[attr-defined]
                or self._action_id_set != action_id_set  # type: ignore[attr-defined]
                or dict(self._seed_class_key_map) != seed_class_key_map  # type: ignore[attr-defined]
                or dict(self._open_response_index) != open_response_index  # type: ignore[attr-defined]
                or dict(self._representative_index) != representative_index  # type: ignore[attr-defined]
            ):
                raise HistoryContractError("canonical chart derived-index mutation detected")
        else:
            object.__setattr__(self, "_edge_index", MappingProxyType(edge_index))
            object.__setattr__(self, "_task_id_set", task_id_set)
            object.__setattr__(self, "_action_id_set", action_id_set)
            object.__setattr__(
                self,
                "_seed_class_key_map",
                MappingProxyType(seed_class_key_map),
            )
            object.__setattr__(
                self,
                "_open_response_index",
                MappingProxyType(open_response_index),
            )
            object.__setattr__(
                self,
                "_representative_index",
                MappingProxyType(representative_index),
            )

    @classmethod
    def build(
        cls,
        domain: FiniteTotalActionDomain,
        *,
        max_depth: int = MAX_CANONICAL_DEPTH,
        markov_contract: CanonicalKStateMarkovContract | None = None,
        duplicate_row_checks: int = 0,
    ) -> "CanonicalHistoryChart":
        if cls is not CanonicalHistoryChart:
            raise HistoryContractError("CanonicalHistoryChart subclass construction is forbidden")
        if type(domain) is not FiniteTotalActionDomain or not domain.sealed:
            raise HistoryContractError("chart construction requires a sealed domain")
        _validate_chart_markov_binding(domain, markov_contract)
        _int(max_depth, "max_depth")
        if max_depth > MAX_CANONICAL_DEPTH:
            raise HistoryContractError("canonical depth exceeds frozen cap")
        count = checked_word_count(len(domain.task_ids), len(domain.action_ids), max_depth)
        cap = MAX_RAW_DEPTH3_OCCURRENCES if max_depth <= 3 else MAX_RAW_DEPTH4_OCCURRENCES
        if count > cap:
            raise HistoryContractError("raw occurrence preflight exceeds the frozen cap")
        report_preflight = preflight_report_bound(
            domain,
            max_depth=max_depth,
            duplicate_row_checks=duplicate_row_checks,
        )

        seed_layer = _seed_layer(domain)
        layers: list[CanonicalHistoryLayer] = [seed_layer]
        total_classes = len(seed_layer.classes)
        total_edges = 0

        for depth in range(1, max_depth + 1):
            layer = _derive_expected_layer(domain, layers[-1], depth)
            total_classes = _checked_add(total_classes, len(layer.classes), "canonical class count")
            total_edges = _checked_add(total_edges, len(layer.incoming_edges), "contribution edge count")
            if total_classes > MAX_CANONICAL_CLASSES or total_edges > MAX_CONTRIBUTION_EDGES:
                raise HistoryContractError("canonical construction exceeds a frozen cap")
            layers.append(layer)
        return cls(
            domain,
            max_depth,
            tuple(layers),
            markov_contract,
            report_preflight,
            duplicate_row_checks,
        )

    @property
    def exactness_scope(self) -> str:
        if _canonical_chart_provenance_entry(self) is None:
            raise HistoryContractError("canonical chart semantic provenance mismatch")
        self.domain.validate()
        return (
            CONDITIONAL_KSTATE_MARKOV
            if (
                self.domain.exactness_floor == CONDITIONAL_KSTATE_MARKOV
                or self.markov_contract is not None
            )
            else UNCONDITIONAL_FINITE_DOMAIN
        )

    @property
    def digest(self) -> str:
        self.validate()
        return _sha(
            {
                "schema_version": HISTORY_GRAMMAR_SCHEMA,
                "domain_digest": self.domain.digest,
                "max_depth": self.max_depth,
                "exactness_scope": self.exactness_scope,
                "markov_contract": (
                    None
                    if self.markov_contract is None
                    else self.markov_contract.to_wire()
                ),
                "duplicate_row_checks": self.duplicate_row_checks,
                "report_preflight": self.report_preflight.to_wire(),  # type: ignore[union-attr]
                "layers": [
                    {
                        "depth": layer.depth,
                        "classes": [
                            [row.key.to_wire(), row.representative_task_id, list(row.representative_word), row.raw_multiplicity]
                            for row in layer.classes
                        ],
                        "edges": [
                            [edge.source_key.to_wire(), edge.action_id, edge.target_key.to_wire(), edge.witness_digest, edge.flow]
                            for edge in layer.incoming_edges
                        ],
                    }
                    for layer in self.layers
                ],
            }
        )

    def lookup(self, task_id: str, word: tuple[str, ...]) -> ExactOccurrenceResponse:
        _str(task_id, "canonical task ID")
        if task_id not in self._task_id_set:  # type: ignore[attr-defined]
            raise HistoryContractError("unknown task ID")
        _registered_word(
            word,
            self._action_id_set,  # type: ignore[attr-defined]
            "canonical query word",
        )
        if len(word) > self.max_depth:
            raise HistoryContractError("query word exceeds the canonical chart")
        return self._lookup_registered(task_id, word, _REGISTERED_LOOKUP_TOKEN)

    def _lookup_registered(
        self,
        task_id: str,
        word: tuple[str, ...],
        token: object,
    ) -> ExactOccurrenceResponse:
        """Fast path only for the sealed Hankel producer's generated words."""

        retained_provenance = _canonical_chart_provenance_entry(self)
        if retained_provenance is None:
            raise HistoryContractError(
                "canonical chart factory provenance / semantic provenance mismatch"
            )
        if token is not _REGISTERED_LOOKUP_TOKEN:
            raise HistoryContractError("registered canonical lookup authority mismatch")
        current = self._seed_class_key_map[task_id]  # type: ignore[attr-defined]
        terminal: TerminalOccurrence | None = None
        for depth, action in enumerate(word, start=1):
            try:
                target = self._edge_index[  # type: ignore[attr-defined]
                    (depth, current[0], current[1], action)
                ]
            except KeyError as exc:
                raise HistoryContractError("canonical edge is absent") from exc
            if (
                current[0] == ExactOutcomeKind.OPEN.value
                and target[0] != ExactOutcomeKind.OPEN.value
            ):
                assert current[1] is not None
                terminal = TerminalOccurrence(
                    _terminal_kind(ExactOutcomeKind(target[0])),
                    task_id,
                    current[1],
                    action,
                    word[:depth],
                )
            current = target
        if current[0] == ExactOutcomeKind.OPEN.value:
            assert current[1] is not None
            try:
                full_signature, debt, response_signature = retained_provenance[13][
                    current[1]
                ]
            except KeyError as exc:
                raise HistoryContractError(
                    "canonical OPEN response payload is absent"
                ) from exc
            return _fresh_open_response_from_primitive(
                current[1],
                full_signature,
                debt,
                response_signature,
            )
        if terminal is None:
            raise HistoryContractError("terminal class lost raw first-entry provenance")
        return ExactOccurrenceResponse.terminal_response(terminal)

    def _representative_registered(
        self,
        depth: int,
        key: BehavioralClassKey,
        token: object,
    ) -> tuple[str, tuple[str, ...]]:
        if _canonical_chart_provenance_entry(self) is None:
            raise HistoryContractError(
                "canonical chart factory provenance / semantic provenance mismatch"
            )
        if token is not _REGISTERED_LOOKUP_TOKEN:
            raise HistoryContractError("registered representative authority mismatch")
        payload = _behavioral_key_payload(key)
        try:
            return self._representative_index[  # type: ignore[attr-defined]
                (depth, payload[0], payload[1])
            ]
        except KeyError as exc:
            raise HistoryContractError("canonical representative is absent") from exc


WalkerOpenPayload = tuple[bytes, tuple[int, int, int, int, int], bytes]
WalkerTransitionPayload = tuple[str, bytes | None, str]


def _prepared_walker_snapshot_digest(
    domain_digest: str,
    task_ids: tuple[str, ...],
    action_ids: tuple[str, ...],
    open_responses: Mapping[bytes, WalkerOpenPayload],
    seeds: Mapping[str, bytes],
    rows: Mapping[tuple[bytes, str], WalkerTransitionPayload],
) -> str:
    def open_response_wire(
        identity_key: bytes, payload: WalkerOpenPayload
    ) -> dict[str, Any]:
        full_signature, debt, response_signature = payload
        state = ExactOpenState(identity_key, full_signature, debt, response_signature)
        return {
            "schema_version": "lean-rgc-kp3d4-exact-occurrence-response-v1",
            "kind": ExactOutcomeKind.OPEN.value,
            "open": {
                "identity_key": state.identity_key.hex().upper(),
                "full_signature": state.full_signature.hex().upper(),
                "debt": list(state.debt),
                "response_signature": state.response_signature.hex().upper(),
            },
            "terminal": None,
        }

    def transition_wire(
        key: tuple[bytes, str], payload: WalkerTransitionPayload
    ) -> dict[str, Any]:
        kind_value, target_identity_key, replay_digest = payload
        try:
            kind = ExactOutcomeKind(kind_value)
        except (TypeError, ValueError) as exc:
            raise HistoryContractError("walker snapshot has an invalid outcome kind") from exc
        row = SealedTransitionRow(
            key[0], key[1], kind, target_identity_key, replay_digest
        )
        return {
            "source_identity_key": row.source_identity_key.hex().upper(),
            "action_id": row.action_id,
            "outcome_kind": row.outcome_kind.value,
            "target_identity_key": (
                None
                if row.target_identity_key is None
                else row.target_identity_key.hex().upper()
            ),
            "replay_digest": row.replay_digest,
        }

    return _sha(
        {
            "schema_version": "lean-rgc-kp3d4-independent-walker-snapshot-v1",
            "domain_digest": domain_digest,
            "task_ids": list(task_ids),
            "action_ids": list(action_ids),
            "open_responses": [
                [key.hex().upper(), open_response_wire(key, open_responses[key])]
                for key in sorted(open_responses)
            ],
            "seeds": [[key, seeds[key].hex().upper()] for key in sorted(seeds)],
            "rows": [
                [key[0].hex().upper(), key[1], transition_wire(key, rows[key])]
                for key in sorted(rows)
            ],
        }
    )


@dataclass(frozen=True, init=False, eq=False)
class IndependentDomainWalker:
    """Prepared raw oracle with maps independent of the canonical chart."""

    domain_digest: str
    task_ids: tuple[str, ...]
    action_ids: tuple[str, ...]
    _task_id_set: frozenset[str]
    _action_id_set: frozenset[str]
    _open_responses: Mapping[bytes, WalkerOpenPayload]
    _seeds: Mapping[str, bytes]
    _rows: Mapping[tuple[bytes, str], WalkerTransitionPayload]
    _snapshot_digest: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise HistoryContractError(
            "IndependentDomainWalker may only be produced by prepare"
        )

    def validate(self) -> None:
        if type(self) is not IndependentDomainWalker:
            raise HistoryContractError("IndependentDomainWalker subclasses are forbidden")
        retained_provenance = _prepared_walker_provenance_entry(self)
        if retained_provenance is None:
            raise HistoryContractError("independent walker lacks factory provenance")
        _digest(self.domain_digest, "IndependentDomainWalker.domain_digest")
        if type(self.task_ids) is not tuple or type(self.action_ids) is not tuple:
            raise HistoryContractError("independent walker IDs must be exact tuples")
        for task_id in self.task_ids:
            _str(task_id, "IndependentDomainWalker.task_id")
        for action_id in self.action_ids:
            _str(action_id, "IndependentDomainWalker.action_id")
        if type(self._task_id_set) is not frozenset or type(self._action_id_set) is not frozenset:
            raise HistoryContractError("independent walker ID sets must be immutable")
        if self._task_id_set != frozenset(self.task_ids) or self._action_id_set != frozenset(self.action_ids):
            raise HistoryContractError("independent walker ID sets mismatch")
        if type(self._open_responses) is not MappingProxyType or type(self._seeds) is not MappingProxyType or type(self._rows) is not MappingProxyType:
            raise HistoryContractError("independent walker maps must be immutable")
        if (
            not self.task_ids
            or not self.action_ids
            or self.task_ids != tuple(sorted(self.task_ids))
            or self.action_ids != tuple(sorted(self.action_ids))
            or len(self.task_ids) != len(self._task_id_set)
            or len(self.action_ids) != len(self._action_id_set)
        ):
            raise HistoryContractError("independent walker IDs are not canonical")
        if len(self.task_ids) > MAX_TASK_SEEDS or len(self.action_ids) > MAX_ACTIONS:
            raise HistoryContractError("independent walker IDs exceed a frozen cap")

        state_keys: set[bytes] = set()
        for key, payload in self._open_responses.items():
            _bytes(key, "independent walker OPEN key")
            if (
                type(payload) is not tuple
                or len(payload) != 3
                or type(payload[1]) is not tuple
                or len(payload[1]) != 5
            ):
                raise HistoryContractError("independent walker OPEN payload mismatch")
            ExactOpenState(key, payload[0], payload[1], payload[2])
            if key in state_keys:
                raise HistoryContractError("independent walker has a duplicate OPEN state")
            state_keys.add(key)
        if not state_keys or len(state_keys) > MAX_OPEN_STATES:
            raise HistoryContractError("independent walker OPEN states exceed a frozen cap")

        if set(self._seeds) != self._task_id_set:
            raise HistoryContractError("independent walker task seed map mismatch")
        for task_id, state_key in self._seeds.items():
            _str(task_id, "independent walker seed task")
            _bytes(state_key, "independent walker seed state")
            if state_key not in state_keys:
                raise HistoryContractError("independent walker seed is outside the snapshot")

        expected_pairs = {
            (state_key, action_id)
            for state_key in state_keys
            for action_id in self.action_ids
        }
        if set(self._rows) != expected_pairs:
            raise HistoryContractError("independent walker transition map is not total")
        for key, payload in self._rows.items():
            if (
                type(key) is not tuple
                or len(key) != 2
                or type(payload) is not tuple
                or len(payload) != 3
            ):
                raise HistoryContractError("independent walker transition entry type mismatch")
            try:
                kind = ExactOutcomeKind(payload[0])
            except (TypeError, ValueError) as exc:
                raise HistoryContractError("independent walker outcome kind mismatch") from exc
            row = SealedTransitionRow(key[0], key[1], kind, payload[1], payload[2])
            if (
                row.outcome_kind is ExactOutcomeKind.OPEN
                and row.target_identity_key not in state_keys
            ):
                raise HistoryContractError("independent walker successor is outside the snapshot")

        _digest(self._snapshot_digest, "IndependentDomainWalker.snapshot_digest")
        expected_digest = _prepared_walker_snapshot_digest(
            self.domain_digest,
            self.task_ids,
            self.action_ids,
            self._open_responses,
            self._seeds,
            self._rows,
        )
        if not hmac.compare_digest(self._snapshot_digest, expected_digest):
            raise HistoryContractError("independent walker snapshot digest mismatch")

    @classmethod
    def prepare(cls, domain: FiniteTotalActionDomain) -> "IndependentDomainWalker":
        if cls is not IndependentDomainWalker:
            raise HistoryContractError("IndependentDomainWalker subclasses are forbidden")
        if type(domain) is not FiniteTotalActionDomain:
            raise HistoryContractError("raw walker requires an exact finite domain")
        domain.validate()
        domain_digest = domain._content_seal  # type: ignore[attr-defined]
        task_ids = tuple(domain.task_ids)
        action_ids = tuple(domain.action_ids)
        states = tuple(_snapshot_open_state(state) for state in domain.open_states)
        seeds = tuple(_snapshot_task_seed(seed) for seed in domain.task_seeds)
        rows = tuple(
            _snapshot_transition_row(row) for row in domain.transition_rows
        )
        open_responses = MappingProxyType(
            {
                state.identity_key: (
                    state.full_signature,
                    tuple(state.debt),
                    state.response_signature,
                )
                for state in states
            }
        )
        seed_map = MappingProxyType(
            {seed.task_id: seed.source_identity_key for seed in seeds}
        )
        row_map = MappingProxyType(
            {
                (row.source_identity_key, row.action_id): (
                    row.outcome_kind.value,
                    row.target_identity_key,
                    row.replay_digest,
                )
                for row in rows
            }
        )
        snapshot_digest = _prepared_walker_snapshot_digest(
            domain_digest,
            task_ids,
            action_ids,
            open_responses,
            seed_map,
            row_map,
        )
        instance = object.__new__(cls)
        object.__setattr__(instance, "domain_digest", domain_digest)
        object.__setattr__(instance, "task_ids", task_ids)
        object.__setattr__(instance, "action_ids", action_ids)
        object.__setattr__(instance, "_task_id_set", frozenset(task_ids))
        object.__setattr__(instance, "_action_id_set", frozenset(action_ids))
        object.__setattr__(instance, "_open_responses", open_responses)
        object.__setattr__(instance, "_seeds", seed_map)
        object.__setattr__(instance, "_rows", row_map)
        object.__setattr__(instance, "_snapshot_digest", snapshot_digest)
        _register_prepared_walker(instance)
        instance.validate()
        return instance

    def lookup(
        self, task_id: str, word: tuple[str, ...]
    ) -> ExactOccurrenceResponse:
        _str(task_id, "independent walker task ID")
        if task_id not in self._task_id_set:
            raise HistoryContractError("unknown task ID")
        _registered_word(word, self._action_id_set, "independent raw word")
        return self._lookup_registered(task_id, word, _REGISTERED_LOOKUP_TOKEN)

    def _lookup_registered(
        self,
        task_id: str,
        word: tuple[str, ...],
        token: object,
    ) -> ExactOccurrenceResponse:
        """Fast path only for the sealed Hankel producer's generated words."""

        retained_provenance = _prepared_walker_provenance_entry(self)
        if retained_provenance is None:
            raise HistoryContractError("independent walker lacks factory provenance")
        if token is not _REGISTERED_LOOKUP_TOKEN:
            raise HistoryContractError("registered raw lookup authority mismatch")
        current_key = self._seeds[task_id]
        terminal: TerminalOccurrence | None = None
        for offset, action in enumerate(word):
            if terminal is not None:
                continue
            kind_value, target_identity_key, _replay_digest = self._rows[
                (current_key, action)
            ]
            if kind_value == ExactOutcomeKind.OPEN.value:
                assert target_identity_key is not None
                current_key = target_identity_key
            else:
                kind = ExactOutcomeKind(kind_value)
                terminal = TerminalOccurrence(
                    _terminal_kind(kind),
                    task_id,
                    current_key,
                    action,
                    word[: offset + 1],
                )
        if terminal is not None:
            return ExactOccurrenceResponse.terminal_response(terminal)
        try:
            full_signature, debt, response_signature = retained_provenance[6][
                current_key
            ]
        except KeyError as exc:
            raise HistoryContractError(
                "independent walker OPEN response payload is absent"
            ) from exc
        return _fresh_open_response_from_primitive(
            current_key,
            full_signature,
            debt,
            response_signature,
        )


_PrimitiveTerminalEntry = tuple[bytes, str, tuple[str, ...]]
_CanonicalPrimitiveCursor = tuple[
    int,
    str,
    str,
    bytes | None,
    _PrimitiveTerminalEntry | None,
]
_RawPrimitiveCursor = tuple[
    int,
    str,
    str,
    bytes | None,
    _PrimitiveTerminalEntry | None,
]


class _CanonicalPrimitiveCursorOracle:
    """Private incremental chart walk over immutable primitive indices."""

    __slots__ = ("_max_depth", "_edge_index", "_seeds", "_open_payloads")

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise HistoryContractError(
            "canonical primitive cursor oracle requires registered preparation"
        )

    @classmethod
    def _prepare(
        cls,
        chart: CanonicalHistoryChart,
        token: object,
    ) -> "_CanonicalPrimitiveCursorOracle":
        if cls is not _CanonicalPrimitiveCursorOracle:
            raise HistoryContractError("canonical primitive cursor subclasses are forbidden")
        retained = _canonical_chart_provenance_entry(chart)
        if retained is None:
            raise HistoryContractError("canonical cursor lacks chart provenance")
        if token is not _REGISTERED_LOOKUP_TOKEN:
            raise HistoryContractError("canonical cursor authority mismatch")
        instance = object.__new__(cls)
        instance._max_depth = retained[2]
        instance._edge_index = retained[11]
        instance._seeds = retained[12]
        instance._open_payloads = retained[13]
        return instance

    def seed(self, task_id: str) -> _CanonicalPrimitiveCursor:
        try:
            kind_value, state_key = self._seeds[task_id]
        except KeyError as exc:
            raise HistoryContractError("canonical cursor task is absent") from exc
        if kind_value != ExactOutcomeKind.OPEN.value or state_key is None:
            raise HistoryContractError("canonical cursor seed is not OPEN")
        return (0, task_id, kind_value, state_key, None)

    def advance(
        self,
        cursor: _CanonicalPrimitiveCursor,
        action_id: str,
        word_left: tuple[str, ...],
        word_right: tuple[str, ...],
    ) -> _CanonicalPrimitiveCursor:
        depth, task_id, kind_value, state_key, terminal_entry = cursor
        next_depth = depth + 1
        if next_depth > self._max_depth:
            raise HistoryContractError("canonical cursor exceeded the sealed chart depth")
        try:
            target_kind, target_key = self._edge_index[
                (next_depth, kind_value, state_key, action_id)
            ]
        except KeyError as exc:
            raise HistoryContractError("canonical cursor edge is absent") from exc
        if terminal_entry is not None:
            if target_kind != kind_value or target_key is not None:
                raise HistoryContractError("canonical terminal cursor is not absorbing")
            return (next_depth, task_id, kind_value, None, terminal_entry)
        if kind_value != ExactOutcomeKind.OPEN.value or state_key is None:
            raise HistoryContractError("canonical cursor lost OPEN source state")
        if target_kind == ExactOutcomeKind.OPEN.value:
            if target_key is None:
                raise HistoryContractError("canonical cursor OPEN edge lost its target")
            return (next_depth, task_id, target_kind, target_key, None)
        if target_key is not None:
            raise HistoryContractError("canonical cursor terminal edge retained a target")
        entry_word = word_left + word_right
        if not entry_word or entry_word[-1] != action_id:
            raise HistoryContractError("canonical cursor terminal provenance mismatch")
        return (
            next_depth,
            task_id,
            target_kind,
            None,
            (state_key, action_id, entry_word),
        )

    def response(
        self, cursor: _CanonicalPrimitiveCursor
    ) -> ExactOccurrenceResponse:
        _depth, task_id, kind_value, state_key, terminal_entry = cursor
        if kind_value == ExactOutcomeKind.OPEN.value:
            if state_key is None or terminal_entry is not None:
                raise HistoryContractError("canonical OPEN cursor has invalid shape")
            try:
                full_signature, debt, response_signature = self._open_payloads[
                    state_key
                ]
            except KeyError as exc:
                raise HistoryContractError(
                    "canonical cursor OPEN response payload is absent"
                ) from exc
            return _fresh_open_response_from_primitive(
                state_key,
                full_signature,
                debt,
                response_signature,
            )
        if state_key is not None or terminal_entry is None:
            raise HistoryContractError("canonical terminal cursor has invalid shape")
        source_key, action_id, entry_word = terminal_entry
        try:
            terminal_kind = TerminalTransitionKind(kind_value)
        except ValueError as exc:
            raise HistoryContractError("canonical cursor terminal kind is invalid") from exc
        return ExactOccurrenceResponse.terminal_response(
            TerminalOccurrence(
                terminal_kind,
                task_id,
                source_key,
                action_id,
                tuple(entry_word),
            )
        )


class _RawPrimitiveCursorOracle:
    """Private incremental raw walk, independent of canonical chart indices."""

    __slots__ = ("_max_depth", "_rows", "_seeds", "_open_payloads")

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise HistoryContractError(
            "raw primitive cursor oracle requires registered preparation"
        )

    @classmethod
    def _prepare(
        cls,
        walker: IndependentDomainWalker,
        *,
        max_depth: int,
        token: object,
    ) -> "_RawPrimitiveCursorOracle":
        if cls is not _RawPrimitiveCursorOracle:
            raise HistoryContractError("raw primitive cursor subclasses are forbidden")
        retained = _prepared_walker_provenance_entry(walker)
        if retained is None:
            raise HistoryContractError("raw cursor lacks walker provenance")
        if token is not _REGISTERED_LOOKUP_TOKEN:
            raise HistoryContractError("raw cursor authority mismatch")
        _int(max_depth, "raw cursor max depth")
        if max_depth > MAX_CANONICAL_DEPTH:
            raise HistoryContractError("raw cursor depth exceeds the depth-four cap")
        instance = object.__new__(cls)
        instance._max_depth = max_depth
        instance._open_payloads = retained[6]
        instance._seeds = retained[7]
        instance._rows = retained[8]
        return instance

    def seed(self, task_id: str) -> _RawPrimitiveCursor:
        try:
            state_key = self._seeds[task_id]
        except KeyError as exc:
            raise HistoryContractError("raw cursor task is absent") from exc
        return (0, task_id, ExactOutcomeKind.OPEN.value, state_key, None)

    def advance(
        self,
        cursor: _RawPrimitiveCursor,
        action_id: str,
        word_left: tuple[str, ...],
        word_right: tuple[str, ...],
    ) -> _RawPrimitiveCursor:
        depth, task_id, kind_value, state_key, terminal_entry = cursor
        next_depth = depth + 1
        if next_depth > self._max_depth:
            raise HistoryContractError("raw cursor exceeded the sealed depth")
        if terminal_entry is not None:
            if kind_value == ExactOutcomeKind.OPEN.value or state_key is not None:
                raise HistoryContractError("raw terminal cursor has invalid shape")
            return (next_depth, task_id, kind_value, None, terminal_entry)
        if kind_value != ExactOutcomeKind.OPEN.value or state_key is None:
            raise HistoryContractError("raw cursor lost OPEN source state")
        try:
            target_kind, target_key, _replay_digest = self._rows[
                (state_key, action_id)
            ]
        except KeyError as exc:
            raise HistoryContractError("raw cursor transition is absent") from exc
        if target_kind == ExactOutcomeKind.OPEN.value:
            if target_key is None:
                raise HistoryContractError("raw cursor OPEN row lost its target")
            return (next_depth, task_id, target_kind, target_key, None)
        if target_key is not None:
            raise HistoryContractError("raw cursor terminal row retained a target")
        entry_word = word_left + word_right
        if not entry_word or entry_word[-1] != action_id:
            raise HistoryContractError("raw cursor terminal provenance mismatch")
        return (
            next_depth,
            task_id,
            target_kind,
            None,
            (state_key, action_id, entry_word),
        )

    def response(self, cursor: _RawPrimitiveCursor) -> ExactOccurrenceResponse:
        _depth, task_id, kind_value, state_key, terminal_entry = cursor
        if kind_value == ExactOutcomeKind.OPEN.value:
            if state_key is None or terminal_entry is not None:
                raise HistoryContractError("raw OPEN cursor has invalid shape")
            try:
                full_signature, debt, response_signature = self._open_payloads[
                    state_key
                ]
            except KeyError as exc:
                raise HistoryContractError(
                    "raw cursor OPEN response payload is absent"
                ) from exc
            return _fresh_open_response_from_primitive(
                state_key,
                full_signature,
                debt,
                response_signature,
            )
        if state_key is not None or terminal_entry is None:
            raise HistoryContractError("raw terminal cursor has invalid shape")
        source_key, action_id, entry_word = terminal_entry
        try:
            terminal_kind = TerminalTransitionKind(kind_value)
        except ValueError as exc:
            raise HistoryContractError("raw cursor terminal kind is invalid") from exc
        return ExactOccurrenceResponse.terminal_response(
            TerminalOccurrence(
                terminal_kind,
                task_id,
                source_key,
                action_id,
                tuple(entry_word),
            )
        )


def independent_walk(
    domain: FiniteTotalActionDomain, task_id: str, word: tuple[str, ...]
) -> ExactOccurrenceResponse:
    """Convenience raw walk; bulk callers prepare one walker and reuse it."""

    return IndependentDomainWalker.prepare(domain).lookup(task_id, word)


@dataclass(frozen=True)
class HistoryNormalForm:
    representative_task_id: str
    class_key: BehavioralClassKey
    representative_word: tuple[str, ...]
    representative_response: ExactOccurrenceResponse

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _str(
            self.representative_task_id,
            "HistoryNormalForm.representative_task_id",
        )
        if type(self.class_key) is not BehavioralClassKey:
            raise HistoryContractError("normal form requires an exact class key")
        _word(self.representative_word, "normal-form representative")
        if type(self.representative_response) is not ExactOccurrenceResponse:
            raise HistoryContractError("normal form requires an exact response")
        self.representative_response.validate()
        self.class_key.validate()


class HistoryGrammar:
    """Only exact-state merge and provenance-free terminal-tail absorption."""

    def __init__(self, chart: CanonicalHistoryChart) -> None:
        if type(chart) is not CanonicalHistoryChart:
            raise HistoryContractError("HistoryGrammar requires an exact chart")
        self._chart = chart

    def normalize(self, task_id: str, word: tuple[str, ...]) -> HistoryNormalForm:
        response = self._chart.lookup(task_id, word)
        key = _response_key(response)
        representative_task_id, representative_word = (
            self._chart._representative_registered(
                len(word), key, _REGISTERED_LOOKUP_TOKEN
            )
        )
        representative_response = self._chart.lookup(
            representative_task_id, representative_word
        )
        return HistoryNormalForm(
            representative_task_id,
            key,
            representative_word,
            representative_response,
        )

    def reconstruct(self, value: HistoryNormalForm) -> ExactOccurrenceResponse:
        if type(value) is not HistoryNormalForm:
            raise HistoryContractError("reconstruction requires an exact normal form")
        value.__post_init__()
        response = self._chart.lookup(
            value.representative_task_id, value.representative_word
        )
        if response != value.representative_response or _response_key(response) != value.class_key:
            raise HistoryContractError("normal-form witness mutation/reconstruction mismatch")
        return response

    def verify_witness(
        self, task_id: str, raw_word: tuple[str, ...], value: HistoryNormalForm
    ) -> None:
        expected = self.normalize(task_id, raw_word)
        if type(value) is not HistoryNormalForm or value != expected:
            raise HistoryContractError("history normal-form witness mutation")
        self.reconstruct(value)


@dataclass(frozen=True)
class BatchHistoryReference:
    max_depth: int
    layers: tuple[tuple[CanonicalHistoryClass, ...], ...]


def build_batch_reference(
    domain: FiniteTotalActionDomain, *, max_depth: int
) -> BatchHistoryReference:
    """Small-fixture oracle: enumerate first, then group (not production path)."""

    _int(max_depth, "batch max_depth")
    if max_depth > MAX_CANONICAL_DEPTH:
        raise HistoryContractError("batch reference exceeds the depth-four cap")
    count = checked_word_count(len(domain.task_ids), len(domain.action_ids), max_depth)
    cap = MAX_RAW_DEPTH3_OCCURRENCES if max_depth <= 3 else MAX_RAW_DEPTH4_OCCURRENCES
    if count > cap:
        raise HistoryContractError("batch reference exceeds a frozen cap")
    walker = IndependentDomainWalker.prepare(domain)
    layers: list[tuple[CanonicalHistoryClass, ...]] = []
    for depth in range(max_depth + 1):
        counts: dict[BehavioralClassKey, int] = {}
        reps: dict[BehavioralClassKey, tuple[str, tuple[str, ...]]] = {}
        for task_id in domain.task_ids:
            for word in _words(domain.action_ids, depth):
                response = walker._lookup_registered(
                    task_id, word, _REGISTERED_LOOKUP_TOKEN
                )
                key = _response_key(response)
                counts[key] = counts.get(key, 0) + 1
                # The representative of a terminal tail is its first-entry prefix.
                candidate = (
                    task_id,
                    (
                        response.terminal.entry_word
                        if response.terminal is not None
                        else word
                    ),
                )
                if key not in reps or _representative_order(*candidate) < _representative_order(*reps[key]):
                    reps[key] = candidate
        layers.append(
            tuple(
                CanonicalHistoryClass(
                    key, reps[key][0], reps[key][1], counts[key]
                )
                for key in sorted(counts, key=lambda item: item.sort_key())
            )
        )
    return BatchHistoryReference(max_depth, tuple(layers))


@dataclass(frozen=True, init=False, eq=False)
class RawNormalizedEqualityReport:
    max_depth: int
    occurrence_count: int
    complete_response_digest: str
    source_digest: str = field(repr=True)
    _source_bound_seal: str = field(repr=False, compare=False)
    equal: bool = True

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise HistoryContractError(
            "raw equality verification report may only be minted by its verifier"
        )

    def _seal_wire(self) -> dict[str, Any]:
        return {
            "schema_version": "lean-rgc-kp3d4-raw-equality-report-v1",
            "source_digest": self.source_digest,
            "max_depth": self.max_depth,
            "occurrence_count": self.occurrence_count,
            "complete_response_digest": self.complete_response_digest,
            "equal": self.equal,
        }

    def validate(self) -> None:
        if type(self) is not RawNormalizedEqualityReport:
            raise HistoryContractError("raw equality report subclasses are forbidden")
        _int(self.max_depth, "raw equality depth")
        _int(self.occurrence_count, "raw equality occurrence count", minimum=1)
        _digest(self.complete_response_digest, "complete response digest")
        if type(self.equal) is not bool or not self.equal:
            raise HistoryContractError("raw/normalized equality report must be exact true")
        _digest(self.source_digest, "raw equality source digest")
        _digest(self._source_bound_seal, "raw equality source-bound seal")
        frozen_fields = (
            self.max_depth,
            self.occurrence_count,
            self.complete_response_digest,
            self.source_digest,
            self._source_bound_seal,
            self.equal,
        )
        if not _has_frozen_report_provenance(
            _RAW_EQUALITY_REPORT_PROVENANCE, self, frozen_fields
        ):
            raise HistoryContractError(
                "raw equality source-bound report seal lacks verifier provenance"
            )
        expected_seal = _sha(self._seal_wire())
        if not hmac.compare_digest(self._source_bound_seal, expected_seal):
            raise HistoryContractError("raw equality source-bound report seal mismatch")


def _mint_raw_normalized_equality_report(
    *,
    source_digest: str,
    max_depth: int,
    occurrence_count: int,
    complete_response_digest: str,
) -> RawNormalizedEqualityReport:
    instance = object.__new__(RawNormalizedEqualityReport)
    object.__setattr__(instance, "max_depth", max_depth)
    object.__setattr__(instance, "occurrence_count", occurrence_count)
    object.__setattr__(instance, "complete_response_digest", complete_response_digest)
    object.__setattr__(instance, "equal", True)
    object.__setattr__(instance, "source_digest", source_digest)
    object.__setattr__(instance, "_source_bound_seal", _sha(instance._seal_wire()))
    _register_frozen_report(
        _RAW_EQUALITY_REPORT_PROVENANCE,
        instance,
        (
            instance.max_depth,
            instance.occurrence_count,
            instance.complete_response_digest,
            instance.source_digest,
            instance._source_bound_seal,
            instance.equal,
        ),
    )
    instance.validate()
    return instance


def verify_raw_normalized_equality(
    chart: CanonicalHistoryChart, *, max_depth: int = 3
) -> RawNormalizedEqualityReport:
    chart.validate()
    source_digest = chart.digest
    if max_depth > chart.max_depth or max_depth > 3:
        raise HistoryContractError("raw equality oracle is frozen at depth at most three")
    expected = checked_word_count(
        len(chart.domain.task_ids), len(chart.domain.action_ids), max_depth
    )
    if expected > MAX_RAW_DEPTH3_OCCURRENCES:
        raise HistoryContractError("raw equality occurrence cap exceeded")
    hasher = hashlib.sha256()
    seen = 0
    walker = IndependentDomainWalker.prepare(chart.domain)
    for depth in range(max_depth + 1):
        for task_id in chart.domain.task_ids:
            for word in _words(chart.domain.action_ids, depth):
                raw = walker._lookup_registered(
                    task_id, word, _REGISTERED_LOOKUP_TOKEN
                )
                canonical = chart._lookup_registered(
                    task_id, word, _REGISTERED_LOOKUP_TOKEN
                )
                if raw != canonical:
                    raise HistoryContractError(
                        f"raw/canonical exact response mismatch at {task_id}:{word!r}"
                    )
                hasher.update(
                    _canonical_bytes(
                        [task_id, list(word), raw.to_wire()]
                    )
                )
                hasher.update(b"\n")
                seen += 1
    if seen != expected:
        raise HistoryContractError("raw equality enumeration count mismatch")
    if not hmac.compare_digest(source_digest, chart.digest):
        raise HistoryContractError("chart changed during raw equality verification")
    return _mint_raw_normalized_equality_report(
        source_digest=source_digest,
        max_depth=max_depth,
        occurrence_count=seen,
        complete_response_digest=hasher.hexdigest().upper(),
    )


@dataclass(frozen=True, init=False, eq=False)
class FlowVerificationReport:
    max_depth: int
    layer_totals: tuple[int, ...]
    streamed_occurrences_checked: int
    exact_raw_histogram_coverage: bool
    streamed_histogram_digest: str
    source_digest: str
    _source_bound_seal: str = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise HistoryContractError(
            "flow verification report may only be minted by its verifier"
        )

    def _seal_wire(self) -> dict[str, Any]:
        return {
            "schema_version": "lean-rgc-kp3d4-flow-report-v1",
            "source_digest": self.source_digest,
            "max_depth": self.max_depth,
            "layer_totals": list(self.layer_totals),
            "streamed_occurrences_checked": self.streamed_occurrences_checked,
            "exact_raw_histogram_coverage": self.exact_raw_histogram_coverage,
            "streamed_histogram_digest": self.streamed_histogram_digest,
        }

    def validate(self) -> None:
        if type(self) is not FlowVerificationReport:
            raise HistoryContractError("flow report subclasses are forbidden")
        _int(self.max_depth, "flow max_depth")
        if type(self.layer_totals) is not tuple or len(self.layer_totals) != self.max_depth + 1:
            raise HistoryContractError("flow layer totals must be a complete exact tuple")
        for index, value in enumerate(self.layer_totals):
            _int(value, f"flow layer total {index}", minimum=1)
        _int(
            self.streamed_occurrences_checked,
            "flow streamed occurrence count",
            minimum=1,
        )
        expected = 0
        for value in self.layer_totals:
            expected = _checked_add(expected, value, "flow coverage count")
        if self.streamed_occurrences_checked != expected:
            raise HistoryContractError("flow report lacks complete raw occurrence coverage")
        if (
            type(self.exact_raw_histogram_coverage) is not bool
            or not self.exact_raw_histogram_coverage
        ):
            raise HistoryContractError("flow report must retain exact raw histogram coverage")
        _digest(self.streamed_histogram_digest, "streamed histogram digest")
        _digest(self.source_digest, "flow source digest")
        _digest(self._source_bound_seal, "flow source-bound seal")
        frozen_fields = (
            self.max_depth,
            self.layer_totals,
            self.streamed_occurrences_checked,
            self.exact_raw_histogram_coverage,
            self.streamed_histogram_digest,
            self.source_digest,
            self._source_bound_seal,
        )
        if not _has_frozen_report_provenance(
            _FLOW_REPORT_PROVENANCE, self, frozen_fields
        ):
            raise HistoryContractError(
                "flow source-bound report seal lacks verifier provenance"
            )
        expected_seal = _sha(self._seal_wire())
        if not hmac.compare_digest(self._source_bound_seal, expected_seal):
            raise HistoryContractError("flow source-bound report seal mismatch")


def _mint_flow_verification_report(
    *,
    source_digest: str,
    max_depth: int,
    layer_totals: tuple[int, ...],
    streamed_occurrences_checked: int,
    streamed_histogram_digest: str,
) -> FlowVerificationReport:
    instance = object.__new__(FlowVerificationReport)
    object.__setattr__(instance, "max_depth", max_depth)
    object.__setattr__(instance, "layer_totals", layer_totals)
    object.__setattr__(
        instance, "streamed_occurrences_checked", streamed_occurrences_checked
    )
    object.__setattr__(instance, "exact_raw_histogram_coverage", True)
    object.__setattr__(instance, "streamed_histogram_digest", streamed_histogram_digest)
    object.__setattr__(instance, "source_digest", source_digest)
    object.__setattr__(instance, "_source_bound_seal", _sha(instance._seal_wire()))
    _register_frozen_report(
        _FLOW_REPORT_PROVENANCE,
        instance,
        (
            instance.max_depth,
            instance.layer_totals,
            instance.streamed_occurrences_checked,
            instance.exact_raw_histogram_coverage,
            instance.streamed_histogram_digest,
            instance.source_digest,
            instance._source_bound_seal,
        ),
    )
    instance.validate()
    return instance


def verify_flow_conservation(chart: CanonicalHistoryChart) -> FlowVerificationReport:
    chart.validate()
    source_digest = chart.digest
    histogram_hasher = hashlib.sha256()
    totals: list[int] = []
    streamed_occurrences = 0
    walker = IndependentDomainWalker.prepare(chart.domain)
    for layer in chart.layers:
        expected_total = _checked_mul(
            len(chart.domain.task_ids),
            len(chart.domain.action_ids) ** layer.depth,
            "layer total",
        )
        if layer.raw_multiplicity != expected_total:
            raise HistoryContractError("secondary layer-total check failed")
        totals.append(expected_total)
        if layer.depth:
            flows: dict[BehavioralClassKey, int] = {}
            previous = chart.layers[layer.depth - 1]
            previous_weights = {row.key: row.raw_multiplicity for row in previous.classes}
            for edge in layer.incoming_edges:
                if edge.flow != previous_weights.get(edge.source_key):
                    raise HistoryContractError("contribution edge flow is not source-derived")
                flows[edge.target_key] = flows.get(edge.target_key, 0) + edge.flow
            if flows != {row.key: row.raw_multiplicity for row in layer.classes}:
                raise HistoryContractError("local class-flow conservation failed")
        raw_counts: dict[BehavioralClassKey, int] = {}
        for task_id in chart.domain.task_ids:
            for word in _words(chart.domain.action_ids, layer.depth):
                response = walker._lookup_registered(
                    task_id, word, _REGISTERED_LOOKUP_TOKEN
                )
                key = _response_key(response)
                raw_counts[key] = raw_counts.get(key, 0) + 1
                streamed_occurrences += 1
        canonical_counts = {row.key: row.raw_multiplicity for row in layer.classes}
        if raw_counts != canonical_counts:
            raise HistoryContractError("streamed raw histogram differs from canonical weights")
        histogram_hasher.update(
            _canonical_bytes(
                [
                    layer.depth,
                    [
                        [key.to_wire(), raw_counts[key]]
                        for key in sorted(raw_counts, key=lambda item: item.sort_key())
                    ],
                ]
            )
        )
    if not hmac.compare_digest(source_digest, chart.digest):
        raise HistoryContractError("chart changed during flow verification")
    return _mint_flow_verification_report(
        source_digest=source_digest,
        max_depth=chart.max_depth,
        layer_totals=tuple(totals),
        streamed_occurrences_checked=streamed_occurrences,
        streamed_histogram_digest=histogram_hasher.hexdigest().upper(),
    )


def verify_generation_time_equals_batch(chart: CanonicalHistoryChart) -> None:
    batch = build_batch_reference(chart.domain, max_depth=chart.max_depth)
    production = tuple(layer.classes for layer in chart.layers)
    if production != batch.layers:
        raise HistoryContractError("generation-time chart differs from batch reference")


__all__ = [
    "ACTION_GRAMMAR_SCHEMA",
    "CONDITIONAL_KSTATE_MARKOV",
    "FINITE_DOMAIN_SCHEMA",
    "HISTORY_GRAMMAR_SCHEMA",
    "MAX_ACTIONS",
    "MAX_CANONICAL_CLASSES",
    "MAX_CANONICAL_DEPTH",
    "MAX_CONTRIBUTION_EDGES",
    "MAX_DUPLICATE_ROW_CHECKS",
    "MAX_OPEN_STATES",
    "MAX_RAW_DEPTH3_OCCURRENCES",
    "MAX_RAW_DEPTH4_OCCURRENCES",
    "MAX_REPORT_BYTES",
    "MAX_SIGNATURE_BYTES",
    "MAX_SIGNED_64",
    "MAX_TASK_SEEDS",
    "MAX_TOTAL_SIGNATURE_BYTES",
    "MAX_TRANSITION_ROWS",
    "UNCONDITIONAL_FINITE_DOMAIN",
    "UNPROVED_MARKOV_STATUS",
    "BehavioralClassKey",
    "CanonicalHistoryChart",
    "CanonicalHistoryClass",
    "CanonicalHistoryLayer",
    "CanonicalKStateMarkovContract",
    "ContributionEdge",
    "ExactOccurrenceResponse",
    "ExactOpenState",
    "ExactOutcomeKind",
    "FiniteTotalActionDomain",
    "FlowVerificationReport",
    "HistoryContractError",
    "HistoryGrammar",
    "HistoryNormalForm",
    "IndependentDomainWalker",
    "RawNormalizedEqualityReport",
    "ReportBytePreflight",
    "SealedTransitionRow",
    "TaskSeed",
    "TerminalOccurrence",
    "TerminalTransitionKind",
    "build_finite_total_action_domain",
    "checked_word_count",
    "independent_walk",
    "preflight_report_bound",
    "verify_flow_conservation",
    "verify_generation_time_equals_batch",
    "verify_raw_normalized_equality",
]
