from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import csv
import json

from .schemas import read_jsonl, write_jsonl, TacticAction
from .candidate_acceptance import accept_candidate_rows, summarize_acceptance


@dataclass
class StageCokerStageSummary:
    name: str
    path: str
    n_candidates: int
    n_accepted: int
    accept_rate: float
    mean_margin: float
    max_margin: float
    mean_goal_gain: float
    mean_carrier_gain: float
    status_counts: dict[str, int]
    accepted_by_source: dict[str, int]
    accepted_by_atom: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StageCokerReport:
    base_responses: str
    stages: list[StageCokerStageSummary]
    n_accepted_total: int
    n_actions_out: int
    out_actions: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_stage_arg(x: str) -> tuple[str, str]:
    if "=" in x:
        name, path = x.split("=", 1)
        return name.strip() or Path(path).stem, path.strip()
    p = Path(x)
    return p.stem, str(p)


def _action_from_acceptance_row(r: dict[str, Any]) -> dict[str, Any] | None:
    if not r.get("accepted"):
        return None
    meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
    action = meta.get("action") if isinstance(meta.get("action"), dict) else None
    if action is None:
        action = r.get("action") if isinstance(r.get("action"), dict) else None
    if action is None:
        tactic = r.get("tactic")
        if not tactic:
            return None
        action = {
            "action_id": r.get("action_id") or str(abs(hash(str(tactic)))),
            "tactic": tactic,
            "tactic_class": "accepted",
            "carrier_tags": [],
            "cost_estimate": r.get("cost", 1.0),
            "metadata": {},
        }
    action = dict(action)
    if r.get("task_id") and not action.get("task_id"):
        action["task_id"] = r.get("task_id")
        action.setdefault("metadata", {})["task_id"] = r.get("task_id")
    action.setdefault("metadata", {})["stage_coker_margin"] = r.get("coker_margin_proxy", r.get("margin"))
    action.setdefault("metadata", {})["stage_coker_source"] = r.get("generated_by") or "stage_coker"
    return TacticAction.from_dict(action).to_dict()


def _dedup_actions(rows: list[dict[str, Any]], *, max_actions: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    # Prefer larger stage margin.
    rows = sorted(rows, key=lambda r: float((r.get("metadata") or {}).get("stage_coker_margin") or 0.0), reverse=True)
    for r in rows:
        task_id = str(r.get("task_id") or (r.get("metadata") or {}).get("task_id") or "")
        tactic = str(r.get("tactic") or "")
        key = (task_id, tactic)
        if not tactic or key in seen:
            continue
        seen.add(key)
        out.append(r)
        if max_actions is not None and len(out) >= max_actions:
            break
    return out


def run_stage_coker(
    base_responses: str | Path,
    stages: list[str | tuple[str, str | Path]],
    *,
    out_report: str | Path | None = None,
    out_actions: str | Path | None = None,
    out_rows_dir: str | Path | None = None,
    out_csv: str | Path | None = None,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.25,
    audit_penalty: float = 1.0,
    require_success: bool = False,
    max_actions: int | None = None,
) -> StageCokerReport:
    base = read_jsonl(base_responses)
    stage_summaries: list[StageCokerStageSummary] = []
    accepted_actions: list[dict[str, Any]] = []
    out_rows_path = Path(out_rows_dir) if out_rows_dir else None
    if out_rows_path:
        out_rows_path.mkdir(parents=True, exist_ok=True)
    for s in stages:
        if isinstance(s, tuple):
            name, path = str(s[0]), str(s[1])
        else:
            name, path = _parse_stage_arg(str(s))
        p = Path(path)
        cand = read_jsonl(p) if p.exists() else []
        records = accept_candidate_rows(
            base,
            cand,
            margin_threshold=margin_threshold,
            cost_weight=cost_weight,
            carrier_weight=carrier_weight,
            audit_penalty=audit_penalty,
            require_success=require_success,
        )
        rows = [r.to_dict() for r in records]
        if out_rows_path:
            write_jsonl(out_rows_path / f"{name}_stage_coker_rows.jsonl", rows)
        summ = summarize_acceptance(records).to_dict()
        stage_summaries.append(StageCokerStageSummary(
            name=name,
            path=str(p),
            n_candidates=int(summ.get("n", 0)),
            n_accepted=int(summ.get("accepted", 0)),
            accept_rate=float(summ.get("accepted", 0)) / max(1, int(summ.get("n", 0))),
            mean_margin=float(summ.get("mean_margin", 0.0)),
            max_margin=float(summ.get("max_margin", 0.0)),
            mean_goal_gain=float(sum(float(r.get("goal_gain", 0.0)) for r in rows) / max(1, len(rows))),
            mean_carrier_gain=float(sum(float(r.get("carrier_gain", 0.0)) for r in rows) / max(1, len(rows))),
            status_counts=dict(summ.get("status_counts", {})),
            accepted_by_source=dict(summ.get("accepted_by_source", {})),
            accepted_by_atom=dict(summ.get("accepted_by_atom", {})),
        ))
        for r in rows:
            a = _action_from_acceptance_row(r)
            if a is not None:
                a.setdefault("metadata", {})["stage_coker_stage"] = name
                accepted_actions.append(a)
    dedup = _dedup_actions(accepted_actions, max_actions=max_actions)
    if out_actions:
        write_jsonl(out_actions, dedup)
    rep = StageCokerReport(
        base_responses=str(base_responses),
        stages=stage_summaries,
        n_accepted_total=sum(s.n_accepted for s in stage_summaries),
        n_actions_out=len(dedup),
        out_actions=str(out_actions) if out_actions else None,
    )
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            fields = ["name", "path", "n_candidates", "n_accepted", "accept_rate", "mean_margin", "max_margin", "mean_goal_gain", "mean_carrier_gain"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for s in stage_summaries:
                d = s.to_dict()
                w.writerow({k: d.get(k) for k in fields})
    return rep


__all__ = ["run_stage_coker", "StageCokerReport", "StageCokerStageSummary"]
