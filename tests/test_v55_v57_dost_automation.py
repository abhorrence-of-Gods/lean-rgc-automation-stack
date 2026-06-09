from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.dost_automation import (
    build_bounded_transcripts,
    build_dost_audit_reports,
    build_dost_auto_plan,
    build_feature_closure,
    select_features_for_dual_obstructions,
    write_primitive_observables,
)
from lean_rgc.face_taxonomy import build_dual_face_taxonomy
from lean_rgc.kernel_state import KernelGoalStateServer, KernelGoalStateServerConfig
from lean_rgc.obstruction_tower import build_canonical_obstruction_tower
from lean_rgc.schemas import LeanTask, TacticAction, read_jsonl, write_jsonl


def _fingerprints(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "premise_use_id": "u_rfl",
                "premise_id": "rfl",
                "use_mode": "exact",
                "fingerprint": {"ctx:eq::resp::goal.eq": 1.0},
                "domain_support": ["ctx:eq"],
                "status_counts": {"success": 2},
                "response_summary": {"goal.eq": 1.0},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 1.0},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_simp",
                "premise_id": "simp",
                "use_mode": "simp",
                "fingerprint": {"ctx:simp::resp::goal.simp": 1.2},
                "domain_support": ["ctx:simp"],
                "status_counts": {"partial": 1},
                "response_summary": {"goal.simp": 1.2},
                "carrier_summary": {"hidden_obligations": 0.0},
                "gamma_summary": {"tail": 0.2},
                "cost_summary": {"elapsed_ms": 4.0},
                "audit_summary": {"unsafe": 0.0},
            },
            {
                "premise_use_id": "u_bad",
                "premise_id": "bad",
                "use_mode": "macro",
                "fingerprint": {"ctx:simp::carrier::hidden_obligations": -1.0},
                "domain_support": ["ctx:simp"],
                "status_counts": {"success": 1},
                "response_summary": {"goal.simp": 0.8},
                "carrier_summary": {"hidden_obligations": -1.0},
                "gamma_summary": {},
                "cost_summary": {"elapsed_ms": 3.0},
                "audit_summary": {"unsafe": 1.0},
            },
        ],
    )
    return path


def test_kernel_transition_defaults_to_bounded_feature_observations():
    server = KernelGoalStateServer(KernelGoalStateServerConfig(backend="dry_run", kernel_state_mode="features"))
    task = LeanTask(task_id="rfl_task", statement="n = n", imports=[])
    action = TacticAction(action_id="rfl", tactic="rfl")
    base = server.register_task(task)
    transition = server.apply_tactic(base["state"]["state_id"], action)

    assert transition["kernel_state_mode"] == "features"
    assert transition["kernel_state_before"]["mode"] == "features"
    assert transition["kernel_state_before"]["target_head"] == "Eq"
    assert "expr_graph" not in transition["kernel_state_before"]
    assert transition["state_delta"]["goal_count_delta"] < 0
    assert transition["transition_features"]["carrier_safe"] is True


def test_dost_feature_loop_and_face_taxonomy_integration(tmp_path: Path):
    fingerprints = _fingerprints(tmp_path / "fingerprints.jsonl")
    primitive = tmp_path / "primitive_observables.jsonl"
    transcripts = tmp_path / "bounded_transcripts.jsonl"
    features = tmp_path / "feature_closure.jsonl"
    values = tmp_path / "bounded_feature_transcripts.jsonl"

    write_primitive_observables(primitive)
    build_bounded_transcripts(fingerprints, transcripts, primitive_observables_out=tmp_path / "primitive_copy.jsonl")
    build_feature_closure(transcripts, features, values_out=values, max_features=128)

    assert read_jsonl(primitive)
    assert read_jsonl(transcripts)
    assert read_jsonl(features)
    assert read_jsonl(values)

    taxonomy_dir = tmp_path / "taxonomy"
    build_dual_face_taxonomy(
        fingerprints_path=fingerprints,
        generated_features_path=values,
        out_dir=taxonomy_dir,
        min_support=1,
    )
    taxonomy = read_jsonl(taxonomy_dir / "dual_face_taxonomy.jsonl")
    assert taxonomy
    assert any((row.get("positive_face") or {}).get("generated_feature_basis") for row in taxonomy)

    tower_dir = tmp_path / "tower"
    build_canonical_obstruction_tower(
        out_dir=tower_dir,
        fingerprints_path=fingerprints,
        taxonomy_dir=taxonomy_dir,
    )
    assert read_jsonl(tower_dir / "tower_next_actions.jsonl")

    selected = tmp_path / "selected_features.jsonl"
    select_features_for_dual_obstructions(
        features,
        values,
        selected,
        taxonomy_path=taxonomy_dir / "dual_face_taxonomy.jsonl",
    )
    assert read_jsonl(selected)

    plan = tmp_path / "auto_plan.json"
    build_dost_auto_plan(
        plan,
        selected_features_path=selected,
        taxonomy_path=taxonomy_dir / "dual_face_taxonomy.jsonl",
        tower_next_actions_path=tower_dir / "tower_next_actions.jsonl",
        tower_summary_path=tower_dir / "tower_summary.json",
        compiled_experiment_out=tmp_path / "compiled_experiment.sh",
        notebook_out=tmp_path / "compiled_notebook_cells.ipynb",
    )
    assert plan.exists()
    assert (tmp_path / "compiled_experiment.sh").exists()

    server_summary = tmp_path / "server_summary.json"
    server_summary.write_text(
        '{"n_responses": 12, "kernel_context_cache": true, "context_cache_hits": 7, "baseline_missing": 0, "timeout_rate": 0.0, "n_failures": 0, "source_check_calls": 0}',
        encoding="utf-8",
    )
    fingerprint_report = tmp_path / "fingerprint_report.json"
    fingerprint_report.write_text(
        '{"n_unique_context_pairs": 4, "row_degenerate": false, "column_degenerate": false}',
        encoding="utf-8",
    )
    premise_rows = tmp_path / "premise_use_rows.jsonl"
    write_jsonl(
        premise_rows,
        [
            {"premise_use_id": "u_rfl", "tactic": "rfl", "premise_use_nf": {"nf_status": "textual_stub"}},
            {"premise_use_id": "u_simp", "tactic": "simp", "premise_use_nf": {"nf_status": "textual_stub"}},
            {"premise_use_id": "u_bad", "tactic": "aesop", "premise_use_nf": {"nf_status": "textual_stub"}},
        ],
    )
    classes = tmp_path / "premise_quotient_classes.jsonl"
    write_jsonl(classes, [{"class_id": "c0", "member_count": 2}, {"class_id": "c1", "member_count": 1}, {"class_id": "c2", "member_count": 1}])
    validation = tmp_path / "premise_quotient_validation_rows.jsonl"
    write_jsonl(
        validation,
        [
            {"class_id": "c0", "validation_status": "split_suggested"},
            {"class_id": "c1", "validation_status": "carrier_unsafe_mixed_class"},
            {"class_id": "c2", "validation_status": "singleton_vacuously_stable_not_informative"},
        ],
    )
    empty_retrieval = tmp_path / "empty_retrieval_faces.jsonl"
    write_jsonl(empty_retrieval, [])

    audit = build_dost_audit_reports(
        tmp_path / "audit",
        server_summary_path=server_summary,
        fingerprint_report_path=fingerprint_report,
        fingerprints_path=fingerprints,
        premise_use_rows_path=premise_rows,
        classes_path=classes,
        validation_rows_path=validation,
        taxonomy_path=taxonomy_dir / "dual_face_taxonomy.jsonl",
        retrieval_faces_path=empty_retrieval,
        tower_summary_path=tower_dir / "tower_summary.json",
        tower_next_actions_path=tower_dir / "tower_next_actions.jsonl",
        feature_selection_report_path=tmp_path / "feature_selection_report.json",
        selected_features_path=selected,
    )
    assert Path(audit["artifacts"]["invariant_ledger"]).exists()
    assert Path(audit["artifacts"]["audit_dashboard"]).exists()
    blockers = (tmp_path / "audit" / "proof_blocker_report.json").read_text(encoding="utf-8")
    assert "carrier_unsafe_mixed_class" in blockers
    assert "textual_row_universe" in blockers


def test_dost_stack_cli(tmp_path: Path):
    fingerprints = _fingerprints(tmp_path / "fingerprints.jsonl")
    out = tmp_path / "dost"
    assert cli_main(["dost-stack", "--input", str(fingerprints), "--out", str(out), "--max-features", "128"]) == 0
    assert read_jsonl(out / "primitive_observables.jsonl")
    assert read_jsonl(out / "feature_closure.jsonl")
    assert read_jsonl(out / "selected_features.jsonl")
    assert (out / "auto_plan.json").exists()
    assert (out / "audit" / "audit_dashboard.json").exists()
