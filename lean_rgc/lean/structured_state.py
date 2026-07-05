from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import re

from ..schemas import AuditRecord, LeanTask, ProofState, read_jsonl, stable_hash, write_jsonl
from ..proof_ir import parse_proof_state_ir, expr_head

SCHEMA_VERSION = "lean-rgc-structured-state-v28.0"
LEGACY_SCHEMA_VERSION = "lean-rgc-structured-state-v22.0"
KERNEL_SCHEMA_VERSION = "lean-rgc-kernel-state-v28.0"


@dataclass
class GoalASTNode:
    """Structured proof-state goal chart.

    v22 still supports text-derived extraction when no Lean-kernel JSON is
    available.  The schema is intentionally close to what a future persistent
    Lean worker should return: target head, relation, binders, symbols, and
    connective counts are stable fields rather than ad-hoc regex flags.
    """

    goal_id: str
    target_text: str
    target_head: str = "unknown"
    relation: str | None = None
    root_symbol: str | None = None
    binders: list[dict[str, Any]] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    connective_counts: dict[str, int] = field(default_factory=dict)
    domain_tags: list[str] = field(default_factory=list)
    carrier_atoms: list[str] = field(default_factory=list)
    text_hash: str = ""
    source: str = "text_chart"
    expr_kind: str | None = None
    expr_json: dict[str, Any] = field(default_factory=dict)
    mvar_id: str | None = None
    local_deps: list[str] = field(default_factory=list)
    kernel_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocalContextNode:
    name: str
    type_text: str
    type_head: str = "unknown"
    symbols: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    is_instance: bool = False
    is_prop_like: bool = False
    fvar_id: str | None = None
    user_name: str | None = None
    binder_kind: str | None = None
    is_implementation_detail: bool = False
    kernel_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LocalContextGraph:
    nodes: list[LocalContextNode] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    n_nodes: int = 0
    n_edges: int = 0
    source: str = "text_chart"
    expr_kind: str | None = None
    expr_json: dict[str, Any] = field(default_factory=dict)
    mvar_id: str | None = None
    local_deps: list[str] = field(default_factory=list)
    kernel_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["nodes"] = [n.to_dict() if hasattr(n, "to_dict") else n for n in self.nodes]
        return d


@dataclass
class MetaVarGraph:
    metavariables: list[str] = field(default_factory=list)
    unsolved_goal_count: int = 0
    synthetic_mvar_count: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    source: str = "text_chart"
    expr_kind: str | None = None
    expr_json: dict[str, Any] = field(default_factory=dict)
    mvar_id: str | None = None
    local_deps: list[str] = field(default_factory=list)
    kernel_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TypeclassObligationGraph:
    obligations: list[dict[str, Any]] = field(default_factory=list)
    n_obligations: int = 0
    source: str = "text_chart"
    expr_kind: str | None = None
    expr_json: dict[str, Any] = field(default_factory=dict)
    mvar_id: str | None = None
    local_deps: list[str] = field(default_factory=list)
    kernel_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredProofState:
    state_id: str
    task_id: str
    schema_version: str = SCHEMA_VERSION
    goals: list[GoalASTNode] = field(default_factory=list)
    local_context: LocalContextGraph = field(default_factory=LocalContextGraph)
    metavars: MetaVarGraph = field(default_factory=MetaVarGraph)
    typeclasses: TypeclassObligationGraph = field(default_factory=TypeclassObligationGraph)
    messages: list[str] = field(default_factory=list)
    raw_text_hash: str = ""
    kernel_state_hash: str = ""
    extraction_backend: str = "text_chart"
    canonical_status: str = "structured_state_chart_only_not_canonical"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "task_id": self.task_id,
            "schema_version": self.schema_version,
            "goals": [g.to_dict() for g in self.goals],
            "local_context": self.local_context.to_dict(),
            "metavars": self.metavars.to_dict(),
            "typeclasses": self.typeclasses.to_dict(),
            "messages": list(self.messages),
            "raw_text_hash": self.raw_text_hash,
            "kernel_state_hash": self.kernel_state_hash,
            "extraction_backend": self.extraction_backend,
            "canonical_status": self.canonical_status,
            "metadata": dict(self.metadata),
        }


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*|[0-9]+|[∀∃→↔∧∨¬=≤≥<>+*\-/]|[^\s]")
_HYP_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_']*)\s*:\s*(.+?)\s*$")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def _symbols(text: str) -> list[str]:
    toks = _tokens(text)
    bad = {"∀", "∃", "→", "↔", "∧", "∨", "¬", "=", "≤", "≥", "<", ">", "+", "*", "-", "/", ":", ",", ".", "(", ")", "[", "]", "{", "}"}
    out: list[str] = []
    seen: set[str] = set()
    for t in toks:
        if t in bad or t.isdigit():
            continue
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:128]


def _connective_counts(text: str) -> dict[str, int]:
    text = text or ""
    return {
        "forall": text.count("∀") + len(re.findall(r"\bforall\b", text)),
        "exists": text.count("∃") + len(re.findall(r"\bExists\b|\bexists\b", text)),
        "imp": text.count("→") + text.count("->"),
        "iff": text.count("↔") + text.count("<->"),
        "and": text.count("∧") + len(re.findall(r"\bAnd\b", text)),
        "or": text.count("∨") + len(re.findall(r"\bOr\b", text)),
        "not": text.count("¬") + len(re.findall(r"\bNot\b", text)),
        "eq": len(re.findall(r"[^<>=!]=[^=>]", " " + text + " ")),
        "order": len(re.findall(r"≤|≥|<=|>=|<|>", text)),
    }


def _relation(text: str) -> str | None:
    for rel in ["↔", "≤", "≥", "<=", ">=", "=", "<", ">"]:
        if rel in text:
            return rel
    return None


def _root_symbol(text: str) -> str | None:
    toks = _tokens(text.strip())
    for t in toks:
        if t not in {"∀", "∃", "fun", "by", "("}:
            return t
    return toks[0] if toks else None


def _domain_tags(text: str) -> list[str]:
    checks = [
        ("Nat", ["Nat", "ℕ", "Nat."]),
        ("Int", ["Int", "ℤ"]),
        ("Rat", ["Rat", "ℚ"]),
        ("Real", ["Real", "ℝ"]),
        ("List", ["List", "[]", "::", "length", "append", "map"]),
        ("Bool", ["Bool", "true", "false"]),
        ("Prop", ["Prop", "∧", "∨", "→", "¬", "∀", "∃"]),
        ("Arith", ["+", "-", "*", "≤", "<", "≥", ">"]),
        ("Eq", ["="]),
    ]
    return [name for name, pats in checks if any(p in (text or "") for p in pats)]


def _carrier_atoms_for_target(text: str) -> list[str]:
    head = expr_head(text)
    atoms: list[str] = []
    if head == "forall": atoms.append("unintroduced_forall")
    if head == "imp": atoms.append("unintroduced_imp")
    if head == "and": atoms.append("unsplit_and_target")
    if head == "eq": atoms.append("eq_reflexive_goal")
    if head in {"arith", "order"} or any(k in text for k in ["+", "*", "≤", "<", "≥", ">"]): atoms.append("nat_arith_goal")
    if "List" in text or "[]" in text or "::" in text: atoms.append("list_simp_goal")
    if "?m" in text or "_uniq" in text: atoms.append("metavariable_debt")
    return atoms


def _binder_chart(target: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Textual approximation of Lean binders: ∀ x : T, ... / forall x : T, ...
    for m in re.finditer(r"(?:∀|forall)\s+([^,]+),", target or ""):
        segment = m.group(1).strip()
        names: list[str] = []
        typ = ""
        if ":" in segment:
            left, typ = segment.split(":", 1)
            names = [x.strip() for x in re.split(r"\s+", left.strip()) if x.strip()]
            typ = typ.strip()
        else:
            names = [x.strip() for x in re.split(r"\s+", segment) if x.strip()]
        for nm in names:
            out.append({"name": nm, "type_text": typ, "binder_kind": "forall", "type_head": expr_head(typ) if typ else "unknown"})
    return out[:64]


def _collect_raw_text(task: LeanTask | None, state: ProofState | None, audit: AuditRecord | dict[str, Any] | None, text: str | None) -> tuple[str, list[str]]:
    parts: list[str] = []
    messages: list[str] = []
    if task is not None:
        parts.extend([task.prefix or "", task.statement or ""])
    if state is not None:
        parts.extend([state.local_context or "", state.goals_text or "", state.target or "", "\n".join(state.raw_messages or [])])
        messages.extend(state.raw_messages or [])
    if isinstance(audit, AuditRecord):
        parts.extend([audit.stdout or "", audit.stderr or "", "\n".join(audit.messages or [])])
        messages.extend(audit.messages or [])
        if audit.after_state is not None:
            parts.extend([audit.after_state.local_context or "", audit.after_state.goals_text or "", audit.after_state.target or "", "\n".join(audit.after_state.raw_messages or [])])
            messages.extend(audit.after_state.raw_messages or [])
    elif isinstance(audit, dict):
        parts.extend([str(audit.get("stdout", "")), str(audit.get("stderr", "")), "\n".join(map(str, audit.get("messages", []) or []))])
        messages.extend(map(str, audit.get("messages", []) or []))
        st = audit.get("after_state")
        if isinstance(st, dict):
            parts.extend([str(st.get("local_context", "")), str(st.get("goals_text", "")), str(st.get("target", "")), "\n".join(map(str, st.get("raw_messages", []) or []))])
            messages.extend(map(str, st.get("raw_messages", []) or []))
    if text:
        parts.append(text)
    raw = "\n".join([p for p in parts if p])
    return raw, messages[-200:]


def _goal_texts_from_ir(task: LeanTask | None, state: ProofState | None, audit: AuditRecord | dict[str, Any] | None, text: str | None) -> list[dict[str, Any]]:
    ir = parse_proof_state_ir(task=task, state=state, audit=audit, text=text, source="structured_state_v22_seed")
    rows = []
    for i, g in enumerate(ir.goals):
        gd = g.to_dict() if hasattr(g, "to_dict") else dict(g)
        rows.append({"goal_id": f"g{i}", "target": gd.get("target") or gd.get("target_text") or "", "ir": gd})
    if not rows and task is not None:
        rows.append({"goal_id": "g0", "target": task.statement, "ir": {}})
    return rows


def _local_context_from_raw(raw: str, goal_ir_rows: list[dict[str, Any]]) -> LocalContextGraph:
    nodes: list[LocalContextNode] = []
    seen: set[str] = set()
    # Prefer hypotheses parsed by proof_ir if available.
    for gr in goal_ir_rows:
        for h in (gr.get("ir") or {}).get("hypotheses", []) or []:
            name = str(h.get("name", "")).strip()
            typ = str(h.get("type_text") or h.get("type") or "").strip()
            if name and typ and name not in seen:
                seen.add(name)
                syms = _symbols(typ)
                nodes.append(LocalContextNode(name=name, type_text=typ, type_head=expr_head(typ), symbols=syms, is_instance=name.startswith("inst") or "Class" in typ or "Decidable" in typ, is_prop_like=expr_head(typ) in {"and", "or", "imp", "forall", "exists", "eq", "order"} or "Prop" in typ))
    # Fallback line parser.
    for line in (raw or "").splitlines():
        m = _HYP_RE.match(line)
        if not m:
            continue
        name, typ = m.group(1), m.group(2).strip()
        if name in seen or name in {"case", "unsolved", "goals"}:
            continue
        seen.add(name)
        syms = _symbols(typ)
        nodes.append(LocalContextNode(name=name, type_text=typ, type_head=expr_head(typ), symbols=syms, is_instance=name.startswith("inst") or "Class" in typ or "Decidable" in typ, is_prop_like=expr_head(typ) in {"and", "or", "imp", "forall", "exists", "eq", "order"} or "Prop" in typ))
    names = {n.name for n in nodes}
    edges: list[dict[str, Any]] = []
    for n in nodes:
        deps = [nm for nm in names if nm != n.name and re.search(rf"\b{re.escape(nm)}\b", n.type_text)]
        n.depends_on = sorted(deps)
        for dep in deps:
            edges.append({"src": n.name, "dst": dep, "kind": "type_mentions_hyp"})
    return LocalContextGraph(nodes=nodes, edges=edges, n_nodes=len(nodes), n_edges=len(edges), source="text_chart_v22")


def _metavars_from_raw(raw: str, messages: list[str]) -> MetaVarGraph:
    text = (raw or "") + "\n" + "\n".join(messages or [])
    mvars = sorted(set(re.findall(r"\?[A-Za-z_][A-Za-z0-9_'.]*|\?m\.[0-9]+", text)))
    unsolved = 0
    for m in re.finditer(r"([0-9]+)\s+unsolved goals?", text):
        try: unsolved += int(m.group(1))
        except Exception: pass
    if unsolved == 0 and "unsolved goals" in text:
        unsolved = 1
    return MetaVarGraph(metavariables=mvars[:200], unsolved_goal_count=unsolved, synthetic_mvar_count=sum(1 for x in mvars if x.startswith("?m")), edges=[], source="text_chart_v22")


def _typeclass_from_raw(raw: str, messages: list[str]) -> TypeclassObligationGraph:
    text = (raw or "") + "\n" + "\n".join(messages or [])
    obligations: list[dict[str, Any]] = []
    pats = [
        r"failed to synthesize\s+([^\n]+)",
        r"failed to infer\s+([^\n]+)",
        r"typeclass instance problem is stuck\s*([^\n]*)",
        r"synthesized type class instance is not definitionally equal\s*([^\n]*)",
    ]
    for pat in pats:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            expr = m.group(1).strip() if m.groups() else m.group(0).strip()
            obligations.append({"kind": "typeclass_or_instance", "text": expr[:500], "head": expr_head(expr), "symbols": _symbols(expr)[:32]})
    # Also detect common instance metavariables/inst names in raw context.
    for m in re.finditer(r"\b(inst[A-Za-z0-9_']*)\b\s*:\s*([^\n]+)", text):
        expr = m.group(2).strip()
        obligations.append({"kind": "local_instance", "name": m.group(1), "text": expr[:500], "head": expr_head(expr), "symbols": _symbols(expr)[:32]})
    return TypeclassObligationGraph(obligations=obligations[:200], n_obligations=len(obligations[:200]), source="text_chart_v22")



def _kernel_expr_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for k in ("text", "pp", "pretty", "expr_text", "type_text", "target_text", "raw"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        if "name" in obj and isinstance(obj.get("name"), str):
            return obj["name"]
        if "head" in obj and isinstance(obj.get("head"), str):
            return obj["head"]
    return str(obj)


def _kernel_expr_kind(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for k in ("kind", "expr_kind", "node", "tag"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
    return None


def _kernel_expr_head(obj: Any, fallback_text: str = "") -> str:
    if isinstance(obj, dict):
        for k in ("head", "head_name", "const", "const_name", "decl_name", "fn"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict):
                txt = _kernel_expr_text(v)
                if txt:
                    return txt
    txt = _kernel_expr_text(obj) or fallback_text
    return expr_head(txt)


def _coerce_kernel_goal(g: Any, idx: int = 0) -> GoalASTNode:
    gd = dict(g or {}) if isinstance(g, dict) else {"target_text": str(g)}
    target_obj = gd.get("target") or gd.get("type") or gd.get("target_expr") or gd.get("expr") or gd.get("target_text") or gd.get("target_text_raw")
    target_text = str(gd.get("target_text") or gd.get("target_pp") or _kernel_expr_text(target_obj) or "")
    expr_json = target_obj if isinstance(target_obj, dict) else ({"text": target_text} if target_text else {})
    local_deps = gd.get("local_deps") or gd.get("fvar_deps") or gd.get("depends_on") or []
    if not isinstance(local_deps, list):
        local_deps = list(local_deps) if local_deps else []
    binders = gd.get("binders") or []
    if not isinstance(binders, list):
        binders = []
    carrier_atoms = gd.get("carrier_atoms") or _carrier_atoms_for_target(target_text)
    return GoalASTNode(
        goal_id=str(gd.get("goal_id") or gd.get("mvar_id") or gd.get("id") or f"g{idx}"),
        target_text=target_text,
        target_head=str(gd.get("target_head") or _kernel_expr_head(target_obj, target_text)),
        relation=gd.get("relation") or _relation(target_text),
        root_symbol=gd.get("root_symbol") or _root_symbol(target_text),
        binders=binders,
        symbols=list(gd.get("symbols") or _symbols(target_text)[:128]),
        connective_counts=dict(gd.get("connective_counts") or _connective_counts(target_text)),
        domain_tags=list(gd.get("domain_tags") or _domain_tags(target_text)),
        carrier_atoms=list(carrier_atoms or []),
        text_hash=stable_hash(target_text, n=16),
        source=str(gd.get("source") or "kernel_json_v28"),
        expr_kind=gd.get("expr_kind") or _kernel_expr_kind(target_obj),
        expr_json=expr_json,
        mvar_id=gd.get("mvar_id") or gd.get("goal_mvar_id"),
        local_deps=[str(x) for x in local_deps],
        kernel_hash=str(gd.get("kernel_hash") or stable_hash(expr_json or target_text, n=16)),
    )


def _coerce_kernel_local_context(kernel: dict[str, Any]) -> LocalContextGraph:
    lcs = kernel.get("local_contexts")
    if isinstance(lcs, list) and lcs:
        raw_nodes = []
        raw_edges = []
        for ctx in lcs:
            if isinstance(ctx, dict):
                raw_nodes.extend(ctx.get("nodes") or ctx.get("entries") or ctx.get("local_decls") or ctx.get("decls") or [])
                raw_edges.extend(ctx.get("edges") or [])
            elif isinstance(ctx, list):
                raw_nodes.extend(ctx)
    else:
        lc = kernel.get("local_context") or kernel.get("localContext") or kernel.get("lctx") or {}
        if isinstance(lc, dict):
            raw_nodes = lc.get("nodes") or lc.get("entries") or lc.get("local_decls") or lc.get("decls") or []
            raw_edges = lc.get("edges") or []
        elif isinstance(lc, list):
            raw_nodes = lc
            raw_edges = []
        else:
            raw_nodes = []
            raw_edges = []
    nodes: list[LocalContextNode] = []
    seen: set[str] = set()
    for i, n in enumerate(raw_nodes):
        nd = dict(n or {}) if isinstance(n, dict) else {"name": str(n)}
        typ_obj = nd.get("type") or nd.get("type_expr") or nd.get("type_text") or nd.get("type_pp")
        typ = str(nd.get("type_text") or nd.get("type_pp") or _kernel_expr_text(typ_obj) or "")
        name = str(nd.get("name") or nd.get("user_name") or nd.get("fvar_id") or f"h{i}")
        if name in seen:
            name = f"{name}_{i}"
        seen.add(name)
        deps = nd.get("depends_on") or nd.get("local_deps") or nd.get("fvar_deps") or []
        if not isinstance(deps, list):
            deps = []
        nodes.append(LocalContextNode(
            name=name,
            type_text=typ,
            type_head=str(nd.get("type_head") or _kernel_expr_head(typ_obj, typ)),
            symbols=list(nd.get("symbols") or _symbols(typ)[:64]),
            depends_on=[str(x) for x in deps],
            is_instance=bool(nd.get("is_instance") or nd.get("binder_kind") == "instImplicit" or name.startswith("inst")),
            is_prop_like=bool(nd.get("is_prop_like") or expr_head(typ) in {"and", "or", "imp", "forall", "exists", "eq", "order"} or "Prop" in typ),
            fvar_id=nd.get("fvar_id") or nd.get("id"),
            user_name=nd.get("user_name") or nd.get("userName"),
            binder_kind=nd.get("binder_kind") or nd.get("binderInfo"),
            is_implementation_detail=bool(nd.get("is_implementation_detail") or nd.get("impl_detail")),
            kernel_hash=str(nd.get("kernel_hash") or stable_hash(nd, n=16)),
        ))
    edges: list[dict[str, Any]] = [dict(e) for e in raw_edges if isinstance(e, dict)]
    if not edges:
        names = {n.name for n in nodes}
        fvar_to_name = {n.fvar_id: n.name for n in nodes if n.fvar_id}
        for n in nodes:
            for dep in n.depends_on:
                dep_name = fvar_to_name.get(dep, dep)
                if dep_name in names and dep_name != n.name:
                    edges.append({"src": n.name, "dst": dep_name, "kind": "kernel_dep"})
            # fallback textual mention edges for partial kernel payloads
            for maybe in names:
                if maybe != n.name and re.search(rf"\b{re.escape(maybe)}\b", n.type_text):
                    e = {"src": n.name, "dst": maybe, "kind": "type_mentions_hyp"}
                    if e not in edges:
                        edges.append(e)
    return LocalContextGraph(nodes=nodes, edges=edges, n_nodes=len(nodes), n_edges=len(edges), source="kernel_json_v28")


def _coerce_kernel_metavars(kernel: dict[str, Any], goals: list[GoalASTNode]) -> MetaVarGraph:
    raw = kernel.get("metavars") or kernel.get("metavariables") or kernel.get("mvars") or []
    entries: list[dict[str, Any]] = []
    names: list[str] = []
    for i, m in enumerate(raw if isinstance(raw, list) else []):
        md = dict(m or {}) if isinstance(m, dict) else {"mvar_id": str(m)}
        mid = str(md.get("mvar_id") or md.get("id") or md.get("name") or f"?m.{i}")
        names.append(mid)
        typ_obj = md.get("type") or md.get("type_expr") or md.get("type_text")
        typ = str(md.get("type_text") or _kernel_expr_text(typ_obj) or "")
        entries.append({
            "mvar_id": mid,
            "type_text": typ,
            "type_head": md.get("type_head") or _kernel_expr_head(typ_obj, typ),
            "assigned": bool(md.get("assigned") or md.get("assignment")),
            "synthetic": bool(md.get("synthetic") or str(mid).startswith("?m")),
            "depends_on": md.get("depends_on") or md.get("dependencies_mvars") or md.get("local_deps") or [],
        })
    # Goals with mvar ids are also metavariables.
    for g in goals:
        if g.mvar_id and g.mvar_id not in names:
            names.append(g.mvar_id)
            entries.append({"mvar_id": g.mvar_id, "type_text": g.target_text, "type_head": g.target_head, "assigned": False, "synthetic": str(g.mvar_id).startswith("?m"), "depends_on": g.local_deps})
    return MetaVarGraph(
        metavariables=names[:512],
        unsolved_goal_count=int(kernel.get("unsolved_goal_count", len(goals))),
        synthetic_mvar_count=sum(1 for x in names if str(x).startswith("?m")),
        entries=entries[:512],
        edges=[],
        source="kernel_json_v28",
    )


def _coerce_kernel_typeclasses(kernel: dict[str, Any]) -> TypeclassObligationGraph:
    raw = kernel.get("typeclasses") or kernel.get("typeclass_obligations") or kernel.get("instance_obligations") or []
    if isinstance(raw, dict):
        raw = raw.get("obligations") or raw.get("nodes") or []
    obligations: list[dict[str, Any]] = []
    for i, ob in enumerate(raw if isinstance(raw, list) else []):
        od = dict(ob or {}) if isinstance(ob, dict) else {"text": str(ob)}
        expr_obj = od.get("type") or od.get("expr") or od.get("text")
        txt = str(od.get("text") or _kernel_expr_text(expr_obj) or "")
        obligations.append({
            "obligation_id": str(od.get("obligation_id") or od.get("mvar_id") or od.get("id") or f"tc{i}"),
            "kind": od.get("kind") or "typeclass_or_instance",
            "text": txt,
            "head": od.get("head") or _kernel_expr_head(expr_obj, txt),
            "symbols": list(od.get("symbols") or _symbols(txt)[:64]),
            "status": od.get("status") or "open",
            "kernel_hash": od.get("kernel_hash") or stable_hash(od, n=16),
        })
    return TypeclassObligationGraph(obligations=obligations[:512], n_obligations=len(obligations[:512]), source="kernel_json_v28")


def extract_structured_state_from_kernel_json(kernel_state: dict[str, Any], task: LeanTask | None = None, state: ProofState | None = None, audit: AuditRecord | dict[str, Any] | None = None, *, backend: str = "kernel_json_v28", metadata: dict[str, Any] | None = None) -> StructuredProofState:
    """Normalize Lean-kernel/proof-state JSON into the v28 StructuredProofState schema.

    This is intentionally permissive: true Lean workers may use different field
    names while the protocol stabilizes.  The resulting object remains a chart,
    but its source is kernel-backed rather than regex-only text extraction.
    """
    kernel = dict(kernel_state or {})
    raw_goals = kernel.get("goals") or kernel.get("mvars") or kernel.get("metavars") or []
    if isinstance(raw_goals, dict):
        raw_goals = raw_goals.get("nodes") or raw_goals.get("goals") or []
    goals = [_coerce_kernel_goal(g, i) for i, g in enumerate(raw_goals if isinstance(raw_goals, list) else [])]
    if not goals:
        # If a worker only supplied one target, still build a kernel-sourced goal.
        target = kernel.get("target") or kernel.get("target_text") or (state.target if state else None) or (task.statement if task else "")
        if target:
            goals = [_coerce_kernel_goal({"goal_id": "g0", "target": target, "source": "kernel_json_v28_partial"}, 0)]
    task_id = str(kernel.get("task_id") or (task.task_id if task else None) or (state.task_id if state else None) or (audit.get("task_id") if isinstance(audit, dict) else None) or "unknown")
    state_id = str(kernel.get("state_id") or kernel.get("proof_state_id") or (state.state_id if state else None) or stable_hash({"kernel": kernel, "task_id": task_id}, n=16))
    messages = kernel.get("messages") or []
    if not isinstance(messages, list):
        messages = [str(messages)]
    meta = dict(metadata or {})
    meta.update(dict(kernel.get("metadata") or {}))
    meta.update({
        "kernel_schema_version": kernel.get("schema_version") or KERNEL_SCHEMA_VERSION,
        "kernel_backend": backend,
        "source_note": "v28 kernel-backed structured state; still a finite chart, not canonical",
        "n_goals": len(goals),
    })
    k_hash = str(kernel.get("kernel_state_hash") or stable_hash(kernel, n=24))
    return StructuredProofState(
        state_id=state_id,
        task_id=task_id,
        goals=goals,
        local_context=_coerce_kernel_local_context(kernel),
        metavars=_coerce_kernel_metavars(kernel, goals),
        typeclasses=_coerce_kernel_typeclasses(kernel),
        messages=[str(m) for m in messages[-200:]],
        raw_text_hash=stable_hash(json.dumps(kernel, sort_keys=True, ensure_ascii=False, default=str)[:8000], n=20),
        kernel_state_hash=k_hash,
        extraction_backend=backend,
        canonical_status="kernel_backed_structured_state_chart_not_canonical",
        metadata=meta,
    )

def extract_structured_state(task: LeanTask | None = None, state: ProofState | None = None, audit: AuditRecord | dict[str, Any] | None = None, *, text: str | None = None, backend: str = "text_chart_v28", metadata: dict[str, Any] | None = None, kernel_state: dict[str, Any] | None = None) -> StructuredProofState:
    if kernel_state is not None:
        return extract_structured_state_from_kernel_json(kernel_state, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata=metadata)
    raw, messages = _collect_raw_text(task, state, audit, text)
    goal_ir_rows = _goal_texts_from_ir(task, state, audit, text)
    goals: list[GoalASTNode] = []
    for gr in goal_ir_rows[:64]:
        target = str(gr.get("target") or "")
        ir = gr.get("ir") or {}
        counts = _connective_counts(target)
        goals.append(GoalASTNode(
            goal_id=str(gr.get("goal_id") or f"g{len(goals)}"),
            target_text=target,
            target_head=expr_head(target),
            relation=_relation(target),
            root_symbol=_root_symbol(target),
            binders=_binder_chart(target),
            symbols=_symbols(target)[:128],
            connective_counts=counts,
            domain_tags=list(ir.get("domain_tags") or _domain_tags(target + "\n" + raw)),
            carrier_atoms=list(ir.get("carrier_atoms") or _carrier_atoms_for_target(target)),
            text_hash=stable_hash(target, n=16),
            source="kernel_json_v28" if str(backend).startswith("kernel") else "text_chart_v28",
        ))
    task_id = task.task_id if task else (state.task_id if state else (str(audit.get("task_id")) if isinstance(audit, dict) and audit.get("task_id") else "unknown"))
    sid_seed = {"task_id": task_id, "raw": stable_hash(raw[:8000], n=16), "goals": [g.target_text for g in goals]}
    state_id = state.state_id if state is not None else stable_hash(sid_seed, n=16)
    meta = dict(metadata or {})
    meta.update({
        "n_goals": len(goals),
        "n_local_context_nodes": None,  # filled below
        "source_note": "v28 structured schema; text-derived unless kernel_state/kernel_json is supplied",
    })
    lc = _local_context_from_raw(raw, goal_ir_rows)
    meta["n_local_context_nodes"] = lc.n_nodes
    return StructuredProofState(
        state_id=state_id,
        task_id=task_id,
        goals=goals,
        local_context=lc,
        metavars=_metavars_from_raw(raw, messages),
        typeclasses=_typeclass_from_raw(raw, messages),
        messages=messages[-120:],
        raw_text_hash=stable_hash(raw, n=20),
        extraction_backend=backend,
        canonical_status="structured_state_chart_only_not_canonical",
        metadata=meta,
    )


def extract_structured_states_from_tasks(tasks_or_path: str | Path | list[Any], out_path: str | Path | None = None) -> list[dict[str, Any]]:
    if isinstance(tasks_or_path, (str, Path)):
        rows = read_jsonl(tasks_or_path)
    else:
        rows = tasks_or_path
    out: list[dict[str, Any]] = []
    for row in rows:
        task = row if isinstance(row, LeanTask) else LeanTask.from_dict(row)
        out.append(extract_structured_state(task=task, state=ProofState.from_task(task), backend="task_text_chart_v28").to_dict())
    if out_path is not None:
        write_jsonl(out_path, out)
    return out


def extract_structured_states_from_audits(audits_or_path: str | Path | list[dict[str, Any]], out_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows_in = read_jsonl(audits_or_path) if isinstance(audits_or_path, (str, Path)) else audits_or_path
    out: list[dict[str, Any]] = []
    for r in rows_in:
        task = LeanTask(task_id=str(r.get("task_id", "task")), statement=str(r.get("target", "")), imports=[])
        st_raw = r.get("after_state") if isinstance(r.get("after_state"), dict) else None
        state = ProofState.from_dict(st_raw) if st_raw else ProofState(state_id=str(r.get("state_id") or stable_hash(r)), task_id=task.task_id, target=str(r.get("target", "")), raw_messages=list(map(str, r.get("messages", []) or [])))
        flags = r.get("audit_flags") or {}
        kernel = r.get("kernel_state") if isinstance(r.get("kernel_state"), dict) else flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        if kernel is not None:
            out.append(extract_structured_state_from_kernel_json(kernel, task=task, state=state, audit=r, backend="audit_kernel_json_v28", metadata={"source": "audit_kernel_state"}).to_dict())
        else:
            out.append(extract_structured_state(task=task, state=state, audit=r, backend=str(flags.get("server_backend") or "audit_text_chart_v28")).to_dict())
    if out_path is not None:
        write_jsonl(out_path, out)
    return out



def extract_structured_states_from_kernel_jsonl(kernel_jsonl_or_rows: str | Path | list[dict[str, Any]], out_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows_in = read_jsonl(kernel_jsonl_or_rows) if isinstance(kernel_jsonl_or_rows, (str, Path)) else kernel_jsonl_or_rows
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows_in):
        kernel = r.get("kernel_state") if isinstance(r, dict) and isinstance(r.get("kernel_state"), dict) else r
        if not isinstance(kernel, dict):
            continue
        task = None
        if isinstance(kernel.get("task"), dict):
            task = LeanTask.from_dict(kernel["task"])
        elif kernel.get("task_id") or kernel.get("statement"):
            task = LeanTask(task_id=str(kernel.get("task_id") or f"kernel_task_{i}"), statement=str(kernel.get("statement") or kernel.get("target_text") or ""), imports=list(kernel.get("imports") or []))
        out.append(extract_structured_state_from_kernel_json(kernel, task=task, backend="kernel_jsonl_v28", metadata={"source_row_index": i}).to_dict())
    if out_path is not None:
        write_jsonl(out_path, out)
    return out

def summarize_structured_states(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    goal_heads: dict[str, int] = {}
    carriers: dict[str, int] = {}
    domains: dict[str, int] = {}
    typeclass_obligations = 0
    metavars = 0
    for r in rows:
        for g in r.get("goals", []) or []:
            goal_heads[str(g.get("target_head", "unknown"))] = goal_heads.get(str(g.get("target_head", "unknown")), 0) + 1
            for c in g.get("carrier_atoms", []) or []:
                carriers[str(c)] = carriers.get(str(c), 0) + 1
            for d in g.get("domain_tags", []) or []:
                domains[str(d)] = domains.get(str(d), 0) + 1
        typeclass_obligations += int((r.get("typeclasses") or {}).get("n_obligations", 0) or 0)
        metavars += len((r.get("metavars") or {}).get("metavariables", []) or [])
    return {
        "n_states": n,
        "schema_version": SCHEMA_VERSION,
        "goal_heads": goal_heads,
        "carrier_atoms": carriers,
        "domain_tags": domains,
        "n_typeclass_obligations": typeclass_obligations,
        "n_metavariables": metavars,
        "canonical_status": "structured_state_summary_chart_only_not_canonical",
    }


def structured_state_extract_cli(*, tasks: str | Path | None = None, audits: str | Path | None = None, kernel_jsonl: str | Path | None = None, out: str | Path, summary_out: str | Path | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if tasks:
        rows.extend(extract_structured_states_from_tasks(tasks))
    if audits:
        rows.extend(extract_structured_states_from_audits(audits))
    if kernel_jsonl:
        rows.extend(extract_structured_states_from_kernel_jsonl(kernel_jsonl))
    write_jsonl(out, rows)
    summary = summarize_structured_states(rows)
    summary["files"] = {"structured_states": str(out)}
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = [
    "SCHEMA_VERSION",
    "GoalASTNode",
    "LocalContextNode",
    "LocalContextGraph",
    "MetaVarGraph",
    "TypeclassObligationGraph",
    "StructuredProofState",
    "extract_structured_state",
    "extract_structured_state_from_kernel_json",
    "extract_structured_states_from_kernel_jsonl",
    "extract_structured_states_from_tasks",
    "extract_structured_states_from_audits",
    "summarize_structured_states",
    "structured_state_extract_cli",
]
