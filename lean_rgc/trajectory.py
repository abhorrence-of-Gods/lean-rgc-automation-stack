from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import numpy as np

from .schemas import LeanTask, ProofState, TacticAction, TrajectoryRecord, TrajectoryStep as SchemaTrajectoryStep, write_jsonl
from .lean.executor import LeanExecutor
from .defects import ProofDefectExtractor
from .candidates import TacticCandidateGenerator
from .carrier_exposure import StateDependentCandidateGenerator
from .carrier import LeanCarrierAlgebra
from .response_model import ResponseModel
from .gamma import GammaAuditor


@dataclass
class TrajectoryRunnerConfig:
    max_steps: int = 8
    max_candidates: int = 32
    carrier_budget: float = 10.0
    carrier_mode: str = "constraint"
    response_mode: str = "mean"
    cost_weight: float = 0.1
    append_partial_success: bool = True


@dataclass
class TrajectoryStep:
    state_id: str
    action_id: str
    defect_before: list[float]
    pred_response: list[float]
    defect_after: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class TrajectoryAuditReport:
    n_steps: int
    gamma_report: dict[str, Any]
    reports: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class TrajectoryAuditor:
    def audit(self, steps: list[TrajectoryStep], *, fit_gamma: bool = True, horizon: int = 4) -> TrajectoryAuditReport:
        if not steps:
            return TrajectoryAuditReport(0, {}, [])
        D = np.stack([np.asarray(s.defect_before, dtype=float) for s in steps])
        R = np.stack([np.asarray(s.pred_response, dtype=float) for s in steps])
        N = np.stack([np.asarray(s.defect_after, dtype=float) for s in steps])
        auditor = GammaAuditor()
        G = auditor.fit_linear_gamma(D - R, N) if fit_gamma and len(steps) >= 2 else np.eye(D.shape[1])
        reps = [auditor.audit(D[i], R[i], N[i], G, horizon=horizon).__dict__ for i in range(len(steps))]
        keys = ["cocycle_resid_norm", "cocycle_resid_rel", "persistence_resid_norm", "gamma_vs_persistence_improvement"]
        summary = {k: float(np.mean([r[k] for r in reps])) for k in keys}
        summary["spectral_radius_proxy"] = reps[-1].get("spectral_radius_proxy")
        return TrajectoryAuditReport(len(steps), summary, reps)


def write_trajectories(path: str | Path, records: list[TrajectoryRecord]) -> None:
    write_jsonl(path, [r.to_dict() for r in records])


class LeanTrajectoryRunner:
    def __init__(self, executor: LeanExecutor, candidate_generator: TacticCandidateGenerator | None = None, response_model: ResponseModel | None = None, config: TrajectoryRunnerConfig | None = None):
        self.executor = executor
        self.gen = candidate_generator or StateDependentCandidateGenerator()
        self.response_model = response_model
        self.config = config or TrajectoryRunnerConfig()
        self.extractor = ProofDefectExtractor()
        self.carrier = LeanCarrierAlgebra()

    def run_task(self, task: LeanTask) -> TrajectoryRecord:
        state = ProofState.from_task(task)
        prefix_lines: list[str] = []
        rec = TrajectoryRecord(task_id=task.task_id, final_status="failed", steps=[], prefix="")
        for step_idx in range(self.config.max_steps):
            cur_task = LeanTask(**{**task.to_dict(), "prefix": "\n".join(prefix_lines)})
            before = self.extractor.extract(state)
            before_vec = before.as_numpy()
            actions = self.gen.candidates(cur_task, state)[: self.config.max_candidates]
            best = None
            best_score = -1e100
            for action in actions:
                risk = self.carrier.carrier_violation_proxy(before, action)
                if self.config.carrier_mode == "constraint" and risk > self.config.carrier_budget:
                    continue
                audit = self.executor.run_tactic(cur_task, action, state)
                after_state = audit.after_state or state
                after = self.extractor.extract(after_state, audit)
                _, flat, _ = self.extractor.response(before, after)
                resp_vec = np.asarray(flat, dtype=float)
                pred_vec = resp_vec
                if self.response_model is not None:
                    pred_vec = np.asarray(self.response_model.predict(action, mode=self.config.response_mode).mean, dtype=float)
                score = float(np.dot(before_vec, pred_vec)) - self.config.cost_weight * action.cost_estimate
                if self.config.carrier_mode == "penalty":
                    score -= risk
                if score > best_score:
                    best_score = score
                    best = (action, audit, after_state, after, resp_vec, pred_vec, risk, score)
            if best is None:
                rec.final_status = "stuck"
                break
            action, audit, after_state, after, resp_vec, pred_vec, risk, score = best
            rec.steps.append(SchemaTrajectoryStep(
                step=step_idx,
                state_id=state.state_id,
                action_id=action.action_id,
                tactic=action.tactic,
                status=audit.status,
                selected_score=float(score),
                defect_norm_before=float(np.linalg.norm(before_vec)),
                defect_norm_after=float(np.linalg.norm(after.as_numpy())),
                response_norm=float(np.linalg.norm(resp_vec)),
                carrier_risk=float(risk),
                elapsed_ms=float(audit.elapsed_ms or 0.0),
            ))
            if audit.status == "success":
                prefix_lines.append(action.tactic)
                rec.final_status = "proved"
                break
            partial = bool((audit.audit_flags or {}).get("partial_success")) or "unsolved goal" in ((audit.stdout or "") + (audit.stderr or "")).lower()
            if partial and self.config.append_partial_success:
                prefix_lines.append(action.tactic)
                state = after_state
                continue
            if audit.status in {"timeout", "unsafe", "elab_error"}:
                rec.final_status = audit.status
                break
            rec.final_status = "stuck"
            break
        rec.prefix = "\n".join(prefix_lines)
        rec.metadata = {"trajectory_config": asdict(self.config)}
        return rec

def _model_predicted_response(model: Any, row: dict[str, Any], mode: str, dim: int) -> list[float] | None:
    """Predict a response vector for one response row, aligned to its chart.

    Returns None when the prediction cannot be produced or aligned to the
    row's dimension, so the caller can fall back explicitly.
    """
    try:
        action_dict = row.get("action") if isinstance(row.get("action"), dict) else None
        if action_dict:
            action = TacticAction.from_dict(action_dict)
        else:
            aid = str(row.get("action_id") or "")
            action = TacticAction(action_id=aid, tactic=str(row.get("tactic") or aid))
        pred = model.predict(action, mode=mode)
        vals = [float(v) for v in (pred.mean or [])]
        model_keys = [str(k) for k in (getattr(model, "response_keys", None) or [])]
        row_keys = [str(k) for k in (row.get("response_keys") or [])]
        if row_keys and model_keys and row_keys != model_keys:
            by_key = dict(zip(model_keys, vals))
            vals = [float(by_key.get(k, 0.0)) for k in row_keys]
        if len(vals) != dim:
            return None
        return vals
    except Exception:
        return None


# Compatibility helper kept for external callers; the CLI gamma-audit now
# reads transition files directly (see cli/experiment.py cmd_gamma_audit).
def audit_gamma_from_responses(
    responses_path: str,
    out_json: str,
    *,
    response_model: Any = None,
    response_mode: str = "mean",
):
    """Audit finite-chart Gamma directly from realized response records.

    ``pred_response`` only carries audit signal when it is a model prediction:
    the realized response equals ``defect_before - defect_after`` by
    construction, so using it makes the residual ``defect - pred_response``
    identical to ``defect_after`` and the fitted Gamma trivially near-identity.
    Pass ``response_model`` (a ResponseModel instance or a path to a saved
    model) to audit genuine predictions. The realized response is always kept
    in each step's ``metadata["response_realized"]``; without a model the
    degenerate legacy behavior is preserved and flagged via
    ``pred_response_source``.
    """
    from .schemas import read_jsonl
    import json
    from pathlib import Path
    model = response_model
    if isinstance(response_model, (str, Path)):
        from .response_model import ResponseModel
        model = ResponseModel.load(response_model)
    rows = read_jsonl(responses_path)
    steps = []
    for r in rows:
        db = r.get("defect_before", {}).get("flat", [])
        da = r.get("defect_after", {}).get("flat", [])
        rr = r.get("response_flat", [])
        if db and da and rr and len(db) == len(da) == len(rr):
            realized = [float(v) for v in rr]
            pred = _model_predicted_response(model, r, response_mode, len(db)) if model is not None else None
            source = "response_model" if pred is not None else "realized_fallback_degenerate"
            steps.append(TrajectoryStep(
                state_id=r.get("state_id", ""),
                action_id=r.get("action_id", ""),
                defect_before=db,
                pred_response=pred if pred is not None else realized,
                defect_after=da,
                metadata={"response_realized": realized, "pred_response_source": source},
            ))
    report = TrajectoryAuditor().audit(steps) if steps else TrajectoryAuditReport(0, {}, [])
    sources: dict[str, int] = {}
    for rep, step in zip(report.per_step, steps):
        src = step.metadata["pred_response_source"]
        rep["pred_response_source"] = src
        sources[src] = sources.get(src, 0) + 1
    report.gamma_report["pred_response_sources"] = sources
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return report

# --- Trajectory-level Gamma audit compatibility layer ---
from dataclasses import asdict
from .gamma import GammaAuditor

@dataclass
class TrajectoryAuditStep:
    state_id: str
    action_id: str
    defect_before: list[float]
    pred_response: list[float]
    defect_after: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryAuditReport:
    n_steps: int
    gamma_report: dict[str, Any]
    per_step: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TrajectoryAuditor:
    """Audit realized response and optional finite-chart Gamma on trajectories."""

    def __init__(self, ridge: float = 1e-3):
        self.ridge = float(ridge)

    def audit(self, steps: list[TrajectoryAuditStep], *, fit_gamma: bool = True, horizon: int = 4) -> TrajectoryAuditReport:
        if not steps:
            return TrajectoryAuditReport(n_steps=0, gamma_report={"status": "empty"})
        D = np.asarray([s.defect_before for s in steps], dtype=float)
        R = np.asarray([s.pred_response for s in steps], dtype=float)
        N = np.asarray([s.defect_after for s in steps], dtype=float)
        auditor = GammaAuditor(ridge=self.ridge)
        gamma = auditor.fit_linear_gamma(D - R, N) if fit_gamma and len(steps) >= 2 else np.eye(D.shape[1])
        reports = []
        for s in steps:
            rep = auditor.audit(np.asarray(s.defect_before), np.asarray(s.pred_response), np.asarray(s.defect_after), gamma=gamma, horizon=horizon)
            d = rep.__dict__.copy()
            d.update({"state_id": s.state_id, "action_id": s.action_id})
            reports.append(d)
        # Aggregate conservatively.
        agg = {
            "cocycle_resid_rel_mean": float(np.mean([r["cocycle_resid_rel"] for r in reports])),
            "gamma_vs_persistence_improvement_mean": float(np.mean([r["gamma_vs_persistence_improvement"] for r in reports])),
            "tail_value_cos_mean": float(np.mean([r.get("tail_value_cos") or 0.0 for r in reports])),
            "spectral_radius_proxy": reports[0].get("spectral_radius_proxy"),
            "fit_gamma": bool(fit_gamma and len(steps) >= 2),
        }
        return TrajectoryAuditReport(n_steps=len(steps), gamma_report=agg, per_step=reports)

# CLI compatibility alias.
TrajectoryAuditStep = TrajectoryStep
