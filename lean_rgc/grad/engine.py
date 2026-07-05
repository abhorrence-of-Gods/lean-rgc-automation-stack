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
from .collect import preserve_wave_rows
from .config import GradInvariantError, GradInvariants, assert_rollout_batch, assert_train_memory
from .estimators import (
    DEFAULT_SUCCESS_STATUSES,
    SCHEMA_GRAD_UPDATE,
    SCHEMA_RFT_TRACE,
    grouped_rloo,
    stratified_groups,
)


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
    stripped = text.strip()
    if not stripped:
        return ""
    # Tolerate proposal-JSON outputs (the v89 boundary format the base model
    # has seen): extract the first lean_tactic instead of sending raw JSON
    # to Lean. The prompt asks for a bare tactic, so this is a fallback.
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped.rstrip(";").strip())
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            proposals = obj.get("proposals")
            if isinstance(proposals, list):
                for p in proposals:
                    if isinstance(p, dict):
                        tactic = str(p.get("lean_tactic") or p.get("tactic") or "").strip()
                        if tactic:
                            return tactic
    line = stripped.splitlines()[0].strip()
    if line.startswith("```"):
        lines = [l for l in stripped.splitlines() if not l.strip().startswith("```")]
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
                output_schema="lean-rgc-grad-raw-tactic-v96.1",
            )
            # The raw-tactic instruction REPLACES the JSON-proposal one;
            # appending it after the JSON instruction left two contradicting
            # format demands and the model followed the JSON one.
            system, user = render_boundary(boundary, output_instruction=GRAD_SYSTEM_SUFFIX)
            prompts.append(
                {
                    "task_id": task.task_id,
                    "boundary": boundary,
                    "system": system,
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
        if self.inv.adapter_path:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, self.inv.adapter_path, is_trainable=True)
        else:
            model = get_peft_model(model, lora)
        if self.inv.gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()
        self._model = model
        params = [p for p in model.parameters() if p.requires_grad]
        self._optimizer = torch.optim.AdamW(params, lr=self.inv.learning_rate)

    def save_adapter(self, path: str | Path) -> str:
        """Persist the LoRA adapter (per-wave checkpoints; prereg: the
        evaluated model is the LAST checkpoint, no post-hoc selection)."""
        self._ensure_loaded()
        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)
        self._model.save_pretrained(str(out))
        return str(out)

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

        losses = {"rft": 0.0, "rloo": 0.0, "kl_per_seq": 0.0, "rft_kl_per_seq": 0.0}
        n_processed = 0
        n_kl_gated = 0
        for sample in rft_active:
            logprobs = self._completion_logprobs(sample)
            if logprobs is None:
                continue
            loss = -logprobs.mean()
            if self.inv.rft_kl_beta > 0:
                # Drift guard on the MAIN gradient path (G1 prerequisite):
                # a penalty, not a gate — a Lean-verified trace is never
                # skipped, only bounded toward the base policy. Without
                # this the RFT path had NO drift constraint at all.
                with self._model.disable_adapter(), torch.no_grad():
                    ref_logprobs = self._completion_logprobs(sample)
                rft_kl_seq = (logprobs - ref_logprobs).sum()
                losses["rft_kl_per_seq"] += float(rft_kl_seq)
                loss = loss + self.inv.rft_kl_beta * rft_kl_seq
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


# Messages produced when the auditor could not run Lean at all (missing
# binary, broken PATH/workdir). Rewarding or feeding back these rows would
# poison the whole run, so they are gated, not scored.
_INFRA_FAILURE_MARKERS = ("FileNotFoundError(", "PermissionError(", "NotADirectoryError(")


def _is_infra_failure(row: dict[str, Any]) -> bool:
    return any(m in str(msg) for msg in (row.get("messages") or []) for m in _INFRA_FAILURE_MARKERS)


def _run_positive_control(
    audit: Callable[..., list[dict[str, Any]]],
    *,
    tasks: list[LeanTask],
    out: Path,
    run_id: str,
    success: set[str],
    runner_kwargs: dict[str, Any],
) -> None:
    """Verify the audit path can prove `True := by trivial` before spending
    a wave. The pilots taught this the hard way: a broken Lean environment
    returns plain failures, which are indistinguishable from model failures
    downstream (protocol: positive control before any scored run)."""

    control = LeanTask(
        task_id="__positive_control__",
        statement="True",
        imports=list(tasks[0].imports) if tasks else [],
    )
    rows = audit(
        tasks=[control],
        actions_by_task={
            control.task_id: [
                {"action_id": "control_trivial", "tactic": "trivial", "metadata": {"boundary_id": "pb_control"}}
            ]
        },
        wave_dir=out / "wave_control",
        run_id=f"{run_id}_control",
        **runner_kwargs,
    )
    ok = any(str(r.get("audit_status") or r.get("status") or "") in success for r in rows)
    if not ok:
        details = [str((r.get("messages") or ["<no message>"])[0])[:300] for r in rows[:3]] or ["<no rows>"]
        raise GradInvariantError(
            "positive control failed: the audit path could not verify "
            f"'theorem : True := by trivial' (messages: {details}). Lean/lake is broken or "
            "unreachable from this process; refusing to run waves whose rewards and feedback "
            "would be infrastructure noise."
        )


def _gini(counts: list[int]) -> float:
    """Gini coefficient of the per-task trace distribution (0 = even)."""
    if not counts:
        return 0.0
    xs = sorted(counts)
    n = len(xs)
    total = sum(xs)
    if total == 0 or n == 1:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    return float((2.0 * cum) / (n * total) - (n + 1.0) / n)


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
    difficulty: dict[str, float] | None = None,
    online_difficulty: bool = False,
    train: bool = True,
    samples_per_task: int | None = None,
    save_checkpoints: bool = False,
    **runner_kwargs: Any,
) -> dict[str, Any]:
    """Alternating wavefront: rollout -> Lean audit -> RFT+RLOO update.

    Every update row carries measured KL/memory/throughput plus the audit
    coverage counters (n_unaudited, n_empty_tactic) so silent starvation of
    any signal path is visible in grad_run.jsonl.

    `difficulty` (task_id -> historical success rate, see grad/difficulty.py)
    switches RLOO from per-task grouping to difficulty-stratified grouping
    with the difficulty as a state-level control variate — a state baseline
    cancels identically inside pure per-task groups, so stratification is
    its precondition, not an option (empirical degenerate-group rate is
    62-67%, not the design-review 43%).
    """

    inv = invariants or GradInvariants()
    inv.validate()
    eng = engine or RolloutEngine(inv)
    audit = wave_audit_runner or _default_wave_audit
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    success = set(success_statuses)
    _run_positive_control(
        audit, tasks=tasks, out=out, run_id=run_id, success=success, runner_kwargs=runner_kwargs
    )

    solved: set[str] = set()
    first_solve_wave: dict[str, int] = {}
    feedback: dict[str, str] = {}
    update_rows: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []
    # Online difficulty (G1 prereg: recomputed from the run's OWN accumulated
    # wave rows after each wave; wave 0 runs unstratified; no external
    # history enters training).
    diff_succ: dict[str, float] = {}
    diff_tot: dict[str, float] = {}

    for wave in range(n_waves):
        live = [t for t in tasks if t.task_id not in solved]
        if not live:
            break
        # Snapshot BEFORE this wave's rewards exist: a baseline computed from
        # the current wave's own outcomes would correlate with the rewards it
        # is subtracted from (biased control variate). Wave 0: unstratified.
        wave_difficulty = difficulty
        if wave_difficulty is None and online_difficulty and diff_tot:
            total = sum(diff_tot.values())
            p0 = sum(diff_succ.values()) / total
            wave_difficulty = {
                t: (diff_succ.get(t, 0.0) + 20.0 * p0) / (diff_tot[t] + 20.0) for t in diff_tot
            }
        # Top up per-task samples so the wavefront never sinks below the
        # verified batch floor as tasks are solved (review major).
        if samples_per_task is not None:
            # Eval-mode attempt semantics: a fixed number of sequential
            # attempts per theorem; late small batches are allowed (RLOO
            # never runs there, so the batch floor is throughput-only).
            n_samples = samples_per_task
        else:
            n_samples = max(inv.group_size, math.ceil(inv.min_rollout_batch / len(live)))
        prompts = eng.render_prompts(live, feedback, wave)
        samples = eng.generate(
            prompts, n_samples=n_samples, seed=inv.seed + wave,
            allow_small_batch=samples_per_task is not None,
        )
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
        n_infra_failures = 0
        for row in rows:
            action = row.get("action") if isinstance(row.get("action"), dict) else {}
            aid = str(row.get("action_id") or action.get("action_id") or "")
            if aid not in by_action:
                continue
            if _is_infra_failure(row):
                # Lean never ran: not a model failure. Leave the sample
                # unaudited (excluded from RLOO) and never feed the OS error
                # back to the model as if it were a Lean message.
                n_infra_failures += 1
                continue
            audited.add(aid)
            status = str(row.get("audit_status") or row.get("status") or "")
            ok = status in success
            rewards[aid] = max(rewards.get(aid, 0.0), 1.0 if ok else 0.0)
            sample = by_action[aid]
            diff_tot[sample["task_id"]] = diff_tot.get(sample["task_id"], 0.0) + 1.0
            if ok:
                diff_succ[sample["task_id"]] = diff_succ.get(sample["task_id"], 0.0) + 1.0
            if ok:
                if sample["task_id"] not in solved:
                    first_solve_wave[sample["task_id"]] = wave
                solved.add(sample["task_id"])
            else:
                msgs = row.get("messages") or []
                if msgs:
                    feedback[sample["task_id"]] = f"Lean error: {str(msgs[0])[:500]}"
        if rows and n_infra_failures > len(rows) / 2:
            raise GradInvariantError(
                f"wave {wave}: {n_infra_failures}/{len(rows)} audit rows failed before Lean ran "
                "(infrastructure errors, e.g. missing lake on PATH); aborting instead of training "
                "on infrastructure noise"
            )
        n_unaudited = 0
        records: list[dict[str, Any]] = []
        for aid, sample in by_action.items():
            if sample["tactic"] and aid not in audited:
                n_unaudited += 1  # excluded: an unaudited sample is not a failure (review major)
                continue
            records.append({
                "task_id": sample["task_id"],
                "action_id": aid,
                "wave_index": wave,
                "reward": rewards.get(aid, 0.0),  # empty tactics: definitional 0
                "sample": sample,
            })
        if wave_difficulty is not None:
            grouped_recs = stratified_groups(records, group_size=inv.group_size, difficulty=wave_difficulty)
        else:
            grouped_recs = {}
            for rec in records:
                grouped_recs.setdefault(rec["task_id"], []).append(rec)
        grouped_recs = {k: v for k, v in grouped_recs.items() if len(v) >= 2}
        groups = {k: [r["reward"] for r in v] for k, v in grouped_recs.items()}
        members = {k: [r["sample"] for r in v] for k, v in grouped_recs.items()}
        baselines = None
        if wave_difficulty is not None:
            baselines = {
                k: [float(wave_difficulty.get(str(r["task_id"]), 0.5)) for r in v]
                for k, v in grouped_recs.items()
            }
        advantages, rloo_stats = grouped_rloo(groups, baselines=baselines)
        rloo_batch: list[tuple[dict[str, Any], float]] = []
        for key, advs in advantages.items():
            for sample, adv in zip(members[key], advs):
                rloo_batch.append((sample, float(adv)))
        raw_traces = [by_action[aid] for aid in sorted(audited) if rewards.get(aid, 0.0) > 0.5]
        # G1 prerequisite: dedup identical (task, tactic) within the wave and
        # cap traces per task — empirical duplication is 3.2x and gradient
        # mass proportional to success frequency is rich-get-richer by
        # construction (unguarded expert-iteration collapse mode).
        trace_samples = []
        seen_tt: set[tuple[str, str]] = set()
        per_task_traces: dict[str, int] = {}
        n_rft_dedup_dropped = 0
        n_rft_cap_dropped = 0
        for s in raw_traces:
            tt = (s["task_id"], s["tactic"])
            if tt in seen_tt:
                n_rft_dedup_dropped += 1
                continue
            seen_tt.add(tt)  # before the cap check: a capped tactic's
            # duplicates are duplicates, not additional cap victims.
            if per_task_traces.get(s["task_id"], 0) >= inv.rft_max_traces_per_task:
                n_rft_cap_dropped += 1
                continue
            per_task_traces[s["task_id"]] = per_task_traces.get(s["task_id"], 0) + 1
            trace_samples.append(s)
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
        if train:
            update = eng.train_step(rft_samples=trace_samples, rloo_samples=rloo_batch)
            if save_checkpoints and hasattr(eng, "save_adapter"):
                update["checkpoint"] = eng.save_adapter(out / "checkpoints" / f"wave_{wave}")
        else:
            update = {"skipped": "eval_mode"}
        # Collapse early-warning gauge (G1 prerequisite): trace concentration.
        trace_counts = sorted(per_task_traces.values(), reverse=True)
        n_tr = sum(trace_counts)
        concentration = {
            "n_tasks_with_traces": len(trace_counts),
            "top1_share": (trace_counts[0] / n_tr) if n_tr else 0.0,
            "gini": _gini(trace_counts),
        }
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
                "n_infra_failures": n_infra_failures,
                "audit_anomaly": audit_anomaly,
                "n_rft_traces": len(trace_samples),
                "n_rft_dedup_dropped": n_rft_dedup_dropped,
                "n_rft_cap_dropped": n_rft_cap_dropped,
                "trace_concentration": concentration,
                "train_enabled": train,
                "rloo_grouping": "stratified" if wave_difficulty is not None else "task",
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
    # Episode rows (paired-bootstrap compatible; the G1 eval-mode contract).
    episodes = [
        {
            "schema_version": "lean-rgc-grad-episode-v97.0",
            "run_id": run_id,
            "arm": run_id,
            "task_id": t.task_id,
            "solved": t.task_id in solved,
            "first_solve_wave": first_solve_wave.get(t.task_id),
            "n_waves": len(update_rows),
            "train_enabled": train,
        }
        for t in tasks
    ]
    write_jsonl(out / "episodes.jsonl", episodes)
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
    # Wave rows are the training table for every learned factor downstream;
    # the pilots lost them once (only episodes left the pod). Preservation is
    # code, not ops discipline: failures land in the summary, never raise.
    # Runs after the summary write so the archive captures grad_summary.json,
    # then the summary is rewritten with the preservation receipt.
    summary["wave_preservation"] = preserve_wave_rows(out)
    (out / "grad_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return summary


__all__ = ["GRAD_SYSTEM_SUFFIX", "RolloutEngine", "run_grad_loop"]
