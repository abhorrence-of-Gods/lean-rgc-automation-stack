from pathlib import Path

from lean_rgc.robust_acceptance import run_robust_acceptance
from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.cli import main


def _row(state, action_id, tactic, response, defect, status="success"):
    return {
        "state_id": state,
        "task_id": state,
        "action_id": action_id,
        "response_flat": response,
        "defect_before": {"flat": defect},
        "audit_status": status,
        "action": {
            "action_id": action_id,
            "tactic": tactic,
            "tactic_class": tactic.split()[0],
            "carrier_tags": [],
            "cost_estimate": 0.0,
            "metadata": {"task_id": state, "generated_by": "test"},
        },
    }


def test_robust_acceptance_lcb_groups_repeated_rows(tmp_path: Path):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    write_jsonl(base, [_row("s", "base", "simp", [0.1, 0.0], [1.0, 0.0])])
    write_jsonl(cand, [
        _row("s", "a", "omega", [0.8, 0.0], [1.0, 0.0]),
        _row("s", "a", "omega", [0.7, 0.0], [1.0, 0.0]),
        _row("s", "b", "bad", [0.9, 0.0], [1.0, 0.0], status="timeout"),
    ])
    rows_out = tmp_path / "rows.jsonl"
    report = tmp_path / "report.json"
    acts = tmp_path / "acts.jsonl"
    rows, summary = run_robust_acceptance(
        base,
        cand,
        rows_out,
        summary_out=report,
        accepted_actions_out=acts,
        margin_threshold=0.0,
        cost_weight=0.0,
        carrier_bonus=0.0,
        goal_bonus=0.0,
        z_value=1.0,
        min_repeats=2,
        min_success_rate=1.0,
    )
    assert summary["n_groups"] == 2
    accepted = [r for r in rows if r["accepted"]]
    assert len(accepted) == 1
    assert accepted[0]["action_id"] == "a"
    out_actions = read_jsonl(acts)
    assert len(out_actions) == 1
    assert out_actions[0]["metadata"]["accepted_by"] == "robust_coker_lcb"


def test_pipeline_qgen_robust_accept(tmp_path: Path):
    out = tmp_path / "run"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--import-mode", "core",
        "--qgen",
        "--audit-qgen-candidates",
        "--qgen-accept-coker",
        "--qgen-robust-accept",
        "--qgen-robust-min-repeats", "1",
        "--qgen-accept-margin", "-10",
    ])
    assert rc == 0
    assert (out / "qgen_robust_acceptance_rows.jsonl").exists()
    assert (out / "qgen_acceptance_report.json").exists()
    assert (out / "qgen_accepted_actions.jsonl").exists()
