from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import LeanTask, ProofState, TacticAction, DefectVector, read_jsonl, write_jsonl, stable_hash
from .lean.executor import LeanExecutor
from .defects import ProofDefectExtractor
from .carrier import LeanCarrierAlgebra


def context_to_actions(ctx: dict[str, Any], *, prefix: str = "gen") -> list[TacticAction]:
    kind = str(ctx.get("kind", "generated"))
    suggestions = ctx.get("suggestions") or ctx.get("tactics") or []
    actions: list[TacticAction] = []
    if kind == "premise_retrieval":
        lemmas = ctx.get("candidate_lemmas") or ctx.get("lemmas") or []
        query = str(ctx.get("query", ""))
        if not lemmas and query:
            # Keep a conservative generated premise-search chart.
            suggestions = suggestions or ["simp_all", "assumption"]
        for lemma in lemmas[:16]:
            suggestions.append(f"apply {lemma}")
            suggestions.append(f"rw [{lemma}]")
    elif kind == "simp_set_extension":
        lemmas = ctx.get("lemmas") or []
        if lemmas:
            suggestions.append("simp [" + ", ".join(map(str, lemmas[:12])) + "]")
    for i, tac in enumerate(suggestions[:32]):
        if not isinstance(tac, str) or not tac.strip():
            continue
        cls = "generated"
        tags = ["generated", kind]
        low = tac.lower()
        if "simp" in low:
            cls = "simp"; tags.append("simp")
        if "induction" in low:
            cls = "induction"; tags.append("induction")
        if "rw" in low:
            cls = "rewrite"; tags.append("rewrite")
        if "apply" in low or "exact" in low or "assumption" in low:
            cls = "apply" if "apply" in low else "exact"; tags.append("premise")
        aid = stable_hash({"prefix": prefix, "kind": kind, "tactic": tac, "i": i}, 14)
        actions.append(TacticAction(action_id=aid, tactic=tac, tactic_class=cls, carrier_tags=tags, cost_estimate=float(ctx.get("cost", 1.0))))
    return actions


@dataclass
class CarrierAcceptanceRecord:
    task_id: str
    state_id: str
    context_kind: str
    action_id: str
    tactic: str
    status: str
    carrier_delta_l1: float
    carrier_residual_l1_before: float
    carrier_residual_l1_after: float
    coker_margin_proxy: float
    cost: float
    accepted: bool
    residual_atoms: list[str]
    audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CarrierContextAcceptor:
    """Micro-audit generated carrier contexts and accept by coker-margin proxy."""

    def __init__(self, executor: LeanExecutor, *, margin_threshold: float = 0.0, cost_weight: float = 0.1):
        self.executor = executor
        self.margin_threshold = float(margin_threshold)
        self.cost_weight = float(cost_weight)
        self.extractor = ProofDefectExtractor()
        self.carrier = LeanCarrierAlgebra()

    def audit_contexts(self, task: LeanTask, proposal_row: dict[str, Any], *, max_actions: int = 32) -> list[CarrierAcceptanceRecord]:
        state = ProofState.from_task(task)
        before = self.extractor.extract(state)
        residual_atoms = list(proposal_row.get("residual_atoms") or [])
        contexts = proposal_row.get("generated_contexts") or []
        records: list[CarrierAcceptanceRecord] = []
        for ctx_idx, ctx in enumerate(contexts):
            actions = context_to_actions(ctx, prefix=f"{task.task_id}:{ctx_idx}")[:max_actions]
            for action in actions:
                audit = self.executor.run_tactic(task, action, state)
                after_state = audit.after_state or state
                after = self.extractor.extract(after_state, audit)
                # Positive carrier improvement on residual atoms.
                before_car = before.carrier
                after_car = after.carrier
                delta_by_atom = {k: float(before_car.get(k, 0.0) - after_car.get(k, 0.0)) for k in set(before_car) | set(after_car)}
                if residual_atoms:
                    carrier_delta_l1 = sum(max(0.0, delta_by_atom.get(k, 0.0)) for k in residual_atoms)
                    before_l1 = sum(max(0.0, before_car.get(k, 0.0)) for k in residual_atoms)
                    after_l1 = sum(max(0.0, after_car.get(k, 0.0)) for k in residual_atoms)
                else:
                    carrier_delta_l1 = sum(max(0.0, v) for v in delta_by_atom.values())
                    before_l1 = sum(max(0.0, v) for v in before_car.values())
                    after_l1 = sum(max(0.0, v) for v in after_car.values())
                cost = float(action.cost_estimate)
                audit_penalty = 1.0 if audit.status in {"timeout", "unsafe", "elab_error"} else 0.0
                margin = float(carrier_delta_l1 - self.cost_weight * cost - audit_penalty)
                accepted = bool(margin > self.margin_threshold and audit.status not in {"timeout", "unsafe", "elab_error"})
                records.append(CarrierAcceptanceRecord(
                    task_id=task.task_id,
                    state_id=state.state_id,
                    context_kind=str(ctx.get("kind", "generated")),
                    action_id=action.action_id,
                    tactic=action.tactic,
                    status=audit.status,
                    carrier_delta_l1=float(carrier_delta_l1),
                    carrier_residual_l1_before=float(before_l1),
                    carrier_residual_l1_after=float(after_l1),
                    coker_margin_proxy=margin,
                    cost=cost,
                    accepted=accepted,
                    residual_atoms=residual_atoms,
                    audit=audit.to_dict(),
                ))
        return records


def accept_carrier_contexts(tasks_path: str | Path, proposals_path: str | Path, out: str | Path, executor: LeanExecutor, *, max_actions: int = 32, margin_threshold: float = 0.0, cost_weight: float = 0.1) -> list[dict[str, Any]]:
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    tasks_by_id = {t.task_id: t for t in tasks}
    proposals = read_jsonl(proposals_path)
    acceptor = CarrierContextAcceptor(executor, margin_threshold=margin_threshold, cost_weight=cost_weight)
    rows: list[dict[str, Any]] = []
    for p in proposals:
        task_id = str(p.get("task_id") or p.get("state_id") or "")
        task = tasks_by_id.get(task_id)
        if task is None and len(tasks) == 1:
            task = tasks[0]
        if task is None:
            # Try match state id from task initial state.
            for t in tasks:
                if ProofState.from_task(t).state_id == p.get("state_id"):
                    task = t; break
        if task is None:
            rows.append({"proposal": p, "error": "could_not_match_task"})
            continue
        for rec in acceptor.audit_contexts(task, p, max_actions=max_actions):
            rows.append(rec.to_dict())
    write_jsonl(out, rows)
    return rows
