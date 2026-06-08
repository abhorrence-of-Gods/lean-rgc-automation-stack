from lean_rgc.coker_synthesis import run_coker_synthesis
from lean_rgc.schemas import write_jsonl


def test_coker_synthesis_generates_seed_artifacts(tmp_path):
    responses = tmp_path / "responses.jsonl"
    out_actions = tmp_path / "coker_actions.jsonl"
    out_summary = tmp_path / "summary.json"
    out_profiles = tmp_path / "profiles.jsonl"
    out_archetypes = tmp_path / "archetypes.jsonl"
    out_atoms = tmp_path / "atoms.json"

    write_jsonl(responses, [
        {
            "task_id": "t0",
            "state_id": "s0",
            "target": "theorem t : True := by",
            "action_id": "simp0",
            "audit_status": "partial",
            "response_flat": [0.2, 0.0],
            "response_keys": ["carrier.unintroduced_forall", "carrier.missing_simp_lemma"],
            "response": {"carrier.unintroduced_forall": 0.2, "carrier.missing_simp_lemma": 0.0},
            "carrier_delta": {"unintroduced_forall": 0.0, "missing_simp_lemma": 0.3},
            "defect_before": {
                "goal": {},
                "type": {},
                "search": {},
                "carrier": {"unintroduced_forall": 1.0, "missing_simp_lemma": 0.5},
                "audit": {},
                "flat": [1.0, 0.5],
                "flat_keys": ["carrier.unintroduced_forall", "carrier.missing_simp_lemma"],
                "quotient_meta": {},
            },
            "action": {
                "action_id": "simp0",
                "tactic": "simp",
                "tactic_class": "simp",
                "carrier_tags": ["simp"],
                "cost_estimate": 1.0,
            },
        },
        {
            "task_id": "t0",
            "state_id": "s0",
            "target": "theorem t : True := by",
            "action_id": "intro0",
            "audit_status": "partial",
            "response_flat": [0.0, 0.1],
            "response_keys": ["carrier.unintroduced_forall", "carrier.missing_simp_lemma"],
            "response": {"carrier.unintroduced_forall": 0.0, "carrier.missing_simp_lemma": 0.1},
            "carrier_delta": {"unintroduced_forall": 0.2, "missing_simp_lemma": 0.0},
            "defect_before": {
                "goal": {},
                "type": {},
                "search": {},
                "carrier": {"unintroduced_forall": 1.0, "missing_simp_lemma": 0.5},
                "audit": {},
                "flat": [1.0, 0.5],
                "flat_keys": ["carrier.unintroduced_forall", "carrier.missing_simp_lemma"],
                "quotient_meta": {},
            },
            "action": {
                "action_id": "intro0",
                "tactic": "intros",
                "tactic_class": "intro",
                "carrier_tags": ["intro"],
                "cost_estimate": 1.0,
            },
        }
    ])

    summary = run_coker_synthesis(
        responses,
        out_actions=out_actions,
        out_profiles=out_profiles,
        out_archetypes=out_archetypes,
        out_atoms=out_atoms,
        out_summary=out_summary,
        margin_threshold=-10.0,
    )
    assert summary["n_response_rows"] == 2
    assert out_actions.exists()
    assert out_profiles.exists()
    assert out_archetypes.exists()
    assert out_atoms.exists()
    assert out_summary.exists()
