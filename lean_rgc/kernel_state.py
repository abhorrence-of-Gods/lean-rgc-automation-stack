from __future__ import annotations

"""Strict kernel-state payloads for Lean-RGC.

This module defines the API-level object requested by the goal-state dynamics
design.  It normalizes worker payloads into ``lean-rgc-kernel-state-v1`` and
provides a small persistent server facade.  The facade can run through the
existing file/dry-run executor, while a Lean-native worker can fill the same
schema with real kernel ``Expr`` / ``LocalDecl`` / ``MVar`` objects.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable
import json
import os
import re
import time

from .schemas import AuditRecord, LeanTask, ProofState, TacticAction, stable_hash
from .executor import LeanExecutor, LeanExecutorConfig
from .goal_state_dynamics import compute_goal_state_transition_delta

KERNEL_STATE_SCHEMA_VERSION = "lean-rgc-kernel-state-v1"
EXPR_GRAPH_SCHEMA_VERSION = "lean-rgc-expr-graph-v1"
LOCAL_CONTEXT_GRAPH_SCHEMA_VERSION = "lean-rgc-local-context-graph-v1"
MVAR_GRAPH_SCHEMA_VERSION = "lean-rgc-metavariable-graph-v1"
TYPECLASS_GRAPH_SCHEMA_VERSION = "lean-rgc-typeclass-graph-v1"
TRANSITION_SCHEMA_VERSION = "lean-rgc-kernel-transition-v1"

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*|[0-9]+|\?m\.[A-Za-z0-9_.']+|[=<>+\-*/(),:{}\[\]]")
_MVAR_RE = re.compile(r"\?[A-Za-z_][A-Za-z0-9_.']*|\?m\.[0-9A-Za-z_.']+")
_FVAR_RE = re.compile(r"\bfvar_[A-Za-z0-9_'.-]+\b")
_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_']*\b")


def _as_list(x: Any) -> list[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    return [x]


def _expr_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for key in ("pretty", "text", "pp", "expr_text", "target_text", "type_text", "raw"):
            v = x.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for key in ("const_name", "head", "name"):
            v = x.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return json.dumps(x, sort_keys=True, ensure_ascii=False, default=str)[:1000]
    return str(x)


def _expr_kind(x: Any) -> str:
    if isinstance(x, dict):
        return str(x.get("kind") or x.get("expr_kind") or x.get("node") or "text_expr")
    return "text_expr"


def _expr_head(x: Any, text: str | None = None) -> str:
    if isinstance(x, dict):
        for key in ("head", "const_name", "head_name", "decl_name"):
            v = x.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    s = text if text is not None else _expr_text(x)
    if re.search(r"\bforall\b", s):
        return "forall"
    if "->" in s:
        return "imp"
    if re.search(r"\bAnd\b", s) or "/\\" in s:
        return "and"
    if re.search(r"\bOr\b", s) or "\\/" in s:
        return "or"
    if re.search(r"[^<>=!]=[^=>]", " " + s + " "):
        return "Eq"
    if re.search(r"<=|>=|<|>", s):
        return "Order"
    toks = _TOKEN_RE.findall(s)
    return toks[0] if toks else "unknown"


def _symbols(text: str) -> list[str]:
    bad = {"forall", "fun", "by", "theorem", "example", "Prop", "Type", "True", "False"}
    out: list[str] = []
    seen: set[str] = set()
    for tok in _TOKEN_RE.findall(text or ""):
        if not _IDENT_RE.fullmatch(tok) or tok in bad or tok.isdigit():
            continue
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out[:256]


def _connective_counts(text: str) -> dict[str, int]:
    text = text or ""
    return {
        "forall": len(re.findall(r"\bforall\b", text)),
        "exists": len(re.findall(r"\bExists\b|\bexists\b", text)),
        "and": len(re.findall(r"\bAnd\b|/\\", text)),
        "or": len(re.findall(r"\bOr\b|\\/", text)),
        "imp": text.count("->"),
        "eq": len(re.findall(r"[^<>=!]=[^=>]", " " + text + " ")),
        "order": len(re.findall(r"<=|>=|<|>", text)),
    }


def _relation(text: str) -> str | None:
    for rel in ["<->", "->", "<=", ">=", "=", "<", ">"]:
        if rel in (text or ""):
            return rel
    return None


def _domain_tags(text: str) -> list[str]:
    checks = [
        ("Nat", ["Nat", "Nat."]),
        ("Int", ["Int", "Int."]),
        ("Rat", ["Rat", "Rat."]),
        ("Real", ["Real", "Real."]),
        ("List", ["List", "[]", "::", "length", "map", "append"]),
        ("Bool", ["Bool", "true", "false"]),
        ("Eq", ["="]),
        ("Arith", ["+", "-", "*", "/", "<=", ">=", "<", ">"]),
        ("Prop", ["Prop", "forall", "Exists", "->", "And", "Or", "Not"]),
    ]
    return [name for name, pats in checks if any(p in (text or "") for p in pats)]


def _carrier_atoms(text: str) -> list[str]:
    head = _expr_head(text)
    atoms: list[str] = []
    if head == "forall":
        atoms.append("unintroduced_forall")
    if head == "imp":
        atoms.append("unintroduced_imp")
    if head == "and":
        atoms.append("unsplit_and_target")
    if head == "Eq":
        atoms.append("eq_goal")
    if any(p in (text or "") for p in ["Nat", "+", "-", "*", "/", "<=", ">=", "<", ">"]):
        atoms.append("nat_arith_goal")
    if "?m" in (text or ""):
        atoms.append("metavariable_debt")
    return atoms


def _local_context_payloads(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("local_contexts")
    if isinstance(raw, list) and raw:
        out: list[dict[str, Any]] = []
        for i, ctx in enumerate(raw):
            if isinstance(ctx, dict):
                out.append(dict(ctx))
            elif isinstance(ctx, list):
                out.append({"local_context_graph_id": f"lctx_{i}", "nodes": ctx, "edges": []})
        return out
    lc = kernel.get("local_context") or kernel.get("localContext") or kernel.get("lctx") or {}
    if isinstance(lc, dict):
        return [dict(lc)]
    if isinstance(lc, list):
        return [{"nodes": lc, "edges": []}]
    return [{"nodes": [], "edges": []}]


def _local_decl_nodes(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for ctx in _local_context_payloads(kernel):
        raw = ctx.get("nodes") or ctx.get("entries") or ctx.get("local_decls") or ctx.get("decls") or []
        for n in raw if isinstance(raw, list) else []:
            nodes.append(dict(n or {}) if isinstance(n, dict) else {"user_name": str(n), "name": str(n)})
    return nodes


def _raw_goals(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("goals") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or raw.get("goals") or []
    return [dict(g or {}) if isinstance(g, dict) else {"target": str(g)} for g in _as_list(raw)]


def _raw_mvars(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("metavars") or kernel.get("metavariables") or kernel.get("mvars") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or raw.get("entries") or []
    return [dict(m or {}) if isinstance(m, dict) else {"mvar_id": str(m)} for m in _as_list(raw)]


def _raw_typeclasses(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("typeclasses") or kernel.get("typeclass_obligations") or kernel.get("instance_obligations") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or raw.get("obligations") or []
    return [dict(t or {}) if isinstance(t, dict) else {"text": str(t)} for t in _as_list(raw)]


def _binder_name_map(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    next_idx = 0
    for m in re.finditer(r"\bforall\s+([^,]+),", text or ""):
        segment = m.group(1)
        left = segment.split(":", 1)[0] if ":" in segment else segment
        for name in _IDENT_RE.findall(left):
            if name in {"_", "Nat", "Int", "Prop", "Type"}:
                continue
            if name not in mapping:
                mapping[name] = f"#b{next_idx}"
                next_idx += 1
    return mapping


def _alpha_maps(kernel: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    fvars: dict[str, str] = {}
    next_idx = 0
    for node in _local_decl_nodes(kernel):
        keys = [
            node.get("fvar_id"),
            node.get("id"),
            node.get("user_name"),
            node.get("name"),
        ]
        for key in keys:
            if isinstance(key, str) and key and key not in fvars:
                fvars[key] = f"#l{next_idx}"
        if any(isinstance(k, str) and k for k in keys):
            next_idx += 1
    for goal in _raw_goals(kernel):
        txt = _expr_text(goal.get("target") or goal.get("target_text") or goal.get("type") or "")
        for name, repl in _binder_name_map(txt).items():
            fvars.setdefault(name, repl)

    mvars: dict[str, str] = {}
    for i, mv in enumerate(_raw_mvars(kernel)):
        mid = str(mv.get("mvar_id") or mv.get("id") or mv.get("name") or f"?m.{i}")
        mvars.setdefault(mid, f"?g{i}")
    for i, goal in enumerate(_raw_goals(kernel)):
        mid = goal.get("mvar_id") or goal.get("goal_mvar_id")
        if mid:
            mvars.setdefault(str(mid), f"?g{i}")
    return fvars, mvars


def _normalize_text(text: str, fvars: dict[str, str], mvars: dict[str, str]) -> str:
    out = text or ""
    # Add binder-local mappings from this expression when no local context exists.
    local = dict(fvars)
    for name, repl in _binder_name_map(out).items():
        local.setdefault(name, repl)
    for raw, repl in sorted(local.items(), key=lambda kv: len(kv[0]), reverse=True):
        if raw.startswith("?"):
            continue
        if _IDENT_RE.fullmatch(raw):
            out = re.sub(rf"\b{re.escape(raw)}\b", repl, out)
        else:
            out = out.replace(raw, repl)
    for raw, repl in sorted(mvars.items(), key=lambda kv: len(kv[0]), reverse=True):
        out = out.replace(raw, repl)
    out = _MVAR_RE.sub(lambda m: mvars.setdefault(m.group(0), f"?g{len(mvars)}"), out)
    out = _FVAR_RE.sub(lambda m: local.setdefault(m.group(0), f"#l{len(local)}"), out)
    out = re.sub(r"\bforall\s+([^,]+),", lambda m: "forall " + re.sub(r"#b[0-9]+", "_", m.group(1)) + ",", out)
    return re.sub(r"\s+", " ", out).strip()


def _norm_hash(obj: Any, fvars: dict[str, str], mvars: dict[str, str]) -> str:
    if isinstance(obj, dict):
        basis = {
            "kind": _expr_kind(obj),
            "head": _expr_head(obj),
            "text": _normalize_text(_expr_text(obj), fvars, mvars),
            "children": [_norm_hash(c, fvars, mvars) for c in _as_list(obj.get("children") or obj.get("args"))],
        }
        return stable_hash(basis, n=24)
    return stable_hash(_normalize_text(_expr_text(obj), fvars, mvars), n=24)


def _expr_node(expr: Any, *, role: str, owner: str, fvars: dict[str, str], mvars: dict[str, str]) -> dict[str, Any]:
    raw = dict(expr) if isinstance(expr, dict) else {"pretty": _expr_text(expr), "kind": "text_expr"}
    text = _expr_text(raw)
    children = [str(c.get("expr_id") if isinstance(c, dict) else c) for c in _as_list(raw.get("children") or raw.get("args"))]
    free_fvars = [x for x in fvars if re.search(rf"\b{re.escape(x)}\b", text)]
    free_mvars = [x for x in mvars if x in text]
    node = {
        "expr_id": str(raw.get("expr_id") or raw.get("id") or "expr_" + stable_hash({"role": role, "owner": owner, "expr": raw}, n=16)),
        "kind": _expr_kind(raw),
        "head": _expr_head(raw, text),
        "const_name": raw.get("const_name") if isinstance(raw.get("const_name"), str) else None,
        "levels": list(raw.get("levels") or []),
        "binder_info": raw.get("binder_info") or raw.get("binderInfo"),
        "children": children,
        "type_expr_id": raw.get("type_expr_id") or raw.get("type"),
        "free_fvars": free_fvars,
        "free_mvars": free_mvars,
        "pretty": text,
        "role": role,
        "owner": owner,
        "raw_hash": str(raw.get("raw_hash") or stable_hash(raw, n=24)),
        "norm_hash": str(raw.get("norm_hash") or _norm_hash(raw, fvars, mvars)),
    }
    return node


def build_expr_graph_v1(kernel_state: dict[str, Any]) -> dict[str, Any]:
    kernel = dict(kernel_state or {})
    fvars, mvars = _alpha_maps(kernel)
    supplied = kernel.get("expr_graph") if isinstance(kernel.get("expr_graph"), dict) else {}
    nodes: list[dict[str, Any]] = []
    roots: list[str] = []
    edges: list[dict[str, Any]] = []

    for raw_node in supplied.get("nodes") or []:
        if isinstance(raw_node, dict):
            node = _expr_node(raw_node, role=str(raw_node.get("role") or "native"), owner=str(raw_node.get("owner") or ""), fvars=fvars, mvars=mvars)
            nodes.append(node)
            for child in node.get("children") or []:
                edges.append({"src": node["expr_id"], "dst": child, "kind": "expr_child"})
    roots.extend([str(x) for x in _as_list(supplied.get("roots")) if x])

    for i, goal in enumerate(_raw_goals(kernel)):
        expr = goal.get("target") or goal.get("target_expr") or goal.get("type") or goal.get("target_text") or ""
        owner = str(goal.get("mvar_id") or goal.get("goal_id") or f"g{i}")
        node = _expr_node(expr, role="goal_target", owner=owner, fvars=fvars, mvars=mvars)
        nodes.append(node)
        roots.append(node["expr_id"])

    for i, decl in enumerate(_local_decl_nodes(kernel)):
        owner = str(decl.get("fvar_id") or decl.get("user_name") or decl.get("name") or f"fvar_{i}")
        typ = decl.get("type") or decl.get("type_expr") or decl.get("type_text") or ""
        node = _expr_node(typ, role="local_decl_type", owner=owner, fvars=fvars, mvars=mvars)
        nodes.append(node)
        val = decl.get("value") or decl.get("value_expr") or decl.get("value_text")
        if val is not None:
            nodes.append(_expr_node(val, role="local_decl_value", owner=owner, fvars=fvars, mvars=mvars))

    for i, mv in enumerate(_raw_mvars(kernel)):
        owner = str(mv.get("mvar_id") or mv.get("id") or f"?m.{i}")
        typ = mv.get("type") or mv.get("type_expr") or mv.get("type_text") or mv.get("target") or ""
        nodes.append(_expr_node(typ, role="metavar_type", owner=owner, fvars=fvars, mvars=mvars))
        if mv.get("assignment") is not None or mv.get("assignment_expr") is not None:
            nodes.append(_expr_node(mv.get("assignment") or mv.get("assignment_expr"), role="metavar_assignment", owner=owner, fvars=fvars, mvars=mvars))

    for i, tc in enumerate(_raw_typeclasses(kernel)):
        owner = str(tc.get("obligation_id") or tc.get("mvar_id") or f"tc_{i}")
        expr = tc.get("target") or tc.get("target_expr") or tc.get("expr") or tc.get("text") or ""
        nodes.append(_expr_node(expr, role="typeclass_obligation", owner=owner, fvars=fvars, mvars=mvars))

    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        by_id.setdefault(node["expr_id"], node)
    nodes = list(by_id.values())[:4096]
    ids = {n["expr_id"] for n in nodes}
    roots = [r for r in roots if r in ids]
    if not roots and nodes:
        roots = [nodes[0]["expr_id"]]
    edges.extend([dict(e) for e in supplied.get("edges") or [] if isinstance(e, dict)])
    edges = [e for e in edges if e.get("src") in ids and e.get("dst") in ids][:8192]
    return {
        "schema_version": EXPR_GRAPH_SCHEMA_VERSION,
        "nodes": nodes,
        "edges": edges,
        "roots": roots,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "source": "native_expr_graph" if supplied.get("nodes") else "kernel_payload_synthesized_expr_graph",
    }


def _expr_id_for(expr_graph: dict[str, Any], role: str, owner: str) -> str | None:
    for node in expr_graph.get("nodes") or []:
        if isinstance(node, dict) and node.get("role") == role and str(node.get("owner")) == str(owner):
            return str(node.get("expr_id"))
    return None


def build_local_contexts_v1(kernel_state: dict[str, Any], expr_graph: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    kernel = dict(kernel_state or {})
    expr_graph = expr_graph or build_expr_graph_v1(kernel)
    fvars, mvars = _alpha_maps(kernel)
    contexts: list[dict[str, Any]] = []
    for ctx_i, ctx in enumerate(_local_context_payloads(kernel)):
        raw_nodes = ctx.get("nodes") or ctx.get("entries") or ctx.get("local_decls") or ctx.get("decls") or []
        nodes: list[dict[str, Any]] = []
        for i, raw in enumerate(raw_nodes if isinstance(raw_nodes, list) else []):
            d = dict(raw or {}) if isinstance(raw, dict) else {"user_name": str(raw), "name": str(raw)}
            fvar_id = str(d.get("fvar_id") or d.get("id") or f"fvar_{ctx_i}_{i}")
            user_name = str(d.get("user_name") or d.get("name") or fvar_id)
            typ = d.get("type") or d.get("type_expr") or d.get("type_text") or ""
            val = d.get("value") or d.get("value_expr") or d.get("value_text")
            type_text = _expr_text(typ)
            value_text = _expr_text(val) if val is not None else ""
            known_fvars = set(fvars) - {fvar_id, user_name}
            depends_fvars = set(map(str, _as_list(d.get("depends_on_fvars") or d.get("depends_on") or d.get("local_deps"))))
            for raw_name in known_fvars:
                if raw_name and re.search(rf"\b{re.escape(raw_name)}\b", type_text + "\n" + value_text):
                    depends_fvars.add(raw_name)
            depends_mvars = sorted({mid for mid in mvars if mid in type_text or mid in value_text})
            node = {
                "fvar_id": fvar_id,
                "user_name": user_name,
                "binder_kind": str(d.get("binder_kind") or d.get("binderInfo") or "default"),
                "type_expr_id": _expr_id_for(expr_graph, "local_decl_type", fvar_id) or _expr_id_for(expr_graph, "local_decl_type", user_name),
                "value_expr_id": _expr_id_for(expr_graph, "local_decl_value", fvar_id) or _expr_id_for(expr_graph, "local_decl_value", user_name),
                "type_text": type_text,
                "value_text": value_text or None,
                "is_implementation_detail": bool(d.get("is_implementation_detail") or d.get("impl_detail")),
                "is_instance": bool(d.get("is_instance") or str(d.get("binder_kind")) == "instImplicit" or user_name.startswith("inst")),
                "depends_on_fvars": sorted(depends_fvars),
                "depends_on_mvars": depends_mvars,
                "raw_hash": str(d.get("raw_hash") or stable_hash(d, n=24)),
                "norm_hash": str(d.get("norm_hash") or stable_hash({
                    "binder_kind": d.get("binder_kind") or "default",
                    "type": _normalize_text(type_text, fvars, mvars),
                    "value": _normalize_text(value_text, fvars, mvars),
                    "is_instance": bool(d.get("is_instance")),
                }, n=24)),
            }
            nodes.append(node)
        fvar_ids = {n["fvar_id"] for n in nodes}
        name_to_fvar = {n["user_name"]: n["fvar_id"] for n in nodes}
        edges: list[dict[str, Any]] = []
        for e in ctx.get("edges") or []:
            if isinstance(e, dict):
                edges.append(dict(e))
        for node in nodes:
            for dep in node.get("depends_on_fvars") or []:
                dep_id = name_to_fvar.get(str(dep), str(dep))
                if dep_id in fvar_ids and dep_id != node["fvar_id"]:
                    edge = {"src": dep_id, "dst": node["fvar_id"], "kind": "decl_type_or_value_depends_on_fvar"}
                    if edge not in edges:
                        edges.append(edge)
        graph_id = str(ctx.get("local_context_graph_id") or ctx.get("id") or "lctx_" + stable_hash({"state": kernel.get("state_id"), "i": ctx_i, "nodes": nodes}, n=12))
        contexts.append({
            "schema_version": LOCAL_CONTEXT_GRAPH_SCHEMA_VERSION,
            "local_context_graph_id": graph_id,
            "nodes": nodes,
            "edges": edges,
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "raw_hash": stable_hash({"nodes": [n["raw_hash"] for n in nodes], "edges": edges}, n=24),
            "norm_hash": stable_hash({"nodes": [n["norm_hash"] for n in nodes], "edges": edges}, n=24),
            "source": str(ctx.get("source") or "kernel_local_context_payload"),
        })
    if not contexts:
        contexts.append({
            "schema_version": LOCAL_CONTEXT_GRAPH_SCHEMA_VERSION,
            "local_context_graph_id": "lctx_empty",
            "nodes": [],
            "edges": [],
            "n_nodes": 0,
            "n_edges": 0,
            "raw_hash": stable_hash([], n=24),
            "norm_hash": stable_hash([], n=24),
            "source": "empty_local_context",
        })
    return contexts


def build_goals_v1(kernel_state: dict[str, Any], expr_graph: dict[str, Any], local_contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kernel = dict(kernel_state or {})
    fvars, mvars = _alpha_maps(kernel)
    default_lctx = local_contexts[0]["local_context_graph_id"] if local_contexts else "lctx_empty"
    default_lctx_norm = local_contexts[0].get("norm_hash") if local_contexts else "empty_lctx"
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(_raw_goals(kernel)):
        target_obj = raw.get("target") or raw.get("target_expr") or raw.get("type") or raw.get("target_text") or ""
        target_text = str(raw.get("target_text") or raw.get("pretty") or _expr_text(target_obj))
        mvar_id = str(raw.get("mvar_id") or raw.get("goal_mvar_id") or f"?m.goal.{i}")
        target_expr_id = _expr_id_for(expr_graph, "goal_target", mvar_id) or _expr_id_for(expr_graph, "goal_target", str(raw.get("goal_id") or f"g{i}"))
        normalized = _normalize_text(target_text, fvars, mvars)
        goal = {
            "goal_id": str(raw.get("goal_id") or f"g{i}"),
            "mvar_id": mvar_id,
            "target_expr_id": target_expr_id,
            "target_head": str(raw.get("target_head") or _expr_head(target_obj, target_text)),
            "relation": raw.get("relation") or _relation(target_text),
            "local_context_graph_id": str(raw.get("local_context_graph_id") or default_lctx),
            "target_symbols": list(raw.get("target_symbols") or raw.get("symbols") or _symbols(target_text)),
            "domain_tags": list(raw.get("domain_tags") or _domain_tags(target_text)),
            "connective_counts": dict(raw.get("connective_counts") or _connective_counts(target_text)),
            "carrier_atoms_readout": list(raw.get("carrier_atoms_readout") or raw.get("carrier_atoms") or _carrier_atoms(target_text)),
            "target_text": target_text,
            "target": {"text": target_text, "kind": _expr_kind(target_obj), "head": _expr_head(target_obj, target_text)},
            "local_deps": list(raw.get("local_deps") or raw.get("local_context_fvars") or []),
            "raw_hash": str(raw.get("raw_hash") or stable_hash(raw, n=24)),
            "norm_hash": str(raw.get("norm_hash") or stable_hash({"target": normalized, "lctx_norm": default_lctx_norm}, n=24)),
        }
        out.append(goal)
    return out


def build_metavars_v1(kernel_state: dict[str, Any], expr_graph: dict[str, Any], goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kernel = dict(kernel_state or {})
    fvars, mvars = _alpha_maps(kernel)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(_raw_mvars(kernel)):
        mid = str(raw.get("mvar_id") or raw.get("id") or raw.get("name") or f"?m.{i}")
        seen.add(mid)
        typ = raw.get("type") or raw.get("type_expr") or raw.get("type_text") or raw.get("target") or ""
        assignment = raw.get("assignment") or raw.get("assignment_expr")
        type_text = _expr_text(typ)
        assignment_text = _expr_text(assignment) if assignment is not None else ""
        rows.append({
            "mvar_id": mid,
            "user_name": str(raw.get("user_name") or raw.get("name") or ""),
            "type_expr_id": _expr_id_for(expr_graph, "metavar_type", mid),
            "type_text": type_text,
            "local_context_fvars": [str(x) for x in _as_list(raw.get("local_context_fvars") or raw.get("local_deps"))],
            "assigned": bool(raw.get("assigned") or assignment is not None),
            "assignment_expr_id": _expr_id_for(expr_graph, "metavar_assignment", mid),
            "kind": str(raw.get("kind") or ("goal" if any(g.get("mvar_id") == mid for g in goals) else "natural")),
            "dependencies_mvars": [str(x) for x in _as_list(raw.get("dependencies_mvars") or raw.get("depends_on"))],
            "dependencies_fvars": [str(x) for x in _as_list(raw.get("dependencies_fvars") or raw.get("local_deps"))],
            "raw_hash": str(raw.get("raw_hash") or stable_hash(raw, n=24)),
            "norm_hash": str(raw.get("norm_hash") or stable_hash({
                "mvar": mvars.get(mid, "?g"),
                "type": _normalize_text(type_text, fvars, mvars),
                "assignment": _normalize_text(assignment_text, fvars, mvars),
                "assigned": bool(raw.get("assigned") or assignment is not None),
            }, n=24)),
        })
    for g in goals:
        mid = str(g.get("mvar_id") or "")
        if mid and mid not in seen:
            rows.append({
                "mvar_id": mid,
                "user_name": "",
                "type_expr_id": g.get("target_expr_id"),
                "type_text": str(g.get("target_text") or ""),
                "local_context_fvars": [str(x) for x in _as_list(g.get("local_deps"))],
                "assigned": False,
                "assignment_expr_id": None,
                "kind": "goal",
                "dependencies_mvars": [],
                "dependencies_fvars": [str(x) for x in _as_list(g.get("local_deps"))],
                "raw_hash": stable_hash(g, n=24),
                "norm_hash": stable_hash({"mvar": mvars.get(mid, "?g"), "target": g.get("norm_hash")}, n=24),
            })
    return rows


def build_typeclasses_v1(kernel_state: dict[str, Any], expr_graph: dict[str, Any]) -> list[dict[str, Any]]:
    kernel = dict(kernel_state or {})
    fvars, mvars = _alpha_maps(kernel)
    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(_raw_typeclasses(kernel)):
        expr = raw.get("target") or raw.get("target_expr") or raw.get("expr") or raw.get("text") or ""
        text = str(raw.get("text") or _expr_text(expr))
        oid = str(raw.get("obligation_id") or raw.get("mvar_id") or raw.get("id") or f"tc_{i}")
        rows.append({
            "obligation_id": oid,
            "mvar_id": str(raw.get("mvar_id") or oid),
            "class_head": str(raw.get("class_head") or raw.get("head") or _expr_head(expr, text)),
            "target_expr_id": _expr_id_for(expr_graph, "typeclass_obligation", oid),
            "target_text": text,
            "arguments": [str(x) for x in _as_list(raw.get("arguments") or raw.get("args"))],
            "local_instances": [str(x) for x in _as_list(raw.get("local_instances"))],
            "status": str(raw.get("status") or "pending"),
            "messages": [str(x) for x in _as_list(raw.get("messages"))],
            "depends_on": [str(x) for x in _as_list(raw.get("depends_on") or raw.get("dependencies"))],
            "raw_hash": str(raw.get("raw_hash") or stable_hash(raw, n=24)),
            "norm_hash": str(raw.get("norm_hash") or stable_hash({
                "class_head": raw.get("class_head") or _expr_head(expr, text),
                "target": _normalize_text(text, fvars, mvars),
                "status": raw.get("status") or "pending",
            }, n=24)),
        })
    return rows


def _project_fingerprint(workdir: str | Path | None, lean_cmd: str = "lake env lean") -> str:
    root = Path(workdir or os.getcwd())
    parts: dict[str, Any] = {"root": str(root.resolve()) if root.exists() else str(root), "lean_cmd": lean_cmd}
    for name in ["lean-toolchain", "lakefile.lean", "lakefile.toml", "lake-manifest.json", "lake-manifest.toml"]:
        p = root / name
        if p.exists() and p.is_file():
            try:
                data = p.read_text(encoding="utf-8", errors="ignore")
                parts[name] = stable_hash({"content": data, "size": p.stat().st_size}, n=16)
            except Exception:
                parts[name] = "unreadable"
    return stable_hash(parts, n=24)


def normalize_kernel_state_v1(
    kernel_state: dict[str, Any],
    *,
    env_fingerprint: str | None = None,
    options: dict[str, Any] | None = None,
    proof_prefix: str | None = None,
    status: str | None = None,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a worker payload into the strict v1 kernel-state schema."""
    kernel = dict(kernel_state or {})
    expr_graph = build_expr_graph_v1(kernel)
    local_contexts = build_local_contexts_v1(kernel, expr_graph)
    goals = build_goals_v1(kernel, expr_graph, local_contexts)
    metavars = build_metavars_v1(kernel, expr_graph, goals)
    typeclasses = build_typeclasses_v1(kernel, expr_graph)
    state_id = str(kernel.get("state_id") or kernel.get("id") or stable_hash(kernel, n=16))
    task_id = str(kernel.get("task_id") or "unknown")
    closed = bool(kernel.get("closed")) or (not goals and not any(not m.get("assigned") for m in metavars))
    status_val = status or str(kernel.get("status") or ("closed" if closed else "open"))
    options_val = dict(options or kernel.get("options") or {})
    env_fp = env_fingerprint or str(kernel.get("env_fingerprint") or kernel.get("project_fingerprint") or kernel.get("EnvFingerprint") or "")
    if not env_fp:
        env_fp = stable_hash({"backend": kernel.get("backend") or kernel.get("extraction_backend"), "task_id": task_id}, n=24)
    prefix = proof_prefix if proof_prefix is not None else str(kernel.get("proof_prefix") or kernel.get("prefix") or "")
    messages = kernel.get("messages") or []
    if not isinstance(messages, list):
        messages = [messages]
    raw_basis = {
        "env": env_fp,
        "options": options_val,
        "goals": [(g.get("mvar_id"), g.get("raw_hash")) for g in goals],
        "local_contexts": [(c.get("local_context_graph_id"), c.get("raw_hash")) for c in local_contexts],
        "metavars": [(m.get("mvar_id"), m.get("raw_hash"), m.get("assigned")) for m in metavars],
        "typeclasses": [(tc.get("obligation_id"), tc.get("raw_hash"), tc.get("status")) for tc in typeclasses],
        "status": status_val,
    }
    norm_basis = {
        "env": env_fp,
        "options": options_val,
        "goals": [g.get("norm_hash") for g in goals],
        "local_contexts": [c.get("norm_hash") for c in local_contexts],
        "metavars": [m.get("norm_hash") for m in metavars],
        "typeclasses": [tc.get("norm_hash") for tc in typeclasses],
        "status": status_val,
    }
    object_coverage = {
        "expr_ast": bool((kernel.get("expr_graph") or {}).get("nodes")) if isinstance(kernel.get("expr_graph"), dict) else False,
        "local_decl_graph": bool(local_contexts and local_contexts[0].get("nodes")),
        "metavariable_graph": bool(metavars),
        "typeclass_graph": bool(typeclasses),
        "in_memory_state_id": bool(state_id),
        "tactic_transition_api": bool(kernel.get("tactic_transition_api") or kernel.get("goal_state_transition_api")),
        "replay_certificate": bool(kernel.get("replay_certificate") or kernel.get("replay")),
        "source": kernel.get("backend") or kernel.get("extraction_backend") or "kernel_state_normalizer",
    }
    object_coverage.update(dict(coverage or kernel.get("object_coverage") or {}))
    top = {
        "schema_version": KERNEL_STATE_SCHEMA_VERSION,
        "state_id": state_id,
        "task_id": task_id,
        "env_fingerprint": env_fp,
        "state_hash_raw": str(kernel.get("state_hash_raw") or kernel.get("kernel_state_hash") or stable_hash(raw_basis, n=32)),
        "state_hash_norm": str(kernel.get("state_hash_norm") or stable_hash(norm_basis, n=32)),
        "status": status_val,
        "goals": goals,
        "expr_graph": expr_graph,
        "local_contexts": local_contexts,
        "local_context": {
            "nodes": local_contexts[0]["nodes"] if local_contexts else [],
            "edges": local_contexts[0]["edges"] if local_contexts else [],
            "source": local_contexts[0].get("source") if local_contexts else "empty_local_context",
        },
        "metavars": metavars,
        "typeclasses": typeclasses,
        "messages": [str(m) for m in messages[-200:]],
        "options": options_val,
        "proof_prefix_hash": str(kernel.get("proof_prefix_hash") or stable_hash(prefix, n=24)),
        "proof_prefix": prefix,
        "parent_state_id": kernel.get("parent_state_id") or kernel.get("parent"),
        "object_coverage": object_coverage,
        "canonical_status": "kernel_structured_state_chart_not_canonical",
    }
    return top


def structural_kernel_response(before: dict[str, Any], after: dict[str, Any], *, action: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute a finite structural response from two kernel states."""
    b = normalize_kernel_state_v1(before)
    a = normalize_kernel_state_v1(after)
    delta = compute_goal_state_transition_delta(b, a, action=action or {})
    return {
        "schema_version": "lean-rgc-kernel-response-v1",
        "before_state_id": b["state_id"],
        "after_state_id": a["state_id"],
        "action_id": str((action or {}).get("action_id") or (action or {}).get("tactic") or "unknown"),
        "response": {
            "mvar_measure": float(delta.get("mvar_response") or 0.0),
            "goal_count": float(delta.get("goal_count_before") or 0) - float(delta.get("goal_count_after") or 0),
            "typeclass_open": float(delta.get("typeclass_open_before") or 0) - float(delta.get("typeclass_open_after") or 0),
            "expr_removed": float(len(delta.get("expr_nodes_removed") or [])),
            "expr_added": -float(len(delta.get("expr_nodes_added") or [])),
        },
        "state_delta": delta,
        "canonical_status": "kernel_response_chart_not_canonical",
    }


def extractor_response(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    defect_extractor: Callable[[dict[str, Any]], dict[str, float]] | None = None,
    carrier_extractor: Callable[[dict[str, Any]], dict[str, float]] | None = None,
    action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = structural_kernel_response(before, after, action=action)
    if defect_extractor is not None:
        db = defect_extractor(before)
        da = defect_extractor(after)
        keys = sorted(set(db) | set(da))
        base["defect_response"] = {k: float(db.get(k, 0.0)) - float(da.get(k, 0.0)) for k in keys}
    if carrier_extractor is not None:
        cb = carrier_extractor(before)
        ca = carrier_extractor(after)
        keys = sorted(set(cb) | set(ca))
        base["carrier_response"] = {k: float(cb.get(k, 0.0)) - float(ca.get(k, 0.0)) for k in keys}
    return base


@dataclass
class KernelStateRecord:
    state_id: str
    task_id: str
    task: dict[str, Any]
    prefix: str = ""
    target: str = ""
    local_context: str = ""
    raw_messages: list[str] = field(default_factory=list)
    parent_state_id: str | None = None
    applied_action_id: str | None = None
    applied_tactic: str | None = None
    depth: int = 0
    closed: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_proof_state(self) -> ProofState:
        return ProofState(
            state_id=self.state_id,
            task_id=self.task_id,
            target=self.target,
            goals_text="" if self.closed else ("|- " + self.target if self.target else ""),
            local_context=self.local_context,
            raw_messages=list(self.raw_messages or []),
        )


@dataclass
class KernelGoalStateServerConfig:
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    backend: str = "dry_run"
    keep_files: bool = False
    cache_dir: str | None = None
    trace_state: bool = False
    session_id: str | None = None


class KernelGoalStateServer:
    """Persistent in-process server for ``g --a--> g'``.

    It is intentionally small and JSON-compatible.  With ``backend=file`` it
    source-checks via Lean; with ``backend=dry_run`` it exercises the protocol
    without requiring Lean on CI.  A native Lean worker can mirror this API over
    JSONL and fill the same kernel-state v1 payload with true kernel objects.
    """

    def __init__(self, config: KernelGoalStateServerConfig | None = None):
        self.config = config or KernelGoalStateServerConfig()
        self.session_id = self.config.session_id or "kernel_goal_state_server_" + stable_hash({"t": time.time(), "pid": os.getpid()}, n=12)
        self.env_fingerprint = _project_fingerprint(self.config.workdir, self.config.lean_cmd)
        self.states: dict[str, KernelStateRecord] = {}
        self.transitions: list[dict[str, Any]] = []
        self.executor = LeanExecutor(LeanExecutorConfig(
            lean_cmd=self.config.lean_cmd,
            workdir=self.config.workdir,
            timeout_s=self.config.timeout_s,
            keep_files=self.config.keep_files,
            dry_run=(self.config.backend == "dry_run"),
            cache_dir=self.config.cache_dir,
            trace_state=self.config.trace_state,
        ))

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "backend": self.config.backend,
            "env_fingerprint": self.env_fingerprint,
            "n_states": len(self.states),
            "n_transitions": len(self.transitions),
            "schema_version": KERNEL_STATE_SCHEMA_VERSION,
            "canonical_status": "kernel_goal_state_server_protocol_not_canonical",
        }

    def register_task(self, task: LeanTask | dict[str, Any], *, state_id: str | None = None) -> dict[str, Any]:
        task = LeanTask.from_dict(task) if isinstance(task, dict) else task
        sid = state_id or "kg_" + stable_hash({"task_id": task.task_id, "statement": task.statement}, n=16)
        rec = KernelStateRecord(
            state_id=sid,
            task_id=task.task_id,
            task=task.to_dict(),
            prefix=task.prefix or "",
            target=task.statement,
            depth=0,
            metadata={"source": "register_task"},
        )
        self.states[sid] = rec
        return {"ok": True, "state": rec.to_dict(), "kernel_state": self.kernel_state(sid), "status": self.status()}

    def _compat_kernel_payload(self, rec: KernelStateRecord) -> dict[str, Any]:
        goal_id = "?m." + stable_hash({"state": rec.state_id, "target": rec.target}, n=10)
        local_nodes: list[dict[str, Any]] = []
        for i, line in enumerate((rec.local_context or "").splitlines()):
            if ":" not in line:
                continue
            name, typ = line.split(":", 1)
            name = name.strip().split()[-1] if name.strip() else f"h{i}"
            local_nodes.append({"fvar_id": f"fvar_{stable_hash({'state': rec.state_id, 'name': name}, n=10)}", "user_name": name, "type_text": typ.strip()})
        closed = rec.closed or not rec.target
        return {
            "schema_version": KERNEL_STATE_SCHEMA_VERSION,
            "state_id": rec.state_id,
            "task_id": rec.task_id,
            "env_fingerprint": self.env_fingerprint,
            "status": "closed" if closed else "open",
            "closed": closed,
            "goals": [] if closed else [{
                "goal_id": "g0",
                "mvar_id": goal_id,
                "target": {"text": rec.target, "kind": "text_expr", "head": _expr_head(rec.target)},
                "target_text": rec.target,
                "local_deps": [n["fvar_id"] for n in local_nodes],
            }],
            "local_context": {"nodes": local_nodes, "edges": []},
            "metavars": [] if closed else [{"mvar_id": goal_id, "type_text": rec.target, "assigned": False, "local_deps": [n["fvar_id"] for n in local_nodes]}],
            "typeclasses": [],
            "messages": list(rec.raw_messages or []),
            "prefix": rec.prefix,
            "parent_state_id": rec.parent_state_id,
            "object_coverage": {
                "expr_ast": False,
                "local_decl_graph": bool(local_nodes),
                "metavariable_graph": not closed,
                "typeclass_graph": False,
                "in_memory_state_id": True,
                "tactic_transition_api": True,
                "replay_certificate": False,
                "source": f"kernel_goal_state_server_{self.config.backend}",
            },
        }

    def kernel_state(self, state_id: str) -> dict[str, Any]:
        if state_id not in self.states:
            raise KeyError(f"unknown state_id: {state_id}")
        return normalize_kernel_state_v1(self._compat_kernel_payload(self.states[state_id]), env_fingerprint=self.env_fingerprint)

    def branch_state(self, state_id: str, *, label: str | None = None, new_state_id: str | None = None) -> dict[str, Any]:
        src = self.states[state_id]
        sid = new_state_id or "branch_" + stable_hash({"src": state_id, "label": label, "t": time.time()}, n=12)
        rec = KernelStateRecord(**src.to_dict())
        rec.state_id = sid
        rec.parent_state_id = state_id
        rec.metadata = dict(rec.metadata or {})
        rec.metadata.update({"source": "branch_state", "label": label, "branched_from": state_id})
        rec.created_at = time.time()
        self.states[sid] = rec
        return {"ok": True, "new_state_id": sid, "parent_state_id": state_id, "state": rec.to_dict(), "kernel_state": self.kernel_state(sid)}

    def rollback_state(self, state_id: str) -> dict[str, Any]:
        cur = self.states[state_id]
        if cur.parent_state_id and cur.parent_state_id in self.states:
            parent = self.states[cur.parent_state_id]
            return {"ok": True, "state": parent.to_dict(), "kernel_state": self.kernel_state(parent.state_id)}
        return {"ok": True, "state": cur.to_dict(), "kernel_state": self.kernel_state(cur.state_id)}

    @staticmethod
    def _join_prefix(prefix: str, tactic: str) -> str:
        prefix = (prefix or "").rstrip()
        tactic = (tactic or "").strip()
        return tactic if not prefix else (prefix if not tactic else prefix + "\n" + tactic)

    @staticmethod
    def _transition_status(status: str) -> str:
        if status == "success":
            return "success"
        if status in {"partial", "dry_run"}:
            return "partial"
        if status == "timeout":
            return "timeout"
        if status == "elab_error":
            return "elab_error"
        return "failure"

    def _safety(self, rec: AuditRecord, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        flags = dict(rec.audit_flags or {})
        new_mvars = max(0, len(after.get("metavars") or []) - len(before.get("metavars") or []))
        return {
            "source_safety": {
                "ok": not bool(flags.get("uses_sorry") or flags.get("uses_admit")),
                "uses_sorry": bool(flags.get("uses_sorry")),
                "uses_admit": bool(flags.get("uses_admit")),
            },
            "cost_safety": {
                "ok": rec.status != "timeout",
                "elapsed_ms": rec.elapsed_ms,
                "heartbeats": rec.heartbeats,
            },
            "audit_safety": {
                "ok": rec.status in {"success", "partial"},
                "replay_status": "verified" if rec.status in {"success", "partial"} else ("pending" if rec.status == "dry_run" else "failed"),
            },
            "target_safety": {
                "ok": before.get("task_id") == after.get("task_id"),
                "before_task_id": before.get("task_id"),
                "after_task_id": after.get("task_id"),
            },
            "carrier_safety": {
                "ok": new_mvars <= 16,
                "new_mvars": new_mvars,
            },
        }

    def apply_tactic(self, state_id: str, action: TacticAction | dict[str, Any]) -> dict[str, Any]:
        if state_id not in self.states:
            raise KeyError(f"unknown state_id: {state_id}")
        action = TacticAction.from_dict(action) if isinstance(action, dict) else action
        before_rec = self.states[state_id]
        before_kernel = self.kernel_state(state_id)
        task = LeanTask.from_dict(before_rec.task)
        task.prefix = before_rec.prefix or task.prefix
        if self.config.backend == "dry_run":
            task.statement = before_rec.target or task.statement
            task.prefix = ""
        rec = self.executor.run_tactic(task, action, before_rec.to_proof_state())
        after_state = rec.after_state or before_rec.to_proof_state()
        new_prefix = self._join_prefix(before_rec.prefix, action.tactic)
        after_id = "kg_" + stable_hash({"parent": before_rec.state_id, "action": action.to_dict(), "target": after_state.target, "prefix": new_prefix}, n=16)
        after_rec = KernelStateRecord(
            state_id=after_id,
            task_id=before_rec.task_id,
            task=before_rec.task,
            prefix=new_prefix,
            target=after_state.target,
            local_context=after_state.local_context,
            raw_messages=list(after_state.raw_messages or rec.messages or []),
            parent_state_id=before_rec.state_id,
            applied_action_id=action.action_id,
            applied_tactic=action.tactic,
            depth=before_rec.depth + 1,
            closed=(rec.status == "success" and not after_state.target),
            metadata={"source": "apply_tactic", "audit_status": rec.status},
        )
        self.states[after_id] = after_rec
        after_kernel = self.kernel_state(after_id)
        state_delta = compute_goal_state_transition_delta(before_kernel, after_kernel, action=action.to_dict())
        replay_certificate = {
            "proof_prefix_before": before_rec.prefix,
            "action": action.tactic,
            "proof_prefix_after": new_prefix,
            "source_check_hash": stable_hash({"task": before_rec.task, "prefix": new_prefix}, n=24),
            "replay_status": "verified" if rec.status in {"success", "partial"} else ("pending" if rec.status == "dry_run" else "failed"),
        }
        transition = {
            "schema_version": TRANSITION_SCHEMA_VERSION,
            "ok": rec.status in {"success", "partial", "dry_run"},
            "status": self._transition_status(rec.status),
            "before_state_id": before_rec.state_id,
            "after_state_id": after_rec.state_id,
            "state_delta": state_delta,
            "goals_before": before_kernel.get("goals") or [],
            "goals_after": after_kernel.get("goals") or [],
            "messages": list(rec.messages or []),
            "heartbeats": rec.heartbeats,
            "elapsed_ms": rec.elapsed_ms,
            "kernel_state_before": before_kernel,
            "kernel_state_after": after_kernel,
            "replay": replay_certificate,
            "safety": self._safety(rec, before_kernel, after_kernel),
            "response": structural_kernel_response(before_kernel, after_kernel, action=action.to_dict()),
            "canonical_status": "kernel_tactic_transition_chart_not_canonical",
        }
        self.transitions.append(transition)
        return transition


__all__ = [
    "KERNEL_STATE_SCHEMA_VERSION",
    "KernelGoalStateServer",
    "KernelGoalStateServerConfig",
    "KernelStateRecord",
    "normalize_kernel_state_v1",
    "build_expr_graph_v1",
    "build_local_contexts_v1",
    "build_goals_v1",
    "build_metavars_v1",
    "build_typeclasses_v1",
    "structural_kernel_response",
    "extractor_response",
]
