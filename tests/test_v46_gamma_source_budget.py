import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.source_budget_scheduler import SourceBudgetConfig, source_budget_schedule_from_files


def _read_jsonl(p):
    return [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]


def test_gamma_aware_source_budget_penalizes_unstable_candidate(tmp_path):
    cand = tmp_path / "candidates.jsonl"
    cand.write_text(
        "\n".join([
            json.dumps({
                "action_id": "stable", "tactic": "stable",
                "response_keys": ["goal.eq"], "response_embedding": [1.0],
                "gamma_scalar": 0.1, "spectral_radius_proxy": 0.1,
                "metadata": {"source": "action_geometry"},
            }),
            json.dumps({
                "action_id": "unstable", "tactic": "unstable",
                "response_keys": ["goal.eq"], "response_embedding": [1.0],
                "gamma_scalar": 1.3, "spectral_radius_proxy": 1.3,
                "metadata": {"source": "action_geometry"},
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    out_actions = tmp_path / "out.jsonl"
    out_rows = tmp_path / "rows.jsonl"
    out_report = tmp_path / "report.json"
    report = source_budget_schedule_from_files(
        candidate_specs=[f"action_geometry={cand}"],
        out_actions=out_actions,
        out_rows=out_rows,
        out_report=out_report,
        response_normal={"goal.eq": 1.0},
        config=SourceBudgetConfig(
            total_budget=1,
            gamma_aware=True,
            gamma_value_weight=0.0,
            gamma_tail_risk_weight=1.0,
            gamma_horizon=2,
        ),
    )
    selected = _read_jsonl(out_actions)
    rows = _read_jsonl(out_rows)
    assert selected[0]["action_id"] == "stable"
    assert report["gamma_summary"]["n_adjusted"] == 2
    by_id = {r["action_id"]: r for r in rows}
    assert by_id["unstable"]["score_terms"]["gamma_tail_risk"] > 0
    assert by_id["unstable"]["score"] < by_id["stable"]["score"]


def test_source_budget_cli_accepts_gamma_flags(tmp_path):
    cand = tmp_path / "candidates.jsonl"
    cand.write_text(json.dumps({
        "action_id": "a", "tactic": "a", "response_keys": ["goal.eq"], "response_embedding": [1.0],
        "gamma_scalar": 0.2, "spectral_radius_proxy": 0.2,
    }) + "\n", encoding="utf-8")
    out_actions = tmp_path / "out.jsonl"
    out_report = tmp_path / "report.json"
    result = subprocess.run([
        sys.executable, "-m", "lean_rgc.cli",
        "source-budget-schedule",
        "--candidates", f"action_geometry={cand}",
        "--out-actions", str(out_actions),
        "--out-report", str(out_report),
        "--budget", "1",
        "--response-normal", '{"goal.eq":1.0}',
        "--gamma-aware",
        "--gamma-value-mode", "finite_horizon",
        "--gamma-horizon", "2",
    ], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(out_report.read_text())
    assert report["gamma_summary"]["gamma_aware"] is True
    assert report["gamma_summary"]["gamma_horizon"] == 2
