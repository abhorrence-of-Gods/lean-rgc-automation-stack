from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash

SCHEMA_VERSION = "lean-rgc-gamma-transition-learner-v44.0"


def _as_float_list(x: Any) -> list[float]:
    if x is None:
        return []
    try:
        return [float(v) for v in list(x)]
    except Exception:
        return []


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _norm(x: np.ndarray | list[float]) -> float:
    a = np.asarray(x, dtype=float)
    return float(np.linalg.norm(a)) if a.size else 0.0


def _spectral_radius(g: np.ndarray) -> float:
    if g.size == 0:
        return 0.0
    try:
        return float(max(abs(np.linalg.eigvals(g))))
    except Exception:
        return float(np.linalg.norm(g, ord=2))


def _fit_affine(X: np.ndarray, Y: np.ndarray, *, ridge: float = 1e-3) -> tuple[np.ndarray, np.ndarray]:
    """Fit Y ≈ X @ A + b, return Gamma=A.T and b.

    External convention uses column vectors: y ≈ Gamma @ x + b.
    """
    if X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0] or X.shape[1] != Y.shape[1]:
        raise ValueError("X and Y must have shape [n,d] with same dimensions")
    n, d = X.shape
    if n == 0:
        return np.eye(d), np.zeros(d)
    Xaug = np.concatenate([X, np.ones((n, 1), dtype=float)], axis=1)
    reg = float(ridge) * np.eye(d + 1)
    # Do not regularize the intercept as much.
    reg[-1, -1] = float(ridge) * 1e-3
    lhs = Xaug.T @ Xaug + reg
    rhs = Xaug.T @ Y
    coef = np.linalg.solve(lhs, rhs)  # [d+1,d]
    A = coef[:d, :]                  # y_row ≈ x_row @ A
    b = coef[d, :]
    return A.T, b


def _predict(G: np.ndarray, b: np.ndarray, X: np.ndarray) -> np.ndarray:
    return X @ G.T + b


def _model_errors(G: np.ndarray, b: np.ndarray, X: np.ndarray, Y: np.ndarray) -> dict[str, float]:
    if X.size == 0 or Y.size == 0:
        return {"rmse": 0.0, "relative_rmse": 0.0, "persistence_rmse": 0.0, "improvement_vs_persistence": 0.0}
    pred = _predict(G, b, X)
    resid = Y - pred
    rmse = float(np.sqrt(np.mean(np.sum(resid * resid, axis=1))))
    rel = float(rmse / (np.sqrt(np.mean(np.sum(Y * Y, axis=1))) + 1e-9))
    pers = Y - X
    pers_rmse = float(np.sqrt(np.mean(np.sum(pers * pers, axis=1))))
    imp = float(1.0 - rmse / (pers_rmse + 1e-9)) if pers_rmse > 1e-12 else (0.0 if rmse < 1e-12 else -1.0)
    return {"rmse": rmse, "relative_rmse": rel, "persistence_rmse": pers_rmse, "improvement_vs_persistence": imp}


def _rows_to_arrays(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    Xs: list[list[float]] = []
    Ys: list[list[float]] = []
    kept: list[dict[str, Any]] = []
    dim = 0
    for r in rows:
        d = _as_float_list(r.get("defect"))
        resp = _as_float_list(r.get("pred_response"))
        nxt = _as_float_list(r.get("next_defect"))
        if d and resp and nxt and len(d) == len(resp) == len(nxt):
            dim = max(dim, len(d))
            Xs.append([d[i] - resp[i] for i in range(len(d))])
            Ys.append(nxt)
            kept.append(r)
    if not Xs:
        return np.zeros((0, 0)), np.zeros((0, 0)), []
    X = np.zeros((len(Xs), dim), dtype=float)
    Y = np.zeros((len(Ys), dim), dtype=float)
    for i, (x, y) in enumerate(zip(Xs, Ys)):
        X[i, : len(x)] = x
        Y[i, : len(y)] = y
    return X, Y, kept


def _split_indices(n: int, frac: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    idx = np.arange(n)
    if n == 0:
        return idx, idx
    rng = np.random.default_rng(int(seed))
    rng.shuffle(idx)
    h = int(round(float(frac) * n))
    h = max(0, min(n, h))
    hold = idx[:h]
    train = idx[h:]
    if train.size == 0:
        train = idx
        hold = np.array([], dtype=int)
    return train, hold


def _action_key_from_teacher_key(k: Any) -> str:
    """Normalize teacher keys such as 'dist::expand' to likely action ids.

    The learner keeps this intentionally conservative. It uses exact action ids
    first and only falls back to the prefix before :: for teacher identity keys.
    """
    s = str(k or "")
    return s.split("::", 1)[0] if "::" in s else s


def _load_teacher_constraints(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return read_jsonl(p)


def _teacher_penalties_by_action(constraints: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for c in constraints:
        actions = [_action_key_from_teacher_key(c.get(k)) for k in ("first", "second", "composed")]
        err = _safe_float(c.get("total_cocycle_error"), _safe_float(c.get("gamma_cocycle_error"), 0.0))
        accepted = bool(c.get("accepted") or c.get("cocycle_accept"))
        for a in actions:
            if not a:
                continue
            rec = by.setdefault(a, {"n_constraints": 0, "n_accepted": 0, "errors": [], "constraints": []})
            rec["n_constraints"] += 1
            rec["n_accepted"] += 1 if accepted else 0
            rec["errors"].append(float(err))
            rec["constraints"].append(c.get("constraint_id") or c.get("composition_id"))
    for a, rec in by.items():
        errs = rec.get("errors") or []
        rec["mean_error"] = float(np.mean(errs)) if errs else 0.0
        rec["accepted_rate"] = float(rec.get("n_accepted", 0) / max(1, rec.get("n_constraints", 0)))
    return by


def _apply_scalar_teacher_regularization(
    action_models: dict[str, dict[str, Any]],
    constraints: list[dict[str, Any]],
    *,
    weight: float,
) -> None:
    """Small finite-chart teacher regularizer for gamma_scalar.

    For accepted constraints with first/second/composed action ids available,
    move the composed gamma scalar toward gamma_second * gamma_first.
    This is intentionally a conservative witness-level regularizer, not a proof.
    """
    w = max(0.0, float(weight))
    if w <= 0:
        return
    for c in constraints:
        if not bool(c.get("accepted") or c.get("cocycle_accept")):
            continue
        first = _action_key_from_teacher_key(c.get("first"))
        second = _action_key_from_teacher_key(c.get("second"))
        comp = _action_key_from_teacher_key(c.get("composed"))
        if not (first and second and comp):
            continue
        if first not in action_models or second not in action_models or comp not in action_models:
            continue
        g1 = action_models[first].get("gamma_scalar")
        g2 = action_models[second].get("gamma_scalar")
        gc = action_models[comp].get("gamma_scalar")
        if g1 is None or g2 is None or gc is None:
            continue
        pred = float(g2) * float(g1)
        old = float(gc)
        new = (old + w * pred) / (1.0 + w)
        action_models[comp]["gamma_scalar_teacher_regularized"] = new
        action_models[comp]["gamma_scalar_before_teacher"] = old
        action_models[comp]["teacher_predicted_gamma_scalar"] = pred
        # If the full matrix is not reliable, at least adjust scalar/radius proxy.
        action_models[comp]["gamma_scalar"] = new
        action_models[comp]["spectral_radius_proxy"] = max(abs(new), _safe_float(action_models[comp].get("spectral_radius_proxy"), 0.0))
        action_models[comp].setdefault("teacher_regularization", []).append({
            "constraint_id": c.get("constraint_id") or c.get("composition_id"),
            "first": first,
            "second": second,
            "predicted_gamma_scalar": pred,
            "old_gamma_scalar": old,
            "new_gamma_scalar": new,
            "weight": w,
        })


def _diag_from_matrix(G: np.ndarray) -> list[float]:
    if G.size == 0:
        return []
    return [float(x) for x in np.diag(G)]


def _scalar_from_matrix(G: np.ndarray) -> float | None:
    if G.size == 0:
        return None
    return float(np.trace(G) / max(1, G.shape[0]))


def _matrix_to_list(G: np.ndarray, include: bool) -> list[list[float]] | None:
    if not include:
        return None
    return [[float(x) for x in row] for row in G.tolist()]


def learn_gamma_transition_model(
    transitions_path: str | Path,
    out_dir: str | Path,
    *,
    actions_path: str | Path | None = None,
    teacher_constraints_path: str | Path | None = None,
    ridge: float = 1e-3,
    shrink: float = 4.0,
    min_count: int = 2,
    holdout_fraction: float = 0.25,
    seed: int = 0,
    teacher_weight: float = 0.25,
    include_matrices: bool = False,
) -> dict[str, Any]:
    """Learn finite-chart action-dependent Gamma transition models.

    Fits global and per-action affine maps:
        next_defect ≈ Gamma(a) @ (defect - response) + bias(a)

    Outputs are explicitly chart/witness artifacts, not canonical propagation
    operators. Arithmetic teacher cocycle constraints can regularize scalar
    Gamma witnesses and are reported in the model metadata.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    all_rows = read_jsonl(transitions_path)
    X, Y, kept = _rows_to_arrays(all_rows)
    d = int(X.shape[1]) if X.ndim == 2 else 0
    if X.shape[0] == 0 or d == 0:
        empty = {
            "schema_version": SCHEMA_VERSION,
            "status": "empty_no_valid_transitions",
            "n_transitions": len(all_rows),
            "out_dir": str(out),
            "canonical_status": "gamma_transition_model_chart_not_canonical",
        }
        (out / "gamma_transition_report.json").write_text(json.dumps(empty, indent=2, ensure_ascii=False), encoding="utf-8")
        write_jsonl(out / "gamma_transition_actions.jsonl", [])
        write_jsonl(out / "gamma_transition_audit_rows.jsonl", [])
        write_jsonl(out / "gamma_transition_action_geometry_patches.jsonl", [])
        (out / "gamma_transition_model.json").write_text(json.dumps(empty, indent=2, ensure_ascii=False), encoding="utf-8")
        return empty

    train_idx, hold_idx = _split_indices(X.shape[0], holdout_fraction, seed)
    G_global, b_global = _fit_affine(X[train_idx], Y[train_idx], ridge=ridge)
    global_train = _model_errors(G_global, b_global, X[train_idx], Y[train_idx])
    global_hold = _model_errors(G_global, b_global, X[hold_idx], Y[hold_idx]) if hold_idx.size else {}

    by_action_rows: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for i, row in enumerate(kept):
        aid = str(row.get("action_id") or "")
        if aid:
            by_action_rows.setdefault(aid, []).append((i, row))

    # Optional action metadata.
    action_meta: dict[str, dict[str, Any]] = {}
    if actions_path and Path(actions_path).exists():
        for a in read_jsonl(actions_path):
            aid = str(a.get("action_id") or a.get("id") or a.get("tactic") or stable_hash(a))
            action_meta[aid] = a

    constraints = _load_teacher_constraints(teacher_constraints_path)
    teacher_by_action = _teacher_penalties_by_action(constraints)

    action_models: dict[str, dict[str, Any]] = {}
    audit_rows: list[dict[str, Any]] = []

    for aid, indexed_rows in sorted(by_action_rows.items()):
        idx = np.asarray([i for i, _ in indexed_rows], dtype=int)
        n = int(idx.size)
        if n >= int(min_count):
            G_local, b_local = _fit_affine(X[idx], Y[idx], ridge=ridge)
            alpha = float(n / (n + max(0.0, float(shrink))))
            G = alpha * G_local + (1.0 - alpha) * G_global
            b = alpha * b_local + (1.0 - alpha) * b_global
            fit_status = "local_shrunk_to_global"
        else:
            G = G_global.copy()
            b = b_global.copy()
            alpha = 0.0
            fit_status = "global_fallback_insufficient_count"
        errs = _model_errors(G, b, X[idx], Y[idx])
        pred = _predict(G, b, X[idx])
        # Persistence baseline for action rows.
        per_resid = Y[idx] - pred
        for local_i, (orig_i, row) in enumerate(indexed_rows):
            pers_resid = np.asarray(Y[orig_i] - X[orig_i], dtype=float)
            gamma_resid = np.asarray(per_resid[local_i], dtype=float)
            gamma_norm = _norm(gamma_resid)
            pers_norm = _norm(pers_resid)
            audit_rows.append({
                "schema_version": SCHEMA_VERSION,
                "state_id": row.get("state_id"),
                "action_id": aid,
                "audit_status": row.get("audit_status"),
                "gamma_residual_norm": gamma_norm,
                "persistence_residual_norm": pers_norm,
                "gamma_improvement_vs_persistence": float(1.0 - gamma_norm / (pers_norm + 1e-9)) if pers_norm > 1e-12 else (0.0 if gamma_norm < 1e-12 else -1.0),
                "predicted_next_defect": [float(v) for v in pred[local_i].tolist()],
                "observed_next_defect": [float(v) for v in Y[orig_i].tolist()],
                "residual_input": [float(v) for v in X[orig_i].tolist()],
                "canonical_status": "gamma_transition_audit_row_chart_not_canonical",
            })
        meta = dict(action_meta.get(aid, {}).get("metadata") or {})
        model = {
            "schema_version": SCHEMA_VERSION,
            "action_id": aid,
            "tactic": str(action_meta.get(aid, {}).get("tactic") or indexed_rows[0][1].get("tactic") or aid),
            "tactic_class": str(action_meta.get(aid, {}).get("tactic_class") or action_meta.get(aid, {}).get("class") or "unknown"),
            "n_transitions": n,
            "fit_status": fit_status,
            "shrink_alpha": alpha,
            "response_dim": d,
            "gamma_scalar": _scalar_from_matrix(G),
            "gamma_diag": _diag_from_matrix(G),
            "gamma_matrix": _matrix_to_list(G, include_matrices),
            "affine_bias": [float(v) for v in b.tolist()],
            "spectral_radius_proxy": _spectral_radius(G),
            "fit_errors": errs,
            "teacher_constraints": teacher_by_action.get(aid, {"n_constraints": 0, "n_accepted": 0, "mean_error": 0.0, "accepted_rate": 0.0}),
            "uncertainty": {
                "count_uncertainty": float(1.0 / math.sqrt(max(1, n))),
                "fit_relative_rmse": float(errs.get("relative_rmse", 0.0)),
                "teacher_mean_error": float((teacher_by_action.get(aid) or {}).get("mean_error", 0.0)),
            },
            "metadata": {
                **meta,
                "source": "gamma_transition_learner_v44",
                "theory_status": "finite action-dependent affine propagation chart; not canonical Gamma",
            },
            "canonical_status": "gamma_transition_action_model_chart_not_canonical",
        }
        action_models[aid] = model

    _apply_scalar_teacher_regularization(action_models, constraints, weight=teacher_weight)

    action_rows = list(action_models.values())
    patches: list[dict[str, Any]] = []
    for row in action_rows:
        patches.append({
            "schema_version": SCHEMA_VERSION,
            "action_id": row.get("action_id"),
            "patch_kind": "action_geometry_gamma_transition_patch",
            "gamma_scalar": row.get("gamma_scalar"),
            "gamma_diag": row.get("gamma_diag"),
            "affine_bias": row.get("affine_bias"),
            "spectral_radius_proxy": row.get("spectral_radius_proxy"),
            "fit_errors": row.get("fit_errors"),
            "teacher_constraints": row.get("teacher_constraints"),
            "source": "gamma_transition_learner_v44",
            "canonical_status": "gamma_transition_patch_chart_not_canonical",
        })

    model = {
        "schema_version": SCHEMA_VERSION,
        "n_input_rows": len(all_rows),
        "n_valid_transitions": int(X.shape[0]),
        "response_dim": d,
        "ridge": float(ridge),
        "shrink": float(shrink),
        "min_count": int(min_count),
        "holdout_fraction": float(holdout_fraction),
        "teacher_weight": float(teacher_weight),
        "global_gamma_scalar": _scalar_from_matrix(G_global),
        "global_gamma_diag": _diag_from_matrix(G_global),
        "global_gamma_matrix": _matrix_to_list(G_global, include_matrices),
        "global_affine_bias": [float(v) for v in b_global.tolist()],
        "global_spectral_radius_proxy": _spectral_radius(G_global),
        "global_train_errors": global_train,
        "global_holdout_errors": global_hold,
        "n_action_models": len(action_rows),
        "teacher_constraints": {
            "path": str(teacher_constraints_path) if teacher_constraints_path else None,
            "n_constraints": len(constraints),
            "n_accepted": sum(1 for c in constraints if c.get("accepted") or c.get("cocycle_accept")),
        },
        "canonical_status": "gamma_transition_model_chart_not_canonical",
    }

    write_jsonl(out / "gamma_transition_actions.jsonl", action_rows)
    write_jsonl(out / "gamma_transition_audit_rows.jsonl", audit_rows)
    write_jsonl(out / "gamma_transition_action_geometry_patches.jsonl", patches)
    (out / "gamma_transition_model.json").write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    report = {
        **model,
        "outputs": {
            "model": str(out / "gamma_transition_model.json"),
            "actions": str(out / "gamma_transition_actions.jsonl"),
            "audit_rows": str(out / "gamma_transition_audit_rows.jsonl"),
            "action_geometry_patches": str(out / "gamma_transition_action_geometry_patches.jsonl"),
        },
    }
    (out / "gamma_transition_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def merge_gamma_transition_patches_into_action_geometry(
    action_geometry_path: str | Path,
    patches_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(action_geometry_path)
    patches = {str(p.get("action_id")): p for p in read_jsonl(patches_path)}
    out_rows: list[dict[str, Any]] = []
    n_patched = 0
    for r in rows:
        row = dict(r)
        aid = str(row.get("action_id") or "")
        p = patches.get(aid)
        if p:
            n_patched += 1
            row["gamma_scalar"] = p.get("gamma_scalar")
            row["gamma_diag"] = p.get("gamma_diag") or []
            row["affine_bias"] = p.get("affine_bias") or []
            row["spectral_radius_proxy"] = p.get("spectral_radius_proxy")
            meta = dict(row.get("metadata") or {})
            meta["gamma_transition_patch"] = p
            row["metadata"] = meta
        out_rows.append(row)
    Path(out_jsonl).parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_jsonl, out_rows)
    rep = {
        "schema_version": SCHEMA_VERSION,
        "n_action_geometry_rows": len(rows),
        "n_patches": len(patches),
        "n_patched": n_patched,
        "out_jsonl": str(out_jsonl),
        "canonical_status": "gamma_transition_patch_merge_chart_not_canonical",
    }
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep


__all__ = [
    "learn_gamma_transition_model",
    "merge_gamma_transition_patches_into_action_geometry",
]
