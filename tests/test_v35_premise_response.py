from pathlib import Path
import json

from lean_rgc.schemas import write_jsonl, read_jsonl
from lean_rgc.premise_response import (
    build_premise_response_registry,
    retrieve_premise_responses,
    write_premise_retrieved_actions,
    mine_premise_quotient,
)
from lean_rgc.cli import main as cli_main


def _fixture(tmp_path: Path):
    actions = tmp_path / "actions.jsonl"
    responses = tmp_path / "responses.jsonl"
    write_jsonl(actions, [
        {
            "action_id": "a_simp_add",
            "tactic": "simp [Nat.add_assoc]",
            "tactic_class": "simp",
            "carrier_tags": ["premise", "simp"],
            "cost_estimate": 0.4,
            "metadata": {"premise": {"name": "Nat.add_assoc", "statement": "..."}},
        },
        {
            "action_id": "a_rw_add",
            "tactic": "rw [Nat.add_assoc]",
            "tactic_class": "rewrite",
            "carrier_tags": ["premise", "rewrite"],
            "cost_estimate": 0.5,
            "metadata": {"premise": {"name": "Nat.add_assoc", "statement": "..."}},
        },
    ])
    write_jsonl(responses, [
        {
            "state_id": "s1",
            "action_id": "a_simp_add",
            "response": {"goal.eq": 0.8, "search.tail": 0.1},
            "response_flat": [0.8, 0.1],
            "response_keys": ["goal.eq", "search.tail"],
            "audit_status": "success",
            "carrier_delta": {"missing_simp_lemma": 0.3},
            "defect_before": {"flat": [1.0], "flat_keys": ["goal.eq"]},
            "defect_after": {"flat": [0.2], "flat_keys": ["goal.eq"]},
        },
        {
            "state_id": "s2",
            "action_id": "a_simp_add",
            "response": {"goal.eq": 0.6, "search.tail": 0.0},
            "response_flat": [0.6, 0.0],
            "response_keys": ["goal.eq", "search.tail"],
            "audit_status": "partial",
            "carrier_delta": {"missing_simp_lemma": 0.1},
            "defect_before": {"flat": [1.0], "flat_keys": ["goal.eq"]},
            "defect_after": {"flat": [0.4], "flat_keys": ["goal.eq"]},
        },
        {
            "state_id": "s1",
            "action_id": "a_rw_add",
            "response": {"goal.eq": 0.2, "search.tail": 0.0},
            "response_flat": [0.2, 0.0],
            "response_keys": ["goal.eq", "search.tail"],
            "audit_status": "fail",
            "carrier_delta": {"missing_simp_lemma": 0.05},
            "defect_before": {"flat": [1.0], "flat_keys": ["goal.eq"]},
            "defect_after": {"flat": [0.8], "flat_keys": ["goal.eq"]},
        },
    ])
    return actions, responses


def test_premise_response_registry_retrieve_and_quotient(tmp_path):
    actions, responses = _fixture(tmp_path)
    registry = tmp_path / "premise_response_registry.jsonl"
    summary = tmp_path / "summary.json"
    meta = build_premise_response_registry(actions_path=actions, responses_path=responses, out=registry, summary_out=summary)
    rows = read_jsonl(registry)
    assert meta["n_premise_use_rows"] >= 2
    assert any(r["premise_id"] == "Nat.add_assoc" for r in rows)
    assert any(r["response_embedding"].get("goal.eq", 0) > 0.5 for r in rows)

    retrieved = tmp_path / "retrieved.jsonl"
    retrieve_premise_responses(
        registry_path=registry,
        out=retrieved,
        response_normal={"goal.eq": 1.0},
        carrier_normal={"missing_simp_lemma": 0.2},
        top_k=2,
    )
    rr = read_jsonl(retrieved)
    assert rr and rr[0]["score"] >= rr[-1]["score"]
    assert rr[0]["candidate_action"]["metadata"]["source"] == "premise_response_retrieval_v35"

    out_actions = tmp_path / "retrieved_actions.jsonl"
    am = write_premise_retrieved_actions(retrieved_path=retrieved, out=out_actions)
    assert am["n_actions"] >= 1

    qdir = tmp_path / "pq"
    qm = mine_premise_quotient(registry_path=registry, out_dir=qdir, cosine_threshold=0.5, distance_threshold=10.0)
    assert qm["n_classes"] >= 1
    assert (qdir / "premise_quotient_classes.jsonl").exists()


def test_premise_response_cli(tmp_path):
    actions, responses = _fixture(tmp_path)
    registry = tmp_path / "reg.jsonl"
    rc = cli_main(["premise-response-registry", "--actions", str(actions), "--responses", str(responses), "--out", str(registry)])
    assert rc == 0 and registry.exists()
    retrieved = tmp_path / "ret.jsonl"
    actions_out = tmp_path / "ret_actions.jsonl"
    rc = cli_main([
        "premise-response-retrieve",
        "--registry", str(registry),
        "--response-normal", '{"goal.eq": 1.0}',
        "--out", str(retrieved),
        "--out-actions", str(actions_out),
        "--top-k", "1",
    ])
    assert rc == 0
    assert len(read_jsonl(actions_out)) == 1
