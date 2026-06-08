from lean_rgc.schemas import LeanTask, ProofState, TacticAction
from lean_rgc.executor import LeanExecutor, LeanExecutorConfig
from lean_rgc.defects import ProofDefectExtractor
from lean_rgc.candidates import TacticCandidateGenerator
from lean_rgc.carrier import LeanCarrierAlgebra, CarrierGenerator
from lean_rgc.gamma import GammaAuditor
from lean_rgc.quotient import ResponseQuotientDiscovery
import numpy as np


def test_dry_audit_and_response():
    task = LeanTask(task_id="t", statement="∀ n : Nat, n + 0 = n")
    action = TacticAction(action_id="simp", tactic="simp", tactic_class="simp", carrier_tags=["simp"])
    ex = LeanExecutor(LeanExecutorConfig(dry_run=True))
    rec = ex.run_tactic(task, action)
    ext = ProofDefectExtractor()
    before = ext.extract(ProofState.from_task(task))
    after = ext.extract(rec.after_state, rec)
    resp, flat, keys = ext.response(before, after)
    assert len(flat) == len(keys)
    assert rec.status in {"success", "dry_run"}


def test_carrier_generator():
    cg = CarrierGenerator()
    out = cg.generate(["missing_induction_scheme", "missing_premise_family"], "∀ n : Nat, P n")
    assert len(out) == 2


def test_gamma_audit():
    ga = GammaAuditor()
    D = np.array([1.0, 2.0])
    R = np.array([0.2, 0.1])
    N = np.array([0.7, 1.7])
    rep = ga.audit(D, R, N, np.eye(2), horizon=2)
    assert rep.cocycle_resid_norm >= 0


def test_quotient_discovery():
    q = ResponseQuotientDiscovery(tolerance=0.2)
    comps = q.discover(["a", "b", "c"], np.array([[1, 0], [1.05, 0.0], [0, 1]]))
    assert len(comps) == 2


def test_response_model_and_prediction(tmp_path):
    from lean_rgc.response_model import train_response_model, ResponseModel
    from lean_rgc.schemas import write_jsonl
    rows = []
    for aid, vec in [("simp", [1.0, 0.0]), ("simp", [0.8, 0.1]), ("rw", [0.0, 1.0])]:
        rows.append({"state_id":"s", "action_id":aid, "response":{}, "response_flat":vec, "response_keys":["a","b"], "defect_before":{}, "defect_after":{}, "audit_status":"success"})
    resp = tmp_path / "responses.jsonl"
    write_jsonl(resp, rows)
    actions = tmp_path / "actions.jsonl"
    write_jsonl(actions, [{"action_id":"simp", "tactic":"simp", "tactic_class":"simp", "carrier_tags":["simp"]}, {"action_id":"rw", "tactic":"rw [h]", "tactic_class":"rewrite", "carrier_tags":["rewrite"]}])
    out = tmp_path / "model.json"
    model = train_response_model(resp, actions, out)
    pred = model.predict(TacticAction(action_id="simp", tactic="simp", tactic_class="simp", carrier_tags=["simp"]))
    assert len(pred.mean) == 2
    loaded = ResponseModel.load(out)
    assert loaded.response_keys == ["a", "b"]


def test_trajectory_runner_dry():
    from lean_rgc.trajectory import LeanTrajectoryRunner, TrajectoryRunnerConfig
    task = LeanTask(task_id="t", statement="∀ n : Nat, n + 0 = n")
    ex = LeanExecutor(LeanExecutorConfig(dry_run=True))
    runner = LeanTrajectoryRunner(ex, config=TrajectoryRunnerConfig(max_steps=2, max_candidates=4))
    rec = runner.run_task(task)
    assert len(rec.steps) >= 1
