from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


@dataclass
class GammaAuditReport:
    cocycle_resid_norm: float
    cocycle_resid_rel: float
    persistence_resid_norm: float
    gamma_vs_persistence_improvement: float
    tail_value_cos: float | None = None
    tail_value_gain: float | None = None
    spectral_radius_proxy: float | None = None
    metadata: dict = field(default_factory=dict)


class GammaAuditor:
    """Finite-chart Gamma auditor.

    Fits or audits D_next ≈ B + Γ(D - R). Initial use is diagnostic.
    """

    def __init__(self, ridge: float = 1e-3):
        self.ridge = float(ridge)

    def fit_linear_gamma(self, residuals: np.ndarray, next_defects: np.ndarray) -> np.ndarray:
        """Fit Γ from columns residuals -> next_defects by ridge LS.

        residuals: [n_samples, dim], next_defects: [n_samples, dim]
        returns [dim, dim] matrix Γ such that residual @ Γ.T ≈ next.
        """
        X = np.asarray(residuals, dtype=float)
        Y = np.asarray(next_defects, dtype=float)
        if X.ndim != 2 or Y.ndim != 2 or X.shape != Y.shape:
            raise ValueError("residuals and next_defects must have same shape [n, d]")
        d = X.shape[1]
        lhs = X.T @ X + self.ridge * np.eye(d)
        rhs = X.T @ Y
        coef = np.linalg.solve(lhs, rhs)  # d x d mapping X @ coef ≈ Y
        return coef.T

    def audit(self, defect: np.ndarray, pred_response: np.ndarray, next_defect: np.ndarray, gamma: np.ndarray | None = None, horizon: int = 4) -> GammaAuditReport:
        D = np.asarray(defect, dtype=float)
        R = np.asarray(pred_response, dtype=float)
        N = np.asarray(next_defect, dtype=float)
        residual = D - R
        if gamma is None:
            gamma = np.eye(D.size)
        G = np.asarray(gamma, dtype=float)
        pred = G @ residual
        coc = float(np.linalg.norm(N - pred))
        base = float(np.linalg.norm(N - residual))
        rel = coc / (float(np.linalg.norm(N)) + 1e-9)
        if base <= 1e-9:
            # Persistence is already exact in this finite chart; Gamma cannot meaningfully improve.
            imp = 0.0 if coc <= 1e-9 else -float("inf")
            base_zero = True
        else:
            imp = 1.0 - coc / base
            base_zero = False
        tail = np.zeros_like(R)
        cur = R.copy()
        for _ in range(max(0, int(horizon)) + 1):
            tail += cur
            cur = G @ cur
        denom = (np.linalg.norm(tail) * np.linalg.norm(D - N)) + 1e-9
        cos = float(np.dot(tail, D - N) / denom) if denom > 0 else None
        gain = float(np.dot(tail, D - N)) if tail.size else None
        try:
            radius = float(max(abs(np.linalg.eigvals(G)))) if G.size else 0.0
        except Exception:
            radius = None
        return GammaAuditReport(cocycle_resid_norm=coc, cocycle_resid_rel=rel, persistence_resid_norm=base, gamma_vs_persistence_improvement=imp, tail_value_cos=cos, tail_value_gain=gain, spectral_radius_proxy=radius, metadata={"persistence_baseline_zero": base_zero})
