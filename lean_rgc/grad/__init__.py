"""Gradient pipeline: continuous / differentiable / parallel Lean-LLM loop.

Only the estimators, config invariants, and orchestration skeleton live here
with no torch dependency, so the default CI can exercise the load-bearing
math. The actual QLoRA policy / HF rollout (rollout.py, policy.py) import
torch lazily and run under the `e2e` tier only.

Design record: docs/experiments/toy0_phase_hmm.md and the sound-gradient
taxonomy (RFT primary, RLOO auxiliary, PRM search-only, Lean as the discrete
identity anchor).
"""

from .config import GradInvariants, assert_rollout_batch, assert_train_memory
from .estimators import (
    SCHEMA_GRAD_UPDATE,
    RLOOStats,
    degenerate_groups,
    rft_trace_selection,
    rloo_advantages,
    stratified_groups,
)
from .engine import RolloutEngine, run_grad_loop

__all__ = [
    "GradInvariants",
    "RLOOStats",
    "RolloutEngine",
    "SCHEMA_GRAD_UPDATE",
    "assert_rollout_batch",
    "assert_train_memory",
    "degenerate_groups",
    "rft_trace_selection",
    "rloo_advantages",
    "run_grad_loop",
    "stratified_groups",
]
