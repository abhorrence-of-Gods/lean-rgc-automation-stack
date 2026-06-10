from __future__ import annotations

from pathlib import Path
from typing import Any

import json

from ..schemas import stable_hash
from .compile_experiment import compile_experiment_from_auto_plan
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



def _tower_action_candidate(row: dict[str, Any]) -> dict[str, Any]:
    kind = str(row.get("action_kind") or "")
    mapped = {
        "hard_split_face": "hard_split_carrier",
        "generate_context": "generate_separator_contexts",
        "generate_object": "generate_tower_object",
        "resolve_boundary": "generate_tower_object",
        "promote_face": "run_ablation",
        "block_retrieval": "block_retrieval",
    }.get(kind, kind or "inspect_tower")
    priority = _safe_float(row.get("priority"), 0.5)
    return {
        "action_kind": mapped,
        "target_face_id": row.get("target_face_id"),
        "target_dual_component_id": row.get("target_dual_component_id"),
        "reason": row.get("reason") or kind,
        "score": priority,
        "source_action_id": row.get("action_id"),
        "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
    }


def build_dost_auto_plan(
    out: str | Path,
    *,
    selected_features_path: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    invariant_ledger_path: str | Path | None = None,
    cost_model_path: str | Path | None = None,
    compiled_experiment_out: str | Path | None = None,
    notebook_out: str | Path | None = None,
    max_actions: int = 12,
    kernel_state_mode: str = "features",
) -> dict[str, Any]:
    selected = _read_rows(selected_features_path)
    taxonomy = _read_rows(taxonomy_path)
    tower_actions = _read_rows(tower_next_actions_path)
    tower_summary = {}
    if tower_summary_path and Path(tower_summary_path).exists():
        tower_summary = json.loads(Path(tower_summary_path).read_text(encoding="utf-8"))

    candidates: list[dict[str, Any]] = [
        {
            "action_kind": "set_observation_policy",
            "kernel_state_mode": kernel_state_mode,
            "reason": "bounded_feature_transcript_default",
            "score": 0.94,
            "cost_canonical_claim": {
                "candidate_set": ["summary", "features", "full"],
                "chosen_min_cost_sufficient": kernel_state_mode == "features",
            },
        }
    ]
    if selected:
        best_support = max(_safe_float(r.get("dual_support")) for r in selected)
        candidates.append(
            {
                "action_kind": "generate_features",
                "reason": "selected_low_cost_dual_separators",
                "score": 0.65 + min(0.25, best_support),
                "payload": {"n_selected_features": len(selected)},
            }
        )
    for row in tower_actions:
        candidates.append(_tower_action_candidate(row))
    for face in taxonomy:
        status = face.get("status") if isinstance(face.get("status"), dict) else {}
        if status.get("retrieval_allowed"):
            candidates.append(
                {
                    "action_kind": "allow_retrieval",
                    "target_face_id": face.get("taxonomy_face_id"),
                    "target_dual_component_id": face.get("dual_component_id"),
                    "reason": "face_retrieval_gate_open",
                    "score": 0.52,
                }
            )

    candidates.sort(key=lambda r: (-_safe_float(r.get("score")), str(r.get("action_kind")), str(r.get("target_face_id"))))
    selected_actions = candidates[: max(1, int(max_actions))]
    blocked_actions = [
        {
            "action_kind": "full_kernel_state_in_apply",
            "reason": "memory_risk",
        }
    ]
    if any((face.get("status") or {}).get("retrieval_blockers") for face in taxonomy if isinstance(face.get("status"), dict)):
        blocked_actions.append({"action_kind": "retrieval_from_bad_faces", "reason": "retrieval_blockers_present"})

    plan = {
        "schema_version": SCHEMA_AUTO_PLAN,
        "plan_id": "plan_" + stable_hash(
            {
                "selected_features": selected_features_path,
                "taxonomy": taxonomy_path,
                "tower_next_actions": tower_next_actions_path,
                "kernel_state_mode": kernel_state_mode,
            },
            14,
        ),
        "inputs": {
            "selected_features": str(selected_features_path) if selected_features_path else None,
            "taxonomy": str(taxonomy_path) if taxonomy_path else None,
            "tower_next_actions": str(tower_next_actions_path) if tower_next_actions_path else None,
            "tower_summary": str(tower_summary_path) if tower_summary_path else None,
            "invariant_ledger": str(invariant_ledger_path) if invariant_ledger_path else None,
            "cost_model": str(cost_model_path) if cost_model_path else None,
        },
        "selected_actions": selected_actions,
        "blocked_actions": blocked_actions,
        "constraints": {
            "carrier_safe": True,
            "memory_budget": "bounded",
            "timeout_budget": "bounded",
            "no_full_state_unless_debug": True,
            "no_retrieval_from_bad_faces": True,
        },
        "tower_summary": {
            "n_faces": tower_summary.get("n_faces"),
            "n_next_actions": tower_summary.get("n_next_actions"),
        },
        "canonical_status": "dost_auto_plan_finite_chart_not_canonical",
    }
    _json_dump(plan, out)
    if compiled_experiment_out:
        compile_experiment_from_auto_plan(out, compiled_experiment_out, notebook_out=notebook_out)
    return plan


__all__ = [
    "build_dost_auto_plan",
]
