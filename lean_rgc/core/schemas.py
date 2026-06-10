from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_CONTRACT_VERSION = "lean-rgc.production-metadata-contract.v1"
PRODUCTION_METADATA_FIELDS = ("schema_version", "run_id", "parent_ids", "payload_json")
PRODUCTION_RECORD_TYPES = (
    "run",
    "artifact",
    "task",
    "action",
    "response",
    "repair_face",
    "crg_problem",
    "relaxed_candidate",
    "hardening_attempt",
    "lineage_edge",
)


@dataclass
class _Record:
    schema_version: str
    run_id: str
    parent_ids: list[str] = field(default_factory=list)
    payload_json: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunRecord(_Record):
    run_dir: str = ""
    status: str = "created"
    git_sha: str = ""
    config_hash: str = ""


@dataclass
class ArtifactRecord(_Record):
    artifact_id: str = ""
    artifact_type: str = ""
    uri: str = ""
    sha256: str = ""
    n_rows: int = 0


@dataclass
class TaskRecord(_Record):
    task_id: str = ""
    source: str = ""
    goal_hash: str = ""
    import_mode: str = ""


@dataclass
class ActionRecord(_Record):
    action_id: str = ""
    action_kind: str = ""
    tactic_hash: str = ""
    source: str = ""
    canonical_status: str = ""


@dataclass
class ResponseRecord(_Record):
    response_id: str = ""
    task_id: str = ""
    action_id: str = ""
    status: str = ""
    elapsed_ms: float = 0.0
    state_before_id: str = ""
    state_after_id: str = ""


@dataclass
class RepairFaceRecord(_Record):
    face_id: str = ""
    obstruction_id: str = ""
    parent_face_id: str = ""
    canonical_status: str = ""


@dataclass
class CRGProblemRecord(_Record):
    problem_id: str = ""
    face_id: str = ""
    obstruction_id: str = ""
    canonical_status: str = ""


@dataclass
class RelaxedCandidateRecord(_Record):
    candidate_id: str = ""
    problem_id: str = ""
    species: str = ""
    relaxed_score: float = 0.0
    cost: float = 0.0
    audit_risk: float = 0.0


@dataclass
class HardeningAttemptRecord(_Record):
    hardening_id: str = ""
    candidate_id: str = ""
    status: str = ""
    hardening_gap: float = 0.0


@dataclass
class LineageEdgeRecord(_Record):
    edge_id: str = ""
    src_type: str = ""
    src_id: str = ""
    dst_type: str = ""
    dst_id: str = ""
    edge_type: str = ""


__all__ = [
    "ActionRecord",
    "ArtifactRecord",
    "CRGProblemRecord",
    "HardeningAttemptRecord",
    "LineageEdgeRecord",
    "PRODUCTION_METADATA_FIELDS",
    "PRODUCTION_RECORD_TYPES",
    "RelaxedCandidateRecord",
    "RepairFaceRecord",
    "ResponseRecord",
    "RunRecord",
    "SCHEMA_CONTRACT_VERSION",
    "TaskRecord",
]
