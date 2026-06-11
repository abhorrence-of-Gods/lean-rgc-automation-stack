import json
from pathlib import Path

import pytest

from lean_rgc.evals.harness import run_eval
from lean_rgc.pbct.boundary import build_prompt_boundary, render_boundary
from lean_rgc.pbct.llm_client import LLMClient, LLMClientConfig
from lean_rgc.pbct.proposals import decode_completion, make_llm_proposal_fn, proposals_to_actions
from lean_rgc.schemas import LeanTask, read_jsonl


def _mock_client(tmp_path: Path, responses: list[str], **overrides) -> LLMClient:
    config = LLMClientConfig(
        provider="mock",
        model="mock-model",
        cache_dir=str(tmp_path / "llm_cache"),
        ledger_path=str(tmp_path / "llm_calls.jsonl"),
        mock_responses=responses,
        **overrides,
    )
    return LLMClient(config)


def test_mock_provider_caches_and_ledgers(tmp_path: Path):
    client = _mock_client(tmp_path, ['{"proposals": []}'])

    first = client.complete(system="s", user="u")
    second = client.complete(system="s", user="u")

    assert first.cached is False
    assert second.cached is True
    assert first.prompt_hash == second.prompt_hash
    assert first.text == second.text
    ledger = read_jsonl(tmp_path / "llm_calls.jsonl")
    assert len(ledger) == 2
    assert [row["cached"] for row in ledger] == [False, True]
    assert all("text" not in row for row in ledger)


def test_replay_provider_raises_on_miss_and_reuses_warm_cache(tmp_path: Path):
    replay = LLMClient(
        LLMClientConfig(provider="replay", model="mock-model", cache_dir=str(tmp_path / "llm_cache"))
    )
    with pytest.raises(RuntimeError, match="replay provider cache miss"):
        replay.complete(system="s", user="u")

    _mock_client(tmp_path, ["warm output"]).complete(system="s", user="u")
    warmed = replay.complete(system="s", user="u")
    assert warmed.cached is True
    assert warmed.text == "warm output"


def test_boundary_id_and_render_are_deterministic():
    task = LeanTask(task_id="t0", statement="True", imports=["Mathlib"])
    a = build_prompt_boundary(task=task, feedback_text="fb", attempt_index=1)
    b = build_prompt_boundary(task=task, feedback_text="fb", attempt_index=1)
    c = build_prompt_boundary(task=task, feedback_text="other", attempt_index=1)

    assert a["boundary_id"] == b["boundary_id"]
    assert a["boundary_id"] != c["boundary_id"]
    assert render_boundary(a) == render_boundary(b)
    system, user = render_boundary(a)
    assert "sorry" in system
    assert "True" in user
    assert "fb" in user
    assert a["canonical_status"] == "prompt_boundary_witness_not_canonical"


def test_decode_completion_strict_fenced_and_garbage():
    strict = decode_completion('{"proposals": [{"proposal_kind": "tactic", "lean_tactic": "simp"}]}')
    assert strict[0]["lean_tactic"] == "simp"

    fenced = decode_completion(
        'Here you go:\n```json\n{"proposals": [{"proposal_kind": "tactic", "lean_tactic": "rfl"}]}\n```\nDone.'
    )
    assert fenced[0]["lean_tactic"] == "rfl"

    garbage = decode_completion("I think you should try simp.")
    assert garbage[0]["proposal_kind"] == "decode_error"

    actions = proposals_to_actions(
        strict + garbage + [{"proposal_kind": "tactic", "lean_tactic": "   "}],
        boundary_id="pb_x",
        task_id="t0",
        prompt_hash="ph",
    )
    assert len(actions) == 1
    assert actions[0]["tactic"] == "simp"
    assert actions[0]["metadata"]["source"] == "llm_prompt_boundary"


def _wave_runner(*, wave_index, tasks, actions_by_task, wave_dir, run_id, **kwargs):
    rows = []
    for task in tasks:
        for action in actions_by_task.get(task.task_id, []):
            status = "proved" if action.tactic == "exact trivial" else "elab_error"
            rows.append({"task_id": task.task_id, "action_id": action.action_id, "status": status})
    return rows


def test_llm_proposal_fn_end_to_end_with_eval_harness(tmp_path: Path):
    losing = json.dumps({"proposals": [{"proposal_kind": "tactic", "lean_tactic": "simp"}]})
    winning = json.dumps({"proposals": [{"proposal_kind": "tactic", "lean_tactic": "exact trivial"}]})
    client = _mock_client(tmp_path, [losing, winning])
    proposal_fn = make_llm_proposal_fn(
        client=client,
        boundaries_out=tmp_path / "boundaries.jsonl",
    )

    summary = run_eval(
        tasks=[LeanTask(task_id="t0", statement="True", imports=[])],
        arm="a1_raw_error",
        proposal_fn=proposal_fn,
        out_dir=tmp_path / "eval",
        run_id="r0",
        budget_calls=3,
        wave_audit_runner=_wave_runner,
    )

    assert summary["n_solved"] == 1
    episodes = read_jsonl(tmp_path / "eval" / "episodes.jsonl")
    assert episodes[0]["first_solve_attempt"] == 2
    boundaries = read_jsonl(tmp_path / "boundaries.jsonl")
    assert len(boundaries) == 2
    # feedback differs between attempts, so the boundary and prompt change
    assert boundaries[0]["boundary_id"] != boundaries[1]["boundary_id"]
    assert boundaries[0]["model_id"] == "mock-model"
