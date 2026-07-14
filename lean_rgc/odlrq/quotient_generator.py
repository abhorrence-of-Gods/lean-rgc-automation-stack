"""Strict finite quotient export and evidence-tier firewall.

This module is development-only.  ``CertifiedIntervalOperator`` certifies
structural successor containment on one complete synthetic finite source.  It
is not a positive envelope, a numeric upper bound, or production Lean evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

from .adapters import ExactAdmissionCompletionGate
from .behavioral_partition import VerifiedExactPartition, verify_exact_partition
from .contracts import (
    ExactRational,
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

POSITIVE_FIBER_WEIGHTS_SCHEMA = "odlrq_positive_fiber_weights_v1"
EXACT_FINITE_FIBER_LAW_SCHEMA = "odlrq_exact_finite_fiber_law_v1"
WEIGHTED_COMPRESSION_SCHEMA = "odlrq_weighted_compression_v1"
WEIGHTED_LIFTING_SCHEMA = "odlrq_weighted_lifting_v1"

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

_EXACT_QUOTIENT_COORDINATE_TERM_SCHEMA = (
    "odlrq_exact_quotient_coordinate_term_v1"
)
_EXACT_QUOTIENT_TRANSFER_ROW_SCHEMA = "odlrq_exact_quotient_transfer_row_v1"
_EXACT_QUOTIENT_COORDINATE_GENERATOR_SCHEMA = (
    "odlrq_exact_quotient_coordinate_generator_v1"
)
_EXACT_QUOTIENT_DOMAIN_SCOPE = "declared_finite_totalized_snapshot_only"
_EXACT_QUOTIENT_BASIS_CONVENTION = "block_basis_column_source_v1"
_EXACT_QUOTIENT_GENERATOR_CONVENTION = "P_action_minus_identity_v1"
_EXACT_QUOTIENT_SOURCE_SEAL_VERSION = (
    "odlrq_exact_quotient_coordinate_source_seal_v1"
)
_MAX_EXACT_QUOTIENT_TERMS = 4_096
_MAX_EXACT_RATIONAL_DECIMAL_DIGITS = 2_467
_MAX_FIBER_MEMBERS = 128
_MAX_FIBER_BLOCKS = 64
_EXACT_QUOTIENT_GENERATOR_SEAL = object()
_POSITIVE_FIBER_WEIGHTS_SEAL = object()
_EXACT_FINITE_FIBER_LAW_SEAL = object()
_WEIGHTED_COMPRESSION_SEAL = object()
_WEIGHTED_LIFTING_SEAL = object()

_EXACT_QUOTIENT_TERM_FIELDS = (
    "schema_version",
    "evidence_scope",
    "domain_scope",
    "target_block_index",
    "coefficient",
)
_EXACT_QUOTIENT_ROW_FIELDS = (
    "schema_version",
    "evidence_scope",
    "domain_scope",
    "source_block_index",
    "action_id",
    "action_sha256",
    "structural_target_block_index",
    "member_transition_count",
    "member_transition_sha256",
    "terms",
)
_EXACT_QUOTIENT_GENERATOR_FIELDS = (
    "schema_version",
    "evidence_scope",
    "domain_scope",
    "basis_convention",
    "generator_convention",
    "admission_report_sha256",
    "snapshot_sha256",
    "environment_digest",
    "reachable_domain_sha256",
    "domain_payload_digest",
    "seed_set_digest",
    "observation_frame_digest",
    "transition_semantics_digest",
    "response_vocabulary_digest",
    "action_alphabet_digest",
    "synthetic_evidence_profile_sha256",
    "verified_partition_sha256",
    "exact_operator_sha256",
    "canonical_block_order_sha256",
    "canonical_action_order_sha256",
    "source_seal_sha256",
    "totalized_state_count",
    "block_count",
    "action_count",
    "canonical_block_indices",
    "canonical_action_ids",
    "row_count",
    "term_count",
    "member_action_witness_count",
    "work_units",
    "rows",
)
_EXACT_OPERATOR_MEMBER_ROW_FIELDS = (
    "source_block_index",
    "action_id",
    "action_sha256",
    "target_block_index",
    "member_transition_count",
    "member_transitions",
)


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


def _canonical_digest(value: Any, where: str) -> str:
    result = _digest(value, where)
    if value != result:
        raise StrictContractError(f"{where} must use canonical uppercase hex")
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


def _fresh_exact_quotient_verified(
    source: VerifiedExactPartition,
) -> VerifiedExactPartition:
    if type(source) is not VerifiedExactPartition:
        raise StrictContractError(
            "exact quotient generator requires an exact VerifiedExactPartition"
        )
    try:
        fresh_admitted = ExactAdmissionCompletionGate.admit(source.admitted.snapshot)
        if canonical_contract_bytes(
            fresh_admitted.to_dict()
        ) != canonical_contract_bytes(source.admitted.to_dict()):
            raise StrictContractError(
                "verified partition admitted source does not match fresh exact admission"
            )
        fresh = verify_exact_partition(fresh_admitted, source.certificate)
        if canonical_contract_bytes(fresh.to_dict()) != canonical_contract_bytes(
            source.to_dict()
        ):
            raise StrictContractError(
                "verified partition source does not match fresh exact verification"
            )
        return fresh
    except StrictContractError:
        raise
    except Exception as exc:
        raise StrictContractError(
            "exact quotient verified source cannot be freshly rederived"
        ) from exc


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
        if type(source) is not VerifiedExactPartition:
            raise StrictContractError(
                "exact operator export requires an exact VerifiedExactPartition"
            )
        # __post_init__ is the single fresh admission for this typed export.
        # Hashing the supplied immutable wire here gives it the comparison seal
        # without running the identical verifier twice in one construction.
        seal = _sha256(source.to_dict())
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


def _fresh_exact_quotient_export(
    source: VerifiedExactPartition,
) -> tuple[
    VerifiedExactPartition,
    dict[str, Any],
    tuple[int, int, int, int, int, int],
]:
    """Indivisibly reverify E0, construct its typed predecessor, and consume it."""

    # No reusable token or arbitrary-fresh constructor exists: the stronger
    # admission/partition verifier and the sealed capability construction are
    # one local transaction over the caller-supplied retained source.
    fresh = _fresh_exact_quotient_verified(source)
    dimensions = _preflight_exact_quotient_dimensions(fresh)
    exact = object.__new__(ExactFiniteOperator)
    object.__setattr__(exact, "_verified_source", fresh)
    object.__setattr__(exact, "_source_seal_sha256", _sha256(fresh.to_dict()))
    object.__setattr__(exact, "_construction_seal", _EXACT_SEAL)
    if (
        type(exact) is not ExactFiniteOperator
        or exact._construction_seal is not _EXACT_SEAL
        or exact._verified_source is not fresh
        or _canonical_digest(
            exact._source_seal_sha256, "fresh exact export source seal"
        )
        != _sha256(fresh.to_dict())
    ):
        raise StrictContractError("fresh exact export capability construction failed")
    return fresh, _derive_exact_wire_from_fresh(fresh), dimensions


@dataclass(frozen=True)
class ExactQuotientCoordinateTerm:
    target_block_index: int
    coefficient: ExactRational
    evidence_scope: str = field(default=SYNTHETIC_EVIDENCE_SCOPE, init=False)
    domain_scope: str = field(default=_EXACT_QUOTIENT_DOMAIN_SCOPE, init=False)

    def __post_init__(self) -> None:
        if type(self) is not ExactQuotientCoordinateTerm:
            raise StrictContractError(
                "ExactQuotientCoordinateTerm subclasses are forbidden"
            )
        _nonnegative_int(
            self.target_block_index, "exact quotient term target_block_index"
        )
        if type(self.coefficient) is not ExactRational:
            raise StrictContractError(
                "exact quotient term coefficient must be an ExactRational"
            )
        if self.coefficient.numerator == 0:
            raise StrictContractError("exact quotient term coefficient must be nonzero")
        if ExactRational.from_dict(self.coefficient.to_dict()) != self.coefficient:
            raise StrictContractError(
                "exact quotient term coefficient is not reduced canonical authority"
            )
        _fixed(
            self.evidence_scope,
            SYNTHETIC_EVIDENCE_SCOPE,
            "exact quotient term evidence_scope",
        )
        _fixed(
            self.domain_scope,
            _EXACT_QUOTIENT_DOMAIN_SCOPE,
            "exact quotient term domain_scope",
        )

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _EXACT_QUOTIENT_COORDINATE_TERM_SCHEMA,
            "evidence_scope": self.evidence_scope,
            "domain_scope": self.domain_scope,
            "target_block_index": self.target_block_index,
            "coefficient": self.coefficient.to_dict(),
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "ExactQuotientCoordinateTerm":
        if cls is not ExactQuotientCoordinateTerm:
            raise StrictContractError(
                "polymorphic exact quotient term parsing is forbidden"
            )
        obj = _object_without_set(
            value, _EXACT_QUOTIENT_TERM_FIELDS, "ExactQuotientCoordinateTerm"
        )
        _fixed(
            obj["schema_version"],
            _EXACT_QUOTIENT_COORDINATE_TERM_SCHEMA,
            "ExactQuotientCoordinateTerm schema",
        )
        _fixed(
            obj["evidence_scope"],
            SYNTHETIC_EVIDENCE_SCOPE,
            "exact quotient term evidence_scope",
        )
        _fixed(
            obj["domain_scope"],
            _EXACT_QUOTIENT_DOMAIN_SCOPE,
            "exact quotient term domain_scope",
        )
        result = cls(
            target_block_index=_nonnegative_int(
                obj["target_block_index"],
                "exact quotient term target_block_index",
            ),
            coefficient=ExactRational.from_dict(obj["coefficient"]),
        )
        if result.to_dict() != obj:
            raise StrictContractError(
                "ExactQuotientCoordinateTerm wire is not canonical"
            )
        return result


def _expected_exact_quotient_terms(
    source_block_index: int, structural_target_block_index: int
) -> tuple[ExactQuotientCoordinateTerm, ...]:
    if source_block_index == structural_target_block_index:
        return ()
    return tuple(
        sorted(
            (
                ExactQuotientCoordinateTerm(
                    source_block_index, ExactRational(-1)
                ),
                ExactQuotientCoordinateTerm(
                    structural_target_block_index, ExactRational(1)
                ),
            ),
            key=lambda term: term.target_block_index,
        )
    )


@dataclass(frozen=True)
class ExactQuotientTransferRow:
    source_block_index: int
    action_id: str
    action_sha256: str
    structural_target_block_index: int
    member_transition_count: int
    member_transition_sha256: str
    terms: tuple[ExactQuotientCoordinateTerm, ...]
    evidence_scope: str = field(default=SYNTHETIC_EVIDENCE_SCOPE, init=False)
    domain_scope: str = field(default=_EXACT_QUOTIENT_DOMAIN_SCOPE, init=False)

    def __post_init__(self) -> None:
        if type(self) is not ExactQuotientTransferRow:
            raise StrictContractError(
                "ExactQuotientTransferRow subclasses are forbidden"
            )
        _nonnegative_int(
            self.source_block_index, "exact quotient row source_block_index"
        )
        _string(self.action_id, "exact quotient row action_id")
        _canonical_digest(self.action_sha256, "exact quotient row action_sha256")
        _nonnegative_int(
            self.structural_target_block_index,
            "exact quotient row structural_target_block_index",
        )
        member_count = _nonnegative_int(
            self.member_transition_count,
            "exact quotient row member_transition_count",
            upper=MAX_SYNTHETIC_TOTALIZED_STATES,
        )
        if member_count == 0:
            raise StrictContractError(
                "exact quotient row must retain a member transition"
            )
        _canonical_digest(
            self.member_transition_sha256,
            "exact quotient row member_transition_sha256",
        )
        if (
            type(self.terms) is not tuple
            or len(self.terms) > 2
            or not all(type(term) is ExactQuotientCoordinateTerm for term in self.terms)
        ):
            raise StrictContractError(
                "exact quotient row terms must be an exact bounded tuple"
            )
        expected_terms = _expected_exact_quotient_terms(
            self.source_block_index, self.structural_target_block_index
        )
        if self.terms != expected_terms:
            raise StrictContractError(
                "exact quotient row terms do not equal P_action minus identity"
            )
        _fixed(
            self.evidence_scope,
            SYNTHETIC_EVIDENCE_SCOPE,
            "exact quotient row evidence_scope",
        )
        _fixed(
            self.domain_scope,
            _EXACT_QUOTIENT_DOMAIN_SCOPE,
            "exact quotient row domain_scope",
        )

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": _EXACT_QUOTIENT_TRANSFER_ROW_SCHEMA,
            "evidence_scope": self.evidence_scope,
            "domain_scope": self.domain_scope,
            "source_block_index": self.source_block_index,
            "action_id": self.action_id,
            "action_sha256": self.action_sha256,
            "structural_target_block_index": self.structural_target_block_index,
            "member_transition_count": self.member_transition_count,
            "member_transition_sha256": self.member_transition_sha256,
            "terms": [term.to_dict() for term in self.terms],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactQuotientTransferRow":
        if cls is not ExactQuotientTransferRow:
            raise StrictContractError(
                "polymorphic exact quotient row parsing is forbidden"
            )
        obj = _object_without_set(
            value, _EXACT_QUOTIENT_ROW_FIELDS, "ExactQuotientTransferRow"
        )
        raw_terms = _array(obj["terms"], "exact quotient row terms")
        if len(raw_terms) > 2:
            raise StrictContractError("exact quotient row has more than two terms")
        _fixed(
            obj["schema_version"],
            _EXACT_QUOTIENT_TRANSFER_ROW_SCHEMA,
            "ExactQuotientTransferRow schema",
        )
        _fixed(
            obj["evidence_scope"],
            SYNTHETIC_EVIDENCE_SCOPE,
            "exact quotient row evidence_scope",
        )
        _fixed(
            obj["domain_scope"],
            _EXACT_QUOTIENT_DOMAIN_SCOPE,
            "exact quotient row domain_scope",
        )
        result = cls(
            source_block_index=_nonnegative_int(
                obj["source_block_index"],
                "exact quotient row source_block_index",
            ),
            action_id=_string(obj["action_id"], "exact quotient row action_id"),
            action_sha256=_canonical_digest(
                obj["action_sha256"], "exact quotient row action_sha256"
            ),
            structural_target_block_index=_nonnegative_int(
                obj["structural_target_block_index"],
                "exact quotient row structural_target_block_index",
            ),
            member_transition_count=_nonnegative_int(
                obj["member_transition_count"],
                "exact quotient row member_transition_count",
                upper=MAX_SYNTHETIC_TOTALIZED_STATES,
            ),
            member_transition_sha256=_canonical_digest(
                obj["member_transition_sha256"],
                "exact quotient row member_transition_sha256",
            ),
            terms=tuple(
                ExactQuotientCoordinateTerm.from_dict(term) for term in raw_terms
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactQuotientTransferRow wire is not canonical")
        return result


def _preflight_exact_quotient_generator_wire(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    obj = _object_without_set(
        value,
        _EXACT_QUOTIENT_GENERATOR_FIELDS,
        "ExactQuotientCoordinateGenerator",
    )
    for field_name in (
        "schema_version",
        "evidence_scope",
        "domain_scope",
        "basis_convention",
        "generator_convention",
    ):
        _string(obj[field_name], f"exact quotient {field_name}")
    for field_name in (
        "admission_report_sha256",
        "snapshot_sha256",
        "environment_digest",
        "reachable_domain_sha256",
        "domain_payload_digest",
        "seed_set_digest",
        "observation_frame_digest",
        "transition_semantics_digest",
        "response_vocabulary_digest",
        "action_alphabet_digest",
        "synthetic_evidence_profile_sha256",
        "verified_partition_sha256",
        "exact_operator_sha256",
        "canonical_block_order_sha256",
        "canonical_action_order_sha256",
        "source_seal_sha256",
    ):
        digest = obj[field_name]
        if type(digest) is not str or len(digest) != 64:
            raise StrictContractError(
                f"exact quotient {field_name} must be an exact 64-character string"
            )
    raw_block_indices = _array(
        obj["canonical_block_indices"], "exact quotient canonical_block_indices"
    )
    raw_action_ids = _array(
        obj["canonical_action_ids"], "exact quotient canonical_action_ids"
    )
    raw_rows = _array(obj["rows"], "exact quotient generator rows")
    if len(raw_block_indices) > MAX_SYNTHETIC_TOTALIZED_STATES:
        raise StrictContractError("exact quotient block-order cap is exceeded")
    if len(raw_action_ids) > MAX_SYNTHETIC_ACTIONS:
        raise StrictContractError("exact quotient action-order cap is exceeded")
    if len(raw_rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
        raise StrictContractError("exact quotient row cap is exceeded")

    for field_name in (
        "totalized_state_count",
        "block_count",
        "action_count",
        "row_count",
        "term_count",
        "member_action_witness_count",
        "work_units",
    ):
        _nonnegative_int(obj[field_name], f"exact quotient {field_name}")
    for block_index in raw_block_indices:
        _nonnegative_int(block_index, "exact quotient canonical block index")
    for action_id in raw_action_ids:
        if type(action_id) is not str or not action_id:
            raise StrictContractError(
                "exact quotient canonical action IDs must be exact strings"
            )

    cumulative_terms = 0
    for row_index, raw_row in enumerate(raw_rows):
        row = _object_without_set(
            raw_row,
            _EXACT_QUOTIENT_ROW_FIELDS,
            f"exact quotient row {row_index}",
        )
        for field_name in (
            "schema_version",
            "evidence_scope",
            "domain_scope",
            "action_id",
        ):
            _string(
                row[field_name],
                f"exact quotient row {row_index} {field_name}",
            )
        for field_name in ("action_sha256", "member_transition_sha256"):
            digest = row[field_name]
            if type(digest) is not str or len(digest) != 64:
                raise StrictContractError(
                    f"exact quotient row {row_index} {field_name} must be an exact "
                    "64-character string"
                )
        for field_name in (
            "source_block_index",
            "structural_target_block_index",
            "member_transition_count",
        ):
            _nonnegative_int(
                row[field_name], f"exact quotient row {row_index} {field_name}"
            )
        raw_terms = _array(row["terms"], f"exact quotient row {row_index} terms")
        if len(raw_terms) > 2:
            raise StrictContractError("exact quotient row has more than two raw terms")
        cumulative_terms += len(raw_terms)
        if cumulative_terms > _MAX_EXACT_QUOTIENT_TERMS:
            raise StrictContractError("exact quotient cumulative term cap is exceeded")
        for term_index, raw_term in enumerate(raw_terms):
            term = _object_without_set(
                raw_term,
                _EXACT_QUOTIENT_TERM_FIELDS,
                f"exact quotient row {row_index} term {term_index}",
            )
            for field_name in ("schema_version", "evidence_scope", "domain_scope"):
                _string(
                    term[field_name],
                    f"exact quotient row {row_index} term {term_index} {field_name}",
                )
            _nonnegative_int(
                term["target_block_index"],
                f"exact quotient row {row_index} term target_block_index",
            )
            rational = _object_without_set(
                term["coefficient"],
                ("schema_version", "numerator", "denominator"),
                f"exact quotient row {row_index} term coefficient",
            )
            _string(
                rational["schema_version"],
                f"exact quotient row {row_index} term coefficient schema_version",
            )
            numerator = rational["numerator"]
            denominator = rational["denominator"]
            if type(numerator) is not str or type(denominator) is not str:
                raise StrictContractError(
                    "exact quotient rational decimal fields must be exact strings"
                )
            if (
                len(numerator.removeprefix("-"))
                > _MAX_EXACT_RATIONAL_DECIMAL_DIGITS
                or len(denominator) > _MAX_EXACT_RATIONAL_DECIMAL_DIGITS
            ):
                raise StrictContractError(
                    "exact quotient rational exceeds the decimal preflight cap"
                )
    return obj


def _preflight_exact_quotient_dimensions(
    fresh: VerifiedExactPartition,
) -> tuple[int, int, int, int, int, int]:
    snapshot = fresh.admitted.snapshot
    certificate = fresh.certificate
    totalized_state_count = len(snapshot.states)
    block_count = len(certificate.final_blocks)
    action_count = len(certificate.canonical_action_ids)
    if not 3 <= totalized_state_count <= MAX_SYNTHETIC_TOTALIZED_STATES:
        raise StrictContractError("exact quotient totalized-state cap is violated")
    if not 1 <= block_count <= MAX_SYNTHETIC_TOTALIZED_STATES:
        raise StrictContractError("exact quotient block cap is violated")
    if not 1 <= action_count <= MAX_SYNTHETIC_ACTIONS:
        raise StrictContractError("exact quotient action cap is violated")
    row_count = _checked_product(block_count, action_count, "exact quotient rows")
    member_action_witness_count = _checked_product(
        totalized_state_count, action_count, "exact quotient member/action witnesses"
    )
    if row_count > MAX_SYNTHETIC_TRANSITION_ROWS:
        raise StrictContractError("exact quotient row cap is violated")
    if member_action_witness_count > MAX_SYNTHETIC_TRANSITION_ROWS:
        raise StrictContractError("exact quotient member/action witness cap is violated")
    maximum_term_count = _checked_product(row_count, 2, "exact quotient terms")
    if maximum_term_count > _MAX_EXACT_QUOTIENT_TERMS:
        raise StrictContractError("exact quotient term cap is violated")
    upper_work = _checked_add(row_count, member_action_witness_count, "exact quotient work")
    _checked_add(upper_work, maximum_term_count, "exact quotient work")
    return (
        totalized_state_count,
        block_count,
        action_count,
        row_count,
        member_action_witness_count,
        maximum_term_count,
    )


def _derive_exact_quotient_generator_wire(
    source: VerifiedExactPartition,
) -> dict[str, Any]:
    if type(source) is not VerifiedExactPartition:
        raise StrictContractError(
            "exact quotient generator requires an exact VerifiedExactPartition"
        )
    fresh, exact_wire, dimensions = _fresh_exact_quotient_export(source)
    (
        totalized_state_count,
        block_count,
        action_count,
        row_count,
        member_action_witness_count,
        _maximum_term_count,
    ) = dimensions
    # _fresh_exact_quotient_export has already transported this stronger fresh
    # admission through a real sealed ExactFiniteOperator and consumed it in
    # the same indivisible transaction.
    snapshot = fresh.admitted.snapshot
    certificate = fresh.certificate

    snapshot_sha256 = _canonical_digest(
        exact_wire["snapshot_sha256"], "exact quotient snapshot_sha256"
    )
    if snapshot_sha256 != fresh.admitted.admission_report.snapshot_sha256:
        raise StrictContractError("exact quotient snapshot authority mismatch")
    environment_digest = _canonical_digest(
        snapshot.domain_id.environment_digest,
        "exact quotient environment_digest",
    )
    domain_payload_digest = _canonical_digest(
        exact_wire["domain_payload_digest"],
        "exact quotient domain_payload_digest",
    )
    if domain_payload_digest != snapshot.domain_id.domain_payload_digest:
        raise StrictContractError("exact quotient domain authority mismatch")
    seed_set_digest = _canonical_digest(
        snapshot.domain_id.seed_set_digest, "exact quotient seed_set_digest"
    )
    observation_frame_digest = _canonical_digest(
        exact_wire["observation_frame_digest"],
        "exact quotient observation_frame_digest",
    )
    if observation_frame_digest != snapshot.domain_id.frame_digest:
        raise StrictContractError("exact quotient frame authority mismatch")
    transition_semantics_digest = _canonical_digest(
        exact_wire["transition_semantics_digest"],
        "exact quotient transition_semantics_digest",
    )
    if transition_semantics_digest != snapshot.domain_id.transition_semantics_digest:
        raise StrictContractError("exact quotient transition authority mismatch")
    response_vocabulary_digest = _canonical_digest(
        exact_wire["response_vocabulary_digest"],
        "exact quotient response_vocabulary_digest",
    )
    if (
        response_vocabulary_digest
        != snapshot.response_vocabulary_id.vocabulary_digest
    ):
        raise StrictContractError("exact quotient vocabulary authority mismatch")
    action_alphabet_digest = _canonical_digest(
        exact_wire["action_alphabet_digest"],
        "exact quotient action_alphabet_digest",
    )
    if action_alphabet_digest != snapshot.domain_id.action_alphabet_digest:
        raise StrictContractError("exact quotient action authority mismatch")

    if (
        exact_wire["totalized_state_count"] != totalized_state_count
        or exact_wire["block_count"] != block_count
        or exact_wire["action_count"] != action_count
    ):
        raise StrictContractError("exact quotient dimension authority mismatch")
    exact_blocks = _array(exact_wire["blocks"], "exact quotient exact blocks")
    canonical_block_indices = [
        _nonnegative_int(block["block_index"], "exact quotient block index")
        for block in exact_blocks
    ]
    if canonical_block_indices != list(range(block_count)):
        raise StrictContractError("exact quotient block order is not canonical")
    exact_actions = _array(exact_wire["actions"], "exact quotient exact actions")
    canonical_action_ids = [
        _string(action["action_id"], "exact quotient action ID")
        for action in exact_actions
    ]
    if canonical_action_ids != list(certificate.canonical_action_ids):
        raise StrictContractError("exact quotient action order is not canonical")

    exact_rows = _array(exact_wire["rows"], "exact quotient exact rows")
    if len(exact_rows) != row_count:
        raise StrictContractError("exact quotient exact row count mismatch")
    rows: list[ExactQuotientTransferRow] = []
    observed_member_witnesses = 0
    observed_term_count = 0
    for row_index, raw_row in enumerate(exact_rows):
        exact_row = _object_without_set(
            raw_row,
            _EXACT_OPERATOR_MEMBER_ROW_FIELDS,
            f"exact operator member row {row_index}",
        )
        expected_source = row_index // action_count
        expected_action = canonical_action_ids[row_index % action_count]
        source_block_index = _nonnegative_int(
            exact_row["source_block_index"],
            "exact quotient source_block_index",
        )
        action_id = _string(exact_row["action_id"], "exact quotient action_id")
        action_sha256 = _canonical_digest(
            exact_row["action_sha256"], "exact quotient action_sha256"
        )
        structural_target_block_index = _nonnegative_int(
            exact_row["target_block_index"],
            "exact quotient structural_target_block_index",
        )
        member_transition_count = _nonnegative_int(
            exact_row["member_transition_count"],
            "exact quotient member_transition_count",
            upper=MAX_SYNTHETIC_TOTALIZED_STATES,
        )
        member_transitions = _array(
            exact_row["member_transitions"],
            "exact quotient member transitions",
        )
        if (
            source_block_index != expected_source
            or action_id != expected_action
            or structural_target_block_index >= block_count
            or member_transition_count != len(member_transitions)
            or member_transition_count == 0
        ):
            raise StrictContractError("exact quotient member row authority mismatch")
        terms = _expected_exact_quotient_terms(
            source_block_index, structural_target_block_index
        )
        row = ExactQuotientTransferRow(
            source_block_index=source_block_index,
            action_id=action_id,
            action_sha256=action_sha256,
            structural_target_block_index=structural_target_block_index,
            member_transition_count=member_transition_count,
            member_transition_sha256=_sha256(exact_row),
            terms=terms,
        )
        rows.append(row)
        observed_member_witnesses = _checked_add(
            observed_member_witnesses,
            member_transition_count,
            "exact quotient member/action witnesses",
        )
        observed_term_count = _checked_add(
            observed_term_count, len(terms), "exact quotient terms"
        )
    if observed_member_witnesses != member_action_witness_count:
        raise StrictContractError("exact quotient member/action witness total mismatch")
    expected_term_count = 2 * sum(
        row.source_block_index != row.structural_target_block_index for row in rows
    )
    if observed_term_count != expected_term_count:
        raise StrictContractError("exact quotient nonzero term total mismatch")
    work_units = _checked_add(row_count, member_action_witness_count, "exact quotient work")
    work_units = _checked_add(work_units, observed_term_count, "exact quotient work")

    admission_report_sha256 = _sha256(
        fresh.admitted.admission_report.to_dict()
    )
    reachable_domain_sha256 = _sha256(snapshot.domain_id.to_dict())
    synthetic_evidence_profile_sha256 = _sha256(
        snapshot.evidence_profile.to_dict()
    )
    verified_partition_sha256 = _sha256(fresh.to_dict())
    if verified_partition_sha256 != _canonical_digest(
        exact_wire["verified_partition_sha256"],
        "exact quotient verified_partition_sha256",
    ):
        raise StrictContractError("exact quotient partition authority mismatch")
    exact_operator_sha256 = _sha256(exact_wire)
    canonical_block_order_sha256 = _sha256({"blocks": exact_blocks})
    canonical_action_order_sha256 = _sha256({"actions": exact_actions})
    source_seal_sha256 = _sha256(
        {
            "seal_version": _EXACT_QUOTIENT_SOURCE_SEAL_VERSION,
            "admission_report_sha256": admission_report_sha256,
            "verified_partition_sha256": verified_partition_sha256,
            "exact_operator_sha256": exact_operator_sha256,
            "canonical_block_order_sha256": canonical_block_order_sha256,
            "canonical_action_order_sha256": canonical_action_order_sha256,
        }
    )

    return {
        "schema_version": _EXACT_QUOTIENT_COORDINATE_GENERATOR_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "domain_scope": _EXACT_QUOTIENT_DOMAIN_SCOPE,
        "basis_convention": _EXACT_QUOTIENT_BASIS_CONVENTION,
        "generator_convention": _EXACT_QUOTIENT_GENERATOR_CONVENTION,
        "admission_report_sha256": admission_report_sha256,
        "snapshot_sha256": snapshot_sha256,
        "environment_digest": environment_digest,
        "reachable_domain_sha256": reachable_domain_sha256,
        "domain_payload_digest": domain_payload_digest,
        "seed_set_digest": seed_set_digest,
        "observation_frame_digest": observation_frame_digest,
        "transition_semantics_digest": transition_semantics_digest,
        "response_vocabulary_digest": response_vocabulary_digest,
        "action_alphabet_digest": action_alphabet_digest,
        "synthetic_evidence_profile_sha256": synthetic_evidence_profile_sha256,
        "verified_partition_sha256": verified_partition_sha256,
        "exact_operator_sha256": exact_operator_sha256,
        "canonical_block_order_sha256": canonical_block_order_sha256,
        "canonical_action_order_sha256": canonical_action_order_sha256,
        "source_seal_sha256": source_seal_sha256,
        "totalized_state_count": totalized_state_count,
        "block_count": block_count,
        "action_count": action_count,
        "canonical_block_indices": canonical_block_indices,
        "canonical_action_ids": canonical_action_ids,
        "row_count": row_count,
        "term_count": observed_term_count,
        "member_action_witness_count": member_action_witness_count,
        "work_units": work_units,
        "rows": [row.to_dict() for row in rows],
    }


def _validate_exact_quotient_generator_wire(obj: dict[str, Any]) -> None:
    _fixed(
        obj["schema_version"],
        _EXACT_QUOTIENT_COORDINATE_GENERATOR_SCHEMA,
        "ExactQuotientCoordinateGenerator schema",
    )
    _fixed(
        obj["evidence_scope"],
        SYNTHETIC_EVIDENCE_SCOPE,
        "exact quotient generator evidence_scope",
    )
    _fixed(
        obj["domain_scope"],
        _EXACT_QUOTIENT_DOMAIN_SCOPE,
        "exact quotient generator domain_scope",
    )
    _fixed(
        obj["basis_convention"],
        _EXACT_QUOTIENT_BASIS_CONVENTION,
        "exact quotient basis_convention",
    )
    _fixed(
        obj["generator_convention"],
        _EXACT_QUOTIENT_GENERATOR_CONVENTION,
        "exact quotient generator_convention",
    )
    for field_name in (
        "admission_report_sha256",
        "snapshot_sha256",
        "environment_digest",
        "reachable_domain_sha256",
        "domain_payload_digest",
        "seed_set_digest",
        "observation_frame_digest",
        "transition_semantics_digest",
        "response_vocabulary_digest",
        "action_alphabet_digest",
        "synthetic_evidence_profile_sha256",
        "verified_partition_sha256",
        "exact_operator_sha256",
        "canonical_block_order_sha256",
        "canonical_action_order_sha256",
        "source_seal_sha256",
    ):
        _canonical_digest(obj[field_name], f"exact quotient {field_name}")

    totalized_state_count = _nonnegative_int(
        obj["totalized_state_count"], "exact quotient totalized_state_count"
    )
    block_count = _nonnegative_int(obj["block_count"], "exact quotient block_count")
    action_count = _nonnegative_int(
        obj["action_count"], "exact quotient action_count"
    )
    row_count = _nonnegative_int(obj["row_count"], "exact quotient row_count")
    term_count = _nonnegative_int(obj["term_count"], "exact quotient term_count")
    member_count = _nonnegative_int(
        obj["member_action_witness_count"],
        "exact quotient member_action_witness_count",
    )
    work_units = _nonnegative_int(
        obj["work_units"],
        "exact quotient work_units",
        upper=MAX_TIER_FIREWALL_WORK_UNITS,
    )
    if (
        not 3 <= totalized_state_count <= MAX_SYNTHETIC_TOTALIZED_STATES
        or not 1 <= block_count <= MAX_SYNTHETIC_TOTALIZED_STATES
        or not 1 <= action_count <= MAX_SYNTHETIC_ACTIONS
        or row_count > MAX_SYNTHETIC_TRANSITION_ROWS
        or term_count > _MAX_EXACT_QUOTIENT_TERMS
        or member_count > MAX_SYNTHETIC_TRANSITION_ROWS
    ):
        raise StrictContractError("exact quotient wire dimensions exceed their caps")
    raw_block_indices = _array(
        obj["canonical_block_indices"], "exact quotient canonical_block_indices"
    )
    block_indices = [
        _nonnegative_int(value, "exact quotient canonical block index")
        for value in raw_block_indices
    ]
    if block_indices != list(range(block_count)):
        raise StrictContractError("exact quotient wire block order is not canonical")
    raw_action_ids = _array(
        obj["canonical_action_ids"], "exact quotient canonical_action_ids"
    )
    action_ids = [
        _string(value, "exact quotient canonical action ID")
        for value in raw_action_ids
    ]
    if len(action_ids) != action_count or len(action_ids) != len(set(action_ids)):
        raise StrictContractError("exact quotient wire action order is invalid")
    raw_rows = _array(obj["rows"], "exact quotient generator rows")
    rows = tuple(ExactQuotientTransferRow.from_dict(row) for row in raw_rows)
    if len(rows) != row_count or row_count != block_count * action_count:
        raise StrictContractError("exact quotient wire row count is invalid")
    expected_keys = tuple(
        (block_index, action_id)
        for block_index in range(block_count)
        for action_id in action_ids
    )
    actual_keys = tuple((row.source_block_index, row.action_id) for row in rows)
    if actual_keys != expected_keys:
        raise StrictContractError("exact quotient wire rows are reordered or duplicated")
    if any(
        row.structural_target_block_index >= block_count
        or any(term.target_block_index >= block_count for term in row.terms)
        for row in rows
    ):
        raise StrictContractError("exact quotient wire contains an out-of-range block")
    observed_terms = sum(len(row.terms) for row in rows)
    observed_members = sum(row.member_transition_count for row in rows)
    if observed_terms != term_count or observed_members != member_count:
        raise StrictContractError("exact quotient wire aggregate counts are invalid")
    if work_units != row_count + term_count + member_count:
        raise StrictContractError("exact quotient wire work formula is invalid")


@dataclass(frozen=True, init=False)
class ExactQuotientCoordinateGenerator:
    _verified_source: VerifiedExactPartition = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError(
            "exact quotient generator has no public constructor"
        )

    def __post_init__(self) -> None:
        if type(self) is not ExactQuotientCoordinateGenerator:
            raise StrictContractError(
                "ExactQuotientCoordinateGenerator subclasses are forbidden"
            )
        if self._construction_seal is not _EXACT_QUOTIENT_GENERATOR_SEAL:
            raise StrictContractError(
                "exact quotient generator requires the verified construction gate"
            )
        if type(self._verified_source) is not VerifiedExactPartition:
            raise StrictContractError(
                "exact quotient generator retained source is not exact"
            )
        _canonical_digest(
            self._source_seal_sha256, "exact quotient generator source seal"
        )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], source: VerifiedExactPartition
    ) -> "ExactQuotientCoordinateGenerator":
        if cls is not ExactQuotientCoordinateGenerator:
            raise StrictContractError(
                "polymorphic exact quotient generator parsing is forbidden"
            )
        if type(source) is not VerifiedExactPartition:
            raise StrictContractError(
                "exact quotient generator parser requires an exact verified source"
            )
        obj = _preflight_exact_quotient_generator_wire(value)
        expected_wire = _derive_exact_quotient_generator_wire(source)
        _validate_exact_quotient_generator_wire(obj)
        if canonical_contract_bytes(obj) != canonical_contract_bytes(expected_wire):
            raise StrictContractError(
                "exact quotient generator wire does not match retained authority"
            )
        return _construct_exact_quotient_coordinate_generator(source, expected_wire)

    @property
    def generator_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _EXACT_QUOTIENT_GENERATOR_SEAL:
            raise StrictContractError("exact quotient generator construction seal changed")
        wire = _derive_exact_quotient_generator_wire(self._verified_source)
        if wire["source_seal_sha256"] != _canonical_digest(
            self._source_seal_sha256, "exact quotient generator source seal"
        ):
            raise StrictContractError(
                "exact quotient generator retained source was replaced or changed"
            )
        return wire


def build_exact_quotient_coordinate_generator(
    source: VerifiedExactPartition,
) -> ExactQuotientCoordinateGenerator:
    if type(source) is not VerifiedExactPartition:
        raise StrictContractError(
            "exact quotient generator requires an exact VerifiedExactPartition"
        )
    wire = _derive_exact_quotient_generator_wire(source)
    return _construct_exact_quotient_coordinate_generator(source, wire)


def _construct_exact_quotient_coordinate_generator(
    source: VerifiedExactPartition, wire: Mapping[str, Any]
) -> ExactQuotientCoordinateGenerator:
    result = object.__new__(ExactQuotientCoordinateGenerator)
    object.__setattr__(result, "_verified_source", source)
    object.__setattr__(
        result, "_source_seal_sha256", wire["source_seal_sha256"]
    )
    object.__setattr__(
        result, "_construction_seal", _EXACT_QUOTIENT_GENERATOR_SEAL
    )
    result.__post_init__()
    return result


def _rational_add(left: ExactRational, right: ExactRational) -> ExactRational:
    if type(left) is not ExactRational or type(right) is not ExactRational:
        raise StrictContractError("exact arithmetic requires ExactRational operands")
    return ExactRational(
        left.numerator * right.denominator
        + right.numerator * left.denominator,
        left.denominator * right.denominator,
    )


def _rational_multiply(left: ExactRational, right: ExactRational) -> ExactRational:
    if type(left) is not ExactRational or type(right) is not ExactRational:
        raise StrictContractError("exact arithmetic requires ExactRational operands")
    return ExactRational(
        left.numerator * right.numerator,
        left.denominator * right.denominator,
    )


def _rational_divide(left: ExactRational, right: ExactRational) -> ExactRational:
    if type(left) is not ExactRational or type(right) is not ExactRational:
        raise StrictContractError("exact arithmetic requires ExactRational operands")
    if right.numerator == 0:
        raise StrictContractError("exact division by zero is forbidden")
    sign = -1 if right.numerator < 0 else 1
    return ExactRational(
        sign * left.numerator * right.denominator,
        left.denominator * abs(right.numerator),
    )


def _fresh_fiber_frame(
    generator: ExactQuotientCoordinateGenerator,
) -> dict[str, Any]:
    """Re-derive the complete ordered member/block frame retained by E0."""

    if type(generator) is not ExactQuotientCoordinateGenerator:
        raise StrictContractError(
            "fiber coordinates require an exact quotient coordinate generator"
        )
    # ``to_dict`` already performs the complete fresh E0 admission, partition,
    # source-seal and wire rederivation.  Repeating that derivation twice here
    # would make each E1 lookup cubic in nested certificate calls.
    generator_wire = generator.to_dict()
    fresh = generator._verified_source
    if type(fresh) is not VerifiedExactPartition:
        raise StrictContractError("fiber coordinate generator authority is stale")
    blocks = tuple(
        (
            block.block_index,
            tuple(sorted(block.member_state_ids)),
        )
        for block in fresh.certificate.final_blocks
    )
    if tuple(index for index, _members in blocks) != tuple(range(len(blocks))):
        raise StrictContractError("fiber block order is not canonical")
    members = tuple(member for _index, block in blocks for member in block)
    if (
        len(members) < 3
        or len(members) > 128
        or len(blocks) > 64
        or len(members) != len(set(members))
    ):
        raise StrictContractError("fiber frame dimensions are outside frozen caps")
    member_sha256 = {
        state.state_id: _sha256(state.to_dict())
        for state in fresh.admitted.snapshot.states
    }
    if set(member_sha256) != set(members):
        raise StrictContractError("fiber frame member authority is incomplete")
    return {
        "generator_sha256": _sha256(generator_wire),
        "reachable_domain_sha256": generator_wire["reachable_domain_sha256"],
        "verified_partition_sha256": generator_wire["verified_partition_sha256"],
        "canonical_block_order_sha256": generator_wire[
            "canonical_block_order_sha256"
        ],
        "blocks": blocks,
        "members": members,
        "member_sha256": member_sha256,
    }


def _normalize_member_rationals(
    frame: Mapping[str, Any], values: Any, where: str
) -> tuple[ExactRational, ...]:
    members = frame["members"]
    if type(values) is dict:
        if set(values) != set(members) or len(values) != len(members):
            raise StrictContractError(f"{where} must cover every member exactly once")
        ordered = tuple(values[member] for member in members)
    elif type(values) in {tuple, list}:
        if len(values) != len(members):
            raise StrictContractError(f"{where} length does not match member order")
        ordered = tuple(values)
    else:
        raise StrictContractError(
            f"{where} must be an exact object or exact tuple/list"
        )
    for value in ordered:
        if type(value) is not ExactRational:
            raise StrictContractError(f"{where} values must be ExactRational")
        if ExactRational.from_dict(value.to_dict()) != value:
            raise StrictContractError(f"{where} contains noncanonical authority")
    return ordered


def _preflight_member_rational_input(
    values: Any, where: str, *, strictly_positive: bool
) -> None:
    if type(values) is dict:
        raw_values = values.values()
    elif type(values) in {tuple, list}:
        raw_values = values
    else:
        raise StrictContractError(
            f"{where} must be an exact object or exact tuple/list"
        )
    if len(values) > _MAX_FIBER_MEMBERS:
        raise StrictContractError(f"{where} exceeds the member preflight cap")
    for value in raw_values:
        if type(value) is not ExactRational:
            raise StrictContractError(f"{where} values must be ExactRational")
        if ExactRational.from_dict(value.to_dict()) != value:
            raise StrictContractError(f"{where} contains noncanonical authority")
        if strictly_positive and value.numerator <= 0:
            raise StrictContractError(f"{where} values must be strictly positive")
        if not strictly_positive and value.numerator < 0:
            raise StrictContractError(f"{where} values must be nonnegative")


def _member_value_wire(
    frame: Mapping[str, Any], values: tuple[ExactRational, ...], value_name: str
) -> list[dict[str, Any]]:
    if len(values) != len(frame["members"]):
        raise StrictContractError(f"{value_name} retained value count changed")
    return [
        {
            "block_index": block_index,
            "member_id": member,
            "member_sha256": frame["member_sha256"][member],
            value_name: values[position].to_dict(),
        }
        for position, member in enumerate(frame["members"])
        for block_index, block_members in frame["blocks"]
        if member in block_members
    ]


def _derive_positive_weights_wire(
    generator: ExactQuotientCoordinateGenerator,
    values: tuple[ExactRational, ...],
) -> dict[str, Any]:
    frame = _fresh_fiber_frame(generator)
    return _derive_positive_weights_wire_from_frame(frame, values)


def _derive_positive_weights_wire_from_frame(
    frame: Mapping[str, Any],
    values: tuple[ExactRational, ...],
) -> dict[str, Any]:
    canonical = _normalize_member_rationals(frame, values, "positive fiber weights")
    if any(value.numerator <= 0 for value in canonical):
        raise StrictContractError("every fiber weight must be strictly positive")
    rows = _member_value_wire(frame, canonical, "weight")
    return {
        "schema_version": POSITIVE_FIBER_WEIGHTS_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "generator_sha256": frame["generator_sha256"],
        "reachable_domain_sha256": frame["reachable_domain_sha256"],
        "verified_partition_sha256": frame["verified_partition_sha256"],
        "canonical_block_order_sha256": frame["canonical_block_order_sha256"],
        "member_count": len(frame["members"]),
        "block_count": len(frame["blocks"]),
        "rows": rows,
    }


@dataclass(frozen=True, init=False)
class PositiveFiberWeights:
    _generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _values: tuple[ExactRational, ...] = field(repr=False)
    _value_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("positive fiber weights have no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not PositiveFiberWeights:
            raise StrictContractError("PositiveFiberWeights subclasses are forbidden")
        if self._construction_seal is not _POSITIVE_FIBER_WEIGHTS_SEAL:
            raise StrictContractError("positive fiber weights require the sealed factory")
        _canonical_digest(self._value_seal_sha256, "positive weight value seal")

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        generator: ExactQuotientCoordinateGenerator,
    ) -> "PositiveFiberWeights":
        if cls is not PositiveFiberWeights:
            raise StrictContractError("polymorphic positive weight parsing is forbidden")
        if type(value) is not dict:
            raise StrictContractError("PositiveFiberWeights must be an exact object")
        if type(generator) is not ExactQuotientCoordinateGenerator:
            raise StrictContractError("PositiveFiberWeights parser requires an E0 generator")
        fields = {
            "schema_version", "evidence_scope", "generator_sha256",
            "reachable_domain_sha256", "verified_partition_sha256",
            "canonical_block_order_sha256", "member_count", "block_count", "rows",
        }
        obj = _object(value, fields, "PositiveFiberWeights")
        if (
            obj["schema_version"] != POSITIVE_FIBER_WEIGHTS_SCHEMA
            or obj["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE
        ):
            raise StrictContractError("PositiveFiberWeights schema/scope mismatch")
        raw_rows = _array(obj["rows"], "positive weight rows")
        if len(raw_rows) > _MAX_FIBER_MEMBERS:
            raise StrictContractError("positive weight rows exceed the preflight cap")
        _canonical_digest(obj["generator_sha256"], "positive weight generator SHA")
        _canonical_digest(obj["reachable_domain_sha256"], "positive weight domain SHA")
        _canonical_digest(obj["verified_partition_sha256"], "positive weight partition SHA")
        _canonical_digest(obj["canonical_block_order_sha256"], "positive weight block-order SHA")
        _nonnegative_int(obj["member_count"], "positive weight member count", upper=_MAX_FIBER_MEMBERS)
        _nonnegative_int(obj["block_count"], "positive weight block count", upper=_MAX_FIBER_BLOCKS)
        parsed: dict[str, ExactRational] = {}
        for row in raw_rows:
            exact = _object(
                row,
                {"block_index", "member_id", "member_sha256", "weight"},
                "positive weight row",
            )
            _nonnegative_int(
                exact["block_index"],
                "positive weight block index",
                upper=_MAX_FIBER_BLOCKS - 1,
            )
            member = _string(exact["member_id"], "positive weight member")
            _canonical_digest(
                exact["member_sha256"], "positive weight member SHA"
            )
            if member in parsed:
                raise StrictContractError("positive weight member is duplicated")
            parsed[member] = ExactRational.from_dict(exact["weight"])
        frame = _fresh_fiber_frame(generator)
        if len(raw_rows) != len(frame["members"]):
            raise StrictContractError("positive weight row count changed")
        canonical = _normalize_member_rationals(frame, parsed, "positive fiber weights")
        expected_wire = _derive_positive_weights_wire_from_frame(frame, canonical)
        if canonical_contract_bytes(obj) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("positive weight wire disagrees with authority")
        return _construct_positive_fiber_weights(generator, canonical, expected_wire)

    @property
    def weights_sha256(self) -> str:
        return _sha256(self.to_dict())

    @property
    def generator_sha256(self) -> str:
        return self.to_dict()["generator_sha256"]

    def weight_for(self, member_id: str) -> ExactRational:
        member = _string(member_id, "fiber weight member_id")
        wire = self.to_dict()
        for row in wire["rows"]:
            if row["member_id"] == member:
                return ExactRational.from_dict(row["weight"])
        raise StrictContractError("fiber weight member is outside the exact domain")

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _POSITIVE_FIBER_WEIGHTS_SEAL:
            raise StrictContractError("positive fiber weight construction seal changed")
        wire = _derive_positive_weights_wire(self._generator, self._values)
        if _sha256(wire) != _canonical_digest(
            self._value_seal_sha256, "positive weight value seal"
        ):
            raise StrictContractError("positive fiber weights retained values changed")
        return wire


def make_positive_fiber_weights(
    generator: ExactQuotientCoordinateGenerator, values: Any
) -> PositiveFiberWeights:
    _preflight_member_rational_input(
        values, "positive fiber weights", strictly_positive=True
    )
    frame = _fresh_fiber_frame(generator)
    canonical = _normalize_member_rationals(frame, values, "positive fiber weights")
    wire = _derive_positive_weights_wire_from_frame(frame, canonical)
    return _construct_positive_fiber_weights(generator, canonical, wire)


def _construct_positive_fiber_weights(
    generator: ExactQuotientCoordinateGenerator,
    canonical: tuple[ExactRational, ...],
    wire: Mapping[str, Any],
) -> PositiveFiberWeights:
    result = object.__new__(PositiveFiberWeights)
    object.__setattr__(result, "_generator", generator)
    object.__setattr__(result, "_values", canonical)
    object.__setattr__(result, "_value_seal_sha256", _sha256(wire))
    object.__setattr__(result, "_construction_seal", _POSITIVE_FIBER_WEIGHTS_SEAL)
    result.__post_init__()
    return result


def _derive_fiber_law_wire(
    generator: ExactQuotientCoordinateGenerator,
    probabilities: tuple[ExactRational, ...],
) -> dict[str, Any]:
    frame = _fresh_fiber_frame(generator)
    return _derive_fiber_law_wire_from_frame(frame, probabilities)


def _derive_fiber_law_wire_from_frame(
    frame: Mapping[str, Any],
    probabilities: tuple[ExactRational, ...],
) -> dict[str, Any]:
    canonical = _normalize_member_rationals(
        frame, probabilities, "exact finite fiber law"
    )
    if any(value.numerator < 0 for value in canonical):
        raise StrictContractError("fiber probabilities must be nonnegative")
    offset = 0
    block_sums: list[dict[str, Any]] = []
    for block_index, members in frame["blocks"]:
        total = ExactRational(0)
        for value in canonical[offset : offset + len(members)]:
            total = _rational_add(total, value)
        if total != ExactRational(1):
            raise StrictContractError("fiber probabilities must sum exactly to one")
        block_sums.append(
            {"block_index": block_index, "probability_sum": total.to_dict()}
        )
        offset += len(members)
    rows = _member_value_wire(frame, canonical, "probability")
    return {
        "schema_version": EXACT_FINITE_FIBER_LAW_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "generator_sha256": frame["generator_sha256"],
        "reachable_domain_sha256": frame["reachable_domain_sha256"],
        "verified_partition_sha256": frame["verified_partition_sha256"],
        "canonical_block_order_sha256": frame["canonical_block_order_sha256"],
        "member_count": len(frame["members"]),
        "block_count": len(frame["blocks"]),
        "rows": rows,
        "block_sums": block_sums,
    }


@dataclass(frozen=True, init=False)
class ExactFiniteFiberLaw:
    _generator: ExactQuotientCoordinateGenerator = field(repr=False)
    _probabilities: tuple[ExactRational, ...] = field(repr=False)
    _value_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("exact finite fiber law has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not ExactFiniteFiberLaw:
            raise StrictContractError("ExactFiniteFiberLaw subclasses are forbidden")
        if self._construction_seal is not _EXACT_FINITE_FIBER_LAW_SEAL:
            raise StrictContractError("exact finite fiber law requires the sealed factory")
        _canonical_digest(self._value_seal_sha256, "fiber law value seal")

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        generator: ExactQuotientCoordinateGenerator,
    ) -> "ExactFiniteFiberLaw":
        if cls is not ExactFiniteFiberLaw or type(value) is not dict:
            raise StrictContractError("strict ExactFiniteFiberLaw parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "generator_sha256",
            "reachable_domain_sha256", "verified_partition_sha256",
            "canonical_block_order_sha256", "member_count", "block_count",
            "rows", "block_sums",
        } or value["schema_version"] != EXACT_FINITE_FIBER_LAW_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE:
            raise StrictContractError("ExactFiniteFiberLaw outer fields/schema mismatch")
        raw_rows = _array(value.get("rows"), "fiber law rows")
        raw_sums = _array(value.get("block_sums"), "fiber law block sums")
        if len(raw_rows) > _MAX_FIBER_MEMBERS or len(raw_sums) > _MAX_FIBER_BLOCKS:
            raise StrictContractError("fiber law arrays exceed their preflight caps")
        _canonical_digest(value["generator_sha256"], "fiber law generator SHA")
        _canonical_digest(value["reachable_domain_sha256"], "fiber law domain SHA")
        _canonical_digest(value["verified_partition_sha256"], "fiber law partition SHA")
        _canonical_digest(value["canonical_block_order_sha256"], "fiber law block-order SHA")
        _nonnegative_int(value["member_count"], "fiber law member count", upper=_MAX_FIBER_MEMBERS)
        _nonnegative_int(value["block_count"], "fiber law block count", upper=_MAX_FIBER_BLOCKS)
        parsed: dict[str, ExactRational] = {}
        for row in raw_rows:
            exact = _object(
                row,
                {"block_index", "member_id", "member_sha256", "probability"},
                "fiber law row",
            )
            _nonnegative_int(
                exact["block_index"],
                "fiber law block index",
                upper=_MAX_FIBER_BLOCKS - 1,
            )
            member = _string(exact["member_id"], "fiber law member")
            _canonical_digest(exact["member_sha256"], "fiber law member SHA")
            if member in parsed:
                raise StrictContractError("fiber law member is duplicated")
            parsed[member] = ExactRational.from_dict(exact["probability"])
        seen_sum_indices: set[int] = set()
        for row in raw_sums:
            exact = _object(
                row,
                {"block_index", "probability_sum"},
                "fiber law block-sum row",
            )
            block_index = _nonnegative_int(
                exact["block_index"],
                "fiber law block-sum index",
                upper=_MAX_FIBER_BLOCKS - 1,
            )
            if block_index in seen_sum_indices:
                raise StrictContractError("fiber law block-sum index is duplicated")
            seen_sum_indices.add(block_index)
            ExactRational.from_dict(exact["probability_sum"])
        frame = _fresh_fiber_frame(generator)
        if len(raw_rows) != len(frame["members"]) or len(raw_sums) != len(frame["blocks"]):
            raise StrictContractError("fiber law row/block-sum count changed")
        canonical = _normalize_member_rationals(frame, parsed, "exact finite fiber law")
        expected_wire = _derive_fiber_law_wire_from_frame(frame, canonical)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("fiber law wire disagrees with authority")
        return _construct_exact_finite_fiber_law(generator, canonical, expected_wire)

    @property
    def law_sha256(self) -> str:
        return _sha256(self.to_dict())

    @property
    def generator_sha256(self) -> str:
        return self.to_dict()["generator_sha256"]

    def probability_for(self, member_id: str) -> ExactRational:
        member = _string(member_id, "fiber law member_id")
        wire = self.to_dict()
        for row in wire["rows"]:
            if row["member_id"] == member:
                return ExactRational.from_dict(row["probability"])
        raise StrictContractError("fiber law member is outside the exact domain")

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _EXACT_FINITE_FIBER_LAW_SEAL:
            raise StrictContractError("fiber law construction seal changed")
        wire = _derive_fiber_law_wire(self._generator, self._probabilities)
        if _sha256(wire) != _canonical_digest(
            self._value_seal_sha256, "fiber law value seal"
        ):
            raise StrictContractError("fiber law retained probabilities changed")
        return wire


def make_exact_finite_fiber_law(
    generator: ExactQuotientCoordinateGenerator, probabilities: Any
) -> ExactFiniteFiberLaw:
    _preflight_member_rational_input(
        probabilities, "exact finite fiber law", strictly_positive=False
    )
    frame = _fresh_fiber_frame(generator)
    canonical = _normalize_member_rationals(
        frame, probabilities, "exact finite fiber law"
    )
    wire = _derive_fiber_law_wire_from_frame(frame, canonical)
    return _construct_exact_finite_fiber_law(generator, canonical, wire)


def _construct_exact_finite_fiber_law(
    generator: ExactQuotientCoordinateGenerator,
    canonical: tuple[ExactRational, ...],
    wire: Mapping[str, Any],
) -> ExactFiniteFiberLaw:
    result = object.__new__(ExactFiniteFiberLaw)
    object.__setattr__(result, "_generator", generator)
    object.__setattr__(result, "_probabilities", canonical)
    object.__setattr__(result, "_value_seal_sha256", _sha256(wire))
    object.__setattr__(result, "_construction_seal", _EXACT_FINITE_FIBER_LAW_SEAL)
    result.__post_init__()
    return result


def _normalize_complete_vector(
    keys: tuple[Any, ...], values: Any, where: str
) -> tuple[ExactRational, ...]:
    if type(values) is dict:
        if set(values) != set(keys) or len(values) != len(keys):
            raise StrictContractError(f"{where} must cover its exact domain")
        ordered = tuple(values[key] for key in keys)
    elif type(values) in {tuple, list}:
        if len(values) != len(keys):
            raise StrictContractError(f"{where} has the wrong dimension")
        ordered = tuple(values)
    else:
        raise StrictContractError(f"{where} must be an exact object or tuple/list")
    if not all(type(value) is ExactRational for value in ordered):
        raise StrictContractError(f"{where} values must be ExactRational")
    return ordered


@dataclass(frozen=True, init=False)
class WeightedCompression:
    _weights: PositiveFiberWeights = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("weighted compression has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not WeightedCompression or self._construction_seal is not _WEIGHTED_COMPRESSION_SEAL:
            raise StrictContractError("weighted compression requires the sealed factory")
        _canonical_digest(self._source_seal_sha256, "weighted compression source seal")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], weights: PositiveFiberWeights) -> "WeightedCompression":
        if cls is not WeightedCompression or type(value) is not dict:
            raise StrictContractError("strict WeightedCompression parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "generator_sha256",
            "weights_sha256", "member_count", "block_count", "formula",
        } or value["schema_version"] != WEIGHTED_COMPRESSION_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE or value["formula"] != "C_omega_column_source_v1":
            raise StrictContractError("WeightedCompression outer fields/schema mismatch")
        _canonical_digest(value["generator_sha256"], "weighted compression generator SHA")
        _canonical_digest(value["weights_sha256"], "weighted compression weights SHA")
        _nonnegative_int(value["member_count"], "weighted compression member count", upper=_MAX_FIBER_MEMBERS)
        _nonnegative_int(value["block_count"], "weighted compression block count", upper=_MAX_FIBER_BLOCKS)
        expected_wire = _derive_weighted_compression_wire(weights)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("weighted compression wire disagrees with authority")
        return _construct_weighted_compression(weights, expected_wire)

    def compress(self, member_vector: Any) -> tuple[ExactRational, ...]:
        if self._construction_seal is not _WEIGHTED_COMPRESSION_SEAL:
            raise StrictContractError("weighted compression construction seal changed")
        weights_wire = self._weights.to_dict()
        wire = _derive_weighted_compression_wire_from_weights_wire(weights_wire)
        if _sha256(wire) != _canonical_digest(
            self._source_seal_sha256, "weighted compression source seal"
        ):
            raise StrictContractError("weighted compression retained authority changed")
        rows = weights_wire["rows"]
        members = tuple(row["member_id"] for row in rows)
        values = _normalize_complete_vector(members, member_vector, "member vector")
        result: list[ExactRational] = []
        for block_index in range(weights_wire["block_count"]):
            total = ExactRational(0)
            for position, row in enumerate(rows):
                if row["block_index"] != block_index:
                    continue
                total = _rational_add(
                    total,
                    _rational_multiply(
                        self._weights._values[position], values[position]
                    ),
                )
            result.append(total)
        return tuple(result)

    __call__ = compress

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _WEIGHTED_COMPRESSION_SEAL:
            raise StrictContractError("weighted compression construction seal changed")
        wire = _derive_weighted_compression_wire(self._weights)
        if _sha256(wire) != _canonical_digest(
            self._source_seal_sha256, "weighted compression source seal"
        ):
            raise StrictContractError("weighted compression retained authority changed")
        return wire


def _derive_weighted_compression_wire(
    weights: PositiveFiberWeights,
) -> dict[str, Any]:
    if type(weights) is not PositiveFiberWeights:
        raise StrictContractError("weighted compression requires PositiveFiberWeights")
    weights_wire = weights.to_dict()
    return _derive_weighted_compression_wire_from_weights_wire(weights_wire)


def _derive_weighted_compression_wire_from_weights_wire(
    weights_wire: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": WEIGHTED_COMPRESSION_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "generator_sha256": weights_wire["generator_sha256"],
        "weights_sha256": _sha256(weights_wire),
        "member_count": weights_wire["member_count"],
        "block_count": weights_wire["block_count"],
        "formula": "C_omega_column_source_v1",
    }


def make_weighted_compression(weights: PositiveFiberWeights) -> WeightedCompression:
    if type(weights) is not PositiveFiberWeights:
        raise StrictContractError("weighted compression requires PositiveFiberWeights")
    wire = _derive_weighted_compression_wire(weights)
    return _construct_weighted_compression(weights, wire)


def _construct_weighted_compression(
    weights: PositiveFiberWeights, wire: Mapping[str, Any]
) -> WeightedCompression:
    result = object.__new__(WeightedCompression)
    object.__setattr__(result, "_weights", weights)
    object.__setattr__(result, "_source_seal_sha256", _sha256(wire))
    object.__setattr__(result, "_construction_seal", _WEIGHTED_COMPRESSION_SEAL)
    result.__post_init__()
    return result


@dataclass(frozen=True, init=False)
class WeightedLifting:
    _weights: PositiveFiberWeights = field(repr=False)
    _law: ExactFiniteFiberLaw = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("weighted lifting has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not WeightedLifting or self._construction_seal is not _WEIGHTED_LIFTING_SEAL:
            raise StrictContractError("weighted lifting requires the sealed factory")
        _canonical_digest(self._source_seal_sha256, "weighted lifting source seal")

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], weights: PositiveFiberWeights, law: ExactFiniteFiberLaw
    ) -> "WeightedLifting":
        if cls is not WeightedLifting or type(value) is not dict:
            raise StrictContractError("strict WeightedLifting parsing is required")
        if set(value) != {
            "schema_version", "evidence_scope", "generator_sha256",
            "weights_sha256", "law_sha256", "member_count", "block_count",
            "formula", "roundtrip_identity_checks",
        } or value["schema_version"] != WEIGHTED_LIFTING_SCHEMA or value["evidence_scope"] != SYNTHETIC_EVIDENCE_SCOPE or value["formula"] != "L_mu_omega_column_source_v1":
            raise StrictContractError("WeightedLifting outer fields/schema mismatch")
        checks = _array(
            value["roundtrip_identity_checks"],
            "weighted lifting roundtrip checks",
        )
        if len(checks) > _MAX_FIBER_BLOCKS:
            raise StrictContractError("weighted lifting checks exceed the preflight cap")
        _canonical_digest(value["generator_sha256"], "weighted lifting generator SHA")
        _canonical_digest(value["weights_sha256"], "weighted lifting weights SHA")
        _canonical_digest(value["law_sha256"], "weighted lifting law SHA")
        _nonnegative_int(value["member_count"], "weighted lifting member count", upper=_MAX_FIBER_MEMBERS)
        _nonnegative_int(value["block_count"], "weighted lifting block count", upper=_MAX_FIBER_BLOCKS)
        seen_indices: set[int] = set()
        for row in checks:
            exact = _object(
                row,
                {"block_index", "roundtrip_value"},
                "weighted lifting roundtrip row",
            )
            block_index = _nonnegative_int(
                exact["block_index"],
                "weighted lifting roundtrip index",
                upper=_MAX_FIBER_BLOCKS - 1,
            )
            if block_index in seen_indices:
                raise StrictContractError("weighted lifting roundtrip index is duplicated")
            seen_indices.add(block_index)
            ExactRational.from_dict(exact["roundtrip_value"])
        expected_wire = _derive_weighted_lifting_wire(weights, law)
        if canonical_contract_bytes(value) != canonical_contract_bytes(expected_wire):
            raise StrictContractError("weighted lifting wire disagrees with authority")
        return _construct_weighted_lifting(weights, law, expected_wire)

    def lift(self, block_vector: Any) -> tuple[ExactRational, ...]:
        if self._construction_seal is not _WEIGHTED_LIFTING_SEAL:
            raise StrictContractError("weighted lifting construction seal changed")
        weights_wire, law_wire = _validated_weight_law_wires(
            self._weights, self._law
        )
        wire = _derive_weighted_lifting_wire_from_wires(weights_wire, law_wire)
        if _sha256(wire) != _canonical_digest(
            self._source_seal_sha256, "weighted lifting source seal"
        ):
            raise StrictContractError("weighted lifting retained authority changed")
        block_keys = tuple(range(weights_wire["block_count"]))
        values = _normalize_complete_vector(block_keys, block_vector, "block vector")
        result: list[ExactRational] = []
        for block_index, block_value in enumerate(values):
            for position, row in enumerate(weights_wire["rows"]):
                if row["block_index"] != block_index:
                    continue
                probability = self._law._probabilities[position]
                weight = self._weights._values[position]
                result.append(
                    _rational_divide(
                        _rational_multiply(probability, block_value), weight
                    )
                )
        return tuple(result)

    __call__ = lift

    def to_dict(self) -> dict[str, Any]:
        if self._construction_seal is not _WEIGHTED_LIFTING_SEAL:
            raise StrictContractError("weighted lifting construction seal changed")
        wire = _derive_weighted_lifting_wire(self._weights, self._law)
        if _sha256(wire) != _canonical_digest(
            self._source_seal_sha256, "weighted lifting source seal"
        ):
            raise StrictContractError("weighted lifting retained authority changed")
        return wire


def _derive_weighted_lifting_wire(
    weights: PositiveFiberWeights, law: ExactFiniteFiberLaw
) -> dict[str, Any]:
    if type(weights) is not PositiveFiberWeights or type(law) is not ExactFiniteFiberLaw:
        raise StrictContractError("weighted lifting requires exact weights and fiber law")
    weights_wire, law_wire = _validated_weight_law_wires(weights, law)
    return _derive_weighted_lifting_wire_from_wires(weights_wire, law_wire)


def _validated_weight_law_wires(
    weights: PositiveFiberWeights, law: ExactFiniteFiberLaw
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate C/L inputs while sharing one exact frame when possible."""

    if type(weights) is not PositiveFiberWeights or type(law) is not ExactFiniteFiberLaw:
        raise StrictContractError("weighted lifting requires exact weights and fiber law")
    weights.__post_init__()
    law.__post_init__()
    weights_frame = _fresh_fiber_frame(weights._generator)
    law_frame = (
        weights_frame
        if law._generator is weights._generator
        else _fresh_fiber_frame(law._generator)
    )
    weights_wire = _derive_positive_weights_wire_from_frame(
        weights_frame, weights._values
    )
    if _sha256(weights_wire) != _canonical_digest(
        weights._value_seal_sha256, "weighted lifting weight value seal"
    ):
        raise StrictContractError("weighted lifting weight authority changed")
    law_wire = _derive_fiber_law_wire_from_frame(
        law_frame, law._probabilities
    )
    if _sha256(law_wire) != _canonical_digest(
        law._value_seal_sha256, "weighted lifting law value seal"
    ):
        raise StrictContractError("weighted lifting law authority changed")
    return weights_wire, law_wire


def _derive_weighted_lifting_wire_from_wires(
    weights_wire: Mapping[str, Any], law_wire: Mapping[str, Any]
) -> dict[str, Any]:
    if weights_wire["generator_sha256"] != law_wire["generator_sha256"]:
        raise StrictContractError("weighted lifting authorities use different frames")
    weight_keys = tuple(
        (row["block_index"], row["member_id"], row["member_sha256"])
        for row in weights_wire["rows"]
    )
    law_keys = tuple(
        (row["block_index"], row["member_id"], row["member_sha256"])
        for row in law_wire["rows"]
    )
    if weight_keys != law_keys:
        raise StrictContractError("weighted lifting authorities use different members")
    # The law serializer independently proves an exact probability sum of one
    # in every block.  Substitution in C_omega L_mu,omega cancels omega exactly.
    block_basis_checks = [
        {"block_index": block_index, "roundtrip_value": ExactRational(1).to_dict()}
        for block_index in range(weights_wire["block_count"])
    ]
    return {
        "schema_version": WEIGHTED_LIFTING_SCHEMA,
        "evidence_scope": SYNTHETIC_EVIDENCE_SCOPE,
        "generator_sha256": weights_wire["generator_sha256"],
        "weights_sha256": _sha256(weights_wire),
        "law_sha256": _sha256(law_wire),
        "member_count": weights_wire["member_count"],
        "block_count": weights_wire["block_count"],
        "formula": "L_mu_omega_column_source_v1",
        "roundtrip_identity_checks": block_basis_checks,
    }


def make_weighted_lifting(
    weights: PositiveFiberWeights, law: ExactFiniteFiberLaw
) -> WeightedLifting:
    if type(weights) is not PositiveFiberWeights or type(law) is not ExactFiniteFiberLaw:
        raise StrictContractError("weighted lifting requires exact weights and fiber law")
    wire = _derive_weighted_lifting_wire(weights, law)
    return _construct_weighted_lifting(weights, law, wire)


def _construct_weighted_lifting(
    weights: PositiveFiberWeights,
    law: ExactFiniteFiberLaw,
    wire: Mapping[str, Any],
) -> WeightedLifting:
    result = object.__new__(WeightedLifting)
    object.__setattr__(result, "_weights", weights)
    object.__setattr__(result, "_law", law)
    object.__setattr__(result, "_source_seal_sha256", _sha256(wire))
    object.__setattr__(result, "_construction_seal", _WEIGHTED_LIFTING_SEAL)
    result.__post_init__()
    return result


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
        # Keep the signed-64 check before every comparison/domain lookup, but
        # avoid allocating an indexed diagnostic string on the valid hot path.
        if (
            type(raw_target) is not int
            or raw_target < 0
            or raw_target > MAX_SIGNED_64
        ):
            target = _signed64_target(raw_target, f"{where}[{index}]")
        else:
            target = raw_target
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


def _contains_sorted_target(targets: tuple[int, ...], target: int) -> bool:
    """Binary membership after the caller has exhaustively validated targets."""

    lower = 0
    upper = len(targets)
    while lower < upper:
        middle = (lower + upper) // 2
        value = targets[middle]
        if value < target:
            lower = middle + 1
        else:
            upper = middle
    return lower < len(targets) and targets[lower] == target


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
        if added_targets:
            merged_count, contains_exact = _union_target_stats(
                old_row.target_block_indices,
                added_targets,
                exact_target=exact_target,
            )
        else:
            merged_count = len(old_row.target_block_indices)
            contains_exact = _contains_sorted_target(
                old_row.target_block_indices, exact_target
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
    final_work = _tier_work_units(
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
        changed = bool(added_targets) and any(
            not _contains_sorted_target(old_row.target_block_indices, target)
            for target in added_targets
        )
        if changed:
            merged = _merge_target_tuples(
                old_row.target_block_indices, added_targets
            )
            new_rows.append(
                IntervalTargetRow(
                    old_row.source_block_index, old_row.action_id, merged
                )
            )
        else:
            new_rows.append(old_row)
    # Both inputs were exhaustively validated before allocation, and
    # `final_work` was computed over their exact union.  The strict dataclass
    # constructor performs the one remaining exhaustive output scan.
    return IntervalCandidate(
        exact_operator_sha256=context.operator_sha256,
        provenance_id=_string(provenance_id, "candidate provenance ID"),
        rows=tuple(new_rows),
        work_units=final_work,
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
    candidate_fresh = _fresh_candidate_with_context(candidate, context)
    return _derive_witness_wire_from_fresh_candidate(
        context, candidate_fresh, evidence
    )


def _derive_witness_wire_from_fresh_candidate(
    context: _ExactContext,
    candidate_fresh: IntervalCandidate,
    evidence: UppernessDomainEvidence,
) -> dict[str, Any]:
    exact_wire = context.wire
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
        return _validated_witness_wire(self)


def verify_upperness_domain(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    evidence: UppernessDomainEvidence,
) -> UppernessDomainWitness:
    return UppernessDomainWitness.verify(exact, candidate, evidence)


def _validated_witness_wire(
    witness: UppernessDomainWitness,
    *,
    shared_exact: ExactFiniteOperator | None = None,
    shared_context: _ExactContext | None = None,
    shared_candidate: IntervalCandidate | None = None,
    shared_candidate_fresh: IntervalCandidate | None = None,
) -> dict[str, Any]:
    """Validate a witness, sharing only already-validated identical authorities."""

    if type(witness) is not UppernessDomainWitness:
        raise StrictContractError("certification requires a verified upperness witness")
    if witness._construction_seal is not _WITNESS_SEAL:
        raise StrictContractError("upperness witness construction seal changed")

    if witness._exact_source is shared_exact and shared_context is not None:
        context = shared_context
    else:
        context = _exact_context(witness._exact_source)
    if context.operator_sha256 != _digest(
        witness._exact_seal_sha256, "witness exact seal"
    ):
        raise StrictContractError("witness exact source changed")

    if (
        witness._candidate_source is shared_candidate
        and shared_candidate_fresh is not None
    ):
        candidate_fresh = shared_candidate_fresh
    else:
        candidate_fresh = _fresh_candidate_with_context(
            witness._candidate_source, context
        )
    if candidate_fresh.candidate_sha256 != _digest(
        witness._candidate_seal_sha256, "witness candidate seal"
    ):
        raise StrictContractError("witness candidate source changed")
    if _sha256(witness._evidence_source.to_dict()) != _digest(
        witness._evidence_seal_sha256, "witness evidence seal"
    ):
        raise StrictContractError("witness evidence source changed")
    return _derive_witness_wire_from_fresh_candidate(
        context, candidate_fresh, witness._evidence_source
    )


def _derive_certified_wire(
    exact: ExactFiniteOperator,
    candidate: IntervalCandidate,
    witness: UppernessDomainWitness,
) -> dict[str, Any]:
    context = _exact_context(exact)
    exact_wire = context.wire
    candidate_fresh = _fresh_candidate_with_context(candidate, context)
    witness_wire = _validated_witness_wire(
        witness,
        shared_exact=exact,
        shared_context=context,
        shared_candidate=candidate,
        shared_candidate_fresh=candidate_fresh,
    )
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
    "ExactQuotientCoordinateGenerator",
    "ExactQuotientCoordinateTerm",
    "ExactQuotientTransferRow",
    "IntervalCandidate",
    "IntervalTargetRow",
    "NominalOperator",
    "ObservedIntervalOperator",
    "PositiveFiberWeights",
    "ExactFiniteFiberLaw",
    "WeightedCompression",
    "WeightedLifting",
    "UppernessDomainEvidence",
    "UppernessDomainWitness",
    "UppernessEvidenceRow",
    "build_exact_quotient_coordinate_generator",
    "certify_interval_operator",
    "export_exact_finite_operator",
    "extend_interval_candidate",
    "make_interval_candidate",
    "make_positive_fiber_weights",
    "make_exact_finite_fiber_law",
    "make_weighted_compression",
    "make_weighted_lifting",
    "verify_upperness_domain",
]
