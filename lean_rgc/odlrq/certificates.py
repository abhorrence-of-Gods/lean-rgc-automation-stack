"""Exact finite E2 endpoint certificates over accepted E1 authorities.

This module implements only the fixed declared synthetic endpoint frozen by
the 2026-07-16 E2 endpoint-semantics authority.  It is deliberately not a
generic matrix, envelope, cocycle, memory, or production-Lean admission API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from math import gcd
import re
from typing import Any

from .adapters import (
    admit_synthetic_finite_snapshot,
    build_synthetic_finite_snapshot,
    make_synthetic_observation_frame_id,
    make_synthetic_transition_semantics_id,
    observation_frame_digest,
)
from .behavioral_partition import refine_exact_partition, verify_exact_partition
from .contracts import (
    CanonicalPayload,
    ExactRational,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    TotalizedStatus,
    canonical_contract_bytes,
)
from .envelope import (
    DeclaredSyntheticTransferLayer,
    FiberCompletenessWitness,
    FiberEnvelope,
    build_fiber_envelope,
    certify_fiber_completeness,
    declare_synthetic_transfer_layer,
)
from .quotient_generator import (
    ExactFiniteFiberLaw,
    ExactQuotientCoordinateGenerator,
    PositiveFiberWeights,
    build_exact_quotient_coordinate_generator,
    make_exact_finite_fiber_law,
    make_positive_fiber_weights,
)


E2_AUTHORITY_COMMIT_SHA = "28c5a29000dddadcaf3e9ad9dd5534554dd67f32"
E2_AUTHORITY_TREE_SHA = "1a71fc6ff774dd0bcf7e4ab551bd737a7a9dab14"
E2_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_e2_endpoint_semantics_authority_amendment_2026-07-16.md"
)
E2_AUTHORITY_DOCUMENT_BLOB_SHA = "139a5992a38269974068858ef00f47f43ef5fca4"
E2_Q1_REPAIR_AUTHORITY_COMMIT_SHA = "fbedf81211b92cb27d4a5a1d8b3091aa08621f26"
E2_Q1_REPAIR_AUTHORITY_TREE_SHA = "8490844d37b4d7815b8e0f3472bf273cd1a88bda"
E2_Q1_REPAIR_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_e2_q1_fixture_repair_authority_2026-07-17.md"
)
E2_Q1_REPAIR_AUTHORITY_DOCUMENT_BLOB_SHA = (
    "263d6ea3e012806f0941008267336a3b3d2128ad"
)

_ENDPOINT_ID = "u24_e2_declared_square_endpoint_v1"
_BASIS_CONVENTION = "target_row_source_column_v1"
_COORDINATES = ("OPEN_0", "OPEN_1", "CLOSED", "SINK")
_RETAINED = ("OPEN_0", "OPEN_1")
_COMPLEMENT = ("CLOSED", "SINK")
_ROLES = (
    "RETAINED_OPEN",
    "RETAINED_OPEN",
    "TERMINAL_CLOSED",
    "TERMINAL_SINK",
)
_P_COORDINATES = ("OPEN_0",)
_Q_COORDINATES = ("OPEN_1",)

_IDENTIFICATION_SCHEMA = "odlrq.e2.source-target-coordinate-identification.v1"
_RESTRICTION_SCHEMA = "odlrq.e2.envelope-restriction.v1"
_SAFETY_SCHEMA = "odlrq.e2.lifting-uniform-safety.v1"
_SPLIT_SCHEMA = "odlrq.e2.resolved-memory-split.v1"
_COCYCLE_SCHEMA = "odlrq.e2.cocycle-certificate.v1"
_RETURN_SCHEMA = "odlrq.e2.finite-return-memory.v1"

_MAX_E2_CANONICAL_WIRE_BYTES = 1_048_576
_MAX_E2_NESTING_DEPTH = 12
_MAX_E2_STRUCTURAL_NODES = 4_096
_MAX_E2_UTF8_SCALAR_BYTES = 262_144
_MAX_E2_COORDINATES = 4
_MAX_E2_RAW_SOURCE_MEMBERS = 5
_MAX_E2_RAW_TARGET_MEMBERS = 4
_MAX_E2_MATRIX_CELLS = 16
_MAX_E2_CANDIDATE_LOAD_ROWS = 20
_MAX_E2_HORIZON = 3
_MAX_E2_RETURN_TERMS = 3
_MAX_E2_DERIVATION_WORK_UNITS = 256

_IDENTIFICATION_SEAL = object()
_RESTRICTION_SEAL = object()
_SAFETY_SEAL = object()
_SPLIT_SEAL = object()
_COCYCLE_SEAL = object()
_RETURN_SEAL = object()

_PARENT_MATRICES: dict[str, tuple[tuple[ExactRational, ...], ...]] = {
    "M0": (
        (ExactRational(1), ExactRational(2), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(1, 2), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
    ),
    "M1": (
        (ExactRational(1, 2), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(3), ExactRational(1), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
    ),
    "MRET": (
        (ExactRational(0), ExactRational(2), ExactRational(0), ExactRational(0)),
        (ExactRational(3), ExactRational(1, 2), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
    ),
    "NONNORMAL": (
        (ExactRational(1), ExactRational(10), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(1), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
    ),
    "NILPOTENT": (
        (ExactRational(0), ExactRational(1), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
        (ExactRational(0), ExactRational(0), ExactRational(0), ExactRational(0)),
    ),
}

_SOURCE_MEMBER_GROUPS = {
    "OPEN_0": (
        "unit_cpu_survivor_u24_e2_source_open0_a",
        "unit_cpu_survivor_u24_e2_source_open0_b",
    ),
    "OPEN_1": ("unit_cpu_survivor_u24_e2_source_open1",),
    "CLOSED": ("unit_cpu_survivor_u24_e2_source_closed",),
    "SINK": ("unit_cpu_survivor_u24_e2_source_sink",),
}
_TARGET_MEMBER_GROUPS = {
    "OPEN_0": ("unit_cpu_survivor_u24_e2_target_open0",),
    "OPEN_1": ("unit_cpu_survivor_u24_e2_target_open1",),
    "CLOSED": ("unit_cpu_survivor_u24_e2_target_closed",),
    "SINK": ("unit_cpu_survivor_u24_e2_target_sink",),
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _same_wire(left: Any, right: Any) -> bool:
    return canonical_contract_bytes(left) == canonical_contract_bytes(right)


def _exact_fields(value: Any, expected: tuple[str, ...], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(value) != len(expected):
        raise StrictContractError(f"{where} field count mismatch")
    for name in expected:
        if name not in value:
            raise StrictContractError(f"{where} is missing field {name!r}")
    if any(name not in expected for name in value):
        raise StrictContractError(f"{where} has an unknown field")
    return value


def _exact_array(value: Any, count: int, where: str) -> list[Any]:
    if type(value) is not list or len(value) != count:
        raise StrictContractError(f"{where} must be an exact {count}-row array")
    return value


def _exact_string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    return value


def _fixed(value: Any, expected: Any, where: str) -> Any:
    if type(value) is not type(expected) or value != expected:
        raise StrictContractError(f"{where} must equal {expected!r}")
    return value


def _digest(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value != value.upper()
        or any(ch not in "0123456789ABCDEF" for ch in value)
    ):
        raise StrictContractError(f"{where} must be canonical uppercase SHA-256")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictContractError(f"{where} must be an exact boolean")
    return value


def _nonnegative_int(value: Any, where: str, upper: int) -> int:
    if type(value) is not int or value < 0 or value > upper:
        raise StrictContractError(
            f"{where} must be an exact nonnegative integer at most {upper}"
        )
    return value


def _string_json_size(value: str) -> int:
    total = 2
    for character in value:
        code = ord(character)
        if character in {'"', "\\"} or character in "\b\f\n\r\t":
            total += 2
        elif code < 0x20:
            total += 6
        elif 0xD800 <= code <= 0xDFFF:
            raise StrictContractError("E2 wire contains a non-UTF-8 surrogate")
        elif code <= 0x7F:
            total += 1
        elif code <= 0x7FF:
            total += 2
        elif code <= 0xFFFF:
            total += 3
        else:
            total += 4
        if total > _MAX_E2_UTF8_SCALAR_BYTES:
            raise StrictContractError("E2 scalar exceeds its UTF-8 preflight cap")
    return total


def _bounded_structural_preflight(value: Any) -> None:
    nodes = 0
    scalar_bytes = 0
    active: set[int] = set()

    def visit(item: Any, depth: int) -> int:
        nonlocal nodes, scalar_bytes
        if depth > _MAX_E2_NESTING_DEPTH:
            raise StrictContractError("E2 wire exceeds its nesting-depth cap")
        nodes += 1
        if nodes > _MAX_E2_STRUCTURAL_NODES:
            raise StrictContractError("E2 wire exceeds its structural-node cap")
        if item is None:
            scalar_bytes += 4
            size = 4
        elif type(item) is bool:
            size = 4 if item else 5
            scalar_bytes += size
        elif type(item) is int:
            if item.bit_length() > 870_000:
                raise StrictContractError("E2 integer scalar exceeds its preflight cap")
            try:
                rendered_integer = str(item)
            except ValueError as exc:
                # CPython's interpreter-wide decimal conversion guard can be
                # stricter than the frozen E2 scalar-byte cap.  An already-
                # decoded hostile integer must still fail through the strict
                # contract boundary rather than leaking a built-in error.
                raise StrictContractError(
                    "E2 integer scalar exceeds the bounded conversion domain"
                ) from exc
            size = len(rendered_integer.encode("ascii"))
            scalar_bytes += size
        elif type(item) is str:
            size = _string_json_size(item)
            scalar_bytes += size
        elif type(item) is list:
            identity = id(item)
            if identity in active:
                raise StrictContractError("E2 wire contains a reference cycle")
            active.add(identity)
            size = 2 + max(0, len(item) - 1)
            for child in item:
                size += visit(child, depth + 1)
            active.remove(identity)
        elif type(item) is dict:
            identity = id(item)
            if identity in active:
                raise StrictContractError("E2 wire contains a reference cycle")
            active.add(identity)
            size = 2 + max(0, len(item) - 1)
            for key, child in item.items():
                if type(key) is not str:
                    raise StrictContractError("E2 wire object keys must be exact strings")
                nodes += 1
                if nodes > _MAX_E2_STRUCTURAL_NODES:
                    raise StrictContractError("E2 wire exceeds its structural-node cap")
                key_size = _string_json_size(key)
                scalar_bytes += key_size
                size += key_size + 1 + visit(child, depth + 1)
            active.remove(identity)
        else:
            raise StrictContractError(
                f"E2 wire contains non-strict JSON type {type(item).__name__}"
            )
        if scalar_bytes > _MAX_E2_UTF8_SCALAR_BYTES:
            raise StrictContractError("E2 wire exceeds its scalar-byte cap")
        if size > _MAX_E2_CANONICAL_WIRE_BYTES:
            raise StrictContractError("E2 wire exceeds its canonical-byte cap")
        return size

    total = visit(value, 1)
    if total > _MAX_E2_CANONICAL_WIRE_BYTES:
        raise StrictContractError("E2 wire exceeds its canonical-byte cap")


def _preflight_rational(value: Any, where: str) -> None:
    row = _exact_fields(
        value, ("schema_version", "numerator", "denominator"), where
    )
    for name in ("schema_version", "numerator", "denominator"):
        _exact_string(row[name], f"{where} {name}")


def _rational(value: Any, where: str) -> ExactRational:
    _preflight_rational(value, where)
    return ExactRational.from_dict(value)


def _matrix_preflight(value: Any, rows: int, columns: int, where: str) -> None:
    matrix = _exact_array(value, rows, where)
    if rows * columns > _MAX_E2_MATRIX_CELLS:
        raise StrictContractError("E2 matrix exceeds its cell cap")
    for row_index, row in enumerate(matrix):
        exact_row = _exact_array(row, columns, f"{where} row {row_index}")
        for column_index, item in enumerate(exact_row):
            _preflight_rational(item, f"{where} [{row_index},{column_index}]")


def _matrix_from_wire(value: list[Any]) -> tuple[tuple[ExactRational, ...], ...]:
    return tuple(tuple(ExactRational.from_dict(item) for item in row) for row in value)


def _matrix_wire(
    value: tuple[tuple[ExactRational, ...], ...]
) -> list[list[dict[str, Any]]]:
    return [[entry.to_dict() for entry in row] for row in value]


def _add(left: ExactRational, right: ExactRational) -> ExactRational:
    return ExactRational(
        left.numerator * right.denominator + right.numerator * left.denominator,
        left.denominator * right.denominator,
    )


def _multiply(left: ExactRational, right: ExactRational) -> ExactRational:
    return ExactRational(
        left.numerator * right.numerator,
        left.denominator * right.denominator,
    )


def _absolute(value: ExactRational) -> ExactRational:
    return ExactRational(abs(value.numerator), value.denominator)


def _divide(left: ExactRational, right: ExactRational) -> ExactRational:
    if right.numerator == 0:
        raise StrictContractError("E2 exact division by zero is forbidden")
    sign = -1 if right.numerator < 0 else 1
    return ExactRational(
        sign * left.numerator * right.denominator,
        left.denominator * abs(right.numerator),
    )


def _less(left: ExactRational, right: ExactRational) -> bool:
    return left.numerator * right.denominator < right.numerator * left.denominator


def _positive(value: ExactRational, where: str) -> ExactRational:
    if type(value) is not ExactRational or value.numerator <= 0:
        raise StrictContractError(f"{where} must be an exact positive rational")
    return value


def _matrix_multiply(
    left: tuple[tuple[ExactRational, ...], ...],
    right: tuple[tuple[ExactRational, ...], ...],
) -> tuple[tuple[ExactRational, ...], ...]:
    if not left or not right or len(left[0]) != len(right):
        raise StrictContractError("E2 matrix product dimensions are incompatible")
    result: list[tuple[ExactRational, ...]] = []
    for left_row in left:
        if not left_row:
            raise StrictContractError("E2 matrix product has an empty inner dimension")
        output_row = []
        for column in range(len(right[0])):
            total = _multiply(left_row[0], right[0][column])
            for inner, left_value in enumerate(left_row[1:], start=1):
                total = _add(total, _multiply(left_value, right[inner][column]))
            output_row.append(total)
        result.append(tuple(output_row))
    return tuple(result)


def _weight_property(
    role: str, coordinate_ids: tuple[str, ...], values: tuple[ExactRational, ...]
) -> dict[str, Any]:
    return {
        "schema_version": "odlrq.e2.weight-vector-property.v1",
        "endpoint_id": _ENDPOINT_ID,
        "role": role,
        "coordinate_ids": list(coordinate_ids),
        "values": [value.to_dict() for value in values],
    }


def _require_work(
    name: str,
    *,
    source_members: int = 5,
    target_members: int = 4,
    coordinates: int = 4,
    candidate_loads: int = 20,
    horizon: int = 3,
    return_terms: int = 3,
) -> None:
    for value, maximum, label in (
        (source_members, _MAX_E2_RAW_SOURCE_MEMBERS, "source members"),
        (target_members, _MAX_E2_RAW_TARGET_MEMBERS, "target members"),
        (coordinates, _MAX_E2_COORDINATES, "coordinates"),
        (candidate_loads, _MAX_E2_CANDIDATE_LOAD_ROWS, "candidate loads"),
        (horizon, _MAX_E2_HORIZON, "horizon"),
        (return_terms, _MAX_E2_RETURN_TERMS, "return terms"),
    ):
        if type(value) is not int or value < 0 or value > maximum:
            raise StrictContractError(f"E2 {label} exceed the frozen work schedule")
    schedules = {
        "identify": 9 + source_members + target_members + coordinates + coordinates * coordinates,
        "restriction": candidate_loads + coordinates + coordinates * coordinates + coordinates,
        "safety": candidate_loads + coordinates * coordinates + coordinates + coordinates + 1,
        "split": coordinates * coordinates + coordinates,
        "cocycle": 2 * coordinates * coordinates + 3 * coordinates + coordinates,
        "return": horizon * (coordinates * coordinates + coordinates) + return_terms,
    }
    units = schedules.get(name)
    if type(units) is not int or units > _MAX_E2_DERIVATION_WORK_UNITS:
        raise StrictContractError("E2 derivation schedule exceeds its frozen cap")


def _payload(kind: str, name: str) -> CanonicalPayload:
    return CanonicalPayload.from_value({"kind": kind, "name": name})


def _build_fixture_generator(role: str) -> ExactQuotientCoordinateGenerator:
    if role == "source":
        environment = "53" * 32
        action_id = "unit_cpu_survivor_u24_e2_source_a"
        state_rows = (
            ("unit_cpu_survivor_u24_e2_source_open0_a", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open0_b", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_source_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_source_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_source_sink", TotalizedStatus.SINK, 3),
        )
    elif role == "target":
        environment = "54" * 32
        action_id = "unit_cpu_survivor_u24_e2_target_a"
        state_rows = (
            ("unit_cpu_survivor_u24_e2_target_open0", TotalizedStatus.OPEN, 0),
            ("unit_cpu_survivor_u24_e2_target_open1", TotalizedStatus.OPEN, 1),
            ("unit_cpu_survivor_u24_e2_target_closed", TotalizedStatus.CLOSED, 2),
            ("unit_cpu_survivor_u24_e2_target_sink", TotalizedStatus.SINK, 3),
        )
    else:
        raise StrictContractError("E2 fixture role is invalid")
    action = SyntheticAction(action_id, _payload("action", action_id))
    vocabulary = ResponseVocabularyId.from_coordinate_names(("e2_coordinate",))
    frame = make_synthetic_observation_frame_id(
        environment_digest=environment, response_vocabulary_id=vocabulary
    )
    semantics = make_synthetic_transition_semantics_id(
        actions=(action,), response_vocabulary_id=vocabulary
    )
    frame_sha = observation_frame_digest(frame)
    states = tuple(
        SyntheticTotalizedState(
            state_id=state_id,
            payload=_payload("state", state_id),
            totalized_kind=kind,
            response_coordinates=(ExactRational(coordinate),),
            frame_digest=frame_sha,
        )
        for state_id, kind, coordinate in state_rows
    )
    transitions = tuple(
        SyntheticTransitionRow(
            source_state_id=state.state_id,
            action_id=action.action_id,
            target_state_id=state.state_id,
            transition_semantics_digest=semantics.semantics_digest,
        )
        for state in states
    )
    snapshot = build_synthetic_finite_snapshot(
        environment_digest=environment,
        coordinate_names=("e2_coordinate",),
        seed_state_ids=tuple(
            state.state_id
            for state in states
            if state.totalized_kind is TotalizedStatus.OPEN
        ),
        states=states,
        actions=(action,),
        transitions=transitions,
    )
    admitted = admit_synthetic_finite_snapshot(snapshot)
    certificate = refine_exact_partition(admitted)
    verified = verify_exact_partition(admitted, certificate)
    return build_exact_quotient_coordinate_generator(verified)


def _build_canonical_fixture(parent_id: str, law_variant: str) -> dict[str, Any]:
    if parent_id not in _PARENT_MATRICES:
        raise StrictContractError("E2 parent ID is not declared")
    if law_variant not in {"PRIMARY", "ALTERNATE_M0_DIAGNOSTIC"}:
        raise StrictContractError("E2 source-law variant is invalid")
    if law_variant == "ALTERNATE_M0_DIAGNOSTIC" and parent_id != "M0":
        raise StrictContractError("alternate E2 law is admitted only for M0")
    source = _build_fixture_generator("source")
    target = _build_fixture_generator("target")
    matrix = _PARENT_MATRICES[parent_id]
    coefficients: list[tuple[str, str, ExactRational]] = []
    target_members = (
        "unit_cpu_survivor_u24_e2_target_open0",
        "unit_cpu_survivor_u24_e2_target_open1",
    )
    for target_coordinate, target_member in enumerate(target_members):
        open0 = matrix[target_coordinate][0]
        open1 = matrix[target_coordinate][1]
        if open0.numerator != 0:
            coefficients.extend(
                (
                    (
                        target_member,
                        "unit_cpu_survivor_u24_e2_source_open0_a",
                        open0,
                    ),
                    (
                        target_member,
                        "unit_cpu_survivor_u24_e2_source_open0_b",
                        ExactRational(-open0.numerator, open0.denominator),
                    ),
                )
            )
        if open1.numerator != 0:
            coefficients.append(
                (target_member, "unit_cpu_survivor_u24_e2_source_open1", open1)
            )
    layer = declare_synthetic_transfer_layer(source, target, tuple(coefficients))
    source_ids = tuple(
        member for coordinate in _COORDINATES for member in _SOURCE_MEMBER_GROUPS[coordinate]
    )
    target_ids = tuple(
        member for coordinate in _COORDINATES for member in _TARGET_MEMBER_GROUPS[coordinate]
    )
    source_weights = make_positive_fiber_weights(
        source, {member: ExactRational(1) for member in source_ids}
    )
    target_weights = make_positive_fiber_weights(
        target, {member: ExactRational(1) for member in target_ids}
    )
    if law_variant == "PRIMARY":
        open0_probabilities = (ExactRational(1, 3), ExactRational(2, 3))
    else:
        open0_probabilities = (ExactRational(2, 3), ExactRational(1, 3))
    law_values = {
        "unit_cpu_survivor_u24_e2_source_open0_a": open0_probabilities[0],
        "unit_cpu_survivor_u24_e2_source_open0_b": open0_probabilities[1],
        "unit_cpu_survivor_u24_e2_source_open1": ExactRational(1),
        "unit_cpu_survivor_u24_e2_source_closed": ExactRational(1),
        "unit_cpu_survivor_u24_e2_source_sink": ExactRational(1),
    }
    source_law = make_exact_finite_fiber_law(source, law_values)
    source_completeness = certify_fiber_completeness(layer, "source")
    target_completeness = certify_fiber_completeness(layer, "target")
    envelope = build_fiber_envelope(
        layer,
        source_weights,
        target_weights,
        source_law,
        source_completeness,
        target_completeness,
    )
    return {
        "source_generator": source,
        "target_generator": target,
        "layer": layer,
        "source_weights": source_weights,
        "target_weights": target_weights,
        "source_law": source_law,
        "source_completeness": source_completeness,
        "target_completeness": target_completeness,
        "envelope": envelope,
    }


def _block_for_members(frame_wire: dict[str, Any], members: tuple[str, ...]) -> int:
    matches = [
        block["block_index"]
        for block in frame_wire["blocks"]
        if [row["member_id"] for row in block["members"]] == list(members)
    ]
    if len(matches) != 1:
        raise StrictContractError("E2 coordinate is not a unique complete E1 block")
    return matches[0]


def _member_rows(
    frame_wire: dict[str, Any], block_index: int
) -> list[dict[str, Any]]:
    for block in frame_wire["blocks"]:
        if block["block_index"] == block_index:
            return block["members"]
    raise StrictContractError("E2 coordinate block is absent from the retained frame")


def _common_block_weight(
    weights_wire: dict[str, Any], member_ids: tuple[str, ...], where: str
) -> ExactRational:
    by_member = {
        row["member_id"]: ExactRational.from_dict(row["weight"])
        for row in weights_wire["rows"]
    }
    if set(member_ids) - set(by_member):
        raise StrictContractError(f"{where} is missing a complete member weight")
    values = tuple(by_member[member] for member in member_ids)
    if not values or any(value != values[0] for value in values[1:]):
        raise StrictContractError(f"{where} has unequal within-block weights")
    return _positive(values[0], where)


def _majorants_from_validated_envelope_wire(
    envelope_wire: dict[str, Any],
    expected_pairs: tuple[tuple[int, int], ...],
    where: str,
) -> dict[tuple[int, int], ExactRational]:
    """Index one already validated envelope without rederiving its authorities."""

    cells = envelope_wire.get("cells")
    if type(cells) is not list or len(cells) != len(expected_pairs):
        raise StrictContractError(f"{where} cell coverage is incomplete")
    expected_pair_set = set(expected_pairs)
    if len(expected_pair_set) != len(expected_pairs):
        raise StrictContractError(f"{where} expected block pairs are not unique")
    by_pair: dict[tuple[int, int], ExactRational] = {}
    for cell in cells:
        if type(cell) is not dict:
            raise StrictContractError(f"{where} cell is not an exact object")
        target_block = cell.get("target_block_index")
        source_block = cell.get("source_block_index")
        if type(target_block) is not int or type(source_block) is not int:
            raise StrictContractError(f"{where} block index is not an exact integer")
        pair = (target_block, source_block)
        if pair in by_pair:
            raise StrictContractError(f"{where} contains a duplicate block pair")
        by_pair[pair] = ExactRational.from_dict(cell.get("majorant"))
    if set(by_pair) != expected_pair_set:
        raise StrictContractError(f"{where} block-pair coverage changed")
    return by_pair


def _validate_e1_bundle(
    *,
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    expected_authority_bytes: tuple[bytes, ...] | None = None,
) -> dict[str, Any]:
    exact_types = (
        (envelope, FiberEnvelope, "envelope"),
        (layer, DeclaredSyntheticTransferLayer, "layer"),
        (source_generator, ExactQuotientCoordinateGenerator, "source generator"),
        (target_generator, ExactQuotientCoordinateGenerator, "target generator"),
        (source_weights, PositiveFiberWeights, "source weights"),
        (target_weights, PositiveFiberWeights, "target weights"),
        (source_law, ExactFiniteFiberLaw, "source law"),
        (source_completeness, FiberCompletenessWitness, "source completeness"),
        (target_completeness, FiberCompletenessWitness, "target completeness"),
    )
    for value, expected, label in exact_types:
        if type(value) is not expected:
            raise StrictContractError(f"E2 {label} has the wrong exact type")

    source_generator_wire = source_generator.to_dict()
    target_generator_wire = target_generator.to_dict()
    layer_wire = layer.to_dict()
    source_weights_wire = source_weights.to_dict()
    target_weights_wire = target_weights.to_dict()
    source_law_wire = source_law.to_dict()
    source_completeness_wire = source_completeness.to_dict()
    target_completeness_wire = target_completeness.to_dict()
    envelope_wire = envelope.to_dict()

    # Re-enter every accepted public parser before using any E2 coordinate.
    DeclaredSyntheticTransferLayer.from_dict(
        layer_wire, source_generator, target_generator
    )
    PositiveFiberWeights.from_dict(source_weights_wire, source_generator)
    PositiveFiberWeights.from_dict(target_weights_wire, target_generator)
    ExactFiniteFiberLaw.from_dict(source_law_wire, source_generator)
    FiberCompletenessWitness.from_dict(source_completeness_wire, layer)
    FiberCompletenessWitness.from_dict(target_completeness_wire, layer)
    FiberEnvelope.from_dict(
        envelope_wire,
        layer,
        source_weights,
        target_weights,
        source_law,
        source_completeness,
        target_completeness,
    )

    if (
        layer_wire["source_generator_sha256"] != _sha256(source_generator_wire)
        or layer_wire["target_generator_sha256"] != _sha256(target_generator_wire)
        or envelope_wire["layer_sha256"] != _sha256(layer_wire)
        or envelope_wire["source_weights_sha256"] != _sha256(source_weights_wire)
        or envelope_wire["target_weights_sha256"] != _sha256(target_weights_wire)
        or envelope_wire["source_law_sha256"] != _sha256(source_law_wire)
        or envelope_wire["source_completeness_sha256"]
        != _sha256(source_completeness_wire)
        or envelope_wire["target_completeness_sha256"]
        != _sha256(target_completeness_wire)
    ):
        raise StrictContractError("E2 E1 authority digests are not mutually bound")

    source_frame = source_completeness_wire["frame"]
    target_frame = target_completeness_wire["frame"]
    if (
        source_frame != layer_wire["source_frame"]
        or target_frame != layer_wire["target_frame"]
        or source_frame["member_count"] != _MAX_E2_RAW_SOURCE_MEMBERS
        or target_frame["member_count"] != _MAX_E2_RAW_TARGET_MEMBERS
        or source_frame["block_count"] != _MAX_E2_COORDINATES
        or target_frame["block_count"] != _MAX_E2_COORDINATES
    ):
        raise StrictContractError("E2 fixture has the wrong complete E1 frame")
    _require_work(
        "identify",
        source_members=source_frame["member_count"],
        target_members=target_frame["member_count"],
        coordinates=source_frame["block_count"],
    )

    source_blocks = {
        coordinate: _block_for_members(source_frame, _SOURCE_MEMBER_GROUPS[coordinate])
        for coordinate in _COORDINATES
    }
    target_blocks = {
        coordinate: _block_for_members(target_frame, _TARGET_MEMBER_GROUPS[coordinate])
        for coordinate in _COORDINATES
    }
    if len(set(source_blocks.values())) != 4 or len(set(target_blocks.values())) != 4:
        raise StrictContractError("E2 coordinate maps are not bijections")

    expected_block_pairs = tuple(
        (
            target_blocks[target_coordinate],
            source_blocks[source_coordinate],
        )
        for target_coordinate in _COORDINATES
        for source_coordinate in _COORDINATES
    )
    majorants = _majorants_from_validated_envelope_wire(
        envelope_wire,
        expected_block_pairs,
        "E2 canonical envelope",
    )
    full_matrix = tuple(
        tuple(
            majorants[
                (
                    target_blocks[target_coordinate],
                    source_blocks[source_coordinate],
                )
            ]
            for source_coordinate in _COORDINATES
        )
        for target_coordinate in _COORDINATES
    )
    parent_matches = [
        parent_id
        for parent_id, expected_matrix in _PARENT_MATRICES.items()
        if full_matrix == expected_matrix
    ]
    if len(parent_matches) != 1:
        raise StrictContractError("E2 parent matrix has zero or multiple fixture matches")
    parent_id = parent_matches[0]

    probabilities = {
        row["member_id"]: ExactRational.from_dict(row["probability"])
        for row in source_law_wire["rows"]
    }
    primary = {
        "unit_cpu_survivor_u24_e2_source_open0_a": ExactRational(1, 3),
        "unit_cpu_survivor_u24_e2_source_open0_b": ExactRational(2, 3),
        "unit_cpu_survivor_u24_e2_source_open1": ExactRational(1),
        "unit_cpu_survivor_u24_e2_source_closed": ExactRational(1),
        "unit_cpu_survivor_u24_e2_source_sink": ExactRational(1),
    }
    alternate = dict(primary)
    alternate["unit_cpu_survivor_u24_e2_source_open0_a"] = ExactRational(2, 3)
    alternate["unit_cpu_survivor_u24_e2_source_open0_b"] = ExactRational(1, 3)
    if probabilities == primary:
        law_variant = "PRIMARY"
    elif parent_id == "M0" and probabilities == alternate:
        law_variant = "ALTERNATE_M0_DIAGNOSTIC"
    else:
        raise StrictContractError("E2 source law is outside the fixed role/law table")

    supplied_wires = {
        "source_generator": source_generator_wire,
        "target_generator": target_generator_wire,
        "layer": layer_wire,
        "source_weights": source_weights_wire,
        "target_weights": target_weights_wire,
        "source_law": source_law_wire,
        "source_completeness": source_completeness_wire,
        "target_completeness": target_completeness_wire,
        "envelope": envelope_wire,
    }
    if expected_authority_bytes is None:
        expected = _build_canonical_fixture(parent_id, law_variant)
        expected_bytes = tuple(
            canonical_contract_bytes(expected[name].to_dict())
            for name in supplied_wires
        )
    else:
        expected_bytes = expected_authority_bytes
    if len(expected_bytes) != len(supplied_wires):
        raise StrictContractError("E2 retained canonical fixture seal is malformed")
    for (name, supplied_wire), expected_wire_bytes in zip(
        supplied_wires.items(), expected_bytes, strict=True
    ):
        if canonical_contract_bytes(supplied_wire) != expected_wire_bytes:
            raise StrictContractError(
                f"E2 {name} does not equal the complete canonical fixture"
            )

    return {
        **supplied_wires,
        "source_frame": source_frame,
        "target_frame": target_frame,
        "source_blocks": source_blocks,
        "target_blocks": target_blocks,
        "full_matrix": full_matrix,
        "parent_id": parent_id,
        "law_variant": law_variant,
    }


_IDENTIFICATION_FIELDS = (
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "basis_convention",
    "parent_envelope_sha256",
    "layer_sha256",
    "source_generator_sha256",
    "target_generator_sha256",
    "source_weights_sha256",
    "target_weights_sha256",
    "source_law_sha256",
    "source_completeness_sha256",
    "target_completeness_sha256",
    "full_coordinate_ids",
    "source_block_count",
    "target_block_count",
    "coordinate_rows",
    "coordinate_core_sha256",
    "verification_disposition",
)
_COORDINATE_ROW_FIELDS = (
    "coordinate_id",
    "coordinate_role",
    "source_block_index",
    "target_block_index",
    "source_member_ids",
    "target_member_ids",
    "source_member_set_sha256",
    "target_member_set_sha256",
    "source_weight",
    "target_weight",
)


def _preflight_identification_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _IDENTIFICATION_FIELDS, "E2 identification")
    rows = _exact_array(wire["coordinate_rows"], 4, "E2 coordinate rows")
    _exact_array(wire["full_coordinate_ids"], 4, "E2 full coordinates")
    _bounded_structural_preflight(wire)
    _fixed(wire["schema_version"], _IDENTIFICATION_SCHEMA, "E2 identification schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 identification endpoint")
    _fixed(wire["basis_convention"], _BASIS_CONVENTION, "E2 identification basis")
    _fixed(wire["full_coordinate_ids"], list(_COORDINATES), "E2 full coordinates")
    parent_id = _exact_string(wire["parent_id"], "E2 identification parent")
    law_variant = _exact_string(
        wire["source_law_variant"], "E2 identification law variant"
    )
    if parent_id not in _PARENT_MATRICES:
        raise StrictContractError("E2 identification parent is invalid")
    if law_variant not in {
        "PRIMARY",
        "ALTERNATE_M0_DIAGNOSTIC",
    }:
        raise StrictContractError("E2 identification law variant is invalid")
    for name in (
        "parent_envelope_sha256",
        "layer_sha256",
        "source_generator_sha256",
        "target_generator_sha256",
        "source_weights_sha256",
        "target_weights_sha256",
        "source_law_sha256",
        "source_completeness_sha256",
        "target_completeness_sha256",
        "coordinate_core_sha256",
    ):
        _digest(wire[name], f"E2 identification {name}")
    _nonnegative_int(wire["source_block_count"], "E2 source blocks", 4)
    _nonnegative_int(wire["target_block_count"], "E2 target blocks", 4)
    for index, raw_row in enumerate(rows):
        row = _exact_fields(raw_row, _COORDINATE_ROW_FIELDS, f"E2 coordinate row {index}")
        _fixed(row["coordinate_id"], _COORDINATES[index], "E2 coordinate ID")
        _fixed(row["coordinate_role"], _ROLES[index], "E2 coordinate role")
        _nonnegative_int(row["source_block_index"], "E2 source block", 3)
        _nonnegative_int(row["target_block_index"], "E2 target block", 3)
        source_members = row["source_member_ids"]
        target_members = row["target_member_ids"]
        if (
            type(source_members) is not list
            or not 1 <= len(source_members) <= 2
            or type(target_members) is not list
            or len(target_members) != 1
            or any(type(member) is not str or not member for member in source_members)
            or any(type(member) is not str or not member for member in target_members)
        ):
            raise StrictContractError("E2 coordinate member arrays are malformed")
        _digest(row["source_member_set_sha256"], "E2 source member-set SHA")
        _digest(row["target_member_set_sha256"], "E2 target member-set SHA")
        _rational(row["source_weight"], "E2 source coordinate weight")
        _rational(row["target_weight"], "E2 target coordinate weight")
    _fixed(
        wire["verification_disposition"],
        "E2_SOURCE_TARGET_COORDINATES_IDENTIFIED",
        "E2 identification disposition",
    )
    return wire


def _derive_identification_wire(
    *,
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    expected_authority_bytes: tuple[bytes, ...] | None = None,
) -> dict[str, Any]:
    context = _validate_e1_bundle(
        envelope=envelope,
        layer=layer,
        source_generator=source_generator,
        target_generator=target_generator,
        source_weights=source_weights,
        target_weights=target_weights,
        source_law=source_law,
        source_completeness=source_completeness,
        target_completeness=target_completeness,
        expected_authority_bytes=expected_authority_bytes,
    )
    coordinate_rows = []
    for coordinate, role in zip(_COORDINATES, _ROLES, strict=True):
        source_block = context["source_blocks"][coordinate]
        target_block = context["target_blocks"][coordinate]
        source_members = _member_rows(context["source_frame"], source_block)
        target_members = _member_rows(context["target_frame"], target_block)
        source_member_ids = tuple(row["member_id"] for row in source_members)
        target_member_ids = tuple(row["member_id"] for row in target_members)
        source_member_property = {
            "schema_version": "odlrq.e2.member-set-property.v1",
            "side": "SOURCE",
            "coordinate_id": coordinate,
            "members": source_members,
        }
        target_member_property = {
            "schema_version": "odlrq.e2.member-set-property.v1",
            "side": "TARGET",
            "coordinate_id": coordinate,
            "members": target_members,
        }
        coordinate_rows.append(
            {
                "coordinate_id": coordinate,
                "coordinate_role": role,
                "source_block_index": source_block,
                "target_block_index": target_block,
                "source_member_ids": list(source_member_ids),
                "target_member_ids": list(target_member_ids),
                "source_member_set_sha256": _sha256(source_member_property),
                "target_member_set_sha256": _sha256(target_member_property),
                "source_weight": _common_block_weight(
                    context["source_weights"], source_member_ids, "E2 source block weight"
                ).to_dict(),
                "target_weight": _common_block_weight(
                    context["target_weights"], target_member_ids, "E2 target block weight"
                ).to_dict(),
            }
        )
    coordinate_core = {
        "schema_version": "odlrq.e2.coordinate-core.v1",
        "endpoint_id": _ENDPOINT_ID,
        "basis_convention": _BASIS_CONVENTION,
        "layer_sha256": _sha256(context["layer"]),
        "source_generator_sha256": _sha256(context["source_generator"]),
        "target_generator_sha256": _sha256(context["target_generator"]),
        "source_weights_sha256": _sha256(context["source_weights"]),
        "target_weights_sha256": _sha256(context["target_weights"]),
        "source_completeness_sha256": _sha256(context["source_completeness"]),
        "target_completeness_sha256": _sha256(context["target_completeness"]),
        "full_coordinate_ids": list(_COORDINATES),
        "coordinate_rows": coordinate_rows,
    }
    return {
        "schema_version": _IDENTIFICATION_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "parent_id": context["parent_id"],
        "source_law_variant": context["law_variant"],
        "basis_convention": _BASIS_CONVENTION,
        "parent_envelope_sha256": _sha256(context["envelope"]),
        "layer_sha256": coordinate_core["layer_sha256"],
        "source_generator_sha256": coordinate_core["source_generator_sha256"],
        "target_generator_sha256": coordinate_core["target_generator_sha256"],
        "source_weights_sha256": coordinate_core["source_weights_sha256"],
        "target_weights_sha256": coordinate_core["target_weights_sha256"],
        "source_law_sha256": _sha256(context["source_law"]),
        "source_completeness_sha256": coordinate_core[
            "source_completeness_sha256"
        ],
        "target_completeness_sha256": coordinate_core[
            "target_completeness_sha256"
        ],
        "full_coordinate_ids": list(_COORDINATES),
        "source_block_count": 4,
        "target_block_count": 4,
        "coordinate_rows": coordinate_rows,
        "coordinate_core_sha256": _sha256(coordinate_core),
        "verification_disposition": "E2_SOURCE_TARGET_COORDINATES_IDENTIFIED",
    }


@dataclass(frozen=True, init=False)
class SourceTargetCoordinateIdentification:
    _envelope: FiberEnvelope = field(repr=False)
    _layer: DeclaredSyntheticTransferLayer = field(repr=False)
    _source_generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _target_generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _source_weights: PositiveFiberWeights = field(repr=False)
    _target_weights: PositiveFiberWeights = field(repr=False)
    _source_law: ExactFiniteFiberLaw = field(repr=False)
    _source_completeness: FiberCompletenessWitness = field(repr=False)
    _target_completeness: FiberCompletenessWitness = field(repr=False)
    _expected_authority_bytes: tuple[bytes, ...] = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 coordinate identification has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not SourceTargetCoordinateIdentification:
            raise StrictContractError("E2 coordinate identification subclasses are forbidden")
        if self._construction_seal is not _IDENTIFICATION_SEAL:
            raise StrictContractError("E2 coordinate identification seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        envelope: FiberEnvelope,
        layer: DeclaredSyntheticTransferLayer,
        source_generator: ExactQuotientCoordinateGenerator,
        target_generator: ExactQuotientCoordinateGenerator,
        source_weights: PositiveFiberWeights,
        target_weights: PositiveFiberWeights,
        source_law: ExactFiniteFiberLaw,
        source_completeness: FiberCompletenessWitness,
        target_completeness: FiberCompletenessWitness,
    ) -> "SourceTargetCoordinateIdentification":
        if cls is not SourceTargetCoordinateIdentification:
            raise StrictContractError("polymorphic E2 identification parsing is forbidden")
        supplied = _preflight_identification_wire(value)
        expected = _derive_identification_wire(
            envelope=envelope,
            layer=layer,
            source_generator=source_generator,
            target_generator=target_generator,
            source_weights=source_weights,
            target_weights=target_weights,
            source_law=source_law,
            source_completeness=source_completeness,
            target_completeness=target_completeness,
        )
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 identification wire disagrees with fresh authority")
        return _construct_identification(
            envelope,
            layer,
            source_generator,
            target_generator,
            source_weights,
            target_weights,
            source_law,
            source_completeness,
            target_completeness,
        )

    @property
    def coordinate_identification_sha256(self) -> str:
        return _sha256(self.to_dict())

    @property
    def source_target_coordinate_identification_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_identification_wire(
            envelope=self._envelope,
            layer=self._layer,
            source_generator=self._source_generator,
            target_generator=self._target_generator,
            source_weights=self._source_weights,
            target_weights=self._target_weights,
            source_law=self._source_law,
            source_completeness=self._source_completeness,
            target_completeness=self._target_completeness,
            expected_authority_bytes=self._expected_authority_bytes,
        )


def _construct_identification(
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
) -> SourceTargetCoordinateIdentification:
    result = object.__new__(SourceTargetCoordinateIdentification)
    for name, value in (
        ("_envelope", envelope),
        ("_layer", layer),
        ("_source_generator", source_generator),
        ("_target_generator", target_generator),
        ("_source_weights", source_weights),
        ("_target_weights", target_weights),
        ("_source_law", source_law),
        ("_source_completeness", source_completeness),
        ("_target_completeness", target_completeness),
    ):
        object.__setattr__(result, name, value)
    object.__setattr__(
        result,
        "_expected_authority_bytes",
        tuple(
            canonical_contract_bytes(authority.to_dict())
            for authority in (
                source_generator,
                target_generator,
                layer,
                source_weights,
                target_weights,
                source_law,
                source_completeness,
                target_completeness,
                envelope,
            )
        ),
    )
    object.__setattr__(result, "_construction_seal", _IDENTIFICATION_SEAL)
    result.__post_init__()
    return result


def identify_e2_source_target_coordinates(
    *,
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
) -> SourceTargetCoordinateIdentification:
    _derive_identification_wire(
        envelope=envelope,
        layer=layer,
        source_generator=source_generator,
        target_generator=target_generator,
        source_weights=source_weights,
        target_weights=target_weights,
        source_law=source_law,
        source_completeness=source_completeness,
        target_completeness=target_completeness,
    )
    return _construct_identification(
        envelope,
        layer,
        source_generator,
        target_generator,
        source_weights,
        target_weights,
        source_law,
        source_completeness,
        target_completeness,
    )


_RESTRICTION_FIELDS = (
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "basis_convention",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "coordinate_core_sha256",
    "full_coordinate_ids",
    "retained_coordinate_ids",
    "complement_coordinate_ids",
    "full_matrix",
    "restricted_matrix",
    "restricted_matrix_sha256",
    "restricted_source_weights",
    "restricted_source_weights_sha256",
    "restricted_target_weights",
    "restricted_target_weights_sha256",
    "omitted_cells",
    "omitted_cells_sha256",
    "omitted_cell_count",
    "replayed_cell_count",
    "restriction_core_sha256",
    "replay_pass",
    "verification_disposition",
)
_OMITTED_CELL_FIELDS = (
    "target_coordinate_id",
    "source_coordinate_id",
    "value",
)


def _preflight_restriction_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _RESTRICTION_FIELDS, "E2 restriction")
    _matrix_preflight(wire["full_matrix"], 4, 4, "E2 full matrix")
    _matrix_preflight(wire["restricted_matrix"], 2, 2, "E2 restricted matrix")
    _exact_array(wire["full_coordinate_ids"], 4, "E2 full coordinate IDs")
    _exact_array(wire["retained_coordinate_ids"], 2, "E2 retained coordinates")
    _exact_array(wire["complement_coordinate_ids"], 2, "E2 complement coordinates")
    source_weights = _exact_array(
        wire["restricted_source_weights"], 2, "E2 restricted source weights"
    )
    target_weights = _exact_array(
        wire["restricted_target_weights"], 2, "E2 restricted target weights"
    )
    omitted = _exact_array(wire["omitted_cells"], 12, "E2 omitted cells")
    _bounded_structural_preflight(wire)
    _matrix_from_wire(wire["full_matrix"])
    _matrix_from_wire(wire["restricted_matrix"])
    _fixed(wire["schema_version"], _RESTRICTION_SCHEMA, "E2 restriction schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 restriction endpoint")
    _fixed(wire["basis_convention"], _BASIS_CONVENTION, "E2 restriction basis")
    _fixed(wire["full_coordinate_ids"], list(_COORDINATES), "E2 full coordinates")
    _fixed(wire["retained_coordinate_ids"], list(_RETAINED), "E2 retained coordinates")
    _fixed(wire["complement_coordinate_ids"], list(_COMPLEMENT), "E2 complement coordinates")
    parent_id = _exact_string(wire["parent_id"], "E2 restriction parent")
    law_variant = _exact_string(
        wire["source_law_variant"], "E2 restriction law variant"
    )
    if parent_id not in _PARENT_MATRICES:
        raise StrictContractError("E2 restriction parent is invalid")
    if law_variant not in {"PRIMARY", "ALTERNATE_M0_DIAGNOSTIC"}:
        raise StrictContractError("E2 restriction law variant is invalid")
    for name in (
        "parent_envelope_sha256",
        "coordinate_identification_sha256",
        "coordinate_core_sha256",
        "restricted_matrix_sha256",
        "restricted_source_weights_sha256",
        "restricted_target_weights_sha256",
        "omitted_cells_sha256",
        "restriction_core_sha256",
    ):
        _digest(wire[name], f"E2 restriction {name}")
    for index, raw in enumerate(source_weights):
        _rational(raw, f"E2 restricted source weight {index}")
    for index, raw in enumerate(target_weights):
        _rational(raw, f"E2 restricted target weight {index}")
    for index, raw_row in enumerate(omitted):
        row = _exact_fields(raw_row, _OMITTED_CELL_FIELDS, f"E2 omitted cell {index}")
        _exact_string(row["target_coordinate_id"], "E2 omitted target coordinate")
        _exact_string(row["source_coordinate_id"], "E2 omitted source coordinate")
        _rational(row["value"], "E2 omitted cell value")
    _fixed(wire["omitted_cell_count"], 12, "E2 omitted-cell count")
    _fixed(wire["replayed_cell_count"], 16, "E2 replayed-cell count")
    _bool(wire["replay_pass"], "E2 restriction replay bit")
    _fixed(
        wire["verification_disposition"],
        "E2_ENVELOPE_RESTRICTION_REPLAYED",
        "E2 restriction disposition",
    )
    return wire


def _revalidate_identification(
    identification: SourceTargetCoordinateIdentification,
) -> dict[str, Any]:
    if type(identification) is not SourceTargetCoordinateIdentification:
        raise StrictContractError("E2 restriction requires an exact identification")
    identification.__post_init__()
    wire = identification.to_dict()
    _preflight_identification_wire(wire)
    return wire


def _derive_restriction_wire(
    *,
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> dict[str, Any]:
    if type(envelope) is not FiberEnvelope:
        raise StrictContractError("E2 restriction requires an exact FiberEnvelope")
    identification_wire = _revalidate_identification(identification)
    envelope_wire = envelope.to_dict()
    FiberEnvelope.from_dict(
        envelope_wire,
        identification._layer,
        identification._source_weights,
        identification._target_weights,
        identification._source_law,
        identification._source_completeness,
        identification._target_completeness,
    )
    if (
        _sha256(envelope_wire) != identification_wire["parent_envelope_sha256"]
        or not _same_wire(envelope_wire, identification._envelope.to_dict())
    ):
        raise StrictContractError("E2 restriction envelope is not its identification parent")

    _require_work(
        "restriction",
        source_members=sum(
            len(row["source_member_ids"])
            for row in identification_wire["coordinate_rows"]
        ),
        target_members=sum(
            len(row["target_member_ids"])
            for row in identification_wire["coordinate_rows"]
        ),
        coordinates=len(identification_wire["full_coordinate_ids"]),
        candidate_loads=envelope_wire["candidate_load_count"],
    )

    coordinate_rows = identification_wire["coordinate_rows"]
    expected_block_pairs = tuple(
        (
            target_row["target_block_index"],
            source_row["source_block_index"],
        )
        for target_row in coordinate_rows
        for source_row in coordinate_rows
    )
    majorants = _majorants_from_validated_envelope_wire(
        envelope_wire,
        expected_block_pairs,
        "E2 restriction envelope",
    )
    full_matrix = tuple(
        tuple(
            majorants[
                (
                    coordinate_rows[target_index]["target_block_index"],
                    coordinate_rows[source_index]["source_block_index"],
                )
            ]
            for source_index in range(4)
        )
        for target_index in range(4)
    )
    if full_matrix != _PARENT_MATRICES[identification_wire["parent_id"]]:
        raise StrictContractError("E2 restriction parent matrix changed")
    restricted = tuple(tuple(row[:2]) for row in full_matrix[:2])
    source_weights = tuple(
        ExactRational.from_dict(row["source_weight"])
        for row in coordinate_rows[:2]
    )
    target_weights = tuple(
        ExactRational.from_dict(row["target_weight"])
        for row in coordinate_rows[:2]
    )
    for index, value in enumerate((*source_weights, *target_weights)):
        _positive(value, f"E2 restricted weight {index}")

    omitted_cells = []
    for target_index, target_coordinate in enumerate(_COORDINATES):
        for source_index, source_coordinate in enumerate(_COORDINATES):
            if target_index < 2 and source_index < 2:
                continue
            value = full_matrix[target_index][source_index]
            if value != ExactRational(0):
                raise StrictContractError("E2 terminal/complement cell is not exact zero")
            omitted_cells.append(
                {
                    "target_coordinate_id": target_coordinate,
                    "source_coordinate_id": source_coordinate,
                    "value": value.to_dict(),
                }
            )
    if len(omitted_cells) != 12:
        raise StrictContractError("E2 omitted-cell coverage is incomplete")

    restricted_matrix_property = {
        "schema_version": "odlrq.e2.matrix-property.v1",
        "endpoint_id": _ENDPOINT_ID,
        "basis_convention": _BASIS_CONVENTION,
        "target_coordinate_ids": list(_RETAINED),
        "source_coordinate_ids": list(_RETAINED),
        "rows": _matrix_wire(restricted),
    }
    source_weight_property = _weight_property("SOURCE", _RETAINED, source_weights)
    target_weight_property = _weight_property("TARGET", _RETAINED, target_weights)
    omitted_property = {
        "schema_version": "odlrq.e2.omitted-cells-property.v1",
        "endpoint_id": _ENDPOINT_ID,
        "basis_convention": _BASIS_CONVENTION,
        "full_coordinate_ids": list(_COORDINATES),
        "rows": omitted_cells,
    }
    restricted_matrix_sha256 = _sha256(restricted_matrix_property)
    source_weights_sha256 = _sha256(source_weight_property)
    target_weights_sha256 = _sha256(target_weight_property)
    omitted_sha256 = _sha256(omitted_property)
    restriction_core = {
        "schema_version": "odlrq.e2.restriction-core.v1",
        "endpoint_id": _ENDPOINT_ID,
        "parent_id": identification_wire["parent_id"],
        "basis_convention": _BASIS_CONVENTION,
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
        "full_coordinate_ids": list(_COORDINATES),
        "retained_coordinate_ids": list(_RETAINED),
        "complement_coordinate_ids": list(_COMPLEMENT),
        "full_matrix": _matrix_wire(full_matrix),
        "restricted_matrix": _matrix_wire(restricted),
        "restricted_matrix_sha256": restricted_matrix_sha256,
        "restricted_source_weights": [value.to_dict() for value in source_weights],
        "restricted_source_weights_sha256": source_weights_sha256,
        "restricted_target_weights": [value.to_dict() for value in target_weights],
        "restricted_target_weights_sha256": target_weights_sha256,
        "omitted_cells": omitted_cells,
        "omitted_cells_sha256": omitted_sha256,
        "omitted_cell_count": 12,
        "replayed_cell_count": 16,
    }
    return {
        "schema_version": _RESTRICTION_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "parent_id": identification_wire["parent_id"],
        "source_law_variant": identification_wire["source_law_variant"],
        "basis_convention": _BASIS_CONVENTION,
        "parent_envelope_sha256": _sha256(envelope_wire),
        "coordinate_identification_sha256": _sha256(identification_wire),
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
        "full_coordinate_ids": list(_COORDINATES),
        "retained_coordinate_ids": list(_RETAINED),
        "complement_coordinate_ids": list(_COMPLEMENT),
        "full_matrix": _matrix_wire(full_matrix),
        "restricted_matrix": _matrix_wire(restricted),
        "restricted_matrix_sha256": restricted_matrix_sha256,
        "restricted_source_weights": [value.to_dict() for value in source_weights],
        "restricted_source_weights_sha256": source_weights_sha256,
        "restricted_target_weights": [value.to_dict() for value in target_weights],
        "restricted_target_weights_sha256": target_weights_sha256,
        "omitted_cells": omitted_cells,
        "omitted_cells_sha256": omitted_sha256,
        "omitted_cell_count": 12,
        "replayed_cell_count": 16,
        "restriction_core_sha256": _sha256(restriction_core),
        "replay_pass": True,
        "verification_disposition": "E2_ENVELOPE_RESTRICTION_REPLAYED",
    }


@dataclass(frozen=True, init=False)
class EnvelopeRestrictionWitness:
    _envelope: FiberEnvelope = field(repr=False)
    _identification: SourceTargetCoordinateIdentification = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 envelope restriction has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not EnvelopeRestrictionWitness:
            raise StrictContractError("E2 restriction subclasses are forbidden")
        if self._construction_seal is not _RESTRICTION_SEAL:
            raise StrictContractError("E2 restriction construction seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        envelope: FiberEnvelope,
        identification: SourceTargetCoordinateIdentification,
    ) -> "EnvelopeRestrictionWitness":
        if cls is not EnvelopeRestrictionWitness:
            raise StrictContractError("polymorphic E2 restriction parsing is forbidden")
        supplied = _preflight_restriction_wire(value)
        expected = _derive_restriction_wire(
            envelope=envelope, identification=identification
        )
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 restriction wire disagrees with fresh authority")
        return _construct_restriction(envelope, identification)

    @property
    def envelope_restriction_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_restriction_wire(
            envelope=self._envelope, identification=self._identification
        )


def _construct_restriction(
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> EnvelopeRestrictionWitness:
    result = object.__new__(EnvelopeRestrictionWitness)
    object.__setattr__(result, "_envelope", envelope)
    object.__setattr__(result, "_identification", identification)
    object.__setattr__(result, "_construction_seal", _RESTRICTION_SEAL)
    result.__post_init__()
    return result


def build_e2_envelope_restriction(
    *,
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> EnvelopeRestrictionWitness:
    _derive_restriction_wire(envelope=envelope, identification=identification)
    return _construct_restriction(envelope, identification)


_SAFETY_FIELDS = (
    "schema_version",
    "endpoint_id",
    "parent_id",
    "source_law_variant",
    "scope",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "envelope_restriction_sha256",
    "source_law_sha256",
    "coordinate_core_sha256",
    "restriction_core_sha256",
    "ordered_candidate_loads",
    "majorant_matrix",
    "candidate_load_count",
    "matrix_cell_count",
    "theorem_core_sha256",
    "law_uniform",
    "cancellation_free",
    "verification_disposition",
)
_CANDIDATE_LOAD_FIELDS = (
    "target_coordinate_id",
    "source_coordinate_id",
    "source_member_id",
    "source_member_sha256",
    "load",
)
_SAFETY_SCOPE = (
    "all_exact_nonnegative_block_probability_laws_on_complete_declared_"
    "source_blocks_v1"
)


def _preflight_safety_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _SAFETY_FIELDS, "E2 lifting-uniform safety")
    loads = _exact_array(
        wire["ordered_candidate_loads"],
        _MAX_E2_CANDIDATE_LOAD_ROWS,
        "E2 candidate loads",
    )
    _matrix_preflight(wire["majorant_matrix"], 4, 4, "E2 safety majorant")
    _bounded_structural_preflight(wire)
    _matrix_from_wire(wire["majorant_matrix"])
    _fixed(wire["schema_version"], _SAFETY_SCHEMA, "E2 safety schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 safety endpoint")
    _fixed(wire["scope"], _SAFETY_SCOPE, "E2 safety scope")
    parent_id = _exact_string(wire["parent_id"], "E2 safety parent")
    law_variant = _exact_string(
        wire["source_law_variant"], "E2 safety law variant"
    )
    if parent_id not in _PARENT_MATRICES:
        raise StrictContractError("E2 safety parent is invalid")
    if law_variant not in {"PRIMARY", "ALTERNATE_M0_DIAGNOSTIC"}:
        raise StrictContractError("E2 safety law variant is invalid")
    for name in (
        "parent_envelope_sha256",
        "coordinate_identification_sha256",
        "envelope_restriction_sha256",
        "source_law_sha256",
        "coordinate_core_sha256",
        "restriction_core_sha256",
        "theorem_core_sha256",
    ):
        _digest(wire[name], f"E2 safety {name}")
    for index, raw_row in enumerate(loads):
        row = _exact_fields(raw_row, _CANDIDATE_LOAD_FIELDS, f"E2 load row {index}")
        for name in (
            "target_coordinate_id",
            "source_coordinate_id",
            "source_member_id",
        ):
            _exact_string(row[name], f"E2 load row {name}")
        _digest(row["source_member_sha256"], "E2 load member SHA")
        _rational(row["load"], "E2 candidate load")
    _fixed(wire["candidate_load_count"], 20, "E2 candidate-load count")
    _fixed(wire["matrix_cell_count"], 16, "E2 matrix-cell count")
    _bool(wire["law_uniform"], "E2 law-uniform bit")
    _bool(wire["cancellation_free"], "E2 cancellation-free bit")
    _fixed(
        wire["verification_disposition"],
        "E2_DECLARED_FINITE_LIFTING_UNIFORM_VERIFIED",
        "E2 safety disposition",
    )
    return wire


def _derive_safety_wire(
    *,
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
    restriction: EnvelopeRestrictionWitness,
) -> dict[str, Any]:
    if (
        type(envelope) is not FiberEnvelope
        or type(identification) is not SourceTargetCoordinateIdentification
        or type(restriction) is not EnvelopeRestrictionWitness
    ):
        raise StrictContractError("E2 safety requires exact typed authorities")
    identification_wire = identification.to_dict()
    restriction_wire = restriction.to_dict()
    envelope_wire = envelope.to_dict()
    if (
        _sha256(envelope_wire) != identification_wire["parent_envelope_sha256"]
        or _sha256(identification_wire)
        != restriction_wire["coordinate_identification_sha256"]
        or _sha256(envelope_wire) != restriction_wire["parent_envelope_sha256"]
        or not _same_wire(envelope_wire, restriction._envelope.to_dict())
        or not _same_wire(identification_wire, restriction._identification.to_dict())
    ):
        raise StrictContractError("E2 safety authority chain is inconsistent")

    # The identification has just re-entered and verified the complete E1
    # bundle.  Materialize each bound authority wire once for this independent
    # replay instead of invoking its full public serializer for every cell.
    layer_wire = identification._layer.to_dict()
    source_weights_wire = identification._source_weights.to_dict()
    target_weights_wire = identification._target_weights.to_dict()
    if (
        _sha256(layer_wire) != identification_wire["layer_sha256"]
        or _sha256(source_weights_wire)
        != identification_wire["source_weights_sha256"]
        or _sha256(target_weights_wire)
        != identification_wire["target_weights_sha256"]
    ):
        raise StrictContractError("E2 safety E1 lookup authorities are misbound")

    coordinate_rows = identification_wire["coordinate_rows"]
    source_member_blocks: dict[str, int] = {}
    target_member_blocks: dict[str, int] = {}
    for coordinate_row in coordinate_rows:
        source_block = coordinate_row["source_block_index"]
        target_block = coordinate_row["target_block_index"]
        if type(source_block) is not int or type(target_block) is not int:
            raise StrictContractError("E2 safety coordinate block index changed type")
        for member in coordinate_row["source_member_ids"]:
            if type(member) is not str or not member or member in source_member_blocks:
                raise StrictContractError(
                    "E2 safety source-member coverage is not exact and unique"
                )
            source_member_blocks[member] = source_block
        for member in coordinate_row["target_member_ids"]:
            if type(member) is not str or not member or member in target_member_blocks:
                raise StrictContractError(
                    "E2 safety target-member coverage is not exact and unique"
                )
            target_member_blocks[member] = target_block
    if (
        len(source_member_blocks) != _MAX_E2_RAW_SOURCE_MEMBERS
        or len(target_member_blocks) != _MAX_E2_RAW_TARGET_MEMBERS
    ):
        raise StrictContractError("E2 safety member coverage changed")

    def _weight_lookup(
        wire: dict[str, Any], expected_blocks: dict[str, int], label: str
    ) -> tuple[dict[str, ExactRational], tuple[str, ...]]:
        rows = wire.get("rows")
        if type(rows) is not list or len(rows) != len(expected_blocks):
            raise StrictContractError(f"E2 safety {label} weight coverage changed")
        values: dict[str, ExactRational] = {}
        order: list[str] = []
        for row in rows:
            if type(row) is not dict or set(row) != {
                "block_index",
                "member_id",
                "member_sha256",
                "weight",
            }:
                raise StrictContractError(
                    f"E2 safety {label} weight row is not exact"
                )
            member = row["member_id"]
            if (
                type(member) is not str
                or member not in expected_blocks
                or member in values
                or row["block_index"] != expected_blocks[member]
            ):
                raise StrictContractError(
                    f"E2 safety {label} weight membership/order binding changed"
                )
            values[member] = _positive(
                ExactRational.from_dict(row["weight"]),
                f"E2 safety {label} member weight",
            )
            order.append(member)
        if set(values) != set(expected_blocks):
            raise StrictContractError(
                f"E2 safety {label} weight membership is incomplete"
            )
        return values, tuple(order)

    source_weight_by_member, source_member_order = _weight_lookup(
        source_weights_wire, source_member_blocks, "source"
    )
    target_weight_by_member, target_member_order = _weight_lookup(
        target_weights_wire, target_member_blocks, "target"
    )
    source_position = {
        member: index for index, member in enumerate(source_member_order)
    }
    target_position = {
        member: index for index, member in enumerate(target_member_order)
    }
    coefficient_rows = layer_wire.get("coefficients")
    if type(coefficient_rows) is not list:
        raise StrictContractError("E2 safety coefficient table is not an exact array")
    coefficient_by_pair: dict[tuple[str, str], ExactRational] = {}
    coefficient_order: list[tuple[int, int]] = []
    for row in coefficient_rows:
        if type(row) is not dict or set(row) != {
            "target_member_id",
            "target_member_sha256",
            "source_member_id",
            "source_member_sha256",
            "coefficient",
        }:
            raise StrictContractError("E2 safety coefficient row is not exact")
        target_member = row["target_member_id"]
        source_member = row["source_member_id"]
        pair = (target_member, source_member)
        if (
            type(target_member) is not str
            or type(source_member) is not str
            or target_member not in target_position
            or source_member not in source_position
            or pair in coefficient_by_pair
        ):
            raise StrictContractError(
                "E2 safety coefficient table is duplicated or outside the rectangle"
            )
        coefficient = ExactRational.from_dict(row["coefficient"])
        if coefficient.numerator == 0:
            raise StrictContractError("E2 safety coefficient table contains explicit zero")
        coefficient_by_pair[pair] = coefficient
        coefficient_order.append(
            (target_position[target_member], source_position[source_member])
        )
    if coefficient_order != sorted(coefficient_order):
        raise StrictContractError("E2 safety coefficient order is not canonical")

    _require_work(
        "safety",
        source_members=sum(
            len(row["source_member_ids"])
            for row in identification_wire["coordinate_rows"]
        ),
        target_members=sum(
            len(row["target_member_ids"])
            for row in identification_wire["coordinate_rows"]
        ),
        coordinates=len(identification_wire["full_coordinate_ids"]),
        candidate_loads=envelope_wire["candidate_load_count"],
    )
    envelope_cells = {
        (cell["target_block_index"], cell["source_block_index"]): cell
        for cell in envelope_wire["cells"]
    }
    if len(envelope_cells) != 16:
        raise StrictContractError("E2 safety parent cell table is incomplete")

    ordered_candidate_loads = []
    for target_row in coordinate_rows:
        target_coordinate = target_row["coordinate_id"]
        target_members = tuple(target_row["target_member_ids"])
        for source_row in coordinate_rows:
            source_coordinate = source_row["coordinate_id"]
            source_members = tuple(source_row["source_member_ids"])
            cell = envelope_cells.get(
                (target_row["target_block_index"], source_row["source_block_index"])
            )
            if cell is None:
                raise StrictContractError("E2 safety parent cell is missing")
            candidate_rows = cell["candidate_loads"]
            if [row["source_member_id"] for row in candidate_rows] != list(source_members):
                raise StrictContractError("E2 safety candidate member order changed")
            recomputed: list[ExactRational] = []
            for candidate, source_member in zip(
                candidate_rows, source_members, strict=True
            ):
                source_weight = source_weight_by_member[source_member]
                load = ExactRational(0)
                for target_member in target_members:
                    coefficient = coefficient_by_pair.get(
                        (target_member, source_member), ExactRational(0)
                    )
                    target_weight = target_weight_by_member[target_member]
                    load = _add(
                        load,
                        _divide(
                            _multiply(_absolute(coefficient), target_weight),
                            source_weight,
                        ),
                    )
                declared = ExactRational.from_dict(candidate["load"])
                if declared != load:
                    raise StrictContractError("E2 candidate load failed independent replay")
                recomputed.append(load)
                ordered_candidate_loads.append(
                    {
                        "target_coordinate_id": target_coordinate,
                        "source_coordinate_id": source_coordinate,
                        "source_member_id": source_member,
                        "source_member_sha256": candidate["source_member_sha256"],
                        "load": load.to_dict(),
                    }
                )
            majorant = ExactRational.from_dict(cell["majorant"])
            maximum = recomputed[0]
            for candidate in recomputed[1:]:
                if _less(maximum, candidate):
                    maximum = candidate
            if maximum != majorant:
                raise StrictContractError("E2 majorant is not the complete candidate maximum")
    if len(ordered_candidate_loads) != _MAX_E2_CANDIDATE_LOAD_ROWS:
        raise StrictContractError("E2 candidate-load proof is incomplete")

    theorem_core = {
        "schema_version": "odlrq.e2.lifting_uniform_theorem_core.v1",
        "endpoint_id": _ENDPOINT_ID,
        "parent_id": identification_wire["parent_id"],
        "basis_convention": _BASIS_CONVENTION,
        "layer_sha256": identification_wire["layer_sha256"],
        "source_generator_sha256": identification_wire["source_generator_sha256"],
        "target_generator_sha256": identification_wire["target_generator_sha256"],
        "source_weights_sha256": identification_wire["source_weights_sha256"],
        "target_weights_sha256": identification_wire["target_weights_sha256"],
        "source_completeness_sha256": identification_wire[
            "source_completeness_sha256"
        ],
        "target_completeness_sha256": identification_wire[
            "target_completeness_sha256"
        ],
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
        "restriction_core_sha256": restriction_wire["restriction_core_sha256"],
        "ordered_candidate_loads": ordered_candidate_loads,
        "majorant_matrix": restriction_wire["full_matrix"],
        "scope": _SAFETY_SCOPE,
    }
    return {
        "schema_version": _SAFETY_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "parent_id": identification_wire["parent_id"],
        "source_law_variant": identification_wire["source_law_variant"],
        "scope": _SAFETY_SCOPE,
        "parent_envelope_sha256": _sha256(envelope_wire),
        "coordinate_identification_sha256": _sha256(identification_wire),
        "envelope_restriction_sha256": _sha256(restriction_wire),
        "source_law_sha256": identification_wire["source_law_sha256"],
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
        "restriction_core_sha256": restriction_wire["restriction_core_sha256"],
        "ordered_candidate_loads": ordered_candidate_loads,
        "majorant_matrix": restriction_wire["full_matrix"],
        "candidate_load_count": 20,
        "matrix_cell_count": 16,
        "theorem_core_sha256": _sha256(theorem_core),
        "law_uniform": True,
        "cancellation_free": True,
        "verification_disposition": "E2_DECLARED_FINITE_LIFTING_UNIFORM_VERIFIED",
    }


@dataclass(frozen=True, init=False)
class LiftingUniformSafetyCertificate:
    _envelope: FiberEnvelope = field(repr=False)
    _identification: SourceTargetCoordinateIdentification = field(repr=False)
    _restriction: EnvelopeRestrictionWitness = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 lifting-uniform safety has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not LiftingUniformSafetyCertificate:
            raise StrictContractError("E2 safety subclasses are forbidden")
        if self._construction_seal is not _SAFETY_SEAL:
            raise StrictContractError("E2 safety construction seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        envelope: FiberEnvelope,
        identification: SourceTargetCoordinateIdentification,
        restriction: EnvelopeRestrictionWitness,
    ) -> "LiftingUniformSafetyCertificate":
        if cls is not LiftingUniformSafetyCertificate:
            raise StrictContractError("polymorphic E2 safety parsing is forbidden")
        supplied = _preflight_safety_wire(value)
        expected = _derive_safety_wire(
            envelope=envelope,
            identification=identification,
            restriction=restriction,
        )
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 safety wire disagrees with fresh authority")
        return _construct_safety(envelope, identification, restriction)

    @property
    def lifting_uniform_safety_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_safety_wire(
            envelope=self._envelope,
            identification=self._identification,
            restriction=self._restriction,
        )


def _construct_safety(
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
    restriction: EnvelopeRestrictionWitness,
) -> LiftingUniformSafetyCertificate:
    result = object.__new__(LiftingUniformSafetyCertificate)
    object.__setattr__(result, "_envelope", envelope)
    object.__setattr__(result, "_identification", identification)
    object.__setattr__(result, "_restriction", restriction)
    object.__setattr__(result, "_construction_seal", _SAFETY_SEAL)
    result.__post_init__()
    return result


def certify_e2_lifting_uniform_safety(
    *,
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
    restriction: EnvelopeRestrictionWitness,
) -> LiftingUniformSafetyCertificate:
    _derive_safety_wire(
        envelope=envelope,
        identification=identification,
        restriction=restriction,
    )
    return _construct_safety(envelope, identification, restriction)


_SPLIT_FIELDS = (
    "schema_version",
    "endpoint_id",
    "envelope_restriction_sha256",
    "basis_convention",
    "retained_coordinate_ids",
    "p_coordinate_ids",
    "q_coordinate_ids",
    "m_pp",
    "m_pq",
    "m_qp",
    "m_qq",
    "split_exhaustive",
    "split_core_sha256",
    "verification_disposition",
)


def _preflight_split_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _SPLIT_FIELDS, "E2 memory split")
    _exact_array(wire["retained_coordinate_ids"], 2, "E2 split retained IDs")
    _exact_array(wire["p_coordinate_ids"], 1, "E2 P IDs")
    _exact_array(wire["q_coordinate_ids"], 1, "E2 Q IDs")
    for name in ("m_pp", "m_pq", "m_qp", "m_qq"):
        _matrix_preflight(wire[name], 1, 1, f"E2 split {name}")
    _bounded_structural_preflight(wire)
    for name in ("m_pp", "m_pq", "m_qp", "m_qq"):
        _matrix_from_wire(wire[name])
    _fixed(wire["schema_version"], _SPLIT_SCHEMA, "E2 split schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 split endpoint")
    _fixed(wire["basis_convention"], _BASIS_CONVENTION, "E2 split basis")
    _fixed(wire["retained_coordinate_ids"], list(_RETAINED), "E2 split retained IDs")
    _fixed(wire["p_coordinate_ids"], list(_P_COORDINATES), "E2 P IDs")
    _fixed(wire["q_coordinate_ids"], list(_Q_COORDINATES), "E2 Q IDs")
    _digest(wire["envelope_restriction_sha256"], "E2 split restriction SHA")
    _digest(wire["split_core_sha256"], "E2 split core SHA")
    _bool(wire["split_exhaustive"], "E2 split exhaustive bit")
    _fixed(
        wire["verification_disposition"],
        "E2_MEMORY_SPLIT_RESOLVED",
        "E2 split disposition",
    )
    return wire


def _derive_split_wire(*, restriction: EnvelopeRestrictionWitness) -> dict[str, Any]:
    if type(restriction) is not EnvelopeRestrictionWitness:
        raise StrictContractError("E2 split requires an exact restriction")
    restriction_wire = restriction.to_dict()
    if (
        restriction_wire["parent_id"] != "MRET"
        or restriction_wire["source_law_variant"] != "PRIMARY"
        or restriction_wire["retained_coordinate_ids"] != list(_RETAINED)
    ):
        raise StrictContractError("E2 split requires PRIMARY MRET on the fixed retained basis")
    _require_work(
        "split",
        coordinates=len(restriction_wire["full_coordinate_ids"]),
    )
    matrix = _matrix_from_wire(restriction_wire["restricted_matrix"])
    m_pp = ((matrix[0][0],),)
    m_pq = ((matrix[0][1],),)
    m_qp = ((matrix[1][0],),)
    m_qq = ((matrix[1][1],),)
    core = {
        "schema_version": "odlrq.e2.memory-split-core.v1",
        "endpoint_id": _ENDPOINT_ID,
        "envelope_restriction_sha256": _sha256(restriction_wire),
        "basis_convention": _BASIS_CONVENTION,
        "retained_coordinate_ids": list(_RETAINED),
        "p_coordinate_ids": list(_P_COORDINATES),
        "q_coordinate_ids": list(_Q_COORDINATES),
        "m_pp": _matrix_wire(m_pp),
        "m_pq": _matrix_wire(m_pq),
        "m_qp": _matrix_wire(m_qp),
        "m_qq": _matrix_wire(m_qq),
    }
    return {
        **core,
        "schema_version": _SPLIT_SCHEMA,
        "split_exhaustive": True,
        "split_core_sha256": _sha256(core),
        "verification_disposition": "E2_MEMORY_SPLIT_RESOLVED",
    }


@dataclass(frozen=True, init=False)
class ResolvedMemorySplit:
    _restriction: EnvelopeRestrictionWitness = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 memory split has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not ResolvedMemorySplit:
            raise StrictContractError("E2 memory-split subclasses are forbidden")
        if self._construction_seal is not _SPLIT_SEAL:
            raise StrictContractError("E2 memory-split construction seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        restriction: EnvelopeRestrictionWitness,
    ) -> "ResolvedMemorySplit":
        if cls is not ResolvedMemorySplit:
            raise StrictContractError("polymorphic E2 split parsing is forbidden")
        supplied = _preflight_split_wire(value)
        expected = _derive_split_wire(restriction=restriction)
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 memory-split wire disagrees with authority")
        return _construct_split(restriction)

    @property
    def resolved_memory_split_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_split_wire(restriction=self._restriction)


def _construct_split(restriction: EnvelopeRestrictionWitness) -> ResolvedMemorySplit:
    result = object.__new__(ResolvedMemorySplit)
    object.__setattr__(result, "_restriction", restriction)
    object.__setattr__(result, "_construction_seal", _SPLIT_SEAL)
    result.__post_init__()
    return result


def resolve_e2_memory_split(
    *, restriction: EnvelopeRestrictionWitness
) -> ResolvedMemorySplit:
    _derive_split_wire(restriction=restriction)
    return _construct_split(restriction)


_COCYCLE_FIELDS = (
    "schema_version",
    "endpoint_id",
    "channel",
    "channel_derivation",
    "composition_scope",
    "product_order",
    "factor_restriction_sha256s",
    "ordered_source_basis",
    "ordered_intermediate_basis",
    "ordered_target_basis",
    "source_weights",
    "intermediate_weights",
    "target_weights",
    "source_weights_sha256",
    "intermediate_weights_sha256",
    "target_weights_sha256",
    "layer_matrices",
    "theta_values",
    "componentwise_lhs_rows",
    "product_matrix",
    "product_weighted_norm",
    "theta_product",
    "finite_horizon",
    "inequality_pass",
    "verification_disposition",
)
_CHANNEL_DERIVATIONS = {
    "P1_BRANCHING_ADJUSTED": "identity_positive_majorant_v1",
    "P2_BRANCHING_ADJUSTED": "entrywise_square_no_cross_terms_synthetic_v1",
}
_COMPOSITION_SCOPE = "declared_abstract_coordinate_composition_v1"
_PRODUCT_ORDER = "rightmost_earliest_M_hminus1_dotdot_M0_v1"


def _preflight_cocycle_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _COCYCLE_FIELDS, "E2 cocycle")
    factors = _exact_array(
        wire["factor_restriction_sha256s"], 2, "E2 cocycle factors"
    )
    for name in (
        "ordered_source_basis",
        "ordered_intermediate_basis",
        "ordered_target_basis",
        "source_weights",
        "intermediate_weights",
        "target_weights",
        "theta_values",
        "componentwise_lhs_rows",
        "layer_matrices",
    ):
        _exact_array(wire[name], 2, f"E2 cocycle {name}")
    for index, matrix in enumerate(wire["layer_matrices"]):
        _matrix_preflight(matrix, 2, 2, f"E2 cocycle layer {index}")
    _matrix_preflight(wire["product_matrix"], 2, 2, "E2 cocycle product")
    _bounded_structural_preflight(wire)
    for matrix in wire["layer_matrices"]:
        _matrix_from_wire(matrix)
    _matrix_from_wire(wire["product_matrix"])
    _fixed(wire["schema_version"], _COCYCLE_SCHEMA, "E2 cocycle schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 cocycle endpoint")
    channel = _exact_string(wire["channel"], "E2 cocycle channel")
    if channel not in _CHANNEL_DERIVATIONS:
        raise StrictContractError("E2 cocycle channel is invalid")
    _fixed(
        wire["channel_derivation"],
        _CHANNEL_DERIVATIONS[channel],
        "E2 cocycle derivation",
    )
    _fixed(wire["composition_scope"], _COMPOSITION_SCOPE, "E2 composition scope")
    _fixed(wire["product_order"], _PRODUCT_ORDER, "E2 product order")
    for factor in factors:
        _digest(factor, "E2 cocycle factor SHA")
    for name in (
        "ordered_source_basis",
        "ordered_intermediate_basis",
        "ordered_target_basis",
    ):
        _fixed(wire[name], list(_RETAINED), f"E2 cocycle {name}")
    for name in ("source_weights", "intermediate_weights", "target_weights"):
        for index, raw in enumerate(wire[name]):
            _rational(raw, f"E2 cocycle {name} {index}")
    for name in (
        "source_weights_sha256",
        "intermediate_weights_sha256",
        "target_weights_sha256",
    ):
        _digest(wire[name], f"E2 cocycle {name}")
    for index, raw in enumerate(wire["theta_values"]):
        _rational(raw, f"E2 theta {index}")
    for row_index, row in enumerate(wire["componentwise_lhs_rows"]):
        exact = _exact_array(row, 2, f"E2 componentwise LHS {row_index}")
        for column_index, raw in enumerate(exact):
            _rational(raw, f"E2 LHS [{row_index},{column_index}]")
    _rational(wire["product_weighted_norm"], "E2 product weighted norm")
    _rational(wire["theta_product"], "E2 theta product")
    _fixed(wire["finite_horizon"], 2, "E2 cocycle horizon")
    _bool(wire["inequality_pass"], "E2 cocycle inequality bit")
    _fixed(
        wire["verification_disposition"],
        "E2_FINITE_ABSTRACT_COCYCLE_VERIFIED",
        "E2 cocycle disposition",
    )
    return wire


def _componentwise_lhs(
    matrix: tuple[tuple[ExactRational, ...], ...],
    target_weights: tuple[ExactRational, ...],
) -> tuple[ExactRational, ...]:
    if len(matrix) != len(target_weights):
        raise StrictContractError("E2 weighted action has the wrong target dimension")
    return tuple(
        _sum_exact(
            tuple(
                _multiply(target_weights[row], matrix[row][column])
                for row in range(len(matrix))
            )
        )
        for column in range(len(matrix[0]))
    )


def _sum_exact(values: tuple[ExactRational, ...]) -> ExactRational:
    if not values:
        return ExactRational(0)
    total = values[0]
    for value in values[1:]:
        total = _add(total, value)
    return total


def _theta_for(
    lhs: tuple[ExactRational, ...], source_weights: tuple[ExactRational, ...]
) -> ExactRational:
    if len(lhs) != len(source_weights) or not lhs:
        raise StrictContractError("E2 theta dimensions are invalid")
    ratios = tuple(
        _divide(value, _positive(weight, "E2 source weight"))
        for value, weight in zip(lhs, source_weights, strict=True)
    )
    result = ratios[0]
    for ratio in ratios[1:]:
        if _less(result, ratio):
            result = ratio
    return result


def _weighted_norm(
    matrix: tuple[tuple[ExactRational, ...], ...],
    source_weights: tuple[ExactRational, ...],
    target_weights: tuple[ExactRational, ...],
) -> ExactRational:
    lhs = _componentwise_lhs(matrix, target_weights)
    return _theta_for(lhs, source_weights)


def _entrywise_square(
    matrix: tuple[tuple[ExactRational, ...], ...]
) -> tuple[tuple[ExactRational, ...], ...]:
    return tuple(
        tuple(_multiply(value, value) for value in row) for row in matrix
    )


def _derive_cocycle_wire(
    *,
    channel: str,
    first: EnvelopeRestrictionWitness,
    second: EnvelopeRestrictionWitness,
) -> dict[str, Any]:
    if type(channel) is not str or channel not in _CHANNEL_DERIVATIONS:
        raise StrictContractError("E2 cocycle requires one exact declared channel")
    if type(first) is not EnvelopeRestrictionWitness or type(second) is not EnvelopeRestrictionWitness:
        raise StrictContractError("E2 cocycle requires exact restriction factors")
    first_wire = first.to_dict()
    second_wire = second.to_dict()
    if (
        first_wire["parent_id"] != "M0"
        or first_wire["source_law_variant"] != "PRIMARY"
        or second_wire["parent_id"] != "M1"
        or second_wire["source_law_variant"] != "PRIMARY"
    ):
        raise StrictContractError("E2 cocycle role/law table requires PRIMARY M0 then M1")
    for wire in (first_wire, second_wire):
        if wire["retained_coordinate_ids"] != list(_RETAINED):
            raise StrictContractError("E2 cocycle factor basis changed")
    _require_work(
        "cocycle", coordinates=len(first_wire["full_coordinate_ids"])
    )

    first_matrix = _matrix_from_wire(first_wire["restricted_matrix"])
    second_matrix = _matrix_from_wire(second_wire["restricted_matrix"])
    if channel == "P2_BRANCHING_ADJUSTED":
        first_matrix = _entrywise_square(first_matrix)
        second_matrix = _entrywise_square(second_matrix)
    source_weights = tuple(
        ExactRational.from_dict(value)
        for value in first_wire["restricted_source_weights"]
    )
    first_target_weights = tuple(
        ExactRational.from_dict(value)
        for value in first_wire["restricted_target_weights"]
    )
    second_source_weights = tuple(
        ExactRational.from_dict(value)
        for value in second_wire["restricted_source_weights"]
    )
    target_weights = tuple(
        ExactRational.from_dict(value)
        for value in second_wire["restricted_target_weights"]
    )
    for value in (
        *source_weights,
        *first_target_weights,
        *second_source_weights,
        *target_weights,
    ):
        _positive(value, "E2 cocycle weight")
    if first_target_weights != second_source_weights:
        raise StrictContractError("E2 cocycle intermediate exact weights disagree")
    intermediate_weights = first_target_weights
    lhs_first = _componentwise_lhs(first_matrix, intermediate_weights)
    lhs_second = _componentwise_lhs(second_matrix, target_weights)
    theta_first = _theta_for(lhs_first, source_weights)
    theta_second = _theta_for(lhs_second, intermediate_weights)
    for lhs, theta, weights in (
        (lhs_first, theta_first, source_weights),
        (lhs_second, theta_second, intermediate_weights),
    ):
        if any(
            _less(_multiply(theta, weight), value)
            for value, weight in zip(lhs, weights, strict=True)
        ):
            raise StrictContractError("E2 cocycle componentwise bound failed")
    product = _matrix_multiply(second_matrix, first_matrix)
    product_norm = _weighted_norm(product, source_weights, target_weights)
    theta_product = _multiply(theta_first, theta_second)
    if _less(theta_product, product_norm):
        raise StrictContractError("E2 cocycle product bound failed")
    return {
        "schema_version": _COCYCLE_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "channel": channel,
        "channel_derivation": _CHANNEL_DERIVATIONS[channel],
        "composition_scope": _COMPOSITION_SCOPE,
        "product_order": _PRODUCT_ORDER,
        "factor_restriction_sha256s": [_sha256(first_wire), _sha256(second_wire)],
        "ordered_source_basis": list(_RETAINED),
        "ordered_intermediate_basis": list(_RETAINED),
        "ordered_target_basis": list(_RETAINED),
        "source_weights": [value.to_dict() for value in source_weights],
        "intermediate_weights": [value.to_dict() for value in intermediate_weights],
        "target_weights": [value.to_dict() for value in target_weights],
        "source_weights_sha256": _sha256(
            _weight_property("SOURCE", _RETAINED, source_weights)
        ),
        "intermediate_weights_sha256": _sha256(
            _weight_property("INTERMEDIATE", _RETAINED, intermediate_weights)
        ),
        "target_weights_sha256": _sha256(
            _weight_property("TARGET", _RETAINED, target_weights)
        ),
        "layer_matrices": [_matrix_wire(first_matrix), _matrix_wire(second_matrix)],
        "theta_values": [theta_first.to_dict(), theta_second.to_dict()],
        "componentwise_lhs_rows": [
            [value.to_dict() for value in lhs_first],
            [value.to_dict() for value in lhs_second],
        ],
        "product_matrix": _matrix_wire(product),
        "product_weighted_norm": product_norm.to_dict(),
        "theta_product": theta_product.to_dict(),
        "finite_horizon": 2,
        "inequality_pass": True,
        "verification_disposition": "E2_FINITE_ABSTRACT_COCYCLE_VERIFIED",
    }


@dataclass(frozen=True, init=False)
class CocycleCertificate:
    _channel: str = field(repr=False)
    _first: EnvelopeRestrictionWitness = field(repr=False)
    _second: EnvelopeRestrictionWitness = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 cocycle certificate has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not CocycleCertificate:
            raise StrictContractError("E2 cocycle subclasses are forbidden")
        if self._construction_seal is not _COCYCLE_SEAL:
            raise StrictContractError("E2 cocycle construction seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        channel: str,
        first: EnvelopeRestrictionWitness,
        second: EnvelopeRestrictionWitness,
    ) -> "CocycleCertificate":
        if cls is not CocycleCertificate:
            raise StrictContractError("polymorphic E2 cocycle parsing is forbidden")
        supplied = _preflight_cocycle_wire(value)
        expected = _derive_cocycle_wire(channel=channel, first=first, second=second)
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 cocycle wire disagrees with fresh authority")
        return _construct_cocycle(channel, first, second)

    @property
    def cocycle_certificate_sha256(self) -> str:
        return _sha256(self.to_dict())

    @property
    def cocycle_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_cocycle_wire(
            channel=self._channel, first=self._first, second=self._second
        )


def _construct_cocycle(
    channel: str,
    first: EnvelopeRestrictionWitness,
    second: EnvelopeRestrictionWitness,
) -> CocycleCertificate:
    result = object.__new__(CocycleCertificate)
    object.__setattr__(result, "_channel", channel)
    object.__setattr__(result, "_first", first)
    object.__setattr__(result, "_second", second)
    object.__setattr__(result, "_construction_seal", _COCYCLE_SEAL)
    result.__post_init__()
    return result


def certify_e2_cocycle(
    *,
    channel: str,
    first: EnvelopeRestrictionWitness,
    second: EnvelopeRestrictionWitness,
) -> CocycleCertificate:
    _derive_cocycle_wire(channel=channel, first=first, second=second)
    return _construct_cocycle(channel, first, second)


_RETURN_FIELDS = (
    "schema_version",
    "endpoint_id",
    "envelope_restriction_sha256",
    "resolved_memory_split_sha256",
    "iteration_scope",
    "finite_only",
    "horizon",
    "m_pp",
    "m_pq",
    "m_qp",
    "m_qq",
    "qq_powers",
    "return_terms",
    "return_sum",
    "p_source_weights",
    "p_source_weights_sha256",
    "p_target_weights",
    "p_target_weights_sha256",
    "weighted_norm",
    "operation_count",
    "direct_zero_memory_positive",
    "verification_disposition",
)
_POWER_TERM_FIELDS = ("k", "matrix")
_ITERATION_SCOPE = "stationary_reuse_of_restricted_abstract_majorant_v1"


def _preflight_return_wire(value: Any) -> dict[str, Any]:
    wire = _exact_fields(value, _RETURN_FIELDS, "E2 return-memory bound")
    for name in ("m_pp", "m_pq", "m_qp", "m_qq", "return_sum"):
        _matrix_preflight(wire[name], 1, 1, f"E2 return {name}")
    powers = _exact_array(wire["qq_powers"], 3, "E2 Q powers")
    terms = _exact_array(wire["return_terms"], 3, "E2 return terms")
    source_weights = _exact_array(wire["p_source_weights"], 1, "E2 P source weights")
    target_weights = _exact_array(wire["p_target_weights"], 1, "E2 P target weights")
    _bounded_structural_preflight(wire)
    for name in ("m_pp", "m_pq", "m_qp", "m_qq", "return_sum"):
        _matrix_from_wire(wire[name])
    _fixed(wire["schema_version"], _RETURN_SCHEMA, "E2 return schema")
    _fixed(wire["endpoint_id"], _ENDPOINT_ID, "E2 return endpoint")
    _fixed(wire["iteration_scope"], _ITERATION_SCOPE, "E2 return iteration scope")
    _bool(wire["finite_only"], "E2 finite-only bit")
    _fixed(wire["horizon"], 3, "E2 return horizon")
    for name in (
        "envelope_restriction_sha256",
        "resolved_memory_split_sha256",
        "p_source_weights_sha256",
        "p_target_weights_sha256",
    ):
        _digest(wire[name], f"E2 return {name}")
    for label, rows in (("power", powers), ("term", terms)):
        for index, raw_row in enumerate(rows):
            row = _exact_fields(raw_row, _POWER_TERM_FIELDS, f"E2 return {label} {index}")
            _fixed(row["k"], index, f"E2 return {label} exponent")
            _matrix_preflight(row["matrix"], 1, 1, f"E2 return {label} matrix")
            _matrix_from_wire(row["matrix"])
    _rational(source_weights[0], "E2 P source weight")
    _rational(target_weights[0], "E2 P target weight")
    _rational(wire["weighted_norm"], "E2 return weighted norm")
    _fixed(wire["operation_count"], 10, "E2 return operation count")
    _bool(wire["direct_zero_memory_positive"], "E2 ghost-memory bit")
    _fixed(
        wire["verification_disposition"],
        "E2_FINITE_RETURN_MEMORY_BOUNDED",
        "E2 return disposition",
    )
    return wire


def _derive_return_wire(
    *,
    restriction: EnvelopeRestrictionWitness,
    split: ResolvedMemorySplit,
) -> dict[str, Any]:
    if type(restriction) is not EnvelopeRestrictionWitness or type(split) is not ResolvedMemorySplit:
        raise StrictContractError("E2 return-memory requires exact typed authorities")
    restriction_wire = restriction.to_dict()
    split_wire = split.to_dict()
    if (
        restriction_wire["parent_id"] != "MRET"
        or restriction_wire["source_law_variant"] != "PRIMARY"
        or _sha256(restriction_wire) != split_wire["envelope_restriction_sha256"]
        or not _same_wire(restriction_wire, split._restriction.to_dict())
    ):
        raise StrictContractError("E2 return-memory authority chain is inconsistent")
    if restriction_wire["retained_coordinate_ids"] != list(_RETAINED):
        raise StrictContractError("E2 stationary reuse basis is incompatible")
    _require_work(
        "return",
        coordinates=len(restriction_wire["full_coordinate_ids"]),
        horizon=_MAX_E2_HORIZON,
        return_terms=_MAX_E2_RETURN_TERMS,
    )
    restricted_source_weights = tuple(
        ExactRational.from_dict(value)
        for value in restriction_wire["restricted_source_weights"]
    )
    restricted_target_weights = tuple(
        ExactRational.from_dict(value)
        for value in restriction_wire["restricted_target_weights"]
    )
    if restricted_source_weights != restricted_target_weights:
        raise StrictContractError("E2 stationary source/target exact weights disagree")
    m_pp = _matrix_from_wire(split_wire["m_pp"])
    m_pq = _matrix_from_wire(split_wire["m_pq"])
    m_qp = _matrix_from_wire(split_wire["m_qp"])
    m_qq = _matrix_from_wire(split_wire["m_qq"])
    identity = ((ExactRational(1),),)
    powers = [identity]
    for _ in range(1, _MAX_E2_HORIZON):
        powers.append(_matrix_multiply(m_qq, powers[-1]))
    terms = [
        _matrix_multiply(_matrix_multiply(m_pq, power), m_qp)
        for power in powers
    ]
    return_value = _sum_exact(tuple(term[0][0] for term in terms))
    return_sum = ((return_value,),)
    p_source_weights = (restricted_source_weights[0],)
    p_target_weights = (restricted_target_weights[0],)
    weighted_norm = _weighted_norm(return_sum, p_source_weights, p_target_weights)
    direct_zero_memory_positive = (
        m_pp == ((ExactRational(0),),) and _less(ExactRational(0), return_value)
    )
    if not direct_zero_memory_positive:
        raise StrictContractError("E2 return-memory ghost diagnostic failed")
    return {
        "schema_version": _RETURN_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "envelope_restriction_sha256": _sha256(restriction_wire),
        "resolved_memory_split_sha256": _sha256(split_wire),
        "iteration_scope": _ITERATION_SCOPE,
        "finite_only": True,
        "horizon": 3,
        "m_pp": _matrix_wire(m_pp),
        "m_pq": _matrix_wire(m_pq),
        "m_qp": _matrix_wire(m_qp),
        "m_qq": _matrix_wire(m_qq),
        "qq_powers": [
            {"k": index, "matrix": _matrix_wire(matrix)}
            for index, matrix in enumerate(powers)
        ],
        "return_terms": [
            {"k": index, "matrix": _matrix_wire(matrix)}
            for index, matrix in enumerate(terms)
        ],
        "return_sum": _matrix_wire(return_sum),
        "p_source_weights": [value.to_dict() for value in p_source_weights],
        "p_source_weights_sha256": _sha256(
            _weight_property("SOURCE", _P_COORDINATES, p_source_weights)
        ),
        "p_target_weights": [value.to_dict() for value in p_target_weights],
        "p_target_weights_sha256": _sha256(
            _weight_property("TARGET", _P_COORDINATES, p_target_weights)
        ),
        "weighted_norm": weighted_norm.to_dict(),
        "operation_count": 10,
        "direct_zero_memory_positive": True,
        "verification_disposition": "E2_FINITE_RETURN_MEMORY_BOUNDED",
    }


@dataclass(frozen=True, init=False)
class ReturnMemoryBound:
    _restriction: EnvelopeRestrictionWitness = field(repr=False)
    _split: ResolvedMemorySplit = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("E2 return-memory bound has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not ReturnMemoryBound:
            raise StrictContractError("E2 return-memory subclasses are forbidden")
        if self._construction_seal is not _RETURN_SEAL:
            raise StrictContractError("E2 return-memory construction seal changed")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        restriction: EnvelopeRestrictionWitness,
        split: ResolvedMemorySplit,
    ) -> "ReturnMemoryBound":
        if cls is not ReturnMemoryBound:
            raise StrictContractError("polymorphic E2 return-memory parsing is forbidden")
        supplied = _preflight_return_wire(value)
        expected = _derive_return_wire(restriction=restriction, split=split)
        if not _same_wire(supplied, expected):
            raise StrictContractError("E2 return-memory wire disagrees with authority")
        return _construct_return_memory(restriction, split)

    @property
    def return_memory_bound_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return _derive_return_wire(restriction=self._restriction, split=self._split)


def _construct_return_memory(
    restriction: EnvelopeRestrictionWitness,
    split: ResolvedMemorySplit,
) -> ReturnMemoryBound:
    result = object.__new__(ReturnMemoryBound)
    object.__setattr__(result, "_restriction", restriction)
    object.__setattr__(result, "_split", split)
    object.__setattr__(result, "_construction_seal", _RETURN_SEAL)
    result.__post_init__()
    return result


def bound_e2_finite_return_memory(
    *,
    restriction: EnvelopeRestrictionWitness,
    split: ResolvedMemorySplit,
) -> ReturnMemoryBound:
    _derive_return_wire(restriction=restriction, split=split)
    return _construct_return_memory(restriction, split)


# ---------------------------------------------------------------------------
# I0: strict typed hard/nominal pipeline integration.
#
# This layer intentionally lives beside the E2 certificates because the
# frozen I0 endpoint composes E0/E1/E2/S0 authorities.  Its private manifest,
# coverage, arithmetic-row, and report carriers are implementation details;
# only the seven names added to ``__all__`` below are package API.


class PipelineEvidenceTier(str, Enum):
    EXACT = "EXACT"
    EXACT_DECLARED_SYNTHETIC = "EXACT_DECLARED_SYNTHETIC"
    CERTIFIED_SYNTHETIC = "CERTIFIED_SYNTHETIC"
    NOMINAL_DIAGNOSTIC_ONLY = "NOMINAL_DIAGNOSTIC_ONLY"


class PipelineDisposition(str, Enum):
    PASS = "PASS"
    FAIL_HARD_BOUND_EXCEEDED = "FAIL_HARD_BOUND_EXCEEDED"
    ABSTAIN_INCOMPLETE_COVERAGE = "ABSTAIN_INCOMPLETE_COVERAGE"


_I0_FACTOR_SCHEMA = "odlrq.i0.typed-pipeline-factor.v1"
_I0_NOMINAL_SCHEMA = "odlrq.i0.nominal-pipeline-addendum.v1"
_I0_COVERAGE_SCHEMA = "odlrq.i0.pipeline-coverage.v1"
_I0_PROPAGATED_SCHEMA = "odlrq.i0.propagated-epsilon-term.v1"
_I0_TOTAL_SCHEMA = "odlrq.i0.typed-diagnostic-total.v1"
_I0_BINDING_SCHEMA = "odlrq.i0.candidate-authority-binding.v1"
_I0_MANIFEST_SCHEMA = "odlrq.i0.candidate-authority-manifest.v1"
_I0_IDENTITY_SCHEMA = "odlrq.i0.authority-identity.v1"
_I0_REPORT_SCHEMA = "odlrq.i0.pipeline-verification-report.v1"
_I0_BOUND_SCHEMA = "odlrq.i0.typed-pipeline-bound.v1"

_I0_NORM_ID = "weighted_l1_exact_rational_v1"
_I0_HARD_COVERAGE_SCOPE = "I0_HARD_DOMAIN_CHAIN"
_I0_S0_COVERAGE_SCOPE = "S0_DECLARED_SIMILARITY_DOMAIN"
_I0_NOMINAL_COVERAGE_SCOPE = "E2_CANDIDATE_UNIVERSE_SUPPORT"
_I0_VERIFICATION_DISPOSITION = "CPU_SYNTHETIC_TYPED_PIPELINE_BOUND_VERIFIED"

_I0_DOMAINS = (
    "u24.declared_finite_totalized_snapshot.v1",
    "u24.exact_quotient_coordinates.v1",
    "u24.positive_finite_fiber_envelope.v1",
    "u24.certified_finite_horizon_support_profile.v1",
    "u24.certified_finite_level_similarity_profile.v1",
)
_I0_NOMINAL_CODOMAIN = "u24.nominal_fixed_support_law.v1"
_I0_STAGES = ("E0", "E1", "E2", "S0")
_I0_FACTOR_BINDINGS = (
    ("E0.pipeline_source_generator", "E0.pipeline_target_generator"),
    ("E1.accepted_qualification_envelope", "E2.m0_parent_envelope"),
    ("E2.p1_cocycle", "E2.p2_cocycle", "E2.return_memory", "E2.support_token"),
    ("S0.positive_core",),
)

_I0_ACCEPTED_E1_COMMIT = "6fb35aa229fc60e2220cbb68c1e7fff2ce64f199"
_I0_ACCEPTED_E1_TREE = "b3fc7f21b6420e718eb954be0c1b5affca65d263"
_I0_ACCEPTED_E2_COMMIT = "7a8b28872439dd61d40174c2500c5990790002be"
_I0_ACCEPTED_E2_TREE = "d54ed9fab52da4929843fabdeb3c1e1920994f6a"
_I0_ACCEPTED_ME0_COMMIT = "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d"
_I0_ACCEPTED_ME0_TREE = "a3b3513ca93430c9f15e5bd90888e81b0af1ff9c"
_I0_ACCEPTED_S0_COMMIT = "2376aca8209c38a3a94dfa872334073d86dc4909"
_I0_ACCEPTED_S0_TREE = "4b3a2c8b3f3364c411b5444885102035ff3a821f"

_I0_FULL_RUNTIME_SHA256 = "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
_I0_S0_RUNTIME_SHA256 = "88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9"

_I0_S0_AUTHORITY_IDENTITY = (
    "48e8aa4b2a50d93367027d3c924944c160ef806a",
    "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d",
    "docs/experiments/uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md",
    "f137a5c4f8411e2b68d6c88d6a6d09683a766aa2",
    "29557149691",
    "87811636093",
)
_I0_ACTIVATION_IDENTITY = (
    "2e6d0b64a88877dd1f1bd87718186c3ac040c2a4",
    _I0_ACCEPTED_S0_COMMIT,
    "docs/experiments/uprime_odlrq_post_s0_i0_activation_2026-07-17.md",
    "a2e7642e132226e50f7f238a7c6fa708f8492ec9",
    "29561412405",
    "87824486788",
)

_I0_MAX_WIRE_BYTES = 1_048_576
_I0_MAX_DEPTH = 16
_I0_MAX_ARRAY = 256
_I0_MAX_KEYS = 64
_I0_MAX_NODES = 8_192
_I0_MAX_STRING_BYTES = 4_096
_I0_MAX_ID_BYTES = 128
_I0_INPUT_BITS = 256
_I0_INTERMEDIATE_BITS = 4_096
_I0_SIGNED64_MAX = 2**63 - 1
_I0_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_I0_HEX64 = re.compile(r"[0-9A-F]{64}\Z")


def _i0_instance(value: Any, expected: type[Any], fields: tuple[str, ...], where: str) -> Any:
    if type(value) is not expected:
        raise StrictContractError(f"{where} must have exact type {expected.__name__}")
    if type(getattr(value, "__dict__", None)) is not dict or tuple(vars(value)) != fields:
        raise StrictContractError(f"{where} instance layout or serializer was changed")
    return value


def _i0_wire_preflight(value: Any, where: str) -> None:
    nodes = 0
    active: set[int] = set()

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        if depth > _I0_MAX_DEPTH:
            raise StrictContractError(f"{where} exceeds JSON depth {_I0_MAX_DEPTH}")
        nodes += 1
        if nodes > _I0_MAX_NODES:
            raise StrictContractError(f"{where} exceeds structural node cap")
        if item is None or type(item) in (bool, int, str):
            if type(item) is int and not (-2**63 <= item <= _I0_SIGNED64_MAX):
                raise StrictContractError(f"{where} integer is outside signed-64")
            if type(item) is str:
                try:
                    encoded = item.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise StrictContractError(f"{where} contains invalid UTF-8") from exc
                if len(encoded) > _I0_MAX_STRING_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap string")
            return
        if type(item) not in (dict, list):
            raise StrictContractError(f"{where} is outside strict JSON")
        identity = id(item)
        if identity in active:
            raise StrictContractError(f"{where} contains a cycle")
        active.add(identity)
        if type(item) is list:
            if len(item) > _I0_MAX_ARRAY:
                raise StrictContractError(f"{where} contains an over-cap array")
            for child in item:
                visit(child, depth + 1)
        else:
            if len(item) > _I0_MAX_KEYS:
                raise StrictContractError(f"{where} contains an over-cap object")
            for key, child in item.items():
                if type(key) is not str:
                    raise StrictContractError(f"{where} contains a non-string key")
                try:
                    encoded = key.encode("utf-8", errors="strict")
                except UnicodeEncodeError as exc:
                    raise StrictContractError(f"{where} contains an invalid key") from exc
                if len(encoded) > _I0_MAX_STRING_BYTES:
                    raise StrictContractError(f"{where} contains an over-cap key")
                nodes += 1
                if nodes > _I0_MAX_NODES:
                    raise StrictContractError(f"{where} exceeds structural node cap")
                visit(child, depth + 1)
        active.remove(identity)

    visit(value, 0)
    try:
        encoded = canonical_contract_bytes(value)
    except Exception as exc:
        if isinstance(exc, StrictContractError):
            raise
        raise StrictContractError(f"{where} is not canonical JSON") from exc
    if len(encoded) > _I0_MAX_WIRE_BYTES:
        raise StrictContractError(f"{where} exceeds one MiB")


def _i0_object(value: Any, fields: tuple[str, ...], where: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != fields:
        raise StrictContractError(f"{where} fields or insertion order mismatch")
    return value


def _i0_array(value: Any, where: str, *, count: int | None = None) -> list[Any]:
    if type(value) is not list or len(value) > _I0_MAX_ARRAY:
        raise StrictContractError(f"{where} must be an exact bounded array")
    if count is not None and len(value) != count:
        raise StrictContractError(f"{where} must contain exactly {count} rows")
    return value


def _i0_string(value: Any, where: str, *, identifier: bool = False) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} must be strict UTF-8") from exc
    limit = _I0_MAX_ID_BYTES if identifier else _I0_MAX_STRING_BYTES
    if len(encoded) > limit or (identifier and not value.isascii()):
        raise StrictContractError(f"{where} exceeds its canonical string bound")
    return value


def _i0_bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictContractError(f"{where} must be an exact boolean")
    return value


def _i0_int(value: Any, where: str) -> int:
    if type(value) is not int or not (0 <= value <= _I0_SIGNED64_MAX):
        raise StrictContractError(f"{where} must be a nonnegative signed-64 integer")
    return value


def _i0_sha1(value: Any, where: str) -> str:
    if type(value) is not str or _I0_HEX40.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be canonical lowercase SHA-1")
    return value


def _i0_sha256(value: Any, where: str) -> str:
    if type(value) is not str or _I0_HEX64.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be canonical uppercase SHA-256")
    return value


def _i0_tier(value: Any, where: str) -> PipelineEvidenceTier:
    if type(value) is not PipelineEvidenceTier:
        raise StrictContractError(f"{where} must be an exact PipelineEvidenceTier")
    return value


def _i0_tier_wire(value: Any, where: str) -> PipelineEvidenceTier:
    if type(value) is not str:
        raise StrictContractError(f"{where} must be a closed tier string")
    try:
        return PipelineEvidenceTier(value)
    except ValueError as exc:
        raise StrictContractError(f"{where} is outside the closed tier vocabulary") from exc


def _i0_disposition(value: Any, where: str) -> PipelineDisposition:
    if type(value) is not PipelineDisposition:
        raise StrictContractError(f"{where} must be an exact PipelineDisposition")
    return value


def _i0_disposition_wire(value: Any, where: str) -> PipelineDisposition:
    if type(value) is not str:
        raise StrictContractError(f"{where} must be a closed disposition string")
    try:
        return PipelineDisposition(value)
    except ValueError as exc:
        raise StrictContractError(f"{where} is outside the closed disposition vocabulary") from exc


def _i0_rational(value: Any, where: str, *, bits: int, nonnegative: bool = True) -> ExactRational:
    _i0_instance(value, ExactRational, ("numerator", "denominator"), where)
    if type(value.numerator) is not int or type(value.denominator) is not int:
        raise StrictContractError(f"{where} rational scalars have wrong types")
    if value.denominator <= 0 or gcd(abs(value.numerator), value.denominator) != 1:
        raise StrictContractError(f"{where} must be reduced with positive denominator")
    if value.numerator == 0 and value.denominator != 1:
        raise StrictContractError(f"{where} zero must have denominator one")
    if nonnegative and value.numerator < 0:
        raise StrictContractError(f"{where} must be nonnegative")
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > bits:
        raise StrictContractError(f"{where} exceeds the {bits}-bit cap")
    return value


def _i0_rational_from_wire(value: Any, where: str, *, bits: int) -> ExactRational:
    _i0_object(value, ("schema_version", "numerator", "denominator"), where)
    try:
        result = ExactRational.from_dict(value)
    except Exception as exc:
        if isinstance(exc, StrictContractError):
            raise
        raise StrictContractError(f"{where} is not an ExactRational wire") from exc
    _i0_rational(result, where, bits=bits)
    if ExactRational.to_dict(result) != value:
        raise StrictContractError(f"{where} rational wire is not canonical")
    return result


def _i0_eq_rational(value: ExactRational, numerator: int, denominator: int = 1) -> bool:
    return value.numerator == numerator and value.denominator == denominator


def _i0_check_intermediate(value: int, where: str) -> None:
    if abs(value).bit_length() > _I0_INTERMEDIATE_BITS:
        raise StrictContractError(f"{where} exceeds the 4096-bit intermediate cap")


def _i0_derived(numerator: int, denominator: int, where: str) -> ExactRational:
    _i0_check_intermediate(numerator, f"{where} numerator")
    _i0_check_intermediate(denominator, f"{where} denominator")
    if denominator <= 0:
        raise StrictContractError(f"{where} denominator must be positive")
    divisor = gcd(abs(numerator), denominator)
    numerator //= divisor
    denominator //= divisor
    if numerator == 0:
        denominator = 1
    _i0_check_intermediate(numerator, f"{where} normalized numerator")
    _i0_check_intermediate(denominator, f"{where} normalized denominator")
    return ExactRational(numerator, denominator)


def _i0_mul(left: ExactRational, right: ExactRational, where: str) -> ExactRational:
    _i0_rational(left, f"{where} left", bits=_I0_INTERMEDIATE_BITS)
    _i0_rational(right, f"{where} right", bits=_I0_INTERMEDIATE_BITS)
    numerator = left.numerator * right.numerator
    denominator = left.denominator * right.denominator
    _i0_check_intermediate(numerator, f"{where} raw numerator product")
    _i0_check_intermediate(denominator, f"{where} raw denominator product")
    return _i0_derived(numerator, denominator, where)


def _i0_add(left: ExactRational, right: ExactRational, where: str) -> ExactRational:
    _i0_rational(left, f"{where} left", bits=_I0_INTERMEDIATE_BITS)
    _i0_rational(right, f"{where} right", bits=_I0_INTERMEDIATE_BITS)
    left_scaled = left.numerator * right.denominator
    right_scaled = right.numerator * left.denominator
    denominator = left.denominator * right.denominator
    for raw, label in (
        (left_scaled, "left cross-product"),
        (right_scaled, "right cross-product"),
        (denominator, "denominator product"),
    ):
        _i0_check_intermediate(raw, f"{where} {label}")
    numerator = left_scaled + right_scaled
    _i0_check_intermediate(numerator, f"{where} numerator sum")
    return _i0_derived(numerator, denominator, where)


def _i0_le(left: ExactRational, right: ExactRational, where: str) -> bool:
    left_cross = left.numerator * right.denominator
    right_cross = right.numerator * left.denominator
    _i0_check_intermediate(left_cross, f"{where} left comparison product")
    _i0_check_intermediate(right_cross, f"{where} right comparison product")
    return left_cross <= right_cross


@dataclass(frozen=True)
class _PipelineCoverage:
    covered_count: int
    universe_count: int
    coverage_scope: str
    complete: bool

    def __post_init__(self) -> None:
        _i0_instance(self, _PipelineCoverage, ("covered_count", "universe_count", "coverage_scope", "complete"), "pipeline coverage")
        covered = _i0_int(self.covered_count, "pipeline covered_count")
        universe = _i0_int(self.universe_count, "pipeline universe_count")
        _i0_string(self.coverage_scope, "pipeline coverage_scope", identifier=True)
        _i0_bool(self.complete, "pipeline complete")
        if universe == 0 or covered > universe or self.complete is not (covered == universe):
            raise StrictContractError("pipeline coverage count/completeness mismatch")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_COVERAGE_SCHEMA,
            "covered_count": self.covered_count,
            "universe_count": self.universe_count,
            "coverage_scope": self.coverage_scope,
            "complete": self.complete,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_PipelineCoverage":
        if cls is not _PipelineCoverage:
            raise StrictContractError("polymorphic pipeline coverage parsing is forbidden")
        _i0_wire_preflight(value, "pipeline coverage")
        obj = _i0_object(value, ("schema_version", "covered_count", "universe_count", "coverage_scope", "complete"), "pipeline coverage")
        if obj["schema_version"] != _I0_COVERAGE_SCHEMA:
            raise StrictContractError("pipeline coverage schema mismatch")
        result = cls(obj["covered_count"], obj["universe_count"], obj["coverage_scope"], obj["complete"])
        if result.to_dict() != obj:
            raise StrictContractError("pipeline coverage wire is not canonical")
        return result


_I0_BINDING_ROLES = {
    "PIPELINE_OBJECT", "LINEAGE_ANCHOR", "HARD_AUTHORITY",
    "NOMINAL_DIAGNOSTIC", "HARD_CORE", "PREDICTIVE_CORE", "FULL_CONTAINER",
}
_I0_DIGEST_DOMAINS = {
    "CANONICAL_CONTRACT_BYTES_SHA256",
    "WINDOWS_RUNTIME_CANONICAL_WIRE_SHA256",
    "CANONICAL_PROJECTION_BYTES_SHA256",
}


@dataclass(frozen=True)
class _CandidateAuthorityBinding:
    binding_id: str
    semantic_stage_id: str
    producer_stage_id: str
    binding_role: str
    object_schema: str
    digest_domain: str
    object_sha256: str
    source_commit: str
    source_tree: str
    evidence_tier: PipelineEvidenceTier
    hard_eligible: bool

    def __post_init__(self) -> None:
        names = ("binding_id", "semantic_stage_id", "producer_stage_id", "binding_role", "object_schema", "digest_domain", "object_sha256", "source_commit", "source_tree", "evidence_tier", "hard_eligible")
        _i0_instance(self, _CandidateAuthorityBinding, names, "candidate authority binding")
        for name in ("binding_id", "semantic_stage_id", "producer_stage_id", "object_schema"):
            _i0_string(getattr(self, name), f"binding {name}", identifier=True)
        if self.binding_role not in _I0_BINDING_ROLES:
            raise StrictContractError("candidate binding role is outside its closed vocabulary")
        if self.digest_domain not in _I0_DIGEST_DOMAINS:
            raise StrictContractError("candidate binding digest domain is outside its closed vocabulary")
        _i0_sha256(self.object_sha256, "candidate binding object_sha256")
        _i0_sha1(self.source_commit, "candidate binding source_commit")
        _i0_sha1(self.source_tree, "candidate binding source_tree")
        _i0_tier(self.evidence_tier, "candidate binding tier")
        _i0_bool(self.hard_eligible, "candidate binding hard_eligible")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_BINDING_SCHEMA,
            "binding_id": self.binding_id,
            "semantic_stage_id": self.semantic_stage_id,
            "producer_stage_id": self.producer_stage_id,
            "binding_role": self.binding_role,
            "object_schema": self.object_schema,
            "digest_domain": self.digest_domain,
            "object_sha256": self.object_sha256,
            "source_commit": self.source_commit,
            "source_tree": self.source_tree,
            "evidence_tier": self.evidence_tier.value,
            "hard_eligible": self.hard_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_CandidateAuthorityBinding":
        fields = ("schema_version", "binding_id", "semantic_stage_id", "producer_stage_id", "binding_role", "object_schema", "digest_domain", "object_sha256", "source_commit", "source_tree", "evidence_tier", "hard_eligible")
        obj = _i0_object(value, fields, "candidate authority binding")
        if obj["schema_version"] != _I0_BINDING_SCHEMA:
            raise StrictContractError("candidate authority binding schema mismatch")
        result = cls(
            obj["binding_id"], obj["semantic_stage_id"], obj["producer_stage_id"],
            obj["binding_role"], obj["object_schema"], obj["digest_domain"],
            obj["object_sha256"], obj["source_commit"], obj["source_tree"],
            _i0_tier_wire(obj["evidence_tier"], "candidate binding evidence_tier"),
            obj["hard_eligible"],
        )
        if result.to_dict() != obj:
            raise StrictContractError("candidate authority binding wire is not canonical")
        return result


@dataclass(frozen=True)
class _AuthorityIdentity:
    authority_commit_sha: str
    authority_parent_sha: str
    authority_document_path: str
    authority_document_blob_sha: str
    authority_ci_run_id: str
    authority_ci_job_id: str

    def __post_init__(self) -> None:
        names = ("authority_commit_sha", "authority_parent_sha", "authority_document_path", "authority_document_blob_sha", "authority_ci_run_id", "authority_ci_job_id")
        _i0_instance(self, _AuthorityIdentity, names, "authority identity")
        _i0_sha1(self.authority_commit_sha, "authority commit")
        _i0_sha1(self.authority_parent_sha, "authority parent")
        _i0_string(self.authority_document_path, "authority document path")
        _i0_sha1(self.authority_document_blob_sha, "authority document blob")
        for name in ("authority_ci_run_id", "authority_ci_job_id"):
            value = _i0_string(getattr(self, name), name, identifier=True)
            if not value.isdecimal() or value.startswith("0"):
                raise StrictContractError(f"{name} must be a canonical positive decimal string")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_IDENTITY_SCHEMA,
            "authority_commit_sha": self.authority_commit_sha,
            "authority_parent_sha": self.authority_parent_sha,
            "authority_document_path": self.authority_document_path,
            "authority_document_blob_sha": self.authority_document_blob_sha,
            "authority_ci_run_id": self.authority_ci_run_id,
            "authority_ci_job_id": self.authority_ci_job_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_AuthorityIdentity":
        fields = ("schema_version", "authority_commit_sha", "authority_parent_sha", "authority_document_path", "authority_document_blob_sha", "authority_ci_run_id", "authority_ci_job_id")
        obj = _i0_object(value, fields, "authority identity")
        if obj["schema_version"] != _I0_IDENTITY_SCHEMA:
            raise StrictContractError("authority identity schema mismatch")
        result = cls(obj["authority_commit_sha"], obj["authority_parent_sha"], obj["authority_document_path"], obj["authority_document_blob_sha"], obj["authority_ci_run_id"], obj["authority_ci_job_id"])
        if result.to_dict() != obj:
            raise StrictContractError("authority identity wire is not canonical")
        return result


def _i0_binding_wire(
    binding_id: str,
    semantic_stage_id: str,
    producer_stage_id: str,
    binding_role: str,
    object_schema: str,
    digest_domain: str,
    object_sha256: str,
    source_commit: str,
    source_tree: str,
    evidence_tier: PipelineEvidenceTier,
    hard_eligible: bool,
) -> dict[str, Any]:
    return _CandidateAuthorityBinding(
        binding_id, semantic_stage_id, producer_stage_id, binding_role,
        object_schema, digest_domain, object_sha256, source_commit, source_tree,
        evidence_tier, hard_eligible,
    ).to_dict()


def _i0_expected_binding_wires() -> list[dict[str, Any]]:
    exact_declared = PipelineEvidenceTier.EXACT_DECLARED_SYNTHETIC
    certified = PipelineEvidenceTier.CERTIFIED_SYNTHETIC
    nominal = PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
    canonical = "CANONICAL_CONTRACT_BYTES_SHA256"
    projection = "CANONICAL_PROJECTION_BYTES_SHA256"
    return [
        _i0_binding_wire(
            "E0.pipeline_source_generator", "E0", "E2", "PIPELINE_OBJECT",
            "odlrq_exact_quotient_coordinate_generator_v1", canonical,
            "5C920F94FA38B6F116526D0BC00340882DE5C1288A8BAE0857F54EB727A3D262",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, exact_declared, True,
        ),
        _i0_binding_wire(
            "E0.pipeline_target_generator", "E0", "E2", "PIPELINE_OBJECT",
            "odlrq_exact_quotient_coordinate_generator_v1", canonical,
            "7281601FA840B29AC3F97AB4E2D5953163706E9C2CEEC8EE3855A8FB9807161C",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, exact_declared, True,
        ),
        _i0_binding_wire(
            "E1.accepted_qualification_envelope", "E1", "E1", "LINEAGE_ANCHOR",
            "odlrq_fiber_envelope_v1", canonical,
            "D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6",
            _I0_ACCEPTED_E1_COMMIT, _I0_ACCEPTED_E1_TREE, exact_declared, True,
        ),
        _i0_binding_wire(
            "E2.m0_parent_envelope", "E1", "E2", "HARD_AUTHORITY",
            "odlrq_fiber_envelope_v1", canonical,
            "9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, exact_declared, True,
        ),
        _i0_binding_wire(
            "E2.p1_cocycle", "E2", "E2", "HARD_AUTHORITY",
            "odlrq.e2.cocycle-certificate.v1", canonical,
            "6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, certified, True,
        ),
        _i0_binding_wire(
            "E2.p2_cocycle", "E2", "E2", "HARD_AUTHORITY",
            "odlrq.e2.cocycle-certificate.v1", canonical,
            "BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, certified, True,
        ),
        _i0_binding_wire(
            "E2.return_memory", "E2", "E2", "HARD_AUTHORITY",
            "odlrq.e2.finite-return-memory.v1", canonical,
            "95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, certified, True,
        ),
        _i0_binding_wire(
            "E2.support_token", "E2", "E2", "HARD_AUTHORITY",
            "odlrq.e2.certified-support-token.v1", canonical,
            "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660",
            _I0_ACCEPTED_E2_COMMIT, _I0_ACCEPTED_E2_TREE, certified, True,
        ),
        _i0_binding_wire(
            "ME0.nontrivial_orbit_windows_result", "ME0", "ME0", "NOMINAL_DIAGNOSTIC",
            "odlrq.me0.maxent-result.v1", "WINDOWS_RUNTIME_CANONICAL_WIRE_SHA256",
            "DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3",
            _I0_ACCEPTED_ME0_COMMIT, _I0_ACCEPTED_ME0_TREE, nominal, False,
        ),
        _i0_binding_wire(
            "S0.positive_core", "S0", "S0", "HARD_CORE",
            "odlrq.s0.positive-core-projection.v1", projection,
            "8670B7381468EC47EBF7DFCEEC6EF1B847A5B4DB40935B2A7521C22A645B96D7",
            _I0_ACCEPTED_S0_COMMIT, _I0_ACCEPTED_S0_TREE, certified, True,
        ),
        _i0_binding_wire(
            "S0.predictive_core", "S0", "S0", "PREDICTIVE_CORE",
            "odlrq.s0.predictive-core-projection.v1", projection,
            "2AEF5156AB4A3C6D329C2346DFAD731D9B0E7BA33CEDC65487B187CF0E383F7E",
            _I0_ACCEPTED_S0_COMMIT, _I0_ACCEPTED_S0_TREE, nominal, False,
        ),
        _i0_binding_wire(
            "S0.full_similarity_certificate", "S0", "S0", "FULL_CONTAINER",
            "odlrq.s0.similarity-certificate.v1", canonical,
            "86C3AF246466BB62A2297EEF40E437CC9152110DC1EF69F64ACCA2A8D0FA3D35",
            _I0_ACCEPTED_S0_COMMIT, _I0_ACCEPTED_S0_TREE, nominal, False,
        ),
    ]


def _i0_identity_wire(values: tuple[str, str, str, str, str, str]) -> dict[str, Any]:
    return _AuthorityIdentity(*values).to_dict()


def _i0_expected_manifest_wire() -> dict[str, Any]:
    """Return a detached exact candidate-manifest wire for fixture builders."""
    return {
        "schema_version": _I0_MANIFEST_SCHEMA,
        "ordered_bindings": _i0_expected_binding_wires(),
        "full_runtime_manifest_sha256": _I0_FULL_RUNTIME_SHA256,
        "s0_runtime_manifest_sha256": _I0_S0_RUNTIME_SHA256,
        "s0_authority_identity": _i0_identity_wire(_I0_S0_AUTHORITY_IDENTITY),
        "i0_activation_identity": _i0_identity_wire(_I0_ACTIVATION_IDENTITY),
    }


@dataclass(frozen=True)
class _CandidateAuthorityManifest:
    ordered_bindings: tuple[_CandidateAuthorityBinding, ...]
    full_runtime_manifest_sha256: str
    s0_runtime_manifest_sha256: str
    s0_authority_identity: _AuthorityIdentity
    i0_activation_identity: _AuthorityIdentity

    def __post_init__(self) -> None:
        names = ("ordered_bindings", "full_runtime_manifest_sha256", "s0_runtime_manifest_sha256", "s0_authority_identity", "i0_activation_identity")
        _i0_instance(self, _CandidateAuthorityManifest, names, "candidate authority manifest")
        if type(self.ordered_bindings) is not tuple or len(self.ordered_bindings) != 12:
            raise StrictContractError("candidate manifest must have exactly twelve bindings")
        for row in self.ordered_bindings:
            _CandidateAuthorityBinding.to_dict(_i0_instance(row, _CandidateAuthorityBinding, ("binding_id", "semantic_stage_id", "producer_stage_id", "binding_role", "object_schema", "digest_domain", "object_sha256", "source_commit", "source_tree", "evidence_tier", "hard_eligible"), "candidate manifest binding"))
        if len({row.binding_id for row in self.ordered_bindings}) != 12:
            raise StrictContractError("candidate manifest binding ids must be unique")
        _i0_sha256(self.full_runtime_manifest_sha256, "full runtime manifest digest")
        _i0_sha256(self.s0_runtime_manifest_sha256, "S0 runtime manifest digest")
        _AuthorityIdentity.to_dict(_i0_instance(self.s0_authority_identity, _AuthorityIdentity, ("authority_commit_sha", "authority_parent_sha", "authority_document_path", "authority_document_blob_sha", "authority_ci_run_id", "authority_ci_job_id"), "S0 authority identity"))
        _AuthorityIdentity.to_dict(_i0_instance(self.i0_activation_identity, _AuthorityIdentity, ("authority_commit_sha", "authority_parent_sha", "authority_document_path", "authority_document_blob_sha", "authority_ci_run_id", "authority_ci_job_id"), "I0 activation identity"))

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_MANIFEST_SCHEMA,
            "ordered_bindings": [_CandidateAuthorityBinding.to_dict(row) for row in self.ordered_bindings],
            "full_runtime_manifest_sha256": self.full_runtime_manifest_sha256,
            "s0_runtime_manifest_sha256": self.s0_runtime_manifest_sha256,
            "s0_authority_identity": _AuthorityIdentity.to_dict(self.s0_authority_identity),
            "i0_activation_identity": _AuthorityIdentity.to_dict(self.i0_activation_identity),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_CandidateAuthorityManifest":
        if cls is not _CandidateAuthorityManifest:
            raise StrictContractError("polymorphic candidate manifest parsing is forbidden")
        _i0_wire_preflight(value, "candidate authority manifest")
        fields = ("schema_version", "ordered_bindings", "full_runtime_manifest_sha256", "s0_runtime_manifest_sha256", "s0_authority_identity", "i0_activation_identity")
        obj = _i0_object(value, fields, "candidate authority manifest")
        if obj["schema_version"] != _I0_MANIFEST_SCHEMA:
            raise StrictContractError("candidate authority manifest schema mismatch")
        rows = tuple(_CandidateAuthorityBinding.from_dict(row) for row in _i0_array(obj["ordered_bindings"], "candidate manifest bindings", count=12))
        result = cls(
            rows,
            obj["full_runtime_manifest_sha256"],
            obj["s0_runtime_manifest_sha256"],
            _AuthorityIdentity.from_dict(obj["s0_authority_identity"]),
            _AuthorityIdentity.from_dict(obj["i0_activation_identity"]),
        )
        result_wire = result.to_dict()
        if result_wire != obj:
            raise StrictContractError("candidate authority manifest wire is not canonical")
        expected = _i0_expected_manifest_wire()
        if canonical_contract_bytes(result_wire) != canonical_contract_bytes(expected):
            raise StrictContractError("candidate authority manifest is stale, reordered, or spliced")
        return result


def _i0_manifest(value: Any, where: str) -> _CandidateAuthorityManifest:
    if type(value) is dict:
        return _CandidateAuthorityManifest.from_dict(value)
    _i0_instance(value, _CandidateAuthorityManifest, ("ordered_bindings", "full_runtime_manifest_sha256", "s0_runtime_manifest_sha256", "s0_authority_identity", "i0_activation_identity"), where)
    wire = _CandidateAuthorityManifest.to_dict(value)
    if canonical_contract_bytes(wire) != canonical_contract_bytes(_i0_expected_manifest_wire()):
        raise StrictContractError(f"{where} is stale, reordered, or spliced")
    return _CandidateAuthorityManifest.from_dict(wire)


def _i0_binding_ids(value: Any, where: str) -> tuple[str, ...]:
    if type(value) is not tuple or not value or len(value) > 8:
        raise StrictContractError(f"{where} must be a nonempty exact bounded tuple")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_i0_string(item, f"{where}[{index}]", identifier=True))
    if len(set(result)) != len(result):
        raise StrictContractError(f"{where} must not contain duplicate bindings")
    return tuple(result)


def _i0_factor_post_init(value: Any, expected_type: type[Any], where: str) -> None:
    names = ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible")
    _i0_instance(value, expected_type, names, where)
    for name in ("stage_id", "domain_id", "codomain_id", "norm_id"):
        _i0_string(getattr(value, name), f"{where} {name}", identifier=True)
    L = _i0_rational(value.L, f"{where} L", bits=_I0_INPUT_BITS)
    _i0_rational(value.epsilon, f"{where} epsilon", bits=_I0_INPUT_BITS)
    if L.numerator <= 0:
        raise StrictContractError(f"{where} L must be positive")
    _i0_tier(value.evidence_tier, f"{where} evidence_tier")
    _i0_binding_ids(value.authority_bindings, f"{where} authority_bindings")
    _PipelineCoverage.to_dict(_i0_instance(value.coverage, _PipelineCoverage, ("covered_count", "universe_count", "coverage_scope", "complete"), f"{where} coverage"))
    _i0_bool(value.hard_eligible, f"{where} hard_eligible")


def _i0_factor_to_dict(value: Any, expected_type: type[Any], schema: str, where: str) -> dict[str, Any]:
    _i0_factor_post_init(value, expected_type, where)
    return {
        "schema_version": schema,
        "stage_id": value.stage_id,
        "domain_id": value.domain_id,
        "codomain_id": value.codomain_id,
        "norm_id": value.norm_id,
        "L": ExactRational.to_dict(value.L),
        "epsilon": ExactRational.to_dict(value.epsilon),
        "evidence_tier": value.evidence_tier.value,
        "authority_bindings": list(value.authority_bindings),
        "coverage": _PipelineCoverage.to_dict(value.coverage),
        "hard_eligible": value.hard_eligible,
    }


def _i0_parse_factor_wire(value: Any, expected_type: type[Any], schema: str, where: str) -> Any:
    _i0_wire_preflight(value, where)
    fields = ("schema_version", "stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible")
    obj = _i0_object(value, fields, where)
    if obj["schema_version"] != schema:
        raise StrictContractError(f"{where} schema mismatch")
    binding_rows = _i0_array(obj["authority_bindings"], f"{where} authority_bindings")
    result = expected_type(
        obj["stage_id"], obj["domain_id"], obj["codomain_id"], obj["norm_id"],
        _i0_rational_from_wire(obj["L"], f"{where} L", bits=_I0_INPUT_BITS),
        _i0_rational_from_wire(obj["epsilon"], f"{where} epsilon", bits=_I0_INPUT_BITS),
        _i0_tier_wire(obj["evidence_tier"], f"{where} evidence_tier"),
        tuple(_i0_string(item, f"{where} authority binding", identifier=True) for item in binding_rows),
        _PipelineCoverage.from_dict(obj["coverage"]),
        obj["hard_eligible"],
    )
    if _i0_factor_to_dict(result, expected_type, schema, where) != obj:
        raise StrictContractError(f"{where} wire is not canonical")
    return result


@dataclass(frozen=True)
class TypedPipelineFactor:
    stage_id: str
    domain_id: str
    codomain_id: str
    norm_id: str
    L: ExactRational
    epsilon: ExactRational
    evidence_tier: PipelineEvidenceTier
    authority_bindings: tuple[str, ...]
    coverage: _PipelineCoverage
    hard_eligible: bool

    def __post_init__(self) -> None:
        _i0_factor_post_init(self, TypedPipelineFactor, "TypedPipelineFactor")

    def to_dict(self) -> dict[str, Any]:
        return _i0_factor_to_dict(self, TypedPipelineFactor, _I0_FACTOR_SCHEMA, "TypedPipelineFactor")

    @classmethod
    def from_dict(cls, value: Any) -> "TypedPipelineFactor":
        if cls is not TypedPipelineFactor:
            raise StrictContractError("polymorphic TypedPipelineFactor parsing is forbidden")
        return _i0_parse_factor_wire(value, TypedPipelineFactor, _I0_FACTOR_SCHEMA, "TypedPipelineFactor")


@dataclass(frozen=True)
class NominalPipelineAddendum:
    stage_id: str
    domain_id: str
    codomain_id: str
    norm_id: str
    L: ExactRational
    epsilon: ExactRational
    evidence_tier: PipelineEvidenceTier
    authority_bindings: tuple[str, ...]
    coverage: _PipelineCoverage
    hard_eligible: bool

    def __post_init__(self) -> None:
        _i0_factor_post_init(self, NominalPipelineAddendum, "NominalPipelineAddendum")

    def to_dict(self) -> dict[str, Any]:
        return _i0_factor_to_dict(self, NominalPipelineAddendum, _I0_NOMINAL_SCHEMA, "NominalPipelineAddendum")

    @classmethod
    def from_dict(cls, value: Any) -> "NominalPipelineAddendum":
        if cls is not NominalPipelineAddendum:
            raise StrictContractError("polymorphic NominalPipelineAddendum parsing is forbidden")
        return _i0_parse_factor_wire(value, NominalPipelineAddendum, _I0_NOMINAL_SCHEMA, "NominalPipelineAddendum")


@dataclass(frozen=True)
class _PropagatedEpsilonTerm:
    stage_id: str
    downstream_L: ExactRational
    epsilon: ExactRational
    contribution: ExactRational

    def __post_init__(self) -> None:
        names = ("stage_id", "downstream_L", "epsilon", "contribution")
        _i0_instance(self, _PropagatedEpsilonTerm, names, "propagated epsilon term")
        _i0_string(self.stage_id, "propagated epsilon stage", identifier=True)
        for name in ("downstream_L", "epsilon", "contribution"):
            _i0_rational(getattr(self, name), f"propagated epsilon {name}", bits=_I0_INTERMEDIATE_BITS)

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_PROPAGATED_SCHEMA,
            "stage_id": self.stage_id,
            "downstream_L": ExactRational.to_dict(self.downstream_L),
            "epsilon": ExactRational.to_dict(self.epsilon),
            "contribution": ExactRational.to_dict(self.contribution),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_PropagatedEpsilonTerm":
        fields = ("schema_version", "stage_id", "downstream_L", "epsilon", "contribution")
        obj = _i0_object(value, fields, "propagated epsilon term")
        if obj["schema_version"] != _I0_PROPAGATED_SCHEMA:
            raise StrictContractError("propagated epsilon term schema mismatch")
        result = cls(
            obj["stage_id"],
            _i0_rational_from_wire(obj["downstream_L"], "propagated downstream L", bits=_I0_INTERMEDIATE_BITS),
            _i0_rational_from_wire(obj["epsilon"], "propagated epsilon", bits=_I0_INTERMEDIATE_BITS),
            _i0_rational_from_wire(obj["contribution"], "propagated contribution", bits=_I0_INTERMEDIATE_BITS),
        )
        if result.to_dict() != obj:
            raise StrictContractError("propagated epsilon term wire is not canonical")
        return result


@dataclass(frozen=True)
class _TypedDiagnosticTotal:
    value: ExactRational
    evidence_tier: PipelineEvidenceTier
    hard_eligible: bool

    def __post_init__(self) -> None:
        _i0_instance(self, _TypedDiagnosticTotal, ("value", "evidence_tier", "hard_eligible"), "typed diagnostic total")
        _i0_rational(self.value, "typed diagnostic total value", bits=_I0_INTERMEDIATE_BITS)
        _i0_tier(self.evidence_tier, "typed diagnostic total tier")
        _i0_bool(self.hard_eligible, "typed diagnostic total hard_eligible")
        if self.evidence_tier is not PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY or self.hard_eligible is not False:
            raise StrictContractError("typed diagnostic total crossed the nominal firewall")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_TOTAL_SCHEMA,
            "value": ExactRational.to_dict(self.value),
            "evidence_tier": self.evidence_tier.value,
            "hard_eligible": self.hard_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_TypedDiagnosticTotal":
        fields = ("schema_version", "value", "evidence_tier", "hard_eligible")
        obj = _i0_object(value, fields, "typed diagnostic total")
        if obj["schema_version"] != _I0_TOTAL_SCHEMA:
            raise StrictContractError("typed diagnostic total schema mismatch")
        result = cls(
            _i0_rational_from_wire(obj["value"], "typed diagnostic total value", bits=_I0_INTERMEDIATE_BITS),
            _i0_tier_wire(obj["evidence_tier"], "typed diagnostic total evidence_tier"),
            obj["hard_eligible"],
        )
        if result.to_dict() != obj:
            raise StrictContractError("typed diagnostic total wire is not canonical")
        return result


@dataclass(frozen=True)
class _PipelineVerificationReport:
    hard_factor_count: int
    hard_factor_order_sha256: str
    initial_term: ExactRational | None
    propagated_epsilon_terms: tuple[_PropagatedEpsilonTerm, ...]
    recomputed_hard_bound: ExactRational | None
    recomputed_nominal_addendum: ExactRational | None
    recomputed_total_bound: _TypedDiagnosticTotal | None
    coverage_complete: bool
    tier_firewall_verified: bool
    domain_chain_verified: bool
    norm_chain_verified: bool
    authority_manifest_verified: bool
    disposition_verified: bool
    verification_disposition: str

    def __post_init__(self) -> None:
        names = (
            "hard_factor_count", "hard_factor_order_sha256", "initial_term",
            "propagated_epsilon_terms", "recomputed_hard_bound",
            "recomputed_nominal_addendum", "recomputed_total_bound",
            "coverage_complete", "tier_firewall_verified", "domain_chain_verified",
            "norm_chain_verified", "authority_manifest_verified",
            "disposition_verified", "verification_disposition",
        )
        _i0_instance(self, _PipelineVerificationReport, names, "pipeline verification report")
        _i0_int(self.hard_factor_count, "report hard_factor_count")
        _i0_sha256(self.hard_factor_order_sha256, "report hard factor order digest")
        if self.initial_term is not None:
            _i0_rational(self.initial_term, "report initial term", bits=_I0_INTERMEDIATE_BITS)
        if type(self.propagated_epsilon_terms) is not tuple or len(self.propagated_epsilon_terms) > 4:
            raise StrictContractError("report propagated terms must be an exact bounded tuple")
        for term in self.propagated_epsilon_terms:
            _PropagatedEpsilonTerm.to_dict(_i0_instance(term, _PropagatedEpsilonTerm, ("stage_id", "downstream_L", "epsilon", "contribution"), "report propagated term"))
        if self.recomputed_hard_bound is not None:
            _i0_rational(self.recomputed_hard_bound, "report recomputed hard bound", bits=_I0_INTERMEDIATE_BITS)
        if self.recomputed_nominal_addendum is not None:
            _i0_rational(self.recomputed_nominal_addendum, "report recomputed nominal addendum", bits=_I0_INTERMEDIATE_BITS)
        if self.recomputed_total_bound is not None:
            _TypedDiagnosticTotal.to_dict(_i0_instance(self.recomputed_total_bound, _TypedDiagnosticTotal, ("value", "evidence_tier", "hard_eligible"), "report recomputed total bound"))
        for name in (
            "coverage_complete", "tier_firewall_verified", "domain_chain_verified",
            "norm_chain_verified", "authority_manifest_verified", "disposition_verified",
        ):
            _i0_bool(getattr(self, name), f"report {name}")
        if self.verification_disposition != _I0_VERIFICATION_DISPOSITION:
            raise StrictContractError("pipeline verification disposition mismatch")

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_REPORT_SCHEMA,
            "hard_factor_count": self.hard_factor_count,
            "hard_factor_order_sha256": self.hard_factor_order_sha256,
            "initial_term": None if self.initial_term is None else ExactRational.to_dict(self.initial_term),
            "propagated_epsilon_terms": [_PropagatedEpsilonTerm.to_dict(row) for row in self.propagated_epsilon_terms],
            "recomputed_hard_bound": None if self.recomputed_hard_bound is None else ExactRational.to_dict(self.recomputed_hard_bound),
            "recomputed_nominal_addendum": None if self.recomputed_nominal_addendum is None else ExactRational.to_dict(self.recomputed_nominal_addendum),
            "recomputed_total_bound": None if self.recomputed_total_bound is None else _TypedDiagnosticTotal.to_dict(self.recomputed_total_bound),
            "coverage_complete": self.coverage_complete,
            "tier_firewall_verified": self.tier_firewall_verified,
            "domain_chain_verified": self.domain_chain_verified,
            "norm_chain_verified": self.norm_chain_verified,
            "authority_manifest_verified": self.authority_manifest_verified,
            "disposition_verified": self.disposition_verified,
            "verification_disposition": self.verification_disposition,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "_PipelineVerificationReport":
        fields = (
            "schema_version", "hard_factor_count", "hard_factor_order_sha256",
            "initial_term", "propagated_epsilon_terms", "recomputed_hard_bound",
            "recomputed_nominal_addendum", "recomputed_total_bound",
            "coverage_complete", "tier_firewall_verified", "domain_chain_verified",
            "norm_chain_verified", "authority_manifest_verified",
            "disposition_verified", "verification_disposition",
        )
        obj = _i0_object(value, fields, "pipeline verification report")
        if obj["schema_version"] != _I0_REPORT_SCHEMA:
            raise StrictContractError("pipeline verification report schema mismatch")
        terms = tuple(_PropagatedEpsilonTerm.from_dict(row) for row in _i0_array(obj["propagated_epsilon_terms"], "report propagated terms"))

        def optional_rational(raw: Any, where: str) -> ExactRational | None:
            return None if raw is None else _i0_rational_from_wire(raw, where, bits=_I0_INTERMEDIATE_BITS)

        total = None if obj["recomputed_total_bound"] is None else _TypedDiagnosticTotal.from_dict(obj["recomputed_total_bound"])
        result = cls(
            obj["hard_factor_count"], obj["hard_factor_order_sha256"],
            optional_rational(obj["initial_term"], "report initial term"), terms,
            optional_rational(obj["recomputed_hard_bound"], "report hard bound"),
            optional_rational(obj["recomputed_nominal_addendum"], "report nominal addendum"),
            total, obj["coverage_complete"], obj["tier_firewall_verified"],
            obj["domain_chain_verified"], obj["norm_chain_verified"],
            obj["authority_manifest_verified"], obj["disposition_verified"],
            obj["verification_disposition"],
        )
        if result.to_dict() != obj:
            raise StrictContractError("pipeline verification report wire is not canonical")
        return result


@dataclass(frozen=True)
class TypedPipelineBound:
    candidate_authority_manifest: _CandidateAuthorityManifest
    ordered_hard_factors: tuple[TypedPipelineFactor, ...]
    initial_residual: ExactRational
    hard_bound: ExactRational | None
    hard_threshold: ExactRational
    nominal_addendum: NominalPipelineAddendum | None
    total_bound: _TypedDiagnosticTotal | None
    coverage: _PipelineCoverage
    disposition: PipelineDisposition
    verification_report: _PipelineVerificationReport

    def __post_init__(self) -> None:
        names = (
            "candidate_authority_manifest", "ordered_hard_factors", "initial_residual",
            "hard_bound", "hard_threshold", "nominal_addendum", "total_bound",
            "coverage", "disposition", "verification_report",
        )
        _i0_instance(self, TypedPipelineBound, names, "TypedPipelineBound")
        _CandidateAuthorityManifest.to_dict(_i0_instance(self.candidate_authority_manifest, _CandidateAuthorityManifest, ("ordered_bindings", "full_runtime_manifest_sha256", "s0_runtime_manifest_sha256", "s0_authority_identity", "i0_activation_identity"), "bound candidate manifest"))
        if type(self.ordered_hard_factors) is not tuple or len(self.ordered_hard_factors) != 4:
            raise StrictContractError("bound must contain exactly four hard factors")
        for factor in self.ordered_hard_factors:
            TypedPipelineFactor.to_dict(_i0_instance(factor, TypedPipelineFactor, ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible"), "bound hard factor"))
        _i0_rational(self.initial_residual, "bound initial_residual", bits=_I0_INPUT_BITS)
        if self.hard_bound is not None:
            _i0_rational(self.hard_bound, "bound hard_bound", bits=_I0_INTERMEDIATE_BITS)
        _i0_rational(self.hard_threshold, "bound hard_threshold", bits=_I0_INPUT_BITS)
        if self.nominal_addendum is not None:
            NominalPipelineAddendum.to_dict(_i0_instance(self.nominal_addendum, NominalPipelineAddendum, ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible"), "bound nominal addendum"))
        if self.total_bound is not None:
            _TypedDiagnosticTotal.to_dict(_i0_instance(self.total_bound, _TypedDiagnosticTotal, ("value", "evidence_tier", "hard_eligible"), "bound total bound"))
        _PipelineCoverage.to_dict(_i0_instance(self.coverage, _PipelineCoverage, ("covered_count", "universe_count", "coverage_scope", "complete"), "bound coverage"))
        _i0_disposition(self.disposition, "bound disposition")
        _PipelineVerificationReport.to_dict(_i0_instance(self.verification_report, _PipelineVerificationReport, ("hard_factor_count", "hard_factor_order_sha256", "initial_term", "propagated_epsilon_terms", "recomputed_hard_bound", "recomputed_nominal_addendum", "recomputed_total_bound", "coverage_complete", "tier_firewall_verified", "domain_chain_verified", "norm_chain_verified", "authority_manifest_verified", "disposition_verified", "verification_disposition"), "bound verification report"))

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _I0_BOUND_SCHEMA,
            "candidate_authority_manifest": _CandidateAuthorityManifest.to_dict(self.candidate_authority_manifest),
            "ordered_hard_factors": [TypedPipelineFactor.to_dict(row) for row in self.ordered_hard_factors],
            "initial_residual": ExactRational.to_dict(self.initial_residual),
            "hard_bound": None if self.hard_bound is None else ExactRational.to_dict(self.hard_bound),
            "hard_threshold": ExactRational.to_dict(self.hard_threshold),
            "nominal_addendum": None if self.nominal_addendum is None else NominalPipelineAddendum.to_dict(self.nominal_addendum),
            "total_bound": None if self.total_bound is None else _TypedDiagnosticTotal.to_dict(self.total_bound),
            "coverage": _PipelineCoverage.to_dict(self.coverage),
            "disposition": self.disposition.value,
            "verification_report": _PipelineVerificationReport.to_dict(self.verification_report),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "TypedPipelineBound":
        if cls is not TypedPipelineBound:
            raise StrictContractError("polymorphic TypedPipelineBound parsing is forbidden")
        _i0_wire_preflight(value, "TypedPipelineBound")
        fields = (
            "schema_version", "candidate_authority_manifest", "ordered_hard_factors",
            "initial_residual", "hard_bound", "hard_threshold", "nominal_addendum",
            "total_bound", "coverage", "disposition", "verification_report",
        )
        obj = _i0_object(value, fields, "TypedPipelineBound")
        if obj["schema_version"] != _I0_BOUND_SCHEMA:
            raise StrictContractError("TypedPipelineBound schema mismatch")
        manifest = _CandidateAuthorityManifest.from_dict(obj["candidate_authority_manifest"])
        factors = tuple(TypedPipelineFactor.from_dict(row) for row in _i0_array(obj["ordered_hard_factors"], "bound hard factors", count=4))
        hard_bound = None if obj["hard_bound"] is None else _i0_rational_from_wire(obj["hard_bound"], "bound hard_bound", bits=_I0_INTERMEDIATE_BITS)
        nominal = None if obj["nominal_addendum"] is None else NominalPipelineAddendum.from_dict(obj["nominal_addendum"])
        total = None if obj["total_bound"] is None else _TypedDiagnosticTotal.from_dict(obj["total_bound"])
        result = cls(
            manifest, factors,
            _i0_rational_from_wire(obj["initial_residual"], "bound initial_residual", bits=_I0_INPUT_BITS),
            hard_bound,
            _i0_rational_from_wire(obj["hard_threshold"], "bound hard_threshold", bits=_I0_INPUT_BITS),
            nominal, total, _PipelineCoverage.from_dict(obj["coverage"]),
            _i0_disposition_wire(obj["disposition"], "bound disposition"),
            _PipelineVerificationReport.from_dict(obj["verification_report"]),
        )
        if TypedPipelineBound.to_dict(result) != obj:
            raise StrictContractError("TypedPipelineBound wire is not canonical")
        return verify_typed_pipeline_bound(bound=result, expected_candidate_authority_manifest=manifest)


def _i0_coverage_wire(covered: int, universe: int, scope: str, complete: bool) -> dict[str, Any]:
    return _PipelineCoverage(covered, universe, scope, complete).to_dict()


def _i0_complete_coverage() -> _PipelineCoverage:
    return _PipelineCoverage.from_dict(_i0_coverage_wire(4, 4, _I0_HARD_COVERAGE_SCOPE, True))


def _i0_incomplete_s0_coverage() -> _PipelineCoverage:
    return _PipelineCoverage.from_dict(_i0_coverage_wire(3, 4, _I0_S0_COVERAGE_SCOPE, False))


def _i0_nominal_coverage() -> _PipelineCoverage:
    return _PipelineCoverage.from_dict(_i0_coverage_wire(2, 3, _I0_NOMINAL_COVERAGE_SCOPE, False))


def _i0_fixed_nominal_addendum() -> NominalPipelineAddendum:
    return NominalPipelineAddendum(
        "ME0",
        _I0_DOMAINS[3],
        _I0_NOMINAL_CODOMAIN,
        _I0_NORM_ID,
        ExactRational(1),
        ExactRational(1, 10),
        PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY,
        ("ME0.nontrivial_orbit_windows_result",),
        _i0_nominal_coverage(),
        False,
    )


def _i0_expected_factor_wires(*, fail: bool = False, abstain: bool = False) -> list[dict[str, Any]]:
    """Private deterministic fixture aid; it is deliberately not exported."""
    coverages = [_i0_complete_coverage() for _ in range(4)]
    if abstain:
        coverages[3] = _i0_incomplete_s0_coverage()
    epsilons = (
        ExactRational(0),
        ExactRational(1, 4) if fail else ExactRational(1, 8),
        ExactRational(1, 4),
        ExactRational(1, 8),
    )
    Ls = (ExactRational(1), ExactRational(2), ExactRational(3, 2), ExactRational(1))
    tiers = (
        PipelineEvidenceTier.EXACT,
        PipelineEvidenceTier.EXACT_DECLARED_SYNTHETIC,
        PipelineEvidenceTier.CERTIFIED_SYNTHETIC,
        PipelineEvidenceTier.CERTIFIED_SYNTHETIC,
    )
    return [
        TypedPipelineFactor(
            _I0_STAGES[index], _I0_DOMAINS[index], _I0_DOMAINS[index + 1],
            _I0_NORM_ID, Ls[index], epsilons[index], tiers[index],
            _I0_FACTOR_BINDINGS[index], coverages[index], True,
        ).to_dict()
        for index in range(4)
    ]


def _i0_expected_nominal_wire() -> dict[str, Any]:
    return _i0_fixed_nominal_addendum().to_dict()


def _i0_detach_factor(value: TypedPipelineFactor) -> TypedPipelineFactor:
    _i0_instance(value, TypedPipelineFactor, ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible"), "hard factor")
    return TypedPipelineFactor.from_dict(TypedPipelineFactor.to_dict(value))


def _i0_detach_nominal(value: NominalPipelineAddendum) -> NominalPipelineAddendum:
    _i0_instance(value, NominalPipelineAddendum, ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible"), "nominal addendum")
    return NominalPipelineAddendum.from_dict(NominalPipelineAddendum.to_dict(value))


def _i0_validate_inputs(
    manifest: _CandidateAuthorityManifest,
    factors: tuple[TypedPipelineFactor, ...],
    initial_residual: ExactRational,
    hard_threshold: ExactRational,
    nominal: NominalPipelineAddendum,
) -> tuple[bool, bool]:
    _i0_manifest(manifest, "candidate authority manifest")
    if type(factors) is not tuple or len(factors) != 4:
        raise StrictContractError("ordered_hard_factors must be an exact four-factor tuple")
    for factor in factors:
        TypedPipelineFactor.to_dict(_i0_instance(factor, TypedPipelineFactor, ("stage_id", "domain_id", "codomain_id", "norm_id", "L", "epsilon", "evidence_tier", "authority_bindings", "coverage", "hard_eligible"), "hard factor"))
    _i0_rational(initial_residual, "initial_residual", bits=_I0_INPUT_BITS)
    _i0_rational(hard_threshold, "hard_threshold", bits=_I0_INPUT_BITS)
    if not _i0_eq_rational(initial_residual, 1, 16):
        raise StrictContractError("initial_residual must equal the frozen 1/16")
    if not _i0_eq_rational(hard_threshold, 3, 4):
        raise StrictContractError("hard_threshold must equal the frozen 3/4")

    expected_L = ((1, 1), (2, 1), (3, 2), (1, 1))
    expected_tiers = (
        PipelineEvidenceTier.EXACT,
        PipelineEvidenceTier.EXACT_DECLARED_SYNTHETIC,
        PipelineEvidenceTier.CERTIFIED_SYNTHETIC,
        PipelineEvidenceTier.CERTIFIED_SYNTHETIC,
    )
    expected_eps = ((0, 1), None, (1, 4), (1, 8))
    complete_wire = _i0_complete_coverage().to_dict()
    incomplete_wire = _i0_incomplete_s0_coverage().to_dict()
    abstain = False
    fail_variant = False
    for index, factor in enumerate(factors):
        if (
            factor.stage_id != _I0_STAGES[index]
            or factor.domain_id != _I0_DOMAINS[index]
            or factor.codomain_id != _I0_DOMAINS[index + 1]
            or factor.norm_id != _I0_NORM_ID
            or factor.evidence_tier is not expected_tiers[index]
            or factor.authority_bindings != _I0_FACTOR_BINDINGS[index]
            or factor.hard_eligible is not True
        ):
            raise StrictContractError(f"hard factor {_I0_STAGES[index]} contract mismatch")
        if not _i0_eq_rational(factor.L, *expected_L[index]):
            raise StrictContractError(f"hard factor {_I0_STAGES[index]} L mismatch")
        if index == 1:
            if _i0_eq_rational(factor.epsilon, 1, 8):
                fail_variant = False
            elif _i0_eq_rational(factor.epsilon, 1, 4):
                fail_variant = True
            else:
                raise StrictContractError("E1 epsilon must be exactly 1/8 or 1/4")
        elif not _i0_eq_rational(factor.epsilon, *expected_eps[index]):
            raise StrictContractError(f"hard factor {_I0_STAGES[index]} epsilon mismatch")
        coverage_wire = _PipelineCoverage.to_dict(factor.coverage)
        if index < 3:
            if coverage_wire != complete_wire:
                raise StrictContractError(f"hard factor {_I0_STAGES[index]} coverage mismatch")
        elif coverage_wire == incomplete_wire:
            abstain = True
        elif coverage_wire != complete_wire:
            raise StrictContractError("S0 coverage is neither frozen complete nor frozen incomplete")

    detached_nominal = _i0_detach_nominal(nominal)
    if detached_nominal.to_dict() != _i0_expected_nominal_wire():
        raise StrictContractError("nominal addendum contract mismatch or hard-channel promotion")

    binding_map = {row.binding_id: row for row in manifest.ordered_bindings}
    for ids in _I0_FACTOR_BINDINGS:
        for binding_id in ids:
            row = binding_map.get(binding_id)
            if row is None or row.hard_eligible is not True:
                raise StrictContractError("hard factor resolved to a missing or non-hard authority")
    nominal_row = binding_map.get("ME0.nontrivial_orbit_windows_result")
    if (
        nominal_row is None
        or nominal_row.evidence_tier is not PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY
        or nominal_row.hard_eligible is not False
    ):
        raise StrictContractError("nominal authority crossed the hard tier firewall")
    return abstain, fail_variant


def _i0_compute_arithmetic(
    factors: tuple[TypedPipelineFactor, ...],
    initial_residual: ExactRational,
    nominal: NominalPipelineAddendum,
) -> tuple[ExactRational, tuple[_PropagatedEpsilonTerm, ...], ExactRational, ExactRational, _TypedDiagnosticTotal]:
    product_all = ExactRational(1)
    for index, factor in enumerate(factors):
        product_all = _i0_mul(product_all, factor.L, f"initial L product {index}")
    initial_term = _i0_mul(product_all, initial_residual, "initial propagated term")
    terms: list[_PropagatedEpsilonTerm] = []
    hard_bound = initial_term
    for index, factor in enumerate(factors):
        downstream = ExactRational(1)
        for later in range(index + 1, len(factors)):
            downstream = _i0_mul(downstream, factors[later].L, f"{factor.stage_id} downstream L")
        contribution = _i0_mul(downstream, factor.epsilon, f"{factor.stage_id} propagated epsilon")
        terms.append(_PropagatedEpsilonTerm(factor.stage_id, downstream, factor.epsilon, contribution))
        hard_bound = _i0_add(hard_bound, contribution, f"hard bound after {factor.stage_id}")
    nominal_value = _i0_mul(nominal.L, nominal.epsilon, "nominal diagnostic addendum")
    total_value = _i0_add(hard_bound, nominal_value, "typed diagnostic total")
    total = _TypedDiagnosticTotal(total_value, PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY, False)
    return initial_term, tuple(terms), hard_bound, nominal_value, total


def _i0_build_bound(
    *,
    manifest: _CandidateAuthorityManifest,
    factors: tuple[TypedPipelineFactor, ...],
    initial_residual: ExactRational,
    hard_threshold: ExactRational,
    nominal: NominalPipelineAddendum,
) -> TypedPipelineBound:
    abstain, _fail_variant = _i0_validate_inputs(manifest, factors, initial_residual, hard_threshold, nominal)
    factor_digest = hashlib.sha256(
        canonical_contract_bytes([TypedPipelineFactor.to_dict(row) for row in factors])
    ).hexdigest().upper()
    if abstain:
        coverage = _PipelineCoverage.from_dict(_PipelineCoverage.to_dict(factors[3].coverage))
        report = _PipelineVerificationReport(
            4, factor_digest, None, (), None, None, None, False,
            True, True, True, True, True, _I0_VERIFICATION_DISPOSITION,
        )
        return TypedPipelineBound(
            manifest, factors, initial_residual, None, hard_threshold, None, None,
            coverage, PipelineDisposition.ABSTAIN_INCOMPLETE_COVERAGE, report,
        )

    initial_term, terms, hard_bound, nominal_value, total = _i0_compute_arithmetic(
        factors, initial_residual, nominal
    )
    disposition = (
        PipelineDisposition.PASS
        if _i0_le(hard_bound, hard_threshold, "hard threshold comparison")
        else PipelineDisposition.FAIL_HARD_BOUND_EXCEEDED
    )
    report = _PipelineVerificationReport(
        4, factor_digest, initial_term, terms, hard_bound, nominal_value, total,
        True, True, True, True, True, True, _I0_VERIFICATION_DISPOSITION,
    )
    return TypedPipelineBound(
        manifest, factors, initial_residual, hard_bound, hard_threshold, nominal,
        total, _i0_complete_coverage(), disposition, report,
    )


def construct_typed_pipeline_bound(
    *,
    candidate_authority_manifest: Any,
    ordered_hard_factors: Any,
    initial_residual: ExactRational,
    hard_threshold: ExactRational,
    nominal_addendum: NominalPipelineAddendum,
) -> TypedPipelineBound:
    manifest = _i0_manifest(candidate_authority_manifest, "candidate_authority_manifest")
    if type(ordered_hard_factors) is not tuple or len(ordered_hard_factors) != 4:
        raise StrictContractError("ordered_hard_factors must be an exact four-factor tuple")
    factors = tuple(_i0_detach_factor(row) for row in ordered_hard_factors)
    initial = _i0_rational(initial_residual, "initial_residual", bits=_I0_INPUT_BITS)
    threshold = _i0_rational(hard_threshold, "hard_threshold", bits=_I0_INPUT_BITS)
    nominal = _i0_detach_nominal(nominal_addendum)
    result = _i0_build_bound(
        manifest=manifest,
        factors=factors,
        initial_residual=ExactRational(initial.numerator, initial.denominator),
        hard_threshold=ExactRational(threshold.numerator, threshold.denominator),
        nominal=nominal,
    )
    _i0_wire_preflight(TypedPipelineBound.to_dict(result), "constructed TypedPipelineBound")
    return result


def verify_typed_pipeline_bound(
    *,
    bound: TypedPipelineBound,
    expected_candidate_authority_manifest: Any,
) -> TypedPipelineBound:
    _i0_instance(bound, TypedPipelineBound, ("candidate_authority_manifest", "ordered_hard_factors", "initial_residual", "hard_bound", "hard_threshold", "nominal_addendum", "total_bound", "coverage", "disposition", "verification_report"), "bound")
    supplied_wire = TypedPipelineBound.to_dict(bound)
    _i0_wire_preflight(supplied_wire, "TypedPipelineBound verification input")
    expected_manifest = _i0_manifest(expected_candidate_authority_manifest, "expected candidate authority manifest")
    if canonical_contract_bytes(_CandidateAuthorityManifest.to_dict(bound.candidate_authority_manifest)) != canonical_contract_bytes(_CandidateAuthorityManifest.to_dict(expected_manifest)):
        raise StrictContractError("bound candidate manifest differs from the expected authority")
    factors = tuple(_i0_detach_factor(row) for row in bound.ordered_hard_factors)
    nominal_input = (
        _i0_fixed_nominal_addendum()
        if bound.nominal_addendum is None
        else _i0_detach_nominal(bound.nominal_addendum)
    )
    expected = _i0_build_bound(
        manifest=expected_manifest,
        factors=factors,
        initial_residual=_i0_rational(bound.initial_residual, "bound initial_residual", bits=_I0_INPUT_BITS),
        hard_threshold=_i0_rational(bound.hard_threshold, "bound hard_threshold", bits=_I0_INPUT_BITS),
        nominal=nominal_input,
    )
    expected_wire = TypedPipelineBound.to_dict(expected)
    if canonical_contract_bytes(supplied_wire) != canonical_contract_bytes(expected_wire):
        raise StrictContractError("TypedPipelineBound disagrees with independent recomputation")
    return TypedPipelineBound(
        _CandidateAuthorityManifest.from_dict(_CandidateAuthorityManifest.to_dict(expected.candidate_authority_manifest)),
        tuple(TypedPipelineFactor.from_dict(TypedPipelineFactor.to_dict(row)) for row in expected.ordered_hard_factors),
        ExactRational(expected.initial_residual.numerator, expected.initial_residual.denominator),
        None if expected.hard_bound is None else ExactRational(expected.hard_bound.numerator, expected.hard_bound.denominator),
        ExactRational(expected.hard_threshold.numerator, expected.hard_threshold.denominator),
        None if expected.nominal_addendum is None else NominalPipelineAddendum.from_dict(expected.nominal_addendum.to_dict()),
        None if expected.total_bound is None else _TypedDiagnosticTotal.from_dict(expected.total_bound.to_dict()),
        _PipelineCoverage.from_dict(expected.coverage.to_dict()),
        expected.disposition,
        _PipelineVerificationReport.from_dict(expected.verification_report.to_dict()),
    )


__all__ = [
    "E2_AUTHORITY_COMMIT_SHA",
    "E2_AUTHORITY_TREE_SHA",
    "E2_AUTHORITY_DOCUMENT_PATH",
    "E2_AUTHORITY_DOCUMENT_BLOB_SHA",
    "E2_Q1_REPAIR_AUTHORITY_COMMIT_SHA",
    "E2_Q1_REPAIR_AUTHORITY_TREE_SHA",
    "E2_Q1_REPAIR_AUTHORITY_DOCUMENT_PATH",
    "E2_Q1_REPAIR_AUTHORITY_DOCUMENT_BLOB_SHA",
    "SourceTargetCoordinateIdentification",
    "EnvelopeRestrictionWitness",
    "LiftingUniformSafetyCertificate",
    "ResolvedMemorySplit",
    "CocycleCertificate",
    "ReturnMemoryBound",
    "identify_e2_source_target_coordinates",
    "build_e2_envelope_restriction",
    "certify_e2_lifting_uniform_safety",
    "resolve_e2_memory_split",
    "certify_e2_cocycle",
    "bound_e2_finite_return_memory",
    "PipelineEvidenceTier",
    "PipelineDisposition",
    "TypedPipelineFactor",
    "NominalPipelineAddendum",
    "TypedPipelineBound",
    "construct_typed_pipeline_bound",
    "verify_typed_pipeline_bound",
]
