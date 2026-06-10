from __future__ import annotations

import argparse
import sys
from pathlib import Path

from inventory_common import INVENTORY_SCHEMA_VERSION, ROOT, classify_module, write_inventory


def subparser_actions(parser: argparse.ArgumentParser) -> list[argparse._SubParsersAction]:
    return [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]


def walk_commands(parser: argparse.ArgumentParser, prefix: list[str] | None = None) -> list[dict]:
    prefix = prefix or []
    actions = subparser_actions(parser)
    if not actions:
        func = parser._defaults.get("func")
        module = getattr(func, "__module__", "") if func else ""
        deprecated = parser._defaults.get("deprecated_command", "")
        replacement = parser._defaults.get("replacement_command", "")
        classification = "legacy" if deprecated else classify_module(module, cli_reachable=True)
        return [
            {
                "command": " ".join(prefix),
                "handler": getattr(func, "__name__", "") if func else "",
                "module": module,
                "deprecated": bool(deprecated),
                "replacement": replacement,
                "classification": classification,
            }
        ]

    rows: list[dict] = []
    for action in actions:
        for name, child in sorted(action.choices.items()):
            rows.extend(walk_commands(child, [*prefix, name]))
    return rows


def build_inventory(root: Path) -> dict:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from lean_rgc.cli import build_parser

    commands = walk_commands(build_parser())
    modules: dict[str, dict] = {}
    for command in commands:
        module = command["module"]
        if not module:
            continue
        info = modules.setdefault(
            module,
            {
                "module": module,
                "commands": [],
                "classification": classify_module(module, cli_reachable=True),
            },
        )
        info["commands"].append(command["command"])
        if command["deprecated"]:
            info["classification"] = "legacy"

    summary: dict[str, int] = {}
    for command in commands:
        summary[command["classification"]] = summary.get(command["classification"], 0) + 1
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "inventory_type": "cli",
        "commands": commands,
        "modules": sorted(modules.values(), key=lambda row: row["module"]),
        "summary": dict(sorted(summary.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Lean-RGC CLI command reachability.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=str(ROOT / "docs" / "inventory" / "cli.json"))
    args = parser.parse_args()
    payload = build_inventory(Path(args.root))
    write_inventory(Path(args.out), payload)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

