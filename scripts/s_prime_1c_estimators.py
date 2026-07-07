"""S'1c estimator stack (frozen instruments 1-3) + OU litmus.

Run as __main__ to execute the LITMUS (must pass before any
real-corpus number is read; prereg requirement).

Derivation note (closed-form ground truth, committed as code per the
frozen prereg — no external-document dependency):

  Synthetic model. For fiber c with n_c rows: z ~ N(0, I_p);
  resp = W_c z + beta_c * ||z|| * s_dir + eps,  eps ~ N(0, Sigma_c).
  - Conditional drift curvature of the TRUE model class:
      V_c = Cov(resp | z, fiber=c) = Sigma_c  (closed form).
  - Pooled leakage Gram of the true class = sum_c pi_c Sigma_c, whose
    trace and eigenvectors are computable directly from the chosen
    Sigma_c (ground truth for instrument 2).
  - Sweep: the rank-1 term beta_c ||z|| s_dir is exactly instrument
    1's model class; the co-moving residual of the true model removes
    it identically (ground truth for instrument 1).
  - Schur value of a feature u that linearly explains part of eps
    (eps = u * g^T + eps'): adding u reduces the residual covariance
    by g g^T Var(u), so the trace reduction share is
    tr(g g^T Var(u)) / tr(Sigma)  (ground truth for instrument 3).

Litmus variants (frozen): (A) recovery at the EMPIRICAL fiber-size
long tail; (B) signal-sweep collinearity — co-moving residual must
retain >= 80% of the collinear signal's correlation with an outcome in
the raw frame; (C) degeneracy — singleton-dominated fibers must be
EXCLUDED by the degeneracy clause, not shipped as zero residuals.
Tolerances: scalar traces/shares rel. bias < 10%; principal angle of
top-3 pooled eigendirections <= 15 deg.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

N_MIN = 8
RIDGE = 1.0
FIBER_HEADS = ["intro", "intros", "apply", "exact", "rw", "simp", "norm_num",
               "ring", "linarith", "nlinarith", "field_simp", "have", "cases",
               "constructor", "refine", "omega"]

# exact duplicate coordinate pairs in the 34-dim defect vector (keep first)
DUP_DROP = ["search.proof_term_growth_proxy", "carrier.constructor_branch_debt"]


def fiber_of(tactic: str) -> str:
    head = (tactic or "").strip().split()[0].rstrip(";,") if (tactic or "").strip() else "other"
    head = head.split("[")[0]
    return head if head in FIBER_HEADS else "other"


def dedup_indices(keys: list[str]) -> list[int]:
    return [i for i, k in enumerate(keys) if k not in DUP_DROP]


# ---------------------------------------------------------------- instrument 1
class SweepModel:
    """Rank-1 bulk flow: per-fiber scalar regression of the response's
    component along the fit-population mean-response direction on
    whitened ||D_before||. Pooled below N_MIN."""

    def fit(self, d_norm: np.ndarray, resp: np.ndarray, fibers: list[str]) -> "SweepModel":
        mean_resp = resp.mean(axis=0)
        nrm = float(np.linalg.norm(mean_resp))
        self.s_dir = mean_resp / nrm if nrm > 1e-12 else np.zeros(resp.shape[1])
        comp = resp @ self.s_dir
        x = d_norm
        self.beta_global = float((x * comp).sum() / max((x * x).sum(), 1e-12))
        self.beta_by_fiber = {}
        for c in set(fibers):
            idx = [i for i, f in enumerate(fibers) if f == c]
            n = len(idx)
            b = float((x[idx] * comp[idx]).sum() / max((x[idx] * x[idx]).sum(), 1e-12))
            w = n / (n + N_MIN)
            self.beta_by_fiber[c] = w * b + (1 - w) * self.beta_global
        return self

    def sweep_component(self, d_norm, fibers):
        beta = np.array([self.beta_by_fiber.get(c, self.beta_global) for c in fibers])
        return np.outer(beta * d_norm, self.s_dir)

    def residual(self, d_norm, resp, fibers):
        return resp - self.sweep_component(d_norm, fibers)


# ---------------------------------------------------------------- instrument 2
def _ridge_fit(Z, R, lam=RIDGE):
    p = Z.shape[1]
    A = Z.T @ Z + lam * np.eye(p)
    return np.linalg.solve(A, Z.T @ R)


class FiberRidge:
    """Per-fiber ridge E[resp | fiber, z] with hierarchical shrinkage to
    the global model below N_MIN; held-out residuals via grouped k-fold
    (by chain); degeneracy clause vs the global-mean predictor."""

    def __init__(self, n_folds: int = 5, seed: int = 20260707):
        self.n_folds = n_folds
        self.seed = seed

    def heldout_residuals(self, Z, R, fibers, chains):
        n = len(R)
        rng = np.random.default_rng(self.seed)
        uniq_chains = sorted(set(chains))
        rng.shuffle(uniq_chains)
        fold_of_chain = {c: i % self.n_folds for i, c in enumerate(uniq_chains)}
        folds = np.array([fold_of_chain[c] for c in chains])
        resid = np.zeros_like(R)
        pred_gmean = np.zeros_like(R)
        deflate = np.ones(n)
        for k in range(self.n_folds):
            tr, te = folds != k, folds == k
            if te.sum() == 0:
                continue
            Zb = np.hstack([Z[tr], np.ones((tr.sum(), 1))])
            Wg = _ridge_fit(Zb, R[tr])
            Ag = Zb.T @ Zb + RIDGE * np.eye(Zb.shape[1])
            p_eff_g = float(np.trace(np.linalg.solve(Ag, Zb.T @ Zb)))
            gmean = R[tr].mean(axis=0)
            for c in set(np.array(fibers)[te]):
                trc = tr & (np.array(fibers) == c)
                tec = te & (np.array(fibers) == c)
                Zte = np.hstack([Z[tec], np.ones((tec.sum(), 1))])
                pred_g = Zte @ Wg
                nc = int(trc.sum())
                if nc >= 2:
                    Zc = np.hstack([Z[trc], np.ones((nc, 1))])
                    Wc = _ridge_fit(Zc, R[trc])
                    Ac = Zc.T @ Zc + RIDGE * np.eye(Zc.shape[1])
                    p_eff_c = float(np.trace(np.linalg.solve(Ac, Zc.T @ Zc)))
                    w = nc / (nc + N_MIN)
                    pred = w * (Zte @ Wc) + (1 - w) * pred_g
                    infl = 1.0 + (w * w) * p_eff_c / max(nc, 1) + ((1 - w) ** 2) * p_eff_g / max(tr.sum(), 1)
                else:
                    pred = pred_g
                    infl = 1.0 + p_eff_g / max(tr.sum(), 1)
                resid[tec] = R[tec] - pred
                # leverage deflation: held-out residual second moments
                # overshoot the noise covariance by ~(1 + p_eff/n_train);
                # registered model-derived correction, not a tuned value.
                deflate[tec] = 1.0 / np.sqrt(infl)
                pred_gmean[tec] = gmean
        resid = resid * deflate[:, None]
        # degeneracy clause: fiber enters ONLY if its model beats the
        # global-mean predictor held-out
        accepted, excluded_rows = [], 0
        fib = np.array(fibers)
        for c in set(fibers):
            m = fib == c
            mse_model = float((resid[m] ** 2).sum())
            mse_gmean = float(((R[m] - pred_gmean[m]) ** 2).sum())
            if mse_model < mse_gmean:
                accepted.append(c)
            else:
                excluded_rows += int(m.sum())
        mask = np.isin(fib, accepted)
        self.accepted_fibers = sorted(accepted)
        self.excluded_row_share = excluded_rows / max(n, 1)
        self.folds = folds
        return resid, mask


def leakage_gram(resid: np.ndarray, mask: np.ndarray, folds: np.ndarray | None = None):
    X = resid[mask]
    Sigma = X.T @ X / max(len(X), 1)
    evals, evecs = np.linalg.eigh(Sigma)
    order = np.argsort(evals)[::-1]
    out = {"trace": float(np.trace(Sigma)), "evals": evals[order],
           "evecs": evecs[:, order], "n_rows": int(len(X))}
    if folds is not None:
        angles = []
        for k in set(folds[mask]):
            Xk = resid[mask & (folds == k)]
            if len(Xk) < 10:
                continue
            Sk = Xk.T @ Xk / len(Xk)
            _, Vk = np.linalg.eigh(Sk)
            Vk = Vk[:, ::-1][:, :3]
            V = out["evecs"][:, :3]
            s = np.linalg.svd(V.T @ Vk, compute_uv=False)
            angles.append(float(np.degrees(np.arccos(np.clip(s.min(), 0, 1)))))
        out["fold_max_principal_angle_deg"] = max(angles) if angles else None
    return out


# ---------------------------------------------------------------- instrument 3
def schur_reduction(Z_base, Z_ext, R, fibers, chains, gate_dims):
    """Relative held-out trace-leakage reduction from extending z,
    on the gating coordinate subset; plus spread stats."""
    fr = FiberRidge()
    r0, m0 = fr.heldout_residuals(Z_base, R, fibers, chains)
    g0 = leakage_gram(r0[:, gate_dims], m0)
    fr2 = FiberRidge()
    r1, m1 = fr2.heldout_residuals(Z_ext, R, fibers, chains)
    m = m0 & m1  # same-row comparison
    g_base = leakage_gram(r0[:, gate_dims], m)
    g_ext = leakage_gram(r1[:, gate_dims], m)
    red = 1.0 - g_ext["trace"] / max(g_base["trace"], 1e-12)
    # spread: per-eigendirection (of base) reduction shares
    V = g_base["evecs"][:, :5]
    per_dir = []
    for j in range(V.shape[1]):
        v = V[:, j]
        b = float(v @ (r0[m][:, gate_dims].T @ r0[m][:, gate_dims] / m.sum()) @ v)
        e = float(v @ (r1[m][:, gate_dims].T @ r1[m][:, gate_dims] / m.sum()) @ v)
        per_dir.append(max(b - e, 0.0))
    tot = sum(per_dir) or 1e-12
    shares = [d / tot for d in per_dir]
    return {"reduction": float(red), "per_direction_shares": shares,
            "n_directions_hit": int(sum(s > 0.05 for s in shares)),
            "max_direction_share": float(max(shares)),
            "base_trace": g_base["trace"], "ext_trace": g_ext["trace"]}


# ------------------------------------------------------------------- litmus
def _make_synthetic(rng, fiber_sizes, p=6, d=10, sweep_beta=2.0, collinear=0.0):
    """Ground-truth generator per the derivation note. Returns data plus
    closed-form truth. `collinear`: fraction of the outcome-bearing
    signal direction lying along the sweep direction."""
    s_dir = np.zeros(d); s_dir[0] = 1.0
    sig_dir = np.zeros(d)
    sig_dir[0] = np.sqrt(collinear)
    sig_dir[1] = np.sqrt(1 - collinear)
    # shared low-rank leakage structure with SEPARATED eigenvalues —
    # eigendirection recovery is only well-posed above the separation
    # margin, so the litmus plants identifiable directions (6, 4, 2)
    # over the ~1-level diagonal noise floor.
    U = np.zeros((d, 3)); U[3, 0] = U[4, 1] = U[5, 2] = 1.0
    lam_shared = np.array([6.0, 4.0, 2.0])
    Z, Rsp, fibers, chains, sig_comp = [], [], [], [], []
    Sigmas, weights = {}, {}
    for ci, n_c in enumerate(fiber_sizes):
        c = f"f{ci}"
        W = rng.normal(0, 0.5, (p, d))
        diagv = np.abs(rng.normal(1.0, 0.3, d))
        Sigmas[c] = np.diag(diagv ** 2) + U @ np.diag(lam_shared) @ U.T
        weights[c] = n_c
        z = rng.normal(0, 1, (n_c, p))
        znorm = np.linalg.norm(z, axis=1)
        eps = rng.normal(0, 1, (n_c, d)) * diagv
        eps = eps + rng.normal(0, 1, (n_c, 3)) * np.sqrt(lam_shared) @ U.T
        sig = rng.normal(0, 1, n_c)  # latent signal riding on sig_dir
        resp = z @ W + np.outer(sweep_beta * znorm, s_dir) + eps + np.outer(sig, sig_dir)
        Z.append(z); Rsp.append(resp)
        fibers += [c] * n_c
        chains += [f"{c}_{i}" for i in range(n_c)]
        sig_comp += list(sig)
    Z, Rsp = np.vstack(Z), np.vstack(Rsp)
    tot = sum(weights.values())
    Sigma_true = sum(w * S for (c, S), w in zip(Sigmas.items(), weights.values())) / tot
    Sigma_true = Sigma_true + np.outer(sig_dir, sig_dir)  # signal variance 1
    return {"Z": Z, "resp": Rsp, "fibers": fibers, "chains": chains,
            "d_norm": np.linalg.norm(Z, axis=1), "Sigma_true": Sigma_true,
            "sig": np.array(sig_comp), "sig_dir": sig_dir, "s_dir": s_dir}


def run_litmus() -> dict:
    rng = np.random.default_rng(20260707)
    report = {}

    # empirical fiber-size distribution at the FROZEN granularity
    # (coarse tactic-head classes — the regime the estimator deploys in)
    trans_path = Path(__file__).resolve().parents[1] / "runs/s_prime_1/s1_stepwise_rerun2/stepwise_transitions.jsonl"
    if trans_path.exists():
        tac = [json.loads(l)["tactic"] for l in open(trans_path, encoding="utf-8")]
        sizes = sorted(Counter(fiber_of(t) for t in tac).values(), reverse=True)
    else:
        sizes = [239, 157, 133, 98, 75, 40, 39, 36, 34, 17, 15, 5, 3, 1]
    sizes4 = sizes  # deployed regime, unscaled

    # (A) recovery at the empirical distribution — FULL STACK in the
    # frozen instrument order: sweep first, ridge on co-moving residual
    data = _make_synthetic(rng, sizes4)
    sw_a = SweepModel().fit(data["d_norm"], data["resp"], data["fibers"])
    resp_cm = sw_a.residual(data["d_norm"], data["resp"], data["fibers"])
    fr = FiberRidge()
    resid, mask = fr.heldout_residuals(data["Z"], resp_cm, data["fibers"], data["chains"])
    g = leakage_gram(resid, mask, fr.folds)
    tr_true = float(np.trace(data["Sigma_true"]))
    bias = abs(g["trace"] - tr_true) / tr_true
    _, Vt = np.linalg.eigh(data["Sigma_true"])
    Vt = Vt[:, ::-1][:, :3]
    s = np.linalg.svd(Vt.T @ g["evecs"][:, :3], compute_uv=False)
    angle = float(np.degrees(np.arccos(np.clip(s.min(), 0, 1))))
    report["A_recovery"] = {"trace_rel_bias": round(float(bias), 4),
                            "top3_principal_angle_deg": round(angle, 2),
                            "excluded_row_share": round(fr.excluded_row_share, 4),
                            "pass": bool(bias < 0.10 and angle <= 15.0)}

    # (B) collinearity: sweeping must retain >= 80% of the collinear
    # signal's raw-frame correlation with an outcome
    datb = _make_synthetic(rng, sizes4, collinear=0.5)
    y = datb["sig"] + rng.normal(0, 0.5, len(datb["sig"]))
    sw = SweepModel().fit(datb["d_norm"], datb["resp"], datb["fibers"])
    resid_cm = sw.residual(datb["d_norm"], datb["resp"], datb["fibers"])
    raw_sig = datb["resp"] @ datb["sig_dir"]
    cm_sig = resid_cm @ datb["sig_dir"]
    c_raw = abs(np.corrcoef(raw_sig, y)[0, 1])
    c_cm = abs(np.corrcoef(cm_sig, y)[0, 1])
    report["B_collinearity"] = {"raw_corr": round(float(c_raw), 4),
                                 "comoving_corr": round(float(c_cm), 4),
                                 "retention": round(float(c_cm / max(c_raw, 1e-9)), 4),
                                 "pass": bool(c_cm / max(c_raw, 1e-9) >= 0.80)}

    # (C) degeneracy: singleton-dominated corpus -> excluded, not zeroed
    sizes_c = [2] * 10 + [1] * 300
    datc = _make_synthetic(rng, sizes_c)
    frc = FiberRidge()
    residc, maskc = frc.heldout_residuals(datc["Z"], datc["resp"], datc["fibers"], datc["chains"])
    zero_rows = int((np.abs(residc[maskc]).sum(axis=1) < 1e-9).sum())
    report["C_degeneracy"] = {"excluded_row_share": round(frc.excluded_row_share, 4),
                               "zero_residual_rows_shipped": zero_rows,
                               "pass": bool(zero_rows == 0)}

    # (D) Schur ground truth: a feature explaining a known eps component
    # (full stack order: sweep first, as deployed)
    datd = _make_synthetic(rng, sizes4)
    g_vec = np.zeros(10); g_vec[2] = 1.5
    u = rng.normal(0, 1, len(datd["Z"]))
    respd = datd["resp"] + np.outer(u, g_vec)
    sw_d = SweepModel().fit(datd["d_norm"], respd, datd["fibers"])
    respd_cm = sw_d.residual(datd["d_norm"], respd, datd["fibers"])
    Zb = datd["Z"]
    Ze = np.hstack([Zb, u[:, None]])
    gd = list(range(10))
    sr = schur_reduction(Zb, Ze, respd_cm, datd["fibers"], datd["chains"], gd)
    tr_base = float(np.trace(datd["Sigma_true"])) + float(g_vec @ g_vec)
    truth = float(g_vec @ g_vec) / tr_base
    bias_s = abs(sr["reduction"] - truth) / truth
    report["D_schur"] = {"estimated": round(sr["reduction"], 4), "truth": round(truth, 4),
                          "rel_bias": round(float(bias_s), 4), "pass": bool(bias_s < 0.10)}

    report["ALL_PASS"] = all(v["pass"] for k, v in report.items() if isinstance(v, dict))
    return report


if __name__ == "__main__":
    rep = run_litmus()
    print(json.dumps(rep, indent=1))
    sys.exit(0 if rep["ALL_PASS"] else 1)
