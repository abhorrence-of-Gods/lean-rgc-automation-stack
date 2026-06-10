from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any
import json

from .schemas import LeanTask, ProofState, TacticAction, write_jsonl, read_jsonl, stable_hash
from .lean.executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor
from .carrier_exposure import CarrierNormalizer
from .candidates import TacticCandidateGenerator, CandidateGeneratorConfig
from .dataset import summarize_response_rows, write_run_report
from dataclasses import asdict, is_dataclass


EXPOSURE_OK = {"success", "partial", "dry_run"}


def _append_prefix(old: str, new: str) -> str:
    old = (old or "").rstrip()
    new = (new or "").strip()
    if not old:
        return new
    if not new:
        return old
    return old + "\n" + new


def _action_from_exposure(exp, *, task_id: str) -> TacticAction:
    tactic = exp.prefix_tactic.strip() or "skip"
    if tactic == "skip":
        # Lean has no skip tactic in theorem script context; `skip` is accepted in tactic mode.
        tactic = "skip"
    return TacticAction(
        action_id="exposure_" + stable_hash({"task": task_id, "prefix": exp.prefix_tactic, "kind": exp.kind}, 12),
        tactic=tactic,
        tactic_class="exposure." + exp.kind,
        carrier_tags=list(exp.carrier_tags or []) + ["exposure"],
        cost_estimate=float(exp.cost),
        metadata={"generated_by": "focused_exposure", "exposure": exp.to_dict(), "task_id": task_id},
    )


def _response_row(task: LeanTask, state: ProofState, action: TacticAction, rec, before, after, extractor: ProofDefectExtractor, *, phase: str, parent_exposure: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    resp, flat, keys = extractor.response(before, after)
    rec.defect_before = before.to_dict()
    rec.defect_after = after.to_dict()
    rec.response = resp
    rec.carrier_delta = {k: before.carrier.get(k, 0.0) - after.carrier.get(k, 0.0) for k in sorted(set(before.carrier) | set(after.carrier))}
    ad = rec.to_dict()
    ad["action"] = action.to_dict()
    ad["task_id"] = task.task_id
    ad["target"] = task.statement
    ad["phase"] = phase
    if parent_exposure is not None:
        ad["parent_exposure"] = parent_exposure
    rr = {
        "state_id": state.state_id,
        "task_id": task.task_id,
        "action_id": action.action_id,
        "audit_status": rec.status,
        "response": resp,
        "response_flat": flat,
        "response_keys": keys,
        "defect_before": before.to_dict(),
        "defect_after": after.to_dict(),
        "carrier_delta": rec.carrier_delta,
        "target": task.statement,
        "action": action.to_dict(),
        "phase": phase,
    }
    if parent_exposure is not None:
        rr["parent_exposure"] = parent_exposure
    return ad, rr


def run_focused_micro_audit(
    tasks: list[LeanTask],
    *,
    out_dir: str | Path,
    executor_config: LeanExecutorConfig,
    base_actions: list[TacticAction] | None = None,
    max_exposures: int = 6,
    max_core_actions: int = 16,
    audit_identity_exposure: bool = False,
) -> dict[str, Any]:
    """Two-phase focused audit: structural exposure first, core tactic second.

    This is stricter than composing `intros\nrfl` directly.  It records whether
    `intros` itself is a carrier exposure and then measures the core tactic on
    the exposed frontier task.  File-mode Lean still audits the full prefix+core
    script for the second phase, but records the decomposition explicitly.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    executor = LeanExecutor(executor_config)
    extractor = ProofDefectExtractor()
    normalizer = CarrierNormalizer()
    core_gen = TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_core_actions))
    fixed_cores = list(base_actions or [])

    exposure_audits: list[dict[str, Any]] = []
    exposure_responses: list[dict[str, Any]] = []
    core_audits: list[dict[str, Any]] = []
    core_responses: list[dict[str, Any]] = []
    frontier_tasks: list[dict[str, Any]] = []

    for task in tasks:
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        exposures = normalizer.expose(task, state)[:max_exposures]
        for exp in exposures:
            if not exp.prefix_tactic.strip() and not audit_identity_exposure:
                # Still use identity to generate core candidates below, but do not
                # waste an audit row for it.
                rec = None
                after_state = state
                after_def = before
                exp_ok = True
                exposure_action = _action_from_exposure(exp, task_id=task.task_id)
                exp_row = {"status": "identity", "after_state": state.to_dict(), "action": exposure_action.to_dict(), "exposure": exp.to_dict()}
            else:
                exposure_action = _action_from_exposure(exp, task_id=task.task_id)
                rec = executor.run_tactic(task, exposure_action, state)
                after_state = rec.after_state or state
                after_def = extractor.extract(after_state, rec)
                ad, rr = _response_row(task, state, exposure_action, rec, before, after_def, extractor, phase="exposure")
                ad["exposure"] = exp.to_dict(); rr["exposure"] = exp.to_dict()
                exposure_audits.append(ad); exposure_responses.append(rr)
                exp_ok = rec.status in EXPOSURE_OK
                exp_row = ad
            if not exp_ok:
                continue
            # If exposure closed the theorem, there is no frontier to core-audit.
            if rec is not None and rec.status == "success":
                continue
            prefix = _append_prefix(task.prefix, exp.prefix_tactic)
            if not prefix.strip() and exp.prefix_tactic.strip():
                prefix = exp.prefix_tactic.strip()
            frontier = replace(task, prefix=prefix)
            frontier_tasks.append({**frontier.to_dict(), "parent_task_id": task.task_id, "exposure": exp.to_dict(), "frontier_state": after_state.to_dict()})
            core_actions = fixed_cores if fixed_cores else core_gen.candidates(frontier, after_state)[:max_core_actions]
            # If fixed cores are supplied, keep them bounded too.
            core_actions = core_actions[:max_core_actions]
            frontier_before = extractor.extract(after_state)
            for core in core_actions:
                if not core.tactic.strip():
                    continue
                meta = dict(core.metadata or {})
                meta.update({
                    "generated_by": "focused_core_after_exposure",
                    "parent_exposure": exp.to_dict(),
                    "prefix_tactic": exp.prefix_tactic,
                    "core_tactic": core.tactic,
                    "parent_task_id": task.task_id,
                })
                action = replace(core, action_id="focused_" + stable_hash({"task": task.task_id, "prefix": exp.prefix_tactic, "core": core.tactic}, 14), metadata=meta)
                rec2 = executor.run_tactic(frontier, action, after_state)
                after2 = extractor.extract(rec2.after_state or after_state, rec2)
                ad2, rr2 = _response_row(frontier, after_state, action, rec2, frontier_before, after2, extractor, phase="core_after_exposure", parent_exposure=exp.to_dict())
                core_audits.append(ad2); core_responses.append(rr2)

    write_jsonl(out / "exposure_audit.jsonl", exposure_audits)
    write_jsonl(out / "exposure_responses.jsonl", exposure_responses)
    write_jsonl(out / "frontier_tasks.jsonl", frontier_tasks)
    write_jsonl(out / "core_audit.jsonl", core_audits)
    write_jsonl(out / "core_responses.jsonl", core_responses)
    all_audits = exposure_audits + core_audits
    all_responses = exposure_responses + core_responses
    write_jsonl(out / "micro_audit.jsonl", all_audits)
    write_jsonl(out / "responses.jsonl", all_responses)
    summary = {
        "n_tasks": len(tasks),
        "n_exposure_audits": len(exposure_audits),
        "n_core_audits": len(core_audits),
        "exposure_summary": asdict(summarize_response_rows(exposure_responses)),
        "core_summary": asdict(summarize_response_rows(core_responses)),
        "all_summary": asdict(summarize_response_rows(all_responses)),
        "out": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = ["run_focused_micro_audit"]
