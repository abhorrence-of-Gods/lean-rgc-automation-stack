from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.learner import ResponseTableLearner
from lean_rgc.response_model import ResponseModel
from lean_rgc.schemas import write_jsonl
from lean_rgc.trajectory import audit_gamma_from_responses

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


def test_audit_without_model_is_degenerate_and_flagged(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    out = tmp_path / "gamma_audit.json"
    report = audit_gamma_from_responses(str(responses), str(out))
    assert report.n_steps == len(rows)
    assert report.gamma_report["pred_response_sources"] == {"realized_fallback_degenerate": len(rows)}
    for rep in report.per_step:
        assert rep["pred_response_source"] == "realized_fallback_degenerate"
        # Realized response equals defect_before - defect_after, so the
        # residual defect - pred_response equals defect_after exactly and the
        # persistence baseline collapses to zero: the vacuous-fit symptom.
        assert rep["persistence_resid_norm"] < 1e-9


def test_audit_with_model_uses_predictions_not_realized(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    model_path = _write_model(tmp_path, rows)
    out = tmp_path / "gamma_audit.json"
    report = audit_gamma_from_responses(str(responses), str(out), response_model=model_path)
    assert report.n_steps == len(rows)
    assert report.gamma_report["pred_response_sources"] == {"response_model": len(rows)}
    for rep in report.per_step:
        assert rep["pred_response_source"] == "response_model"
        # The table model predicts per-action means, which differ from every
        # realized response above, so the persistence baseline is genuinely
        # nonzero and the Gamma fit is no longer trivially near-identity.
        assert rep["persistence_resid_norm"] > 1e-6
    # Written report round-trips with the same provenance flags.
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk["n_steps"] == len(rows)
    assert on_disk["gamma_report"]["pred_response_sources"] == {"response_model": len(rows)}
    assert [r["pred_response_source"] for r in on_disk["per_step"]] == ["response_model"] * len(rows)


def test_audit_accepts_model_instance(tmp_path: Path):
    rows = _response_rows()
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, rows)
    model = ResponseModel.from_base(ResponseTableLearner().fit(rows))
    report = audit_gamma_from_responses(str(responses), str(tmp_path / "gamma_audit.json"), response_model=model)
    assert report.gamma_report["pred_response_sources"] == {"response_model": len(rows)}
