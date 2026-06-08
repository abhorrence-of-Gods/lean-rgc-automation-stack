from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


@dataclass
class QuotientComponent:
    component_id: str
    members: list[str]
    centroid: list[float]
    status: str = "open"
    bootstrap_stability: float | None = None
    metadata: dict = field(default_factory=dict)


class ResponseQuotientDiscovery:
    """Finite approximation of Act/ker R via response-vector clustering."""

    def __init__(self, tolerance: float = 0.25, metric: str = "l2"):
        self.tolerance = float(tolerance)
        self.metric = metric

    def discover(self, action_ids: list[str], response_matrix: np.ndarray, weights: np.ndarray | None = None) -> list[QuotientComponent]:
        R = np.asarray(response_matrix, dtype=float)
        # Expected shape [n_actions, dim]. If transposed, caller can transpose.
        if R.ndim != 2:
            raise ValueError("response_matrix must be 2D")
        n = R.shape[0]
        if n != len(action_ids):
            raise ValueError("len(action_ids) must equal response_matrix.shape[0]")
        W = np.ones(R.shape[1]) if weights is None else np.asarray(weights, dtype=float)
        parent = list(range(n))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri

        for i in range(n):
            for j in range(i + 1, n):
                dist = float(np.linalg.norm((R[i] - R[j]) * W))
                if dist <= self.tolerance:
                    union(i, j)
        groups: dict[int, list[int]] = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(i)
        comps: list[QuotientComponent] = []
        for k, inds in enumerate(groups.values()):
            centroid = R[inds].mean(axis=0)
            # Component is a shadow by default; faithfulness needs contextual tests.
            status = "shadow" if len(inds) > 1 else "open"
            comps.append(QuotientComponent(component_id=f"QR_{k:04d}", members=[action_ids[i] for i in inds], centroid=centroid.tolist(), status=status, metadata={"size": len(inds)}))
        return comps

    @staticmethod
    def paid_null_violation(response_matrix: np.ndarray, paid_dirs: np.ndarray) -> float:
        R = np.asarray(response_matrix, dtype=float)
        P = np.asarray(paid_dirs, dtype=float)
        if P.size == 0:
            return 0.0
        # Compute energy of responses in paid-null directions.
        if P.ndim == 1:
            P = P[None, :]
        # orthonormalize rows of P
        q, _ = np.linalg.qr(P.T)
        proj = R @ q @ q.T
        return float(np.linalg.norm(proj) / (np.linalg.norm(R) + 1e-9))
