"""M1: reuse-rate ladder over cache-key gauges (preregistered in
docs/experiments/m1_reuse_ladder.md — thresholds frozen there).

Parses residual goal states out of partial-status pilot rows and measures
within-/inter-theorem key collision rates at four gauges (raw, text-alpha,
goal-only, goal+support-proxy). Text-level canonicalization only; the exact
rungs (kernel alpha, proof-term support) are M2 riders on kernel_rpc.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..lean.state_parser import LeanMessageParser
from ..schemas import read_jsonl

SCHEMA_REUSE_LADDER = "lean-rgc-m1-reuse-ladder-v97.0"

_RUNGS = ("K0_raw", "K1_alpha", "K2_goal_only", "K3_goal_support")

# Identifier-ish token incl. primes, subscripts, inaccessible markers.
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'₀-₉✝⁰¹²³⁴⁵⁶⁷⁸⁹]*")
_NUMERIC_TOKEN_RE = re.compile(r"^(?:\d+|[+\-*/^=()<>{}\[\],.]|le|lt|ge|gt|≤|≥|≠)$")


def _boundary_sub(text: str, mapping: dict[str, str]) -> str:
    """Replace whole identifier occurrences per mapping."""
    if not mapping:
        return text
    def repl(m: re.Match) -> str:
        return mapping.get(m.group(0), m.group(0))
    return _NAME_RE.sub(repl, text)


def _split_hyp(line: str) -> tuple[list[str], str] | None:
    """'a b : T' -> (['a','b'], 'T'); None if not a hypothesis line."""
    if ":" not in line:
        return None
    names_part, _, type_part = line.partition(":")
    names = names_part.strip().split()
    if not names or not all(_NAME_RE.fullmatch(n) for n in names):
        return None
    return names, type_part.strip()


def parse_goal(hypotheses: list[str], target: str) -> dict[str, Any]:
    hyps: list[tuple[str, str]] = []
    for line in hypotheses:
        parsed = _split_hyp(line)
        if parsed is None:
            continue
        names, typ = parsed
        for n in names:
            hyps.append((n, typ))
    return {"hyps": hyps, "target": target.strip()}


# ---------------- gauges ----------------

def key_k0(raw_block: str) -> str:
    return raw_block.strip()


def key_k1(goal: dict[str, Any]) -> str:
    """Rename hypothesis names in order of appearance; sort hyps by
    canonical type. Text-level alpha approximation."""
    mapping = {name: f"v{i}" for i, (name, _) in enumerate(goal["hyps"])}
    canon_hyps = sorted(_boundary_sub(t, mapping) for _, t in goal["hyps"])
    target = _boundary_sub(goal["target"], mapping)
    return " ; ".join(canon_hyps) + " ⊢ " + target


def _target_order_mapping(goal: dict[str, Any]) -> dict[str, str]:
    hyp_names = {n for n, _ in goal["hyps"]}
    mapping: dict[str, str] = {}
    for tok in _NAME_RE.findall(goal["target"]):
        if tok in hyp_names and tok not in mapping:
            mapping[tok] = f"v{len(mapping)}"
    return mapping


def key_k2(goal: dict[str, Any]) -> str:
    return _boundary_sub(goal["target"], _target_order_mapping(goal))


def _dependency_closure(goal: dict[str, Any]) -> list[tuple[str, str]]:
    """Hypotheses reachable from the target through name occurrence."""
    by_name = {n: t for n, t in goal["hyps"]}
    seen: set[str] = set()
    frontier = [tok for tok in _NAME_RE.findall(goal["target"]) if tok in by_name]
    while frontier:
        n = frontier.pop()
        if n in seen:
            continue
        seen.add(n)
        for tok in _NAME_RE.findall(by_name[n]):
            if tok in by_name and tok not in seen:
                frontier.append(tok)
    return [(n, t) for n, t in goal["hyps"] if n in seen]


def key_k3(goal: dict[str, Any]) -> str:
    support = _dependency_closure(goal)
    mapping = _target_order_mapping(goal)
    for n, _ in support:
        if n not in mapping:
            mapping[n] = f"v{len(mapping)}"
    canon_support = sorted(_boundary_sub(t, mapping) for _, t in support)
    return " ; ".join(canon_support) + " ⊢ " + _boundary_sub(goal["target"], mapping)


def is_trivial_target(canon_target: str) -> bool:
    t = canon_target.strip()
    if t == "True":
        return True
    if "=" in t:
        lhs, _, rhs = t.partition("=")
        if lhs.strip() and lhs.strip() == rhs.strip():
            return True
    toks = _NAME_RE.findall(t) + re.findall(r"\d+|[+\-*/^=()<>]", t)
    text_toks = [x for x in re.split(r"\s+", t) if x]
    return bool(text_toks) and all(_NUMERIC_TOKEN_RE.match(x) for x in text_toks)


# ---------------- extraction ----------------

def extract_goal_instances(waves_root: str | Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    root = Path(waves_root)
    parser = LeanMessageParser()
    instances: list[dict[str, Any]] = []
    counts = {"partial_rows": 0, "rows_with_goals": 0, "rows_zero_goals": 0}
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for wave_dir in sorted(run_dir.glob("wave_*")):
            m = re.match(r"wave_(\d+)$", wave_dir.name)
            micro = wave_dir / "micro_audit.jsonl"
            if not m or not micro.exists():
                continue
            for r in read_jsonl(micro):
                if not isinstance(r, dict) or r.get("status") != "partial":
                    continue
                counts["partial_rows"] += 1
                text = str((r.get("after_state") or {}).get("goals_text") or "")
                if "⊢" not in text:
                    counts["rows_zero_goals"] += 1
                    continue
                goals = parser.extract_goals(text)
                if not goals:
                    counts["rows_zero_goals"] += 1
                    continue
                counts["rows_with_goals"] += 1
                for g in goals:
                    goal = parse_goal(list(g.hypotheses), g.target or "")
                    if not goal["target"]:
                        continue
                    instances.append({
                        "task_id": str(r.get("task_id") or ""),
                        "run": run_dir.name,
                        "wave": int(m.group(1)),
                        "raw": (g.raw if hasattr(g, "raw") else g.target) or "",
                        "goal": goal,
                    })
    return instances, counts


# ---------------- metrics ----------------

def _rates(instances: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    n = len(keys)
    by_key_tasks: dict[str, set[str]] = defaultdict(set)
    per_task_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for inst, k in zip(instances, keys):
        by_key_tasks[k].add(inst["task_id"])
        per_task_counts[inst["task_id"]][k] += 1
    dup = sum(cnt - len(ks) for cnt, ks in ((sum(v.values()), v) for v in per_task_counts.values()))
    inter = sum(1 for inst, k in zip(instances, keys) if len(by_key_tasks[k]) >= 2)
    return {
        "n_instances": n,
        "n_unique_keys": len(by_key_tasks),
        "within_theorem_dup_rate": dup / n if n else 0.0,
        "inter_theorem_rate": inter / n if n else 0.0,
        "n_inter_instances": inter,
        "n_keys_shared_across_tasks": sum(1 for ts in by_key_tasks.values() if len(ts) >= 2),
    }


def run_reuse_ladder(waves_root: str | Path) -> dict[str, Any]:
    instances, counts = extract_goal_instances(waves_root)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_REUSE_LADDER,
        "prereg": "docs/experiments/m1_reuse_ladder.md",
        "extraction": counts,
        "n_goal_instances": len(instances),
        "n_tasks": len({i["task_id"] for i in instances}),
        "rungs": {},
        "canonical_status": "m1_report_witness_not_canonical",
    }
    key_fns = {
        "K0_raw": lambda i: key_k0(i["raw"]),
        "K1_alpha": lambda i: key_k1(i["goal"]),
        "K2_goal_only": lambda i: key_k2(i["goal"]),
        "K3_goal_support": lambda i: key_k3(i["goal"]),
    }
    keys_by_rung: dict[str, list[str]] = {}
    for rung in _RUNGS:
        keys = [key_fns[rung](i) for i in instances]
        keys_by_rung[rung] = keys
        report["rungs"][rung] = _rates(instances, keys)

    # Squeeze check: trivial fraction of K3 inter-theorem hit instances.
    k3 = keys_by_rung["K3_goal_support"]
    by_key_tasks: dict[str, set[str]] = defaultdict(set)
    for inst, k in zip(instances, k3):
        by_key_tasks[k].add(inst["task_id"])
    inter_idx = [i for i, k in enumerate(k3) if len(by_key_tasks[k]) >= 2]
    trivial = sum(1 for i in inter_idx if is_trivial_target(key_k2(instances[i]["goal"])))
    report["squeeze_check"] = {
        "n_inter_instances_K3": len(inter_idx),
        "n_trivial": trivial,
        "trivial_fraction": trivial / len(inter_idx) if inter_idx else 0.0,
        "nontrivial_inter_theorem_rate": (len(inter_idx) - trivial) / len(instances) if instances else 0.0,
    }

    r3 = report["rungs"]["K3_goal_support"]
    degenerate = r3["inter_theorem_rate"] < 0.01 and r3["within_theorem_dup_rate"] < 0.10
    report["decision"] = "central_layer_degenerates" if degenerate else "central_layer_live"
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    report = run_reuse_ladder(args.waves_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
