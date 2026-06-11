from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import json

from ..schemas import LeanTask, TacticAction, stable_hash, write_jsonl
from .arms import render_feedback


SCHEMA_EVAL_EPISODE = "lean-rgc-eval-episode-v88.0"
SCHEMA_EVAL_ATTEMPT = "lean-rgc-eval-attempt-v88.0"

DEFAULT_SUCCESS_STATUSES = ("success", "proved", "advanced", "ok", "succeeded")

# proposal_fn(task=..., attempt_index=..., feedback=...) -> list of action dicts
ProposalFn = Callable[..., list[dict[str, Any]]]
# wave_audit_runner(wave_index=..., tasks=..., actions_by_task=..., wave_dir=..., run_id=...) -> response rows
WaveAuditRunner = Callable[..., list[dict[str, Any]]]


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def select_task_subset(rows: list[dict[str, Any]], *, n: int, seed: int = 0) -> list[dict[str, Any]]:
    """Deterministic benchmark subset: order by hash of (task_id, seed)."""

    keyed = sorted(
        rows,
        key=lambda r: stable_hash({"task_id": str(r.get("task_id") or ""), "seed": int(seed)}, 24),
    )
    return keyed[: max(0, int(n))]


def _response_task_id(row: dict[str, Any]) -> str:
    task = row.get("task") if isinstance(row.get("task"), dict) else {}
    state = row.get("state") if isinstance(row.get("state"), dict) else {}
    return str(row.get("task_id") or task.get("task_id") or state.get("task_id") or "")


def _response_status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "")


def _response_error_text(row: dict[str, Any]) -> str:
    for key in ("messages", "lean_messages", "errors", "message", "last_error"):
        value = row.get(key)
        if isinstance(value, list) and value:
            return " | ".join(str(v) for v in value if str(v).strip())
        if isinstance(value, str) and value.strip():
            return value
    audit = row.get("audit") if isinstance(row.get("audit"), dict) else {}
    for key in ("messages", "message", "stderr_tail"):
        value = audit.get(key)
        if isinstance(value, list) and value:
            return " | ".join(str(v) for v in value if str(v).strip())
        if isinstance(value, str) and value.strip():
            return value
    return _response_status(row)


def _default_wave_audit_runner(
    *,
    wave_index: int,
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]],
    wave_dir: Path,
    run_id: str,
    **runner_kwargs: Any,
) -> list[dict[str, Any]]:
    from ..lean.worker_supervisor import enqueue_and_run_supervised_audit
    from ..schemas import read_jsonl

    max_actions = max((len(v) for v in actions_by_task.values()), default=0)
    enqueue_and_run_supervised_audit(
        db_path=wave_dir / "audit_queue.sqlite",
        tasks=tasks,
        actions_by_task=actions_by_task,
        out_dir=wave_dir,
        run_id=f"{run_id}_wave{wave_index}",
        max_actions=max(1, max_actions),
        **runner_kwargs,
    )
    responses_path = wave_dir / "responses.jsonl"
    if not responses_path.exists():
        return []
    return [r for r in read_jsonl(responses_path) if isinstance(r, dict)]


def run_eval(
    *,
    tasks: list[LeanTask],
    arm: str,
    proposal_fn: ProposalFn,
    out_dir: str | Path,
    run_id: str,
    budget_calls: int = 8,
    success_statuses: tuple[str, ...] = DEFAULT_SUCCESS_STATUSES,
    wave_audit_runner: WaveAuditRunner | None = None,
    signal_packet_fn: Callable[..., str] | None = None,
    summary_out: str | Path | None = None,
    **runner_kwargs: Any,
) -> dict[str, Any]:
    """Run fixed-budget eval episodes with wavefront scheduling.

    Attempt k of every unsolved theorem is generated and audited as one
    batch, so sequential per-theorem feedback loops still amortize Lean
    imports across the whole wave.
    """

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    runner = wave_audit_runner or _default_wave_audit_runner
    success = set(success_statuses)

    states: dict[str, dict[str, Any]] = {
        task.task_id: {
            "task": task,
            "solved": False,
            "attempts_used": 0,
            "audit_pass_count": 0,
            "n_failed": 0,
            "last_errors": [],
            "first_solve_attempt": None,
        }
        for task in tasks
    }
    attempt_rows: list[dict[str, Any]] = []

    for wave_index in range(max(0, int(budget_calls))):
        unsolved = [s for s in states.values() if not s["solved"]]
        if not unsolved:
            break
        actions_by_task: dict[str, list[TacticAction]] = {}
        for state in unsolved:
            task: LeanTask = state["task"]
            if signal_packet_fn is not None:
                state["signal_packet_text"] = signal_packet_fn(task=task, state=state)
            feedback = render_feedback(arm, state)
            proposals = proposal_fn(task=task, attempt_index=wave_index, feedback=feedback)
            actions: list[TacticAction] = []
            for i, row in enumerate(proposals or []):
                row = dict(row)
                row.setdefault("action_id", f"eval_{task.task_id}_w{wave_index}_{i}")
                actions.append(TacticAction.from_dict(row))
            actions_by_task[task.task_id] = actions
            state["attempts_used"] += 1
        wave_tasks = [s["task"] for s in unsolved]
        responses = runner(
            wave_index=wave_index,
            tasks=wave_tasks,
            actions_by_task=actions_by_task,
            wave_dir=out / f"wave_{wave_index}",
            run_id=run_id,
            **runner_kwargs,
        )
        rows_by_task: dict[str, list[dict[str, Any]]] = {}
        for row in responses:
            tid = _response_task_id(row)
            if tid:
                rows_by_task.setdefault(tid, []).append(row)
        for state in unsolved:
            task = state["task"]
            rows = rows_by_task.get(task.task_id, [])
            passed = [r for r in rows if _response_status(r) in success]
            state["audit_pass_count"] += len(passed)
            if passed:
                state["solved"] = True
                if state["first_solve_attempt"] is None:
                    state["first_solve_attempt"] = wave_index + 1
            else:
                state["n_failed"] += 1
                state["last_errors"] = [_response_error_text(r) for r in rows][:8]
            state["last_responses"] = rows
            attempt_rows.append(
                {
                    "schema_version": SCHEMA_EVAL_ATTEMPT,
                    "run_id": run_id,
                    "arm": arm,
                    "task_id": task.task_id,
                    "wave_index": wave_index,
                    "n_actions": len(actions_by_task.get(task.task_id, [])),
                    "n_responses": len(rows),
                    "n_passed": len(passed),
                    "solved": bool(passed),
                }
            )

    episode_rows: list[dict[str, Any]] = []
    for task in tasks:
        state = states[task.task_id]
        episode_rows.append(
            {
                "schema_version": SCHEMA_EVAL_EPISODE,
                "episode_id": "ep_" + stable_hash({"run": run_id, "task": task.task_id, "arm": arm}, 16),
                "run_id": run_id,
                "arm": arm,
                "task_id": task.task_id,
                "solved": bool(state["solved"]),
                "attempts_used": int(state["attempts_used"]),
                "llm_calls": int(state["attempts_used"]),
                "audit_pass_count": int(state["audit_pass_count"]),
                "first_solve_attempt": state["first_solve_attempt"],
                "budget_calls": int(budget_calls),
                "canonical_status": "eval_episode_witness_not_canonical",
            }
        )
    write_jsonl(out / "episodes.jsonl", episode_rows)
    write_jsonl(out / "attempts.jsonl", attempt_rows)

    n_solved = sum(1 for r in episode_rows if r["solved"])
    total_calls = sum(r["llm_calls"] for r in episode_rows)
    summary = {
        "schema_version": SCHEMA_EVAL_EPISODE,
        "run_id": run_id,
        "arm": arm,
        "n_tasks": len(tasks),
        "n_solved": n_solved,
        "solve_rate": (n_solved / len(tasks)) if tasks else 0.0,
        "total_llm_calls": int(total_calls),
        "audit_pass_per_call": (
            sum(r["audit_pass_count"] for r in episode_rows) / total_calls if total_calls else 0.0
        ),
        "budget_calls": int(budget_calls),
        "episodes_out": str(out / "episodes.jsonl"),
        "attempts_out": str(out / "attempts.jsonl"),
        "canonical_status": "eval_summary_is_measurement_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = [
    "DEFAULT_SUCCESS_STATUSES",
    "SCHEMA_EVAL_ATTEMPT",
    "SCHEMA_EVAL_EPISODE",
    "run_eval",
    "select_task_subset",
]
