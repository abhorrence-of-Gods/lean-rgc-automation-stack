from lean_rgc.bulk_executor import _render_bulk_file, _errors_by_line, _block_messages
from lean_rgc.schemas import LeanTask, TacticAction


def test_bulk_render_line_mapping_and_error_parse():
    task = LeanTask(task_id="t1", statement="True", imports=[])
    a1 = TacticAction(action_id="trivial", tactic="trivial", tactic_class="trivial")
    a2 = TacticAction(action_id="bad", tactic="exact False.elim ?h", tactic_class="exact")
    src, blocks = _render_bulk_file([(task, a1), (task, a2)])
    assert "RGC_AUDIT_BEGIN" in src
    assert len(blocks) == 2
    assert blocks[0].start_line < blocks[0].end_line < blocks[1].start_line
    fake = f"/tmp/x.lean:{blocks[1].start_line+1}:3: error: unknown identifier 'h'\nmore detail"
    errs = _errors_by_line(fake)
    assert blocks[1].start_line + 1 in errs
    assert _block_messages(blocks[0], errs) == []
    assert any("unknown identifier" in m for m in _block_messages(blocks[1], errs))
