"""Verified operating invariants for the gradient loop.

Every number here traces to the adversarially verified feasibility claims
(design review, 2026-07-03): the two load-bearing conditions are batch >= 8
during rollout and gradient checkpointing during training. They are checked
against MEASURED values at runtime — the assert helpers receive numbers the
engine actually observed, they do not restate analysis as fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCHEMA_GRAD_CONFIG = "lean-rgc-grad-config-v96.0"


class GradInvariantError(RuntimeError):
    """A verified load-bearing condition of the gradient loop is violated."""


@dataclass
class GradInvariants:
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    load_in_4bit: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    # rollout
    min_rollout_batch: int = 8          # load-bearing: batch-1 decode ~20-25 tok/s kills throughput
    rollout_chunk: int = 32             # decode chunk: output_logits holds steps x batch x vocab, so
                                        # an unchunked wavefront (100s of seqs) OOMs at max_new_tokens
    max_new_tokens: int = 512           # decode time dominates beyond this; verified budget
    group_size: int = 8                 # RLOO group G
    temperature: float = 0.7
    top_p: float = 0.95
    # training
    gradient_checkpointing: bool = True  # load-bearing: without it activations OOM at micro-batch 4 x 1.6k
    micro_batch: int = 4
    grad_accum: int = 4
    inner_epochs: int = 1                # verified: <= 2; on-policy default 1
    learning_rate: float = 1e-5
    kl_beta: float = 0.05
    kl_target_per_token: tuple[float, float] = (0.01, 0.02)
    kl_hard_cap_per_seq: float = 0.5
    # gates (S3-verified cadence)
    gate_every_steps: int = 10
    # memory budget (measured against, not assumed)
    gpu_budget_gb: float = 24.0
    memory_headroom: float = 0.9
    seed: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        problems: list[str] = []
        if self.min_rollout_batch < 8:
            problems.append(f"min_rollout_batch={self.min_rollout_batch} < 8 (batched decode is load-bearing)")
        if self.rollout_chunk < self.min_rollout_batch:
            problems.append(
                f"rollout_chunk={self.rollout_chunk} < min_rollout_batch={self.min_rollout_batch}: "
                "chunked decode would sink below the batch floor"
            )
        if self.rollout_chunk > 64:
            problems.append(
                f"rollout_chunk={self.rollout_chunk} > 64: output_logits retention "
                "(steps x batch x vocab) exceeds the verified memory budget at max_new_tokens"
            )
        if self.max_new_tokens > 512:
            problems.append(f"max_new_tokens={self.max_new_tokens} > 512 (decode budget)")
        if not self.gradient_checkpointing:
            problems.append("gradient_checkpointing disabled (activations OOM without it)")
        if self.inner_epochs != 1:
            problems.append(
                f"inner_epochs={self.inner_epochs}: v96 implements no importance correction, "
                "so only on-policy single-epoch updates are sound"
            )
        if self.group_size < 2:
            problems.append("group_size < 2 makes the leave-one-out baseline undefined")
        if not self.load_in_4bit:
            problems.append("load_in_4bit disabled: the verified memory budget assumes the NF4 base")
        if problems:
            raise GradInvariantError("; ".join(problems))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_GRAD_CONFIG,
            "model_name": self.model_name,
            "load_in_4bit": self.load_in_4bit,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "min_rollout_batch": self.min_rollout_batch,
            "rollout_chunk": self.rollout_chunk,
            "max_new_tokens": self.max_new_tokens,
            "group_size": self.group_size,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "gradient_checkpointing": self.gradient_checkpointing,
            "micro_batch": self.micro_batch,
            "grad_accum": self.grad_accum,
            "inner_epochs": self.inner_epochs,
            "learning_rate": self.learning_rate,
            "kl_beta": self.kl_beta,
            "kl_target_per_token": list(self.kl_target_per_token),
            "kl_hard_cap_per_seq": self.kl_hard_cap_per_seq,
            "gate_every_steps": self.gate_every_steps,
            "gpu_budget_gb": self.gpu_budget_gb,
            "seed": self.seed,
        }


def assert_rollout_batch(batch_size: int, *, invariants: GradInvariants | None = None, allow_small: bool = False) -> None:
    """Check the MEASURED rollout batch size against the load-bearing floor."""

    floor = (invariants or GradInvariants()).min_rollout_batch
    if batch_size < floor and not allow_small:
        raise GradInvariantError(
            f"rollout batch {batch_size} < {floor}: batch-1 bnb decode (~20-25 tok/s) drops throughput "
            "below the viable floor; pass allow_small=True only for debugging"
        )


def assert_train_memory(
    peak_gb: float,
    *,
    checkpointing_enabled: bool,
    invariants: GradInvariants | None = None,
) -> None:
    """Check MEASURED training peak memory and the checkpointing condition."""

    inv = invariants or GradInvariants()
    if not checkpointing_enabled:
        raise GradInvariantError("gradient checkpointing is off: measured designs OOM at micro-batch 4 x 1.6k")
    limit = inv.gpu_budget_gb * inv.memory_headroom
    if peak_gb > limit:
        raise GradInvariantError(f"measured training peak {peak_gb:.1f}GB exceeds {limit:.1f}GB budget")


__all__ = [
    "GradInvariantError",
    "GradInvariants",
    "SCHEMA_GRAD_CONFIG",
    "assert_rollout_batch",
    "assert_train_memory",
]
