"""S1 stepwise replay: script splitting and inventory construction."""

from __future__ import annotations

from lean_rgc.evals.stepwise_replay import build_script_inventory, split_script
from lean_rgc.schemas import write_jsonl


def test_split_script_semicolons_and_newlines():
    assert split_script("intro n; rw [h]; ring") == ["intro n", "rw [h]", "ring"]
    assert split_script("constructor\nrfl\nrfl") == ["constructor", "rfl", "rfl"]
    assert split_script("norm_num") == ["norm_num"]


def test_split_script_respects_brackets_and_combinator():
    steps = split_script("rw [h₀, h₁]; simp <;> ring")
    assert steps == ["rw [h₀, h₁]", "simp <;> ring"]


def test_inventory_dedupes_and_counts(tmp_path):
    keys = [f"k{i}" for i in range(34)]
    rows = []
    for status, tactic in (("success", "intro n; rfl"), ("success", "intro n; rfl"), ("fail", "sorry_ish")):
        rows.append({
            "task_id": "tA",
            "status": status,
            "action": {"tactic": tactic, "metadata": {}},
            "defect_before": {"flat": [0.0] * 34, "flat_keys": keys},
            "after_state": {"goals_text": ""},
            "lean_file": "/tmp/x/rgc_bulk_0001.lean",
            "audit_flags": {},
            "messages": [],
        })
    write_jsonl(tmp_path / "runA" / "wave_0" / "micro_audit.jsonl", rows)
    items = build_script_inventory([tmp_path / "runA"], include_d3_prefixes=False)
    assert len(items) == 1
    assert items[0]["task_id"] == "tA"
    assert items[0]["n_steps"] == 2
    assert items[0]["source"] == "success_script"
