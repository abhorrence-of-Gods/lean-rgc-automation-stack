from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json
import math

import numpy as np

from .schemas import TacticAction, read_jsonl, write_jsonl, stable_hash

IDENTITY_CONTEXT_ID = "__id__"


def _json_dump(obj: Any, path: str | Path) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _load_actions(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    rows = []
    for row in read_jsonl(path):
        try:
            rows.append(TacticAction.from_dict(row).to_dict())
        except Exception:
            rows.append(dict(row))
    return rows


def _identity_action() -> dict[str, Any]:
    return {"action_id": IDENTITY_CONTEXT_ID, "tactic": "", "tactic_class": "identity_context", "carrier_tags": [], "cost_estimate": 0.0, "metadata": {"source": "identity_context"}}


def _aid(a: dict[str, Any] | None) -> str:
    if not a:
        return IDENTITY_CONTEXT_ID
    return str(a.get("action_id") or a.get("id") or IDENTITY_CONTEXT_ID)


def _tactic(a: dict[str, Any] | None) -> str:
    if not a or _aid(a) == IDENTITY_CONTEXT_ID:
        return ""
    return str(a.get("tactic") or "").strip()


def compose_tactics(left: str | None, core: str | None, right: str | None, *, separator: str = "\n") -> str:
    parts = [str(x or "").strip() for x in (left, core, right)]
    parts = [p for p in parts if p]
    if not parts:
        return "skip"
    return "; ".join(parts) if separator == ";" else separator.join(parts)


def make_contextual_actions(
    core_actions: Iterable[dict[str, Any] | TacticAction],
    context_actions: Iterable[dict[str, Any] | TacticAction],
    *,
    include_identity: bool = True,
    max_left: int | None = None,
    max_right: int | None = None,
    max_actions: int | None = None,
    separator: str = "\n",
    source: str = "contextual_response_probe_v31",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cores = [a.to_dict() if isinstance(a, TacticAction) else dict(a) for a in core_actions]
    ctxs = [a.to_dict() if isinstance(a, TacticAction) else dict(a) for a in context_actions]
    if include_identity:
        ctxs = [_identity_action()] + ctxs
    lefts = ctxs[:max_left] if max_left is not None else ctxs
    rights = ctxs[:max_right] if max_right is not None else ctxs
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in cores:
        for l in lefts:
            for r in rights:
                cid, lid, rid = _aid(c), _aid(l), _aid(r)
                tactic = compose_tactics(_tactic(l), _tactic(c), _tactic(r), separator=separator)
                h = stable_hash({"core": cid, "left": lid, "right": rid, "tactic": tactic}, n=12)
                action_id = f"ctx_{cid}_{lid}_{rid}_{h}".replace(" ", "_")
                if action_id in seen:
                    continue
                seen.add(action_id)
                meta = dict(c.get("metadata") or {})
                meta.update({
                    "source": source,
                    "core_action_id": cid,
                    "base_action_id": cid,
                    "left_context_id": lid,
                    "right_context_id": rid,
                    "context_pair": f"{lid}::{rid}",
                    "context_formula": "left; core; right",
                    "context_depth": int(lid != IDENTITY_CONTEXT_ID) + int(rid != IDENTITY_CONTEXT_ID),
                    "canonical_status": "contextual_probe_action_chart_only_not_canonical",
                })
                carrier_tags = sorted(set(list(c.get("carrier_tags") or []) + list(l.get("carrier_tags") or []) + list(r.get("carrier_tags") or [])))
                rows.append({
                    "action_id": action_id,
                    "tactic": tactic,
                    "tactic_class": "contextual_probe",
                    "class": "contextual_probe",
                    "carrier_tags": carrier_tags,
                    "cost_estimate": _safe_float(c.get("cost_estimate"), 1.0) + 0.25 * meta["context_depth"],
                    "metadata": meta,
                })
                if max_actions is not None and len(rows) >= int(max_actions):
                    return rows, _contextual_actions_summary(rows, len(cores), len(lefts), len(rights), True)
    return rows, _contextual_actions_summary(rows, len(cores), len(lefts), len(rights), False)


def _contextual_actions_summary(rows: list[dict[str, Any]], n_core: int, n_left: int, n_right: int, truncated: bool) -> dict[str, Any]:
    return {
        "schema_version": "lean-rgc-contextual-actions-v31.0",
        "n_actions": len(rows),
        "n_core_actions": n_core,
        "n_left_contexts": n_left,
        "n_right_contexts": n_right,
        "truncated": bool(truncated),
        "canonical_status": "contextual_probe_action_chart_only_not_canonical",
    }


@dataclass
class ContextualProbeConfig:
    max_base_actions: int = 64
    max_left_contexts: int = 8
    max_right_contexts: int = 8
    include_identity: bool = True
    include_base_identity_probe: bool = True
    mode: str = "sandwich"


def generate_contextual_probe_actions(actions_path: str | Path, *, out: str | Path, contexts_path: str | Path | None = None, config: ContextualProbeConfig | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = config or ContextualProbeConfig()
    core = _load_actions(actions_path)[: cfg.max_base_actions]
    ctx = _load_actions(contexts_path) if contexts_path else list(core)
    ctx = ctx[: max(cfg.max_left_contexts, cfg.max_right_contexts)]
    rows, summary = make_contextual_actions(core, ctx, include_identity=cfg.include_identity, max_left=cfg.max_left_contexts + int(cfg.include_identity), max_right=cfg.max_right_contexts + int(cfg.include_identity), source="contextual_probe_v31")
    if not cfg.include_base_identity_probe:
        rows = [r for r in rows if (r.get("metadata") or {}).get("context_depth", 0) > 0]
        summary["n_actions"] = len(rows)
    write_jsonl(out, rows)
    summary["out"] = str(out)
    return rows, summary


def generate_contextual_composite_actions(actions_path: str | Path, out: str | Path, *, contexts_path: str | Path | None = None, max_core_actions: int | None = None, max_contexts: int | None = None, include_identity: bool = True, separator: str = "\n", source: str = "contextual_composite_v31") -> dict[str, Any]:
    core = _load_actions(actions_path)
    ctx = _load_actions(contexts_path) if contexts_path else list(core)
    if max_core_actions is not None:
        core = core[:max_core_actions]
    if max_contexts is not None:
        ctx = ctx[:max_contexts]
    rows, summary = make_contextual_actions(core, ctx, include_identity=include_identity, max_left=(max_contexts + int(include_identity)) if max_contexts is not None else None, max_right=(max_contexts + int(include_identity)) if max_contexts is not None else None, separator=separator, source=source)
    write_jsonl(out, rows)
    summary["out"] = str(out)
    return summary


def generate_contextual_candidates(actions_path: str | Path, out: str | Path, *, contexts_path: str | Path | None = None, max_left: int = 8, max_right: int = 8, max_core: int | None = None, max_candidates: int | None = None, include_identity: bool = True, include_left: bool = True, include_right: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    core = _load_actions(actions_path)
    ctx = _load_actions(contexts_path) if contexts_path else list(core)
    if max_core is not None:
        core = core[:max_core]
    # identity occupies one slot if requested
    ml = (max_left + int(include_identity)) if include_left else int(include_identity)
    mr = (max_right + int(include_identity)) if include_right else int(include_identity)
    rows, summary = make_contextual_actions(core, ctx, include_identity=include_identity, max_left=ml, max_right=mr, max_actions=max_candidates, source="contextual_candidates_v31")
    write_jsonl(out, rows)
    summary["out"] = str(out)
    return rows, summary


def _row_response_map(row: dict[str, Any]) -> dict[str, float]:
    if isinstance(row.get("response"), dict):
        return {str(k): _safe_float(v) for k, v in (row.get("response") or {}).items()}
    keys = [str(k) for k in row.get("response_keys") or []]
    vals = row.get("response_flat") or []
    return {k: _safe_float(vals[i]) for i, k in enumerate(keys[: len(vals)])}


def _row_core_context(row: dict[str, Any]) -> tuple[str, str, str]:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    if not meta and isinstance(row.get("metadata"), dict):
        meta = row.get("metadata") or {}
    action_id = str(row.get("action_id") or action.get("action_id") or "unknown")
    core = str(meta.get("core_action_id") or meta.get("base_action_id") or row.get("core_action_id") or action_id)
    left = str(meta.get("left_context_id") or row.get("left_context_id") or IDENTITY_CONTEXT_ID)
    right = str(meta.get("right_context_id") or row.get("right_context_id") or IDENTITY_CONTEXT_ID)
    return core, left, right


def build_contextual_fingerprints(response_rows: Iterable[dict[str, Any]], *, include_state: bool = True, include_carrier: bool = True, min_contexts: int = 1) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = list(response_rows)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        core, _, _ = _row_core_context(row)
        grouped.setdefault(core, []).append(row)
    out: list[dict[str, Any]] = []
    for core, gr in sorted(grouped.items()):
        accum: dict[str, list[float]] = {}
        contexts: set[str] = set()
        action_ids: set[str] = set()
        statuses: dict[str, int] = {}
        for row in gr:
            _core, left, right = _row_core_context(row)
            state = str(row.get("state_id") or row.get("task_id") or "state") if include_state else "state"
            ctx = f"state={state}|L={left}|R={right}"
            contexts.add(ctx)
            action_ids.add(str(row.get("action_id") or ""))
            status = str(row.get("audit_status") or row.get("status") or "unknown")
            statuses[status] = statuses.get(status, 0) + 1
            for k, v in _row_response_map(row).items():
                accum.setdefault(f"resp::{ctx}::{k}", []).append(v)
            if include_carrier:
                for k, v in (row.get("carrier_delta") or {}).items():
                    accum.setdefault(f"carrier::{ctx}::{k}", []).append(_safe_float(v))
        if len(contexts) < min_contexts:
            continue
        fp = {k: float(np.mean(vs)) for k, vs in sorted(accum.items())}
        norm = float(math.sqrt(sum(v*v for v in fp.values())))
        top = sorted(({"key": k, "loading": v, "abs_loading": abs(v)} for k, v in fp.items()), key=lambda x: -x["abs_loading"])[:12]
        out.append({
            "schema_version": "lean-rgc-contextual-fingerprint-v31.0",
            "core_action_id": core,
            "action_ids": sorted([x for x in action_ids if x]),
            "n_rows": len(gr),
            "n_contexts": len(contexts),
            "contexts": sorted(contexts),
            "fingerprint": fp,
            "fingerprint_norm": norm,
            "statuses": statuses,
            "top_loadings": top,
            "canonical_status": "contextual_response_fingerprint_chart_only_not_canonical",
        })
    summary = {"schema_version": "lean-rgc-contextual-fingerprint-summary-v31.0", "n_fingerprints": len(out), "n_input_rows": len(rows), "include_state": include_state, "include_carrier": include_carrier, "min_contexts": min_contexts, "canonical_status": "finite_contextual_response_chart_not_operation_complete"}
    return out, summary


def build_contextual_response_fingerprints(responses_path: str | Path, out: str | Path, *, summary_out: str | Path | None = None, min_audits: int = 1, normalize: bool = True) -> dict[str, Any]:
    fps, summary = build_contextual_fingerprints(read_jsonl(responses_path), min_contexts=max(1, min_audits))
    if normalize:
        for fp in fps:
            d = fp.get("fingerprint") or {}
            n = math.sqrt(sum(float(v) * float(v) for v in d.values()))
            if n > 1e-12:
                fp["fingerprint_norm_before_normalize"] = n
                fp["fingerprint"] = {k: float(v) / n for k, v in d.items()}
                fp["fingerprint_norm"] = 1.0
    write_jsonl(out, fps)
    summary["out"] = str(out)
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def _cosine_dict(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    va = np.asarray([float(a.get(k, 0.0)) for k in keys], dtype=float)
    vb = np.asarray([float(b.get(k, 0.0)) for k in keys], dtype=float)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na <= 1e-12 and nb <= 1e-12:
        return 1.0
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _l2_dict(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return float(math.sqrt(sum((float(a.get(k, 0.0)) - float(b.get(k, 0.0))) ** 2 for k in keys))) if keys else 0.0


def _mean_fp(fps: list[dict[str, float]], weights: list[float] | None = None) -> dict[str, float]:
    keys = sorted(set().union(*(fp.keys() for fp in fps))) if fps else []
    weights = weights or [1.0] * len(fps)
    sw = sum(weights) or 1.0
    return {k: float(sum(float(fp.get(k, 0.0)) * float(w) for fp, w in zip(fps, weights)) / sw) for k in keys}


def mine_response_congruence_classes(fingerprints: Iterable[dict[str, Any]], *, cosine_threshold: float = 0.95, l2_threshold: float | None = None, min_members: int = 1) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fps = list(fingerprints)
    fps.sort(key=lambda r: (-float(r.get("fingerprint_norm") or 0.0), str(r.get("core_action_id") or "")))
    classes: list[dict[str, Any]] = []
    for row in fps:
        fp = {str(k): float(v) for k, v in (row.get("fingerprint") or {}).items()}
        placed = False
        for cls in classes:
            sim = _cosine_dict(fp, cls["mean_fingerprint"])
            dist = _l2_dict(fp, cls["mean_fingerprint"])
            if sim >= cosine_threshold and (l2_threshold is None or dist <= l2_threshold):
                cls["members"].append(row)
                cls["mean_fingerprint"] = _mean_fp([m.get("fingerprint") or {} for m in cls["members"]], [float(m.get("n_rows") or 1.0) for m in cls["members"]])
                placed = True
                break
        if not placed:
            classes.append({"members": [row], "mean_fingerprint": dict(fp)})
    out: list[dict[str, Any]] = []
    for cls in classes:
        members = cls["members"]
        ids = sorted(set(str(m.get("core_action_id") or "") for m in members if m.get("core_action_id")))
        if len(ids) < min_members:
            continue
        mean_fp = cls["mean_fingerprint"]
        sims = [_cosine_dict(m.get("fingerprint") or {}, mean_fp) for m in members]
        dists = [_l2_dict(m.get("fingerprint") or {}, mean_fp) for m in members]
        rep = max(members, key=lambda m: _cosine_dict(m.get("fingerprint") or {}, mean_fp))
        cid = "qact_" + stable_hash({"members": ids, "mean": mean_fp}, n=12)
        top = sorted(({"key": k, "loading": v, "abs_loading": abs(v)} for k, v in mean_fp.items()), key=lambda x: -x["abs_loading"])[:12]
        out.append({
            "schema_version": "lean-rgc-response-congruence-class-v31.0",
            "class_id": cid,
            "representative_action_id": str(rep.get("core_action_id") or ids[0]),
            "member_action_ids": ids,
            "n_members": len(ids),
            "n_fingerprint_rows": len(members),
            "mean_fingerprint": mean_fp,
            "mean_fingerprint_norm": float(math.sqrt(sum(v*v for v in mean_fp.values()))),
            "mean_member_cosine": float(np.mean(sims)) if sims else 0.0,
            "min_member_cosine": float(np.min(sims)) if sims else 0.0,
            "max_member_l2": float(np.max(dists)) if dists else 0.0,
            "support_context_count": len(set().union(*(set(m.get("contexts") or []) for m in members))) if members else 0,
            "top_loadings": top,
            "congruence_rule": {"kind": "finite_contextual_response_fingerprint", "cosine_threshold": cosine_threshold, "l2_threshold": l2_threshold, "theory": "C1~C2 iff R(A C1 B)=R(A C2 B) for all safe A,B; this is a finite sampled approximation."},
            "member_status": "finite_contextual_response_equivalent_candidate",
            "canonical_status": "response_congruence_class_candidate_not_canonical_context_set_finite",
        })
    summary = {"schema_version": "lean-rgc-response-congruence-summary-v31.0", "n_input_fingerprints": len(fps), "n_classes": len(out), "cosine_threshold": cosine_threshold, "l2_threshold": l2_threshold, "min_members": min_members, "canonical_status": "finite_contextual_response_congruence_proxy_not_full_forall_contexts"}
    return out, summary


def mine_action_response_congruence(fingerprints_path: str | Path, out: str | Path, *, summary_out: str | Path | None = None, cosine_threshold: float = 0.95, distance_threshold: float | None = None, min_members: int = 1, out_edges: str | Path | None = None) -> dict[str, Any]:
    fps = read_jsonl(fingerprints_path)
    classes, summary = mine_response_congruence_classes(fps, cosine_threshold=cosine_threshold, l2_threshold=distance_threshold, min_members=min_members)
    write_jsonl(out, classes)
    if out_edges:
        pair_rows = []
        for i, a in enumerate(fps):
            for b in fps[i+1:]:
                pair_rows.append({"action_i": a.get("core_action_id"), "action_j": b.get("core_action_id"), "cosine": _cosine_dict(a.get("fingerprint") or {}, b.get("fingerprint") or {}), "l2": _l2_dict(a.get("fingerprint") or {}, b.get("fingerprint") or {})})
        write_jsonl(out_edges, pair_rows)
    summary["out"] = str(out)
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def mine_contextual_action_quotient(*args, **kwargs):
    return mine_action_response_congruence(*args, **kwargs)


def select_class_representative_actions(classes: Iterable[dict[str, Any]], actions: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    by_id = {str(a.get("action_id") or a.get("id")): dict(a) for a in (actions or [])}
    out = []
    for c in classes:
        rep = str(c.get("representative_action_id") or "")
        if not rep:
            continue
        row = dict(by_id.get(rep) or {"action_id": rep, "tactic": rep, "tactic_class": "contextual_representative"})
        meta = dict(row.get("metadata") or {})
        meta.update({"source": "response_congruence_representative_v31", "class_id": c.get("class_id"), "members": c.get("member_action_ids") or [], "canonical_status": c.get("canonical_status")})
        row["metadata"] = meta
        row["action_id"] = f"repr_{rep}_{str(c.get('class_id'))[-8:]}"
        out.append(row)
    return out


def class_representative_actions(classes: Iterable[dict[str, Any]], actions: Iterable[dict[str, Any]] | None = None, **kwargs) -> list[dict[str, Any]]:
    return select_class_representative_actions(classes, actions)


def action_classes_to_registry(classes_path: str | Path, out: str | Path, *, out_actions: str | Path | None = None) -> dict[str, Any]:
    classes = read_jsonl(classes_path)
    atoms, actions = [], []
    for c in classes:
        cid = str(c.get("class_id") or stable_hash(c))
        members = [str(x) for x in c.get("member_action_ids") or []]
        atom_id = f"response_congruence_{cid}"
        atoms.append({"atom_id": atom_id, "kind": "response_congruence_class", "description": "Finite contextual response congruence class candidate.", "evidence": c, "canonical_status": "response_congruence_registry_readout_not_canonical"})
        rep = str(c.get("representative_action_id") or (members[0] if members else ""))
        if rep:
            actions.append({"action_id": f"congruence_repr_{rep}_{cid[-8:]}", "tactic": rep, "tactic_class": "response_congruence_representative", "carrier_tags": ["response_congruence"], "metadata": {"source": "response_congruence_class_v31", "class_id": cid, "members": members, "atom_id": atom_id}})
    registry = {"schema_version": "lean-rgc-response-congruence-registry-v31.0", "atoms": atoms, "canonical_status": "registry_chart_not_canonical"}
    _json_dump(registry, out)
    if out_actions:
        write_jsonl(out_actions, actions)
    return {"n_atoms": len(atoms), "n_actions": len(actions), "out": str(out), "out_actions": str(out_actions) if out_actions else None}


def contextual_congruence_from_files(
    responses_path: str | Path,
    out_dir: str | Path,
    *,
    actions_path: str | Path | None = None,
    actions: str | Path | None = None,
    include_state: bool = True,
    include_carrier: bool = True,
    cosine_threshold: float = 0.95,
    l2_threshold: float | None = None,
    max_distance: float | None = None,
    distance_threshold: float | None = None,
    min_contexts: int = 1,
    min_audits: int | None = None,
    min_members: int = 1,
    **_ignored: Any,
) -> dict[str, Any]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    if min_audits is not None:
        min_contexts = min_audits
    if l2_threshold is None:
        l2_threshold = distance_threshold if distance_threshold is not None else max_distance
    if actions_path is None and actions is not None:
        actions_path = actions
    rows = read_jsonl(responses_path)
    fps, fp_summary = build_contextual_fingerprints(rows, include_state=include_state, include_carrier=include_carrier, min_contexts=min_contexts)
    classes, cls_summary = mine_response_congruence_classes(fps, cosine_threshold=cosine_threshold, l2_threshold=l2_threshold, min_members=min_members)
    actions_rows = read_jsonl(actions_path) if actions_path and Path(actions_path).exists() else []
    reps = select_class_representative_actions(classes, actions_rows)
    write_jsonl(out / "contextual_fingerprints.jsonl", fps)
    write_jsonl(out / "response_congruence_classes.jsonl", classes)
    write_jsonl(out / "contextual_response_congruence_classes.jsonl", classes)
    write_jsonl(out / "response_congruence_representatives.jsonl", reps)
    report = {"schema_version": "lean-rgc-contextual-congruence-report-v31.0", "responses_path": str(responses_path), "actions_path": str(actions_path) if actions_path else None, "fingerprints": fp_summary, "classes": cls_summary, "n_representative_actions": len(reps), "canonical_status": "finite_contextual_response_congruence_proxy_not_full_operation_stable_quotient", "files": {"fingerprints": str(out / "contextual_fingerprints.jsonl"), "classes": str(out / "response_congruence_classes.jsonl"), "representatives": str(out / "response_congruence_representatives.jsonl")}}
    _json_dump(report, out / "contextual_congruence_report.json")
    _json_dump(report, out / "contextual_response_congruence_report.json")
    return report


def contextual_response_congruence_from_files(responses_path: str | Path, out_dir: str | Path, *, context_mode: str = "state", include_carrier: bool = True, min_count: int = 1, cosine_threshold: float = 0.95, distance_threshold: float | None = 0.25, min_context_jaccard: float = 0.0) -> dict[str, Any]:
    report = contextual_congruence_from_files(responses_path, out_dir, include_state=(context_mode == "state"), include_carrier=include_carrier, min_contexts=min_count, cosine_threshold=cosine_threshold, l2_threshold=distance_threshold)
    report["context_mode"] = context_mode
    report["min_context_jaccard"] = min_context_jaccard
    return report
