from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "lean-rgc.dead-candidate-ledger-check.v1"
ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "inventory" / "imports.json"
LEDGER_PATH = ROOT / "docs" / "inventory" / "dead_candidates.md"
MODULE_HEADING = re.compile(r"^##\s+(lean_rgc(?:\.[A-Za-z0-9_]+)+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ModuleObservation:
    module: str
    path: str
    imported_by: list[str]
    imports: list[str]
    compile_status: str
    compile_detail: str
    import_status: str
    import_detail: str
    ledger_entry: bool
    deletion_blocked: bool
    risk_documented: bool


@dataclass(frozen=True)
class Violation:
    kind: str
    module: str
    message: str


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _load_dead_candidates() -> list[dict[str, Any]]:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return [
        row
        for row in payload.get("modules", [])
        if row.get("classification") == "dead_candidate"
    ]


def _ledger_sections() -> dict[str, str]:
    if not LEDGER_PATH.exists():
        return {}
    text = LEDGER_PATH.read_text(encoding="utf-8")
    matches = list(MODULE_HEADING.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end]
    return sections


def _compile_status(path: Path) -> tuple[str, str]:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:  # pragma: no cover - exercised only by broken candidates.
        return "error", f"{type(exc).__name__}: {exc}"
    return "ok", ""


def _import_status(module: str) -> tuple[str, str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        importlib.import_module(module)
    except Exception as exc:  # pragma: no cover - exercised only by broken candidates.
        return "error", f"{type(exc).__name__}: {exc}"
    return "ok", ""


def _observe_module(row: dict[str, Any], sections: dict[str, str]) -> ModuleObservation:
    module = str(row["module"])
    path = ROOT / str(row["path"])
    section = sections.get(module, "")
    compile_status, compile_detail = _compile_status(path)
    import_status, import_detail = _import_status(module)
    lowered = section.lower()
    return ModuleObservation(
        module=module,
        path=_repo_path(path),
        imported_by=list(row.get("imported_by", [])),
        imports=list(row.get("imports", [])),
        compile_status=compile_status,
        compile_detail=compile_detail,
        import_status=import_status,
        import_detail=import_detail,
        ledger_entry=bool(section),
        deletion_blocked="not approved for deletion" in lowered,
        risk_documented="risk:" in lowered or "risk note:" in lowered,
    )


def run_check() -> dict[str, Any]:
    dead_candidates = _load_dead_candidates()
    sections = _ledger_sections()
    expected = {str(row["module"]) for row in dead_candidates}
    observed = [_observe_module(row, sections) for row in dead_candidates]
    violations: list[Violation] = []

    for module in sorted(expected - set(sections)):
        violations.append(Violation("missing_ledger_entry", module, "dead candidate is not recorded in the human ledger"))
    for module in sorted(set(sections) - expected):
        violations.append(Violation("stale_ledger_entry", module, "ledger entry is no longer a generated dead candidate"))
    for row in observed:
        if row.ledger_entry and not row.deletion_blocked:
            violations.append(Violation("deletion_not_blocked", row.module, "ledger entry must say not approved for deletion"))
        if row.ledger_entry and (row.compile_status != "ok" or row.import_status != "ok") and not row.risk_documented:
            violations.append(Violation("missing_risk_note", row.module, "non-importable or non-compiling candidate must have an explicit risk note"))

    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not violations,
        "inventory_path": _repo_path(INVENTORY_PATH),
        "ledger_path": _repo_path(LEDGER_PATH),
        "checked_modules": [asdict(row) for row in observed],
        "n_checked_modules": len(observed),
        "missing": sorted(expected - set(sections)),
        "stale": sorted(set(sections) - expected),
        "violations": [asdict(violation) for violation in violations],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the human disposition ledger for generated dead candidates.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)
    result = run_check()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["ok"]:
        print(f"dead candidate ledger ok: {result['n_checked_modules']} modules")
    else:
        print("dead candidate ledger violations:")
        for violation in result["violations"]:
            print(f"- {violation['kind']}: {violation['module']}: {violation['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
