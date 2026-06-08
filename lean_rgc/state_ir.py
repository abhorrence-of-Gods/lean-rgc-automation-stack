from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any
import re

from .schemas import LeanTask, ProofState, AuditRecord
from .goal_shape import parse_goal_shape, extract_hypotheses


@dataclass
class LeanHypIR:
    name: str
    type_text: str
    head: str = "unknown"
    is_prop_like: bool = False
    atoms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeanGoalIR:
    target_text: str
    target_head: str = "unknown"
    binder_count: int = 0
    implication_count: int = 0
    connective_counts: dict[str, int] = field(default_factory=dict)
    domain_tags: list[str] = field(default_factory=list)
    hypotheses: list[LeanHypIR] = field(default_factory=list)
    shape: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProofStateIR:
    state_id: str
    task_id: str
    goals: list[LeanGoalIR] = field(default_factory=list)
    raw_text: str = ""
    source: str = "text-chart"
    version: str = "lean-rgc-state-ir-v0.6"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_turnstile(text: str) -> str:
    if "⊢" in text:
        return text.split("⊢", 1)[1].strip()
    return text.strip()


def _head_of_target(target: str) -> str:
    s = target.strip()
    if s.startswith("∀") or s.startswith("forall"):
        return "forall"
    if s.startswith("fun"):
        return "lambda"
    if "→" in s or "->" in s:
        # Only call it implication if the arrow occurs at top-level-ish in this textual chart.
        return "imp"
    if "∧" in s:
        return "and"
    if "∨" in s:
        return "or"
    if "∃" in s or s.startswith("Exists"):
        return "exists"
    if re.search(r"[^<>=!]=[^=]", " " + s + " "):
        return "eq"
    if re.search(r"(≤|>=|<=|<|>)", s):
        return "order"
    return "app"


def _domain_tags(text: str) -> list[str]:
    tags = []
    checks = [
        ("Nat", ["Nat", "ℕ", " n ", "Nat."]),
        ("Int", ["Int", "ℤ"]),
        ("List", ["List", "[]", "::", "length", "map", "append"]),
        ("Bool", ["Bool", "true", "false"]),
        ("Prop", ["Prop", "∧", "∨", "→", "¬"]),
        ("Arith", ["+", "-", "*", "≤", "<", ">", "≥"]),
    ]
    for name, pats in checks:
        if any(p in text for p in pats):
            tags.append(name)
    return tags


def _connective_counts(text: str) -> dict[str, int]:
    return {
        "forall": text.count("∀") + len(re.findall(r"\bforall\b", text)),
        "imp": text.count("→") + text.count("->"),
        "and": text.count("∧"),
        "or": text.count("∨"),
        "exists": text.count("∃") + len(re.findall(r"\bExists\b", text)),
        "eq": len(re.findall(r"[^<>=!]=[^=]", " " + text + " ")),
    }


def _hyp_head(type_text: str) -> str:
    return _head_of_target(type_text)


def _hyp_atoms(type_text: str) -> dict[str, float]:
    return {
        "and_hyp": float("∧" in type_text),
        "eq_hyp": float(bool(re.search(r"[^<>=!]=[^=]", " " + type_text + " "))),
        "imp_hyp": float("→" in type_text or "->" in type_text),
    }


def parse_proof_state_ir(task: LeanTask | None = None, state: ProofState | None = None, audit: AuditRecord | None = None, text: str | None = None) -> ProofStateIR:
    parts = []
    if task is not None:
        parts.append(task.statement)
    if state is not None:
        parts.extend([state.target or "", state.goals_text or "", "\n".join(state.raw_messages or [])])
    if audit is not None:
        parts.extend(["\n".join(audit.messages or []), audit.stdout or "", audit.stderr or ""])
    if text:
        parts.append(text)
    raw = "\n".join([p for p in parts if p])
    state_id = state.state_id if state is not None else ("task:" + task.task_id if task is not None else "unknown")
    task_id = state.task_id if state is not None else (task.task_id if task is not None else "unknown")
    # Split multiple goals very conservatively; each segment with turnstile is a goal chart.
    goal_texts: list[str] = []
    if "⊢" in raw:
        segs = re.split(r"(?=⊢)", raw)
        for seg in segs:
            if "⊢" in seg:
                # Keep some context before turnstile if available by using whole raw for hyps later.
                goal_texts.append(seg.strip())
    if not goal_texts:
        target = state.target if state is not None and state.target else (task.statement if task is not None else raw)
        goal_texts = [target or raw]
    goals: list[LeanGoalIR] = []
    for gt in goal_texts[:16]:
        target = _strip_turnstile(gt)
        shape = parse_goal_shape(task=task, state=state, audit=audit, extra=gt)
        hyps_raw = extract_hypotheses(raw)
        hyps = [LeanHypIR(name=h.get("name", ""), type_text=h.get("type", ""), head=_hyp_head(h.get("type", "")), is_prop_like=("Prop" in h.get("type", "") or any(x in h.get("type", "") for x in ["∧", "∨", "→", "="])), atoms=_hyp_atoms(h.get("type", ""))) for h in hyps_raw]
        counts = _connective_counts(target)
        goals.append(LeanGoalIR(
            target_text=target,
            target_head=_head_of_target(target),
            binder_count=counts.get("forall", 0),
            implication_count=counts.get("imp", 0),
            connective_counts=counts,
            domain_tags=_domain_tags(raw),
            hypotheses=hyps,
            shape=shape.to_dict(),
        ))
    return ProofStateIR(state_id=state_id, task_id=task_id, goals=goals, raw_text=raw[:4000])


__all__ = ["LeanHypIR", "LeanGoalIR", "ProofStateIR", "parse_proof_state_ir"]
