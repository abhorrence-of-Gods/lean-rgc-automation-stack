import json
from pathlib import Path
from lean_rgc.arithmetic_teacher import generate_arithmetic_teacher_graph, audit_arithmetic_teacher_transitions
from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import write_jsonl


def _states(path: Path):
    rows = [
        {
            "schema_version": "lean-rgc-structured-state-v28.0",
            "state_id": "s1",
            "task_id": "t1",
            "goals": [{"goal_id": "g0", "mvar_id": "?m.1", "target_text": "n + 0 = n", "domain_tags": ["Nat", "Arith"], "carrier_atoms": ["nat_arith_goal"]}],
            "metavars": {"metavariables": ["?m.1"], "unsolved_goal_count": 1, "synthetic_mvar_count": 0, "entries": []},
            "typeclasses": {"obligations": [], "n_obligations": 0},
        },
        {
            "schema_version": "lean-rgc-structured-state-v28.0",
            "state_id": "s2",
            "task_id": "t2",
            "goals": [{"goal_id": "g0", "mvar_id": "?m.2", "target_text": "n = n", "domain_tags": ["Nat", "Arith"], "carrier_atoms": ["eq_reflexive_goal"]}],
            "metavars": {"metavariables": ["?m.2"], "unsolved_goal_count": 1, "synthetic_mvar_count": 0, "entries": []},
            "typeclasses": {"obligations": [], "n_obligations": 0},
        },
    ]
    write_jsonl(path, rows)


def test_arithmetic_teacher_graph_and_audit(tmp_path: Path):
    states = tmp_path / "states.jsonl"
    _states(states)
    out = tmp_path / "arith"
    rep = generate_arithmetic_teacher_graph(states, out)
    assert rep["n_transformations"] >= 1
    assert (out / "arithmetic_teacher_transformations.jsonl").exists()
    assert (out / "arithmetic_teacher_actions.jsonl").exists()
    trs = [json.loads(line) for line in (out / "arithmetic_teacher_transformations.jsonl").read_text().splitlines() if line.strip()]
    assert any(r["identity_id"] == "add_zero_right" for r in trs)
    audit_out = tmp_path / "arith_audit.jsonl"
    audit_rep = audit_arithmetic_teacher_transitions(out / "arithmetic_teacher_transformations.jsonl", states, audit_out, report_out=tmp_path / "arith_audit_report.json")
    assert audit_rep["n_verified_target_matches"] >= 1


def test_arithmetic_teacher_cli(tmp_path: Path):
    states = tmp_path / "states.jsonl"
    _states(states)
    out = tmp_path / "arith_cli"
    assert cli_main(["arithmetic-teacher-graph", "--structured-states", str(states), "--out", str(out)]) == 0
    assert (out / "arithmetic_teacher_report.json").exists()
    assert cli_main([
        "arithmetic-teacher-audit",
        "--transformations", str(out / "arithmetic_teacher_transformations.jsonl"),
        "--structured-states", str(states),
        "--out-rows", str(tmp_path / "audit_rows.jsonl"),
        "--report-out", str(tmp_path / "audit_report.json"),
    ]) == 0
    assert (tmp_path / "audit_report.json").exists()


def test_pipeline_arithmetic_teacher_graph(tmp_path: Path):
    out = tmp_path / "pipe"
    rc = cli_main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "2",
        "--arithmetic-teacher-graph",
        "--audit-arithmetic-teacher-candidates",
        "--arithmetic-teacher-audit-max-actions", "2",
    ])
    assert rc == 0
    assert (out / "arithmetic_teacher" / "arithmetic_teacher_report.json").exists()
    assert (out / "arithmetic_teacher_audit" / "responses.jsonl").exists()
    summary = json.loads((out / "pipeline_summary.json").read_text())
    files = summary.get("pipeline_files", {})
    assert files.get("arithmetic_teacher_dir")
