from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import json
import math

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_TOWER_OBJECT = "lean-rgc-obstruction-tower-object-v54.0"
SCHEMA_TOWER_TRANSCRIPT = "lean-rgc-obstruction-tower-transcript-v54.0"
SCHEMA_TOWER_FACE = "lean-rgc-obstruction-tower-face-v54.0"
SCHEMA_TOWER_DUAL = "lean-rgc-obstruction-tower-dual-component-v54.0"
SCHEMA_TOWER_BOUNDARY = "lean-rgc-obstruction-tower-boundary-v54.0"
SCHEMA_TOWER_PROMOTION = "lean-rgc-obstruction-tower-promotion-v54.0"
SCHEMA_TOWER_NEXT_ACTION = "lean-rgc-obstruction-tower-next-action-v54.0"
SCHEMA_TOWER_RETRIEVAL = "lean-rgc-obstruction-tower-retrieval-v54.0"
SCHEMA_TOWER_SUMMARY = "lean-rgc-obstruction-tower-summary-v54.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("premise_use_id") or row.get("premise_use_row_id") or row.get("row_id") or stable_hash(row, 14))


def _context_from_key(key: str) -> str:
    return key.split("::", 1)[0] if "::" in key else "__global__"


def _kind_metric_from_key(key: str) -> tuple[str, str]:
    parts = key.split("::")
    if len(parts) >= 3:
        return parts[1], "::".join(parts[2:])
    return "metric", key


def _carrier_safe_from_row(row: dict[str, Any]) -> bool:
    carrier = row.get("carrier_summary") if isinstance(row.get("carrier_summary"), dict) else {}
    audit = row.get("audit_summary") if isinstance(row.get("audit_summary"), dict) else {}
    if _safe_float(audit.get("unsafe")) > 0:
        return False
    if _safe_float(audit.get("hidden_obligations")) > 0:
        return False
    return all(_safe_float(v) >= 0 for v in carrier.values())


def _status_mode(row: dict[str, Any]) -> str:
    counts = row.get("status_counts") if isinstance(row.get("status_counts"), dict) else {}
    if not counts:
        return "unknown"
    return str(max(counts.items(), key=lambda kv: _safe_float(kv[1]))[0])


def _infer_order(face: dict[str, Any]) -> tuple[int, int, str]:
    """Finite approximation of ord(xi) and interaction order.

    The real DOST order is defined by support functions over a filtered
    universal repair cone.  Here we use the finite taxonomy chart as evidence:
    row/separator/carrier split faces are level 0, gamma/mixed-curvature faces
    are interaction level 1, and explicitly upper-failure faces are level 2.
    """

    dual_source = str(face.get("dual_source") or "")
    name = str(((face.get("human_name") or {}).get("suggested")) or "")
    pos = face.get("positive_face") if isinstance(face.get("positive_face"), dict) else {}
    gamma_basis = _as_list(pos.get("gamma_basis"))
    if dual_source == "upper_failure" or "plan" in name or "transfer" in name:
        return 2, 1, "finite_taxonomy_upper_failure_hint"
    if dual_source == "mixed_curvature" or gamma_basis:
        return 1, 2, "finite_taxonomy_mixed_curvature_hint"
    return 0, 1, "finite_support_function_first_positive_approximation"


def _face_kind(face: dict[str, Any]) -> str:
    dual_source = str(face.get("dual_source") or "")
    if dual_source == "separator_split":
        return "separator"
    if dual_source in {"mixed_curvature", "upper_failure"}:
        return "mixed"
    return "row"


def _validation_counts(face: dict[str, Any]) -> dict[str, int]:
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    counts = status.get("validation_status_counts")
    if isinstance(counts, dict):
        return {str(k): int(v) for k, v in counts.items()}
    return {}


def _retrieval_blockers(face: dict[str, Any]) -> list[str]:
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    return [str(x) for x in _as_list(status.get("retrieval_blockers"))]


def _support_rows(face: dict[str, Any]) -> list[str]:
    support = face.get("minimal_support") if isinstance(face.get("minimal_support"), dict) else {}
    return [str(x) for x in _as_list(support.get("rows"))]


def _source_repair_faces(face: dict[str, Any]) -> list[str]:
    return [str(x) for x in _as_list(face.get("source_repair_face_ids")) if str(x)]


def _carrier_status(face: dict[str, Any]) -> str:
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    return str(status.get("carrier_status") or ("safe" if status.get("carrier_safe") else "unknown"))


def _retrieval_allowed(face: dict[str, Any]) -> bool:
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    return bool(status.get("retrieval_allowed"))


def _object_from_fingerprint(row: dict[str, Any]) -> dict[str, Any]:
    uid = _row_id(row)
    return {
        "schema_version": SCHEMA_TOWER_OBJECT,
        "object_id": "obj_row_" + uid,
        "source_row_id": uid,
        "object_family_hint": str(row.get("use_mode") or row.get("tactic_class") or row.get("premise_id") or "row_like"),
        "family_hint_noncanonical": True,
        "construction_depth_chart": 0,
        "canonical_level": None,
        "canonical_level_source": None,
        "typed_signature": {
            "premise_id": row.get("premise_id"),
            "use_mode": row.get("use_mode"),
            "tactic_class": row.get("tactic_class"),
        },
        "domain_signature": {
            "domain_support": _as_list(row.get("domain_support")),
            "domain_hash": stable_hash(_as_list(row.get("domain_support")), 16),
        },
        "carrier_signature": {
            "carrier_safe": _carrier_safe_from_row(row),
            "carrier_summary": row.get("carrier_summary") if isinstance(row.get("carrier_summary"), dict) else {},
            "audit_summary": row.get("audit_summary") if isinstance(row.get("audit_summary"), dict) else {},
        },
        "tail_signature": {
            "gamma_summary": row.get("gamma_summary") if isinstance(row.get("gamma_summary"), dict) else {},
        },
        "cost": row.get("cost_summary") if isinstance(row.get("cost_summary"), dict) else {},
        "construction_trace": {
            "subobject_ids": [],
            "source_face_ids": [],
            "replay_trace_id": None,
        },
        "kernel_backed": True,
        "kernel_replay_status": "observed_or_pending",
        "canonical_status": "object_witness_not_canonical",
    }


def _object_from_face(face: dict[str, Any]) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    k, _, source = _infer_order(face)
    support = _support_rows(face)
    return {
        "schema_version": SCHEMA_TOWER_OBJECT,
        "object_id": "obj_face_" + face_id,
        "source_face_id": face_id,
        "object_family_hint": str(((face.get("human_name") or {}).get("suggested")) or face.get("dual_source") or "face_like"),
        "family_hint_noncanonical": True,
        "construction_depth_chart": k,
        "canonical_level": k,
        "canonical_level_source": source,
        "typed_signature": {
            "dual_component_id": face.get("dual_component_id"),
            "dual_source": face.get("dual_source"),
            "source_class_ids": _as_list(face.get("source_class_ids")),
        },
        "domain_signature": (face.get("signatures") or {}) if isinstance(face.get("signatures"), dict) else {},
        "carrier_signature": {
            "carrier_status": _carrier_status(face),
            "carrier_safe": bool((face.get("status") or {}).get("carrier_safe")) if isinstance(face.get("status"), dict) else None,
        },
        "tail_signature": {
            "tail_signature": ((face.get("signatures") or {}).get("tail_signature")) if isinstance(face.get("signatures"), dict) else None,
        },
        "cost": {},
        "construction_trace": {
            "subobject_ids": ["obj_row_" + uid for uid in support],
            "source_face_ids": _source_repair_faces(face),
            "replay_trace_id": None,
        },
        "kernel_backed": bool(support),
        "kernel_replay_status": "finite_face_chart_pending_replay",
        "canonical_status": "object_witness_not_canonical",
    }


def _transcripts_from_fingerprint(row: dict[str, Any]) -> list[dict[str, Any]]:
    uid = _row_id(row)
    fp = row.get("fingerprint") if isinstance(row.get("fingerprint"), dict) else {}
    out: list[dict[str, Any]] = []
    for key, raw in sorted(fp.items()):
        if not isinstance(raw, (int, float)):
            continue
        kind, metric = _kind_metric_from_key(str(key))
        value = _safe_float(raw)
        transcript = {
            "schema_version": SCHEMA_TOWER_TRANSCRIPT,
            "transcript_id": "tr_" + stable_hash({"row": uid, "key": key}, 14),
            "object_id": "obj_row_" + uid,
            "context_id": _context_from_key(str(key)),
            "level_chart": 0,
            "baseline_id": None,
            "baseline_complete": True,
            "response_delta": {metric: value} if kind == "resp" else {},
            "carrier_delta": {metric: value} if kind == "carrier" else {},
            "gamma_delta": {metric: value} if kind == "gamma" else {},
            "domain_status": "observed",
            "kernel_delta": {
                "fingerprint_key": key,
                "fingerprint_kind": kind,
                "fingerprint_metric": metric,
            },
            "cost": {metric: value} if kind == "cost" else {},
            "status": _status_mode(row),
            "kernel_backed": True,
            "replay_status": "pending",
            "canonical_status": "finite_transcript_cell_not_canonical",
        }
        out.append(transcript)
    return out


def _tower_face(face: dict[str, Any], boundary_status: str) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    k, _, _ = _infer_order(face)
    source_classes = [str(x) for x in _as_list(face.get("source_class_ids"))]
    validation_counts = _validation_counts(face)
    validation_status = "unvalidated"
    if validation_counts:
        validation_status = max(validation_counts.items(), key=lambda kv: kv[1])[0]
    return {
        "schema_version": SCHEMA_TOWER_FACE,
        "face_id": face_id,
        "source_taxonomy_face_id": face_id,
        "face_kind": _face_kind(face),
        "level_chart": k,
        "canonical_level": k,
        "dual_component_id": face.get("dual_component_id"),
        "positive_face_signature": face.get("positive_face") if isinstance(face.get("positive_face"), dict) else {},
        "realizing_object_ids": ["obj_row_" + uid for uid in _support_rows(face)],
        "minimal_context_support": ((face.get("minimal_support") or {}).get("contexts") or []) if isinstance(face.get("minimal_support"), dict) else [],
        "boundary_status": boundary_status,
        "validation_status": validation_status,
        "poms_status": "pending",
        "canonical_status": "dual_exposed_finite_face_not_canonical",
        "metadata": {
            "source_class_ids": source_classes,
            "source_repair_face_ids": _source_repair_faces(face),
            "carrier_status": _carrier_status(face),
        },
    }


def _dual_component(face: dict[str, Any]) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    dual_id = str(face.get("dual_component_id") or ("xi_" + stable_hash(face_id, 12)))
    k, r, source = _infer_order(face)
    pos = face.get("positive_face") if isinstance(face.get("positive_face"), dict) else {}
    return {
        "schema_version": SCHEMA_TOWER_DUAL,
        "dual_component_id": dual_id,
        "dual_source": str(face.get("dual_source") or "row_coker"),
        "normal_vector": {
            "response_weights": {str(x): 1.0 for x in _as_list(pos.get("response_basis"))},
            "carrier_weights": {str(x): 1.0 for x in _as_list(pos.get("carrier_basis"))},
            "gamma_weights": {str(x): 1.0 for x in _as_list(pos.get("gamma_basis"))},
            "domain_weights": {str(x): 1.0 for x in _as_list(pos.get("domain_basis"))},
            "cost_weights": {str(x): -1.0 for x in _as_list(pos.get("cost_basis"))},
            "generated_feature_weights": {str(x): 1.0 for x in _as_list(pos.get("generated_feature_basis"))},
        },
        "minimal_repair_order": {
            "construction_depth": k,
            "interaction_order": r,
            "source": source,
        },
        "exposed_face_id": face_id,
        "canonical_status": "finite_dual_component_not_canonical",
    }


def _boundary(face: dict[str, Any]) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    source_faces = _source_repair_faces(face)
    support = _support_rows(face)
    alternatives: list[dict[str, Any]] = []
    if source_faces:
        alternatives.append(
            {
                "boundary_id": "bd_" + stable_hash({"face": face_id, "source_faces": source_faces}, 12),
                "lower_face_ids": source_faces,
                "realizing_object_ids": ["obj_row_" + uid for uid in support],
                "replay_certified": False,
                "cost": {},
                "status": "available",
            }
        )
    elif support:
        alternatives.append(
            {
                "boundary_id": "bd_" + stable_hash({"face": face_id, "rows": support}, 12),
                "lower_face_ids": [],
                "realizing_object_ids": ["obj_row_" + uid for uid in support],
                "replay_certified": False,
                "cost": {},
                "status": "available",
            }
        )
    status = "resolved" if alternatives else "unresolved"
    return {
        "schema_version": SCHEMA_TOWER_BOUNDARY,
        "upper_face_id": face_id,
        "boundary_alternatives": alternatives,
        "boundary_status": status,
        "canonical_status": "finite_boundary_chart_not_canonical",
    }


def _promotion(face: dict[str, Any], boundary_status: str) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    validation_counts = _validation_counts(face)
    heldout = bool(status.get("heldout_validated") or validation_counts.get("heldout_validated_premise_class"))
    carrier_safe = bool(status.get("carrier_safe"))
    retrieval_allowed = bool(status.get("retrieval_allowed"))
    promotion_level = "dual_exposed"
    if heldout:
        promotion_level = "validated_chart"
    if boundary_status == "resolved" and heldout:
        promotion_level = "boundary_resolved"
    if retrieval_allowed:
        promotion_level = "boundary_resolved"
    return {
        "schema_version": SCHEMA_TOWER_PROMOTION,
        "face_id": face_id,
        "promotion_level": promotion_level,
        "checks": {
            "descended": True,
            "positive": bool((face.get("positive_face") or {}) if isinstance(face.get("positive_face"), dict) else True),
            "non_source_paid": None,
            "dual_supported": True,
            "least_repair": None,
            "boundary_resolved": boundary_status == "resolved",
            "replay_certified": False,
            "carrier_safe": carrier_safe,
            "gamma_stable": None,
            "heldout_validated": heldout,
        },
        "canonical_declared": False,
        "canonical_status": "tower_promotion_ladder_chart_not_canonical",
    }


def _next_actions(face: dict[str, Any], boundary_status: str, *, min_retrieval_support: int) -> list[dict[str, Any]]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    dual_id = str(face.get("dual_component_id") or "")
    status = face.get("status") if isinstance(face.get("status"), dict) else {}
    validation_counts = _validation_counts(face)
    support = len(_support_rows(face))
    out: list[dict[str, Any]] = []

    def add(kind: str, reason: str, priority: float, payload: dict[str, Any] | None = None) -> None:
        out.append(
            {
                "schema_version": SCHEMA_TOWER_NEXT_ACTION,
                "action_id": "tower_next_" + stable_hash({"face": face_id, "kind": kind, "reason": reason, "payload": payload or {}}, 14),
                "action_kind": kind,
                "target_level": _infer_order(face)[0],
                "target_dual_component_id": dual_id,
                "target_face_id": face_id,
                "reason": reason,
                "priority": priority,
                "payload": payload or {},
                "canonical_status": "tower_next_action_chart_not_canonical",
            }
        )

    carrier_status = _carrier_status(face)
    if carrier_status in {"mixed", "unsafe"} or validation_counts.get("carrier_unsafe_mixed_class"):
        add("hard_split_face", "carrier_mixed", 0.95, {"carrier_status": carrier_status})
    if validation_counts.get("split_suggested"):
        add("generate_context", "separator_split", 0.9, {"validation_status_counts": validation_counts})
    if support < min_retrieval_support:
        add("generate_object", "singleton_sparse", 0.75, {"support": support, "min_retrieval_support": min_retrieval_support})
    if boundary_status != "resolved":
        add("resolve_boundary", "missing_lower_face", 0.85)
    blockers = _retrieval_blockers(face)
    if blockers and not status.get("retrieval_allowed"):
        add("block_retrieval", "retrieval_gate_blocked", 0.7, {"retrieval_blockers": blockers})
    if not status.get("heldout_validated") and not validation_counts.get("heldout_validated_premise_class"):
        add("promote_face", "heldout_validation_missing", 0.55)
    if status.get("retrieval_allowed"):
        add("promote_face", "retrieval_ready_boundary_poms_pending", 0.45)
    return out


def _retrieval_candidate(face: dict[str, Any]) -> dict[str, Any]:
    face_id = str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 14))
    support = _support_rows(face)
    dual_id = str(face.get("dual_component_id") or "")
    return {
        "schema_version": SCHEMA_TOWER_RETRIEVAL,
        "retrieval_candidate_id": "tower_retr_" + stable_hash({"face": face_id, "rows": support}, 14),
        "face_id": face_id,
        "dual_component_id": dual_id,
        "candidate_object_ids": ["obj_row_" + uid for uid in support],
        "candidate_row_ids": support,
        "score_proxy": {
            "support": len(support),
            "carrier_safe": ((face.get("status") or {}).get("carrier_safe") if isinstance(face.get("status"), dict) else None),
            "retrieval_allowed": _retrieval_allowed(face),
        },
        "retrieval_status": "face_mediated_candidate",
        "canonical_status": "tower_retrieval_candidate_chart_not_canonical",
    }


def build_canonical_obstruction_tower(
    *,
    out_dir: str | Path,
    fingerprints_path: str | Path | None = None,
    taxonomy_dir: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    concept_lattice_path: str | Path | None = None,
    row_memberships_path: str | Path | None = None,
    retrieval_faces_path: str | Path | None = None,
    repair_faces_path: str | Path | None = None,
    validation_rows_path: str | Path | None = None,
    min_retrieval_support: int = 2,
) -> dict[str, Any]:
    """Build a finite Canonical Obstruction Tower chart.

    This function does not claim canonicality.  It projects the already audited
    bivariate transcript and dual face taxonomy into the tower artifacts needed
    for DOST-style feedback: objects, transcripts, faces, dual components,
    boundaries, promotion ladder, next actions, and face-mediated retrieval.
    """

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    tax_dir = Path(taxonomy_dir) if taxonomy_dir else None
    taxonomy_path = Path(taxonomy_path) if taxonomy_path else (tax_dir / "dual_face_taxonomy.jsonl" if tax_dir else None)
    concept_lattice_path = Path(concept_lattice_path) if concept_lattice_path else (tax_dir / "face_concept_lattice.jsonl" if tax_dir else None)
    row_memberships_path = Path(row_memberships_path) if row_memberships_path else (tax_dir / "row_face_memberships.jsonl" if tax_dir else None)
    retrieval_faces_path = Path(retrieval_faces_path) if retrieval_faces_path else (tax_dir / "retrieval_allowed_faces.jsonl" if tax_dir else None)

    fingerprints = _read_rows(fingerprints_path)
    taxonomy = _read_rows(taxonomy_path)
    concepts = _read_rows(concept_lattice_path)
    memberships = _read_rows(row_memberships_path)
    retrieval_faces = _read_rows(retrieval_faces_path)
    repair_faces = _read_rows(repair_faces_path)
    validation_rows = _read_rows(validation_rows_path)

    objects: list[dict[str, Any]] = []
    transcripts: list[dict[str, Any]] = []
    for row in fingerprints:
        objects.append(_object_from_fingerprint(row))
        transcripts.extend(_transcripts_from_fingerprint(row))
    for face in taxonomy:
        objects.append(_object_from_face(face))

    boundaries = [_boundary(face) for face in taxonomy]
    boundary_by_face = {str(row.get("upper_face_id")): str(row.get("boundary_status") or "unknown") for row in boundaries}
    faces = [_tower_face(face, boundary_by_face.get(str(face.get("taxonomy_face_id")), "unknown")) for face in taxonomy]
    dual_components = [_dual_component(face) for face in taxonomy]
    promotions = [_promotion(face, boundary_by_face.get(str(face.get("taxonomy_face_id")), "unknown")) for face in taxonomy]
    next_actions: list[dict[str, Any]] = []
    for face in taxonomy:
        next_actions.extend(
            _next_actions(
                face,
                boundary_by_face.get(str(face.get("taxonomy_face_id")), "unknown"),
                min_retrieval_support=min_retrieval_support,
            )
        )
    retrieval_candidates = [_retrieval_candidate(face) for face in retrieval_faces]

    write_jsonl(out_path / "tower_objects.jsonl", objects)
    write_jsonl(out_path / "tower_transcripts.jsonl", transcripts)
    write_jsonl(out_path / "tower_faces.jsonl", faces)
    write_jsonl(out_path / "tower_dual_components.jsonl", dual_components)
    write_jsonl(out_path / "tower_boundaries.jsonl", boundaries)
    write_jsonl(out_path / "tower_promotions.jsonl", promotions)
    write_jsonl(out_path / "tower_next_actions.jsonl", next_actions)
    write_jsonl(out_path / "tower_retrieval_candidates.jsonl", retrieval_candidates)

    next_counts = Counter(str(r.get("action_kind")) for r in next_actions)
    reason_counts = Counter(str(r.get("reason")) for r in next_actions)
    level_counts = Counter(str(r.get("level_chart")) for r in faces)
    summary = {
        "schema_version": SCHEMA_TOWER_SUMMARY,
        "out_dir": str(out_path),
        "inputs": {
            "fingerprints": str(fingerprints_path) if fingerprints_path else None,
            "taxonomy_dir": str(taxonomy_dir) if taxonomy_dir else None,
            "taxonomy": str(taxonomy_path) if taxonomy_path else None,
            "concept_lattice": str(concept_lattice_path) if concept_lattice_path else None,
            "row_memberships": str(row_memberships_path) if row_memberships_path else None,
            "retrieval_faces": str(retrieval_faces_path) if retrieval_faces_path else None,
            "repair_faces": str(repair_faces_path) if repair_faces_path else None,
            "validation_rows": str(validation_rows_path) if validation_rows_path else None,
        },
        "n_fingerprints": len(fingerprints),
        "n_concepts": len(concepts),
        "n_memberships": len(memberships),
        "n_source_repair_faces": len(repair_faces),
        "n_validation_rows": len(validation_rows),
        "n_objects": len(objects),
        "n_transcripts": len(transcripts),
        "n_faces": len(faces),
        "n_dual_components": len(dual_components),
        "n_boundaries": len(boundaries),
        "n_promotions": len(promotions),
        "n_next_actions": len(next_actions),
        "n_retrieval_candidates": len(retrieval_candidates),
        "face_level_counts": dict(sorted(level_counts.items())),
        "next_action_counts": dict(sorted(next_counts.items())),
        "next_reason_counts": dict(sorted(reason_counts.items())),
        "artifacts": {
            "tower_objects": str(out_path / "tower_objects.jsonl"),
            "tower_transcripts": str(out_path / "tower_transcripts.jsonl"),
            "tower_faces": str(out_path / "tower_faces.jsonl"),
            "tower_dual_components": str(out_path / "tower_dual_components.jsonl"),
            "tower_boundaries": str(out_path / "tower_boundaries.jsonl"),
            "tower_promotions": str(out_path / "tower_promotions.jsonl"),
            "tower_next_actions": str(out_path / "tower_next_actions.jsonl"),
            "tower_retrieval_candidates": str(out_path / "tower_retrieval_candidates.jsonl"),
        },
        "canonical_status": "canonical_obstruction_tower_is_finite_chart_not_canonical",
    }
    _json_dump(summary, out_path / "tower_summary.json")
    return summary


__all__ = ["build_canonical_obstruction_tower"]
