from pathlib import Path

from lean_rgc.robust_coker import run_robust_coker_acceptance
from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.cli import main


def _row(state, action, resp, defect=(1.0, 0.0), status="success", carrier=None, tactic=None):
    tactic = tactic or action
    return {
        "state_id": state,
        "task_id": state,
        "action_id": action,
        "response_flat": list(resp),
        "response_keys": ["goal.main", "carrier.safe"],
        "defect_before": {"flat": list(defect), "flat_keys": ["goal.main", "carrier.safe"]},
        "defect_after": {"flat": [max(0.0, defect[0]-resp[0]), max(0.0, defect[1]-resp[1])], "flat_keys": ["goal.main", "carrier.safe"]},
        "carrier_delta": carrier or {},
        "audit_status": status,
        "action": {"action_id": action, "tactic": tactic, "tactic_class": "test", "carrier_tags": [], "cost_estimate": 1.0, "metadata": {}},
    }


def test_robust_coker_acceptance_outputs(tmp_path: Path):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    write_jsonl(base, [
        _row("s", "base_good", (0.3, 0.0)),
        _row("s", "base_bad", (0.1, 0.0)),
        _row("s", "base_hold", (0.2, 0.0)),
        _row("s", "base_other", (0.05, 0.0)),
    ])
    write_jsonl(cand, [
        _row("s", "new_good", (0.9, 0.0), carrier={"safe": 0.2}),
        _row("s", "new_timeout", (2.0, 0.0), status="timeout"),
    ])
    rep = run_robust_coker_acceptance(base, cand, out_report=tmp_path/"report.json", out_actions=tmp_path/"actions.jsonl", out_rows=tmp_path/"rows.jsonl", margin_threshold=-0.5)
    assert rep.n_candidates == 2
    assert (tmp_path/"report.json").exists()
    rows = read_jsonl(tmp_path/"rows.jsonl")
    assert all("robust_margin" in r for r in rows)
    acts = read_jsonl(tmp_path/"actions.jsonl")
    assert any(a["action_id"] == "new_good" for a in acts)
    assert all(a["action_id"] != "new_timeout" for a in acts)


def test_cli_robust_coker_accept(tmp_path: Path):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    write_jsonl(base, [_row("s", "base", (0.2, 0.0)), _row("s", "base2", (0.1, 0.0))])
    write_jsonl(cand, [_row("s", "new", (0.5, 0.0))])
    rc = main([
        "robust-coker-accept",
        "--base-responses", str(base),
        "--candidate-responses", str(cand),
        "--out-report", str(tmp_path/"report.json"),
        "--out-actions", str(tmp_path/"actions.jsonl"),
        "--out-rows", str(tmp_path/"rows.jsonl"),
        "--margin-threshold", "-1",
    ])
    assert rc == 0
    assert (tmp_path/"report.json").exists()
    assert (tmp_path/"actions.jsonl").exists()
