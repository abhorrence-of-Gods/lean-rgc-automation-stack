import json
from pathlib import Path

from lean_rgc.evals.harness import _response_error_text, load_wave_rows
from lean_rgc.pbct.signal_bridge import build_signal_packet


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _micro_row() -> dict:
    return {
        "task_id": "t0",
        "action_id": "a0",
        "action": {"action_id": "a0", "tactic": "simp"},
        "status": "fail",
        "messages": ["/tmp/x.lean:23:27: error: unexpected token ':'; expected command"],
        "response": {"goal.eq": 0.2},
    }


def test_load_wave_rows_prefers_micro_audit(tmp_path: Path):
    _write_jsonl(tmp_path / "responses.jsonl", [{"task_id": "t0", "audit_status": "fail"}])
    _write_jsonl(tmp_path / "micro_audit.jsonl", [_micro_row()])

    rows = load_wave_rows(tmp_path)

    assert len(rows) == 1
    assert rows[0]["messages"], "micro_audit rows carry Lean messages; responses.jsonl rows do not"


def test_load_wave_rows_falls_back_to_responses(tmp_path: Path):
    _write_jsonl(tmp_path / "responses.jsonl", [{"task_id": "t0", "audit_status": "fail"}])

    rows = load_wave_rows(tmp_path)

    assert len(rows) == 1
    assert load_wave_rows(tmp_path / "missing") == []


def test_micro_audit_row_feeds_error_text_and_packet_messages():
    row = _micro_row()

    assert "unexpected token" in _response_error_text(row)

    packet = build_signal_packet(task_id="t0", response_rows=[row])
    assert packet["last_failure"]["lean_messages"]
    assert "unexpected token" in packet["last_failure"]["lean_messages"][0]

    typed_only = build_signal_packet(task_id="t0", response_rows=[row], include_instance_messages=False)
    assert typed_only["last_failure"]["lean_messages"] == []
