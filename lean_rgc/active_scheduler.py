from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json, math, hashlib

from .schemas import read_jsonl, write_jsonl, TacticAction

SCHEMA_VERSION = "lean-rgc-active-audit-scheduler-v36.0"


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _stable_hash(obj: Any, n: int = 12) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:n]


def _flatten_numbers(obj: Any, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            kk = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten_numbers(v, kk))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = float(obj)
    return out


def _metadata_margin(meta: dict[str, Any]) -> float:
    nums = _flatten_numbers(meta)
    pos = 0.0
    for k, v in nums.items():
        kl = k.lower()
        if any(s in kl for s in ["margin", "surplus", "score", "gain", "response"]):
            if not any(s in kl for s in ["cost", "risk", "penalty", "uncert", "loss", "std", "elapsed"]):
                pos = max(pos, float(v))
    return pos


def _action_source(row: dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return str(meta.get("source") or meta.get("generated_by") or row.get("source") or row.get("tactic_class") or "unknown")


def _load_carrier_normal(x: str | None) -> dict[str, float]:
    if not x:
        return {}
    p = Path(x)
    try:
        if p.exists():
            return {str(k): float(v) for k, v in json.loads(p.read_text(encoding="utf-8")).items()}
    except Exception:
        pass
    try:
        return {str(k): float(v) for k, v in json.loads(x).items()}
    except Exception:
        return {}


@dataclass
class ActionHistory:
    action_id: str
    n: int = 0
    success: int = 0
    timeout: int = 0
    mean_goal_response: float = 0.0
    mean_carrier_delta: float = 0.0
    response_std: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _response_goal_value(row: dict[str, Any]) -> float:
    resp = row.get("response") if isinstance(row.get("response"), dict) else {}
    if resp:
        vals = []
        for k, v in resp.items():
            # Prefer proof-defect response, not carrier-only channels.
            if str(k).startswith("carrier."):
                continue
            vals.append(_as_float(v))
        if vals:
            return float(sum(vals))
    flat = row.get("response_flat") if isinstance(row.get("response_flat"), list) else []
    return float(sum(_as_float(v) for v in flat))


def _response_carrier_value(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") if isinstance(row.get("carrier_delta"), dict) else {}
    return float(sum(_as_float(v) for v in cd.values()))


def build_action_history(responses: list[dict[str, Any]]) -> dict[str, ActionHistory]:
    vals: dict[str, list[float]] = {}
    cvals: dict[str, list[float]] = {}
    status: dict[str, dict[str, int]] = {}
    for r in responses:
        aid = str(r.get("action_id") or (r.get("metadata") or {}).get("action_id") or "")
        if not aid:
            continue
        vals.setdefault(aid, []).append(_response_goal_value(r))
        cvals.setdefault(aid, []).append(_response_carrier_value(r))
        st = str(r.get("audit_status") or r.get("status") or "")
        status.setdefault(aid, {"success": 0, "timeout": 0})
        if st == "success":
            status[aid]["success"] += 1
        if st == "timeout":
            status[aid]["timeout"] += 1
    hist: dict[str, ActionHistory] = {}
    for aid, xs in vals.items():
        n = len(xs)
        mean = sum(xs) / max(1, n)
        var = sum((x - mean) ** 2 for x in xs) / max(1, n - 1) if n > 1 else 0.0
        cs = cvals.get(aid, [])
        hist[aid] = ActionHistory(
            action_id=aid,
            n=n,
            success=status.get(aid, {}).get("success", 0),
            timeout=status.get(aid, {}).get("timeout", 0),
            mean_goal_response=mean,
            mean_carrier_delta=(sum(cs) / max(1, len(cs))) if cs else 0.0,
            response_std=math.sqrt(max(0.0, var)),
        )
    return hist


@dataclass
class SchedulerWeights:
    margin_weight: float = 1.0
    history_weight: float = 0.75
    carrier_weight: float = 0.5
    novelty_weight: float = 0.2
    lineage_novelty_weight: float = 0.05
    uncertainty_weight: float = 0.25
    cost_weight: float = 0.05
    audit_risk_weight: float = 0.1
    timeout_weight: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _carrier_normal_score(row: dict[str, Any], normal: dict[str, float]) -> float:
    if not normal:
        return 0.0
    tags = []
    if isinstance(row.get("carrier_tags"), list):
        tags += [str(x) for x in row.get("carrier_tags")]
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    for key in ["carrier_atom", "carrier_key", "residual_key"]:
        if meta.get(key):
            tags.append(str(meta.get(key)))
    parent = meta.get("parent_residual_keys")
    if isinstance(parent, list):
        tags += [str(x) for x in parent]
    s = 0.0
    for t in set(tags):
        s += normal.get(t, 0.0)
        # Allow prefix/suffix soft matches for mined atoms.
        for k, v in normal.items():
            if k != t and (k in t or t in k):
                s += 0.25 * v
    return float(s)


def score_action(row: dict[str, Any], hist: ActionHistory | None, weights: SchedulerWeights, *, carrier_normal: dict[str, float] | None = None, source_counts: dict[str, int] | None = None) -> dict[str, Any]:
    aid = str(row.get("action_id") or row.get("id") or _stable_hash(row))
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    margin = _metadata_margin(meta) + _metadata_margin(row)
    n = hist.n if hist else 0
    hist_goal = hist.mean_goal_response if hist else 0.0
    hist_carrier = hist.mean_carrier_delta if hist else 0.0
    success_rate = (hist.success / n) if hist and n else 0.0
    timeout_rate = (hist.timeout / n) if hist and n else 0.0
    count_unc = 1.0 / math.sqrt(1.0 + n)
    resp_unc = hist.response_std / math.sqrt(max(1, n)) if hist and n else 0.0
    meta_unc = 0.0
    if isinstance(meta.get("uncertainty"), dict):
        meta_unc = sum(abs(_as_float(v)) for v in _flatten_numbers(meta.get("uncertainty")).values())
    uncertainty = count_unc + resp_unc + meta_unc
    novelty = 1.0 if n == 0 else 1.0 / math.sqrt(1.0 + n)
    source = _action_source(row)
    scount = (source_counts or {}).get(source, 0)
    lineage_novelty = 1.0 / math.sqrt(1.0 + scount)
    cost = _as_float(row.get("cost_estimate", meta.get("cost", meta.get("cost_estimate", 1.0))), 1.0)
    audit_risk = _as_float(meta.get("audit_risk", meta.get("ghost_risk", 0.0)), 0.0)
    carrier_score = hist_carrier + _carrier_normal_score(row, carrier_normal or {})
    score = (
        weights.margin_weight * margin
        + weights.history_weight * hist_goal
        + weights.carrier_weight * carrier_score
        + weights.novelty_weight * novelty
        + weights.lineage_novelty_weight * lineage_novelty
        + 0.1 * success_rate
        - weights.uncertainty_weight * uncertainty
        - weights.cost_weight * cost
        - weights.audit_risk_weight * audit_risk
        - weights.timeout_weight * timeout_rate
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "action_id": aid,
        "task_id": row.get("task_id") or meta.get("task_id"),
        "tactic": row.get("tactic"),
        "source": source,
        "score": float(score),
        "components": {
            "metadata_margin": float(margin),
            "history_goal_response": float(hist_goal),
            "history_carrier_delta": float(hist_carrier),
            "carrier_normal_score": float(_carrier_normal_score(row, carrier_normal or {})),
            "success_rate": float(success_rate),
            "timeout_rate": float(timeout_rate),
            "novelty": float(novelty),
            "lineage_novelty": float(lineage_novelty),
            "uncertainty": float(uncertainty),
            "cost": float(cost),
            "audit_risk": float(audit_risk),
        },
        "history": hist.to_dict() if hist else {"action_id": aid, "n": 0},
        "canonical_status": "active_audit_priority_chart_not_canonical",
        "action": row,
    }


def schedule_actions(
    actions: list[dict[str, Any]],
    responses: list[dict[str, Any]] | None = None,
    *,
    budget: int | None = None,
    per_task: int | None = None,
    min_score: float | None = None,
    weights: SchedulerWeights | None = None,
    carrier_normal: dict[str, float] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    weights = weights or SchedulerWeights()
    hist = build_action_history(responses or [])
    source_counts: dict[str, int] = {}
    for row in actions:
        source_counts[_action_source(row)] = source_counts.get(_action_source(row), 0) + 1
    scored = []
    for row in actions:
        aid = str(row.get("action_id") or row.get("id") or _stable_hash(row))
        scored.append(score_action(row, hist.get(aid), weights, carrier_normal=carrier_normal, source_counts=source_counts))
    scored.sort(key=lambda r: (r["score"], r["components"].get("metadata_margin", 0.0)), reverse=True)
    if min_score is not None:
        scored = [r for r in scored if r["score"] >= min_score]
    selected_records: list[dict[str, Any]] = []
    if per_task and per_task > 0:
        counts: dict[str, int] = {}
        global_count = 0
        for r in scored:
            tid = r.get("task_id") or "__global__"
            cap = per_task
            if tid == "__global__":
                # Keep global actions under the global budget to avoid starving task-specific candidates.
                if budget is not None and global_count >= budget:
                    continue
                global_count += 1
            else:
                if counts.get(tid, 0) >= cap:
                    continue
                counts[tid] = counts.get(tid, 0) + 1
            selected_records.append(r)
            if budget is not None and len(selected_records) >= budget:
                break
    else:
        selected_records = scored[:budget] if budget is not None else scored
    selected_actions = []
    for r in selected_records:
        a = dict(r["action"])
        meta = dict(a.get("metadata") or {})
        meta["active_audit_scheduler"] = {
            "score": r["score"],
            "components": r["components"],
            "source": r.get("source"),
            "schema_version": SCHEMA_VERSION,
            "selected": True,
        }
        a["metadata"] = meta
        selected_actions.append(a)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "n_actions_in": len(actions),
        "n_actions_scored": len(scored),
        "n_actions_selected": len(selected_actions),
        "budget": budget,
        "per_task": per_task,
        "min_score": min_score,
        "weights": weights.to_dict(),
        "canonical_status": "active_audit_schedule_is_cost_aware_chart_not_canonical",
    }
    return selected_actions, scored, summary


def active_audit_schedule_from_files(
    actions_path: str | Path,
    out_actions: str | Path,
    *,
    responses_path: str | Path | None = None,
    out_scores: str | Path | None = None,
    out_report: str | Path | None = None,
    budget: int | None = None,
    per_task: int | None = None,
    min_score: float | None = None,
    carrier_normal_json: str | None = None,
    weights: SchedulerWeights | None = None,
) -> dict[str, Any]:
    actions = read_jsonl(actions_path)
    responses = read_jsonl(responses_path) if responses_path and Path(responses_path).exists() else []
    selected, scores, summary = schedule_actions(
        actions,
        responses,
        budget=budget,
        per_task=per_task,
        min_score=min_score,
        weights=weights,
        carrier_normal=_load_carrier_normal(carrier_normal_json),
    )
    write_jsonl(out_actions, selected)
    if out_scores:
        write_jsonl(out_scores, [{k: v for k, v in r.items() if k != "action"} for r in scores])
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return summary


__all__ = ["SchedulerWeights", "schedule_actions", "active_audit_schedule_from_files", "build_action_history", "score_action"]




# Backward-compatible v36 API.  Newer code uses SchedulerWeights and
# active_audit_schedule_from_files; old tests/scripts used these names.
@dataclass
class AuditScheduleConfig:
    top_k: int = 32
    max_per_task: int | None = None
    min_score: float | None = None
    response_weight: float = 1.0
    carrier_weight: float = 0.5
    novelty_weight: float = 0.25
    uncertainty_weight: float = 0.25
    success_weight: float = 0.25
    cost_weight: float = 0.10
    timeout_weight: float = 0.50

    def to_weights(self) -> SchedulerWeights:
        return SchedulerWeights(
            margin_weight=self.response_weight,
            carrier_weight=self.carrier_weight,
            novelty_weight=self.novelty_weight,
            uncertainty_weight=self.uncertainty_weight,
            history_weight=self.success_weight,
            cost_weight=self.cost_weight,
            timeout_weight=self.timeout_weight,
        )


def schedule_candidates_from_files(
    *,
    candidates_path: str | Path,
    out_actions: str | Path,
    out_report: str | Path | None = None,
    out_scores: str | Path | None = None,
    response_normal: dict[str, float] | str | None = None,
    carrier_normal: dict[str, float] | str | None = None,
    config: AuditScheduleConfig | None = None,
    db_path: str | Path | None = None,
    response_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    # The legacy scheduler did not have a separate response-normal argument;
    # response embeddings are scored through metadata_margin.  Preserve that
    # behavior while accepting the old parameter for CLI compatibility.
    cfg = config or AuditScheduleConfig()
    summary = active_audit_schedule_from_files(
        actions_path=candidates_path,
        out_actions=out_actions,
        responses_path=(response_paths[0] if response_paths else None),
        out_scores=out_scores,
        out_report=out_report,
        budget=cfg.top_k,
        per_task=cfg.max_per_task,
        min_score=cfg.min_score,
        carrier_normal_json=carrier_normal if isinstance(carrier_normal, str) else None,
        weights=cfg.to_weights(),
    )
    # Legacy summary aliases.
    summary.setdefault("n_selected", summary.get("n_actions_selected", 0))
    summary.setdefault("n_candidates", summary.get("n_actions_in", 0))
    return summary


__all__ = [
    "SchedulerWeights", "AuditScheduleConfig", "schedule_actions",
    "active_audit_schedule_from_files", "schedule_candidates_from_files",
    "build_action_history", "score_action",
]
