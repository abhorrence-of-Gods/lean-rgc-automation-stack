from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from .goal_shape import GoalShape, parse_goal_shape
from .schemas import LeanTask, ProofState, TacticAction, stable_hash


@dataclass
class ExposureCandidate:
    prefix_id: str
    prefix_tactic: str
    kind: str
    carrier_atoms: list[str] = field(default_factory=list)
    cost: float = 0.05
    branching: bool = False
    gamma_debt: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CarrierNormalizer:
    """Focused structural exposure generator.

    Intro/projection/safe split prefixes are treated as carrier exposure, not as
    canonical tactic components. The composed full tactic is still audited by
    Lean; this object only generates quotient-safe candidates to test.
    """

    def expose(self, task: LeanTask, state: ProofState | None = None) -> list[ExposureCandidate]:
        shape = parse_goal_shape(task, state)
        prefixes: list[ExposureCandidate] = [ExposureCandidate("id", "", "identity", [], 0.0, False, 0.0, {"shape": shape.to_dict()})]

        if shape.has_forall or shape.has_imp:
            # Generic exposure. It avoids fragile binder naming.
            prefixes.append(ExposureCandidate(
                prefix_id="expose_intros",
                prefix_tactic="intros",
                kind="nonbranching_intro",
                carrier_atoms=["unintroduced_forall", "unintroduced_imp", "missing_intro_scheme"],
                cost=0.05,
                metadata={"shape": shape.to_dict()},
            ))
            # Named-intro chart for simple theorem statements; useful when later tactics refer to names.
            names = shape.candidate_binders or []
            if names:
                tactic = "\n".join(f"intro {n}" for n in names)
                prefixes.append(ExposureCandidate(
                    prefix_id="expose_named_intros_" + stable_hash(names, 6),
                    prefix_tactic=tactic,
                    kind="named_intro",
                    carrier_atoms=["unintroduced_forall", "missing_intro_scheme"],
                    cost=0.08,
                    metadata={"names": names, "shape": shape.to_dict()},
                ))

        if shape.has_and_hyp:
            # This is a chart: actual names may differ, so we generate only safe generic cases.
            prefixes.append(ExposureCandidate(
                prefix_id="expose_and_hyp_simp_all",
                prefix_tactic="simp_all",
                kind="premise_projection_simp",
                carrier_atoms=["missing_and_projection", "missing_premise_family"],
                cost=0.15,
                metadata={"shape": shape.to_dict()},
            ))

        # Target conjunction splitting is invertible but branching; keep gamma debt visible.
        if shape.target_is_and:
            prefixes.append(ExposureCandidate(
                prefix_id="expose_constructor",
                prefix_tactic="constructor",
                kind="branching_constructor",
                carrier_atoms=["unsplit_and_target", "constructor_branch_debt"],
                cost=0.2,
                branching=True,
                gamma_debt=0.25,
                metadata={"shape": shape.to_dict()},
            ))
        return prefixes


def _compose_tactic(prefix: str, core: str) -> str:
    prefix = (prefix or "").strip()
    core = (core or "").strip()
    if prefix and core:
        return prefix + "\n" + core
    return prefix or core


def compose_exposure_actions(task: LeanTask, state: ProofState | None, core_actions: list[TacticAction], *, max_exposures: int = 8) -> list[TacticAction]:
    prefixes = CarrierNormalizer().expose(task, state)[:max_exposures]
    out: list[TacticAction] = []
    for p in prefixes:
        for core in core_actions:
            full = _compose_tactic(p.prefix_tactic, core.tactic)
            if not full:
                continue
            meta = dict(core.metadata or {})
            meta.update({
                "generated_by": "carrier_normalizer" if p.prefix_id != "id" else meta.get("generated_by", "base"),
                "exposure": p.to_dict(),
                "core_action": core.to_dict(),
            })
            tags = list(dict.fromkeys((core.carrier_tags or []) + p.carrier_atoms + [p.kind]))
            cls = core.tactic_class if p.prefix_id == "id" else f"{p.kind}+{core.tactic_class}"
            aid = stable_hash({"prefix": p.prefix_tactic, "core": core.tactic, "cls": cls}, 12)
            out.append(TacticAction(
                action_id=aid,
                tactic=full,
                tactic_class=cls,
                carrier_tags=tags,
                cost_estimate=float(core.cost_estimate + p.cost + p.gamma_debt),
                max_heartbeats=core.max_heartbeats,
                metadata=meta,
            ))
    # Deduplicate by tactic string while preferring lower cost.
    by_tactic: dict[str, TacticAction] = {}
    for a in out:
        old = by_tactic.get(a.tactic)
        if old is None or a.cost_estimate < old.cost_estimate:
            by_tactic[a.tactic] = a
    return sorted(by_tactic.values(), key=lambda a: (a.cost_estimate, a.tactic))
