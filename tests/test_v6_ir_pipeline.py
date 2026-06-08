from lean_rgc.schemas import LeanTask, ProofState
from lean_rgc.proof_ir import parse_proof_state_ir
from lean_rgc.carrier_acceptance import context_to_actions
from lean_rgc.carrier import CarrierGenerator


def test_proof_ir_forall_target():
    task = LeanTask(task_id="t", imports=[], statement="∀ n : Nat, n = n")
    ir = parse_proof_state_ir(task=task, state=ProofState.from_task(task))
    assert ir.goals
    assert ir.goals[0].target_head in {"forall", "eq"}
    assert ir.metadata["n_goals"] >= 1


def test_carrier_context_to_actions():
    ctx = CarrierGenerator().generate(["unintroduced_forall"], "⊢ ∀ n : Nat, n = n")[0]
    acts = context_to_actions(ctx, prefix="test")
    assert any("intros" in a.tactic for a in acts)
    assert all("generated" in a.carrier_tags for a in acts)
