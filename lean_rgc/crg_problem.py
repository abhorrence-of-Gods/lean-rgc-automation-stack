from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .response_completion import load_completion
from .schemas import read_jsonl, stable_hash, write_records


SCHEMA_CRG_PROBLEM = "lean-rgc-crg-problem-v58.0"


DEFAULT_BUDGET = {
    "cost_max": 4.0,
    "audit_risk_max": 0.2,
    "source_risk_max": 0.1,
    "ghost_risk_max": 0.1,
    "hardening_cost_max": 8.0,
}


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


def _as_float_map(obj: Any) -> dict[str, float]:
    if not isinstance(obj, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in obj.items():
        try:
            out[str(key)] = float(value)
        except Exception:
            out[str(key)] = 0.0
    return out


def _normal_from_dual(row: dict[str, Any]) -> dict[str, float]:
    normal = row.get("normal_vector") if isinstance(row.get("normal_vector"), dict) else {}
    out: dict[str, float] = {}
    for key, value in _as_float_map(normal.get("response_weights")).items():
        out[key] = out.get(key, 0.0) + float(value)
    for prefix, field in [
        ("carrier", "carrier_weights"),
        ("gamma", "gamma_weights"),
        ("domain", "domain_weights"),
        ("cost", "cost_weights"),
        ("generated_feature", "generated_feature_weights"),
    ]:
        for key, value in _as_float_map(normal.get(field)).items():
            nkey = key if key.startswith(prefix + ".") else f"{prefix}.{key}"
            out[nkey] = out.get(nkey, 0.0) + float(value)
    # Permit already-flat problem-like rows in tests and downstream tools.
    for key, value in _as_float_map(row.get("lambda_normal") or row.get("normal")).items():
        out[key] = out.get(key, 0.0) + float(value)
    return dict(sorted(out.items()))


def _normal_from_face(row: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in _as_float_map(row.get("positive_response_face")).items():
        out[str(key)] = out.get(str(key), 0.0) + float(value)
    for prefix, field in [
        ("carrier", "carrier_face"),
        ("gamma", "gamma_face"),
        ("cost", "cost_face"),
    ]:
        for key, value in _as_float_map(row.get(field)).items():
            nkey = key if key.startswith(prefix + ".") else f"{prefix}.{key}"
            out[nkey] = out.get(nkey, 0.0) + float(value)
    return dict(sorted(out.items()))


def _face_id(row: dict[str, Any]) -> str:
    return str(row.get("face_id") or row.get("taxonomy_face_id") or row.get("exposed_face_id") or stable_hash(row, 14))


def _dual_face_id(row: dict[str, Any]) -> str:
    return str(row.get("exposed_face_id") or row.get("face_id") or row.get("taxonomy_face_id") or stable_hash(row, 14))


def _source_repair_face_ids(row: dict[str, Any]) -> set[str]:
    out = {str(x) for x in (row.get("source_repair_face_ids") or []) if str(x)}
    if row.get("exposed_face_id"):
        out.add(str(row.get("exposed_face_id")))
    return out


def _problem_row(
    *,
    face: dict[str, Any] | None,
    dual: dict[str, Any] | None,
    completion: dict[str, Any],
    budget: dict[str, float],
    repair_space_scope: str,
) -> dict[str, Any]:
    parent_face_id = _face_id(face or dual or {})
    obstruction_id = str((dual or {}).get("dual_component_id") or (face or {}).get("source_class_id") or "lambda_" + stable_hash(parent_face_id, 10))
    normal = _normal_from_dual(dual or {}) or _normal_from_face(face or {})
    pid = "crg_" + stable_hash({"face": parent_face_id, "obstruction": obstruction_id, "normal": normal, "budget": budget}, 16)
    return {
        "schema_version": SCHEMA_CRG_PROBLEM,
        "problem_id": pid,
        "parent_face_id": parent_face_id,
        "obstruction_id": obstruction_id,
        "objective": {
            "type": "support_maximization",
            "lambda_normal": normal,
            "response_space": str(completion.get("topology") or "weighted_projective_response"),
            "response_completion_id": completion.get("probe_family_id"),
        },
        "repair_space_scope": repair_space_scope,
        "budget": budget,
        "safety": {
            "source_safe": True,
            "audit_safe": True,
            "replay_safe": True,
            "carrier_safe": True,
            "overrefinement_guard": True,
        },
        "argmax_quotient": {
            "equivalence": "same_response_and_paid_equivalent_cost",
            "selector_status": "set_valued_no_doctrine_selector",
        },
        "source_refs": {
            "repair_face_id": _face_id(face) if face else None,
            "dual_component_id": (dual or {}).get("dual_component_id"),
            "source_repair_face_ids": sorted(_source_repair_face_ids(dual or {})),
        },
        "canonical_status": "optimization_problem_canonical_candidate_not_generator",
    }


def build_crg_problems(
    *,
    out: str | Path,
    repair_faces_path: str | Path | None = None,
    tower_dual_components_path: str | Path | None = None,
    response_completion_path: str | Path | None = None,
    summary_out: str | Path | None = None,
    budget: dict[str, Any] | None = None,
    repair_space_scope: str = "relaxed",
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    faces = _read_rows(repair_faces_path)
    duals = _read_rows(tower_dual_components_path)
    completion = load_completion(response_completion_path)
    b = {**DEFAULT_BUDGET, **{str(k): float(v) for k, v in (budget or {}).items()}}

    rows: list[dict[str, Any]] = []
    faces_by_id = {_face_id(face): face for face in faces}
    if duals:
        for dual in duals:
            repair_ids = _source_repair_face_ids(dual)
            matched = [faces_by_id[rid] for rid in sorted(repair_ids) if rid in faces_by_id]
            if not matched and _dual_face_id(dual) in faces_by_id:
                matched = [faces_by_id[_dual_face_id(dual)]]
            if not matched:
                matched = [None]
            for face in matched:
                rows.append(
                    _problem_row(
                        face=face,
                        dual=dual,
                        completion=completion,
                        budget=b,
                        repair_space_scope=repair_space_scope,
                    )
                )
    else:
        for face in faces:
            rows.append(
                _problem_row(
                    face=face,
                    dual=None,
                    completion=completion,
                    budget=b,
                    repair_space_scope=repair_space_scope,
                )
            )

    # If neither input has rows, still emit an empty report rather than an
    # invented problem. That keeps canonicality explicit.
    write_records(out, rows, schema_version=SCHEMA_CRG_PROBLEM, run_id=run_id, parent_ids=parent_ids)
    summary = {
        "schema_version": SCHEMA_CRG_PROBLEM,
        "out": str(out),
        "repair_faces": str(repair_faces_path) if repair_faces_path else None,
        "tower_dual_components": str(tower_dual_components_path) if tower_dual_components_path else None,
        "response_completion": str(response_completion_path) if response_completion_path else None,
        "n_repair_faces": len(faces),
        "n_dual_components": len(duals),
        "n_problems": len(rows),
        "canonical_status": "crg_problem_ledger_is_canonical_problem_chart_not_generator",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_CRG_PROBLEM", "DEFAULT_BUDGET", "build_crg_problems"]
