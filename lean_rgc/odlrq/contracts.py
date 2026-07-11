from __future__ import annotations

"""Strict, versioned semantic contracts for the U05 apparatus.

The contracts in this module are intentionally not adapters for legacy
``AuditRecord`` objects.  Every ``from_dict`` rejects unknown fields, and every
``to_dict`` is accepted by the integer/string-only canonical JSON serializer in
``kernel_state_identity``.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from lean_rgc.lean.kernel_state_identity import (
    STATE_IDENTITY_SCHEMA,
    StateIdentityKey,
    StrictIdentityError,
    canonical_json_bytes,
    debt_readout_from_identity,
)


U05_SEMANTICS_VERSION = "lean-rgc-u05-rpc-semantics-v1"
ACTION_SYMBOL_SCHEMA = "lean-rgc-odlrq-action-symbol-v1"
BOUND_ACTION_SCHEMA = "lean-rgc-odlrq-bound-action-v1"
OBSERVATION_FRAME_SCHEMA = "lean-rgc-odlrq-observation-frame-v1"
TRANSITION_SEMANTICS_SCHEMA = "lean-rgc-odlrq-transition-semantics-v1"
STATE_DELTA_SCHEMA = "lean-rgc-odlrq-canonical-state-delta-v1"
REPLAY_COMPARABLE_SCHEMA = "lean-rgc-u05-replay-comparable-v1"
REPLAY_VERIFICATION_SCHEMA = "lean-rgc-u05-replay-v1"
CAP_SEMANTICS_SCHEMA = "lean-rgc-u05-cap-semantics-v1"
DEBT_READOUT_SCHEMA = "lean-rgc-u05-debt-readout-v1"
FIELD_COVERAGE_SCHEMA = "lean-rgc-u05-field-coverage-v1"
CENSOR_SCHEMA = "lean-rgc-u05-censor-v1"
EXACT_KERNEL_TRANSITION_CORE_SCHEMA = "lean-rgc-u05-exact-kernel-transition-core-v1"
U05_PROBE_TRANSITION_SCHEMA = "lean-rgc-u05-probe-transition-v1"
U05_TASK_SCHEMA = "lean-rgc-u05-task-v1"
EPISODE_BUDGET_SENTINEL = "NOT_ENFORCED_DEVELOPMENT_ONLY"


class StrictContractError(ValueError):
    """A payload is not a member of a strict ODLRQ/U05 contract."""


def _obj(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an object")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an array")
    return value


def _str(value: Any, where: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty string")
    return value


def _int(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise StrictContractError(f"{where} must be an integer >= {minimum}")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictContractError(f"{where} must be a boolean")
    return value


def _exact_fields(
    value: Mapping[str, Any], expected: set[str], where: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise StrictContractError(
            f"{where} field mismatch; missing={missing}, unknown={unknown}"
        )


_HEX64_RE = re.compile(r"[0-9A-Fa-f]{64}\Z")


def _digest(value: Any, where: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HEX64_RE.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be a full SHA-256 hex digest")
    return value.upper()


def _enum(cls: type[Enum], value: Any, where: str) -> Any:
    if type(value) is not str:
        raise StrictContractError(f"{where} must be a string enum")
    try:
        return cls(value)
    except ValueError as exc:
        raise StrictContractError(f"invalid {where}: {value}") from exc


def _unique_strings(value: Any, where: str) -> tuple[str, ...]:
    rows = tuple(_str(item, where) for item in _list(value, where))
    if len(rows) != len(set(rows)):
        raise StrictContractError(f"{where} contains duplicates")
    return rows  # type: ignore[return-value]


class RawTransitionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ORDINARY_FAILURE = "ordinary_failure"


class TotalizedStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    SINK = "sink"


class TargetSelector(str, Enum):
    FIRST = "first"
    LAST = "last"


class ReplayStatus(str, Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"


class FieldCoverageStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    TRUNCATED = "truncated"
    NOT_APPLICABLE = "not_applicable"


class CensorKind(str, Enum):
    HEARTBEAT_EXHAUSTION = "heartbeat_exhaustion"
    WALL_TIMEOUT = "wall_timeout"
    PROCESS_CRASH = "process_crash"
    TRANSPORT_FAILURE = "transport_failure"
    MALFORMED_RESPONSE = "malformed_response"
    REQUIRED_FIELD_TRUNCATED = "required_field_truncated"
    REPLAY_MISMATCH = "replay_mismatch"
    CAP_MISMATCH = "cap_mismatch"
    INSTRUMENT_INCOMPLETE = "instrument_incomplete"


class WorkPackageStatus(str, Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    PASSED = "passed"
    BLOCKED = "blocked"
    KILLED = "killed"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class U05TaskSpec:
    """Exact inline task/prefix record admitted by the U05 RPC adapter."""

    task_id: str
    statement: str
    imports: tuple[str, ...]
    prefix: str
    max_heartbeats: int = 20_000

    def __post_init__(self) -> None:
        _str(self.task_id, "U05TaskSpec.task_id")
        _str(self.statement, "U05TaskSpec.statement")
        if type(self.imports) is not tuple or not self.imports or not all(
            type(item) is str and item for item in self.imports
        ):
            raise StrictContractError("U05TaskSpec.imports must be a nonempty string tuple")
        if len(self.imports) != len(set(self.imports)):
            raise StrictContractError("U05TaskSpec.imports contains duplicates")
        if type(self.prefix) is not str:
            raise StrictContractError("U05TaskSpec.prefix must be a string")
        if self.max_heartbeats != 20_000:
            raise StrictContractError("U05TaskSpec max_heartbeats must be 20000")

    def to_rpc_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "statement": self.statement,
            "imports": list(self.imports),
            "prefix": self.prefix,
            "max_heartbeats": self.max_heartbeats,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": U05_TASK_SCHEMA, **self.to_rpc_dict()}

    @classmethod
    def from_frozen_record(cls, value: Mapping[str, Any]) -> "U05TaskSpec":
        obj = _obj(value, "U05 task record")
        _exact_fields(
            obj,
            {"task_id", "statement", "imports", "prefix", "max_heartbeats"},
            "U05 task record",
        )
        imports = tuple(_str(item, "task import") for item in _list(obj["imports"], "imports"))
        prefix = obj["prefix"]
        if type(prefix) is not str:
            raise StrictContractError("U05 task prefix must be a string")
        return cls(
            task_id=_str(obj["task_id"], "task_id"),  # type: ignore[arg-type]
            statement=_str(obj["statement"], "statement"),  # type: ignore[arg-type]
            imports=imports,  # type: ignore[arg-type]
            prefix=prefix,
            max_heartbeats=_int(obj["max_heartbeats"], "max_heartbeats", minimum=1),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "U05TaskSpec":
        obj = _obj(value, "U05TaskSpec")
        _exact_fields(
            obj,
            {
                "schema_version",
                "task_id",
                "statement",
                "imports",
                "prefix",
                "max_heartbeats",
            },
            "U05TaskSpec",
        )
        if obj["schema_version"] != U05_TASK_SCHEMA:
            raise StrictContractError("wrong U05TaskSpec schema")
        return cls.from_frozen_record(
            {key: item for key, item in obj.items() if key != "schema_version"}
        )


@dataclass(frozen=True)
class ObservationFrameId:
    environment_content_digest: str
    source_lane: str
    granularity: str
    coordinate_schema_digest: str
    normalization_id: str
    extractor_version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "environment_content_digest",
            _digest(self.environment_content_digest, "environment_content_digest"),
        )
        object.__setattr__(
            self,
            "coordinate_schema_digest",
            _digest(self.coordinate_schema_digest, "coordinate_schema_digest"),
        )
        for field_name in (
            "source_lane",
            "granularity",
            "normalization_id",
            "extractor_version",
        ):
            _str(getattr(self, field_name), f"ObservationFrameId.{field_name}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": OBSERVATION_FRAME_SCHEMA,
            "environment_content_digest": self.environment_content_digest,
            "source_lane": self.source_lane,
            "granularity": self.granularity,
            "coordinate_schema_digest": self.coordinate_schema_digest,
            "normalization_id": self.normalization_id,
            "extractor_version": self.extractor_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationFrameId":
        obj = _obj(value, "ObservationFrameId")
        fields = {
            "schema_version",
            "environment_content_digest",
            "source_lane",
            "granularity",
            "coordinate_schema_digest",
            "normalization_id",
            "extractor_version",
        }
        _exact_fields(obj, fields, "ObservationFrameId")
        if obj["schema_version"] != OBSERVATION_FRAME_SCHEMA:
            raise StrictContractError("wrong ObservationFrameId schema")
        return cls(
            environment_content_digest=obj["environment_content_digest"],
            source_lane=obj["source_lane"],
            granularity=obj["granularity"],
            coordinate_schema_digest=obj["coordinate_schema_digest"],
            normalization_id=obj["normalization_id"],
            extractor_version=obj["extractor_version"],
        )


@dataclass(frozen=True)
class BehavioralObservationKey:
    frame: ObservationFrameId
    projection_id: str
    coordinate_key: str

    def __post_init__(self) -> None:
        _str(self.projection_id, "BehavioralObservationKey.projection_id")
        _str(self.coordinate_key, "BehavioralObservationKey.coordinate_key")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "lean-rgc-odlrq-behavioral-observation-key-v1",
            "frame": self.frame.to_dict(),
            "projection_id": self.projection_id,
            "coordinate_key": self.coordinate_key,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BehavioralObservationKey":
        obj = _obj(value, "BehavioralObservationKey")
        _exact_fields(
            obj,
            {"schema_version", "frame", "projection_id", "coordinate_key"},
            "BehavioralObservationKey",
        )
        if obj["schema_version"] != "lean-rgc-odlrq-behavioral-observation-key-v1":
            raise StrictContractError("wrong BehavioralObservationKey schema")
        return cls(
            ObservationFrameId.from_dict(_obj(obj["frame"], "frame")),
            _str(obj["projection_id"], "projection_id"),  # type: ignore[arg-type]
            _str(obj["coordinate_key"], "coordinate_key"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class TransitionSemanticsId:
    compiler_build_digest: str
    dependency_import_digest: str
    action_grammar_digest: str
    target_site_convention: str
    premise_simp_typeclass_whitelist_digest: str
    transparency_options_digest: str
    per_action_budget: int
    episode_budget: str
    cache_policy: str = "bypass"

    def __post_init__(self) -> None:
        for field_name in (
            "compiler_build_digest",
            "dependency_import_digest",
            "action_grammar_digest",
            "premise_simp_typeclass_whitelist_digest",
            "transparency_options_digest",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        _str(self.target_site_convention, "target_site_convention")
        _int(self.per_action_budget, "per_action_budget", minimum=1)
        if self.episode_budget != EPISODE_BUDGET_SENTINEL:
            raise StrictContractError("U05 episode budget must be the development sentinel")
        if self.cache_policy != "bypass":
            raise StrictContractError("U05 cache policy must be bypass")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TRANSITION_SEMANTICS_SCHEMA,
            "compiler_build_digest": self.compiler_build_digest,
            "dependency_import_digest": self.dependency_import_digest,
            "action_grammar_digest": self.action_grammar_digest,
            "target_site_convention": self.target_site_convention,
            "premise_simp_typeclass_whitelist_digest": self.premise_simp_typeclass_whitelist_digest,
            "transparency_options_digest": self.transparency_options_digest,
            "per_action_budget": self.per_action_budget,
            "episode_budget": self.episode_budget,
            "cache_policy": self.cache_policy,
        }


@dataclass(frozen=True)
class ActionSymbol:
    action_id: str
    opcode: str
    target_selector: TargetSelector
    premise_slot_rule_id: str | None
    premise_selector_ordinal: int | None
    expected_normalized_type_pattern: str | None
    global_constant: str | None
    opaque_hyperedge_source: str | None
    opaque_hyperedge_digest: str | None
    cap_profile_id: str

    def __post_init__(self) -> None:
        for field_name in ("action_id", "opcode", "cap_profile_id"):
            _str(getattr(self, field_name), f"ActionSymbol.{field_name}")
        if self.cap_profile_id != "u05-hb-20000-cache-bypass-v1":
            raise StrictContractError("ActionSymbol cap profile is not the frozen U05 profile")
        if not isinstance(self.target_selector, TargetSelector):
            object.__setattr__(
                self,
                "target_selector",
                _enum(TargetSelector, self.target_selector, "target_selector"),
            )
        _str(self.premise_slot_rule_id, "premise_slot_rule_id", optional=True)
        if self.premise_selector_ordinal is not None:
            _int(self.premise_selector_ordinal, "premise_selector_ordinal")
        _str(
            self.expected_normalized_type_pattern,
            "expected_normalized_type_pattern",
            optional=True,
        )
        _str(self.global_constant, "global_constant", optional=True)
        _str(self.opaque_hyperedge_source, "opaque_hyperedge_source", optional=True)
        object.__setattr__(
            self,
            "opaque_hyperedge_digest",
            _digest(
                self.opaque_hyperedge_digest,
                "opaque_hyperedge_digest",
                optional=True,
            ),
        )
        if self.opcode not in {"constructor", "exact_local", "exact_const", "opaque_tactic"}:
            raise StrictContractError("opcode is outside the frozen U05 grammar")
        if (self.premise_slot_rule_id is None) != (
            self.premise_selector_ordinal is None
        ):
            raise StrictContractError("symbolic premise rule and ordinal must be joint")
        if self.opcode == "exact_local":
            if (
                self.premise_slot_rule_id is None
                or self.expected_normalized_type_pattern is None
                or self.global_constant is not None
                or self.opaque_hyperedge_source is not None
                or self.opaque_hyperedge_digest is not None
            ):
                raise StrictContractError("exact_local has incomplete or foreign semantics")
        elif self.opcode == "exact_const":
            if (
                self.premise_slot_rule_id is not None
                or self.expected_normalized_type_pattern is None
                or self.global_constant is None
                or self.opaque_hyperedge_source is not None
                or self.opaque_hyperedge_digest is not None
            ):
                raise StrictContractError("exact_const has incomplete or foreign semantics")
        elif self.opcode == "opaque_tactic":
            if (
                self.premise_slot_rule_id is not None
                or self.expected_normalized_type_pattern is not None
                or self.global_constant is not None
                or self.opaque_hyperedge_source is None
                or self.opaque_hyperedge_digest is None
            ):
                raise StrictContractError("opaque_tactic has incomplete or foreign semantics")
            if _digest_from_utf8(self.opaque_hyperedge_source) != self.opaque_hyperedge_digest:
                raise StrictContractError("opaque hyperedge source digest mismatch")
        elif any(
            value is not None
            for value in (
                self.premise_slot_rule_id,
                self.expected_normalized_type_pattern,
                self.global_constant,
                self.opaque_hyperedge_source,
                self.opaque_hyperedge_digest,
            )
        ):
            raise StrictContractError("constructor cannot carry premise/constant/opaque data")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ACTION_SYMBOL_SCHEMA,
            "action_id": self.action_id,
            "opcode": self.opcode,
            "target_selector": self.target_selector.value,
            "premise_slot_rule_id": self.premise_slot_rule_id,
            "premise_selector_ordinal": self.premise_selector_ordinal,
            "expected_normalized_type_pattern": self.expected_normalized_type_pattern,
            "global_constant": self.global_constant,
            "opaque_hyperedge_source": self.opaque_hyperedge_source,
            "opaque_hyperedge_digest": self.opaque_hyperedge_digest,
            "cap_profile_id": self.cap_profile_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionSymbol":
        obj = _obj(value, "ActionSymbol")
        fields = {
            "schema_version",
            "action_id",
            "opcode",
            "target_selector",
            "premise_slot_rule_id",
            "premise_selector_ordinal",
            "expected_normalized_type_pattern",
            "global_constant",
            "opaque_hyperedge_source",
            "opaque_hyperedge_digest",
            "cap_profile_id",
        }
        _exact_fields(obj, fields, "ActionSymbol")
        if obj["schema_version"] != ACTION_SYMBOL_SCHEMA:
            raise StrictContractError("wrong ActionSymbol schema")
        return cls(
            action_id=_str(obj["action_id"], "action_id"),  # type: ignore[arg-type]
            opcode=_str(obj["opcode"], "opcode"),  # type: ignore[arg-type]
            target_selector=_enum(TargetSelector, obj["target_selector"], "target_selector"),
            premise_slot_rule_id=_str(
                obj["premise_slot_rule_id"], "premise_slot_rule_id", optional=True
            ),
            premise_selector_ordinal=(
                None
                if obj["premise_selector_ordinal"] is None
                else _int(obj["premise_selector_ordinal"], "premise_selector_ordinal")
            ),
            expected_normalized_type_pattern=_str(
                obj["expected_normalized_type_pattern"],
                "expected_normalized_type_pattern",
                optional=True,
            ),
            global_constant=_str(obj["global_constant"], "global_constant", optional=True),
            opaque_hyperedge_source=_str(
                obj["opaque_hyperedge_source"], "opaque_hyperedge_source", optional=True
            ),
            opaque_hyperedge_digest=_digest(
                obj["opaque_hyperedge_digest"], "opaque_hyperedge_digest", optional=True
            ),
            cap_profile_id=_str(obj["cap_profile_id"], "cap_profile_id"),  # type: ignore[arg-type]
        )

    @classmethod
    def from_frozen_action_record(cls, value: Mapping[str, Any]) -> "ActionSymbol":
        """Bind one exact plan action row without importing runtime names."""

        obj = _obj(value, "frozen action")
        fields = {
            "action_id",
            "opcode",
            "target_selector",
            "premise_slot_rule_id",
            "premise_selector_ordinal",
            "expected_normalized_type_signature",
            "global_constant",
            "opaque_hyperedge_source",
            "opaque_hyperedge_digest",
            "max_heartbeats",
        }
        _exact_fields(obj, fields, "frozen action")
        max_heartbeats = _int(obj["max_heartbeats"], "max_heartbeats", minimum=1)
        if max_heartbeats != 20_000:
            raise StrictContractError("frozen U05 action max_heartbeats must be 20000")
        # The ordinal/global constant are part of the named symbolic rule and
        # are checked by the binder.  They are not a resolved declaration/hash.
        premise_ordinal = (
            None
            if obj["premise_selector_ordinal"] is None
            else _int(obj["premise_selector_ordinal"], "premise_selector_ordinal")
        )
        global_constant = _str(obj["global_constant"], "global_constant", optional=True)
        source = _str(
            obj["opaque_hyperedge_source"], "opaque_hyperedge_source", optional=True
        )
        digest = _digest(
            obj["opaque_hyperedge_digest"], "opaque_hyperedge_digest", optional=True
        )
        if (source is None) != (digest is None):
            raise StrictContractError("opaque source and digest must be jointly present")
        if source is not None and _digest_from_utf8(source) != digest:
            raise StrictContractError("opaque hyperedge source digest mismatch")
        return cls(
            action_id=_str(obj["action_id"], "action_id"),  # type: ignore[arg-type]
            opcode=_str(obj["opcode"], "opcode"),  # type: ignore[arg-type]
            target_selector=_enum(TargetSelector, obj["target_selector"], "target_selector"),
            premise_slot_rule_id=_str(
                obj["premise_slot_rule_id"], "premise_slot_rule_id", optional=True
            ),
            premise_selector_ordinal=premise_ordinal,
            expected_normalized_type_pattern=_str(
                obj["expected_normalized_type_signature"],
                "expected_normalized_type_signature",
                optional=True,
            ),
            global_constant=global_constant,
            opaque_hyperedge_source=source,
            opaque_hyperedge_digest=digest,
            cap_profile_id=f"u05-hb-{max_heartbeats}-cache-bypass-v1",
        )


def _digest_from_utf8(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _state_rows(key: StateIdentityKey, field_name: str) -> list[dict[str, Any]]:
    raw = key.full_signature.get(field_name)
    if type(raw) is not list:
        raise StrictContractError(f"state identity lacks {field_name}")
    return [_obj(row, f"state.{field_name}") for row in raw]


def _state_expression_map(key: StateIdentityKey) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _state_rows(key, "expressions"):
        expr_id = _str(row.get("id"), "expression.id")
        if expr_id in out:
            raise StrictContractError("duplicate canonical expression id")
        out[expr_id] = row  # type: ignore[index]
    return out


def _expression_digest(key: StateIdentityKey, expr_id: str) -> str:
    expressions = _state_expression_map(key)
    if expr_id not in expressions:
        raise StrictContractError(f"missing canonical expression: {expr_id}")
    return _digest_from_utf8(canonical_json_bytes(expressions[expr_id]).decode("utf-8"))


def _expression_head_constant(
    expressions: Mapping[str, Mapping[str, Any]], expr_id: str
) -> str | None:
    seen: set[str] = set()
    current = expr_id
    while True:
        if current in seen or current not in expressions:
            raise StrictContractError("cyclic or missing expression head")
        seen.add(current)
        node = expressions[current]
        const_name = node.get("const_name")
        if const_name is not None:
            return _str(const_name, "expression.const_name")
        if node.get("kind") != "app":
            return None
        children = node.get("children")
        if type(children) is not list:
            raise StrictContractError("application expression lacks children")
        fns = [
            _obj(child, "application child")
            for child in children
            if _obj(child, "application child").get("role") == "fn"
        ]
        if len(fns) != 1:
            raise StrictContractError("application expression lacks one fn child")
        current = _str(fns[0].get("expr"), "application fn")  # type: ignore[assignment]


def _matches_frozen_type_pattern(
    *,
    pattern: str,
    expression_id: str,
    expressions: Mapping[str, Mapping[str, Any]],
    local_declarations: Sequence[str],
) -> bool:
    fvar_match = re.fullmatch(r"FVAR_TYPE\(local:(\d+)\)", pattern)
    if fvar_match is not None:
        ordinal = int(fvar_match.group(1))
        if ordinal >= len(local_declarations):
            return False
        node = expressions.get(expression_id)
        if node is None or node.get("kind") != "fvar":
            return False
        return node.get("free_fvars") == [local_declarations[ordinal]]
    const_match = re.fullmatch(r"CONST\(([^()]+)\)", pattern)
    if const_match is not None:
        return _expression_head_constant(expressions, expression_id) == const_match.group(1)
    raise StrictContractError(f"unknown frozen normalized-type pattern: {pattern}")


@dataclass(frozen=True)
class PremiseBinding:
    premise_slot_rule_id: str
    canonical_ordinal: int
    normalized_type_hash: str
    runtime_fvar_id: str

    def __post_init__(self) -> None:
        _str(self.premise_slot_rule_id, "PremiseBinding.premise_slot_rule_id")
        _int(self.canonical_ordinal, "PremiseBinding.canonical_ordinal")
        object.__setattr__(
            self,
            "normalized_type_hash",
            _digest(self.normalized_type_hash, "PremiseBinding.normalized_type_hash"),
        )
        _str(self.runtime_fvar_id, "PremiseBinding.runtime_fvar_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "premise_slot_rule_id": self.premise_slot_rule_id,
            "canonical_ordinal": self.canonical_ordinal,
            "normalized_type_hash": self.normalized_type_hash,
            "runtime_fvar_id": self.runtime_fvar_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PremiseBinding":
        obj = _obj(value, "PremiseBinding")
        _exact_fields(
            obj,
            {
                "premise_slot_rule_id",
                "canonical_ordinal",
                "normalized_type_hash",
                "runtime_fvar_id",
            },
            "PremiseBinding",
        )
        return cls(
            premise_slot_rule_id=_str(
                obj["premise_slot_rule_id"], "premise_slot_rule_id"
            ),  # type: ignore[arg-type]
            canonical_ordinal=_int(obj["canonical_ordinal"], "canonical_ordinal"),
            normalized_type_hash=_digest(
                obj["normalized_type_hash"], "normalized_type_hash"
            ),  # type: ignore[arg-type]
            runtime_fvar_id=_str(obj["runtime_fvar_id"], "runtime_fvar_id"),  # type: ignore[arg-type]
        )

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "premise_slot_rule_id": self.premise_slot_rule_id,
            "canonical_ordinal": self.canonical_ordinal,
            "normalized_type_hash": self.normalized_type_hash,
        }


@dataclass(frozen=True)
class BoundAction:
    symbol: ActionSymbol
    canonical_target_ordinal: int
    target_normalized_type_hash: str
    runtime_target_mvar_id: str
    premises: tuple[PremiseBinding, ...] = ()
    rendered_tactic: str = ""

    def __post_init__(self) -> None:
        _int(self.canonical_target_ordinal, "BoundAction.canonical_target_ordinal")
        object.__setattr__(
            self,
            "target_normalized_type_hash",
            _digest(
                self.target_normalized_type_hash,
                "BoundAction.target_normalized_type_hash",
            ),
        )
        _str(self.runtime_target_mvar_id, "BoundAction.runtime_target_mvar_id")
        if type(self.premises) is not tuple or not all(
            isinstance(row, PremiseBinding) for row in self.premises
        ):
            raise StrictContractError("BoundAction.premises must be PremiseBinding tuple")
        if len({row.premise_slot_rule_id for row in self.premises}) != len(self.premises):
            raise StrictContractError("BoundAction has duplicate premise slots")
        if self.symbol.premise_slot_rule_id is None and self.premises:
            raise StrictContractError("premise-free ActionSymbol cannot bind premises")
        if self.symbol.premise_slot_rule_id is not None and (
            len(self.premises) != 1
            or self.premises[0].premise_slot_rule_id != self.symbol.premise_slot_rule_id
            or self.premises[0].canonical_ordinal
            != self.symbol.premise_selector_ordinal
        ):
            raise StrictContractError("BoundAction does not resolve its symbolic premise slot")
        _str(self.rendered_tactic, "BoundAction.rendered_tactic")
        expected_render = {
            "constructor": "constructor",
            "exact_const": f"exact {self.symbol.global_constant}",
            "opaque_tactic": self.symbol.opaque_hyperedge_source,
        }.get(self.symbol.opcode)
        if self.symbol.opcode == "exact_local":
            expected_render = f"exact {self.premises[0].runtime_fvar_id}"
        if self.rendered_tactic != expected_render:
            raise StrictContractError("rendered tactic ignores frozen symbol/binding semantics")

    @classmethod
    def bind_to_state(
        cls,
        symbol: ActionSymbol,
        state: StateIdentityKey,
        *,
        runtime_goal_mvar_ids: Sequence[str],
        runtime_local_fvar_ids: Sequence[str] | None = None,
    ) -> "BoundAction":
        """Resolve one frozen symbol against one full canonical state.

        The runtime sequences must be in the same ordered-goal/local-declaration
        order used to construct ``state``.  They are retained only for tactic
        rendering; canonical ordinals and normalized expression hashes are the
        semantic binding.
        """

        if state.status != "open":
            raise StrictContractError("an action can bind only to an open state")
        if symbol.cap_profile_id != "u05-hb-20000-cache-bypass-v1":
            raise StrictContractError("ActionSymbol uses a non-U05 cap profile")
        if isinstance(runtime_goal_mvar_ids, (str, bytes)):
            raise StrictContractError("runtime goals must be an ordered sequence")
        runtime_goals = tuple(
            _str(value, "runtime goal mvar") for value in runtime_goal_mvar_ids
        )
        goals = _state_rows(state, "goals")
        if not goals or len(runtime_goals) != len(goals):
            raise StrictContractError("runtime goal order does not cover canonical goals")
        target_ordinal = 0 if symbol.target_selector is TargetSelector.FIRST else len(goals) - 1
        target_goal = goals[target_ordinal]
        target_expr = _str(target_goal.get("target_expr"), "goal.target_expr")
        target_hash = _expression_digest(state, target_expr)  # type: ignore[arg-type]
        expressions = _state_expression_map(state)

        contexts = {
            _str(row.get("id"), "local context.id"): row
            for row in _state_rows(state, "local_contexts")
        }
        context_id = _str(target_goal.get("local_context"), "goal.local_context")
        if context_id not in contexts:
            raise StrictContractError("target goal has no canonical local context")
        declarations_raw = contexts[context_id].get("declarations")
        if type(declarations_raw) is not list or not all(
            type(item) is str and item for item in declarations_raw
        ):
            raise StrictContractError("local-context declarations are malformed")
        declarations = tuple(declarations_raw)
        declaration_rows = {
            _str(row.get("id"), "local declaration.id"): row
            for row in _state_rows(state, "local_declarations")
        }

        premises: tuple[PremiseBinding, ...] = ()
        if symbol.opcode == "constructor":
            rendered = "constructor"
        elif symbol.opcode == "exact_local":
            if runtime_local_fvar_ids is None or isinstance(
                runtime_local_fvar_ids, (str, bytes)
            ):
                raise StrictContractError("exact_local requires ordered runtime fvars")
            runtime_fvars = tuple(
                _str(value, "runtime local fvar") for value in runtime_local_fvar_ids
            )
            if len(runtime_fvars) != len(declarations):
                raise StrictContractError(
                    "runtime local order does not cover canonical declarations"
                )
            ordinal = symbol.premise_selector_ordinal
            if ordinal is None or ordinal >= len(declarations):
                raise StrictContractError("symbolic premise ordinal is unavailable")
            declaration_id = declarations[ordinal]
            declaration = declaration_rows.get(declaration_id)
            if declaration is None:
                raise StrictContractError("symbolic premise declaration is missing")
            premise_type_expr = _str(
                declaration.get("type_expr"), "local declaration.type_expr"
            )
            pattern = symbol.expected_normalized_type_pattern
            if pattern is None or not _matches_frozen_type_pattern(
                pattern=pattern,
                expression_id=premise_type_expr,  # type: ignore[arg-type]
                expressions=expressions,
                local_declarations=declarations,
            ):
                raise StrictContractError("symbolic premise normalized type does not match")
            premise = PremiseBinding(
                premise_slot_rule_id=symbol.premise_slot_rule_id,  # type: ignore[arg-type]
                canonical_ordinal=ordinal,
                normalized_type_hash=_expression_digest(
                    state, premise_type_expr  # type: ignore[arg-type]
                ),
                runtime_fvar_id=runtime_fvars[ordinal],  # type: ignore[arg-type]
            )
            premises = (premise,)
            rendered = f"exact {runtime_fvars[ordinal]}"
        elif symbol.opcode == "exact_const":
            pattern = symbol.expected_normalized_type_pattern
            if pattern is None or not _matches_frozen_type_pattern(
                pattern=pattern,
                expression_id=target_expr,  # type: ignore[arg-type]
                expressions=expressions,
                local_declarations=declarations,
            ):
                raise StrictContractError("target normalized type does not match exact_const")
            rendered = f"exact {symbol.global_constant}"
        else:
            if symbol.opaque_hyperedge_source is None:
                raise StrictContractError("opaque action source is unavailable")
            rendered = symbol.opaque_hyperedge_source

        return cls(
            symbol=symbol,
            canonical_target_ordinal=target_ordinal,
            target_normalized_type_hash=target_hash,
            runtime_target_mvar_id=runtime_goals[target_ordinal],  # type: ignore[arg-type]
            premises=premises,
            rendered_tactic=rendered,
        )

    def semantic_binding_dict(self) -> dict[str, Any]:
        return {
            "canonical_target_ordinal": self.canonical_target_ordinal,
            "target_normalized_type_hash": self.target_normalized_type_hash,
            "premises": [row.semantic_dict() for row in self.premises],
        }

    def to_rpc_action(self) -> dict[str, Any]:
        """Render the exact four-field action accepted by the strict RPC client."""

        return {
            "action_id": self.symbol.action_id,
            "tactic": self.rendered_tactic,
            "target_selector": self.symbol.target_selector.value,
            "max_heartbeats": 20_000,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": BOUND_ACTION_SCHEMA,
            "symbol": self.symbol.to_dict(),
            "canonical_target_ordinal": self.canonical_target_ordinal,
            "target_normalized_type_hash": self.target_normalized_type_hash,
            "runtime_target_mvar_id": self.runtime_target_mvar_id,
            "premises": [row.to_dict() for row in self.premises],
            "rendered_tactic": self.rendered_tactic,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BoundAction":
        obj = _obj(value, "BoundAction")
        _exact_fields(
            obj,
            {
                "schema_version",
                "symbol",
                "canonical_target_ordinal",
                "target_normalized_type_hash",
                "runtime_target_mvar_id",
                "premises",
                "rendered_tactic",
            },
            "BoundAction",
        )
        if obj["schema_version"] != BOUND_ACTION_SCHEMA:
            raise StrictContractError("wrong BoundAction schema")
        return cls(
            symbol=ActionSymbol.from_dict(_obj(obj["symbol"], "BoundAction.symbol")),
            canonical_target_ordinal=_int(
                obj["canonical_target_ordinal"], "canonical_target_ordinal"
            ),
            target_normalized_type_hash=_digest(
                obj["target_normalized_type_hash"], "target_normalized_type_hash"
            ),  # type: ignore[arg-type]
            runtime_target_mvar_id=_str(
                obj["runtime_target_mvar_id"], "runtime_target_mvar_id"
            ),  # type: ignore[arg-type]
            premises=tuple(
                PremiseBinding.from_dict(_obj(row, "premise"))
                for row in _list(obj["premises"], "premises")
            ),
            rendered_tactic=(
                obj["rendered_tactic"]
                if type(obj["rendered_tactic"]) is str
                else (_raise("rendered_tactic must be a string"))
            ),
        )


def _validate_bound_action_against_state(
    bound_action: BoundAction, source_state: StateIdentityKey
) -> None:
    """Re-admit a public ``BoundAction`` against its full source identity.

    ``BoundAction`` remains a public transport type, so callers can construct
    one without using ``bind_to_state``.  Exact transition admission must not
    trust that route: all semantic ordinals, normalized hashes, contexts, and
    frozen patterns are recomputed here from ``source_state``.
    """

    if source_state.status != "open":
        raise StrictContractError("bound action source must be an open state")
    goals = _state_rows(source_state, "goals")
    if not goals:
        raise StrictContractError("bound action source has no open goals")
    expected_target = (
        0
        if bound_action.symbol.target_selector is TargetSelector.FIRST
        else len(goals) - 1
    )
    if bound_action.canonical_target_ordinal != expected_target:
        raise StrictContractError(
            "bound target ordinal does not implement the symbolic selector"
        )
    target_goal = goals[expected_target]
    target_expr = _str(target_goal.get("target_expr"), "source goal target_expr")
    expected_target_hash = _expression_digest(
        source_state, target_expr  # type: ignore[arg-type]
    )
    if bound_action.target_normalized_type_hash != expected_target_hash:
        raise StrictContractError("bound target hash differs from source goal target")

    contexts = {
        _str(row.get("id"), "local context.id"): row
        for row in _state_rows(source_state, "local_contexts")
    }
    context_id = _str(target_goal.get("local_context"), "source goal local_context")
    context = contexts.get(context_id)
    if context is None:
        raise StrictContractError("source goal local context is absent")
    declarations_raw = context.get("declarations")
    if type(declarations_raw) is not list or not all(
        type(item) is str and item for item in declarations_raw
    ):
        raise StrictContractError("source local-context declarations are malformed")
    declarations = tuple(declarations_raw)
    declaration_rows = {
        _str(row.get("id"), "local declaration.id"): row
        for row in _state_rows(source_state, "local_declarations")
    }
    expressions = _state_expression_map(source_state)

    symbol = bound_action.symbol
    if symbol.opcode == "exact_local":
        ordinal = symbol.premise_selector_ordinal
        if ordinal is None or ordinal >= len(declarations):
            raise StrictContractError("bound premise ordinal is outside source context")
        if len(bound_action.premises) != 1:
            raise StrictContractError("exact_local requires one admitted premise")
        premise = bound_action.premises[0]
        if premise.canonical_ordinal != ordinal:
            raise StrictContractError("bound premise ordinal differs from symbol")
        declaration = declaration_rows.get(declarations[ordinal])
        if declaration is None:
            raise StrictContractError("bound premise declaration is absent from source")
        type_expr = _str(
            declaration.get("type_expr"), "source premise declaration type_expr"
        )
        expected_premise_hash = _expression_digest(
            source_state, type_expr  # type: ignore[arg-type]
        )
        if premise.normalized_type_hash != expected_premise_hash:
            raise StrictContractError(
                "bound premise hash differs from source declaration type"
            )
        pattern = symbol.expected_normalized_type_pattern
        if pattern is None or not _matches_frozen_type_pattern(
            pattern=pattern,
            expression_id=type_expr,  # type: ignore[arg-type]
            expressions=expressions,
            local_declarations=declarations,
        ):
            raise StrictContractError(
                "bound premise does not satisfy frozen normalized-type pattern"
            )
    elif symbol.opcode == "exact_const":
        pattern = symbol.expected_normalized_type_pattern
        if pattern is None or not _matches_frozen_type_pattern(
            pattern=pattern,
            expression_id=target_expr,  # type: ignore[arg-type]
            expressions=expressions,
            local_declarations=declarations,
        ):
            raise StrictContractError(
                "bound exact_const target does not satisfy frozen type pattern"
            )
    elif bound_action.premises:
        raise StrictContractError("premise-free opcode carries a bound premise")


def _raise(message: str) -> Any:
    raise StrictContractError(message)


@dataclass(frozen=True)
class CapSemantics:
    requested_max_heartbeats_option: int
    effective_max_heartbeats_option: int
    effective_max_heartbeats_counter: int
    unlimited: bool
    source: str
    cache_policy: str
    cache_lookup_performed: bool
    consumption_reported: bool
    episode_budget: str

    def __post_init__(self) -> None:
        requested = _int(
            self.requested_max_heartbeats_option,
            "requested_max_heartbeats_option",
            minimum=1,
        )
        effective_option = _int(
            self.effective_max_heartbeats_option,
            "effective_max_heartbeats_option",
            minimum=1,
        )
        effective_counter = _int(
            self.effective_max_heartbeats_counter,
            "effective_max_heartbeats_counter",
            minimum=1,
        )
        if not isinstance(self.unlimited, bool):
            raise StrictContractError("unlimited must be boolean")
        if self.unlimited:
            raise StrictContractError("U05 action caps cannot be unlimited")
        if requested != effective_option or effective_counter != effective_option * 1000:
            raise StrictContractError(
                "requested/effective heartbeat option or Core counter-unit mismatch"
            )
        if requested != 20_000 or effective_counter != 20_000_000:
            raise StrictContractError("U05 requires the frozen 20000-heartbeat cap")
        if self.source != "explicit_action":
            raise StrictContractError("U05 cap source must be explicit_action")
        if self.cache_policy != "bypass" or self.cache_lookup_performed:
            raise StrictContractError("U05 must bypass every result/audit cache")
        if not isinstance(self.consumption_reported, bool):
            raise StrictContractError("consumption_reported must be boolean")
        if self.episode_budget != EPISODE_BUDGET_SENTINEL:
            raise StrictContractError("wrong U05 episode-budget sentinel")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CAP_SEMANTICS_SCHEMA,
            "requested_max_heartbeats_option": self.requested_max_heartbeats_option,
            "effective_max_heartbeats_option": self.effective_max_heartbeats_option,
            "effective_max_heartbeats_counter": self.effective_max_heartbeats_counter,
            "unlimited": self.unlimited,
            "source": self.source,
            "cache_policy": self.cache_policy,
            "cache_lookup_performed": self.cache_lookup_performed,
            "consumption_reported": self.consumption_reported,
            "episode_budget": self.episode_budget,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, native: bool = False) -> "CapSemantics":
        obj = _obj(value, "CapSemantics")
        expected = {
            "requested_max_heartbeats_option",
            "effective_max_heartbeats_option",
            "effective_max_heartbeats_counter",
            "unlimited",
            "source",
            "cache_policy",
            "cache_lookup_performed",
            "consumption_reported",
            "episode_budget",
        }
        if not native:
            expected = expected | {"schema_version"}
        _exact_fields(obj, expected, "CapSemantics")
        if not native and obj["schema_version"] != CAP_SEMANTICS_SCHEMA:
            raise StrictContractError("wrong CapSemantics schema")
        return cls(
            requested_max_heartbeats_option=_int(
                obj["requested_max_heartbeats_option"],
                "requested_max_heartbeats_option",
                minimum=1,
            ),
            effective_max_heartbeats_option=_int(
                obj["effective_max_heartbeats_option"],
                "effective_max_heartbeats_option",
                minimum=1,
            ),
            effective_max_heartbeats_counter=_int(
                obj["effective_max_heartbeats_counter"],
                "effective_max_heartbeats_counter",
                minimum=1,
            ),
            unlimited=_bool(obj["unlimited"], "unlimited"),
            source=_str(obj["source"], "source"),  # type: ignore[arg-type]
            cache_policy=_str(obj["cache_policy"], "cache_policy"),  # type: ignore[arg-type]
            cache_lookup_performed=_bool(
                obj["cache_lookup_performed"], "cache_lookup_performed"
            ),
            consumption_reported=_bool(
                obj["consumption_reported"], "consumption_reported"
            ),
            episode_budget=_str(obj["episode_budget"], "episode_budget"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class CanonicalStateDelta:
    before_goals: tuple[str, ...]
    after_goals: tuple[str, ...]
    before_mvars: tuple[str, ...]
    after_mvars: tuple[str, ...]
    before_assigned_mvars: tuple[str, ...]
    after_assigned_mvars: tuple[str, ...]
    closed_goals: tuple[str, ...]
    new_goals: tuple[str, ...]
    assigned_mvars: tuple[str, ...]
    new_mvars: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "before_goals",
            "after_goals",
            "before_mvars",
            "after_mvars",
            "before_assigned_mvars",
            "after_assigned_mvars",
            "closed_goals",
            "new_goals",
            "assigned_mvars",
            "new_mvars",
        ):
            value = getattr(self, field_name)
            if type(value) is not tuple or not all(type(item) is str and item for item in value):
                raise StrictContractError(f"{field_name} must be a tuple of labels")
            if len(value) != len(set(value)):
                raise StrictContractError(f"{field_name} contains duplicate labels")
        if set(self.closed_goals) != set(self.before_goals) - set(self.after_goals):
            raise StrictContractError("closed_goals is not the exact before/after difference")
        if set(self.new_goals) != set(self.after_goals) - set(self.before_goals):
            raise StrictContractError("new_goals is not the exact before/after difference")
        if set(self.new_mvars) != set(self.after_mvars) - set(self.before_mvars):
            raise StrictContractError("new_mvars is not the exact before/after difference")
        if set(self.assigned_mvars) != (
            set(self.after_assigned_mvars) - set(self.before_assigned_mvars)
        ):
            raise StrictContractError(
                "assigned_mvars is cumulative rather than the exact before/after difference"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_DELTA_SCHEMA,
            **{
                field_name: list(getattr(self, field_name))
                for field_name in (
                    "before_goals",
                    "after_goals",
                    "before_mvars",
                    "after_mvars",
                    "before_assigned_mvars",
                    "after_assigned_mvars",
                    "closed_goals",
                    "new_goals",
                    "assigned_mvars",
                    "new_mvars",
                )
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalStateDelta":
        obj = _obj(value, "CanonicalStateDelta")
        names = {
            "before_goals",
            "after_goals",
            "before_mvars",
            "after_mvars",
            "before_assigned_mvars",
            "after_assigned_mvars",
            "closed_goals",
            "new_goals",
            "assigned_mvars",
            "new_mvars",
        }
        _exact_fields(obj, names | {"schema_version"}, "CanonicalStateDelta")
        if obj["schema_version"] != STATE_DELTA_SCHEMA:
            raise StrictContractError("wrong CanonicalStateDelta schema")
        return cls(**{name: _unique_strings(obj[name], name) for name in names})


@dataclass(frozen=True)
class DebtReadout:
    open_goal_count: int
    open_unassigned_mvar_count: int
    pending_typeclass_count: int
    carrier_atom_count: int
    expression_node_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "open_goal_count",
            "open_unassigned_mvar_count",
            "pending_typeclass_count",
            "carrier_atom_count",
            "expression_node_count",
        ):
            _int(getattr(self, field_name), f"DebtReadout.{field_name}")

    @classmethod
    def from_identity(cls, key: StateIdentityKey) -> "DebtReadout":
        return cls(*debt_readout_from_identity(key))

    def to_tuple(self) -> tuple[int, int, int, int, int]:
        return (
            self.open_goal_count,
            self.open_unassigned_mvar_count,
            self.pending_typeclass_count,
            self.carrier_atom_count,
            self.expression_node_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DEBT_READOUT_SCHEMA,
            "open_goal_count": self.open_goal_count,
            "open_unassigned_mvar_count": self.open_unassigned_mvar_count,
            "pending_typeclass_count": self.pending_typeclass_count,
            "carrier_atom_count": self.carrier_atom_count,
            "expression_node_count": self.expression_node_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DebtReadout":
        obj = _obj(value, "DebtReadout")
        names = {
            "open_goal_count",
            "open_unassigned_mvar_count",
            "pending_typeclass_count",
            "carrier_atom_count",
            "expression_node_count",
        }
        _exact_fields(obj, names | {"schema_version"}, "DebtReadout")
        if obj["schema_version"] != DEBT_READOUT_SCHEMA:
            raise StrictContractError("wrong DebtReadout schema")
        return cls(**{name: _int(obj[name], name) for name in names})


@dataclass(frozen=True)
class ReplayComparableResponse:
    raw_status: RawTransitionStatus
    totalized_status: TotalizedStatus
    after_state: StateIdentityKey | None
    delta: CanonicalStateDelta
    action_symbol: ActionSymbol
    canonical_binding: Mapping[str, Any]
    ordinary_failure_class: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.raw_status, RawTransitionStatus):
            object.__setattr__(
                self, "raw_status", _enum(RawTransitionStatus, self.raw_status, "raw_status")
            )
        if not isinstance(self.totalized_status, TotalizedStatus):
            object.__setattr__(
                self,
                "totalized_status",
                _enum(TotalizedStatus, self.totalized_status, "totalized_status"),
            )
        binding = _obj(self.canonical_binding, "canonical_binding")
        _exact_fields(
            binding,
            {"canonical_target_ordinal", "target_normalized_type_hash", "premises"},
            "canonical_binding",
        )
        _int(binding["canonical_target_ordinal"], "canonical_target_ordinal")
        _digest(binding["target_normalized_type_hash"], "target_normalized_type_hash")
        for row in _list(binding["premises"], "canonical_binding.premises"):
            premise = _obj(row, "canonical premise binding")
            _exact_fields(
                premise,
                {"premise_slot_rule_id", "canonical_ordinal", "normalized_type_hash"},
                "canonical premise binding",
            )
            _str(premise["premise_slot_rule_id"], "premise_slot_rule_id")
            _int(premise["canonical_ordinal"], "canonical_ordinal")
            _digest(premise["normalized_type_hash"], "normalized_type_hash")
        canonical_json_bytes(binding)
        object.__setattr__(self, "canonical_binding", binding)
        _str(self.ordinary_failure_class, "ordinary_failure_class", optional=True)
        expected_total = {
            RawTransitionStatus.OPEN: TotalizedStatus.OPEN,
            RawTransitionStatus.CLOSED: TotalizedStatus.CLOSED,
            RawTransitionStatus.ORDINARY_FAILURE: TotalizedStatus.SINK,
        }[self.raw_status]
        if self.totalized_status is not expected_total:
            raise StrictContractError("raw and totalized status are inconsistent")
        if self.raw_status is RawTransitionStatus.ORDINARY_FAILURE:
            if self.after_state is not None or self.ordinary_failure_class is None:
                raise StrictContractError("ordinary failure requires class and no child state")
        elif self.after_state is None or self.ordinary_failure_class is not None:
            raise StrictContractError("open/closed response requires child state and no failure class")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REPLAY_COMPARABLE_SCHEMA,
            "raw_status": self.raw_status.value,
            "totalized_status": self.totalized_status.value,
            "after_state": None if self.after_state is None else self.after_state.to_dict(),
            "delta": self.delta.to_dict(),
            "action_symbol": self.action_symbol.to_dict(),
            "canonical_binding": dict(self.canonical_binding),
            "ordinary_failure_class": self.ordinary_failure_class,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReplayComparableResponse":
        obj = _obj(value, "ReplayComparableResponse")
        fields = {
            "schema_version",
            "raw_status",
            "totalized_status",
            "after_state",
            "delta",
            "action_symbol",
            "canonical_binding",
            "ordinary_failure_class",
        }
        _exact_fields(obj, fields, "ReplayComparableResponse")
        if obj["schema_version"] != REPLAY_COMPARABLE_SCHEMA:
            raise StrictContractError("wrong ReplayComparableResponse schema")
        try:
            after = (
                None
                if obj["after_state"] is None
                else StateIdentityKey.from_dict(_obj(obj["after_state"], "after_state"))
            )
        except StrictIdentityError as exc:
            raise StrictContractError("invalid after-state identity") from exc
        return cls(
            raw_status=_enum(RawTransitionStatus, obj["raw_status"], "raw_status"),
            totalized_status=_enum(
                TotalizedStatus, obj["totalized_status"], "totalized_status"
            ),
            after_state=after,
            delta=CanonicalStateDelta.from_dict(_obj(obj["delta"], "delta")),
            action_symbol=ActionSymbol.from_dict(
                _obj(obj["action_symbol"], "action_symbol")
            ),
            canonical_binding=_obj(obj["canonical_binding"], "canonical_binding"),
            ordinary_failure_class=_str(
                obj["ordinary_failure_class"], "ordinary_failure_class", optional=True
            ),
        )


@dataclass(frozen=True)
class ReplayVerification:
    replay_status: ReplayStatus
    reexecution_performed: bool
    verification_method: str
    semantic_response_match: bool
    post_state_match: bool
    delta_match: bool
    target_match: bool
    cap_match: bool
    error: str | None
    primary: ReplayComparableResponse
    replay: ReplayComparableResponse

    def __post_init__(self) -> None:
        if not isinstance(self.replay_status, ReplayStatus):
            object.__setattr__(
                self,
                "replay_status",
                _enum(ReplayStatus, self.replay_status, "replay_status"),
            )
        _str(self.verification_method, "verification_method")
        _str(self.error, "replay.error", optional=True)
        flags = (
            self.reexecution_performed,
            self.semantic_response_match,
            self.post_state_match,
            self.delta_match,
            self.target_match,
            self.cap_match,
        )
        if not all(type(flag) is bool for flag in flags):
            raise StrictContractError("replay verification flags must be booleans")
        if self.replay_status is ReplayStatus.VERIFIED:
            if not all(flags) or self.error is not None or self.primary != self.replay:
                raise StrictContractError("verified replay must be a second exact match")
        elif self.error is None and all(flags) and self.primary == self.replay:
            raise StrictContractError("mismatch replay cannot carry a verified payload")

    @property
    def verified(self) -> bool:
        return self.replay_status is ReplayStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REPLAY_VERIFICATION_SCHEMA,
            "replay_status": self.replay_status.value,
            "reexecution_performed": self.reexecution_performed,
            "verification_method": self.verification_method,
            "semantic_response_match": self.semantic_response_match,
            "post_state_match": self.post_state_match,
            "delta_match": self.delta_match,
            "target_match": self.target_match,
            "cap_match": self.cap_match,
            "error": self.error,
            "primary_comparable": self.primary.to_dict(),
            "replay_comparable": self.replay.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReplayVerification":
        obj = _obj(value, "ReplayVerification")
        fields = {
            "schema_version",
            "replay_status",
            "reexecution_performed",
            "verification_method",
            "semantic_response_match",
            "post_state_match",
            "delta_match",
            "target_match",
            "cap_match",
            "error",
            "primary_comparable",
            "replay_comparable",
        }
        _exact_fields(obj, fields, "ReplayVerification")
        if obj["schema_version"] != REPLAY_VERIFICATION_SCHEMA:
            raise StrictContractError("wrong ReplayVerification schema")
        return cls(
            replay_status=_enum(ReplayStatus, obj["replay_status"], "replay_status"),
            reexecution_performed=_bool(
                obj["reexecution_performed"], "reexecution_performed"
            ),
            verification_method=_str(
                obj["verification_method"], "verification_method"
            ),  # type: ignore[arg-type]
            semantic_response_match=_bool(
                obj["semantic_response_match"], "semantic_response_match"
            ),
            post_state_match=_bool(obj["post_state_match"], "post_state_match"),
            delta_match=_bool(obj["delta_match"], "delta_match"),
            target_match=_bool(obj["target_match"], "target_match"),
            cap_match=_bool(obj["cap_match"], "cap_match"),
            error=_str(obj["error"], "error", optional=True),
            primary=ReplayComparableResponse.from_dict(
                _obj(obj["primary_comparable"], "primary_comparable")
            ),
            replay=ReplayComparableResponse.from_dict(
                _obj(obj["replay_comparable"], "replay_comparable")
            ),
        )


@dataclass(frozen=True)
class FieldCoverage:
    field_name: str
    status: FieldCoverageStatus
    source: str
    reason: str | None = None

    def __post_init__(self) -> None:
        _str(self.field_name, "FieldCoverage.field_name")
        _str(self.source, "FieldCoverage.source")
        _str(self.reason, "FieldCoverage.reason", optional=True)
        if not isinstance(self.status, FieldCoverageStatus):
            object.__setattr__(
                self,
                "status",
                _enum(FieldCoverageStatus, self.status, "coverage status"),
            )
        if self.status is FieldCoverageStatus.COMPLETE and self.reason is not None:
            raise StrictContractError("complete coverage cannot carry a failure reason")
        if self.status in {
            FieldCoverageStatus.INCOMPLETE,
            FieldCoverageStatus.TRUNCATED,
        } and self.reason is None:
            raise StrictContractError("incomplete/truncated coverage requires a reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FIELD_COVERAGE_SCHEMA,
            "field_name": self.field_name,
            "status": self.status.value,
            "source": self.source,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FieldCoverage":
        obj = _obj(value, "FieldCoverage")
        _exact_fields(
            obj,
            {"schema_version", "field_name", "status", "source", "reason"},
            "FieldCoverage",
        )
        if obj["schema_version"] != FIELD_COVERAGE_SCHEMA:
            raise StrictContractError("wrong FieldCoverage schema")
        return cls(
            field_name=_str(obj["field_name"], "field_name"),  # type: ignore[arg-type]
            status=_enum(FieldCoverageStatus, obj["status"], "coverage status"),
            source=_str(obj["source"], "source"),  # type: ignore[arg-type]
            reason=_str(obj["reason"], "reason", optional=True),
        )


@dataclass(frozen=True)
class Censor:
    kind: CensorKind
    stage: str
    message: str
    required_field: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CensorKind):
            object.__setattr__(self, "kind", _enum(CensorKind, self.kind, "censor kind"))
        _str(self.stage, "Censor.stage")
        _str(self.message, "Censor.message")
        _str(self.required_field, "Censor.required_field", optional=True)
        if self.kind is CensorKind.REQUIRED_FIELD_TRUNCATED and self.required_field is None:
            raise StrictContractError("truncation censor requires required_field")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CENSOR_SCHEMA,
            "kind": self.kind.value,
            "stage": self.stage,
            "message": self.message,
            "required_field": self.required_field,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Censor":
        obj = _obj(value, "Censor")
        _exact_fields(
            obj,
            {"schema_version", "kind", "stage", "message", "required_field"},
            "Censor",
        )
        if obj["schema_version"] != CENSOR_SCHEMA:
            raise StrictContractError("wrong Censor schema")
        return cls(
            kind=_enum(CensorKind, obj["kind"], "censor kind"),
            stage=_str(obj["stage"], "stage"),  # type: ignore[arg-type]
            message=_str(obj["message"], "message"),  # type: ignore[arg-type]
            required_field=_str(
                obj["required_field"], "required_field", optional=True
            ),
        )


_REQUIRED_CORE_COVERAGE = {
    "state_identity",
    "target_binding",
    "transition_delta",
    "replay",
    "cap_semantics",
    "debt_readout",
}


@dataclass(frozen=True)
class ExactKernelTransitionCore:
    source_state: StateIdentityKey
    target_state: StateIdentityKey | None
    bound_action: BoundAction
    cap_semantics: CapSemantics
    raw_status: RawTransitionStatus
    totalized_status: TotalizedStatus
    delta: CanonicalStateDelta
    debt_before: DebtReadout
    debt_after: DebtReadout | None
    replay: ReplayVerification
    field_coverage: tuple[FieldCoverage, ...]
    u05_semantics_version: str = U05_SEMANTICS_VERSION

    def __post_init__(self) -> None:
        if self.u05_semantics_version != U05_SEMANTICS_VERSION:
            raise StrictContractError("wrong U05 semantics version")
        if not isinstance(self.source_state, StateIdentityKey):
            raise StrictContractError("source_state must be a full StateIdentityKey")
        if not isinstance(self.bound_action, BoundAction):
            raise StrictContractError("bound_action must be a strict BoundAction")
        _validate_bound_action_against_state(self.bound_action, self.source_state)
        if not isinstance(self.raw_status, RawTransitionStatus):
            object.__setattr__(
                self, "raw_status", _enum(RawTransitionStatus, self.raw_status, "raw_status")
            )
        if not isinstance(self.totalized_status, TotalizedStatus):
            object.__setattr__(
                self,
                "totalized_status",
                _enum(TotalizedStatus, self.totalized_status, "totalized_status"),
            )
        expected_total = {
            RawTransitionStatus.OPEN: TotalizedStatus.OPEN,
            RawTransitionStatus.CLOSED: TotalizedStatus.CLOSED,
            RawTransitionStatus.ORDINARY_FAILURE: TotalizedStatus.SINK,
        }[self.raw_status]
        if self.totalized_status is not expected_total:
            raise StrictContractError("transition raw/totalized status mismatch")
        if self.raw_status is RawTransitionStatus.ORDINARY_FAILURE:
            if self.target_state is not None or self.debt_after is not None:
                raise StrictContractError("ordinary failure totalizes to sink without child state")
        elif self.target_state is None or self.debt_after is None:
            raise StrictContractError("open/closed transition requires an exact child state")
        if self.debt_before != DebtReadout.from_identity(self.source_state):
            raise StrictContractError("debt_before is not derived from source identity")
        if self.target_state is not None and self.debt_after != DebtReadout.from_identity(
            self.target_state
        ):
            raise StrictContractError("debt_after is not derived from target identity")
        if not self.replay.verified:
            raise StrictContractError("ExactKernelTransitionCore requires verified replay")
        primary = self.replay.primary
        if (
            primary.raw_status is not self.raw_status
            or primary.totalized_status is not self.totalized_status
            or primary.after_state != self.target_state
            or primary.delta != self.delta
            or primary.action_symbol != self.bound_action.symbol
            or primary.canonical_binding != self.bound_action.semantic_binding_dict()
        ):
            raise StrictContractError("transition core differs from replay-comparable response")
        if type(self.field_coverage) is not tuple or not all(
            isinstance(row, FieldCoverage) for row in self.field_coverage
        ):
            raise StrictContractError("field_coverage must be a FieldCoverage tuple")
        coverage = {row.field_name: row for row in self.field_coverage}
        if len(coverage) != len(self.field_coverage):
            raise StrictContractError("duplicate field-coverage records")
        missing = _REQUIRED_CORE_COVERAGE - set(coverage)
        if missing:
            raise StrictContractError(f"missing core field coverage: {sorted(missing)}")
        if any(
            coverage[name].status is not FieldCoverageStatus.COMPLETE
            for name in _REQUIRED_CORE_COVERAGE
        ):
            raise StrictContractError("incomplete required field cannot enter exact core")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_KERNEL_TRANSITION_CORE_SCHEMA,
            "u05_semantics_version": self.u05_semantics_version,
            "source_state": self.source_state.to_dict(),
            "target_state": None if self.target_state is None else self.target_state.to_dict(),
            "bound_action": self.bound_action.to_dict(),
            "cap_semantics": self.cap_semantics.to_dict(),
            "raw_status": self.raw_status.value,
            "totalized_status": self.totalized_status.value,
            "delta": self.delta.to_dict(),
            "debt_before": self.debt_before.to_dict(),
            "debt_after": None if self.debt_after is None else self.debt_after.to_dict(),
            "replay": self.replay.to_dict(),
            "field_coverage": [row.to_dict() for row in self.field_coverage],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactKernelTransitionCore":
        obj = _obj(value, "ExactKernelTransitionCore")
        fields = {
            "schema_version",
            "u05_semantics_version",
            "source_state",
            "target_state",
            "bound_action",
            "cap_semantics",
            "raw_status",
            "totalized_status",
            "delta",
            "debt_before",
            "debt_after",
            "replay",
            "field_coverage",
        }
        _exact_fields(obj, fields, "ExactKernelTransitionCore")
        if obj["schema_version"] != EXACT_KERNEL_TRANSITION_CORE_SCHEMA:
            raise StrictContractError("wrong ExactKernelTransitionCore schema")
        try:
            source = StateIdentityKey.from_dict(_obj(obj["source_state"], "source_state"))
            target = (
                None
                if obj["target_state"] is None
                else StateIdentityKey.from_dict(_obj(obj["target_state"], "target_state"))
            )
        except StrictIdentityError as exc:
            raise StrictContractError("invalid transition state identity") from exc
        return cls(
            source_state=source,
            target_state=target,
            bound_action=BoundAction.from_dict(_obj(obj["bound_action"], "bound_action")),
            cap_semantics=CapSemantics.from_dict(
                _obj(obj["cap_semantics"], "cap_semantics")
            ),
            raw_status=_enum(RawTransitionStatus, obj["raw_status"], "raw_status"),
            totalized_status=_enum(
                TotalizedStatus, obj["totalized_status"], "totalized_status"
            ),
            delta=CanonicalStateDelta.from_dict(_obj(obj["delta"], "delta")),
            debt_before=DebtReadout.from_dict(
                _obj(obj["debt_before"], "debt_before")
            ),
            debt_after=(
                None
                if obj["debt_after"] is None
                else DebtReadout.from_dict(_obj(obj["debt_after"], "debt_after"))
            ),
            replay=ReplayVerification.from_dict(_obj(obj["replay"], "replay")),
            field_coverage=tuple(
                FieldCoverage.from_dict(_obj(row, "field coverage"))
                for row in _list(obj["field_coverage"], "field_coverage")
            ),
            u05_semantics_version=_str(
                obj["u05_semantics_version"], "u05_semantics_version"
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class U05ProbeTransition:
    core: ExactKernelTransitionCore
    locality_coverage: tuple[FieldCoverage, ...] = ()
    m3_read_set_complete: bool = field(default=False, init=False)
    promotable_to_exact_oracle: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.locality_coverage) is not tuple or not all(
            isinstance(row, FieldCoverage) for row in self.locality_coverage
        ):
            raise StrictContractError("locality_coverage must be a FieldCoverage tuple")
        for row in self.locality_coverage:
            if row.field_name == "m3_read_set" and row.status is FieldCoverageStatus.COMPLETE:
                raise StrictContractError("U05 cannot claim complete M3 read-set coverage")

    def to_dict(self) -> dict[str, Any]:
        # This is a U05-only transport form, never an ExactOracleTransition or a
        # hard-tier locality serializer.
        return {
            "schema_version": U05_PROBE_TRANSITION_SCHEMA,
            "core": self.core.to_dict(),
            "locality_coverage": [row.to_dict() for row in self.locality_coverage],
            "m3_read_set_complete": False,
            "promotable_to_exact_oracle": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "U05ProbeTransition":
        obj = _obj(value, "U05ProbeTransition")
        _exact_fields(
            obj,
            {
                "schema_version",
                "core",
                "locality_coverage",
                "m3_read_set_complete",
                "promotable_to_exact_oracle",
            },
            "U05ProbeTransition",
        )
        if obj["schema_version"] != U05_PROBE_TRANSITION_SCHEMA:
            raise StrictContractError("wrong U05ProbeTransition schema")
        if obj["m3_read_set_complete"] is not False:
            raise StrictContractError("U05 m3_read_set_complete must be false")
        if obj["promotable_to_exact_oracle"] is not False:
            raise StrictContractError("U05 transition is nonpromotable")
        return cls(
            core=ExactKernelTransitionCore.from_dict(_obj(obj["core"], "core")),
            locality_coverage=tuple(
                FieldCoverage.from_dict(_obj(row, "locality coverage"))
                for row in _list(obj["locality_coverage"], "locality_coverage")
            ),
        )


def canonical_contract_bytes(value: Any) -> bytes:
    """Serialize a strict contract or a plain strict-JSON value canonically."""

    if hasattr(value, "to_dict"):
        value = value.to_dict()
    try:
        return canonical_json_bytes(value)
    except StrictIdentityError as exc:
        raise StrictContractError("contract is outside canonical JSON") from exc


__all__ = [
    "ACTION_SYMBOL_SCHEMA",
    "BOUND_ACTION_SCHEMA",
    "CAP_SEMANTICS_SCHEMA",
    "CENSOR_SCHEMA",
    "DEBT_READOUT_SCHEMA",
    "EPISODE_BUDGET_SENTINEL",
    "EXACT_KERNEL_TRANSITION_CORE_SCHEMA",
    "FIELD_COVERAGE_SCHEMA",
    "OBSERVATION_FRAME_SCHEMA",
    "REPLAY_COMPARABLE_SCHEMA",
    "REPLAY_VERIFICATION_SCHEMA",
    "STATE_DELTA_SCHEMA",
    "TRANSITION_SEMANTICS_SCHEMA",
    "U05_PROBE_TRANSITION_SCHEMA",
    "U05_SEMANTICS_VERSION",
    "U05_TASK_SCHEMA",
    "ActionSymbol",
    "BehavioralObservationKey",
    "BoundAction",
    "CanonicalStateDelta",
    "CapSemantics",
    "Censor",
    "CensorKind",
    "DebtReadout",
    "ExactKernelTransitionCore",
    "FieldCoverage",
    "FieldCoverageStatus",
    "ObservationFrameId",
    "PremiseBinding",
    "RawTransitionStatus",
    "ReplayComparableResponse",
    "ReplayStatus",
    "ReplayVerification",
    "StrictContractError",
    "TargetSelector",
    "TotalizedStatus",
    "TransitionSemanticsId",
    "U05ProbeTransition",
    "U05TaskSpec",
    "WorkPackageStatus",
    "canonical_contract_bytes",
]
