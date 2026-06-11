from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

from .response_completion import response_map_from_row
from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_CRG_AUDIT = "lean-rgc-crg-audit-row-v85.0"


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
        out = float(value)
    except Exception:
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def _normal(candidate: dict[str, Any]) -> dict[str, float]:
    obj = candidate.get("objective") if isinstance(candidate.get("objective"), dict) else {}
    normal = obj.get("lambda_normal") if isinstance(obj.get("lambda_normal"), dict) else {}
    return {str(k): _safe_float(v) for k, v in normal.items()}


def _dot(normal: dict[str, float], response: dict[str, float]) -> float:
    return float(sum(float(v) * float(response.get(k, 0.0)) for k, v in normal.items()))


def _action_id(row: dict[str, Any]) -> str:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    return str(row.get("action_id") or action.get("action_id") or row.get("tactic") or action.get("tactic") or "")


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _carrier_safe(row: dict[str, Any]) -> bool:
    cd = row.get("carrier_delta") if isinstance(row.get("carrier_delta"), dict) else {}
    audit = row.get("audit") if isinstance(row.get("audit"), dict) else {}
    if _safe_float(audit.get("unsafe"), 0.0) > 0.0:
        return False
    return all(_safe_float(v) >= -1e-12 for v in cd.values())


def _candidate_to_actions(attempts: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for attempt in attempts:
        cid = str(attempt.get("candidate_id") or "")
        if not cid:
            continue
        ids: list[str] = []
        for hard in attempt.get("hard_candidates") or []:
            if isinstance(hard, dict) and hard.get("action_id"):
                ids.append(str(hard.get("action_id")))
        out.setdefault(cid, []).extend(ids)
    return out


def _promotion_readiness(
    *,
    audited_score: float,
    hardening_gap: float,
    ghost_risk: float,
    source_safe: bool,
    carrier_safe: bool,
    max_hardening_gap: float,
    max_ghost_risk: float,
) -> str:
    if audited_score <= 0.0:
        return "witness_only"
    if not (source_safe and carrier_safe):
        return "paid_witness"
    if hardening_gap <= max_hardening_gap and ghost_risk <= max_ghost_risk:
        return "promotion_candidate"
    return "paid_witness"


def audit_crg_candidates(
    *,
    candidates_path: str | Path,
    hardening_attempts_path: str | Path,
    out_rows: str | Path,
    audited_responses_path: str | Path | None = None,
    poms_out: str | Path | None = None,
    summary_out: str | Path | None = None,
    max_hardening_gap: float = 0.25,
    max_ghost_risk: float = 0.25,
) -> dict[str, Any]:
    candidates = _read_rows(candidates_path)
    attempts = _read_rows(hardening_attempts_path)
    responses = _read_rows(audited_responses_path)
    actions_by_candidate = _candidate_to_actions(attempts)
    response_by_action: dict[str, list[dict[str, Any]]] = {}
    for row in responses:
        aid = _action_id(row)
        if aid:
            response_by_action.setdefault(aid, []).append(row)

    audit_rows: list[dict[str, Any]] = []
    poms_rows: list[dict[str, Any]] = []
    for cand in candidates:
        cid = str(cand.get("candidate_id") or "")
        normal = _normal(cand)
        relaxed_score = _safe_float((cand.get("scores") or {}).get("lambda_response"), 0.0)
        hard_ids = actions_by_candidate.get(cid, [])
        unique_hard_ids = list(dict.fromkeys(hard_ids))
        n_hard_total = len(unique_hard_ids)
        n_hard_audited = sum(1 for aid in unique_hard_ids if response_by_action.get(aid))
        # n_hard_total == 0 means hardening decoded nothing, so a zero hard
        # value is a true statement about the hard grammar, not missing audit.
        if n_hard_total == 0 or n_hard_audited == n_hard_total:
            audit_coverage = "full"
        elif n_hard_audited == 0:
            audit_coverage = "none"
        else:
            audit_coverage = "partial"
        hard_scores: list[float] = []
        hard_statuses: list[str] = []
        carrier_flags: list[bool] = []
        for aid in hard_ids:
            for row in response_by_action.get(aid, []):
                hard_scores.append(_dot(normal, response_map_from_row(row)))
                hard_statuses.append(_status(row))
                carrier_flags.append(_carrier_safe(row))
        if hard_scores:
            audited_score = max(hard_scores)
            heldout_score = min(hard_scores)
        else:
            # No audit rows means hardening has not realized the relaxed
            # prediction yet. Keep this conservative: zero hard value.
            audited_score = 0.0
            heldout_score = 0.0
        hardening_gap = max(0.0, relaxed_score - audited_score)
        denom = abs(relaxed_score) + 1e-9
        ghost_risk = min(1.0, hardening_gap / denom) if relaxed_score > 0 else 0.0
        bad_statuses = {"timeout", "unsafe", "elab_error"}
        source_safe = not any(status in bad_statuses for status in hard_statuses)
        carrier_safe = all(carrier_flags) if carrier_flags else True
        readiness = _promotion_readiness(
            audited_score=audited_score,
            hardening_gap=hardening_gap,
            ghost_risk=ghost_risk,
            source_safe=source_safe,
            carrier_safe=carrier_safe,
            max_hardening_gap=max_hardening_gap,
            max_ghost_risk=max_ghost_risk,
        )
        # Budget-skipped hardening must not be promotable: an unaudited hard
        # action could contradict the audited subset.
        if audit_coverage != "full" and readiness == "promotion_candidate":
            readiness = "paid_witness"
        row = {
            "schema_version": SCHEMA_CRG_AUDIT,
            "candidate_id": cid,
            "problem_id": cand.get("problem_id"),
            "parent_face_id": cand.get("parent_face_id"),
            "obstruction_id": cand.get("obstruction_id"),
            "hard_action_ids": hard_ids,
            "audit_coverage": audit_coverage,
            "n_hard_actions_total": int(n_hard_total),
            "n_hard_actions_audited": int(n_hard_audited),
            "relaxed_score": float(relaxed_score),
            "audited_score": float(audited_score),
            "hardening_gap": float(hardening_gap),
            "heldout_score": float(heldout_score),
            "ghost_risk": float(ghost_risk),
            "source_safe": bool(source_safe),
            "carrier_safe": bool(carrier_safe),
            "promotion_readiness": readiness,
            "canonical_status": "not_canonical_without_parent_nonpaid_dual_least",
        }
        audit_rows.append(row)
        poms_rows.append(
            {
                "schema_version": "lean-rgc-promotion-evidence-v38.0",
                "id": "crg_ev_" + stable_hash({"candidate": cid, "audit": row}, 14),
                "evidence_kind": "crg_audit_witness",
                "source": "crg_audit",
                "action_id": hard_ids[0] if hard_ids else cid,
                "tactic": None,
                "residual_key": str(cand.get("obstruction_id") or cand.get("problem_id") or cid),
                "parent_residual_keys": [str(cand.get("obstruction_id") or cand.get("problem_id") or cid)],
                "parent_obstruction": str(cand.get("obstruction_id") or cand.get("problem_id") or cid),
                "parent_nonpaid": False,
                "dual_certificate": bool(relaxed_score > 0.0),
                "least_repair": False,
                "parent_paid": False,
                "confidence": float(max(0.0, min(1.0, audited_score / (abs(relaxed_score) + 1e-9)))) if relaxed_score else 0.0,
                "reason": "crg_audit_bridge_witness_parent_nonpaid_and_least_repair_not_declared",
                "canonical_status": "promotion_evidence_for_poms_not_canonical",
                "provenance": {"crg_audit_row": row},
            }
        )

    write_jsonl(out_rows, audit_rows)
    if poms_out:
        write_jsonl(poms_out, poms_rows)
    summary = {
        "schema_version": SCHEMA_CRG_AUDIT,
        "candidates": str(candidates_path),
        "hardening_attempts": str(hardening_attempts_path),
        "audited_responses": str(audited_responses_path) if audited_responses_path else None,
        "out_rows": str(out_rows),
        "poms_out": str(poms_out) if poms_out else None,
        "n_candidates": len(candidates),
        "n_audit_rows": len(audit_rows),
        "n_promotion_candidates": sum(1 for row in audit_rows if row.get("promotion_readiness") == "promotion_candidate"),
        "coverage_counts": {
            key: sum(1 for row in audit_rows if row.get("audit_coverage") == key)
            for key in ("full", "partial", "none")
        },
        "canonical_status": "crg_audit_is_witness_chart_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_CRG_AUDIT", "audit_crg_candidates"]
