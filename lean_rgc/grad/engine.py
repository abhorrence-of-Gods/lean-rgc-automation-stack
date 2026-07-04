"""Rollout engine and alternating gradient loop.

Import of this module is torch-free; torch/transformers/peft are imported
lazily inside RolloutEngine methods so the default CI can exercise the loop
orchestration with an injected fake engine.

The engine implements the verified load-bearing conditions and the fixes
from the adversarial review of 2026-07-04:
  - model.train()/eval() switching (checkpointing is gated on training mode)
  - raw (unwarped) rollout logprobs via output_logits, batch-vectorized
  - sampled completion ids kept verbatim (eos included) — no retokenization
  - full-sample gradient accumulation normalized by processed terms
  - per-sequence KL with a non-saturating gate instead of a clamped penalty
  - wavefront batch floor topped up by raising n_samples per live task
  - unaudited samples excluded from RLOO; empty tactics kept as reward-0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import json
import math
import time

from ..pbct.boundary import build_prompt_boundary, render_boundary
from ..schemas import LeanTask, stable_hash, write_jsonl
from .config import GradInvariants, assert_rollout_batch, assert_train_memory
from .estimators import DEFAULT_SUCCESS_STATUSES, SCHEMA_GRAD_UPDATE, SCHEMA_RFT_TRACE, grouped_rloo


GRAD_SYSTEM_SUFFIX = (
    "Output exactly one Lean 4 tactic (or a short semicolon-separated tactic block) "
    "and nothing else: no JSON, no prose, no code fences."
)


def _require_torch():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise ImportError(
            "the gradient loop needs the [grad] extra: pip install -e .[grad] "
            "(torch, transformers, peft, bitsandbytes, accelerate)"
        ) from exc


def _clean_tactic(text: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if line.startswith("```"):
        lines = [l for l in text.strip().splitlines() if not l.strip().startswith("```")]
        line = lines[0].strip() if lines else ""
    return line


class RolloutEngine:
    """Hard-prompt QLoRA policy engine (soft prefixes arrive in v97)."""

    def __init__(self, invariants: GradInvariants | None = None, device: str = "cuda"):
        self.inv = invariants or GradInvariants()
        self.inv.validate()
        self.device = device
        self._model = None
        self._tokenizer = None
        self._optimizer = None
        self._last_rollout: dict[str, Any] = {}

    # ---- torch-free prompt construction -------------------------------
    def render_prompts(
        self,
        tasks: list[LeanTask],
        feedback_by_task: dict[str, str],
        attempt_index: int,
    ) -> list[dict[str, Any]]:
        prompts = []
        for task in tasks:
            boundary = build_prompt_boundary(
                task=task,
                boundary_kind="grad_tactic_synthesis",
                feedback_text=feedback_by_task.get(task.task_id, ""),
                attempt_index=attempt_index,
                max_proposals=1,
            )
            system, user = render_boundary(boundary)
            prompts.append(
                {
                    "task_id": task.task_id,
                    "boundary": boundary,
                    "system": f"{system}\n{GRAD_SYSTEM_SUFFIX}",
                    "user": user,
                }
            )
        return prompts

    # ---- torch-lazy internals ------------------------------------------
    def _ensure_loaded(self):
        if self._model is not None:
            return
        _require_torch()
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        # Prequantized checkpoints (e.g. *-bnb-4bit) carry their own
        # quantization_config; passing another one conflicts. They satisfy
        # the load_in_4bit invariant by construction.
        prequantized = "bnb-4bit" in self.inv.model_name.lower()
        quant = (
            BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            if self.inv.load_in_4bit and not prequantized
            else None
        )
        self._tokenizer = AutoTokenizer.from_pretrained(self.inv.model_name)
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        self._tokenizer.padding_side = "left"
        # transformers v5 treats an explicit quantization_config=None as an
        # override that DISABLES the checkpoint's own quantization_config,
        # so prequantized weights then fail with shape mismatches; only pass
        # the kwarg when we quantize at load time.
        load_kwargs: dict[str, Any] = {"torch_dtype": torch.bfloat16, "device_map": {"": 0}}
        if quant is not None:
            load_kwargs["quantization_config"] = quant
        model = AutoModelForCausalLM.from_pretrained(self.inv.model_name, **load_kwargs)
        lora = LoraConfig(
            r=self.inv.lora_r,
            lora_alpha=self.inv.lora_alpha,
            lora_dropout=self.inv.lora_dropout,
            target_modules="all-linear",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora)
        if self.inv.gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()
        self._model = model
        params = [p for p in model.parameters() if p.requires_grad]
        self._optimizer = torch.optim.AdamW(params, lr=self.inv.learning_rate)

    def _chat_ids(self, system: str, user: str) -> list[int]:
        # return_dict=False keeps the flat list[int] contract on both
        # transformers 4.x (where it is the default) and 5.x (where the
        # default flipped to a BatchEncoding, which tok.pad rejects).
        return self._tokenizer.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            add_generation_prompt=True,
            tokenize=True,
            return_dict=False,
            return_tensors=None,
        )

    def _measured_peak_gb(self) -> float:
        import torch

        return float(torch.cuda.max_memory_allocated() / 2**30) if torch.cuda.is_available() else 0.0

    def _truncate_at_eos(self, comp_ids: list[int]) -> list[int]:
        """Keep the sampled ids verbatim up to and INCLUDING the first eos."""

        tok = self._tokenizer
        out: list[int] = []
        for tid in comp_ids:
            if tid == tok.pad_token_id and tok.pad_token_id != tok.eos_token_id:
                break
            out.append(tid)
            if tid == tok.eos_token_id:
                break
        return out

    # ---- rollout --------------------------------------------------------
    def generate(
        self,
        prompts: list[dict[str, Any]],
        *,
        n_samples: int,
        seed: int = 0,
        allow_small_batch: bool = False,
    ) -> list[dict[str, Any]]:
        """Sample n_samples completions per prompt.

        Cached rollout logprobs come from output_logits (raw, pre-warp), so
        they are genuine pi_theta values; the sampled token ids are kept
        verbatim (eos included) for training-side reuse.
        """

        self._ensure_loaded()
        import torch

        expanded = [p for p in prompts for _ in range(n_samples)]
        assert_rollout_batch(len(expanded), invariants=self.inv, allow_small=allow_small_batch)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        self._model.eval()  # checkpointing off, KV cache on: linear-time decode
        tok = self._tokenizer
        # output_logits retains every decode step's (B, vocab) logits until
        # we gather from them, so memory grows with batch x steps x vocab —
        # a full wavefront (hundreds of sequences) at max_new_tokens would
        # OOM. Decode in chunks; each chunk still satisfies the batch floor.
        chunk_size = max(1, int(self.inv.rollout_chunk))
        samples: list[dict[str, Any]] = []
        elapsed_total = 0.0
        for c0 in range(0, len(expanded), chunk_size):
            chunk = expanded[c0 : c0 + chunk_size]
            ids = [self._chat_ids(p["system"], p["user"]) for p in chunk]
            batch = tok.pad({"input_ids": ids}, return_tensors="pt").to(self._model.device)
            start = time.monotonic()
            with torch.no_grad():
                out = self._model.generate(
                    **batch,
                    do_sample=True,
                    temperature=self.inv.temperature,
                    top_p=self.inv.top_p,
                    max_new_tokens=self.inv.max_new_tokens,
                    return_dict_in_generate=True,
                    output_logits=True,
                    pad_token_id=tok.pad_token_id,
                )
            elapsed_total += time.monotonic() - start
            prompt_len = batch["input_ids"].shape[1]
            completions = out.sequences[:, prompt_len:]
            # Batched raw logprobs, one (B, V) log_softmax per decode step.
            step_logprobs = []
            for t, logits in enumerate(out.logits):
                lp = torch.log_softmax(logits.float(), dim=-1)
                step_logprobs.append(lp.gather(1, completions[:, t : t + 1]).squeeze(1))
            lp_matrix = torch.stack(step_logprobs, dim=1) if step_logprobs else torch.zeros((len(chunk), 0))
            del out, step_logprobs
            for i, prompt in enumerate(chunk):
                comp_ids = self._truncate_at_eos(completions[i].tolist())
                n_tok = len(comp_ids)
                logprob_sum = float(lp_matrix[i, :n_tok].sum()) if n_tok else 0.0
                text = tok.decode(comp_ids, skip_special_tokens=True)
                samples.append(
                    {
                        "task_id": prompt["task_id"],
                        "boundary": prompt["boundary"],
                        "system": prompt["system"],
                        "user": prompt["user"],
                        "text": text,
                        "tactic": _clean_tactic(text),
                        "completion_ids": comp_ids,
                        "rollout_logprob_sum": logprob_sum,
                        "n_completion_tokens": n_tok,
                    }
                )
        total_new = sum(s["n_completion_tokens"] for s in samples)
        self._last_rollout = {
            "tokens_per_second": total_new / elapsed_total if elapsed_total > 0 else 0.0,
            "peak_gb": self._measured_peak_gb(),
            "batch": len(expanded),
            "n_chunks": math.ceil(len(expanded) / chunk_size),
        }
        return samples

    # ---- training -------------------------------------------------------
    def _completion_logprobs(self, sample: dict[str, Any]):
        """Teacher-forced logprobs of the EXACT sampled completion ids under
        current weights; logits sliced to completion tokens only."""

        import torch

        comp_ids = list(sample.get("completion_ids") or [])
        if not comp_ids:
            comp_ids = self._tokenizer(sample["text"], add_special_tokens=False)["input_ids"]
        if not comp_ids:
            return None
        prompt_ids = self._chat_ids(sample["system"], sample["user"])
        full = torch.tensor([prompt_ids + comp_ids], device=self._model.device)
        n_comp = len(comp_ids)
        out = self._model(input_ids=full, logits_to_keep=n_comp + 1, use_cache=False)
        logits = out.logits[0, :-1].float()
        targets = full[0, -n_comp:]
        return torch.log_softmax(logits[-n_comp:], dim=-1).gather(1, targets.unsqueeze(1)).squeeze(1)

    def train_step(
        self,
        *,
        rft_samples: list[dict[str, Any]],
        rloo_samples: list[tuple[dict[str, Any], float]],
    ) -> dict[str, Any]:
        """One optimizer step over ALL provided samples (accumulated),
        normalized by the number of terms actually backpropagated."""

        self._ensure_loaded()
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        self._model.train()  # gates gradient checkpointing on (review blocker)
        checkpointing_active = self.inv.gradient_checkpointing and bool(self._model.training)
        self._optimizer.zero_grad(set_to_none=True)

        rft_active = [s for s in rft_samples if (s.get("completion_ids") or s.get("text", "").strip())]
        rloo_active = [(s, a) for s, a in rloo_samples if abs(a) >= 1e-12]
        n_total_terms = max(1, len(rft_active) + len(rloo_active))

        losses = {"rft": 0.0, "rloo": 0.0, "kl_per_seq": 0.0}
        n_processed = 0
        n_kl_gated = 0
        for sample in rft_active:
            logprobs = self._completion_logprobs(sample)
            if logprobs is None:
                continue
            loss = -logprobs.mean()
            (loss / n_total_terms).backward()
            losses["rft"] += float(loss)
            n_processed += 1
        for sample, advantage in rloo_active:
            logprobs = self._completion_logprobs(sample)
            if logprobs is None:
                continue
            with self._model.disable_adapter(), torch.no_grad():
                ref_logprobs = self._completion_logprobs(sample)
            kl_seq = (logprobs - ref_logprobs).sum()  # per-sequence units
            losses["kl_per_seq"] += float(kl_seq)
            if float(kl_seq) > self.inv.kl_hard_cap_per_seq:
                # Gate, do not clamp: a clamped penalty has zero gradient
                # exactly where the constraint binds (review major).
                n_kl_gated += 1
                continue
            loss = -(float(advantage) * logprobs.sum()) + self.inv.kl_beta * kl_seq
            (loss / n_total_terms).backward()
            losses["rloo"] += float(loss)
            n_processed += 1
        grad_norm = float(
            torch.nn.utils.clip_grad_norm_(
                [p for p in self._model.parameters() if p.requires_grad], 1.0
            )
        )
        self._optimizer.step()
        self._model.eval()
        peak = self._measured_peak_gb()
        assert_train_memory(peak, checkpointing_enabled=checkpointing_active, invariants=self.inv)
        return {
            "losses": losses,
            "n_terms": n_processed,
            "n_rft_in": len(rft_active),
            "n_rloo_in": len(rloo_active),
            "n_kl_gated": n_kl_gated,
            "grad_norm": grad_norm,
            "train_peak_gb": peak,
        }

    def smoke(self, *, batch_sizes: tuple[int, ...] = (1, 8, 16), train_probe: bool = True) -> dict[str, Any]:
        """Measured (not asserted) throughput/memory over dummy prompts.

        The train probe runs one real optimizer step over samples from the
        last rollout so the full training path (teacher forcing, KL reference
        via disable_adapter, checkpointing, memory assert) is exercised before
        a long run pays a full rollout+audit wave to discover a break.
        """

        task = LeanTask(task_id="smoke", statement="True", imports=[])
        report: dict[str, Any] = {"batches": []}
        samples: list[dict[str, Any]] = []
        for b in batch_sizes:
            prompts = self.render_prompts([task] * b, {}, 0)
            samples = self.generate(prompts, n_samples=1, allow_small_batch=True)
            report["batches"].append({"batch": b, **self._last_rollout})
        if train_probe and len(samples) >= 3:
            report["train_probe"] = self.train_step(
                rft_samples=[samples[0]],
                rloo_samples=[(samples[1], 1.0), (samples[2], -1.0)],
            )
        return report


def _default_wave_audit(
    *, tasks: list[LeanTask], actions_by_task: dict[str, list[dict[str, Any]]], wave_dir: Path, run_id: str, **kw: Any
) -> list[dict[str, Any]]:
    from ..evals.harness import load_wave_rows
    from ..lean.worker_supervisor import enqueue_and_run_supervised_audit
    from ..schemas import TacticAction

    typed = {t: [TacticAction.from_dict(a) for a in acts] for t, acts in actions_by_task.items()}
    max_actions = max((len(v) for v in typed.values()), default=1)
    enqueue_and_run_supervised_audit(
        db_path=wave_dir / "audit_queue.sqlite",
        tasks=tasks,
        actions_by_task=typed,
        out_dir=wave_dir,
        run_id=run_id,
        max_actions=max(1, max_actions),
        **kw,
    )
    return load_wave_rows(wave_dir)


def run_grad_loop(
    *,
    tasks: list[LeanTask],
    out_dir: str | Path,
    run_id: str,
    invariants: GradInvariants | None = None,
    engine: Any | None = None,
    wave_audit_runner: Callable[..., list[dict[str, Any]]] | None = None,
    n_waves: int = 4,
    success_statuses: tuple[str, ...] = DEFAULT_SUCCESS_STATUSES,
    **runner_kwargs: Any,
) -> dict[str, Any]:
    """Alternating wavefront: rollout -> Lean audit -> RFT+RLOO update.

    Every update row carries measured KL/memory/throughput plus the audit
    coverage counters (n_unaudited, n_empty_tactic) so silent starvation of
    any signal path is visible in grad_run.jsonl.
    """

    inv = invariants or GradInvariants()
    inv.validate()
    eng = engine or RolloutEngine(inv)
    audit = wave_audit_runner or _default_wave_audit
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    success = set(success_statuses)

    solved: set[str] = set()
    feedback: dict[str, str] = {}
    update_rows: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []

    for wave in range(n_waves):
        live = [t for t in tasks if t.task_id not in solved]
        if not live:
            break
        # Top up per-task samples so the wavefront never sinks below the
        # verified batch floor as tasks are solved (review major).
        n_samples = max(inv.group_size, math.ceil(inv.min_rollout_batch / len(live)))
        prompts = eng.render_prompts(live, feedback, wave)
        samples = eng.generate(prompts, n_samples=n_samples, seed=inv.seed + wave)
        actions_by_task: dict[str, list[dict[str, Any]]] = {}
        by_action: dict[str, dict[str, Any]] = {}
        n_empty_tactic = 0
        for i, s in enumerate(samples):
            aid = "grad_" + stable_hash({"run": run_id, "wave": wave, "i": i, "t": s.get("tactic", "")}, 16)
            s["action_id"] = aid
            by_action[aid] = s
            if not s["tactic"]:
                # Kept in the RLOO group with reward 0 (it definitionally
                # fails Lean) but never sent to the auditor (review major).
                n_empty_tactic += 1
                continue
            actions_by_task.setdefault(s["task_id"], []).append(
                {"action_id": aid, "tactic": s["tactic"], "metadata": {"boundary_id": s["boundary"]["boundary_id"]}}
            )
        rows = audit(
            tasks=live,
            actions_by_task=actions_by_task,
            wave_dir=out / f"wave_{wave}",
            run_id=f"{run_id}_w{wave}",
            **runner_kwargs,
        )
        audit_anomaly = bool(actions_by_task) and not rows
        audited: set[str] = set()
        rewards: dict[str, float] = {}
        for row in rows:
            action = row.get("action") if isinstance(row.get("action"), dict) else {}
            aid = str(row.get("action_id") or action.get("action_id") or "")
            if aid not in by_action:
                continue
            audited.add(aid)
            status = str(row.get("audit_status") or row.get("status") or "")
            ok = status in success
            rewards[aid] = max(rewards.get(aid, 0.0), 1.0 if ok else 0.0)
            sample = by_action[aid]
            if ok:
                solved.add(sample["task_id"])
            else:
                msgs = row.get("messages") or []
                if msgs:
                    feedback[sample["task_id"]] = f"Lean error: {str(msgs[0])[:500]}"
        n_unaudited = 0
        groups: dict[str, list[float]] = {}
        members: dict[str, list[dict[str, Any]]] = {}
        for aid, sample in by_action.items():
            if sample["tactic"] and aid not in audited:
                n_unaudited += 1  # excluded: an unaudited sample is not a failure (review major)
                continue
            reward = rewards.get(aid, 0.0)  # empty tactics: definitional 0
            key = sample["task_id"]
            groups.setdefault(key, []).append(reward)
            members.setdefault(key, []).append(sample)
        advantages, rloo_stats = grouped_rloo({k: v for k, v in groups.items() if len(v) >= 2})
        rloo_batch: list[tuple[dict[str, Any], float]] = []
        for key, advs in advantages.items():
            for sample, adv in zip(members[key], advs):
                rloo_batch.append((sample, float(adv)))
        trace_samples = [by_action[aid] for aid in audited if rewards.get(aid, 0.0) > 0.5]
        for s in trace_samples:
            all_traces.append(
                {
                    "schema_version": SCHEMA_RFT_TRACE,
                    "task_id": s["task_id"],
                    "boundary_id": s["boundary"]["boundary_id"],
                    "boundary": s["boundary"],
                    "tactic": s["tactic"],
                    "text": s["text"],  # what the gradient actually reinforces
                    "status": "success",
                    "canonical_status": "rft_trace_is_lean_verified_witness",
                }
            )
        update = eng.train_step(rft_samples=trace_samples, rloo_samples=rloo_batch)
        update_rows.append(
            {
                "schema_version": SCHEMA_GRAD_UPDATE,
                "run_id": run_id,
                "wave": wave,
                "n_live_tasks": len(live),
                "n_samples": len(samples),
                "n_samples_per_task": n_samples,
                "n_empty_tactic": n_empty_tactic,
                "n_unaudited": n_unaudited,
                "audit_anomaly": audit_anomaly,
                "n_rft_traces": len(trace_samples),
                "rloo": rloo_stats.to_dict(),
                "rollout": getattr(eng, "_last_rollout", {}),
                "update": update,
                "n_solved_total": len(solved),
                "canonical_status": "grad_update_is_measured_witness",
            }
        )
        # Crash safety: both artifacts are rewritten every wave (review minor).
        write_jsonl(out / "grad_run.jsonl", update_rows)
        write_jsonl(out / "rft_traces.jsonl", all_traces)
    summary = {
        "schema_version": SCHEMA_GRAD_UPDATE,
        "run_id": run_id,
        "n_tasks": len(tasks),
        "n_solved": len(solved),
        "solve_rate": len(solved) / len(tasks) if tasks else 0.0,
        "n_waves_run": len(update_rows),
        "n_rft_traces": len(all_traces),
        "invariants": inv.to_dict(),
        "updates_out": str(out / "grad_run.jsonl"),
    }
    (out / "grad_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return summary


__all__ = ["GRAD_SYSTEM_SUFFIX", "RolloutEngine", "run_grad_loop"]
