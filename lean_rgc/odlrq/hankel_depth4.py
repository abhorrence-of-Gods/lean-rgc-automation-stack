"""Exact raw-coordinate Hankel construction through total cutoff four.

This module is intentionally independent of the historical U05 evaluator and
of native Lean.  Its sealed producer accepts one exact canonical-history chart
and internally prepares a separately implemented raw transition walker.  Every
raw coordinate is compared before its seven response channels enter the
retained matrix.

Only exact integer/rational operations are used.  In particular, this module
does not compute a floating-point conditioning diagnostic; the official value
for this phase is fixed to ``None`` with an explicit censor string.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
from math import ceil, floor, gcd
from typing import Any, Iterable, Sequence
import weakref

from .contracts import StrictContractError
from .history_normal_form import (
    CanonicalHistoryChart,
    ExactOpenState,
    ExactOccurrenceResponse,
    ExactOutcomeKind,
    IndependentDomainWalker,
    _CanonicalPrimitiveCursorOracle,
    _REGISTERED_LOOKUP_TOKEN,
    _RawPrimitiveCursorOracle,
)


MAX_SIGNED_64 = (1 << 63) - 1
MAX_RAW_HANKEL_CELLS = 1_000_000
MAX_RAW_DEPTH3_OCCURRENCES = 15_000
MAX_RAW_DEPTH4_OCCURRENCES = 150_000
MAX_EXACT_RANK = 64
RANK_LOWER_BOUND_SIZE = MAX_EXACT_RANK + 1
MAX_EXACT_COEFFICIENT_BITS = 8_192
MAX_RESPONSE_DIGEST_CACHE = 1_024

UNCONDITIONAL_FINITE_DOMAIN = "UNCONDITIONAL_FINITE_DOMAIN"
CONDITIONAL_KSTATE_MARKOV = "CONDITIONAL_KSTATE_MARKOV"
EXACTNESS_SCOPES = frozenset(
    {UNCONDITIONAL_FINITE_DOMAIN, CONDITIONAL_KSTATE_MARKOV}
)

RESPONSE_CHANNELS = (
    "closed_indicator",
    "sink_indicator",
    "open_goal_count",
    "open_unassigned_mvar_count",
    "pending_typeclass_count",
    "carrier_atom_count",
    "expression_node_count",
)

OFFICIAL_CONDITIONING = None
OFFICIAL_CONDITIONING_CENSOR = "NOT_ATTEMPTED_IN_THIS_PHASE"

HANKEL_SCHEMA = "lean-rgc-odlrq-exact-raw-coordinate-hankel-v1"
RANK_CERTIFICATE_SCHEMA = "lean-rgc-odlrq-exact-rank-certificate-v1"
_PRIVATE_RANK_FIXTURE_TOKEN = object()

# Affirmative evidence objects use an identity registry rather than a bearer
# token retained on the instance.  A public caller can copy every visible
# field, but cannot enroll the copied identity.  Weak references prevent the
# registry from extending the lifetime of large H4 matrices.
_FACTORY_REGISTRIES: dict[
    type[Any], dict[int, tuple[weakref.ReferenceType[Any], str]]
] = {}
_PENDING_FACTORY_IDENTITIES: dict[int, tuple[object, type[Any]]] = {}


class _WeakReferenceableEvidence:
    """Python 3.10-compatible weak-reference slot for slotted evidence records."""

    __slots__ = ("__weakref__",)


def _factory_construct(exact_type: type[Any], /, **fields: Any) -> Any:
    """Run one generated dataclass constructor under identity-bound authority."""

    instance = object.__new__(exact_type)
    object_id = id(instance)
    if object_id in _PENDING_FACTORY_IDENTITIES:
        raise AssertionError("factory identity collision")
    _PENDING_FACTORY_IDENTITIES[object_id] = (instance, exact_type)
    try:
        exact_type.__init__(instance, **fields)
    finally:
        _PENDING_FACTORY_IDENTITIES.pop(object_id, None)
    registered = _FACTORY_REGISTRIES.get(exact_type, {}).get(object_id)
    if registered is None or registered[0]() is not instance:
        raise AssertionError("factory constructor failed to register exact evidence")
    return instance


def _attest_factory_identity(instance: object, semantic_snapshot: str, where: str) -> None:
    """Enroll a pending factory identity or verify an already enrolled one."""

    exact_type = type(instance)
    object_id = id(instance)
    registry = _FACTORY_REGISTRIES.setdefault(exact_type, {})
    pending = _PENDING_FACTORY_IDENTITIES.get(object_id)
    if pending is not None:
        if pending[0] is not instance or pending[1] is not exact_type:
            raise StrictContractError(f"{where} factory identity mismatch")

        def forget(
            dead_reference: weakref.ReferenceType[Any],
            *,
            retained_id: int = object_id,
            retained_type: type[Any] = exact_type,
        ) -> None:
            retained_registry = _FACTORY_REGISTRIES.get(retained_type)
            if retained_registry is None:
                return
            retained = retained_registry.get(retained_id)
            if retained is not None and retained[0] is dead_reference:
                retained_registry.pop(retained_id, None)

        registry[object_id] = (weakref.ref(instance, forget), semantic_snapshot)
        return
    retained = registry.get(object_id)
    if retained is None or retained[0]() is not instance:
        raise StrictContractError(f"{where} lacks factory provenance")
    if retained[1] != semantic_snapshot:
        raise StrictContractError(f"{where} immutable semantic binding mismatch")


def _registered_semantic_snapshot(instance: object, where: str) -> str:
    registry = _FACTORY_REGISTRIES.get(type(instance), {})
    retained = registry.get(id(instance))
    if retained is None or retained[0]() is not instance:
        raise StrictContractError(f"{where} lacks factory provenance")
    return retained[1]

ActionWord = tuple[str, ...]


class ExactRankCertificateKind(str, Enum):
    """The two frozen outcomes of the bounded exact-rank screen."""

    COMPLETE_SPAN = "COMPLETE_SPAN"
    RANK_AT_LEAST_65 = "RANK_AT_LEAST_65"


def _strict_integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > MAX_SIGNED_64:
        raise StrictContractError(
            f"{where} must be an exact signed-64 integer >= {minimum}"
        )
    return value


def _strict_nonempty_string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} is not strict UTF-8") from exc
    return value


def _strict_digest(value: Any, where: str) -> str:
    result = _strict_nonempty_string(value, where)
    if len(result) != 64 or any(character not in "0123456789ABCDEF" for character in result):
        raise StrictContractError(f"{where} must be an uppercase SHA-256 digest")
    return result


def _strict_scope(value: Any) -> str:
    if type(value) is not str or value not in EXACTNESS_SCOPES:
        raise StrictContractError("unknown exactness scope")
    return value


def _strict_word(value: Any, where: str) -> ActionWord:
    if type(value) is not tuple:
        raise StrictContractError(f"{where} must be an exact tuple")
    for index, action_id in enumerate(value):
        _strict_nonempty_string(action_id, f"{where}[{index}]")
    return value


def _strict_ids(value: Any, where: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise StrictContractError(f"{where} must be a nonempty exact tuple")
    result = tuple(
        _strict_nonempty_string(item, f"{where}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise StrictContractError(f"{where} contains a duplicate")
    return result


def _checked_add(left: int, right: int, where: str) -> int:
    _strict_integer(left, f"{where} left")
    _strict_integer(right, f"{where} right")
    if left > MAX_SIGNED_64 - right:
        raise StrictContractError(f"D4_RESOURCE_BLOCKED: signed-64 overflow in {where}")
    return left + right


def _checked_mul(left: int, right: int, where: str) -> int:
    _strict_integer(left, f"{where} left")
    _strict_integer(right, f"{where} right")
    if left and right > MAX_SIGNED_64 // left:
        raise StrictContractError(f"D4_RESOURCE_BLOCKED: signed-64 overflow in {where}")
    return left * right


def _checked_geometric_sum(base: int, depth: int, where: str) -> int:
    _strict_integer(base, f"{where} base", minimum=1)
    _strict_integer(depth, f"{where} depth")
    total = 1
    power = 1
    for index in range(1, depth + 1):
        power = _checked_mul(power, base, f"{where} power {index}")
        total = _checked_add(total, power, f"{where} sum {index}")
    return total


def _canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return text.encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StrictContractError("value is not strict canonical JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


@dataclass(frozen=True, slots=True)
class HankelDimensions:
    cutoff: int
    prefix_depth: int
    suffix_depth: int
    n_rows: int
    n_suffixes: int
    n_columns: int
    n_word_coordinates: int
    n_cells: int
    raw_words_through_cutoff: int

    def __post_init__(self) -> None:
        cutoff = _strict_integer(self.cutoff, "dimension cutoff", minimum=1)
        if cutoff > 4:
            raise StrictContractError("dimension cutoff must be at most four")
        _strict_integer(self.prefix_depth, "dimension prefix depth")
        _strict_integer(self.suffix_depth, "dimension suffix depth")
        if self.prefix_depth != floor(cutoff / 2):
            raise StrictContractError("dimension prefix depth mismatch")
        if self.suffix_depth != ceil(cutoff / 2):
            raise StrictContractError("dimension suffix depth mismatch")
        for value, where in (
            (self.n_rows, "dimension rows"),
            (self.n_suffixes, "dimension suffixes"),
            (self.n_columns, "dimension columns"),
            (self.n_word_coordinates, "dimension word coordinates"),
            (self.n_cells, "dimension cells"),
            (self.raw_words_through_cutoff, "dimension raw words"),
        ):
            _strict_integer(value, where, minimum=1)
        if self.n_columns != self.n_suffixes * len(RESPONSE_CHANNELS):
            raise StrictContractError("dimension column/channel mismatch")
        if self.n_word_coordinates != self.n_rows * self.n_suffixes:
            raise StrictContractError("dimension word-coordinate mismatch")
        if self.n_cells != self.n_rows * self.n_columns:
            raise StrictContractError("dimension cell mismatch")


def preflight_hankel_dimensions(
    *,
    n_tasks: int,
    n_actions: int,
    cutoff: int,
) -> HankelDimensions:
    """Check all input-only D1--D4 arithmetic before word generation.

    The function performs signed-64 operations explicitly and rejects the cell
    and raw-occurrence envelopes before a caller can invoke an oracle or
    allocate a coordinate table.
    """

    n_tasks = _strict_integer(n_tasks, "task count", minimum=1)
    n_actions = _strict_integer(n_actions, "action count", minimum=1)
    cutoff = _strict_integer(cutoff, "cutoff", minimum=1)
    if cutoff > 4:
        raise StrictContractError("cutoff must be one of 1, 2, 3, 4")
    raw_occurrence_cap = (
        MAX_RAW_DEPTH4_OCCURRENCES
        if cutoff == 4
        else MAX_RAW_DEPTH3_OCCURRENCES
    )

    prefix_depth = floor(cutoff / 2)
    suffix_depth = ceil(cutoff / 2)
    prefix_count = _checked_geometric_sum(
        n_actions, prefix_depth, "prefix geometric sum"
    )
    suffix_count = _checked_geometric_sum(
        n_actions, suffix_depth, "suffix geometric sum"
    )
    n_rows = _checked_mul(n_tasks, prefix_count, "row count")
    n_columns = _checked_mul(
        suffix_count, len(RESPONSE_CHANNELS), "column count"
    )
    n_word_coordinates = _checked_mul(
        n_rows, suffix_count, "word-coordinate count"
    )
    n_cells = _checked_mul(n_rows, n_columns, "cell count")
    raw_words_through_cutoff = _checked_mul(
        n_tasks,
        _checked_geometric_sum(n_actions, cutoff, "raw-word geometric sum"),
        "raw word count",
    )
    if raw_words_through_cutoff > raw_occurrence_cap:
        raise StrictContractError(
            "D4_RESOURCE_BLOCKED: raw occurrence cap exceeded before word generation"
        )
    if n_cells > MAX_RAW_HANKEL_CELLS:
        raise StrictContractError(
            "D4_RESOURCE_BLOCKED: Hankel cell cap exceeded before construction"
        )
    return HankelDimensions(
        cutoff=cutoff,
        prefix_depth=prefix_depth,
        suffix_depth=suffix_depth,
        n_rows=n_rows,
        n_suffixes=suffix_count,
        n_columns=n_columns,
        n_word_coordinates=n_word_coordinates,
        n_cells=n_cells,
        raw_words_through_cutoff=raw_words_through_cutoff,
    )


def _action_words(action_ids: tuple[str, ...], max_depth: int) -> tuple[ActionWord, ...]:
    """Generate words in frozen depth-major, alphabet-major order."""

    words: list[ActionWord] = [()]
    layer: tuple[ActionWord, ...] = ((),)
    for _ in range(max_depth):
        layer = tuple(prefix + (action,) for prefix in layer for action in action_ids)
        words.extend(layer)
    return tuple(words)


def _word_trie_steps(
    words: tuple[ActionWord, ...],
) -> tuple[tuple[int, str] | None, ...]:
    """Bind each depth-major word to its already-emitted parent coordinate."""

    if not words or words[0] != ():
        raise StrictContractError("word trie must begin at the empty word")
    indices: dict[ActionWord, int] = {(): 0}
    steps: list[tuple[int, str] | None] = [None]
    for index, word in enumerate(words[1:], start=1):
        if type(word) is not tuple or not word:
            raise StrictContractError("word trie contains an invalid coordinate")
        parent = word[:-1]
        parent_index = indices.get(parent)
        if parent_index is None or parent_index >= index:
            raise StrictContractError("word trie parent was not emitted first")
        action_id = word[-1]
        if type(action_id) is not str or not action_id:
            raise StrictContractError("word trie action must be an exact string")
        if word in indices:
            raise StrictContractError("word trie contains a duplicate coordinate")
        indices[word] = index
        steps.append((parent_index, action_id))
    return tuple(steps)


def _primitive_trie_transition_count(
    dimensions: HankelDimensions, *, n_tasks: int
) -> int:
    """Exact per-authority transition count for the retained trie traversal."""

    if type(dimensions) is not HankelDimensions:
        raise StrictContractError("trie transition count requires exact dimensions")
    dimensions.__post_init__()
    n_tasks = _strict_integer(n_tasks, "trie task count", minimum=1)
    if dimensions.n_rows % n_tasks:
        raise StrictContractError("trie row count is not task-divisible")
    prefix_count = dimensions.n_rows // n_tasks
    prefix_transitions = _checked_mul(
        n_tasks, prefix_count - 1, "prefix trie transitions"
    )
    suffix_transitions = _checked_mul(
        dimensions.n_rows,
        dimensions.n_suffixes - 1,
        "suffix trie transitions",
    )
    return _checked_add(
        prefix_transitions, suffix_transitions, "primitive trie transitions"
    )


@dataclass(frozen=True, slots=True)
class RawHankelRowKey:
    task_id: str
    prefix_word: ActionWord

    def __post_init__(self) -> None:
        _strict_nonempty_string(self.task_id, "row task id")
        _strict_word(self.prefix_word, "row prefix")

    def to_wire(self) -> list[Any]:
        self.__post_init__()
        return [self.task_id, list(self.prefix_word)]


@dataclass(frozen=True, slots=True)
class RawHankelColumnKey:
    suffix_word: ActionWord
    channel: str

    def __post_init__(self) -> None:
        _strict_word(self.suffix_word, "column suffix")
        if type(self.channel) is not str or self.channel not in RESPONSE_CHANNELS:
            raise StrictContractError("unknown response channel")

    def to_wire(self) -> list[Any]:
        self.__post_init__()
        return [list(self.suffix_word), self.channel]


@dataclass(frozen=True, slots=True)
class RawCoordinateEqualityReport(_WeakReferenceableEvidence):
    cutoff: int
    word_coordinates_checked: int
    channel_cells_checked: int
    exact_response_records_equal: bool
    response_coordinate_digest: str
    matrix_digest: str

    def __post_init__(self) -> None:
        _strict_integer(self.cutoff, "equality cutoff", minimum=1)
        _strict_integer(
            self.word_coordinates_checked, "word-coordinate check count", minimum=1
        )
        _strict_integer(
            self.channel_cells_checked, "channel-cell check count", minimum=1
        )
        if type(self.exact_response_records_equal) is not bool:
            raise StrictContractError("record-equality flag must be an exact bool")
        if not self.exact_response_records_equal:
            raise StrictContractError("an unequal raw-coordinate report cannot be retained")
        _strict_digest(
            self.response_coordinate_digest, "equality response-coordinate digest"
        )
        _strict_digest(self.matrix_digest, "equality matrix digest")
        _attest_factory_identity(
            self,
            _sha256(
                {
                    "schema": "lean-rgc-odlrq-raw-coordinate-equality-authority-v1",
                    "cutoff": self.cutoff,
                    "word_coordinates_checked": self.word_coordinates_checked,
                    "channel_cells_checked": self.channel_cells_checked,
                    "exact_response_records_equal": self.exact_response_records_equal,
                    "response_coordinate_digest": self.response_coordinate_digest,
                    "matrix_digest": self.matrix_digest,
                }
            ),
            "raw-coordinate equality report",
        )

    def validate(self) -> None:
        self.__post_init__()


def _matrix_binding_wire(
    *,
    cutoff: int,
    source_digest: str,
    exactness_scope: str,
    row_keys: Sequence[RawHankelRowKey],
    suffix_words: Sequence[ActionWord],
    matrix: Sequence[Sequence[int]],
    response_coordinate_digest: str,
) -> dict[str, Any]:
    return {
        "schema": HANKEL_SCHEMA,
        "cutoff": cutoff,
        "source_digest": source_digest,
        "exactness_scope": exactness_scope,
        "rows": [key.to_wire() for key in row_keys],
        "suffixes": [list(word) for word in suffix_words],
        "channels": list(RESPONSE_CHANNELS),
        "matrix": [list(row) for row in matrix],
        "response_coordinate_digest": response_coordinate_digest,
        "conditioning": OFFICIAL_CONDITIONING,
        "conditioning_censor": OFFICIAL_CONDITIONING_CENSOR,
    }


def _row_coordinate_digest(row_keys: Sequence[RawHankelRowKey]) -> str:
    return _sha256(
        {
            "schema": "lean-rgc-odlrq-raw-hankel-rows-v1",
            "rows": [key.to_wire() for key in row_keys],
        }
    )


def _column_coordinate_digest(suffix_words: Sequence[ActionWord]) -> str:
    return _sha256(
        {
            "schema": "lean-rgc-odlrq-raw-hankel-columns-v1",
            "columns": [
                RawHankelColumnKey(word, channel).to_wire()
                for word in suffix_words
                for channel in RESPONSE_CHANNELS
            ],
        }
    )


def _strict_matrix_value(value: Any, where: str) -> int:
    if type(value) is not int or value < -MAX_SIGNED_64 or value > MAX_SIGNED_64:
        raise StrictContractError(f"{where} must be an exact signed-64 integer")
    return value


@dataclass(frozen=True, slots=True)
class ExactRawCoordinateHankel(_WeakReferenceableEvidence):
    """A retained exact raw-coordinate matrix with sealed digest bindings."""

    cutoff: int
    source_digest: str
    exactness_scope: str
    row_keys: tuple[RawHankelRowKey, ...]
    suffix_words: tuple[ActionWord, ...]
    matrix: tuple[tuple[int, ...], ...]
    dimensions: HankelDimensions
    row_coordinate_digest: str
    column_coordinate_digest: str
    response_coordinate_digest: str
    matrix_digest: str
    equality_report: RawCoordinateEqualityReport
    conditioning: None = OFFICIAL_CONDITIONING
    conditioning_censor: str = OFFICIAL_CONDITIONING_CENSOR

    def __post_init__(self) -> None:
        self.validate()

    @property
    def column_keys(self) -> tuple[RawHankelColumnKey, ...]:
        return tuple(
            RawHankelColumnKey(word, channel)
            for word in self.suffix_words
            for channel in RESPONSE_CHANNELS
        )

    def validate(self) -> None:
        cutoff = _strict_integer(self.cutoff, "Hankel cutoff", minimum=1)
        if cutoff > 4:
            raise StrictContractError("Hankel cutoff must be at most four")
        source_digest = _strict_digest(self.source_digest, "Hankel source digest")
        exactness_scope = _strict_scope(self.exactness_scope)
        if type(self.row_keys) is not tuple or not self.row_keys:
            raise StrictContractError("row keys must be a nonempty exact tuple")
        if type(self.suffix_words) is not tuple or not self.suffix_words:
            raise StrictContractError("suffix words must be a nonempty exact tuple")
        if type(self.matrix) is not tuple or len(self.matrix) != len(self.row_keys):
            raise StrictContractError("matrix row count disagrees with raw coordinates")
        if type(self.dimensions) is not HankelDimensions:
            raise StrictContractError("dimensions must be an exact HankelDimensions")
        self.dimensions.__post_init__()
        for key in self.row_keys:
            if type(key) is not RawHankelRowKey:
                raise StrictContractError("row key has an inexact type")
            key.__post_init__()
        for index, word in enumerate(self.suffix_words):
            _strict_word(word, f"suffix word {index}")
        width = len(self.suffix_words) * len(RESPONSE_CHANNELS)
        for row_index, row in enumerate(self.matrix):
            if type(row) is not tuple or len(row) != width:
                raise StrictContractError("matrix must be exact and rectangular")
            for column_index, value in enumerate(row):
                if (
                    type(value) is not int
                    or value < -MAX_SIGNED_64
                    or value > MAX_SIGNED_64
                ):
                    raise StrictContractError(
                        f"matrix[{row_index}][{column_index}] must be an exact signed-64 integer"
                    )
        if self.dimensions.cutoff != cutoff:
            raise StrictContractError("dimension cutoff mismatch")
        if (
            self.dimensions.n_rows != len(self.row_keys)
            or self.dimensions.n_suffixes != len(self.suffix_words)
            or self.dimensions.n_columns != width
            or self.dimensions.n_word_coordinates
            != len(self.row_keys) * len(self.suffix_words)
            or self.dimensions.n_cells != len(self.row_keys) * width
        ):
            raise StrictContractError("retained matrix dimensions are inconsistent")
        expected_rows = _row_coordinate_digest(self.row_keys)
        expected_columns = _column_coordinate_digest(self.suffix_words)
        response_coordinate_digest = _strict_digest(
            self.response_coordinate_digest, "Hankel response-coordinate digest"
        )
        expected_matrix = _sha256(
            _matrix_binding_wire(
                cutoff=cutoff,
                source_digest=source_digest,
                exactness_scope=exactness_scope,
                row_keys=self.row_keys,
                suffix_words=self.suffix_words,
                matrix=self.matrix,
                response_coordinate_digest=response_coordinate_digest,
            )
        )
        if self.row_coordinate_digest != expected_rows:
            raise StrictContractError("row-coordinate digest mismatch")
        if self.column_coordinate_digest != expected_columns:
            raise StrictContractError("column-coordinate digest mismatch")
        if self.matrix_digest != expected_matrix:
            raise StrictContractError("matrix digest mismatch")
        if type(self.equality_report) is not RawCoordinateEqualityReport:
            raise StrictContractError("missing exact raw-coordinate equality report")
        self.equality_report.validate()
        if (
            self.equality_report.cutoff != cutoff
            or self.equality_report.word_coordinates_checked
            != self.dimensions.n_word_coordinates
            or self.equality_report.channel_cells_checked != self.dimensions.n_cells
            or self.equality_report.response_coordinate_digest
            != response_coordinate_digest
            or self.equality_report.matrix_digest != expected_matrix
        ):
            raise StrictContractError("raw-coordinate equality report mismatch")
        if self.conditioning is not None:
            raise StrictContractError("official conditioning must be exactly null")
        if self.conditioning_censor != OFFICIAL_CONDITIONING_CENSOR:
            raise StrictContractError("official conditioning censor mismatch")
        _attest_factory_identity(
            self,
            _sha256(
                {
                    "schema": "lean-rgc-odlrq-retained-hankel-authority-v1",
                    "cutoff": cutoff,
                    "source_digest": source_digest,
                    "exactness_scope": exactness_scope,
                    "row_coordinate_digest": self.row_coordinate_digest,
                    "column_coordinate_digest": self.column_coordinate_digest,
                    "response_coordinate_digest": response_coordinate_digest,
                    "matrix_digest": self.matrix_digest,
                    "dimensions": {
                        "cutoff": self.dimensions.cutoff,
                        "prefix_depth": self.dimensions.prefix_depth,
                        "suffix_depth": self.dimensions.suffix_depth,
                        "n_rows": self.dimensions.n_rows,
                        "n_suffixes": self.dimensions.n_suffixes,
                        "n_columns": self.dimensions.n_columns,
                        "n_word_coordinates": self.dimensions.n_word_coordinates,
                        "n_cells": self.dimensions.n_cells,
                        "raw_words_through_cutoff": self.dimensions.raw_words_through_cutoff,
                    },
                    "equality_report_snapshot": _registered_semantic_snapshot(
                        self.equality_report, "raw-coordinate equality report"
                    ),
                    "conditioning": self.conditioning,
                    "conditioning_censor": self.conditioning_censor,
                }
            ),
            "retained Hankel",
        )


OpenResponseCacheKey = tuple[bytes, bytes, tuple[int, int, int, int, int], bytes]


def _open_response_cache_key(
    response: ExactOccurrenceResponse,
) -> OpenResponseCacheKey | None:
    # ``response`` was freshly minted by one of the two sealed lookup
    # authorities, whose exact constructor already validated the complete
    # record.  Repeat only the cheap shape check here: recursively validating
    # the same immutable state at every D4 coordinate otherwise dominates the
    # bounded exhaustive audit without adding an independent check.
    if type(response.kind) is not ExactOutcomeKind:
        raise StrictContractError("exact response has an inexact outcome kind")
    state = response.open_state
    if state is None:
        if response.kind is ExactOutcomeKind.OPEN:
            raise StrictContractError("OPEN response lost its exact state")
        return None
    if (
        response.kind is not ExactOutcomeKind.OPEN
        or type(state) is not ExactOpenState
        or response.terminal is not None
    ):
        raise StrictContractError("exact OPEN response has an invalid shape")
    return (
        state.identity_key,
        state.full_signature,
        state.debt,
        state.response_signature,
    )


def _serialize_exact_response(
    response: ExactOccurrenceResponse,
    cache: dict[OpenResponseCacheKey, tuple[bytes, str]],
    where: str,
) -> tuple[bytes, str]:
    """Validate and serialize one exact response under a side-local cache.

    Canonical and raw callers use distinct caches.  Cache keys are the complete
    exact OPEN record, never caller-defined ``__eq__``/``__hash__`` behavior;
    terminal occurrences are not cached because their raw provenance differs.
    """

    if type(response) is not ExactOccurrenceResponse:
        raise StrictContractError(f"{where} must be an exact ExactOccurrenceResponse")
    cache_key = _open_response_cache_key(response)
    if cache_key is not None:
        retained = cache.get(cache_key)
        if retained is not None:
            return retained
    wire = response.to_wire()
    if type(wire) is not dict:
        raise StrictContractError(f"{where} wire must be an exact object")
    canonical_wire = _canonical_bytes(wire)
    response_digest = hashlib.sha256(
        b"lean-rgc-odlrq-exact-occurrence-response-digest-v1\x00"
        + canonical_wire
    ).hexdigest().upper()
    retained = (canonical_wire, response_digest)
    if cache_key is not None:
        if len(cache) >= MAX_RESPONSE_DIGEST_CACHE:
            raise StrictContractError("OPEN response cache exceeds the frozen state cap")
        cache[cache_key] = retained
    return retained


class _ResponseCoordinateHasher:
    def __init__(self) -> None:
        self._hash = hashlib.sha256()
        self._hash.update(b"lean-rgc-odlrq-response-coordinate-stream-v1\x00")
        self._text_cache: dict[str, bytes] = {}
        self._word_cache: dict[ActionWord, bytes] = {}
        self._digest_cache: dict[str, bytes] = {}

    def update(
        self,
        task_id: str,
        prefix: ActionWord,
        suffix: ActionWord,
        response_digest: str,
    ) -> None:
        def framed_text(value: str) -> bytes:
            framed = self._text_cache.get(value)
            if framed is None:
                # The builder validated every task/action identifier before it
                # generated these private coordinates.
                payload = value.encode("utf-8", errors="strict")
                framed = len(payload).to_bytes(8, "big", signed=False) + payload
                self._text_cache[value] = framed
            return framed

        def framed_word(word: ActionWord) -> bytes:
            framed = self._word_cache.get(word)
            if framed is None:
                framed = len(word).to_bytes(8, "big", signed=False) + b"".join(
                    framed_text(action_id) for action_id in word
                )
                self._word_cache[word] = framed
            return framed

        digest_bytes = self._digest_cache.get(response_digest)
        if digest_bytes is None:
            # Every digest is minted by _sha256 immediately above this call.
            digest_bytes = bytes.fromhex(response_digest)
            if len(self._digest_cache) < MAX_RESPONSE_DIGEST_CACHE:
                self._digest_cache[response_digest] = digest_bytes
        self._hash.update(
            b"\x01"
            + framed_text(task_id)
            + framed_word(prefix)
            + framed_word(suffix)
            + digest_bytes
        )

    def hexdigest(self) -> str:
        return self._hash.hexdigest().upper()


def _project_response(
    response: ExactOccurrenceResponse, where: str
) -> tuple[int, ...]:
    if type(response) is not ExactOccurrenceResponse:
        raise StrictContractError(f"{where} must be an exact ExactOccurrenceResponse")
    # Complete record validation and serialization precede projection in the
    # sealed builder.  Project directly from the immutable exact record so the
    # exhaustive D4 audit does not recursively revalidate it twice more.
    if response.kind is ExactOutcomeKind.CLOSED:
        values = (1, 0, 0, 0, 0, 0, 0)
    elif response.kind is ExactOutcomeKind.SINK:
        values = (0, 1, 0, 0, 0, 0, 0)
    elif (
        response.kind is ExactOutcomeKind.OPEN
        and type(response.open_state) is ExactOpenState
        and response.terminal is None
    ):
        values = (0, 0, *response.open_state.debt)
    else:
        raise StrictContractError(f"{where} has an invalid exact response shape")
    # OPEN debt was already checked as an exact signed-64 5-tuple when the
    # sealed domain was admitted; the two terminal projections are literals.
    # Re-looping over seven cells at every raw coordinate would only repeat
    # that same authority check.  The builder still compares the two complete
    # seven-tuples for every coordinate below.
    return values


def build_exact_raw_coordinate_hankel(
    chart: CanonicalHistoryChart,
    *,
    cutoff: int,
) -> ExactRawCoordinateHankel:
    """Build a sealed D1--D4 matrix from one exact canonical-history chart.

    Task/action coordinates, source digest, and exactness scope are derived
    from the chart.  The raw oracle is an internally prepared, separately
    implemented ``IndependentDomainWalker``; arbitrary callables cannot mint a
    retained matrix.  Frozen caps are checked before preparing that walker,
    generating words, or allocating a matrix.
    """

    if type(chart) is not CanonicalHistoryChart:
        raise StrictContractError("sealed Hankel construction requires an exact CanonicalHistoryChart")
    chart.validate()
    if type(cutoff) is not int or cutoff < 1 or cutoff > chart.max_depth:
        raise StrictContractError("Hankel cutoff must be within the sealed chart depth")
    task_ids = _strict_ids(chart.domain.task_ids, "chart task ids")
    action_ids = _strict_ids(chart.domain.action_ids, "chart action ids")
    if task_ids != tuple(sorted(task_ids)) or action_ids != tuple(sorted(action_ids)):
        raise StrictContractError("chart task/action coordinates are not canonical")
    dimensions = preflight_hankel_dimensions(
        n_tasks=len(task_ids),
        n_actions=len(action_ids),
        cutoff=cutoff,
    )
    walker = IndependentDomainWalker.prepare(chart.domain)
    if type(walker) is not IndependentDomainWalker:
        raise StrictContractError("prepared raw walker has an inexact type")
    if walker.domain_digest != chart.domain.digest:
        raise StrictContractError("prepared raw walker/domain binding mismatch")
    return _build_exact_raw_coordinate_hankel(chart, walker, dimensions)


def _build_exact_raw_coordinate_hankel(
    chart: CanonicalHistoryChart,
    walker: IndependentDomainWalker,
    dimensions: HankelDimensions,
) -> ExactRawCoordinateHankel:
    """Private sealed producer after public preflight and walker preparation."""

    if type(chart) is not CanonicalHistoryChart or type(walker) is not IndependentDomainWalker:
        raise StrictContractError("private Hankel producer requires exact sealed authorities")
    if type(dimensions) is not HankelDimensions:
        raise StrictContractError("private Hankel producer requires exact dimensions")
    cutoff = dimensions.cutoff
    task_ids = chart.domain.task_ids
    action_ids = chart.domain.action_ids
    source_digest = _strict_digest(chart.digest, "chart source digest")
    exactness_scope = _strict_scope(chart.exactness_scope)
    prefixes = _action_words(action_ids, dimensions.prefix_depth)
    suffixes = _action_words(action_ids, dimensions.suffix_depth)
    prefix_steps = _word_trie_steps(prefixes)
    suffix_steps = _word_trie_steps(suffixes)
    row_keys = tuple(
        RawHankelRowKey(task_id, prefix)
        for task_id in task_ids
        for prefix in prefixes
    )
    if len(row_keys) != dimensions.n_rows or len(suffixes) != dimensions.n_suffixes:
        raise AssertionError("preflight arithmetic disagrees with generated coordinates")

    canonical_oracle = _CanonicalPrimitiveCursorOracle._prepare(
        chart, _REGISTERED_LOOKUP_TOKEN
    )
    raw_oracle = _RawPrimitiveCursorOracle._prepare(
        walker,
        max_depth=cutoff,
        token=_REGISTERED_LOOKUP_TOKEN,
    )
    canonical_prefix_rows: list[Any] = []
    raw_prefix_rows: list[Any] = []
    canonical_transition_count = 0
    raw_transition_count = 0
    for task_id in task_ids:
        canonical_task_prefixes: list[Any] = []
        raw_task_prefixes: list[Any] = []
        for prefix_index, prefix in enumerate(prefixes):
            step = prefix_steps[prefix_index]
            if step is None:
                canonical_cursor = canonical_oracle.seed(task_id)
                raw_cursor = raw_oracle.seed(task_id)
            else:
                parent_index, action_id = step
                canonical_cursor = canonical_oracle.advance(
                    canonical_task_prefixes[parent_index],
                    action_id,
                    (),
                    prefix,
                )
                raw_cursor = raw_oracle.advance(
                    raw_task_prefixes[parent_index],
                    action_id,
                    (),
                    prefix,
                )
                canonical_transition_count += 1
                raw_transition_count += 1
            canonical_task_prefixes.append(canonical_cursor)
            raw_task_prefixes.append(raw_cursor)
        canonical_prefix_rows.extend(canonical_task_prefixes)
        raw_prefix_rows.extend(raw_task_prefixes)
    if (
        len(canonical_prefix_rows) != dimensions.n_rows
        or len(raw_prefix_rows) != dimensions.n_rows
    ):
        raise AssertionError("prefix cursor trie disagrees with row preflight")

    matrix_rows: list[tuple[int, ...]] = []
    response_hasher = _ResponseCoordinateHasher()
    canonical_response_cache: dict[OpenResponseCacheKey, tuple[bytes, str]] = {}
    raw_response_cache: dict[OpenResponseCacheKey, tuple[bytes, str]] = {}
    word_coordinates_checked = 0
    channel_cells_checked = 0
    for row_key, canonical_prefix, raw_prefix in zip(
        row_keys,
        canonical_prefix_rows,
        raw_prefix_rows,
        strict=True,
    ):
        cells: list[int] = []
        canonical_suffix_cursors: list[Any] = []
        raw_suffix_cursors: list[Any] = []
        for suffix_index, suffix in enumerate(suffixes):
            step = suffix_steps[suffix_index]
            if step is None:
                canonical_cursor = canonical_prefix
                raw_cursor = raw_prefix
            else:
                parent_index, action_id = step
                canonical_cursor = canonical_oracle.advance(
                    canonical_suffix_cursors[parent_index],
                    action_id,
                    row_key.prefix_word,
                    suffix,
                )
                raw_cursor = raw_oracle.advance(
                    raw_suffix_cursors[parent_index],
                    action_id,
                    row_key.prefix_word,
                    suffix,
                )
                canonical_transition_count += 1
                raw_transition_count += 1
            canonical_suffix_cursors.append(canonical_cursor)
            raw_suffix_cursors.append(raw_cursor)

            # Each retained coordinate still mints two detached exact records,
            # serializes them through side-local caches, and compares the two
            # independently advanced authorities field by field.
            canonical = canonical_oracle.response(canonical_cursor)
            raw = raw_oracle.response(raw_cursor)
            canonical_wire, response_digest = _serialize_exact_response(
                canonical, canonical_response_cache, "canonical response"
            )
            raw_wire, _ = _serialize_exact_response(
                raw, raw_response_cache, "independent raw response"
            )
            if (
                type(canonical) is not ExactOccurrenceResponse
                or type(raw) is not ExactOccurrenceResponse
                or canonical != raw
                or canonical_wire != raw_wire
            ):
                word = row_key.prefix_word + suffix
                raise StrictContractError(
                    "D4_NORMALIZATION_UNSOUND: exact raw-coordinate response mismatch "
                    f"at task={row_key.task_id!r}, word={word!r}"
                )
            canonical_channels = _project_response(canonical, "canonical response")
            raw_channels = _project_response(raw, "independent raw response")
            if raw_channels != canonical_channels:
                raise StrictContractError(
                    "D4_NORMALIZATION_UNSOUND: projected raw-coordinate cell mismatch"
                )
            response_hasher.update(
                row_key.task_id, row_key.prefix_word, suffix, response_digest
            )
            cells.extend(canonical_channels)
            word_coordinates_checked += 1
            channel_cells_checked += len(RESPONSE_CHANNELS)
        matrix_rows.append(tuple(cells))
    expected_transition_count = _primitive_trie_transition_count(
        dimensions, n_tasks=len(task_ids)
    )
    if (
        canonical_transition_count != expected_transition_count
        or raw_transition_count != expected_transition_count
    ):
        raise AssertionError("primitive cursor trie transition count mismatch")
    chart.validate()
    walker.validate()
    if chart.digest != source_digest or walker.domain_digest != chart.domain.digest:
        raise StrictContractError("primitive cursor authorities changed during traversal")
    matrix = tuple(matrix_rows)
    row_digest = _row_coordinate_digest(row_keys)
    column_digest = _column_coordinate_digest(suffixes)
    response_coordinate_digest = response_hasher.hexdigest()
    matrix_digest = _sha256(
        _matrix_binding_wire(
            cutoff=cutoff,
            source_digest=source_digest,
            exactness_scope=exactness_scope,
            row_keys=row_keys,
            suffix_words=suffixes,
            matrix=matrix,
            response_coordinate_digest=response_coordinate_digest,
        )
    )
    equality_report = _factory_construct(
        RawCoordinateEqualityReport,
        cutoff=cutoff,
        word_coordinates_checked=word_coordinates_checked,
        channel_cells_checked=channel_cells_checked,
        exact_response_records_equal=True,
        response_coordinate_digest=response_coordinate_digest,
        matrix_digest=matrix_digest,
    )
    return _factory_construct(
        ExactRawCoordinateHankel,
        cutoff=cutoff,
        source_digest=source_digest,
        exactness_scope=exactness_scope,
        row_keys=row_keys,
        suffix_words=suffixes,
        matrix=matrix,
        dimensions=dimensions,
        row_coordinate_digest=row_digest,
        column_coordinate_digest=column_digest,
        response_coordinate_digest=response_coordinate_digest,
        matrix_digest=matrix_digest,
        equality_report=equality_report,
    )


def _materialize_private_rank65_algebra_fixture(
    token: object,
) -> ExactRawCoordinateHankel:
    """Test-only 65-dimensional algebra fixture; never an oracle result path."""

    if token is not _PRIVATE_RANK_FIXTURE_TOKEN:
        raise StrictContractError("private rank fixture authority mismatch")
    task_ids = tuple(f"unit_kp3d4_rank_t{index}" for index in range(5))
    action_ids = tuple(f"unit_kp3d4_rank_a{index:02d}" for index in range(12))
    dimensions = preflight_hankel_dimensions(
        n_tasks=len(task_ids), n_actions=len(action_ids), cutoff=2
    )
    prefixes = _action_words(action_ids, dimensions.prefix_depth)
    suffixes = _action_words(action_ids, dimensions.suffix_depth)
    row_keys = tuple(
        RawHankelRowKey(task_id, prefix)
        for task_id in task_ids
        for prefix in prefixes
    )
    matrix = tuple(
        tuple(1 if column == row else 0 for column in range(dimensions.n_columns))
        for row in range(dimensions.n_rows)
    )
    row_digest = _row_coordinate_digest(row_keys)
    column_digest = _column_coordinate_digest(suffixes)
    response_coordinate_digest = _sha256(
        {
            "schema": "lean-rgc-odlrq-private-rank65-algebra-fixture-v1",
            "rows": [key.to_wire() for key in row_keys],
            "columns": [list(word) for word in suffixes],
        }
    )
    source_digest = _sha256(
        {"schema": "lean-rgc-odlrq-private-rank65-source-v1"}
    )
    matrix_digest = _sha256(
        _matrix_binding_wire(
            cutoff=2,
            source_digest=source_digest,
            exactness_scope=UNCONDITIONAL_FINITE_DOMAIN,
            row_keys=row_keys,
            suffix_words=suffixes,
            matrix=matrix,
            response_coordinate_digest=response_coordinate_digest,
        )
    )
    equality_report = _factory_construct(
        RawCoordinateEqualityReport,
        cutoff=2,
        word_coordinates_checked=dimensions.n_word_coordinates,
        channel_cells_checked=dimensions.n_cells,
        exact_response_records_equal=True,
        response_coordinate_digest=response_coordinate_digest,
        matrix_digest=matrix_digest,
    )
    return _factory_construct(
        ExactRawCoordinateHankel,
        cutoff=2,
        source_digest=source_digest,
        exactness_scope=UNCONDITIONAL_FINITE_DOMAIN,
        row_keys=row_keys,
        suffix_words=suffixes,
        matrix=matrix,
        dimensions=dimensions,
        row_coordinate_digest=row_digest,
        column_coordinate_digest=column_digest,
        response_coordinate_digest=response_coordinate_digest,
        matrix_digest=matrix_digest,
        equality_report=equality_report,
    )


def _check_coefficient(value: int | Fraction, bit_cap: int, where: str) -> None:
    if type(value) is int:
        numerator = value
        denominator = 1
    elif type(value) is Fraction:
        numerator = value.numerator
        denominator = value.denominator
    else:
        raise StrictContractError(f"{where} is not exact")
    if abs(numerator).bit_length() > bit_cap or denominator.bit_length() > bit_cap:
        raise StrictContractError(
            f"D4_RESOURCE_BLOCKED: {where} exceeds the exact coefficient bit cap"
        )


def _primitive_integer_row(values: Sequence[int], bit_cap: int) -> list[int]:
    result = list(values)
    for value in result:
        _check_coefficient(value, bit_cap, "fraction-free row input")
    divisor = 0
    for value in result:
        divisor = gcd(divisor, abs(value))
    if divisor > 1:
        result = [value // divisor for value in result]
    first = next((value for value in result if value), 0)
    if first < 0:
        result = [-value for value in result]
    for value in result:
        _check_coefficient(value, bit_cap, "fraction-free row")
    return result


def _reduce_integer_row(
    source: Sequence[int],
    basis: Sequence[tuple[int, Sequence[int]]],
    bit_cap: int,
) -> list[int]:
    """Fraction-free exact reduction over Q with primitive-content control."""

    reduced = _primitive_integer_row(source, bit_cap)
    for pivot, basis_row in basis:
        factor = reduced[pivot]
        if factor == 0:
            continue
        pivot_value = basis_row[pivot]
        work: list[int] = []
        for left, right in zip(reduced, basis_row, strict=True):
            value = left * pivot_value - right * factor
            _check_coefficient(value, bit_cap, "fraction-free elimination")
            work.append(value)
        reduced = _primitive_integer_row(work, bit_cap)
    return reduced


def _scan_exact_basis(
    rows: Iterable[tuple[int, Sequence[int]]],
    *,
    stop_after: int,
    bit_cap: int,
) -> tuple[list[int], list[int], list[tuple[int, list[int]]], list[list[Any]], bool]:
    basis_indices: list[int] = []
    pivots: list[int] = []
    basis: list[tuple[int, list[int]]] = []
    transcript: list[list[Any]] = []
    stopped = False
    for row_index, row in rows:
        reduced = _reduce_integer_row(row, basis, bit_cap)
        pivot = next((index for index, value in enumerate(reduced) if value), None)
        accepted = pivot is not None
        transcript.append([row_index, accepted, pivot])
        if accepted:
            assert pivot is not None
            basis_indices.append(row_index)
            pivots.append(pivot)
            basis.append((pivot, reduced))
            basis.sort(key=lambda item: item[0])
            if len(basis_indices) == stop_after:
                stopped = True
                break
    return basis_indices, pivots, basis, transcript, stopped


def _fraction_verifier_reduce(
    source: Sequence[int],
    basis: Sequence[tuple[int, Sequence[Fraction]]],
    bit_cap: int,
) -> list[Fraction]:
    """Separately coded rational reduction used only by the verifier.

    The producer above is primitive, fraction-free integer elimination.  This
    verifier deliberately uses normalized ``Fraction`` rows so that an error in
    the producer's content/sign handling is not repeated as a common-mode
    certificate acceptance bug.
    """

    reduced = [Fraction(value) for value in source]
    for value in reduced:
        _check_coefficient(value, bit_cap, "rational verifier input")
    for pivot, basis_row in basis:
        factor = reduced[pivot]
        if factor == 0:
            continue
        updated: list[Fraction] = []
        for left, right in zip(reduced, basis_row, strict=True):
            product = factor * right
            _check_coefficient(product, bit_cap, "rational verifier product")
            value = left - product
            _check_coefficient(value, bit_cap, "rational verifier subtraction")
            updated.append(value)
        reduced = updated
    return reduced


def _fraction_verifier_scan(
    matrix: Sequence[Sequence[int]],
    *,
    stop_after: int,
    bit_cap: int,
) -> tuple[list[int], list[int], list[list[Any]], bool]:
    basis_indices: list[int] = []
    pivots: list[int] = []
    basis: list[tuple[int, list[Fraction]]] = []
    transcript: list[list[Any]] = []
    stopped = False
    for row_index, row in enumerate(matrix):
        reduced = _fraction_verifier_reduce(row, basis, bit_cap)
        pivot = next((index for index, value in enumerate(reduced) if value), None)
        accepted = pivot is not None
        transcript.append([row_index, accepted, pivot])
        if not accepted:
            continue
        assert pivot is not None
        pivot_value = reduced[pivot]
        normalized: list[Fraction] = []
        for value in reduced:
            result = value / pivot_value
            _check_coefficient(result, bit_cap, "rational verifier normalization")
            normalized.append(result)
        basis_indices.append(row_index)
        pivots.append(pivot)
        basis.append((pivot, normalized))
        basis.sort(key=lambda item: item[0])
        if len(basis_indices) == stop_after:
            stopped = True
            break
    return basis_indices, pivots, transcript, stopped


def _elimination_transcript_digest(
    matrix_digest: str, transcript: Sequence[Sequence[Any]], stopped: bool
) -> str:
    return _sha256(
        {
            "schema": "lean-rgc-odlrq-rank-elimination-transcript-v1",
            "matrix_digest": matrix_digest,
            "decisions": [list(decision) for decision in transcript],
            "stopped_at_lower_bound": stopped,
        }
    )


@dataclass(frozen=True, slots=True)
class ExactRankCertificate(_WeakReferenceableEvidence):
    cutoff: int
    kind: ExactRankCertificateKind
    rank_or_lower_bound: int
    basis_row_indices: tuple[int, ...]
    pivot_columns: tuple[int, ...]
    row_coordinate_digest: str
    column_coordinate_digest: str
    response_coordinate_digest: str
    matrix_digest: str
    source_digest: str
    exactness_scope: str
    elimination_transcript_digest: str
    complete_span_verified: bool

    def __post_init__(self) -> None:
        _strict_integer(self.cutoff, "certificate cutoff", minimum=1)
        if type(self.kind) is not ExactRankCertificateKind:
            raise StrictContractError("certificate kind has an inexact type")
        _strict_integer(
            self.rank_or_lower_bound, "certificate rank/lower bound", minimum=0
        )
        if type(self.basis_row_indices) is not tuple or type(self.pivot_columns) is not tuple:
            raise StrictContractError("certificate coordinates must be exact tuples")
        if len(self.basis_row_indices) != len(self.pivot_columns):
            raise StrictContractError("basis and pivot coordinate lengths disagree")
        for value in self.basis_row_indices:
            _strict_integer(value, "basis row index")
        for value in self.pivot_columns:
            _strict_integer(value, "pivot column")
        for value, where in (
            (self.row_coordinate_digest, "certificate row-coordinate digest"),
            (self.column_coordinate_digest, "certificate column-coordinate digest"),
            (
                self.response_coordinate_digest,
                "certificate response-coordinate digest",
            ),
            (self.matrix_digest, "certificate matrix digest"),
            (self.source_digest, "certificate source digest"),
            (self.elimination_transcript_digest, "elimination transcript digest"),
        ):
            _strict_digest(value, where)
        _strict_scope(self.exactness_scope)
        if type(self.complete_span_verified) is not bool:
            raise StrictContractError("complete-span flag must be an exact bool")
        if self.kind is ExactRankCertificateKind.COMPLETE_SPAN:
            if self.rank_or_lower_bound > MAX_EXACT_RANK:
                raise StrictContractError("complete rank exceeds the frozen cap")
            if len(self.basis_row_indices) != self.rank_or_lower_bound:
                raise StrictContractError("complete certificate basis length mismatch")
            if not self.complete_span_verified:
                raise StrictContractError("complete certificate lacks a span verification")
        else:
            if self.rank_or_lower_bound != RANK_LOWER_BOUND_SIZE:
                raise StrictContractError("lower-bound certificate must witness rank at least 65")
            if len(self.basis_row_indices) != RANK_LOWER_BOUND_SIZE:
                raise StrictContractError("lower-bound certificate needs 65 basis rows")
            if self.complete_span_verified:
                raise StrictContractError("lower-bound certificate cannot claim complete span")
        _attest_factory_identity(
            self,
            _sha256(
                {
                    "schema": "lean-rgc-odlrq-exact-rank-authority-v1",
                    "cutoff": self.cutoff,
                    "kind": self.kind.value,
                    "rank_or_lower_bound": self.rank_or_lower_bound,
                    "basis_row_indices": list(self.basis_row_indices),
                    "pivot_columns": list(self.pivot_columns),
                    "row_coordinate_digest": self.row_coordinate_digest,
                    "column_coordinate_digest": self.column_coordinate_digest,
                    "response_coordinate_digest": self.response_coordinate_digest,
                    "matrix_digest": self.matrix_digest,
                    "source_digest": self.source_digest,
                    "exactness_scope": self.exactness_scope,
                    "elimination_transcript_digest": self.elimination_transcript_digest,
                    "complete_span_verified": self.complete_span_verified,
                }
            ),
            "exact rank certificate",
        )

    def validate(self) -> None:
        self.__post_init__()

    def to_wire(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": RANK_CERTIFICATE_SCHEMA,
            "cutoff": self.cutoff,
            "kind": self.kind.value,
            "rank_or_lower_bound": self.rank_or_lower_bound,
            "basis_row_indices": list(self.basis_row_indices),
            "pivot_columns": list(self.pivot_columns),
            "row_coordinate_digest": self.row_coordinate_digest,
            "column_coordinate_digest": self.column_coordinate_digest,
            "response_coordinate_digest": self.response_coordinate_digest,
            "matrix_digest": self.matrix_digest,
            "source_digest": self.source_digest,
            "exactness_scope": self.exactness_scope,
            "elimination_transcript_digest": self.elimination_transcript_digest,
            "complete_span_verified": self.complete_span_verified,
        }


def certify_exact_rank(
    hankel: ExactRawCoordinateHankel,
) -> ExactRankCertificate:
    """Create a bounded exact rank or exact rank-at-least-65 certificate."""

    if type(hankel) is not ExactRawCoordinateHankel:
        raise StrictContractError("rank certification requires an exact retained Hankel")
    hankel.validate()
    basis_indices, pivots, _, transcript, stopped = _scan_exact_basis(
        enumerate(hankel.matrix),
        stop_after=RANK_LOWER_BOUND_SIZE,
        bit_cap=MAX_EXACT_COEFFICIENT_BITS,
    )
    if stopped:
        kind = ExactRankCertificateKind.RANK_AT_LEAST_65
        rank_or_lower_bound = RANK_LOWER_BOUND_SIZE
        complete_span_verified = False
    else:
        kind = ExactRankCertificateKind.COMPLETE_SPAN
        rank_or_lower_bound = len(basis_indices)
        complete_span_verified = True
    transcript_digest = _elimination_transcript_digest(
        hankel.matrix_digest, transcript, stopped
    )
    certificate = _factory_construct(
        ExactRankCertificate,
        cutoff=hankel.cutoff,
        kind=kind,
        rank_or_lower_bound=rank_or_lower_bound,
        basis_row_indices=tuple(basis_indices),
        pivot_columns=tuple(pivots),
        row_coordinate_digest=hankel.row_coordinate_digest,
        column_coordinate_digest=hankel.column_coordinate_digest,
        response_coordinate_digest=hankel.response_coordinate_digest,
        matrix_digest=hankel.matrix_digest,
        source_digest=hankel.source_digest,
        exactness_scope=hankel.exactness_scope,
        elimination_transcript_digest=transcript_digest,
        complete_span_verified=complete_span_verified,
    )
    verification = verify_exact_rank_certificate(
        hankel, certificate
    )
    if not verification.verified:
        raise AssertionError("new exact-rank certificate failed independent verification")
    return certificate


@dataclass(frozen=True, slots=True)
class ExactRankVerificationReport(_WeakReferenceableEvidence):
    verified: bool
    basis_independent: bool
    complete_span_verified: bool
    rows_checked: int
    matrix_digest: str
    source_digest: str
    exactness_scope: str
    certificate_digest: str

    def __post_init__(self) -> None:
        for value, where in (
            (self.verified, "verification result"),
            (self.basis_independent, "basis-independence result"),
            (self.complete_span_verified, "complete-span result"),
        ):
            if type(value) is not bool:
                raise StrictContractError(f"{where} must be an exact bool")
        _strict_integer(self.rows_checked, "verification rows checked")
        _strict_digest(self.matrix_digest, "verification matrix digest")
        _strict_digest(self.source_digest, "verification source digest")
        _strict_scope(self.exactness_scope)
        _strict_digest(self.certificate_digest, "verification certificate digest")
        if not self.verified and (
            self.basis_independent or self.complete_span_verified
        ):
            raise StrictContractError(
                "a rejected rank certificate cannot retain affirmative subclaims"
            )
        if self.verified and not self.basis_independent:
            raise StrictContractError(
                "an accepted rank certificate must retain independent-basis verification"
            )
        _attest_factory_identity(
            self,
            _sha256(
                {
                    "schema": "lean-rgc-odlrq-rank-verification-authority-v1",
                    "verified": self.verified,
                    "basis_independent": self.basis_independent,
                    "complete_span_verified": self.complete_span_verified,
                    "rows_checked": self.rows_checked,
                    "matrix_digest": self.matrix_digest,
                    "source_digest": self.source_digest,
                    "exactness_scope": self.exactness_scope,
                    "certificate_digest": self.certificate_digest,
                }
            ),
            "exact rank verification report",
        )

    def validate(self) -> None:
        self.__post_init__()


def _mint_rank_verification_report(
    hankel: ExactRawCoordinateHankel,
    certificate: ExactRankCertificate,
    *,
    verified: bool,
    basis_independent: bool,
    complete_span_verified: bool,
    rows_checked: int,
) -> ExactRankVerificationReport:
    return _factory_construct(
        ExactRankVerificationReport,
        verified=verified,
        basis_independent=basis_independent,
        complete_span_verified=complete_span_verified,
        rows_checked=rows_checked,
        matrix_digest=hankel.matrix_digest,
        source_digest=hankel.source_digest,
        exactness_scope=hankel.exactness_scope,
        certificate_digest=_registered_semantic_snapshot(
            certificate, "exact rank certificate"
        ),
    )


def verify_exact_rank_certificate(
    hankel: ExactRawCoordinateHankel,
    certificate: ExactRankCertificate,
) -> ExactRankVerificationReport:
    """Independently re-eliminate immutable raw rows against a certificate."""

    if type(hankel) is not ExactRawCoordinateHankel:
        raise StrictContractError("verification requires an exact retained Hankel")
    if type(certificate) is not ExactRankCertificate:
        raise StrictContractError("verification requires an exact rank certificate")
    hankel.validate()
    certificate.validate()
    bindings_match = (
        certificate.cutoff == hankel.cutoff
        and certificate.row_coordinate_digest == hankel.row_coordinate_digest
        and certificate.column_coordinate_digest == hankel.column_coordinate_digest
        and certificate.response_coordinate_digest
        == hankel.response_coordinate_digest
        and certificate.matrix_digest == hankel.matrix_digest
        and certificate.source_digest == hankel.source_digest
        and certificate.exactness_scope == hankel.exactness_scope
    )
    if not bindings_match:
        return _mint_rank_verification_report(
            hankel,
            certificate,
            verified=False,
            basis_independent=False,
            complete_span_verified=False,
            rows_checked=0,
        )
    indices, pivots, transcript, stopped = _fraction_verifier_scan(
        hankel.matrix,
        stop_after=RANK_LOWER_BOUND_SIZE,
        bit_cap=MAX_EXACT_COEFFICIENT_BITS,
    )
    transcript_digest = _elimination_transcript_digest(
        hankel.matrix_digest, transcript, stopped
    )
    expected_kind = (
        ExactRankCertificateKind.RANK_AT_LEAST_65
        if stopped
        else ExactRankCertificateKind.COMPLETE_SPAN
    )
    expected_rank = RANK_LOWER_BOUND_SIZE if stopped else len(indices)
    matches_recomputed_elimination = (
        certificate.kind is expected_kind
        and certificate.rank_or_lower_bound == expected_rank
        and certificate.basis_row_indices == tuple(indices)
        and certificate.pivot_columns == tuple(pivots)
        and certificate.elimination_transcript_digest == transcript_digest
        and certificate.complete_span_verified is (not stopped)
    )
    if not matches_recomputed_elimination:
        return _mint_rank_verification_report(
            hankel,
            certificate,
            verified=False,
            basis_independent=False,
            complete_span_verified=False,
            rows_checked=len(transcript),
        )
    return _mint_rank_verification_report(
        hankel,
        certificate,
        verified=True,
        basis_independent=True,
        complete_span_verified=not stopped,
        rows_checked=len(transcript),
    )


def certify_hankel_family(
    hankels: Sequence[ExactRawCoordinateHankel],
) -> tuple[ExactRankCertificate, ...]:
    """Certify exactly one immutable matrix for each of H1, H2, H3, H4."""

    if type(hankels) not in {tuple, list} or len(hankels) != 4:
        raise StrictContractError("the family must contain exactly H1 through H4")
    if tuple(item.cutoff for item in hankels) != (1, 2, 3, 4):
        raise StrictContractError("the family must be ordered H1, H2, H3, H4")
    source_digests = {item.source_digest for item in hankels}
    scopes = {item.exactness_scope for item in hankels}
    if len(source_digests) != 1 or len(scopes) != 1:
        raise StrictContractError("H1 through H4 must share one source and scope")
    return tuple(certify_exact_rank(item) for item in hankels)


__all__ = [
    "CONDITIONAL_KSTATE_MARKOV",
    "EXACTNESS_SCOPES",
    "ExactRankCertificate",
    "ExactRankCertificateKind",
    "ExactRankVerificationReport",
    "ExactRawCoordinateHankel",
    "HankelDimensions",
    "MAX_EXACT_COEFFICIENT_BITS",
    "MAX_EXACT_RANK",
    "MAX_RAW_DEPTH3_OCCURRENCES",
    "MAX_RAW_DEPTH4_OCCURRENCES",
    "MAX_RAW_HANKEL_CELLS",
    "OFFICIAL_CONDITIONING",
    "OFFICIAL_CONDITIONING_CENSOR",
    "RANK_LOWER_BOUND_SIZE",
    "RESPONSE_CHANNELS",
    "RawCoordinateEqualityReport",
    "RawHankelColumnKey",
    "RawHankelRowKey",
    "UNCONDITIONAL_FINITE_DOMAIN",
    "build_exact_raw_coordinate_hankel",
    "certify_exact_rank",
    "certify_hankel_family",
    "preflight_hankel_dimensions",
    "verify_exact_rank_certificate",
]
