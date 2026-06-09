from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import stable_hash, write_jsonl


SCHEMA_RELAXED_SPECIES = "lean-rgc-relaxed-repair-species-v58.0"


DEFAULT_RELAXED_SPECIES: list[dict[str, Any]] = [
    {
        "species_id": "action_distribution",
        "species_kind": "finite_support_probability_simplex",
        "decoder": "mixture_to_candidate_actions",
        "compactness_proxy": "finite_action_simplex",
        "hardening_methods": ["topk_decode", "beam_sequence_decode"],
        "audit_requirements": ["micro_audit", "robust_acceptance"],
    },
    {
        "species_id": "premise_distribution",
        "species_kind": "finite_support_probability_simplex",
        "decoder": "premise_mixture_to_candidate_actions",
        "compactness_proxy": "finite_premise_use_simplex",
        "hardening_methods": ["topk_decode", "beam_sequence_decode"],
        "audit_requirements": ["micro_audit", "heldout"],
    },
    {
        "species_id": "carrier_patch_measure",
        "species_kind": "positive_measure_chart",
        "decoder": "carrier_patch_to_incidence_candidate",
        "compactness_proxy": "finite_positive_patch_cone",
        "hardening_methods": ["carrier_patch_audit"],
        "audit_requirements": ["carrier_patch_audit", "source_safe"],
    },
    {
        "species_id": "quotient_coordinate_cone",
        "species_kind": "positive_coordinate_cone",
        "decoder": "quotient_coordinate_to_defect_registry",
        "compactness_proxy": "finite_linear_functional_cone",
        "hardening_methods": ["coordinate_top_loading_decode"],
        "audit_requirements": ["coordinate_validation", "micro_audit"],
    },
    {
        "species_id": "context_portfolio",
        "species_kind": "relaxed_atlas",
        "decoder": "portfolio_to_candidate_actions",
        "compactness_proxy": "finite_context_pair_simplex",
        "hardening_methods": ["portfolio_to_candidates", "beam_sequence_decode"],
        "audit_requirements": ["micro_audit", "heldout", "carrier_patch_audit"],
    },
    {
        "species_id": "gamma_policy",
        "species_kind": "finite_horizon_policy_chart",
        "decoder": "gamma_policy_to_action_sequence",
        "compactness_proxy": "finite_gamma_policy_simplex",
        "hardening_methods": ["gamma_policy_to_action_sequence"],
        "audit_requirements": ["gamma_tail_audit", "micro_audit"],
    },
    {
        "species_id": "goal_state_transform",
        "species_kind": "goal_state_transition_chart",
        "decoder": "goal_state_transform_to_tactic_candidate",
        "compactness_proxy": "finite_goal_state_transition_graph",
        "hardening_methods": ["transition_to_tactic"],
        "audit_requirements": ["kernel_replay", "micro_audit"],
    },
    {
        "species_id": "proof_sketch",
        "species_kind": "relaxed_sequence_chart",
        "decoder": "proof_sketch_to_tactic_script",
        "compactness_proxy": "bounded_sequence_beam",
        "hardening_methods": ["sequence_decode"],
        "audit_requirements": ["proof_replay", "source_safe"],
    },
    {
        "species_id": "concept_latent",
        "species_kind": "concept_geometry_chart",
        "decoder": "concept_to_repair_species",
        "compactness_proxy": "response_metric_completion_chart",
        "hardening_methods": ["concept_to_syntax", "concept_to_repair_atom"],
        "audit_requirements": ["concept_decode", "crg_audit"],
    },
]


def default_relaxed_species_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in DEFAULT_RELAXED_SPECIES:
        species_id = str(row["species_id"])
        rows.append(
            {
                "schema_version": SCHEMA_RELAXED_SPECIES,
                "species_id": species_id,
                "registry_row_id": "rspecies_" + stable_hash(species_id, 12),
                "canonical_status": "repair_species_chart",
                **row,
            }
        )
    return rows


def write_relaxed_species_registry(
    out: str | Path,
    *,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    rows = default_relaxed_species_rows()
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_RELAXED_SPECIES,
        "out": str(out),
        "n_species": len(rows),
        "species_ids": [str(row["species_id"]) for row in rows],
        "canonical_status": "relaxed_repair_species_registry_is_chart_not_canonical",
    }
    if summary_out:
        p = Path(summary_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return summary


__all__ = [
    "SCHEMA_RELAXED_SPECIES",
    "DEFAULT_RELAXED_SPECIES",
    "default_relaxed_species_rows",
    "write_relaxed_species_registry",
]
