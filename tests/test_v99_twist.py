"""S0: unified twist — head semantics, optimism direction, persistence."""

from __future__ import annotations

import numpy as np

from lean_rgc.grad.twist import FactorizedTwist, OptimisticLogLift, post_features, state_features

KEYS = ["goal.num_goals", "carrier.nat_arith_goal"]


def _row(task, tactic, status, *, carrier=1.0, resp=None):
    return {
        "task_id": task,
        "status": status,
        "tactic": tactic,
        "flat": [1.0, carrier],
        "flat_keys": KEYS,
        "goal_shape": {"has_arith": True},
        "feedback_text": "",
        "response": resp or {},
    }


def _fit_rows():
    rows = []
    for i in range(12):
        rows.append(_row(f"t{i}", "ring", "success" if i % 3 else "fail"))
        rows.append(_row(f"t{i}", "sorry_ish", "fail"))
    return rows


def test_state_value_is_action_invariant():
    tw = FactorizedTwist().fit(_fit_rows())
    a = _row("x", "ring", "fail")
    b = _row("x", "totally_different_tactic", "fail")
    va, vb = tw.state_value([a, b])
    assert va == vb
    # but the pre head DOES distinguish actions
    pa, pb = tw.score_pre([a, b])
    assert pa != pb


def test_optimism_dominates_mean_and_shrinks_with_evidence():
    rows = _fit_rows()
    tw = FactorizedTwist().fit(rows)
    probe = [_row("x", "ring", "fail")]
    assert tw.score_optimistic(probe)[0] >= tw.score_pre(probe)[0]
    # Rare feature gets more optimism than a frequent one with same rate.
    y = np.array([1.0, 0.0] * 10 + [1.0, 0.0])
    feats = [["f:common"]] * 20 + [["f:rare"]] * 2
    opt = OptimisticLogLift(shrinkage=2.0).fit(feats, y)
    assert opt.lift["f:rare"] > opt.lift["f:common"]


def test_post_head_uses_response_deltas():
    rows = _fit_rows()
    # Make response informative: successes carry a positive goal delta.
    for r in rows:
        r["response"] = {"goal.num_goals": 1.0 if r["status"] == "success" else -1.0}
    tw = FactorizedTwist().fit(rows)
    good = _row("x", "ring", "fail", resp={"goal.num_goals": 1.0})
    bad = _row("x", "ring", "fail", resp={"goal.num_goals": -1.0})
    sg, sb = tw.score_post([good, bad])
    assert sg > sb
    assert "rd:goal.num_goals+" in post_features(good)


def test_state_features_exclude_action_factors():
    feats = state_features(_row("x", "ring", "fail"))
    assert feats and all(not f.startswith(("tok:", "rw:", "fb:")) for f in feats)


def test_save_load_roundtrip(tmp_path):
    tw = FactorizedTwist().fit(_fit_rows())
    p = tmp_path / "twist.json"
    tw.save(p)
    tw2 = FactorizedTwist.load(p)
    probe = [_row("x", "ring", "fail")]
    assert np.allclose(tw.score_pre(probe), tw2.score_pre(probe))
    assert np.allclose(tw.score_optimistic(probe), tw2.score_optimistic(probe))
