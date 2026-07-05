"""Label audit: tagged-error re-attribution and the fixed _ERROR_RE."""

from __future__ import annotations

from lean_rgc.evals.label_audit import recount_rows
from lean_rgc.lean.bulk_executor import _ERROR_RE, _errors_by_line


def test_error_re_catches_tagged_diagnostics():
    plain = "/tmp/x.lean:10:2: error: unsolved goals"
    tagged = "/tmp/x.lean:23:6: error(lean.unknownIdentifier): Unknown identifier `h`"
    assert _ERROR_RE.match(plain)
    m = _ERROR_RE.match(tagged)
    assert m and m.group("line") == "23" and m.group("level") == "error"
    # tagged line now gets its OWN key instead of riding the previous error
    out = _errors_by_line(plain + "\n" + tagged)
    assert 10 in out and 23 in out
    assert all("unknownIdentifier" not in x for x in out[10])


def test_attribution_ownership_rule():
    # Defects #3/#4: bleed errors on the NEXT block's set_option line
    # belong to the offender; file-end errors belong to the LAST block;
    # only pre-first-block lines stay global.
    from lean_rgc.lean.bulk_executor import _attribute_lines, _render_bulk_file
    from lean_rgc.schemas import LeanTask, TacticAction

    task = LeanTask(task_id="t", statement="True", imports=[])
    pairs = [
        (task, TacticAction(action_id="a0", tactic="calc")),      # dangling
        (task, TacticAction(action_id="a1", tactic="trivial")),   # innocent
        (task, TacticAction(action_id="a2", tactic="calc")),      # dangling last
    ]
    _src, blocks = _render_bulk_file(pairs)
    bleed_line = blocks[1].start_line          # next block's set_option line
    eof_line = blocks[2].end_line + 40         # far past the last block
    global_line = 1                            # import failure territory
    line_errors = {
        bleed_line: ["err: bleed from block0"],
        eof_line: ["err: dangling at EOF"],
        global_line: ["err: unknown module"],
    }
    per_block, global_msgs = _attribute_lines(blocks, line_errors)
    assert per_block[0] == ["err: bleed from block0"]   # offender pays
    assert per_block[1] == []                            # neighbor unpoisoned
    assert per_block[2] == ["err: dangling at EOF"]      # last owns EOF
    assert global_msgs == ["err: unknown module"]


def _row(task, status, msgs, bs, be, lf="/tmp/x/rgc_bulk_0001.lean", tactic="t"):
    return {
        "task_id": task, "status": status, "messages": msgs, "lean_file": lf,
        "action": {"tactic": tactic},
        "audit_flags": {"block_start_line": bs, "block_end_line": be},
    }


def test_recount_flags_false_success_via_neighbor_stored_error():
    # Block A (lines 8-12) failed plainly; the tagged error of block B
    # (lines 20-24) was stored in A's messages. B claims success.
    rows = [
        _row("tA", "fail", [
            "/tmp/x/rgc_bulk_0001.lean:9:0: error: unsolved goals",
            "/tmp/x/rgc_bulk_0001.lean:22:6: error(lean.unknownIdentifier): Unknown identifier `h`",
        ], 8, 12),
        _row("tB", "success", [], 20, 24),
        _row("tC", "success", [], 30, 34),
    ]
    rep = recount_rows(rows)
    assert rep["n_success_rows"] == 2
    assert rep["n_false_success_rows"] == 1
    assert rep["false_rows"][0]["task_id"] == "tB"
    assert rep["true_tasks"] == ["tC"]


def test_load_false_pairs_refuses_empty_and_reads_bundles(tmp_path):
    import json

    import pytest

    from lean_rgc.evals.label_audit import load_false_pairs

    p = tmp_path / "bundle.json"
    p.write_text(json.dumps({"pilot": {"false_pairs": [["t1", "rw [h]"]]}}), encoding="utf-8")
    assert load_false_pairs(p) == {("t1", "rw [h]")}
    # Loader must fail loudly rather than silently no-op (the empty-set
    # join invalidated a whole analysis pass before this guard existed).
    p2 = tmp_path / "empty.json"
    p2.write_text(json.dumps({"pilot": {"false_pairs": []}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_false_pairs(p2)


def test_apply_corrected_labels_demotes_only_matches():
    from lean_rgc.evals.label_audit import apply_corrected_labels

    rows = [
        {"task_id": "t1", "tactic": "bad", "status": "success"},
        {"task_id": "t1", "tactic": "good", "status": "success"},
        {"task_id": "t2", "tactic": "bad", "status": "fail"},
    ]
    n = apply_corrected_labels(rows, {("t1", "bad")})
    assert n == 1
    assert rows[0]["status"] == "elab_error"
    assert rows[1]["status"] == "success"
    assert rows[2]["status"] == "fail"


def test_recount_leaves_unrangeable_rows_as_claimed():
    rows = [{"task_id": "old", "status": "success", "messages": [], "lean_file": "x", "action": {}, "audit_flags": {}}]
    rep = recount_rows(rows)
    assert rep["n_unrangeable_rows"] == 1
    assert rep["true_tasks"] == ["old"]
