from __future__ import annotations

"""Fixed finite E2 candidate universe and binding support gate.

This module intentionally exposes no generic candidate registry or caller-
parameterized threshold.  Its two sealed values are the literal three-row E2
endpoint frozen by the 2026-07-16 endpoint-semantics authority.
"""

from dataclasses import dataclass, field
import hashlib
from typing import Any

from .certificates import (
    CocycleCertificate,
    EnvelopeRestrictionWitness,
    LiftingUniformSafetyCertificate,
    ReturnMemoryBound,
    SourceTargetCoordinateIdentification,
)
from .contracts import ExactRational, StrictContractError, canonical_contract_bytes


_ENDPOINT_ID = "u24_e2_declared_square_endpoint_v1"
_BASIS_CONVENTION = "target_row_source_column_v1"
_UNIVERSE_ID = "u24_e2_literal_three_candidate_universe_v1"
_MANIFEST_SCHEMA = "odlrq.e2.candidate-universe-manifest.v1"
_MANIFEST_CORE_SCHEMA = "odlrq.e2.candidate-universe-core.v1"
_TOKEN_SCHEMA = "odlrq.e2.certified-support-token.v1"
_INVALIDATION_SCHEMA = "odlrq.e2.support-invalidation.v1"
_CANDIDATE_PAYLOAD_SCHEMA = "odlrq.e2.synthetic-candidate.v1"
_DECISION_AUTHORITY_SCHEMA = "odlrq.e2.decision-authority-bundle.v1"

_MANIFEST_DISPOSITION = "E2_DECLARED_CANDIDATE_UNIVERSE_SEALED"
_TOKEN_DISPOSITION = "E2_BINDING_SUPPORT_CERTIFIED"
_COMPARATOR = "exact_rational_less_equal_v1"

_MAX_E2_CANONICAL_WIRE_BYTES = 1_048_576
_MAX_E2_NESTING_DEPTH = 12
_MAX_E2_STRUCTURAL_NODES = 4_096
_MAX_E2_UTF8_SCALAR_BYTES = 262_144
_MAX_E2_COORDINATES = 4
_MAX_E2_CANDIDATE_LOAD_ROWS = 20
_MAX_E2_RETURN_TERMS = 3
_MAX_E2_DECLARED_CANDIDATES = 3
_MAX_E2_DECISION_ROWS = 3
_MAX_E2_DERIVATION_WORK_UNITS = 256

_CANONICAL_CANDIDATE_IDS = ("c0", "c1", "c2")
_MANIFEST_SEAL = object()
_TOKEN_SEAL = object()

_MANIFEST_FIELDS = {
    "schema_version",
    "endpoint_id",
    "universe_id",
    "sealed_before_threshold",
    "candidate_rows",
    "candidate_count",
    "canonical_candidate_ids",
    "pre_gate_complete",
    "manifest_core_sha256",
    "verification_disposition",
}
_CANDIDATE_ROW_FIELDS = {
    "candidate_id",
    "candidate_payload_sha256",
    "source_coordinate_ids",
    "membership_core_sha256",
    "parent_id",
    "parent_envelope_sha256",
    "coordinate_identification_sha256",
    "envelope_restriction_sha256",
    "lifting_uniform_safety_sha256",
    "target_coordinate_id",
    "source_coordinate_id",
    "bound",
    "utility",
}
_TOKEN_FIELDS = {
    "schema_version",
    "endpoint_id",
    "candidate_universe_manifest_sha256",
    "p1_cocycle_sha256",
    "p2_cocycle_sha256",
    "return_memory_bound_sha256",
    "comparator",
    "threshold",
    "decision_rows",
    "denominator",
    "numerator",
    "coverage",
    "ungated_ranking",
    "gated_ranking",
    "support_candidate_ids",
    "rejected_candidate_ids",
    "abstained_candidate_ids",
    "ranking_changed",
    "invalidation_sha256",
    "verification_disposition",
}
_DECISION_ROW_FIELDS = {
    "candidate_id",
    "bound",
    "threshold",
    "decision",
    "reason",
    "authority_bundle_sha256",
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _require_digest(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise StrictContractError(f"{where} must be canonical uppercase SHA-256")
    return value


def _require_string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StrictContractError(f"{where} must be strict UTF-8") from exc
    return value


def _require_int(value: Any, where: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise StrictContractError(f"{where} is outside its exact integer bounds")
    return value


def _require_exact_list(
    value: Any,
    where: str,
    *,
    length: int | None = None,
    maximum: int | None = None,
) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an exact array")
    if length is not None and len(value) != length:
        raise StrictContractError(f"{where} has the wrong exact cardinality")
    if maximum is not None and len(value) > maximum:
        raise StrictContractError(f"{where} exceeds its cardinality cap")
    return value


def _require_exact_string_array(
    value: Any,
    where: str,
    *,
    length: int | None = None,
    maximum: int | None = None,
) -> list[str]:
    rows = _require_exact_list(value, where, length=length, maximum=maximum)
    for index, item in enumerate(rows):
        _require_string(item, f"{where}[{index}]")
    return rows


def _bounded_wire_walk(value: Any, where: str) -> None:
    """Bound an already-decoded strict-JSON object without copying its tree."""

    nodes = 0
    scalar_bytes = 0
    total_bytes = 0
    active_containers: set[int] = set()

    def add_bytes(count: int, *, scalar: bool = False) -> None:
        nonlocal scalar_bytes, total_bytes
        total_bytes += count
        if total_bytes > _MAX_E2_CANONICAL_WIRE_BYTES:
            raise StrictContractError(f"{where} exceeds the canonical-wire byte cap")
        if scalar:
            scalar_bytes += count
            if scalar_bytes > _MAX_E2_UTF8_SCALAR_BYTES:
                raise StrictContractError(f"{where} exceeds the UTF-8 scalar byte cap")

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        if depth > _MAX_E2_NESTING_DEPTH:
            raise StrictContractError(f"{where} exceeds the nesting-depth cap")
        nodes += 1
        if nodes > _MAX_E2_STRUCTURAL_NODES:
            raise StrictContractError(f"{where} exceeds the structural-node cap")

        if item is None:
            add_bytes(4, scalar=True)
            return
        if type(item) is bool:
            add_bytes(4 if item else 5, scalar=True)
            return
        if type(item) is int:
            if not (-(2**63) <= item < 2**63):
                raise StrictContractError(f"{where} contains an out-of-range integer")
            add_bytes(len(str(item).encode("ascii")), scalar=True)
            return
        if type(item) is str:
            try:
                add_bytes(1, scalar=True)
                for character in item:
                    codepoint = ord(character)
                    if character in {'"', "\\"} or character in {
                        "\b",
                        "\t",
                        "\n",
                        "\f",
                        "\r",
                    }:
                        add_bytes(2, scalar=True)
                    elif codepoint < 0x20:
                        add_bytes(6, scalar=True)
                    else:
                        add_bytes(
                            len(character.encode("utf-8", errors="strict")),
                            scalar=True,
                        )
                add_bytes(1, scalar=True)
            except UnicodeEncodeError as exc:
                raise StrictContractError(f"{where} contains a noncanonical string") from exc
            return
        if type(item) is list:
            identity = id(item)
            if identity in active_containers:
                raise StrictContractError(f"{where} contains a container cycle")
            active_containers.add(identity)
            add_bytes(1)
            for index, child in enumerate(item):
                if index:
                    add_bytes(1)
                visit(child, depth + 1)
            add_bytes(1)
            active_containers.remove(identity)
            return
        if type(item) is dict:
            identity = id(item)
            if identity in active_containers:
                raise StrictContractError(f"{where} contains a container cycle")
            active_containers.add(identity)
            add_bytes(1)
            for index, (key, child) in enumerate(item.items()):
                if type(key) is not str:
                    raise StrictContractError(f"{where} contains a non-string object key")
                if index:
                    add_bytes(1)
                visit(key, depth + 1)
                add_bytes(1)
                visit(child, depth + 1)
            add_bytes(1)
            active_containers.remove(identity)
            return
        raise StrictContractError(
            f"{where} contains a value outside the strict JSON algebra"
        )

    visit(value, 0)


def _rational_from_wire(value: Any, where: str) -> ExactRational:
    if type(value) is not dict or len(value) != 3 or set(value) != {
        "schema_version",
        "numerator",
        "denominator",
    }:
        raise StrictContractError(f"{where} must be an exact rational wire")
    return ExactRational.from_dict(value)


def _exact_rational(value: Any, where: str) -> ExactRational:
    if type(value) is not ExactRational:
        raise StrictContractError(f"{where} must be ExactRational")
    if ExactRational.from_dict(value.to_dict()) != value:
        raise StrictContractError(f"{where} is not a reduced exact rational")
    return value


def _multiply(left: ExactRational, right: ExactRational) -> ExactRational:
    _exact_rational(left, "left exact factor")
    _exact_rational(right, "right exact factor")
    return ExactRational(
        left.numerator * right.numerator,
        left.denominator * right.denominator,
    )


def _less(left: ExactRational, right: ExactRational) -> bool:
    _exact_rational(left, "left exact comparator operand")
    _exact_rational(right, "right exact comparator operand")
    return left.numerator * right.denominator < right.numerator * left.denominator


def _less_equal(left: ExactRational, right: ExactRational) -> bool:
    return not _less(right, left)


def _certificate_wire(
    authority: Any,
    exact_type: type[Any],
    where: str,
) -> tuple[dict[str, Any], str]:
    if type(authority) is not exact_type:
        raise StrictContractError(f"{where} requires an exact {exact_type.__name__}")
    if "to_dict" in vars(authority):
        raise StrictContractError(f"{where} forbids an instance serializer override")
    wire = exact_type.to_dict(authority)
    if type(wire) is not dict:
        raise StrictContractError(f"{where} did not rederive an exact wire")
    digest = _sha256(wire)
    # Exact authority types define their public digest as this fresh wire hash;
    # reading the property here would redundantly rederive the full authority graph.
    return wire, digest


def _preflight_manifest_wire(value: Any) -> dict[str, Any]:
    if type(value) is not dict or len(value) != len(_MANIFEST_FIELDS):
        raise StrictContractError("strict CandidateUniverseManifest parsing is required")
    if set(value) != _MANIFEST_FIELDS:
        raise StrictContractError("candidate manifest outer fields mismatch")
    rows = _require_exact_list(
        value["candidate_rows"],
        "candidate manifest rows",
        length=_MAX_E2_DECLARED_CANDIDATES,
    )
    for row in rows:
        if type(row) is not dict or len(row) != len(_CANDIDATE_ROW_FIELDS):
            raise StrictContractError("candidate manifest row shape mismatch")
        if set(row) != _CANDIDATE_ROW_FIELDS:
            raise StrictContractError("candidate manifest row fields mismatch")
        _require_exact_list(
            row["source_coordinate_ids"],
            "candidate source coordinates",
            length=1,
        )
    _require_exact_list(
        value["canonical_candidate_ids"],
        "canonical candidate IDs",
        length=_MAX_E2_DECLARED_CANDIDATES,
    )
    _bounded_wire_walk(value, "CandidateUniverseManifest wire")

    if (
        value["schema_version"] != _MANIFEST_SCHEMA
        or value["endpoint_id"] != _ENDPOINT_ID
        or value["universe_id"] != _UNIVERSE_ID
        or type(value["sealed_before_threshold"]) is not bool
        or not value["sealed_before_threshold"]
        or type(value["pre_gate_complete"]) is not bool
        or not value["pre_gate_complete"]
        or value["verification_disposition"] != _MANIFEST_DISPOSITION
    ):
        raise StrictContractError("candidate manifest fixed schema/scope fields mismatch")
    _require_int(
        value["candidate_count"],
        "candidate manifest count",
        minimum=_MAX_E2_DECLARED_CANDIDATES,
        maximum=_MAX_E2_DECLARED_CANDIDATES,
    )
    if value["canonical_candidate_ids"] != list(_CANONICAL_CANDIDATE_IDS):
        raise StrictContractError("candidate manifest canonical IDs changed")
    _require_digest(value["manifest_core_sha256"], "manifest core SHA")

    for index, row in enumerate(rows):
        if row["candidate_id"] != _CANONICAL_CANDIDATE_IDS[index]:
            raise StrictContractError("candidate manifest rows are reordered or substituted")
        for name in (
            "candidate_payload_sha256",
            "membership_core_sha256",
            "parent_envelope_sha256",
            "coordinate_identification_sha256",
            "envelope_restriction_sha256",
            "lifting_uniform_safety_sha256",
        ):
            _require_digest(row[name], f"candidate row {name}")
        _require_exact_string_array(
            row["source_coordinate_ids"],
            "candidate source coordinates",
            length=1,
        )
        for name in (
            "candidate_id",
            "parent_id",
            "target_coordinate_id",
            "source_coordinate_id",
        ):
            _require_string(row[name], f"candidate row {name}")
        _rational_from_wire(row["bound"], "candidate bound")
        _rational_from_wire(row["utility"], "candidate utility")
    return value


def _preflight_token_wire(value: Any) -> dict[str, Any]:
    if type(value) is not dict or len(value) != len(_TOKEN_FIELDS):
        raise StrictContractError("strict CertifiedSupportToken parsing is required")
    if set(value) != _TOKEN_FIELDS:
        raise StrictContractError("certified support token outer fields mismatch")
    decisions = _require_exact_list(
        value["decision_rows"],
        "support decision rows",
        length=_MAX_E2_DECISION_ROWS,
    )
    for row in decisions:
        if type(row) is not dict or len(row) != len(_DECISION_ROW_FIELDS):
            raise StrictContractError("support decision row shape mismatch")
        if set(row) != _DECISION_ROW_FIELDS:
            raise StrictContractError("support decision row fields mismatch")
    array_cardinalities = {
        "ungated_ranking": 3,
        "gated_ranking": 2,
        "support_candidate_ids": 2,
        "rejected_candidate_ids": 1,
        "abstained_candidate_ids": 0,
    }
    for name, length in array_cardinalities.items():
        _require_exact_list(value[name], name, length=length)
    _bounded_wire_walk(value, "CertifiedSupportToken wire")

    if (
        value["schema_version"] != _TOKEN_SCHEMA
        or value["endpoint_id"] != _ENDPOINT_ID
        or value["comparator"] != _COMPARATOR
        or value["verification_disposition"] != _TOKEN_DISPOSITION
        or type(value["ranking_changed"]) is not bool
        or not value["ranking_changed"]
    ):
        raise StrictContractError("support token fixed schema/scope fields mismatch")
    for name in (
        "candidate_universe_manifest_sha256",
        "p1_cocycle_sha256",
        "p2_cocycle_sha256",
        "return_memory_bound_sha256",
        "invalidation_sha256",
    ):
        _require_digest(value[name], f"support token {name}")
    _require_int(value["denominator"], "support denominator", minimum=3, maximum=3)
    _require_int(value["numerator"], "support numerator", minimum=2, maximum=2)
    _rational_from_wire(value["threshold"], "support threshold")
    _rational_from_wire(value["coverage"], "support coverage")
    for name, length in array_cardinalities.items():
        _require_exact_string_array(value[name], name, length=length)
    for index, row in enumerate(decisions):
        if row["candidate_id"] != _CANONICAL_CANDIDATE_IDS[index]:
            raise StrictContractError("support decision rows are reordered or substituted")
        for name in ("candidate_id", "decision", "reason"):
            _require_string(row[name], f"support decision {name}")
        if row["decision"] not in {"ACCEPT", "REJECT"}:
            raise StrictContractError("ABSTAIN is outside the fixed support-token schema")
        if row["reason"] not in {"BOUND_LE_THRESHOLD", "BOUND_GT_THRESHOLD"}:
            raise StrictContractError("support decision reason is invalid")
        _rational_from_wire(row["bound"], "support decision bound")
        _rational_from_wire(row["threshold"], "support decision threshold")
        _require_digest(
            row["authority_bundle_sha256"],
            "support decision authority-bundle SHA",
        )
    return value


def _manifest_authority_context(
    *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
) -> dict[str, Any]:
    m0_identification_wire, m0_identification_sha = _certificate_wire(
        m0_identification,
        SourceTargetCoordinateIdentification,
        "M0 coordinate identification",
    )
    m0_restriction_wire, m0_restriction_sha = _certificate_wire(
        m0_restriction,
        EnvelopeRestrictionWitness,
        "M0 envelope restriction",
    )
    m0_safety_wire, m0_safety_sha = _certificate_wire(
        m0_safety,
        LiftingUniformSafetyCertificate,
        "M0 lifting-uniform safety certificate",
    )
    m1_identification_wire, m1_identification_sha = _certificate_wire(
        m1_identification,
        SourceTargetCoordinateIdentification,
        "M1 coordinate identification",
    )
    m1_restriction_wire, m1_restriction_sha = _certificate_wire(
        m1_restriction,
        EnvelopeRestrictionWitness,
        "M1 envelope restriction",
    )
    m1_safety_wire, m1_safety_sha = _certificate_wire(
        m1_safety,
        LiftingUniformSafetyCertificate,
        "M1 lifting-uniform safety certificate",
    )

    authorities = (
        (
            "M0",
            m0_identification_wire,
            m0_identification_sha,
            m0_restriction_wire,
            m0_restriction_sha,
            m0_safety_wire,
            m0_safety_sha,
        ),
        (
            "M1",
            m1_identification_wire,
            m1_identification_sha,
            m1_restriction_wire,
            m1_restriction_sha,
            m1_safety_wire,
            m1_safety_sha,
        ),
    )
    for (
        parent_id,
        identification_wire,
        identification_sha,
        restriction_wire,
        restriction_sha,
        safety_wire,
        _safety_sha,
    ) in authorities:
        if (
            identification_wire.get("schema_version")
            != "odlrq.e2.source-target-coordinate-identification.v1"
            or restriction_wire.get("schema_version")
            != "odlrq.e2.envelope-restriction.v1"
            or safety_wire.get("schema_version")
            != "odlrq.e2.lifting-uniform-safety.v1"
            or identification_wire.get("endpoint_id") != _ENDPOINT_ID
            or restriction_wire.get("endpoint_id") != _ENDPOINT_ID
            or safety_wire.get("endpoint_id") != _ENDPOINT_ID
            or identification_wire.get("parent_id") != parent_id
            or restriction_wire.get("parent_id") != parent_id
            or safety_wire.get("parent_id") != parent_id
            or identification_wire.get("source_law_variant") != "PRIMARY"
            or restriction_wire.get("source_law_variant") != "PRIMARY"
            or safety_wire.get("source_law_variant") != "PRIMARY"
            or identification_wire.get("basis_convention") != _BASIS_CONVENTION
            or restriction_wire.get("basis_convention") != _BASIS_CONVENTION
            or restriction_wire.get("coordinate_identification_sha256")
            != identification_sha
            or safety_wire.get("coordinate_identification_sha256")
            != identification_sha
            or safety_wire.get("envelope_restriction_sha256") != restriction_sha
            or restriction_wire.get("parent_envelope_sha256")
            != identification_wire.get("parent_envelope_sha256")
            or safety_wire.get("parent_envelope_sha256")
            != identification_wire.get("parent_envelope_sha256")
            or restriction_wire.get("coordinate_core_sha256")
            != identification_wire.get("coordinate_core_sha256")
            or safety_wire.get("coordinate_core_sha256")
            != identification_wire.get("coordinate_core_sha256")
            or safety_wire.get("restriction_core_sha256")
            != restriction_wire.get("restriction_core_sha256")
        ):
            raise StrictContractError(
                f"{parent_id} manifest authorities are stale, substituted, or misbound"
            )
        if identification_wire.get("full_coordinate_ids") != [
            "OPEN_0",
            "OPEN_1",
            "CLOSED",
            "SINK",
        ]:
            raise StrictContractError(f"{parent_id} coordinate basis is not the fixed I")
        if restriction_wire.get("retained_coordinate_ids") != ["OPEN_0", "OPEN_1"]:
            raise StrictContractError(f"{parent_id} retained basis is not the fixed J")
        if safety_wire.get("candidate_load_count") != _MAX_E2_CANDIDATE_LOAD_ROWS:
            raise StrictContractError(f"{parent_id} candidate-load proof is incomplete")

    coordinate_count = len(m0_identification_wire["full_coordinate_ids"])
    candidate_load_count = m0_safety_wire["candidate_load_count"]
    if (
        coordinate_count != _MAX_E2_COORDINATES
        or len(m1_identification_wire["full_coordinate_ids"]) != coordinate_count
        or candidate_load_count != _MAX_E2_CANDIDATE_LOAD_ROWS
        or m1_safety_wire["candidate_load_count"] != candidate_load_count
    ):
        raise StrictContractError("candidate manifest dimensions changed before allocation")
    work_units = _MAX_E2_DECLARED_CANDIDATES * (
        candidate_load_count + coordinate_count + 1
    )
    if work_units != 75 or work_units > _MAX_E2_DERIVATION_WORK_UNITS:
        raise StrictContractError("candidate manifest derivation schedule is invalid")

    source_seal = _sha256(
        {
            "schema_version": "odlrq.e2.candidate-universe-source-seal.v1",
            "m0_identification_sha256": m0_identification_sha,
            "m0_restriction_sha256": m0_restriction_sha,
            "m0_safety_sha256": m0_safety_sha,
            "m1_identification_sha256": m1_identification_sha,
            "m1_restriction_sha256": m1_restriction_sha,
            "m1_safety_sha256": m1_safety_sha,
        }
    )
    return {
        "m0_identification_wire": m0_identification_wire,
        "m0_identification_sha": m0_identification_sha,
        "m0_restriction_wire": m0_restriction_wire,
        "m0_restriction_sha": m0_restriction_sha,
        "m0_safety_sha": m0_safety_sha,
        "m1_identification_wire": m1_identification_wire,
        "m1_identification_sha": m1_identification_sha,
        "m1_restriction_wire": m1_restriction_wire,
        "m1_restriction_sha": m1_restriction_sha,
        "m1_safety_sha": m1_safety_sha,
        "source_seal": source_seal,
    }


def _matrix_entry(
    restriction_wire: dict[str, Any],
    target_index: int,
    source_index: int,
    where: str,
) -> ExactRational:
    matrix = restriction_wire.get("restricted_matrix")
    if type(matrix) is not list or len(matrix) != 2:
        raise StrictContractError(f"{where} restricted matrix is not exact 2 x 2")
    for row in matrix:
        if type(row) is not list or len(row) != 2:
            raise StrictContractError(f"{where} restricted matrix is not exact 2 x 2")
    return _rational_from_wire(matrix[target_index][source_index], where)


def _candidate_payload(candidate_id: str) -> dict[str, Any]:
    literal_payloads = {
        "c0": {
            "schema_version": _CANDIDATE_PAYLOAD_SCHEMA,
            "candidate_id": "c0",
            "declared_action_id": "E2_SYNTHETIC_C0",
        },
        "c1": {
            "schema_version": _CANDIDATE_PAYLOAD_SCHEMA,
            "candidate_id": "c1",
            "declared_action_id": "E2_SYNTHETIC_C1",
        },
        "c2": {
            "schema_version": _CANDIDATE_PAYLOAD_SCHEMA,
            "candidate_id": "c2",
            "declared_action_id": "E2_SYNTHETIC_C2",
        },
    }
    if candidate_id not in literal_payloads:
        raise StrictContractError("candidate payload is outside the literal E2 universe")
    return literal_payloads[candidate_id]


def _candidate_row(
    *,
    candidate_id: str,
    parent_id: str,
    target_coordinate_id: str,
    source_coordinate_id: str,
    bound: ExactRational,
    identification_wire: dict[str, Any],
    identification_sha: str,
    restriction_sha: str,
    safety_sha: str,
) -> dict[str, Any]:
    payload_sha = _sha256(_candidate_payload(candidate_id))
    source_coordinate_ids = [source_coordinate_id]
    membership_core = {
        "endpoint_id": _ENDPOINT_ID,
        "candidate_id": candidate_id,
        "candidate_payload_sha256": payload_sha,
        "parent_id": parent_id,
        "source_coordinate_ids": source_coordinate_ids,
        "source_coordinate_id": source_coordinate_id,
        "coordinate_core_sha256": identification_wire["coordinate_core_sha256"],
    }
    return {
        "candidate_id": candidate_id,
        "candidate_payload_sha256": payload_sha,
        "source_coordinate_ids": source_coordinate_ids,
        "membership_core_sha256": _sha256(membership_core),
        "parent_id": parent_id,
        "parent_envelope_sha256": identification_wire["parent_envelope_sha256"],
        "coordinate_identification_sha256": identification_sha,
        "envelope_restriction_sha256": restriction_sha,
        "lifting_uniform_safety_sha256": safety_sha,
        "target_coordinate_id": target_coordinate_id,
        "source_coordinate_id": source_coordinate_id,
        "bound": bound.to_dict(),
        "utility": _multiply(bound, bound).to_dict(),
    }


def _derive_manifest_wire(
    *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
) -> tuple[dict[str, Any], str]:
    context = _manifest_authority_context(
        m0_identification=m0_identification,
        m0_restriction=m0_restriction,
        m0_safety=m0_safety,
        m1_identification=m1_identification,
        m1_restriction=m1_restriction,
        m1_safety=m1_safety,
    )
    c0_bound = _matrix_entry(context["m0_restriction_wire"], 0, 0, "c0 bound")
    c1_bound = _matrix_entry(context["m1_restriction_wire"], 1, 0, "c1 bound")
    c2_bound = _matrix_entry(context["m0_restriction_wire"], 0, 1, "c2 bound")
    if (c0_bound, c1_bound, c2_bound) != (
        ExactRational(1),
        ExactRational(3),
        ExactRational(2),
    ):
        raise StrictContractError("literal candidate bound authorities changed")

    candidate_rows = [
        _candidate_row(
            candidate_id="c0",
            parent_id="M0",
            target_coordinate_id="OPEN_0",
            source_coordinate_id="OPEN_0",
            bound=c0_bound,
            identification_wire=context["m0_identification_wire"],
            identification_sha=context["m0_identification_sha"],
            restriction_sha=context["m0_restriction_sha"],
            safety_sha=context["m0_safety_sha"],
        ),
        _candidate_row(
            candidate_id="c1",
            parent_id="M1",
            target_coordinate_id="OPEN_1",
            source_coordinate_id="OPEN_0",
            bound=c1_bound,
            identification_wire=context["m1_identification_wire"],
            identification_sha=context["m1_identification_sha"],
            restriction_sha=context["m1_restriction_sha"],
            safety_sha=context["m1_safety_sha"],
        ),
        _candidate_row(
            candidate_id="c2",
            parent_id="M0",
            target_coordinate_id="OPEN_0",
            source_coordinate_id="OPEN_1",
            bound=c2_bound,
            identification_wire=context["m0_identification_wire"],
            identification_sha=context["m0_identification_sha"],
            restriction_sha=context["m0_restriction_sha"],
            safety_sha=context["m0_safety_sha"],
        ),
    ]
    core = {
        "schema_version": _MANIFEST_CORE_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "universe_id": _UNIVERSE_ID,
        "sealed_before_threshold": True,
        "candidate_rows": candidate_rows,
        "candidate_count": len(candidate_rows),
        "canonical_candidate_ids": list(_CANONICAL_CANDIDATE_IDS),
        "pre_gate_complete": True,
    }
    wire = {
        **core,
        "schema_version": _MANIFEST_SCHEMA,
        "manifest_core_sha256": _sha256(core),
        "verification_disposition": _MANIFEST_DISPOSITION,
    }
    return wire, context["source_seal"]


@dataclass(frozen=True, init=False)
class CandidateUniverseManifest:
    _m0_identification: SourceTargetCoordinateIdentification = field(repr=False)
    _m0_restriction: EnvelopeRestrictionWitness = field(repr=False)
    _m0_safety: LiftingUniformSafetyCertificate = field(repr=False)
    _m1_identification: SourceTargetCoordinateIdentification = field(repr=False)
    _m1_restriction: EnvelopeRestrictionWitness = field(repr=False)
    _m1_safety: LiftingUniformSafetyCertificate = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("candidate universe manifest has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not CandidateUniverseManifest:
            raise StrictContractError("CandidateUniverseManifest subclasses are forbidden")
        if self._construction_seal is not _MANIFEST_SEAL:
            raise StrictContractError("candidate universe requires the declared E2 builder")
        _require_digest(self._source_seal_sha256, "candidate manifest source seal")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        m0_identification: SourceTargetCoordinateIdentification,
        m0_restriction: EnvelopeRestrictionWitness,
        m0_safety: LiftingUniformSafetyCertificate,
        m1_identification: SourceTargetCoordinateIdentification,
        m1_restriction: EnvelopeRestrictionWitness,
        m1_safety: LiftingUniformSafetyCertificate,
    ) -> "CandidateUniverseManifest":
        if cls is not CandidateUniverseManifest:
            raise StrictContractError("polymorphic candidate-manifest parsing is forbidden")
        supplied = _preflight_manifest_wire(value)
        expected, source_seal = _derive_manifest_wire(
            m0_identification=m0_identification,
            m0_restriction=m0_restriction,
            m0_safety=m0_safety,
            m1_identification=m1_identification,
            m1_restriction=m1_restriction,
            m1_safety=m1_safety,
        )
        if canonical_contract_bytes(supplied) != canonical_contract_bytes(expected):
            raise StrictContractError(
                "candidate manifest wire disagrees with retained exact authorities"
            )
        return _construct_manifest(
            m0_identification=m0_identification,
            m0_restriction=m0_restriction,
            m0_safety=m0_safety,
            m1_identification=m1_identification,
            m1_restriction=m1_restriction,
            m1_safety=m1_safety,
            source_seal=source_seal,
        )

    @property
    def candidate_universe_manifest_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        wire, source_seal = _derive_manifest_wire(
            m0_identification=self._m0_identification,
            m0_restriction=self._m0_restriction,
            m0_safety=self._m0_safety,
            m1_identification=self._m1_identification,
            m1_restriction=self._m1_restriction,
            m1_safety=self._m1_safety,
        )
        if source_seal != _require_digest(
            self._source_seal_sha256, "candidate manifest source seal"
        ):
            raise StrictContractError("candidate manifest retained authority changed")
        return wire


def _construct_manifest(
    *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
    source_seal: str,
) -> CandidateUniverseManifest:
    result = object.__new__(CandidateUniverseManifest)
    object.__setattr__(result, "_m0_identification", m0_identification)
    object.__setattr__(result, "_m0_restriction", m0_restriction)
    object.__setattr__(result, "_m0_safety", m0_safety)
    object.__setattr__(result, "_m1_identification", m1_identification)
    object.__setattr__(result, "_m1_restriction", m1_restriction)
    object.__setattr__(result, "_m1_safety", m1_safety)
    object.__setattr__(result, "_source_seal_sha256", source_seal)
    object.__setattr__(result, "_construction_seal", _MANIFEST_SEAL)
    result.__post_init__()
    return result


def build_declared_e2_candidate_universe(
    *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
) -> CandidateUniverseManifest:
    _wire, source_seal = _derive_manifest_wire(
        m0_identification=m0_identification,
        m0_restriction=m0_restriction,
        m0_safety=m0_safety,
        m1_identification=m1_identification,
        m1_restriction=m1_restriction,
        m1_safety=m1_safety,
    )
    return _construct_manifest(
        m0_identification=m0_identification,
        m0_restriction=m0_restriction,
        m0_safety=m0_safety,
        m1_identification=m1_identification,
        m1_restriction=m1_restriction,
        m1_safety=m1_safety,
        source_seal=source_seal,
    )


def _ranking(candidate_rows: list[dict[str, Any]]) -> list[str]:
    ordered: list[tuple[str, ExactRational]] = []
    for row in candidate_rows:
        candidate_id = _require_string(row.get("candidate_id"), "ranking candidate ID")
        utility = _rational_from_wire(row.get("utility"), "ranking utility")
        insertion = len(ordered)
        for index, (other_id, other_utility) in enumerate(ordered):
            if _less(other_utility, utility) or (
                other_utility == utility and candidate_id < other_id
            ):
                insertion = index
                break
        ordered.insert(insertion, (candidate_id, utility))
    return [candidate_id for candidate_id, _utility in ordered]


def _token_authority_context(
    *,
    manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
) -> dict[str, Any]:
    manifest_wire, manifest_sha = _certificate_wire(
        manifest,
        CandidateUniverseManifest,
        "candidate universe manifest",
    )
    p1_wire, p1_sha = _certificate_wire(
        p1_cocycle,
        CocycleCertificate,
        "P1 cocycle certificate",
    )
    p2_wire, p2_sha = _certificate_wire(
        p2_cocycle,
        CocycleCertificate,
        "P2 cocycle certificate",
    )
    return_wire, return_sha = _certificate_wire(
        return_memory,
        ReturnMemoryBound,
        "finite return-memory bound",
    )
    if (
        manifest_wire.get("schema_version") != _MANIFEST_SCHEMA
        or manifest_wire.get("endpoint_id") != _ENDPOINT_ID
        or manifest_wire.get("universe_id") != _UNIVERSE_ID
        or manifest_wire.get("sealed_before_threshold") is not True
        or manifest_wire.get("pre_gate_complete") is not True
    ):
        raise StrictContractError("binding gate requires the sealed literal universe")

    candidate_rows = manifest_wire.get("candidate_rows")
    if type(candidate_rows) is not list or len(candidate_rows) != 3:
        raise StrictContractError("binding gate candidate universe is incomplete")
    return_terms = return_wire.get("return_terms")
    if type(return_terms) is not list or len(return_terms) != _MAX_E2_RETURN_TERMS:
        raise StrictContractError("binding gate requires the complete finite return sum")
    work_units = (
        len(candidate_rows)
        + len(candidate_rows)
        + len(return_terms)
        + 1
    )
    if work_units != 10 or work_units > _MAX_E2_DERIVATION_WORK_UNITS:
        raise StrictContractError("binding gate derivation schedule is invalid")
    if (
        any(type(row) is not dict for row in candidate_rows)
        or [row.get("candidate_id") for row in candidate_rows]
        != list(_CANONICAL_CANDIDATE_IDS)
    ):
        raise StrictContractError("binding gate candidate order is not canonical")
    c0_row, c1_row, c2_row = candidate_rows
    m0_restriction_sha = c0_row.get("envelope_restriction_sha256")
    m1_restriction_sha = c1_row.get("envelope_restriction_sha256")
    if c2_row.get("envelope_restriction_sha256") != m0_restriction_sha:
        raise StrictContractError("M0 candidate authorities disagree")
    factor_sha256s = [m0_restriction_sha, m1_restriction_sha]
    if (
        p1_wire.get("endpoint_id") != _ENDPOINT_ID
        or p2_wire.get("endpoint_id") != _ENDPOINT_ID
        or return_wire.get("endpoint_id") != _ENDPOINT_ID
        or p1_wire.get("channel") != "P1_BRANCHING_ADJUSTED"
        or p2_wire.get("channel") != "P2_BRANCHING_ADJUSTED"
        or p1_wire.get("channel_derivation") != "identity_positive_majorant_v1"
        or p2_wire.get("channel_derivation")
        != "entrywise_square_no_cross_terms_synthetic_v1"
        or p1_wire.get("factor_restriction_sha256s") != factor_sha256s
        or p2_wire.get("factor_restriction_sha256s") != factor_sha256s
        or p1_wire.get("composition_scope")
        != "declared_abstract_coordinate_composition_v1"
        or p2_wire.get("composition_scope")
        != "declared_abstract_coordinate_composition_v1"
        or p1_wire.get("inequality_pass") is not True
        or p2_wire.get("inequality_pass") is not True
        or return_wire.get("iteration_scope")
        != "stationary_reuse_of_restricted_abstract_majorant_v1"
        or return_wire.get("finite_only") is not True
        or return_wire.get("horizon") != 3
        or return_wire.get("direct_zero_memory_positive") is not True
    ):
        raise StrictContractError("binding-gate certificate roles or scopes are invalid")
    weighted_norm = _rational_from_wire(
        return_wire.get("weighted_norm"), "return-memory weighted norm"
    )
    if weighted_norm != ExactRational(21, 2):
        raise StrictContractError("binding gate return-memory authority changed")

    source_seal = _sha256(
        {
            "schema_version": "odlrq.e2.certified-support-source-seal.v1",
            "candidate_universe_manifest_sha256": manifest_sha,
            "p1_cocycle_sha256": p1_sha,
            "p2_cocycle_sha256": p2_sha,
            "return_memory_bound_sha256": return_sha,
        }
    )
    return {
        "manifest_wire": manifest_wire,
        "manifest_sha": manifest_sha,
        "p1_sha": p1_sha,
        "p2_sha": p2_sha,
        "return_sha": return_sha,
        "source_seal": source_seal,
    }


def _derive_token_wire(
    *,
    manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
) -> tuple[dict[str, Any], str]:
    context = _token_authority_context(
        manifest=manifest,
        p1_cocycle=p1_cocycle,
        p2_cocycle=p2_cocycle,
        return_memory=return_memory,
    )
    candidate_rows = context["manifest_wire"]["candidate_rows"]
    threshold = ExactRational(2)
    ungated_ranking = _ranking(candidate_rows)
    decision_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    rejected_candidate_ids: list[str] = []
    for row in candidate_rows:
        bound = _rational_from_wire(row["bound"], "candidate decision bound")
        accepted = _less_equal(bound, threshold)
        authority_bundle = {
            "schema_version": _DECISION_AUTHORITY_SCHEMA,
            "candidate_row": row,
            "p1_cocycle_sha256": context["p1_sha"],
            "p2_cocycle_sha256": context["p2_sha"],
            "return_memory_bound_sha256": context["return_sha"],
        }
        decision_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "bound": bound.to_dict(),
                "threshold": threshold.to_dict(),
                "decision": "ACCEPT" if accepted else "REJECT",
                "reason": "BOUND_LE_THRESHOLD" if accepted else "BOUND_GT_THRESHOLD",
                "authority_bundle_sha256": _sha256(authority_bundle),
            }
        )
        if accepted:
            accepted_rows.append(row)
        else:
            rejected_candidate_ids.append(row["candidate_id"])
    if not accepted_rows:
        raise StrictContractError("the fixed E2 gate produced no certified support")

    gated_ranking = _ranking(accepted_rows)
    support_candidate_ids = [row["candidate_id"] for row in accepted_rows]
    denominator = len(candidate_rows)
    numerator = len(accepted_rows)
    coverage = ExactRational(numerator, denominator)
    ranking_changed = ungated_ranking[0] != gated_ranking[0]
    if (
        ungated_ranking != ["c1", "c2", "c0"]
        or gated_ranking != ["c2", "c0"]
        or support_candidate_ids != ["c0", "c2"]
        or rejected_candidate_ids != ["c1"]
        or coverage != ExactRational(2, 3)
        or not ranking_changed
    ):
        raise StrictContractError("the fixed E2 gate is nonbinding or changed scope")

    invalidation = {
        "schema_version": _INVALIDATION_SCHEMA,
        "endpoint_id": _ENDPOINT_ID,
        "candidate_universe_manifest_sha256": context["manifest_sha"],
        "p1_cocycle_sha256": context["p1_sha"],
        "p2_cocycle_sha256": context["p2_sha"],
        "return_memory_bound_sha256": context["return_sha"],
        "comparator": _COMPARATOR,
        "threshold": threshold.to_dict(),
        "decision_rows": decision_rows,
        "denominator": denominator,
        "numerator": numerator,
        "coverage": coverage.to_dict(),
        "ungated_ranking": ungated_ranking,
        "gated_ranking": gated_ranking,
        "support_candidate_ids": support_candidate_ids,
        "rejected_candidate_ids": rejected_candidate_ids,
        "abstained_candidate_ids": [],
        "ranking_changed": ranking_changed,
    }
    wire = {
        **invalidation,
        "schema_version": _TOKEN_SCHEMA,
        "invalidation_sha256": _sha256(invalidation),
        "verification_disposition": _TOKEN_DISPOSITION,
    }
    return wire, context["source_seal"]


@dataclass(frozen=True, init=False)
class CertifiedSupportToken:
    _manifest: CandidateUniverseManifest = field(repr=False)
    _p1_cocycle: CocycleCertificate = field(repr=False)
    _p2_cocycle: CocycleCertificate = field(repr=False)
    _return_memory: ReturnMemoryBound = field(repr=False)
    _source_seal_sha256: str = field(repr=False)
    _construction_seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("certified support token has no public constructor")

    def __post_init__(self) -> None:
        if type(self) is not CertifiedSupportToken:
            raise StrictContractError("CertifiedSupportToken subclasses are forbidden")
        if self._construction_seal is not _TOKEN_SEAL:
            raise StrictContractError("certified support requires the binding E2 gate")
        _require_digest(self._source_seal_sha256, "certified support source seal")

    @classmethod
    def from_dict(
        cls,
        value: dict,
        *,
        manifest: CandidateUniverseManifest,
        p1_cocycle: CocycleCertificate,
        p2_cocycle: CocycleCertificate,
        return_memory: ReturnMemoryBound,
    ) -> "CertifiedSupportToken":
        if cls is not CertifiedSupportToken:
            raise StrictContractError("polymorphic certified-support parsing is forbidden")
        supplied = _preflight_token_wire(value)
        expected, source_seal = _derive_token_wire(
            manifest=manifest,
            p1_cocycle=p1_cocycle,
            p2_cocycle=p2_cocycle,
            return_memory=return_memory,
        )
        if canonical_contract_bytes(supplied) != canonical_contract_bytes(expected):
            raise StrictContractError(
                "certified support wire disagrees with retained exact authorities"
            )
        return _construct_token(
            manifest=manifest,
            p1_cocycle=p1_cocycle,
            p2_cocycle=p2_cocycle,
            return_memory=return_memory,
            source_seal=source_seal,
        )

    @property
    def certified_support_token_sha256(self) -> str:
        return _sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        self.__post_init__()
        wire, source_seal = _derive_token_wire(
            manifest=self._manifest,
            p1_cocycle=self._p1_cocycle,
            p2_cocycle=self._p2_cocycle,
            return_memory=self._return_memory,
        )
        if source_seal != _require_digest(
            self._source_seal_sha256, "certified support source seal"
        ):
            raise StrictContractError("certified support retained authority changed")
        return wire


def _construct_token(
    *,
    manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
    source_seal: str,
) -> CertifiedSupportToken:
    result = object.__new__(CertifiedSupportToken)
    object.__setattr__(result, "_manifest", manifest)
    object.__setattr__(result, "_p1_cocycle", p1_cocycle)
    object.__setattr__(result, "_p2_cocycle", p2_cocycle)
    object.__setattr__(result, "_return_memory", return_memory)
    object.__setattr__(result, "_source_seal_sha256", source_seal)
    object.__setattr__(result, "_construction_seal", _TOKEN_SEAL)
    result.__post_init__()
    return result


def apply_e2_binding_gate(
    *,
    manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
) -> CertifiedSupportToken:
    _wire, source_seal = _derive_token_wire(
        manifest=manifest,
        p1_cocycle=p1_cocycle,
        p2_cocycle=p2_cocycle,
        return_memory=return_memory,
    )
    return _construct_token(
        manifest=manifest,
        p1_cocycle=p1_cocycle,
        p2_cocycle=p2_cocycle,
        return_memory=return_memory,
        source_seal=source_seal,
    )


__all__ = [
    "CandidateUniverseManifest",
    "CertifiedSupportToken",
    "apply_e2_binding_gate",
    "build_declared_e2_candidate_universe",
]
