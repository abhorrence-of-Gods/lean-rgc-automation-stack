
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import csv
import json
import math

import numpy as np

from .schemas import read_jsonl


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _response_vec(row: dict[str, Any]) -> np.ndarray:
    try:
        if isinstance(row.get("response_flat"), list):
            return np.asarray(row.get("response_flat") or [], dtype=float)
        if isinstance(row.get("response"), dict):
            return np.asarray([float(row["response"][k]) for k in sorted(row["response"])], dtype=float)
    except Exception:
        pass
    return np.zeros(0, dtype=float)


def _goal_response(row: dict[str, Any]) -> float:
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        return float(sum(float(v) for k, v in resp.items() if str(k).startswith("goal.")))
    return 0.0


def _carrier_delta(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if isinstance(cd, dict):
        return float(sum(float(v) for v in cd.values()))
    return 0.0


def _action_source(row: dict[str, Any]) -> str:
    a = row.get("action") if isinstance(row.get("action"), dict) else {}
    m = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    if m.get("generated_by"):
        return str(m.get("generated_by"))
    if m.get("prefix_kind") or m.get("prefix_tactic"):
        return "carrier_exposure"
    if a.get("tactic_class"):
        return str(a.get("tactic_class"))
    return "unknown"


@dataclass
class StageSummary:
    name: str
    path: str
    n: int
    success_rate: float
    positive_goal_rate: float
    mean_response_norm: float
    mean_goal_response: float
    mean_carrier_delta: float
    statuses: dict[str, int]
    by_source: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_response_file(path: str | Path, name: str | None = None) -> StageSummary:
    p = Path(path)
    rows = read_jsonl(p) if p.exists() else []
    statuses: dict[str, int] = {}
    norms: list[float] = []
    goals: list[float] = []
    carriers: list[float] = []
    by_src: dict[str, dict[str, Any]] = {}
    for r in rows:
        st = _status(r)
        statuses[st] = statuses.get(st, 0) + 1
        rv = _response_vec(r)
        rn = float(np.linalg.norm(rv)) if rv.size else 0.0
        gr = _goal_response(r)
        cd = _carrier_delta(r)
        norms.append(rn); goals.append(gr); carriers.append(cd)
        src = _action_source(r)
        d = by_src.setdefault(src, {"n": 0, "success": 0, "mean_goal_response": 0.0, "mean_response_norm": 0.0, "mean_carrier_delta": 0.0})
        d["n"] += 1
        d["success"] += int(st in {"success", "partial", "dry_run"})
        d["mean_goal_response"] += gr
        d["mean_response_norm"] += rn
        d["mean_carrier_delta"] += cd
    for d in by_src.values():
        n = max(1, int(d["n"]))
        d["success_rate"] = d["success"] / n
        d["mean_goal_response"] /= n
        d["mean_response_norm"] /= n
        d["mean_carrier_delta"] /= n
    n = len(rows)
    success = statuses.get("success", 0) + statuses.get("partial", 0) + statuses.get("dry_run", 0)
    return StageSummary(
        name=name or p.stem,
        path=str(p),
        n=n,
        success_rate=float(success / max(1, n)),
        positive_goal_rate=float(sum(1 for x in goals if x > 0) / max(1, n)),
        mean_response_norm=float(np.mean(norms)) if norms else 0.0,
        mean_goal_response=float(np.mean(goals)) if goals else 0.0,
        mean_carrier_delta=float(np.mean(carriers)) if carriers else 0.0,
        statuses=statuses,
        by_source=by_src,
    )


def write_stage_report(stages: list[tuple[str, str | Path]], out_json: str | Path, out_csv: str | Path | None = None) -> dict[str, Any]:
    summaries = [summarize_response_file(path, name=name).to_dict() for name, path in stages]
    rep = {"n_stages": len(summaries), "stages": summaries}
    outp = Path(out_json); outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        csvp = Path(out_csv); csvp.parent.mkdir(parents=True, exist_ok=True)
        keys = ["name", "path", "n", "success_rate", "positive_goal_rate", "mean_response_norm", "mean_goal_response", "mean_carrier_delta"]
        with csvp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for s in summaries:
                w.writerow({k: s.get(k) for k in keys})
    return rep


def default_pipeline_stages(run_dir: str | Path) -> list[tuple[str, Path]]:
    rd = Path(run_dir)
    candidates = [
        ("base", rd / "audit" / "responses.jsonl"),
        ("exposure", rd / "exposure_audit" / "responses.jsonl"),
        ("registry", rd / "registry_audit" / "responses.jsonl"),
        ("qgen", rd / "qgen_audit" / "responses.jsonl"),
        ("carrier_quotient", rd / "carrier_quotient_audit" / "responses.jsonl"),
        ("contextual_probe", rd / "contextual_probe_audit" / "responses.jsonl"),
        ("action_geometry", rd / "action_geometry_audit" / "responses.jsonl"),
        ("failure_signature", rd / "failure_signature_audit" / "responses.jsonl"),
        ("ir", rd / "ir_audit" / "responses.jsonl"),
        ("premise", rd / "premise_audit" / "responses.jsonl"),
        ("premise_response", rd / "premise_response_audit" / "responses.jsonl"),
        ("arithmetic_teacher", rd / "arithmetic_teacher_audit" / "responses.jsonl"),
        ("arithmetic_teacher_kernel", rd / "arithmetic_teacher" / "kernel_transition_audit" / "arithmetic_teacher_kernel_responses.jsonl"),
        ("carrier_accept", rd / "carrier_acceptance.jsonl"),
    ]
    return [(n, p) for n, p in candidates if p.exists()]


__all__ = ["summarize_response_file", "write_stage_report", "default_pipeline_stages", "StageSummary"]
