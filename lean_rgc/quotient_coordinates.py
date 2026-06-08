from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash
from .coker import project_onto_response_cone, ConeProjectionReport


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _row_state_key(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or (row.get("metadata") or {}).get("state_id") or "global")


def _response_keys(row: dict[str, Any]) -> list[str]:
    if isinstance(row.get("response_keys"), list) and row["response_keys"]:
        return [str(k) for k in row["response_keys"]]
    if isinstance(row.get("response"), dict) and row["response"]:
        return sorted(str(k) for k in row["response"])
    if isinstance(row.get("response_flat"), list):
        return [f"coord_{i}" for i in range(len(row.get("response_flat", [])))]
    return []


def _response_vec(row: dict[str, Any], keys: list[str] | None = None) -> np.ndarray:
    if isinstance(row.get("response_flat"), list):
        return np.asarray([_safe_float(v) for v in row.get("response_flat", [])], dtype=float)
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        keys = keys or sorted(str(k) for k in resp)
        return np.asarray([_safe_float(resp.get(k, 0.0)) for k in keys], dtype=float)
    return np.zeros(0, dtype=float)


def _defect_vec(row: dict[str, Any], keys: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    db = row.get("defect_before") or row.get("defect") or {}
    if isinstance(db, dict):
        if isinstance(db.get("flat"), list):
            ks = [str(x) for x in (db.get("flat_keys") or keys or [f"coord_{i}" for i in range(len(db.get("flat", [])))])]
            return np.asarray([_safe_float(v) for v in db.get("flat", [])], dtype=float), ks
        vals: list[float] = []
        ks: list[str] = []
        for block in ("goal", "type", "search", "carrier", "audit"):
            sub = db.get(block)
            if isinstance(sub, dict):
                for name in sorted(sub):
                    ks.append(f"{block}.{name}")
                    vals.append(_safe_float(sub.get(name, 0.0)))
        if vals:
            return np.asarray(vals, dtype=float), ks
    vals = []
    ks = []
    for block in ("goal", "type", "search", "carrier", "audit"):
        sub = row.get(block)
        if isinstance(sub, dict):
            for name in sorted(sub):
                ks.append(f"{block}.{name}")
                vals.append(_safe_float(sub.get(name, 0.0)))
    if vals:
        return np.asarray(vals, dtype=float), ks
    return np.zeros(0, dtype=float), list(keys or [])


def _align_group(rows: list[dict[str, Any]], global_keys: list[str] | None = None) -> tuple[np.ndarray, np.ndarray, list[str], list[dict[str, Any]]]:
    if not rows:
        return np.zeros(0), np.zeros((0, 0)), [], []
    keys = list(global_keys or _response_keys(rows[0]))
    R_list: list[np.ndarray] = []
    D_list: list[np.ndarray] = []
    valid: list[dict[str, Any]] = []
    for r in rows:
        rv = _response_vec(r, keys)
        dv, dkeys = _defect_vec(r, keys)
        if not keys:
            keys = dkeys or _response_keys(r)
        n = min(rv.size, dv.size, len(keys))
        if n <= 0:
            continue
        R_list.append(rv[:n])
        D_list.append(dv[:n])
        valid.append(r)
    if not R_list:
        return np.zeros(0), np.zeros((0, 0)), keys, []
    R = np.vstack(R_list)
    D = np.maximum(np.mean(np.vstack(D_list), axis=0), 0.0)
    return D, R, keys[: R.shape[1]], valid


def _normed(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n <= 1e-12:
        return np.zeros_like(v)
    return v / n


def _top_loadings(keys: list[str], vector: np.ndarray, *, k: int = 8) -> list[dict[str, Any]]:
    if vector.size == 0:
        return []
    n = min(len(keys), int(vector.size))
    order = np.argsort(-np.abs(vector[:n]))[: max(0, k)]
    out = []
    for i in order:
        out.append({"key": keys[int(i)] if int(i) < len(keys) else f"coord_{int(i)}", "loading": float(vector[int(i)]), "abs_loading": float(abs(vector[int(i)]))})
    return out


@dataclass
class StateCokerNormal:
    state_id: str
    response_keys: list[str]
    defect: list[float]
    projection: list[float]
    residual: list[float]
    normal: list[float]
    normalized_normal: list[float]
    residual_norm: float
    relative_residual: float
    support_value: float
    active_count: int
    top_loadings: list[dict[str, Any]] = field(default_factory=list)
    canonical_status: str = "finite_coker_normal_chart_not_canonical"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuotientCoordinateCandidate:
    coordinate_id: str
    response_keys: list[str]
    basis_vector: list[float]
    kernel_threshold: float
    support_state_ids: list[str]
    n_states: int
    mean_residual_norm: float
    max_residual_norm: float
    mean_relative_residual: float
    top_loadings: list[dict[str, Any]] = field(default_factory=list)
    coordinate_map: dict[str, Any] = field(default_factory=dict)
    quotient_kernel: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)
    canonical_status: str = "quotient_coordinate_candidate_not_canonical_parent_nonpaid_least_repair_required"
    chart_status: str = "finite_linear_functional_on_response_quotient"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuotientActionScore:
    coordinate_id: str
    action_id: str
    state_id: str
    tactic: str
    response_score: float
    support_value: float
    coker_surplus: float
    normalized_score: float
    accepted: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_state_coker_normals(
    responses_path: str | Path,
    *,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    min_residual_norm: float = 1e-9,
    global_keys: list[str] | None = None,
) -> tuple[list[StateCokerNormal], dict[str, Any]]:
    rows = read_jsonl(responses_path)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(_row_state_key(row), []).append(row)
    out: list[StateCokerNormal] = []
    all_keys = global_keys
    for state_id, gr in sorted(groups.items()):
        D, R, keys, valid = _align_group(gr, all_keys)
        if R.size == 0 or D.size == 0:
            continue
        if all_keys is None:
            all_keys = keys
        rep = project_onto_response_cone(D, R, ridge=ridge, max_mass=max_mass)
        residual = np.asarray(rep.residual, dtype=float)
        if float(np.linalg.norm(residual)) < min_residual_norm:
            continue
        normal = np.asarray(rep.normal, dtype=float)
        nn = _normed(normal)
        out.append(StateCokerNormal(
            state_id=state_id,
            response_keys=keys,
            defect=[float(x) for x in D],
            projection=rep.projection,
            residual=rep.residual,
            normal=rep.normal,
            normalized_normal=[float(x) for x in nn],
            residual_norm=float(rep.residual_norm),
            relative_residual=float(rep.relative_residual),
            support_value=float(rep.support_value),
            active_count=int(rep.active_count),
            top_loadings=_top_loadings(keys, normal, k=10),
            metadata={"n_response_rows": len(valid), "ridge": ridge, "max_mass": max_mass},
        ))
    summary = {
        "n_response_rows": len(rows),
        "n_state_normals": len(out),
        "mean_residual_norm": float(np.mean([x.residual_norm for x in out])) if out else 0.0,
        "max_residual_norm": float(np.max([x.residual_norm for x in out])) if out else 0.0,
        "canonical_status": "state_coker_normals_are_finite_charts_not_canonical",
    }
    return out, summary


def _cluster_normals(normals: list[StateCokerNormal], *, cosine_threshold: float = 0.85) -> list[list[int]]:
    clusters: list[list[int]] = []
    centroids: list[np.ndarray] = []
    for idx, rec in enumerate(normals):
        v = np.asarray(rec.normalized_normal, dtype=float)
        if v.size == 0 or np.linalg.norm(v) <= 1e-12:
            continue
        best = -1
        best_score = -2.0
        for ci, c in enumerate(centroids):
            n = min(v.size, c.size)
            score = float(np.dot(v[:n], c[:n])) if n else -2.0
            if score > best_score:
                best_score = score
                best = ci
        if best >= 0 and best_score >= cosine_threshold:
            clusters[best].append(idx)
            mats = [np.asarray(normals[j].normalized_normal, dtype=float) for j in clusters[best]]
            max_len = max(m.size for m in mats)
            arr = np.zeros((len(mats), max_len), dtype=float)
            for i, m in enumerate(mats):
                arr[i, : m.size] = m
            centroids[best] = _normed(arr.mean(axis=0))
        else:
            clusters.append([idx])
            centroids.append(v)
    return clusters


def generate_quotient_coordinates(
    normals: list[StateCokerNormal],
    *,
    cosine_threshold: float = 0.85,
    min_states: int = 1,
    top_loadings: int = 10,
) -> tuple[list[QuotientCoordinateCandidate], dict[str, Any]]:
    clusters = _cluster_normals(normals, cosine_threshold=cosine_threshold)
    coords: list[QuotientCoordinateCandidate] = []
    for cluster in clusters:
        if len(cluster) < int(min_states):
            continue
        records = [normals[i] for i in cluster]
        max_len = max(len(r.normalized_normal) for r in records)
        arr = np.zeros((len(records), max_len), dtype=float)
        for i, rec in enumerate(records):
            v = np.asarray(rec.normalized_normal, dtype=float)
            arr[i, : v.size] = v
        # Weight by residual norm so stronger coker normals define the coordinate.
        weights = np.asarray([max(r.residual_norm, 1e-9) for r in records], dtype=float)
        basis = _normed((arr * weights[:, None]).sum(axis=0) / max(float(weights.sum()), 1e-9))
        keys = records[0].response_keys[: len(basis)]
        coord_payload = {
            "states": [r.state_id for r in records],
            "basis_top": [(x["key"], round(float(x["loading"]), 8)) for x in _top_loadings(keys, basis, k=6)],
            "n_states": len(records),
        }
        cid = "qcoord_" + stable_hash(coord_payload, 14)
        coords.append(QuotientCoordinateCandidate(
            coordinate_id=cid,
            response_keys=keys,
            basis_vector=[float(x) for x in basis[: len(keys)]],
            kernel_threshold=1e-8,
            support_state_ids=[r.state_id for r in records],
            n_states=len(records),
            mean_residual_norm=float(np.mean([r.residual_norm for r in records])),
            max_residual_norm=float(np.max([r.residual_norm for r in records])),
            mean_relative_residual=float(np.mean([r.relative_residual for r in records])),
            top_loadings=_top_loadings(keys, basis, k=top_loadings),
            coordinate_map={
                "formula": "q_phi(d)=dot(phi,d)",
                "basis": [float(x) for x in basis[: len(keys)]],
                "response_keys": keys,
            },
            quotient_kernel={
                "equivalence_test": "abs(dot(phi,d1-d2))<=kernel_threshold",
                "kernel_threshold": 1e-8,
                "modulo": "paid_noise_response_chart",
            },
            lineage={
                "source": "state_coker_normal_clustering",
                "cosine_threshold": cosine_threshold,
                "state_residuals": [{"state_id": r.state_id, "residual_norm": r.residual_norm, "relative_residual": r.relative_residual} for r in records],
            },
        ))
    summary = {
        "n_state_normals": len(normals),
        "n_clusters": len(clusters),
        "n_quotient_coordinates": len(coords),
        "cosine_threshold": cosine_threshold,
        "min_states": min_states,
        "canonical_status": "quotient_coordinates_are_candidates_until_parent_nonpaid_least_repair",
    }
    return coords, summary


def score_actions_by_quotient_coordinates(
    responses_path: str | Path,
    coordinates: list[QuotientCoordinateCandidate],
    *,
    top_k: int = 128,
    margin_threshold: float = 0.0,
) -> tuple[list[QuotientActionScore], dict[str, Any]]:
    rows = read_jsonl(responses_path)
    out: list[QuotientActionScore] = []
    for row in rows:
        aid = str(row.get("action_id") or (row.get("action") or {}).get("action_id") or row.get("tactic") or "")
        if not aid:
            continue
        tactic = str(row.get("tactic") or (row.get("action") or {}).get("tactic") or aid)
        state_id = _row_state_key(row)
        for coord in coordinates:
            keys = coord.response_keys
            rv = _response_vec(row, keys)
            basis = np.asarray(coord.basis_vector, dtype=float)
            n = min(rv.size, basis.size)
            if n <= 0:
                continue
            score = float(np.dot(basis[:n], rv[:n]))
            # A finite support proxy: max score from coordinate-support states is unavailable here;
            # use zero support and expose the raw coordinate score. Robust acceptance can add support later.
            support = 0.0
            surplus = score - support
            denom = float(np.linalg.norm(basis[:n]) * np.linalg.norm(rv[:n]) + 1e-9)
            norm_score = float(score / denom) if denom else 0.0
            out.append(QuotientActionScore(
                coordinate_id=coord.coordinate_id,
                action_id=aid,
                state_id=state_id,
                tactic=tactic,
                response_score=score,
                support_value=support,
                coker_surplus=surplus,
                normalized_score=norm_score,
                accepted=bool(surplus > margin_threshold),
                metadata={
                    "source": "quotient_coordinate_action_score",
                    "canonical_status": "action_score_chart_not_canonical",
                    "coordinate_top_loadings": coord.top_loadings[:5],
                },
            ))
    out.sort(key=lambda x: (x.coker_surplus, x.normalized_score), reverse=True)
    if top_k is not None and top_k > 0:
        out = out[: int(top_k)]
    summary = {
        "n_scores": len(out),
        "n_coordinates": len(coordinates),
        "n_actions_scored": len({r.action_id for r in out}),
        "n_accepted": sum(1 for r in out if r.accepted),
        "margin_threshold": margin_threshold,
    }
    return out, summary


def quotient_coordinates_from_files(
    responses: str | Path,
    *,
    out_dir: str | Path | None = None,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    cosine_threshold: float = 0.85,
    min_states: int = 1,
    score_actions: bool = True,
    top_action_scores: int = 128,
    margin_threshold: float = 0.0,
) -> dict[str, Any]:
    normals, nsum = compute_state_coker_normals(responses, ridge=ridge, max_mass=max_mass)
    coords, csum = generate_quotient_coordinates(normals, cosine_threshold=cosine_threshold, min_states=min_states)
    scores: list[QuotientActionScore] = []
    ssum: dict[str, Any] = {}
    if score_actions:
        scores, ssum = score_actions_by_quotient_coordinates(responses, coords, top_k=top_action_scores, margin_threshold=margin_threshold)
    report = {
        "schema_version": "lean-rgc-quotient-coordinate-v25.0",
        "state_normals_summary": nsum,
        "coordinate_summary": csum,
        "action_score_summary": ssum,
        "canonical_status": "finite_quotient_coordinate_candidates_not_canonical",
        "notes": [
            "Coordinates are linear functionals q_phi(d)=dot(phi,d) mined from coker residual normals.",
            "They are quotient-coordinate candidates, not defect labels and not canonical observables.",
            "Canonical promotion still requires parent non-paid + dual certificate + least repair.",
        ],
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "quotient_coordinate_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        write_jsonl(out / "state_coker_normals.jsonl", [r.to_dict() for r in normals])
        write_jsonl(out / "quotient_coordinates.jsonl", [c.to_dict() for c in coords])
        write_jsonl(out / "quotient_coordinate_action_scores.jsonl", [s.to_dict() for s in scores])
        write_jsonl(out / "quotient_coordinate_selected_actions.jsonl", [
            {
                "action_id": s.action_id,
                "tactic": s.tactic,
                "metadata": {
                    "source": "quotient_coordinate_retrieval",
                    "coordinate_id": s.coordinate_id,
                    "response_score": s.response_score,
                    "coker_surplus": s.coker_surplus,
                    "normalized_score": s.normalized_score,
                    "canonical_status": "context_witness_until_audited_and_promoted",
                },
            }
            for s in scores if s.accepted
        ])
    return report


__all__ = [
    "StateCokerNormal",
    "QuotientCoordinateCandidate",
    "QuotientActionScore",
    "compute_state_coker_normals",
    "generate_quotient_coordinates",
    "score_actions_by_quotient_coordinates",
    "quotient_coordinates_from_files",
]
