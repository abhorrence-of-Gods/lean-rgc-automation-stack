from __future__ import annotations

"""Strict raw client boundary for the additive U05 kernel RPC contract.

The legacy wire envelope remains ``lean-rgc-jsonl-rpc-v2`` and the kernel-state
payload remains v3.  This module validates the separately versioned U05 fields
without passing them through permissive schema adapters.  Unknown or duplicate
fields fail closed before a transition contract can be built.
"""

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping

from lean_rgc.odlrq.contracts import (
    CapSemantics,
    EPISODE_BUDGET_SENTINEL,
    REPLAY_VERIFICATION_SCHEMA,
    StrictContractError,
    U05_SEMANTICS_VERSION,
)
from .kernel_state_identity import (
    LEGACY_KERNEL_STATE_SCHEMA_VERSION,
    canonical_json_bytes,
)


LEGACY_RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"


class StrictKernelRPCError(RuntimeError):
    """Base error for malformed, rejected, or mismatched RPC records."""


class StrictKernelRPCProtocolError(StrictKernelRPCError):
    """The response is outside the frozen strict wire contract."""


class KernelRPCRemoteError(StrictKernelRPCError):
    """The worker returned a well-formed ``ok=false`` response."""


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
        state_summary = cls._state_summary(parsed["state"])
        audit, audit_flags = cls._audit(parsed["audit"])
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
        elif retained:
            raise StrictKernelRPCProtocolError("failure/timeout must not retain a child state")
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
        if state_summary["state_id"] != parsed["after_state_id"]:
            raise StrictKernelRPCProtocolError("state summary differs from after_state_id")

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


class StrictKernelRPCClient:
    """Tiny synchronous client over a caller-owned line transport.

    ``round_trip`` receives canonical request bytes and must return exactly one
    response line.  Process creation, timeouts, and publication remain runner
    responsibilities so a transport failure can be represented as an external
    censor rather than a fabricated transition.
    """

    def __init__(self, round_trip: Callable[[bytes], bytes | str]) -> None:
        self._round_trip = round_trip

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


__all__ = [
    "LEGACY_RPC_PROTOCOL_VERSION",
    "DiscardStateResponse",
    "KernelRPCRemoteError",
    "RawReplayCertificate",
    "RawStateDelta",
    "RawTargetBinding",
    "StrictKernelRPCClient",
    "StrictKernelRPCError",
    "StrictKernelRPCProtocolError",
    "U05ApplyResponse",
    "parse_apply_tactic_response",
    "parse_discard_state_response",
    "parse_strict_json_line",
    "raise_for_rpc_error",
    "strict_apply_request_bytes",
    "strict_discard_request_bytes",
    "strip_replay_transport",
]
