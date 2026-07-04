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


# ---------------- M1 reuse ladder ----------------

def test_m1_alpha_gauge_unifies_renamed_goals():
    from lean_rgc.evals.reuse_ladder import key_k1, key_k2, parse_goal

    g1 = parse_goal(["n : Nat"], "n + 0 = n")
    g2 = parse_goal(["m : Nat"], "m + 0 = m")
    assert key_k1(g1) == key_k1(g2)
    assert key_k2(g1) == key_k2(g2) == "v0 + 0 = v0"


def test_m1_support_gauge_ignores_garbage_context():
    from lean_rgc.evals.reuse_ladder import key_k1, key_k3, parse_goal

    clean = parse_goal(["n : Nat", "h : 0 < n"], "n + 0 = n")
    garbage = parse_goal(["n : Nat", "h : 0 < n", "junk : List Bool", "u : junk = junk"], "n + 0 = n")
    # h is in the closure only if referenced from the target; here only n is.
    assert key_k3(clean) == key_k3(garbage)
    assert key_k1(clean) != key_k1(garbage)


def test_m1_dependency_closure_is_transitive():
    from lean_rgc.evals.reuse_ladder import _dependency_closure, parse_goal

    g = parse_goal(["a : Nat", "h : a < b", "b : Nat", "z : Bool"], "a = 0")
    names = {n for n, _ in _dependency_closure(g)}
    # target -> a; a appears in h's type? h : a < b references a, but closure
    # follows FROM target names to hyps whose names occur in visited types:
    # target mentions a only; a's type mentions nothing; h is NOT pulled in
    # because 'h' does not occur in the target.
    assert names == {"a"}


def test_m1_trivial_target_proxy():
    from lean_rgc.evals.reuse_ladder import is_trivial_target

    assert is_trivial_target("True")
    assert is_trivial_target("v0 = v0")
    assert is_trivial_target("1 + 1 = 2")
    assert not is_trivial_target("v0 + 0 = v0")
    assert not is_trivial_target("v0 ^ 2 + v1 ^ 2 = 369")


def test_m1_parser_handles_subscripts_and_multibinder():
    from lean_rgc.lean.state_parser import LeanMessageParser

    text = (
        "unsolved goals\n"
        "b h v : ℝ\n"
        "h₀ : 0 < b ∧ 0 < h\n"
        "⊢ v = 65\n"
    )
    goals = LeanMessageParser().extract_goals(text)
    assert len(goals) == 1
    assert goals[0].hypotheses == ["b h v : ℝ", "h₀ : 0 < b ∧ 0 < h"]


def test_m1_end_to_end_ladder(tmp_path):
    from lean_rgc.evals.reuse_ladder import run_reuse_ladder
    from lean_rgc.schemas import write_jsonl

    root = tmp_path / "waves"
    # Two theorems reaching alpha-equivalent residual goals + garbage variant.
    rows_a = [
        {"task_id": "thmA", "status": "partial",
         "after_state": {"goals_text": "unsolved goals\nn : Nat\n⊢ n + 0 = n"}},
        {"task_id": "thmA", "status": "partial",
         "after_state": {"goals_text": "unsolved goals\nn : Nat\njunk : Bool\n⊢ n + 0 = n"}},
    ]
    rows_b = [
        {"task_id": "thmB", "status": "partial",
         "after_state": {"goals_text": "unsolved goals\nm : Nat\n⊢ m + 0 = m"}},
        {"task_id": "thmB", "status": "fail",
         "after_state": {"goals_text": "error: unknown identifier"}},
    ]
    write_jsonl(root / "run1" / "wave_0" / "micro_audit.jsonl", rows_a)
    write_jsonl(root / "run1" / "wave_1" / "micro_audit.jsonl", rows_b)
    report = run_reuse_ladder(root)
    assert report["n_goal_instances"] == 3
    r = report["rungs"]
    # Raw strings never collide across the garbage variant or renaming.
    assert r["K0_raw"]["inter_theorem_rate"] == 0.0
    assert r["K0_raw"]["within_theorem_dup_rate"] == 0.0
    # K1 unifies renaming (thmA clean vs thmB) but not garbage.
    assert r["K1_alpha"]["inter_theorem_rate"] > 0.0
    # K3 unifies all three: garbage dropped, variables renamed.
    assert r["K3_goal_support"]["n_unique_keys"] == 1
    assert r["K3_goal_support"]["inter_theorem_rate"] == 1.0
    assert r["K3_goal_support"]["within_theorem_dup_rate"] == 1 / 3
    assert report["decision"] == "central_layer_live"
