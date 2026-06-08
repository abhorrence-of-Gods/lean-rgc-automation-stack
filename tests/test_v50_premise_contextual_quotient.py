from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.premise_contextual_quotient import (
    build_premise_contextual_fingerprints,
    generate_premise_contextual_candidates,
    mine_premise_contextual_quotient,
    premise_quotient_retrieved_actions,
    retrieve_premise_quotient_classes,
    validate_premise_contextual_quotient,
)
from lean_rgc.schemas import read_jsonl, write_jsonl


def _fixture(tmp_path: Path):
    premises = tmp_path / "premises.jsonl"
    contexts = tmp_path / "contexts.jsonl"
    write_jsonl(
        premises,
        [
            {
                "action_id": "p_add_zero",
                "tactic": "simp [Nat.add_zero]",
                "tactic_class": "simp",
                "carrier_tags": ["premise", "simp"],
                "metadata": {"premise": {"name": "Nat.add_zero"}},
            },
            {
                "action_id": "p_zero_add",
                "tactic": "simp [Nat.zero_add]",
                "tactic_class": "simp",
                "carrier_tags": ["premise", "simp"],
                "metadata": {"premise": {"name": "Nat.zero_add"}},
            },
            {
                "action_id": "p_assoc",
                "tactic": "rw [Nat.add_assoc]",
                "tactic_class": "rewrite",
                "carrier_tags": ["premise", "rewrite"],
                "metadata": {"premise": {"name": "Nat.add_assoc"}},
            },
        ],
    )
    write_jsonl(
        contexts,
        [
            {
                "action_id": "ctx_simp",
                "tactic": "simp",
                "tactic_class": "simp",
                "carrier_tags": ["simp"],
            }
        ],
    )
    return premises, contexts


def _build_responses(candidates: Path, responses: Path):
    rows = read_jsonl(candidates)
    out = []
    for row in rows:
        meta = row.get("metadata") or {}
        pre = meta.get("pre_context_id")
        post = meta.get("post_context_id")
        if post != "__id__":
            continue
        baseline = 0.20 if pre == "ctx_simp" else 0.10
        if meta.get("is_contextual_baseline"):
            out.append(
                {
                    "state_id": "s1",
                    "action_id": row["action_id"],
                    "audit_status": "success",
                    "response": {"goal.eq": baseline, "search.tail": 0.0},
                    "carrier_delta": {"missing_simp": 0.0},
                    "elapsed_ms": 3,
                    "heartbeats": 10,
                }
            )
            continue
        premise = meta.get("premise_id")
        if premise == "Nat.add_zero":
            response = {"goal.eq": baseline + 0.60, "search.tail": 0.0}
            carrier = {"missing_simp": 0.10}
        elif premise == "Nat.zero_add":
            response = {"goal.eq": baseline + 0.61, "search.tail": 0.0}
            carrier = {"missing_simp": 0.11}
        else:
            response = {"goal.eq": baseline, "search.tail": 0.70}
            carrier = {"missing_simp": -0.40}
        out.append(
            {
                "state_id": "s1",
                "action_id": row["action_id"],
                "audit_status": "success",
                "response": response,
                "carrier_delta": carrier,
                "elapsed_ms": 5,
                "heartbeats": 20,
            }
        )
    write_jsonl(responses, out)


def test_premise_contextual_fingerprint_uses_baseline_increment(tmp_path):
    premises, contexts = _fixture(tmp_path)
    candidates = tmp_path / "premise_contextual_candidates.jsonl"
    summary = generate_premise_contextual_candidates(
        premises,
        candidates,
        contexts_path=contexts,
        max_left=1,
        max_right=0,
        include_identity=True,
        include_baselines=True,
    )
    assert summary["n_baseline_actions"] == 2
    assert summary["n_premise_contextual_actions"] == 6

    responses = tmp_path / "responses.jsonl"
    _build_responses(candidates, responses)
    fingerprints = tmp_path / "premise_contextual_fingerprints.jsonl"
    build_premise_contextual_fingerprints(
        responses_path=responses,
        actions_path=candidates,
        out=fingerprints,
        baseline_required=True,
    )
    rows = read_jsonl(fingerprints)
    add_zero = next(r for r in rows if r["premise_id"] == "Nat.add_zero")
    key = "ctx:s1|pre:__id__|post:__id__::resp::goal.eq"
    assert abs(add_zero["fingerprint"][key] - 0.60) < 1e-9
    assert add_zero["baseline_coverage"]["baseline_subtracted"] == 2


def test_premise_contextual_quotient_validate_and_retrieve(tmp_path):
    premises, contexts = _fixture(tmp_path)
    candidates = tmp_path / "candidates.jsonl"
    generate_premise_contextual_candidates(premises, candidates, contexts_path=contexts, max_left=1, max_right=0)
    responses = tmp_path / "responses.jsonl"
    _build_responses(candidates, responses)
    fingerprints = tmp_path / "fingerprints.jsonl"
    build_premise_contextual_fingerprints(responses_path=responses, actions_path=candidates, out=fingerprints, baseline_required=True)

    qdir = tmp_path / "pq"
    mine_premise_contextual_quotient(
        fingerprints_path=fingerprints,
        out_dir=qdir,
        epsilon=0.05,
        cosine_threshold=0.995,
        domain_jaccard_threshold=1.0,
    )
    classes = read_jsonl(qdir / "premise_quotient_classes.jsonl")
    assert any(len(c["member_premise_use_ids"]) == 2 for c in classes)
    assert any(c["premise_ids"] == ["Nat.add_assoc"] for c in classes)

    rows_out = qdir / "premise_quotient_validation_rows.jsonl"
    report_out = qdir / "premise_quotient_validation_report.json"
    validate_premise_contextual_quotient(
        fingerprints_path=fingerprints,
        classes_path=qdir / "premise_quotient_classes.jsonl",
        out_rows=rows_out,
        out_report=report_out,
        epsilon_holdout=0.10,
        separation_delta=0.01,
    )
    assert rows_out.exists() and report_out.exists()

    retrieved = qdir / "premise_quotient_retrieved_actions.jsonl"
    retrieve_premise_quotient_classes(
        classes_path=qdir / "premise_quotient_classes.jsonl",
        out=retrieved,
        response_normal={"goal.eq": 1.0},
        top_k=1,
    )
    rr = read_jsonl(retrieved)
    assert rr[0]["score"] > 0.0
    assert rr[0]["candidate_action"]["metadata"]["source"] == "premise_contextual_quotient_retrieval"
    actions = qdir / "premise_quotient_actions.jsonl"
    meta = premise_quotient_retrieved_actions(retrieved_path=retrieved, out=actions)
    assert meta["n_actions"] == 1


def test_premise_contextual_cli(tmp_path):
    premises, contexts = _fixture(tmp_path)
    candidates = tmp_path / "cli_candidates.jsonl"
    rc = cli_main(
        [
            "premise-contextual-generate",
            "--premise-actions",
            str(premises),
            "--contexts",
            str(contexts),
            "--out",
            str(candidates),
            "--max-left",
            "1",
            "--max-right",
            "0",
        ]
    )
    assert rc == 0 and candidates.exists()
    responses = tmp_path / "cli_responses.jsonl"
    _build_responses(candidates, responses)
    fingerprints = tmp_path / "cli_fingerprints.jsonl"
    rc = cli_main(
        [
            "premise-contextual-fingerprints",
            "--responses",
            str(responses),
            "--actions",
            str(candidates),
            "--out",
            str(fingerprints),
            "--baseline-required",
        ]
    )
    assert rc == 0 and fingerprints.exists()
    qdir = tmp_path / "cli_q"
    rc = cli_main(
        [
            "premise-contextual-mine",
            "--fingerprints",
            str(fingerprints),
            "--out",
            str(qdir),
            "--epsilon",
            "0.05",
            "--cosine-threshold",
            "0.995",
        ]
    )
    assert rc == 0 and (qdir / "premise_quotient_classes.jsonl").exists()
