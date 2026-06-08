from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import TacticAction, stable_hash, read_jsonl, write_jsonl


def _goal_targets(ir_row: dict[str, Any]) -> list[dict[str, Any]]:
    return [g for g in (ir_row.get("goals") or []) if isinstance(g, dict)]


def _add_action(rows: list[dict[str, Any]], *, task_id: str, tactic: str, cls: str, tags: list[str], meta: dict[str, Any], cost: float = 0.8) -> None:
    if not tactic.strip():
        return
    aid = stable_hash({"task_id": task_id, "tactic": tactic, "meta": meta}, 14)
    row = TacticAction(action_id=aid, tactic=tactic, tactic_class=cls, carrier_tags=tags, cost_estimate=cost, metadata=meta).to_dict()
    if task_id:
        row["task_id"] = task_id
        row.setdefault("metadata", {})["task_id"] = task_id
    rows.append(row)


def _compose(prefix: str, core: str) -> str:
    prefix = (prefix or "").strip()
    core = (core or "").strip()
    if prefix and core:
        return prefix + "\n" + core
    return prefix or core


@dataclass
class IRCandidateConfig:
    max_candidates_per_state: int = 64
    include_identity_prefix: bool = True
    include_branching_exposure: bool = True
    include_hyp_projection: bool = True
    include_arith: bool = True
    include_rewrite_shells: bool = True


class IRDrivenCandidateGenerator:
    """Generate tactic candidates from structured-ish ProofStateIR rows.

    This is still a chart-level generator.  It makes the exposure/core split
    explicit so later response quotienting can forget raw tactic labels.
    """

    def __init__(self, config: IRCandidateConfig | None = None):
        self.config = config or IRCandidateConfig()

    def candidates_for_ir(self, ir_row: dict[str, Any]) -> list[dict[str, Any]]:
        task_id = str(ir_row.get("task_id") or ir_row.get("state_id") or "")
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for gi, goal in enumerate(_goal_targets(ir_row)):
            shape = goal.get("shape") or {}
            target = str(goal.get("target") or "")
            target_head = str(goal.get("target_head") or "")
            atoms = list(map(str, goal.get("carrier_atoms") or []))
            hyps = [h for h in (goal.get("hypotheses") or []) if isinstance(h, dict)]
            prefixes: list[tuple[str, str, list[str], float, dict[str, Any]]] = []
            if self.config.include_identity_prefix:
                prefixes.append(("", "identity", [], 0.0, {}))
            if shape.get("has_forall") or shape.get("has_imp") or target_head in {"forall", "imp"}:
                prefixes.append(("intros", "nonbranching_intro", ["exposure", "intro"], 0.05, {"addresses": ["unintroduced_forall", "unintroduced_imp"]}))
                if self.config.include_branching_exposure and (shape.get("target_is_and") or target_head == "and" or "∧" in target):
                    prefixes.append(("intros\nconstructor", "branching_intro_constructor", ["exposure", "intro", "constructor"], 0.20, {"addresses": ["unintroduced_forall", "unintroduced_imp", "unsplit_and_target"], "gamma_debt": 0.2}))
            elif self.config.include_branching_exposure and (shape.get("target_is_and") or target_head == "and" or "∧" in target):
                prefixes.append(("constructor", "branching_constructor", ["exposure", "constructor"], 0.18, {"addresses": ["unsplit_and_target"], "gamma_debt": 0.2}))

            cores: list[tuple[str, str, list[str], float, dict[str, Any]]] = []
            # Cheap closers.
            cores.extend([
                ("rfl", "eq", ["eq", "rfl"], 0.10, {"addresses": ["eq_reflexive_goal"]}),
                ("simp", "simp", ["simp"], 0.35, {"addresses": ["missing_simp_lemma"]}),
                ("simp_all", "simp", ["simp", "premise"], 0.55, {"addresses": ["missing_simp_lemma", "missing_premise_family"]}),
                ("assumption", "premise", ["premise"], 0.20, {"addresses": ["missing_premise_family"]}),
                ("constructor <;> assumption", "constructor", ["constructor", "premise"], 0.75, {"addresses": ["unsplit_and_target", "missing_premise_family"]}),
                ("constructor <;> simp_all", "constructor", ["constructor", "simp", "premise"], 0.85, {"addresses": ["unsplit_and_target", "missing_premise_family"]}),
            ])
            if self.config.include_arith and (shape.get("has_arith") or any(t in target for t in ["Nat", "Int", "+", "*", "≤", "<", "≥", ">"])):
                cores.extend([
                    ("omega", "arith", ["arithmetic", "omega"], 0.70, {"addresses": ["nat_arith_goal"]}),
                    ("norm_num", "arith", ["arithmetic", "norm_num"], 0.45, {"addresses": ["nat_arith_goal"]}),
                    ("ring_nf", "arith", ["arithmetic", "ring"], 0.90, {"addresses": ["nat_arith_goal"]}),
                ])
            if shape.get("has_list") or "List" in target or "length" in target:
                cores.extend([
                    ("simp", "simp", ["list", "simp"], 0.40, {"addresses": ["list_simp_goal"]}),
                    ("simp_all", "simp", ["list", "simp", "premise"], 0.65, {"addresses": ["list_simp_goal", "missing_premise_family"]}),
                ])
            if self.config.include_rewrite_shells and (shape.get("target_is_eq") or target_head == "eq"):
                cores.extend([
                    ("rw [Nat.add_comm]", "rewrite", ["rewrite", "nat"], 0.70, {"addresses": ["missing_rewrite_orientation"]}),
                    ("simp [Nat.add_comm, Nat.add_assoc, Nat.add_left_comm]", "simp", ["simp", "rewrite", "nat"], 0.80, {"addresses": ["missing_rewrite_orientation", "missing_simp_lemma"]}),
                ])
            if self.config.include_hyp_projection:
                for h in hyps[:8]:
                    name = str(h.get("name") or "")
                    if not name:
                        continue
                    if h.get("is_and") or h.get("head") == "and" or "∧" in str(h.get("type_text") or ""):
                        cores.extend([
                            (f"exact {name}.left", "premise", ["premise", "projection"], 0.30, {"addresses": ["missing_and_projection", "missing_premise_family"], "hyp": name}),
                            (f"exact {name}.right", "premise", ["premise", "projection"], 0.30, {"addresses": ["missing_and_projection", "missing_premise_family"], "hyp": name}),
                            (f"have {name}_left := {name}.left\nhave {name}_right := {name}.right\nsimp_all", "premise", ["premise", "projection", "simp"], 0.70, {"addresses": ["missing_and_projection", "missing_simp_lemma"], "hyp": name}),
                        ])
                    # Direct exact for matching-looking hypotheses; still audit-gated.
                    cores.append((f"exact {name}", "premise", ["premise"], 0.25, {"addresses": ["missing_premise_family"], "hyp": name}))

            for prefix, pkind, ptags, pcost, pmeta in prefixes:
                for core, cls, ctags, ccost, cmeta in cores:
                    tactic = _compose(prefix, core)
                    if tactic in seen:
                        continue
                    seen.add(tactic)
                    meta = {
                        "generated_by": "ir_driven_candidate_generator",
                        "goal_index": gi,
                        "goal_head": target_head,
                        "goal_carrier_atoms": atoms,
                        "prefix_tactic": prefix,
                        "prefix_kind": pkind,
                        "core_tactic": core,
                        "prefix_meta": pmeta,
                        "core_meta": cmeta,
                    }
                    _add_action(rows, task_id=task_id, tactic=tactic, cls=cls, tags=list(dict.fromkeys(ptags + ctags + atoms)), meta=meta, cost=pcost + ccost)
                    if len(rows) >= self.config.max_candidates_per_state:
                        return rows
        return rows


def ir_candidates_file(ir_path: str | Path, out: str | Path, *, max_candidates: int = 64) -> list[dict[str, Any]]:
    gen = IRDrivenCandidateGenerator(IRCandidateConfig(max_candidates_per_state=max_candidates))
    rows: list[dict[str, Any]] = []
    for ir in read_jsonl(ir_path):
        rows.extend(gen.candidates_for_ir(ir))
    write_jsonl(out, rows)
    return rows


__all__ = ["IRCandidateConfig", "IRDrivenCandidateGenerator", "ir_candidates_file"]
