from pathlib import Path
from lean_rgc.failure_signatures import FailureSignatureMiner, mine_failure_signatures
from lean_rgc.schemas import write_jsonl, read_jsonl


def test_failure_signature_miner_generates_intro_actions(tmp_path: Path):
    audits = [
        {
            "task_id": "t1",
            "state_id": "s1",
            "action_id": "a_rfl",
            "target": "∀ (n : Nat), n = n",
            "status": "fail",
            "messages": ["rfl failed\nExpected the goal to be a binary relation\n⊢ ∀ (n : Nat), n = n"],
            "action": {"action_id": "a_rfl", "tactic": "rfl"},
        }
    ]
    responses = [
        {
            "task_id": "t1",
            "state_id": "s1",
            "action_id": "a_rfl",
            "response_flat": [0.0, -1.0],
            "carrier_delta": {"unintroduced_forall": 0.0},
        }
    ]
    miner = FailureSignatureMiner(min_support=1)
    res = miner.mine(audits, responses)
    assert res.signatures
    assert any(s.kind == "rfl_before_intro" for s in res.signatures)
    assert any("intros\nrfl" == a["tactic"] for a in res.actions)
    assert all(a.get("task_id") == "t1" for a in res.actions)


def test_failure_signatures_cli_helper_writes_files(tmp_path: Path):
    audits_path = tmp_path / "audit.jsonl"
    responses_path = tmp_path / "responses.jsonl"
    out = tmp_path / "signatures.jsonl"
    actions_out = tmp_path / "actions.jsonl"
    summary_out = tmp_path / "summary.json"
    write_jsonl(audits_path, [{"task_id": "t", "state_id": "s", "action_id": "a", "target": "∀ n : Nat, n = n", "status": "fail", "messages": ["rfl failed ⊢ ∀ n : Nat, n = n"], "action": {"action_id": "a", "tactic": "rfl"}}])
    write_jsonl(responses_path, [{"task_id": "t", "state_id": "s", "action_id": "a", "response_flat": [1.0]}])
    res = mine_failure_signatures(audits_path, out, responses=responses_path, actions_out=actions_out, summary_out=summary_out)
    assert out.exists() and actions_out.exists() and summary_out.exists()
    assert len(read_jsonl(out)) == len(res.signatures)
    assert len(read_jsonl(actions_out)) == len(res.actions)
