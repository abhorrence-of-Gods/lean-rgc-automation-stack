from __future__ import annotations

import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl
from lean_rgc.contextual_congruence import contextual_response_congruence_from_files
from lean_rgc.cli import build_parser


def test_contextual_response_congruence_classes(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, [
        {"state_id":"s1", "action_id":"simp", "tactic":"simp", "response":{"goal.eq":1.0}, "carrier_delta":{"simp":0.2}},
        {"state_id":"s2", "action_id":"simp", "tactic":"simp", "response":{"goal.eq":0.8}, "carrier_delta":{"simp":0.1}},
        {"state_id":"s1", "action_id":"rw", "tactic":"rw", "response":{"goal.eq":0.95}, "carrier_delta":{"simp":0.15}},
        {"state_id":"s2", "action_id":"rw", "tactic":"rw", "response":{"goal.eq":0.75}, "carrier_delta":{"simp":0.1}},
        {"state_id":"s1", "action_id":"omega", "tactic":"omega", "response":{"goal.arith":1.0}, "carrier_delta":{"arith":0.4}},
    ])
    rep = contextual_response_congruence_from_files(responses, tmp_path / "cc", cosine_threshold=0.8, distance_threshold=0.4)
    assert rep["classes"]["n_classes"] >= 2
    classes = [json.loads(x) for x in (tmp_path / "cc" / "response_congruence_classes.jsonl").read_text().splitlines() if x.strip()]
    merged = [set(c.get("member_action_ids", [])) for c in classes]
    assert any({"simp", "rw"}.issubset(s) for s in merged)
    assert (tmp_path / "cc" / "contextual_response_congruence_report.json").exists()


def test_contextual_response_congruence_cli_and_pipeline(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    write_jsonl(responses, [
        {"state_id":"s", "action_id":"a", "response":{"goal.closed":1.0}},
        {"state_id":"s", "action_id":"b", "response":{"goal.closed":0.9}},
    ])
    parser = build_parser()
    out = tmp_path / "out"
    args = parser.parse_args(["contextual-response-congruence", "--responses", str(responses), "--out", str(out), "--cosine-threshold", "0.7"])
    assert args.func(args) == 0
    assert (out / "contextual_response_congruence_report.json").exists()
