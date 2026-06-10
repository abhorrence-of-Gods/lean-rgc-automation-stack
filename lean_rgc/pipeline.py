from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import LeanTask, ProofState, TacticAction, DefectVector, ResponseRecord, read_jsonl, stable_hash, write_jsonl, write_records
from .executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor
from .candidates import TacticCandidateGenerator, CandidateGeneratorConfig
from .carrier_exposure import StateDependentCandidateGenerator
from .carrier import CarrierGenerator, carrier_coker_proxy
from .carrier_acceptance import accept_carrier_contexts, context_to_actions
from .carrier_promotion import write_accepted_carrier_actions
from .candidate_acceptance import accept_candidates_file, promote_registry_from_acceptance
from .quotient import ResponseQuotientDiscovery
from .response_model import ResponseModelConfig, train_response_model, predict_response_file, ResponseModel
from .trajectory import LeanTrajectoryRunner, TrajectoryRunnerConfig, write_trajectories
from .dataset import summarize_response_rows, split_jsonl, transitions_from_responses, write_run_report
from .batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW, run_micro_audit_batch
from .gamma import GammaAuditor
from .selector import RGCTacticSelector, SelectorConfig
from .goal_shape import parse_goal_shape
from .defect_registry import seed_defect_registry
from .defect_miner import mine_defects as mine_defects_file
from .auto_defects import AutoDefectExtractor
from .proof_ir import ir_rows_from_tasks, ir_rows_from_audits, parse_audits_to_ir
from .focused_analysis import summarize_exposures
from .registry_candidates import registry_candidates_cli
from .iteration import merge_action_files, compare_pipeline_dirs
from .registry_promotion import promote_registry_file
from .registry_acceptance import run_registry_acceptance
from .robust_acceptance import run_robust_acceptance
from .premise_index import build_premise_index, PremiseIndex, premise_actions_from_hits
from .premise_retrieval import build_premise_index_from_tasks, premise_candidates_for_tasks
from .ir_defects import ir_defects_file
from .bulk_executor import BulkAuditConfig, bulk_audit_to_files
from .audit_env_profile import profile_audit_environment
from .ir_candidates import ir_candidates_file
from .multicarrier import build_carrier_matrix_from_responses, annotate_actions_with_carrier_matrix, multi_carrier_report, merge_carrier_incidence_patches, carrier_patch_report
from .frontier import expose_frontier_files
from .exposure_frontier import write_exposure_frontiers
from .action_analysis import write_action_group_report
from .response_eval import evaluate_response_model
from .stage_coker import run_stage_coker
from .quality import quality_gates_for_run, write_quality_report
from .failure_signatures import mine_failure_signatures
from .exposure_audit import exposure_actions_for_tasks, summarize_exposure_audit
from .stage_report import write_stage_report, default_pipeline_stages
from .qgen import qgen_from_files
from .lineage import build_qgen_lineage, build_qgen_acceptance_lineage
from .robust_coker import run_robust_coker_acceptance
from .robust_acceptance import robust_accept_candidates_file
from .realized_response import collect_qgen_realized_calibration
from .carrier_patch_audit import audit_carrier_incidence_patches
from .poms_status import collect_poms_status
from .poms_promotion import collect_poms_promotion
from .promotion_evidence import generate_promotion_evidence
from .action_geometry import build_action_geometry_registry, score_action_geometry_registry, audit_action_cocycles, teacher_constraints_from_arithmetic_actions
from .action_geometry_loop import run_action_geometry_from_qgen
from .structured_state import structured_state_extract_cli, summarize_structured_states
from .audit_db import build_audit_db
from .audit_pruning import prune_actions_file
from .data.store import build_run_db
from .cli_common import _actions_for_tasks, _executor_from_args, _load_actions, _load_actions_grouped, _load_tasks, _normalize_tasks_imports, _server_config_from_args
from .lean_server import LeanServerConfig, audit_with_lean_server
from .lean_worker_supervisor import enqueue_and_run_supervised_audit, run_bulk_audit_queue, run_supervised_audit_queue
from .active_audit_scheduler import active_audit_schedule_from_files, SchedulerConfig, _read_json_or_file
from .quotient_coordinates import quotient_coordinates_from_files
from .carrier_quotient import carrier_quotient_from_files, validate_carrier_quotient_coordinates
from .quotient_coordinate_loop import run_quotient_coordinate_loop, validate_quotient_coordinates
from .contextual_congruence import (
    ContextualProbeConfig,
    generate_contextual_probe_actions, generate_contextual_candidates, generate_contextual_composite_actions,
    build_contextual_response_fingerprints, mine_action_response_congruence,
    contextual_congruence_from_files, contextual_response_congruence_from_files,
    action_classes_to_registry,
)
from .response_quotient import build_response_quotient_registry, project_actions_by_response_quotient, response_quotient_from_congruence_dir
from .premise_response import build_premise_response_registry, retrieve_premise_responses, write_premise_retrieved_actions, mine_premise_quotient, _parse_json_or_file
from .premise_contextual_quotient import (
    generate_premise_contextual_candidates,
    build_premise_contextual_fingerprints,
    mine_premise_contextual_quotient,
    validate_premise_contextual_quotient,
    retrieve_premise_quotient_classes,
    premise_quotient_retrieved_actions,
)
from .bivariate_contextual_quotient import (
    build_premise_use_rows,
    write_separator_contexts,
    generate_bivariate_contextual_candidates,
    schedule_bivariate_candidates,
    build_repair_face_ledger,
)
from .face_taxonomy import build_dual_face_taxonomy
from .obstruction_tower import build_canonical_obstruction_tower
from .dost import (
    write_primitive_observables,
    build_bounded_transcripts,
    build_feature_closure,
    select_features_for_dual_obstructions,
    build_dost_auto_plan,
    compile_experiment_from_auto_plan,
    build_dost_audit_reports,
    run_dost_automation_stack,
)
from .response_completion import build_response_completion
from .crg_registry import SCHEMA_REPAIR_SPECIES_REGISTRY, build_repair_species_registry
from .crg_problem import build_crg_problems
from .nonlinear_generator import generate_nonlinear_repair_candidates
from .crg_hardening import harden_crg_candidates
from .crg_audit import audit_crg_candidates
from .hardening_gap_report import build_hardening_gap_report
from .repair_gradient_flow import repair_gradient_flow_steps
from .concept_geometry import build_concept_geometry
from .concept_search import search_concepts
from .concept_hardening import decode_concepts_to_repair_atoms
from .source_budget_scheduler import source_budget_schedule_from_files, SourceBudgetConfig, _read_json_or_file as _read_source_budget_json_or_file
from .arithmetic_teacher import generate_arithmetic_teacher_graph, audit_arithmetic_teacher_transitions
from .arithmetic_teacher_kernel_audit import audit_arithmetic_teacher_kernel_transitions
from .arithmetic_teacher_cocycle import arithmetic_teacher_cocycle_from_files, build_arithmetic_teacher_transition_geometry, audit_arithmetic_teacher_cocycles, write_arithmetic_teacher_gamma_constraints
from .gamma_transition_learner import learn_gamma_transition_model, merge_gamma_transition_patches_into_action_geometry
from .kernel_context_cache import audit_contextual_candidates_with_kernel_cache



from .cli_experiment import (
    cmd_candidates,
    cmd_registry_candidates,
    cmd_build_premise_index,
    cmd_premise_retrieve,
    cmd_premise_actions,
    cmd_premise_response_registry,
    cmd_premise_response_retrieve,
    cmd_premise_quotient_mine,
    cmd_parse_states,
    cmd_ir_defects,
    cmd_exposure_report,
    cmd_exposure_candidates,
    cmd_action_report,
    cmd_quotient,
    cmd_carrier_generate,
    cmd_carrier_coker,
    cmd_mine_defects,
    cmd_promote_registry,
    cmd_auto_defects,
    cmd_failure_signatures,
    cmd_train_response,
    cmd_eval_response,
    cmd_gamma_audit,
    cmd_make_transitions,
    cmd_carrier_actions,
    cmd_carrier_accept,
    cmd_carrier_accept_summary,
    cmd_accepted_carrier_actions,
    cmd_robust_accept,
    cmd_registry_accept,
    cmd_accept_candidates,
    cmd_ir_candidates,
    cmd_carrier_matrix,
    cmd_carrier_matrix_merge_patches,
    cmd_carrier_safe_actions,
    cmd_multi_carrier_report,
    cmd_robust_coker_accept,
    cmd_expose_frontiers,
    cmd_carrier_patch_audit,
)
@dataclass
class PipelineConfig:
    tasks: str
    actions: str | None
    out: str
    dry_run: bool = True
    jobs: int = 1
    max_actions: int = 32
    quotient_tolerance: float = 0.25
    carrier_threshold: float = 0.1
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    keep_files: bool = False
    cache_dir: str | None = None
    trace_state: bool = False
    import_mode: str = "auto"
    resume: bool = False
    flush_every: int = 50
    fit_gamma: bool = False
    gamma_horizon: int = 4

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_basic_pipeline(cfg: PipelineConfig) -> dict[str, Any]:
    """Run the production pipeline runtime with the historical basic config surface."""
    return run_pipeline(normalize_pipeline_args(cfg), emit_stage=True)



_PIPELINE_DEFAULTS: dict[str, Any] = {
    "actions": None,
    "audit_action_geometry_candidates": False,
    "audit_arithmetic_teacher_candidates": False,
    "audit_arithmetic_teacher_cocycle": False,
    "audit_arithmetic_teacher_kernel_audit": False,
    "audit_carrier_quotient_candidates": False,
    "audit_db": False,
    "audit_db_append": False,
    "audit_db_path": None,
    "audit_exposures": False,
    "audit_failure_signature_candidates": False,
    "audit_ir_candidates": False,
    "audit_lane": None,
    "audit_max_attempts": 1,
    "audit_premise_candidates": False,
    "audit_premise_response_candidates": False,
    "audit_qgen_candidates": False,
    "audit_qgen_registry_candidates": False,
    "audit_queue": False,
    "audit_queue_backend": "bulk",
    "audit_continue_on_timeout": True,
    "audit_auto_profile": False,
    "audit_cache": False,
    "audit_cache_db": None,
    "audit_cache_readonly": False,
    "audit_prune_candidates": False,
    "audit_prune_report": None,
    "audit_quotient_coordinate_candidates": False,
    "audit_registry_candidates": False,
    "audit_scheduler": False,
    "audit_scheduler_budget": None,
    "audit_scheduler_carrier_weight": 0.5,
    "audit_scheduler_coker_weight": 1.0,
    "audit_scheduler_cost_weight": 0.10,
    "audit_scheduler_db": None,
    "audit_scheduler_lineage": None,
    "audit_scheduler_novelty_weight": 0.15,
    "audit_scheduler_per_source_cap": None,
    "audit_scheduler_per_task_cap": None,
    "audit_scheduler_responses": None,
    "audit_scheduler_success_weight": 0.25,
    "audit_scheduler_timeout_weight": 0.50,
    "audit_scheduler_uncertainty_weight": 0.25,
    "audit_source_budget_candidates": False,
    "audit_workers": 1,
    "cache_dir": None,
    "candidate_mode": "state",
    "carrier_accept": False,
    "carrier_accept_cost_weight": 0.1,
    "carrier_accept_margin": 0.0,
    "carrier_accept_max_actions": 8,
    "carrier_matrix": False,
    "carrier_matrix_budget": 0.0,
    "carrier_matrix_keep_unsafe": False,
    "carrier_matrix_merge_qgen": False,
    "carrier_matrix_min_count": 1,
    "carrier_matrix_qgen_audit_patches": False,
    "carrier_matrix_qgen_patch_holdout_fraction": 0.0,
    "carrier_matrix_qgen_patch_min_count": 1,
    "carrier_matrix_qgen_patch_min_mean_delta": 0.0,
    "carrier_matrix_qgen_patch_require_heldout": False,
    "carrier_matrix_qgen_patch_weight": 1.0,
    "carrier_matrix_qgen_require_safe": False,
    "carrier_matrix_shrink": 2.0,
    "carrier_quotient": False,
    "carrier_quotient_accept_carrier_weight": 0.7,
    "carrier_quotient_accept_coker": False,
    "carrier_quotient_accept_cost_weight": 0.05,
    "carrier_quotient_accept_margin": 0.0,
    "carrier_quotient_accept_max_per_task": 16,
    "carrier_quotient_audit_max_actions": 16,
    "carrier_quotient_cosine_threshold": 0.85,
    "carrier_quotient_max_mass": 1.0,
    "carrier_quotient_merge_actions": False,
    "carrier_quotient_merge_policy": "robust-only",
    "carrier_quotient_min_states": 1,
    "carrier_quotient_no_infer_defect_from_violations": False,
    "carrier_quotient_ridge": 1e-4,
    "carrier_quotient_robust_coker_accept": False,
    "carrier_quotient_robust_coker_audit_penalty": 1.0,
    "carrier_quotient_robust_coker_carrier_gain_weight": 0.25,
    "carrier_quotient_robust_coker_holdout_fraction": 0.35,
    "carrier_quotient_robust_coker_require_success": False,
    "carrier_quotient_robust_coker_uncertainty_weight": 0.10,
    "carrier_quotient_top_action_scores": 128,
    "carrier_threshold": 0.1,
    "contextual_congruence": False,
    "contextual_congruence_context_mode": "state",
    "contextual_congruence_cosine_threshold": 0.95,
    "contextual_congruence_distance_threshold": 0.25,
    "contextual_congruence_min_context_jaccard": 0.0,
    "contextual_congruence_min_count": 1,
    "contextual_congruence_no_carrier": False,
    "contextual_probe": False,
    "contextual_probe_accept_coker": False,
    "contextual_probe_audit_max_actions": 24,
    "contextual_probe_context_mode": "state",
    "contextual_probe_cosine_threshold": 0.95,
    "contextual_probe_cost_weight": 0.05,
    "contextual_probe_distance_threshold": 0.25,
    "contextual_probe_max_candidates": None,
    "contextual_probe_max_contexts": None,
    "contextual_probe_min_context_jaccard": 0.0,
    "contextual_probe_min_count": 1,
    "contextual_probe_mode": "weighted",
    "contextual_probe_no_carrier": False,
    "contextual_probe_no_identity": False,
    "contextual_probe_robust_coker_accept": False,
    "contextual_probe_top_k": 32,
    "db_import_artifacts": False,
    "db_materialize_lineage": False,
    "dry_run": False,
    "eval_response_model": False,
    "expose_frontier": False,
    "expose_max_exposures": 8,
    "expose_no_identity": False,
    "exposure_audit_max_actions": 8,
    "failure_signature_accept_carrier_weight": 0.7,
    "failure_signature_accept_coker": False,
    "failure_signature_accept_cost_weight": 0.05,
    "failure_signature_accept_margin": 0.0,
    "failure_signature_accept_max_per_task": 16,
    "failure_signature_audit_max_actions": 16,
    "failure_signature_min_support": 1,
    "failure_signatures": False,
    "fit_gamma": False,
    "flush_every": 50,
    "frontier_include_identity": False,
    "frontier_max_prefixes": 8,
    "frontier_normalize": False,
    "gamma_horizon": 4,
    "gamma_transition_holdout_fraction": 0.25,
    "gamma_transition_include_matrices": False,
    "gamma_transition_learner": False,
    "gamma_transition_min_count": 2,
    "gamma_transition_patch_action_geometry": False,
    "gamma_transition_ridge": 1e-3,
    "gamma_transition_shrink": 4.0,
    "gamma_transition_teacher_weight": 0.25,
    "import_mode": "auto",
    "ir_accept_carrier_weight": 0.7,
    "ir_accept_coker": False,
    "ir_accept_cost_weight": 0.05,
    "ir_accept_margin": 0.0,
    "ir_accept_max_per_task": 16,
    "ir_audit_max_actions": 24,
    "ir_candidates": False,
    "ir_max_candidates": 64,
    "jobs": 1,
    "keep_files": False,
    "lean_cmd": "lake env lean",
    "max_actions": 32,
    "mine_defects": False,
    "mine_min_coker_reduction": -1e9,
    "mine_min_intervention_success": 0.0,
    "mine_min_response_contrast": -1e9,
    "mine_min_stability": 0.0,
    "mine_min_support": 1,
    "native_exec_mode": "source_check",
    "poms_declare_canonical": False,
    "poms_evidence_least_repair_epsilon": 1e-9,
    "poms_evidence_min_margin": 0.0,
    "poms_evidence_min_relative_residual": 0.05,
    "poms_evidence_min_residual_norm": 1e-6,
    "poms_evidence_min_robust_margin": 0.0,
    "poms_evidence_min_support_count": 1,
    "poms_generate_evidence": False,
    "poms_promote": False,
    "poms_promote_dual_certificate": False,
    "poms_promote_least_repair": False,
    "poms_promote_parent_nonpaid": False,
    "poms_promotion_evidence": None,
    "premise_audit_max_actions": 24,
    "premise_contextual": False,
    "premise_contextual_audit": False,
    "premise_contextual_audit_max_actions": 24,
    "premise_contextual_baseline_required": False,
    "premise_contextual_cosine_threshold": 0.95,
    "premise_contextual_distance_threshold": 0.25,
    "premise_contextual_epsilon": 0.25,
    "premise_contextual_face_taxonomy": False,
    "premise_contextual_holdout_fraction": 0.35,
    "premise_contextual_include_context_actions": False,
    "premise_contextual_max_candidates": None,
    "premise_contextual_max_left": 4,
    "premise_contextual_max_premises": None,
    "premise_contextual_max_right": 4,
    "premise_contextual_min_contexts": 1,
    "premise_contextual_no_baselines": False,
    "premise_contextual_no_carrier": False,
    "premise_contextual_no_gamma": False,
    "premise_contextual_no_identity": False,
    "premise_contextual_obstruction_tower": False,
    "premise_contextual_response_weight": 1.0,
    "premise_contextual_retrieval": False,
    "premise_contextual_retrieval_top_k": 16,
    "premise_contextual_schedule": False,
    "premise_contextual_schedule_budget": None,
    "premise_contextual_schedule_response_weight": 1.0,
    "premise_index": False,
    "premise_max_actions": 8,
    "premise_quotient_audit_max_actions": 16,
    "premise_quotient_mine": False,
    "premise_response_audit_max_actions": 16,
    "premise_response_registry": False,
    "premise_response_retrieve": False,
    "premise_response_top_k": 32,
    "premise_top_k": 8,
    "promote_carrier_actions": False,
    "promote_carrier_min_margin": 0.0,
    "promote_drop_rejected": False,
    "promote_min_coker_reduction": -1e9,
    "promote_min_intervention_success": 0.1,
    "promote_min_promotion_score": -1e9,
    "promote_min_support": 1,
    "promote_registry": False,
    "qgen": False,
    "qgen_accept_carrier_weight": 0.7,
    "qgen_accept_coker": False,
    "qgen_accept_cost_weight": 0.05,
    "qgen_accept_margin": 0.0,
    "qgen_accept_max_per_task": 16,
    "qgen_audit_max_actions": 24,
    "qgen_audit_penalty": 1.0,
    "qgen_carrier_weight": 0.25,
    "qgen_cost_weight": 0.05,
    "qgen_margin_threshold": 0.0,
    "qgen_max_mass": 1.0,
    "qgen_merge_actions": False,
    "qgen_merge_policy": "all",
    "qgen_registry_accept_carrier_weight": 0.7,
    "qgen_registry_accept_coker": False,
    "qgen_registry_accept_cost_weight": 0.05,
    "qgen_registry_accept_margin": 0.0,
    "qgen_registry_accept_max_per_task": 16,
    "qgen_registry_audit_max_actions": 16,
    "qgen_registry_candidates": False,
    "qgen_registry_max_candidates": 64,
    "qgen_registry_robust_accept": False,
    "qgen_registry_robust_coker_accept": False,
    "qgen_ridge": 1e-4,
    "qgen_robust_accept": False,
    "qgen_robust_coker_accept": False,
    "qgen_robust_coker_audit_penalty": 1.0,
    "qgen_robust_coker_carrier_gain_weight": 0.25,
    "qgen_robust_coker_holdout_fraction": 0.35,
    "qgen_robust_coker_require_success": False,
    "qgen_robust_coker_uncertainty_weight": 0.10,
    "qgen_robust_min_repeats": 1,
    "qgen_robust_min_success_rate": 1.0,
    "qgen_robust_z": 1.0,
    "qgen_top_carriers": 64,
    "qgen_top_contexts": 32,
    "qgen_top_defects": 16,
    "qgen_top_failures": 32,
    "quotient_coordinate_accept_carrier_weight": 0.7,
    "quotient_coordinate_accept_coker": False,
    "quotient_coordinate_accept_cost_weight": 0.05,
    "quotient_coordinate_accept_margin": 0.0,
    "quotient_coordinate_accept_max_per_task": 16,
    "quotient_coordinate_audit_max_actions": 16,
    "quotient_coordinate_cosine_threshold": 0.85,
    "quotient_coordinate_max_mass": 1.0,
    "quotient_coordinate_merge_actions": False,
    "quotient_coordinate_merge_policy": "robust-only",
    "quotient_coordinate_min_states": 1,
    "quotient_coordinate_registry_candidates": False,
    "quotient_coordinate_registry_max_candidates": 64,
    "quotient_coordinate_ridge": 1e-4,
    "quotient_coordinate_robust_coker_accept": False,
    "quotient_coordinate_robust_coker_audit_penalty": 1.0,
    "quotient_coordinate_robust_coker_carrier_gain_weight": 0.25,
    "quotient_coordinate_robust_coker_holdout_fraction": 0.35,
    "quotient_coordinate_robust_coker_require_success": False,
    "quotient_coordinate_robust_coker_uncertainty_weight": 0.10,
    "quotient_coordinate_top_action_scores": 128,
    "quotient_coordinate_validate": False,
    "quotient_tolerance": 0.25,
    "registry_accept_carrier_weight": 0.7,
    "registry_accept_coker": False,
    "registry_accept_cost_weight": 0.05,
    "registry_accept_margin": 0.0,
    "registry_accept_max_per_task": 16,
    "registry_audit_max_actions": 32,
    "registry_candidates": False,
    "registry_max_candidates": 96,
    "response_eval_mode": "mean",
    "response_quotient": False,
    "response_quotient_min_members": 1,
    "response_quotient_min_quality": None,
    "response_quotient_project_actions": False,
    "resume": False,
    "run_db": False,
    "run_db_append": False,
    "run_db_path": None,
    "server_backend": "auto",
    "server_cmd": None,
    "server_no_fallback": False,
    "source_budget": False,
    "source_budget_budget": None,
    "stage_coker": False,
    "stage_coker_carrier_weight": 0.25,
    "stage_coker_cost_weight": 0.05,
    "stage_coker_margin": 0.0,
    "stage_coker_max_actions": None,
    "state_candidates": False,
    "timeout_s": 20.0,
    "trace_state": False,
    "workdir": None,
}


def make_pipeline_run_id(out_dir: str | Path) -> str:
    out = Path(out_dir)
    return "run_" + stable_hash({"out_dir": str(out.resolve())}, 20)


def normalize_pipeline_args(args) -> argparse.Namespace:
    if isinstance(args, argparse.Namespace):
        data = vars(args).copy()
    elif isinstance(args, PipelineConfig):
        data = args.to_dict()
    elif isinstance(args, dict):
        data = dict(args)
    else:
        data = dict(vars(args))
    merged = dict(_PIPELINE_DEFAULTS)
    merged.update(data)
    return argparse.Namespace(**merged)


def _action_task_id(row: dict[str, Any]) -> str | None:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    task_id = row.get("task_id") or meta.get("task_id")
    return str(task_id) if task_id else None

def _is_contextual_baseline_row(row: dict[str, Any]) -> bool:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return bool(meta.get("is_contextual_baseline")) or str(meta.get("source") or "").startswith("premise_contextual_baseline")

def _clone_action_for_task(row: dict[str, Any], task_id: str, *, role: str = "task_budget") -> dict[str, Any]:
    out = dict(row)
    meta = dict(out.get("metadata") if isinstance(out.get("metadata"), dict) else {})
    source_action_id = str(out.get("action_id") or stable_hash(out, 12))
    task_suffix = stable_hash({"action_id": source_action_id, "task_id": task_id, "role": role}, 10)
    out["action_id"] = f"{source_action_id}__task_{task_suffix}"
    out["task_id"] = task_id
    out["metadata"] = {
        **meta,
        "task_id": task_id,
        "source_action_id": source_action_id,
        "task_budget_materialized": True,
        "task_budget_role": role,
    }
    return out

def _materialize_total_budget_task_actions(
    actions_path: str | Path,
    tasks: list[LeanTask],
    out_path: str | Path,
    *,
    budget: int | None,
    require_baseline_pairs: bool = False,
) -> dict[str, Any]:
    """Convert a global scheduled action budget into a total audit-job budget.

    `_pipeline_audit` treats global actions as a per-task pool.  For scheduled
    contextual candidates, users usually mean "audit at most N total probes",
    not "audit N probes on every task".  This helper assigns global rows to
    concrete tasks, preserving baseline/probe context pairs on the same task.
    """
    rows = [r for r in read_jsonl(actions_path) if isinstance(r, dict)]
    task_ids = [t.task_id for t in tasks]
    cap = max(0, int(budget or len(rows)))
    if not rows or not task_ids or cap <= 0:
        write_jsonl(out_path, [])
        summary = {
            "schema_version": "lean-rgc-task-budget-materialized-actions-v64.1",
            "source": str(actions_path),
            "out": str(out_path),
            "budget": cap,
            "n_source_actions": len(rows),
            "n_tasks": len(task_ids),
            "n_actions": 0,
            "n_baselines": 0,
            "n_probes": 0,
            "canonical_status": "task_budget_materialization_chart_not_canonical",
        }
        return summary

    baselines_by_id = {str(r.get("action_id")): r for r in rows if _is_contextual_baseline_row(r)}
    probes = [r for r in rows if not _is_contextual_baseline_row(r)]
    emitted: list[dict[str, Any]] = []
    emitted_baseline_for_task: dict[tuple[str, str], str] = {}
    task_index = 0

    def choose_task(row: dict[str, Any]) -> str:
        nonlocal task_index
        explicit = _action_task_id(row)
        if explicit:
            return explicit
        task_id = task_ids[task_index % len(task_ids)]
        task_index += 1
        return task_id

    for probe in probes:
        if len(emitted) >= cap:
            break
        meta = probe.get("metadata") if isinstance(probe.get("metadata"), dict) else {}
        task_id = choose_task(probe)
        baseline_id = str(meta.get("baseline_action_id") or "")
        cloned_baseline_id = ""
        if baseline_id and baseline_id in baselines_by_id:
            key = (task_id, baseline_id)
            if key not in emitted_baseline_for_task:
                if len(emitted) + (2 if require_baseline_pairs else 1) > cap:
                    break
                base = _clone_action_for_task(baselines_by_id[baseline_id], task_id, role="baseline")
                emitted_baseline_for_task[key] = str(base.get("action_id"))
                emitted.append(base)
            cloned_baseline_id = emitted_baseline_for_task[key]
        elif require_baseline_pairs:
            continue
        if len(emitted) >= cap:
            break
        cloned_probe = _clone_action_for_task(probe, task_id, role="probe")
        cloned_meta = dict(cloned_probe.get("metadata") if isinstance(cloned_probe.get("metadata"), dict) else {})
        if cloned_baseline_id:
            cloned_meta["baseline_action_id"] = cloned_baseline_id
        cloned_probe["metadata"] = cloned_meta
        emitted.append(cloned_probe)

    if not probes:
        for i, row in enumerate(rows[:cap]):
            emitted.append(_clone_action_for_task(row, task_ids[i % len(task_ids)], role="scheduled"))

    write_jsonl(out_path, emitted)
    n_baselines = sum(1 for r in emitted if _is_contextual_baseline_row(r))
    summary = {
        "schema_version": "lean-rgc-task-budget-materialized-actions-v64.1",
        "source": str(actions_path),
        "out": str(out_path),
        "budget": cap,
        "n_source_actions": len(rows),
        "n_tasks": len(task_ids),
        "n_actions": len(emitted),
        "n_baselines": n_baselines,
        "n_probes": len(emitted) - n_baselines,
        "n_distinct_task_ids": len({str(r.get("task_id")) for r in emitted if r.get("task_id")}),
        "require_baseline_pairs": bool(require_baseline_pairs),
        "canonical_status": "task_budget_materialization_chart_not_canonical",
    }
    return summary

def _summarize_pipeline_responses(responses: list[dict[str, Any]]) -> dict[str, Any]:
    if not responses:
        return {"n": 0}
    statuses: dict[str, int] = {}
    norms: list[float] = []
    carrier_deltas: list[float] = []
    goal_responses: list[float] = []
    for row in responses:
        status = str(row.get("audit_status", row.get("status", "unknown")))
        statuses[status] = statuses.get(status, 0) + 1
        norms.append(float(np.linalg.norm(np.asarray(row.get("response_flat", []), dtype=float))))
        carrier_delta = row.get("carrier_delta", {}) or {}
        carrier_deltas.append(sum(float(v) for v in carrier_delta.values()))
        response = row.get("response", {}) or {}
        goal_responses.append(sum(float(v) for k, v in response.items() if str(k).startswith("goal.")))
    return {
        "n": len(responses),
        "statuses": statuses,
        "success_rate": statuses.get("success", 0) / max(1, len(responses)),
        "mean_response_norm": float(np.mean(norms)),
        "max_response_norm": float(np.max(norms)),
        "mean_goal_response": float(np.mean(goal_responses)),
        "mean_carrier_delta": float(np.mean(carrier_deltas)),
    }


def _run_pipeline_batch_audit(args) -> int:
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    cfg = LeanExecutorConfig(
        lean_cmd=args.lean_cmd,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
        keep_files=args.keep_files,
        workdir=args.workdir,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
    )
    summary = run_micro_audit_batch(
        tasks,
        acts,
        out_dir=args.out,
        executor_config=cfg,
        max_actions=args.max_actions,
        jobs=getattr(args, "jobs", 1),
        resume=args.resume,
        flush_every=args.flush_every,
        run_id=getattr(args, "run_id", None),
    )
    responses_path = Path(args.out) / "responses.jsonl"
    responses = read_jsonl(responses_path) if responses_path.exists() else []
    summary.update(_summarize_pipeline_responses(responses))
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _run_pipeline_bulk_audit(args) -> int:
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    trimmed = {k: v[: args.max_actions] for k, v in acts.items()}
    cfg = BulkAuditConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        batch_size=args.batch_size,
        keep_files=args.keep_files,
        trace_state=args.trace_state,
    )
    rep = bulk_audit_to_files(tasks, trimmed, args.out, cfg, run_id=getattr(args, "run_id", None))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def _run_pipeline_server_audit(args) -> int:
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(
        tasks,
        base,
        by_task,
        state_candidates=args.state_candidates or not (base or by_task),
        candidate_mode=args.candidate_mode,
        max_candidates=args.max_actions,
    )
    summary = audit_with_lean_server(
        tasks,
        acts,
        out_dir=args.out,
        server_config=_server_config_from_args(args),
        max_actions=args.max_actions,
        resume=args.resume,
        flush_every=args.flush_every,
        run_id=getattr(args, "run_id", None),
    )
    responses_path = Path(args.out) / "responses.jsonl"
    responses = read_jsonl(responses_path) if responses_path.exists() else []
    summary.update(_summarize_pipeline_responses(responses))
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def run_pipeline(args, *, emit_stage: bool = True) -> dict[str, Any]:
    args = normalize_pipeline_args(args)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True); audit_dir=out/'audit'
    pipeline_run_id = make_pipeline_run_id(out)
    def _stage(name: str, **fields: Any) -> None:
        payload = {"pipeline_stage": name, **fields}
        if emit_stage:
            print(json.dumps(payload, ensure_ascii=False), flush=True)

    def _pipeline_audit(tasks_path, actions_path, out_dir, max_actions, *, state_candidates=False, candidate_mode=None):
        scheduled_actions_path = actions_path
        if getattr(args, 'audit_scheduler', False) and actions_path:
            sched_dir = Path(out_dir) / 'audit_scheduler'
            sched_dir.mkdir(parents=True, exist_ok=True)
            scheduled_actions_path = sched_dir / 'scheduled_actions.jsonl'
            active_audit_schedule_from_files(
                candidates_path=actions_path,
                out_actions=scheduled_actions_path,
                out_rows=sched_dir / 'audit_schedule_rows.jsonl',
                out_report=sched_dir / 'audit_schedule_report.json',
                db_path=getattr(args, 'audit_scheduler_db', None),
                response_paths=[getattr(args, 'audit_scheduler_responses')] if getattr(args, 'audit_scheduler_responses', None) else None,
                response_normal=None,
                carrier_normal=None,
                config=SchedulerConfig(
                    top_k=getattr(args, 'audit_scheduler_budget', None) or max_actions,
                    per_task_cap=getattr(args, 'audit_scheduler_per_task_cap', None),
                    response_weight=getattr(args, 'audit_scheduler_coker_weight', 1.0),
                    carrier_weight=getattr(args, 'audit_scheduler_carrier_weight', 0.5),
                    uncertainty_weight=getattr(args, 'audit_scheduler_uncertainty_weight', 0.25),
                    novelty_weight=getattr(args, 'audit_scheduler_novelty_weight', 0.15),
                    success_weight=getattr(args, 'audit_scheduler_success_weight', 0.25),
                    cost_weight=getattr(args, 'audit_scheduler_cost_weight', 0.10),
                    timeout_weight=getattr(args, 'audit_scheduler_timeout_weight', 0.50),
                ),
            )
            # Legacy compatibility path used by early v36 experiments.
            legacy_sched_dir = Path(args.out) / 'audit_schedules'
            legacy_sched_dir.mkdir(parents=True, exist_ok=True)
            try:
                import shutil
                shutil.copyfile(scheduled_actions_path, legacy_sched_dir / 'audit_scheduled_actions.jsonl')
                shutil.copyfile(sched_dir / 'audit_schedule_report.json', legacy_sched_dir / 'audit_schedule_report.json')
            except Exception:
                pass
        if getattr(args, 'audit_prune_candidates', False) and scheduled_actions_path:
            prune_dir = Path(out_dir) / 'audit_prune'
            prune_dir.mkdir(parents=True, exist_ok=True)
            pruned_actions_path = prune_dir / 'pruned_actions.jsonl'
            prune_report_path = Path(getattr(args, 'audit_prune_report', None) or (Path(out_dir) / 'audit_prune_report.json'))
            try:
                n_prune_tasks = len(_load_tasks(tasks_path))
            except Exception:
                n_prune_tasks = None
            prune_report = prune_actions_file(
                scheduled_actions_path,
                pruned_actions_path,
                report_out=prune_report_path,
                n_tasks=n_prune_tasks,
            )
            scheduled_actions_path = pruned_actions_path
            _stage("audit_prune_done", out=str(out_dir), **{k: prune_report.get(k) for k in ("n_input", "n_output", "n_pruned", "estimated_jobs_saved")})
        ns = argparse.Namespace(tasks=str(tasks_path), actions=str(scheduled_actions_path) if scheduled_actions_path else None, out=str(out_dir), jobs=args.jobs, max_actions=max_actions, state_candidates=state_candidates, candidate_mode=candidate_mode or args.candidate_mode, lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, cache_dir=args.cache_dir or str(out/'cache'), trace_state=args.trace_state, import_mode=args.import_mode, resume=args.resume, flush_every=args.flush_every, batch_size=getattr(args, 'bulk_batch_size', 64), server_cmd=getattr(args, 'server_cmd', None), server_backend=getattr(args, 'server_backend', 'auto'), server_no_fallback=getattr(args, 'server_no_fallback', False), native_exec_mode=getattr(args, 'native_exec_mode', 'source_check'), run_id=pipeline_run_id)
        if getattr(args, 'audit_queue', False):
            tasks = _normalize_tasks_imports(_load_tasks(tasks_path), args.import_mode, args.workdir, args.lean_cmd)
            base, by_task = _load_actions_grouped(str(scheduled_actions_path) if scheduled_actions_path else None)
            acts = _actions_for_tasks(tasks, base, by_task, state_candidates=state_candidates or not (base or by_task), candidate_mode=candidate_mode or args.candidate_mode, max_candidates=max_actions)
            estimated_jobs = sum(len(v) for v in acts.values()) if isinstance(acts, dict) else len(tasks) * len(acts)
            _stage("audit_queue_start", out=str(out_dir), tasks=len(tasks), global_actions=len(base), task_action_tasks=len(by_task), estimated_jobs=estimated_jobs, max_actions=max_actions)
            lane = getattr(args, 'audit_lane', None) or getattr(args, 'native_exec_mode', 'source_check')
            if lane not in {'source_check', 'kernel_rpc', 'heavy'}:
                lane = 'source_check'
            db_path = getattr(args, 'audit_db_path', None) or str(Path(out_dir) / 'audit_queue.sqlite')
            run_id = pipeline_run_id
            audit_profile = None
            effective_workers = int(getattr(args, 'audit_workers', 1) or 1)
            effective_timeout_s = float(getattr(args, 'audit_job_timeout_s', None) or args.timeout_s)
            requested_queue_backend = getattr(args, 'audit_queue_backend', 'bulk') or 'bulk'
            queue_backend = requested_queue_backend
            if args.keep_files or args.dry_run or lane == 'kernel_rpc':
                queue_backend = 'file'
            backend = f"{lane}_{queue_backend}"
            bulk_batch_size = int(getattr(args, 'audit_bulk_batch_size', None) or 32)
            if queue_backend == 'bulk':
                effective_timeout_s = max(effective_timeout_s, 60.0)
            if getattr(args, 'audit_auto_profile', False) and not args.dry_run:
                profile_path = Path(out_dir) / 'audit_env_profile.json'
                if profile_path.exists() and getattr(args, 'resume', False):
                    try:
                        audit_profile = json.loads(profile_path.read_text(encoding='utf-8'))
                    except Exception:
                        audit_profile = None
                if audit_profile is None:
                    audit_profile = profile_audit_environment(
                        tasks=tasks,
                        actions_by_task=acts,
                        lean_cmd=args.lean_cmd,
                        workdir=args.workdir,
                        timeout_s=max(60.0, float(args.timeout_s or 20.0), float(getattr(args, 'audit_job_timeout_s', None) or 0.0)),
                        out_json=profile_path,
                        keep_files_dir=Path(out_dir) / 'audit_env_profile_files',
                    )
                effective_timeout_s = max(effective_timeout_s, float(audit_profile.get('recommended_timeout_s') or 30.0))
                if queue_backend == 'bulk':
                    import_wall = float(audit_profile.get('import_wall_s') or 0.0)
                    effective_timeout_s = max(effective_timeout_s, float(max(60.0, import_wall * 2.0 + 3.0 * bulk_batch_size)))
                recommended_workers = int(audit_profile.get('recommended_workers') or effective_workers)
                effective_workers = max(1, min(effective_workers, recommended_workers))
            audit_cache_db = None
            if getattr(args, 'audit_cache', False):
                audit_cache_db = str(Path(getattr(args, 'audit_cache_db', None) or (Path.cwd() / '.lean_rgc' / 'audit_cache.sqlite')))
            cfg = LeanExecutorConfig(
                lean_cmd=args.lean_cmd,
                timeout_s=effective_timeout_s,
                dry_run=args.dry_run,
                keep_files=args.keep_files,
                workdir=args.workdir,
                cache_dir=args.cache_dir or str(out / 'cache'),
                trace_state=args.trace_state,
            )
            summary = enqueue_and_run_supervised_audit(
                db_path=db_path,
                tasks=tasks,
                actions_by_task=acts,
                out_dir=out_dir,
                executor_config=cfg,
                run_id=run_id,
                backend=str(backend),
                import_mode=args.import_mode,
                max_actions=max_actions,
                max_attempts=getattr(args, 'audit_max_attempts', 1),
                workers=effective_workers,
                job_timeout_s=effective_timeout_s,
                continue_on_timeout=getattr(args, 'audit_continue_on_timeout', True),
                lane=lane,
                queue_backend=queue_backend,
                bulk_batch_size=bulk_batch_size,
                import_wall_s=float(audit_profile.get('import_wall_s')) if isinstance(audit_profile, dict) and audit_profile.get('import_wall_s') is not None else None,
                audit_cache_db=audit_cache_db,
                audit_cache_readonly=getattr(args, 'audit_cache_readonly', False),
            )
            summary['audit_queue_backend'] = queue_backend
            if requested_queue_backend != queue_backend:
                summary['audit_queue_backend_requested'] = requested_queue_backend
            summary['audit_workers_effective'] = effective_workers
            summary['audit_job_timeout_s_effective'] = effective_timeout_s
            if audit_profile:
                summary['audit_env_profile'] = audit_profile
                summary['audit_env_profile_path'] = str(Path(out_dir) / 'audit_env_profile.json')
            if audit_cache_db:
                summary['audit_cache_db'] = audit_cache_db
                summary['audit_cache_readonly'] = bool(getattr(args, 'audit_cache_readonly', False))
            (Path(out_dir) / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')
            (Path(out_dir) / 'server_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding='utf-8')
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 0
        if getattr(args, 'audit_mode', 'batch') == 'server':
            return _run_pipeline_server_audit(ns)
        if getattr(args, 'audit_mode', 'batch') == 'bulk' and not args.dry_run:
            return _run_pipeline_bulk_audit(ns)
        return _run_pipeline_batch_audit(ns)
    frontier_tasks_path = None
    if getattr(args, 'expose_frontier', False):
        frontier_tasks_path = out / 'frontier_tasks.jsonl'
        write_jsonl(out / '_pipeline_input_tasks.jsonl', [t.to_dict() for t in _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)])
        write_exposure_frontiers(out / '_pipeline_input_tasks.jsonl', frontier_tasks_path, out / 'exposure_frontier_report.jsonl', _executor_from_args(args), max_exposures=getattr(args, 'expose_max_exposures', 8), allow_identity=not getattr(args, 'expose_no_identity', False))
        args = argparse.Namespace(**{**vars(args), 'tasks': str(frontier_tasks_path)})
    tasks_for_pipeline = args.tasks
    frontier_summary = None
    if getattr(args, 'frontier_normalize', False):
        frontier_dir = out/'frontier'
        cmd_expose_frontiers(argparse.Namespace(tasks=args.tasks,out=str(frontier_dir),max_prefixes=args.frontier_max_prefixes,include_identity=args.frontier_include_identity,accept_status=['partial','dry_run'],lean_cmd=args.lean_cmd,workdir=args.workdir,timeout_s=args.timeout_s,dry_run=args.dry_run,keep_files=args.keep_files,cache_dir=args.cache_dir or str(out/'cache'),trace_state=args.trace_state,import_mode=args.import_mode,resume=args.resume))
        ft = frontier_dir/'frontier_tasks.jsonl'
        if ft.exists() and read_jsonl(ft):
            tasks_for_pipeline = str(ft)
            frontier_summary = json.loads((frontier_dir/'frontier_summary.json').read_text(encoding='utf-8')) if (frontier_dir/'frontier_summary.json').exists() else {'frontier_tasks': str(ft)}
    _pipeline_audit(tasks_for_pipeline, args.actions, audit_dir, args.max_actions, state_candidates=args.state_candidates or args.candidate_mode=='state', candidate_mode=args.candidate_mode)
    if getattr(args, 'audit_exposures', False):
        exp_actions = out/'exposure_actions.jsonl'
        cmd_exposure_candidates(argparse.Namespace(tasks=tasks_for_pipeline, out=str(exp_actions), include_identity=False, import_mode=args.import_mode))
        exp_dir = out/'exposure_audit'
        _pipeline_audit(tasks_for_pipeline, str(exp_actions), exp_dir, args.exposure_audit_max_actions, state_candidates=False, candidate_mode='state')
        summarize_exposure_audit(exp_dir, out/'exposure_audit_report.json')
    cmd_action_report(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(out/'action_report.json'), csv_out=str(out/'action_report.csv'), group_keys=None))
    # v41: arithmetic teacher graph.  This treats arithmetic identities as
    # goal-state transformation charts g -> tau_I(g), not as data curriculum.
    arithmetic_teacher_dir = None
    arithmetic_teacher_actions_path = None
    arithmetic_teacher_audit_dir = None
    arithmetic_teacher_audit_report_path = None
    if getattr(args, 'arithmetic_teacher_graph', False):
        arithmetic_teacher_dir = out / 'arithmetic_teacher'
        arithmetic_teacher_dir.mkdir(parents=True, exist_ok=True)
        _arith_ss_arg = getattr(args, 'arithmetic_teacher_structured_states', None)
        structured_states_path = Path(_arith_ss_arg) if _arith_ss_arg else Path('__missing_arithmetic_teacher_structured_states__')
        if not structured_states_path.exists():
            # Prefer server-audit structured states if present; otherwise build a
            # stable structured-state chart from tasks and micro-audit logs.
            candidate_ss = audit_dir / 'structured_states.jsonl'
            if candidate_ss.exists():
                structured_states_path = candidate_ss
            else:
                structured_states_path = out / 'structured_states.jsonl'
                try:
                    structured_state_extract_cli(tasks=tasks_for_pipeline, audits=str(audit_dir/'micro_audit.jsonl'), out=str(structured_states_path), summary_out=str(out/'structured_state_summary.json'))
                except Exception:
                    # Last-resort tasks-only chart.
                    structured_state_extract_cli(tasks=tasks_for_pipeline, out=str(structured_states_path), summary_out=str(out/'structured_state_summary.json'))
        generate_arithmetic_teacher_graph(
            structured_states_path,
            arithmetic_teacher_dir,
            identities_path=getattr(args, 'arithmetic_teacher_identities', None),
            actions_path=args.actions,
            responses_path=audit_dir/'responses.jsonl',
            max_transforms_per_state=getattr(args, 'arithmetic_teacher_max_transforms_per_state', 32),
            emit_candidate_actions=not getattr(args, 'arithmetic_teacher_no_actions', False),
        )
        transformations = arithmetic_teacher_dir / 'arithmetic_teacher_transformations.jsonl'
        if transformations.exists():
            arithmetic_teacher_audit_report_path = arithmetic_teacher_dir / 'arithmetic_teacher_audit_report.json'
            audit_arithmetic_teacher_transitions(transformations, structured_states_path, arithmetic_teacher_dir / 'arithmetic_teacher_audit_rows.jsonl', report_out=arithmetic_teacher_audit_report_path)
            if getattr(args, 'arithmetic_teacher_kernel_audit', False):
                kernel_dir = arithmetic_teacher_dir / 'kernel_transition_audit'
                audit_arithmetic_teacher_kernel_transitions(
                    transformations,
                    tasks_for_pipeline,
                    kernel_dir,
                    identities_path=getattr(args, 'arithmetic_teacher_identities', None),
                    structured_states_path=structured_states_path,
                    server_config=_server_config_from_args(args),
                    max_transitions=getattr(args, 'arithmetic_teacher_kernel_audit_max_transitions', 32),
                )
                if getattr(args, 'arithmetic_teacher_cocycle_audit', False):
                    cocycle_dir = arithmetic_teacher_dir / 'cocycle_audit'
                    arithmetic_teacher_cocycle_from_files(
                        kernel_dir / 'arithmetic_teacher_kernel_audit_rows.jsonl',
                        cocycle_dir,
                        compositions_path=getattr(args, 'arithmetic_teacher_cocycle_compositions', None),
                        min_count=getattr(args, 'arithmetic_teacher_cocycle_min_count', 1),
                        accept_threshold=getattr(args, 'arithmetic_teacher_cocycle_accept_threshold', 1.0),
                        min_verified_rate=getattr(args, 'arithmetic_teacher_cocycle_min_verified_rate', 0.0),
                        max_tail_radius=getattr(args, 'arithmetic_teacher_cocycle_max_tail_radius', None),
                        max_auto_pairs=getattr(args, 'arithmetic_teacher_cocycle_max_auto_pairs', 0),
                    )
        arithmetic_teacher_actions_path = arithmetic_teacher_dir / 'arithmetic_teacher_actions.jsonl'
        if getattr(args, 'audit_arithmetic_teacher_candidates', False) and arithmetic_teacher_actions_path.exists():
            arithmetic_teacher_audit_dir = out / 'arithmetic_teacher_audit'
            _pipeline_audit(tasks_for_pipeline, str(arithmetic_teacher_actions_path), arithmetic_teacher_audit_dir, getattr(args, 'arithmetic_teacher_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(arithmetic_teacher_audit_dir/'responses.jsonl'), out=str(out/'arithmetic_teacher_action_report.json'), csv_out=str(out/'arithmetic_teacher_action_report.csv'), group_keys=None))
    # v32: finite contextual probe generation.  This creates A∘C∘B-style
    # action probes, audits them, and optionally mines contextual response
    # congruence from their responses.  These probes are charts/witnesses for
    # operation-stable congruence; they are not canonical contexts.
    contextual_probe_dir = None
    contextual_probe_candidates_path = None
    contextual_probe_audit_dir = None
    contextual_probe_accepted_actions_path = None
    contextual_probe_robust_accepted_actions_path = None
    contextual_probe_congruence_dir = None
    contextual_probe_report_path = None
    if getattr(args, 'contextual_probes', False):
        contextual_probe_dir = out / 'contextual_probes'
        contextual_probe_dir.mkdir(parents=True, exist_ok=True)
        contextual_probe_candidates_path = contextual_probe_dir / 'contextual_probe_candidates.jsonl'
        if not args.actions:
            (contextual_probe_dir / 'contextual_probe_report.json').write_text(json.dumps({
                'schema_version': 'lean-rgc-contextual-probe-loop-v32.0',
                'status': 'skipped_no_actions',
                'canonical_status': 'contextual_probe_chart_only_not_canonical',
            }, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            _, cp_summary = generate_contextual_candidates(
                args.actions,
                contextual_probe_candidates_path,
                contexts_path=getattr(args, 'contextual_probe_contexts', None),
                max_left=getattr(args, 'contextual_probe_max_left', 4),
                max_right=getattr(args, 'contextual_probe_max_right', 4),
                max_core=getattr(args, 'contextual_probe_max_core', None),
                max_candidates=getattr(args, 'contextual_probe_max_candidates', None),
                include_identity=not getattr(args, 'contextual_probe_no_identity', False),
                include_left=not getattr(args, 'contextual_probe_no_left', False),
                include_right=not getattr(args, 'contextual_probe_no_right', False),
            )
            cp_summary.update({
                'schema_version': 'lean-rgc-contextual-probe-loop-v32.0',
                'canonical_status': 'contextual_probe_action_chart_only_not_canonical',
            })
            contextual_probe_report_path = contextual_probe_dir / 'contextual_probe_report.json'
            contextual_probe_report_path.write_text(json.dumps(cp_summary, indent=2, ensure_ascii=False), encoding='utf-8')
            if getattr(args, 'audit_contextual_probe_candidates', False) and contextual_probe_candidates_path.exists():
                contextual_probe_audit_dir = out / 'contextual_probe_audit'
                _pipeline_audit(tasks_for_pipeline, str(contextual_probe_candidates_path), contextual_probe_audit_dir, getattr(args, 'contextual_probe_audit_max_actions', 24), state_candidates=False, candidate_mode='state')
                cmd_action_report(argparse.Namespace(responses=str(contextual_probe_audit_dir/'responses.jsonl'), out=str(out/'contextual_probe_action_report.json'), csv_out=str(out/'contextual_probe_action_report.csv'), group_keys=None))
                if getattr(args, 'contextual_probe_congruence', False):
                    contextual_probe_congruence_dir = contextual_probe_dir / 'contextual_probe_congruence'
                    contextual_response_congruence_from_files(
                        contextual_probe_audit_dir/'responses.jsonl',
                        contextual_probe_congruence_dir,
                        context_mode=getattr(args, 'contextual_probe_congruence_context_mode', getattr(args, 'contextual_congruence_context_mode', 'state')),
                        include_carrier=not getattr(args, 'contextual_probe_congruence_no_carrier', False),
                        min_count=getattr(args, 'contextual_probe_congruence_min_count', getattr(args, 'contextual_congruence_min_count', 1)),
                        cosine_threshold=getattr(args, 'contextual_probe_congruence_cosine_threshold', getattr(args, 'contextual_congruence_cosine_threshold', 0.95)),
                        distance_threshold=getattr(args, 'contextual_probe_congruence_distance_threshold', getattr(args, 'contextual_congruence_distance_threshold', 0.25)),
                        min_context_jaccard=getattr(args, 'contextual_probe_congruence_min_context_jaccard', getattr(args, 'contextual_congruence_min_context_jaccard', 0.0)),
                    )
                if getattr(args, 'contextual_probe_accept_coker', False):
                    if getattr(args, 'contextual_probe_robust_coker_accept', False):
                        contextual_probe_robust_accepted_actions_path = out / 'contextual_probe_robust_accepted_actions.jsonl'
                        cmd_robust_coker_accept(argparse.Namespace(
                            base_responses=str(audit_dir/'responses.jsonl'),
                            candidate_responses=str(contextual_probe_audit_dir/'responses.jsonl'),
                            out_report=str(out/'contextual_probe_robust_acceptance_report.json'),
                            out_actions=str(contextual_probe_robust_accepted_actions_path),
                            out_rows=str(out/'contextual_probe_robust_acceptance_rows.jsonl'),
                            csv_out=str(out/'contextual_probe_robust_acceptance_rows.csv'),
                            margin_threshold=getattr(args, 'contextual_probe_accept_margin', 0.0),
                            holdout_fraction=getattr(args, 'contextual_probe_robust_coker_holdout_fraction', 0.35),
                            ridge=1e-4,
                            max_mass=1.0,
                            cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
                            carrier_gain_weight=getattr(args, 'contextual_probe_robust_coker_carrier_gain_weight', 0.25),
                            carrier_violation_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7),
                            audit_penalty=getattr(args, 'contextual_probe_robust_coker_audit_penalty', 1.0),
                            uncertainty_weight=getattr(args, 'contextual_probe_robust_coker_uncertainty_weight', 0.10),
                            require_success=getattr(args, 'contextual_probe_robust_coker_require_success', False),
                            max_actions=getattr(args, 'contextual_probe_accept_max_per_task', 16),
                        ))
                        contextual_probe_accepted_actions_path = out / 'contextual_probe_accepted_actions.jsonl'
                        if contextual_probe_robust_accepted_actions_path.exists():
                            contextual_probe_accepted_actions_path.write_text(contextual_probe_robust_accepted_actions_path.read_text(encoding='utf-8'), encoding='utf-8')
                    else:
                        contextual_probe_accepted_actions_path = out / 'contextual_probe_accepted_actions.jsonl'
                        cmd_registry_accept(argparse.Namespace(
                            base_responses=str(audit_dir/'responses.jsonl'),
                            registry_responses=str(contextual_probe_audit_dir/'responses.jsonl'),
                            accepted_actions_out=str(contextual_probe_accepted_actions_path),
                            report_out=str(out/'contextual_probe_acceptance_report.json'),
                            audit_out=str(out/'contextual_probe_acceptance_rows.jsonl'),
                            margin_threshold=getattr(args, 'contextual_probe_accept_margin', 0.0),
                            max_per_task=getattr(args, 'contextual_probe_accept_max_per_task', 16),
                            goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                            carrier_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7), audit_weight=0.2,
                            success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                            cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
                        ))
    contextual_congruence_dir = None
    contextual_congruence_report_path = None
    contextual_congruence_classes_path = None
    contextual_congruence_representatives_path = None
    if getattr(args, 'contextual_congruence', False):
        contextual_congruence_dir = out / 'contextual_congruence'
        contextual_response_congruence_from_files(
            audit_dir/'responses.jsonl',
            contextual_congruence_dir,
            context_mode=getattr(args, 'contextual_congruence_context_mode', 'state'),
            include_carrier=not getattr(args, 'contextual_congruence_no_carrier', False),
            min_count=getattr(args, 'contextual_congruence_min_count', 1),
            cosine_threshold=getattr(args, 'contextual_congruence_cosine_threshold', 0.95),
            distance_threshold=getattr(args, 'contextual_congruence_distance_threshold', 0.25),
            min_context_jaccard=getattr(args, 'contextual_congruence_min_context_jaccard', 0.0),
        )
        contextual_congruence_report_path = contextual_congruence_dir / 'contextual_response_congruence_report.json'
        contextual_congruence_classes_path = contextual_congruence_dir / 'response_congruence_classes.jsonl'
        contextual_congruence_representatives_path = contextual_congruence_dir / 'response_congruence_representatives.jsonl'
    # v33: finite response-quotient registry.  This projects contextual
    # response-congruence classes into an action->class->representative map.
    # It is still a finite chart of operation-stable congruence, not canonical.
    response_quotient_dir = None
    response_quotient_registry_path = None
    response_quotient_representatives_path = None
    response_quotient_projected_actions_path = None
    if getattr(args, 'response_quotient_registry', False):
        source_cong_dir = None
        if contextual_probe_congruence_dir and (contextual_probe_congruence_dir / 'response_congruence_classes.jsonl').exists():
            source_cong_dir = contextual_probe_congruence_dir
        elif contextual_congruence_dir and (contextual_congruence_dir / 'response_congruence_classes.jsonl').exists():
            source_cong_dir = contextual_congruence_dir
        if source_cong_dir:
            response_quotient_dir = out / 'response_quotient'
            response_quotient_registry = response_quotient_from_congruence_dir(
                source_cong_dir,
                actions_path=args.actions,
                out_dir=response_quotient_dir,
                min_members=getattr(args, 'response_quotient_min_members', 1),
                min_quality=getattr(args, 'response_quotient_min_quality', None),
            )
            response_quotient_registry_path = response_quotient_dir / 'response_quotient_registry.json'
            response_quotient_representatives_path = response_quotient_dir / 'response_quotient_representatives.jsonl'
            if getattr(args, 'response_quotient_project_actions', False) and args.actions:
                response_quotient_projected_actions_path = out / 'response_quotient_projected_actions.jsonl'
                project_actions_by_response_quotient(
                    args.actions,
                    response_quotient_registry_path,
                    response_quotient_projected_actions_path,
                    annotate_only=getattr(args, 'response_quotient_annotate_only', False),
                )
    quotient_coordinate_dir = None
    quotient_coordinate_candidates_path = None
    quotient_coordinate_registry_path = None
    quotient_coordinate_registry_candidates_path = None
    quotient_coordinate_audit_dir = None
    quotient_coordinate_accepted_actions_path = None
    quotient_coordinate_robust_accepted_actions_path = None
    quotient_coordinate_normal_path = None
    quotient_coordinate_validation_report_path = None
    quotient_coordinate_validation_report_path = None
    quotient_coordinate_response_normal_path = None
    qgen_dir = None
    qgen_context_candidates_path = None
    qgen_accepted_actions_path = None
    qgen_defect_registry_path = None
    qgen_carrier_incidence_path = None
    qgen_failure_signatures_path = None
    qgen_lineage_path = None
    qgen_registry_candidates_path = None
    qgen_registry_audit_dir = None
    qgen_registry_accepted_path = None
    if getattr(args, 'qgen', False):
        qgen_dir = out / 'qgen'
        qgen_from_files(
            audit_dir/'responses.jsonl',
            audits=audit_dir/'micro_audit.jsonl',
            out_dir=qgen_dir,
            ridge=args.qgen_ridge,
            max_mass=args.qgen_max_mass,
            top_defects=args.qgen_top_defects,
            top_contexts=args.qgen_top_contexts,
            top_carriers=args.qgen_top_carriers,
            top_failures=args.qgen_top_failures,
            margin_threshold=args.qgen_margin_threshold,
            cost_weight=args.qgen_cost_weight,
            carrier_weight=args.qgen_carrier_weight,
            audit_penalty=args.qgen_audit_penalty,
        )
        qgen_context_candidates_path = qgen_dir / 'qgen_context_candidates.jsonl'
        qgen_accepted_actions_path = qgen_dir / 'qgen_accepted_actions.jsonl'
        qgen_defect_registry_path = qgen_dir / 'qgen_defect_registry.json'
        qgen_carrier_incidence_path = qgen_dir / 'qgen_carrier_incidence.jsonl'
        qgen_failure_signatures_path = qgen_dir / 'qgen_failure_signatures.jsonl'
        qgen_lineage_path = qgen_dir / 'qgen_lineage.json'
        build_qgen_lineage(qgen_dir, out=qgen_lineage_path)
        if getattr(args, 'qgen_registry_candidates', False) and qgen_defect_registry_path.exists():
            qgen_registry_candidates_path = out / 'qgen_registry_candidates.jsonl'
            cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline, registry=str(qgen_defect_registry_path), out=str(qgen_registry_candidates_path), max_candidates=args.qgen_registry_max_candidates))
    # v34: carrier-quotient mining.  This mines carrier coker residuals
    # into finite carrier-coordinate candidates q_phi^C(c)=<phi,c>.
    carrier_quotient_dir = None
    carrier_quotient_candidates_path = None
    carrier_quotient_registry_path = None
    carrier_quotient_patch_path = None
    carrier_quotient_audit_dir = None
    carrier_quotient_accepted_actions_path = None
    carrier_quotient_robust_accepted_actions_path = None
    if getattr(args, 'carrier_quotient', False):
        carrier_quotient_dir = out / 'carrier_quotient'
        carrier_quotient_from_files(
            audit_dir/'responses.jsonl',
            out_dir=carrier_quotient_dir,
            ridge=getattr(args, 'carrier_quotient_ridge', 1e-4),
            max_mass=getattr(args, 'carrier_quotient_max_mass', 1.0),
            cosine_threshold=getattr(args, 'carrier_quotient_cosine_threshold', 0.85),
            min_states=getattr(args, 'carrier_quotient_min_states', 1),
            top_action_scores=getattr(args, 'carrier_quotient_top_action_scores', 128),
            margin_threshold=getattr(args, 'carrier_quotient_margin_threshold', 0.0),
            validate=getattr(args, 'carrier_quotient_validate', False),
            infer_defect_from_violations=not getattr(args, 'carrier_quotient_no_infer_defect_from_violations', False),
        )
        carrier_quotient_candidates_path = carrier_quotient_dir / 'carrier_quotient_candidates.jsonl'
        carrier_quotient_registry_path = carrier_quotient_dir / 'carrier_quotient_defect_registry.json'
        carrier_quotient_patch_path = carrier_quotient_dir / 'carrier_quotient_incidence_patches.jsonl'
        if getattr(args, 'audit_carrier_quotient_candidates', False) and carrier_quotient_candidates_path.exists():
            carrier_quotient_audit_dir = out / 'carrier_quotient_audit'
            _pipeline_audit(tasks_for_pipeline, str(carrier_quotient_candidates_path), carrier_quotient_audit_dir, getattr(args, 'carrier_quotient_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(carrier_quotient_audit_dir/'responses.jsonl'), out=str(out/'carrier_quotient_action_report.json'), csv_out=str(out/'carrier_quotient_action_report.csv'), group_keys=None))
            if getattr(args, 'carrier_quotient_accept_coker', False):
                if getattr(args, 'carrier_quotient_robust_coker_accept', False):
                    carrier_quotient_robust_accepted_actions_path = out / 'carrier_quotient_robust_accepted_actions.jsonl'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(carrier_quotient_audit_dir/'responses.jsonl'),
                        out_report=str(out/'carrier_quotient_robust_acceptance_report.json'),
                        out_actions=str(carrier_quotient_robust_accepted_actions_path),
                        out_rows=str(out/'carrier_quotient_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'carrier_quotient_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'carrier_quotient_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'carrier_quotient_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'carrier_quotient_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'carrier_quotient_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'carrier_quotient_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'carrier_quotient_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'carrier_quotient_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'carrier_quotient_robust_coker_require_success', False),
                        max_actions=getattr(args, 'carrier_quotient_accept_max_per_task', 16),
                    ))
                else:
                    carrier_quotient_accepted_actions_path = out / 'carrier_quotient_accepted_actions.jsonl'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(carrier_quotient_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(carrier_quotient_accepted_actions_path),
                        report_out=str(out/'carrier_quotient_acceptance_report.json'),
                        audit_out=str(out/'carrier_quotient_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'carrier_quotient_accept_margin', 0.0),
                        max_per_task=getattr(args, 'carrier_quotient_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'carrier_quotient_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'carrier_quotient_accept_cost_weight', 0.05),
                    ))

    # v26: quotient-coordinate generation.  This mines coker normals into
    # finite linear quotient-coordinate candidates q_phi(d)=<phi,d>.  The
    # outputs remain charts/witnesses until validated, audited and promoted.
    quotient_coordinate_dir = None
    quotient_coordinate_candidates_path = None
    quotient_coordinate_registry_path = None
    quotient_coordinate_registry_candidates_path = None
    quotient_coordinate_audit_dir = None
    quotient_coordinate_accepted_actions_path = None
    quotient_coordinate_robust_accepted_actions_path = None
    if getattr(args, 'quotient_coordinates', False):
        quotient_coordinate_dir = out / 'quotient_coordinates'
        run_quotient_coordinate_loop(
            responses=audit_dir/'responses.jsonl',
            out_dir=quotient_coordinate_dir,
            ridge=getattr(args, 'quotient_coordinate_ridge', 1e-4),
            max_mass=getattr(args, 'quotient_coordinate_max_mass', 1.0),
            cosine_threshold=getattr(args, 'quotient_coordinate_cosine_threshold', 0.85),
            min_states=getattr(args, 'quotient_coordinate_min_states', 1),
            top_action_scores=getattr(args, 'quotient_coordinate_top_action_scores', 128),
            margin_threshold=getattr(args, 'quotient_coordinate_margin_threshold', 0.0),
            validate=getattr(args, 'quotient_coordinate_validate', False),
        )
        quotient_coordinate_candidates_path = quotient_coordinate_dir / 'quotient_coordinate_selected_actions.jsonl'
        quotient_coordinate_registry_path = quotient_coordinate_dir / 'quotient_coordinate_defect_registry.json'
        quotient_coordinate_normal_path = quotient_coordinate_dir / 'quotient_coordinate_response_normal.json'
        quotient_coordinate_response_normal_path = quotient_coordinate_normal_path
        quotient_coordinate_validation_report_path = quotient_coordinate_dir / 'quotient_coordinate_validation_report.json'
        if getattr(args, 'quotient_coordinate_registry_candidates', False) and quotient_coordinate_registry_path.exists():
            quotient_coordinate_registry_candidates_path = out / 'quotient_coordinate_registry_candidates.jsonl'
            cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline, registry=str(quotient_coordinate_registry_path), out=str(quotient_coordinate_registry_candidates_path), max_candidates=getattr(args, 'quotient_coordinate_registry_max_candidates', 64)))
        if getattr(args, 'audit_quotient_coordinate_candidates', False) and quotient_coordinate_candidates_path.exists():
            quotient_coordinate_audit_dir = out / 'quotient_coordinate_audit'
            _pipeline_audit(tasks_for_pipeline, str(quotient_coordinate_candidates_path), quotient_coordinate_audit_dir, getattr(args, 'quotient_coordinate_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(quotient_coordinate_audit_dir/'responses.jsonl'), out=str(out/'quotient_coordinate_action_report.json'), csv_out=str(out/'quotient_coordinate_action_report.csv'), group_keys=None))
            if getattr(args, 'quotient_coordinate_accept_coker', False):
                if getattr(args, 'quotient_coordinate_robust_coker_accept', False):
                    quotient_coordinate_robust_accepted_actions_path = out / 'quotient_coordinate_robust_accepted_actions.jsonl'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(quotient_coordinate_audit_dir/'responses.jsonl'),
                        out_report=str(out/'quotient_coordinate_robust_acceptance_report.json'),
                        out_actions=str(quotient_coordinate_robust_accepted_actions_path),
                        out_rows=str(out/'quotient_coordinate_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'quotient_coordinate_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'quotient_coordinate_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'quotient_coordinate_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'quotient_coordinate_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'quotient_coordinate_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'quotient_coordinate_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'quotient_coordinate_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'quotient_coordinate_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'quotient_coordinate_robust_coker_require_success', False),
                        max_actions=getattr(args, 'quotient_coordinate_accept_max_per_task', 16),
                    ))
                else:
                    quotient_coordinate_accepted_actions_path = out / 'quotient_coordinate_accepted_actions.jsonl'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(quotient_coordinate_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(quotient_coordinate_accepted_actions_path),
                        report_out=str(out/'quotient_coordinate_acceptance_report.json'),
                        audit_out=str(out/'quotient_coordinate_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'quotient_coordinate_accept_margin', 0.0),
                        max_per_task=getattr(args, 'quotient_coordinate_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'quotient_coordinate_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'quotient_coordinate_accept_cost_weight', 0.05),
                    ))
    # v23: action-geometry retrieval loop.  This is a finite chart-level
    # action manifold search driven by qgen/coker normals; retrieved actions
    # remain witnesses until micro-audited and accepted.
    action_geometry_dir = None
    action_geometry_registry_path = None
    action_geometry_candidates_path = None
    action_geometry_audit_dir = None
    action_geometry_accepted_actions_path = None
    action_geometry_acceptance_report_path = None
    action_geometry_robust_accepted_actions_path = None
    action_geometry_robust_acceptance_report_path = None
    if getattr(args, 'action_geometry', False):
        action_geometry_dir = out / 'action_geometry'
        ag_transitions_path = out / 'transitions.jsonl'
        try:
            cmd_make_transitions(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(ag_transitions_path)))
        except Exception:
            ag_transitions_path = None
        qrep = qgen_dir / 'qgen_report.json' if qgen_dir and (qgen_dir / 'qgen_report.json').exists() else None
        if getattr(args, 'action_geometry_use_quotient_normals', False) and quotient_coordinate_normal_path and Path(quotient_coordinate_normal_path).exists():
            qrep = quotient_coordinate_normal_path
        action_geometry_gamma_transition_patches_for_retrieval = None
        if getattr(args, 'action_geometry_use_gamma_transition', False) and ag_transitions_path and Path(ag_transitions_path).exists():
            ag_gamma_dir = action_geometry_dir / 'gamma_transition_for_retrieval'
            ag_teacher_constraints = None
            if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl').exists():
                ag_teacher_constraints = arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl'
            try:
                learn_gamma_transition_model(
                    ag_transitions_path,
                    ag_gamma_dir,
                    actions_path=args.actions,
                    teacher_constraints_path=ag_teacher_constraints,
                    ridge=getattr(args, 'gamma_transition_ridge', 1e-3),
                    shrink=getattr(args, 'gamma_transition_shrink', 4.0),
                    min_count=getattr(args, 'gamma_transition_min_count', 2),
                    holdout_fraction=getattr(args, 'gamma_transition_holdout_fraction', 0.25),
                    teacher_weight=getattr(args, 'gamma_transition_teacher_weight', 0.25),
                    include_matrices=getattr(args, 'gamma_transition_include_matrices', False),
                )
                action_geometry_gamma_transition_patches_for_retrieval = ag_gamma_dir / 'gamma_transition_action_geometry_patches.jsonl'
            except Exception:
                action_geometry_gamma_transition_patches_for_retrieval = None
        run_action_geometry_from_qgen(
            responses=audit_dir/'responses.jsonl',
            actions=args.actions,
            qgen_report=qrep if (getattr(args, 'action_geometry_use_qgen_normals', False) or getattr(args, 'action_geometry_use_quotient_normals', False)) else None,
            out_dir=action_geometry_dir,
            quotient_coordinates=(quotient_coordinate_dir / 'quotient_coordinates.jsonl') if (getattr(args, 'action_geometry_use_quotient_normals', False) and quotient_coordinate_dir and (quotient_coordinate_dir / 'quotient_coordinates.jsonl').exists()) else None,
            transitions=ag_transitions_path if ag_transitions_path and Path(ag_transitions_path).exists() else None,
            top_k=getattr(args, 'action_geometry_top_k', None),
            tail_weight=getattr(args, 'action_geometry_tail_weight', 0.25),
            cost_weight=getattr(args, 'action_geometry_cost_weight', 0.05),
            uncertainty_weight=getattr(args, 'action_geometry_uncertainty_weight', 0.10),
            audit_weight=getattr(args, 'action_geometry_audit_weight', 0.20),
            require_carrier_safe=getattr(args, 'action_geometry_require_carrier_safe', False),
            carrier_budget=getattr(args, 'action_geometry_carrier_budget', 0.0),
            min_count=getattr(args, 'action_geometry_min_count', 1),
            gamma_transition_patches=locals().get('action_geometry_gamma_transition_patches_for_retrieval'),
            gamma_aware=bool(getattr(args, 'action_geometry_use_gamma_transition', False) or str(getattr(args, 'action_geometry_gamma_value_mode', 'local')).lower() not in {'local', 'none', 'off'}),
            gamma_mode=getattr(args, 'action_geometry_gamma_value_mode', 'finite_horizon'),
            gamma_horizon=getattr(args, 'action_geometry_gamma_horizon', 4),
            gamma_discount=getattr(args, 'action_geometry_gamma_discount', 1.0),
            gamma_value_weight=getattr(args, 'action_geometry_gamma_tail_value_weight', 1.0),
            gamma_stability_delta=getattr(args, 'action_geometry_gamma_stability_margin', 0.05),
            gamma_tail_risk_mode=getattr(args, 'action_geometry_gamma_tail_risk_mode', 'spectral'),
        )
        action_geometry_registry_path = action_geometry_dir / 'action_geometry.jsonl'
        action_geometry_candidates_path = action_geometry_dir / 'action_geometry_candidates.jsonl'
        if getattr(args, 'audit_action_geometry_candidates', False) and action_geometry_candidates_path.exists():
            action_geometry_audit_dir = out / 'action_geometry_audit'
            _pipeline_audit(tasks_for_pipeline, str(action_geometry_candidates_path), action_geometry_audit_dir, getattr(args, 'action_geometry_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(action_geometry_audit_dir/'responses.jsonl'), out=str(out/'action_geometry_action_report.json'), csv_out=str(out/'action_geometry_action_report.csv'), group_keys=None))
            if getattr(args, 'action_geometry_accept_coker', False):
                if getattr(args, 'action_geometry_robust_coker_accept', False):
                    action_geometry_robust_accepted_actions_path = out / 'action_geometry_robust_accepted_actions.jsonl'
                    action_geometry_robust_acceptance_report_path = out / 'action_geometry_robust_acceptance_report.json'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(action_geometry_audit_dir/'responses.jsonl'),
                        out_report=str(action_geometry_robust_acceptance_report_path),
                        out_actions=str(action_geometry_robust_accepted_actions_path),
                        out_rows=str(out/'action_geometry_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'action_geometry_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'action_geometry_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'action_geometry_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'action_geometry_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'action_geometry_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'action_geometry_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'action_geometry_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'action_geometry_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'action_geometry_robust_coker_require_success', False),
                        max_actions=getattr(args, 'action_geometry_accept_max_per_task', 16),
                    ))
                else:
                    action_geometry_accepted_actions_path = out / 'action_geometry_accepted_actions.jsonl'
                    action_geometry_acceptance_report_path = out / 'action_geometry_acceptance_report.json'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(action_geometry_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(action_geometry_accepted_actions_path),
                        report_out=str(action_geometry_acceptance_report_path),
                        audit_out=str(out/'action_geometry_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'action_geometry_accept_margin', 0.0),
                        max_per_task=getattr(args, 'action_geometry_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'action_geometry_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'action_geometry_accept_cost_weight', 0.05),
                    ))

    qgen_audit_dir = None
    qgen_audited_accepted_actions_path = None
    qgen_acceptance_report_path = None
    qgen_robust_accepted_actions_path = None
    qgen_robust_acceptance_report_path = None
    qgen_robust_acceptance_rows_path = None
    if getattr(args, 'qgen', False) and getattr(args, 'audit_qgen_candidates', False) and qgen_context_candidates_path and qgen_context_candidates_path.exists():
        qgen_audit_dir = out / 'qgen_audit'
        _pipeline_audit(tasks_for_pipeline, str(qgen_context_candidates_path), qgen_audit_dir, args.qgen_audit_max_actions, state_candidates=False, candidate_mode='state')
        cmd_action_report(argparse.Namespace(responses=str(qgen_audit_dir/'responses.jsonl'), out=str(out/'qgen_action_report.json'), csv_out=str(out/'qgen_action_report.csv'), group_keys=None))
        if getattr(args, 'qgen_accept_coker', False):
            qgen_audited_accepted_actions_path = out / 'qgen_accepted_actions.jsonl'
            qgen_acceptance_report_path = out / 'qgen_acceptance_report.json'
            if getattr(args, 'qgen_robust_coker_accept', False):
                qgen_robust_accepted_actions_path = out / 'qgen_robust_accepted_actions.jsonl'
                qgen_robust_acceptance_report_path = out / 'qgen_robust_acceptance_report.json'
                qgen_robust_acceptance_rows_path = out / 'qgen_robust_acceptance_rows.jsonl'
                cmd_robust_coker_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_audit_dir/'responses.jsonl'),
                    out_report=str(qgen_robust_acceptance_report_path),
                    out_actions=str(qgen_robust_accepted_actions_path),
                    out_rows=str(qgen_robust_acceptance_rows_path),
                    csv_out=str(out/'qgen_robust_acceptance_rows.csv'),
                    margin_threshold=args.qgen_accept_margin,
                    holdout_fraction=args.qgen_robust_coker_holdout_fraction,
                    ridge=1e-4,
                    max_mass=1.0,
                    cost_weight=args.qgen_accept_cost_weight,
                    carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
                    carrier_violation_weight=args.qgen_accept_carrier_weight,
                    audit_penalty=args.qgen_robust_coker_audit_penalty,
                    uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
                    require_success=args.qgen_robust_coker_require_success,
                    max_actions=args.qgen_accept_max_per_task,
                ))
                # Keep the legacy accepted-actions path populated for downstream tools while
                # preserving the robust-specific artifact name for provenance.
                if qgen_robust_accepted_actions_path.exists():
                    qgen_audited_accepted_actions_path.write_text(qgen_robust_accepted_actions_path.read_text(encoding='utf-8'), encoding='utf-8')
                if qgen_robust_acceptance_report_path.exists():
                    qgen_acceptance_report_path.write_text(qgen_robust_acceptance_report_path.read_text(encoding='utf-8'), encoding='utf-8')
            elif getattr(args, 'qgen_robust_accept', False):
                cmd_robust_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_audit_dir/'responses.jsonl'),
                    out=str(out/'qgen_robust_acceptance_rows.jsonl'),
                    report_out=str(qgen_acceptance_report_path),
                    accepted_actions_out=str(qgen_audited_accepted_actions_path),
                    per_row_out=str(out/'qgen_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_accept_margin,
                    max_per_task=args.qgen_accept_max_per_task,
                    goal_weight=1.0,
                    carrier_weight=args.qgen_accept_carrier_weight,
                    cost_weight=args.qgen_accept_cost_weight,
                    max_mass=1.0,
                    ridge=1e-4,
                    robust_z=args.qgen_robust_z,
                    robust_min_repeats=args.qgen_robust_min_repeats,
                    robust_min_success_rate=args.qgen_robust_min_success_rate,
                ))
            else:
                cmd_registry_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    registry_responses=str(qgen_audit_dir/'responses.jsonl'),
                    accepted_actions_out=str(qgen_audited_accepted_actions_path),
                    report_out=str(qgen_acceptance_report_path),
                    audit_out=str(out/'qgen_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_accept_margin,
                    max_per_task=args.qgen_accept_max_per_task,
                    goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                    carrier_weight=args.qgen_accept_carrier_weight, audit_weight=0.2,
                    success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                    cost_weight=args.qgen_accept_cost_weight,
                ))
    if getattr(args, 'qgen', False) and getattr(args, 'audit_qgen_registry_candidates', False) and qgen_registry_candidates_path and qgen_registry_candidates_path.exists():
        qgen_registry_audit_dir = out / 'qgen_registry_audit'
        _pipeline_audit(tasks_for_pipeline, str(qgen_registry_candidates_path), qgen_registry_audit_dir, args.qgen_registry_audit_max_actions, state_candidates=False, candidate_mode='state')
        cmd_action_report(argparse.Namespace(responses=str(qgen_registry_audit_dir/'responses.jsonl'), out=str(out/'qgen_registry_action_report.json'), csv_out=str(out/'qgen_registry_action_report.csv'), group_keys=None))
        if getattr(args, 'qgen_registry_accept_coker', False):
            qgen_registry_accepted_path = out / 'qgen_registry_accepted_actions.jsonl'
            if getattr(args, 'qgen_registry_robust_coker_accept', False):
                qgen_registry_robust_accepted_path = out / 'qgen_registry_robust_accepted_actions.jsonl'
                cmd_robust_coker_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    out_report=str(out/'qgen_registry_robust_acceptance_report.json'),
                    out_actions=str(qgen_registry_robust_accepted_path),
                    out_rows=str(out/'qgen_registry_robust_acceptance_rows.jsonl'),
                    csv_out=str(out/'qgen_registry_robust_acceptance_rows.csv'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    holdout_fraction=args.qgen_robust_coker_holdout_fraction,
                    ridge=1e-4,
                    max_mass=1.0,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                    carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
                    carrier_violation_weight=args.qgen_registry_accept_carrier_weight,
                    audit_penalty=args.qgen_robust_coker_audit_penalty,
                    uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
                    require_success=args.qgen_robust_coker_require_success,
                    max_actions=args.qgen_registry_accept_max_per_task,
                ))
                if qgen_registry_robust_accepted_path.exists():
                    qgen_registry_accepted_path.write_text(qgen_registry_robust_accepted_path.read_text(encoding='utf-8'), encoding='utf-8')
            elif getattr(args, 'qgen_registry_robust_accept', False):
                cmd_robust_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    out=str(out/'qgen_registry_robust_acceptance_rows.jsonl'),
                    report_out=str(out/'qgen_registry_acceptance_report.json'),
                    accepted_actions_out=str(qgen_registry_accepted_path),
                    per_row_out=str(out/'qgen_registry_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    max_per_task=args.qgen_registry_accept_max_per_task,
                    goal_weight=1.0,
                    carrier_weight=args.qgen_registry_accept_carrier_weight,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                    max_mass=1.0,
                    ridge=1e-4,
                    robust_z=args.qgen_robust_z,
                    robust_min_repeats=args.qgen_robust_min_repeats,
                    robust_min_success_rate=args.qgen_robust_min_success_rate,
                ))
            else:
                cmd_registry_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    registry_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    accepted_actions_out=str(qgen_registry_accepted_path),
                    report_out=str(out/'qgen_registry_acceptance_report.json'),
                    audit_out=str(out/'qgen_registry_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    max_per_task=args.qgen_registry_accept_max_per_task,
                    goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                    carrier_weight=args.qgen_registry_accept_carrier_weight, audit_weight=0.2,
                    success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                ))
    failure_signatures_path=None; failure_signature_actions_path=None; failure_signature_audit_dir=None
    if getattr(args, 'failure_signatures', False):
        failure_signatures_path = out/'failure_signatures.jsonl'
        failure_signature_actions_path = out/'failure_signature_actions.jsonl'
        cmd_failure_signatures(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'), responses=str(audit_dir/'responses.jsonl'), out=str(failure_signatures_path), actions_out=str(failure_signature_actions_path), summary_out=str(out/'failure_signatures.summary.json'), min_support=args.failure_signature_min_support))
        if getattr(args, 'audit_failure_signature_candidates', False):
            failure_signature_audit_dir = out/'failure_signature_audit'
            _pipeline_audit(tasks_for_pipeline, str(failure_signature_actions_path), failure_signature_audit_dir, args.failure_signature_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(failure_signature_audit_dir/'responses.jsonl'), out=str(out/'failure_signature_action_report.json'), csv_out=str(out/'failure_signature_action_report.csv'), group_keys=None))
            if getattr(args, 'failure_signature_accept_coker', False):
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(failure_signature_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'failure_signature_accepted_actions.jsonl'), report_out=str(out/'failure_signature_acceptance_report.json'), audit_out=str(out/'failure_signature_acceptance_rows.jsonl'), margin_threshold=args.failure_signature_accept_margin, max_per_task=args.failure_signature_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.failure_signature_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.failure_signature_accept_cost_weight))
    cmd_train_response(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),actions=args.actions,out=str(out/'response_model.json'),lcb_kappa=1.0,min_count_for_action=2,shrink=2.0))
    if getattr(args, 'eval_response_model', False):
        cmd_eval_response(argparse.Namespace(model=str(out/'response_model.json'), responses=str(audit_dir/'responses.jsonl'), out=str(out/'response_eval_summary.json'), out_rows=str(out/'response_eval_rows.jsonl'), csv_out=str(out/'response_eval_rows.csv'), mode=args.response_eval_mode))
    cmd_quotient(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(out/'response_components.jsonl'),tolerance=args.quotient_tolerance))
    states_ir_path=out/'states_ir.jsonl'; exposure_report_path=out/'exposure_report.json'
    cmd_parse_states(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'),out=str(states_ir_path)))
    cmd_ir_defects(argparse.Namespace(ir=str(states_ir_path), out=str(out/'ir_defects.jsonl')))
    cmd_exposure_report(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(exposure_report_path)))
    ir_candidates_path = None
    ir_audit_dir = None
    ir_acceptance_path = None
    if getattr(args, 'ir_candidates', False):
        ir_candidates_path = out/'ir_candidates.jsonl'
        cmd_ir_candidates(argparse.Namespace(ir=str(states_ir_path), out=str(ir_candidates_path), max_candidates=args.ir_max_candidates))
        if getattr(args, 'audit_ir_candidates', False):
            ir_audit_dir = out/'ir_audit'
            _pipeline_audit(tasks_for_pipeline, str(ir_candidates_path), ir_audit_dir, args.ir_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(ir_audit_dir/'responses.jsonl'), out=str(out/'ir_action_report.json'), csv_out=str(out/'ir_action_report.csv'), group_keys=None))
            if getattr(args, 'ir_accept_coker', False):
                ir_acceptance_path = out/'ir_acceptance_rows.jsonl'
                cmd_accept_candidates(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), candidate_responses=str(ir_audit_dir/'responses.jsonl'), out=str(ir_acceptance_path), summary_out=str(out/'ir_acceptance_report.json'), margin_threshold=args.ir_accept_margin, cost_weight=args.ir_accept_cost_weight, carrier_weight=args.ir_accept_carrier_weight, audit_penalty=1.0, require_success=False))
        if getattr(args, 'audit_ir_candidates', False):
            ir_audit_dir = out/'ir_audit'
            _pipeline_audit(tasks_for_pipeline, str(ir_candidates_path), ir_audit_dir, args.ir_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(ir_audit_dir/'responses.jsonl'), out=str(out/'ir_action_report.json'), csv_out=str(out/'ir_action_report.csv'), group_keys=None))
            if getattr(args, 'ir_accept_coker', False):
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(ir_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'ir_accepted_actions.jsonl'), report_out=str(out/'ir_acceptance_report.json'), audit_out=str(out/'ir_acceptance_rows.jsonl'), margin_threshold=args.ir_accept_margin, max_per_task=args.ir_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.ir_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.ir_accept_cost_weight))
    registry_path=None
    promoted_registry_path=None
    if args.mine_defects:
        registry_path=out/'defect_registry.json'
        cmd_mine_defects(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'),responses=str(audit_dir/'responses.jsonl'),out=str(registry_path),scores_out=str(out/'defect_registry.scores.jsonl'),min_support=args.mine_min_support,min_response_contrast=args.mine_min_response_contrast,min_stability=args.mine_min_stability,min_intervention_success=args.mine_min_intervention_success,min_coker_reduction=args.mine_min_coker_reduction))
        cmd_auto_defects(argparse.Namespace(registry=str(registry_path),tasks=tasks_for_pipeline,states=None,out=str(out/'auto_defects.jsonl'),import_mode=args.import_mode))
    # Carrier proposals from the base audit defects.
    cmd_carrier_generate(argparse.Namespace(defects=str(audit_dir/'defects.jsonl'),out=str(out/'carrier_generated_contexts.jsonl'),threshold=args.carrier_threshold))
    actions_for_coker=args.actions
    registry_candidates_path=None
    if registry_path is not None and args.registry_candidates:
        registry_candidates_path=out/'registry_candidates.jsonl'
        cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline,registry=str(registry_path),out=str(registry_candidates_path),max_candidates=args.registry_max_candidates,registry_only=False,import_mode=args.import_mode))
        actions_for_coker=str(registry_candidates_path)
        if args.audit_registry_candidates:
            registry_audit_dir = out/'registry_audit'
            _pipeline_audit(tasks_for_pipeline, str(registry_candidates_path), registry_audit_dir, args.registry_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(registry_audit_dir/'responses.jsonl'), out=str(out/'registry_action_report.json'), csv_out=str(out/'registry_action_report.csv'), group_keys=None))
            if args.registry_accept_coker:
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(registry_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'registry_accepted_actions.jsonl'), report_out=str(out/'registry_acceptance_report.json'), audit_out=str(out/'registry_acceptance_rows.jsonl'), margin_threshold=args.registry_accept_margin, max_per_task=args.registry_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.registry_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.registry_accept_cost_weight))
        if args.promote_registry:
            promoted_registry_path=out/'defect_registry.promoted.json'
            cmd_promote_registry(argparse.Namespace(registry=str(registry_path),audits=str(out/'registry_audit') if args.audit_registry_candidates else str(audit_dir/'micro_audit.jsonl'),responses=str(out/'registry_audit'/'responses.jsonl') if args.audit_registry_candidates and (out/'registry_audit'/'responses.jsonl').exists() else str(audit_dir/'responses.jsonl'),out=str(promoted_registry_path),report_out=str(out/'defect_registry.promotion_report.json'),min_support=args.promote_min_support,min_intervention_success=args.promote_min_intervention_success,min_coker_reduction=args.promote_min_coker_reduction,min_promotion_score=args.promote_min_promotion_score,drop_rejected=args.promote_drop_rejected))
    # Premise retrieval chart.
    premise_index_path=None; premise_candidates_path=None; premise_audit_dir=None
    if args.premise_index:
        premise_index_path=out/'premise_index.json'
        cmd_build_premise_index(argparse.Namespace(tasks=tasks_for_pipeline, actions=actions_for_coker, out=str(premise_index_path)))
        hits_path=out/'premise_hits.jsonl'
        cmd_premise_retrieve(argparse.Namespace(index=str(premise_index_path),out=str(hits_path),query=None,tasks=tasks_for_pipeline,states=None,k=args.premise_top_k,kind=None,import_mode=args.import_mode))
        premise_candidates_path=out/'premise_actions.jsonl'
        cmd_premise_actions(argparse.Namespace(hits=str(hits_path),out=str(premise_candidates_path),task_id=None,max_actions_per_query=args.premise_max_actions))
        if args.audit_premise_candidates:
            premise_audit_dir=out/'premise_audit'
            _pipeline_audit(tasks_for_pipeline, str(premise_candidates_path), premise_audit_dir, args.premise_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(premise_audit_dir/'responses.jsonl'), out=str(out/'premise_action_report.json'), csv_out=str(out/'premise_action_report.csv'), group_keys=None))
            # v35: Premise Response Registry / Retrieval.  This treats
            # premise-use contexts as response/carrier embeddings rather than
            # theorem-name or lexical-similarity primitives.
            if getattr(args, 'premise_response_registry', False):
                premise_response_dir = out/'premise_response'
                premise_response_dir.mkdir(parents=True, exist_ok=True)
                cmd_premise_response_registry(argparse.Namespace(
                    responses=str(premise_audit_dir/'responses.jsonl'),
                    actions=str(premise_candidates_path),
                    out=str(premise_response_dir/'premise_response_registry.jsonl'),
                    summary_out=str(premise_response_dir/'premise_response_registry_summary.json'),
                    min_count=1,
                ))
                if getattr(args, 'premise_quotient_mine', False):
                    cmd_premise_quotient_mine(argparse.Namespace(
                        registry=str(premise_response_dir/'premise_response_registry.jsonl'),
                        out=str(premise_response_dir/'premise_quotient'),
                        cosine_threshold=0.95,
                        distance_threshold=0.25,
                        no_carrier=False,
                    ))
                if getattr(args, 'premise_response_retrieve', False):
                    # Prefer mined quotient-coordinate normals when available; otherwise
                    # fall back to an empty normal, yielding a conservative audit-prior sort.
                    normal_path = out/'quotient_coordinates'/'quotient_coordinate_response_normal.json'
                    rn = str(normal_path) if normal_path.exists() else None
                    retrieved_path = premise_response_dir/'premise_response_retrieved.jsonl'
                    retrieved_actions = out/'premise_response_actions.jsonl'
                    cmd_premise_response_retrieve(argparse.Namespace(
                        registry=str(premise_response_dir/'premise_response_registry.jsonl'),
                        out=str(retrieved_path),
                        summary_out=str(premise_response_dir/'premise_response_retrieval_summary.json'),
                        out_actions=str(retrieved_actions),
                        response_normal=rn, response_normal_json=None,
                        carrier_normal=None, carrier_normal_json=None,
                        top_k=getattr(args, 'premise_response_top_k', 32),
                        cost_weight=0.05, uncertainty_weight=0.10, audit_weight=0.20,
                        carrier_safe=False, carrier_budget=0.0,
                    ))
                    if getattr(args, 'audit_premise_response_candidates', False) and retrieved_actions.exists():
                        premise_resp_audit_dir = out/'premise_response_audit'
                        _pipeline_audit(tasks_for_pipeline, str(retrieved_actions), premise_resp_audit_dir, getattr(args, 'premise_response_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
                        cmd_action_report(argparse.Namespace(responses=str(premise_resp_audit_dir/'responses.jsonl'), out=str(out/'premise_response_action_report.json'), csv_out=str(out/'premise_response_action_report.csv'), group_keys=None))
    # v50: premise contextual quotient.  This wraps premise-use actions in
    # finite safe pre/post contexts and fingerprints the incremental response
    # probe_response - baseline_context_response.
    premise_contextual_dir = None
    premise_contextual_candidates_path = None
    premise_contextual_audit_dir = None
    premise_contextual_fingerprints_path = None
    premise_contextual_classes_path = None
    premise_quotient_retrieved_path = None
    premise_quotient_actions_path = None
    premise_use_rows_path = None
    separator_contexts_path = None
    premise_contextual_scheduled_path = None
    repair_face_ledger_path = None
    face_taxonomy_dir = None
    face_taxonomy_path = None
    obstruction_tower_dir = None
    dost_dir = None
    dost_feature_closure_path = None
    dost_feature_values_path = None
    dost_selected_features_path = None
    dost_auto_plan_path = None
    dost_audit_dir = None
    premise_contextual_requested = any(getattr(args, k, False) for k in [
        'premise_contextual_quotient',
        'premise_contextual_generate',
        'premise_contextual_bivariate',
        'audit_premise_contextual_candidates',
        'premise_contextual_mine',
        'premise_contextual_validate',
        'premise_quotient_retrieve',
        'repair_face_ledger',
        'face_taxonomy',
        'obstruction_tower',
        'dost_automation',
    ])
    if premise_contextual_requested:
        premise_contextual_dir = out / 'premise_contextual'
        premise_contextual_dir.mkdir(parents=True, exist_ok=True)
        source_actions = None
        for candidate_source in [
            locals().get('retrieved_actions'),
            locals().get('premise_candidates_path'),
            args.actions,
        ]:
            if candidate_source and Path(candidate_source).exists():
                source_actions = candidate_source
                break
        if not source_actions:
            (premise_contextual_dir / 'premise_contextual_report.json').write_text(json.dumps({
                'schema_version': 'lean-rgc-premise-contextual-pipeline-v50.0',
                'status': 'skipped_no_premise_actions',
                'canonical_status': 'premise_contextual_pipeline_chart_not_canonical',
            }, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            premise_contextual_candidates_path = premise_contextual_dir / 'premise_contextual_candidates.jsonl'
            if getattr(args, 'premise_contextual_bivariate', False):
                _stage("premise_contextual_bivariate_build_start", out=str(premise_contextual_dir), max_premises=getattr(args, 'premise_contextual_max_premises', None), max_left=getattr(args, 'premise_contextual_max_left', 4), max_right=getattr(args, 'premise_contextual_max_right', 4), audit_budget=getattr(args, 'bivariate_audit_budget', None))
                premise_use_rows_path = Path(getattr(args, 'premise_use_rows_out', None) or premise_contextual_dir / 'premise_use_rows.jsonl')
                separator_contexts_path = Path(getattr(args, 'separator_contexts_out', None) or getattr(args, 'premise_contextual_contexts', None) or premise_contextual_dir / 'separator_contexts.jsonl')
                build_premise_use_rows(
                    source_actions,
                    premise_use_rows_path,
                    summary_out=premise_contextual_dir / 'premise_use_row_report.json',
                    max_rows=getattr(args, 'premise_contextual_max_premises', None),
                )
                if not Path(separator_contexts_path).exists():
                    write_separator_contexts(
                        separator_contexts_path,
                        templates=getattr(args, 'separator_contexts_builtin', 'builtin_core'),
                        summary_out=premise_contextual_dir / 'separator_context_report.json',
                    )
                generate_bivariate_contextual_candidates(
                    premise_use_rows_path,
                    separator_contexts_path,
                    premise_contextual_candidates_path,
                    summary_out=premise_contextual_dir / 'bivariate_contextual_candidate_report.json',
                    max_rows=getattr(args, 'premise_contextual_max_premises', None),
                    max_pre=getattr(args, 'premise_contextual_max_left', 4),
                    max_post=getattr(args, 'premise_contextual_max_right', 4),
                    max_candidates=getattr(args, 'premise_contextual_max_candidates', None),
                    include_baselines=True,
                )
                premise_contextual_scheduled_path = premise_contextual_dir / 'bivariate_contextual_scheduled_actions.jsonl'
                schedule_bivariate_candidates(
                    premise_contextual_candidates_path,
                    premise_contextual_scheduled_path,
                    budget=getattr(args, 'bivariate_audit_budget', None) or getattr(args, 'premise_contextual_audit_max_actions', 32),
                    report_out=premise_contextual_dir / 'bivariate_contextual_schedule_report.json',
                    require_baseline_pairs=getattr(args, 'bivariate_require_baseline_pairs', False) or getattr(args, 'premise_contextual_baseline_required', False),
                )
                _stage("premise_contextual_bivariate_build_done", candidates=str(premise_contextual_candidates_path), scheduled=str(premise_contextual_scheduled_path))
            else:
                generate_premise_contextual_candidates(
                    source_actions,
                    premise_contextual_candidates_path,
                    contexts_path=getattr(args, 'premise_contextual_contexts', None),
                    max_premises=getattr(args, 'premise_contextual_max_premises', None),
                    max_left=getattr(args, 'premise_contextual_max_left', 4),
                    max_right=getattr(args, 'premise_contextual_max_right', 4),
                    max_candidates=getattr(args, 'premise_contextual_max_candidates', None),
                    include_identity=True,
                    include_baselines=True,
                )
            if getattr(args, 'audit_premise_contextual_candidates', False) or getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_mine', False) or getattr(args, 'premise_contextual_validate', False) or getattr(args, 'premise_quotient_retrieve', False) or getattr(args, 'face_taxonomy', False) or getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                premise_contextual_audit_dir = out / 'premise_contextual_audit'
                audit_actions_path = premise_contextual_scheduled_path if premise_contextual_scheduled_path is not None else premise_contextual_candidates_path
                audit_budget = getattr(args, 'bivariate_audit_budget', None) or getattr(args, 'premise_contextual_audit_max_actions', 32)
                if getattr(args, 'premise_contextual_bivariate', False) and audit_actions_path and Path(audit_actions_path).exists():
                    task_budgeted_actions_path = premise_contextual_dir / 'bivariate_contextual_task_budgeted_actions.jsonl'
                    task_budget_summary = _materialize_total_budget_task_actions(
                        audit_actions_path,
                        _normalize_tasks_imports(_load_tasks(tasks_for_pipeline), args.import_mode, args.workdir, args.lean_cmd),
                        task_budgeted_actions_path,
                        budget=audit_budget,
                        require_baseline_pairs=getattr(args, 'bivariate_require_baseline_pairs', False) or getattr(args, 'premise_contextual_baseline_required', False),
                    )
                    (premise_contextual_dir / 'bivariate_contextual_task_budget_report.json').write_text(json.dumps(task_budget_summary, indent=2, ensure_ascii=False), encoding='utf-8')
                    _stage("premise_contextual_task_budget_materialized", **task_budget_summary)
                    audit_actions_path = task_budgeted_actions_path
                use_kernel_context_cache = bool(
                    getattr(args, 'premise_contextual_bivariate', False)
                    and getattr(args, 'audit_mode', 'batch') == 'server'
                    and getattr(args, 'native_exec_mode', 'source_check') == 'kernel_rpc'
                    and getattr(args, 'server_backend', 'auto') in {'native', 'jsonl'}
                    and not getattr(args, 'dry_run', False)
                )
                if use_kernel_context_cache:
                    kc_cfg = LeanServerConfig(
                        lean_cmd=args.lean_cmd,
                        workdir=args.workdir,
                        timeout_s=args.timeout_s,
                        dry_run=args.dry_run,
                        keep_files=args.keep_files,
                        cache_dir=args.cache_dir or str(out/'cache'),
                        trace_state=args.trace_state,
                        server_cmd=getattr(args, 'server_cmd', None),
                        backend=getattr(args, 'server_backend', 'auto'),
                        fallback_to_file=not getattr(args, 'server_no_fallback', False),
                        native_exec_mode=getattr(args, 'native_exec_mode', 'source_check'),
                    )
                    audit_contextual_candidates_with_kernel_cache(
                        _normalize_tasks_imports(_load_tasks(tasks_for_pipeline), args.import_mode, args.workdir, args.lean_cmd),
                        _load_actions(audit_actions_path),
                        out_dir=premise_contextual_audit_dir,
                        server_config=kc_cfg,
                        max_actions=audit_budget,
                        resume=args.resume,
                        flush_every=args.flush_every,
                    )
                else:
                    _stage("premise_contextual_audit_start", actions=str(audit_actions_path), audit_budget=audit_budget, out=str(premise_contextual_audit_dir))
                    _pipeline_audit(tasks_for_pipeline, str(audit_actions_path), premise_contextual_audit_dir, audit_budget, state_candidates=False, candidate_mode='state')
                    _stage("premise_contextual_audit_done", out=str(premise_contextual_audit_dir))
                cmd_action_report(argparse.Namespace(responses=str(premise_contextual_audit_dir/'responses.jsonl'), out=str(out/'premise_contextual_action_report.json'), csv_out=str(out/'premise_contextual_action_report.csv'), group_keys=None))
                premise_contextual_fingerprints_path = premise_contextual_dir / 'premise_contextual_fingerprints.jsonl'
                build_premise_contextual_fingerprints(
                    responses_path=premise_contextual_audit_dir/'responses.jsonl',
                    actions_path=audit_actions_path,
                    out=premise_contextual_fingerprints_path,
                    summary_out=premise_contextual_dir/'premise_contextual_fingerprint_report.json',
                    min_contexts=1,
                    baseline_required=getattr(args, 'premise_contextual_baseline_required', False),
                )
                if getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_mine', False) or getattr(args, 'premise_contextual_validate', False) or getattr(args, 'premise_quotient_retrieve', False) or getattr(args, 'face_taxonomy', False) or getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                    mine_premise_contextual_quotient(
                        fingerprints_path=premise_contextual_fingerprints_path,
                        out_dir=premise_contextual_dir,
                        epsilon=getattr(args, 'premise_contextual_epsilon', 0.25),
                        cosine_threshold=getattr(args, 'premise_contextual_cosine_threshold', 0.95),
                        domain_jaccard_threshold=getattr(args, 'premise_contextual_domain_jaccard_threshold', 0.0),
                    )
                    premise_contextual_classes_path = premise_contextual_dir / 'premise_quotient_classes.jsonl'
                if getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_validate', False) or getattr(args, 'face_taxonomy', False) or getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and (not getattr(args, 'skip_vacuous_premise_quotient', False) or read_jsonl(premise_contextual_classes_path)):
                        validate_premise_contextual_quotient(
                            fingerprints_path=premise_contextual_fingerprints_path,
                            classes_path=premise_contextual_classes_path,
                            out_rows=premise_contextual_dir/'premise_quotient_validation_rows.jsonl',
                            out_report=premise_contextual_dir/'premise_quotient_validation_report.json',
                            epsilon_holdout=getattr(args, 'premise_contextual_epsilon_holdout', 0.35),
                            separation_delta=getattr(args, 'premise_contextual_separation_delta', 0.10),
                            domain_jaccard_min=getattr(args, 'premise_contextual_domain_jaccard_threshold', 0.0),
                        )
                if getattr(args, 'repair_face_ledger', False) or getattr(args, 'face_taxonomy', False) or getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and read_jsonl(premise_contextual_classes_path):
                        repair_face_ledger_path = premise_contextual_dir / 'repair_faces.jsonl'
                        build_repair_face_ledger(
                            fingerprints_path=premise_contextual_fingerprints_path,
                            classes_path=premise_contextual_classes_path,
                            validation_rows_path=premise_contextual_dir/'premise_quotient_validation_rows.jsonl',
                            out=repair_face_ledger_path,
                            report_out=premise_contextual_dir/'repair_face_ledger_report.json',
                        )
                if getattr(args, 'dost_automation', False):
                    if premise_contextual_fingerprints_path and premise_contextual_fingerprints_path.exists() and read_jsonl(premise_contextual_fingerprints_path):
                        dost_dir = premise_contextual_dir / 'dost'
                        dost_dir.mkdir(parents=True, exist_ok=True)
                        write_primitive_observables(
                            dost_dir / 'primitive_observables.jsonl',
                            report_out=dost_dir / 'primitive_observables_report.json',
                        )
                        build_bounded_transcripts(
                            premise_contextual_fingerprints_path,
                            dost_dir / 'bounded_transcripts.jsonl',
                            summary_out=dost_dir / 'bounded_transcripts_report.json',
                            kernel_state_mode=getattr(args, 'kernel_state_mode', 'features'),
                        )
                        dost_feature_closure_path = dost_dir / 'feature_closure.jsonl'
                        dost_feature_values_path = dost_dir / 'bounded_feature_transcripts.jsonl'
                        build_feature_closure(
                            dost_dir / 'bounded_transcripts.jsonl',
                            dost_feature_closure_path,
                            values_out=dost_feature_values_path,
                            report_out=dost_dir / 'feature_closure_report.json',
                            max_features=getattr(args, 'dost_max_features', 512),
                        )
                if getattr(args, 'face_taxonomy', False) or getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                    if premise_contextual_fingerprints_path and premise_contextual_fingerprints_path.exists() and read_jsonl(premise_contextual_fingerprints_path):
                        face_taxonomy_dir = premise_contextual_dir / 'face_taxonomy'
                        validation_path = premise_contextual_dir / 'premise_quotient_validation_rows.jsonl'
                        face_taxonomy_path = face_taxonomy_dir / 'dual_face_taxonomy.jsonl'
                        build_dual_face_taxonomy(
                            fingerprints_path=premise_contextual_fingerprints_path,
                            classes_path=premise_contextual_classes_path if premise_contextual_classes_path and premise_contextual_classes_path.exists() else None,
                            validation_rows_path=validation_path if validation_path.exists() else None,
                            repair_faces_path=repair_face_ledger_path if repair_face_ledger_path and Path(repair_face_ledger_path).exists() else None,
                            generated_features_path=dost_feature_values_path if dost_feature_values_path and Path(dost_feature_values_path).exists() else None,
                            out_dir=face_taxonomy_dir,
                            min_support=getattr(args, 'face_taxonomy_min_support', 1),
                            min_retrieval_support=getattr(args, 'face_taxonomy_min_retrieval_support', 2),
                            max_concepts=getattr(args, 'face_taxonomy_max_concepts', 256),
                            max_pair_properties=getattr(args, 'face_taxonomy_max_pair_properties', 80),
                            allow_singleton_retrieval=getattr(args, 'face_taxonomy_allow_singleton_retrieval', False),
                        )
                if getattr(args, 'obstruction_tower', False) or getattr(args, 'dost_automation', False):
                    if face_taxonomy_dir and face_taxonomy_path and Path(face_taxonomy_path).exists() and read_jsonl(face_taxonomy_path):
                        obstruction_tower_dir = premise_contextual_dir / 'obstruction_tower'
                        build_canonical_obstruction_tower(
                            out_dir=obstruction_tower_dir,
                            fingerprints_path=premise_contextual_fingerprints_path,
                            taxonomy_dir=face_taxonomy_dir,
                            taxonomy_path=face_taxonomy_path,
                            concept_lattice_path=face_taxonomy_dir/'face_concept_lattice.jsonl',
                            row_memberships_path=face_taxonomy_dir/'row_face_memberships.jsonl',
                            retrieval_faces_path=face_taxonomy_dir/'retrieval_allowed_faces.jsonl',
                            repair_faces_path=repair_face_ledger_path if repair_face_ledger_path and Path(repair_face_ledger_path).exists() else None,
                            validation_rows_path=premise_contextual_dir/'premise_quotient_validation_rows.jsonl',
                            min_retrieval_support=getattr(args, 'face_taxonomy_min_retrieval_support', 2),
                        )
                if getattr(args, 'dost_automation', False):
                    if dost_feature_closure_path and dost_feature_values_path and Path(dost_feature_closure_path).exists() and Path(dost_feature_values_path).exists():
                        if dost_dir is None:
                            dost_dir = premise_contextual_dir / 'dost'
                            dost_dir.mkdir(parents=True, exist_ok=True)
                        dost_selected_features_path = dost_dir / 'selected_features.jsonl'
                        select_features_for_dual_obstructions(
                            dost_feature_closure_path,
                            dost_feature_values_path,
                            dost_selected_features_path,
                            report_out=dost_dir / 'feature_selection_report.json',
                            taxonomy_path=face_taxonomy_path if face_taxonomy_path and Path(face_taxonomy_path).exists() else None,
                            max_selected_per_dual=getattr(args, 'dost_max_selected_per_dual', 8),
                        )
                        dost_auto_plan_path = dost_dir / 'auto_plan.json'
                        build_dost_auto_plan(
                            dost_auto_plan_path,
                            selected_features_path=dost_selected_features_path,
                            taxonomy_path=face_taxonomy_path if face_taxonomy_path and Path(face_taxonomy_path).exists() else None,
                            tower_next_actions_path=obstruction_tower_dir / 'tower_next_actions.jsonl' if obstruction_tower_dir and (obstruction_tower_dir / 'tower_next_actions.jsonl').exists() else None,
                            tower_summary_path=obstruction_tower_dir / 'tower_summary.json' if obstruction_tower_dir and (obstruction_tower_dir / 'tower_summary.json').exists() else None,
                            compiled_experiment_out=dost_dir / 'compiled_experiment.sh',
                            notebook_out=dost_dir / 'compiled_notebook_cells.ipynb',
                            kernel_state_mode=getattr(args, 'kernel_state_mode', 'features'),
                        )
                        dost_report = {
                            'schema_version': 'lean-rgc-dost-automation-stack-v57.0',
                            'out_dir': str(dost_dir),
                            'artifacts': {
                                'primitive_observables': str(dost_dir / 'primitive_observables.jsonl'),
                                'bounded_transcripts': str(dost_dir / 'bounded_transcripts.jsonl'),
                                'feature_closure': str(dost_feature_closure_path),
                                'feature_values': str(dost_feature_values_path),
                                'selected_features': str(dost_selected_features_path),
                                'feature_selection_report': str(dost_dir / 'feature_selection_report.json'),
                                'auto_plan': str(dost_auto_plan_path),
                                'compiled_experiment': str(dost_dir / 'compiled_experiment.sh'),
                                'compiled_notebook_cells': str(dost_dir / 'compiled_notebook_cells.ipynb'),
                            },
                            'canonical_status': 'dost_automation_stack_is_finite_chart_not_canonical',
                        }
                        (dost_dir / 'dost_obstruction_report.json').write_text(json.dumps(dost_report, indent=2, ensure_ascii=False), encoding='utf-8')
                        dost_audit_dir = dost_dir / 'audit'
                        build_dost_audit_reports(
                            dost_audit_dir,
                            run_dir=out,
                            server_summary_path=premise_contextual_audit_dir / 'summary.json' if premise_contextual_audit_dir and (premise_contextual_audit_dir / 'summary.json').exists() else None,
                            fingerprints_path=premise_contextual_fingerprints_path,
                            fingerprint_report_path=premise_contextual_dir / 'premise_contextual_fingerprint_report.json' if premise_contextual_dir and (premise_contextual_dir / 'premise_contextual_fingerprint_report.json').exists() else None,
                            premise_use_rows_path=premise_use_rows_path if premise_use_rows_path and Path(premise_use_rows_path).exists() else None,
                            classes_path=premise_contextual_classes_path if premise_contextual_classes_path and Path(premise_contextual_classes_path).exists() else None,
                            validation_rows_path=premise_contextual_dir / 'premise_quotient_validation_rows.jsonl' if premise_contextual_dir and (premise_contextual_dir / 'premise_quotient_validation_rows.jsonl').exists() else None,
                            validation_report_path=premise_contextual_dir / 'premise_quotient_validation_report.json' if premise_contextual_dir and (premise_contextual_dir / 'premise_quotient_validation_report.json').exists() else None,
                            taxonomy_path=face_taxonomy_path if face_taxonomy_path and Path(face_taxonomy_path).exists() else None,
                            taxonomy_report_path=face_taxonomy_dir / 'dual_face_taxonomy_report.json' if face_taxonomy_dir and (face_taxonomy_dir / 'dual_face_taxonomy_report.json').exists() else None,
                            retrieval_faces_path=face_taxonomy_dir / 'retrieval_allowed_faces.jsonl' if face_taxonomy_dir and (face_taxonomy_dir / 'retrieval_allowed_faces.jsonl').exists() else None,
                            tower_summary_path=obstruction_tower_dir / 'tower_summary.json' if obstruction_tower_dir and (obstruction_tower_dir / 'tower_summary.json').exists() else None,
                            tower_next_actions_path=obstruction_tower_dir / 'tower_next_actions.jsonl' if obstruction_tower_dir and (obstruction_tower_dir / 'tower_next_actions.jsonl').exists() else None,
                            dost_report_path=dost_dir / 'dost_obstruction_report.json',
                            feature_selection_report_path=dost_dir / 'feature_selection_report.json',
                            selected_features_path=dost_selected_features_path,
                            responses_path=premise_contextual_audit_dir / 'responses.jsonl' if premise_contextual_audit_dir and (premise_contextual_audit_dir / 'responses.jsonl').exists() else None,
                            actions_path=args.actions,
                        )
                if getattr(args, 'premise_quotient_retrieve', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and (not getattr(args, 'skip_vacuous_premise_quotient', False) or read_jsonl(premise_contextual_classes_path)):
                        normal_path = out/'quotient_coordinates'/'quotient_coordinate_response_normal.json'
                        rn = str(normal_path) if normal_path.exists() else None
                        premise_quotient_retrieved_path = premise_contextual_dir / 'premise_quotient_retrieved_actions.jsonl'
                        premise_quotient_actions_path = out / 'premise_quotient_actions.jsonl'
                        retrieve_premise_quotient_classes(
                            classes_path=premise_contextual_classes_path,
                            out=premise_quotient_retrieved_path,
                            summary_out=premise_contextual_dir/'premise_quotient_retrieval_summary.json',
                            response_normal=_parse_json_or_file(rn),
                            carrier_normal={},
                            top_k=getattr(args, 'premise_quotient_top_k', 32),
                        )
                        premise_quotient_retrieved_actions(retrieved_path=premise_quotient_retrieved_path, out=premise_quotient_actions_path)
                        if getattr(args, 'audit_premise_quotient_candidates', False) and premise_quotient_actions_path.exists():
                            premise_quotient_audit_dir = out / 'premise_quotient_audit'
                            _pipeline_audit(tasks_for_pipeline, str(premise_quotient_actions_path), premise_quotient_audit_dir, getattr(args, 'premise_quotient_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
                            cmd_action_report(argparse.Namespace(responses=str(premise_quotient_audit_dir/'responses.jsonl'), out=str(out/'premise_quotient_action_report.json'), csv_out=str(out/'premise_quotient_action_report.csv'), group_keys=None))
    # v58-v62: DOST -> URS -> CRG -> CGT soft-search extension.  Generator
    # outputs stay witness-only; POMS promotion remains the canonical gate.
    crg_dir = None
    crg_response_completion_path = None
    crg_registry_path = None
    crg_problems_path = None
    crg_relaxed_candidates_path = None
    crg_hardening_attempts_path = None
    crg_hard_candidates_path = None
    crg_candidate_audit_dir = None
    crg_audit_rows_path = None
    crg_gap_report_path = None
    crg_poms_evidence_path = None
    crg_robust_acceptance_rows_path = None
    crg_robust_acceptance_report_path = None
    crg_robust_accepted_actions_path = None
    repair_flow_steps_path = None
    concept_geometry_dir = None
    concept_points_path = None
    concept_edges_path = None
    concept_search_rows_path = None
    concept_decoded_atoms_path = None
    crg_requested = any(
        getattr(args, name, False)
        for name in (
            'crg',
            'crg_build_problems',
            'crg_optimize',
            'crg_hardening',
            'audit_crg_candidates',
            'crg_robust_accept',
            'crg_audit',
            'crg_poms_bridge',
            'repair_gradient_flow',
            'concept_geometry',
            'concept_search',
            'concept_decode',
        )
    )
    if crg_requested:
        crg_dir = out / 'crg'
        crg_dir.mkdir(parents=True, exist_ok=True)

        def _existing_path(path_obj):
            if not path_obj:
                return None
            p = Path(path_obj)
            return p if p.exists() else None

        response_input_path = _existing_path(audit_dir / 'responses.jsonl')
        premise_response_registry_path = _existing_path(out / 'premise_response' / 'premise_response_registry.jsonl')
        quotient_coordinates_path = _existing_path(out / 'quotient_coordinates' / 'quotient_coordinates.jsonl')
        carrier_quotient_path = _existing_path(out / 'carrier_quotient' / 'carrier_quotient_coordinates.jsonl')
        tower_dual_components_path = _existing_path(Path(obstruction_tower_dir) / 'tower_dual_components.jsonl') if locals().get('obstruction_tower_dir') else None
        tower_retrieval_path = _existing_path(Path(obstruction_tower_dir) / 'tower_retrieval_candidates.jsonl') if locals().get('obstruction_tower_dir') else None

        crg_response_completion_path = crg_dir / 'response_completion.json'
        build_response_completion(
            out=crg_response_completion_path,
            responses_path=response_input_path,
            fingerprints_path=_existing_path(locals().get('premise_contextual_fingerprints_path')),
            action_geometry_path=_existing_path(locals().get('action_geometry_registry_path')),
            premise_registry_path=premise_response_registry_path,
            topology='weighted_projective',
        )

        crg_registry_path = crg_dir / 'repair_species_registry.jsonl'
        build_repair_species_registry(
            out=crg_registry_path,
            summary_out=crg_dir / 'repair_species_registry_summary.json',
            actions_path=_existing_path(args.actions),
            action_geometry_path=_existing_path(locals().get('action_geometry_registry_path')),
            premise_registry_path=premise_response_registry_path,
            quotient_coordinates_path=quotient_coordinates_path,
            carrier_quotient_path=carrier_quotient_path,
            tower_retrieval_path=tower_retrieval_path,
            repair_faces_path=_existing_path(locals().get('repair_face_ledger_path')),
            run_id=pipeline_run_id,
        )

        crg_problems_path = crg_dir / 'crg_problems.jsonl'
        build_crg_problems(
            out=crg_problems_path,
            repair_faces_path=_existing_path(locals().get('repair_face_ledger_path')),
            tower_dual_components_path=tower_dual_components_path,
            response_completion_path=crg_response_completion_path,
            summary_out=crg_dir / 'crg_problems_summary.json',
            repair_space_scope='relaxed',
            run_id=pipeline_run_id,
            parent_ids=[str(crg_registry_path)],
        )

        if getattr(args, 'concept_geometry', False) or getattr(args, 'concept_search', False) or getattr(args, 'concept_decode', False):
            concept_geometry_dir = out / 'concept_geometry'
            concept_geometry_dir.mkdir(parents=True, exist_ok=True)
            build_concept_geometry(
                out_dir=concept_geometry_dir,
                taxonomy_path=_existing_path(locals().get('face_taxonomy_path')),
                selected_features_path=_existing_path(locals().get('dost_selected_features_path')),
                summary_out=concept_geometry_dir / 'concept_geometry_summary.json',
                run_id=pipeline_run_id,
            )
            concept_points_path = concept_geometry_dir / 'concept_points.jsonl'
            concept_edges_path = concept_geometry_dir / 'concept_edges.jsonl'
            if getattr(args, 'concept_search', False) or getattr(args, 'concept_decode', False):
                concept_search_rows_path = concept_geometry_dir / 'concept_search_rows.jsonl'
                search_concepts(
                    concept_points_path=concept_points_path,
                    concept_edges_path=concept_edges_path,
                    out=concept_search_rows_path,
                    summary_out=concept_geometry_dir / 'concept_search_summary.json',
                    problems_path=crg_problems_path,
                    top_k=getattr(args, 'concept_search_top_k', 32),
                    mode=getattr(args, 'concept_search_mode', 'response-nearest-neighbor'),
                )
            if getattr(args, 'concept_decode', False) and concept_search_rows_path and concept_search_rows_path.exists():
                concept_decoded_atoms_path = concept_geometry_dir / 'concept_decoded_repair_atoms.jsonl'
                decode_concepts_to_repair_atoms(
                    concept_search_path=concept_search_rows_path,
                    concept_points_path=concept_points_path,
                    out=concept_decoded_atoms_path,
                    summary_out=concept_geometry_dir / 'concept_decode_summary.json',
                    top_k=getattr(args, 'concept_search_top_k', 32),
                )
                decoded_atoms = read_jsonl(concept_decoded_atoms_path)
                if decoded_atoms:
                    write_records(crg_registry_path, read_jsonl(crg_registry_path) + decoded_atoms, schema_version=SCHEMA_REPAIR_SPECIES_REGISTRY, run_id=pipeline_run_id)

        if getattr(args, 'crg', False) or getattr(args, 'crg_optimize', False):
            crg_relaxed_candidates_path = crg_dir / 'relaxed_candidates.jsonl'
            generate_nonlinear_repair_candidates(
                problems_path=crg_problems_path,
                registry_path=crg_registry_path,
                out=crg_relaxed_candidates_path,
                response_completion_path=crg_response_completion_path,
                summary_out=crg_dir / 'relaxed_candidates_summary.json',
                optimizer=getattr(args, 'crg_optimizer', 'convex_mixture'),
                temperature=getattr(args, 'crg_temperature', 1.0),
                top_k=getattr(args, 'crg_top_k', 16),
                cost_weight=getattr(args, 'crg_cost_weight', 0.0),
                audit_weight=getattr(args, 'crg_audit_weight', 0.0),
                source_weight=getattr(args, 'crg_source_weight', 0.0),
                ghost_weight=getattr(args, 'crg_ghost_weight', 0.0),
                hardening_weight=getattr(args, 'crg_hardening_weight', 0.0),
                run_id=pipeline_run_id,
                parent_ids=[str(crg_problems_path), str(crg_registry_path)],
            )
        if (getattr(args, 'crg', False) or getattr(args, 'crg_hardening', False)) and crg_relaxed_candidates_path and crg_relaxed_candidates_path.exists():
            crg_hardening_attempts_path = crg_dir / 'hardening_attempts.jsonl'
            crg_hard_candidates_path = crg_dir / 'hard_candidates.jsonl'
            harden_crg_candidates(
                candidates_path=crg_relaxed_candidates_path,
                out_attempts=crg_hardening_attempts_path,
                out_actions=crg_hard_candidates_path,
                summary_out=crg_dir / 'hardening_summary.json',
                method='mixture_to_beam',
                top_k=getattr(args, 'crg_hardening_top_k', 3),
                run_id=pipeline_run_id,
                parent_ids=[str(crg_relaxed_candidates_path)],
            )
        if getattr(args, 'audit_crg_candidates', False) and crg_hard_candidates_path and crg_hard_candidates_path.exists():
            crg_candidate_audit_dir = crg_dir / 'candidate_audit'
            _stage("crg_candidate_audit_start", actions=str(crg_hard_candidates_path), max_actions=getattr(args, 'crg_audit_max_actions', 16), out=str(crg_candidate_audit_dir))
            _pipeline_audit(tasks_for_pipeline, str(crg_hard_candidates_path), crg_candidate_audit_dir, getattr(args, 'crg_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            _stage("crg_candidate_audit_done", out=str(crg_candidate_audit_dir))
            cmd_action_report(argparse.Namespace(responses=str(crg_candidate_audit_dir/'responses.jsonl'), out=str(crg_dir/'candidate_audit_action_report.json'), csv_out=str(crg_dir/'candidate_audit_action_report.csv'), group_keys=None))
        if getattr(args, 'crg_robust_accept', False) and crg_candidate_audit_dir and (crg_candidate_audit_dir / 'responses.jsonl').exists():
            crg_robust_acceptance_rows_path = crg_dir / 'crg_robust_acceptance_rows.jsonl'
            crg_robust_acceptance_report_path = crg_dir / 'crg_robust_acceptance_report.json'
            crg_robust_accepted_actions_path = crg_dir / 'crg_robust_accepted_actions.jsonl'
            run_robust_acceptance(
                audit_dir / 'responses.jsonl',
                crg_candidate_audit_dir / 'responses.jsonl',
                crg_robust_acceptance_rows_path,
                summary_out=crg_robust_acceptance_report_path,
                accepted_actions_out=crg_robust_accepted_actions_path,
                margin_threshold=0.0,
                cost_weight=0.05,
                carrier_bonus=0.7,
                max_per_task=16,
            )
        if (getattr(args, 'crg', False) or getattr(args, 'crg_audit', False)) and crg_relaxed_candidates_path and crg_hardening_attempts_path:
            crg_audit_rows_path = crg_dir / 'crg_audit_rows.jsonl'
            crg_gap_report_path = crg_dir / 'hardening_gap_report.json'
            crg_poms_evidence_path = crg_dir / 'crg_poms_evidence.jsonl' if (getattr(args, 'crg', False) or getattr(args, 'crg_poms_bridge', False)) else None
            audited_responses_path = crg_candidate_audit_dir / 'responses.jsonl' if crg_candidate_audit_dir and (crg_candidate_audit_dir / 'responses.jsonl').exists() else None
            audit_crg_candidates(
                candidates_path=crg_relaxed_candidates_path,
                hardening_attempts_path=crg_hardening_attempts_path,
                audited_responses_path=audited_responses_path,
                out_rows=crg_audit_rows_path,
                poms_out=crg_poms_evidence_path,
                summary_out=crg_dir / 'crg_audit_summary.json',
            )
            build_hardening_gap_report(
                crg_audit_rows_path=crg_audit_rows_path,
                out=crg_gap_report_path,
            )
        if getattr(args, 'repair_gradient_flow', False):
            repair_flow_steps_path = crg_dir / 'repair_flow_steps.jsonl'
            repair_gradient_flow_steps(
                problems_path=crg_problems_path,
                registry_path=crg_registry_path,
                out=repair_flow_steps_path,
                response_completion_path=crg_response_completion_path,
                previous_candidates_path=crg_relaxed_candidates_path if crg_relaxed_candidates_path and crg_relaxed_candidates_path.exists() else None,
                summary_out=crg_dir / 'repair_flow_summary.json',
                top_k=getattr(args, 'crg_top_k', 16),
            )
    # v37: source-budget scheduler across candidate families.  This is a
    # finite audit-budget allocation chart, not a canonical selector.
    source_budget_dir = None
    source_budget_actions_path = None
    source_budget_audit_dir = None
    source_budget_report_path = None
    if getattr(args, 'source_budget', False):
        source_budget_dir = out / 'source_budget'
        source_budget_dir.mkdir(parents=True, exist_ok=True)
        source_specs = []
        def _add_source_spec(name, path_obj):
            if path_obj and Path(path_obj).exists() and read_jsonl(path_obj):
                source_specs.append(f"{name}={Path(path_obj)}")
        _add_source_spec('qgen', locals().get('qgen_context_candidates_path'))
        _add_source_spec('qgen_registry', locals().get('qgen_registry_candidates_path'))
        _add_source_spec('action_geometry', locals().get('action_geometry_candidates_path'))
        _add_source_spec('quotient_coordinate', locals().get('quotient_coordinate_candidates_path'))
        _add_source_spec('quotient_coordinate_registry', locals().get('quotient_coordinate_registry_candidates_path'))
        _add_source_spec('carrier_quotient', locals().get('carrier_quotient_candidates_path'))
        _add_source_spec('contextual_probe', locals().get('contextual_probe_candidates_path'))
        _add_source_spec('registry', locals().get('registry_candidates_path'))
        _add_source_spec('failure_signature', locals().get('failure_signature_actions_path'))
        _add_source_spec('ir', locals().get('ir_candidates_path'))
        _add_source_spec('premise', locals().get('premise_candidates_path'))
        _add_source_spec('premise_response', locals().get('retrieved_actions'))
        _add_source_spec('premise_contextual', locals().get('premise_contextual_candidates_path'))
        _add_source_spec('premise_quotient', locals().get('premise_quotient_actions_path'))
        _add_source_spec('crg_hardening', locals().get('crg_hard_candidates_path'))
        if source_specs:
            source_budget_actions_path = source_budget_dir / 'source_budget_actions.jsonl'
            source_budget_report_path = source_budget_dir / 'source_budget_report.json'
            source_budget_rows_path = source_budget_dir / 'source_budget_rows.jsonl'
            sb_cfg = SourceBudgetConfig(
                total_budget=getattr(args, 'source_budget_budget', None) or args.max_actions,
                min_per_source=getattr(args, 'source_budget_min_per_source', 0),
                max_per_source=getattr(args, 'source_budget_max_per_source', None),
                per_task_cap=getattr(args, 'source_budget_per_task_cap', None),
                per_action_cap=getattr(args, 'source_budget_per_action_cap', 1),
                coker_weight=getattr(args, 'source_budget_coker_weight', 1.0),
                carrier_weight=getattr(args, 'source_budget_carrier_weight', 0.5),
                uncertainty_weight=getattr(args, 'source_budget_uncertainty_weight', 0.25),
                novelty_weight=getattr(args, 'source_budget_novelty_weight', 0.15),
                success_weight=getattr(args, 'source_budget_success_weight', 0.25),
                cost_weight=getattr(args, 'source_budget_cost_weight', 0.10),
                timeout_weight=getattr(args, 'source_budget_timeout_weight', 0.50),
                gamma_aware=getattr(args, 'source_budget_gamma_aware', False),
                gamma_mode=getattr(args, 'source_budget_gamma_value_mode', 'finite_horizon'),
                gamma_horizon=getattr(args, 'source_budget_gamma_horizon', 4),
                gamma_discount=getattr(args, 'source_budget_gamma_discount', 1.0),
                gamma_value_weight=getattr(args, 'source_budget_gamma_value_weight', 0.50),
                gamma_tail_value_weight=getattr(args, 'source_budget_gamma_tail_value_weight', None),
                gamma_tail_risk_weight=getattr(args, 'source_budget_gamma_tail_risk_weight', 0.50),
                gamma_tail_radius_weight=getattr(args, 'source_budget_gamma_tail_radius_weight', 0.0),
                gamma_stability_delta=getattr(args, 'source_budget_gamma_stability_delta', 0.05),
                gamma_tail_risk_mode=getattr(args, 'source_budget_gamma_tail_risk_mode', 'spectral'),
            )
            source_budget_schedule_from_files(
                candidate_specs=source_specs,
                out_actions=source_budget_actions_path,
                out_rows=source_budget_rows_path,
                out_report=source_budget_report_path,
                db_path=getattr(args, 'audit_scheduler_db', None),
                response_paths=[str(audit_dir/'responses.jsonl')] if (audit_dir/'responses.jsonl').exists() else None,
                config=sb_cfg,
            )
            if getattr(args, 'audit_source_budget_candidates', False) and source_budget_actions_path.exists():
                source_budget_audit_dir = out / 'source_budget_audit'
                _pipeline_audit(tasks_for_pipeline, str(source_budget_actions_path), source_budget_audit_dir, getattr(args, 'source_budget_budget', None) or args.max_actions, state_candidates=False, candidate_mode='state')
                cmd_action_report(argparse.Namespace(responses=str(source_budget_audit_dir/'responses.jsonl'), out=str(out/'source_budget_action_report.json'), csv_out=str(out/'source_budget_action_report.csv'), group_keys=None))
        else:
            (source_budget_dir / 'source_budget_report.json').write_text(json.dumps({'schema_version': 'lean-rgc-source-budget-scheduler-v46.0', 'status': 'skipped_no_candidate_sources', 'canonical_status': 'source_budget_schedule_chart_not_canonical'}, indent=2, ensure_ascii=False), encoding='utf-8')

    if actions_for_coker is None:
        cand_path=out/'generated_candidates.jsonl'
        cmd_candidates(argparse.Namespace(tasks=tasks_for_pipeline,out=str(cand_path),max_candidates=args.max_actions,candidate_mode=args.candidate_mode,import_mode=args.import_mode))
        actions_for_coker=str(cand_path)
    carrier_actions_path=out/'carrier_actions.jsonl'
    cmd_carrier_actions(argparse.Namespace(proposals=str(out/'carrier_generated_contexts.jsonl'),out=str(carrier_actions_path),prefix='carrier',max_actions_per_context=8))
    cmd_carrier_coker(argparse.Namespace(defects=str(audit_dir/'defects.jsonl'),actions=actions_for_coker,out=str(out/'carrier_coker.jsonl')))
    carrier_matrix_path = None
    carrier_matrix_merged_path = None
    if getattr(args, 'carrier_matrix', False):
        carrier_matrix_path = out/'carrier_matrix.json'
        cmd_carrier_matrix(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(carrier_matrix_path), shrink=args.carrier_matrix_shrink, min_count=args.carrier_matrix_min_count))
        matrix_for_actions = carrier_matrix_path
        if getattr(args, 'carrier_matrix_merge_qgen', False) and qgen_carrier_incidence_path and qgen_carrier_incidence_path.exists():
            carrier_matrix_merged_path = out/'carrier_matrix_qgen.json'
            patch_path_for_merge = qgen_carrier_incidence_path
            if getattr(args, 'carrier_matrix_qgen_audit_patches', False):
                patch_audit_responses = None
                if qgen_audit_dir and (qgen_audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = qgen_audit_dir/'responses.jsonl'
                elif qgen_registry_audit_dir and (qgen_registry_audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = qgen_registry_audit_dir/'responses.jsonl'
                elif (audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = audit_dir/'responses.jsonl'
                if patch_audit_responses is not None:
                    audited_patches = out/'qgen_carrier_incidence_audited.jsonl'
                    cmd_carrier_patch_audit(argparse.Namespace(
                        patches=str(qgen_carrier_incidence_path),
                        responses=str(patch_audit_responses),
                        out_report=str(out/'qgen_carrier_patch_audit_report.json'),
                        out_patches=str(audited_patches),
                        min_count=args.carrier_matrix_qgen_patch_min_count,
                        min_mean_delta=args.carrier_matrix_qgen_patch_min_mean_delta,
                        no_sign_agreement=False,
                        holdout_fraction=getattr(args, "carrier_matrix_qgen_patch_holdout_fraction", 0.0),
                        heldout_min_count=getattr(args, "carrier_matrix_qgen_patch_heldout_min_count", None),
                        heldout_min_mean_delta=getattr(args, "carrier_matrix_qgen_patch_heldout_min_mean_delta", None),
                        require_heldout=getattr(args, "carrier_matrix_qgen_patch_require_heldout", False),
                    ))
                    patch_path_for_merge = audited_patches
            cmd_carrier_matrix_merge_patches(argparse.Namespace(matrix=str(carrier_matrix_path), patches=str(patch_path_for_merge), out=str(carrier_matrix_merged_path), patch_weight=args.carrier_matrix_qgen_patch_weight, require_safe=args.carrier_matrix_qgen_require_safe, report_out=str(out/'qgen_carrier_patch_report.json')))
            matrix_for_actions = carrier_matrix_merged_path
        cmd_multi_carrier_report(argparse.Namespace(matrix=str(matrix_for_actions), defects=str(audit_dir/'defects.jsonl'), out=str(out/'multi_carrier_report.json')))
        if actions_for_coker:
            cmd_carrier_safe_actions(argparse.Namespace(actions=actions_for_coker, matrix=str(matrix_for_actions), out=str(out/'carrier_safe_actions.jsonl'), budget=args.carrier_matrix_budget, keep_unsafe=args.carrier_matrix_keep_unsafe))
    carrier_accept_path=None; carrier_accept_summary_path=None
    if args.carrier_accept:
        carrier_accept_path=out/'carrier_acceptance.jsonl'
        cmd_carrier_accept(argparse.Namespace(tasks=tasks_for_pipeline,proposals=str(out/'carrier_generated_contexts.jsonl'),out=str(carrier_accept_path),margin_threshold=args.carrier_accept_margin,cost_weight=args.carrier_accept_cost_weight,lean_cmd=args.lean_cmd,workdir=args.workdir,timeout_s=args.timeout_s,dry_run=args.dry_run,keep_files=args.keep_files,cache_dir=args.cache_dir or str(out/'cache'),trace_state=args.trace_state,import_mode=args.import_mode,max_actions=args.carrier_accept_max_actions))
        carrier_accept_summary_path=out/'carrier_acceptance_summary.json'
        cmd_carrier_accept_summary(argparse.Namespace(accepted=str(carrier_accept_path),out=str(carrier_accept_summary_path)))
        if args.promote_carrier_actions:
            cmd_accepted_carrier_actions(argparse.Namespace(accepted=str(carrier_accept_path),out=str(out/'carrier_promoted_actions.jsonl'),min_margin=args.promote_carrier_min_margin,include_rejected=False))
    qgen_acceptance_lineage_path = None
    if qgen_dir:
        accepted_paths = []
        for pth in [qgen_audited_accepted_actions_path, qgen_robust_accepted_actions_path, qgen_registry_accepted_path, locals().get('qgen_registry_robust_accepted_path')]:
            if pth and Path(pth).exists():
                accepted_paths.append(pth)
        row_paths = []
        for pth in [out/'qgen_acceptance_rows.jsonl', out/'qgen_robust_acceptance_rows.jsonl', out/'qgen_registry_acceptance_rows.jsonl', out/'qgen_registry_robust_acceptance_rows.jsonl']:
            if Path(pth).exists():
                row_paths.append(pth)
        audit_paths = []
        for pth in [qgen_audit_dir/'responses.jsonl' if qgen_audit_dir else None, qgen_registry_audit_dir/'responses.jsonl' if qgen_registry_audit_dir else None]:
            if pth and Path(pth).exists():
                audit_paths.append(pth)
        registry_paths = []
        if qgen_registry_candidates_path and Path(qgen_registry_candidates_path).exists():
            registry_paths.append(qgen_registry_candidates_path)
        qgen_acceptance_lineage_path = out/'qgen_acceptance_lineage.json'
        build_qgen_acceptance_lineage(qgen_dir, accepted_actions=accepted_paths, acceptance_rows=row_paths, audit_responses=audit_paths, registry_candidates=registry_paths, out=qgen_acceptance_lineage_path)
    transitions_path=out/'transitions.jsonl'
    cmd_make_transitions(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(transitions_path)))
    gamma_path=out/'gamma_audit.jsonl'
    cmd_gamma_audit(argparse.Namespace(transitions=str(transitions_path),out=str(gamma_path),fit_gamma=args.fit_gamma,ridge=1e-3,horizon=args.gamma_horizon,include_gamma_matrix=False))
    gamma_transition_dir = None
    gamma_transition_report_path = None
    gamma_transition_actions_path = None
    gamma_transition_patches_path = None
    gamma_transition_patched_action_geometry_path = None
    if getattr(args, 'gamma_transition_learner', False):
        gamma_transition_dir = out / 'gamma_transition'
        teacher_constraints = None
        if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl').exists():
            teacher_constraints = arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl'
        learn_gamma_transition_model(
            transitions_path,
            gamma_transition_dir,
            actions_path=args.actions,
            teacher_constraints_path=teacher_constraints,
            ridge=getattr(args, 'gamma_transition_ridge', 1e-3),
            shrink=getattr(args, 'gamma_transition_shrink', 4.0),
            min_count=getattr(args, 'gamma_transition_min_count', 2),
            holdout_fraction=getattr(args, 'gamma_transition_holdout_fraction', 0.25),
            teacher_weight=getattr(args, 'gamma_transition_teacher_weight', 0.25),
            include_matrices=getattr(args, 'gamma_transition_include_matrices', False),
        )
        gamma_transition_report_path = gamma_transition_dir / 'gamma_transition_report.json'
        gamma_transition_actions_path = gamma_transition_dir / 'gamma_transition_actions.jsonl'
        gamma_transition_patches_path = gamma_transition_dir / 'gamma_transition_action_geometry_patches.jsonl'
        if getattr(args, 'gamma_transition_patch_action_geometry', False) and action_geometry_registry_path and Path(action_geometry_registry_path).exists() and gamma_transition_patches_path.exists():
            gamma_transition_patched_action_geometry_path = gamma_transition_dir / 'action_geometry_gamma_patched.jsonl'
            merge_gamma_transition_patches_into_action_geometry(
                action_geometry_registry_path,
                gamma_transition_patches_path,
                gamma_transition_patched_action_geometry_path,
                summary_out=gamma_transition_dir / 'action_geometry_gamma_patch_report.json',
            )
    rep=write_run_report(audit_dir,out/'pipeline_report.json')
    rep['pipeline_files']={
        'audit_dir':str(audit_dir),'frontier_summary':frontier_summary,'response_model':str(out/'response_model.json'),'response_eval_summary':str(out/'response_eval_summary.json') if getattr(args, 'eval_response_model', False) else None,'response_eval_rows':str(out/'response_eval_rows.jsonl') if getattr(args, 'eval_response_model', False) else None,'components':str(out/'response_components.jsonl'),
        'states_ir':str(states_ir_path),'ir_defects':str(out/'ir_defects.jsonl'),'exposure_report':str(exposure_report_path),'action_report':str(out/'action_report.json'),'action_report_csv':str(out/'action_report.csv'),
        'arithmetic_teacher_dir': str(arithmetic_teacher_dir) if arithmetic_teacher_dir else None,
        'arithmetic_teacher_actions': str(arithmetic_teacher_actions_path) if arithmetic_teacher_actions_path else None,
        'arithmetic_teacher_audit_dir': str(arithmetic_teacher_audit_dir) if arithmetic_teacher_audit_dir else None,
        'arithmetic_teacher_audit_report': str(arithmetic_teacher_audit_report_path) if arithmetic_teacher_audit_report_path else None,
        'arithmetic_teacher_kernel_audit_dir': str(arithmetic_teacher_dir / 'kernel_transition_audit') if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'kernel_transition_audit').exists() else None,
        'arithmetic_teacher_cocycle_dir': str(arithmetic_teacher_dir / 'cocycle_audit') if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit').exists() else None,
        'contextual_congruence_dir': str(contextual_congruence_dir) if contextual_congruence_dir else None,
        'contextual_congruence_report': str(contextual_congruence_report_path) if contextual_congruence_report_path else None,
        'contextual_congruence_classes': str(contextual_congruence_classes_path) if contextual_congruence_classes_path else None,
        'contextual_congruence_representatives': str(contextual_congruence_representatives_path) if contextual_congruence_representatives_path else None,
        'contextual_probe_dir': str(contextual_probe_dir) if contextual_probe_dir else None,
        'contextual_probe_candidates': str(contextual_probe_candidates_path) if contextual_probe_candidates_path else None,
        'contextual_probe_audit_dir': str(contextual_probe_audit_dir) if contextual_probe_audit_dir else None,
        'contextual_probe_accepted_actions': str(contextual_probe_accepted_actions_path) if contextual_probe_accepted_actions_path else None,
        'contextual_probe_robust_accepted_actions': str(contextual_probe_robust_accepted_actions_path) if contextual_probe_robust_accepted_actions_path else None,
        'contextual_probe_congruence_dir': str(contextual_probe_congruence_dir) if contextual_probe_congruence_dir else None,
        'contextual_probe_report': str(contextual_probe_report_path) if contextual_probe_report_path else None,
        'source_budget_dir': str(source_budget_dir) if locals().get('source_budget_dir') else None,
        'source_budget_actions': str(source_budget_actions_path) if locals().get('source_budget_actions_path') else None,
        'source_budget_report': str(source_budget_report_path) if locals().get('source_budget_report_path') else None,
        'source_budget_audit_dir': str(source_budget_audit_dir) if locals().get('source_budget_audit_dir') else None,
        'source_budget_action_report': str(out/'source_budget_action_report.json') if locals().get('source_budget_audit_dir') else None,
        'crg_dir': str(crg_dir) if locals().get('crg_dir') else None,
        'crg_response_completion': str(crg_response_completion_path) if locals().get('crg_response_completion_path') else None,
        'crg_repair_species_registry': str(crg_registry_path) if locals().get('crg_registry_path') else None,
        'crg_problems': str(crg_problems_path) if locals().get('crg_problems_path') else None,
        'crg_relaxed_candidates': str(crg_relaxed_candidates_path) if locals().get('crg_relaxed_candidates_path') else None,
        'crg_hardening_attempts': str(crg_hardening_attempts_path) if locals().get('crg_hardening_attempts_path') else None,
        'crg_hard_candidates': str(crg_hard_candidates_path) if locals().get('crg_hard_candidates_path') else None,
        'crg_candidate_audit_dir': str(crg_candidate_audit_dir) if locals().get('crg_candidate_audit_dir') else None,
        'crg_candidate_audit_responses': str(crg_candidate_audit_dir / 'responses.jsonl') if locals().get('crg_candidate_audit_dir') else None,
        'crg_audit_rows': str(crg_audit_rows_path) if locals().get('crg_audit_rows_path') else None,
        'crg_hardening_gap_report': str(crg_gap_report_path) if locals().get('crg_gap_report_path') else None,
        'crg_poms_evidence': str(crg_poms_evidence_path) if locals().get('crg_poms_evidence_path') else None,
        'crg_robust_acceptance_rows': str(crg_robust_acceptance_rows_path) if locals().get('crg_robust_acceptance_rows_path') else None,
        'crg_robust_acceptance_report': str(crg_robust_acceptance_report_path) if locals().get('crg_robust_acceptance_report_path') else None,
        'crg_robust_accepted_actions': str(crg_robust_accepted_actions_path) if locals().get('crg_robust_accepted_actions_path') else None,
        'repair_flow_steps': str(repair_flow_steps_path) if locals().get('repair_flow_steps_path') else None,
        'concept_geometry_dir': str(concept_geometry_dir) if locals().get('concept_geometry_dir') else None,
        'concept_points': str(concept_points_path) if locals().get('concept_points_path') else None,
        'concept_edges': str(concept_edges_path) if locals().get('concept_edges_path') else None,
        'concept_search_rows': str(concept_search_rows_path) if locals().get('concept_search_rows_path') else None,
        'concept_decoded_atoms': str(concept_decoded_atoms_path) if locals().get('concept_decoded_atoms_path') else None,
        'response_quotient_dir': str(response_quotient_dir) if response_quotient_dir else None,
        'response_quotient_registry': str(response_quotient_registry_path) if response_quotient_registry_path else None,
        'response_quotient_representatives': str(response_quotient_representatives_path) if response_quotient_representatives_path else None,
        'response_quotient_projected_actions': str(response_quotient_projected_actions_path) if response_quotient_projected_actions_path else None,
        'carrier_quotient_dir': str(carrier_quotient_dir) if carrier_quotient_dir else None,
        'carrier_quotient_candidates': str(carrier_quotient_candidates_path) if carrier_quotient_candidates_path else None,
        'carrier_quotient_defect_registry': str(carrier_quotient_registry_path) if carrier_quotient_registry_path else None,
        'carrier_quotient_incidence_patches': str(carrier_quotient_patch_path) if carrier_quotient_patch_path else None,
        'carrier_quotient_audit_dir': str(carrier_quotient_audit_dir) if carrier_quotient_audit_dir else None,
        'carrier_quotient_accepted_actions': str(carrier_quotient_accepted_actions_path) if carrier_quotient_accepted_actions_path else None,
        'carrier_quotient_robust_accepted_actions': str(carrier_quotient_robust_accepted_actions_path) if carrier_quotient_robust_accepted_actions_path else None,
        'qgen_dir':str(qgen_dir) if qgen_dir else None,'qgen_context_candidates':str(qgen_context_candidates_path) if qgen_context_candidates_path else None,'qgen_accepted_actions':str(qgen_accepted_actions_path) if qgen_accepted_actions_path else None,'qgen_defect_registry':str(qgen_defect_registry_path) if qgen_defect_registry_path else None,'qgen_carrier_incidence':str(qgen_carrier_incidence_path) if qgen_carrier_incidence_path else None,'qgen_failure_signatures':str(qgen_failure_signatures_path) if qgen_failure_signatures_path else None,'qgen_lineage':str(qgen_lineage_path) if qgen_lineage_path else None,'qgen_registry_candidates':str(qgen_registry_candidates_path) if qgen_registry_candidates_path else None,'qgen_registry_audit_dir':str(qgen_registry_audit_dir) if qgen_registry_audit_dir else None,'qgen_registry_accepted_actions':str(qgen_registry_accepted_path) if qgen_registry_accepted_path else None,'qgen_audit_dir':str(qgen_audit_dir) if qgen_audit_dir else None,'qgen_action_report':str(out/'qgen_action_report.json') if qgen_audit_dir else None,'qgen_audited_accepted_actions':str(qgen_audited_accepted_actions_path) if qgen_audited_accepted_actions_path else None,'qgen_acceptance_report':str(qgen_acceptance_report_path) if qgen_acceptance_report_path else None,'qgen_robust_accepted_actions':str(qgen_robust_accepted_actions_path) if qgen_robust_accepted_actions_path else None,'qgen_robust_acceptance_report':str(qgen_robust_acceptance_report_path) if qgen_robust_acceptance_report_path else None,'qgen_robust_acceptance_rows':str(qgen_robust_acceptance_rows_path) if qgen_robust_acceptance_rows_path else None,'qgen_acceptance_lineage':str(qgen_acceptance_lineage_path) if qgen_acceptance_lineage_path else None,
        'quotient_coordinate_dir': str(quotient_coordinate_dir) if quotient_coordinate_dir else None,
        'quotient_coordinate_candidates': str(quotient_coordinate_candidates_path) if quotient_coordinate_candidates_path else None,
        'quotient_coordinate_defect_registry': str(quotient_coordinate_registry_path) if quotient_coordinate_registry_path else None,
        'quotient_coordinate_registry_candidates': str(quotient_coordinate_registry_candidates_path) if quotient_coordinate_registry_candidates_path else None,
        'quotient_coordinate_audit_dir': str(quotient_coordinate_audit_dir) if quotient_coordinate_audit_dir else None,
        'quotient_coordinate_accepted_actions': str(quotient_coordinate_accepted_actions_path) if quotient_coordinate_accepted_actions_path else None,
        'quotient_coordinate_robust_accepted_actions': str(quotient_coordinate_robust_accepted_actions_path) if quotient_coordinate_robust_accepted_actions_path else None,
        'action_geometry_dir': str(action_geometry_dir) if action_geometry_dir else None,
        'action_geometry_registry': str(action_geometry_registry_path) if action_geometry_registry_path else None,
        'action_geometry_candidates': str(action_geometry_candidates_path) if action_geometry_candidates_path else None,
        'action_geometry_audit_dir': str(action_geometry_audit_dir) if action_geometry_audit_dir else None,
        'action_geometry_action_report': str(out/'action_geometry_action_report.json') if action_geometry_audit_dir else None,
        'action_geometry_accepted_actions': str(action_geometry_accepted_actions_path) if action_geometry_accepted_actions_path else None,
        'action_geometry_robust_accepted_actions': str(action_geometry_robust_accepted_actions_path) if action_geometry_robust_accepted_actions_path else None,
        'action_geometry_acceptance_report': str(action_geometry_acceptance_report_path) if action_geometry_acceptance_report_path else None,
        'action_geometry_robust_acceptance_report': str(action_geometry_robust_acceptance_report_path) if action_geometry_robust_acceptance_report_path else None,
        'quotient_coordinate_dir': str(quotient_coordinate_dir) if quotient_coordinate_dir else None,
        'quotient_coordinate_candidates': str(quotient_coordinate_candidates_path) if quotient_coordinate_candidates_path else None,
        'quotient_coordinate_defect_registry': str(quotient_coordinate_registry_path) if quotient_coordinate_registry_path else None,
        'quotient_coordinate_registry_candidates': str(quotient_coordinate_registry_candidates_path) if quotient_coordinate_registry_candidates_path else None,
        'quotient_coordinate_audit_dir': str(quotient_coordinate_audit_dir) if quotient_coordinate_audit_dir else None,
        'quotient_coordinate_accepted_actions': str(quotient_coordinate_accepted_actions_path) if quotient_coordinate_accepted_actions_path else None,
        'quotient_coordinate_robust_accepted_actions': str(quotient_coordinate_robust_accepted_actions_path) if quotient_coordinate_robust_accepted_actions_path else None,
        'quotient_coordinate_validation_report': str(quotient_coordinate_validation_report_path) if quotient_coordinate_validation_report_path and Path(quotient_coordinate_validation_report_path).exists() else None,
        'quotient_coordinate_response_normal': str(quotient_coordinate_response_normal_path) if quotient_coordinate_response_normal_path else None,
        'failure_signatures':str(failure_signatures_path) if failure_signatures_path else None,'failure_signature_actions':str(failure_signature_actions_path) if failure_signature_actions_path else None,'failure_signature_audit_dir':str(failure_signature_audit_dir) if failure_signature_audit_dir else None,'failure_signature_acceptance_report':str(out/'failure_signature_acceptance_report.json') if failure_signature_audit_dir and getattr(args, 'failure_signature_accept_coker', False) else None,'exposure_audit_report':str(out/'exposure_audit_report.json') if getattr(args, 'audit_exposures', False) else None,
        'defect_registry':str(registry_path) if registry_path else None,'promoted_registry':str(promoted_registry_path) if promoted_registry_path else None,
        'auto_defects':str(out/'auto_defects.jsonl') if registry_path else None,'registry_candidates':str(registry_candidates_path) if registry_candidates_path else None,
        'registry_audit_dir':str(out/'registry_audit') if (registry_candidates_path is not None and args.audit_registry_candidates) else None,
        'registry_acceptance_report':str(out/'registry_acceptance_report.json') if (registry_candidates_path is not None and args.registry_accept_coker) else None,'registry_action_report':str(out/'registry_action_report.json') if (registry_candidates_path is not None and args.audit_registry_candidates) else None,
        'premise_index':str(premise_index_path) if premise_index_path else None,'premise_candidates':str(premise_candidates_path) if premise_candidates_path else None,'premise_audit_dir':str(premise_audit_dir) if premise_audit_dir else None,'premise_action_report':str(out/'premise_action_report.json') if premise_audit_dir else None,
        'premise_contextual_dir': str(premise_contextual_dir) if locals().get('premise_contextual_dir') else None,
        'premise_use_rows': str(premise_use_rows_path) if locals().get('premise_use_rows_path') else None,
        'separator_contexts': str(separator_contexts_path) if locals().get('separator_contexts_path') else None,
        'premise_contextual_candidates': str(premise_contextual_candidates_path) if locals().get('premise_contextual_candidates_path') else None,
        'premise_contextual_scheduled_actions': str(premise_contextual_scheduled_path) if locals().get('premise_contextual_scheduled_path') else None,
        'premise_contextual_audit_dir': str(premise_contextual_audit_dir) if locals().get('premise_contextual_audit_dir') else None,
        'premise_contextual_kernel_context_cache': str(premise_contextual_audit_dir/'kernel_context_state_cache.jsonl') if locals().get('premise_contextual_audit_dir') and (premise_contextual_audit_dir/'kernel_context_state_cache.jsonl').exists() else None,
        'premise_contextual_plan_transitions': str(premise_contextual_audit_dir/'contextual_plan_transitions.jsonl') if locals().get('premise_contextual_audit_dir') and (premise_contextual_audit_dir/'contextual_plan_transitions.jsonl').exists() else None,
        'premise_contextual_plan_audit_report': str(premise_contextual_audit_dir/'contextual_plan_audit_report.json') if locals().get('premise_contextual_audit_dir') and (premise_contextual_audit_dir/'contextual_plan_audit_report.json').exists() else None,
        'premise_contextual_fingerprints': str(premise_contextual_fingerprints_path) if locals().get('premise_contextual_fingerprints_path') else None,
        'premise_contextual_classes': str(premise_contextual_classes_path) if locals().get('premise_contextual_classes_path') else None,
        'premise_contextual_validation': str(premise_contextual_dir/'premise_quotient_validation_rows.jsonl') if locals().get('premise_contextual_dir') else None,
        'premise_contextual_repair_faces': str(repair_face_ledger_path) if locals().get('repair_face_ledger_path') else None,
        'premise_contextual_face_taxonomy_dir': str(face_taxonomy_dir) if locals().get('face_taxonomy_dir') else None,
        'premise_contextual_dual_face_taxonomy': str(face_taxonomy_path) if locals().get('face_taxonomy_path') else None,
        'premise_contextual_face_concept_lattice': str(face_taxonomy_dir/'face_concept_lattice.jsonl') if locals().get('face_taxonomy_dir') else None,
        'premise_contextual_row_face_memberships': str(face_taxonomy_dir/'row_face_memberships.jsonl') if locals().get('face_taxonomy_dir') else None,
        'premise_contextual_retrieval_allowed_faces': str(face_taxonomy_dir/'retrieval_allowed_faces.jsonl') if locals().get('face_taxonomy_dir') else None,
        'premise_contextual_obstruction_tower_dir': str(obstruction_tower_dir) if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_objects': str(obstruction_tower_dir/'tower_objects.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_transcripts': str(obstruction_tower_dir/'tower_transcripts.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_faces': str(obstruction_tower_dir/'tower_faces.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_dual_components': str(obstruction_tower_dir/'tower_dual_components.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_boundaries': str(obstruction_tower_dir/'tower_boundaries.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_promotions': str(obstruction_tower_dir/'tower_promotions.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_next_actions': str(obstruction_tower_dir/'tower_next_actions.jsonl') if locals().get('obstruction_tower_dir') else None,
        'premise_contextual_tower_retrieval_candidates': str(obstruction_tower_dir/'tower_retrieval_candidates.jsonl') if locals().get('obstruction_tower_dir') else None,
        'dost_audit_dir': str(dost_audit_dir) if locals().get('dost_audit_dir') else None,
        'dost_invariant_ledger': str(dost_audit_dir/'invariant_ledger.json') if locals().get('dost_audit_dir') else None,
        'dost_proof_blocker_report': str(dost_audit_dir/'proof_blocker_report.json') if locals().get('dost_audit_dir') else None,
        'dost_action_poverty_report': str(dost_audit_dir/'action_poverty_report.json') if locals().get('dost_audit_dir') else None,
        'dost_big_theorem_readiness': str(dost_audit_dir/'big_theorem_readiness.json') if locals().get('dost_audit_dir') else None,
        'dost_audit_dashboard': str(dost_audit_dir/'audit_dashboard.json') if locals().get('dost_audit_dir') else None,
        'dost_retrieval_safety_report': str(dost_audit_dir/'retrieval_safety_report.json') if locals().get('dost_audit_dir') else None,
        'dost_dir': str(dost_dir) if locals().get('dost_dir') else None,
        'primitive_observables': str(dost_dir/'primitive_observables.jsonl') if locals().get('dost_dir') else None,
        'bounded_transcripts': str(dost_dir/'bounded_transcripts.jsonl') if locals().get('dost_dir') else None,
        'feature_closure': str(dost_feature_closure_path) if locals().get('dost_feature_closure_path') else None,
        'bounded_feature_transcripts': str(dost_feature_values_path) if locals().get('dost_feature_values_path') else None,
        'selected_features': str(dost_selected_features_path) if locals().get('dost_selected_features_path') else None,
        'feature_selection_report': str(dost_dir/'feature_selection_report.json') if locals().get('dost_dir') else None,
        'auto_plan': str(dost_auto_plan_path) if locals().get('dost_auto_plan_path') else None,
        'compiled_experiment': str(dost_dir/'compiled_experiment.sh') if locals().get('dost_dir') else None,
        'compiled_notebook_cells': str(dost_dir/'compiled_notebook_cells.ipynb') if locals().get('dost_dir') else None,
        'premise_quotient_retrieved': str(premise_quotient_retrieved_path) if locals().get('premise_quotient_retrieved_path') else None,
        'premise_quotient_actions': str(premise_quotient_actions_path) if locals().get('premise_quotient_actions_path') else None,
        'carrier_generated':str(out/'carrier_generated_contexts.jsonl'),'carrier_actions':str(carrier_actions_path),'carrier_coker':str(out/'carrier_coker.jsonl'),
        'carrier_acceptance':str(carrier_accept_path) if carrier_accept_path else None,'carrier_acceptance_summary':str(carrier_accept_summary_path) if carrier_accept_summary_path else None,
        'ir_candidates': str(out/'ir_candidates.jsonl') if getattr(args, 'ir_candidates', False) else None,
        'ir_audit_dir': str(out/'ir_audit') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_action_report': str(out/'ir_action_report.json') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_acceptance_report': str(out/'ir_acceptance_report.json') if getattr(args, 'ir_accept_coker', False) else None,
        'ir_audit_dir': str(out/'ir_audit') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_action_report': str(out/'ir_action_report.json') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_acceptance_report': str(out/'ir_acceptance_report.json') if getattr(args, 'ir_accept_coker', False) else None,
        'ir_accepted_actions': str(out/'ir_accepted_actions.jsonl') if getattr(args, 'ir_accept_coker', False) else None,
        'carrier_matrix': str(out/'carrier_matrix.json') if getattr(args, 'carrier_matrix', False) else None,
        'carrier_matrix_qgen': str(out/'carrier_matrix_qgen.json') if (getattr(args, 'carrier_matrix', False) and getattr(args, 'carrier_matrix_merge_qgen', False)) else None,
        'qgen_carrier_patch_report': str(out/'qgen_carrier_patch_report.json') if (getattr(args, 'carrier_matrix', False) and getattr(args, 'carrier_matrix_merge_qgen', False)) else None,
        'qgen_carrier_patch_audit_report': str(out/'qgen_carrier_patch_audit_report.json') if (getattr(args, 'carrier_matrix_qgen_audit_patches', False)) else None,
        'qgen_carrier_incidence_audited': str(out/'qgen_carrier_incidence_audited.jsonl') if (getattr(args, 'carrier_matrix_qgen_audit_patches', False)) else None,
        'multi_carrier_report': str(out/'multi_carrier_report.json') if getattr(args, 'carrier_matrix', False) else None,
        'carrier_safe_actions': str(out/'carrier_safe_actions.jsonl') if getattr(args, 'carrier_matrix', False) else None,
        'transitions':str(transitions_path),'gamma_audit':str(gamma_path),
        'gamma_transition_dir': str(gamma_transition_dir) if gamma_transition_dir else None,
        'gamma_transition_report': str(gamma_transition_report_path) if gamma_transition_report_path else None,
        'gamma_transition_actions': str(gamma_transition_actions_path) if gamma_transition_actions_path else None,
        'gamma_transition_action_geometry_patches': str(gamma_transition_patches_path) if gamma_transition_patches_path else None,
        'gamma_transition_patched_action_geometry': str(gamma_transition_patched_action_geometry_path) if gamma_transition_patched_action_geometry_path else None,
    }
    if getattr(args, 'audit_queue', False):
        rep['pipeline_files']['audit_queue_db'] = str(Path(getattr(args, 'audit_db_path', None) or (audit_dir / 'audit_queue.sqlite')))
        rep['pipeline_files']['audit_queue_summary'] = str(audit_dir / 'summary.json')
        rep['pipeline_files']['audit_queue_server_summary'] = str(audit_dir / 'server_summary.json')
        rep['pipeline_files']['audit_env_profile'] = str(audit_dir / 'audit_env_profile.json') if (audit_dir / 'audit_env_profile.json').exists() else None
        rep['pipeline_files']['audit_cache_db'] = str(Path(getattr(args, 'audit_cache_db', None) or (Path.cwd() / '.lean_rgc' / 'audit_cache.sqlite'))) if getattr(args, 'audit_cache', False) else None
        rep['pipeline_files']['audit_prune_report'] = str(audit_dir / 'audit_prune_report.json') if (audit_dir / 'audit_prune_report.json').exists() else None
    # Stage ladder summarizes whether registry/IR/premise/carrier generated charts improve over the base audit.
    try:
        stage_paths = default_pipeline_stages(out)
        if stage_paths:
            write_stage_report(stage_paths, out/'stage_report.json', out/'stage_report.csv')
            rep['pipeline_files']['stage_report'] = str(out/'stage_report.json')
            rep['pipeline_files']['stage_report_csv'] = str(out/'stage_report.csv')
            if getattr(args, 'stage_coker', False):
                stage_args = [f"{name}={path}" for name, path in stage_paths if name != 'base']
                if stage_args:
                    stage_coker_rep = run_stage_coker(
                        audit_dir/'responses.jsonl',
                        stage_args,
                        out_report=out/'stage_coker_report.json',
                        out_actions=out/'stage_coker_accepted_actions.jsonl',
                        out_rows_dir=out/'stage_coker_rows',
                        out_csv=out/'stage_coker_report.csv',
                        margin_threshold=args.stage_coker_margin,
                        cost_weight=args.stage_coker_cost_weight,
                        carrier_weight=args.stage_coker_carrier_weight,
                        max_actions=args.stage_coker_max_actions,
                    )
                    rep['pipeline_files']['stage_coker_report'] = str(out/'stage_coker_report.json')
                    rep['pipeline_files']['stage_coker_actions'] = str(out/'stage_coker_accepted_actions.jsonl')
    except Exception as e:
        rep.setdefault('warnings', []).append({'stage_report_error': str(e)})
    if getattr(args, 'audit_db', False):
        try:
            db_path = Path(args.audit_db_path) if getattr(args, 'audit_db_path', None) else (out / 'audit.db')
            db_summary = build_audit_db(out, db_path, reset=(not getattr(args, 'audit_db_append', False) and not getattr(args, 'audit_queue', False)))
            rep['pipeline_files']['audit_db'] = str(db_path)
            rep['pipeline_files']['audit_db_summary'] = str(Path(db_path).parent / 'audit_db_summary.json')
            rep['audit_db_summary'] = db_summary
        except Exception as e:
            rep.setdefault('warnings', []).append({'audit_db_error': str(e)})
    if getattr(args, 'run_db', False):
        try:
            # Persist the current report before importing artifacts so the DB can index it too.
            (out/'pipeline_report.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
            (out/'pipeline_summary.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
            run_db_path = Path(getattr(args, 'run_db_path', None) or (out / 'runs.db'))
            run_db_summary = build_run_db(
                out,
                run_db_path,
                append=getattr(args, 'run_db_append', False),
                artifact_store_root=getattr(args, 'artifact_store_root', None),
                import_artifacts=bool(getattr(args, 'db_import_artifacts', False) or getattr(args, 'run_db', False)),
                materialize_lineage=bool(getattr(args, 'db_materialize_lineage', False) or getattr(args, 'run_db', False)),
                run_id=pipeline_run_id,
                config=vars(args),
            )
            rep['pipeline_files']['run_db'] = str(run_db_path)
            rep['pipeline_files']['run_db_summary'] = str(run_db_path.parent / 'run_db_summary.json')
            rep['run_db_summary'] = run_db_summary
        except Exception as e:
            rep.setdefault('warnings', []).append({'run_db_error': str(e)})
    (out/'pipeline_report.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'pipeline_summary.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
    return rep


__all__ = [
    "PipelineConfig",
    "make_pipeline_run_id",
    "normalize_pipeline_args",
    "run_basic_pipeline",
    "run_pipeline",
]

