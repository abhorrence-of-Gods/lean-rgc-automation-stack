"""Bounded public-synthetic locality CEGAR for U'1.5-L0.

The exact objects consumed here have already passed the independent finite
snapshot and partition verifiers.  This module never constructs or promotes
that capability: it only binds verified terminal observations to a nominal,
monotone region partition and an exact-rational ranking objective.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import json
from types import MappingProxyType
from typing import Any

from .adapters import make_synthetic_transition_semantics_id
from .behavioral_partition import VerifiedExactPartition
from .certificates import PipelineEvidenceTier
from .contracts import (
    ActionSymbol,
    BehavioralObservationKey,
    CanonicalPayload,
    ExactRational,
    ObservationFrameId,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTransitionSemanticsId,
    TotalizedStatus,
    canonical_contract_bytes,
)


_REGION_SCHEMA = "lean-rgc-uprime-u15-l0-before-region-v1"
_FEATURE_SCHEMA = "lean-rgc-uprime-u15-l0-locality-feature-v1"
_QUERY_SCHEMA = "lean-rgc-uprime-u15-l0-query-v1"
_OBSERVATION_SCHEMA = "lean-rgc-uprime-u15-l0-exact-local-observation-v1"
_COUNTEREXAMPLE_SCHEMA = "lean-rgc-uprime-u15-l0-exact-local-counterexample-v1"
_PARTITION_SCHEMA = "lean-rgc-uprime-u15-l0-nominal-partition-v1"
_SCORE_SCHEMA = "lean-rgc-uprime-u15-l0-query-score-v1"
_REPORT_SCHEMA = "lean-rgc-uprime-u15-l0-cegar-report-v1"
_CANDIDATE_SCHEMA = "lean-rgc-uprime-u15-l0-candidate-v1"
_CONSTRUCTION_TOKEN = object()

_MAX_REGIONS = 16
_MAX_NODES = 12
_MAX_EDGES = 24
_MAX_QUERIES = 16
_MAX_ACTION_DEPTH = 3
_MAX_RESPONSE_CELLS = 256
_GLOBAL_DIMENSION = 16
_MAX_IDENTIFIER_BYTES = 128
_MAX_INPUT_BITS = 256
_MAX_INTERMEDIATE_BITS = 4096
_MAX_WIRE_BYTES = 1 << 20
_MAX_JSON_DEPTH = 16
_MAX_JSON_ARRAY = 256
_MAX_JSON_KEYS = 64
_MAX_TREEWIDTH = 8
_BUDGET = 16
_L0_ADMISSION_PREFIX = "unit_cpu_survivor_u15_l0_"


def _fail(message: str) -> None:
    raise StrictContractError(message)


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be a nonempty exact string")
    try:
        size = len(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{label} is not strict UTF-8") from exc
    if size > _MAX_IDENTIFIER_BYTES:
        _fail(f"{label} exceeds the 128-byte identifier cap")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} is not an exact bounded integer")
    return value


def _digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        _fail(f"{label} is not an uppercase SHA-256 digest")
    return value


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _bounded_tuple(
    values: Sequence[Any], *, maximum: int, label: str, minimum: int = 0
) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        _fail(f"{label} must be a finite sequence, not scalar bytes")
    try:
        declared = len(values)
    except TypeError as exc:
        raise StrictContractError(f"{label} has no finite declared length") from exc
    if declared < minimum or declared > maximum:
        _fail(f"{label} violates its pre-materialization cap")
    result: list[Any] = []
    iterator = iter(values)
    for _ in range(declared):
        try:
            result.append(next(iterator))
        except StopIteration as exc:
            raise StrictContractError(f"{label} ended before its declared length") from exc
    try:
        next(iterator)
    except StopIteration:
        pass
    else:
        _fail(f"{label} exceeds its declared length")
    return tuple(result)


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} has missing, duplicate, or unknown fields")
    return value


def _json_preflight(value: Any, *, depth: int = 1) -> None:
    if depth > _MAX_JSON_DEPTH:
        _fail("strict JSON depth cap exceeded")
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        if len(value) > _MAX_JSON_ARRAY:
            _fail("strict JSON array cap exceeded")
        for item in value:
            _json_preflight(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > _MAX_JSON_KEYS:
            _fail("strict JSON object-key cap exceeded")
        for key, item in value.items():
            if type(key) is not str:
                _fail("strict JSON object key is not a string")
            _json_preflight(item, depth=depth + 1)
        return
    _fail("value is outside strict JSON")


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate JSON object key")
        result[key] = value
    return result


def _parse_wire(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_WIRE_BYTES:
        _fail("wire violates the byte cap")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictContractError("wire is not strict JSON") from exc
    _json_preflight(value)
    if type(value) is not dict or canonical_contract_bytes(value) != raw:
        _fail("wire is not a canonical JSON object")
    return value


def _exact_rational(value: Any, label: str, *, intermediate: bool = False) -> ExactRational:
    if type(value) is not ExactRational:
        _fail(f"{label} is not an ExactRational")
    limit = _MAX_INTERMEDIATE_BITS if intermediate else _MAX_INPUT_BITS
    if abs(value.numerator).bit_length() > limit or value.denominator.bit_length() > limit:
        _fail(f"{label} violates the L0 rational bit cap")
    return value


def _fraction(value: ExactRational, label: str, *, intermediate: bool = False) -> Fraction:
    checked = _exact_rational(value, label, intermediate=intermediate)
    return Fraction(checked.numerator, checked.denominator)


def _from_fraction(value: Fraction, label: str) -> ExactRational:
    if abs(value.numerator).bit_length() > _MAX_INTERMEDIATE_BITS or value.denominator.bit_length() > _MAX_INTERMEDIATE_BITS:
        _fail(f"{label} violates the intermediate rational bit cap")
    return ExactRational(value.numerator, value.denominator)


def _action_symbol(action: SyntheticAction) -> ActionSymbol:
    if type(action) is not SyntheticAction:
        _fail("action catalogue contains a non-SyntheticAction")
    try:
        payload = json.loads(action.payload.canonical_json)
    except json.JSONDecodeError as exc:
        raise StrictContractError("action payload is not JSON") from exc
    if type(payload) is not dict:
        _fail("action payload does not contain a complete ActionSymbol object")
    symbol = ActionSymbol.from_dict(payload)
    if symbol.action_id != action.action_id:
        _fail("outer and inner action IDs disagree")
    if not action.action_id.startswith(_L0_ADMISSION_PREFIX):
        _fail("action ID is outside the frozen L0 admission prefix")
    return symbol


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    if left == right:
        _fail("region pair must contain two distinct IDs")
    return tuple(sorted((left, right), key=lambda item: item.encode("utf-8")))  # type: ignore[return-value]


def _partition_digest(partition: "ProposedNominalPartition") -> str:
    return _sha(partition.to_dict())


def _candidate_value(
    family_id: str,
    instance_id: str,
    left_region_id: str,
    right_region_id: str,
    query: "LocalityQuery",
) -> dict[str, Any]:
    left, right = _canonical_pair(left_region_id, right_region_id)
    response_cells = 2 * len(query.response_keys)
    word_work = 2 * (len(query.action_word) + len(query.closing_action_word))
    full_query_row = {
        "query_id": query.query_id,
        "action_word": [symbol.action_id for symbol in query.action_word],
        "closing_context_id": query.closing_context_id,
        "derived_cost": {
            "response_cells": response_cells,
            "word_work": word_work,
            "total": response_cells + word_work,
        },
    }
    return {
        "schema_version": _CANDIDATE_SCHEMA,
        "family_id": family_id,
        "instance_id": instance_id,
        "left_region_id": left,
        "right_region_id": right,
        "full_query_row": full_query_row,
    }


def _candidate_json(value: dict[str, Any]) -> str:
    return canonical_contract_bytes(value).decode("utf-8")


def _block_owner(partition: "ProposedNominalPartition") -> dict[str, int]:
    return {
        member: index
        for index, block in enumerate(partition.blocks)
        for member in block
    }


def _canonical_blocks(blocks: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    normalized = [
        tuple(sorted(block, key=lambda item: item.encode("utf-8"))) for block in blocks
    ]
    return tuple(sorted(normalized, key=lambda block: canonical_contract_bytes(list(block))))


def _feature_key(feature: "LocalityFeatureVector") -> bytes:
    return canonical_contract_bytes(feature.to_dict())


@dataclass(frozen=True)
class BeforeLocalRegion:
    region_id: str
    observation_frame_id: ObservationFrameId
    transition_semantics_id: SyntheticTransitionSemanticsId
    nodes: tuple[tuple[str, str], ...]
    edges: tuple[tuple[str, str, str], ...]
    boundary_ports: tuple[tuple[str, str, str], ...]
    separator_node_ids: tuple[str, ...]
    target_node_id: str
    _gate_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._gate_token is not _CONSTRUCTION_TOKEN:
            _fail("BeforeLocalRegion must be built by make_before_local_region")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _REGION_SCHEMA,
            "region_id": self.region_id,
            "observation_frame_id": self.observation_frame_id.to_dict(),
            "transition_semantics_id": self.transition_semantics_id.to_dict(),
            "nodes": [{"node_id": a, "node_kind": b} for a, b in self.nodes],
            "edges": [
                {"source": a, "target": b, "edge_kind": c}
                for a, b, c in self.edges
            ],
            "boundary_ports": [
                {"port_id": a, "kind": b, "attached_node_id": c}
                for a, b, c in self.boundary_ports
            ],
            "separator_node_ids": list(self.separator_node_ids),
            "target_node_id": self.target_node_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BeforeLocalRegion":
        obj = _object(
            value,
            {
                "schema_version", "region_id", "observation_frame_id",
                "transition_semantics_id", "nodes", "edges", "boundary_ports",
                "separator_node_ids", "target_node_id",
            },
            "BeforeLocalRegion",
        )
        if obj["schema_version"] != _REGION_SCHEMA:
            _fail("wrong BeforeLocalRegion schema")
        return make_before_local_region(
            region_id=obj["region_id"],
            observation_frame_id=ObservationFrameId.from_dict(obj["observation_frame_id"]),
            transition_semantics_id=SyntheticTransitionSemanticsId.from_dict(obj["transition_semantics_id"]),
            nodes=obj["nodes"], edges=obj["edges"], boundary_ports=obj["boundary_ports"],
            separator_node_ids=obj["separator_node_ids"], target_node_id=obj["target_node_id"],
        )

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "BeforeLocalRegion":
        return cls.from_dict(_parse_wire(raw))


@dataclass(frozen=True)
class LocalityFeatureVector:
    node_kind_count_rows: tuple[tuple[str, int], ...]
    boundary_port_kind_count_rows: tuple[tuple[str, int], ...]
    shared_mvar_degree_multiset: tuple[int, ...]
    component_size_profile_after_separator_deletion: tuple[int, ...]
    articulation_count: int
    cycle_rank: int
    exact_treewidth: int
    radius: int
    target_site_kind: str

    def __post_init__(self) -> None:
        for rows, label in (
            (self.node_kind_count_rows, "node kind counts"),
            (self.boundary_port_kind_count_rows, "boundary port counts"),
        ):
            if (
                type(rows) is not tuple
                or tuple(sorted(rows, key=lambda row: row[0].encode("utf-8"))) != rows
                or len({row[0] for row in rows}) != len(rows)
            ):
                _fail(f"{label} are not canonical and unique")
            for kind, count in rows:
                _identifier(kind, label)
                _integer(count, label, minimum=1)
        if (
            type(self.shared_mvar_degree_multiset) is not tuple
            or tuple(sorted(self.shared_mvar_degree_multiset))
            != self.shared_mvar_degree_multiset
            or any(
                type(value) is not int or value < 0 or value > _MAX_NODES
                for value in self.shared_mvar_degree_multiset
            )
        ):
            _fail("shared-mvar degree multiset is not canonical")
        if (
            type(self.component_size_profile_after_separator_deletion) is not tuple
            or tuple(sorted(self.component_size_profile_after_separator_deletion))
            != self.component_size_profile_after_separator_deletion
            or any(
                type(value) is not int or value < 1 or value > _MAX_NODES
                for value in self.component_size_profile_after_separator_deletion
            )
        ):
            _fail("separator component profile is not canonical")
        _integer(self.articulation_count, "articulation_count")
        _integer(self.cycle_rank, "cycle_rank")
        if _integer(self.exact_treewidth, "exact_treewidth") > _MAX_TREEWIDTH:
            _fail("feature treewidth exceeds the cap")
        _integer(self.radius, "radius")
        _identifier(self.target_site_kind, "target_site_kind")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _FEATURE_SCHEMA,
            "node_kind_count_rows": [{"kind": k, "count": n} for k, n in self.node_kind_count_rows],
            "boundary_port_kind_count_rows": [{"kind": k, "count": n} for k, n in self.boundary_port_kind_count_rows],
            "shared_mvar_degree_multiset": list(self.shared_mvar_degree_multiset),
            "component_size_profile_after_separator_deletion": list(self.component_size_profile_after_separator_deletion),
            "articulation_count": self.articulation_count,
            "cycle_rank": self.cycle_rank,
            "exact_treewidth": self.exact_treewidth,
            "radius": self.radius,
            "target_site_kind": self.target_site_kind,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalityFeatureVector":
        obj = _object(value, {"schema_version", "node_kind_count_rows", "boundary_port_kind_count_rows", "shared_mvar_degree_multiset", "component_size_profile_after_separator_deletion", "articulation_count", "cycle_rank", "exact_treewidth", "radius", "target_site_kind"}, "LocalityFeatureVector")
        if obj["schema_version"] != _FEATURE_SCHEMA:
            _fail("wrong LocalityFeatureVector schema")
        def rows(raw: Any, label: str) -> tuple[tuple[str, int], ...]:
            values = _bounded_tuple(raw, maximum=_MAX_JSON_ARRAY, label=label)
            result = []
            for row in values:
                item = _object(row, {"kind", "count"}, label)
                result.append((_identifier(item["kind"], label), _integer(item["count"], label, minimum=1)))
            return tuple(result)
        result = cls(
            rows(obj["node_kind_count_rows"], "node kind row"),
            rows(obj["boundary_port_kind_count_rows"], "boundary kind row"),
            tuple(_integer(v, "shared mvar degree") for v in _bounded_tuple(obj["shared_mvar_degree_multiset"], maximum=_MAX_NODES, label="shared degrees")),
            tuple(_integer(v, "component size", minimum=1) for v in _bounded_tuple(obj["component_size_profile_after_separator_deletion"], maximum=_MAX_NODES, label="component profile")),
            _integer(obj["articulation_count"], "articulation_count"),
            _integer(obj["cycle_rank"], "cycle_rank"),
            _integer(obj["exact_treewidth"], "exact_treewidth"),
            _integer(obj["radius"], "radius"),
            _identifier(obj["target_site_kind"], "target_site_kind"),
        )
        if result.to_dict() != obj:
            _fail("LocalityFeatureVector is not canonical")
        return result


@dataclass(frozen=True)
class LocalityQuery:
    query_id: str
    observation_frame_id: ObservationFrameId
    transition_semantics_id: SyntheticTransitionSemanticsId
    response_vocabulary_id: ResponseVocabularyId
    action_catalog_digest: str
    action_word: tuple[ActionSymbol, ...]
    closing_context_id: str
    closing_action_word: tuple[ActionSymbol, ...]
    response_keys: tuple[BehavioralObservationKey, ...]
    _gate_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._gate_token is not _CONSTRUCTION_TOKEN:
            _fail("LocalityQuery must be built by make_locality_query")
        _identifier(self.query_id, "query_id")
        if (
            type(self.observation_frame_id) is not ObservationFrameId
            or type(self.transition_semantics_id) is not SyntheticTransitionSemanticsId
            or type(self.response_vocabulary_id) is not ResponseVocabularyId
        ):
            _fail("query frame, semantics, or response vocabulary is not strict")
        if (
            _digest(self.action_catalog_digest, "query action catalogue digest")
            != self.transition_semantics_id.action_alphabet_digest
            or self.observation_frame_id.coordinate_schema_digest
            != self.response_vocabulary_id.coordinate_schema_digest
        ):
            _fail("query catalogue or response vocabulary binding is inconsistent")
        if (
            type(self.action_word) is not tuple
            or not self.action_word
            or type(self.closing_action_word) is not tuple
            or len(self.action_word) + len(self.closing_action_word)
            > _MAX_ACTION_DEPTH
            or not all(
                type(symbol) is ActionSymbol
                for symbol in self.action_word + self.closing_action_word
            )
            or any(
                not symbol.action_id.startswith(_L0_ADMISSION_PREFIX)
                for symbol in self.action_word + self.closing_action_word
            )
        ):
            _fail("query action words are not exact and bounded")
        _identifier(self.closing_context_id, "closing_context_id")
        if (
            type(self.response_keys) is not tuple
            or not self.response_keys
            or len(self.response_keys) > 8
            or not all(type(key) is BehavioralObservationKey for key in self.response_keys)
            or tuple(key.coordinate_key for key in self.response_keys)
            != self.response_vocabulary_id.coordinate_names
            or any(
                key.frame != self.observation_frame_id
                or key.projection_id != self.closing_context_id
                for key in self.response_keys
            )
        ):
            _fail("query response keys are not the bound ordered vocabulary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _QUERY_SCHEMA,
            "query_id": self.query_id,
            "observation_frame_id": self.observation_frame_id.to_dict(),
            "transition_semantics_id": self.transition_semantics_id.to_dict(),
            "response_vocabulary_id": self.response_vocabulary_id.to_dict(),
            "action_catalog_digest": self.action_catalog_digest,
            "action_word": [item.to_dict() for item in self.action_word],
            "closing_context_id": self.closing_context_id,
            "closing_action_word": [item.to_dict() for item in self.closing_action_word],
            "response_keys": [item.to_dict() for item in self.response_keys],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LocalityQuery":
        obj = _object(
            value,
            {
                "schema_version",
                "query_id",
                "observation_frame_id",
                "transition_semantics_id",
                "response_vocabulary_id",
                "action_catalog_digest",
                "action_word",
                "closing_context_id",
                "closing_action_word",
                "response_keys",
            },
            "LocalityQuery",
        )
        if obj["schema_version"] != _QUERY_SCHEMA:
            _fail("wrong LocalityQuery schema")
        action_rows = _bounded_tuple(
            obj["action_word"], maximum=_MAX_ACTION_DEPTH, minimum=1,
            label="query action word",
        )
        closing_rows = _bounded_tuple(
            obj["closing_action_word"], maximum=_MAX_ACTION_DEPTH,
            label="query closing action word",
        )
        key_rows = _bounded_tuple(
            obj["response_keys"], maximum=8, minimum=1,
            label="query response keys",
        )
        result = cls(
            query_id=_identifier(obj["query_id"], "query_id"),
            observation_frame_id=ObservationFrameId.from_dict(
                obj["observation_frame_id"]
            ),
            transition_semantics_id=SyntheticTransitionSemanticsId.from_dict(
                obj["transition_semantics_id"]
            ),
            response_vocabulary_id=ResponseVocabularyId.from_dict(
                obj["response_vocabulary_id"]
            ),
            action_catalog_digest=_digest(
                obj["action_catalog_digest"], "query action catalogue digest"
            ),
            action_word=tuple(ActionSymbol.from_dict(row) for row in action_rows),
            closing_context_id=_identifier(
                obj["closing_context_id"], "closing_context_id"
            ),
            closing_action_word=tuple(
                ActionSymbol.from_dict(row) for row in closing_rows
            ),
            response_keys=tuple(
                BehavioralObservationKey.from_dict(row) for row in key_rows
            ),
            _gate_token=_CONSTRUCTION_TOKEN,
        )
        if result.to_dict() != obj:
            _fail("LocalityQuery is not canonical")
        return result

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "LocalityQuery":
        return cls.from_dict(_parse_wire(raw))


@dataclass(frozen=True)
class ExactLocalResponseObservation:
    family_id: str
    instance_id: str
    region_id: str
    query: LocalityQuery
    response_vector: tuple[ExactRational, ...]
    snapshot_sha256: str
    certificate_sha256: str
    terminal_state_id: str
    terminal_block_index: int
    _verified_partition: VerifiedExactPartition | None = field(
        default=None, repr=False, compare=False
    )
    _gate_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._gate_token is not _CONSTRUCTION_TOKEN
            or type(self._verified_partition) is not VerifiedExactPartition
        ):
            _fail("exact local observation requires an independently verified source")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _OBSERVATION_SCHEMA,
            "family_id": self.family_id, "instance_id": self.instance_id,
            "region_id": self.region_id, "query": self.query.to_dict(),
            "response_vector": [v.to_dict() for v in self.response_vector],
            "snapshot_sha256": self.snapshot_sha256,
            "certificate_sha256": self.certificate_sha256,
            "terminal_state_id": self.terminal_state_id,
            "terminal_block_index": self.terminal_block_index,
        }


@dataclass(frozen=True)
class ExactLocalCounterexample:
    family_id: str
    instance_id: str
    query: LocalityQuery
    left_region_id: str
    right_region_id: str
    left_response_vector: tuple[ExactRational, ...]
    right_response_vector: tuple[ExactRational, ...]
    first_differing_coordinate: int
    first_differing_coordinate_key: BehavioralObservationKey
    snapshot_sha256: str
    certificate_sha256: str
    left_terminal_state_id: str
    right_terminal_state_id: str
    left_terminal_block_index: int
    right_terminal_block_index: int
    _left_observation: ExactLocalResponseObservation | None = field(
        default=None, repr=False, compare=False
    )
    _right_observation: ExactLocalResponseObservation | None = field(
        default=None, repr=False, compare=False
    )
    _gate_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._gate_token is not _CONSTRUCTION_TOKEN
            or type(self._left_observation) is not ExactLocalResponseObservation
            or type(self._right_observation) is not ExactLocalResponseObservation
        ):
            _fail("ExactLocalCounterexample must be derived from exact observations")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _COUNTEREXAMPLE_SCHEMA,
            "family_id": self.family_id, "instance_id": self.instance_id,
            "query": self.query.to_dict(), "left_region_id": self.left_region_id,
            "right_region_id": self.right_region_id,
            "left_response_vector": [v.to_dict() for v in self.left_response_vector],
            "right_response_vector": [v.to_dict() for v in self.right_response_vector],
            "first_differing_coordinate": self.first_differing_coordinate,
            "first_differing_coordinate_key": self.first_differing_coordinate_key.to_dict(),
            "snapshot_sha256": self.snapshot_sha256, "certificate_sha256": self.certificate_sha256,
            "left_terminal_state_id": self.left_terminal_state_id,
            "right_terminal_state_id": self.right_terminal_state_id,
            "left_terminal_block_index": self.left_terminal_block_index,
            "right_terminal_block_index": self.right_terminal_block_index,
        }


@dataclass(frozen=True)
class ProposedNominalPartition:
    observation_frame_id: ObservationFrameId
    transition_semantics_id: SyntheticTransitionSemanticsId
    action_catalog_digest: str
    region_ids: tuple[str, ...]
    blocks: tuple[tuple[str, ...], ...]
    must_not_link_edges: tuple[tuple[str, str], ...]
    generation: int
    evidence_tier: PipelineEvidenceTier = field(default=PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY, init=False)
    hard_eligible: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.observation_frame_id) is not ObservationFrameId or type(self.transition_semantics_id) is not SyntheticTransitionSemanticsId:
            _fail("partition frame or semantics is not strict")
        _digest(self.action_catalog_digest, "partition action catalogue digest")
        if type(self.region_ids) is not tuple or not self.region_ids or len(self.region_ids) > _MAX_REGIONS:
            _fail("partition region IDs violate the cap")
        if tuple(sorted(self.region_ids, key=lambda v: v.encode("utf-8"))) != self.region_ids or len(set(self.region_ids)) != len(self.region_ids):
            _fail("partition region IDs are not canonical and unique")
        members = tuple(member for block in self.blocks for member in block)
        if tuple(sorted(members, key=lambda v: v.encode("utf-8"))) != self.region_ids or _canonical_blocks(self.blocks) != self.blocks:
            _fail("partition blocks do not canonically cover the region universe")
        for edge in self.must_not_link_edges:
            if _canonical_pair(*edge) != edge or not set(edge).issubset(self.region_ids):
                _fail("partition must-not-link edge is invalid")
            if _block_owner(self)[edge[0]] == _block_owner(self)[edge[1]]:
                _fail("must-not-link endpoints remain co-blocked")
        if tuple(
            sorted(
                set(self.must_not_link_edges),
                key=lambda edge: canonical_contract_bytes(list(edge)),
            )
        ) != self.must_not_link_edges:
            _fail("must-not-link edges are not canonical and unique")
        _integer(self.generation, "partition generation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _PARTITION_SCHEMA,
            "observation_frame_id": self.observation_frame_id.to_dict(),
            "transition_semantics_id": self.transition_semantics_id.to_dict(),
            "action_catalog_digest": self.action_catalog_digest,
            "region_ids": list(self.region_ids), "blocks": [list(b) for b in self.blocks],
            "must_not_link_edges": [list(e) for e in self.must_not_link_edges],
            "generation": self.generation,
            "evidence_tier": "NOMINAL_DIAGNOSTIC_ONLY",
            "hard_eligible": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProposedNominalPartition":
        obj = _object(
            value,
            {
                "schema_version",
                "observation_frame_id",
                "transition_semantics_id",
                "action_catalog_digest",
                "region_ids",
                "blocks",
                "must_not_link_edges",
                "generation",
                "evidence_tier",
                "hard_eligible",
            },
            "ProposedNominalPartition",
        )
        if (
            obj["schema_version"] != _PARTITION_SCHEMA
            or obj["evidence_tier"]
            != "NOMINAL_DIAGNOSTIC_ONLY"
            or obj["hard_eligible"] is not False
        ):
            _fail("partition schema or nominal firewall is invalid")
        region_rows = _bounded_tuple(
            obj["region_ids"], maximum=_MAX_REGIONS, minimum=1,
            label="partition region IDs",
        )
        block_rows = _bounded_tuple(
            obj["blocks"], maximum=_MAX_REGIONS, minimum=1,
            label="partition blocks",
        )
        edge_rows = _bounded_tuple(
            obj["must_not_link_edges"], maximum=_MAX_RESPONSE_CELLS,
            label="partition must-not-link edges",
        )
        blocks = tuple(
            tuple(
                _identifier(member, "partition block member")
                for member in _bounded_tuple(
                    block, maximum=_MAX_REGIONS, minimum=1,
                    label="partition block",
                )
            )
            for block in block_rows
        )
        edges: list[tuple[str, str]] = []
        for row in edge_rows:
            pair = _bounded_tuple(
                row, maximum=2, minimum=2, label="must-not-link edge"
            )
            edges.append(
                (
                    _identifier(pair[0], "must-not-link left"),
                    _identifier(pair[1], "must-not-link right"),
                )
            )
        result = cls(
            observation_frame_id=ObservationFrameId.from_dict(
                obj["observation_frame_id"]
            ),
            transition_semantics_id=SyntheticTransitionSemanticsId.from_dict(
                obj["transition_semantics_id"]
            ),
            action_catalog_digest=_digest(
                obj["action_catalog_digest"], "partition action catalogue digest"
            ),
            region_ids=tuple(
                _identifier(member, "partition region ID") for member in region_rows
            ),
            blocks=blocks,
            must_not_link_edges=tuple(edges),
            generation=_integer(obj["generation"], "partition generation"),
        )
        if result.to_dict() != obj:
            _fail("ProposedNominalPartition is not canonical")
        return result

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "ProposedNominalPartition":
        return cls.from_dict(_parse_wire(raw))


@dataclass(frozen=True)
class LocalityQueryScore:
    family_id: str
    instance_id: str
    left_region_id: str
    right_region_id: str
    query: LocalityQuery
    canonical_candidate_json: str
    partition_sha256: str
    covariance_before_sha256: str
    trace_before: ExactRational
    covariance_after_sha256: str
    trace_after: ExactRational
    gain: ExactRational
    derived_cost: int
    score: ExactRational
    evidence_tier: PipelineEvidenceTier = field(default=PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY, init=False)
    hard_eligible: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCORE_SCHEMA, "family_id": self.family_id,
            "instance_id": self.instance_id, "left_region_id": self.left_region_id,
            "right_region_id": self.right_region_id, "query": self.query.to_dict(),
            "canonical_candidate_json": self.canonical_candidate_json,
            "partition_sha256": self.partition_sha256,
            "covariance_before_sha256": self.covariance_before_sha256,
            "trace_before": self.trace_before.to_dict(),
            "covariance_after_sha256": self.covariance_after_sha256,
            "trace_after": self.trace_after.to_dict(), "gain": self.gain.to_dict(),
            "derived_cost": self.derived_cost, "score": self.score.to_dict(),
            "evidence_tier": "NOMINAL_DIAGNOSTIC_ONLY", "hard_eligible": False,
        }


@dataclass(frozen=True)
class LocalityCEGARReport:
    family_id: str
    instance_id: str
    observation_frame_id: ObservationFrameId
    transition_semantics_id: SyntheticTransitionSemanticsId
    action_catalog_digest: str
    initial_partition: ProposedNominalPartition | None
    final_partition: ProposedNominalPartition | None
    selected_scores: tuple[LocalityQueryScore, ...]
    terminal_status: str
    terminal_reason: str
    candidate_observations_consumed: int
    cumulative_derived_cost: int
    evidence_tier: PipelineEvidenceTier = field(default=PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY, init=False)
    hard_eligible: bool = field(default=False, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _REPORT_SCHEMA, "family_id": self.family_id,
            "instance_id": self.instance_id,
            "observation_frame_id": self.observation_frame_id.to_dict(),
            "transition_semantics_id": self.transition_semantics_id.to_dict(),
            "action_catalog_digest": self.action_catalog_digest,
            "initial_partition": None if self.initial_partition is None else self.initial_partition.to_dict(),
            "final_partition": None if self.final_partition is None else self.final_partition.to_dict(),
            "selected_scores": [v.to_dict() for v in self.selected_scores],
            "terminal_status": self.terminal_status, "terminal_reason": self.terminal_reason,
            "candidate_observations_consumed": self.candidate_observations_consumed,
            "cumulative_derived_cost": self.cumulative_derived_cost,
            "evidence_tier": "NOMINAL_DIAGNOSTIC_ONLY", "hard_eligible": False,
        }


class LocalityResultDisposition(str, Enum):
    L0_SYNTHETIC_CEGAR_GAIN_OBSERVED = "L0_SYNTHETIC_CEGAR_GAIN_OBSERVED"
    L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN = "L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN"
    L0_SYNTHETIC_CEGAR_DEGRADED = "L0_SYNTHETIC_CEGAR_DEGRADED"
    L0_PREREQUISITE_BLOCKED = "L0_PREREQUISITE_BLOCKED"
    L0_EXECUTION_FAILED = "L0_EXECUTION_FAILED"


def make_before_local_region(
    *, region_id: str, observation_frame_id: ObservationFrameId,
    transition_semantics_id: SyntheticTransitionSemanticsId,
    nodes: Sequence[Any], edges: Sequence[Any], boundary_ports: Sequence[Any],
    separator_node_ids: Sequence[str], target_node_id: str,
) -> BeforeLocalRegion:
    region_id = _identifier(region_id, "region_id")
    if type(observation_frame_id) is not ObservationFrameId or type(transition_semantics_id) is not SyntheticTransitionSemanticsId:
        _fail("region frame or transition semantics is not strict")
    raw_nodes = _bounded_tuple(nodes, maximum=_MAX_NODES, minimum=1, label="region nodes")
    raw_edges = _bounded_tuple(edges, maximum=_MAX_EDGES, label="region edges")
    raw_ports = _bounded_tuple(boundary_ports, maximum=_MAX_JSON_ARRAY, label="boundary ports")
    raw_separators = _bounded_tuple(separator_node_ids, maximum=_MAX_NODES, label="separator nodes")
    target = _identifier(target_node_id, "target_node_id")

    parsed_nodes: list[tuple[str, str]] = []
    for row in raw_nodes:
        if type(row) is tuple and len(row) == 2:
            node_id, node_kind = row
        else:
            item = _object(row, {"node_id", "node_kind"}, "node row")
            node_id, node_kind = item["node_id"], item["node_kind"]
        parsed_nodes.append((_identifier(node_id, "node_id"), _identifier(node_kind, "node_kind")))
    node_ids = tuple(row[0] for row in parsed_nodes)
    if len(set(node_ids)) != len(node_ids) or target not in node_ids:
        _fail("region node IDs are duplicate or target is absent")
    occurrence = (target,) + tuple(node for node in node_ids if node != target)
    rename = {node: f"n{index}" for index, node in enumerate(occurrence)}
    kind_by_old = {node: kind for node, kind in parsed_nodes}
    canonical_nodes = tuple((f"n{index}", kind_by_old[node]) for index, node in enumerate(occurrence))

    parsed_edges: list[tuple[str, str, str]] = []
    endpoints: set[tuple[str, str]] = set()
    for row in raw_edges:
        if type(row) is tuple and len(row) == 3:
            source, target_value, kind = row
        else:
            item = _object(row, {"source", "target", "edge_kind"}, "edge row")
            source, target_value, kind = item["source"], item["target"], item["edge_kind"]
        source = _identifier(source, "edge source")
        target_value = _identifier(target_value, "edge target")
        kind = _identifier(kind, "edge kind")
        if source not in rename or target_value not in rename or source == target_value:
            _fail("edge endpoint is absent or self-looped")
        pair = tuple(sorted((rename[source], rename[target_value]), key=lambda value: int(value[1:])))
        if pair in endpoints:
            _fail("duplicate undirected edge")
        endpoints.add(pair)
        parsed_edges.append((pair[0], pair[1], kind))
    canonical_edges = tuple(sorted(parsed_edges, key=lambda row: (int(row[0][1:]), int(row[1][1:]), row[2].encode("utf-8"))))

    parsed_ports: list[tuple[str, str, str]] = []
    seen_port_ids: set[str] = set()
    for index, row in enumerate(raw_ports):
        if type(row) is tuple and len(row) == 3:
            port_id, kind, attached = row
        else:
            item = _object(row, {"port_id", "kind", "attached_node_id"}, "boundary port")
            port_id, kind, attached = item["port_id"], item["kind"], item["attached_node_id"]
        port_id = _identifier(port_id, "port_id")
        if port_id in seen_port_ids or attached not in rename:
            _fail("boundary port is duplicate or detached")
        seen_port_ids.add(port_id)
        parsed_ports.append((f"p{index}", _identifier(kind, "boundary port kind"), rename[attached]))
    canonical_ports = tuple(
        sorted(parsed_ports, key=lambda row: canonical_contract_bytes(list(row)))
    )
    separators = tuple(sorted((_identifier(v, "separator node") for v in raw_separators), key=lambda value: int(rename[value][1:]) if value in rename else _MAX_NODES + 1))
    if len(set(separators)) != len(separators) or any(value not in rename for value in separators):
        _fail("separator node set is invalid")
    canonical_separators = tuple(rename[value] for value in separators)
    result = BeforeLocalRegion(region_id, observation_frame_id, transition_semantics_id, canonical_nodes, canonical_edges, canonical_ports, canonical_separators, "n0", _gate_token=_CONSTRUCTION_TOKEN)
    extract_before_locality_features(result)
    if len(canonical_contract_bytes(result.to_dict())) > _MAX_WIRE_BYTES:
        _fail("region wire exceeds one MiB")
    return result


def extract_before_locality_features(region: BeforeLocalRegion) -> LocalityFeatureVector:
    if type(region) is not BeforeLocalRegion:
        _fail("feature extraction requires a BeforeLocalRegion")
    node_count = len(region.nodes)
    adjacency = {node_id: set() for node_id, _ in region.nodes}
    for source, target, _ in region.edges:
        adjacency[source].add(target); adjacency[target].add(source)
    distances = {region.target_node_id: 0}
    queue = deque((region.target_node_id,))
    while queue:
        current = queue.popleft()
        for target in sorted(adjacency[current], key=lambda value: int(value[1:])):
            if target not in distances:
                distances[target] = distances[current] + 1; queue.append(target)
    if len(distances) != node_count:
        _fail("region graph is disconnected from its target")

    def component_count(excluded: set[str]) -> int:
        remaining = set(adjacency) - excluded; count = 0
        while remaining:
            count += 1; seed = min(remaining, key=lambda value: int(value[1:])); remaining.remove(seed)
            frontier = [seed]
            while frontier:
                current = frontier.pop()
                for target in adjacency[current] - excluded:
                    if target in remaining:
                        remaining.remove(target); frontier.append(target)
        return count

    base_components = component_count(set())
    articulation = sum(component_count({node}) > base_components for node in adjacency)
    separator_set = set(region.separator_node_ids)
    remaining = set(adjacency) - separator_set; component_sizes: list[int] = []
    while remaining:
        seed = min(remaining, key=lambda value: int(value[1:])); remaining.remove(seed); size = 1; frontier = [seed]
        while frontier:
            current = frontier.pop()
            for target in adjacency[current] - separator_set:
                if target in remaining:
                    remaining.remove(target); size += 1; frontier.append(target)
        component_sizes.append(size)

    names = tuple(node for node, _ in region.nodes)
    original_edges = {frozenset((a, b)) for a, b, _ in region.edges}
    full_mask = (1 << node_count) - 1
    dp = [_MAX_NODES] * (1 << node_count); dp[0] = 0
    for mask in range(1 << node_count):
        if dp[mask] == _MAX_NODES:
            continue
        eliminated = {names[index] for index in range(node_count) if mask & (1 << index)}
        for index, vertex in enumerate(names):
            bit = 1 << index
            if mask & bit:
                continue
            degree = 0
            for other_index, other in enumerate(names):
                if other == vertex or mask & (1 << other_index):
                    continue
                allowed = eliminated | {vertex, other}; seen = {vertex}; frontier = [vertex]; connected = False
                while frontier and not connected:
                    current = frontier.pop()
                    for edge in original_edges:
                        if current not in edge:
                            continue
                        target = next(iter(edge - {current}))
                        if target == other:
                            connected = True; break
                        if target in allowed and target not in seen:
                            seen.add(target); frontier.append(target)
                degree += int(connected)
            new_mask = mask | bit; candidate = max(dp[mask], degree)
            if candidate < dp[new_mask]:
                dp[new_mask] = candidate
    treewidth = dp[full_mask]
    if treewidth > _MAX_TREEWIDTH:
        _fail("exact treewidth exceeds the L0 cap")

    kind_counts: dict[str, int] = {}
    node_kind = dict(region.nodes)
    for kind in node_kind.values(): kind_counts[kind] = kind_counts.get(kind, 0) + 1
    port_counts: dict[str, int] = {}
    for _, kind, _ in region.boundary_ports: port_counts[kind] = port_counts.get(kind, 0) + 1
    return LocalityFeatureVector(
        tuple(sorted(kind_counts.items(), key=lambda row: row[0].encode("utf-8"))),
        tuple(sorted(port_counts.items(), key=lambda row: row[0].encode("utf-8"))),
        tuple(sorted(len(adjacency[node]) for node, kind in region.nodes if kind == "shared_mvar")),
        tuple(sorted(component_sizes)), articulation,
        len(region.edges) - node_count + base_components, treewidth,
        max(distances.values()), node_kind[region.target_node_id],
    )


def make_locality_query(
    *, query_id: str, observation_frame_id: ObservationFrameId,
    transition_semantics_id: SyntheticTransitionSemanticsId,
    response_vocabulary_id: ResponseVocabularyId,
    action_catalog: Sequence[SyntheticAction], action_word_ids: Sequence[str],
    closing_context_id: str, closing_action_ids: Sequence[str],
    response_coordinate_ids: Sequence[str],
) -> LocalityQuery:
    query_id = _identifier(query_id, "query_id")
    if type(observation_frame_id) is not ObservationFrameId or type(transition_semantics_id) is not SyntheticTransitionSemanticsId or type(response_vocabulary_id) is not ResponseVocabularyId:
        _fail("query frame, semantics, or response vocabulary is not strict")
    actions = _bounded_tuple(action_catalog, maximum=_MAX_QUERIES, minimum=1, label="action catalogue")
    symbols = tuple(_action_symbol(action) for action in actions)
    by_id = {symbol.action_id: symbol for symbol in symbols}
    if len(by_id) != len(symbols): _fail("action catalogue IDs are not unique")
    derived = make_synthetic_transition_semantics_id(actions=actions, response_vocabulary_id=response_vocabulary_id)
    if derived != transition_semantics_id or observation_frame_id.coordinate_schema_digest != response_vocabulary_id.coordinate_schema_digest:
        _fail("query frame/semantics do not bind the complete action catalogue")
    word_ids = _bounded_tuple(action_word_ids, maximum=_MAX_ACTION_DEPTH, minimum=1, label="action word")
    closing_ids = _bounded_tuple(closing_action_ids, maximum=_MAX_ACTION_DEPTH, label="closing action word")
    if len(word_ids) + len(closing_ids) > _MAX_ACTION_DEPTH: _fail("combined query action depth exceeds three")
    if any(type(value) is not str or value not in by_id for value in word_ids + closing_ids): _fail("query word uses an action outside the complete catalogue")
    coordinates = _bounded_tuple(response_coordinate_ids, maximum=8, minimum=1, label="response coordinates")
    if tuple(coordinates) != response_vocabulary_id.coordinate_names:
        _fail("query response coordinate order disagrees with its vocabulary")
    context_id = _identifier(closing_context_id, "closing_context_id")
    keys = tuple(BehavioralObservationKey(observation_frame_id, context_id, _identifier(value, "response coordinate")) for value in coordinates)
    result = LocalityQuery(query_id, observation_frame_id, transition_semantics_id, response_vocabulary_id, transition_semantics_id.action_alphabet_digest, tuple(by_id[value] for value in word_ids), context_id, tuple(by_id[value] for value in closing_ids), keys, _gate_token=_CONSTRUCTION_TOKEN)
    if len(canonical_contract_bytes(result.to_dict())) > _MAX_WIRE_BYTES: _fail("query wire exceeds one MiB")
    return result


def derive_exact_query_cost(query: LocalityQuery) -> int:
    if type(query) is not LocalityQuery: _fail("query cost requires a LocalityQuery")
    cost = 2 * (len(query.action_word) + len(query.closing_action_word) + len(query.response_keys))
    if cost < 1: _fail("derived query cost is not positive")
    return cost


def _verified_observation_source_material(
    verified_partition: VerifiedExactPartition,
) -> tuple[
    dict[str, Any],
    dict[str, tuple[Any, ...]],
    dict[str, ActionSymbol],
    dict[tuple[str, str], str],
    dict[str, int],
    str,
    str,
]:
    if type(verified_partition) is not VerifiedExactPartition:
        _fail("exact local observation requires a VerifiedExactPartition capability")
    snapshot = verified_partition.admitted.snapshot
    state_by_id = {state.state_id: state for state in snapshot.states}
    if len(state_by_id) != len(snapshot.states):
        _fail("retained snapshot state IDs are not unique")
    states_by_payload: dict[str, list[Any]] = {}
    for state in snapshot.states:
        states_by_payload.setdefault(state.payload.canonical_json, []).append(state)
    action_symbols: dict[str, ActionSymbol] = {}
    for action in snapshot.actions:
        symbol = _action_symbol(action)
        if symbol.action_id in action_symbols:
            _fail("retained snapshot action catalogue is not unique")
        action_symbols[symbol.action_id] = symbol
    transition_lookup: dict[tuple[str, str], str] = {}
    for row in snapshot.transitions:
        key = (row.source_state_id, row.action_id)
        if key in transition_lookup:
            _fail("retained snapshot transition table is not functional")
        transition_lookup[key] = row.target_state_id
    terminal_block_owner: dict[str, int] = {}
    for block in verified_partition.certificate.final_blocks:
        for state_id in block.member_state_ids:
            if state_id in terminal_block_owner:
                _fail("verified partition assigns a state to multiple final blocks")
            terminal_block_owner[state_id] = block.block_index
    return (
        state_by_id,
        {key: tuple(value) for key, value in states_by_payload.items()},
        action_symbols,
        transition_lookup,
        terminal_block_owner,
        verified_partition.admitted.admission_report.snapshot_sha256,
        _sha(verified_partition.certificate.to_dict()),
    )


@dataclass(frozen=True, slots=True)
class _VerifiedObservationSourceIssuance:
    """Private immutable witness that one binder issued one exact index bundle."""

    verified_partition: VerifiedExactPartition
    state_by_id: Mapping[str, Any]
    state_by_payload: Mapping[str, tuple[Any, ...]]
    action_symbols: Mapping[str, ActionSymbol]
    transition_lookup: Mapping[tuple[str, str], str]
    terminal_block_owner: Mapping[str, int]
    snapshot_sha256: str
    certificate_sha256: str
    _identity_binding: tuple[Any, ...] = field(repr=False, compare=False)
    _gate_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._gate_token is not _CONSTRUCTION_TOKEN:
            _fail("verified observation source issuance bypassed its private binder")
        expected = (
            id(self.verified_partition),
            id(self.state_by_id),
            id(self.state_by_payload),
            id(self.action_symbols),
            id(self.transition_lookup),
            id(self.terminal_block_owner),
            self.snapshot_sha256,
            self.certificate_sha256,
        )
        if self._identity_binding != expected:
            _fail("verified observation source issuance identity changed")


@dataclass(frozen=True)
class _VerifiedObservationSource:
    """Invocation-local indexes derived from one exact verifier capability."""

    verified_partition: VerifiedExactPartition
    state_by_id: Mapping[str, Any]
    state_by_payload: Mapping[str, tuple[Any, ...]]
    action_symbols: Mapping[str, ActionSymbol]
    transition_lookup: Mapping[tuple[str, str], str]
    terminal_block_owner: Mapping[str, int]
    snapshot_sha256: str
    certificate_sha256: str
    _issuance: _VerifiedObservationSourceIssuance = field(
        repr=False, compare=False
    )
    _gate_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._gate_token is not _CONSTRUCTION_TOKEN:
            _fail("verified observation source bypassed its private binder")
        if type(self.verified_partition) is not VerifiedExactPartition:
            _fail("verified observation source lacks an exact verifier capability")
        if any(
            type(value) is not MappingProxyType
            for value in (
                self.state_by_id,
                self.state_by_payload,
                self.action_symbols,
                self.transition_lookup,
                self.terminal_block_owner,
            )
        ):
            _fail("verified observation source indexes are not immutable")
        issuance = self._issuance
        if (
            type(issuance) is not _VerifiedObservationSourceIssuance
            or issuance._gate_token is not _CONSTRUCTION_TOKEN
            or issuance.verified_partition is not self.verified_partition
            or issuance.state_by_id is not self.state_by_id
            or issuance.state_by_payload is not self.state_by_payload
            or issuance.action_symbols is not self.action_symbols
            or issuance.transition_lookup is not self.transition_lookup
            or issuance.terminal_block_owner is not self.terminal_block_owner
            or issuance.snapshot_sha256 != self.snapshot_sha256
            or issuance.certificate_sha256 != self.certificate_sha256
        ):
            _fail("verified observation source differs from its private issuance")


_VERIFIED_OBSERVATION_SOURCE_MEMO: list[
    tuple[VerifiedExactPartition, _VerifiedObservationSource]
] = []


def _clear_verified_observation_source_memo() -> None:
    _VERIFIED_OBSERVATION_SOURCE_MEMO.clear()


def _bind_verified_observation_source(
    verified_partition: VerifiedExactPartition,
) -> _VerifiedObservationSource:
    """Bind immutable indexes, memoized only for one exact capability at a time."""

    if _VERIFIED_OBSERVATION_SOURCE_MEMO:
        if len(_VERIFIED_OBSERVATION_SOURCE_MEMO) != 1:
            _fail("verified observation source memo is corrupted")
        retained, source = _VERIFIED_OBSERVATION_SOURCE_MEMO[0]
        if (
            type(retained) is not VerifiedExactPartition
            or type(source) is not _VerifiedObservationSource
            or source._gate_token is not _CONSTRUCTION_TOKEN
            or source.verified_partition is not retained
        ):
            _fail("verified observation source memo is corrupted")
        if retained is verified_partition:
            if (
                source.snapshot_sha256
                != retained.admitted.admission_report.snapshot_sha256
                or source.certificate_sha256
                != _sha(retained.certificate.to_dict())
            ):
                _fail("verified observation source memo binding changed")
            return source
        _clear_verified_observation_source_memo()

    (
        state_by_id,
        states_by_payload,
        action_symbols,
        transition_lookup,
        terminal_block_owner,
        snapshot_sha256,
        certificate_sha256,
    ) = _verified_observation_source_material(verified_partition)
    state_by_id_view = MappingProxyType(state_by_id)
    state_by_payload_view = MappingProxyType(states_by_payload)
    action_symbols_view = MappingProxyType(action_symbols)
    transition_lookup_view = MappingProxyType(transition_lookup)
    terminal_block_owner_view = MappingProxyType(terminal_block_owner)
    issuance = _VerifiedObservationSourceIssuance(
        verified_partition=verified_partition,
        state_by_id=state_by_id_view,
        state_by_payload=state_by_payload_view,
        action_symbols=action_symbols_view,
        transition_lookup=transition_lookup_view,
        terminal_block_owner=terminal_block_owner_view,
        snapshot_sha256=snapshot_sha256,
        certificate_sha256=certificate_sha256,
        _identity_binding=(
            id(verified_partition),
            id(state_by_id_view),
            id(state_by_payload_view),
            id(action_symbols_view),
            id(transition_lookup_view),
            id(terminal_block_owner_view),
            snapshot_sha256,
            certificate_sha256,
        ),
        _gate_token=_CONSTRUCTION_TOKEN,
    )
    source = _VerifiedObservationSource(
        verified_partition=verified_partition,
        state_by_id=state_by_id_view,
        state_by_payload=state_by_payload_view,
        action_symbols=action_symbols_view,
        transition_lookup=transition_lookup_view,
        terminal_block_owner=terminal_block_owner_view,
        snapshot_sha256=snapshot_sha256,
        certificate_sha256=certificate_sha256,
        _issuance=issuance,
        _gate_token=_CONSTRUCTION_TOKEN,
    )
    _VERIFIED_OBSERVATION_SOURCE_MEMO.append((verified_partition, source))
    return source


def _make_exact_local_response_observation_core(
    *,
    family_id: str,
    instance_id: str,
    region_id: str,
    query: LocalityQuery,
    response_vector: Sequence[ExactRational],
    terminal_state_id: str,
    source: _VerifiedObservationSource,
    query_sha256: str,
) -> ExactLocalResponseObservation:
    if type(source) is not _VerifiedObservationSource or source._gate_token is not _CONSTRUCTION_TOKEN:
        _fail("exact local observation source is not a private verified binding")
    verified_partition = source.verified_partition
    snapshot = verified_partition.admitted.snapshot
    if type(query) is not LocalityQuery:
        _fail("observation query is not strict")
    family_id = _identifier(family_id, "family_id")
    instance_id = _identifier(instance_id, "instance_id")
    region_id = _identifier(region_id, "region_id")
    terminal_state_id = _identifier(terminal_state_id, "terminal_state_id")
    query_sha256 = _digest(query_sha256, "complete query digest")
    values = tuple(
        _exact_rational(value, "response coordinate")
        for value in _bounded_tuple(
            response_vector,
            maximum=8,
            minimum=1,
            label="response vector",
        )
    )
    if len(values) != len(query.response_keys):
        _fail("response arity disagrees with query")
    if (
        snapshot.observation_frame_id != query.observation_frame_id
        or snapshot.transition_semantics_id != query.transition_semantics_id
        or snapshot.domain_id.action_alphabet_digest != query.action_catalog_digest
        or snapshot.response_vocabulary_id != query.response_vocabulary_id
    ):
        _fail("observation frame, semantics, catalogue, or response vocabulary was spliced")
    if not terminal_state_id.startswith(_L0_ADMISSION_PREFIX):
        _fail("terminal state is outside the frozen L0 admission prefix")
    state = source.state_by_id.get(terminal_state_id)
    if state is None:
        _fail("terminal state is absent or duplicate")
    if state.totalized_kind is not TotalizedStatus.OPEN or state.response_coordinates != values:
        _fail("terminal response is not the exact declared OPEN-state payload")
    terminal_payload = {
        "instance_id": instance_id,
        "kind": "u15_l0_terminal",
        "query_id": query.query_id,
        "query_sha256": query_sha256,
        "region_id": region_id,
    }
    if state.payload.canonical_json != canonical_contract_bytes(terminal_payload).decode("utf-8"):
        _fail("terminal payload binding does not match instance/region/query")
    source_payload = {
        "instance_id": instance_id,
        "kind": "u15_l0_source",
        "query_id": query.query_id,
        "query_sha256": query_sha256,
        "region_id": region_id,
    }
    sources = source.state_by_payload.get(
        canonical_contract_bytes(source_payload).decode("utf-8"), ()
    )
    if len(sources) != 1:
        _fail("query source state is absent or duplicate")
    source_state = sources[0]
    if (
        not source_state.state_id.startswith(_L0_ADMISSION_PREFIX)
        or source_state.state_id not in snapshot.seed_state_ids
        or source_state.totalized_kind is not TotalizedStatus.OPEN
    ):
        _fail("query source is outside the frozen prefix, seed set, or OPEN carrier")
    complete_word = query.action_word + query.closing_action_word
    if any(
        symbol.action_id not in source.action_symbols
        or source.action_symbols[symbol.action_id] != symbol
        for symbol in complete_word
    ):
        _fail("query word is not a complete ordered member of the retained catalogue")
    current_state_id = source_state.state_id
    for symbol in complete_word:
        key = (current_state_id, symbol.action_id)
        if key not in source.transition_lookup:
            _fail("query path is absent from the retained total transition table")
        current_state_id = source.transition_lookup[key]
        if current_state_id not in source.state_by_id:
            _fail("query path exits the retained snapshot carrier")
    if current_state_id != terminal_state_id:
        _fail("complete ordered query path does not reach the claimed terminal")
    owner = source.terminal_block_owner.get(terminal_state_id)
    if owner is None:
        _fail("terminal state has no unique verifier-issued block")
    return ExactLocalResponseObservation(
        family_id,
        instance_id,
        region_id,
        query,
        values,
        source.snapshot_sha256,
        source.certificate_sha256,
        terminal_state_id,
        owner,
        _verified_partition=verified_partition,
        _gate_token=_CONSTRUCTION_TOKEN,
    )


def _make_exact_local_response_observation_batch(
    requests: Sequence[tuple[Any, ...]],
    *,
    verified_partition: VerifiedExactPartition,
) -> tuple[ExactLocalResponseObservation, ...]:
    """Construct one bounded grid from one freshly bound verifier source."""

    rows = _bounded_tuple(
        requests,
        maximum=_MAX_RESPONSE_CELLS,
        minimum=1,
        label="exact observation requests",
    )
    source = _bind_verified_observation_source(verified_partition)
    query_digests: dict[str, tuple[LocalityQuery, str]] = {}
    result: list[ExactLocalResponseObservation] = []
    for row in rows:
        if type(row) is not tuple or len(row) != 6:
            _fail("exact observation request is not an exact six-tuple")
        family_id, instance_id, region_id, query, response_vector, terminal_state_id = row
        if type(query) is not LocalityQuery:
            _fail("observation query is not strict")
        cached = query_digests.get(query.query_id)
        if cached is None:
            query_sha256 = _sha(query.to_dict())
            query_digests[query.query_id] = (query, query_sha256)
        else:
            if cached[0] != query:
                _fail("observation batch reuses a query ID with different semantics")
            query_sha256 = cached[1]
        result.append(
            _make_exact_local_response_observation_core(
                family_id=family_id,
                instance_id=instance_id,
                region_id=region_id,
                query=query,
                response_vector=response_vector,
                terminal_state_id=terminal_state_id,
                source=source,
                query_sha256=query_sha256,
            )
        )
    return tuple(result)


def make_exact_local_response_observation(
    *, family_id: str, instance_id: str, region_id: str, query: LocalityQuery,
    response_vector: Sequence[ExactRational], verified_partition: VerifiedExactPartition,
    terminal_state_id: str,
) -> ExactLocalResponseObservation:
    return _make_exact_local_response_observation_batch(
        (
            (
                family_id,
                instance_id,
                region_id,
                query,
                response_vector,
                terminal_state_id,
            ),
        ),
        verified_partition=verified_partition,
    )[0]


def _reverify_observation(
    observation: ExactLocalResponseObservation,
) -> ExactLocalResponseObservation:
    if type(observation) is not ExactLocalResponseObservation:
        _fail("exact observation capability has the wrong type")
    source = _bind_verified_observation_source(observation._verified_partition)
    return _reverify_observation_batch((observation,), source=source)[0]


def _reverify_observation_batch(
    observations: tuple[ExactLocalResponseObservation, ...],
    *,
    source: _VerifiedObservationSource,
) -> tuple[ExactLocalResponseObservation, ...]:
    if (
        type(source) is not _VerifiedObservationSource
        or source._gate_token is not _CONSTRUCTION_TOKEN
    ):
        _fail("observation replay source is not a private verified binding")
    query_digests: dict[str, tuple[LocalityQuery, str]] = {}
    output: list[ExactLocalResponseObservation] = []
    for observation in observations:
        if type(observation) is not ExactLocalResponseObservation:
            _fail("exact observation capability has the wrong type")
        if observation._verified_partition is not source.verified_partition:
            _fail("observation replay crossed its verifier capability")
        cached = query_digests.get(observation.query.query_id)
        if cached is None:
            query_sha256 = _sha(observation.query.to_dict())
            query_digests[observation.query.query_id] = (
                observation.query,
                query_sha256,
            )
        else:
            if cached[0] != observation.query:
                _fail("observation replay reuses a query ID with different semantics")
            query_sha256 = cached[1]
        recomputed = _make_exact_local_response_observation_core(
            family_id=observation.family_id,
            instance_id=observation.instance_id,
            region_id=observation.region_id,
            query=observation.query,
            response_vector=observation.response_vector,
            terminal_state_id=observation.terminal_state_id,
            source=source,
            query_sha256=query_sha256,
        )
        if canonical_contract_bytes(recomputed.to_dict()) != canonical_contract_bytes(
            observation.to_dict()
        ):
            _fail("exact local observation no longer matches its retained verifier source")
        output.append(recomputed)
    return tuple(output)


def _find_exact_local_counterexample_core(
    partition: ProposedNominalPartition,
    left_observation: ExactLocalResponseObservation,
    right_observation: ExactLocalResponseObservation,
    *,
    reverify: bool,
) -> ExactLocalCounterexample | None:
    if type(partition) is not ProposedNominalPartition or type(left_observation) is not ExactLocalResponseObservation or type(right_observation) is not ExactLocalResponseObservation:
        _fail("counterexample search requires strict partition and observations")
    if reverify:
        left_observation = _reverify_observation(left_observation)
        right_observation = _reverify_observation(right_observation)
    left, right = (left_observation, right_observation)
    ordered = _canonical_pair(left.region_id, right.region_id)
    if ordered != (left.region_id, right.region_id): left, right = right, left
    bindings_equal = (
        left.family_id == right.family_id and left.instance_id == right.instance_id
        and left.query == right.query and left.snapshot_sha256 == right.snapshot_sha256
        and left.certificate_sha256 == right.certificate_sha256
        and partition.observation_frame_id == left.query.observation_frame_id
        and partition.transition_semantics_id == left.query.transition_semantics_id
        and partition.action_catalog_digest == left.query.action_catalog_digest
    )
    if not bindings_equal: _fail("cross-frame, semantics, catalogue, query, or source splicing")
    owner = _block_owner(partition)
    if left.region_id not in owner or right.region_id not in owner or owner[left.region_id] != owner[right.region_id]:
        return None
    if left.response_vector == right.response_vector:
        return None
    if left.terminal_block_index == right.terminal_block_index:
        _fail("unequal terminal responses lack distinct verified blocks")
    differing = next(index for index, pair in enumerate(zip(left.response_vector, right.response_vector)) if pair[0] != pair[1])
    return ExactLocalCounterexample(
        left.family_id,
        left.instance_id,
        left.query,
        left.region_id,
        right.region_id,
        left.response_vector,
        right.response_vector,
        differing,
        left.query.response_keys[differing],
        left.snapshot_sha256,
        left.certificate_sha256,
        left.terminal_state_id,
        right.terminal_state_id,
        left.terminal_block_index,
        right.terminal_block_index,
        _left_observation=left,
        _right_observation=right,
        _gate_token=_CONSTRUCTION_TOKEN,
    )


def find_exact_local_counterexample(
    partition: ProposedNominalPartition,
    left_observation: ExactLocalResponseObservation,
    right_observation: ExactLocalResponseObservation,
) -> ExactLocalCounterexample | None:
    return _find_exact_local_counterexample_core(
        partition,
        left_observation,
        right_observation,
        reverify=True,
    )


def propose_nominal_partition(
    regions: Sequence[BeforeLocalRegion], *, action_catalog_digest: str,
) -> ProposedNominalPartition:
    values = _bounded_tuple(regions, maximum=_MAX_REGIONS, minimum=1, label="regions")
    if not all(type(value) is BeforeLocalRegion for value in values): _fail("region universe contains a non-BeforeLocalRegion")
    frame = values[0].observation_frame_id; semantics = values[0].transition_semantics_id
    if any(value.observation_frame_id != frame or value.transition_semantics_id != semantics for value in values): _fail("region universe crosses frame or semantics")
    region_ids = tuple(sorted((_identifier(value.region_id, "region_id") for value in values), key=lambda value: value.encode("utf-8")))
    if len(set(region_ids)) != len(region_ids): _fail("region universe contains duplicate IDs")
    groups: dict[bytes, list[str]] = {}
    for value in values: groups.setdefault(_feature_key(extract_before_locality_features(value)), []).append(value.region_id)
    blocks = _canonical_blocks(tuple(groups.values()))
    return ProposedNominalPartition(frame, semantics, _digest(action_catalog_digest, "action catalogue digest"), region_ids, blocks, (), 0)


def _bind_exact_observation_grid(
    partition: ProposedNominalPartition,
    query_values: tuple[LocalityQuery, ...],
    observations: Sequence[ExactLocalResponseObservation],
    *,
    reverify: bool,
) -> tuple[
    tuple[ExactLocalResponseObservation, ...],
    dict[tuple[str, str], ExactLocalResponseObservation],
    str,
    str,
]:
    observation_values = _bounded_tuple(
        observations,
        maximum=_MAX_RESPONSE_CELLS,
        minimum=1,
        label="exact observation grid",
    )
    if not all(
        type(value) is ExactLocalResponseObservation
        for value in observation_values
    ):
        _fail("observation grid contains a non-exact member")
    query_by_id = {query.query_id: query for query in query_values}
    if any(
        value.query.query_id not in query_by_id
        or value.query != query_by_id[value.query.query_id]
        for value in observation_values
    ):
        _fail("observation query differs from its complete catalogue row")

    retained = observation_values[0]._verified_partition
    if type(retained) is not VerifiedExactPartition or any(
        value._verified_partition is not retained for value in observation_values
    ):
        _fail("observation grid does not retain one verifier capability")
    source = _bind_verified_observation_source(retained)
    snapshot_sha256 = source.snapshot_sha256
    certificate_sha256 = source.certificate_sha256
    if any(
        value.snapshot_sha256 != snapshot_sha256
        or value.certificate_sha256 != certificate_sha256
        for value in observation_values
    ):
        _fail("observation grid crosses snapshot or certificate source")
    if reverify:
        observation_values = _reverify_observation_batch(
            observation_values,
            source=source,
        )

    expected_cells = len(partition.region_ids) * len(query_values)
    response_cells = len(partition.region_ids) * sum(
        len(query.response_keys) for query in query_values
    )
    if (
        len(observation_values) != expected_cells
        or response_cells > _MAX_RESPONSE_CELLS
    ):
        _fail("observation grid is incomplete or exceeds its cell cap")
    lookup: dict[tuple[str, str], ExactLocalResponseObservation] = {}
    family_ids: set[str] = set()
    instance_ids: set[str] = set()
    for observation in observation_values:
        key = (observation.region_id, observation.query.query_id)
        if key in lookup:
            _fail("observation grid contains a duplicate row")
        lookup[key] = observation
        family_ids.add(observation.family_id)
        instance_ids.add(observation.instance_id)
    expected_keys = {
        (region_id, query.query_id)
        for region_id in partition.region_ids
        for query in query_values
    }
    if (
        len(family_ids) != 1
        or len(instance_ids) != 1
        or set(lookup) != expected_keys
    ):
        _fail("observation grid crosses carrier or is not complete")
    return (
        observation_values,
        lookup,
        next(iter(family_ids)),
        next(iter(instance_ids)),
    )


def _rank_locality_queries_core(
    partition: ProposedNominalPartition,
    queries: Sequence[LocalityQuery],
    observations: Sequence[ExactLocalResponseObservation],
    *, excluded_candidate_bytes: Sequence[str] = (),
    only_candidate: tuple[str, str, str] | None = None,
    reverify_observations: bool = True,
    bound_grid: tuple[
        tuple[ExactLocalResponseObservation, ...],
        dict[tuple[str, str], ExactLocalResponseObservation],
        str,
        str,
    ] | None = None,
    bound_behavior: dict[str, tuple[Fraction, ...]] | None = None,
    shared_covariance_cache: dict[
        tuple[tuple[str, ...], ...],
        tuple[tuple[tuple[ExactRational, ...], ...], ExactRational, str],
    ] | None = None,
) -> tuple[LocalityQueryScore, ...]:
    if type(partition) is not ProposedNominalPartition: _fail("ranker partition is not strict")
    query_values = _bounded_tuple(queries, maximum=_MAX_QUERIES, minimum=1, label="queries")
    if not all(type(query) is LocalityQuery for query in query_values) or len({q.query_id for q in query_values}) != len(query_values): _fail("query catalogue is not strict and unique")
    if any(q.observation_frame_id != partition.observation_frame_id or q.transition_semantics_id != partition.transition_semantics_id or q.action_catalog_digest != partition.action_catalog_digest for q in query_values): _fail("query catalogue crosses partition bindings")
    if sum(len(q.response_keys) for q in query_values) != _GLOBAL_DIMENSION: _fail("global behavior dimension is not exactly 16")
    if bound_grid is None:
        observation_values, lookup, family_id, instance_id = (
            _bind_exact_observation_grid(
                partition,
                query_values,
                observations,
                reverify=reverify_observations,
            )
        )
    else:
        if reverify_observations or type(bound_grid) is not tuple or len(bound_grid) != 4:
            _fail("prebound observation grid is not an internal verified tuple")
        observation_values, lookup, family_id, instance_id = bound_grid
    behavior = (
        {region: tuple(_fraction(value, "behavior coordinate") for query in query_values for value in lookup[(region, query.query_id)].response_vector) for region in partition.region_ids}
        if bound_behavior is None
        else bound_behavior
    )
    if set(behavior) != set(partition.region_ids) or any(
        type(vector) is not tuple or len(vector) != _GLOBAL_DIMENSION
        for vector in behavior.values()
    ):
        _fail("prebound behavior grid differs from the partition")
    covariance_cache = (
        {} if shared_covariance_cache is None else shared_covariance_cache
    )

    def covariance(blocks: tuple[tuple[str, ...], ...]) -> tuple[tuple[tuple[ExactRational, ...], ...], ExactRational, str]:
        cached = covariance_cache.get(blocks)
        if cached is not None:
            return cached
        n = len(partition.region_ids); matrix = [[Fraction(0) for _ in range(_GLOBAL_DIMENSION)] for _ in range(_GLOBAL_DIMENSION)]
        for block in blocks:
            means = [sum((behavior[region][j] for region in block), Fraction(0)) / len(block) for j in range(_GLOBAL_DIMENSION)]
            for region in block:
                deltas = [behavior[region][j] - means[j] for j in range(_GLOBAL_DIMENSION)]
                for j in range(_GLOBAL_DIMENSION):
                    for k in range(_GLOBAL_DIMENSION): matrix[j][k] += deltas[j] * deltas[k] / n
        exact = tuple(tuple(_from_fraction(cell, "covariance cell") for cell in row) for row in matrix)
        trace = _from_fraction(sum((matrix[j][j] for j in range(_GLOBAL_DIMENSION)), Fraction(0)), "covariance trace")
        digest = _sha([[cell.to_dict() for cell in row] for row in exact])
        result = (exact, trace, digest)
        covariance_cache[blocks] = result
        return result

    _, before_trace, before_digest = covariance(partition.blocks); before_fraction = _fraction(before_trace, "trace", intermediate=True)
    excluded = set(_bounded_tuple(excluded_candidate_bytes, maximum=_MAX_RESPONSE_CELLS, label="excluded candidates"))
    owner = _block_owner(partition); scores: list[LocalityQueryScore] = []
    for left_index, left in enumerate(partition.region_ids):
        for right in partition.region_ids[left_index + 1:]:
            for query in query_values:
                if only_candidate is not None and (
                    left,
                    right,
                    query.query_id,
                ) != only_candidate:
                    continue
                candidate = _candidate_value(family_id, instance_id, left, right, query); candidate_json = _candidate_json(candidate)
                if candidate_json in excluded: continue
                after_blocks = partition.blocks
                left_observation = lookup[(left, query.query_id)]; right_observation = lookup[(right, query.query_id)]
                if owner[left] == owner[right] and left_observation.response_vector != right_observation.response_vector:
                    witness = _find_exact_local_counterexample_core(
                        partition,
                        left_observation,
                        right_observation,
                        reverify=False,
                    )
                    if witness is not None:
                        after_blocks = _apply_exact_counterexample_split_core(
                            partition, witness, reverify=False
                        ).blocks
                _, after_trace, after_digest = covariance(after_blocks)
                gain_fraction = before_fraction - _fraction(after_trace, "after trace", intermediate=True)
                cost = derive_exact_query_cost(query); score_fraction = gain_fraction / cost
                scores.append(LocalityQueryScore(family_id, instance_id, left, right, query, candidate_json, _partition_digest(partition), before_digest, before_trace, after_digest, after_trace, _from_fraction(gain_fraction, "gain"), cost, _from_fraction(score_fraction, "score")))
    scores.sort(key=lambda value: (-_fraction(value.score, "score", intermediate=True), value.derived_cost, value.canonical_candidate_json.encode("utf-8")))
    return tuple(scores)


def rank_locality_queries(
    partition: ProposedNominalPartition,
    queries: Sequence[LocalityQuery],
    observations: Sequence[ExactLocalResponseObservation],
    *,
    excluded_candidate_bytes: Sequence[str] = (),
) -> tuple[LocalityQueryScore, ...]:
    return _rank_locality_queries_core(
        partition,
        queries,
        observations,
        excluded_candidate_bytes=excluded_candidate_bytes,
    )


def _apply_exact_counterexample_split_core(
    partition: ProposedNominalPartition,
    counterexample: ExactLocalCounterexample,
    *,
    reverify: bool,
) -> ProposedNominalPartition:
    if type(partition) is not ProposedNominalPartition or type(counterexample) is not ExactLocalCounterexample: _fail("split requires strict partition and counterexample")
    if reverify:
        recomputed = find_exact_local_counterexample(
            partition,
            counterexample._left_observation,
            counterexample._right_observation,
        )
        if recomputed is None or canonical_contract_bytes(
            recomputed.to_dict()
        ) != canonical_contract_bytes(counterexample.to_dict()):
            _fail("counterexample no longer matches its retained exact observations")
    if partition.observation_frame_id != counterexample.query.observation_frame_id or partition.transition_semantics_id != counterexample.query.transition_semantics_id or partition.action_catalog_digest != counterexample.query.action_catalog_digest:
        _fail("counterexample is not bound to the partition")
    owner = _block_owner(partition); left = counterexample.left_region_id; right = counterexample.right_region_id
    if left not in owner or right not in owner or owner[left] != owner[right]: _fail("counterexample is stale or already separated")
    larger = max((left, right), key=lambda value: value.encode("utf-8")); block_index = owner[left]
    updated: list[tuple[str, ...]] = []
    for index, block in enumerate(partition.blocks):
        if index != block_index: updated.append(block); continue
        remainder = tuple(value for value in block if value != larger)
        if remainder: updated.append(remainder)
        updated.append((larger,))
    blocks = _canonical_blocks(updated); edge = _canonical_pair(left, right)
    edges = tuple(
        sorted(
            set(partition.must_not_link_edges + (edge,)),
            key=lambda row: canonical_contract_bytes(list(row)),
        )
    )
    result = ProposedNominalPartition(partition.observation_frame_id, partition.transition_semantics_id, partition.action_catalog_digest, partition.region_ids, blocks, edges, partition.generation + 1)
    if len(result.blocks) <= len(partition.blocks) or not set(partition.must_not_link_edges).issubset(result.must_not_link_edges): _fail("split is nonmonotone")
    return result


def apply_exact_counterexample_split(
    partition: ProposedNominalPartition,
    counterexample: ExactLocalCounterexample,
) -> ProposedNominalPartition:
    return _apply_exact_counterexample_split_core(
        partition, counterexample, reverify=True
    )


def run_synthetic_locality_cegar(
    regions: Sequence[BeforeLocalRegion], queries: Sequence[LocalityQuery],
    observations: Sequence[ExactLocalResponseObservation], *, action_catalog_digest: str,
    frozen_candidate_order: Sequence[tuple[str, str, str]] | None = None,
) -> LocalityCEGARReport:
    region_count = len(regions); query_count = len(queries); observation_count = len(observations)
    if region_count > _MAX_REGIONS or query_count > _MAX_QUERIES or observation_count > _MAX_RESPONSE_CELLS:
        if region_count < 1 or query_count < 1: _fail("ABSTAIN requires visible frame bindings")
        first_region = regions[0]
        if type(first_region) is not BeforeLocalRegion: _fail("ABSTAIN frame binding is not strict")
        return LocalityCEGARReport("unseen_runtime", "unseen_runtime", first_region.observation_frame_id, first_region.transition_semantics_id, _digest(action_catalog_digest, "action catalogue digest"), None, None, (), "ABSTAIN", "PRE_MATERIALIZATION_CAP_EXCEEDED", 0, 0)
    region_values = _bounded_tuple(
        regions, maximum=_MAX_REGIONS, minimum=1, label="regions"
    )
    query_values = _bounded_tuple(
        queries, maximum=_MAX_QUERIES, minimum=1, label="queries"
    )
    observation_values = _bounded_tuple(
        observations,
        maximum=_MAX_RESPONSE_CELLS,
        minimum=1,
        label="exact observation grid",
    )
    partition = propose_nominal_partition(
        region_values, action_catalog_digest=action_catalog_digest
    )
    initial = partition
    observation_values, lookup, family_id, instance_id = (
        _bind_exact_observation_grid(
            partition,
            query_values,
            observation_values,
            reverify=True,
        )
    )
    bound_grid = (observation_values, lookup, family_id, instance_id)
    bound_behavior = {
        region: tuple(
            _fraction(value, "behavior coordinate")
            for query in query_values
            for value in lookup[(region, query.query_id)].response_vector
        )
        for region in partition.region_ids
    }
    shared_covariance_cache: dict[
        tuple[tuple[str, ...], ...],
        tuple[tuple[tuple[ExactRational, ...], ...], ExactRational, str],
    ] = {}
    excluded: list[str] = []; selected: list[LocalityQueryScore] = []; cumulative_cost = 0
    fixed_order = None if frozen_candidate_order is None else _bounded_tuple(frozen_candidate_order, maximum=_BUDGET, label="frozen candidate order")
    if fixed_order is not None:
        normalized_order: list[tuple[str, str, str]] = []
        for row in fixed_order:
            if type(row) is not tuple or len(row) != 3:
                _fail("frozen candidate order row is not an exact triple")
            left, right = _canonical_pair(_identifier(row[0], "candidate left"), _identifier(row[1], "candidate right"))
            normalized_order.append((left, right, _identifier(row[2], "candidate query_id")))
        if len(set(normalized_order)) != len(normalized_order):
            _fail("frozen candidate order repeats a candidate")
        fixed_order = tuple(normalized_order)
    while len(selected) < _BUDGET:
        if fixed_order is not None and len(selected) >= len(fixed_order):
            break
        wanted = (
            None
            if fixed_order is None
            else fixed_order[len(selected)]
        )
        ranked = _rank_locality_queries_core(
            partition,
            query_values,
            observation_values,
            excluded_candidate_bytes=tuple(excluded),
            only_candidate=wanted,
            reverify_observations=False,
            bound_grid=bound_grid,
            bound_behavior=bound_behavior,
            shared_covariance_cache=shared_covariance_cache,
        )
        if not ranked:
            if fixed_order is not None:
                _fail("frozen candidate order selects an absent or repeated candidate")
            break
        if fixed_order is None:
            choice = ranked[0]
        else:
            matches = [score for score in ranked if (score.left_region_id, score.right_region_id, score.query.query_id) == wanted]
            if len(matches) != 1:
                _fail("frozen candidate order selects an absent or repeated candidate")
            choice = matches[0]
        if choice.canonical_candidate_json in excluded: _fail("candidate observation repeated")
        excluded.append(choice.canonical_candidate_json); selected.append(choice); cumulative_cost += choice.derived_cost
        witness = _find_exact_local_counterexample_core(
            partition,
            lookup[(choice.left_region_id, choice.query.query_id)],
            lookup[(choice.right_region_id, choice.query.query_id)],
            reverify=False,
        )
        if witness is not None:
            partition = _apply_exact_counterexample_split_core(
                partition, witness, reverify=False
            )
    status = "NORMAL_BUDGET_COMPLETE" if len(selected) == _BUDGET else "UNIVERSE_EXHAUSTED_PLATEAU"
    return LocalityCEGARReport(family_id, instance_id, partition.observation_frame_id, partition.transition_semantics_id, partition.action_catalog_digest, initial, partition, tuple(selected), status, "NONE", len(selected), cumulative_cost)


def verify_locality_cegar_report(
    report: LocalityCEGARReport, regions: Sequence[BeforeLocalRegion],
    queries: Sequence[LocalityQuery], observations: Sequence[ExactLocalResponseObservation],
    *, action_catalog_digest: str,
    frozen_candidate_order: Sequence[tuple[str, str, str]] | None = None,
) -> LocalityCEGARReport:
    if type(report) is not LocalityCEGARReport: _fail("report verifier requires a LocalityCEGARReport")
    _clear_verified_observation_source_memo()
    recomputed = run_synthetic_locality_cegar(regions, queries, observations, action_catalog_digest=action_catalog_digest, frozen_candidate_order=frozen_candidate_order)
    if canonical_contract_bytes(report.to_dict()) != canonical_contract_bytes(recomputed.to_dict()):
        _fail("locality report does not match independent semantic replay")
    return recomputed


__all__ = [
    "BeforeLocalRegion", "LocalityFeatureVector", "LocalityQuery",
    "ExactLocalResponseObservation", "ExactLocalCounterexample",
    "ProposedNominalPartition", "LocalityQueryScore", "LocalityCEGARReport",
    "LocalityResultDisposition", "make_before_local_region",
    "extract_before_locality_features", "make_locality_query",
    "derive_exact_query_cost", "make_exact_local_response_observation",
    "find_exact_local_counterexample", "propose_nominal_partition",
    "rank_locality_queries", "apply_exact_counterexample_split",
    "run_synthetic_locality_cegar", "verify_locality_cegar_report",
]
