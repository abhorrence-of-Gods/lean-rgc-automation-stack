from __future__ import annotations

from dataclasses import dataclass, asdict, field, field, field
from pathlib import Path
from typing import Any
import json

import numpy as np

from .coker import project_onto_response_cone
from .schemas import read_jsonl, write_jsonl, TacticAction


def _vec(row: dict[str, Any], key: str = "response_flat") -> np.ndarray:
    try:
        return np.asarray(row.get(key, []) or [], dtype=float).reshape(-1)
    except Exception:
        return np.asarray([], dtype=float)


def _defect_vec(row: dict[str, Any]) -> np.ndarray:
    d = row.get("defect_before") or row.get("defect") or {}
    if isinstance(d, dict):
        if d.get("flat"):
            try:
                return np.asarray(d.get("flat") or [], dtype=float).reshape(-1)
            except Exception:
                pass
        # Fallback: flatten nested numeric components in stable order.
        vals: list[float] = []
        for comp in ["goal", "type", "search", "carrier", "audit"]:
            cd = d.get(comp) or {}
            if isinstance(cd, dict):
                for k in sorted(cd):
                    try:
                        vals.append(float(cd[k]))
                    except Exception:
                        pass
        return np.asarray(vals, dtype=float)
    return np.asarray([], dtype=float)


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "")


def _action(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action")
    return a if isinstance(a, dict) else {}


def _cost(row: dict[str, Any]) -> float:
    a = _action(row)
    try:
        return float(a.get("cost_estimate", row.get("cost", 1.0)))
    except Exception:
        return 1.0


def _carrier_gain(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return 0.0
    total = 0.0
    for v in cd.values():
        try:
            total += max(0.0, float(v))
        except Exception:
            pass
    return float(total)


def _goal_gain(row: dict[str, Any]) -> float:
    resp = row.get("response") or {}
    if not isinstance(resp, dict):
        return 0.0
    total = 0.0
    for k, v in resp.items():
        if str(k).startswith("goal."):
            try:
                total += float(v)
            except Exception:
                pass
    return float(total)


def _state_key(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or "unknown")


@dataclass
class RegistryAcceptanceRow:
    state_id: str
    task_id: str | None
    action_id: str
    tactic: str
    status: str
    margin: float
    accepted: bool
    local_support: float
    coker_dot: float
    cost: float
    carrier_gain: float
    goal_gain: float
    response_norm: float
    normal_norm: float = 0.0
    robust_penalty: float = 0.0
    robust_margin: float = 0.0
    base_active_count: int = 0
    base_residual_norm: float = 0.0
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegistryAcceptanceSummary:
    n_candidates: int
    n_accepted: int
    accept_rate: float
    mean_margin: float
    mean_accepted_margin: float
    mean_goal_gain: float
    mean_carrier_gain: float
    by_status: dict[str, int] = field(default_factory=dict)
    by_generator: dict[str, dict[str, Any]] = field(default_factory=dict)
    mean_robust_margin: float = 0.0
    mean_accepted_robust_margin: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RegistryCokerAcceptor:
    """Accept registry-generated actions by finite coker-margin proxy.

    For each state, base responses define the current reachable cone.  A generated
    candidate is accepted only if its audited response has positive margin against
    the normal residual of the base cone, after cost/audit penalties.
    """

    def __init__(self, *, margin_threshold: float = 0.0, cost_weight: float = 0.05, carrier_bonus: float = 0.0, goal_bonus: float = 0.0, max_mass: float = 1.0, ridge: float = 1e-4, robust_radius: float = 0.0, robust_relative_radius: float = 0.0, accept_on_robust: bool = False):
        self.margin_threshold = float(margin_threshold)
        self.cost_weight = float(cost_weight)
        self.carrier_bonus = float(carrier_bonus)
        self.goal_bonus = float(goal_bonus)
        self.max_mass = float(max_mass)
        self.ridge = float(ridge)
        self.robust_radius = float(robust_radius)
        self.robust_relative_radius = float(robust_relative_radius)
        self.accept_on_robust = bool(accept_on_robust)

    def _base_projection(self, defect: np.ndarray, base_rows: list[dict[str, Any]]):
        R = []
        for r in base_rows:
            v = _vec(r)
            if v.size == defect.size and v.size:
                R.append(v)
        if not R:
            # Empty base cone: residual normal is the defect itself.
            class Empty:
                pass
            rep = Empty()
            rep.residual = defect.tolist()
            rep.residual_norm = float(np.linalg.norm(defect))
            rep.active_count = 0
            rep.support_value = 0.0
            return rep, np.zeros((0, defect.size), dtype=float)
        Rm = np.stack(R, axis=0)
        rep = project_onto_response_cone(defect, Rm, ridge=self.ridge, max_mass=self.max_mass)
        return rep, Rm

    def accept(self, base_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[RegistryAcceptanceRow]:
        base_by: dict[str, list[dict[str, Any]]] = {}
        cand_by: dict[str, list[dict[str, Any]]] = {}
        for r in base_rows:
            base_by.setdefault(_state_key(r), []).append(r)
        for r in candidate_rows:
            cand_by.setdefault(_state_key(r), []).append(r)
        out: list[RegistryAcceptanceRow] = []
        for key, cands in cand_by.items():
            bases = base_by.get(key, [])
            defect = np.asarray([], dtype=float)
            for r in bases + cands:
                defect = _defect_vec(r)
                if defect.size:
                    break
            if not defect.size:
                # Fall back to dimension of first candidate response.
                rv = _vec(cands[0]) if cands else np.asarray([], dtype=float)
                defect = np.zeros_like(rv)
            proj, Rm = self._base_projection(defect, bases)
            normal = np.asarray(getattr(proj, "residual", defect.tolist()), dtype=float)
            normal_norm = float(np.linalg.norm(normal)) if normal.size else 0.0
            support = float(np.max(Rm @ normal)) if Rm.size else 0.0
            for row in cands:
                r = _vec(row)
                if r.size != normal.size or not r.size:
                    dot = 0.0
                    response_norm = 0.0
                else:
                    dot = float(np.dot(normal, r))
                    response_norm = float(np.linalg.norm(r))
                status = _status(row)
                cost = _cost(row)
                carrier_gain = _carrier_gain(row)
                goal_gain = _goal_gain(row)
                audit_penalty = 1.0 if status in {"timeout", "unsafe", "elab_error"} else 0.0
                margin = dot - support - self.cost_weight * cost - audit_penalty + self.carrier_bonus * carrier_gain + self.goal_bonus * goal_gain
                robust_penalty = normal_norm * (self.robust_radius + self.robust_relative_radius * response_norm)
                robust_margin = margin - robust_penalty
                decision_margin = robust_margin if self.accept_on_robust else margin
                accepted = bool(decision_margin > self.margin_threshold and status not in {"timeout", "unsafe", "elab_error"})
                act = _action(row)
                out.append(RegistryAcceptanceRow(
                    state_id=key,
                    task_id=str(row.get("task_id")) if row.get("task_id") is not None else None,
                    action_id=str(row.get("action_id") or act.get("action_id") or ""),
                    tactic=str(act.get("tactic") or row.get("tactic") or ""),
                    status=status,
                    margin=float(margin),
                    accepted=accepted,
                    local_support=support,
                    coker_dot=dot,
                    cost=cost,
                    carrier_gain=carrier_gain,
                    goal_gain=goal_gain,
                    response_norm=response_norm,
                    normal_norm=normal_norm,
                    robust_penalty=float(robust_penalty),
                    robust_margin=float(robust_margin),
                    base_active_count=int(getattr(proj, "active_count", 0)),
                    base_residual_norm=float(getattr(proj, "residual_norm", np.linalg.norm(normal))),
                    metadata={"action": act, "raw": {k: row.get(k) for k in ["state_id", "task_id", "audit_status", "status"]}},
                ))
        return out


def summarize_acceptance(rows: list[RegistryAcceptanceRow] | list[dict[str, Any]]) -> RegistryAcceptanceSummary:
    dicts = [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in rows]
    n = len(dicts)
    acc = [r for r in dicts if r.get("accepted")]
    by_status: dict[str, int] = {}
    by_gen: dict[str, dict[str, Any]] = {}
    for r in dicts:
        st = str(r.get("status", "unknown"))
        by_status[st] = by_status.get(st, 0) + 1
        meta = r.get("metadata", {}) or {}
        act = meta.get("action", {}) if isinstance(meta, dict) else {}
        ameta = act.get("metadata", {}) if isinstance(act, dict) else {}
        gen = str(ameta.get("generated_by") or ameta.get("prefix_kind") or r.get("context_kind") or "unknown")
        d = by_gen.setdefault(gen, {"n": 0, "accepted": 0, "mean_margin": 0.0, "mean_goal_gain": 0.0, "mean_carrier_gain": 0.0})
        d["n"] += 1
        d["accepted"] += int(bool(r.get("accepted")))
        d["mean_margin"] += float(r.get("margin", 0.0))
        d["mean_goal_gain"] += float(r.get("goal_gain", 0.0))
        d["mean_carrier_gain"] += float(r.get("carrier_gain", 0.0))
    for d in by_gen.values():
        if d["n"]:
            d["mean_margin"] /= d["n"]
            d["mean_goal_gain"] /= d["n"]
            d["mean_carrier_gain"] /= d["n"]
            d["accept_rate"] = d["accepted"] / d["n"]
    return RegistryAcceptanceSummary(
        n_candidates=n,
        n_accepted=len(acc),
        accept_rate=len(acc) / max(1, n),
        mean_margin=sum(float(r.get("margin", 0.0)) for r in dicts) / max(1, n),
        mean_accepted_margin=sum(float(r.get("margin", 0.0)) for r in acc) / max(1, len(acc)),
        mean_goal_gain=sum(float(r.get("goal_gain", 0.0)) for r in dicts) / max(1, n),
        mean_carrier_gain=sum(float(r.get("carrier_gain", 0.0)) for r in dicts) / max(1, n),
        mean_robust_margin=sum(float(r.get("robust_margin", r.get("margin", 0.0))) for r in dicts) / max(1, n),
        mean_accepted_robust_margin=sum(float(r.get("robust_margin", r.get("margin", 0.0))) for r in acc) / max(1, len(acc)),
        by_status=by_status,
        by_generator=by_gen,
    )


def run_registry_acceptance(base_responses: str | Path, candidate_responses: str | Path, out: str | Path, *, summary_out: str | Path | None = None, accepted_actions_out: str | Path | None = None, margin_threshold: float = 0.0, cost_weight: float = 0.05, carrier_bonus: float = 0.0, goal_bonus: float = 0.0, max_mass: float = 1.0, ridge: float = 1e-4, robust_radius: float = 0.0, robust_relative_radius: float = 0.0, accept_on_robust: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    acceptor = RegistryCokerAcceptor(margin_threshold=margin_threshold, cost_weight=cost_weight, carrier_bonus=carrier_bonus, goal_bonus=goal_bonus, max_mass=max_mass, ridge=ridge, robust_radius=robust_radius, robust_relative_radius=robust_relative_radius, accept_on_robust=accept_on_robust)
    rows = [r.to_dict() for r in acceptor.accept(base, cand)]
    write_jsonl(out, rows)
    summary = summarize_acceptance(rows).to_dict()
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if accepted_actions_out:
        actions: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for r in rows:
            if not r.get("accepted"):
                continue
            act = ((r.get("metadata") or {}).get("action") or {})
            if not act:
                continue
            task_id = r.get("task_id") or (act.get("metadata") or {}).get("task_id") or ""
            key = (str(task_id), str(act.get("tactic")))
            if key in seen:
                continue
            seen.add(key)
            d = dict(act)
            if task_id:
                d["task_id"] = task_id
                meta = dict(d.get("metadata") or {})
                meta["task_id"] = task_id
                meta["accepted_by"] = "registry_coker_margin"
                meta["accepted_by"] = "registry_coker_margin_robust" if r.get("robust_margin") is not None and r.get("robust_margin") != r.get("margin") else "registry_coker_margin"
                meta["acceptance_margin"] = r.get("margin")
                meta["acceptance_robust_margin"] = r.get("robust_margin")
                meta["acceptance_robust_penalty"] = r.get("robust_penalty")
                d["metadata"] = meta
            actions.append(d)
        write_jsonl(accepted_actions_out, actions)
    return rows, summary

# ---------------------------------------------------------------------------
# Compatibility layer for v0.7 CLI experiments.  The coker-margin acceptor
# above is the primary implementation; these wrappers expose a simpler
# score-based interface used by older/alternate pipeline paths.
# ---------------------------------------------------------------------------
@dataclass
class RegistryAcceptanceConfig:
    margin_threshold: float = 0.0
    max_per_task: int = 16
    goal_weight: float = 1.0
    type_weight: float = 0.6
    search_weight: float = 0.4
    carrier_weight: float = 0.7
    audit_weight: float = 0.2
    success_bonus: float = 0.25
    fail_penalty: float = 0.25
    timeout_penalty: float = 1.0
    cost_weight: float = 0.05


def accept_registry_candidates_files(
    base_responses_path: str | Path,
    registry_responses_path: str | Path,
    accepted_actions_out: str | Path,
    report_out: str | Path,
    audit_out: str | Path | None = None,
    cfg: RegistryAcceptanceConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or RegistryAcceptanceConfig()
    rows, summary = run_registry_acceptance(
        base_responses_path,
        registry_responses_path,
        audit_out or Path(report_out).with_suffix(".rows.jsonl"),
        summary_out=report_out,
        accepted_actions_out=accepted_actions_out,
        margin_threshold=cfg.margin_threshold,
        cost_weight=cfg.cost_weight,
        carrier_bonus=cfg.carrier_weight,
        goal_bonus=cfg.goal_weight,
    )
    # Respect max_per_task by rewriting accepted action file if requested.
    if accepted_actions_out and cfg.max_per_task > 0 and Path(accepted_actions_out).exists():
        acts = read_jsonl(accepted_actions_out)
        counts: dict[str, int] = {}
        kept = []
        for a in acts:
            tid = str(a.get("task_id") or (a.get("metadata") or {}).get("task_id") or "")
            if counts.get(tid, 0) >= cfg.max_per_task:
                continue
            counts[tid] = counts.get(tid, 0) + 1
            kept.append(a)
        write_jsonl(accepted_actions_out, kept)
        summary = dict(summary)
        summary["n_accepted_actions_capped"] = len(kept)
    return summary


# Historical alias expected by some dev branches.
def registry_acceptance(*args: Any, **kwargs: Any):
    return run_registry_acceptance(*args, **kwargs)

# ---------------------------------------------------------------------------
# v0.7 compatibility layer for older CLI hooks that used the name
# `registry_acceptance` / `RegistryAcceptanceConfig`.
# ---------------------------------------------------------------------------

@dataclass
class RegistryAcceptanceConfig:
    margin_threshold: float = 0.0
    max_per_task: int = 16
    goal_weight: float = 1.0
    type_weight: float = 0.6
    search_weight: float = 0.4
    carrier_weight: float = 0.7
    audit_weight: float = 0.2
    success_bonus: float = 0.25
    fail_penalty: float = 0.25
    timeout_penalty: float = 1.0
    cost_weight: float = 0.05


def accept_registry_candidates_files(
    base_responses: str | Path,
    registry_responses: str | Path,
    accepted_actions_out: str | Path,
    report_out: str | Path,
    audit_out: str | Path,
    cfg: RegistryAcceptanceConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or RegistryAcceptanceConfig()
    rows, summary = run_registry_acceptance(
        base_responses,
        registry_responses,
        audit_out,
        summary_out=report_out,
        accepted_actions_out=accepted_actions_out,
        margin_threshold=cfg.margin_threshold,
        cost_weight=cfg.cost_weight,
        carrier_bonus=cfg.carrier_weight,
        goal_bonus=cfg.goal_weight,
        max_mass=1.0,
        ridge=1e-4,
    )
    # max_per_task is enforced after writing by keeping the best margins.
    if cfg.max_per_task and Path(accepted_actions_out).exists():
        acts = read_jsonl(accepted_actions_out)
        by_task: dict[str, list[dict[str, Any]]] = {}
        for a in acts:
            task_id = str(a.get("task_id") or (a.get("metadata") or {}).get("task_id") or "")
            by_task.setdefault(task_id, []).append(a)
        trimmed: list[dict[str, Any]] = []
        for task_id, xs in by_task.items():
            xs.sort(key=lambda r: -float((r.get("metadata") or {}).get("acceptance_margin", 0.0)))
            trimmed.extend(xs[: cfg.max_per_task])
        write_jsonl(accepted_actions_out, trimmed)
        summary["n_accepted_actions_written"] = len(trimmed)
    return summary


def registry_acceptance(*args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compatibility alias for run_registry_acceptance."""
    return run_registry_acceptance(*args, **kwargs)
