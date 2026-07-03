from pathlib import Path

import pytest

from lean_rgc.evals.arms import ARMS, render_feedback
from lean_rgc.evals.harness import run_eval
from lean_rgc.pbct.signal_bridge import build_signal_packet, make_signal_packet_fn, render_packet_for_prompt
from lean_rgc.schemas import LeanTask


def _responses() -> list[dict]:
    return [
        {
            "task_id": "t0",
            "status": "elab_error",
            "messages": ["unknown identifier 'secret_instance_string'"],
            "response": {"goal.eq": 0.4},
        }
    ]


def test_typed_only_packet_drops_messages_keeps_aggregates():
    full = build_signal_packet(task_id="t0", response_rows=_responses())
    typed_only = build_signal_packet(task_id="t0", response_rows=_responses(), include_instance_messages=False)

    assert full["last_failure"]["lean_messages"]
    assert typed_only["last_failure"]["lean_messages"] == []
    # the aggregated typed blocks survive: this is the G-channel content
    assert typed_only["last_failure"]["status_counts"] == {"elab_error": 1}
    assert typed_only["response"]["observed_max"]["goal.eq"] == 0.4

    rendered = render_packet_for_prompt(typed_only)
    assert "secret_instance_string" not in rendered
    assert "elab_error" in rendered
    assert "response observed max" in rendered


def test_a3_arm_registered_and_requires_packet():
    assert "a3_typed_only" in ARMS
    with pytest.raises(NotImplementedError, match="a3_typed_only"):
        render_feedback("a3_typed_only", {"n_failed": 1})


def _wave_runner(*, wave_index, tasks, actions_by_task, wave_dir, run_id, **kwargs):
    rows = []
    for task in tasks:
        for action in actions_by_task.get(task.task_id, []):
            rows.append(
                {
                    "task_id": task.task_id,
                    "action_id": action.action_id,
                    "status": "elab_error",
                    "messages": ["unknown identifier 'secret_instance_string'"],
                    "response": {"goal.eq": 0.5},
                }
            )
    return rows


def test_a3_end_to_end_feedback_has_structure_without_instance_text(tmp_path: Path):
    seen: list[str] = []

    def proposal_fn(*, task, attempt_index, feedback):
        seen.append(feedback)
        return [{"tactic": "simp"}]

    run_eval(
        tasks=[LeanTask(task_id="t0", statement="True", imports=[])],
        arm="a3_typed_only",
        proposal_fn=proposal_fn,
        signal_packet_fn=make_signal_packet_fn(include_instance_messages=False),
        out_dir=tmp_path,
        run_id="r0",
        budget_calls=2,
        wave_audit_runner=_wave_runner,
    )

    assert "[audited telemetry]" in seen[1]
    assert "elab_error" in seen[1]
    assert "secret_instance_string" not in seen[1]
