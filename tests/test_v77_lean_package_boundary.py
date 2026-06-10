import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CANONICAL_MODULES = {
    "lean_rgc.lean.executor": ("lean_rgc.executor", ["LeanExecutor", "LeanExecutorConfig"]),
    "lean_rgc.lean.server": ("lean_rgc.lean_server", ["LeanServerConfig", "LeanServerAdapter", "audit_with_lean_server"]),
    "lean_rgc.lean.persistent_worker": ("lean_rgc.persistent_worker", ["PersistentLeanWorker", "WorkerConfig", "run_persistent_worker"]),
    "lean_rgc.lean.native_worker": ("lean_rgc.native_worker", ["NativeWorkerInstall", "native_worker_command", "native_worker_manifest"]),
    "lean_rgc.lean.state_parser": ("lean_rgc.state_parser", ["LeanMessageParser", "parse_proof_state"]),
    "lean_rgc.lean.kernel_state": ("lean_rgc.kernel_state", ["KernelGoalStateServer", "KernelGoalStateServerConfig", "normalize_kernel_state_v1"]),
    "lean_rgc.lean.structured_state": ("lean_rgc.structured_state", ["StructuredProofState", "extract_structured_state", "structured_state_extract_cli"]),
    "lean_rgc.lean.goal_state_dynamics": ("lean_rgc.goal_state_dynamics", ["normalize_goal_state_graph", "compute_goal_state_transition_delta", "goal_state_transitions_from_audits"]),
    "lean_rgc.lean.frontier": ("lean_rgc.frontier", ["FrontierRecord", "build_frontiers", "expose_frontier_files"]),
    "lean_rgc.lean.worker_supervisor": ("lean_rgc.lean_worker_supervisor", ["enqueue_and_run_supervised_audit", "run_bulk_audit_queue", "run_supervised_audit_queue"]),
    "lean_rgc.lean.bulk_executor": ("lean_rgc.bulk_executor", ["BulkAuditConfig", "LeanBulkAuditor", "bulk_audit_to_files"]),
}


def test_canonical_lean_runtime_modules_import():
    for canonical_name in CANONICAL_MODULES:
        module = importlib.import_module(canonical_name)
        assert module.__all__


def test_canonical_exports_match_compatibility_modules():
    for canonical_name, (compat_name, attrs) in CANONICAL_MODULES.items():
        canonical = importlib.import_module(canonical_name)
        compat = importlib.import_module(compat_name)
        for attr in attrs:
            assert getattr(canonical, attr) is getattr(compat, attr)


def test_package_facade_reexports_from_canonical_modules():
    import lean_rgc.lean as lean

    for canonical_name, (_compat_name, attrs) in CANONICAL_MODULES.items():
        canonical = importlib.import_module(canonical_name)
        for attr in attrs:
            if hasattr(lean, attr):
                assert getattr(lean, attr) is getattr(canonical, attr)


def test_cli_and_pipeline_runtime_imports_use_canonical_boundary():
    files = [
        ROOT / "lean_rgc" / "cli" / "common.py",
        ROOT / "lean_rgc" / "cli" / "audit.py",
        ROOT / "lean_rgc" / "cli" / "experiment.py",
        ROOT / "lean_rgc" / "cli" / "pipeline.py",
        ROOT / "lean_rgc" / "cli" / "lean.py",
        ROOT / "lean_rgc" / "pipeline.py",
    ]
    forbidden = [
        "from ..executor import",
        "from ..lean_server import",
        "from ..bulk_executor import",
        "from ..frontier import",
        "from ..native_worker import",
        "from ..lean_worker_supervisor import",
        "from .executor import",
        "from .lean_server import",
        "from .bulk_executor import",
        "from .frontier import",
        "from .structured_state import",
        "from .lean_worker_supervisor import",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still uses compatibility import {needle!r}"


def test_top_level_runtime_imports_remain_compatible():
    import lean_rgc.bulk_executor as bulk_executor
    import lean_rgc.executor as executor
    import lean_rgc.frontier as frontier
    import lean_rgc.lean_server as lean_server
    import lean_rgc.lean_worker_supervisor as supervisor
    import lean_rgc.native_worker as native_worker

    assert executor.LeanExecutorConfig is importlib.import_module("lean_rgc.lean.executor").LeanExecutorConfig
    assert lean_server.LeanServerConfig is importlib.import_module("lean_rgc.lean.server").LeanServerConfig
    assert native_worker.native_worker_command is importlib.import_module("lean_rgc.lean.native_worker").native_worker_command
    assert frontier.build_frontiers is importlib.import_module("lean_rgc.lean.frontier").build_frontiers
    assert supervisor.run_supervised_audit_queue is importlib.import_module("lean_rgc.lean.worker_supervisor").run_supervised_audit_queue
    assert bulk_executor.bulk_audit_to_files is importlib.import_module("lean_rgc.lean.bulk_executor").bulk_audit_to_files
