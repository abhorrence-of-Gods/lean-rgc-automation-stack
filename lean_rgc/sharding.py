from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, write_jsonl, stable_hash


def _key(row: dict[str, Any], key: str | None) -> str:
    if not key:
        return json.dumps(row, sort_keys=True, ensure_ascii=False)[:500]
    cur: Any = row
    for part in key.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = None
            break
    return str(cur if cur is not None else row.get('task_id') or row.get('state_id') or row.get('action_id') or json.dumps(row, sort_keys=True, ensure_ascii=False)[:500])


def shard_jsonl(input_path: str | Path, out_dir: str | Path, *, shards: int, key: str | None = 'task_id', mode: str = 'hash', prefix: str = 'shard') -> dict[str, Any]:
    rows = read_jsonl(input_path)
    outp = Path(out_dir); outp.mkdir(parents=True, exist_ok=True)
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(max(1, int(shards)))]
    for i, row in enumerate(rows):
        idx = i % len(buckets) if mode == 'round_robin' else int(stable_hash(_key(row, key), 12), 16) % len(buckets)
        buckets[idx].append(row)
    manifest = {"input": str(input_path), "out_dir": str(outp), "shards": len(buckets), "n_rows": len(rows), "files": []}
    for i, b in enumerate(buckets):
        fp = outp / f"{prefix}_{i:04d}.jsonl"
        write_jsonl(fp, b)
        manifest["files"].append({"shard": i, "path": str(fp), "n": len(b)})
    (outp / f"{prefix}_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def merge_jsonl(inputs: list[str | Path], out: str | Path, *, dedup_key: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in inputs:
        for row in read_jsonl(p):
            if dedup_key:
                k = _key(row, dedup_key)
                if k in seen:
                    continue
                seen.add(k)
            rows.append(row)
    write_jsonl(out, rows)
    return {"n_inputs": len(inputs), "n_rows": len(rows), "out": str(out), "dedup_key": dedup_key}


__all__ = ["shard_jsonl", "merge_jsonl"]
