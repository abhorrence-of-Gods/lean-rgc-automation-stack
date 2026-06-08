from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import numpy as np

from .schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl, stable_hash
from .executor import LeanExecutor
from .defects import ProofDefectExtractor
from .carrier_exposure import CarrierNormalizer


@dataclass
class ExposureFrontierRow:
    task_id: str
    state_id: str
    selected_prefix_id: str
    selected_prefix_tactic: str
    selected_status: str
    score: float
    defect_norm_before: float
    defect_norm_after: float
    response_norm: float
    carrier_delta_l1: float
    frontier_task: dict[str, Any]
    audit: dict[str, Any]
    candidates: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm_defect(d) -> float:
    try:
        return float(np.linalg.norm(d.as_numpy()))
    except Exception:
        return 0.0


def _carrier_delta_l1(before, after) -> float:
    keys = set(before.carrier) | set(after.carrier)
    total = 0.0
    for k in keys:
        try:
            total += max(0.0, float(before.carrier.get(k, 0.0) - after.carrier.get(k, 0.0)))
        except Exception:
            pass
    return float(total)


def _score_exposure(status: str, before, after, response_flat: list[float], carrier_delta: float, cost: float, branching: bool) -> float:
    # Exposure should reduce carrier/goal/type debt but not be rewarded purely as a final proof tactic.
    before_n = _norm_defect(before)
    after_n = _norm_defect(after)
    defect_drop = before_n - after_n
    goal_drop = sum(float(before.goal.get(k, 0.0) - after.goal.get(k, 0.0)) for k in set(before.goal) | set(after.goal))
    type_drop = sum(float(before.type.get(k, 0.0) - after.type.get(k, 0.0)) for k in set(before.type) | set(after.type))
    status_bonus = 0.0
    if status == "success":
        status_bonus = 1.0
    elif status in {"partial", "partial_success", "dry_run"}:
        status_bonus = 0.35
    elif status in {"timeout", "unsafe", "elab_error"}:
        status_bonus = -1.0
    branch_penalty = 0.15 if branching else 0.0
    return float(defect_drop + 0.7 * goal_drop + 0.5 * type_drop + 0.8 * carrier_delta + status_bonus - 0.1 * cost - branch_penalty)


def build_exposure_frontiers(
    tasks: list[LeanTask],
    executor: LeanExecutor,
    *,
    max_exposures: int = 8,
    allow_identity: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Audit structural exposure prefixes and create frontier tasks.

    A frontier task has the selected exposure prefix embedded into LeanTask.prefix,
    so subsequent core-action audits can operate on a carrier-exposed state.
    The selected prefix is still a chart/witness; it is saved with audit evidence.
    """
    extractor = ProofDefectExtractor()
    normalizer = CarrierNormalizer()
    frontier_tasks: list[dict[str, Any]] = []
    frontier_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for task in tasks:
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        exposures = normalizer.expose(task, state)[:max_exposures]
        if not allow_identity:
            exposures = [e for e in exposures if (getattr(e, "prefix_tactic", "") or "").strip()]
        if not exposures:
            exposures = normalizer.expose(task, state)[:1]
        candidates: list[dict[str, Any]] = []
        best: tuple[float, Any, Any, Any, list[float], float] | None = None
        for exp in exposures:
            tactic = (getattr(exp, "prefix_tactic", "") or "").strip()
            action = TacticAction(
                action_id="exposure_" + stable_hash({"task": task.task_id, "prefix": tactic, "kind": getattr(exp, "kind", "exposure")}, 12),
                tactic=tactic or "skip",
                tactic_class="exposure",
                carrier_tags=list(getattr(exp, "carrier_tags", []) or getattr(exp, "carrier_atoms", []) or []) + [str(getattr(exp, "kind", "exposure"))],
                cost_estimate=float(getattr(exp, "cost", 0.0) or 0.0),
                metadata={"generated_by": "exposure_frontier", "exposure": exp.to_dict() if hasattr(exp, "to_dict") else asdict(exp)},
            )
            # Lean has no `skip` tactic in all contexts; identity exposure is represented by an empty proof step.
            # For identity, do not call Lean; construct a neutral audit.
            if not tactic:
                after = before
                resp = {k: 0.0 for k in before.flat_keys}
                flat = [0.0 for _ in before.flat]
                status = "identity"
                audit_d = {"task_id": task.task_id, "state_id": state.state_id, "action_id": action.action_id, "status": status, "messages": ["identity exposure"], "action": action.to_dict()}
            else:
                rec = executor.run_tactic(task, action, state)
                after = extractor.extract(rec.after_state or state, rec)
                resp, flat, _ = extractor.response(before, after)
                rec.defect_before = before.to_dict(); rec.defect_after = after.to_dict(); rec.response = resp
                rec.carrier_delta = {k: before.carrier.get(k, 0.0) - after.carrier.get(k, 0.0) for k in sorted(set(before.carrier) | set(after.carrier))}
                audit_d = rec.to_dict(); audit_d["action"] = action.to_dict(); audit_rows.append(audit_d)
                status = rec.status
            carrier_delta = _carrier_delta_l1(before, after)
            score = _score_exposure(status, before, after, flat, carrier_delta, float(action.cost_estimate), bool(getattr(exp, "branching", False)))
            # Structural exposure is allowed to look locally worse in a file-mode
            # chart because the exposed frontier is intentionally unfinished.
            # Prefer non-empty, audit-safe exposure over the identity when it
            # addresses a visible carrier atom (e.g. forall/imp introduction).
            if tactic and status in {"partial", "dry_run", "success"}:
                score += 1.0
                if any(a in (getattr(exp, "carrier_tags", []) or getattr(exp, "carrier_atoms", []) or []) for a in ["unintroduced_forall", "unintroduced_imp", "missing_intro_scheme", "forall", "imp"]):
                    score += 0.5
            cand_d = {
                "prefix_id": getattr(exp, "prefix_id", action.action_id),
                "prefix_tactic": tactic,
                "kind": getattr(exp, "kind", "exposure"),
                "status": status,
                "score": score,
                "defect_norm_before": _norm_defect(before),
                "defect_norm_after": _norm_defect(after),
                "response_norm": float(np.linalg.norm(np.asarray(flat, dtype=float))) if flat else 0.0,
                "carrier_delta_l1": carrier_delta,
                "action": action.to_dict(),
            }
            candidates.append(cand_d)
            if best is None or score > best[0]:
                best = (score, exp, action, after, flat, carrier_delta)
        assert best is not None
        score, exp, action, after, flat, carrier_delta = best
        prefix = (getattr(exp, "prefix_tactic", "") or "").strip()
        old_prefix = (task.prefix or "").rstrip()
        new_prefix = "\n".join([x for x in [old_prefix, prefix] if x]).strip()
        ftask = LeanTask(**{**task.to_dict(), "prefix": new_prefix})
        meta = dict(ftask.metadata or {})
        meta["exposure_frontier"] = {
            "selected_prefix_id": getattr(exp, "prefix_id", action.action_id),
            "selected_prefix_tactic": prefix,
            "selected_kind": getattr(exp, "kind", "exposure"),
            "score": score,
            "carrier_delta_l1": carrier_delta,
            "source_task_id": task.task_id,
        }
        ftask = LeanTask(**{**ftask.to_dict(), "metadata": meta})
        frontier_tasks.append(ftask.to_dict())
        frontier_rows.append(ExposureFrontierRow(
            task_id=task.task_id,
            state_id=state.state_id,
            selected_prefix_id=getattr(exp, "prefix_id", action.action_id),
            selected_prefix_tactic=prefix,
            selected_status=candidates[int(np.argmax([c["score"] for c in candidates]))].get("status", "unknown"),
            score=float(score),
            defect_norm_before=_norm_defect(before),
            defect_norm_after=_norm_defect(after),
            response_norm=float(np.linalg.norm(np.asarray(flat, dtype=float))) if flat else 0.0,
            carrier_delta_l1=float(carrier_delta),
            frontier_task=ftask.to_dict(),
            audit={},
            candidates=candidates,
        ).to_dict())
    return frontier_tasks, frontier_rows, audit_rows


def write_exposure_frontiers(
    tasks_path: str | Path,
    out_tasks: str | Path,
    out_report: str | Path,
    executor: LeanExecutor,
    *,
    max_exposures: int = 8,
    import_mode: str = "preserve",
    allow_identity: bool = True,
) -> dict[str, Any]:
    # Import normalization is deliberately left to CLI to avoid circular import.
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    frontier, report, audits = build_exposure_frontiers(tasks, executor, max_exposures=max_exposures, allow_identity=allow_identity)
    write_jsonl(out_tasks, frontier)
    write_jsonl(out_report, report)
    audit_path = Path(out_report).with_suffix(".audit.jsonl")
    write_jsonl(audit_path, audits)
    scores = [float(r.get("score", 0.0)) for r in report]
    nonempty = sum(1 for r in report if str(r.get("selected_prefix_tactic", "")).strip())
    summary = {
        "n": len(report),
        "nonempty_prefix": nonempty,
        "nonempty_rate": nonempty / max(1, len(report)),
        "mean_score": float(np.mean(scores)) if scores else 0.0,
        "out_tasks": str(out_tasks),
        "out_report": str(out_report),
        "out_audit": str(audit_path),
    }
    Path(out_report).with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
