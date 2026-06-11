from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import json
import re

from ..schemas import LeanTask, stable_hash, write_jsonl
from .boundary import build_prompt_boundary, render_boundary
from .llm_client import LLMClient


SCHEMA_LLM_PROPOSAL = "lean-rgc-llm-repair-proposal-v89.0"

_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def decode_completion(text: str) -> list[dict[str, Any]]:
    """Decode LLM output into proposal dicts without ever raising.

    Strict JSON first, then the first fenced JSON block; anything else
    becomes a decode_error proposal so the episode keeps running and the
    failure stays visible in artifacts.
    """

    candidates = [text]
    fenced = _FENCED_JSON.search(text or "")
    if fenced:
        candidates.append(fenced.group(1))
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("proposals"), list):
            out = [p for p in obj["proposals"] if isinstance(p, dict)]
            if out:
                return out
    return [{"proposal_kind": "decode_error", "raw_text_head": str(text or "")[:200]}]


def proposals_to_actions(
    proposals: list[dict[str, Any]],
    *,
    boundary_id: str,
    task_id: str,
    prompt_hash: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for i, proposal in enumerate(proposals):
        if proposal.get("proposal_kind") == "decode_error":
            continue
        tactic = str(proposal.get("lean_tactic") or "").strip()
        if not tactic:
            continue
        actions.append(
            {
                "action_id": "llm_" + stable_hash({"boundary": boundary_id, "task": task_id, "i": i, "tactic": tactic}, 16),
                "tactic": tactic,
                "tactic_class": "llm_proposal",
                "metadata": {
                    "source": "llm_prompt_boundary",
                    "boundary_id": boundary_id,
                    "prompt_hash": prompt_hash,
                    "proposal_index": i,
                    "confidence": proposal.get("confidence"),
                    "canonical_status": "llm_proposal_witness_not_canonical",
                },
            }
        )
    return actions


def make_llm_proposal_fn(
    *,
    client: LLMClient,
    boundary_kind: str = "tactic_synthesis",
    max_proposals: int = 4,
    boundaries_out: str | Path | None = None,
) -> Callable[..., list[dict[str, Any]]]:
    """Adapt an LLMClient to the eval harness ProposalFn interface."""

    boundary_rows: list[dict[str, Any]] = []

    def proposal_fn(*, task: LeanTask, attempt_index: int, feedback: str) -> list[dict[str, Any]]:
        boundary = build_prompt_boundary(
            task=task,
            boundary_kind=boundary_kind,
            feedback_text=feedback,
            attempt_index=attempt_index,
            max_proposals=max_proposals,
        )
        system, user = render_boundary(boundary)
        completion = client.complete(system=system, user=user)
        proposals = decode_completion(completion.text)
        if boundaries_out is not None:
            boundary_rows.append(
                {
                    **boundary,
                    "prompt_hash": completion.prompt_hash,
                    "output_hash": completion.output_hash,
                    "model_id": completion.model_id,
                    "model_version": completion.model_version,
                    "cached": completion.cached,
                    "n_proposals": len(proposals),
                }
            )
            write_jsonl(boundaries_out, boundary_rows)
        return proposals_to_actions(
            proposals,
            boundary_id=str(boundary["boundary_id"]),
            task_id=task.task_id,
            prompt_hash=completion.prompt_hash,
        )

    return proposal_fn


__all__ = [
    "SCHEMA_LLM_PROPOSAL",
    "decode_completion",
    "make_llm_proposal_fn",
    "proposals_to_actions",
]
