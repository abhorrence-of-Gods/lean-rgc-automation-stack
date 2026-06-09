from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_CONCEPT_SEARCH = "lean-rgc-concept-search-row-v62.0"


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
        out = float(value)
    except Exception:
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def _embedding(point: dict[str, Any]) -> dict[str, float]:
    if isinstance(point.get("response_embedding_map"), dict):
        return {str(k): _safe_float(v) for k, v in point["response_embedding_map"].items()}
    emb = point.get("response_embedding") if isinstance(point.get("response_embedding"), dict) else {}
    keys = [str(k) for k in (emb.get("keys") or [])]
    vals = [_safe_float(v) for v in (emb.get("values") or [])]
    return {k: vals[i] if i < len(vals) else 0.0 for i, k in enumerate(keys)}


def _normal_from_problem(row: dict[str, Any]) -> dict[str, float]:
    obj = row.get("objective") if isinstance(row.get("objective"), dict) else {}
    normal = obj.get("lambda_normal") if isinstance(obj.get("lambda_normal"), dict) else {}
    return {str(k): _safe_float(v) for k, v in normal.items()}


def _parse_normal(value: dict[str, Any] | str | Path | None, problems_path: str | Path | None) -> dict[str, float]:
    if isinstance(value, dict):
        return {str(k): _safe_float(v) for k, v in value.items()}
    if value:
        text = str(value)
        p = Path(text)
        obj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(text)
        if isinstance(obj, dict) and "normal" in obj and isinstance(obj["normal"], dict):
            obj = obj["normal"]
        if isinstance(obj, dict):
            return {str(k): _safe_float(v) for k, v in obj.items()}
    for row in _read_rows(problems_path):
        n = _normal_from_problem(row)
        if n:
            return n
    return {}


def _dot(normal: dict[str, float], emb: dict[str, float]) -> float:
    return float(sum(float(v) * float(emb.get(k, 0.0)) for k, v in normal.items()))


def search_concepts(
    *,
    concept_points_path: str | Path,
    concept_edges_path: str | Path | None = None,
    out: str | Path,
    summary_out: str | Path | None = None,
    response_normal: dict[str, Any] | str | Path | None = None,
    problems_path: str | Path | None = None,
    top_k: int | None = 32,
    mode: str = "response-nearest-neighbor",
) -> dict[str, Any]:
    points = _read_rows(concept_points_path)
    edges = _read_rows(concept_edges_path)
    normal = _parse_normal(response_normal, problems_path)
    point_by_id = {str(p.get("concept_id")): p for p in points}
    rows: list[dict[str, Any]] = []
    for point in points:
        cost = point.get("cost_embedding") if isinstance(point.get("cost_embedding"), dict) else {}
        score = _dot(normal, _embedding(point))
        risk = _safe_float(cost.get("hardening_risk"), 0.0) + _safe_float(cost.get("audit_risk"), 0.0)
        rows.append(
            {
                "schema_version": SCHEMA_CONCEPT_SEARCH,
                "search_row_id": "csearch_" + stable_hash({"concept": point.get("concept_id"), "mode": "response-nearest-neighbor"}, 14),
                "concept_id": point.get("concept_id"),
                "search_method": "response-nearest-neighbor",
                "repair_score": float(score - risk),
                "response_score": float(score),
                "hardening_risk": _safe_float(cost.get("hardening_risk"), 0.0),
                "audit_risk": _safe_float(cost.get("audit_risk"), 0.0),
                "decoder": point.get("decoder"),
                "status": "concept_search_witness",
                "canonical_status": "concept_search_witness_not_canonical",
                "provenance": {"concept_point": point},
            }
        )
    if mode in {"operation-graph", "operation-graph expansion", "operation_graph", "all"}:
        for edge in edges:
            src = point_by_id.get(str(edge.get("source_concept_id")))
            dst = point_by_id.get(str(edge.get("target_concept_id")))
            if not (src and dst):
                continue
            score = 0.5 * _dot(normal, _embedding(src)) + _dot(normal, _embedding(dst)) - _safe_float(edge.get("edge_cost"), 0.0)
            rows.append(
                {
                    "schema_version": SCHEMA_CONCEPT_SEARCH,
                    "search_row_id": "csearch_" + stable_hash({"edge": edge.get("edge_id"), "mode": "operation-graph"}, 14),
                    "concept_id": dst.get("concept_id"),
                    "source_concept_id": src.get("concept_id"),
                    "edge_id": edge.get("edge_id"),
                    "search_method": "operation-graph expansion",
                    "repair_score": float(score),
                    "response_score": float(score + _safe_float(edge.get("edge_cost"), 0.0)),
                    "hardening_risk": _safe_float((dst.get("cost_embedding") or {}).get("hardening_risk"), 0.0),
                    "audit_risk": _safe_float((dst.get("cost_embedding") or {}).get("audit_risk"), 0.0),
                    "decoder": dst.get("decoder"),
                    "status": "concept_deformation_search_witness",
                    "canonical_status": "concept_search_witness_not_canonical",
                    "provenance": {"concept_point": dst, "concept_edge": edge},
                }
            )
    rows.sort(key=lambda row: (float(row.get("repair_score") or 0.0), str(row.get("concept_id"))), reverse=True)
    if top_k is not None and int(top_k) > 0:
        rows = rows[: int(top_k)]
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_CONCEPT_SEARCH,
        "concept_points": str(concept_points_path),
        "concept_edges": str(concept_edges_path) if concept_edges_path else None,
        "out": str(out),
        "n_points": len(points),
        "n_edges": len(edges),
        "n_rows": len(rows),
        "normal_keys": sorted(normal),
        "mode": mode,
        "canonical_status": "concept_search_is_variational_witness_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_CONCEPT_SEARCH", "search_concepts"]
