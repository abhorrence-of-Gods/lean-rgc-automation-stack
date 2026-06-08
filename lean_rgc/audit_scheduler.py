from __future__ import annotations

import csv
import json
import math
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from .schemas import read_jsonl, write_jsonl, stable_hash

SCHEMA_VERSION = "lean-rgc-active-audit-scheduler-v36.0"


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return 1.0 if x else 0.0
        return float(x)
    except Exception:
        return default


def _action_id(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or row.get("id") or row.get("candidate_id") or row.get("tactic") or stable_hash(row))


def _task_id(row: dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return str(row.get("task_id") or meta.get("task_id") or "")


def _source(row: dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return str(row.get("source") or meta.get("source") or row.get("tactic_class") or "unknown")


def _tactic(row: dict[str, Any]) -> str:
    return str(row.get("tactic") or row.get("full_tactic") or "")


def _carrier_tags(row: dict[str, Any]) -> list[str]:
    tags = row.get("carrier_tags")
    if isinstance(tags, list):
        return [str(x) for x in tags]
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    tags = meta.get("carrier_tags")
    if isinstance(tags, list):
        return [str(x) for x in tags]
    return []


def _nested_get(row: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for k in keys:
        cur: Any = row
        ok = True
        for part in k.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok:
            return cur
    return default


def _candidate_margin(row: dict[str, Any]) -> float:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    # Many candidate sources already store one of these fields.
    val = _nested_get(row, [
        "robust_margin", "coker_surplus", "normalized_score", "response_score", "score", "margin",
        "metadata.robust_margin", "metadata.coker_surplus", "metadata.response_score", "metadata.score",
        "metadata.score_components.response_score",
    ], None)
    if val is not None:
        return _as_float(val)
    # Fall back to positive hints from quotient/action geometry/premise metadata.
    hints: list[float] = []
    for obj in [row, meta]:
        for key in ["response_embedding", "response", "carrier_embedding", "carrier_delta"]:
            d = obj.get(key) if isinstance(obj, dict) else None
            if isinstance(d, dict):
                hints.extend([_as_float(v) for v in d.values() if _as_float(v) > 0])
    if hints:
        return float(sum(hints) / max(1, len(hints)))
    return 0.0


def _candidate_uncertainty(row: dict[str, Any]) -> float:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    val = _nested_get(row, [
        "uncertainty", "metadata.uncertainty", "metadata.uncertainty.count_uncertainty",
        "metadata.uncertainty.response_l2_std", "metadata.uncertainty.carrier_l2_std",
        "audit_risk", "metadata.audit_risk", "ghost_risk", "metadata.ghost_risk",
    ], None)
    if isinstance(val, dict):
        nums = [_as_float(v) for v in val.values() if isinstance(v, (int, float, str, bool))]
        return float(sum(abs(x) for x in nums)) if nums else 0.0
    return abs(_as_float(val, 0.0))


def _candidate_cost(row: dict[str, Any], history_cost: float | None = None) -> float:
    val = _nested_get(row, ["cost_estimate", "cost", "metadata.cost", "metadata.cost_estimate", "metadata.import_cost"], None)
    base = _as_float(val, 1.0)
    if history_cost is not None and history_cost > 0:
        # Blend author prior and observed audit cost.
        base = 0.5 * base + 0.5 * history_cost
    return max(1e-6, base)


@dataclass
class ActionHistory:
    action_id: str
    n: int = 0
    success_rate: float = 0.0
    mean_goal_response: float = 0.0
    mean_response_norm: float = 0.0
    mean_carrier_delta: float = 0.0
    mean_elapsed_ms: float = 0.0
    timeout_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulerWeights:
    coker_weight: float = 1.0
    carrier_weight: float = 0.5
    novelty_weight: float = 0.25
    uncertainty_weight: float = 0.25
    success_weight: float = 0.25
    cost_weight: float = 0.10
    carrier_violation_weight: float = 0.75
    prior_weight: float = 1.0



def _history_from_rows(rows: list[dict[str, Any]]) -> dict[str, ActionHistory]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        aid = _action_id(r)
        if not aid:
            continue
        buckets.setdefault(aid, []).append(r)
    out: dict[str, ActionHistory] = {}
    for aid, rs in buckets.items():
        n = len(rs)
        succ = 0
        timeout = 0
        goal_vals: list[float] = []
        norms: list[float] = []
        carriers: list[float] = []
        costs: list[float] = []
        for r in rs:
            st = str(r.get("audit_status", r.get("status", ""))).lower()
            if st in {"success", "ok", "proved"}:
                succ += 1
            if st == "timeout":
                timeout += 1
            resp = r.get("response") if isinstance(r.get("response"), dict) else {}
            if not resp and isinstance(r.get("response_keys"), list) and isinstance(r.get("response_flat"), list):
                resp = {str(k): _as_float(v) for k, v in zip(r.get("response_keys"), r.get("response_flat"))}
            goal_vals.append(sum(_as_float(v) for k, v in resp.items() if str(k).startswith("goal.")))
            norms.append(math.sqrt(sum(_as_float(v) ** 2 for v in resp.values())))
            cd = r.get("carrier_delta") if isinstance(r.get("carrier_delta"), dict) else {}
            carriers.append(sum(_as_float(v) for v in cd.values()))
            if r.get("elapsed_ms") is not None:
                costs.append(_as_float(r.get("elapsed_ms")) / 1000.0)
            elif r.get("heartbeats") is not None:
                costs.append(_as_float(r.get("heartbeats")) / 100000.0)
        out[aid] = ActionHistory(
            action_id=aid,
            n=n,
            success_rate=succ / max(1, n),
            mean_goal_response=sum(goal_vals) / max(1, len(goal_vals)),
            mean_response_norm=sum(norms) / max(1, len(norms)),
            mean_carrier_delta=sum(carriers) / max(1, len(carriers)),
            mean_elapsed_ms=1000.0 * (sum(costs) / max(1, len(costs))) if costs else 0.0,
            timeout_rate=timeout / max(1, n),
        )
    return out


def _read_history_from_responses(path: str | Path | None) -> dict[str, ActionHistory]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return _history_from_rows(read_jsonl(p))


def _read_history_from_db(path: str | Path | None) -> dict[str, ActionHistory]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rr.action_id,
                   COUNT(*) AS n,
                   AVG(rr.success) AS success_rate,
                   AVG(CASE WHEN rv.response_key LIKE 'goal.%' THEN rv.value ELSE NULL END) AS mean_goal_response,
                   AVG(CASE WHEN rr.audit_status='timeout' THEN 1.0 ELSE 0.0 END) AS timeout_rate
            FROM response_rows rr
            LEFT JOIN response_values rv ON rr.artifact_id=rv.artifact_id AND rr.row_index=rv.row_index
            GROUP BY rr.action_id
            """
        )
        basic = {str(aid): ActionHistory(action_id=str(aid), n=int(n or 0), success_rate=_as_float(sr), mean_goal_response=_as_float(gr), timeout_rate=_as_float(tr)) for aid, n, sr, gr, tr in cur.fetchall() if aid}
        cur.execute(
            """
            SELECT action_id, AVG(elapsed_ms) FROM audit_rows GROUP BY action_id
            """
        )
        for aid, ms in cur.fetchall():
            if str(aid) in basic:
                basic[str(aid)].mean_elapsed_ms = _as_float(ms)
        cur.execute(
            """
            SELECT action_id, AVG(value) FROM carrier_values GROUP BY action_id
            """
        )
        for aid, val in cur.fetchall():
            if str(aid) in basic:
                basic[str(aid)].mean_carrier_delta = _as_float(val)
        return basic
    finally:
        conn.close()


def _lineage_counts(paths: list[str | Path] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not paths:
        return counts
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        nodes = obj.get("nodes") if isinstance(obj, dict) else None
        if isinstance(nodes, list):
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                aid = str(n.get("action_id") or n.get("id") or "")
                if aid:
                    counts[aid] = counts.get(aid, 0) + 1
    return counts


def score_audit_candidates(
    candidates: list[dict[str, Any]],
    *,
    history: dict[str, ActionHistory] | None = None,
    lineage_counts: dict[str, int] | None = None,
    coker_weight: float = 1.0,
    carrier_weight: float = 0.5,
    uncertainty_weight: float = 0.25,
    novelty_weight: float = 0.15,
    success_weight: float = 0.25,
    cost_weight: float = 0.1,
    timeout_weight: float = 0.5,
    task_diversity_weight: float = 0.05,
) -> list[dict[str, Any]]:
    history = history or {}
    lineage_counts = lineage_counts or {}
    # Source/task rarity supports exploration across generated families.
    source_counts: dict[str, int] = {}
    task_counts: dict[str, int] = {}
    for r in candidates:
        source_counts[_source(r)] = source_counts.get(_source(r), 0) + 1
        tid = _task_id(r)
        if tid:
            task_counts[tid] = task_counts.get(tid, 0) + 1
    rows: list[dict[str, Any]] = []
    for r in candidates:
        row = dict(r)
        aid = _action_id(row)
        hist = history.get(aid)
        coker = _candidate_margin(row)
        carrier = 0.0
        # Positive carrier tags / embeddings indicate potential carrier need payment.
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        for obj in [row, meta]:
            for key in ["carrier_embedding", "carrier_delta", "carrier_response"]:
                d = obj.get(key) if isinstance(obj, dict) else None
                if isinstance(d, dict):
                    carrier += sum(max(0.0, _as_float(v)) for v in d.values())
        carrier += 0.05 * len(_carrier_tags(row))
        uncertainty = _candidate_uncertainty(row)
        cost = _candidate_cost(row, (hist.mean_elapsed_ms / 1000.0) if hist and hist.mean_elapsed_ms else None)
        prior_success = hist.success_rate if hist and hist.n else 0.5
        timeout = hist.timeout_rate if hist and hist.n else 0.0
        # Novelty is high for unseen actions and underrepresented sources/lineage.
        source = _source(row)
        tid = _task_id(row)
        source_n = source_counts.get(source, 1)
        lineage_n = lineage_counts.get(aid, 0)
        seen_n = hist.n if hist else 0
        novelty = 1.0 / math.sqrt(1.0 + seen_n + lineage_n) + 1.0 / math.sqrt(1.0 + source_n)
        if tid:
            novelty += task_diversity_weight / math.sqrt(1.0 + task_counts.get(tid, 1))
        score = (
            coker_weight * coker
            + carrier_weight * carrier
            + uncertainty_weight * uncertainty
            + novelty_weight * novelty
            + success_weight * prior_success
            - cost_weight * cost
            - timeout_weight * timeout
        )
        row.setdefault("metadata", {})
        row["metadata"]["audit_scheduler"] = {
            "schema_version": SCHEMA_VERSION,
            "schedule_score": score,
            "components": {
                "coker_margin_proxy": coker,
                "carrier_need_proxy": carrier,
                "uncertainty_reduction_proxy": uncertainty,
                "lineage_novelty_proxy": novelty,
                "prior_success": prior_success,
                "expected_cost": cost,
                "timeout_rate": timeout,
            },
            "history": hist.to_dict() if hist else None,
            "source_count": source_n,
        }
        row["schedule_score"] = score
        rows.append(row)
    rows.sort(key=lambda x: _as_float(x.get("schedule_score")), reverse=True)
    for i, row in enumerate(rows, 1):
        row["schedule_rank"] = i
        row.setdefault("metadata", {})["audit_scheduler"]["rank"] = i
    return rows


def schedule_audit_candidates(
    candidates_path: str | Path,
    out_actions: str | Path,
    *,
    report_out: str | Path | None = None,
    scored_out: str | Path | None = None,
    responses_path: str | Path | None = None,
    audit_db_path: str | Path | None = None,
    lineage_paths: list[str | Path] | None = None,
    budget: int | None = None,
    per_task_cap: int | None = None,
    per_source_cap: int | None = None,
    coker_weight: float = 1.0,
    carrier_weight: float = 0.5,
    uncertainty_weight: float = 0.25,
    novelty_weight: float = 0.15,
    success_weight: float = 0.25,
    cost_weight: float = 0.1,
    timeout_weight: float = 0.5,
) -> dict[str, Any]:
    candidates = read_jsonl(candidates_path)
    history: dict[str, ActionHistory] = {}
    history.update(_read_history_from_responses(responses_path))
    db_hist = _read_history_from_db(audit_db_path)
    history.update(db_hist)
    lineage_counts = _lineage_counts(lineage_paths)
    scored = score_audit_candidates(
        candidates,
        history=history,
        lineage_counts=lineage_counts,
        coker_weight=coker_weight,
        carrier_weight=carrier_weight,
        uncertainty_weight=uncertainty_weight,
        novelty_weight=novelty_weight,
        success_weight=success_weight,
        cost_weight=cost_weight,
        timeout_weight=timeout_weight,
    )
    if scored_out:
        write_jsonl(scored_out, scored)
    selected: list[dict[str, Any]] = []
    by_task: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for r in scored:
        if budget is not None and len(selected) >= budget:
            break
        tid = _task_id(r)
        src = _source(r)
        if per_task_cap is not None and tid and by_task.get(tid, 0) >= per_task_cap:
            continue
        if per_source_cap is not None and by_source.get(src, 0) >= per_source_cap:
            continue
        selected.append(r)
        if tid:
            by_task[tid] = by_task.get(tid, 0) + 1
        by_source[src] = by_source.get(src, 0) + 1
    write_jsonl(out_actions, selected)
    scores = [_as_float(r.get("schedule_score")) for r in scored]
    report = {
        "schema_version": SCHEMA_VERSION,
        "candidates_path": str(candidates_path),
        "out_actions": str(out_actions),
        "n_candidates": len(candidates),
        "n_scored": len(scored),
        "n_selected": len(selected),
        "budget": budget,
        "per_task_cap": per_task_cap,
        "per_source_cap": per_source_cap,
        "score_summary": {
            "max": max(scores) if scores else 0.0,
            "min": min(scores) if scores else 0.0,
            "mean": sum(scores) / len(scores) if scores else 0.0,
        },
        "selected_sources": by_source,
        "selected_tasks": by_task,
        "weights": {
            "coker_weight": coker_weight,
            "carrier_weight": carrier_weight,
            "uncertainty_weight": uncertainty_weight,
            "novelty_weight": novelty_weight,
            "success_weight": success_weight,
            "cost_weight": cost_weight,
            "timeout_weight": timeout_weight,
        },
        "canonical_status": "active_audit_schedule_chart_not_canonical",
    }
    if report_out:
        Path(report_out).parent.mkdir(parents=True, exist_ok=True)
        Path(report_out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


def write_scheduler_csv(scored_path: str | Path, out_csv: str | Path) -> None:
    rows = read_jsonl(scored_path)
    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["schedule_rank", "action_id", "task_id", "source", "tactic", "schedule_score", "coker_margin_proxy", "carrier_need_proxy", "uncertainty_reduction_proxy", "lineage_novelty_proxy", "prior_success", "expected_cost", "timeout_rate"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            comp = (((r.get("metadata") or {}).get("audit_scheduler") or {}).get("components") or {})
            w.writerow({
                "schedule_rank": r.get("schedule_rank"),
                "action_id": _action_id(r),
                "task_id": _task_id(r),
                "source": _source(r),
                "tactic": _tactic(r),
                "schedule_score": r.get("schedule_score"),
                "coker_margin_proxy": comp.get("coker_margin_proxy"),
                "carrier_need_proxy": comp.get("carrier_need_proxy"),
                "uncertainty_reduction_proxy": comp.get("uncertainty_reduction_proxy"),
                "lineage_novelty_proxy": comp.get("lineage_novelty_proxy"),
                "prior_success": comp.get("prior_success"),
                "expected_cost": comp.get("expected_cost"),
                "timeout_rate": comp.get("timeout_rate"),
            })

# v36 compatibility/high-level wrapper expected by cli.py.
def schedule_candidate_actions(
    *,
    candidates_path: str | Path,
    db_path: str | Path | None = None,
    out_actions: str | Path,
    out_rows: str | Path | None = None,
    out_report: str | Path | None = None,
    top_k: int | None = 32,
    max_per_task: int | None = None,
    min_score: float | None = None,
    weights: SchedulerWeights | None = None,
) -> dict[str, Any]:
    weights = weights or SchedulerWeights()
    return schedule_audit_candidates(
        candidates_path,
        out_actions,
        report_out=out_report,
        scored_out=out_rows,
        audit_db_path=db_path,
        budget=top_k,
        per_task_cap=max_per_task,
        coker_weight=weights.coker_weight,
        carrier_weight=weights.carrier_weight,
        uncertainty_weight=weights.uncertainty_weight,
        novelty_weight=weights.novelty_weight,
        success_weight=weights.success_weight,
        cost_weight=weights.cost_weight,
        timeout_weight=0.5,
    )
