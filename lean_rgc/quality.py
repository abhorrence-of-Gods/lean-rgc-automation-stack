from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import csv
import json

from .schemas import read_jsonl
from .iteration import summarize_pipeline_dir


@dataclass
class QualityGate:
    name: str
    passed: bool
    value: float | int | str | None
    threshold: float | int | str | None
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityReport:
    run_dir: str
    status: str
    gates: list[QualityGate]
    recommendations: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"run_dir": self.run_dir, "status": self.status, "gates": [g.to_dict() for g in self.gates], "recommendations": self.recommendations, "metrics": self.metrics}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}



def _aggregate_round_json(root: Path, filename: str) -> dict[str, Any]:
    reps = [_read_json(p / filename) for p in sorted(root.glob("round_*")) if p.is_dir() and (p / filename).exists()]
    reps = [r for r in reps if r]
    if not reps:
        return {}
    out: dict[str, Any] = {"source": "round_aggregate", "n_reports": len(reps)}
    # Sum common count fields and aggregate rates where possible.
    for key in ["n_candidates", "n_accepted", "n_patches", "n_audited", "n_train_audited", "n_holdout_audited"]:
        vals = [r.get(key) for r in reps if isinstance(r.get(key), (int, float))]
        if vals:
            out[key] = sum(vals)
    if out.get("n_candidates"):
        out["accept_rate"] = float(out.get("n_accepted", 0)) / max(1.0, float(out["n_candidates"]))
    elif out.get("n_patches"):
        out["accept_rate"] = float(out.get("n_accepted", 0)) / max(1.0, float(out["n_patches"]))
    # Acceptance lineage stores summary under summary.
    if filename == "qgen_acceptance_lineage.json":
        sm = {"n_accepted_contexts": 0, "n_nodes": 0, "n_edges": 0}
        for r in reps:
            rs = r.get("summary") if isinstance(r.get("summary"), dict) else {}
            for k in list(sm):
                try:
                    sm[k] += int(rs.get(k, 0) or 0)
                except Exception:
                    pass
        out["summary"] = sm
    return out

def _last_jsonl(path: Path) -> dict[str, Any]:
    try:
        rows = read_jsonl(path)
        return rows[-1] if rows else {}
    except Exception:
        return {}


def _gate_ge(name: str, value: Any, threshold: float, severity: str, msg: str) -> QualityGate:
    try:
        v = float(value)
        ok = v >= threshold
    except Exception:
        v = None
        ok = False
    return QualityGate(name=name, passed=ok, value=v, threshold=threshold, severity=severity, message=msg)


def _gate_le(name: str, value: Any, threshold: float, severity: str, msg: str) -> QualityGate:
    try:
        v = float(value)
        ok = v <= threshold
    except Exception:
        v = None
        ok = False
    return QualityGate(name=name, passed=ok, value=v, threshold=threshold, severity=severity, message=msg)


def quality_gates_for_run(
    run_dir: str | Path,
    *,
    min_audits: int = 50,
    min_success_rate: float = 0.05,
    min_mean_goal_response: float = 0.0,
    min_registry_accept: int = 1,
    min_gamma_improvement: float | None = None,
    max_gamma_cocycle_rel: float | None = None,
    min_qgen_realized_match_rate: float | None = None,
    min_qgen_realized_success_rate: float | None = None,
    min_qgen_realized_goal_response: float | None = None,
    min_qgen_patch_audit_accept_rate: float | None = None,
) -> QualityReport:
    rd = Path(run_dir)
    metrics = summarize_pipeline_dir(rd)
    audit_summary = _read_json(rd / "audit" / "summary.json")
    pipeline = _read_json(rd / "pipeline_summary.json")
    frontier = _read_json(rd / "frontier" / "frontier_summary.json")
    registry = _read_json(rd / "registry_acceptance_report.json")
    carrier = _read_json(rd / "carrier_acceptance_summary.json")
    stage = _read_json(rd / "stage_coker_report.json")
    gamma = _last_jsonl(rd / "gamma_audit.jsonl")
    iracc = _read_json(rd / "ir_acceptance_report.json")
    qgen_lineage = _read_json(rd / "qgen_acceptance_lineage.json") or _aggregate_round_json(rd, "qgen_acceptance_lineage.json")
    qgen_robust = _read_json(rd / "qgen_robust_acceptance_report.json") or _aggregate_round_json(rd, "qgen_robust_acceptance_report.json")
    qgen_registry_robust = _read_json(rd / "qgen_registry_robust_acceptance_report.json") or _aggregate_round_json(rd, "qgen_registry_robust_acceptance_report.json")
    qgen_realized = _read_json(rd / "qgen_realized_calibration.json")
    qgen_patch_audit = _read_json(rd / "qgen_carrier_patch_audit_report.json") or _aggregate_round_json(rd, "qgen_carrier_patch_audit_report.json")
    poms_status = _read_json(rd / "poms_status_report.json")
    poms_promotion = _read_json(rd / "poms_promotion_report.json")
    full_metrics = {
        "pipeline": pipeline,
        "audit_summary": audit_summary,
        "frontier_summary": frontier,
        "registry_acceptance": registry,
        "carrier_acceptance": carrier,
        "stage_coker": stage,
        "gamma_last": gamma,
        "ir_acceptance": iracc,
        "qgen_acceptance_lineage": qgen_lineage,
        "qgen_robust_acceptance": qgen_robust,
        "qgen_registry_robust_acceptance": qgen_registry_robust,
        "qgen_realized_calibration": qgen_realized,
        "qgen_carrier_patch_audit": qgen_patch_audit,
        "poms_status": poms_status,
        "poms_promotion": poms_promotion,
        "compact": metrics,
    }
    n_audits = metrics.get("audit_n") or audit_summary.get("n") or audit_summary.get("n_responses") or 0
    success_rate = metrics.get("audit_success_rate")
    if success_rate is None:
        statuses = audit_summary.get("statuses") or {}
        success_rate = (statuses.get("success", 0) + statuses.get("partial", 0) + statuses.get("dry_run", 0)) / max(1, int(n_audits or 0))
    mean_goal = metrics.get("mean_goal_response") or audit_summary.get("mean_goal_response") or 0.0
    reg_acc = metrics.get("registry_accept_n") or registry.get("accepted") or registry.get("n_accepted") or 0
    gates: list[QualityGate] = [
        _gate_ge("audit_volume", n_audits, min_audits, "error", "Need enough micro-audits before interpreting R/Gamma/Carrier statistics."),
        _gate_ge("audit_success_rate", success_rate, min_success_rate, "warn", "Low success/partial rate usually means the action universe or exposure frontier is too weak."),
        _gate_ge("mean_goal_response", mean_goal, min_mean_goal_response, "warn", "Mean goal response should be non-negative after focused exposure on core tasks."),
        _gate_ge("registry_accepted", reg_acc, min_registry_accept, "info", "Registry-generated candidates should produce at least some positive coker-margin actions."),
    ]
    qgen_summary = qgen_lineage.get("summary", {}) if isinstance(qgen_lineage.get("summary"), dict) else {}
    if qgen_lineage:
        gates.append(_gate_ge("qgen_lineage_accepted_contexts", qgen_summary.get("n_accepted_contexts", 0), 0, "info", "QGEN acceptance lineage is a finite provenance chart; accepted contexts remain witnesses."))
    if qgen_robust:
        gates.append(_gate_ge("qgen_robust_accept_rate", qgen_robust.get("accept_rate", 0.0), 0.0, "info", "Robust coker acceptance is available for qgen candidates."))
    if qgen_registry_robust:
        gates.append(_gate_ge("qgen_registry_robust_accept_rate", qgen_registry_robust.get("accept_rate", 0.0), 0.0, "info", "Robust coker acceptance is available for qgen registry candidates."))
    if poms_promotion:
        promo_sum = poms_promotion.get("summary", {}) if isinstance(poms_promotion.get("summary"), dict) else {}
        forced_n = (promo_sum.get("by_promotion_status") or {}).get("forced_candidate", 0)
        canonical_n = (promo_sum.get("by_promotion_status") or {}).get("canonical_promoted", 0)
        gates.append(_gate_ge("poms_forced_candidates", forced_n, 0, "info", "POMS promotion report is available; forced candidates still require modal safety/canonical review."))
        gates.append(_gate_ge("poms_canonical_promoted", canonical_n, 0, "info", "Canonical promotions require explicit parent non-paid, dual, least-repair, and modal-safety certificates."))
    if min_gamma_improvement is not None:
        gates.append(_gate_ge("gamma_vs_persistence", gamma.get("gamma_vs_persistence_improvement"), min_gamma_improvement, "info", "Gamma should beat persistence before being used for control."))
    if max_gamma_cocycle_rel is not None:
        gates.append(_gate_le("gamma_cocycle_rel", gamma.get("cocycle_resid_rel"), max_gamma_cocycle_rel, "info", "Large cocycle residual means Gamma should remain diagnostic."))
    qreal_sum = qgen_realized.get("summary") if isinstance(qgen_realized.get("summary"), dict) else {}
    if min_qgen_realized_match_rate is not None:
        gates.append(_gate_ge("qgen_realized_match_rate", qreal_sum.get("match_rate"), min_qgen_realized_match_rate, "warn", "Accepted qgen actions should reappear in next-round audits before being trusted."))
    if min_qgen_realized_success_rate is not None:
        gates.append(_gate_ge("qgen_realized_success_rate_next", qreal_sum.get("success_rate_next"), min_qgen_realized_success_rate, "warn", "Accepted qgen actions should have positive next-round success evidence."))
    if min_qgen_realized_goal_response is not None:
        gates.append(_gate_ge("qgen_realized_mean_goal_response_next", qreal_sum.get("mean_goal_response_next"), min_qgen_realized_goal_response, "warn", "Accepted qgen actions should show non-negative next-round goal response."))
    if min_qgen_patch_audit_accept_rate is not None:
        gates.append(_gate_ge("qgen_carrier_patch_audit_accept_rate", qgen_patch_audit.get("accept_rate"), min_qgen_patch_audit_accept_rate, "warn", "QGEN carrier-incidence patches should pass audit before matrix merge is trusted."))
    recommendations: list[str] = []
    if not gates[0].passed:
        recommendations.append("Collect more audits or increase jobs/max-actions; do not promote components yet.")
    if not gates[1].passed:
        recommendations.append("Strengthen focused carrier exposure and state-dependent candidates before training a larger response model.")
    if not gates[2].passed:
        recommendations.append("Inspect frontier/exposure report; missing intro/constructor/premise carriers may still dominate.")
    if not gates[3].passed:
        recommendations.append("Run registry-candidates with audit and lower acceptance threshold, or inspect mined defect atoms for weak interventions.")
    gi = gamma.get("gamma_vs_persistence_improvement")
    if gi is not None:
        try:
            if float(gi) <= 0:
                recommendations.append("Keep Gamma in audit mode; it does not beat persistence on this run.")
        except Exception:
            pass
    if frontier and frontier.get("n_frontier_tasks", 0) == 0 and frontier.get("n_closed_by_exposure", 0) == 0:
        recommendations.append("Frontier normalization produced no usable frontier tasks; inspect exposure prefixes and Lean import mode.")
    if qgen_lineage and qgen_summary.get("n_accepted_contexts", 0) == 0:
        recommendations.append("QGEN produced lineage but no accepted contexts; inspect coker normals, carrier penalties, and candidate grammar.")
    if qgen_robust and qgen_robust.get("n_candidates", 0) and qgen_robust.get("n_accepted", 0) == 0:
        recommendations.append("Robust qgen coker rejected all candidates; compare train/holdout support and candidate uncertainty penalties.")
    if qgen_realized:
        qrs = qgen_realized.get("summary") or {}
        if qrs.get("match_rate") is not None and float(qrs.get("match_rate") or 0.0) < 0.5:
            recommendations.append("QGEN accepted actions have low next-round re-audit match rate; strengthen merge/provenance matching or audit accepted actions explicitly.")
        if qrs.get("mean_goal_response_next") is not None and float(qrs.get("mean_goal_response_next") or 0.0) < 0.0:
            recommendations.append("QGEN accepted actions have negative realized goal response; keep them witness-only and raise robust acceptance thresholds.")
    if qgen_patch_audit and qgen_patch_audit.get("accept_rate") is not None and float(qgen_patch_audit.get("accept_rate") or 0.0) <= 0.0:
        recommendations.append("No QGEN carrier patches passed audit; do not merge raw carrier patches into the carrier matrix.")
    status = "pass" if all(g.passed or g.severity == "info" for g in gates) else "needs_attention"
    return QualityReport(str(rd), status, gates, recommendations, full_metrics)


def write_quality_report(report: QualityReport, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> QualityReport:
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["name", "passed", "value", "threshold", "severity", "message"])
            w.writeheader()
            for g in report.gates:
                w.writerow(g.to_dict())
    return report


__all__ = ["quality_gates_for_run", "write_quality_report", "QualityReport", "QualityGate"]
