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
            return float(x)
        return float(x)
    except Exception:
        return default


def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _flatten_numeric_map(obj: Any, *, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            kk = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (int, float, bool)) and not isinstance(v, bool):
                out[kk] = float(v)
            elif isinstance(v, dict):
                out.update(_flatten_numeric_map(v, prefix=kk))
            elif isinstance(v, list):
                # Lists are intentionally not expanded unless scalar-only and short.
                if len(v) <= 64 and all(isinstance(z, (int, float)) for z in v):
                    for i, z in enumerate(v):
                        out[f"{kk}[{i}]"] = float(z)
    return out


def _read_json_or_file(s: str | None) -> dict[str, float]:
    if not s:
        return {}
    p = Path(s)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        data = json.loads(s)
    if isinstance(data, dict):
        return {str(k): _as_float(v) for k, v in data.items()}
    return {}


def _dot(weights: dict[str, float], values: dict[str, float]) -> float:
    if not weights or not values:
        return 0.0
    if len(weights) <= len(values):
        return sum(w * values.get(k, 0.0) for k, w in weights.items())
    return sum(weights.get(k, 0.0) * v for k, v in values.items())


def _action_id(row: dict[str, Any]) -> str:
    return str(row.get("action_id") or row.get("id") or row.get("tactic") or stable_hash(row)[:12])


def _tactic(row: dict[str, Any]) -> str:
    return str(row.get("tactic") or row.get("text") or row.get("action") or _action_id(row))


def _source(row: dict[str, Any]) -> str:
    meta = _as_dict(row.get("metadata"))
    return str(row.get("source") or meta.get("source") or meta.get("generator") or row.get("tactic_class") or "unknown")


def _cost(row: dict[str, Any], default: float = 1.0) -> float:
    meta = _as_dict(row.get("metadata"))
    for key in ("cost_estimate", "cost", "audit_cost", "import_cost"):
        if key in row:
            return max(1e-6, _as_float(row.get(key), default))
        if key in meta:
            return max(1e-6, _as_float(meta.get(key), default))
    return max(1e-6, default)


@dataclass
class ActionHistoryStats:
    action_id: str
    n_audits: int = 0
    success_count: int = 0
    timeout_count: int = 0
    mean_elapsed_ms: float = 0.0
    mean_response_sum: float = 0.0
    mean_goal_response: float = 0.0
    mean_carrier_delta: float = 0.0
    response_means: dict[str, float] | None = None
    carrier_means: dict[str, float] | None = None

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.n_audits)

    @property
    def timeout_rate(self) -> float:
        return self.timeout_count / max(1, self.n_audits)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        d["timeout_rate"] = self.timeout_rate
        return d


def _history_from_responses(responses: Iterable[dict[str, Any]]) -> dict[str, ActionHistoryStats]:
    tmp: dict[str, dict[str, Any]] = {}
    for row in responses:
        aid = _action_id(row)
        rec = tmp.setdefault(aid, {
            "n": 0, "succ": 0, "timeout": 0, "elapsed": [], "resp_sum": [], "goal": [], "carrier": [], "resp_maps": [], "carrier_maps": []
        })
        rec["n"] += 1
        status = str(row.get("audit_status") or row.get("status") or "")
        if status in {"success", "dry_run"}:
            rec["succ"] += 1
        if status == "timeout":
            rec["timeout"] += 1
        if "elapsed_ms" in row:
            rec["elapsed"].append(_as_float(row.get("elapsed_ms")))
        resp = _flatten_numeric_map(row.get("response") or {})
        if not resp and isinstance(row.get("response_flat"), list):
            keys = row.get("response_keys") or [f"r{i}" for i in range(len(row.get("response_flat") or []))]
            resp = {str(k): _as_float(v) for k, v in zip(keys, row.get("response_flat") or [])}
        carrier = _flatten_numeric_map(row.get("carrier_delta") or {})
        rec["resp_maps"].append(resp)
        rec["carrier_maps"].append(carrier)
        rec["resp_sum"].append(sum(resp.values()))
        rec["goal"].append(sum(v for k, v in resp.items() if str(k).startswith("goal")))
        rec["carrier"].append(sum(carrier.values()))
    out: dict[str, ActionHistoryStats] = {}
    for aid, r in tmp.items():
        def mean(xs):
            return float(sum(xs) / max(1, len(xs))) if xs else 0.0
        keys = sorted({k for m in r["resp_maps"] for k in m})
        ckeys = sorted({k for m in r["carrier_maps"] for k in m})
        out[aid] = ActionHistoryStats(
            action_id=aid,
            n_audits=int(r["n"]),
            success_count=int(r["succ"]),
            timeout_count=int(r["timeout"]),
            mean_elapsed_ms=mean(r["elapsed"]),
            mean_response_sum=mean(r["resp_sum"]),
            mean_goal_response=mean(r["goal"]),
            mean_carrier_delta=mean(r["carrier"]),
            response_means={k: mean([m.get(k, 0.0) for m in r["resp_maps"]]) for k in keys},
            carrier_means={k: mean([m.get(k, 0.0) for m in r["carrier_maps"]]) for k in ckeys},
        )
    return out


def load_history_from_db(db_path: str | Path | None) -> dict[str, ActionHistoryStats]:
    if not db_path:
        return {}
    p = Path(db_path)
    if not p.exists():
        return {}
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        # Build response/carrier maps per response row from long-form tables.
        rows = conn.execute("SELECT artifact_id,row_index,action_id,audit_status AS status,success FROM response_rows").fetchall()
        records: dict[tuple[int, int], dict[str, Any]] = {}
        for rr in rows:
            records[(rr["artifact_id"], rr["row_index"])] = {
                "action_id": rr["action_id"],
                "audit_status": "success" if int(rr["success"] or 0) else (rr["status"] or "fail"),
                "response": {},
                "carrier_delta": {},
            }
        for rv in conn.execute("SELECT artifact_id,row_index,response_key,value FROM response_values"):
            rec = records.get((rv["artifact_id"], rv["row_index"]))
            if rec is not None:
                rec["response"][rv["response_key"]] = _as_float(rv["value"])
        for cv in conn.execute("SELECT artifact_id,row_index,carrier_key,value FROM carrier_values"):
            rec = records.get((cv["artifact_id"], cv["row_index"]))
            if rec is not None:
                rec["carrier_delta"][cv["carrier_key"]] = _as_float(cv["value"])
        return _history_from_responses(records.values())
    finally:
        conn.close()


def load_history_from_response_files(paths: list[str | Path] | None) -> dict[str, ActionHistoryStats]:
    if not paths:
        return {}
    rows: list[dict[str, Any]] = []
    for pp in paths:
        p = Path(pp)
        if p.exists():
            rows.extend(read_jsonl(p))
    return _history_from_responses(rows)


def merge_histories(*histories: dict[str, ActionHistoryStats]) -> dict[str, ActionHistoryStats]:
    # Simple merge by synthetic response rows generated from means and counts.
    rows: list[dict[str, Any]] = []
    for hist in histories:
        for aid, st in hist.items():
            for _ in range(max(1, st.n_audits)):
                rows.append({
                    "action_id": aid,
                    "audit_status": "success" if st.success_rate >= 0.5 else "fail",
                    "response": st.response_means or {},
                    "carrier_delta": st.carrier_means or {},
                })
    return _history_from_responses(rows)


@dataclass
class SchedulerConfig:
    top_k: int = 64
    per_task_cap: int | None = None
    response_weight: float = 1.0
    carrier_weight: float = 0.5
    success_weight: float = 0.2
    novelty_weight: float = 0.2
    uncertainty_weight: float = 0.1
    lineage_weight: float = 0.1
    cost_weight: float = 0.05
    timeout_weight: float = 0.5
    min_score: float | None = None
    default_cost: float = 1.0
    cold_start_bonus: float = 0.15


def _candidate_embeddings(row: dict[str, Any]) -> tuple[dict[str, float], dict[str, float], float]:
    meta = _as_dict(row.get("metadata"))
    resp = {}
    carr = {}
    for key in ("response_embedding", "response", "predicted_response"):
        if isinstance(row.get(key), dict):
            resp.update({str(k): _as_float(v) for k, v in row[key].items()})
        elif isinstance(row.get(key), list):
            keys = list(row.get("response_keys") or meta.get("response_keys") or [f"r{i}" for i in range(len(row.get(key) or []))])
            resp.update({str(k): _as_float(v) for k, v in zip(keys, row.get(key) or [])})
        if isinstance(meta.get(key), dict):
            resp.update({str(k): _as_float(v) for k, v in meta[key].items()})
        elif isinstance(meta.get(key), list):
            keys = list(meta.get("response_keys") or row.get("response_keys") or [f"r{i}" for i in range(len(meta.get(key) or []))])
            resp.update({str(k): _as_float(v) for k, v in zip(keys, meta.get(key) or [])})
    for key in ("carrier_embedding", "carrier_delta", "predicted_carrier"):
        if isinstance(row.get(key), dict):
            carr.update({str(k): _as_float(v) for k, v in row[key].items()})
        if isinstance(meta.get(key), dict):
            carr.update({str(k): _as_float(v) for k, v in meta[key].items()})
    # Some rows have score components from previous stages.
    score_components = _as_dict(meta.get("score_components") or row.get("score_components"))
    prior = 0.0
    for k in ("score", "margin", "robust_margin", "response_score", "coker_surplus"):
        if k in row:
            prior += _as_float(row[k])
        if k in meta:
            prior += _as_float(meta[k])
        if k in score_components:
            prior += _as_float(score_components[k])
    return resp, carr, prior


def schedule_actions(
    candidates: list[dict[str, Any]],
    *,
    history: dict[str, ActionHistoryStats] | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    config: SchedulerConfig | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    history = history or {}
    response_normal = response_normal or {}
    carrier_normal = carrier_normal or {}
    cfg = config or SchedulerConfig()
    seen_sources = {st.action_id for st in history.values() if st.n_audits > 0}
    out_rows: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for row in candidates:
        aid = _action_id(row)
        tac = _tactic(row)
        src = _source(row)
        hist = history.get(aid)
        emb_r, emb_c, prior = _candidate_embeddings(row)
        if hist:
            # Historical means fill missing candidate embeddings.
            for k, v in (hist.response_means or {}).items():
                emb_r.setdefault(k, v)
            for k, v in (hist.carrier_means or {}).items():
                emb_c.setdefault(k, v)
        response_score = _dot(response_normal, emb_r)
        if not response_normal:
            response_score = sum(emb_r.values()) if emb_r else (hist.mean_goal_response if hist else 0.0)
        carrier_score = _dot(carrier_normal, emb_c)
        if not carrier_normal:
            carrier_score = sum(emb_c.values()) if emb_c else (hist.mean_carrier_delta if hist else 0.0)
        n = hist.n_audits if hist else 0
        success_rate = hist.success_rate if hist else 0.0
        timeout_rate = hist.timeout_rate if hist else 0.0
        mean_elapsed = hist.mean_elapsed_ms if hist else 0.0
        uncertainty = 1.0 / math.sqrt(1.0 + n)
        novelty = 1.0 if n == 0 else 0.0
        # Additional novelty for underrepresented candidate sources.
        src_n = source_counts.get(src, 0)
        source_novelty = 1.0 / math.sqrt(1.0 + src_n)
        cost = _cost(row, cfg.default_cost)
        audit_cost = cost + max(0.0, mean_elapsed) / 1000.0
        score = (
            cfg.response_weight * response_score
            + cfg.carrier_weight * carrier_score
            + cfg.success_weight * success_rate
            + cfg.novelty_weight * novelty
            + cfg.lineage_weight * source_novelty
            + cfg.cold_start_bonus * (1.0 if n == 0 else 0.0)
            - cfg.uncertainty_weight * uncertainty
            - cfg.cost_weight * audit_cost
            - cfg.timeout_weight * timeout_rate
            + prior
        )
        score_per_cost = score / max(1e-6, audit_cost)
        scheduled = True
        if cfg.min_score is not None and score < cfg.min_score:
            scheduled = False
        meta = dict(_as_dict(row.get("metadata")))
        meta.setdefault("active_audit_scheduler", {})
        meta["active_audit_scheduler"].update({
            "schema_version": SCHEMA_VERSION,
            "score": score,
            "score_per_cost": score_per_cost,
            "response_score": response_score,
            "carrier_score": carrier_score,
            "success_rate": success_rate,
            "timeout_rate": timeout_rate,
            "uncertainty": uncertainty,
            "novelty": novelty,
            "source_novelty": source_novelty,
            "audit_cost": audit_cost,
            "history_count": n,
        })
        new_row = dict(row)
        new_row.setdefault("action_id", aid)
        new_row.setdefault("tactic", tac)
        new_row["metadata"] = meta
        out_rows.append({
            "action_id": aid,
            "tactic": tac,
            "source": src,
            "scheduled": scheduled,
            "score": score,
            "score_per_cost": score_per_cost,
            "response_score": response_score,
            "carrier_score": carrier_score,
            "success_rate": success_rate,
            "timeout_rate": timeout_rate,
            "uncertainty": uncertainty,
            "novelty": novelty,
            "source_novelty": source_novelty,
            "audit_cost": audit_cost,
            "history_count": n,
            "canonical_status": "active_audit_schedule_chart_not_canonical",
            "action": new_row,
        })
        source_counts[src] = source_counts.get(src, 0) + 1
    # Sort by score-per-cost, then raw score.
    out_rows.sort(key=lambda r: (r["scheduled"], r["score_per_cost"], r["score"]), reverse=True)
    selected: list[dict[str, Any]] = []
    per_task: dict[str, int] = {}
    for rr in out_rows:
        if not rr.get("scheduled"):
            continue
        action = rr["action"]
        task_id = str(action.get("task_id") or _as_dict(action.get("metadata")).get("task_id") or "")
        if cfg.per_task_cap is not None and task_id:
            if per_task.get(task_id, 0) >= cfg.per_task_cap:
                rr["scheduled"] = False
                rr["rejected_reason"] = "per_task_cap"
                continue
            per_task[task_id] = per_task.get(task_id, 0) + 1
        selected.append(action)
        if cfg.top_k and len(selected) >= cfg.top_k:
            break
    selected_ids = {_action_id(a) for a in selected}
    for rr in out_rows:
        rr["selected"] = rr["action_id"] in selected_ids
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_candidates": len(candidates),
        "n_selected": len(selected),
        "top_k": cfg.top_k,
        "score_weights": {
            "response_weight": cfg.response_weight,
            "carrier_weight": cfg.carrier_weight,
            "success_weight": cfg.success_weight,
            "novelty_weight": cfg.novelty_weight,
            "uncertainty_weight": cfg.uncertainty_weight,
            "lineage_weight": cfg.lineage_weight,
            "cost_weight": cfg.cost_weight,
            "timeout_weight": cfg.timeout_weight,
        },
        "response_normal_keys": sorted(response_normal.keys()),
        "carrier_normal_keys": sorted(carrier_normal.keys()),
        "selected_action_ids": [_action_id(a) for a in selected],
        "canonical_status": "active_audit_scheduler_is_candidate_selection_chart_not_canonical",
    }
    return out_rows, report


def active_audit_schedule_from_files(
    *,
    candidates_path: str | Path,
    out_actions: str | Path,
    out_rows: str | Path | None = None,
    out_report: str | Path | None = None,
    db_path: str | Path | None = None,
    response_paths: list[str | Path] | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    config: SchedulerConfig | None = None,
) -> dict[str, Any]:
    candidates = read_jsonl(candidates_path)
    history = merge_histories(load_history_from_db(db_path), load_history_from_response_files(response_paths))
    rows, report = schedule_actions(candidates, history=history, response_normal=response_normal, carrier_normal=carrier_normal, config=config)
    selected = [r["action"] for r in rows if r.get("selected")]
    write_jsonl(out_actions, selected)
    if out_rows:
        write_jsonl(out_rows, rows)
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def write_rows_csv(rows_path: str | Path, csv_path: str | Path) -> None:
    rows = read_jsonl(rows_path)
    fieldnames = [
        "selected", "scheduled", "action_id", "source", "score", "score_per_cost",
        "response_score", "carrier_score", "success_rate", "timeout_rate", "uncertainty",
        "novelty", "source_novelty", "audit_cost", "history_count",
    ]
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(csv_path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


# v36 compatibility wrapper used by the CLI.  This supports multiple candidate
# sources and keeps the older single-file helper above intact.
def _parse_json_or_file(s: str | None) -> dict[str, float]:
    return _read_json_or_file(s)


def schedule_active_audits_from_files(
    candidate_paths: list[str | Path],
    out_actions: str | Path,
    out_rows: str | Path | None = None,
    out_report: str | Path | None = None,
    *,
    db_path: str | Path | None = None,
    history_response_paths: list[str | Path] | None = None,
    lineage_paths: list[str | Path] | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    budget: int | None = None,
    per_source_cap: int | None = None,
    per_action_cap: int | None = 1,
    min_priority: float | None = None,
    coker_weight: float = 1.0,
    carrier_weight: float = 0.5,
    uncertainty_weight: float = 0.25,
    novelty_weight: float = 0.25,
    success_weight: float = 0.25,
    cost_weight: float = 1.0,
    audit_risk_weight: float = 0.25,
) -> dict[str, Any]:
    # Load and deduplicate candidates across all sources.
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cp in candidate_paths or []:
        p = Path(cp)
        if not p.exists():
            continue
        for row in read_jsonl(p):
            if not isinstance(row, dict):
                continue
            row = dict(row)
            meta = dict(_as_dict(row.get('metadata')))
            meta.setdefault('source', meta.get('source') or row.get('source') or p.stem)
            meta.setdefault('candidate_source_path', str(p))
            row['metadata'] = meta
            key = f"{row.get('task_id') or meta.get('task_id') or ''}␟{row.get('tactic') or row.get('full_tactic') or ''}␟{row.get('action_id') or row.get('id') or ''}"
            if key in seen:
                continue
            seen.add(key)
            candidates.append(row)
    history = merge_histories(load_history_from_db(db_path), load_history_from_response_files(history_response_paths))
    cfg = SchedulerConfig(
        top_k=int(budget or 64),
        per_task_cap=per_action_cap,
        response_weight=float(coker_weight),
        carrier_weight=float(carrier_weight),
        success_weight=float(success_weight),
        novelty_weight=float(novelty_weight),
        uncertainty_weight=float(uncertainty_weight),
        lineage_weight=float(novelty_weight),
        cost_weight=float(cost_weight),
        timeout_weight=float(audit_risk_weight),
        min_score=min_priority,
    )
    rows, report = schedule_actions(candidates, history=history, response_normal=response_normal, carrier_normal=carrier_normal, config=cfg)
    # Apply per-source cap after scoring if requested.
    if per_source_cap is not None:
        selected: list[dict[str, Any]] = []
        source_counts: dict[str, int] = {}
        for r in rows:
            if not r.get('scheduled'):
                continue
            src = str(r.get('source') or 'unknown')
            if source_counts.get(src, 0) >= per_source_cap:
                r['selected'] = False
                r['scheduled'] = False
                r['rejected_reason'] = 'per_source_cap'
                continue
            if len(selected) >= cfg.top_k:
                r['selected'] = False
                continue
            r['selected'] = True
            selected.append(r['action'])
            source_counts[src] = source_counts.get(src, 0) + 1
        report['per_source_cap'] = per_source_cap
        report['selected_by_source'] = source_counts
    else:
        selected = [r['action'] for r in rows if r.get('selected')]
    # Attach lineage summary as chart-level metadata if supplied.
    if lineage_paths:
        report['lineage_inputs'] = [str(x) for x in lineage_paths]
    report['n_selected'] = len(selected)
    write_jsonl(out_actions, selected)
    if out_rows:
        write_jsonl(out_rows, rows)
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


__all__ = [
    "SCHEMA_VERSION", "SchedulerConfig", "ActionHistoryStats", "load_history_from_db", "load_history_from_response_files",
    "schedule_actions", "active_audit_schedule_from_files", "schedule_active_audits_from_files", "_parse_json_or_file", "write_rows_csv",
]
