from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import LeanTask, TacticAction, read_jsonl, write_jsonl, stable_hash
from .carrier_exposure import CarrierNormalizer


def exposure_actions_for_tasks(tasks_path: str | Path, out: str | Path, *, include_identity: bool = False, import_mode: str = "preserve") -> dict[str, Any]:
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(tasks_path)]
    norm = CarrierNormalizer()
    rows: list[dict[str, Any]] = []
    for task in tasks:
        for exp in norm.expose(task):
            if not include_identity and not exp.prefix_tactic.strip():
                continue
            tactic = exp.prefix_tactic.strip() or "skip"
            aid = "exposure_" + stable_hash({"task": task.task_id, "prefix": tactic, "kind": exp.kind}, 12)
            action = TacticAction(
                action_id=aid,
                tactic=tactic,
                tactic_class="exposure",
                carrier_tags=list(exp.carrier_tags),
                cost_estimate=float(exp.cost),
                metadata={
                    "generated_by": "carrier_exposure_only",
                    "prefix_id": exp.prefix_id,
                    "prefix_tactic": exp.prefix_tactic,
                    "prefix_kind": exp.kind,
                    "exposure": exp.to_dict(),
                    "task_id": task.task_id,
                },
            )
            d = action.to_dict(); d["task_id"] = task.task_id
            rows.append(d)
    write_jsonl(out, rows)
    return {"n_actions": len(rows), "out": str(out)}


def summarize_exposure_audit(audit_dir: str | Path, out: str | Path) -> dict[str, Any]:
    audit_dir = Path(audit_dir)
    responses = read_jsonl(audit_dir / "responses.jsonl") if (audit_dir / "responses.jsonl").exists() else []
    by_kind: dict[str, dict[str, Any]] = {}
    for r in responses:
        action = r.get("action") or {}
        meta = action.get("metadata") or {}
        kind = meta.get("prefix_kind") or action.get("tactic_class") or "unknown"
        item = by_kind.setdefault(kind, {"n": 0, "success": 0, "partial": 0, "goal_response": 0.0, "carrier_delta": 0.0})
        item["n"] += 1
        status = str(r.get("audit_status") or r.get("status") or "")
        if status in {"success", "dry_run"}:
            item["success"] += 1
        if status in {"partial", "partial_success"}:
            item["partial"] += 1
        resp = r.get("response") or {}
        item["goal_response"] += sum(float(v) for k, v in resp.items() if str(k).startswith("goal."))
        cd = r.get("carrier_delta") or {}
        if isinstance(cd, dict):
            item["carrier_delta"] += sum(float(v) for v in cd.values())
    rows = []
    for kind, item in sorted(by_kind.items()):
        n = max(1, int(item["n"]))
        rows.append({
            "prefix_kind": kind,
            "n": item["n"],
            "success_rate": item["success"] / n,
            "partial_rate": item["partial"] / n,
            "mean_goal_response": item["goal_response"] / n,
            "mean_carrier_delta": item["carrier_delta"] / n,
        })
    rep = {"n_responses": len(responses), "by_prefix_kind": rows}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(__import__("json").dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep


__all__ = ["exposure_actions_for_tasks", "summarize_exposure_audit"]
