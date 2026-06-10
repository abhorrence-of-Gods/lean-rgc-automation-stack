from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json

from ..schemas import write_jsonl
from .features import _eval_feature
from .common import (
    SCHEMA_PRIMITIVE_OBSERVABLE,
    SCHEMA_BOUNDED_TRANSCRIPT,
    SCHEMA_FEATURE_CLOSURE,
    SCHEMA_FEATURE_VALUE,
    SCHEMA_FEATURE_SELECTION,
    SCHEMA_AUTO_PLAN,
    SCHEMA_DOST_AUDIT,
    DEFAULT_PRIMITIVE_OBSERVABLES,
    _json_dump,
    _json_load,
    _read_rows,
    _safe_float,
    _as_list,
    _path_if_exists,
    _first_existing,
    _ratio,
    _score_avg,
    _json_bytes,
    _row_identity,
    _status_counter,
    _class_member_count,
    _row_tactic_text,
    _is_macro_policy_row,
    _is_structural_row,
    _nf_status,
    _is_typed_nf_status,
    _matrix_metrics,
)



def _feature_values_by_object(value_rows: list[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in value_rows:
        oid = str(row.get("object_id") or row.get("source_row_id") or "")
        if oid.startswith("obj_row_"):
            oid = oid[len("obj_row_") :]
        vals = row.get("generated_features") if isinstance(row.get("generated_features"), dict) else {}
        for fid, value in vals.items():
            out[oid][str(fid)].append(_safe_float(value))
    return out


def _taxonomy_duals(taxonomy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for face in taxonomy_rows:
        support = (face.get("minimal_support") or {}).get("rows") if isinstance(face.get("minimal_support"), dict) else []
        out.append(
            {
                "dual_component_id": str(face.get("dual_component_id") or "xi_" + stable_hash(face, 12)),
                "target_face_id": str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 12)),
                "support_rows": [str(x) for x in _as_list(support)],
                "dual_source": str(face.get("dual_source") or "row_coker"),
                "retrieval_blockers": (face.get("status") or {}).get("retrieval_blockers") if isinstance(face.get("status"), dict) else [],
            }
        )
    return out


def select_features_for_dual_obstructions(
    feature_closure_path: str | Path,
    feature_values_path: str | Path,
    out: str | Path,
    *,
    report_out: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    max_selected_per_dual: int = 8,
    cost_weight: float = 0.05,
    mem_weight: float = 0.10,
    unsafe_weight: float = 0.25,
) -> dict[str, Any]:
    features = _read_rows(feature_closure_path)
    value_rows = _read_rows(feature_values_path)
    taxonomy_rows = _read_rows(taxonomy_path)
    by_object = _feature_values_by_object(value_rows)
    all_objects = set(by_object)
    duals = _taxonomy_duals(taxonomy_rows)
    if not duals:
        duals = [{"dual_component_id": "xi_global_feature_variance", "target_face_id": None, "support_rows": sorted(all_objects), "dual_source": "global_variance", "retrieval_blockers": []}]

    feature_by_id = {str(f.get("feature_id")): f for f in features}
    selected: list[dict[str, Any]] = []
    for dual in duals:
        face_objects = {str(x) for x in dual.get("support_rows") or []}
        face_objects |= {"obj_row_" + x for x in list(face_objects)}
        normalized_face = {x[len("obj_row_") :] if x.startswith("obj_row_") else x for x in face_objects}
        off_objects = all_objects - normalized_face
        scored: list[dict[str, Any]] = []
        for fid, feature in feature_by_id.items():
            face_vals = [
                _safe_float(v)
                for oid in normalized_face
                for v in by_object.get(oid, {}).get(fid, [])
            ]
            off_vals = [
                _safe_float(v)
                for oid in off_objects
                for v in by_object.get(oid, {}).get(fid, [])
            ]
            all_vals = face_vals + off_vals
            if not all_vals:
                continue
            if face_vals and off_vals:
                dual_support = abs(sum(face_vals) / len(face_vals) - sum(off_vals) / len(off_vals))
            else:
                mean = sum(all_vals) / len(all_vals)
                dual_support = sum((x - mean) ** 2 for x in all_vals) / max(1, len(all_vals))
            cost = _safe_float((feature.get("cost") or {}).get("compute"), 0.1)
            mem_risk = 1.0 if (feature.get("cost") or {}).get("requires_full_state") else 0.0
            unsafe_risk = 0.25 if "unsafe" in json.dumps(feature.get("definition"), sort_keys=True, default=str).lower() else 0.0
            score = dual_support - cost_weight * cost - mem_weight * mem_risk - unsafe_weight * unsafe_risk
            scored.append(
                {
                    "feature_id": fid,
                    "dual_support": float(dual_support),
                    "cost": float(cost),
                    "mem_risk": float(mem_risk),
                    "unsafe_risk": float(unsafe_risk),
                    "score": float(score),
                }
            )
        scored.sort(key=lambda r: (-_safe_float(r.get("score")), str(r.get("feature_id"))))
        for item in scored[: max(0, int(max_selected_per_dual))]:
            selected.append(
                {
                    "schema_version": SCHEMA_FEATURE_SELECTION,
                    "selected_feature_id": item["feature_id"],
                    "dual_component_id": dual["dual_component_id"],
                    "target_face_id": dual.get("target_face_id"),
                    "selection_reason": "max_dual_support_per_cost",
                    "dual_support": item["dual_support"],
                    "cost": item["cost"],
                    "score": item["score"],
                    "mem_risk": item["mem_risk"],
                    "unsafe_risk": item["unsafe_risk"],
                    "blocked": False,
                    "feature_definition": feature_by_id[item["feature_id"]].get("definition"),
                    "dual_source": dual.get("dual_source"),
                    "canonical_status": "selected_feature_witness_not_canonical",
                }
            )

    write_jsonl(out, selected)
    by_dual = Counter(str(r.get("dual_component_id")) for r in selected)
    report = {
        "schema_version": SCHEMA_FEATURE_SELECTION,
        "feature_closure": str(feature_closure_path),
        "feature_values": str(feature_values_path),
        "taxonomy": str(taxonomy_path) if taxonomy_path else None,
        "out": str(out),
        "n_features": len(features),
        "n_feature_value_rows": len(value_rows),
        "n_dual_components": len(duals),
        "n_selected": len(selected),
        "selected_by_dual": dict(sorted(by_dual.items())),
        "canonical_status": "feature_selection_report_not_canonical",
    }
    if report_out:
        _json_dump(report, report_out)
    return report


__all__ = [
    "select_features_for_dual_obstructions",
]
