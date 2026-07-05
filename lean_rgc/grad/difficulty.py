"""D5 v1: per-task difficulty table from audited candidate rows.

Count-with-shrinkage estimate of P(candidate succeeds | task), used to
(a) bucket tasks for stratified RLOO grouping and (b) serve as the
state-level control variate b(s) in rloo_advantages.

v2 (registered direction, not built here): the E-MZ T2 finding — wave-0
outcome summaries carry a persistent difficulty fingerprint that later
feedback-conditioned waves dilute — says the model-based difficulty head
should consume wave-0/root defect features; that head is the twist's
state_value (M2, after kernel_rpc data exists).

Torch-free; runs in the default CI tier.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..schemas import read_jsonl

SCHEMA_TASK_DIFFICULTY = "lean-rgc-task-difficulty-v97.0"


def task_difficulty_from_micro_rows(
    rows: list[dict[str, Any]],
    *,
    shrinkage: float = 20.0,
    success_status: str = "success",
) -> dict[str, float]:
    succ: dict[str, float] = defaultdict(float)
    cnt: dict[str, float] = defaultdict(float)
    for r in rows:
        task = str(r.get("task_id") or "")
        if not task:
            continue
        cnt[task] += 1.0
        if str(r.get("status") or r.get("audit_status") or "") == success_status:
            succ[task] += 1.0
    total = sum(cnt.values())
    p0 = (sum(succ.values()) / total) if total else 0.0
    return {t: (succ[t] + shrinkage * p0) / (cnt[t] + shrinkage) for t in cnt}


def difficulty_from_waves_root(waves_root: str | Path, *, shrinkage: float = 20.0) -> dict[str, Any]:
    root = Path(waves_root)
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for wave_dir in sorted(run_dir.glob("wave_*")):
            if not re.match(r"wave_(\d+)$", wave_dir.name):
                continue
            micro = wave_dir / "micro_audit.jsonl"
            if micro.exists():
                for r in read_jsonl(micro):
                    if isinstance(r, dict):
                        rows.append({"task_id": r.get("task_id"), "status": r.get("status")})
    table = task_difficulty_from_micro_rows(rows, shrinkage=shrinkage)
    return {
        "schema_version": SCHEMA_TASK_DIFFICULTY,
        "n_rows": len(rows),
        "n_tasks": len(table),
        "shrinkage": shrinkage,
        "table": table,
        "canonical_status": "difficulty_table_witness_not_canonical",
    }


def load_difficulty_table(path: str | Path) -> dict[str, float]:
    """Accepts either a bare {task_id: p} mapping or the report format."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    table = data.get("table") if isinstance(data, dict) and "table" in data else data
    return {str(k): float(v) for k, v in dict(table).items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shrinkage", type=float, default=20.0)
    args = ap.parse_args(argv)
    report = difficulty_from_waves_root(args.waves_root, shrinkage=args.shrinkage)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_rows", "n_tasks", "shrinkage")}, indent=2))
    return 0


__all__ = [
    "SCHEMA_TASK_DIFFICULTY",
    "difficulty_from_waves_root",
    "load_difficulty_table",
    "task_difficulty_from_micro_rows",
]

if __name__ == "__main__":
    raise SystemExit(main())
