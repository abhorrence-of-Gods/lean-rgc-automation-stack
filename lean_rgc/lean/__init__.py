from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "BulkAuditConfig": "bulk_executor",
    "FrontierAuditSummaryCompat": "frontier",
    "FrontierAuditor": "frontier",
    "FrontierRecord": "frontier",
    "KernelGoalStateServer": "kernel_state",
    "KernelGoalStateServerConfig": "kernel_state",
    "KernelStateRecord": "kernel_state",
    "LeanExecutor": "executor",
    "LeanExecutorConfig": "executor",
    "LeanServerAdapter": "server",
    "LeanServerConfig": "server",
    "LeanServerStatus": "server",
    "NativeWorkerInstall": "native_worker",
    "PersistentLeanWorker": "persistent_worker",
    "PersistentStateRecord": "persistent_worker",
    "StructuredProofState": "structured_state",
    "WorkerConfig": "persistent_worker",
    "adapter_from_executor_args": "server",
    "audit_with_lean_server": "server",
    "bulk_audit_to_files": "bulk_executor",
    "build_frontiers": "frontier",
    "enqueue_and_run_supervised_audit": "worker_supervisor",
    "expose_frontier_files": "frontier",
    "goal_state_transitions_from_audits": "goal_state_dynamics",
    "install_native_worker": "native_worker",
    "kernel_state_graphs_from_jsonl": "goal_state_dynamics",
    "native_worker_command": "native_worker",
    "native_worker_manifest": "native_worker",
    "normalize_kernel_state_v1": "kernel_state",
    "run_bulk_audit_queue": "worker_supervisor",
    "run_persistent_worker": "persistent_worker",
    "run_server_micro_audit_to_files": "server",
    "run_supervised_audit_queue": "worker_supervisor",
    "serve_jsonl": "persistent_worker",
    "server_audit_to_files": "server",
    "structured_state_extract_cli": "structured_state",
    "summarize_structured_states": "structured_state",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module_name}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
