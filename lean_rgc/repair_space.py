from __future__ import annotations

from pathlib import Path
from typing import Any
import math

from .response_completion import response_map_from_row
from .schemas import read_jsonl, stable_hash


SCHEMA_REPAIR_ATOM = "lean-rgc-relaxed-repair-atom-v58.0"


def read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def normalize_response_embedding(row: dict[str, Any]) -> dict[str, float]:
    return {str(k): safe_float(v) for k, v in response_map_from_row(row).items()}


def normalize_cost_vector(row: dict[str, Any]) -> dict[str, float]:
    cost = row.get("cost") if isinstance(row.get("cost"), dict) else {}
    cost_summary = row.get("cost_summary") if isinstance(row.get("cost_summary"), dict) else {}
    audit = row.get("audit") if isinstance(row.get("audit"), dict) else {}
    uncertainty = row.get("uncertainty") if isinstance(row.get("uncertainty"), dict) else {}
    success_rate = safe_float(row.get("success_rate"), safe_float(audit.get("success_rate"), 1.0))
    audit_risk = max(0.0, 1.0 - success_rate)
    if "audit_risk" in row:
        audit_risk = safe_float(row.get("audit_risk"), audit_risk)
    return {
        "cost": safe_float(row.get("cost_estimate"), safe_float(cost.get("cost_estimate"), safe_float(cost_summary.get("cost_estimate"), 1.0))),
        "audit_risk": audit_risk,
        "source_risk": safe_float(row.get("source_risk"), 0.0),
        "ghost_risk": safe_float(row.get("ghost_risk"), 0.0),
        "hardening_cost": safe_float(row.get("hardening_cost"), safe_float(uncertainty.get("response_l2_std"), 0.0)),
    }


def normalize_candidate_action(row: dict[str, Any]) -> dict[str, Any] | None:
    for key in ["candidate_action", "representative_action", "action"]:
        obj = row.get(key)
        if isinstance(obj, dict) and (obj.get("tactic") or obj.get("action_id")):
            action = dict(obj)
            action.setdefault("metadata", {})
            return action
    tactic = row.get("tactic")
    action_id = row.get("action_id") or row.get("id")
    if tactic or action_id:
        return {
            "action_id": str(action_id or stable_hash(row, 14)),
            "tactic": str(tactic or action_id or "skip"),
            "tactic_class": str(row.get("tactic_class") or row.get("class") or "crg_atom"),
            "carrier_tags": list(row.get("carrier_tags") or []),
            "cost_estimate": safe_float(row.get("cost_estimate"), 1.0),
            "metadata": dict(row.get("metadata") or {}),
        }
    return None


def make_repair_atom(
    *,
    species_id: str,
    source: str,
    source_row: dict[str, Any],
    response_embedding: dict[str, float] | None = None,
    candidate_action: dict[str, Any] | None = None,
    atom_hint: str | None = None,
) -> dict[str, Any]:
    response_embedding = response_embedding if response_embedding is not None else normalize_response_embedding(source_row)
    candidate_action = candidate_action if candidate_action is not None else normalize_candidate_action(source_row)
    src_id = (
        source_row.get("repair_atom_id")
        or source_row.get("action_id")
        or source_row.get("premise_use_id")
        or source_row.get("coordinate_id")
        or source_row.get("retrieval_candidate_id")
        or source_row.get("face_id")
        or source_row.get("taxonomy_face_id")
        or atom_hint
        or stable_hash(source_row, 14)
    )
    payload = {"species": species_id, "source": source, "src_id": str(src_id), "response": response_embedding}
    return {
        "schema_version": SCHEMA_REPAIR_ATOM,
        "repair_atom_id": "rel_atom_" + stable_hash(payload, 16),
        "species_id": species_id,
        "repair_species": species_id,
        "source": source,
        "source_id": str(src_id),
        "response_embedding": {str(k): float(v) for k, v in sorted(response_embedding.items())},
        "cost_vector": normalize_cost_vector(source_row),
        "candidate_action": candidate_action,
        "decoder": _decoder_for_species(species_id),
        "compactness_proxy": "finite_support_probability_simplex",
        "promotion_required": [
            "parent_nonpaid",
            "dual_certificate",
            "least_repair",
            "source_safe",
            "audit_safe",
            "cost_safe",
        ],
        "canonical_status": "repair_witness_not_canonical",
        "provenance": {"source_row": source_row},
    }


def _decoder_for_species(species_id: str) -> str:
    return {
        "action_distribution": "mixture_to_candidate_actions",
        "premise_distribution": "premise_mixture_to_candidate_actions",
        "carrier_patch_measure": "carrier_patch_to_incidence_candidate",
        "quotient_coordinate_cone": "quotient_coordinate_to_defect_registry",
        "context_portfolio": "portfolio_to_candidate_actions",
        "gamma_policy": "gamma_policy_to_action_sequence",
        "goal_state_transform": "goal_state_transform_to_tactic_candidate",
        "proof_sketch": "proof_sketch_to_tactic_script",
        "concept_latent": "concept_to_repair_species",
    }.get(species_id, "unknown_decoder")


__all__ = [
    "SCHEMA_REPAIR_ATOM",
    "make_repair_atom",
    "normalize_candidate_action",
    "normalize_cost_vector",
    "normalize_response_embedding",
    "read_rows",
    "safe_float",
]
