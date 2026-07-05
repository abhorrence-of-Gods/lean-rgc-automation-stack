"""D3 Phase 1: verified-prefix salvage measurement (preregistered in
docs/experiments/d3_phase1_prefix_salvage.md — thresholds frozen there).

Column-augmented, boundary-snapped estimator of the verified-prefix
fraction f per failed/partial whole-script candidate, computed entirely
from stored micro_audit messages (the bulk pipeline stored raw
'file:line:col:' prefixes; block offsets are reconstructed from lean_file
grouping + file order + deterministic block sizes + the 'by'-column
anchor). Logic ported from the feasibility-workflow-validated prototype.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..schemas import read_jsonl, write_jsonl

SCHEMA_PREFIX_SALVAGE = "lean-rgc-d3-prefix-salvage-v97.0"

# Also matches the tagged 'error(lean.unknownIdentifier):' form that the
# storage-time _ERROR_RE missed (those lines were stored as continuations
# but carry their own location).
_ANYLOC_RE = re.compile(r"^([^\s:]+\.lean):(\d+):(\d+):\s*(error|warning)(\([^)]*\))?:\s*(.*)$")

# Run dirs whose bulk files died at line 1:0 on a missing module: no script
# ever elaborated, no prefix exists by construction.
BROKEN_RUN_PREFIXES = ("pilot_a0", "pilot_a1", "pilot_a2", "pilot2_a0", "pilot2_a1", "pilot2_a2", "sanity_a1")

_OPEN = set("([{⟨")
_CLOSE = set(")]}⟩")


def _sanitize_ident(x: str) -> str:
    # Pinned to the pilot-era bulk renderer (byte-identical to HEAD).
    y = re.sub(r"[^A-Za-z0-9_]", "_", x)
    y = re.sub(r"_+", "_", y).strip("_")
    if not y:
        y = "x"
    if y[0].isdigit():
        y = "x_" + y
    return y[:80].rstrip("_") or "x"


def _by_column(task_id: str, statement: str) -> int:
    """0-based codepoint column of 'by' on the rendered theorem line:
    'theorem rgc_bulk_<sanitized>_<hash10> : <stmt> := by'."""
    return 35 + len(_sanitize_ident(task_id)) + len(statement)


def tactic_boundaries(script: str) -> list[int]:
    """Char offsets that are valid resume points (end of a verified prefix):
    start; after top-level ';' (not '<;>'); BEFORE a top-level ',' (Lean3
    separator); after newline. Depth tracked over ([{⟨."""
    bs = [0]
    depth = 0
    for i, ch in enumerate(script):
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
        elif depth == 0:
            if ch == ";" and not (i > 0 and script[i - 1] == "<" and i + 1 < len(script) and script[i + 1] == ">"):
                bs.append(i + 1)
            elif ch == ",":
                bs.append(i)
            elif ch == "\n":
                bs.append(i + 1)
    return bs


def snap_fraction(script: str, k: int, col: int) -> tuple[float, int]:
    """Boundary-snapped fraction for an error on tactic line k (1-based
    within the script) at stored column `col` (0-based, includes the
    2-space render indent). Returns (f, cut_offset)."""
    lines = script.splitlines() or [""]
    flat = "\n".join(lines)
    total = len(flat)
    if total <= 0:
        return 0.0, 0
    err = sum(len(l) + 1 for l in lines[: k - 1]) + min(max(0, col - 2), len(lines[k - 1]))
    cuts = [b for b in tactic_boundaries(flat) if b <= err]
    cut = max(cuts) if cuts else 0
    return len(flat[:cut].rstrip()) / total, cut


def _error_locs(messages: list[str]) -> list[tuple[int, int, str]]:
    out = []
    for m in messages:
        if not isinstance(m, str):
            continue
        mm = _ANYLOC_RE.match(m.strip())
        if mm and mm.group(4) == "error":
            out.append((int(mm.group(2)), int(mm.group(3)), mm.group(6)))
    return out


def _load_rows(waves_root: Path) -> list[dict[str, Any]]:
    rows = []
    for f in sorted(waves_root.glob("*/wave_*/micro_audit.jsonl")):
        run = f.parts[-3]
        if run.startswith(BROKEN_RUN_PREFIXES):
            continue
        for i, r in enumerate(read_jsonl(f)):
            if not isinstance(r, dict):
                continue
            rows.append({
                "run": run,
                "ord": i,
                "status": str(r.get("status") or ""),
                "task_id": str(r.get("task_id") or ""),
                "action_id": str(r.get("action_id") or ""),
                "statement": str(r.get("target") or ((r.get("after_state") or {}).get("target")) or ""),
                "tactic": str((r.get("action") or {}).get("tactic") or ""),
                "lean_file": str(r.get("lean_file") or ""),
                "messages": r.get("messages") or [],
                "cache_hit": bool((r.get("audit_flags") or {}).get("cache_hit")),
            })
    return rows


def _n_block_lines(row: dict[str, Any]) -> int:
    return max(1, len(row["tactic"].splitlines()) or 1)


def _reconstruct_chunks(rows: list[dict[str, Any]]) -> tuple[dict, dict, dict[str, int]]:
    """Per lean_file: member offsets (file order, fresh preferred) and the
    header height H from the 'by'-column anchor (fallback 7). Also returns
    anchor agreement counters for G0a."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["lean_file"]].append(r)
    chunk_off: dict[str, dict] = {}
    chunk_h: dict[str, int] = {}
    agree = {"anchored": 0, "disagree": 0}
    for lf, gr in groups.items():
        seen: dict[tuple, dict] = {}
        for r in gr:
            key = (r["task_id"], r["action_id"])
            if key not in seen or (seen[key]["cache_hit"] and not r["cache_hit"]):
                seen[key] = r
        members = sorted(seen.values(), key=lambda m: m["ord"])
        offs: dict[tuple, int] = {}
        acc = 0
        for m in members:
            offs[(m["task_id"], m["action_id"])] = acc
            acc += _n_block_lines(m) + 5
        chunk_off[lf] = offs
        votes: Counter = Counter()
        anchors: dict[tuple, int] = {}
        for m in members:
            pred = _by_column(m["task_id"], m["statement"])
            for (line, col, _msg) in _error_locs(m["messages"]):
                if col == pred:
                    anchors[(m["task_id"], m["action_id"])] = line
                    votes[line - offs[(m["task_id"], m["action_id"])] - 3] += 1
                    break
        h = votes.most_common(1)[0][0] if votes else 7
        chunk_h[lf] = h
        for key, line in anchors.items():
            agree["anchored"] += 1
            if h + offs[key] + 3 != line:
                agree["disagree"] += 1
    return chunk_off, chunk_h, agree


def estimate_candidates(waves_root: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Per-row f estimates plus diagnostics. Returns (records, diag)."""
    rows = _load_rows(Path(waves_root))
    chunk_off, chunk_h, agree = _reconstruct_chunks(rows)
    # Sibling-scan pool (2026-07-05 amendment, part of the original design
    # recipe): tagged-format error lines were stored under the PREVIOUS
    # plain error's line key at audit time, i.e. possibly in a NEIGHBOR
    # row's messages — so a row's first error may only exist chunk-wide.
    chunk_locs: dict[str, set[tuple[int, int, str]]] = defaultdict(set)
    for r in rows:
        for loc in _error_locs(r["messages"]):
            chunk_locs[r["lean_file"]].add(loc)
    records: list[dict[str, Any]] = []
    undefined: Counter = Counter()
    n_sibling_recovered = 0
    for r in rows:
        st = r["status"]
        if st == "success":
            continue
        offs = chunk_off[r["lean_file"]]
        off = offs.get((r["task_id"], r["action_id"]))
        script = "\n".join(r["tactic"].splitlines() or [""])
        if off is None or not script:
            undefined[(st, "no_member" if off is None else "empty_script")] += 1
            continue
        t_line = chunk_h[r["lean_file"]] + off + 3
        n = _n_block_lines(r)
        pred = _by_column(r["task_id"], r["statement"])
        locs = _error_locs(r["messages"])

        def _in_block(cands):
            return [
                (line, col, msg) for (line, col, msg) in cands
                if t_line - 1 <= line <= t_line + n
                and not (line == t_line and col == pred and "unsolved goal" in msg.lower())
            ]

        in_block = _in_block(locs)
        if not in_block:
            if st == "partial" and any(line == t_line for (line, _c, _m) in locs):
                records.append({**_key(r), "f": 1.0, "klass": "complete_unsolved", "cut": len(script), "prefix": script})
                continue
            in_block = _in_block(chunk_locs[r["lean_file"]])
            if in_block:
                n_sibling_recovered += 1
            else:
                undefined[(st, "locs_all_outside_block" if locs else "no_locs")] += 1
                continue
        line, col, _msg = min(in_block, key=lambda x: (x[0], x[1]))
        k = line - t_line
        if k <= 0:
            records.append({**_key(r), "f": 0.0, "klass": "err_pre_tactic", "cut": 0, "prefix": ""})
            continue
        f, cut = snap_fraction(script, k, col)
        records.append({**_key(r), "f": f, "klass": "err_tactic", "cut": cut, "prefix": script[:cut].rstrip()})
    diag = {
        "n_rows_loaded": len(rows),
        "anchor_agreement": agree,
        "undefined": {f"{s}:{w}": c for (s, w), c in sorted(undefined.items())},
        "n_undefined": sum(undefined.values()),
        "n_sibling_recovered": n_sibling_recovered,
    }
    return records, diag


def _key(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": r["run"], "status": r["status"], "task_id": r["task_id"],
        "action_id": r["action_id"], "statement": r["statement"], "tactic": r["tactic"],
        "cache_hit": r["cache_hit"],
    }


def _summary(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0}
    s = sorted(vals)
    return {
        "n": len(s),
        "median": statistics.median(s),
        "mean": statistics.fmean(s),
        "share_f0": sum(v == 0 for v in s) / len(s),
        "share_ge_05": sum(v >= 0.5 for v in s) / len(s),
        "share_f1": sum(v == 1.0 for v in s) / len(s),
    }


def run_prefix_salvage(waves_root: str | Path) -> dict[str, Any]:
    records, diag = estimate_candidates(waves_root)
    # Dedupe (task_id, tactic), fresh preferred.
    dedup: dict[tuple, dict] = {}
    for rec in records:
        key = (rec["task_id"], rec["tactic"])
        if key not in dedup or (dedup[key]["cache_hit"] and not rec["cache_hit"]):
            dedup[key] = rec
    dvals = [r["f"] for r in dedup.values()]
    nonzero = [v for v in dvals if v > 0]
    n_defined = len(dedup)
    n_pool = n_defined + diag["n_undefined"]
    imputed = dvals + [0.0] * diag["n_undefined"]

    ded = _summary(dvals)
    agree = diag["anchor_agreement"]
    g0a = (1 - agree["disagree"] / agree["anchored"]) >= 0.99 if agree["anchored"] else False
    g0b = (n_defined / n_pool) >= 0.95 if n_pool else False
    g1 = ded.get("median", 0.0) >= 0.5
    g2 = ded.get("share_ge_05", 0.0) >= 0.25 and (statistics.median(nonzero) if nonzero else 0.0) >= 0.5
    g3 = ded.get("share_f1", 0.0) >= 0.15
    return {
        "schema_version": SCHEMA_PREFIX_SALVAGE,
        "prereg": "docs/experiments/d3_phase1_prefix_salvage.md",
        "diagnostics": diag,
        "deduped": ded,
        "median_over_nonzero": statistics.median(nonzero) if nonzero else 0.0,
        "sensitivity": {
            "imputed_f0": _summary(imputed),
            "replay_weighted": _summary([r["f"] for r in records]),
        },
        "gates": {
            "G0a_anchor_agreement": g0a,
            "G0b_coverage": g0b,
            "G0c_calibration": "pending_pod_probe",
            "G1_full_license": g1,
            "G2_partial_license": g2,
            "G3_continuation_arm": g3,
        },
        "canonical_status": "d3_phase1_report_witness_not_canonical",
    }


def build_calibration_sample(
    waves_root: str | Path,
    out_path: str | Path,
    *,
    n_per_status: int = 20,
    seed: int = 0,
) -> dict[str, Any]:
    """Stratified sample of candidates with 0 < f < 1 for the G0c
    prefix+sorry pod probe."""
    import random

    records, _diag = estimate_candidates(waves_root)
    dedup: dict[tuple, dict] = {}
    for rec in records:
        key = (rec["task_id"], rec["tactic"])
        if key not in dedup or (dedup[key]["cache_hit"] and not rec["cache_hit"]):
            dedup[key] = rec
    rng = random.Random(seed)
    sample = []
    for status in ("partial", "fail", "elab_error"):
        pool = [r for r in dedup.values() if r["status"] == status and 0 < r["f"] < 1 and r["prefix"]]
        rng.shuffle(pool)
        sample.extend(pool[:n_per_status])
    out_rows = [
        {
            "task_id": r["task_id"],
            "statement": r["statement"],
            "status": r["status"],
            "f_est": r["f"],
            "prefix": r["prefix"],
            "probe_tactic": r["prefix"] + "\nsorry",
        }
        for r in sample
    ]
    write_jsonl(out_path, out_rows)
    return {"n_sample": len(out_rows), "out": str(out_path)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--calibration-out")
    args = ap.parse_args(argv)
    report = run_prefix_salvage(args.waves_root)
    if args.calibration_out:
        report["calibration_sample"] = build_calibration_sample(args.waves_root, args.calibration_out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("deduped", "median_over_nonzero", "gates")}, indent=2, ensure_ascii=False))
    return 0


__all__ = [
    "SCHEMA_PREFIX_SALVAGE",
    "build_calibration_sample",
    "estimate_candidates",
    "run_prefix_salvage",
    "snap_fraction",
    "tactic_boundaries",
]

if __name__ == "__main__":
    raise SystemExit(main())
