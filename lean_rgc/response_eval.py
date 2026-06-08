from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import csv
import json
import math

import numpy as np

from .response_model import ResponseModel
from .schemas import TacticAction, read_jsonl, write_jsonl


def _actual_vec(row: dict[str, Any]) -> np.ndarray:
    v = row.get("response_flat") or []
    try:
        return np.asarray(v, dtype=float).reshape(-1)
    except Exception:
        return np.asarray([], dtype=float)


def _action_from_row(row: dict[str, Any]) -> TacticAction | None:
    a = row.get("action") if isinstance(row.get("action"), dict) else None
    if a is not None:
        try:
            return TacticAction.from_dict(a)
        except Exception:
            return None
    tactic = row.get("tactic")
    aid = row.get("action_id")
    if tactic or aid:
        try:
            return TacticAction(
                action_id=str(aid or tactic),
                tactic=str(tactic or ""),
                tactic_class=str(row.get("tactic_class") or row.get("class") or "unknown"),
                carrier_tags=list(row.get("carrier_tags") or []),
                cost_estimate=float(row.get("cost_estimate", 1.0)),
                metadata=dict(row.get("metadata") or {}),
            )
        except Exception:
            return None
    return None


def _cos(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return None
    na = float(np.linalg.norm(a)); nb = float(np.linalg.norm(b))
    if na <= 1e-12 or nb <= 1e-12:
        return None
    return float(np.dot(a, b) / (na * nb))


def _safe_corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    x = np.asarray(xs, dtype=float); y = np.asarray(ys, dtype=float)
    if float(np.std(x)) <= 1e-12 or float(np.std(y)) <= 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


@dataclass
class ResponseEvalRow:
    state_id: str
    task_id: str | None
    action_id: str
    tactic_class: str
    generated_by: str
    source: str
    status: str
    dim: int
    rmse: float
    mae: float
    cosine: float | None
    actual_norm: float
    pred_norm: float
    lcb_norm: float
    lcb_coordinate_coverage: float | None
    lcb_vector_safe: bool | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseEvalSummary:
    n: int
    n_eval: int
    mean_rmse: float
    mean_mae: float
    mean_cosine: float | None
    median_cosine: float | None
    norm_corr: float | None
    lcb_coordinate_coverage: float | None
    lcb_vector_safe_rate: float | None
    by_source: dict[str, dict[str, Any]]
    by_generated_by: dict[str, dict[str, Any]]
    by_status: dict[str, dict[str, Any]]
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _group_summary(rows: list[ResponseEvalRow], key_fn) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[ResponseEvalRow]] = {}
    for r in rows:
        groups.setdefault(str(key_fn(r) or "unknown"), []).append(r)
    out: dict[str, dict[str, Any]] = {}
    for k, rs in groups.items():
        cos = [r.cosine for r in rs if r.cosine is not None]
        out[k] = {
            "n": len(rs),
            "mean_rmse": float(np.mean([r.rmse for r in rs])) if rs else 0.0,
            "mean_mae": float(np.mean([r.mae for r in rs])) if rs else 0.0,
            "mean_cosine": float(np.mean(cos)) if cos else None,
            "mean_actual_norm": float(np.mean([r.actual_norm for r in rs])) if rs else 0.0,
            "mean_pred_norm": float(np.mean([r.pred_norm for r in rs])) if rs else 0.0,
            "lcb_vector_safe_rate": float(np.mean([1.0 if r.lcb_vector_safe else 0.0 for r in rs if r.lcb_vector_safe is not None])) if any(r.lcb_vector_safe is not None for r in rs) else None,
        }
    return out


def evaluate_response_model(model_path: str | Path, responses_path: str | Path, *, mode: str = "mean", out_rows: str | Path | None = None, out_summary: str | Path | None = None, out_csv: str | Path | None = None) -> tuple[list[ResponseEvalRow], ResponseEvalSummary]:
    model = ResponseModel.load(model_path)
    rows = read_jsonl(responses_path)
    eval_rows: list[ResponseEvalRow] = []
    pred_norms: list[float] = []
    actual_norms: list[float] = []
    for row in rows:
        actual = _actual_vec(row)
        action = _action_from_row(row)
        if action is None or actual.size == 0:
            continue
        pred = model.predict(action, mode=mode)
        mean = np.asarray(pred.mean if mode != "lcb" else pred.lcb, dtype=float).reshape(-1)
        lcb = np.asarray(pred.lcb, dtype=float).reshape(-1)
        if mean.size != actual.size:
            # Pad or truncate only for reporting; dimension mismatch is a genuine chart warning.
            d = min(mean.size, actual.size)
            mean = mean[:d]
            lcb = lcb[:d]
            actual2 = actual[:d]
        else:
            actual2 = actual
        if actual2.size == 0:
            continue
        diff = mean - actual2
        rmse = float(math.sqrt(float(np.mean(diff ** 2))))
        mae = float(np.mean(np.abs(diff)))
        c = _cos(mean, actual2)
        lcb_cov = None
        lcb_safe = None
        if lcb.size == actual2.size and lcb.size:
            # Coordinate-wise lower confidence bound should not over-predict local response.
            ok = lcb <= actual2 + 1e-9
            lcb_cov = float(np.mean(ok))
            lcb_safe = bool(np.all(ok))
        act_meta = action.metadata if isinstance(action.metadata, dict) else {}
        gen = str(act_meta.get("generated_by") or act_meta.get("prefix_kind") or "manual")
        status = str(row.get("audit_status") or row.get("status") or "unknown")
        pn = float(np.linalg.norm(mean)); an = float(np.linalg.norm(actual2)); ln = float(np.linalg.norm(lcb)) if lcb.size else 0.0
        pred_norms.append(pn); actual_norms.append(an)
        eval_rows.append(ResponseEvalRow(
            state_id=str(row.get("state_id") or ""),
            task_id=str(row.get("task_id")) if row.get("task_id") is not None else None,
            action_id=action.action_id,
            tactic_class=action.tactic_class,
            generated_by=gen,
            source=str(pred.source),
            status=status,
            dim=int(actual2.size),
            rmse=rmse,
            mae=mae,
            cosine=c,
            actual_norm=an,
            pred_norm=pn,
            lcb_norm=ln,
            lcb_coordinate_coverage=lcb_cov,
            lcb_vector_safe=lcb_safe,
            metadata={"prediction_source_meta": pred.metadata or {}, "tactic": action.tactic[:200]},
        ))
    cosines = [r.cosine for r in eval_rows if r.cosine is not None]
    summary = ResponseEvalSummary(
        n=len(rows),
        n_eval=len(eval_rows),
        mean_rmse=float(np.mean([r.rmse for r in eval_rows])) if eval_rows else 0.0,
        mean_mae=float(np.mean([r.mae for r in eval_rows])) if eval_rows else 0.0,
        mean_cosine=float(np.mean(cosines)) if cosines else None,
        median_cosine=float(np.median(cosines)) if cosines else None,
        norm_corr=_safe_corr(pred_norms, actual_norms),
        lcb_coordinate_coverage=float(np.mean([r.lcb_coordinate_coverage for r in eval_rows if r.lcb_coordinate_coverage is not None])) if any(r.lcb_coordinate_coverage is not None for r in eval_rows) else None,
        lcb_vector_safe_rate=float(np.mean([1.0 if r.lcb_vector_safe else 0.0 for r in eval_rows if r.lcb_vector_safe is not None])) if any(r.lcb_vector_safe is not None for r in eval_rows) else None,
        by_source=_group_summary(eval_rows, lambda r: r.source),
        by_generated_by=_group_summary(eval_rows, lambda r: r.generated_by),
        by_status=_group_summary(eval_rows, lambda r: r.status),
        warning="in-sample evaluation if model was trained on the same responses" if str(model_path) and str(responses_path) else None,
    )
    if out_rows:
        write_jsonl(out_rows, [r.to_dict() for r in eval_rows])
    if out_summary:
        Path(out_summary).parent.mkdir(parents=True, exist_ok=True)
        Path(out_summary).write_text(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["state_id", "task_id", "action_id", "tactic_class", "generated_by", "source", "status", "dim", "rmse", "mae", "cosine", "actual_norm", "pred_norm", "lcb_norm", "lcb_coordinate_coverage", "lcb_vector_safe"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in eval_rows:
                d = r.to_dict()
                w.writerow({k: d.get(k) for k in fieldnames})
    return eval_rows, summary


__all__ = ["ResponseEvalRow", "ResponseEvalSummary", "evaluate_response_model"]
