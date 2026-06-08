from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re

from .schemas import LeanTask, stable_hash, write_jsonl
from .premise_retrieval import PremiseRecord

_IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")
_DECL_START_RE = re.compile(r"^\s*(?:@[\w\[\].,\s]+\s*)*(?P<kind>theorem|lemma|example)\b(?P<rest>.*)$")
_NAME_RE = re.compile(r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_'.]*)\b(?P<rest>.*)$")
_NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_'.]*)")
_END_NAMESPACE_RE = re.compile(r"^\s*end\s*(?:[A-Za-z_][A-Za-z0-9_'.]*)?\s*(?:--.*)?$")


def _strip_line_comment(line: str) -> str:
    return line.split("--", 1)[0] if "--" in line else line


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _domain_tags(text: str, imports: list[str]) -> list[str]:
    tags: set[str] = set()
    t = text + " " + " ".join(imports)
    probes = {
        "Nat": "nat", "Int": "int", "List": "list", "Bool": "bool", "Prop": "prop",
        "Set": "set", "Finset": "finset", "Option": "option", "Prod": "prod", "Sum": "sum",
        "≤": "order", "≥": "order", "<": "order", "+": "arith", "*": "arith", "∧": "logic", "∨": "logic", "∀": "quantifier", "∃": "quantifier",
        "Mathlib": "mathlib",
    }
    for k, v in probes.items():
        if k in t:
            tags.add(v)
    return sorted(tags)


@dataclass
class HarvestedDeclaration:
    kind: str
    name: str
    statement: str
    imports: list[str]
    file: str
    line: int
    namespace: str | None = None
    domain_tags: list[str] = field(default_factory=list)
    source: str = "lean_project"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_task(self, root: Path) -> LeanTask:
        rel = str(Path(self.file).relative_to(root)) if str(self.file).startswith(str(root)) else self.file
        tid = self.name if self.kind != "example" else f"example_{stable_hash(rel + ':' + str(self.line) + ':' + self.statement, 10)}"
        return LeanTask(
            task_id=tid,
            statement=self.statement,
            imports=list(self.imports),
            namespace=self.namespace,
            domain_tags=list(self.domain_tags),
        )

    def to_premise(self, root: Path) -> PremiseRecord:
        rel = str(Path(self.file).relative_to(root)) if str(self.file).startswith(str(root)) else self.file
        nm = self.name if self.kind != "example" else f"example_{stable_hash(rel + ':' + str(self.line), 10)}"
        return PremiseRecord(
            name=nm,
            statement=self.statement,
            imports=list(self.imports),
            namespace=self.namespace,
            domain_tags=list(self.domain_tags),
            source="lean_project",
            metadata={"kind": self.kind, "file": rel, "line": self.line, **self.metadata},
        )


def _module_import_from_path(root: Path, path: Path) -> str | None:
    try:
        rel = path.relative_to(root)
    except Exception:
        return None
    if rel.suffix != ".lean":
        return None
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts) if parts else None


def _collect_decl(lines: list[str], start: int) -> tuple[str, int]:
    chunks: list[str] = []
    i = start
    while i < len(lines):
        raw = _strip_line_comment(lines[i]).rstrip()
        chunks.append(raw)
        text = "\n".join(chunks)
        if " :=" in text:
            return text.split(" :=", 1)[0], i
        if re.search(r"\bby\b", text):
            return re.split(r"\bby\b", text, 1)[0], i
        if i > start and text.count("(") <= text.count(")") and text.count("{") <= text.count("}") and text.count("[") <= text.count("]"):
            if not raw.strip().endswith((",", "→", "->", ":")):
                return text, i
        i += 1
    return "\n".join(chunks), i


def parse_lean_file(path: str | Path, *, root: str | Path | None = None, include_examples: bool = True, include_theorems: bool = True, include_lemmas: bool = True, max_decl_chars: int = 2000) -> list[HarvestedDeclaration]:
    path = Path(path)
    rootp = Path(root) if root else path.parent
    try:
        txt = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        txt = path.read_text(errors="ignore")
    lines = txt.splitlines()
    imports: list[str] = []
    for line in lines[:200]:
        m = _IMPORT_RE.match(line)
        if m:
            imports.extend([p.strip() for p in m.group(1).split() if p.strip()])
    namespace_stack: list[str] = []
    decls: list[HarvestedDeclaration] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        ns = _NAMESPACE_RE.match(line)
        if ns:
            namespace_stack.append(ns.group(1)); i += 1; continue
        if _END_NAMESPACE_RE.match(line) and namespace_stack:
            namespace_stack.pop(); i += 1; continue
        m = _DECL_START_RE.match(line)
        if not m:
            i += 1; continue
        kind = m.group("kind")
        if (kind == "example" and not include_examples) or (kind == "theorem" and not include_theorems) or (kind == "lemma" and not include_lemmas):
            i += 1; continue
        text, end_i = _collect_decl(lines, i)
        text = _normalize_ws(text)
        if len(text) > max_decl_chars:
            text = text[:max_decl_chars]
        mm = _DECL_START_RE.match(text)
        rest = mm.group("rest") if mm else ""
        name = ""
        if kind in {"theorem", "lemma"}:
            nm = _NAME_RE.match(rest)
            if nm:
                name = nm.group("name")
        if not name:
            name = f"{kind}_{stable_hash(str(path) + ':' + str(i+1) + ':' + text, 10)}"
        ns_cur = ".".join(namespace_stack) if namespace_stack else None
        decls.append(HarvestedDeclaration(
            kind=kind,
            name=name,
            statement=text,
            imports=list(imports),
            file=str(path),
            line=i + 1,
            namespace=ns_cur,
            domain_tags=_domain_tags(text, imports),
            metadata={"module_import": _module_import_from_path(rootp, path)},
        ))
        i = max(end_i + 1, i + 1)
    return decls


def harvest_lean_project(root: str | Path, *, out_tasks: str | Path | None = None, out_premises: str | Path | None = None, glob: str = "**/*.lean", exclude: list[str] | None = None, include_examples: bool = True, include_theorems: bool = True, include_lemmas: bool = True, max_files: int | None = None, max_decls: int | None = None) -> dict[str, Any]:
    rootp = Path(root).resolve()
    exclude = exclude or [".lake", "build", ".git", "lake-packages"]
    paths: list[Path] = []
    for p in rootp.glob(glob):
        if not p.is_file() or p.suffix != ".lean":
            continue
        parts = set(p.relative_to(rootp).parts) if p.is_relative_to(rootp) else set(p.parts)
        if parts & set(exclude):
            continue
        paths.append(p)
    paths.sort()
    if max_files is not None:
        paths = paths[:max_files]
    decls: list[HarvestedDeclaration] = []
    for p in paths:
        decls.extend(parse_lean_file(p, root=rootp, include_examples=include_examples, include_theorems=include_theorems, include_lemmas=include_lemmas))
        if max_decls is not None and len(decls) >= max_decls:
            decls = decls[:max_decls]
            break
    meta: dict[str, Any] = {"root": str(rootp), "n_files": len(paths), "n_decls": len(decls), "out_tasks": str(out_tasks) if out_tasks else None, "out_premises": str(out_premises) if out_premises else None}
    if out_tasks:
        write_jsonl(out_tasks, [d.to_task(rootp).to_dict() for d in decls])
    if out_premises:
        prems = [d.to_premise(rootp).to_dict() for d in decls if d.kind in {"theorem", "lemma"}]
        write_jsonl(out_premises, prems)
        meta["n_premises"] = len(prems)
    return meta


__all__ = ["HarvestedDeclaration", "parse_lean_file", "harvest_lean_project"]
