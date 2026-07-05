"""D4: metavariable-sharing decomposition — the Euler-product witness.

Connected components of the metavariable graph restricted to OPEN
(unassigned) nodes. A subgoal decomposition is context-independent iff no
two open goal mvars share a component: then success probabilities factor,
search parallelizes, and per-goal cache transfer is licensed. Sharing =
ramification: the interaction factor between those goals is non-trivial
and they must be treated as one cluster (or routed to a port).

Edges through ASSIGNED mvars do not transmit freedom (their value is a
fixed term), so components are computed over open nodes only.
"""

from __future__ import annotations

from typing import Any

from .goal_state_dynamics import build_metavariable_graph

SCHEMA_MVAR_BLOCKS = "lean-rgc-mvar-blocks-v97.0"


def _union_find_components(node_ids: set[str], edges: list[tuple[str, str]]) -> dict[str, str]:
    parent = {n: n for n in node_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    return {n: find(n) for n in node_ids}


def decompose_mvar_blocks(
    graph: dict[str, Any],
    *,
    goal_mvar_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Decompose a build_metavariable_graph payload into open-mvar blocks.

    `goal_mvar_ids` names which open mvars are the GOALS (from the state's
    goals list). Without it, nodes with kind == "goal" are used — correct
    only for payloads where goals were absent from the metavars table.
    """
    nodes = [dict(n) for n in (graph.get("nodes") or [])]
    by_id = {str(n.get("mvar_id")): n for n in nodes}
    open_ids = {i for i, n in by_id.items() if not n.get("assigned")}
    if goal_mvar_ids is not None:
        goal_ids = [str(g) for g in goal_mvar_ids if str(g) in by_id]
    else:
        goal_ids = [i for i, n in by_id.items() if str(n.get("kind")) == "goal"]
    open_goal_ids = [g for g in goal_ids if g in open_ids]

    edges: list[tuple[str, str]] = []
    for e in graph.get("edges") or []:
        a, b = str(e.get("src")), str(e.get("dst"))
        if a in open_ids and b in open_ids:
            edges.append((a, b))
    roots = _union_find_components(open_ids, edges)

    members: dict[str, list[str]] = {}
    for i in open_ids:
        members.setdefault(roots[i], []).append(i)
    blocks: list[dict[str, Any]] = []
    for root, ids in sorted(members.items()):
        goals_here = sorted(g for g in open_goal_ids if roots[g] == root)
        if not goals_here:
            continue  # orphan open mvars without a goal: reported separately
        blocks.append({
            "goal_mvars": goals_here,
            "mvar_ids": sorted(ids),
            "n_open_members": len(ids),
            "shared": len(goals_here) >= 2,
        })
    ramified_pairs = [
        (b["goal_mvars"][i], b["goal_mvars"][j])
        for b in blocks
        for i in range(len(b["goal_mvars"]))
        for j in range(i + 1, len(b["goal_mvars"]))
    ]
    orphan_open = sorted(
        i for i in open_ids if not any(i in b["mvar_ids"] for b in blocks)
    )
    return {
        "schema_version": SCHEMA_MVAR_BLOCKS,
        "n_nodes": len(nodes),
        "n_open": len(open_ids),
        "n_open_goals": len(open_goal_ids),
        "n_blocks": len(blocks),
        "blocks": blocks,
        "ramified": bool(ramified_pairs),
        "ramified_pairs": ramified_pairs,
        "orphan_open_mvars": orphan_open,
        "context_independent": not ramified_pairs and len(blocks) == len(open_goal_ids),
        "canonical_status": "mvar_block_decomposition_witness_not_canonical",
    }


def decompose_structured_state(state_row: dict[str, Any]) -> dict[str, Any]:
    """D4 on a kernel-backed structured state row (kernel_json_v28 shape:
    metavars.entries + goals[*].mvar_id)."""
    goals = state_row.get("goals") or []
    graph = build_metavariable_graph(state_row, goals=goals)
    gids = [str(g.get("mvar_id")) for g in goals if g.get("mvar_id")]
    out = decompose_mvar_blocks(graph, goal_mvar_ids=gids or None)
    out["task_id"] = state_row.get("task_id")
    out["state_id"] = state_row.get("state_id")
    return out


__all__ = [
    "SCHEMA_MVAR_BLOCKS",
    "decompose_mvar_blocks",
    "decompose_structured_state",
]
