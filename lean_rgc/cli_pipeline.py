from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli_common import _load_tasks, _normalize_tasks_imports
from .dataset import write_run_report
from .exposure_frontier import write_exposure_frontiers
from .frontier import expose_frontier_files
from .iteration import compare_pipeline_dirs, merge_action_files
from .iteration_report import collect_iteration_report
from .pipeline import run_pipeline
from .schemas import write_jsonl
from .stage_report import default_pipeline_stages, write_stage_report


def cmd_compare_runs(args):
    rows = compare_pipeline_dirs(args.runs, out_json=args.out_json, out_csv=args.out_csv)
    print(json.dumps({"n": len(rows), "runs": rows}, indent=2, ensure_ascii=False)); return 0


def cmd_rgc_loop(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    current_actions = args.actions
    summaries = []
    for i in range(args.rounds):
        rd = out / f"round_{i:02d}"
        rd.mkdir(parents=True, exist_ok=True)
        # Pipeline args mirror cmd_pipeline.  Keep this intentionally explicit so
        # future flags do not silently change loop semantics.
        pipe_args = argparse.Namespace(
            tasks=args.tasks, actions=current_actions, out=str(rd), dry_run=args.dry_run,
            jobs=args.jobs, max_actions=args.max_actions, candidate_mode=args.candidate_mode,
            state_candidates=args.state_candidates, quotient_tolerance=args.quotient_tolerance,
            carrier_threshold=args.carrier_threshold, lean_cmd=args.lean_cmd, workdir=args.workdir,
            timeout_s=args.timeout_s, keep_files=args.keep_files, cache_dir=(str(out/'cache') if args.cache_dir is None else args.cache_dir),
            trace_state=args.trace_state, import_mode=args.import_mode, resume=args.resume,
            flush_every=args.flush_every, fit_gamma=args.fit_gamma, gamma_horizon=args.gamma_horizon,
            qgen=args.qgen, qgen_ridge=1e-4, qgen_max_mass=1.0, qgen_top_defects=args.qgen_top_defects, qgen_top_contexts=args.qgen_top_contexts, qgen_top_carriers=args.qgen_top_carriers, qgen_top_failures=args.qgen_top_failures, qgen_margin_threshold=args.qgen_margin_threshold, qgen_cost_weight=0.05, qgen_carrier_weight=0.25, qgen_audit_penalty=1.0,
            mine_defects=True, mine_min_support=args.mine_min_support,
            mine_min_response_contrast=args.mine_min_response_contrast, mine_min_stability=args.mine_min_stability,
            mine_min_intervention_success=args.mine_min_intervention_success,
            mine_min_coker_reduction=args.mine_min_coker_reduction,
            registry_candidates=True, registry_max_candidates=args.registry_max_candidates,
            audit_registry_candidates=True, registry_audit_max_actions=args.registry_audit_max_actions,
            registry_accept_coker=True, registry_accept_margin=args.registry_accept_margin,
            registry_accept_max_per_task=args.registry_accept_max_per_task,
            registry_accept_cost_weight=args.registry_accept_cost_weight,
            registry_accept_carrier_weight=args.registry_accept_carrier_weight,
            promote_registry=True, promote_min_support=args.promote_min_support,
            promote_min_intervention_success=args.promote_min_intervention_success,
            promote_min_coker_reduction=args.promote_min_coker_reduction,
            promote_min_promotion_score=args.promote_min_promotion_score,
            promote_drop_rejected=False,
            premise_index=args.premise_index, premise_top_k=args.premise_top_k,
            premise_max_actions=args.premise_max_actions, audit_premise_candidates=args.audit_premise_candidates,
            premise_audit_max_actions=args.premise_audit_max_actions,
            carrier_accept=args.carrier_accept, carrier_accept_max_actions=args.carrier_accept_max_actions,
            carrier_accept_margin=args.carrier_accept_margin, carrier_accept_cost_weight=args.carrier_accept_cost_weight,
            promote_carrier_actions=args.promote_carrier_actions, promote_carrier_min_margin=args.promote_carrier_min_margin,
        )
        run_pipeline(pipe_args, emit_stage=True)
        next_actions = out / f"actions_round_{i+1:02d}.jsonl"
        merge_inputs = []
        if current_actions:
            merge_inputs.append(current_actions)
        for candidate in [
            rd/'registry_accepted_actions.jsonl',
            rd/'carrier_promoted_actions.jsonl',
            rd/'qgen'/'qgen_accepted_actions.jsonl' if args.qgen_merge_actions else None,
            rd/'premise_actions.jsonl' if args.merge_premise_actions else None,
        ]:
            if candidate and Path(candidate).exists():
                merge_inputs.append(str(candidate))
        merge_meta = merge_action_files(merge_inputs, next_actions, max_actions=args.next_action_cap)
        summary = compare_pipeline_dirs([rd])[0]
        summaries.append({"round": i, "run_dir": str(rd), "actions_in": current_actions, "actions_out": str(next_actions), "merge": merge_meta, "summary": summary})
        current_actions = str(next_actions)
    (out/'rgc_loop_summary.json').write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding='utf-8')
    compare_pipeline_dirs([x['run_dir'] for x in summaries], out_json=out/'rgc_loop_compare.json', out_csv=out/'rgc_loop_compare.csv')
    print(json.dumps({"rounds": len(summaries), "out": str(out), "summary": str(out/'rgc_loop_summary.json')}, indent=2, ensure_ascii=False)); return 0


def cmd_expose_frontier(args):
    tasks=_normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    norm_path = Path(args.out_tasks).parent / (Path(args.out_tasks).stem + ".input.normalized.jsonl")
    write_jsonl(norm_path, [t.to_dict() for t in tasks])
    executor = _executor_from_args(args)
    summary = write_exposure_frontiers(norm_path, args.out_tasks, args.out_report, executor, max_exposures=args.max_exposures, allow_identity=not args.no_identity)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_frontier_pipeline(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    frontier_tasks = out / "frontier_tasks.jsonl"
    frontier_exposures = out / "frontier_exposures.jsonl"
    frontier_actions = out / "frontier_core_actions.jsonl"
    cmd_expose_frontier(argparse.Namespace(
        tasks=args.tasks,
        out_tasks=str(frontier_tasks),
        out_exposures=str(frontier_exposures),
        out_actions=str(frontier_actions),
        no_identity=args.no_identity,
        max_frontiers_per_task=args.max_frontiers_per_task,
        max_core_actions=args.max_core_actions,
        import_mode=args.import_mode,
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
    ))
    # Run the normal pipeline on exposed frontier states using core actions only.
    pipe_args = argparse.Namespace(
        tasks=str(frontier_tasks), actions=str(frontier_actions), out=str(out / "frontier_run"), dry_run=args.dry_run,
        jobs=args.jobs, max_actions=args.max_actions, candidate_mode="basic", state_candidates=False,
        quotient_tolerance=args.quotient_tolerance, carrier_threshold=args.carrier_threshold,
        lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, keep_files=args.keep_files,
        cache_dir=args.cache_dir or str(out / "cache"), trace_state=args.trace_state, import_mode="preserve", resume=args.resume,
        flush_every=args.flush_every, fit_gamma=args.fit_gamma, gamma_horizon=args.gamma_horizon,
        mine_defects=args.mine_defects, mine_min_support=args.mine_min_support,
        mine_min_response_contrast=args.mine_min_response_contrast, mine_min_stability=args.mine_min_stability,
        mine_min_intervention_success=args.mine_min_intervention_success,
        mine_min_coker_reduction=args.mine_min_coker_reduction,
        registry_candidates=args.registry_candidates, registry_max_candidates=args.registry_max_candidates,
        audit_registry_candidates=args.audit_registry_candidates, registry_audit_max_actions=args.registry_audit_max_actions,
        registry_accept_coker=args.registry_accept_coker, registry_accept_margin=args.registry_accept_margin,
        registry_accept_max_per_task=args.registry_accept_max_per_task, registry_accept_cost_weight=args.registry_accept_cost_weight,
        registry_accept_carrier_weight=args.registry_accept_carrier_weight,
        promote_registry=args.promote_registry, promote_min_support=args.promote_min_support,
        promote_min_intervention_success=args.promote_min_intervention_success,
        promote_min_coker_reduction=args.promote_min_coker_reduction,
        promote_min_promotion_score=args.promote_min_promotion_score,
        promote_drop_rejected=False,
        premise_index=args.premise_index, premise_top_k=args.premise_top_k,
        premise_max_actions=args.premise_max_actions, audit_premise_candidates=args.audit_premise_candidates,
        premise_audit_max_actions=args.premise_audit_max_actions,
        carrier_accept=args.carrier_accept, carrier_accept_max_actions=args.carrier_accept_max_actions,
        carrier_accept_margin=args.carrier_accept_margin, carrier_accept_cost_weight=args.carrier_accept_cost_weight,
        promote_carrier_actions=args.promote_carrier_actions, promote_carrier_min_margin=args.promote_carrier_min_margin,
    )
    run_pipeline(pipe_args, emit_stage=True)
    summary = {
        "frontier_tasks": str(frontier_tasks),
        "frontier_exposures": str(frontier_exposures),
        "frontier_actions": str(frontier_actions),
        "frontier_run": str(out / "frontier_run"),
    }
    (out / "frontier_pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_stage_report(args):
    stages = []
    if getattr(args, "run_dir", None):
        stages.extend(default_pipeline_stages(args.run_dir))
    if getattr(args, "stage", None):
        for spec in args.stage:
            if "=" in spec:
                name, path = spec.split("=", 1)
            else:
                path = spec
                name = Path(path).stem
            stages.append((name, Path(path)))
    rep = write_stage_report(stages, args.out, args.csv_out)
    print(json.dumps({"n_stages": rep.get("n_stages", 0), "out": args.out, "csv": args.csv_out}, indent=2, ensure_ascii=False))
    return 0


def cmd_iterate(args):
    from .iterative import run_iterative_pipeline
    rep = run_iterative_pipeline(
        tasks=args.tasks,
        actions=args.actions,
        out=args.out,
        rounds=args.rounds,
        dry_run=args.dry_run,
        jobs=args.jobs,
        max_actions=args.max_actions,
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        import_mode=args.import_mode,
        cache_dir=args.cache_dir,
        server_cmd=args.server_cmd,
        server_backend=args.server_backend,
        server_no_fallback=args.server_no_fallback,
        native_exec_mode=getattr(args, "native_exec_mode", "source_check"),
        resume=args.resume,
        flush_every=args.flush_every,
        candidate_mode=args.candidate_mode,
        audit_mode=args.audit_mode,
        bulk_batch_size=args.bulk_batch_size,
        frontier_normalize=args.frontier_normalize,
        frontier_max_prefixes=args.frontier_max_prefixes,
        frontier_include_identity=args.frontier_include_identity,
        registry_audit_max_actions=args.registry_audit_max_actions,
        registry_accept_margin=args.registry_accept_margin,
        registry_accept_max_per_task=args.registry_accept_max_per_task,
        promote_registry=args.promote_registry,
        premise_index=args.premise_index,
        audit_premise_candidates=args.audit_premise_candidates,
        premise_audit_max_actions=args.premise_audit_max_actions,
        merge_premise_actions=args.merge_premise_actions,
        carrier_accept=args.carrier_accept,
        carrier_accept_max_actions=args.carrier_accept_max_actions,
        promote_carrier_actions=args.promote_carrier_actions,
        fit_gamma=args.fit_gamma,
        qgen=args.qgen,
        qgen_merge_actions=args.qgen_merge_actions,
        qgen_merge_policy=args.qgen_merge_policy,
        poms_promote=args.poms_promote,
        poms_generate_evidence=getattr(args, "poms_generate_evidence", False),
        poms_evidence_min_relative_residual=getattr(args, "poms_evidence_min_relative_residual", 0.05),
        poms_evidence_min_residual_norm=getattr(args, "poms_evidence_min_residual_norm", 1e-6),
        poms_evidence_min_support_count=getattr(args, "poms_evidence_min_support_count", 1),
        poms_evidence_min_margin=getattr(args, "poms_evidence_min_margin", 0.0),
        poms_evidence_min_robust_margin=getattr(args, "poms_evidence_min_robust_margin", 0.0),
        poms_evidence_least_repair_epsilon=getattr(args, "poms_evidence_least_repair_epsilon", 1e-9),
        poms_promotion_evidence=args.poms_promotion_evidence,
        poms_promote_parent_nonpaid=args.poms_promote_parent_nonpaid,
        poms_promote_dual_certificate=args.poms_promote_dual_certificate,
        poms_promote_least_repair=args.poms_promote_least_repair,
        poms_declare_canonical=args.poms_declare_canonical,
        qgen_top_defects=args.qgen_top_defects,
        qgen_top_contexts=args.qgen_top_contexts,
        qgen_top_carriers=args.qgen_top_carriers,
        qgen_top_failures=args.qgen_top_failures,
        qgen_margin_threshold=args.qgen_margin_threshold,
        qgen_cost_weight=args.qgen_cost_weight,
        qgen_carrier_weight=args.qgen_carrier_weight,
        qgen_audit_penalty=args.qgen_audit_penalty,
        audit_qgen_candidates=args.audit_qgen_candidates,
        qgen_audit_max_actions=args.qgen_audit_max_actions,
        qgen_accept_coker=args.qgen_accept_coker,
        qgen_accept_margin=args.qgen_accept_margin,
        qgen_accept_max_per_task=args.qgen_accept_max_per_task,
        qgen_accept_cost_weight=args.qgen_accept_cost_weight,
        qgen_accept_carrier_weight=args.qgen_accept_carrier_weight,
        qgen_robust_accept=args.qgen_robust_accept,
        qgen_registry_robust_accept=args.qgen_registry_robust_accept,
        qgen_robust_coker_accept=args.qgen_robust_coker_accept,
        qgen_registry_robust_coker_accept=args.qgen_registry_robust_coker_accept,
        qgen_robust_coker_holdout_fraction=args.qgen_robust_coker_holdout_fraction,
        qgen_robust_coker_uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
        qgen_robust_coker_carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
        qgen_robust_coker_audit_penalty=args.qgen_robust_coker_audit_penalty,
        qgen_robust_coker_require_success=args.qgen_robust_coker_require_success,
        qgen_robust_z=args.qgen_robust_z,
        qgen_robust_min_repeats=args.qgen_robust_min_repeats,
        qgen_robust_min_success_rate=args.qgen_robust_min_success_rate,
        qgen_registry_candidates=args.qgen_registry_candidates,
        qgen_registry_max_candidates=args.qgen_registry_max_candidates,
        audit_qgen_registry_candidates=args.audit_qgen_registry_candidates,
        qgen_registry_audit_max_actions=args.qgen_registry_audit_max_actions,
        qgen_registry_accept_coker=args.qgen_registry_accept_coker,
        qgen_registry_accept_margin=args.qgen_registry_accept_margin,
        qgen_registry_accept_max_per_task=args.qgen_registry_accept_max_per_task,
        qgen_registry_accept_cost_weight=args.qgen_registry_accept_cost_weight,
        qgen_registry_accept_carrier_weight=args.qgen_registry_accept_carrier_weight,
        action_geometry=args.action_geometry,
        action_geometry_retrieve=args.action_geometry_retrieve,
        action_geometry_use_qgen_normals=args.action_geometry_use_qgen_normals,
        action_geometry_top_k=args.action_geometry_top_k,
        action_geometry_min_count=args.action_geometry_min_count,
        action_geometry_tail_weight=getattr(args, "action_geometry_tail_weight", 0.25),
        action_geometry_gamma_value_mode=getattr(args, "action_geometry_gamma_value_mode", "local"),
        action_geometry_gamma_horizon=getattr(args, "action_geometry_gamma_horizon", 4),
        action_geometry_gamma_discount=getattr(args, "action_geometry_gamma_discount", 1.0),
        action_geometry_gamma_stability_margin=getattr(args, "action_geometry_gamma_stability_margin", 1.0),
        action_geometry_gamma_tail_value_weight=getattr(args, "action_geometry_gamma_tail_value_weight", 1.0),
        action_geometry_cost_weight=getattr(args, "action_geometry_cost_weight", 0.05),
        action_geometry_uncertainty_weight=getattr(args, "action_geometry_uncertainty_weight", 0.10),
        action_geometry_audit_weight=getattr(args, "action_geometry_audit_weight", 0.20),
        action_geometry_require_carrier_safe=getattr(args, "action_geometry_require_carrier_safe", False),
        action_geometry_carrier_budget=getattr(args, "action_geometry_carrier_budget", 0.0),
        audit_action_geometry_candidates=args.audit_action_geometry_candidates,
        action_geometry_audit_max_actions=args.action_geometry_audit_max_actions,
        action_geometry_accept_coker=args.action_geometry_accept_coker,
        action_geometry_accept_margin=args.action_geometry_accept_margin,
        action_geometry_accept_max_per_task=args.action_geometry_accept_max_per_task,
        action_geometry_accept_cost_weight=args.action_geometry_accept_cost_weight,
        action_geometry_accept_carrier_weight=args.action_geometry_accept_carrier_weight,
        action_geometry_robust_coker_accept=args.action_geometry_robust_coker_accept,
        action_geometry_robust_coker_holdout_fraction=args.action_geometry_robust_coker_holdout_fraction,
        action_geometry_robust_coker_uncertainty_weight=args.action_geometry_robust_coker_uncertainty_weight,
        action_geometry_robust_coker_carrier_gain_weight=args.action_geometry_robust_coker_carrier_gain_weight,
        action_geometry_robust_coker_audit_penalty=args.action_geometry_robust_coker_audit_penalty,
        action_geometry_robust_coker_require_success=args.action_geometry_robust_coker_require_success,
        quotient_coordinates=args.quotient_coordinates,
        quotient_coordinate_merge_actions=args.quotient_coordinate_merge_actions,
        quotient_coordinate_merge_policy=args.quotient_coordinate_merge_policy,
        quotient_coordinate_ridge=args.quotient_coordinate_ridge,
        quotient_coordinate_max_mass=args.quotient_coordinate_max_mass,
        quotient_coordinate_cosine_threshold=args.quotient_coordinate_cosine_threshold,
        quotient_coordinate_min_states=args.quotient_coordinate_min_states,
        quotient_coordinate_top_action_scores=args.quotient_coordinate_top_action_scores,
        quotient_coordinate_margin_threshold=args.quotient_coordinate_margin_threshold,
        quotient_coordinate_validate=args.quotient_coordinate_validate,
        quotient_coordinate_registry_candidates=args.quotient_coordinate_registry_candidates,
        quotient_coordinate_registry_max_candidates=args.quotient_coordinate_registry_max_candidates,
        audit_quotient_coordinate_candidates=args.audit_quotient_coordinate_candidates,
        quotient_coordinate_audit_max_actions=args.quotient_coordinate_audit_max_actions,
        quotient_coordinate_accept_coker=args.quotient_coordinate_accept_coker,
        quotient_coordinate_robust_coker_accept=args.quotient_coordinate_robust_coker_accept,
        quotient_coordinate_accept_margin=args.quotient_coordinate_accept_margin,
        quotient_coordinate_accept_max_per_task=args.quotient_coordinate_accept_max_per_task,
        quotient_coordinate_accept_cost_weight=args.quotient_coordinate_accept_cost_weight,
        quotient_coordinate_accept_carrier_weight=args.quotient_coordinate_accept_carrier_weight,
        quotient_coordinate_robust_coker_holdout_fraction=args.quotient_coordinate_robust_coker_holdout_fraction,
        quotient_coordinate_robust_coker_uncertainty_weight=args.quotient_coordinate_robust_coker_uncertainty_weight,
        quotient_coordinate_robust_coker_carrier_gain_weight=args.quotient_coordinate_robust_coker_carrier_gain_weight,
        quotient_coordinate_robust_coker_audit_penalty=args.quotient_coordinate_robust_coker_audit_penalty,
        quotient_coordinate_robust_coker_require_success=args.quotient_coordinate_robust_coker_require_success,
        carrier_quotient=getattr(args, "carrier_quotient", False),
        carrier_quotient_merge_actions=getattr(args, "carrier_quotient_merge_actions", False),
        carrier_quotient_merge_policy=getattr(args, "carrier_quotient_merge_policy", "robust-only"),
        carrier_quotient_ridge=getattr(args, "carrier_quotient_ridge", 1e-4),
        carrier_quotient_max_mass=getattr(args, "carrier_quotient_max_mass", 1.0),
        carrier_quotient_cosine_threshold=getattr(args, "carrier_quotient_cosine_threshold", 0.85),
        carrier_quotient_min_states=getattr(args, "carrier_quotient_min_states", 1),
        carrier_quotient_top_action_scores=getattr(args, "carrier_quotient_top_action_scores", 128),
        carrier_quotient_margin_threshold=getattr(args, "carrier_quotient_margin_threshold", 0.0),
        audit_carrier_quotient_candidates=getattr(args, "audit_carrier_quotient_candidates", False),
        carrier_quotient_audit_max_actions=getattr(args, "carrier_quotient_audit_max_actions", 16),
        carrier_quotient_accept_coker=getattr(args, "carrier_quotient_accept_coker", False),
        carrier_quotient_robust_coker_accept=getattr(args, "carrier_quotient_robust_coker_accept", False),
        carrier_quotient_accept_margin=getattr(args, "carrier_quotient_accept_margin", 0.0),
        carrier_quotient_accept_max_per_task=getattr(args, "carrier_quotient_accept_max_per_task", 16),
        carrier_quotient_accept_cost_weight=getattr(args, "carrier_quotient_accept_cost_weight", 0.05),
        carrier_quotient_accept_carrier_weight=getattr(args, "carrier_quotient_accept_carrier_weight", 0.7),
        carrier_quotient_robust_coker_holdout_fraction=getattr(args, "carrier_quotient_robust_coker_holdout_fraction", 0.35),
        carrier_quotient_robust_coker_uncertainty_weight=getattr(args, "carrier_quotient_robust_coker_uncertainty_weight", 0.10),
        carrier_quotient_robust_coker_carrier_gain_weight=getattr(args, "carrier_quotient_robust_coker_carrier_gain_weight", 0.25),
        carrier_quotient_robust_coker_audit_penalty=getattr(args, "carrier_quotient_robust_coker_audit_penalty", 1.0),
        carrier_quotient_robust_coker_require_success=getattr(args, "carrier_quotient_robust_coker_require_success", False),
        source_budget=getattr(args, "source_budget", False),
        audit_source_budget_candidates=getattr(args, "audit_source_budget_candidates", False),
        source_budget_merge_actions=getattr(args, "source_budget_merge_actions", False),
        source_budget_merge_policy=getattr(args, "source_budget_merge_policy", "scheduled-only"),
        source_budget_budget=getattr(args, "source_budget_budget", None),
        source_budget_min_per_source=getattr(args, "source_budget_min_per_source", 0),
        source_budget_max_per_source=getattr(args, "source_budget_max_per_source", None),
        source_budget_per_task_cap=getattr(args, "source_budget_per_task_cap", None),
        source_budget_per_action_cap=getattr(args, "source_budget_per_action_cap", 1),
        source_budget_allocation_mode=getattr(args, "source_budget_allocation_mode", "proportional"),
        source_budget_coker_weight=getattr(args, "source_budget_coker_weight", 1.0),
        source_budget_carrier_weight=getattr(args, "source_budget_carrier_weight", 0.5),
        source_budget_uncertainty_weight=getattr(args, "source_budget_uncertainty_weight", 0.20),
        source_budget_novelty_weight=getattr(args, "source_budget_novelty_weight", 0.25),
        source_budget_lineage_weight=getattr(args, "source_budget_lineage_weight", 0.15),
        source_budget_success_weight=getattr(args, "source_budget_success_weight", 0.25),
        source_budget_cost_weight=getattr(args, "source_budget_cost_weight", 0.10),
        source_budget_timeout_weight=getattr(args, "source_budget_timeout_weight", 0.50),
        source_budget_gamma_aware=getattr(args, "source_budget_gamma_aware", False),
        source_budget_gamma_value_mode=getattr(args, "source_budget_gamma_value_mode", "finite_horizon"),
        source_budget_gamma_horizon=getattr(args, "source_budget_gamma_horizon", 4),
        source_budget_gamma_discount=getattr(args, "source_budget_gamma_discount", 1.0),
        source_budget_gamma_value_weight=getattr(args, "source_budget_gamma_value_weight", 0.50),
        source_budget_gamma_tail_risk_weight=getattr(args, "source_budget_gamma_tail_risk_weight", 0.25),
        source_budget_gamma_stability_delta=getattr(args, "source_budget_gamma_stability_delta", 0.05),
        source_budget_gamma_tail_risk_mode=getattr(args, "source_budget_gamma_tail_risk_mode", "spectral"),
        action_geometry_use_quotient_normals=args.action_geometry_use_quotient_normals,
        contextual_congruence=getattr(args, 'contextual_congruence', False),
        contextual_congruence_context_mode=getattr(args, 'contextual_congruence_context_mode', 'state'),
        contextual_congruence_no_carrier=getattr(args, 'contextual_congruence_no_carrier', False),
        contextual_congruence_min_count=getattr(args, 'contextual_congruence_min_count', 1),
        contextual_congruence_cosine_threshold=getattr(args, 'contextual_congruence_cosine_threshold', 0.95),
        contextual_congruence_distance_threshold=getattr(args, 'contextual_congruence_distance_threshold', 0.25),
        contextual_congruence_min_context_jaccard=getattr(args, 'contextual_congruence_min_context_jaccard', 0.0),
        contextual_probes=getattr(args, 'contextual_probes', False),
        contextual_probe_contexts=getattr(args, 'contextual_probe_contexts', None),
        contextual_probe_max_left=getattr(args, 'contextual_probe_max_left', 4),
        contextual_probe_max_right=getattr(args, 'contextual_probe_max_right', 4),
        contextual_probe_max_core=getattr(args, 'contextual_probe_max_core', None),
        contextual_probe_max_candidates=getattr(args, 'contextual_probe_max_candidates', 128),
        contextual_probe_no_identity=getattr(args, 'contextual_probe_no_identity', False),
        contextual_probe_no_left=getattr(args, 'contextual_probe_no_left', False),
        contextual_probe_no_right=getattr(args, 'contextual_probe_no_right', False),
        audit_contextual_probe_candidates=getattr(args, 'audit_contextual_probe_candidates', False),
        contextual_probe_audit_max_actions=getattr(args, 'contextual_probe_audit_max_actions', 24),
        contextual_probe_congruence=getattr(args, 'contextual_probe_congruence', False),
        contextual_probe_congruence_context_mode=getattr(args, 'contextual_probe_congruence_context_mode', 'state'),
        contextual_probe_congruence_no_carrier=getattr(args, 'contextual_probe_congruence_no_carrier', False),
        contextual_probe_congruence_min_count=getattr(args, 'contextual_probe_congruence_min_count', 1),
        contextual_probe_congruence_cosine_threshold=getattr(args, 'contextual_probe_congruence_cosine_threshold', 0.95),
        contextual_probe_congruence_distance_threshold=getattr(args, 'contextual_probe_congruence_distance_threshold', 0.25),
        contextual_probe_congruence_min_context_jaccard=getattr(args, 'contextual_probe_congruence_min_context_jaccard', 0.0),
        contextual_probe_accept_coker=getattr(args, 'contextual_probe_accept_coker', False),
        contextual_probe_robust_coker_accept=getattr(args, 'contextual_probe_robust_coker_accept', False),
        contextual_probe_accept_margin=getattr(args, 'contextual_probe_accept_margin', 0.0),
        contextual_probe_accept_max_per_task=getattr(args, 'contextual_probe_accept_max_per_task', 16),
        contextual_probe_accept_cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
        contextual_probe_accept_carrier_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7),
        contextual_probe_robust_coker_holdout_fraction=getattr(args, 'contextual_probe_robust_coker_holdout_fraction', 0.35),
        contextual_probe_robust_coker_uncertainty_weight=getattr(args, 'contextual_probe_robust_coker_uncertainty_weight', 0.10),
        contextual_probe_robust_coker_carrier_gain_weight=getattr(args, 'contextual_probe_robust_coker_carrier_gain_weight', 0.25),
        contextual_probe_robust_coker_audit_penalty=getattr(args, 'contextual_probe_robust_coker_audit_penalty', 1.0),
        contextual_probe_robust_coker_require_success=getattr(args, 'contextual_probe_robust_coker_require_success', False),
        contextual_probe_merge_actions=getattr(args, 'contextual_probe_merge_actions', False),
        contextual_probe_merge_policy=getattr(args, 'contextual_probe_merge_policy', 'robust-only'),
        response_quotient_registry=getattr(args, 'response_quotient_registry', False),
        response_quotient_min_members=getattr(args, 'response_quotient_min_members', 1),
        response_quotient_min_quality=getattr(args, 'response_quotient_min_quality', None),
        response_quotient_project_actions=getattr(args, 'response_quotient_project_actions', False),
        response_quotient_annotate_only=getattr(args, 'response_quotient_annotate_only', False),
        response_quotient_merge_actions=getattr(args, 'response_quotient_merge_actions', False),
        response_quotient_merge_policy=getattr(args, 'response_quotient_merge_policy', 'representatives'),
        action_geometry_merge_actions=args.action_geometry_merge_actions,
        action_geometry_merge_policy=args.action_geometry_merge_policy,
        audit_db=args.audit_db,
        audit_db_path=args.audit_db_path,
        audit_db_append=args.audit_db_append,
        audit_scheduler=getattr(args, "audit_scheduler", False),
        audit_scheduler_db=getattr(args, "audit_scheduler_db", None),
        audit_scheduler_responses=getattr(args, "audit_scheduler_responses", None),
        audit_scheduler_lineage=getattr(args, "audit_scheduler_lineage", None),
        audit_scheduler_budget=getattr(args, "audit_scheduler_budget", None),
        audit_scheduler_per_task_cap=getattr(args, "audit_scheduler_per_task_cap", None),
        audit_scheduler_per_source_cap=getattr(args, "audit_scheduler_per_source_cap", None),
        audit_scheduler_coker_weight=getattr(args, "audit_scheduler_coker_weight", 1.0),
        audit_scheduler_carrier_weight=getattr(args, "audit_scheduler_carrier_weight", 0.5),
        audit_scheduler_uncertainty_weight=getattr(args, "audit_scheduler_uncertainty_weight", 0.25),
        audit_scheduler_novelty_weight=getattr(args, "audit_scheduler_novelty_weight", 0.15),
        audit_scheduler_success_weight=getattr(args, "audit_scheduler_success_weight", 0.25),
        audit_scheduler_cost_weight=getattr(args, "audit_scheduler_cost_weight", 0.10),
        audit_scheduler_timeout_weight=getattr(args, "audit_scheduler_timeout_weight", 0.50),
        ir_candidates=args.ir_candidates,
        ir_max_candidates=args.ir_max_candidates,
        audit_ir_candidates=args.audit_ir_candidates,
        ir_audit_max_actions=args.ir_audit_max_actions,
        ir_accept_coker=args.ir_accept_coker,
        carrier_matrix=args.carrier_matrix,
        carrier_matrix_budget=args.carrier_matrix_budget,
        carrier_matrix_keep_unsafe=args.carrier_matrix_keep_unsafe,
        carrier_matrix_merge_qgen=args.carrier_matrix_merge_qgen,
        carrier_matrix_qgen_patch_weight=args.carrier_matrix_qgen_patch_weight,
        carrier_matrix_qgen_require_safe=args.carrier_matrix_qgen_require_safe,
        carrier_matrix_qgen_audit_patches=args.carrier_matrix_qgen_audit_patches,
        carrier_matrix_qgen_patch_min_count=args.carrier_matrix_qgen_patch_min_count,
        carrier_matrix_qgen_patch_min_mean_delta=args.carrier_matrix_qgen_patch_min_mean_delta,
        carrier_matrix_qgen_patch_holdout_fraction=args.carrier_matrix_qgen_patch_holdout_fraction,
        carrier_matrix_qgen_patch_require_heldout=args.carrier_matrix_qgen_patch_require_heldout,
        failure_signatures=args.failure_signatures,
        audit_failure_signature_candidates=args.audit_failure_signature_candidates,
        failure_signature_audit_max_actions=args.failure_signature_audit_max_actions,
        failure_signature_accept_coker=args.failure_signature_accept_coker,
        failure_signature_accept_margin=args.failure_signature_accept_margin,
        failure_signature_accept_max_per_task=args.failure_signature_accept_max_per_task,
        next_action_cap=args.next_action_cap,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_iterate_report(args):
    rep = collect_iteration_report(args.run_dir, out_json=args.out_json, out_csv=args.out_csv)
    print(json.dumps({"run_dir": args.run_dir, "n_rounds": len(rep.get("rounds", [])), "out_json": args.out_json, "out_csv": args.out_csv, "trends": rep.get("trends", {})}, indent=2, ensure_ascii=False))
    return 0


def add_response_quotient_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--response-quotient-registry', action='store_true', help='Build a finite action response-quotient registry from contextual congruence classes.')
    parser.add_argument('--response-quotient-min-members', type=int, default=1)
    parser.add_argument('--response-quotient-min-quality', type=float)
    parser.add_argument('--response-quotient-project-actions', action='store_true', help='Project/deduplicate the input action file through the finite response-quotient registry.')
    parser.add_argument('--response-quotient-annotate-only', action='store_true', help='Keep all actions but annotate them with quotient class metadata instead of deduplicating.')
    parser.add_argument('--response-quotient-merge-actions', action='store_true', help='In iterate, merge response-quotient representatives/projected actions into the next action pool.')
    parser.add_argument('--response-quotient-merge-policy', choices=['representatives','projected','all'], default='representatives')

def add_contextual_probe_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--contextual-probes', action='store_true', help='Generate finite A∘C∘B contextual probe candidates from the current action pool.')
    parser.add_argument('--contextual-probe-contexts', help='Optional JSONL actions used as left/right contexts; defaults to --actions.')
    parser.add_argument('--contextual-probe-max-left', type=int, default=4)
    parser.add_argument('--contextual-probe-max-right', type=int, default=4)
    parser.add_argument('--contextual-probe-max-core', type=int)
    parser.add_argument('--contextual-probe-max-candidates', type=int, default=128)
    parser.add_argument('--contextual-probe-no-identity', action='store_true')
    parser.add_argument('--contextual-probe-no-left', action='store_true')
    parser.add_argument('--contextual-probe-no-right', action='store_true')
    parser.add_argument('--audit-contextual-probe-candidates', action='store_true')
    parser.add_argument('--contextual-probe-audit-max-actions', type=int, default=24)
    parser.add_argument('--contextual-probe-congruence', action='store_true')
    parser.add_argument('--contextual-probe-congruence-context-mode', choices=['state','task','global'], default='state')
    parser.add_argument('--contextual-probe-congruence-no-carrier', action='store_true')
    parser.add_argument('--contextual-probe-congruence-min-count', type=int, default=1)
    parser.add_argument('--contextual-probe-congruence-cosine-threshold', type=float, default=0.95)
    parser.add_argument('--contextual-probe-congruence-distance-threshold', type=float, default=0.25)
    parser.add_argument('--contextual-probe-congruence-min-context-jaccard', type=float, default=0.0)
    parser.add_argument('--contextual-probe-accept-coker', action='store_true')
    parser.add_argument('--contextual-probe-robust-coker-accept', action='store_true')
    parser.add_argument('--contextual-probe-accept-margin', type=float, default=0.0)
    parser.add_argument('--contextual-probe-accept-max-per-task', type=int, default=16)
    parser.add_argument('--contextual-probe-accept-cost-weight', type=float, default=0.05)
    parser.add_argument('--contextual-probe-accept-carrier-weight', type=float, default=0.7)
    parser.add_argument('--contextual-probe-robust-coker-holdout-fraction', type=float, default=0.35)
    parser.add_argument('--contextual-probe-robust-coker-uncertainty-weight', type=float, default=0.10)
    parser.add_argument('--contextual-probe-robust-coker-carrier-gain-weight', type=float, default=0.25)
    parser.add_argument('--contextual-probe-robust-coker-audit-penalty', type=float, default=1.0)
    parser.add_argument('--contextual-probe-robust-coker-require-success', action='store_true')
    parser.add_argument('--contextual-probe-merge-actions', action='store_true')
    parser.add_argument('--contextual-probe-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only')

def add_premise_contextual_pipeline_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--premise-contextual-quotient', action='store_true')
    parser.add_argument('--premise-contextual-generate', action='store_true')
    parser.add_argument('--premise-contextual-bivariate', action='store_true')
    parser.add_argument('--premise-contextual-contexts')
    parser.add_argument('--separator-contexts-builtin', choices=['builtin_core','core'], default='builtin_core')
    parser.add_argument('--premise-use-rows-out')
    parser.add_argument('--separator-contexts-out')
    parser.add_argument('--premise-contextual-max-premises', type=int)
    parser.add_argument('--premise-contextual-max-left', type=int, default=4)
    parser.add_argument('--premise-contextual-max-right', type=int, default=4)
    parser.add_argument('--premise-contextual-max-candidates', type=int)
    parser.add_argument('--premise-contextual-baseline-required', action='store_true')
    parser.add_argument('--audit-premise-contextual-candidates', action='store_true')
    parser.add_argument('--premise-contextual-audit-max-actions', type=int, default=32)
    parser.add_argument('--bivariate-audit-budget', type=int)
    parser.add_argument('--bivariate-require-baseline-pairs', action='store_true')
    parser.add_argument('--skip-vacuous-premise-quotient', action='store_true')
    parser.add_argument('--repair-face-ledger', action='store_true')
    parser.add_argument('--face-taxonomy', action='store_true', help='Build finite dual-exposed face taxonomy/concept lattice from bivariate fingerprints.')
    parser.add_argument('--face-taxonomy-min-support', type=int, default=1)
    parser.add_argument('--face-taxonomy-min-retrieval-support', type=int, default=2)
    parser.add_argument('--face-taxonomy-max-concepts', type=int, default=256)
    parser.add_argument('--face-taxonomy-max-pair-properties', type=int, default=80)
    parser.add_argument('--face-taxonomy-allow-singleton-retrieval', action='store_true')
    parser.add_argument('--obstruction-tower', action='store_true', help='Build finite Canonical Obstruction Tower artifacts from the face taxonomy chart.')
    parser.add_argument('--dost-automation', action='store_true', help='Generate primitive observables, feature closure, feature selection, and a DOST auto-plan.')
    parser.add_argument('--kernel-state-mode', choices=['none','summary','features','full'], default='features')
    parser.add_argument('--dost-max-features', type=int, default=512)
    parser.add_argument('--dost-max-selected-per-dual', type=int, default=8)
    parser.add_argument('--premise-contextual-mine', action='store_true')
    parser.add_argument('--premise-contextual-validate', action='store_true')
    parser.add_argument('--premise-contextual-epsilon', type=float, default=0.25)
    parser.add_argument('--premise-contextual-cosine-threshold', type=float, default=0.95)
    parser.add_argument('--premise-contextual-domain-jaccard-threshold', type=float, default=0.0)
    parser.add_argument('--premise-contextual-epsilon-holdout', type=float, default=0.35)
    parser.add_argument('--premise-contextual-separation-delta', type=float, default=0.10)
    parser.add_argument('--premise-quotient-retrieve', action='store_true')
    parser.add_argument('--premise-quotient-top-k', type=int, default=32)
    parser.add_argument('--audit-premise-quotient-candidates', action='store_true')
    parser.add_argument('--premise-quotient-audit-max-actions', type=int, default=16)

def add_crg_pipeline_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--crg', action='store_true')
    parser.add_argument('--crg-build-problems', action='store_true')
    parser.add_argument('--crg-optimize', action='store_true')
    parser.add_argument('--crg-hardening', action='store_true')
    parser.add_argument('--audit-crg-candidates', action='store_true')
    parser.add_argument('--crg-robust-accept', action='store_true')
    parser.add_argument('--crg-audit', action='store_true')
    parser.add_argument('--crg-poms-bridge', action='store_true')
    parser.add_argument('--crg-optimizer', choices=['linear','linear_support','convex','convex_mixture','LinearSupportOptimizer','ConvexMixtureOptimizer'], default='convex_mixture')
    parser.add_argument('--crg-top-k', type=int, default=16)
    parser.add_argument('--crg-temperature', type=float, default=1.0)
    parser.add_argument('--crg-cost-weight', type=float, default=0.0)
    parser.add_argument('--crg-audit-weight', type=float, default=0.0)
    parser.add_argument('--crg-source-weight', type=float, default=0.0)
    parser.add_argument('--crg-ghost-weight', type=float, default=0.0)
    parser.add_argument('--crg-hardening-weight', type=float, default=0.0)
    parser.add_argument('--crg-hardening-top-k', type=int, default=3)
    parser.add_argument('--crg-audit-max-actions', type=int, default=24)
    parser.add_argument('--concept-geometry', action='store_true')
    parser.add_argument('--concept-search', action='store_true')
    parser.add_argument('--concept-decode', action='store_true')
    parser.add_argument('--concept-search-top-k', type=int, default=32)
    parser.add_argument('--concept-search-mode', choices=['response-nearest-neighbor','operation-graph','operation-graph expansion','operation_graph','all'], default='response-nearest-neighbor')


def add_source_budget_pipeline_args(parser: argparse.ArgumentParser, *, include_merge: bool = False) -> None:
    parser.add_argument('--source-budget', action='store_true')
    parser.add_argument('--audit-source-budget-candidates', action='store_true')
    if include_merge:
        parser.add_argument('--source-budget-merge-actions', action='store_true')
        parser.add_argument('--source-budget-merge-policy', choices=['all','scheduled-only'], default='scheduled-only')
    parser.add_argument('--source-budget-budget', type=int)
    parser.add_argument('--source-budget-min-per-source', type=int, default=0)
    parser.add_argument('--source-budget-max-per-source', type=int)
    parser.add_argument('--source-budget-per-task-cap', type=int)
    parser.add_argument('--source-budget-per-action-cap', type=int, default=1)
    parser.add_argument('--source-budget-allocation-mode', choices=['proportional','score','round_robin'], default='proportional')
    parser.add_argument('--source-budget-coker-weight', type=float, default=1.0)
    parser.add_argument('--source-budget-carrier-weight', type=float, default=0.5)
    parser.add_argument('--source-budget-uncertainty-weight', type=float, default=0.20)
    parser.add_argument('--source-budget-novelty-weight', type=float, default=0.25)
    parser.add_argument('--source-budget-lineage-weight', type=float, default=0.15)
    parser.add_argument('--source-budget-success-weight', type=float, default=0.25)
    parser.add_argument('--source-budget-cost-weight', type=float, default=0.10)
    parser.add_argument('--source-budget-timeout-weight', type=float, default=0.50)
    parser.add_argument('--source-budget-gamma-aware', action='store_true')
    parser.add_argument('--source-budget-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='finite_horizon')
    parser.add_argument('--source-budget-gamma-horizon', type=int, default=4)
    parser.add_argument('--source-budget-gamma-discount', type=float, default=1.0)
    parser.add_argument('--source-budget-gamma-value-weight', type=float, default=0.50)
    parser.add_argument('--source-budget-gamma-tail-value-weight', type=float)
    parser.add_argument('--source-budget-gamma-tail-risk-weight', type=float, default=0.50)
    parser.add_argument('--source-budget-gamma-stability-delta', type=float, default=0.05)
    parser.add_argument('--source-budget-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral')
    parser.add_argument('--source-budget-gamma-tail-radius-weight', type=float, default=0.0)


def cmd_pipeline(args):
    rep = run_pipeline(args, emit_stage=True)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def register_pipeline_commands(sub) -> None:
    cr=sub.add_parser('compare-runs'); cr.add_argument('--runs', nargs='+', required=True); cr.add_argument('--out-json'); cr.add_argument('--out-csv'); cr.set_defaults(func=cmd_compare_runs)
    sr=sub.add_parser('stage-report'); sr.add_argument('--run-dir'); sr.add_argument('--stage', action='append', help='NAME=responses.jsonl or responses.jsonl; may be repeated'); sr.add_argument('--out', required=True); sr.add_argument('--csv-out'); sr.set_defaults(func=cmd_stage_report)
    pipe=sub.add_parser('pipeline', conflict_handler='resolve'); pipe.add_argument('--tasks', required=True); pipe.add_argument('--actions'); pipe.add_argument('--out', required=True); pipe.add_argument('--expose-frontier', action='store_true'); pipe.add_argument('--expose-max-exposures', type=int, default=8); pipe.add_argument('--expose-no-identity', action='store_true'); pipe.add_argument('--dry-run', action='store_true'); pipe.add_argument('--jobs', type=int, default=1); pipe.add_argument('--audit-mode', choices=['batch','bulk','server'], default='batch'); pipe.add_argument('--bulk-batch-size', type=int, default=64); pipe.add_argument('--max-actions', type=int, default=32); pipe.add_argument('--frontier-normalize', action='store_true'); pipe.add_argument('--frontier-max-prefixes', type=int, default=8); pipe.add_argument('--frontier-include-identity', action='store_true'); pipe.add_argument('--candidate-mode', choices=['basic','state'], default='state'); pipe.add_argument('--state-candidates', action='store_true'); pipe.add_argument('--quotient-tolerance', type=float, default=0.25); pipe.add_argument('--carrier-threshold', type=float, default=0.1); pipe.add_argument('--lean-cmd', default='lake env lean'); pipe.add_argument('--workdir'); pipe.add_argument('--timeout-s', type=float, default=20.0); pipe.add_argument('--keep-files', action='store_true'); pipe.add_argument('--cache-dir'); pipe.add_argument('--trace-state', action='store_true'); pipe.add_argument('--server-cmd'); pipe.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); pipe.add_argument('--server-no-fallback', action='store_true'); pipe.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); pipe.add_argument('--audit-exposures', action='store_true'); pipe.add_argument('--exposure-audit-max-actions', type=int, default=8); pipe.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); pipe.add_argument('--resume', action='store_true'); pipe.add_argument('--flush-every', type=int, default=50); pipe.add_argument('--fit-gamma', action='store_true'); pipe.add_argument('--gamma-horizon', type=int, default=4); pipe.add_argument('--gamma-transition-learner', action='store_true'); pipe.add_argument('--gamma-transition-min-count', type=int, default=2); pipe.add_argument('--gamma-transition-shrink', type=float, default=4.0); pipe.add_argument('--gamma-transition-ridge', type=float, default=1e-3); pipe.add_argument('--gamma-transition-holdout-fraction', type=float, default=0.25); pipe.add_argument('--gamma-transition-teacher-weight', type=float, default=0.25); pipe.add_argument('--gamma-transition-include-matrices', action='store_true'); pipe.add_argument('--gamma-transition-patch-action-geometry', action='store_true'); pipe.add_argument('--arithmetic-teacher-graph', action='store_true'); pipe.add_argument('--arithmetic-teacher-identities'); pipe.add_argument('--arithmetic-teacher-structured-states'); pipe.add_argument('--arithmetic-teacher-max-transforms-per-state', type=int, default=32); pipe.add_argument('--arithmetic-teacher-no-actions', action='store_true'); pipe.add_argument('--audit-arithmetic-teacher-candidates', action='store_true'); pipe.add_argument('--arithmetic-teacher-audit-max-actions', type=int, default=16); pipe.add_argument('--arithmetic-teacher-kernel-audit', action='store_true'); pipe.add_argument('--arithmetic-teacher-kernel-audit-max-transitions', type=int, default=32); pipe.add_argument('--arithmetic-teacher-cocycle-audit', action='store_true'); pipe.add_argument('--arithmetic-teacher-cocycle-compositions'); pipe.add_argument('--arithmetic-teacher-cocycle-min-count', type=int, default=1); pipe.add_argument('--arithmetic-teacher-cocycle-accept-threshold', type=float, default=1.0); pipe.add_argument('--arithmetic-teacher-cocycle-min-verified-rate', type=float, default=0.0); pipe.add_argument('--arithmetic-teacher-cocycle-max-tail-radius', type=float); pipe.add_argument('--arithmetic-teacher-cocycle-max-auto-pairs', type=int, default=0); pipe.add_argument('--qgen', action='store_true'); pipe.add_argument('--qgen-ridge', type=float, default=1e-4); pipe.add_argument('--qgen-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient', action='store_true'); pipe.add_argument('--carrier-quotient-ridge', type=float, default=1e-4); pipe.add_argument('--carrier-quotient-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient-cosine-threshold', type=float, default=0.85); pipe.add_argument('--carrier-quotient-min-states', type=int, default=1); pipe.add_argument('--carrier-quotient-top-action-scores', type=int, default=128); pipe.add_argument('--carrier-quotient-margin-threshold', type=float, default=0.0); pipe.add_argument('--carrier-quotient-validate', action='store_true'); pipe.add_argument('--carrier-quotient-no-infer-defect-from-violations', action='store_true'); pipe.add_argument('--qgen-top-defects', type=int, default=16); pipe.add_argument('--qgen-top-contexts', type=int, default=32); pipe.add_argument('--qgen-top-carriers', type=int, default=64); pipe.add_argument('--qgen-top-failures', type=int, default=32); pipe.add_argument('--qgen-margin-threshold', type=float, default=0.0); pipe.add_argument('--qgen-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-carrier-weight', type=float, default=0.25); pipe.add_argument('--qgen-audit-penalty', type=float, default=1.0); pipe.add_argument('--audit-qgen-candidates', action='store_true'); pipe.add_argument('--qgen-audit-max-actions', type=int, default=24); pipe.add_argument('--qgen-accept-coker', action='store_true'); pipe.add_argument('--qgen-accept-margin', type=float, default=0.0); pipe.add_argument('--qgen-accept-max-per-task', type=int, default=16); pipe.add_argument('--qgen-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--qgen-robust-accept', action='store_true'); pipe.add_argument('--qgen-registry-robust-accept', action='store_true'); pipe.add_argument('--qgen-robust-coker-accept', action='store_true'); pipe.add_argument('--qgen-registry-robust-coker-accept', action='store_true'); pipe.add_argument('--qgen-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--qgen-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--qgen-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--qgen-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--qgen-robust-coker-require-success', action='store_true'); pipe.add_argument('--qgen-robust-z', type=float, default=1.0); pipe.add_argument('--qgen-robust-min-repeats', type=int, default=1); pipe.add_argument('--qgen-robust-min-success-rate', type=float, default=1.0); pipe.add_argument('--qgen-registry-candidates', action='store_true'); pipe.add_argument('--qgen-registry-max-candidates', type=int, default=64); pipe.add_argument('--audit-qgen-registry-candidates', action='store_true'); pipe.add_argument('--qgen-registry-audit-max-actions', type=int, default=16); pipe.add_argument('--qgen-registry-accept-coker', action='store_true'); pipe.add_argument('--qgen-registry-accept-margin', type=float, default=0.0); pipe.add_argument('--qgen-registry-accept-max-per-task', type=int, default=16); pipe.add_argument('--qgen-registry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-registry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--action-geometry', action='store_true'); pipe.add_argument('--action-geometry-retrieve', action='store_true'); pipe.add_argument('--action-geometry-use-qgen-normals', action='store_true'); pipe.add_argument('--action-geometry-top-k', type=int, default=32); pipe.add_argument('--action-geometry-min-count', type=int, default=1); pipe.add_argument('--action-geometry-tail-weight', type=float, default=0.25); pipe.add_argument('--action-geometry-cost-weight', type=float, default=0.05); pipe.add_argument('--action-geometry-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--action-geometry-audit-weight', type=float, default=0.20); pipe.add_argument('--action-geometry-require-carrier-safe', action='store_true'); pipe.add_argument('--action-geometry-carrier-budget', type=float, default=0.0); pipe.add_argument('--action-geometry-use-gamma-transition', action='store_true'); pipe.add_argument('--action-geometry-gamma-aware', action='store_true'); pipe.add_argument('--action-geometry-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='local'); pipe.add_argument('--action-geometry-gamma-horizon', type=int, default=4); pipe.add_argument('--action-geometry-gamma-discount', type=float, default=1.0); pipe.add_argument('--action-geometry-gamma-tail-value-weight', type=float, default=1.0); pipe.add_argument('--action-geometry-gamma-stability-margin', type=float, default=0.05); pipe.add_argument('--action-geometry-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); pipe.add_argument('--audit-action-geometry-candidates', action='store_true'); pipe.add_argument('--action-geometry-audit-max-actions', type=int, default=24); pipe.add_argument('--action-geometry-accept-coker', action='store_true'); pipe.add_argument('--action-geometry-accept-margin', type=float, default=0.0); pipe.add_argument('--action-geometry-accept-max-per-task', type=int, default=16); pipe.add_argument('--action-geometry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--action-geometry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--action-geometry-robust-coker-accept', action='store_true'); pipe.add_argument('--action-geometry-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--action-geometry-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--action-geometry-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--action-geometry-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--action-geometry-robust-coker-require-success', action='store_true'); pipe.add_argument('--quotient-coordinates', action='store_true'); pipe.add_argument('--quotient-coordinate-ridge', type=float, default=1e-4); pipe.add_argument('--quotient-coordinate-max-mass', type=float, default=1.0); pipe.add_argument('--quotient-coordinate-cosine-threshold', type=float, default=0.85); pipe.add_argument('--quotient-coordinate-min-states', type=int, default=1); pipe.add_argument('--quotient-coordinate-top-action-scores', type=int, default=128); pipe.add_argument('--quotient-coordinate-margin-threshold', type=float, default=0.0); pipe.add_argument('--quotient-coordinate-validate', action='store_true'); pipe.add_argument('--quotient-coordinate-registry-candidates', action='store_true'); pipe.add_argument('--quotient-coordinate-registry-max-candidates', type=int, default=64); pipe.add_argument('--audit-quotient-coordinate-candidates', action='store_true'); pipe.add_argument('--quotient-coordinate-audit-max-actions', type=int, default=16); pipe.add_argument('--quotient-coordinate-accept-coker', action='store_true'); pipe.add_argument('--quotient-coordinate-robust-coker-accept', action='store_true'); pipe.add_argument('--quotient-coordinate-accept-margin', type=float, default=0.0); pipe.add_argument('--quotient-coordinate-accept-max-per-task', type=int, default=16); pipe.add_argument('--quotient-coordinate-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--quotient-coordinate-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--quotient-coordinate-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--quotient-coordinate-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--quotient-coordinate-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--quotient-coordinate-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--quotient-coordinate-robust-coker-require-success', action='store_true'); pipe.add_argument('--action-geometry-use-quotient-normals', action='store_true'); pipe.add_argument('--carrier-quotient', action='store_true'); pipe.add_argument('--carrier-quotient-ridge', type=float, default=1e-4); pipe.add_argument('--carrier-quotient-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient-cosine-threshold', type=float, default=0.85); pipe.add_argument('--carrier-quotient-min-states', type=int, default=1); pipe.add_argument('--carrier-quotient-top-action-scores', type=int, default=128); pipe.add_argument('--carrier-quotient-margin-threshold', type=float, default=0.0); pipe.add_argument('--audit-carrier-quotient-candidates', action='store_true'); pipe.add_argument('--carrier-quotient-audit-max-actions', type=int, default=16); pipe.add_argument('--carrier-quotient-accept-coker', action='store_true'); pipe.add_argument('--carrier-quotient-robust-coker-accept', action='store_true'); pipe.add_argument('--carrier-quotient-accept-margin', type=float, default=0.0); pipe.add_argument('--carrier-quotient-accept-max-per-task', type=int, default=16); pipe.add_argument('--carrier-quotient-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--carrier-quotient-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--carrier-quotient-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--carrier-quotient-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--carrier-quotient-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--carrier-quotient-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--carrier-quotient-robust-coker-require-success', action='store_true'); pipe.add_argument('--carrier-quotient-merge-actions', action='store_true'); pipe.add_argument('--carrier-quotient-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); pipe.add_argument('--contextual-congruence', action='store_true'); pipe.add_argument('--contextual-congruence-context-mode', choices=['state','task','global'], default='state'); pipe.add_argument('--contextual-congruence-no-carrier', action='store_true'); pipe.add_argument('--contextual-congruence-min-count', type=int, default=1); pipe.add_argument('--contextual-congruence-cosine-threshold', type=float, default=0.95); pipe.add_argument('--contextual-congruence-distance-threshold', type=float, default=0.25); pipe.add_argument('--contextual-congruence-min-context-jaccard', type=float, default=0.0); pipe.add_argument('--audit-db', action='store_true'); pipe.add_argument('--audit-db-path'); pipe.add_argument('--audit-db-append', action='store_true'); pipe.add_argument('--run-db', action='store_true'); pipe.add_argument('--run-db-path'); pipe.add_argument('--run-db-append', action='store_true'); pipe.add_argument('--artifact-store-root'); pipe.add_argument('--db-import-artifacts', action='store_true'); pipe.add_argument('--db-materialize-lineage', action='store_true'); pipe.add_argument('--audit-scheduler', action='store_true'); pipe.add_argument('--active-audit-scheduler', dest='audit_scheduler', action='store_true'); pipe.add_argument('--audit-scheduler-db'); pipe.add_argument('--audit-scheduler-responses'); pipe.add_argument('--audit-scheduler-lineage', action='append'); pipe.add_argument('--audit-scheduler-budget', type=int); pipe.add_argument('--audit-scheduler-top-k', dest='audit_scheduler_budget', type=int); pipe.add_argument('--audit-scheduler-per-task-cap', type=int); pipe.add_argument('--audit-scheduler-per-source-cap', type=int); pipe.add_argument('--audit-scheduler-coker-weight', type=float, default=1.0); pipe.add_argument('--audit-scheduler-carrier-weight', type=float, default=0.5); pipe.add_argument('--audit-scheduler-uncertainty-weight', type=float, default=0.25); pipe.add_argument('--audit-scheduler-novelty-weight', type=float, default=0.15); pipe.add_argument('--audit-scheduler-success-weight', type=float, default=0.25); pipe.add_argument('--audit-scheduler-cost-weight', type=float, default=0.10); pipe.add_argument('--audit-scheduler-timeout-weight', type=float, default=0.50); pipe.add_argument('--eval-response-model', action='store_true'); pipe.add_argument('--response-eval-mode', choices=['mean','lcb'], default='mean'); pipe.add_argument('--mine-defects', action='store_true'); pipe.add_argument('--mine-min-support', type=int, default=1); pipe.add_argument('--mine-min-response-contrast', type=float, default=-1e9); pipe.add_argument('--mine-min-stability', type=float, default=0.0); pipe.add_argument('--mine-min-intervention-success', type=float, default=0.0); pipe.add_argument('--mine-min-coker-reduction', type=float, default=0.0); pipe.add_argument('--registry-candidates', action='store_true'); pipe.add_argument('--registry-max-candidates', type=int, default=96); pipe.add_argument('--audit-registry-candidates', action='store_true'); pipe.add_argument('--registry-audit-max-actions', type=int, default=32); pipe.add_argument('--registry-accept-coker', action='store_true'); pipe.add_argument('--registry-accept-margin', type=float, default=0.0); pipe.add_argument('--registry-accept-max-per-task', type=int, default=16); pipe.add_argument('--registry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--registry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--promote-registry', action='store_true'); pipe.add_argument('--promote-min-support', type=int, default=1); pipe.add_argument('--promote-min-intervention-success', type=float, default=0.1); pipe.add_argument('--promote-min-coker-reduction', type=float, default=-1e9); pipe.add_argument('--promote-min-promotion-score', type=float, default=-1e9); pipe.add_argument('--promote-drop-rejected', action='store_true'); pipe.add_argument('--premise-index', action='store_true'); pipe.add_argument('--premise-top-k', type=int, default=8); pipe.add_argument('--premise-max-actions', type=int, default=8); pipe.add_argument('--audit-premise-candidates', action='store_true'); pipe.add_argument('--premise-audit-max-actions', type=int, default=24); pipe.add_argument('--premise-response-registry', action='store_true'); pipe.add_argument('--premise-response-retrieve', action='store_true'); pipe.add_argument('--premise-response-top-k', type=int, default=32); pipe.add_argument('--premise-quotient-mine', action='store_true'); pipe.add_argument('--audit-premise-response-candidates', action='store_true'); pipe.add_argument('--premise-response-audit-max-actions', type=int, default=16); pipe.add_argument('--carrier-accept', action='store_true'); pipe.add_argument('--carrier-accept-max-actions', type=int, default=8); pipe.add_argument('--carrier-accept-margin', type=float, default=0.0); pipe.add_argument('--carrier-accept-cost-weight', type=float, default=0.1); pipe.add_argument('--promote-carrier-actions', action='store_true'); pipe.add_argument('--promote-carrier-min-margin', type=float, default=0.0); pipe.add_argument('--ir-candidates', action='store_true'); pipe.add_argument('--ir-max-candidates', type=int, default=64); pipe.add_argument('--audit-ir-candidates', action='store_true'); pipe.add_argument('--ir-audit-max-actions', type=int, default=24); pipe.add_argument('--ir-accept-coker', action='store_true'); pipe.add_argument('--ir-accept-margin', type=float, default=0.0); pipe.add_argument('--ir-accept-max-per-task', type=int, default=16); pipe.add_argument('--ir-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--ir-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--carrier-matrix', action='store_true'); pipe.add_argument('--carrier-matrix-shrink', type=float, default=2.0); pipe.add_argument('--carrier-matrix-min-count', type=int, default=1); pipe.add_argument('--carrier-matrix-budget', type=float, default=0.0); pipe.add_argument('--carrier-matrix-keep-unsafe', action='store_true'); pipe.add_argument('--carrier-matrix-merge-qgen', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-patch-weight', type=float, default=1.0); pipe.add_argument('--carrier-matrix-qgen-require-safe', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-audit-patches', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-patch-min-count', type=int, default=1); pipe.add_argument('--carrier-matrix-qgen-patch-min-mean-delta', type=float, default=0.0); pipe.add_argument('--carrier-matrix-qgen-patch-holdout-fraction', type=float, default=0.0); pipe.add_argument('--carrier-matrix-qgen-patch-require-heldout', action='store_true'); pipe.add_argument('--failure-signatures', action='store_true'); pipe.add_argument('--failure-signature-min-support', type=int, default=1); pipe.add_argument('--audit-failure-signature-candidates', action='store_true'); pipe.add_argument('--failure-signature-audit-max-actions', type=int, default=16); pipe.add_argument('--failure-signature-accept-coker', action='store_true'); pipe.add_argument('--failure-signature-accept-margin', type=float, default=0.0); pipe.add_argument('--failure-signature-accept-max-per-task', type=int, default=16); pipe.add_argument('--failure-signature-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--failure-signature-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--stage-coker', action='store_true'); pipe.add_argument('--stage-coker-margin', type=float, default=0.0); pipe.add_argument('--stage-coker-cost-weight', type=float, default=0.05); pipe.add_argument('--stage-coker-carrier-weight', type=float, default=0.25); pipe.add_argument('--stage-coker-max-actions', type=int); add_contextual_probe_args(pipe); add_response_quotient_args(pipe); add_premise_contextual_pipeline_args(pipe); add_crg_pipeline_args(pipe);
    add_source_budget_pipeline_args(pipe)
    pipe.set_defaults(func=cmd_pipeline)
    it=sub.add_parser('iterate', conflict_handler='resolve'); it.add_argument('--tasks', required=True); it.add_argument('--actions'); it.add_argument('--out', required=True); it.add_argument('--rounds', type=int, default=2); it.add_argument('--dry-run', action='store_true'); it.add_argument('--jobs', type=int, default=1); it.add_argument('--audit-mode', choices=['batch','bulk','server'], default='batch'); it.add_argument('--bulk-batch-size', type=int, default=64); it.add_argument('--max-actions', type=int, default=32); it.add_argument('--candidate-mode', choices=['basic','state'], default='state'); it.add_argument('--frontier-normalize', action='store_true'); it.add_argument('--frontier-max-prefixes', type=int, default=8); it.add_argument('--frontier-include-identity', action='store_true'); it.add_argument('--lean-cmd', default='lake env lean'); it.add_argument('--workdir'); it.add_argument('--timeout-s', type=float, default=20.0); it.add_argument('--cache-dir'); it.add_argument('--server-cmd'); it.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); it.add_argument('--server-no-fallback', action='store_true'); it.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); it.add_argument('--resume', action='store_true'); it.add_argument('--flush-every', type=int, default=50); it.add_argument('--registry-audit-max-actions', type=int, default=16); it.add_argument('--registry-accept-margin', type=float, default=0.0); it.add_argument('--registry-accept-max-per-task', type=int, default=16); it.add_argument('--promote-registry', action='store_true'); it.add_argument('--premise-index', action='store_true'); it.add_argument('--audit-premise-candidates', action='store_true'); it.add_argument('--premise-audit-max-actions', type=int, default=16); it.add_argument('--premise-response-registry', action='store_true'); it.add_argument('--premise-response-retrieve', action='store_true'); it.add_argument('--premise-response-top-k', type=int, default=32); it.add_argument('--premise-quotient-mine', action='store_true'); it.add_argument('--audit-premise-response-candidates', action='store_true'); it.add_argument('--premise-response-audit-max-actions', type=int, default=16); it.add_argument('--merge-premise-response-actions', action='store_true'); it.add_argument('--merge-premise-actions', action='store_true'); it.add_argument('--carrier-accept', action='store_true'); it.add_argument('--carrier-accept-max-actions', type=int, default=8); it.add_argument('--promote-carrier-actions', action='store_true'); it.add_argument('--carrier-matrix', action='store_true'); it.add_argument('--carrier-matrix-budget', type=float, default=0.0); it.add_argument('--carrier-matrix-keep-unsafe', action='store_true'); it.add_argument('--carrier-matrix-merge-qgen', action='store_true'); it.add_argument('--carrier-matrix-qgen-patch-weight', type=float, default=1.0); it.add_argument('--carrier-matrix-qgen-require-safe', action='store_true'); it.add_argument('--carrier-matrix-qgen-audit-patches', action='store_true'); it.add_argument('--carrier-matrix-qgen-patch-min-count', type=int, default=1); it.add_argument('--carrier-matrix-qgen-patch-min-mean-delta', type=float, default=0.0); it.add_argument('--carrier-matrix-qgen-patch-holdout-fraction', type=float, default=0.0); it.add_argument('--carrier-matrix-qgen-patch-require-heldout', action='store_true'); it.add_argument('--ir-candidates', action='store_true'); it.add_argument('--ir-max-candidates', type=int, default=64); it.add_argument('--audit-ir-candidates', action='store_true'); it.add_argument('--ir-audit-max-actions', type=int, default=24); it.add_argument('--ir-accept-coker', action='store_true'); it.add_argument('--next-action-cap', type=int); it.add_argument('--failure-signatures', action='store_true'); it.add_argument('--audit-failure-signature-candidates', action='store_true'); it.add_argument('--failure-signature-audit-max-actions', type=int, default=16); it.add_argument('--failure-signature-accept-coker', action='store_true'); it.add_argument('--failure-signature-accept-margin', type=float, default=0.0); it.add_argument('--failure-signature-accept-max-per-task', type=int, default=16); it.add_argument('--fit-gamma', action='store_true'); it.add_argument('--action-geometry', action='store_true'); it.add_argument('--action-geometry-retrieve', action='store_true'); it.add_argument('--action-geometry-use-qgen-normals', action='store_true'); it.add_argument('--action-geometry-merge-actions', action='store_true'); it.add_argument('--action-geometry-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); it.add_argument('--audit-db', action='store_true'); it.add_argument('--audit-db-path'); it.add_argument('--audit-db-append', action='store_true'); it.add_argument('--audit-scheduler', action='store_true'); it.add_argument('--audit-scheduler-db'); it.add_argument('--audit-scheduler-responses'); it.add_argument('--audit-scheduler-lineage', action='append'); it.add_argument('--audit-scheduler-budget', type=int); it.add_argument('--audit-scheduler-per-task-cap', type=int); it.add_argument('--audit-scheduler-per-source-cap', type=int); it.add_argument('--audit-scheduler-coker-weight', type=float, default=1.0); it.add_argument('--audit-scheduler-carrier-weight', type=float, default=0.5); it.add_argument('--audit-scheduler-uncertainty-weight', type=float, default=0.25); it.add_argument('--audit-scheduler-novelty-weight', type=float, default=0.15); it.add_argument('--audit-scheduler-success-weight', type=float, default=0.25); it.add_argument('--audit-scheduler-cost-weight', type=float, default=0.10); it.add_argument('--audit-scheduler-timeout-weight', type=float, default=0.50); it.add_argument('--action-geometry-top-k', type=int, default=32); it.add_argument('--action-geometry-min-count', type=int, default=1); it.add_argument('--action-geometry-tail-weight', type=float, default=0.25); it.add_argument('--action-geometry-cost-weight', type=float, default=0.05); it.add_argument('--action-geometry-uncertainty-weight', type=float, default=0.10); it.add_argument('--action-geometry-audit-weight', type=float, default=0.20); it.add_argument('--action-geometry-require-carrier-safe', action='store_true'); it.add_argument('--action-geometry-carrier-budget', type=float, default=0.0); it.add_argument('--action-geometry-use-gamma-transition', action='store_true'); it.add_argument('--action-geometry-gamma-aware', action='store_true'); it.add_argument('--action-geometry-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='local'); it.add_argument('--action-geometry-gamma-horizon', type=int, default=4); it.add_argument('--action-geometry-gamma-discount', type=float, default=1.0); it.add_argument('--action-geometry-gamma-tail-value-weight', type=float, default=1.0); it.add_argument('--action-geometry-gamma-stability-margin', type=float, default=0.05); it.add_argument('--action-geometry-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); it.add_argument('--audit-action-geometry-candidates', action='store_true'); it.add_argument('--action-geometry-audit-max-actions', type=int, default=24); it.add_argument('--action-geometry-accept-coker', action='store_true'); it.add_argument('--action-geometry-accept-margin', type=float, default=0.0); it.add_argument('--action-geometry-accept-max-per-task', type=int, default=16); it.add_argument('--action-geometry-accept-cost-weight', type=float, default=0.05); it.add_argument('--action-geometry-accept-carrier-weight', type=float, default=0.7); it.add_argument('--action-geometry-robust-coker-accept', action='store_true'); it.add_argument('--action-geometry-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--action-geometry-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--action-geometry-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--action-geometry-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--action-geometry-robust-coker-require-success', action='store_true'); it.add_argument('--quotient-coordinates', action='store_true'); it.add_argument('--quotient-coordinate-ridge', type=float, default=1e-4); it.add_argument('--quotient-coordinate-max-mass', type=float, default=1.0); it.add_argument('--quotient-coordinate-cosine-threshold', type=float, default=0.85); it.add_argument('--quotient-coordinate-min-states', type=int, default=1); it.add_argument('--quotient-coordinate-top-action-scores', type=int, default=128); it.add_argument('--quotient-coordinate-margin-threshold', type=float, default=0.0); it.add_argument('--quotient-coordinate-validate', action='store_true'); it.add_argument('--quotient-coordinate-registry-candidates', action='store_true'); it.add_argument('--quotient-coordinate-registry-max-candidates', type=int, default=64); it.add_argument('--audit-quotient-coordinate-candidates', action='store_true'); it.add_argument('--quotient-coordinate-audit-max-actions', type=int, default=16); it.add_argument('--quotient-coordinate-accept-coker', action='store_true'); it.add_argument('--quotient-coordinate-robust-coker-accept', action='store_true'); it.add_argument('--quotient-coordinate-accept-margin', type=float, default=0.0); it.add_argument('--quotient-coordinate-accept-max-per-task', type=int, default=16); it.add_argument('--quotient-coordinate-accept-cost-weight', type=float, default=0.05); it.add_argument('--quotient-coordinate-accept-carrier-weight', type=float, default=0.7); it.add_argument('--quotient-coordinate-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--quotient-coordinate-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--quotient-coordinate-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--quotient-coordinate-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--quotient-coordinate-robust-coker-require-success', action='store_true'); it.add_argument('--action-geometry-use-quotient-normals', action='store_true'); it.add_argument('--contextual-congruence', action='store_true'); it.add_argument('--contextual-congruence-context-mode', choices=['state','task','global'], default='state'); it.add_argument('--contextual-congruence-no-carrier', action='store_true'); it.add_argument('--contextual-congruence-min-count', type=int, default=1); it.add_argument('--contextual-congruence-cosine-threshold', type=float, default=0.95); it.add_argument('--contextual-congruence-distance-threshold', type=float, default=0.25); it.add_argument('--contextual-congruence-min-context-jaccard', type=float, default=0.0); it.add_argument('--quotient-coordinate-merge-actions', action='store_true'); it.add_argument('--quotient-coordinate-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); it.add_argument('--qgen', action='store_true'); it.add_argument('--qgen-merge-actions', action='store_true'); it.add_argument('--qgen-merge-policy', choices=['all','robust-only','accepted-only'], default='all'); it.add_argument('--poms-promote', action='store_true'); it.add_argument('--poms-generate-evidence', action='store_true'); it.add_argument('--poms-evidence-min-relative-residual', type=float, default=0.05); it.add_argument('--poms-evidence-min-residual-norm', type=float, default=1e-6); it.add_argument('--poms-evidence-min-support-count', type=int, default=1); it.add_argument('--poms-evidence-min-margin', type=float, default=0.0); it.add_argument('--poms-evidence-min-robust-margin', type=float, default=0.0); it.add_argument('--poms-evidence-least-repair-epsilon', type=float, default=1e-9); it.add_argument('--poms-promotion-evidence', action='append'); it.add_argument('--poms-promote-parent-nonpaid', action='store_true'); it.add_argument('--poms-promote-dual-certificate', action='store_true'); it.add_argument('--poms-promote-least-repair', action='store_true'); it.add_argument('--poms-declare-canonical', action='store_true'); it.add_argument('--qgen-top-defects', type=int, default=16); it.add_argument('--qgen-top-contexts', type=int, default=32); it.add_argument('--qgen-top-carriers', type=int, default=64); it.add_argument('--qgen-top-failures', type=int, default=32); it.add_argument('--qgen-margin-threshold', type=float, default=0.0); it.add_argument('--qgen-cost-weight', type=float, default=0.05); it.add_argument('--qgen-carrier-weight', type=float, default=0.25); it.add_argument('--qgen-audit-penalty', type=float, default=1.0); it.add_argument('--audit-qgen-candidates', action='store_true'); it.add_argument('--qgen-audit-max-actions', type=int, default=24); it.add_argument('--qgen-accept-coker', action='store_true'); it.add_argument('--qgen-accept-margin', type=float, default=0.0); it.add_argument('--qgen-accept-max-per-task', type=int, default=16); it.add_argument('--qgen-accept-cost-weight', type=float, default=0.05); it.add_argument('--qgen-accept-carrier-weight', type=float, default=0.7); it.add_argument('--qgen-robust-accept', action='store_true'); it.add_argument('--qgen-registry-robust-accept', action='store_true'); it.add_argument('--qgen-robust-coker-accept', action='store_true'); it.add_argument('--qgen-registry-robust-coker-accept', action='store_true'); it.add_argument('--qgen-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--qgen-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--qgen-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--qgen-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--qgen-robust-coker-require-success', action='store_true'); it.add_argument('--qgen-robust-z', type=float, default=1.0); it.add_argument('--qgen-robust-min-repeats', type=int, default=1); it.add_argument('--qgen-robust-min-success-rate', type=float, default=1.0); it.add_argument('--qgen-registry-candidates', action='store_true'); it.add_argument('--qgen-registry-max-candidates', type=int, default=64); it.add_argument('--audit-qgen-registry-candidates', action='store_true'); it.add_argument('--qgen-registry-audit-max-actions', type=int, default=16); it.add_argument('--qgen-registry-accept-coker', action='store_true'); it.add_argument('--qgen-registry-accept-margin', type=float, default=0.0); it.add_argument('--qgen-registry-accept-max-per-task', type=int, default=16); it.add_argument('--qgen-registry-accept-cost-weight', type=float, default=0.05); it.add_argument('--qgen-registry-accept-carrier-weight', type=float, default=0.7); 
    add_contextual_probe_args(it)
    add_response_quotient_args(it)
    add_source_budget_pipeline_args(it, include_merge=True)
    it.set_defaults(func=cmd_iterate)
    irp=sub.add_parser('iterate-report'); irp.add_argument('--run-dir', required=True); irp.add_argument('--out-json'); irp.add_argument('--out-csv'); irp.set_defaults(func=cmd_iterate_report)
    loop=sub.add_parser('rgc-loop', conflict_handler='resolve'); loop.add_argument('--tasks', required=True); loop.add_argument('--actions'); loop.add_argument('--out', required=True); loop.add_argument('--rounds', type=int, default=2); loop.add_argument('--dry-run', action='store_true'); loop.add_argument('--jobs', type=int, default=1); loop.add_argument('--max-actions', type=int, default=24); loop.add_argument('--candidate-mode', choices=['basic','state'], default='state'); loop.add_argument('--state-candidates', action='store_true'); loop.add_argument('--quotient-tolerance', type=float, default=0.25); loop.add_argument('--carrier-threshold', type=float, default=0.1); loop.add_argument('--lean-cmd', default='lake env lean'); loop.add_argument('--workdir'); loop.add_argument('--timeout-s', type=float, default=20.0); loop.add_argument('--keep-files', action='store_true'); loop.add_argument('--cache-dir'); loop.add_argument('--trace-state', action='store_true'); loop.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); loop.add_argument('--resume', action='store_true'); loop.add_argument('--flush-every', type=int, default=50); loop.add_argument('--fit-gamma', action='store_true'); loop.add_argument('--gamma-horizon', type=int, default=4); loop.add_argument('--qgen', action='store_true'); loop.add_argument('--qgen-merge-actions', action='store_true'); loop.add_argument('--qgen-top-defects', type=int, default=16); loop.add_argument('--qgen-top-contexts', type=int, default=32); loop.add_argument('--qgen-top-carriers', type=int, default=64); loop.add_argument('--qgen-top-failures', type=int, default=32); loop.add_argument('--qgen-margin-threshold', type=float, default=0.0); loop.add_argument('--mine-min-support', type=int, default=1); loop.add_argument('--mine-min-response-contrast', type=float, default=-1e9); loop.add_argument('--mine-min-stability', type=float, default=0.0); loop.add_argument('--mine-min-intervention-success', type=float, default=0.0); loop.add_argument('--mine-min-coker-reduction', type=float, default=0.0); loop.add_argument('--registry-max-candidates', type=int, default=96); loop.add_argument('--registry-audit-max-actions', type=int, default=24); loop.add_argument('--registry-accept-margin', type=float, default=0.0); loop.add_argument('--registry-accept-max-per-task', type=int, default=16); loop.add_argument('--registry-accept-cost-weight', type=float, default=0.05); loop.add_argument('--registry-accept-carrier-weight', type=float, default=0.7); loop.add_argument('--promote-min-support', type=int, default=1); loop.add_argument('--promote-min-intervention-success', type=float, default=0.1); loop.add_argument('--promote-min-coker-reduction', type=float, default=-1e9); loop.add_argument('--promote-min-promotion-score', type=float, default=-1e9); loop.add_argument('--premise-index', action='store_true'); loop.add_argument('--premise-top-k', type=int, default=8); loop.add_argument('--premise-max-actions', type=int, default=8); loop.add_argument('--audit-premise-candidates', action='store_true'); loop.add_argument('--premise-audit-max-actions', type=int, default=16); loop.add_argument('--merge-premise-actions', action='store_true'); loop.add_argument('--carrier-accept', action='store_true'); loop.add_argument('--carrier-accept-max-actions', type=int, default=8); loop.add_argument('--carrier-accept-margin', type=float, default=0.0); loop.add_argument('--carrier-accept-cost-weight', type=float, default=0.1); loop.add_argument('--promote-carrier-actions', action='store_true'); loop.add_argument('--promote-carrier-min-margin', type=float, default=0.0); loop.add_argument('--next-action-cap', type=int); loop.set_defaults(func=cmd_rgc_loop)

    fp = sub.add_parser('frontier-pipeline', conflict_handler='resolve')
    fp.add_argument('--tasks', required=True)
    fp.add_argument('--out', required=True)
    fp.add_argument('--no-identity', action='store_true')
    fp.add_argument('--max-frontiers-per-task', type=int, default=8)
    fp.add_argument('--max-core-actions', type=int, default=12)
    fp.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto')
    fp.add_argument('--lean-cmd', default='lake env lean')
    fp.add_argument('--workdir')
    fp.add_argument('--dry-run', action='store_true')
    fp.add_argument('--jobs', type=int, default=1)
    fp.add_argument('--max-actions', type=int, default=32)
    fp.add_argument('--quotient-tolerance', type=float, default=0.25)
    fp.add_argument('--carrier-threshold', type=float, default=0.1)
    fp.add_argument('--timeout-s', type=float, default=20.0)
    fp.add_argument('--keep-files', action='store_true')
    fp.add_argument('--cache-dir')
    fp.add_argument('--trace-state', action='store_true')
    fp.add_argument('--resume', action='store_true')
    fp.add_argument('--flush-every', type=int, default=50)
    fp.add_argument('--fit-gamma', action='store_true')
    fp.add_argument('--gamma-horizon', type=int, default=4)
    fp.add_argument('--mine-defects', action='store_true')
    fp.add_argument('--mine-min-support', type=int, default=1)
    fp.add_argument('--mine-min-response-contrast', type=float, default=-1e9)
    fp.add_argument('--mine-min-stability', type=float, default=0.0)
    fp.add_argument('--mine-min-intervention-success', type=float, default=0.0)
    fp.add_argument('--mine-min-coker-reduction', type=float, default=0.0)
    fp.add_argument('--registry-candidates', action='store_true')
    fp.add_argument('--registry-max-candidates', type=int, default=96)
    fp.add_argument('--audit-registry-candidates', action='store_true')
    fp.add_argument('--registry-audit-max-actions', type=int, default=32)
    fp.add_argument('--registry-accept-coker', action='store_true')
    fp.add_argument('--registry-accept-margin', type=float, default=0.0)
    fp.add_argument('--registry-accept-max-per-task', type=int, default=16)
    fp.add_argument('--registry-accept-cost-weight', type=float, default=0.05)
    fp.add_argument('--registry-accept-carrier-weight', type=float, default=0.7)
    fp.add_argument('--promote-registry', action='store_true')
    fp.add_argument('--promote-min-support', type=int, default=1)
    fp.add_argument('--promote-min-intervention-success', type=float, default=0.1)
    fp.add_argument('--promote-min-coker-reduction', type=float, default=-1e9)
    fp.add_argument('--promote-min-promotion-score', type=float, default=-1e9)
    fp.add_argument('--premise-index', action='store_true')
    fp.add_argument('--premise-top-k', type=int, default=8)
    fp.add_argument('--premise-max-actions', type=int, default=8)
    fp.add_argument('--audit-premise-candidates', action='store_true')
    fp.add_argument('--premise-audit-max-actions', type=int, default=24)
    fp.add_argument('--carrier-accept', action='store_true')
    fp.add_argument('--carrier-accept-max-actions', type=int, default=8)
    fp.add_argument('--carrier-accept-margin', type=float, default=0.0)
    fp.add_argument('--carrier-accept-cost-weight', type=float, default=0.1)
    fp.add_argument('--promote-carrier-actions', action='store_true')
    fp.add_argument('--promote-carrier-min-margin', type=float, default=0.0)
    fp.set_defaults(func=cmd_frontier_pipeline)



__all__ = [
    'cmd_compare_runs',
    'cmd_frontier_pipeline',
    'cmd_iterate',
    'cmd_iterate_report',
    'cmd_pipeline',
    'cmd_rgc_loop',
    'cmd_stage_report',
    'add_source_budget_pipeline_args',
    'register_pipeline_commands',
]
