from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import csv
import json
import math

import numpy as np

from .coker import project_onto_response_cone
from .schemas import read_jsonl, write_jsonl, TacticAction, stable_hash


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


def _state_key(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or "unknown")


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _action(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action")
    if isinstance(a, dict):
        return dict(a)
    tactic = str(row.get("tactic") or row.get("action_id") or "")
    if not tactic:
        return {}
    return {
        "action_id": str(row.get("action_id") or stable_hash({"tactic": tactic}, 10)),
        "tactic": tactic,
        "tactic_class": str(row.get("tactic_class") or "robust_coker"),
        "carrier_tags": [],
        "cost_estimate": float(row.get("cost", 1.0) or 1.0),
        "metadata": {},
    }


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
    s = 0.0
    for v in cd.values():
        try:
            s += max(0.0, float(v))
        except Exception:
            pass
    return float(s)


def _carrier_violation(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return 0.0
    s = 0.0
    for v in cd.values():
        try:
            s += max(0.0, -float(v))
        except Exception:
            pass
    return float(s)


def _goal_gain(row: dict[str, Any]) -> float:
    resp = row.get("response") or {}
    if not isinstance(resp, dict):
        return 0.0
    s = 0.0
    for k, v in resp.items():
        if str(k).startswith("goal."):
            try:
                s += float(v)
            except Exception:
                pass
    return float(s)


def _stable_fraction(row: dict[str, Any], salt: str = "robust") -> float:
    h = stable_hash({"salt": salt, "state": _state_key(row), "action": row.get("action_id") or _action(row).get("action_id") or row.get("tactic")}, 12)
    return int(h, 16) / float(16 ** len(h))


@dataclass
class RobustCokerRow:
    state_id: str
    task_id: str | None
    action_id: str
    tactic: str
    status: str
    train_margin: float
    robust_margin: float
    holdout_support: float
    train_support: float
    coker_dot: float
    overfit_gap: float
    uncertainty_penalty: float
    cost: float
    carrier_gain: float
    carrier_violation: float
    response_norm: float
    accepted: bool
    n_base_train: int
    n_base_holdout: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RobustCokerReport:
    base_responses: str
    candidate_responses: str
    n_candidates: int
    n_accepted: int
    accept_rate: float
    mean_train_margin: float
    mean_robust_margin: float
    mean_overfit_gap: float
    by_status: dict[str, int]
    settings: dict[str, Any]
    out_actions: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RobustCokerAcceptor:
    """Held-out/robust finite coker acceptor.

    This strengthens the ordinary coker-margin proxy by splitting base responses into
    a train cone and a holdout cone.  Candidate margin is computed against the train
    residual normal, but its support baseline is the maximum of train and holdout
    support.  A candidate whose margin disappears on held-out actions is rejected.
    """

    def __init__(
        self,
        *,
        margin_threshold: float = 0.0,
        holdout_fraction: float = 0.35,
        ridge: float = 1e-4,
        max_mass: float | None = 1.0,
        cost_weight: float = 0.05,
        carrier_gain_weight: float = 0.25,
        carrier_violation_weight: float = 0.7,
        audit_penalty: float = 1.0,
        uncertainty_weight: float = 0.10,
        require_success: bool = False,
    ):
        self.margin_threshold = float(margin_threshold)
        self.holdout_fraction = max(0.0, min(0.9, float(holdout_fraction)))
        self.ridge = float(ridge)
        self.max_mass = max_mass
        self.cost_weight = float(cost_weight)
        self.carrier_gain_weight = float(carrier_gain_weight)
        self.carrier_violation_weight = float(carrier_violation_weight)
        self.audit_penalty = float(audit_penalty)
        self.uncertainty_weight = float(uncertainty_weight)
        self.require_success = bool(require_success)

    def _split_base(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if len(rows) <= 2 or self.holdout_fraction <= 0:
            return rows, []
        hold = [r for r in rows if _stable_fraction(r) < self.holdout_fraction]
        train = [r for r in rows if r not in hold]
        if not train:
            train, hold = rows[:1], rows[1:]
        return train, hold

    def _projection(self, defect: np.ndarray, rows: list[dict[str, Any]]):
        R = []
        for r in rows:
            v = _vec(r)
            if v.size == defect.size and v.size:
                R.append(v)
        if not R:
            class Empty:
                pass
            rep = Empty()
            rep.residual = defect.tolist()
            rep.residual_norm = float(np.linalg.norm(defect))
            rep.active_count = 0
            rep.support_value = 0.0
            return rep, np.zeros((0, defect.size), dtype=float)
        Rm = np.stack(R, axis=0)
        return project_onto_response_cone(defect, Rm, ridge=self.ridge, max_mass=self.max_mass), Rm

    def accept(self, base_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[RobustCokerRow]:
        base_by: dict[str, list[dict[str, Any]]] = {}
        cand_by: dict[str, list[dict[str, Any]]] = {}
        for r in base_rows:
            base_by.setdefault(_state_key(r), []).append(r)
        for r in candidate_rows:
            cand_by.setdefault(_state_key(r), []).append(r)
        out: list[RobustCokerRow] = []
        for key, cands in cand_by.items():
            bases = base_by.get(key, [])
            defect = np.asarray([], dtype=float)
            for r in bases + cands:
                defect = _defect_vec(r)
                if defect.size:
                    break
            if not defect.size:
                rv = _vec(cands[0]) if cands else np.asarray([], dtype=float)
                defect = np.zeros_like(rv)
            train, hold = self._split_base(bases)
            proj, R_train = self._projection(defect, train)
            normal = np.asarray(getattr(proj, "residual", defect.tolist()), dtype=float)
            train_support = float(np.max(R_train @ normal)) if R_train.size else 0.0
            hold_vecs = []
            for r in hold:
                v = _vec(r)
                if v.size == normal.size and v.size:
                    hold_vecs.append(v)
            R_hold = np.stack(hold_vecs, axis=0) if hold_vecs else np.zeros((0, normal.size), dtype=float)
            holdout_support = float(np.max(R_hold @ normal)) if R_hold.size else train_support
            support = max(train_support, holdout_support)
            for row in cands:
                rv = _vec(row)
                if rv.size != normal.size or not rv.size:
                    dot = 0.0
                    response_norm = 0.0
                else:
                    dot = float(np.dot(normal, rv))
                    response_norm = float(np.linalg.norm(rv))
                status = _status(row)
                cost = _cost(row)
                cg = _carrier_gain(row)
                cv = _carrier_violation(row)
                uncertainty_penalty = self.uncertainty_weight * response_norm / math.sqrt(max(1, len(train)))
                audit = self.audit_penalty if status in {"timeout", "unsafe", "elab_error"} else 0.0
                train_margin = dot - train_support - self.cost_weight * cost + self.carrier_gain_weight * cg - self.carrier_violation_weight * cv - audit
                robust_margin = dot - support - self.cost_weight * cost + self.carrier_gain_weight * cg - self.carrier_violation_weight * cv - audit - uncertainty_penalty
                if self.require_success and status not in {"success", "dry_run"}:
                    robust_margin -= self.audit_penalty
                accepted = bool(robust_margin > self.margin_threshold and status not in {"timeout", "unsafe", "elab_error"})
                act = _action(row)
                meta = dict(act.get("metadata") or {}) if act else {}
                meta.setdefault("robust_coker", {})
                meta["robust_coker"].update({
                    "train_margin": train_margin,
                    "robust_margin": robust_margin,
                    "holdout_support": holdout_support,
                    "train_support": train_support,
                    "coker_dot": dot,
                    "overfit_gap": train_margin - robust_margin,
                    "canonical_status": "robust_coker_witness_not_canonical",
                })
                out.append(RobustCokerRow(
                    state_id=key,
                    task_id=str(row.get("task_id")) if row.get("task_id") is not None else None,
                    action_id=str(row.get("action_id") or act.get("action_id") or ""),
                    tactic=str(act.get("tactic") or row.get("tactic") or ""),
                    status=status,
                    train_margin=float(train_margin),
                    robust_margin=float(robust_margin),
                    holdout_support=float(holdout_support),
                    train_support=float(train_support),
                    coker_dot=float(dot),
                    overfit_gap=float(train_margin - robust_margin),
                    uncertainty_penalty=float(uncertainty_penalty),
                    cost=float(cost),
                    carrier_gain=float(cg),
                    carrier_violation=float(cv),
                    response_norm=float(response_norm),
                    accepted=accepted,
                    n_base_train=len(train),
                    n_base_holdout=len(hold),
                    metadata={"action": {**act, "metadata": meta} if act else {}, "raw": {k: row.get(k) for k in ["state_id", "task_id", "audit_status", "status"]}},
                ))
        return out


def _action_from_row(r: dict[str, Any]) -> dict[str, Any] | None:
    if not r.get("accepted"):
        return None
    meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
    action = meta.get("action") if isinstance(meta.get("action"), dict) else None
    if action is None:
        tactic = r.get("tactic")
        if not tactic:
            return None
        action = {"action_id": r.get("action_id") or stable_hash({"tactic": tactic}, 10), "tactic": tactic, "tactic_class": "robust_coker", "carrier_tags": [], "cost_estimate": r.get("cost", 1.0), "metadata": {}}
    action = dict(action)
    action.setdefault("metadata", {})["robust_coker_margin"] = r.get("robust_margin")
    action.setdefault("metadata", {})["robust_coker_overfit_gap"] = r.get("overfit_gap")
    if r.get("task_id") and not action.get("task_id"):
        action["task_id"] = r.get("task_id")
        action.setdefault("metadata", {})["task_id"] = r.get("task_id")
    return TacticAction.from_dict(action).to_dict()


def summarize_robust_rows(rows: list[RobustCokerRow] | list[dict[str, Any]]) -> dict[str, Any]:
    ds = [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in rows]
    acc = [r for r in ds if r.get("accepted")]
    by_status: dict[str, int] = {}
    for r in ds:
        st = str(r.get("status", "unknown"))
        by_status[st] = by_status.get(st, 0) + 1
    def mean(key: str, xs: list[dict[str, Any]] = ds) -> float:
        return float(sum(float(x.get(key, 0.0) or 0.0) for x in xs) / max(1, len(xs)))
    return {
        "n_candidates": len(ds),
        "n_accepted": len(acc),
        "accept_rate": len(acc) / max(1, len(ds)),
        "mean_train_margin": mean("train_margin"),
        "mean_robust_margin": mean("robust_margin"),
        "mean_accepted_robust_margin": mean("robust_margin", acc),
        "mean_overfit_gap": mean("overfit_gap"),
        "by_status": by_status,
    }


def run_robust_coker_acceptance(
    base_responses: str | Path,
    candidate_responses: str | Path,
    *,
    out_report: str | Path | None = None,
    out_actions: str | Path | None = None,
    out_rows: str | Path | None = None,
    out_csv: str | Path | None = None,
    margin_threshold: float = 0.0,
    holdout_fraction: float = 0.35,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    cost_weight: float = 0.05,
    carrier_gain_weight: float = 0.25,
    carrier_violation_weight: float = 0.7,
    audit_penalty: float = 1.0,
    uncertainty_weight: float = 0.10,
    require_success: bool = False,
    max_actions: int | None = None,
) -> RobustCokerReport:
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    acc = RobustCokerAcceptor(
        margin_threshold=margin_threshold,
        holdout_fraction=holdout_fraction,
        ridge=ridge,
        max_mass=max_mass,
        cost_weight=cost_weight,
        carrier_gain_weight=carrier_gain_weight,
        carrier_violation_weight=carrier_violation_weight,
        audit_penalty=audit_penalty,
        uncertainty_weight=uncertainty_weight,
        require_success=require_success,
    )
    rows = [r.to_dict() for r in acc.accept(base, cand)]
    actions = [_action_from_row(r) for r in rows]
    actions = [a for a in actions if a is not None]
    actions = sorted(actions, key=lambda a: float((a.get("metadata") or {}).get("robust_coker_margin") or 0.0), reverse=True)
    if max_actions is not None:
        actions = actions[:max_actions]
    if out_rows:
        write_jsonl(out_rows, rows)
    if out_actions:
        write_jsonl(out_actions, actions)
    summ = summarize_robust_rows(rows)
    rep = RobustCokerReport(
        base_responses=str(base_responses),
        candidate_responses=str(candidate_responses),
        n_candidates=int(summ["n_candidates"]),
        n_accepted=int(summ["n_accepted"]),
        accept_rate=float(summ["accept_rate"]),
        mean_train_margin=float(summ["mean_train_margin"]),
        mean_robust_margin=float(summ["mean_robust_margin"]),
        mean_overfit_gap=float(summ["mean_overfit_gap"]),
        by_status=dict(summ["by_status"]),
        settings={
            "margin_threshold": margin_threshold,
            "holdout_fraction": holdout_fraction,
            "ridge": ridge,
            "max_mass": max_mass,
            "cost_weight": cost_weight,
            "carrier_gain_weight": carrier_gain_weight,
            "carrier_violation_weight": carrier_violation_weight,
            "audit_penalty": audit_penalty,
            "uncertainty_weight": uncertainty_weight,
            "require_success": require_success,
            "canonical_status": "robust_acceptance_witness_not_canonical",
        },
        out_actions=str(out_actions) if out_actions else None,
    )
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            fields = ["state_id", "task_id", "action_id", "tactic", "status", "train_margin", "robust_margin", "holdout_support", "train_support", "overfit_gap", "accepted"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fields})
    return rep


__all__ = ["RobustCokerAcceptor", "RobustCokerRow", "RobustCokerReport", "run_robust_coker_acceptance", "summarize_robust_rows"]
