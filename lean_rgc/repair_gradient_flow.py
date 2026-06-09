from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .crg_optimizer import optimize_crg_problem_rows
from .crg_registry import load_repair_atoms
from .response_completion import load_completion
from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_REPAIR_FLOW_STEP = "lean-rgc-repair-flow-step-v61.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _support_map(candidate: dict[str, Any] | None) -> dict[str, float]:
    if not candidate:
        return {}
    relaxed = candidate.get("relaxed_object") if isinstance(candidate.get("relaxed_object"), dict) else {}
    out: dict[str, float] = {}
    for row in relaxed.get("support") or []:
        if isinstance(row, dict) and row.get("repair_atom_id"):
            out[str(row.get("repair_atom_id"))] = float(row.get("weight") or 0.0)
    return out


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    keys = sorted(set(a) | set(b))
    if not keys:
        return 0.0
    va = np.asarray([float(a.get(k, 0.0)) for k in keys], dtype=float)
    vb = np.asarray([float(b.get(k, 0.0)) for k in keys], dtype=float)
    return float(np.linalg.norm(va - vb))


def _blend(prev: dict[str, float], cur: dict[str, float], tau: float) -> dict[str, float]:
    keys = sorted(set(prev) | set(cur))
    if not keys:
        return {}
    tau = max(float(tau), 1e-9)
    w_cur = tau / (1.0 + tau)
    out = {k: (1.0 - w_cur) * float(prev.get(k, 0.0)) + w_cur * float(cur.get(k, 0.0)) for k in keys}
    total = sum(max(0.0, v) for v in out.values())
    if total <= 0.0:
        return cur
    return {k: max(0.0, v) / total for k, v in out.items() if max(0.0, v) > 1e-12}


def repair_gradient_flow_steps(
    *,
    problems_path: str | Path,
    registry_path: str | Path,
    out: str | Path,
    response_completion_path: str | Path | None = None,
    previous_candidates_path: str | Path | None = None,
    summary_out: str | Path | None = None,
    tau: float = 1.0,
    steps: int = 1,
    top_k: int = 16,
) -> dict[str, Any]:
    problems = _read_rows(problems_path)
    atoms = load_repair_atoms(registry_path)
    completion = load_completion(response_completion_path)
    previous_candidates = _read_rows(previous_candidates_path)
    prev_by_problem = {str(row.get("problem_id")): row for row in previous_candidates}
    rows: list[dict[str, Any]] = []
    current_prev = dict(prev_by_problem)
    for step in range(1, max(1, int(steps)) + 1):
        optimized = optimize_crg_problem_rows(
            problems,
            atoms,
            completion=completion,
            optimizer="convex_mixture",
            temperature=max(float(tau), 1e-9),
            top_k=top_k,
        )
        for cand in optimized:
            pid = str(cand.get("problem_id"))
            prev = current_prev.get(pid)
            prev_map = _support_map(prev)
            opt_map = _support_map(cand)
            new_map = _blend(prev_map, opt_map, tau)
            prox = _l2(prev_map, new_map)
            objective_gain = float((cand.get("scores") or {}).get("lambda_response") or 0.0) - float(((prev or {}).get("scores") or {}).get("lambda_response") or 0.0)
            new_repair_id = "rel_flow_" + stable_hash({"problem": pid, "step": step, "weights": new_map}, 14)
            rows.append(
                {
                    "schema_version": SCHEMA_REPAIR_FLOW_STEP,
                    "flow_id": "rgf_" + stable_hash({"problem": pid, "step": step}, 14),
                    "problem_id": pid,
                    "step": step,
                    "previous_repair_id": (prev or {}).get("candidate_id"),
                    "new_repair_id": new_repair_id,
                    "lambda_id": cand.get("obstruction_id"),
                    "proximal_distance": float(prox),
                    "objective_gain": float(objective_gain),
                    "cost_delta": float((cand.get("scores") or {}).get("cost") or 0.0) - float(((prev or {}).get("scores") or {}).get("cost") or 0.0),
                    "audit_risk_delta": float((cand.get("scores") or {}).get("audit_risk") or 0.0) - float(((prev or {}).get("scores") or {}).get("audit_risk") or 0.0),
                    "relaxed_weights": new_map,
                    "status": "flow_step_witness",
                    "canonical_status": "repair_gradient_flow_step_witness_not_canonical",
                }
            )
            current_prev[pid] = cand
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_REPAIR_FLOW_STEP,
        "out": str(out),
        "n_steps": len(rows),
        "tau": float(tau),
        "top_k": int(top_k),
        "canonical_status": "repair_gradient_flow_is_dynamic_witness_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_REPAIR_FLOW_STEP", "repair_gradient_flow_steps"]
