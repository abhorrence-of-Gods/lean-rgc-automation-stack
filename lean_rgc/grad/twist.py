"""S0: unified twist — one log-linear core, three heads.

The D1-validated LogLiftModel promoted to the unified object the bridge
program identified: twist = PRM = value = difficulty are projections of
the same partition function, differing only in filtration.

- score_pre        E[accept | state, action]   (pre-audit; proposal ranking)
- score_optimistic normal-approx upper confidence of score_pre
                   (admissible side; pruning/ranking, NEVER a reward)
- state_value      E[accept | state]           (action-marginalized b(s):
                   RLOO control variate, difficulty key)
- score_post       adds response-delta features (post-audit PRM head;
                   search/rerank only)

Per the S6 prereg recursion clause, this is a ONE-LEVEL log-linear
object; no meta-twist is built here. Torch-free.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ..evals.retro_fpr import LogLiftModel, features_for_row, load_candidate_rows

SCHEMA_TWIST = "lean-rgc-twist-v99.0"


def state_features(row: dict[str, Any]) -> list[str]:
    """State-only features: the F arm minus every action-derived factor."""
    return [f for f in features_for_row(row, "F") if not f.startswith(("tok:", "rw:", "fb:"))]


def post_features(row: dict[str, Any]) -> list[str]:
    """Pre-audit features plus signed response-delta flags (needs audit)."""
    feats = features_for_row(row, "F")
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        for k, v in resp.items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv > 0:
                feats.append(f"rd:{k}+")
            elif fv < 0:
                feats.append(f"rd:{k}-")
    return feats


class OptimisticLogLift(LogLiftModel):
    """Per-feature upper-confidence lifts (normal approximation to the
    Beta posterior upper quantile). Optimism shrinks as counts grow, so
    the bound tightens with evidence and never loosens (S6/D1 clause)."""

    def __init__(self, shrinkage: float = 20.0, z: float = 1.2816):
        super().__init__(shrinkage)
        self.z = z

    def fit(self, feats: list[list[str]], y: np.ndarray) -> "OptimisticLogLift":
        super().fit(feats, y)
        # Recompute lifts at the upper quantile.
        from collections import defaultdict

        succ: dict[str, float] = defaultdict(float)
        cnt: dict[str, float] = defaultdict(float)
        for fs, yi in zip(feats, y):
            for f in set(fs):
                succ[f] += float(yi)
                cnt[f] += 1.0
        p0 = self.base_rate
        base_lo = math.log(p0 / (1 - p0))
        s = self.shrinkage
        for f, n in cnt.items():
            p = (succ[f] + s * p0) / (n + s)
            se = math.sqrt(max(p * (1 - p), 1e-6) / (n + s + 1))
            p_ub = min(max(p + self.z * se, 1e-4), 1 - 1e-4)
            self.lift[f] = math.log(p_ub / (1 - p_ub)) - base_lo
        return self


class FactorizedTwist:
    def __init__(self, shrinkage: float = 20.0, z: float = 1.2816):
        self.shrinkage = shrinkage
        self.z = z
        self._pre = LogLiftModel(shrinkage)
        self._opt = OptimisticLogLift(shrinkage, z)
        self._state = LogLiftModel(shrinkage)
        self._post = LogLiftModel(shrinkage)

    def fit(self, rows: list[dict[str, Any]]) -> "FactorizedTwist":
        y = np.array([1.0 if r.get("status") == "success" else 0.0 for r in rows])
        pre = [features_for_row(r, "F") for r in rows]
        self._pre.fit(pre, y)
        self._opt.fit(pre, y)
        self._state.fit([state_features(r) for r in rows], y)
        self._post.fit([post_features(r) for r in rows], y)
        return self

    # ---- heads ----
    def score_pre(self, rows: list[dict[str, Any]]) -> np.ndarray:
        return self._pre.score([features_for_row(r, "F") for r in rows])

    def score_optimistic(self, rows: list[dict[str, Any]]) -> np.ndarray:
        return self._opt.score([features_for_row(r, "F") for r in rows])

    def state_value(self, rows: list[dict[str, Any]]) -> np.ndarray:
        """Log-odds scale; action-invariant by construction."""
        return self._state.score([state_features(r) for r in rows])

    def score_post(self, rows: list[dict[str, Any]]) -> np.ndarray:
        return self._post.score([post_features(r) for r in rows])

    # ---- persistence ----
    def to_dict(self) -> dict[str, Any]:
        def dump(m: LogLiftModel) -> dict[str, Any]:
            return {"base_rate": m.base_rate, "lift": m.lift}

        return {
            "schema_version": SCHEMA_TWIST,
            "shrinkage": self.shrinkage,
            "z": self.z,
            "heads": {
                "pre": dump(self._pre),
                "optimistic": dump(self._opt),
                "state": dump(self._state),
                "post": dump(self._post),
            },
            "canonical_status": "twist_chart_witness_not_canonical",
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FactorizedTwist":
        tw = cls(shrinkage=float(d.get("shrinkage", 20.0)), z=float(d.get("z", 1.2816)))
        for name, model in (("pre", tw._pre), ("optimistic", tw._opt), ("state", tw._state), ("post", tw._post)):
            h = d["heads"][name]
            model.base_rate = float(h["base_rate"])
            model.lift = {str(k): float(v) for k, v in h["lift"].items()}
        return tw

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "FactorizedTwist":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def load_rows_multi(roots: list[str | Path]) -> list[dict[str, Any]]:
    """Accept both the pilot layout (root/*/wave_*/) and a bare run dir
    (root/wave_*/) such as an extracted G1 archive."""
    rows: list[dict[str, Any]] = []
    for root in roots:
        rp = Path(root)
        if any(rp.glob("wave_*/micro_audit.jsonl")):
            rows.extend(_load_bare_run(rp))
        else:
            rows.extend(load_candidate_rows(rp))
    return rows


def _load_bare_run(run_dir: Path) -> list[dict[str, Any]]:
    import re

    from ..schemas import read_jsonl

    out: list[dict[str, Any]] = []
    for wave_dir in sorted(run_dir.glob("wave_*")):
        m = re.match(r"wave_(\d+)$", wave_dir.name)
        micro = wave_dir / "micro_audit.jsonl"
        if not m or not micro.exists():
            continue
        for r in read_jsonl(micro):
            if not isinstance(r, dict):
                continue
            action = r.get("action") or {}
            db = r.get("defect_before") or {}
            out.append({
                "run": run_dir.name,
                "wave": int(m.group(1)),
                "task_id": str(r.get("task_id") or ""),
                "status": str(r.get("status") or ""),
                "tactic": str(action.get("tactic") or ""),
                "boundary_id": str((action.get("metadata") or {}).get("boundary_id") or ""),
                "prompt_hash": str((action.get("metadata") or {}).get("prompt_hash") or "nohash"),
                "flat": [float(v) for v in (db.get("flat") or [])],
                "flat_keys": [str(k) for k in (db.get("flat_keys") or [])],
                "goal_shape": ((db.get("quotient_meta") or {}).get("goal_shape") or {}),
                "feedback_text": "",
                "response": r.get("response") or {},
            })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rows = load_rows_multi(args.roots)
    tw = FactorizedTwist().fit(rows)
    tw.save(args.out)
    y = np.array([1.0 if r.get("status") == "success" else 0.0 for r in rows])
    from ..evals.stats_np import auc_score

    print(json.dumps({
        "n_rows": len(rows),
        "n_success": int(y.sum()),
        "in_sample_auc_pre": auc_score(y, tw.score_pre(rows)),
        "out": args.out,
    }, indent=2))
    return 0


__all__ = ["SCHEMA_TWIST", "FactorizedTwist", "OptimisticLogLift", "post_features", "state_features"]

if __name__ == "__main__":
    raise SystemExit(main())
