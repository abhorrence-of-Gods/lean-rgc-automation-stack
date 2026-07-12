"""Strict finite quotient export and evidence-tier firewall.

This module is development-only.  ``CertifiedIntervalOperator`` certifies
structural successor containment on one complete synthetic finite source.  It
is not a positive envelope, a numeric upper bound, or production Lean evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

from .behavioral_partition import VerifiedExactPartition, verify_exact_partition
from .contracts import (
    MAX_SYNTHETIC_ACTIONS,
    MAX_SYNTHETIC_TOTALIZED_STATES,
    MAX_SYNTHETIC_TRANSITION_ROWS,
    SYNTHETIC_EVIDENCE_SCOPE,
    StrictContractError,
    TotalizedStatus,
    canonical_contract_bytes,
)


MAX_SIGNED_64 = (1 << 63) - 1
MAX_TIER_FIREWALL_WORK_UNITS = 250_000

EXACT_FINITE_OPERATOR_SCHEMA = "odlrq_exact_finite_operator_v1"
INTERVAL_TARGET_ROW_SCHEMA = "odlrq_interval_target_row_v1"
INTERVAL_CANDIDATE_SCHEMA = "odlrq_interval_candidate_v1"
UPPERNESS_EVIDENCE_ROW_SCHEMA = "odlrq_upperness_evidence_row_v1"
UPPERNESS_DOMAIN_EVIDENCE_SCHEMA = "odlrq_upperness_domain_evidence_v1"
UPPERNESS_DOMAIN_WITNESS_SCHEMA = "odlrq_upperness_domain_witness_v1"
CERTIFIED_INTERVAL_OPERATOR_SCHEMA = "odlrq_certified_interval_operator_v1"
OBSERVED_INTERVAL_OPERATOR_SCHEMA = "odlrq_observed_interval_operator_v1"
NOMINAL_OPERATOR_SCHEMA = "odlrq_nominal_operator_v1"

_INTERVAL_ROW_FIELDS = (
    "schema_version",
    "source_block_index",
    "action_id",
    "target_block_indices",
)
_INTERVAL_CANDIDATE_FIELDS = (
    "schema_version",
    "exact_operator_sha256",
    "provenance_id",
    "work_units",
    "rows",
)

EXACT_OPERATOR_TIER = "exact_finite_synthetic_development"
CERTIFIED_OPERATOR_TIER = "certified_structural_interval_synthetic_development"
OBSERVED_OPERATOR_TIER = "observed_interval_development"
NOMINAL_OPERATOR_TIER = "nominal_support_development"

_EXACT_SEAL = object()
_WITNESS_SEAL = object()
_CERTIFIED_SEAL = object()


def _object(value: Mapping[str, Any] | Any, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    obj = value
    if set(obj) != fields:
        missing = sorted(fields - set(obj))
        unknown = sorted(set(obj) - fields)
        raise StrictContractError(
            f"{where} fields mismatch; missing={missing}, unknown={unknown}"
        )
    return obj


def _object_without_set(
    value: Mapping[str, Any] | Any, fields: tuple[str, ...], where: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(value) != len(fields):
        raise StrictContractError(f"{where} field count mismatch")
    for field_name in fields:
        if field_name not in value:
            raise StrictContractError(f"{where} is missing field {field_name!r}")
    for field_name in value:
        if field_name not in fields:
            raise StrictContractError(f"{where} has unknown field {field_name!r}")
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


def _nonnegative_int(value: Any, where: str, *, upper: int = MAX_SIGNED_64) -> int:
    if type(value) is not int or value < 0 or value > upper:
        raise StrictContractError(
            f"{where} must be an exact nonnegative integer at most {upper}"
        )
    return value


def _signed64_target(value: Any, where: str) -> int:
    # This check deliberately precedes every set, sort, bit operation, and
    # domain lookup involving an interval target.
    return _nonnegative_int(value, where, upper=MAX_SIGNED_64)


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _digest(value: Any, where: str) -> str:
    result = _string(value, where).upper()
    if len(result) != 64 or any(ch not in "0123456789ABCDEF" for ch in result):
        raise StrictContractError(f"{where} must be a SHA-256 hex digest")
    return result


def _checked_add(total: int, units: int, where: str) -> int:
    _nonnegative_int(total, f"{where} total")
    _nonnegative_int(units, f"{where} units")
    result = total + units
    if result > MAX_TIER_FIREWALL_WORK_UNITS:
        raise StrictContractError(
            f"{where} exceeds the {MAX_TIER_FIREWALL_WORK_UNITS} work-unit cap"
        )
    return result


def _checked_product(left: int, right: int, where: str) -> int:
    _nonnegative_int(left, f"{where} left")
    _nonnegative_int(right, f"{where} right")
    if left and right > MAX_TIER_FIREWALL_WORK_UNITS // left:
        raise StrictContractError(
            f"{where} exceeds the {MAX_TIER_FIREWALL_WORK_UNITS} work-unit cap"
        )
    return left * right


def _tier_base_work_units(
    *, total_members: int, block_count: int, action_count: int
) -> int:
    total = _checked_product(total_members, action_count, "member/action cells")
    return _checked_add(
        total,
        _checked_product(block_count, action_count, "block/action cells"),
        "tier work",
    )


def _fresh_verified(source: VerifiedExactPartition) -> VerifiedExactPartition:
    if type(source) is not VerifiedExactPartition:
        raise StrictContractError(
            "exact operator export requires an exact VerifiedExactPartition"
        )
    try:
        fresh = verify_exact_partition(source.admitted, source.certificate)
        supplied_wire = canonical_contract_bytes(source.to_dict())
        fresh_wire = canonical_contract_bytes(fresh.to_dict())
    except StrictContractError:
        raise
    except Exception as exc:
        raise StrictContractError(
            "verified partition object cannot be freshly rederived"
        ) from exc
    if supplied_wire != fresh_wire:
        raise StrictContractError(
            "verified partition object does not match fresh independent verification"
        )
    return fresh


def _fresh_verified_digest(source: VerifiedExactPartition) -> str:
    return _sha256(_fresh_verified(source).to_dict())


def _derive_exact_wire_from_fresh(
    fresh: VerifiedExactPartition,
) -> dict[str, Any]:
    snapshot = fresh.admitted.snapshot
    certificate = fresh.certificate

    # The exact authority is the first table consumed by the tier firewall.
    # Reject an impossible base budget before deriving any lookup table.
    _tier_base_work_units(
        total_members=len(snapshot.states),
        block_count=len(certificate.final_blocks),
        action_count=len(certificate.canonical_action_ids),
    )

    states_by_id = {state.state_id: state for state in snapshot.states}
    actions_by_id = {action.action_id: action for action in snapshot.actions}
    transitions_by_key = {
        (row.source_state_id, row.action_id): row for row in snapshot.transitions
    }
    if (
        len(states_by_id) != len(snapshot.states)
        or len(actions_by_id) != len(snapshot.actions)
        or len(transitions_by_key) != len(snapshot.transitions)
    ):
        raise StrictContractError("exact source contains duplicate semantic payloads")

    block_owner: dict[str, int] = {}
    block_wires: list[dict[str, Any]] = []
    total_members = 0
    for block in certificate.final_blocks:
        member_wires: list[dict[str, Any]] = []
        for state_id in block.member_state_ids:
            if state_id in block_owner or state_id not in states_by_id:
                raise StrictContractError("exact partition member lookup is invalid")
            block_owner[state_id] = block.block_index
            member_wires.append(states_by_id[state_id].to_dict())
            total_members += 1
        block_wires.append(
            {
                "block_index": block.block_index,
                "member_count": len(block.member_state_ids),
                "members": member_wires,
            }
        )
    if total_members != len(snapshot.states) or set(block_owner) != set(states_by_id):
        raise StrictContractError("exact partition does not retain every totalized state")

    canonical_action_ids = certificate.canonical_action_ids
    if set(canonical_action_ids) != set(actions_by_id):
        raise StrictContractError("exact partition action alphabet changed")
    action_wires = [actions_by_id[action_id].to_dict() for action_id in canonical_action_ids]

    quotient_rows_by_key = {
        (row.source_block_index, row.action_id): row
        for row in certificate.quotient_rows
    }
    row_wires: list[dict[str, Any]] = []
    for block in certificate.final_blocks:
        for action_id in canonical_action_ids:
            key = (block.block_index, action_id)
            quotient_row = quotient_rows_by_key.get(key)
            if quotient_row is None:
                raise StrictContractError("exact quotient row is missing")
            member_transitions: list[dict[str, Any]] = []
            for member_state_id in block.member_state_ids:
                transition = transitions_by_key.get((member_state_id, action_id))
                if transition is None:
                    raise StrictContractError("exact member/action transition is missing")
                target_block = block_owner.get(transition.target_state_id)
                if target_block is None or target_block != quotient_row.target_block_index:
                    raise StrictContractError(
                        "representative substitution disagrees with a complete member transition"
                    )
                source_state = states_by_id[member_state_id]
                if source_state.totalized_kind in {
                    TotalizedStatus.CLOSED,
                    TotalizedStatus.SINK,
                } and transition.target_state_id != member_state_id:
                    raise StrictContractError("terminal totalization is not absorbing")
                member_transitions.append(
                    {
                        "source_state_id": member_state_id,
                        "source_state_sha256": _sha256(source_state.to_dict()),
                        "target_state_id": transition.target_state_id,
                        "target_state_sha256": _sha256(
                            states_by_id[transition.target_state_id].to_dict()
                        ),
                    }
                )
            row_wires.append(
                {
                    "source_block_index": block.block_index,
                    "action_id": action_id,
                    "action_sha256": _sha256(actions_by_id[action_id].to_dict()),
                    "target_block_index": quotient_row.target_block_index,
                    "member_transition_count": len(member_transitions),
                    "member_transitions": member_transitions,
                }
            )

    if len(row_wires) != len(certificate.final_blocks) * len(canonical_action_ids):
        raise StrictContractError("exact quotient export is not structurally total")

    return {
        "schema_version": EXACT_FINITE_OPERATOR_SCHEMA,
        "operator_tier": EXACT_OPERATOR_TIER,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "verified_partition_sha256": _sha256(fresh.to_dict()),
        "snapshot_sha256": certificate.snapshot_sha256,
        "domain_payload_digest": certificate.domain_payload_digest,
        "observation_frame_digest": certificate.observation_frame_digest,
        "transition_semantics_digest": certificate.transition_semantics_digest,
        "response_vocabulary_digest": certificate.response_vocabulary_digest,
        "action_alphabet_digest": certificate.action_alphabet_digest,
        "totalized_state_count": total_members,
        "block_count": len(certificate.final_blocks),
        "action_count": len(canonical_action_ids),
        "blocks": block_wires,
        "actions": action_wires,
        "rows": row_wires,
    }


def _derive_exact_wire(source: VerifiedExactPartition) -> dict[str, Any]:
    return _derive_exact_wire_from_fresh(_fresh_verified(source))


@dataclass(frozen=True)
class ExactFiniteOperator:
    _verified_source: VerifiedExactPartition = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not ExactFiniteOperator:
            raise StrictContractError("ExactFiniteOperator subclasses are forbidden")
        if self._construction_seal is not _EXACT_SEAL:
            raise StrictContractError("exact operator requires the verified export gate")
        expected = _fresh_verified_digest(self._verified_source)
        if _digest(self._source_seal_sha256, "exact source seal") != expected:
            raise StrictContractError("exact operator source seal mismatch")

    @classmethod
    def from_verified(cls, source: VerifiedExactPartition) -> "ExactFiniteOperator":
        if cls is not ExactFiniteOperator:
            raise StrictContractError("polymorphic exact export is forbidden")
        seal = _fresh_verified_digest(source)
        return cls(source, seal, _construction_seal=_EXACT_SEAL)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], source: VerifiedExactPartition
    ) -> "ExactFiniteOperator":
        if cls is not ExactFiniteOperator:
            raise StrictContractError("polymorphic exact parsing is forbidden")
        obj = _object(value, set(_derive_exact_wire(source)), "ExactFiniteOperator")
        expected = cls.from_verified(source)
        if canonical_contract_bytes(obj) != canonical_contract_bytes(expected.to_dict()):
            raise StrictContractError("exact wire does not match external verified authority")
        return expected

    @property
    def operator_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _EXACT_SEAL:
            raise StrictContractError("exact operator construction seal changed")
        fresh = _fresh_verified(self._verified_source)
        if _sha256(fresh.to_dict()) != _digest(
            self._source_seal_sha256, "exact source seal"
        ):
            raise StrictContractError("exact operator retained source was replaced or changed")
        return _derive_exact_wire_from_fresh(fresh)


def export_exact_finite_operator(
    source: VerifiedExactPartition,
) -> ExactFiniteOperator:
    return ExactFiniteOperator.from_verified(source)


@dataclass(frozen=True)
class _ExactContext:
    wire: dict[str, Any]
    operator_sha256: str
    total_members: int
    block_count: int
    action_count: int


def _exact_context(exact: ExactFiniteOperator) -> _ExactContext:
    if type(exact) is not ExactFiniteOperator:
        raise StrictContractError("operation requires an exact finite operator")
    wire = exact.to_dict()
    total_members = _nonnegative_int(
        wire["totalized_state_count"], "exact totalized states"
    )
    block_count = _nonnegative_int(wire["block_count"], "exact block count")
    action_count = _nonnegative_int(wire["action_count"], "exact action count")
    return _ExactContext(
        wire,
        _sha256(wire),
        total_members,
        block_count,
        action_count,
    )


def _scan_interval_targets(
    targets: Sequence[Any],
    *,
    required_container_type: type,
    where: str,
    block_count: int | None = None,
    exact_target: int | None = None,
) -> tuple[int, bool]:
    if type(targets) is not required_container_type:
        raise StrictContractError(
            f"{where} must be an exact {required_container_type.__name__}"
        )
    count = len(targets)
    if count == 0:
        raise StrictContractError(f"{where} must be nonempty")
    if count > MAX_TIER_FIREWALL_WORK_UNITS:
        raise StrictContractError(f"{where} exceeds the work cap")

    contains_exact = False
    previous: int | None = None
    for index, raw_target in enumerate(targets):
        target = _signed64_target(raw_target, f"{where}[{index}]")
        if previous is not None and target <= previous:
            if target == previous:
                raise StrictContractError(f"{where} contains duplicates")
            raise StrictContractError(f"{where} is not in canonical order")
        if block_count is not None and target >= block_count:
            raise StrictContractError("candidate target block is outside the exact domain")
        if exact_target is not None and target == exact_target:
            contains_exact = True
        previous = target
    return count, contains_exact


def _scan_interval_row(
    row: "IntervalTargetRow",
    *,
    where: str,
    expected_wire: Mapping[str, Any] | None = None,
    block_count: int | None = None,
) -> tuple[int, bool]:
    if type(row) is not IntervalTargetRow:
        raise StrictContractError(f"{where} is not an exact IntervalTargetRow")
    source = _nonnegative_int(row.source_block_index, f"{where} source block")
    action = _string(row.action_id, f"{where} action ID")
    exact_target: int | None = None
    if expected_wire is not None:
        expected_source = _nonnegative_int(
            expected_wire["source_block_index"], f"{where} expected source block"
        )
        expected_action = _string(
            expected_wire["action_id"], f"{where} expected action ID"
        )
        exact_target = _nonnegative_int(
            expected_wire["target_block_index"], f"{where} exact target"
        )
        if source != expected_source or action != expected_action:
            raise StrictContractError(
                "candidate rows are missing, duplicated, or reordered"
            )
    return _scan_interval_targets(
        row.target_block_indices,
        required_container_type=tuple,
        where=f"{where} targets",
        block_count=block_count,
        exact_target=exact_target,
    )


@dataclass(frozen=True)
class IntervalTargetRow:
    source_block_index: int
    action_id: str
    target_block_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self) is not IntervalTargetRow:
            raise StrictContractError("IntervalTargetRow subclasses are forbidden")
        _scan_interval_row(self, where="interval row")

    def to_dict(self) -> dict[str, Any]:
        _scan_interval_row(self, where="interval row")
        return {
            "schema_version": INTERVAL_TARGET_ROW_SCHEMA,
            "source_block_index": self.source_block_index,
            "action_id": self.action_id,
            "target_block_indices": list(self.target_block_indices),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IntervalTargetRow":
        if cls is not IntervalTargetRow:
            raise StrictContractError("polymorphic interval row parsing is forbidden")
        obj = _object(
            value,
            {
                "schema_version",
                "source_block_index",
                "action_id",
                "target_block_indices",
            },
            "IntervalTargetRow",
        )
        _fixed(obj["schema_version"], INTERVAL_TARGET_ROW_SCHEMA, "interval row schema")
        raw_targets = _array(obj["target_block_indices"], "interval targets")
        # Charge raw length, including duplicates, before parsing/normalizing.
        if len(raw_targets) > MAX_TIER_FIREWALL_WORK_UNITS:
            raise StrictContractError("raw interval target list exceeds the work cap")
        result = cls(
            source_block_index=_nonnegative_int(
                obj["source_block_index"], "interval source block"
            ),
            action_id=_string(obj["action_id"], "interval action ID"),
            target_block_indices=tuple(
                _signed64_target(target, f"interval target[{index}]")
                for index, target in enumerate(raw_targets)
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("interval row is not canonical")
        return result


def _exact_dimensions(exact: ExactFiniteOperator) -> tuple[dict[str, Any], int, int, int]:
    context = _exact_context(exact)
    return (
        context.wire,
        context.total_members,
        context.block_count,
        context.action_count,
    )


def _exact_target_map(exact_wire: Mapping[str, Any]) -> dict[tuple[int, str], int]:
    return {
        (row["source_block_index"], row["action_id"]): row["target_block_index"]
        for row in exact_wire["rows"]
    }


def _tier_work_units(
    *,
    total_members: int,
    block_count: int,
    action_count: int,
    target_cells: int,
    union_cells: int,
) -> int:
    total = _tier_base_work_units(
        total_members=total_members,
        block_count=block_count,
        action_count=action_count,
    )
    total = _checked_add(total, target_cells, "tier work")
    total = _checked_add(total, union_cells, "tier work")
    return total


def _preflight_candidate_rows_with_context(
    context: _ExactContext, rows: Sequence[IntervalTargetRow]
) -> int:
    if type(rows) not in {tuple, list}:
        raise StrictContractError("candidate rows require an exact list or tuple")
    expected_rows = context.wire["rows"]
    if len(rows) != context.block_count * context.action_count:
        raise StrictContractError("candidate must contain every block/action row")
    if len(rows) != len(expected_rows):
        raise StrictContractError("exact operator row count changed")

    # Shape and T are charged before any nested target value is decoded.
    target_cells = 0
    for row in rows:
        if type(row) is not IntervalTargetRow:
            raise StrictContractError(
                "candidate rows must contain exact IntervalTargetRow objects"
            )
        if type(row.target_block_indices) is not tuple:
            raise StrictContractError("candidate targets must be exact tuples")
        if not row.target_block_indices:
            raise StrictContractError("candidate target tuple must be nonempty")
        target_cells = _checked_add(
            target_cells,
            len(row.target_block_indices),
            "candidate target cells",
        )

    # U >= T.  This rejects raw nested bombs before value validation and before
    # constructing any derived table, set, or output tuple.
    lower = _tier_base_work_units(
        total_members=context.total_members,
        block_count=context.block_count,
        action_count=context.action_count,
    )
    lower = _checked_add(lower, target_cells, "candidate lower-bound work")
    _checked_add(lower, target_cells, "candidate lower-bound work")

    union_cells = 0
    for index in range(len(rows)):
        target_count, contains_exact = _scan_interval_row(
            rows[index],
            where=f"candidate row[{index}]",
            expected_wire=expected_rows[index],
            block_count=context.block_count,
        )
        union_cells = _checked_add(
            union_cells,
            target_count + (0 if contains_exact else 1),
            "candidate union cells",
        )
    return _tier_work_units(
        total_members=context.total_members,
        block_count=context.block_count,
        action_count=context.action_count,
        target_cells=target_cells,
        union_cells=union_cells,
    )


def _validate_candidate_rows_with_context(
    context: _ExactContext, rows: tuple[IntervalTargetRow, ...]
) -> tuple[tuple[IntervalTargetRow, ...], int]:
    if type(rows) is not tuple:
        raise StrictContractError("candidate rows must be an exact IntervalTargetRow tuple")
    return rows, _preflight_candidate_rows_with_context(context, rows)


def _validate_candidate_rows(
    exact: ExactFiniteOperator, rows: tuple[IntervalTargetRow, ...]
) -> tuple[tuple[IntervalTargetRow, ...], int]:
    return _validate_candidate_rows_with_context(_exact_context(exact), rows)


def _make_interval_candidate_with_context(
    context: _ExactContext,
    rows: Sequence[IntervalTargetRow],
    *,
    provenance_id: str,
) -> IntervalCandidate:
    work = _preflight_candidate_rows_with_context(context, rows)
    # This is the first output tuple derived from the caller's proposal, and it
    # is intentionally built only after the exact frozen W_T has passed.
    materialized = rows if type(rows) is tuple else tuple(rows)
    return IntervalCandidate(
        exact_operator_sha256=context.operator_sha256,
        provenance_id=_string(provenance_id, "candidate provenance ID"),
        rows=materialized,
        work_units=work,
    )


def _preflight_raw_candidate_rows(
    context: _ExactContext, raw_rows: list[Any]
) -> int:
    expected_rows = context.wire["rows"]
    if len(raw_rows) != context.block_count * context.action_count:
        raise StrictContractError("candidate raw row count is not structurally total")
    if len(raw_rows) != len(expected_rows):
        raise StrictContractError("exact operator row count changed")

    # First pass: wire shape and raw T only.  No nested value is decoded and no
    # proposal-derived tuple, set, or table is constructed.
    target_cells = 0
    for index, raw_row in enumerate(raw_rows):
        row_obj = _object_without_set(
            raw_row, _INTERVAL_ROW_FIELDS, f"candidate raw row[{index}]"
        )
        raw_targets = row_obj["target_block_indices"]
        if type(raw_targets) is not list:
            raise StrictContractError("candidate raw targets must be an exact array")
        if not raw_targets:
            raise StrictContractError("candidate raw targets must be nonempty")
        target_cells = _checked_add(
            target_cells, len(raw_targets), "raw candidate target cells"
        )

    lower = _tier_base_work_units(
        total_members=context.total_members,
        block_count=context.block_count,
        action_count=context.action_count,
    )
    lower = _checked_add(lower, target_cells, "raw candidate lower-bound work")
    _checked_add(lower, target_cells, "raw candidate lower-bound work")

    # Second pass: exact signed-64/domain/key validation and exact U.  This is
    # still streaming over the two authority/input tables.
    union_cells = 0
    for index in range(len(raw_rows)):
        row_obj = _object_without_set(
            raw_rows[index], _INTERVAL_ROW_FIELDS, f"candidate raw row[{index}]"
        )
        expected = expected_rows[index]
        _fixed(
            row_obj["schema_version"],
            INTERVAL_TARGET_ROW_SCHEMA,
            f"candidate raw row[{index}] schema",
        )
        source = _nonnegative_int(
            row_obj["source_block_index"],
            f"candidate raw row[{index}] source block",
        )
        action = _string(
            row_obj["action_id"], f"candidate raw row[{index}] action ID"
        )
        expected_source = _nonnegative_int(
            expected["source_block_index"],
            f"candidate raw row[{index}] expected source block",
        )
        expected_action = _string(
            expected["action_id"],
            f"candidate raw row[{index}] expected action ID",
        )
        exact_target = _nonnegative_int(
            expected["target_block_index"],
            f"candidate raw row[{index}] exact target",
        )
        if source != expected_source or action != expected_action:
            raise StrictContractError(
                "candidate rows are missing, duplicated, or reordered"
            )
        target_count, contains_exact = _scan_interval_targets(
            row_obj["target_block_indices"],
            required_container_type=list,
            where=f"candidate raw row[{index}] targets",
            block_count=context.block_count,
            exact_target=exact_target,
        )
        union_cells = _checked_add(
            union_cells,
            target_count + (0 if contains_exact else 1),
            "raw candidate union cells",
        )
    return _tier_work_units(
        total_members=context.total_members,
        block_count=context.block_count,
        action_count=context.action_count,
        target_cells=target_cells,
        union_cells=union_cells,
    )


@dataclass(frozen=True)
class IntervalCandidate:
    exact_operator_sha256: str
    provenance_id: str
    rows: tuple[IntervalTargetRow, ...]
    work_units: int

    def __post_init__(self) -> None:
        if type(self) is not IntervalCandidate:
            raise StrictContractError("IntervalCandidate subclasses are forbidden")
        object.__setattr__(
            self,
            "exact_operator_sha256",
            _digest(self.exact_operator_sha256, "candidate exact operator digest"),
        )
        _string(self.provenance_id, "candidate provenance ID")
        if type(self.rows) is not tuple:
            raise StrictContractError("candidate rows are not an exact strict tuple")
        if len(self.rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
            raise StrictContractError("candidate row count exceeds the finite table cap")
        for index, row in enumerate(self.rows):
            _scan_interval_row(row, where=f"candidate row[{index}]")
        _nonnegative_int(
            self.work_units,
            "candidate work units",
            upper=MAX_TIER_FIREWALL_WORK_UNITS,
        )

    @property
    def candidate_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        if type(self.rows) is not tuple or len(self.rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
            raise StrictContractError("candidate retained rows are invalid")
        for index, row in enumerate(self.rows):
            _scan_interval_row(row, where=f"candidate row[{index}]")
        _digest(self.exact_operator_sha256, "candidate exact operator digest")
        _string(self.provenance_id, "candidate provenance ID")
        _nonnegative_int(
            self.work_units,
            "candidate work units",
            upper=MAX_TIER_FIREWALL_WORK_UNITS,
        )
        return {
            "schema_version": INTERVAL_CANDIDATE_SCHEMA,
            "exact_operator_sha256": self.exact_operator_sha256,
            "provenance_id": self.provenance_id,
            "work_units": self.work_units,
            "rows": [row.to_dict() for row in self.rows],
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], exact: ExactFiniteOperator
    ) -> "IntervalCandidate":
        if cls is not IntervalCandidate:
            raise StrictContractError("polymorphic candidate parsing is forbidden")
        obj = _object_without_set(
            value, _INTERVAL_CANDIDATE_FIELDS, "IntervalCandidate"
        )
        _fixed(obj["schema_version"], INTERVAL_CANDIDATE_SCHEMA, "candidate schema")
        raw_rows = _array(obj["rows"], "candidate rows")
        context = _exact_context(exact)
        if (
            _digest(obj["exact_operator_sha256"], "candidate exact operator digest")
            != context.operator_sha256
        ):
            raise StrictContractError("candidate wire binds a different exact operator")
        _string(obj["provenance_id"], "candidate provenance ID")
        declared_work = _nonnegative_int(
            obj["work_units"],
            "candidate work units",
            upper=MAX_TIER_FIREWALL_WORK_UNITS,
        )
        preflight_work = _preflight_raw_candidate_rows(context, raw_rows)
        if declared_work != preflight_work:
            raise StrictContractError("candidate wire work accounting mismatch")
        rows = tuple(IntervalTargetRow.from_dict(row) for row in raw_rows)
        candidate = _make_interval_candidate_with_context(
            context,
            rows,
            provenance_id=_string(obj["provenance_id"], "candidate provenance ID"),
        )
        if candidate.to_dict() != obj:
            raise StrictContractError("candidate wire does not match external exact authority")
        return candidate


def make_interval_candidate(
    exact: ExactFiniteOperator,
    rows: Sequence[IntervalTargetRow],
    *,
    provenance_id: str,
) -> IntervalCandidate:
    if type(rows) not in {tuple, list}:
        raise StrictContractError("candidate factory requires an exact list or tuple")
    context = _exact_context(exact)
    if len(rows) != context.block_count * context.action_count:
        raise StrictContractError(
            "candidate row count is rejected before tuple construction"
        )
    return _make_interval_candidate_with_context(
        context,
        rows,
        provenance_id=provenance_id,
    )


def _validate_candidate_object_with_context(
    candidate: IntervalCandidate, context: _ExactContext
) -> int:
    if type(candidate) is not IntervalCandidate:
        raise StrictContractError("operation requires a strict interval candidate")
    if type(candidate.rows) is not tuple:
        raise StrictContractError("candidate retained rows are not an exact tuple")
    if _digest(
        candidate.exact_operator_sha256, "candidate exact operator digest"
    ) != context.operator_sha256:
        raise StrictContractError("candidate binds a different exact operator")
    _string(candidate.provenance_id, "candidate provenance ID")
    work = _preflight_candidate_rows_with_context(context, candidate.rows)
    declared = _nonnegative_int(
        candidate.work_units,
        "candidate work units",
        upper=MAX_TIER_FIREWALL_WORK_UNITS,
    )
    if declared != work:
        raise StrictContractError("candidate work accounting changed")
    return work


def _union_target_stats(
    left: tuple[int, ...], right: tuple[int, ...], *, exact_target: int
) -> tuple[int, bool]:
    left_index = 0
    right_index = 0
    count = 0
    contains_exact = False
    while left_index < len(left) or right_index < len(right):
        if right_index >= len(right):
            value = left[left_index]
            left_index += 1
        elif left_index >= len(left):
            value = right[right_index]
            right_index += 1
        else:
            left_value = left[left_index]
            right_value = right[right_index]
            if left_value < right_value:
                value = left_value
                left_index += 1
            elif right_value < left_value:
                value = right_value
                right_index += 1
            else:
                value = left_value
                left_index += 1
                right_index += 1
        count += 1
        if value == exact_target:
            contains_exact = True
    return count, contains_exact


def _merge_target_tuples(
    left: tuple[int, ...], right: tuple[int, ...]
) -> tuple[int, ...]:
    merged: list[int] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) or right_index < len(right):
        if right_index >= len(right):
            value = left[left_index]
            left_index += 1
        elif left_index >= len(left):
            value = right[right_index]
            right_index += 1
        else:
            left_value = left[left_index]
            right_value = right[right_index]
            if left_value < right_value:
                value = left_value
                left_index += 1
            elif right_value < left_value:
                value = right_value
                right_index += 1
            else:
                value = left_value
                left_index += 1
                right_index += 1
        merged.append(value)
    return tuple(merged)


def extend_interval_candidate(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    additions: Sequence[IntervalTargetRow],
    *,
    provenance_id: str,
) -> IntervalCandidate:
    context = _exact_context(exact)
    _validate_candidate_object_with_context(candidate, context)
    if type(additions) not in {tuple, list}:
        raise StrictContractError("candidate extension requires an exact list or tuple")
    if len(additions) > context.block_count * context.action_count:
        raise StrictContractError(
            "candidate extension row count exceeds the exact table before allocation"
        )
    for index, row in enumerate(additions):
        _scan_interval_row(
            row,
            where=f"candidate extension row[{index}]",
            block_count=context.block_count,
        )

    # Consume additions as an exact-row-ordered subsequence.  The two-pointer
    # pass computes the final T and U exactly before building a map/list/tuple.
    addition_index = 0
    target_cells = 0
    union_cells = 0
    exact_rows = context.wire["rows"]
    for row_index in range(len(candidate.rows)):
        old_row = candidate.rows[row_index]
        exact_row = exact_rows[row_index]
        added_targets: tuple[int, ...] = ()
        if addition_index < len(additions):
            addition = additions[addition_index]
            if (
                addition.source_block_index == exact_row["source_block_index"]
                and addition.action_id == exact_row["action_id"]
            ):
                added_targets = addition.target_block_indices
                addition_index += 1
        exact_target = _nonnegative_int(
            exact_row["target_block_index"], "candidate extension exact target"
        )
        merged_count, contains_exact = _union_target_stats(
            old_row.target_block_indices,
            added_targets,
            exact_target=exact_target,
        )
        target_cells = _checked_add(
            target_cells, merged_count, "candidate extension target cells"
        )
        union_cells = _checked_add(
            union_cells,
            merged_count + (0 if contains_exact else 1),
            "candidate extension union cells",
        )
    if addition_index != len(additions):
        raise StrictContractError(
            "candidate extension rows are duplicated, reordered, or unknown"
        )
    _tier_work_units(
        total_members=context.total_members,
        block_count=context.block_count,
        action_count=context.action_count,
        target_cells=target_cells,
        union_cells=union_cells,
    )

    new_rows: list[IntervalTargetRow] = []
    addition_index = 0
    for row_index in range(len(candidate.rows)):
        old_row = candidate.rows[row_index]
        exact_row = exact_rows[row_index]
        added_targets = ()
        if addition_index < len(additions):
            addition = additions[addition_index]
            if (
                addition.source_block_index == exact_row["source_block_index"]
                and addition.action_id == exact_row["action_id"]
            ):
                added_targets = addition.target_block_indices
                addition_index += 1
        merged = _merge_target_tuples(old_row.target_block_indices, added_targets)
        new_rows.append(
            IntervalTargetRow(old_row.source_block_index, old_row.action_id, merged)
        )
    return _make_interval_candidate_with_context(
        context, tuple(new_rows), provenance_id=provenance_id
    )


@dataclass(frozen=True)
class UppernessEvidenceRow:
    source_block_index: int
    member_state_id: str
    action_id: str
    concrete_target_block_index: int

    def __post_init__(self) -> None:
        if type(self) is not UppernessEvidenceRow:
            raise StrictContractError("UppernessEvidenceRow subclasses are forbidden")
        _nonnegative_int(self.source_block_index, "upperness source block")
        _string(self.member_state_id, "upperness member state ID")
        _string(self.action_id, "upperness action ID")
        _signed64_target(
            self.concrete_target_block_index, "upperness concrete target block"
        )

    def to_dict(self) -> dict[str, Any]:
        if type(self) is not UppernessEvidenceRow:
            raise StrictContractError("upperness evidence row subclass is forbidden")
        _nonnegative_int(self.source_block_index, "upperness source block")
        _string(self.member_state_id, "upperness member state ID")
        _string(self.action_id, "upperness action ID")
        _signed64_target(
            self.concrete_target_block_index, "upperness concrete target block"
        )
        return {
            "schema_version": UPPERNESS_EVIDENCE_ROW_SCHEMA,
            "source_block_index": self.source_block_index,
            "member_state_id": self.member_state_id,
            "action_id": self.action_id,
            "concrete_target_block_index": self.concrete_target_block_index,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UppernessEvidenceRow":
        obj = _object(
            value,
            {
                "schema_version",
                "source_block_index",
                "member_state_id",
                "action_id",
                "concrete_target_block_index",
            },
            "UppernessEvidenceRow",
        )
        _fixed(
            obj["schema_version"],
            UPPERNESS_EVIDENCE_ROW_SCHEMA,
            "upperness evidence row schema",
        )
        result = cls(
            _nonnegative_int(obj["source_block_index"], "upperness source block"),
            _string(obj["member_state_id"], "upperness member state ID"),
            _string(obj["action_id"], "upperness action ID"),
            _signed64_target(
                obj["concrete_target_block_index"], "upperness target block"
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("upperness evidence row is not canonical")
        return result


def _evidence_payload(
    *,
    evidence_id: str,
    issuer: str,
    method: str,
    exact_operator_sha256: str,
    candidate_sha256: str,
    domain_payload_digest: str,
    observation_frame_digest: str,
    transition_semantics_digest: str,
    rows: Sequence[UppernessEvidenceRow],
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "issuer": issuer,
        "method": method,
        "exact_operator_sha256": exact_operator_sha256,
        "candidate_sha256": candidate_sha256,
        "domain_payload_digest": domain_payload_digest,
        "observation_frame_digest": observation_frame_digest,
        "transition_semantics_digest": transition_semantics_digest,
        "rows": [row.to_dict() for row in rows],
    }


@dataclass(frozen=True)
class UppernessDomainEvidence:
    evidence_id: str
    issuer: str
    method: str
    exact_operator_sha256: str
    candidate_sha256: str
    domain_payload_digest: str
    observation_frame_digest: str
    transition_semantics_digest: str
    rows: tuple[UppernessEvidenceRow, ...]
    evidence_payload_sha256: str

    def _validated_payload(self) -> dict[str, Any]:
        if type(self) is not UppernessDomainEvidence:
            raise StrictContractError("UppernessDomainEvidence subclasses are forbidden")
        for name in ("evidence_id", "issuer", "method"):
            _string(getattr(self, name), f"upperness {name}")
        for name in (
            "exact_operator_sha256",
            "candidate_sha256",
            "domain_payload_digest",
            "observation_frame_digest",
            "transition_semantics_digest",
            "evidence_payload_sha256",
        ):
            supplied = getattr(self, name)
            if supplied != _digest(supplied, name):
                raise StrictContractError(f"{name} is not canonical")
        if type(self.rows) is not tuple or not self.rows:
            raise StrictContractError("upperness evidence rows are not a nonempty tuple")
        if len(self.rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
            raise StrictContractError("upperness evidence row cap is exceeded")
        previous_key: tuple[int, str, str] | None = None
        for index, row in enumerate(self.rows):
            if type(row) is not UppernessEvidenceRow:
                raise StrictContractError("upperness evidence row is not strict")
            row.to_dict()
            key = (row.source_block_index, row.member_state_id, row.action_id)
            if previous_key is not None and key <= previous_key:
                raise StrictContractError(
                    "upperness evidence rows are not canonical and unique"
                )
            previous_key = key
        payload = _evidence_payload(
            evidence_id=self.evidence_id,
            issuer=self.issuer,
            method=self.method,
            exact_operator_sha256=self.exact_operator_sha256,
            candidate_sha256=self.candidate_sha256,
            domain_payload_digest=self.domain_payload_digest,
            observation_frame_digest=self.observation_frame_digest,
            transition_semantics_digest=self.transition_semantics_digest,
            rows=self.rows,
        )
        if self.evidence_payload_sha256 != _sha256(payload):
            raise StrictContractError("independent upperness evidence digest mismatch")
        return payload

    def __post_init__(self) -> None:
        if type(self) is not UppernessDomainEvidence:
            raise StrictContractError("UppernessDomainEvidence subclasses are forbidden")
        for name in ("evidence_id", "issuer", "method"):
            _string(getattr(self, name), f"upperness {name}")
        for name in (
            "exact_operator_sha256",
            "candidate_sha256",
            "domain_payload_digest",
            "observation_frame_digest",
            "transition_semantics_digest",
            "evidence_payload_sha256",
        ):
            object.__setattr__(self, name, _digest(getattr(self, name), name))
        self._validated_payload()

    def to_dict(self) -> dict[str, Any]:
        payload = self._validated_payload()
        return {
            "schema_version": UPPERNESS_DOMAIN_EVIDENCE_SCHEMA,
            **payload,
            "evidence_payload_sha256": self.evidence_payload_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UppernessDomainEvidence":
        obj = _object(
            value,
            {
                "schema_version",
                "evidence_id",
                "issuer",
                "method",
                "exact_operator_sha256",
                "candidate_sha256",
                "domain_payload_digest",
                "observation_frame_digest",
                "transition_semantics_digest",
                "rows",
                "evidence_payload_sha256",
            },
            "UppernessDomainEvidence",
        )
        _fixed(
            obj["schema_version"],
            UPPERNESS_DOMAIN_EVIDENCE_SCHEMA,
            "upperness evidence schema",
        )
        raw_rows = _array(obj["rows"], "upperness evidence rows")
        if not raw_rows or len(raw_rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
            raise StrictContractError("upperness evidence row count is outside the cap")
        result = cls(
            evidence_id=_string(obj["evidence_id"], "evidence ID"),
            issuer=_string(obj["issuer"], "evidence issuer"),
            method=_string(obj["method"], "evidence method"),
            exact_operator_sha256=_digest(
                obj["exact_operator_sha256"], "evidence exact operator digest"
            ),
            candidate_sha256=_digest(obj["candidate_sha256"], "candidate digest"),
            domain_payload_digest=_digest(
                obj["domain_payload_digest"], "evidence domain digest"
            ),
            observation_frame_digest=_digest(
                obj["observation_frame_digest"], "evidence frame digest"
            ),
            transition_semantics_digest=_digest(
                obj["transition_semantics_digest"], "evidence semantics digest"
            ),
            rows=tuple(UppernessEvidenceRow.from_dict(row) for row in raw_rows),
            evidence_payload_sha256=_digest(
                obj["evidence_payload_sha256"], "evidence payload digest"
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("upperness evidence wire is not canonical")
        return result


def _expected_evidence_rows(exact_wire: Mapping[str, Any]) -> tuple[UppernessEvidenceRow, ...]:
    rows: list[UppernessEvidenceRow] = []
    for quotient_row in exact_wire["rows"]:
        for member in quotient_row["member_transitions"]:
            rows.append(
                UppernessEvidenceRow(
                    source_block_index=quotient_row["source_block_index"],
                    member_state_id=member["source_state_id"],
                    action_id=quotient_row["action_id"],
                    concrete_target_block_index=quotient_row["target_block_index"],
                )
            )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.source_block_index,
                row.member_state_id,
                row.action_id,
            ),
        )
    )


def _fresh_candidate_with_context(
    candidate: IntervalCandidate, context: _ExactContext
) -> IntervalCandidate:
    if type(candidate) is not IntervalCandidate:
        raise StrictContractError("upperness verification requires a strict candidate")
    work = _validate_candidate_object_with_context(candidate, context)
    fresh = IntervalCandidate(
        context.operator_sha256,
        candidate.provenance_id,
        candidate.rows,
        work,
    )
    if fresh.to_dict() != candidate.to_dict():
        raise StrictContractError("candidate object does not match fresh source-bound validation")
    return fresh


def _derive_witness_wire_with_context(
    context: _ExactContext,
    candidate: IntervalCandidate,
    evidence: UppernessDomainEvidence,
) -> dict[str, Any]:
    exact_wire = context.wire
    candidate_fresh = _fresh_candidate_with_context(candidate, context)
    evidence_fresh = UppernessDomainEvidence.from_dict(evidence.to_dict())
    if evidence_fresh.exact_operator_sha256 != context.operator_sha256:
        raise StrictContractError("upperness evidence binds a different exact operator")
    if evidence_fresh.candidate_sha256 != candidate_fresh.candidate_sha256:
        raise StrictContractError("upperness evidence binds a different candidate")
    for name in (
        "domain_payload_digest",
        "observation_frame_digest",
        "transition_semantics_digest",
    ):
        if getattr(evidence_fresh, name) != exact_wire[name]:
            raise StrictContractError(f"upperness evidence {name} binding mismatch")
    expected_rows = _expected_evidence_rows(exact_wire)
    if evidence_fresh.rows != expected_rows:
        raise StrictContractError(
            "upperness evidence does not cover every exact member/action transition"
        )

    exact_targets = _exact_target_map(exact_wire)
    for row in candidate_fresh.rows:
        exact_target = exact_targets[(row.source_block_index, row.action_id)]
        if exact_target not in row.target_block_indices:
            raise StrictContractError("candidate interval undercovers an exact successor")
    _, work = _validate_candidate_rows_with_context(context, candidate_fresh.rows)
    if work != candidate_fresh.work_units:
        raise StrictContractError("candidate work accounting changed")
    return {
        "schema_version": UPPERNESS_DOMAIN_WITNESS_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "witness_kind": "complete_member_action_structural_containment",
        "exact_operator_sha256": context.operator_sha256,
        "candidate_sha256": candidate_fresh.candidate_sha256,
        "evidence_payload_sha256": evidence_fresh.evidence_payload_sha256,
        "work_units": work,
        "covered_member_action_count": len(expected_rows),
        "checks": [
            "fresh_exact_partition_verification",
            "complete_totalized_member_action_coverage",
            "source_frame_semantics_binding",
            "candidate_exact_successor_containment",
            "signed64_then_domain_target_validation",
            "combined_preallocation_work_cap",
        ],
    }


def _derive_witness_wire(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    evidence: UppernessDomainEvidence,
) -> dict[str, Any]:
    return _derive_witness_wire_with_context(
        _exact_context(exact), candidate, evidence
    )


@dataclass(frozen=True)
class UppernessDomainWitness:
    _exact_source: ExactFiniteOperator = field(repr=False)
    _candidate_source: IntervalCandidate = field(repr=False)
    _evidence_source: UppernessDomainEvidence = field(repr=False)
    _exact_seal_sha256: str = field(repr=False)
    _candidate_seal_sha256: str = field(repr=False)
    _evidence_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not UppernessDomainWitness:
            raise StrictContractError("UppernessDomainWitness subclasses are forbidden")
        if self._construction_seal is not _WITNESS_SEAL:
            raise StrictContractError("upperness witness requires independent verification")
        if type(self._exact_source) is not ExactFiniteOperator:
            raise StrictContractError("witness exact source is not strict")
        if type(self._candidate_source) is not IntervalCandidate:
            raise StrictContractError("witness candidate source is not strict")
        if type(self._evidence_source) is not UppernessDomainEvidence:
            raise StrictContractError("witness evidence source is not strict")
        for name in (
            "_exact_seal_sha256",
            "_candidate_seal_sha256",
            "_evidence_seal_sha256",
        ):
            _digest(getattr(self, name), name)

    @classmethod
    def verify(
        cls,
        exact: ExactFiniteOperator,
        candidate: IntervalCandidate,
        evidence: UppernessDomainEvidence,
    ) -> "UppernessDomainWitness":
        if cls is not UppernessDomainWitness:
            raise StrictContractError("polymorphic upperness verification is forbidden")
        wire = _derive_witness_wire(exact, candidate, evidence)
        return cls(
            exact,
            candidate,
            evidence,
            wire["exact_operator_sha256"],
            wire["candidate_sha256"],
            _sha256(evidence.to_dict()),
            _construction_seal=_WITNESS_SEAL,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        exact: ExactFiniteOperator,
        candidate: IntervalCandidate,
        evidence: UppernessDomainEvidence,
    ) -> "UppernessDomainWitness":
        if cls is not UppernessDomainWitness:
            raise StrictContractError("polymorphic witness parsing is forbidden")
        expected_wire = _derive_witness_wire(exact, candidate, evidence)
        obj = _object(value, set(expected_wire), "UppernessDomainWitness")
        if canonical_contract_bytes(obj) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("witness wire does not match external authorities")
        return cls(
            exact,
            candidate,
            evidence,
            expected_wire["exact_operator_sha256"],
            expected_wire["candidate_sha256"],
            _sha256(evidence.to_dict()),
            _construction_seal=_WITNESS_SEAL,
        )

    @property
    def witness_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _WITNESS_SEAL:
            raise StrictContractError("upperness witness construction seal changed")
        context = _exact_context(self._exact_source)
        if context.operator_sha256 != _digest(
            self._exact_seal_sha256, "witness exact seal"
        ):
            raise StrictContractError("witness exact source changed")
        if self._candidate_source.candidate_sha256 != _digest(
            self._candidate_seal_sha256, "witness candidate seal"
        ):
            raise StrictContractError("witness candidate source changed")
        if _sha256(self._evidence_source.to_dict()) != _digest(
            self._evidence_seal_sha256, "witness evidence seal"
        ):
            raise StrictContractError("witness evidence source changed")
        return _derive_witness_wire_with_context(
            context, self._candidate_source, self._evidence_source
        )


def verify_upperness_domain(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    evidence: UppernessDomainEvidence,
) -> UppernessDomainWitness:
    return UppernessDomainWitness.verify(exact, candidate, evidence)


def _derive_certified_wire(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    witness: UppernessDomainWitness,
) -> dict[str, Any]:
    context = _exact_context(exact)
    exact_wire = context.wire
    candidate_fresh = _fresh_candidate_with_context(candidate, context)
    if type(witness) is not UppernessDomainWitness:
        raise StrictContractError("certification requires a verified upperness witness")
    witness_wire = witness.to_dict()
    if witness_wire["exact_operator_sha256"] != context.operator_sha256:
        raise StrictContractError("witness binds a different exact operator")
    if witness_wire["candidate_sha256"] != candidate_fresh.candidate_sha256:
        raise StrictContractError("witness binds a different candidate")
    return {
        "schema_version": CERTIFIED_INTERVAL_OPERATOR_SCHEMA,
        "operator_tier": CERTIFIED_OPERATOR_TIER,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "exact_operator_sha256": context.operator_sha256,
        "candidate_sha256": candidate_fresh.candidate_sha256,
        "upperness_witness_sha256": _sha256(witness_wire),
        "domain_payload_digest": exact_wire["domain_payload_digest"],
        "observation_frame_digest": exact_wire["observation_frame_digest"],
        "transition_semantics_digest": exact_wire["transition_semantics_digest"],
        "response_vocabulary_digest": exact_wire["response_vocabulary_digest"],
        "work_units": candidate_fresh.work_units,
        "rows": [row.to_dict() for row in candidate_fresh.rows],
    }


@dataclass(frozen=True)
class CertifiedIntervalOperator:
    _exact_source: ExactFiniteOperator = field(repr=False)
    _candidate_source: IntervalCandidate = field(repr=False)
    _witness_source: UppernessDomainWitness = field(repr=False)
    _exact_seal_sha256: str = field(repr=False)
    _candidate_seal_sha256: str = field(repr=False)
    _witness_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self) is not CertifiedIntervalOperator:
            raise StrictContractError("CertifiedIntervalOperator subclasses are forbidden")
        if self._construction_seal is not _CERTIFIED_SEAL:
            raise StrictContractError("certified interval requires the certification gate")
        if type(self._exact_source) is not ExactFiniteOperator:
            raise StrictContractError("certified exact source is not strict")
        if type(self._candidate_source) is not IntervalCandidate:
            raise StrictContractError("certified candidate source is not strict")
        if type(self._witness_source) is not UppernessDomainWitness:
            raise StrictContractError("certified witness source is not strict")
        for name in (
            "_exact_seal_sha256",
            "_candidate_seal_sha256",
            "_witness_seal_sha256",
        ):
            _digest(getattr(self, name), name)

    @classmethod
    def certify(
        cls,
        exact: ExactFiniteOperator,
        candidate: IntervalCandidate,
        witness: UppernessDomainWitness,
    ) -> "CertifiedIntervalOperator":
        if cls is not CertifiedIntervalOperator:
            raise StrictContractError("polymorphic certification is forbidden")
        wire = _derive_certified_wire(exact, candidate, witness)
        return cls(
            exact,
            candidate,
            witness,
            wire["exact_operator_sha256"],
            wire["candidate_sha256"],
            wire["upperness_witness_sha256"],
            _construction_seal=_CERTIFIED_SEAL,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        exact: ExactFiniteOperator,
        candidate: IntervalCandidate,
        witness: UppernessDomainWitness,
    ) -> "CertifiedIntervalOperator":
        if cls is not CertifiedIntervalOperator:
            raise StrictContractError("polymorphic certified parsing is forbidden")
        expected_wire = _derive_certified_wire(exact, candidate, witness)
        obj = _object(value, set(expected_wire), "CertifiedIntervalOperator")
        if canonical_contract_bytes(obj) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("certified wire does not match external authorities")
        return cls(
            exact,
            candidate,
            witness,
            expected_wire["exact_operator_sha256"],
            expected_wire["candidate_sha256"],
            expected_wire["upperness_witness_sha256"],
            _construction_seal=_CERTIFIED_SEAL,
        )

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _CERTIFIED_SEAL:
            raise StrictContractError("certified operator construction seal changed")
        wire = _derive_certified_wire(
            self._exact_source, self._candidate_source, self._witness_source
        )
        if wire["exact_operator_sha256"] != _digest(
            self._exact_seal_sha256, "certified exact seal"
        ):
            raise StrictContractError("certified exact source changed")
        if wire["candidate_sha256"] != _digest(
            self._candidate_seal_sha256, "certified candidate seal"
        ):
            raise StrictContractError("certified candidate source changed")
        if wire["upperness_witness_sha256"] != _digest(
            self._witness_seal_sha256, "certified witness seal"
        ):
            raise StrictContractError("certified witness source changed")
        return wire


def certify_interval_operator(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    witness: UppernessDomainWitness,
) -> CertifiedIntervalOperator:
    return CertifiedIntervalOperator.certify(exact, candidate, witness)


def _preflight_standalone_rows(
    rows: tuple[IntervalTargetRow, ...], *, where: str
) -> None:
    if type(rows) is not tuple or not rows:
        raise StrictContractError(f"{where} rows are not a strict nonempty tuple")
    if len(rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
        raise StrictContractError(f"{where} row count exceeds the finite table cap")
    target_cells = 0
    for row in rows:
        if type(row) is not IntervalTargetRow:
            raise StrictContractError(f"{where} row is not strict")
        if type(row.target_block_indices) is not tuple:
            raise StrictContractError(f"{where} targets are not exact tuples")
        target_cells = _checked_add(
            target_cells, len(row.target_block_indices), f"{where} target cells"
        )
    for index, row in enumerate(rows):
        _scan_interval_row(row, where=f"{where} row[{index}]")


def _preflight_raw_standalone_rows(raw_rows: list[Any], *, where: str) -> None:
    if not raw_rows:
        raise StrictContractError(f"{where} rows must be nonempty")
    if len(raw_rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
        raise StrictContractError(f"{where} row count exceeds the finite table cap")
    target_cells = 0
    for index, raw_row in enumerate(raw_rows):
        row_obj = _object_without_set(
            raw_row, _INTERVAL_ROW_FIELDS, f"{where} raw row[{index}]"
        )
        raw_targets = row_obj["target_block_indices"]
        if type(raw_targets) is not list:
            raise StrictContractError(f"{where} raw targets must be exact arrays")
        if not raw_targets:
            raise StrictContractError(f"{where} raw targets must be nonempty")
        target_cells = _checked_add(
            target_cells, len(raw_targets), f"{where} raw target cells"
        )
    for index, raw_row in enumerate(raw_rows):
        row_obj = _object_without_set(
            raw_row, _INTERVAL_ROW_FIELDS, f"{where} raw row[{index}]"
        )
        _fixed(
            row_obj["schema_version"],
            INTERVAL_TARGET_ROW_SCHEMA,
            f"{where} raw row[{index}] schema",
        )
        _nonnegative_int(
            row_obj["source_block_index"], f"{where} raw row[{index}] source"
        )
        _string(row_obj["action_id"], f"{where} raw row[{index}] action")
        _scan_interval_targets(
            row_obj["target_block_indices"],
            required_container_type=list,
            where=f"{where} raw row[{index}] targets",
        )


@dataclass(frozen=True)
class ObservedIntervalOperator:
    observation_id: str
    rows: tuple[IntervalTargetRow, ...]
    evidence_scope: str = OBSERVED_OPERATOR_TIER

    def __post_init__(self) -> None:
        if type(self) is not ObservedIntervalOperator:
            raise StrictContractError("ObservedIntervalOperator subclasses are forbidden")
        _string(self.observation_id, "observation ID")
        _fixed(self.evidence_scope, OBSERVED_OPERATOR_TIER, "observed evidence scope")
        _preflight_standalone_rows(self.rows, where="observed")

    def to_dict(self) -> dict[str, Any]:
        _string(self.observation_id, "observation ID")
        _fixed(self.evidence_scope, OBSERVED_OPERATOR_TIER, "observed evidence scope")
        _preflight_standalone_rows(self.rows, where="observed")
        return {
            "schema_version": OBSERVED_INTERVAL_OPERATOR_SCHEMA,
            "operator_tier": OBSERVED_OPERATOR_TIER,
            "evidence_scope": self.evidence_scope,
            "observation_id": self.observation_id,
            "rows": [row.to_dict() for row in self.rows],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservedIntervalOperator":
        obj = _object(
            value,
            {"schema_version", "operator_tier", "evidence_scope", "observation_id", "rows"},
            "ObservedIntervalOperator",
        )
        _fixed(obj["schema_version"], OBSERVED_INTERVAL_OPERATOR_SCHEMA, "observed schema")
        _fixed(obj["operator_tier"], OBSERVED_OPERATOR_TIER, "observed tier")
        raw_rows = _array(obj["rows"], "observed rows")
        _preflight_raw_standalone_rows(raw_rows, where="observed")
        rows = tuple(IntervalTargetRow.from_dict(row) for row in raw_rows)
        result = cls(
            _string(obj["observation_id"], "observation ID"),
            rows,
            _fixed(obj["evidence_scope"], OBSERVED_OPERATOR_TIER, "observed evidence scope"),
        )
        if result.to_dict() != obj:
            raise StrictContractError("observed interval wire is not canonical")
        return result


@dataclass(frozen=True)
class NominalOperator:
    model_id: str
    support_rows: tuple[IntervalTargetRow, ...]
    evidence_scope: str = NOMINAL_OPERATOR_TIER

    def __post_init__(self) -> None:
        if type(self) is not NominalOperator:
            raise StrictContractError("NominalOperator subclasses are forbidden")
        _string(self.model_id, "nominal model ID")
        _fixed(self.evidence_scope, NOMINAL_OPERATOR_TIER, "nominal evidence scope")
        _preflight_standalone_rows(self.support_rows, where="nominal")

    def to_dict(self) -> dict[str, Any]:
        _string(self.model_id, "nominal model ID")
        _fixed(self.evidence_scope, NOMINAL_OPERATOR_TIER, "nominal evidence scope")
        _preflight_standalone_rows(self.support_rows, where="nominal")
        return {
            "schema_version": NOMINAL_OPERATOR_SCHEMA,
            "operator_tier": NOMINAL_OPERATOR_TIER,
            "evidence_scope": self.evidence_scope,
            "model_id": self.model_id,
            "support_rows": [row.to_dict() for row in self.support_rows],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NominalOperator":
        obj = _object(
            value,
            {"schema_version", "operator_tier", "evidence_scope", "model_id", "support_rows"},
            "NominalOperator",
        )
        _fixed(obj["schema_version"], NOMINAL_OPERATOR_SCHEMA, "nominal schema")
        _fixed(obj["operator_tier"], NOMINAL_OPERATOR_TIER, "nominal tier")
        raw_rows = _array(obj["support_rows"], "nominal support rows")
        _preflight_raw_standalone_rows(raw_rows, where="nominal")
        rows = tuple(IntervalTargetRow.from_dict(row) for row in raw_rows)
        result = cls(
            _string(obj["model_id"], "nominal model ID"),
            rows,
            _fixed(obj["evidence_scope"], NOMINAL_OPERATOR_TIER, "nominal evidence scope"),
        )
        if result.to_dict() != obj:
            raise StrictContractError("nominal wire is not canonical")
        return result


__all__ = [
    "CERTIFIED_OPERATOR_TIER",
    "EXACT_OPERATOR_TIER",
    "MAX_SIGNED_64",
    "MAX_TIER_FIREWALL_WORK_UNITS",
    "NOMINAL_OPERATOR_TIER",
    "OBSERVED_OPERATOR_TIER",
    "CertifiedIntervalOperator",
    "ExactFiniteOperator",
    "IntervalCandidate",
    "IntervalTargetRow",
    "NominalOperator",
    "ObservedIntervalOperator",
    "UppernessDomainEvidence",
    "UppernessDomainWitness",
    "UppernessEvidenceRow",
    "certify_interval_operator",
    "export_exact_finite_operator",
    "extend_interval_candidate",
    "make_interval_candidate",
    "verify_upperness_domain",
]
