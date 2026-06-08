from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable
import json
import math

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction


def _as_float_list(x: Any) -> list[float]:
    if x is None:
        return []
    try:
        return [float(v) for v in list(x)]
    except Exception:
        return []


def _mean_vec(vs: list[list[float]]) -> list[float]:
    if not vs:
        return []
    max_len = max(len(v) for v in vs)
    arr = np.zeros((len(vs), max_len), dtype=float)
    for i, v in enumerate(vs):
        if v:
            arr[i, : len(v)] = np.asarray(v, dtype=float)
    return [float(x) for x in arr.mean(axis=0)]


def _std_vec(vs: list[list[float]]) -> list[float]:
    if len(vs) <= 1:
        return [0.0 for _ in _mean_vec(vs)]
    max_len = max(len(v) for v in vs)
    arr = np.zeros((len(vs), max_len), dtype=float)
    for i, v in enumerate(vs):
        if v:
            arr[i, : len(v)] = np.asarray(v, dtype=float)
    return [float(x) for x in arr.std(axis=0, ddof=1)]


def _mean_dict(ds: list[dict[str, Any]]) -> dict[str, float]:
    keys: set[str] = set()
    for d in ds:
        keys.update(str(k) for k in (d or {}).keys())
    out: dict[str, float] = {}
    for k in sorted(keys):
        vals = [float((d or {}).get(k, 0.0)) for d in ds]
        out[k] = float(np.mean(vals)) if vals else 0.0
    return out


def _std_dict(ds: list[dict[str, Any]]) -> dict[str, float]:
    keys: set[str] = set()
    for d in ds:
        keys.update(str(k) for k in (d or {}).keys())
    out: dict[str, float] = {}
    for k in sorted(keys):
        vals = [float((d or {}).get(k, 0.0)) for d in ds]
        out[k] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    return out


def _norm(v: list[float] | np.ndarray) -> float:
    a = np.asarray(v, dtype=float)
    return float(np.linalg.norm(a)) if a.size else 0.0


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return float(default)
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def _dot_by_keys(vec: dict[str, float] | list[float] | None, emb: dict[str, float] | list[float] | None, keys: list[str] | None = None) -> float:
    if vec is None or emb is None:
        return 0.0
    if isinstance(vec, dict):
        if isinstance(emb, dict):
            return float(sum(float(vec.get(k, 0.0)) * float(emb.get(k, 0.0)) for k in set(vec) | set(emb)))
        # list emb with keys
        if keys:
            return float(sum(float(vec.get(k, 0.0)) * float(emb[i]) for i, k in enumerate(keys[: len(emb)])))
        return 0.0
    v = np.asarray(vec, dtype=float)
    if isinstance(emb, dict):
        if keys:
            e = np.asarray([float(emb.get(k, 0.0)) for k in keys], dtype=float)
        else:
            e = np.asarray(list(emb.values()), dtype=float)
    else:
        e = np.asarray(emb, dtype=float)
    n = min(v.size, e.size)
    return float(np.dot(v[:n], e[:n])) if n else 0.0


def _normal_array(normal: Any, keys: list[str], dim: int) -> np.ndarray:
    """Return a dense normal vector aligned to response keys."""
    if dim <= 0:
        return np.zeros(0, dtype=float)
    if normal is None:
        return np.zeros(dim, dtype=float)
    if isinstance(normal, dict):
        return np.asarray([float(normal.get(k, 0.0)) for k in keys[:dim]], dtype=float)
    try:
        arr = np.asarray(list(normal), dtype=float)
    except Exception:
        arr = np.zeros(0, dtype=float)
    out = np.zeros(dim, dtype=float)
    n = min(dim, arr.size)
    if n:
        out[:n] = arr[:n]
    return out


def _spectral_radius(G: np.ndarray) -> float:
    if G.size == 0:
        return 0.0
    try:
        vals = np.linalg.eigvals(G)
        return float(max(abs(v) for v in vals)) if len(vals) else 0.0
    except Exception:
        try:
            return float(np.linalg.norm(G, ord=2))
        except Exception:
            return 0.0


def _gamma_matrix_from_row(row: dict[str, Any], dim: int) -> np.ndarray:
    """Finite chart Gamma matrix from an action-geometry row.

    Preference order: explicit gamma_matrix, gamma_diag, gamma_scalar.  Missing
    values are treated as zero.  This is a chart-level propagation witness.
    """
    if dim <= 0:
        return np.zeros((0, 0), dtype=float)
    gm = row.get("gamma_matrix")
    if isinstance(gm, list) and gm:
        try:
            arr = np.asarray(gm, dtype=float)
            if arr.ndim == 2:
                out = np.zeros((dim, dim), dtype=float)
                n0 = min(dim, arr.shape[0]); n1 = min(dim, arr.shape[1])
                out[:n0, :n1] = arr[:n0, :n1]
                return out
        except Exception:
            pass
    diag = row.get("gamma_diag") or []
    try:
        d = [float(x) for x in list(diag)]
    except Exception:
        d = []
    if d:
        out = np.zeros((dim, dim), dtype=float)
        for i, v in enumerate(d[:dim]):
            out[i, i] = float(v)
        return out
    scalar = row.get("gamma_scalar")
    try:
        if scalar is not None:
            return float(scalar) * np.eye(dim, dtype=float)
    except Exception:
        pass
    return np.zeros((dim, dim), dtype=float)


def _finite_horizon_gamma_value(
    row: dict[str, Any],
    response: list[float] | np.ndarray,
    *,
    horizon: int = 4,
    discount: float = 1.0,
) -> tuple[np.ndarray, dict[str, float]]:
    """Compute Q_{Gamma,H}(r)=sum_{k=0}^H discount^k Gamma^k r.

    Returns the tail-value vector and diagnostics.  This is used only for
    finite-chart retrieval; it is not a canonical propagation operator.
    """
    r = np.asarray(response, dtype=float)
    dim = int(r.size)
    if dim == 0:
        return np.zeros(0, dtype=float), {"horizon": float(horizon), "amplification": 0.0, "tail_value_norm": 0.0}
    G = _gamma_matrix_from_row(row, dim)
    H = max(0, int(horizon))
    disc = float(discount)
    q = np.zeros(dim, dtype=float)
    v = r.copy()
    for k in range(H + 1):
        q += (disc ** k) * v
        if k < H:
            v = G @ v
    amp = float(np.linalg.norm(q) / (np.linalg.norm(r) + 1e-9))
    try:
        radius = float(max(abs(np.linalg.eigvals(G)))) if G.size else 0.0
    except Exception:
        radius = float(np.linalg.norm(G, ord=2)) if G.size else 0.0
    return q, {
        "horizon": float(H),
        "discount": float(disc),
        "tail_value_norm": float(np.linalg.norm(q)),
        "local_response_norm": float(np.linalg.norm(r)),
        "amplification": amp,
        "matrix_radius": radius,
    }


def _gamma_tail_value_vector(
    response: list[float] | np.ndarray,
    *,
    gamma_scalar: float | None = None,
    gamma_diag: list[float] | None = None,
    mode: str = "finite_horizon",
    horizon: int = 4,
    discount: float = 1.0,
) -> list[float]:
    """Finite-chart tail-native value Q_{Gamma,H}(r).

    This is deliberately a chart-level computation.  It treats gamma_diag as a
    diagonal propagation operator when dimensions match, otherwise falls back to
    gamma_scalar.  The returned vector is sum_{k=0}^H (discount*Gamma)^k r.
    """
    r = np.asarray(response, dtype=float)
    if r.size == 0:
        return []
    H = max(0, int(horizon))
    disc = float(discount)
    diag = np.asarray(gamma_diag or [], dtype=float)
    if diag.size != r.size:
        g = 0.0 if gamma_scalar is None else float(gamma_scalar)
        diag = np.full(r.size, g, dtype=float)
    if mode == "local":
        val = r.copy()
    else:
        val = np.zeros_like(r)
        power = np.ones_like(r)
        for k in range(H + 1):
            val += power * r
            power = power * (disc * diag)
    return [float(x) for x in val.tolist()]


def _gamma_tail_risk(
    *,
    spectral_radius_proxy: float | None,
    gamma_scalar: float | None = None,
    gamma_diag: list[float] | None = None,
    stability_delta: float = 0.0,
    mode: str = "spectral",
) -> float:
    """Chart-level tail risk for learned Gamma.

    The risk is positive when the observed/estimated propagation radius exceeds
    1-delta.  The spectral radius proxy is preferred; gamma_diag/scalar are
    fallbacks for old registries.
    """
    vals: list[float] = []
    if spectral_radius_proxy is not None:
        vals.append(abs(float(spectral_radius_proxy)))
    if gamma_scalar is not None:
        vals.append(abs(float(gamma_scalar)))
    for v in gamma_diag or []:
        try:
            vals.append(abs(float(v)))
        except Exception:
            pass
    radius = max(vals) if vals else 0.0
    threshold = max(0.0, 1.0 - float(stability_delta))
    return float(max(0.0, radius - threshold))


def _as_matrix(x: Any) -> np.ndarray | None:
    if x is None:
        return None
    try:
        arr = np.asarray(x, dtype=float)
    except Exception:
        return None
    if arr.ndim != 2 or arr.size == 0:
        return None
    return arr


def _gamma_operator_for_row(row: dict[str, Any], dim: int) -> np.ndarray:
    """Return a finite-chart Gamma operator for an action row.

    Preference order: explicit gamma_matrix, diagonal chart, scalar chart, identity-free zero operator.
    The zero fallback makes finite-horizon value equal to the local response for k=0 only.
    """
    if dim <= 0:
        return np.zeros((0, 0), dtype=float)
    G = _as_matrix(row.get("gamma_matrix"))
    if G is not None:
        out = np.zeros((dim, dim), dtype=float)
        m = min(dim, G.shape[0], G.shape[1])
        out[:m, :m] = G[:m, :m]
        return out
    diag = _as_float_list(row.get("gamma_diag"))
    if diag:
        out = np.zeros((dim, dim), dtype=float)
        for i, v in enumerate(diag[:dim]):
            out[i, i] = float(v)
        return out
    g = row.get("gamma_scalar")
    if g is not None:
        try:
            return float(g) * np.eye(dim, dtype=float)
        except Exception:
            pass
    return np.zeros((dim, dim), dtype=float)


def _finite_horizon_tail_value(response: list[float], row: dict[str, Any], *, horizon: int = 4, mode: str = "local", resolvent_delta: float = 0.05, clip: float = 100.0) -> tuple[list[float], dict[str, Any]]:
    """Compute a tail-native response chart from a learned Gamma(a).

    mode:
      - local: q = r.
      - finite_horizon: q = sum_{k=0}^H Gamma^k r.
      - resolvent: q = (I-Gamma)^{-1} r when stable enough; otherwise finite-horizon fallback.

    This is a chart-level witness, not a canonical value function.
    """
    r = np.asarray(response or [], dtype=float)
    if r.size == 0:
        return [], {"mode": mode, "horizon": int(horizon), "status": "empty_response"}
    mode_n = str(mode or "local").replace("_", "-").lower()
    if mode_n in {"local", "none"}:
        return [float(x) for x in r.tolist()], {"mode": "local", "horizon": 0, "status": "local_response"}
    G = _gamma_operator_for_row(row, int(r.size))
    radius = float(row.get("spectral_radius_proxy") or 0.0)
    meta: dict[str, Any] = {
        "mode": mode_n,
        "horizon": int(horizon),
        "spectral_radius_proxy": radius,
        "gamma_source": "gamma_matrix" if row.get("gamma_matrix") is not None else ("gamma_diag" if row.get("gamma_diag") else ("gamma_scalar" if row.get("gamma_scalar") is not None else "zero_fallback")),
    }
    if mode_n in {"resolvent", "inverse"}:
        # Avoid unstable inversions. Use an explicit stability buffer and fall back to finite horizon.
        try:
            eig_radius = float(max(abs(np.linalg.eigvals(G)))) if G.size else 0.0
        except Exception:
            eig_radius = radius
        meta["eig_radius"] = eig_radius
        if eig_radius < 1.0 - float(resolvent_delta):
            try:
                q = np.linalg.solve(np.eye(r.size) - G, r)
                q = np.clip(q, -float(clip), float(clip))
                meta["status"] = "resolvent_stable"
                return [float(x) for x in q.tolist()], meta
            except Exception as e:
                meta["resolvent_error"] = str(e)
        meta["status"] = "resolvent_fallback_finite_horizon"
    # finite horizon fallback/default
    H = max(0, int(horizon))
    q = np.zeros_like(r)
    cur = r.copy()
    for _ in range(H + 1):
        q += cur
        cur = G @ cur
        if np.linalg.norm(cur) > float(clip) * max(1.0, np.linalg.norm(r)):
            meta["truncated_for_clip"] = True
            break
    q = np.clip(q, -float(clip), float(clip))
    meta.setdefault("status", "finite_horizon")
    meta["tail_value_norm"] = float(np.linalg.norm(q))
    return [float(x) for x in q.tolist()], meta




def _spectral_radius(G: np.ndarray) -> float:
    if G.size == 0:
        return 0.0
    try:
        vals = np.linalg.eigvals(G)
        return float(max(abs(v) for v in vals)) if len(vals) else 0.0
    except Exception:
        try:
            return float(np.linalg.norm(G, ord=2))
        except Exception:
            return 0.0


def _gamma_matrix_from_row(row: dict[str, Any], dim: int) -> np.ndarray:
    """Return a finite-chart Gamma matrix for an action geometry row.

    Priority: explicit gamma_matrix -> gamma_diag -> gamma_scalar -> zero.
    This is a chart of propagation, not a canonical operator.
    """
    d = int(max(0, dim))
    if d == 0:
        return np.zeros((0, 0), dtype=float)
    gm = row.get("gamma_matrix")
    if isinstance(gm, list) and gm:
        try:
            G = np.asarray(gm, dtype=float)
            if G.ndim == 2:
                out = np.zeros((d, d), dtype=float)
                r = min(d, G.shape[0]); c = min(d, G.shape[1])
                out[:r, :c] = G[:r, :c]
                return out
        except Exception:
            pass
    gd = row.get("gamma_diag") or []
    if isinstance(gd, list) and gd:
        vals = np.zeros(d, dtype=float)
        for i, v in enumerate(gd[:d]):
            vals[i] = _safe_float(v)
        return np.diag(vals)
    gs = row.get("gamma_scalar")
    if gs is not None:
        return float(_safe_float(gs)) * np.eye(d, dtype=float)
    return np.zeros((d, d), dtype=float)


def _effective_gamma_response(
    row: dict[str, Any],
    response: list[float],
    *,
    mode: str = "local",
    horizon: int = 4,
    stability_margin: float = 0.05,
) -> tuple[list[float], dict[str, Any]]:
    """Compute a gamma-aware finite-horizon/stationary response value.

    local:           q = r
    finite_horizon:  q = sum_{k=0}^H G^k r
    stationary:      q = (I-G)^{-1} r when stable, otherwise finite horizon
    """
    r = np.asarray(response or [], dtype=float)
    d = int(r.size)
    meta: dict[str, Any] = {"gamma_value_mode": mode, "horizon": int(horizon)}
    if d == 0 or mode in {"", "local", "none"}:
        meta["used_gamma"] = False
        return [float(x) for x in r.tolist()], meta
    G = _gamma_matrix_from_row(row, d)
    radius = _spectral_radius(G) if G.size else 0.0
    meta["used_gamma"] = True
    meta["spectral_radius_proxy_computed"] = float(radius)
    if mode in {"stationary", "resolvent"}:
        if radius < 1.0 - float(stability_margin):
            try:
                q = np.linalg.solve(np.eye(d) - G, r)
                meta["stationary_solved"] = True
                return [float(x) for x in q.tolist()], meta
            except Exception as e:
                meta["stationary_solved"] = False
                meta["stationary_error"] = str(e)[:200]
        mode = "finite_horizon"
        meta["stationary_fallback"] = "finite_horizon"
    H = max(0, int(horizon))
    q = np.zeros(d, dtype=float)
    cur = r.copy()
    for _ in range(H + 1):
        q += cur
        cur = G @ cur
    meta["stationary_solved"] = False
    meta["finite_horizon_terms"] = H + 1
    return [float(x) for x in q.tolist()], meta


def _gamma_tail_risk(
    row: dict[str, Any],
    response_normal: Any,
    response_keys: list[str],
    dim: int,
    *,
    mode: str = "spectral",
    stability_margin: float = 0.05,
) -> tuple[float, dict[str, Any]]:
    """Finite chart risk of future propagation.

    spectral:              [rho(G)-(1-delta)]_+
    normal_amplification:  [||G^T phi||/||phi||-(1-delta)]_+
    none:                  0
    """
    mode = (mode or "spectral").lower()
    d = int(max(0, dim))
    if d == 0 or mode in {"none", "off"}:
        return 0.0, {"gamma_tail_risk_mode": mode}
    G = _gamma_matrix_from_row(row, d)
    threshold = 1.0 - float(stability_margin)
    if mode in {"normal", "normal_amplification", "coker", "coker_normal"}:
        if isinstance(response_normal, dict):
            phi = np.asarray([float(response_normal.get(k, 0.0)) for k in response_keys[:d]], dtype=float)
            if phi.size < d:
                phi = np.pad(phi, (0, d - phi.size))
        elif response_normal is None:
            phi = np.zeros(d, dtype=float)
        else:
            phi = np.asarray(response_normal, dtype=float)[:d]
            if phi.size < d:
                phi = np.pad(phi, (0, d - phi.size))
        denom = float(np.linalg.norm(phi)) + 1e-12
        amp = float(np.linalg.norm(G.T @ phi) / denom) if denom > 1e-12 else 0.0
        risk = max(0.0, amp - threshold)
        return float(risk), {"gamma_tail_risk_mode": mode, "normal_amplification": amp, "stability_threshold": threshold}
    radius = float(row.get("spectral_radius_proxy") or _spectral_radius(G))
    risk = max(0.0, radius - threshold)
    return float(risk), {"gamma_tail_risk_mode": mode, "spectral_radius": radius, "stability_threshold": threshold}


@dataclass
class ActionGeometryEmbedding:
    action_id: str
    tactic: str = ""
    tactic_class: str = "unknown"
    carrier_tags: list[str] = field(default_factory=list)
    cost_estimate: float = 1.0
    response_keys: list[str] = field(default_factory=list)
    response_embedding: list[float] = field(default_factory=list)
    response_std: list[float] = field(default_factory=list)
    carrier_embedding: dict[str, float] = field(default_factory=dict)
    carrier_std: dict[str, float] = field(default_factory=dict)
    gamma_scalar: float | None = None
    gamma_diag: list[float] = field(default_factory=list)
    spectral_radius_proxy: float | None = None
    affine_bias: list[float] = field(default_factory=list)
    uncertainty: dict[str, float] = field(default_factory=dict)
    audit_count: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    source: str = "response_audit"
    canonical_status: str = "action_embedding_chart_only_not_canonical"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_actions_map(actions_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not actions_path:
        return {}
    p = Path(actions_path)
    if not p.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(p):
        try:
            act = TacticAction.from_dict(row).to_dict()
        except Exception:
            act = dict(row)
        aid = str(act.get("action_id") or act.get("id") or act.get("tactic") or stable_hash(act))
        out[aid] = act
    return out


def _estimate_gamma_for_action(transitions: list[dict[str, Any]]) -> tuple[float | None, list[float], list[float], float | None]:
    """Estimate a tiny action-dependent affine propagation chart.

    The model is next_defect ≈ gamma_scalar * (defect - pred_response) + affine_bias.
    We also record a diagonal ratio chart as a witness. This is intentionally a finite chart, not a
    canonical propagation operator.
    """
    xs: list[list[float]] = []
    ys: list[list[float]] = []
    for row in transitions:
        d = _as_float_list(row.get("defect"))
        r = _as_float_list(row.get("pred_response"))
        n = _as_float_list(row.get("next_defect"))
        if d and r and n and len(d) == len(r) == len(n):
            xs.append([float(d[i]) - float(r[i]) for i in range(len(d))])
            ys.append(n)
    if not xs:
        return None, [], [], None
    m = max(len(x) for x in xs)
    X = np.zeros((len(xs), m), dtype=float)
    Y = np.zeros((len(ys), m), dtype=float)
    for i, (x, y) in enumerate(zip(xs, ys)):
        X[i, : len(x)] = x
        Y[i, : len(y)] = y
    denom = float(np.sum(X * X)) + 1e-12
    gamma = float(np.sum(X * Y) / denom)
    bias = np.mean(Y - gamma * X, axis=0)
    # robust-ish diagonal ratios by dimension, clipped for finite chart stability.
    diag: list[float] = []
    for j in range(m):
        xj = X[:, j]
        yj = Y[:, j]
        mask = np.abs(xj) > 1e-9
        if np.any(mask):
            ratio = np.median(yj[mask] / xj[mask])
            ratio = float(np.clip(ratio, -5.0, 5.0))
        else:
            ratio = 0.0
        diag.append(ratio)
    radius = float(max(abs(gamma), max([abs(v) for v in diag], default=0.0)))
    return gamma, [float(v) for v in diag], [float(v) for v in bias], radius


def build_action_geometry_registry(
    responses_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    actions_path: str | Path | None = None,
    transitions_path: str | Path | None = None,
    min_count: int = 1,
) -> dict[str, Any]:
    responses = read_jsonl(responses_path)
    actions = _load_actions_map(actions_path)
    transitions_by_action: dict[str, list[dict[str, Any]]] = {}
    if transitions_path and Path(transitions_path).exists():
        for tr in read_jsonl(transitions_path):
            aid = str(tr.get("action_id") or "")
            if aid:
                transitions_by_action.setdefault(aid, []).append(tr)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in responses:
        aid = str(row.get("action_id") or (row.get("action") or {}).get("action_id") or "")
        if not aid:
            continue
        grouped.setdefault(aid, []).append(row)
    embeddings: list[dict[str, Any]] = []
    for aid, rows in sorted(grouped.items()):
        if len(rows) < int(min_count):
            continue
        act = actions.get(aid) or (rows[0].get("action") or {}) or {}
        response_vecs = [_as_float_list(r.get("response_flat")) for r in rows]
        response_vecs = [v for v in response_vecs if v]
        response_keys = list(rows[0].get("response_keys") or [])
        if not response_keys:
            # fallback: sorted response dict keys
            response_keys = sorted({k for r in rows for k in (r.get("response") or {}).keys()})
        carrier_ds = [r.get("carrier_delta") or {} for r in rows]
        statuses = [str(r.get("audit_status", r.get("status", "unknown"))) for r in rows]
        success_count = sum(1 for s in statuses if s == "success")
        gamma_scalar, gamma_diag, affine_bias, radius = _estimate_gamma_for_action(transitions_by_action.get(aid, []))
        resp_mean = _mean_vec(response_vecs)
        resp_std = _std_vec(response_vecs)
        carrier_mean = _mean_dict(carrier_ds)
        carrier_std = _std_dict(carrier_ds)
        uncertainty = {
            "response_l2_std": _norm(resp_std),
            "carrier_l2_std": float(np.linalg.norm(np.asarray(list(carrier_std.values()), dtype=float))) if carrier_std else 0.0,
            "count_uncertainty": float(1.0 / math.sqrt(max(1, len(rows)))),
        }
        emb = ActionGeometryEmbedding(
            action_id=aid,
            tactic=str(act.get("tactic") or rows[0].get("tactic") or aid),
            tactic_class=str(act.get("tactic_class") or act.get("class") or "unknown"),
            carrier_tags=[str(x) for x in act.get("carrier_tags", []) or []],
            cost_estimate=float(act.get("cost_estimate", 1.0) or 1.0),
            response_keys=response_keys,
            response_embedding=resp_mean,
            response_std=resp_std,
            carrier_embedding=carrier_mean,
            carrier_std=carrier_std,
            gamma_scalar=gamma_scalar,
            gamma_diag=gamma_diag,
            spectral_radius_proxy=radius,
            affine_bias=affine_bias,
            audit_count=len(rows),
            success_count=success_count,
            success_rate=float(success_count / max(1, len(rows))),
            metadata={
                "statuses": {s: statuses.count(s) for s in sorted(set(statuses))},
                "transition_count": len(transitions_by_action.get(aid, [])),
                "theory_status": "finite action geometry chart; tactic syntax is metadata, not primitive",
            },
            uncertainty=uncertainty,
        )
        embeddings.append(emb.to_dict())
    out_path = Path(out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, embeddings)
    summary = {
        "n_responses": len(responses),
        "n_actions_total": len(grouped),
        "n_embeddings": len(embeddings),
        "min_count": int(min_count),
        "out_jsonl": str(out_path),
        "canonical_status": "action_geometry_registry_is_chart_not_canonical",
        "mean_success_rate": float(np.mean([e.get("success_rate", 0.0) for e in embeddings])) if embeddings else 0.0,
        "mean_response_norm": float(np.mean([_norm(e.get("response_embedding", [])) for e in embeddings])) if embeddings else 0.0,
        "mean_tail_radius": float(np.mean([float(e.get("spectral_radius_proxy") or 0.0) for e in embeddings])) if embeddings else 0.0,
    }
    if summary_out:
        sp = Path(summary_out)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def _load_normal(normal_json: str | Path | None, normal_inline: str | None) -> Any:
    if normal_json:
        obj = json.loads(Path(normal_json).read_text(encoding="utf-8"))
    elif normal_inline:
        obj = json.loads(normal_inline)
    else:
        return None
    # Allow wrappers.
    for k in ["normal", "response_normal", "carrier_normal", "vector"]:
        if isinstance(obj, dict) and k in obj:
            return obj[k]
    return obj


def score_action_geometry_registry(
    registry_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    response_normal: Any = None,
    carrier_normal: Any = None,
    top_k: int | None = None,
    tail_weight: float = 0.25,
    cost_weight: float = 0.05,
    uncertainty_weight: float = 0.10,
    audit_weight: float = 0.20,
    require_carrier_safe: bool = False,
    carrier_budget: float = 0.0,
    gamma_aware: bool = False,
    gamma_mode: str = "finite_horizon",
    gamma_horizon: int = 4,
    gamma_discount: float = 1.0,
    gamma_value_weight: float = 0.50,
    gamma_stability_delta: float = 0.05,
    gamma_tail_risk_mode: str = "spectral",
) -> dict[str, Any]:
    """Score action-geometry rows against response/carrier normals.

    v45 extends the v20/v23 score by optionally replacing the local response
    score with a learned-Gamma tail value chart:

        Q_{Gamma,H}(r) = sum_{k=0}^H discount^k Gamma(a)^k r

    and by penalizing learned propagation risk.  This remains a finite audit
    chart/witness rather than a canonical selector.
    """
    rows = read_jsonl(registry_path)
    scored: list[dict[str, Any]] = []
    for row in rows:
        r_keys = list(row.get("response_keys") or [])
        local_response = row.get("response_embedding") or []
        local_r_score = _dot_by_keys(response_normal, local_response, r_keys)
        gamma_tail_vector: list[float] = []
        gamma_tail_score = float(local_r_score)
        gamma_meta: dict[str, Any] = {"gamma_aware": bool(gamma_aware), "gamma_mode": "local"}
        if gamma_aware:
            # Prefer the matrix-aware helper when available.  It supports explicit
            # gamma_matrix, diag, scalar, and stationary/resolvent fallback.
            gamma_tail_vector, gamma_meta = _effective_gamma_response(
                row,
                local_response,
                mode=gamma_mode,
                horizon=gamma_horizon,
                stability_margin=gamma_stability_delta,
            )
            # If a discount != 1 is requested, use the diagonal/scalar helper as a
            # conservative discount-aware finite-horizon chart.  This path is kept
            # for backwards compatibility and for cheap scalar/diag registries.
            if str(gamma_mode).lower() in {"finite_horizon", "finite-horizon"} and abs(float(gamma_discount) - 1.0) > 1e-12:
                gamma_tail_vector = _gamma_tail_value_vector(
                    local_response,
                    gamma_scalar=row.get("gamma_scalar"),
                    gamma_diag=row.get("gamma_diag") or [],
                    mode="finite_horizon",
                    horizon=gamma_horizon,
                    discount=gamma_discount,
                )
                gamma_meta = {**gamma_meta, "discount": float(gamma_discount), "discount_helper": "diag_or_scalar"}
            gamma_tail_score = _dot_by_keys(response_normal, gamma_tail_vector, r_keys)
            wv = min(1.0, max(0.0, float(gamma_value_weight)))
            r_score = (1.0 - wv) * float(local_r_score) + wv * float(gamma_tail_score)
        else:
            r_score = float(local_r_score)
        c_score = _dot_by_keys(carrier_normal, row.get("carrier_embedding") or {})
        carrier_vals = [float(v) for v in (row.get("carrier_embedding") or {}).values()]
        carrier_violation = float(sum(max(0.0, -v) for v in carrier_vals))
        tail_radius = float(row.get("spectral_radius_proxy") or 0.0)
        if gamma_aware:
            tail_risk, risk_meta = _gamma_tail_risk(
                row,
                response_normal,
                r_keys,
                len(local_response or []),
                mode=gamma_tail_risk_mode,
                stability_margin=gamma_stability_delta,
            )
        else:
            tail_risk = max(0.0, tail_radius - 1.0)
            risk_meta = {"gamma_tail_risk_mode": "legacy_radius", "spectral_radius": tail_radius, "stability_threshold": 1.0}
        uncertainty = dict(row.get("uncertainty") or {})
        u = float(uncertainty.get("response_l2_std", 0.0)) + float(uncertainty.get("carrier_l2_std", 0.0)) + float(uncertainty.get("count_uncertainty", 0.0))
        u += float(uncertainty.get("fit_relative_rmse", 0.0)) + float(uncertainty.get("teacher_mean_error", 0.0))
        cost = float(row.get("cost_estimate", 1.0) or 1.0)
        audit_risk = 1.0 - float(row.get("success_rate", 0.0) or 0.0)
        score = float(r_score + c_score - tail_weight * tail_risk - cost_weight * cost - uncertainty_weight * u - audit_weight * audit_risk)
        accepted = bool(score > 0.0 and (not require_carrier_safe or carrier_violation <= carrier_budget))
        out = dict(row)
        out["action_geometry_score"] = score
        out["score_terms"] = {
            "response_score": float(r_score),
            "local_response_score": float(local_r_score),
            "gamma_tail_response_score": float(gamma_tail_score),
            "gamma_tail_value_gain": float(gamma_tail_score - local_r_score),
            "carrier_score": float(c_score),
            "carrier_violation": carrier_violation,
            "tail_risk": float(tail_risk),
            "tail_radius": tail_radius,
            "gamma_aware": bool(gamma_aware),
            "gamma_mode": str(gamma_mode),
            "gamma_horizon": int(gamma_horizon),
            "gamma_discount": float(gamma_discount),
            "gamma_value_weight": float(gamma_value_weight),
            "gamma_stability_delta": float(gamma_stability_delta),
            "gamma_tail_risk_mode": str(gamma_tail_risk_mode),
            "gamma_value_meta": gamma_meta,
            "gamma_risk_meta": risk_meta,
            "cost": cost,
            "uncertainty": u,
            "audit_risk": audit_risk,
        }
        if gamma_aware:
            out["gamma_tail_value_embedding"] = gamma_tail_vector
        out["action_geometry_accept"] = accepted
        out["canonical_status"] = "retrieved_action_geometry_witness_not_canonical"
        meta = dict(out.get("metadata") or {})
        meta["action_geometry"] = {
            "source": "action_geometry_retrieval_v45_gamma_aware" if gamma_aware else "action_geometry_retrieval",
            "score": float(score),
            "score_terms": out["score_terms"],
            "response_keys": r_keys,
            "gamma_aware_retrieval": bool(gamma_aware),
            "gamma_tail_value_embedding_present": bool(gamma_tail_vector),
            "canonical_status": "retrieved_action_geometry_witness_not_canonical",
        }
        out["metadata"] = meta
        scored.append(out)
    scored.sort(key=lambda x: float(x.get("action_geometry_score", 0.0)), reverse=True)
    if top_k is not None and int(top_k) > 0:
        scored = scored[: int(top_k)]
    out_path = Path(out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, scored)
    summary = {
        "n_registry": len(rows),
        "n_scored": len(scored),
        "n_accepted": sum(1 for r in scored if r.get("action_geometry_accept")),
        "top_score": float(scored[0].get("action_geometry_score", 0.0)) if scored else None,
        "out_jsonl": str(out_path),
        "gamma_aware": bool(gamma_aware),
        "gamma_mode": str(gamma_mode),
        "gamma_horizon": int(gamma_horizon),
        "gamma_discount": float(gamma_discount),
        "gamma_value_weight": float(gamma_value_weight),
        "gamma_stability_delta": float(gamma_stability_delta),
        "gamma_tail_risk_mode": str(gamma_tail_risk_mode),
        "canonical_status": "action_geometry_retrieval_summary_chart_not_canonical",
    }
    if summary_out:
        sp = Path(summary_out)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary

def _action_map_from_registry(path: str | Path) -> dict[str, dict[str, Any]]:
    return {str(r.get("action_id")): r for r in read_jsonl(path) if r.get("action_id") is not None}


def _vec_diff_norm(a: list[float], b: list[float]) -> float:
    n = max(len(a), len(b))
    if n == 0:
        return 0.0
    aa = np.zeros(n); bb = np.zeros(n)
    aa[: len(a)] = np.asarray(a, dtype=float)
    bb[: len(b)] = np.asarray(b, dtype=float)
    return float(np.linalg.norm(aa - bb))


def audit_action_cocycles(
    registry_path: str | Path,
    compositions_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    accept_threshold: float = 1.0,
) -> dict[str, Any]:
    reg = _action_map_from_registry(registry_path)
    rows: list[dict[str, Any]] = []
    for comp in read_jsonl(compositions_path):
        a_id = str(comp.get("a") or comp.get("first") or comp.get("left") or "")
        b_id = str(comp.get("b") or comp.get("second") or comp.get("right") or "")
        ab_id = str(comp.get("ab") or comp.get("composition") or comp.get("composed") or comp.get("result") or "")
        a = reg.get(a_id); b = reg.get(b_id); ab = reg.get(ab_id)
        row = dict(comp)
        row["a"] = a_id; row["b"] = b_id; row["ab"] = ab_id
        if not (a and b and ab):
            row.update({"cocycle_status": "missing_embedding", "cocycle_accept": False})
            rows.append(row); continue
        # Response additive chart: r_ab ≈ r_a + r_b as first-order witness.
        ra = np.asarray(a.get("response_embedding") or [], dtype=float)
        rb = np.asarray(b.get("response_embedding") or [], dtype=float)
        rab = np.asarray(ab.get("response_embedding") or [], dtype=float)
        n = max(ra.size, rb.size, rab.size)
        rpred = np.zeros(n); robj = np.zeros(n)
        rpred[:ra.size] += ra; rpred[:rb.size] += rb; robj[:rab.size] = rab
        response_additive_error = float(np.linalg.norm(robj - rpred))
        # Carrier additive chart.
        ca = a.get("carrier_embedding") or {}; cb = b.get("carrier_embedding") or {}; cab = ab.get("carrier_embedding") or {}
        carrier_keys = sorted(set(ca) | set(cb) | set(cab))
        carrier_additive_error = float(np.linalg.norm(np.asarray([float(cab.get(k,0.0)) - float(ca.get(k,0.0)) - float(cb.get(k,0.0)) for k in carrier_keys], dtype=float))) if carrier_keys else 0.0
        # Multiplicative gamma scalar chart: gamma_ab ≈ gamma_b * gamma_a.
        ga = a.get("gamma_scalar"); gb = b.get("gamma_scalar"); gab = ab.get("gamma_scalar")
        if ga is None or gb is None or gab is None:
            gamma_cocycle_error = None
        else:
            gamma_cocycle_error = float(abs(float(gab) - float(gb) * float(ga)))
        # Bias cocycle chart: b_ab ≈ gamma_b b_a + b_b.
        ba = np.asarray(a.get("affine_bias") or [], dtype=float)
        bb = np.asarray(b.get("affine_bias") or [], dtype=float)
        bab = np.asarray(ab.get("affine_bias") or [], dtype=float)
        if ba.size and bb.size and bab.size and gb is not None:
            m = max(ba.size, bb.size, bab.size)
            pred = np.zeros(m); obj = np.zeros(m)
            pred[:ba.size] += float(gb) * ba; pred[:bb.size] += bb; obj[:bab.size] = bab
            bias_cocycle_error = float(np.linalg.norm(obj - pred))
        else:
            bias_cocycle_error = None
        total = response_additive_error + carrier_additive_error + (gamma_cocycle_error or 0.0) + (bias_cocycle_error or 0.0)
        row.update({
            "response_additive_error": response_additive_error,
            "carrier_additive_error": carrier_additive_error,
            "gamma_cocycle_error": gamma_cocycle_error,
            "bias_cocycle_error": bias_cocycle_error,
            "total_cocycle_error": float(total),
            "cocycle_accept": bool(total <= float(accept_threshold)),
            "canonical_status": "cocycle_audit_chart_only_not_canonical",
        })
        rows.append(row)
    out_path = Path(out_jsonl); out_path.parent.mkdir(parents=True, exist_ok=True); write_jsonl(out_path, rows)
    summary = {
        "n_compositions": len(rows),
        "n_accepted": sum(1 for r in rows if r.get("cocycle_accept")),
        "accept_threshold": float(accept_threshold),
        "mean_total_cocycle_error": float(np.mean([float(r.get("total_cocycle_error", 0.0)) for r in rows if r.get("total_cocycle_error") is not None])) if rows else 0.0,
        "out_jsonl": str(out_path),
    }
    if summary_out:
        sp = Path(summary_out); sp.parent.mkdir(parents=True, exist_ok=True); sp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def teacher_constraints_from_arithmetic_actions(
    actions_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    """Generate lightweight arithmetic teacher constraint specs from action metadata.

    This is intentionally conservative. It only emits constraints when an action row explicitly
    declares metadata such as {"arith": {"expr": ..., "op": ..., "lhs": ..., "rhs": ...}} or
    {"teacher_equiv": [...]}.
    """
    acts = read_jsonl(actions_path)
    rows: list[dict[str, Any]] = []
    by_expr: dict[str, list[dict[str, Any]]] = {}
    for a in acts:
        meta = a.get("metadata") or {}
        ar = meta.get("arith") or {}
        expr = ar.get("expr") or meta.get("teacher_expr")
        if expr:
            by_expr.setdefault(str(expr), []).append(a)
        for eq in meta.get("teacher_equiv", []) or []:
            rows.append({
                "kind": "declared_equivalence",
                "lhs_action": a.get("action_id"),
                "rhs_action": eq,
                "source": "action_metadata.teacher_equiv",
                "canonical_status": "teacher_constraint_chart_only_not_canonical",
            })
    for expr, group in by_expr.items():
        if len(group) <= 1:
            continue
        ids = [str(g.get("action_id")) for g in group]
        rows.append({
            "kind": "same_arithmetic_expr",
            "expr": expr,
            "actions": ids,
            "source": "action_metadata.arith.expr",
            "canonical_status": "teacher_constraint_chart_only_not_canonical",
        })
    out_path = Path(out_jsonl); out_path.parent.mkdir(parents=True, exist_ok=True); write_jsonl(out_path, rows)
    summary = {"n_actions": len(acts), "n_constraints": len(rows), "out_jsonl": str(out_path)}
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True); Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
