from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.structured_state import extract_structured_state
from lean_rgc.schemas import LeanTask, ProofState, AuditRecord
from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig


def test_extract_structured_state_goal_ast_and_context():
    task = LeanTask(task_id="t", imports=[], statement="∀ n : Nat, n = n")
    state = ProofState(
        state_id="s",
        task_id="t",
        goals_text="h : n = n\n⊢ ∀ n : Nat, n = n",
        target="∀ n : Nat, n = n",
        local_context="h : n = n",
    )
    row = extract_structured_state(task=task, state=state).to_dict()
    assert row["schema_version"].startswith("lean-rgc-structured-state-v28")
    assert row["goals"]
    assert row["goals"][0]["target_head"] in {"forall", "eq"}
    assert "GoalAST" not in row  # ensure JSON-like schema, not repr
    assert row["local_context"]["n_nodes"] >= 1
    assert row["canonical_status"] == "structured_state_chart_only_not_canonical"


def test_structured_state_extract_cli_from_tasks_and_audits(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    audits = tmp_path / "audits.jsonl"
    tasks.write_text(json.dumps({"task_id": "t1", "statement": "∀ n : Nat, n = n", "imports": []}) + "\n", encoding="utf-8")
    audits.write_text(json.dumps({
        "task_id": "t1",
        "state_id": "s1",
        "action_id": "intro",
        "status": "partial",
        "target": "∀ n : Nat, n = n",
        "messages": ["1 unsolved goals", "failed to synthesize OfNat Nat 0"],
        "after_state": {"state_id": "s2", "task_id": "t1", "target": "n = n", "goals_text": "n : Nat\n⊢ n = n"},
    }) + "\n", encoding="utf-8")
    out = tmp_path / "structured.jsonl"
    summary = tmp_path / "summary.json"
    assert cli_main(["structured-state-extract", "--tasks", str(tasks), "--audits", str(audits), "--out", str(out), "--summary-out", str(summary)]) == 0
    rows = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    assert len(rows) == 2
    rep = json.loads(summary.read_text())
    assert rep["n_states"] == 2
    assert rep["n_typeclass_obligations"] >= 1


def test_lean_server_structured_state_uses_v28_schema(tmp_path: Path):
    task = LeanTask(task_id="t", imports=[], statement="1 + 1 = 2")
    action = {"action_id": "simp", "tactic": "norm_num", "tactic_class": "arith"}
    with LeanServerAdapter(LeanServerConfig(dry_run=True, workdir=str(tmp_path))) as server:
        rec = server.apply_tactic(task, __import__("lean_rgc.schemas", fromlist=["TacticAction"]).TacticAction.from_dict(action))
        row = server.structured_state(task, rec.after_state or ProofState.from_task(task), rec)
    assert row["schema_version"].startswith("lean-rgc-structured-state-v28")
    assert "goals" in row and isinstance(row["goals"], list)
    assert "local_context" in row
