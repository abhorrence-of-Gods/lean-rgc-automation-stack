from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .crg_registry import load_repair_atoms
from .response_completion import load_completion
from .schemas import read_jsonl, stable_hash, write_records


SCHEMA_CRG_CANDIDATE = "lean-rgc-crg-candidate-v59.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _normal(problem: dict[str, Any]) -> dict[str, float]:
    obj = problem.get("objective") if isinstance(problem.get("objective"), dict) else {}
    normal = obj.get("lambda_normal") if isinstance(obj.get("lambda_normal"), dict) else {}
    return {str(k): _safe_float(v) for k, v in normal.items()}


def _cost(atom: dict[str, Any]) -> dict[str, float]:
    cv = atom.get("cost_vector") if isinstance(atom.get("cost_vector"), dict) else {}
    return {
        "cost": _safe_float(cv.get("cost"), 1.0),
        "audit_risk": _safe_float(cv.get("audit_risk"), 0.0),
        "source_risk": _safe_float(cv.get("source_risk"), 0.0),
        "ghost_risk": _safe_float(cv.get("ghost_risk"), 0.0),
        "hardening_cost": _safe_float(cv.get("hardening_cost"), 0.0),
    }


def _within_budget(atom: dict[str, Any], problem: dict[str, Any]) -> bool:
    b = problem.get("budget") if isinstance(problem.get("budget"), dict) else {}
    c = _cost(atom)
    checks = [
        ("cost", "cost_max"),
        ("audit_risk", "audit_risk_max"),
        ("source_risk", "source_risk_max"),
        ("ghost_risk", "ghost_risk_max"),
        ("hardening_cost", "hardening_cost_max"),
    ]
    return all(c[key] <= _safe_float(b.get(limit), float("inf")) for key, limit in checks)


def _response(atom: dict[str, Any]) -> dict[str, float]:
    obj = atom.get("response_embedding") if isinstance(atom.get("response_embedding"), dict) else {}
    return {str(k): _safe_float(v) for k, v in obj.items()}


def _dot(normal: dict[str, float], response: dict[str, float]) -> float:
    if len(normal) > len(response):
        return float(sum(float(v) * float(normal.get(k, 0.0)) for k, v in response.items()))
    return float(sum(float(v) * float(response.get(k, 0.0)) for k, v in normal.items()))


def _softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    if values.size == 0:
        return values
    temp = max(float(temperature), 1e-9)
    shifted = values / temp
    shifted = shifted - np.max(shifted)
    exp = np.exp(np.clip(shifted, -60.0, 60.0))
    total = float(exp.sum())
    if total <= 0.0 or not np.isfinite(total):
        return np.full(values.size, 1.0 / float(values.size), dtype=float)
    return exp / total


def _support_entry(atom: dict[str, Any], weight: float, score: float) -> dict[str, Any]:
    action = atom.get("candidate_action") if isinstance(atom.get("candidate_action"), dict) else {}
    return {
        "repair_atom_id": atom.get("repair_atom_id"),
        "species_id": atom.get("species_id"),
        "source": atom.get("source"),
        "source_id": atom.get("source_id"),
        "weight": float(weight),
        "predicted_score": float(score),
        "action_id": action.get("action_id"),
        "tactic": action.get("tactic"),
        "cost_vector": _cost(atom),
        "canonical_status": "support_atom_witness_not_canonical",
    }


def optimize_crg_problem_rows(
    problems: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    *,
    completion: dict[str, Any] | None = None,
    optimizer: str = "convex_mixture",
    temperature: float = 1.0,
    top_k: int = 16,
    cost_weight: float = 0.0,
    audit_weight: float = 0.0,
    source_weight: float = 0.0,
    ghost_weight: float = 0.0,
    hardening_weight: float = 0.0,
) -> list[dict[str, Any]]:
    completion = completion or {}
    out: list[dict[str, Any]] = []
    for problem in problems:
        normal = _normal(problem)
        feasible = [atom for atom in atoms if _within_budget(atom, problem)]
        scored: list[tuple[dict[str, Any], float, float]] = []
        for atom in feasible:
            c = _cost(atom)
            lambda_score = _dot(normal, _response(atom))
            net = (
                lambda_score
                - float(cost_weight) * c["cost"]
                - float(audit_weight) * c["audit_risk"]
                - float(source_weight) * c["source_risk"]
                - float(ghost_weight) * c["ghost_risk"]
                - float(hardening_weight) * c["hardening_cost"]
            )
            scored.append((atom, float(lambda_score), float(net)))
        scored.sort(key=lambda item: (item[2], item[1], str(item[0].get("repair_atom_id"))), reverse=True)
        if not scored:
            out.append(_empty_candidate(problem, normal, completion))
            continue
        kept = scored[: max(1, int(top_k))]
        if optimizer in {"linear", "linear_support", "LinearSupportOptimizer"}:
            weights = np.zeros(len(kept), dtype=float)
            weights[0] = 1.0
            optimizer_name = "LinearSupportOptimizer"
        elif optimizer in {"convex", "convex_mixture", "ConvexMixtureOptimizer"}:
            weights = _softmax(np.asarray([item[2] for item in kept], dtype=float), temperature=temperature)
            optimizer_name = "ConvexMixtureOptimizer"
        else:
            raise ValueError(f"unknown CRG optimizer: {optimizer}")
        support = [_support_entry(atom, float(w), lambda_score) for (atom, lambda_score, _), w in zip(kept, weights) if float(w) > 1e-12]
        relaxed_response: dict[str, float] = {}
        weighted_cost = {"cost": 0.0, "audit_risk": 0.0, "source_risk": 0.0, "ghost_risk": 0.0, "hardening_cost": 0.0}
        for (atom, _, _), w in zip(kept, weights):
            wf = float(w)
            for key, value in _response(atom).items():
                relaxed_response[key] = relaxed_response.get(key, 0.0) + wf * float(value)
            c = _cost(atom)
            for key in weighted_cost:
                weighted_cost[key] += wf * c[key]
        lambda_response = _dot(normal, relaxed_response)
        net_score = (
            lambda_response
            - float(cost_weight) * weighted_cost["cost"]
            - float(audit_weight) * weighted_cost["audit_risk"]
            - float(source_weight) * weighted_cost["source_risk"]
            - float(ghost_weight) * weighted_cost["ghost_risk"]
            - float(hardening_weight) * weighted_cost["hardening_cost"]
        )
        cid = "crg_cand_" + stable_hash({"problem": problem.get("problem_id"), "support": support, "optimizer": optimizer_name}, 16)
        out.append(
            {
                "schema_version": SCHEMA_CRG_CANDIDATE,
                "candidate_id": cid,
                "problem_id": problem.get("problem_id"),
                "parent_face_id": problem.get("parent_face_id"),
                "obstruction_id": problem.get("obstruction_id"),
                "optimizer_family": optimizer_name,
                "repair_species": "mixed_relaxed_species",
                "relaxed_object": {
                    "type": "mixture",
                    "support": support,
                    "response_embedding": dict(sorted(relaxed_response.items())),
                    "cost_vector": weighted_cost,
                },
                "decoded_candidates": [
                    {
                        "action_id": s.get("action_id"),
                        "tactic": s.get("tactic"),
                        "hardening_method": "support_topk_hint",
                    }
                    for s in support
                    if s.get("tactic")
                ],
                "scores": {
                    "lambda_response": float(lambda_response),
                    "cost": float(weighted_cost["cost"]),
                    "audit_risk": float(weighted_cost["audit_risk"]),
                    "source_risk": float(weighted_cost["source_risk"]),
                    "ghost_risk": float(weighted_cost["ghost_risk"]),
                    "hardening_cost": float(weighted_cost["hardening_cost"]),
                    "net_score": float(net_score),
                    "n_feasible_atoms": len(feasible),
                },
                "objective": problem.get("objective"),
                "budget": problem.get("budget"),
                "status": "relaxed_optimizer_witness",
                "canonical_status": "not_canonical_until_poms_promotion",
                "promotion_required": [
                    "parent_nonpaid",
                    "dual_certificate",
                    "least_repair",
                    "source_safe",
                    "audit_safe",
                    "cost_safe",
                ],
            }
        )
    return out


def _empty_candidate(problem: dict[str, Any], normal: dict[str, float], completion: dict[str, Any]) -> dict[str, Any]:
    cid = "crg_cand_" + stable_hash({"problem": problem.get("problem_id"), "empty": True}, 16)
    return {
        "schema_version": SCHEMA_CRG_CANDIDATE,
        "candidate_id": cid,
        "problem_id": problem.get("problem_id"),
        "parent_face_id": problem.get("parent_face_id"),
        "obstruction_id": problem.get("obstruction_id"),
        "optimizer_family": "NoFeasibleAtoms",
        "repair_species": "mixed_relaxed_species",
        "relaxed_object": {"type": "mixture", "support": [], "response_embedding": {}, "cost_vector": {}},
        "decoded_candidates": [],
        "scores": {
            "lambda_response": 0.0,
            "cost": 0.0,
            "audit_risk": 0.0,
            "source_risk": 0.0,
            "ghost_risk": 0.0,
            "hardening_cost": 0.0,
            "net_score": 0.0,
            "n_feasible_atoms": 0,
        },
        "objective": {"lambda_normal": normal, "response_completion_id": completion.get("probe_family_id")},
        "budget": problem.get("budget"),
        "status": "relaxed_optimizer_witness",
        "canonical_status": "not_canonical_until_poms_promotion",
        "promotion_required": ["parent_nonpaid", "dual_certificate", "least_repair", "source_safe", "audit_safe", "cost_safe"],
    }


def optimize_crg_candidates(
    *,
    problems_path: str | Path,
    registry_path: str | Path,
    out: str | Path,
    response_completion_path: str | Path | None = None,
    summary_out: str | Path | None = None,
    optimizer: str = "convex_mixture",
    temperature: float = 1.0,
    top_k: int = 16,
    cost_weight: float = 0.0,
    audit_weight: float = 0.0,
    source_weight: float = 0.0,
    ghost_weight: float = 0.0,
    hardening_weight: float = 0.0,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    problems = _read_rows(problems_path)
    atoms = load_repair_atoms(registry_path)
    completion = load_completion(response_completion_path)
    rows = optimize_crg_problem_rows(
        problems,
        atoms,
        completion=completion,
        optimizer=optimizer,
        temperature=temperature,
        top_k=top_k,
        cost_weight=cost_weight,
        audit_weight=audit_weight,
        source_weight=source_weight,
        ghost_weight=ghost_weight,
        hardening_weight=hardening_weight,
    )
    write_records(out, rows, schema_version=SCHEMA_CRG_CANDIDATE, run_id=run_id, parent_ids=parent_ids)
    summary = {
        "schema_version": SCHEMA_CRG_CANDIDATE,
        "out": str(out),
        "problems": str(problems_path),
        "registry": str(registry_path),
        "n_problems": len(problems),
        "n_atoms": len(atoms),
        "n_candidates": len(rows),
        "optimizer": optimizer,
        "top_k": int(top_k),
        "temperature": float(temperature),
        "canonical_status": "crg_optimizer_outputs_are_witnesses_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = [
    "SCHEMA_CRG_CANDIDATE",
    "optimize_crg_candidates",
    "optimize_crg_problem_rows",
]
