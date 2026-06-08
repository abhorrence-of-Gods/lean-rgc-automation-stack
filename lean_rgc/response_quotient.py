from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction


def _dump_json(obj: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _aid(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or row.get("id") or row.get("tactic") or stable_hash(row, n=10))


def _load_actions(path: str | Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).exists():
        return []
    out: list[dict[str, Any]] = []
    for row in read_jsonl(path):
        try:
            out.append(TacticAction.from_dict(row).to_dict())
        except Exception:
            out.append(dict(row))
    return out


def _class_quality(cls: dict[str, Any]) -> float:
    # Higher means more trustworthy as a finite contextual quotient class.
    vals = []
    for k in ("min_member_cosine", "mean_member_cosine"):
        try:
            if cls.get(k) is not None:
                vals.append(float(cls.get(k)))
        except Exception:
            pass
    q = min(vals) if vals else 0.0
    try:
        q -= 0.05 * float(cls.get("max_member_l2") or 0.0)
    except Exception:
        pass
    return float(q)


def build_response_quotient_registry(
    classes_path: str | Path,
    *,
    actions_path: str | Path | None = None,
    out_dir: str | Path,
    min_members: int = 1,
    min_quality: float | None = None,
) -> dict[str, Any]:
    """Build a finite response-congruence quotient registry.

    Input classes are contextual response congruence class rows produced by
    contextual_congruence.py.  The registry is still a finite sampled chart of
    the operation-stable quotient; it is not canonical by itself.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    classes_in = [dict(r) for r in read_jsonl(classes_path)] if Path(classes_path).exists() else []
    actions = _load_actions(actions_path)
    action_by_id = {_aid(a): a for a in actions}

    qclasses: list[dict[str, Any]] = []
    members_rows: list[dict[str, Any]] = []
    rep_actions: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    action_to_class: dict[str, str] = {}
    action_to_rep: dict[str, str] = {}

    for i, c in enumerate(classes_in):
        members = [str(x) for x in (c.get("member_action_ids") or []) if str(x)]
        members = sorted(set(members))
        if len(members) < int(min_members):
            continue
        quality = _class_quality(c)
        if min_quality is not None and quality < float(min_quality):
            continue
        class_id = str(c.get("class_id") or ("rq_" + stable_hash({"members": members, "i": i}, n=12)))
        rep = str(c.get("representative_action_id") or (members[0] if members else ""))
        if not rep and members:
            rep = members[0]
        qrow = {
            "schema_version": "lean-rgc-response-quotient-class-v33.0",
            "quotient_class_id": class_id,
            "representative_action_id": rep,
            "member_action_ids": members,
            "n_members": len(members),
            "source_class_id": c.get("class_id"),
            "mean_fingerprint_norm": c.get("mean_fingerprint_norm"),
            "mean_member_cosine": c.get("mean_member_cosine"),
            "min_member_cosine": c.get("min_member_cosine"),
            "max_member_l2": c.get("max_member_l2"),
            "support_context_count": c.get("support_context_count"),
            "quality_score": quality,
            "mean_fingerprint": c.get("mean_fingerprint") or {},
            "top_loadings": c.get("top_loadings") or [],
            "theory": "finite sampled approximation to Q^R = Act_safe / operation-stable response congruence",
            "canonical_status": "response_quotient_class_candidate_not_canonical_finite_contexts_parent_nonpaid_least_repair_required",
        }
        qclasses.append(qrow)
        for m in members:
            action_to_class[m] = class_id
            action_to_rep[m] = rep
            members_rows.append({
                "schema_version": "lean-rgc-response-quotient-member-v33.0",
                "action_id": m,
                "quotient_class_id": class_id,
                "representative_action_id": rep,
                "is_representative": m == rep,
                "canonical_status": "response_quotient_membership_chart_only_not_canonical",
            })
            projection_rows.append({
                "schema_version": "lean-rgc-response-quotient-projection-v33.0",
                "action_id": m,
                "projected_action_id": rep,
                "quotient_class_id": class_id,
                "projection_kind": "finite_contextual_response_representative",
                "canonical_status": "projection_chart_only_not_canonical",
            })
        if rep:
            base = dict(action_by_id.get(rep) or {"action_id": rep, "tactic": rep, "tactic_class": "response_quotient_representative"})
            meta = dict(base.get("metadata") or {})
            meta.update({
                "source": "response_quotient_representative_v33",
                "quotient_class_id": class_id,
                "member_action_ids": members,
                "finite_contextual_quality_score": quality,
                "canonical_status": qrow["canonical_status"],
            })
            base["metadata"] = meta
            base["action_id"] = f"rqrepr_{rep}_{class_id[-8:]}"
            base.setdefault("tactic_class", "response_quotient_representative")
            rep_actions.append(base)

    # singleton classes for known actions not covered, so downstream projection is total if wanted.
    covered = set(action_to_class)
    singleton_rows: list[dict[str, Any]] = []
    for a in actions:
        aid = _aid(a)
        if aid in covered:
            continue
        cid = "rq_single_" + stable_hash(aid, n=12)
        singleton_rows.append({
            "schema_version": "lean-rgc-response-quotient-class-v33.0",
            "quotient_class_id": cid,
            "representative_action_id": aid,
            "member_action_ids": [aid],
            "n_members": 1,
            "quality_score": 1.0,
            "source_class_id": None,
            "theory": "singleton fallback outside mined finite contextual congruence",
            "canonical_status": "singleton_response_quotient_fallback_chart_only_not_canonical",
        })
        action_to_class[aid] = cid
        action_to_rep[aid] = aid
    # Keep singleton classes in registry but not representatives list (the original action already exists).
    all_classes = qclasses + singleton_rows

    registry = {
        "schema_version": "lean-rgc-response-quotient-registry-v33.0",
        "classes_path": str(classes_path),
        "actions_path": str(actions_path) if actions_path else None,
        "n_source_classes": len(classes_in),
        "n_quotient_classes": len(all_classes),
        "n_nontrivial_classes": sum(1 for c in qclasses if int(c.get("n_members") or 0) > 1),
        "n_singleton_fallback_classes": len(singleton_rows),
        "n_members": len(members_rows),
        "action_to_class": action_to_class,
        "action_to_representative": action_to_rep,
        "files": {
            "classes": str(out / "response_quotient_classes.jsonl"),
            "members": str(out / "response_quotient_members.jsonl"),
            "representatives": str(out / "response_quotient_representatives.jsonl"),
            "projection": str(out / "response_quotient_projection.jsonl"),
        },
        "canonical_status": "finite_response_quotient_registry_not_full_operation_stable_congruence",
    }
    write_jsonl(out / "response_quotient_classes.jsonl", all_classes)
    write_jsonl(out / "response_quotient_members.jsonl", members_rows)
    write_jsonl(out / "response_quotient_representatives.jsonl", rep_actions)
    write_jsonl(out / "response_quotient_projection.jsonl", projection_rows)
    _dump_json(registry, out / "response_quotient_registry.json")
    return registry


def _load_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def project_actions_by_response_quotient(
    actions_path: str | Path,
    registry_path: str | Path,
    out: str | Path,
    *,
    keep_unmapped: bool = True,
    annotate_only: bool = False,
) -> dict[str, Any]:
    """Project an action file to finite response-quotient representatives.

    If annotate_only is false, duplicate members of a mined quotient class are
    collapsed to one representative.  Otherwise all rows are kept with metadata.
    """
    actions = _load_actions(actions_path)
    reg = _load_registry(registry_path)
    amap = {str(k): str(v) for k, v in (reg.get("action_to_representative") or {}).items()}
    cmap = {str(k): str(v) for k, v in (reg.get("action_to_class") or {}).items()}
    out_rows: list[dict[str, Any]] = []
    seen_reps: set[str] = set()
    n_collapsed = 0
    n_unmapped = 0
    for a in actions:
        aid = _aid(a)
        rep = amap.get(aid)
        cid = cmap.get(aid)
        if not rep:
            n_unmapped += 1
            if not keep_unmapped:
                continue
            rep = aid
            cid = None
        row = dict(a)
        meta = dict(row.get("metadata") or {})
        meta.update({
            "response_quotient_class_id": cid,
            "response_quotient_representative_action_id": rep,
            "response_quotient_projected_from_action_id": aid,
            "response_quotient_registry": str(registry_path),
            "canonical_status": "response_quotient_projection_chart_only_not_canonical",
        })
        row["metadata"] = meta
        if annotate_only:
            out_rows.append(row)
            continue
        key = rep
        if key in seen_reps:
            n_collapsed += 1
            continue
        seen_reps.add(key)
        # If the row is not the representative, keep its syntax only if the representative syntax is not available.
        row["action_id"] = f"rqproj_{rep}_{stable_hash({'from': aid, 'class': cid}, n=8)}"
        out_rows.append(row)
    write_jsonl(out, out_rows)
    return {
        "schema_version": "lean-rgc-response-quotient-action-projection-summary-v33.0",
        "actions_path": str(actions_path),
        "registry_path": str(registry_path),
        "out": str(out),
        "n_input_actions": len(actions),
        "n_output_actions": len(out_rows),
        "n_collapsed_duplicates": n_collapsed,
        "n_unmapped": n_unmapped,
        "annotate_only": bool(annotate_only),
        "canonical_status": "action_projection_by_finite_response_quotient_not_canonical",
    }


def response_quotient_from_congruence_dir(
    congruence_dir: str | Path,
    *,
    actions_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    min_members: int = 1,
    min_quality: float | None = None,
) -> dict[str, Any]:
    cdir = Path(congruence_dir)
    classes_path = cdir / "response_congruence_classes.jsonl"
    if not classes_path.exists():
        classes_path = cdir / "contextual_response_congruence_classes.jsonl"
    out = Path(out_dir) if out_dir else cdir / "response_quotient"
    return build_response_quotient_registry(classes_path, actions_path=actions_path, out_dir=out, min_members=min_members, min_quality=min_quality)
