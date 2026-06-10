from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from .schemas import TacticAction, read_jsonl, stable_hash, write_jsonl


SCHEMA_AUDIT_PRUNE_REPORT = "lean-rgc-audit-prune-report-v65.0"


def normalize_tactic(tactic: str) -> str:
    lines: list[str] = []
    for raw in str(tactic or "").splitlines():
        line = raw.split("--", 1)[0].strip()
        if line:
            lines.append(line)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _meta(action: TacticAction) -> dict[str, Any]:
    return action.metadata if isinstance(action.metadata, dict) else {}


def _task_id(action: TacticAction, row: dict[str, Any]) -> str:
    meta = _meta(action)
    return str(row.get("task_id") or meta.get("task_id") or meta.get("source_task_id") or "*")


def _context_pair_signature(meta: dict[str, Any]) -> str | None:
    for key in ("context_pair", "bivariate_context_pair", "premise_context_pair"):
        value = meta.get(key)
        if value is not None:
            return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    src = meta.get("source_context_id")
    dst = meta.get("target_context_id")
    if src is not None or dst is not None:
        return json.dumps([src, dst], sort_keys=True, ensure_ascii=False, default=str)
    return None


def _crg_support_signature(meta: dict[str, Any]) -> str | None:
    support = meta.get("support_topk_signature") or meta.get("support_signature")
    if support is not None:
        return str(support)
    if meta.get("source") == "crg_hardening" or meta.get("candidate_id") or meta.get("support_repair_atom_id"):
        payload = {
            "problem_id": meta.get("problem_id"),
            "support_repair_atom_id": meta.get("support_repair_atom_id"),
            "hardening_method": meta.get("hardening_method"),
        }
        return stable_hash(payload, 24)
    return None


def candidate_prune_key(action: TacticAction, row: dict[str, Any]) -> str:
    meta = _meta(action)
    task_id = _task_id(action, row)
    norm = normalize_tactic(action.tactic)
    ctx = _context_pair_signature(meta)
    if ctx:
        core = meta.get("core_action_id") or meta.get("base_action_id") or meta.get("parent_action_id") or action.action_id
        return stable_hash({"kind": "contextual", "task_id": task_id, "context": ctx, "core": core, "tactic": norm}, 32)
    crg = _crg_support_signature(meta)
    if crg:
        return stable_hash({"kind": "crg", "task_id": task_id, "support": crg, "tactic": norm}, 32)
    return stable_hash({"kind": "tactic", "task_id": task_id, "tactic": norm}, 32)


def _candidate_score(action: TacticAction) -> float:
    meta = _meta(action)
    for key in (
        "audit_score",
        "promotion_score",
        "robust_margin",
        "score",
        "net_score",
        "relaxed_score",
        "lambda_response",
        "coker_surplus",
        "predicted_score",
    ):
        value = meta.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    scores = meta.get("scores")
    if isinstance(scores, dict):
        for key in ("net_score", "lambda_response", "relaxed_score", "score"):
            try:
                return float(scores.get(key))
            except (TypeError, ValueError):
                continue
    return 0.0


def _candidate_cost(action: TacticAction) -> float:
    try:
        return float(action.cost_estimate)
    except (TypeError, ValueError):
        return 1.0


def _row_action(row: dict[str, Any]) -> TacticAction:
    return TacticAction.from_dict(row)


def _baseline_ids_for(action: TacticAction) -> set[str]:
    meta = _meta(action)
    ids: set[str] = set()
    for key in ("baseline_action_id", "paired_baseline_action_id", "parent_action_id"):
        value = meta.get(key)
        if value:
            ids.add(str(value))
    extra = meta.get("required_baseline_action_ids")
    if isinstance(extra, list):
        ids.update(str(x) for x in extra if x)
    return ids


def prune_action_rows(rows: list[dict[str, Any]], *, n_tasks: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    actions = [_row_action(r) for r in rows]
    by_id = {a.action_id: (a, r) for a, r in zip(actions, rows)}
    best_by_key: dict[str, tuple[TacticAction, dict[str, Any], float, float]] = {}
    duplicate_count = 0
    dominated_count = 0
    for action, row in zip(actions, rows):
        key = candidate_prune_key(action, row)
        score = _candidate_score(action)
        cost = _candidate_cost(action)
        prev = best_by_key.get(key)
        if prev is None:
            best_by_key[key] = (action, row, score, cost)
            continue
        prev_action, prev_row, prev_score, prev_cost = prev
        if score > prev_score or (score == prev_score and cost < prev_cost):
            best_by_key[key] = (action, row, score, cost)
            dominated_count += 1
        else:
            duplicate_count += 1 if score == prev_score and cost == prev_cost else 0
            dominated_count += 0 if score == prev_score and cost == prev_cost else 1

    kept: dict[str, dict[str, Any]] = {a.action_id: r for a, r, _s, _c in best_by_key.values()}
    preserved = 0
    for action, _row, _score, _cost in list(best_by_key.values()):
        for bid in _baseline_ids_for(action):
            if bid in by_id and bid not in kept:
                kept[bid] = by_id[bid][1]
                preserved += 1
    output = [row for row in rows if str(row.get("action_id") or row.get("id") or "") in kept]
    n_input = len(rows)
    n_output = len(output)
    saved_per_task = max(0, n_input - n_output)
    estimated_jobs_saved = saved_per_task * max(1, int(n_tasks or 1))
    report = {
        "schema_version": SCHEMA_AUDIT_PRUNE_REPORT,
        "n_input": n_input,
        "n_output": n_output,
        "n_pruned": n_input - n_output,
        "n_pruned_duplicate": duplicate_count,
        "n_pruned_dominated": dominated_count,
        "n_baselines_preserved": preserved,
        "estimated_jobs_saved": estimated_jobs_saved,
    }
    return output, report


def prune_actions_file(
    actions_path: str | Path,
    out_path: str | Path,
    *,
    report_out: str | Path | None = None,
    n_tasks: int | None = None,
) -> dict[str, Any]:
    rows = [r for r in read_jsonl(actions_path) if isinstance(r, dict)]
    pruned, report = prune_action_rows(rows, n_tasks=n_tasks)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, pruned)
    report["input_path"] = str(actions_path)
    report["output_path"] = str(out)
    if report_out:
        p = Path(report_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


__all__ = [
    "SCHEMA_AUDIT_PRUNE_REPORT",
    "candidate_prune_key",
    "normalize_tactic",
    "prune_action_rows",
    "prune_actions_file",
]
