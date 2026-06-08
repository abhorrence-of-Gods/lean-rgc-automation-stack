from pathlib import Path
import json

from lean_rgc.schemas import write_jsonl
from lean_rgc.lineage import build_qgen_acceptance_lineage


def test_qgen_acceptance_lineage_augments_audit_and_acceptance(tmp_path: Path):
    qdir = tmp_path / "qgen"
    qdir.mkdir()
    (qdir / "qgen_report.json").write_text(json.dumps({"projection": {"residual_norm": 1.0, "support_value": 0.2}}), encoding="utf-8")
    action = {
        "action_id": "a1",
        "tactic": "simp",
        "tactic_class": "qgen",
        "metadata": {"qgen": {"parent_residual_keys": ["goal.eq"], "lineage_id": "qgen_x"}},
    }
    write_jsonl(qdir / "qgen_context_candidates.jsonl", [action])
    write_jsonl(qdir / "qgen_defect_atoms.jsonl", [{"atom_id": "qgen_residual_goal_eq", "detector": "qgen"}])
    write_jsonl(qdir / "qgen_carrier_incidence.jsonl", [])
    write_jsonl(qdir / "qgen_failure_signatures.jsonl", [])
    accepted = tmp_path / "qgen_accepted_actions.jsonl"
    write_jsonl(accepted, [action])
    audit = tmp_path / "qgen_audit_responses.jsonl"
    write_jsonl(audit, [{"task_id": "t1", "state_id": "s1", "action": action, "audit_status": "success", "response": {"goal.unsolved": 1.0}}])
    rows = tmp_path / "qgen_acceptance_rows.jsonl"
    write_jsonl(rows, [{"action": action, "accepted": True, "robust_margin": 0.5}])
    out = tmp_path / "lineage.json"
    graph = build_qgen_acceptance_lineage(qdir, accepted_actions=accepted, acceptance_rows=rows, audit_responses=audit, out=out)
    assert out.exists()
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "accepted_context" in kinds
    assert "micro_audit_response" in kinds
    assert "coker_acceptance_record" in kinds
    assert graph["summary"]["n_accepted_contexts"] == 1

