from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .core.ids import stable_hash
from .core.jsonio import default_run_id_for_path, read_jsonl, write_jsonl, write_records


@dataclass
class LeanTask:
    """A theorem/task-level Lean proof target.

    `prefix` may contain imports, namespace openings, helper definitions, or an
    unfinished proof prefix for step-level audits. For simple theorem-level
    audits, use `statement` and candidate tactics are tested as the whole proof.
    """

    task_id: str
    statement: str
    imports: list[str] = field(default_factory=lambda: ["Mathlib"])
    prefix: str = ""
    namespace: str | None = None
    domain_tags: list[str] = field(default_factory=list)
    max_heartbeats: int = 200000
    allowed_axioms: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LeanTask":
        d = dict(d)
        allowed = {"task_id", "statement", "imports", "prefix", "namespace", "domain_tags", "max_heartbeats", "allowed_axioms", "metadata"}
        extra = {k: d.pop(k) for k in list(d.keys()) if k not in allowed}
        if extra:
            meta = dict(d.get("metadata") or {})
            meta.setdefault("extra", {}).update(extra)
            d["metadata"] = meta
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProofState:
    state_id: str
    task_id: str
    goals_text: str = ""
    local_context: str = ""
    target: str = ""
    raw_messages: list[str] = field(default_factory=list)
    features: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(cls, task: LeanTask) -> "ProofState":
        return cls(
            state_id=stable_hash({"task_id": task.task_id, "statement": task.statement}),
            task_id=task.task_id,
            target=task.statement,
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProofState":
        d = dict(d)
        allowed = {"state_id", "task_id", "goals_text", "local_context", "target", "raw_messages", "features", "metadata"}
        extra = {k: d.pop(k) for k in list(d.keys()) if k not in allowed}
        if extra:
            meta = dict(d.get("metadata") or {})
            meta.setdefault("extra", {}).update(extra)
            d["metadata"] = meta
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TacticAction:
    action_id: str
    tactic: str
    tactic_class: str = "unknown"
    carrier_tags: list[str] = field(default_factory=list)
    cost_estimate: float = 1.0
    max_heartbeats: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TacticAction":
        d = dict(d)
        if "class" in d and "tactic_class" not in d:
            d["tactic_class"] = d.pop("class")
        if "id" in d and "action_id" not in d:
            d["action_id"] = d.pop("id")
        allowed = {"action_id", "tactic", "tactic_class", "carrier_tags", "cost_estimate", "max_heartbeats", "metadata"}
        extra = {k: d.pop(k) for k in list(d.keys()) if k not in allowed}
        if extra:
            meta = dict(d.get("metadata") or {})
            meta.setdefault("extra", {}).update(extra)
            d["metadata"] = meta
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditRecord:
    task_id: str
    state_id: str
    action_id: str
    status: Literal["success", "partial", "fail", "timeout", "unsafe", "elab_error", "dry_run"]
    elapsed_ms: float = 0.0
    heartbeats: int | None = None
    stdout: str = ""
    stderr: str = ""
    messages: list[str] = field(default_factory=list)
    after_state: ProofState | None = None
    defect_before: dict[str, Any] | None = None
    defect_after: dict[str, Any] | None = None
    response: dict[str, float] | None = None
    carrier_delta: dict[str, float] | None = None
    audit_flags: dict[str, Any] = field(default_factory=dict)
    lean_file: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AuditRecord":
        d = dict(d)
        if isinstance(d.get("after_state"), dict):
            d["after_state"] = ProofState.from_dict(d["after_state"])
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class DefectVector:
    goal: dict[str, float] = field(default_factory=dict)
    type: dict[str, float] = field(default_factory=dict)
    search: dict[str, float] = field(default_factory=dict)
    carrier: dict[str, float] = field(default_factory=dict)
    audit: dict[str, float] = field(default_factory=dict)
    flat: list[float] = field(default_factory=list)
    flat_keys: list[str] = field(default_factory=list)
    quotient_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DefectVector":
        return cls(**d)

    def as_numpy(self):
        import numpy as np

        return np.asarray(self.flat, dtype=float)


@dataclass
class ResponseRecord:
    state_id: str
    action_id: str
    response: dict[str, float]
    response_flat: list[float]
    response_keys: list[str]
    defect_before: DefectVector
    defect_after: DefectVector
    audit_status: str
    carrier_delta: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResponseRecord":
        d = dict(d)
        if isinstance(d.get("defect_before"), dict):
            d["defect_before"] = DefectVector.from_dict(d["defect_before"])
        if isinstance(d.get("defect_after"), dict):
            d["defect_after"] = DefectVector.from_dict(d["defect_after"])
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RGCSelection:
    state_id: str
    selected_action_id: str | None
    scores: dict[str, float]
    carrier_risks: dict[str, float]
    gamma_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryStep:
    step: int
    state_id: str
    action_id: str
    tactic: str
    status: str
    selected_score: float | None = None
    defect_norm_before: float | None = None
    defect_norm_after: float | None = None
    response_norm: float | None = None
    carrier_risk: float | None = None
    elapsed_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryRecord:
    task_id: str
    final_status: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    prefix: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
