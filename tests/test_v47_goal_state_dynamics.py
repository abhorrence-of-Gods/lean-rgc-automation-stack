from pathlib import Path
import json
from lean_rgc.goal_state_dynamics import normalize_goal_state_graph, compute_goal_state_transition_delta, goal_state_transitions_from_audits
from lean_rgc.schemas import write_jsonl
from lean_rgc.cli import main


def _kernel(state_id, target, closed=False):
    return {
        "schema_version": "lean-rgc-kernel-state-v28.0",
        "state_id": state_id,
        "task_id": "t",
        "closed": closed,
        "goals": [] if closed else [{"mvar_id": f"?m.{state_id}", "target": {"text": target, "kind": "app", "head": "Eq"}, "local_deps": ["fvar_n"]}],
        "local_context": {"nodes": [{"fvar_id": "fvar_n", "user_name": "n", "type": {"text": "Nat", "head": "Nat"}}], "edges": []},
        "metavars": [] if closed else [{"mvar_id": f"?m.{state_id}", "type_text": target, "assigned": False, "local_deps": ["fvar_n"]}],
        "typeclasses": [],
    }


def test_goal_state_graph_has_expr_lctx_mvar_typeclass():
    g = normalize_goal_state_graph(_kernel("s0", "n = n"))
    assert g["expr_graph"]["n_nodes"] >= 1
    assert g["local_decl_graph"]["n_nodes"] == 1
    assert g["metavariable_graph"]["open_count"] == 1
    assert g["typeclass_graph"]["n_nodes"] == 0
    assert g["state_hash_norm"]


def test_transition_delta_mvar_response():
    d = compute_goal_state_transition_delta(_kernel("s0", "n = n"), _kernel("s1", "", closed=True), action={"action_id":"rfl", "tactic":"rfl"})
    assert d["goal_count_before"] == 1
    assert d["goal_count_after"] == 0
    assert d["mvar_response"] > 0
    assert d["progress_status"] == "closed"


def test_goal_state_transitions_from_audits_cli(tmp_path: Path):
    audits = [{
        "task_id": "t", "state_id": "s0", "action_id": "rfl", "status": "success",
        "audit_flags": {"kernel_state_before": _kernel("s0", "n = n"), "kernel_state_after": _kernel("s1", "", closed=True)}
    }]
    ap = tmp_path / "audits.jsonl"; out = tmp_path / "transitions.jsonl"; rep = tmp_path / "report.json"
    write_jsonl(ap, audits)
    assert main(["goal-state-transitions", "--audits", str(ap), "--out", str(out), "--summary-out", str(rep)]) == 0
    rows = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["mvar_response"] > 0
    assert json.loads(rep.read_text())["n_transitions"] == 1

from lean_rgc.schemas import LeanTask, TacticAction
from lean_rgc.lean_server import audit_with_lean_server, LeanServerConfig


def test_server_audit_writes_goal_state_transitions(tmp_path: Path):
    tasks = [LeanTask(task_id="t", statement="n = n", imports=[])]
    actions = {"t": [TacticAction(action_id="rfl", tactic="rfl")]}
    rep = audit_with_lean_server(tasks, actions, out_dir=tmp_path / "audit", server_config=LeanServerConfig(backend="persistent", dry_run=True), max_actions=1)
    p = tmp_path / "audit" / "goal_state_transitions.jsonl"
    assert p.exists()
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    assert rows
    assert "mvar_response" in rows[0]
    assert "goal_state_transitions" in rep.get("files", {})
