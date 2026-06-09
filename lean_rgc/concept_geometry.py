from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_CONCEPT_POINT = "lean-rgc-concept-point-v62.0"
SCHEMA_CONCEPT_EDGE = "lean-rgc-concept-edge-v62.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _point_species(row: dict[str, Any]) -> str:
    dual_source = str(row.get("dual_source") or "")
    if dual_source == "mixed_curvature":
        return "gamma_policy_like"
    if dual_source == "carrier_split":
        return "capacity_like"
    if dual_source == "separator_split":
        return "atlas_like"
    if dual_source == "row_coker":
        return "premise_like"
    return "kernel_like"


def _embedding_from_positive_face(row: dict[str, Any]) -> dict[str, float]:
    face = row.get("positive_face") if isinstance(row.get("positive_face"), dict) else {}
    out: dict[str, float] = {}
    for key in face.get("response_basis") or []:
        out[str(key).replace("summary::resp_pos::", "")] = 1.0
    for key in face.get("carrier_basis") or []:
        out["carrier." + str(key)] = 1.0
    for key in face.get("gamma_basis") or []:
        out["gamma." + str(key)] = 1.0
    for key in face.get("generated_feature_basis") or []:
        out["generated_feature." + str(key)] = 1.0
    return out


def _concept_from_taxonomy(row: dict[str, Any]) -> dict[str, Any]:
    cid = str(row.get("concept_id") or ("concept_" + stable_hash(row, 14)))
    emb = _embedding_from_positive_face(row)
    status = row.get("status") if isinstance(row.get("status"), dict) else {}
    return {
        "schema_version": SCHEMA_CONCEPT_POINT,
        "concept_id": cid,
        "source_id": row.get("taxonomy_face_id"),
        "concept_species": _point_species(row),
        "origin": "completion",
        "decoder": {"decoder_type": "to_repair_species", "target_species": "context_portfolio"},
        "response_embedding": {"keys": sorted(emb), "values": [float(emb[k]) for k in sorted(emb)]},
        "response_embedding_map": dict(sorted(emb.items())),
        "operation_history": [{"op": "finite_dual_face_taxonomy"}, {"op": str(row.get("dual_source") or "expose")}],
        "cost_embedding": {
            "description_cost": float(len(emb) or 1),
            "audit_risk": 0.0 if status.get("heldout_validated") else 0.1,
            "hardening_risk": 0.1 if status.get("retrieval_allowed") else 0.3,
        },
        "canonical_status": "concept_chart_not_canonical",
        "provenance": {"taxonomy_row": row},
    }


def _concept_from_feature(row: dict[str, Any]) -> dict[str, Any]:
    fid = str(row.get("feature_id") or row.get("selected_feature_id") or stable_hash(row, 14))
    emb_key = "generated_feature." + fid
    return {
        "schema_version": SCHEMA_CONCEPT_POINT,
        "concept_id": "concept_feature_" + stable_hash(fid, 12),
        "source_id": fid,
        "concept_species": "kernel_like",
        "origin": "language_chart",
        "decoder": {"decoder_type": "to_repair_species", "target_species": "concept_latent"},
        "response_embedding": {"keys": [emb_key], "values": [1.0]},
        "response_embedding_map": {emb_key: 1.0},
        "operation_history": [{"op": "feature_selection"}, {"op": "language_chart"}],
        "cost_embedding": {
            "description_cost": _safe_float(row.get("description_cost"), 1.0),
            "audit_risk": _safe_float(row.get("unsafe_weight"), 0.1),
            "hardening_risk": 0.35,
        },
        "canonical_status": "concept_chart_not_canonical",
        "provenance": {"feature_row": row},
    }


def build_concept_geometry(
    *,
    out_dir: str | Path,
    taxonomy_path: str | Path | None = None,
    selected_features_path: str | Path | None = None,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    taxonomy = _read_rows(taxonomy_path)
    features = _read_rows(selected_features_path)
    points = [_concept_from_taxonomy(row) for row in taxonomy]
    points.extend(_concept_from_feature(row) for row in features)
    seen: set[str] = set()
    dedup_points: list[dict[str, Any]] = []
    for point in points:
        cid = str(point.get("concept_id"))
        if cid in seen:
            continue
        seen.add(cid)
        dedup_points.append(point)
    edges: list[dict[str, Any]] = []
    taxonomy_points = [p for p in dedup_points if str(p.get("origin")) == "completion"]
    feature_points = [p for p in dedup_points if str(p.get("origin")) == "language_chart"]
    for src in taxonomy_points:
        for dst in feature_points[:16]:
            edges.append(
                {
                    "schema_version": SCHEMA_CONCEPT_EDGE,
                    "edge_id": "cedge_" + stable_hash({"src": src.get("concept_id"), "dst": dst.get("concept_id"), "op": "atlasify"}, 14),
                    "source_concept_id": src.get("concept_id"),
                    "target_concept_id": dst.get("concept_id"),
                    "operation": "atlasify",
                    "edge_cost": 0.3,
                    "audit_status": "unchecked",
                    "canonical_status": "concept_deformation_witness",
                }
            )
    write_jsonl(out_path / "concept_points.jsonl", dedup_points)
    write_jsonl(out_path / "concept_edges.jsonl", edges)
    summary = {
        "schema_version": SCHEMA_CONCEPT_POINT,
        "out_dir": str(out_path),
        "taxonomy": str(taxonomy_path) if taxonomy_path else None,
        "selected_features": str(selected_features_path) if selected_features_path else None,
        "n_points": len(dedup_points),
        "n_edges": len(edges),
        "artifacts": {
            "concept_points": str(out_path / "concept_points.jsonl"),
            "concept_edges": str(out_path / "concept_edges.jsonl"),
        },
        "canonical_status": "concept_geometry_is_response_metric_chart_not_canonical",
    }
    _json_dump(summary, summary_out or out_path / "concept_geometry_report.json")
    return summary


__all__ = ["SCHEMA_CONCEPT_POINT", "SCHEMA_CONCEPT_EDGE", "build_concept_geometry"]
