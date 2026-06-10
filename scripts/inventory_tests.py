from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from inventory_common import INVENTORY_SCHEMA_VERSION, ROOT, repo_path, write_inventory


def lean_rgc_imports(path: Path) -> list[str]:
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
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "lean_rgc" or node.module.startswith("lean_rgc."):
                imports.add(node.module)
    return sorted(imports)


def classify_test(tiers: list[str]) -> str:
    if "legacy" in tiers:
        return "legacy"
    if "slow" in tiers:
        return "experimental"
    return "core"


def build_inventory(root: Path) -> dict:
    tests_dir = root / "tests"
    manifest = json.loads((tests_dir / "tier_manifest.json").read_text(encoding="utf-8"))
    files = []
    summary: dict[str, int] = {}
    tier_summary: dict[str, int] = {}
    for name, tiers in sorted(manifest.items()):
        path = tests_dir / name
        classification = classify_test(list(tiers))
        summary[classification] = summary.get(classification, 0) + 1
        for tier in tiers:
            tier_summary[tier] = tier_summary.get(tier, 0) + 1
        files.append(
            {
                "file": repo_path(path, root),
                "tiers": list(tiers),
                "imports": lean_rgc_imports(path),
                "classification": classification,
            }
        )
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "inventory_type": "tests",
        "files": files,
        "summary": dict(sorted(summary.items())),
        "tier_summary": dict(sorted(tier_summary.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Lean-RGC pytest tier coverage.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=str(ROOT / "docs" / "inventory" / "tests.json"))
    args = parser.parse_args()
    payload = build_inventory(Path(args.root))
    write_inventory(Path(args.out), payload)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

