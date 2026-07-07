"""S'1c instrument 4: equal-capacity memory race on linked pairs.

Registered reopening of the branch-(b) question (S'1 Amendment d).
Verdict-bearing only if linked-pair count >= 120. Both arms add exactly
6 dims to the base Z; effective dof reported.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from s_prime_1c_estimators import FiberRidge, SweepModel, dedup_indices, leakage_gram
from s_prime_1c_run import build_corpus, head_symbol

SELECTED_HEADS = ["opaque", "Prime", "Eq", "mem", "le"]  # from the Schur run
SELECTED_CONST = "Finset.Icc"


def main():
    rows, keys, w = build_corpus()
    keep = dedup_indices(keys)
    keys_d = [keys[i] for i in keep]
    Z = np.vstack([r["z"] for r in rows])[:, keep] * w[keep]
    R = np.vstack([r["resp"] for r in rows])[:, keep] * w[keep]
    fibers = [r["fiber"] for r in rows]
    chains = [r["chain"] for r in rows]
    d_norm = np.linalg.norm(Z, axis=1)
    sw = SweepModel().fit(d_norm, R, fibers)
    R_cm = sw.residual(d_norm, R, fibers)
    gate_dims = [i for i, k in enumerate(keys_d) if not k.startswith("carrier.")]

    # linked pairs: consecutive rows within the same chain
    linked, prev_idx = [], {}
    for i, r in enumerate(rows):
        c = r["chain"]
        if c in prev_idx:
            linked.append((prev_idx[c], i))
        prev_idx[c] = i
    n_linked = len(linked)
    idx = np.array([j for _, j in linked])
    prev = np.array([i for i, _ in linked])
    print(f"linked pairs: {n_linked} (verdict-bearing: {n_linked >= 120})")

    Zl, Rl = Z[idx], R_cm[idx]
    fl = [fibers[j] for j in idx]
    cl = [chains[j] for j in idx]

    def trace_of(Zarm):
        fr = FiberRidge()
        resid, mask = fr.heldout_residuals(Zarm, Rl, fl, cl)
        return leakage_gram(resid[:, gate_dims], mask)["trace"]

    base = trace_of(Zl)

    # reader arm: the 6 features selected by the Schur run
    heads = [head_symbol((rows[j]["before_text"] or "").split("\n")[0]) for j in idx]
    feats_r = [np.array([1.0 if h == s else 0.0 for h in heads]) for s in SELECTED_HEADS]
    feats_r.append(np.array([1.0 if SELECTED_CONST in (rows[j]["before_text"] or "") else 0.0 for j in idx]))
    Z_reader = np.hstack([Zl] + [f[:, None] for f in feats_r])

    # memory arm (equal 6 added dims): prev fiber-class onehot (top-5 by
    # linked-pair frequency) + prev co-moving response on the top leakage
    # eigendirection
    fr_all = FiberRidge()
    resid_all, mask_all = fr_all.heldout_residuals(Z, R_cm, fibers, chains)
    g = leakage_gram(resid_all[:, gate_dims], mask_all)
    eig1 = np.zeros(Z.shape[1]); eig1[gate_dims] = g["evecs"][:, 0]
    prev_fibers = [fibers[i] for i in prev]
    top5 = [c for c, _ in Counter(prev_fibers).most_common(5)]
    feats_m = [np.array([1.0 if pf == c else 0.0 for pf in prev_fibers]) for c in top5]
    feats_m.append(R_cm[prev] @ eig1)
    Z_mem = np.hstack([Zl] + [f[:, None] for f in feats_m])

    t_reader, t_mem = trace_of(Z_reader), trace_of(Z_mem)
    red_r = 1 - t_reader / max(base, 1e-12)
    red_m = 1 - t_mem / max(base, 1e-12)
    report = {
        "n_linked_pairs": n_linked, "verdict_bearing": bool(n_linked >= 120),
        "base_trace": round(base, 4),
        "reader_arm": {"added_dims": 6, "trace": round(t_reader, 4), "reduction": round(float(red_r), 4)},
        "memory_arm": {"added_dims": 6, "trace": round(t_mem, 4), "reduction": round(float(red_m), 4)},
        "memory_wins": bool(red_m >= 0.30 and red_m > red_r),
        "verdict": ("NON-MARKOV-COMPRESSION" if (n_linked >= 120 and red_m >= 0.30 and red_m > red_r)
                    else "NO-MEMORY-WIN" if n_linked >= 120 else "DESCRIPTIVE-ONLY"),
    }
    (ROOT / "runs/s_prime_1c/memory_control.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
