from __future__ import annotations

from typing import Any, Callable

from ..response_completion import response_map_from_row
from ..schemas import stable_hash


SCHEMA_PROMPT_SIGNAL = "lean-rgc-prompt-signal-v90.0"

PACKET_BLOCKS = ("obstruction", "crg", "last_failure", "response", "safety", "poms")

DEFAULT_MAX_MESSAGES = 3
DEFAULT_MAX_MESSAGE_CHARS = 500


def _response_status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _response_messages(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("messages", "lean_messages", "errors"):
        value = row.get(key)
        if isinstance(value, list):
            out.extend(str(v) for v in value if str(v).strip())
        elif isinstance(value, str) and value.strip():
            out.append(value)
    audit = row.get("audit") if isinstance(row.get("audit"), dict) else {}
    for key in ("messages", "message", "stderr_tail"):
        value = audit.get(key)
        if isinstance(value, list):
            out.extend(str(v) for v in value if str(v).strip())
        elif isinstance(value, str) and value.strip():
            out.append(value)
    return out


def build_signal_packet(
    *,
    task_id: str,
    response_rows: list[dict[str, Any]],
    obstruction: dict[str, Any] | None = None,
    crg: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
    poms: dict[str, Any] | None = None,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
) -> dict[str, Any]:
    """Aggregate audited telemetry into the typed packet of design §9."""

    rows = [r for r in response_rows if isinstance(r, dict)]
    status_counts: dict[str, int] = {}
    messages: list[str] = []
    response_acc: dict[str, float] = {}
    for row in rows:
        status = _response_status(row)
        status_counts[status] = status_counts.get(status, 0) + 1
        messages.extend(_response_messages(row))
        for key, value in response_map_from_row(row).items():
            response_acc[key] = max(response_acc.get(key, float("-inf")), float(value))
    truncated = [m[: max(0, int(max_message_chars))] for m in messages[: max(0, int(max_messages))]]
    packet = {
        "schema_version": SCHEMA_PROMPT_SIGNAL,
        "task_id": str(task_id),
        "obstruction": dict(obstruction or {}),
        "crg": dict(crg or {}),
        "last_failure": {
            "n_responses": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "lean_messages": truncated,
        },
        "response": {"observed_max": dict(sorted(response_acc.items()))},
        "safety": dict(safety or {}),
        "poms": dict(poms or {}),
        "canonical_status": "prompt_signal_packet_is_diagnostic_not_canonical",
    }
    packet["signal_id"] = "psig_" + stable_hash(packet, 16)
    return packet


def render_packet_for_prompt(
    packet: dict[str, Any],
    *,
    include_keys: tuple[str, ...] | list[str] | None = None,
) -> str:
    """Deterministic serialization; include_keys is the bandit control point."""

    keys = [k for k in PACKET_BLOCKS if include_keys is None or k in set(include_keys)]
    lines = ["[audited telemetry]"]
    for key in keys:
        block = packet.get(key)
        if not block:
            continue
        if key == "last_failure":
            lines.append(f"failure: {block.get('n_responses', 0)} responses, statuses {block.get('status_counts', {})}")
            for msg in block.get("lean_messages") or []:
                lines.append(f"lean: {msg}")
        elif key == "response":
            observed = block.get("observed_max") or {}
            if observed:
                pairs = ", ".join(f"{k}={v:.3f}" for k, v in sorted(observed.items()))
                lines.append(f"response observed max: {pairs}")
        else:
            pairs = ", ".join(f"{k}={v}" for k, v in sorted(block.items()))
            lines.append(f"{key}: {pairs}")
    return "\n".join(lines)


def make_signal_packet_fn(
    *,
    obstruction: dict[str, Any] | None = None,
    crg: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
    poms: dict[str, Any] | None = None,
    include_keys: tuple[str, ...] | list[str] | None = None,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
    packets_sink: list[dict[str, Any]] | None = None,
) -> Callable[..., str]:
    """Adapt the bridge to the eval harness signal_packet_fn interface.

    The static blocks (obstruction/crg/safety/poms) come from run artifacts
    when available; the per-attempt failure telemetry comes from the episode
    state the harness maintains.
    """

    def signal_packet_fn(*, task: Any, state: dict[str, Any]) -> str:
        packet = build_signal_packet(
            task_id=str(getattr(task, "task_id", "") or ""),
            response_rows=list(state.get("last_responses") or []),
            obstruction=obstruction,
            crg=crg,
            safety=safety,
            poms=poms,
            max_messages=max_messages,
            max_message_chars=max_message_chars,
        )
        if packets_sink is not None:
            packets_sink.append(packet)
        return render_packet_for_prompt(packet, include_keys=include_keys)

    return signal_packet_fn


__all__ = [
    "DEFAULT_MAX_MESSAGES",
    "DEFAULT_MAX_MESSAGE_CHARS",
    "PACKET_BLOCKS",
    "SCHEMA_PROMPT_SIGNAL",
    "build_signal_packet",
    "make_signal_packet_fn",
    "render_packet_for_prompt",
]
