"""Sound-gradient estimators (torch-free arithmetic).

Taxonomy from the verified design: RFT (exact supervised gradient on
Lean-verified traces) is the primary path; RLOO (unbiased on-policy score
function with leave-one-out baseline) is the auxiliary; anything scored on
relaxed/soft inputs is a search heuristic and never appears here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


SCHEMA_GRAD_UPDATE = "lean-rgc-grad-update-v96.0"
SCHEMA_RFT_TRACE = "lean-rgc-rft-trace-v96.0"

DEFAULT_SUCCESS_STATUSES = ("proved", "advanced", "ok", "succeeded", "success")


def rloo_advantages(
    rewards: "np.ndarray | list[float]",
    baselines: "np.ndarray | list[float] | None" = None,
) -> np.ndarray:
    """Leave-one-out advantages: a_i = r_i - mean(r_{-i}) = G/(G-1) * (r_i - mean).

    A degenerate group (all rewards equal) yields exactly zero advantages —
    no gradient, which is the honest signal, not an error.

    `baselines` is an optional STATE-level control variate b(s_i) subtracted
    before the leave-one-out mean. Unbiasedness holds because b(s) does not
    depend on the sampled action; a baseline constant within the group
    cancels identically (so this is a no-op under pure per-task grouping —
    it only reduces variance in mixed-task stratified groups). An all-equal
    reward group with VARYING baselines carries signal: failing on an easy
    state is punished harder than failing on a hard one.
    """

    r = np.asarray(rewards, dtype=float)
    if r.ndim != 1 or r.size < 2:
        raise ValueError("rloo_advantages needs a flat group of >= 2 rewards")
    if baselines is not None:
        b = np.asarray(baselines, dtype=float)
        if b.shape != r.shape:
            raise ValueError("baselines must align with rewards")
        r = r - b
    g = r.size
    return (g / (g - 1.0)) * (r - r.mean())


@dataclass
class RLOOStats:
    n_groups: int
    n_degenerate: int
    mean_abs_advantage: float
    mean_reward: float

    @property
    def fraction_degenerate(self) -> float:
        return self.n_degenerate / self.n_groups if self.n_groups else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_groups": self.n_groups,
            "n_degenerate": self.n_degenerate,
            "fraction_degenerate": self.fraction_degenerate,
            "mean_abs_advantage": self.mean_abs_advantage,
            "mean_reward": self.mean_reward,
        }


def degenerate_groups(groups: dict[Any, "list[float]"]) -> list[Any]:
    """Keys of groups whose rewards are all equal (zero RLOO gradient)."""

    return [k for k, rewards in groups.items() if len(set(np.round(rewards, 12))) <= 1]


def grouped_rloo(
    groups: dict[Any, "list[float]"],
    baselines: "dict[Any, list[float]] | None" = None,
) -> tuple[dict[Any, np.ndarray], RLOOStats]:
    """Per-group RLOO. `baselines[key]` aligns with `groups[key]`.

    Degeneracy statistics are computed on RAW rewards (comparable across
    grouping modes); note a raw-degenerate group can still carry gradient
    when baselines vary within it.
    """
    advantages: dict[Any, np.ndarray] = {}
    degenerate = set(degenerate_groups(groups))
    abs_sum = 0.0
    n_items = 0
    reward_sum = 0.0
    for key, rewards in groups.items():
        b = baselines.get(key) if baselines is not None else None
        adv = rloo_advantages(rewards, baselines=b) if len(rewards) >= 2 else np.zeros(len(rewards))
        advantages[key] = adv
        abs_sum += float(np.abs(adv).sum())
        n_items += len(rewards)
        reward_sum += float(np.sum(rewards))
    stats = RLOOStats(
        n_groups=len(groups),
        n_degenerate=len(degenerate),
        mean_abs_advantage=abs_sum / n_items if n_items else 0.0,
        mean_reward=reward_sum / n_items if n_items else 0.0,
    )
    return advantages, stats


def stratified_groups(
    records: list[dict[str, Any]],
    *,
    group_size: int,
    reward_key: str = "reward",
    difficulty: dict[str, float] | None = None,
    task_key: str = "task_id",
) -> dict[str, list[dict[str, Any]]]:
    """Group per-sample records for RLOO.

    Primary grouping is per (task, wave) — the natural exchangeable unit.
    When `difficulty` (historical solve rate per task) is provided, tasks are
    bucketed by difficulty so that mixed-difficulty groups do not manufacture
    fake advantages; within a bucket, records are chunked to `group_size`.
    """

    if difficulty is None:
        groups: dict[str, list[dict[str, Any]]] = {}
        for rec in records:
            key = f"{rec.get(task_key)}::w{rec.get('wave_index', 0)}"
            groups.setdefault(key, []).append(rec)
        return groups
    buckets: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        d = difficulty.get(str(rec.get(task_key)), 0.0)
        bucket = "hard" if d < 0.2 else ("mid" if d < 0.6 else "easy")
        buckets.setdefault(bucket, []).append(rec)
    groups = {}
    for bucket, recs in buckets.items():
        ordered = sorted(recs, key=lambda r: (str(r.get(task_key)), str(r.get("action_id", ""))))
        chunks = [ordered[i : i + group_size] for i in range(0, len(ordered), group_size)]
        if len(chunks) >= 2 and len(chunks[-1]) < 2:
            # A trailing singleton would be silently dropped from RLOO;
            # merge it into the previous chunk instead (LOO stays valid).
            chunks[-2].extend(chunks.pop())
        for j, chunk in enumerate(chunks):
            if len(chunk) >= 2:
                groups[f"{bucket}::{j}"] = chunk
    return groups


def rft_trace_selection(
    micro_rows: list[dict[str, Any]],
    boundary_rows: list[dict[str, Any]],
    *,
    success_statuses: tuple[str, ...] = DEFAULT_SUCCESS_STATUSES,
) -> list[dict[str, Any]]:
    """Join audited rows with their prompt boundaries into RFT training traces.

    micro_audit rows carry action.metadata.boundary_id; boundary rows carry
    the full boundary content, so the exact (system, user) prompt can be
    re-rendered downstream. Only Lean-verified successes become traces —
    the reward is the identity judgment, never a heuristic score.
    """

    boundaries = {str(b.get("boundary_id")): b for b in boundary_rows if b.get("boundary_id")}
    traces: list[dict[str, Any]] = []
    for row in micro_rows:
        status = str(row.get("audit_status") or row.get("status") or "")
        if status not in set(success_statuses):
            continue
        action = row.get("action") if isinstance(row.get("action"), dict) else {}
        meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        boundary_id = str(meta.get("boundary_id") or "")
        boundary = boundaries.get(boundary_id)
        if boundary is None:
            continue
        tactic = str(action.get("tactic") or "").strip()
        if not tactic:
            continue
        traces.append(
            {
                "schema_version": SCHEMA_RFT_TRACE,
                "task_id": row.get("task_id"),
                "boundary_id": boundary_id,
                "boundary": boundary,
                "tactic": tactic,
                "status": status,
                "canonical_status": "rft_trace_is_lean_verified_witness",
            }
        )
    return traces


__all__ = [
    "DEFAULT_SUCCESS_STATUSES",
    "RLOOStats",
    "SCHEMA_GRAD_UPDATE",
    "SCHEMA_RFT_TRACE",
    "degenerate_groups",
    "grouped_rloo",
    "rft_trace_selection",
    "rloo_advantages",
    "stratified_groups",
]
