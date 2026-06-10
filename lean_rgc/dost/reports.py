from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import math

from ..schemas import stable_hash, write_jsonl
from .common import (
    SCHEMA_PRIMITIVE_OBSERVABLE,
    SCHEMA_BOUNDED_TRANSCRIPT,
    SCHEMA_FEATURE_CLOSURE,
    SCHEMA_FEATURE_VALUE,
    SCHEMA_FEATURE_SELECTION,
    SCHEMA_AUTO_PLAN,
    SCHEMA_DOST_AUDIT,
    DEFAULT_PRIMITIVE_OBSERVABLES,
    _json_dump,
    _json_load,
    _read_rows,
    _safe_float,
    _as_list,
    _path_if_exists,
    _first_existing,
    _ratio,
    _score_avg,
    _json_bytes,
    _row_identity,
    _status_counter,
    _class_member_count,
    _row_tactic_text,
    _is_macro_policy_row,
    _is_structural_row,
    _nf_status,
    _is_typed_nf_status,
    _matrix_metrics,
)



def _discover_audit_inputs(
    run_dir: str | Path | None = None,
    **overrides: str | Path | None,
) -> dict[str, Path | None]:
    root = Path(run_dir) if run_dir else None
    pc = root / "premise_contextual" if root else None
    pca = root / "premise_contextual_audit" if root else None
    audit = root / "audit" if root else None
    taxonomy_dir = pc / "face_taxonomy" if pc else None
    tower_dir = pc / "obstruction_tower" if pc else None
    dost_dir = pc / "dost" if pc else None
    return {
        "server_summary_path": _first_existing(overrides.get("server_summary_path"), pca / "server_summary.json" if pca else None, pca / "summary.json" if pca else None, audit / "summary.json" if audit else None),
        "fingerprint_report_path": _first_existing(overrides.get("fingerprint_report_path"), pc / "premise_contextual_fingerprint_report.json" if pc else None),
        "fingerprints_path": _first_existing(overrides.get("fingerprints_path"), pc / "premise_contextual_fingerprints.jsonl" if pc else None),
        "premise_use_rows_path": _first_existing(overrides.get("premise_use_rows_path"), pc / "premise_use_rows.jsonl" if pc else None),
        "classes_path": _first_existing(overrides.get("classes_path"), pc / "premise_quotient_classes.jsonl" if pc else None),
        "validation_rows_path": _first_existing(overrides.get("validation_rows_path"), pc / "premise_quotient_validation_rows.jsonl" if pc else None),
        "validation_report_path": _first_existing(overrides.get("validation_report_path"), pc / "premise_quotient_validation_report.json" if pc else None),
        "taxonomy_path": _first_existing(overrides.get("taxonomy_path"), taxonomy_dir / "dual_face_taxonomy.jsonl" if taxonomy_dir else None),
        "taxonomy_report_path": _first_existing(overrides.get("taxonomy_report_path"), taxonomy_dir / "dual_face_taxonomy_report.json" if taxonomy_dir else None),
        "retrieval_faces_path": _first_existing(overrides.get("retrieval_faces_path"), taxonomy_dir / "retrieval_allowed_faces.jsonl" if taxonomy_dir else None),
        "tower_summary_path": _first_existing(overrides.get("tower_summary_path"), tower_dir / "tower_summary.json" if tower_dir else None),
        "tower_next_actions_path": _first_existing(overrides.get("tower_next_actions_path"), tower_dir / "tower_next_actions.jsonl" if tower_dir else None),
        "dost_report_path": _first_existing(overrides.get("dost_report_path"), dost_dir / "dost_obstruction_report.json" if dost_dir else None),
        "feature_selection_report_path": _first_existing(overrides.get("feature_selection_report_path"), dost_dir / "feature_selection_report.json" if dost_dir else None),
        "selected_features_path": _first_existing(overrides.get("selected_features_path"), dost_dir / "selected_features.jsonl" if dost_dir else None),
        "responses_path": _first_existing(overrides.get("responses_path"), pca / "responses.jsonl" if pca else None, audit / "responses.jsonl" if audit else None),
        "actions_path": _first_existing(overrides.get("actions_path"), root / "actions.jsonl" if root else None),
    }


def _server_summary_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    n_responses = int(_safe_float(summary.get("n_responses") or summary.get("responses") or 0))
    n_failures = int(_safe_float(summary.get("n_failures") or summary.get("failures") or 0))
    timeout_count = int(_safe_float(summary.get("timeout_count") or summary.get("timeouts") or 0))
    timeout_rate = _safe_float(summary.get("timeout_rate"), _ratio(timeout_count, n_responses))
    cache_hits = int(_safe_float(summary.get("context_cache_hits") or summary.get("kernel_context_cache_hits") or 0))
    kernel_cache = bool(summary.get("kernel_context_cache") or summary.get("context_cache_enabled") or cache_hits > 0)
    baseline_missing = int(_safe_float(summary.get("baseline_missing") or summary.get("n_baseline_missing") or 0))
    source_check_calls = int(_safe_float(summary.get("source_check_calls") or summary.get("source_checks") or 0))
    return {
        "stateful_kernel_rpc": bool(summary.get("stateful_kernel_rpc_audit") or summary.get("kernel_rpc_enabled") or summary.get("kernel_rpc") or kernel_cache),
        "kernel_context_cache": kernel_cache,
        "context_cache_hits": cache_hits,
        "baseline_missing": baseline_missing,
        "timeout_rate": round(timeout_rate, 6),
        "n_responses": n_responses,
        "n_failures": n_failures,
        "source_check_calls": source_check_calls,
        "score": "green_pilot_yellow_certificate" if baseline_missing == 0 and timeout_rate <= 0.02 and n_failures == 0 else "yellow_or_red_substrate",
    }


def _proof_effect_from_responses(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "prove_rate": None,
            "partial_progress_rate": None,
            "fail_rate": None,
            "retrieved_success_rate": None,
            "oracle_topk_coverage": None,
            "cost_per_success": None,
        }
    success = 0
    partial = 0
    fail = 0
    total_cost = 0.0
    for row in rows:
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        cost = row.get("cost") if isinstance(row.get("cost"), dict) else {}
        status = str(row.get("status") or row.get("result_status") or response.get("status") or "").lower()
        if status == "success" or bool(row.get("success")):
            success += 1
        elif status == "partial":
            partial += 1
        elif status in {"fail", "failure", "timeout", "error"}:
            fail += 1
        total_cost += _safe_float(row.get("elapsed_ms") or cost.get("elapsed_ms"))
    n = len(rows)
    return {
        "prove_rate": round(success / n, 6),
        "partial_progress_rate": round(partial / n, 6),
        "fail_rate": round(fail / n, 6),
        "retrieved_success_rate": None,
        "oracle_topk_coverage": None,
        "cost_per_success": round(total_cost / success, 6) if success else None,
    }


def _failure_attributions(
    responses: list[dict[str, Any]],
    *,
    typed_nf_rate: float,
    retrieval_allowed_count: int,
    tower_next_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not responses:
        return []
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in responses:
        task_id = str(row.get("task_id") or row.get("goal_state_id") or row.get("state_id") or row.get("candidate_id") or "unknown")
        by_task[task_id].append(row)
    action_kinds = Counter(str(r.get("action_kind") or r.get("next_action_kind") or r.get("kind") or "unknown") for r in tower_next_actions)
    out: list[dict[str, Any]] = []
    for task_id, task_rows in sorted(by_task.items()):
        has_success = any(str(r.get("status") or "").lower() == "success" or bool(r.get("success")) for r in task_rows)
        if has_success:
            failure_kind = "not_failed_or_oracle_success_exists"
            suspected_order = None
            suspected_face = None
        elif retrieval_allowed_count <= 0:
            failure_kind = "retrieval_blocked_no_safe_face"
            suspected_order = 0 if typed_nf_rate < 0.2 else 1
            suspected_face = "validated_retrieval_face_missing"
        elif typed_nf_rate < 0.2:
            failure_kind = "action_universe_poverty"
            suspected_order = 1
            suspected_face = "typed_premise_use_missing"
        else:
            failure_kind = "retrieval_or_scheduling_failure"
            suspected_order = None
            suspected_face = "face_matching_or_budget_issue"
        out.append(
            {
                "schema_version": SCHEMA_DOST_AUDIT,
                "task_id": task_id,
                "failed": not has_success,
                "oracle_success_exists": has_success,
                "retrieved_success_exists": None,
                "failure_kind": failure_kind,
                "suspected_missing_order": suspected_order,
                "suspected_missing_face": suspected_face,
                "evidence": {
                    "typed_nf_rate": round(typed_nf_rate, 6),
                    "retrieval_allowed_faces": retrieval_allowed_count,
                    "tower_next_action_counts": dict(sorted(action_kinds.items())),
                },
                "canonical_status": "finite_failure_attribution_chart_not_canonical",
            }
        )
    return out


def build_dost_audit_reports(
    out_dir: str | Path,
    *,
    run_dir: str | Path | None = None,
    server_summary_path: str | Path | None = None,
    fingerprint_report_path: str | Path | None = None,
    fingerprints_path: str | Path | None = None,
    premise_use_rows_path: str | Path | None = None,
    classes_path: str | Path | None = None,
    validation_rows_path: str | Path | None = None,
    validation_report_path: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    taxonomy_report_path: str | Path | None = None,
    retrieval_faces_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    dost_report_path: str | Path | None = None,
    feature_selection_report_path: str | Path | None = None,
    selected_features_path: str | Path | None = None,
    responses_path: str | Path | None = None,
    actions_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build finite DOST audit ledgers from existing run artifacts."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    inputs = _discover_audit_inputs(
        run_dir,
        server_summary_path=server_summary_path,
        fingerprint_report_path=fingerprint_report_path,
        fingerprints_path=fingerprints_path,
        premise_use_rows_path=premise_use_rows_path,
        classes_path=classes_path,
        validation_rows_path=validation_rows_path,
        validation_report_path=validation_report_path,
        taxonomy_path=taxonomy_path,
        taxonomy_report_path=taxonomy_report_path,
        retrieval_faces_path=retrieval_faces_path,
        tower_summary_path=tower_summary_path,
        tower_next_actions_path=tower_next_actions_path,
        dost_report_path=dost_report_path,
        feature_selection_report_path=feature_selection_report_path,
        selected_features_path=selected_features_path,
        responses_path=responses_path,
        actions_path=actions_path,
    )
    server_summary = _json_load(inputs["server_summary_path"])
    fingerprint_report = _json_load(inputs["fingerprint_report_path"])
    validation_report = _json_load(inputs["validation_report_path"])
    taxonomy_report = _json_load(inputs["taxonomy_report_path"])
    tower_summary = _json_load(inputs["tower_summary_path"])
    dost_report = _json_load(inputs["dost_report_path"])
    feature_selection_report = _json_load(inputs["feature_selection_report_path"])

    fingerprints = _read_rows(inputs["fingerprints_path"])
    premise_rows = _read_rows(inputs["premise_use_rows_path"])
    actions = _read_rows(inputs["actions_path"])
    row_universe = premise_rows if premise_rows else actions
    classes = _read_rows(inputs["classes_path"])
    validation_rows = _read_rows(inputs["validation_rows_path"])
    taxonomy = _read_rows(inputs["taxonomy_path"])
    retrieval_faces = _read_rows(inputs["retrieval_faces_path"])
    tower_next_actions = _read_rows(inputs["tower_next_actions_path"])
    selected_features = _read_rows(inputs["selected_features_path"])
    responses = _read_rows(inputs["responses_path"])

    kernel = _server_summary_metrics(server_summary)
    matrix_metrics = _matrix_metrics(fingerprints)
    validation_counts = Counter(validation_report.get("validation_status_counts") or {})
    validation_counts.update(_status_counter(validation_rows))
    class_sizes = [_class_member_count(row) for row in classes]
    n_classes = len(classes) or int(_safe_float(validation_report.get("n_classes") or taxonomy_report.get("n_classes") or 0))
    singleton_count = sum(1 for x in class_sizes if x <= 1)
    if not classes and validation_counts.get("singleton_vacuously_stable_not_informative"):
        singleton_count = int(validation_counts.get("singleton_vacuously_stable_not_informative"))
    split_count = int(validation_counts.get("split_suggested", 0))
    carrier_mixed_count = int(validation_counts.get("carrier_unsafe_mixed_class", 0))
    heldout_validated_count = int(validation_counts.get("heldout_validated_premise_class", 0))
    multi_member_classes = sum(1 for x in class_sizes if x > 1)
    validated_multi_member_rate = _ratio(heldout_validated_count, max(1, multi_member_classes))

    n_rows = len(fingerprints) or int(_safe_float(fingerprint_report.get("n_fingerprints") or fingerprint_report.get("n_rows") or 0))
    n_context_pairs = int(
        _safe_float(
            fingerprint_report.get("n_unique_context_pairs")
            or fingerprint_report.get("context_pairs")
            or fingerprint_report.get("n_context_pairs")
            or 0
        )
    )
    row_degenerate = bool(fingerprint_report.get("row_degenerate", False))
    column_degenerate = bool(fingerprint_report.get("column_degenerate", False))

    nf_statuses = Counter(_nf_status(row) for row in row_universe)
    typed_rows = sum(1 for row in row_universe if _is_typed_nf_status(_nf_status(row)))
    kernel_observed_rows = sum(1 for row in row_universe if "kernel" in _nf_status(row).lower())
    macro_rows = sum(1 for row in row_universe if _is_macro_policy_row(row))
    structural_rows = sum(1 for row in row_universe if _is_structural_row(row))
    n_row_universe = len(row_universe)
    typed_nf_rate = _ratio(typed_rows, n_row_universe)
    kernel_observed_nf_rate = _ratio(kernel_observed_rows, n_row_universe)
    macro_policy_fraction = _ratio(macro_rows, n_row_universe)
    structural_tactic_fraction = _ratio(structural_rows, n_row_universe)

    retrieval_allowed_count = len(retrieval_faces) or int(_safe_float(taxonomy_report.get("n_retrieval_allowed_faces") or 0))
    retrieval_blocker_counts = Counter(taxonomy_report.get("retrieval_blocker_counts") or {})
    dual_source_counts = Counter(taxonomy_report.get("dual_source_counts") or {})
    allowed_with_blockers = 0
    carrier_safe_allowed = 0
    for face in retrieval_faces:
        status = face.get("status") if isinstance(face.get("status"), dict) else {}
        blockers = _as_list(status.get("retrieval_blockers"))
        if blockers:
            allowed_with_blockers += 1
        if status.get("carrier_safe", False):
            carrier_safe_allowed += 1
    carrier_safe_retrieval_rate = _ratio(carrier_safe_allowed, len(retrieval_faces)) if retrieval_faces else 0.0

    tower_action_counts = Counter(str(row.get("action_kind") or row.get("next_action_kind") or row.get("kind") or "unknown") for row in tower_next_actions)
    tower_reason_counts = Counter(str(row.get("reason") or row.get("selection_reason") or row.get("next_reason") or "unknown") for row in tower_next_actions)
    promotion_counts = Counter(tower_summary.get("promotion_level_counts") or {})
    boundary_counts = Counter(tower_summary.get("boundary_status_counts") or {})
    proof_effect = _proof_effect_from_responses(responses)

    kernel_score = _score_avg(
        [
            1.0 if kernel["baseline_missing"] == 0 else 0.0,
            1.0 if kernel["timeout_rate"] <= 0.02 else 0.0,
            1.0 if kernel["n_failures"] == 0 else 0.0,
            1.0 if kernel["kernel_context_cache"] or kernel["stateful_kernel_rpc"] else 0.0,
        ]
    )
    typed_object_score = round(min(1.0, 0.7 * typed_nf_rate + 0.3 * kernel_observed_nf_rate), 4)
    quotient_quality_score = _score_avg(
        [
            validated_multi_member_rate,
            1.0 - _ratio(split_count, max(1, n_classes)),
            1.0 - _ratio(carrier_mixed_count, max(1, n_classes)),
            1.0 - _ratio(singleton_count, max(1, n_classes)),
            1.0 if retrieval_allowed_count > 0 else 0.0,
        ]
    )
    retrieval_safety_score = (
        _score_avg([1.0 if allowed_with_blockers == 0 else 0.0, carrier_safe_retrieval_rate, 1.0 if retrieval_allowed_count > 0 else 0.0])
        if retrieval_allowed_count > 0
        else 0.05
    )
    action_family_entropy = 0.0
    if n_row_universe:
        family_counts = [macro_rows, structural_rows, max(0, n_row_universe - macro_rows - structural_rows)]
        total = sum(family_counts)
        if total:
            probs = [c / total for c in family_counts if c > 0]
            action_family_entropy = -sum(p * math.log(p) for p in probs) / math.log(3)
    expressivity_score = round(min(1.0, 0.45 * typed_nf_rate + 0.25 * action_family_entropy + 0.30 * _ratio(retrieval_allowed_count, max(1, n_classes))), 4)
    boundary_resolved_rate = _ratio(boundary_counts.get("resolved", 0), sum(boundary_counts.values()))
    tower_score = round(min(1.0, 0.6 * boundary_resolved_rate + 0.4 * _ratio(sum(promotion_counts.values()), max(1, len(taxonomy)))), 4)
    btr_score = round(
        0.20 * kernel_score
        + 0.20 * typed_object_score
        + 0.20 * quotient_quality_score
        + 0.15 * retrieval_safety_score
        + 0.15 * expressivity_score
        + 0.10 * tower_score,
        4,
    )
    overall = "not_big_theorem_ready" if btr_score < 0.35 else ("pilot_ready_not_canonical" if btr_score < 0.65 else "candidate_ready_requires_replay")

    invariant_ledger = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "kernel_substrate": kernel,
        "bivariate_matrix": {
            "n_rows": n_rows,
            "n_context_pairs": n_context_pairs,
            "row_degenerate": row_degenerate,
            "column_degenerate": column_degenerate,
            "effective_rank": matrix_metrics.get("effective_rank"),
            "top_singular_value_ratio": matrix_metrics.get("top_singular_value_ratio"),
            "row_entropy": matrix_metrics.get("row_entropy"),
            "column_entropy": matrix_metrics.get("column_entropy"),
            "score": "green_substrate" if n_rows and not row_degenerate and not column_degenerate else "yellow_or_red_substrate",
        },
        "class_quality": {
            "n_classes": n_classes,
            "split_suggested": split_count,
            "carrier_unsafe_mixed": carrier_mixed_count,
            "singleton_vacuous": singleton_count,
            "heldout_validated_multi_member": heldout_validated_count,
            "strict_retrieval_ready": retrieval_allowed_count > 0 and allowed_with_blockers == 0,
            "score": "green" if quotient_quality_score >= 0.7 else ("yellow" if quotient_quality_score >= 0.4 else "red"),
        },
        "canonical_status": "dost_audit_invariant_ledger_finite_chart_not_canonical",
    }

    blockers: list[dict[str, Any]] = []
    if carrier_mixed_count:
        blockers.append({"blocker": "carrier_unsafe_mixed_class", "count": carrier_mixed_count, "reason": "carrier safety is not yet a hard enough quotient constraint", "effect_on_proof": "unsafe or debt-producing actions can be retrieved as if equivalent", "next_action": "hard_split_carrier"})
    if split_count:
        blockers.append({"blocker": "split_suggested_overmerge", "count": split_count, "reason": "finite chart merges rows with heldout response diameter above threshold", "effect_on_proof": "representative retrieval becomes unstable across contexts", "next_action": "generate_separator_contexts"})
    if n_classes and _ratio(singleton_count, n_classes) >= 0.4:
        blockers.append({"blocker": "singleton_vacuous_classes", "count": singleton_count, "reason": "member_count=1 gives vacuous stability rather than class-level robustness", "effect_on_proof": "retrieval has witness actions but little generalization evidence", "next_action": "generate_face_neighbor_rows"})
    if typed_nf_rate < 0.3:
        blockers.append({"blocker": "textual_row_universe", "count": n_row_universe - typed_rows, "reason": "premise-use rows are not mostly typed/kernel-elaborated premise-use objects", "effect_on_proof": "the action universe remains local tactic pilot rather than theorem-indexed Mathlib proof search", "next_action": "generate_typed_premise_rows"})
    if retrieval_allowed_count <= 0:
        blockers.append({"blocker": "no_strict_retrieval_faces", "count": 0, "reason": "no heldout-validated carrier-safe faces passed the strict retrieval gate", "effect_on_proof": "face-mediated retrieval should remain blocked", "next_action": "block_retrieval"})
    if kernel.get("source_check_calls", 0) <= 0:
        blockers.append({"blocker": "proof_certificate_weak", "count": 0, "reason": "kernel-backed audit is present but source/replay certificate calls are absent or unknown", "effect_on_proof": "pilot observations should not be treated as final proof certificates", "next_action": "run_replay_certificate_audit"})

    proof_blocker_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "primary_blockers": blockers,
        "blocker_counts": dict(sorted(Counter(b["blocker"] for b in blockers).items())),
        "canonical_status": "proof_blocker_report_finite_chart_not_canonical",
    }
    action_poverty_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "row_universe": {
            "n_rows": n_row_universe,
            "nf_status_counts": dict(sorted(nf_statuses.items())),
            "macro_policy_fraction": round(macro_policy_fraction, 6),
            "structural_tactic_fraction": round(structural_tactic_fraction, 6),
            "typed_premise_use_fraction": round(typed_nf_rate, 6),
            "kernel_elaborated_instantiation_rate": round(kernel_observed_nf_rate, 6),
        },
        "tier_scores": {
            "tier0_local_close": None,
            "tier1_typed_premise": None,
            "tier2_lemma_like": None,
            "tier3_plan_like": None,
            "tier4_transfer_like": None,
        },
        "diagnosis": "action_universe_is_local_tactic_pilot_not_big_theorem_ready" if typed_nf_rate < 0.3 else "typed_action_universe_present_but_requires_tiered_benchmark",
        "canonical_status": "action_poverty_report_finite_chart_not_canonical",
    }
    retrieval_safety_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "retrieval_allowed_faces": retrieval_allowed_count,
        "retrieval_used_bad_class_count": None,
        "retrieval_allowed_with_blockers": allowed_with_blockers,
        "carrier_safe_retrieval_rate": round(carrier_safe_retrieval_rate, 6),
        "retrieval_blocker_counts": dict(sorted(retrieval_blocker_counts.items())),
        "bad_class_retrieval_should_be_zero": True,
        "diagnosis": "retrieval_not_ready" if retrieval_allowed_count <= 0 else "retrieval_gate_has_candidate_faces",
        "canonical_status": "retrieval_safety_report_finite_chart_not_canonical",
    }
    big_theorem_readiness = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "kernel_substrate_score": kernel_score,
        "typed_object_score": typed_object_score,
        "quotient_quality_score": quotient_quality_score,
        "retrieval_safety_score": round(retrieval_safety_score, 4),
        "expressivity_score": expressivity_score,
        "tower_score": tower_score,
        "weighted_score": btr_score,
        "overall": overall,
        "reason": [b["blocker"] for b in blockers],
        "canonical_status": "big_theorem_readiness_score_is_audit_heuristic_not_canonical",
    }

    diagnosis: list[str] = []
    if kernel_score >= 0.75:
        diagnosis.append("substrate_ok")
    if n_rows and not row_degenerate and not column_degenerate:
        diagnosis.append("row_universe_non_degenerate_but_sparse" if n_rows < 50 else "row_universe_non_degenerate")
    if typed_nf_rate < 0.3:
        diagnosis.append("typed_premise_use_missing")
    if carrier_mixed_count:
        diagnosis.append("carrier_safe_gate_needed")
    if retrieval_allowed_count <= 0:
        diagnosis.append("retrieval_not_ready")
    if overall == "not_big_theorem_ready":
        diagnosis.append("not_big_theorem_ready")

    audit_dashboard = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "run_id": stable_hash({k: str(v) if v else None for k, v in inputs.items()}, 12),
        "substrate": {"kernel_rpc": kernel["stateful_kernel_rpc"], "baseline_missing": kernel["baseline_missing"], "timeout_rate": kernel["timeout_rate"], "cache_hits": kernel["context_cache_hits"], "replay_pass_rate": None},
        "row_universe": {"n_rows": n_rows, "typed_row_ratio": round(typed_nf_rate, 6), "singleton_rate": round(_ratio(singleton_count, max(1, n_classes)), 6), "row_rank": matrix_metrics.get("effective_rank"), "macro_policy_ratio": round(macro_policy_fraction, 6)},
        "context_universe": {"n_contexts": int(_safe_float(fingerprint_report.get("n_contexts") or 0)), "n_context_pairs": n_context_pairs, "split_suggested": split_count, "avg_sep_gain": None},
        "quotient_quality": {"n_classes": n_classes, "heldout_validated": heldout_validated_count, "split_suggested": split_count, "carrier_unsafe_mixed": carrier_mixed_count, "singleton_vacuous": singleton_count, "retrieval_allowed_classes": retrieval_allowed_count},
        "dost": {"n_faces": len(taxonomy) or int(_safe_float(taxonomy_report.get("n_taxonomy_faces") or 0)), "dual_source_counts": dict(sorted(dual_source_counts.items())), "tower_next_action_counts": dict(sorted(tower_action_counts.items())), "tower_next_reason_counts": dict(sorted(tower_reason_counts.items())), "retrieval_allowed_faces": retrieval_allowed_count, "promotion_levels": dict(sorted(promotion_counts.items()))},
        "proof_effect": proof_effect,
        "feature_selection": {"n_selected_features": len(selected_features) or int(_safe_float(feature_selection_report.get("n_selected") or 0)), "report": str(inputs["feature_selection_report_path"]) if inputs["feature_selection_report_path"] else None},
        "diagnosis": diagnosis,
        "canonical_status": "audit_dashboard_finite_chart_not_canonical",
    }
    failure_rows = _failure_attributions(responses, typed_nf_rate=typed_nf_rate, retrieval_allowed_count=retrieval_allowed_count, tower_next_actions=tower_next_actions)

    artifacts = {
        "invariant_ledger": out_path / "invariant_ledger.json",
        "proof_blocker_report": out_path / "proof_blocker_report.json",
        "action_poverty_report": out_path / "action_poverty_report.json",
        "big_theorem_readiness": out_path / "big_theorem_readiness.json",
        "dost_obstruction_report": out_path / "dost_obstruction_report.json",
        "retrieval_safety_report": out_path / "retrieval_safety_report.json",
        "audit_dashboard": out_path / "audit_dashboard.json",
        "failure_attribution": out_path / "failure_attribution.jsonl",
    }
    _json_dump(invariant_ledger, artifacts["invariant_ledger"])
    _json_dump(proof_blocker_report, artifacts["proof_blocker_report"])
    _json_dump(action_poverty_report, artifacts["action_poverty_report"])
    _json_dump(big_theorem_readiness, artifacts["big_theorem_readiness"])
    _json_dump(retrieval_safety_report, artifacts["retrieval_safety_report"])
    _json_dump(audit_dashboard, artifacts["audit_dashboard"])
    write_jsonl(artifacts["failure_attribution"], failure_rows)

    obstruction_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "source_dost_report": dost_report,
        "primary_blockers": blockers,
        "dual_source_counts": dict(sorted(dual_source_counts.items())),
        "tower_next_action_counts": dict(sorted(tower_action_counts.items())),
        "selected_feature_count": len(selected_features) or int(_safe_float(feature_selection_report.get("n_selected") or 0)),
        "diagnosis": diagnosis,
        "canonical_status": "dost_obstruction_audit_report_finite_chart_not_canonical",
    }
    _json_dump(obstruction_report, artifacts["dost_obstruction_report"])
    summary = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "out_dir": str(out_path),
        "inputs": {k: str(v) if v else None for k, v in inputs.items()},
        "n_blockers": len(blockers),
        "big_theorem_readiness": overall,
        "weighted_score": btr_score,
        "artifacts": {k: str(v) for k, v in artifacts.items()},
        "canonical_status": "dost_audit_report_bundle_finite_chart_not_canonical",
    }
    _json_dump(summary, out_path / "audit_report_summary.json")
    return summary


__all__ = [
    "build_dost_audit_reports",
]
