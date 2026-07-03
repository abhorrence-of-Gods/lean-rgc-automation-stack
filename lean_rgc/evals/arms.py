from __future__ import annotations

from typing import Any


ARMS = ("a0_onebit", "a1_raw_error", "a2_typed_packet", "a3_typed_only")

DEFAULT_MAX_ERROR_MESSAGES = 3
DEFAULT_MAX_ERROR_CHARS = 500


def render_feedback(
    arm: str,
    state: dict[str, Any],
    *,
    max_error_messages: int = DEFAULT_MAX_ERROR_MESSAGES,
    max_error_chars: int = DEFAULT_MAX_ERROR_CHARS,
) -> str:
    """Render the feedback block for one attempt.

    This function is the only thing that may differ between experiment arms;
    model, decoding, instruction text, and budget must stay identical so the
    arm comparison isolates the feedback channel.
    """

    if arm not in ARMS:
        raise ValueError(f"unknown eval arm: {arm}")
    n_failed = int(state.get("n_failed") or 0)
    lines = [f"Previous failed attempts: {n_failed}."]
    if arm == "a0_onebit":
        return "\n".join(lines)
    if arm == "a1_raw_error":
        errors = [str(e) for e in (state.get("last_errors") or []) if str(e).strip()]
        for err in errors[: max(0, int(max_error_messages))]:
            lines.append(f"Lean error: {err[: max(0, int(max_error_chars))]}")
        return "\n".join(lines)
    # a2_typed_packet and a3_typed_only both consume a rendered packet; the
    # factorial difference (raw instance messages in or out) is decided by
    # the signal bridge that produced the packet, not here.
    packet_text = state.get("signal_packet_text")
    if not packet_text:
        raise NotImplementedError(
            f"{arm} requires a rendered signal packet; the prompt signal bridge is not wired yet"
        )
    lines.append(str(packet_text))
    return "\n".join(lines)


__all__ = ["ARMS", "DEFAULT_MAX_ERROR_CHARS", "DEFAULT_MAX_ERROR_MESSAGES", "render_feedback"]
