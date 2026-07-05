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


def test_recount_leaves_unrangeable_rows_as_claimed():
    rows = [{"task_id": "old", "status": "success", "messages": [], "lean_file": "x", "action": {}, "audit_flags": {}}]
    rep = recount_rows(rows)
    assert rep["n_unrangeable_rows"] == 1
    assert rep["true_tasks"] == ["old"]
