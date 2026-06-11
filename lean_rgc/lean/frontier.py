from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

from ..schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl, stable_hash
from .executor import LeanExecutor, LeanExecutorConfig
from ..defects import ProofDefectExtractor
from ..carrier_normalizer import CarrierNormalizer, ExposureCandidate
from ..candidates import TacticCandidateGenerator, CandidateGeneratorConfig


@dataclass
class FrontierRecord:
    original_task_id: str
    frontier_task_id: str
    exposure_action_id: str
    exposure_tactic: str
    exposure_kind: str
    status: str
    accepted: bool
    reason: str
    task: dict[str, Any]
    audit: dict[str, Any]
    defect_before: dict[str, Any] = field(default_factory=dict)
    defect_after: dict[str, Any] = field(default_factory=dict)
    response: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def exposure_actions_for_task(task: LeanTask, *, max_prefixes: int = 8, include_identity: bool = False) -> list[TacticAction]:
    state = ProofState.from_task(task)
    prefixes = CarrierNormalizer().expose(task, state)[:max_prefixes]
    actions: list[TacticAction] = []
    for p in prefixes:
        if p.prefix_id == "id" and not include_identity:
            continue
        if not p.prefix_tactic.strip():
            continue
        meta = {
            "generated_by": "frontier_exposure",
            "exposure": p.to_dict(),
            "frontier_prefix": True,
        }
        aid = "frontier_" + stable_hash({"task": task.task_id, "prefix": p.prefix_tactic, "kind": p.kind}, 14)
        actions.append(TacticAction(action_id=aid, tactic=p.prefix_tactic, tactic_class="frontier_exposure", carrier_tags=list(dict.fromkeys(["exposure"] + p.carrier_atoms + [p.kind])), cost_estimate=float(p.cost + p.gamma_debt), max_heartbeats=task.max_heartbeats, metadata=meta))
    return actions


def _append_prefix(old: str, prefix: str) -> str:
    old = (old or "").rstrip()
    prefix = (prefix or "").strip()
    if old and prefix:
        return old + "\n" + prefix
    return old or prefix


def _frontier_task_from(task: LeanTask, action: TacticAction, status: str, audit_d: dict[str, Any], *, accepted: bool) -> LeanTask:
    meta = dict(task.metadata or {})
    meta.setdefault("frontier", {})
    meta["frontier"].update({
        "original_task_id": task.task_id,
        "exposure_action_id": action.action_id,
        "exposure_tactic": action.tactic,
        "exposure_status": status,
        "accepted": accepted,
        "audit_summary": {"elapsed_ms": audit_d.get("elapsed_ms"), "heartbeats": audit_d.get("heartbeats")},
    })
    new_id = task.task_id + "__frontier__" + stable_hash({"prefix": task.prefix, "action": action.tactic, "status": status}, 10)
    return LeanTask(task_id=new_id, statement=task.statement, imports=list(task.imports), prefix=_append_prefix(task.prefix, action.tactic), namespace=task.namespace, domain_tags=list(task.domain_tags), max_heartbeats=task.max_heartbeats, allowed_axioms=list(task.allowed_axioms), metadata=meta)


def build_frontiers(
    tasks: list[LeanTask],
    *,
    executor_config: LeanExecutorConfig,
    out_dir: str | Path,
    max_prefixes: int = 8,
    include_identity: bool = False,
    accept_statuses: set[str] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    """Audit structural exposure prefixes and materialize frontier tasks.

    The resulting frontier tasks carry the exposure prefix in `LeanTask.prefix`.
    They are meant to be fed into ordinary audit/search commands with core tactics.
    This makes `intro`/simple exposure a carrier-normalization phase instead of
    a ranked core tactic.
    """
    accept_statuses = accept_statuses or {"partial", "success", "dry_run"}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frontier_path = out / "frontier_tasks.jsonl"
    closed_path = out / "closed_by_exposure.jsonl"
    audit_path = out / "exposure_audit.jsonl"
    response_path = out / "exposure_responses.jsonl"
    record_path = out / "frontier_records.jsonl"

    existing_keys: set[tuple[str, str]] = set()
    frontier_rows: list[dict[str, Any]] = []
    closed_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    resp_rows: list[dict[str, Any]] = []
    rec_rows: list[dict[str, Any]] = []
    if resume and record_path.exists():
        rec_rows = read_jsonl(record_path)
        for r in rec_rows:
            existing_keys.add((str(r.get("original_task_id")), str(r.get("exposure_action_id"))))
        if frontier_path.exists():
            frontier_rows = read_jsonl(frontier_path)
        if closed_path.exists():
            closed_rows = read_jsonl(closed_path)
        if audit_path.exists():
            audit_rows = read_jsonl(audit_path)
        if response_path.exists():
            resp_rows = read_jsonl(response_path)

    extractor = ProofDefectExtractor()
    executor = LeanExecutor(executor_config)
    n_actions = 0
    n_accepted = 0
    n_closed = 0
    statuses: dict[str, int] = {}
    for task in tasks:
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        actions = exposure_actions_for_task(task, max_prefixes=max_prefixes, include_identity=include_identity)
        for action in actions:
            key = (task.task_id, action.action_id)
            if key in existing_keys:
                continue
            n_actions += 1
            audit = executor.run_tactic(task, action, state)
            after = extractor.extract(audit.after_state or state, audit)
            resp, flat, keys = extractor.response(before, after)
            audit.defect_before = before.to_dict(); audit.defect_after = after.to_dict(); audit.response = resp
            audit.carrier_delta = {k: before.carrier.get(k,0.0)-after.carrier.get(k,0.0) for k in sorted(set(before.carrier)|set(after.carrier))}
            ad = audit.to_dict(); ad["action"] = action.to_dict(); ad["task_id"] = task.task_id; ad["target"] = task.statement
            rr = {"state_id": state.state_id, "task_id": task.task_id, "action_id": action.action_id, "response": resp, "response_flat": flat, "response_keys": keys, "defect_before": before.to_dict(), "defect_after": after.to_dict(), "audit_status": audit.status, "carrier_delta": audit.carrier_delta, "action": action.to_dict(), "target": task.statement}
            status = audit.status
            statuses[status] = statuses.get(status, 0) + 1
            accepted = status in accept_statuses
            reason = "accepted_status" if accepted else "status_not_accepted"
            ft = _frontier_task_from(task, action, status, ad, accepted=accepted)
            rec = FrontierRecord(original_task_id=task.task_id, frontier_task_id=ft.task_id, exposure_action_id=action.action_id, exposure_tactic=action.tactic, exposure_kind=str((action.metadata.get("exposure") or {}).get("kind") or action.tactic_class), status=status, accepted=accepted, reason=reason, task=ft.to_dict(), audit=ad, defect_before=before.to_dict(), defect_after=after.to_dict(), response=resp, metadata={"action": action.to_dict()})
            audit_rows.append(ad); resp_rows.append(rr); rec_rows.append(rec.to_dict())
            if accepted:
                n_accepted += 1
                if status == "success":
                    n_closed += 1
                    closed_rows.append({"original_task_id": task.task_id, "frontier_task_id": ft.task_id, "task": ft.to_dict(), "audit": ad})
                else:
                    frontier_rows.append(ft.to_dict())
    write_jsonl(frontier_path, frontier_rows)
    write_jsonl(closed_path, closed_rows)
    write_jsonl(audit_path, audit_rows)
    write_jsonl(response_path, resp_rows)
    write_jsonl(record_path, rec_rows)
    summary = {"n_tasks": len(tasks), "n_exposure_actions_new": n_actions, "n_records": len(rec_rows), "n_frontier_tasks": len(frontier_rows), "n_closed_by_exposure": len(closed_rows), "n_accepted_new": n_accepted, "n_closed_new": n_closed, "statuses_new": statuses, "out": str(out)}
    (out / "frontier_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = ["FrontierRecord", "exposure_actions_for_task", "build_frontiers"]

# Compatibility wrappers used by CLI versions that predate build_frontiers.
class FrontierAuditor:
    def __init__(self, executor_config: LeanExecutorConfig | None = None, **kwargs):
        self.executor_config = executor_config or LeanExecutorConfig(**kwargs)

    def run(self, tasks: list[LeanTask], out_dir: str | Path, *, max_prefixes: int = 8, include_identity: bool = False, resume: bool = False) -> dict[str, Any]:
        return build_frontiers(tasks, executor_config=self.executor_config, out_dir=out_dir, max_prefixes=max_prefixes, include_identity=include_identity, resume=resume)


def expose_frontier_files(
    tasks_path: str | Path,
    out_tasks: str | Path,
    out_exposures: str | Path | None = None,
    out_actions: str | Path | None = None,
    executor: LeanExecutor | None = None,
    *,
    lean_cmd: str = "lake env lean",
    workdir: str | None = None,
    timeout_s: float = 20.0,
    dry_run: bool = False,
    cache_dir: str | None = None,
    trace_state: bool = False,
    max_frontiers_per_task: int = 8,
    max_exposures: int | None = None,
    include_identity: bool = False,
    accept_statuses: set[str] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(tasks_path)]
    out_tasks = Path(out_tasks)
    tmp_dir = out_tasks.parent / (out_tasks.stem + "_frontier_tmp")
    if executor is not None:
        cfg = executor.config
    else:
        cfg = LeanExecutorConfig(lean_cmd=lean_cmd, workdir=workdir, timeout_s=timeout_s, dry_run=dry_run, cache_dir=cache_dir, trace_state=trace_state)
    summary = build_frontiers(tasks, executor_config=cfg, out_dir=tmp_dir, max_prefixes=max_exposures or max_frontiers_per_task, include_identity=include_identity, accept_statuses=accept_statuses, resume=resume)
    frontier_src = tmp_dir / "frontier_tasks.jsonl"
    exposure_src = tmp_dir / "frontier_records.jsonl"
    actions = []
    # Generate core action placeholders for each frontier task; downstream can merge with explicit actions.
    for row in read_jsonl(frontier_src) if frontier_src.exists() else []:
        tid = row.get("task_id")
        for tactic, cls, tags in [("rfl", "rfl", ["eq"]), ("simp", "simp", ["simp"]), ("simp_all", "simp", ["simp", "premise"]), ("assumption", "premise", ["premise"]), ("omega", "arith", ["arithmetic"]), ("norm_num", "arith", ["arithmetic"]), ("constructor <;> simp_all", "constructor", ["constructor", "simp", "premise"])]:
            a = TacticAction(action_id="frontier_core_" + stable_hash({"task": tid, "tactic": tactic}, 12), tactic=tactic, tactic_class=cls, carrier_tags=tags, metadata={"task_id": tid, "generated_by": "frontier_core"}).to_dict()
            a["task_id"] = tid
            actions.append(a)
    if frontier_src.exists():
        out_tasks.parent.mkdir(parents=True, exist_ok=True)
        out_tasks.write_text(frontier_src.read_text(encoding="utf-8"), encoding="utf-8")
    if out_exposures is not None:
        Path(out_exposures).parent.mkdir(parents=True, exist_ok=True)
        Path(out_exposures).write_text(exposure_src.read_text(encoding="utf-8") if exposure_src.exists() else "", encoding="utf-8")
    if out_actions is not None:
        write_jsonl(out_actions, actions)
    summary.update({"out_tasks": str(out_tasks), "out_exposures": str(out_exposures) if out_exposures else None, "out_actions": str(out_actions) if out_actions else None, "n_frontier_core_actions": len(actions)})
    return summary

# ---------------------------------------------------------------------------
# Compatibility helpers used by CLI v0.8+.
# ---------------------------------------------------------------------------

def expose_frontier_files(
    tasks_path: str | Path,
    out_tasks: str | Path,
    *,
    out_exposures: str | Path | None = None,
    out_actions: str | Path | None = None,
    include_identity: bool = False,
    max_frontiers_per_task: int = 8,
    max_core_actions: int = 16,
) -> dict[str, Any]:
    """Materialize frontier tasks without auditing exposure prefixes.

    This light-weight helper is intentionally chart-level: it expands structural
    exposure prefixes into LeanTask.prefix and writes core action candidates for
    the exposed frontier.  Use `expose-frontiers` / `build_frontiers` when Lean
    micro-auditing of exposure prefixes is required.
    """
    from ..candidates import TacticCandidateGenerator, CandidateGeneratorConfig
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    core_gen = __import__("lean_rgc.candidates", fromlist=["TacticCandidateGenerator", "CandidateGeneratorConfig"])
    TacticCandidateGenerator = core_gen.TacticCandidateGenerator
    CandidateGeneratorConfig = core_gen.CandidateGeneratorConfig
    gen = TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_core_actions))

    frontier_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    seen_actions: set[tuple[str, str]] = set()

    for task in tasks:
        state = ProofState.from_task(task)
        prefixes = CarrierNormalizer().expose(task, state)[:max_frontiers_per_task]
        for p in prefixes:
            tactic = (p.prefix_tactic or "").strip()
            if not tactic and not include_identity:
                continue
            ft = LeanTask(
                task_id=task.task_id + "__frontier__" + stable_hash({"prefix": tactic, "task": task.task_id}, 10),
                statement=task.statement,
                imports=list(task.imports),
                prefix=_append_prefix(task.prefix, tactic),
                namespace=task.namespace,
                domain_tags=list(task.domain_tags),
                max_heartbeats=task.max_heartbeats,
                allowed_axioms=list(task.allowed_axioms),
                metadata={**(task.metadata or {}), "frontier": {"original_task_id": task.task_id, "exposure": p.to_dict(), "audit_required": False}},
            )
            ftd = ft.to_dict(); ftd["parent_task_id"] = task.task_id; ftd["exposure"] = p.to_dict()
            frontier_rows.append(ftd)
            exposure_rows.append({"task_id": task.task_id, "frontier_task_id": ft.task_id, "exposure": p.to_dict(), "prefix_tactic": tactic})
            for a in gen.candidates(ft, ProofState.from_task(ft))[:max_core_actions]:
                key = (ft.task_id, a.tactic)
                if key in seen_actions:
                    continue
                seen_actions.add(key)
                d = a.to_dict()
                d["task_id"] = ft.task_id
                d.setdefault("metadata", {})["task_id"] = ft.task_id
                d.setdefault("metadata", {})["frontier_parent_task_id"] = task.task_id
                d.setdefault("metadata", {})["frontier_exposure"] = p.to_dict()
                action_rows.append(d)

    write_jsonl(out_tasks, frontier_rows)
    if out_exposures:
        write_jsonl(out_exposures, exposure_rows)
    if out_actions:
        write_jsonl(out_actions, action_rows)
    return {
        "n_input_tasks": len(tasks),
        "n_frontier_tasks": len(frontier_rows),
        "n_exposures": len(exposure_rows),
        "n_core_actions": len(action_rows),
        "out_tasks": str(out_tasks),
        "out_exposures": str(out_exposures) if out_exposures else None,
        "out_actions": str(out_actions) if out_actions else None,
    }


class FrontierAuditor:
    """Thin compatibility wrapper around build_frontiers."""

    def __init__(self, executor_config: LeanExecutorConfig | None = None):
        self.executor_config = executor_config or LeanExecutorConfig(dry_run=True)

    def run(self, tasks: list[LeanTask], out_dir: str | Path, **kwargs) -> dict[str, Any]:
        return build_frontiers(tasks, executor_config=self.executor_config, out_dir=out_dir, **kwargs)


__all__ = [
    "FrontierRecord",
    "exposure_actions_for_task",
    "build_frontiers",
    "expose_frontier_files",
    "FrontierAuditor",
]

class FrontierAuditor:
    """Compatibility wrapper for focused exposure audits.

    It exposes structural prefixes as first-class audited carrier contexts and
    then core-audits tactics on the exposed frontier.  This keeps `intro`/simple
    split prefixes out of the primitive tactic-label space.
    """

    def __init__(self, executor: LeanExecutor, extractor: ProofDefectExtractor | None = None):
        self.executor = executor
        self.extractor = extractor or ProofDefectExtractor()

    def run(self, tasks: list[LeanTask], *, out_dir: str | Path, max_exposures: int = 4, max_core_actions: int = 12, include_identity: bool = True) -> Any:
        from ..focused import run_focused_micro_audit
        summary = run_focused_micro_audit(
            tasks,
            out_dir=out_dir,
            executor_config=self.executor.config,
            base_actions=None,
            max_exposures=max_exposures,
            max_core_actions=max_core_actions,
            audit_identity_exposure=include_identity,
        )
        # Small object with to_dict for old CLI compatibility.
        class _Summary:
            def __init__(self, d): self._d = d
            def to_dict(self): return self._d
        return _Summary(summary)


def expose_frontier_files(
    tasks_path: str | Path,
    out_tasks: str | Path,
    *,
    out_exposures: str | Path | None = None,
    out_actions: str | Path | None = None,
    include_identity: bool = False,
    max_frontiers_per_task: int = 8,
    max_core_actions: int = 32,
) -> dict[str, Any]:
    """Chart-only frontier materialization without Lean execution.

    This is used to prepare frontier tasks and candidate core actions.  It does
    not certify the exposure; use `expose-frontiers` or `focused-audit` for an
    audited version.
    """
    from ..candidates import TacticCandidateGenerator, CandidateGeneratorConfig
    from ..carrier_exposure import StateDependentCandidateGenerator

    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    normalizer = CarrierNormalizer()
    core_gen = TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_core_actions))
    frontier_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for task in tasks:
        state = ProofState.from_task(task)
        exps = normalizer.expose(task, state)[:max_frontiers_per_task]
        if not include_identity:
            exps = [e for e in exps if (getattr(e, "prefix_tactic", "") or "").strip()]
        if not exps:
            continue
        for exp in exps:
            prefix = (getattr(exp, "prefix_tactic", "") or "").strip()
            new_prefix = _append_prefix(task.prefix, prefix)
            meta = dict(task.metadata or {})
            meta["frontier_chart"] = {"source_task_id": task.task_id, "prefix_tactic": prefix, "prefix_id": getattr(exp, "prefix_id", "exposure"), "kind": getattr(exp, "kind", "exposure"), "audited": False}
            ftask = LeanTask(**{**task.to_dict(), "task_id": task.task_id + "__frontier__" + stable_hash({"prefix": prefix}, 8), "prefix": new_prefix, "metadata": meta})
            fdict = ftask.to_dict()
            frontier_rows.append(fdict)
            exposure_rows.append({"task_id": task.task_id, "frontier_task_id": ftask.task_id, "exposure": exp.to_dict() if hasattr(exp, "to_dict") else asdict(exp)})
            for core in core_gen.candidates(ftask, state)[:max_core_actions]:
                md = dict(core.metadata or {})
                md.update({"generated_by": "frontier_core_chart", "frontier_task_id": ftask.task_id, "source_task_id": task.task_id, "prefix_tactic": prefix, "core_tactic": core.tactic})
                row = TacticAction(**{**core.to_dict(), "action_id": "frontier_core_" + stable_hash({"frontier": ftask.task_id, "core": core.tactic}, 12), "metadata": md}).to_dict()
                row["task_id"] = ftask.task_id
                row.setdefault("metadata", {})["task_id"] = ftask.task_id
                action_rows.append(row)
    write_jsonl(out_tasks, frontier_rows)
    if out_exposures:
        write_jsonl(out_exposures, exposure_rows)
    if out_actions:
        write_jsonl(out_actions, action_rows)
    summary = {"n_source_tasks": len(tasks), "n_frontier_tasks": len(frontier_rows), "n_exposure_rows": len(exposure_rows), "n_actions": len(action_rows), "out_tasks": str(out_tasks), "out_exposures": str(out_exposures) if out_exposures else None, "out_actions": str(out_actions) if out_actions else None}
    return summary


__all__ = ["FrontierRecord", "exposure_actions_for_task", "build_frontiers", "FrontierAuditor", "expose_frontier_files"]

# ---------------------------------------------------------------------------
# Backward-compatible v9 frontier helpers used by older CLI entry points.
# ---------------------------------------------------------------------------
@dataclass
class FrontierAuditSummary:
    n_tasks: int
    n_exposure_audits: int
    n_core_audits: int
    out: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FrontierAuditor:
    """Compatibility wrapper around focused two-phase micro-audit."""

    def __init__(self, executor: LeanExecutor, extractor: ProofDefectExtractor | None = None):
        self.executor = executor
        self.extractor = extractor or ProofDefectExtractor()

    def run(self, tasks: list[LeanTask], *, out_dir: str | Path, max_exposures: int = 4, max_core_actions: int = 12, include_identity: bool = True) -> FrontierAuditSummary:
        from ..focused import run_focused_micro_audit
        rep = run_focused_micro_audit(tasks, out_dir=out_dir, executor_config=self.executor.config, base_actions=None, max_exposures=max_exposures, max_core_actions=max_core_actions, audit_identity_exposure=include_identity)
        return FrontierAuditSummary(n_tasks=int(rep.get("n_tasks", len(tasks))), n_exposure_audits=int(rep.get("n_exposure_audits", 0)), n_core_audits=int(rep.get("n_core_audits", 0)), out=str(out_dir), metadata=rep)


def expose_frontier_files(
    tasks_path: str | Path,
    out_tasks: str | Path,
    *,
    out_exposures: str | Path | None = None,
    out_actions: str | Path | None = None,
    include_identity: bool = True,
    max_frontiers_per_task: int = 2,
    max_core_actions: int = 16,
) -> dict[str, Any]:
    """Pure, no-Lean frontier materialization for CLI compatibility.

    This function does not audit prefixes; it generates carrier-exposed task
    variants and optional core actions.  It is intended for fast planning.  Use
    `expose-frontiers` or `frontier-audit` for audited frontier construction.
    """
    from ..candidates import TacticCandidateGenerator, CandidateGeneratorConfig
    tasks = [LeanTask.from_dict(r) for r in read_jsonl(tasks_path)]
    normalizer = CarrierNormalizer()
    core_gen = TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_core_actions))
    frontier_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for task in tasks:
        state = ProofState.from_task(task)
        exps = normalizer.expose(task, state)
        if not include_identity:
            exps = [e for e in exps if (getattr(e, "prefix_tactic", "") or "").strip()]
        exps = exps[:max_frontiers_per_task]
        for exp in exps:
            prefix = getattr(exp, "prefix_tactic", "") or ""
            new_id = task.task_id + "__frontier_plan__" + stable_hash({"prefix": prefix, "task": task.task_id}, 10)
            meta = dict(task.metadata or {})
            meta["frontier_plan"] = {"source_task_id": task.task_id, "prefix_tactic": prefix, "exposure": exp.to_dict() if hasattr(exp, "to_dict") else asdict(exp)}
            ft = LeanTask(task_id=new_id, statement=task.statement, imports=list(task.imports), prefix=_append_prefix(task.prefix, prefix), namespace=task.namespace, domain_tags=list(task.domain_tags), max_heartbeats=task.max_heartbeats, allowed_axioms=list(task.allowed_axioms), metadata=meta)
            frontier_rows.append(ft.to_dict())
            exposure_rows.append({"task_id": task.task_id, "frontier_task_id": new_id, "prefix_tactic": prefix, "exposure": meta["frontier_plan"]["exposure"]})
            for core in core_gen.candidates(ft, ProofState.from_task(ft))[:max_core_actions]:
                d = core.to_dict(); d["task_id"] = new_id; d.setdefault("metadata", {})["frontier_task_id"] = new_id; d["metadata"]["source_task_id"] = task.task_id; d["metadata"]["frontier_prefix_tactic"] = prefix
                action_rows.append(d)
    write_jsonl(out_tasks, frontier_rows)
    if out_exposures:
        write_jsonl(out_exposures, exposure_rows)
    if out_actions:
        write_jsonl(out_actions, action_rows)
    summary = {"n_tasks": len(tasks), "n_frontier_tasks": len(frontier_rows), "n_exposures": len(exposure_rows), "n_actions": len(action_rows), "out_tasks": str(out_tasks), "out_exposures": str(out_exposures) if out_exposures else None, "out_actions": str(out_actions) if out_actions else None}
    return summary

# Update exported names for compatibility.
__all__ = list(dict.fromkeys(__all__ + ["FrontierAuditor", "FrontierAuditSummary", "expose_frontier_files"]))

# v9 compatibility helpers -------------------------------------------------
# Earlier CLI surfaces expected these names from `lean_rgc.frontier`.  Keep
# them as thin wrappers so old and new frontier/exposure commands coexist.

@dataclass
class FrontierAuditSummaryCompat:
    data: dict[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return self.data


class FrontierAuditor:
    """Compatibility wrapper around the focused two-phase micro-audit."""

    def __init__(self, executor: LeanExecutor, extractor: ProofDefectExtractor | None = None):
        self.executor = executor
        self.extractor = extractor or ProofDefectExtractor()

    def run(self, tasks: list[LeanTask], *, out_dir: str | Path, max_exposures: int = 4, max_core_actions: int = 12, include_identity: bool = True) -> FrontierAuditSummaryCompat:
        from ..focused import run_focused_micro_audit
        summary = run_focused_micro_audit(
            tasks,
            out_dir=out_dir,
            executor_config=self.executor.config,
            base_actions=None,
            max_exposures=max_exposures,
            max_core_actions=max_core_actions,
            audit_identity_exposure=include_identity,
        )
        return FrontierAuditSummaryCompat(summary)


def expose_frontier_files(
    tasks_path: str | Path,
    out_tasks: str | Path,
    *,
    out_exposures: str | Path | None = None,
    out_actions: str | Path | None = None,
    include_identity: bool = True,
    max_frontiers_per_task: int = 8,
    max_core_actions: int = 16,
) -> dict[str, Any]:
    """Generate frontier tasks and optional action rows without running Lean.

    This lightweight helper is used by legacy `expose-frontier`.  For audited
    frontier construction use `expose-frontiers` or `focused-audit`.
    """
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    normalizer = CarrierNormalizer()
    core_gen = TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_core_actions))
    frontier_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for task in tasks:
        state = ProofState.from_task(task)
        prefixes = normalizer.expose(task, state)[:max_frontiers_per_task]
        for exp in prefixes:
            if not include_identity and not (exp.prefix_tactic or '').strip():
                continue
            prefix = _append_prefix(task.prefix, exp.prefix_tactic)
            ft = LeanTask.from_dict({**task.to_dict(), "task_id": task.task_id + "__frontier__" + stable_hash({"prefix": prefix}, 10), "prefix": prefix})
            meta = dict(ft.metadata or {})
            meta["frontier_exposure"] = exp.to_dict()
            ft = LeanTask.from_dict({**ft.to_dict(), "metadata": meta})
            frontier_rows.append(ft.to_dict())
            exposure_rows.append({"task_id": task.task_id, "frontier_task_id": ft.task_id, "exposure": exp.to_dict(), "prefix_tactic": exp.prefix_tactic})
            for core in core_gen.candidates(ft, ProofState.from_task(ft))[:max_core_actions]:
                d = core.to_dict()
                d["task_id"] = ft.task_id
                d.setdefault("metadata", {})["frontier_task_id"] = ft.task_id
                d.setdefault("metadata", {})["parent_task_id"] = task.task_id
                d.setdefault("metadata", {})["frontier_exposure"] = exp.to_dict()
                action_rows.append(d)
    write_jsonl(out_tasks, frontier_rows)
    if out_exposures:
        write_jsonl(out_exposures, exposure_rows)
    if out_actions:
        write_jsonl(out_actions, action_rows)
    return {"n_tasks": len(tasks), "n_frontier_tasks": len(frontier_rows), "n_exposures": len(exposure_rows), "n_actions": len(action_rows), "out_tasks": str(out_tasks), "out_exposures": str(out_exposures) if out_exposures else None, "out_actions": str(out_actions) if out_actions else None}


# Extend __all__ if it already exists from the earlier frontier API.
try:
    __all__ = list(dict.fromkeys(list(__all__) + ["FrontierAuditor", "FrontierAuditSummaryCompat", "expose_frontier_files"]))
except NameError:
    __all__ = ["FrontierAuditor", "FrontierAuditSummaryCompat", "expose_frontier_files"]
