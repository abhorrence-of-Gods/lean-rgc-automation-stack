"""R0 instrumentation bundle: block line offsets, prefix visibility, wave-row preservation."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

from lean_rgc.grad.collect import archive_run_artifacts, collect_wave_rows, preserve_wave_rows
from lean_rgc.lean import bulk_executor as bx
from lean_rgc.pbct.boundary import build_prompt_boundary, render_boundary
from lean_rgc.schemas import LeanTask, TacticAction, write_jsonl


# ---- bulk executor: audit_flags carry block line offsets ----

class _FakeProc:
    stdout = ""
    stderr = ""
    returncode = 0


def test_bulk_audit_flags_carry_block_line_offsets(monkeypatch):
    task = LeanTask(task_id="t1", statement="True", imports=[])
    a1 = TacticAction(action_id="trivial", tactic="trivial", tactic_class="trivial")
    a2 = TacticAction(action_id="rfl2", tactic="rfl", tactic_class="rfl")
    pairs = [(task, a1), (task, a2)]
    monkeypatch.setattr(bx.subprocess, "run", lambda *a, **k: _FakeProc())
    auditor = bx.LeanBulkAuditor(bx.BulkAuditConfig(lean_cmd="lean-stub"))
    records = auditor._run_chunk(pairs, batch_index=1)
    _, blocks = bx._render_bulk_file(pairs, trace_state=auditor.config.trace_state)
    assert len(records) == len(blocks) == 2
    for rec, block in zip(records, blocks):
        assert rec.audit_flags["block_start_line"] == block.start_line
        assert rec.audit_flags["block_end_line"] == block.end_line
        assert block.start_line < block.end_line


def test_sanitize_ident_is_style_linter_clean():
    # Regression: "__positive_control__" rendered a theorem name with "__",
    # mathlib's linter.style.nameCheck warned, and the audit classified the
    # note as failure — the g1 positive control gate tripped on it.
    assert bx._sanitize_ident("__positive_control__") == "positive_control"
    assert bx._sanitize_ident("a--b..c") == "a_b_c"
    assert bx._sanitize_ident("123abc") == "x_123abc"
    assert bx._sanitize_ident("___") == "x"
    task = LeanTask(task_id="__positive_control__", statement="True", imports=[])
    action = TacticAction(action_id="control_trivial", tactic="trivial", tactic_class="trivial")
    src, blocks = bx._render_bulk_file([(task, action)])
    assert "__" not in blocks[0].theorem_name
    assert f"theorem {blocks[0].theorem_name} : True := by" in src


# ---- prompt boundary: prefix visibility with hash stability ----

def test_boundary_without_prefix_has_no_prefix_key():
    task = LeanTask(task_id="t1", statement="1 + 1 = 2", imports=[])
    b = build_prompt_boundary(task=task)
    assert "prefix" not in b
    _, user = render_boundary(b)
    assert "Verified proof prefix" not in user


def test_boundary_with_prefix_is_model_visible_and_changes_id():
    bare = LeanTask(task_id="t1", statement="1 + 1 = 2", imports=[])
    with_prefix = LeanTask(
        task_id="t1", statement="1 + 1 = 2", imports=[],
        prefix="theorem t1 : 1 + 1 = 2 := by\n  have h : 1 = 1 := rfl",
    )
    b0 = build_prompt_boundary(task=bare)
    b1 = build_prompt_boundary(task=with_prefix)
    assert b1["prefix"] == with_prefix.prefix
    assert b0["boundary_id"] != b1["boundary_id"]
    _, user = render_boundary(b1)
    assert "Verified proof prefix" in user
    assert "have h : 1 = 1 := rfl" in user
    # Statement first, prefix after it: the prefix is context, not the goal.
    assert user.index("Theorem statement") < user.index("Verified proof prefix")


# ---- wave-row preservation ----

def _make_run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    for wave, statuses in (("wave_0", ["success", "fail"]), ("wave_1", ["elab_error"]), ("wave_control", ["success"])):
        rows = [
            {"task_id": f"t{i}", "status": s, "action": {"tactic": "rfl"}}
            for i, s in enumerate(statuses)
        ]
        write_jsonl(run / wave / "micro_audit.jsonl", rows)
    write_jsonl(run / "boundaries.jsonl", [{"boundary_id": "pb_x"}])
    return run


def test_collect_wave_rows_aggregates_and_annotates(tmp_path):
    run = _make_run_dir(tmp_path)
    summary = collect_wave_rows(run)
    assert summary["n_rows"] == 4
    assert summary["per_wave"] == {"wave_0": 2, "wave_1": 1, "wave_control": 1}
    assert summary["status_counts"] == {"success": 2, "fail": 1, "elab_error": 1}
    rows = [json.loads(l) for l in (run / "wave_rows.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["wave_index"] for r in rows] == [0, 0, 1, -1]
    assert rows[0]["wave_source"] == "wave_0/micro_audit.jsonl"


def test_archive_contains_wave_and_run_level_files(tmp_path):
    run = _make_run_dir(tmp_path)
    collect_wave_rows(run)
    summary = archive_run_artifacts(run)
    with tarfile.open(summary["archive"], "r:gz") as tf:
        names = set(tf.getnames())
    assert "wave_0/micro_audit.jsonl" in names
    assert "wave_control/micro_audit.jsonl" in names
    assert "boundaries.jsonl" in names
    assert "wave_rows.jsonl" in names


def test_preserve_wave_rows_returns_errors_as_data(tmp_path):
    # Missing run dir must not raise: failures surface in the summary.
    result = preserve_wave_rows(tmp_path / "does_not_exist")
    assert "collect_error" in result or "archive_error" in result
