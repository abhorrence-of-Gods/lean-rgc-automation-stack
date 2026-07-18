"""Frozen public-synthetic U'1.5-L0 locality CEGAR evaluation.

The evaluator is deliberately finite and CPU-only.  It seals train-derived
schedules before it exposes held-out carriers, admits every synthetic snapshot,
and verifies exact partitions directly or through a checked finite-state
isomorphism orbit.  It then computes the registered full exact conditional-
covariance endpoint.  Nothing in this module is hard evidence.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from lean_rgc.odlrq import locality_cegar as _locality_cegar_core
from lean_rgc.odlrq import (
    ActionSymbol,
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactRational,
    extract_before_locality_features,
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
    build_synthetic_finite_snapshot,
    canonical_contract_bytes,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    make_before_local_region,
    make_exact_local_response_observation,
    make_locality_query,
    observation_frame_digest,
    propose_nominal_partition,
    refine_exact_partition,
    run_synthetic_locality_cegar,
    verify_locality_cegar_report,
    verify_exact_partition,
)


__all__ = [
    "build_u15_l0_result_bytes",
    "verify_u15_l0_result_bytes",
]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MATRIX_PATH = (
    _REPO_ROOT / "docs/experiments/inputs/uprime_u15_l0_matrix.json"
)
_MATRIX_BYTES = 73_723
_MATRIX_SHA256 = "5CC24CF1F298A7BE4598C754973B307D78CA211CAC89287444B29E49391BDE5B"
_MATRIX_CANONICAL_SHA256 = (
    "5D78388ED832F4CCD9998DAD70D0F40680E2B5733AC60586339636861126FC06"
)
_MATRIX_ID = "uprime-u15-l0-public-synthetic-locality-cegar-20260717-v1"
_MATRIX_SCHEMA = "lean-rgc-uprime-u15-l0-matrix-v1"
_RESULT_SCHEMA = "lean-rgc-uprime-u15-l0-locality-cegar-result-v1"
_CONTROL_RESULT_SCHEMA = "lean-rgc-uprime-u15-l0-reachability-control-result-v1"
_CANDIDATE_SCHEMA = "lean-rgc-uprime-u15-l0-candidate-v1"
_QUERY_SCHEMA = "lean-rgc-uprime-u15-l0-query-v1"
_RESULT_WIRE_CAP = 1_048_576
_JSON_DEPTH_CAP = 16
_JSON_ARRAY_CAP = 256
_JSON_KEY_CAP = 64
_IDENTIFIER_BYTES_CAP = 128
_INPUT_RATIONAL_BITS = 256
_INTERMEDIATE_RATIONAL_BITS = 4096
_BEHAVIOR_DIMENSION = 16
_BUDGET = 16
_CHECKPOINTS = (0, 1, 2, 4, 8, 16)
_FAMILY_IDS = (
    "separator_rank0",
    "separator_rank1",
    "separator_rank2",
    "delayed_effect",
    "ghost_memory",
    "noncommutativity",
    "bisimilar",
    "relabel",
)
_ACTION_IDS = (
    "unit_cpu_survivor_u15_l0_a",
    "unit_cpu_survivor_u15_l0_b",
    "unit_cpu_survivor_u15_l0_ghost_store",
    "unit_cpu_survivor_u15_l0_reveal",
    "unit_cpu_survivor_u15_l0_close",
)
_QUERY_IDS = (
    "q_a",
    "q_b",
    "q_ghost_store",
    "q_reveal",
    "q_ghost_store_reveal",
    "q_a_b",
    "q_b_a",
    "q_close",
)
_ZERO = ExactRational(0)
_STATE_ID_PREFIX = "unit_cpu_survivor_u15_l0_"
_OPEN_TOKEN = object()
_SCHEDULE_TOKEN = object()
_P0_TOKEN = object()
_CONTROL_TOKEN = object()
_VERIFIED_INSTANCE_CACHE: dict[str, "_VerifiedInstance"] = {}
_CONTROL_ORBIT_CACHE: dict[tuple[str, str], "_VerifiedControlOrbit"] = {}
_CONTROL_QUERY_TEMPLATE_BYTES: dict[str, bytes] = {}
_CONTROL_QUERY_TEMPLATE_ENVIRONMENTS: list[str] = []
_CONTROL_EXPECTED_VOCABULARIES: list[ResponseVocabularyId] = []
_CONTROL_EXPECTED_SEMANTICS: list[Any] = []
_CONTROL_QUERY_BINDING_CACHE: dict[
    tuple[str, str], tuple[tuple[str, str], ...]
] = {}
_RECOMPUTE_CERTIFICATE_WITNESSES: dict[
    str, tuple["_InstanceSpec", Any]
] = {}
_PUBLIC_REPORT_CACHE: dict[str, Any] = {}


class _RawPairs(list):
    """Retain duplicate object keys until the strict conversion pass."""


def _reject_number(token: str) -> Any:
    raise StrictContractError(f"non-integer JSON number is forbidden: {token[:32]}")


def _parse_integer(token: str) -> int:
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise StrictContractError("invalid JSON integer") from exc
    if token == "-0" or str(value) != token or not (-(2**63) <= value < 2**63):
        raise StrictContractError("JSON integer is not canonical signed-64")
    return value


def _strict_json_object(
    raw: bytes, where: str, *, require_canonical: bool
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > _RESULT_WIRE_CAP:
        raise StrictContractError(f"{where} is missing or over the one-MiB cap")
    try:
        text = raw.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_RawPairs,
            parse_int=_parse_integer,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictContractError(f"{where} is not strict UTF-8 JSON") from exc

    def convert(value: Any, depth: int) -> Any:
        if depth > _JSON_DEPTH_CAP:
            raise StrictContractError(f"{where} exceeds the JSON depth cap")
        if type(value) is _RawPairs:
            if len(value) > _JSON_KEY_CAP:
                raise StrictContractError(f"{where} object exceeds the key cap")
            result: dict[str, Any] = {}
            for key, item in value:
                if type(key) is not str or key in result:
                    raise StrictContractError(f"{where} has a duplicate or invalid key")
                key.encode("utf-8", errors="strict")
                result[key] = convert(item, depth + 1)
            return result
        if type(value) is list:
            if len(value) > _JSON_ARRAY_CAP:
                raise StrictContractError(f"{where} array exceeds the cap")
            return [convert(item, depth + 1) for item in value]
        if type(value) is str:
            value.encode("utf-8", errors="strict")
            return value
        if value is None or type(value) is bool or type(value) is int:
            return value
        raise StrictContractError(f"{where} contains a forbidden scalar")

    result = convert(parsed, 0)
    if type(result) is not dict:
        raise StrictContractError(f"{where} root must be an object")
    if require_canonical and canonical_contract_bytes(result) != raw:
        raise StrictContractError(f"{where} is not canonical JSON")
    return result


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _sha(value: Any) -> str:
    return _sha_bytes(canonical_contract_bytes(value))


def _identifier(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty string")
    try:
        size = len(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} is not strict UTF-8") from exc
    if size > _IDENTIFIER_BYTES_CAP:
        raise StrictContractError(f"{where} exceeds the identifier cap")
    return value


def _exact_fields(value: Any, names: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != names:
        raise StrictContractError(f"{where} fields differ from the frozen schema")
    return value


def _fraction(value: ExactRational) -> Fraction:
    if type(value) is not ExactRational:
        raise StrictContractError("an exact rational capability is required")
    return Fraction(value.numerator, value.denominator)


def _exact(value: Fraction | int) -> ExactRational:
    current = value if type(value) is Fraction else Fraction(value)
    if (
        abs(current.numerator).bit_length() > _INTERMEDIATE_RATIONAL_BITS
        or current.denominator.bit_length() > _INTERMEDIATE_RATIONAL_BITS
    ):
        raise StrictContractError("intermediate rational exceeds the frozen cap")
    return ExactRational(current.numerator, current.denominator)


def _rational_row(value: Any, where: str) -> tuple[ExactRational, ExactRational]:
    if type(value) is not list or len(value) != 2:
        raise StrictContractError(f"{where} must have two coordinates")
    result = tuple(ExactRational.from_dict(row) for row in value)
    for coordinate in result:
        if (
            abs(coordinate.numerator).bit_length() > _INPUT_RATIONAL_BITS
            or coordinate.denominator.bit_length() > _INPUT_RATIONAL_BITS
        ):
            raise StrictContractError(f"{where} exceeds the input rational cap")
    return result  # type: ignore[return-value]


@dataclass(frozen=True)
class _QuerySpec:
    query_id: str
    action_ids: tuple[str, ...]
    full_wire_bytes: bytes
    cost: int

    @property
    def full_wire(self) -> dict[str, Any]:
        return _strict_json_object(
            self.full_wire_bytes, "query wire", require_canonical=True
        )


@dataclass(frozen=True)
class _InstanceSpec:
    family_id: str
    instance_id: str
    stratum: str
    region_ids: tuple[str, ...]
    initial_partition: tuple[tuple[str, ...], ...]
    exact_partition: tuple[tuple[str, ...], ...]
    response_rows: tuple[
        tuple[str, str, tuple[ExactRational, ExactRational]], ...
    ]
    seeds: tuple[tuple[str, str, str], ...]

    def response(
        self, region_id: str, query_id: str
    ) -> tuple[ExactRational, ExactRational]:
        for region, query, value in self.response_rows:
            if region == region_id and query == query_id:
                return value
        raise StrictContractError("response lookup is outside the complete table")


@dataclass(frozen=True)
class _FamilySpec:
    family_id: str
    region_rows: tuple[bytes, ...]
    initial_partition: tuple[tuple[str, ...], ...]
    exact_partition: tuple[tuple[str, ...], ...]
    train: _InstanceSpec
    heldout_bytes: tuple[bytes, bytes]


@dataclass(frozen=True)
class _FrozenMatrix:
    canonical_sha256: str
    actions: tuple[ActionSymbol, ...]
    synthetic_actions: tuple[SyntheticAction, ...]
    queries: tuple[_QuerySpec, ...]
    template_rows: tuple[tuple[str, bytes], ...]
    families: tuple[_FamilySpec, ...]
    control_bytes: bytes


@dataclass(frozen=True)
class _TrainCarrier:
    family_id: str
    instance: _InstanceSpec
    queries: tuple[_QuerySpec, ...]


@dataclass(frozen=True)
class _ScheduleBarrier:
    digest_map_bytes: bytes
    barrier_sha256: str
    _token: object

    def __post_init__(self) -> None:
        if self._token is not _SCHEDULE_TOKEN:
            raise StrictContractError("schedule barrier requires all frozen schedules")


@dataclass(frozen=True)
class _OpenedHeldout:
    instances: tuple[_InstanceSpec, ...]
    _token: object

    def __post_init__(self) -> None:
        if self._token is not _OPEN_TOKEN:
            raise StrictContractError("held-out carrier requires the schedule barrier")


@dataclass(frozen=True)
class _VerifiedInstance:
    spec: _InstanceSpec
    admitted: Any
    verified: Any
    terminal_blocks: tuple[tuple[str, str, int], ...]
    snapshot_sha256: str
    certificate_sha256: str

    def terminal_block(self, region_id: str, query_id: str) -> int:
        for region, query, block in self.terminal_blocks:
            if region == region_id and query == query_id:
                return block
        raise StrictContractError("terminal projection lookup failed")


@dataclass(frozen=True)
class _AdmittedControlMember:
    spec: _InstanceSpec
    admitted: AdmittedExactFiniteSnapshot

    def __post_init__(self) -> None:
        if (
            type(self.spec) is not _InstanceSpec
            or type(self.admitted) is not AdmittedExactFiniteSnapshot
        ):
            raise StrictContractError("control orbit member is not strictly admitted")


@dataclass(frozen=True)
class _VerifiedControlOrbit:
    role: str
    members: tuple[_AdmittedControlMember, ...]
    representative: _VerifiedInstance
    isomorphism_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.role not in {"train", "heldout_alpha", "heldout_beta"}
            or type(self.members) is not tuple
            or len(self.members) != 8
            or not all(type(row) is _AdmittedControlMember for row in self.members)
            or type(self.representative) is not _VerifiedInstance
            or self.members[0].spec != self.representative.spec
            or self.members[0].admitted != self.representative.admitted
            or type(self.isomorphism_sha256s) is not tuple
            or len(self.isomorphism_sha256s) != 8
            or not all(re.fullmatch(r"[0-9A-F]{64}", value) for value in self.isomorphism_sha256s)
        ):
            raise StrictContractError("verified control orbit is incomplete")


@dataclass(frozen=True)
class _Candidate:
    family_id: str
    instance_id: str
    left_region_id: str
    right_region_id: str
    query: _QuerySpec
    wire_bytes: bytes

    @property
    def wire(self) -> dict[str, Any]:
        return _strict_json_object(
            self.wire_bytes, "candidate wire", require_canonical=True
        )


@dataclass(frozen=True)
class _Schedule:
    family_id: str
    method_id: str
    candidates: tuple[_Candidate, ...]
    sha256: str


@dataclass(frozen=True)
class _Covariance:
    cells: tuple[tuple[Fraction, ...], ...]
    sha256: str
    trace: Fraction


@dataclass(frozen=True)
class _P0Barrier:
    rows: tuple[tuple[str, str, str, Fraction], ...]
    sha256: str
    _token: object

    def __post_init__(self) -> None:
        if self._token is not _P0_TOKEN or len(self.rows) != 16:
            raise StrictContractError("global P0 barrier is incomplete")


@dataclass(frozen=True)
class _CoreBinding:
    regions: tuple[Any, ...]
    queries: tuple[Any, ...]
    observations: tuple[Any, ...]
    action_catalog_digest: str


class _PrerequisiteBlocked(StrictContractError):
    pass


def _partition(value: Any, region_ids: tuple[str, ...], where: str) -> tuple[tuple[str, ...], ...]:
    if type(value) is not list or not value:
        raise StrictContractError(f"{where} is not a nonempty partition")
    blocks: list[tuple[str, ...]] = []
    members: list[str] = []
    for row in value:
        if type(row) is not list or not row:
            raise StrictContractError(f"{where} has an empty block")
        block = tuple(
            sorted(
                (_identifier(item, f"{where} member") for item in row),
                key=lambda item: item.encode("utf-8"),
            )
        )
        blocks.append(block)
        members.extend(block)
    if len(members) != len(set(members)) or set(members) != set(region_ids):
        raise StrictContractError(f"{where} does not partition all regions exactly")
    return tuple(
        sorted(blocks, key=lambda block: canonical_contract_bytes(list(block)))
    )


def _query_wire(
    row: dict[str, Any], actions: dict[str, ActionSymbol], context: dict[str, Any]
) -> dict[str, Any]:
    _exact_fields(
        row,
        {"query_id", "action_word", "closing_context_id", "derived_cost"},
        "query row",
    )
    query_id = _identifier(row.get("query_id"), "query_id")
    action_ids = row.get("action_word")
    if type(action_ids) is not list or not (1 <= len(action_ids) <= 3):
        raise StrictContractError("query action word is outside the depth cap")
    action_word = tuple(_identifier(item, "query action_id") for item in action_ids)
    if any(action_id not in actions for action_id in action_word):
        raise StrictContractError("query action is outside the catalogue")
    if row.get("closing_context_id") != context["closing_context_id"]:
        raise StrictContractError("query closing context is unknown")
    derived = _exact_fields(
        row.get("derived_cost"),
        {"response_cells", "word_work", "total"},
        "derived query cost",
    )
    expected_cost = 2 * (len(action_word) + len(context["ordered_action_ids"]) + 2)
    if derived != {
        "response_cells": 4,
        "word_work": 2 * (len(action_word) + len(context["ordered_action_ids"])),
        "total": expected_cost,
    }:
        raise StrictContractError("query cost is not mechanically derived")
    # `full_query_row` is the complete frozen catalogue row.  In particular,
    # it is not the frame-expanded public LocalityQuery wire: baseline order
    # is defined over these exact bytes by the registered matrix.
    return {
        "query_id": query_id,
        "action_word": list(action_word),
        "closing_context_id": context["closing_context_id"],
        "derived_cost": derived,
    }


def _parse_instance(
    family_id: str,
    region_ids: tuple[str, ...],
    initial_partition: tuple[tuple[str, ...], ...],
    exact_partition: tuple[tuple[str, ...], ...],
    value: dict[str, Any],
) -> _InstanceSpec:
    _exact_fields(
        value,
        {
            "instance_id",
            "stratum",
            "response_access",
            "full_response_table",
            "seeded_counterexample_pairs",
        },
        "instance",
    )
    instance_id = _identifier(value["instance_id"], "instance_id")
    stratum = value["stratum"]
    if stratum not in {"train", "heldout"}:
        raise StrictContractError("instance stratum is invalid")
    table = _exact_fields(
        value["full_response_table"],
        {"default_response_vector", "overrides"},
        "response table",
    )
    default = _rational_row(table["default_response_vector"], "default response")
    overrides = table["overrides"]
    if type(overrides) is not list:
        raise StrictContractError("response overrides must be an array")
    override_map: dict[tuple[str, str], tuple[ExactRational, ExactRational]] = {}
    for row in overrides:
        _exact_fields(row, {"region_id", "query_id", "response_vector"}, "override")
        key = (
            _identifier(row["region_id"], "override region_id"),
            _identifier(row["query_id"], "override query_id"),
        )
        if key in override_map or key[0] not in region_ids or key[1] not in _QUERY_IDS:
            raise StrictContractError("response override is duplicate or outside the table")
        override_map[key] = _rational_row(row["response_vector"], "response override")
    response_rows = tuple(
        (region_id, query_id, override_map.get((region_id, query_id), default))
        for region_id in region_ids
        for query_id in _QUERY_IDS
    )
    if len(response_rows) > 256:
        raise StrictContractError("oracle response-cell cap is exceeded")
    seeds_raw = value["seeded_counterexample_pairs"]
    if type(seeds_raw) is not list:
        raise StrictContractError("seeded pairs must be an array")
    seeds: list[tuple[str, str, str]] = []
    for row in seeds_raw:
        _exact_fields(
            row, {"left_region_id", "right_region_id", "query_id"}, "seeded pair"
        )
        left = _identifier(row["left_region_id"], "seed left")
        right = _identifier(row["right_region_id"], "seed right")
        query = _identifier(row["query_id"], "seed query")
        if left not in region_ids or right not in region_ids or query not in _QUERY_IDS:
            raise StrictContractError("seeded pair is outside the instance")
        if (left, right, query) in seeds:
            raise StrictContractError("seeded pair is duplicated")
        seeds.append((left, right, query))
    return _InstanceSpec(
        family_id,
        instance_id,
        stratum,
        region_ids,
        initial_partition,
        exact_partition,
        response_rows,
        tuple(seeds),
    )


def _action_symbol(row: dict[str, Any]) -> ActionSymbol:
    symbol = ActionSymbol.from_dict(row)
    if symbol.to_dict() != row:
        raise StrictContractError("action symbol changed under strict roundtrip")
    if not symbol.action_id.startswith("unit_cpu_survivor_u15_l0_"):
        raise StrictContractError("action is outside the admitted L0 prefix")
    return symbol


def _validate_matrix_constants(source: dict[str, Any]) -> None:
    if (
        source.get("schema_version") != _MATRIX_SCHEMA
        or source.get("matrix_id") != _MATRIX_ID
        or source.get("evidence_scope") != "synthetic_development"
        or source.get("evidence_tier") != "NOMINAL_DIAGNOSTIC_ONLY"
    ):
        raise StrictContractError("frozen matrix identity or tier changed")
    caps = source.get("caps")
    required_caps = {
        "max_families": 8,
        "max_instances_per_family": 3,
        "max_regions": 16,
        "max_region_nodes": 12,
        "max_region_edges": 24,
        "max_response_coordinates": 8,
        "max_identifier_utf8_bytes": 128,
        "max_input_exact_rational_bits": 256,
        "max_intermediate_exact_rational_bits": 4096,
        "max_object_wire_bytes": 1_048_576,
        "max_json_depth": 16,
        "max_json_array_length": 256,
        "max_json_object_keys": 64,
        "exact_treewidth_cap": 8,
        "max_query_count": 16,
        "max_action_word_depth": 3,
        "max_oracle_response_cells": 256,
        "max_snapshot_totalized_states": 128,
        "max_snapshot_transition_rows": 2048,
        "global_behavior_dimension": 16,
        "cap_check_order": "reject_or_abstain_before_graph_snapshot_or_candidate_materialization",
        "stage_wall_seconds": 120,
    }
    if caps != required_caps:
        raise StrictContractError("frozen matrix caps changed")
    response = source.get("response_space")
    if (
        type(response) is not dict
        or response.get("coordinate_ids") != ["observable_delta", "return_memory"]
        or response.get("coordinate_count") != 2
    ):
        raise StrictContractError("response vocabulary changed")
    evaluation = source.get("evaluation")
    if (
        type(evaluation) is not dict
        or tuple(evaluation.get("fixed_denominator_family_ids", ())) != _FAMILY_IDS
        or evaluation.get("heldout_instance_count") != 16
        or evaluation.get("reporting_checkpoints") != list(_CHECKPOINTS)
    ):
        raise StrictContractError("evaluation denominator or checkpoints changed")
    dispositions = source.get("allowed_dispositions")
    if dispositions != [
        "L0_SYNTHETIC_CEGAR_GAIN_OBSERVED",
        "L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN",
        "L0_SYNTHETIC_CEGAR_DEGRADED",
        "L0_PREREQUISITE_BLOCKED",
        "L0_EXECUTION_FAILED",
    ]:
        raise StrictContractError("allowed disposition sum changed")


def _parse_matrix_bytes(raw: bytes, *, control_token: object | None = None) -> _FrozenMatrix:
    primary = control_token is None
    if primary and (len(raw) != _MATRIX_BYTES or _sha_bytes(raw) != _MATRIX_SHA256):
        raise StrictContractError("frozen matrix raw identity changed")
    if not primary and control_token is not _CONTROL_TOKEN:
        raise StrictContractError("test-control matrix authority is missing")
    source = _strict_json_object(raw, "L0 matrix", require_canonical=not primary)
    if primary and _sha(source) != _MATRIX_CANONICAL_SHA256:
        raise StrictContractError("frozen matrix canonical identity changed")
    _validate_matrix_constants(source)

    action_rows = source.get("action_catalog")
    if type(action_rows) is not list or len(action_rows) != 5:
        raise StrictContractError("action catalogue must have five rows")
    actions = tuple(_action_symbol(row) for row in action_rows)
    if tuple(action.action_id for action in actions) != _ACTION_IDS:
        raise StrictContractError("action catalogue order or membership changed")
    action_map = {action.action_id: action for action in actions}
    synthetic_actions = tuple(
        SyntheticAction(
            action.action_id, CanonicalPayload.from_value(action.to_dict())
        )
        for action in actions
    )
    if any(
        action.action_id
        != ActionSymbol.from_dict(
            _strict_json_object(
                synthetic.payload.canonical_json.encode("utf-8"),
                "action payload",
                require_canonical=True,
            )
        ).action_id
        for action, synthetic in zip(actions, synthetic_actions, strict=True)
    ):
        raise StrictContractError("outer and inner action IDs disagree")

    contexts = source.get("closing_context_catalog")
    if type(contexts) is not list or len(contexts) != 1:
        raise StrictContractError("closing-context catalogue changed")
    context = _exact_fields(
        contexts[0],
        {"closing_context_id", "ordered_action_ids", "response_coordinate_ids"},
        "closing context",
    )
    if context != {
        "closing_context_id": "observe_two_coordinate_response",
        "ordered_action_ids": [],
        "response_coordinate_ids": ["observable_delta", "return_memory"],
    }:
        raise StrictContractError("closing-context semantics changed")
    query_rows = source.get("query_catalog")
    if type(query_rows) is not list or len(query_rows) != 8:
        raise StrictContractError("query catalogue must have eight rows")
    queries: list[_QuerySpec] = []
    for row in query_rows:
        query_wire = _query_wire(row, action_map, context)
        action_ids = tuple(query_wire["action_word"])
        queries.append(
            _QuerySpec(
                query_wire["query_id"],
                action_ids,
                canonical_contract_bytes(query_wire),
                query_wire["derived_cost"]["total"],
            )
        )
    if tuple(query.query_id for query in queries) != _QUERY_IDS:
        raise StrictContractError("query catalogue order or membership changed")

    template_rows = source.get("before_graph_templates")
    if type(template_rows) is not list or len(template_rows) != 6:
        raise StrictContractError("before-graph template catalogue changed")
    templates: list[tuple[str, bytes]] = []
    for row in template_rows:
        template_id = _identifier(row.get("template_id"), "template_id")
        if template_id in {name for name, _raw in templates}:
            raise StrictContractError("duplicate graph template")
        templates.append((template_id, canonical_contract_bytes(row)))

    family_rows = source.get("families")
    if type(family_rows) is not list or len(family_rows) != 8:
        raise StrictContractError("family count changed")
    families: list[_FamilySpec] = []
    for family_row in family_rows:
        family_id = _identifier(family_row.get("family_id"), "family_id")
        region_rows = family_row.get("regions")
        if type(region_rows) is not list or not (1 <= len(region_rows) <= 16):
            raise StrictContractError("family regions are outside the cap")
        region_ids = tuple(
            _identifier(row.get("region_id"), "region_id") for row in region_rows
        )
        if len(region_ids) != len(set(region_ids)):
            raise StrictContractError("family has duplicate region IDs")
        initial = _partition(
            family_row.get("initial_partition"), region_ids, "initial partition"
        )
        exact_partition = _partition(
            family_row.get("exact_partition"), region_ids, "exact partition"
        )
        instance_rows = family_row.get("instances")
        if type(instance_rows) is not list or len(instance_rows) != 3:
            raise StrictContractError("family requires one train and two held-out rows")
        parsed_instances = tuple(
            _parse_instance(
                family_id,
                region_ids,
                initial,
                exact_partition,
                instance_row,
            )
            for instance_row in instance_rows
        )
        if (
            parsed_instances[0].stratum != "train"
            or parsed_instances[1].stratum != "heldout"
            or parsed_instances[2].stratum != "heldout"
            or tuple(instance.instance_id for instance in parsed_instances)
            != (
                f"{family_id}__train",
                f"{family_id}__heldout_alpha",
                f"{family_id}__heldout_beta",
            )
        ):
            raise StrictContractError("family instance roles/order changed")
        heldout_bytes = tuple(
            canonical_contract_bytes(instance_row)
            for instance_row in instance_rows[1:]
        )
        families.append(
            _FamilySpec(
                family_id,
                tuple(canonical_contract_bytes(row) for row in region_rows),
                initial,
                exact_partition,
                parsed_instances[0],
                heldout_bytes,  # type: ignore[arg-type]
            )
        )
    if tuple(family.family_id for family in families) != _FAMILY_IDS:
        raise StrictContractError("family order or membership changed")
    return _FrozenMatrix(
        _sha(source),
        actions,
        synthetic_actions,
        tuple(queries),
        tuple(templates),
        tuple(families),
        canonical_contract_bytes(
            {
                "reachability_control_fixture": copy.deepcopy(
                    source["reachability_control_fixture"]
                ),
                "disposition_reachability_controls": copy.deepcopy(
                    source["disposition_reachability_controls"]
                ),
            }
        ),
    )


@lru_cache(maxsize=1)
def _load_frozen_matrix() -> _FrozenMatrix:
    return _parse_matrix_bytes(_MATRIX_PATH.read_bytes())


def _train_carriers(matrix: _FrozenMatrix) -> tuple[_TrainCarrier, ...]:
    if type(matrix) is not _FrozenMatrix:
        raise StrictContractError("train extraction requires the frozen matrix")
    return tuple(
        _TrainCarrier(family.family_id, family.train, matrix.queries)
        for family in matrix.families
    )


def _candidate(
    family_id: str,
    instance_id: str,
    left: str,
    right: str,
    query: _QuerySpec,
) -> _Candidate:
    if left.encode("utf-8") > right.encode("utf-8"):
        left, right = right, left
    wire = {
        "schema_version": _CANDIDATE_SCHEMA,
        "family_id": family_id,
        "instance_id": instance_id,
        "left_region_id": left,
        "right_region_id": right,
        "full_query_row": query.full_wire,
    }
    raw = canonical_contract_bytes(wire)
    return _Candidate(family_id, instance_id, left, right, query, raw)


def _candidate_universe(carrier: _TrainCarrier) -> tuple[_Candidate, ...]:
    if type(carrier) is not _TrainCarrier:
        raise StrictContractError("ranker accepts only a train carrier")
    region_ids = carrier.instance.region_ids
    candidates = tuple(
        _candidate(
            carrier.family_id,
            carrier.instance.instance_id,
            region_ids[left],
            region_ids[right],
            query,
        )
        for left in range(len(region_ids))
        for right in range(left + 1, len(region_ids))
        for query in carrier.queries
    )
    if len(candidates) != len({candidate.wire_bytes for candidate in candidates}):
        raise StrictContractError("candidate universe is not unique")
    return candidates


def _state_id(
    spec: _InstanceSpec, region_id: str, query_id: str, suffix: str
) -> str:
    try:
        region_index = spec.region_ids.index(region_id)
        query_index = _QUERY_IDS.index(query_id)
    except ValueError as exc:
        raise StrictContractError("state ID requested outside its frozen carrier") from exc
    if suffix == "source":
        local_code = "S"
    elif suffix == "terminal":
        local_code = "T"
    elif suffix.isdecimal() and int(suffix) > 0:
        local_code = "I" + suffix
    else:
        raise StrictContractError("state ID suffix is outside the frozen topology")
    return _STATE_ID_PREFIX + f"{region_index}{query_index}{local_code}"


def _terminal_id(spec: _InstanceSpec, region_id: str, query_id: str) -> str:
    return _state_id(spec, region_id, query_id, "terminal")


def _snapshot_counts(spec: _InstanceSpec, queries: tuple[_QuerySpec, ...]) -> tuple[int, int]:
    intermediate_per_region = sum(len(query.action_ids) - 1 for query in queries)
    states = len(spec.region_ids) * (2 * len(queries) + intermediate_per_region) + 2
    return states, states * len(_ACTION_IDS)


def _frozen_runtime_ids(
    matrix: _FrozenMatrix,
) -> tuple[ResponseVocabularyId, Any]:
    if not _CONTROL_EXPECTED_VOCABULARIES:
        _CONTROL_EXPECTED_VOCABULARIES.append(
            ResponseVocabularyId.from_coordinate_names(
                ("observable_delta", "return_memory")
            )
        )
    vocabulary = _CONTROL_EXPECTED_VOCABULARIES[0]
    if not _CONTROL_EXPECTED_SEMANTICS:
        _CONTROL_EXPECTED_SEMANTICS.append(
            make_synthetic_transition_semantics_id(
                actions=matrix.synthetic_actions,
                response_vocabulary_id=vocabulary,
            )
        )
    semantics = _CONTROL_EXPECTED_SEMANTICS[0]
    return vocabulary, semantics


def _query_sha256s_for_frame(
    matrix: _FrozenMatrix,
    frame: Any,
    semantics: Any,
    vocabulary: ResponseVocabularyId,
) -> dict[str, str]:
    if not _CONTROL_QUERY_TEMPLATE_BYTES:
        for query in matrix.queries:
            wire = canonical_contract_bytes(
                make_locality_query(
                    query_id=query.query_id,
                    observation_frame_id=frame,
                    transition_semantics_id=semantics,
                    response_vocabulary_id=vocabulary,
                    action_catalog=matrix.synthetic_actions,
                    action_word_ids=query.action_ids,
                    closing_context_id="observe_two_coordinate_response",
                    closing_action_ids=(),
                    response_coordinate_ids=(
                        "observable_delta",
                        "return_memory",
                    ),
                ).to_dict()
            )
            _CONTROL_QUERY_TEMPLATE_BYTES[query.query_id] = wire
        _CONTROL_QUERY_TEMPLATE_ENVIRONMENTS.append(
            frame.environment_content_digest
        )
    if len(_CONTROL_QUERY_TEMPLATE_ENVIRONMENTS) != 1:
        raise StrictContractError("query template environment is ambiguous")
    template_environment = _CONTROL_QUERY_TEMPLATE_ENVIRONMENTS[0].encode("ascii")
    target_environment = frame.environment_content_digest.encode("ascii")
    result: dict[str, str] = {}
    for query in matrix.queries:
        wire = _CONTROL_QUERY_TEMPLATE_BYTES[query.query_id]
        if wire.count(template_environment) != 3:
            raise StrictContractError("query template frame multiplicity changed")
        result[query.query_id] = hashlib.sha256(
            wire.replace(template_environment, target_environment)
        ).hexdigest().upper()
    return result


def _require_control_spec_isomorphism(
    source: _InstanceSpec, target: _InstanceSpec
) -> None:
    """Prove that two strict control specs differ only in carrier identifiers."""

    if (
        source.stratum != target.stratum
        or source.region_ids != target.region_ids
        or source.initial_partition != target.initial_partition
        or source.exact_partition != target.exact_partition
        or source.response_rows != target.response_rows
        or source.seeds != target.seeds
    ):
        raise StrictContractError("control certificate transport crossed an isomorphism class")


def _control_snapshot_isomorphism_sha256(
    matrix: _FrozenMatrix,
    source: _AdmittedControlMember,
    target: _AdmittedControlMember,
) -> str:
    """Check a total response-labelled transition isomorphism between controls."""

    _require_control_spec_isomorphism(source.spec, target.spec)
    source_snapshot = source.admitted.snapshot
    target_snapshot = target.admitted.snapshot
    def expected_query_sha256s(
        member: _AdmittedControlMember,
    ) -> dict[str, str]:
        snapshot = member.admitted.snapshot
        cache_key = (
            member.spec.instance_id,
            member.admitted.admission_report.snapshot_sha256,
        )
        cached = _CONTROL_QUERY_BINDING_CACHE.get(cache_key)
        if cached is not None:
            return dict(cached)
        vocabulary, semantics = _frozen_runtime_ids(matrix)
        environment = _sha_bytes(
            f"u15-l0-environment-v1|{_MATRIX_ID}|{member.spec.instance_id}".encode(
                "utf-8"
            )
        )
        frame = make_synthetic_observation_frame_id(
            environment_digest=environment,
            response_vocabulary_id=vocabulary,
        )
        if (
            snapshot.observation_frame_id != frame
            or snapshot.response_vocabulary_id != vocabulary
            or snapshot.transition_semantics_id != semantics
        ):
            raise StrictContractError(
                "control orbit environment/frame binding changed"
            )
        result = _query_sha256s_for_frame(
            matrix, frame, semantics, vocabulary
        )
        _CONTROL_QUERY_BINDING_CACHE[cache_key] = tuple(result.items())
        return result

    expected_query_digests = {
        source.spec.instance_id: expected_query_sha256s(source),
        target.spec.instance_id: expected_query_sha256s(target),
    }

    def rename(state_id: str) -> str:
        if not state_id.startswith(_STATE_ID_PREFIX):
            raise StrictContractError("control isomorphism source ID is out of carrier")
        return state_id

    source_states = {state.state_id: state for state in source_snapshot.states}
    target_states = {state.state_id: state for state in target_snapshot.states}
    if (
        len(source_states) != len(source_snapshot.states)
        or len(target_states) != len(target_snapshot.states)
        or {rename(state_id) for state_id in source_states} != set(target_states)
        or source_snapshot.actions != target_snapshot.actions
        or source_snapshot.response_vocabulary_id.coordinate_names
        != target_snapshot.response_vocabulary_id.coordinate_names
    ):
        raise StrictContractError("control orbit is not a total state/action bijection")

    for source_id, source_state in source_states.items():
        target_id = rename(source_id)
        target_state = target_states[target_id]
        try:
            source_payload = json.loads(source_state.payload.canonical_json)
            target_payload = json.loads(target_state.payload.canonical_json)
        except json.JSONDecodeError as exc:
            raise StrictContractError("control orbit payload is not JSON") from exc
        if type(source_payload) is not dict or type(target_payload) is not dict:
            raise StrictContractError("control orbit payload is not an object")
        for payload, instance_id in (
            (source_payload, source.spec.instance_id),
            (target_payload, target.spec.instance_id),
        ):
            if payload.get("instance_id") != instance_id:
                raise StrictContractError("control orbit payload instance binding changed")
            payload["instance_id"] = "<INSTANCE>"
            query_sha256 = payload.pop("query_sha256", None)
            kind = payload.get("kind")
            if kind in {"u15_l0_source", "u15_l0_terminal"}:
                query_id = payload.get("query_id")
                if (
                    query_id not in expected_query_digests[instance_id]
                    or query_sha256
                    != expected_query_digests[instance_id][query_id]
                ):
                    raise StrictContractError(
                        "control orbit full query binding changed"
                    )
            elif query_sha256 is not None:
                raise StrictContractError(
                    "control orbit query digest appears on an unbound state"
                )
        if (
            source_payload != target_payload
            or source_state.totalized_kind != target_state.totalized_kind
            or source_state.response_coordinates != target_state.response_coordinates
        ):
            raise StrictContractError("control orbit changes payload, status, or response")

    source_rows = {
        (rename(row.source_state_id), row.action_id, rename(row.target_state_id))
        for row in source_snapshot.transitions
    }
    target_rows = {
        (row.source_state_id, row.action_id, row.target_state_id)
        for row in target_snapshot.transitions
    }
    if (
        len(source_rows) != len(source_snapshot.transitions)
        or len(target_rows) != len(target_snapshot.transitions)
        or source_rows != target_rows
        or tuple(rename(state_id) for state_id in source_snapshot.seed_state_ids)
        != target_snapshot.seed_state_ids
    ):
        raise StrictContractError("control orbit changes transition or seed semantics")
    return _sha_bytes(
        (
            "u15-l0-control-response-labelled-transition-isomorphism-v1|"
            + source.admitted.admission_report.snapshot_sha256
            + "|"
            + target.admitted.admission_report.snapshot_sha256
        ).encode("ascii")
    )


def _verified_control_orbit(
    matrix: _FrozenMatrix,
    specs: tuple[_InstanceSpec, ...],
    *,
    role: str,
    opened: _OpenedHeldout | None,
    max_transition_rows: int,
) -> _VerifiedControlOrbit:
    if len(specs) != 8 or any(
        spec.instance_id.rsplit("__", 1)[-1] != role for spec in specs
    ):
        raise StrictContractError("control orbit does not contain eight frozen roles")
    cache_key = (specs[0].instance_id.split("__reachability_control_", 1)[0], role)
    cached = _CONTROL_ORBIT_CACHE.get(cache_key)
    if cached is not None:
        if tuple(member.spec for member in cached.members) != specs:
            raise StrictContractError("control orbit cache binding changed")
        if opened is not None and any(spec not in opened.instances for spec in specs):
            raise StrictContractError("cached control orbit preceded its heldout barrier")
        return cached
    representative = _materialize_verified_instance(
        matrix,
        specs[0],
        opened=opened,
        max_transition_rows=max_transition_rows,
    )
    members = (
        _AdmittedControlMember(specs[0], representative.admitted),
    ) + tuple(
        _AdmittedControlMember(
            spec,
            _admit_control_instance(
                matrix,
                spec,
                opened=opened,
                max_transition_rows=max_transition_rows,
            ),
        )
        for spec in specs[1:]
    )
    source = members[0]
    witnesses = tuple(
        _control_snapshot_isomorphism_sha256(matrix, source, member)
        for member in members
    )
    result = _VerifiedControlOrbit(role, members, representative, witnesses)
    _CONTROL_ORBIT_CACHE[cache_key] = result
    return result


def _materialize_instance_source(
    matrix: _FrozenMatrix,
    spec: _InstanceSpec,
    *,
    opened: _OpenedHeldout | None = None,
    max_transition_rows: int = 2048,
    admit_only: bool = False,
) -> Any:
    if type(matrix) is not _FrozenMatrix or type(spec) is not _InstanceSpec:
        raise StrictContractError("snapshot materialization requires strict frozen inputs")
    if spec.stratum == "heldout":
        if type(opened) is not _OpenedHeldout or spec not in opened.instances:
            raise StrictContractError("held-out snapshot access preceded the schedule barrier")
    elif opened is not None:
        raise StrictContractError("train materialization cannot consume a held-out capability")
    if type(max_transition_rows) is not int or max_transition_rows < 0:
        raise StrictContractError("snapshot transition-row cap is invalid")
    state_count, row_count = _snapshot_counts(spec, matrix.queries)
    if state_count > 128 or row_count > max_transition_rows:
        raise _PrerequisiteBlocked(
            "GLOBAL_PREFLIGHT_FROZEN_FIXTURE_SNAPSHOT_ROW_CAP_INCOMPATIBILITY"
        )
    if type(admit_only) is not bool:
        raise StrictContractError("snapshot admission mode is not boolean")
    cached = None if admit_only else _VERIFIED_INSTANCE_CACHE.get(spec.instance_id)
    if cached is not None:
        if cached.spec != spec:
            raise StrictContractError("verified snapshot cache binding changed")
        return cached

    vocabulary, semantics = _frozen_runtime_ids(matrix)
    environment = _sha_bytes(
        f"u15-l0-environment-v1|{_MATRIX_ID}|{spec.instance_id}".encode("utf-8")
    )
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    frame_digest = observation_frame_digest(frame)
    bound_query_sha256s = _query_sha256s_for_frame(
        matrix, frame, semantics, vocabulary
    )
    zero = (_ZERO, _ZERO)
    states: list[SyntheticTotalizedState] = []
    seeds: list[str] = []
    transitions: list[SyntheticTransitionRow] = []
    query_by_id = {query.query_id: query for query in matrix.queries}

    def add_state(
        state_id: str,
        payload: dict[str, Any],
        status: TotalizedStatus,
        response: tuple[ExactRational, ExactRational],
    ) -> None:
        states.append(
            SyntheticTotalizedState(
                state_id=state_id,
                payload=CanonicalPayload.from_value(payload),
                totalized_kind=status,
                response_coordinates=response,
                frame_digest=frame_digest,
            )
        )

    closed_id = _STATE_ID_PREFIX + "C"
    sink_id = _STATE_ID_PREFIX + "K"
    for region_id in spec.region_ids:
        for query_id in _QUERY_IDS:
            query = query_by_id[query_id]
            source_id = _state_id(spec, region_id, query_id, "source")
            terminal_id = _terminal_id(spec, region_id, query_id)
            seeds.append(source_id)
            add_state(
                source_id,
                {
                    "kind": "u15_l0_source",
                    "instance_id": spec.instance_id,
                    "region_id": region_id,
                    "query_id": query_id,
                    "query_sha256": bound_query_sha256s[query_id],
                },
                TotalizedStatus.OPEN,
                zero,
            )
            intermediate_ids: list[str] = []
            for position in range(1, len(query.action_ids)):
                intermediate_id = _state_id(spec, region_id, query_id, str(position))
                intermediate_ids.append(intermediate_id)
                add_state(
                    intermediate_id,
                    {
                        "kind": "u15_l0_intermediate",
                        "instance_id": spec.instance_id,
                        "region_id": region_id,
                        "query_id": query_id,
                        "word_position_decimal": str(position),
                    },
                    TotalizedStatus.OPEN,
                    zero,
                )
            add_state(
                terminal_id,
                {
                    "kind": "u15_l0_terminal",
                    "instance_id": spec.instance_id,
                    "region_id": region_id,
                    "query_id": query_id,
                    "query_sha256": bound_query_sha256s[query_id],
                },
                TotalizedStatus.OPEN,
                spec.response(region_id, query_id),
            )
            chain = (source_id, *intermediate_ids)
            for position, source_id_in_chain in enumerate(chain):
                matching = query.action_ids[position]
                target = (
                    intermediate_ids[position]
                    if position < len(intermediate_ids)
                    else terminal_id
                )
                for action_id in _ACTION_IDS:
                    transitions.append(
                        SyntheticTransitionRow(
                            source_state_id=source_id_in_chain,
                            action_id=action_id,
                            target_state_id=target if action_id == matching else sink_id,
                            transition_semantics_digest=semantics.semantics_digest,
                        )
                    )
            for action_id in _ACTION_IDS:
                transitions.append(
                    SyntheticTransitionRow(
                        source_state_id=terminal_id,
                        action_id=action_id,
                        target_state_id=closed_id,
                        transition_semantics_digest=semantics.semantics_digest,
                    )
                )
    add_state(
        closed_id,
        {"kind": "u15_l0_closed", "instance_id": spec.instance_id},
        TotalizedStatus.CLOSED,
        zero,
    )
    add_state(
        sink_id,
        {"kind": "u15_l0_sink", "instance_id": spec.instance_id},
        TotalizedStatus.SINK,
        zero,
    )
    for absorber in (closed_id, sink_id):
        for action_id in _ACTION_IDS:
            transitions.append(
                SyntheticTransitionRow(
                    source_state_id=absorber,
                    action_id=action_id,
                    target_state_id=absorber,
                    transition_semantics_digest=semantics.semantics_digest,
                )
            )
    if len(states) != state_count or len(transitions) != row_count:
        raise StrictContractError("snapshot preflight and materialization counts disagree")
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=("observable_delta", "return_memory"),
        seed_state_ids=tuple(seeds),
        states=tuple(states),
        actions=matrix.synthetic_actions,
        transitions=tuple(transitions),
        frame_digest=frame_digest,
        transition_semantics_digest=semantics.semantics_digest,
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    if admit_only:
        return admitted
    witness = _RECOMPUTE_CERTIFICATE_WITNESSES.get(spec.instance_id)
    certificate = None
    if witness is not None and witness[0] == spec:
        candidate = type(witness[1]).from_dict(witness[1].to_dict())
        if candidate.snapshot_sha256 == admitted.admission_report.snapshot_sha256:
            try:
                verified = verify_exact_partition(admitted, candidate)
                certificate = candidate
            except StrictContractError:
                certificate = None
    if certificate is None:
        certificate = refine_exact_partition(admitted)
        verified = verify_exact_partition(admitted, certificate)
    state_to_block = {
        state_id: block.block_index
        for block in verified.certificate.final_blocks
        for state_id in block.member_state_ids
    }
    terminal_blocks = tuple(
        (
            region_id,
            query.query_id,
            state_to_block[_terminal_id(spec, region_id, query.query_id)],
        )
        for region_id in spec.region_ids
        for query in matrix.queries
    )
    result = _VerifiedInstance(
        spec,
        admitted,
        verified,
        terminal_blocks,
        admitted.admission_report.snapshot_sha256,
        _sha(verified.certificate.to_dict()),
    )
    _verify_region_projection(result, matrix.queries)
    _VERIFIED_INSTANCE_CACHE[spec.instance_id] = result
    return result


def _materialize_verified_instance(
    matrix: _FrozenMatrix,
    spec: _InstanceSpec,
    *,
    opened: _OpenedHeldout | None = None,
    max_transition_rows: int = 2048,
) -> _VerifiedInstance:
    result = _materialize_instance_source(
        matrix,
        spec,
        opened=opened,
        max_transition_rows=max_transition_rows,
        admit_only=False,
    )
    if type(result) is not _VerifiedInstance:
        raise StrictContractError("verified snapshot materialization returned admission only")
    return result


def _admit_control_instance(
    matrix: _FrozenMatrix,
    spec: _InstanceSpec,
    *,
    opened: _OpenedHeldout | None = None,
    max_transition_rows: int,
) -> Any:
    return _materialize_instance_source(
        matrix,
        spec,
        opened=opened,
        max_transition_rows=max_transition_rows,
        admit_only=True,
    )


def _verify_region_projection(
    instance: _VerifiedInstance, queries: tuple[_QuerySpec, ...]
) -> None:
    signatures = {
        region_id: tuple(
            instance.terminal_block(region_id, query.query_id) for query in queries
        )
        for region_id in instance.spec.region_ids
    }
    block_by_region = {
        region_id: block_index
        for block_index, block in enumerate(instance.spec.exact_partition)
        for region_id in block
    }
    for left in instance.spec.region_ids:
        for right in instance.spec.region_ids:
            same_declared = block_by_region[left] == block_by_region[right]
            if (signatures[left] == signatures[right]) is not same_declared:
                raise StrictContractError(
                    "declared region partition violates verified terminal signatures"
                )
    for left, right, query_id in instance.spec.seeds:
        if (
            instance.spec.response(left, query_id)
            == instance.spec.response(right, query_id)
            or instance.terminal_block(left, query_id)
            == instance.terminal_block(right, query_id)
        ):
            raise StrictContractError("seeded exact inequality is not independently verified")


def _family_spec(matrix: _FrozenMatrix, family_id: str) -> _FamilySpec:
    matches = tuple(family for family in matrix.families if family.family_id == family_id)
    if len(matches) != 1:
        raise StrictContractError("family lookup is not unique")
    return matches[0]


def _template(matrix: _FrozenMatrix, template_id: str) -> dict[str, Any]:
    matches = tuple(raw for name, raw in matrix.template_rows if name == template_id)
    if len(matches) != 1:
        raise StrictContractError("before-graph template lookup is not unique")
    return _strict_json_object(matches[0], "before-graph template", require_canonical=True)


def _core_binding(matrix: _FrozenMatrix, verified: _VerifiedInstance) -> _CoreBinding:
    snapshot = verified.admitted.snapshot
    family = _family_spec(matrix, verified.spec.family_id)
    regions: list[Any] = []
    for raw in family.region_rows:
        row = _strict_json_object(raw, "family region", require_canonical=True)
        template = _template(matrix, row["before_graph_template_id"])
        relabel = row["node_relabeling"]
        if type(relabel) is not dict:
            raise StrictContractError("node relabeling is not an object")
        old_ids = tuple(node["node_id"] for node in template["nodes"])
        if set(relabel) != set(old_ids) or len(set(relabel.values())) != len(relabel):
            raise StrictContractError("node relabeling is not a bijection")
        nodes = tuple(
            {"node_id": relabel[node["node_id"]], "node_kind": node["node_kind"]}
            for node in template["nodes"]
        )
        edges = tuple(
            {
                "source": relabel[edge["source"]],
                "target": relabel[edge["target"]],
                "edge_kind": edge["edge_kind"],
            }
            for edge in template["edges"]
        )
        ports = tuple(
            {
                "port_id": port["port_id"],
                "kind": port["kind"],
                "attached_node_id": relabel[port["attached_node_id"]],
            }
            for port in template["boundary_ports"]
        )
        region = make_before_local_region(
            region_id=row["region_id"],
            observation_frame_id=snapshot.observation_frame_id,
            transition_semantics_id=snapshot.transition_semantics_id,
            nodes=nodes,
            edges=edges,
            boundary_ports=ports,
            separator_node_ids=tuple(
                relabel[item] for item in template["separator_node_ids"]
            ),
            target_node_id=relabel[template["target_node_id"]],
        )
        feature = extract_before_locality_features(region)
        expected = template["expected_features"]
        feature_wire = feature.to_dict()
        if (
            {row["kind"]: row["count"] for row in feature_wire["node_kind_count_rows"]}
            != expected["node_kind_counts"]
            or feature_wire["boundary_port_kind_count_rows"]
            != expected["boundary_port_kind_count_rows"]
            or feature_wire["shared_mvar_degree_multiset"]
            != expected["shared_mvar_degree_multiset"]
            or feature_wire["component_size_profile_after_separator_deletion"]
            != expected["component_size_profile_after_separator_deletion"]
            or feature_wire["articulation_count"] != expected["articulation_count"]
            or feature_wire["cycle_rank"] != expected["cycle_rank"]
            or feature_wire["exact_treewidth"] != expected["exact_treewidth"]
            or feature_wire["radius"] != expected["radius"]
            or feature_wire["target_site_kind"] != expected["target_site_kind"]
        ):
            raise StrictContractError("derived before feature differs from frozen template")
        regions.append(region)
    queries = tuple(
        make_locality_query(
            query_id=query.query_id,
            observation_frame_id=snapshot.observation_frame_id,
            transition_semantics_id=snapshot.transition_semantics_id,
            response_vocabulary_id=snapshot.response_vocabulary_id,
            action_catalog=matrix.synthetic_actions,
            action_word_ids=query.action_ids,
            closing_context_id="observe_two_coordinate_response",
            closing_action_ids=(),
            response_coordinate_ids=("observable_delta", "return_memory"),
        )
        for query in matrix.queries
    )
    observations = tuple(
        make_exact_local_response_observation(
            family_id=verified.spec.family_id,
            instance_id=verified.spec.instance_id,
            region_id=region_id,
            query=query,
            response_vector=verified.spec.response(region_id, query.query_id),
            verified_partition=verified.verified,
            terminal_state_id=_terminal_id(
                verified.spec, region_id, query.query_id
            ),
        )
        for region_id in verified.spec.region_ids
        for query in queries
    )
    action_digest = snapshot.domain_id.action_alphabet_digest
    initial = propose_nominal_partition(regions, action_catalog_digest=action_digest)
    if initial.blocks != _canonical_partition(verified.spec.initial_partition):
        raise StrictContractError("feature-derived P0 differs from the frozen partition")
    return _CoreBinding(
        tuple(regions), queries, observations, action_digest
    )


@lru_cache(maxsize=1)
def _open_heldout(
    matrix: _FrozenMatrix, barrier: _ScheduleBarrier
) -> _OpenedHeldout:
    if type(matrix) is not _FrozenMatrix or type(barrier) is not _ScheduleBarrier:
        raise StrictContractError("held-out opening requires the complete schedule barrier")
    if _sha_bytes(barrier.digest_map_bytes) != barrier.barrier_sha256:
        raise StrictContractError("schedule barrier digest changed")
    digest_map = _strict_json_object(
        barrier.digest_map_bytes, "schedule digest map", require_canonical=True
    )
    if (
        len(digest_map) != len(_FAMILY_IDS)
        or frozenset(digest_map) != frozenset(_FAMILY_IDS)
    ):
        raise StrictContractError("schedule barrier lacks the eight frozen families")
    instances: list[_InstanceSpec] = []
    for family in matrix.families:
        if set(digest_map[family.family_id]) != {
            "locality_schedule_sha256",
            "baseline_schedule_sha256",
        }:
            raise StrictContractError("schedule barrier lacks one method digest")
        for raw in family.heldout_bytes:
            row = _strict_json_object(raw, "sealed held-out row", require_canonical=True)
            instances.append(
                _parse_instance(
                    family.family_id,
                    family.train.region_ids,
                    family.initial_partition,
                    family.exact_partition,
                    row,
                )
            )
    if len(instances) != 16:
        raise StrictContractError("held-out denominator changed")
    return _OpenedHeldout(tuple(instances), _OPEN_TOKEN)


def _behavior_vector(spec: _InstanceSpec, region_id: str) -> tuple[Fraction, ...]:
    values = tuple(
        coordinate
        for query_id in _QUERY_IDS
        for coordinate in spec.response(region_id, query_id)
    )
    result = tuple(_fraction(value) for value in values)
    if len(result) != _BEHAVIOR_DIMENSION:
        raise StrictContractError("global behavior vector is not 16-dimensional")
    return result


@lru_cache(maxsize=2048)
def _covariance(
    spec: _InstanceSpec, partition: tuple[tuple[str, ...], ...]
) -> _Covariance:
    _partition([list(block) for block in partition], spec.region_ids, "runtime partition")
    vectors = {region: _behavior_vector(spec, region) for region in spec.region_ids}
    n = len(spec.region_ids)
    cells = [
        [Fraction(0) for _column in range(_BEHAVIOR_DIMENSION)]
        for _row in range(_BEHAVIOR_DIMENSION)
    ]
    for block in partition:
        means = tuple(
            sum(vectors[region][coordinate] for region in block) / len(block)
            for coordinate in range(_BEHAVIOR_DIMENSION)
        )
        for region in block:
            residual = tuple(
                vectors[region][coordinate] - means[coordinate]
                for coordinate in range(_BEHAVIOR_DIMENSION)
            )
            for row in range(_BEHAVIOR_DIMENSION):
                for column in range(_BEHAVIOR_DIMENSION):
                    cells[row][column] += residual[row] * residual[column] / n
                    _exact(cells[row][column])
    result_cells = tuple(tuple(row) for row in cells)
    wire = [
        [_exact(value).to_dict() for value in row]
        for row in result_cells
    ]
    trace = sum(
        result_cells[index][index] for index in range(_BEHAVIOR_DIMENSION)
    )
    _exact(trace)
    return _Covariance(result_cells, _sha(wire), trace)


def _canonical_partition(
    blocks: tuple[tuple[str, ...], ...]
) -> tuple[tuple[str, ...], ...]:
    normalized = tuple(
        tuple(sorted(block, key=lambda item: item.encode("utf-8")))
        for block in blocks
    )
    return tuple(
        sorted(normalized, key=lambda block: canonical_contract_bytes(list(block)))
    )


def _carrier_covariance(
    spec: _InstanceSpec,
    partition: tuple[tuple[str, ...], ...],
    memo: dict[tuple[tuple[str, ...], ...], _Covariance],
) -> _Covariance:
    """Memoize the exact covariance only inside one immutable carrier run."""

    canonical = _canonical_partition(partition)
    current = memo.get(canonical)
    if current is None:
        current = _covariance(spec, canonical)
        memo[canonical] = current
    return current


def _separate(
    partition: tuple[tuple[str, ...], ...], left: str, right: str
) -> tuple[tuple[str, ...], ...]:
    if not any(left in block and right in block for block in partition):
        return partition
    endpoint = max((left, right), key=lambda item: item.encode("utf-8"))
    output: list[tuple[str, ...]] = []
    for block in partition:
        if endpoint in block and len(block) > 1:
            output.append(tuple(item for item in block if item != endpoint))
            output.append((endpoint,))
        else:
            output.append(block)
    refined = _canonical_partition(tuple(output))
    if len(refined) != len(partition) + 1:
        raise StrictContractError("counterexample split is not a strict refinement")
    return refined


def _candidate_refinement(
    spec: _InstanceSpec,
    partition: tuple[tuple[str, ...], ...],
    candidate: _Candidate,
) -> tuple[tuple[str, ...], ...]:
    if candidate.instance_id != spec.instance_id:
        raise StrictContractError("candidate instance binding changed")
    if spec.response(candidate.left_region_id, candidate.query.query_id) == spec.response(
        candidate.right_region_id, candidate.query.query_id
    ):
        return partition
    return _separate(partition, candidate.left_region_id, candidate.right_region_id)


def _schedule_digest(candidates: tuple[_Candidate, ...]) -> str:
    return _sha([candidate.wire for candidate in candidates])


@lru_cache(maxsize=1)
def _build_train_schedules(
    matrix: _FrozenMatrix,
) -> tuple[
    tuple[_Schedule, ...], tuple[_Schedule, ...], tuple[_VerifiedInstance, ...]
]:
    locality: list[_Schedule] = []
    baseline: list[_Schedule] = []
    verified_train: list[_VerifiedInstance] = []
    for carrier in _train_carriers(matrix):
        verified = _materialize_verified_instance(matrix, carrier.instance)
        verified_train.append(verified)
        universe = _candidate_universe(carrier)
        baseline_candidates = tuple(
            sorted(universe, key=lambda candidate: candidate.wire_bytes)[:_BUDGET]
        )
        baseline.append(
            _Schedule(
                carrier.family_id,
                "baseline",
                baseline_candidates,
                _schedule_digest(baseline_candidates),
            )
        )

        partition = _canonical_partition(carrier.instance.initial_partition)
        covariance_memo: dict[tuple[tuple[str, ...], ...], _Covariance] = {}
        remaining = list(universe)
        selected: list[_Candidate] = []
        while remaining and len(selected) < _BUDGET:
            before = _carrier_covariance(
                carrier.instance, partition, covariance_memo
            ).trace
            scored: list[tuple[Fraction, int, bytes, _Candidate]] = []
            for candidate in remaining:
                after_partition = _candidate_refinement(
                    carrier.instance, partition, candidate
                )
                after = _carrier_covariance(
                    carrier.instance, after_partition, covariance_memo
                ).trace
                gain = before - after
                if gain < 0:
                    raise StrictContractError("candidate refinement increased exact loss")
                score = gain / candidate.query.cost
                _exact(score)
                scored.append(
                    (-score, candidate.query.cost, candidate.wire_bytes, candidate)
                )
            scored.sort(key=lambda row: (row[0], row[1], row[2]))
            candidate = scored[0][3]
            # Only the selected two-coordinate response causes the operative split.
            partition = _candidate_refinement(carrier.instance, partition, candidate)
            selected.append(candidate)
            remaining.remove(candidate)
        selected_tuple = tuple(selected)
        locality.append(
            _Schedule(
                carrier.family_id,
                "locality",
                selected_tuple,
                _schedule_digest(selected_tuple),
            )
        )
        binding = _core_binding(matrix, verified)
        report = run_synthetic_locality_cegar(
            binding.regions,
            binding.queries,
            binding.observations,
            action_catalog_digest=binding.action_catalog_digest,
        )
        verified_report = verify_locality_cegar_report(
            report,
            binding.regions,
            binding.queries,
            binding.observations,
            action_catalog_digest=binding.action_catalog_digest,
        )
        public_order = tuple(
            (
                row.left_region_id,
                row.right_region_id,
                row.query.query_id,
            )
            for row in verified_report.selected_scores
        )
        private_order = tuple(
            (
                row.left_region_id,
                row.right_region_id,
                row.query.query_id,
            )
            for row in selected_tuple
        )
        if public_order != private_order:
            raise StrictContractError("public and evaluation locality recurrences disagree")
        _PUBLIC_REPORT_CACHE[carrier.instance.instance_id] = verified_report
    return tuple(locality), tuple(baseline), tuple(verified_train)


def _seal_schedules(
    locality: tuple[_Schedule, ...], baseline: tuple[_Schedule, ...]
) -> _ScheduleBarrier:
    if (
        tuple(row.family_id for row in locality) != _FAMILY_IDS
        or tuple(row.family_id for row in baseline) != _FAMILY_IDS
        or any(row.method_id != "locality" for row in locality)
        or any(row.method_id != "baseline" for row in baseline)
    ):
        raise StrictContractError("complete two-method family schedules are required")
    digest_map = {
        family_id: {
            "locality_schedule_sha256": locality[index].sha256,
            "baseline_schedule_sha256": baseline[index].sha256,
        }
        for index, family_id in enumerate(_FAMILY_IDS)
    }
    raw = canonical_contract_bytes(digest_map)
    return _ScheduleBarrier(raw, _sha_bytes(raw), _SCHEDULE_TOKEN)


def _substitute_schedule(
    schedule: _Schedule, spec: _InstanceSpec
) -> tuple[_Candidate, ...]:
    if schedule.family_id != spec.family_id or spec.stratum != "heldout":
        raise StrictContractError("held-out schedule substitution changed family/role")
    result = tuple(
        _candidate(
            candidate.family_id,
            spec.instance_id,
            candidate.left_region_id,
            candidate.right_region_id,
            candidate.query,
        )
        for candidate in schedule.candidates
    )
    for source, target in zip(schedule.candidates, result, strict=True):
        source_wire = source.wire
        target_wire = target.wire
        if source_wire["instance_id"] == target_wire["instance_id"]:
            raise StrictContractError("held-out substitution did not change instance ID")
        source_wire["instance_id"] = target_wire["instance_id"]
        if source_wire != target_wire:
            raise StrictContractError("held-out schedule was altered beyond instance ID")
    return result


@dataclass(frozen=True)
class _InstanceCurve:
    family_id: str
    instance_id: str
    method_id: str
    partitions: tuple[tuple[tuple[str, ...], ...], ...]
    covariances: tuple[_Covariance, ...]
    cumulative_costs: tuple[int, ...]
    prefix_sha256s: tuple[str, ...]
    statuses: tuple[str, ...]
    consumed: tuple[int, ...]


@lru_cache(maxsize=64)
def _evaluate_instance(
    verified: _VerifiedInstance,
    schedule: _Schedule,
    p0: _P0Barrier,
) -> _InstanceCurve:
    if type(p0) is not _P0Barrier:
        raise StrictContractError("paired evaluation requires the global P0 barrier")
    candidates = _substitute_schedule(schedule, verified.spec)
    if len(candidates) > _BUDGET or len(candidates) != len(
        {candidate.wire_bytes for candidate in candidates}
    ):
        raise StrictContractError("held-out schedule exceeds budget or repeats")
    partition = _canonical_partition(verified.spec.initial_partition)
    partitions = [partition]
    covariances = [_covariance(verified.spec, partition)]
    costs = [0]
    prefixes = [_sha([])]
    statuses = ["P0_SEALED"]
    consumed = [0]
    prefix: list[_Candidate] = []
    for candidate in candidates:
        if len(prefix) >= _BUDGET:
            raise StrictContractError("seventeenth candidate observation attempted")
        partition = _candidate_refinement(verified.spec, partition, candidate)
        prefix.append(candidate)
        partitions.append(partition)
        covariances.append(_covariance(verified.spec, partition))
        costs.append(costs[-1] + candidate.query.cost)
        prefixes.append(_sha([item.wire for item in prefix]))
        statuses.append("NORMAL_BUDGET_COMPLETE" if len(prefix) == 16 else "OBSERVED")
        consumed.append(len(prefix))
    while len(partitions) < 17:
        partitions.append(partition)
        covariances.append(covariances[-1])
        costs.append(costs[-1])
        prefixes.append(prefixes[-1])
        statuses.append("UNIVERSE_EXHAUSTED_PLATEAU")
        consumed.append(len(prefix))
    if not all(len(rows) == 17 for rows in (partitions, covariances, costs, prefixes, statuses, consumed)):
        raise StrictContractError("paired curve is not defined at t=0..16")
    return _InstanceCurve(
        verified.spec.family_id,
        verified.spec.instance_id,
        schedule.method_id,
        tuple(partitions),
        tuple(covariances),
        tuple(costs),
        tuple(prefixes),
        tuple(statuses),
        tuple(consumed),
    )


@lru_cache(maxsize=1)
def _seal_p0(
    matrix: _FrozenMatrix,
    opened: _OpenedHeldout,
) -> tuple[_P0Barrier, tuple[_VerifiedInstance, ...]]:
    if type(opened) is not _OpenedHeldout:
        raise StrictContractError("P0 sealing requires an opened held-out carrier")
    verified: list[_VerifiedInstance] = []
    rows: list[tuple[str, str, str, Fraction]] = []
    for spec in opened.instances:
        current = _materialize_verified_instance(matrix, spec, opened=opened)
        verified.append(current)
        covariance = _covariance(spec, _canonical_partition(spec.initial_partition))
        rows.append(
            (spec.family_id, spec.instance_id, covariance.sha256, covariance.trace)
        )
    if len(rows) != 16:
        raise _PrerequisiteBlocked("GLOBAL_P0_DENOMINATOR_INCOMPLETE")
    wire = [
        {
            "family_id": family,
            "instance_id": instance,
            "covariance_sha256": digest,
            "trace_loss": _exact(trace).to_dict(),
        }
        for family, instance, digest, trace in rows
    ]
    return _P0Barrier(tuple(rows), _sha(wire), _P0_TOKEN), tuple(verified)


def _mean_covariances(left: _Covariance, right: _Covariance) -> _Covariance:
    cells = tuple(
        tuple((left.cells[row][column] + right.cells[row][column]) / 2 for column in range(16))
        for row in range(16)
    )
    wire = [[_exact(value).to_dict() for value in row] for row in cells]
    trace = sum(cells[index][index] for index in range(16))
    if trace != (left.trace + right.trace) / 2:
        raise StrictContractError("family covariance trace is not the exact instance mean")
    return _Covariance(cells, _sha(wire), trace)


def _seed_misses(
    verified_train: tuple[_VerifiedInstance, ...],
    verified_heldout: tuple[_VerifiedInstance, ...],
    locality_schedules: tuple[_Schedule, ...],
    locality_curves: tuple[_InstanceCurve, ...],
) -> tuple[dict[str, Any], ...]:
    locality_only = tuple(
        curve for curve in locality_curves if curve.method_id == "locality"
    )
    if (
        len(locality_only) != len(verified_heldout)
        or len({curve.instance_id for curve in locality_only}) != len(locality_only)
    ):
        raise StrictContractError(
            "seed audit requires one locality curve per held-out instance"
        )
    final_by_instance = {
        curve.instance_id: curve.partitions[-1] for curve in locality_only
    }
    schedule_by_family = {row.family_id: row for row in locality_schedules}
    misses: list[dict[str, Any]] = []
    for verified in (*verified_train, *verified_heldout):
        spec = verified.spec
        if spec.stratum == "train":
            partition = _canonical_partition(spec.initial_partition)
            for candidate in schedule_by_family[spec.family_id].candidates:
                partition = _candidate_refinement(spec, partition, candidate)
        else:
            partition = final_by_instance[spec.instance_id]
        for left, right, query_id in spec.seeds:
            if any(left in block and right in block for block in partition):
                misses.append(
                    {
                        "family_id": spec.family_id,
                        "instance_id": spec.instance_id,
                        "left_region_id": left,
                        "right_region_id": right,
                        "query_id": query_id,
                    }
                )
    return tuple(misses)


def _verify_heldout_public_reports(
    matrix: _FrozenMatrix,
    verified_heldout: tuple[_VerifiedInstance, ...],
    locality_schedules: tuple[_Schedule, ...],
    locality_curves: tuple[_InstanceCurve, ...],
) -> None:
    schedules = {row.family_id: row for row in locality_schedules}
    curves = {
        row.instance_id: row
        for row in locality_curves
        if row.method_id == "locality"
    }
    for verified in verified_heldout:
        schedule = schedules[verified.spec.family_id]
        frozen_order = tuple(
            (
                candidate.left_region_id,
                candidate.right_region_id,
                candidate.query.query_id,
            )
            for candidate in schedule.candidates
        )
        binding = _core_binding(matrix, verified)
        checked = _PUBLIC_REPORT_CACHE.get(verified.spec.instance_id)
        if checked is None:
            report = run_synthetic_locality_cegar(
                binding.regions,
                binding.queries,
                binding.observations,
                action_catalog_digest=binding.action_catalog_digest,
                frozen_candidate_order=frozen_order,
            )
            checked = verify_locality_cegar_report(
                report,
                binding.regions,
                binding.queries,
                binding.observations,
                action_catalog_digest=binding.action_catalog_digest,
                frozen_candidate_order=frozen_order,
            )
        curve = curves[verified.spec.instance_id]
        selected_order = tuple(
            (row.left_region_id, row.right_region_id, row.query.query_id)
            for row in checked.selected_scores
        )
        if selected_order != frozen_order:
            raise StrictContractError("held-out public report reordered the train schedule")
        for index, score in enumerate(checked.selected_scores):
            if (
                score.covariance_before_sha256
                != curve.covariances[index].sha256
                or score.covariance_after_sha256
                != curve.covariances[index + 1].sha256
                or _fraction(score.trace_before)
                != curve.covariances[index].trace
                or _fraction(score.trace_after)
                != curve.covariances[index + 1].trace
                or score.derived_cost != schedule.candidates[index].query.cost
            ):
                raise StrictContractError(
                    "public held-out report differs from exact paired recurrence"
                )
        if (
            checked.final_partition is None
            or checked.final_partition.blocks != curve.partitions[len(frozen_order)]
            or checked.candidate_observations_consumed != len(frozen_order)
            or checked.cumulative_derived_cost
            != sum(candidate.query.cost for candidate in schedule.candidates)
        ):
            raise StrictContractError("public held-out report final binding changed")
        _PUBLIC_REPORT_CACHE[verified.spec.instance_id] = checked


def _family_curve_rows(
    curves: tuple[_InstanceCurve, ...]
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for method_id in ("locality", "baseline"):
        for family_id in _FAMILY_IDS:
            pair = tuple(
                curve
                for curve in curves
                if curve.method_id == method_id and curve.family_id == family_id
            )
            if len(pair) != 2:
                raise StrictContractError("family curve does not contain two instances")
            for t in range(17):
                covariance = _mean_covariances(
                    pair[0].covariances[t], pair[1].covariances[t]
                )
                rows.append(
                    {
                        "method_id": method_id,
                        "family_id": family_id,
                        "t": t,
                        "covariance_sha256": covariance.sha256,
                        "trace_loss": _exact(covariance.trace).to_dict(),
                    }
                )
    return tuple(rows)


def _family_curve_wire_rows(
    family_rows: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    """Group the 272 exact points below the frozen per-array wire cap."""

    grouped: list[dict[str, Any]] = []
    for method_id in ("locality", "baseline"):
        for family_id in _FAMILY_IDS:
            points = tuple(
                row
                for row in family_rows
                if row["method_id"] == method_id and row["family_id"] == family_id
            )
            if len(points) != 17 or tuple(row["t"] for row in points) != tuple(
                range(17)
            ):
                raise StrictContractError("family curve is not a complete t=0..16 row")
            grouped.append(
                {
                    "method_id": method_id,
                    "family_id": family_id,
                    "points": [
                        {
                            "t": row["t"],
                            "covariance_sha256": row["covariance_sha256"],
                            "trace_loss": row["trace_loss"],
                        }
                        for row in points
                    ],
                }
            )
    return tuple(grouped)


def _family_loss(
    family_rows: tuple[dict[str, Any], ...], method_id: str, family_id: str, t: int
) -> Fraction:
    matches = tuple(
        row
        for row in family_rows
        if row["method_id"] == method_id
        and row["family_id"] == family_id
        and row["t"] == t
    )
    if len(matches) != 1:
        raise StrictContractError("family loss lookup is not unique")
    return _fraction(ExactRational.from_dict(matches[0]["trace_loss"]))


def _overall_curve(
    family_rows: tuple[dict[str, Any], ...], method_id: str
) -> tuple[Fraction, ...]:
    return tuple(
        sum(_family_loss(family_rows, method_id, family_id, t) for family_id in _FAMILY_IDS)
        / 8
        for t in range(17)
    )


@lru_cache(maxsize=4)
def _bootstrap(
    family_deltas: tuple[Fraction, ...]
) -> tuple[Fraction, Fraction]:
    if len(family_deltas) != 8:
        raise StrictContractError("bootstrap requires eight family aggregates")
    replicates: list[tuple[Fraction, int]] = []
    seed = 2_026_071_701
    for replicate in range(10_000):
        total = Fraction(0)
        for draw in range(8):
            material = (
                f"u15-l0-bootstrap-v1|{seed}|{replicate}|{draw}".encode("utf-8")
            )
            digest = hashlib.sha256(material).digest()
            family_index = int.from_bytes(digest[:8], "big") % 8
            total += family_deltas[family_index]
        value = total / 8
        _exact(value)
        replicates.append((value, replicate))
    replicates.sort(key=lambda row: (row[0], row[1]))
    return replicates[249][0], replicates[9749][0]


def _instance_checkpoint_rows(
    curves: tuple[_InstanceCurve, ...]
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for curve in curves:
        for t in _CHECKPOINTS:
            row = {
                "method_id": curve.method_id,
                "family_id": curve.family_id,
                "instance_id": curve.instance_id,
                "t": t,
                "partition": [list(block) for block in curve.partitions[t]],
                "candidate_prefix_sha256": curve.prefix_sha256s[t],
                "covariance_sha256": curve.covariances[t].sha256,
                "trace_loss": _exact(curve.covariances[t].trace).to_dict(),
                "coverage_numerator": 1,
                "fixed_denominator": 1,
                "abstention_count": 0,
                "abstention_reason": None,
                "censor_count": 0,
                "censor_reason": None,
                "candidate_observations_consumed": curve.consumed[t],
                "cumulative_derived_cost": curve.cumulative_costs[t],
                "status": curve.statuses[t],
            }
            row["row_sha256"] = _sha(row)
            rows.append(row)
    return tuple(rows)


def _instance_row(
    rows: tuple[dict[str, Any], ...], method: str, instance: str, t: int
) -> dict[str, Any]:
    matches = tuple(
        row
        for row in rows
        if row["method_id"] == method
        and row["instance_id"] == instance
        and row["t"] == t
    )
    if len(matches) != 1:
        raise StrictContractError("instance checkpoint lookup is not unique")
    return matches[0]


def _family_checkpoint_rows(
    family_curves: tuple[dict[str, Any], ...],
    instance_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    output: list[dict[str, Any]] = []
    for method in ("locality", "baseline"):
        for family_id in _FAMILY_IDS:
            instance_ids = (
                f"{family_id}__heldout_alpha",
                f"{family_id}__heldout_beta",
            )
            for t in _CHECKPOINTS:
                curve_row = next(
                    row
                    for row in family_curves
                    if row["method_id"] == method
                    and row["family_id"] == family_id
                    and row["t"] == t
                )
                bound = tuple(
                    _instance_row(instance_rows, method, instance_id, t)
                    for instance_id in instance_ids
                )
                output.append(
                    {
                        "method_id": method,
                        "family_id": family_id,
                        "t": t,
                        "instance_checkpoint_sha256s": [
                            row["row_sha256"] for row in bound
                        ],
                        "candidate_prefix_sha256s": [
                            row["candidate_prefix_sha256"] for row in bound
                        ],
                        "covariance_sha256": curve_row["covariance_sha256"],
                        "trace_loss": curve_row["trace_loss"],
                        "coverage_numerator": 2,
                        "fixed_denominator": 2,
                        "abstention_count": 0,
                        "censor_count": 0,
                    }
                )
    return tuple(output)


def _schedule_rows(
    locality: tuple[_Schedule, ...], baseline: tuple[_Schedule, ...]
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "method_id": schedule.method_id,
            "family_id": schedule.family_id,
            "schedule_length": len(schedule.candidates),
            "schedule_sha256": schedule.sha256,
            "candidate_sha256s": [
                _sha_bytes(candidate.wire_bytes) for candidate in schedule.candidates
            ],
            "total_derived_cost": sum(
                candidate.query.cost for candidate in schedule.candidates
            ),
        }
        for schedule in (*locality, *baseline)
    )


def _classify_disposition(
    *,
    locality: tuple[Fraction, ...],
    baseline: tuple[Fraction, ...],
    seed_miss_count: int,
    locality_abstentions: int = 0,
    baseline_abstentions: int = 0,
    execution_failure: str | None = None,
    prerequisite_failure: str | None = None,
) -> tuple[str, str | None]:
    if execution_failure is not None:
        return "L0_EXECUTION_FAILED", execution_failure
    if prerequisite_failure is not None:
        return "L0_PREREQUISITE_BLOCKED", prerequisite_failure
    if (
        len(locality) != 17
        or len(baseline) != 17
        or seed_miss_count < 0
        or locality_abstentions < 0
        or baseline_abstentions < 0
    ):
        return "L0_EXECUTION_FAILED", "INCOMPLETE_OR_INVALID_PAIRED_CURVE"
    if (
        seed_miss_count
        or locality_abstentions > baseline_abstentions
        or any(locality[t] > baseline[t] for t in range(17))
    ):
        return (
            "L0_SYNTHETIC_CEGAR_DEGRADED",
            "LOCALITY_POLICY_WORSE_OR_SEED_INCOMPLETE",
        )
    if any(locality[t] < baseline[t] for t in range(17)):
        return "L0_SYNTHETIC_CEGAR_GAIN_OBSERVED", None
    return (
        "L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN",
        "L0_STRUCTURAL_HEURISTIC_NOT_SUPPORTED",
    )


def _strict_reachability_fixture(
    matrix: _FrozenMatrix,
) -> tuple[dict[str, Any], dict[str, str]]:
    source = _strict_json_object(
        matrix.control_bytes, "reachability controls", require_canonical=True
    )
    _exact_fields(
        source,
        {"reachability_control_fixture", "disposition_reachability_controls"},
        "reachability control source",
    )
    fixture = _exact_fields(
        source["reachability_control_fixture"],
        {
            "scope",
            "strictness_rule",
            "family_ids",
            "regions",
            "initial_partition",
            "exact_partition_for_distinguishing_variants",
            "instances_per_family",
            "default_response_vector",
            "train_right_override_vector",
            "heldout_alpha_right_override_vector",
            "heldout_beta_right_override_vector",
            "canonical_query_order_for_the_sole_region_pair",
            "fixed_denominator",
            "coverage_censor_abstention_rule",
        },
        "reachability control fixture",
    )
    family_ids = [f"reachability_control_{index}" for index in range(8)]
    if (
        fixture["scope"] != "test_only_derivation_never_primary_data"
        or fixture["strictness_rule"]
        != "every_control_uses_the_same_strict_input_parser_verifier_and_disposition_precedence_and_no_control_bypasses_a_gate"
        or fixture["family_ids"] != family_ids
        or fixture["regions"] != ["control_left", "control_right"]
        or fixture["instances_per_family"]
        != ["train", "heldout_alpha", "heldout_beta"]
        or fixture["canonical_query_order_for_the_sole_region_pair"]
        != [
            "q_a_b",
            "q_a",
            "q_b_a",
            "q_b",
            "q_close",
            "q_ghost_store_reveal",
            "q_ghost_store",
            "q_reveal",
        ]
        or fixture["fixed_denominator"]
        != "eight_equal_families_and_sixteen_heldout_instances"
    ):
        raise StrictContractError("reachability control fixture changed")
    regions = tuple(fixture["regions"])
    if (
        _partition(fixture["initial_partition"], regions, "control initial partition")
        != (("control_left", "control_right"),)
        or _partition(
            fixture["exact_partition_for_distinguishing_variants"],
            regions,
            "control exact partition",
        )
        != (("control_left",), ("control_right",))
    ):
        raise StrictContractError("reachability control partitions changed")
    expected_vectors = (
        (Fraction(0), Fraction(0)),
        (Fraction(1), Fraction(0)),
        (Fraction(1), Fraction(1)),
        (Fraction(-1), Fraction(2)),
    )
    vector_fields = (
        "default_response_vector",
        "train_right_override_vector",
        "heldout_alpha_right_override_vector",
        "heldout_beta_right_override_vector",
    )
    parsed_vectors = tuple(
        tuple(_fraction(value) for value in _rational_row(fixture[name], name))
        for name in vector_fields
    )
    if parsed_vectors != expected_vectors:
        raise StrictContractError("reachability response vectors changed")
    registered_rows = source["disposition_reachability_controls"]
    if type(registered_rows) is not list or len(registered_rows) != 5:
        raise StrictContractError("reachability disposition rows changed")
    registered: dict[str, str] = {}
    for row in registered_rows:
        if type(row) is not dict or row.get("included_in_primary_endpoint") is not False:
            raise StrictContractError("reachability control entered the primary endpoint")
        variant = _identifier(row.get("variant_id"), "control variant_id")
        disposition = _identifier(
            row.get("expected_disposition"), "control expected disposition"
        )
        if variant in registered:
            raise StrictContractError("duplicate reachability control variant")
        registered[variant] = disposition
    if tuple(registered) != (
        "gain_reachable",
        "no_clear_gain_reachable",
        "degraded_reachable",
        "prerequisite_blocked_reachable",
        "execution_failed_reachable",
    ):
        raise StrictContractError("reachability control order changed")
    return fixture, registered


def _control_instance(
    fixture: dict[str, Any],
    *,
    variant_id: str,
    family_id: str,
    role: str,
    distinguishing_query_id: str | None,
) -> _InstanceSpec:
    regions = tuple(fixture["regions"])
    initial = _partition(
        fixture["initial_partition"], regions, "control initial partition"
    )
    exact = _partition(
        fixture[
            "initial_partition"
            if distinguishing_query_id is None
            else "exact_partition_for_distinguishing_variants"
        ],
        regions,
        "control exact partition",
    )
    if role not in {"train", "heldout_alpha", "heldout_beta"}:
        raise StrictContractError("control instance role changed")
    stratum = "train" if role == "train" else "heldout"
    vector_field = {
        "train": "train_right_override_vector",
        "heldout_alpha": "heldout_alpha_right_override_vector",
        "heldout_beta": "heldout_beta_right_override_vector",
    }[role]
    overrides = []
    seeds = []
    if distinguishing_query_id is not None:
        if distinguishing_query_id not in _QUERY_IDS:
            raise StrictContractError("control query is outside the frozen catalogue")
        overrides.append(
            {
                "region_id": "control_right",
                "query_id": distinguishing_query_id,
                "response_vector": copy.deepcopy(fixture[vector_field]),
            }
        )
        seeds.append(
            {
                "left_region_id": "control_left",
                "right_region_id": "control_right",
                "query_id": distinguishing_query_id,
            }
        )
    row = {
        "instance_id": f"{variant_id}__{family_id}__{role}",
        "stratum": stratum,
        "response_access": (
            "available_before_candidate_order_seal"
            if stratum == "train"
            else "sealed_until_global_eight_family_two_method_schedule_digest_map_committed"
        ),
        "full_response_table": {
            "default_response_vector": copy.deepcopy(
                fixture["default_response_vector"]
            ),
            "overrides": overrides,
        },
        "seeded_counterexample_pairs": seeds,
    }
    strict_row = _strict_json_object(
        canonical_contract_bytes(row),
        "reachability control instance",
        require_canonical=True,
    )
    return _parse_instance(family_id, regions, initial, exact, strict_row)


def _control_train_specs(
    fixture: dict[str, Any], variant_id: str, distinguishing_query_id: str | None
) -> tuple[_InstanceSpec, ...]:
    return tuple(
        _control_instance(
            fixture,
            variant_id=variant_id,
            family_id=family_id,
            role="train",
            distinguishing_query_id=distinguishing_query_id,
        )
        for family_id in fixture["family_ids"]
    )


def _control_heldout_specs(
    fixture: dict[str, Any],
    variant_id: str,
    distinguishing_query_id: str | None,
    barrier: _ScheduleBarrier,
) -> tuple[_InstanceSpec, ...]:
    if type(barrier) is not _ScheduleBarrier:
        raise StrictContractError("control heldout spec access preceded its barrier")
    return tuple(
        _control_instance(
            fixture,
            variant_id=variant_id,
            family_id=family_id,
            role=role,
            distinguishing_query_id=distinguishing_query_id,
        )
        for family_id in fixture["family_ids"]
        for role in ("heldout_alpha", "heldout_beta")
    )


def _control_global_preflight(
    matrix: _FrozenMatrix,
    fixture: dict[str, Any],
    *,
    max_transition_rows: int,
) -> tuple[int, int]:
    """Check the complete 24-carrier shape without opening heldout responses."""

    if type(max_transition_rows) is not int or max_transition_rows < 0:
        raise StrictContractError("control transition-row cap is invalid")
    if (
        fixture.get("family_ids")
        != [f"reachability_control_{index}" for index in range(8)]
        or fixture.get("instances_per_family")
        != ["train", "heldout_alpha", "heldout_beta"]
        or fixture.get("regions") != ["control_left", "control_right"]
    ):
        raise StrictContractError("control preflight denominator or shape changed")
    intermediate_per_region = sum(
        len(query.action_ids) - 1 for query in matrix.queries
    )
    state_count = len(fixture["regions"]) * (
        2 * len(matrix.queries) + intermediate_per_region
    ) + 2
    row_count = state_count * len(matrix.actions)
    if 8 * 3 != 24 or state_count != 40 or row_count != 200:
        raise StrictContractError(
            "control fixture no longer requires 24 carriers of 40 states and 200 rows"
        )
    if state_count > 128 or row_count > max_transition_rows:
        raise _PrerequisiteBlocked(
            "GLOBAL_PREFLIGHT_FROZEN_FIXTURE_SNAPSHOT_ROW_CAP_INCOMPATIBILITY"
        )
    return state_count, row_count


def _control_schedule(
    carrier: _TrainCarrier, *, method_id: str, adversarial: bool
) -> _Schedule:
    universe = _candidate_universe(carrier)
    if len(universe) != 8:
        raise StrictContractError("control candidate universe is not the frozen eight")
    if method_id == "baseline":
        selected = tuple(sorted(universe, key=lambda row: row.wire_bytes))
    elif method_id == "locality":
        partition = _canonical_partition(carrier.instance.initial_partition)
        covariance_memo: dict[tuple[tuple[str, ...], ...], _Covariance] = {}
        remaining = list(universe)
        output: list[_Candidate] = []
        while remaining:
            before = _carrier_covariance(
                carrier.instance, partition, covariance_memo
            ).trace
            scored: list[tuple[Fraction, int, bytes, _Candidate]] = []
            for candidate in remaining:
                after_partition = _candidate_refinement(
                    carrier.instance, partition, candidate
                )
                gain = before - _carrier_covariance(
                    carrier.instance, after_partition, covariance_memo
                ).trace
                if gain < 0:
                    raise StrictContractError("control refinement increased exact loss")
                score = gain / candidate.query.cost
                _exact(score)
                scored.append(
                    (
                        score if adversarial else -score,
                        candidate.query.cost,
                        candidate.wire_bytes,
                        candidate,
                    )
                )
            scored.sort(key=lambda row: (row[0], row[1], row[2]))
            candidate = scored[0][3]
            partition = _candidate_refinement(carrier.instance, partition, candidate)
            output.append(candidate)
            remaining.remove(candidate)
        selected = tuple(output)
    else:
        raise StrictContractError("control schedule method changed")
    return _Schedule(
        carrier.family_id, method_id, selected, _schedule_digest(selected)
    )


def _seal_control_schedules(
    fixture: dict[str, Any],
    locality: tuple[_Schedule, ...],
    baseline: tuple[_Schedule, ...],
) -> _ScheduleBarrier:
    family_ids = tuple(fixture["family_ids"])
    if (
        tuple(row.family_id for row in locality) != family_ids
        or tuple(row.family_id for row in baseline) != family_ids
        or any(row.method_id != "locality" for row in locality)
        or any(row.method_id != "baseline" for row in baseline)
    ):
        raise StrictContractError("control schedule barrier is incomplete")
    digest_map = {
        family_id: {
            "locality_schedule_sha256": locality[index].sha256,
            "baseline_schedule_sha256": baseline[index].sha256,
        }
        for index, family_id in enumerate(family_ids)
    }
    raw = canonical_contract_bytes(digest_map)
    return _ScheduleBarrier(raw, _sha_bytes(raw), _SCHEDULE_TOKEN)


def _open_control_heldout(
    fixture: dict[str, Any],
    heldout: tuple[_InstanceSpec, ...],
    barrier: _ScheduleBarrier,
) -> _OpenedHeldout:
    digest_map = _strict_json_object(
        barrier.digest_map_bytes,
        "control schedule digest map",
        require_canonical=True,
    )
    if (
        _sha_bytes(barrier.digest_map_bytes) != barrier.barrier_sha256
        or tuple(digest_map) != tuple(fixture["family_ids"])
        or len(heldout) != 16
    ):
        raise StrictContractError("control held-out opening preceded its barrier")
    return _OpenedHeldout(heldout, _OPEN_TOKEN)


def _seal_control_p0(
    opened: _OpenedHeldout,
    alpha_orbit: _VerifiedControlOrbit,
    beta_orbit: _VerifiedControlOrbit,
) -> _P0Barrier:
    by_instance = {
        member.spec.instance_id: member
        for orbit in (alpha_orbit, beta_orbit)
        for member in orbit.members
    }
    if len(by_instance) != 16 or set(by_instance) != {
        spec.instance_id for spec in opened.instances
    }:
        raise StrictContractError("control P0 verifier bindings are incomplete")
    rows: list[tuple[str, str, str, Fraction]] = []
    role_covariances: dict[str, tuple[_InstanceSpec, _Covariance]] = {}
    for spec in opened.instances:
        current = by_instance[spec.instance_id]
        if current.spec != spec:
            raise StrictContractError("control P0 member differs from opened carrier")
        role = spec.instance_id.rsplit("__", 1)[-1]
        if role not in {"heldout_alpha", "heldout_beta"}:
            raise StrictContractError("control P0 contains a non-heldout role")
        retained = role_covariances.get(role)
        if retained is None:
            covariance = _covariance(
                spec, _canonical_partition(spec.initial_partition)
            )
            role_covariances[role] = (spec, covariance)
        else:
            representative, covariance = retained
            _require_control_spec_isomorphism(representative, spec)
        rows.append(
            (spec.family_id, spec.instance_id, covariance.sha256, covariance.trace)
        )
    if len(rows) != 16:
        raise _PrerequisiteBlocked("GLOBAL_P0_DENOMINATOR_INCOMPLETE")
    wire = [
        {
            "family_id": family,
            "instance_id": instance,
            "covariance_sha256": digest,
            "trace_loss": _exact(trace).to_dict(),
        }
        for family, instance, digest, trace in rows
    ]
    return _P0Barrier(tuple(rows), _sha(wire), _P0_TOKEN)


def _require_control_schedule_isomorphism(
    source: _Schedule, target: _Schedule
) -> None:
    source_shape = tuple(
        (
            row.left_region_id,
            row.right_region_id,
            row.query,
        )
        for row in source.candidates
    )
    target_shape = tuple(
        (
            row.left_region_id,
            row.right_region_id,
            row.query,
        )
        for row in target.candidates
    )
    if source.method_id != target.method_id or source_shape != target_shape:
        raise StrictContractError("control schedule crossed a semantic orbit")


def _control_seed_misses(
    train_specs: tuple[_InstanceSpec, ...],
    heldout_specs: tuple[_InstanceSpec, ...],
    locality_schedules: tuple[_Schedule, ...],
) -> tuple[dict[str, Any], ...]:
    schedule_by_family = {row.family_id: row for row in locality_schedules}
    if len(schedule_by_family) != 8:
        raise StrictContractError("control seed audit lacks eight locality schedules")
    misses: list[dict[str, Any]] = []
    for spec in (*train_specs, *heldout_specs):
        partition = _canonical_partition(spec.initial_partition)
        schedule = schedule_by_family[spec.family_id]
        candidates = (
            schedule.candidates
            if spec.stratum == "train"
            else _substitute_schedule(schedule, spec)
        )
        for candidate in candidates:
            partition = _candidate_refinement(spec, partition, candidate)
        for left, right, query_id in spec.seeds:
            if any(left in block and right in block for block in partition):
                misses.append(
                    {
                        "family_id": spec.family_id,
                        "instance_id": spec.instance_id,
                        "left_region_id": left,
                        "right_region_id": right,
                        "query_id": query_id,
                    }
                )
    return tuple(misses)


def _control_result_object(
    matrix: _FrozenMatrix,
    fixture: dict[str, Any],
    *,
    variant_id: str,
    distinguishing_query_id: str | None,
    adversarial: bool,
    max_transition_rows: int,
) -> dict[str, Any]:
    train = _control_train_specs(
        fixture, variant_id, distinguishing_query_id
    )
    state_count, row_count = _control_global_preflight(
        matrix, fixture, max_transition_rows=max_transition_rows
    )
    train_orbit = _verified_control_orbit(
        matrix,
        train,
        role="train",
        opened=None,
        max_transition_rows=max_transition_rows,
    )
    carriers = tuple(_TrainCarrier(spec.family_id, spec, matrix.queries) for spec in train)
    locality = tuple(
        _control_schedule(carrier, method_id="locality", adversarial=adversarial)
        for carrier in carriers
    )
    baseline = tuple(
        _control_schedule(carrier, method_id="baseline", adversarial=False)
        for carrier in carriers
    )
    canonical_order = tuple(
        candidate.query.query_id for candidate in baseline[0].candidates
    )
    if canonical_order != tuple(
        fixture["canonical_query_order_for_the_sole_region_pair"]
    ) or any(
        tuple(candidate.query.query_id for candidate in row.candidates)
        != canonical_order
        for row in baseline
    ):
        raise StrictContractError("control baseline is not the frozen byte order")
    barrier = _seal_control_schedules(fixture, locality, baseline)
    heldout = _control_heldout_specs(
        fixture,
        variant_id,
        distinguishing_query_id,
        barrier,
    )
    opened = _open_control_heldout(fixture, heldout, barrier)
    alpha_specs = heldout[0::2]
    beta_specs = heldout[1::2]
    alpha_orbit = _verified_control_orbit(
        matrix,
        alpha_specs,
        role="heldout_alpha",
        opened=opened,
        max_transition_rows=max_transition_rows,
    )
    beta_orbit = _verified_control_orbit(
        matrix,
        beta_specs,
        role="heldout_beta",
        opened=opened,
        max_transition_rows=max_transition_rows,
    )
    p0 = _seal_control_p0(opened, alpha_orbit, beta_orbit)
    representative_alpha = alpha_orbit.representative
    representative_beta = beta_orbit.representative
    curve_pairs: dict[str, tuple[_InstanceCurve, _InstanceCurve]] = {}
    for schedules in (locality, baseline):
        representative_schedule = schedules[0]
        for schedule in schedules[1:]:
            _require_control_schedule_isomorphism(
                representative_schedule, schedule
            )
        curve_pairs[representative_schedule.method_id] = (
            _evaluate_instance(representative_alpha, representative_schedule, p0),
            _evaluate_instance(representative_beta, representative_schedule, p0),
        )
    locality_curve = tuple(
        (
            curve_pairs["locality"][0].covariances[t].trace
            + curve_pairs["locality"][1].covariances[t].trace
        )
        / 2
        for t in range(17)
    )
    baseline_curve = tuple(
        (
            curve_pairs["baseline"][0].covariances[t].trace
            + curve_pairs["baseline"][1].covariances[t].trace
        )
        / 2
        for t in range(17)
    )
    misses = _control_seed_misses(train, heldout, locality)
    disposition, reason = _classify_disposition(
        locality=locality_curve,
        baseline=baseline_curve,
        seed_miss_count=len(misses),
    )
    covariance_rows: list[dict[str, Any]] = []
    for method_id in ("locality", "baseline"):
        representative_pair = curve_pairs[method_id]
        representative_points = []
        for t in range(17):
            covariance = _mean_covariances(
                representative_pair[0].covariances[t],
                representative_pair[1].covariances[t],
            )
            representative_points.append(
                {
                    "t": t,
                    "covariance_sha256": covariance.sha256,
                    "trace_loss": _exact(covariance.trace).to_dict(),
                }
            )
        for family_id in fixture["family_ids"]:
            covariance_rows.append(
                {
                    "method_id": method_id,
                    "family_id": family_id,
                    "points": copy.deepcopy(representative_points),
                }
            )
    return {
        "schema_version": _CONTROL_RESULT_SCHEMA,
        "variant_id": variant_id,
        "disposition": disposition,
        "diagnostic_reason": reason,
        "preflight": {
            "declared_max_snapshot_transition_rows": max_transition_rows,
            "mechanically_required_snapshot_states": state_count,
            "mechanically_required_snapshot_transition_rows": row_count,
        },
        "schedule_barrier_sha256": barrier.barrier_sha256,
        "p0_sha256": p0.sha256,
        "p0_fixed_denominator": len(p0.rows),
        "seed_miss_count": len(misses),
        "overall_curves": {
            "locality": [_exact(value).to_dict() for value in locality_curve],
            "baseline": [_exact(value).to_dict() for value in baseline_curve],
        },
        "family_covariances": covariance_rows,
    }


def _control_result_bytes(
    variant_id: str,
    *,
    max_transition_rows: int = 200,
) -> bytes:
    matrix = _load_frozen_matrix()
    fixture, _registered = _strict_reachability_fixture(matrix)
    variants = {
        "gain_reachable": ("q_reveal", False),
        "no_clear_gain_reachable": (None, False),
        "degraded_reachable": ("q_a_b", True),
    }
    if variant_id not in variants:
        raise StrictContractError("control result variant is not executable")
    query_id, adversarial = variants[variant_id]
    raw = canonical_contract_bytes(
        _control_result_object(
            matrix,
            fixture,
            variant_id=variant_id,
            distinguishing_query_id=query_id,
            adversarial=adversarial,
            max_transition_rows=max_transition_rows,
        )
    )
    if len(raw) > _RESULT_WIRE_CAP:
        raise StrictContractError("control result exceeds its one-MiB cap")
    return raw


def _verify_control_result_bytes(raw: bytes, variant_id: str) -> bytes:
    supplied = _strict_json_object(
        raw, "reachability control result", require_canonical=True
    )
    _exact_fields(
        supplied,
        {
            "schema_version",
            "variant_id",
            "disposition",
            "diagnostic_reason",
            "preflight",
            "schedule_barrier_sha256",
            "p0_sha256",
            "p0_fixed_denominator",
            "seed_miss_count",
            "overall_curves",
            "family_covariances",
        },
        "reachability control result",
    )
    if (
        supplied["schema_version"] != _CONTROL_RESULT_SCHEMA
        or supplied["variant_id"] != variant_id
        or type(supplied["family_covariances"]) is not list
        or len(supplied["family_covariances"]) != 16
    ):
        raise StrictContractError("reachability control result shape changed")
    for family_row in supplied["family_covariances"]:
        _exact_fields(
            family_row,
            {"method_id", "family_id", "points"},
            "control family covariance",
        )
        if type(family_row["points"]) is not list or len(family_row["points"]) != 17:
            raise StrictContractError("control covariance curve is incomplete")
        for t, point in enumerate(family_row["points"]):
            _exact_fields(
                point,
                {"t", "covariance_sha256", "trace_loss"},
                "control covariance point",
            )
            if (
                point["t"] != t
                or type(point["covariance_sha256"]) is not str
                or re.fullmatch(r"[0-9A-F]{64}", point["covariance_sha256"])
                is None
            ):
                raise StrictContractError("control covariance point is invalid")
            ExactRational.from_dict(point["trace_loss"])
    expected = _control_result_bytes(variant_id)
    expected_object = _strict_json_object(
        expected, "recomputed reachability control result", require_canonical=True
    )
    supplied_digests = tuple(
        point["covariance_sha256"]
        for family_row in supplied["family_covariances"]
        for point in family_row["points"]
    )
    expected_digests = tuple(
        point["covariance_sha256"]
        for family_row in expected_object["family_covariances"]
        for point in family_row["points"]
    )
    if supplied_digests != expected_digests:
        raise StrictContractError("RESULT_COVARIANCE_SHA256_MISMATCH")
    if raw != expected:
        raise StrictContractError("reachability control differs from full recomputation")
    return expected


def _reachability_control_audit() -> tuple[
    dict[str, tuple[str, str | None]], dict[str, bytes]
]:
    matrix = _load_frozen_matrix()
    fixture, registered = _strict_reachability_fixture(matrix)
    controls: dict[str, tuple[str, str | None]] = {}
    valid_results: dict[str, bytes] = {}
    for variant_id in (
        "gain_reachable",
        "no_clear_gain_reachable",
        "degraded_reachable",
    ):
        raw = _control_result_bytes(variant_id)
        valid_results[variant_id] = raw
        result = _strict_json_object(
            raw, f"{variant_id} control result", require_canonical=True
        )
        controls[variant_id] = (result["disposition"], result["diagnostic_reason"])

    try:
        _control_global_preflight(
            matrix, fixture, max_transition_rows=199
        )
    except _PrerequisiteBlocked as exc:
        controls["prerequisite_blocked_reachable"] = _classify_disposition(
            locality=(),
            baseline=(),
            seed_miss_count=0,
            prerequisite_failure=str(exc),
        )
    else:
        raise StrictContractError("199-row control did not block the 200-row fixture")

    gain = _strict_json_object(
        valid_results["gain_reachable"],
        "valid gain reachability result",
        require_canonical=True,
    )
    point = gain["family_covariances"][0]["points"][0]
    digest = point["covariance_sha256"]
    point["covariance_sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
    mutated = canonical_contract_bytes(gain)
    try:
        _verify_control_result_bytes(mutated, "gain_reachable")
    except StrictContractError as exc:
        if str(exc) != "RESULT_COVARIANCE_SHA256_MISMATCH":
            raise
        controls["execution_failed_reachable"] = _classify_disposition(
            locality=(),
            baseline=(),
            seed_miss_count=0,
            execution_failure=str(exc),
        )
    else:
        raise StrictContractError("mutated covariance digest passed strict verification")

    if {name: row[0] for name, row in controls.items()} != registered:
        raise StrictContractError("reachability controls do not match the frozen sum")
    return controls, valid_results


def _reachability_control_dispositions() -> dict[str, tuple[str, str | None]]:
    controls, _valid_results = _reachability_control_audit()
    return controls


def _result_object(matrix: _FrozenMatrix | None = None) -> dict[str, Any]:
    if matrix is None:
        matrix = _load_frozen_matrix()
    elif type(matrix) is not _FrozenMatrix:
        raise StrictContractError("result construction requires a frozen matrix")
    locality_schedules, baseline_schedules, verified_train = _build_train_schedules(
        matrix
    )
    barrier = _seal_schedules(locality_schedules, baseline_schedules)
    opened = _open_heldout(matrix, barrier)
    p0, verified_heldout = _seal_p0(matrix, opened)
    schedule_maps = (
        {row.family_id: row for row in locality_schedules},
        {row.family_id: row for row in baseline_schedules},
    )
    curves: list[_InstanceCurve] = []
    for method_map in schedule_maps:
        for verified in verified_heldout:
            curves.append(
                _evaluate_instance(verified, method_map[verified.spec.family_id], p0)
            )
    curve_tuple = tuple(curves)
    _verify_heldout_public_reports(
        matrix,
        verified_heldout,
        locality_schedules,
        curve_tuple,
    )
    family_curves = _family_curve_rows(curve_tuple)
    locality_overall = _overall_curve(family_curves, "locality")
    baseline_overall = _overall_curve(family_curves, "baseline")
    locality_aulc = sum(locality_overall[:16])
    baseline_aulc = sum(baseline_overall[:16])
    family_deltas = tuple(
        sum(
            _family_loss(family_curves, "baseline", family_id, t)
            - _family_loss(family_curves, "locality", family_id, t)
            for t in range(16)
        )
        for family_id in _FAMILY_IDS
    )
    lower, upper = _bootstrap(family_deltas)
    misses = _seed_misses(
        verified_train, verified_heldout, locality_schedules, curve_tuple
    )
    no_worse = all(
        locality_overall[t] <= baseline_overall[t] for t in range(17)
    )
    strict_gain = any(
        locality_overall[t] < baseline_overall[t] for t in range(17)
    )
    disposition, diagnostic_reason = _classify_disposition(
        locality=locality_overall,
        baseline=baseline_overall,
        seed_miss_count=len(misses),
    )
    if no_worse != all(
        locality_overall[t] <= baseline_overall[t] for t in range(17)
    ) or strict_gain != any(
        locality_overall[t] < baseline_overall[t] for t in range(17)
    ):
        raise StrictContractError("paired disposition predicates changed")
    instance_rows = _instance_checkpoint_rows(curve_tuple)
    family_rows = _family_checkpoint_rows(family_curves, instance_rows)
    schedule_map = _strict_json_object(
        barrier.digest_map_bytes, "schedule digest map", require_canonical=True
    )
    reports = tuple(
        {
            "instance_id": verified.spec.instance_id,
            "snapshot_sha256": verified.snapshot_sha256,
            "verified_partition_certificate_sha256": verified.certificate_sha256,
            "terminal_projection_sha256": _sha(
                [
                    {
                        "region_id": region,
                        "query_id": query,
                        "verified_block_index": block,
                    }
                    for region, query, block in verified.terminal_blocks
                ]
            ),
            "public_locality_report_sha256": _sha(
                _PUBLIC_REPORT_CACHE[verified.spec.instance_id].to_dict()
            ),
        }
        for verified in (*verified_train, *verified_heldout)
    )
    result = {
        "schema_version": _RESULT_SCHEMA,
        "matrix_id": _MATRIX_ID,
        "matrix_raw_sha256": _MATRIX_SHA256,
        "matrix_canonical_sha256": matrix.canonical_sha256,
        "evidence_scope": "synthetic_development",
        "evidence_tier": "NOMINAL_DIAGNOSTIC_ONLY",
        "hard_eligible": False,
        "disposition": disposition,
        "diagnostic_reason": diagnostic_reason,
        "action_catalog_sha256": _sha(
            [action.to_dict() for action in matrix.actions]
        ),
        "query_catalog_sha256": _sha(
            [query.full_wire for query in matrix.queries]
        ),
        "schedule_digest_map": schedule_map,
        "schedule_barrier_sha256": barrier.barrier_sha256,
        "schedules": list(_schedule_rows(locality_schedules, baseline_schedules)),
        "global_p0_barrier": {
            "sealed_instance_count": 16,
            "fixed_denominator": 16,
            "p0_rows_sha256": p0.sha256,
        },
        "verified_snapshot_bindings": list(reports),
        "instance_checkpoints": list(instance_rows),
        "family_checkpoints": list(family_rows),
        "family_curves": list(_family_curve_wire_rows(family_curves)),
        "overall_curves": {
            "locality": [_exact(value).to_dict() for value in locality_overall],
            "baseline": [_exact(value).to_dict() for value in baseline_overall],
            "coverage_numerators": [16] * 17,
            "fixed_denominator": 16,
            "locality_abstention_counts": [0] * 17,
            "baseline_abstention_counts": [0] * 17,
            "locality_censor_counts": [0] * 17,
            "baseline_censor_counts": [0] * 17,
        },
        "aulc": {
            "included_t_values": list(range(16)),
            "locality": _exact(locality_aulc).to_dict(),
            "baseline": _exact(baseline_aulc).to_dict(),
            "baseline_minus_locality": _exact(
                baseline_aulc - locality_aulc
            ).to_dict(),
            "family_baseline_minus_locality": [
                _exact(value).to_dict() for value in family_deltas
            ],
        },
        "cluster_bootstrap_diagnostic": {
            "seed": 2_026_071_701,
            "replicates": 10_000,
            "lower_order_statistic_zero_based": 249,
            "upper_order_statistic_zero_based": 9749,
            "lower": _exact(lower).to_dict(),
            "upper": _exact(upper).to_dict(),
            "may_change_primary_disposition": False,
        },
        "seed_audit": {
            "seeded_pair_count": sum(
                len(verified.spec.seeds)
                for verified in (*verified_train, *verified_heldout)
            ),
            "all_seeded_pairs_separated": not misses,
            "misses": list(misses),
        },
        "resource_receipt": {
            "execution_lane": "WINDOWS_CPU_ONLY",
            "candidate_observation_budget": 16,
            "heldout_instance_count": 16,
            "wire_cap_bytes": _RESULT_WIRE_CAP,
        },
    }
    # Touch the public sum type so a future incompatible enum cannot silently
    # reinterpret the frozen wire.  Exact member spelling is checked by value.
    if disposition not in {member.value for member in LocalityResultDisposition}:
        raise StrictContractError("result disposition is outside the public L0 sum")
    return result


@lru_cache(maxsize=1)
def build_u15_l0_result_bytes() -> bytes:
    """Recompute the complete frozen public-synthetic result."""

    raw = canonical_contract_bytes(_result_object())
    if len(raw) > _RESULT_WIRE_CAP:
        raise StrictContractError("L0 result exceeds its one-MiB cap")
    return raw


def _recompute_u15_l0_result_bytes_from_source() -> bytes:
    """Re-read source, rebuild snapshots, and independently check proof witnesses."""

    witnesses = {
        instance_id: (cached.spec, cached.verified.certificate)
        for instance_id, cached in _VERIFIED_INSTANCE_CACHE.items()
        if type(cached) is _VerifiedInstance
    }
    _load_frozen_matrix.cache_clear()
    _VERIFIED_INSTANCE_CACHE.clear()
    _CONTROL_ORBIT_CACHE.clear()
    _CONTROL_QUERY_TEMPLATE_BYTES.clear()
    _CONTROL_QUERY_TEMPLATE_ENVIRONMENTS.clear()
    _CONTROL_EXPECTED_VOCABULARIES.clear()
    _CONTROL_EXPECTED_SEMANTICS.clear()
    _CONTROL_QUERY_BINDING_CACHE.clear()
    _locality_cegar_core._clear_verified_observation_source_memo()
    _open_heldout.cache_clear()
    _covariance.cache_clear()
    _build_train_schedules.cache_clear()
    _evaluate_instance.cache_clear()
    _seal_p0.cache_clear()
    _bootstrap.cache_clear()
    _PUBLIC_REPORT_CACHE.clear()
    _RECOMPUTE_CERTIFICATE_WITNESSES.clear()
    _RECOMPUTE_CERTIFICATE_WITNESSES.update(witnesses)
    try:
        matrix = _parse_matrix_bytes(_MATRIX_PATH.read_bytes())
        raw = canonical_contract_bytes(_result_object(matrix))
    finally:
        _RECOMPUTE_CERTIFICATE_WITNESSES.clear()
    if len(raw) > _RESULT_WIRE_CAP:
        raise StrictContractError("L0 result exceeds its one-MiB cap")
    return raw


def verify_u15_l0_result_bytes(raw: bytes) -> bytes:
    """Strict-parse and fully recompute one result wire."""

    supplied = _strict_json_object(raw, "L0 result", require_canonical=True)
    if supplied.get("schema_version") != _RESULT_SCHEMA:
        raise StrictContractError("L0 result schema changed")
    expected = _recompute_u15_l0_result_bytes_from_source()
    if raw != expected:
        raise StrictContractError("L0 result differs from full frozen recomputation")
    return expected
