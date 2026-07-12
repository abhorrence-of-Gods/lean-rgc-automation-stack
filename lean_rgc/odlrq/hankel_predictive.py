"""Bounded exact-rational predictive realization for synthetic development.

This module is deliberately independent of the historical U05 Hankel cutoff
probe and of every exact/certified operator type.  A training view contains no
target values.  It is a capability over a finite exact training atom store;
all fit-time reads are recorded and target-key reads fail before lookup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from math import gcd
from typing import Any, Mapping, Sequence

from .contracts import (
    CANONICAL_PAYLOAD_SCHEMA,
    MAX_EXACT_RATIONAL_BITS,
    NOT_APPLICABLE,
    SYNTHETIC_EVIDENCE_SCOPE,
    CanonicalPayload,
    ExactRational,
    StrictContractError,
    canonical_contract_bytes,
)


MAX_HANKEL_ROWS = 512
MAX_HANKEL_COLUMNS = 512
MAX_HANKEL_CELLS = 250_000
MAX_HANKEL_RANK = 64
MAX_HANKEL_KEY_BYTES = 1_000_000
MAX_HANKEL_WORK_UNITS = 2_000_000

PREDICTIVE_TIER = "bounded_rational_predictive_synthetic_development"

ACTION_SCHEMA = "lean-rgc-odlrq-predictive-action-v1"
CHANNEL_SCHEMA = "lean-rgc-odlrq-response-channel-key-v1"
ATOM_KEY_SCHEMA = "lean-rgc-odlrq-response-atom-key-v1"
ROW_KEY_SCHEMA = "lean-rgc-odlrq-hankel-row-key-v1"
COLUMN_KEY_SCHEMA = "lean-rgc-odlrq-hankel-column-key-v1"
ATOM_SCHEMA = "lean-rgc-odlrq-exact-response-atom-v1"
TARGET_DECLARATION_SCHEMA = "lean-rgc-odlrq-target-atom-declaration-v1"
TRAINING_SPEC_SCHEMA = "lean-rgc-odlrq-hankel-training-spec-v1"
READ_EVENT_SCHEMA = "lean-rgc-odlrq-training-read-event-v1"
BASIS_DECISION_SCHEMA = "lean-rgc-odlrq-basis-decision-v1"
FOOTPRINT_SCHEMA = "lean-rgc-odlrq-training-footprint-v1"
VIEW_SCHEMA = "lean-rgc-odlrq-training-hankel-view-v1"
REALIZATION_SCHEMA = "lean-rgc-odlrq-bounded-rational-realization-v1"
TARGET_SET_SCHEMA = "lean-rgc-odlrq-exact-target-response-set-v1"
CHANNEL_RESIDUAL_SCHEMA = "lean-rgc-odlrq-channel-residual-v1"
RESIDUAL_REPORT_SCHEMA = "lean-rgc-odlrq-predictive-residual-report-v1"

_VIEW_SEAL = object()
_REALIZATION_SEAL = object()
_REPORT_SEAL = object()


def _object(value: Any, fields: tuple[str, ...], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(value) != len(fields):
        raise StrictContractError(f"{where} field count mismatch")
    for name in fields:
        if name not in value:
            raise StrictContractError(f"{where} is missing {name!r}")
    for name in value:
        if type(name) is not str or name not in fields:
            raise StrictContractError(f"{where} has an unknown field")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an exact array")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    return value


def _fixed(value: Any, expected: str, where: str) -> str:
    result = _string(value, where)
    if result != expected:
        raise StrictContractError(f"{where} must equal {expected!r}")
    return result


def _integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > (1 << 63) - 1:
        raise StrictContractError(f"{where} must be a signed-64 integer >= {minimum}")
    return value


def _digest(value: Any, where: str) -> str:
    result = _string(value, where)
    if len(result) != 64 or any(ch not in "0123456789ABCDEF" for ch in result):
        raise StrictContractError(f"{where} must be an uppercase SHA-256 digest")
    return result


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _word(value: Any, where: str) -> tuple[str, ...]:
    if type(value) is not tuple or not all(type(item) is str and item for item in value):
        raise StrictContractError(f"{where} must be an exact nonempty-string tuple")
    return value


def _word_from_wire(value: Any, where: str) -> tuple[str, ...]:
    return _word(tuple(_string(item, where) for item in _array(value, where)), where)


def _canonical_key(value: Any) -> bytes:
    return canonical_contract_bytes(value.to_dict())


def _charge(total: int, amount: int, limit: int, where: str) -> int:
    _integer(total, f"{where} total")
    _integer(amount, f"{where} amount")
    if amount > limit - total:
        raise StrictContractError(
            f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds {limit}"
        )
    return total + amount


def _strict_payload(value: CanonicalPayload, where: str) -> CanonicalPayload:
    """Revalidate a retained payload through the base contract parser.

    Frozen dataclasses can still be changed with ``object.__setattr__``.  Calling
    their serializer alone therefore is not an authority check: the base parser
    must accept the resulting wire and reproduce the exact source fields.
    """

    if type(value) is not CanonicalPayload or type(value.canonical_json) is not str:
        raise StrictContractError(f"{where} is not an exact canonical payload")
    if _strict_utf8_size(value.canonical_json, where) > MAX_HANKEL_KEY_BYTES:
        raise StrictContractError(
            f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds the semantic key-byte cap"
        )
    wire = CanonicalPayload.to_dict(value)
    restored = CanonicalPayload.from_dict(wire)
    if restored.canonical_json != value.canonical_json:
        raise StrictContractError(f"{where} is not source-canonical")
    return value


def _strict_rational(value: ExactRational, where: str) -> ExactRational:
    """Reject low-level mutation and noncanonical exact-rational authorities."""

    if (
        type(value) is not ExactRational
        or type(value.numerator) is not int
        or type(value.denominator) is not int
        or value.denominator < 1
    ):
        raise StrictContractError(f"{where} is not an exact rational")
    if (
        abs(value.numerator).bit_length() > MAX_EXACT_RATIONAL_BITS
        or value.denominator.bit_length() > MAX_EXACT_RATIONAL_BITS
    ):
        raise StrictContractError(
            f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds coefficient bit cap"
        )
    if (value.numerator == 0 and value.denominator != 1) or (
        value.numerator != 0 and gcd(abs(value.numerator), value.denominator) != 1
    ):
        raise StrictContractError(f"{where} is not reduced canonical form")
    wire = ExactRational.to_dict(value)
    restored = ExactRational.from_dict(wire)
    if (
        type(restored.numerator) is not int
        or type(restored.denominator) is not int
        or restored.numerator != value.numerator
        or restored.denominator != value.denominator
    ):
        raise StrictContractError(f"{where} is not source-canonical")
    return value


def _strict_utf8_size(value: str, where: str) -> int:
    """Return exact UTF-8 length without allocating an encoded copy."""

    if type(value) is not str:
        raise StrictContractError(f"{where} must be an exact string")
    if len(value) > MAX_HANKEL_KEY_BYTES:
        raise StrictContractError(
            f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds the semantic key-byte cap"
        )
    size = 0
    for character in value:
        codepoint = ord(character)
        if codepoint <= 0x7F:
            size += 1
        elif codepoint <= 0x7FF:
            size += 2
        elif 0xD800 <= codepoint <= 0xDFFF:
            raise StrictContractError(f"{where} is not strict UTF-8")
        elif codepoint <= 0xFFFF:
            size += 3
        else:
            size += 4
        if size > MAX_HANKEL_KEY_BYTES:
            raise StrictContractError(
                f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds the semantic key-byte cap"
            )
    return size


def _charge_utf8_text(total: int, value: str, where: str) -> int:
    """Charge a raw UTF-8 key component without allocating encoded bytes."""

    return _charge(
        total,
        _strict_utf8_size(value, where),
        MAX_HANKEL_KEY_BYTES,
        "semantic key bytes",
    )


def _json_string_size(value: str, where: str) -> int:
    """Exact ensure_ascii=False canonical-JSON string size, allocation-free."""

    _strict_utf8_size(value, where)
    size = 2  # quotation marks
    for character in value:
        codepoint = ord(character)
        if character in {'"', "\\"} or character in {"\b", "\f", "\n", "\r", "\t"}:
            size += 2
        elif codepoint <= 0x1F:
            size += 6
        elif codepoint <= 0x7F:
            size += 1
        elif codepoint <= 0x7FF:
            size += 2
        elif codepoint <= 0xFFFF:
            size += 3
        else:
            size += 4
        if size > MAX_HANKEL_KEY_BYTES:
            raise StrictContractError(
                f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} canonical wire exceeds the semantic key-byte cap"
            )
    return size


def _json_array_of_strings_size(values: tuple[str, ...], where: str) -> int:
    _word(values, where)
    size = 2 + max(0, len(values) - 1)
    for value in values:
        size += _json_string_size(value, where)
        if size > MAX_HANKEL_KEY_BYTES:
            raise StrictContractError(
                f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} canonical wire exceeds the semantic key-byte cap"
            )
    return size


def _json_object_size(fields: Sequence[tuple[str, int]], where: str) -> int:
    size = 2 + max(0, len(fields) - 1)
    for name, value_size in fields:
        size += _json_string_size(name, f"{where} field name") + 1 + value_size
        if size > MAX_HANKEL_KEY_BYTES:
            raise StrictContractError(
                f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} canonical wire exceeds the semantic key-byte cap"
            )
    return size


class PredictiveChannelClass(str, Enum):
    NONTERMINAL = "nonterminal"
    CLOSED_TERMINAL = "closed_terminal"
    SINK_TERMINAL = "sink_terminal"


@dataclass(frozen=True)
class PredictiveActionSymbol:
    action_id: str
    payload: CanonicalPayload

    def __post_init__(self) -> None:
        if type(self) is not PredictiveActionSymbol:
            raise StrictContractError("predictive action subclasses are forbidden")
        _string(self.action_id, "predictive action ID")
        _strict_payload(self.payload, "predictive action payload")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": ACTION_SCHEMA, "action_id": self.action_id, "payload": self.payload.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PredictiveActionSymbol":
        if cls is not PredictiveActionSymbol:
            raise StrictContractError("polymorphic action parsing is forbidden")
        obj = _object(value, ("schema_version", "action_id", "payload"), "PredictiveActionSymbol")
        _fixed(obj["schema_version"], ACTION_SCHEMA, "predictive action schema")
        result = cls(_string(obj["action_id"], "action ID"), CanonicalPayload.from_dict(obj["payload"]))
        if result.to_dict() != obj:
            raise StrictContractError("predictive action is not canonical")
        return result


@dataclass(frozen=True)
class ResponseChannelKey:
    channel_id: str
    channel_class: PredictiveChannelClass

    def __post_init__(self) -> None:
        if type(self) is not ResponseChannelKey:
            raise StrictContractError("response channel subclasses are forbidden")
        _string(self.channel_id, "response channel ID")
        if type(self.channel_class) is not PredictiveChannelClass:
            raise StrictContractError("response channel class is not exact")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": CHANNEL_SCHEMA, "channel_id": self.channel_id, "channel_class": self.channel_class.value}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResponseChannelKey":
        if cls is not ResponseChannelKey:
            raise StrictContractError("polymorphic channel parsing is forbidden")
        obj = _object(value, ("schema_version", "channel_id", "channel_class"), "ResponseChannelKey")
        _fixed(obj["schema_version"], CHANNEL_SCHEMA, "channel schema")
        try:
            kind = PredictiveChannelClass(_string(obj["channel_class"], "channel class"))
        except ValueError as exc:
            raise StrictContractError("unknown predictive channel class") from exc
        result = cls(_string(obj["channel_id"], "channel ID"), kind)
        if result.to_dict() != obj:
            raise StrictContractError("channel key is not canonical")
        return result


@dataclass(frozen=True)
class ResponseAtomKey:
    task_id: str
    action_word: tuple[str, ...]
    channel: ResponseChannelKey

    def __post_init__(self) -> None:
        if type(self) is not ResponseAtomKey:
            raise StrictContractError("response atom key subclasses are forbidden")
        _string(self.task_id, "response atom task ID")
        _word(self.action_word, "response atom action word")
        if type(self.channel) is not ResponseChannelKey:
            raise StrictContractError("response atom channel is not exact")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": ATOM_KEY_SCHEMA, "task_id": self.task_id, "action_word": list(self.action_word), "channel": self.channel.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResponseAtomKey":
        if cls is not ResponseAtomKey:
            raise StrictContractError("polymorphic atom-key parsing is forbidden")
        obj = _object(value, ("schema_version", "task_id", "action_word", "channel"), "ResponseAtomKey")
        _fixed(obj["schema_version"], ATOM_KEY_SCHEMA, "atom-key schema")
        result = cls(_string(obj["task_id"], "atom task ID"), _word_from_wire(obj["action_word"], "atom word"), ResponseChannelKey.from_dict(obj["channel"]))
        if result.to_dict() != obj:
            raise StrictContractError("response atom key is not canonical")
        return result


@dataclass(frozen=True)
class HankelRowKey:
    task_id: str
    prefix_word: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self) is not HankelRowKey:
            raise StrictContractError("Hankel row subclasses are forbidden")
        _string(self.task_id, "Hankel row task ID")
        _word(self.prefix_word, "Hankel row prefix")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": ROW_KEY_SCHEMA, "task_id": self.task_id, "prefix_word": list(self.prefix_word)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HankelRowKey":
        if cls is not HankelRowKey:
            raise StrictContractError("polymorphic row-key parsing is forbidden")
        obj = _object(value, ("schema_version", "task_id", "prefix_word"), "HankelRowKey")
        _fixed(obj["schema_version"], ROW_KEY_SCHEMA, "row-key schema")
        return cls(_string(obj["task_id"], "row task"), _word_from_wire(obj["prefix_word"], "row prefix"))


@dataclass(frozen=True)
class HankelColumnKey:
    suffix_word: tuple[str, ...]
    channel: ResponseChannelKey

    def __post_init__(self) -> None:
        if type(self) is not HankelColumnKey:
            raise StrictContractError("Hankel column subclasses are forbidden")
        _word(self.suffix_word, "Hankel column suffix")
        if type(self.channel) is not ResponseChannelKey:
            raise StrictContractError("Hankel column channel is not exact")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": COLUMN_KEY_SCHEMA, "suffix_word": list(self.suffix_word), "channel": self.channel.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HankelColumnKey":
        if cls is not HankelColumnKey:
            raise StrictContractError("polymorphic column-key parsing is forbidden")
        obj = _object(value, ("schema_version", "suffix_word", "channel"), "HankelColumnKey")
        _fixed(obj["schema_version"], COLUMN_KEY_SCHEMA, "column-key schema")
        return cls(_word_from_wire(obj["suffix_word"], "column suffix"), ResponseChannelKey.from_dict(obj["channel"]))


def make_response_atom_key(row: HankelRowKey, column: HankelColumnKey) -> ResponseAtomKey:
    if type(row) is not HankelRowKey or type(column) is not HankelColumnKey:
        raise StrictContractError("response atom construction requires exact row/column keys")
    return ResponseAtomKey(row.task_id, row.prefix_word + column.suffix_word, column.channel)


@dataclass(frozen=True)
class ExactResponseAtom:
    key: ResponseAtomKey
    value: ExactRational
    censor: str = NOT_APPLICABLE

    def __post_init__(self) -> None:
        if type(self) is not ExactResponseAtom:
            raise StrictContractError("exact response atom subclasses are forbidden")
        if type(self.key) is not ResponseAtomKey:
            raise StrictContractError("exact response atom key/value is not exact")
        self.key.to_dict()
        _strict_rational(self.value, "exact response value")
        _fixed(self.censor, NOT_APPLICABLE, "response atom censor")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": ATOM_SCHEMA, "key": self.key.to_dict(), "value": ExactRational.to_dict(self.value), "censor": self.censor}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactResponseAtom":
        if cls is not ExactResponseAtom:
            raise StrictContractError("polymorphic response-atom parsing is forbidden")
        obj = _object(value, ("schema_version", "key", "value", "censor"), "ExactResponseAtom")
        _fixed(obj["schema_version"], ATOM_SCHEMA, "response atom schema")
        return cls(ResponseAtomKey.from_dict(obj["key"]), ExactRational.from_dict(obj["value"]), _fixed(obj["censor"], NOT_APPLICABLE, "response atom censor"))


def _taxonomy_digest(channels: Sequence[ResponseChannelKey]) -> str:
    return _sha256({"channels": [channel.to_dict() for channel in channels]})


@dataclass(frozen=True)
class TargetAtomDeclaration:
    declaration_id: str
    taxonomy_sha256: str
    keys: tuple[ResponseAtomKey, ...]

    def __post_init__(self) -> None:
        if type(self) is not TargetAtomDeclaration:
            raise StrictContractError("target declaration subclasses are forbidden")
        _string(self.declaration_id, "target declaration ID")
        object.__setattr__(self, "taxonomy_sha256", _digest(self.taxonomy_sha256, "target taxonomy digest"))
        if type(self.keys) is not tuple or not self.keys or not all(type(key) is ResponseAtomKey for key in self.keys):
            raise StrictContractError("target declaration keys are not a nonempty exact tuple")
        minimum_key_bytes = len(ATOM_KEY_SCHEMA.encode("utf-8")) + 3
        if len(self.keys) > MAX_HANKEL_KEY_BYTES // minimum_key_bytes:
            raise StrictContractError(
                "CPU_RECOVERY_PREREQUISITE_BLOCKED: target registration count exceeds the key-byte-derived cap"
            )
        key_bytes = 0
        for key in self.keys:
            key_bytes = _charge_semantic_key(key_bytes, key)
        ordered = tuple(sorted(self.keys, key=_canonical_key))
        if len({_canonical_key(key) for key in ordered}) != len(ordered):
            raise StrictContractError("target declaration contains duplicate atom keys")
        object.__setattr__(self, "keys", ordered)

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": TARGET_DECLARATION_SCHEMA, "declaration_id": self.declaration_id, "taxonomy_sha256": self.taxonomy_sha256, "keys": [key.to_dict() for key in self.keys]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TargetAtomDeclaration":
        if cls is not TargetAtomDeclaration:
            raise StrictContractError("polymorphic target-declaration parsing is forbidden")
        obj = _object(value, ("schema_version", "declaration_id", "taxonomy_sha256", "keys"), "TargetAtomDeclaration")
        _fixed(obj["schema_version"], TARGET_DECLARATION_SCHEMA, "target declaration schema")
        result = cls(_string(obj["declaration_id"], "declaration ID"), _digest(obj["taxonomy_sha256"], "taxonomy digest"), tuple(ResponseAtomKey.from_dict(row) for row in _array(obj["keys"], "target keys")))
        if result.to_dict() != obj:
            raise StrictContractError("target declaration arrays are not canonical")
        return result


def _action_order(actions: Sequence[PredictiveActionSymbol]) -> tuple[PredictiveActionSymbol, ...]:
    return tuple(
        sorted(
            actions,
            key=lambda action: (
                action.payload.canonical_json.encode("utf-8"),
                action.action_id.encode("utf-8"),
            ),
        )
    )


def _semantic_word_key(word: tuple[str, ...], rank: Mapping[str, int]) -> tuple[int, ...]:
    try:
        return tuple(rank[action_id] for action_id in word)
    except KeyError as exc:
        raise StrictContractError("word contains an action outside the declared alphabet") from exc


@dataclass(frozen=True)
class HankelTrainingSpec:
    actions: tuple[PredictiveActionSymbol, ...]
    task_ids: tuple[str, ...]
    channels: tuple[ResponseChannelKey, ...]
    rows: tuple[HankelRowKey, ...]
    columns: tuple[HankelColumnKey, ...]
    r_cap: int

    def __post_init__(self) -> None:
        if type(self) is not HankelTrainingSpec:
            raise StrictContractError("training spec subclasses are forbidden")
        for name, values, cls in (("actions", self.actions, PredictiveActionSymbol), ("channels", self.channels, ResponseChannelKey), ("rows", self.rows, HankelRowKey), ("columns", self.columns, HankelColumnKey)):
            if type(values) is not tuple or not values or not all(type(value) is cls for value in values):
                raise StrictContractError(f"training spec {name} is not a nonempty exact tuple")
        if type(self.task_ids) is not tuple or not self.task_ids or not all(type(value) is str and value for value in self.task_ids):
            raise StrictContractError("training task IDs are not a nonempty exact tuple")
        if len(self.rows) > MAX_HANKEL_ROWS or len(self.columns) > MAX_HANKEL_COLUMNS:
            raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: structural Hankel cap exceeded")
        minimum_action_bytes = len(ACTION_SCHEMA.encode("utf-8")) + 2
        if len(self.actions) > MAX_HANKEL_KEY_BYTES // minimum_action_bytes:
            raise StrictContractError(
                "CPU_RECOVERY_PREREQUISITE_BLOCKED: action count exceeds the key-byte-derived cap"
            )
        spec_key_bytes = 0
        for collection in (self.actions, self.channels, self.rows, self.columns):
            for value in collection:
                spec_key_bytes = _charge_semantic_key(spec_key_bytes, value)
        for task_id in self.task_ids:
            spec_key_bytes = _charge_utf8_text(spec_key_bytes, task_id, "task ID")
        actions = _action_order(self.actions)
        if len({action.action_id for action in actions}) != len(actions) or len({action.payload.canonical_json for action in actions}) != len(actions):
            raise StrictContractError("training actions are not unique")
        rank = {action.action_id: index for index, action in enumerate(actions)}
        tasks = tuple(sorted(self.task_ids, key=lambda value: value.encode("utf-8")))
        channels = tuple(sorted(self.channels, key=_canonical_key))
        if len(set(tasks)) != len(tasks) or len({_canonical_key(channel) for channel in channels}) != len(channels):
            raise StrictContractError("training tasks/channels are not unique")
        task_set = set(tasks)
        channel_wires = {_canonical_key(channel) for channel in channels}
        for row in self.rows:
            if row.task_id not in task_set:
                raise StrictContractError("Hankel row uses an undeclared task")
            _semantic_word_key(row.prefix_word, rank)
        for column in self.columns:
            if _canonical_key(column.channel) not in channel_wires:
                raise StrictContractError("Hankel column uses an undeclared channel")
            _semantic_word_key(column.suffix_word, rank)
        rows = tuple(sorted(self.rows, key=lambda row: (_semantic_word_key(row.prefix_word, rank), row.task_id.encode("utf-8"))))
        columns = tuple(sorted(self.columns, key=lambda column: (_semantic_word_key(column.suffix_word, rank), _canonical_key(column.channel))))
        if len({_canonical_key(row) for row in rows}) != len(rows) or len({_canonical_key(column) for column in columns}) != len(columns):
            raise StrictContractError("Hankel rows/columns are not unique")
        row_keys = {(row.task_id, row.prefix_word) for row in rows}
        for task_id in tasks:
            if (task_id, ()) not in row_keys:
                raise StrictContractError(
                    "CPU_RECOVERY_PREREQUISITE_BLOCKED: row prefix closure lacks the epsilon row for a declared task"
                )
        for row in rows:
            for length in range(len(row.prefix_word)):
                if (row.task_id, row.prefix_word[:length]) not in row_keys:
                    raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: row prefix closure is incomplete")
        column_keys = {(column.suffix_word, _canonical_key(column.channel)) for column in columns}
        for channel in channels:
            if ((), _canonical_key(channel)) not in column_keys:
                raise StrictContractError(
                    "CPU_RECOVERY_PREREQUISITE_BLOCKED: column prefix closure lacks the epsilon column for a declared channel"
                )
        for column in columns:
            # Columns denote right-hand suffixes.  Their closure direction is
            # therefore the standard Hankel tail closure: a.v requires v.
            # This is the dual of row prefix closure and preserves natural,
            # noncommutative action order in Y_(a.v) = A_a Y_v.
            if column.suffix_word and (
                column.suffix_word[1:],
                _canonical_key(column.channel),
            ) not in column_keys:
                raise StrictContractError(
                    "CPU_RECOVERY_PREREQUISITE_BLOCKED: column suffix/tail closure is incomplete"
                )
        r_cap = _integer(self.r_cap, "training rank cap", minimum=1)
        if r_cap > min(MAX_HANKEL_RANK, len(rows), len(columns)):
            raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: rank cap is outside dimensions")
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "task_ids", tasks)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "columns", columns)

    @property
    def taxonomy_sha256(self) -> str:
        return _taxonomy_digest(self.channels)

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": TRAINING_SPEC_SCHEMA, "actions": [value.to_dict() for value in self.actions], "task_ids": list(self.task_ids), "channels": [value.to_dict() for value in self.channels], "rows": [value.to_dict() for value in self.rows], "columns": [value.to_dict() for value in self.columns], "r_cap": self.r_cap, "taxonomy_sha256": self.taxonomy_sha256}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HankelTrainingSpec":
        if cls is not HankelTrainingSpec:
            raise StrictContractError("polymorphic training-spec parsing is forbidden")
        obj = _object(
            value,
            (
                "schema_version",
                "actions",
                "task_ids",
                "channels",
                "rows",
                "columns",
                "r_cap",
                "taxonomy_sha256",
            ),
            "HankelTrainingSpec",
        )
        _fixed(obj["schema_version"], TRAINING_SPEC_SCHEMA, "training spec schema")
        result = cls(
            tuple(PredictiveActionSymbol.from_dict(item) for item in _array(obj["actions"], "training actions")),
            tuple(_string(item, "training task") for item in _array(obj["task_ids"], "training tasks")),
            tuple(ResponseChannelKey.from_dict(item) for item in _array(obj["channels"], "training channels")),
            tuple(HankelRowKey.from_dict(item) for item in _array(obj["rows"], "training rows")),
            tuple(HankelColumnKey.from_dict(item) for item in _array(obj["columns"], "training columns")),
            _integer(obj["r_cap"], "training rank cap", minimum=1),
        )
        _digest(obj["taxonomy_sha256"], "training taxonomy digest")
        if result.to_dict() != obj:
            raise StrictContractError("training spec is not canonical")
        return result


@dataclass(frozen=True)
class TrainingReadEvent:
    sequence: int
    purpose: str
    atom_key: ResponseAtomKey

    def __post_init__(self) -> None:
        if type(self) is not TrainingReadEvent:
            raise StrictContractError("training read event subclasses are forbidden")
        _integer(self.sequence, "training read sequence")
        _string(self.purpose, "training read purpose")
        if type(self.atom_key) is not ResponseAtomKey:
            raise StrictContractError("training read atom key is not exact")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": READ_EVENT_SCHEMA, "sequence": self.sequence, "purpose": self.purpose, "atom_key": self.atom_key.to_dict()}


@dataclass(frozen=True)
class BasisDecision:
    basis_kind: str
    candidate_key: HankelRowKey | HankelColumnKey
    accepted: bool
    pivot_key: HankelRowKey | HankelColumnKey | None

    def __post_init__(self) -> None:
        if type(self) is not BasisDecision:
            raise StrictContractError("basis decision subclasses are forbidden")
        if self.basis_kind not in {"row", "column"}:
            raise StrictContractError("basis kind is not row or column")
        candidate_type = HankelRowKey if self.basis_kind == "row" else HankelColumnKey
        pivot_type = HankelColumnKey if self.basis_kind == "row" else HankelRowKey
        if type(self.candidate_key) is not candidate_type:
            raise StrictContractError("basis candidate key has the wrong semantic type")
        self.candidate_key.to_dict()
        if type(self.accepted) is not bool:
            raise StrictContractError("basis accepted flag is not exact")
        if self.pivot_key is not None:
            if type(self.pivot_key) is not pivot_type:
                raise StrictContractError("basis pivot key has the wrong semantic type")
            self.pivot_key.to_dict()
        if self.accepted != (self.pivot_key is not None):
            raise StrictContractError("basis acceptance and pivot key disagree")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": BASIS_DECISION_SCHEMA,
            "basis_kind": self.basis_kind,
            "candidate_key": self.candidate_key.to_dict(),
            "accepted": self.accepted,
            "pivot_key": None if self.pivot_key is None else self.pivot_key.to_dict(),
        }


@dataclass(frozen=True)
class TrainingFootprint:
    reads: tuple[TrainingReadEvent, ...]
    basis_decisions: tuple[BasisDecision, ...]

    def __post_init__(self) -> None:
        if type(self) is not TrainingFootprint or type(self.reads) is not tuple or type(self.basis_decisions) is not tuple:
            raise StrictContractError("training footprint is not exact")
        if not all(type(value) is TrainingReadEvent for value in self.reads) or not all(type(value) is BasisDecision for value in self.basis_decisions):
            raise StrictContractError("training footprint members are not exact")
        if tuple(event.sequence for event in self.reads) != tuple(range(len(self.reads))):
            raise StrictContractError("training read sequence is not contiguous")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": FOOTPRINT_SCHEMA, "reads": [value.to_dict() for value in self.reads], "basis_decisions": [value.to_dict() for value in self.basis_decisions]}


def _semantic_atom_sort_key(key: ResponseAtomKey, spec: HankelTrainingSpec) -> tuple[Any, ...]:
    rank = {action.action_id: index for index, action in enumerate(spec.actions)}
    return (_semantic_word_key(key.action_word, rank), key.task_id.encode("utf-8"), _canonical_key(key.channel))


def _channel_key_wire_size(value: ResponseChannelKey) -> int:
    value.__post_init__()
    return _json_object_size(
        (
            ("schema_version", _json_string_size(CHANNEL_SCHEMA, "channel schema")),
            ("channel_id", _json_string_size(value.channel_id, "channel ID")),
            (
                "channel_class",
                _json_string_size(value.channel_class.value, "channel class"),
            ),
        ),
        "channel key",
    )


def _charge_semantic_key(total: int, value: Any) -> int:
    """Charge the exact canonical key wire without first materializing it."""

    if type(value) is PredictiveActionSymbol:
        if type(value.action_id) is not str or not value.action_id:
            raise StrictContractError("action ID must be a nonempty exact string")
        if (
            type(value.payload) is not CanonicalPayload
            or type(value.payload.canonical_json) is not str
            or not value.payload.canonical_json
        ):
            raise StrictContractError("action payload is not structurally exact")
        payload_size = _json_object_size(
            (
                (
                    "schema_version",
                    _json_string_size(
                        CANONICAL_PAYLOAD_SCHEMA,
                        "canonical payload schema",
                    ),
                ),
                (
                    "canonical_json",
                    _json_string_size(
                        value.payload.canonical_json, "action payload"
                    ),
                ),
            ),
            "canonical payload",
        )
        wire_size = _json_object_size(
            (
                ("schema_version", _json_string_size(ACTION_SCHEMA, "action schema")),
                ("action_id", _json_string_size(value.action_id, "action ID")),
                ("payload", payload_size),
            ),
            "predictive action",
        )
        total = _charge(
            total,
            wire_size,
            MAX_HANKEL_KEY_BYTES,
            "semantic key bytes",
        )
        _strict_payload(value.payload, "action payload")
        return total
    if type(value) is ResponseChannelKey:
        wire_size = _channel_key_wire_size(value)
        return _charge(total, wire_size, MAX_HANKEL_KEY_BYTES, "semantic key bytes")
    if type(value) is HankelRowKey:
        value.__post_init__()
        wire_size = _json_object_size(
            (
                ("schema_version", _json_string_size(ROW_KEY_SCHEMA, "row schema")),
                ("task_id", _json_string_size(value.task_id, "row task")),
                (
                    "prefix_word",
                    _json_array_of_strings_size(value.prefix_word, "row prefix"),
                ),
            ),
            "Hankel row key",
        )
        return _charge(total, wire_size, MAX_HANKEL_KEY_BYTES, "semantic key bytes")
    if type(value) is HankelColumnKey:
        value.__post_init__()
        wire_size = _json_object_size(
            (
                (
                    "schema_version",
                    _json_string_size(COLUMN_KEY_SCHEMA, "column schema"),
                ),
                (
                    "suffix_word",
                    _json_array_of_strings_size(value.suffix_word, "column suffix"),
                ),
                ("channel", _channel_key_wire_size(value.channel)),
            ),
            "Hankel column key",
        )
        return _charge(total, wire_size, MAX_HANKEL_KEY_BYTES, "semantic key bytes")
    if type(value) is ResponseAtomKey:
        value.__post_init__()
        value.channel.__post_init__()
        wire_size = _json_object_size(
            (
                (
                    "schema_version",
                    _json_string_size(ATOM_KEY_SCHEMA, "atom-key schema"),
                ),
                ("task_id", _json_string_size(value.task_id, "atom task")),
                (
                    "action_word",
                    _json_array_of_strings_size(value.action_word, "atom word"),
                ),
                ("channel", _channel_key_wire_size(value.channel)),
            ),
            "response atom key",
        )
        return _charge(total, wire_size, MAX_HANKEL_KEY_BYTES, "semantic key bytes")
    raise StrictContractError("unsupported semantic key type")


def _preflight_view(spec: HankelTrainingSpec, atoms: Sequence[ExactResponseAtom], targets: TargetAtomDeclaration) -> tuple[int, int]:
    if type(spec) is not HankelTrainingSpec or type(targets) is not TargetAtomDeclaration:
        raise StrictContractError("training view authorities are not exact")
    for name, values, member_type in (
        ("actions", spec.actions, PredictiveActionSymbol),
        ("channels", spec.channels, ResponseChannelKey),
        ("rows", spec.rows, HankelRowKey),
        ("columns", spec.columns, HankelColumnKey),
    ):
        if (
            type(values) is not tuple
            or not values
            or not all(type(value) is member_type for value in values)
        ):
            raise StrictContractError(f"training spec {name} authority changed")
    if (
        type(spec.task_ids) is not tuple
        or not spec.task_ids
        or not all(type(task) is str and task for task in spec.task_ids)
    ):
        raise StrictContractError("training task authority changed")
    if len(spec.rows) > MAX_HANKEL_ROWS or len(spec.columns) > MAX_HANKEL_COLUMNS:
        raise StrictContractError(
            "CPU_RECOVERY_PREREQUISITE_BLOCKED: structural Hankel cap exceeded"
        )
    _integer(spec.r_cap, "training rank cap", minimum=1)
    if (
        type(targets.keys) is not tuple
        or not targets.keys
        or not all(type(key) is ResponseAtomKey for key in targets.keys)
    ):
        raise StrictContractError("target declaration authority changed")
    if type(atoms) not in {tuple, list} or not all(type(atom) is ExactResponseAtom for atom in atoms):
        raise StrictContractError("training atoms require an exact list or tuple")
    nr, nc = len(spec.rows), len(spec.columns)
    if nr * nc > MAX_HANKEL_CELLS:
        raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: Hankel cell cap exceeded")
    max_target_word_length = max(len(key.action_word) for key in targets.keys)
    ntargets = len(targets.keys)
    na, nt, nch = len(spec.actions), len(spec.task_ids), len(spec.channels)
    minimum_atom_key_bytes = len(ATOM_KEY_SCHEMA.encode("utf-8")) + 3
    if len(atoms) + ntargets > MAX_HANKEL_KEY_BYTES // minimum_atom_key_bytes:
        raise StrictContractError(
            "CPU_RECOVERY_PREREQUISITE_BLOCKED: registered atom count exceeds the key-byte-derived cap"
        )

    # The registered W_H formula is charged before any vocabulary set, sort, or
    # training/target wire map can be allocated.
    work = 0
    work = _charge(work, nr * nc * min(nr, nc), MAX_HANKEL_WORK_UNITS, "Hankel work")
    work = _charge(work, (na + 1) * spec.r_cap**3, MAX_HANKEL_WORK_UNITS, "Hankel work")
    work = _charge(work, (nt + nch) * spec.r_cap**2, MAX_HANKEL_WORK_UNITS, "Hankel work")
    work = _charge(work, ntargets * spec.r_cap**2 * max(1, max_target_word_length), MAX_HANKEL_WORK_UNITS, "Hankel work")

    # Likewise, key bytes are streamed component-by-component; no unbounded
    # canonical aggregate is created before its remaining-cap guard.
    key_bytes = 0
    for collection in (spec.actions, spec.channels, spec.rows, spec.columns, targets.keys):
        for value in collection:
            key_bytes = _charge_semantic_key(key_bytes, value)
    for atom in atoms:
        key_bytes = _charge_semantic_key(key_bytes, atom.key)
    for task in spec.task_ids:
        key_bytes = _charge_utf8_text(key_bytes, task, "task ID")

    # Full retained-authority validation (including prefix closure and
    # canonical ordering) is now safe to run because its allocations are under
    # the complete structural/key envelope.
    spec.__post_init__()
    targets.__post_init__()
    if targets.taxonomy_sha256 != spec.taxonomy_sha256:
        raise StrictContractError("target declaration taxonomy mismatch")

    # Response values/censors are inspected only after the complete structural
    # work and key-byte preflight has passed.
    for atom in atoms:
        atom.__post_init__()

    # Only after both registered caps pass may lookup/set authorities be built.
    action_ids = {action.action_id for action in spec.actions}
    tasks = set(spec.task_ids)
    channel_wires = {_canonical_key(channel) for channel in spec.channels}
    for key in targets.keys:
        if key.task_id not in tasks or _canonical_key(key.channel) not in channel_wires or any(action not in action_ids for action in key.action_word):
            raise StrictContractError("response atom key is outside the training vocabulary")
    for atom in atoms:
        key = atom.key
        if key.task_id not in tasks or _canonical_key(key.channel) not in channel_wires or any(action not in action_ids for action in key.action_word):
            raise StrictContractError("response atom key is outside the training vocabulary")
    target_wires = {_canonical_key(key) for key in targets.keys}
    atom_wires: set[bytes] = set()
    for atom in atoms:
        wire = _canonical_key(atom.key)
        if wire in atom_wires:
            raise StrictContractError("training atom store contains duplicate keys")
        if wire in target_wires:
            raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: target atom leaked into training store")
        atom_wires.add(wire)
    return work, key_bytes


def _view_wire(spec: HankelTrainingSpec, atoms: Sequence[ExactResponseAtom], targets: TargetAtomDeclaration) -> dict[str, Any]:
    work, key_bytes = _preflight_view(spec, atoms, targets)
    ordered_atoms = tuple(sorted(atoms, key=lambda atom: _semantic_atom_sort_key(atom.key, spec)))
    return {"schema_version": VIEW_SCHEMA, "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE, "predictive_tier": PREDICTIVE_TIER, "spec_sha256": _sha256(spec.to_dict()), "target_declaration_sha256": _sha256(targets.to_dict()), "training_store_sha256": _sha256({"atoms": [atom.to_dict() for atom in ordered_atoms]}), "row_count": len(spec.rows), "column_count": len(spec.columns), "cell_count": len(spec.rows) * len(spec.columns), "work_units": work, "key_bytes": key_bytes}


@dataclass(frozen=True)
class TrainingHankelView:
    _spec: HankelTrainingSpec = field(repr=False)
    _training_atoms: tuple[ExactResponseAtom, ...] = field(repr=False)
    _target_declaration: TargetAtomDeclaration = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not TrainingHankelView or self._construction_seal is not _VIEW_SEAL:
            raise StrictContractError("training view requires its sealed factory")
        wire = _view_wire(self._spec, self._training_atoms, self._target_declaration)
        if _digest(self._source_seal_sha256, "training view seal") != _sha256(wire):
            raise StrictContractError("training view source seal mismatch")

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _VIEW_SEAL:
            raise StrictContractError("training view construction seal changed")
        wire = _view_wire(self._spec, self._training_atoms, self._target_declaration)
        if _sha256(wire) != _digest(self._source_seal_sha256, "training view seal"):
            raise StrictContractError("training view retained authority changed")
        return wire

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], spec: HankelTrainingSpec, training_atoms: Sequence[ExactResponseAtom], target_declaration: TargetAtomDeclaration) -> "TrainingHankelView":
        if cls is not TrainingHankelView:
            raise StrictContractError("polymorphic training-view parsing is forbidden")
        expected = make_training_hankel_view(spec, training_atoms, target_declaration)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError("training view wire does not match external authority")
        return expected


def make_training_hankel_view(spec: HankelTrainingSpec, training_atoms: Sequence[ExactResponseAtom], target_declaration: TargetAtomDeclaration) -> TrainingHankelView:
    if type(training_atoms) not in {tuple, list}:
        raise StrictContractError("training atom factory requires an exact list or tuple")
    _preflight_view(spec, training_atoms, target_declaration)
    ordered = tuple(sorted(training_atoms, key=lambda atom: _semantic_atom_sort_key(atom.key, spec)))
    wire = _view_wire(spec, ordered, target_declaration)
    return TrainingHankelView(spec, ordered, target_declaration, _sha256(wire), _construction_seal=_VIEW_SEAL)


# ---------------------------------------------------------------------------
# Bounded exact rational linear algebra


def _q_check(value: ExactRational, where: str) -> ExactRational:
    return _strict_rational(value, where)


def _raw_bits(numerator: int, denominator: int, where: str) -> None:
    if abs(numerator).bit_length() > MAX_EXACT_RATIONAL_BITS or denominator.bit_length() > MAX_EXACT_RATIONAL_BITS:
        raise StrictContractError(f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} exceeds coefficient bit cap")


def _q_add(left: ExactRational, right: ExactRational, where: str = "rational addition") -> ExactRational:
    left, right = _q_check(left, where), _q_check(right, where)
    common = gcd(left.denominator, right.denominator)
    left_scale = right.denominator // common
    right_scale = left.denominator // common
    if abs(left.numerator).bit_length() + left_scale.bit_length() > MAX_EXACT_RATIONAL_BITS + 1 or abs(right.numerator).bit_length() + right_scale.bit_length() > MAX_EXACT_RATIONAL_BITS + 1:
        raise StrictContractError(f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} pre-product bit cap")
    left_term = left.numerator * left_scale
    right_term = right.numerator * right_scale
    denominator = left.denominator * left_scale
    _raw_bits(left_term, denominator, where)
    _raw_bits(right_term, denominator, where)
    numerator = left_term + right_term
    _raw_bits(numerator, denominator, where)
    return ExactRational(numerator, denominator)


def _q_neg(value: ExactRational) -> ExactRational:
    value = _q_check(value, "rational negation")
    return ExactRational(-value.numerator, value.denominator)


def _q_sub(left: ExactRational, right: ExactRational, where: str = "rational subtraction") -> ExactRational:
    return _q_add(left, _q_neg(right), where)


def _q_mul(left: ExactRational, right: ExactRational, where: str = "rational multiplication") -> ExactRational:
    left, right = _q_check(left, where), _q_check(right, where)
    g1 = gcd(abs(left.numerator), right.denominator)
    g2 = gcd(abs(right.numerator), left.denominator)
    a = left.numerator // g1
    d = right.denominator // g1
    b = right.numerator // g2
    c = left.denominator // g2
    if abs(a).bit_length() + abs(b).bit_length() > MAX_EXACT_RATIONAL_BITS + 1 or c.bit_length() + d.bit_length() > MAX_EXACT_RATIONAL_BITS + 1:
        raise StrictContractError(f"CPU_RECOVERY_PREREQUISITE_BLOCKED: {where} pre-product bit cap")
    numerator, denominator = a * b, c * d
    _raw_bits(numerator, denominator, where)
    return ExactRational(numerator, denominator)


def _q_div(left: ExactRational, right: ExactRational, where: str = "rational division") -> ExactRational:
    right = _q_check(right, where)
    if right.numerator == 0:
        raise StrictContractError(f"{where} divides by zero")
    sign = -1 if right.numerator < 0 else 1
    return _q_mul(left, ExactRational(sign * right.denominator, abs(right.numerator)), where)


def _q_abs(value: ExactRational) -> ExactRational:
    value = _q_check(value, "rational absolute value")
    return ExactRational(abs(value.numerator), value.denominator)


def _q_less(left: ExactRational, right: ExactRational) -> bool:
    difference = _q_sub(left, right, "rational comparison")
    return difference.numerator < 0


def _zero() -> ExactRational:
    return ExactRational(0)


def _one() -> ExactRational:
    return ExactRational(1)


def _dot(left: Sequence[ExactRational], right: Sequence[ExactRational], where: str) -> ExactRational:
    if len(left) != len(right):
        raise StrictContractError(f"{where} dimension mismatch")
    total = _zero()
    for index in range(len(left)):
        total = _q_add(total, _q_mul(left[index], right[index], where), where)
    return total


def _matrix_multiply(left: Sequence[Sequence[ExactRational]], right: Sequence[Sequence[ExactRational]], where: str) -> tuple[tuple[ExactRational, ...], ...]:
    if not left or not right:
        raise StrictContractError(f"{where} has an empty matrix")
    inner = len(left[0])
    if any(len(row) != inner for row in left) or len(right) != inner:
        raise StrictContractError(f"{where} dimension mismatch")
    width = len(right[0])
    if any(len(row) != width for row in right):
        raise StrictContractError(f"{where} ragged matrix")
    columns = tuple(tuple(right[row][column] for row in range(inner)) for column in range(width))
    return tuple(tuple(_dot(row, columns[column], where) for column in range(width)) for row in left)


def _row_times_matrix(row: Sequence[ExactRational], matrix: Sequence[Sequence[ExactRational]], where: str) -> tuple[ExactRational, ...]:
    return _matrix_multiply((tuple(row),), matrix, where)[0]


def _inverse(matrix: Sequence[Sequence[ExactRational]]) -> tuple[tuple[ExactRational, ...], ...]:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise StrictContractError("core cross is not square")
    work = [list(row) + [_one() if row_index == column else _zero() for column in range(size)] for row_index, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((row for row in range(column, size) if work[row][column].numerator != 0), None)
        if pivot is None:
            raise StrictContractError("core cross is singular")
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
        pivot_value = work[column][column]
        work[column] = [_q_div(value, pivot_value, "core inverse pivot") for value in work[column]]
        for row in range(size):
            if row == column or work[row][column].numerator == 0:
                continue
            factor = work[row][column]
            work[row] = [_q_sub(work[row][index], _q_mul(factor, work[column][index], "core inverse elimination"), "core inverse elimination") for index in range(2 * size)]
    return tuple(tuple(row[size:]) for row in work)


def _try_extend_basis(vector: Sequence[ExactRational], basis: list[tuple[int, list[ExactRational]]]) -> tuple[bool, int | None]:
    reduced = list(vector)
    for pivot, basis_vector in basis:
        factor = reduced[pivot]
        if factor.numerator:
            reduced = [_q_sub(reduced[index], _q_mul(factor, basis_vector[index], "basis reduction"), "basis reduction") for index in range(len(reduced))]
    pivot = next((index for index, value in enumerate(reduced) if value.numerator != 0), None)
    if pivot is None:
        return False, None
    pivot_value = reduced[pivot]
    normalized = [_q_div(value, pivot_value, "basis normalization") for value in reduced]
    for basis_index, (old_pivot, basis_vector) in enumerate(basis):
        factor = basis_vector[pivot]
        if factor.numerator:
            basis[basis_index] = (old_pivot, [_q_sub(basis_vector[index], _q_mul(factor, normalized[index], "basis insertion"), "basis insertion") for index in range(len(normalized))])
    basis.append((pivot, normalized))
    basis.sort(key=lambda item: item[0])
    return True, pivot


class _TrackedReader:
    def __init__(self, view: TrainingHankelView) -> None:
        self.view = view
        self.events: list[TrainingReadEvent] = []
        self.decisions: list[BasisDecision] = []
        self.target_wires = {_canonical_key(key) for key in view._target_declaration.keys}
        self.atom_map = {_canonical_key(atom.key): atom for atom in view._training_atoms}

    def read_key(self, key: ResponseAtomKey, purpose: str) -> ExactRational:
        wire = _canonical_key(key)
        if wire in self.target_wires:
            raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: target atom read attempted during fitting")
        atom = self.atom_map.get(wire)
        if atom is None:
            raise StrictContractError(f"CPU_RECOVERY_PREREQUISITE_BLOCKED: missing training atom for {purpose}")
        atom.__post_init__()
        self.events.append(TrainingReadEvent(len(self.events), purpose, key))
        return atom.value

    def read(self, row: HankelRowKey, column: HankelColumnKey, purpose: str) -> ExactRational:
        return self.read_key(make_response_atom_key(row, column), purpose)


def _q_to_wire(value: ExactRational) -> dict[str, Any]:
    return _q_check(value, "wire rational").to_dict()


def _vector_wire(values: Sequence[ExactRational]) -> list[dict[str, Any]]:
    return [_q_to_wire(value) for value in values]


def _matrix_wire(values: Sequence[Sequence[ExactRational]]) -> list[list[dict[str, Any]]]:
    return [_vector_wire(row) for row in values]


@dataclass(frozen=True)
class _FitResult:
    wire: dict[str, Any]
    rank: int
    basis_rows: tuple[HankelRowKey, ...]
    basis_columns: tuple[HankelColumnKey, ...]
    alphas: tuple[tuple[str, tuple[ExactRational, ...]], ...]
    action_matrices: tuple[tuple[str, tuple[tuple[ExactRational, ...], ...]], ...]
    betas: tuple[tuple[ResponseChannelKey, tuple[ExactRational, ...]], ...]
    footprint: TrainingFootprint


def _derive_fit(view: TrainingHankelView) -> _FitResult:
    if type(view) is not TrainingHankelView:
        raise StrictContractError("fit requires an exact TrainingHankelView")
    view_wire = view.to_dict()
    spec = view._spec
    reader = _TrackedReader(view)
    base_matrix: list[list[ExactRational]] = []
    for row in spec.rows:
        base_matrix.append([reader.read(row, column, "rank_candidate") for column in spec.columns])

    row_basis_work: list[tuple[int, list[ExactRational]]] = []
    row_indices: list[int] = []
    for index, vector in enumerate(base_matrix):
        accepted, pivot = _try_extend_basis(vector, row_basis_work)
        pivot_key = None if pivot is None else spec.columns[pivot]
        reader.decisions.append(BasisDecision("row", spec.rows[index], accepted, pivot_key))
        if accepted:
            row_indices.append(index)
    rank = len(row_indices)
    if rank == 0:
        raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: training Hankel rank is zero")
    if rank > spec.r_cap:
        raise StrictContractError("CPU_RECOVERY_PREREQUISITE_BLOCKED: training rank exceeds r_cap")

    column_basis_work: list[tuple[int, list[ExactRational]]] = []
    column_indices: list[int] = []
    for column_index, column in enumerate(spec.columns):
        vector = [reader.read(spec.rows[row_index], column, "column_basis_candidate") for row_index in row_indices]
        accepted, pivot = _try_extend_basis(vector, column_basis_work)
        pivot_key = None if pivot is None else spec.rows[row_indices[pivot]]
        reader.decisions.append(BasisDecision("column", column, accepted, pivot_key))
        if accepted:
            column_indices.append(column_index)
        if len(column_indices) == rank:
            # Continue recording rejected/accepted rank candidates is not needed:
            # the lexicographically first full basis is already determined.
            break
    if len(column_indices) != rank:
        raise StrictContractError("column basis does not realize training rank")

    basis_rows = tuple(spec.rows[index] for index in row_indices)
    basis_columns = tuple(spec.columns[index] for index in column_indices)
    core = tuple(tuple(reader.read(row, column, "core_C") for column in basis_columns) for row in basis_rows)
    inverse = _inverse(core)

    row_coordinates = tuple(
        _row_times_matrix(
            tuple(
                base_matrix[row_index][column_index]
                for column_index in column_indices
            ),
            inverse,
            "row coordinate",
        )
        for row_index in range(len(spec.rows))
    )
    row_coordinate_map = {
        (row.task_id, row.prefix_word): row_coordinates[index]
        for index, row in enumerate(spec.rows)
    }
    column_coordinates = tuple(
        tuple(base_matrix[row_index][column_index] for row_index in row_indices)
        for column_index in range(len(spec.columns))
    )
    column_coordinate_map = {
        (column.suffix_word, _canonical_key(column.channel)): column_coordinates[index]
        for index, column in enumerate(spec.columns)
    }

    # Exact rank plus an invertible cross entails this factorization; checking
    # it explicitly keeps the sealed capability fail-closed under arithmetic
    # or source corruption.  Its nr*nc*r_train work is covered by the first
    # registered W_H term.
    for row_index in range(len(spec.rows)):
        for column_index in range(len(spec.columns)):
            if _dot(
                row_coordinates[row_index],
                column_coordinates[column_index],
                "Hankel cross factorization",
            ) != base_matrix[row_index][column_index]:
                raise StrictContractError(
                    "CPU_RECOVERY_PREREQUISITE_BLOCKED: exact Hankel cross factorization failed"
                )

    alphas: list[tuple[str, tuple[ExactRational, ...]]] = []
    for task_id in spec.task_ids:
        initial = tuple(reader.read(HankelRowKey(task_id, ()), column, "alpha") for column in basis_columns)
        alphas.append((task_id, _row_times_matrix(initial, inverse, "alpha realization")))

    action_matrices: list[tuple[str, tuple[tuple[ExactRational, ...], ...]]] = []
    for action in spec.actions:
        shifted = tuple(tuple(reader.read(HankelRowKey(row.task_id, row.prefix_word + (action.action_id,)), column, "action_shift") for column in basis_columns) for row in basis_rows)
        action_matrices.append((action.action_id, _matrix_multiply(shifted, inverse, "action realization")))

    betas: list[tuple[ResponseChannelKey, tuple[ExactRational, ...]]] = []
    for channel in spec.channels:
        column = HankelColumnKey((), channel)
        betas.append((channel, tuple(reader.read(row, column, "beta") for row in basis_rows)))

    # Exact two-sided Hankel closure turns the cross factorization into a word
    # realization without replaying whole histories.  Rows use u=q.a and
    # columns use v=a.tail, so the natural noncommutative order is preserved:
    # X_(q.a)=X_q A_a and Y_(a.tail)=A_a Y_tail.  The row/column checks cost
    # O((nr+nc)r_train^2), also covered by nr*nc*min(nr,nc).
    action_map = dict(action_matrices)
    for row in spec.rows:
        if not row.prefix_word:
            continue
        parent = row_coordinate_map[(row.task_id, row.prefix_word[:-1])]
        expected = _row_times_matrix(
            parent,
            action_map[row.prefix_word[-1]],
            "row shift consistency",
        )
        if expected != row_coordinate_map[(row.task_id, row.prefix_word)]:
            raise StrictContractError(
                "CPU_RECOVERY_PREREQUISITE_BLOCKED: exact row shift consistency failed"
            )
    for column in spec.columns:
        if not column.suffix_word:
            continue
        tail = column_coordinate_map[
            (column.suffix_word[1:], _canonical_key(column.channel))
        ]
        expected = tuple(
            _dot(
                matrix_row,
                tail,
                "column shift consistency",
            )
            for matrix_row in action_map[column.suffix_word[0]]
        )
        if expected != column_coordinate_map[
            (column.suffix_word, _canonical_key(column.channel))
        ]:
            raise StrictContractError(
                "CPU_RECOVERY_PREREQUISITE_BLOCKED: exact column shift consistency failed"
            )

    footprint = TrainingFootprint(tuple(reader.events), tuple(reader.decisions))
    wire = {
        "schema_version": REALIZATION_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "predictive_tier": PREDICTIVE_TIER,
        "view_sha256": _sha256(view_wire),
        "taxonomy_sha256": spec.taxonomy_sha256,
        "target_declaration_sha256": _sha256(view._target_declaration.to_dict()),
        "r_cap": spec.r_cap,
        "r_train": rank,
        "basis_rows": [row.to_dict() for row in basis_rows],
        "basis_columns": [column.to_dict() for column in basis_columns],
        "core": _matrix_wire(core),
        "core_inverse": _matrix_wire(inverse),
        "alphas": [{"task_id": task, "values": _vector_wire(values)} for task, values in alphas],
        "action_matrices": [{"action_id": action, "values": _matrix_wire(values)} for action, values in action_matrices],
        "betas": [{"channel": channel.to_dict(), "values": _vector_wire(values)} for channel, values in betas],
        "training_footprint": footprint.to_dict(),
    }
    return _FitResult(wire, rank, basis_rows, basis_columns, tuple(alphas), tuple(action_matrices), tuple(betas), footprint)


@dataclass(frozen=True)
class BoundedRationalRealization:
    _view: TrainingHankelView = field(repr=False)
    _view_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not BoundedRationalRealization or self._construction_seal is not _REALIZATION_SEAL:
            raise StrictContractError("bounded realization requires its fit gate")
        if type(self._view) is not TrainingHankelView:
            raise StrictContractError("bounded realization view is not exact")
        if _digest(self._view_seal_sha256, "realization view seal") != _sha256(self._view.to_dict()):
            raise StrictContractError("bounded realization source seal mismatch")

    @property
    def r_train(self) -> int:
        return _derive_fit(self._view).rank

    @property
    def basis_rows(self) -> tuple[HankelRowKey, ...]:
        return _derive_fit(self._view).basis_rows

    @property
    def basis_columns(self) -> tuple[HankelColumnKey, ...]:
        return _derive_fit(self._view).basis_columns

    @property
    def training_footprint(self) -> TrainingFootprint:
        return _derive_fit(self._view).footprint

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _REALIZATION_SEAL:
            raise StrictContractError("bounded realization construction seal changed")
        if _sha256(self._view.to_dict()) != _digest(self._view_seal_sha256, "realization view seal"):
            raise StrictContractError("bounded realization retained view changed")
        return _derive_fit(self._view).wire

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], view: TrainingHankelView) -> "BoundedRationalRealization":
        if cls is not BoundedRationalRealization:
            raise StrictContractError("polymorphic realization parsing is forbidden")
        expected = fit_bounded_rational_realization(view)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError("realization wire does not match external training authority")
        return expected


def fit_bounded_rational_realization(view: TrainingHankelView) -> BoundedRationalRealization:
    # The complete training-only derivation is the construction gate.  Later
    # serialization rederives against the retained source seal, but the factory
    # itself performs the fit exactly once.
    _derive_fit(view)
    return BoundedRationalRealization(
        view, _sha256(view.to_dict()), _construction_seal=_REALIZATION_SEAL
    )


# ---------------------------------------------------------------------------
# Frozen-target predictive residuals


@dataclass(frozen=True)
class ExactTargetResponseSet:
    set_id: str
    taxonomy_sha256: str
    atoms: tuple[ExactResponseAtom, ...]

    def __post_init__(self) -> None:
        if type(self) is not ExactTargetResponseSet:
            raise StrictContractError("target-response-set subclasses are forbidden")
        _string(self.set_id, "target response set ID")
        object.__setattr__(
            self,
            "taxonomy_sha256",
            _digest(self.taxonomy_sha256, "target response taxonomy digest"),
        )
        if (
            type(self.atoms) is not tuple
            or not self.atoms
            or not all(type(atom) is ExactResponseAtom for atom in self.atoms)
        ):
            raise StrictContractError(
                "target responses are not a nonempty exact atom tuple"
            )
        minimum_key_bytes = len(ATOM_KEY_SCHEMA.encode("utf-8")) + 3
        if len(self.atoms) > MAX_HANKEL_KEY_BYTES // minimum_key_bytes:
            raise StrictContractError(
                "CPU_RECOVERY_PREREQUISITE_BLOCKED: target response count exceeds the key-byte-derived cap"
            )
        key_bytes = 0
        for atom in self.atoms:
            key_bytes = _charge_semantic_key(key_bytes, atom.key)
        for atom in self.atoms:
            atom.__post_init__()
        ordered = tuple(sorted(self.atoms, key=lambda atom: _canonical_key(atom.key)))
        wires = tuple(_canonical_key(atom.key) for atom in ordered)
        if len(set(wires)) != len(wires):
            raise StrictContractError("target response set contains duplicate keys")
        object.__setattr__(self, "atoms", ordered)

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": TARGET_SET_SCHEMA,
            "set_id": self.set_id,
            "taxonomy_sha256": self.taxonomy_sha256,
            "atoms": [atom.to_dict() for atom in self.atoms],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactTargetResponseSet":
        if cls is not ExactTargetResponseSet:
            raise StrictContractError("polymorphic target-response parsing is forbidden")
        obj = _object(
            value,
            ("schema_version", "set_id", "taxonomy_sha256", "atoms"),
            "ExactTargetResponseSet",
        )
        _fixed(obj["schema_version"], TARGET_SET_SCHEMA, "target response schema")
        result = cls(
            _string(obj["set_id"], "target response set ID"),
            _digest(obj["taxonomy_sha256"], "target response taxonomy digest"),
            tuple(
                ExactResponseAtom.from_dict(item)
                for item in _array(obj["atoms"], "target response atoms")
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("target response set is not canonical")
        return result


@dataclass(frozen=True)
class ChannelResidualReport:
    scope: str
    channel: ResponseChannelKey | None
    target_count: int
    prediction_count: int
    abstention_count: int
    exact_match_count: int
    coverage: ExactRational
    exact_match_fraction: ExactRational
    l1_error: ExactRational
    max_absolute_error: ExactRational

    def __post_init__(self) -> None:
        if type(self) is not ChannelResidualReport:
            raise StrictContractError("channel residual subclasses are forbidden")
        _string(self.scope, "residual scope")
        if self.channel is not None:
            if type(self.channel) is not ResponseChannelKey:
                raise StrictContractError("residual channel is not exact")
            self.channel.to_dict()
        target_count = _integer(self.target_count, "residual target count", minimum=1)
        prediction_count = _integer(
            self.prediction_count, "residual prediction count"
        )
        abstention_count = _integer(
            self.abstention_count, "residual abstention count"
        )
        exact_match_count = _integer(
            self.exact_match_count, "residual exact-match count"
        )
        if prediction_count + abstention_count != target_count:
            raise StrictContractError("residual coverage counts do not partition targets")
        if exact_match_count > prediction_count:
            raise StrictContractError("exact matches exceed predictions")
        for name, value in (
            ("coverage", self.coverage),
            ("exact-match fraction", self.exact_match_fraction),
            ("L1 error", self.l1_error),
            ("maximum absolute error", self.max_absolute_error),
        ):
            _strict_rational(value, f"residual {name}")
        expected_coverage = ExactRational(prediction_count, target_count)
        expected_match = ExactRational(exact_match_count, target_count)
        if self.coverage != expected_coverage or self.exact_match_fraction != expected_match:
            raise StrictContractError("residual exact fractions disagree with counts")
        if self.l1_error.numerator < 0 or self.max_absolute_error.numerator < 0:
            raise StrictContractError("residual errors must be nonnegative")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": CHANNEL_RESIDUAL_SCHEMA,
            "scope": self.scope,
            "channel": None if self.channel is None else self.channel.to_dict(),
            "target_count": self.target_count,
            "prediction_count": self.prediction_count,
            "abstention_count": self.abstention_count,
            "exact_match_count": self.exact_match_count,
            "coverage": _q_to_wire(self.coverage),
            "exact_match_fraction": _q_to_wire(self.exact_match_fraction),
            "l1_error": _q_to_wire(self.l1_error),
            "max_absolute_error": _q_to_wire(self.max_absolute_error),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ChannelResidualReport":
        if cls is not ChannelResidualReport:
            raise StrictContractError("polymorphic channel-residual parsing is forbidden")
        obj = _object(
            value,
            (
                "schema_version",
                "scope",
                "channel",
                "target_count",
                "prediction_count",
                "abstention_count",
                "exact_match_count",
                "coverage",
                "exact_match_fraction",
                "l1_error",
                "max_absolute_error",
            ),
            "ChannelResidualReport",
        )
        _fixed(obj["schema_version"], CHANNEL_RESIDUAL_SCHEMA, "channel residual schema")
        channel = (
            None
            if obj["channel"] is None
            else ResponseChannelKey.from_dict(obj["channel"])
        )
        result = cls(
            _string(obj["scope"], "residual scope"),
            channel,
            _integer(obj["target_count"], "residual target count", minimum=1),
            _integer(obj["prediction_count"], "residual prediction count"),
            _integer(obj["abstention_count"], "residual abstention count"),
            _integer(obj["exact_match_count"], "residual exact-match count"),
            ExactRational.from_dict(obj["coverage"]),
            ExactRational.from_dict(obj["exact_match_fraction"]),
            ExactRational.from_dict(obj["l1_error"]),
            ExactRational.from_dict(obj["max_absolute_error"]),
        )
        if result.to_dict() != obj:
            raise StrictContractError("channel residual is not canonical")
        return result


@dataclass(frozen=True)
class _PredictionRow:
    key: ResponseAtomKey
    observed: ExactRational
    predicted: ExactRational
    absolute_error: ExactRational

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key.to_dict(),
            "observed": _q_to_wire(self.observed),
            "predicted": _q_to_wire(self.predicted),
            "absolute_error": _q_to_wire(self.absolute_error),
            "covered": True,
            "abstention_reason": NOT_APPLICABLE,
        }


def _predict_from_fit(result: _FitResult, key: ResponseAtomKey) -> ExactRational:
    alpha_map = dict(result.alphas)
    action_map = dict(result.action_matrices)
    beta_map = {_canonical_key(channel): values for channel, values in result.betas}
    try:
        state = alpha_map[key.task_id]
        for action_id in key.action_word:
            state = _row_times_matrix(
                state, action_map[action_id], "target prediction"
            )
        beta = beta_map[_canonical_key(key.channel)]
    except KeyError as exc:
        # The target declaration was frozen against the view vocabulary.  A
        # miss here is authority corruption, not a discretionary abstention.
        raise StrictContractError(
            "target prediction is outside the sealed realization vocabulary"
        ) from exc
    return _dot(state, beta, "target prediction")


def _residual_metrics(
    scope: str,
    channel: ResponseChannelKey | None,
    rows: Sequence[_PredictionRow],
) -> ChannelResidualReport:
    if not rows:
        raise StrictContractError(f"residual scope {scope!r} is empty")
    l1_error = _zero()
    maximum = _zero()
    exact_matches = 0
    for row in rows:
        error = _q_check(row.absolute_error, "residual absolute error")
        l1_error = _q_add(l1_error, error, "residual L1 accumulation")
        if _q_less(maximum, error):
            maximum = error
        if error.numerator == 0:
            exact_matches += 1
    count = len(rows)
    return ChannelResidualReport(
        scope,
        channel,
        count,
        count,
        0,
        exact_matches,
        ExactRational(1),
        ExactRational(exact_matches, count),
        l1_error,
        maximum,
    )


@dataclass(frozen=True)
class _ReportResult:
    wire: dict[str, Any]
    overall: ChannelResidualReport
    per_channel: tuple[ChannelResidualReport, ...]
    ablations: tuple[ChannelResidualReport, ...]


def _derive_report(
    realization: BoundedRationalRealization,
    target_responses: ExactTargetResponseSet,
) -> _ReportResult:
    if type(realization) is not BoundedRationalRealization:
        raise StrictContractError("predictive residual requires an exact realization")
    if type(target_responses) is not ExactTargetResponseSet:
        raise StrictContractError("predictive residual requires an exact target set")
    if realization._construction_seal is not _REALIZATION_SEAL:
        raise StrictContractError("bounded realization construction seal changed")
    realization.__post_init__()
    target_wire = target_responses.to_dict()
    view = realization._view
    spec = view._spec
    declaration = view._target_declaration
    if target_responses.taxonomy_sha256 != spec.taxonomy_sha256:
        raise StrictContractError("target response taxonomy does not match realization")
    declared_wires = tuple(sorted(_canonical_key(key) for key in declaration.keys))
    response_wires = tuple(
        sorted(_canonical_key(atom.key) for atom in target_responses.atoms)
    )
    if response_wires != declared_wires:
        raise StrictContractError(
            "CPU_RECOVERY_PREREQUISITE_BLOCKED: target response set does not exactly equal the preregistered declaration"
        )

    fit = _derive_fit(view)
    realization_wire = fit.wire
    atoms = tuple(
        sorted(
            target_responses.atoms,
            key=lambda atom: _semantic_atom_sort_key(atom.key, spec),
        )
    )
    rows: list[_PredictionRow] = []
    for atom in atoms:
        predicted = _predict_from_fit(fit, atom.key)
        error = _q_abs(_q_sub(predicted, atom.value, "predictive residual"))
        rows.append(_PredictionRow(atom.key, atom.value, predicted, error))
    if not rows:
        raise StrictContractError("predictive residual target set is empty")

    overall = _residual_metrics("all", None, rows)
    per_channel: list[ChannelResidualReport] = []
    for channel in spec.channels:
        selected = [row for row in rows if row.key.channel == channel]
        if selected:
            per_channel.append(
                _residual_metrics(f"channel:{channel.channel_id}", channel, selected)
            )

    class_rows: dict[str, list[_PredictionRow]] = {
        "nonterminal": [],
        "closed_terminal": [],
        "sink_terminal": [],
        "terminal_all": [],
    }
    for row in rows:
        class_name = row.key.channel.channel_class.value
        class_rows[class_name].append(row)
        if row.key.channel.channel_class in {
            PredictiveChannelClass.CLOSED_TERMINAL,
            PredictiveChannelClass.SINK_TERMINAL,
        }:
            class_rows["terminal_all"].append(row)
    ablations = tuple(
        _residual_metrics(scope, None, class_rows[scope])
        for scope in (
            "nonterminal",
            "closed_terminal",
            "sink_terminal",
            "terminal_all",
        )
        if class_rows[scope]
    )
    ablation_map = {report.scope: report.to_dict() for report in ablations}
    wire = {
        "schema_version": RESIDUAL_REPORT_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "predictive_tier": PREDICTIVE_TIER,
        "realization_sha256": _sha256(realization_wire),
        "target_response_set_sha256": _sha256(target_wire),
        "target_declaration_sha256": _sha256(declaration.to_dict()),
        "taxonomy_sha256": spec.taxonomy_sha256,
        "target_count": overall.target_count,
        "prediction_count": overall.prediction_count,
        "abstention_count": overall.abstention_count,
        "exact_match_count": overall.exact_match_count,
        "coverage": _q_to_wire(overall.coverage),
        "exact_match_fraction": _q_to_wire(overall.exact_match_fraction),
        "l1_error": _q_to_wire(overall.l1_error),
        "max_absolute_error": _q_to_wire(overall.max_absolute_error),
        "responses": [row.to_dict() for row in rows],
        "per_channel": [report.to_dict() for report in per_channel],
        "ablations": ablation_map,
    }
    return _ReportResult(
        wire, overall, tuple(per_channel), ablations
    )


@dataclass(frozen=True)
class PredictiveResidualReport:
    _realization: BoundedRationalRealization = field(repr=False)
    _target_responses: ExactTargetResponseSet = field(repr=False)
    _realization_seal_sha256: str = field(repr=False)
    _target_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not PredictiveResidualReport or self._construction_seal is not _REPORT_SEAL:
            raise StrictContractError("predictive residual report requires its evaluation gate")
        if type(self._realization) is not BoundedRationalRealization or type(self._target_responses) is not ExactTargetResponseSet:
            raise StrictContractError("predictive residual retained authorities are not exact")
        _digest(self._realization_seal_sha256, "report realization seal")
        _digest(self._target_seal_sha256, "report target seal")

    def _validated_result(self) -> _ReportResult:
        if self._construction_seal is not _REPORT_SEAL:
            raise StrictContractError("predictive residual construction seal changed")
        result = _derive_report(self._realization, self._target_responses)
        if result.wire["realization_sha256"] != _digest(
            self._realization_seal_sha256, "report realization seal"
        ):
            raise StrictContractError("predictive residual retained realization changed")
        if result.wire["target_response_set_sha256"] != _digest(
            self._target_seal_sha256, "report target seal"
        ):
            raise StrictContractError("predictive residual retained target set changed")
        return result

    @property
    def overall(self) -> ChannelResidualReport:
        return self._validated_result().overall

    @property
    def per_channel(self) -> tuple[ChannelResidualReport, ...]:
        return self._validated_result().per_channel

    @property
    def ablations(self) -> tuple[ChannelResidualReport, ...]:
        return self._validated_result().ablations

    def to_dict(self) -> dict[str, Any]:
        return self._validated_result().wire

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        realization: BoundedRationalRealization,
        target_responses: ExactTargetResponseSet,
    ) -> "PredictiveResidualReport":
        if cls is not PredictiveResidualReport:
            raise StrictContractError("polymorphic residual-report parsing is forbidden")
        expected = evaluate_predictive_residual(realization, target_responses)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError("predictive residual wire does not match external authorities")
        return expected


def evaluate_predictive_residual(
    realization: BoundedRationalRealization,
    target_responses: ExactTargetResponseSet,
) -> PredictiveResidualReport:
    result = _derive_report(realization, target_responses)
    report = PredictiveResidualReport(
        realization,
        target_responses,
        result.wire["realization_sha256"],
        result.wire["target_response_set_sha256"],
        _construction_seal=_REPORT_SEAL,
    )
    # `_derive_report` is the one evaluation pass for this factory call.
    # Subsequent serialization remains source-rederived and seal-checked.
    return report


__all__ = [
    "MAX_HANKEL_ROWS",
    "MAX_HANKEL_COLUMNS",
    "MAX_HANKEL_CELLS",
    "MAX_HANKEL_RANK",
    "MAX_HANKEL_KEY_BYTES",
    "MAX_HANKEL_WORK_UNITS",
    "PREDICTIVE_TIER",
    "PredictiveChannelClass",
    "PredictiveActionSymbol",
    "ResponseChannelKey",
    "ResponseAtomKey",
    "HankelRowKey",
    "HankelColumnKey",
    "ExactResponseAtom",
    "TargetAtomDeclaration",
    "HankelTrainingSpec",
    "TrainingReadEvent",
    "BasisDecision",
    "TrainingFootprint",
    "TrainingHankelView",
    "BoundedRationalRealization",
    "ExactTargetResponseSet",
    "ChannelResidualReport",
    "PredictiveResidualReport",
    "make_response_atom_key",
    "make_training_hankel_view",
    "fit_bounded_rational_realization",
    "evaluate_predictive_residual",
]
