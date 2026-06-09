import json
from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.crg_audit import audit_crg_candidates
from lean_rgc.crg_hardening import harden_crg_candidates
from lean_rgc.crg_optimizer import optimize_crg_candidates
from lean_rgc.hardening_gap_report import build_hardening_gap_report
from lean_rgc.repair_gradient_flow import repair_gradient_flow_steps
from lean_rgc.schemas import read_jsonl, write_jsonl


def _completion(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "probe_family_id": "completion_test",
                "topology": "weighted_projective_response",
                "response_keys": ["goal.eq"],
                "weights": {"goal.eq": 1.0},
                "paid_cone_keys": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def _problem(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "schema_version": "lean-rgc-crg-problem-v58.0",
                "problem_id": "crg_test",
                "parent_face_id": "face_test",
                "obstruction_id": "lambda_test",
                "objective": {"lambda_normal": {"goal.eq": 1.0}, "type": "support_maximization"},
                "budget": {
                    "cost_max": 0.5,
                    "audit_risk_max": 0.2,
                    "source_risk_max": 0.2,
                    "ghost_risk_max": 0.2,
                    "hardening_cost_max": 1.0,
                },
            }
        ],
    )
    return path


def _registry(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "row_kind": "repair_atom",
                "repair_atom_id": "atom_simp",
                "species_id": "action_distribution",
                "repair_species": "action_distribution",
                "response_embedding": {"goal.eq": 1.0},
                "cost_vector": {"cost": 0.1, "audit_risk": 0.0, "source_risk": 0.0, "ghost_risk": 0.0, "hardening_cost": 0.1},
                "candidate_action": {"action_id": "simp", "tactic": "simp"},
                "canonical_status": "repair_witness_not_canonical",
            },
            {
                "row_kind": "repair_atom",
                "repair_atom_id": "atom_expensive",
                "species_id": "action_distribution",
                "repair_species": "action_distribution",
                "response_embedding": {"goal.eq": 5.0},
                "cost_vector": {"cost": 5.0, "audit_risk": 0.0, "source_risk": 0.0, "ghost_risk": 0.0, "hardening_cost": 0.1},
                "candidate_action": {"action_id": "expensive", "tactic": "aesop"},
                "canonical_status": "repair_witness_not_canonical",
            },
            {
                "row_kind": "repair_atom",
                "repair_atom_id": "atom_rfl",
                "species_id": "action_distribution",
                "repair_species": "action_distribution",
                "response_embedding": {"goal.eq": 0.5},
                "cost_vector": {"cost": 0.1, "audit_risk": 0.0, "source_risk": 0.0, "ghost_risk": 0.0, "hardening_cost": 0.1},
                "candidate_action": {"action_id": "rfl", "tactic": "rfl"},
                "canonical_status": "repair_witness_not_canonical",
            },
        ],
    )
    return path


def test_convex_mixture_optimizer_filters_budget_and_hardens(tmp_path: Path):
    problems = _problem(tmp_path / "problems.jsonl")
    registry = _registry(tmp_path / "registry.jsonl")
    completion = _completion(tmp_path / "completion.json")
    candidates = tmp_path / "relaxed_candidates.jsonl"
    attempts = tmp_path / "hardening_attempts.jsonl"
    hard_actions = tmp_path / "hard_candidates.jsonl"

    summary = optimize_crg_candidates(
        problems_path=problems,
        registry_path=registry,
        response_completion_path=completion,
        out=candidates,
        optimizer="convex_mixture",
        temperature=1.0,
        top_k=3,
    )
    rows = read_jsonl(candidates)
    support = rows[0]["relaxed_object"]["support"]

    assert summary["n_candidates"] == 1
    assert rows[0]["status"] == "relaxed_optimizer_witness"
    assert rows[0]["canonical_status"] == "not_canonical_until_poms_promotion"
    assert abs(sum(float(row["weight"]) for row in support) - 1.0) < 1e-9
    assert {row["repair_atom_id"] for row in support} == {"atom_simp", "atom_rfl"}

    hsummary = harden_crg_candidates(candidates_path=candidates, out_attempts=attempts, out_actions=hard_actions, top_k=2)
    hardening_rows = read_jsonl(attempts)

    assert hsummary["n_hard_actions"] >= 2
    assert hardening_rows[0]["canonical_status"] == "hardening_witness_not_canonical"
    assert {row["tactic"] for row in read_jsonl(hard_actions)} >= {"simp", "rfl"}


def test_crg_audit_gap_report_and_repair_flow(tmp_path: Path):
    problems = _problem(tmp_path / "problems.jsonl")
    registry = _registry(tmp_path / "registry.jsonl")
    completion = _completion(tmp_path / "completion.json")
    candidates = tmp_path / "relaxed_candidates.jsonl"
    attempts = tmp_path / "hardening_attempts.jsonl"
    hard_actions = tmp_path / "hard_candidates.jsonl"
    audit_rows = tmp_path / "crg_audit_rows.jsonl"
    poms = tmp_path / "crg_poms_evidence.jsonl"
    gap = tmp_path / "gap.json"
    flow = tmp_path / "repair_flow_steps.jsonl"

    optimize_crg_candidates(problems_path=problems, registry_path=registry, response_completion_path=completion, out=candidates)
    harden_crg_candidates(candidates_path=candidates, out_attempts=attempts, out_actions=hard_actions, top_k=1)

    hard_action = read_jsonl(hard_actions)[0]
    audited = tmp_path / "responses.jsonl"
    write_jsonl(
        audited,
        [
            {
                "action_id": hard_action["action_id"],
                "action": hard_action,
                "response": {"goal.eq": 0.75},
                "audit_status": "success",
                "carrier_delta": {},
            }
        ],
    )

    summary = audit_crg_candidates(
        candidates_path=candidates,
        hardening_attempts_path=attempts,
        audited_responses_path=audited,
        out_rows=audit_rows,
        poms_out=poms,
    )
    report = build_hardening_gap_report(crg_audit_rows_path=audit_rows, out=gap)
    flow_summary = repair_gradient_flow_steps(
        problems_path=problems,
        registry_path=registry,
        response_completion_path=completion,
        previous_candidates_path=candidates,
        out=flow,
        steps=2,
    )

    row = read_jsonl(audit_rows)[0]
    assert summary["n_audit_rows"] == 1
    assert row["relaxed_score"] > row["audited_score"]
    assert row["promotion_readiness"] in {"promotion_candidate", "paid_witness", "witness_only"}
    assert read_jsonl(poms)[0]["evidence_kind"] == "crg_audit_witness"
    assert report["classification_counts"]["hardening_realized"] == 1
    assert flow_summary["n_steps"] == 2
    assert read_jsonl(flow)[0]["status"] == "flow_step_witness"


def test_pipeline_crg_dry_run_smoke(tmp_path: Path):
    out = tmp_path / "pipe"

    rc = cli_main(
        [
            "pipeline",
            "--tasks",
            "examples/minimal_theorems.jsonl",
            "--actions",
            "examples/core_tactics.jsonl",
            "--out",
            str(out),
            "--dry-run",
            "--import-mode",
            "core",
            "--max-actions",
            "2",
            "--crg",
        ]
    )

    assert rc == 0
    assert (out / "crg" / "response_completion.json").exists()
    assert (out / "crg" / "repair_species_registry.jsonl").exists()
    assert (out / "crg" / "crg_problems.jsonl").exists()
    assert (out / "crg" / "relaxed_candidates.jsonl").exists()
    assert (out / "crg" / "hardening_gap_report.json").exists()
