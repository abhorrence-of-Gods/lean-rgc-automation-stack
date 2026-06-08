import json
from pathlib import Path

from lean_rgc.arithmetic_teacher_cocycle import (
    build_arithmetic_teacher_transition_geometry,
    audit_arithmetic_teacher_cocycles,
    arithmetic_teacher_cocycle_from_files,
)
from lean_rgc.schemas import write_jsonl
from lean_rgc.cli import main as cli_main


def _kernel_rows(path: Path):
    rows = [
        {
            "transition_id": "tI1", "identity_id": "I", "direction": "forward", "action_id": "aI", "kernel_transition_verified": True,
            "audit_status": "partial", "mvar_measure_before": {"measure": 2.0}, "mvar_measure_after": {"measure": 1.0}, "mvar_response": 1.0,
            "response": {"goal.eq": 0.4}, "carrier_delta": {"arith_carrier": 0.2},
        },
        {
            "transition_id": "tJ1", "identity_id": "J", "direction": "forward", "action_id": "aJ", "kernel_transition_verified": True,
            "audit_status": "partial", "mvar_measure_before": {"measure": 2.0}, "mvar_measure_after": {"measure": 1.5}, "mvar_response": 0.5,
            "response": {"goal.eq": 0.3}, "carrier_delta": {"arith_carrier": 0.1},
        },
        {
            "transition_id": "tJI1", "identity_id": "JI", "direction": "forward", "action_id": "aJI", "kernel_transition_verified": True,
            "audit_status": "partial", "mvar_measure_before": {"measure": 2.0}, "mvar_measure_after": {"measure": 0.75}, "mvar_response": 1.25,
            "response": {"goal.eq": 0.7}, "carrier_delta": {"arith_carrier": 0.3},
        },
    ]
    write_jsonl(path, rows)


def test_transition_geometry_and_cocycle(tmp_path: Path):
    rows = tmp_path / "kernel_rows.jsonl"
    _kernel_rows(rows)
    geom = tmp_path / "geom.jsonl"
    rep = build_arithmetic_teacher_transition_geometry(rows, geom, summary_out=tmp_path / "geom_report.json")
    assert rep["n_transition_geometries"] == 3
    comps = tmp_path / "comps.jsonl"
    write_jsonl(comps, [{"first": "I::forward", "second": "J::forward", "composed": "JI::forward"}])
    out = tmp_path / "cocycles.jsonl"
    crep = audit_arithmetic_teacher_cocycles(geom, out, summary_out=tmp_path / "cocycle_report.json", compositions_path=comps, accept_threshold=2.0)
    assert crep["n_compositions"] == 1
    row = json.loads(out.read_text().splitlines()[0])
    assert row["cocycle_status"] == "audited"
    assert "gamma_cocycle_error" in row
    assert row["canonical_status"].endswith("not_canonical")


def test_arithmetic_teacher_cocycle_cli_and_loop(tmp_path: Path):
    rows = tmp_path / "kernel_rows.jsonl"
    _kernel_rows(rows)
    comps = tmp_path / "comps.jsonl"
    write_jsonl(comps, [{"first": "I::forward", "second": "J::forward", "composed": "JI::forward"}])
    out = tmp_path / "loop"
    rc = cli_main([
        "arithmetic-teacher-cocycle",
        "--kernel-audit-rows", str(rows),
        "--out", str(out),
        "--compositions", str(comps),
        "--accept-threshold", "2.0",
    ])
    assert rc == 0
    assert (out / "arithmetic_teacher_transition_geometry.jsonl").exists()
    assert (out / "arithmetic_teacher_cocycle_rows.jsonl").exists()
    assert (out / "arithmetic_teacher_gamma_constraints.jsonl").exists()


def test_pipeline_arithmetic_teacher_cocycle(tmp_path: Path):
    states = tmp_path / "states.jsonl"
    write_jsonl(states, [{
        "schema_version": "lean-rgc-structured-state-v28.0",
        "state_id": "s_add0",
        "task_id": "nat_add_zero",
        "goals": [{"goal_id": "g0", "mvar_id": "?m.1", "target_text": "∀ n : Nat, n + 0 = n", "domain_tags": ["Nat", "Arith"], "carrier_atoms": ["nat_arith_goal"]}],
        "metavars": {"metavariables": ["?m.1"], "unsolved_goal_count": 1, "synthetic_mvar_count": 0, "entries": []},
        "typeclasses": {"obligations": [], "n_obligations": 0},
    }])
    tasks = tmp_path / "tasks.jsonl"
    write_jsonl(tasks, [{"task_id": "nat_add_zero", "imports": ["Mathlib"], "statement": "∀ n : Nat, n + 0 = n", "domain_tags": ["nat", "arithmetic"]}])
    out = tmp_path / "pipe"
    rc = cli_main([
        "pipeline", "--tasks", str(tasks), "--actions", "examples/core_tactics.jsonl", "--out", str(out), "--dry-run", "--max-actions", "2",
        "--arithmetic-teacher-graph", "--arithmetic-teacher-structured-states", str(states),
        "--arithmetic-teacher-kernel-audit", "--arithmetic-teacher-kernel-audit-max-transitions", "3", "--server-backend", "dry_run",
        "--arithmetic-teacher-cocycle-audit", "--arithmetic-teacher-cocycle-max-auto-pairs", "2",
    ])
    assert rc == 0
    assert (out / "arithmetic_teacher" / "cocycle_audit" / "arithmetic_teacher_cocycle_loop_report.json").exists()
