import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.schemas import read_jsonl, write_jsonl


MOVED_COMMANDS = {
    "candidates",
    "registry-candidates",
    "build-premise-index",
    "minif2f-fetch",
    "minif2f-tasks",
    "premise-retrieve",
    "premise-actions",
    "premise-candidates",
    "premise-response-registry",
    "premise-response-retrieve",
    "premise-quotient-mine",
    "carrier-actions",
    "accepted-carrier-actions",
    "merge-actions",
    "expose-frontier",
    "goal-shapes",
    "state-ir",
    "parse-states",
    "ir-defects",
    "exposure-report",
    "exposure-candidates",
    "action-report",
    "quotient",
    "carrier-generate",
    "carrier-coker",
    "failure-signatures",
    "seed-defect-registry",
    "mine-defects",
    "promote-registry",
    "auto-defects",
    "audit-defect-atoms",
    "train-response",
    "predict-response",
    "eval-response",
    "select",
    "gamma-audit",
    "gamma-transition-learner",
    "gamma-transition-patch-action-geometry",
    "run-search",
    "focused-audit",
    "make-transitions",
    "dataset-summary",
    "split",
    "carrier-accept",
    "carrier-accept-summary",
    "robust-accept",
    "registry-accept",
    "accept-candidates",
    "merge-action-files",
    "report",
    "expose-frontiers",
    "make-corebench",
    "extract-proofs",
    "replay-proofs",
    "export-proofs",
    "harvest-project",
    "shard-jsonl",
    "merge-jsonl",
    "ir-candidates",
    "carrier-matrix",
    "carrier-matrix-merge-patches",
    "carrier-safe-actions",
    "multi-carrier-report",
    "qgen",
    "qgen-lineage",
    "qgen-acceptance-lineage",
    "qgen-realized-calibration",
    "carrier-patch-audit",
    "robust-accept-candidates",
    "robust-coker-accept",
    "stage-coker",
    "coker-synthesize",
    "quality-gates",
    "synthesize-from-coker",
    "init-lake",
    "action-geometry-registry",
    "action-geometry-retrieve",
    "action-cocycle-audit",
    "arithmetic-teacher-constraints",
    "arithmetic-teacher-graph",
    "arithmetic-teacher-audit",
    "arithmetic-teacher-kernel-audit",
    "arithmetic-teacher-transition-geometry",
    "arithmetic-teacher-cocycle-audit",
    "arithmetic-teacher-cocycle",
    "source-budget-schedule",
    "carrier-quotient-mine",
    "quotient-coordinates",
    "carrier-quotient",
    "carrier-quotient-validate",
    "quotient-coordinate-validate",
    "active-audit-schedule",
    "defect-ontology-reconcile",
    "defect-ontology-lifecycle",
}


def _command_choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("root parser has no subparser action")


def _dummy_for(action: argparse.Action) -> str:
    if action.choices:
        return str(next(iter(action.choices)))
    if action.type is int:
        return "1"
    if action.type is float:
        return "1.0"
    return "dummy"


def _argv_for(command: str, parser: argparse.ArgumentParser) -> list[str]:
    argv = [command]
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if not getattr(action, "required", False):
            continue
        if action.option_strings:
            argv.append(action.option_strings[0])
        value = _dummy_for(action)
        if action.nargs in {"+", "*"}:
            argv.append(value)
        else:
            argv.append(value)
    return argv


def _write_experiment_fixtures(tmp_path: Path) -> dict[str, Path]:
    tasks = tmp_path / "tasks.jsonl"
    responses = tmp_path / "responses.jsonl"
    audits = tmp_path / "audits.jsonl"
    actions = tmp_path / "actions.jsonl"
    defects = tmp_path / "defects.jsonl"
    proposals = tmp_path / "proposals.jsonl"
    write_jsonl(tasks, [{"task_id": "t_true", "statement": "theorem t_true : True := by trivial", "imports": ["Init"]}])
    write_jsonl(actions, [{"action_id": "trivial", "tactic": "trivial", "tactic_class": "trivial", "cost_estimate": 1.0}])
    write_jsonl(
        responses,
        [
            {
                "state_id": "s1",
                "task_id": "t_true",
                "action_id": "trivial",
                "response_flat": [1.0, 0.0],
                "response_keys": ["goal.eq", "carrier.safe"],
                "defect_before": {"flat": [1.0, 0.0], "flat_keys": ["goal.eq", "carrier.safe"]},
                "defect_after": {"flat": [0.0, 0.0], "flat_keys": ["goal.eq", "carrier.safe"]},
                "carrier_delta": {"safe": 0.0},
                "audit_status": "success",
                "status": "success",
                "elapsed_ms": 1,
                "action": {"action_id": "trivial", "tactic": "trivial", "tactic_class": "trivial", "cost_estimate": 1.0},
            }
        ],
    )
    write_jsonl(audits, [{"task_id": "t_true", "target": "True", "status": "success", "state_id": "s1", "action_id": "trivial"}])
    write_jsonl(defects, [{"state_id": "s1", "carrier": {"missing": 1.0}, "flat": [1.0], "flat_keys": ["carrier.missing"]}])
    write_jsonl(proposals, [{"context_id": "ctx_trivial", "task_id": "t_true", "kind": "manual", "suggestions": ["trivial"]}])
    return {"tasks": tasks, "responses": responses, "audits": audits, "actions": actions, "defects": defects, "proposals": proposals}


def test_experiment_cli_modules_import_without_root_cli():
    code = """
import importlib
import sys
importlib.import_module('lean_rgc.experiment')
importlib.import_module('lean_rgc.cli_experiment')
assert 'lean_rgc.cli' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_experiment_facade_reexports_runtime_apis():
    experiment = importlib.import_module("lean_rgc.experiment")
    checks = [
        ("TacticCandidateGenerator", "lean_rgc.candidates"),
        ("CarrierGenerator", "lean_rgc.carrier"),
        ("accept_carrier_contexts", "lean_rgc.carrier_acceptance"),
        ("run_robust_acceptance", "lean_rgc.robust_acceptance"),
        ("qgen_from_files", "lean_rgc.qgen"),
        ("quality_gates_for_run", "lean_rgc.quality"),
        ("source_budget_schedule_from_files", "lean_rgc.source_budget_scheduler"),
        ("reconcile_defect_ontology", "lean_rgc.defect_ontology"),
        ("generate_arithmetic_teacher_graph", "lean_rgc.arithmetic_teacher"),
        ("build_action_geometry_registry", "lean_rgc.action_geometry"),
    ]
    for attr, module_name in checks:
        assert getattr(experiment, attr) is getattr(importlib.import_module(module_name), attr)


def test_experiment_commands_live_in_cli_experiment():
    from lean_rgc.cli import build_parser

    parser = build_parser()
    choices = _command_choices(parser)
    assert MOVED_COMMANDS <= set(choices)
    for command in MOVED_COMMANDS:
        ns = parser.parse_args(_argv_for(command, choices[command]))
        assert ns.func.__module__ == "lean_rgc.cli_experiment"


def test_experiment_split_modules_do_not_import_root_cli_statically():
    root = Path(__file__).resolve().parents[1]
    for rel in ["lean_rgc/cli_experiment.py", "lean_rgc/experiment/__init__.py", "lean_rgc/pipeline.py"]:
        text = (root / rel).read_text(encoding="utf-8")
        assert "from .cli import" not in text
        assert "from ..cli import" not in text
        assert "import lean_rgc.cli" not in text


def test_candidate_premise_and_carrier_smoke(tmp_path: Path):
    fx = _write_experiment_fixtures(tmp_path)
    candidates = tmp_path / "candidates.jsonl"
    index = tmp_path / "premise_index.json"
    hits = tmp_path / "premise_hits.jsonl"
    carrier_actions = tmp_path / "carrier_actions.jsonl"
    carrier_summary = tmp_path / "carrier_summary.json"
    accepted = tmp_path / "accepted.jsonl"
    write_jsonl(accepted, [{"accepted": True, "action": {"action_id": "trivial", "tactic": "trivial"}, "margin": 1.0}])
    assert cli_main(["candidates", "--tasks", str(fx["tasks"]), "--out", str(candidates), "--candidate-mode", "basic"]) == 0
    assert read_jsonl(candidates)
    assert cli_main(["build-premise-index", "--tasks", str(fx["tasks"]), "--actions", str(fx["actions"]), "--out", str(index)]) == 0
    assert cli_main(["premise-retrieve", "--index", str(index), "--tasks", str(fx["tasks"]), "--out", str(hits)]) == 0
    assert hits.exists()
    assert cli_main(["carrier-actions", "--proposals", str(fx["proposals"]), "--out", str(carrier_actions)]) == 0
    assert read_jsonl(carrier_actions)
    assert cli_main(["carrier-accept-summary", "--accepted", str(accepted), "--out", str(carrier_summary)]) == 0
    assert carrier_summary.exists()


def test_qgen_quality_source_budget_and_ontology_smoke(tmp_path: Path):
    fx = _write_experiment_fixtures(tmp_path)
    qgen_dir = tmp_path / "qgen"
    quality = tmp_path / "quality.json"
    source_actions = tmp_path / "source_actions.jsonl"
    ontology = tmp_path / "ontology.jsonl"
    assert cli_main(["qgen", "--responses", str(fx["responses"]), "--audits", str(fx["audits"]), "--out", str(qgen_dir)]) == 0
    assert (qgen_dir / "qgen_report.json").exists()
    assert cli_main(["quality-gates", "--run-dir", str(tmp_path), "--out", str(quality), "--min-audits", "0", "--min-registry-accept", "0"]) == 0
    assert quality.exists()
    assert cli_main(["source-budget-schedule", "--candidates", str(fx["actions"]), "--out-actions", str(source_actions), "--budget", "1"]) == 0
    assert source_actions.exists()
    assert cli_main(["defect-ontology-reconcile", "--candidate-atoms", str(fx["defects"]), "--out", str(ontology)]) == 0
    assert ontology.exists()


def test_arithmetic_teacher_command_registration_smoke():
    from lean_rgc.cli import build_parser

    ns = build_parser().parse_args(["arithmetic-teacher-graph", "--structured-states", "states.jsonl", "--out", "graph.jsonl"])
    assert ns.func.__module__ == "lean_rgc.cli_experiment"
