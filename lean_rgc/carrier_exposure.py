from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .goal_shape import GoalShape, GoalShapeParser
from .schemas import LeanTask, ProofState, TacticAction, stable_hash
from .candidates import CandidateGeneratorConfig, TacticCandidateGenerator


@dataclass
class ExposureCandidate:
    prefix_id: str
    prefix_tactic: str
    kind: str
    carrier_tags: list[str] = field(default_factory=list)
    cost: float = 0.05
    branching: bool = False
    gamma_debt: float = 0.0
    expected_carrier_delta: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CarrierNormalizer:
    """Focused carrier exposure generator.

    Structural tactics such as `intros` are treated as carrier exposure prefixes,
    not as primitive tactic labels. The returned prefixes are still charts and
    must be micro-audited.
    """

    def __init__(self, parser: GoalShapeParser | None = None):
        self.parser = parser or GoalShapeParser()

    def expose(self, task: LeanTask, state: ProofState | None = None) -> list[ExposureCandidate]:
        shape = self.parser.parse(task, state)
        out: list[ExposureCandidate] = []
        # Always include empty exposure.
        out.append(ExposureCandidate(prefix_id="expose_empty", prefix_tactic="", kind="identity", carrier_tags=[], cost=0.0, metadata={"shape": shape.to_dict()}))
        if shape.has_forall or shape.has_imp:
            out.append(ExposureCandidate(
                prefix_id="expose_intros",
                prefix_tactic="intros",
                kind="nonbranching_intro",
                carrier_tags=["exposure", "intro", "forall", "imp"],
                cost=0.05,
                expected_carrier_delta={"unintroduced_forall": -1.0, "unintroduced_imp": -1.0, "missing_intro_scheme": -1.0},
                metadata={"shape": shape.to_dict()},
            ))
            # For common logic goals, expose intro and split target conjunction.
            if shape.target_is_and or "∧" in task.statement:
                out.append(ExposureCandidate(
                    prefix_id="expose_intros_constructor",
                    prefix_tactic="intros\nconstructor",
                    kind="branching_intro_constructor",
                    carrier_tags=["exposure", "intro", "constructor", "and"],
                    cost=0.18,
                    branching=True,
                    gamma_debt=0.2,
                    expected_carrier_delta={"unintroduced_forall": -1.0, "unintroduced_imp": -1.0, "unsplit_and_target": -1.0},
                    metadata={"shape": shape.to_dict()},
                ))
        elif shape.target_is_and:
            out.append(ExposureCandidate(
                prefix_id="expose_constructor",
                prefix_tactic="constructor",
                kind="branching_constructor",
                carrier_tags=["exposure", "constructor", "and"],
                cost=0.15,
                branching=True,
                gamma_debt=0.2,
                expected_carrier_delta={"unsplit_and_target": -1.0},
                metadata={"shape": shape.to_dict()},
            ))
        return self._dedupe(out)

    @staticmethod
    def _dedupe(xs: list[ExposureCandidate]) -> list[ExposureCandidate]:
        seen: set[str] = set()
        out: list[ExposureCandidate] = []
        for x in xs:
            key = x.prefix_tactic.strip()
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out


class StateDependentCandidateGenerator:
    """Generate tactic candidates after focused carrier exposure.

    The produced TacticAction stores the full tactic string, exposure prefix,
    and core tactic in metadata so response quotient discovery can later forget
    raw labels and group by measured response.
    """

    def __init__(self, config: CandidateGeneratorConfig | None = None, max_exposures: int = 4):
        self.base = TacticCandidateGenerator(config or CandidateGeneratorConfig(use_carrier_exposure=False))
        self.normalizer = CarrierNormalizer()
        self.max_exposures = max_exposures

    def _core_actions(self, task: LeanTask, state: ProofState | None = None) -> list[TacticAction]:
        # Use existing generator but also include a few closure schemas that are
        # particularly useful after exposure.
        actions = self.base.candidates(task, state)
        extras = [
            TacticAction(action_id="core_simp_all", tactic="simp_all", tactic_class="simp", carrier_tags=["simp", "premise"], cost_estimate=0.75),
            TacticAction(action_id="core_constructor_simp_all", tactic="constructor <;> simp_all", tactic_class="constructor", carrier_tags=["constructor", "premise", "simp"], cost_estimate=0.95),
            TacticAction(action_id="core_constructor_assumption", tactic="constructor <;> assumption", tactic_class="constructor", carrier_tags=["constructor", "premise"], cost_estimate=0.85),
        ]
        seen = {a.tactic for a in actions}
        for e in extras:
            if e.tactic not in seen:
                actions.insert(0, e)
                seen.add(e.tactic)
        return actions

    @staticmethod
    def _compose(prefix: str, core: str) -> str:
        prefix = prefix.strip()
        core = core.strip()
        if not prefix:
            return core
        if not core:
            return prefix
        return prefix + "\n" + core

    def candidates(self, task: LeanTask, state: ProofState | None = None, max_candidates: int | None = None) -> list[TacticAction]:
        exposures_raw = self.normalizer.expose(task, state)
        exposures_raw = [e for e in exposures_raw if e.prefix_tactic.strip()] + [e for e in exposures_raw if not e.prefix_tactic.strip()]
        exposures = exposures_raw[: self.max_exposures]
        core_actions = self._core_actions(task, state)
        max_n = max_candidates or self.base.config.max_candidates
        out: list[TacticAction] = []
        seen: set[str] = set()
        for exp in exposures:
            for core in core_actions:
                full = self._compose(exp.prefix_tactic, core.tactic)
                if not full or full in seen:
                    continue
                seen.add(full)
                aid = stable_hash({"prefix": exp.prefix_tactic, "core": core.tactic, "class": core.tactic_class}, 12)
                tags = list(dict.fromkeys(exp.carrier_tags + core.carrier_tags))
                meta = dict(core.metadata or {})
                meta.update({
                    "generated_by": "state_dependent_carrier_exposure",
                    "prefix_id": exp.prefix_id,
                    "prefix_tactic": exp.prefix_tactic,
                    "prefix_kind": exp.kind,
                    "core_action_id": core.action_id,
                    "core_tactic": core.tactic,
                    "exposure": exp.to_dict(),
                })
                out.append(TacticAction(action_id=aid, tactic=full, tactic_class=core.tactic_class, carrier_tags=tags, cost_estimate=float(core.cost_estimate + exp.cost), metadata=meta))
                if len(out) >= max_n:
                    return out
        return out


__all__ = ["ExposureCandidate", "CarrierNormalizer", "StateDependentCandidateGenerator"]
