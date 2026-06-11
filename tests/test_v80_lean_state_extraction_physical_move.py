from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MODULES = {
    "structured_state": [
        "StructuredProofState",
        "GoalASTNode",
        "LocalContextGraph",
        "MetaVarGraph",
        "TypeclassObligationGraph",
        "extract_structured_state",
        "extract_structured_state_from_kernel_json",
        "structured_state_extract_cli",
    ],
    "kernel_state": [
        "KERNEL_STATE_SCHEMA_VERSION",
        "KernelGoalStateServer",
        "KernelGoalStateServerConfig",
        "KernelStateRecord",
        "normalize_kernel_state_v1",
        "structural_kernel_response",
    ],
    "goal_state_dynamics": [
        "SCHEMA_VERSION",
        "GRAPH_SCHEMA_VERSION",
        "TRANSITION_SCHEMA_VERSION",
        "normalize_goal_state_graph",
        "compute_goal_state_transition_delta",
        "goal_state_transitions_from_audits",
    ],
}


def test_state_extraction_implementations_live_under_lean_package():
    for module_name, attrs in MODULES.items():
        canonical = importlib.import_module(f"lean_rgc.lean.{module_name}")
        compat = importlib.import_module(f"lean_rgc.{module_name}")

        assert Path(canonical.__file__).resolve() == ROOT / "lean_rgc" / "lean" / f"{module_name}.py"
        assert Path(compat.__file__).resolve() == ROOT / "lean_rgc" / f"{module_name}.py"
        for attr in attrs:
            assert getattr(compat, attr) is getattr(canonical, attr)


def test_kernel_state_uses_canonical_goal_state_dynamics():
    text = (ROOT / "lean_rgc" / "lean" / "kernel_state.py").read_text(encoding="utf-8")
    assert "from .goal_state_dynamics import compute_goal_state_transition_delta" in text
    assert "from ..goal_state_dynamics import" not in text
    assert "from .lean.goal_state_dynamics import" not in text


def test_fresh_state_extraction_imports_do_not_reintroduce_circular_imports():
    code = """
import lean_rgc
import lean_rgc.structured_state
import lean_rgc.kernel_state
import lean_rgc.goal_state_dynamics
import lean_rgc.lean.structured_state
import lean_rgc.lean.kernel_state
import lean_rgc.lean.goal_state_dynamics
import lean_rgc.lean_server
import lean_rgc.persistent_lean_worker
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr


def test_runtime_callers_use_canonical_state_extraction_imports():
    expected = {
        "arithmetic_teacher_kernel_audit.py": "from .lean.server import LeanServerAdapter, LeanServerConfig",
        "lean/server.py": "from .structured_state import extract_structured_state, extract_structured_state_from_kernel_json",
        "kernel_context_cache.py": "from .lean.structured_state import extract_structured_state_from_kernel_json",
        "lean/persistent_lean_worker.py": "from .structured_state import extract_structured_state, extract_structured_state_from_kernel_json",
        "__init__.py": "from .lean.kernel_state import KernelGoalStateServer",
    }
    for filename, needle in expected.items():
        text = (ROOT / "lean_rgc" / filename).read_text(encoding="utf-8")
        assert needle in text

    server_text = (ROOT / "lean_rgc" / "lean" / "server.py").read_text(encoding="utf-8")
    cache_text = (ROOT / "lean_rgc" / "kernel_context_cache.py").read_text(encoding="utf-8")
    worker_text = (ROOT / "lean_rgc" / "lean" / "persistent_lean_worker.py").read_text(encoding="utf-8")
    assert "from .goal_state_dynamics import goal_state_transition_from_audit" in server_text
    assert "from .lean.goal_state_dynamics import goal_state_transition_from_audit" in cache_text
    assert "from .goal_state_dynamics import compute_goal_state_transition_delta" in worker_text
    assert "from .kernel_state import normalize_kernel_state_v1" in worker_text


def test_state_extraction_helpers_still_work_through_compatibility_paths():
    from lean_rgc.goal_state_dynamics import compute_goal_state_transition_delta
    from lean_rgc.kernel_state import normalize_kernel_state_v1
    from lean_rgc.structured_state import extract_structured_state_from_kernel_json

    before = {
        "schema_version": "lean-rgc-kernel-state-v1",
        "state_id": "s0",
        "task_id": "t",
        "goals": [{"mvar_id": "?m.1", "target": {"text": "n = n", "head": "Eq"}}],
        "local_context": {"nodes": [{"fvar_id": "fvar_n", "user_name": "n", "type_text": "Nat"}], "edges": []},
        "metavars": [{"mvar_id": "?m.1", "type_text": "n = n"}],
        "typeclasses": [],
    }
    after = {**before, "state_id": "s1", "goals": [], "metavars": [], "closed": True}
    normalized = normalize_kernel_state_v1(before)
    structured = extract_structured_state_from_kernel_json(before).to_dict()
    delta = compute_goal_state_transition_delta(before, after, action={"action_id": "rfl", "tactic": "rfl"})

    assert normalized["schema_version"] == "lean-rgc-kernel-state-v1"
    assert structured["schema_version"].startswith("lean-rgc-structured-state")
    assert delta["progress_status"] == "closed"
