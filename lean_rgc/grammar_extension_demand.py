from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_GRAMMAR_EXTENSION_DEMAND = "lean-rgc-grammar-extension-demand-v87.0"

TRIGGER_RELAXED_POSITIVE_HARD_ZERO = "relaxed_positive_hard_zero"


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _dominant_species(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return "unknown_species"
    relaxed = candidate.get("relaxed_object") if isinstance(candidate.get("relaxed_object"), dict) else {}
    weight_by_species: dict[str, float] = {}
    for supp in relaxed.get("support") or []:
        if not isinstance(supp, dict):
            continue
        species = str(supp.get("species_id") or "")
        if species:
            weight_by_species[species] = weight_by_species.get(species, 0.0) + _safe_float(supp.get("weight"))
    if weight_by_species:
        return max(weight_by_species.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return str(candidate.get("repair_species") or "unknown_species")


def _missing_capability(species: str, attempt: dict[str, Any] | None) -> dict[str, str]:
    hard = (attempt or {}).get("hard_candidates") or []
    status = str((attempt or {}).get("hardening_status") or "")
    if attempt is None or status == "failed" or not hard:
        # Nothing decodable came out of the relaxed object: the missing move
        # is a decoder for this species, not a better tactic.
        return {"kind": "decoder", "name": f"{species}_to_lean_decoder"}
    return {"kind": "tactic_template", "name": f"{species}_tactic_template"}


def _demand_id(species: str, kind: str) -> str:
    # Keyed by capability only so the same demand accumulates evidence
    # across runs instead of forking per run.
    return "ged_" + stable_hash({"species": species, "kind": kind}, 14)


def _case_from_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(row.get("candidate_id") or ""),
        "problem_id": row.get("problem_id"),
        "parent_face_id": row.get("parent_face_id"),
        "obstruction_id": row.get("obstruction_id"),
        "relaxed_score": _safe_float(row.get("relaxed_score")),
        "audited_score": _safe_float(row.get("audited_score")),
        "hardening_gap": _safe_float(row.get("hardening_gap")),
    }


def _demand_row(species: str, capability: dict[str, str], cases: list[dict[str, Any]]) -> dict[str, Any]:
    cases = sorted(cases, key=lambda c: (-c["hardening_gap"], c["candidate_id"]))
    total_gap = float(sum(c["hardening_gap"] for c in cases))
    return {
        "schema_version": SCHEMA_GRAMMAR_EXTENSION_DEMAND,
        "demand_id": _demand_id(species, capability["kind"]),
        "trigger": TRIGGER_RELAXED_POSITIVE_HARD_ZERO,
        "dominant_species": species,
        "missing_capability": dict(capability),
        "evidence": {
            "n_cases": len(cases),
            "total_hardening_gap": total_gap,
            "max_relaxed_score": float(max((c["relaxed_score"] for c in cases), default=0.0)),
            "candidate_ids": [c["candidate_id"] for c in cases],
            "failure_signature_ids": [],
            "example": cases[0] if cases else None,
        },
        "required_signature": {
            "input": ["relaxed_object", "local_goal_state", "available_hypotheses"],
            "output": ["auditable_tactic"],
            "constraints": ["no_sorry", "no_unknown_identifier", "source_safe"],
        },
        "free_generator_proxy": {
            "generator_id": "g_" + stable_hash({"species": species, "kind": capability["kind"]}, 12),
            "description": f"hardening map for relaxed {species} repairs into auditable Lean candidates",
        },
        "priority": total_gap,
        "cases": cases,
        "canonical_status": "grammar_demand_witness_not_canonical",
    }


def _merge_demand_rows(existing: list[dict[str, Any]], fresh: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in existing + fresh:
        did = str(row.get("demand_id") or "")
        if not did:
            continue
        if did not in by_id:
            by_id[did] = row
            continue
        base = by_id[did]
        merged_cases: dict[str, dict[str, Any]] = {}
        for case in (base.get("cases") or []) + (row.get("cases") or []):
            if isinstance(case, dict) and case.get("candidate_id"):
                merged_cases[str(case["candidate_id"])] = case
        by_id[did] = _demand_row(
            str(base.get("dominant_species") or "unknown_species"),
            dict(base.get("missing_capability") or {"kind": "decoder", "name": "unknown"}),
            list(merged_cases.values()),
        )
    return sorted(by_id.values(), key=lambda r: (-_safe_float(r.get("priority")), str(r.get("demand_id"))))


def build_grammar_extension_demands(
    *,
    crg_audit_rows_path: str | Path,
    out: str | Path,
    candidates_path: str | Path | None = None,
    hardening_attempts_path: str | Path | None = None,
    relaxed_positive_threshold: float = 0.0,
    hard_positive_threshold: float = 0.0,
    merge_existing: bool = True,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    audit_rows = _read_rows(crg_audit_rows_path)
    candidate_by_id = {str(r.get("candidate_id") or ""): r for r in _read_rows(candidates_path)}
    attempt_by_candidate = {str(r.get("candidate_id") or ""): r for r in _read_rows(hardening_attempts_path)}

    n_trigger = 0
    n_excluded_underaudited = 0
    cases_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    capability_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in audit_rows:
        relaxed = _safe_float(row.get("relaxed_score"))
        hard = _safe_float(row.get("audited_score"))
        if not (relaxed > relaxed_positive_threshold and hard <= hard_positive_threshold):
            continue
        coverage = str(row.get("audit_coverage") or "full")
        if coverage != "full":
            n_excluded_underaudited += 1
            continue
        n_trigger += 1
        cid = str(row.get("candidate_id") or "")
        species = _dominant_species(candidate_by_id.get(cid))
        capability = _missing_capability(species, attempt_by_candidate.get(cid))
        key = (species, capability["kind"])
        cases_by_key.setdefault(key, []).append(_case_from_audit_row(row))
        capability_by_key[key] = capability

    fresh = [
        _demand_row(species, capability_by_key[(species, kind)], cases)
        for (species, kind), cases in cases_by_key.items()
    ]
    existing = _read_rows(out) if merge_existing else []
    demands = _merge_demand_rows(existing, fresh)
    write_jsonl(out, demands)

    summary = {
        "schema_version": SCHEMA_GRAMMAR_EXTENSION_DEMAND,
        "crg_audit_rows": str(crg_audit_rows_path),
        "out": str(out),
        "n_audit_rows": len(audit_rows),
        "n_trigger_cases": n_trigger,
        "n_excluded_underaudited": n_excluded_underaudited,
        "n_demands": len(demands),
        "n_merged_existing": len(existing),
        "top_demands": [
            {
                "demand_id": r["demand_id"],
                "dominant_species": r["dominant_species"],
                "missing_capability": r["missing_capability"],
                "priority": r["priority"],
                "n_cases": r["evidence"]["n_cases"],
            }
            for r in demands[:5]
        ],
        "canonical_status": "grammar_demand_ledger_is_diagnostic_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = [
    "SCHEMA_GRAMMAR_EXTENSION_DEMAND",
    "TRIGGER_RELAXED_POSITIVE_HARD_ZERO",
    "build_grammar_extension_demands",
]
