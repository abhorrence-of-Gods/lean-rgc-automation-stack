"""v98: kernel RPC substrate for the D4 mvar-sharing detector.

The `lean-rgc-kernel-state-v2` payload emits, for every open metavariable, a
bounded pretty-printed `type_text` and the `depends_on` list of metavariables
occurring in its instantiated type, plus `target_text` on goals, and replays
`task.prefix` tactics so the initial state is the post-prefix state.  Fixture
payloads here mirror live worker output (runs/krpc_* probes, 2026-07-05).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lean_rgc.lean.mvar_blocks import decompose_structured_state
from lean_rgc.lean.structured_state import extract_structured_state_from_kernel_json
from lean_rgc.native_worker import packaged_kernel_rpc_worker_path


def _kernel_v2(task_id, state_id, goals, metavars, proof_prefix=""):
    return {
        "schema_version": "lean-rgc-kernel-state-v2",
        "extraction_backend": "lean_kernel_rpc_in_memory_v1",
        "state_id": state_id,
        "task_id": task_id,
        "status": "open",
        "goals": goals,
        "metavars": metavars,
        "local_contexts": [],
        "typeclasses": [],
        "messages": [],
        "proof_prefix": proof_prefix,
        "closed": False,
    }


def _mvar(mid, type_text="", depends_on=(), assigned=False, kind="natural", user_name=""):
    return {
        "mvar_id": mid,
        "user_name": user_name,
        "type_text": type_text,
        "depends_on": list(depends_on),
        "assigned": assigned,
        "kind": kind,
    }


# `refine ⟨?_, ?_⟩` on `∃ n : Nat, n = 0`: the hypothesis goal's type mentions
# the witness goal, so the two goals share one open block (Euler-product witness).
KERNEL_EXISTS_V2 = _kernel_v2(
    "t_exists_split",
    "krpc_state_1",
    goals=[
        {"goal_id": "g0", "mvar_id": "?_uniq.46", "target_text": "Nat", "target_head": "Nat", "relation": ""},
        {"goal_id": "g1", "mvar_id": "?_uniq.47", "target_text": "?refine_1 = 0", "target_head": "Eq", "relation": "="},
    ],
    metavars=[
        _mvar("?_uniq.44", assigned=True),
        _mvar("?_uniq.46", type_text="Nat", user_name="refine_1", kind="syntheticOpaque"),
        _mvar("?_uniq.47", type_text="?refine_1 = 0", depends_on=["?_uniq.46"], user_name="refine_2", kind="syntheticOpaque"),
    ],
    proof_prefix="refine ⟨?_, ?_⟩",
)

# Initial state of `(1 = 1) ∧ (2 = 2)` with prefix "constructor" already
# replayed by the worker: two goals whose open support sets are disjoint.
KERNEL_AND_V2 = _kernel_v2(
    "t_and_split",
    "krpc_state_0",
    goals=[
        {"goal_id": "g0", "mvar_id": "?_uniq.156", "target_text": "1 = 1", "target_head": "Eq", "relation": "="},
        {"goal_id": "g1", "mvar_id": "?_uniq.157", "target_text": "2 = 2", "target_head": "Eq", "relation": "="},
    ],
    metavars=[
        _mvar("?_uniq.60", type_text="Type ?u.4"),
        _mvar("?_uniq.132", type_text="Type ?u.9"),
        _mvar("?_uniq.156", type_text="1 = 1", depends_on=["?_uniq.60"], kind="syntheticOpaque"),
        _mvar("?_uniq.157", type_text="2 = 2", depends_on=["?_uniq.132"], kind="syntheticOpaque"),
    ],
    proof_prefix="constructor",
)


def test_v2_payload_carries_type_text_and_depends_on_into_entries():
    row = extract_structured_state_from_kernel_json(KERNEL_EXISTS_V2, backend="kernel_json_v28").to_dict()
    assert row["metadata"]["kernel_schema_version"] == "lean-rgc-kernel-state-v2"
    assert [g["target_text"] for g in row["goals"]] == ["Nat", "?refine_1 = 0"]
    by_id = {e["mvar_id"]: e for e in row["metavars"]["entries"]}
    assert by_id["?_uniq.47"]["type_text"] == "?refine_1 = 0"
    assert by_id["?_uniq.47"]["depends_on"] == ["?_uniq.46"]


def test_shared_witness_from_v2_payload_is_ramified():
    row = extract_structured_state_from_kernel_json(KERNEL_EXISTS_V2, backend="kernel_json_v28").to_dict()
    out = decompose_structured_state(row)
    assert out["ramified"] is True
    assert out["n_blocks"] == 1
    assert out["ramified_pairs"] == [("?_uniq.46", "?_uniq.47")]
    assert out["context_independent"] is False
    assert out["task_id"] == "t_exists_split"


def test_post_prefix_conjunction_from_v2_payload_is_context_independent():
    row = extract_structured_state_from_kernel_json(KERNEL_AND_V2, backend="kernel_json_v28").to_dict()
    assert len(row["goals"]) == 2
    out = decompose_structured_state(row)
    assert out["ramified"] is False
    assert out["n_blocks"] == 2
    assert out["context_independent"] is True


def test_dependencies_mvars_fallback_for_entries_without_depends_on():
    # Rows serialized before the depends_on key existed still carry the raw
    # dependencies_mvars readout; the coercion must not drop it.
    kernel = json.loads(json.dumps(KERNEL_EXISTS_V2))
    for m in kernel["metavars"]:
        m["dependencies_mvars"] = m.pop("depends_on")
    out = decompose_structured_state(
        extract_structured_state_from_kernel_json(kernel, backend="kernel_json_v28").to_dict()
    )
    assert out["ramified"] is True


def test_packaged_worker_source_declares_v2_substrate():
    text = packaged_kernel_rpc_worker_path().read_text(encoding="utf-8")
    assert '"lean-rgc-kernel-state-v2"' in text
    assert '"depends_on"' in text
    assert '"target_text"' in text
    assert "mvarTypeReadout" in text
    assert "replayPrefix" in text
    assert "prefixTacticLines" in text


def _lean_bin() -> str | None:
    found = shutil.which("lean")
    if found:
        return found
    home = Path.home()
    for candidate in [home / ".elan" / "bin" / "lean.exe", home / ".elan" / "bin" / "lean"]:
        if candidate.exists():
            return str(candidate)
    return None


@pytest.mark.skipif(_lean_bin() is None, reason="Lean binary is not installed")
def test_live_worker_feeds_d4_detector_end_to_end():
    lean = _lean_bin()
    worker = packaged_kernel_rpc_worker_path()
    lines = [
        {"id": "load", "cmd": "load_project", "imports": ["Lean"]},
        {"id": "init_exists", "cmd": "init_state",
         "task": {"task_id": "t_exists_split", "statement": "∃ n : Nat, n = 0", "imports": ["Lean"]}},
        {"id": "refine", "cmd": "apply_tactic", "state_id": "krpc_state_0",
         "action": {"action_id": "refine_pair", "tactic": "refine ⟨?_, ?_⟩"}},
        {"id": "init_and", "cmd": "init_state",
         "task": {"task_id": "t_and_split", "statement": "(1 = 1) ∧ (2 = 2)",
                  "prefix": "constructor", "imports": ["Lean"]}},
        {"id": "stop", "cmd": "shutdown"},
    ]
    payload = "\n".join(json.dumps(x, ensure_ascii=True) for x in lines) + "\n"
    proc = subprocess.run(
        [lean, "--run", str(worker), "--imports", "Lean"],
        input=payload,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert all(r.get("ok") for r in replies), replies

    refine_after = replies[2]["kernel_state_after"]
    assert refine_after["schema_version"] == "lean-rgc-kernel-state-v2"
    exists_out = decompose_structured_state(
        extract_structured_state_from_kernel_json(refine_after, backend="kernel_json_v28").to_dict()
    )
    assert exists_out["ramified"] is True

    and_init = replies[3]["kernel_state"]
    assert and_init["proof_prefix"] == "constructor"
    assert len(and_init["goals"]) == 2
    and_out = decompose_structured_state(
        extract_structured_state_from_kernel_json(and_init, backend="kernel_json_v28").to_dict()
    )
    assert and_out["ramified"] is False
    assert and_out["n_blocks"] == 2
