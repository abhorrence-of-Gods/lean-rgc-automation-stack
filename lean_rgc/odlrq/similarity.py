from __future__ import annotations

"""Strict finite-level S0 similarity certificates.

The hard channel in this module is exact rational arithmetic over one declared
finite synthetic universe.  The ME0 input is retained only by the predictive
channel.  Nothing in this module promotes a nominal MaxEnt result to safety
evidence or makes an infinite-cutoff claim.
"""

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math
import re
import struct
from typing import Any, Mapping, Sequence

from .contracts import ExactRational, StrictContractError, canonical_contract_bytes
from .envelope import FiberEnvelope, verify_fiber_envelope
from .maxent import MaxEntProblem, MaxEntResult, MaxEntStatus, verify_maxent_result
from .selection import CertifiedSupportToken


# Mechanical identity completion of authority commit 48e8aa4.
S0_AUTHORITY_COMMIT_SHA = "48e8aa4b2a50d93367027d3c924944c160ef806a"
S0_AUTHORITY_PARENT_SHA = "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d"
S0_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md"
)
S0_AUTHORITY_DOCUMENT_BLOB_SHA = "f137a5c4f8411e2b68d6c88d6a6d09683a766aa2"
S0_AUTHORITY_CI_RUN_ID = "29557149691"
S0_AUTHORITY_CI_JOB_ID = "87811636093"

_ACCEPTED_E1_COMMIT = "6fb35aa229fc60e2220cbb68c1e7fff2ce64f199"
_ACCEPTED_E1_TREE = "b3fc7f21b6420e718eb954be0c1b5affca65d263"
_ACCEPTED_E2_COMMIT = "7a8b28872439dd61d40174c2500c5990790002be"
_ACCEPTED_E2_TREE = "d54ed9fab52da4929843fabdeb3c1e1920994f6a"
_ACCEPTED_ME0_COMMIT = "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d"
_ACCEPTED_ME0_TREE = "a3b3513ca93430c9f15e5bd90888e81b0af1ff9c"

_E1_ENVELOPE_SHA = "D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6"
_E1_ENVELOPE_BYTES = 16_351
_E2_M0_ENVELOPE_SHA = "9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C"
_E2_M0_ENVELOPE_BYTES = 16_578
_E2_MANIFEST_SHA = "327DDC3DBD63C049A1B16B570B81F5DDECCE1B8C3C7F83734609C83B12501D9A"
_E2_P1_SHA = "6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11"
_E2_P2_SHA = "BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D"
_E2_RETURN_SHA = "95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46"
_E2_SUPPORT_SHA = "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"
_PRIMITIVE_UNIVERSE_SHA = "9FA1D0431DF67EEDD0661EE70A0836A60ECF6153488EDE21699DD24867722FEC"
_HARD_AUTHORITY_TUPLE_SHA = "840B46E6743EF531DC3C7266CEA3BE3D2A731959A8F9E808207372E17CCC97F0"

_ME0_PROBLEM_WIRE_SHA = "F055C10309DB4AFCA1A140ECFE3FAAF3AF2BF11F7B25F6366F92667446899B7B"
_ME0_PROBLEM_CORE_SHA = "20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C"
_ME0_RESULT_WIRE_SHA = "DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3"
_ME0_ROW_TABLE_SHA = "75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76"
_ME0_PROBLEM_BYTES = 3_308
_ME0_RESULT_BYTES = 4_177
_ME0_RUNTIME_SHA = "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
_S0_RUNTIME_SHA = "88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9"

_EVIDENCE_SCOPE = "declared_synthetic"
_DOMAIN_SCOPE = "declared_finite_totalized_snapshot_only"
_NORM_ID = "weighted_l1_exact_rational_v1"
_FRAME_ID = "u24.e2.declared_square.observation_frame.v1"
_DOMAIN_ID = "u24.s0.declared_finite_similarity_domain.v1"
_ME0_TIER = "NOMINAL_MODEL_SELECTION_ONLY"
_FROZEN_PRIMITIVE_IDS = (
    "u24_s0_t0_node0",
    "u24_s0_t1_node1_edge01",
    "u24_s0_t2_edge11",
    "u24_s0_t3_ghost_return",
)

_LEVEL_SCHEMA = "odlrq.s0.approximation-level-id.v1"
_PRIMITIVE_ROW_SCHEMA = "odlrq.s0.primitive-target-row.v1"
_PRIMITIVE_UNIVERSE_SCHEMA = "odlrq.s0.primitive-universe.v2"
_COVERAGE_SCHEMA = "odlrq.s0.counted-coverage-witness.v1"
_HARD_REFERENCE_SCHEMA = "odlrq.s0.declared-hard-authority-reference.v1"
_ME0_REFERENCE_SCHEMA = "odlrq.s0.declared-me0-result-reference.v1"
_LPLUS_SCHEMA = "odlrq.s0.declared-synthetic-lplus-token.v1"
_TARGET_RESIDUAL_SCHEMA = "odlrq.s0.target-residual-bound.v1"
_MEASURE_SCHEMA = "odlrq.s0.global-measure.v1"
_PREDICTIVE_DISTANCE_SCHEMA = "odlrq.s0.predictive-distance.v1"
_POSITIVE_DISTANCE_SCHEMA = "odlrq.s0.positive-distance.v1"
_RADIUS_SCHEMA = "odlrq.s0.radius-morphism.v1"
_WORD_DEPTH_SCHEMA = "odlrq.s0.word-depth-morphism.v1"
_GRANULARITY_SCHEMA = "odlrq.s0.granularity-morphism.v1"
_LOCAL_TOWER_SCHEMA = "odlrq.s0.local-tower.v1"
_PREDICTIVE_TRANSPORT_SCHEMA = "odlrq.s0.predictive-transport.v1"
_POSITIVE_TRANSPORT_SCHEMA = "odlrq.s0.positive-transport.v1"
_REMAINDER_SCHEMA = "odlrq.s0.finite-remainder.v1"
_SIMILARITY_SCHEMA = "odlrq.s0.similarity-certificate.v1"
_POSITIVE_CORE_SCHEMA = "odlrq.s0.positive-core-projection.v1"
_PREDICTIVE_CORE_SCHEMA = "odlrq.s0.predictive-core-projection.v1"
_FIXTURE_SCHEMA = "odlrq.s0.declared-similarity-fixture.v1"
_CASE_SCHEMA = "odlrq.s0.similarity-case-result.v1"

_MAX_WIRE_DEPTH = 16
_MAX_WIRE_NODES = 32_768
_MAX_WIRE_BYTES = 1_048_576
_MAX_LEVELS = 8
_MAX_NODES = 32
_MAX_EDGES = 128
_MAX_PRIMITIVES = 64
_MAX_COVERAGE_IDS = 256
_MAX_CASE_ROWS = 128
_MAX_MEASURES = 64
_MAX_MORPHISMS = 7
_MAX_MATRIX_CELLS = 32_768
_MAX_TOTAL_MATRIX_CELLS = 131_072
_MAX_INPUT_BITS = 256
_MAX_INTERMEDIATE_BITS = 4_096
_MAX_ID_BYTES = 128
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9A-F]{64}\Z")
_CANONICAL_FLOAT = re.compile(
    r"(?:0|-[1-9][0-9]*(?:\.[0-9]+)?|[1-9][0-9]*(?:\.[0-9]+)?|"
    r"-?0\.[0-9]+)(?:e[+-]?[0-9]+)?\Z"
)

_COVERAGE_SEAL = object()
_HARD_REFERENCE_SEAL = object()
_HARD_BINDING_SEAL = object()
_ME0_REFERENCE_SEAL = object()
_ME0_BINDING_SEAL = object()


def _object(value: Any, fields: Sequence[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StrictContractError(f"{where} must be an exact object")
    expected = set(fields)
    if set(value) != expected:
        raise StrictContractError(
            f"{where} fields mismatch; missing={sorted(expected-set(value))}, "
            f"unknown={sorted(set(value)-expected)}"
        )
    return value


def _array(value: Any, where: str, *, maximum: int) -> list[Any]:
    if type(value) is not list or len(value) > maximum:
        raise StrictContractError(f"{where} must be an exact bounded array")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} must be strict UTF-8") from exc
    return value


def _identifier(value: Any, where: str) -> str:
    result = _string(value, where)
    if len(result.encode("utf-8")) > _MAX_ID_BYTES or not result.isascii():
        raise StrictContractError(f"{where} must be ASCII and at most 128 bytes")
    return result


def _fixed(value: Any, expected: str, where: str) -> str:
    result = _string(value, where)
    if result != expected:
        raise StrictContractError(f"{where} must equal {expected!r}")
    return result


def _digest(value: Any, where: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be canonical uppercase SHA-256")
    return value


def _commit(value: Any, expected: str, where: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None or value != expected:
        raise StrictContractError(f"{where} does not match frozen commit")
    return value


def _exact_int(value: Any, where: str, *, minimum: int = 0, maximum: int = 2**63-1) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise StrictContractError(f"{where} is outside its exact integer bounds")
    return value


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _bounded_wire_walk(value: Any, where: str) -> None:
    nodes = 0
    active: set[int] = set()

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        if depth > _MAX_WIRE_DEPTH:
            raise StrictContractError(f"{where} exceeds wire depth")
        nodes += 1
        if nodes > _MAX_WIRE_NODES:
            raise StrictContractError(f"{where} exceeds wire node cap")
        if item is None or type(item) in (bool, int, str):
            if type(item) is int and not (-(2**63) <= item < 2**63):
                raise StrictContractError(f"{where} integer is outside signed64")
            if type(item) is str:
                if len(item) > _MAX_WIRE_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap string")
                try:
                    encoded_item=item.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise StrictContractError(f"{where} contains invalid UTF-8") from exc
                if len(encoded_item)>_MAX_WIRE_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap UTF-8 string")
            return
        if type(item) not in (dict, list):
            raise StrictContractError(f"{where} is outside strict JSON")
        identity = id(item)
        if identity in active:
            raise StrictContractError(f"{where} contains a cycle")
        active.add(identity)
        if type(item) is list:
            if len(item) > _MAX_COVERAGE_IDS:
                raise StrictContractError(f"{where} contains an over-cap array")
            for child in item:
                visit(child, depth + 1)
        else:
            if len(item) > 128:
                raise StrictContractError(f"{where} object has too many keys")
            for key, child in item.items():
                if type(key) is not str:
                    raise StrictContractError(f"{where} key must be an exact string")
                if len(key) > _MAX_WIRE_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap key")
                try:
                    encoded_key=key.encode("utf-8",errors="strict")
                except UnicodeEncodeError as exc:
                    raise StrictContractError(f"{where} contains invalid UTF-8 key") from exc
                if len(encoded_key)>_MAX_WIRE_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap UTF-8 key")
                nodes += 1
                if nodes > _MAX_WIRE_NODES:
                    raise StrictContractError(f"{where} exceeds wire node cap")
                visit(child, depth + 1)
        active.remove(identity)

    visit(value, 0)
    try:
        encoded = canonical_contract_bytes(value)
    except Exception as exc:
        if isinstance(exc, StrictContractError):
            raise
        raise StrictContractError(f"{where} is not canonical JSON") from exc
    if len(encoded) > _MAX_WIRE_BYTES:
        raise StrictContractError(f"{where} exceeds one MiB")


def _rational(value: Any, where: str, *, nonnegative: bool = False) -> ExactRational:
    if type(value) is not ExactRational or ExactRational.from_dict(value.to_dict()) != value:
        raise StrictContractError(f"{where} must be reduced ExactRational")
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > _MAX_INPUT_BITS:
        raise StrictContractError(f"{where} exceeds 256-bit input cap")
    if nonnegative and value.numerator < 0:
        raise StrictContractError(f"{where} must be nonnegative")
    return value


def _derived(value: Fraction, where: str) -> ExactRational:
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > _MAX_INTERMEDIATE_BITS:
        raise StrictContractError(f"{where} exceeds 4096-bit intermediate cap")
    result = ExactRational(value.numerator, value.denominator)
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > _MAX_INTERMEDIATE_BITS:
        raise StrictContractError(f"{where} normalized output exceeds cap")
    return result


def _fraction(value: ExactRational, where: str) -> Fraction:
    return Fraction(_rational(value, where).numerator, value.denominator)


def _add(left: ExactRational, right: ExactRational, where: str) -> ExactRational:
    return _derived(_fraction(left, where) + _fraction(right, where), where)


def _float_bits(value: float) -> bytes:
    return struct.pack(">d", value)


def _float_text(value: Any, where: str) -> str:
    """Format an internally derived finite binary64 value.

    Public contract boundaries must use :func:`_parse_float` and therefore
    reject raw ``float`` objects.  Keeping this formatter separate prevents a
    Python value from silently becoming an authority-bearing wire scalar.
    """
    if type(value) is str:
        return _parse_float(value, where)[0]
    if type(value) is not float or not math.isfinite(value):
        raise StrictContractError(f"{where} must be finite binary64")
    if value == 0.0:
        value = 0.0
    text = format(value, ".17g").replace("E", "e")
    decoded = float(text)
    if _float_bits(decoded) != _float_bits(value):
        raise StrictContractError(f"{where} is not roundtrip binary64")
    return text


def _parse_float(value: Any, where: str) -> tuple[str, float]:
    if type(value) is not str or _CANONICAL_FLOAT.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be canonical binary64 text")
    result = float(value)
    if not math.isfinite(result) or (result == 0.0 and value.startswith("-")):
        raise StrictContractError(f"{where} is nonfinite or negative zero")
    text = format(result, ".17g").replace("E", "e")
    if text != value:
        raise StrictContractError(f"{where} is not decode-reencode canonical")
    return value, result


def _exact_tuple(value: Any, expected: type[Any], where: str, maximum: int) -> tuple[Any, ...]:
    if type(value) is not tuple or len(value) > maximum:
        raise StrictContractError(f"{where} must be an exact bounded tuple")
    if any(type(item) is not expected for item in value):
        raise StrictContractError(f"{where} contains a wrong exact type")
    return value


@dataclass(frozen=True)
class ApproximationLevelId:
    frame_id: str
    domain_id: str
    radius: int
    word_depth: int
    granularity: int

    def __post_init__(self) -> None:
        if type(self) is not ApproximationLevelId:
            raise StrictContractError("ApproximationLevelId subclasses are forbidden")
        _fixed(self.frame_id, _FRAME_ID, "level frame_id")
        _fixed(self.domain_id, _DOMAIN_ID, "level domain_id")
        for name in ("radius", "word_depth", "granularity"):
            _exact_int(getattr(self, name), f"level {name}", minimum=1)

    @property
    def level_id(self) -> str:
        return f"L{self.radius-1 + self.word_depth-1 + self.granularity-1}"

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": _LEVEL_SCHEMA, "frame_id": self.frame_id,
                "domain_id": self.domain_id, "radius": self.radius,
                "word_depth": self.word_depth, "granularity": self.granularity}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApproximationLevelId":
        if cls is not ApproximationLevelId:
            raise StrictContractError("polymorphic level parsing is forbidden")
        _bounded_wire_walk(value, "ApproximationLevelId")
        obj = _object(value, ("schema_version","frame_id","domain_id","radius","word_depth","granularity"), "ApproximationLevelId")
        _fixed(obj["schema_version"], _LEVEL_SCHEMA, "level schema")
        result = cls(obj["frame_id"], obj["domain_id"], obj["radius"], obj["word_depth"], obj["granularity"])
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("ApproximationLevelId wire is not canonical")
        return result


@dataclass(frozen=True)
class PrimitiveTargetRow:
    primitive_id: str
    node_load: tuple[ExactRational, ...]
    edge_load: tuple[ExactRational, ...]
    target_residual: ExactRational

    def __post_init__(self) -> None:
        if type(self) is not PrimitiveTargetRow:
            raise StrictContractError("PrimitiveTargetRow subclasses are forbidden")
        _identifier(self.primitive_id, "primitive_id")
        if type(self.node_load) is not tuple or len(self.node_load) != 2:
            raise StrictContractError("primitive node_load must have two entries")
        if type(self.edge_load) is not tuple or len(self.edge_load) != 3:
            raise StrictContractError("primitive edge_load must have three entries")
        for index, value in enumerate(self.node_load + self.edge_load):
            _rational(value, f"primitive load {index}", nonnegative=True)
        _rational(self.target_residual, "primitive target residual", nonnegative=True)

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": _PRIMITIVE_ROW_SCHEMA, "primitive_id": self.primitive_id,
                "node_load": [x.to_dict() for x in self.node_load],
                "edge_load": [x.to_dict() for x in self.edge_load],
                "target_residual": self.target_residual.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrimitiveTargetRow":
        if cls is not PrimitiveTargetRow:
            raise StrictContractError("polymorphic primitive parsing is forbidden")
        _bounded_wire_walk(value, "PrimitiveTargetRow")
        obj = _object(value, ("schema_version","primitive_id","node_load","edge_load","target_residual"), "PrimitiveTargetRow")
        _fixed(obj["schema_version"], _PRIMITIVE_ROW_SCHEMA, "primitive schema")
        nodes = _array(obj["node_load"], "node_load", maximum=2)
        edges = _array(obj["edge_load"], "edge_load", maximum=3)
        if len(nodes) != 2 or len(edges) != 3:
            raise StrictContractError("primitive load dimensions changed")
        result = cls(obj["primitive_id"], tuple(ExactRational.from_dict(x) for x in nodes),
                     tuple(ExactRational.from_dict(x) for x in edges),
                     ExactRational.from_dict(obj["target_residual"]))
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("PrimitiveTargetRow wire is not canonical")
        return result


def _primitive_universe(rows: tuple[PrimitiveTargetRow, ...]) -> dict[str, Any]:
    _exact_tuple(rows, PrimitiveTargetRow, "primitive rows", _MAX_PRIMITIVES)
    ids = tuple(row.primitive_id for row in rows)
    if len(rows) != 4 or ids != _FROZEN_PRIMITIVE_IDS:
        raise StrictContractError("primitive universe order changed")
    wire = {"schema_version": _PRIMITIVE_UNIVERSE_SCHEMA, "node_ids": ["n0","n1"],
            "edge_orientation": "unordered_canonical_pair_v1",
            "edge_ids": [["n0","n0"],["n0","n1"],["n1","n1"]],
            "rows": [row.to_dict() for row in rows]}
    if _sha256(wire) != _PRIMITIVE_UNIVERSE_SHA:
        raise StrictContractError("primitive universe does not match frozen authority")
    return wire


def _frozen_primitive_rows() -> tuple[PrimitiveTargetRow, ...]:
    z, o, t, e = ExactRational(0), ExactRational(1), ExactRational(2), ExactRational(1,8)
    return (
        PrimitiveTargetRow("u24_s0_t0_node0", (o,z), (o,z,z), e),
        PrimitiveTargetRow("u24_s0_t1_node1_edge01", (z,t), (z,o,z), e),
        PrimitiveTargetRow("u24_s0_t2_edge11", (z,z), (z,z,t), e),
        PrimitiveTargetRow("u24_s0_t3_ghost_return", (z,z), (z,z,z), e),
    )


@dataclass(frozen=True, init=False)
class CountedCoverageWitness:
    ordered_universe_ids: tuple[str, ...]
    covered_ids: tuple[str, ...]
    covered_count: int
    universe_count: int
    universe_ids_sha256: str
    covered_ids_sha256: str
    complete: bool
    _construction_seal: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("coverage witness requires the counted constructor")

    def __post_init__(self) -> None:
        if type(self) is not CountedCoverageWitness or self._construction_seal is not _COVERAGE_SEAL:
            raise StrictContractError("coverage witness construction seal changed")
        if self.covered_count != len(self.covered_ids) or self.universe_count != len(self.ordered_universe_ids):
            raise StrictContractError("coverage counts changed")
        if (
            len(self.ordered_universe_ids) != len(set(self.ordered_universe_ids))
            or len(self.covered_ids) != len(set(self.covered_ids))
        ):
            raise StrictContractError("coverage IDs duplicate")
        expected_covered = tuple(
            item for item in self.ordered_universe_ids if item in set(self.covered_ids)
        )
        if self.covered_ids != expected_covered or any(
            item not in self.ordered_universe_ids for item in self.covered_ids
        ):
            raise StrictContractError("coverage IDs are unknown or reordered")
        if self.universe_ids_sha256 != _sha256(list(self.ordered_universe_ids)) or self.covered_ids_sha256 != _sha256(list(self.covered_ids)):
            raise StrictContractError("coverage digest changed")
        if self.complete is not (self.covered_ids == self.ordered_universe_ids):
            raise StrictContractError("coverage completeness changed")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": _COVERAGE_SCHEMA,
                "ordered_universe_ids": list(self.ordered_universe_ids),
                "covered_ids": list(self.covered_ids), "covered_count": self.covered_count,
                "universe_count": self.universe_count,
                "universe_ids_sha256": self.universe_ids_sha256,
                "covered_ids_sha256": self.covered_ids_sha256, "complete": self.complete}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CountedCoverageWitness":
        if cls is not CountedCoverageWitness:
            raise StrictContractError("polymorphic coverage parsing is forbidden")
        _bounded_wire_walk(value, "CountedCoverageWitness")
        obj = _object(value, ("schema_version","ordered_universe_ids","covered_ids","covered_count","universe_count","universe_ids_sha256","covered_ids_sha256","complete"), "CountedCoverageWitness")
        _fixed(obj["schema_version"], _COVERAGE_SCHEMA, "coverage schema")
        result = make_counted_coverage_witness(
            ordered_universe_ids=tuple(_identifier(x,"universe ID") for x in _array(obj["ordered_universe_ids"],"ordered_universe_ids",maximum=_MAX_COVERAGE_IDS)),
            covered_ids=tuple(_identifier(x,"covered ID") for x in _array(obj["covered_ids"],"covered_ids",maximum=_MAX_COVERAGE_IDS)),
        )
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("coverage wire does not match recomputation")
        return result


def make_counted_coverage_witness(*, ordered_universe_ids: Any, covered_ids: Any) -> CountedCoverageWitness:
    if type(ordered_universe_ids) is not tuple or type(covered_ids) is not tuple:
        raise StrictContractError("coverage inputs must be exact tuples")
    if not ordered_universe_ids or len(ordered_universe_ids) > _MAX_COVERAGE_IDS:
        raise StrictContractError("coverage universe is empty or over cap")
    universe = tuple(_identifier(x,"universe ID") for x in ordered_universe_ids)
    covered = tuple(_identifier(x,"covered ID") for x in covered_ids)
    if len(universe) != len(set(universe)) or len(covered) != len(set(covered)):
        raise StrictContractError("coverage IDs duplicate")
    expected = tuple(x for x in universe if x in set(covered))
    if covered != expected or any(x not in universe for x in covered):
        raise StrictContractError("coverage IDs are unknown or reordered")
    result = object.__new__(CountedCoverageWitness)
    for name, item in (("ordered_universe_ids",universe),("covered_ids",covered),
                       ("covered_count",len(covered)),("universe_count",len(universe)),
                       ("universe_ids_sha256",_sha256(list(universe))),
                       ("covered_ids_sha256",_sha256(list(covered))),
                       ("complete",covered==universe),("_construction_seal",_COVERAGE_SEAL)):
        object.__setattr__(result,name,item)
    result.__post_init__()
    return result


def _require_frozen_coverage_domain(
    coverage: Any, where: str, *, complete: bool = False
) -> CountedCoverageWitness:
    if type(coverage) is not CountedCoverageWitness:
        raise StrictContractError(f"{where} requires exact counted coverage")
    coverage.__post_init__()
    if coverage.ordered_universe_ids != _FROZEN_PRIMITIVE_IDS:
        raise StrictContractError(f"{where} primitive universe changed")
    if complete and coverage.covered_ids != _FROZEN_PRIMITIVE_IDS:
        raise StrictContractError(f"{where} requires frozen four-of-four coverage")
    return coverage


def _authority_tuple() -> dict[str, Any]:
    return {"schema_version":"odlrq.s0.hard-authority-tuple.v3",
            "accepted_e1_commit_sha":_ACCEPTED_E1_COMMIT,"accepted_e1_tree_sha":_ACCEPTED_E1_TREE,
            "accepted_e1_qualification_envelope_sha256":_E1_ENVELOPE_SHA,
            "accepted_e2_commit_sha":_ACCEPTED_E2_COMMIT,"accepted_e2_tree_sha":_ACCEPTED_E2_TREE,
            "e2_m0_parent_envelope_sha256":_E2_M0_ENVELOPE_SHA,
            "e2_candidate_universe_manifest_sha256":_E2_MANIFEST_SHA,
            "e2_p1_cocycle_sha256":_E2_P1_SHA,"e2_p2_cocycle_sha256":_E2_P2_SHA,
            "e2_return_memory_bound_sha256":_E2_RETURN_SHA,
            "e2_certified_support_token_sha256":_E2_SUPPORT_SHA,
            "s0_primitive_universe_sha256":_PRIMITIVE_UNIVERSE_SHA,
            "norm_id":_NORM_ID,"evidence_scope":_EVIDENCE_SCOPE,"domain_scope":_DOMAIN_SCOPE}


@dataclass(frozen=True, init=False)
class DeclaredS0HardAuthorityReference:
    primitive_rows: tuple[PrimitiveTargetRow, ...] = field(repr=False, compare=False)
    _construction_seal: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("hard authority reference has no public constructor")

    def to_dict(self) -> dict[str, Any]:
        if type(self) is not DeclaredS0HardAuthorityReference or self._construction_seal is not _HARD_REFERENCE_SEAL:
            raise StrictContractError("hard reference construction seal changed")
        _primitive_universe(self.primitive_rows)
        return {"schema_version":_HARD_REFERENCE_SCHEMA,
                "s0_authority_commit_sha":S0_AUTHORITY_COMMIT_SHA,
                "s0_authority_parent_sha":S0_AUTHORITY_PARENT_SHA,
                "s0_authority_document_path":S0_AUTHORITY_DOCUMENT_PATH,
                "s0_authority_document_blob_sha":S0_AUTHORITY_DOCUMENT_BLOB_SHA,
                "s0_authority_ci_run_id":S0_AUTHORITY_CI_RUN_ID,"s0_authority_ci_job_id":S0_AUTHORITY_CI_JOB_ID,
                "accepted_e1_commit_sha":_ACCEPTED_E1_COMMIT,"accepted_e1_tree_sha":_ACCEPTED_E1_TREE,
                "accepted_e1_qualification_envelope_sha256":_E1_ENVELOPE_SHA,
                "accepted_e2_commit_sha":_ACCEPTED_E2_COMMIT,"accepted_e2_tree_sha":_ACCEPTED_E2_TREE,
                "e2_m0_parent_envelope_sha256":_E2_M0_ENVELOPE_SHA,
                "e2_candidate_universe_manifest_sha256":_E2_MANIFEST_SHA,
                "e2_p1_cocycle_sha256":_E2_P1_SHA,"e2_p2_cocycle_sha256":_E2_P2_SHA,
                "e2_return_memory_bound_sha256":_E2_RETURN_SHA,"e2_certified_support_token_sha256":_E2_SUPPORT_SHA,
                "s0_primitive_universe_sha256":_PRIMITIVE_UNIVERSE_SHA,"norm_id":_NORM_ID,
                "evidence_scope":_EVIDENCE_SCOPE,"domain_scope":_DOMAIN_SCOPE,
                "authority_tuple_sha256":_HARD_AUTHORITY_TUPLE_SHA}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeclaredS0HardAuthorityReference":
        if cls is not DeclaredS0HardAuthorityReference:
            raise StrictContractError("polymorphic hard reference parsing forbidden")
        _bounded_wire_walk(value,"DeclaredS0HardAuthorityReference")
        expected = make_declared_s0_hard_authority_reference(primitive_rows=_frozen_primitive_rows())
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError("hard authority reference differs from frozen authority")
        return expected


def make_declared_s0_hard_authority_reference(*, primitive_rows: Any) -> DeclaredS0HardAuthorityReference:
    rows = _exact_tuple(primitive_rows, PrimitiveTargetRow, "primitive_rows", _MAX_PRIMITIVES)
    _primitive_universe(rows)
    if _sha256(_authority_tuple()) != _HARD_AUTHORITY_TUPLE_SHA:
        raise StrictContractError("hard authority tuple constant is inconsistent")
    result = object.__new__(DeclaredS0HardAuthorityReference)
    object.__setattr__(result,"primitive_rows",rows)
    object.__setattr__(result,"_construction_seal",_HARD_REFERENCE_SEAL)
    return result


@dataclass(frozen=True, init=False)
class LiveS0HardAuthorityBinding:
    reference: DeclaredS0HardAuthorityReference
    accepted_e1_qualification_envelope: FiberEnvelope = field(repr=False)
    e2_m0_parent_envelope: FiberEnvelope = field(repr=False)
    e2_support_token: CertifiedSupportToken = field(repr=False)
    _source_seals: tuple[str, str, str] = field(repr=False)
    _construction_seal: object = field(repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("live hard binding has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not LiveS0HardAuthorityBinding or self._construction_seal is not _HARD_BINDING_SEAL:
            raise StrictContractError("live hard binding construction seal changed")
        if type(self.reference) is not DeclaredS0HardAuthorityReference:
            raise StrictContractError("live hard binding reference type changed")


def _base_wire(value: Any, exact_type: type[Any], where: str) -> dict[str, Any]:
    if type(value) is not exact_type:
        raise StrictContractError(f"{where} requires exact {exact_type.__name__}")
    if "to_dict" in vars(value):
        raise StrictContractError(f"{where} forbids instance serializer override")
    wire = exact_type.to_dict(value)
    _bounded_wire_walk(wire,where)
    return wire


def bind_s0_hard_authorities(*, accepted_e1_qualification_envelope: Any,
                             e2_m0_parent_envelope: Any,
                             e2_support_token: Any) -> LiveS0HardAuthorityBinding:
    if (
        type(accepted_e1_qualification_envelope) is not FiberEnvelope
        or type(e2_m0_parent_envelope) is not FiberEnvelope
        or type(e2_support_token) is not CertifiedSupportToken
    ):
        raise StrictContractError(
            "hard binding requires exact envelopes and support token"
        )
    verify_fiber_envelope(accepted_e1_qualification_envelope)
    verify_fiber_envelope(e2_m0_parent_envelope)
    e1_wire = _base_wire(accepted_e1_qualification_envelope,FiberEnvelope,"accepted-E1 qualification envelope")
    e2_wire = _base_wire(e2_m0_parent_envelope,FiberEnvelope,"E2 M0 parent envelope")
    e1_bytes, e2_bytes = canonical_contract_bytes(e1_wire), canonical_contract_bytes(e2_wire)
    if len(e1_bytes) != _E1_ENVELOPE_BYTES or _sha256(e1_wire) != _E1_ENVELOPE_SHA:
        raise StrictContractError("accepted-E1 qualification envelope identity mismatch")
    if len(e2_bytes) != _E2_M0_ENVELOPE_BYTES or _sha256(e2_wire) != _E2_M0_ENVELOPE_SHA:
        raise StrictContractError("E2 M0 parent envelope identity mismatch")
    if e1_bytes == e2_bytes:
        raise StrictContractError("the two named envelope authorities must differ")
    token_wire = _base_wire(e2_support_token,CertifiedSupportToken,"E2 certified support token")
    if _sha256(token_wire) != _E2_SUPPORT_SHA or token_wire.get("candidate_universe_manifest_sha256") != _E2_MANIFEST_SHA or token_wire.get("p1_cocycle_sha256") != _E2_P1_SHA or token_wire.get("p2_cocycle_sha256") != _E2_P2_SHA or token_wire.get("return_memory_bound_sha256") != _E2_RETURN_SHA:
        raise StrictContractError("E2 certified support authority graph changed")
    reference = make_declared_s0_hard_authority_reference(primitive_rows=_frozen_primitive_rows())
    result = object.__new__(LiveS0HardAuthorityBinding)
    for name,item in (("reference",reference),("accepted_e1_qualification_envelope",accepted_e1_qualification_envelope),
                      ("e2_m0_parent_envelope",e2_m0_parent_envelope),("e2_support_token",e2_support_token),
                      ("_source_seals",(_sha256(e1_wire),_sha256(e2_wire),_sha256(token_wire))),
                      ("_construction_seal",_HARD_BINDING_SEAL)):
        object.__setattr__(result,name,item)
    result.__post_init__()
    return result


@dataclass(frozen=True, init=False)
class DeclaredME0ResultReference:
    problem_wire: dict[str, Any] = field(repr=False, compare=False)
    result_wire: dict[str, Any] = field(repr=False, compare=False)
    _construction_seal: object = field(repr=False, compare=False)

    def __init__(self,*_args:Any,**_kwargs:Any)->None:
        raise StrictContractError("ME0 reference has no public constructor")

    def to_dict(self)->dict[str,Any]:
        if type(self) is not DeclaredME0ResultReference or self._construction_seal is not _ME0_REFERENCE_SEAL:
            raise StrictContractError("ME0 reference construction seal changed")
        return {"schema_version":_ME0_REFERENCE_SCHEMA,"accepted_me0_commit_sha":_ACCEPTED_ME0_COMMIT,
                "accepted_me0_tree_sha":_ACCEPTED_ME0_TREE,"me0_problem_wire_sha256":_ME0_PROBLEM_WIRE_SHA,
                "me0_problem_core_sha256":_ME0_PROBLEM_CORE_SHA,"me0_windows_result_wire_sha256":_ME0_RESULT_WIRE_SHA,
                "me0_row_table_sha256":_ME0_ROW_TABLE_SHA,"status":"INTERIOR_SOLVED",
                "support_candidate_ids":["c0","c2"],"runtime_manifest_sha256":_ME0_RUNTIME_SHA,
                "evidence_tier":_ME0_TIER,"predictive_only":True}

    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"DeclaredME0ResultReference":
        if cls is not DeclaredME0ResultReference:
            raise StrictContractError("polymorphic ME0 reference parsing forbidden")
        _bounded_wire_walk(value,"DeclaredME0ResultReference")
        # A serialized reference alone cannot recreate the live result; validate
        # the exact fixed payload and retain no counterfeit object.
        expected = {"schema_version":_ME0_REFERENCE_SCHEMA,"accepted_me0_commit_sha":_ACCEPTED_ME0_COMMIT,
                    "accepted_me0_tree_sha":_ACCEPTED_ME0_TREE,"me0_problem_wire_sha256":_ME0_PROBLEM_WIRE_SHA,
                    "me0_problem_core_sha256":_ME0_PROBLEM_CORE_SHA,"me0_windows_result_wire_sha256":_ME0_RESULT_WIRE_SHA,
                    "me0_row_table_sha256":_ME0_ROW_TABLE_SHA,"status":"INTERIOR_SOLVED",
                    "support_candidate_ids":["c0","c2"],"runtime_manifest_sha256":_ME0_RUNTIME_SHA,
                    "evidence_tier":_ME0_TIER,"predictive_only":True}
        if canonical_contract_bytes(value)!=canonical_contract_bytes(expected):
            raise StrictContractError("ME0 reference differs from frozen authority")
        result=object.__new__(cls)
        object.__setattr__(result,"problem_wire",{})
        object.__setattr__(result,"result_wire",{})
        object.__setattr__(result,"_construction_seal",_ME0_REFERENCE_SEAL)
        return result


def make_declared_me0_result_reference(*,problem_wire:Any,result_wire:Any)->DeclaredME0ResultReference:
    if type(problem_wire) is not dict or type(result_wire) is not dict:
        raise StrictContractError("ME0 reference requires exact wire objects")
    _bounded_wire_walk(problem_wire,"ME0 problem wire")
    _bounded_wire_walk(result_wire,"ME0 result wire")
    problem=MaxEntProblem.from_dict(problem_wire)
    result=MaxEntResult.from_dict(result_wire,problem=problem)
    verify_maxent_result(problem,result)
    pb,rb=canonical_contract_bytes(problem_wire),canonical_contract_bytes(result_wire)
    if len(pb)!=_ME0_PROBLEM_BYTES or _sha256(problem_wire)!=_ME0_PROBLEM_WIRE_SHA or problem.problem_sha256!=_ME0_PROBLEM_CORE_SHA or problem.row_table_sha256!=_ME0_ROW_TABLE_SHA:
        raise StrictContractError("selected ME0 problem identity mismatch")
    if len(rb)!=_ME0_RESULT_BYTES or _sha256(result_wire)!=_ME0_RESULT_WIRE_SHA:
        raise StrictContractError("selected Windows ME0 result identity mismatch")
    if result.status is not MaxEntStatus.INTERIOR_SOLVED or tuple(problem.support_candidate_ids)!=("c0","c2") or result.tier!=_ME0_TIER:
        raise StrictContractError("selected ME0 semantics changed")
    out=object.__new__(DeclaredME0ResultReference)
    # The live binding retains the independently verified source objects.  A
    # declared reference is digest-only and must not retain mutable wire aliases.
    object.__setattr__(out,"problem_wire",{})
    object.__setattr__(out,"result_wire",{})
    object.__setattr__(out,"_construction_seal",_ME0_REFERENCE_SEAL)
    return out


@dataclass(frozen=True,init=False)
class LiveME0ResultBinding:
    reference: DeclaredME0ResultReference
    problem: MaxEntProblem=field(repr=False)
    result: MaxEntResult=field(repr=False)
    _source_seals:tuple[str,str]=field(repr=False)
    _construction_seal:object=field(repr=False,compare=False)
    def __init__(self,*_args:Any,**_kwargs:Any)->None:
        raise StrictContractError("live ME0 binding has no public constructor")
    def __post_init__(self)->None:
        if type(self) is not LiveME0ResultBinding or self._construction_seal is not _ME0_BINDING_SEAL:
            raise StrictContractError("live ME0 binding construction seal changed")


def bind_me0_result(*,problem:Any,result:Any)->LiveME0ResultBinding:
    if type(problem) is not MaxEntProblem or type(result) is not MaxEntResult:
        raise StrictContractError("live ME0 binding requires exact problem/result types")
    if "to_dict" in vars(problem) or "to_dict" in vars(result):
        raise StrictContractError("live ME0 binding forbids serializer overrides")
    problem_wire=MaxEntProblem.to_dict(problem)
    result_wire=MaxEntResult.to_dict(result)
    reference=make_declared_me0_result_reference(problem_wire=problem_wire,result_wire=result_wire)
    out=object.__new__(LiveME0ResultBinding)
    for name,item in (("reference",reference),("problem",problem),("result",result),
                      ("_source_seals",(_sha256(problem_wire),_sha256(result_wire))),
                      ("_construction_seal",_ME0_BINDING_SEAL)):
        object.__setattr__(out,name,item)
    out.__post_init__()
    return out


@dataclass(frozen=True)
class DeclaredSyntheticLPlusToken:
    hard_authority_reference: DeclaredS0HardAuthorityReference
    primitive_universe: dict[str, Any]
    node_l_plus: tuple[ExactRational, ...]
    edge_l_plus: tuple[ExactRational, ...]
    target_residual_upper_bound: ExactRational
    coverage: CountedCoverageWitness
    norm_id: str = _NORM_ID
    evidence_scope: str = _EVIDENCE_SCOPE
    domain_scope: str = _DOMAIN_SCOPE
    disposition: str = "DECLARED_SYNTHETIC_LPLUS_VERIFIED"

    def __post_init__(self) -> None:
        if type(self) is not DeclaredSyntheticLPlusToken:
            raise StrictContractError("DeclaredSyntheticLPlusToken subclasses are forbidden")
        if type(self.hard_authority_reference) is not DeclaredS0HardAuthorityReference:
            raise StrictContractError("L-plus requires exact hard reference")
        if _sha256(self.primitive_universe) != _PRIMITIVE_UNIVERSE_SHA:
            raise StrictContractError("L-plus primitive universe changed")
        if self.node_l_plus != (ExactRational(1), ExactRational(2)) or self.edge_l_plus != (
            ExactRational(1), ExactRational(1), ExactRational(2)
        ) or self.target_residual_upper_bound != ExactRational(1, 8):
            raise StrictContractError("L-plus values differ from complete primitive enumeration")
        _require_frozen_coverage_domain(
            self.coverage, "L-plus declaration", complete=True
        )
        _fixed(self.norm_id, _NORM_ID, "L-plus norm")
        _fixed(self.evidence_scope, _EVIDENCE_SCOPE, "L-plus evidence scope")
        _fixed(self.domain_scope, _DOMAIN_SCOPE, "L-plus domain scope")
        _fixed(self.disposition, "DECLARED_SYNTHETIC_LPLUS_VERIFIED", "L-plus disposition")

    @property
    def l_plus_token_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version": _LPLUS_SCHEMA,
                "hard_authority_reference": self.hard_authority_reference.to_dict(),
                "primitive_universe": self.primitive_universe,
                "node_l_plus": [x.to_dict() for x in self.node_l_plus],
                "edge_l_plus": [x.to_dict() for x in self.edge_l_plus],
                "target_residual_upper_bound": self.target_residual_upper_bound.to_dict(),
                "coverage": self.coverage.to_dict(), "norm_id": self.norm_id,
                "evidence_scope": self.evidence_scope, "domain_scope": self.domain_scope,
                "disposition": self.disposition}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeclaredSyntheticLPlusToken":
        if cls is not DeclaredSyntheticLPlusToken:
            raise StrictContractError("polymorphic L-plus parsing forbidden")
        _bounded_wire_walk(value, "DeclaredSyntheticLPlusToken")
        fields = ("schema_version","hard_authority_reference","primitive_universe","node_l_plus","edge_l_plus","target_residual_upper_bound","coverage","norm_id","evidence_scope","domain_scope","disposition")
        obj = _object(value, fields, "DeclaredSyntheticLPlusToken")
        _fixed(obj["schema_version"], _LPLUS_SCHEMA, "L-plus schema")
        result = cls(
            DeclaredS0HardAuthorityReference.from_dict(obj["hard_authority_reference"]),
            _object(obj["primitive_universe"], ("schema_version","node_ids","edge_orientation","edge_ids","rows"), "primitive universe"),
            tuple(ExactRational.from_dict(x) for x in _array(obj["node_l_plus"],"node_l_plus",maximum=_MAX_NODES)),
            tuple(ExactRational.from_dict(x) for x in _array(obj["edge_l_plus"],"edge_l_plus",maximum=_MAX_EDGES)),
            ExactRational.from_dict(obj["target_residual_upper_bound"]),
            CountedCoverageWitness.from_dict(obj["coverage"]), obj["norm_id"],
            obj["evidence_scope"], obj["domain_scope"], obj["disposition"])
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("L-plus wire does not match recomputation")
        return result


def declare_synthetic_l_plus(*, hard_reference: Any, primitive_rows: Any,
                             coverage: Any) -> DeclaredSyntheticLPlusToken:
    if (
        type(hard_reference) is not DeclaredS0HardAuthorityReference
        or type(primitive_rows) is not tuple
        or type(coverage) is not CountedCoverageWitness
    ):
        raise StrictContractError("L-plus inputs have wrong exact type")
    _require_frozen_coverage_domain(coverage, "L-plus declaration", complete=True)
    rows = _exact_tuple(primitive_rows, PrimitiveTargetRow, "primitive_rows", _MAX_PRIMITIVES)
    universe = _primitive_universe(rows)
    coverage = CountedCoverageWitness.from_dict(coverage.to_dict())
    node = tuple(max((row.node_load[i] for row in rows), key=lambda x: Fraction(x.numerator,x.denominator)) for i in range(2))
    edge = tuple(max((row.edge_load[i] for row in rows), key=lambda x: Fraction(x.numerator,x.denominator)) for i in range(3))
    residual = max((row.target_residual for row in rows), key=lambda x: Fraction(x.numerator,x.denominator))
    return DeclaredSyntheticLPlusToken(hard_reference, universe, node, edge, residual, coverage)


@dataclass(frozen=True)
class TargetResidualBound:
    primitive_universe_sha256: str
    measure_id: str
    value: ExactRational
    coverage: CountedCoverageWitness
    evidence_scope: str
    hard_eligible: bool
    disposition: str

    def __post_init__(self) -> None:
        if type(self) is not TargetResidualBound:
            raise StrictContractError("TargetResidualBound subclasses are forbidden")
        _fixed(self.primitive_universe_sha256, _PRIMITIVE_UNIVERSE_SHA, "target residual primitive universe")
        _identifier(self.measure_id, "target residual measure_id")
        if _rational(self.value, "target residual value", nonnegative=True) != ExactRational(1,8):
            raise StrictContractError("target residual value changed")
        if type(self.coverage) is not CountedCoverageWitness or type(self.hard_eligible) is not bool:
            raise StrictContractError("target residual coverage/eligibility type changed")
        _require_frozen_coverage_domain(self.coverage, "target residual")
        _fixed(self.evidence_scope, _EVIDENCE_SCOPE, "target residual scope")
        expected_hard = self.coverage.covered_ids == _FROZEN_PRIMITIVE_IDS
        expected_disposition = "HARD_TARGET_RESIDUAL_VERIFIED" if expected_hard else "ABSTAIN_INCOMPLETE_COVERAGE"
        if self.hard_eligible is not expected_hard or self.disposition != expected_disposition:
            raise StrictContractError("target residual disposition contradicts coverage")

    @property
    def residual_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {"schema_version":_TARGET_RESIDUAL_SCHEMA,
                "primitive_universe_sha256":self.primitive_universe_sha256,
                "measure_id":self.measure_id,"value":self.value.to_dict(),
                "coverage":self.coverage.to_dict(),"evidence_scope":self.evidence_scope,
                "hard_eligible":self.hard_eligible,"disposition":self.disposition}

    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"TargetResidualBound":
        if cls is not TargetResidualBound:
            raise StrictContractError("polymorphic target residual parsing forbidden")
        _bounded_wire_walk(value,"TargetResidualBound")
        obj=_object(value,("schema_version","primitive_universe_sha256","measure_id","value","coverage","evidence_scope","hard_eligible","disposition"),"TargetResidualBound")
        _fixed(obj["schema_version"],_TARGET_RESIDUAL_SCHEMA,"target residual schema")
        result=cls(obj["primitive_universe_sha256"],obj["measure_id"],ExactRational.from_dict(obj["value"]),CountedCoverageWitness.from_dict(obj["coverage"]),obj["evidence_scope"],obj["hard_eligible"],obj["disposition"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj):
            raise StrictContractError("target residual wire changed")
        return result


def make_target_residual_bound(*,l_plus_token:Any,measure_id:Any,coverage:Any)->TargetResidualBound:
    if type(l_plus_token) is not DeclaredSyntheticLPlusToken or type(coverage) is not CountedCoverageWitness:
        raise StrictContractError("target residual requires exact L-plus and coverage")
    l_plus_token.__post_init__()
    _require_frozen_coverage_domain(coverage,"target residual")
    coverage=CountedCoverageWitness.from_dict(coverage.to_dict())
    hard=coverage.covered_ids==_FROZEN_PRIMITIVE_IDS
    return TargetResidualBound(_PRIMITIVE_UNIVERSE_SHA,_identifier(measure_id,"measure_id"),
                               l_plus_token.target_residual_upper_bound,coverage,_EVIDENCE_SCOPE,hard,
                               "HARD_TARGET_RESIDUAL_VERIFIED" if hard else "ABSTAIN_INCOMPLETE_COVERAGE")


def _rational_sum(values: Sequence[ExactRational], where: str) -> ExactRational:
    total=ExactRational(0)
    for value in values:
        total=_add(total,value,where)
    return total


@dataclass(frozen=True)
class GlobalMeasure:
    measure_id: str
    level: ApproximationLevelId
    normalization_mode: str
    node_ids: tuple[str,...]
    edge_ids: tuple[tuple[str,str],...]
    node_mass: tuple[ExactRational,...]
    edge_mass: tuple[ExactRational,...]
    rho1: ExactRational
    rho2: ExactRational
    cross_covariance_residual: str
    numeric_residual: str

    def __post_init__(self)->None:
        if type(self) is not GlobalMeasure:
            raise StrictContractError("GlobalMeasure subclasses are forbidden")
        _identifier(self.measure_id,"measure_id")
        if type(self.level) is not ApproximationLevelId:
            raise StrictContractError("measure level must be exact ApproximationLevelId")
        if self.node_ids!=("n0","n1") or self.edge_ids!=(("n0","n0"),("n0","n1"),("n1","n1")):
            raise StrictContractError("measure coordinate order changed")
        if type(self.node_mass) is not tuple or len(self.node_mass)!=2 or type(self.edge_mass) is not tuple or len(self.edge_mass)!=3:
            raise StrictContractError("measure mass dimensions changed")
        for value in self.node_mass+self.edge_mass:
            _rational(value,"measure mass",nonnegative=True)
        if self.rho1!=_rational_sum(self.node_mass,"rho1") or self.rho2!=_rational_sum(self.edge_mass,"rho2"):
            raise StrictContractError("measure normalization totals changed")
        if self.normalization_mode=="UNIT_BOTH":
            if self.rho1!=ExactRational(1) or self.rho2!=ExactRational(1):
                raise StrictContractError("UNIT_BOTH requires both masses one")
        elif self.normalization_mode=="ZERO_BOTH":
            if self.rho1!=ExactRational(0) or self.rho2!=ExactRational(0):
                raise StrictContractError("ZERO_BOTH requires both masses zero")
        else:
            raise StrictContractError("invalid normalization_mode")
        _parse_float(self.cross_covariance_residual,"cross covariance residual")
        _parse_float(self.numeric_residual,"numeric residual")
        if float(self.cross_covariance_residual)<0 or float(self.numeric_residual)<0:
            raise StrictContractError("predictive residuals must be nonnegative")

    @property
    def measure_sha256(self)->str:
        return _sha256(self.to_dict())

    def _structural_projection(self)->dict[str,Any]:
        """Return the hard-channel projection, excluding predictive residuals."""
        self.__post_init__()
        return {
            "schema_version": "odlrq.s0.global-measure-structural-projection.v1",
            "measure_id": self.measure_id,
            "level": self.level.to_dict(),
            "normalization_mode": self.normalization_mode,
            "node_ids": list(self.node_ids),
            "edge_ids": [list(x) for x in self.edge_ids],
            "node_mass": [x.to_dict() for x in self.node_mass],
            "edge_mass": [x.to_dict() for x in self.edge_mass],
            "rho1": self.rho1.to_dict(),
            "rho2": self.rho2.to_dict(),
        }

    @property
    def _structural_sha256(self)->str:
        return _sha256(self._structural_projection())

    def to_dict(self)->dict[str,Any]:
        self.__post_init__()
        return {"schema_version":_MEASURE_SCHEMA,"measure_id":self.measure_id,"level":self.level.to_dict(),
                "normalization_mode":self.normalization_mode,"node_ids":list(self.node_ids),
                "edge_ids":[list(x) for x in self.edge_ids],"node_mass":[x.to_dict() for x in self.node_mass],
                "edge_mass":[x.to_dict() for x in self.edge_mass],"rho1":self.rho1.to_dict(),"rho2":self.rho2.to_dict(),
                "cross_covariance_residual":self.cross_covariance_residual,"numeric_residual":self.numeric_residual}

    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"GlobalMeasure":
        if cls is not GlobalMeasure:
            raise StrictContractError("polymorphic GlobalMeasure parsing forbidden")
        _bounded_wire_walk(value,"GlobalMeasure")
        obj=_object(value,("schema_version","measure_id","level","normalization_mode","node_ids","edge_ids","node_mass","edge_mass","rho1","rho2","cross_covariance_residual","numeric_residual"),"GlobalMeasure")
        _fixed(obj["schema_version"],_MEASURE_SCHEMA,"measure schema")
        node_ids=_array(obj["node_ids"],"node_ids",maximum=2)
        edge_rows=_array(obj["edge_ids"],"edge_ids",maximum=3)
        node_mass=_array(obj["node_mass"],"node_mass",maximum=2)
        edge_mass=_array(obj["edge_mass"],"edge_mass",maximum=3)
        if len(node_ids)!=2 or len(edge_rows)!=3 or len(node_mass)!=2 or len(edge_mass)!=3:
            raise StrictContractError("GlobalMeasure coordinate dimensions changed")
        checked_edges=[]
        for row in edge_rows:
            checked=_array(row,"edge_id",maximum=2)
            if len(checked)!=2:raise StrictContractError("edge_id width changed")
            checked_edges.append(checked)
        result=cls(obj["measure_id"],ApproximationLevelId.from_dict(obj["level"]),obj["normalization_mode"],
                   tuple(node_ids),tuple(tuple(x) for x in checked_edges),
                   tuple(ExactRational.from_dict(x) for x in node_mass),tuple(ExactRational.from_dict(x) for x in edge_mass),
                   ExactRational.from_dict(obj["rho1"]),ExactRational.from_dict(obj["rho2"]),obj["cross_covariance_residual"],obj["numeric_residual"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj):
            raise StrictContractError("GlobalMeasure wire changed")
        return result


def make_global_measure(*,measure_id:Any,level:Any,node_ids:Any,edge_ids:Any,node_mass:Any,edge_mass:Any,
                        cross_covariance_residual:Any,numeric_residual:Any)->GlobalMeasure:
    if type(level) is not ApproximationLevelId or type(node_ids) is not tuple or type(edge_ids) is not tuple or type(node_mass) is not tuple or type(edge_mass) is not tuple or type(cross_covariance_residual) is not str or type(numeric_residual) is not str or any(type(value) is not ExactRational for value in node_mass+edge_mass):
        raise StrictContractError("global measure inputs require exact tuple/value types")
    rho1=_rational_sum(node_mass,"rho1")
    rho2=_rational_sum(edge_mass,"rho2")
    if rho1==ExactRational(1) and rho2==ExactRational(1): mode="UNIT_BOTH"
    elif rho1==ExactRational(0) and rho2==ExactRational(0): mode="ZERO_BOTH"
    else: raise StrictContractError("global measure must be UNIT_BOTH or ZERO_BOTH")
    cross_text=_parse_float(cross_covariance_residual,"cross residual")[0]
    numeric_text=_parse_float(numeric_residual,"numeric residual")[0]
    return GlobalMeasure(_identifier(measure_id,"measure_id"),level,mode,node_ids,edge_ids,node_mass,edge_mass,rho1,rho2,
                         cross_text,numeric_text)


def _comparable(x:GlobalMeasure,y:GlobalMeasure)->None:
    if type(x) is not GlobalMeasure or type(y) is not GlobalMeasure:
        raise StrictContractError("distance requires exact GlobalMeasure operands")
    x.__post_init__(); y.__post_init__()
    if x.level!=y.level or x.node_ids!=y.node_ids or x.edge_ids!=y.edge_ids:
        raise StrictContractError("measure domains or coordinate order differ")
    if x.normalization_mode!=y.normalization_mode:
        raise StrictContractError("ZERO_NONZERO_NORMALIZATION_MISMATCH")


@dataclass(frozen=True)
class PredictiveDistance:
    me0_result_reference: DeclaredME0ResultReference
    x_measure_sha256: str
    y_measure_sha256: str
    predictive_metric: str
    x_cross_residual: str
    y_cross_residual: str
    x_numeric_residual: str
    y_numeric_residual: str
    discrepancy_upper_bound: str
    evidence_tier: str="PREDICTIVE_NOMINAL_ONLY"
    disposition: str="PREDICTIVE_DISTANCE_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not PredictiveDistance or type(self.me0_result_reference) is not DeclaredME0ResultReference:
            raise StrictContractError("PredictiveDistance type/provenance changed")
        for name in ("x_measure_sha256","y_measure_sha256"): _digest(getattr(self,name),name)
        parsed=[]
        for name in ("predictive_metric","x_cross_residual","y_cross_residual","x_numeric_residual","y_numeric_residual","discrepancy_upper_bound"):
            parsed.append(_parse_float(getattr(self,name),name)[1])
        if any(value<0 for value in parsed):
            raise StrictContractError("predictive distance scalars must be nonnegative")
        metric,x_cross,y_cross,x_numeric,y_numeric,upper=parsed
        expected=metric+x_cross+y_cross+x_numeric+y_numeric
        if _float_bits(expected)!=_float_bits(upper):
            raise StrictContractError("predictive discrepancy does not equal its components")
        _fixed(self.evidence_tier,"PREDICTIVE_NOMINAL_ONLY","predictive tier")
        _fixed(self.disposition,"PREDICTIVE_DISTANCE_VERIFIED","predictive disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__()
        return {"schema_version":_PREDICTIVE_DISTANCE_SCHEMA,"me0_result_reference":self.me0_result_reference.to_dict(),
                "x_measure_sha256":self.x_measure_sha256,"y_measure_sha256":self.y_measure_sha256,
                "predictive_metric":self.predictive_metric,"x_cross_residual":self.x_cross_residual,"y_cross_residual":self.y_cross_residual,
                "x_numeric_residual":self.x_numeric_residual,"y_numeric_residual":self.y_numeric_residual,
                "discrepancy_upper_bound":self.discrepancy_upper_bound,"evidence_tier":self.evidence_tier,"disposition":self.disposition}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"PredictiveDistance":
        if cls is not PredictiveDistance:
            raise StrictContractError("polymorphic PredictiveDistance parsing forbidden")
        _bounded_wire_walk(value,"PredictiveDistance")
        obj=_object(value,("schema_version","me0_result_reference","x_measure_sha256","y_measure_sha256","predictive_metric","x_cross_residual","y_cross_residual","x_numeric_residual","y_numeric_residual","discrepancy_upper_bound","evidence_tier","disposition"),"PredictiveDistance")
        _fixed(obj["schema_version"],_PREDICTIVE_DISTANCE_SCHEMA,"predictive distance schema")
        result=cls(DeclaredME0ResultReference.from_dict(obj["me0_result_reference"]),obj["x_measure_sha256"],obj["y_measure_sha256"],obj["predictive_metric"],obj["x_cross_residual"],obj["y_cross_residual"],obj["x_numeric_residual"],obj["y_numeric_residual"],obj["discrepancy_upper_bound"],obj["evidence_tier"],obj["disposition"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj): raise StrictContractError("PredictiveDistance wire changed")
        return result


def compute_predictive_distance(*,me0_reference:Any,x:Any,y:Any)->PredictiveDistance:
    if type(me0_reference) is not DeclaredME0ResultReference:
        raise StrictContractError("predictive distance requires exact ME0 reference")
    _comparable(x,y)
    node=sum(abs(Fraction(a.numerator,a.denominator)-Fraction(b.numerator,b.denominator)) for a,b in zip(x.node_mass,y.node_mass))/2
    edge=sum(abs(Fraction(a.numerator,a.denominator)-Fraction(b.numerator,b.denominator)) for a,b in zip(x.edge_mass,y.edge_mass))/2
    metric=float(node+edge)
    upper=metric+float(x.cross_covariance_residual)+float(y.cross_covariance_residual)+float(x.numeric_residual)+float(y.numeric_residual)
    return PredictiveDistance(me0_reference,x.measure_sha256,y.measure_sha256,_float_text(metric,"predictive metric"),
                              x.cross_covariance_residual,y.cross_covariance_residual,x.numeric_residual,y.numeric_residual,
                              _float_text(upper,"predictive upper"))


@dataclass(frozen=True)
class PositiveDistance:
    x_measure_sha256:str
    y_measure_sha256:str
    l_plus_token_sha256:str
    coverage_sha256:str
    x_target_residual_sha256:str
    y_target_residual_sha256:str
    positive_representation_distance:ExactRational
    safety_majorant:ExactRational|None
    disposition:str
    def __post_init__(self)->None:
        if type(self) is not PositiveDistance: raise StrictContractError("PositiveDistance subclasses forbidden")
        for name in ("x_measure_sha256","y_measure_sha256","l_plus_token_sha256","coverage_sha256","x_target_residual_sha256","y_target_residual_sha256"): _digest(getattr(self,name),name)
        _rational(self.positive_representation_distance,"positive representation distance",nonnegative=True)
        if self.disposition=="POSITIVE_SAFETY_MAJORANT_VERIFIED":
            if type(self.safety_majorant) is not ExactRational: raise StrictContractError("verified majorant must be exact")
            _rational(self.safety_majorant,"safety majorant",nonnegative=True)
        elif self.disposition=="ABSTAIN_INCOMPLETE_COVERAGE":
            if self.safety_majorant is not None: raise StrictContractError("abstention majorant must be null")
        else: raise StrictContractError("invalid positive disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__()
        return {"schema_version":_POSITIVE_DISTANCE_SCHEMA,"x_measure_sha256":self.x_measure_sha256,"y_measure_sha256":self.y_measure_sha256,
                "l_plus_token_sha256":self.l_plus_token_sha256,"coverage_sha256":self.coverage_sha256,
                "x_target_residual_sha256":self.x_target_residual_sha256,"y_target_residual_sha256":self.y_target_residual_sha256,
                "positive_representation_distance":self.positive_representation_distance.to_dict(),
                "safety_majorant":None if self.safety_majorant is None else self.safety_majorant.to_dict(),"disposition":self.disposition}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"PositiveDistance":
        if cls is not PositiveDistance:
            raise StrictContractError("polymorphic PositiveDistance parsing forbidden")
        _bounded_wire_walk(value,"PositiveDistance")
        obj=_object(value,("schema_version","x_measure_sha256","y_measure_sha256","l_plus_token_sha256","coverage_sha256","x_target_residual_sha256","y_target_residual_sha256","positive_representation_distance","safety_majorant","disposition"),"PositiveDistance")
        _fixed(obj["schema_version"],_POSITIVE_DISTANCE_SCHEMA,"positive distance schema")
        result=cls(obj["x_measure_sha256"],obj["y_measure_sha256"],obj["l_plus_token_sha256"],obj["coverage_sha256"],obj["x_target_residual_sha256"],obj["y_target_residual_sha256"],ExactRational.from_dict(obj["positive_representation_distance"]),None if obj["safety_majorant"] is None else ExactRational.from_dict(obj["safety_majorant"]),obj["disposition"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj): raise StrictContractError("PositiveDistance wire changed")
        return result


def compute_positive_distance(*,l_plus_token:Any,coverage:Any,x_target_residual:Any,y_target_residual:Any,x:Any,y:Any)->PositiveDistance:
    if type(l_plus_token) is not DeclaredSyntheticLPlusToken or type(coverage) is not CountedCoverageWitness or type(x_target_residual) is not TargetResidualBound or type(y_target_residual) is not TargetResidualBound or type(x) is not GlobalMeasure or type(y) is not GlobalMeasure:
        raise StrictContractError("positive distance requires exact hard inputs")
    l_plus_token.__post_init__()
    _require_frozen_coverage_domain(coverage,"positive distance")
    x_target_residual.__post_init__();y_target_residual.__post_init__()
    if (
        canonical_contract_bytes(coverage.to_dict())
        != canonical_contract_bytes(x_target_residual.coverage.to_dict())
        or canonical_contract_bytes(coverage.to_dict())
        != canonical_contract_bytes(y_target_residual.coverage.to_dict())
    ):
        raise StrictContractError(
            "positive distance coverage must equal both target-residual witnesses"
        )
    _comparable(x,y)
    node=sum(Fraction(w.numerator,w.denominator)*abs(Fraction(a.numerator,a.denominator)-Fraction(b.numerator,b.denominator)) for w,a,b in zip(l_plus_token.node_l_plus,x.node_mass,y.node_mass))
    edge=sum(Fraction(w.numerator,w.denominator)*abs(Fraction(a.numerator,a.denominator)-Fraction(b.numerator,b.denominator)) for w,a,b in zip(l_plus_token.edge_l_plus,x.edge_mass,y.edge_mass))
    distance=_derived(node+edge,"positive distance")
    hard=coverage.covered_ids==_FROZEN_PRIMITIVE_IDS and x_target_residual.hard_eligible and y_target_residual.hard_eligible and x_target_residual.measure_id==x.measure_id and y_target_residual.measure_id==y.measure_id
    majorant=_derived(Fraction(distance.numerator,distance.denominator)+Fraction(x_target_residual.value.numerator,x_target_residual.value.denominator)+Fraction(y_target_residual.value.numerator,y_target_residual.value.denominator),"safety majorant") if hard else None
    return PositiveDistance(x._structural_sha256,y._structural_sha256,l_plus_token.l_plus_token_sha256,_sha256(coverage.to_dict()),x_target_residual.residual_sha256,y_target_residual.residual_sha256,distance,majorant,"POSITIVE_SAFETY_MAJORANT_VERIFIED" if hard else "ABSTAIN_INCOMPLETE_COVERAGE")


def _matrix(value:Any,where:str,rows:int,cols:int)->tuple[tuple[ExactRational,...],...]:
    if type(value) is not tuple or len(value)!=rows or rows*cols>_MAX_MATRIX_CELLS:
        raise StrictContractError(f"{where} has wrong/capped dimensions")
    result=[]
    for row in value:
        if type(row) is not tuple or len(row)!=cols: raise StrictContractError(f"{where} row width changed")
        result.append(tuple(_rational(x,where,nonnegative=True) for x in row))
    return tuple(result)


def _sym2(node:tuple[tuple[ExactRational,...],...])->tuple[tuple[ExactRational,...],...]:
    _matrix(node,"node matrix",2,2)
    pairs=((0,0),(0,1),(1,1))
    out=[]
    for i,j in pairs:
        row=[]
        for u,v in pairs:
            a=Fraction(node[i][u].numerator,node[i][u].denominator)*Fraction(node[j][v].numerator,node[j][v].denominator)
            if i!=j:
                a+=Fraction(node[j][u].numerator,node[j][u].denominator)*Fraction(node[i][v].numerator,node[i][v].denominator)
            row.append(_derived(a,"symmetric-square entry"))
        out.append(tuple(row))
    return tuple(out)


def _matmul(left:tuple[tuple[ExactRational,...],...],right:tuple[tuple[ExactRational,...],...])->tuple[tuple[ExactRational,...],...]:
    if not left or not right or len(left[0])!=len(right): raise StrictContractError("matrix composition dimensions differ")
    return tuple(tuple(_derived(sum(Fraction(left[i][k].numerator,left[i][k].denominator)*Fraction(right[k][j].numerator,right[k][j].denominator) for k in range(len(right))),"matrix composition") for j in range(len(right[0]))) for i in range(len(left)))


@dataclass(frozen=True)
class _Morphism:
    axis:str
    source_level:ApproximationLevelId
    target_level:ApproximationLevelId
    node_matrix:tuple[tuple[ExactRational,...],...]
    edge_matrix:tuple[tuple[ExactRational,...],...]
    edge_orientation:str
    coverage:CountedCoverageWitness
    commutator_l1:ExactRational
    target_residual_transport:ExactRational
    cross_covariance_budget:str
    numeric_residual_budget:str
    remainder_e:ExactRational
    norm_id:str=_NORM_ID
    disposition:str="FINITE_LEVEL_MORPHISM_VERIFIED"
    def __post_init__(self)->None:
        if type(self) not in (RadiusMorphism,WordDepthMorphism,GranularityMorphism): raise StrictContractError("abstract/polymorphic morphism forbidden")
        expected_axis={RadiusMorphism:"RADIUS",WordDepthMorphism:"WORD_DEPTH",GranularityMorphism:"GRANULARITY"}[type(self)]
        _fixed(self.axis,expected_axis,"morphism axis")
        if type(self.source_level) is not ApproximationLevelId or type(self.target_level) is not ApproximationLevelId: raise StrictContractError("morphism levels must be exact")
        source = (self.source_level.radius, self.source_level.word_depth, self.source_level.granularity)
        target = (self.target_level.radius, self.target_level.word_depth, self.target_level.granularity)
        expected_relation = {
            RadiusMorphism: (target[0] + 1, target[1], target[2]),
            WordDepthMorphism: (target[0], target[1] + 1, target[2]),
            GranularityMorphism: (target[0], target[1], target[2] + 1),
        }[type(self)]
        if source != expected_relation:
            raise StrictContractError("morphism is not the typed fine-to-coarse adjacent restriction")
        node=_matrix(self.node_matrix,"node matrix",2,2); edge=_matrix(self.edge_matrix,"edge matrix",3,3)
        if edge!=_sym2(node): raise StrictContractError("edge map is not induced symmetric square")
        for col in range(2):
            if _rational_sum(tuple(node[row][col] for row in range(2)),"node column")!=ExactRational(1): raise StrictContractError("node matrix is not column stochastic")
        for col in range(3):
            if _rational_sum(tuple(edge[row][col] for row in range(3)),"edge column")!=ExactRational(1): raise StrictContractError("edge matrix is not column stochastic")
        _fixed(self.edge_orientation,"unordered_canonical_pair_v1","edge orientation")
        _require_frozen_coverage_domain(
            self.coverage,"morphism",complete=True
        )
        for name in ("commutator_l1","target_residual_transport","remainder_e"): _rational(getattr(self,name),name,nonnegative=True)
        _,cross_budget=_parse_float(self.cross_covariance_budget,"cross covariance budget")
        _,numeric_budget=_parse_float(self.numeric_residual_budget,"numeric residual budget")
        if cross_budget<0 or numeric_budget<0:
            raise StrictContractError("morphism predictive budgets must be nonnegative")
        if (
            self.commutator_l1!=ExactRational(0)
            or self.target_residual_transport!=ExactRational(0)
            or self.cross_covariance_budget!="0"
            or self.numeric_residual_budget!="0"
            or self.remainder_e!=ExactRational(1,4)
        ):
            raise StrictContractError("morphism error tuple differs from frozen S0 authority")
        _fixed(self.norm_id,_NORM_ID,"morphism norm"); _fixed(self.disposition,"FINITE_LEVEL_MORPHISM_VERIFIED","morphism disposition")
    @property
    def morphism_sha256(self)->str:return _sha256(self.to_dict())
    def to_dict(self)->dict[str,Any]:
        self.__post_init__(); schema={RadiusMorphism:_RADIUS_SCHEMA,WordDepthMorphism:_WORD_DEPTH_SCHEMA,GranularityMorphism:_GRANULARITY_SCHEMA}[type(self)]
        return {"schema_version":schema,"axis":self.axis,"source_level":self.source_level.to_dict(),"target_level":self.target_level.to_dict(),
                "node_matrix":[[x.to_dict() for x in row] for row in self.node_matrix],"edge_matrix":[[x.to_dict() for x in row] for row in self.edge_matrix],
                "edge_orientation":self.edge_orientation,"coverage":self.coverage.to_dict(),"commutator_l1":self.commutator_l1.to_dict(),
                "target_residual_transport":self.target_residual_transport.to_dict(),"cross_covariance_budget":self.cross_covariance_budget,
                "numeric_residual_budget":self.numeric_residual_budget,"remainder_e":self.remainder_e.to_dict(),"norm_id":self.norm_id,"disposition":self.disposition}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any]):
        if cls not in (RadiusMorphism,WordDepthMorphism,GranularityMorphism): raise StrictContractError("invalid morphism parser")
        _bounded_wire_walk(value,cls.__name__)
        fields=("schema_version","axis","source_level","target_level","node_matrix","edge_matrix","edge_orientation","coverage","commutator_l1","target_residual_transport","cross_covariance_budget","numeric_residual_budget","remainder_e","norm_id","disposition")
        obj=_object(value,fields,cls.__name__); schema={RadiusMorphism:_RADIUS_SCHEMA,WordDepthMorphism:_WORD_DEPTH_SCHEMA,GranularityMorphism:_GRANULARITY_SCHEMA}[cls]
        _fixed(obj["schema_version"],schema,"morphism schema")
        node_rows=_array(obj["node_matrix"],"node_matrix",maximum=2)
        edge_rows=_array(obj["edge_matrix"],"edge_matrix",maximum=3)
        if len(node_rows)!=2 or len(edge_rows)!=3:
            raise StrictContractError("morphism matrix height changed")
        checked_node_rows=[]
        for row in node_rows:
            checked=_array(row,"node_matrix row",maximum=2)
            if len(checked)!=2:raise StrictContractError("node matrix width changed")
            checked_node_rows.append(checked)
        checked_edge_rows=[]
        for row in edge_rows:
            checked=_array(row,"edge_matrix row",maximum=3)
            if len(checked)!=3:raise StrictContractError("edge matrix width changed")
            checked_edge_rows.append(checked)
        if sum(len(row) for row in checked_node_rows+checked_edge_rows)>_MAX_MATRIX_CELLS:
            raise StrictContractError("morphism matrices exceed cell cap")
        node=tuple(tuple(ExactRational.from_dict(x) for x in row) for row in checked_node_rows)
        edge=tuple(tuple(ExactRational.from_dict(x) for x in row) for row in checked_edge_rows)
        result=cls(obj["axis"],ApproximationLevelId.from_dict(obj["source_level"]),ApproximationLevelId.from_dict(obj["target_level"]),node,edge,obj["edge_orientation"],CountedCoverageWitness.from_dict(obj["coverage"]),ExactRational.from_dict(obj["commutator_l1"]),ExactRational.from_dict(obj["target_residual_transport"]),obj["cross_covariance_budget"],obj["numeric_residual_budget"],ExactRational.from_dict(obj["remainder_e"]),obj["norm_id"],obj["disposition"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj): raise StrictContractError("morphism wire changed")
        return result


@dataclass(frozen=True)
class RadiusMorphism(_Morphism): pass
@dataclass(frozen=True)
class WordDepthMorphism(_Morphism): pass
@dataclass(frozen=True)
class GranularityMorphism(_Morphism): pass


def _make_morphism(cls:type[_Morphism],axis:str,source_level:Any,target_level:Any,node_matrix:Any,coverage:Any,commutator_l1:Any,target_residual_transport:Any,cross_covariance_budget:Any,numeric_residual_budget:Any,remainder_e:Any)->_Morphism:
    if type(source_level) is not ApproximationLevelId or type(target_level) is not ApproximationLevelId or type(coverage) is not CountedCoverageWitness or type(node_matrix) is not tuple or type(commutator_l1) is not ExactRational or type(target_residual_transport) is not ExactRational or type(cross_covariance_budget) is not str or type(numeric_residual_budget) is not str or type(remainder_e) is not ExactRational: raise StrictContractError("morphism inputs have wrong exact type")
    node=_matrix(node_matrix,"node_matrix",2,2)
    _require_frozen_coverage_domain(coverage,"morphism",complete=True)
    cross_text,cross_value=_parse_float(cross_covariance_budget,"cross budget")
    numeric_text,numeric_value=_parse_float(numeric_residual_budget,"numeric budget")
    if cross_value<0 or numeric_value<0:
        raise StrictContractError("morphism predictive budgets must be nonnegative")
    return cls(axis,source_level,target_level,node,_sym2(node),"unordered_canonical_pair_v1",coverage,_rational(commutator_l1,"commutator",nonnegative=True),_rational(target_residual_transport,"target residual transport",nonnegative=True),cross_text,numeric_text,_rational(remainder_e,"remainder",nonnegative=True))


def make_radius_morphism(*,source_level:Any,target_level:Any,node_matrix:Any,coverage:Any,commutator_l1:Any,target_residual_transport:Any,cross_covariance_budget:Any,numeric_residual_budget:Any,remainder_e:Any)->RadiusMorphism:
    return _make_morphism(RadiusMorphism,"RADIUS",source_level,target_level,node_matrix,coverage,commutator_l1,target_residual_transport,cross_covariance_budget,numeric_residual_budget,remainder_e) # type: ignore[return-value]
def make_word_depth_morphism(*,source_level:Any,target_level:Any,node_matrix:Any,coverage:Any,commutator_l1:Any,target_residual_transport:Any,cross_covariance_budget:Any,numeric_residual_budget:Any,remainder_e:Any)->WordDepthMorphism:
    return _make_morphism(WordDepthMorphism,"WORD_DEPTH",source_level,target_level,node_matrix,coverage,commutator_l1,target_residual_transport,cross_covariance_budget,numeric_residual_budget,remainder_e) # type: ignore[return-value]
def make_granularity_morphism(*,source_level:Any,target_level:Any,node_matrix:Any,coverage:Any,commutator_l1:Any,target_residual_transport:Any,cross_covariance_budget:Any,numeric_residual_budget:Any,remainder_e:Any)->GranularityMorphism:
    return _make_morphism(GranularityMorphism,"GRANULARITY",source_level,target_level,node_matrix,coverage,commutator_l1,target_residual_transport,cross_covariance_budget,numeric_residual_budget,remainder_e) # type: ignore[return-value]


@dataclass(frozen=True)
class LocalTower:
    ordered_levels:tuple[ApproximationLevelId,...]
    radius_morphism:RadiusMorphism
    word_depth_morphism:WordDepthMorphism
    granularity_morphism:GranularityMorphism
    composition_order:tuple[str,...]=("GRANULARITY","WORD_DEPTH","RADIUS")
    disposition:str="FINITE_LEVEL_MORPHISM_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not LocalTower or type(self.ordered_levels) is not tuple or len(self.ordered_levels)!=4: raise StrictContractError("local tower levels changed")
        if any(type(x) is not ApproximationLevelId for x in self.ordered_levels) or tuple(x.level_id for x in self.ordered_levels)!=("L0","L1","L2","L3"): raise StrictContractError("local tower level order changed")
        if type(self.radius_morphism) is not RadiusMorphism or type(self.word_depth_morphism) is not WordDepthMorphism or type(self.granularity_morphism) is not GranularityMorphism: raise StrictContractError("local tower morphism type changed")
        if self.radius_morphism.source_level!=self.ordered_levels[1] or self.radius_morphism.target_level!=self.ordered_levels[0] or self.word_depth_morphism.source_level!=self.ordered_levels[2] or self.word_depth_morphism.target_level!=self.ordered_levels[1] or self.granularity_morphism.source_level!=self.ordered_levels[3] or self.granularity_morphism.target_level!=self.ordered_levels[2]: raise StrictContractError("local tower adjacency changed")
        if self.composition_order!=("GRANULARITY","WORD_DEPTH","RADIUS"): raise StrictContractError("local tower composition order changed")
        _fixed(self.disposition,"FINITE_LEVEL_MORPHISM_VERIFIED","local tower disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__();return {"schema_version":_LOCAL_TOWER_SCHEMA,"ordered_levels":[x.to_dict() for x in self.ordered_levels],"radius_morphism":self.radius_morphism.to_dict(),"word_depth_morphism":self.word_depth_morphism.to_dict(),"granularity_morphism":self.granularity_morphism.to_dict(),"composition_order":list(self.composition_order),"disposition":self.disposition}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"LocalTower":
        if cls is not LocalTower:raise StrictContractError("polymorphic LocalTower parsing forbidden")
        _bounded_wire_walk(value,"LocalTower")
        obj=_object(value,("schema_version","ordered_levels","radius_morphism","word_depth_morphism","granularity_morphism","composition_order","disposition"),"LocalTower");_fixed(obj["schema_version"],_LOCAL_TOWER_SCHEMA,"tower schema")
        levels=_array(obj["ordered_levels"],"ordered_levels",maximum=_MAX_LEVELS)
        composition=_array(obj["composition_order"],"composition_order",maximum=3)
        result=cls(tuple(ApproximationLevelId.from_dict(x) for x in levels),RadiusMorphism.from_dict(obj["radius_morphism"]),WordDepthMorphism.from_dict(obj["word_depth_morphism"]),GranularityMorphism.from_dict(obj["granularity_morphism"]),tuple(composition),obj["disposition"])
        if canonical_contract_bytes(result.to_dict())!=canonical_contract_bytes(obj): raise StrictContractError("LocalTower wire changed")
        return result


def build_local_tower(*,ordered_levels:Any,radius_morphism:Any,word_depth_morphism:Any,granularity_morphism:Any)->LocalTower:
    if type(ordered_levels) is not tuple or type(radius_morphism) is not RadiusMorphism or type(word_depth_morphism) is not WordDepthMorphism or type(granularity_morphism) is not GranularityMorphism:
        raise StrictContractError("local tower inputs have wrong exact type")
    return LocalTower(_exact_tuple(ordered_levels,ApproximationLevelId,"ordered_levels",_MAX_LEVELS),radius_morphism,word_depth_morphism,granularity_morphism)


def _predictive_pair_sha(x:GlobalMeasure,y:GlobalMeasure)->str:
    return _sha256([x.measure_sha256,y.measure_sha256])


def _positive_pair_sha(x:GlobalMeasure,y:GlobalMeasure)->str:
    return _sha256([x._structural_sha256,y._structural_sha256])


def _matvec(
    matrix:tuple[tuple[ExactRational,...],...],
    vector:tuple[ExactRational,...],
    where:str,
)->tuple[ExactRational,...]:
    if not matrix or any(len(row)!=len(vector) for row in matrix):
        raise StrictContractError(f"{where} dimensions differ")
    return tuple(
        _derived(
            sum(
                Fraction(entry.numerator,entry.denominator)
                * Fraction(value.numerator,value.denominator)
                for entry,value in zip(row,vector)
            ),
            where,
        )
        for row in matrix
    )


def _verify_measure_image(
    morphism:_Morphism,fine:GlobalMeasure,coarse:GlobalMeasure,where:str
)->None:
    if type(fine) is not GlobalMeasure or type(coarse) is not GlobalMeasure:
        raise StrictContractError(f"{where} requires exact GlobalMeasure values")
    fine.__post_init__();coarse.__post_init__();morphism.__post_init__()
    if fine.level!=morphism.source_level or coarse.level!=morphism.target_level:
        raise StrictContractError(f"{where} levels do not match the morphism")
    if fine.node_ids!=coarse.node_ids or fine.edge_ids!=coarse.edge_ids:
        raise StrictContractError(f"{where} coordinate order changed")
    expected_node=_matvec(morphism.node_matrix,fine.node_mass,f"{where} node image")
    expected_edge=_matvec(morphism.edge_matrix,fine.edge_mass,f"{where} edge image")
    if coarse.node_mass!=expected_node or coarse.edge_mass!=expected_edge:
        raise StrictContractError(f"{where} is not the exact morphism image")


def _verify_predictive_residual_image(
    morphism:_Morphism,fine:GlobalMeasure,coarse:GlobalMeasure,where:str
)->None:
    _,fine_cross=_parse_float(fine.cross_covariance_residual,f"{where} fine cross")
    _,coarse_cross=_parse_float(coarse.cross_covariance_residual,f"{where} coarse cross")
    _,cross_budget=_parse_float(morphism.cross_covariance_budget,f"{where} cross budget")
    _,fine_numeric=_parse_float(fine.numeric_residual,f"{where} fine numeric")
    _,coarse_numeric=_parse_float(coarse.numeric_residual,f"{where} coarse numeric")
    _,numeric_budget=_parse_float(morphism.numeric_residual_budget,f"{where} numeric budget")
    if coarse_cross>fine_cross+cross_budget or coarse_numeric>fine_numeric+numeric_budget:
        raise StrictContractError(f"{where} predictive residual transport failed")


@dataclass(frozen=True)
class PredictiveTransportCertificate:
    channel:str; me0_result_reference_sha256:str; morphism_sha256:str; source_pair_sha256:str; target_pair_sha256:str
    fine_upper:str; coarse_upper:str; remainder_e:ExactRational; inequality_holds:bool; disposition:str="PREDICTIVE_TRANSPORT_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not PredictiveTransportCertificate: raise StrictContractError("predictive transport subtype forbidden")
        _fixed(self.channel,"PREDICTIVE","predictive channel")
        for name in ("me0_result_reference_sha256","morphism_sha256","source_pair_sha256","target_pair_sha256"): _digest(getattr(self,name),name)
        _,fine=_parse_float(self.fine_upper,"fine upper");_,coarse=_parse_float(self.coarse_upper,"coarse upper");_rational(self.remainder_e,"transport remainder",nonnegative=True)
        expected=coarse<=fine+float(Fraction(self.remainder_e.numerator,self.remainder_e.denominator))
        if type(self.inequality_holds) is not bool or self.inequality_holds is not expected or not expected: raise StrictContractError("predictive transport inequality failed")
        _fixed(self.disposition,"PREDICTIVE_TRANSPORT_VERIFIED","predictive transport disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__();return {"schema_version":_PREDICTIVE_TRANSPORT_SCHEMA,"channel":self.channel,"me0_result_reference_sha256":self.me0_result_reference_sha256,"morphism_sha256":self.morphism_sha256,"source_pair_sha256":self.source_pair_sha256,"target_pair_sha256":self.target_pair_sha256,"fine_upper":self.fine_upper,"coarse_upper":self.coarse_upper,"remainder_e":self.remainder_e.to_dict(),"inequality_holds":self.inequality_holds,"disposition":self.disposition}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"PredictiveTransportCertificate":
        if cls is not PredictiveTransportCertificate:raise StrictContractError("polymorphic predictive transport parsing forbidden")
        _bounded_wire_walk(v,"PredictiveTransportCertificate")
        o=_object(v,("schema_version","channel","me0_result_reference_sha256","morphism_sha256","source_pair_sha256","target_pair_sha256","fine_upper","coarse_upper","remainder_e","inequality_holds","disposition"),"PredictiveTransportCertificate");_fixed(o["schema_version"],_PREDICTIVE_TRANSPORT_SCHEMA,"schema");r=cls(o["channel"],o["me0_result_reference_sha256"],o["morphism_sha256"],o["source_pair_sha256"],o["target_pair_sha256"],o["fine_upper"],o["coarse_upper"],ExactRational.from_dict(o["remainder_e"]),o["inequality_holds"],o["disposition"])
        if canonical_contract_bytes(r.to_dict())!=canonical_contract_bytes(o):raise StrictContractError("predictive transport wire changed")
        return r


@dataclass(frozen=True)
class PositiveTransportCertificate:
    channel:str; morphism_sha256:str; source_pair_sha256:str; target_pair_sha256:str; fine_upper:ExactRational; coarse_upper:ExactRational; remainder_e:ExactRational; inequality_holds:bool; disposition:str="POSITIVE_TRANSPORT_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not PositiveTransportCertificate:raise StrictContractError("positive transport subtype forbidden")
        _fixed(self.channel,"POSITIVE","positive channel")
        for name in ("morphism_sha256","source_pair_sha256","target_pair_sha256"): _digest(getattr(self,name),name)
        for name in ("fine_upper","coarse_upper","remainder_e"):_rational(getattr(self,name),name,nonnegative=True)
        expected=Fraction(self.coarse_upper.numerator,self.coarse_upper.denominator)<=Fraction(self.fine_upper.numerator,self.fine_upper.denominator)+Fraction(self.remainder_e.numerator,self.remainder_e.denominator)
        if type(self.inequality_holds) is not bool or self.inequality_holds is not expected or not expected:raise StrictContractError("positive transport inequality failed")
        _fixed(self.disposition,"POSITIVE_TRANSPORT_VERIFIED","positive transport disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__();return {"schema_version":_POSITIVE_TRANSPORT_SCHEMA,"channel":self.channel,"morphism_sha256":self.morphism_sha256,"source_pair_sha256":self.source_pair_sha256,"target_pair_sha256":self.target_pair_sha256,"fine_upper":self.fine_upper.to_dict(),"coarse_upper":self.coarse_upper.to_dict(),"remainder_e":self.remainder_e.to_dict(),"inequality_holds":self.inequality_holds,"disposition":self.disposition}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"PositiveTransportCertificate":
        if cls is not PositiveTransportCertificate:raise StrictContractError("polymorphic positive transport parsing forbidden")
        _bounded_wire_walk(v,"PositiveTransportCertificate")
        o=_object(v,("schema_version","channel","morphism_sha256","source_pair_sha256","target_pair_sha256","fine_upper","coarse_upper","remainder_e","inequality_holds","disposition"),"PositiveTransportCertificate");_fixed(o["schema_version"],_POSITIVE_TRANSPORT_SCHEMA,"schema");r=cls(o["channel"],o["morphism_sha256"],o["source_pair_sha256"],o["target_pair_sha256"],ExactRational.from_dict(o["fine_upper"]),ExactRational.from_dict(o["coarse_upper"]),ExactRational.from_dict(o["remainder_e"]),o["inequality_holds"],o["disposition"])
        if canonical_contract_bytes(r.to_dict())!=canonical_contract_bytes(o):raise StrictContractError("positive transport wire changed")
        return r


def verify_predictive_transport(*,me0_reference:Any,morphism:Any,x_fine:Any,y_fine:Any,x_coarse:Any,y_coarse:Any)->PredictiveTransportCertificate:
    if type(me0_reference) is not DeclaredME0ResultReference or type(morphism) not in (RadiusMorphism,WordDepthMorphism,GranularityMorphism) or any(type(value) is not GlobalMeasure for value in (x_fine,y_fine,x_coarse,y_coarse)):raise StrictContractError("predictive transport authority/type changed")
    _verify_measure_image(morphism,x_fine,x_coarse,"predictive x image")
    _verify_measure_image(morphism,y_fine,y_coarse,"predictive y image")
    _verify_predictive_residual_image(morphism,x_fine,x_coarse,"predictive x image")
    _verify_predictive_residual_image(morphism,y_fine,y_coarse,"predictive y image")
    fine=compute_predictive_distance(me0_reference=me0_reference,x=x_fine,y=y_fine);coarse=compute_predictive_distance(me0_reference=me0_reference,x=x_coarse,y=y_coarse)
    holds=float(coarse.discrepancy_upper_bound)<=float(fine.discrepancy_upper_bound)+float(Fraction(morphism.remainder_e.numerator,morphism.remainder_e.denominator))
    return PredictiveTransportCertificate("PREDICTIVE",_sha256(me0_reference.to_dict()),morphism.morphism_sha256,_predictive_pair_sha(x_fine,y_fine),_predictive_pair_sha(x_coarse,y_coarse),fine.discrepancy_upper_bound,coarse.discrepancy_upper_bound,morphism.remainder_e,holds)


def verify_positive_transport(*,l_plus_token:Any,coverage:Any,morphism:Any,x_fine_target_residual:Any,y_fine_target_residual:Any,x_coarse_target_residual:Any,y_coarse_target_residual:Any,x_fine:Any,y_fine:Any,x_coarse:Any,y_coarse:Any)->PositiveTransportCertificate:
    if type(l_plus_token) is not DeclaredSyntheticLPlusToken or type(coverage) is not CountedCoverageWitness or type(morphism) not in (RadiusMorphism,WordDepthMorphism,GranularityMorphism) or any(type(value) is not TargetResidualBound for value in (x_fine_target_residual,y_fine_target_residual,x_coarse_target_residual,y_coarse_target_residual)) or any(type(value) is not GlobalMeasure for value in (x_fine,y_fine,x_coarse,y_coarse)):raise StrictContractError("positive transport input type changed")
    _verify_measure_image(morphism,x_fine,x_coarse,"positive x image")
    _verify_measure_image(morphism,y_fine,y_coarse,"positive y image")
    fine=compute_positive_distance(l_plus_token=l_plus_token,coverage=coverage,x_target_residual=x_fine_target_residual,y_target_residual=y_fine_target_residual,x=x_fine,y=y_fine);coarse=compute_positive_distance(l_plus_token=l_plus_token,coverage=coverage,x_target_residual=x_coarse_target_residual,y_target_residual=y_coarse_target_residual,x=x_coarse,y=y_coarse)
    if fine.safety_majorant is None or coarse.safety_majorant is None:raise StrictContractError("positive transport cannot use abstention")
    holds=Fraction(coarse.safety_majorant.numerator,coarse.safety_majorant.denominator)<=Fraction(fine.safety_majorant.numerator,fine.safety_majorant.denominator)+Fraction(morphism.remainder_e.numerator,morphism.remainder_e.denominator)
    return PositiveTransportCertificate("POSITIVE",morphism.morphism_sha256,_positive_pair_sha(x_fine,y_fine),_positive_pair_sha(x_coarse,y_coarse),fine.safety_majorant,coarse.safety_majorant,morphism.remainder_e,holds)


def _composed_morphism_projection_sha256(
    *,source_level:ApproximationLevelId,target_level:ApproximationLevelId,
    application_order:tuple[str,...],node_matrix:tuple[tuple[ExactRational,...],...]
)->str:
    node=_matrix(node_matrix,"composed node matrix",2,2)
    return _sha256({
        "schema_version":"odlrq.s0.composed-morphism-projection.v1",
        "source_level":source_level.to_dict(),
        "target_level":target_level.to_dict(),
        "application_order":list(application_order),
        "node_matrix":[[x.to_dict() for x in row] for row in node],
        "edge_matrix":[[x.to_dict() for x in row] for row in _sym2(node)],
        "edge_orientation":"unordered_canonical_pair_v1",
        "norm_id":_NORM_ID,
    })


def _expected_transport_morphism_rows(
    tower:LocalTower,
)->tuple[tuple[str,ExactRational],...]:
    if type(tower) is not LocalTower:
        raise StrictContractError("transport rows require exact LocalTower")
    tower.__post_init__()
    r=tower.radius_morphism;w=tower.word_depth_morphism;g=tower.granularity_morphism
    n20=_matmul(r.node_matrix,w.node_matrix)
    n31=_matmul(w.node_matrix,g.node_matrix)
    n30=_matmul(r.node_matrix,n31)
    return (
        (r.morphism_sha256,ExactRational(1,4)),
        (w.morphism_sha256,ExactRational(1,4)),
        (g.morphism_sha256,ExactRational(1,4)),
        (_composed_morphism_projection_sha256(
            source_level=tower.ordered_levels[2],target_level=tower.ordered_levels[0],
            application_order=("WORD_DEPTH","RADIUS"),node_matrix=n20,
        ),ExactRational(1,2)),
        (_composed_morphism_projection_sha256(
            source_level=tower.ordered_levels[3],target_level=tower.ordered_levels[1],
            application_order=("GRANULARITY","WORD_DEPTH"),node_matrix=n31,
        ),ExactRational(1,2)),
        (_composed_morphism_projection_sha256(
            source_level=tower.ordered_levels[3],target_level=tower.ordered_levels[0],
            application_order=("GRANULARITY","WORD_DEPTH","RADIUS"),node_matrix=n30,
        ),ExactRational(3,4)),
    )


def _validate_six_transport_chain(rows:tuple[Any,...],where:str)->None:
    if type(rows) is not tuple or len(rows)!=6:
        raise StrictContractError(f"{where} must contain exactly six rows")
    # The fixed six rows are R, N, G, RN, NG, RNG.  These pair equalities
    # independently fix their graph order even when a wire recomputes its own
    # outer projection digest after reordering.
    r,n,g,rn,ng,rng=rows
    if not (
        n.target_pair_sha256==r.source_pair_sha256
        and g.target_pair_sha256==n.source_pair_sha256
        and rn.source_pair_sha256==n.source_pair_sha256
        and rn.target_pair_sha256==r.target_pair_sha256
        and ng.source_pair_sha256==g.source_pair_sha256
        and ng.target_pair_sha256==r.source_pair_sha256
        and rng.source_pair_sha256==g.source_pair_sha256
        and rng.target_pair_sha256==r.target_pair_sha256
    ):
        raise StrictContractError(f"{where} six-composite order/chain changed")


@dataclass(frozen=True)
class FiniteRemainderCertificate:
    finite_level_count:int;ordered_level_ids:tuple[str,...];adjacent_remainders:tuple[ExactRational,...];suffix_majorants:tuple[ExactRational,...];composite_remainders:tuple[ExactRational,...]
    predictive_transport_certificates:tuple[PredictiveTransportCertificate,...];positive_transport_certificates:tuple[PositiveTransportCertificate,...]
    predictive_projection_sha256:str;positive_projection_sha256:str;infinite_cutoff_claim:bool;disposition:str="FINITE_REMAINDER_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not FiniteRemainderCertificate or _exact_int(self.finite_level_count,"finite level count")!=4 or type(self.ordered_level_ids) is not tuple or any(type(x) is not str for x in self.ordered_level_ids) or self.ordered_level_ids!=("L0","L1","L2","L3"):raise StrictContractError("finite remainder levels changed")
        _exact_tuple(self.adjacent_remainders,ExactRational,"adjacent remainders",3)
        _exact_tuple(self.suffix_majorants,ExactRational,"suffix majorants",4)
        _exact_tuple(self.composite_remainders,ExactRational,"composite remainders",6)
        if self.adjacent_remainders!=(ExactRational(1,4),)*3 or self.suffix_majorants!=(ExactRational(3,4),ExactRational(1,2),ExactRational(1,4),ExactRational(0)) or self.composite_remainders!=(ExactRational(1,4),ExactRational(1,4),ExactRational(1,4),ExactRational(1,2),ExactRational(1,2),ExactRational(3,4)):raise StrictContractError("finite remainder arithmetic changed")
        _exact_tuple(self.predictive_transport_certificates,PredictiveTransportCertificate,"predictive transports",6)
        _exact_tuple(self.positive_transport_certificates,PositiveTransportCertificate,"positive transports",6)
        if len(self.predictive_transport_certificates)!=6 or len(self.positive_transport_certificates)!=6:raise StrictContractError("transport certificate coverage changed")
        for cert in self.predictive_transport_certificates+self.positive_transport_certificates:cert.__post_init__()
        if tuple(x.remainder_e for x in self.predictive_transport_certificates)!=self.composite_remainders or tuple(x.remainder_e for x in self.positive_transport_certificates)!=self.composite_remainders:raise StrictContractError("transport remainder rows changed")
        if tuple(x.morphism_sha256 for x in self.predictive_transport_certificates)!=tuple(x.morphism_sha256 for x in self.positive_transport_certificates):raise StrictContractError("predictive/positive morphism projections differ")
        if len({x.me0_result_reference_sha256 for x in self.predictive_transport_certificates})!=1:raise StrictContractError("predictive transport ME0 provenance changed")
        _validate_six_transport_chain(self.predictive_transport_certificates,"predictive transports")
        _validate_six_transport_chain(self.positive_transport_certificates,"positive transports")
        if self.infinite_cutoff_claim is not False:raise StrictContractError("infinite cutoff claim forbidden")
        if self.predictive_projection_sha256!=_sha256([x.to_dict() for x in self.predictive_transport_certificates]) or self.positive_projection_sha256!=_sha256([x.to_dict() for x in self.positive_transport_certificates]):raise StrictContractError("finite remainder projections changed")
        _fixed(self.disposition,"FINITE_REMAINDER_VERIFIED","finite remainder disposition")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__();return {"schema_version":_REMAINDER_SCHEMA,"finite_level_count":self.finite_level_count,"ordered_level_ids":list(self.ordered_level_ids),"adjacent_remainders":[x.to_dict() for x in self.adjacent_remainders],"suffix_majorants":[x.to_dict() for x in self.suffix_majorants],"composite_remainders":[x.to_dict() for x in self.composite_remainders],"predictive_transport_certificates":[x.to_dict() for x in self.predictive_transport_certificates],"positive_transport_certificates":[x.to_dict() for x in self.positive_transport_certificates],"predictive_projection_sha256":self.predictive_projection_sha256,"positive_projection_sha256":self.positive_projection_sha256,"infinite_cutoff_claim":self.infinite_cutoff_claim,"disposition":self.disposition}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"FiniteRemainderCertificate":
        if cls is not FiniteRemainderCertificate:raise StrictContractError("polymorphic finite remainder parsing forbidden")
        _bounded_wire_walk(v,"FiniteRemainderCertificate")
        o=_object(v,("schema_version","finite_level_count","ordered_level_ids","adjacent_remainders","suffix_majorants","composite_remainders","predictive_transport_certificates","positive_transport_certificates","predictive_projection_sha256","positive_projection_sha256","infinite_cutoff_claim","disposition"),"FiniteRemainderCertificate");_fixed(o["schema_version"],_REMAINDER_SCHEMA,"schema")
        level_ids=_array(o["ordered_level_ids"],"ordered_level_ids",maximum=4)
        adjacent=_array(o["adjacent_remainders"],"adjacent_remainders",maximum=3)
        suffix=_array(o["suffix_majorants"],"suffix_majorants",maximum=4)
        composites=_array(o["composite_remainders"],"composite_remainders",maximum=6)
        predictive=_array(o["predictive_transport_certificates"],"predictive transports",maximum=6)
        positive=_array(o["positive_transport_certificates"],"positive transports",maximum=6)
        r=cls(o["finite_level_count"],tuple(level_ids),tuple(ExactRational.from_dict(x) for x in adjacent),tuple(ExactRational.from_dict(x) for x in suffix),tuple(ExactRational.from_dict(x) for x in composites),tuple(PredictiveTransportCertificate.from_dict(x) for x in predictive),tuple(PositiveTransportCertificate.from_dict(x) for x in positive),o["predictive_projection_sha256"],o["positive_projection_sha256"],o["infinite_cutoff_claim"],o["disposition"])
        if canonical_contract_bytes(r.to_dict())!=canonical_contract_bytes(o):raise StrictContractError("finite remainder wire changed")
        return r


def certify_finite_remainder(*,tower:Any,predictive_transport_certificates:Any,positive_transport_certificates:Any)->FiniteRemainderCertificate:
    if type(tower) is not LocalTower:raise StrictContractError("finite remainder requires exact LocalTower")
    predictive=_exact_tuple(predictive_transport_certificates,PredictiveTransportCertificate,"predictive transports",6);positive=_exact_tuple(positive_transport_certificates,PositiveTransportCertificate,"positive transports",6)
    if len(predictive)!=6 or len(positive)!=6:raise StrictContractError("all six composites must be supplied")
    adjacent=(ExactRational(1,4),)*3;suffix=(ExactRational(3,4),ExactRational(1,2),ExactRational(1,4),ExactRational(0));composite=(ExactRational(1,4),ExactRational(1,4),ExactRational(1,4),ExactRational(1,2),ExactRational(1,2),ExactRational(3,4))
    expected_rows=_expected_transport_morphism_rows(tower)
    expected_hashes=tuple(row[0] for row in expected_rows)
    expected_remainders=tuple(row[1] for row in expected_rows)
    if expected_remainders!=composite or tuple(x.morphism_sha256 for x in predictive)!=expected_hashes or tuple(x.morphism_sha256 for x in positive)!=expected_hashes or tuple(x.remainder_e for x in predictive)!=composite or tuple(x.remainder_e for x in positive)!=composite:
        raise StrictContractError("six transport composites do not match the tower")
    _validate_six_transport_chain(predictive,"predictive transports")
    _validate_six_transport_chain(positive,"positive transports")
    return FiniteRemainderCertificate(4,("L0","L1","L2","L3"),adjacent,suffix,composite,predictive,positive,_sha256([x.to_dict() for x in predictive]),_sha256([x.to_dict() for x in positive]),False)


def _case_row(case_id:str,x:GlobalMeasure,y:GlobalMeasure,coverage:CountedCoverageWitness,
              predictive:PredictiveDistance|None,positive:PositiveDistance|None,
              error:str|None)->dict[str,Any]:
    return {"schema_version":_CASE_SCHEMA,"case_id":case_id,"x_measure_id":x.measure_id,
            "y_measure_id":y.measure_id,"coverage":coverage.to_dict(),
            "predictive_distance":None if predictive is None else predictive.to_dict(),
            "positive_distance":None if positive is None else positive.to_dict(),
            "expected_error":error}


@dataclass(frozen=True)
class SimilarityCertificate:
    hard_authority_reference:DeclaredS0HardAuthorityReference
    predictive_me0_result_reference:DeclaredME0ResultReference
    primitive_universe_sha256:str
    l_plus_token:DeclaredSyntheticLPlusToken
    measures:tuple[GlobalMeasure,...]
    local_tower:LocalTower
    predictive_case_results:tuple[dict[str,Any],...]
    positive_case_results:tuple[dict[str,Any],...]
    finite_remainder_certificate:FiniteRemainderCertificate
    coverage:CountedCoverageWitness
    target_residuals:tuple[TargetResidualBound,...]=field(repr=False)
    runtime_manifest_sha256:str=_S0_RUNTIME_SHA
    disposition:str="CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED"
    def __post_init__(self)->None:
        if type(self) is not SimilarityCertificate:raise StrictContractError("SimilarityCertificate subclasses forbidden")
        if type(self.hard_authority_reference) is not DeclaredS0HardAuthorityReference or type(self.predictive_me0_result_reference) is not DeclaredME0ResultReference:raise StrictContractError("similarity authority reference type changed")
        _fixed(self.primitive_universe_sha256,_PRIMITIVE_UNIVERSE_SHA,"similarity primitive universe")
        if type(self.l_plus_token) is not DeclaredSyntheticLPlusToken or type(self.local_tower) is not LocalTower or type(self.finite_remainder_certificate) is not FiniteRemainderCertificate or type(self.coverage) is not CountedCoverageWitness:raise StrictContractError("similarity nested type changed")
        self.l_plus_token.__post_init__();self.local_tower.__post_init__();self.finite_remainder_certificate.__post_init__()
        _require_frozen_coverage_domain(self.coverage,"similarity certificate",complete=True)
        if self.l_plus_token.hard_authority_reference!=self.hard_authority_reference:
            raise StrictContractError("similarity hard authority binding changed")
        _exact_tuple(self.measures,GlobalMeasure,"similarity measures",_MAX_MEASURES);_exact_tuple(self.target_residuals,TargetResidualBound,"target residuals",_MAX_MEASURES)
        expected_measure_ids=("u24_s0_s_id_m","u24_s0_s_node_x","u24_s0_s_node_y","u24_s0_s_edge_x","u24_s0_s_edge_y","u24_s0_s_cross_x","u24_s0_s_cross_y","u24_s0_s_cover_x","u24_s0_s_cover_y","u24_s0_s_zero_m","u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y","u24_s0_s_compose_l2_m","u24_s0_s_compose_l1_m","u24_s0_s_compose_l0_m","u24_s0_s_numeric_x","u24_s0_s_numeric_y")
        if tuple(x.measure_id for x in self.measures)!=expected_measure_ids or tuple(x.measure_id for x in self.target_residuals)!=expected_measure_ids:raise StrictContractError("similarity measure/residual order changed")
        by_measure={x.measure_id:x for x in self.measures}
        by_residual={x.measure_id:x for x in self.target_residuals}
        expected_predictive,expected_positive=_manual_transports(
            self.predictive_me0_result_reference,self.local_tower,by_measure,
            self.l_plus_token,self.coverage,by_residual,
        )
        if (
            canonical_contract_bytes([x.to_dict() for x in expected_predictive])
            != canonical_contract_bytes([x.to_dict() for x in self.finite_remainder_certificate.predictive_transport_certificates])
            or canonical_contract_bytes([x.to_dict() for x in expected_positive])
            != canonical_contract_bytes([x.to_dict() for x in self.finite_remainder_certificate.positive_transport_certificates])
        ):
            raise StrictContractError("similarity transport rows differ from contained tower/measures")
        expected_finite=certify_finite_remainder(
            tower=self.local_tower,
            predictive_transport_certificates=expected_predictive,
            positive_transport_certificates=expected_positive,
        )
        if canonical_contract_bytes(expected_finite.to_dict())!=canonical_contract_bytes(self.finite_remainder_certificate.to_dict()):
            raise StrictContractError("similarity finite remainder differs from recomputation")
        self._normalized_case_rows("predictive")
        self._normalized_case_rows("positive")
        _fixed(self.runtime_manifest_sha256,_S0_RUNTIME_SHA,"S0 runtime")
        _fixed(self.disposition,"CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED","similarity disposition")

    def _normalized_case_rows(self,channel:str)->list[dict[str,Any]]:
        if channel not in ("predictive","positive"):
            raise StrictContractError("unknown similarity channel")
        rows=self.predictive_case_results if channel=="predictive" else self.positive_case_results
        if type(rows) is not tuple or len(rows)!=9:
            raise StrictContractError(f"{channel} case count changed")
        specs=(
            ("s-id","u24_s0_s_id_m","u24_s0_s_id_m",False,None),
            ("s-node","u24_s0_s_node_x","u24_s0_s_node_y",False,None),
            ("s-edge","u24_s0_s_edge_x","u24_s0_s_edge_y",False,None),
            ("s-cross","u24_s0_s_cross_x","u24_s0_s_cross_y",False,None),
            ("s-cover","u24_s0_s_cover_x","u24_s0_s_cover_y",True,None),
            ("s-zero","u24_s0_s_zero_m","u24_s0_s_zero_m",False,None),
            ("s-zero-kill","u24_s0_s_zero_m","u24_s0_s_id_m",False,"ZERO_NONZERO_NORMALIZATION_MISMATCH"),
            ("s-compose","u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y",False,None),
            ("s-numeric","u24_s0_s_numeric_x","u24_s0_s_numeric_y",False,None),
        )
        by_measure={x.measure_id:x for x in self.measures}
        by_residual={x.measure_id:x for x in self.target_residuals}
        normalized=[]
        for row,spec in zip(rows,specs):
            cid,xid,yid,incomplete,error=spec
            obj=_object(row,("schema_version","case_id","x_measure_id","y_measure_id","coverage","predictive_distance","positive_distance","expected_error"),f"{channel} case")
            _fixed(obj["schema_version"],_CASE_SCHEMA,"case schema")
            if obj["case_id"]!=cid or obj["x_measure_id"]!=xid or obj["y_measure_id"]!=yid or obj["expected_error"]!=error:
                raise StrictContractError(f"{channel} case identity/error changed")
            coverage=CountedCoverageWitness.from_dict(obj["coverage"])
            _require_frozen_coverage_domain(coverage,f"{channel} case coverage")
            expected_covered=_FROZEN_PRIMITIVE_IDS[:-1] if incomplete else _FROZEN_PRIMITIVE_IDS
            if coverage.covered_ids!=expected_covered:
                raise StrictContractError(f"{channel} case coverage changed")
            x=by_measure[xid];y=by_measure[yid]
            if error is not None:
                if obj["predictive_distance"] is not None or obj["positive_distance"] is not None:
                    raise StrictContractError(f"{channel} error case carries a distance")
                normalized.append(_case_row(cid,x,y,coverage,None,None,error))
                continue
            if channel=="predictive":
                if obj["positive_distance"] is not None or obj["predictive_distance"] is None:
                    raise StrictContractError("predictive case channel firewall failed")
                supplied=PredictiveDistance.from_dict(obj["predictive_distance"])
                expected=compute_predictive_distance(
                    me0_reference=self.predictive_me0_result_reference,x=x,y=y
                )
                if canonical_contract_bytes(supplied.to_dict())!=canonical_contract_bytes(expected.to_dict()):
                    raise StrictContractError("predictive case differs from recomputation")
                normalized.append(_case_row(cid,x,y,coverage,expected,None,None))
            else:
                if obj["predictive_distance"] is not None or obj["positive_distance"] is None:
                    raise StrictContractError("positive case channel firewall failed")
                supplied=PositiveDistance.from_dict(obj["positive_distance"])
                expected=compute_positive_distance(
                    l_plus_token=self.l_plus_token,coverage=coverage,
                    x_target_residual=by_residual[xid],y_target_residual=by_residual[yid],
                    x=x,y=y,
                )
                if canonical_contract_bytes(supplied.to_dict())!=canonical_contract_bytes(expected.to_dict()):
                    raise StrictContractError("positive case differs from recomputation")
                normalized.append(_case_row(cid,x,y,coverage,None,expected,None))
        return normalized

    def _structural_measure_rows(self)->list[dict[str,Any]]:
        return [{"measure_id":x.measure_id,"measure_sha256":x._structural_sha256} for x in self.measures]

    def _positive_core(self)->dict[str,Any]:
        return {"schema_version":_POSITIVE_CORE_SCHEMA,"hard_authority_reference":self.hard_authority_reference.to_dict(),
                "primitive_universe_sha256":self.primitive_universe_sha256,"l_plus_token":self.l_plus_token.to_dict(),
                "structural_measure_sha256_rows":self._structural_measure_rows(),
                "positive_case_results":self._normalized_case_rows("positive"),
                "positive_transport_certificates":[x.to_dict() for x in self.finite_remainder_certificate.positive_transport_certificates],
                "coverage":self.coverage.to_dict(),"target_residuals":[x.to_dict() for x in self.target_residuals],
                "positive_finite_remainder":{"adjacent_remainders":[x.to_dict() for x in self.finite_remainder_certificate.adjacent_remainders],"suffix_majorants":[x.to_dict() for x in self.finite_remainder_certificate.suffix_majorants],"composite_remainders":[x.to_dict() for x in self.finite_remainder_certificate.composite_remainders],"infinite_cutoff_claim":False},
                "runtime_manifest_sha256":self.runtime_manifest_sha256,"disposition":self.disposition}

    def _predictive_core(self)->dict[str,Any]:
        return {"schema_version":_PREDICTIVE_CORE_SCHEMA,"predictive_me0_result_reference":self.predictive_me0_result_reference.to_dict(),
                "structural_measure_sha256_rows":self._structural_measure_rows(),"predictive_case_results":self._normalized_case_rows("predictive"),
                "predictive_transport_certificates":[x.to_dict() for x in self.finite_remainder_certificate.predictive_transport_certificates],
                "predictive_finite_remainder":{"adjacent_remainders":[x.to_dict() for x in self.finite_remainder_certificate.adjacent_remainders],"suffix_majorants":[x.to_dict() for x in self.finite_remainder_certificate.suffix_majorants],"composite_remainders":[x.to_dict() for x in self.finite_remainder_certificate.composite_remainders],"infinite_cutoff_claim":False},
                "runtime_manifest_sha256":self.runtime_manifest_sha256,"disposition":self.disposition}

    @property
    def positive_core_sha256(self)->str:return _sha256(self._positive_core())
    @property
    def predictive_core_sha256(self)->str:return _sha256(self._predictive_core())
    def to_dict(self)->dict[str,Any]:
        self.__post_init__()
        return {"schema_version":_SIMILARITY_SCHEMA,"hard_authority_reference":self.hard_authority_reference.to_dict(),
                "predictive_me0_result_reference":self.predictive_me0_result_reference.to_dict(),"primitive_universe_sha256":self.primitive_universe_sha256,
                "l_plus_token":self.l_plus_token.to_dict(),"measures":[x.to_dict() for x in self.measures],"local_tower":self.local_tower.to_dict(),
                "predictive_case_results":self._normalized_case_rows("predictive"),"positive_case_results":self._normalized_case_rows("positive"),
                "finite_remainder_certificate":self.finite_remainder_certificate.to_dict(),"coverage":self.coverage.to_dict(),
                "positive_core_sha256":self.positive_core_sha256,"predictive_core_sha256":self.predictive_core_sha256,
                "runtime_manifest_sha256":self.runtime_manifest_sha256,"disposition":self.disposition}

    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"SimilarityCertificate":
        if cls is not SimilarityCertificate:raise StrictContractError("polymorphic similarity parsing forbidden")
        _bounded_wire_walk(value,"SimilarityCertificate")
        fields=("schema_version","hard_authority_reference","predictive_me0_result_reference","primitive_universe_sha256","l_plus_token","measures","local_tower","predictive_case_results","positive_case_results","finite_remainder_certificate","coverage","positive_core_sha256","predictive_core_sha256","runtime_manifest_sha256","disposition")
        obj=_object(value,fields,"SimilarityCertificate");_fixed(obj["schema_version"],_SIMILARITY_SCHEMA,"similarity schema")
        hard=DeclaredS0HardAuthorityReference.from_dict(obj["hard_authority_reference"]);me0=DeclaredME0ResultReference.from_dict(obj["predictive_me0_result_reference"])
        expected=build_declared_synthetic_similarity_fixture(hard_reference=hard,me0_reference=me0).similarity_certificate
        if canonical_contract_bytes(expected.to_dict())!=canonical_contract_bytes(obj):raise StrictContractError("similarity wire differs from fixed live recomputation")
        return expected


@dataclass(frozen=True)
class DeclaredSyntheticSimilarityFixture:
    hard_authority_reference:DeclaredS0HardAuthorityReference
    predictive_me0_result_reference:DeclaredME0ResultReference
    primitive_rows:tuple[PrimitiveTargetRow,...]
    coverage_witnesses:tuple[CountedCoverageWitness,...]
    target_residuals:tuple[TargetResidualBound,...]
    measures:tuple[GlobalMeasure,...]
    local_tower:LocalTower
    similarity_certificate:SimilarityCertificate
    def __post_init__(self)->None:
        if type(self) is not DeclaredSyntheticSimilarityFixture:raise StrictContractError("fixture subclasses forbidden")
        _exact_tuple(self.primitive_rows,PrimitiveTargetRow,"fixture primitive rows",4)
        _exact_tuple(self.coverage_witnesses,CountedCoverageWitness,"fixture coverage witnesses",2)
        _exact_tuple(self.target_residuals,TargetResidualBound,"fixture target residuals",_MAX_MEASURES)
        _exact_tuple(self.measures,GlobalMeasure,"fixture measures",_MAX_MEASURES)
        if self.primitive_rows!=_frozen_primitive_rows() or len(self.coverage_witnesses)!=2 or len(self.measures)!=17:raise StrictContractError("fixed similarity fixture changed")
        full,missing=self.coverage_witnesses
        _require_frozen_coverage_domain(full,"fixture full coverage",complete=True)
        _require_frozen_coverage_domain(missing,"fixture incomplete coverage")
        if missing.covered_ids!=_FROZEN_PRIMITIVE_IDS[:-1]:raise StrictContractError("fixture incomplete coverage changed")
        if type(self.hard_authority_reference) is not DeclaredS0HardAuthorityReference or type(self.predictive_me0_result_reference) is not DeclaredME0ResultReference or type(self.local_tower) is not LocalTower or type(self.similarity_certificate) is not SimilarityCertificate:raise StrictContractError("fixture nested type changed")
        self.local_tower.__post_init__();self.similarity_certificate.__post_init__()
        if self.similarity_certificate.hard_authority_reference!=self.hard_authority_reference or self.similarity_certificate.predictive_me0_result_reference!=self.predictive_me0_result_reference or self.similarity_certificate.measures!=self.measures or self.similarity_certificate.target_residuals!=self.target_residuals or self.similarity_certificate.local_tower!=self.local_tower or self.similarity_certificate.coverage!=full:raise StrictContractError("fixture/certificate binding changed")
    def to_dict(self)->dict[str,Any]:
        self.__post_init__();return {"schema_version":_FIXTURE_SCHEMA,"hard_authority_reference":self.hard_authority_reference.to_dict(),"predictive_me0_result_reference":self.predictive_me0_result_reference.to_dict(),"primitive_rows":[x.to_dict() for x in self.primitive_rows],"coverage_witnesses":[x.to_dict() for x in self.coverage_witnesses],"target_residuals":[x.to_dict() for x in self.target_residuals],"measures":[x.to_dict() for x in self.measures],"local_tower":self.local_tower.to_dict(),"similarity_certificate":self.similarity_certificate.to_dict()}
    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"DeclaredSyntheticSimilarityFixture":
        if cls is not DeclaredSyntheticSimilarityFixture:raise StrictContractError("polymorphic fixture parsing forbidden")
        _bounded_wire_walk(value,"DeclaredSyntheticSimilarityFixture")
        obj=_object(value,("schema_version","hard_authority_reference","predictive_me0_result_reference","primitive_rows","coverage_witnesses","target_residuals","measures","local_tower","similarity_certificate"),"DeclaredSyntheticSimilarityFixture");_fixed(obj["schema_version"],_FIXTURE_SCHEMA,"fixture schema")
        expected=build_declared_synthetic_similarity_fixture(hard_reference=DeclaredS0HardAuthorityReference.from_dict(obj["hard_authority_reference"]),me0_reference=DeclaredME0ResultReference.from_dict(obj["predictive_me0_result_reference"]))
        if canonical_contract_bytes(expected.to_dict())!=canonical_contract_bytes(obj):raise StrictContractError("fixture wire differs from fixed recomputation")
        return expected


def _fixed_levels()->tuple[ApproximationLevelId,...]:
    return tuple(ApproximationLevelId(_FRAME_ID,_DOMAIN_ID,*row) for row in ((1,1,1),(2,1,1),(2,2,1),(2,2,2)))


def _fixed_measure(measure_id:str,level:ApproximationLevelId,node:tuple[ExactRational,...],edge:tuple[ExactRational,...],cross:str="0",numeric:str="0")->GlobalMeasure:
    return make_global_measure(measure_id=measure_id,level=level,node_ids=("n0","n1"),edge_ids=(("n0","n0"),("n0","n1"),("n1","n1")),node_mass=node,edge_mass=edge,cross_covariance_residual=cross,numeric_residual=numeric)


def _manual_transports(me0:DeclaredME0ResultReference,tower:LocalTower,by_id:dict[str,GlobalMeasure],lplus:DeclaredSyntheticLPlusToken,coverage:CountedCoverageWitness,residuals:dict[str,TargetResidualBound])->tuple[tuple[PredictiveTransportCertificate,...],tuple[PositiveTransportCertificate,...]]:
    morphism_rows=_expected_transport_morphism_rows(tower)
    ids=(("u24_s0_s_compose_l1_m","u24_s0_s_compose_l1_m","u24_s0_s_compose_l0_m","u24_s0_s_compose_l0_m"),
         ("u24_s0_s_compose_l2_m","u24_s0_s_compose_l2_m","u24_s0_s_compose_l1_m","u24_s0_s_compose_l1_m"),
         ("u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y","u24_s0_s_compose_l2_m","u24_s0_s_compose_l2_m"),
         ("u24_s0_s_compose_l2_m","u24_s0_s_compose_l2_m","u24_s0_s_compose_l0_m","u24_s0_s_compose_l0_m"),
         ("u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y","u24_s0_s_compose_l1_m","u24_s0_s_compose_l1_m"),
         ("u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y","u24_s0_s_compose_l0_m","u24_s0_s_compose_l0_m"))
    pairs=tuple((*row,msha,e) for row,(msha,e) in zip(ids,morphism_rows))
    predictive=[];positive=[]
    for fx,fy,cx,cy,msha,e in pairs:
        x,y,u,v=by_id[fx],by_id[fy],by_id[cx],by_id[cy]
        fp=compute_predictive_distance(me0_reference=me0,x=x,y=y);cp=compute_predictive_distance(me0_reference=me0,x=u,y=v)
        predictive.append(PredictiveTransportCertificate("PREDICTIVE",_sha256(me0.to_dict()),msha,_predictive_pair_sha(x,y),_predictive_pair_sha(u,v),fp.discrepancy_upper_bound,cp.discrepancy_upper_bound,e,float(cp.discrepancy_upper_bound)<=float(fp.discrepancy_upper_bound)+float(Fraction(e.numerator,e.denominator))))
        fh=compute_positive_distance(l_plus_token=lplus,coverage=coverage,x_target_residual=residuals[fx],y_target_residual=residuals[fy],x=x,y=y);ch=compute_positive_distance(l_plus_token=lplus,coverage=coverage,x_target_residual=residuals[cx],y_target_residual=residuals[cy],x=u,y=v)
        assert fh.safety_majorant is not None and ch.safety_majorant is not None
        positive.append(PositiveTransportCertificate("POSITIVE",msha,_positive_pair_sha(x,y),_positive_pair_sha(u,v),fh.safety_majorant,ch.safety_majorant,e,Fraction(ch.safety_majorant.numerator,ch.safety_majorant.denominator)<=Fraction(fh.safety_majorant.numerator,fh.safety_majorant.denominator)+Fraction(e.numerator,e.denominator)))
    return tuple(predictive),tuple(positive)


def build_declared_synthetic_similarity_fixture(*,hard_reference:Any,me0_reference:Any)->DeclaredSyntheticSimilarityFixture:
    if type(hard_reference) is not DeclaredS0HardAuthorityReference or type(me0_reference) is not DeclaredME0ResultReference:raise StrictContractError("fixture requires exact declared hard/ME0 references")
    rows=_frozen_primitive_rows(); ids=tuple(x.primitive_id for x in rows)
    complete=make_counted_coverage_witness(ordered_universe_ids=ids,covered_ids=ids);incomplete=make_counted_coverage_witness(ordered_universe_ids=ids,covered_ids=ids[:-1])
    lplus=declare_synthetic_l_plus(hard_reference=hard_reference,primitive_rows=rows,coverage=complete)
    L0,L1,L2,L3=_fixed_levels();I=((ExactRational(1),ExactRational(0)),(ExactRational(0),ExactRational(1)));G=((ExactRational(1),ExactRational(1)),(ExactRational(0),ExactRational(0)))
    common=dict(coverage=complete,commutator_l1=ExactRational(0),target_residual_transport=ExactRational(0),cross_covariance_budget="0",numeric_residual_budget="0",remainder_e=ExactRational(1,4))
    tower=build_local_tower(ordered_levels=(L0,L1,L2,L3),radius_morphism=make_radius_morphism(source_level=L1,target_level=L0,node_matrix=I,**common),word_depth_morphism=make_word_depth_morphism(source_level=L2,target_level=L1,node_matrix=I,**common),granularity_morphism=make_granularity_morphism(source_level=L3,target_level=L2,node_matrix=G,**common))
    z,o,h=ExactRational(0),ExactRational(1),ExactRational(1,2);n0=(o,z);e0=(o,z,z);nh=(h,h)
    measures=(
        _fixed_measure("u24_s0_s_id_m",L3,n0,e0),_fixed_measure("u24_s0_s_node_x",L3,n0,e0),_fixed_measure("u24_s0_s_node_y",L3,(z,o),e0),
        _fixed_measure("u24_s0_s_edge_x",L3,nh,e0),_fixed_measure("u24_s0_s_edge_y",L3,nh,(z,z,o)),
        _fixed_measure("u24_s0_s_cross_x",L3,n0,e0,"0.125"),_fixed_measure("u24_s0_s_cross_y",L3,n0,e0),
        _fixed_measure("u24_s0_s_cover_x",L3,n0,e0),_fixed_measure("u24_s0_s_cover_y",L3,n0,e0),
        _fixed_measure("u24_s0_s_zero_m",L3,(z,z),(z,z,z)),
        _fixed_measure("u24_s0_s_compose_l3_x",L3,n0,e0),_fixed_measure("u24_s0_s_compose_l3_y",L3,nh,(h,h,z)),
        _fixed_measure("u24_s0_s_compose_l2_m",L2,n0,e0),_fixed_measure("u24_s0_s_compose_l1_m",L1,n0,e0),_fixed_measure("u24_s0_s_compose_l0_m",L0,n0,e0),
        _fixed_measure("u24_s0_s_numeric_x",L3,n0,e0,"0","0.0625"),_fixed_measure("u24_s0_s_numeric_y",L3,n0,e0))
    by={x.measure_id:x for x in measures}
    target_residuals=tuple(make_target_residual_bound(l_plus_token=lplus,measure_id=x.measure_id,coverage=incomplete if "s_cover" in x.measure_id else complete) for x in measures); residual={x.measure_id:x for x in target_residuals}
    specs=(("s-id","u24_s0_s_id_m","u24_s0_s_id_m",complete,None),("s-node","u24_s0_s_node_x","u24_s0_s_node_y",complete,None),("s-edge","u24_s0_s_edge_x","u24_s0_s_edge_y",complete,None),("s-cross","u24_s0_s_cross_x","u24_s0_s_cross_y",complete,None),("s-cover","u24_s0_s_cover_x","u24_s0_s_cover_y",incomplete,None),("s-zero","u24_s0_s_zero_m","u24_s0_s_zero_m",complete,None),("s-zero-kill","u24_s0_s_zero_m","u24_s0_s_id_m",complete,"ZERO_NONZERO_NORMALIZATION_MISMATCH"),("s-compose","u24_s0_s_compose_l3_x","u24_s0_s_compose_l3_y",complete,None),("s-numeric","u24_s0_s_numeric_x","u24_s0_s_numeric_y",complete,None))
    pred_rows=[];pos_rows=[]
    for cid,xid,yid,cov,error in specs:
        x,y=by[xid],by[yid]
        pred=None if error else compute_predictive_distance(me0_reference=me0_reference,x=x,y=y)
        pos=None if error else compute_positive_distance(l_plus_token=lplus,coverage=cov,x_target_residual=residual[xid],y_target_residual=residual[yid],x=x,y=y)
        pred_rows.append(_case_row(cid,x,y,cov,pred,None,error));pos_rows.append(_case_row(cid,x,y,cov,None,pos,error))
    predictive_transports,positive_transports=_manual_transports(me0_reference,tower,by,lplus,complete,residual)
    finite=certify_finite_remainder(tower=tower,predictive_transport_certificates=predictive_transports,positive_transport_certificates=positive_transports)
    certificate=SimilarityCertificate(hard_reference,me0_reference,_PRIMITIVE_UNIVERSE_SHA,lplus,measures,tower,tuple(pred_rows),tuple(pos_rows),finite,complete,target_residuals)
    return DeclaredSyntheticSimilarityFixture(hard_reference,me0_reference,rows,(complete,incomplete),target_residuals,measures,tower,certificate)


def verify_similarity_certificate(*,certificate:Any)->SimilarityCertificate:
    if type(certificate) is not SimilarityCertificate:raise StrictContractError("similarity verifier requires exact certificate")
    expected=build_declared_synthetic_similarity_fixture(hard_reference=certificate.hard_authority_reference,me0_reference=certificate.predictive_me0_result_reference).similarity_certificate
    if canonical_contract_bytes(expected.to_dict())!=canonical_contract_bytes(certificate.to_dict()):raise StrictContractError("similarity certificate failed full recomputation")
    return certificate


def verify_similarity_certificate_live(*,certificate:Any,hard_binding:Any,me0_binding:Any)->SimilarityCertificate:
    if type(certificate) is not SimilarityCertificate or type(hard_binding) is not LiveS0HardAuthorityBinding or type(me0_binding) is not LiveME0ResultBinding:raise StrictContractError("live similarity verifier requires exact certificate/bindings")
    verify_similarity_certificate(certificate=certificate)
    rebound_hard=bind_s0_hard_authorities(accepted_e1_qualification_envelope=hard_binding.accepted_e1_qualification_envelope,e2_m0_parent_envelope=hard_binding.e2_m0_parent_envelope,e2_support_token=hard_binding.e2_support_token)
    rebound_me0=bind_me0_result(problem=me0_binding.problem,result=me0_binding.result)
    if canonical_contract_bytes(rebound_hard.reference.to_dict())!=canonical_contract_bytes(certificate.hard_authority_reference.to_dict()) or canonical_contract_bytes(rebound_me0.reference.to_dict())!=canonical_contract_bytes(certificate.predictive_me0_result_reference.to_dict()):raise StrictContractError("live similarity authority/reference mismatch")
    return certificate


__all__ = [
    "ApproximationLevelId","PrimitiveTargetRow","CountedCoverageWitness",
    "DeclaredS0HardAuthorityReference","LiveS0HardAuthorityBinding",
    "DeclaredME0ResultReference","LiveME0ResultBinding","DeclaredSyntheticLPlusToken",
    "TargetResidualBound","GlobalMeasure","PredictiveDistance","PositiveDistance",
    "RadiusMorphism","WordDepthMorphism","GranularityMorphism","LocalTower",
    "PredictiveTransportCertificate","PositiveTransportCertificate","FiniteRemainderCertificate",
    "SimilarityCertificate","DeclaredSyntheticSimilarityFixture",
    "make_declared_s0_hard_authority_reference","bind_s0_hard_authorities",
    "make_declared_me0_result_reference","bind_me0_result","declare_synthetic_l_plus",
    "make_counted_coverage_witness","make_target_residual_bound","make_global_measure",
    "compute_predictive_distance","compute_positive_distance","make_radius_morphism",
    "make_word_depth_morphism","make_granularity_morphism","build_local_tower",
    "verify_predictive_transport","verify_positive_transport","certify_finite_remainder",
    "build_declared_synthetic_similarity_fixture","verify_similarity_certificate",
    "verify_similarity_certificate_live",
]
