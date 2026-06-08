from pathlib import Path

from lean_rgc.qgen import qgen_from_files, CokerDrivenGenerator
from lean_rgc.schemas import write_jsonl


def test_qgen_from_response_rows(tmp_path: Path):
    rows = [
        {
            "state_id": "s1",
            "task_id": "t1",
            "action_id": "simp",
            "response_flat": [0.8, 0.0, 0.1],
            "response_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"],
            "defect_before": {"flat": [1.0, 0.5, 0.2], "flat_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"]},
            "defect_after": {"flat": [0.2, 0.5, 0.1], "flat_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"]},
            "carrier_delta": {"missing_simp_lemma": 0.1},
            "audit_status": "success",
            "action": {"action_id": "simp", "tactic": "simp", "tactic_class": "simp", "carrier_tags": ["simp"], "cost_estimate": 1.0},
        },
        {
            "state_id": "s2",
            "task_id": "t2",
            "action_id": "intro",
            "response_flat": [0.0, 0.1, 0.0],
            "response_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"],
            "defect_before": {"flat": [1.0, 0.6, 0.3], "flat_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"]},
            "defect_after": {"flat": [1.0, 0.5, 0.3], "flat_keys": ["goal.eq", "carrier.missing_simp_lemma", "search.tail"]},
            "carrier_delta": {"missing_simp_lemma": -0.2},
            "audit_status": "partial",
            "action": {"action_id": "intro", "tactic": "intro", "tactic_class": "intro", "carrier_tags": ["intro"], "cost_estimate": 1.0},
        },
    ]
    resp = tmp_path / "responses.jsonl"
    write_jsonl(resp, rows)
    out = tmp_path / "qgen"
    rep = qgen_from_files(resp, out_dir=out, top_defects=3, top_contexts=3)
    assert rep.summary["n_response_rows"] == 2
    assert (out / "qgen_report.json").exists()
    assert (out / "qgen_defect_registry.json").exists()
    assert (out / "qgen_accepted_actions.jsonl").exists()
    assert isinstance(rep.generated_defect_atoms, list)
    assert isinstance(rep.context_candidates, list)


def test_qgen_empty_rows():
    rep, D, R, keys, rows = CokerDrivenGenerator().project([])
    assert rep.residual_norm == 0.0
    assert len(rows) == 0
