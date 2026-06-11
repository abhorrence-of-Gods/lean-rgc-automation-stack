import json
from pathlib import Path

from lean_rgc.grammar_extension_demand import build_grammar_extension_demands
from lean_rgc.schemas import read_jsonl


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _audit_row(candidate_id: str, *, relaxed: float = 0.7, hard: float = 0.0, coverage: str | None = "full") -> dict:
    row = {
        "candidate_id": candidate_id,
        "problem_id": f"p_{candidate_id}",
        "relaxed_score": relaxed,
        "audited_score": hard,
        "hardening_gap": max(0.0, relaxed - hard),
    }
    if coverage is not None:
        row["audit_coverage"] = coverage
    return row


def _candidate(candidate_id: str, species: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "relaxed_object": {
            "support": [
                {"species_id": species, "weight": 0.6},
                {"species_id": "action_distribution", "weight": 0.4},
            ]
        },
    }


def test_demands_only_from_fully_audited_trigger_cases(tmp_path: Path):
    audit = tmp_path / "crg_audit_rows.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    attempts = tmp_path / "attempts.jsonl"
    out = tmp_path / "demands.jsonl"
    _write_jsonl(
        audit,
        [
            _audit_row("c_full"),
            _audit_row("c_skipped", coverage="none"),
            _audit_row("c_realized", hard=0.5),
        ],
    )
    _write_jsonl(candidates, [_candidate("c_full", "context_portfolio")])
    _write_jsonl(attempts, [{"candidate_id": "c_full", "hardening_status": "failed", "hard_candidates": []}])

    summary = build_grammar_extension_demands(
        crg_audit_rows_path=audit,
        out=out,
        candidates_path=candidates,
        hardening_attempts_path=attempts,
    )
    demands = read_jsonl(out)

    assert summary["n_trigger_cases"] == 1
    assert summary["n_excluded_underaudited"] == 1
    assert summary["n_demands"] == 1
    demand = demands[0]
    assert demand["dominant_species"] == "context_portfolio"
    assert demand["missing_capability"]["kind"] == "decoder"
    assert demand["evidence"]["candidate_ids"] == ["c_full"]
    assert demand["canonical_status"] == "grammar_demand_witness_not_canonical"


def test_decoded_attempt_demands_tactic_template(tmp_path: Path):
    audit = tmp_path / "crg_audit_rows.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    attempts = tmp_path / "attempts.jsonl"
    out = tmp_path / "demands.jsonl"
    _write_jsonl(audit, [_audit_row("c1")])
    _write_jsonl(candidates, [_candidate("c1", "gamma_policy")])
    _write_jsonl(
        attempts,
        [{"candidate_id": "c1", "hardening_status": "decoded", "hard_candidates": [{"action_id": "h1"}]}],
    )

    build_grammar_extension_demands(
        crg_audit_rows_path=audit,
        out=out,
        candidates_path=candidates,
        hardening_attempts_path=attempts,
    )
    demand = read_jsonl(out)[0]

    assert demand["missing_capability"] == {
        "kind": "tactic_template",
        "name": "gamma_policy_tactic_template",
    }


def test_cross_run_merge_dedups_candidates_and_accumulates(tmp_path: Path):
    out = tmp_path / "demands.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    _write_jsonl(candidates, [_candidate("c1", "context_portfolio"), _candidate("c2", "context_portfolio")])

    audit_run1 = tmp_path / "audit_run1.jsonl"
    _write_jsonl(audit_run1, [_audit_row("c1", relaxed=0.5)])
    build_grammar_extension_demands(crg_audit_rows_path=audit_run1, out=out, candidates_path=candidates)
    first = read_jsonl(out)[0]

    audit_run2 = tmp_path / "audit_run2.jsonl"
    _write_jsonl(audit_run2, [_audit_row("c1", relaxed=0.5), _audit_row("c2", relaxed=0.3)])
    build_grammar_extension_demands(crg_audit_rows_path=audit_run2, out=out, candidates_path=candidates)
    demands = read_jsonl(out)

    assert len(demands) == 1
    merged = demands[0]
    assert merged["demand_id"] == first["demand_id"]
    assert merged["evidence"]["n_cases"] == 2
    assert sorted(merged["evidence"]["candidate_ids"]) == ["c1", "c2"]
    assert abs(merged["priority"] - 0.8) < 1e-9


def test_demands_sorted_by_priority(tmp_path: Path):
    audit = tmp_path / "crg_audit_rows.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    out = tmp_path / "demands.jsonl"
    _write_jsonl(audit, [_audit_row("c_small", relaxed=0.2), _audit_row("c_big", relaxed=0.9)])
    _write_jsonl(
        candidates,
        [_candidate("c_small", "premise_distribution"), _candidate("c_big", "context_portfolio")],
    )

    summary = build_grammar_extension_demands(
        crg_audit_rows_path=audit,
        out=out,
        candidates_path=candidates,
        summary_out=tmp_path / "summary.json",
    )
    demands = read_jsonl(out)

    assert [d["dominant_species"] for d in demands] == ["context_portfolio", "premise_distribution"]
    assert summary["top_demands"][0]["dominant_species"] == "context_portfolio"
    assert (tmp_path / "summary.json").exists()
