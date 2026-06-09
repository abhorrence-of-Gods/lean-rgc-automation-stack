from __future__ import annotations

from pathlib import Path
from typing import Any

from .crg_optimizer import optimize_crg_candidates


def generate_nonlinear_repair_candidates(
    *,
    problems_path: str | Path,
    registry_path: str | Path,
    out: str | Path,
    response_completion_path: str | Path | None = None,
    summary_out: str | Path | None = None,
    optimizer: str = "convex_mixture",
    temperature: float = 1.0,
    top_k: int = 16,
    cost_weight: float = 0.0,
    audit_weight: float = 0.0,
    source_weight: float = 0.0,
    ghost_weight: float = 0.0,
    hardening_weight: float = 0.0,
) -> dict[str, Any]:
    """Generate relaxed optimizer witnesses.

    The generator is intentionally a noncanonical witness producer. Canonicality
    lives in the CRG problem and downstream audit/POMS promotion.
    """

    return optimize_crg_candidates(
        problems_path=problems_path,
        registry_path=registry_path,
        out=out,
        response_completion_path=response_completion_path,
        summary_out=summary_out,
        optimizer=optimizer,
        temperature=temperature,
        top_k=top_k,
        cost_weight=cost_weight,
        audit_weight=audit_weight,
        source_weight=source_weight,
        ghost_weight=ghost_weight,
        hardening_weight=hardening_weight,
    )


__all__ = ["generate_nonlinear_repair_candidates"]
