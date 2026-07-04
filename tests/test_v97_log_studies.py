"""D1 retro-FPR and E-MZ memory analyses: estimator sanity + end-to-end on synthetic runs."""

from __future__ import annotations

import numpy as np

from lean_rgc.evals.mz_memory import build_chains, memory_delta, run_emz
from lean_rgc.evals.retro_fpr import LogLiftModel, load_candidate_rows, run_retro_fpr
from lean_rgc.evals.stats_np import (
    auc_score,
    ece_score,
    grouped_folds,
    logistic_fit,
    logistic_predict,
    pav_isotonic_apply,
    pav_isotonic_fit,
)
from lean_rgc.schemas import write_jsonl


# ---------------- stats_np ----------------

def test_auc_perfect_and_random():
    y = np.array([0, 0, 1, 1])
    assert auc_score(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert auc_score(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert abs(auc_score(y, np.array([0.5, 0.5, 0.5, 0.5])) - 0.5) < 1e-9


def test_grouped_folds_never_split_a_group():
    groups = [f"g{i % 7}" for i in range(70)]
    folds = grouped_folds(groups, n_folds=3, seed=0)
    for g in set(groups):
        vals = {int(f) for gg, f in zip(groups, folds) if gg == g}
        assert len(vals) == 1


def test_isotonic_is_monotone_and_calibrates():
    rng = np.random.default_rng(0)
    s = rng.uniform(-3, 3, size=500)
    y = (rng.uniform(size=500) < 1 / (1 + np.exp(-s))).astype(float)
    thr, val = pav_isotonic_fit(s, y)
    assert (np.diff(val) >= -1e-12).all()
    p = pav_isotonic_apply(thr, val, s)
    assert ece_score(y, p) < 0.08


def test_logistic_separates():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 3))
    y = (X[:, 0] + 0.5 * X[:, 1] > 0).astype(float)
    w = logistic_fit(X, y, l2=0.1)
    p = logistic_predict(w, X)
    assert auc_score(y, p) > 0.95


def test_loglift_ranks_by_token_rate():
    feats = [["tok:good"]] * 10 + [["tok:bad"]] * 10
    y = np.array([1.0] * 8 + [0.0] * 2 + [0.0] * 10)
    m = LogLiftModel(shrinkage=1.0).fit(feats, y)
    s = m.score([["tok:good"], ["tok:bad"], ["tok:unseen"]])
    assert s[0] > s[2] > s[1]


# ---------------- synthetic run dirs ----------------

def _make_waves_root(tmp_path, *, memory: bool, n_tasks: int = 24, n_waves: int = 4, seed: int = 0):
    """Synthetic pilot layout.

    memory=False: success is token-driven (the retro-FPR signal) and the
    chain is Markov in the wave features.
    memory=True: a fresh latent is REVEALED in wave w's defect_after and
    determines success two waves later (wave w+2) — visible to the lag
    features f_{t-1}, invisible to f_t, and never leaked through wave-t
    status counts. This is genuine non-Markov structure.
    """
    rng = np.random.default_rng(seed)
    root = tmp_path / "waves"
    run = root / "runA"
    boundaries = []
    rows_by_wave: dict[int, list[dict]] = {w: [] for w in range(n_waves)}
    keys = [f"k{i}" for i in range(34)]
    for ti in range(n_tasks):
        task = f"task{ti}"
        hidden = [float(rng.uniform()) for _ in range(n_waves)]
        for w in range(n_waves):
            bid = f"pb_{task}_w{w}"
            boundaries.append({"boundary_id": bid, "task_id": task, "feedback_text": f"err_w{w}" if w else "", "prompt_hash": f"ph_{task}_{w}"})
            for j in range(4):
                good = rng.uniform() < 0.5
                if memory:
                    p = 0.4 if w < 2 else (0.75 if hidden[w - 2] > 0.5 else 0.05)
                else:
                    p = 0.9 if good else 0.02
                flat_after = [hidden[w]] * 34 if memory else [0.0] * 34
                rows_by_wave[w].append({
                    "task_id": task,
                    "status": "success" if rng.uniform() < p else "fail",
                    "action": {"tactic": ("ring_nf x" if good else "sorry_free x"), "metadata": {"boundary_id": bid, "prompt_hash": f"ph_{task}_{w}", "proposal_index": j}},
                    "defect_before": {"flat": [0.0] * 34, "flat_keys": keys, "quotient_meta": {"goal_shape": {"has_arith": bool(good)}}},
                    "defect_after": {"flat": flat_after},
                    "response": {f"r{k}": 0.0 for k in range(3)},
                    "messages": [f"m_{'hi' if hidden[w] > 0.5 else 'lo'}"] if memory else ["m_flat"],
                })
    for w, rows in rows_by_wave.items():
        write_jsonl(run / f"wave_{w}" / "micro_audit.jsonl", rows)
    write_jsonl(run / "boundaries.jsonl", boundaries)
    return root


def test_retro_fpr_end_to_end(tmp_path):
    root = _make_waves_root(tmp_path, memory=False)
    rows = load_candidate_rows(root)
    assert len(rows) == 24 * 4 * 4
    assert rows[0]["prompt_hash"].startswith("ph_")
    report = run_retro_fpr(root, n_boot=50)
    # Token decides success: every arm containing the token factor separates.
    assert report["arms"]["T"]["auc"] > 0.85
    assert report["arms"]["F"]["auc"] > 0.85
    assert 0 <= report["set_level_fn"]["B1"] <= 1
    assert set(report["gates"]) == {"C1_auc_F_ge_0.70", "C2_exists_tau", "C3_ece_le_0.05", "C4_raw_within_2pt"}


def test_emz_detects_planted_memory_and_not_its_absence(tmp_path):
    root_mem = _make_waves_root(tmp_path / "m", memory=True, n_tasks=40, seed=1)
    root_nomem = _make_waves_root(tmp_path / "n", memory=False, n_tasks=40, seed=2)
    chains_mem = build_chains(root_mem)
    chains_nomem = build_chains(root_nomem)
    assert all(len(c["waves"]) == 4 for c in chains_mem)
    d_mem = memory_delta(chains_mem, "L34", n_perm=30, seed=0)
    d_nomem = memory_delta(chains_nomem, "L34", n_perm=30, seed=0)
    # Planted latent is lag-visible only: strong delta with memory, none without.
    assert d_mem["n_transitions"] == 40 * 2
    assert d_mem["delta_auc"] > 0.10
    assert d_mem["p_value"] <= 0.1
    assert d_nomem["p_value"] > 0.05 or d_nomem["delta_auc"] < 0.03


def test_run_emz_report_shape(tmp_path):
    root = _make_waves_root(tmp_path, memory=False, n_tasks=12)
    report = run_emz(root, n_perm=10)
    assert report["n_chains"] == 12
    assert set(report["arms"]) == {"L34", "LTXT", "BOTH", "T2_L34"}
    assert report["decision"] in {"kill_memory_module", "ema_port_only", "learned_memory_justified"}
