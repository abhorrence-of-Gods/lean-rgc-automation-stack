from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import math
import re

from .schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl, stable_hash
from .goal_shape import parse_goal_shape

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*|[∀∃→↔∧∨=≤≥<>+*\-]")


def tokenize(text: str) -> list[str]:
    toks = [t for t in _TOKEN_RE.findall(text or "") if t.strip()]
    drop = {"theorem", "example", "by", "fun", "Prop", "Type", "Sort"}
    return [t for t in toks if t not in drop]


@dataclass
class PremiseRecord:
    name: str
    statement: str
    imports: list[str] = field(default_factory=list)
    namespace: str | None = None
    domain_tags: list[str] = field(default_factory=list)
    source: str = "task"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PremiseRecord":
        d = dict(d)
        if "task_id" in d and "name" not in d:
            d["name"] = d.pop("task_id")
        if "statement" not in d and "type" in d:
            d["statement"] = d.pop("type")
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PremiseCandidate:
    premise: PremiseRecord
    score: float
    overlap: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"premise": self.premise.to_dict(), "score": self.score, "overlap": self.overlap}


class PremiseIndex:
    """Small lexical premise index for Lean-RGC carrier generation.

    This is a chart-level retriever: it proposes theorem names to micro-audit.
    It does not certify that a premise is canonical or even usable in the current
    environment.  Lean replay / carrier acceptance remains the certificate.
    """

    def __init__(self, premises: list[PremiseRecord] | None = None):
        self.premises = premises or []
        self._df: dict[str, int] = {}
        self._tokens: list[set[str]] = []
        self._build()

    def _build(self) -> None:
        self._df.clear(); self._tokens.clear()
        for p in self.premises:
            toks = set(tokenize(p.name + " " + p.statement + " " + " ".join(p.domain_tags)))
            self._tokens.append(toks)
            for t in toks:
                self._df[t] = self._df.get(t, 0) + 1

    @classmethod
    def from_tasks(cls, tasks: list[LeanTask], *, include_tasks_as_premises: bool = True) -> "PremiseIndex":
        premises: list[PremiseRecord] = []
        if include_tasks_as_premises:
            for t in tasks:
                # The name may not be in scope when using standalone examples;
                # this is still useful as a retrieval chart and will be audited.
                name = re.sub(r"[^A-Za-z0-9_'.]", "_", t.task_id).strip("_") or stable_hash(t.statement, 8)
                premises.append(PremiseRecord(name=name, statement=t.statement, imports=list(t.imports), namespace=t.namespace, domain_tags=list(t.domain_tags), source="task"))
        return cls(premises)

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "PremiseIndex":
        return cls([PremiseRecord.from_dict(r) for r in read_jsonl(path)])

    def save(self, path: str | Path) -> None:
        write_jsonl(path, [p.to_dict() for p in self.premises])

    def query(self, text: str, *, top_k: int = 16, domain_tags: list[str] | None = None) -> list[PremiseCandidate]:
        q = set(tokenize(text + " " + " ".join(domain_tags or [])))
        if not q or not self.premises:
            return []
        n = max(1, len(self.premises))
        scores: list[PremiseCandidate] = []
        for p, toks in zip(self.premises, self._tokens):
            ov = sorted(q & toks)
            if not ov:
                continue
            score = 0.0
            for t in ov:
                score += math.log((n + 1.0) / (1.0 + self._df.get(t, 0))) + 1.0
            if domain_tags and set(domain_tags) & set(p.domain_tags):
                score += 1.0
            scores.append(PremiseCandidate(premise=p, score=float(score), overlap=ov))
        scores.sort(key=lambda x: (-x.score, x.premise.name))
        return scores[:top_k]

    def actions_for(self, task: LeanTask, state: ProofState | None = None, *, top_k: int = 8, max_actions: int = 48) -> list[TacticAction]:
        state = state or ProofState.from_task(task)
        shape = parse_goal_shape(task, state)
        text = "\n".join([task.statement, state.target or "", state.goals_text or "", state.local_context or ""])
        cands = self.query(text, top_k=top_k, domain_tags=list(task.domain_tags))
        actions: list[TacticAction] = []
        for c in cands:
            nm = c.premise.name
            # Skip self-name exact/apply if the premise appears to be the current task.
            templates = [
                (f"exact {nm}", "exact", ["premise", "retrieval"]),
                (f"apply {nm}", "apply", ["premise", "retrieval"]),
                (f"rw [{nm}]", "rewrite", ["rewrite", "premise", "retrieval"]),
                (f"simp [{nm}]", "simp", ["simp", "premise", "retrieval"]),
            ]
            if shape.has_forall or shape.has_imp:
                templates.extend([
                    (f"intros\nexact {nm}", "exact", ["exposure", "premise", "retrieval"]),
                    (f"intros\napply {nm}", "apply", ["exposure", "premise", "retrieval"]),
                    (f"intros\nsimp [{nm}]", "simp", ["exposure", "simp", "premise", "retrieval"]),
                ])
            for tactic, cls, tags in templates:
                meta = {
                    "generated_by": "premise_retrieval",
                    "premise": c.premise.to_dict(),
                    "retrieval_score": c.score,
                    "retrieval_overlap": c.overlap,
                }
                aid = stable_hash({"premise": nm, "tactic": tactic, "task": task.task_id}, 14)
                actions.append(TacticAction(action_id=aid, tactic=tactic, tactic_class=cls, carrier_tags=tags, cost_estimate=0.85, metadata=meta))
                if len(actions) >= max_actions:
                    return actions
        return actions


def build_premise_index_from_tasks(tasks_path: str | Path, out: str | Path) -> dict[str, Any]:
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(tasks_path)]
    idx = PremiseIndex.from_tasks(tasks)
    idx.save(out)
    return {"n_premises": len(idx.premises), "out": str(out)}


def premise_candidates_for_tasks(tasks_path: str | Path, index_path: str | Path, out: str | Path, *, top_k: int = 8, max_actions: int = 48) -> dict[str, Any]:
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(tasks_path)]
    idx = PremiseIndex.from_jsonl(index_path)
    rows: list[dict[str, Any]] = []
    for task in tasks:
        state = ProofState.from_task(task)
        for action in idx.actions_for(task, state, top_k=top_k, max_actions=max_actions):
            d = action.to_dict(); d["task_id"] = task.task_id; d.setdefault("metadata", {})["task_id"] = task.task_id
            rows.append(d)
    write_jsonl(out, rows)
    return {"n_actions": len(rows), "out": str(out), "index": str(index_path)}


__all__ = ["PremiseRecord", "PremiseCandidate", "PremiseIndex", "build_premise_index_from_tasks", "premise_candidates_for_tasks", "tokenize"]
