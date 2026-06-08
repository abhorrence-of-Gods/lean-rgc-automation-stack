import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.source_budget_scheduler import (
    CandidateSourceSpec,
    SourceBudgetConfig,
    source_budget_schedule,
)


def test_gamma_aware_source_budget_prefers_tail_stable_candidate(tmp_path: Path):
    good = tmp_path / "good.jsonl"
    bad = tmp_path / "bad.jsonl"
    write_jsonl(good, [{
        "action_id": "good_tail",
        "tactic": "simp",
        "response_keys": ["goal.eq"],
        "response_embedding": [1.0],
        "gamma_tail_value_embedding": [3.0],
        "spectral_radius_proxy": 0.2,
        "metadata": {"source": "action_geometry"},
    }])
    write_jsonl(bad, [{
        "action_id": "bad_tail",
        "tactic": "omega",
        "response_keys": ["goal.eq"],
        "response_embedding": [1.0],
        "gamma_tail_value_embedding": [-1.0],
        "spectral_radius_proxy": 1.8,
        "metadata": {"source": "qgen"},
    }])
    out = tmp_path / "selected.jsonl"
    rows = tmp_path / "rows.jsonl"
    rep = tmp_path / "report.json"
    report = source_budget_schedule(
        [CandidateSourceSpec("good", str(good)), CandidateSourceSpec("bad", str(bad))],
        out_actions=out,
        out_rows=rows,
        out_report=rep,
        response_normal={"goal.eq": 1.0},
        config=SourceBudgetConfig(
            total_budget=1,
            gamma_aware=True,
            gamma_value_weight=1.0,
            gamma_tail_risk_weight=1.0,
            source_exploration_weight=0.0,
        ),
    )
    selected = read_jsonl(out)
    all_rows = read_jsonl(rows)
    assert selected[0]["action_id"] == "good_tail"
    good_row = next(r for r in all_rows if r["action_id"] == "good_tail")
    bad_row = next(r for r in all_rows if r["action_id"] == "bad_tail")
    assert good_row["score"] > bad_row["score"]
    assert good_row["score_terms"]["gamma_tail_value_gain"] > 0
    assert report["gamma_summary"]["gamma_aware"] is True
    assert report["n_selected"] == 1
