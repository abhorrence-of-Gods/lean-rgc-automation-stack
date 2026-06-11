from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import json

from .audit_pruning import _candidate_score, _row_action
from .response_completion import response_map_from_row
from .schemas import LeanTask, TacticAction, stable_hash, write_jsonl


SCHEMA_AUDIT_STAGE_PLAN = "lean-rgc-audit-stage-plan-v86.0"
SCHEMA_AUDIT_STAGE_ROW = "lean-rgc-audit-stage-row-v86.0"

DEFAULT_STAGE_CAPS = (64, 256, 512)
DEFAULT_SUCCESS_STATUSES = ("proved", "advanced", "ok", "succeeded")

AuditRunner = Callable[..., list[dict[str, Any]]]


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def rank_action_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic audit order: predicted score desc, action_id asc."""

    entries: list[dict[str, Any]] = []
    for row in rows:
        action = _row_action(row)
        entries.append(
            {
                "action_id": str(action.action_id),
                "predicted_score": float(_candidate_score(action)),
                "row": row,
                "action": action,
            }
        )
    entries.sort(key=lambda e: (-e["predicted_score"], e["action_id"]))
    for rank, entry in enumerate(entries):
        entry["rank"] = rank
    return entries


def _response_action_id(row: dict[str, Any]) -> str:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    return str(row.get("action_id") or action.get("action_id") or "")


def _response_status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "")


def audited_score_for_row(
    row: dict[str, Any],
    *,
    lambda_normal: dict[str, float] | None = None,
    success_statuses: tuple[str, ...] = DEFAULT_SUCCESS_STATUSES,
) -> float:
    if lambda_normal:
        response = response_map_from_row(row)
        return float(sum(float(v) * float(response.get(k, 0.0)) for k, v in lambda_normal.items()))
    return 1.0 if _response_status(row) in set(success_statuses) else 0.0


def should_escalate(
    *,
    best_audited: float,
    max_predicted_unaudited: float | None,
    budget_remaining: int,
    epsilon: float = 0.0,
    relaxed_value: float | None = None,
    gap_min: float = 0.0,
) -> dict[str, Any]:
    """No-regret escalation rule.

    Escalation is only justified while the optimistic upper bound of the
    unaudited pool exceeds the realized best; this is sound only insofar as
    predicted scores are admissible, which the calibration block in the stage
    summary is meant to monitor.
    """

    decision: dict[str, Any] = {
        "best_audited": float(best_audited),
        "max_predicted_unaudited": None if max_predicted_unaudited is None else float(max_predicted_unaudited),
        "budget_remaining": int(budget_remaining),
        "epsilon": float(epsilon),
        "relaxed_value": None if relaxed_value is None else float(relaxed_value),
        "gap_min": float(gap_min),
    }
    if max_predicted_unaudited is None:
        decision.update({"escalate": False, "reason": "no_candidates_remaining"})
        return decision
    if budget_remaining <= 0:
        decision.update({"escalate": False, "reason": "budget_exhausted"})
        return decision
    if max_predicted_unaudited <= best_audited + epsilon:
        decision.update({"escalate": False, "reason": "predicted_upper_bound_below_realized"})
        return decision
    if relaxed_value is not None and (relaxed_value - best_audited) <= gap_min:
        decision.update({"escalate": False, "reason": "relaxed_gap_closed"})
        return decision
    decision.update({"escalate": True, "reason": "upper_bound_above_realized"})
    return decision


def _default_audit_runner(
    *,
    stage_index: int,
    tasks: list[LeanTask],
    actions: list[TacticAction],
    stage_dir: Path,
    run_id: str,
    **runner_kwargs: Any,
) -> list[dict[str, Any]]:
    from .lean.worker_supervisor import enqueue_and_run_supervised_audit
    from .schemas import read_jsonl

    enqueue_and_run_supervised_audit(
        db_path=stage_dir / "audit_queue.sqlite",
        tasks=tasks,
        actions_by_task=actions,
        out_dir=stage_dir,
        run_id=f"{run_id}_stage{stage_index}",
        max_actions=len(actions),
        **runner_kwargs,
    )
    responses_path = stage_dir / "responses.jsonl"
    if not responses_path.exists():
        return []
    return [r for r in read_jsonl(responses_path) if isinstance(r, dict)]


def run_staged_audit(
    *,
    tasks: list[LeanTask],
    action_rows: list[dict[str, Any]],
    out_dir: str | Path,
    run_id: str,
    stage_caps: tuple[int, ...] = DEFAULT_STAGE_CAPS,
    budget_jobs: int | None = None,
    epsilon: float = 0.0,
    gap_min: float = 0.0,
    lambda_normal: dict[str, float] | None = None,
    relaxed_value: float | None = None,
    success_statuses: tuple[str, ...] = DEFAULT_SUCCESS_STATUSES,
    audit_runner: AuditRunner | None = None,
    plan_out: str | Path | None = None,
    rows_out: str | Path | None = None,
    summary_out: str | Path | None = None,
    **runner_kwargs: Any,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan_out = plan_out or out / "audit_stage_plan.json"
    rows_out = rows_out or out / "audit_stage_rows.jsonl"
    summary_out = summary_out or out / "audit_stage_summary.json"
    runner = audit_runner or _default_audit_runner

    ranked = rank_action_rows(action_rows)
    n_tasks = max(1, len(tasks))
    caps = sorted({min(int(c), len(ranked)) for c in stage_caps if int(c) > 0})

    plan = {
        "schema_version": SCHEMA_AUDIT_STAGE_PLAN,
        "run_id": run_id,
        "n_input": len(ranked),
        "n_tasks": len(tasks),
        "stage_caps": [int(c) for c in caps],
        "budget_jobs": None if budget_jobs is None else int(budget_jobs),
        "epsilon": float(epsilon),
        "gap_min": float(gap_min),
        "ranking": [
            {"action_id": e["action_id"], "rank": e["rank"], "predicted_score": e["predicted_score"]}
            for e in ranked
        ],
        "plan_hash": stable_hash(
            {
                "order": [e["action_id"] for e in ranked],
                "caps": [int(c) for c in caps],
                "budget_jobs": budget_jobs,
                "epsilon": float(epsilon),
                "gap_min": float(gap_min),
            },
            32,
        ),
        "canonical_status": "audit_stage_plan_is_schedule_not_canonical",
    }
    _json_dump(plan, plan_out)

    audited_by_action: dict[str, float] = {}
    stage_of_action: dict[str, int] = {}
    stages: list[dict[str, Any]] = []
    best_audited = 0.0
    jobs_used = 0
    n_underpredicted = 0
    max_underprediction = 0.0
    stop_reason: str | None = None
    cursor = 0

    for stage_index, cap in enumerate(caps):
        intended = cap - cursor
        chunk = ranked[cursor:cap]
        if not chunk:
            continue
        budget_remaining = (budget_jobs - jobs_used) if budget_jobs is not None else len(chunk) * n_tasks
        if stage_index > 0:
            decision = should_escalate(
                best_audited=best_audited,
                max_predicted_unaudited=chunk[0]["predicted_score"],
                budget_remaining=budget_remaining,
                epsilon=epsilon,
                relaxed_value=relaxed_value,
                gap_min=gap_min,
            )
            if not decision["escalate"]:
                stop_reason = str(decision["reason"])
                stages.append({"stage_index": stage_index, "cap": int(cap), "decision": decision, "n_actions": 0, "n_jobs": 0})
                break
        else:
            decision = {"escalate": True, "reason": "initial_stage"}
        # The job budget is enforced here at selection time, never delegated
        # to workers: a stage may only consume whole actions across all tasks.
        max_actions_in_budget = budget_remaining // n_tasks if budget_jobs is not None else len(chunk)
        if max_actions_in_budget <= 0:
            stop_reason = "budget_exhausted"
            stages.append(
                {
                    "stage_index": stage_index,
                    "cap": int(cap),
                    "decision": {"escalate": False, "reason": "budget_exhausted"},
                    "n_actions": 0,
                    "n_jobs": 0,
                }
            )
            break
        chunk = chunk[: int(max_actions_in_budget)]
        stage_dir = out / f"stage_{stage_index}"
        responses = runner(
            stage_index=stage_index,
            tasks=tasks,
            actions=[e["action"] for e in chunk],
            stage_dir=stage_dir,
            run_id=run_id,
            **runner_kwargs,
        )
        jobs_used += len(chunk) * n_tasks
        chunk_ids = {e["action_id"] for e in chunk}
        for row in responses:
            aid = _response_action_id(row)
            if aid not in chunk_ids:
                continue
            score = audited_score_for_row(row, lambda_normal=lambda_normal, success_statuses=success_statuses)
            audited_by_action[aid] = max(score, audited_by_action.get(aid, float("-inf")))
        predicted_by_id = {e["action_id"]: e["predicted_score"] for e in chunk}
        for entry in chunk:
            stage_of_action[entry["action_id"]] = stage_index
            audited = audited_by_action.get(entry["action_id"])
            if audited is not None:
                best_audited = max(best_audited, audited)
                under = audited - predicted_by_id[entry["action_id"]]
                if under > 0:
                    n_underpredicted += 1
                    max_underprediction = max(max_underprediction, under)
        stages.append(
            {
                "stage_index": stage_index,
                "cap": int(cap),
                "decision": decision,
                "n_actions": len(chunk),
                "n_jobs": len(chunk) * n_tasks,
                "best_audited_after": float(best_audited),
            }
        )
        cursor += len(chunk)
        if len(chunk) < intended:
            stop_reason = "budget_exhausted"
            break

    stage_rows: list[dict[str, Any]] = []
    n_audited_actions = 0
    n_skipped_actions = 0
    skip_reason = stop_reason or "stage_caps_exhausted"
    for entry in ranked:
        aid = entry["action_id"]
        if aid in stage_of_action:
            n_audited_actions += 1
            stage_rows.append(
                {
                    "schema_version": SCHEMA_AUDIT_STAGE_ROW,
                    "action_id": aid,
                    "rank": entry["rank"],
                    "predicted_score": entry["predicted_score"],
                    "state": "kernel_audited",
                    "stage_index": stage_of_action[aid],
                    "audited_score": audited_by_action.get(aid),
                    "canonical_status": "audit_stage_row_is_schedule_witness",
                }
            )
        else:
            n_skipped_actions += 1
            stage_rows.append(
                {
                    "schema_version": SCHEMA_AUDIT_STAGE_ROW,
                    "action_id": aid,
                    "rank": entry["rank"],
                    "predicted_score": entry["predicted_score"],
                    "state": "stage_skipped",
                    "stage_index": None,
                    "reason": skip_reason,
                    "canonical_status": "audit_stage_row_is_schedule_witness",
                }
            )
    write_jsonl(rows_out, stage_rows)

    summary = {
        "schema_version": SCHEMA_AUDIT_STAGE_PLAN,
        "run_id": run_id,
        "plan_hash": plan["plan_hash"],
        "n_input": len(ranked),
        "n_audited_actions": n_audited_actions,
        "n_skipped_actions": n_skipped_actions,
        "n_jobs_audited": int(jobs_used),
        "budget_jobs": None if budget_jobs is None else int(budget_jobs),
        "best_audited": float(best_audited),
        "stop_reason": stop_reason,
        "stages": stages,
        "calibration": {
            "n_underpredicted": int(n_underpredicted),
            "max_underprediction": float(max_underprediction),
        },
        "accounting_ok": bool(n_audited_actions + n_skipped_actions == len(ranked)),
        "plan_out": str(plan_out),
        "rows_out": str(rows_out),
        "canonical_status": "staged_audit_summary_is_schedule_not_canonical",
    }
    _json_dump(summary, summary_out)
    return summary


__all__ = [
    "DEFAULT_STAGE_CAPS",
    "SCHEMA_AUDIT_STAGE_PLAN",
    "SCHEMA_AUDIT_STAGE_ROW",
    "audited_score_for_row",
    "rank_action_rows",
    "run_staged_audit",
    "should_escalate",
]
