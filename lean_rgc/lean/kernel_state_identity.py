from __future__ import annotations

"""Path-invariant U05 identity for the legacy kernel-state v3 graph.

The native worker necessarily uses process-local ``MVarId``/``FVarId`` names
and graph labels.  Those labels are transport handles, not state semantics.
This module follows the reachable ordered graph from the open goals, assigns
first-occurrence ordinals, and emits a strict canonical JSON signature.  A
SHA-256 digest is provided only as an index: equality always compares the full
canonical bytes after the digest matches.

This is deliberately separate from :mod:`lean_rgc.lean.kernel_state`.  The
latter is a legacy observation/chart adapter and its normalized hash is not an
identity key for the U05 program.
"""

from collections import Counter, deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import re
from typing import Any, Callable, Mapping, Sequence


LEGACY_KERNEL_STATE_SCHEMA_VERSION = "lean-rgc-kernel-state-v3"
STATE_IDENTITY_SCHEMA = "u05-state-identity-v1"


class StrictIdentityError(ValueError):
    """A state cannot be admitted to the strict U05 identity domain."""


def _reject_float(_text: str) -> None:
    raise StrictIdentityError("floating-point JSON is outside the U05 contract")


def _reject_constant(_text: str) -> None:
    raise StrictIdentityError("non-finite JSON is outside the U05 contract")


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictIdentityError(f"duplicate JSON field: {key}")
        out[key] = value
    return out


def _validate_json(value: Any, *, depth: int = 0) -> None:
    if depth > 128:
        raise StrictIdentityError("JSON nesting depth exceeded")
    if value is None or type(value) in (bool, int, str):
        if type(value) is int and not (-(2**63) <= value < 2**63):
            raise StrictIdentityError("integer is outside signed 64-bit range")
        if type(value) is str:
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise StrictIdentityError("string is not strict UTF-8") from exc
        return
    if type(value) is list:
        for item in value:
            _validate_json(item, depth=depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise StrictIdentityError("JSON object key is not a string")
            _validate_json(key, depth=depth + 1)
            _validate_json(item, depth=depth + 1)
        return
    raise StrictIdentityError(
        f"value is outside the strict JSON algebra: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes without a trailing newline."""

    _validate_json(value)
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise StrictIdentityError("strict canonical JSON serialization failed") from exc


def parse_canonical_json_bytes(raw: bytes) -> Any:
    """Parse canonical U05 JSON and reject every noncanonical byte form."""

    if type(raw) is not bytes:
        raise StrictIdentityError("canonical JSON input must be bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictIdentityError("UTF-8 BOM is forbidden")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_from_pairs,
            parse_float=_reject_float,
            parse_int=int,
            parse_constant=_reject_constant,
        )
        _validate_json(value)
    except StrictIdentityError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise StrictIdentityError("strict canonical JSON parse failed") from exc
    if canonical_json_bytes(value) != raw:
        raise StrictIdentityError("JSON bytes are not canonical")
    return value


def _sha256_upper(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


_HEX64_RE = re.compile(r"[0-9A-Fa-f]{64}\Z")


def _digest(value: str, field_name: str) -> str:
    if type(value) is not str or _HEX64_RE.fullmatch(value) is None:
        raise StrictIdentityError(f"{field_name} must be a full SHA-256 hex digest")
    return value.upper()


def _mapping(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictIdentityError(f"{where} must be an object")
    return value


def _array(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictIdentityError(f"{where} must be an array")
    return value


def _string(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise StrictIdentityError(f"{where} must be a string")
    return value


def _boolean(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictIdentityError(f"{where} must be a boolean")
    return value


def _expect_fields(
    value: Mapping[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    where: str,
) -> None:
    actual = set(value)
    missing = required - actual
    unknown = actual - allowed
    if missing:
        raise StrictIdentityError(f"{where} missing fields: {sorted(missing)}")
    if unknown:
        raise StrictIdentityError(f"{where} has unknown fields: {sorted(unknown)}")


def _integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise StrictIdentityError(f"{where} must be an integer >= {minimum}")
    return value


def _strict_string_array(value: Any, where: str) -> list[str]:
    return [_string(item, where) for item in _array(value, where)]


def _strict_unique_string_array(value: Any, where: str) -> list[str]:
    rows = _strict_string_array(value, where)
    if len(rows) != len(set(rows)):
        raise StrictIdentityError(f"{where} contains duplicate canonical references")
    return rows


def _strict_sorted_reference_array(
    value: Any, where: str, *, prefix: str
) -> list[str]:
    rows = _strict_unique_string_array(value, where)

    def ordinal(label: str) -> int:
        suffix = label.removeprefix(prefix) if label.startswith(prefix) else ""
        if not suffix.isdecimal():
            raise StrictIdentityError(
                f"{where} has a noncanonical reference label"
            )
        return int(suffix)

    expected = sorted(rows, key=ordinal)
    if rows != expected:
        raise StrictIdentityError(f"{where} is not in canonical reference order")
    return rows


def _validate_state_signature(obj: Mapping[str, Any]) -> None:
    status = _string(obj["status"], "state identity status")
    if status not in {"open", "closed"}:
        raise StrictIdentityError("state identity status must be open or closed")
    options = _mapping(obj["baseline_semantic_options"], "baseline_semantic_options")
    _expect_fields(
        options,
        required={"maxHeartbeats"},
        allowed={"maxHeartbeats"},
        where="baseline_semantic_options",
    )
    max_heartbeats = _string(options["maxHeartbeats"], "maxHeartbeats")
    if not max_heartbeats.isdecimal() or int(max_heartbeats) != 20_000:
        raise StrictIdentityError("U05 baseline maxHeartbeats must be 20000")

    def indexed_rows(field_name: str, prefix: str, fields: set[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        rows: list[dict[str, Any]] = []
        index: dict[str, dict[str, Any]] = {}
        for ordinal, raw in enumerate(_array(obj[field_name], field_name)):
            row = _mapping(raw, f"{field_name}[{ordinal}]")
            _expect_fields(row, required=fields, allowed=fields, where=f"{field_name}[{ordinal}]")
            expected_id = f"{prefix}{ordinal}"
            if row["id"] != expected_id:
                raise StrictIdentityError(f"{field_name} IDs are not canonical ordinals")
            rows.append(row)
            index[expected_id] = row
        return rows, index

    expressions, expr_index = indexed_rows(
        "expressions",
        "e",
        {
            "id",
            "kind",
            "const_name",
            "binder_info",
            "semantic_head",
            "levels",
            "children",
            "type_expr",
            "free_fvars",
            "free_mvars",
        },
    )
    local_declarations, fvar_index = indexed_rows(
        "local_declarations",
        "f",
        {
            "id",
            "binder_kind",
            "local_decl_kind",
            "type_expr",
            "value_expr",
            "is_implementation_detail",
            "is_instance",
            "depends_on_fvars",
            "depends_on_mvars",
        },
    )
    metavars, mvar_index = indexed_rows(
        "metavars",
        "m",
        {
            "id",
            "kind",
            "type_expr",
            "local_context_fvars",
            "assigned",
            "assignment_expr",
            "depends_on_mvars",
            "depends_on_fvars",
        },
    )
    local_contexts, lctx_index = indexed_rows(
        "local_contexts", "l", {"id", "declarations"}
    )

    def optional_ref(value: Any, index: Mapping[str, Any], where: str) -> None:
        if value is None:
            return
        ref = _string(value, where)
        if ref not in index:
            raise StrictIdentityError(f"{where} references missing canonical object")

    for ordinal, row in enumerate(expressions):
        _string(row["kind"], f"expression {ordinal}.kind")
        _string(row["const_name"], f"expression {ordinal}.const_name", allow_empty=False) if row["const_name"] is not None else None
        _string(row["binder_info"], f"expression {ordinal}.binder_info") if row["binder_info"] is not None else None
        _string(row["semantic_head"], f"expression {ordinal}.semantic_head", allow_empty=True) if row["semantic_head"] is not None else None
        _strict_string_array(row["levels"], f"expression {ordinal}.levels")
        for child_raw in _array(row["children"], f"expression {ordinal}.children"):
            child = _mapping(child_raw, "expression child")
            _expect_fields(child, required={"role", "expr"}, allowed={"role", "expr"}, where="expression child")
            _string(child["role"], "expression child role")
            optional_ref(child["expr"], expr_index, "expression child")
        optional_ref(row["type_expr"], expr_index, "expression type_expr")
        for ref in _strict_sorted_reference_array(
            row["free_fvars"], "expression free_fvars", prefix="f"
        ):
            optional_ref(ref, fvar_index, "expression free_fvar")
        for ref in _strict_sorted_reference_array(
            row["free_mvars"], "expression free_mvars", prefix="m"
        ):
            optional_ref(ref, mvar_index, "expression free_mvar")

    for ordinal, row in enumerate(local_declarations):
        _string(row["binder_kind"], f"local declaration {ordinal}.binder_kind")
        _string(row["local_decl_kind"], f"local declaration {ordinal}.local_decl_kind")
        optional_ref(row["type_expr"], expr_index, "local declaration type")
        optional_ref(row["value_expr"], expr_index, "local declaration value")
        _boolean(row["is_implementation_detail"], "is_implementation_detail")
        _boolean(row["is_instance"], "is_instance")
        for ref in _strict_sorted_reference_array(
            row["depends_on_fvars"], "depends_on_fvars", prefix="f"
        ):
            optional_ref(ref, fvar_index, "local-declaration fvar dependency")
        for ref in _strict_sorted_reference_array(
            row["depends_on_mvars"], "depends_on_mvars", prefix="m"
        ):
            optional_ref(ref, mvar_index, "local-declaration mvar dependency")

    for ordinal, row in enumerate(metavars):
        _string(row["kind"], f"metavar {ordinal}.kind")
        optional_ref(row["type_expr"], expr_index, "metavar type")
        _boolean(row["assigned"], "metavar assigned")
        optional_ref(row["assignment_expr"], expr_index, "metavar assignment")
        if (row["assignment_expr"] is None) == row["assigned"]:
            raise StrictIdentityError("metavar assignment presence disagrees with assigned flag")
        for ref in _strict_unique_string_array(
            row["local_context_fvars"], "local_context_fvars"
        ):
            optional_ref(ref, fvar_index, "metavar local fvar")
        for ref in _strict_sorted_reference_array(
            row["depends_on_mvars"], "metavar dependencies", prefix="m"
        ):
            optional_ref(ref, mvar_index, "metavar dependency")
        for ref in _strict_sorted_reference_array(
            row["depends_on_fvars"], "metavar fvar dependencies", prefix="f"
        ):
            optional_ref(ref, fvar_index, "metavar fvar dependency")

    for row in local_contexts:
        declarations = _strict_string_array(row["declarations"], "local context declarations")
        if len(declarations) != len(set(declarations)):
            raise StrictIdentityError("local context repeats a declaration")
        for ref in declarations:
            optional_ref(ref, fvar_index, "local-context declaration")

    goals = _array(obj["goals"], "goals")
    for ordinal, raw in enumerate(goals):
        goal = _mapping(raw, f"goal {ordinal}")
        _expect_fields(
            goal,
            required={"ordinal", "mvar", "target_expr", "local_context"},
            allowed={"ordinal", "mvar", "target_expr", "local_context"},
            where=f"goal {ordinal}",
        )
        if _integer(goal["ordinal"], "goal ordinal") != ordinal:
            raise StrictIdentityError("goal ordinals are not ordered")
        optional_ref(goal["mvar"], mvar_index, "goal mvar")
        optional_ref(goal["target_expr"], expr_index, "goal target")
        optional_ref(goal["local_context"], lctx_index, "goal local context")
        if mvar_index[goal["mvar"]]["type_expr"] != goal["target_expr"]:
            raise StrictIdentityError("goal target differs from goal-mvar type")

    typeclasses = _array(obj["typeclasses"], "typeclasses")
    seen_tc: set[str] = set()
    typeclass_by_mvar: dict[str, dict[str, Any]] = {}
    typeclass_order: list[str] = []
    for ordinal, raw in enumerate(typeclasses):
        row = _mapping(raw, f"typeclass {ordinal}")
        _expect_fields(
            row,
            required={"mvar", "class_head", "target_expr", "arguments", "local_instances", "status"},
            allowed={"mvar", "class_head", "target_expr", "arguments", "local_instances", "status"},
            where=f"typeclass {ordinal}",
        )
        mid = _string(row["mvar"], "typeclass mvar")
        if mid in seen_tc:
            raise StrictIdentityError("duplicate canonical typeclass mvar")
        seen_tc.add(mid)
        typeclass_by_mvar[mid] = row
        typeclass_order.append(mid)
        optional_ref(mid, mvar_index, "typeclass mvar")
        _string(row["class_head"], "typeclass class_head")
        optional_ref(row["target_expr"], expr_index, "typeclass target")
        for ref in _strict_string_array(row["arguments"], "typeclass arguments"):
            optional_ref(ref, expr_index, "typeclass argument")
        _strict_string_array(row["local_instances"], "typeclass local_instances")
        if row["status"] not in {"pending", "synthesized"}:
            raise StrictIdentityError("unknown canonical typeclass status")

    if typeclass_order != sorted(
        typeclass_order, key=lambda mid: _integer(mid[1:], "typeclass mvar ordinal")
    ):
        raise StrictIdentityError("typeclasses are not in canonical mvar order")

    # Re-run the exact first-occurrence traversal used by ``_Canonicalizer``.
    # Sequential labels alone are insufficient: appending an unreferenced eN,
    # fN, mN, or lN would otherwise change equality/debt while masquerading as
    # a canonical full signature.
    expr_seen: list[str] = []
    mvar_seen: list[str] = []
    fvar_seen: list[str] = []
    lctx_seen: list[str] = []
    expr_queue: deque[str] = deque()
    mvar_queue: deque[str] = deque()
    fvar_queue: deque[str] = deque()
    lctx_queue: deque[str] = deque()

    def discover(
        ref: Any,
        index: Mapping[str, Any],
        seen: list[str],
        queue: deque[str],
        where: str,
    ) -> None:
        label = _string(ref, where)
        if label not in index:
            raise StrictIdentityError(f"{where} references missing canonical object")
        if label not in seen:
            seen.append(label)
            queue.append(label)

    for goal_raw in goals:
        goal = _mapping(goal_raw, "goal")
        discover(goal["mvar"], mvar_index, mvar_seen, mvar_queue, "goal mvar")
        discover(goal["target_expr"], expr_index, expr_seen, expr_queue, "goal target")
        discover(
            goal["local_context"],
            lctx_index,
            lctx_seen,
            lctx_queue,
            "goal local context",
        )

    while expr_queue or mvar_queue or fvar_queue or lctx_queue:
        if expr_queue:
            eid = expr_queue.popleft()
            row = expr_index[eid]
            for child_raw in _array(row["children"], "expression children"):
                child = _mapping(child_raw, "expression child")
                discover(
                    child["expr"],
                    expr_index,
                    expr_seen,
                    expr_queue,
                    "expression child",
                )
            if row["type_expr"] is not None:
                discover(
                    row["type_expr"],
                    expr_index,
                    expr_seen,
                    expr_queue,
                    "expression type",
                )
            if row["kind"] == "fvar":
                refs = _strict_unique_string_array(
                    row["free_fvars"], "fvar expression refs"
                )
                if len(refs) != 1:
                    raise StrictIdentityError(
                        "canonical fvar expression lacks one exact free-fvar"
                    )
                discover(refs[0], fvar_index, fvar_seen, fvar_queue, "fvar expression")
            if row["kind"] == "mvar":
                refs = _strict_unique_string_array(
                    row["free_mvars"], "mvar expression refs"
                )
                if len(refs) != 1:
                    raise StrictIdentityError(
                        "canonical mvar expression lacks one exact free-mvar"
                    )
                discover(refs[0], mvar_index, mvar_seen, mvar_queue, "mvar expression")
            continue
        if mvar_queue:
            mid = mvar_queue.popleft()
            row = mvar_index[mid]
            discover(
                row["type_expr"], expr_index, expr_seen, expr_queue, "metavar type"
            )
            if row["assignment_expr"] is not None:
                discover(
                    row["assignment_expr"],
                    expr_index,
                    expr_seen,
                    expr_queue,
                    "metavar assignment",
                )
            for ref in _strict_unique_string_array(
                row["local_context_fvars"], "metavar local context"
            ):
                discover(ref, fvar_index, fvar_seen, fvar_queue, "metavar local fvar")
            tc = typeclass_by_mvar.get(mid)
            if tc is not None:
                discover(
                    tc["target_expr"],
                    expr_index,
                    expr_seen,
                    expr_queue,
                    "typeclass target",
                )
                for ref in _strict_string_array(tc["arguments"], "typeclass arguments"):
                    discover(
                        ref,
                        expr_index,
                        expr_seen,
                        expr_queue,
                        "typeclass argument",
                    )
            continue
        if fvar_queue:
            fid = fvar_queue.popleft()
            row = fvar_index[fid]
            discover(
                row["type_expr"],
                expr_index,
                expr_seen,
                expr_queue,
                "local declaration type",
            )
            if row["value_expr"] is not None:
                discover(
                    row["value_expr"],
                    expr_index,
                    expr_seen,
                    expr_queue,
                    "local declaration value",
                )
            continue
        lid = lctx_queue.popleft()
        for ref in _strict_string_array(
            lctx_index[lid]["declarations"], "local context declarations"
        ):
            discover(
                ref,
                fvar_index,
                fvar_seen,
                fvar_queue,
                "local context declaration",
            )

    expected_orders = (
        (expr_seen, list(expr_index), "expressions"),
        (mvar_seen, list(mvar_index), "metavars"),
        (fvar_seen, list(fvar_index), "local declarations"),
        (lctx_seen, list(lctx_index), "local contexts"),
    )
    for reached, declared, label in expected_orders:
        if reached != declared:
            raise StrictIdentityError(
                f"{label} violate reachable canonical first-occurrence closure"
            )

    if (status == "closed") != (len(goals) == 0):
        raise StrictIdentityError("state status disagrees with ordered open goals")
    if status == "closed" and any(
        (expressions, local_declarations, metavars, local_contexts, typeclasses)
    ):
        raise StrictIdentityError("closed absorbing identity contains reachable graph state")


@dataclass(frozen=True, eq=False)
class StateIdentityKey:
    """Full-compare state key; ``index_sha256`` is never equality evidence."""

    canonical_bytes: bytes = field(repr=False)
    index_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        value = parse_canonical_json_bytes(self.canonical_bytes)
        obj = _mapping(value, "state identity signature")
        _expect_fields(
            obj,
            required={
                "baseline_semantic_options",
                "environment_content_digest",
                "expressions",
                "goals",
                "local_declarations",
                "local_contexts",
                "metavars",
                "state_identity_schema",
                "status",
                "typeclasses",
            },
            allowed={
                "baseline_semantic_options",
                "environment_content_digest",
                "expressions",
                "goals",
                "local_declarations",
                "local_contexts",
                "metavars",
                "state_identity_schema",
                "status",
                "typeclasses",
            },
            where="state identity signature",
        )
        if obj["state_identity_schema"] != STATE_IDENTITY_SCHEMA:
            raise StrictIdentityError("wrong state identity schema")
        _digest(obj["environment_content_digest"], "environment_content_digest")
        _validate_state_signature(obj)
        object.__setattr__(self, "index_sha256", _sha256_upper(self.canonical_bytes))

    @classmethod
    def from_signature(cls, signature: Mapping[str, Any]) -> "StateIdentityKey":
        if type(signature) is not dict:
            raise StrictIdentityError("state identity signature must be a plain object")
        return cls(canonical_json_bytes(signature))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StateIdentityKey":
        obj = _mapping(value, "StateIdentityKey")
        _expect_fields(
            obj,
            required={"schema_version", "index_sha256", "full_signature"},
            allowed={"schema_version", "index_sha256", "full_signature"},
            where="StateIdentityKey",
        )
        if obj["schema_version"] != STATE_IDENTITY_SCHEMA:
            raise StrictIdentityError("wrong StateIdentityKey schema")
        key = cls.from_signature(_mapping(obj["full_signature"], "full_signature"))
        if _digest(obj["index_sha256"], "index_sha256") != key.index_sha256:
            raise StrictIdentityError("StateIdentityKey index digest mismatch")
        return key

    @property
    def full_signature(self) -> dict[str, Any]:
        return _mapping(parse_canonical_json_bytes(self.canonical_bytes), "signature")

    @property
    def environment_content_digest(self) -> str:
        return str(self.full_signature["environment_content_digest"])

    @property
    def status(self) -> str:
        return str(self.full_signature["status"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_IDENTITY_SCHEMA,
            "index_sha256": self.index_sha256,
            "full_signature": self.full_signature,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StateIdentityKey):
            return NotImplemented
        if self.index_sha256 != other.index_sha256:
            return False
        return hmac.compare_digest(self.canonical_bytes, other.canonical_bytes)

    def __hash__(self) -> int:
        return hash((STATE_IDENTITY_SCHEMA, self.index_sha256))


_TOP_REQUIRED = {
    "schema_version",
    "extraction_backend",
    "state_id",
    "task_id",
    "env_fingerprint",
    "state_hash_raw",
    "state_hash_norm",
    "status",
    "goals",
    "expr_graph",
    "local_contexts",
    "local_context",
    "metavars",
    "typeclasses",
    "messages",
    "options",
    "proof_prefix_hash",
    "proof_prefix",
    "parent_state_id",
    "object_coverage",
    "minimal_support",
    "closed",
    "canonical_status",
}

_GOAL_FIELDS = {
    "goal_id",
    "mvar_id",
    "target_text",
    "target_expr_id",
    "target_head",
    "relation",
    "local_context_graph_id",
    "target_symbols",
    "domain_tags",
    "connective_counts",
    "carrier_atoms_readout",
    "raw_hash",
    "norm_hash",
}

_EXPR_FIELDS = {
    "expr_id",
    "kind",
    "head",
    "const_name",
    "levels",
    "binder_info",
    "children",
    "type_expr_id",
    "free_fvars",
    "free_mvars",
    "pretty",
    "raw_hash",
    "norm_hash",
}

_LCTX_FIELDS = {
    "schema_version",
    "local_context_graph_id",
    "nodes",
    "edges",
    "raw_hash",
    "norm_hash",
}

_LOCAL_DECL_FIELDS = {
    "fvar_id",
    "user_name",
    "binder_kind",
    "local_decl_kind",
    "type_expr_id",
    "value_expr_id",
    "is_implementation_detail",
    "is_instance",
    "depends_on_fvars",
    "depends_on_mvars",
    "raw_hash",
    "norm_hash",
}

_MVAR_FIELDS = {
    "mvar_id",
    "user_name",
    "type_text",
    "depends_on",
    "type_expr_id",
    "local_context_fvars",
    "assigned",
    "assignment_expr_id",
    "kind",
    "dependencies_mvars",
    "dependencies_fvars",
    "raw_hash",
    "norm_hash",
}

_TYPECLASS_FIELDS = {
    "obligation_id",
    "mvar_id",
    "class_head",
    "target_expr_id",
    "arguments",
    "local_instances",
    "status",
    "messages",
}


class _Canonicalizer:
    def __init__(self, kernel_state: Mapping[str, Any]) -> None:
        self.state = _mapping(kernel_state, "kernel_state")
        _expect_fields(
            self.state,
            required=_TOP_REQUIRED,
            allowed=_TOP_REQUIRED,
            where="kernel_state",
        )
        if self.state["schema_version"] != LEGACY_KERNEL_STATE_SCHEMA_VERSION:
            raise StrictIdentityError("U05 identity requires kernel-state v3")
        if self.state["extraction_backend"] != "lean_kernel_rpc_in_memory_v1":
            raise StrictIdentityError("kernel state was not extracted by the in-memory RPC")

        coverage = _mapping(self.state["object_coverage"], "object_coverage")
        required_coverage = {
            "expr_ast",
            "local_decl_graph",
            "metavariable_graph",
            "typeclass_graph",
        }
        for field_name in required_coverage:
            if coverage.get(field_name) is not True:
                raise StrictIdentityError(f"required coverage is incomplete: {field_name}")

        status = _string(self.state["status"], "kernel_state.status")
        closed = _boolean(self.state["closed"], "kernel_state.closed")
        if status not in {"open", "closed"} or closed != (status == "closed"):
            raise StrictIdentityError("identity is defined only for coherent open/closed states")

        graph = _mapping(self.state["expr_graph"], "expr_graph")
        _expect_fields(
            graph,
            required={"schema_version", "nodes", "edges", "roots", "source"},
            allowed={"schema_version", "nodes", "edges", "roots", "source"},
            where="expr_graph",
        )
        if graph["schema_version"] != "lean-rgc-expr-graph-v1":
            raise StrictIdentityError("wrong expression graph schema")
        self.expr_nodes = self._unique_map(
            _array(graph["nodes"], "expr_graph.nodes"), "expr_id", _EXPR_FIELDS, "expr"
        )
        self.graph_roots = [
            _string(root, "expr_graph.root")
            for root in _array(graph["roots"], "expr_graph.roots")
        ]
        self.expr_edges = _array(graph["edges"], "expr_graph.edges")
        self.edge_roles: dict[tuple[str, str], deque[str]] = {}
        for index, raw_edge in enumerate(self.expr_edges):
            edge = _mapping(raw_edge, f"expr edge {index}")
            _expect_fields(
                edge,
                required={"src", "dst", "role"},
                allowed={"src", "dst", "role"},
                where=f"expr edge {index}",
            )
            src = _string(edge["src"], f"expr edge {index}.src")
            dst = _string(edge["dst"], f"expr edge {index}.dst")
            role = _string(edge["role"], f"expr edge {index}.role")
            self.edge_roles.setdefault((src, dst), deque()).append(role)

        self.goals = self._objects(
            _array(self.state["goals"], "goals"), _GOAL_FIELDS, "goal"
        )
        goal_roots = [
            _string(goal["target_expr_id"], "goal.target_expr_id")
            for goal in self.goals
        ]
        if self.graph_roots != goal_roots:
            raise StrictIdentityError("expression roots do not equal ordered goal targets")
        self.mvars = self._unique_map(
            _array(self.state["metavars"], "metavars"),
            "mvar_id",
            _MVAR_FIELDS,
            "metavar",
        )
        self.local_contexts = self._unique_map(
            _array(self.state["local_contexts"], "local_contexts"),
            "local_context_graph_id",
            _LCTX_FIELDS,
            "local context",
        )
        self.fvars: dict[str, dict[str, Any]] = {}
        self.fvar_context: dict[str, str] = {}
        for lctx_id, lctx in self.local_contexts.items():
            if lctx["schema_version"] != "lean-rgc-local-context-graph-v1":
                raise StrictIdentityError("wrong local-context graph schema")
            nodes = self._objects(
                _array(lctx["nodes"], f"local context {lctx_id}.nodes"),
                _LOCAL_DECL_FIELDS,
                f"local declaration in {lctx_id}",
            )
            for node in nodes:
                fid = _string(node["fvar_id"], "local declaration fvar_id")
                if fid in self.fvars:
                    if canonical_json_bytes(self.fvars[fid]) != canonical_json_bytes(node):
                        raise StrictIdentityError(f"conflicting local declaration: {fid}")
                else:
                    self.fvars[fid] = node
                    self.fvar_context[fid] = lctx_id

        self.typeclasses = self._objects(
            _array(self.state["typeclasses"], "typeclasses"),
            _TYPECLASS_FIELDS,
            "typeclass",
        )
        self.typeclass_by_mvar: dict[str, dict[str, Any]] = {}
        for tc in self.typeclasses:
            mid = _string(tc["mvar_id"], "typeclass.mvar_id")
            if mid in self.typeclass_by_mvar:
                raise StrictIdentityError(f"duplicate typeclass mvar: {mid}")
            self.typeclass_by_mvar[mid] = tc

        self.expr_ord: dict[str, int] = {}
        self.mvar_ord: dict[str, int] = {}
        self.fvar_ord: dict[str, int] = {}
        self.lctx_ord: dict[str, int] = {}
        self.expr_queue: deque[str] = deque()
        self.mvar_queue: deque[str] = deque()
        self.fvar_queue: deque[str] = deque()
        self.lctx_queue: deque[str] = deque()
        self.universe_ord: dict[str, int] = {}

    @staticmethod
    def _objects(rows: list[Any], allowed: set[str], where: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for index, raw in enumerate(rows):
            obj = _mapping(raw, f"{where} {index}")
            _expect_fields(
                obj, required=allowed, allowed=allowed, where=f"{where} {index}"
            )
            out.append(obj)
        return out

    @classmethod
    def _unique_map(
        cls,
        rows: list[Any],
        key: str,
        allowed: set[str],
        where: str,
    ) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for row in cls._objects(rows, allowed, where):
            identity = _string(row[key], f"{where}.{key}")
            if identity in out:
                raise StrictIdentityError(f"duplicate {where} identity: {identity}")
            out[identity] = row
        return out

    def _discover(
        self,
        raw: Any,
        table: Mapping[str, Any],
        ordinals: dict[str, int],
        queue: deque[str],
        where: str,
    ) -> str:
        identity = _string(raw, where)
        if identity not in table:
            raise StrictIdentityError(f"{where} references missing object: {identity}")
        if identity not in ordinals:
            ordinals[identity] = len(ordinals)
            queue.append(identity)
        return identity

    def discover_expr(self, raw: Any, where: str) -> str | None:
        if raw is None:
            return None
        return self._discover(
            raw, self.expr_nodes, self.expr_ord, self.expr_queue, where
        )

    def discover_mvar(self, raw: Any, where: str) -> str:
        return self._discover(raw, self.mvars, self.mvar_ord, self.mvar_queue, where)

    def discover_fvar(self, raw: Any, where: str) -> str:
        return self._discover(raw, self.fvars, self.fvar_ord, self.fvar_queue, where)

    def discover_lctx(self, raw: Any, where: str) -> str:
        return self._discover(
            raw, self.local_contexts, self.lctx_ord, self.lctx_queue, where
        )

    @staticmethod
    def _ordered_unique(values: Sequence[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                out.append(value)
        return out

    def _drain_discovery(self) -> None:
        while self.expr_queue or self.mvar_queue or self.fvar_queue or self.lctx_queue:
            if self.expr_queue:
                eid = self.expr_queue.popleft()
                node = self.expr_nodes[eid]
                for child in _array(node["children"], f"expr {eid}.children"):
                    self.discover_expr(child, f"expr {eid}.child")
                self.discover_expr(node["type_expr_id"], f"expr {eid}.type_expr_id")
                kind = _string(node["kind"], f"expr {eid}.kind")
                free_fvars = _array(node["free_fvars"], f"expr {eid}.free_fvars")
                free_mvars = _array(node["free_mvars"], f"expr {eid}.free_mvars")
                if kind == "fvar":
                    if len(free_fvars) != 1:
                        raise StrictIdentityError("fvar expression lacks one exact free-fvar")
                    self.discover_fvar(free_fvars[0], f"expr {eid}.free_fvar")
                if kind == "mvar":
                    if len(free_mvars) != 1:
                        raise StrictIdentityError("mvar expression lacks one exact free-mvar")
                    self.discover_mvar(free_mvars[0], f"expr {eid}.free_mvar")
                continue
            if self.mvar_queue:
                mid = self.mvar_queue.popleft()
                node = self.mvars[mid]
                self.discover_expr(node["type_expr_id"], f"mvar {mid}.type")
                self.discover_expr(node["assignment_expr_id"], f"mvar {mid}.assignment")
                for fid in _array(node["local_context_fvars"], f"mvar {mid}.lctx"):
                    self.discover_fvar(fid, f"mvar {mid}.local fvar")
                tc = self.typeclass_by_mvar.get(mid)
                if tc is not None:
                    self.discover_expr(tc["target_expr_id"], f"typeclass {mid}.target")
                    for arg in _array(tc["arguments"], f"typeclass {mid}.arguments"):
                        self.discover_expr(arg, f"typeclass {mid}.argument")
                continue
            if self.fvar_queue:
                fid = self.fvar_queue.popleft()
                node = self.fvars[fid]
                self.discover_expr(node["type_expr_id"], f"fvar {fid}.type")
                self.discover_expr(node["value_expr_id"], f"fvar {fid}.value")
                continue
            lctx_id = self.lctx_queue.popleft()
            lctx = self.local_contexts[lctx_id]
            for node in _array(lctx["nodes"], f"local context {lctx_id}.nodes"):
                self.discover_fvar(
                    _mapping(node, "local declaration")["fvar_id"],
                    f"local context {lctx_id}.fvar",
                )

    def _expr_label(self, raw: Any) -> str | None:
        if raw is None:
            return None
        identity = _string(raw, "expression reference")
        if identity not in self.expr_ord:
            raise StrictIdentityError(f"unreachable expression reference: {identity}")
        return f"e{self.expr_ord[identity]}"

    def _mvar_label(self, raw: Any) -> str:
        identity = _string(raw, "mvar reference")
        if identity not in self.mvar_ord:
            raise StrictIdentityError(f"unreachable mvar reference: {identity}")
        return f"m{self.mvar_ord[identity]}"

    def _fvar_label(self, raw: Any) -> str:
        identity = _string(raw, "fvar reference")
        if identity not in self.fvar_ord:
            raise StrictIdentityError(f"unreachable fvar reference: {identity}")
        return f"f{self.fvar_ord[identity]}"

    def _lctx_label(self, raw: Any) -> str:
        return f"l{self.lctx_ord[_string(raw, 'local context reference')]}"

    def _normalize_level_text(self, value: Any) -> str:
        text = _string(value, "universe level", allow_empty=True)
        # Lean-generated universe metavariable names are transport names.  Keep
        # the structured constructor text while numbering names by their global
        # first occurrence in the reachable ordered expression traversal.  This
        # preserves sharing: one universe metavariable used in two nodes remains
        # different from two unrelated universe metavariables.

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if token not in self.universe_ord:
                self.universe_ord[token] = len(self.universe_ord)
            return f"?u{self.universe_ord[token]}"

        return re.sub(r"\?(?:u|m)\.[A-Za-z0-9_.']+", repl, text)

    def _canonical_expr(self, raw_id: str) -> dict[str, Any]:
        node = self.expr_nodes[raw_id]
        kind = _string(node["kind"], f"expr {raw_id}.kind")
        children = [
            _string(child, f"expr {raw_id}.child")
            for child in _array(node["children"], f"expr {raw_id}.children")
        ]
        expected_roles = {
            "app": ["fn", "arg"],
            "lam": ["type", "body"],
            "forallE": ["domain", "body"],
            "letE": ["type", "value", "body"],
            "mdata": ["expr"],
            "proj": ["expr"],
        }.get(kind, [])
        if len(children) != len(expected_roles):
            raise StrictIdentityError(
                f"expression child arity disagrees with kind {kind}: {raw_id}"
            )
        actual_edges = Counter(
            (dst, role)
            for (src, dst), roles in self.edge_roles.items()
            if src == raw_id
            for role in roles
        )
        expected_edges = Counter(zip(children, expected_roles))
        if actual_edges != expected_edges:
            raise StrictIdentityError(f"expression role edges disagree with children: {raw_id}")
        child_rows: list[dict[str, str]] = []
        for child_id, role in zip(children, expected_roles):
            child_rows.append({"role": role, "expr": self._expr_label(child_id)})

        const_name = node["const_name"]
        binder_info = node["binder_info"]
        if const_name is not None:
            _string(const_name, f"expr {raw_id}.const_name")
        if binder_info is not None:
            _string(binder_info, f"expr {raw_id}.binder_info")
        semantic_head: str | None = None
        if kind in {"bvar", "lit", "proj"}:
            semantic_head = _string(node["head"], f"expr {raw_id}.head", allow_empty=True)
        return {
            "id": self._expr_label(raw_id),
            "kind": kind,
            "const_name": const_name,
            "binder_info": binder_info,
            "semantic_head": semantic_head,
            "levels": [
                self._normalize_level_text(level)
                for level in _array(node["levels"], f"expr {raw_id}.levels")
            ],
            "children": child_rows,
            "type_expr": self._expr_label(node["type_expr_id"]),
            "free_fvars": [
                self._fvar_label(fid)
                for fid in sorted(
                    self._ordered_unique(
                    [
                        _string(x, f"expr {raw_id}.free_fvar")
                        for x in _array(node["free_fvars"], f"expr {raw_id}.free_fvars")
                    ]),
                    key=lambda raw: self.fvar_ord.get(raw, 2**63 - 1),
                )
            ],
            "free_mvars": [
                self._mvar_label(mid)
                for mid in sorted(
                    self._ordered_unique(
                    [
                        _string(x, f"expr {raw_id}.free_mvar")
                        for x in _array(node["free_mvars"], f"expr {raw_id}.free_mvars")
                    ]),
                    key=lambda raw: self.mvar_ord.get(raw, 2**63 - 1),
                )
            ],
        }

    def _canonical_fvar(self, raw_id: str) -> dict[str, Any]:
        node = self.fvars[raw_id]
        return {
            "id": self._fvar_label(raw_id),
            "binder_kind": _string(node["binder_kind"], f"fvar {raw_id}.binder_kind"),
            "local_decl_kind": _string(
                node["local_decl_kind"], f"fvar {raw_id}.local_decl_kind"
            ),
            "type_expr": self._expr_label(node["type_expr_id"]),
            "value_expr": self._expr_label(node["value_expr_id"]),
            "is_implementation_detail": _boolean(
                node["is_implementation_detail"],
                f"fvar {raw_id}.is_implementation_detail",
            ),
            "is_instance": _boolean(node["is_instance"], f"fvar {raw_id}.is_instance"),
            "depends_on_fvars": [
                self._fvar_label(fid)
                for fid in sorted(
                    self._ordered_unique(
                    [
                        _string(x, f"fvar {raw_id}.dependency")
                        for x in _array(node["depends_on_fvars"], "depends_on_fvars")
                    ]),
                    key=lambda raw: self.fvar_ord.get(raw, 2**63 - 1),
                )
            ],
            "depends_on_mvars": [
                self._mvar_label(mid)
                for mid in sorted(
                    self._ordered_unique(
                    [
                        _string(x, f"fvar {raw_id}.mvar dependency")
                        for x in _array(node["depends_on_mvars"], "depends_on_mvars")
                    ]),
                    key=lambda raw: self.mvar_ord.get(raw, 2**63 - 1),
                )
            ],
        }

    def _canonical_mvar(self, raw_id: str) -> dict[str, Any]:
        node = self.mvars[raw_id]
        dependencies = sorted(
            self._ordered_unique(
            [
                _string(x, f"mvar {raw_id}.dependency")
                for x in _array(node["depends_on"], "depends_on")
                + _array(node["dependencies_mvars"], "dependencies_mvars")
            ]),
            key=lambda raw: self.mvar_ord.get(raw, 2**63 - 1),
        )
        return {
            "id": self._mvar_label(raw_id),
            "kind": _string(node["kind"], f"mvar {raw_id}.kind"),
            "type_expr": self._expr_label(node["type_expr_id"]),
            "local_context_fvars": [
                self._fvar_label(fid)
                for fid in self._ordered_unique(
                    [
                        _string(x, f"mvar {raw_id}.local fvar")
                        for x in _array(node["local_context_fvars"], "local_context_fvars")
                    ]
                )
            ],
            "assigned": _boolean(node["assigned"], f"mvar {raw_id}.assigned"),
            "assignment_expr": self._expr_label(node["assignment_expr_id"]),
            "depends_on_mvars": [self._mvar_label(mid) for mid in dependencies],
            "depends_on_fvars": [
                self._fvar_label(fid)
                for fid in sorted(
                    self._ordered_unique(
                    [
                        _string(x, f"mvar {raw_id}.fvar dependency")
                        for x in _array(node["dependencies_fvars"], "dependencies_fvars")
                    ]),
                    key=lambda raw: self.fvar_ord.get(raw, 2**63 - 1),
                )
            ],
        }

    def signature(
        self,
        *,
        environment_content_digest: str,
        baseline_semantic_options: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        canonical_goals: list[dict[str, Any]] = []
        for index, goal in enumerate(self.goals):
            mid = self.discover_mvar(goal["mvar_id"], f"goal {index}.mvar_id")
            expr = self.discover_expr(goal["target_expr_id"], f"goal {index}.target")
            lctx = self.discover_lctx(
                goal["local_context_graph_id"], f"goal {index}.local_context"
            )
            mvar_type = self.mvars[mid]["type_expr_id"]
            if mvar_type != expr:
                raise StrictIdentityError("goal target and goal-mvar type disagree")
            # The legacy carrier readout is an observation, not state identity.
            # Validate its shape but never copy it into the full signature.
            for atom in _array(goal["carrier_atoms_readout"], "carrier_atoms_readout"):
                _string(atom, f"goal {index}.carrier atom")
            canonical_goals.append(
                {
                    "ordinal": index,
                    "mvar": mid,
                    "target_expr": expr,
                    "local_context": lctx,
                }
            )
        self._drain_discovery()

        # Substitute labels only after the complete reachable first-occurrence
        # pass, so every reference is checked and no raw process label survives.
        for row in canonical_goals:
            row["mvar"] = self._mvar_label(row["mvar"])
            row["target_expr"] = self._expr_label(row["target_expr"])
            row["local_context"] = self._lctx_label(row["local_context"])

        lctx_rows: list[dict[str, Any]] = []
        for raw_id, ordinal in sorted(self.lctx_ord.items(), key=lambda pair: pair[1]):
            lctx = self.local_contexts[raw_id]
            ordered_fvars = [
                _string(_mapping(node, "local declaration")["fvar_id"], "fvar_id")
                for node in _array(lctx["nodes"], f"local context {raw_id}.nodes")
            ]
            lctx_rows.append(
                {
                    "id": self._lctx_label(raw_id),
                    "declarations": [self._fvar_label(fid) for fid in ordered_fvars],
                }
            )

        tc_rows: list[dict[str, Any]] = []
        for raw_mid, ordinal in sorted(self.mvar_ord.items(), key=lambda pair: pair[1]):
            tc = self.typeclass_by_mvar.get(raw_mid)
            if tc is None:
                continue
            status = _string(tc["status"], f"typeclass {raw_mid}.status")
            if status not in {"pending", "synthesized"}:
                raise StrictIdentityError("unknown typeclass status")
            tc_rows.append(
                {
                    "mvar": self._mvar_label(raw_mid),
                    "class_head": _string(
                        tc["class_head"], f"typeclass {raw_mid}.class_head"
                    ),
                    "target_expr": self._expr_label(tc["target_expr_id"]),
                    "arguments": [
                        self._expr_label(arg)
                        for arg in _array(tc["arguments"], "typeclass.arguments")
                    ],
                    "local_instances": [
                        _string(x, "typeclass.local_instance")
                        for x in _array(tc["local_instances"], "local_instances")
                    ],
                    "status": status,
                }
            )

        options = (
            _mapping(self.state["options"], "kernel_state.options")
            if baseline_semantic_options is None
            else _mapping(baseline_semantic_options, "baseline_semantic_options")
        )
        _validate_json(options)
        signature = {
            "state_identity_schema": STATE_IDENTITY_SCHEMA,
            "environment_content_digest": _digest(
                environment_content_digest, "environment_content_digest"
            ),
            "baseline_semantic_options": dict(options),
            "status": _string(self.state["status"], "kernel_state.status"),
            "goals": canonical_goals,
            "local_contexts": lctx_rows,
            "local_declarations": [
                self._canonical_fvar(raw_id)
                for raw_id, _ordinal in sorted(
                    self.fvar_ord.items(), key=lambda pair: pair[1]
                )
            ],
            "metavars": [
                self._canonical_mvar(raw_id)
                for raw_id, _ordinal in sorted(
                    self.mvar_ord.items(), key=lambda pair: pair[1]
                )
            ],
            "expressions": [
                self._canonical_expr(raw_id)
                for raw_id, _ordinal in sorted(
                    self.expr_ord.items(), key=lambda pair: pair[1]
                )
            ],
            "typeclasses": tc_rows,
        }
        canonical_json_bytes(signature)
        return signature


def state_identity_from_kernel_state(
    kernel_state: Mapping[str, Any],
    *,
    environment_content_digest: str,
    baseline_semantic_options: Mapping[str, Any] | None = None,
) -> StateIdentityKey:
    """Construct an exact U05 key from a complete reachable v3 graph."""

    signature = _Canonicalizer(kernel_state).signature(
        environment_content_digest=environment_content_digest,
        baseline_semantic_options=baseline_semantic_options,
    )
    return StateIdentityKey.from_signature(signature)


def debt_readout_from_identity(key: StateIdentityKey) -> tuple[int, int, int, int, int]:
    """Return the frozen five-coordinate U05 debt readout.

    The carrier coordinate preserves per-goal atom multiplicity.  All remaining
    coordinates are counted only over the reachable canonical signature.
    """

    signature = key.full_signature
    goals = _array(signature["goals"], "signature.goals")
    mvars = _array(signature["metavars"], "signature.metavars")
    typeclasses = _array(signature["typeclasses"], "signature.typeclasses")
    expressions = _array(signature["expressions"], "signature.expressions")
    expr_by_id = {
        _string(_mapping(row, "expression")["id"], "expression.id"): _mapping(
            row, "expression"
        )
        for row in expressions
    }

    def target_carrier_count(goal: Any) -> int:
        goal_obj = _mapping(goal, "goal")
        root = _string(goal_obj["target_expr"], "goal.target_expr")
        reachable: list[dict[str, Any]] = []
        queue = deque([root])
        seen: set[str] = set()
        while queue:
            expr_id = queue.popleft()
            if expr_id in seen:
                continue
            seen.add(expr_id)
            node = expr_by_id.get(expr_id)
            if node is None:
                raise StrictIdentityError(f"debt readout references missing expr: {expr_id}")
            reachable.append(node)
            for child in _array(node["children"], "expression.children"):
                queue.append(
                    _string(_mapping(child, "expression child")["expr"], "child.expr")
                )

        head_node = expr_by_id[root]
        while head_node["kind"] == "app":
            children = _array(head_node["children"], "head expression children")
            fn_children = [
                _mapping(child, "head child")
                for child in children
                if _mapping(child, "head child")["role"] == "fn"
            ]
            if len(fn_children) != 1:
                break
            head_node = expr_by_id[
                _string(fn_children[0]["expr"], "head function expression")
            ]
        head = head_node.get("const_name") or head_node.get("semantic_head") or head_node[
            "kind"
        ]
        count = 0
        if head == "Eq":
            count += 1
        if head == "And":
            count += 1
        if head == "Or":
            count += 1
        if head_node["kind"] == "forallE":
            count += 1
        if any(
            "Nat" in str(node.get("const_name") or node.get("semantic_head") or "")
            for node in reachable
        ):
            count += 1
        return count

    return (
        len(goals),
        sum(1 for row in mvars if not _mapping(row, "mvar")["assigned"]),
        sum(1 for row in typeclasses if _mapping(row, "typeclass")["status"] == "pending"),
        sum(target_carrier_count(goal) for goal in goals),
        len(expressions),
    )


__all__ = [
    "LEGACY_KERNEL_STATE_SCHEMA_VERSION",
    "STATE_IDENTITY_SCHEMA",
    "StateIdentityKey",
    "StrictIdentityError",
    "canonical_json_bytes",
    "debt_readout_from_identity",
    "parse_canonical_json_bytes",
    "state_identity_from_kernel_state",
]
