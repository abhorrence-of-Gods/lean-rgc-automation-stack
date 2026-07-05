"""v99/M2: proof-term minimal support over the kernel RPC worker (v3 payload).

After a tactic application assigns a goal mvar, the worker instantiates the
assignment and emits, per closed goal, `used_hypotheses` (goal-lctx fvars in
the proof term, expanded to their dependency closure) and `used_constants`
(bounded).  Fixture payloads mirror live v3 worker output (local Lean 4.31
probe, 2026-07-05).  Litmus: on `∀ (a b : Nat), a = 0 → b = b` with prefix
`intro a b h`, `rfl` must NOT pull in `h` or `a`; on
`∀ (a b : Nat), a = 0 → a + b = b`, `rw [h]` MUST pull in `h`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lean_rgc.lean.minimal_support import (
    SCHEMA_MINIMAL_SUPPORT,
    minimal_support_goals,
    support_by_mvar,
    support_key,
    used_constants,
    used_hypothesis_names,
)
from lean_rgc.lean.structured_state import extract_structured_state_from_kernel_json
from lean_rgc.native_worker import packaged_kernel_rpc_worker_path


def _hyp(fvar_id, user_name, type_text):
    return {
        "fvar_id": fvar_id,
        "user_name": user_name,
        "type_text": type_text,
        "is_implementation_detail": False,
    }


# `rfl` closing `b = b` under hypotheses a b : Nat, h : a = 0: the proof term
# `Eq.refl b` touches only b, so h and a stay OUT of the minimal support.
SUPPORT_RFL = {
    "schema_version": SCHEMA_MINIMAL_SUPPORT,
    "source": "lean_kernel_rpc_proof_term_v1",
    "goals": [
        {
            "mvar_id": "?_uniq.49",
            "used_hypotheses": [_hyp("fvar__uniq.45", "b", "Nat")],
            "used_constants": ["Eq.refl", "Nat"],
            "n_constants_total": 2,
            "constants_truncated": False,
            "residual_mvars": [],
            "fully_closed": True,
            "proof_hash_raw": "15458856919153879409",
        }
    ],
}

# `rw [h]` on `a + b = b`: the goal mvar is assigned `Eq.mpr (congrArg .. h) ?g'`
# — h enters the support directly and drags a in via its type `a = 0`.
SUPPORT_RW = {
    "schema_version": SCHEMA_MINIMAL_SUPPORT,
    "source": "lean_kernel_rpc_proof_term_v1",
    "goals": [
        {
            "mvar_id": "?_uniq.84",
            "used_hypotheses": [
                _hyp("fvar__uniq.77", "a", "Nat"),
                _hyp("fvar__uniq.80", "b", "Nat"),
                _hyp("fvar__uniq.83", "h", "a = 0"),
            ],
            "used_constants": ["Eq", "Eq.mpr", "congrArg", "id"],
            "n_constants_total": 4,
            "constants_truncated": False,
            "residual_mvars": ["?_uniq.88"],
            "fully_closed": False,
            "proof_hash_raw": "16725397178924170691",
        }
    ],
}


def _kernel_v3(task_id, state_id, minimal_support, goals=(), metavars=()):
    return {
        "schema_version": "lean-rgc-kernel-state-v3",
        "extraction_backend": "lean_kernel_rpc_in_memory_v1",
        "state_id": state_id,
        "task_id": task_id,
        "status": "closed" if not goals else "open",
        "goals": list(goals),
        "metavars": list(metavars),
        "local_contexts": [],
        "typeclasses": [],
        "messages": [],
        "minimal_support": minimal_support,
        "closed": not goals,
    }


KERNEL_RFL_V3 = _kernel_v3("t_rfl", "krpc_state_1", SUPPORT_RFL)


def test_v3_payload_surfaces_minimal_support_in_structured_state():
    row = extract_structured_state_from_kernel_json(KERNEL_RFL_V3, backend="kernel_json_v28").to_dict()
    assert row["metadata"]["kernel_schema_version"] == "lean-rgc-kernel-state-v3"
    ms = row["minimal_support"]
    assert ms["schema_version"] == SCHEMA_MINIMAL_SUPPORT
    assert ms["n_goals"] == 1
    assert row["metadata"]["n_minimal_support_goals"] == 1
    (goal,) = ms["goals"]
    assert goal["used_hypothesis_names"] == ["b"]
    assert goal["used_constants"] == ["Eq.refl", "Nat"]


def test_pre_v3_payload_yields_empty_minimal_support():
    kernel = {k: v for k, v in KERNEL_RFL_V3.items() if k != "minimal_support"}
    kernel["schema_version"] = "lean-rgc-kernel-state-v2"
    row = extract_structured_state_from_kernel_json(kernel, backend="kernel_json_v28").to_dict()
    assert row["minimal_support"] == {}
    assert minimal_support_goals(row) == []


def test_accessors_read_structured_row_and_transition_reply_shapes():
    row = extract_structured_state_from_kernel_json(KERNEL_RFL_V3, backend="kernel_json_v28").to_dict()
    (goal,) = minimal_support_goals(row)
    assert used_hypothesis_names(goal) == ["b"]
    assert used_constants(goal) == ["Eq.refl", "Nat"]

    # apply_tactic reply shape: support rides in state_delta (and the v3
    # kernel_state_after); the accessor finds it either way.
    reply = {"ok": True, "status": "partial", "state_delta": {"closed_goals": ["?_uniq.84"], "minimal_support": SUPPORT_RW}}
    by_mvar = support_by_mvar(reply)
    entry = by_mvar["?_uniq.84"]
    names = used_hypothesis_names(entry)
    assert "h" in names and "a" in names
    assert entry["fully_closed"] is False

    # face-taxonomy minimal_support (rows/contexts shape) must NOT match.
    assert minimal_support_goals({"minimal_support": {"rows": ["u_rfl"]}}) == []


def test_support_key_is_alpha_invariant_over_hypothesis_names():
    goal = SUPPORT_RFL["goals"][0]
    renamed = json.loads(json.dumps(goal))
    renamed["used_hypotheses"][0]["user_name"] = "x"
    renamed["used_hypotheses"][0]["fvar_id"] = "fvar__uniq.999"
    assert support_key(goal, target_text="b = b") == support_key(renamed, target_text="b = b")
    assert support_key(goal, target_text="b = b") != support_key(SUPPORT_RW["goals"][0], target_text="b = b")


def test_packaged_worker_source_declares_v3_minimal_support():
    text = packaged_kernel_rpc_worker_path().read_text(encoding="utf-8")
    assert '"lean-rgc-kernel-state-v3"' in text
    assert '"lean-rgc-minimal-support-v1"' in text
    assert '"minimal_support"' in text
    assert '"used_hypotheses"' in text
    assert '"used_constants"' in text
    assert "minimalSupportForGoal" in text
    assert "fvarSupportClosure" in text
    assert "collectConstNames" in text


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
def test_live_worker_minimal_support_litmus():
    lean = _lean_bin()
    worker = packaged_kernel_rpc_worker_path()
    lines = [
        {"id": "load", "cmd": "load_project", "imports": ["Lean"]},
        {"id": "init_rfl", "cmd": "init_state",
         "task": {"task_id": "t_rfl", "statement": "∀ (a b : Nat), a = 0 → b = b",
                  "prefix": "intro a b h", "imports": ["Lean"]}},
        {"id": "rfl", "cmd": "apply_tactic", "state_id": "krpc_state_0",
         "action": {"action_id": "rfl", "tactic": "rfl"}},
        {"id": "init_rw", "cmd": "init_state",
         "task": {"task_id": "t_rw", "statement": "∀ (a b : Nat), a = 0 → a + b = b",
                  "prefix": "intro a b h", "imports": ["Lean"]}},
        {"id": "rw", "cmd": "apply_tactic", "state_id": "krpc_state_2",
         "action": {"action_id": "rw_h", "tactic": "rw [h]"}},
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

    # Litmus 1: rfl closes `b = b` — support must exclude h and a.
    rfl = replies[2]
    assert rfl["status"] == "success"
    after = rfl["kernel_state_after"]
    assert after["schema_version"] == "lean-rgc-kernel-state-v3"
    assert after["minimal_support"] == rfl["state_delta"]["minimal_support"]
    (goal,) = minimal_support_goals(rfl)
    names = used_hypothesis_names(goal)
    assert names == ["b"], names
    assert "h" not in names and "a" not in names
    assert goal["fully_closed"] is True
    assert goal["residual_mvars"] == []
    assert "Eq.refl" in used_constants(goal) or "rfl" in used_constants(goal)

    # The structured-state row carries the same support.
    row = extract_structured_state_from_kernel_json(after, backend="kernel_json_v28").to_dict()
    assert [used_hypothesis_names(g) for g in minimal_support_goals(row)] == [["b"]]

    # Litmus 2: rw [h] assigns the goal mvar (partial: `0 + b = b` remains) —
    # support MUST include h, and the closure drags in a via `h : a = 0`.
    rw = replies[4]
    assert rw["status"] == "partial"
    assert rw["state_delta"]["closed_goals"], rw["state_delta"]
    (goal2,) = minimal_support_goals(rw)
    names2 = used_hypothesis_names(goal2)
    assert "h" in names2, names2
    assert "a" in names2, names2
    assert goal2["fully_closed"] is False
    assert goal2["residual_mvars"], goal2
