from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import numpy as np

from ..schemas import read_jsonl


SCHEMA_EVAL_REPORT = "lean-rgc-eval-report-v88.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _episodes_by_task(path: str | Path) -> dict[str, dict[str, Any]]:
    rows = [r for r in read_jsonl(path) if isinstance(r, dict)]
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        tid = str(row.get("task_id") or "")
        if tid:
            out[tid] = row
    return out


def _arm_metrics(episodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n = len(episodes)
    n_solved = sum(1 for r in episodes.values() if r.get("solved"))
    calls = sum(int(r.get("llm_calls") or 0) for r in episodes.values())
    passes = sum(int(r.get("audit_pass_count") or 0) for r in episodes.values())
    return {
        "n_tasks": n,
        "n_solved": n_solved,
        "solve_rate": (n_solved / n) if n else 0.0,
        "total_llm_calls": calls,
        "audit_pass_per_call": (passes / calls) if calls else 0.0,
    }


def _paired_bootstrap(
    deltas: np.ndarray,
    *,
    n_bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = deltas.size
    if n == 0:
        return {"mean_delta": 0.0, "ci_low": 0.0, "ci_high": 0.0, "ci_excludes_zero": False}
    idx = rng.integers(0, n, size=(int(n_bootstrap), n))
    means = deltas[idx].mean(axis=1)
    ci_low = float(np.percentile(means, 2.5))
    ci_high = float(np.percentile(means, 97.5))
    return {
        "mean_delta": float(deltas.mean()),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_excludes_zero": bool(ci_low > 0.0 or ci_high < 0.0),
        "n_bootstrap": int(n_bootstrap),
    }


def build_eval_report(
    *,
    episodes_paths: dict[str, str | Path],
    out: str | Path,
    n_bootstrap: int = 10000,
    seed: int = 0,
) -> dict[str, Any]:
    """Paired comparison of eval arms over an identical task set."""

    by_arm = {arm: _episodes_by_task(path) for arm, path in episodes_paths.items()}
    task_sets = {arm: set(eps.keys()) for arm, eps in by_arm.items()}
    base_tasks: set[str] | None = None
    for arm, tasks in task_sets.items():
        if base_tasks is None:
            base_tasks = tasks
        elif tasks != base_tasks:
            missing = sorted(base_tasks.symmetric_difference(tasks))[:5]
            raise ValueError(f"eval arms cover different task sets; paired comparison invalid (e.g. {missing})")
    task_ids = sorted(base_tasks or set())

    arms = sorted(by_arm.keys())
    comparisons: list[dict[str, Any]] = []
    for i, arm_a in enumerate(arms):
        for arm_b in arms[i + 1 :]:
            deltas = np.asarray(
                [
                    float(bool(by_arm[arm_a][tid].get("solved"))) - float(bool(by_arm[arm_b][tid].get("solved")))
                    for tid in task_ids
                ],
                dtype=float,
            )
            stats = _paired_bootstrap(deltas, n_bootstrap=n_bootstrap, seed=seed)
            comparisons.append({"arm_a": arm_a, "arm_b": arm_b, "metric": "solve_rate", **stats})

    report = {
        "schema_version": SCHEMA_EVAL_REPORT,
        "n_tasks": len(task_ids),
        "seed": int(seed),
        "arms": {arm: _arm_metrics(eps) for arm, eps in by_arm.items()},
        "paired_comparisons": comparisons,
        "episodes_paths": {arm: str(p) for arm, p in episodes_paths.items()},
        "canonical_status": "eval_report_is_measurement_not_canonical",
    }
    _json_dump(report, out)
    return report


__all__ = ["SCHEMA_EVAL_REPORT", "build_eval_report"]
