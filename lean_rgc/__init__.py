"""Lean-RGC automation stack."""
from .schemas import (
    LeanTask, ProofState, TacticAction, AuditRecord, DefectVector,
    ResponseRecord, RGCSelection, TrajectoryRecord, TrajectoryStep,
)
from .executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor
from .candidates import TacticCandidateGenerator, CandidateGeneratorConfig
from .goal_shape import GoalShape, HypInfo, parse_goal_shape, shape_atoms, GoalShapeParser
from .carrier_normalizer import CarrierNormalizer, ExposureCandidate, compose_exposure_actions
from .carrier_exposure import StateDependentCandidateGenerator
from .defect_registry import DefectAtom, DefectRegistry, seed_defect_registry
from .defect_miner import AutoDefectMiner, CandidateAtomScore
from .auto_defects import AutoDefectExtractor
from .proof_ir import ProofStateIR, GoalIR, HypothesisIR, parse_proof_state_ir
from .carrier import LeanCarrierAlgebra, CarrierGenerator
from .gamma import GammaAuditor
from .quotient import ResponseQuotientDiscovery
from .selector import RGCTacticSelector, SelectorConfig
from .cache import AuditCache
from .response_model import ResponseModel, ResponseModelConfig, ResponsePrediction
from .trajectory import LeanTrajectoryRunner, TrajectoryRunnerConfig
from .registry_promotion import promote_registry_from_audits, promote_registry_file, RegistryPromotionReport
from .premise_index import PremiseIndex, PremiseDoc, PremiseHit, build_premise_index
from .ir_defects import defect_from_ir_row, ir_defects_file
try:
    from .coker import project_onto_response_cone, coker_margin, ConeProjectionReport
except Exception:  # pragma: no cover
    project_onto_response_cone = None  # type: ignore
    coker_margin = None  # type: ignore
    ConeProjectionReport = None  # type: ignore

__all__ = [
    "LeanTask", "ProofState", "TacticAction", "AuditRecord", "DefectVector", "ResponseRecord", "RGCSelection",
    "TrajectoryRecord", "TrajectoryStep", "LeanExecutor", "LeanExecutorConfig", "ProofDefectExtractor",
    "TacticCandidateGenerator", "CandidateGeneratorConfig", "GoalShape", "HypInfo", "GoalShapeParser", "parse_goal_shape", "shape_atoms",
    "CarrierNormalizer", "ExposureCandidate", "compose_exposure_actions", "StateDependentCandidateGenerator",
    "DefectAtom", "DefectRegistry", "seed_defect_registry", "AutoDefectMiner", "CandidateAtomScore", "AutoDefectExtractor", "ProofStateIR", "GoalIR", "HypothesisIR", "parse_proof_state_ir",
    "LeanCarrierAlgebra", "CarrierGenerator", "GammaAuditor", "ResponseQuotientDiscovery", "RGCTacticSelector", "SelectorConfig",
    "AuditCache", "ResponseModel", "ResponseModelConfig", "ResponsePrediction", "LeanTrajectoryRunner", "TrajectoryRunnerConfig",
    "project_onto_response_cone", "coker_margin", "ConeProjectionReport",
    "promote_registry_from_audits", "promote_registry_file", "RegistryPromotionReport",
    "PremiseIndex", "PremiseDoc", "PremiseHit", "build_premise_index",
    "defect_from_ir_row", "ir_defects_file", "summarize_action_groups", "write_action_group_report", "exposure_actions_for_tasks", "summarize_exposure_audit",
    "FrontierAuditor", "expose_frontier_files",
    "KernelGoalStateServer", "KernelGoalStateServerConfig", "normalize_kernel_state_v1", "structural_kernel_response",
    "write_primitive_observables", "build_bounded_transcripts", "build_feature_closure",
    "select_features_for_dual_obstructions", "build_dost_auto_plan", "compile_experiment_from_auto_plan",
    "build_dost_audit_reports", "run_dost_automation_stack",
]


from .registry_acceptance import RegistryCokerAcceptor, run_registry_acceptance

from .candidate_acceptance import accept_candidates_file, promote_registry_from_acceptance, accept_candidate_rows, summarize_acceptance

from .project_harvest import HarvestedDeclaration, harvest_lean_project, parse_lean_file
from .sharding import shard_jsonl, merge_jsonl

from .frontier import build_frontiers, exposure_actions_for_task, FrontierAuditor, expose_frontier_files

from .action_analysis import summarize_action_groups, write_action_group_report
from .exposure_audit import exposure_actions_for_tasks, summarize_exposure_audit

from .failure_signatures import FailureSignatureMiner, mine_failure_signatures
from .proof_replay import ProofScript, scripts_from_trajectories, replay_proof_scripts, export_proof_file

from .structured_state import StructuredProofState, GoalASTNode, LocalContextGraph, MetaVarGraph, TypeclassObligationGraph, extract_structured_state
from .kernel_state import KernelGoalStateServer, KernelGoalStateServerConfig, normalize_kernel_state_v1, structural_kernel_response
from .dost_automation import (
    write_primitive_observables,
    build_bounded_transcripts,
    build_feature_closure,
    select_features_for_dual_obstructions,
    build_dost_auto_plan,
    compile_experiment_from_auto_plan,
    build_dost_audit_reports,
    run_dost_automation_stack,
)
