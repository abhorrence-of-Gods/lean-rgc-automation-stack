from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.gamma_transition_learner import learn_gamma_transition_model, merge_gamma_transition_patches_into_action_geometry
from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.cli import main as cli_main


def _transitions(path: Path):
    rows = [
        {"state_id":"s1","action_id":"a","defect":[1.0,0.0],"pred_response":[0.2,0.0],"next_defect":[0.4,0.0],"audit_status":"success"},
        {"state_id":"s2","action_id":"a","defect":[0.0,1.0],"pred_response":[0.0,0.1],"next_defect":[0.0,0.45],"audit_status":"partial"},
        {"state_id":"s3","action_id":"b","defect":[1.0,1.0],"pred_response":[0.0,0.0],"next_defect":[0.8,0.8],"audit_status":"partial"},
    ]
    write_jsonl(path, rows)


def test_gamma_transition_learner_outputs(tmp_path: Path):
    transitions = tmp_path / "transitions.jsonl"
    _transitions(transitions)
    constraints = tmp_path / "constraints.jsonl"
    write_jsonl(constraints, [{"constraint_id":"c1","first":"a","second":"a","composed":"b","accepted":True,"total_cocycle_error":0.01}])
    out = tmp_path / "gamma_transition"
    rep = learn_gamma_transition_model(transitions, out, teacher_constraints_path=constraints, min_count=1, teacher_weight=0.5)
    assert rep["n_valid_transitions"] == 3
    actions = read_jsonl(out / "gamma_transition_actions.jsonl")
    assert {a["action_id"] for a in actions} == {"a", "b"}
    assert (out / "gamma_transition_action_geometry_patches.jsonl").exists()
    assert read_jsonl(out / "gamma_transition_audit_rows.jsonl")


def test_gamma_transition_cli_and_patch(tmp_path: Path):
    transitions = tmp_path / "transitions.jsonl"
    _transitions(transitions)
    out = tmp_path / "gt"
    cli_main(["gamma-transition-learner", "--transitions", str(transitions), "--out", str(out), "--min-count", "1"])
    assert (out / "gamma_transition_report.json").exists()
    ag = tmp_path / "ag.jsonl"
    write_jsonl(ag, [{"action_id":"a","tactic":"simp","response_embedding":[0.1,0.2]}])
    patched = tmp_path / "ag_patched.jsonl"
    cli_main(["gamma-transition-patch-action-geometry", "--action-geometry", str(ag), "--patches", str(out / "gamma_transition_action_geometry_patches.jsonl"), "--out", str(patched)])
    rows = read_jsonl(patched)
    assert rows[0].get("gamma_diag") is not None
    assert "gamma_transition_patch" in rows[0].get("metadata", {})


def test_pipeline_gamma_transition_smoke(tmp_path: Path):
    out = tmp_path / "run"
    cli_main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--import-mode", "core",
        "--gamma-transition-learner",
    ])
    assert (out / "gamma_transition" / "gamma_transition_report.json").exists()
    summary = json.loads((out / "pipeline_summary.json").read_text())
    assert summary["pipeline_files"].get("gamma_transition_report")
