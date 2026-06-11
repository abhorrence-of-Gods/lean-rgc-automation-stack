import json
from pathlib import Path

from lean_rgc.evals.harness import run_eval
from lean_rgc.pbct.episode_store import import_prompt_artifacts, summarize_prompt_db
from lean_rgc.pbct.llm_client import LLMClient, LLMClientConfig
from lean_rgc.pbct.proposals import make_llm_proposal_fn
from lean_rgc.pbct.signal_bridge import build_signal_packet, make_signal_packet_fn, render_packet_for_prompt
from lean_rgc.schemas import LeanTask, read_jsonl


def _responses() -> list[dict]:
    return [
        {
            "task_id": "t0",
            "status": "elab_error",
            "messages": ["unknown identifier 'foo'" + "x" * 600],
            "response": {"goal.eq": 0.4},
        },
        {"task_id": "t0", "status": "timeout", "response": {"goal.eq": 0.9, "carrier.missing_simp": 0.1}},
    ]


def test_packet_build_truncates_and_aggregates():
    packet = build_signal_packet(task_id="t0", response_rows=_responses(), max_message_chars=100)

    assert packet["last_failure"]["n_responses"] == 2
    assert packet["last_failure"]["status_counts"] == {"elab_error": 1, "timeout": 1}
    assert len(packet["last_failure"]["lean_messages"][0]) == 100
    assert packet["response"]["observed_max"]["goal.eq"] == 0.9
    assert packet["canonical_status"] == "prompt_signal_packet_is_diagnostic_not_canonical"


def test_packet_render_is_deterministic_and_filterable():
    packet = build_signal_packet(
        task_id="t0",
        response_rows=_responses(),
        crg={"relaxed_score": 0.7, "hardening_gap": 0.7},
        poms={"promotion_readiness": "witness_only"},
    )
    full_a = render_packet_for_prompt(packet)
    full_b = render_packet_for_prompt(packet)
    only_failure = render_packet_for_prompt(packet, include_keys=("last_failure",))

    assert full_a == full_b
    assert "crg:" in full_a
    assert "poms:" in full_a
    assert "lean: unknown identifier" in full_a
    assert "crg:" not in only_failure
    assert "lean: unknown identifier" in only_failure


def _wave_runner(*, wave_index, tasks, actions_by_task, wave_dir, run_id, **kwargs):
    rows = []
    for task in tasks:
        for action in actions_by_task.get(task.task_id, []):
            solved = action.tactic == "exact trivial"
            rows.append(
                {
                    "task_id": task.task_id,
                    "action_id": action.action_id,
                    "status": "proved" if solved else "elab_error",
                    "messages": [] if solved else [f"unknown identifier wave{wave_index}"],
                    "response": {"goal.eq": 0.3 + 0.1 * wave_index},
                }
            )
    return rows


def test_a2_arm_end_to_end_with_bridge(tmp_path: Path):
    losing = json.dumps({"proposals": [{"proposal_kind": "tactic", "lean_tactic": "simp"}]})
    winning = json.dumps({"proposals": [{"proposal_kind": "tactic", "lean_tactic": "exact trivial"}]})
    client = LLMClient(
        LLMClientConfig(
            provider="mock",
            cache_dir=str(tmp_path / "llm_cache"),
            mock_responses=[losing, winning],
        )
    )
    seen_feedback: list[str] = []
    base_proposal_fn = make_llm_proposal_fn(client=client, boundaries_out=tmp_path / "boundaries.jsonl")

    def spying_proposal_fn(*, task, attempt_index, feedback):
        seen_feedback.append(feedback)
        return base_proposal_fn(task=task, attempt_index=attempt_index, feedback=feedback)

    packets: list[dict] = []
    summary = run_eval(
        tasks=[LeanTask(task_id="t0", statement="True", imports=[])],
        arm="a2_typed_packet",
        proposal_fn=spying_proposal_fn,
        signal_packet_fn=make_signal_packet_fn(packets_sink=packets),
        out_dir=tmp_path / "eval",
        run_id="r0",
        budget_calls=3,
        wave_audit_runner=_wave_runner,
    )

    assert summary["n_solved"] == 1
    assert "[audited telemetry]" in seen_feedback[0]
    # wave 1 feedback must carry the typed telemetry of wave 0 failures
    assert "unknown identifier wave0" in seen_feedback[1]
    assert "response observed max" in seen_feedback[1]
    assert len(packets) == 2


def test_episode_store_imports_and_summarizes(tmp_path: Path):
    boundaries = tmp_path / "boundaries.jsonl"
    episodes = tmp_path / "episodes.jsonl"
    mutations = tmp_path / "mutations.jsonl"
    boundaries.write_text(
        json.dumps(
            {
                "boundary_id": "pb_a",
                "task_id": "t0",
                "boundary_kind": "tactic_synthesis",
                "attempt_index": 0,
                "prompt_hash": "ph",
                "output_hash": "oh",
                "model_id": "m",
                "cached": True,
                "n_proposals": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    episodes.write_text(
        "".join(
            json.dumps(r) + "\n"
            for r in [
                {"episode_id": "ep_1", "run_id": "r0", "arm": "a2_typed_packet", "task_id": "t0", "solved": True, "attempts_used": 2, "llm_calls": 2, "audit_pass_count": 1, "first_solve_attempt": 2, "budget_calls": 4},
                {"episode_id": "ep_2", "run_id": "r0", "arm": "a1_raw_error", "task_id": "t0", "solved": False, "attempts_used": 4, "llm_calls": 4, "audit_pass_count": 0, "first_solve_attempt": None, "budget_calls": 4},
            ]
        ),
        encoding="utf-8",
    )
    mutations.write_text(
        json.dumps(
            {
                "mutation_id": "mu_1",
                "parent_boundary_id": "pb_a",
                "child_boundary_id": "pb_b",
                "mutation_kind": "inject_coker_normal",
                "expected_effect": {"hardening_gap_delta": -0.1},
                "observed_effect": {"hardening_gap_delta": -0.12},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    db = tmp_path / "prompt.sqlite"
    report = import_prompt_artifacts(
        db_path=db, boundaries_path=boundaries, episodes_path=episodes, mutations_path=mutations
    )
    again = import_prompt_artifacts(
        db_path=db, boundaries_path=boundaries, episodes_path=episodes, mutations_path=mutations
    )
    summary = summarize_prompt_db(db)

    assert report["n_boundaries_imported"] == 1
    assert report["n_episodes_imported"] == 2
    assert report["n_mutations_imported"] == 1
    assert again["n_episodes_imported"] == 2  # idempotent re-import, no duplication
    assert summary["counts"] == {"prompt_boundaries": 1, "prompt_episodes": 2, "prompt_mutations": 1}
    assert summary["episodes_by_arm"]["a2_typed_packet"]["solve_rate"] == 1.0
    assert summary["episodes_by_arm"]["a1_raw_error"]["solve_rate"] == 0.0
    assert summary["boundary_cache_rate"] == 1.0
