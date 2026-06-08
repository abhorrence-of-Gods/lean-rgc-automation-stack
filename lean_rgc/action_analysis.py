from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import csv
import json
import math
from collections import defaultdict, Counter

import numpy as np

from .schemas import read_jsonl


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _sum_prefix(d: dict[str, Any] | None, prefix: str) -> float:
    d = d or {}
    return float(sum(_as_float(v) for k, v in d.items() if str(k).startswith(prefix)))


def _response_norm(row: dict[str, Any]) -> float:
    flat = row.get("response_flat")
    if flat is not None:
        try:
            return float(np.linalg.norm(np.asarray(flat, dtype=float)))
        except Exception:
            pass
    resp = row.get("response") or {}
    return float(np.linalg.norm(np.asarray([_as_float(v) for v in resp.values()], dtype=float))) if resp else 0.0


def _action_dict(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action") or {}
    if isinstance(a, dict):
        return a
    return {}


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    a = _action_dict(row)
    meta = a.get("metadata") or row.get("metadata") or {}
    return meta if isinstance(meta, dict) else {}


def _carrier_delta(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if isinstance(cd, dict):
        return float(sum(_as_float(v) for v in cd.values()))
    return 0.0


def _carrier_negative(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return 0.0
    return float(sum(max(0.0, -_as_float(v)) for v in cd.values()))


@dataclass
class ActionGroupSummary:
    group_key: str
    group_value: str
    n: int
    success_rate: float
    partial_rate: float
    timeout_rate: float
    elab_error_rate: float
    mean_response_norm: float
    mean_goal_response: float
    mean_type_response: float
    mean_search_response: float
    mean_carrier_delta: float
    mean_carrier_negative: float
    mean_cost: float
    top_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_action_groups(
    responses_path: str | Path,
    *,
    group_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Summarize response quality by tactic/chart provenance.

    This is intentionally chart-level: it helps audit which generated candidate
    families are useful, without declaring the family canonical.
    """
    rows = read_jsonl(responses_path)
    group_keys = group_keys or [
        "generated_by",
        "prefix_kind",
        "prefix_tactic",
        "core_tactic",
        "tactic_class",
        "carrier_tags",
        "task_id",
    ]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        action = _action_dict(row)
        meta = _metadata(row)
        # Normalized fields.
        fields: dict[str, Any] = {}
        fields["task_id"] = row.get("task_id") or action.get("task_id") or meta.get("task_id") or ""
        fields["tactic_class"] = action.get("tactic_class") or row.get("tactic_class") or ""
        fields["generated_by"] = meta.get("generated_by") or action.get("generated_by") or "manual_or_unknown"
        fields["prefix_kind"] = meta.get("prefix_kind") or ""
        fields["prefix_tactic"] = (meta.get("prefix_tactic") or "").strip().replace("\n", "; ")
        fields["core_tactic"] = (meta.get("core_tactic") or action.get("tactic") or row.get("tactic") or "").strip().replace("\n", "; ")
        tags = action.get("carrier_tags") or meta.get("carrier_tags") or []
        if isinstance(tags, str):
            tags = [tags]
        fields["carrier_tags"] = ",".join(sorted(str(t) for t in tags))
        for k in group_keys:
            v = str(fields.get(k, ""))
            if v:
                groups[(k, v)].append(row)
    summaries: list[ActionGroupSummary] = []
    for (gk, gv), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = len(rs)
        statuses = Counter(str(r.get("audit_status") or r.get("status") or "unknown") for r in rs)
        norms = [_response_norm(r) for r in rs]
        goal = [_sum_prefix(r.get("response") or {}, "goal.") for r in rs]
        typ = [_sum_prefix(r.get("response") or {}, "type.") for r in rs]
        search = [_sum_prefix(r.get("response") or {}, "search.") for r in rs]
        carrier = [_carrier_delta(r) for r in rs]
        carrier_neg = [_carrier_negative(r) for r in rs]
        costs = []
        for r in rs:
            a = _action_dict(r)
            costs.append(_as_float(a.get("cost_estimate"), 0.0))
        top_status = statuses.most_common(1)[0][0] if statuses else "unknown"
        summaries.append(ActionGroupSummary(
            group_key=gk,
            group_value=gv,
            n=n,
            success_rate=(statuses.get("success", 0) + statuses.get("dry_run", 0)) / max(1, n),
            partial_rate=(statuses.get("partial", 0) + statuses.get("partial_success", 0)) / max(1, n),
            timeout_rate=statuses.get("timeout", 0) / max(1, n),
            elab_error_rate=statuses.get("elab_error", 0) / max(1, n),
            mean_response_norm=float(np.mean(norms)) if norms else 0.0,
            mean_goal_response=float(np.mean(goal)) if goal else 0.0,
            mean_type_response=float(np.mean(typ)) if typ else 0.0,
            mean_search_response=float(np.mean(search)) if search else 0.0,
            mean_carrier_delta=float(np.mean(carrier)) if carrier else 0.0,
            mean_carrier_negative=float(np.mean(carrier_neg)) if carrier_neg else 0.0,
            mean_cost=float(np.mean(costs)) if costs else 0.0,
            top_status=top_status,
        ))
    overall = {
        "n_responses": len(rows),
        "group_keys": group_keys,
        "groups": [s.to_dict() for s in summaries],
    }
    return overall


def write_action_group_report(responses_path: str | Path, out_json: str | Path, out_csv: str | Path | None = None, *, group_keys: list[str] | None = None) -> dict[str, Any]:
    rep = summarize_action_groups(responses_path, group_keys=group_keys)
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        rows = rep.get("groups", [])
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            if rows:
                fieldnames = list(rows[0].keys())
            else:
                fieldnames = ["group_key", "group_value", "n"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    return rep


__all__ = ["ActionGroupSummary", "summarize_action_groups", "write_action_group_report"]
