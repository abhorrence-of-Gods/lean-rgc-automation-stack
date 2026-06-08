from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction
from .coker import project_onto_response_cone
from .defect_registry import DefectAtom, DefectRegistry


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _state_key(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or (row.get("metadata") or {}).get("state_id") or "global")


def _action_id(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or (row.get("action") or {}).get("action_id") or row.get("tactic") or "")


def _carrier_delta_dict(row: dict[str, Any]) -> dict[str, float]:
    cd = row.get("carrier_delta") or {}
    out: dict[str, float] = {}
    if isinstance(cd, dict):
        for k, v in cd.items():
            out[str(k)] = _safe_float(v)
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        for k, v in resp.items():
            sk = str(k)
            if sk.startswith("carrier."):
                out.setdefault(sk.split(".", 1)[1], _safe_float(v))
    return out


def _carrier_defect_dict(row: dict[str, Any]) -> dict[str, float]:
    db = row.get("defect_before") or row.get("defect") or {}
    out: dict[str, float] = {}
    if isinstance(db, dict):
        carrier = db.get("carrier") or {}
        if isinstance(carrier, dict):
            for k, v in carrier.items():
                out[str(k)] = max(0.0, _safe_float(v))
        # Some rows store flat with flat_keys like carrier.foo.
        flat = db.get("flat")
        keys = db.get("flat_keys") or []
        if isinstance(flat, list) and isinstance(keys, list):
            for k, v in zip(keys, flat):
                sk = str(k)
                if sk.startswith("carrier."):
                    out.setdefault(sk.split(".", 1)[1], max(0.0, _safe_float(v)))
    # Fallback top-level carrier chart.
    carrier2 = row.get("carrier") or {}
    if isinstance(carrier2, dict):
        for k, v in carrier2.items():
            out.setdefault(str(k), max(0.0, _safe_float(v)))
    return out


def _carrier_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for r in rows:
        keys.update(_carrier_delta_dict(r))
        keys.update(_carrier_defect_dict(r))
    return sorted(keys)


def _vec(d: dict[str, float], keys: list[str]) -> np.ndarray:
    return np.asarray([_safe_float(d.get(k, 0.0)) for k in keys], dtype=float)


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
    return [
        {"key": keys[int(i)] if int(i) < len(keys) else f"carrier_{int(i)}", "loading": float(vector[int(i)]), "abs_loading": float(abs(vector[int(i)]))}
        for i in order
    ]


@dataclass
class CarrierStateCokerNormal:
    state_id: str
    carrier_keys: list[str]
    carrier_defect: list[float]
    projection: list[float]
    residual: list[float]
    normal: list[float]
    normalized_normal: list[float]
    residual_norm: float
    relative_residual: float
    support_value: float
    active_count: int
    top_loadings: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_status: str = "carrier_coker_normal_chart_not_canonical"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CarrierQuotientCoordinate:
    coordinate_id: str
    carrier_keys: list[str]
    basis_vector: list[float]
    kernel_threshold: float
    support_state_ids: list[str]
    n_states: int
    mean_residual_norm: float
    max_residual_norm: float
    top_loadings: list[dict[str, Any]] = field(default_factory=list)
    coordinate_map: dict[str, Any] = field(default_factory=dict)
    quotient_kernel: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)
    canonical_status: str = "carrier_quotient_coordinate_candidate_not_canonical_parent_nonpaid_least_repair_required"
    chart_status: str = "finite_linear_functional_on_carrier_quotient"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CarrierQuotientActionScore:
    coordinate_id: str
    action_id: str
    state_id: str
    tactic: str
    carrier_score: float
    support_value: float
    coker_surplus: float
    normalized_score: float
    accepted: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_carrier_state_coker_normals(
    responses: str | Path,
    *,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    min_residual_norm: float = 1e-9,
    infer_defect_from_violations: bool = True,
) -> tuple[list[CarrierStateCokerNormal], dict[str, Any]]:
    rows = read_jsonl(responses)
    keys = _carrier_keys(rows)
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(_state_key(r), []).append(r)
    out: list[CarrierStateCokerNormal] = []
    skipped = 0
    for sid, gr in sorted(groups.items()):
        if not keys:
            skipped += 1
            continue
        C = np.vstack([_vec(_carrier_delta_dict(r), keys) for r in gr])
        defects = np.vstack([_vec(_carrier_defect_dict(r), keys) for r in gr]) if gr else np.zeros((0, len(keys)))
        D = np.maximum(defects.mean(axis=0), 0.0) if defects.size else np.zeros(len(keys))
        if infer_defect_from_violations and float(np.linalg.norm(D)) <= 1e-12 and C.size:
            # If explicit carrier defect is absent, use observed negative carrier deltas
            # as a finite-chart proxy for carrier debt.  This is a witness only.
            D = np.maximum(-np.min(C, axis=0), 0.0)
        if C.size == 0 or D.size == 0 or float(np.linalg.norm(D)) <= 1e-12:
            skipped += 1
            continue
        rep = project_onto_response_cone(D, C, ridge=ridge, max_mass=max_mass)
        residual = np.asarray(rep.residual, dtype=float)
        if float(np.linalg.norm(residual)) < min_residual_norm:
            continue
        normal = np.asarray(rep.normal, dtype=float)
        nn = _normed(normal)
        out.append(CarrierStateCokerNormal(
            state_id=sid,
            carrier_keys=keys,
            carrier_defect=[float(x) for x in D],
            projection=rep.projection,
            residual=rep.residual,
            normal=rep.normal,
            normalized_normal=[float(x) for x in nn],
            residual_norm=float(rep.residual_norm),
            relative_residual=float(rep.relative_residual),
            support_value=float(rep.support_value),
            active_count=int(rep.active_count),
            top_loadings=_top_loadings(keys, normal, k=10),
            metadata={"n_response_rows": len(gr), "ridge": ridge, "max_mass": max_mass, "infer_defect_from_violations": infer_defect_from_violations},
        ))
    summary = {
        "schema_version": "lean-rgc-carrier-quotient-v34.0",
        "n_response_rows": len(rows),
        "n_carrier_keys": len(keys),
        "carrier_keys": keys,
        "n_state_normals": len(out),
        "n_skipped_states": skipped,
        "mean_residual_norm": float(np.mean([x.residual_norm for x in out])) if out else 0.0,
        "max_residual_norm": float(np.max([x.residual_norm for x in out])) if out else 0.0,
        "canonical_status": "carrier_state_coker_normals_are_finite_charts_not_canonical",
    }
    return out, summary


def _cluster_normals(normals: list[CarrierStateCokerNormal], *, cosine_threshold: float = 0.85) -> list[list[int]]:
    clusters: list[list[int]] = []
    centroids: list[np.ndarray] = []
    for idx, rec in enumerate(normals):
        v = np.asarray(rec.normalized_normal, dtype=float)
        if v.size == 0 or float(np.linalg.norm(v)) <= 1e-12:
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
                arr[i, :m.size] = m
            centroids[best] = _normed(arr.mean(axis=0))
        else:
            clusters.append([idx])
            centroids.append(v)
    return clusters


def generate_carrier_quotient_coordinates(
    normals: list[CarrierStateCokerNormal],
    *,
    cosine_threshold: float = 0.85,
    min_states: int = 1,
    kernel_threshold: float = 1e-6,
) -> tuple[list[CarrierQuotientCoordinate], dict[str, Any]]:
    clusters = _cluster_normals(normals, cosine_threshold=cosine_threshold)
    coords: list[CarrierQuotientCoordinate] = []
    for ci, idxs in enumerate(clusters):
        if len(idxs) < min_states:
            continue
        recs = [normals[i] for i in idxs]
        max_len = max(len(r.normalized_normal) for r in recs)
        arr = np.zeros((len(recs), max_len), dtype=float)
        weights = np.asarray([max(r.residual_norm, 1e-9) for r in recs], dtype=float)
        for i, r in enumerate(recs):
            v = np.asarray(r.normalized_normal, dtype=float)
            arr[i, : v.size] = v
        basis = _normed(np.average(arr, axis=0, weights=weights))
        # Use the first record's carrier keys; all records use the same global key list.
        keys = recs[0].carrier_keys[: basis.size]
        coord_id = "qcar_" + stable_hash({"basis": [round(float(x), 6) for x in basis], "states": [r.state_id for r in recs]}, n=14)
        coords.append(CarrierQuotientCoordinate(
            coordinate_id=coord_id,
            carrier_keys=keys,
            basis_vector=[float(x) for x in basis[: len(keys)]],
            kernel_threshold=kernel_threshold,
            support_state_ids=[r.state_id for r in recs],
            n_states=len(recs),
            mean_residual_norm=float(np.mean([r.residual_norm for r in recs])),
            max_residual_norm=float(np.max([r.residual_norm for r in recs])),
            top_loadings=_top_loadings(keys, basis, k=10),
            coordinate_map={"formula": "q_phi(c)=dot(phi,c)", "domain": "carrier_response_chart", "meaning": "carrier coker normal functional"},
            quotient_kernel={"equivalence_test": "abs(dot(phi,c1-c2))<=kernel_threshold", "modulo": "paid_noise_carrier_chart"},
            lineage={"source_state_ids": [r.state_id for r in recs], "source": "carrier_coker_normal_cluster", "cosine_threshold": cosine_threshold},
        ))
    summary = {
        "n_input_normals": len(normals),
        "n_clusters": len(clusters),
        "n_coordinates": len(coords),
        "cosine_threshold": cosine_threshold,
        "min_states": min_states,
        "canonical_status": "carrier_quotient_coordinates_are_candidates_not_canonical",
    }
    return coords, summary


def score_actions_by_carrier_quotient_coordinates(
    responses: str | Path,
    coordinates: list[CarrierQuotientCoordinate],
    *,
    top_k: int = 128,
    margin_threshold: float = 0.0,
) -> tuple[list[CarrierQuotientActionScore], dict[str, Any]]:
    rows = read_jsonl(responses)
    out: list[CarrierQuotientActionScore] = []
    for row in rows:
        aid = _action_id(row)
        if not aid:
            continue
        tactic = str(row.get("tactic") or (row.get("action") or {}).get("tactic") or aid)
        sid = _state_key(row)
        cd = _carrier_delta_dict(row)
        for coord in coordinates:
            v = _vec(cd, coord.carrier_keys)
            basis = np.asarray(coord.basis_vector, dtype=float)
            n = min(v.size, basis.size)
            if n <= 0:
                continue
            score = float(np.dot(basis[:n], v[:n]))
            support = 0.0
            surplus = score - support
            denom = float(np.linalg.norm(basis[:n]) * np.linalg.norm(v[:n]) + 1e-9)
            norm_score = float(score / denom) if denom else 0.0
            out.append(CarrierQuotientActionScore(
                coordinate_id=coord.coordinate_id,
                action_id=aid,
                state_id=sid,
                tactic=tactic,
                carrier_score=score,
                support_value=support,
                coker_surplus=surplus,
                normalized_score=norm_score,
                accepted=bool(surplus > margin_threshold),
                metadata={"source": "carrier_quotient_action_score", "canonical_status": "carrier_action_score_chart_not_canonical", "coordinate_top_loadings": coord.top_loadings[:5]},
            ))
    out.sort(key=lambda x: (x.coker_surplus, x.normalized_score), reverse=True)
    if top_k is not None and top_k > 0:
        out = out[: int(top_k)]
    summary = {"n_scores": len(out), "n_coordinates": len(coordinates), "n_actions_scored": len({r.action_id for r in out}), "n_accepted": sum(1 for r in out if r.accepted), "margin_threshold": margin_threshold}
    return out, summary


def write_carrier_quotient_candidate_actions(scores: str | Path, out: str | Path, *, accepted_only: bool = True, max_actions: int | None = None) -> dict[str, Any]:
    rows = read_jsonl(scores)
    seen: set[tuple[str, str]] = set()
    actions: list[dict[str, Any]] = []
    for r in rows:
        if accepted_only and not bool(r.get("accepted")):
            continue
        aid = str(r.get("action_id") or "")
        tactic = str(r.get("tactic") or aid)
        if not aid or not tactic:
            continue
        key = (aid, tactic)
        if key in seen:
            continue
        seen.add(key)
        action = TacticAction(action_id=aid, tactic=tactic, tactic_class="carrier_quotient", carrier_tags=["carrier_quotient"], cost_estimate=1.0, metadata={"source": "carrier_quotient_coordinate", "coordinate_id": r.get("coordinate_id"), "carrier_score": r.get("carrier_score"), "coker_surplus": r.get("coker_surplus"), "canonical_status": "carrier_quotient_action_candidate_not_canonical"}).to_dict()
        actions.append(action)
        if max_actions is not None and len(actions) >= max_actions:
            break
    write_jsonl(out, actions)
    return {"out": str(out), "n_actions": len(actions), "accepted_only": accepted_only}


def carrier_quotients_to_defect_registry(coordinates: str | Path, *, out_registry: str | Path, out_atoms: str | Path | None = None) -> dict[str, Any]:
    coords = read_jsonl(coordinates)
    atoms: list[DefectAtom] = []
    for c in coords:
        cid = str(c.get("coordinate_id") or stable_hash(c))
        atom_id = f"carrier_quotient_{cid}"
        top = c.get("top_loadings") or []
        templates = ["carrier-search", "simp", "apply ?", "rw [?]"]
        desc = "Carrier quotient coordinate mined from carrier coker normal"
        atoms.append(DefectAtom(
            atom_id=atom_id,
            group="carrier_quotient",
            detector="carrier_coker_normal",
            intervention_templates=templates,
            status="candidate",
            evidence={"coordinate_id": cid, "top_loadings": top, "canonical_status": c.get("canonical_status"), "chart_status": c.get("chart_status")},
            description=desc,
        ))
    reg = DefectRegistry(atoms=atoms, version="lean-rgc-carrier-quotient-registry-v34.0", metadata={"source": str(coordinates), "canonical_status": "carrier_quotient_registry_is_chart_not_canonical"})
    reg.save(out_registry)
    if out_atoms:
        write_jsonl(out_atoms, [a.to_dict() for a in atoms])
    return {"out_registry": str(out_registry), "out_atoms": str(out_atoms) if out_atoms else None, "n_atoms": len(atoms)}


def carrier_quotient_incidence_patches(scores: str | Path, out: str | Path, *, top_k: int = 128, margin_threshold: float = 0.0) -> dict[str, Any]:
    rows = read_jsonl(scores)
    patches: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for r in rows:
        if float(r.get("coker_surplus", 0.0) or 0.0) <= margin_threshold:
            continue
        aid = str(r.get("action_id") or "")
        cid = str(r.get("coordinate_id") or "")
        if not aid or not cid:
            continue
        atom = f"carrier_quotient_{cid}"
        key = (aid, atom)
        if key in seen:
            continue
        seen.add(key)
        mean = float(r.get("carrier_score", r.get("coker_surplus", 0.0)) or 0.0)
        patches.append({"action_id": aid, "carrier_atom": atom, "mean_delta": mean, "count": 1, "safe_direction": mean >= 0.0, "evidence": {"source": "carrier_quotient_coordinate_score", "coordinate_id": cid, "score_row": r, "canonical_status": "carrier_incidence_patch_from_quotient_chart_not_canonical"}})
        if top_k and len(patches) >= top_k:
            break
    write_jsonl(out, patches)
    return {"out": str(out), "n_patches": len(patches), "margin_threshold": margin_threshold}


def validate_carrier_quotients(
    responses: str | Path,
    coordinates: str | Path,
    *,
    out_rows: str | Path,
    out_report: str | Path | None = None,
    holdout_fraction: float = 0.35,
    min_support_score: float = 0.0,
    over_refinement_ratio: float = 0.5,
) -> dict[str, Any]:
    coords = read_jsonl(coordinates)
    rows = read_jsonl(responses)
    out: list[dict[str, Any]] = []
    for c in coords:
        cid = str(c.get("coordinate_id") or "")
        keys = [str(k) for k in (c.get("carrier_keys") or [])]
        basis = np.asarray([_safe_float(x) for x in (c.get("basis_vector") or [])], dtype=float)
        support_states = set(str(x) for x in (c.get("support_state_ids") or []))
        support_scores: list[float] = []
        nonsupport_scores: list[float] = []
        all_scores: list[float] = []
        for r in rows:
            v = _vec(_carrier_delta_dict(r), keys)
            n = min(v.size, basis.size)
            if n <= 0:
                continue
            score = float(np.dot(basis[:n], v[:n]))
            all_scores.append(score)
            if _state_key(r) in support_states:
                support_scores.append(score)
            else:
                nonsupport_scores.append(score)
        sm = float(np.mean(support_scores)) if support_scores else 0.0
        split = int(len(support_scores) * max(0.0, min(1.0, holdout_fraction)))
        hold = support_scores[split:] if support_scores else []
        hm = float(np.mean(hold)) if hold else 0.0
        nm = float(np.max(np.abs(nonsupport_scores))) if nonsupport_scores else 0.0
        support_pass = bool(sm >= min_support_score)
        over_flag = bool(nm > over_refinement_ratio * max(abs(sm), 1e-9) and nm > 0.0)
        status = "validated_carrier_shadow_candidate" if support_pass and not over_flag else ("possible_carrier_over_refinement" if over_flag else "open_low_carrier_support")
        out.append({"coordinate_id": cid, "n_support_scores": len(support_scores), "n_nonsupport_scores": len(nonsupport_scores), "support_mean_score": sm, "support_holdout_proxy_score": hm, "nonsupport_max_abs_score": nm, "support_pass": support_pass, "over_refinement_flag": over_flag, "chart_status": status, "canonical_status": "carrier_quotient_validation_chart_only_not_canonical", "top_loadings": c.get("top_loadings") or []})
    write_jsonl(out_rows, out)
    summary = {"n_coordinates": len(coords), "n_validation_rows": len(out), "by_chart_status": {}, "canonical_status": "carrier_quotient_validation_is_finite_chart_not_canonical"}
    for r in out:
        summary["by_chart_status"][r["chart_status"]] = summary["by_chart_status"].get(r["chart_status"], 0) + 1
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def carrier_quotient_from_files(
    responses: str | Path,
    out_dir: str | Path | None = None,
    *,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    cosine_threshold: float = 0.85,
    min_states: int = 1,
    top_action_scores: int = 128,
    margin_threshold: float = 0.0,
    validate: bool = False,
    infer_defect_from_violations: bool = True,
    registry: bool = True,
    normal: bool = True,
    **_: Any,
) -> dict[str, Any]:
    normals, nsum = compute_carrier_state_coker_normals(responses, ridge=ridge, max_mass=max_mass, infer_defect_from_violations=infer_defect_from_violations)
    coords, csum = generate_carrier_quotient_coordinates(normals, cosine_threshold=cosine_threshold, min_states=min_states)
    scores, ssum = score_actions_by_carrier_quotient_coordinates(responses, coords, top_k=top_action_scores, margin_threshold=margin_threshold)
    report = {"schema_version": "lean-rgc-carrier-quotient-v34.0", "state_normals_summary": nsum, "coordinate_summary": csum, "action_score_summary": ssum, "canonical_status": "carrier_quotient_outputs_are_candidates_not_canonical", "notes": ["Carrier quotient coordinates are linear functionals q_phi(c)=dot(phi,c) mined from carrier coker residual normals.", "They are not carrier atoms by themselves and not canonical observables.", "Canonical promotion requires parent non-paid + dual certificate + least repair."]}
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "carrier_quotient_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        write_jsonl(out / "carrier_state_coker_normals.jsonl", [r.to_dict() for r in normals])
        write_jsonl(out / "carrier_quotient_coordinates.jsonl", [c.to_dict() for c in coords])
        write_jsonl(out / "carrier_quotient_action_scores.jsonl", [s.to_dict() for s in scores])
        write_carrier_quotient_candidate_actions(out / "carrier_quotient_action_scores.jsonl", out / "carrier_quotient_candidates.jsonl", accepted_only=True, max_actions=top_action_scores)
        if registry:
            carrier_quotients_to_defect_registry(out / "carrier_quotient_coordinates.jsonl", out_registry=out / "carrier_quotient_defect_registry.json", out_atoms=out / "carrier_quotient_defect_atoms.jsonl")
        carrier_quotient_incidence_patches(out / "carrier_quotient_action_scores.jsonl", out / "carrier_quotient_incidence_patches.jsonl", top_k=top_action_scores, margin_threshold=margin_threshold)
        if validate:
            validate_carrier_quotients(responses, out / "carrier_quotient_coordinates.jsonl", out_rows=out / "carrier_quotient_validation_rows.jsonl", out_report=out / "carrier_quotient_validation_report.json")
    return report



def validate_carrier_quotient_coordinates(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible wrapper for carrier quotient validation.

    Supports both (responses, coordinates, ...) and (coordinates, responses, ...)
    orderings by inspecting filenames when possible.  The underlying object is a
    finite chart validation; it is not a canonicality proof.
    """
    if len(args) < 2:
        return validate_carrier_quotients(*args, **kwargs)
    a0, a1, *rest = args
    s0, s1 = str(a0), str(a1)

    def looks_like_coords(s: str) -> bool:
        ss = s.lower()
        return (
            "coordinate" in ss
            or "carrier_quotient" in ss and "response" not in ss
            or ss.endswith("coords.jsonl")
        )

    if looks_like_coords(s0) and not looks_like_coords(s1):
        coords, responses = a0, a1
    elif looks_like_coords(s1) and not looks_like_coords(s0):
        responses, coords = a0, a1
    else:
        # Default to the newer explicit ordering: responses, coordinates.
        responses, coords = a0, a1
    return validate_carrier_quotients(responses, coords, *rest, **kwargs)


# Keep a symbol name used by older notes/tests.
validate_carrier_quotient_coordinate_candidates = validate_carrier_quotient_coordinates
