from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .schemas import AuditRecord, DefectVector, ProofState
from .goal_shape import parse_goal_shape, shape_atoms
from .proof_ir import parse_proof_state_ir

_TOKEN_RE = re.compile(r"[A-Za-z0-9_'.]+|[^\s]")


def _tokens(s: str) -> list[str]:
    return _TOKEN_RE.findall(s or "")


def _count_any(text: str, pats: list[str]) -> int:
    low = text.lower()
    return sum(low.count(p.lower()) for p in pats)


@dataclass
class DefectWeights:
    goal_count: float = 1.0
    goal_size: float = 0.03
    hyp_count: float = 0.05
    mvar: float = 0.5
    typeclass: float = 1.0
    elab_error: float = 2.0
    timeout: float = 5.0
    proof_size: float = 0.001


class ProofDefectExtractor:
    """Charted proof-state defect extractor.

    v0.5 augments the original hand-written components with structural carrier
    atoms from GoalShape.  These atoms are seed candidates for AutoDefectMiner;
    they remain charts until response/coker audits validate them.
    """

    def __init__(self, weights: DefectWeights | None = None):
        self.weights = weights or DefectWeights()

    def extract(self, state: ProofState, audit: AuditRecord | None = None) -> DefectVector:
        text = "\n".join([state.target or "", state.goals_text or "", "\n".join(state.raw_messages or [])])
        if audit is not None:
            text += "\n" + "\n".join(audit.messages or []) + "\n" + audit.stderr + "\n" + audit.stdout
        toks = _tokens(text)
        shape = parse_goal_shape(state=state, audit=audit, extra=("\n".join(audit.messages or []) if audit else ""))
        ir = parse_proof_state_ir(state=state, audit=audit, text=text)
        num_goals = self._estimate_num_goals(text, audit)
        total_goal_size = len(toks)
        hyp_count = self._estimate_hyp_count(text)
        metavar_count = text.count("?") + _count_any(text, ["mvar", "metavariable"])
        typeclass_pending = _count_any(text, ["failed to synthesize", "typeclass", "instance"])
        coercion_pending = _count_any(text, ["coercion", "coe", "type mismatch"])
        elab_error = 1.0 if (audit and audit.status == "elab_error") else 0.0
        timeout = 1.0 if (audit and audit.status == "timeout") else 0.0
        unsafe = 1.0 if (audit and audit.status == "unsafe") else 0.0
        heartbeats = float(audit.heartbeats or 0.0) if audit else 0.0
        proof_size_risk = self._proof_size_proxy(text)
        carrier = self._carrier_defect(text, audit, shape)
        audit_d = {
            "timeout_risk": timeout,
            "unsafe_risk": unsafe,
            "nonreplay_risk": 0.0,
            "heartbeat_scaled": math.log1p(heartbeats) / 20.0 if heartbeats else 0.0,
            "proof_size_risk": proof_size_risk,
        }
        goal = {
            "num_goals": float(num_goals),
            "total_goal_size_log": math.log1p(total_goal_size),
            "hyp_count_log": math.log1p(hyp_count),
            "target_symbol_count_log": math.log1p(len(_tokens(state.target or ""))),
            "unsolved_goal_flag": 0.0 if (audit and audit.status == "success") else 1.0,
        }
        type_d = {
            "metavar_count_log": math.log1p(metavar_count),
            "typeclass_pending": float(typeclass_pending > 0 or shape.has_typeclass_error),
            "coercion_pending": float(coercion_pending > 0),
            "elaboration_error": elab_error,
        }
        search = {
            "branch_factor_est": self._branch_factor_proxy(text),
            "loop_signature_risk": self._loop_signature_proxy(text),
            "simp_explosion_risk": float(_count_any(text, ["simp", "rewrite"]) > 10),
            "proof_term_growth_proxy": proof_size_risk,
            "constructor_branch_debt": carrier.get("constructor_branch_debt", 0.0),
        }
        keys: list[str] = []
        vals: list[float] = []
        for prefix, d in [("goal", goal), ("type", type_d), ("search", search), ("carrier", carrier), ("audit", audit_d)]:
            for k in sorted(d):
                keys.append(f"{prefix}.{k}")
                vals.append(float(d[k]))
        return DefectVector(goal=goal, type=type_d, search=search, carrier=carrier, audit=audit_d, flat=vals, flat_keys=keys, quotient_meta={"extractor": "lean-rgc-defect-v0.6", "goal_shape": shape.to_dict(), "state_ir": ir.to_dict()})

    def response(self, before: DefectVector, after: DefectVector) -> tuple[dict[str, float], list[float], list[str]]:
        after_map = dict(zip(after.flat_keys, after.flat))
        resp = {k: float(v - after_map.get(k, 0.0)) for k, v in zip(before.flat_keys, before.flat)}
        return resp, [resp[k] for k in before.flat_keys], list(before.flat_keys)

    @staticmethod
    def _estimate_num_goals(text: str, audit: AuditRecord | None) -> int:
        if audit and audit.status == "success":
            return 0
        if "unsolved goals" in text.lower() or "unsolved goal" in text.lower():
            cases = len(re.findall(r"(^|\n)case\s+", text))
            turnstile = text.count("⊢")
            return max(1, cases, turnstile)
        return 1 if text.strip() else 0

    @staticmethod
    def _estimate_hyp_count(text: str) -> int:
        before = text.split("⊢")[0]
        return len(re.findall(r"(^|\n)\s*[A-Za-z_][A-Za-z0-9_']*\s*:", before))

    @staticmethod
    def _proof_size_proxy(text: str) -> float:
        return min(10.0, math.log1p(len(_tokens(text))) / 5.0)

    @staticmethod
    def _branch_factor_proxy(text: str) -> float:
        return float(max(0, text.count("case ") + text.count("⊢") - 1))

    @staticmethod
    def _loop_signature_proxy(text: str) -> float:
        low = text.lower()
        return float(any(p in low for p in ["maximum recursion", "recursion", "stuck", "no progress"]))

    @staticmethod
    def _carrier_defect(text: str, audit: AuditRecord | None, shape=None) -> dict[str, float]:
        low = text.lower()
        if shape is None:
            shape = parse_goal_shape(extra_text=text)
        atoms = shape_atoms(shape)
        tactic_text = ""
        # Pattern-based legacy carrier signals from Lean messages / goal syntax.
        missing_induction = float(any(k in low for k in ["nat", "list", "tree", "succ", "rec"]) and "induction" not in low)
        missing_simp = float(any(k in low for k in ["simp made no progress", "unsolved goals", "rewrite"]))
        missing_rewrite = float(any(k in low for k in ["rw", "rewrite", "equality", "="]))
        missing_premise = float(any(k in low for k in ["unknown identifier", "invalid field", "application type mismatch"]))
        missing_typeclass = float(any(k in low for k in ["failed to synthesize", "typeclass", "instance"]) or shape.has_typeclass_error)
        arithmetic = float(any(k in low for k in ["nat", "int", "≤", "<", "+", "*", "omega", "linarith", "ring"]) or shape.has_arith)
        constructor_branch = float("constructor" in low and ("unsolved goals" in low or "case " in low))
        d = {
            "missing_induction_scheme": missing_induction,
            "missing_simp_lemma": max(missing_simp, atoms.get("list_simp_goal", 0.0)),
            "missing_rewrite_orientation": max(missing_rewrite, float(shape.has_eq_hyp)),
            "missing_premise_family": max(missing_premise, float(shape.has_and_hyp)),
            "missing_typeclass_instance": missing_typeclass,
            "missing_domain_tactic": arithmetic * float("omega" not in low and "linarith" not in low and "ring" not in low),
            "unintroduced_forall": atoms.get("unintroduced_forall", 0.0),
            "unintroduced_imp": atoms.get("unintroduced_imp", 0.0),
            "unsplit_and_target": atoms.get("unsplit_and_target", 0.0),
            "missing_and_projection": atoms.get("missing_and_projection", 0.0),
            "eq_reflexive_goal": atoms.get("eq_reflexive_goal", 0.0),
            "nat_arith_goal": atoms.get("nat_arith_goal", 0.0),
            "list_simp_goal": atoms.get("list_simp_goal", 0.0),
            "metavar_exposure_debt": atoms.get("metavar_exposure_debt", 0.0),
            "constructor_branch_debt": constructor_branch,
        }
        if audit and audit.status == "success":
            # Closed proof has no active carrier defects in this chart.
            return {k: 0.0 for k in d}
        return d
