from lean_rgc.schemas import LeanTask, ProofState
from lean_rgc.goal_shape import GoalShapeParser
from lean_rgc.carrier_exposure import StateDependentCandidateGenerator, CarrierNormalizer
from lean_rgc.defect_miner import AutoDefectMiner


def test_goal_shape_forall_and_candidates():
    task = LeanTask(task_id="t", imports=[], statement="∀ n : Nat, n = n")
    state = ProofState.from_task(task)
    shape = GoalShapeParser().parse(task, state)
    assert shape.has_forall
    cands = StateDependentCandidateGenerator().candidates(task, state, max_candidates=20)
    tactics = [c.tactic for c in cands]
    assert any("intros" in t and "rfl" in t for t in tactics)
    assert any(c.metadata.get("prefix_kind") == "nonbranching_intro" for c in cands)


def test_and_comm_exposure_constructor():
    task = LeanTask(task_id="and", imports=[], statement="∀ p q : Prop, p ∧ q → q ∧ p")
    cands = StateDependentCandidateGenerator().candidates(task, ProofState.from_task(task), max_candidates=50)
    assert any("intros" in c.tactic and "constructor" in c.tactic for c in cands)


def test_auto_defect_miner_detects_forall_rfl_failure():
    rows = [{
        "state_id": "s", "action_id": "rfl", "status": "fail",
        "messages": ["rfl failed", "Expected the goal to be a binary relation", "⊢ ∀ (n : Nat), n = n"],
        "response_flat": [0.0, -1.0, 0.5],
        "action": {"tactic": "rfl"},
    } for _ in range(3)]
    miner = AutoDefectMiner(min_support=2, response_threshold=0.0, stability_threshold=0.0)
    scores = miner.score(rows)
    reg = miner.promote(scores, min_support=2, min_response_contrast=-1e9, min_stability=0.0)
    atoms = {a.atom_id: a.status for a in reg.atoms}
    assert atoms.get("unintroduced_forall") == "active"
