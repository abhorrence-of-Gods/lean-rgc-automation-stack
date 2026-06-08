from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

import numpy as np

from .schemas import read_jsonl, write_jsonl
from .candidate_acceptance import _action as _base_action, _carrier_gain, _defect_vec, _dot_aligned, _response_vec, _status, addressed_atoms, generated_source


def _key(row: dict[str, Any]) -> tuple[str, str, str]:
    a = _base_action(row)
    return (
        str(row.get("task_id") or ""),
        str(row.get("state_id") or ""),
        str(row.get("action_id") or a.get("action_id") or row.get("tactic") or a.get("tactic") or ""),
    )


def _cost(row: dict[str, Any]) -> float:
    try:
        return float((_base_action(row).get("cost_estimate", 1.0) or 1.0))
    except Exception:
        return 1.0


def _audit_penalty(row: dict[str, Any], weight: float) -> float:
    return float(weight if _status(row) in {"timeout", "unsafe", "elab_error"} else 0.0)


def _base_support(base_rows: list[dict[str, Any]]) -> dict[str, float]:
    sup: dict[str, float] = {}
    for r in base_rows:
        sid = str(r.get("state_id", ""))
        score = _dot_aligned(_response_vec(r), _defect_vec(r))
        sup[sid] = max(sup.get(sid, float("-inf")), score)
    return {k: (0.0 if v == float("-inf") else float(v)) for k, v in sup.items()}


def _margin(row: dict[str, Any], base_support: dict[str, float], *, carrier_weight: float, cost_weight: float, audit_weight: float) -> dict[str, float]:
    sid = str(row.get("state_id", ""))
    rv = _response_vec(row)
    dv = _defect_vec(row)
    score = _dot_aligned(rv, dv)
    base = float(base_support.get(sid, 0.0))
    atoms = addressed_atoms(row)
    carrier = _carrier_gain(row, atoms)
    cost = _cost(row)
    audit = _audit_penalty(row, audit_weight)
    margin = score - base + carrier_weight * carrier - cost_weight * cost - audit
    return {
        "response_score": float(score),
        "base_support": base,
        "carrier_gain": float(carrier),
        "cost": float(cost),
        "audit_penalty": float(audit),
        "margin": float(margin),
        "response_norm": float(np.linalg.norm(rv)) if rv.size else 0.0,
        "defect_norm": float(np.linalg.norm(dv)) if dv.size else 0.0,
    }


@dataclass
class RobustAcceptanceRecord:
    task_id: str
    state_id: str
    action_id: str
    tactic: str
    status: str
    generated_by: str
    addressed_atoms: list[str]
    train_margin: float
    shadow_margin: float | None
    robust_margin: float
    disagreement: float
    accepted: bool
    train: dict[str, float] = field(default_factory=dict)
    shadow: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RobustAcceptanceSummary:
    n: int
    accepted: int
    mean_robust_margin: float
    max_robust_margin: float
    shadow_coverage: float
    status_counts: dict[str, int] = field(default_factory=dict)
    accepted_by_source: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def robust_accept_candidate_rows(
    base_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    shadow_rows: list[dict[str, Any]] | None = None,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.7,
    audit_weight: float = 0.2,
    disagreement_weight: float = 0.5,
    require_shadow: bool = False,
    require_success: bool = False,
) -> list[RobustAcceptanceRecord]:
    """Robust coker acceptance for generated candidates.

    Candidate acceptance is evaluated on the primary audit rows and, when supplied,
    a shadow/held-out audit chart.  The robust margin is

        min(train_margin, shadow_margin) - disagreement_weight * |train-shadow|.

    Without shadow rows, this reduces to train_margin.  The output is still a
    witness-level acceptance chart; canonical promotion is handled elsewhere.
    """
    support = _base_support(base_rows)
    shadow_by_key = {_key(r): r for r in (shadow_rows or [])}
    out: list[RobustAcceptanceRecord] = []
    for r in candidate_rows:
        a = _base_action(r)
        k = _key(r)
        train = _margin(r, support, carrier_weight=carrier_weight, cost_weight=cost_weight, audit_weight=audit_weight)
        sr = shadow_by_key.get(k)
        shadow: dict[str, float] = {}
        shadow_margin: float | None = None
        if sr is not None:
            shadow = _margin(sr, support, carrier_weight=carrier_weight, cost_weight=cost_weight, audit_weight=audit_weight)
            shadow_margin = float(shadow["margin"])
        if shadow_margin is None:
            robust = float("-inf") if require_shadow else float(train["margin"])
            disagreement = 0.0 if not require_shadow else float("inf")
        else:
            disagreement = abs(float(train["margin"]) - shadow_margin)
            robust = min(float(train["margin"]), shadow_margin) - disagreement_weight * disagreement
        status = _status(r)
        ok_status = status in {"success", "partial", "dry_run"} if require_success else status not in {"timeout", "unsafe", "elab_error"}
        accepted = bool(ok_status and robust > margin_threshold and np.isfinite(robust))
        meta = dict(a.get("metadata") or {})
        meta.setdefault("robust_acceptance", {})
        meta["robust_acceptance"].update({
            "train_margin": float(train["margin"]),
            "shadow_margin": shadow_margin,
            "robust_margin": float(robust) if np.isfinite(robust) else None,
            "disagreement": float(disagreement) if np.isfinite(disagreement) else None,
            "canonical_status": "robust_acceptance_chart_not_canonical",
        })
        out.append(RobustAcceptanceRecord(
            task_id=str(k[0]),
            state_id=str(k[1]),
            action_id=str(k[2]),
            tactic=str(a.get("tactic") or r.get("tactic") or ""),
            status=status,
            generated_by=generated_source(r),
            addressed_atoms=sorted(addressed_atoms(r)),
            train_margin=float(train["margin"]),
            shadow_margin=shadow_margin,
            robust_margin=float(robust) if np.isfinite(robust) else -1e100,
            disagreement=float(disagreement) if np.isfinite(disagreement) else 1e100,
            accepted=accepted,
            train=train,
            shadow=shadow,
            metadata={"action": {**a, "metadata": meta}, "shadow_found": sr is not None},
        ))
    out.sort(key=lambda x: x.robust_margin, reverse=True)
    return out


def summarize_robust_acceptance(records: list[RobustAcceptanceRecord]) -> RobustAcceptanceSummary:
    if not records:
        return RobustAcceptanceSummary(n=0, accepted=0, mean_robust_margin=0.0, max_robust_margin=0.0, shadow_coverage=0.0)
    accepted = [r for r in records if r.accepted]
    status_counts: dict[str, int] = {}
    by_source: dict[str, int] = {}
    shadow_found = 0
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        if r.metadata.get("shadow_found"):
            shadow_found += 1
        if r.accepted:
            by_source[r.generated_by] = by_source.get(r.generated_by, 0) + 1
    margins = [float(r.robust_margin) for r in records if r.robust_margin > -1e50]
    return RobustAcceptanceSummary(
        n=len(records),
        accepted=len(accepted),
        mean_robust_margin=float(np.mean(margins)) if margins else 0.0,
        max_robust_margin=float(np.max(margins)) if margins else 0.0,
        shadow_coverage=float(shadow_found / len(records)) if records else 0.0,
        status_counts=status_counts,
        accepted_by_source=by_source,
    )


def robust_accept_candidates_file(
    base_responses: str | Path,
    candidate_responses: str | Path,
    out: str | Path,
    *,
    shadow_responses: str | Path | None = None,
    accepted_actions_out: str | Path | None = None,
    summary_out: str | Path | None = None,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.7,
    audit_weight: float = 0.2,
    disagreement_weight: float = 0.5,
    require_shadow: bool = False,
    require_success: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    shadow = read_jsonl(shadow_responses) if shadow_responses else None
    recs = robust_accept_candidate_rows(
        base,
        cand,
        shadow_rows=shadow,
        margin_threshold=margin_threshold,
        cost_weight=cost_weight,
        carrier_weight=carrier_weight,
        audit_weight=audit_weight,
        disagreement_weight=disagreement_weight,
        require_shadow=require_shadow,
        require_success=require_success,
    )
    rows = [r.to_dict() for r in recs]
    write_jsonl(out, rows)
    if accepted_actions_out:
        actions: list[dict[str, Any]] = []
        for r in recs:
            if r.accepted:
                action = dict(r.metadata.get("action") or {})
                if action:
                    actions.append(action)
        write_jsonl(accepted_actions_out, actions)
    summary = summarize_robust_acceptance(recs).to_dict()
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows, summary



def run_robust_acceptance(
    base_responses: str | Path,
    candidate_responses: str | Path,
    out: str | Path,
    *,
    summary_out: str | Path | None = None,
    accepted_actions_out: str | Path | None = None,
    per_row_out: str | Path | None = None,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_bonus: float = 0.7,
    goal_bonus: float = 1.0,
    max_mass: float = 1.0,
    ridge: float = 1e-4,
    z_value: float = 1.0,
    min_repeats: int = 1,
    min_success_rate: float = 1.0,
    max_per_task: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """LCB-style robust acceptance grouped by task/state/action.

    This is the v15-compatible entry point used by the existing CLI.  It groups
    repeated audits of the same candidate, computes a lower confidence bound for
    coker margin, and accepts only if the group has enough repeats and success
    rate.  Outputs are finite robust acceptance witnesses, not canonical
    promotion certificates.
    """
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    support = _base_support(base)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in cand:
        groups.setdefault(_key(r), []).append(r)
    rows: list[dict[str, Any]] = []
    accepted_actions: list[dict[str, Any]] = []
    for key, gs in groups.items():
        margins = [_margin(r, support, carrier_weight=carrier_bonus, cost_weight=cost_weight, audit_weight=0.2) for r in gs]
        vals = [float(m.get('margin', 0.0)) for m in margins]
        mean_margin = float(np.mean(vals)) if vals else 0.0
        std_margin = float(np.std(vals)) if len(vals) > 1 else 0.0
        lcb = mean_margin - float(z_value) * std_margin / float(np.sqrt(max(1, len(vals))))
        statuses = [_status(r) for r in gs]
        success_like = [s for s in statuses if s in {'success', 'partial', 'dry_run'}]
        success_rate = len(success_like) / max(1, len(statuses))
        hard_bad = any(s in {'timeout', 'unsafe', 'elab_error'} for s in statuses)
        accepted = bool(len(gs) >= int(min_repeats) and success_rate >= float(min_success_rate) and lcb > margin_threshold and not hard_bad)
        first = gs[0]
        act = _base_action(first)
        meta = dict(act.get('metadata') or {})
        meta.update({
            'accepted_by': 'robust_coker_lcb' if accepted else meta.get('accepted_by'),
            'robust_acceptance': {
                'mean_margin': mean_margin,
                'std_margin': std_margin,
                'lcb_margin': lcb,
                'n_repeats': len(gs),
                'success_rate': success_rate,
                'canonical_status': 'robust_acceptance_chart_not_canonical',
            },
        })
        act = {**act, 'metadata': meta}
        row = {
            'task_id': key[0],
            'state_id': key[1],
            'action_id': key[2],
            'tactic': str(act.get('tactic') or first.get('tactic') or ''),
            'status': 'group',
            'statuses': statuses,
            'generated_by': generated_source(first),
            'addressed_atoms': sorted(addressed_atoms(first)),
            'mean_margin': mean_margin,
            'std_margin': std_margin,
            'robust_margin': lcb,
            'lcb_margin': lcb,
            'n_repeats': len(gs),
            'success_rate': success_rate,
            'accepted': accepted,
            'train': margins[0] if margins else {},
            'metadata': {'action': act, 'group_key': list(key), 'raw_count': len(gs)},
        }
        rows.append(row)
        if accepted:
            accepted_actions.append(act)
    rows.sort(key=lambda r: float(r.get('robust_margin', 0.0)), reverse=True)
    accepted_actions.sort(key=lambda a: float((a.get('metadata') or {}).get('robust_acceptance', {}).get('lcb_margin', 0.0)), reverse=True)
    if max_per_task is not None:
        kept=[]; counts={}
        for a in accepted_actions:
            tid=str((a.get('metadata') or {}).get('task_id') or '')
            if counts.get(tid,0) >= max_per_task:
                continue
            kept.append(a); counts[tid]=counts.get(tid,0)+1
        accepted_actions=kept
    write_jsonl(out, rows)
    if per_row_out:
        write_jsonl(per_row_out, rows)
    if accepted_actions_out:
        write_jsonl(accepted_actions_out, accepted_actions)
    acc=[r for r in rows if r.get('accepted')]
    summary={
        'n_groups': len(rows),
        'n_accepted': len(acc),
        'accept_rate': len(acc)/max(1,len(rows)),
        'mean_robust_margin': float(np.mean([float(r.get('robust_margin',0.0)) for r in rows])) if rows else 0.0,
        'mean_accepted_robust_margin': float(np.mean([float(r.get('robust_margin',0.0)) for r in acc])) if acc else 0.0,
        'settings': {
            'margin_threshold': margin_threshold,
            'cost_weight': cost_weight,
            'carrier_bonus': carrier_bonus,
            'goal_bonus': goal_bonus,
            'max_mass': max_mass,
            'ridge': ridge,
            'z_value': z_value,
            'min_repeats': min_repeats,
            'min_success_rate': min_success_rate,
            'max_per_task': max_per_task,
            'canonical_status': 'robust_acceptance_chart_not_canonical',
        },
    }
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    return rows, summary


__all__ = [
    "RobustAcceptanceRecord",
    "RobustAcceptanceSummary",
    "robust_accept_candidate_rows",
    "robust_accept_candidates_file",
    "run_robust_acceptance",
    "summarize_robust_acceptance",
    "run_robust_acceptance",
]

# ---------------------------------------------------------------------------
# v15 compatibility API: repeated-row lower-confidence-bound acceptance.
# This is used by pipeline --qgen-robust-accept.  It groups repeated audits for
# the same candidate action and accepts only if the LCB coker margin clears the
# threshold and the empirical success rate is high enough.
# ---------------------------------------------------------------------------

def _action_key(row: dict[str, Any]) -> tuple[str, str, str]:
    a = _base_action(row)
    return (str(row.get("task_id") or ""), str(row.get("state_id") or ""), str(row.get("action_id") or a.get("action_id") or a.get("tactic") or ""))


def run_robust_acceptance(
    base_responses: str | Path,
    candidate_responses: str | Path,
    out: str | Path,
    *,
    summary_out: str | Path | None = None,
    accepted_actions_out: str | Path | None = None,
    per_row_out: str | Path | None = None,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_bonus: float = 0.0,
    goal_bonus: float = 0.0,
    max_mass: float = 1.0,
    ridge: float = 1e-4,
    z_value: float = 1.0,
    min_repeats: int = 1,
    min_success_rate: float = 1.0,
    max_per_task: int = 16,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    support = _base_support(base)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in cand:
        groups.setdefault(_action_key(r), []).append(r)
    rows: list[dict[str, Any]] = []
    accepted_actions: list[dict[str, Any]] = []
    by_task_accept_count: dict[str, int] = {}
    for k, rs in groups.items():
        margins: list[float] = []
        statuses: list[str] = []
        metric_rows: list[dict[str, float]] = []
        for r in rs:
            m = _margin(r, support, carrier_weight=carrier_bonus, cost_weight=cost_weight, audit_weight=0.0)
            # Optional goal bonus: approximated by positive response mass in goal.* coordinates when present.
            if goal_bonus:
                resp = r.get("response") or {}
                if isinstance(resp, dict):
                    goal_gain = sum(float(v) for kk, v in resp.items() if str(kk).startswith("goal."))
                    m["margin"] += float(goal_bonus) * float(goal_gain)
                    m["goal_gain"] = float(goal_gain)
            margins.append(float(m["margin"]))
            statuses.append(_status(r))
            metric_rows.append(m)
        n = len(rs)
        mean = float(np.mean(margins)) if margins else 0.0
        std = float(np.std(margins, ddof=1)) if len(margins) > 1 else 0.0
        lcb = mean - float(z_value) * std / max(1.0, float(n) ** 0.5)
        success_like = sum(1 for s in statuses if s in {"success", "partial", "dry_run"})
        success_rate = success_like / max(1, n)
        base_row = rs[0]
        action = dict(_base_action(base_row))
        tid, sid, aid = k
        ok = bool(n >= int(min_repeats) and success_rate >= float(min_success_rate) and lcb > margin_threshold and all(s not in {"timeout", "unsafe", "elab_error"} for s in statuses))
        if by_task_accept_count.get(tid, 0) >= max_per_task:
            ok = False
        row = {
            "task_id": tid,
            "state_id": sid,
            "action_id": aid,
            "tactic": str(action.get("tactic") or ""),
            "n_repeats": n,
            "mean_margin": mean,
            "std_margin": std,
            "lcb_margin": float(lcb),
            "margin_threshold": float(margin_threshold),
            "success_rate": float(success_rate),
            "statuses": {s: statuses.count(s) for s in sorted(set(statuses))},
            "accepted": ok,
            "accepted_by": "robust_coker_lcb" if ok else "not_accepted",
            "canonical_status": "robust_acceptance_chart_not_canonical",
            "metadata": {"action": action, "per_row_margins": margins, "per_row_metrics": metric_rows},
        }
        rows.append(row)
        if ok:
            by_task_accept_count[tid] = by_task_accept_count.get(tid, 0) + 1
            meta = dict(action.get("metadata") or {})
            meta["accepted_by"] = "robust_coker_lcb"
            meta["robust_acceptance"] = {"lcb_margin": float(lcb), "mean_margin": mean, "std_margin": std, "n_repeats": n, "success_rate": success_rate, "canonical_status": "accepted_witness_not_canonical"}
            action["metadata"] = meta
            accepted_actions.append(action)
    rows.sort(key=lambda r: float(r.get("lcb_margin", 0.0)), reverse=True)
    write_jsonl(out, rows)
    if per_row_out:
        write_jsonl(per_row_out, [{"group_key": list(_action_key(r)), "row": r} for r in cand])
    if accepted_actions_out:
        write_jsonl(accepted_actions_out, accepted_actions)
    summary = {
        "n_groups": len(groups),
        "n_rows": len(cand),
        "n_accepted": len(accepted_actions),
        "mean_lcb_margin": float(np.mean([r["lcb_margin"] for r in rows])) if rows else 0.0,
        "max_lcb_margin": float(np.max([r["lcb_margin"] for r in rows])) if rows else 0.0,
        "min_repeats": int(min_repeats),
        "min_success_rate": float(min_success_rate),
        "canonical_status": "robust_acceptance_summary_not_canonical",
    }
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows, summary

# Extend __all__ after late definition.
try:
    __all__.append("run_robust_acceptance")
except Exception:
    __all__ = ["run_robust_acceptance"]
