from __future__ import annotations

from typing import Any

from ..schemas import LeanTask, stable_hash


SCHEMA_PROMPT_BOUNDARY = "lean-rgc-prompt-boundary-v89.0"

DEFAULT_FORBIDDEN_OPERATIONS = ("sorry", "admit", "new_axiom", "unknown_identifier")
DEFAULT_ALLOWED_OPERATIONS = ("use_premise", "rewrite", "tactic_sequence")

OUTPUT_SCHEMA_INSTRUCTION = (
    "Respond with a single JSON object and nothing else, shaped as: "
    '{"proposals": [{"proposal_kind": "tactic", "lean_tactic": "<Lean 4 tactic>", '
    '"premises_used": [], "confidence": 0.0}]}. '
    "Propose at most {n} tactics, ordered best first."
)


def _task_dict(task: LeanTask | dict[str, Any]) -> dict[str, Any]:
    if isinstance(task, LeanTask):
        return task.to_dict()
    return dict(task)


def build_prompt_boundary(
    *,
    task: LeanTask | dict[str, Any],
    boundary_kind: str = "tactic_synthesis",
    feedback_text: str = "",
    attempt_index: int = 0,
    allowed_operations: tuple[str, ...] | list[str] = DEFAULT_ALLOWED_OPERATIONS,
    forbidden_operations: tuple[str, ...] | list[str] = DEFAULT_FORBIDDEN_OPERATIONS,
    max_proposals: int = 4,
    decoding: dict[str, Any] | None = None,
    output_schema: str | None = None,
) -> dict[str, Any]:
    """Build the boundary object; the rendered prompt is derived from it.

    The boundary JSON is authoritative and the natural-language prompt is
    only its serialization, so boundary_id hashes the object, not the text.
    """

    task_obj = _task_dict(task)
    content = {
        "schema_version": SCHEMA_PROMPT_BOUNDARY,
        "boundary_kind": str(boundary_kind),
        "task_id": str(task_obj.get("task_id") or ""),
        "statement": str(task_obj.get("statement") or ""),
        "imports": list(task_obj.get("imports") or []),
        "attempt_index": int(attempt_index),
        "feedback_text": str(feedback_text or ""),
        "allowed_operations": sorted(str(x) for x in allowed_operations),
        "forbidden_operations": sorted(str(x) for x in forbidden_operations),
        "max_proposals": int(max_proposals),
        "decoding": dict(decoding or {}),
        "output_schema": str(output_schema or "lean-rgc-llm-repair-proposal-v89.0"),
    }
    # A frontier/salvage task's verified prefix is part of what Lean will see,
    # so it must be part of what the model sees. Only present when non-empty:
    # prefix-less boundaries keep their historical boundary_id/prompt hashes.
    prefix = str(task_obj.get("prefix") or "")
    if prefix:
        content["prefix"] = prefix
    return {
        **content,
        "boundary_id": "pb_" + stable_hash(content, 20),
        "canonical_status": "prompt_boundary_witness_not_canonical",
    }


def render_boundary(boundary: dict[str, Any], *, output_instruction: str | None = None) -> tuple[str, str]:
    """Serialize a boundary into (system, user) prompts, deterministically.

    `output_instruction` overrides the default JSON-proposal instruction —
    a caller that demands a different output format (e.g. the grad loop's
    raw-tactic contract) must replace it, not append a contradicting line.
    """

    forbidden = ", ".join(boundary.get("forbidden_operations") or [])
    system_lines = [
        "You are a Lean 4 tactic synthesis engine inside an audited proof pipeline.",
        "Your proposals are noncanonical witnesses; every output is replayed against Lean before use.",
        f"Never use: {forbidden}.",
        "Only reference identifiers that exist in the stated imports.",
        output_instruction
        if output_instruction is not None
        else OUTPUT_SCHEMA_INSTRUCTION.replace("{n}", str(int(boundary.get("max_proposals") or 4))),
    ]
    user_lines = [
        f"Theorem statement:\n{boundary.get('statement') or ''}",
    ]
    prefix = str(boundary.get("prefix") or "")
    if prefix:
        user_lines.append(
            "Verified proof prefix (already accepted by Lean; your tactic continues after it):\n"
            f"{prefix}"
        )
    user_lines.extend([
        f"Imports: {', '.join(boundary.get('imports') or []) or '(core only)'}",
        f"Attempt index: {int(boundary.get('attempt_index') or 0)}",
    ])
    feedback = str(boundary.get("feedback_text") or "")
    if feedback:
        user_lines.append(f"Feedback from previous audited attempts:\n{feedback}")
    return "\n".join(system_lines), "\n\n".join(user_lines)


__all__ = [
    "DEFAULT_ALLOWED_OPERATIONS",
    "DEFAULT_FORBIDDEN_OPERATIONS",
    "OUTPUT_SCHEMA_INSTRUCTION",
    "SCHEMA_PROMPT_BOUNDARY",
    "build_prompt_boundary",
    "render_boundary",
]
