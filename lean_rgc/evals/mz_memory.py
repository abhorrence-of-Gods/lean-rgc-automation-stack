"""E-MZ: Mori-Zwanzig memory test on wave chains (preregistered in
docs/experiments/emz_memory.md — thresholds are frozen there).

Measures whether wave t-1 features improve prediction of the wave t+1
outcome beyond wave t features (predictive-Delta estimator with a
permutation null). Decides the existence/shape of v98 memory.py.
"""

from __future__ import annotations

import argparse
import json
import re
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from ..schemas import read_jsonl
from .stats_np import auc_score, grouped_folds, logistic_fit, logistic_predict

SCHEMA_EMZ = "lean-rgc-emz-memory-v97.0"

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_STATUSES = ("success", "partial", "fail", "elab_error", "unsafe", "timeout")
_TXT_DIM = 128


# ---------------- chain construction ----------------

def _wave_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    counts = {s: 0 for s in _STATUSES}
    da = np.zeros(34)
    resp = np.zeros(34)
    n_da = 0
    txt = np.zeros(_TXT_DIM)
    for r in rows:
        s = str(r.get("status") or "")
        if s in counts:
            counts[s] += 1
        flat = ((r.get("defect_after") or {}).get("flat") or [])
        if len(flat) == 34:
            da += np.array(flat, dtype=float)
            n_da += 1
        rf = r.get("response") or {}
        if isinstance(rf, dict):
            for i, k in enumerate(sorted(rf)):
                if i < 34:
                    try:
                        resp[i] += float(rf[k])
                    except (TypeError, ValueError):
                        pass
        for msg in (r.get("messages") or []):
            for t in _TOKEN_RE.findall(str(msg)):
                # zlib.crc32, not hash(): str hashing is per-process salted.
                txt[zlib.crc32(t.encode("utf-8")) % _TXT_DIM] += 1.0
    if n_da:
        da /= n_da
        resp /= max(1, n_da)
    typed = np.concatenate([
        np.array([n] + [counts[s] / max(1, n) for s in _STATUSES], dtype=float),
        da,
        resp,
    ])
    return {
        "typed": typed,
        "text": np.log1p(txt),
        "success": counts["success"] > 0,
    }


def build_chains(waves_root: str | Path) -> list[dict[str, Any]]:
    """One chain per (run, task_id): the per-wave outcome summaries."""
    root = Path(waves_root)
    chains: dict[tuple[str, str], dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for wave_dir in sorted(run_dir.glob("wave_*")):
            m = re.match(r"wave_(\d+)$", wave_dir.name)
            micro = wave_dir / "micro_audit.jsonl"
            if not m or not micro.exists():
                continue
            w = int(m.group(1))
            for r in read_jsonl(micro):
                if isinstance(r, dict) and r.get("task_id"):
                    chains[(run_dir.name, str(r["task_id"]))][w].append(r)
    out = []
    for (run, task_id), waves in sorted(chains.items()):
        idxs = sorted(waves)
        if idxs != list(range(len(idxs))):
            # Keep the contiguous prefix only: memory needs adjacency.
            contiguous = []
            for i, w in enumerate(idxs):
                if w == i:
                    contiguous.append(w)
                else:
                    break
            idxs = contiguous
        if len(idxs) < 2:
            continue
        out.append({
            "run": run,
            "task_id": task_id,
            "waves": [_wave_summary(waves[w]) for w in idxs],
        })
    return out


# ---------------- transitions ----------------

def _features(summary: dict[str, Any], arm: str) -> np.ndarray:
    if arm == "L34":
        return summary["typed"]
    if arm == "LTXT":
        return summary["text"]
    return np.concatenate([summary["typed"], summary["text"]])


def build_transitions(chains: list[dict[str, Any]], arm: str, *, order: int = 1) -> dict[str, Any]:
    """Transition t (t >= order+... ) predicting outcome at t+1.

    order=1: base [f_t], lag adds f_{t-1}   (needs chain length >= 3)
    order=2: base [f_t, f_{t-1}], lag adds f_{t-2}  (needs length >= 4)
    """
    Xb, Xl, y, groups, wave_idx = [], [], [], [], []
    for c in chains:
        ws = c["waves"]
        for t in range(order, len(ws) - 1):
            base = [np.array([t], dtype=float)] + [_features(ws[t - j], arm) for j in range(order)]
            lag = base + [_features(ws[t - order], arm)]
            Xb.append(np.concatenate(base))
            Xl.append(np.concatenate(lag))
            y.append(1.0 if ws[t + 1]["success"] else 0.0)
            groups.append(c["task_id"])
            wave_idx.append(t)
    return {
        "X_base": np.array(Xb) if Xb else np.zeros((0, 1)),
        "X_lag": np.array(Xl) if Xl else np.zeros((0, 1)),
        "y": np.array(y),
        "groups": groups,
        "wave_idx": np.array(wave_idx, dtype=int),
    }


def _oof_auc(X: np.ndarray, y: np.ndarray, groups: list[str], *, n_folds: int, seed: int, l2: float) -> float:
    folds = grouped_folds(groups, n_folds=n_folds, seed=seed)
    p = np.zeros(len(y))
    for k in range(n_folds):
        tr, te = folds != k, folds == k
        if not te.any() or len(set(y[tr])) < 2:
            continue
        mu = X[tr].mean(axis=0)
        sd = X[tr].std(axis=0)
        sd[sd < 1e-9] = 1.0
        w = logistic_fit((X[tr] - mu) / sd, y[tr], l2=l2)
        p[te] = logistic_predict(w, (X[te] - mu) / sd)
    return auc_score(y, p)


def memory_delta(chains: list[dict[str, Any]], arm: str, *, order: int = 1, n_folds: int = 5, seed: int = 0, l2: float = 1.0, n_perm: int = 200) -> dict[str, Any]:
    tr = build_transitions(chains, arm, order=order)
    y, groups = tr["y"], tr["groups"]
    n = len(y)
    if n < 20 or len(set(y.tolist())) < 2:
        return {"arm": arm, "order": order, "n_transitions": n, "delta_auc": float("nan"), "p_value": float("nan")}
    auc_base = _oof_auc(tr["X_base"], y, groups, n_folds=n_folds, seed=seed, l2=l2)
    auc_lag = _oof_auc(tr["X_lag"], y, groups, n_folds=n_folds, seed=seed, l2=l2)
    delta = auc_lag - auc_base
    # Permutation null: shuffle the lag block within wave_idx strata.
    d_base = tr["X_base"].shape[1]
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        Xp = tr["X_lag"].copy()
        for w in set(tr["wave_idx"].tolist()):
            idx = np.where(tr["wave_idx"] == w)[0]
            Xp[idx, d_base:] = Xp[rng.permutation(idx), d_base:]
        null.append(_oof_auc(Xp, y, groups, n_folds=n_folds, seed=seed, l2=l2) - auc_base)
    null_arr = np.array(null)
    p_value = float((null_arr >= delta).mean())
    return {
        "arm": arm,
        "order": order,
        "n_transitions": n,
        "n_positive": int(y.sum()),
        "auc_base": auc_base,
        "auc_lag": auc_lag,
        "delta_auc": float(delta),
        "p_value": p_value,
        "null_q95": float(np.percentile(null_arr, 95)),
    }


def run_emz(waves_root: str | Path, *, n_perm: int = 200, seed: int = 0, arms: list[str] | None = None) -> dict[str, Any]:
    chains = build_chains(waves_root)
    lengths = defaultdict(int)
    for c in chains:
        lengths[len(c["waves"])] += 1
    report: dict[str, Any] = {
        "schema_version": SCHEMA_EMZ,
        "prereg": "docs/experiments/emz_memory.md",
        "n_chains": len(chains),
        "chain_lengths": dict(sorted(lengths.items())),
        "seed": seed,
        "arms": {},
        "canonical_status": "emz_report_witness_not_canonical",
    }
    wanted = arms or ["L34", "LTXT", "BOTH", "T2_L34"]
    for arm in ("L34", "LTXT", "BOTH"):
        if arm in wanted:
            report["arms"][arm] = memory_delta(chains, arm, order=1, n_perm=n_perm, seed=seed)
    if "T2_L34" in wanted:
        report["arms"]["T2_L34"] = memory_delta(chains, "L34", order=2, n_perm=n_perm, seed=seed)
    if set(report["arms"]) != {"L34", "LTXT", "BOTH", "T2_L34"}:
        report["decision"] = "partial_arms_no_decision"
        report["text_lag_escape_clause"] = False
        return report

    d34 = report["arms"]["L34"]
    dtxt = report["arms"]["LTXT"]
    significant34 = d34["p_value"] <= 0.1 if not np.isnan(d34["delta_auc"]) else False
    if not significant34 or d34["delta_auc"] < 0.01:
        decision = "kill_memory_module"
    elif d34["delta_auc"] < 0.03:
        decision = "ema_port_only"
    else:
        decision = "learned_memory_justified"
    text_escape = (
        not np.isnan(dtxt["delta_auc"]) and dtxt["delta_auc"] >= 0.01 and dtxt["p_value"] <= 0.1
        and (np.isnan(d34["delta_auc"]) or d34["delta_auc"] < 0.01 or not significant34)
    )
    report["decision"] = decision
    report["text_lag_escape_clause"] = bool(text_escape)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--arms", nargs="+", choices=["L34", "LTXT", "BOTH", "T2_L34"])
    args = ap.parse_args(argv)
    report = run_emz(args.waves_root, n_perm=args.n_perm, seed=args.seed, arms=args.arms)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
