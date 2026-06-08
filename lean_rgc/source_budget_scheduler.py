from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from .schemas import read_jsonl, write_jsonl, stable_hash
from .active_audit_scheduler import (
    SchedulerConfig,
    load_history_from_db,
    load_history_from_response_files,
    merge_histories,
    schedule_actions,
    _read_json_or_file,
)
from .action_geometry import _effective_gamma_response, _gamma_tail_risk, _dot_by_keys

SCHEMA_VERSION = "lean-rgc-source-budget-scheduler-v46.0"


def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return 1.0 if x else 0.0
        return float(x)
    except Exception:
        return default


def _as_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _action_id(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or row.get("id") or row.get("candidate_id") or row.get("tactic") or stable_hash(row)[:16])


def _task_id(row: dict[str, Any]) -> str:
    meta = _as_dict(row.get("metadata"))
    return str(row.get("task_id") or meta.get("task_id") or "")


def _source_from_row(row: dict[str, Any]) -> str:
    meta = _as_dict(row.get("metadata"))
    return str(
        meta.get("source_budget_source")
        or row.get("source_budget_source")
        or meta.get("source")
        or row.get("source")
        or row.get("tactic_class")
        or "unknown"
    )


def infer_source_id(path: str | Path) -> str:
    p = Path(path)
    parts = [x.lower() for x in p.parts]
    joined = "/".join(parts)
    # Prefer semantically stable source ids over raw filenames.
    patterns = [
        ("carrier_quotient", "carrier_quotient"),
        ("quotient_coordinate", "quotient_coordinate"),
        ("action_geometry", "action_geometry"),
        ("contextual_probe", "contextual_probe"),
        ("contextual", "contextual"),
        ("premise_response", "premise_response"),
        ("premise", "premise"),
        ("qgen_registry", "qgen_registry"),
        ("qgen", "qgen"),
        ("failure_signature", "failure_signature"),
        ("ir", "ir"),
        ("registry", "registry"),
        ("exposure", "exposure"),
    ]
    for needle, sid in patterns:
        if needle in joined:
            return sid
    stem = p.stem.replace("_actions", "").replace("_candidates", "")
    return stem or "unknown"


@dataclass
class CandidateSourceSpec:
    source_id: str
    path: str
    priority: float = 1.0
    min_quota: int = 0
    max_quota: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceBudgetConfig:
    total_budget: int = 64
    min_per_source: int = 0
    max_per_source: int | None = None
    per_task_cap: int | None = None
    per_action_cap: int = 1
    source_exploration_weight: float = 0.25
    source_fairness_power: float = 0.5
    coker_weight: float = 1.0
    carrier_weight: float = 0.5
    uncertainty_weight: float = 0.25
    novelty_weight: float = 0.15
    success_weight: float = 0.25
    cost_weight: float = 0.10
    timeout_weight: float = 0.50
    min_score: float | None = None
    score_metric: str = "score_per_cost"
    # v46: optional Gamma-aware source-budget scoring.  These terms are finite
    # audit charts; they are not canonical propagation operators.
    gamma_aware: bool = False
    gamma_mode: str = "finite_horizon"
    gamma_horizon: int = 4
    gamma_discount: float = 1.0
    gamma_value_weight: float = 0.50
    # Backwards-compatible alias used by earlier experimental v46 drafts.
    gamma_tail_value_weight: float | None = None
    gamma_tail_risk_weight: float = 0.25
    gamma_tail_radius_weight: float = 0.0
    gamma_stability_delta: float = 0.05
    gamma_tail_risk_mode: str = "spectral"
    gamma_prefer_tail_response: bool = False

    def __post_init__(self) -> None:
        if self.gamma_tail_value_weight is not None:
            self.gamma_value_weight = float(self.gamma_tail_value_weight)
        else:
            self.gamma_tail_value_weight = float(self.gamma_value_weight)


def _nested_dicts(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return likely containers for score terms / gamma metadata."""
    out: list[dict[str, Any]] = []
    for obj in [row, _as_dict(row.get("metadata"))]:
        if obj and isinstance(obj, dict):
            out.append(obj)
            for key in [
                "score_terms",
                "action_geometry",
                "active_audit_scheduler",
                "source_budget_scheduler",
                "gamma_transition",
                "gamma",
            ]:
                sub = obj.get(key)
                if isinstance(sub, dict):
                    out.append(sub)
                    st = sub.get("score_terms")
                    if isinstance(st, dict):
                        out.append(st)
    # Preserve order but avoid object-id duplicates.
    seen: set[int] = set()
    uniq: list[dict[str, Any]] = []
    for d in out:
        if id(d) not in seen:
            uniq.append(d); seen.add(id(d))
    return uniq


def _lookup_nested_float(row: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    for d in _nested_dicts(row):
        for k in keys:
            if k in d:
                return _as_float(d.get(k), default)
    return default


def _lookup_nested_bool(row: dict[str, Any], keys: list[str], default: bool = False) -> bool:
    for d in _nested_dicts(row):
        for k in keys:
            if k in d:
                v = d.get(k)
                if isinstance(v, str):
                    return v.lower() in {"1", "true", "yes", "y"}
                return bool(v)
    return default


def gamma_score_terms(row: dict[str, Any], cfg: SourceBudgetConfig) -> dict[str, Any]:
    """Extract v45/v44 Gamma-aware score terms from a candidate action.

    This deliberately accepts several schemas because candidates may come from
    action_geometry retrieval, source-budget re-scheduling, or manually supplied
    gamma transition patches.  Missing gamma metadata yields zero adjustment.
    """
    gamma_aware = _lookup_nested_bool(row, ["gamma_aware", "gamma_aware_retrieval"], False)
    local_response = _lookup_nested_float(row, ["local_response_score"], 0.0)
    tail_response = _lookup_nested_float(row, ["gamma_tail_response_score", "tail_response_score"], local_response)
    value_gain = _lookup_nested_float(row, ["gamma_tail_value_gain", "tail_value_gain"], tail_response - local_response)
    tail_risk = _lookup_nested_float(row, ["tail_risk", "gamma_tail_risk"], 0.0)
    tail_radius = _lookup_nested_float(row, ["tail_radius", "spectral_radius_proxy"], 0.0)
    adjustment = 0.0
    if cfg.gamma_aware:
        adjustment += float(cfg.gamma_tail_value_weight) * value_gain
        adjustment -= float(cfg.gamma_tail_risk_weight) * max(0.0, tail_risk)
        adjustment -= float(cfg.gamma_tail_radius_weight) * max(0.0, tail_radius - 1.0)
    return {
        "gamma_aware_candidate": bool(gamma_aware),
        "gamma_scheduler_enabled": bool(cfg.gamma_aware),
        "local_response_score": float(local_response),
        "gamma_tail_response_score": float(tail_response),
        "gamma_tail_value_gain": float(value_gain),
        "tail_risk": float(tail_risk),
        "tail_radius": float(tail_radius),
        "gamma_score_adjustment": float(adjustment),
        "gamma_tail_value_weight": float(cfg.gamma_tail_value_weight),
        "gamma_tail_risk_weight": float(cfg.gamma_tail_risk_weight),
        "gamma_tail_radius_weight": float(cfg.gamma_tail_radius_weight),
        "canonical_status": "gamma_aware_source_budget_terms_are_finite_chart_not_canonical",
    }


def parse_source_spec(raw: str) -> CandidateSourceSpec:
    # Accepted forms:
    #   path.jsonl
    #   source_id=path.jsonl
    #   source_id@priority=path.jsonl
    left: str | None = None
    path = raw
    if "=" in raw:
        left, path = raw.split("=", 1)
    source_id = infer_source_id(path)
    priority = 1.0
    min_quota = 0
    max_quota: int | None = None
    if left:
        parts = left.split("@")
        source_id = parts[0] or source_id
        for token in parts[1:]:
            if token.startswith("min"):
                min_quota = _as_int(token[3:].lstrip(":"), min_quota)
            elif token.startswith("max"):
                max_quota = _as_int(token[3:].lstrip(":"), 0)
            else:
                priority = _as_float(token, priority)
    return CandidateSourceSpec(source_id=source_id, path=str(path), priority=priority, min_quota=min_quota, max_quota=max_quota)


DEFAULT_CANDIDATE_PATTERNS = [
    "qgen/qgen_context_candidates.jsonl",
    "qgen_context_candidates.jsonl",
    "qgen_registry_candidates.jsonl",
    "action_geometry/action_geometry_candidates.jsonl",
    "action_geometry_candidates.jsonl",
    "quotient_coordinates/quotient_coordinate_selected_actions.jsonl",
    "quotient_coordinates/quotient_coordinate_candidates.jsonl",
    "quotient_coordinate_registry_candidates.jsonl",
    "carrier_quotient/carrier_quotient_candidates.jsonl",
    "carrier_quotient_candidates.jsonl",
    "contextual_probes/contextual_probe_candidates.jsonl",
    "contextual_probe_candidates.jsonl",
    "premise_response_actions.jsonl",
    "premise_response/premise_response_actions.jsonl",
    "premise_candidates.jsonl",
    "registry_candidates.jsonl",
    "failure_signature_candidates.jsonl",
    "ir_candidates.jsonl",
    "exposure_candidates.jsonl",
]


def discover_candidate_sources(run_dir: str | Path, *, patterns: list[str] | None = None) -> list[CandidateSourceSpec]:
    root = Path(run_dir)
    out: list[CandidateSourceSpec] = []
    seen: set[Path] = set()
    for pat in patterns or DEFAULT_CANDIDATE_PATTERNS:
        p = root / pat
        if p.exists() and p.is_file() and p not in seen:
            out.append(CandidateSourceSpec(source_id=infer_source_id(p), path=str(p)))
            seen.add(p)
    # Also discover round-local common candidate files without recursively picking accepted/audit outputs.
    for p in root.glob("**/*candidates.jsonl"):
        rel = str(p.relative_to(root))
        if any(skip in rel for skip in ["audit/", "_audit/", "accepted", "scheduled", "response_quotient"]):
            continue
        if p not in seen:
            out.append(CandidateSourceSpec(source_id=infer_source_id(p), path=str(p)))
            seen.add(p)
    return out


def _load_candidates_from_sources(sources: list[CandidateSourceSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in sources:
        p = Path(spec.path)
        if not p.exists():
            continue
        for row in read_jsonl(p):
            if not isinstance(row, dict):
                continue
            nr = dict(row)
            meta = dict(_as_dict(nr.get("metadata")))
            meta.setdefault("source", spec.source_id)
            meta["source_budget_source"] = spec.source_id
            meta["candidate_source_path"] = str(p)
            meta["source_priority"] = spec.priority
            nr["metadata"] = meta
            nr.setdefault("source_budget_source", spec.source_id)
            key = f"{_task_id(nr)}\u241f{nr.get('tactic') or nr.get('full_tactic') or nr.get('text') or ''}\u241f{_action_id(nr)}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(nr)
    return rows


def _source_limits(sources: list[CandidateSourceSpec], cfg: SourceBudgetConfig) -> dict[str, dict[str, int | float | None]]:
    out: dict[str, dict[str, int | float | None]] = {}
    for spec in sources:
        out[spec.source_id] = {
            "priority": spec.priority,
            "min_quota": max(cfg.min_per_source, spec.min_quota),
            "max_quota": spec.max_quota if spec.max_quota is not None else cfg.max_per_source,
        }
    return out


def _metric(row: dict[str, Any], name: str) -> float:
    if name == "score":
        return _as_float(row.get("score"))
    if name == "score_per_cost":
        return _as_float(row.get("score_per_cost"), _as_float(row.get("score")))
    if name == "response":
        return _as_float(row.get("response_score"))
    return _as_float(row.get(name), _as_float(row.get("score_per_cost"), _as_float(row.get("score"))))



def _extract_response_vector_for_gamma(action: dict[str, Any]) -> tuple[list[str], list[float]]:
    """Return a finite response vector for gamma-aware source budgeting.

    This accepts both Action Geometry rows (response_embedding list + response_keys)
    and generic candidate rows (response_embedding dict).  It is a chart-level
    helper, not a canonical response extractor.
    """
    meta = _as_dict(action.get("metadata"))
    keys = list(action.get("response_keys") or meta.get("response_keys") or [])
    emb = action.get("response_embedding")
    if emb is None and isinstance(meta.get("response_embedding"), (dict, list)):
        emb = meta.get("response_embedding")
    if isinstance(emb, list):
        vals = [_as_float(x) for x in emb]
        if not keys:
            keys = [f"r{i}" for i in range(len(vals))]
        return [str(k) for k in keys], vals
    if isinstance(emb, dict):
        if not keys:
            keys = sorted(str(k) for k in emb.keys())
        vals = [_as_float(emb.get(k, 0.0)) for k in keys]
        return [str(k) for k in keys], vals
    # Fallback: use response or predicted_response maps when present.
    for k in ("response", "predicted_response"):
        obj = action.get(k) if isinstance(action.get(k), dict) else meta.get(k)
        if isinstance(obj, dict):
            keys = sorted(str(x) for x in obj.keys())
            return keys, [_as_float(obj.get(x, 0.0)) for x in keys]
    return [], []


def _apply_gamma_source_budget_adjustment(
    rows: list[dict[str, Any]],
    *,
    response_normal: dict[str, float] | None,
    cfg: SourceBudgetConfig,
) -> dict[str, Any]:
    """Adjust source-budget rows using learned Gamma tail value/risk.

    The input rows are the v36/v37 active-scheduler rows.  We preserve the
    existing source-budget score, then add a chart-level correction:

        Δscore = coker_weight * (tail_response_score - local_response_score)
                 - gamma_tail_risk_weight * TailRisk(Gamma)

    This lets the scheduler allocate audit budget away from locally-attractive
    but tail-unstable candidates.  Missing Gamma information is a zero
    correction.  The output remains a finite audit-budget chart.
    """
    if not getattr(cfg, "gamma_aware", False):
        return {"gamma_aware": False, "n_adjusted": 0}
    n_adjusted = 0
    gains: list[float] = []
    risks: list[float] = []
    rn = response_normal or {}
    for rr in rows:
        action = rr.get("action") or {}
        keys, local_response = _extract_response_vector_for_gamma(action)
        if not keys or not local_response:
            rr.setdefault("score_terms", {})["gamma_aware_source_budget"] = False
            continue
        local_score = _dot_by_keys(rn, local_response, keys) if rn else sum(local_response)
        try:
            tail_vec, gamma_meta = _effective_gamma_response(
                action,
                local_response,
                mode=str(cfg.gamma_mode),
                horizon=int(cfg.gamma_horizon),
                stability_margin=float(cfg.gamma_stability_delta),
            )
        except Exception as e:
            tail_vec, gamma_meta = local_response, {"error": str(e)[:200], "used_gamma": False}
        # Respect discount for finite-horizon scalar/diag charts when requested by
        # falling back to existing metadata if the action-geometry stage already
        # supplied a gamma_tail_value_embedding.
        if isinstance(action.get("gamma_tail_value_embedding"), list):
            tail_vec = [_as_float(x) for x in action.get("gamma_tail_value_embedding")]
            gamma_meta = {**gamma_meta, "used_precomputed_gamma_tail_value_embedding": True}
        tail_score = _dot_by_keys(rn, tail_vec, keys) if rn else sum(_as_float(x) for x in tail_vec)
        try:
            tail_risk, risk_meta = _gamma_tail_risk(
                action,
                rn,
                keys,
                len(local_response),
                mode=str(cfg.gamma_tail_risk_mode),
                stability_margin=float(cfg.gamma_stability_delta),
            )
        except Exception as e:
            tail_risk, risk_meta = 0.0, {"error": str(e)[:200], "gamma_tail_risk_mode": str(cfg.gamma_tail_risk_mode)}
        wv = min(1.0, max(0.0, float(cfg.gamma_value_weight)))
        blended_tail_score = (1.0 - wv) * float(local_score) + wv * float(tail_score)
        value_gain = blended_tail_score - float(local_score)
        score_delta = float(cfg.coker_weight) * value_gain - float(cfg.gamma_tail_risk_weight) * float(tail_risk)
        rr["score"] = _as_float(rr.get("score")) + score_delta
        audit_cost = max(1e-6, _as_float(rr.get("audit_cost"), 1.0))
        rr["score_per_cost"] = rr["score"] / audit_cost
        terms = dict(_as_dict(rr.get("score_terms")))
        terms.update({
            "gamma_aware_source_budget": True,
            "gamma_local_response_score": float(local_score),
            "gamma_tail_response_score": float(tail_score),
            "gamma_blended_tail_response_score": float(blended_tail_score),
            "gamma_tail_value_gain": float(value_gain),
            "gamma_tail_risk": float(tail_risk),
            "gamma_score_delta": float(score_delta),
            "gamma_mode": str(cfg.gamma_mode),
            "gamma_horizon": int(cfg.gamma_horizon),
            "gamma_discount": float(cfg.gamma_discount),
            "gamma_value_weight": float(cfg.gamma_value_weight),
            "gamma_tail_risk_weight": float(cfg.gamma_tail_risk_weight),
            "gamma_tail_risk_mode": str(cfg.gamma_tail_risk_mode),
            "gamma_value_meta": gamma_meta,
            "gamma_risk_meta": risk_meta,
        })
        rr["score_terms"] = terms
        meta = dict(_as_dict(action.get("metadata")))
        sb_meta = dict(_as_dict(meta.get("source_budget_scheduler")))
        sb_meta.update({
            "gamma_aware": True,
            "gamma_score_delta": float(score_delta),
            "gamma_tail_value_gain": float(value_gain),
            "gamma_tail_risk": float(tail_risk),
            "gamma_mode": str(cfg.gamma_mode),
            "gamma_horizon": int(cfg.gamma_horizon),
            "canonical_status": "gamma_aware_source_budget_schedule_chart_not_canonical",
        })
        meta["source_budget_scheduler"] = sb_meta
        action["metadata"] = meta
        rr["action"] = action
        n_adjusted += 1
        gains.append(float(value_gain))
        risks.append(float(tail_risk))
    rows.sort(key=lambda r: (bool(r.get("scheduled", True)), _metric(r, cfg.score_metric), _as_float(r.get("score"))), reverse=True)
    return {
        "gamma_aware": True,
        "n_adjusted": n_adjusted,
        "mean_tail_value_gain": sum(gains) / len(gains) if gains else 0.0,
        "mean_tail_risk": sum(risks) / len(risks) if risks else 0.0,
        "max_tail_risk": max(risks) if risks else 0.0,
        "gamma_mode": str(cfg.gamma_mode),
        "gamma_horizon": int(cfg.gamma_horizon),
        "gamma_value_weight": float(cfg.gamma_value_weight),
        "gamma_tail_risk_weight": float(cfg.gamma_tail_risk_weight),
        "gamma_tail_risk_mode": str(cfg.gamma_tail_risk_mode),
    }

def source_budget_schedule(
    sources: list[CandidateSourceSpec],
    *,
    out_actions: str | Path,
    out_rows: str | Path | None = None,
    out_report: str | Path | None = None,
    db_path: str | Path | None = None,
    response_paths: list[str | Path] | None = None,
    lineage_paths: list[str | Path] | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    config: SourceBudgetConfig | None = None,
) -> dict[str, Any]:
    cfg = config or SourceBudgetConfig()
    candidates = _load_candidates_from_sources(sources)
    history = merge_histories(load_history_from_db(db_path), load_history_from_response_files(response_paths))
    sched_cfg = SchedulerConfig(
        top_k=max(len(candidates), cfg.total_budget),
        per_task_cap=None,
        response_weight=cfg.coker_weight,
        carrier_weight=cfg.carrier_weight,
        success_weight=cfg.success_weight,
        novelty_weight=cfg.novelty_weight,
        uncertainty_weight=cfg.uncertainty_weight,
        lineage_weight=cfg.novelty_weight,
        cost_weight=cfg.cost_weight,
        timeout_weight=cfg.timeout_weight,
        min_score=cfg.min_score,
    )
    rows, score_report = schedule_actions(candidates, history=history, response_normal=response_normal or {}, carrier_normal=carrier_normal or {}, config=sched_cfg)
    # v46: optionally augment scheduler scores by learned Gamma tail-value and
    # tail-risk terms.  This lets the source-level budget allocator distinguish
    # sources whose candidates are locally attractive but propagation-unsafe.
    gamma_summary = _apply_gamma_source_budget_adjustment(rows, response_normal=response_normal or {}, cfg=cfg)
    # Re-index by source preserving scheduler order.
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rr in rows:
        src = _source_from_row(rr.get("action") or rr)
        grouped.setdefault(src, []).append(rr)
        rr["selected"] = False
        rr["source_budget_selected"] = False
    limits = _source_limits(sources, cfg)
    selected_rows: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {sid: 0 for sid in grouped}
    action_counts: dict[str, int] = {}
    task_counts: dict[str, int] = {}

    def can_take(rr: dict[str, Any]) -> bool:
        action = rr.get("action") or {}
        aid = _action_id(action)
        src = _source_from_row(action)
        lim = limits.get(src, {})
        max_q = lim.get("max_quota")
        if max_q is not None and source_counts.get(src, 0) >= int(max_q):
            return False
        if cfg.per_action_cap is not None and action_counts.get(aid, 0) >= cfg.per_action_cap:
            return False
        tid = _task_id(action)
        if cfg.per_task_cap is not None and tid and task_counts.get(tid, 0) >= cfg.per_task_cap:
            return False
        return bool(rr.get("scheduled", True))

    def take(rr: dict[str, Any], reason: str) -> None:
        action = rr.get("action") or {}
        aid = _action_id(action)
        tid = _task_id(action)
        src = _source_from_row(action)
        rr["selected"] = True
        rr["source_budget_selected"] = True
        rr["source_budget_reason"] = reason
        meta = dict(_as_dict(action.get("metadata")))
        meta["source_budget_scheduler"] = {
            "schema_version": SCHEMA_VERSION,
            "source_id": src,
            "selection_reason": reason,
            "source_budget_rank": len(selected_rows) + 1,
            "source_metric": _metric(rr, cfg.score_metric),
            "gamma_aware": bool(cfg.gamma_aware),
            "gamma_score_adjustment": _as_float(rr.get("gamma_score_adjustment"), 0.0),
            "gamma_tail_value_gain": _as_float(rr.get("gamma_tail_value_gain"), 0.0),
            "gamma_tail_risk": _as_float(rr.get("gamma_tail_risk"), 0.0),
            "score_before_gamma": _as_float(rr.get("score_before_gamma"), _as_float(rr.get("score"), 0.0)),
            "canonical_status": "source_budget_schedule_chart_not_canonical",
        }
        action["metadata"] = meta
        selected_rows.append(rr)
        source_counts[src] = source_counts.get(src, 0) + 1
        action_counts[aid] = action_counts.get(aid, 0) + 1
        if tid:
            task_counts[tid] = task_counts.get(tid, 0) + 1

    # First satisfy per-source minima with the best available from each source.
    for sid, lim in limits.items():
        want = int(lim.get("min_quota") or 0)
        if want <= 0:
            continue
        for rr in grouped.get(sid, []):
            if len(selected_rows) >= cfg.total_budget or source_counts.get(sid, 0) >= want:
                break
            if can_take(rr):
                take(rr, "min_quota")

    # Greedy cross-source allocation.  Penalize repeatedly taking from one source.
    while len(selected_rows) < cfg.total_budget:
        best: tuple[float, dict[str, Any]] | None = None
        for sid, g in grouped.items():
            for rr in g:
                if rr.get("source_budget_selected"):
                    continue
                if not can_take(rr):
                    continue
                lim = limits.get(sid, {})
                priority = _as_float(lim.get("priority"), 1.0)
                alloc = source_counts.get(sid, 0)
                fairness = 1.0 / ((1.0 + alloc) ** max(0.0, cfg.source_fairness_power))
                adjusted = priority * (_metric(rr, cfg.score_metric) + cfg.source_exploration_weight * fairness)
                if best is None or adjusted > best[0]:
                    best = (adjusted, rr)
                break
        if best is None:
            break
        take(best[1], "greedy_source_budget")

    selected_actions = [rr["action"] for rr in selected_rows]
    for rr in rows:
        if not rr.get("source_budget_selected") and rr.get("scheduled"):
            rr.setdefault("rejected_reason", "not_in_source_budget")
    write_jsonl(out_actions, selected_actions)
    if out_rows:
        write_jsonl(out_rows, rows)
    source_report: dict[str, Any] = {}
    for sid, g in grouped.items():
        vals = [_metric(rr, cfg.score_metric) for rr in g]
        selected_vals = [_metric(rr, cfg.score_metric) for rr in g if rr.get("source_budget_selected")]
        source_report[sid] = {
            "n_candidates": len(g),
            "n_selected": sum(1 for rr in g if rr.get("source_budget_selected")),
            "top_score": max(vals) if vals else 0.0,
            "mean_score": sum(vals) / len(vals) if vals else 0.0,
            "mean_selected_score": sum(selected_vals) / len(selected_vals) if selected_vals else 0.0,
            "limits": limits.get(sid, {}),
        }
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_sources": len(grouped),
        "n_candidates": len(candidates),
        "n_selected": len(selected_actions),
        "total_budget": cfg.total_budget,
        "source_reports": source_report,
        "selected_action_ids": [_action_id(a) for a in selected_actions],
        "sources": [s.to_dict() for s in sources],
        "score_report": score_report,
        "gamma_aware": bool(cfg.gamma_aware),
        "gamma_summary": gamma_summary,
        "config": asdict(cfg),
        "lineage_inputs": [str(x) for x in (lineage_paths or [])],
        "canonical_status": "source_budget_scheduler_is_audit_budget_chart_not_canonical",
    }
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


def source_budget_schedule_from_files(
    *,
    candidate_specs: list[str] | None = None,
    run_dir: str | Path | None = None,
    out_actions: str | Path,
    out_rows: str | Path | None = None,
    out_report: str | Path | None = None,
    db_path: str | Path | None = None,
    response_paths: list[str | Path] | None = None,
    lineage_paths: list[str | Path] | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    config: SourceBudgetConfig | None = None,
) -> dict[str, Any]:
    sources = [parse_source_spec(x) for x in (candidate_specs or [])]
    if run_dir:
        existing = {str(Path(s.path).resolve()) for s in sources if Path(s.path).exists()}
        for spec in discover_candidate_sources(run_dir):
            rp = str(Path(spec.path).resolve())
            if rp not in existing:
                sources.append(spec)
                existing.add(rp)
    return source_budget_schedule(
        sources,
        out_actions=out_actions,
        out_rows=out_rows,
        out_report=out_report,
        db_path=db_path,
        response_paths=response_paths,
        lineage_paths=lineage_paths,
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        config=config,
    )


__all__ = [
    "SCHEMA_VERSION",
    "CandidateSourceSpec",
    "SourceBudgetConfig",
    "parse_source_spec",
    "discover_candidate_sources",
    "gamma_score_terms",
    "source_budget_schedule",
    "source_budget_schedule_from_files",
]
