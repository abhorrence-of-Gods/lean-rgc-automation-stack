from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import csv

from .schemas import read_jsonl


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return len(read_jsonl(path))
    except Exception:
        return 0


def _last_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    rows = read_jsonl(path)
    return rows[-1] if rows else {}


def _flatten_for_csv(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    def rec(prefix: str, val: Any):
        if isinstance(val, dict):
            for k, v in val.items():
                rec(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(val, (list, tuple)):
            out[prefix] = json.dumps(val, ensure_ascii=False)
        else:
            out[prefix] = val
    rec("", row)
    return out


def collect_iteration_report(run_dir: str | Path, *, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> dict[str, Any]:
    root = Path(run_dir)
    summary = _read_json(root / "iterate_summary.json")
    round_dirs = sorted([p for p in root.glob("round_*" ) if p.is_dir()])
    rounds: list[dict[str, Any]] = []
    for rdir in round_dirs:
        audit_summary = _read_json(rdir / "audit" / "summary.json")
        pipeline_summary = _read_json(rdir / "pipeline_summary.json")
        registry_report = _read_json(rdir / "registry_acceptance_report.json")
        carrier_summary = _read_json(rdir / "carrier_acceptance_summary.json")
        frontier_summary = _read_json(rdir / "frontier" / "frontier_summary.json")
        gamma_last = _last_jsonl(rdir / "gamma_audit.jsonl")
        action_report = _read_json(rdir / "action_report.json")
        qgen_lineage = _read_json(rdir / "qgen_acceptance_lineage.json")
        qgen_robust = _read_json(rdir / "qgen_robust_acceptance_report.json")
        qgen_registry_robust = _read_json(rdir / "qgen_registry_robust_acceptance_report.json")
        row: dict[str, Any] = {
            "round_dir": str(rdir),
            "round": int(rdir.name.split("_")[-1]) if rdir.name.split("_")[-1].isdigit() else len(rounds),
            "n_responses": audit_summary.get("n") or audit_summary.get("n_responses") or 0,
            "success_rate": audit_summary.get("success_rate"),
            "mean_response_norm": audit_summary.get("mean_response_norm"),
            "mean_goal_response": audit_summary.get("mean_goal_response"),
            "mean_carrier_delta": audit_summary.get("mean_carrier_delta"),
            "statuses": audit_summary.get("statuses", {}),
            "registry_accepted": _count_jsonl(rdir / "registry_accepted_actions.jsonl"),
            "registry_candidates": _count_jsonl(rdir / "registry_candidates.jsonl"),
            "carrier_promoted": _count_jsonl(rdir / "carrier_promoted_actions.jsonl"),
            "carrier_actions": _count_jsonl(rdir / "carrier_actions.jsonl"),
            "premise_actions": _count_jsonl(rdir / "premise_actions.jsonl"),
            "next_actions": _count_jsonl(root / f"{rdir.name}_actions_next.jsonl"),
            "registry_acceptance": registry_report,
            "carrier_acceptance": carrier_summary,
            "frontier_summary": frontier_summary,
            "gamma_last": gamma_last,
            "pipeline_files": pipeline_summary.get("pipeline_files", {}),
            "action_report": action_report,
            "qgen_acceptance_lineage": qgen_lineage.get("summary", {}) if qgen_lineage else {},
            "qgen_robust_acceptance": qgen_robust,
            "qgen_registry_robust_acceptance": qgen_registry_robust,
            "qgen_robust_accepted": _count_jsonl(rdir / "qgen_robust_accepted_actions.jsonl"),
            "qgen_registry_robust_accepted": _count_jsonl(rdir / "qgen_registry_robust_accepted_actions.jsonl"),
        }
        rounds.append(row)
    # simple trend fields
    trends: dict[str, Any] = {}
    if rounds:
        for key in ["success_rate", "mean_goal_response", "mean_response_norm", "mean_carrier_delta"]:
            vals = [r.get(key) for r in rounds if r.get(key) is not None]
            if vals:
                trends[key] = {"first": vals[0], "last": vals[-1], "delta": vals[-1] - vals[0] if len(vals) > 1 else 0.0}
    qgen_realized = _read_json(root / "qgen_realized_calibration.json")
    if qgen_realized:
        trends["qgen_realized_match_rate"] = (qgen_realized.get("summary") or {}).get("match_rate")
        trends["qgen_realized_mean_goal_response_next"] = (qgen_realized.get("summary") or {}).get("mean_goal_response_next")
        trends["qgen_realized_success_rate_next"] = (qgen_realized.get("summary") or {}).get("success_rate_next")
    rep = {"run_dir": str(root), "iterate_summary": summary, "rounds": rounds, "trends": trends}
    if qgen_realized:
        rep["qgen_realized_calibration"] = qgen_realized
    poms_status = _read_json(root / "poms_status_report.json")
    if poms_status:
        rep["poms_status"] = poms_status
        trends["poms_by_status"] = (poms_status.get("summary") or {}).get("by_status")
    poms_promotion = _read_json(root / "poms_promotion_report.json")
    if poms_promotion:
        rep["poms_promotion"] = poms_promotion
        trends["poms_by_promotion_status"] = (poms_promotion.get("summary") or {}).get("by_promotion_status")
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        flat = [_flatten_for_csv(r) for r in rounds]
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        keys: list[str] = []
        for r in flat:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in flat:
                writer.writerow(r)
    return rep


__all__ = ["collect_iteration_report"]
