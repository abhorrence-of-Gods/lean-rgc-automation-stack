import numpy as np
import pytest

from lean_rgc.toys.phase_hmm import (
    build_loop_kernel,
    decide_split,
    dual_error,
    estimate_value,
    freeze_decision,
    hierarchical_vs_flat_recovery,
    loop_effect,
    make_phase_system,
    phase_value,
    run_toy0_report,
    selection_defect,
    split_gains,
)


def test_kernels_are_stochastic_and_rewards_bounded():
    system = make_phase_system("S2", seed=0)
    for phase in system.leaves:
        P, r = build_loop_kernel(system, phase)
        assert np.allclose(P.sum(axis=1), 1.0)
        assert np.all((r >= 0.0) & (r <= 1.0))


def test_result1_and_3_future_only_difference_does_not_split():
    """S1: A1/A2 differ in future token law but not in reward or loop kernel."""

    system = make_phase_system("S1", seed=0)
    gains = split_gains(system, "A")

    assert gains["g_future"] > 0.2, "token preference difference must be visible in the future law"
    assert gains["g_loop"] == pytest.approx(0.0, abs=1e-12), "loop kernel must be exactly identical"
    assert gains["g_target"] == pytest.approx(0.0, abs=1e-12)
    assert decide_split(gains)["split"] is False


def test_result2_reward_difference_splits_and_b_does_not():
    system = make_phase_system("S2", seed=0)

    assert decide_split(split_gains(system, "root"))["split"] is True
    assert decide_split(split_gains(system, "A"))["split"] is True
    b = split_gains(system, "B")
    assert b["g_loop"] == pytest.approx(0.0, abs=1e-9)
    assert decide_split(b)["split"] is False


def test_certified_freeze_requires_margin_over_uncertainty():
    system = make_phase_system("S2", seed=0)
    rng = np.random.default_rng(0)

    small = {p: estimate_value(system, p, n_episodes=2, steps=5, rng=rng) for p in ("A1", "A2")}
    large = {p: estimate_value(system, p, n_episodes=200, steps=20, rng=rng) for p in ("A1", "A2")}

    assert freeze_decision(small)["frozen"] is False
    decision = freeze_decision(large)
    assert decision["frozen"] is True
    assert decision["chosen"] == "A1"


def test_closed_loop_beats_open_loop():
    system = make_phase_system("S2", seed=0)
    assert loop_effect(system, "A1") > 0.02


def test_selection_defect_tracks_loop_relevance():
    assert selection_defect(make_phase_system("S1", seed=0), "A") == pytest.approx(0.0, abs=1e-12)
    assert selection_defect(make_phase_system("S2", seed=0), "A") > 0.2


def test_dual_error_shrinks_with_finer_atlas():
    system = make_phase_system("S2", seed=0)
    coarse = dual_error(system, target_phase="A1", posterior=0.95, atlas_cell="A")
    fine = dual_error(system, target_phase="A1", posterior=0.95, atlas_cell="A1")
    assert coarse > 5 * fine


def test_hierarchical_recovery_beats_flat_at_equal_budget():
    system = make_phase_system("S2h", seed=0)
    rec = hierarchical_vs_flat_recovery(system, budget_episodes=32, seed=0)
    assert rec["hierarchical"] > rec["flat"]


def test_report_supports_all_hypotheses(tmp_path):
    report = run_toy0_report(out=tmp_path / "toy0_report.json")
    assert all(report["hypotheses"].values()), report["hypotheses"]
    assert (tmp_path / "toy0_report.json").exists()


def test_token_labels_carry_no_meaning():
    """Different label permutations must not change any loop quantity."""

    a = make_phase_system("S2", seed=0)
    b = make_phase_system("S2", seed=123)
    assert not np.array_equal(a.sigma, b.sigma)
    for phase in a.leaves:
        assert phase_value(a, phase) == pytest.approx(phase_value(b, phase), abs=1e-12)
    ga, gb = split_gains(a, "A"), split_gains(b, "A")
    assert ga["g_loop"] == pytest.approx(gb["g_loop"], abs=1e-12)
    assert ga["g_target"] == pytest.approx(gb["g_target"], abs=1e-12)
