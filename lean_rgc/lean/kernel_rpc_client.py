from __future__ import annotations

"""Strict raw client boundary for the additive U05 kernel RPC contract.

The legacy wire envelope remains ``lean-rgc-jsonl-rpc-v2`` and the kernel-state
payload remains v3.  This module validates the separately versioned U05 fields
without passing them through permissive schema adapters.  Unknown or duplicate
fields fail closed before a transition contract can be built.
"""

from collections import deque
from dataclasses import dataclass
import json
import os
import queue
import subprocess
import threading
from typing import Any, Callable, Mapping, Protocol, Sequence

from lean_rgc.odlrq.contracts import (
    ActionSymbol,
    BoundAction,
    CapSemantics,
    Censor,
    CensorKind,
    DebtReadout,
    EPISODE_BUDGET_SENTINEL,
    REPLAY_VERIFICATION_SCHEMA,
    StrictContractError,
    U05_SEMANTICS_VERSION,
    U05TaskSpec,
)
from lean_rgc.odlrq.rule_algebra import (
    OracleEvent,
    StateView,
)
from .kernel_state_identity import (
    LEGACY_KERNEL_STATE_SCHEMA_VERSION,
    StateIdentityKey,
    StrictIdentityError,
    canonical_json_bytes,
    state_identity_from_kernel_state,
)


LEGACY_RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"


class StrictKernelRPCError(RuntimeError):
    """Base error for malformed, rejected, or mismatched RPC records."""


class StrictKernelRPCProtocolError(StrictKernelRPCError):
    """The response is outside the frozen strict wire contract."""


class KernelRPCRemoteError(StrictKernelRPCError):
    """The worker returned a well-formed ``ok=false`` response."""


class KernelRPCTransportError(StrictKernelRPCError):
    """The worker process transport failed before a strict response arrived."""


class KernelRPCTransportTimeout(KernelRPCTransportError):
    """The wall-clock response deadline expired and the worker was stopped."""


class KernelRPCProcessExited(KernelRPCTransportError):
    """The worker closed stdout before returning the requested response."""


class StrictStateOwnershipError(StrictKernelRPCError):
    """An operation attempted to use or discard an unowned live state id."""


def _obj(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StrictKernelRPCProtocolError(f"{where} must be an object")
    return value


def _arr(value: Any, where: str) -> list[Any]:
    if type(value) is not list:
        raise StrictKernelRPCProtocolError(f"{where} must be an array")
    return value


def _str(value: Any, where: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or not value:
        raise StrictKernelRPCProtocolError(f"{where} must be a nonempty string")
    return value


def _plain_str(value: Any, where: str) -> str:
    if type(value) is not str:
        raise StrictKernelRPCProtocolError(f"{where} must be a string")
    return value


def _int(value: Any, where: str, *, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if type(value) is not int or value < 0:
        raise StrictKernelRPCProtocolError(f"{where} must be a nonnegative integer")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        raise StrictKernelRPCProtocolError(f"{where} must be a boolean")
    return value


def _exact(value: Mapping[str, Any], fields: set[str], where: str) -> None:
    actual = set(value)
    if actual != fields:
        raise StrictKernelRPCProtocolError(
            f"{where} field mismatch; missing={sorted(fields - actual)}, "
            f"unknown={sorted(actual - fields)}"
        )


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictKernelRPCProtocolError(f"duplicate JSON field: {key}")
        out[key] = value
    return out


def _reject_float(_raw: str) -> None:
    raise StrictKernelRPCProtocolError("floating-point JSON is forbidden")


def _reject_constant(_raw: str) -> None:
    raise StrictKernelRPCProtocolError("non-finite JSON is forbidden")


def parse_strict_json_line(raw: bytes | str) -> dict[str, Any]:
    """Parse one worker line with duplicate/float/non-finite rejection."""

    try:
        if type(raw) is bytes:
            text = raw.decode("utf-8", errors="strict")
        elif type(raw) is str:
            text = raw
        else:
            raise StrictKernelRPCProtocolError("RPC line must be bytes or str")
        if "\n" in text.rstrip("\r\n"):
            raise StrictKernelRPCProtocolError("RPC response contains multiple lines")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except StrictKernelRPCProtocolError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise StrictKernelRPCProtocolError("invalid strict RPC JSON") from exc
    return _obj(value, "RPC response")


_REPLAY_TRANSPORT_KEYS = {
    "state_id",
    "parent_state_id",
    "state_hash_raw",
    "state_hash_norm",
    "graph_id",
    "local_context_graph_id",
}


def strip_replay_transport(value: Any) -> Any:
    """Mirror the native replay comparison's exact transport-field erasure."""

    if type(value) is dict:
        return {
            key: strip_replay_transport(item)
            for key, item in value.items()
            if key not in _REPLAY_TRANSPORT_KEYS
        }
    if type(value) is list:
        return [strip_replay_transport(item) for item in value]
    return value


def _json_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _validate_envelope(
    value: Mapping[str, Any], *, expected_request_id: str | None, fields: set[str]
) -> dict[str, Any]:
    obj = _obj(value, "RPC response")
    _exact(obj, fields | {"id", "rpc_protocol_version", "ok"}, "RPC response")
    if obj["rpc_protocol_version"] != LEGACY_RPC_PROTOCOL_VERSION:
        raise StrictKernelRPCProtocolError("legacy RPC protocol version changed")
    request_id = obj["id"]
    if request_id is not None and type(request_id) is not str:
        raise StrictKernelRPCProtocolError("response id must be string or null")
    if request_id != expected_request_id:
        raise StrictKernelRPCProtocolError("response id does not match request")
    _bool(obj["ok"], "RPC response.ok")
    return obj


def raise_for_rpc_error(
    value: Mapping[str, Any], *, expected_request_id: str | None
) -> None:
    obj = _obj(value, "RPC response")
    if obj.get("ok") is not False:
        return
    parsed = _validate_envelope(
        obj, expected_request_id=expected_request_id, fields={"error"}
    )
    message = _str(parsed["error"], "RPC error")
    raise KernelRPCRemoteError(message)


KERNEL_RPC_BACKEND = "lean_kernel_rpc_in_memory_v1"
U05_BASELINE_OPTIONS = {"maxHeartbeats": "20000"}


def _response_value(raw: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    return (
        parse_strict_json_line(raw)
        if type(raw) in (bytes, str)
        else _obj(raw, "response")
    )


def _string_tuple(value: Any, where: str, *, nonempty: bool = False) -> tuple[str, ...]:
    rows = tuple(_str(item, f"{where} item") for item in _arr(value, where))
    if nonempty and not rows:
        raise StrictKernelRPCProtocolError(f"{where} must be nonempty")
    if len(rows) != len(set(rows)):
        raise StrictKernelRPCProtocolError(f"{where} contains duplicates")
    return rows  # type: ignore[return-value]


@dataclass(frozen=True)
class KernelStateSummary:
    state_id: str
    task_id: str
    status: str
    goal_count: int
    parent_state_id: str | None
    proof_prefix: str


def _parse_state_summary(
    value: Any, *, allowed_statuses: frozenset[str]
) -> KernelStateSummary:
    obj = _obj(value, "state summary")
    _exact(
        obj,
        {
            "state_id",
            "task_id",
            "status",
            "goal_count",
            "parent_state_id",
            "proof_prefix",
            "canonical_status",
        },
        "state summary",
    )
    status = _str(obj["status"], "state summary.status")
    if status not in allowed_statuses:
        raise StrictKernelRPCProtocolError("state summary has an inadmissible status")
    if obj["canonical_status"] != "lean_kernel_rpc_in_memory_state":
        raise StrictKernelRPCProtocolError("state summary canonical status changed")
    parent = _str(
        obj["parent_state_id"], "state summary.parent_state_id", optional=True
    )
    return KernelStateSummary(
        state_id=_str(obj["state_id"], "state summary.state_id"),  # type: ignore[arg-type]
        task_id=_str(obj["task_id"], "state summary.task_id"),  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        goal_count=_int(obj["goal_count"], "state summary.goal_count"),  # type: ignore[arg-type]
        parent_state_id=parent,
        proof_prefix=_plain_str(obj["proof_prefix"], "state summary.proof_prefix"),
    )


def _validate_v3_kernel_state(
    value: Any,
    *,
    expected_summary: KernelStateSummary,
    expected_task: U05TaskSpec | None = None,
    require_identity_status: bool = True,
) -> dict[str, Any]:
    kernel = _obj(value, "kernel_state")
    if kernel.get("schema_version") != LEGACY_KERNEL_STATE_SCHEMA_VERSION:
        raise StrictKernelRPCProtocolError("kernel_state is not legacy v3")
    if kernel.get("extraction_backend") != KERNEL_RPC_BACKEND:
        raise StrictKernelRPCProtocolError("kernel_state backend changed")
    if kernel.get("state_id") != expected_summary.state_id:
        raise StrictKernelRPCProtocolError("kernel_state id differs from summary")
    if kernel.get("task_id") != expected_summary.task_id:
        raise StrictKernelRPCProtocolError("kernel_state task differs from summary")
    if kernel.get("status") != expected_summary.status:
        raise StrictKernelRPCProtocolError("kernel_state status differs from summary")
    goals = _arr(kernel.get("goals"), "kernel_state.goals")
    if len(goals) != expected_summary.goal_count:
        raise StrictKernelRPCProtocolError("kernel_state goal count differs from summary")
    if (expected_summary.status == "closed") != (expected_summary.goal_count == 0):
        raise StrictKernelRPCProtocolError("state summary status disagrees with goals")
    if _bool(kernel.get("closed"), "kernel_state.closed") != (
        expected_summary.status == "closed"
    ):
        raise StrictKernelRPCProtocolError("kernel_state closed flag disagrees with status")
    if kernel.get("canonical_status") != "kernel_structured_state_chart_not_canonical":
        raise StrictKernelRPCProtocolError("kernel_state canonical status changed")
    if kernel.get("parent_state_id") != expected_summary.parent_state_id:
        raise StrictKernelRPCProtocolError("kernel_state parent differs from summary")
    if kernel.get("proof_prefix") != expected_summary.proof_prefix:
        raise StrictKernelRPCProtocolError("kernel_state prefix differs from summary")
    options = _obj(kernel.get("options"), "kernel_state.options")
    _exact(options, {"maxHeartbeats"}, "kernel_state.options")
    if options != U05_BASELINE_OPTIONS:
        raise StrictKernelRPCProtocolError("kernel_state heartbeat cap is not 20000")
    if expected_task is not None:
        if expected_summary.task_id != expected_task.task_id:
            raise StrictKernelRPCProtocolError("init task_id differs from request")
        if expected_summary.proof_prefix != expected_task.prefix:
            raise StrictKernelRPCProtocolError("init proof prefix differs from request")
        if expected_summary.parent_state_id is not None:
            raise StrictKernelRPCProtocolError("initial state unexpectedly has a parent")
    validation_kernel = kernel
    if not require_identity_status and expected_summary.status not in {"open", "closed"}:
        validation_kernel = dict(kernel)
        validation_kernel["status"] = "open"
        validation_kernel["closed"] = False
    try:
        state_identity_from_kernel_state(
            validation_kernel,
            environment_content_digest="0" * 64,
            baseline_semantic_options=U05_BASELINE_OPTIONS,
        )
    except StrictIdentityError as exc:
        raise StrictKernelRPCProtocolError(
            "kernel_state v3 identity validation failed"
        ) from exc
    return kernel


@dataclass(frozen=True)
class LoadProjectResponse:
    request_id: str
    session_id: str
    imports: tuple[str, ...]
    n_states: int

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        expected_request_id: str,
        expected_imports: Sequence[str],
    ) -> "LoadProjectResponse":
        obj = _obj(value, "load_project response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        parsed = _validate_envelope(
            obj,
            expected_request_id=expected_request_id,
            fields={"backend", "loaded", "imports", "session_id", "n_states"},
        )
        imports = _string_tuple(parsed["imports"], "load_project imports", nonempty=True)
        if imports != tuple(expected_imports):
            raise StrictKernelRPCProtocolError("loaded imports differ from request")
        if parsed["backend"] != KERNEL_RPC_BACKEND or parsed["loaded"] is not True:
            raise StrictKernelRPCProtocolError("load_project did not bind the kernel backend")
        return cls(
            request_id=expected_request_id,
            session_id=_str(parsed["session_id"], "session_id"),  # type: ignore[arg-type]
            imports=imports,
            n_states=_int(parsed["n_states"], "n_states"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class InitStateResponse:
    request_id: str
    summary: KernelStateSummary
    kernel_state: Mapping[str, Any]

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        expected_request_id: str,
        expected_task: U05TaskSpec,
    ) -> "InitStateResponse":
        obj = _obj(value, "init_state response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        parsed = _validate_envelope(
            obj,
            expected_request_id=expected_request_id,
            fields={"state", "kernel_state"},
        )
        summary = _parse_state_summary(
            parsed["state"], allowed_statuses=frozenset({"open", "closed"})
        )
        kernel = _validate_v3_kernel_state(
            parsed["kernel_state"],
            expected_summary=summary,
            expected_task=expected_task,
        )
        return cls(expected_request_id, summary, kernel)


@dataclass(frozen=True)
class StatusResponse:
    request_id: str
    session_id: str
    loaded: bool
    imports: tuple[str, ...]
    n_states: int
    n_requests: int
    n_failures: int
    n_primary_executions: int
    n_replay_executions: int

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        expected_request_id: str,
        expected_session_id: str | None = None,
        expected_imports: Sequence[str] | None = None,
    ) -> "StatusResponse":
        obj = _obj(value, "status response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        parsed = _validate_envelope(
            obj,
            expected_request_id=expected_request_id,
            fields={
                "backend",
                "loaded",
                "session_id",
                "n_states",
                "n_requests",
                "n_failures",
                "n_primary_executions",
                "n_replay_executions",
                "imports",
            },
        )
        if parsed["backend"] != KERNEL_RPC_BACKEND:
            raise StrictKernelRPCProtocolError("status backend changed")
        loaded = _bool(parsed["loaded"], "status.loaded")
        session_id = _str(parsed["session_id"], "status.session_id")
        imports = _string_tuple(parsed["imports"], "status imports", nonempty=True)
        if expected_session_id is not None and session_id != expected_session_id:
            raise StrictKernelRPCProtocolError("status session differs from load_project")
        if expected_imports is not None and imports != tuple(expected_imports):
            raise StrictKernelRPCProtocolError("status imports differ from loaded imports")
        n_states = _int(parsed["n_states"], "status.n_states")
        n_requests = _int(parsed["n_requests"], "status.n_requests")
        n_failures = _int(parsed["n_failures"], "status.n_failures")
        n_primary = _int(
            parsed["n_primary_executions"], "status.n_primary_executions"
        )
        n_replay = _int(
            parsed["n_replay_executions"], "status.n_replay_executions"
        )
        assert None not in {
            n_states,
            n_requests,
            n_failures,
            n_primary,
            n_replay,
        }
        if n_failures > n_requests or n_primary > n_requests or n_replay > n_requests:
            raise StrictKernelRPCProtocolError("status counters violate request bounds")
        if n_primary != n_replay:
            raise StrictKernelRPCProtocolError("primary/replay execution counters diverged")
        return cls(
            request_id=expected_request_id,
            session_id=session_id,  # type: ignore[arg-type]
            loaded=loaded,
            imports=imports,
            n_states=n_states,  # type: ignore[arg-type]
            n_requests=n_requests,  # type: ignore[arg-type]
            n_failures=n_failures,  # type: ignore[arg-type]
            n_primary_executions=n_primary,  # type: ignore[arg-type]
            n_replay_executions=n_replay,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ShutdownResponse:
    request_id: str

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], *, expected_request_id: str
    ) -> "ShutdownResponse":
        obj = _obj(value, "shutdown response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        parsed = _validate_envelope(
            obj, expected_request_id=expected_request_id, fields={"shutdown"}
        )
        if parsed["shutdown"] is not True:
            raise StrictKernelRPCProtocolError("worker did not acknowledge shutdown")
        return cls(expected_request_id)


@dataclass(frozen=True)
class RawTargetBinding:
    requested_target_mvar_id: str | None
    requested_target_selector: str | None
    effective_target_mvar_id: str | None
    effective_target_goal_index: int | None
    source: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RawTargetBinding":
        obj = _obj(value, "target_binding")
        _exact(
            obj,
            {
                "requested_target_mvar_id",
                "requested_target_selector",
                "effective_target_mvar_id",
                "effective_target_goal_index",
                "source",
            },
            "target_binding",
        )
        result = cls(
            requested_target_mvar_id=_str(
                obj["requested_target_mvar_id"],
                "requested_target_mvar_id",
                optional=True,
            ),
            requested_target_selector=_str(
                obj["requested_target_selector"],
                "requested_target_selector",
                optional=True,
            ),
            effective_target_mvar_id=_str(
                obj["effective_target_mvar_id"],
                "effective_target_mvar_id",
                optional=True,
            ),
            effective_target_goal_index=_int(
                obj["effective_target_goal_index"],
                "effective_target_goal_index",
                optional=True,
            ),
            source=_str(obj["source"], "target_binding.source"),  # type: ignore[arg-type]
        )
        if result.requested_target_selector not in {None, "first", "last"}:
            raise StrictKernelRPCProtocolError("unknown requested target selector")
        if (result.effective_target_mvar_id is None) != (
            result.effective_target_goal_index is None
        ):
            raise StrictKernelRPCProtocolError("effective target fields are not jointly present")
        if result.source == "unresolved":
            if result.effective_target_mvar_id is not None:
                raise StrictKernelRPCProtocolError("unresolved target has an effective target")
        elif result.effective_target_mvar_id is None:
            raise StrictKernelRPCProtocolError("resolved target lacks effective target")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_target_mvar_id": self.requested_target_mvar_id,
            "requested_target_selector": self.requested_target_selector,
            "effective_target_mvar_id": self.effective_target_mvar_id,
            "effective_target_goal_index": self.effective_target_goal_index,
            "source": self.source,
        }


@dataclass(frozen=True)
class RawStateDelta:
    closed_goals: tuple[str, ...]
    new_goals: tuple[str, ...]
    assigned_mvars: tuple[str, ...]
    new_mvars: tuple[str, ...]
    before_goals: tuple[str, ...]
    after_goals: tuple[str, ...]
    before_mvars: tuple[str, ...]
    after_mvars: tuple[str, ...]
    before_assigned_mvars: tuple[str, ...]
    after_assigned_mvars: tuple[str, ...]
    minimal_support: Mapping[str, Any]

    @staticmethod
    def _names(value: Any, where: str) -> tuple[str, ...]:
        names = tuple(_str(item, where) for item in _arr(value, where))
        if len(names) != len(set(names)):
            raise StrictKernelRPCProtocolError(f"{where} has duplicates")
        return names  # type: ignore[return-value]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RawStateDelta":
        obj = _obj(value, "state_delta")
        names = {
            "closed_goals",
            "new_goals",
            "assigned_mvars",
            "new_mvars",
            "before_goals",
            "after_goals",
            "before_mvars",
            "after_mvars",
            "before_assigned_mvars",
            "after_assigned_mvars",
        }
        _exact(obj, names | {"minimal_support"}, "state_delta")
        delta = cls(
            **{name: cls._names(obj[name], f"state_delta.{name}") for name in names},
            minimal_support=_obj(obj["minimal_support"], "minimal_support"),
        )
        if set(delta.closed_goals) != set(delta.before_goals) - set(delta.after_goals):
            raise StrictKernelRPCProtocolError("closed_goals is not an exact difference")
        if set(delta.new_goals) != set(delta.after_goals) - set(delta.before_goals):
            raise StrictKernelRPCProtocolError("new_goals is not an exact difference")
        if set(delta.new_mvars) != set(delta.after_mvars) - set(delta.before_mvars):
            raise StrictKernelRPCProtocolError("new_mvars is not an exact difference")
        if set(delta.assigned_mvars) != set(delta.after_assigned_mvars) - set(
            delta.before_assigned_mvars
        ):
            raise StrictKernelRPCProtocolError(
                "assigned_mvars is cumulative rather than an exact difference"
            )
        return delta

    def to_dict(self) -> dict[str, Any]:
        return {
            "closed_goals": list(self.closed_goals),
            "new_goals": list(self.new_goals),
            "assigned_mvars": list(self.assigned_mvars),
            "new_mvars": list(self.new_mvars),
            "before_goals": list(self.before_goals),
            "after_goals": list(self.after_goals),
            "before_mvars": list(self.before_mvars),
            "after_mvars": list(self.after_mvars),
            "before_assigned_mvars": list(self.before_assigned_mvars),
            "after_assigned_mvars": list(self.after_assigned_mvars),
            "minimal_support": dict(self.minimal_support),
        }


_COMPARABLE_FIELDS = {
    "semantic_status",
    "post_kernel_state",
    "state_delta",
    "action_id",
    "target_binding",
    "budget",
    "normalized_failure_class",
}


@dataclass(frozen=True)
class RawReplayCertificate:
    replay_status: str
    reexecution_performed: bool
    verification_method: str
    semantic_response_match: bool
    post_state_match: bool
    delta_match: bool
    target_match: bool
    cap_match: bool
    error: str | None
    primary_comparable: Mapping[str, Any]
    replay_comparable: Mapping[str, Any] | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RawReplayCertificate":
        obj = _obj(value, "replay")
        fields = {
            "schema_version",
            "replay_status",
            "reexecution_performed",
            "verification_method",
            "semantic_response_match",
            "post_state_match",
            "delta_match",
            "target_match",
            "cap_match",
            "error",
            "primary_comparable",
            "replay_comparable",
        }
        _exact(obj, fields, "replay")
        if obj["schema_version"] != REPLAY_VERIFICATION_SCHEMA:
            raise StrictKernelRPCProtocolError("wrong U05 replay schema")
        primary = cls._comparable(obj["primary_comparable"], "primary_comparable")
        replay = (
            None
            if obj["replay_comparable"] is None
            else cls._comparable(obj["replay_comparable"], "replay_comparable")
        )
        result = cls(
            replay_status=_str(obj["replay_status"], "replay_status"),  # type: ignore[arg-type]
            reexecution_performed=_bool(
                obj["reexecution_performed"], "reexecution_performed"
            ),
            verification_method=_str(
                obj["verification_method"], "verification_method"
            ),  # type: ignore[arg-type]
            semantic_response_match=_bool(
                obj["semantic_response_match"], "semantic_response_match"
            ),
            post_state_match=_bool(obj["post_state_match"], "post_state_match"),
            delta_match=_bool(obj["delta_match"], "delta_match"),
            target_match=_bool(obj["target_match"], "target_match"),
            cap_match=_bool(obj["cap_match"], "cap_match"),
            error=_str(obj["error"], "replay.error", optional=True),
            primary_comparable=primary,
            replay_comparable=replay,
        )
        if result.replay_status not in {"verified", "mismatch"}:
            raise StrictKernelRPCProtocolError("unknown replay status")
        flags = (
            result.reexecution_performed,
            result.semantic_response_match,
            result.post_state_match,
            result.delta_match,
            result.target_match,
            result.cap_match,
        )
        if result.replay_status == "verified":
            if not all(flags) or result.error is not None or replay is None:
                raise StrictKernelRPCProtocolError("verified replay has incomplete evidence")
            if canonical_json_bytes(primary) != canonical_json_bytes(replay):
                raise StrictKernelRPCProtocolError("verified replay comparables differ")
        return result

    @staticmethod
    def _comparable(value: Any, where: str) -> dict[str, Any]:
        obj = _obj(value, where)
        _exact(obj, _COMPARABLE_FIELDS, where)
        _str(obj["semantic_status"], f"{where}.semantic_status")
        _obj(obj["post_kernel_state"], f"{where}.post_kernel_state")
        if obj["state_delta"] is not None:
            RawStateDelta.from_dict(_obj(obj["state_delta"], f"{where}.state_delta"))
        _str(obj["action_id"], f"{where}.action_id")
        RawTargetBinding.from_dict(_obj(obj["target_binding"], f"{where}.target_binding"))
        try:
            CapSemantics.from_dict(_obj(obj["budget"], f"{where}.budget"), native=True)
        except StrictContractError as exc:
            raise StrictKernelRPCProtocolError(f"invalid {where} budget") from exc
        _str(
            obj["normalized_failure_class"],
            f"{where}.normalized_failure_class",
            optional=True,
        )
        return obj

    @property
    def verified(self) -> bool:
        return self.replay_status == "verified"


@dataclass(frozen=True)
class U05ApplyResponse:
    request_id: str
    action_id: str
    wire_status: str
    status: str
    normalized_failure_class: str | None
    censor_reason: str | None
    before_state_id: str
    after_state_id: str
    after_state_retained: bool
    target_mvar_id: str | None
    target_binding: RawTargetBinding
    budget: CapSemantics
    state_delta: RawStateDelta
    kernel_state_before: Mapping[str, Any]
    kernel_state_after: Mapping[str, Any]
    replay: RawReplayCertificate
    messages: tuple[str, ...]
    elapsed_ms: int

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        expected_request_id: str,
        expected_state_id: str,
        expected_action: Mapping[str, Any],
        expected_target_mvar_id: str | None = None,
    ) -> "U05ApplyResponse":
        obj = _obj(value, "apply_tactic response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        status = obj.get("status")
        if status in {"success", "partial", "censor"}:
            variant = {"censor_reason"}
        elif status in {"failure", "timeout"}:
            variant = {"normalized_failure_class"}
        else:
            raise StrictKernelRPCProtocolError("unknown apply_tactic status")
        common = {
            "u05_semantics_version",
            "status",
            "before_state_id",
            "after_state_id",
            "after_state_retained",
            "target_mvar_id",
            "target_binding",
            "budget",
            "state_delta",
            "kernel_state_before",
            "kernel_state_after",
            "kernel_state",
            "state",
            "audit",
            "replay",
            "replay_certificate",
            "messages",
            "elapsed_ms",
            "heartbeats",
        }
        parsed = _validate_envelope(
            obj,
            expected_request_id=expected_request_id,
            fields=common | variant,
        )
        if parsed["ok"] is not True:
            raise StrictKernelRPCProtocolError("apply_tactic ok field is not true")
        if parsed["u05_semantics_version"] != U05_SEMANTICS_VERSION:
            raise StrictKernelRPCProtocolError("wrong U05 RPC semantics version")
        action = _obj(expected_action, "expected action")
        _exact(action, _APPLY_ACTION_FIELDS, "expected action")
        expected_action_id = _str(action["action_id"], "expected action_id")
        expected_selector = _str(action["target_selector"], "expected target_selector")
        if expected_selector not in {"first", "last"}:
            raise StrictKernelRPCProtocolError("expected selector is outside U05")
        if _int(action["max_heartbeats"], "expected max_heartbeats") != 20_000:
            raise StrictKernelRPCProtocolError("expected action cap is not frozen at 20000")
        if parsed["before_state_id"] != expected_state_id:
            raise StrictKernelRPCProtocolError("response before_state_id differs from request")
        binding = RawTargetBinding.from_dict(
            _obj(parsed["target_binding"], "target_binding")
        )
        if binding.requested_target_selector != expected_selector:
            raise StrictKernelRPCProtocolError("response target selector differs from request")
        if binding.requested_target_mvar_id != expected_target_mvar_id:
            raise StrictKernelRPCProtocolError("response requested target differs from request")
        if expected_target_mvar_id is not None and (
            binding.effective_target_mvar_id != expected_target_mvar_id
        ):
            raise StrictKernelRPCProtocolError("explicit request target was not effective")
        try:
            budget = CapSemantics.from_dict(_obj(parsed["budget"], "budget"), native=True)
        except StrictContractError as exc:
            raise StrictKernelRPCProtocolError("invalid explicit U05 budget") from exc
        delta = RawStateDelta.from_dict(_obj(parsed["state_delta"], "state_delta"))
        replay = RawReplayCertificate.from_dict(_obj(parsed["replay"], "replay"))
        if canonical_json_bytes(parsed["replay"]) != canonical_json_bytes(
            parsed["replay_certificate"]
        ):
            raise StrictKernelRPCProtocolError("replay aliases differ")
        before = cls._kernel_state(parsed["kernel_state_before"], "kernel_state_before")
        after = cls._kernel_state(parsed["kernel_state_after"], "kernel_state_after")
        if canonical_json_bytes(after) != canonical_json_bytes(parsed["kernel_state"]):
            raise StrictKernelRPCProtocolError("kernel_state alias differs from after state")
        state_summary = _parse_state_summary(
            parsed["state"],
            allowed_statuses=frozenset({"open", "closed", "failed", "timeout"}),
        )
        audit, audit_flags = cls._audit(parsed["audit"])
        if status in {"success", "partial"}:
            if "heartbeats" not in audit or audit["heartbeats"] is not None:
                raise StrictKernelRPCProtocolError(
                    "success audit must retain the null legacy heartbeat field"
                )
        elif status in {"failure", "timeout"} and "heartbeats" in audit:
            raise StrictKernelRPCProtocolError(
                "failure audit must omit the legacy heartbeat field"
            )
        expected_audit_status = {
            "success": "success",
            "partial": "partial",
            "failure": "fail",
            "timeout": "timeout",
            "censor": "fail",
        }[status]
        if audit.get("status") != expected_audit_status:
            raise StrictKernelRPCProtocolError("audit status differs from wire status")
        messages = tuple(_str(item, "message") for item in _arr(parsed["messages"], "messages"))
        target_id = _str(parsed["target_mvar_id"], "target_mvar_id", optional=True)
        if target_id != binding.effective_target_mvar_id:
            raise StrictKernelRPCProtocolError("top-level target differs from target_binding")
        before_goals = _arr(before.get("goals"), "kernel_state_before.goals")
        if binding.effective_target_goal_index is not None:
            index = binding.effective_target_goal_index
            if index >= len(before_goals):
                raise StrictKernelRPCProtocolError("effective target index is outside before goals")
            goal = _obj(before_goals[index], "before goal")
            if goal.get("mvar_id") != binding.effective_target_mvar_id:
                raise StrictKernelRPCProtocolError("effective target does not name indexed goal")
            expected_index = 0 if expected_selector == "first" else len(before_goals) - 1
            if index != expected_index:
                raise StrictKernelRPCProtocolError("effective target violates symbolic selector")
        retained = _bool(parsed["after_state_retained"], "after_state_retained")
        censor_reason = (
            _str(parsed["censor_reason"], "censor_reason", optional=True)
            if "censor_reason" in parsed
            else None
        )
        failure_class = (
            _str(
                parsed["normalized_failure_class"],
                "normalized_failure_class",
                optional=True,
            )
            if "normalized_failure_class" in parsed
            else None
        )
        if status == "censor":
            if retained or replay.verified or censor_reason != "replay_mismatch":
                raise StrictKernelRPCProtocolError("replay censor has inconsistent retention")
        elif status in {"success", "partial"}:
            if not retained or not replay.verified or censor_reason is not None:
                raise StrictKernelRPCProtocolError("successful transition lacks verified retention")
        elif retained or not replay.verified:
            raise StrictKernelRPCProtocolError(
                "failure/timeout must be replay-verified and unretained"
            )
        if status == "timeout" and failure_class != "heartbeat_exhaustion":
            raise StrictKernelRPCProtocolError("timeout lacks heartbeat-exhaustion class")
        if parsed["heartbeats"] is not None:
            raise StrictKernelRPCProtocolError("legacy heartbeat field must remain null")

        primary = _obj(replay.primary_comparable, "primary comparable")
        if primary["action_id"] != expected_action_id:
            raise StrictKernelRPCProtocolError("replay action_id differs from request")
        if not _json_equal(primary["target_binding"], parsed["target_binding"]):
            raise StrictKernelRPCProtocolError("top target binding differs from replay primary")
        if not _json_equal(primary["budget"], parsed["budget"]):
            raise StrictKernelRPCProtocolError("top budget differs from replay primary")
        failure_like = status in {"failure", "timeout"} or (
            status == "censor" and primary["state_delta"] is None
        )
        if not failure_like:
            if not _json_equal(primary["state_delta"], strip_replay_transport(parsed["state_delta"])):
                raise StrictKernelRPCProtocolError("top delta differs from replay primary")
            if not _json_equal(
                primary["post_kernel_state"], strip_replay_transport(after)
            ):
                raise StrictKernelRPCProtocolError("after state differs from replay primary")
            expected_semantic_status = "closed" if after.get("status") == "closed" else "open"
            if primary["semantic_status"] != expected_semantic_status:
                raise StrictKernelRPCProtocolError("replay semantic status differs from after state")
        else:
            if primary["state_delta"] is not None:
                raise StrictKernelRPCProtocolError("ordinary/resource failure replay delta must be null")
            if not _json_equal(
                primary["post_kernel_state"], strip_replay_transport(before)
            ):
                raise StrictKernelRPCProtocolError("failure replay post-state differs from before state")
            primary_failure_class = _str(
                primary["normalized_failure_class"],
                "primary normalized_failure_class",
            )
            if primary["semantic_status"] != primary_failure_class:
                raise StrictKernelRPCProtocolError("failure comparable status/class disagree")
            if failure_class is not None and primary_failure_class != failure_class:
                raise StrictKernelRPCProtocolError("failure class differs from replay primary")

        mirror_pairs = (
            (audit_flags["kernel_state_before"], parsed["kernel_state_before"], "audit before state"),
            (audit_flags["kernel_state_after"], parsed["kernel_state_after"], "audit after state"),
            (audit_flags["state_delta"], parsed["state_delta"], "audit delta"),
            (audit_flags["replay"], parsed["replay"], "audit replay"),
            (audit_flags["heartbeat_telemetry"], parsed["budget"], "audit budget"),
            (audit_flags["target_binding"], parsed["target_binding"], "audit target"),
        )
        for left, right, label in mirror_pairs:
            if not _json_equal(left, right):
                raise StrictKernelRPCProtocolError(f"{label} does not mirror top-level evidence")
        if audit["state_id"] != expected_state_id or audit["action_id"] != expected_action_id:
            raise StrictKernelRPCProtocolError("audit request identity does not mirror request")
        if audit["elapsed_ms"] != parsed["elapsed_ms"] or audit["messages"] != parsed["messages"]:
            raise StrictKernelRPCProtocolError("audit telemetry/messages do not mirror top level")
        if audit_flags["before_persistent_state_id"] != expected_state_id:
            raise StrictKernelRPCProtocolError("audit before persistent state differs from request")
        expected_after_persistent = parsed["after_state_id"] if retained else None
        if audit_flags["after_persistent_state_id"] != expected_after_persistent:
            raise StrictKernelRPCProtocolError("audit after-state retention mirror is false")
        if state_summary.state_id != parsed["after_state_id"]:
            raise StrictKernelRPCProtocolError("state summary differs from after_state_id")

        if before.get("state_id") != expected_state_id:
            raise StrictKernelRPCProtocolError("before kernel state differs from request")
        if before.get("status") != "open" or before.get("closed") is not False:
            raise StrictKernelRPCProtocolError("apply source must be a coherent open state")
        before_options = _obj(before.get("options"), "kernel_state_before.options")
        _exact(before_options, {"maxHeartbeats"}, "kernel_state_before.options")
        if before_options != U05_BASELINE_OPTIONS:
            raise StrictKernelRPCProtocolError("source state heartbeat cap is not 20000")
        try:
            state_identity_from_kernel_state(
                before,
                environment_content_digest="0" * 64,
                baseline_semantic_options=U05_BASELINE_OPTIONS,
            )
        except StrictIdentityError as exc:
            raise StrictKernelRPCProtocolError("source kernel-state v3 is incomplete") from exc
        after = _validate_v3_kernel_state(
            after,
            expected_summary=state_summary,
            require_identity_status=status in {"success", "partial"},
        )
        if after.get("parent_state_id") != expected_state_id:
            raise StrictKernelRPCProtocolError("after kernel state parent differs from source")
        if after.get("task_id") != before.get("task_id"):
            raise StrictKernelRPCProtocolError("transition changed task identity")
        if status == "success" and state_summary.status != "closed":
            raise StrictKernelRPCProtocolError("success did not produce a closed state")
        if status == "partial" and state_summary.status != "open":
            raise StrictKernelRPCProtocolError("partial did not produce an open state")
        if status == "failure" and state_summary.status != "failed":
            raise StrictKernelRPCProtocolError("failure state status changed")
        if status == "timeout" and state_summary.status != "timeout":
            raise StrictKernelRPCProtocolError("timeout state status changed")

        admitted_status = status
        admitted_censor = censor_reason
        if status == "timeout":
            admitted_status = "censor"
            admitted_censor = "heartbeat_exhaustion"
        elif status == "failure" and not replay.verified:
            admitted_status = "censor"
            admitted_censor = "replay_mismatch"
        return cls(
            request_id=expected_request_id,
            action_id=expected_action_id,  # type: ignore[arg-type]
            wire_status=status,
            status=admitted_status,
            normalized_failure_class=failure_class,
            censor_reason=admitted_censor,
            before_state_id=_str(parsed["before_state_id"], "before_state_id"),  # type: ignore[arg-type]
            after_state_id=_str(parsed["after_state_id"], "after_state_id"),  # type: ignore[arg-type]
            after_state_retained=retained,
            target_mvar_id=target_id,
            target_binding=binding,
            budget=budget,
            state_delta=delta,
            kernel_state_before=before,
            kernel_state_after=after,
            replay=replay,
            messages=messages,  # type: ignore[arg-type]
            elapsed_ms=_int(parsed["elapsed_ms"], "elapsed_ms"),  # type: ignore[arg-type]
        )

    @staticmethod
    def _kernel_state(value: Any, where: str) -> dict[str, Any]:
        obj = _obj(value, where)
        if obj.get("schema_version") != LEGACY_KERNEL_STATE_SCHEMA_VERSION:
            raise StrictKernelRPCProtocolError(f"{where} is not kernel-state v3")
        return obj

    @staticmethod
    def _state_summary(value: Any) -> dict[str, Any]:
        obj = _obj(value, "state summary")
        _exact(
            obj,
            {
                "state_id",
                "task_id",
                "status",
                "goal_count",
                "parent_state_id",
                "proof_prefix",
                "canonical_status",
            },
            "state summary",
        )
        return obj

    @staticmethod
    def _audit(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        obj = _obj(value, "audit")
        success_fields = {
            "task_id",
            "state_id",
            "action_id",
            "status",
            "elapsed_ms",
            "heartbeats",
            "stdout",
            "stderr",
            "messages",
            "after_state",
            "audit_flags",
        }
        failure_fields = success_fields - {"heartbeats"}
        if frozenset(obj) not in {frozenset(success_fields), frozenset(failure_fields)}:
            raise StrictKernelRPCProtocolError("audit has unknown or missing fields")
        flags = _obj(obj["audit_flags"], "audit_flags")
        _exact(
            flags,
            {
                "kernel_rpc_worker",
                "execution_backend",
                "kernel_state_before",
                "kernel_state_after",
                "state_delta",
                "replay",
                "heartbeat_telemetry",
                "target_binding",
                "before_persistent_state_id",
                "after_persistent_state_id",
            },
            "audit_flags",
        )
        return obj, flags


@dataclass(frozen=True)
class DiscardStateResponse:
    request_id: str
    state_id: str
    n_states_before: int
    n_states_after: int

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        expected_request_id: str,
        expected_state_id: str,
    ) -> "DiscardStateResponse":
        obj = _obj(value, "discard_state response")
        if obj.get("ok") is False:
            raise_for_rpc_error(obj, expected_request_id=expected_request_id)
        parsed = _validate_envelope(
            obj,
            expected_request_id=expected_request_id,
            fields={
                "u05_semantics_version",
                "state_id",
                "discarded",
                "n_states_before",
                "n_states_after",
            },
        )
        if parsed["u05_semantics_version"] != U05_SEMANTICS_VERSION:
            raise StrictKernelRPCProtocolError("wrong discard semantics version")
        if parsed["state_id"] != expected_state_id:
            raise StrictKernelRPCProtocolError("discarded state differs from request")
        if parsed["discarded"] is not True:
            raise StrictKernelRPCProtocolError("discard_state did not discard")
        before = _int(parsed["n_states_before"], "n_states_before")
        after = _int(parsed["n_states_after"], "n_states_after")
        assert before is not None and after is not None
        if before != after + 1:
            raise StrictKernelRPCProtocolError("discard_state count did not decrease by one")
        return cls(
            request_id=expected_request_id,
            state_id=_str(parsed["state_id"], "state_id"),  # type: ignore[arg-type]
            n_states_before=before,
            n_states_after=after,
        )


def parse_apply_tactic_response(
    raw: bytes | str | Mapping[str, Any],
    *,
    expected_request_id: str,
    expected_state_id: str,
    expected_action: Mapping[str, Any],
    expected_target_mvar_id: str | None = None,
) -> U05ApplyResponse:
    value = parse_strict_json_line(raw) if type(raw) in (bytes, str) else _obj(raw, "response")
    return U05ApplyResponse.from_dict(
        value,
        expected_request_id=expected_request_id,
        expected_state_id=expected_state_id,
        expected_action=expected_action,
        expected_target_mvar_id=expected_target_mvar_id,
    )


def parse_discard_state_response(
    raw: bytes | str | Mapping[str, Any],
    *,
    expected_request_id: str,
    expected_state_id: str,
) -> DiscardStateResponse:
    value = parse_strict_json_line(raw) if type(raw) in (bytes, str) else _obj(raw, "response")
    return DiscardStateResponse.from_dict(
        value,
        expected_request_id=expected_request_id,
        expected_state_id=expected_state_id,
    )


def parse_load_project_response(
    raw: bytes | str | Mapping[str, Any],
    *,
    expected_request_id: str,
    expected_imports: Sequence[str],
) -> LoadProjectResponse:
    return LoadProjectResponse.from_dict(
        _response_value(raw),
        expected_request_id=expected_request_id,
        expected_imports=expected_imports,
    )


def parse_init_state_response(
    raw: bytes | str | Mapping[str, Any],
    *,
    expected_request_id: str,
    expected_task: U05TaskSpec,
) -> InitStateResponse:
    return InitStateResponse.from_dict(
        _response_value(raw),
        expected_request_id=expected_request_id,
        expected_task=expected_task,
    )


def parse_status_response(
    raw: bytes | str | Mapping[str, Any],
    *,
    expected_request_id: str,
    expected_session_id: str | None = None,
    expected_imports: Sequence[str] | None = None,
) -> StatusResponse:
    return StatusResponse.from_dict(
        _response_value(raw),
        expected_request_id=expected_request_id,
        expected_session_id=expected_session_id,
        expected_imports=expected_imports,
    )


def parse_shutdown_response(
    raw: bytes | str | Mapping[str, Any], *, expected_request_id: str
) -> ShutdownResponse:
    return ShutdownResponse.from_dict(
        _response_value(raw), expected_request_id=expected_request_id
    )


def _request_imports(imports: Sequence[str]) -> tuple[str, ...]:
    if isinstance(imports, (str, bytes)):
        raise StrictKernelRPCProtocolError("imports must be an ordered sequence")
    rows = tuple(imports)
    if not rows or any(type(item) is not str or not item for item in rows):
        raise StrictKernelRPCProtocolError("imports must contain nonempty strings")
    if len(rows) != len(set(rows)):
        raise StrictKernelRPCProtocolError("imports contain duplicates")
    return rows


def strict_load_project_request_bytes(
    *, request_id: str, imports: Sequence[str]
) -> bytes:
    _str(request_id, "request_id")
    rows = _request_imports(imports)
    return canonical_json_bytes(
        {"id": request_id, "cmd": "load_project", "imports": list(rows)}
    ) + b"\n"


def strict_init_state_request_bytes(
    *, request_id: str, task: U05TaskSpec
) -> bytes:
    _str(request_id, "request_id")
    if not isinstance(task, U05TaskSpec):
        raise StrictKernelRPCProtocolError("init task must be a strict U05TaskSpec")
    return canonical_json_bytes(
        {"id": request_id, "cmd": "init_state", "task": task.to_rpc_dict()}
    ) + b"\n"


def strict_status_request_bytes(*, request_id: str) -> bytes:
    _str(request_id, "request_id")
    return canonical_json_bytes({"id": request_id, "cmd": "status"}) + b"\n"


def strict_shutdown_request_bytes(*, request_id: str) -> bytes:
    _str(request_id, "request_id")
    return canonical_json_bytes({"id": request_id, "cmd": "shutdown"}) + b"\n"


def strict_discard_request_bytes(*, request_id: str, state_id: str) -> bytes:
    _str(request_id, "request_id")
    _str(state_id, "state_id")
    return canonical_json_bytes(
        {"id": request_id, "cmd": "discard_state", "state_id": state_id}
    ) + b"\n"


_APPLY_ACTION_FIELDS = {
    "action_id",
    "tactic",
    "target_selector",
    "max_heartbeats",
}


def strict_apply_request_bytes(
    *,
    request_id: str,
    state_id: str,
    action: Mapping[str, Any],
    target_mvar_id: str | None = None,
) -> bytes:
    """Build one exact cache-bypassed U05 apply request plus trailing LF."""

    _str(request_id, "request_id")
    _str(state_id, "state_id")
    action_obj = _obj(action, "action")
    _exact(action_obj, _APPLY_ACTION_FIELDS, "action")
    _str(action_obj["action_id"], "action.action_id")
    _str(action_obj["tactic"], "action.tactic")
    if action_obj["target_selector"] not in {"first", "last"}:
        raise StrictKernelRPCProtocolError("action target_selector must be first or last")
    heartbeat = _int(action_obj["max_heartbeats"], "action.max_heartbeats")
    if heartbeat != 20_000:
        raise StrictKernelRPCProtocolError("U05 action heartbeat cap must be 20000")
    request: dict[str, Any] = {
        "id": request_id,
        "cmd": "apply_tactic",
        "state_id": state_id,
        "action": dict(action_obj),
    }
    if target_mvar_id is not None:
        request["target_mvar_id"] = _str(target_mvar_id, "target_mvar_id")
    return canonical_json_bytes(request) + b"\n"


class TimedJSONLTransport(Protocol):
    def round_trip(
        self, request: bytes, *, timeout_seconds: float
    ) -> bytes | str: ...


_TRANSPORT_EOF = object()


class SynchronousJSONLSubprocessTransport:
    """One-process, one-request-at-a-time binary JSONL transport.

    A daemon reader prevents a blocking ``readline`` from defeating the
    caller's wall deadline.  Any timeout makes the process unusable and stops
    it, so a late line can never be mistaken for the next response.
    """

    def __init__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | os.PathLike[str] | None = None,
        env: Mapping[str, str] | None = None,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        stderr_chunks: int = 32,
    ) -> None:
        if isinstance(argv, (str, bytes)):
            raise ValueError("argv must be an ordered argument sequence")
        args = tuple(argv)
        if not args or any(type(arg) is not str or not arg for arg in args):
            raise ValueError("argv must contain nonempty strings")
        if type(stderr_chunks) is not int or stderr_chunks < 1:
            raise ValueError("stderr_chunks must be a positive integer")
        self._process = popen_factory(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=None if env is None else dict(env),
            bufsize=0,
        )
        if (
            self._process.stdin is None
            or self._process.stdout is None
            or self._process.stderr is None
        ):
            raise KernelRPCTransportError("worker pipes were not created")
        self._responses: queue.Queue[bytes | object] = queue.Queue()
        self._stderr_tail: deque[bytes] = deque(maxlen=stderr_chunks)
        self._lock = threading.Lock()
        self._closed = False
        self._stdout_thread = threading.Thread(
            target=self._read_stdout,
            name="lean-rgc-kernel-rpc-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr,
            name="lean-rgc-kernel-rpc-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    @property
    def stderr_tail(self) -> bytes:
        return b"".join(tuple(self._stderr_tail))

    @property
    def returncode(self) -> int | None:
        return self._process.poll()

    def _read_stdout(self) -> None:
        try:
            while True:
                line = self._process.stdout.readline()
                if line in {b"", ""}:
                    break
                if type(line) is not bytes:
                    self._responses.put(_TRANSPORT_EOF)
                    return
                self._responses.put(line)
        finally:
            self._responses.put(_TRANSPORT_EOF)

    def _read_stderr(self) -> None:
        try:
            while True:
                chunk = self._process.stderr.read(4096)
                if chunk in {b"", ""}:
                    return
                if type(chunk) is bytes:
                    self._stderr_tail.append(chunk)
        except (OSError, ValueError):
            return

    @staticmethod
    def _deadline(value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return float(value)

    def _stop_locked(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._process.stdin.close()
        except (OSError, ValueError):
            pass
        if self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass
        try:
            self._process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                self._process.kill()
            except OSError:
                pass
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass

    def round_trip(self, request: bytes, *, timeout_seconds: float) -> bytes:
        timeout = self._deadline(timeout_seconds)
        if type(request) is not bytes or not request.endswith(b"\n"):
            raise KernelRPCTransportError("request must be one LF-terminated byte line")
        if b"\n" in request[:-1] or b"\r" in request:
            raise KernelRPCTransportError("request contains more than one JSONL line")
        with self._lock:
            if self._closed:
                raise KernelRPCTransportError("worker transport is closed")
            if self._process.poll() is not None:
                code = self._process.returncode
                self._stop_locked()
                raise KernelRPCProcessExited(
                    f"worker exited with code {code}"
                )
            try:
                self._process.stdin.write(request)
                self._process.stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                self._stop_locked()
                raise KernelRPCProcessExited("worker stdin closed during request") from exc
            try:
                response = self._responses.get(timeout=timeout)
            except queue.Empty as exc:
                self._stop_locked()
                raise KernelRPCTransportTimeout(
                    f"worker response exceeded {timeout:g} seconds"
                ) from exc
            if response is _TRANSPORT_EOF:
                code = self._process.poll()
                self._stop_locked()
                raise KernelRPCProcessExited(
                    f"worker stdout closed before response (code={code})"
                )
            assert type(response) is bytes
            if not response.endswith(b"\n") or b"\n" in response[:-1]:
                self._stop_locked()
                raise KernelRPCTransportError("worker emitted a non-JSONL response")
            return response

    def finish_clean_shutdown(self, *, timeout_seconds: float) -> None:
        """Wait for natural exit after a validated shutdown acknowledgement."""

        timeout = self._deadline(timeout_seconds)
        with self._lock:
            if self._closed:
                if self._process.poll() is None:
                    raise KernelRPCTransportError("closed transport still has a live worker")
                return
            try:
                self._process.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                self._stop_locked()
                raise KernelRPCTransportTimeout(
                    "worker did not exit after shutdown acknowledgement"
                ) from exc
            self._closed = True
            if self._process.returncode != 0:
                raise KernelRPCProcessExited(
                    f"worker exited nonzero after shutdown: {self._process.returncode}"
                )

    def close(self) -> None:
        with self._lock:
            self._stop_locked()

    def __enter__(self) -> "SynchronousJSONLSubprocessTransport":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()


@dataclass(frozen=True)
class RuntimeStateView:
    identity: StateIdentityKey
    debt: DebtReadout
    state_view: StateView
    live_rpc_state_id: str
    runtime_goal_mvar_ids: tuple[str, ...]
    runtime_local_fvar_ids_by_goal: tuple[tuple[str, ...], ...]

    def bind_action(self, symbol: ActionSymbol) -> BoundAction:
        if not isinstance(symbol, ActionSymbol):
            raise StrictContractError("runtime binding requires an ActionSymbol")
        target = 0 if symbol.target_selector.value == "first" else -1
        return BoundAction.bind_to_state(
            symbol,
            self.identity,
            runtime_goal_mvar_ids=self.runtime_goal_mvar_ids,
            runtime_local_fvar_ids=self.runtime_local_fvar_ids_by_goal[target],
        )


def occurrence_response_signature(kernel_state: Mapping[str, Any]) -> bytes:
    """Independent alpha/path-invariant OPEN response used by KP1 ``P_raw``.

    The five debt coordinates are already implied by ``StateIdentityKey`` and
    cannot audit that identity.  This projection instead uses the native
    redundant goal readouts that are deliberately excluded from exact state
    identity, while excluding process IDs, proof history, rendered names,
    hashes, action/delta/replay data, and transport metadata.
    """

    kernel = _obj(kernel_state, "kernel_state")
    if kernel.get("status") != "open" or kernel.get("closed") is not False:
        raise StrictKernelRPCProtocolError(
            "occurrence response is defined only for an open state"
        )
    # Messages are explicitly transport/diagnostic material. Validate their
    # container through the strict v3 parser, but never admit them to P_raw.
    _arr(kernel.get("messages"), "kernel_state.messages")
    connective_fields = {"forall", "exists", "and", "or", "imp", "eq"}
    rows: list[dict[str, Any]] = []
    for ordinal, raw_goal in enumerate(_arr(kernel.get("goals"), "kernel_state.goals")):
        goal = _obj(raw_goal, "kernel goal")
        domain_tags = [
            _str(value, "goal.domain_tags item")
            for value in _arr(goal.get("domain_tags"), "goal.domain_tags")
        ]
        counts = _obj(goal.get("connective_counts"), "goal.connective_counts")
        _exact(counts, connective_fields, "goal.connective_counts")
        connective_counts = {
            key: _int(counts[key], f"goal.connective_counts.{key}")
            for key in sorted(connective_fields)
        }
        carrier_atoms = [
            _str(value, "goal.carrier_atoms_readout item")
            for value in _arr(
                goal.get("carrier_atoms_readout"), "goal.carrier_atoms_readout"
            )
        ]
        rows.append(
            {
                "ordinal": ordinal,
                "relation": _plain_str(goal.get("relation"), "goal.relation"),
                "domain_tags": domain_tags,
                "connective_counts": connective_counts,
                "carrier_atoms_readout": carrier_atoms,
            }
        )
    return canonical_json_bytes(
        {
            "schema": "lean-rgc-u05-occurrence-response-v1",
            "status": "open",
            "goals": rows,
        }
    )


def build_runtime_state_view(
    kernel_state: Mapping[str, Any],
    *,
    environment_content_digest: str,
    live_rpc_state_id: str,
) -> RuntimeStateView:
    """Bind a complete open v3 state to its process-local goal/fvar names."""

    kernel = _obj(kernel_state, "kernel_state")
    if kernel.get("state_id") != live_rpc_state_id:
        raise StrictKernelRPCProtocolError("live state id differs from kernel_state")
    options = _obj(kernel.get("options"), "kernel_state.options")
    _exact(options, {"maxHeartbeats"}, "kernel_state.options")
    if options != U05_BASELINE_OPTIONS:
        raise StrictKernelRPCProtocolError("runtime state cap is not frozen at 20000")
    try:
        identity = state_identity_from_kernel_state(
            kernel,
            environment_content_digest=environment_content_digest,
            baseline_semantic_options=U05_BASELINE_OPTIONS,
        )
    except StrictIdentityError as exc:
        raise StrictKernelRPCProtocolError("runtime state has no exact v3 identity") from exc
    if identity.status != "open":
        raise StrictKernelRPCProtocolError("RuntimeStateView is defined only for open states")
    goals = tuple(_obj(row, "kernel goal") for row in _arr(kernel.get("goals"), "goals"))
    contexts: dict[str, dict[str, Any]] = {}
    for raw_context in _arr(kernel.get("local_contexts"), "local_contexts"):
        context = _obj(raw_context, "local context")
        context_id = _str(context.get("local_context_graph_id"), "local context id")
        if context_id in contexts:
            raise StrictKernelRPCProtocolError("duplicate runtime local context id")
        contexts[context_id] = context  # type: ignore[index]
    runtime_goals: list[str] = []
    runtime_locals: list[tuple[str, ...]] = []
    for goal in goals:
        runtime_goals.append(_str(goal.get("mvar_id"), "goal.mvar_id"))  # type: ignore[arg-type]
        context_id = _str(goal.get("local_context_graph_id"), "goal local context")
        context = contexts.get(context_id)  # type: ignore[arg-type]
        if context is None:
            raise StrictKernelRPCProtocolError("goal references a missing local context")
        fvars = tuple(
            _str(_obj(node, "local declaration").get("fvar_id"), "local fvar id")
            for node in _arr(context.get("nodes"), "local context nodes")
        )
        runtime_locals.append(fvars)  # type: ignore[arg-type]
    debt = DebtReadout.from_identity(identity)
    response_signature = occurrence_response_signature(kernel)
    state_view = StateView(
        identity_key=identity.canonical_bytes,
        full_signature=identity.canonical_bytes,
        debt=debt.to_tuple(),
        live_rpc_state_id=live_rpc_state_id,
        response_signature=response_signature,
    )
    return RuntimeStateView(
        identity=identity,
        debt=debt,
        state_view=state_view,
        live_rpc_state_id=live_rpc_state_id,
        runtime_goal_mvar_ids=tuple(runtime_goals),
        runtime_local_fvar_ids_by_goal=tuple(runtime_locals),
    )


@dataclass(frozen=True)
class ApplyOracleResult:
    bound_action: BoundAction
    response: U05ApplyResponse | None
    event: OracleEvent
    censor: Censor | None
    target_state: RuntimeStateView | None = None

    def __post_init__(self) -> None:
        if self.event.is_censor != (self.censor is not None):
            raise StrictKernelRPCProtocolError("Oracle event/censor fields disagree")
        if (self.event.totalized_status is not None and self.event.raw_status == "open") != (
            self.target_state is not None
        ):
            raise StrictKernelRPCProtocolError("Oracle target runtime state is incoherent")

    @property
    def retained_state_id(self) -> str | None:
        if self.response is None or not self.response.after_state_retained:
            return None
        return self.response.after_state_id


def _censor_apply_result(
    *,
    source: RuntimeStateView,
    bound_action: BoundAction,
    kind: CensorKind,
    message: str,
    response: U05ApplyResponse | None = None,
    replay_attempts: int = 0,
) -> ApplyOracleResult:
    censor = Censor(kind=kind, stage="apply_tactic", message=message)
    event = OracleEvent.censor(
        source.identity.canonical_bytes,
        bound_action.symbol.action_id,
        kind.value,
        primary_attempts=1,
        replay_attempts=replay_attempts,
    )
    return ApplyOracleResult(bound_action, response, event, censor)


def oracle_event_from_apply(
    response: U05ApplyResponse,
    *,
    source: RuntimeStateView,
    bound_action: BoundAction,
    environment_content_digest: str,
) -> ApplyOracleResult:
    """Totalize one already-strict wire result, leaving censors outside Q."""

    if response.before_state_id != source.live_rpc_state_id:
        raise StrictKernelRPCProtocolError("apply response does not belong to source state")
    if response.action_id != bound_action.symbol.action_id:
        raise StrictKernelRPCProtocolError("apply response does not belong to bound action")
    try:
        before_identity = state_identity_from_kernel_state(
            response.kernel_state_before,
            environment_content_digest=environment_content_digest,
            baseline_semantic_options=U05_BASELINE_OPTIONS,
        )
    except StrictIdentityError as exc:
        raise StrictKernelRPCProtocolError("apply source identity cannot be reconstructed") from exc
    if before_identity != source.identity:
        raise StrictKernelRPCProtocolError("apply source full identity differs from runtime source")
    source_key = source.identity.canonical_bytes
    action_id = bound_action.symbol.action_id
    if response.status == "partial":
        target = build_runtime_state_view(
            response.kernel_state_after,
            environment_content_digest=environment_content_digest,
            live_rpc_state_id=response.after_state_id,
        )
        return ApplyOracleResult(
            bound_action,
            response,
            OracleEvent.open(source_key, action_id, target.state_view),
            None,
            target,
        )
    if response.status == "success":
        try:
            closed = state_identity_from_kernel_state(
                response.kernel_state_after,
                environment_content_digest=environment_content_digest,
                baseline_semantic_options=U05_BASELINE_OPTIONS,
            )
        except StrictIdentityError as exc:
            raise StrictKernelRPCProtocolError("closed target identity is incomplete") from exc
        if closed.status != "closed":
            raise StrictKernelRPCProtocolError("success target is not closed")
        return ApplyOracleResult(
            bound_action,
            response,
            OracleEvent.closed(source_key, action_id),
            None,
        )
    if response.status == "failure":
        if response.normalized_failure_class not in {
            "ordinary_failure",
            "target_resolution",
        }:
            raise StrictKernelRPCProtocolError("unknown ordinary failure class")
        return ApplyOracleResult(
            bound_action,
            response,
            OracleEvent.ordinary_failure(source_key, action_id),
            None,
        )
    if response.status == "censor":
        kind = (
            CensorKind.HEARTBEAT_EXHAUSTION
            if response.censor_reason == "heartbeat_exhaustion"
            else CensorKind.REPLAY_MISMATCH
        )
        return _censor_apply_result(
            source=source,
            bound_action=bound_action,
            kind=kind,
            message=response.censor_reason or "kernel response was censored",
            response=response,
            replay_attempts=1,
        )
    raise StrictKernelRPCProtocolError("strict apply response has no totalization rule")


class StrictKernelRPCOracleAdapter:
    """Strict owner of one worker process and its admitted live state ids."""

    def __init__(
        self,
        transport: TimedJSONLTransport,
        *,
        environment_content_digest: str,
        action_timeout_seconds: float = 30.0,
        control_timeout_seconds: float = 30.0,
    ) -> None:
        digest = environment_content_digest.upper()
        if len(digest) != 64 or any(ch not in "0123456789ABCDEF" for ch in digest):
            raise ValueError("environment_content_digest must be a SHA-256 digest")
        self._transport = transport
        self._environment_content_digest = digest
        self._action_timeout_seconds = SynchronousJSONLSubprocessTransport._deadline(
            action_timeout_seconds
        )
        self._control_timeout_seconds = SynchronousJSONLSubprocessTransport._deadline(
            control_timeout_seconds
        )
        self._session_id: str | None = None
        self._imports: tuple[str, ...] | None = None
        self._owned_state_ids: set[str] = set()
        self._shutdown = False

    @property
    def owned_state_ids(self) -> frozenset[str]:
        return frozenset(self._owned_state_ids)

    def _exchange(self, request: bytes, *, action: bool = False) -> bytes | str:
        if self._shutdown:
            raise KernelRPCTransportError("adapter is shut down")
        return self._transport.round_trip(
            request,
            timeout_seconds=(
                self._action_timeout_seconds if action else self._control_timeout_seconds
            ),
        )

    def load_project(
        self, *, request_id: str, imports: Sequence[str]
    ) -> LoadProjectResponse:
        if self._session_id is not None or self._owned_state_ids:
            raise StrictStateOwnershipError("project load is allowed exactly once")
        rows = _request_imports(imports)
        response = parse_load_project_response(
            self._exchange(
                strict_load_project_request_bytes(request_id=request_id, imports=rows)
            ),
            expected_request_id=request_id,
            expected_imports=rows,
        )
        if response.n_states != 0:
            raise StrictStateOwnershipError("new adapter did not receive an empty worker")
        self._session_id = response.session_id
        self._imports = response.imports
        return response

    def init_state(
        self, *, request_id: str, task: U05TaskSpec
    ) -> RuntimeStateView:
        if self._session_id is None or self._imports is None:
            raise StrictKernelRPCError("load_project must precede init_state")
        if task.imports != self._imports:
            raise StrictKernelRPCProtocolError("task imports differ from loaded project")
        parsed = parse_init_state_response(
            self._exchange(strict_init_state_request_bytes(request_id=request_id, task=task)),
            expected_request_id=request_id,
            expected_task=task,
        )
        state_id = parsed.summary.state_id
        if state_id in self._owned_state_ids:
            raise StrictStateOwnershipError("init_state reused an owned state id")
        self._owned_state_ids.add(state_id)
        if parsed.summary.status != "open":
            raise StrictKernelRPCProtocolError(
                f"initial state {state_id} is terminal; discard it before chart expansion"
            )
        runtime = build_runtime_state_view(
            parsed.kernel_state,
            environment_content_digest=self._environment_content_digest,
            live_rpc_state_id=state_id,
        )
        return runtime

    def status(self, *, request_id: str) -> StatusResponse:
        if self._session_id is None or self._imports is None:
            raise StrictKernelRPCError("load_project must precede status")
        response = parse_status_response(
            self._exchange(strict_status_request_bytes(request_id=request_id)),
            expected_request_id=request_id,
            expected_session_id=self._session_id,
            expected_imports=self._imports,
        )
        if not response.loaded:
            raise StrictKernelRPCProtocolError("loaded adapter reported unloaded status")
        if response.n_states != len(self._owned_state_ids):
            raise StrictStateOwnershipError("worker state count differs from adapter ownership")
        return response

    def apply_symbol(
        self,
        *,
        request_id: str,
        source: RuntimeStateView,
        symbol: ActionSymbol,
    ) -> ApplyOracleResult:
        if source.live_rpc_state_id not in self._owned_state_ids:
            raise StrictStateOwnershipError("apply source is not owned by this adapter")
        bound = source.bind_action(symbol)
        action = bound.to_rpc_action()
        request = strict_apply_request_bytes(
            request_id=request_id,
            state_id=source.live_rpc_state_id,
            action=action,
            target_mvar_id=bound.runtime_target_mvar_id,
        )
        response: U05ApplyResponse | None = None
        retained_registered = False
        try:
            raw = self._exchange(request, action=True)
            response = parse_apply_tactic_response(
                raw,
                expected_request_id=request_id,
                expected_state_id=source.live_rpc_state_id,
                expected_action=action,
                expected_target_mvar_id=bound.runtime_target_mvar_id,
            )
            if response.after_state_retained:
                child_id = response.after_state_id
                if child_id in self._owned_state_ids:
                    raise StrictStateOwnershipError(
                        "apply reused an owned child state id"
                    )
                self._owned_state_ids.add(child_id)
                retained_registered = True
            result = oracle_event_from_apply(
                response,
                source=source,
                bound_action=bound,
                environment_content_digest=self._environment_content_digest,
            )
        except KernelRPCTransportTimeout as exc:
            return _censor_apply_result(
                source=source,
                bound_action=bound,
                kind=CensorKind.WALL_TIMEOUT,
                message=str(exc),
            )
        except KernelRPCProcessExited as exc:
            return _censor_apply_result(
                source=source,
                bound_action=bound,
                kind=CensorKind.PROCESS_CRASH,
                message=str(exc),
            )
        except KernelRPCTransportError as exc:
            return _censor_apply_result(
                source=source,
                bound_action=bound,
                kind=CensorKind.TRANSPORT_FAILURE,
                message=str(exc),
            )
        except (StrictKernelRPCProtocolError, KernelRPCRemoteError) as exc:
            message = str(exc)
            lowered = message.lower()
            if "replay" in lowered:
                kind = CensorKind.REPLAY_MISMATCH
            elif "cap" in lowered or "heartbeat" in lowered:
                kind = CensorKind.CAP_MISMATCH
            else:
                kind = CensorKind.MALFORMED_RESPONSE
            return _censor_apply_result(
                source=source,
                bound_action=bound,
                kind=kind,
                message=message,
                response=response,
                replay_attempts=1 if response is not None else 0,
            )
        child_id = result.retained_state_id
        if child_id is not None and not retained_registered:
            if child_id in self._owned_state_ids:
                raise StrictStateOwnershipError("apply reused an owned child state id")
            self._owned_state_ids.add(child_id)
        return result

    def discard_owned(
        self, *, request_id: str, state_id: str
    ) -> DiscardStateResponse:
        if state_id not in self._owned_state_ids:
            raise StrictStateOwnershipError("discard requires an owned live state id")
        expected_before = len(self._owned_state_ids)
        response = parse_discard_state_response(
            self._exchange(
                strict_discard_request_bytes(request_id=request_id, state_id=state_id)
            ),
            expected_request_id=request_id,
            expected_state_id=state_id,
        )
        if (
            response.n_states_before != expected_before
            or response.n_states_after != expected_before - 1
        ):
            raise StrictStateOwnershipError("discard counts differ from strict ownership")
        self._owned_state_ids.remove(state_id)
        return response

    def shutdown(self, *, request_id: str) -> ShutdownResponse:
        response = parse_shutdown_response(
            self._exchange(strict_shutdown_request_bytes(request_id=request_id)),
            expected_request_id=request_id,
        )
        finish = getattr(self._transport, "finish_clean_shutdown", None)
        if not callable(finish):
            raise KernelRPCTransportError("transport lacks clean-shutdown completion")
        finish(timeout_seconds=self._control_timeout_seconds)
        self._owned_state_ids.clear()
        self._shutdown = True
        return response


class StrictKernelRPCClient:
    """Tiny synchronous client over a caller-owned line transport.

    ``round_trip`` receives canonical request bytes and must return exactly one
    response line.  Process creation, timeouts, and publication remain runner
    responsibilities so a transport failure can be represented as an external
    censor rather than a fabricated transition.
    """

    def __init__(self, round_trip: Callable[[bytes], bytes | str]) -> None:
        self._round_trip = round_trip

    def load_project(
        self, *, request_id: str, imports: Sequence[str]
    ) -> LoadProjectResponse:
        rows = _request_imports(imports)
        return parse_load_project_response(
            self._round_trip(
                strict_load_project_request_bytes(request_id=request_id, imports=rows)
            ),
            expected_request_id=request_id,
            expected_imports=rows,
        )

    def init_state(
        self, *, request_id: str, task: U05TaskSpec
    ) -> InitStateResponse:
        return parse_init_state_response(
            self._round_trip(
                strict_init_state_request_bytes(request_id=request_id, task=task)
            ),
            expected_request_id=request_id,
            expected_task=task,
        )

    def status(
        self,
        *,
        request_id: str,
        expected_session_id: str | None = None,
        expected_imports: Sequence[str] | None = None,
    ) -> StatusResponse:
        return parse_status_response(
            self._round_trip(strict_status_request_bytes(request_id=request_id)),
            expected_request_id=request_id,
            expected_session_id=expected_session_id,
            expected_imports=expected_imports,
        )

    def apply_tactic(
        self,
        *,
        request_id: str,
        state_id: str,
        action: Mapping[str, Any],
        target_mvar_id: str | None = None,
    ) -> U05ApplyResponse:
        request = strict_apply_request_bytes(
            request_id=request_id,
            state_id=state_id,
            action=action,
            target_mvar_id=target_mvar_id,
        )
        return parse_apply_tactic_response(
            self._round_trip(request),
            expected_request_id=request_id,
            expected_state_id=state_id,
            expected_action=action,
            expected_target_mvar_id=target_mvar_id,
        )

    def discard_state(
        self, *, request_id: str, state_id: str
    ) -> DiscardStateResponse:
        request = strict_discard_request_bytes(
            request_id=request_id, state_id=state_id
        )
        return parse_discard_state_response(
            self._round_trip(request),
            expected_request_id=request_id,
            expected_state_id=state_id,
        )

    def shutdown(self, *, request_id: str) -> ShutdownResponse:
        return parse_shutdown_response(
            self._round_trip(strict_shutdown_request_bytes(request_id=request_id)),
            expected_request_id=request_id,
        )


__all__ = [
    "ApplyOracleResult",
    "InitStateResponse",
    "KERNEL_RPC_BACKEND",
    "LEGACY_RPC_PROTOCOL_VERSION",
    "DiscardStateResponse",
    "KernelRPCProcessExited",
    "KernelRPCRemoteError",
    "KernelRPCTransportError",
    "KernelRPCTransportTimeout",
    "KernelStateSummary",
    "LoadProjectResponse",
    "RawReplayCertificate",
    "RawStateDelta",
    "RawTargetBinding",
    "RuntimeStateView",
    "ShutdownResponse",
    "StatusResponse",
    "StrictKernelRPCClient",
    "StrictKernelRPCError",
    "StrictKernelRPCOracleAdapter",
    "StrictKernelRPCProtocolError",
    "StrictStateOwnershipError",
    "SynchronousJSONLSubprocessTransport",
    "TimedJSONLTransport",
    "U05_BASELINE_OPTIONS",
    "U05ApplyResponse",
    "build_runtime_state_view",
    "oracle_event_from_apply",
    "occurrence_response_signature",
    "parse_apply_tactic_response",
    "parse_discard_state_response",
    "parse_init_state_response",
    "parse_load_project_response",
    "parse_shutdown_response",
    "parse_status_response",
    "parse_strict_json_line",
    "raise_for_rpc_error",
    "strict_apply_request_bytes",
    "strict_discard_request_bytes",
    "strict_init_state_request_bytes",
    "strict_load_project_request_bytes",
    "strict_shutdown_request_bytes",
    "strict_status_request_bytes",
    "strip_replay_transport",
]
