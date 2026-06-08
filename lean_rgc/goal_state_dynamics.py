from __future__ import annotations

"""Goal-state dynamics substrate for Lean-RGC v47.

This module is intentionally protocol-oriented.  It does not claim that the
in-tree worker is already a full Lean-kernel RPC server; rather, it gives the
RGC side a first-class object for

    g --a--> g'

using kernel-shaped state payloads.  True Lean workers can fill the same
schema with real Expr / LocalDecl / MVar / typeclass data.  Fallback workers
still populate the schema from persistent state / source-check charts.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import re

from .schemas import AuditRecord, read_jsonl, write_jsonl, stable_hash

SCHEMA_VERSION = "lean-rgc-goal-state-dynamics-v47.0"
GRAPH_SCHEMA_VERSION = "lean-rgc-goal-state-graph-v47.0"
TRANSITION_SCHEMA_VERSION = "lean-rgc-goal-state-transition-v47.0"

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*|[0-9]+|[∀∃→↔∧∨¬=≤≥<>+*\-/]|[^\s]")


def _as_list(x: Any) -> list[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    return [x]


def _expr_text(x: Any) -> str:
    if isinstance(x, dict):
        for k in ("text", "pretty", "pp", "type_text", "target_text", "expr_text"):
            if x.get(k) is not None:
                return str(x.get(k))
        if x.get("head") is not None:
            return str(x.get("head"))
        return json.dumps(x, ensure_ascii=False, sort_keys=True)[:400]
    return str(x or "")


def _expr_kind(x: Any) -> str:
    if isinstance(x, dict):
        return str(x.get("kind") or x.get("expr_kind") or "unknown")
    return "text_expr"


def _expr_head(x: Any) -> str:
    if isinstance(x, dict):
        if x.get("head") is not None:
            return str(x.get("head"))
        if x.get("const_name") is not None:
            return str(x.get("const_name"))
    text = _expr_text(x)
    if "∀" in text or re.search(r"\bforall\b", text):
        return "forall"
    if "→" in text or "->" in text:
        return "imp"
    if "∧" in text or re.search(r"\bAnd\b", text):
        return "and"
    if "∨" in text or re.search(r"\bOr\b", text):
        return "or"
    if "=" in text:
        return "Eq"
    if any(s in text for s in ["≤", "≥", "<", ">", "<=", ">="]):
        return "Order"
    toks = _TOKEN_RE.findall(text)
    return toks[0] if toks else "unknown"


def _symbols(text: str) -> list[str]:
    bad = {"∀", "∃", "→", "↔", "∧", "∨", "¬", "=", "≤", "≥", "<", ">", "+", "*", "-", "/", ":", ",", ".", "(", ")", "[", "]", "{", "}"}
    out: list[str] = []
    seen: set[str] = set()
    for t in _TOKEN_RE.findall(text or ""):
        if t in bad or t.isdigit():
            continue
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:256]


def _domain_tags(text: str) -> list[str]:
    tags: list[str] = []
    checks = [
        ("Nat", ["Nat", "ℕ", "Nat."]),
        ("Int", ["Int", "ℤ", "Int."]),
        ("Real", ["Real", "ℝ", "Real."]),
        ("List", ["List", "[]", "::", "length", "map", "append"]),
        ("Eq", ["="]),
        ("Arith", ["+", "-", "*", "≤", "<", "≥", ">"]),
        ("Prop", ["Prop", "∀", "∃", "→", "∧", "∨", "¬"]),
    ]
    for name, pats in checks:
        if any(p in (text or "") for p in pats):
            tags.append(name)
    return tags


def _carrier_atoms(text: str) -> list[str]:
    head = _expr_head(text)
    atoms: list[str] = []
    if head == "forall": atoms.append("unintroduced_forall")
    if head == "imp": atoms.append("unintroduced_imp")
    if head == "and": atoms.append("unsplit_and_target")
    if head in {"Eq", "eq"}: atoms.append("eq_reflexive_goal")
    if any(k in text for k in ["+", "*", "≤", "<", "≥", ">", "Nat", "ℕ"]): atoms.append("nat_arith_goal")
    if "?m" in text: atoms.append("metavariable_debt")
    return atoms


def _expr_node(expr: Any, *, role: str, owner: str = "") -> dict[str, Any]:
    text = _expr_text(expr)
    kind = _expr_kind(expr)
    head = _expr_head(expr)
    raw = expr if isinstance(expr, dict) else {"text": text, "kind": kind, "head": head}
    eid = str(raw.get("expr_id") or raw.get("id") or stable_hash({"role": role, "owner": owner, "expr": raw}, n=16))
    children = raw.get("children") or raw.get("args") or []
    if not isinstance(children, list):
        children = []
    return {
        "expr_id": eid,
        "kind": kind,
        "head": head,
        "text": text,
        "role": role,
        "owner": owner,
        "children": [str(c.get("expr_id") if isinstance(c, dict) else c) for c in children],
        "symbols": _symbols(text),
        "domain_tags": _domain_tags(text),
        "raw_hash": stable_hash(raw, n=20),
        "norm_hash": stable_hash({"kind": kind, "head": head, "symbols": _symbols(text)}, n=20),
        "raw": raw if len(json.dumps(raw, ensure_ascii=False, default=str)) < 2000 else {"text": text, "kind": kind, "head": head},
    }


def _kernel_goals(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("goals") or kernel.get("mvars") or kernel.get("metavars") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or raw.get("goals") or raw.get("entries") or []
    return [dict(x or {}) if isinstance(x, dict) else {"target": str(x)} for x in _as_list(raw)]


def _kernel_lctx_nodes(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    lcs = kernel.get("local_contexts")
    if isinstance(lcs, list) and lcs:
        out: list[dict[str, Any]] = []
        for ctx in lcs:
            if isinstance(ctx, dict):
                raw = ctx.get("nodes") or ctx.get("entries") or ctx.get("local_decls") or ctx.get("decls") or []
            elif isinstance(ctx, list):
                raw = ctx
            else:
                raw = []
            out.extend(dict(x or {}) if isinstance(x, dict) else {"name": str(x)} for x in raw)
        return out
    lc = kernel.get("local_context") or kernel.get("localContext") or kernel.get("lctx") or {}
    if isinstance(lc, dict):
        raw = lc.get("nodes") or lc.get("entries") or lc.get("local_decls") or lc.get("decls") or []
    elif isinstance(lc, list):
        raw = lc
    else:
        raw = []
    return [dict(x or {}) if isinstance(x, dict) else {"name": str(x)} for x in raw]


def _kernel_mvars(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("metavars") or kernel.get("metavariables") or kernel.get("mvars") or []
    if isinstance(raw, dict):
        raw = raw.get("nodes") or raw.get("entries") or []
    return [dict(x or {}) if isinstance(x, dict) else {"mvar_id": str(x)} for x in _as_list(raw)]


def _kernel_typeclasses(kernel: dict[str, Any]) -> list[dict[str, Any]]:
    raw = kernel.get("typeclasses") or kernel.get("typeclass_obligations") or kernel.get("instance_obligations") or []
    if isinstance(raw, dict):
        raw = raw.get("obligations") or raw.get("nodes") or []
    return [dict(x or {}) if isinstance(x, dict) else {"text": str(x)} for x in _as_list(raw)]


def build_expr_graph(kernel: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Expr DAG chart from kernel-shaped JSON.

    If the worker supplied a native expr_graph, we keep it and add hashes.  If
    not, we synthesize a DAG from goal targets, local-decl types, metavariable
    types, and typeclass obligations.  The synthesized graph is a chart; a true
    Lean worker should fill the same fields with real Expr JSON.
    """
    supplied = kernel.get("expr_graph") if isinstance(kernel.get("expr_graph"), dict) else None
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    roots: list[str] = []
    if supplied:
        raw_nodes = supplied.get("nodes") or []
        for n in raw_nodes if isinstance(raw_nodes, list) else []:
            nd = dict(n or {}) if isinstance(n, dict) else {"text": str(n)}
            expr = _expr_node(nd, role=str(nd.get("role") or "native"), owner=str(nd.get("owner") or ""))
            nodes.append(expr)
            roots.extend([str(x) for x in _as_list(supplied.get("roots"))])
            for ch in expr.get("children") or []:
                edges.append({"src": expr["expr_id"], "dst": ch, "kind": "expr_child"})
    for i, g in enumerate(_kernel_goals(kernel)):
        expr = g.get("target") or g.get("target_expr") or g.get("type") or g.get("target_text") or g.get("target_text_raw")
        node = _expr_node(expr, role="goal_target", owner=str(g.get("mvar_id") or g.get("goal_id") or f"g{i}"))
        nodes.append(node); roots.append(node["expr_id"])
    for i, d in enumerate(_kernel_lctx_nodes(kernel)):
        expr = d.get("type") or d.get("type_expr") or d.get("type_text") or d.get("type_pp") or ""
        node = _expr_node(expr, role="local_decl_type", owner=str(d.get("fvar_id") or d.get("name") or f"h{i}"))
        nodes.append(node)
    for i, m in enumerate(_kernel_mvars(kernel)):
        expr = m.get("type") or m.get("type_expr") or m.get("type_text") or m.get("target") or ""
        node = _expr_node(expr, role="metavar_type", owner=str(m.get("mvar_id") or m.get("id") or f"?m.{i}"))
        nodes.append(node)
    for i, tc in enumerate(_kernel_typeclasses(kernel)):
        expr = tc.get("type") or tc.get("expr") or tc.get("text") or ""
        node = _expr_node(expr, role="typeclass_obligation", owner=str(tc.get("obligation_id") or tc.get("mvar_id") or f"tc{i}"))
        nodes.append(node)
    # Deduplicate by raw_hash while preserving roots mapping best-effort.
    by_hash: dict[str, dict[str, Any]] = {}
    for n in nodes:
        by_hash.setdefault(n["raw_hash"], n)
    nodes = list(by_hash.values())[:2048]
    node_ids = {n["expr_id"] for n in nodes}
    roots = [r for r in roots if r in node_ids]
    if not roots and nodes:
        roots = [nodes[0]["expr_id"]]
    return {
        "schema_version": "lean-rgc-expr-graph-v47.0",
        "nodes": nodes,
        "edges": [e for e in edges if e.get("src") in node_ids and e.get("dst") in node_ids][:4096],
        "roots": roots,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "source": "kernel_expr_graph" if supplied else "kernel_payload_synthesized_expr_graph",
        "canonical_status": "expr_graph_chart_not_canonical",
    }


def build_local_decl_graph(kernel: dict[str, Any], expr_graph: dict[str, Any] | None = None) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    raw = _kernel_lctx_nodes(kernel)
    name_to_id: dict[str, str] = {}
    for i, d in enumerate(raw):
        fvar = str(d.get("fvar_id") or d.get("id") or d.get("name") or d.get("user_name") or f"fvar_{i}")
        name = str(d.get("user_name") or d.get("name") or fvar)
        typ_obj = d.get("type") or d.get("type_expr") or d.get("type_text") or ""
        typ = str(d.get("type_text") or _expr_text(typ_obj))
        deps = d.get("depends_on") or d.get("local_deps") or d.get("fvar_deps") or []
        if not isinstance(deps, list): deps = []
        node = {
            "fvar_id": fvar,
            "user_name": name,
            "name": name,
            "binder_kind": str(d.get("binder_kind") or d.get("binderInfo") or "default"),
            "type_text": typ,
            "type_head": str(d.get("type_head") or _expr_head(typ_obj)),
            "is_instance": bool(d.get("is_instance") or d.get("binder_kind") == "instImplicit" or name.startswith("inst")),
            "is_implementation_detail": bool(d.get("is_implementation_detail") or d.get("impl_detail")),
            "depends_on_fvars": [str(x) for x in deps],
            "symbols": _symbols(typ),
            "kernel_hash": str(d.get("kernel_hash") or stable_hash(d, n=18)),
        }
        nodes.append(node); name_to_id[name] = fvar; name_to_id[fvar] = fvar
    edges: list[dict[str, Any]] = []
    fvars = {n["fvar_id"] for n in nodes}
    names = {n["name"]: n["fvar_id"] for n in nodes}
    for n in nodes:
        for dep in n.get("depends_on_fvars") or []:
            dep_id = name_to_id.get(str(dep), str(dep))
            if dep_id in fvars and dep_id != n["fvar_id"]:
                edges.append({"src": dep_id, "dst": n["fvar_id"], "kind": "type_depends_on_fvar"})
        for nm, fid in names.items():
            if fid != n["fvar_id"] and re.search(rf"\b{re.escape(nm)}\b", n.get("type_text", "")):
                e = {"src": fid, "dst": n["fvar_id"], "kind": "type_text_mentions_fvar"}
                if e not in edges:
                    edges.append(e)
    return {
        "schema_version": "lean-rgc-local-decl-graph-v47.0",
        "nodes": nodes[:2048],
        "edges": edges[:4096],
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "source": "kernel_local_decl_graph",
        "canonical_status": "local_decl_graph_chart_not_canonical",
    }


def build_metavariable_graph(kernel: dict[str, Any], goals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    raw = _kernel_mvars(kernel)
    goals = goals if goals is not None else _kernel_goals(kernel)
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, m in enumerate(raw):
        mid = str(m.get("mvar_id") or m.get("id") or m.get("name") or f"?m.{i}")
        seen.add(mid)
        typ = str(m.get("type_text") or _expr_text(m.get("type") or m.get("type_expr") or m.get("target") or ""))
        deps = m.get("depends_on") or m.get("dependencies_mvars") or []
        if not isinstance(deps, list): deps = []
        node = {
            "mvar_id": mid,
            "type_text": typ,
            "type_head": str(m.get("type_head") or _expr_head(m.get("type") or typ)),
            "assigned": bool(m.get("assigned") or m.get("assignment")),
            "kind": str(m.get("kind") or ("synthetic" if str(mid).startswith("?m") else "natural")),
            "local_context_fvars": [str(x) for x in _as_list(m.get("local_context_fvars") or m.get("local_deps"))],
            "dependencies_mvars": [str(x) for x in deps],
            "synthetic": bool(m.get("synthetic") or str(mid).startswith("?m")),
            "kernel_hash": str(m.get("kernel_hash") or stable_hash(m, n=18)),
        }
        nodes.append(node)
    for i, g in enumerate(goals or []):
        gd = dict(g or {})
        mid = str(gd.get("mvar_id") or gd.get("goal_mvar_id") or gd.get("goal_id") or f"?goal.{i}")
        if mid in seen: continue
        target = str(gd.get("target_text") or _expr_text(gd.get("target") or gd.get("type") or ""))
        nodes.append({
            "mvar_id": mid,
            "type_text": target,
            "type_head": str(gd.get("target_head") or _expr_head(gd.get("target") or target)),
            "assigned": False,
            "kind": "goal",
            "local_context_fvars": [str(x) for x in _as_list(gd.get("local_deps"))],
            "dependencies_mvars": [],
            "synthetic": str(mid).startswith("?m"),
            "kernel_hash": stable_hash(gd, n=18),
        })
    ids = {n["mvar_id"] for n in nodes}
    edges: list[dict[str, Any]] = []
    for n in nodes:
        for dep in n.get("dependencies_mvars") or []:
            if dep in ids and dep != n["mvar_id"]:
                edges.append({"src": dep, "dst": n["mvar_id"], "kind": "mvar_dependency"})
        txt = n.get("type_text", "")
        for mid in ids:
            if mid != n["mvar_id"] and mid in txt:
                e = {"src": mid, "dst": n["mvar_id"], "kind": "type_mentions_mvar"}
                if e not in edges: edges.append(e)
    open_count = sum(1 for n in nodes if not n.get("assigned"))
    synthetic_count = sum(1 for n in nodes if n.get("synthetic") or n.get("kind") in {"synthetic", "syntheticOpaque"})
    return {
        "schema_version": "lean-rgc-metavariable-graph-v47.0",
        "nodes": nodes[:2048],
        "edges": edges[:4096],
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "open_count": open_count,
        "synthetic_count": synthetic_count,
        "max_depth_proxy": _graph_depth_proxy(nodes, edges),
        "measure": mvar_graph_measure(nodes, edges),
        "source": "kernel_metavariable_graph",
        "canonical_status": "metavariable_graph_chart_not_canonical",
    }


def _graph_depth_proxy(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> int:
    out: dict[str, list[str]] = {}
    for e in edges:
        out.setdefault(str(e.get("src")), []).append(str(e.get("dst")))
    maxd = 0
    for n in nodes[:512]:
        start = str(n.get("mvar_id") or n.get("id"))
        seen = {start}
        frontier = [(start, 0)]
        while frontier:
            cur, d = frontier.pop(0)
            maxd = max(maxd, d)
            if d > 32: break
            for nxt in out.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt); frontier.append((nxt, d + 1))
    return maxd


def mvar_graph_measure(nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None, typeclasses: list[dict[str, Any]] | None = None) -> float:
    edges = edges or []
    typeclasses = typeclasses or []
    open_count = sum(1 for n in nodes if not n.get("assigned"))
    synthetic = sum(1 for n in nodes if n.get("synthetic") or n.get("kind") in {"synthetic", "syntheticOpaque"})
    depth = _graph_depth_proxy(nodes, edges)
    cycles = 0.0  # future: SCC count; keep schema stable.
    tc_open = sum(1 for t in typeclasses if str(t.get("status") or "open") not in {"closed", "synthesized", "solved"})
    return float(open_count + 0.25 * synthetic + 0.15 * depth + 0.5 * tc_open + cycles)


def build_typeclass_graph(kernel: dict[str, Any]) -> dict[str, Any]:
    raw = _kernel_typeclasses(kernel)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for i, t in enumerate(raw):
        expr = t.get("type") or t.get("expr") or t.get("text") or ""
        text = str(t.get("text") or _expr_text(expr))
        oid = str(t.get("obligation_id") or t.get("mvar_id") or t.get("id") or f"tc{i}")
        deps = t.get("depends_on") or t.get("dependencies") or []
        if not isinstance(deps, list): deps = []
        nodes.append({
            "obligation_id": oid,
            "mvar_id": str(t.get("mvar_id") or oid),
            "class_head": str(t.get("class_head") or t.get("head") or _expr_head(expr)),
            "target_text": text,
            "status": str(t.get("status") or "open"),
            "local_instances": [str(x) for x in _as_list(t.get("local_instances"))],
            "depends_on": [str(x) for x in deps],
            "symbols": _symbols(text),
            "kernel_hash": str(t.get("kernel_hash") or stable_hash(t, n=18)),
        })
    ids = {n["obligation_id"] for n in nodes}
    for n in nodes:
        for dep in n.get("depends_on") or []:
            if dep in ids:
                edges.append({"src": dep, "dst": n["obligation_id"], "kind": "typeclass_dependency"})
    return {
        "schema_version": "lean-rgc-typeclass-graph-v47.0",
        "nodes": nodes[:1024],
        "edges": edges[:2048],
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "open_count": sum(1 for n in nodes if n.get("status") not in {"closed", "synthesized", "solved"}),
        "source": "kernel_typeclass_graph",
        "canonical_status": "typeclass_graph_chart_not_canonical",
    }


def normalize_goal_state_graph(kernel_state: dict[str, Any]) -> dict[str, Any]:
    kernel = dict(kernel_state or {})
    expr_graph = build_expr_graph(kernel)
    lctx_graph = build_local_decl_graph(kernel, expr_graph)
    goals = _kernel_goals(kernel)
    mvar_graph = build_metavariable_graph(kernel, goals)
    tc_graph = build_typeclass_graph(kernel)
    state_id = str(kernel.get("state_id") or kernel.get("proof_state_id") or stable_hash(kernel, n=16))
    task_id = str(kernel.get("task_id") or "unknown")
    raw_hash = str(kernel.get("state_hash_raw") or kernel.get("kernel_state_hash") or stable_hash(kernel, n=24))
    norm_basis = {
        "goal_heads": [n.get("head") for n in expr_graph.get("nodes", []) if n.get("role") == "goal_target"],
        "goal_symbols": sorted({s for n in expr_graph.get("nodes", []) if n.get("role") == "goal_target" for s in n.get("symbols", [])}),
        "lctx_heads": sorted(n.get("type_head") for n in lctx_graph.get("nodes", [])),
        "mvar_open": mvar_graph.get("open_count"),
        "mvar_measure": round(float(mvar_graph.get("measure") or 0.0), 6),
        "tc_open": tc_graph.get("open_count"),
    }
    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "state_id": state_id,
        "task_id": task_id,
        "project_fingerprint": kernel.get("project_fingerprint") or kernel.get("env_fingerprint"),
        "status": "closed" if not _kernel_goals(kernel) or bool(kernel.get("closed")) else str(kernel.get("status") or "open"),
        "expr_graph": expr_graph,
        "local_decl_graph": lctx_graph,
        "metavariable_graph": mvar_graph,
        "typeclass_graph": tc_graph,
        "state_hash_raw": raw_hash,
        "state_hash_norm": str(kernel.get("state_hash_norm") or stable_hash(norm_basis, n=24)),
        "metadata": dict(kernel.get("metadata") or {}),
        "canonical_status": "goal_state_graph_chart_not_canonical",
    }


def _ids(nodes: list[dict[str, Any]], key: str) -> set[str]:
    return {str(n.get(key)) for n in nodes if n.get(key) is not None}


def compute_goal_state_transition_delta(before_kernel: dict[str, Any], after_kernel: dict[str, Any], *, action: dict[str, Any] | None = None) -> dict[str, Any]:
    before = normalize_goal_state_graph(before_kernel)
    after = normalize_goal_state_graph(after_kernel)
    bm = before["metavariable_graph"]; am = after["metavariable_graph"]
    b_mids = _ids(bm.get("nodes", []), "mvar_id"); a_mids = _ids(am.get("nodes", []), "mvar_id")
    bexpr = before["expr_graph"]; aexpr = after["expr_graph"]
    b_expr_hashes = _ids(bexpr.get("nodes", []), "raw_hash"); a_expr_hashes = _ids(aexpr.get("nodes", []), "raw_hash")
    bl = before["local_decl_graph"]; al = after["local_decl_graph"]
    b_fvars = _ids(bl.get("nodes", []), "fvar_id"); a_fvars = _ids(al.get("nodes", []), "fvar_id")
    btc = before["typeclass_graph"]; atc = after["typeclass_graph"]
    b_tcs = _ids(btc.get("nodes", []), "obligation_id"); a_tcs = _ids(atc.get("nodes", []), "obligation_id")
    m_before = float(bm.get("measure") or 0.0); m_after = float(am.get("measure") or 0.0)
    delta = {
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "transition_id": stable_hash({"before": before.get("state_hash_raw"), "after": after.get("state_hash_raw"), "action": action or {}}, n=20),
        "before_state_id": before.get("state_id"),
        "after_state_id": after.get("state_id"),
        "action_id": str((action or {}).get("action_id") or (action or {}).get("tactic") or "unknown"),
        "tactic": str((action or {}).get("tactic") or ""),
        "closed_mvars": sorted(b_mids - a_mids),
        "new_mvars": sorted(a_mids - b_mids),
        "persisting_mvars": sorted(b_mids & a_mids),
        "mvar_measure_before": m_before,
        "mvar_measure_after": m_after,
        "mvar_response": m_before - m_after,
        "expr_nodes_removed": sorted(b_expr_hashes - a_expr_hashes)[:128],
        "expr_nodes_added": sorted(a_expr_hashes - b_expr_hashes)[:128],
        "local_decls_removed": sorted(b_fvars - a_fvars),
        "local_decls_added": sorted(a_fvars - b_fvars),
        "typeclass_obligations_closed": sorted(b_tcs - a_tcs),
        "typeclass_obligations_new": sorted(a_tcs - b_tcs),
        "goal_count_before": int(bm.get("open_count") or 0),
        "goal_count_after": int(am.get("open_count") or 0),
        "typeclass_open_before": int(btc.get("open_count") or 0),
        "typeclass_open_after": int(atc.get("open_count") or 0),
        "state_hash_raw_before": before.get("state_hash_raw"),
        "state_hash_raw_after": after.get("state_hash_raw"),
        "state_hash_norm_before": before.get("state_hash_norm"),
        "state_hash_norm_after": after.get("state_hash_norm"),
        "progress_status": "closed" if int(am.get("open_count") or 0) == 0 else ("mvar_progress" if m_before > m_after else "open"),
        "canonical_status": "goal_state_transition_delta_chart_not_canonical",
    }
    return delta


def _kernel_from_audit_side(row: dict[str, Any], side: str) -> dict[str, Any] | None:
    flags = row.get("audit_flags") if isinstance(row.get("audit_flags"), dict) else {}
    keys = [f"kernel_state_{side}", f"{side}_kernel_state"]
    if side == "after":
        keys += ["kernel_state"]
    for k in keys:
        val = row.get(k) if isinstance(row.get(k), dict) else flags.get(k) if isinstance(flags.get(k), dict) else None
        if isinstance(val, dict): return val
    return None


def goal_state_transition_from_audit(row: dict[str, Any]) -> dict[str, Any] | None:
    before = _kernel_from_audit_side(row, "before")
    after = _kernel_from_audit_side(row, "after")
    if before is None or after is None:
        return None
    action = {"action_id": row.get("action_id"), "tactic": (row.get("action") or {}).get("tactic") if isinstance(row.get("action"), dict) else row.get("tactic")}
    delta = compute_goal_state_transition_delta(before, after, action=action)
    delta.update({
        "task_id": row.get("task_id"),
        "audit_status": row.get("status"),
        "elapsed_ms": row.get("elapsed_ms"),
        "source": "audit_kernel_before_after",
    })
    return delta


def goal_state_transitions_from_audits(audits_or_path: str | Path | list[dict[str, Any]], out_path: str | Path | None = None, summary_out: str | Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(audits_or_path) if isinstance(audits_or_path, (str, Path)) else audits_or_path
    out: list[dict[str, Any]] = []
    missing = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        tr = goal_state_transition_from_audit(r)
        if tr is None:
            missing += 1
            continue
        out.append(tr)
    if out_path is not None:
        write_jsonl(out_path, out)
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_audit_rows": len(rows),
        "n_transitions": len(out),
        "n_missing_kernel_before_after": missing,
        "mean_mvar_response": sum(float(x.get("mvar_response") or 0.0) for x in out) / max(1, len(out)),
        "by_progress_status": {},
        "canonical_status": "goal_state_transition_report_chart_not_canonical",
    }
    for x in out:
        k = str(x.get("progress_status") or "unknown")
        report["by_progress_status"][k] = report["by_progress_status"].get(k, 0) + 1
    if summary_out is not None:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


def kernel_state_graphs_from_jsonl(kernel_jsonl_or_rows: str | Path | list[dict[str, Any]], out_path: str | Path | None = None, summary_out: str | Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(kernel_jsonl_or_rows) if isinstance(kernel_jsonl_or_rows, (str, Path)) else kernel_jsonl_or_rows
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict): continue
        kernel = r.get("kernel_state") if isinstance(r.get("kernel_state"), dict) else r
        if isinstance(kernel, dict):
            out.append(normalize_goal_state_graph(kernel))
    if out_path is not None:
        write_jsonl(out_path, out)
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_input_rows": len(rows),
        "n_goal_state_graphs": len(out),
        "mean_expr_nodes": sum(int(x.get("expr_graph", {}).get("n_nodes", 0) or 0) for x in out) / max(1, len(out)),
        "mean_mvar_measure": sum(float(x.get("metavariable_graph", {}).get("measure", 0.0) or 0.0) for x in out) / max(1, len(out)),
        "canonical_status": "goal_state_graph_report_chart_not_canonical",
    }
    if summary_out is not None:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


__all__ = [
    "SCHEMA_VERSION", "GRAPH_SCHEMA_VERSION", "TRANSITION_SCHEMA_VERSION",
    "build_expr_graph", "build_local_decl_graph", "build_metavariable_graph", "build_typeclass_graph",
    "normalize_goal_state_graph", "compute_goal_state_transition_delta",
    "goal_state_transition_from_audit", "goal_state_transitions_from_audits", "kernel_state_graphs_from_jsonl",
]
