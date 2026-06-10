from __future__ import annotations

import json
from pathlib import Path

from ..dost import (
    _parse_json_or_file,
    write_primitive_observables,
    build_bounded_transcripts,
    build_feature_closure,
    select_features_for_dual_obstructions,
    build_dost_auto_plan,
    compile_experiment_from_auto_plan,
    build_dost_audit_reports,
    run_dost_automation_stack,
    generate_premise_contextual_candidates,
    build_premise_contextual_fingerprints,
    mine_premise_contextual_quotient,
    validate_premise_contextual_quotient,
    retrieve_premise_quotient_classes,
    premise_quotient_retrieved_actions,
    build_premise_use_rows,
    write_separator_contexts,
    generate_bivariate_contextual_candidates,
    schedule_bivariate_candidates,
    build_repair_face_ledger,
    build_dual_face_taxonomy,
    build_canonical_obstruction_tower,
    build_response_completion,
    generate_contextual_candidates,
    contextual_congruence_from_files,
    contextual_response_congruence_from_files,
    build_response_quotient_registry,
    project_actions_by_response_quotient,
    response_quotient_from_congruence_dir,
)


def cmd_dost_primitive_observables(args):
    summary = write_primitive_observables(
        out=args.out,
        report_out=getattr(args, "report_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_bounded_transcripts(args):
    summary = build_bounded_transcripts(
        input_path=args.input,
        out=args.out,
        primitive_observables_out=getattr(args, "primitive_observables_out", None),
        summary_out=getattr(args, "summary_out", None),
        kernel_state_mode=getattr(args, "kernel_state_mode", "features"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_feature_closure(args):
    summary = build_feature_closure(
        transcripts_path=args.transcripts,
        out=args.out,
        values_out=getattr(args, "values_out", None),
        report_out=getattr(args, "report_out", None),
        max_features=getattr(args, "max_features", 512),
        max_category_values=getattr(args, "max_category_values", 16),
        max_interaction_features=getattr(args, "max_interaction_features", 24),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_feature_select(args):
    summary = select_features_for_dual_obstructions(
        feature_closure_path=args.features,
        feature_values_path=args.feature_values,
        out=args.out,
        report_out=getattr(args, "report_out", None),
        taxonomy_path=getattr(args, "taxonomy", None),
        max_selected_per_dual=getattr(args, "max_selected_per_dual", 8),
        cost_weight=getattr(args, "cost_weight", 0.05),
        mem_weight=getattr(args, "mem_weight", 0.10),
        unsafe_weight=getattr(args, "unsafe_weight", 0.25),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_autoplan(args):
    summary = build_dost_auto_plan(
        out=args.out,
        selected_features_path=getattr(args, "selected_features", None),
        taxonomy_path=getattr(args, "taxonomy", None),
        tower_next_actions_path=getattr(args, "tower_next_actions", None),
        tower_summary_path=getattr(args, "tower_summary", None),
        invariant_ledger_path=getattr(args, "invariant_ledger", None),
        cost_model_path=getattr(args, "cost_model", None),
        compiled_experiment_out=getattr(args, "compiled_experiment_out", None),
        notebook_out=getattr(args, "notebook_out", None),
        max_actions=getattr(args, "max_actions", 12),
        kernel_state_mode=getattr(args, "kernel_state_mode", "features"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_compile_experiment(args):
    summary = compile_experiment_from_auto_plan(
        auto_plan_path=args.auto_plan,
        out=args.out,
        notebook_out=getattr(args, "notebook_out", None),
        base_command=getattr(args, "base_command", "lean-rgc pipeline"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_audit_reports(args):
    summary = build_dost_audit_reports(
        out_dir=args.out,
        run_dir=getattr(args, "run_dir", None),
        server_summary_path=getattr(args, "server_summary", None),
        fingerprint_report_path=getattr(args, "fingerprint_report", None),
        fingerprints_path=getattr(args, "fingerprints", None),
        premise_use_rows_path=getattr(args, "premise_use_rows", None),
        classes_path=getattr(args, "classes", None),
        validation_rows_path=getattr(args, "validation", None),
        validation_report_path=getattr(args, "validation_report", None),
        taxonomy_path=getattr(args, "taxonomy", None),
        taxonomy_report_path=getattr(args, "taxonomy_report", None),
        retrieval_faces_path=getattr(args, "retrieval_faces", None),
        tower_summary_path=getattr(args, "tower_summary", None),
        tower_next_actions_path=getattr(args, "tower_next_actions", None),
        dost_report_path=getattr(args, "dost_report", None),
        feature_selection_report_path=getattr(args, "feature_selection_report", None),
        selected_features_path=getattr(args, "selected_features", None),
        responses_path=getattr(args, "responses", None),
        actions_path=getattr(args, "actions", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_dost_stack(args):
    summary = run_dost_automation_stack(
        input_path=args.input,
        out_dir=args.out,
        taxonomy_path=getattr(args, "taxonomy", None),
        tower_next_actions_path=getattr(args, "tower_next_actions", None),
        tower_summary_path=getattr(args, "tower_summary", None),
        max_features=getattr(args, "max_features", 512),
        max_selected_per_dual=getattr(args, "max_selected_per_dual", 8),
        kernel_state_mode=getattr(args, "kernel_state_mode", "features"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_generate(args):
    summary = generate_premise_contextual_candidates(
        premise_actions_path=getattr(args, "premise_actions", None) or getattr(args, "actions", None),
        out=args.out,
        contexts_path=getattr(args, "contexts", None),
        max_premises=getattr(args, "max_premises", None),
        max_left=getattr(args, "max_left", 4),
        max_right=getattr(args, "max_right", 4),
        max_candidates=getattr(args, "max_candidates", None),
        include_identity=not getattr(args, "no_identity", False),
        include_baselines=not getattr(args, "no_baselines", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_fingerprints(args):
    summary = build_premise_contextual_fingerprints(
        responses_path=args.responses,
        actions_path=getattr(args, "actions", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        min_contexts=getattr(args, "min_contexts", 1),
        include_carrier=not getattr(args, "no_carrier", False),
        include_gamma=not getattr(args, "no_gamma", False),
        include_cost=not getattr(args, "no_cost", False),
        include_audit=not getattr(args, "no_audit", False),
        baseline_required=getattr(args, "baseline_required", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_mine(args):
    summary = mine_premise_contextual_quotient(
        fingerprints_path=args.fingerprints,
        out_dir=args.out,
        epsilon=getattr(args, "epsilon", 0.25),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        domain_jaccard_threshold=getattr(args, "domain_jaccard_threshold", 0.0),
        response_weight=getattr(args, "response_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 1.0),
        gamma_weight=getattr(args, "gamma_weight", 0.25),
        domain_weight=getattr(args, "domain_weight", 1.0),
        cost_weight=getattr(args, "cost_weight", 0.05),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.10),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_validate(args):
    summary = validate_premise_contextual_quotient(
        fingerprints_path=args.fingerprints,
        classes_path=args.classes,
        out_rows=args.out_rows,
        out_report=args.out_report,
        holdout_fraction=getattr(args, "holdout_fraction", 0.35),
        epsilon_holdout=getattr(args, "epsilon_holdout", 0.35),
        separation_delta=getattr(args, "separation_delta", 0.10),
        domain_jaccard_min=getattr(args, "domain_jaccard_min", 0.0),
        carrier_mixed_threshold=getattr(args, "carrier_mixed_threshold", 0.05),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_quotient_retrieve(args):
    rn = _parse_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    cn = _parse_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    summary = retrieve_premise_quotient_classes(
        classes_path=args.classes,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        response_normal=rn,
        carrier_normal=cn,
        top_k=getattr(args, "top_k", None),
        gamma_weight=getattr(args, "gamma_weight", 0.10),
        cost_weight=getattr(args, "cost_weight", 0.05),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.10),
        import_cost_weight=getattr(args, "import_cost_weight", 0.05),
        require_validated=getattr(args, "require_validated", False),
    )
    if getattr(args, "out_actions", None):
        act_meta = premise_quotient_retrieved_actions(retrieved_path=args.out, out=args.out_actions)
        summary["actions"] = act_meta
        if getattr(args, "summary_out", None):
            Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_use_rows(args):
    summary = build_premise_use_rows(
        actions_path=args.actions,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        max_rows=getattr(args, "max_rows", None),
        include_context_actions=getattr(args, "include_context_actions", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_separator_contexts(args):
    summary = write_separator_contexts(
        out=args.out,
        templates=getattr(args, "templates", "builtin_core"),
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_bivariate_contextual_generate(args):
    summary = generate_bivariate_contextual_candidates(
        premise_rows_path=args.premise_rows,
        contexts_path=args.contexts,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        max_rows=getattr(args, "max_rows", None),
        max_pre=getattr(args, "max_pre", 8),
        max_post=getattr(args, "max_post", 8),
        max_candidates=getattr(args, "max_candidates", None),
        include_baselines=not getattr(args, "no_baselines", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_bivariate_contextual_schedule(args):
    summary = schedule_bivariate_candidates(
        candidates_path=args.candidates,
        out=args.out,
        budget=getattr(args, "budget", 512),
        report_out=getattr(args, "report_out", None),
        require_baseline_pairs=getattr(args, "require_baseline_pairs", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_repair_face_ledger(args):
    summary = build_repair_face_ledger(
        fingerprints_path=args.fingerprints,
        classes_path=args.classes,
        validation_rows_path=getattr(args, "validation", None),
        out=args.out,
        report_out=getattr(args, "report", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_face_taxonomy(args):
    summary = build_dual_face_taxonomy(
        fingerprints_path=args.fingerprints,
        classes_path=getattr(args, "classes", None),
        validation_rows_path=getattr(args, "validation", None),
        repair_faces_path=getattr(args, "repair_faces", None),
        generated_features_path=getattr(args, "generated_features", None),
        out_dir=args.out,
        min_support=getattr(args, "min_support", 1),
        min_retrieval_support=getattr(args, "min_retrieval_support", 2),
        positive_threshold=getattr(args, "positive_threshold", 1e-9),
        negative_threshold=getattr(args, "negative_threshold", -1e-9),
        carrier_threshold=getattr(args, "carrier_threshold", 1e-12),
        max_concepts=getattr(args, "max_concepts", 256),
        max_pair_properties=getattr(args, "max_pair_properties", 80),
        allow_singleton_retrieval=getattr(args, "allow_singleton_retrieval", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_obstruction_tower(args):
    summary = build_canonical_obstruction_tower(
        out_dir=args.out,
        fingerprints_path=getattr(args, "fingerprints", None),
        taxonomy_dir=getattr(args, "taxonomy_dir", None),
        taxonomy_path=getattr(args, "taxonomy", None),
        concept_lattice_path=getattr(args, "concept_lattice", None),
        row_memberships_path=getattr(args, "row_memberships", None),
        retrieval_faces_path=getattr(args, "retrieval_faces", None),
        repair_faces_path=getattr(args, "repair_faces", None),
        validation_rows_path=getattr(args, "validation", None),
        min_retrieval_support=getattr(args, "min_retrieval_support", 2),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_response_completion(args):
    weights = None
    if getattr(args, "weights", None):
        weights = args.weights
    summary = build_response_completion(
        out=args.out,
        responses_path=getattr(args, "responses", None),
        fingerprints_path=getattr(args, "fingerprints", None),
        action_geometry_path=getattr(args, "action_geometry", None),
        premise_registry_path=getattr(args, "premise_registry", None),
        weights=weights,
        topology=getattr(args, "topology", "weighted_projective"),
        paid_cone_keys=list(getattr(args, "paid_cone_key", []) or []),
        probe_family_id=getattr(args, "probe_family_id", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_contextual_candidates(args):
    rows, summary = generate_contextual_candidates(
        args.actions,
        args.out,
        contexts_path=getattr(args, "contexts", None),
        max_left=getattr(args, "max_left", 8),
        max_right=getattr(args, "max_right", 8),
        max_core=getattr(args, "max_core", None),
        max_candidates=getattr(args, "max_candidates", None),
        include_identity=not getattr(args, "no_identity", False),
        include_left=not getattr(args, "no_left", False),
        include_right=not getattr(args, "no_right", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_congruence(args):
    report = contextual_congruence_from_files(
        args.responses,
        args.out,
        actions_path=getattr(args, "actions", None),
        min_contexts=getattr(args, "min_contexts", 1),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        l2_threshold=getattr(args, "max_distance", None),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_response_congruence(args):
    report = contextual_response_congruence_from_files(
        args.responses,
        args.out,
        context_mode=getattr(args, "context_mode", "state"),
        include_carrier=not getattr(args, "no_carrier", False),
        min_count=getattr(args, "min_count", 1),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        distance_threshold=getattr(args, "distance_threshold", 0.25),
        min_context_jaccard=getattr(args, "min_context_jaccard", 0.0),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_response_quotient_registry(args):
    if getattr(args, "congruence_dir", None):
        report = response_quotient_from_congruence_dir(
            args.congruence_dir,
            actions_path=getattr(args, "actions", None),
            out_dir=args.out,
            min_members=getattr(args, "min_members", 1),
            min_quality=getattr(args, "min_quality", None),
        )
    else:
        report = build_response_quotient_registry(
            args.classes,
            actions_path=getattr(args, "actions", None),
            out_dir=args.out,
            min_members=getattr(args, "min_members", 1),
            min_quality=getattr(args, "min_quality", None),
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_response_quotient_project_actions(args):
    report = project_actions_by_response_quotient(
        args.actions,
        args.registry,
        args.out,
        keep_unmapped=not getattr(args, "drop_unmapped", False),
        annotate_only=getattr(args, "annotate_only", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def register_dost_commands(subparsers) -> None:
    sub = subparsers
    pcg=sub.add_parser('premise-contextual-generate'); pcg.add_argument('--premise-actions'); pcg.add_argument('--actions'); pcg.add_argument('--contexts'); pcg.add_argument('--out', required=True); pcg.add_argument('--summary-out'); pcg.add_argument('--max-premises', type=int); pcg.add_argument('--max-left', type=int, default=4); pcg.add_argument('--max-right', type=int, default=4); pcg.add_argument('--max-candidates', type=int); pcg.add_argument('--no-identity', action='store_true'); pcg.add_argument('--no-baselines', action='store_true'); pcg.set_defaults(func=cmd_premise_contextual_generate)
    pcf=sub.add_parser('premise-contextual-fingerprints'); pcf.add_argument('--responses', required=True); pcf.add_argument('--actions'); pcf.add_argument('--out', required=True); pcf.add_argument('--summary-out'); pcf.add_argument('--min-contexts', type=int, default=1); pcf.add_argument('--baseline-required', action='store_true'); pcf.add_argument('--no-carrier', action='store_true'); pcf.add_argument('--no-gamma', action='store_true'); pcf.add_argument('--no-cost', action='store_true'); pcf.add_argument('--no-audit', action='store_true'); pcf.set_defaults(func=cmd_premise_contextual_fingerprints)
    pcqm=sub.add_parser('premise-contextual-mine'); pcqm.add_argument('--fingerprints', required=True); pcqm.add_argument('--out', required=True); pcqm.add_argument('--epsilon', type=float, default=0.25); pcqm.add_argument('--cosine-threshold', type=float, default=0.95); pcqm.add_argument('--domain-jaccard-threshold', type=float, default=0.0); pcqm.add_argument('--response-weight', type=float, default=1.0); pcqm.add_argument('--carrier-weight', type=float, default=1.0); pcqm.add_argument('--gamma-weight', type=float, default=0.25); pcqm.add_argument('--domain-weight', type=float, default=1.0); pcqm.add_argument('--cost-weight', type=float, default=0.05); pcqm.add_argument('--uncertainty-weight', type=float, default=0.10); pcqm.set_defaults(func=cmd_premise_contextual_mine)
    pcv=sub.add_parser('premise-contextual-validate'); pcv.add_argument('--fingerprints', required=True); pcv.add_argument('--classes', required=True); pcv.add_argument('--out-rows', required=True); pcv.add_argument('--out-report', required=True); pcv.add_argument('--holdout-fraction', type=float, default=0.35); pcv.add_argument('--epsilon-holdout', type=float, default=0.35); pcv.add_argument('--separation-delta', type=float, default=0.10); pcv.add_argument('--domain-jaccard-min', type=float, default=0.0); pcv.add_argument('--carrier-mixed-threshold', type=float, default=0.05); pcv.set_defaults(func=cmd_premise_contextual_validate)
    pqr=sub.add_parser('premise-quotient-retrieve'); pqr.add_argument('--classes', required=True); pqr.add_argument('--out', required=True); pqr.add_argument('--summary-out'); pqr.add_argument('--out-actions'); pqr.add_argument('--response-normal'); pqr.add_argument('--response-normal-json'); pqr.add_argument('--carrier-normal'); pqr.add_argument('--carrier-normal-json'); pqr.add_argument('--top-k', type=int); pqr.add_argument('--gamma-weight', type=float, default=0.10); pqr.add_argument('--cost-weight', type=float, default=0.05); pqr.add_argument('--uncertainty-weight', type=float, default=0.10); pqr.add_argument('--import-cost-weight', type=float, default=0.05); pqr.add_argument('--require-validated', action='store_true'); pqr.set_defaults(func=cmd_premise_quotient_retrieve)
    pur=sub.add_parser('premise-use-rows'); pur.add_argument('--actions', required=True); pur.add_argument('--out', required=True); pur.add_argument('--summary-out'); pur.add_argument('--max-rows', type=int); pur.add_argument('--include-context-actions', action='store_true'); pur.set_defaults(func=cmd_premise_use_rows)
    sep=sub.add_parser('separator-contexts'); sep.add_argument('--templates', choices=['builtin_core','core'], default='builtin_core'); sep.add_argument('--out', required=True); sep.add_argument('--summary-out'); sep.set_defaults(func=cmd_separator_contexts)
    bcg=sub.add_parser('bivariate-contextual-generate'); bcg.add_argument('--premise-rows', required=True); bcg.add_argument('--contexts', required=True); bcg.add_argument('--out', required=True); bcg.add_argument('--summary-out'); bcg.add_argument('--max-rows', type=int); bcg.add_argument('--max-pre', type=int, default=8); bcg.add_argument('--max-post', type=int, default=8); bcg.add_argument('--max-candidates', type=int); bcg.add_argument('--no-baselines', action='store_true'); bcg.set_defaults(func=cmd_bivariate_contextual_generate)
    bcs=sub.add_parser('bivariate-contextual-schedule'); bcs.add_argument('--candidates', required=True); bcs.add_argument('--out', required=True); bcs.add_argument('--budget', type=int, default=512); bcs.add_argument('--report-out'); bcs.add_argument('--require-baseline-pairs', action='store_true'); bcs.set_defaults(func=cmd_bivariate_contextual_schedule)
    rfl=sub.add_parser('repair-face-ledger'); rfl.add_argument('--fingerprints', required=True); rfl.add_argument('--classes', required=True); rfl.add_argument('--validation'); rfl.add_argument('--out', required=True); rfl.add_argument('--report'); rfl.set_defaults(func=cmd_repair_face_ledger)
    ftx=sub.add_parser('face-taxonomy'); ftx.add_argument('--fingerprints', required=True); ftx.add_argument('--classes'); ftx.add_argument('--validation'); ftx.add_argument('--repair-faces'); ftx.add_argument('--generated-features'); ftx.add_argument('--out', required=True); ftx.add_argument('--min-support', type=int, default=1); ftx.add_argument('--min-retrieval-support', type=int, default=2); ftx.add_argument('--positive-threshold', type=float, default=1e-9); ftx.add_argument('--negative-threshold', type=float, default=-1e-9); ftx.add_argument('--carrier-threshold', type=float, default=1e-12); ftx.add_argument('--max-concepts', type=int, default=256); ftx.add_argument('--max-pair-properties', type=int, default=80); ftx.add_argument('--allow-singleton-retrieval', action='store_true'); ftx.set_defaults(func=cmd_face_taxonomy)
    otw=sub.add_parser('obstruction-tower'); otw.add_argument('--out', required=True); otw.add_argument('--fingerprints'); otw.add_argument('--taxonomy-dir'); otw.add_argument('--taxonomy'); otw.add_argument('--concept-lattice'); otw.add_argument('--row-memberships'); otw.add_argument('--retrieval-faces'); otw.add_argument('--repair-faces'); otw.add_argument('--validation'); otw.add_argument('--min-retrieval-support', type=int, default=2); otw.set_defaults(func=cmd_obstruction_tower)
    dpo=sub.add_parser('dost-primitive-observables'); dpo.add_argument('--out', required=True); dpo.add_argument('--report-out'); dpo.set_defaults(func=cmd_dost_primitive_observables)
    dbt=sub.add_parser('dost-bounded-transcripts'); dbt.add_argument('--input', required=True); dbt.add_argument('--out', required=True); dbt.add_argument('--primitive-observables-out'); dbt.add_argument('--summary-out'); dbt.add_argument('--kernel-state-mode', choices=['none','summary','features','full'], default='features'); dbt.set_defaults(func=cmd_dost_bounded_transcripts)
    dfc=sub.add_parser('dost-feature-closure'); dfc.add_argument('--transcripts', required=True); dfc.add_argument('--out', required=True); dfc.add_argument('--values-out'); dfc.add_argument('--report-out'); dfc.add_argument('--max-features', type=int, default=512); dfc.add_argument('--max-category-values', type=int, default=16); dfc.add_argument('--max-interaction-features', type=int, default=24); dfc.set_defaults(func=cmd_dost_feature_closure)
    dfs=sub.add_parser('dost-feature-select'); dfs.add_argument('--features', required=True); dfs.add_argument('--feature-values', required=True); dfs.add_argument('--out', required=True); dfs.add_argument('--report-out'); dfs.add_argument('--taxonomy'); dfs.add_argument('--max-selected-per-dual', type=int, default=8); dfs.add_argument('--cost-weight', type=float, default=0.05); dfs.add_argument('--mem-weight', type=float, default=0.10); dfs.add_argument('--unsafe-weight', type=float, default=0.25); dfs.set_defaults(func=cmd_dost_feature_select)
    dap=sub.add_parser('dost-autoplan'); dap.add_argument('--out', required=True); dap.add_argument('--selected-features'); dap.add_argument('--taxonomy'); dap.add_argument('--tower-next-actions'); dap.add_argument('--tower-summary'); dap.add_argument('--invariant-ledger'); dap.add_argument('--cost-model'); dap.add_argument('--compiled-experiment-out'); dap.add_argument('--notebook-out'); dap.add_argument('--max-actions', type=int, default=12); dap.add_argument('--kernel-state-mode', choices=['none','summary','features','full'], default='features'); dap.set_defaults(func=cmd_dost_autoplan)
    dce=sub.add_parser('dost-compile-experiment'); dce.add_argument('--auto-plan', required=True); dce.add_argument('--out', required=True); dce.add_argument('--notebook-out'); dce.add_argument('--base-command', default='lean-rgc pipeline'); dce.set_defaults(func=cmd_dost_compile_experiment)
    dar=sub.add_parser('dost-audit-reports'); dar.add_argument('--out', required=True); dar.add_argument('--run-dir'); dar.add_argument('--server-summary'); dar.add_argument('--fingerprint-report'); dar.add_argument('--fingerprints'); dar.add_argument('--premise-use-rows'); dar.add_argument('--classes'); dar.add_argument('--validation'); dar.add_argument('--validation-report'); dar.add_argument('--taxonomy'); dar.add_argument('--taxonomy-report'); dar.add_argument('--retrieval-faces'); dar.add_argument('--tower-summary'); dar.add_argument('--tower-next-actions'); dar.add_argument('--dost-report'); dar.add_argument('--feature-selection-report'); dar.add_argument('--selected-features'); dar.add_argument('--responses'); dar.add_argument('--actions'); dar.set_defaults(func=cmd_dost_audit_reports)
    dst=sub.add_parser('dost-stack'); dst.add_argument('--input', required=True); dst.add_argument('--out', required=True); dst.add_argument('--taxonomy'); dst.add_argument('--tower-next-actions'); dst.add_argument('--tower-summary'); dst.add_argument('--max-features', type=int, default=512); dst.add_argument('--max-selected-per-dual', type=int, default=8); dst.add_argument('--kernel-state-mode', choices=['none','summary','features','full'], default='features'); dst.set_defaults(func=cmd_dost_stack)
    rcpl=sub.add_parser('response-completion'); rcpl.add_argument('--out', required=True); rcpl.add_argument('--responses'); rcpl.add_argument('--fingerprints'); rcpl.add_argument('--action-geometry'); rcpl.add_argument('--premise-registry'); rcpl.add_argument('--weights'); rcpl.add_argument('--topology', default='weighted_projective'); rcpl.add_argument('--paid-cone-key', action='append', default=[]); rcpl.add_argument('--probe-family-id'); rcpl.set_defaults(func=cmd_response_completion)
    ccand=sub.add_parser('contextual-candidates'); ccand.add_argument('--actions', required=True); ccand.add_argument('--out', required=True); ccand.add_argument('--contexts'); ccand.add_argument('--summary-out'); ccand.add_argument('--max-left', type=int, default=8); ccand.add_argument('--max-right', type=int, default=8); ccand.add_argument('--max-core', type=int); ccand.add_argument('--max-candidates', type=int); ccand.add_argument('--no-identity', action='store_true'); ccand.add_argument('--no-left', action='store_true'); ccand.add_argument('--no-right', action='store_true'); ccand.set_defaults(func=cmd_contextual_candidates)
    ccong=sub.add_parser('contextual-congruence'); ccong.add_argument('--responses', required=True); ccong.add_argument('--out', required=True); ccong.add_argument('--actions'); ccong.add_argument('--min-contexts', type=int, default=1); ccong.add_argument('--cosine-threshold', type=float, default=0.95); ccong.add_argument('--max-distance', type=float); ccong.set_defaults(func=cmd_contextual_congruence)
    rq=sub.add_parser('response-quotient-registry'); rq.add_argument('--classes'); rq.add_argument('--congruence-dir'); rq.add_argument('--actions'); rq.add_argument('--out', required=True); rq.add_argument('--min-members', type=int, default=1); rq.add_argument('--min-quality', type=float); rq.set_defaults(func=cmd_response_quotient_registry)
    rqp=sub.add_parser('response-quotient-project-actions'); rqp.add_argument('--actions', required=True); rqp.add_argument('--registry', required=True); rqp.add_argument('--out', required=True); rqp.add_argument('--summary-out'); rqp.add_argument('--drop-unmapped', action='store_true'); rqp.add_argument('--annotate-only', action='store_true'); rqp.set_defaults(func=cmd_response_quotient_project_actions)
    crc=sub.add_parser('contextual-response-congruence'); crc.add_argument('--responses', required=True); crc.add_argument('--out', required=True); crc.add_argument('--context-mode', choices=['state','task','global'], default='state'); crc.add_argument('--no-carrier', action='store_true'); crc.add_argument('--min-count', type=int, default=1); crc.add_argument('--cosine-threshold', type=float, default=0.95); crc.add_argument('--distance-threshold', type=float, default=0.25); crc.add_argument('--min-context-jaccard', type=float, default=0.0); crc.set_defaults(func=cmd_contextual_response_congruence)


__all__ = [
    "register_dost_commands",
    "cmd_premise_contextual_generate",
    "cmd_premise_contextual_fingerprints",
    "cmd_premise_contextual_mine",
    "cmd_premise_contextual_validate",
    "cmd_premise_quotient_retrieve",
    "cmd_premise_use_rows",
    "cmd_separator_contexts",
    "cmd_bivariate_contextual_generate",
    "cmd_bivariate_contextual_schedule",
    "cmd_repair_face_ledger",
    "cmd_face_taxonomy",
    "cmd_obstruction_tower",
    "cmd_dost_primitive_observables",
    "cmd_dost_bounded_transcripts",
    "cmd_dost_feature_closure",
    "cmd_dost_feature_select",
    "cmd_dost_autoplan",
    "cmd_dost_compile_experiment",
    "cmd_dost_audit_reports",
    "cmd_dost_stack",
    "cmd_response_completion",
    "cmd_contextual_candidates",
    "cmd_contextual_congruence",
    "cmd_contextual_response_congruence",
    "cmd_response_quotient_registry",
    "cmd_response_quotient_project_actions",
]
