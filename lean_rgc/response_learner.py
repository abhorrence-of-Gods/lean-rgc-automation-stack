from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
from pathlib import Path
from typing import Any
import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash


@dataclass
class ResponseLearnerReport:
    model_type: str
    n_train: int
    n_val: int
    dim_response: int
    dim_features: int
    train_rmse: float
    val_rmse: float | None
    val_cos: float | None
    response_keys: list[str]
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class HashingFeatureMap:
    """Small dependency-free feature map for state/action pairs.

    This is intentionally a chart, not a canonical tactic representation. It is
    useful for bootstrapping response prediction from micro-audits.
    """

    def __init__(self, dim: int = 256):
        self.dim = int(dim)

    def _add(self, x: np.ndarray, key: str, val: float = 1.0):
        idx = int(stable_hash(key, 12), 16) % self.dim
        sign = 1.0 if (int(stable_hash("sign:" + key, 12), 16) % 2 == 0) else -1.0
        x[idx] += sign * float(val)

    def encode(self, row: dict[str, Any]) -> np.ndarray:
        x = np.zeros(self.dim, dtype=float)
        action = row.get("action_id", "")
        status = row.get("audit_status", "")
        self._add(x, "bias", 1.0)
        self._add(x, f"action:{action}", 1.0)
        self._add(x, f"status:{status}", 1.0)
        # Defect-before values are legitimate state charts.
        db = row.get("defect_before", {})
        if isinstance(db, dict):
            for comp in ["goal", "type", "search", "carrier", "audit"]:
                dd = db.get(comp, {}) or {}
                for k, v in dd.items():
                    try:
                        fv = float(v)
                    except Exception:
                        continue
                    self._add(x, f"{comp}:{k}", fv)
        # Carrier delta/action class if available.
        for k, v in (row.get("carrier_delta", {}) or {}).items():
            try:
                self._add(x, f"carrier_delta:{k}", float(v))
            except Exception:
                pass
        # Light action token features.
        tactic = row.get("tactic") or row.get("action", {}).get("tactic") or ""
        for tok in str(tactic).replace("[", " ").replace("]", " ").replace(",", " ").split()[:24]:
            self._add(x, f"tok:{tok}", 1.0)
        # Normalize hashed vector to keep ridge stable.
        norm = np.linalg.norm(x)
        if norm > 0:
            x /= max(1.0, norm / 4.0)
        return x


class LeanResponseLearner:
    """Ridge multi-output response learner over hashed state/action features."""

    def __init__(self, feature_dim: int = 256, ridge: float = 1e-2):
        self.feature_dim = int(feature_dim)
        self.ridge = float(ridge)
        self.feature_map = HashingFeatureMap(feature_dim)
        self.coef: np.ndarray | None = None  # [feature_dim, response_dim]
        self.response_keys: list[str] = []
        self.report: ResponseLearnerReport | None = None

    @staticmethod
    def _cos_mean(yhat: np.ndarray, y: np.ndarray) -> float:
        num = np.sum(yhat * y, axis=1)
        den = np.linalg.norm(yhat, axis=1) * np.linalg.norm(y, axis=1) + 1e-9
        return float(np.mean(num / den))

    def fit(self, rows: list[dict[str, Any]], val_fraction: float = 0.2, seed: int = 0) -> ResponseLearnerReport:
        rows = [r for r in rows if "response_flat" in r]
        if not rows:
            raise ValueError("no response rows")
        rng = np.random.default_rng(seed)
        idx = np.arange(len(rows))
        rng.shuffle(idx)
        n_val = int(round(len(rows) * val_fraction)) if len(rows) >= 5 else 0
        val_idx = idx[:n_val]
        tr_idx = idx[n_val:]
        X = np.stack([self.feature_map.encode(rows[i]) for i in idx], axis=0)
        Y = np.stack([np.asarray(rows[i]["response_flat"], dtype=float) for i in idx], axis=0)
        self.response_keys = list(rows[idx[0]].get("response_keys", []))
        Xtr, Ytr = X[n_val:], Y[n_val:]
        Xval, Yval = X[:n_val], Y[:n_val]
        A = Xtr.T @ Xtr + self.ridge * np.eye(self.feature_dim)
        B = Xtr.T @ Ytr
        self.coef = np.linalg.solve(A, B)
        pred_tr = Xtr @ self.coef
        train_rmse = float(np.sqrt(np.mean((pred_tr - Ytr) ** 2)))
        val_rmse = None
        val_cos = None
        if n_val:
            pred_val = Xval @ self.coef
            val_rmse = float(np.sqrt(np.mean((pred_val - Yval) ** 2)))
            val_cos = self._cos_mean(pred_val, Yval)
        self.report = ResponseLearnerReport(
            model_type="hash_ridge_response_v0",
            n_train=int(len(tr_idx)),
            n_val=int(n_val),
            dim_response=int(Y.shape[1]),
            dim_features=int(self.feature_dim),
            train_rmse=train_rmse,
            val_rmse=val_rmse,
            val_cos=val_cos,
            response_keys=self.response_keys,
            metadata={"ridge": self.ridge, "seed": seed},
        )
        return self.report

    def predict_row(self, row: dict[str, Any]) -> np.ndarray:
        if self.coef is None:
            raise RuntimeError("model not fit")
        return self.feature_map.encode(row) @ self.coef

    def predict(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            pred = self.predict_row(r)
            out.append({
                "state_id": r.get("state_id"),
                "action_id": r.get("action_id"),
                "pred_response_flat": pred.tolist(),
                "response_keys": self.response_keys,
            })
        return out

    def predict_actions(self, defect, actions):
        """Predict response vectors for TacticAction objects at a DefectVector chart.

        This helper is used by the minimal trajectory runner. It builds the same
        row schema used by the hashed featurizer, so predictions remain charted
        and non-canonical.
        """
        out = {}
        db = defect.to_dict() if hasattr(defect, "to_dict") else defect
        for a in actions:
            row = {
                "state_id": "current",
                "action_id": a.action_id,
                "audit_status": "candidate",
                "defect_before": db,
                "carrier_delta": {},
                "tactic": a.tactic,
                "action": a.to_dict() if hasattr(a, "to_dict") else {},
            }
            out[a.action_id] = self.predict_row(row)
        return out

    def save(self, path: str | Path) -> None:
        if self.coef is None or self.report is None:
            raise RuntimeError("model not fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, coef=self.coef, response_keys=np.asarray(self.response_keys, dtype=object), report=json.dumps(self.report.to_dict()))

    @classmethod
    def load(cls, path: str | Path) -> "LeanResponseLearner":
        data = np.load(path, allow_pickle=True)
        coef = data["coef"]
        obj = cls(feature_dim=coef.shape[0])
        obj.coef = coef
        obj.response_keys = [str(x) for x in data["response_keys"].tolist()]
        return obj


def train_response_model(responses_path: str | Path, model_out: str | Path, predictions_out: str | Path | None = None, *, feature_dim: int = 256, ridge: float = 1e-2, val_fraction: float = 0.2, seed: int = 0) -> ResponseLearnerReport:
    rows = read_jsonl(responses_path)
    learner = LeanResponseLearner(feature_dim=feature_dim, ridge=ridge)
    report = learner.fit(rows, val_fraction=val_fraction, seed=seed)
    learner.save(model_out)
    Path(str(model_out) + ".report.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if predictions_out:
        write_jsonl(predictions_out, learner.predict(rows))
    return report


def load_action_lookup(path):
    # compatibility shim; the hashing learner does not require action metadata.
    return {}
