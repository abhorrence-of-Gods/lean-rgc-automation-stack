from __future__ import annotations

"""Finite-fiber maximum-entropy model selection on an immutable E2 support.

This module is deliberately a nominal layer.  It can reweight the atoms named
by an accepted E2 support reference, but it cannot create or widen that
support.  Exact rational geometry is decided before NumPy is imported.
"""

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
import math
import re
import struct
from typing import Any, Mapping, Sequence

from .contracts import ExactRational, StrictContractError, canonical_contract_bytes
from .selection import CertifiedSupportToken as _CertifiedSupportToken


ME0_AUTHORITY_COMMIT_SHA = "0ff63861a2957b53f4c0b5f2948d561d936337ca"
ME0_AUTHORITY_PARENT_SHA = "7a8b28872439dd61d40174c2500c5990790002be"
ME0_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md"
)
ME0_AUTHORITY_DOCUMENT_BLOB_SHA = "831c226a2b25ae367b288a8fb18d7cb7afb42124"
ME0_AUTHORITY_CI_RUN_ID = "29551068987"
ME0_AUTHORITY_CI_JOB_ID = "87793466452"
ME0_WINDOWS_RUNTIME_MANIFEST_SHA256 = (
    "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
)

_ACCEPTED_E2_COMMIT_SHA = "7a8b28872439dd61d40174c2500c5990790002be"
_ACCEPTED_E2_TREE_SHA = "d54ed9fab52da4929843fabdeb3c1e1920994f6a"
_ACCEPTED_E2_TOKEN_SHA256 = (
    "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"
)
_ACCEPTED_SUPPORT = ("c0", "c2")
_TIER = "NOMINAL_MODEL_SELECTION_ONLY"

_REFERENCE_SCHEMA = "odlrq.me0.declared-e2-support-reference.v1"
_PROBLEM_SCHEMA = "odlrq.me0.maxent-problem.v1"
_GEOMETRY_SCHEMA = "odlrq.me0.moment-geometry.v1"
_ORBIT_SCHEMA = "odlrq.me0.orbit-reference-law.v1"
_OPERATOR_SCHEMA = "odlrq.me0.operator-span-residual.v1"
_RESULT_SCHEMA = "odlrq.me0.maxent-result.v1"

_MAX_SUPPORT = 32
_MAX_STATISTIC_DIMENSION = 4
_MAX_ORBIT_SIZE = 32
_MAX_INPUT_BITS = 256
_MAX_INTERMEDIATE_BITS = 4096
_MAX_OPERATOR_DIMENSION = 32
_MAX_RULE_COLUMNS = 32
_MAX_OPERATOR_CELLS = 1024
_MAX_SUBSET_WORK = 242_824
_MAX_ITERATIONS = 128
_MAX_BACKTRACKS = 32
_RCOND = 1e-12
_MOMENT_TOL = 1e-10
_SIMPLEX_TOL = 1e-12
_DUAL_TOL = 1e-10
_OPERATOR_TOL = 1e-10

_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9A-F]{64}\Z")
_CANONICAL_FLOAT = re.compile(
    r"(?:0|-[1-9][0-9]*(?:\.[0-9]+)?|[1-9][0-9]*(?:\.[0-9]+)?|"
    r"-?0\.[0-9]+)(?:e[+-]?[0-9]+)?\Z"
)


class MaxEntStatus(str, Enum):
    INTERIOR_SOLVED = "INTERIOR_SOLVED"
    BOUNDARY_NO_FINITE_PARAMETER = "BOUNDARY_NO_FINITE_PARAMETER"
    OUTSIDE_HULL = "OUTSIDE_HULL"
    SINGULAR_STATISTICS = "SINGULAR_STATISTICS"
    NUMERIC_FAILURE = "NUMERIC_FAILURE"


def _exact_dict(value: Any, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or any(type(k) is not str for k in value):
        raise StrictContractError(f"{where} must be an exact object")
    if set(value) != fields:
        raise StrictContractError(
            f"{where} fields mismatch; missing={sorted(fields - set(value))}, "
            f"unknown={sorted(set(value) - fields)}"
        )
    return value


def _exact_list(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictContractError(f"{where} must be an array")
    return value


def _exact_string(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise StrictContractError(f"{where} must be a nonempty exact string")
    return value


def _bounded_wire_preflight(
    value: Any,
    where: str,
    *,
    max_nodes: int = 20_000,
    max_depth: int = 10,
) -> None:
    """Reject unbounded/non-strict JSON before canonical serialization.

    The component limits dominate every frozen ME0 problem/result shape:
    support/rule arrays are at most 32, objects at most 64 fields, and a
    4096-bit derived rational needs fewer than 1,300 decimal characters.
    """

    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise StrictContractError(f"{where} exceeds bounded wire traversal")
        if type(current) is dict:
            if len(current) > 64 or any(
                type(key) is not str or not key or len(key) > 128 for key in current
            ):
                raise StrictContractError(f"{where} object shape exceeds wire caps")
            stack.extend((child, depth + 1) for child in current.values())
        elif type(current) is list:
            if len(current) > 32:
                raise StrictContractError(f"{where} array exceeds the 32-cell wire cap")
            stack.extend((child, depth + 1) for child in current)
        elif type(current) is str:
            if len(current) > 1_300:
                raise StrictContractError(f"{where} string exceeds the derived-rational cap")
        elif type(current) is int:
            if abs(current).bit_length() > 64:
                raise StrictContractError(f"{where} integer exceeds strict wire cap")
        elif type(current) is bool or current is None:
            continue
        else:
            raise StrictContractError(f"{where} contains a non-strict JSON scalar")


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_contract_bytes(value)).hexdigest().upper()


def _require_sha256(value: Any, where: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be an uppercase SHA-256 digest")
    return value


def _require_commit(value: Any, expected: str, where: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None or value != expected:
        raise StrictContractError(f"{where} does not match the frozen commit")
    return value


def _rational(value: Any, where: str, *, nonnegative: bool = False) -> ExactRational:
    if type(value) is not ExactRational:
        raise StrictContractError(f"{where} must be an exact ExactRational")
    if (
        abs(value.numerator).bit_length() > _MAX_INPUT_BITS
        or value.denominator.bit_length() > _MAX_INPUT_BITS
    ):
        raise StrictContractError(f"{where} exceeds the 256-bit input cap")
    if nonnegative and value.numerator < 0:
        raise StrictContractError(f"{where} must be nonnegative")
    return value


def _rational_from_wire(value: Any, where: str) -> ExactRational:
    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact-rational object")
    result = ExactRational.from_dict(value)
    return _rational(result, where)


def _derived_rational_from_wire(value: Any, where: str) -> ExactRational:
    """Parse a recomputed exact output under the wider intermediate cap."""

    if type(value) is not dict:
        raise StrictContractError(f"{where} must be an exact-rational object")
    result = ExactRational.from_dict(value)
    if (
        abs(result.numerator).bit_length() > _MAX_INTERMEDIATE_BITS
        or result.denominator.bit_length() > _MAX_INTERMEDIATE_BITS
    ):
        raise StrictContractError(f"{where} exceeds the 4096-bit derived-output cap")
    return result


def _fraction(value: ExactRational) -> Fraction:
    return Fraction(value.numerator, value.denominator)


def _cap_fraction(value: Fraction, where: str) -> Fraction:
    if (
        abs(value.numerator).bit_length() > _MAX_INTERMEDIATE_BITS
        or value.denominator.bit_length() > _MAX_INTERMEDIATE_BITS
    ):
        raise StrictContractError(f"{where} exceeds the 4096-bit intermediate cap")
    return value


def _fadd(a: Fraction, b: Fraction) -> Fraction:
    return _cap_fraction(a + b, "exact addition")


def _fsub(a: Fraction, b: Fraction) -> Fraction:
    return _cap_fraction(a - b, "exact subtraction")


def _fmul(a: Fraction, b: Fraction) -> Fraction:
    return _cap_fraction(a * b, "exact multiplication")


def _fdiv(a: Fraction, b: Fraction) -> Fraction:
    if b == 0:
        raise StrictContractError("exact division by zero")
    return _cap_fraction(a / b, "exact division")


def _as_exact(value: Fraction) -> ExactRational:
    _cap_fraction(value, "exact output")
    return ExactRational(value.numerator, value.denominator)


def _float_bits(value: float) -> bytes:
    return struct.pack(">d", value)


def _float_text(value: float, where: str) -> str:
    if type(value) is not float or not math.isfinite(value):
        raise StrictContractError(f"{where} must be finite binary64")
    if value == 0.0:
        value = 0.0
    text = format(value, ".17g").replace("E", "e")
    decoded = float(text)
    if (
        not math.isfinite(decoded)
        or _float_bits(decoded) != _float_bits(value)
        or format(decoded, ".17g").replace("E", "e") != text
    ):
        raise StrictContractError(f"{where} is not canonical binary64 text")
    return text


def _float_from_wire(value: Any, where: str) -> float:
    if type(value) is not str or _CANONICAL_FLOAT.fullmatch(value) is None:
        raise StrictContractError(f"{where} must be canonical binary64 text")
    try:
        result = float(value)
    except ValueError as exc:
        raise StrictContractError(f"{where} is not binary64 text") from exc
    if not math.isfinite(result) or (result == 0.0 and value.startswith("-")):
        raise StrictContractError(f"{where} is nonfinite or negative zero")
    if _float_text(result, where) != value:
        raise StrictContractError(f"{where} is not decode-reencode canonical")
    return result


def _authority_wire() -> dict[str, Any]:
    return {
        "me0_authority_commit_sha": ME0_AUTHORITY_COMMIT_SHA,
        "me0_authority_parent_sha": ME0_AUTHORITY_PARENT_SHA,
        "me0_authority_document_path": ME0_AUTHORITY_DOCUMENT_PATH,
        "me0_authority_document_blob_sha": ME0_AUTHORITY_DOCUMENT_BLOB_SHA,
        "me0_authority_ci_run_id": ME0_AUTHORITY_CI_RUN_ID,
        "me0_authority_ci_job_id": ME0_AUTHORITY_CI_JOB_ID,
    }


_AUTHORITY_FIELDS = set(_authority_wire())


def _check_authority_wire(value: Mapping[str, Any], where: str) -> None:
    expected = _authority_wire()
    for name, literal in expected.items():
        if value.get(name) != literal:
            raise StrictContractError(f"{where} {name} does not match frozen authority")


@dataclass(frozen=True, init=False)
class DeclaredE2SupportReference:
    accepted_e2_commit_sha: str
    accepted_e2_tree_sha: str
    certified_support_token_sha256: str
    support_candidate_ids: tuple[str, ...]
    tier: str
    runtime_manifest_sha256: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("declared E2 support reference has no public constructor")

    @property
    def row_count(self) -> int:
        return len(self.support_candidate_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _REFERENCE_SCHEMA,
            **_authority_wire(),
            "accepted_e2_commit_sha": self.accepted_e2_commit_sha,
            "accepted_e2_tree_sha": self.accepted_e2_tree_sha,
            "certified_support_token_sha256": self.certified_support_token_sha256,
            "support_candidate_ids": list(self.support_candidate_ids),
            "tier": self.tier,
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeclaredE2SupportReference":
        _bounded_wire_preflight(value, "DeclaredE2SupportReference wire")
        fields = {
            "schema_version",
            *_AUTHORITY_FIELDS,
            "accepted_e2_commit_sha",
            "accepted_e2_tree_sha",
            "certified_support_token_sha256",
            "support_candidate_ids",
            "tier",
            "runtime_manifest_sha256",
        }
        obj = _exact_dict(value, fields, "DeclaredE2SupportReference")
        _check_authority_wire(obj, "DeclaredE2SupportReference")
        if obj["schema_version"] != _REFERENCE_SCHEMA:
            raise StrictContractError("declared support schema mismatch")
        _require_commit(
            obj["accepted_e2_commit_sha"], _ACCEPTED_E2_COMMIT_SHA, "accepted E2 commit"
        )
        _require_commit(
            obj["accepted_e2_tree_sha"], _ACCEPTED_E2_TREE_SHA, "accepted E2 tree"
        )
        if obj["certified_support_token_sha256"] != _ACCEPTED_E2_TOKEN_SHA256:
            raise StrictContractError("declared support token digest mismatch")
        ids = _exact_list(obj["support_candidate_ids"], "support_candidate_ids")
        if len(ids) != len(_ACCEPTED_SUPPORT) or ids != list(_ACCEPTED_SUPPORT):
            raise StrictContractError("declared E2 support order changed")
        if obj["tier"] != _TIER:
            raise StrictContractError("declared support tier mismatch")
        if obj["runtime_manifest_sha256"] != ME0_WINDOWS_RUNTIME_MANIFEST_SHA256:
            raise StrictContractError("ME0 runtime manifest digest mismatch")
        instance = object.__new__(cls)
        object.__setattr__(instance, "accepted_e2_commit_sha", _ACCEPTED_E2_COMMIT_SHA)
        object.__setattr__(instance, "accepted_e2_tree_sha", _ACCEPTED_E2_TREE_SHA)
        object.__setattr__(instance, "certified_support_token_sha256", _ACCEPTED_E2_TOKEN_SHA256)
        object.__setattr__(instance, "support_candidate_ids", _ACCEPTED_SUPPORT)
        object.__setattr__(instance, "tier", _TIER)
        object.__setattr__(instance, "runtime_manifest_sha256", ME0_WINDOWS_RUNTIME_MANIFEST_SHA256)
        return instance


def _validate_token_wire(value: Any) -> tuple[dict[str, Any], tuple[str, ...], str]:
    _bounded_wire_preflight(value, "CertifiedSupportToken wire", max_nodes=512)
    required = {
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
    obj = _exact_dict(value, required, "CertifiedSupportToken wire")
    decisions = _exact_list(obj["decision_rows"], "decision_rows")
    if len(decisions) != 3:
        raise StrictContractError("support token must have exactly three decision rows")
    decision_fields = {
        "authority_bundle_sha256",
        "bound",
        "candidate_id",
        "decision",
        "reason",
        "threshold",
    }
    for index, row in enumerate(decisions):
        _exact_dict(row, decision_fields, f"decision_rows[{index}]")
    for name, length in (
        ("ungated_ranking", 3),
        ("gated_ranking", 2),
        ("support_candidate_ids", 2),
        ("rejected_candidate_ids", 1),
        ("abstained_candidate_ids", 0),
    ):
        if len(_exact_list(obj[name], name)) != length:
            raise StrictContractError(f"support token {name} cardinality changed")
    # Only the bounded, exact-shape payload may reach canonical serialization.
    try:
        wire_bytes = canonical_contract_bytes(obj)
    except Exception as exc:
        if isinstance(exc, StrictContractError):
            raise
        raise StrictContractError("support token is outside strict canonical JSON") from exc
    digest = hashlib.sha256(wire_bytes).hexdigest().upper()
    if digest != _ACCEPTED_E2_TOKEN_SHA256:
        raise StrictContractError("support token does not match the frozen accepted wire")
    if len(wire_bytes) != 2185:
        raise StrictContractError("support token wire byte count changed")
    if (
        obj["schema_version"] != "odlrq.e2.certified-support-token.v1"
        or obj["endpoint_id"] != "u24_e2_declared_square_endpoint_v1"
        or obj["verification_disposition"] != "E2_BINDING_SUPPORT_CERTIFIED"
        or obj["support_candidate_ids"] != list(_ACCEPTED_SUPPORT)
        or obj["rejected_candidate_ids"] != ["c1"]
        or obj["abstained_candidate_ids"] != []
    ):
        raise StrictContractError("support token fixed semantics mismatch")
    return obj, _ACCEPTED_SUPPORT, digest


def make_declared_e2_support_reference(
    token_wire: Mapping[str, Any],
    *,
    accepted_e2_commit_sha: str = _ACCEPTED_E2_COMMIT_SHA,
    accepted_e2_tree_sha: str = _ACCEPTED_E2_TREE_SHA,
) -> DeclaredE2SupportReference:
    _require_commit(accepted_e2_commit_sha, _ACCEPTED_E2_COMMIT_SHA, "accepted E2 commit")
    _require_commit(accepted_e2_tree_sha, _ACCEPTED_E2_TREE_SHA, "accepted E2 tree")
    wire, support, digest = _validate_token_wire(token_wire)
    del wire
    payload = {
        "schema_version": _REFERENCE_SCHEMA,
        **_authority_wire(),
        "accepted_e2_commit_sha": accepted_e2_commit_sha,
        "accepted_e2_tree_sha": accepted_e2_tree_sha,
        "certified_support_token_sha256": digest,
        "support_candidate_ids": list(support),
        "tier": _TIER,
        "runtime_manifest_sha256": ME0_WINDOWS_RUNTIME_MANIFEST_SHA256,
    }
    return DeclaredE2SupportReference.from_dict(payload)


def bind_e2_support(
    token: _CertifiedSupportToken,
    *,
    accepted_e2_commit_sha: str = _ACCEPTED_E2_COMMIT_SHA,
    accepted_e2_tree_sha: str = _ACCEPTED_E2_TREE_SHA,
) -> DeclaredE2SupportReference:
    if type(token) is not _CertifiedSupportToken:
        raise StrictContractError("live support binding requires exact CertifiedSupportToken type")
    if "to_dict" in vars(token):
        raise StrictContractError("instance-level CertifiedSupportToken serializer override")
    wire = _CertifiedSupportToken.to_dict(token)
    return make_declared_e2_support_reference(
        wire,
        accepted_e2_commit_sha=accepted_e2_commit_sha,
        accepted_e2_tree_sha=accepted_e2_tree_sha,
    )


def _validate_keyed_rows(
    rows: Any,
    support: tuple[str, ...],
    where: str,
) -> tuple[tuple[str, Any], ...]:
    if type(rows) is not tuple or len(rows) != len(support):
        raise StrictContractError(f"{where} must have one tuple row per support atom")
    # Validate the full outer shape and IDs before copying any row value.
    for index, row in enumerate(rows):
        if type(row) is not tuple or len(row) != 2:
            raise StrictContractError(f"{where}[{index}] must be an exact keyed pair")
        if type(row[0]) is not str or row[0] != support[index]:
            raise StrictContractError(f"{where} is reordered, duplicated, or support-substituted")
    # The caller supplied an exact immutable tuple.  Retain it after validation
    # rather than allocating a second row table before cell checks complete.
    return rows


def _rows_to_wire(
    rows: tuple[tuple[str, Any], ...],
    encode: Any,
) -> list[dict[str, Any]]:
    return [{"candidate_id": key, "value": encode(value)} for key, value in rows]


def _rows_from_wire(value: Any, where: str, decode: Any) -> tuple[tuple[str, Any], ...]:
    rows = _exact_list(value, where)
    result: list[tuple[str, Any]] = []
    for index, row in enumerate(rows):
        obj = _exact_dict(row, {"candidate_id", "value"}, f"{where}[{index}]")
        result.append((_exact_string(obj["candidate_id"], where), decode(obj["value"], where)))
    return tuple(result)


def _preflight_problem_wire_tables(
    obj: Mapping[str, Any], support: tuple[str, ...]
) -> None:
    """Bound every problem wire shape before decoding/copying row payloads."""

    n = len(support)
    if not (1 <= n <= _MAX_SUPPORT):
        raise StrictContractError("problem wire support exceeds registered cap")
    target = _exact_list(obj["target"], "target")
    if not (1 <= len(target) <= _MAX_STATISTIC_DIMENSION):
        raise StrictContractError("problem wire target dimension exceeds cap")
    d = len(target)
    columns = _exact_list(obj["exact_rule_column_ids"], "exact_rule_column_ids")
    c = len(columns)
    if c > _MAX_RULE_COLUMNS or n > _MAX_OPERATOR_DIMENSION:
        raise StrictContractError("problem wire operator dimensions exceed caps")
    if n * c > _MAX_OPERATOR_CELLS:
        raise StrictContractError("problem wire operator cell count exceeds cap")
    if any(type(column) is not str or not column for column in columns):
        raise StrictContractError("problem wire rule-column IDs must be strings")
    if len(set(columns)) != c:
        raise StrictContractError("problem wire rule-column IDs contain duplicates")
    subset_work = sum(math.comb(n, k) for k in range(1, min(n, d + 1) + 1))
    if subset_work > _MAX_SUBSET_WORK:
        raise StrictContractError("problem wire lazy subset-work cap exceeded")

    scalar_tables = (
        "reference_mass_rows",
        "orbit_size_rows",
        "row_load_rows",
        "nominal_operator_rows",
    )
    vector_tables = {
        "statistic_rows": d,
        "exact_rule_rows": c,
    }
    for table_name in (*scalar_tables, *vector_tables):
        rows = _exact_list(obj[table_name], table_name)
        if len(rows) != n:
            raise StrictContractError(
                f"{table_name} must have exactly one wire row per support atom"
            )
        for index, row in enumerate(rows):
            row_obj = _exact_dict(
                row, {"candidate_id", "value"}, f"{table_name}[{index}]"
            )
            if row_obj["candidate_id"] != support[index]:
                raise StrictContractError(
                    f"{table_name} is reordered, duplicated, or support-substituted"
                )
            if table_name in vector_tables:
                cells = _exact_list(row_obj["value"], f"{table_name}[{index}].value")
                if len(cells) != vector_tables[table_name]:
                    raise StrictContractError(
                        f"{table_name} row width disagrees with frozen dimension"
                    )


@dataclass(frozen=True, init=False)
class MaxEntProblem:
    support_reference: DeclaredE2SupportReference
    reference_mass_rows: tuple[tuple[str, ExactRational], ...]
    statistic_rows: tuple[tuple[str, tuple[ExactRational, ...]], ...]
    orbit_size_rows: tuple[tuple[str, int], ...]
    target: tuple[ExactRational, ...]
    kl_radius: ExactRational
    row_load_rows: tuple[tuple[str, ExactRational], ...]
    nominal_operator_rows: tuple[tuple[str, ExactRational], ...]
    exact_rule_column_ids: tuple[str, ...]
    exact_rule_rows: tuple[tuple[str, tuple[ExactRational, ...]], ...]
    row_table_sha256: str
    problem_sha256: str
    tier: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StrictContractError("MaxEntProblem must be built by create/from_dict")

    @property
    def support_candidate_ids(self) -> tuple[str, ...]:
        return self.support_reference.support_candidate_ids

    @property
    def declared_dimension(self) -> int:
        return len(self.target)

    @classmethod
    def create(
        cls,
        support_reference: DeclaredE2SupportReference,
        *,
        reference_mass_rows: tuple[tuple[str, ExactRational], ...],
        statistic_rows: tuple[tuple[str, tuple[ExactRational, ...]], ...],
        orbit_size_rows: tuple[tuple[str, int], ...],
        target: tuple[ExactRational, ...],
        kl_radius: ExactRational,
        row_load_rows: tuple[tuple[str, ExactRational], ...],
        nominal_operator_rows: tuple[tuple[str, ExactRational], ...],
        exact_rule_column_ids: tuple[str, ...],
        exact_rule_rows: tuple[tuple[str, tuple[ExactRational, ...]], ...],
    ) -> "MaxEntProblem":
        if type(support_reference) is not DeclaredE2SupportReference:
            raise StrictContractError("problem requires an exact declared E2 support reference")
        # Reparse to detect an object mutated through object.__setattr__.
        support_reference = DeclaredE2SupportReference.from_dict(support_reference.to_dict())
        support = support_reference.support_candidate_ids
        n = len(support)
        if n < 1 or n > _MAX_SUPPORT:
            raise StrictContractError("support size exceeds the registered cap")
        if type(target) is not tuple or not (1 <= len(target) <= _MAX_STATISTIC_DIMENSION):
            raise StrictContractError("target must declare between one and four statistics")
        d = len(target)
        for index, value in enumerate(target):
            _rational(value, f"target[{index}]")
        _rational(kl_radius, "kl_radius", nonnegative=True)
        ref = _validate_keyed_rows(reference_mass_rows, support, "reference_mass_rows")
        stats = _validate_keyed_rows(statistic_rows, support, "statistic_rows")
        orbits = _validate_keyed_rows(orbit_size_rows, support, "orbit_size_rows")
        loads = _validate_keyed_rows(row_load_rows, support, "row_load_rows")
        nominal = _validate_keyed_rows(nominal_operator_rows, support, "nominal_operator_rows")
        rules = _validate_keyed_rows(exact_rule_rows, support, "exact_rule_rows")
        if type(exact_rule_column_ids) is not tuple:
            raise StrictContractError("exact_rule_column_ids must be an exact tuple")
        c = len(exact_rule_column_ids)
        if c > _MAX_RULE_COLUMNS or n * c > _MAX_OPERATOR_CELLS:
            raise StrictContractError("exact-rule matrix exceeds registered caps")
        if n > _MAX_OPERATOR_DIMENSION:
            raise StrictContractError("vectorized operator dimension exceeds cap")
        if any(type(x) is not str or not x for x in exact_rule_column_ids):
            raise StrictContractError("exact-rule column IDs must be nonempty strings")
        if len(set(exact_rule_column_ids)) != c:
            raise StrictContractError("exact-rule column IDs contain duplicates")
        subset_work = sum(math.comb(n, k) for k in range(1, min(n, d + 1) + 1))
        if subset_work > _MAX_SUBSET_WORK:
            raise StrictContractError("exact lazy subset-work cap exceeded")
        for index in range(n):
            q = _rational(ref[index][1], f"reference_mass_rows[{index}]", nonnegative=True)
            if q.numerator == 0:
                raise StrictContractError("reference masses must be strictly positive")
            stat = stats[index][1]
            if type(stat) is not tuple or len(stat) != d:
                raise StrictContractError("every statistic row must match target dimension")
            for j, value in enumerate(stat):
                _rational(value, f"statistic_rows[{index}][{j}]")
            orbit = orbits[index][1]
            if type(orbit) is not int or not (1 <= orbit <= _MAX_ORBIT_SIZE):
                raise StrictContractError("orbit sizes must be exact integers in [1,32]")
            _rational(loads[index][1], f"row_load_rows[{index}]", nonnegative=True)
            _rational(nominal[index][1], f"nominal_operator_rows[{index}]")
            rule_row = rules[index][1]
            if type(rule_row) is not tuple or len(rule_row) != c:
                raise StrictContractError("exact-rule rows must match the frozen column order")
            for j, value in enumerate(rule_row):
                _rational(value, f"exact_rule_rows[{index}][{j}]")
        instance = object.__new__(cls)
        for name, value in (
            ("support_reference", support_reference),
            ("reference_mass_rows", ref),
            ("statistic_rows", stats),
            ("orbit_size_rows", orbits),
            ("target", tuple(target)),
            ("kl_radius", kl_radius),
            ("row_load_rows", loads),
            ("nominal_operator_rows", nominal),
            ("exact_rule_column_ids", tuple(exact_rule_column_ids)),
            ("exact_rule_rows", rules),
            ("tier", _TIER),
        ):
            object.__setattr__(instance, name, value)
        row_digest = _sha256(instance._row_table_wire())
        object.__setattr__(instance, "row_table_sha256", row_digest)
        problem_core = instance._wire(include_digest=False)
        problem_sha = _sha256(problem_core)
        object.__setattr__(instance, "problem_sha256", problem_sha)
        return instance

    def _row_table_wire(self) -> dict[str, Any]:
        return {
            "support_candidate_ids": list(self.support_candidate_ids),
            "reference_mass_rows": _rows_to_wire(self.reference_mass_rows, lambda x: x.to_dict()),
            "statistic_rows": _rows_to_wire(
                self.statistic_rows, lambda row: [x.to_dict() for x in row]
            ),
            "orbit_size_rows": _rows_to_wire(self.orbit_size_rows, lambda x: x),
            "row_load_rows": _rows_to_wire(self.row_load_rows, lambda x: x.to_dict()),
            "nominal_operator_rows": _rows_to_wire(
                self.nominal_operator_rows, lambda x: x.to_dict()
            ),
            "exact_rule_column_ids": list(self.exact_rule_column_ids),
            "exact_rule_rows": _rows_to_wire(
                self.exact_rule_rows, lambda row: [x.to_dict() for x in row]
            ),
        }

    def _wire(self, *, include_digest: bool) -> dict[str, Any]:
        wire = {
            "schema_version": _PROBLEM_SCHEMA,
            **_authority_wire(),
            "runtime_manifest_sha256": ME0_WINDOWS_RUNTIME_MANIFEST_SHA256,
            "support_reference": self.support_reference.to_dict(),
            **self._row_table_wire(),
            "target": [x.to_dict() for x in self.target],
            "kl_radius": self.kl_radius.to_dict(),
            "row_table_sha256": self.row_table_sha256,
            "tier": self.tier,
        }
        if include_digest:
            wire["problem_sha256"] = self.problem_sha256
        return wire

    def to_dict(self) -> dict[str, Any]:
        return self._wire(include_digest=True)

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        reference: DeclaredE2SupportReference | None = None,
    ) -> "MaxEntProblem":
        _bounded_wire_preflight(value, "MaxEntProblem wire")
        fields = {
            "schema_version", *_AUTHORITY_FIELDS, "runtime_manifest_sha256",
            "support_reference", "support_candidate_ids", "reference_mass_rows",
            "statistic_rows", "orbit_size_rows", "row_load_rows",
            "nominal_operator_rows", "exact_rule_column_ids", "exact_rule_rows",
            "target", "kl_radius", "row_table_sha256", "problem_sha256", "tier",
        }
        obj = _exact_dict(value, fields, "MaxEntProblem")
        _check_authority_wire(obj, "MaxEntProblem")
        if obj["schema_version"] != _PROBLEM_SCHEMA or obj["tier"] != _TIER:
            raise StrictContractError("MaxEntProblem fixed fields mismatch")
        if obj["runtime_manifest_sha256"] != ME0_WINDOWS_RUNTIME_MANIFEST_SHA256:
            raise StrictContractError("MaxEntProblem runtime binding mismatch")
        ref = DeclaredE2SupportReference.from_dict(obj["support_reference"])
        if reference is not None:
            if type(reference) is not DeclaredE2SupportReference:
                raise StrictContractError("problem reference must have exact declared-reference type")
            retained = DeclaredE2SupportReference.from_dict(reference.to_dict())
            if canonical_contract_bytes(retained.to_dict()) != canonical_contract_bytes(ref.to_dict()):
                raise StrictContractError("problem wire is not bound to the supplied E2 reference")
        if obj["support_candidate_ids"] != list(ref.support_candidate_ids):
            raise StrictContractError("problem support rows are not live-bound to E2")
        _preflight_problem_wire_tables(obj, ref.support_candidate_ids)
        rat = lambda x, w: _rational_from_wire(x, w)
        vector = lambda x, w: tuple(
            _rational_from_wire(v, w) for v in _exact_list(x, w)
        )
        integer = lambda x, w: x if type(x) is int else (_raise(f"{w} must be integer"))
        created = cls.create(
            ref,
            reference_mass_rows=_rows_from_wire(obj["reference_mass_rows"], "reference_mass_rows", rat),
            statistic_rows=_rows_from_wire(obj["statistic_rows"], "statistic_rows", vector),
            orbit_size_rows=_rows_from_wire(obj["orbit_size_rows"], "orbit_size_rows", integer),
            target=tuple(_rational_from_wire(x, "target") for x in _exact_list(obj["target"], "target")),
            kl_radius=_rational_from_wire(obj["kl_radius"], "kl_radius"),
            row_load_rows=_rows_from_wire(obj["row_load_rows"], "row_load_rows", rat),
            nominal_operator_rows=_rows_from_wire(
                obj["nominal_operator_rows"], "nominal_operator_rows", rat
            ),
            exact_rule_column_ids=tuple(
                _exact_string(x, "exact_rule_column_ids")
                for x in _exact_list(obj["exact_rule_column_ids"], "exact_rule_column_ids")
            ),
            exact_rule_rows=_rows_from_wire(obj["exact_rule_rows"], "exact_rule_rows", vector),
        )
        if canonical_contract_bytes(created.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("MaxEntProblem wire does not match recomputed binding")
        return created


def _raise(message: str) -> Any:
    raise StrictContractError(message)


def _rref(matrix: Sequence[Sequence[Fraction]]) -> tuple[list[list[Fraction]], list[int]]:
    rows = [list(row) for row in matrix]
    if not rows:
        return rows, []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise StrictContractError("exact matrix is ragged")
    pivot_cols: list[int] = []
    pivot_row = 0
    for col in range(width):
        found = next((r for r in range(pivot_row, len(rows)) if rows[r][col] != 0), None)
        if found is None:
            continue
        rows[pivot_row], rows[found] = rows[found], rows[pivot_row]
        divisor = rows[pivot_row][col]
        rows[pivot_row] = [_fdiv(x, divisor) for x in rows[pivot_row]]
        for r in range(len(rows)):
            if r == pivot_row or rows[r][col] == 0:
                continue
            factor = rows[r][col]
            rows[r] = [
                _fsub(rows[r][j], _fmul(factor, rows[pivot_row][j]))
                for j in range(width)
            ]
        pivot_cols.append(col)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return rows, pivot_cols


def _rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    if not matrix:
        return 0
    return len(_rref(matrix)[1])


def _solve_unique_columns(
    matrix: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction]
) -> tuple[Fraction, ...] | None:
    if len(matrix) != len(rhs) or not matrix:
        return None
    columns = len(matrix[0])
    if columns == 0 or any(len(row) != columns for row in matrix):
        return None
    augmented = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    reduced, pivots = _rref(augmented)
    for row in reduced:
        if all(x == 0 for x in row[:columns]) and row[columns] != 0:
            return None
    coefficient_pivots = [p for p in pivots if p < columns]
    if len(coefficient_pivots) != columns:
        return None
    result = [Fraction(0) for _ in range(columns)]
    for row_index, pivot in enumerate(pivots):
        if pivot < columns:
            result[pivot] = _cap_fraction(reduced[row_index][columns], "exact solution")
    return tuple(result)


def _null_vector(matrix: Sequence[Sequence[Fraction]], dimension: int) -> tuple[Fraction, ...]:
    if not matrix:
        if dimension != 1:
            raise StrictContractError("empty facet matrix has wrong dimension")
        return (Fraction(1),)
    reduced, pivots = _rref(matrix)
    if len(pivots) != dimension - 1:
        raise StrictContractError("facet does not have codimension one")
    free = next((j for j in range(dimension) if j not in pivots), None)
    if free is None:
        raise StrictContractError("facet normal has no free coordinate")
    result = [Fraction(0) for _ in range(dimension)]
    result[free] = Fraction(1)
    for row_index, pivot in enumerate(pivots):
        result[pivot] = _cap_fraction(-reduced[row_index][free], "facet normal")
    return tuple(result)


def _dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    total = Fraction(0)
    for x, y in zip(a, b, strict=True):
        total = _fadd(total, _fmul(x, y))
    return total


@dataclass(frozen=True)
class MomentGeometry:
    status: MaxEntStatus
    declared_dimension: int
    affine_rank: int
    subset_work_bound: int
    membership_subset_indices: tuple[int, ...]
    membership_weights: tuple[ExactRational, ...]
    supporting_face_indices: tuple[int, ...]
    tier: str = _TIER

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _GEOMETRY_SCHEMA,
            "status": self.status.value,
            "declared_dimension": self.declared_dimension,
            "affine_rank": self.affine_rank,
            "subset_work_bound": self.subset_work_bound,
            "membership_subset_indices": list(self.membership_subset_indices),
            "membership_weights": [x.to_dict() for x in self.membership_weights],
            "supporting_face_indices": list(self.supporting_face_indices),
            "tier": self.tier,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MomentGeometry":
        _bounded_wire_preflight(value, "MomentGeometry wire")
        obj = _exact_dict(
            value,
            {"schema_version", "status", "declared_dimension", "affine_rank",
             "subset_work_bound", "membership_subset_indices", "membership_weights",
             "supporting_face_indices", "tier"},
            "MomentGeometry",
        )
        if obj["schema_version"] != _GEOMETRY_SCHEMA or obj["tier"] != _TIER:
            raise StrictContractError("MomentGeometry fixed fields mismatch")
        try:
            status = MaxEntStatus(obj["status"])
        except (TypeError, ValueError) as exc:
            raise StrictContractError("MomentGeometry status invalid") from exc
        ints: list[tuple[int, ...]] = []
        for name in ("membership_subset_indices", "supporting_face_indices"):
            raw = _exact_list(obj[name], name)
            if (
                any(type(x) is not int or not (0 <= x < _MAX_SUPPORT) for x in raw)
                or len(set(raw)) != len(raw)
                or raw != sorted(raw)
            ):
                raise StrictContractError(
                    f"{name} must be sorted unique capped nonnegative integers"
                )
            ints.append(tuple(raw))
        if any(type(obj[x]) is not int or obj[x] < 0 for x in (
            "declared_dimension", "affine_rank", "subset_work_bound"
        )):
            raise StrictContractError("MomentGeometry integer field invalid")
        weights = tuple(
            _derived_rational_from_wire(x, "membership_weights")
            for x in _exact_list(obj["membership_weights"], "membership_weights")
        )
        dimension = obj["declared_dimension"]
        rank = obj["affine_rank"]
        work = obj["subset_work_bound"]
        if not (1 <= dimension <= _MAX_STATISTIC_DIMENSION):
            raise StrictContractError("MomentGeometry declared dimension exceeds cap")
        if rank > dimension or not (1 <= work <= _MAX_SUBSET_WORK):
            raise StrictContractError("MomentGeometry rank/work bound is impossible")
        if len(ints[0]) > dimension + 1:
            raise StrictContractError("MomentGeometry witness exceeds Caratheodory cap")
        if len(weights) != len(ints[0]):
            raise StrictContractError("MomentGeometry witness shape mismatch")
        weight_sum = Fraction(0)
        for weight in weights:
            if weight.numerator < 0:
                raise StrictContractError("MomentGeometry witness has negative weight")
            weight_sum = _fadd(weight_sum, _fraction(weight))
        has_witness = bool(ints[0])
        has_face = bool(ints[1])
        if has_witness and weight_sum != 1:
            raise StrictContractError("MomentGeometry witness weights do not sum to one")
        valid_shape = {
            MaxEntStatus.SINGULAR_STATISTICS: rank < dimension and not has_witness and not has_face,
            MaxEntStatus.OUTSIDE_HULL: rank == dimension and not has_witness and not has_face,
            MaxEntStatus.BOUNDARY_NO_FINITE_PARAMETER: (
                rank == dimension and has_witness and has_face and len(ints[1]) == dimension
            ),
            MaxEntStatus.INTERIOR_SOLVED: rank == dimension and has_witness and not has_face,
            MaxEntStatus.NUMERIC_FAILURE: False,
        }[status]
        if not valid_shape:
            raise StrictContractError("MomentGeometry status/invariant mismatch")
        result = cls(
            status, dimension, rank, work, ints[0], weights, ints[1]
        )
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("MomentGeometry is not canonical")
        return result


def _classify_exact_points(
    statistics: tuple[tuple[ExactRational, ...], ...],
    target: tuple[ExactRational, ...],
    declared_dimension: int,
) -> MomentGeometry:
    if type(statistics) is not tuple or not (1 <= len(statistics) <= _MAX_SUPPORT):
        raise StrictContractError("statistics must be a nonempty capped tuple")
    if type(target) is not tuple or type(declared_dimension) is not int:
        raise StrictContractError("target/dimension exact types required")
    if declared_dimension != len(target) or not (1 <= declared_dimension <= _MAX_STATISTIC_DIMENSION):
        raise StrictContractError("declared statistic dimension mismatch")
    n, d = len(statistics), declared_dimension
    for i, row in enumerate(statistics):
        if type(row) is not tuple or len(row) != d:
            raise StrictContractError("statistics matrix shape mismatch")
        for j, value in enumerate(row):
            _rational(value, f"statistics[{i}][{j}]")
    for j, value in enumerate(target):
        _rational(value, f"target[{j}]")
    subset_work = sum(math.comb(n, k) for k in range(1, min(n, d + 1) + 1))
    if subset_work > _MAX_SUBSET_WORK:
        raise StrictContractError("exact lazy subset-work cap exceeded")
    points = tuple(tuple(_fraction(x) for x in row) for row in statistics)
    target_f = tuple(_fraction(x) for x in target)
    base = points[0]
    differences = [
        [_fsub(points[i][j], base[j]) for j in range(d)] for i in range(1, n)
    ]
    affine_rank = _rank(differences)
    if affine_rank < d:
        return MomentGeometry(
            MaxEntStatus.SINGULAR_STATISTICS, d, affine_rank, subset_work, (), (), ()
        )
    witness_indices: tuple[int, ...] = ()
    witness_weights: tuple[Fraction, ...] = ()
    for size in range(1, min(n, d + 1) + 1):
        for subset in itertools.combinations(range(n), size):
            matrix = [[points[index][j] for index in subset] for j in range(d)]
            matrix.append([Fraction(1) for _ in subset])
            solution = _solve_unique_columns(matrix, (*target_f, Fraction(1)))
            if solution is not None and all(weight >= 0 for weight in solution):
                witness_indices = tuple(subset)
                witness_weights = solution
                break
        if witness_indices:
            break
    if not witness_indices:
        return MomentGeometry(
            MaxEntStatus.OUTSIDE_HULL, d, affine_rank, subset_work, (), (), ()
        )
    supporting_face: tuple[int, ...] = ()
    for facet in itertools.combinations(range(n), d):
        facet_base = points[facet[0]]
        facet_differences = [
            [_fsub(points[index][j], facet_base[j]) for j in range(d)]
            for index in facet[1:]
        ]
        if _rank(facet_differences) != d - 1:
            continue
        normal = _null_vector(facet_differences, d)
        signs = [
            _dot(normal, [_fsub(point[j], facet_base[j]) for j in range(d)])
            for point in points
        ]
        if not any(sign != 0 for sign in signs):
            continue
        one_side = all(sign >= 0 for sign in signs) or all(sign <= 0 for sign in signs)
        target_sign = _dot(
            normal, [_fsub(target_f[j], facet_base[j]) for j in range(d)]
        )
        if one_side and target_sign == 0:
            supporting_face = tuple(facet)
            break
    status = (
        MaxEntStatus.BOUNDARY_NO_FINITE_PARAMETER
        if supporting_face
        else MaxEntStatus.INTERIOR_SOLVED
    )
    return MomentGeometry(
        status,
        d,
        affine_rank,
        subset_work,
        witness_indices,
        tuple(_as_exact(x) for x in witness_weights),
        supporting_face,
    )


def classify_exact_moment_geometry(problem: MaxEntProblem) -> MomentGeometry:
    if type(problem) is not MaxEntProblem:
        raise StrictContractError("exact geometry classifier requires MaxEntProblem")
    problem = MaxEntProblem.from_dict(problem.to_dict())
    statistics = tuple(row for _, row in problem.statistic_rows)
    return _classify_exact_points(statistics, problem.target, problem.declared_dimension)


@dataclass(frozen=True)
class OrbitReferenceLaw:
    support_candidate_ids: tuple[str, ...]
    probabilities: tuple[ExactRational, ...]
    unnormalized_mass: tuple[ExactRational, ...]
    normalization: ExactRational
    tier: str = _TIER

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _ORBIT_SCHEMA,
            "support_candidate_ids": list(self.support_candidate_ids),
            "probabilities": [x.to_dict() for x in self.probabilities],
            "unnormalized_mass": [x.to_dict() for x in self.unnormalized_mass],
            "normalization": self.normalization.to_dict(),
            "tier": self.tier,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OrbitReferenceLaw":
        _bounded_wire_preflight(value, "OrbitReferenceLaw wire")
        obj = _exact_dict(value, {"schema_version", "support_candidate_ids", "probabilities",
                                  "unnormalized_mass", "normalization", "tier"},
                          "OrbitReferenceLaw")
        raw_ids = _exact_list(obj["support_candidate_ids"], "support_candidate_ids")
        raw_probs = _exact_list(obj["probabilities"], "probabilities")
        raw_masses = _exact_list(obj["unnormalized_mass"], "unnormalized_mass")
        if not (1 <= len(raw_ids) <= _MAX_SUPPORT):
            raise StrictContractError("OrbitReferenceLaw support size exceeds cap")
        if len(raw_probs) != len(raw_ids) or len(raw_masses) != len(raw_ids):
            raise StrictContractError("OrbitReferenceLaw aligned row counts mismatch")
        if any(type(x) is not str or not x for x in raw_ids) or len(set(raw_ids)) != len(raw_ids):
            raise StrictContractError("OrbitReferenceLaw support IDs must be unique strings")
        ids = tuple(raw_ids)
        probs = tuple(_derived_rational_from_wire(x, "probabilities") for x in raw_probs)
        masses = tuple(_derived_rational_from_wire(x, "unnormalized_mass") for x in raw_masses)
        result = cls(
            ids,
            probs,
            masses,
            _derived_rational_from_wire(obj["normalization"], "normalization"),
        )
        if obj["schema_version"] != _ORBIT_SCHEMA or obj["tier"] != _TIER:
            raise StrictContractError("OrbitReferenceLaw fixed fields mismatch")
        if len(ids) != len(probs) or len(ids) != len(masses):
            raise StrictContractError("OrbitReferenceLaw shape/simplex mismatch")
        probability_sum = Fraction(0)
        mass_sum = Fraction(0)
        for probability, mass in zip(probs, masses, strict=True):
            if probability.numerator <= 0 or mass.numerator <= 0:
                raise StrictContractError("orbit reference atoms must be strictly positive")
            probability_sum = _fadd(probability_sum, _fraction(probability))
            mass_sum = _fadd(mass_sum, _fraction(mass))
        normalization = _fraction(result.normalization)
        if probability_sum != 1 or mass_sum != normalization or normalization <= 0:
            raise StrictContractError("OrbitReferenceLaw exact normalization mismatch")
        for probability, mass in zip(probs, masses, strict=True):
            if _fraction(probability) != _fdiv(_fraction(mass), normalization):
                raise StrictContractError("orbit reference probability was not rederived")
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("OrbitReferenceLaw is not canonical")
        return result


def _orbit_reference(problem: MaxEntProblem) -> OrbitReferenceLaw:
    masses: list[Fraction] = []
    for (_, q), (_, orbit) in zip(
        problem.reference_mass_rows, problem.orbit_size_rows, strict=True
    ):
        masses.append(_fdiv(_fraction(q), Fraction(orbit)))
    normalization = Fraction(0)
    for mass in masses:
        normalization = _fadd(normalization, mass)
    if normalization <= 0:
        raise StrictContractError("orbit reference normalization must be positive")
    probabilities = tuple(_fdiv(mass, normalization) for mass in masses)
    return OrbitReferenceLaw(
        problem.support_candidate_ids,
        tuple(_as_exact(x) for x in probabilities),
        tuple(_as_exact(x) for x in masses),
        _as_exact(normalization),
    )


@dataclass(frozen=True)
class OperatorSpanResidual:
    column_ids: tuple[str, ...]
    coefficients: tuple[str, ...]
    residual_l2: str
    tolerance: str
    within_tolerance: bool
    tier: str = _TIER

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _OPERATOR_SCHEMA,
            "column_ids": list(self.column_ids),
            "coefficients": list(self.coefficients),
            "residual_l2": self.residual_l2,
            "tolerance": self.tolerance,
            "within_tolerance": self.within_tolerance,
            "tier": self.tier,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OperatorSpanResidual":
        _bounded_wire_preflight(value, "OperatorSpanResidual wire")
        obj = _exact_dict(value, {"schema_version", "column_ids", "coefficients",
                                  "residual_l2", "tolerance", "within_tolerance", "tier"},
                          "OperatorSpanResidual")
        raw_ids = _exact_list(obj["column_ids"], "column_ids")
        raw_coeffs = _exact_list(obj["coefficients"], "coefficients")
        if len(raw_ids) > _MAX_RULE_COLUMNS or len(raw_coeffs) != len(raw_ids):
            raise StrictContractError("operator span column/coordinate count mismatch")
        if any(type(x) is not str or not x for x in raw_ids) or len(set(raw_ids)) != len(raw_ids):
            raise StrictContractError("operator span column IDs must be unique strings")
        ids = tuple(raw_ids)
        coeffs = tuple(
            _float_text(_float_from_wire(x, "coefficients"), "coefficients")
            for x in raw_coeffs
        )
        residual = _float_text(_float_from_wire(obj["residual_l2"], "residual_l2"), "residual_l2")
        tolerance = _float_text(_float_from_wire(obj["tolerance"], "tolerance"), "tolerance")
        if float(residual) < 0.0 or float(tolerance) < 0.0:
            raise StrictContractError("operator residual/tolerance must be nonnegative")
        if tolerance != _float_text(float(_OPERATOR_TOL), "operator tolerance"):
            raise StrictContractError("operator tolerance differs from frozen ME0 value")
        if type(obj["within_tolerance"]) is not bool:
            raise StrictContractError("within_tolerance must be boolean")
        result = cls(ids, coeffs, residual, tolerance, obj["within_tolerance"])
        if obj["schema_version"] != _OPERATOR_SCHEMA or obj["tier"] != _TIER:
            raise StrictContractError("OperatorSpanResidual fixed fields mismatch")
        if len(ids) != len(coeffs):
            raise StrictContractError("operator coefficient order mismatch")
        if (float(residual) <= float(tolerance)) != result.within_tolerance:
            raise StrictContractError("operator tolerance disposition mismatch")
        if canonical_contract_bytes(result.to_dict()) != canonical_contract_bytes(obj):
            raise StrictContractError("OperatorSpanResidual is not canonical")
        return result


@dataclass(frozen=True)
class MaxEntResult:
    status: MaxEntStatus
    support_reference: DeclaredE2SupportReference
    problem_sha256: str
    row_table_sha256: str
    geometry: MomentGeometry
    orbit_reference: OrbitReferenceLaw
    probabilities: tuple[str, ...]
    dual_parameter: tuple[str, ...]
    log_partition: str | None
    simplex_error: str | None
    moment_residual_inf: str | None
    dual_residual_inf: str | None
    kl_divergence: str | None
    kl_radius: ExactRational
    kl_within_radius: bool
    expected_row_load: str | None
    orbit_expected_row_load: str | None
    pinsker_rhs: str | None
    operator_span: OperatorSpanResidual | None
    selected_candidate_id: str
    fallback_used: bool
    tier: str = _TIER

    def to_dict(self) -> dict[str, Any]:
        orbit_probabilities = tuple(
            _float_text(float(_fraction(value)), "orbit reference probability")
            for value in self.orbit_reference.probabilities
        )
        return {
            "schema_version": _RESULT_SCHEMA,
            **_authority_wire(),
            "runtime_manifest_sha256": ME0_WINDOWS_RUNTIME_MANIFEST_SHA256,
            "status": self.status.value,
            "support_reference": self.support_reference.to_dict(),
            "problem_sha256": self.problem_sha256,
            "row_table_sha256": self.row_table_sha256,
            "geometry": self.geometry.to_dict(),
            "orbit_reference": self.orbit_reference.to_dict(),
            "orbit_reference_probabilities": list(orbit_probabilities),
            "support_candidate_ids": list(self.support_reference.support_candidate_ids),
            "certified_support_token_sha256": (
                self.support_reference.certified_support_token_sha256
            ),
            "probabilities": list(self.probabilities),
            "dual_parameter": list(self.dual_parameter),
            "log_partition": self.log_partition,
            "simplex_error": self.simplex_error,
            "simplex_residual": self.simplex_error,
            "moment_residual_inf": self.moment_residual_inf,
            "dual_residual_inf": self.dual_residual_inf,
            "kl_divergence": self.kl_divergence,
            "kl_radius": self.kl_radius.to_dict(),
            "kl_within_radius": self.kl_within_radius,
            "expected_row_load": self.expected_row_load,
            "fitted_expected_load": self.expected_row_load,
            "orbit_expected_row_load": self.orbit_expected_row_load,
            "reference_expected_load": self.orbit_expected_row_load,
            "pinsker_rhs": self.pinsker_rhs,
            "pinsker_upper": self.pinsker_rhs,
            "operator_span": None if self.operator_span is None else self.operator_span.to_dict(),
            "operator_span_residual": (
                None if self.operator_span is None else self.operator_span.residual_l2
            ),
            "operator_tier": self.tier,
            "selected_candidate_id": self.selected_candidate_id,
            "fallback_candidate_id": (
                self.selected_candidate_id if self.fallback_used else None
            ),
            "fallback_used": self.fallback_used,
            "verification_disposition": (
                "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
                if self.status is MaxEntStatus.INTERIOR_SOLVED
                else "ME0_NON_SUCCESS_FALLBACK_RETAINED"
            ),
            "tier": self.tier,
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], *, problem: MaxEntProblem
    ) -> "MaxEntResult":
        return _parse_maxent_result_wire(problem, value)


_RESULT_FIELDS = {
    "schema_version",
    *_AUTHORITY_FIELDS,
    "runtime_manifest_sha256",
    "status",
    "support_reference",
    "problem_sha256",
    "row_table_sha256",
    "geometry",
    "orbit_reference",
    "orbit_reference_probabilities",
    "support_candidate_ids",
    "certified_support_token_sha256",
    "probabilities",
    "dual_parameter",
    "log_partition",
    "simplex_error",
    "simplex_residual",
    "moment_residual_inf",
    "dual_residual_inf",
    "kl_divergence",
    "kl_radius",
    "kl_within_radius",
    "expected_row_load",
    "fitted_expected_load",
    "orbit_expected_row_load",
    "reference_expected_load",
    "pinsker_rhs",
    "pinsker_upper",
    "operator_span",
    "operator_span_residual",
    "operator_tier",
    "selected_candidate_id",
    "fallback_candidate_id",
    "fallback_used",
    "verification_disposition",
    "tier",
}


def _fallback_result(
    problem: MaxEntProblem,
    geometry: MomentGeometry,
    orbit: OrbitReferenceLaw,
    status: MaxEntStatus,
) -> MaxEntResult:
    q_load_exact = Fraction(0)
    for probability, (_, load) in zip(
        orbit.probabilities, problem.row_load_rows, strict=True
    ):
        q_load_exact = _fadd(
            q_load_exact, _fmul(_fraction(probability), _fraction(load))
        )
    try:
        q_load_float = float(q_load_exact)
        q_load_wire = (
            _float_text(q_load_float, "orbit expected load")
            if math.isfinite(q_load_float)
            else None
        )
    except (OverflowError, StrictContractError):
        q_load_wire = None
    return MaxEntResult(
        status=status,
        support_reference=problem.support_reference,
        problem_sha256=problem.problem_sha256,
        row_table_sha256=problem.row_table_sha256,
        geometry=geometry,
        orbit_reference=orbit,
        probabilities=(),
        dual_parameter=(),
        log_partition=None,
        simplex_error=None,
        moment_residual_inf=None,
        dual_residual_inf=None,
        kl_divergence=None,
        kl_radius=problem.kl_radius,
        kl_within_radius=False,
        expected_row_load=None,
        orbit_expected_row_load=q_load_wire,
        pinsker_rhs=None,
        operator_span=None,
        selected_candidate_id=min(problem.support_candidate_ids),
        fallback_used=True,
    )


def _same_exact_wire(left: Any, right: Any) -> bool:
    return canonical_contract_bytes(left) == canonical_contract_bytes(right)


def _required_wire_float(obj: Mapping[str, Any], name: str) -> float:
    return _float_from_wire(obj[name], name)


def _wire_float_vector(
    obj: Mapping[str, Any], name: str, expected_length: int
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    raw = _exact_list(obj[name], name)
    if len(raw) != expected_length:
        raise StrictContractError(f"{name} length disagrees with frozen shape")
    values = tuple(_float_from_wire(value, name) for value in raw)
    return tuple(raw), values  # every raw entry was proved to be an exact string


def _scaled_close(left: float, right: float, tolerance: float) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def _parse_maxent_result_wire(
    problem: MaxEntProblem, value: Mapping[str, Any]
) -> MaxEntResult:
    """Verify a result semantically without requiring identical LAPACK bits."""

    if type(problem) is not MaxEntProblem:
        raise StrictContractError("MaxEntResult parsing requires exact MaxEntProblem")
    _bounded_wire_preflight(value, "MaxEntResult wire")
    checked_problem = MaxEntProblem.from_dict(problem.to_dict())
    obj = _exact_dict(value, _RESULT_FIELDS, "MaxEntResult")
    _check_authority_wire(obj, "MaxEntResult")
    if (
        obj["schema_version"] != _RESULT_SCHEMA
        or obj["runtime_manifest_sha256"] != ME0_WINDOWS_RUNTIME_MANIFEST_SHA256
        or obj["tier"] != _TIER
        or obj["operator_tier"] != _TIER
    ):
        raise StrictContractError("MaxEntResult fixed schema/tier/runtime fields mismatch")
    try:
        status = MaxEntStatus(obj["status"])
    except (TypeError, ValueError) as exc:
        raise StrictContractError("MaxEntResult status is invalid") from exc
    expected_disposition = (
        "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
        if status is MaxEntStatus.INTERIOR_SOLVED
        else "ME0_NON_SUCCESS_FALLBACK_RETAINED"
    )
    if obj["verification_disposition"] != expected_disposition:
        raise StrictContractError("MaxEntResult success disposition contradicts status")

    reference = DeclaredE2SupportReference.from_dict(obj["support_reference"])
    if not _same_exact_wire(
        reference.to_dict(), checked_problem.support_reference.to_dict()
    ):
        raise StrictContractError("MaxEntResult support reference changed")
    if (
        obj["problem_sha256"] != checked_problem.problem_sha256
        or obj["row_table_sha256"] != checked_problem.row_table_sha256
        or obj["support_candidate_ids"] != list(checked_problem.support_candidate_ids)
        or obj["certified_support_token_sha256"]
        != checked_problem.support_reference.certified_support_token_sha256
    ):
        raise StrictContractError("MaxEntResult problem/support binding mismatch")
    _require_sha256(obj["problem_sha256"], "result problem SHA")
    _require_sha256(obj["row_table_sha256"], "result row-table SHA")

    geometry = MomentGeometry.from_dict(obj["geometry"])
    expected_geometry = classify_exact_moment_geometry(checked_problem)
    if not _same_exact_wire(geometry.to_dict(), expected_geometry.to_dict()):
        raise StrictContractError("MaxEntResult exact geometry changed")
    orbit = OrbitReferenceLaw.from_dict(obj["orbit_reference"])
    expected_orbit = _orbit_reference(checked_problem)
    if not _same_exact_wire(orbit.to_dict(), expected_orbit.to_dict()):
        raise StrictContractError("MaxEntResult orbit reference changed")
    expected_orbit_float = [
        _float_text(float(_fraction(item)), "orbit reference probability")
        for item in orbit.probabilities
    ]
    raw_orbit_float = _exact_list(
        obj["orbit_reference_probabilities"], "orbit_reference_probabilities"
    )
    if raw_orbit_float != expected_orbit_float:
        raise StrictContractError("MaxEntResult orbit float view changed")
    for item in raw_orbit_float:
        _float_from_wire(item, "orbit_reference_probabilities")

    kl_radius = _rational_from_wire(obj["kl_radius"], "result kl_radius")
    if kl_radius != checked_problem.kl_radius:
        raise StrictContractError("MaxEntResult KL radius changed")
    if type(obj["kl_within_radius"]) is not bool:
        raise StrictContractError("kl_within_radius must be boolean")
    if type(obj["fallback_used"]) is not bool:
        raise StrictContractError("fallback_used must be boolean")
    selected = _exact_string(obj["selected_candidate_id"], "selected_candidate_id")
    if selected not in checked_problem.support_candidate_ids:
        raise StrictContractError("selected candidate lies outside certified support")
    fallback_candidate = obj["fallback_candidate_id"]
    if fallback_candidate is not None and type(fallback_candidate) is not str:
        raise StrictContractError("fallback_candidate_id must be null or exact string")

    # Exact non-success fallbacks contain no LAPACK-dependent values, so their
    # complete wire remains byte-comparable and conservatively verifiable.
    if status is not MaxEntStatus.INTERIOR_SOLVED:
        if status is MaxEntStatus.NUMERIC_FAILURE:
            if geometry.status is not MaxEntStatus.INTERIOR_SOLVED:
                raise StrictContractError("numeric failure must retain interior geometry")
        elif geometry.status is not status:
            raise StrictContractError("noninterior result status changed")
        expected_fallback = _fallback_result(
            checked_problem, geometry, orbit, status
        )
        if not _same_exact_wire(obj, expected_fallback.to_dict()):
            raise StrictContractError("non-success MaxEnt fallback wire changed")
        return expected_fallback

    if geometry.status is not MaxEntStatus.INTERIOR_SOLVED:
        raise StrictContractError("only strict-interior geometry can carry a solved law")
    n = len(checked_problem.support_candidate_ids)
    d = checked_problem.declared_dimension
    probability_text, probability_values = _wire_float_vector(
        obj, "probabilities", n
    )
    dual_text, dual_values = _wire_float_vector(obj, "dual_parameter", d)
    if any(item <= 0.0 for item in probability_values):
        raise StrictContractError("solved MaxEnt probabilities must be strictly positive")
    required_names = (
        "log_partition",
        "simplex_error",
        "moment_residual_inf",
        "dual_residual_inf",
        "kl_divergence",
        "expected_row_load",
        "orbit_expected_row_load",
    )
    if any(obj[name] is None for name in required_names):
        raise StrictContractError("solved MaxEnt result omits a numeric diagnostic")
    log_partition = _required_wire_float(obj, "log_partition")
    simplex_error = _required_wire_float(obj, "simplex_error")
    moment_residual = _required_wire_float(obj, "moment_residual_inf")
    dual_residual = _required_wire_float(obj, "dual_residual_inf")
    kl_reported = _required_wire_float(obj, "kl_divergence")
    expected_load_reported = _required_wire_float(obj, "expected_row_load")
    orbit_load_reported = _required_wire_float(obj, "orbit_expected_row_load")
    if (
        obj["simplex_residual"] != obj["simplex_error"]
        or obj["fitted_expected_load"] != obj["expected_row_load"]
        or obj["reference_expected_load"] != obj["orbit_expected_row_load"]
        or obj["pinsker_upper"] != obj["pinsker_rhs"]
    ):
        raise StrictContractError("MaxEntResult duplicate diagnostic views disagree")
    for name in ("simplex_residual", "fitted_expected_load", "reference_expected_load"):
        _required_wire_float(obj, name)
    if simplex_error < 0.0 or moment_residual < 0.0 or dual_residual < 0.0 or kl_reported < 0.0:
        raise StrictContractError("MaxEntResult residual/KL diagnostics must be nonnegative")
    if type(obj["operator_span"]) is not dict:
        raise StrictContractError("solved MaxEnt result requires operator-span diagnostic")
    operator = OperatorSpanResidual.from_dict(obj["operator_span"])
    if (
        operator.column_ids != checked_problem.exact_rule_column_ids
        or obj["operator_span_residual"] != operator.residual_l2
    ):
        raise StrictContractError("operator-span diagnostic changed column/order view")

    # Only exact-interior result verification reaches NumPy.  Values from the
    # wire are checked against equations and frozen tolerances, never against
    # a byte-identical rerun of Newton or LAPACK.
    import numpy as np

    p = np.asarray(probability_values, dtype=np.float64)
    lam = np.asarray(dual_values, dtype=np.float64)
    phi = np.asarray(
        [[float(_fraction(item)) for item in row] for _, row in checked_problem.statistic_rows],
        dtype=np.float64,
    )
    target = np.asarray(
        [float(_fraction(item)) for item in checked_problem.target], dtype=np.float64
    )
    q = np.asarray(
        [float(_fraction(item)) for item in orbit.probabilities], dtype=np.float64
    )
    loads = np.asarray(
        [float(_fraction(item)) for _, item in checked_problem.row_load_rows],
        dtype=np.float64,
    )
    g = np.asarray(
        [[float(_fraction(item)) for item in row] for _, row in checked_problem.exact_rule_rows],
        dtype=np.float64,
    )
    k = np.asarray(
        [float(_fraction(item)) for _, item in checked_problem.nominal_operator_rows],
        dtype=np.float64,
    )
    beta = np.asarray([float(item) for item in operator.coefficients], dtype=np.float64)
    if not all(
        np.all(np.isfinite(array))
        for array in (p, lam, phi, target, q, loads, g, k, beta)
    ):
        raise StrictContractError("MaxEntResult semantic arrays contain nonfinite values")
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        logits = np.log(q) + phi @ lam
        if not np.all(np.isfinite(logits)):
            raise StrictContractError("MaxEntResult dual law has nonfinite logits")
        maximum = float(np.max(logits))
        exponentials = np.exp(logits - maximum)
        if np.any(exponentials == 0.0) or not np.all(np.isfinite(exponentials)):
            raise StrictContractError("MaxEntResult dual law underflowed an atom")
        fitted = exponentials / float(np.sum(exponentials))
        recomputed_log_partition = maximum + math.log(float(np.sum(exponentials)))
        moment = p @ phi
        simplex_actual = abs(float(np.sum(p)) - 1.0)
        moment_actual = float(np.max(np.abs(moment - target)))
        law_actual = float(np.max(np.abs(p - fitted)))
        kl_actual = float(np.sum(p * (np.log(p) - np.log(q))))
        fitted_load = float(p @ loads)
        orbit_load = float(q @ loads)
    if not all(
        math.isfinite(item)
        for item in (
            recomputed_log_partition,
            simplex_actual,
            moment_actual,
            law_actual,
            kl_actual,
            fitted_load,
            orbit_load,
        )
    ):
        raise StrictContractError("MaxEntResult semantic diagnostics are nonfinite")
    if (
        simplex_actual > _SIMPLEX_TOL
        or simplex_error > _SIMPLEX_TOL
        or abs(simplex_actual - simplex_error) > _SIMPLEX_TOL
        or moment_actual > _MOMENT_TOL
        or moment_residual > _MOMENT_TOL
        or abs(moment_actual - moment_residual) > _MOMENT_TOL
        or dual_residual > _DUAL_TOL
        or abs(moment_actual - dual_residual) > _DUAL_TOL
        or law_actual > _MOMENT_TOL
        or not _scaled_close(log_partition, recomputed_log_partition, _MOMENT_TOL)
    ):
        raise StrictContractError("MaxEntResult violates simplex/moment/dual-law tolerances")
    if kl_actual < -_MOMENT_TOL:
        raise StrictContractError("MaxEntResult recomputed KL is negative")
    kl_actual = max(0.0, kl_actual)
    if abs(kl_actual - kl_reported) > _MOMENT_TOL:
        raise StrictContractError("MaxEntResult KL diagnostic is not equation-consistent")
    eta = float(_fraction(checked_problem.kl_radius))
    kl_within = kl_reported <= eta and kl_actual <= eta
    if obj["kl_within_radius"] is not kl_within:
        raise StrictContractError("MaxEntResult KL-radius disposition is false")
    if not _scaled_close(expected_load_reported, fitted_load, _MOMENT_TOL):
        raise StrictContractError("MaxEntResult fitted load is inconsistent")
    if not _scaled_close(orbit_load_reported, orbit_load, _MOMENT_TOL):
        raise StrictContractError("MaxEntResult orbit load is inconsistent")
    pinsker_value: float | None
    if kl_within:
        if obj["pinsker_rhs"] is None:
            raise StrictContractError("KL-admissible result omitted Pinsker diagnostic")
        pinsker_value = _required_wire_float(obj, "pinsker_rhs")
        pinsker_expected = orbit_load + float(np.max(loads) - np.min(loads)) * math.sqrt(eta / 2.0)
        if (
            not _scaled_close(pinsker_value, pinsker_expected, _MOMENT_TOL)
            or fitted_load > pinsker_value + _MOMENT_TOL
        ):
            raise StrictContractError("MaxEntResult Pinsker diagnostic is invalid")
    else:
        if obj["pinsker_rhs"] is not None:
            raise StrictContractError("KL-outside result must make Pinsker unavailable")
        pinsker_value = None

    fallback_used = not kl_within
    expected_selected = (
        min(checked_problem.support_candidate_ids)
        if fallback_used
        else min(
            checked_problem.support_candidate_ids,
            key=lambda candidate_id: (
                -probability_values[
                    checked_problem.support_candidate_ids.index(candidate_id)
                ],
                candidate_id,
            ),
        )
    )
    if (
        obj["fallback_used"] is not fallback_used
        or selected != expected_selected
        or fallback_candidate != (expected_selected if fallback_used else None)
    ):
        raise StrictContractError("MaxEntResult within-support selection/fallback changed")

    try:
        if g.shape[1] == 0:
            supplied_operator_residual = float(np.linalg.norm(k, ord=2))
            optimal_operator_residual = supplied_operator_residual
        else:
            supplied_operator_residual = float(np.linalg.norm(k - g @ beta, ord=2))
            optimum_beta = np.linalg.pinv(g, rcond=_RCOND) @ k
            optimal_operator_residual = float(
                np.linalg.norm(k - g @ optimum_beta, ord=2)
            )
    except Exception as exc:
        raise StrictContractError("operator-span semantic verification failed") from exc
    operator_reported = float(operator.residual_l2)
    if (
        not math.isfinite(supplied_operator_residual)
        or not math.isfinite(optimal_operator_residual)
        or abs(supplied_operator_residual - operator_reported) > _OPERATOR_TOL
        or supplied_operator_residual > optimal_operator_residual + _OPERATOR_TOL
        or operator.within_tolerance
        is not (supplied_operator_residual <= _OPERATOR_TOL)
    ):
        raise StrictContractError("operator-span residual is not a tolerant minimum")

    result = MaxEntResult(
        status=status,
        support_reference=reference,
        problem_sha256=checked_problem.problem_sha256,
        row_table_sha256=checked_problem.row_table_sha256,
        geometry=geometry,
        orbit_reference=orbit,
        probabilities=probability_text,
        dual_parameter=dual_text,
        log_partition=obj["log_partition"],
        simplex_error=obj["simplex_error"],
        moment_residual_inf=obj["moment_residual_inf"],
        dual_residual_inf=obj["dual_residual_inf"],
        kl_divergence=obj["kl_divergence"],
        kl_radius=kl_radius,
        kl_within_radius=kl_within,
        expected_row_load=obj["expected_row_load"],
        orbit_expected_row_load=obj["orbit_expected_row_load"],
        pinsker_rhs=obj["pinsker_rhs"],
        operator_span=operator,
        selected_candidate_id=selected,
        fallback_used=fallback_used,
        tier=_TIER,
    )
    if result.to_dict() != obj:
        raise StrictContractError("MaxEntResult wire aliases are not canonical")
    return result


def _numeric_solution(problem: MaxEntProblem, max_iterations: int) -> MaxEntResult:
    geometry = classify_exact_moment_geometry(problem)
    orbit = _orbit_reference(problem)
    if geometry.status is not MaxEntStatus.INTERIOR_SOLVED:
        return _fallback_result(problem, geometry, orbit, geometry.status)
    if type(max_iterations) is not int or max_iterations < 0 or max_iterations > _MAX_ITERATIONS:
        raise StrictContractError("private iteration bound is outside registered range")
    if max_iterations == 0:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    # Import only after all exact shape/cap/geometry gates have passed.
    import numpy as np

    phi = np.asarray(
        [[float(_fraction(x)) for x in row] for _, row in problem.statistic_rows],
        dtype=np.float64,
    )
    target = np.asarray([float(_fraction(x)) for x in problem.target], dtype=np.float64)
    q = np.asarray([float(_fraction(x)) for x in orbit.probabilities], dtype=np.float64)
    if not (
        np.all(np.isfinite(phi))
        and np.all(np.isfinite(target))
        and np.all(np.isfinite(q))
        and np.all(q > 0.0)
    ):
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    lam = np.zeros(problem.declared_dimension, dtype=np.float64)

    def evaluate(parameter: Any) -> tuple[Any, float, Any, Any, float] | None:
        with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
            logits = np.log(q) + phi @ parameter
            if not np.all(np.isfinite(logits)):
                return None
            maximum = float(np.max(logits))
            shifted = np.exp(logits - maximum)
        if not np.all(np.isfinite(shifted)) or np.any(shifted == 0.0):
            return None
        normalizer = float(np.sum(shifted))
        if not math.isfinite(normalizer) or normalizer <= 0.0:
            return None
        with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
            probabilities = shifted / normalizer
            log_partition = maximum + math.log(normalizer)
            moment = probabilities @ phi
            residual = target - moment
            centered = phi - moment
            hessian = (centered.T * probabilities) @ centered
            dual = log_partition - float(parameter @ target)
        if not (
            np.all(np.isfinite(probabilities)) and np.all(probabilities > 0.0)
            and math.isfinite(log_partition) and np.all(np.isfinite(moment))
            and np.all(np.isfinite(residual)) and np.all(np.isfinite(hessian))
            and math.isfinite(dual)
        ):
            return None
        return probabilities, log_partition, residual, hessian, dual

    state = evaluate(lam)
    if state is None:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    solved = False
    for _ in range(max_iterations):
        probabilities, log_partition, residual, hessian, dual = state
        residual_inf = float(np.max(np.abs(residual)))
        if residual_inf <= _MOMENT_TOL and residual_inf <= _DUAL_TOL:
            solved = True
            break
        try:
            step = np.linalg.pinv(hessian, rcond=_RCOND) @ residual
        except Exception:
            return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
        if not np.all(np.isfinite(step)):
            return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
        accepted = False
        scale = 1.0
        for _backtrack in range(_MAX_BACKTRACKS):
            candidate = lam + scale * step
            trial = evaluate(candidate)
            if trial is not None:
                trial_residual = float(np.max(np.abs(trial[2])))
                if trial[4] <= dual + 1e-15 or trial_residual < residual_inf:
                    lam, state, accepted = candidate, trial, True
                    break
            scale *= 0.5
        if not accepted:
            return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    if not solved:
        probabilities, log_partition, residual, hessian, dual = state
        residual_inf = float(np.max(np.abs(residual)))
        solved = residual_inf <= _MOMENT_TOL and residual_inf <= _DUAL_TOL
    if not solved:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)

    probabilities, log_partition, residual, _hessian, _dual = state
    simplex_error = abs(float(np.sum(probabilities)) - 1.0)
    moment_residual = float(np.max(np.abs(residual)))
    dual_residual = moment_residual
    if simplex_error > _SIMPLEX_TOL or dual_residual > _DUAL_TOL:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    kl = float(np.sum(probabilities * (np.log(probabilities) - np.log(q))))
    if not math.isfinite(kl) or kl < -1e-12:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    kl = max(0.0, kl)
    eta = float(_fraction(problem.kl_radius))
    kl_within = kl <= eta
    loads = np.asarray([float(_fraction(x)) for _, x in problem.row_load_rows], dtype=np.float64)
    expected_load = float(probabilities @ loads)
    q_load = float(q @ loads)
    pinsker = q_load + float(np.max(loads) - np.min(loads)) * math.sqrt(eta / 2.0)
    g = np.asarray(
        [[float(_fraction(x)) for x in row] for _, row in problem.exact_rule_rows],
        dtype=np.float64,
    )
    k = np.asarray(
        [float(_fraction(x)) for _, x in problem.nominal_operator_rows], dtype=np.float64
    )
    if not (np.all(np.isfinite(g)) and np.all(np.isfinite(k))):
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    try:
        if g.shape[1] == 0:
            coefficients = np.empty((0,), dtype=np.float64)
            operator_residual = float(np.linalg.norm(k, ord=2))
        else:
            coefficients = np.linalg.pinv(g, rcond=_RCOND) @ k
            operator_residual = float(np.linalg.norm(k - g @ coefficients, ord=2))
    except Exception:
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    if not (
        np.all(np.isfinite(loads)) and math.isfinite(expected_load)
        and math.isfinite(q_load) and math.isfinite(pinsker)
        and np.all(np.isfinite(coefficients)) and math.isfinite(operator_residual)
    ):
        return _fallback_result(problem, geometry, orbit, MaxEntStatus.NUMERIC_FAILURE)
    operator = OperatorSpanResidual(
        problem.exact_rule_column_ids,
        tuple(_float_text(float(x), "operator coefficient") for x in coefficients),
        _float_text(operator_residual, "operator residual"),
        _float_text(float(_OPERATOR_TOL), "operator tolerance"),
        operator_residual <= _OPERATOR_TOL,
    )
    fallback = not kl_within
    if fallback:
        selected = min(problem.support_candidate_ids)
    else:
        selected = min(
            problem.support_candidate_ids,
            key=lambda candidate_id: (
                -float(probabilities[problem.support_candidate_ids.index(candidate_id)]),
                candidate_id,
            ),
        )
    return MaxEntResult(
        status=MaxEntStatus.INTERIOR_SOLVED,
        support_reference=problem.support_reference,
        problem_sha256=problem.problem_sha256,
        row_table_sha256=problem.row_table_sha256,
        geometry=geometry,
        orbit_reference=orbit,
        probabilities=tuple(_float_text(float(x), "probability") for x in probabilities),
        dual_parameter=tuple(_float_text(float(x), "dual parameter") for x in lam),
        log_partition=_float_text(float(log_partition), "log partition"),
        simplex_error=_float_text(float(simplex_error), "simplex error"),
        moment_residual_inf=_float_text(float(moment_residual), "moment residual"),
        dual_residual_inf=_float_text(float(dual_residual), "dual residual"),
        kl_divergence=_float_text(float(kl), "KL divergence"),
        kl_radius=problem.kl_radius,
        kl_within_radius=kl_within,
        expected_row_load=_float_text(expected_load, "expected row load"),
        orbit_expected_row_load=_float_text(q_load, "orbit expected row load"),
        pinsker_rhs=_float_text(pinsker, "Pinsker RHS") if kl_within else None,
        operator_span=operator,
        selected_candidate_id=selected,
        fallback_used=fallback,
    )


def _solve_finite_fiber_maxent(
    problem: MaxEntProblem, *, max_iterations: int
) -> MaxEntResult:
    if type(problem) is not MaxEntProblem:
        raise StrictContractError("solver requires exact MaxEntProblem")
    problem = MaxEntProblem.from_dict(problem.to_dict())
    return _numeric_solution(problem, max_iterations)


def solve_finite_fiber_maxent(problem: MaxEntProblem) -> MaxEntResult:
    return _solve_finite_fiber_maxent(problem, max_iterations=_MAX_ITERATIONS)


def verify_maxent_result(problem: MaxEntProblem, result: MaxEntResult) -> MaxEntResult:
    if type(problem) is not MaxEntProblem or type(result) is not MaxEntResult:
        raise StrictContractError("ME0 verifier requires exact problem/result types")
    _parse_maxent_result_wire(problem, result.to_dict())
    return result


__all__ = [
    "MaxEntStatus",
    "DeclaredE2SupportReference",
    "MaxEntProblem",
    "MomentGeometry",
    "OrbitReferenceLaw",
    "OperatorSpanResidual",
    "MaxEntResult",
    "bind_e2_support",
    "make_declared_e2_support_reference",
    "classify_exact_moment_geometry",
    "solve_finite_fiber_maxent",
    "verify_maxent_result",
]
