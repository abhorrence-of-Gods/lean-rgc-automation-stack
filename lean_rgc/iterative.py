from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json

from .schemas import read_jsonl, write_jsonl, TacticAction
from .cli import main as cli_main
from .realized_response import collect_qgen_realized_calibration
from .audit_db import build_audit_db
from .poms_status import collect_poms_status
from .poms_promotion import collect_poms_promotion
from .promotion_evidence import generate_promotion_evidence


@dataclass
class IterationRoundSummary:
    round: int
    out_dir: str
    actions_in: str | None
    actions_next: str | None
    n_actions_next: int
    audit_success_rate: float | None = None
    audit_n: int | None = None
    registry_accepted: int | None = None
    carrier_promoted: int | None = None
    premise_actions: int | None = None
    frontier_tasks: int | None = None
    frontier_closed: int | None = None
    gamma_vs_persistence: float | None = None
    gamma_cocycle_rel: float | None = None
    mean_goal_response: float | None = None
    mean_carrier_delta: float | None = None
    qgen_contexts: int | None = None
    qgen_accepted: int | None = None
    qgen_defects: int | None = None
    qgen_carriers: int | None = None
    qgen_failures: int | None = None
    action_geometry_candidates: int | None = None
    action_geometry_accepted: int | None = None
    contextual_probe_candidates: int | None = None
    contextual_probe_accepted: int | None = None
    carrier_quotient_candidates: int | None = None
    carrier_quotient_accepted: int | None = None
    merged_sources: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return len(read_jsonl(path))
    except Exception:
        return 0


def _action_key(row: dict[str, Any]) -> tuple[str, str]:
    task_id = str(row.get("task_id") or (row.get("metadata") or {}).get("task_id") or "")
    tactic = str(row.get("tactic") or row.get("full_tactic") or "")
    return task_id, tactic


def _normalize_action_row(row: dict[str, Any]) -> dict[str, Any] | None:
    row = dict(row)
    # Acceptance rows often wrap the action.
    if "tactic" not in row:
        action = row.get("action") if isinstance(row.get("action"), dict) else None
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        if action is None and isinstance(meta.get("action"), dict):
            action = meta.get("action")
        if action is not None:
            base = dict(action)
            if row.get("task_id"):
                base.setdefault("task_id", row.get("task_id"))
                base.setdefault("metadata", {})["task_id"] = row.get("task_id")
            row = base
    row.setdefault("metadata", {})
    if row.get("task_id") and not row["metadata"].get("task_id"):
        row["metadata"]["task_id"] = row.get("task_id")
    row.setdefault("action_id", row.get("id") or str(abs(hash(row.get("tactic", json.dumps(row, sort_keys=True))))))
    row.setdefault("tactic_class", row.get("class", "generated"))
    row.setdefault("carrier_tags", row.get("carrier_tags", []))
    row.setdefault("cost_estimate", row.get("cost", 1.0))
    if not row.get("tactic"):
        return None
    try:
        return TacticAction.from_dict(row).to_dict() | ({"task_id": row.get("task_id")} if row.get("task_id") else {})
    except Exception:
        return row


def _merge_actions(paths: Iterable[Path], out: Path, *, max_actions: int | None = None) -> dict[str, Any]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    sources: dict[str, int] = {}
    for p in paths:
        if not p or not p.exists():
            continue
        data = read_jsonl(p)
        sources[str(p)] = len(data)
        for r in data:
            nr = _normalize_action_row(r)
            if nr is None:
                continue
            key = _action_key(nr)
            if not key[1] or key in seen:
                continue
            seen.add(key)
            rows.append(nr)
            if max_actions is not None and len(rows) >= max_actions:
                break
        if max_actions is not None and len(rows) >= max_actions:
            break
    write_jsonl(out, rows)
    return {"out": str(out), "n_actions": len(rows), "sources": sources}


def _pipeline_args(
    *, tasks: str, action_path: str | None, rdir: Path, dry_run: bool, jobs: int, max_actions: int,
    lean_cmd: str, workdir: str | None, timeout_s: float, import_mode: str, flush_every: int,
    candidate_mode: str, audit_mode: str, bulk_batch_size: int, cache_dir: str | None,
    server_cmd: str | None = None, server_backend: str = "auto", server_no_fallback: bool = False,
    native_exec_mode: str = "source_check",
    resume: bool, fit_gamma: bool, frontier_normalize: bool, frontier_max_prefixes: int,
    frontier_include_identity: bool,
    registry_audit_max_actions: int, registry_accept_margin: float, registry_accept_max_per_task: int,
    promote_registry: bool, premise_index: bool, audit_premise_candidates: bool, premise_audit_max_actions: int,
    carrier_accept: bool, carrier_accept_max_actions: int, promote_carrier_actions: bool,
    ir_candidates: bool, ir_max_candidates: int, audit_ir_candidates: bool, ir_audit_max_actions: int,
    ir_accept_coker: bool, carrier_matrix: bool, carrier_matrix_budget: float,
    carrier_matrix_keep_unsafe: bool, carrier_matrix_merge_qgen: bool = False,
    carrier_matrix_qgen_patch_weight: float = 1.0, carrier_matrix_qgen_require_safe: bool = False,
    carrier_matrix_qgen_audit_patches: bool = False, carrier_matrix_qgen_patch_min_count: int = 1, carrier_matrix_qgen_patch_min_mean_delta: float = 0.0,
    carrier_matrix_qgen_patch_holdout_fraction: float = 0.0, carrier_matrix_qgen_patch_require_heldout: bool = False,
    qgen: bool = False, qgen_top_defects: int = 16, qgen_top_contexts: int = 32,
    qgen_top_carriers: int = 64, qgen_top_failures: int = 32, qgen_margin_threshold: float = 0.0,
    qgen_cost_weight: float = 0.05, qgen_carrier_weight: float = 0.25, qgen_audit_penalty: float = 1.0,
    audit_qgen_candidates: bool = False, qgen_audit_max_actions: int = 24,
    qgen_accept_coker: bool = False, qgen_accept_margin: float = 0.0,
    qgen_accept_max_per_task: int = 16, qgen_accept_cost_weight: float = 0.05,
    qgen_accept_carrier_weight: float = 0.7,
    qgen_robust_accept: bool = False, qgen_registry_robust_accept: bool = False,
    qgen_robust_coker_accept: bool = False, qgen_registry_robust_coker_accept: bool = False,
    qgen_robust_coker_holdout_fraction: float = 0.35, qgen_robust_coker_uncertainty_weight: float = 0.10,
    qgen_robust_coker_carrier_gain_weight: float = 0.25, qgen_robust_coker_audit_penalty: float = 1.0,
    qgen_robust_coker_require_success: bool = False,
    qgen_robust_z: float = 1.0, qgen_robust_min_repeats: int = 1,
    qgen_robust_min_success_rate: float = 1.0,
    qgen_registry_candidates: bool = False, qgen_registry_max_candidates: int = 64,
    audit_qgen_registry_candidates: bool = False, qgen_registry_audit_max_actions: int = 16,
    qgen_registry_accept_coker: bool = False, qgen_registry_accept_margin: float = 0.0,
    qgen_registry_accept_max_per_task: int = 16, qgen_registry_accept_cost_weight: float = 0.05,
    qgen_registry_accept_carrier_weight: float = 0.7,
    action_geometry: bool = False, action_geometry_retrieve: bool = False, action_geometry_use_qgen_normals: bool = False,
    action_geometry_use_gamma_transition: bool = False,
    audit_scheduler: bool = False, audit_scheduler_db: str | None = None, audit_scheduler_responses: str | None = None,
    audit_scheduler_lineage: list[str] | None = None, audit_scheduler_budget: int | None = None,
    audit_scheduler_per_task_cap: int | None = None, audit_scheduler_per_source_cap: int | None = None,
    audit_scheduler_coker_weight: float = 1.0, audit_scheduler_carrier_weight: float = 0.5,
    audit_scheduler_uncertainty_weight: float = 0.25, audit_scheduler_novelty_weight: float = 0.15,
    audit_scheduler_success_weight: float = 0.25, audit_scheduler_cost_weight: float = 0.10,
    audit_scheduler_timeout_weight: float = 0.50,
    source_budget: bool = False, audit_source_budget_candidates: bool = False,
    source_budget_merge_actions: bool = False, source_budget_merge_policy: str = 'scheduled-only',
    source_budget_budget: int | None = None, source_budget_min_per_source: int = 0,
    source_budget_max_per_source: int | None = None, source_budget_per_task_cap: int | None = None,
    source_budget_per_action_cap: int = 1, source_budget_allocation_mode: str = 'proportional',
    source_budget_coker_weight: float = 1.0, source_budget_carrier_weight: float = 0.5,
    source_budget_uncertainty_weight: float = 0.20, source_budget_novelty_weight: float = 0.25,
    source_budget_lineage_weight: float = 0.15, source_budget_success_weight: float = 0.25,
    source_budget_cost_weight: float = 0.10, source_budget_timeout_weight: float = 0.50,
    source_budget_gamma_aware: bool = False, source_budget_gamma_value_mode: str = 'finite_horizon',
    source_budget_gamma_horizon: int = 4, source_budget_gamma_discount: float = 1.0,
    source_budget_gamma_value_weight: float = 0.50, source_budget_gamma_tail_risk_weight: float = 0.25,
    source_budget_gamma_stability_delta: float = 0.05, source_budget_gamma_tail_risk_mode: str = 'spectral',
    action_geometry_top_k: int | None = 32, action_geometry_min_count: int = 1,
    action_geometry_tail_weight: float = 0.25, action_geometry_gamma_value_mode: str = "local",
    action_geometry_gamma_horizon: int = 4, action_geometry_gamma_discount: float = 1.0,
    action_geometry_gamma_stability_margin: float = 0.05, action_geometry_gamma_tail_value_weight: float = 1.0,
    action_geometry_gamma_tail_risk_mode: str = 'spectral',
    action_geometry_cost_weight: float = 0.05,
    action_geometry_uncertainty_weight: float = 0.10, action_geometry_audit_weight: float = 0.20,
    action_geometry_require_carrier_safe: bool = False, action_geometry_carrier_budget: float = 0.0,
    audit_action_geometry_candidates: bool = False, action_geometry_audit_max_actions: int = 24,
    action_geometry_accept_coker: bool = False, action_geometry_accept_margin: float = 0.0,
    action_geometry_accept_max_per_task: int = 16, action_geometry_accept_cost_weight: float = 0.05,
    action_geometry_accept_carrier_weight: float = 0.7, action_geometry_robust_coker_accept: bool = False,
    action_geometry_robust_coker_holdout_fraction: float = 0.35, action_geometry_robust_coker_uncertainty_weight: float = 0.10,
    action_geometry_robust_coker_carrier_gain_weight: float = 0.25, action_geometry_robust_coker_audit_penalty: float = 1.0,
    action_geometry_robust_coker_require_success: bool = False,
    quotient_coordinates: bool = False, quotient_coordinate_merge_actions: bool = False, quotient_coordinate_merge_policy: str = "robust-only",
    quotient_coordinate_ridge: float = 1e-4, quotient_coordinate_max_mass: float = 1.0,
    quotient_coordinate_cosine_threshold: float = 0.85, quotient_coordinate_min_states: int = 1,
    quotient_coordinate_top_action_scores: int = 128, quotient_coordinate_margin_threshold: float = 0.0,
    quotient_coordinate_validate: bool = False, quotient_coordinate_registry_candidates: bool = False,
    quotient_coordinate_registry_max_candidates: int = 64, audit_quotient_coordinate_candidates: bool = False,
    quotient_coordinate_audit_max_actions: int = 16, quotient_coordinate_accept_coker: bool = False,
    quotient_coordinate_robust_coker_accept: bool = False, quotient_coordinate_accept_margin: float = 0.0,
    quotient_coordinate_accept_max_per_task: int = 16, quotient_coordinate_accept_cost_weight: float = 0.05,
    quotient_coordinate_accept_carrier_weight: float = 0.7, quotient_coordinate_robust_coker_holdout_fraction: float = 0.35,
    quotient_coordinate_robust_coker_uncertainty_weight: float = 0.10, quotient_coordinate_robust_coker_carrier_gain_weight: float = 0.25,
    quotient_coordinate_robust_coker_audit_penalty: float = 1.0, quotient_coordinate_robust_coker_require_success: bool = False,
    carrier_quotient: bool = False, carrier_quotient_merge_actions: bool = False, carrier_quotient_merge_policy: str = "robust-only",
    carrier_quotient_ridge: float = 1e-4, carrier_quotient_max_mass: float = 1.0, carrier_quotient_cosine_threshold: float = 0.85,
    carrier_quotient_min_states: int = 1, carrier_quotient_top_action_scores: int = 128, carrier_quotient_margin_threshold: float = 0.0,
    audit_carrier_quotient_candidates: bool = False, carrier_quotient_audit_max_actions: int = 16, carrier_quotient_accept_coker: bool = False,
    carrier_quotient_robust_coker_accept: bool = False, carrier_quotient_accept_margin: float = 0.0, carrier_quotient_accept_max_per_task: int = 16,
    carrier_quotient_accept_cost_weight: float = 0.05, carrier_quotient_accept_carrier_weight: float = 0.7,
    carrier_quotient_robust_coker_holdout_fraction: float = 0.35, carrier_quotient_robust_coker_uncertainty_weight: float = 0.10,
    carrier_quotient_robust_coker_carrier_gain_weight: float = 0.25, carrier_quotient_robust_coker_audit_penalty: float = 1.0,
    carrier_quotient_robust_coker_require_success: bool = False,
    action_geometry_use_quotient_normals: bool = False,
    contextual_congruence: bool = False, contextual_congruence_context_mode: str = 'state',
    contextual_congruence_no_carrier: bool = False, contextual_congruence_min_count: int = 1,
    contextual_congruence_cosine_threshold: float = 0.95, contextual_congruence_distance_threshold: float = 0.25,
    contextual_congruence_min_context_jaccard: float = 0.0,
    contextual_probes: bool = False,
    contextual_probe_contexts: str | None = None,
    contextual_probe_max_left: int = 4,
    contextual_probe_max_right: int = 4,
    contextual_probe_max_core: int | None = None,
    contextual_probe_max_candidates: int | None = 128,
    contextual_probe_no_identity: bool = False,
    contextual_probe_no_left: bool = False,
    contextual_probe_no_right: bool = False,
    audit_contextual_probe_candidates: bool = False,
    contextual_probe_audit_max_actions: int = 24,
    contextual_probe_congruence: bool = False,
    contextual_probe_congruence_context_mode: str = 'state',
    contextual_probe_congruence_no_carrier: bool = False,
    contextual_probe_congruence_min_count: int = 1,
    contextual_probe_congruence_cosine_threshold: float = 0.95,
    contextual_probe_congruence_distance_threshold: float = 0.25,
    contextual_probe_congruence_min_context_jaccard: float = 0.0,
    contextual_probe_accept_coker: bool = False,
    contextual_probe_robust_coker_accept: bool = False,
    contextual_probe_accept_margin: float = 0.0,
    contextual_probe_accept_max_per_task: int = 16,
    contextual_probe_accept_cost_weight: float = 0.05,
    contextual_probe_accept_carrier_weight: float = 0.7,
    contextual_probe_robust_coker_holdout_fraction: float = 0.35,
    contextual_probe_robust_coker_uncertainty_weight: float = 0.10,
    contextual_probe_robust_coker_carrier_gain_weight: float = 0.25,
    contextual_probe_robust_coker_audit_penalty: float = 1.0,
    contextual_probe_robust_coker_require_success: bool = False,
    contextual_probe_merge_actions: bool = False,
    contextual_probe_merge_policy: str = 'robust-only',
    response_quotient_registry: bool = False,
    response_quotient_min_members: int = 1,
    response_quotient_min_quality: float | None = None,
    response_quotient_project_actions: bool = False,
    response_quotient_annotate_only: bool = False,
    response_quotient_merge_actions: bool = False,
    response_quotient_merge_policy: str = 'representatives',
    failure_signatures: bool = False, audit_failure_signature_candidates: bool = False,
    failure_signature_audit_max_actions: int = 16, failure_signature_accept_coker: bool = False,
    failure_signature_accept_margin: float = 0.0, failure_signature_accept_max_per_task: int = 16,
) -> list[str]:
    args = [
        "pipeline",
        "--tasks", tasks,
        "--out", str(rdir),
        "--jobs", str(jobs),
        "--audit-mode", audit_mode,
        "--bulk-batch-size", str(bulk_batch_size),
        "--max-actions", str(max_actions),
        "--candidate-mode", candidate_mode,
        "--lean-cmd", lean_cmd,
        "--timeout-s", str(timeout_s),
        "--import-mode", import_mode,
        "--flush-every", str(flush_every),
        "--mine-defects",
        "--registry-candidates",
        "--audit-registry-candidates",
        "--registry-audit-max-actions", str(registry_audit_max_actions),
        "--registry-accept-coker",
        "--registry-accept-margin", str(registry_accept_margin),
        "--registry-accept-max-per-task", str(registry_accept_max_per_task),
    ]
    if action_path:
        args += ["--actions", action_path]
    if dry_run:
        args += ["--dry-run"]
    if workdir:
        args += ["--workdir", workdir]
    if cache_dir:
        args += ["--cache-dir", str(Path(cache_dir) / rdir.name)]
    if server_cmd:
        args += ["--server-cmd", server_cmd]
    if server_backend and server_backend != "auto":
        args += ["--server-backend", server_backend]
    if server_no_fallback:
        args += ["--server-no-fallback"]
    if native_exec_mode:
        args += ["--native-exec-mode", native_exec_mode]
    if audit_scheduler:
        args += ["--audit-scheduler"]
        if audit_scheduler_db:
            args += ["--audit-scheduler-db", audit_scheduler_db]
        if audit_scheduler_responses:
            args += ["--audit-scheduler-responses", audit_scheduler_responses]
        for lp in (audit_scheduler_lineage or []):
            args += ["--audit-scheduler-lineage", lp]
        if audit_scheduler_budget is not None:
            args += ["--audit-scheduler-budget", str(audit_scheduler_budget)]
        if audit_scheduler_per_task_cap is not None:
            args += ["--audit-scheduler-per-task-cap", str(audit_scheduler_per_task_cap)]
        if audit_scheduler_per_source_cap is not None:
            args += ["--audit-scheduler-per-source-cap", str(audit_scheduler_per_source_cap)]
        args += ["--audit-scheduler-coker-weight", str(audit_scheduler_coker_weight)]
        args += ["--audit-scheduler-carrier-weight", str(audit_scheduler_carrier_weight)]
        args += ["--audit-scheduler-uncertainty-weight", str(audit_scheduler_uncertainty_weight)]
        args += ["--audit-scheduler-novelty-weight", str(audit_scheduler_novelty_weight)]
        args += ["--audit-scheduler-success-weight", str(audit_scheduler_success_weight)]
        args += ["--audit-scheduler-cost-weight", str(audit_scheduler_cost_weight)]
        args += ["--audit-scheduler-timeout-weight", str(audit_scheduler_timeout_weight)]
    if source_budget:
        args += ["--source-budget"]
    if audit_source_budget_candidates:
        args += ["--audit-source-budget-candidates"]
    if source_budget_budget is not None:
        args += ["--source-budget-budget", str(source_budget_budget)]
    args += ["--source-budget-min-per-source", str(source_budget_min_per_source)]
    if source_budget_max_per_source is not None:
        args += ["--source-budget-max-per-source", str(source_budget_max_per_source)]
    if source_budget_per_task_cap is not None:
        args += ["--source-budget-per-task-cap", str(source_budget_per_task_cap)]
    args += ["--source-budget-per-action-cap", str(source_budget_per_action_cap)]
    args += ["--source-budget-allocation-mode", str(source_budget_allocation_mode)]
    args += ["--source-budget-coker-weight", str(source_budget_coker_weight)]
    args += ["--source-budget-carrier-weight", str(source_budget_carrier_weight)]
    args += ["--source-budget-uncertainty-weight", str(source_budget_uncertainty_weight)]
    args += ["--source-budget-novelty-weight", str(source_budget_novelty_weight)]
    args += ["--source-budget-lineage-weight", str(source_budget_lineage_weight)]
    args += ["--source-budget-success-weight", str(source_budget_success_weight)]
    args += ["--source-budget-cost-weight", str(source_budget_cost_weight)]
    args += ["--source-budget-timeout-weight", str(source_budget_timeout_weight)]
    if source_budget_gamma_aware:
        args += ["--source-budget-gamma-aware"]
    args += ["--source-budget-gamma-value-mode", str(source_budget_gamma_value_mode)]
    args += ["--source-budget-gamma-horizon", str(source_budget_gamma_horizon)]
    args += ["--source-budget-gamma-discount", str(source_budget_gamma_discount)]
    args += ["--source-budget-gamma-value-weight", str(source_budget_gamma_value_weight)]
    args += ["--source-budget-gamma-tail-risk-weight", str(source_budget_gamma_tail_risk_weight)]
    args += ["--source-budget-gamma-stability-delta", str(source_budget_gamma_stability_delta)]
    args += ["--source-budget-gamma-tail-risk-mode", str(source_budget_gamma_tail_risk_mode)]
    if resume:
        args += ["--resume"]
    if fit_gamma:
        args += ["--fit-gamma"]
    if qgen:
        args += ["--qgen", "--qgen-top-defects", str(qgen_top_defects), "--qgen-top-contexts", str(qgen_top_contexts), "--qgen-top-carriers", str(qgen_top_carriers), "--qgen-top-failures", str(qgen_top_failures), "--qgen-margin-threshold", str(qgen_margin_threshold), "--qgen-cost-weight", str(qgen_cost_weight), "--qgen-carrier-weight", str(qgen_carrier_weight), "--qgen-audit-penalty", str(qgen_audit_penalty)]
        if audit_qgen_candidates:
            args += ["--audit-qgen-candidates", "--qgen-audit-max-actions", str(qgen_audit_max_actions)]
        if qgen_accept_coker:
            args += ["--qgen-accept-coker", "--qgen-accept-margin", str(qgen_accept_margin), "--qgen-accept-max-per-task", str(qgen_accept_max_per_task), "--qgen-accept-cost-weight", str(qgen_accept_cost_weight), "--qgen-accept-carrier-weight", str(qgen_accept_carrier_weight)]
            if qgen_robust_coker_accept:
                args += ["--qgen-robust-coker-accept", "--qgen-robust-coker-holdout-fraction", str(qgen_robust_coker_holdout_fraction), "--qgen-robust-coker-uncertainty-weight", str(qgen_robust_coker_uncertainty_weight), "--qgen-robust-coker-carrier-gain-weight", str(qgen_robust_coker_carrier_gain_weight), "--qgen-robust-coker-audit-penalty", str(qgen_robust_coker_audit_penalty)]
                if qgen_robust_coker_require_success:
                    args += ["--qgen-robust-coker-require-success"]
            elif qgen_robust_accept:
                args += ["--qgen-robust-accept", "--qgen-robust-z", str(qgen_robust_z), "--qgen-robust-min-repeats", str(qgen_robust_min_repeats), "--qgen-robust-min-success-rate", str(qgen_robust_min_success_rate)]
        if qgen_registry_candidates:
            args += ["--qgen-registry-candidates", "--qgen-registry-max-candidates", str(qgen_registry_max_candidates)]
        if audit_qgen_registry_candidates:
            args += ["--audit-qgen-registry-candidates", "--qgen-registry-audit-max-actions", str(qgen_registry_audit_max_actions)]
        if qgen_registry_accept_coker:
            args += ["--qgen-registry-accept-coker", "--qgen-registry-accept-margin", str(qgen_registry_accept_margin), "--qgen-registry-accept-max-per-task", str(qgen_registry_accept_max_per_task), "--qgen-registry-accept-cost-weight", str(qgen_registry_accept_cost_weight), "--qgen-registry-accept-carrier-weight", str(qgen_registry_accept_carrier_weight)]
            if qgen_registry_robust_coker_accept:
                args += ["--qgen-registry-robust-coker-accept", "--qgen-robust-coker-holdout-fraction", str(qgen_robust_coker_holdout_fraction), "--qgen-robust-coker-uncertainty-weight", str(qgen_robust_coker_uncertainty_weight), "--qgen-robust-coker-carrier-gain-weight", str(qgen_robust_coker_carrier_gain_weight), "--qgen-robust-coker-audit-penalty", str(qgen_robust_coker_audit_penalty)]
                if qgen_robust_coker_require_success:
                    args += ["--qgen-robust-coker-require-success"]
            elif qgen_registry_robust_accept:
                args += ["--qgen-registry-robust-accept", "--qgen-robust-z", str(qgen_robust_z), "--qgen-robust-min-repeats", str(qgen_robust_min_repeats), "--qgen-robust-min-success-rate", str(qgen_robust_min_success_rate)]
    if quotient_coordinates:
        args += ["--quotient-coordinates", "--quotient-coordinate-ridge", str(quotient_coordinate_ridge), "--quotient-coordinate-max-mass", str(quotient_coordinate_max_mass), "--quotient-coordinate-cosine-threshold", str(quotient_coordinate_cosine_threshold), "--quotient-coordinate-min-states", str(quotient_coordinate_min_states), "--quotient-coordinate-top-action-scores", str(quotient_coordinate_top_action_scores), "--quotient-coordinate-margin-threshold", str(quotient_coordinate_margin_threshold)]
        if quotient_coordinate_validate:
            args += ["--quotient-coordinate-validate"]
        if quotient_coordinate_registry_candidates:
            args += ["--quotient-coordinate-registry-candidates", "--quotient-coordinate-registry-max-candidates", str(quotient_coordinate_registry_max_candidates)]
        if audit_quotient_coordinate_candidates:
            args += ["--audit-quotient-coordinate-candidates", "--quotient-coordinate-audit-max-actions", str(quotient_coordinate_audit_max_actions)]
        if quotient_coordinate_accept_coker:
            args += ["--quotient-coordinate-accept-coker", "--quotient-coordinate-accept-margin", str(quotient_coordinate_accept_margin), "--quotient-coordinate-accept-max-per-task", str(quotient_coordinate_accept_max_per_task), "--quotient-coordinate-accept-cost-weight", str(quotient_coordinate_accept_cost_weight), "--quotient-coordinate-accept-carrier-weight", str(quotient_coordinate_accept_carrier_weight)]
            if quotient_coordinate_robust_coker_accept:
                args += ["--quotient-coordinate-robust-coker-accept", "--quotient-coordinate-robust-coker-holdout-fraction", str(quotient_coordinate_robust_coker_holdout_fraction), "--quotient-coordinate-robust-coker-uncertainty-weight", str(quotient_coordinate_robust_coker_uncertainty_weight), "--quotient-coordinate-robust-coker-carrier-gain-weight", str(quotient_coordinate_robust_coker_carrier_gain_weight), "--quotient-coordinate-robust-coker-audit-penalty", str(quotient_coordinate_robust_coker_audit_penalty)]
                if quotient_coordinate_robust_coker_require_success:
                    args += ["--quotient-coordinate-robust-coker-require-success"]
    if quotient_coordinates:
        args += ["--quotient-coordinates", "--quotient-coordinate-ridge", str(quotient_coordinate_ridge), "--quotient-coordinate-max-mass", str(quotient_coordinate_max_mass), "--quotient-coordinate-cosine-threshold", str(quotient_coordinate_cosine_threshold), "--quotient-coordinate-min-states", str(quotient_coordinate_min_states), "--quotient-coordinate-top-action-scores", str(quotient_coordinate_top_action_scores), "--quotient-coordinate-margin-threshold", str(quotient_coordinate_margin_threshold)]
        if quotient_coordinate_validate:
            args += ["--quotient-coordinate-validate"]
        if quotient_coordinate_registry_candidates:
            args += ["--quotient-coordinate-registry-candidates", "--quotient-coordinate-registry-max-candidates", str(quotient_coordinate_registry_max_candidates)]
        if audit_quotient_coordinate_candidates:
            args += ["--audit-quotient-coordinate-candidates", "--quotient-coordinate-audit-max-actions", str(quotient_coordinate_audit_max_actions)]
        if quotient_coordinate_accept_coker:
            args += ["--quotient-coordinate-accept-coker", "--quotient-coordinate-accept-margin", str(quotient_coordinate_accept_margin), "--quotient-coordinate-accept-max-per-task", str(quotient_coordinate_accept_max_per_task), "--quotient-coordinate-accept-cost-weight", str(quotient_coordinate_accept_cost_weight), "--quotient-coordinate-accept-carrier-weight", str(quotient_coordinate_accept_carrier_weight)]
            if quotient_coordinate_robust_coker_accept:
                args += ["--quotient-coordinate-robust-coker-accept", "--quotient-coordinate-robust-coker-holdout-fraction", str(quotient_coordinate_robust_coker_holdout_fraction), "--quotient-coordinate-robust-coker-uncertainty-weight", str(quotient_coordinate_robust_coker_uncertainty_weight), "--quotient-coordinate-robust-coker-carrier-gain-weight", str(quotient_coordinate_robust_coker_carrier_gain_weight), "--quotient-coordinate-robust-coker-audit-penalty", str(quotient_coordinate_robust_coker_audit_penalty)]
                if quotient_coordinate_robust_coker_require_success:
                    args += ["--quotient-coordinate-robust-coker-require-success"]
    if carrier_quotient:
        args += ["--carrier-quotient", "--carrier-quotient-ridge", str(carrier_quotient_ridge), "--carrier-quotient-max-mass", str(carrier_quotient_max_mass), "--carrier-quotient-cosine-threshold", str(carrier_quotient_cosine_threshold), "--carrier-quotient-min-states", str(carrier_quotient_min_states), "--carrier-quotient-top-action-scores", str(carrier_quotient_top_action_scores), "--carrier-quotient-margin-threshold", str(carrier_quotient_margin_threshold)]
        if audit_carrier_quotient_candidates:
            args += ["--audit-carrier-quotient-candidates", "--carrier-quotient-audit-max-actions", str(carrier_quotient_audit_max_actions)]
        if carrier_quotient_accept_coker:
            args += ["--carrier-quotient-accept-coker", "--carrier-quotient-accept-margin", str(carrier_quotient_accept_margin), "--carrier-quotient-accept-max-per-task", str(carrier_quotient_accept_max_per_task), "--carrier-quotient-accept-cost-weight", str(carrier_quotient_accept_cost_weight), "--carrier-quotient-accept-carrier-weight", str(carrier_quotient_accept_carrier_weight)]
            if carrier_quotient_robust_coker_accept:
                args += ["--carrier-quotient-robust-coker-accept", "--carrier-quotient-robust-coker-holdout-fraction", str(carrier_quotient_robust_coker_holdout_fraction), "--carrier-quotient-robust-coker-uncertainty-weight", str(carrier_quotient_robust_coker_uncertainty_weight), "--carrier-quotient-robust-coker-carrier-gain-weight", str(carrier_quotient_robust_coker_carrier_gain_weight), "--carrier-quotient-robust-coker-audit-penalty", str(carrier_quotient_robust_coker_audit_penalty)]
                if carrier_quotient_robust_coker_require_success:
                    args += ["--carrier-quotient-robust-coker-require-success"]
    if action_geometry:
        args += ["--action-geometry", "--action-geometry-min-count", str(action_geometry_min_count), "--action-geometry-tail-weight", str(action_geometry_tail_weight), "--action-geometry-gamma-value-mode", str(action_geometry_gamma_value_mode), "--action-geometry-gamma-horizon", str(action_geometry_gamma_horizon), "--action-geometry-gamma-discount", str(action_geometry_gamma_discount), "--action-geometry-gamma-stability-margin", str(action_geometry_gamma_stability_margin), "--action-geometry-gamma-tail-value-weight", str(action_geometry_gamma_tail_value_weight), "--action-geometry-gamma-tail-risk-mode", str(action_geometry_gamma_tail_risk_mode), "--action-geometry-cost-weight", str(action_geometry_cost_weight), "--action-geometry-uncertainty-weight", str(action_geometry_uncertainty_weight), "--action-geometry-audit-weight", str(action_geometry_audit_weight), "--action-geometry-carrier-budget", str(action_geometry_carrier_budget)]
        if action_geometry_retrieve:
            args += ["--action-geometry-retrieve"]
        if action_geometry_use_gamma_transition:
            args += ["--action-geometry-use-gamma-transition"]
        if action_geometry_use_qgen_normals:
            args += ["--action-geometry-use-qgen-normals"]
        if action_geometry_use_quotient_normals:
            args += ["--action-geometry-use-quotient-normals"]
        if action_geometry_use_quotient_normals:
            args += ["--action-geometry-use-quotient-normals"]
        if action_geometry_top_k is not None:
            args += ["--action-geometry-top-k", str(action_geometry_top_k)]
        if action_geometry_require_carrier_safe:
            args += ["--action-geometry-require-carrier-safe"]
        if audit_action_geometry_candidates:
            args += ["--audit-action-geometry-candidates", "--action-geometry-audit-max-actions", str(action_geometry_audit_max_actions)]
        if action_geometry_accept_coker:
            args += ["--action-geometry-accept-coker", "--action-geometry-accept-margin", str(action_geometry_accept_margin), "--action-geometry-accept-max-per-task", str(action_geometry_accept_max_per_task), "--action-geometry-accept-cost-weight", str(action_geometry_accept_cost_weight), "--action-geometry-accept-carrier-weight", str(action_geometry_accept_carrier_weight)]
            if action_geometry_robust_coker_accept:
                args += ["--action-geometry-robust-coker-accept", "--action-geometry-robust-coker-holdout-fraction", str(action_geometry_robust_coker_holdout_fraction), "--action-geometry-robust-coker-uncertainty-weight", str(action_geometry_robust_coker_uncertainty_weight), "--action-geometry-robust-coker-carrier-gain-weight", str(action_geometry_robust_coker_carrier_gain_weight), "--action-geometry-robust-coker-audit-penalty", str(action_geometry_robust_coker_audit_penalty)]
                if action_geometry_robust_coker_require_success:
                    args += ["--action-geometry-robust-coker-require-success"]
    if frontier_normalize:
        args += ["--frontier-normalize", "--frontier-max-prefixes", str(frontier_max_prefixes)]
        if frontier_include_identity:
            args += ["--frontier-include-identity"]
    if promote_registry:
        args += ["--promote-registry"]
    if premise_index:
        args += ["--premise-index"]
        if audit_premise_candidates:
            args += ["--audit-premise-candidates", "--premise-audit-max-actions", str(premise_audit_max_actions)]
    if carrier_accept:
        args += ["--carrier-accept", "--carrier-accept-max-actions", str(carrier_accept_max_actions)]
        if promote_carrier_actions:
            args += ["--promote-carrier-actions"]
    if ir_candidates:
        args += ["--ir-candidates", "--ir-max-candidates", str(ir_max_candidates)]
        if audit_ir_candidates:
            args += ["--audit-ir-candidates", "--ir-audit-max-actions", str(ir_audit_max_actions)]
        if ir_accept_coker:
            args += ["--ir-accept-coker"]
    if carrier_matrix:
        args += ["--carrier-matrix", "--carrier-matrix-budget", str(carrier_matrix_budget)]
        if carrier_matrix_keep_unsafe:
            args += ["--carrier-matrix-keep-unsafe"]
        if carrier_matrix_merge_qgen:
            args += ["--carrier-matrix-merge-qgen", "--carrier-matrix-qgen-patch-weight", str(carrier_matrix_qgen_patch_weight)]
            if carrier_matrix_qgen_require_safe:
                args += ["--carrier-matrix-qgen-require-safe"]
            if carrier_matrix_qgen_audit_patches:
                args += ["--carrier-matrix-qgen-audit-patches", "--carrier-matrix-qgen-patch-min-count", str(carrier_matrix_qgen_patch_min_count), "--carrier-matrix-qgen-patch-min-mean-delta", str(carrier_matrix_qgen_patch_min_mean_delta), "--carrier-matrix-qgen-patch-holdout-fraction", str(carrier_matrix_qgen_patch_holdout_fraction)]
                if carrier_matrix_qgen_patch_require_heldout:
                    args += ["--carrier-matrix-qgen-patch-require-heldout"]
    if contextual_congruence:
        args += [
            "--contextual-congruence",
            "--contextual-congruence-context-mode", str(contextual_congruence_context_mode),
            "--contextual-congruence-min-count", str(contextual_congruence_min_count),
            "--contextual-congruence-cosine-threshold", str(contextual_congruence_cosine_threshold),
            "--contextual-congruence-distance-threshold", str(contextual_congruence_distance_threshold),
            "--contextual-congruence-min-context-jaccard", str(contextual_congruence_min_context_jaccard),
        ]
        if contextual_congruence_no_carrier:
            args += ["--contextual-congruence-no-carrier"]
    if contextual_probes:
        args += [
            "--contextual-probes",
            "--contextual-probe-max-left", str(contextual_probe_max_left),
            "--contextual-probe-max-right", str(contextual_probe_max_right),
            "--contextual-probe-max-candidates", str(contextual_probe_max_candidates if contextual_probe_max_candidates is not None else 0),
        ]
        if contextual_probe_contexts:
            args += ["--contextual-probe-contexts", str(contextual_probe_contexts)]
        if contextual_probe_max_core is not None:
            args += ["--contextual-probe-max-core", str(contextual_probe_max_core)]
        if contextual_probe_no_identity:
            args += ["--contextual-probe-no-identity"]
        if contextual_probe_no_left:
            args += ["--contextual-probe-no-left"]
        if contextual_probe_no_right:
            args += ["--contextual-probe-no-right"]
        if audit_contextual_probe_candidates:
            args += ["--audit-contextual-probe-candidates", "--contextual-probe-audit-max-actions", str(contextual_probe_audit_max_actions)]
        if contextual_probe_congruence:
            args += [
                "--contextual-probe-congruence",
                "--contextual-probe-congruence-context-mode", str(contextual_probe_congruence_context_mode),
                "--contextual-probe-congruence-min-count", str(contextual_probe_congruence_min_count),
                "--contextual-probe-congruence-cosine-threshold", str(contextual_probe_congruence_cosine_threshold),
                "--contextual-probe-congruence-distance-threshold", str(contextual_probe_congruence_distance_threshold),
                "--contextual-probe-congruence-min-context-jaccard", str(contextual_probe_congruence_min_context_jaccard),
            ]
            if contextual_probe_congruence_no_carrier:
                args += ["--contextual-probe-congruence-no-carrier"]
        if contextual_probe_accept_coker:
            args += [
                "--contextual-probe-accept-coker",
                "--contextual-probe-accept-margin", str(contextual_probe_accept_margin),
                "--contextual-probe-accept-max-per-task", str(contextual_probe_accept_max_per_task),
                "--contextual-probe-accept-cost-weight", str(contextual_probe_accept_cost_weight),
                "--contextual-probe-accept-carrier-weight", str(contextual_probe_accept_carrier_weight),
            ]
            if contextual_probe_robust_coker_accept:
                args += [
                    "--contextual-probe-robust-coker-accept",
                    "--contextual-probe-robust-coker-holdout-fraction", str(contextual_probe_robust_coker_holdout_fraction),
                    "--contextual-probe-robust-coker-uncertainty-weight", str(contextual_probe_robust_coker_uncertainty_weight),
                    "--contextual-probe-robust-coker-carrier-gain-weight", str(contextual_probe_robust_coker_carrier_gain_weight),
                    "--contextual-probe-robust-coker-audit-penalty", str(contextual_probe_robust_coker_audit_penalty),
                ]
                if contextual_probe_robust_coker_require_success:
                    args += ["--contextual-probe-robust-coker-require-success"]
        if response_quotient_registry:
            args += [
                "--response-quotient-registry",
                "--response-quotient-min-members", str(response_quotient_min_members),
            ]
            if response_quotient_min_quality is not None:
                args += ["--response-quotient-min-quality", str(response_quotient_min_quality)]
            if response_quotient_project_actions:
                args += ["--response-quotient-project-actions"]
            if response_quotient_annotate_only:
                args += ["--response-quotient-annotate-only"]
        if failure_signatures:
            args += ["--failure-signatures"]
        if audit_failure_signature_candidates:
            args += ["--audit-failure-signature-candidates", "--failure-signature-audit-max-actions", str(failure_signature_audit_max_actions)]
        if failure_signature_accept_coker:
            args += ["--failure-signature-accept-coker", "--failure-signature-accept-margin", str(failure_signature_accept_margin), "--failure-signature-accept-max-per-task", str(failure_signature_accept_max_per_task)]
    return args


def _round_metrics(rdir: Path, merge_inputs: list[Path], *, r: int, actions_in: str | None, actions_next: Path | None, n_next: int) -> IterationRoundSummary:
    audit_summary = _read_json(rdir / "audit" / "summary.json")
    n_resp = int((audit_summary.get("n") or audit_summary.get("n_responses") or 0) or 0)
    statuses = audit_summary.get("statuses") or {}
    succ = float(statuses.get("success", 0) + statuses.get("dry_run", 0) + statuses.get("partial", 0))
    success_rate = (succ / n_resp) if n_resp else None
    gamma_rows = read_jsonl(rdir / "gamma_audit.jsonl") if (rdir / "gamma_audit.jsonl").exists() else []
    gamma_last = gamma_rows[-1] if gamma_rows else {}
    frontier = _read_json(rdir / "frontier" / "frontier_summary.json")
    qgen_report = _read_json(rdir / "qgen" / "qgen_report.json")
    qgen_summary = qgen_report.get("summary", {}) if isinstance(qgen_report.get("summary"), dict) else {}
    merged_stats = {str(p): _count_jsonl(p) for p in merge_inputs if p and p.exists()}
    return IterationRoundSummary(
        round=r,
        out_dir=str(rdir),
        actions_in=actions_in,
        actions_next=str(actions_next) if actions_next and n_next > 0 else None,
        n_actions_next=n_next,
        audit_success_rate=success_rate,
        audit_n=n_resp or None,
        registry_accepted=_count_jsonl(rdir / "registry_accepted_actions.jsonl"),
        carrier_promoted=_count_jsonl(rdir / "carrier_promoted_actions.jsonl"),
        premise_actions=_count_jsonl(rdir / "premise_actions.jsonl"),
        frontier_tasks=frontier.get("n_frontier_tasks") if frontier else None,
        frontier_closed=frontier.get("n_closed_by_exposure") if frontier else None,
        gamma_vs_persistence=gamma_last.get("gamma_vs_persistence_improvement"),
        gamma_cocycle_rel=gamma_last.get("cocycle_resid_rel"),
        mean_goal_response=audit_summary.get("mean_goal_response"),
        mean_carrier_delta=audit_summary.get("mean_carrier_delta"),
        qgen_contexts=qgen_summary.get("n_context_proposals", _count_jsonl(rdir / "qgen" / "qgen_context_candidates.jsonl")),
        qgen_accepted=qgen_summary.get("n_context_accepted", _count_jsonl(rdir / "qgen" / "qgen_accepted_actions.jsonl")),
        qgen_defects=qgen_summary.get("n_defect_proposals", _count_jsonl(rdir / "qgen" / "qgen_defect_atoms.jsonl")),
        qgen_carriers=qgen_summary.get("n_carrier_incidence", _count_jsonl(rdir / "qgen" / "qgen_carrier_incidence.jsonl")),
        qgen_failures=qgen_summary.get("n_failure_charts", _count_jsonl(rdir / "qgen" / "qgen_failure_signatures.jsonl")),
        action_geometry_candidates=_count_jsonl(rdir / "action_geometry" / "action_geometry_candidates.jsonl") or _count_jsonl(rdir / "action_geometry_candidates.jsonl"),
        action_geometry_accepted=_count_jsonl(rdir / "action_geometry_robust_accepted_actions.jsonl") or _count_jsonl(rdir / "action_geometry_accepted_actions.jsonl"),
        contextual_probe_candidates=_count_jsonl(rdir / "contextual_probes" / "contextual_probe_candidates.jsonl"),
        contextual_probe_accepted=_count_jsonl(rdir / "contextual_probe_robust_accepted_actions.jsonl") or _count_jsonl(rdir / "contextual_probe_accepted_actions.jsonl"),
        carrier_quotient_candidates=_count_jsonl(rdir / "carrier_quotient" / "carrier_quotient_candidates.jsonl"),
        carrier_quotient_accepted=_count_jsonl(rdir / "carrier_quotient_robust_accepted_actions.jsonl") or _count_jsonl(rdir / "carrier_quotient_accepted_actions.jsonl"),
        merged_sources=merged_stats,
    )


def run_iterative_pipeline(
    *,
    tasks: str,
    actions: str | None,
    out: str,
    rounds: int = 2,
    dry_run: bool = True,
    jobs: int = 1,
    max_actions: int = 32,
    lean_cmd: str = "lake env lean",
    workdir: str | None = None,
    timeout_s: float = 20.0,
    import_mode: str = "auto",
    cache_dir: str | None = None,
    server_cmd: str | None = None,
    server_backend: str = "auto",
    server_no_fallback: bool = False,
    native_exec_mode: str = "source_check",
    resume: bool = False,
    flush_every: int = 50,
    candidate_mode: str = "state",
    audit_mode: str = "batch",
    bulk_batch_size: int = 64,
    frontier_normalize: bool = False,
    frontier_max_prefixes: int = 8,
    frontier_include_identity: bool = False,
    registry_audit_max_actions: int = 16,
    registry_accept_margin: float = 0.0,
    registry_accept_max_per_task: int = 16,
    promote_registry: bool = False,
    premise_index: bool = False,
    audit_premise_candidates: bool = False,
    premise_audit_max_actions: int = 16,
    merge_premise_actions: bool = False,
    carrier_accept: bool = False,
    carrier_accept_max_actions: int = 8,
    promote_carrier_actions: bool = False,
    fit_gamma: bool = True,
    qgen: bool = False,
    qgen_merge_actions: bool = False,
    qgen_merge_policy: str = "all",
    poms_promote: bool = False,
    poms_generate_evidence: bool = False,
    poms_evidence_min_relative_residual: float = 0.05,
    poms_evidence_min_residual_norm: float = 1e-6,
    poms_evidence_min_support_count: int = 1,
    poms_evidence_min_margin: float = 0.0,
    poms_evidence_min_robust_margin: float = 0.0,
    poms_evidence_least_repair_epsilon: float = 1e-9,
    poms_promotion_evidence: list[str] | None = None,
    poms_promote_parent_nonpaid: bool = False,
    poms_promote_dual_certificate: bool = False,
    poms_promote_least_repair: bool = False,
    poms_declare_canonical: bool = False,
    qgen_top_defects: int = 16,
    qgen_top_contexts: int = 32,
    qgen_top_carriers: int = 64,
    qgen_top_failures: int = 32,
    qgen_margin_threshold: float = 0.0,
    qgen_cost_weight: float = 0.05,
    qgen_carrier_weight: float = 0.25,
    qgen_audit_penalty: float = 1.0,
    audit_qgen_candidates: bool = False,
    qgen_audit_max_actions: int = 24,
    qgen_accept_coker: bool = False,
    qgen_accept_margin: float = 0.0,
    qgen_accept_max_per_task: int = 16,
    qgen_accept_cost_weight: float = 0.05,
    qgen_accept_carrier_weight: float = 0.7,
    qgen_robust_accept: bool = False, qgen_registry_robust_accept: bool = False,
    qgen_robust_coker_accept: bool = False, qgen_registry_robust_coker_accept: bool = False,
    qgen_robust_coker_holdout_fraction: float = 0.35, qgen_robust_coker_uncertainty_weight: float = 0.10,
    qgen_robust_coker_carrier_gain_weight: float = 0.25, qgen_robust_coker_audit_penalty: float = 1.0,
    qgen_robust_coker_require_success: bool = False,
    qgen_robust_z: float = 1.0, qgen_robust_min_repeats: int = 1,
    qgen_robust_min_success_rate: float = 1.0,
    qgen_registry_candidates: bool = False,
    qgen_registry_max_candidates: int = 64,
    audit_qgen_registry_candidates: bool = False,
    qgen_registry_audit_max_actions: int = 16,
    qgen_registry_accept_coker: bool = False,
    qgen_registry_accept_margin: float = 0.0,
    qgen_registry_accept_max_per_task: int = 16,
    qgen_registry_accept_cost_weight: float = 0.05,
    qgen_registry_accept_carrier_weight: float = 0.7,
    action_geometry: bool = False,
    action_geometry_retrieve: bool = False,
    action_geometry_use_qgen_normals: bool = False,
    action_geometry_use_gamma_transition: bool = False,
    action_geometry_merge_actions: bool = False,
    action_geometry_merge_policy: str = "robust-only",
    audit_db: bool = False,
    audit_db_path: str | None = None,
    audit_db_append: bool = False,
    audit_scheduler: bool = False,
    audit_scheduler_db: str | None = None,
    audit_scheduler_responses: str | None = None,
    audit_scheduler_lineage: list[str] | None = None,
    audit_scheduler_budget: int | None = None,
    audit_scheduler_per_task_cap: int | None = None,
    audit_scheduler_per_source_cap: int | None = None,
    audit_scheduler_coker_weight: float = 1.0,
    audit_scheduler_carrier_weight: float = 0.5,
    audit_scheduler_uncertainty_weight: float = 0.25,
    audit_scheduler_novelty_weight: float = 0.15,
    audit_scheduler_success_weight: float = 0.25,
    audit_scheduler_cost_weight: float = 0.10,
    audit_scheduler_timeout_weight: float = 0.50,
    source_budget: bool = False,
    audit_source_budget_candidates: bool = False,
    source_budget_merge_actions: bool = False,
    source_budget_merge_policy: str = 'scheduled-only',
    source_budget_budget: int | None = None,
    source_budget_min_per_source: int = 0,
    source_budget_max_per_source: int | None = None,
    source_budget_per_task_cap: int | None = None,
    source_budget_per_action_cap: int = 1,
    source_budget_allocation_mode: str = 'proportional',
    source_budget_coker_weight: float = 1.0,
    source_budget_carrier_weight: float = 0.5,
    source_budget_uncertainty_weight: float = 0.20,
    source_budget_novelty_weight: float = 0.25,
    source_budget_lineage_weight: float = 0.15,
    source_budget_success_weight: float = 0.25,
    source_budget_cost_weight: float = 0.10,
    source_budget_timeout_weight: float = 0.50,
    source_budget_gamma_aware: bool = False,
    source_budget_gamma_value_mode: str = 'finite_horizon',
    source_budget_gamma_horizon: int = 4,
    source_budget_gamma_discount: float = 1.0,
    source_budget_gamma_value_weight: float = 0.50,
    source_budget_gamma_tail_risk_weight: float = 0.25,
    source_budget_gamma_stability_delta: float = 0.05,
    source_budget_gamma_tail_risk_mode: str = 'spectral',
    action_geometry_top_k: int | None = 32,
    action_geometry_min_count: int = 1,
    action_geometry_tail_weight: float = 0.25,
    action_geometry_gamma_value_mode: str = "local",
    action_geometry_gamma_horizon: int = 4,
    action_geometry_gamma_discount: float = 1.0,
    action_geometry_gamma_stability_margin: float = 0.05,
    action_geometry_gamma_tail_value_weight: float = 1.0,
    action_geometry_gamma_tail_risk_mode: str = 'spectral',
    action_geometry_cost_weight: float = 0.05,
    action_geometry_uncertainty_weight: float = 0.10,
    action_geometry_audit_weight: float = 0.20,
    action_geometry_require_carrier_safe: bool = False,
    action_geometry_carrier_budget: float = 0.0,
    audit_action_geometry_candidates: bool = False,
    action_geometry_audit_max_actions: int = 24,
    action_geometry_accept_coker: bool = False,
    action_geometry_accept_margin: float = 0.0,
    action_geometry_accept_max_per_task: int = 16,
    action_geometry_accept_cost_weight: float = 0.05,
    action_geometry_accept_carrier_weight: float = 0.7,
    action_geometry_robust_coker_accept: bool = False,
    action_geometry_robust_coker_holdout_fraction: float = 0.35,
    action_geometry_robust_coker_uncertainty_weight: float = 0.10,
    action_geometry_robust_coker_carrier_gain_weight: float = 0.25,
    action_geometry_robust_coker_audit_penalty: float = 1.0,
    action_geometry_robust_coker_require_success: bool = False,
    quotient_coordinates: bool = False,
    quotient_coordinate_merge_actions: bool = False,
    quotient_coordinate_merge_policy: str = "robust-only",
    quotient_coordinate_ridge: float = 1e-4,
    quotient_coordinate_max_mass: float = 1.0,
    quotient_coordinate_cosine_threshold: float = 0.85,
    quotient_coordinate_min_states: int = 1,
    quotient_coordinate_top_action_scores: int = 128,
    quotient_coordinate_margin_threshold: float = 0.0,
    quotient_coordinate_validate: bool = False,
    quotient_coordinate_registry_candidates: bool = False,
    quotient_coordinate_registry_max_candidates: int = 64,
    audit_quotient_coordinate_candidates: bool = False,
    quotient_coordinate_audit_max_actions: int = 16,
    quotient_coordinate_accept_coker: bool = False,
    quotient_coordinate_robust_coker_accept: bool = False,
    quotient_coordinate_accept_margin: float = 0.0,
    quotient_coordinate_accept_max_per_task: int = 16,
    quotient_coordinate_accept_cost_weight: float = 0.05,
    quotient_coordinate_accept_carrier_weight: float = 0.7,
    quotient_coordinate_robust_coker_holdout_fraction: float = 0.35,
    quotient_coordinate_robust_coker_uncertainty_weight: float = 0.10,
    quotient_coordinate_robust_coker_carrier_gain_weight: float = 0.25,
    quotient_coordinate_robust_coker_audit_penalty: float = 1.0,
    quotient_coordinate_robust_coker_require_success: bool = False,
    carrier_quotient: bool = False,
    carrier_quotient_merge_actions: bool = False,
    carrier_quotient_merge_policy: str = "robust-only",
    carrier_quotient_ridge: float = 1e-4,
    carrier_quotient_max_mass: float = 1.0,
    carrier_quotient_cosine_threshold: float = 0.85,
    carrier_quotient_min_states: int = 1,
    carrier_quotient_top_action_scores: int = 128,
    carrier_quotient_margin_threshold: float = 0.0,
    audit_carrier_quotient_candidates: bool = False,
    carrier_quotient_audit_max_actions: int = 16,
    carrier_quotient_accept_coker: bool = False,
    carrier_quotient_robust_coker_accept: bool = False,
    carrier_quotient_accept_margin: float = 0.0,
    carrier_quotient_accept_max_per_task: int = 16,
    carrier_quotient_accept_cost_weight: float = 0.05,
    carrier_quotient_accept_carrier_weight: float = 0.7,
    carrier_quotient_robust_coker_holdout_fraction: float = 0.35,
    carrier_quotient_robust_coker_uncertainty_weight: float = 0.10,
    carrier_quotient_robust_coker_carrier_gain_weight: float = 0.25,
    carrier_quotient_robust_coker_audit_penalty: float = 1.0,
    carrier_quotient_robust_coker_require_success: bool = False,
    action_geometry_use_quotient_normals: bool = False,
    contextual_congruence: bool = False,
    contextual_congruence_context_mode: str = 'state',
    contextual_congruence_no_carrier: bool = False,
    contextual_congruence_min_count: int = 1,
    contextual_congruence_cosine_threshold: float = 0.95,
    contextual_congruence_distance_threshold: float = 0.25,
    contextual_congruence_min_context_jaccard: float = 0.0,
    contextual_probes: bool = False,
    contextual_probe_contexts: str | None = None,
    contextual_probe_max_left: int = 4,
    contextual_probe_max_right: int = 4,
    contextual_probe_max_core: int | None = None,
    contextual_probe_max_candidates: int | None = 128,
    contextual_probe_no_identity: bool = False,
    contextual_probe_no_left: bool = False,
    contextual_probe_no_right: bool = False,
    audit_contextual_probe_candidates: bool = False,
    contextual_probe_audit_max_actions: int = 24,
    contextual_probe_congruence: bool = False,
    contextual_probe_congruence_context_mode: str = 'state',
    contextual_probe_congruence_no_carrier: bool = False,
    contextual_probe_congruence_min_count: int = 1,
    contextual_probe_congruence_cosine_threshold: float = 0.95,
    contextual_probe_congruence_distance_threshold: float = 0.25,
    contextual_probe_congruence_min_context_jaccard: float = 0.0,
    contextual_probe_accept_coker: bool = False,
    contextual_probe_robust_coker_accept: bool = False,
    contextual_probe_accept_margin: float = 0.0,
    contextual_probe_accept_max_per_task: int = 16,
    contextual_probe_accept_cost_weight: float = 0.05,
    contextual_probe_accept_carrier_weight: float = 0.7,
    contextual_probe_robust_coker_holdout_fraction: float = 0.35,
    contextual_probe_robust_coker_uncertainty_weight: float = 0.10,
    contextual_probe_robust_coker_carrier_gain_weight: float = 0.25,
    contextual_probe_robust_coker_audit_penalty: float = 1.0,
    contextual_probe_robust_coker_require_success: bool = False,
    contextual_probe_merge_actions: bool = False,
    contextual_probe_merge_policy: str = 'robust-only',
    response_quotient_registry: bool = False,
    response_quotient_min_members: int = 1,
    response_quotient_min_quality: float | None = None,
    response_quotient_project_actions: bool = False,
    response_quotient_annotate_only: bool = False,
    response_quotient_merge_actions: bool = False,
    response_quotient_merge_policy: str = 'representatives',
    ir_candidates: bool = False,
    ir_max_candidates: int = 64,
    audit_ir_candidates: bool = False,
    ir_audit_max_actions: int = 24,
    ir_accept_coker: bool = False,
    carrier_matrix: bool = False,
    carrier_matrix_budget: float = 0.0,
    carrier_matrix_keep_unsafe: bool = False,
    carrier_matrix_merge_qgen: bool = False,
    carrier_matrix_qgen_patch_weight: float = 1.0,
    carrier_matrix_qgen_require_safe: bool = False,
    carrier_matrix_qgen_audit_patches: bool = False,
    carrier_matrix_qgen_patch_min_count: int = 1,
    carrier_matrix_qgen_patch_min_mean_delta: float = 0.0,
    carrier_matrix_qgen_patch_holdout_fraction: float = 0.0,
    carrier_matrix_qgen_patch_require_heldout: bool = False,
    failure_signatures: bool = False,
    audit_failure_signature_candidates: bool = False,
    failure_signature_audit_max_actions: int = 16,
    failure_signature_accept_coker: bool = False,
    failure_signature_accept_margin: float = 0.0,
    failure_signature_accept_max_per_task: int = 16,
    next_action_cap: int | None = None,
) -> dict[str, Any]:
    root = Path(out); root.mkdir(parents=True, exist_ok=True)
    action_path: str | None = actions
    summaries: list[IterationRoundSummary] = []
    for r in range(rounds):
        rdir = root / f"round_{r:02d}"
        args = _pipeline_args(
            tasks=tasks,
            action_path=action_path,
            rdir=rdir,
            dry_run=dry_run,
            jobs=jobs,
            max_actions=max_actions,
            lean_cmd=lean_cmd,
            workdir=workdir,
            timeout_s=timeout_s,
            import_mode=import_mode,
            flush_every=flush_every,
            candidate_mode=candidate_mode,
            audit_mode=audit_mode,
            bulk_batch_size=bulk_batch_size,
            cache_dir=cache_dir,
            server_cmd=server_cmd,
            server_backend=server_backend,
            server_no_fallback=server_no_fallback,
            native_exec_mode=native_exec_mode,
            resume=resume,
            fit_gamma=fit_gamma,
            qgen=qgen,
            qgen_top_defects=qgen_top_defects,
            qgen_top_contexts=qgen_top_contexts,
            qgen_top_carriers=qgen_top_carriers,
            qgen_top_failures=qgen_top_failures,
            qgen_margin_threshold=qgen_margin_threshold,
            qgen_cost_weight=qgen_cost_weight,
            qgen_carrier_weight=qgen_carrier_weight,
            qgen_audit_penalty=qgen_audit_penalty,
            audit_qgen_candidates=audit_qgen_candidates,
            qgen_audit_max_actions=qgen_audit_max_actions,
            qgen_accept_coker=qgen_accept_coker,
            qgen_accept_margin=qgen_accept_margin,
            qgen_accept_max_per_task=qgen_accept_max_per_task,
            qgen_accept_cost_weight=qgen_accept_cost_weight,
            qgen_accept_carrier_weight=qgen_accept_carrier_weight,
            qgen_robust_accept=qgen_robust_accept,
            qgen_registry_robust_accept=qgen_registry_robust_accept,
            qgen_robust_coker_accept=qgen_robust_coker_accept,
            qgen_registry_robust_coker_accept=qgen_registry_robust_coker_accept,
            qgen_robust_coker_holdout_fraction=qgen_robust_coker_holdout_fraction,
            qgen_robust_coker_uncertainty_weight=qgen_robust_coker_uncertainty_weight,
            qgen_robust_coker_carrier_gain_weight=qgen_robust_coker_carrier_gain_weight,
            qgen_robust_coker_audit_penalty=qgen_robust_coker_audit_penalty,
            qgen_robust_coker_require_success=qgen_robust_coker_require_success,
            qgen_robust_z=qgen_robust_z,
            qgen_robust_min_repeats=qgen_robust_min_repeats,
            qgen_robust_min_success_rate=qgen_robust_min_success_rate,
            qgen_registry_candidates=qgen_registry_candidates,
            qgen_registry_max_candidates=qgen_registry_max_candidates,
            audit_qgen_registry_candidates=audit_qgen_registry_candidates,
            qgen_registry_audit_max_actions=qgen_registry_audit_max_actions,
            qgen_registry_accept_coker=qgen_registry_accept_coker,
            qgen_registry_accept_margin=qgen_registry_accept_margin,
            qgen_registry_accept_max_per_task=qgen_registry_accept_max_per_task,
            qgen_registry_accept_cost_weight=qgen_registry_accept_cost_weight,
            qgen_registry_accept_carrier_weight=qgen_registry_accept_carrier_weight,
            action_geometry=action_geometry,
            action_geometry_retrieve=action_geometry_retrieve,
            action_geometry_use_qgen_normals=action_geometry_use_qgen_normals,
            action_geometry_use_gamma_transition=action_geometry_use_gamma_transition,
            audit_scheduler=audit_scheduler,
            audit_scheduler_db=audit_scheduler_db,
            audit_scheduler_responses=audit_scheduler_responses,
            audit_scheduler_lineage=audit_scheduler_lineage,
            audit_scheduler_budget=audit_scheduler_budget,
            audit_scheduler_per_task_cap=audit_scheduler_per_task_cap,
            audit_scheduler_per_source_cap=audit_scheduler_per_source_cap,
            audit_scheduler_coker_weight=audit_scheduler_coker_weight,
            audit_scheduler_carrier_weight=audit_scheduler_carrier_weight,
            audit_scheduler_uncertainty_weight=audit_scheduler_uncertainty_weight,
            audit_scheduler_novelty_weight=audit_scheduler_novelty_weight,
            audit_scheduler_success_weight=audit_scheduler_success_weight,
            audit_scheduler_cost_weight=audit_scheduler_cost_weight,
            audit_scheduler_timeout_weight=audit_scheduler_timeout_weight,
            source_budget=source_budget,
            audit_source_budget_candidates=audit_source_budget_candidates,
            source_budget_merge_actions=source_budget_merge_actions,
            source_budget_merge_policy=source_budget_merge_policy,
            source_budget_budget=source_budget_budget,
            source_budget_min_per_source=source_budget_min_per_source,
            source_budget_max_per_source=source_budget_max_per_source,
            source_budget_per_task_cap=source_budget_per_task_cap,
            source_budget_per_action_cap=source_budget_per_action_cap,
            source_budget_allocation_mode=source_budget_allocation_mode,
            source_budget_coker_weight=source_budget_coker_weight,
            source_budget_carrier_weight=source_budget_carrier_weight,
            source_budget_uncertainty_weight=source_budget_uncertainty_weight,
            source_budget_novelty_weight=source_budget_novelty_weight,
            source_budget_lineage_weight=source_budget_lineage_weight,
            source_budget_success_weight=source_budget_success_weight,
            source_budget_cost_weight=source_budget_cost_weight,
            source_budget_timeout_weight=source_budget_timeout_weight,
            source_budget_gamma_aware=source_budget_gamma_aware,
            source_budget_gamma_value_mode=source_budget_gamma_value_mode,
            source_budget_gamma_horizon=source_budget_gamma_horizon,
            source_budget_gamma_discount=source_budget_gamma_discount,
            source_budget_gamma_value_weight=source_budget_gamma_value_weight,
            source_budget_gamma_tail_risk_weight=source_budget_gamma_tail_risk_weight,
            source_budget_gamma_stability_delta=source_budget_gamma_stability_delta,
            source_budget_gamma_tail_risk_mode=source_budget_gamma_tail_risk_mode,
            action_geometry_top_k=action_geometry_top_k,
            action_geometry_min_count=action_geometry_min_count,
            action_geometry_tail_weight=action_geometry_tail_weight,
            action_geometry_gamma_value_mode=action_geometry_gamma_value_mode,
            action_geometry_gamma_horizon=action_geometry_gamma_horizon,
            action_geometry_gamma_discount=action_geometry_gamma_discount,
            action_geometry_gamma_stability_margin=action_geometry_gamma_stability_margin,
            action_geometry_gamma_tail_value_weight=action_geometry_gamma_tail_value_weight,
            action_geometry_gamma_tail_risk_mode=action_geometry_gamma_tail_risk_mode,
            action_geometry_cost_weight=action_geometry_cost_weight,
            action_geometry_uncertainty_weight=action_geometry_uncertainty_weight,
            action_geometry_audit_weight=action_geometry_audit_weight,
            action_geometry_require_carrier_safe=action_geometry_require_carrier_safe,
            action_geometry_carrier_budget=action_geometry_carrier_budget,
            audit_action_geometry_candidates=audit_action_geometry_candidates,
            action_geometry_audit_max_actions=action_geometry_audit_max_actions,
            action_geometry_accept_coker=action_geometry_accept_coker,
            action_geometry_accept_margin=action_geometry_accept_margin,
            action_geometry_accept_max_per_task=action_geometry_accept_max_per_task,
            action_geometry_accept_cost_weight=action_geometry_accept_cost_weight,
            action_geometry_accept_carrier_weight=action_geometry_accept_carrier_weight,
            action_geometry_robust_coker_accept=action_geometry_robust_coker_accept,
            action_geometry_robust_coker_holdout_fraction=action_geometry_robust_coker_holdout_fraction,
            action_geometry_robust_coker_uncertainty_weight=action_geometry_robust_coker_uncertainty_weight,
            action_geometry_robust_coker_carrier_gain_weight=action_geometry_robust_coker_carrier_gain_weight,
            action_geometry_robust_coker_audit_penalty=action_geometry_robust_coker_audit_penalty,
            action_geometry_robust_coker_require_success=action_geometry_robust_coker_require_success,
            quotient_coordinates=quotient_coordinates,
            quotient_coordinate_ridge=quotient_coordinate_ridge,
            quotient_coordinate_max_mass=quotient_coordinate_max_mass,
            quotient_coordinate_cosine_threshold=quotient_coordinate_cosine_threshold,
            quotient_coordinate_min_states=quotient_coordinate_min_states,
            quotient_coordinate_top_action_scores=quotient_coordinate_top_action_scores,
            quotient_coordinate_margin_threshold=quotient_coordinate_margin_threshold,
            quotient_coordinate_validate=quotient_coordinate_validate,
            quotient_coordinate_registry_candidates=quotient_coordinate_registry_candidates,
            quotient_coordinate_registry_max_candidates=quotient_coordinate_registry_max_candidates,
            audit_quotient_coordinate_candidates=audit_quotient_coordinate_candidates,
            quotient_coordinate_audit_max_actions=quotient_coordinate_audit_max_actions,
            quotient_coordinate_accept_coker=quotient_coordinate_accept_coker,
            quotient_coordinate_robust_coker_accept=quotient_coordinate_robust_coker_accept,
            quotient_coordinate_accept_margin=quotient_coordinate_accept_margin,
            quotient_coordinate_accept_max_per_task=quotient_coordinate_accept_max_per_task,
            quotient_coordinate_accept_cost_weight=quotient_coordinate_accept_cost_weight,
            quotient_coordinate_accept_carrier_weight=quotient_coordinate_accept_carrier_weight,
            quotient_coordinate_robust_coker_holdout_fraction=quotient_coordinate_robust_coker_holdout_fraction,
            quotient_coordinate_robust_coker_uncertainty_weight=quotient_coordinate_robust_coker_uncertainty_weight,
            quotient_coordinate_robust_coker_carrier_gain_weight=quotient_coordinate_robust_coker_carrier_gain_weight,
            quotient_coordinate_robust_coker_audit_penalty=quotient_coordinate_robust_coker_audit_penalty,
            quotient_coordinate_robust_coker_require_success=quotient_coordinate_robust_coker_require_success,
            carrier_quotient=carrier_quotient,
            carrier_quotient_merge_actions=carrier_quotient_merge_actions,
            carrier_quotient_merge_policy=carrier_quotient_merge_policy,
            carrier_quotient_ridge=carrier_quotient_ridge,
            carrier_quotient_max_mass=carrier_quotient_max_mass,
            carrier_quotient_cosine_threshold=carrier_quotient_cosine_threshold,
            carrier_quotient_min_states=carrier_quotient_min_states,
            carrier_quotient_top_action_scores=carrier_quotient_top_action_scores,
            carrier_quotient_margin_threshold=carrier_quotient_margin_threshold,
            audit_carrier_quotient_candidates=audit_carrier_quotient_candidates,
            carrier_quotient_audit_max_actions=carrier_quotient_audit_max_actions,
            carrier_quotient_accept_coker=carrier_quotient_accept_coker,
            carrier_quotient_robust_coker_accept=carrier_quotient_robust_coker_accept,
            carrier_quotient_accept_margin=carrier_quotient_accept_margin,
            carrier_quotient_accept_max_per_task=carrier_quotient_accept_max_per_task,
            carrier_quotient_accept_cost_weight=carrier_quotient_accept_cost_weight,
            carrier_quotient_accept_carrier_weight=carrier_quotient_accept_carrier_weight,
            carrier_quotient_robust_coker_holdout_fraction=carrier_quotient_robust_coker_holdout_fraction,
            carrier_quotient_robust_coker_uncertainty_weight=carrier_quotient_robust_coker_uncertainty_weight,
            carrier_quotient_robust_coker_carrier_gain_weight=carrier_quotient_robust_coker_carrier_gain_weight,
            carrier_quotient_robust_coker_audit_penalty=carrier_quotient_robust_coker_audit_penalty,
            carrier_quotient_robust_coker_require_success=carrier_quotient_robust_coker_require_success,
            action_geometry_use_quotient_normals=action_geometry_use_quotient_normals,
            contextual_congruence=contextual_congruence,
            contextual_congruence_context_mode=contextual_congruence_context_mode,
            contextual_congruence_no_carrier=contextual_congruence_no_carrier,
            contextual_congruence_min_count=contextual_congruence_min_count,
            contextual_congruence_cosine_threshold=contextual_congruence_cosine_threshold,
            contextual_congruence_distance_threshold=contextual_congruence_distance_threshold,
            contextual_congruence_min_context_jaccard=contextual_congruence_min_context_jaccard,
            contextual_probes=contextual_probes,
            contextual_probe_contexts=contextual_probe_contexts,
            contextual_probe_max_left=contextual_probe_max_left,
            contextual_probe_max_right=contextual_probe_max_right,
            contextual_probe_max_core=contextual_probe_max_core,
            contextual_probe_max_candidates=contextual_probe_max_candidates,
            contextual_probe_no_identity=contextual_probe_no_identity,
            contextual_probe_no_left=contextual_probe_no_left,
            contextual_probe_no_right=contextual_probe_no_right,
            audit_contextual_probe_candidates=audit_contextual_probe_candidates,
            contextual_probe_audit_max_actions=contextual_probe_audit_max_actions,
            contextual_probe_congruence=contextual_probe_congruence,
            contextual_probe_congruence_context_mode=contextual_probe_congruence_context_mode,
            contextual_probe_congruence_no_carrier=contextual_probe_congruence_no_carrier,
            contextual_probe_congruence_min_count=contextual_probe_congruence_min_count,
            contextual_probe_congruence_cosine_threshold=contextual_probe_congruence_cosine_threshold,
            contextual_probe_congruence_distance_threshold=contextual_probe_congruence_distance_threshold,
            contextual_probe_congruence_min_context_jaccard=contextual_probe_congruence_min_context_jaccard,
            contextual_probe_accept_coker=contextual_probe_accept_coker,
            contextual_probe_robust_coker_accept=contextual_probe_robust_coker_accept,
            contextual_probe_accept_margin=contextual_probe_accept_margin,
            contextual_probe_accept_max_per_task=contextual_probe_accept_max_per_task,
            contextual_probe_accept_cost_weight=contextual_probe_accept_cost_weight,
            contextual_probe_accept_carrier_weight=contextual_probe_accept_carrier_weight,
            contextual_probe_robust_coker_holdout_fraction=contextual_probe_robust_coker_holdout_fraction,
            contextual_probe_robust_coker_uncertainty_weight=contextual_probe_robust_coker_uncertainty_weight,
            contextual_probe_robust_coker_carrier_gain_weight=contextual_probe_robust_coker_carrier_gain_weight,
            contextual_probe_robust_coker_audit_penalty=contextual_probe_robust_coker_audit_penalty,
            contextual_probe_robust_coker_require_success=contextual_probe_robust_coker_require_success,
            response_quotient_registry=response_quotient_registry,
            response_quotient_min_members=response_quotient_min_members,
            response_quotient_min_quality=response_quotient_min_quality,
            response_quotient_project_actions=response_quotient_project_actions,
            response_quotient_annotate_only=response_quotient_annotate_only,
            response_quotient_merge_actions=response_quotient_merge_actions,
            response_quotient_merge_policy=response_quotient_merge_policy,
            frontier_normalize=frontier_normalize,
            frontier_max_prefixes=frontier_max_prefixes,
            frontier_include_identity=frontier_include_identity,
            registry_audit_max_actions=registry_audit_max_actions,
            registry_accept_margin=registry_accept_margin,
            registry_accept_max_per_task=registry_accept_max_per_task,
            promote_registry=promote_registry,
            premise_index=premise_index,
            audit_premise_candidates=audit_premise_candidates,
            premise_audit_max_actions=premise_audit_max_actions,
            carrier_accept=carrier_accept,
            carrier_accept_max_actions=carrier_accept_max_actions,
            promote_carrier_actions=promote_carrier_actions,
            ir_candidates=ir_candidates,
            ir_max_candidates=ir_max_candidates,
            audit_ir_candidates=audit_ir_candidates,
            ir_audit_max_actions=ir_audit_max_actions,
            ir_accept_coker=ir_accept_coker,
            carrier_matrix=carrier_matrix,
            carrier_matrix_budget=carrier_matrix_budget,
            carrier_matrix_keep_unsafe=carrier_matrix_keep_unsafe,
            carrier_matrix_merge_qgen=carrier_matrix_merge_qgen,
            carrier_matrix_qgen_patch_weight=carrier_matrix_qgen_patch_weight,
            carrier_matrix_qgen_require_safe=carrier_matrix_qgen_require_safe,
            carrier_matrix_qgen_audit_patches=carrier_matrix_qgen_audit_patches,
            carrier_matrix_qgen_patch_min_count=carrier_matrix_qgen_patch_min_count,
            carrier_matrix_qgen_patch_min_mean_delta=carrier_matrix_qgen_patch_min_mean_delta,
            carrier_matrix_qgen_patch_holdout_fraction=carrier_matrix_qgen_patch_holdout_fraction,
            carrier_matrix_qgen_patch_require_heldout=carrier_matrix_qgen_patch_require_heldout,
            failure_signatures=failure_signatures,
            audit_failure_signature_candidates=audit_failure_signature_candidates,
            failure_signature_audit_max_actions=failure_signature_audit_max_actions,
            failure_signature_accept_coker=failure_signature_accept_coker,
            failure_signature_accept_margin=failure_signature_accept_margin,
            failure_signature_accept_max_per_task=failure_signature_accept_max_per_task,
        )
        cli_main(args)

        next_actions = root / f"round_{r:02d}_actions_next.jsonl"
        merge_inputs: list[Path] = []
        if action_path:
            merge_inputs.append(Path(action_path))
        merge_inputs.extend([
            rdir / "registry_accepted_actions.jsonl",
            rdir / "failure_signature_accepted_actions.jsonl",
            rdir / "ir_accepted_actions.jsonl",
            rdir / "carrier_promoted_actions.jsonl",
        ])
        if qgen:
            policy = (qgen_merge_policy or "all").lower()
            if (rdir / "qgen_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "qgen_robust_accepted_actions.jsonl")
            if (rdir / "qgen_registry_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "qgen_registry_robust_accepted_actions.jsonl")
            if policy not in {"robust-only", "robust_only"}:
                if (rdir / "qgen_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "qgen_accepted_actions.jsonl")
                elif (rdir / "qgen" / "qgen_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "qgen" / "qgen_accepted_actions.jsonl")
                if (rdir / "qgen_registry_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "qgen_registry_accepted_actions.jsonl")
            if qgen_merge_actions and policy not in {"robust-only", "robust_only", "accepted-only", "accepted_only"}:
                merge_inputs.append(rdir / "qgen" / "qgen_context_candidates.jsonl")
                merge_inputs.append(rdir / "qgen_registry_candidates.jsonl")
        if contextual_probes:
            cp_policy = (contextual_probe_merge_policy or "robust-only").lower()
            if (rdir / "contextual_probe_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "contextual_probe_robust_accepted_actions.jsonl")
            if cp_policy not in {"robust-only", "robust_only"}:
                if (rdir / "contextual_probe_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "contextual_probe_accepted_actions.jsonl")
            if contextual_probe_merge_actions and cp_policy not in {"robust-only", "robust_only", "accepted-only", "accepted_only"}:
                if (rdir / "contextual_probes" / "contextual_probe_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "contextual_probes" / "contextual_probe_candidates.jsonl")
        if action_geometry:
            ag_policy = (action_geometry_merge_policy or "robust-only").lower()
            if (rdir / "action_geometry_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "action_geometry_robust_accepted_actions.jsonl")
            if ag_policy not in {"robust-only", "robust_only"}:
                if (rdir / "action_geometry_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "action_geometry_accepted_actions.jsonl")
            if action_geometry_merge_actions and ag_policy not in {"robust-only", "robust_only", "accepted-only", "accepted_only"}:
                if (rdir / "action_geometry" / "action_geometry_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "action_geometry" / "action_geometry_candidates.jsonl")
                elif (rdir / "action_geometry_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "action_geometry_candidates.jsonl")
        if response_quotient_registry and response_quotient_merge_actions:
            rq_policy = (response_quotient_merge_policy or "representatives").lower()
            if rq_policy in {"representatives", "all"} and (rdir / "response_quotient" / "response_quotient_representatives.jsonl").exists():
                merge_inputs.append(rdir / "response_quotient" / "response_quotient_representatives.jsonl")
            if rq_policy in {"projected", "all"} and (rdir / "response_quotient_projected_actions.jsonl").exists():
                merge_inputs.append(rdir / "response_quotient_projected_actions.jsonl")
        if quotient_coordinates:
            qc_policy = (quotient_coordinate_merge_policy or "robust-only").lower()
            if (rdir / "quotient_coordinate_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "quotient_coordinate_robust_accepted_actions.jsonl")
            if qc_policy not in {"robust-only", "robust_only"}:
                if (rdir / "quotient_coordinate_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "quotient_coordinate_accepted_actions.jsonl")
            if quotient_coordinate_merge_actions and qc_policy not in {"robust-only", "robust_only", "accepted-only", "accepted_only"}:
                if (rdir / "quotient_coordinates" / "quotient_coordinate_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "quotient_coordinates" / "quotient_coordinate_candidates.jsonl")
                if (rdir / "quotient_coordinate_registry_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "quotient_coordinate_registry_candidates.jsonl")
        if carrier_quotient:
            cq_policy = (carrier_quotient_merge_policy or "robust-only").lower()
            if (rdir / "carrier_quotient_robust_accepted_actions.jsonl").exists():
                merge_inputs.append(rdir / "carrier_quotient_robust_accepted_actions.jsonl")
            if cq_policy not in {"robust-only", "robust_only"}:
                if (rdir / "carrier_quotient_accepted_actions.jsonl").exists():
                    merge_inputs.append(rdir / "carrier_quotient_accepted_actions.jsonl")
            if carrier_quotient_merge_actions and cq_policy not in {"robust-only", "robust_only", "accepted-only", "accepted_only"}:
                if (rdir / "carrier_quotient" / "carrier_quotient_candidates.jsonl").exists():
                    merge_inputs.append(rdir / "carrier_quotient" / "carrier_quotient_candidates.jsonl")
        if premise_index and merge_premise_actions:
            merge_inputs.append(rdir / "premise_actions.jsonl")
        if ir_candidates and not (rdir / "ir_accepted_actions.jsonl").exists():
            merge_inputs.append(rdir / "ir_candidates.jsonl")
        if source_budget:
            sb_policy = (source_budget_merge_policy or 'scheduled-only').lower()
            if (rdir / 'source_budget' / 'source_budget_actions.jsonl').exists():
                merge_inputs.append(rdir / 'source_budget' / 'source_budget_actions.jsonl')
            if source_budget_merge_actions and sb_policy == 'all':
                if (rdir / 'source_budget_audit' / 'responses.jsonl').exists():
                    pass
        if carrier_matrix:
            merge_inputs.append(rdir / "carrier_safe_actions.jsonl")
        merge_meta = _merge_actions(merge_inputs, next_actions, max_actions=next_action_cap)
        n_next = int(merge_meta.get("n_actions", 0))
        if n_next == 0 and (rdir / "registry_candidates.jsonl").exists():
            merge_meta = _merge_actions([rdir / "registry_candidates.jsonl"], next_actions, max_actions=next_action_cap)
            n_next = int(merge_meta.get("n_actions", 0))
        action_path = str(next_actions) if n_next > 0 else action_path
        summaries.append(_round_metrics(rdir, merge_inputs, r=r, actions_in=actions if r == 0 else summaries[-1].actions_next, actions_next=next_actions, n_next=n_next))
        if summaries[-1].merged_sources is None:
            summaries[-1].merged_sources = {}
        summaries[-1].merged_sources["__merge_out__"] = n_next

    realized_report = None
    if qgen:
        try:
            realized_report = collect_qgen_realized_calibration(root, out_json=root / "qgen_realized_calibration.json", out_csv=root / "qgen_realized_calibration.csv")
        except Exception as exc:
            realized_report = {"error": str(exc), "canonical_status": "realized_response_chart_failed"}
    rep = {"tasks": tasks, "initial_actions": actions, "rounds": [s.to_dict() for s in summaries]}
    if realized_report is not None:
        rep["qgen_realized_calibration"] = realized_report.get("summary", realized_report)
    poms_report = None
    if any((root / f"round_{i:02d}" / "qgen_acceptance_lineage.json").exists() for i in range(rounds)) or (root / "qgen_realized_calibration.json").exists():
        try:
            poms_report = collect_poms_status(root, out_json=root / "poms_status_report.json", out_jsonl=root / "poms_status_rows.jsonl", out_csv=root / "poms_status_rows.csv")
        except Exception as exc:
            poms_report = {"error": str(exc), "canonical_status": "poms_status_chart_failed"}
    if poms_report is not None:
        rep["poms_status"] = poms_report.get("summary", poms_report)
        generated_evidence_paths = list(poms_promotion_evidence or [])
        if poms_generate_evidence:
            try:
                ev_report = generate_promotion_evidence(
                    root,
                    out_json=root / "promotion_evidence_report.json",
                    out_jsonl=root / "promotion_evidence_rows.jsonl",
                    out_poms=root / "promotion_evidence_for_poms.jsonl",
                    out_csv=root / "promotion_evidence_rows.csv",
                    min_relative_residual=poms_evidence_min_relative_residual,
                    min_residual_norm=poms_evidence_min_residual_norm,
                    min_support_count=poms_evidence_min_support_count,
                    min_margin=poms_evidence_min_margin,
                    min_robust_margin=poms_evidence_min_robust_margin,
                    least_repair_epsilon=poms_evidence_least_repair_epsilon,
                )
                rep["promotion_evidence"] = ev_report.get("summary", ev_report)
                generated_evidence_paths.append(str(root / "promotion_evidence_for_poms.jsonl"))
            except Exception as exc:
                rep["promotion_evidence"] = {"error": str(exc), "canonical_status": "promotion_evidence_generation_failed"}
        if poms_promote:
            try:
                prom_report = collect_poms_promotion(
                    root,
                    evidence=generated_evidence_paths or None,
                    out_json=root / "poms_promotion_report.json",
                    out_jsonl=root / "poms_promotion_rows.jsonl",
                    out_csv=root / "poms_promotion_rows.csv",
                    out_promoted_actions=root / "poms_promoted_actions.jsonl",
                    global_parent_nonpaid=poms_promote_parent_nonpaid,
                    global_dual_certificate=poms_promote_dual_certificate,
                    global_least_repair=poms_promote_least_repair,
                    declare_canonical=poms_declare_canonical,
                )
                rep["poms_promotion"] = prom_report.get("summary", prom_report)
            except Exception as exc:
                rep["poms_promotion"] = {"error": str(exc), "canonical_status": "poms_promotion_chart_failed"}
    if audit_db:
        try:
            db_path = Path(audit_db_path) if audit_db_path else (root / "audit.db")
            db_summary = build_audit_db(root, db_path, reset=not audit_db_append)
            rep["audit_db_summary"] = db_summary
            rep["audit_db"] = str(db_path)
        except Exception as exc:
            rep["audit_db_summary"] = {"error": str(exc), "canonical_status": "audit_db_chart_failed"}
    (root / "iterate_summary.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep


__all__ = ["run_iterative_pipeline", "IterationRoundSummary"]
