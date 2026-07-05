"""D1: retroactive twist-gate FPR analysis (preregistered in
docs/experiments/d1_twist_gate.md — thresholds are frozen there; this module
computes, it does not decide).

Estimator class (all arms identical for fairness): naive-Bayes log-lift with
count shrinkage — score(row) = base_logodds + sum_f lift(f), which is exactly
the factorized form log h_hat ~= b0 + sum log k_omega. Calibration: isotonic
(PAV) fit on training folds, applied out-of-fold.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from ..schemas import read_jsonl
from .stats_np import auc_score, ece_score, grouped_folds, pav_isotonic_apply, pav_isotonic_fit

SCHEMA_RETRO_FPR = "lean-rgc-retro-fpr-v97.0"

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*|\S")
_ARMS = ("T", "F", "R", "FR")


# ---------------- loading ----------------

def load_candidate_rows(waves_root: str | Path) -> list[dict[str, Any]]:
    """Flatten every */wave_*/micro_audit.jsonl under waves_root, joining
    boundary feedback_text via boundary_id."""
    root = Path(waves_root)
    out: list[dict[str, Any]] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        feedback: dict[str, str] = {}
        bpath = run_dir / "boundaries.jsonl"
        if bpath.exists():
            for b in read_jsonl(bpath):
                if isinstance(b, dict) and b.get("boundary_id"):
                    feedback[str(b["boundary_id"])] = str(b.get("feedback_text") or "")
        for wave_dir in sorted(run_dir.glob("wave_*")):
            m = re.match(r"wave_(\d+)$", wave_dir.name)
            if not m:
                continue
            micro = wave_dir / "micro_audit.jsonl"
            if not micro.exists():
                continue
            for r in read_jsonl(micro):
                if not isinstance(r, dict):
                    continue
                action = r.get("action") or {}
                meta = action.get("metadata") or {}
                db = r.get("defect_before") or {}
                bid = str(meta.get("boundary_id") or "")
                out.append({
                    "run": run_dir.name,
                    "wave": int(m.group(1)),
                    "task_id": str(r.get("task_id") or ""),
                    "status": str(r.get("status") or ""),
                    "tactic": str(action.get("tactic") or ""),
                    "boundary_id": bid,
                    "prompt_hash": str(meta.get("prompt_hash") or bid or "nohash"),
                    "flat": [float(v) for v in (db.get("flat") or [])],
                    "flat_keys": [str(k) for k in (db.get("flat_keys") or [])],
                    "goal_shape": ((db.get("quotient_meta") or {}).get("goal_shape") or {}),
                    "feedback_text": feedback.get(bid, ""),
                })
    return out


# ---------------- featurization ----------------

def _first_token(tactic: str) -> str:
    toks = _TOKEN_RE.findall(tactic.strip())
    return toks[0] if toks else "<empty>"


def features_for_row(row: dict[str, Any], arm: str) -> list[str]:
    feats: list[str] = []
    if arm in ("T", "F", "FR"):
        feats.append(f"tok:{_first_token(row['tactic'])}")
    if arm in ("F", "FR"):
        for k, v in zip(row["flat_keys"], row["flat"]):
            if k.startswith(("carrier.", "type.", "search.", "audit.")):
                if v > 0:
                    feats.append(f"d:{k}>0")
            elif k == "goal.num_goals":
                feats.append(f"d:num_goals={int(round(v))}")
            elif k == "goal.unsolved_goal_flag" and v > 0:
                feats.append(f"d:{k}")
        for k, v in row["goal_shape"].items():
            if isinstance(v, bool) and v:
                feats.append(f"gs:{k}")
    if arm in ("R", "FR"):
        for t in set(_TOKEN_RE.findall(row["tactic"])):
            feats.append(f"rw:{t}")
        for t in set(_TOKEN_RE.findall(row["feedback_text"])):
            feats.append(f"fb:{t}")
    return feats


# ---------------- NB log-lift model ----------------

class LogLiftModel:
    def __init__(self, shrinkage: float = 20.0):
        self.shrinkage = shrinkage
        self.base_rate = 0.5
        self.lift: dict[str, float] = {}

    def fit(self, feats: list[list[str]], y: np.ndarray) -> "LogLiftModel":
        p0 = float(np.clip(y.mean(), 1e-4, 1 - 1e-4))
        self.base_rate = p0
        succ: dict[str, float] = defaultdict(float)
        cnt: dict[str, float] = defaultdict(float)
        for fs, yi in zip(feats, y):
            for f in set(fs):
                succ[f] += float(yi)
                cnt[f] += 1.0
        s = self.shrinkage
        base_lo = math.log(p0 / (1 - p0))
        self.lift = {}
        for f, n in cnt.items():
            pf = (succ[f] + s * p0) / (n + s)
            pf = min(max(pf, 1e-4), 1 - 1e-4)
            self.lift[f] = math.log(pf / (1 - pf)) - base_lo
        return self

    def score(self, feats: list[list[str]]) -> np.ndarray:
        base_lo = math.log(self.base_rate / (1 - self.base_rate))
        out = np.full(len(feats), base_lo, dtype=float)
        for i, fs in enumerate(feats):
            out[i] += sum(self.lift.get(f, 0.0) for f in set(fs))
        return out


# ---------------- analysis ----------------

def _oof_scores(rows: list[dict[str, Any]], y: np.ndarray, arm: str, *, n_folds: int, seed: int, shrinkage: float) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-fold raw scores and isotonic-calibrated probabilities."""
    feats = [features_for_row(r, arm) for r in rows]
    folds = grouped_folds([r["task_id"] for r in rows], n_folds=n_folds, seed=seed)
    raw = np.zeros(len(rows))
    cal = np.zeros(len(rows))
    for k in range(n_folds):
        tr = folds != k
        te = folds == k
        if not te.any():
            continue
        model = LogLiftModel(shrinkage).fit([f for f, m in zip(feats, tr) if m], y[tr])
        tr_scores = model.score([f for f, m in zip(feats, tr) if m])
        thresholds, values = pav_isotonic_fit(tr_scores, y[tr])
        te_scores = model.score([f for f, m in zip(feats, te) if m])
        raw[te] = te_scores
        cal[te] = pav_isotonic_apply(thresholds, values, te_scores)
    return raw, cal


def _tau_sweep(y: np.ndarray, p: np.ndarray, taus: np.ndarray) -> list[dict[str, float]]:
    out = []
    n_succ = max(1, int(y.sum()))
    for tau in taus:
        pruned = p < tau
        out.append({
            "tau": float(tau),
            "fn": float((pruned & (y > 0)).sum() / n_succ),
            "savings": float(pruned.mean()),
        })
    return out


def _set_level_fn(rows: list[dict[str, Any]], y: np.ndarray, score: np.ndarray, k: int) -> float:
    """Fraction of positive candidate sets whose successes are ALL outside
    the top-k by score."""
    sets: dict[tuple, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        sets[(r["run"], r["wave"], r["boundary_id"])].append(i)
    n_pos = 0
    n_dropped = 0
    for idx in sets.values():
        idx_arr = np.array(idx)
        ys = y[idx_arr]
        if not ys.any():
            continue
        n_pos += 1
        top = idx_arr[np.argsort(-score[idx_arr], kind="mergesort")[:k]]
        if not y[top].any():
            n_dropped += 1
    return n_dropped / max(1, n_pos)


def _cluster_bootstrap(rows, y, p, stat_fn, *, n_boot: int, seed: int) -> tuple[float, float]:
    clusters: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        clusters[r["prompt_hash"]].append(i)
    keys = sorted(clusters)
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(keys), size=len(keys))
        idx = np.concatenate([np.array(clusters[keys[j]]) for j in pick])
        v = stat_fn(idx)
        if not math.isnan(v):
            stats.append(v)
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def run_retro_fpr(
    waves_root: str | Path,
    *,
    n_folds: int = 5,
    seed: int = 0,
    shrinkage: float = 20.0,
    n_boot: int = 1000,
    fn_budget: float = 0.05,
    savings_floor: float = 0.20,
    false_pairs: "set[tuple[str, str]] | None" = None,
) -> dict[str, Any]:
    rows = load_candidate_rows(waves_root)
    n_demoted = 0
    if false_pairs:
        from .label_audit import apply_corrected_labels

        n_demoted = apply_corrected_labels(rows, false_pairs)
    y = np.array([1.0 if r["status"] == "success" else 0.0 for r in rows])
    report: dict[str, Any] = {
        "schema_version": SCHEMA_RETRO_FPR,
        "prereg": "docs/experiments/d1_twist_gate.md",
        "n_rows": len(rows),
        "n_success": int(y.sum()),
        "n_labels_demoted": n_demoted,
        "seed": seed,
        "n_folds": n_folds,
        "shrinkage": shrinkage,
        "arms": {},
        "canonical_status": "retro_fpr_report_witness_not_canonical",
    }
    scores: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for arm in _ARMS:
        raw, cal = _oof_scores(rows, y, arm, n_folds=n_folds, seed=seed, shrinkage=shrinkage)
        scores[arm] = (raw, cal)
        report["arms"][arm] = {"auc": auc_score(y, raw)}

    raw_f, cal_f = scores["F"]
    taus = np.unique(np.round(np.linspace(0.0, 0.5, 101), 4))
    sweep = _tau_sweep(y, cal_f, taus)
    feasible = [s for s in sweep if s["fn"] <= fn_budget and s["savings"] >= savings_floor]
    best = max(feasible, key=lambda s: s["savings"]) if feasible else None
    report["tau_sweep"] = sweep[::5]
    report["c2_best_tau"] = best
    report["set_level_fn"] = {f"B{k}": _set_level_fn(rows, y, raw_f, k) for k in (1, 2, 3)}
    report["ece_F"] = ece_score(y, cal_f)

    # Bootstrap CIs (clustered by prompt_hash).
    report["ci"] = {}
    report["ci"]["auc_F"] = _cluster_bootstrap(
        rows, y, raw_f, lambda idx: auc_score(y[idx], raw_f[idx]), n_boot=n_boot, seed=seed)
    if best is not None:
        tau_star = best["tau"]
        def fn_at_tau(idx):
            yy = y[idx]
            if yy.sum() == 0:
                return float("nan")
            return float(((cal_f[idx] < tau_star) & (yy > 0)).sum() / yy.sum())
        report["ci"]["fn_at_tau_star"] = _cluster_bootstrap(rows, y, cal_f, fn_at_tau, n_boot=n_boot, seed=seed)

    # Sensitivity: drop partial rows.
    keep = np.array([r["status"] != "partial" for r in rows])
    rows_np = [r for r, m in zip(rows, keep) if m]
    y_np = y[keep]
    raw_np, cal_np = _oof_scores(rows_np, y_np, "F", n_folds=n_folds, seed=seed, shrinkage=shrinkage)
    report["sensitivity_no_partial"] = {"n_rows": len(rows_np), "auc_F": auc_score(y_np, raw_np)}

    # Frozen gates (decided values recorded; thresholds live in the prereg).
    auc_f = report["arms"]["F"]["auc"]
    auc_r = report["arms"]["R"]["auc"]
    report["gates"] = {
        "C1_auc_F_ge_0.70": bool(auc_f >= 0.70),
        "C2_exists_tau": bool(best is not None),
        "C3_ece_le_0.05": bool(report["ece_F"] <= 0.05),
        "C4_raw_within_2pt": bool(auc_r - auc_f <= 0.02),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--waves-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--false-pairs", help="label_audit JSON with false (task, tactic) pairs")
    args = ap.parse_args(argv)
    fp = None
    if args.false_pairs:
        from .label_audit import load_false_pairs

        fp = load_false_pairs(args.false_pairs)
    report = run_retro_fpr(args.waves_root, n_boot=args.n_boot, seed=args.seed, false_pairs=fp)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_rows", "n_success", "arms", "c2_best_tau", "set_level_fn", "ece_F", "gates")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
