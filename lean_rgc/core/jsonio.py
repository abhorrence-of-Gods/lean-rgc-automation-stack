from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

from .ids import stable_hash


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                rows.append(obj if isinstance(obj, dict) else {"value": obj})
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_records(
    path: str | Path,
    rows: Iterable[dict[str, Any]],
    *,
    schema_version: str,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
    artifact_ref: str | None = None,
) -> None:
    stamped: list[dict[str, Any]] = []
    parents = list(parent_ids or [])
    rid = run_id or default_run_id_for_path(path)
    for row in rows:
        out = dict(row)
        out.setdefault("schema_version", schema_version)
        out.setdefault("run_id", rid)
        out.setdefault("parent_ids", parents)
        if artifact_ref is not None:
            out.setdefault("artifact_ref", artifact_ref)
        stamped.append(out)
    write_jsonl(path, stamped)


def default_run_id_for_path(path: str | Path) -> str:
    parent = Path(path).parent
    try:
        key = str(parent.resolve())
    except Exception:
        key = str(parent)
    return "run_" + stable_hash({"out_parent": key}, 20)


__all__ = ["default_run_id_for_path", "read_jsonl", "write_jsonl", "write_records"]
