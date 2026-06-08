import json
from pathlib import Path

from lean_rgc.arithmetic_teacher import generate_arithmetic_teacher_graph
from lean_rgc.arithmetic_teacher_kernel_audit import audit_arithmetic_teacher_kernel_transitions
from lean_rgc.cli import main as cli_main
from lean_rgc.lean_server import LeanServerConfig
from lean_rgc.schemas import write_jsonl


def _states(path: Path):
    write_jsonl(path, [
        {
            "schema_version": "lean-rgc-structured-state-v28.0",
            "state_id": "s_add0",
            "task_id": "nat_add_zero",
            "goals": [{"goal_id": "g0", "mvar_id": "?m.1", "target_text": "∀ n : Nat, n + 0 = n", "domain_tags": ["Nat", "Arith"], "carrier_atoms": ["nat_arith_goal"]}],
            "metavars": {"metavariables": ["?m.1"], "unsolved_goal_count": 1, "synthetic_mvar_count": 0, "entries": []},
            "typeclasses": {"obligations": [], "n_obligations": 0},
        }
    ])


def _tasks(path: Path):
    write_jsonl(path, [
        {"task_id": "nat_add_zero", "imports": ["Mathlib"], "statement": "∀ n : Nat, n + 0 = n", "domain_tags": ["nat", "arithmetic"]}
    ])


def test_kernel_transition_audit_direct(tmp_path: Path):
    states = tmp_path / "states.jsonl"
    tasks = tmp_path / "tasks.jsonl"
    _states(states); _tasks(tasks)
    graph = tmp_path / "arith"
    rep = generate_arithmetic_teacher_graph(states, graph, max_transforms_per_state=8)
    assert rep["n_transformations"] > 0
    out = tmp_path / "kernel"
    krep = audit_arithmetic_teacher_kernel_transitions(
        graph / "arithmetic_teacher_transformations.jsonl",
        tasks,
        out,
        structured_states_path=states,
        server_config=LeanServerConfig(dry_run=True, backend="dry_run"),
        max_transitions=4,
    )
    assert krep["n_audits"] > 0
    assert (out / "arithmetic_teacher_kernel_responses.jsonl").exists()
    assert (out / "arithmetic_teacher_kernel_audit_rows.jsonl").exists()
    rows = [json.loads(x) for x in (out / "arithmetic_teacher_kernel_audit_rows.jsonl").read_text().splitlines() if x.strip()]
    assert rows[0]["canonical_status"].endswith("not_canonical")
    assert "mvar_response" in rows[0]


def test_kernel_transition_audit_cli_and_pipeline(tmp_path: Path):
    states = tmp_path / "states.jsonl"
    tasks = tmp_path / "tasks.jsonl"
    _states(states); _tasks(tasks)
    graph = tmp_path / "arith_cli"
    assert cli_main(["arithmetic-teacher-graph", "--structured-states", str(states), "--out", str(graph)]) == 0
    out = tmp_path / "kernel_cli"
    rc = cli_main([
        "arithmetic-teacher-kernel-audit",
        "--transformations", str(graph / "arithmetic_teacher_transformations.jsonl"),
        "--tasks", str(tasks),
        "--structured-states", str(states),
        "--out", str(out),
        "--dry-run",
        "--server-backend", "dry_run",
        "--max-transitions", "3",
    ])
    assert rc == 0
    assert (out / "arithmetic_teacher_kernel_audit_report.json").exists()

    pipe = tmp_path / "pipe"
    rc = cli_main([
        "pipeline",
        "--tasks", str(tasks),
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(pipe),
        "--dry-run",
        "--max-actions", "2",
        "--arithmetic-teacher-graph",
        "--arithmetic-teacher-structured-states", str(states),
        "--arithmetic-teacher-kernel-audit",
        "--arithmetic-teacher-kernel-audit-max-transitions", "2",
        "--server-backend", "dry_run",
    ])
    assert rc == 0
    assert (pipe / "arithmetic_teacher" / "kernel_transition_audit" / "arithmetic_teacher_kernel_audit_report.json").exists()
