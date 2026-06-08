from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .carrier import CarrierGenerator
from .carrier_acceptance import context_to_actions
from .carrier_exposure import StateDependentCandidateGenerator
from .defect_registry import DefectRegistry
from .schemas import LeanTask, ProofState, TacticAction, stable_hash, read_jsonl, write_jsonl


def active_atom_ids(registry: DefectRegistry | dict[str, Any]) -> set[str]:
    if isinstance(registry, DefectRegistry):
        atoms = registry.atoms
        return {a.atom_id for a in atoms if getattr(a, "status", "active") == "active"}
    atoms = registry.get("atoms") or registry.get("active_atoms") or []
    out = set()
    for a in atoms:
        if isinstance(a, dict):
            if a.get("status", "active") == "active":
                out.add(str(a.get("atom_id") or a.get("id")))
    return {x for x in out if x and x != "None"}


def registry_atom_aliases(registry: DefectRegistry | dict[str, Any]) -> dict[str, set[str]]:
    """Return quotient-chart aliases for registry atoms.

    Mined qgen atoms often have ids such as qgen_residual_goal_eq.  They are
    candidate charts, so downstream generators should also see their residual
    key, detector, group and intervention templates as aliases.
    """
    atoms = registry.atoms if isinstance(registry, DefectRegistry) else (registry.get("atoms") or registry.get("active_atoms") or [])
    out: dict[str, set[str]] = {}
    for a in atoms:
        if isinstance(a, dict):
            if a.get("status", "active") != "active":
                continue
            atom_id = str(a.get("atom_id") or a.get("id") or "")
            group = str(a.get("group") or "")
            detector = str(a.get("detector") or "")
            templates = a.get("intervention_templates") or []
            evidence = a.get("evidence") or {}
            desc = str(a.get("description") or "")
        else:
            if getattr(a, "status", "active") != "active":
                continue
            atom_id = str(a.atom_id)
            group = str(a.group)
            detector = str(a.detector)
            templates = list(a.intervention_templates or [])
            evidence = dict(a.evidence or {})
            desc = str(a.description or "")
        if not atom_id:
            continue
        aliases = {atom_id, group, detector}
        for key in [evidence.get("residual_key"), evidence.get("source"), desc]:
            if key:
                txt = str(key).replace(".", "_").replace("-", "_")
                aliases.add(str(key))
                aliases.update([p for p in txt.split("_") if p])
        for tmpl in templates:
            st = str(tmpl)
            aliases.add(st)
            aliases.update(st.replace("[", " ").replace("]", " ").replace(";", " ").replace("<", " ").replace(">", " ").split())
        # Coarse qgen residual aliases.
        if atom_id.startswith("qgen_residual_"):
            rest = atom_id[len("qgen_residual_"): ]
            aliases.update([p for p in rest.split("_") if p])
        out[atom_id] = {x for x in aliases if x and x != "None"}
    return out


def _action_addresses_atoms(action: TacticAction, atoms: set[str], aliases_by_atom: dict[str, set[str]] | None = None) -> bool:
    tags = set(action.carrier_tags or []) | {action.tactic_class}
    meta = action.metadata or {}
    for k in ["carrier_atoms", "carrier_atoms_addressed", "expected_atoms"]:
        vals = meta.get(k) or []
        if isinstance(vals, str):
            vals = [vals]
        tags.update(map(str, vals))
    exp = meta.get("exposure") or {}
    if isinstance(exp, dict):
        vals = exp.get("carrier_tags") or exp.get("carrier_atoms") or []
        tags.update(map(str, vals))
        vals = (exp.get("expected_carrier_delta") or {}).keys()
        tags.update(map(str, vals))
    core = meta.get("core_action") or {}
    if isinstance(core, dict):
        tags.update(map(str, core.get("carrier_tags") or []))
    # Coarse aliases.
    aliases = {
        "unintroduced_forall": {"intro", "forall", "exposure", "nonbranching_intro"},
        "unintroduced_imp": {"intro", "imp", "exposure", "nonbranching_intro"},
        "unsplit_and_target": {"constructor", "and", "branching_constructor"},
        "missing_and_projection": {"projection", "premise", "and_projection"},
        "eq_reflexive_goal": {"rfl", "eq", "exact", "simp"},
        "nat_arith_goal": {"nat", "arithmetic", "linear_arithmetic", "normalization"},
        "list_simp_goal": {"list", "simp", "list_simp_goal"},
        "missing_rewrite_orientation": {"rewrite", "rw", "simp"},
        "missing_typeclass_instance": {"typeclass", "simp"},
        "missing_induction_scheme": {"induction"},
        "missing_simp_lemma": {"simp"},
        "missing_premise_family": {"premise", "apply", "exact"},
        "constructor_branch_debt": {"constructor", "premise", "simp"},
        "metavar_exposure_debt": {"exposure", "refine", "apply", "exact"},
        "missing_domain_tactic": {"arithmetic", "nat", "ring", "normalization"},
    }
    if tags & atoms:
        return True
    aliases_by_atom = aliases_by_atom or {}
    for atom in atoms:
        if tags & aliases.get(atom, set()):
            return True
        if tags & aliases_by_atom.get(atom, set()):
            return True
    return False


@dataclass
class RegistryCandidateReport:
    task_id: str
    n_state_candidates: int
    n_registry_context_actions: int
    n_written: int
    active_atoms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RegistryGuidedCandidateGenerator:
    """Generate state-specific tactic actions from a mined defect registry.

    The output is still a candidate chart: every action must be micro-audited
    before it is treated as a response witness.
    """

    def __init__(self, registry: DefectRegistry | dict[str, Any], *, max_state_candidates: int = 64, max_context_actions: int = 64):
        self.registry = registry
        self.atoms = active_atom_ids(registry)
        self.atom_aliases = registry_atom_aliases(registry)
        self.state_gen = StateDependentCandidateGenerator(max_exposures=6)
        self.carrier_gen = CarrierGenerator()
        self.max_state_candidates = max_state_candidates
        self.max_context_actions = max_context_actions

    def candidates(self, task: LeanTask, state: ProofState | None = None) -> tuple[list[TacticAction], RegistryCandidateReport]:
        state = state or ProofState.from_task(task)
        state_text = "\n".join([task.statement or "", state.target or "", state.goals_text or "", state.local_context or ""])
        actions: list[TacticAction] = []
        state_cands = self.state_gen.candidates(task, state, max_candidates=self.max_state_candidates)
        # Keep candidates that address active atoms; if registry is empty, keep all state candidates.
        if self.atoms:
            actions.extend([a for a in state_cands if _action_addresses_atoms(a, self.atoms, self.atom_aliases)])
        else:
            actions.extend(state_cands)
        context_action_count = 0
        for ctx in self.carrier_gen.generate(sorted(self.atoms), state_text=state_text):
            for a in context_to_actions(ctx, prefix=f"reg:{task.task_id}:{ctx.get('kind','ctx')}"):
                meta = dict(a.metadata or {})
                meta.update({"generated_by": "defect_registry_carrier_generator", "carrier_context": ctx, "task_id": task.task_id})
                a.metadata = meta
                actions.append(a)
                context_action_count += 1
                if context_action_count >= self.max_context_actions:
                    break
            if context_action_count >= self.max_context_actions:
                break
        # Annotate and deduplicate by tactic string.
        by_tactic: dict[str, TacticAction] = {}
        for a in actions:
            meta = dict(a.metadata or {})
            meta.setdefault("task_id", task.task_id)
            meta.setdefault("active_registry_atoms", sorted(self.atoms))
            meta.setdefault("active_registry_aliases", {k: sorted(v)[:24] for k, v in self.atom_aliases.items()})
            a.metadata = meta
            old = by_tactic.get(a.tactic)
            if old is None or a.cost_estimate < old.cost_estimate:
                by_tactic[a.tactic] = a
        out = sorted(by_tactic.values(), key=lambda x: (x.cost_estimate, x.tactic))
        rep = RegistryCandidateReport(task_id=task.task_id, n_state_candidates=len(state_cands), n_registry_context_actions=context_action_count, n_written=len(out), active_atoms=sorted(self.atoms))
        return out, rep


def generate_registry_candidates(tasks: list[LeanTask], registry: DefectRegistry | dict[str, Any], *, max_candidates: int = 96) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gen = RegistryGuidedCandidateGenerator(registry, max_state_candidates=max_candidates, max_context_actions=max_candidates)
    rows: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for task in tasks:
        actions, rep = gen.candidates(task, ProofState.from_task(task))
        for a in actions[:max_candidates]:
            d = a.to_dict()
            d["task_id"] = task.task_id
            rows.append(d)
        reports.append(rep.to_dict())
    return rows, reports


def registry_candidates_cli(tasks_path: str | Path, registry_path: str | Path, out: str | Path, *, report_out: str | Path | None = None, max_candidates: int = 96) -> None:
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    reg = DefectRegistry.load(registry_path)
    rows, reports = generate_registry_candidates(tasks, reg, max_candidates=max_candidates)
    write_jsonl(out, rows)
    if report_out:
        write_jsonl(report_out, reports)

# Compatibility wrapper expected by v0.6 CLI imports.
def write_registry_candidates(tasks_path: str | Path, registry_path: str | Path, out: str | Path, *, report_out: str | Path | None = None, max_candidates: int = 96) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    reg = DefectRegistry.load(registry_path)
    rows, reports = generate_registry_candidates(tasks, reg, max_candidates=max_candidates)
    write_jsonl(out, rows)
    if report_out:
        write_jsonl(report_out, reports)
    return rows, reports
