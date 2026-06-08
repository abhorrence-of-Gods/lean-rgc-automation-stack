from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import math
import re
from collections import defaultdict

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction, ResponseRecord


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) <= 1:
        return 0.0
    m = _mean(xs)
    return float(math.sqrt(sum((x-m)**2 for x in xs) / (len(xs)-1)))


def _l2_std(vs: list[dict[str, float]], keys: list[str]) -> float:
    if len(vs) <= 1 or not keys:
        return 0.0
    arr = np.asarray([[float(v.get(k, 0.0)) for k in keys] for v in vs], dtype=float)
    return float(np.linalg.norm(arr.std(axis=0, ddof=1)))


def _dot_map(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return float(sum(float(v) * float(b.get(k, 0.0)) for k, v in a.items()))


def _norm_map(a: dict[str, float]) -> float:
    return float(math.sqrt(sum(float(v) ** 2 for v in a.values())))


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    na = _norm_map(a); nb = _norm_map(b)
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return _dot_map(a, b) / (na * nb)


def _distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return float(math.sqrt(sum((float(a.get(k, 0.0))-float(b.get(k, 0.0)))**2 for k in keys)))


def _parse_json_or_file(s: str | None) -> dict[str, float]:
    if not s:
        return {}
    p = Path(s)
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
    else:
        data = json.loads(s)
    if isinstance(data, dict) and "normal" in data and isinstance(data["normal"], dict):
        data = data["normal"]
    if isinstance(data, dict) and "response_normal" in data and isinstance(data["response_normal"], dict):
        data = data["response_normal"]
    return {str(k): _safe_float(v) for k, v in (data or {}).items()}


def infer_use_mode(tactic: str) -> str:
    t = (tactic or "").strip()
    if t.startswith("rw"):
        return "rw"
    if t.startswith("simp"):
        return "simp"
    if t.startswith("apply"):
        return "apply"
    if t.startswith("exact"):
        return "exact"
    if t.startswith("have"):
        return "have"
    if "rw [" in t:
        return "rw"
    if "simp [" in t:
        return "simp"
    if "apply " in t:
        return "apply"
    if "exact " in t:
        return "exact"
    return "unknown"


def extract_premise_name(action: dict[str, Any]) -> str:
    meta = action.get("metadata") or {}
    # Existing premise_retrieval action format.
    prem = meta.get("premise")
    if isinstance(prem, dict):
        return str(prem.get("name") or prem.get("doc_id") or "")
    ph = meta.get("premise_hit")
    if isinstance(ph, dict):
        return str(ph.get("name") or ph.get("doc_id") or "")
    extra = meta.get("extra") if isinstance(meta.get("extra"), dict) else {}
    prem2 = extra.get("premise") if isinstance(extra, dict) else None
    if isinstance(prem2, dict):
        return str(prem2.get("name") or prem2.get("doc_id") or "")
    tac = action.get("tactic") or ""
    m = re.search(r"\b(?:rw|simp|apply|exact)\s*\[?\s*([A-Za-z_][A-Za-z0-9_'.]*)", tac)
    if m:
        return m.group(1)
    return str(action.get("action_id") or "unknown_premise")


def premise_use_id(action: dict[str, Any]) -> str:
    prem = extract_premise_name(action)
    mode = infer_use_mode(action.get("tactic", ""))
    meta = action.get("metadata") or {}
    inst = {
        "direction": "reverse" if "←" in (action.get("tactic") or "") else "forward",
        "tactic_class": action.get("tactic_class") or action.get("class") or mode,
    }
    return stable_hash({"premise": prem, "mode": mode, "inst": inst, "tactic": action.get("tactic")}, 16)


def _load_action_map(actions_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not actions_path or not Path(actions_path).exists():
        return {}
    rows = read_jsonl(actions_path)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        aid = str(r.get("action_id") or r.get("id") or stable_hash(r, 14))
        out[aid] = r
    return out


def _load_response_rows(responses_path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for r in read_jsonl(responses_path):
        # Be permissive over slightly different schemas.
        aid = str(r.get("action_id") or r.get("selected_action_id") or "")
        if not aid:
            continue
        resp = r.get("response") or {}
        if not resp and isinstance(r.get("response_flat"), list) and isinstance(r.get("response_keys"), list):
            resp = {str(k): _safe_float(v) for k, v in zip(r.get("response_keys") or [], r.get("response_flat") or [])}
        carrier = r.get("carrier_delta") or {}
        rows.append({**r, "action_id": aid, "response": {str(k): _safe_float(v) for k, v in resp.items()}, "carrier_delta": {str(k): _safe_float(v) for k, v in carrier.items()}})
    return rows


def _row_success(row: dict[str, Any]) -> bool:
    st = str(row.get("audit_status") or row.get("status") or "").lower()
    return st in {"success", "ok", "proved"}


def build_premise_response_registry(*,
    actions_path: str | Path | None,
    responses_path: str | Path,
    out: str | Path,
    summary_out: str | Path | None = None,
    min_count: int = 1,
) -> dict[str, Any]:
    """Aggregate audited premise-use contexts into a response/carrier registry.

    The registry is chart-level: premise names and use modes are metadata; the
    selection primitive is the audited response/carrier embedding.
    """
    action_map = _load_action_map(actions_path)
    resp_rows = _load_response_rows(responses_path)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    action_for_group: dict[str, dict[str, Any]] = {}

    for row in resp_rows:
        aid = row["action_id"]
        action = action_map.get(aid) or {"action_id": aid, "tactic": row.get("tactic", ""), "metadata": row.get("metadata", {}) or {}}
        # Restrict to premise-like actions if action metadata/tags indicate it;
        # if no action file is given, keep all rows as premise-use candidates.
        tags = set(action.get("carrier_tags") or []) | {str(action.get("tactic_class") or "")}
        meta = action.get("metadata") or {}
        looks_premise = bool({"premise", "retrieval", "apply", "rewrite", "simp", "exact"} & tags) or "premise" in meta or "premise_hit" in meta or "premise" in (action.get("tactic") or "")
        if action_map and not looks_premise:
            continue
        uid = premise_use_id(action)
        groups[uid].append(row)
        action_for_group.setdefault(uid, action)

    out_rows: list[dict[str, Any]] = []
    for uid, rows in groups.items():
        if len(rows) < min_count:
            continue
        action = action_for_group[uid]
        resp_keys = sorted(set().union(*(r.get("response", {}).keys() for r in rows)))
        carrier_keys = sorted(set().union(*(r.get("carrier_delta", {}).keys() for r in rows)))
        resp_mean = {k: _mean([_safe_float(r.get("response", {}).get(k)) for r in rows]) for k in resp_keys}
        carrier_mean = {k: _mean([_safe_float(r.get("carrier_delta", {}).get(k)) for r in rows]) for k in carrier_keys}
        success_rate = _mean([1.0 if _row_success(r) else 0.0 for r in rows])
        uidata = {
            "premise_use_id": uid,
            "premise_id": extract_premise_name(action),
            "use_mode": infer_use_mode(action.get("tactic", "")),
            "tactic": action.get("tactic", ""),
            "action_id": action.get("action_id"),
            "representative_action": action,
            "response_embedding": resp_mean,
            "carrier_embedding": carrier_mean,
            "response_keys": resp_keys,
            "carrier_keys": carrier_keys,
            "cost": {
                "cost_estimate": _safe_float(action.get("cost_estimate"), 1.0),
                "import_cost": _safe_float((action.get("metadata") or {}).get("import_cost"), 0.0),
            },
            "audit": {
                "audit_count": len(rows),
                "success_rate": success_rate,
                "statuses": dict(sorted({str(r.get("audit_status") or r.get("status") or "unknown"): sum(1 for rr in rows if str(rr.get("audit_status") or rr.get("status") or "unknown") == str(r.get("audit_status") or r.get("status") or "unknown")) for r in rows}.items())),
            },
            "uncertainty": {
                "response_l2_std": _l2_std([r.get("response", {}) for r in rows], resp_keys),
                "carrier_l2_std": _l2_std([r.get("carrier_delta", {}) for r in rows], carrier_keys),
                "count_uncertainty": 1.0 / math.sqrt(max(1, len(rows))),
            },
            "metadata": {
                "source": "premise_response_registry_v35",
                "premise_source_metadata": (action.get("metadata") or {}).get("premise") or (action.get("metadata") or {}).get("premise_hit") or {},
            },
            "canonical_status": "premise_response_chart_not_canonical_parent_nonpaid_least_repair_required",
        }
        out_rows.append(uidata)
    out_rows.sort(key=lambda r: (-r["audit"]["audit_count"], r["premise_id"], r["use_mode"]))
    write_jsonl(out, out_rows)
    summary = {
        "schema_version": "lean-rgc-premise-response-registry-v35.0",
        "responses": str(responses_path),
        "actions": str(actions_path) if actions_path else None,
        "n_response_rows": len(resp_rows),
        "n_premise_use_rows": len(out_rows),
        "min_count": min_count,
        "canonical_status": "registry_is_finite_premise_response_chart_not_canonical",
    }
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def retrieve_premise_responses(*,
    registry_path: str | Path,
    out: str | Path,
    summary_out: str | Path | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    top_k: int | None = None,
    cost_weight: float = 0.05,
    uncertainty_weight: float = 0.10,
    audit_weight: float = 0.20,
    carrier_safe: bool = False,
    carrier_budget: float = 0.0,
) -> dict[str, Any]:
    rows = read_jsonl(registry_path)
    response_normal = response_normal or {}
    carrier_normal = carrier_normal or {}
    scored: list[dict[str, Any]] = []
    for r in rows:
        resp = {str(k): _safe_float(v) for k, v in (r.get("response_embedding") or {}).items()}
        car = {str(k): _safe_float(v) for k, v in (r.get("carrier_embedding") or {}).items()}
        response_score = _dot_map(response_normal, resp)
        carrier_score = _dot_map(carrier_normal, car)
        violation = sum(max(0.0, -v - carrier_budget) for v in car.values())
        if carrier_safe and violation > 1e-12:
            continue
        uncertainty = _safe_float((r.get("uncertainty") or {}).get("response_l2_std")) + _safe_float((r.get("uncertainty") or {}).get("carrier_l2_std")) + _safe_float((r.get("uncertainty") or {}).get("count_uncertainty"))
        cost = _safe_float((r.get("cost") or {}).get("cost_estimate"), 1.0) + _safe_float((r.get("cost") or {}).get("import_cost"), 0.0)
        audit_risk = 1.0 - _safe_float((r.get("audit") or {}).get("success_rate"), 0.0)
        score = response_score + carrier_score - cost_weight * cost - uncertainty_weight * uncertainty - audit_weight * audit_risk
        d = dict(r)
        d["score"] = float(score)
        d["score_components"] = {
            "response_score": float(response_score),
            "carrier_score": float(carrier_score),
            "carrier_violation": float(violation),
            "cost_penalty": float(cost_weight * cost),
            "uncertainty_penalty": float(uncertainty_weight * uncertainty),
            "audit_penalty": float(audit_weight * audit_risk),
        }
        # Candidate action row for downstream audit.
        action = dict(r.get("representative_action") or {})
        action.setdefault("action_id", r.get("action_id") or stable_hash({"premise_use_id": r.get("premise_use_id")}, 14))
        action.setdefault("tactic", r.get("tactic") or "skip")
        action.setdefault("tactic_class", r.get("use_mode") or "premise")
        action.setdefault("carrier_tags", ["premise_response", r.get("use_mode") or "premise"])
        action.setdefault("metadata", {})
        action["metadata"].update({
            "source": "premise_response_retrieval_v35",
            "premise_use_id": r.get("premise_use_id"),
            "premise_id": r.get("premise_id"),
            "premise_response_score": float(score),
            "score_components": d["score_components"],
            "canonical_status": "premise_retrieval_candidate_not_canonical",
        })
        d["candidate_action"] = action
        scored.append(d)
    scored.sort(key=lambda x: (-x.get("score", 0.0), str(x.get("premise_id")), str(x.get("use_mode"))))
    if top_k is not None and top_k > 0:
        scored = scored[:top_k]
    write_jsonl(out, scored)
    summary = {
        "schema_version": "lean-rgc-premise-response-retrieval-v35.0",
        "registry": str(registry_path),
        "n_selected": len(scored),
        "response_normal_keys": sorted(response_normal.keys()),
        "carrier_normal_keys": sorted(carrier_normal.keys()),
        "canonical_status": "premise_response_retrieval_is_coker_chart_not_canonical",
    }
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def write_premise_retrieved_actions(*, retrieved_path: str | Path, out: str | Path) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in read_jsonl(retrieved_path):
        a = r.get("candidate_action") or r.get("representative_action") or {}
        if not a:
            continue
        aid = str(a.get("action_id") or stable_hash(a, 14))
        if aid in seen:
            continue
        seen.add(aid)
        actions.append(a)
    write_jsonl(out, actions)
    return {"n_actions": len(actions), "out": str(out)}


def mine_premise_quotient(*,
    registry_path: str | Path,
    out_dir: str | Path,
    cosine_threshold: float = 0.95,
    distance_threshold: float = 0.25,
    include_carrier: bool = True,
) -> dict[str, Any]:
    rows = read_jsonl(registry_path)
    vectors: list[dict[str, float]] = []
    for r in rows:
        vec = {"resp::"+str(k): _safe_float(v) for k, v in (r.get("response_embedding") or {}).items()}
        if include_carrier:
            vec.update({"carrier::"+str(k): _safe_float(v) for k, v in (r.get("carrier_embedding") or {}).items()})
        vectors.append(vec)
    n = len(rows)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i+1, n):
            cos = _cosine(vectors[i], vectors[j])
            dist = _distance(vectors[i], vectors[j])
            if cos >= cosine_threshold or dist <= distance_threshold:
                union(i,j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    out_path = Path(out_dir); out_path.mkdir(parents=True, exist_ok=True)
    classes = []
    members = []
    reps = []
    for ci, idxs in enumerate(sorted(groups.values(), key=lambda x: (-len(x), x[0]))):
        rep_idx = idxs[0]
        cid = "qprem_" + stable_hash([rows[i].get("premise_use_id") for i in idxs], 14)
        cl = {
            "class_id": cid,
            "representative_premise_use_id": rows[rep_idx].get("premise_use_id"),
            "representative_action_id": rows[rep_idx].get("action_id"),
            "member_premise_use_ids": [rows[i].get("premise_use_id") for i in idxs],
            "member_action_ids": [rows[i].get("action_id") for i in idxs],
            "n_members": len(idxs),
            "canonical_status": "finite_premise_response_quotient_class_not_canonical",
        }
        classes.append(cl)
        reps.append({**rows[rep_idx], "class_id": cid})
        for i in idxs:
            members.append({"class_id": cid, "premise_use_id": rows[i].get("premise_use_id"), "action_id": rows[i].get("action_id"), "premise_id": rows[i].get("premise_id"), "use_mode": rows[i].get("use_mode")})
    write_jsonl(out_path / "premise_quotient_classes.jsonl", classes)
    write_jsonl(out_path / "premise_quotient_members.jsonl", members)
    write_jsonl(out_path / "premise_quotient_representatives.jsonl", reps)
    summary = {
        "schema_version": "lean-rgc-premise-quotient-v35.0",
        "registry": str(registry_path),
        "n_premise_use_rows": n,
        "n_classes": len(classes),
        "cosine_threshold": cosine_threshold,
        "distance_threshold": distance_threshold,
        "include_carrier": include_carrier,
        "canonical_status": "finite_premise_response_quotient_registry_not_full_operation_stable_congruence",
    }
    (out_path / "premise_quotient_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = [
    "build_premise_response_registry",
    "retrieve_premise_responses",
    "write_premise_retrieved_actions",
    "mine_premise_quotient",
    "infer_use_mode",
    "extract_premise_name",
]
