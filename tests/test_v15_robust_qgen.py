from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.qgen import qgen_from_files
from lean_rgc.schemas import read_jsonl, write_jsonl


def _row(task, state, action, resp, defect, status="success", carrier=None):
    return {
        "task_id": task,
        "state_id": state,
        "action_id": action,
        "audit_status": status,
        "response_flat": resp,
        "response_keys": ["goal.eq", "carrier.k"],
        "defect_before": {"flat": defect, "flat_keys": ["goal.eq", "carrier.k"]},
        "carrier_delta": carrier or {},
        "action": {"action_id": action, "tactic": "simp", "tactic_class": "simp", "cost_estimate": 1.0, "carrier_tags": ["k"], "metadata": {"generated_by": "qgen_test"}},
    }


def test_qgen_context_candidates_have_lineage(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, [
        _row("t", "s", "a0", [0.2, 0.0], [1.0, 0.5], carrier={"k": 0.1}),
        _row("t", "s", "a1", [0.0, 0.1], [1.0, 0.5], carrier={"k": -0.1}),
    ])
    out = tmp_path / "qgen"
    qgen_from_files(responses, out_dir=out, margin_threshold=-10)
    acts = read_jsonl(out / "qgen_context_candidates.jsonl")
    assert acts
    qmeta = acts[0]["metadata"]["qgen"]
    assert qmeta["lineage_id"].startswith("qgen_")
    assert isinstance(qmeta["top_coordinate_contributions"], list)
    assert "projection" in qmeta


def test_robust_accept_candidates_cli(tmp_path: Path):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    shadow = tmp_path / "shadow.jsonl"
    write_jsonl(base, [_row("t", "s", "base", [0.1, 0.0], [1.0, 0.0])])
    write_jsonl(cand, [_row("t", "s", "good", [0.8, 0.0], [1.0, 0.0])])
    write_jsonl(shadow, [_row("t", "s", "good", [0.7, 0.0], [1.0, 0.0])])
    out = tmp_path / "robust.jsonl"
    accepted = tmp_path / "accepted.jsonl"
    summary = tmp_path / "summary.json"
    rc = main([
        "robust-accept-candidates",
        "--base-responses", str(base),
        "--candidate-responses", str(cand),
        "--shadow-responses", str(shadow),
        "--out", str(out),
        "--accepted-actions-out", str(accepted),
        "--summary-out", str(summary),
        "--margin-threshold", "0.1",
    ])
    assert rc == 0
    rows = read_jsonl(out)
    assert rows and rows[0]["accepted"] is True
    assert rows[0]["shadow_margin"] is not None
    acts = read_jsonl(accepted)
    assert acts and acts[0]["metadata"]["robust_acceptance"]["robust_margin"] is not None


def test_robust_accept_requires_shadow(tmp_path: Path):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    write_jsonl(base, [_row("t", "s", "base", [0.1, 0.0], [1.0, 0.0])])
    write_jsonl(cand, [_row("t", "s", "good", [0.8, 0.0], [1.0, 0.0])])
    out = tmp_path / "robust.jsonl"
    rc = main([
        "robust-accept-candidates",
        "--base-responses", str(base),
        "--candidate-responses", str(cand),
        "--out", str(out),
        "--require-shadow",
    ])
    assert rc == 0
    rows = read_jsonl(out)
    assert rows and rows[0]["accepted"] is False
