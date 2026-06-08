from __future__ import annotations

import re
from dataclasses import dataclass, field

from .goal_shape import parse_goal_shape
from .schemas import LeanTask, ProofState, TacticAction, stable_hash
from .carrier_normalizer import compose_exposure_actions


@dataclass
class CandidateGeneratorConfig:
    include_expensive: bool = False
    include_induction: bool = True
    include_aesop: bool = False
    max_candidates: int = 96
    use_carrier_exposure: bool = True
    max_exposure_prefixes: int = 8
    library_rewrite_lemmas: list[str] = field(default_factory=lambda: [
        "Nat.add_comm", "Nat.add_assoc", "Nat.mul_comm", "Nat.mul_assoc",
        "Nat.add_left_comm", "List.length_append", "List.map_map",
    ])


class TacticCandidateGenerator:
    """Lean tactic candidate generator with carrier metadata.

    Candidate labels are charts, not canonical components.  v0.5 adds focused
    carrier exposure: structural prefixes such as `intros` are generated from
    goal shape and composed with core response-ranked actions.
    """

    def __init__(self, config: CandidateGeneratorConfig | None = None):
        self.config = config or CandidateGeneratorConfig()

    @classmethod
    def from_exposure_disabled(cls) -> "TacticCandidateGenerator":
        cfg = CandidateGeneratorConfig(use_carrier_exposure=False)
        return cls(cfg)

    def candidates(self, task: LeanTask, state: ProofState | None = None) -> list[TacticAction]:
        text = (task.statement + "\n" + (state.target if state else "") + "\n" + (state.goals_text if state else "")).lower()
        shape = parse_goal_shape(task, state)
        cands: list[TacticAction] = []

        def add(tactic: str, cls: str, tags: list[str], cost: float = 1.0, metadata: dict | None = None):
            aid = stable_hash({"tactic": tactic, "cls": cls, "metadata": metadata or {}}, 12)
            cands.append(TacticAction(action_id=aid, tactic=tactic, tactic_class=cls, carrier_tags=tags, cost_estimate=cost, metadata=metadata or {}))

        # Core actions: these are response-ranked after any structural exposure.
        add("rfl", "exact", ["rfl", "easy", "eq"], 0.1)
        add("assumption", "exact", ["premise", "easy"], 0.2)
        add("simp", "simp", ["simp"], 0.5)
        add("simp_all", "simp", ["simp", "premise"], 0.8)
        add("constructor", "constructor", ["constructor", "branching"], 0.8)
        add("constructor <;> assumption", "constructor", ["constructor", "premise"], 0.9)
        add("constructor <;> simp_all", "constructor", ["constructor", "premise", "simp"], 1.0)
        add("norm_num", "arithmetic", ["arithmetic", "normalization"], 0.8)
        if shape.has_arith or any(k in text for k in ["nat", "int", "≤", "<", "+", "-"]):
            add("omega", "arithmetic", ["nat", "linear_arithmetic", "arithmetic"], 1.0)
            add("linarith", "arithmetic", ["linear_arithmetic", "arithmetic"], 1.2)
        if shape.has_arith or any(k in text for k in ["*", "semiring", "ring"]):
            add("ring_nf", "normalization", ["ring", "normalization"], 1.3)
            if self.config.include_expensive:
                add("nlinarith", "arithmetic", ["nonlinear_arithmetic", "arithmetic"], 2.0)
        if self.config.include_induction and re.search(r"\b(n|m|k)\s*:\s*nat", text, flags=re.I):
            for v in ["n", "m", "k"]:
                if re.search(rf"\b{v}\s*:\s*nat", text, flags=re.I):
                    add(f"induction {v} with\n  | zero => simp\n  | succ {v} ih => simp [ih]", "induction", ["induction", "nat"], 2.0)
        for lemma in self.config.library_rewrite_lemmas:
            add(f"rw [{lemma}]", "rewrite", ["rewrite", "library"], 0.8)
            add(f"simp [{lemma}]", "simp", ["simp", "library"], 0.9)
        # Local-hypothesis charts: exact/apply/rw/simp with local names.
        state_text = (state.goals_text if state else "") + "\n" + (state.local_context if state else "")
        hyp_names = []
        for m in re.finditer(r"(^|\n)\s*([A-Za-z_][A-Za-z0-9_']*)\s*:", state_text):
            name = m.group(2)
            if name not in {"theorem", "example"} and name not in hyp_names:
                hyp_names.append(name)
        for h in hyp_names[:8]:
            add(f"exact {h}", "exact", ["premise", "local"], 0.25)
            add(f"apply {h}", "apply", ["premise", "local"], 0.5)
            add(f"rw [{h}]", "rewrite", ["rewrite", "local"], 0.65)
            add(f"simp [{h}]", "simp", ["simp", "local"], 0.75)
            # Projection charts for conjunction hypotheses. Lean may reject if h is not a conjunction; micro-audit decides.
            add(f"exact {h}.left", "exact", ["premise", "and_projection"], 0.3)
            add(f"exact {h}.right", "exact", ["premise", "and_projection"], 0.3)
        # More state-dependent induction candidates.
        for v in re.findall(r"\b([A-Za-z_][A-Za-z0-9_']*)\s*:\s*(?:Nat|List|Fin|Int)\b", state_text + "\n" + task.statement):
            if self.config.include_induction:
                add(f"induction {v} <;> simp_all", "induction", ["induction"], 2.2)
        if self.config.include_aesop:
            add("aesop", "search", ["search", "aesop"], 3.0)

        # Structural exposure phase: intro/constructor/projection prefixes are carrier exposure charts.
        if self.config.use_carrier_exposure:
            cands = compose_exposure_actions(task, state, cands, max_exposures=self.config.max_exposure_prefixes)

        # Deduplicate by tactic string.
        seen: set[str] = set()
        out: list[TacticAction] = []
        for a in sorted(cands, key=lambda x: (x.cost_estimate, x.tactic)):
            if a.tactic not in seen:
                seen.add(a.tactic)
                out.append(a)
            if len(out) >= self.config.max_candidates:
                break
        return out
