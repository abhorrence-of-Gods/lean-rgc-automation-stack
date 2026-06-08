from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .learner import ResponseLearnerModel, ResponseTableLearner
from .schemas import TacticAction, read_jsonl, write_jsonl


@dataclass
class ResponseModelConfig:
    lcb_kappa: float = 1.0
    min_count_for_action: int = 2
    shrink: float = 2.0


@dataclass
class ResponsePrediction:
    action_id: str
    mean: list[float]
    uncertainty: list[float]
    lcb: list[float]
    source: str = "global"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResponseModel(ResponseLearnerModel):
    """Compatibility response model used by CLI / trajectory runner."""

    @classmethod
    def from_base(cls, base: ResponseLearnerModel) -> "ResponseModel":
        return cls(**base.to_dict())

    @classmethod
    def load(cls, path: str | Path) -> "ResponseModel":
        return cls.from_dict(__import__("json").loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResponseModel":
        return cls(**d)

    def predict(self, action: TacticAction | dict[str, Any], mode: str = "mean") -> ResponsePrediction:
        if isinstance(action, dict):
            action = TacticAction.from_dict(action)
        lcb_kappa = float(self.metadata.get("lcb_kappa", 1.0))
        mean_arr, meta_mean = ResponseTableLearner.predict(self, action, mode="mean", lcb_kappa=lcb_kappa)
        lcb_arr, meta_lcb = ResponseTableLearner.predict(self, action, mode="lcb", lcb_kappa=lcb_kappa)
        if mode == "lcb":
            arr, meta = lcb_arr, meta_lcb
        else:
            arr, meta = mean_arr, meta_mean
        # Estimate elementwise uncertainty from source std record.
        if action.action_id in self.by_action:
            std = self.by_action[action.action_id].get("std", self.global_std)
        elif action.tactic_class in self.by_class:
            std = self.by_class[action.tactic_class].get("std", self.global_std)
        else:
            std = self.global_std
        return ResponsePrediction(
            action_id=action.action_id,
            mean=arr.astype(float).tolist(),
            uncertainty=[float(x) for x in std],
            lcb=lcb_arr.astype(float).tolist(),
            source=str(meta.get("source", "unknown")),
            metadata=meta,
        )


def load_actions(path: str | Path | None) -> list[TacticAction]:
    if not path:
        return []
    return [TacticAction.from_dict(x) for x in read_jsonl(path)]


def train_response_model(responses_path: str | Path, actions_path: str | Path | None, out: str | Path, config: ResponseModelConfig | None = None) -> ResponseModel:
    rows = read_jsonl(responses_path)
    actions = load_actions(actions_path)
    base = ResponseTableLearner().fit(rows, actions)
    model = ResponseModel.from_base(base)
    if config:
        model.metadata.update(asdict(config))
    model.save(out)
    return model


def predict_response_file(model_path: str | Path, actions_path: str | Path, out: str | Path, *, mode: str = "mean") -> list[dict[str, Any]]:
    model = ResponseModel.load(model_path)
    actions = load_actions(actions_path)
    rows = [model.predict(a, mode=mode).to_dict() for a in actions]
    write_jsonl(out, rows)
    return rows
