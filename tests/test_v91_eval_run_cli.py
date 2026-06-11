import json
import sys
from pathlib import Path

from lean_rgc.cli.main import main
from lean_rgc.schemas import read_jsonl


def _fake_lean(tmp_path: Path) -> str:
    script = tmp_path / "fake_lean.py"
    script.write_text(
        "\n".join(
            [
                "import sys",
                "if '--version' in sys.argv:",
                "    print('Lean (fake eval-run test)')",
                "    raise SystemExit(0)",
                "print('ok')",
                "raise SystemExit(0)",
            ]
        ),
        encoding="utf-8",
    )
    return f"{Path(sys.executable).as_posix()} {script.as_posix()}"


def test_eval_run_cli_end_to_end(tmp_path: Path, capsys):
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(json.dumps({"task_id": "t0", "statement": "True", "imports": []}) + "\n", encoding="utf-8")
    llm_config = tmp_path / "llm_mock.json"
    llm_config.write_text(
        json.dumps(
            {
                "provider": "mock",
                "model": "mock-model",
                "cache_dir": str(tmp_path / "llm_cache"),
                "mock_responses": [
                    json.dumps({"proposals": [{"proposal_kind": "tactic", "lean_tactic": "simp"}]})
                ],
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "eval_a1"

    rc = main(
        [
            "eval-run",
            "--tasks", str(tasks),
            "--arm", "a1_raw_error",
            "--llm-config", str(llm_config),
            "--out-dir", str(out_dir),
            "--run-id", "r0",
            "--budget-calls", "1",
            "--lean-cmd", _fake_lean(tmp_path),
            "--task-timeout-s", "5",
            "--job-timeout-s", "5",
            "--queue-backend", "bulk",
        ]
    )

    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["arm"] == "a1_raw_error"
    assert printed["n_tasks"] == 1
    episodes = read_jsonl(out_dir / "episodes.jsonl")
    assert len(episodes) == 1
    assert episodes[0]["llm_calls"] == 1
    boundaries = read_jsonl(out_dir / "boundaries.jsonl")
    assert len(boundaries) == 1
    assert boundaries[0]["model_id"] == "mock-model"
    assert (out_dir / "prompt.sqlite").exists()
    assert (out_dir / "llm_calls.jsonl").exists()
    assert printed["prompt_store"]["counts"]["prompt_boundaries"] == 1
