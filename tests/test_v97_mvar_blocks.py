"""D4 mvar-sharing decomposition: the context-independence certificate."""

from __future__ import annotations

from lean_rgc.lean.mvar_blocks import decompose_mvar_blocks, decompose_structured_state


def _graph(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def _n(mid, *, assigned=False, kind="natural", type_text=""):
    return {"mvar_id": mid, "assigned": assigned, "kind": kind, "type_text": type_text}


def test_independent_goals_give_singleton_blocks():
    g = _graph([_n("?g1"), _n("?g2")], [])
    out = decompose_mvar_blocks(g, goal_mvar_ids=["?g1", "?g2"])
    assert out["n_blocks"] == 2
    assert not out["ramified"]
    assert out["context_independent"]


def test_shared_witness_mvar_is_ramified():
    # refine ⟨?_, ?_⟩ on ∃ n, n = 0: goal ?h's type mentions witness goal ?w.
    g = _graph(
        [_n("?w"), _n("?h", type_text="?w = 0")],
        [{"src": "?w", "dst": "?h", "kind": "type_mentions_mvar"}],
    )
    out = decompose_mvar_blocks(g, goal_mvar_ids=["?w", "?h"])
    assert out["n_blocks"] == 1
    assert out["ramified"]
    assert out["ramified_pairs"] == [("?h", "?w")] or out["ramified_pairs"] == [("?w", "?h")]
    assert not out["context_independent"]


def test_assigned_mediator_does_not_transmit_freedom():
    g = _graph(
        [_n("?a", assigned=True), _n("?g1"), _n("?g2")],
        [
            {"src": "?a", "dst": "?g1", "kind": "mvar_dependency"},
            {"src": "?a", "dst": "?g2", "kind": "mvar_dependency"},
        ],
    )
    out = decompose_mvar_blocks(g, goal_mvar_ids=["?g1", "?g2"])
    assert out["n_blocks"] == 2
    assert not out["ramified"]
    assert out["context_independent"]


def test_orphan_open_mvar_reported_not_blocked():
    g = _graph([_n("?g1"), _n("?stray")], [])
    out = decompose_mvar_blocks(g, goal_mvar_ids=["?g1"])
    assert out["n_blocks"] == 1
    assert out["orphan_open_mvars"] == ["?stray"]
    # An orphan open mvar breaks strict block==goal bijection but not
    # goal-goal independence; context_independent tracks goal blocks only
    # when every goal sits alone AND blocks == goals.
    assert out["context_independent"]


def test_structured_state_adapter_kernel_json_shape():
    row = {
        "task_id": "t_exists",
        "state_id": "krpc_state_0",
        "goals": [
            {"goal_id": "g0", "mvar_id": "?_uniq.10", "target_text": "Nat", "target_head": "const"},
            {"goal_id": "g1", "mvar_id": "?_uniq.11", "target_text": "?_uniq.10 = 0", "target_head": "eq"},
        ],
        "metavars": {
            "entries": [
                {"mvar_id": "?_uniq.10", "assigned": False, "depends_on": [], "type_text": "Nat"},
                {"mvar_id": "?_uniq.11", "assigned": False, "depends_on": [], "type_text": "?_uniq.10 = 0"},
            ]
        },
    }
    out = decompose_structured_state(row)
    # type_mentions_mvar edge is derived from the type text substring.
    assert out["ramified"]
    assert out["n_open_goals"] == 2
    assert out["task_id"] == "t_exists"
