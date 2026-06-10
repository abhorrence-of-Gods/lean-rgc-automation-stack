from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from inventory_common import INVENTORY_SCHEMA_VERSION, ROOT, classify_module, module_name_for_path, repo_path, write_inventory


def iter_python_modules(root: Path) -> Iterable[Path]:
    yield from sorted((root / "lean_rgc").rglob("*.py"))


def resolve_from_import(current: str, node: ast.ImportFrom) -> list[str]:
    if node.level == 0:
        return [node.module] if node.module and node.module.startswith("lean_rgc") else []
    parts = current.split(".")
    base_parts = parts[:-node.level]
    base = ".".join(base_parts)
    if node.module:
        return [f"{base}.{node.module}"]
    return [f"{base}.{alias.name}" for alias in node.names if alias.name != "*"]


def internal_imports(path: Path, root: Path) -> list[str]:
    module = module_name_for_path(path, root)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "lean_rgc" or alias.name.startswith("lean_rgc."):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for resolved in resolve_from_import(module, node):
                if resolved == "lean_rgc" or resolved.startswith("lean_rgc."):
                    imports.add(resolved)
    return sorted(imports)


def build_inventory(root: Path) -> dict:
    modules: dict[str, dict] = {}
    imported_by: dict[str, list[str]] = defaultdict(list)
    for path in iter_python_modules(root):
        module = module_name_for_path(path, root)
        imports = internal_imports(path, root)
        modules[module] = {"path": repo_path(path, root), "imports": imports}
        for imported in imports:
            imported_by[imported].append(module)

    rows = []
    for module, info in sorted(modules.items()):
        parents = sorted(imported_by.get(module, []))
        rows.append(
            {
                "module": module,
                "path": info["path"],
                "imports": info["imports"],
                "imported_by": parents,
                "classification": classify_module(module, imported_by=parents),
            }
        )

    summary: dict[str, int] = {}
    for row in rows:
        summary[row["classification"]] = summary.get(row["classification"], 0) + 1
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "inventory_type": "imports",
        "modules": rows,
        "summary": dict(sorted(summary.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Lean-RGC internal Python imports.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=str(ROOT / "docs" / "inventory" / "imports.json"))
    args = parser.parse_args()
    payload = build_inventory(Path(args.root))
    write_inventory(Path(args.out), payload)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

