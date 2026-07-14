"""Exact positive finite-fiber majorants on E0 quotient coordinates.

The module is deliberately development-only.  A certificate is hard only for
the complete displayed ``DECLARED_SYNTHETIC_FIXTURE`` rectangle retained by a
pair of exact E0 generators; it is not an admission path for event-derived,
observed, nominal, or production operators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from .contracts import (
    ExactRational,
    SYNTHETIC_EVIDENCE_SCOPE,
    StrictContractError,
    canonical_contract_bytes,
)
from .quotient_generator import (
    ExactFiniteFiberLaw,
    ExactQuotientCoordinateGenerator,
    PositiveFiberWeights,
    WeightedCompression,
    WeightedLifting,
    _derive_fiber_law_wire_from_frame,
    _derive_positive_weights_wire_from_frame,
    _fresh_fiber_frame,
    _rational_add,
    _rational_divide,
    _rational_multiply,
    make_weighted_compression,
    make_weighted_lifting,
)


DECLARED_SYNTHETIC_FIXTURE = "DECLARED_SYNTHETIC_FIXTURE"
FIBER_ENVELOPE_DISPOSITION = "CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED"

DECLARED_SYNTHETIC_TRANSFER_LAYER_SCHEMA = (
    "odlrq_declared_synthetic_transfer_layer_v1"
)
FIBER_COMPLETENESS_WITNESS_SCHEMA = "odlrq_fiber_completeness_witness_v1"
DOMAIN_MEMBERSHIP_WITNESS_SCHEMA = "odlrq_domain_membership_witness_v1"
FIBER_ENVELOPE_SCHEMA = "odlrq_fiber_envelope_v1"
FIBER_INCLUSION_WITNESS_SCHEMA = "odlrq_fiber_inclusion_witness_v1"

MAX_FIBER_MEMBERS = 128
MAX_FIBER_BLOCKS = 64
MAX_SPARSE_TRANSFER_CELLS = 4_096
MAX_FIBER_WORK_UNITS = 250_000

_LAYER_SEAL = object()
_COMPLETENESS_SEAL = object()
_MEMBERSHIP_SEAL = object()
_ENVELOPE_SEAL = object()
_INCLUSION_SEAL = object()


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _digest(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value != value.upper()
        or any(ch not in "0123456789ABCDEF" for ch in value)
    ):
        raise StrictContractError(f"{where} must be canonical uppercase SHA-256")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    return value


def _bounded_int(value: Any, where: str, upper: int) -> int:
    if type(value) is not int or value < 0 or value > upper:
        raise StrictContractError(
            f"{where} must be an exact nonnegative integer at most {upper}"
        )
    return value


def _exact_rational(value: Any, where: str) -> ExactRational:
    if type(value) is not ExactRational:
        raise StrictContractError(f"{where} must be ExactRational")
    if ExactRational.from_dict(value.to_dict()) != value:
        raise StrictContractError(f"{where} must be reduced canonical authority")
    return value


def _less(left: ExactRational, right: ExactRational) -> bool:
    _exact_rational(left, "left comparison operand")
    _exact_rational(right, "right comparison operand")
    return left.numerator * right.denominator < right.numerator * left.denominator


def _absolute(value: ExactRational) -> ExactRational:
    value = _exact_rational(value, "absolute-value operand")
    return ExactRational(abs(value.numerator), value.denominator)


def _frame_wire(frame: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "generator_sha256": frame["generator_sha256"],
        "reachable_domain_sha256": frame["reachable_domain_sha256"],
        "verified_partition_sha256": frame["verified_partition_sha256"],
        "canonical_block_order_sha256": frame["canonical_block_order_sha256"],
        "member_count": len(frame["members"]),
        "block_count": len(frame["blocks"]),
        "blocks": [
            {
                "block_index": block_index,
                "members": [
                    {
                        "member_id": member,
                        "member_sha256": frame["member_sha256"][member],
                    }
                    for member in members
                ],
            }
            for block_index, members in frame["blocks"]
        ],
    }


def _preflight_frame_wire(value: Any, where: str) -> dict[str, Any]:
    """Bound and type-check an embedded frame before touching E0 authority."""

    fields = {
        "generator_sha256",
        "reachable_domain_sha256",
        "verified_partition_sha256",
        "canonical_block_order_sha256",
        "member_count",
        "block_count",
        "blocks",
    }
    if type(value) is not dict or set(value) != fields:
        raise StrictContractError(f"{where} fields mismatch")
    for name in (
        "generator_sha256",
        "reachable_domain_sha256",
        "verified_partition_sha256",
        "canonical_block_order_sha256",
    ):
        _digest(value[name], f"{where} {name}")
    member_count = _bounded_int(
        value["member_count"], f"{where} member_count", MAX_FIBER_MEMBERS
    )
    block_count = _bounded_int(
        value["block_count"], f"{where} block_count", MAX_FIBER_BLOCKS
    )
    blocks = value["blocks"]
    if type(blocks) is not list or len(blocks) != block_count:
        raise StrictContractError(f"{where} block array count mismatch")
    seen: set[str] = set()
    observed_members = 0
    for expected_index, block in enumerate(blocks):
        if type(block) is not dict or set(block) != {"block_index", "members"}:
            raise StrictContractError(f"{where} block fields mismatch")
        block_index = _bounded_int(
            block["block_index"],
            f"{where} block index",
            MAX_FIBER_BLOCKS - 1,
        )
        if block_index != expected_index:
            raise StrictContractError(f"{where} block order is not canonical")
        members = block["members"]
        if type(members) is not list or len(members) > MAX_FIBER_MEMBERS:
            raise StrictContractError(f"{where} member array exceeds its cap")
        observed_members += len(members)
        if observed_members > MAX_FIBER_MEMBERS:
            raise StrictContractError(f"{where} total member count exceeds its cap")
        for member in members:
            if type(member) is not dict or set(member) != {
                "member_id",
                "member_sha256",
            }:
                raise StrictContractError(f"{where} member fields mismatch")
            member_id = _string(member["member_id"], f"{where} member_id")
            _digest(member["member_sha256"], f"{where} member_sha256")
            if member_id in seen:
                raise StrictContractError(f"{where} duplicates a member")
            seen.add(member_id)
    if observed_members != member_count:
        raise StrictContractError(f"{where} member count mismatch")
    return value


def _frame_from_validated_wire(value: Mapping[str, Any]) -> dict[str, Any]:
    blocks = tuple(
        (
            block["block_index"],
            tuple(member["member_id"] for member in block["members"]),
        )
        for block in value["blocks"]
    )
    members = tuple(member for _index, block_members in blocks for member in block_members)
    member_sha256 = {
        member["member_id"]: member["member_sha256"]
        for block in value["blocks"]
        for member in block["members"]
    }
    if len(members) != value["member_count"] or len(blocks) != value["block_count"]:
        raise StrictContractError("validated frame wire dimensions changed")
    return {
        "generator_sha256": value["generator_sha256"],
        "reachable_domain_sha256": value["reachable_domain_sha256"],
        "verified_partition_sha256": value["verified_partition_sha256"],
        "canonical_block_order_sha256": value["canonical_block_order_sha256"],
        "blocks": blocks,
        "members": members,
        "member_sha256": member_sha256,
    }


def _retained_frame_preflight(
    generator: ExactQuotientCoordinateGenerator,
) -> dict[str, Any]:
    """Cheap untrusted shape view; a valid path later runs generator.to_dict."""

    if type(generator) is not ExactQuotientCoordinateGenerator:
        raise StrictContractError("retained frame preflight requires an E0 generator")
    try:
        verified = generator._verified_source
        raw_blocks = verified.certificate.final_blocks
        raw_states = verified.admitted.snapshot.states
        if (
            len(raw_blocks) > MAX_FIBER_BLOCKS
            or len(raw_states) > MAX_FIBER_MEMBERS
        ):
            raise StrictContractError("retained E0 frame exceeds its preflight cap")
        observed_members = 0
        for block in raw_blocks:
            if len(block.member_state_ids) > MAX_FIBER_MEMBERS:
                raise StrictContractError("retained E0 block exceeds its member cap")
            observed_members += len(block.member_state_ids)
            if observed_members > MAX_FIBER_MEMBERS:
                raise StrictContractError("retained E0 members exceed their cap")
        blocks = tuple(
            (block.block_index, tuple(sorted(block.member_state_ids)))
            for block in raw_blocks
        )
        members = tuple(member for _index, block in blocks for member in block)
        member_sha256 = {
            state.state_id: _sha256(state.to_dict())
            for state in raw_states
        }
    except Exception as exc:
        raise StrictContractError("retained E0 frame preflight is unavailable") from exc
    if (
        tuple(index for index, _members in blocks) != tuple(range(len(blocks)))
        or len(members) != len(set(members))
        or set(members) != set(member_sha256)
        or len(members) > MAX_FIBER_MEMBERS
        or len(blocks) > MAX_FIBER_BLOCKS
    ):
        raise StrictContractError("retained E0 frame preflight is malformed")
    return {"blocks": blocks, "members": members, "member_sha256": member_sha256}


def _checked_rectangle(source_count: int, target_count: int) -> int:
    if (
        type(source_count) is not int
        or type(target_count) is not int
        or source_count < 1
        or target_count < 1
        or source_count > MAX_FIBER_MEMBERS
        or target_count > MAX_FIBER_MEMBERS
        or target_count > MAX_FIBER_WORK_UNITS // source_count
    ):
        raise StrictContractError("transfer rectangle exceeds the frozen preflight cap")
    return source_count * target_count


def _normalize_coefficients(
    coefficients: Any,
    source_frame: Mapping[str, Any],
    target_frame: Mapping[str, Any],
) -> tuple[tuple[str, str, ExactRational], ...]:
    if type(coefficients) is dict:
        if len(coefficients) > MAX_SPARSE_TRANSFER_CELLS:
            raise StrictContractError("sparse transfer-cell cap exceeded before parsing")
        raw = []
        for key, coefficient in coefficients.items():
            if type(key) is not tuple or len(key) != 2:
                raise StrictContractError("transfer coefficient key must be (target, source)")
            raw.append((key[0], key[1], coefficient))
    elif type(coefficients) in {tuple, list}:
        if len(coefficients) > MAX_SPARSE_TRANSFER_CELLS:
            raise StrictContractError("sparse transfer-cell cap exceeded before parsing")
        raw = list(coefficients)
    else:
        raise StrictContractError("transfer coefficients must be an exact object or tuple/list")

    source_position = {member: index for index, member in enumerate(source_frame["members"])}
    target_position = {member: index for index, member in enumerate(target_frame["members"])}
    seen: set[tuple[str, str]] = set()
    parsed: list[tuple[str, str, ExactRational]] = []
    for item in raw:
        if type(item) is not tuple or len(item) != 3:
            raise StrictContractError("transfer coefficient row must be an exact triple")
        target = _string(item[0], "transfer target member")
        source = _string(item[1], "transfer source member")
        coefficient = _exact_rational(item[2], "transfer coefficient")
        key = (target, source)
        if key in seen:
            raise StrictContractError("duplicate transfer coefficient cell")
        seen.add(key)
        if target not in target_position or source not in source_position:
            raise StrictContractError("transfer coefficient lies outside the exact rectangle")
        if coefficient.numerator == 0:
            raise StrictContractError("explicit zero transfer cells are forbidden")
        parsed.append((target, source, coefficient))
    parsed.sort(key=lambda row: (target_position[row[0]], source_position[row[1]]))
    return tuple(parsed)


def _derive_layer_wire(
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    coefficients: tuple[tuple[str, str, ExactRational], ...],
) -> dict[str, Any]:
    source_frame = _fresh_fiber_frame(source_generator)
    target_frame = _fresh_fiber_frame(target_generator)
    return _derive_layer_wire_from_frames(
        source_frame, target_frame, coefficients
    )


def _derive_layer_wire_from_frames(
    source_frame: Mapping[str, Any],
    target_frame: Mapping[str, Any],
    coefficients: tuple[tuple[str, str, ExactRational], ...],
) -> dict[str, Any]:
    if len(source_frame["blocks"]) > MAX_FIBER_BLOCKS or len(target_frame["blocks"]) > MAX_FIBER_BLOCKS:
        raise StrictContractError("transfer block cap exceeded")
    universe_count = _checked_rectangle(
        len(source_frame["members"]), len(target_frame["members"])
    )
    canonical = _normalize_coefficients(coefficients, source_frame, target_frame)
    # This complete ordered universe makes an absent sparse cell exact zero.
    universe = [
        {"target_member_id": target, "source_member_id": source}
        for target in target_frame["members"]
        for source in source_frame["members"]
    ]
    if len(universe) != universe_count:
        raise StrictContractError("transfer rectangle materialization changed dimensions")
    rows = [
        {
            "target_member_id": target,
            "target_member_sha256": target_frame["member_sha256"][target],
            "source_member_id": source,
            "source_member_sha256": source_frame["member_sha256"][source],
            "coefficient": coefficient.to_dict(),
        }
        for target, source, coefficient in canonical
    ]
    return {
        "schema_version": DECLARED_SYNTHETIC_TRANSFER_LAYER_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "coefficient_authority": DECLARED_SYNTHETIC_FIXTURE,
        "basis_convention": "target_row_source_column_v1",
        "source_frame": _frame_wire(source_frame),
        "target_frame": _frame_wire(target_frame),
        "source_generator_sha256": source_frame["generator_sha256"],
        "target_generator_sha256": target_frame["generator_sha256"],
        "rectangular_key_universe_count": universe_count,
        "rectangular_key_universe_sha256": _sha256(universe),
        "sparse_cell_count": len(rows),
        "coefficient_table_sha256": _sha256(rows),
        "coefficients": rows,
    }


@dataclass(frozen=True, init=False)
class DeclaredSyntheticTransferLayer:
    _source_generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _target_generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _coefficients: tuple[tuple[str, str, ExactRational], ...] = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("declared synthetic transfer layer has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not DeclaredSyntheticTransferLayer:
            raise StrictContractError("DeclaredSyntheticTransferLayer subclasses are forbidden")
        if self._construction_seal is not _LAYER_SEAL:
            raise StrictContractError("transfer layer requires the declared synthetic gate")
        _digest(self._source_seal_sha256, "transfer layer source seal")

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        source_generator: ExactQuotientCoordinateGenerator,
        target_generator: ExactQuotientCoordinateGenerator,
    ) -> "DeclaredSyntheticTransferLayer":
        if cls is not DeclaredSyntheticTransferLayer or type(value) is not dict:
            raise StrictContractError("strict transfer-layer parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "coefficient_authority",
            "basis_convention", "source_frame", "target_frame",
            "source_generator_sha256", "target_generator_sha256",
            "rectangular_key_universe_count", "rectangular_key_universe_sha256",
            "sparse_cell_count", "coefficient_table_sha256", "coefficients",
        } or value["schema_version"] != DECLARED_SYNTHETIC_TRANSFER_LAYER_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE or value["coefficient_authority"] != DECLARED_SYNTHETIC_FIXTURE or value["basis_convention"] != "target_row_source_column_v1":
            raise StrictContractError("transfer-layer outer fields/schema/authority mismatch")
        source_frame_wire = _preflight_frame_wire(
            value["source_frame"], "transfer source frame"
        )
        target_frame_wire = _preflight_frame_wire(
            value["target_frame"], "transfer target frame"
        )
        _digest(value["source_generator_sha256"], "transfer source generator SHA")
        _digest(value["target_generator_sha256"], "transfer target generator SHA")
        _digest(
            value["rectangular_key_universe_sha256"],
            "transfer rectangular universe SHA",
        )
        _digest(value["coefficient_table_sha256"], "transfer coefficient table SHA")
        universe_count = _bounded_int(
            value["rectangular_key_universe_count"],
            "transfer rectangular universe count",
            MAX_FIBER_MEMBERS * MAX_FIBER_MEMBERS,
        )
        sparse_count = _bounded_int(
            value["sparse_cell_count"],
            "transfer sparse cell count",
            MAX_SPARSE_TRANSFER_CELLS,
        )
        if universe_count != _checked_rectangle(
            source_frame_wire["member_count"], target_frame_wire["member_count"]
        ):
            raise StrictContractError("transfer rectangular universe count changed")
        raw_rows = value.get("coefficients")
        if type(raw_rows) is not list:
            raise StrictContractError("transfer coefficients must be an exact array")
        if len(raw_rows) > MAX_SPARSE_TRANSFER_CELLS:
            raise StrictContractError("sparse transfer-cell cap exceeded before parsing")
        if len(raw_rows) != sparse_count:
            raise StrictContractError("sparse transfer-cell count changed")
        coefficients = []
        for row in raw_rows:
            if type(row) is not dict or set(row) != {
                "target_member_id", "target_member_sha256", "source_member_id",
                "source_member_sha256", "coefficient",
            }:
                raise StrictContractError("transfer coefficient wire row fields mismatch")
            target_member_id = _string(
                row["target_member_id"], "transfer target member"
            )
            source_member_id = _string(
                row["source_member_id"], "transfer source member"
            )
            _digest(row["target_member_sha256"], "transfer target member SHA")
            _digest(row["source_member_sha256"], "transfer source member SHA")
            coefficients.append(
                (
                    target_member_id,
                    source_member_id,
                    ExactRational.from_dict(row["coefficient"]),
                )
            )
        source_frame = _fresh_fiber_frame(source_generator)
        target_frame = _fresh_fiber_frame(target_generator)
        if source_frame["reachable_domain_sha256"] == target_frame["reachable_domain_sha256"]:
            raise StrictContractError("transfer layer requires distinct exact domains")
        canonical = _normalize_coefficients(
            tuple(coefficients), source_frame, target_frame
        )
        expected_wire = _derive_layer_wire_from_frames(
            source_frame, target_frame, canonical
        )
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("transfer-layer wire disagrees with retained authority")
        return _construct_declared_synthetic_transfer_layer(
            source_generator, target_generator, canonical, expected_wire
        )

    @property
    def layer_sha256(self) -> str:
        return _sha256(self.to_dict())

    def coefficient_for(self, target_member_id: str, source_member_id: str) -> ExactRational:
        target = _string(target_member_id, "transfer target member")
        source = _string(source_member_id, "transfer source member")
        self.to_dict()
        source_frame = _fresh_fiber_frame(self._source_generator)
        target_frame = _fresh_fiber_frame(self._target_generator)
        if source not in source_frame["members"] or target not in target_frame["members"]:
            raise StrictContractError("transfer lookup is outside the exact rectangle")
        for row_target, row_source, coefficient in self._coefficients:
            if row_target == target and row_source == source:
                return coefficient
        return ExactRational(0)

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _LAYER_SEAL:
            raise StrictContractError("transfer-layer construction seal changed")
        wire = _derive_layer_wire(
            self._source_generator, self._target_generator, self._coefficients
        )
        if _sha256(
            {
                "source": wire["source_generator_sha256"],
                "target": wire["target_generator_sha256"],
                "universe": wire["rectangular_key_universe_sha256"],
                "coefficients": wire["coefficient_table_sha256"],
            }
        ) != _digest(self._source_seal_sha256, "transfer layer source seal"):
            raise StrictContractError("transfer-layer retained authority changed")
        return wire


def declare_synthetic_transfer_layer(
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    coefficients: Any,
) -> DeclaredSyntheticTransferLayer:
    if type(source_generator) is not ExactQuotientCoordinateGenerator or type(target_generator) is not ExactQuotientCoordinateGenerator:
        raise StrictContractError("transfer layer requires exact E0 source and target generators")
    if type(coefficients) not in {dict, tuple, list}:
        raise StrictContractError(
            "transfer coefficients must be an exact object or tuple/list"
        )
    if len(coefficients) > MAX_SPARSE_TRANSFER_CELLS:
        raise StrictContractError("sparse transfer-cell cap exceeded before authority")
    if source_generator is target_generator:
        raise StrictContractError(
            "transfer layer requires distinct source and target exact domains"
        )
    source_frame = _fresh_fiber_frame(source_generator)
    target_frame = _fresh_fiber_frame(target_generator)
    if (
        source_frame["reachable_domain_sha256"]
        == target_frame["reachable_domain_sha256"]
    ):
        raise StrictContractError(
            "transfer layer requires distinct source and target exact domains"
        )
    _checked_rectangle(len(source_frame["members"]), len(target_frame["members"]))
    canonical = _normalize_coefficients(coefficients, source_frame, target_frame)
    wire = _derive_layer_wire_from_frames(source_frame, target_frame, canonical)
    return _construct_declared_synthetic_transfer_layer(
        source_generator, target_generator, canonical, wire
    )


def _construct_declared_synthetic_transfer_layer(
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    canonical: tuple[tuple[str, str, ExactRational], ...],
    wire: Mapping[str, Any],
) -> DeclaredSyntheticTransferLayer:
    result = object.__new__(DeclaredSyntheticTransferLayer)
    object.__setattr__(result, "_source_generator", source_generator)
    object.__setattr__(result, "_target_generator", target_generator)
    object.__setattr__(result, "_coefficients", canonical)
    object.__setattr__(
        result,
        "_source_seal_sha256",
        _sha256(
            {
                "source": wire["source_generator_sha256"],
                "target": wire["target_generator_sha256"],
                "universe": wire["rectangular_key_universe_sha256"],
                "coefficients": wire["coefficient_table_sha256"],
            }
        ),
    )
    object.__setattr__(result, "_construction_seal", _LAYER_SEAL)
    result.__post_init__()
    return result


def _role_frame(layer: DeclaredSyntheticTransferLayer, role: str) -> dict[str, Any]:
    if type(layer) is not DeclaredSyntheticTransferLayer:
        raise StrictContractError("fiber witness requires a declared synthetic transfer layer")
    layer.to_dict()
    if role == "source":
        return _fresh_fiber_frame(layer._source_generator)
    if role == "target":
        return _fresh_fiber_frame(layer._target_generator)
    raise StrictContractError("fiber witness role must be 'source' or 'target'")


@dataclass(frozen=True, init=False)
class FiberCompletenessWitness:
    _layer: DeclaredSyntheticTransferLayer = field(repr=False)
    _role: str = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("fiber completeness witness has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not FiberCompletenessWitness or self._construction_seal is not _COMPLETENESS_SEAL:
            raise StrictContractError("fiber completeness witness requires independent verification")
        _digest(self._source_seal_sha256, "fiber completeness source seal")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], layer: DeclaredSyntheticTransferLayer) -> "FiberCompletenessWitness":
        if cls is not FiberCompletenessWitness or type(value) is not dict:
            raise StrictContractError("strict FiberCompletenessWitness parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "layer_sha256", "role",
            "generator_sha256", "reachable_domain_sha256",
            "verified_partition_sha256", "member_count", "block_count",
            "complete_member_universe_sha256", "frame",
        } or value["schema_version"] != FIBER_COMPLETENESS_WITNESS_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE:
            raise StrictContractError("FiberCompletenessWitness outer fields/schema mismatch")
        _preflight_frame_wire(value["frame"], "fiber completeness frame")
        for name in (
            "layer_sha256",
            "generator_sha256",
            "reachable_domain_sha256",
            "verified_partition_sha256",
            "complete_member_universe_sha256",
        ):
            _digest(value[name], f"fiber completeness {name}")
        _bounded_int(
            value["member_count"],
            "fiber completeness member count",
            MAX_FIBER_MEMBERS,
        )
        _bounded_int(
            value["block_count"],
            "fiber completeness block count",
            MAX_FIBER_BLOCKS,
        )
        role = _string(value.get("role"), "fiber completeness role")
        if type(layer) is not DeclaredSyntheticTransferLayer:
            raise StrictContractError("fiber completeness parser layer type changed")
        layer_wire = layer.to_dict()
        if role == "source":
            frame = _frame_from_validated_wire(layer_wire["source_frame"])
        elif role == "target":
            frame = _frame_from_validated_wire(layer_wire["target_frame"])
        else:
            raise StrictContractError("fiber completeness role is invalid")
        expected_wire = _completeness_payload(layer_wire, frame, role)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("fiber completeness wire disagrees with authority")
        return _construct_fiber_completeness(layer, role, expected_wire)

    @property
    def witness_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _COMPLETENESS_SEAL:
            raise StrictContractError("fiber completeness construction seal changed")
        layer_wire = self._layer.to_dict()
        if self._role == "source":
            frame = _frame_from_validated_wire(layer_wire["source_frame"])
        elif self._role == "target":
            frame = _frame_from_validated_wire(layer_wire["target_frame"])
        else:
            raise StrictContractError("fiber completeness role changed")
        return _completeness_wire_from_validated(
            self, layer_wire, frame
        )


def _completeness_wire_from_validated(
    witness: FiberCompletenessWitness,
    layer_wire: Mapping[str, Any],
    frame: Mapping[str, Any],
) -> dict[str, Any]:
        if (
            type(witness) is not FiberCompletenessWitness
            or witness._construction_seal is not _COMPLETENESS_SEAL
            or witness._role not in {"source", "target"}
        ):
            raise StrictContractError("fiber completeness capability seal changed")
        payload = _completeness_payload(layer_wire, frame, witness._role)
        if _sha256({"layer": payload["layer_sha256"], "role": witness._role, "frame": payload["frame"]}) != _digest(
            witness._source_seal_sha256, "fiber completeness source seal"
        ):
            raise StrictContractError("fiber completeness retained authority changed")
        return payload


def _completeness_payload(
    layer_wire: Mapping[str, Any], frame: Mapping[str, Any], role: str
) -> dict[str, Any]:
        return {
            "schema_version": FIBER_COMPLETENESS_WITNESS_SCHEMA,
            "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
            "layer_sha256": _sha256(layer_wire),
            "role": role,
            "generator_sha256": frame["generator_sha256"],
            "reachable_domain_sha256": frame["reachable_domain_sha256"],
            "verified_partition_sha256": frame["verified_partition_sha256"],
            "member_count": len(frame["members"]),
            "block_count": len(frame["blocks"]),
            "complete_member_universe_sha256": _sha256(
                [
                    {"member_id": member, "member_sha256": frame["member_sha256"][member]}
                    for member in frame["members"]
                ]
            ),
            "frame": _frame_wire(frame),
        }


def certify_fiber_completeness(
    layer: DeclaredSyntheticTransferLayer, role: str
) -> FiberCompletenessWitness:
    role = _string(role, "fiber completeness role")
    if type(layer) is not DeclaredSyntheticTransferLayer:
        raise StrictContractError("fiber completeness requires a declared layer")
    layer_wire = layer.to_dict()
    if role == "source":
        frame = _frame_from_validated_wire(layer_wire["source_frame"])
    elif role == "target":
        frame = _frame_from_validated_wire(layer_wire["target_frame"])
    else:
        raise StrictContractError("fiber witness role must be 'source' or 'target'")
    wire = _completeness_payload(layer_wire, frame, role)
    return _construct_fiber_completeness(layer, role, wire)


def _construct_fiber_completeness(
    layer: DeclaredSyntheticTransferLayer,
    role: str,
    wire: Mapping[str, Any],
) -> FiberCompletenessWitness:
    result = object.__new__(FiberCompletenessWitness)
    object.__setattr__(result, "_layer", layer)
    object.__setattr__(result, "_role", role)
    object.__setattr__(
        result,
        "_source_seal_sha256",
        _sha256({"layer": wire["layer_sha256"], "role": role, "frame": wire["frame"]}),
    )
    object.__setattr__(result, "_construction_seal", _COMPLETENESS_SEAL)
    result.__post_init__()
    return result


@dataclass(frozen=True, init=False)
class DomainMembershipWitness:
    _completeness: FiberCompletenessWitness = field(repr=False)
    _member_id: str = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("domain membership witness has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not DomainMembershipWitness or self._construction_seal is not _MEMBERSHIP_SEAL:
            raise StrictContractError("domain membership witness requires exact membership verification")
        _digest(self._source_seal_sha256, "domain membership source seal")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], completeness: FiberCompletenessWitness) -> "DomainMembershipWitness":
        if cls is not DomainMembershipWitness or type(value) is not dict:
            raise StrictContractError("strict DomainMembershipWitness parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "completeness_witness_sha256",
            "role", "member_id", "member_sha256", "block_index",
        } or value["schema_version"] != DOMAIN_MEMBERSHIP_WITNESS_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE:
            raise StrictContractError("DomainMembershipWitness outer fields/schema mismatch")
        if type(completeness) is not FiberCompletenessWitness:
            raise StrictContractError("domain membership completeness authority is invalid")
        _digest(
            value["completeness_witness_sha256"],
            "domain membership completeness SHA",
        )
        role = _string(value["role"], "domain membership role")
        if role not in {"source", "target"}:
            raise StrictContractError("domain membership role is invalid")
        _digest(value["member_sha256"], "domain membership member SHA")
        _bounded_int(
            value["block_index"],
            "domain membership block index",
            MAX_FIBER_BLOCKS - 1,
        )
        member = _string(value.get("member_id"), "domain membership member_id")
        expected_wire = _derive_membership_wire(completeness, member)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("domain membership wire disagrees with authority")
        return _construct_domain_membership(completeness, member, expected_wire)

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _MEMBERSHIP_SEAL:
            raise StrictContractError("domain membership construction seal changed")
        wire = _derive_membership_wire(self._completeness, self._member_id)
        if _sha256(wire) != _digest(
            self._source_seal_sha256, "domain membership source seal"
        ):
            raise StrictContractError("domain membership retained authority changed")
        return wire


def _derive_membership_wire(
    completeness: FiberCompletenessWitness, member_id: str
) -> dict[str, Any]:
        if type(completeness) is not FiberCompletenessWitness:
            raise StrictContractError("domain membership completeness type changed")
        member_id = _string(member_id, "domain membership member_id")
        completeness_wire = completeness.to_dict()
        frame = _frame_from_validated_wire(completeness_wire["frame"])
        if member_id not in frame["members"]:
            raise StrictContractError("retained member is outside the exact domain")
        block_index = next(
            index for index, members in frame["blocks"] if member_id in members
        )
        return {
            "schema_version": DOMAIN_MEMBERSHIP_WITNESS_SCHEMA,
            "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
            "completeness_witness_sha256": _sha256(completeness_wire),
            "role": completeness._role,
            "member_id": member_id,
            "member_sha256": frame["member_sha256"][member_id],
            "block_index": block_index,
        }


def witness_domain_membership(
    completeness: FiberCompletenessWitness, member_id: Any
) -> DomainMembershipWitness:
    if type(completeness) is not FiberCompletenessWitness:
        raise StrictContractError("domain membership requires FiberCompletenessWitness")
    member = _string(member_id, "domain member_id")
    wire = _derive_membership_wire(completeness, member)
    return _construct_domain_membership(completeness, member, wire)


def _construct_domain_membership(
    completeness: FiberCompletenessWitness,
    member: str,
    wire: Mapping[str, Any],
) -> DomainMembershipWitness:
    result = object.__new__(DomainMembershipWitness)
    object.__setattr__(result, "_completeness", completeness)
    object.__setattr__(result, "_member_id", member)
    object.__setattr__(result, "_source_seal_sha256", _sha256(wire))
    object.__setattr__(result, "_construction_seal", _MEMBERSHIP_SEAL)
    result.__post_init__()
    return result


def _check_envelope_authorities(
    layer: DeclaredSyntheticTransferLayer,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    *,
    _frame_cache: list[
        tuple[ExactQuotientCoordinateGenerator, dict[str, Any]]
    ] | None = None,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
]:
    if type(layer) is not DeclaredSyntheticTransferLayer:
        raise StrictContractError("fiber envelope requires a declared synthetic layer")
    for value, expected, label in (
        (source_weights, PositiveFiberWeights, "source weights"),
        (target_weights, PositiveFiberWeights, "target weights"),
        (source_law, ExactFiniteFiberLaw, "source law"),
        (source_completeness, FiberCompletenessWitness, "source completeness"),
        (target_completeness, FiberCompletenessWitness, "target completeness"),
    ):
        if type(value) is not expected:
            raise StrictContractError(f"fiber envelope {label} has the wrong tier/type")
    # Reject role/object contradictions before any proportional E0 rederivation.
    # Structurally equivalent clone generators remain admissible and are still
    # checked by digest below; only the known opposite endpoint is rejected.
    if source_completeness._layer is not layer or source_completeness._role != "source":
        raise StrictContractError("source completeness witness is not layer-bound")
    if target_completeness._layer is not layer or target_completeness._role != "target":
        raise StrictContractError("target completeness witness is not layer-bound")
    if (
        source_weights._generator is layer._target_generator
        or source_law._generator is layer._target_generator
        or target_weights._generator is layer._source_generator
    ):
        raise StrictContractError("fiber envelope authority is bound to the opposite endpoint")
    # A single validation transaction rederives each distinct E0 generator at
    # most once.  Every nested capability is still checked against its own
    # frozen full-wire seal; only duplicate E0 partition work is shared.
    frames: list[tuple[ExactQuotientCoordinateGenerator, dict[str, Any]]] = (
        [] if _frame_cache is None else _frame_cache
    )

    def frame_for(generator: ExactQuotientCoordinateGenerator) -> dict[str, Any]:
        for retained_generator, retained_frame in frames:
            if generator is retained_generator:
                return retained_frame
        fresh = _fresh_fiber_frame(generator)
        frames.append((generator, fresh))
        return fresh

    source_frame = frame_for(layer._source_generator)
    target_frame = frame_for(layer._target_generator)

    layer.__post_init__()
    layer_wire = _derive_layer_wire_from_frames(
        source_frame, target_frame, layer._coefficients
    )
    if _sha256(
        {
            "source": layer_wire["source_generator_sha256"],
            "target": layer_wire["target_generator_sha256"],
            "universe": layer_wire["rectangular_key_universe_sha256"],
            "coefficients": layer_wire["coefficient_table_sha256"],
        }
    ) != _digest(layer._source_seal_sha256, "transfer layer source seal"):
        raise StrictContractError("transfer-layer retained authority changed")

    source_weights.__post_init__()
    source_weights_wire = _derive_positive_weights_wire_from_frame(
        frame_for(source_weights._generator), source_weights._values
    )
    if _sha256(source_weights_wire) != _digest(
        source_weights._value_seal_sha256, "source weight value seal"
    ):
        raise StrictContractError("source weight retained authority changed")
    target_weights.__post_init__()
    target_weights_wire = _derive_positive_weights_wire_from_frame(
        frame_for(target_weights._generator), target_weights._values
    )
    if _sha256(target_weights_wire) != _digest(
        target_weights._value_seal_sha256, "target weight value seal"
    ):
        raise StrictContractError("target weight retained authority changed")
    source_law.__post_init__()
    source_law_wire = _derive_fiber_law_wire_from_frame(
        frame_for(source_law._generator), source_law._probabilities
    )
    if _sha256(source_law_wire) != _digest(
        source_law._value_seal_sha256, "source law value seal"
    ):
        raise StrictContractError("source law retained authority changed")
    if source_weights_wire["generator_sha256"] != source_frame["generator_sha256"] or source_law_wire["generator_sha256"] != source_frame["generator_sha256"]:
        raise StrictContractError("source weight/law frame does not match transfer source")
    if target_weights_wire["generator_sha256"] != target_frame["generator_sha256"]:
        raise StrictContractError("target weight frame does not match transfer target")
    source_completeness_wire = _completeness_wire_from_validated(
        source_completeness, layer_wire, source_frame
    )
    target_completeness_wire = _completeness_wire_from_validated(
        target_completeness, layer_wire, target_frame
    )
    return (
        source_frame, target_frame, layer_wire, source_weights_wire,
        target_weights_wire, source_law_wire, source_completeness_wire,
        target_completeness_wire,
    )


def _derive_envelope_wire(
    layer: DeclaredSyntheticTransferLayer,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    *,
    _validated_context: tuple[
        dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
        dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    ] | None = None,
) -> dict[str, Any]:
    (
        source_frame, target_frame, layer_wire, source_weights_wire,
        target_weights_wire, source_law_wire, source_completeness_wire,
        target_completeness_wire,
    ) = (
        _check_envelope_authorities(
            layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness,
        )
        if _validated_context is None
        else _validated_context
    )
    rectangle_work = _checked_rectangle(
        len(source_frame["members"]), len(target_frame["members"])
    )
    candidate_count = len(target_frame["blocks"]) * len(source_frame["members"])
    if candidate_count > MAX_FIBER_WORK_UNITS:
        raise StrictContractError("fiber candidate-load cap exceeded before allocation")
    coefficient = {
        (target, source): value
        for target, source, value in layer._coefficients
    }
    source_weight = {
        member: source_weights._values[index]
        for index, member in enumerate(source_frame["members"])
    }
    target_weight = {
        member: target_weights._values[index]
        for index, member in enumerate(target_frame["members"])
    }
    probability = {
        member: source_law._probabilities[index]
        for index, member in enumerate(source_frame["members"])
    }
    cells: list[dict[str, Any]] = []
    observed_candidates = 0
    observed_work = 0
    for target_block_index, target_members in target_frame["blocks"]:
        for source_block_index, source_members_unsorted in source_frame["blocks"]:
            source_members = tuple(sorted(source_members_unsorted))
            candidate_rows: list[dict[str, Any]] = []
            maximum: ExactRational | None = None
            maximizer: str | None = None
            compressed = ExactRational(0)
            for source in source_members:
                load = ExactRational(0)
                signed_target_sum = ExactRational(0)
                for target in target_members:
                    value = coefficient.get((target, source), ExactRational(0))
                    load = _rational_add(
                        load,
                        _rational_divide(
                            _rational_multiply(_absolute(value), target_weight[target]),
                            source_weight[source],
                        ),
                    )
                    signed_target_sum = _rational_add(
                        signed_target_sum,
                        _rational_multiply(value, target_weight[target]),
                    )
                compressed = _rational_add(
                    compressed,
                    _rational_multiply(
                        probability[source],
                        _rational_divide(signed_target_sum, source_weight[source]),
                    ),
                )
                candidate_rows.append(
                    {
                        "source_member_id": source,
                        "source_member_sha256": source_frame["member_sha256"][source],
                        "load": load.to_dict(),
                        "target_member_count": len(target_members),
                        "work_count": len(target_members),
                    }
                )
                if maximum is None or _less(maximum, load):
                    maximum = load
                    maximizer = source
            if maximum is None or maximizer is None:
                raise StrictContractError("fiber envelope encountered an empty source block")
            if _less(maximum, _absolute(compressed)):
                raise StrictContractError("fiber majorant is below the compressed coefficient")
            cell_work = len(source_members) * len(target_members)
            observed_candidates += len(source_members)
            observed_work += cell_work
            cells.append(
                {
                    "target_block_index": target_block_index,
                    "source_block_index": source_block_index,
                    "candidate_loads": candidate_rows,
                    "maximizing_source_member_id": maximizer,
                    "maximizing_source_member_sha256": source_frame["member_sha256"][maximizer],
                    "majorant": maximum.to_dict(),
                    "compressed_coefficient": compressed.to_dict(),
                    "absolute_compressed_coefficient": _absolute(compressed).to_dict(),
                    "member_count": len(source_members),
                    "work_count": cell_work,
                }
            )
    expected_pair_count = len(source_frame["blocks"]) * len(target_frame["blocks"])
    if (
        len(cells) != expected_pair_count
        or observed_candidates != candidate_count
        or observed_work != rectangle_work
    ):
        raise StrictContractError("fiber envelope certificate coverage is incomplete")
    return {
        "schema_version": FIBER_ENVELOPE_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "hard_scope": "complete_declared_finite_synthetic_rectangle_only",
        "coefficient_authority": DECLARED_SYNTHETIC_FIXTURE,
        "basis_convention": "target_row_source_column_v1",
        "layer_sha256": _sha256(layer_wire),
        "source_generator_sha256": source_frame["generator_sha256"],
        "target_generator_sha256": target_frame["generator_sha256"],
        "source_weights_sha256": _sha256(source_weights_wire),
        "target_weights_sha256": _sha256(target_weights_wire),
        "source_law_sha256": _sha256(source_law_wire),
        "source_completeness_sha256": _sha256(source_completeness_wire),
        "target_completeness_sha256": _sha256(target_completeness_wire),
        "source_block_count": len(source_frame["blocks"]),
        "target_block_count": len(target_frame["blocks"]),
        "block_pair_count": expected_pair_count,
        "candidate_load_count": candidate_count,
        "work_count": rectangle_work,
        "cells": cells,
        "verification_disposition": FIBER_ENVELOPE_DISPOSITION,
    }


def _fraction(value: ExactRational) -> Fraction:
    value = _exact_rational(value, "independent verifier rational")
    return Fraction(value.numerator, value.denominator)


def _fraction_wire(value: Fraction) -> dict[str, Any]:
    return ExactRational(value.numerator, value.denominator).to_dict()


def _independently_verify_envelope_wire(
    value: Mapping[str, Any],
    layer: DeclaredSyntheticTransferLayer,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    *,
    _validated_context: tuple[
        dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
        dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any],
    ] | None = None,
) -> None:
    """Recompute M and K with stdlib Fraction, not the construction arithmetic."""

    (
        source_frame, target_frame, _layer_wire, _source_weights_wire,
        _target_weights_wire, _source_law_wire, _source_completeness_wire,
        _target_completeness_wire,
    ) = (
        _check_envelope_authorities(
            layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness,
        )
        if _validated_context is None
        else _validated_context
    )
    coefficients = {
        (target, source): _fraction(coefficient)
        for target, source, coefficient in layer._coefficients
    }
    source_weight = {
        member: _fraction(source_weights._values[index])
        for index, member in enumerate(source_frame["members"])
    }
    target_weight = {
        member: _fraction(target_weights._values[index])
        for index, member in enumerate(target_frame["members"])
    }
    probability = {
        member: _fraction(source_law._probabilities[index])
        for index, member in enumerate(source_frame["members"])
    }
    expected_cells: list[dict[str, Any]] = []
    for target_block_index, target_members in target_frame["blocks"]:
        for source_block_index, raw_source_members in source_frame["blocks"]:
            source_members = tuple(sorted(raw_source_members))
            loads: list[tuple[str, Fraction]] = []
            compressed = Fraction(0)
            candidates = []
            for source in source_members:
                load = sum(
                    abs(coefficients.get((target, source), Fraction(0)))
                    * target_weight[target]
                    / source_weight[source]
                    for target in target_members
                )
                signed = sum(
                    coefficients.get((target, source), Fraction(0))
                    * target_weight[target]
                    for target in target_members
                )
                compressed += probability[source] * signed / source_weight[source]
                loads.append((source, load))
                candidates.append(
                    {
                        "source_member_id": source,
                        "source_member_sha256": source_frame["member_sha256"][source],
                        "load": _fraction_wire(load),
                        "target_member_count": len(target_members),
                        "work_count": len(target_members),
                    }
                )
            maximum = max(load for _source, load in loads)
            maximizer = next(source for source, load in loads if load == maximum)
            if abs(compressed) > maximum:
                raise StrictContractError(
                    "independent verifier found M below abs(K_mu)"
                )
            expected_cells.append(
                {
                    "target_block_index": target_block_index,
                    "source_block_index": source_block_index,
                    "candidate_loads": candidates,
                    "maximizing_source_member_id": maximizer,
                    "maximizing_source_member_sha256": source_frame["member_sha256"][maximizer],
                    "majorant": _fraction_wire(maximum),
                    "compressed_coefficient": _fraction_wire(compressed),
                    "absolute_compressed_coefficient": _fraction_wire(abs(compressed)),
                    "member_count": len(source_members),
                    "work_count": len(source_members) * len(target_members),
                }
            )
    if type(value) is not dict or value.get("cells") != expected_cells:
        raise StrictContractError(
            "fiber envelope certificate disagrees with independent Fraction verification"
        )


@dataclass(frozen=True, init=False)
class FiberEnvelope:
    _layer: DeclaredSyntheticTransferLayer = field(repr=False)
    _source_weights: PositiveFiberWeights = field(repr=False)
    _target_weights: PositiveFiberWeights = field(repr=False)
    _source_law: ExactFiniteFiberLaw = field(repr=False)
    _source_completeness: FiberCompletenessWitness = field(repr=False)
    _target_completeness: FiberCompletenessWitness = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("fiber envelope has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not FiberEnvelope or self._construction_seal is not _ENVELOPE_SEAL:
            raise StrictContractError("FiberEnvelope requires independent exact verification")
        _digest(self._source_seal_sha256, "fiber envelope source seal")

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        layer: DeclaredSyntheticTransferLayer,
        source_weights: PositiveFiberWeights,
        target_weights: PositiveFiberWeights,
        source_law: ExactFiniteFiberLaw,
        source_completeness: FiberCompletenessWitness,
        target_completeness: FiberCompletenessWitness,
    ) -> "FiberEnvelope":
        if cls is not FiberEnvelope or type(value) is not dict:
            raise StrictContractError("strict FiberEnvelope parsing is required")
        if (
            type(layer) is not DeclaredSyntheticTransferLayer
            or type(source_weights) is not PositiveFiberWeights
            or type(target_weights) is not PositiveFiberWeights
            or type(source_law) is not ExactFiniteFiberLaw
            or type(source_completeness) is not FiberCompletenessWitness
            or type(target_completeness) is not FiberCompletenessWitness
        ):
            raise StrictContractError("FiberEnvelope parser authority types are invalid")
        # Cheap shape/count checks precede exact certificate reconstruction.
        envelope_fields = {
            "schema_version", "evidence_scope", "hard_scope",
            "coefficient_authority", "basis_convention", "layer_sha256",
            "source_generator_sha256", "target_generator_sha256",
            "source_weights_sha256", "target_weights_sha256",
            "source_law_sha256", "source_completeness_sha256",
            "target_completeness_sha256", "source_block_count",
            "target_block_count", "block_pair_count", "candidate_load_count",
            "work_count", "cells", "verification_disposition",
        }
        if set(value) != envelope_fields:
            raise StrictContractError("fiber envelope outer fields mismatch")
        if (
            value["schema_version"] != FIBER_ENVELOPE_SCHEMA
            or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE
            or value["hard_scope"] != "complete_declared_finite_synthetic_rectangle_only"
            or value["coefficient_authority"] != DECLARED_SYNTHETIC_FIXTURE
            or value["basis_convention"] != "target_row_source_column_v1"
            or value["verification_disposition"] != FIBER_ENVELOPE_DISPOSITION
        ):
            raise StrictContractError("fiber envelope fixed schema/scope fields mismatch")
        raw_cells = value.get("cells")
        if type(raw_cells) is not list:
            raise StrictContractError("fiber envelope cells must be an exact array")
        if len(raw_cells) > MAX_FIBER_BLOCKS * MAX_FIBER_BLOCKS:
            raise StrictContractError("fiber envelope cell array exceeds its preflight cap")
        for name in (
            "layer_sha256",
            "source_generator_sha256",
            "target_generator_sha256",
            "source_weights_sha256",
            "target_weights_sha256",
            "source_law_sha256",
            "source_completeness_sha256",
            "target_completeness_sha256",
        ):
            _digest(value[name], f"fiber envelope {name}")
        for name, cap in (
            ("source_block_count", MAX_FIBER_BLOCKS),
            ("target_block_count", MAX_FIBER_BLOCKS),
            ("block_pair_count", MAX_FIBER_BLOCKS * MAX_FIBER_BLOCKS),
            ("candidate_load_count", MAX_FIBER_WORK_UNITS),
            ("work_count", MAX_FIBER_WORK_UNITS),
        ):
            _bounded_int(value[name], f"fiber envelope {name}", cap)
        cell_fields = {
            "target_block_index", "source_block_index", "candidate_loads",
            "maximizing_source_member_id", "maximizing_source_member_sha256",
            "majorant", "compressed_coefficient",
            "absolute_compressed_coefficient", "member_count", "work_count",
        }
        candidate_fields = {
            "source_member_id", "source_member_sha256", "load",
            "target_member_count", "work_count",
        }
        observed_candidates = 0
        observed_work = 0
        for cell in raw_cells:
            if type(cell) is not dict or set(cell) != cell_fields:
                raise StrictContractError("fiber envelope cell fields mismatch")
            candidates = cell["candidate_loads"]
            if type(candidates) is not list or len(candidates) > MAX_FIBER_MEMBERS:
                raise StrictContractError("fiber candidate list exceeds its preflight cap")
            for name in ("target_block_index", "source_block_index", "member_count", "work_count"):
                if type(cell[name]) is not int or cell[name] < 0 or cell[name] > MAX_FIBER_WORK_UNITS:
                    raise StrictContractError(f"fiber cell {name} is outside its cap")
            observed_candidates += len(candidates)
            observed_work += cell["work_count"]
            if observed_candidates > MAX_FIBER_WORK_UNITS or observed_work > MAX_FIBER_WORK_UNITS:
                raise StrictContractError("fiber envelope nested work exceeds its cap")
            candidate_ids: list[str] = []
            candidate_loads: list[ExactRational] = []
            candidate_sha256: dict[str, str] = {}
            for candidate in candidates:
                if type(candidate) is not dict or set(candidate) != candidate_fields:
                    raise StrictContractError("fiber candidate-load fields mismatch")
                for name in ("target_member_count", "work_count"):
                    if type(candidate[name]) is not int or candidate[name] < 0 or candidate[name] > MAX_FIBER_MEMBERS:
                        raise StrictContractError(f"fiber candidate {name} is outside its cap")
                member_id = _string(
                    candidate["source_member_id"], "fiber candidate member_id"
                )
                candidate_ids.append(member_id)
                candidate_sha256[member_id] = _digest(
                    candidate["source_member_sha256"],
                    "fiber candidate member_sha256",
                )
                candidate_loads.append(
                    ExactRational.from_dict(candidate["load"])
                )
            if (
                candidate_ids != sorted(candidate_ids)
                or len(candidate_ids) != len(set(candidate_ids))
                or cell["member_count"] != len(candidate_ids)
                or not candidate_loads
            ):
                raise StrictContractError("fiber candidate membership is not exact/canonical")
            maximum = candidate_loads[0]
            maximizer = candidate_ids[0]
            for member_id, load in zip(
                candidate_ids[1:], candidate_loads[1:], strict=True
            ):
                if _less(maximum, load):
                    maximum = load
                    maximizer = member_id
            declared_maximum = ExactRational.from_dict(cell["majorant"])
            compressed = ExactRational.from_dict(cell["compressed_coefficient"])
            absolute_compressed = ExactRational.from_dict(
                cell["absolute_compressed_coefficient"]
            )
            if (
                declared_maximum != maximum
                or cell["maximizing_source_member_id"] != maximizer
                or cell["maximizing_source_member_sha256"]
                != candidate_sha256[maximizer]
                or absolute_compressed != _absolute(compressed)
                or _less(declared_maximum, absolute_compressed)
            ):
                raise StrictContractError("fiber cell fails local majorant/extremizer checks")
        # Only after the complete nested certificate is bounded and parsed do
        # we invoke the expensive E0 authorities used for exact dimensions.
        context = _check_envelope_authorities(
            layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness,
        )
        source_frame, target_frame = context[0], context[1]
        expected_pairs = len(source_frame["blocks"]) * len(target_frame["blocks"])
        expected_candidates = len(target_frame["blocks"]) * len(source_frame["members"])
        expected_work = _checked_rectangle(
            len(source_frame["members"]), len(target_frame["members"])
        )
        if (
            len(raw_cells) != expected_pairs
            or value["candidate_load_count"] != expected_candidates
            or value["work_count"] != expected_work
            or observed_candidates != expected_candidates
            or observed_work != expected_work
        ):
            raise StrictContractError("fiber envelope nested coverage is incomplete")
        _independently_verify_envelope_wire(
            value, layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness,
            _validated_context=context,
        )
        expected_wire = _derive_envelope_wire(
            layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness,
            _validated_context=context,
        )
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("fiber envelope wire disagrees with independent recomputation")
        return _construct_fiber_envelope(
            layer, source_weights, target_weights, source_law,
            source_completeness, target_completeness, expected_wire,
        )

    @property
    def envelope_sha256(self) -> str:
        return _sha256(self.to_dict())

    @property
    def source_compression(self) -> WeightedCompression:
        _validated_envelope_wire(self)
        return make_weighted_compression(self._source_weights)

    @property
    def target_compression(self) -> WeightedCompression:
        _validated_envelope_wire(self)
        return make_weighted_compression(self._target_weights)

    @property
    def source_lifting(self) -> WeightedLifting:
        _validated_envelope_wire(self)
        return make_weighted_lifting(self._source_weights, self._source_law)

    def majorant_for(self, target_block_index: int, source_block_index: int) -> ExactRational:
        if type(target_block_index) is not int or type(source_block_index) is not int:
            raise StrictContractError("fiber envelope block indices must be exact integers")
        for cell in self.to_dict()["cells"]:
            if cell["target_block_index"] == target_block_index and cell["source_block_index"] == source_block_index:
                return ExactRational.from_dict(cell["majorant"])
        raise StrictContractError("fiber envelope block pair is outside the exact domain")

    def to_dict(self) -> dict[str, Any]:
        return _validated_envelope_wire(self)


def _validated_envelope_wire(
    envelope: FiberEnvelope,
    *,
    _frame_cache: list[
        tuple[ExactQuotientCoordinateGenerator, dict[str, Any]]
    ] | None = None,
) -> dict[str, Any]:
        if type(envelope) is not FiberEnvelope or envelope._construction_seal is not _ENVELOPE_SEAL:
            raise StrictContractError("fiber envelope construction seal changed")
        context = _check_envelope_authorities(
            envelope._layer,
            envelope._source_weights,
            envelope._target_weights,
            envelope._source_law,
            envelope._source_completeness,
            envelope._target_completeness,
            _frame_cache=_frame_cache,
        )
        wire = _derive_envelope_wire(
            envelope._layer, envelope._source_weights, envelope._target_weights,
            envelope._source_law, envelope._source_completeness,
            envelope._target_completeness, _validated_context=context,
        )
        if _sha256(
            {
                "layer": wire["layer_sha256"],
                "source_weights": wire["source_weights_sha256"],
                "target_weights": wire["target_weights_sha256"],
                "law": wire["source_law_sha256"],
                "source_completeness": wire["source_completeness_sha256"],
                "target_completeness": wire["target_completeness_sha256"],
            }
        ) != _digest(envelope._source_seal_sha256, "fiber envelope source seal"):
            raise StrictContractError("fiber envelope retained authority changed")
        return wire


def build_fiber_envelope(
    layer: DeclaredSyntheticTransferLayer,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
) -> FiberEnvelope:
    context = _check_envelope_authorities(
        layer, source_weights, target_weights, source_law,
        source_completeness, target_completeness,
    )
    wire = _derive_envelope_wire(
        layer, source_weights, target_weights, source_law,
        source_completeness, target_completeness,
        _validated_context=context,
    )
    _independently_verify_envelope_wire(
        wire, layer, source_weights, target_weights, source_law,
        source_completeness, target_completeness,
        _validated_context=context,
    )
    return _construct_fiber_envelope(
        layer, source_weights, target_weights, source_law,
        source_completeness, target_completeness, wire,
    )


def _construct_fiber_envelope(
    layer: DeclaredSyntheticTransferLayer,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
    wire: Mapping[str, Any],
) -> FiberEnvelope:
    result = object.__new__(FiberEnvelope)
    object.__setattr__(result, "_layer", layer)
    object.__setattr__(result, "_source_weights", source_weights)
    object.__setattr__(result, "_target_weights", target_weights)
    object.__setattr__(result, "_source_law", source_law)
    object.__setattr__(result, "_source_completeness", source_completeness)
    object.__setattr__(result, "_target_completeness", target_completeness)
    object.__setattr__(
        result,
        "_source_seal_sha256",
        _sha256(
            {
                "layer": wire["layer_sha256"],
                "source_weights": wire["source_weights_sha256"],
                "target_weights": wire["target_weights_sha256"],
                "law": wire["source_law_sha256"],
                "source_completeness": wire["source_completeness_sha256"],
                "target_completeness": wire["target_completeness_sha256"],
            }
        ),
    )
    object.__setattr__(result, "_construction_seal", _ENVELOPE_SEAL)
    result.__post_init__()
    return result


def verify_fiber_envelope(envelope: FiberEnvelope) -> FiberEnvelope:
    if type(envelope) is not FiberEnvelope:
        raise StrictContractError("fiber envelope verifier requires FiberEnvelope")
    wire = envelope.to_dict()
    _independently_verify_envelope_wire(
        wire, envelope._layer, envelope._source_weights,
        envelope._target_weights, envelope._source_law,
        envelope._source_completeness, envelope._target_completeness,
    )
    return envelope


def _normalize_injection(
    old_members: tuple[str, ...], new_members: tuple[str, ...], injection: Any, where: str
) -> dict[str, str]:
    if type(injection) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(injection) > MAX_FIBER_MEMBERS:
        raise StrictContractError(f"{where} exceeds its preflight cap")
    if len(injection) != len(old_members) or set(injection) != set(old_members):
        raise StrictContractError(f"{where} must inject every old member exactly once")
    result: dict[str, str] = {}
    for old in old_members:
        new = _string(injection[old], f"{where} target")
        if new not in new_members:
            raise StrictContractError(f"{where} maps outside the extended domain")
        result[old] = new
    if len(set(result.values())) != len(result):
        raise StrictContractError(f"{where} is not injective")
    return result


def _derive_inclusion_wire(
    old: FiberEnvelope,
    new: FiberEnvelope,
    source_injection: dict[str, str],
    target_injection: dict[str, str],
) -> dict[str, Any]:
    if type(old) is not FiberEnvelope or type(new) is not FiberEnvelope:
        raise StrictContractError("fiber inclusion requires two exact FiberEnvelope values")
    old_source = _retained_frame_preflight(old._layer._source_generator)
    new_source = _retained_frame_preflight(new._layer._source_generator)
    old_target = _retained_frame_preflight(old._layer._target_generator)
    new_target = _retained_frame_preflight(new._layer._target_generator)
    source_map = _normalize_injection(old_source["members"], new_source["members"], source_injection, "source injection")
    target_map = _normalize_injection(old_target["members"], new_target["members"], target_injection, "target injection")
    if len(old_source["blocks"]) != len(new_source["blocks"]) or len(old_target["blocks"]) != len(new_target["blocks"]):
        raise StrictContractError("fiber inclusion changes quotient block IDs/order")
    old_source_owner = {m: q for q, ms in old_source["blocks"] for m in ms}
    new_source_owner = {m: q for q, ms in new_source["blocks"] for m in ms}
    old_target_owner = {m: q for q, ms in old_target["blocks"] for m in ms}
    new_target_owner = {m: q for q, ms in new_target["blocks"] for m in ms}
    if any(old_source_owner[m] != new_source_owner[source_map[m]] for m in old_source["members"]) or any(old_target_owner[m] != new_target_owner[target_map[m]] for m in old_target["members"]):
        raise StrictContractError("fiber inclusion does not preserve quotient block IDs")
    if any(
        old_source["member_sha256"][member]
        != new_source["member_sha256"][source_map[member]]
        for member in old_source["members"]
    ) or any(
        old_target["member_sha256"][member]
        != new_target["member_sha256"][target_map[member]]
        for member in old_target["members"]
    ):
        raise StrictContractError("fiber inclusion changes an injected member identity")
    old_source_weights = dict(zip(old_source["members"], old._source_weights._values, strict=True))
    new_source_weights = dict(zip(new_source["members"], new._source_weights._values, strict=True))
    old_target_weights = dict(zip(old_target["members"], old._target_weights._values, strict=True))
    new_target_weights = dict(zip(new_target["members"], new._target_weights._values, strict=True))
    for old_member, new_member in source_map.items():
        if old_source_weights[old_member] != new_source_weights[new_member]:
            raise StrictContractError("fiber inclusion changes an injected source weight")
    for old_member, new_member in target_map.items():
        if old_target_weights[old_member] != new_target_weights[new_member]:
            raise StrictContractError("fiber inclusion changes an injected target weight")
    old_coefficients = {
        (target, source): value for target, source, value in old._layer._coefficients
    }
    new_coefficients = {
        (target, source): value for target, source, value in new._layer._coefficients
    }
    for old_target_member in old_target["members"]:
        for old_source_member in old_source["members"]:
            if old_coefficients.get(
                (old_target_member, old_source_member), ExactRational(0)
            ) != new_coefficients.get(
                (target_map[old_target_member], source_map[old_source_member]),
                ExactRational(0),
            ):
                raise StrictContractError("fiber inclusion changes an injected transfer cell")
    # Serialize the two expensive envelopes only after the typed injection,
    # state identities, inherited weights, and complete old rectangle pass.
    shared_frames: list[
        tuple[ExactQuotientCoordinateGenerator, dict[str, Any]]
    ] = []
    old_wire = _validated_envelope_wire(old, _frame_cache=shared_frames)
    new_wire = _validated_envelope_wire(new, _frame_cache=shared_frames)
    old_cells = {
        (row["target_block_index"], row["source_block_index"]): ExactRational.from_dict(row["majorant"])
        for row in old_wire["cells"]
    }
    new_cells = {
        (row["target_block_index"], row["source_block_index"]): ExactRational.from_dict(row["majorant"])
        for row in new_wire["cells"]
    }
    comparisons = []
    strict_count = 0
    for key in sorted(old_cells):
        if key not in new_cells or _less(new_cells[key], old_cells[key]):
            raise StrictContractError("fiber extension decreases an envelope cell")
        strict = _less(old_cells[key], new_cells[key])
        strict_count += int(strict)
        comparisons.append(
            {
                "target_block_index": key[0],
                "source_block_index": key[1],
                "old_majorant": old_cells[key].to_dict(),
                "new_majorant": new_cells[key].to_dict(),
                "strictly_increased": strict,
            }
        )
    return {
        "schema_version": FIBER_INCLUSION_WITNESS_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "old_envelope_sha256": _sha256(old_wire),
        "new_envelope_sha256": _sha256(new_wire),
        "source_injection": [
            {"old_member_id": member, "new_member_id": source_map[member]}
            for member in old_source["members"]
        ],
        "target_injection": [
            {"old_member_id": member, "new_member_id": target_map[member]}
            for member in old_target["members"]
        ],
        "injected_rectangle_count": len(old_source["members"]) * len(old_target["members"]),
        "cell_comparisons": comparisons,
        "strict_cell_count": strict_count,
        "monotone": True,
    }


@dataclass(frozen=True, init=False)
class FiberInclusionWitness:
    _old: FiberEnvelope = field(repr=False)
    _new: FiberEnvelope = field(repr=False)
    _source_injection: dict[str, str] = field(repr=False)
    _target_injection: dict[str, str] = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("fiber inclusion witness has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not FiberInclusionWitness or self._construction_seal is not _INCLUSION_SEAL:
            raise StrictContractError("FiberInclusionWitness requires typed exact verification")
        _digest(self._source_seal_sha256, "fiber inclusion source seal")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], old: FiberEnvelope, new: FiberEnvelope) -> "FiberInclusionWitness":
        if cls is not FiberInclusionWitness or type(value) is not dict:
            raise StrictContractError("strict FiberInclusionWitness parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "old_envelope_sha256",
            "new_envelope_sha256", "source_injection", "target_injection",
            "injected_rectangle_count", "cell_comparisons", "strict_cell_count",
            "monotone",
        } or value["schema_version"] != FIBER_INCLUSION_WITNESS_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE or value["monotone"] is not True:
            raise StrictContractError("FiberInclusionWitness outer fields/schema mismatch")
        if type(old) is not FiberEnvelope or type(new) is not FiberEnvelope:
            raise StrictContractError("fiber inclusion parser authorities are invalid")
        _digest(value["old_envelope_sha256"], "old fiber envelope SHA")
        _digest(value["new_envelope_sha256"], "new fiber envelope SHA")
        injected_count = _bounded_int(
            value["injected_rectangle_count"],
            "fiber inclusion rectangle count",
            MAX_FIBER_MEMBERS * MAX_FIBER_MEMBERS,
        )
        strict_count = _bounded_int(
            value["strict_cell_count"],
            "fiber inclusion strict-cell count",
            MAX_FIBER_BLOCKS * MAX_FIBER_BLOCKS,
        )
        comparisons = value["cell_comparisons"]
        if type(comparisons) is not list or len(comparisons) > MAX_FIBER_BLOCKS * MAX_FIBER_BLOCKS:
            raise StrictContractError("fiber inclusion comparison array exceeds preflight cap")
        comparison_fields = {
            "target_block_index",
            "source_block_index",
            "old_majorant",
            "new_majorant",
            "strictly_increased",
        }
        seen_comparisons: set[tuple[int, int]] = set()
        observed_strict = 0
        for row in comparisons:
            if type(row) is not dict or set(row) != comparison_fields:
                raise StrictContractError("fiber inclusion comparison fields mismatch")
            target_index = _bounded_int(
                row["target_block_index"],
                "fiber inclusion target block index",
                MAX_FIBER_BLOCKS - 1,
            )
            source_index = _bounded_int(
                row["source_block_index"],
                "fiber inclusion source block index",
                MAX_FIBER_BLOCKS - 1,
            )
            key = (target_index, source_index)
            if key in seen_comparisons:
                raise StrictContractError("fiber inclusion comparison is duplicated")
            seen_comparisons.add(key)
            old_majorant = ExactRational.from_dict(row["old_majorant"])
            new_majorant = ExactRational.from_dict(row["new_majorant"])
            if type(row["strictly_increased"]) is not bool:
                raise StrictContractError("fiber inclusion strict flag must be exact bool")
            if _less(new_majorant, old_majorant):
                raise StrictContractError("fiber inclusion preflight decreases a majorant")
            expected_strict = _less(old_majorant, new_majorant)
            if row["strictly_increased"] is not expected_strict:
                raise StrictContractError("fiber inclusion strict flag is inconsistent")
            observed_strict += int(expected_strict)
        if observed_strict != strict_count:
            raise StrictContractError("fiber inclusion strict-cell count changed")
        raw_source = value.get("source_injection")
        raw_target = value.get("target_injection")
        if type(raw_source) is not list or type(raw_target) is not list:
            raise StrictContractError("fiber inclusion injections must be exact arrays")
        if len(raw_source) > MAX_FIBER_MEMBERS or len(raw_target) > MAX_FIBER_MEMBERS:
            raise StrictContractError("fiber inclusion injection exceeds its preflight cap")
        if injected_count != len(raw_source) * len(raw_target):
            raise StrictContractError("fiber inclusion rectangle count changed")
        source = {}
        target = {}
        for rows, destination, label in ((raw_source, source, "source"), (raw_target, target, "target")):
            for row in rows:
                if type(row) is not dict or set(row) != {"old_member_id", "new_member_id"}:
                    raise StrictContractError(f"fiber {label} injection row fields mismatch")
                old_id = _string(row["old_member_id"], f"fiber {label} old member")
                if old_id in destination:
                    raise StrictContractError(f"fiber {label} injection duplicates a member")
                destination[old_id] = _string(row["new_member_id"], f"fiber {label} new member")
        expected_wire = _derive_inclusion_wire(old, new, source, target)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("fiber inclusion wire disagrees with independent verification")
        return _construct_fiber_inclusion(old, new, source, target, expected_wire)

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _INCLUSION_SEAL:
            raise StrictContractError("fiber inclusion construction seal changed")
        wire = _derive_inclusion_wire(
            self._old, self._new, self._source_injection, self._target_injection
        )
        if _sha256(
            {
                "old": wire["old_envelope_sha256"],
                "new": wire["new_envelope_sha256"],
                "source": wire["source_injection"],
                "target": wire["target_injection"],
            }
        ) != _digest(self._source_seal_sha256, "fiber inclusion source seal"):
            raise StrictContractError("fiber inclusion retained authority changed")
        return wire


def verify_fiber_inclusion(
    old: FiberEnvelope,
    new: FiberEnvelope,
    source_injection: Any,
    target_injection: Any,
) -> FiberInclusionWitness:
    if type(old) is not FiberEnvelope or type(new) is not FiberEnvelope:
        raise StrictContractError("fiber inclusion requires two exact FiberEnvelope values")
    if type(source_injection) is not dict or type(target_injection) is not dict:
        raise StrictContractError("fiber inclusion injections must be exact objects")
    if (
        len(source_injection) > MAX_FIBER_MEMBERS
        or len(target_injection) > MAX_FIBER_MEMBERS
    ):
        raise StrictContractError("fiber inclusion injection exceeds its preflight cap")
    old_source = _retained_frame_preflight(old._layer._source_generator)
    new_source = _retained_frame_preflight(new._layer._source_generator)
    old_target = _retained_frame_preflight(old._layer._target_generator)
    new_target = _retained_frame_preflight(new._layer._target_generator)
    source = _normalize_injection(old_source["members"], new_source["members"], source_injection, "source injection")
    target = _normalize_injection(old_target["members"], new_target["members"], target_injection, "target injection")
    wire = _derive_inclusion_wire(old, new, source, target)
    return _construct_fiber_inclusion(old, new, source, target, wire)


def _construct_fiber_inclusion(
    old: FiberEnvelope,
    new: FiberEnvelope,
    source: dict[str, str],
    target: dict[str, str],
    wire: Mapping[str, Any],
) -> FiberInclusionWitness:
    result = object.__new__(FiberInclusionWitness)
    object.__setattr__(result, "_old", old)
    object.__setattr__(result, "_new", new)
    object.__setattr__(result, "_source_injection", source)
    object.__setattr__(result, "_target_injection", target)
    object.__setattr__(
        result,
        "_source_seal_sha256",
        _sha256(
            {
                "old": wire["old_envelope_sha256"],
                "new": wire["new_envelope_sha256"],
                "source": wire["source_injection"],
                "target": wire["target_injection"],
            }
        ),
    )
    object.__setattr__(result, "_construction_seal", _INCLUSION_SEAL)
    result.__post_init__()
    return result


__all__ = [
    "DECLARED_SYNTHETIC_FIXTURE",
    "FIBER_ENVELOPE_DISPOSITION",
    "MAX_FIBER_BLOCKS",
    "MAX_FIBER_MEMBERS",
    "MAX_FIBER_WORK_UNITS",
    "MAX_SPARSE_TRANSFER_CELLS",
    "DeclaredSyntheticTransferLayer",
    "DomainMembershipWitness",
    "FiberCompletenessWitness",
    "FiberEnvelope",
    "FiberInclusionWitness",
    "build_fiber_envelope",
    "certify_fiber_completeness",
    "declare_synthetic_transfer_layer",
    "verify_fiber_envelope",
    "verify_fiber_inclusion",
    "witness_domain_membership",
]
