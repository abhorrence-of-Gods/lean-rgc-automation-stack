from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import math
import re
from collections import Counter, defaultdict

from .schemas import LeanTask, TacticAction, read_jsonl, write_jsonl, stable_hash


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-z_][A-Za-z0-9_'.]*|[0-9]+|[∀∃→↔∧∨=≤≥<>+*\-]", text or "")
    stop = {"theorem", "example", "by", "where", "Prop", "Type", "fun", "forall"}
    return [t for t in toks if t not in stop and len(t) > 0]


def extract_lean_names(text: str) -> list[str]:
    names: list[str] = []
    for pat in [r"\btheorem\s+([A-Za-z_][A-Za-z0-9_'.]*)", r"\blemma\s+([A-Za-z_][A-Za-z0-9_'.]*)", r"\bdef\s+([A-Za-z_][A-Za-z0-9_'.]*)"]:
        for m in re.finditer(pat, text or ""):
            names.append(m.group(1))
    return names


@dataclass
class PremiseDoc:
    doc_id: str
    name: str
    kind: str
    text: str
    tactic: str | None = None
    imports: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PremiseDoc":
        return cls(**d)


@dataclass
class PremiseHit:
    doc_id: str
    name: str
    kind: str
    score: float
    tactic: str | None = None
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PremiseIndex:
    def __init__(self, docs: list[PremiseDoc] | None = None):
        self.docs = docs or []
        self.df: Counter[str] = Counter()
        self.idf: dict[str, float] = {}
        self.doc_tf: list[Counter[str]] = []
        if docs:
            self._build_stats()

    def _build_stats(self) -> None:
        self.doc_tf = []
        self.df = Counter()
        for d in self.docs:
            tf = Counter(tokenize(d.name + " " + d.text + " " + (d.tactic or "")))
            self.doc_tf.append(tf)
            for tok in tf:
                self.df[tok] += 1
        n = max(1, len(self.docs))
        self.idf = {tok: math.log((n + 1) / (df + 0.5)) + 1.0 for tok, df in self.df.items()}

    def add(self, doc: PremiseDoc) -> None:
        self.docs.append(doc)
        self._build_stats()

    def search(self, query: str, *, k: int = 10, kind: str | None = None) -> list[PremiseHit]:
        qtf = Counter(tokenize(query))
        if not qtf:
            return []
        hits: list[PremiseHit] = []
        for i, d in enumerate(self.docs):
            if kind and d.kind != kind:
                continue
            tf = self.doc_tf[i]
            score = 0.0
            dl = sum(tf.values()) or 1
            for tok, qn in qtf.items():
                if tok not in tf:
                    continue
                score += qn * self.idf.get(tok, 1.0) * (tf[tok] / math.sqrt(dl))
            if score > 0:
                hits.append(PremiseHit(doc_id=d.doc_id, name=d.name, kind=d.kind, score=float(score), tactic=d.tactic, text=d.text[:300], metadata=d.metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def to_dict(self) -> dict[str, Any]:
        return {"version": "lean-rgc-premise-index-v0.7", "docs": [d.to_dict() for d in self.docs]}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PremiseIndex":
        return cls([PremiseDoc.from_dict(x) for x in d.get("docs", [])])

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PremiseIndex":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def docs_from_tasks(tasks_path: str | Path) -> list[PremiseDoc]:
    docs: list[PremiseDoc] = []
    for row in read_jsonl(tasks_path):
        task = LeanTask.from_dict(row)
        name = task.task_id
        # Try theorem name from statement if present.
        names = extract_lean_names(task.statement)
        if names:
            name = names[0]
        docs.append(PremiseDoc(doc_id="task:" + task.task_id, name=name, kind="task", text=task.statement, imports=task.imports, metadata={"task_id": task.task_id, "domain_tags": task.domain_tags}))
    return docs


def docs_from_actions(actions_path: str | Path) -> list[PremiseDoc]:
    docs: list[PremiseDoc] = []
    for row in read_jsonl(actions_path):
        action = TacticAction.from_dict(row)
        # Extract lemma names from rw/apply/simp brackets.
        names = re.findall(r"\b(?:rw|simp|apply|exact)\s*\[?\s*([A-Za-z_][A-Za-z0-9_'.]*)", action.tactic)
        if not names:
            names = [action.action_id]
        for name in names[:4]:
            docs.append(PremiseDoc(doc_id="action:" + action.action_id + ":" + name, name=name, kind="action", text=action.tactic, tactic=action.tactic, metadata={"action_id": action.action_id, "class": action.tactic_class, "carrier_tags": action.carrier_tags}))
    return docs


def build_premise_index(*, tasks: str | Path | None = None, actions: str | Path | None = None, out: str | Path) -> PremiseIndex:
    docs: list[PremiseDoc] = []
    if tasks:
        docs.extend(docs_from_tasks(tasks))
    if actions:
        docs.extend(docs_from_actions(actions))
    idx = PremiseIndex(docs)
    idx.save(out)
    return idx


def premise_actions_from_hits(hits: list[PremiseHit], *, prefix: str = "premise") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for h in hits:
        name = h.name
        suggestions = []
        if h.tactic:
            suggestions.append(h.tactic)
        if name and not name.startswith("core_"):
            suggestions.extend([f"apply {name}", f"rw [{name}]", f"simp [{name}]"])
        seen: set[str] = set()
        for i, tac in enumerate(suggestions):
            if not tac or tac in seen:
                continue
            seen.add(tac)
            cls = "premise"
            if tac.startswith("rw"):
                cls = "rewrite"
            elif tac.startswith("simp"):
                cls = "simp"
            elif tac.startswith("apply"):
                cls = "apply"
            rows.append({
                "action_id": stable_hash({"prefix": prefix, "doc": h.doc_id, "tactic": tac}, 14),
                "tactic": tac,
                "tactic_class": cls,
                "carrier_tags": ["premise", cls],
                "cost_estimate": max(0.2, 1.0 / (1.0 + h.score)),
                "metadata": {"generated_by": "premise_index", "premise_hit": h.to_dict()},
            })
    return rows
