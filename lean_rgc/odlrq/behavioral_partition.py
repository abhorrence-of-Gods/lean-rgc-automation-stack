"""Exact Moore partition refinement for admitted synthetic finite snapshots.

The implementation in this module is deliberately scoped to the
``synthetic_development`` evidence profile.  State and action IDs are only
locators into an admitted table: every canonical ordering and every certified
identity is determined by the corresponding full :class:`CanonicalPayload`
UTF-8 bytes.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from lean_rgc.lean.kernel_state_identity import StrictIdentityError, canonical_json_bytes

from .adapters import validate_synthetic_finite_snapshot
from .contracts import (
    MAX_SYNTHETIC_ACTIONS,
    MAX_SYNTHETIC_TOTALIZED_STATES,
    MAX_SYNTHETIC_TRANSITION_ROWS,
    SYNTHETIC_EVIDENCE_SCOPE,
    AdmittedExactFiniteSnapshot,
    CanonicalPayload,
    ExactAdmissionReport,
    ExactRational,
    ObservationFrameId,
    ReachableDomainId,
    ResponseVocabularyId,
    StrictContractError,
    SyntheticAction,
    SyntheticEvidenceProfile,
    SyntheticFiniteSnapshot,
    SyntheticTotalizedState,
    SyntheticTransitionRow,
    SyntheticTransitionSemanticsId,
    TotalizedStatus,
)


MAX_EXACT_PARTITION_WORK_UNITS = 250_000

EXACT_PARTITION_BLOCK_SCHEMA = "lean-rgc-odlrq-exact-partition-block-v1"
EXACT_REFINEMENT_STAGE_SCHEMA = "lean-rgc-odlrq-exact-refinement-stage-v1"
EXACT_QUOTIENT_ROW_SCHEMA = "lean-rgc-odlrq-exact-quotient-row-v1"
EXACT_DISTINGUISHING_WITNESS_SCHEMA = (
    "lean-rgc-odlrq-exact-distinguishing-witness-v1"
)
EXACT_PARTITION_WORK_COUNTERS_SCHEMA = (
    "lean-rgc-odlrq-exact-partition-work-counters-v1"
)
EXACT_PARTITION_CERTIFICATE_SCHEMA = (
    "lean-rgc-odlrq-exact-partition-certificate-v1"
)
EXACT_PARTITION_VERIFICATION_REPORT_SCHEMA = (
    "lean-rgc-odlrq-exact-partition-verification-report-v1"
)
VERIFIED_EXACT_PARTITION_SCHEMA = "lean-rgc-odlrq-verified-exact-partition-v1"


EXACT_PARTITION_VERIFICATION_CHECKS = (
    "strict_admitted_source_recomputed",
    "certificate_source_binding",
    "semantic_action_order",
    "initial_response_partition",
    "strict_refinement_trace",
    "single_fixed_point_pass",
    "response_homogeneity",
    "all_action_stability",
    "full_member_quotient",
    "shortest_semantic_lex_distinguishing_words",
    "canonical_strict_roundtrip",
    "aggregate_work_cap",
)


def _object(value: Any, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact object")
    if len(value) != len(fields):
        raise StrictContractError(f"{where} has the wrong field count")
    if any(type(key) is not str for key in value):
        raise StrictContractError(f"{where} keys must be exact strings")
    if any(key not in fields for key in value):
        missing = sorted(field for field in fields if field not in value)
        unknown = sorted(key for key in value if key not in fields)
        raise StrictContractError(
            f"{where} field mismatch; "
            f"missing={missing}, unknown={unknown}"
        )
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an array")
    return value


def _string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    return value


def _fixed_string(value: Any, expected: str, where: str) -> str:
    if type(value) is not str or value != expected:
        raise StrictContractError(f"{where} must be the exact literal {expected}")
    return value


def _strict_wire_preflight(value: Any, where: str) -> int:
    """Scan exact JSON types/UTF-8 bytes once, stopping at the work cap."""

    units = 0

    def charge(amount: int) -> None:
        nonlocal units
        if amount < 0 or units + amount > MAX_EXACT_PARTITION_WORK_UNITS:
            raise StrictContractError(
                "CPU_SURVIVOR_PREREQUISITE_BLOCKED: strict partition wire "
                "preflight exceeds 250000 aggregate units"
            )
        units += amount

    def scan_text(text: Any, label: str) -> None:
        if type(text) is not str:
            raise StrictContractError(f"{label} must be an exact string")
        charge(1)
        for character in text:
            codepoint = ord(character)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise StrictContractError(f"{label} contains an invalid surrogate")
            if codepoint <= 0x7F:
                charge(1)
            elif codepoint <= 0x7FF:
                charge(2)
            elif codepoint <= 0xFFFF:
                charge(3)
            else:
                charge(4)

    def scan(item: Any, depth: int) -> None:
        if depth > 128:
            raise StrictContractError(f"{where} exceeds the strict JSON depth cap")
        item_type = type(item)
        if item_type is dict:
            charge(1)
            for key, child in item.items():
                scan_text(key, f"{where} key")
                scan(child, depth + 1)
            return
        if item_type is list:
            charge(1)
            for child in item:
                scan(child, depth + 1)
            return
        if item_type is str:
            scan_text(item, where)
            return
        if item_type is int:
            if item < -(1 << 63) or item > (1 << 63) - 1:
                raise StrictContractError(
                    f"{where} integer is outside exact signed-64 wire range"
                )
            charge(max(1, (abs(item).bit_length() + 7) // 8))
            return
        if item_type is bool or item is None:
            charge(1)
            return
        raise StrictContractError(f"{where} is outside recursive exact JSON")

    scan(value, 0)
    return units


def _integer(
    value: Any,
    where: str,
    *,
    minimum: int = 0,
    maximum: int = (1 << 63) - 1,
) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise StrictContractError(
            f"{where} must be an exact signed-64 integer in [{minimum}, {maximum}]"
        )
    return value


def _boolean(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictContractError(f"{where} must be an exact boolean")
    return value


def _digest(value: Any, where: str) -> str:
    text = _string(value, where)
    if len(text) != 64 or any(char not in "0123456789abcdefABCDEF" for char in text):
        raise StrictContractError(f"{where} must be a full SHA-256 digest")
    return text.upper()


def _payload_bytes(value: CanonicalPayload) -> bytes:
    if type(value) is not CanonicalPayload:
        raise StrictContractError("partition payload is not an exact CanonicalPayload")
    try:
        return value.canonical_json.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:  # defensive against post-construction mutation
        raise StrictContractError("partition payload is not valid UTF-8") from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return canonical_json_bytes(value.to_dict())
    except (AttributeError, StrictIdentityError, TypeError, ValueError) as exc:
        raise StrictContractError("partition contract is not canonical strict JSON") from exc


@dataclass
class _WorkLedger:
    semantic_input_units: int = 0
    source_validation_units: int = 0
    initial_partition_units: int = 0
    refinement_units: int = 0
    quotient_units: int = 0
    distinguishing_units: int = 0
    certificate_units: int = 0

    @property
    def total_units(self) -> int:
        return (
            self.semantic_input_units
            + self.source_validation_units
            + self.initial_partition_units
            + self.refinement_units
            + self.quotient_units
            + self.distinguishing_units
            + self.certificate_units
        )

    def charge(self, category: str, units: int) -> None:
        if type(units) is not int or units < 0:
            raise StrictContractError("partition work charge is invalid")
        if self.total_units + units > MAX_EXACT_PARTITION_WORK_UNITS:
            raise StrictContractError(
                "CPU_SURVIVOR_PREREQUISITE_BLOCKED: exact partition aggregate "
                "work cap would be exceeded before work"
            )
        setattr(self, category, getattr(self, category) + units)


@dataclass(frozen=True)
class ExactPartitionBlock:
    """One block whose IDs locate complete members in the bound source."""

    block_index: int
    member_state_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self) is not ExactPartitionBlock:
            raise StrictContractError("ExactPartitionBlock subclasses are forbidden")
        _integer(self.block_index, "partition block_index")
        if (
            type(self.member_state_ids) is not tuple
            or not self.member_state_ids
            or len(self.member_state_ids) > MAX_SYNTHETIC_TOTALIZED_STATES
            or not all(type(value) is str and value for value in self.member_state_ids)
        ):
            raise StrictContractError(
                "partition member_state_ids must be a nonempty exact string tuple"
            )
        if len(self.member_state_ids) != len(set(self.member_state_ids)):
            raise StrictContractError("partition block contains duplicate state IDs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_PARTITION_BLOCK_SCHEMA,
            "block_index": self.block_index,
            "member_state_ids": list(self.member_state_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactPartitionBlock":
        if cls is not ExactPartitionBlock:
            raise StrictContractError("polymorphic partition block parsing is forbidden")
        obj = _object(
            value,
            {
                "schema_version",
                "block_index",
                "member_state_ids",
            },
            "ExactPartitionBlock",
        )
        _fixed_string(
            obj["schema_version"], EXACT_PARTITION_BLOCK_SCHEMA, "ExactPartitionBlock schema"
        )
        member_ids = _array(obj["member_state_ids"], "partition member_state_ids")
        if not member_ids or len(member_ids) > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("partition member count is outside the state cap")
        result = cls(
            block_index=_integer(obj["block_index"], "partition block_index"),
            member_state_ids=tuple(
                _string(item, "partition member state ID") for item in member_ids
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactPartitionBlock is not canonical")
        return result


@dataclass(frozen=True)
class ExactRefinementStage:
    """P0 or a strict changed round; the no-change pass is counter-only."""

    stage_index: int
    changed_from_previous: bool
    blocks: tuple[ExactPartitionBlock, ...]

    def __post_init__(self) -> None:
        if type(self) is not ExactRefinementStage:
            raise StrictContractError("ExactRefinementStage subclasses are forbidden")
        _integer(self.stage_index, "refinement stage_index")
        _boolean(self.changed_from_previous, "refinement changed_from_previous")
        if (
            type(self.blocks) is not tuple
            or not self.blocks
            or len(self.blocks) > MAX_SYNTHETIC_TOTALIZED_STATES
            or not all(type(block) is ExactPartitionBlock for block in self.blocks)
        ):
            raise StrictContractError("refinement blocks are not an exact bounded tuple")
        if tuple(block.block_index for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise StrictContractError("refinement block numbering is not contiguous")
        total_member_count = 0
        for block in self.blocks:
            total_member_count += len(block.member_state_ids)
            if total_member_count > MAX_SYNTHETIC_TOTALIZED_STATES:
                raise StrictContractError(
                    "refinement stage aggregate member count exceeds the state cap"
                )
        all_ids = tuple(
            state_id for block in self.blocks for state_id in block.member_state_ids
        )
        if len(all_ids) != len(set(all_ids)):
            raise StrictContractError("refinement stage repeats a member")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_REFINEMENT_STAGE_SCHEMA,
            "stage_index": self.stage_index,
            "changed_from_previous": self.changed_from_previous,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactRefinementStage":
        if cls is not ExactRefinementStage:
            raise StrictContractError("polymorphic refinement stage parsing is forbidden")
        obj = _object(
            value,
            {"schema_version", "stage_index", "changed_from_previous", "blocks"},
            "ExactRefinementStage",
        )
        _fixed_string(
            obj["schema_version"],
            EXACT_REFINEMENT_STAGE_SCHEMA,
            "ExactRefinementStage schema",
        )
        block_rows = _array(obj["blocks"], "refinement blocks")
        if not block_rows or len(block_rows) > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("refinement block count is outside the state cap")
        result = cls(
            stage_index=_integer(obj["stage_index"], "refinement stage_index"),
            changed_from_previous=_boolean(
                obj["changed_from_previous"], "refinement changed_from_previous"
            ),
            blocks=tuple(ExactPartitionBlock.from_dict(row) for row in block_rows),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactRefinementStage is not canonical")
        return result


@dataclass(frozen=True)
class ExactQuotientRow:
    """One structural block/action row, rechecked against every source member."""

    source_block_index: int
    action_id: str
    target_block_index: int

    def __post_init__(self) -> None:
        if type(self) is not ExactQuotientRow:
            raise StrictContractError("ExactQuotientRow subclasses are forbidden")
        _integer(self.source_block_index, "quotient source_block_index")
        _integer(self.target_block_index, "quotient target_block_index")
        _string(self.action_id, "quotient action_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_QUOTIENT_ROW_SCHEMA,
            "source_block_index": self.source_block_index,
            "action_id": self.action_id,
            "target_block_index": self.target_block_index,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactQuotientRow":
        if cls is not ExactQuotientRow:
            raise StrictContractError("polymorphic quotient row parsing is forbidden")
        obj = _object(
            value,
            {
                "schema_version",
                "source_block_index",
                "action_id",
                "target_block_index",
            },
            "ExactQuotientRow",
        )
        _fixed_string(
            obj["schema_version"], EXACT_QUOTIENT_ROW_SCHEMA, "ExactQuotientRow schema"
        )
        result = cls(
            source_block_index=_integer(
                obj["source_block_index"], "quotient source_block_index"
            ),
            action_id=_string(obj["action_id"], "quotient action_id"),
            target_block_index=_integer(
                obj["target_block_index"], "quotient target_block_index"
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactQuotientRow is not canonical")
        return result


@dataclass(frozen=True)
class ExactDistinguishingWitness:
    """The canonical shortest action word for one ordered block pair."""

    left_block_index: int
    right_block_index: int
    action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self) is not ExactDistinguishingWitness:
            raise StrictContractError(
                "ExactDistinguishingWitness subclasses are forbidden"
            )
        left = _integer(self.left_block_index, "witness left_block_index")
        right = _integer(self.right_block_index, "witness right_block_index")
        if left >= right:
            raise StrictContractError("distinguishing witness block pair is not ordered")
        if (
            type(self.action_ids) is not tuple
            or len(self.action_ids) > MAX_SYNTHETIC_TOTALIZED_STATES - 1
            or not all(type(value) is str and value for value in self.action_ids)
        ):
            raise StrictContractError("witness action_ids are not an exact string tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_DISTINGUISHING_WITNESS_SCHEMA,
            "left_block_index": self.left_block_index,
            "right_block_index": self.right_block_index,
            "action_ids": list(self.action_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactDistinguishingWitness":
        if cls is not ExactDistinguishingWitness:
            raise StrictContractError(
                "polymorphic distinguishing witness parsing is forbidden"
            )
        obj = _object(
            value,
            {
                "schema_version",
                "left_block_index",
                "right_block_index",
                "action_ids",
            },
            "ExactDistinguishingWitness",
        )
        _fixed_string(
            obj["schema_version"],
            EXACT_DISTINGUISHING_WITNESS_SCHEMA,
            "ExactDistinguishingWitness schema",
        )
        action_ids = _array(obj["action_ids"], "witness action_ids")
        if len(action_ids) > MAX_SYNTHETIC_TOTALIZED_STATES - 1:
            raise StrictContractError("distinguishing word exceeds the finite-state bound")
        result = cls(
            left_block_index=_integer(
                obj["left_block_index"], "witness left_block_index"
            ),
            right_block_index=_integer(
                obj["right_block_index"], "witness right_block_index"
            ),
            action_ids=tuple(_string(item, "witness action ID") for item in action_ids),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactDistinguishingWitness is not canonical")
        return result


@dataclass(frozen=True)
class ExactPartitionWorkCounters:
    """Auditable charges made before each producer or verifier work unit."""

    semantic_input_units: int
    source_validation_units: int
    initial_partition_units: int
    refinement_units: int
    quotient_units: int
    distinguishing_units: int
    certificate_units: int
    total_units: int
    work_limit: int = MAX_EXACT_PARTITION_WORK_UNITS

    def __post_init__(self) -> None:
        if type(self) is not ExactPartitionWorkCounters:
            raise StrictContractError("ExactPartitionWorkCounters subclasses are forbidden")
        names = (
            "semantic_input_units",
            "source_validation_units",
            "initial_partition_units",
            "refinement_units",
            "quotient_units",
            "distinguishing_units",
            "certificate_units",
            "total_units",
        )
        for name in names:
            _integer(getattr(self, name), f"partition counter {name}")
        if type(self.work_limit) is not int or self.work_limit != MAX_EXACT_PARTITION_WORK_UNITS:
            raise StrictContractError("partition work_limit is not frozen")
        subtotal = sum(getattr(self, name) for name in names[:-1])
        if self.total_units != subtotal:
            raise StrictContractError("partition work counter total is inconsistent")
        if self.total_units > self.work_limit:
            raise StrictContractError(
                "CPU_SURVIVOR_PREREQUISITE_BLOCKED: exact partition work cap exceeded"
            )

    @classmethod
    def from_ledger(cls, ledger: _WorkLedger) -> "ExactPartitionWorkCounters":
        if cls is not ExactPartitionWorkCounters:
            raise StrictContractError("polymorphic work counters are forbidden")
        return cls(
            semantic_input_units=ledger.semantic_input_units,
            source_validation_units=ledger.source_validation_units,
            initial_partition_units=ledger.initial_partition_units,
            refinement_units=ledger.refinement_units,
            quotient_units=ledger.quotient_units,
            distinguishing_units=ledger.distinguishing_units,
            certificate_units=ledger.certificate_units,
            total_units=ledger.total_units,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_PARTITION_WORK_COUNTERS_SCHEMA,
            "semantic_input_units": self.semantic_input_units,
            "source_validation_units": self.source_validation_units,
            "initial_partition_units": self.initial_partition_units,
            "refinement_units": self.refinement_units,
            "quotient_units": self.quotient_units,
            "distinguishing_units": self.distinguishing_units,
            "certificate_units": self.certificate_units,
            "total_units": self.total_units,
            "work_limit": self.work_limit,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactPartitionWorkCounters":
        if cls is not ExactPartitionWorkCounters:
            raise StrictContractError("polymorphic work-counter parsing is forbidden")
        fields = {
            "schema_version",
            "semantic_input_units",
            "source_validation_units",
            "initial_partition_units",
            "refinement_units",
            "quotient_units",
            "distinguishing_units",
            "certificate_units",
            "total_units",
            "work_limit",
        }
        obj = _object(value, fields, "ExactPartitionWorkCounters")
        _fixed_string(
            obj["schema_version"],
            EXACT_PARTITION_WORK_COUNTERS_SCHEMA,
            "ExactPartitionWorkCounters schema",
        )
        result = cls(
            **{
                name: _integer(obj[name], f"partition counter {name}")
                for name in fields - {"schema_version"}
            }
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactPartitionWorkCounters is not canonical")
        return result


def _stage_member_set(stage: ExactRefinementStage) -> frozenset[str]:
    return frozenset(
        state_id for block in stage.blocks for state_id in block.member_state_ids
    )


def _is_strict_structural_refinement(
    previous: ExactRefinementStage, current: ExactRefinementStage
) -> bool:
    if len(current.blocks) <= len(previous.blocks):
        return False
    previous_owner = {
        state_id: block.block_index
        for block in previous.blocks
        for state_id in block.member_state_ids
    }
    for block in current.blocks:
        owners = {previous_owner.get(state_id) for state_id in block.member_state_ids}
        if len(owners) != 1 or None in owners:
            return False
    return True


@dataclass(frozen=True)
class ExactPartitionCertificate:
    """Immutable, source-bound witness for the coarsest response congruence."""

    evidence_scope: str
    snapshot_sha256: str
    domain_payload_digest: str
    observation_frame_digest: str
    transition_semantics_digest: str
    response_vocabulary_digest: str
    action_alphabet_digest: str
    canonical_action_ids: tuple[str, ...]
    refinement_trace: tuple[ExactRefinementStage, ...]
    final_blocks: tuple[ExactPartitionBlock, ...]
    quotient_rows: tuple[ExactQuotientRow, ...]
    distinguishing_witnesses: tuple[ExactDistinguishingWitness, ...]
    work_counters: ExactPartitionWorkCounters
    fixed_point_passes: int = 1

    def __post_init__(self) -> None:
        if type(self) is not ExactPartitionCertificate:
            raise StrictContractError("ExactPartitionCertificate subclasses are forbidden")
        _preflight_certificate_object_shape(self)
        _fixed_string(
            self.evidence_scope,
            SYNTHETIC_EVIDENCE_SCOPE,
            "partition certificate evidence_scope",
        )
        object.__setattr__(
            self,
            "snapshot_sha256",
            _digest(self.snapshot_sha256, "partition snapshot_sha256"),
        )
        for label in (
            "domain_payload_digest",
            "observation_frame_digest",
            "transition_semantics_digest",
            "response_vocabulary_digest",
            "action_alphabet_digest",
        ):
            object.__setattr__(
                self,
                label,
                _digest(getattr(self, label), f"partition certificate {label}"),
            )
        if (
            type(self.canonical_action_ids) is not tuple
            or not self.canonical_action_ids
            or len(self.canonical_action_ids) > MAX_SYNTHETIC_ACTIONS
            or not all(type(value) is str and value for value in self.canonical_action_ids)
            or len(self.canonical_action_ids) != len(set(self.canonical_action_ids))
        ):
            raise StrictContractError(
                "partition canonical_action_ids are not an exact bounded unique tuple"
            )
        if (
            type(self.refinement_trace) is not tuple
            or not self.refinement_trace
            or len(self.refinement_trace) > MAX_SYNTHETIC_TOTALIZED_STATES
            or not all(
                type(stage) is ExactRefinementStage
                for stage in self.refinement_trace
            )
        ):
            raise StrictContractError("partition refinement_trace is not exact and bounded")
        if tuple(stage.stage_index for stage in self.refinement_trace) != tuple(
            range(len(self.refinement_trace))
        ):
            raise StrictContractError("partition refinement stage indices are not contiguous")
        if self.refinement_trace[0].changed_from_previous is not False or any(
            stage.changed_from_previous is not True
            for stage in self.refinement_trace[1:]
        ):
            raise StrictContractError("partition trace must contain P0 then strict stages")
        initial_members = _stage_member_set(self.refinement_trace[0])
        n_members = len(initial_members)
        if n_members < 3 or n_members > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("partition trace member count is outside source bounds")
        for previous, current in zip(
            self.refinement_trace, self.refinement_trace[1:]
        ):
            if _stage_member_set(current) != initial_members:
                raise StrictContractError("partition trace changes the source member set")
            if not _is_strict_structural_refinement(previous, current):
                raise StrictContractError("partition trace contains a non-strict split stage")
        if len(self.refinement_trace) - 1 > n_members - 1:
            raise StrictContractError("partition trace exceeds the finite split bound")
        if (
            type(self.final_blocks) is not tuple
            or not self.final_blocks
            or len(self.final_blocks) > MAX_SYNTHETIC_TOTALIZED_STATES
            or not all(type(block) is ExactPartitionBlock for block in self.final_blocks)
            or self.final_blocks != self.refinement_trace[-1].blocks
        ):
            raise StrictContractError("partition final_blocks do not equal the final stage")
        block_count = len(self.final_blocks)
        if _integer(self.fixed_point_passes, "partition fixed_point_passes") != 1:
            raise StrictContractError("partition must record exactly one no-change pass")
        if (
            type(self.quotient_rows) is not tuple
            or len(self.quotient_rows)
            != block_count * len(self.canonical_action_ids)
            or not all(type(row) is ExactQuotientRow for row in self.quotient_rows)
        ):
            raise StrictContractError("partition quotient row table is not structurally total")
        expected_quotient_keys = tuple(
            (block_index, action_id)
            for block_index in range(block_count)
            for action_id in self.canonical_action_ids
        )
        actual_quotient_keys = tuple(
            (row.source_block_index, row.action_id) for row in self.quotient_rows
        )
        if actual_quotient_keys != expected_quotient_keys:
            raise StrictContractError(
                "partition quotient rows are not in block/semantic-action order"
            )
        if any(
            row.target_block_index >= block_count for row in self.quotient_rows
        ):
            raise StrictContractError("partition quotient target block is out of range")
        if (
            type(self.distinguishing_witnesses) is not tuple
            or len(self.distinguishing_witnesses)
            > MAX_SYNTHETIC_TOTALIZED_STATES
            * (MAX_SYNTHETIC_TOTALIZED_STATES - 1)
            // 2
            or not all(
                type(witness) is ExactDistinguishingWitness
                for witness in self.distinguishing_witnesses
            )
        ):
            raise StrictContractError("partition distinguishing witnesses are not exact")
        expected_pairs = tuple(
            (left, right)
            for left in range(block_count)
            for right in range(left + 1, block_count)
        )
        actual_pairs = tuple(
            (witness.left_block_index, witness.right_block_index)
            for witness in self.distinguishing_witnesses
        )
        if actual_pairs != expected_pairs:
            raise StrictContractError(
                "partition must carry one ordered witness for every block pair"
            )
        action_id_set = set(self.canonical_action_ids)
        if any(
            action_id not in action_id_set
            for witness in self.distinguishing_witnesses
            for action_id in witness.action_ids
        ):
            raise StrictContractError("partition witness uses an action outside the alphabet")
        if type(self.work_counters) is not ExactPartitionWorkCounters:
            raise StrictContractError("partition work counters are not exact")

    @property
    def strict_refinement_passes(self) -> int:
        return len(self.refinement_trace) - 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_PARTITION_CERTIFICATE_SCHEMA,
            "evidence_scope": self.evidence_scope,
            "snapshot_sha256": self.snapshot_sha256,
            "domain_payload_digest": self.domain_payload_digest,
            "observation_frame_digest": self.observation_frame_digest,
            "transition_semantics_digest": self.transition_semantics_digest,
            "response_vocabulary_digest": self.response_vocabulary_digest,
            "action_alphabet_digest": self.action_alphabet_digest,
            "canonical_action_ids": list(self.canonical_action_ids),
            "refinement_trace": [
                stage.to_dict() for stage in self.refinement_trace
            ],
            "final_blocks": [block.to_dict() for block in self.final_blocks],
            "quotient_rows": [row.to_dict() for row in self.quotient_rows],
            "distinguishing_witnesses": [
                witness.to_dict() for witness in self.distinguishing_witnesses
            ],
            "work_counters": self.work_counters.to_dict(),
            "fixed_point_passes": self.fixed_point_passes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactPartitionCertificate":
        if cls is not ExactPartitionCertificate:
            raise StrictContractError("polymorphic partition certificate parsing is forbidden")
        obj = _object(
            value,
            {
                "schema_version",
                "evidence_scope",
                "snapshot_sha256",
                "domain_payload_digest",
                "observation_frame_digest",
                "transition_semantics_digest",
                "response_vocabulary_digest",
                "action_alphabet_digest",
                "canonical_action_ids",
                "refinement_trace",
                "final_blocks",
                "quotient_rows",
                "distinguishing_witnesses",
                "work_counters",
                "fixed_point_passes",
            },
            "ExactPartitionCertificate",
        )
        _fixed_string(
            obj["schema_version"],
            EXACT_PARTITION_CERTIFICATE_SCHEMA,
            "ExactPartitionCertificate schema",
        )
        _fixed_string(
            obj["evidence_scope"],
            SYNTHETIC_EVIDENCE_SCOPE,
            "ExactPartitionCertificate evidence_scope",
        )
        action_ids = _array(
            obj["canonical_action_ids"], "partition canonical_action_ids"
        )
        trace_rows = _array(obj["refinement_trace"], "partition refinement_trace")
        final_rows = _array(obj["final_blocks"], "partition final_blocks")
        quotient_rows = _array(obj["quotient_rows"], "partition quotient_rows")
        witness_rows = _array(
            obj["distinguishing_witnesses"], "partition distinguishing_witnesses"
        )
        if not action_ids or len(action_ids) > MAX_SYNTHETIC_ACTIONS:
            raise StrictContractError("certificate action count is outside the cap")
        if not trace_rows or len(trace_rows) > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("certificate refinement trace is outside the cap")
        if not final_rows or len(final_rows) > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("certificate final block count is outside the cap")
        if len(quotient_rows) > MAX_SYNTHETIC_TRANSITION_ROWS:
            raise StrictContractError("certificate quotient row count is outside the cap")
        if len(witness_rows) > (
            MAX_SYNTHETIC_TOTALIZED_STATES
            * (MAX_SYNTHETIC_TOTALIZED_STATES - 1)
            // 2
        ):
            raise StrictContractError("certificate witness count is outside the cap")
        _strict_wire_preflight(obj, "ExactPartitionCertificate")
        result = cls(
            evidence_scope=_string(obj["evidence_scope"], "certificate evidence_scope"),
            snapshot_sha256=_digest(
                obj["snapshot_sha256"], "certificate snapshot_sha256"
            ),
            domain_payload_digest=_digest(
                obj["domain_payload_digest"], "certificate domain_payload_digest"
            ),
            observation_frame_digest=_digest(
                obj["observation_frame_digest"],
                "certificate observation_frame_digest",
            ),
            transition_semantics_digest=_digest(
                obj["transition_semantics_digest"],
                "certificate transition_semantics_digest",
            ),
            response_vocabulary_digest=_digest(
                obj["response_vocabulary_digest"],
                "certificate response_vocabulary_digest",
            ),
            action_alphabet_digest=_digest(
                obj["action_alphabet_digest"],
                "certificate action_alphabet_digest",
            ),
            canonical_action_ids=tuple(
                _string(item, "certificate canonical action ID")
                for item in action_ids
            ),
            refinement_trace=tuple(
                ExactRefinementStage.from_dict(row) for row in trace_rows
            ),
            final_blocks=tuple(
                ExactPartitionBlock.from_dict(row) for row in final_rows
            ),
            quotient_rows=tuple(
                ExactQuotientRow.from_dict(row) for row in quotient_rows
            ),
            distinguishing_witnesses=tuple(
                ExactDistinguishingWitness.from_dict(row) for row in witness_rows
            ),
            work_counters=ExactPartitionWorkCounters.from_dict(obj["work_counters"]),
            fixed_point_passes=_integer(
                obj["fixed_point_passes"], "certificate fixed_point_passes"
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactPartitionCertificate is not canonical")
        return result


@dataclass(frozen=True)
class ExactPartitionVerificationReport:
    evidence_scope: str
    snapshot_sha256: str
    certificate_sha256: str
    final_block_count: int
    strict_refinement_passes: int
    distinguishing_witness_count: int
    work_counters: ExactPartitionWorkCounters
    checks: tuple[str, ...] = EXACT_PARTITION_VERIFICATION_CHECKS

    def __post_init__(self) -> None:
        if type(self) is not ExactPartitionVerificationReport:
            raise StrictContractError(
                "ExactPartitionVerificationReport subclasses are forbidden"
            )
        _fixed_string(
            self.evidence_scope,
            SYNTHETIC_EVIDENCE_SCOPE,
            "partition verification evidence_scope",
        )
        object.__setattr__(
            self,
            "snapshot_sha256",
            _digest(self.snapshot_sha256, "verification snapshot_sha256"),
        )
        object.__setattr__(
            self,
            "certificate_sha256",
            _digest(self.certificate_sha256, "verification certificate_sha256"),
        )
        for name in (
            "final_block_count",
            "strict_refinement_passes",
            "distinguishing_witness_count",
        ):
            _integer(getattr(self, name), f"verification {name}")
        if type(self.work_counters) is not ExactPartitionWorkCounters:
            raise StrictContractError("verification work counters are not exact")
        if (
            type(self.checks) is not tuple
            or len(self.checks) != len(EXACT_PARTITION_VERIFICATION_CHECKS)
            or not all(type(check) is str for check in self.checks)
            or self.checks != EXACT_PARTITION_VERIFICATION_CHECKS
        ):
            raise StrictContractError("partition verification checks are incomplete")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXACT_PARTITION_VERIFICATION_REPORT_SCHEMA,
            "evidence_scope": self.evidence_scope,
            "snapshot_sha256": self.snapshot_sha256,
            "certificate_sha256": self.certificate_sha256,
            "final_block_count": self.final_block_count,
            "strict_refinement_passes": self.strict_refinement_passes,
            "distinguishing_witness_count": self.distinguishing_witness_count,
            "work_counters": self.work_counters.to_dict(),
            "checks": list(self.checks),
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "ExactPartitionVerificationReport":
        if cls is not ExactPartitionVerificationReport:
            raise StrictContractError(
                "polymorphic partition verification parsing is forbidden"
            )
        obj = _object(
            value,
            {
                "schema_version",
                "evidence_scope",
                "snapshot_sha256",
                "certificate_sha256",
                "final_block_count",
                "strict_refinement_passes",
                "distinguishing_witness_count",
                "work_counters",
                "checks",
            },
            "ExactPartitionVerificationReport",
        )
        _fixed_string(
            obj["schema_version"],
            EXACT_PARTITION_VERIFICATION_REPORT_SCHEMA,
            "ExactPartitionVerificationReport schema",
        )
        _fixed_string(
            obj["evidence_scope"],
            SYNTHETIC_EVIDENCE_SCOPE,
            "ExactPartitionVerificationReport evidence_scope",
        )
        check_rows = _array(obj["checks"], "partition verification checks")
        if len(check_rows) != len(EXACT_PARTITION_VERIFICATION_CHECKS):
            raise StrictContractError("partition verification check count is invalid")
        _strict_wire_preflight(obj, "ExactPartitionVerificationReport")
        result = cls(
            evidence_scope=_string(obj["evidence_scope"], "verification evidence_scope"),
            snapshot_sha256=_digest(
                obj["snapshot_sha256"], "verification snapshot_sha256"
            ),
            certificate_sha256=_digest(
                obj["certificate_sha256"], "verification certificate_sha256"
            ),
            final_block_count=_integer(
                obj["final_block_count"], "verification final_block_count"
            ),
            strict_refinement_passes=_integer(
                obj["strict_refinement_passes"],
                "verification strict_refinement_passes",
            ),
            distinguishing_witness_count=_integer(
                obj["distinguishing_witness_count"],
                "verification distinguishing_witness_count",
            ),
            work_counters=ExactPartitionWorkCounters.from_dict(obj["work_counters"]),
            checks=tuple(
                _string(item, "partition verification check") for item in check_rows
            ),
        )
        if result.to_dict() != obj:
            raise StrictContractError("ExactPartitionVerificationReport is not canonical")
        return result


def _charge_utf8_units(
    ledger: _WorkLedger, category: str, value: Any, where: str
) -> None:
    text = _string(value, where)
    for character in text:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise StrictContractError(f"{where} contains an invalid UTF-8 surrogate")
        if codepoint <= 0x7F:
            width = 1
        elif codepoint <= 0x7FF:
            width = 2
        elif codepoint <= 0xFFFF:
            width = 3
        else:
            width = 4
        ledger.charge(category, width)


def _preflight_source_shape(
    admitted: AdmittedExactFiniteSnapshot,
) -> tuple[SyntheticFiniteSnapshot, int, int, int]:
    if type(admitted) is not AdmittedExactFiniteSnapshot:
        raise StrictContractError(
            "exact partition requires an exact AdmittedExactFiniteSnapshot"
        )
    _fixed_string(
        admitted.evidence_scope,
        SYNTHETIC_EVIDENCE_SCOPE,
        "admitted partition source evidence_scope",
    )
    if type(admitted.snapshot) is not SyntheticFiniteSnapshot:
        raise StrictContractError("admitted partition source snapshot is not exact")
    if type(admitted.admission_report) is not ExactAdmissionReport:
        raise StrictContractError("admitted partition source report is not exact")
    snapshot = admitted.snapshot
    for label, value, expected in (
        ("domain_id", snapshot.domain_id, ReachableDomainId),
        (
            "response_vocabulary_id",
            snapshot.response_vocabulary_id,
            ResponseVocabularyId,
        ),
        ("observation_frame_id", snapshot.observation_frame_id, ObservationFrameId),
        (
            "transition_semantics_id",
            snapshot.transition_semantics_id,
            SyntheticTransitionSemanticsId,
        ),
        ("evidence_profile", snapshot.evidence_profile, SyntheticEvidenceProfile),
    ):
        if type(value) is not expected:
            raise StrictContractError(
                f"admitted partition source {label} is not an exact type"
            )
    for label, values, expected in (
        ("states", snapshot.states, SyntheticTotalizedState),
        ("actions", snapshot.actions, SyntheticAction),
        ("transitions", snapshot.transitions, SyntheticTransitionRow),
    ):
        if type(values) is not tuple or not all(type(value) is expected for value in values):
            raise StrictContractError(f"admitted partition source {label} are not exact")
    if type(snapshot.seed_state_ids) is not tuple or not all(
        type(value) is str and value for value in snapshot.seed_state_ids
    ):
        raise StrictContractError("admitted partition source seed IDs are not exact")
    n_states = len(snapshot.states)
    n_actions = len(snapshot.actions)
    n_rows = len(snapshot.transitions)
    if n_states < 3 or n_states > MAX_SYNTHETIC_TOTALIZED_STATES:
        raise StrictContractError("partition source state count is outside the cap")
    if n_actions < 1 or n_actions > MAX_SYNTHETIC_ACTIONS:
        raise StrictContractError("partition source action count is outside the cap")
    if (
        n_rows != n_states * n_actions
        or n_rows > MAX_SYNTHETIC_TRANSITION_ROWS
    ):
        raise StrictContractError("partition source transition shape is outside the cap")
    return snapshot, n_states, n_actions, n_rows


def _charge_semantic_source_units(
    snapshot: SyntheticFiniteSnapshot, ledger: _WorkLedger
) -> None:
    """Measure semantic bytes without making an M2 copy or sorting a member."""

    vocabulary = snapshot.response_vocabulary_id
    if type(vocabulary) is not ResponseVocabularyId:
        raise StrictContractError("partition source response vocabulary is not exact")
    if type(vocabulary.coordinate_names) is not tuple:
        raise StrictContractError("partition source coordinate names are not exact")
    for name in vocabulary.coordinate_names:
        _charge_utf8_units(
            ledger, "semantic_input_units", name, "partition coordinate name"
        )
    for state_id in snapshot.seed_state_ids:
        _charge_utf8_units(
            ledger, "semantic_input_units", state_id, "partition seed state ID"
        )
    for state in snapshot.states:
        _charge_utf8_units(
            ledger, "semantic_input_units", state.state_id, "partition state ID"
        )
        if type(state.payload) is not CanonicalPayload:
            raise StrictContractError("partition state payload is not exact")
        _charge_utf8_units(
            ledger,
            "semantic_input_units",
            state.payload.canonical_json,
            "partition state payload",
        )
        if type(state.totalized_kind) is not TotalizedStatus:
            raise StrictContractError("partition state totalized kind is not exact")
        _charge_utf8_units(
            ledger,
            "semantic_input_units",
            state.totalized_kind.value,
            "partition response kind",
        )
        if type(state.response_coordinates) is not tuple:
            raise StrictContractError("partition state response coordinates are not exact")
        for rational in state.response_coordinates:
            if type(rational) is not ExactRational:
                raise StrictContractError(
                    "partition state response coordinate member is not exact"
                )
            _charge_utf8_units(
                ledger,
                "semantic_input_units",
                str(rational.numerator),
                "rational numerator decimal",
            )
            _charge_utf8_units(
                ledger,
                "semantic_input_units",
                str(rational.denominator),
                "rational denominator decimal",
            )
        _charge_utf8_units(
            ledger, "semantic_input_units", state.frame_digest, "partition state frame ID"
        )
    for action in snapshot.actions:
        _charge_utf8_units(
            ledger, "semantic_input_units", action.action_id, "partition action ID"
        )
        if type(action.payload) is not CanonicalPayload:
            raise StrictContractError("partition action payload is not exact")
        _charge_utf8_units(
            ledger,
            "semantic_input_units",
            action.payload.canonical_json,
            "partition action payload",
        )
    for row in snapshot.transitions:
        for value, label in (
            (row.source_state_id, "partition row source ID"),
            (row.action_id, "partition row action ID"),
            (row.target_state_id, "partition row target ID"),
            (row.transition_semantics_digest, "partition row semantics ID"),
        ):
            _charge_utf8_units(ledger, "semantic_input_units", value, label)
    # Typed source bindings are also semantic IDs, but are charged once rather
    # than once per certificate stage.
    domain = snapshot.domain_id
    for label in (
        "environment_digest",
        "frame_digest",
        "transition_semantics_digest",
        "seed_set_digest",
        "action_alphabet_digest",
        "domain_payload_digest",
    ):
        _charge_utf8_units(
            ledger,
            "semantic_input_units",
            getattr(domain, label),
            f"partition domain {label}",
        )
    _charge_utf8_units(
        ledger,
        "semantic_input_units",
        vocabulary.coordinate_schema_digest,
        "partition coordinate schema digest",
    )
    _charge_utf8_units(
        ledger,
        "semantic_input_units",
        vocabulary.vocabulary_digest,
        "partition vocabulary digest",
    )


def _prepare_source(
    admitted: AdmittedExactFiniteSnapshot, ledger: _WorkLedger
) -> SyntheticFiniteSnapshot:
    snapshot, n_states, n_actions, _ = _preflight_source_shape(admitted)
    # This charge is completed before any M2 map, copy, or semantic sort.
    _charge_semantic_source_units(snapshot, ledger)
    coordinate_count = len(snapshot.response_vocabulary_id.coordinate_names)
    ledger.charge(
        "source_validation_units",
        n_states * n_actions
        + n_states * coordinate_count
        + n_states
        + n_actions,
    )
    expected_report = validate_synthetic_finite_snapshot(snapshot)
    if _canonical_bytes(expected_report) != _canonical_bytes(admitted.admission_report):
        raise StrictContractError(
            "admitted partition source report does not match recomputed admission"
        )
    return snapshot


def _canonical_blocks_from_groups(
    groups: Any,
    state_payload_key: dict[str, bytes],
) -> tuple[ExactPartitionBlock, ...]:
    canonical_groups: list[tuple[tuple[bytes, ...], tuple[str, ...]]] = []
    for group in groups:
        member_ids = tuple(
            sorted(group, key=lambda state_id: state_payload_key[state_id])
        )
        payload_key = tuple(state_payload_key[state_id] for state_id in member_ids)
        canonical_groups.append((payload_key, member_ids))
    canonical_groups.sort(key=lambda item: item[0])
    return tuple(
        ExactPartitionBlock(block_index, member_ids)
        for block_index, (_, member_ids) in enumerate(canonical_groups)
    )


def _block_owner(blocks: tuple[ExactPartitionBlock, ...]) -> dict[str, int]:
    return {
        state_id: block.block_index
        for block in blocks
        for state_id in block.member_state_ids
    }


def _producer_refinement_pass(
    blocks: tuple[ExactPartitionBlock, ...],
    state_by_id: dict[str, SyntheticTotalizedState],
    transition_target: dict[tuple[str, str], str],
    actions: tuple[SyntheticAction, ...],
    state_payload_key: dict[str, bytes],
) -> tuple[ExactPartitionBlock, ...]:
    """Producer-only signature refinement; the verifier never calls this."""

    owner = _block_owner(blocks)
    new_groups: list[list[str]] = []
    for block in blocks:
        buckets: dict[
            tuple[str, tuple[tuple[int, int], ...], tuple[int, ...]], list[str]
        ] = {}
        for state_id in block.member_state_ids:
            state = state_by_id[state_id]
            kind, coordinates = state.response_key
            signature = (
                kind,
                coordinates,
                tuple(
                    owner[transition_target[(state_id, action.action_id)]]
                    for action in actions
                ),
            )
            buckets.setdefault(signature, []).append(state_id)
        new_groups.extend(buckets.values())
    return _canonical_blocks_from_groups(new_groups, state_payload_key)


def _charge_refinement_pass(
    ledger: _WorkLedger,
    *,
    n_states: int,
    n_actions: int,
    coordinate_count: int,
    block_count: int,
) -> None:
    ledger.charge(
        "refinement_units",
        n_states * (n_actions + coordinate_count + 1) + block_count,
    )


def _produce_distinguishing_witnesses(
    blocks: tuple[ExactPartitionBlock, ...],
    quotient_rows: tuple[ExactQuotientRow, ...],
    canonical_actions: tuple[SyntheticAction, ...],
    state_by_id: dict[str, SyntheticTotalizedState],
    ledger: _WorkLedger,
) -> tuple[ExactDistinguishingWitness, ...]:
    block_count = len(blocks)
    pair_count = block_count * (block_count - 1) // 2
    coordinate_count = (
        len(state_by_id[blocks[0].member_state_ids[0]].response_coordinates)
        if blocks
        else 0
    )
    ledger.charge(
        "distinguishing_units",
        pair_count * (len(canonical_actions) + coordinate_count + 1),
    )
    pairs = tuple(
        (left, right)
        for left in range(block_count)
        for right in range(left + 1, block_count)
    )
    quotient = {
        (row.source_block_index, row.action_id): row.target_block_index
        for row in quotient_rows
    }
    response = {
        block.block_index: state_by_id[block.member_state_ids[0]].response_key
        for block in blocks
    }
    reverse: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for pair in pairs:
        left, right = pair
        for action in canonical_actions:
            next_left = quotient[(left, action.action_id)]
            next_right = quotient[(right, action.action_id)]
            if next_left == next_right:
                continue
            successor = (
                (next_left, next_right)
                if next_left < next_right
                else (next_right, next_left)
            )
            reverse[successor].append(pair)
    distance: dict[tuple[int, int], int] = {}
    queue: deque[tuple[int, int]] = deque()
    for pair in pairs:
        if response[pair[0]] != response[pair[1]]:
            distance[pair] = 0
            queue.append(pair)
    while queue:
        separated = queue.popleft()
        next_distance = distance[separated] + 1
        for predecessor in reverse.get(separated, ()):
            if predecessor not in distance:
                distance[predecessor] = next_distance
                queue.append(predecessor)
    if len(distance) != len(pairs):
        raise StrictContractError(
            "producer final blocks contain a behaviorally indistinguishable pair"
        )
    ledger.charge(
        "distinguishing_units",
        sum(
            distance[pair] * len(canonical_actions) + 1 for pair in pairs
        ),
    )
    witnesses: list[ExactDistinguishingWitness] = []
    for left, right in pairs:
        current = (left, right)
        word: list[str] = []
        while distance[current] > 0:
            required = distance[current] - 1
            selected: str | None = None
            selected_pair: tuple[int, int] | None = None
            for action in canonical_actions:
                next_left = quotient[(current[0], action.action_id)]
                next_right = quotient[(current[1], action.action_id)]
                if next_left == next_right:
                    continue
                successor = (
                    (next_left, next_right)
                    if next_left < next_right
                    else (next_right, next_left)
                )
                if distance.get(successor) == required:
                    selected = action.action_id
                    selected_pair = successor
                    break
            if selected is None or selected_pair is None:
                raise StrictContractError("producer could not reconstruct a shortest witness")
            word.append(selected)
            current = selected_pair
        witnesses.append(
            ExactDistinguishingWitness(left, right, tuple(word))
        )
    return tuple(witnesses)


def _charge_certificate_output(
    ledger: _WorkLedger,
    *,
    binding_values: tuple[str, ...],
    canonical_action_ids: tuple[str, ...],
    trace: tuple[ExactRefinementStage, ...],
    final_blocks: tuple[ExactPartitionBlock, ...],
    quotient_rows: tuple[ExactQuotientRow, ...],
    witnesses: tuple[ExactDistinguishingWitness, ...],
) -> None:
    """Charge locator duplication before constructing/serializing a result."""

    bindings = (
        EXACT_PARTITION_CERTIFICATE_SCHEMA,
        *binding_values,
    )
    for value in bindings:
        _charge_utf8_units(
            ledger, "certificate_units", value, "partition certificate binding"
        )
    for action_id in canonical_action_ids:
        _charge_utf8_units(
            ledger,
            "certificate_units",
            action_id,
            "partition certificate canonical action ID",
        )
    for stage in trace:
        ledger.charge("certificate_units", 2 + len(stage.blocks))
        for block in stage.blocks:
            for state_id in block.member_state_ids:
                _charge_utf8_units(
                    ledger,
                    "certificate_units",
                    state_id,
                    "partition certificate trace state ID",
                )
    for block in final_blocks:
        ledger.charge("certificate_units", 1)
        for state_id in block.member_state_ids:
            _charge_utf8_units(
                ledger,
                "certificate_units",
                state_id,
                "partition certificate final state ID",
            )
    for row in quotient_rows:
        ledger.charge("certificate_units", 2)
        _charge_utf8_units(
            ledger,
            "certificate_units",
            row.action_id,
            "partition certificate quotient action ID",
        )
    for witness in witnesses:
        ledger.charge("certificate_units", 2)
        for action_id in witness.action_ids:
            _charge_utf8_units(
                ledger,
                "certificate_units",
                action_id,
                "partition certificate witness action ID",
            )


def refine_exact_partition(
    admitted: AdmittedExactFiniteSnapshot,
) -> ExactPartitionCertificate:
    """Produce the exact coarsest response congruence or fail without a result."""

    ledger = _WorkLedger()
    snapshot = _prepare_source(admitted, ledger)
    n_states = len(snapshot.states)
    n_actions = len(snapshot.actions)
    coordinate_count = len(snapshot.response_vocabulary_id.coordinate_names)
    ledger.charge(
        "initial_partition_units",
        n_states * (coordinate_count + 1) + n_actions,
    )
    state_by_id = {state.state_id: state for state in snapshot.states}
    state_payload_key = {
        state.state_id: _payload_bytes(state.payload) for state in snapshot.states
    }
    action_payload_key = {
        action.action_id: _payload_bytes(action.payload) for action in snapshot.actions
    }
    canonical_actions = tuple(
        sorted(snapshot.actions, key=lambda action: action_payload_key[action.action_id])
    )
    transition_target = {
        (row.source_state_id, row.action_id): row.target_state_id
        for row in snapshot.transitions
    }
    response_groups: dict[
        tuple[str, tuple[tuple[int, int], ...]], list[str]
    ] = {}
    for state in sorted(
        snapshot.states, key=lambda state: state_payload_key[state.state_id]
    ):
        response_groups.setdefault(state.response_key, []).append(state.state_id)
    blocks = _canonical_blocks_from_groups(
        response_groups.values(), state_payload_key
    )
    trace: list[ExactRefinementStage] = [
        ExactRefinementStage(0, False, blocks)
    ]
    strict_rounds = 0
    while True:
        _charge_refinement_pass(
            ledger,
            n_states=n_states,
            n_actions=n_actions,
            coordinate_count=coordinate_count,
            block_count=len(blocks),
        )
        refined = _producer_refinement_pass(
            blocks,
            state_by_id,
            transition_target,
            canonical_actions,
            state_payload_key,
        )
        if refined == blocks:
            break
        if len(refined) <= len(blocks):
            raise StrictContractError("producer refinement pass was not a strict split")
        strict_rounds += 1
        if strict_rounds > n_states - 1:
            raise StrictContractError("producer refinement exceeded the finite split bound")
        blocks = refined
        trace.append(ExactRefinementStage(strict_rounds, True, blocks))
    owner = _block_owner(blocks)
    ledger.charge("quotient_units", n_states * n_actions)
    quotient_rows: list[ExactQuotientRow] = []
    for block in blocks:
        for action in canonical_actions:
            target_blocks = {
                owner[transition_target[(state_id, action.action_id)]]
                for state_id in block.member_state_ids
            }
            if len(target_blocks) != 1:
                raise StrictContractError(
                    "producer final partition is not stable for every block member"
                )
            quotient_rows.append(
                ExactQuotientRow(
                    block.block_index,
                    action.action_id,
                    next(iter(target_blocks)),
                )
            )
    quotient_tuple = tuple(quotient_rows)
    witnesses = _produce_distinguishing_witnesses(
        blocks, quotient_tuple, canonical_actions, state_by_id, ledger
    )
    trace_tuple = tuple(trace)
    canonical_action_ids = tuple(action.action_id for action in canonical_actions)
    _charge_certificate_output(
        ledger,
        binding_values=(
            SYNTHETIC_EVIDENCE_SCOPE,
            admitted.admission_report.snapshot_sha256,
            snapshot.domain_id.domain_payload_digest,
            snapshot.domain_id.frame_digest,
            snapshot.domain_id.transition_semantics_digest,
            snapshot.response_vocabulary_id.vocabulary_digest,
            snapshot.domain_id.action_alphabet_digest,
        ),
        canonical_action_ids=canonical_action_ids,
        trace=trace_tuple,
        final_blocks=blocks,
        quotient_rows=quotient_tuple,
        witnesses=witnesses,
    )
    certificate = ExactPartitionCertificate(
        evidence_scope=SYNTHETIC_EVIDENCE_SCOPE,
        snapshot_sha256=admitted.admission_report.snapshot_sha256,
        domain_payload_digest=snapshot.domain_id.domain_payload_digest,
        observation_frame_digest=snapshot.domain_id.frame_digest,
        transition_semantics_digest=snapshot.domain_id.transition_semantics_digest,
        response_vocabulary_digest=snapshot.response_vocabulary_id.vocabulary_digest,
        action_alphabet_digest=snapshot.domain_id.action_alphabet_digest,
        canonical_action_ids=canonical_action_ids,
        refinement_trace=trace_tuple,
        final_blocks=blocks,
        quotient_rows=quotient_tuple,
        distinguishing_witnesses=witnesses,
        work_counters=ExactPartitionWorkCounters.from_ledger(ledger),
        fixed_point_passes=1,
    )
    # Return only a certificate that survives its strict immutable wire format.
    roundtripped = ExactPartitionCertificate.from_dict(certificate.to_dict())
    if roundtripped != certificate:
        raise StrictContractError("partition certificate failed its strict roundtrip")
    return roundtripped


def _preflight_certificate_object_shape(
    certificate: ExactPartitionCertificate,
    ledger: _WorkLedger | None = None,
) -> None:
    structural_units = 0

    def charge(units: int, *, ledger_account: bool = True) -> None:
        nonlocal structural_units
        structural_units += units
        if structural_units > MAX_EXACT_PARTITION_WORK_UNITS:
            raise StrictContractError(
                "CPU_SURVIVOR_PREREQUISITE_BLOCKED: certificate nested locator "
                "shape exceeds 250000 aggregate units"
            )
        if ledger is not None and ledger_account:
            ledger.charge("certificate_units", units)

    def scan_locator(value: Any, where: str) -> None:
        if type(value) is not str or not value:
            raise StrictContractError(f"{where} is not an exact nonempty string")
        for character in value:
            codepoint = ord(character)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise StrictContractError(f"{where} contains an invalid surrogate")
            if codepoint <= 0x7F:
                width = 1
            elif codepoint <= 0x7FF:
                width = 2
            elif codepoint <= 0xFFFF:
                width = 3
            else:
                width = 4
            # Output serialization is separately charged to a verifier ledger;
            # this local byte scan bounds direct base-class construction.
            charge(width, ledger_account=False)

    if type(certificate) is not ExactPartitionCertificate:
        raise StrictContractError("partition verifier requires an exact certificate type")
    if (
        type(certificate.canonical_action_ids) is not tuple
        or not certificate.canonical_action_ids
        or len(certificate.canonical_action_ids) > MAX_SYNTHETIC_ACTIONS
    ):
        raise StrictContractError("certificate action locator shape is invalid")
    for action_id in certificate.canonical_action_ids:
        charge(1)
        scan_locator(action_id, "certificate action locator")
    if (
        type(certificate.refinement_trace) is not tuple
        or not certificate.refinement_trace
        or len(certificate.refinement_trace) > MAX_SYNTHETIC_TOTALIZED_STATES
    ):
        raise StrictContractError("certificate trace shape is invalid")
    for stage in certificate.refinement_trace:
        charge(1)
        if type(stage) is not ExactRefinementStage or type(stage.blocks) is not tuple:
            raise StrictContractError("certificate trace stage shape is invalid")
        if not stage.blocks or len(stage.blocks) > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError("certificate trace block count is invalid")
        for block in stage.blocks:
            charge(1)
            if (
                type(block) is not ExactPartitionBlock
                or type(block.member_state_ids) is not tuple
                or not block.member_state_ids
                or len(block.member_state_ids) > MAX_SYNTHETIC_TOTALIZED_STATES
            ):
                raise StrictContractError("certificate trace member shape is invalid")
            for state_id in block.member_state_ids:
                charge(1)
                scan_locator(state_id, "certificate trace locator")
    if (
        type(certificate.final_blocks) is not tuple
        or not certificate.final_blocks
        or len(certificate.final_blocks) > MAX_SYNTHETIC_TOTALIZED_STATES
    ):
        raise StrictContractError("certificate final block shape is invalid")
    final_member_count = 0
    for block in certificate.final_blocks:
        charge(1)
        if (
            type(block) is not ExactPartitionBlock
            or type(block.member_state_ids) is not tuple
            or not block.member_state_ids
            or len(block.member_state_ids) > MAX_SYNTHETIC_TOTALIZED_STATES
        ):
            raise StrictContractError("certificate final member shape is invalid")
        final_member_count += len(block.member_state_ids)
        if final_member_count > MAX_SYNTHETIC_TOTALIZED_STATES:
            raise StrictContractError(
                "certificate final aggregate membership exceeds the state cap"
            )
        for state_id in block.member_state_ids:
            charge(1)
            scan_locator(state_id, "certificate final locator")
    if (
        type(certificate.quotient_rows) is not tuple
        or len(certificate.quotient_rows) > MAX_SYNTHETIC_TRANSITION_ROWS
    ):
        raise StrictContractError("certificate quotient shape is invalid")
    for row in certificate.quotient_rows:
        charge(1)
        if type(row) is not ExactQuotientRow:
            raise StrictContractError("certificate quotient row is not exact")
        scan_locator(row.action_id, "certificate quotient action locator")
    if (
        type(certificate.distinguishing_witnesses) is not tuple
        or len(certificate.distinguishing_witnesses)
        > MAX_SYNTHETIC_TOTALIZED_STATES
        * (MAX_SYNTHETIC_TOTALIZED_STATES - 1)
        // 2
    ):
        raise StrictContractError("certificate witness shape is invalid")
    for witness in certificate.distinguishing_witnesses:
        charge(1)
        if (
            type(witness) is not ExactDistinguishingWitness
            or type(witness.action_ids) is not tuple
            or len(witness.action_ids) > MAX_SYNTHETIC_TOTALIZED_STATES - 1
        ):
            raise StrictContractError("certificate witness word shape is invalid")
        for action_id in witness.action_ids:
            charge(1)
            scan_locator(action_id, "certificate witness locator")
    if type(certificate.work_counters) is not ExactPartitionWorkCounters:
        raise StrictContractError("certificate work counter shape is invalid")


def _certificate_binding_values(
    certificate: ExactPartitionCertificate,
) -> tuple[str, ...]:
    return (
        certificate.evidence_scope,
        certificate.snapshot_sha256,
        certificate.domain_payload_digest,
        certificate.observation_frame_digest,
        certificate.transition_semantics_digest,
        certificate.response_vocabulary_digest,
        certificate.action_alphabet_digest,
    )


def _verifier_relation_refinement(
    blocks: tuple[ExactPartitionBlock, ...],
    state_by_id: dict[str, SyntheticTotalizedState],
    transition_target: dict[tuple[str, str], str],
    actions: tuple[SyntheticAction, ...],
    state_payload_key: dict[str, bytes],
) -> tuple[ExactPartitionBlock, ...]:
    """Pair-relation refinement, structurally separate from producer signatures."""

    owner = _block_owner(blocks)
    relation_classes: list[list[str]] = []
    for block in blocks:
        classes_inside_block: list[list[str]] = []
        for state_id in block.member_state_ids:
            state = state_by_id[state_id]
            matched = False
            for relation_class in classes_inside_block:
                representative_id = relation_class[0]
                representative = state_by_id[representative_id]
                if state.response_key != representative.response_key:
                    continue
                pair_is_related = True
                for action in actions:
                    left_target = transition_target[(state_id, action.action_id)]
                    right_target = transition_target[
                        (representative_id, action.action_id)
                    ]
                    if owner[left_target] != owner[right_target]:
                        pair_is_related = False
                        break
                if pair_is_related:
                    relation_class.append(state_id)
                    matched = True
                    break
            if not matched:
                classes_inside_block.append([state_id])
        relation_classes.extend(classes_inside_block)
    return _canonical_blocks_from_groups(relation_classes, state_payload_key)


def _charge_verifier_relation_pass(
    ledger: _WorkLedger,
    *,
    blocks: tuple[ExactPartitionBlock, ...],
    n_actions: int,
    coordinate_count: int,
) -> None:
    pair_relation_bound = sum(
        len(block.member_state_ids) ** 2 for block in blocks
    )
    ledger.charge(
        "refinement_units",
        pair_relation_bound * (n_actions + coordinate_count + 1)
        + len(blocks),
    )


def _verify_distinguishing_words_by_state_pair_relation(
    *,
    snapshot: SyntheticFiniteSnapshot,
    blocks: tuple[ExactPartitionBlock, ...],
    canonical_actions: tuple[SyntheticAction, ...],
    state_by_id: dict[str, SyntheticTotalizedState],
    state_payload_key: dict[str, bytes],
    transition_target: dict[tuple[str, str], str],
    ledger: _WorkLedger,
) -> tuple[ExactDistinguishingWitness, ...]:
    """Independently compute reverse distances on the raw state-pair relation."""

    state_count = len(state_by_id)
    pair_count = state_count * (state_count - 1) // 2
    coordinate_count = len(snapshot.response_vocabulary_id.coordinate_names)
    ledger.charge(
        "distinguishing_units",
        pair_count * (len(canonical_actions) + coordinate_count + 1),
    )
    ordered_state_ids = tuple(
        sorted(state_by_id, key=lambda state_id: state_payload_key[state_id])
    )
    state_rank = {
        state_id: index for index, state_id in enumerate(ordered_state_ids)
    }
    pairs = tuple(
        (left, right)
        for left in range(len(ordered_state_ids))
        for right in range(left + 1, len(ordered_state_ids))
    )
    raw_successor: dict[tuple[int, str], int] = {}
    for state_index, state_id in enumerate(ordered_state_ids):
        for action in canonical_actions:
            target_id = transition_target[(state_id, action.action_id)]
            raw_successor[(state_index, action.action_id)] = state_rank[target_id]
    reverse: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for left, right in pairs:
        for action in canonical_actions:
            next_left = raw_successor[(left, action.action_id)]
            next_right = raw_successor[(right, action.action_id)]
            if next_left == next_right:
                continue
            successor = (
                (next_left, next_right)
                if next_left < next_right
                else (next_right, next_left)
            )
            reverse[successor].append((left, right))
    distance: dict[tuple[int, int], int] = {}
    queue: deque[tuple[int, int]] = deque()
    for pair in pairs:
        left_response = state_by_id[ordered_state_ids[pair[0]]].response_key
        right_response = state_by_id[ordered_state_ids[pair[1]]].response_key
        if left_response != right_response:
            distance[pair] = 0
            queue.append(pair)
    while queue:
        pair = queue.popleft()
        predecessor_distance = distance[pair] + 1
        for predecessor in reverse.get(pair, ()):
            if predecessor not in distance:
                distance[predecessor] = predecessor_distance
                queue.append(predecessor)
    representative_pairs: list[tuple[int, int, tuple[int, int]]] = []
    for left_block in range(len(blocks)):
        for right_block in range(left_block + 1, len(blocks)):
            left_rank = state_rank[blocks[left_block].member_state_ids[0]]
            right_rank = state_rank[blocks[right_block].member_state_ids[0]]
            state_pair = (
                (left_rank, right_rank)
                if left_rank < right_rank
                else (right_rank, left_rank)
            )
            if state_pair not in distance:
                raise StrictContractError(
                    "final blocks contain an indistinguishable raw state pair"
                )
            representative_pairs.append((left_block, right_block, state_pair))
    ledger.charge(
        "distinguishing_units",
        sum(
            distance[state_pair] * len(canonical_actions) + 1
            for _, _, state_pair in representative_pairs
        ),
    )
    expected: list[ExactDistinguishingWitness] = []
    for left_block, right_block, start_pair in representative_pairs:
        current = start_pair
        word: list[str] = []
        while distance[current] > 0:
            needed = distance[current] - 1
            chosen_action: str | None = None
            chosen_pair: tuple[int, int] | None = None
            for action in canonical_actions:
                next_left = raw_successor[(current[0], action.action_id)]
                next_right = raw_successor[(current[1], action.action_id)]
                if next_left == next_right:
                    continue
                successor = (
                    (next_left, next_right)
                    if next_left < next_right
                    else (next_right, next_left)
                )
                if distance.get(successor) == needed:
                    chosen_action = action.action_id
                    chosen_pair = successor
                    break
            if chosen_action is None or chosen_pair is None:
                raise StrictContractError(
                    "state-pair verifier could not reconstruct a shortest word"
                )
            word.append(chosen_action)
            current = chosen_pair
        expected.append(
            ExactDistinguishingWitness(left_block, right_block, tuple(word))
        )
    return tuple(expected)


def _recompute_producer_work_counters(
    *,
    semantic_input_units: int,
    snapshot: SyntheticFiniteSnapshot,
    certificate: ExactPartitionCertificate,
) -> ExactPartitionWorkCounters:
    ledger = _WorkLedger()
    ledger.charge("semantic_input_units", semantic_input_units)
    n_states = len(snapshot.states)
    n_actions = len(snapshot.actions)
    coordinate_count = len(snapshot.response_vocabulary_id.coordinate_names)
    ledger.charge(
        "source_validation_units",
        n_states * n_actions
        + n_states * coordinate_count
        + n_states
        + n_actions,
    )
    ledger.charge(
        "initial_partition_units",
        n_states * (coordinate_count + 1) + n_actions,
    )
    # There is one producer pass from each stored stage: every nonfinal pass
    # yields the next strict stage and the final pass is the required no-change.
    for stage in certificate.refinement_trace:
        _charge_refinement_pass(
            ledger,
            n_states=n_states,
            n_actions=n_actions,
            coordinate_count=coordinate_count,
            block_count=len(stage.blocks),
        )
    ledger.charge("quotient_units", n_states * n_actions)
    block_count = len(certificate.final_blocks)
    pair_count = block_count * (block_count - 1) // 2
    ledger.charge(
        "distinguishing_units",
        pair_count * (n_actions + coordinate_count + 1),
    )
    ledger.charge(
        "distinguishing_units",
        sum(
            len(witness.action_ids) * n_actions + 1
            for witness in certificate.distinguishing_witnesses
        ),
    )
    _charge_certificate_output(
        ledger,
        binding_values=_certificate_binding_values(certificate),
        canonical_action_ids=certificate.canonical_action_ids,
        trace=certificate.refinement_trace,
        final_blocks=certificate.final_blocks,
        quotient_rows=certificate.quotient_rows,
        witnesses=certificate.distinguishing_witnesses,
    )
    return ExactPartitionWorkCounters.from_ledger(ledger)


def _charge_verification_report_output(
    ledger: _WorkLedger, *, snapshot_sha256: str, certificate_sha256: str
) -> None:
    """Conservatively reserve report construction and strict roundtrip work."""

    fixed_strings = (
        EXACT_PARTITION_VERIFICATION_REPORT_SCHEMA,
        EXACT_PARTITION_WORK_COUNTERS_SCHEMA,
        SYNTHETIC_EVIDENCE_SCOPE,
        snapshot_sha256,
        certificate_sha256,
        *EXACT_PARTITION_VERIFICATION_CHECKS,
        "semantic_input_units",
        "source_validation_units",
        "initial_partition_units",
        "refinement_units",
        "quotient_units",
        "distinguishing_units",
        "certificate_units",
        "total_units",
        "work_limit",
    )
    for value in fixed_strings:
        _charge_utf8_units(
            ledger,
            "certificate_units",
            value,
            "partition verification report field",
        )
    ledger.charge(
        "certificate_units",
        32 + len(EXACT_PARTITION_VERIFICATION_CHECKS),
    )


def _verify_exact_partition_core(
    admitted: AdmittedExactFiniteSnapshot,
    certificate: ExactPartitionCertificate,
) -> ExactPartitionVerificationReport:
    if type(certificate) is not ExactPartitionCertificate:
        raise StrictContractError("partition verifier requires an exact certificate")
    ledger = _WorkLedger()
    snapshot = _prepare_source(admitted, ledger)
    _preflight_certificate_object_shape(certificate, ledger)
    # Charge every repeated locator before certificate copying or roundtrip.
    _charge_certificate_output(
        ledger,
        binding_values=_certificate_binding_values(certificate),
        canonical_action_ids=certificate.canonical_action_ids,
        trace=certificate.refinement_trace,
        final_blocks=certificate.final_blocks,
        quotient_rows=certificate.quotient_rows,
        witnesses=certificate.distinguishing_witnesses,
    )
    n_states = len(snapshot.states)
    n_actions = len(snapshot.actions)
    coordinate_count = len(snapshot.response_vocabulary_id.coordinate_names)
    ledger.charge(
        "initial_partition_units",
        n_states * (coordinate_count + 1) + n_actions,
    )
    roundtripped = ExactPartitionCertificate.from_dict(certificate.to_dict())
    if roundtripped != certificate:
        raise StrictContractError("partition certificate failed strict roundtrip")
    expected_bindings = (
        SYNTHETIC_EVIDENCE_SCOPE,
        admitted.admission_report.snapshot_sha256,
        snapshot.domain_id.domain_payload_digest,
        snapshot.domain_id.frame_digest,
        snapshot.domain_id.transition_semantics_digest,
        snapshot.response_vocabulary_id.vocabulary_digest,
        snapshot.domain_id.action_alphabet_digest,
    )
    if _certificate_binding_values(certificate) != expected_bindings:
        raise StrictContractError("partition certificate source binding mismatch")
    state_by_id = {state.state_id: state for state in snapshot.states}
    state_payload_key = {
        state.state_id: _payload_bytes(state.payload) for state in snapshot.states
    }
    action_payload_key = {
        action.action_id: _payload_bytes(action.payload) for action in snapshot.actions
    }
    canonical_actions = tuple(
        sorted(snapshot.actions, key=lambda action: action_payload_key[action.action_id])
    )
    expected_action_ids = tuple(action.action_id for action in canonical_actions)
    if certificate.canonical_action_ids != expected_action_ids:
        raise StrictContractError(
            "certificate action order is not semantic CanonicalPayload order"
        )
    transition_target = {
        (row.source_state_id, row.action_id): row.target_state_id
        for row in snapshot.transitions
    }
    p0_groups: dict[tuple[str, tuple[tuple[int, int], ...]], list[str]] = {}
    for state in sorted(
        snapshot.states, key=lambda state: state_payload_key[state.state_id]
    ):
        p0_groups.setdefault(state.response_key, []).append(state.state_id)
    current_blocks = _canonical_blocks_from_groups(
        p0_groups.values(), state_payload_key
    )
    if certificate.refinement_trace[0].blocks != current_blocks:
        raise StrictContractError("certificate P0 is not the exact response partition")
    for stage in certificate.refinement_trace[1:]:
        _charge_verifier_relation_pass(
            ledger,
            blocks=current_blocks,
            n_actions=n_actions,
            coordinate_count=coordinate_count,
        )
        next_blocks = _verifier_relation_refinement(
            current_blocks,
            state_by_id,
            transition_target,
            canonical_actions,
            state_payload_key,
        )
        if len(next_blocks) <= len(current_blocks) or stage.blocks != next_blocks:
            raise StrictContractError(
                "certificate strict refinement stage is missing, reordered, or incorrect"
            )
        current_blocks = next_blocks
    _charge_verifier_relation_pass(
        ledger,
        blocks=current_blocks,
        n_actions=n_actions,
        coordinate_count=coordinate_count,
    )
    fixed_point = _verifier_relation_refinement(
        current_blocks,
        state_by_id,
        transition_target,
        canonical_actions,
        state_payload_key,
    )
    if fixed_point != current_blocks or certificate.fixed_point_passes != 1:
        raise StrictContractError(
            "certificate does not terminate in exactly one verified no-change pass"
        )
    if certificate.final_blocks != current_blocks:
        raise StrictContractError("certificate final blocks do not match refinement")
    owner = _block_owner(current_blocks)
    ledger.charge("quotient_units", n_states * n_actions)
    expected_quotient: list[ExactQuotientRow] = []
    for block in current_blocks:
        responses = {
            state_by_id[state_id].response_key for state_id in block.member_state_ids
        }
        if len(responses) != 1:
            raise StrictContractError("certificate final block is response-inhomogeneous")
        for action in canonical_actions:
            member_targets: set[int] = set()
            for state_id in block.member_state_ids:
                target_id = transition_target[(state_id, action.action_id)]
                member_targets.add(owner[target_id])
            if len(member_targets) != 1:
                raise StrictContractError(
                    "certificate quotient depends on a representative member"
                )
            expected_quotient.append(
                ExactQuotientRow(
                    block.block_index,
                    action.action_id,
                    next(iter(member_targets)),
                )
            )
    expected_quotient_tuple = tuple(expected_quotient)
    if certificate.quotient_rows != expected_quotient_tuple:
        raise StrictContractError("certificate full-member quotient table is incorrect")
    expected_witnesses = _verify_distinguishing_words_by_state_pair_relation(
        snapshot=snapshot,
        blocks=current_blocks,
        canonical_actions=canonical_actions,
        state_by_id=state_by_id,
        state_payload_key=state_payload_key,
        transition_target=transition_target,
        ledger=ledger,
    )
    if certificate.distinguishing_witnesses != expected_witnesses:
        raise StrictContractError(
            "certificate witness is not shortest semantic-action-lexicographic"
        )
    expected_producer_counters = _recompute_producer_work_counters(
        semantic_input_units=ledger.semantic_input_units,
        snapshot=snapshot,
        certificate=certificate,
    )
    if certificate.work_counters != expected_producer_counters:
        raise StrictContractError("certificate producer work counters are incorrect")
    certificate_sha256 = hashlib.sha256(_canonical_bytes(certificate)).hexdigest().upper()
    _charge_verification_report_output(
        ledger,
        snapshot_sha256=admitted.admission_report.snapshot_sha256,
        certificate_sha256=certificate_sha256,
    )
    report = ExactPartitionVerificationReport(
        evidence_scope=SYNTHETIC_EVIDENCE_SCOPE,
        snapshot_sha256=admitted.admission_report.snapshot_sha256,
        certificate_sha256=certificate_sha256,
        final_block_count=len(current_blocks),
        strict_refinement_passes=len(certificate.refinement_trace) - 1,
        distinguishing_witness_count=len(expected_witnesses),
        work_counters=ExactPartitionWorkCounters.from_ledger(ledger),
        checks=EXACT_PARTITION_VERIFICATION_CHECKS,
    )
    roundtrip_report = ExactPartitionVerificationReport.from_dict(report.to_dict())
    if roundtrip_report != report:
        raise StrictContractError("partition verification report failed strict roundtrip")
    return roundtrip_report


@dataclass(frozen=True)
class VerifiedExactPartition:
    """Capability retaining the complete source and independently checked proof."""

    admitted: AdmittedExactFiniteSnapshot
    certificate: ExactPartitionCertificate
    verification_report: ExactPartitionVerificationReport = field(init=False)
    evidence_scope: str = field(default=SYNTHETIC_EVIDENCE_SCOPE, init=False)

    def __post_init__(self) -> None:
        if type(self) is not VerifiedExactPartition:
            raise StrictContractError("verified exact partition subclasses are forbidden")
        if type(self.admitted) is not AdmittedExactFiniteSnapshot:
            raise StrictContractError("verified partition admitted source is not exact")
        if type(self.certificate) is not ExactPartitionCertificate:
            raise StrictContractError("verified partition certificate is not exact")
        _fixed_string(
            self.evidence_scope,
            SYNTHETIC_EVIDENCE_SCOPE,
            "verified partition evidence_scope",
        )
        object.__setattr__(
            self,
            "verification_report",
            _verify_exact_partition_core(self.admitted, self.certificate),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VERIFIED_EXACT_PARTITION_SCHEMA,
            "evidence_scope": self.evidence_scope,
            "snapshot_sha256": self.certificate.snapshot_sha256,
            "domain_payload_digest": self.certificate.domain_payload_digest,
            "observation_frame_digest": self.certificate.observation_frame_digest,
            "transition_semantics_digest": self.certificate.transition_semantics_digest,
            "response_vocabulary_digest": self.certificate.response_vocabulary_digest,
            "action_alphabet_digest": self.certificate.action_alphabet_digest,
            "certificate": self.certificate.to_dict(),
            "verification_report": self.verification_report.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        admitted: AdmittedExactFiniteSnapshot,
    ) -> "VerifiedExactPartition":
        if cls is not VerifiedExactPartition:
            raise StrictContractError("polymorphic verified deserialization is forbidden")
        if type(admitted) is not AdmittedExactFiniteSnapshot:
            raise StrictContractError(
                "verified deserialization requires the external exact admitted source"
            )
        obj = _object(
            value,
            {
                "schema_version",
                "evidence_scope",
                "snapshot_sha256",
                "domain_payload_digest",
                "observation_frame_digest",
                "transition_semantics_digest",
                "response_vocabulary_digest",
                "action_alphabet_digest",
                "certificate",
                "verification_report",
            },
            "VerifiedExactPartition",
        )
        _fixed_string(
            obj["schema_version"],
            VERIFIED_EXACT_PARTITION_SCHEMA,
            "VerifiedExactPartition schema",
        )
        _fixed_string(
            obj["evidence_scope"],
            SYNTHETIC_EVIDENCE_SCOPE,
            "VerifiedExactPartition evidence_scope",
        )
        _strict_wire_preflight(obj, "VerifiedExactPartition")
        certificate = ExactPartitionCertificate.from_dict(obj["certificate"])
        supplied_report = ExactPartitionVerificationReport.from_dict(
            obj["verification_report"]
        )
        verified = verify_exact_partition(admitted, certificate)
        supplied_bindings = (
            _digest(obj["snapshot_sha256"], "verified snapshot_sha256"),
            _digest(
                obj["domain_payload_digest"], "verified domain_payload_digest"
            ),
            _digest(
                obj["observation_frame_digest"],
                "verified observation_frame_digest",
            ),
            _digest(
                obj["transition_semantics_digest"],
                "verified transition_semantics_digest",
            ),
            _digest(
                obj["response_vocabulary_digest"],
                "verified response_vocabulary_digest",
            ),
            _digest(
                obj["action_alphabet_digest"], "verified action_alphabet_digest"
            ),
        )
        expected_bindings = _certificate_binding_values(certificate)[1:]
        if _canonical_bytes(supplied_report) != _canonical_bytes(
            verified.verification_report
        ) or supplied_bindings != expected_bindings or verified.to_dict() != obj:
            raise StrictContractError(
                "verified exact partition does not match recomputed verifier"
            )
        return verified


def verify_exact_partition(
    admitted: AdmittedExactFiniteSnapshot,
    certificate: ExactPartitionCertificate,
) -> VerifiedExactPartition:
    """Independently verify a certificate and retain its exact admitted source."""

    return VerifiedExactPartition(admitted, certificate)


__all__ = [
    "EXACT_PARTITION_VERIFICATION_CHECKS",
    "MAX_EXACT_PARTITION_WORK_UNITS",
    "ExactDistinguishingWitness",
    "ExactPartitionBlock",
    "ExactPartitionCertificate",
    "ExactPartitionVerificationReport",
    "ExactPartitionWorkCounters",
    "ExactQuotientRow",
    "ExactRefinementStage",
    "VerifiedExactPartition",
    "refine_exact_partition",
    "verify_exact_partition",
]
