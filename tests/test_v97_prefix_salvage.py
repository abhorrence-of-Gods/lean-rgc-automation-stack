"""D3 Phase 1 estimator: boundary snapping, block reconstruction, end-to-end."""

from __future__ import annotations

import json

from lean_rgc.evals.prefix_salvage import (
    estimate_candidates,
    run_prefix_salvage,
    snap_fraction,
    tactic_boundaries,
)
from lean_rgc.schemas import write_jsonl


def test_boundaries_semicolon_comma_and_combinator():
    s = "rw [h₀, h₁]; ring_nf <;> simp, linarith"
    bs = tactic_boundaries(s)
    assert 0 in bs
    assert s.index(";") + 1 in bs            # top-level ';' -> after
    assert s.index(",", 15) in bs             # top-level ',' -> before
    # commas INSIDE brackets are not boundaries
    assert s.index(",") not in bs
    # '<;>' is a combinator, not a boundary
    semis = [i for i, ch in enumerate(s) if ch == ";"]
    assert semis[1] + 1 not in bs


def test_snap_fraction_snaps_down_to_boundary():
    script = "intro n; rw [h]; ring"
    # Error inside 'rw [h]' (line 1, col points mid-tactic incl. 2-indent):
    err_col_in_rw = 2 + script.index("[h]")
    f, cut = snap_fraction(script, 1, err_col_in_rw)
    assert script[:cut].rstrip() == "intro n;"
    assert 0 < f < 0.5
    # Error inside the final 'ring': prefix keeps the first two tactics.
    f2, cut2 = snap_fraction(script, 1, 2 + script.index("ring"))
    assert script[:cut2].rstrip() == "intro n; rw [h];"
    assert f2 > f


def _mk_run(tmp_path, task_id, statement, tactic, messages, status):
    """One-chunk synthetic run matching the reconstructor's layout
    assumptions (H=7; block = [BEGIN, set_option(S), theorem(T), tactic
    lines, END, blank] so offsets step by n+5)."""
    row = {
        "task_id": task_id,
        "action_id": "a0",
        "status": status,
        "target": statement,
        "action": {"tactic": tactic},
        "lean_file": "/tmp/x/rgc_bulk_0001.lean",
        "messages": messages,
        "audit_flags": {"cache_hit": False},
        "after_state": {"target": statement},
    }
    write_jsonl(tmp_path / "runX" / "wave_0" / "micro_audit.jsonl", [row])
    return tmp_path


def test_end_to_end_partial_with_anchor_is_f1(tmp_path):
    from lean_rgc.evals.prefix_salvage import _by_column

    task, stmt = "taskA", "1 + 1 = 2"
    # H=7 -> first block offset 0 -> theorem line T = 7 + 0 + 3 = 10.
    anchor = f"/tmp/x/rgc_bulk_0001.lean:10:{_by_column(task, stmt)}: error: unsolved goals"
    root = _mk_run(tmp_path, task, stmt, "norm_num", [anchor], "partial")
    records, diag = estimate_candidates(root)
    assert len(records) == 1
    assert records[0]["f"] == 1.0 and records[0]["klass"] == "complete_unsolved"
    assert diag["anchor_agreement"]["anchored"] == 1
    assert diag["anchor_agreement"]["disagree"] == 0


def test_end_to_end_mid_script_error_snaps(tmp_path):
    task, stmt = "taskB", "True"
    tactic = "intro h; exact bad_name; trivial"
    # Error on the tactic line (T=10 -> k=1), column inside 'exact ...'.
    col = 2 + tactic.index("exact")
    msg = f"/tmp/x/rgc_bulk_0001.lean:11:{col}: error(lean.unknownIdentifier): Unknown identifier `bad_name`"
    root = _mk_run(tmp_path, task, stmt, tactic, [msg], "fail")
    records, _ = estimate_candidates(root)
    assert len(records) == 1
    rec = records[0]
    assert rec["klass"] == "err_tactic"
    assert rec["prefix"] == "intro h;"
    assert 0 < rec["f"] < 0.5


def test_report_shape_and_gates(tmp_path):
    task, stmt = "taskC", "True"
    msg = "/tmp/x/rgc_bulk_0001.lean:10:0: error: unexpected token"
    root = _mk_run(tmp_path, task, stmt, "trivial", [msg], "fail")
    report = run_prefix_salvage(root)
    assert set(report["gates"]) == {
        "G0a_anchor_agreement", "G0b_coverage", "G0c_calibration",
        "G1_full_license", "G2_partial_license", "G3_continuation_arm",
    }
    assert report["gates"]["G0c_calibration"] == "pending_pod_probe"
    # Error at the theorem line -> f = 0 (statement-level failure).
    assert report["deduped"]["share_f0"] == 1.0
