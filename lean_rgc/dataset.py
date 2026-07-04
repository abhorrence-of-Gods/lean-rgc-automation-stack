from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import math
import random

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash


@dataclass
class DatasetSummary:
    n_responses: int = 0
    n_states: int = 0
    n_actions: int = 0
    statuses: dict[str, int] | None = None
    mean_response_norm: float = 0.0
    max_response_norm: float = 0.0
    mean_goal_response: float = 0.0
    mean_carrier_delta: float = 0.0
    timeout_rate: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["statuses"] = d.get("statuses") or {}
        return d


def summarize_response_rows(rows: list[dict[str, Any]]) -> DatasetSummary:
    statuses: dict[str, int] = {}
    states: set[str] = set()
    actions: set[str] = set()
    norms: list[float] = []
    goal_resps: list[float] = []
    carrier_deltas: list[float] = []
    for r in rows:
        st = str(r.get("audit_status", r.get("status", "unknown")))
        statuses[st] = statuses.get(st, 0) + 1
        if r.get("state_id") is not None:
            states.add(str(r.get("state_id")))
        if r.get("action_id") is not None:
            actions.add(str(r.get("action_id")))
        v = np.asarray(r.get("response_flat", []), dtype=float)
        if v.size:
            norms.append(float(np.linalg.norm(v)))
        resp = r.get("response", {}) or {}
        goal_resps.append(sum(float(v) for k, v in resp.items() if str(k).startswith("goal.")))
        carrier_deltas.append(sum(float(v) for v in (r.get("carrier_delta", {}) or {}).values()))
    n = len(rows)
    return DatasetSummary(
        n_responses=n,
        n_states=len(states),
        n_actions=len(actions),
        statuses=statuses,
        mean_response_norm=float(np.mean(norms)) if norms else 0.0,
        max_response_norm=float(np.max(norms)) if norms else 0.0,
        mean_goal_response=float(np.mean(goal_resps)) if goal_resps else 0.0,
        mean_carrier_delta=float(np.mean(carrier_deltas)) if carrier_deltas else 0.0,
        timeout_rate=float(statuses.get("timeout", 0) / n) if n else 0.0,
        success_rate=float(statuses.get("success", 0) / n) if n else 0.0,
    )


def split_jsonl(path: str | Path, out_dir: str | Path, *, train_frac: float = 0.8, seed: int = 0, key: str | None = None) -> dict[str, Any]:
    rows = read_jsonl(path)
    rng = random.Random(seed)
    if key:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            buckets.setdefault(str(r.get(key, stable_hash(r))), []).append(r)
        keys = list(buckets)
        rng.shuffle(keys)
        cutoff = int(round(train_frac * len(keys)))
        train_keys = set(keys[:cutoff])
        train = [r for k in keys if k in train_keys for r in buckets[k]]
        valid = [r for k in keys if k not in train_keys for r in buckets[k]]
    else:
        rows2 = list(rows)
        rng.shuffle(rows2)
        cutoff = int(round(train_frac * len(rows2)))
        train, valid = rows2[:cutoff], rows2[cutoff:]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "valid.jsonl", valid)
    meta = {"n": len(rows), "n_train": len(train), "n_valid": len(valid), "train_frac": train_frac, "seed": seed, "group_key": key}
    (out / "split.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def _model_predicted_response(model: Any, row: dict[str, Any], mode: str, dim: int) -> list[float] | None:
    """Predict a response vector for one response row, aligned to its chart.

    Returns None when the prediction cannot be produced or aligned to the
    row's dimension, so the caller can fall back explicitly.
    """
    try:
        from .schemas import TacticAction

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


def transitions_from_responses(
    responses_path: str | Path,
    out: str | Path,
    *,
    response_model: Any = None,
    response_mode: str = "mean",
) -> list[dict[str, Any]]:
    """Build Gamma-transition rows from realized response records.

    ``pred_response`` only carries training signal when it is a model
    prediction: the realized response equals ``defect - next_defect`` by
    construction, so using it as the prediction makes the residual
    ``defect - pred_response`` identical to ``next_defect`` and any Gamma fit
    trivially near-identity. Pass ``response_model`` (a ResponseModel /
    ResponseLearnerModel instance or a path to a saved model) to emit genuine
    predictions. The realized response is always kept in ``response_realized``;
    without a model the degenerate legacy behavior is preserved and flagged
    via ``pred_response_source``.
    """
    model = response_model
    if isinstance(response_model, (str, Path)):
        from .response_model import ResponseModel

        model = ResponseModel.load(response_model)
    rows = read_jsonl(responses_path)
    transitions: list[dict[str, Any]] = []
    for r in rows:
        db = (r.get("defect_before") or {}).get("flat", [])
        da = (r.get("defect_after") or {}).get("flat", [])
        rr = r.get("response_flat", [])
        if db and da and rr and len(db) == len(da) == len(rr):
            realized = [float(v) for v in rr]
            pred = _model_predicted_response(model, r, response_mode, len(db)) if model is not None else None
            source = "response_model" if pred is not None else "realized_fallback_degenerate"
            transitions.append({
                "state_id": r.get("state_id"),
                "action_id": r.get("action_id"),
                "defect": db,
                "pred_response": pred if pred is not None else realized,
                "response_realized": realized,
                "pred_response_source": source,
                "next_defect": da,
                "audit_status": r.get("audit_status"),
            })
    write_jsonl(out, transitions)
    return transitions


def write_run_report(run_dir: str | Path, out: str | Path | None = None) -> dict[str, Any]:
    run = Path(run_dir)
    report: dict[str, Any] = {"run_dir": str(run)}
    resp_path = run / "responses.jsonl"
    if resp_path.exists():
        rows = read_jsonl(resp_path)
        report["responses"] = summarize_response_rows(rows).to_dict()
    for name in ["summary.json", "trajectory_summary.json"]:
        p = run / name
        if p.exists():
            try:
                report[name.removesuffix(".json")] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    for name in ["carrier_coker.jsonl", "response_components.jsonl", "gamma_audit.jsonl", "carrier_acceptance.jsonl"]:
        p = run / name
        if p.exists():
            rows = read_jsonl(p)
            report[name.removesuffix(".jsonl")] = {"n": len(rows), "sample": rows[:3]}
    out_path = Path(out) if out else run / "rgc_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
