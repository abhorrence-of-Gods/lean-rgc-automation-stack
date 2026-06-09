from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl


SCHEMA_HARDENING_GAP_REPORT = "lean-rgc-hardening-gap-report-v60.0"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def build_hardening_gap_report(
    *,
    crg_audit_rows_path: str | Path,
    out: str | Path,
    relaxed_positive_threshold: float = 0.0,
    hard_positive_threshold: float = 0.0,
) -> dict[str, Any]:
    rows = [r for r in read_jsonl(crg_audit_rows_path) if isinstance(r, dict)]
    cases: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in rows:
        relaxed = _safe_float(row.get("relaxed_score"))
        hard = _safe_float(row.get("audited_score"))
        if relaxed > relaxed_positive_threshold and hard <= hard_positive_threshold:
            classification = "grammar_defect_candidate"
        elif relaxed > relaxed_positive_threshold and hard > hard_positive_threshold:
            classification = "hardening_realized"
        elif relaxed <= relaxed_positive_threshold:
            classification = "relaxed_nonpositive"
        else:
            classification = "open"
        counts[classification] = counts.get(classification, 0) + 1
        cases.append(
            {
                "candidate_id": row.get("candidate_id"),
                "problem_id": row.get("problem_id"),
                "relaxed_score": relaxed,
                "audited_score": hard,
                "hardening_gap": _safe_float(row.get("hardening_gap")),
                "classification": classification,
                "canonical_status": "hardening_gap_case_is_diagnostic_not_canonical",
            }
        )
    report = {
        "schema_version": SCHEMA_HARDENING_GAP_REPORT,
        "crg_audit_rows": str(crg_audit_rows_path),
        "n_rows": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "grammar_defect_candidates": [case for case in cases if case["classification"] == "grammar_defect_candidate"],
        "cases": cases,
        "canonical_status": "hardening_gap_report_is_grammar_diagnostic_not_canonical",
    }
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


__all__ = ["SCHEMA_HARDENING_GAP_REPORT", "build_hardening_gap_report"]
