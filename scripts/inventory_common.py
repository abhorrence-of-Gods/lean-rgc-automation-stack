from __future__ import annotations

import json
from pathlib import Path


INVENTORY_SCHEMA_VERSION = "lean-rgc.inventory.v1"
ROOT = Path(__file__).resolve().parents[1]

CORE_PREFIXES = (
    "lean_rgc.cli",
    "lean_rgc.core",
    "lean_rgc.data",
    "lean_rgc.dost",
    "lean_rgc.lean",
)
CORE_MODULES = {
    "lean_rgc.__init__",
    "lean_rgc.schemas",
    "lean_rgc.batch",
    "lean_rgc.bulk_executor",
    "lean_rgc.executor",
    "lean_rgc.frontier",
    "lean_rgc.goal_state_dynamics",
    "lean_rgc.kernel_state",
    "lean_rgc.lean_worker_supervisor",
    "lean_rgc.lean_server",
    "lean_rgc.native_worker",
    "lean_rgc.state_parser",
    "lean_rgc.structured_state",
    "lean_rgc.persistent_worker",
    "lean_rgc.response_completion",
    "lean_rgc.response_quotient",
    "lean_rgc.contextual_congruence",
    "lean_rgc.face_taxonomy",
    "lean_rgc.obstruction_tower",
    "lean_rgc.repair_space",
    "lean_rgc.relaxed_species",
    "lean_rgc.crg_registry",
    "lean_rgc.crg_problem",
    "lean_rgc.crg_optimizer",
    "lean_rgc.crg_hardening",
    "lean_rgc.crg_audit",
    "lean_rgc.hardening_gap_report",
    "lean_rgc.concept_geometry",
    "lean_rgc.concept_search",
    "lean_rgc.concept_hardening",
    "lean_rgc.poms_status",
    "lean_rgc.poms_promotion",
    "lean_rgc.poms_promotion_service",
    "lean_rgc.pipeline",
    "lean_rgc.repair_db",
    "lean_rgc.audit_db",
}
LEGACY_MODULES = {
    "lean_rgc.iterative",
    "lean_rgc.iteration",
    "lean_rgc.iteration_report",
    "lean_rgc.coker",
    "lean_rgc.coker_synthesis",
    "lean_rgc.stage_coker",
}
EXPERIMENTAL_PREFIXES = ("lean_rgc.experiment",)


def repo_path(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def module_name_for_path(path: Path, root: Path = ROOT) -> str:
    rel = path.resolve().relative_to(root.resolve()).with_suffix("")
    return ".".join(rel.parts)


def classify_module(module: str, *, imported_by: list[str] | None = None, cli_reachable: bool = False) -> str:
    imported_by = imported_by or []
    if module.startswith(CORE_PREFIXES) or module in CORE_MODULES:
        return "core"
    if module.startswith("lean_rgc.cli_") or module in LEGACY_MODULES:
        return "legacy"
    if module.startswith(EXPERIMENTAL_PREFIXES):
        return "experimental"
    if cli_reachable:
        return "core"
    if not imported_by and not module.endswith(".__init__"):
        return "dead_candidate"
    return "experimental"


def write_inventory(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
