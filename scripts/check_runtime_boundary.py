from __future__ import annotations

import argparse
import ast
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "lean-rgc.runtime-boundary-check.v1"
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "lean_rgc"


@dataclass(frozen=True)
class RuntimeModule:
    canonical: str
    compatibility: str
    canonical_path: str
    compatibility_path: str
    attrs: tuple[str, ...]


@dataclass
class Violation:
    kind: str
    path: str
    message: str
    detail: str = ""


RUNTIME_MODULES: tuple[RuntimeModule, ...] = (
    RuntimeModule("lean_rgc.lean.executor", "lean_rgc.executor", "lean_rgc/lean/executor.py", "lean_rgc/executor.py", ("LeanExecutor", "LeanExecutorConfig")),
    RuntimeModule("lean_rgc.lean.bulk_executor", "lean_rgc.bulk_executor", "lean_rgc/lean/bulk_executor.py", "lean_rgc/bulk_executor.py", ("BulkAuditConfig", "LeanBulkAuditor", "bulk_audit_to_files")),
    RuntimeModule("lean_rgc.lean.server", "lean_rgc.lean_server", "lean_rgc/lean/server.py", "lean_rgc/lean_server.py", ("LeanServerConfig", "LeanServerAdapter", "audit_with_lean_server", "project_fingerprint")),
    RuntimeModule("lean_rgc.lean.persistent_lean_worker", "lean_rgc.persistent_lean_worker", "lean_rgc/lean/persistent_lean_worker.py", "lean_rgc/persistent_lean_worker.py", ("PersistentLeanWorker", "WorkerConfig", "PersistentStateRecord", "main")),
    RuntimeModule("lean_rgc.lean.persistent_worker", "lean_rgc.persistent_worker", "lean_rgc/lean/persistent_worker.py", "lean_rgc/persistent_worker.py", ("PersistentLeanWorker", "WorkerConfig", "run_persistent_worker", "main")),
    RuntimeModule("lean_rgc.lean.native_worker", "lean_rgc.native_worker", "lean_rgc/lean/native_worker.py", "lean_rgc/native_worker.py", ("NativeWorkerInstall", "native_worker_command", "native_worker_manifest", "main")),
    RuntimeModule("lean_rgc.lean.state_parser", "lean_rgc.state_parser", "lean_rgc/lean/state_parser.py", "lean_rgc/state_parser.py", ("LeanMessageParser", "parse_proof_state")),
    RuntimeModule("lean_rgc.lean.kernel_state", "lean_rgc.kernel_state", "lean_rgc/lean/kernel_state.py", "lean_rgc/kernel_state.py", ("KernelGoalStateServer", "KernelGoalStateServerConfig", "normalize_kernel_state_v1")),
    RuntimeModule("lean_rgc.lean.structured_state", "lean_rgc.structured_state", "lean_rgc/lean/structured_state.py", "lean_rgc/structured_state.py", ("StructuredProofState", "extract_structured_state", "structured_state_extract_cli")),
    RuntimeModule("lean_rgc.lean.goal_state_dynamics", "lean_rgc.goal_state_dynamics", "lean_rgc/lean/goal_state_dynamics.py", "lean_rgc/goal_state_dynamics.py", ("normalize_goal_state_graph", "compute_goal_state_transition_delta", "goal_state_transitions_from_audits")),
    RuntimeModule("lean_rgc.lean.frontier", "lean_rgc.frontier", "lean_rgc/lean/frontier.py", "lean_rgc/frontier.py", ("FrontierRecord", "build_frontiers", "expose_frontier_files")),
    RuntimeModule("lean_rgc.lean.worker_supervisor", "lean_rgc.lean_worker_supervisor", "lean_rgc/lean/worker_supervisor.py", "lean_rgc/lean_worker_supervisor.py", ("enqueue_and_run_supervised_audit", "run_bulk_audit_queue", "run_supervised_audit_queue")),
)

COMPAT_MODULES = {m.compatibility for m in RUNTIME_MODULES}
COMPAT_PATHS = {m.compatibility_path for m in RUNTIME_MODULES}


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def module_name_for_path(path: Path) -> str:
    rel = path.resolve().relative_to(ROOT.resolve()).with_suffix("")
    return ".".join(rel.parts)


def package_name_for_path(path: Path) -> str:
    module_name = module_name_for_path(path)
    if path.name == "__init__.py":
        return module_name
    return module_name.rsplit(".", 1)[0]


def resolve_import_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level <= 0:
        return node.module
    package_parts = package_name_for_path(path).split(".")
    if node.level > len(package_parts):
        return None
    base = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def is_compat_module(module: str | None) -> bool:
    if not module:
        return False
    return module in COMPAT_MODULES or any(module.startswith(f"{compat}.") for compat in COMPAT_MODULES)


def scan_imports(path: Path) -> list[Violation]:
    rel = repo_path(path)
    if rel in COMPAT_PATHS:
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [Violation("parse_error", rel, "could not parse Python file", str(exc))]
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_compat_module(alias.name):
                    violations.append(Violation("compat_import", rel, "runtime-facing code imports a compatibility runtime module", alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = resolve_import_from(path, node)
            if is_compat_module(module):
                detail = f"{'.' * node.level}{node.module or ''}" if node.level else (node.module or "")
                violations.append(Violation("compat_import", rel, "runtime-facing code imports a compatibility runtime module", detail))
            if module == "lean_rgc":
                for alias in node.names:
                    candidate = f"lean_rgc.{alias.name}"
                    if is_compat_module(candidate):
                        violations.append(Violation("compat_import", rel, "runtime-facing code imports a compatibility runtime module", candidate))
    return violations


def check_shim(module: RuntimeModule) -> list[Violation]:
    rel = module.compatibility_path
    path = ROOT / rel
    if not path.exists():
        return [Violation("missing_shim", rel, "compatibility shim file is missing")]
    text = path.read_text(encoding="utf-8")
    expected_star = f"from .lean.{module.canonical.rsplit('.', 1)[-1]} import *"
    if expected_star not in text:
        return [Violation("invalid_shim", rel, "compatibility shim does not re-export canonical module", expected_star)]
    blocked = ("class ", "def ", "@dataclass")
    violations = [Violation("fat_shim", rel, "compatibility shim contains implementation-like code", token) for token in blocked if token in text]
    if len(text.splitlines()) > 30:
        violations.append(Violation("fat_shim", rel, "compatibility shim is unexpectedly large", f"{len(text.splitlines())} lines"))
    return violations


def check_identity(module: RuntimeModule) -> list[Violation]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    violations: list[Violation] = []
    canonical = importlib.import_module(module.canonical)
    compatibility = importlib.import_module(module.compatibility)
    if repo_path(Path(canonical.__file__ or "")) != module.canonical_path:
        violations.append(Violation("canonical_path", module.canonical_path, "canonical module file path does not match contract", str(canonical.__file__)))
    if repo_path(Path(compatibility.__file__ or "")) != module.compatibility_path:
        violations.append(Violation("compatibility_path", module.compatibility_path, "compatibility module file path does not match contract", str(compatibility.__file__)))
    for attr in module.attrs:
        if not hasattr(canonical, attr):
            violations.append(Violation("missing_export", module.canonical_path, "canonical module is missing expected export", attr))
            continue
        if not hasattr(compatibility, attr):
            violations.append(Violation("missing_export", module.compatibility_path, "compatibility module is missing expected export", attr))
            continue
        if getattr(canonical, attr) is not getattr(compatibility, attr):
            violations.append(Violation("identity_mismatch", module.compatibility_path, "compatibility export is not identical to canonical export", attr))
    return violations


def runtime_files() -> list[Path]:
    return sorted(path for path in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def run_check() -> dict[str, Any]:
    checked_files = [repo_path(path) for path in runtime_files()]
    violations: list[Violation] = []
    for module in RUNTIME_MODULES:
        violations.extend(check_shim(module))
        violations.extend(check_identity(module))
    for path in runtime_files():
        violations.extend(scan_imports(path))
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not violations,
        "checked_modules": [asdict(module) for module in RUNTIME_MODULES],
        "checked_files": checked_files,
        "n_checked_modules": len(RUNTIME_MODULES),
        "n_checked_files": len(checked_files),
        "violations": [asdict(violation) for violation in violations],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Lean runtime canonical package boundary.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)
    result = run_check()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["ok"]:
        print(f"runtime boundary ok: {result['n_checked_modules']} modules, {result['n_checked_files']} files")
    else:
        print("runtime boundary violations:")
        for violation in result["violations"]:
            detail = f" ({violation['detail']})" if violation.get("detail") else ""
            print(f"- {violation['kind']}: {violation['path']}: {violation['message']}{detail}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
