from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import numpy as np

from .schemas import TacticAction, read_jsonl


@dataclass
class ResponsePrediction:
    action_id: str
    mean: list[float]
    uncertainty: list[float]
    source: str
    n: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseLearnerModel:
    response_keys: list[str]
    global_mean: list[float]
    global_std: list[float]
    by_action: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_class: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResponseLearnerModel":
        return cls(**d)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ResponseLearnerModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def predict(self, action: TacticAction, mode: str = "mean", lcb_kappa: float = 1.0) -> ResponsePrediction:
        pred, meta = ResponseTableLearner.predict(self, action, mode=mode, lcb_kappa=lcb_kappa)
        source = str(meta.get("source", "unknown"))
        n = int(meta.get("n", 0))
        if action.action_id in self.by_action:
            std = self.by_action[action.action_id].get("std", self.global_std)
        elif action.tactic_class in self.by_class:
            std = self.by_class[action.tactic_class].get("std", self.global_std)
        else:
            std = self.global_std
        return ResponsePrediction(action.action_id, pred.astype(float).tolist(), list(map(float, std)), source, n)


class ResponseTableLearner:
    """Small robust baseline response learner.

    It estimates response means / standard deviations by action id and optional
    tactic class. It is deliberately simple and audit-friendly; it should be
    treated as a finite response chart, not as a canonical operator.
    """

    def fit(self, response_rows: list[dict[str, Any]], actions: list[TacticAction] | None = None) -> ResponseLearnerModel:
        if not response_rows:
            raise ValueError("response_rows is empty")
        keys = list(response_rows[0].get("response_keys") or [])
        # Older / hand-written rows may omit response_keys.  Infer a stable
        # chart from response_flat length or sorted response dict keys so the
        # learner remains useful as a finite response chart.
        if not keys:
            if isinstance(response_rows[0].get("response_flat"), list):
                keys = [f"resp.{i}" for i in range(len(response_rows[0].get("response_flat") or []))]
            elif isinstance(response_rows[0].get("response"), dict):
                keys = sorted(str(k) for k in response_rows[0]["response"].keys())
            else:
                raise ValueError("response rows must include response_keys, response_flat, or response dict")
        action_class = {a.action_id: a.tactic_class for a in actions or []}
        def _flat(r):
            if isinstance(r.get("response_flat"), list):
                return r.get("response_flat")
            resp = r.get("response") if isinstance(r.get("response"), dict) else {}
            return [float(resp.get(k, 0.0)) for k in keys]
        X = np.asarray([_flat(r) for r in response_rows], dtype=float)
        global_mean = X.mean(axis=0)
        global_std = X.std(axis=0) + 1e-8
        by_action: dict[str, dict[str, Any]] = {}
        for aid in sorted({r["action_id"] for r in response_rows}):
            arr = np.asarray([_flat(r) for r in response_rows if r["action_id"] == aid], dtype=float)
            by_action[aid] = {"mean": arr.mean(axis=0).tolist(), "std": (arr.std(axis=0) + 1e-8).tolist(), "n": int(arr.shape[0])}
        by_class: dict[str, dict[str, Any]] = {}
        if action_class:
            for cls in sorted(set(action_class.values())):
                aids = {a for a, c in action_class.items() if c == cls}
                arrs = [_flat(r) for r in response_rows if r["action_id"] in aids]
                if arrs:
                    arr = np.asarray(arrs, dtype=float)
                    by_class[cls] = {"mean": arr.mean(axis=0).tolist(), "std": (arr.std(axis=0) + 1e-8).tolist(), "n": int(arr.shape[0])}
        return ResponseLearnerModel(
            response_keys=keys,
            global_mean=global_mean.tolist(),
            global_std=global_std.tolist(),
            by_action=by_action,
            by_class=by_class,
            metadata={"learner": "ResponseTableLearner", "n_rows": len(response_rows)},
        )

    @staticmethod
    def predict(model: ResponseLearnerModel, action: TacticAction, mode: str = "lcb", lcb_kappa: float = 1.0) -> tuple[np.ndarray, dict[str, Any]]:
        if action.action_id in model.by_action:
            rec = model.by_action[action.action_id]
            source = "action"
        elif action.tactic_class in model.by_class:
            rec = model.by_class[action.tactic_class]
            source = "class"
        else:
            rec = {"mean": model.global_mean, "std": model.global_std, "n": 0}
            source = "global"
        mean = np.asarray(rec["mean"], dtype=float)
        std = np.asarray(rec["std"], dtype=float)
        if mode == "mean":
            pred = mean
        elif mode == "ucb":
            pred = mean + lcb_kappa * std
        else:
            pred = mean - lcb_kappa * std
        return pred, {"source": source, "n": int(rec.get("n", 0)), "mean_norm": float(np.linalg.norm(mean)), "unc_norm": float(np.linalg.norm(std)), "mode": mode}


def fit_response_model_from_files(responses_path: str | Path, actions_path: str | Path | None = None, out_path: str | Path | None = None) -> ResponseLearnerModel:
    rows = read_jsonl(responses_path)
    actions = None
    if actions_path:
        actions = [TacticAction.from_dict(x) for x in read_jsonl(actions_path)]
    model = ResponseTableLearner().fit(rows, actions)
    if out_path:
        model.save(out_path)
    return model
