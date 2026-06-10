from pathlib import Path

from lean_rgc.cli import main
from lean_rgc.poms_promotion_service import poms_promotion_decisions, run_poms_promotion_service
from lean_rgc.repair_db import build_repair_db, failure_attribution_report
from lean_rgc.schemas import write_jsonl


def test_repair_db_imports_crg_cgt_artifacts_and_reports_values(tmp_path: Path):
    run = tmp_path / "run"
    crg = run / "crg"
    cgt = run / "concept_geometry"
    crg.mkdir(parents=True)
    cgt.mkdir(parents=True)
    write_jsonl(
        crg / "repair_species_registry.jsonl",
        [
            {
                "repair_atom_id": "atom_a",
                "species_id": "action_distribution",
                "source": "actions",
                "cost_vector": {"cost": 1.0, "audit_risk": 0.1},
                "canonical_status": "repair_witness_not_canonical",
            }
        ],
    )
    write_jsonl(
        crg / "crg_problems.jsonl",
        [
            {
                "problem_id": "crg_1",
                "parent_face_id": "face_1",
                "obstruction_id": "lambda_1",
                "repair_space_scope": "known",
                "canonical_status": "optimization_problem_canonical_candidate_not_generator",
            }
        ],
    )
    write_jsonl(
        crg / "relaxed_candidates.jsonl",
        [
            {
                "candidate_id": "cand_1",
                "problem_id": "crg_1",
                "repair_species": "action_distribution",
                "scores": {"lambda_response": 0.7, "net_score": 0.5, "n_feasible_atoms": 3},
                "canonical_status": "not_canonical_until_poms_promotion",
            }
        ],
    )
    write_jsonl(
        crg / "hardening_attempts.jsonl",
        [
            {
                "hardening_id": "hard_1",
                "candidate_id": "cand_1",
                "hardening_status": "decoded",
                "hardening_gap": 0.2,
                "hard_candidates": [{"action_id": "a1", "tactic": "trivial"}],
                "canonical_status": "hardening_witness_not_canonical",
            }
        ],
    )
    write_jsonl(
        crg / "crg_audit_rows.jsonl",
        [
            {
                "candidate_id": "cand_1",
                "problem_id": "crg_1",
                "relaxed_score": 0.7,
                "audited_score": 0.0,
                "hardening_gap": 0.7,
                "heldout_score": 0.0,
                "ghost_risk": 1.0,
                "source_safe": True,
                "carrier_safe": True,
                "promotion_readiness": "witness_only",
                "canonical_status": "not_canonical_without_parent_nonpaid_dual_least",
            }
        ],
    )
    write_jsonl(cgt / "concept_points.jsonl", [{"concept_id": "z1", "concept_species": "premise_like"}])
    write_jsonl(cgt / "concept_search_rows.jsonl", [{"concept_id": "z1", "score": 0.9, "target_species": "premise_distribution"}])

    db = tmp_path / "repair.sqlite"
    summary = build_repair_db(run, db, include_audit_db=False)
    report = failure_attribution_report(db_path=db)

    assert summary["tables"]["repair_atoms"] == 1
    assert summary["tables"]["crg_audit_rows"] == 1
    assert summary["V_relaxed"] == 0.7
    assert summary["V_hard"] == 0.0
    assert report["diagnosis"] == "hardening_or_grammar_defect"
    assert report["recommended_next"] == "improve_hardening_decoder_or_tactic_grammar"


def test_cli_repair_db_deprecated_commands_still_work(tmp_path: Path):
    run = tmp_path / "run"
    write_jsonl(
        run / "crg" / "crg_audit_rows.jsonl",
        [{"candidate_id": "cand_cli", "problem_id": "crg_cli", "relaxed_score": 0.8, "audited_score": 0.1}],
    )
    db = tmp_path / "repair_cli.sqlite"
    out = tmp_path / "repair_query.json"

    assert main(["repair-db-build", "--run-dir", str(run), "--db", str(db)]) == 0
    assert main(["repair-db-query", "--db", str(db), "--sql", "SELECT COUNT(*) AS n FROM crg_audit_rows", "--out-json", str(out)]) == 0
    assert db.exists()
    assert out.exists()


def test_poms_promotion_service_keeps_canonical_boundary(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    poms_rows = run / "poms_status_rows.jsonl"
    evidence = run / "evidence.jsonl"
    write_jsonl(
        poms_rows,
        [
            {"id": "r1", "kind": "context_action", "action_id": "a1", "poms_status": "accepted_witness"},
            {"id": "r2", "kind": "context_action", "action_id": "a2", "poms_status": "accepted_witness"},
            {"id": "r3", "kind": "context_action", "action_id": "a3", "poms_status": "accepted_witness"},
        ],
    )
    write_jsonl(
        evidence,
        [
            {"action_id": "a2", "parent_nonpaid": True, "dual_certificate": True},
            {"action_id": "a3", "parent_nonpaid": True, "dual_certificate": True, "least_repair": True},
        ],
    )
    db = tmp_path / "poms.sqlite"
    out_jsonl = tmp_path / "decisions.jsonl"

    rep = run_poms_promotion_service(run, db_path=db, evidence=[evidence], out_jsonl=out_jsonl)
    statuses = {row["action_id"]: row["promotion_status"] for row in rep["rows"]}
    canon = {row["action_id"]: row["canonical_status"] for row in rep["rows"]}

    assert statuses["a1"] == "accepted_witness"
    assert statuses["a2"] == "forced_candidate"
    assert statuses["a3"] == "canonical_candidate"
    assert canon["a3"] == "canonical_candidate_not_declared"
    assert out_jsonl.exists()
    stored = poms_promotion_decisions(db)
    assert stored["by_promotion_status"]["canonical_candidate"] == 1
