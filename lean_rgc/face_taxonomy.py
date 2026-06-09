from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json
import math
import re

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_FACE_TAXONOMY = "lean-rgc-dual-face-taxonomy-v52.0"
SCHEMA_FACE_CONCEPT = "lean-rgc-face-concept-lattice-v52.0"
SCHEMA_ROW_FACE_MEMBERSHIP = "lean-rgc-row-face-membership-v52.0"
SCHEMA_NAME_SUGGESTION = "lean-rgc-taxonomy-name-suggestion-v52.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
    except Exception:
        return default
    if math.isnan(v) or math.isinf(v):
        return default
    return v


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _sanitize_token(text: Any, *, max_len: int = 96) -> str:
    s = str(text or "unknown").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_.:/<>=+\-]+", "_", s)
    return s[:max_len] or "unknown"


def _fingerprint_context(key: str) -> str:
    return key.split("::", 1)[0] if "::" in key else "__global__"


def _fingerprint_kind(key: str) -> str:
    parts = key.split("::")
    return parts[1] if len(parts) >= 3 else "metric"


def _fingerprint_metric(key: str) -> str:
    parts = key.split("::")
    return "::".join(parts[2:]) if len(parts) >= 3 else key


def _row_id(row: dict[str, Any]) -> str:
    return str(row.get("premise_use_id") or row.get("premise_use_row_id") or row.get("row_id") or stable_hash(row, 14))


def _carrier_is_safe(row: dict[str, Any], *, threshold: float) -> bool:
    carrier = row.get("carrier_summary") if isinstance(row.get("carrier_summary"), dict) else {}
    audit = row.get("audit_summary") if isinstance(row.get("audit_summary"), dict) else {}
    if _safe_float(audit.get("unsafe")) > threshold:
        return False
    if _safe_float(audit.get("hidden_obligations")) > threshold:
        return False
    return all(_safe_float(v) >= -threshold for v in carrier.values())


def _summary_properties(
    row: dict[str, Any],
    *,
    positive_threshold: float,
    negative_threshold: float,
    carrier_threshold: float,
) -> set[str]:
    props: set[str] = set()
    carrier_safe = _carrier_is_safe(row, threshold=carrier_threshold)
    props.add("carrier::safe" if carrier_safe else "carrier::unsafe")

    for domain in _as_list(row.get("domain_support")):
        props.add("domain::" + _sanitize_token(domain, max_len=128))

    for status, count in (row.get("status_counts") if isinstance(row.get("status_counts"), dict) else {}).items():
        if _safe_float(count) > 0:
            props.add("status::" + _sanitize_token(status))

    summary_specs = [
        ("resp", row.get("response_summary")),
        ("carrier", row.get("carrier_summary")),
        ("gamma", row.get("gamma_summary")),
        ("cost", row.get("cost_summary")),
        ("audit", row.get("audit_summary")),
    ]
    for kind, obj in summary_specs:
        if not isinstance(obj, dict):
            continue
        for metric, raw in obj.items():
            value = _safe_float(raw)
            metric_s = _sanitize_token(metric, max_len=96)
            if value > positive_threshold:
                props.add(f"summary::{kind}_pos::{metric_s}")
            elif value < negative_threshold:
                props.add(f"summary::{kind}_neg::{metric_s}")

    fp = row.get("fingerprint") if isinstance(row.get("fingerprint"), dict) else {}
    for key, raw in fp.items():
        if not isinstance(raw, (int, float)):
            continue
        value = _safe_float(raw)
        if abs(value) <= positive_threshold:
            continue
        key_s = str(key)
        ctx = _sanitize_token(_fingerprint_context(key_s), max_len=128)
        kind = _sanitize_token(_fingerprint_kind(key_s), max_len=32)
        metric = _sanitize_token(_fingerprint_metric(key_s), max_len=96)
        sign = "pos" if value > 0 else "neg"
        props.add(f"{kind}_{sign}::{metric}")
        props.add(f"ctx::{ctx}::{kind}_{sign}::{metric}")

    return props


def _load_fingerprints(path: str | Path) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(path) if isinstance(r, dict)]


def _load_classes(path: str | Path | None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_id: dict[str, dict[str, Any]] = {}
    row_to_class: dict[str, str] = {}
    if not path or not Path(path).exists():
        return by_id, row_to_class
    for row in read_jsonl(path):
        if not isinstance(row, dict):
            continue
        cid = str(row.get("premise_class_id") or row.get("class_id") or stable_hash(row, 12))
        by_id[cid] = row
        for uid in _as_list(row.get("member_premise_use_ids")):
            row_to_class[str(uid)] = cid
    return by_id, row_to_class


def _load_validation(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if isinstance(row, dict):
            cid = str(row.get("premise_class_id") or row.get("class_id") or "")
            if cid:
                out[cid] = row
    return out


def _load_repair_faces(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if isinstance(row, dict):
            cid = str(row.get("source_class_id") or "")
            if cid:
                out[cid] = row
    return out


def _load_generated_feature_values(path: str | Path | None) -> dict[str, dict[str, float]]:
    if not path or not Path(path).exists():
        return {}
    out: dict[str, dict[str, float]] = {}
    for row in read_jsonl(path):
        if not isinstance(row, dict):
            continue
        oid = str(row.get("object_id") or row.get("source_row_id") or row.get("premise_use_id") or "")
        if oid.startswith("obj_row_"):
            oid = oid[len("obj_row_") :]
        features = row.get("generated_features") if isinstance(row.get("generated_features"), dict) else {}
        if oid and features:
            dst = out.setdefault(oid, {})
            for fid, value in features.items():
                dst[str(fid)] = max(dst.get(str(fid), 0.0), abs(_safe_float(value)))
    return out


def _closure(
    seed_extent: frozenset[str],
    row_props: dict[str, set[str]],
) -> tuple[frozenset[str], frozenset[str]]:
    if not seed_extent:
        return frozenset(), frozenset()
    intent: set[str] | None = None
    for uid in seed_extent:
        props = row_props.get(uid, set())
        intent = set(props) if intent is None else intent & props
    intent = intent or set()
    extent = frozenset(uid for uid, props in row_props.items() if intent <= props)
    return extent, frozenset(intent)


def _context_properties(props: set[str]) -> list[str]:
    contexts: set[str] = set()
    for prop in props:
        if prop.startswith("ctx::"):
            parts = prop.split("::")
            if len(parts) >= 3:
                contexts.add(parts[1])
        elif prop.startswith("domain::"):
            contexts.add(prop.split("::", 1)[1])
    return sorted(contexts)


def _measurements(props: set[str]) -> list[str]:
    out: set[str] = set()
    for prop in props:
        head = prop.split("::", 1)[0]
        if "_" in head:
            head = head.split("_", 1)[0]
        if head in {"resp", "carrier", "gamma", "cost", "audit", "summary", "status"}:
            out.add(head)
    return sorted(out)


def _carrier_status_for_extent(
    extent: set[str],
    rows_by_id: dict[str, dict[str, Any]],
    *,
    threshold: float,
) -> str:
    if not extent:
        return "unknown"
    safe = [_carrier_is_safe(rows_by_id[uid], threshold=threshold) for uid in extent if uid in rows_by_id]
    if safe and all(safe):
        return "safe"
    if safe and not any(safe):
        return "unsafe"
    return "mixed"


def _source_classes_for_extent(extent: set[str], row_to_class: dict[str, str]) -> list[str]:
    return sorted({row_to_class[uid] for uid in extent if uid in row_to_class})


def _validation_status_counts(classes: list[str], validations: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for cid in classes:
        status = str((validations.get(cid) or {}).get("validation_status") or "unvalidated")
        counts[status] += 1
    return dict(sorted(counts.items()))


def _dual_source(
    *,
    props: set[str],
    validation_counts: dict[str, int],
    carrier_status: str,
    support: int,
) -> str:
    if carrier_status in {"mixed", "unsafe"} or "carrier::unsafe" in props or validation_counts.get("carrier_unsafe_mixed_class", 0):
        return "carrier_split"
    if validation_counts.get("split_suggested", 0):
        return "separator_split"
    if support <= 1 or validation_counts.get("singleton_vacuously_stable_not_informative", 0):
        return "row_coker"
    if any(p.startswith("gamma_") or p.startswith("summary::gamma") for p in props):
        return "mixed_curvature"
    return "row_coker"


def _human_name(props: set[str], rows: list[dict[str, Any]]) -> tuple[str, float]:
    hay = " ".join(sorted(props))
    hay += " " + " ".join(str(r.get("premise_id") or "") + " " + str(r.get("use_mode") or "") + " " + str(r.get("tactic") or "") for r in rows)
    hay = hay.lower()
    rules = [
        ("reflexive_close_like", ["rfl", "reflexive", "eq_reflexive", "exact_rfl", "eq"]),
        ("normalization_like", ["simp", "simp_all", "normal", "rewrite"]),
        ("arithmetic_close_like", ["norm_num", "omega", "decide", "arith", "nat_arith"]),
        ("structural_decompose_like", ["constructor", "cases", "split", "intro", "forall", "imp"]),
        ("hypothesis_close_like", ["assumption", "close_by_hyp", "hyp"]),
        ("carrier_repair_like", ["carrier", "typeclass", "obligation"]),
    ]
    best_name = "response_face_like"
    best_score = 0
    for name, tokens in rules:
        score = sum(1 for t in tokens if t in hay)
        if score > best_score:
            best_name = name
            best_score = score
    confidence = min(0.95, 0.35 + 0.12 * best_score)
    return best_name, round(confidence, 4)


def _retrieval_allowed(
    *,
    support: int,
    carrier_status: str,
    validation_counts: dict[str, int],
    min_retrieval_support: int,
    allow_singletons: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if support < min_retrieval_support and not (allow_singletons and support == 1):
        reasons.append("support_below_threshold")
    if carrier_status != "safe":
        reasons.append(f"carrier_status_{carrier_status}")
    forbidden = [
        "split_suggested",
        "carrier_unsafe_mixed_class",
        "domain_unstable_class",
        "merge_suggested",
    ]
    for status in forbidden:
        if validation_counts.get(status, 0):
            reasons.append(status)
    if validation_counts and not validation_counts.get("heldout_validated_premise_class", 0):
        if not (allow_singletons and validation_counts.get("singleton_vacuously_stable_not_informative", 0)):
            reasons.append("no_heldout_validated_source_class")
    return not reasons, reasons


def _build_concepts(
    row_props: dict[str, set[str]],
    *,
    min_support: int,
    max_concepts: int,
    max_pair_properties: int,
) -> list[dict[str, Any]]:
    prop_to_rows: dict[str, set[str]] = defaultdict(set)
    for uid, props in row_props.items():
        for prop in props:
            prop_to_rows[prop].add(uid)

    seeds: set[frozenset[str]] = set()
    for rows in prop_to_rows.values():
        if len(rows) >= min_support:
            seeds.add(frozenset(rows))

    frequent = sorted(
        (p for p, rows in prop_to_rows.items() if len(rows) >= min_support),
        key=lambda p: (-len(prop_to_rows[p]), p),
    )[:max_pair_properties]
    for i, p in enumerate(frequent):
        for q in frequent[i + 1 :]:
            extent = prop_to_rows[p] & prop_to_rows[q]
            if len(extent) >= min_support:
                seeds.add(frozenset(extent))

    if row_props:
        seeds.add(frozenset(row_props.keys()))

    closed: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for seed in seeds:
        extent, intent = _closure(seed, row_props)
        if len(extent) < min_support:
            continue
        key = (tuple(sorted(extent)), tuple(sorted(intent)))
        cid = "concept_" + stable_hash({"extent": key[0], "intent": key[1]}, 14)
        closed[key] = {
            "schema_version": SCHEMA_FACE_CONCEPT,
            "concept_id": cid,
            "extent_rows": list(key[0]),
            "intent_properties": list(key[1]),
            "support": len(extent),
            "intent_size": len(intent),
            "concept_status": "finite_formal_concept_chart",
            "canonical_status": "concept_lattice_is_finite_chart_not_canonical",
        }

    concepts = sorted(
        closed.values(),
        key=lambda r: (-int(r["support"]), -int(r["intent_size"]), str(r["concept_id"])),
    )
    return concepts[:max_concepts]


def build_dual_face_taxonomy(
    *,
    fingerprints_path: str | Path,
    out_dir: str | Path,
    classes_path: str | Path | None = None,
    validation_rows_path: str | Path | None = None,
    repair_faces_path: str | Path | None = None,
    generated_features_path: str | Path | None = None,
    min_support: int = 1,
    min_retrieval_support: int = 2,
    positive_threshold: float = 1e-9,
    negative_threshold: float = -1e-9,
    carrier_threshold: float = 1e-12,
    max_concepts: int = 256,
    max_pair_properties: int = 80,
    allow_singleton_retrieval: bool = False,
) -> dict[str, Any]:
    """Build a finite dual-exposed face taxonomy chart from bivariate rows.

    This is not a canonical declaration.  It is a DOST/FCA-style finite chart:
    row-context response properties are closed into a concept lattice; concepts
    are then emitted as positive-face candidates with validation/carrier gates.
    """

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    fingerprints = _load_fingerprints(fingerprints_path)
    rows_by_id = {_row_id(row): row for row in fingerprints}
    classes, row_to_class = _load_classes(classes_path)
    validations = _load_validation(validation_rows_path)
    repair_faces = _load_repair_faces(repair_faces_path)
    generated_features = _load_generated_feature_values(generated_features_path)

    row_props: dict[str, set[str]] = {}
    incidence_rows: list[dict[str, Any]] = []
    for row in fingerprints:
        uid = _row_id(row)
        props = _summary_properties(
            row,
            positive_threshold=positive_threshold,
            negative_threshold=negative_threshold,
            carrier_threshold=carrier_threshold,
        )
        cid = row_to_class.get(uid)
        if cid:
            props.add("source_class::" + _sanitize_token(cid, max_len=80))
            status = (validations.get(cid) or {}).get("validation_status")
            if status:
                props.add("validation::" + _sanitize_token(status))
        for fid, value in sorted((generated_features.get(uid) or {}).items()):
            if abs(_safe_float(value)) > positive_threshold:
                props.add("generated_feature::" + _sanitize_token(fid, max_len=96))
        row_props[uid] = props
        incidence_rows.append(
            {
                "schema_version": SCHEMA_FACE_CONCEPT,
                "premise_use_id": uid,
                "properties": sorted(props),
                "property_count": len(props),
                "source_class_id": cid,
                "canonical_status": "row_property_incidence_is_finite_chart_not_canonical",
            }
        )

    concepts = _build_concepts(
        row_props,
        min_support=max(1, min_support),
        max_concepts=max_concepts,
        max_pair_properties=max_pair_properties,
    )

    taxonomy_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    name_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []

    for concept in concepts:
        extent = set(str(x) for x in concept.get("extent_rows") or [])
        props = set(str(x) for x in concept.get("intent_properties") or [])
        source_classes = _source_classes_for_extent(extent, row_to_class)
        validation_counts = _validation_status_counts(source_classes, validations)
        carrier_status = _carrier_status_for_extent(extent, rows_by_id, threshold=carrier_threshold)
        dual_source = _dual_source(
            props=props,
            validation_counts=validation_counts,
            carrier_status=carrier_status,
            support=len(extent),
        )
        retrieval_allowed, retrieval_blockers = _retrieval_allowed(
            support=len(extent),
            carrier_status=carrier_status,
            validation_counts=validation_counts,
            min_retrieval_support=min_retrieval_support,
            allow_singletons=allow_singleton_retrieval,
        )
        extent_rows = [rows_by_id[uid] for uid in sorted(extent) if uid in rows_by_id]
        human_name, confidence = _human_name(props, extent_rows)
        face_id = "taxface_" + stable_hash(
            {
                "extent": sorted(extent),
                "intent": sorted(props),
                "carrier": carrier_status,
                "dual_source": dual_source,
            },
            14,
        )
        dual_component_id = "xi_" + stable_hash({"face": face_id, "source": dual_source}, 12)
        contexts = _context_properties(props)
        measurements = _measurements(props)
        repair_face_ids = sorted(
            str((repair_faces.get(cid) or {}).get("face_id"))
            for cid in source_classes
            if (repair_faces.get(cid) or {}).get("face_id")
        )
        taxonomy = {
            "schema_version": SCHEMA_FACE_TAXONOMY,
            "taxonomy_face_id": face_id,
            "concept_id": concept.get("concept_id"),
            "generation_source": "finite_incidence_dual_exposed_face_approximation",
            "dual_component_id": dual_component_id,
            "dual_source": dual_source,
            "source_class_ids": source_classes,
            "source_repair_face_ids": repair_face_ids,
            "positive_face": {
                "response_basis": sorted(p for p in props if p.startswith("resp_") or p.startswith("summary::resp")),
                "carrier_basis": sorted(p for p in props if p.startswith("carrier") or p.startswith("summary::carrier")),
                "gamma_basis": sorted(p for p in props if p.startswith("gamma_") or p.startswith("summary::gamma")),
                "domain_basis": sorted(p for p in props if p.startswith("domain::") or p.startswith("ctx::")),
                "audit_basis": sorted(p for p in props if p.startswith("audit_") or p.startswith("summary::audit") or p.startswith("status::")),
                "generated_feature_basis": sorted(p for p in props if p.startswith("generated_feature::")),
            },
            "minimal_support": {
                "rows": sorted(extent),
                "contexts": contexts,
                "measurements": measurements,
            },
            "signatures": {
                "domain_signature": stable_hash(sorted(p for p in props if p.startswith("domain::") or p.startswith("ctx::")), 16),
                "carrier_signature": carrier_status + ":" + stable_hash(sorted(p for p in props if "carrier" in p), 12),
                "tail_signature": stable_hash(sorted(p for p in props if p.startswith("gamma") or "::gamma" in p), 16),
                "closure_signature": stable_hash(sorted(p for p in props if p.startswith("resp") or "::resp" in p or p.startswith("status::")), 16),
            },
            "realizations": {
                "rows": sorted(extent),
                "representatives": [str(r.get("representative_action_id") or r.get("premise_id") or _row_id(r)) for r in extent_rows[:5]],
            },
            "human_name": {
                "suggested": human_name,
                "confidence": confidence,
                "noncanonical": True,
            },
            "status": {
                "finite_chart": True,
                "heldout_validated": bool(validation_counts.get("heldout_validated_premise_class", 0)),
                "carrier_safe": carrier_status == "safe",
                "carrier_status": carrier_status,
                "validation_status_counts": validation_counts,
                "retrieval_allowed": retrieval_allowed,
                "retrieval_blockers": retrieval_blockers,
                "poms_promoted": False,
                "canonical_declared": False,
            },
            "canonical_status": "finite_dual_exposed_face_taxonomy_chart_not_canonical",
        }
        taxonomy_rows.append(taxonomy)
        name_rows.append(
            {
                "schema_version": SCHEMA_NAME_SUGGESTION,
                "taxonomy_face_id": face_id,
                "human_name_suggestion": human_name,
                "confidence": confidence,
                "basis_properties": sorted(list(props))[:32],
                "noncanonical": True,
            }
        )
        if retrieval_allowed:
            retrieval_rows.append(taxonomy)
        for uid in sorted(extent):
            membership_rows.append(
                {
                    "schema_version": SCHEMA_ROW_FACE_MEMBERSHIP,
                    "premise_use_id": uid,
                    "taxonomy_face_id": face_id,
                    "concept_id": concept.get("concept_id"),
                    "membership_kind": "extent_member",
                    "support": len(extent),
                    "intent_size": len(props),
                    "dual_source": dual_source,
                    "retrieval_allowed_face": retrieval_allowed,
                    "canonical_status": "row_face_membership_chart_not_canonical",
                }
            )

    write_jsonl(out_path / "row_property_incidence.jsonl", incidence_rows)
    write_jsonl(out_path / "face_concept_lattice.jsonl", concepts)
    write_jsonl(out_path / "dual_face_taxonomy.jsonl", taxonomy_rows)
    write_jsonl(out_path / "row_face_memberships.jsonl", membership_rows)
    write_jsonl(out_path / "taxonomy_name_suggestions.jsonl", name_rows)
    write_jsonl(out_path / "retrieval_allowed_faces.jsonl", retrieval_rows)

    dual_counts = Counter(str(r.get("dual_source")) for r in taxonomy_rows)
    human_counts = Counter(str((r.get("human_name") or {}).get("suggested")) for r in taxonomy_rows)
    retrieval_blockers = Counter(
        str(reason)
        for row in taxonomy_rows
        for reason in ((row.get("status") or {}).get("retrieval_blockers") or [])
    )
    report = {
        "schema_version": SCHEMA_FACE_TAXONOMY,
        "fingerprints": str(fingerprints_path),
        "classes": str(classes_path) if classes_path else None,
        "validation_rows": str(validation_rows_path) if validation_rows_path else None,
        "repair_faces": str(repair_faces_path) if repair_faces_path else None,
        "generated_features": str(generated_features_path) if generated_features_path else None,
        "out_dir": str(out_path),
        "n_rows": len(fingerprints),
        "n_properties": len({p for props in row_props.values() for p in props}),
        "n_concepts": len(concepts),
        "n_taxonomy_faces": len(taxonomy_rows),
        "n_retrieval_allowed_faces": len(retrieval_rows),
        "dual_source_counts": dict(sorted(dual_counts.items())),
        "human_name_counts": dict(sorted(human_counts.items())),
        "retrieval_blocker_counts": dict(sorted(retrieval_blockers.items())),
        "artifacts": {
            "row_property_incidence": str(out_path / "row_property_incidence.jsonl"),
            "face_concept_lattice": str(out_path / "face_concept_lattice.jsonl"),
            "dual_face_taxonomy": str(out_path / "dual_face_taxonomy.jsonl"),
            "row_face_memberships": str(out_path / "row_face_memberships.jsonl"),
            "taxonomy_name_suggestions": str(out_path / "taxonomy_name_suggestions.jsonl"),
            "retrieval_allowed_faces": str(out_path / "retrieval_allowed_faces.jsonl"),
        },
        "canonical_status": "dual_face_taxonomy_is_finite_chart_not_canonical",
    }
    _json_dump(report, out_path / "dual_face_taxonomy_report.json")
    return report


__all__ = ["build_dual_face_taxonomy"]
