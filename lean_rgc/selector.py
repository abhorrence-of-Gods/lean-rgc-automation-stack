from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .schemas import DefectVector, RGCSelection, TacticAction
from .carrier import LeanCarrierAlgebra


@dataclass
class SelectorConfig:
    carrier_budget: float = 1.0
    carrier_mode: str = "constraint"  # off|penalty|constraint
    carrier_penalty: float = 1.0
    cost_weight: float = 0.1
    use_gamma_tail: bool = False


class RGCTacticSelector:
    """Select actions from predicted response vectors under carrier constraints."""

    def __init__(self, config: SelectorConfig | None = None, carrier: LeanCarrierAlgebra | None = None):
        self.config = config or SelectorConfig()
        self.carrier = carrier or LeanCarrierAlgebra()

    def select(self, state_id: str, defect: DefectVector, actions: list[TacticAction], response_preds: dict[str, np.ndarray], normal: np.ndarray | None = None, gamma_scores: dict[str, float] | None = None) -> RGCSelection:
        if normal is None:
            normal = defect.as_numpy()
        risks = self.carrier.action_risks(defect, actions)
        scores: dict[str, float] = {}
        best_id: str | None = None
        best_score = -1e100
        for a in actions:
            r = response_preds.get(a.action_id)
            if r is None:
                score = -1e9
            else:
                score = float(np.dot(normal, r)) - self.config.cost_weight * a.cost_estimate
                if gamma_scores and self.config.use_gamma_tail:
                    score += float(gamma_scores.get(a.action_id, 0.0))
                risk = risks.get(a.action_id, 0.0)
                if self.config.carrier_mode == "constraint" and risk > self.config.carrier_budget:
                    score = -1e9 - risk
                elif self.config.carrier_mode == "penalty":
                    score -= self.config.carrier_penalty * risk
            scores[a.action_id] = score
            if score > best_score:
                best_id, best_score = a.action_id, score
        return RGCSelection(state_id=state_id, selected_action_id=best_id, scores=scores, carrier_risks=risks, gamma_scores=gamma_scores or {}, metadata={"best_score": best_score})
