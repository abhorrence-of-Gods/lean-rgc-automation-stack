from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any
import numpy as np

from .schemas import LeanTask, ProofState, TacticAction
from .lean.executor import LeanExecutor
from .defects import ProofDefectExtractor
from .candidates import TacticCandidateGenerator
from .carrier import LeanCarrierAlgebra
from .selector import RGCTacticSelector, SelectorConfig


@dataclass
class TrajectoryStep:
    step: int
    state_id: str
    selected_action_id: str | None
    selected_tactic: str | None
    selected_status: str | None
    predicted_score: float | None
    defect_norm_before: float
    defect_norm_after: float | None
    response_norm: float | None
    carrier_risk: float | None
    audit_record: dict[str, Any] | None = None
    selection: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryReport:
    task_id: str
    final_status: str
    steps: list[TrajectoryStep]
    prefix: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "final_status": self.final_status, "steps": [s.to_dict() for s in self.steps], "prefix": self.prefix, "metadata": self.metadata}


@dataclass
class TrajectoryConfig:
    max_steps: int = 8
    max_actions: int = 32
    selection_mode: str = "oracle"  # oracle|learner
    carrier_mode: str = "constraint"
    carrier_budget: float = 1.0
    cost_weight: float = 0.1
    append_partial_success: bool = True


class LeanTrajectoryRunner:
    """Minimal file-mode tactic trajectory runner.

    It audits candidate tactics at each step and chooses via RGC selector. This is
    a charted trajectory runner; structured Lean server integration can replace
    the state extraction later without changing the JSON schema.
    """

    def __init__(self, executor: LeanExecutor, config: TrajectoryConfig | None = None):
        self.executor = executor
        self.config = config or TrajectoryConfig()
        self.extractor = ProofDefectExtractor()
        self.carrier = LeanCarrierAlgebra()

    def run(self, task: LeanTask, actions: list[TacticAction] | None = None, model=None) -> TrajectoryReport:
        gen = TacticCandidateGenerator()
        prefix_lines: list[str] = []
        state = ProofState.from_task(task)
        steps: list[TrajectoryStep] = []
        final_status = "max_steps"
        for k in range(self.config.max_steps):
            cur_task = LeanTask(**{**task.to_dict(), "prefix": "\n".join(prefix_lines)})
            defect_before = self.extractor.extract(state)
            cands = (actions or gen.candidates(cur_task, state))[: self.config.max_actions]
            audits = []
            response_preds: dict[str, np.ndarray] = {}
            for a in cands:
                rec = self.executor.run_tactic(cur_task, a, state)
                after_state = rec.after_state or state
                defect_after = self.extractor.extract(after_state, rec)
                resp, flat, keys = self.extractor.response(defect_before, defect_after)
                rec.defect_before = defect_before.to_dict()
                rec.defect_after = defect_after.to_dict()
                rec.response = resp
                rec.carrier_delta = {kk: defect_before.carrier.get(kk, 0.0) - defect_after.carrier.get(kk, 0.0) for kk in sorted(set(defect_before.carrier) | set(defect_after.carrier))}
                flat_arr = np.asarray(flat, dtype=float)
                audits.append((a, rec, defect_after, flat_arr))
                if model is not None and self.config.selection_mode == "learner":
                    try:
                        # Support both ResponseTableLearner-style and LeanResponseLearner-style models.
                        from .learner import ResponseTableLearner
                        pred, _ = ResponseTableLearner.predict(model, a, mode="lcb")
                        response_preds[a.action_id] = np.asarray(pred, dtype=float)
                    except Exception:
                        response_preds[a.action_id] = flat_arr
                else:
                    response_preds[a.action_id] = flat_arr
            selector = RGCTacticSelector(
                SelectorConfig(carrier_budget=self.config.carrier_budget, carrier_mode=self.config.carrier_mode, cost_weight=self.config.cost_weight),
                self.carrier,
            )
            sel = selector.select(state.state_id, defect_before, cands, response_preds)
            selected = next(((a, rec, da, rf) for a, rec, da, rf in audits if a.action_id == sel.selected_action_id), None)
            before_norm = float(np.linalg.norm(defect_before.as_numpy()))
            if selected is None:
                steps.append(TrajectoryStep(k, state.state_id, None, None, None, None, before_norm, None, None, None, selection=sel.to_dict()))
                final_status = "no_action"
                break
            a, rec, defect_after, resp_flat = selected
            after_norm = float(np.linalg.norm(defect_after.as_numpy()))
            risk = self.carrier.carrier_violation_proxy(defect_before, a)
            steps.append(TrajectoryStep(k, state.state_id, a.action_id, a.tactic, rec.status, float(sel.scores.get(a.action_id, 0.0)), before_norm, after_norm, float(np.linalg.norm(resp_flat)), risk, audit_record=rec.to_dict(), selection=sel.to_dict()))
            if rec.status == "success":
                prefix_lines.append(a.tactic)
                final_status = "proved"
                break
            partial = bool((rec.audit_flags or {}).get("partial_success")) or rec.status == "partial_success"
            if partial and self.config.append_partial_success:
                prefix_lines.append(a.tactic)
                state = rec.after_state or state
                continue
            if rec.status in {"timeout", "unsafe", "elab_error"}:
                final_status = rec.status
                break
            final_status = "stuck"
            break
        return TrajectoryReport(task_id=task.task_id, final_status=final_status, steps=steps, prefix="\n".join(prefix_lines), metadata={"trajectory_config": asdict(self.config)})
