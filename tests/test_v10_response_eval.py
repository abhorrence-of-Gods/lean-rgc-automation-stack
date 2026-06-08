from pathlib import Path
import json

from lean_rgc.schemas import write_jsonl, TacticAction
from lean_rgc.response_model import train_response_model
from lean_rgc.response_eval import evaluate_response_model


def test_response_eval(tmp_path: Path):
    actions = [TacticAction(action_id="a1", tactic="rfl", tactic_class="eq").to_dict()]
    rows = []
    for i in range(3):
        rows.append({
            "state_id": f"s{i}",
            "task_id": "t",
            "action_id": "a1",
            "action": actions[0],
            "audit_status": "success",
            "response_flat": [1.0, 0.0],
            "response_keys": ["goal.num_goals", "carrier.x"],
            "response": {"goal.num_goals": 1.0, "carrier.x": 0.0},
        })
    resp = tmp_path / "responses.jsonl"
    acts = tmp_path / "actions.jsonl"
    modelp = tmp_path / "model.json"
    summaryp = tmp_path / "summary.json"
    rowsp = tmp_path / "eval_rows.jsonl"
    write_jsonl(resp, rows)
    write_jsonl(acts, actions)
    train_response_model(resp, acts, modelp)
    erows, summary = evaluate_response_model(modelp, resp, out_summary=summaryp, out_rows=rowsp)
    assert summary.n_eval == 3
    assert summary.mean_rmse < 1e-9
    assert summary.mean_cosine and summary.mean_cosine > 0.99
    assert summaryp.exists() and rowsp.exists()
