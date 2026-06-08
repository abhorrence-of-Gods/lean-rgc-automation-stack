from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import read_jsonl, write_jsonl, TacticAction
from .action_geometry import build_action_geometry_registry, score_action_geometry_registry
from .gamma_transition_learner import merge_gamma_transition_patches_into_action_geometry
from .quotient_coordinate_loop import merged_response_normal_from_coordinates


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def normals_from_qgen_report(qgen_report: str | Path | None, *, out_dir: str | Path | None = None) -> dict[str, Any]:
    """Extract finite response/carrier normals from a qgen report.

    These normals are charts of the qgen coker residual, not canonical objects.
    The response normal is keyed by qgen response_keys.  The carrier normal is
    keyed by carrier atoms when qgen residual coordinates live in carrier.*.
    """
    response_normal: dict[str, float] = {}
    carrier_normal: dict[str, float] = {}
    meta: dict[str, Any] = {
        "source": "qgen_report",
        "canonical_status": "qgen_normal_chart_only_not_canonical",
    }
    if qgen_report and Path(qgen_report).exists():
        obj = json.loads(Path(qgen_report).read_text(encoding="utf-8"))
        # v26: accept explicit normal JSONs produced by quotient-coordinate loop.
        if isinstance(obj.get("response_normal"), dict) or isinstance(obj.get("carrier_normal"), dict):
            response_normal.update({str(k): _safe_float(v) for k, v in (obj.get("response_normal") or {}).items() if abs(_safe_float(v)) > 0.0})
            carrier_normal.update({str(k): _safe_float(v) for k, v in (obj.get("carrier_normal") or {}).items() if abs(_safe_float(v)) > 0.0})
            meta["normal_json_kind"] = "explicit_response_carrier_normal"
            meta["normal_json"] = str(qgen_report)
            meta["n_response_normal"] = len(response_normal)
            meta["n_carrier_normal"] = len(carrier_normal)
            out = {"response_normal": response_normal, "carrier_normal": carrier_normal, "metadata": meta}
            if out_dir:
                d = Path(out_dir)
                d.mkdir(parents=True, exist_ok=True)
                (d / "action_geometry_response_normal.json").write_text(json.dumps({"response_normal": response_normal, "metadata": meta}, indent=2, ensure_ascii=False), encoding="utf-8")
                (d / "action_geometry_carrier_normal.json").write_text(json.dumps({"carrier_normal": carrier_normal, "metadata": meta}, indent=2, ensure_ascii=False), encoding="utf-8")
            return out
        keys = [str(k) for k in obj.get("response_keys") or []]
        proj = obj.get("projection") or {}
        normal = proj.get("normal") or proj.get("residual") or []
        for i, k in enumerate(keys[: len(normal)]):
            val = _safe_float(normal[i])
            if abs(val) > 0.0:
                response_normal[k] = val
            if k.startswith("carrier."):
                carrier_normal[k.split(".", 1)[1]] = val
        for proposal in obj.get("generated_defect_atoms") or []:
            atom = proposal.get("atom") if isinstance(proposal, dict) else None
            ev = (atom or {}).get("evidence") if isinstance(atom, dict) else None
            ev = ev or (proposal.get("evidence") if isinstance(proposal, dict) else {}) or {}
            key = str(ev.get("residual_key") or proposal.get("residual_key") or "")
            val = _safe_float(ev.get("normal_value", ev.get("residual_value", proposal.get("normal_value", proposal.get("residual_value", 0.0))))) if isinstance(proposal, dict) else 0.0
            if key.startswith("carrier."):
                carrier_normal.setdefault(key.split(".", 1)[1], val)
        meta["qgen_report"] = str(qgen_report)
        meta["n_response_normal"] = len(response_normal)
        meta["n_carrier_normal"] = len(carrier_normal)
        meta["projection"] = {k: proj.get(k) for k in ["residual_norm", "relative_residual", "support_value", "active_count"] if k in proj}
    out = {"response_normal": response_normal, "carrier_normal": carrier_normal, "metadata": meta}
    if out_dir:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / "action_geometry_response_normal.json").write_text(json.dumps({"response_normal": response_normal, "metadata": meta}, indent=2, ensure_ascii=False), encoding="utf-8")
        (d / "action_geometry_carrier_normal.json").write_text(json.dumps({"carrier_normal": carrier_normal, "metadata": meta}, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _as_action_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a scored action-geometry row into a TacticAction-compatible row."""
    try:
        action = TacticAction.from_dict(row).to_dict()
    except Exception:
        action = {
            "action_id": str(row.get("action_id") or row.get("tactic") or "action_geometry_candidate"),
            "tactic": str(row.get("tactic") or row.get("action_id") or "skip"),
            "tactic_class": str(row.get("tactic_class") or "action_geometry"),
            "carrier_tags": [str(x) for x in row.get("carrier_tags", []) or []],
            "cost_estimate": _safe_float(row.get("cost_estimate", 1.0), 1.0),
            "metadata": {},
        }
    meta = dict(action.get("metadata") or {})
    meta["action_geometry"] = {
        "source": "action_geometry_retrieval",
        "score": _safe_float(row.get("action_geometry_score")),
        "score_terms": row.get("score_terms") or {},
        "canonical_status": "retrieved_action_geometry_witness_not_canonical",
        "response_keys": row.get("response_keys") or [],
    }
    # Preserve original metadata if present under extra.
    if isinstance(row.get("metadata"), dict):
        meta.setdefault("source_metadata", row.get("metadata"))
    action["metadata"] = meta
    return action


def write_action_geometry_candidate_actions(scored_path: str | Path, out_actions: str | Path, *, accepted_only: bool = False) -> dict[str, Any]:
    rows = read_jsonl(scored_path) if Path(scored_path).exists() else []
    acts: list[dict[str, Any]] = []
    for row in rows:
        if accepted_only and not bool(row.get("action_geometry_accept")):
            continue
        acts.append(_as_action_row(row))
    write_jsonl(out_actions, acts)
    return {"n_rows": len(rows), "n_actions": len(acts), "out_actions": str(out_actions), "accepted_only": bool(accepted_only)}


def run_action_geometry_from_qgen(
    *,
    responses: str | Path,
    actions: str | Path | None,
    qgen_report: str | Path | None,
    out_dir: str | Path,
    quotient_coordinates: str | Path | None = None,
    response_normal_json: str | Path | None = None,
    transitions: str | Path | None = None,
    top_k: int | None = None,
    tail_weight: float = 0.25,
    cost_weight: float = 0.05,
    uncertainty_weight: float = 0.10,
    audit_weight: float = 0.20,
    require_carrier_safe: bool = False,
    carrier_budget: float = 0.0,
    min_count: int = 1,
    gamma_transition_patches: str | Path | None = None,
    gamma_aware: bool = False,
    gamma_mode: str = "finite_horizon",
    gamma_horizon: int = 4,
    gamma_discount: float = 1.0,
    gamma_value_weight: float = 0.50,
    gamma_stability_delta: float = 0.05,
    gamma_tail_risk_mode: str = "spectral",
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    registry = out / "action_geometry.jsonl"
    registry_summary = out / "action_geometry_summary.json"
    build_action_geometry_registry(responses, registry, summary_out=registry_summary, actions_path=actions, transitions_path=transitions, min_count=min_count)

    registry_for_scoring = registry
    gamma_patch_report: str | None = None
    if gamma_transition_patches and Path(gamma_transition_patches).exists():
        patched = out / "action_geometry_gamma_patched_for_retrieval.jsonl"
        patch_report = out / "action_geometry_gamma_patch_for_retrieval_report.json"
        merge_gamma_transition_patches_into_action_geometry(registry, gamma_transition_patches, patched, summary_out=patch_report)
        registry_for_scoring = patched
        gamma_patch_report = str(patch_report)

    normal_source = response_normal_json if response_normal_json and Path(response_normal_json).exists() else qgen_report
    normals = normals_from_qgen_report(normal_source, out_dir=out)
    if quotient_coordinates and Path(quotient_coordinates).exists():
        qn = merged_response_normal_from_coordinates(quotient_coordinates)
        (out / "quotient_coordinate_response_normal_for_action_geometry.json").write_text(json.dumps(qn, indent=2, ensure_ascii=False), encoding="utf-8")
        rn = dict(normals.get("response_normal") or {})
        for k, v in (qn.get("response_normal") or {}).items():
            rn[k] = rn.get(k, 0.0) + float(v)
        cn = dict(normals.get("carrier_normal") or {})
        for k, v in (qn.get("carrier_normal") or {}).items():
            cn[k] = cn.get(k, 0.0) + float(v)
        normals["response_normal"] = rn
        normals["carrier_normal"] = cn
        normals.setdefault("metadata", {})["quotient_coordinates"] = str(quotient_coordinates)

    selected = out / "action_geometry_candidates_scored.jsonl"
    selected_summary = out / "action_geometry_selected_summary.json"
    score_action_geometry_registry(
        registry_for_scoring,
        selected,
        summary_out=selected_summary,
        response_normal=normals.get("response_normal"),
        carrier_normal=normals.get("carrier_normal"),
        top_k=top_k,
        tail_weight=tail_weight,
        cost_weight=cost_weight,
        uncertainty_weight=uncertainty_weight,
        audit_weight=audit_weight,
        require_carrier_safe=require_carrier_safe,
        carrier_budget=carrier_budget,
        gamma_aware=gamma_aware,
        gamma_mode=gamma_mode,
        gamma_horizon=gamma_horizon,
        gamma_discount=gamma_discount,
        gamma_value_weight=gamma_value_weight,
        gamma_stability_delta=gamma_stability_delta,
        gamma_tail_risk_mode=gamma_tail_risk_mode,
    )
    candidates = out / "action_geometry_candidates.jsonl"
    cand_meta = write_action_geometry_candidate_actions(selected, candidates, accepted_only=False)
    summary = {
        "registry": str(registry),
        "registry_for_scoring": str(registry_for_scoring),
        "gamma_transition_patches": str(gamma_transition_patches) if gamma_transition_patches else None,
        "gamma_patch_report": gamma_patch_report,
        "selected": str(selected),
        "candidates": str(candidates),
        "normal_source": str(qgen_report) if qgen_report else None,
        "quotient_coordinates_source": str(quotient_coordinates) if quotient_coordinates else None,
        "n_candidates": cand_meta.get("n_actions", 0),
        "gamma_aware": bool(gamma_aware),
        "gamma_mode": str(gamma_mode),
        "gamma_horizon": int(gamma_horizon),
        "gamma_discount": float(gamma_discount),
        "gamma_value_weight": float(gamma_value_weight),
        "gamma_stability_delta": float(gamma_stability_delta),
        "gamma_tail_risk_mode": str(gamma_tail_risk_mode),
        "canonical_status": "action_geometry_retrieval_chart_only_not_canonical",
    }
    (out / "action_geometry_loop_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = [
    "normals_from_qgen_report",
    "run_action_geometry_from_qgen",
    "write_action_geometry_candidate_actions",
]
