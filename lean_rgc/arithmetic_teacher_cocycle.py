from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash

SCHEMA_VERSION = "lean-rgc-arithmetic-teacher-cocycle-v43.0"


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if not math.isfinite(v):
            return default
        return v
    except Exception:
        return default


def _mean(vals: list[float]) -> float:
    return float(np.mean(vals)) if vals else 0.0


def _std(vals: list[float]) -> float:
    return float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0


def _mean_dict(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys: set[str] = set()
    for r in rows:
        if isinstance(r, dict):
            keys.update(str(k) for k in r.keys())
    return {k: _mean([_safe_float((r or {}).get(k), 0.0) for r in rows]) for k in sorted(keys)}


def _std_dict(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys: set[str] = set()
    for r in rows:
        if isinstance(r, dict):
            keys.update(str(k) for k in r.keys())
    return {k: _std([_safe_float((r or {}).get(k), 0.0) for r in rows]) for k in sorted(keys)}


def _dict_norm(d: dict[str, float]) -> float:
    return float(np.linalg.norm(np.asarray(list(d.values()), dtype=float))) if d else 0.0


def _dict_add(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {k: float(a.get(k, 0.0) + b.get(k, 0.0)) for k in sorted(set(a) | set(b))}


def _dict_sub(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {k: float(a.get(k, 0.0) - b.get(k, 0.0)) for k in sorted(set(a) | set(b))}


def _dict_error(obj: dict[str, float], pred: dict[str, float]) -> float:
    return _dict_norm(_dict_sub(obj, pred))


def _transition_key(row: dict[str, Any]) -> str:
    iid = str(row.get("identity_id") or row.get("identity") or "unknown_identity")
    direction = str(row.get("direction") or row.get("mode") or "default")
    return f"{iid}::{direction}"


def _parse_key(x: Any) -> str:
    if isinstance(x, dict):
        return _transition_key(x)
    return str(x or "")


@dataclass
class ArithmeticTeacherTransitionGeometry:
    transition_class_id: str
    identity_id: str
    direction: str
    n: int = 0
    verified_count: int = 0
    success_count: int = 0
    verified_rate: float = 0.0
    success_rate: float = 0.0
    response_embedding: dict[str, float] = field(default_factory=dict)
    response_std: dict[str, float] = field(default_factory=dict)
    carrier_embedding: dict[str, float] = field(default_factory=dict)
    carrier_std: dict[str, float] = field(default_factory=dict)
    mvar_before_mean: float = 0.0
    mvar_after_mean: float = 0.0
    mvar_response_mean: float = 0.0
    gamma_scalar: float | None = None
    affine_bias: float | None = None
    spectral_radius_proxy: float | None = None
    uncertainty: dict[str, float] = field(default_factory=dict)
    action_ids: list[str] = field(default_factory=list)
    transition_ids: list[str] = field(default_factory=list)
    canonical_status: str = "arithmetic_teacher_transition_geometry_chart_not_canonical"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_arithmetic_teacher_transition_geometry(
    kernel_audit_rows_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    min_count: int = 1,
) -> dict[str, Any]:
    rows = read_jsonl(kernel_audit_rows_path)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = _transition_key(r)
        grouped.setdefault(key, []).append(r)

    geoms: list[dict[str, Any]] = []
    for key, rs in sorted(grouped.items()):
        if len(rs) < int(min_count):
            continue
        iid, direction = key.split("::", 1) if "::" in key else (key, "default")
        verified = [1.0 if r.get("kernel_transition_verified") else 0.0 for r in rs]
        success = [1.0 if str(r.get("audit_status") or "") == "success" or r.get("goal_closed") else 0.0 for r in rs]
        resp_dicts = [r.get("response") or {} for r in rs]
        carrier_dicts = [r.get("carrier_delta") or {} for r in rs]
        before = [_safe_float(((r.get("mvar_measure_before") or {}).get("measure")), 0.0) for r in rs]
        after = [_safe_float(((r.get("mvar_measure_after") or {}).get("measure")), 0.0) for r in rs]
        mresp = [_safe_float(r.get("mvar_response"), before[i] - after[i] if i < len(after) else 0.0) for i, r in enumerate(rs)]
        X = np.asarray(before, dtype=float)
        Y = np.asarray(after, dtype=float)
        mask = np.abs(X) > 1e-9
        if np.any(mask):
            gamma = float(np.dot(X[mask], Y[mask]) / (np.dot(X[mask], X[mask]) + 1e-12))
            bias = float(np.mean(Y[mask] - gamma * X[mask]))
            radius = float(abs(gamma))
        else:
            gamma = None
            bias = None
            radius = None
        resp_std = _std_dict(resp_dicts)
        car_std = _std_dict(carrier_dicts)
        uncertainty = {
            "response_l2_std": _dict_norm(resp_std),
            "carrier_l2_std": _dict_norm(car_std),
            "mvar_response_std": _std(mresp),
            "count_uncertainty": float(1.0 / math.sqrt(max(1, len(rs)))),
        }
        geom = ArithmeticTeacherTransitionGeometry(
            transition_class_id="arith_tgeom_" + stable_hash({"key": key}, n=16),
            identity_id=iid,
            direction=direction,
            n=len(rs),
            verified_count=int(sum(verified)),
            success_count=int(sum(success)),
            verified_rate=float(np.mean(verified)) if verified else 0.0,
            success_rate=float(np.mean(success)) if success else 0.0,
            response_embedding=_mean_dict(resp_dicts),
            response_std=resp_std,
            carrier_embedding=_mean_dict(carrier_dicts),
            carrier_std=car_std,
            mvar_before_mean=_mean(before),
            mvar_after_mean=_mean(after),
            mvar_response_mean=_mean(mresp),
            gamma_scalar=gamma,
            affine_bias=bias,
            spectral_radius_proxy=radius,
            uncertainty=uncertainty,
            action_ids=sorted({str(r.get("action_id") or "") for r in rs if r.get("action_id")}),
            transition_ids=sorted({str(r.get("transition_id") or "") for r in rs if r.get("transition_id")}),
        ).to_dict()
        geoms.append(geom)

    out = Path(out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, geoms)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "n_rows": len(rows),
        "n_transition_geometries": len(geoms),
        "min_count": int(min_count),
        "mean_verified_rate": float(np.mean([g.get("verified_rate", 0.0) for g in geoms])) if geoms else 0.0,
        "mean_gamma_radius": float(np.mean([float(g.get("spectral_radius_proxy") or 0.0) for g in geoms])) if geoms else 0.0,
        "out_jsonl": str(out),
        "canonical_status": "arithmetic_teacher_transition_geometry_summary_not_canonical",
    }
    if summary_out:
        _write_json(summary_out, summary)
    return summary


def _load_geometry_map(path: str | Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for g in read_jsonl(path):
        key = f"{g.get('identity_id')}::{g.get('direction')}"
        out[key] = g
        out[str(g.get("transition_class_id") or key)] = g
    return out


def _load_compositions(path: str | Path | None, geoms: dict[str, dict[str, Any]], *, max_auto_pairs: int = 0) -> list[dict[str, Any]]:
    if path and Path(path).exists():
        rows = read_jsonl(path)
        out: list[dict[str, Any]] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            out.append({
                "first": _parse_key(r.get("first") or r.get("a") or r.get("left") or r.get("I")),
                "second": _parse_key(r.get("second") or r.get("b") or r.get("right") or r.get("J")),
                "composed": _parse_key(r.get("composed") or r.get("ab") or r.get("result") or r.get("composition") or r.get("JI")),
                "composition_id": str(r.get("composition_id") or r.get("id") or stable_hash(r, n=16)),
                "metadata": dict(r.get("metadata") or {}),
            })
        return out
    # Conservative default: generate diagnostic pair rows without composed target.
    keys = [k for k in sorted(geoms) if "::" in k]
    pairs: list[dict[str, Any]] = []
    cap = max(0, int(max_auto_pairs))
    if cap <= 0:
        return []
    for i, a in enumerate(keys):
        for b in keys:
            pairs.append({"first": a, "second": b, "composed": "", "composition_id": "auto_" + stable_hash({"a": a, "b": b}, n=16), "metadata": {"auto_generated": True}})
            if len(pairs) >= cap:
                return pairs
    return pairs


def audit_arithmetic_teacher_cocycles(
    transition_geometry_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    compositions_path: str | Path | None = None,
    accept_threshold: float = 1.0,
    min_verified_rate: float = 0.0,
    max_tail_radius: float | None = None,
    max_auto_pairs: int = 0,
) -> dict[str, Any]:
    geoms = _load_geometry_map(transition_geometry_path)
    comps = _load_compositions(compositions_path, geoms, max_auto_pairs=max_auto_pairs)
    rows: list[dict[str, Any]] = []
    for comp in comps:
        first_key = str(comp.get("first") or "")
        second_key = str(comp.get("second") or "")
        composed_key = str(comp.get("composed") or "")
        first = geoms.get(first_key)
        second = geoms.get(second_key)
        composed = geoms.get(composed_key) if composed_key else None
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "composition_id": comp.get("composition_id") or "comp_" + stable_hash(comp, n=16),
            "first": first_key,
            "second": second_key,
            "composed": composed_key,
            "metadata": comp.get("metadata") or {},
            "canonical_status": "arithmetic_teacher_cocycle_audit_chart_not_canonical",
        }
        if not (first and second):
            row.update({"cocycle_status": "missing_factor_geometry", "cocycle_accept": False})
            rows.append(row)
            continue
        if composed is None:
            # Still emit predicted composition geometry as a teacher constraint seed.
            gamma_pred = None
            if first.get("gamma_scalar") is not None and second.get("gamma_scalar") is not None:
                gamma_pred = float(second.get("gamma_scalar")) * float(first.get("gamma_scalar"))
            bias_pred = None
            if gamma_pred is not None and first.get("affine_bias") is not None and second.get("affine_bias") is not None:
                bias_pred = float(second.get("gamma_scalar")) * float(first.get("affine_bias")) + float(second.get("affine_bias"))
            row.update({
                "cocycle_status": "missing_composed_geometry_predicted_only",
                "cocycle_accept": False,
                "predicted_gamma_scalar": gamma_pred,
                "predicted_affine_bias": bias_pred,
                "predicted_response_embedding": _dict_add(first.get("response_embedding") or {}, second.get("response_embedding") or {}),
                "predicted_carrier_embedding": _dict_add(first.get("carrier_embedding") or {}, second.get("carrier_embedding") or {}),
                "teacher_constraint_status": "composition_prediction_needs_audit",
            })
            rows.append(row)
            continue
        min_vr = min(_safe_float(first.get("verified_rate")), _safe_float(second.get("verified_rate")), _safe_float(composed.get("verified_rate")))
        # Additive charts.
        pred_resp = _dict_add(first.get("response_embedding") or {}, second.get("response_embedding") or {})
        pred_car = _dict_add(first.get("carrier_embedding") or {}, second.get("carrier_embedding") or {})
        resp_err = _dict_error(composed.get("response_embedding") or {}, pred_resp)
        car_err = _dict_error(composed.get("carrier_embedding") or {}, pred_car)
        # Multiplicative gamma / affine bias.
        gamma_err = None
        gamma_pred = None
        if first.get("gamma_scalar") is not None and second.get("gamma_scalar") is not None and composed.get("gamma_scalar") is not None:
            gamma_pred = float(second.get("gamma_scalar")) * float(first.get("gamma_scalar"))
            gamma_err = abs(float(composed.get("gamma_scalar")) - gamma_pred)
        bias_err = None
        bias_pred = None
        if first.get("affine_bias") is not None and second.get("affine_bias") is not None and composed.get("affine_bias") is not None and second.get("gamma_scalar") is not None:
            bias_pred = float(second.get("gamma_scalar")) * float(first.get("affine_bias")) + float(second.get("affine_bias"))
            bias_err = abs(float(composed.get("affine_bias")) - bias_pred)
        mvar_pred = _safe_float(first.get("mvar_response_mean")) + _safe_float(second.get("mvar_response_mean"))
        mvar_err = abs(_safe_float(composed.get("mvar_response_mean")) - mvar_pred)
        total = resp_err + car_err + (gamma_err or 0.0) + (bias_err or 0.0) + 0.25 * mvar_err
        radius = max(abs(_safe_float(composed.get("spectral_radius_proxy"))), abs(_safe_float(gamma_pred)) if gamma_pred is not None else 0.0)
        accepted = bool(total <= float(accept_threshold) and min_vr >= float(min_verified_rate) and (max_tail_radius is None or radius <= float(max_tail_radius)))
        row.update({
            "cocycle_status": "audited",
            "cocycle_accept": accepted,
            "min_verified_rate": min_vr,
            "response_additive_error": resp_err,
            "carrier_additive_error": car_err,
            "gamma_cocycle_error": gamma_err,
            "bias_cocycle_error": bias_err,
            "mvar_additive_error": mvar_err,
            "total_cocycle_error": float(total),
            "predicted_gamma_scalar": gamma_pred,
            "observed_gamma_scalar": composed.get("gamma_scalar"),
            "predicted_affine_bias": bias_pred,
            "observed_affine_bias": composed.get("affine_bias"),
            "tail_radius_proxy": radius,
            "teacher_constraint_status": "accepted_multiplicative_stabilizer_witness" if accepted else "cocycle_witness_rejected_or_open",
        })
        rows.append(row)
    out = Path(out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "n_compositions": len(rows),
        "n_accepted": sum(1 for r in rows if r.get("cocycle_accept")),
        "n_predicted_only": sum(1 for r in rows if r.get("cocycle_status") == "missing_composed_geometry_predicted_only"),
        "accept_threshold": float(accept_threshold),
        "min_verified_rate": float(min_verified_rate),
        "max_tail_radius": max_tail_radius,
        "mean_total_cocycle_error": (float(np.mean([_safe_float(r.get("total_cocycle_error"), 0.0) for r in rows if r.get("total_cocycle_error") is not None])) if any(r.get("total_cocycle_error") is not None for r in rows) else 0.0),
        "out_jsonl": str(out),
        "canonical_status": "arithmetic_teacher_cocycle_report_not_canonical",
    }
    if summary_out:
        _write_json(summary_out, summary)
    return summary


def write_arithmetic_teacher_gamma_constraints(
    cocycle_rows_path: str | Path,
    out_jsonl: str | Path,
    *,
    summary_out: str | Path | None = None,
    accepted_only: bool = False,
) -> dict[str, Any]:
    rows = read_jsonl(cocycle_rows_path)
    out_rows: list[dict[str, Any]] = []
    for r in rows:
        if accepted_only and not r.get("cocycle_accept"):
            continue
        cid = str(r.get("composition_id") or stable_hash(r, n=16))
        out_rows.append({
            "schema_version": SCHEMA_VERSION,
            "constraint_id": "arith_gamma_constraint_" + stable_hash({"composition_id": cid}, n=16),
            "composition_id": cid,
            "first": r.get("first"),
            "second": r.get("second"),
            "composed": r.get("composed"),
            "accepted": bool(r.get("cocycle_accept")),
            "predicted_gamma_scalar": r.get("predicted_gamma_scalar"),
            "observed_gamma_scalar": r.get("observed_gamma_scalar"),
            "predicted_affine_bias": r.get("predicted_affine_bias"),
            "observed_affine_bias": r.get("observed_affine_bias"),
            "gamma_cocycle_error": r.get("gamma_cocycle_error"),
            "bias_cocycle_error": r.get("bias_cocycle_error"),
            "total_cocycle_error": r.get("total_cocycle_error"),
            "tail_radius_proxy": r.get("tail_radius_proxy"),
            "teacher_constraint_status": r.get("teacher_constraint_status"),
            "canonical_status": "arithmetic_teacher_gamma_constraint_chart_not_canonical",
        })
    out = Path(out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, out_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "n_constraints": len(out_rows),
        "n_accepted_constraints": sum(1 for r in out_rows if r.get("accepted")),
        "out_jsonl": str(out),
        "canonical_status": "arithmetic_teacher_gamma_constraints_not_canonical",
    }
    if summary_out:
        _write_json(summary_out, summary)
    return summary


def arithmetic_teacher_cocycle_from_files(
    kernel_audit_rows: str | Path,
    out_dir: str | Path,
    *,
    compositions_path: str | Path | None = None,
    min_count: int = 1,
    accept_threshold: float = 1.0,
    min_verified_rate: float = 0.0,
    max_tail_radius: float | None = None,
    max_auto_pairs: int = 0,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    geom_path = out / "arithmetic_teacher_transition_geometry.jsonl"
    geom_rep = build_arithmetic_teacher_transition_geometry(kernel_audit_rows, geom_path, summary_out=out / "arithmetic_teacher_transition_geometry_report.json", min_count=min_count)
    cocycle_path = out / "arithmetic_teacher_cocycle_rows.jsonl"
    cocycle_rep = audit_arithmetic_teacher_cocycles(
        geom_path,
        cocycle_path,
        summary_out=out / "arithmetic_teacher_cocycle_report.json",
        compositions_path=compositions_path,
        accept_threshold=accept_threshold,
        min_verified_rate=min_verified_rate,
        max_tail_radius=max_tail_radius,
        max_auto_pairs=max_auto_pairs,
    )
    gamma_rep = write_arithmetic_teacher_gamma_constraints(cocycle_path, out / "arithmetic_teacher_gamma_constraints.jsonl", summary_out=out / "arithmetic_teacher_gamma_constraints_report.json")
    report = {
        "schema_version": SCHEMA_VERSION,
        "transition_geometry": geom_rep,
        "cocycle": cocycle_rep,
        "gamma_constraints": gamma_rep,
        "outputs": {
            "transition_geometry": str(geom_path),
            "cocycles": str(cocycle_path),
            "gamma_constraints": str(out / "arithmetic_teacher_gamma_constraints.jsonl"),
        },
        "canonical_status": "arithmetic_teacher_cocycle_loop_report_not_canonical",
    }
    _write_json(out / "arithmetic_teacher_cocycle_loop_report.json", report)
    return report


__all__ = [
    "build_arithmetic_teacher_transition_geometry",
    "audit_arithmetic_teacher_cocycles",
    "write_arithmetic_teacher_gamma_constraints",
    "arithmetic_teacher_cocycle_from_files",
]
