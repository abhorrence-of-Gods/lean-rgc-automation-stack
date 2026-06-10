from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import re

from .schemas import AuditRecord, LeanTask, ProofState, read_jsonl, stable_hash, write_jsonl
from .goal_shape import parse_goal_shape, extract_hypotheses


@dataclass
class HypothesisIR:
    name: str
    type_text: str
    head: str = "unknown"
    is_prop: bool = False
    is_and: bool = False
    is_eq: bool = False
    is_forall: bool = False
    is_imp: bool = False
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GoalIR:
    raw: str
    target: str
    target_head: str
    hypotheses: list[HypothesisIR] = field(default_factory=list)
    binders: list[str] = field(default_factory=list)
    domain_tags: list[str] = field(default_factory=list)
    carrier_atoms: list[str] = field(default_factory=list)
    shape: dict[str, Any] = field(default_factory=dict)
    case_name: str | None = None
    features: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "hypotheses": [h.to_dict() for h in self.hypotheses]}


@dataclass
class ProofStateIR:
    state_id: str
    task_id: str
    goals: list[GoalIR] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    source: str = "textual_chart"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "goals": [g.to_dict() for g in self.goals]}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_'.]+|[∀∃→↔∧∨=≤≥<>+*\-]|[^\s]", text or "")


def expr_head(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "empty"
    low = t.lower()
    if t.startswith("∀") or low.startswith("forall") or re.search(r"\bforall\b", low):
        return "forall"
    if t.startswith("∃") or low.startswith("exists") or "Exists" in t:
        return "exists"
    if "→" in t or " -> " in t:
        return "imp"
    if "∧" in t or re.search(r"\bAnd\b", t) or "/\\" in t:
        return "and"
    if "∨" in t or re.search(r"\bOr\b", t) or "\\/" in t:
        return "or"
    if re.search(r"[^<>=!]=[^=>]", " " + t + " "):
        return "eq"
    if any(k in t for k in ["≤", "<", "≥", ">"]):
        return "order"
    if any(k in t for k in ["+", "-", "*"]):
        return "arith"
    return _tokens(t)[0] if _tokens(t) else "atom"


def _domain_tags(text: str) -> list[str]:
    checks = [
        ("Nat", ["Nat", "ℕ", "Nat."]),
        ("Int", ["Int", "ℤ"]),
        ("List", ["List", "[]", "::", "length", "append", "map"]),
        ("Bool", ["Bool", "true", "false"]),
        ("Prop", ["Prop", "∧", "∨", "→", "¬"]),
        ("Arith", ["+", "-", "*", "≤", "<", "≥", ">"]),
    ]
    return [name for name, pats in checks if any(p in text for p in pats)]


def hyp_ir_from_text(name: str, type_text: str) -> HypothesisIR:
    head = expr_head(type_text)
    syms = [s for s in ["∧", "∨", "=", "≤", "<", "→"] if s in type_text]
    return HypothesisIR(name=name, type_text=type_text, head=head, is_prop=("Prop" in type_text or head in {"and", "or", "imp", "forall", "exists", "eq", "order"}), is_and=head == "and", is_eq=head == "eq", is_forall=head == "forall", is_imp=head == "imp", symbols=syms)


def parse_hypotheses_from_text(raw: str) -> list[HypothesisIR]:
    out: list[HypothesisIR] = []
    seen: set[str] = set()
    for h in extract_hypotheses(raw or ""):
        name = str(h.get("name", "")).strip()
        typ = str(h.get("type", "")).strip()
        if not name or not typ or name in seen:
            continue
        seen.add(name)
        out.append(hyp_ir_from_text(name, typ))
    return out


def _target_from_raw(raw: str, fallback: str = "") -> str:
    if "⊢" in raw:
        return raw.split("⊢", 1)[1].strip().splitlines()[0].strip()
    return (raw or fallback or "").strip().splitlines()[0].strip() if (raw or fallback or "").strip() else ""


def _goal_blocks(text: str) -> list[str]:
    text = text or ""
    blocks = []
    # Keep case blocks when present.
    for part in re.split(r"(?=\n\s*case\s+)", "\n" + text):
        if "⊢" in part:
            blocks.append(part.strip())
    if blocks:
        return blocks[:32]
    if "⊢" in text:
        return [text]
    return [text] if text.strip() else []


def _carrier_atoms(shape_d: dict[str, Any]) -> list[str]:
    atoms = []
    mapping = [
        ("has_forall", "unintroduced_forall"),
        ("has_imp", "unintroduced_imp"),
        ("target_is_and", "unsplit_and_target"),
        ("has_and_hyp", "missing_and_projection"),
        ("target_is_eq", "eq_reflexive_goal"),
        ("has_arith", "nat_arith_goal"),
        ("has_list", "list_simp_goal"),
        ("has_typeclass_error", "missing_typeclass_instance"),
    ]
    for k, atom in mapping:
        if shape_d.get(k):
            atoms.append(atom)
    return atoms


def _features(target: str, hyps: list[HypothesisIR], shape_d: dict[str, Any]) -> dict[str, float]:
    return {
        "target_len": float(len(target or "")),
        "hyp_count": float(len(hyps)),
        "has_forall": float(bool(shape_d.get("has_forall"))),
        "has_imp": float(bool(shape_d.get("has_imp"))),
        "target_is_and": float(bool(shape_d.get("target_is_and"))),
        "target_is_eq": float(bool(shape_d.get("target_is_eq"))),
        "has_and_hyp": float(any(h.is_and for h in hyps) or bool(shape_d.get("has_and_hyp"))),
        "has_arith": float(bool(shape_d.get("has_arith"))),
    }


def parse_proof_state_ir(task: LeanTask | None = None, state: ProofState | None = None, audit: AuditRecord | dict[str, Any] | None = None, *, text: str | None = None, source: str = "textual_chart", status: str | None = None) -> ProofStateIR:
    parts: list[str] = []
    messages: list[str] = []
    task_id = task.task_id if task else (state.task_id if state else "parsed")
    seed: dict[str, Any] = {"task_id": task_id, "source": source}
    audit_obj: AuditRecord | None = None
    if task is not None:
        parts.append(task.statement)
        seed["statement"] = task.statement
    if state is not None:
        parts.extend([state.goals_text or "", state.local_context or "", state.target or "", "\n".join(state.raw_messages or [])])
        messages.extend(state.raw_messages or [])
        seed["state_id"] = state.state_id
    if isinstance(audit, AuditRecord):
        audit_obj = audit
        parts.extend([audit.stdout or "", audit.stderr or "", "\n".join(audit.messages or [])])
        messages.extend(audit.messages or [])
        seed["audit_status"] = audit.status
    elif isinstance(audit, dict):
        parts.extend([str(audit.get("stdout", "")), str(audit.get("stderr", "")), "\n".join(map(str, audit.get("messages", []) or []))])
        messages.extend(map(str, audit.get("messages", []) or []))
        seed["audit_status"] = audit.get("status") or audit.get("audit_status")
    if text:
        parts.append(text)
    raw_text = "\n".join(p for p in parts if p)
    if not raw_text.strip() and task is not None:
        raw_text = task.statement
    goals: list[GoalIR] = []
    for block in _goal_blocks(raw_text):
        target = _target_from_raw(block, task.statement if task else (state.target if state else ""))
        pseudo_state = state or ProofState(state_id=stable_hash(seed), task_id=task_id, target=target, goals_text=block)
        shape = parse_goal_shape(task=task, state=pseudo_state, audit=audit_obj, extra=block + "\n" + raw_text)
        shape_d = shape.to_dict()
        hyps = parse_hypotheses_from_text(block + "\n" + raw_text)
        goals.append(GoalIR(raw=block, target=target, target_head=expr_head(target), hypotheses=hyps, binders=list(shape.candidate_binders or []), domain_tags=_domain_tags(raw_text + "\n" + target), carrier_atoms=_carrier_atoms(shape_d), shape=shape_d, features=_features(target, hyps, shape_d)))
    if not goals and task is not None:
        target = task.statement
        shape = parse_goal_shape(task=task, state=state, audit=audit_obj, extra=target)
        shape_d = shape.to_dict()
        goals.append(GoalIR(raw="⊢ " + target, target=target, target_head=expr_head(target), hypotheses=[], binders=list(shape.candidate_binders or []), domain_tags=_domain_tags(target), carrier_atoms=_carrier_atoms(shape_d), shape=shape_d, features=_features(target, [], shape_d)))
    seed["goals"] = [g.target for g in goals]
    return ProofStateIR(state_id=stable_hash(seed), task_id=task_id, goals=goals, messages=messages[-80:], source=source, metadata={"n_goals": len(goals), "status": status})


def ir_rows_from_tasks(tasks_or_path: str | Path | list[Any], out_path: str | Path | None = None, *, import_mode: str = "preserve") -> list[dict[str, Any]]:
    if isinstance(tasks_or_path, (str, Path)):
        from .cli.common import _load_tasks, _normalize_tasks_imports

        tasks = _normalize_tasks_imports(_load_tasks(tasks_or_path), import_mode, None, None)
    else:
        tasks = [LeanTask.from_dict(t) if isinstance(t, dict) else t for t in tasks_or_path]
    rows = [parse_proof_state_ir(task=t, state=ProofState.from_task(t), source="task_statement").to_dict() for t in tasks]
    if out_path is not None:
        write_jsonl(out_path, rows)
    return rows


def ir_rows_from_audits(audits_or_path: str | Path | list[dict[str, Any]], out_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows_in = read_jsonl(audits_or_path) if isinstance(audits_or_path, (str, Path)) else audits_or_path
    rows: list[dict[str, Any]] = []
    for r in rows_in:
        task = LeanTask(task_id=str(r.get("task_id", "task")), statement=str(r.get("target", "")), imports=[])
        after = r.get("after_state") if isinstance(r.get("after_state"), dict) else None
        if after:
            st = ProofState.from_dict(after)
        else:
            st = ProofState(state_id=str(r.get("state_id", stable_hash(r))), task_id=task.task_id, target=str(r.get("target", "")), goals_text=str(r.get("goals_text", "")), raw_messages=list(map(str, r.get("messages", []) or [])))
        rows.append(parse_proof_state_ir(task=task, state=st, audit=r, source="audit_message").to_dict())
    if out_path is not None:
        write_jsonl(out_path, rows)
    return rows


def parse_audits_to_ir(audits_path: str | Path, out_path: str | Path) -> list[dict[str, Any]]:
    return ir_rows_from_audits(audits_path, out_path)


__all__ = ["HypothesisIR", "GoalIR", "ProofStateIR", "expr_head", "parse_proof_state_ir", "ir_rows_from_tasks", "ir_rows_from_audits", "parse_audits_to_ir"]
