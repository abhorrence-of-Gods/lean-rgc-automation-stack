from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from .schemas import LeanTask, ProofState, AuditRecord


@dataclass
class HypInfo:
    name: str
    type: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "type": self.type}


@dataclass
class GoalShape:
    """Lightweight proof-state shape chart.

    This is intentionally a chart, not a canonical proof-state representation.
    It supports both the rule-based defect seed and focused carrier exposure.
    """

    has_forall: bool = False
    has_imp: bool = False
    target_is_and: bool = False
    target_is_or: bool = False
    target_is_exists: bool = False
    target_is_eq: bool = False
    target_is_true: bool = False
    has_and_hyp: bool = False
    has_eq_hyp: bool = False
    has_nat: bool = False
    has_int: bool = False
    has_list: bool = False
    has_arith: bool = False
    has_typeclass_error: bool = False
    has_unknown_identifier: bool = False
    has_rfl_failure: bool = False
    has_constructor_failure: bool = False
    has_unsolved_goals: bool = False
    has_metavar: bool = False
    candidate_binders: list[str] | None = None
    candidate_hyp_names: list[str] | None = None
    raw_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text_for(task: LeanTask | None = None, state: ProofState | None = None, extra: str = "", audit: AuditRecord | None = None) -> str:
    parts: list[str] = []
    if task is not None:
        parts.extend([task.statement or "", "\n".join(task.imports or []), " ".join(task.domain_tags or []), task.prefix or ""])
    if state is not None:
        parts.extend([state.target or "", state.goals_text or "", state.local_context or "", "\n".join(state.raw_messages or [])])
    if audit is not None:
        parts.extend(audit.messages or [])
        parts.extend([audit.stdout or "", audit.stderr or ""])
    if extra:
        parts.append(extra)
    return "\n".join(str(p) for p in parts if p)


def _target_line(text: str) -> str:
    if "⊢" in text:
        return text.split("⊢")[-1].splitlines()[0].strip()
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def _binder_names(target: str) -> list[str]:
    # Best-effort extraction for `∀ n : Nat, ...` and grouped binders
    # `∀ p q : Prop, ...`. Preserve order and avoid treating the final
    # grouped name as a singleton before the earlier names.
    names: list[str] = []
    if "∀" not in target:
        return names
    head = target.split(",", 1)[0]
    grouped = re.search(r"∀\s+(.+?)\s*:\s*[^,]+", head)
    if grouped:
        for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_']*\b", grouped.group(1)):
            if tok not in {"∀", "fun"} and tok not in names:
                names.append(tok)
    else:
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_']*)\s*:", head):
            name = m.group(1)
            if name not in names and name not in {"Prop", "Nat", "Int", "List"}:
                names.append(name)
    return names[:8]

def _hyp_names(text: str) -> list[str]:
    names: list[str] = []
    before = text.split("⊢")[0] if "⊢" in text else text
    for m in re.finditer(r"(^|\n)\s*([A-Za-z_][A-Za-z0-9_']*)\s*:", before):
        name = m.group(2)
        if name not in names and name not in {"theorem", "example"}:
            names.append(name)
    return names[:12]


def parse_goal_shape(task: LeanTask | None = None, state: ProofState | None = None, *, extra: str = "", extra_text: str = "", audit: AuditRecord | None = None) -> GoalShape:
    if extra_text and not extra:
        extra = extra_text
    text = _text_for(task, state, extra, audit)
    target = _target_line(text)
    low = text.lower()
    target_low = target.lower()
    has_forall = "∀" in target or target_low.startswith("forall") or bool(re.search(r"\bforall\b", target_low))
    has_imp = "→" in target or "->" in target or " → " in text or " -> " in text
    target_is_and = bool("∧" in target or re.search(r"\bAnd\b", target) or "/\\" in target)
    target_is_or = bool("∨" in target or re.search(r"\bOr\b", target) or "\\/" in target)
    target_is_exists = bool("∃" in target or re.search(r"\bExists\b|\bexists\b", target))
    target_is_eq = bool(re.search(r"[^<>=!]=[^=>]", target)) or " = " in target
    target_is_true = target.strip() in {"True", "true"} or "⊢ true" in low
    has_and_hyp = bool(re.search(r"(^|\n)\s*[A-Za-z_][A-Za-z0-9_']*\s*:\s*.*(∧|\bAnd\b|/\\)", text))
    has_eq_hyp = bool(re.search(r"(^|\n)\s*[A-Za-z_][A-Za-z0-9_']*\s*:\s*.*[^<>=!]=[^=>]", text))
    return GoalShape(
        has_forall=has_forall,
        has_imp=has_imp,
        target_is_and=target_is_and,
        target_is_or=target_is_or,
        target_is_exists=target_is_exists,
        target_is_eq=target_is_eq,
        target_is_true=target_is_true,
        has_and_hyp=has_and_hyp,
        has_eq_hyp=has_eq_hyp,
        has_nat="nat" in low or "ℕ" in text,
        has_int="int" in low or "ℤ" in text,
        has_list="list" in low,
        has_arith=any(k in text for k in ["+", "-", "*", "≤", "<", "≥", ">"] ) or "nat" in low or "int" in low,
        has_typeclass_error=any(k in low for k in ["failed to synthesize", "typeclass", "instance"]),
        has_unknown_identifier="unknown identifier" in low,
        has_rfl_failure="rfl failed" in low,
        has_constructor_failure="constructor" in low and ("failed" in low or "not a" in low),
        has_unsolved_goals="unsolved goal" in low,
        has_metavar="?" in text or "mvar" in low or "metavariable" in low,
        candidate_binders=_binder_names(target),
        candidate_hyp_names=_hyp_names(text),
        raw_summary=" ".join(text.split())[:512],
    )


def shape_atoms(shape: GoalShape) -> dict[str, float]:
    return {
        "unintroduced_forall": float(shape.has_forall),
        "unintroduced_imp": float(shape.has_imp),
        "unsplit_and_target": float(shape.target_is_and),
        "missing_and_projection": float(shape.has_and_hyp),
        "eq_reflexive_goal": float(shape.target_is_eq or shape.has_rfl_failure),
        "nat_arith_goal": float(shape.has_arith and (shape.has_nat or shape.has_int)),
        "list_simp_goal": float(shape.has_list),
        "missing_typeclass_instance": float(shape.has_typeclass_error),
        "constructor_branch_debt": float(shape.target_is_and or shape.has_constructor_failure),
        "metavar_exposure_debt": float(shape.has_metavar),
    }


__all__ = ["GoalShape", "HypInfo", "parse_goal_shape", "shape_atoms", "GoalShapeParser", "extract_hypotheses"]


def extract_hypotheses(text: str) -> list[dict[str, str]]:
    """Best-effort local hypothesis extraction used by candidate charts."""
    hyps = []
    before = text.split("⊢")[0] if "⊢" in text else text
    for m in re.finditer(r"(^|\n)\s*([A-Za-z_][A-Za-z0-9_']*)\s*:\s*([^\n]+)", before):
        hyps.append({"name": m.group(2), "type": m.group(3).strip()})
    return hyps


class GoalShapeParser:
    """Compatibility wrapper for older modules.

    Keep the full signature used by carrier exposure, defect mining, and IR
    extraction.  Earlier generated stacks accidentally redefined this class with
    a narrower signature at the end of the file; that made audit-aware shape
    parsing brittle.
    """

    def parse(self, task: LeanTask | None = None, state: ProofState | None = None, audit: AuditRecord | None = None, extra: str = "") -> GoalShape:
        return parse_goal_shape(task=task, state=state, audit=audit, extra=extra)
