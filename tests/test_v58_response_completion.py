from pathlib import Path

from lean_rgc.response_completion import build_response_completion, response_map_from_row
from lean_rgc.schemas import write_jsonl


def test_response_completion_aligns_response_shapes(tmp_path: Path):
    responses = tmp_path / "responses.jsonl"
    fingerprints = tmp_path / "fingerprints.jsonl"
    out = tmp_path / "response_completion.json"

    write_jsonl(
        responses,
        [
            {
                "response_keys": ["goal.eq", "carrier.missing_simp"],
                "response_flat": [1.0, -0.5],
                "carrier_delta": {"hidden_obligations": -1.0},
                "gamma_transition": {"tail": 0.25},
            },
            {"response": {"goal.eq": 0.4, "audit.unsafe": -1.0}},
        ],
    )
    write_jsonl(
        fingerprints,
        [
            {
                "fingerprint": {"ctx:eq::resp::goal.simp": 0.7},
                "response_summary": {"goal.rfl": 1.0},
                "carrier_summary": {"hidden_obligations": -0.25},
            }
        ],
    )

    summary = build_response_completion(out=out, responses_path=responses, fingerprints_path=fingerprints)
    completion = __import__("json").loads(out.read_text(encoding="utf-8"))

    assert len(summary["response_keys"]) >= 6
    assert "goal.eq" in completion["response_keys"]
    assert "carrier.hidden_obligations" in completion["response_keys"]
    assert "goal.simp" in completion["response_keys"]
    assert completion["weights"]["goal.eq"] == 1.0
    assert "audit.unsafe" in completion["paid_cone_keys"]


def test_response_map_from_dict_flat_and_fingerprint():
    row = {
        "response_keys": ["goal.eq"],
        "response_flat": [0.5],
        "response": {"goal.rfl": 1.0},
        "fingerprint": {"ctx::carrier::missing": -1.0},
    }

    response = response_map_from_row(row)

    assert response["goal.eq"] == 0.5
    assert response["goal.rfl"] == 1.0
    assert response["carrier.missing"] == -1.0
