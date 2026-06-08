from __future__ import annotations

from pathlib import Path
from typing import Any
import math

from .schemas import DefectVector, read_jsonl, write_jsonl


def defect_from_ir_row(row: dict[str, Any]) -> DefectVector:
    goals = row.get("goals") or []
    goal = {
        "num_goals": float(len(goals)),
        "unsolved_goal_flag": float(len(goals) > 0),
        "total_goal_size_log": float(math.log1p(sum(len(str(g.get("target", ""))) for g in goals))),
        "hyp_count_log": float(math.log1p(sum(len(g.get("hypotheses") or []) for g in goals))),
    }
    type_d = {
        "metavar_count_log": float(math.log1p(sum(float((g.get("features") or {}).get("has_metavar", 0.0)) for g in goals))),
        "typeclass_pending": float(any("missing_typeclass_instance" in (g.get("carrier_atoms") or []) for g in goals)),
    }
    search = {
        "branch_factor_est": float(sum(1.0 for g in goals if g.get("target_head") in {"and", "or", "exists"})),
        "constructor_branch_debt": float(any("constructor_branch_debt" in (g.get("carrier_atoms") or []) for g in goals)),
    }
    carrier: dict[str, float] = {}
    for g in goals:
        for atom in g.get("carrier_atoms") or []:
            carrier[str(atom)] = carrier.get(str(atom), 0.0) + 1.0
    audit = {"ir_chart": 1.0}
    flat_keys: list[str] = []
    flat: list[float] = []
    for group_name, dct in [("goal", goal), ("type", type_d), ("search", search), ("carrier", carrier), ("audit", audit)]:
        for k in sorted(dct):
            flat_keys.append(f"{group_name}.{k}")
            flat.append(float(dct[k]))
    return DefectVector(goal=goal, type=type_d, search=search, carrier=carrier, audit=audit, flat=flat, flat_keys=flat_keys, quotient_meta={"source": "proof_ir", "ir_version": row.get("source", "unknown")})


def ir_defects_file(ir_path: str | Path, out_path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(ir_path):
        d = defect_from_ir_row(row)
        rows.append({"state_id": row.get("state_id"), "task_id": row.get("task_id"), "defect": d.to_dict(), **d.to_dict()})
    write_jsonl(out_path, rows)
    return rows
