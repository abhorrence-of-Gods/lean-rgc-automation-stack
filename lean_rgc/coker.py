from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any
import numpy as np

from .schemas import TacticAction
from .carrier import LeanCarrierAlgebra


@dataclass
class ConeProjectionReport:
    defect_norm: float
    projection_norm: float
    residual_norm: float
    relative_residual: float
    active_count: int
    weights: list[float]
    residual: list[float]
    projection: list[float]
    normal: list[float]
    support_value: float
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _project_simplex_l1_nonneg(x: np.ndarray, max_mass: float | None = None) -> np.ndarray:
    y = np.maximum(np.asarray(x, dtype=float), 0.0)
    if max_mass is None or y.sum() <= max_mass:
        return y
    if max_mass <= 0:
        return np.zeros_like(y)
    u = np.sort(y)[::-1]
    cssv = np.cumsum(u)
    rho_candidates = u - (cssv - max_mass) / (np.arange(len(u)) + 1) > 0
    if not np.any(rho_candidates):
        theta = cssv[-1] / len(u)
    else:
        rho = np.nonzero(rho_candidates)[0][-1]
        theta = (cssv[rho] - max_mass) / (rho + 1)
    return np.maximum(y - theta, 0.0)


def project_onto_response_cone(defect: np.ndarray, responses: np.ndarray, *, ridge: float = 1e-4, max_mass: float | None = 1.0, max_iter: int = 500, tol: float = 1e-8) -> ConeProjectionReport:
    D = np.asarray(defect, dtype=float).reshape(-1)
    R = np.asarray(responses, dtype=float)
    if R.ndim != 2:
        raise ValueError("responses must be shape [n, d]")
    if R.shape[1] != D.size:
        raise ValueError(f"responses dim {R.shape[1]} != defect dim {D.size}")
    n = R.shape[0]
    if n == 0:
        proj = np.zeros_like(D)
        resid = D.copy()
        return ConeProjectionReport(float(np.linalg.norm(D)), 0.0, float(np.linalg.norm(resid)), float(np.linalg.norm(resid)/(np.linalg.norm(D)+1e-9)), 0, [], resid.tolist(), proj.tolist(), resid.tolist(), 0.0)
    G = R @ R.T + ridge * np.eye(n)
    b = R @ D
    try:
        L = 2.0 * float(np.linalg.norm(G, ord=2)) + 1e-9
    except Exception:
        L = 2.0 * float(np.linalg.norm(G)) + 1e-9
    j = np.zeros(n, dtype=float)
    for _ in range(max_iter):
        grad = 2.0 * (G @ j - b)
        new_j = _project_simplex_l1_nonneg(j - grad / L, max_mass=max_mass)
        if np.linalg.norm(new_j - j) <= tol * (1.0 + np.linalg.norm(j)):
            j = new_j
            break
        j = new_j
    proj = R.T @ j
    resid = D - proj
    support = float(np.max(R @ resid)) if n else 0.0
    return ConeProjectionReport(float(np.linalg.norm(D)), float(np.linalg.norm(proj)), float(np.linalg.norm(resid)), float(np.linalg.norm(resid)/(np.linalg.norm(D)+1e-9)), int(np.count_nonzero(j > 1e-8)), j.tolist(), resid.tolist(), proj.tolist(), resid.tolist(), support, {"ridge": ridge, "max_mass": max_mass, "max_iter": max_iter})


def coker_margin(normal: np.ndarray, response: np.ndarray, responses: np.ndarray) -> float:
    phi = np.asarray(normal, dtype=float).reshape(-1)
    r = np.asarray(response, dtype=float).reshape(-1)
    R = np.asarray(responses, dtype=float)
    val = float(np.dot(phi, r))
    support = float(np.max(R @ phi)) if R.size else 0.0
    return val - support


class NonnegativeConeProjector:
    def __init__(self, ridge: float = 1e-4, max_mass: float | None = 1.0, max_iter: int = 500):
        self.ridge = float(ridge)
        self.max_mass = max_mass
        self.max_iter = int(max_iter)

    def project(self, defect: np.ndarray, responses: np.ndarray) -> ConeProjectionReport:
        return project_onto_response_cone(defect, responses, ridge=self.ridge, max_mass=self.max_mass, max_iter=self.max_iter)


@dataclass
class CarrierCokerReport:
    atoms: list[str]
    projection: dict[str, Any]
    residual_atoms: list[str]
    action_ids: list[str]
    action_risks: dict[str, float] = field(default_factory=dict)
    response_matrix: list[list[float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CarrierCokerAnalyzer:
    """Finite carrier-coker proxy over action carrier response charts."""

    def __init__(self, projector: NonnegativeConeProjector | None = None):
        self.projector = projector or NonnegativeConeProjector()
        self.carrier = LeanCarrierAlgebra()

    def analyze(self, carrier_defect: dict[str, float] | np.ndarray, actions: list[TacticAction] | np.ndarray, carrier_deltas: dict[str, dict[str, float]] | None = None) -> CarrierCokerReport | ConeProjectionReport:
        # Numeric fallback: analyze(defect_array, response_matrix)
        if not isinstance(carrier_defect, dict):
            return self.projector.project(np.asarray(carrier_defect, dtype=float), np.asarray(actions, dtype=float))  # type: ignore[arg-type]
        atoms = sorted(carrier_defect)
        D = np.asarray([float(carrier_defect[k]) for k in atoms], dtype=float)
        R_rows: list[list[float]] = []
        risks: dict[str, float] = {}
        action_ids: list[str] = []
        for a in actions:  # type: ignore[assignment]
            action_ids.append(a.action_id)
            if carrier_deltas and a.action_id in carrier_deltas:
                row = [max(0.0, float(carrier_deltas[a.action_id].get(k, 0.0))) for k in atoms]
            else:
                tags = set(a.carrier_tags + [a.tactic_class])
                row = []
                for k in atoms:
                    pays = (
                        (k == "missing_induction_scheme" and "induction" in tags) or
                        (k == "missing_simp_lemma" and "simp" in tags) or
                        (k == "missing_rewrite_orientation" and ("rewrite" in tags or "simp" in tags)) or
                        (k == "missing_premise_family" and ("premise" in tags or a.tactic_class in {"apply", "exact"})) or
                        (k == "missing_typeclass_instance" and ("typeclass" in tags or "simp" in tags)) or
                        (k == "missing_domain_tactic" and bool(tags & {"arithmetic", "nat", "ring", "linear_arithmetic", "normalization"}))
                    )
                    row.append(float(carrier_defect[k]) if pays else 0.0)
            R_rows.append(row)
            # Build a defect vector-like object for risk proxy.
            from .schemas import DefectVector
            risks[a.action_id] = self.carrier.carrier_violation_proxy(DefectVector(carrier={k: float(carrier_defect[k]) for k in atoms}), a)
        proj = self.projector.project(D, np.asarray(R_rows, dtype=float))
        residual = np.asarray(proj.residual, dtype=float)
        residual_atoms = [atoms[i] for i, v in enumerate(residual) if v > 1e-6]
        return CarrierCokerReport(atoms=atoms, projection=proj.to_dict(), residual_atoms=residual_atoms, action_ids=action_ids, action_risks=risks, response_matrix=R_rows)
