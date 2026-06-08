from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction
from .defect_registry import DefectAtom, DefectRegistry
from .quotient_coordinates import quotient_coordinates_from_files


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _coordinate_weight(row: dict[str, Any]) -> float:
    return max(
        abs(_safe_float(row.get("mean_residual_norm"))),
        abs(_safe_float(row.get("max_residual_norm"))),
        1e-9,
    )


def merged_response_normal_from_coordinates(coords_path: str | Path, *, top_k: int | None = None) -> dict[str, Any]:
    """Build a finite response-normal chart from quotient-coordinate candidates.

    The result is a chart-level normal, not a canonical observable.  It is useful
    for feeding action-geometry retrieval from mined quotient coordinates.
    """
    coords = read_jsonl(coords_path) if Path(coords_path).exists() else []
    if top_k is not None and int(top_k) > 0:
        coords = sorted(coords, key=_coordinate_weight, reverse=True)[: int(top_k)]
    acc: dict[str, float] = {}
    total = 0.0
    sources = []
    for c in coords:
        keys = [str(k) for k in c.get("response_keys") or []]
        vec = [_safe_float(v) for v in c.get("basis_vector") or []]
        w = _coordinate_weight(c)
        total += w
        sources.append({"coordinate_id": c.get("coordinate_id"), "weight": w, "n_states": c.get("n_states")})
        for k, v in zip(keys, vec):
            acc[k] = acc.get(k, 0.0) + w * v
    if total > 0:
        acc = {k: v / total for k, v in acc.items() if abs(v / total) > 1e-12}
    return {
        "response_normal": acc,
        "metadata": {
            "source": "quotient_coordinates",
            "n_coordinates": len(coords),
            "top_k": top_k,
            "coordinate_sources": sources,
            "canonical_status": "merged_quotient_coordinate_normal_chart_not_canonical",
        },
    }


def write_quotient_coordinate_candidate_actions(
    scores_path: str | Path,
    out_actions: str | Path,
    *,
    accepted_only: bool = True,
    max_actions: int | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(scores_path) if Path(scores_path).exists() else []
    rows = sorted(rows, key=lambda r: (_safe_float(r.get("coker_surplus")), _safe_float(r.get("normalized_score"))), reverse=True)
    acts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if accepted_only and not bool(row.get("accepted")):
            continue
        aid = str(row.get("action_id") or row.get("tactic") or "qcoord_action")
        tactic = str(row.get("tactic") or aid)
        key = tactic
        if key in seen:
            continue
        seen.add(key)
        meta = {
            "source": "quotient_coordinate_retrieval",
            "coordinate_id": row.get("coordinate_id"),
            "state_id": row.get("state_id"),
            "response_score": row.get("response_score"),
            "coker_surplus": row.get("coker_surplus"),
            "normalized_score": row.get("normalized_score"),
            "canonical_status": "quotient_coordinate_action_candidate_not_canonical",
            "score_metadata": row.get("metadata") or {},
        }
        action = TacticAction(
            action_id=f"qcoord:{aid}:{stable_hash(meta, 8)}",
            tactic=tactic,
            tactic_class="quotient_coordinate",
            carrier_tags=["quotient_coordinate"],
            cost_estimate=1.0,
            metadata=meta,
        ).to_dict()
        acts.append(action)
        if max_actions is not None and len(acts) >= int(max_actions):
            break
    write_jsonl(out_actions, acts)
    return {"n_score_rows": len(rows), "n_actions": len(acts), "out_actions": str(out_actions), "accepted_only": accepted_only}


def quotient_coordinates_to_defect_registry(
    coords_path: str | Path,
    *,
    out_registry: str | Path,
    out_atoms: str | Path | None = None,
    max_atoms: int | None = None,
) -> dict[str, Any]:
    coords = read_jsonl(coords_path) if Path(coords_path).exists() else []
    coords = sorted(coords, key=_coordinate_weight, reverse=True)
    if max_atoms is not None and int(max_atoms) > 0:
        coords = coords[: int(max_atoms)]
    atoms: list[DefectAtom] = []
    atom_rows: list[dict[str, Any]] = []
    for c in coords:
        cid = str(c.get("coordinate_id") or stable_hash(c, 10))
        tops = c.get("top_loadings") or []
        aliases = []
        for t in tops[:8]:
            key = str(t.get("key") or "")
            if key:
                aliases.append(key)
                aliases.extend(key.replace(".", "_").replace("-", "_").split("_"))
        atom_id = "qcoord_" + cid.replace("qcoord_", "")
        evidence = {
            "source": "quotient_coordinates",
            "coordinate_id": cid,
            "residual_key": ",".join([str((x or {}).get("key")) for x in tops[:3] if isinstance(x, dict)]),
            "top_loadings": tops[:10],
            "support_state_ids": c.get("support_state_ids") or [],
            "mean_residual_norm": c.get("mean_residual_norm"),
            "max_residual_norm": c.get("max_residual_norm"),
            "basis_vector": c.get("basis_vector") or [],
            "response_keys": c.get("response_keys") or [],
        }
        atom = DefectAtom(
            atom_id=atom_id,
            group="quotient_coordinate",
            detector="coker_normal_coordinate",
            intervention_templates=list(dict.fromkeys([a for a in aliases if a]))[:24],
            status="active",
            evidence=evidence,
            description=f"Finite quotient-coordinate candidate {cid} mined from coker normal cluster.",
        )
        atoms.append(atom)
        atom_rows.append(atom.to_dict())
    reg = DefectRegistry(atoms=atoms, version="lean-rgc-defect-registry-v26-qcoord", metadata={
        "source": "quotient_coordinates",
        "canonical_status": "registry_from_quotient_coordinates_chart_not_canonical",
        "n_atoms": len(atoms),
    })
    reg.save(out_registry)
    if out_atoms:
        write_jsonl(out_atoms, atom_rows)
    return {"n_atoms": len(atoms), "out_registry": str(out_registry), "out_atoms": str(out_atoms) if out_atoms else None}


def validate_quotient_coordinates(
    responses_path: str | Path,
    coords_path: str | Path,
    *,
    out_rows: str | Path,
    out_report: str | Path | None = None,
    holdout_fraction: float = 0.35,
    min_support_score: float = 0.0,
    over_refinement_ratio: float = 2.0,
) -> dict[str, Any]:
    """Finite validation chart for quotient-coordinate candidates.

    This is not a proof of canonicality.  It checks whether mined coordinates have
    stable positive support on their source states and whether they are grossly
    over-refined relative to non-support response rows.
    """
    rows = read_jsonl(responses_path) if Path(responses_path).exists() else []
    coords = read_jsonl(coords_path) if Path(coords_path).exists() else []
    out: list[dict[str, Any]] = []
    state_to_rows: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sid = str(r.get("state_id") or r.get("task_id") or "global")
        state_to_rows.setdefault(sid, []).append(r)
    for c in coords:
        cid = str(c.get("coordinate_id") or "qcoord")
        keys = [str(k) for k in c.get("response_keys") or []]
        basis = np.asarray([_safe_float(v) for v in c.get("basis_vector") or []], dtype=float)
        support_states = set(str(x) for x in c.get("support_state_ids") or [])
        support_scores: list[float] = []
        nonsupport_scores: list[float] = []
        all_scores: list[float] = []
        # local response extraction compatible with quotient_coordinates._response_vec
        for r in rows:
            resp = r.get("response") or {}
            if isinstance(resp, dict):
                rv = np.asarray([_safe_float(resp.get(k, 0.0)) for k in keys], dtype=float)
            elif isinstance(r.get("response_flat"), list):
                rv = np.asarray([_safe_float(v) for v in r.get("response_flat")[: len(basis)]], dtype=float)
            else:
                continue
            n = min(len(rv), len(basis))
            if n <= 0:
                continue
            score = float(np.dot(basis[:n], rv[:n]))
            all_scores.append(score)
            sid = str(r.get("state_id") or r.get("task_id") or "global")
            if sid in support_states:
                support_scores.append(score)
            else:
                nonsupport_scores.append(score)
        sm = float(np.mean(support_scores)) if support_scores else 0.0
        hm = float(np.mean(support_scores[int(len(support_scores)*holdout_fraction):])) if support_scores else 0.0
        nm = float(np.max(np.abs(nonsupport_scores))) if nonsupport_scores else 0.0
        am = float(np.mean(all_scores)) if all_scores else 0.0
        support_pass = bool(sm >= min_support_score)
        over_flag = bool(nm > over_refinement_ratio * max(abs(sm), 1e-9) and nm > 0.0)
        if support_pass and not over_flag:
            status = "validated_shadow_candidate"
        elif over_flag:
            status = "possible_over_refinement"
        else:
            status = "open_low_support"
        out.append({
            "coordinate_id": cid,
            "n_support_scores": len(support_scores),
            "n_nonsupport_scores": len(nonsupport_scores),
            "support_mean_score": sm,
            "support_holdout_proxy_score": hm,
            "nonsupport_max_abs_score": nm,
            "all_mean_score": am,
            "support_pass": support_pass,
            "over_refinement_flag": over_flag,
            "chart_status": status,
            "canonical_status": "validation_chart_only_not_canonical",
            "top_loadings": c.get("top_loadings") or [],
        })
    write_jsonl(out_rows, out)
    summary = {
        "n_coordinates": len(coords),
        "n_validation_rows": len(out),
        "by_chart_status": {},
        "canonical_status": "quotient_coordinate_validation_is_finite_chart_not_canonical",
    }
    for r in out:
        summary["by_chart_status"][r["chart_status"]] = summary["by_chart_status"].get(r["chart_status"], 0) + 1
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def run_quotient_coordinate_loop(
    *,
    responses: str | Path,
    out_dir: str | Path,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    cosine_threshold: float = 0.85,
    min_states: int = 1,
    top_action_scores: int = 128,
    margin_threshold: float = 0.0,
    write_actions: bool = True,
    accepted_only: bool = True,
    registry: bool = True,
    validate: bool = True,
    normal_top_k: int | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rep = quotient_coordinates_from_files(
        responses,
        out_dir=out,
        ridge=ridge,
        max_mass=max_mass,
        cosine_threshold=cosine_threshold,
        min_states=min_states,
        score_actions=True,
        top_action_scores=top_action_scores,
        margin_threshold=margin_threshold,
    )
    paths: dict[str, str | None] = {
        "quotient_coordinate_report": str(out / "quotient_coordinate_report.json"),
        "state_coker_normals": str(out / "state_coker_normals.jsonl"),
        "quotient_coordinates": str(out / "quotient_coordinates.jsonl"),
        "quotient_coordinate_action_scores": str(out / "quotient_coordinate_action_scores.jsonl"),
    }
    if write_actions:
        actions_path = out / "quotient_coordinate_candidates.jsonl"
        write_quotient_coordinate_candidate_actions(out / "quotient_coordinate_action_scores.jsonl", actions_path, accepted_only=accepted_only, max_actions=top_action_scores)
        paths["quotient_coordinate_candidates"] = str(actions_path)
    if registry:
        paths["quotient_coordinate_defect_registry"] = str(out / "quotient_coordinate_defect_registry.json")
        paths["quotient_coordinate_defect_atoms"] = str(out / "quotient_coordinate_defect_atoms.jsonl")
        quotient_coordinates_to_defect_registry(out / "quotient_coordinates.jsonl", out_registry=out / "quotient_coordinate_defect_registry.json", out_atoms=out / "quotient_coordinate_defect_atoms.jsonl")
    normal = merged_response_normal_from_coordinates(out / "quotient_coordinates.jsonl", top_k=normal_top_k)
    (out / "quotient_coordinate_response_normal.json").write_text(json.dumps(normal, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["quotient_coordinate_response_normal"] = str(out / "quotient_coordinate_response_normal.json")
    if validate:
        validate_quotient_coordinates(responses, out / "quotient_coordinates.jsonl", out_rows=out / "quotient_coordinate_validation_rows.jsonl", out_report=out / "quotient_coordinate_validation_report.json")
        paths["quotient_coordinate_validation_rows"] = str(out / "quotient_coordinate_validation_rows.jsonl")
        paths["quotient_coordinate_validation_report"] = str(out / "quotient_coordinate_validation_report.json")
    summary = {
        "schema_version": "lean-rgc-quotient-coordinate-loop-v26.0",
        "paths": paths,
        "report": rep,
        "canonical_status": "quotient_coordinate_loop_outputs_are_candidates_not_canonical",
    }
    (out / "quotient_coordinate_loop_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = [
    "run_quotient_coordinate_loop",
    "write_quotient_coordinate_candidate_actions",
    "quotient_coordinates_to_defect_registry",
    "merged_response_normal_from_coordinates",
    "validate_quotient_coordinates",
]
