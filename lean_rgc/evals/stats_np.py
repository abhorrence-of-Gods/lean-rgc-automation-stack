"""Shared numpy-only statistics for the log-study analyses (D1, E-MZ).

No sklearn/torch: these run in the default CI tier and on bare pods.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "auc_score",
    "ece_score",
    "grouped_folds",
    "logistic_fit",
    "logistic_predict",
    "pav_isotonic_fit",
    "pav_isotonic_apply",
]


def auc_score(y: np.ndarray, s: np.ndarray) -> float:
    """Rank-based AUC with tie averaging. Returns nan if one class is absent."""
    y = np.asarray(y, dtype=bool)
    s = np.asarray(s, dtype=float)
    n1 = int(y.sum())
    n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def grouped_folds(groups: list[str], n_folds: int = 5, seed: int = 0) -> np.ndarray:
    """Fold index per row such that a group never spans folds."""
    uniq = sorted(set(groups))
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(uniq))
    fold_of_group = {g: int(perm[i] % n_folds) for i, g in enumerate(uniq)}
    return np.array([fold_of_group[g] for g in groups], dtype=int)


def pav_isotonic_fit(scores: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pool-adjacent-violators: returns (thresholds, values) step function."""
    order = np.argsort(scores, kind="mergesort")
    s = np.asarray(scores, dtype=float)[order]
    t = np.asarray(y, dtype=float)[order]
    # Blocks: (value_sum, weight, right_edge_score)
    vals: list[float] = []
    wts: list[float] = []
    edges: list[float] = []
    for i in range(len(s)):
        vals.append(t[i])
        wts.append(1.0)
        edges.append(s[i])
        while len(vals) > 1 and vals[-2] / wts[-2] >= vals[-1] / wts[-1]:
            v, w, e = vals.pop(), wts.pop(), edges.pop()
            vals[-1] += v
            wts[-1] += w
            edges[-1] = e
    values = np.array([v / w for v, w in zip(vals, wts)], dtype=float)
    thresholds = np.array(edges, dtype=float)
    return thresholds, values


def pav_isotonic_apply(thresholds: np.ndarray, values: np.ndarray, scores: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(thresholds, np.asarray(scores, dtype=float), side="left")
    idx = np.clip(idx, 0, len(values) - 1)
    return values[idx]


def ece_score(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error with equal-count bins."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    order = np.argsort(p, kind="mergesort")
    total = 0.0
    n = len(p)
    if n == 0:
        return float("nan")
    for chunk in np.array_split(order, n_bins):
        if len(chunk) == 0:
            continue
        total += abs(p[chunk].mean() - y[chunk].mean()) * (len(chunk) / n)
    return float(total)


def logistic_fit(X: np.ndarray, y: np.ndarray, *, l2: float = 1.0, iters: int = 50) -> np.ndarray:
    """Ridge-regularized logistic regression via IRLS. X excludes the
    intercept; a column of ones is appended (intercept unpenalized)."""
    Xb = np.hstack([X, np.ones((X.shape[0], 1))])
    y = np.asarray(y, dtype=float)
    w = np.zeros(Xb.shape[1])
    reg = l2 * np.eye(Xb.shape[1])
    reg[-1, -1] = 0.0
    for _ in range(iters):
        z = Xb @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        W = np.clip(p * (1 - p), 1e-6, None)
        H = (Xb * W[:, None]).T @ Xb + reg
        g = Xb.T @ (y - p) - reg @ w
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        w = w + step
        if float(np.max(np.abs(step))) < 1e-8:
            break
    return w


def logistic_predict(w: np.ndarray, X: np.ndarray) -> np.ndarray:
    Xb = np.hstack([X, np.ones((X.shape[0], 1))])
    return 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -30, 30)))
