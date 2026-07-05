"""Label audit: re-attribute tagged-format errors and recount successes.

Root cause (2026-07-05): bulk_executor's _ERROR_RE missed Lean's tagged
diagnostics ('error(lean.unknownIdentifier): ...'). Tagged lines were
stored as continuations under the PREVIOUS plain error's line key — in
the wrong block — and a block whose ONLY errors were tagged carried no
messages and was classified SUCCESS. Training then reinforced scripts
that fail with tagged errors (reward hacking through the label hole).

This module recounts, from stored rows alone, which claimed successes
have any error located inside their own block range, using the
chunk-wide pool of stored error locations (tagged lines retain their
own file:line:col even when mis-keyed). Rows must carry
audit_flags.block_start_line/block_end_line (R0c instrumentation);
older rows without them are left as claimed and counted separately.

LOWER-BOUND caveat: a tagged error with NO preceding plain error in the
entire chunk output was dropped at storage time and is unrecoverable
retro; the false-success counts here are lower bounds.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..schemas import read_jsonl

SCHEMA_LABEL_AUDIT = "lean-rgc-label-audit-v99.0"

_ANYLOC_RE = re.compile(r"^([^\s:]+\.lean):(\d+):(\d+):\s*(error|warning)(\([^)]*\))?:\s*(.*)$")


def recount_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pool: dict[str, set[int]] = defaultdict(set)
    for r in rows:
        for m in (r.get("messages") or []):
            mm = _ANYLOC_RE.match(str(m).strip())
            if mm and mm.group(4) == "error":
                pool[str(r.get("lean_file"))].add(int(mm.group(2)))
    n_success = n_false = n_unrangeable = 0
    claimed: set[str] = set()
    true_solved: set[str] = set()
    false_rows: list[dict[str, Any]] = []
    for r in rows:
        if str(r.get("status")) != "success":
            continue
        n_success += 1
        task = str(r.get("task_id"))
        claimed.add(task)
        flags = r.get("audit_flags") or {}
        bs, be = flags.get("block_start_line"), flags.get("block_end_line")
        if bs is None or be is None:
            n_unrangeable += 1
            true_solved.add(task)  # cannot re-attribute: left as claimed
            continue
        bad = sorted(L for L in pool[str(r.get("lean_file"))] if int(bs) <= L <= int(be))
        if bad:
            n_false += 1
            false_rows.append({
                "task_id": task,
                "tactic": str((r.get("action") or {}).get("tactic") or "")[:120],
                "error_lines": bad[:5],
            })
        else:
            true_solved.add(task)
    return {
        "schema_version": SCHEMA_LABEL_AUDIT,
        "n_success_rows": n_success,
        "n_false_success_rows": n_false,
        "n_unrangeable_rows": n_unrangeable,
        "claimed_tasks": sorted(claimed),
        "true_tasks": sorted(true_solved),
        "false_rows": false_rows,
        "caveat": "lower_bound_dropped_tagged_errors_unrecoverable",
    }


def recount_run(run_dir: str | Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for micro in sorted(Path(run_dir).glob("wave_*/micro_audit.jsonl")):
        rows.extend(r for r in read_jsonl(micro) if isinstance(r, dict))
    out = recount_rows(rows)
    out["run_dir"] = str(run_dir)
    return out


def recount_pilot_layout(waves_root: str | Path) -> dict[str, Any]:
    """Recount pilot-era rows (no stored block offsets) by reconstructing
    block ranges with the D3 chunk machinery (lean_file grouping + file
    order + 'by'-column anchor). Same lower-bound caveat applies.

    The true verdict of a (task_id, tactic) pair is deterministic, so the
    output false set is keyed by (task_id, tactic) and applies to every
    replica (cache hits copy the fresh row's result)."""
    from .prefix_salvage import _load_rows, _n_block_lines, _reconstruct_chunks

    rows = _load_rows(Path(waves_root))
    chunk_off, chunk_h, _agree = _reconstruct_chunks(rows)
    pool: dict[str, set[int]] = defaultdict(set)
    for r in rows:
        for m in r["messages"]:
            mm = _ANYLOC_RE.match(str(m).strip())
            if mm and mm.group(4) == "error":
                pool[r["lean_file"]].add(int(mm.group(2)))
    n_success = n_false = n_unrangeable = 0
    false_pairs: set[tuple[str, str]] = set()
    examples: list[dict[str, Any]] = []
    for r in rows:
        if r["status"] != "success":
            continue
        n_success += 1
        off = chunk_off[r["lean_file"]].get((r["task_id"], r["action_id"]))
        if off is None:
            n_unrangeable += 1
            continue
        t_line = chunk_h[r["lean_file"]] + off + 3
        lo, hi = t_line - 1, t_line + _n_block_lines(r)
        bad = sorted(L for L in pool[r["lean_file"]] if lo <= L <= hi)
        if bad:
            n_false += 1
            pair = (r["task_id"], r["tactic"])
            if pair not in false_pairs and len(examples) < 10:
                examples.append({"task_id": r["task_id"], "tactic": r["tactic"][:120], "error_lines": bad[:4]})
            false_pairs.add(pair)
    return {
        "schema_version": SCHEMA_LABEL_AUDIT,
        "layout": "pilot",
        "n_success_rows": n_success,
        "n_false_success_rows": n_false,
        "n_unrangeable_rows": n_unrangeable,
        "n_false_pairs": len(false_pairs),
        "false_pairs": sorted(false_pairs),
        "examples": examples,
        "caveat": "lower_bound_dropped_tagged_errors_unrecoverable",
    }


def load_false_pairs(path: str | Path) -> set[tuple[str, str]]:
    """Accepts a single recount report or a {name: report} bundle."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out: set[tuple[str, str]] = set()
    reports = [d] if "false_pairs" in d or "schema_version" in d else list(d.values())
    for rep in reports:
        if isinstance(rep, dict):
            for t, s in rep.get("false_pairs", []):
                out.add((str(t), str(s)))
    if not out:
        raise ValueError(f"no false_pairs found in {path} — refusing to silently no-op")
    return out


def apply_corrected_labels(rows: list[dict[str, Any]], false_pairs: set[tuple[str, str]]) -> int:
    """In-place: demote false successes to elab_error. Returns count."""
    n = 0
    for r in rows:
        if r.get("status") == "success" and (str(r.get("task_id")), str(r.get("tactic"))) in false_pairs:
            r["status"] = "elab_error"
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dirs", nargs="+")
    ap.add_argument("--pilot-waves-root")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    reports: dict[str, Any] = {}
    if args.pilot_waves_root:
        reports["pilot"] = recount_pilot_layout(args.pilot_waves_root)
    for d in (args.run_dirs or []):
        reports[str(d)] = recount_run(d)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(reports, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    for d, rep in reports.items():
        print(json.dumps({
            "run": d, "success_rows": rep["n_success_rows"],
            "false_rows": rep["n_false_success_rows"],
            "unrangeable": rep.get("n_unrangeable_rows"),
            "claimed_tasks": len(rep.get("claimed_tasks", [])) or None,
            "true_tasks": len(rep.get("true_tasks", [])) or None,
            "false_pairs": rep.get("n_false_pairs"),
        }))
    return 0


__all__ = [
    "SCHEMA_LABEL_AUDIT",
    "apply_corrected_labels",
    "load_false_pairs",
    "recount_pilot_layout",
    "recount_rows",
    "recount_run",
]

if __name__ == "__main__":
    raise SystemExit(main())
