import json
from pathlib import Path

from lean_rgc.schemas import write_jsonl
from lean_rgc.response_quotient import build_response_quotient_registry, project_actions_by_response_quotient
from lean_rgc.cli import main as cli_main


def test_response_quotient_registry_and_projection(tmp_path: Path):
    classes = tmp_path / "classes.jsonl"
    actions = tmp_path / "actions.jsonl"
    write_jsonl(classes, [
        {
            "class_id": "qact_demo",
            "representative_action_id": "simp",
            "member_action_ids": ["simp", "rw"],
            "mean_member_cosine": 0.99,
            "min_member_cosine": 0.98,
            "max_member_l2": 0.02,
            "mean_fingerprint": {"resp::s::goal.eq": 1.0},
        }
    ])
    write_jsonl(actions, [
        {"action_id": "simp", "tactic": "simp", "tactic_class": "simp"},
        {"action_id": "rw", "tactic": "rw [h]", "tactic_class": "rw"},
        {"action_id": "omega", "tactic": "omega", "tactic_class": "arith"},
    ])
    out = tmp_path / "rq"
    rep = build_response_quotient_registry(classes, actions_path=actions, out_dir=out)
    assert rep["n_nontrivial_classes"] == 1
    assert (out / "response_quotient_registry.json").exists()
    assert (out / "response_quotient_representatives.jsonl").exists()
    proj = tmp_path / "projected.jsonl"
    summ = project_actions_by_response_quotient(actions, out / "response_quotient_registry.json", proj)
    rows = [json.loads(x) for x in proj.read_text().splitlines() if x.strip()]
    assert summ["n_output_actions"] == 2  # simp/rw collapsed plus omega singleton
    assert any((r.get("metadata") or {}).get("response_quotient_class_id") == "qact_demo" for r in rows)


def test_response_quotient_cli(tmp_path: Path):
    cdir = tmp_path / "cong"
    cdir.mkdir()
    actions = tmp_path / "actions.jsonl"
    write_jsonl(cdir / "response_congruence_classes.jsonl", [
        {"class_id": "q", "representative_action_id": "a", "member_action_ids": ["a", "b"], "mean_member_cosine": 1.0}
    ])
    write_jsonl(actions, [{"action_id": "a", "tactic": "rfl"}, {"action_id": "b", "tactic": "rfl"}])
    out = tmp_path / "out"
    code = cli_main(["response-quotient-registry", "--congruence-dir", str(cdir), "--actions", str(actions), "--out", str(out)])
    assert code == 0
    assert (out / "response_quotient_registry.json").exists()
