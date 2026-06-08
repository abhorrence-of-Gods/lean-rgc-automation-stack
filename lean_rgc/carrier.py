from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np

from .schemas import DefectVector, TacticAction, stable_hash


CARRIER_KEYS = [
    "missing_induction_scheme",
    "missing_simp_lemma",
    "missing_rewrite_orientation",
    "missing_premise_family",
    "missing_typeclass_instance",
    "missing_domain_tactic",
    "unintroduced_forall",
    "unintroduced_imp",
    "unsplit_and_target",
    "missing_and_projection",
    "eq_reflexive_goal",
    "nat_arith_goal",
    "list_simp_goal",
    "metavar_exposure_debt",
    "constructor_branch_debt",
]


@dataclass
class CarrierReport:
    carrier_defect: dict[str, float]
    action_risks: dict[str, float] = field(default_factory=dict)
    binding_atoms: list[str] = field(default_factory=list)
    coker_residual_norm: float | None = None
    generated_contexts: list[dict[str, Any]] = field(default_factory=list)


class LeanCarrierAlgebra:
    """Carrier defect/violation module.

    This is deliberately simple. It turns carrier component vectors into risk
    constraints and computes action-level carrier violation proxies.
    """

    def carrier_defect(self, defect: DefectVector) -> dict[str, float]:
        return {k: float(defect.carrier.get(k, 0.0)) for k in CARRIER_KEYS}

    def carrier_violation_proxy(self, defect: DefectVector, action: TacticAction) -> float:
        d = self.carrier_defect(defect)
        tags = set(action.carrier_tags + [action.tactic_class])
        # Action pays carriers matching its tags; risks carriers it ignores.
        pay = {
            "missing_induction_scheme": "induction" in tags,
            "missing_simp_lemma": "simp" in tags,
            "missing_rewrite_orientation": "rewrite" in tags or "simp" in tags,
            "missing_premise_family": "premise" in tags or action.tactic_class in {"exact", "apply"},
            "missing_typeclass_instance": "typeclass" in tags or "simp" in tags,
            "missing_domain_tactic": bool(tags & {"arithmetic", "nat", "ring", "linear_arithmetic", "normalization"}),
            "unintroduced_forall": "unintroduced_forall" in tags or "nonbranching_intro" in tags or "intro" in tags or "exposure" in tags,
            "unintroduced_imp": "unintroduced_imp" in tags or "nonbranching_intro" in tags or "intro" in tags or "exposure" in tags,
            "unsplit_and_target": "unsplit_and_target" in tags or "constructor" in tags or action.tactic_class.startswith("constructor"),
            "missing_and_projection": "missing_and_projection" in tags or "projection" in tags or "premise" in tags,
            "eq_reflexive_goal": "rfl" in tags or action.tactic_class in {"exact", "simp"},
            "nat_arith_goal": bool(tags & {"arithmetic", "nat", "linear_arithmetic", "normalization"}),
            "list_simp_goal": "list_simp_goal" in tags or "simp" in tags,
            "metavar_exposure_debt": "exposure" in tags or action.tactic_class in {"refine", "exact", "apply"},
            "constructor_branch_debt": "constructor" in tags or "premise" in tags or "simp" in tags,
        }
        risk = 0.0
        for k, v in d.items():
            if pay.get(k, False):
                risk -= 0.25 * v
            else:
                risk += v
        return float(max(0.0, risk))

    def action_risks(self, defect: DefectVector, actions: list[TacticAction]) -> dict[str, float]:
        return {a.action_id: self.carrier_violation_proxy(defect, a) for a in actions}

    def coker_residual_proxy(self, defect: DefectVector, actions: list[TacticAction]) -> tuple[float, list[str]]:
        d = self.carrier_defect(defect)
        tags = {tag for a in actions for tag in (a.carrier_tags + [a.tactic_class])}
        covered = {
            "missing_induction_scheme": "induction" in tags,
            "missing_simp_lemma": "simp" in tags,
            "missing_rewrite_orientation": "rewrite" in tags or "simp" in tags,
            "missing_premise_family": "premise" in tags or "apply" in tags or "exact" in tags,
            "missing_typeclass_instance": "typeclass" in tags or "simp" in tags,
            "missing_domain_tactic": bool(tags & {"arithmetic", "nat", "ring", "linear_arithmetic", "normalization"}),
            "unintroduced_forall": "exposure" in tags or "nonbranching_intro" in tags or "intro" in tags,
            "unintroduced_imp": "exposure" in tags or "nonbranching_intro" in tags or "intro" in tags,
            "unsplit_and_target": "constructor" in tags,
            "missing_and_projection": "projection" in tags or "premise" in tags,
            "eq_reflexive_goal": "rfl" in tags or "simp" in tags or "exact" in tags,
            "nat_arith_goal": bool(tags & {"arithmetic", "nat", "linear_arithmetic", "normalization"}),
            "list_simp_goal": "list_simp_goal" in tags or "simp" in tags,
            "metavar_exposure_debt": "exposure" in tags or "refine" in tags or "exact" in tags or "apply" in tags,
            "constructor_branch_debt": "constructor" in tags or "simp" in tags or "premise" in tags,
        }
        residual_atoms = [k for k, v in d.items() if v > 0 and not covered.get(k, False)]
        norm = float(sum(d[k] for k in residual_atoms))
        return norm, residual_atoms


class CarrierGenerator:
    """Generate target-safe context candidates from carrier residual atoms."""

    def generate(self, residual_atoms: list[str], state_text: str = "") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for atom in residual_atoms:
            if atom in {"unintroduced_forall", "unintroduced_imp"}:
                out.append({
                    "kind": "carrier_exposure",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["intros", "intros\nsimp_all", "intros\nrfl"],
                    "carrier_atom": atom,
                })
            elif atom == "unsplit_and_target":
                out.append({
                    "kind": "constructor_exposure",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["constructor", "constructor <;> assumption", "constructor <;> simp_all"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_and_projection":
                out.append({
                    "kind": "premise_projection",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["exact h.left", "exact h.right", "simp_all"],
                    "carrier_atom": atom,
                })
            elif atom == "eq_reflexive_goal":
                out.append({
                    "kind": "equality_closure",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["rfl", "simp"],
                    "carrier_atom": atom,
                })
            elif atom == "nat_arith_goal":
                out.append({
                    "kind": "arithmetic_context",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["omega", "norm_num", "simp", "linarith"],
                    "carrier_atom": atom,
                })
            elif atom == "list_simp_goal":
                out.append({
                    "kind": "list_simp_context",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["simp", "simp_all", "simp [List.length_append]"],
                    "carrier_atom": atom,
                })
            elif atom == "constructor_branch_debt":
                out.append({
                    "kind": "branch_closure",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["constructor <;> assumption", "constructor <;> simp_all"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_induction_scheme":
                out.append({
                    "kind": "induction_scheme",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["induction n with | zero => simp | succ n ih => simp [ih]", "induction xs with | nil => simp | cons x xs ih => simp [ih]"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_simp_lemma":
                out.append({
                    "kind": "simp_set_extension",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["simp_all", "simp [*, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_rewrite_orientation":
                out.append({
                    "kind": "rewrite_orientation_search",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["rw [← ?lemma]", "rw [?lemma]"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_premise_family":
                out.append({
                    "kind": "premise_retrieval",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "query": state_text[:512],
                    "carrier_atom": atom,
                })
            elif atom == "missing_typeclass_instance":
                out.append({
                    "kind": "typeclass_context",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["infer_instance", "haveI := ?instance"],
                    "carrier_atom": atom,
                })
            elif atom == "missing_domain_tactic":
                out.append({
                    "kind": "domain_tactic",
                    "context_id": stable_hash({"carrier": atom, "state": state_text[:120]}),
                    "suggestions": ["omega", "linarith", "ring_nf", "norm_num"],
                    "carrier_atom": atom,
                })
        return out


@dataclass
class CarrierCokerReport:
    defect_norm: float
    covered_norm: float
    residual_norm: float
    residual_atoms: list[str]
    normal: dict[str, float]


def carrier_coker_proxy(defect: DefectVector, actions: list[TacticAction]) -> CarrierCokerReport:
    """Finite proxy for carrier coker residual.

    This is a conservative chart: an atom is covered if the current action
    universe contains a tag that can plausibly pay it. Remaining carrier mass
    is the residual normal used by the carrier generator.
    """
    alg = LeanCarrierAlgebra()
    d = alg.carrier_defect(defect)
    residual_norm, residual_atoms = alg.coker_residual_proxy(defect, actions)
    defect_norm = float(sum(max(0.0, v) for v in d.values()))
    covered_norm = max(0.0, defect_norm - residual_norm)
    normal = {k: float(d.get(k, 0.0)) for k in residual_atoms}
    return CarrierCokerReport(defect_norm=defect_norm, covered_norm=covered_norm, residual_norm=residual_norm, residual_atoms=residual_atoms, normal=normal)
