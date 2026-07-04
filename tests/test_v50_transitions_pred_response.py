from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from lean_rgc.dataset import transitions_from_responses
from lean_rgc.gamma_transition_learner import _rows_to_arrays, learn_gamma_transition_model
from lean_rgc.learner import ResponseTableLearner
from lean_rgc.response_model import ResponseModel
from lean_rgc.schemas import read_jsonl, write_jsonl
from lean_rgc.cli import main as cli_main

KEYS = ["goal.num_goals", "goal.depth"]


def _response_rows() -> list[dict]:
    # response_flat is the realized response: defect_before - defect_after.
    data = [
        ("s1", "a", [1.0, 0.5], [0.4, 0.1]),
        ("s2", "a", [0.8, 0.2], [0.5, 0.0]),
        ("s3", "b", [1.0, 1.0], [0.9, 0.7]),
        ("s4", "b", [0.6, 0.4], [0.2, 0.3]),
    ]
    rows = []
    for sid, aid, before, after in data:
        resp = [b - a for b, a in zip(before, after)]
        rows.append({
            "state_id": sid,
            "action_id": aid,
            "response": dict(zip(KEYS, resp)),
            "response_flat": resp,
            "response_keys": KEYS,
            "defect_before": {"flat": before, "flat_keys": KEYS},
            "defect_after": {"flat": after, "flat_keys": KEYS},
            "audit_status": "success",
        })
    return rows


def _write_model(tmp_path: Path, rows: list[dict]) -> Path:
    base = ResponseTableLearner().fit(rows)
    model = ResponseModel.from_base(base)
    model_path = tmp_path / "response_model.json"
    model.save(model_path)
    return model_path


def test_pred_response_is_model_prediction_not_realized(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    model_path = _write_model(tmp_path, rows)
    out = tmp_path / "transitions.jsonl"
    transitions = transitions_from_responses(responses, out, response_model=model_path)
    assert len(transitions) == len(rows)
    for t, r in zip(transitions, rows):
        assert t["pred_response_source"] == "response_model"
        assert t["response_realized"] == [float(v) for v in r["response_flat"]]
        # The realized response differs per row while the table model predicts
        # the per-action mean, so the prediction must not equal the realized
        # response for these rows.
        assert t["pred_response"] != t["response_realized"]
    # Round-trips through jsonl.
    assert read_jsonl(out) == transitions


def test_gamma_fit_no_longer_receives_realized_response(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    model_path = _write_model(tmp_path, rows)

    degenerate = transitions_from_responses(responses, tmp_path / "t_degenerate.jsonl")
    fixed = transitions_from_responses(responses, tmp_path / "t_fixed.jsonl", response_model=model_path)

    # Degenerate legacy behavior: residual (defect - pred_response) equals
    # next_defect exactly, so any Gamma fit is a trivial identity map.
    Xd, Yd, _ = _rows_to_arrays(degenerate)
    assert np.allclose(Xd, Yd)
    # With a model prediction the residuals genuinely differ from the target.
    Xf, Yf, kept = _rows_to_arrays(fixed)
    assert len(kept) == len(rows)
    assert not np.allclose(Xf, Yf)

    # End-to-end: the transition learner's persistence baseline is no longer
    # exactly zero (which was the vacuous-statistics symptom).
    rep = learn_gamma_transition_model(tmp_path / "t_fixed.jsonl", tmp_path / "gt", min_count=1, holdout_fraction=0.0)
    assert rep["n_valid_transitions"] == len(rows)
    assert rep["global_train_errors"]["persistence_rmse"] > 1e-6
    rep_deg = learn_gamma_transition_model(tmp_path / "t_degenerate.jsonl", tmp_path / "gt_deg", min_count=1, holdout_fraction=0.0)
    assert rep_deg["global_train_errors"]["persistence_rmse"] < 1e-9


def test_transitions_without_model_keep_realized_and_are_flagged(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    transitions = transitions_from_responses(responses, tmp_path / "transitions.jsonl")
    assert len(transitions) == len(rows)
    for t, r in zip(transitions, rows):
        assert t["pred_response_source"] == "realized_fallback_degenerate"
        assert t["pred_response"] == [float(v) for v in r["response_flat"]]
        assert t["response_realized"] == t["pred_response"]


def test_make_transitions_cli_accepts_response_model(tmp_path: Path, capsys):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    model_path = _write_model(tmp_path, rows)
    out = tmp_path / "transitions.jsonl"
    cli_main([
        "make-transitions",
        "--responses", str(responses),
        "--out", str(out),
        "--response-model", str(model_path),
    ])
    summary = json.loads(capsys.readouterr().out)
    assert summary["n"] == len(rows)
    assert summary["n_model_pred"] == len(rows)
    transitions = read_jsonl(out)
    assert all(t["pred_response"] != t["response_realized"] for t in transitions)
