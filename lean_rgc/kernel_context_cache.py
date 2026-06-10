from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import time

from .contextual_congruence import IDENTITY_CONTEXT_ID
from .dataset import summarize_response_rows
from .defects import ProofDefectExtractor
from .lean_server import LeanServerAdapter, LeanServerConfig
from .schemas import AuditRecord, LeanTask, ProofState, TacticAction, read_jsonl, stable_hash, write_jsonl
from .lean.structured_state import extract_structured_state_from_kernel_json


SCHEMA_KERNEL_CONTEXT_CACHE = "lean-rgc-kernel-context-state-cache-v52.0"
SCHEMA_CONTEXTUAL_PLAN_AUDIT = "lean-rgc-contextual-plan-audit-v52.0"


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def _is_identity_action(action: dict[str, Any] | None) -> bool:
    if not action:
        return True
    aid = str(action.get("action_id") or action.get("context_id") or "")
    tactic = str(action.get("tactic") or "").strip()
    return aid == IDENTITY_CONTEXT_ID or tactic in {"", "skip", "all_goals skip"}


def _action_from_chart(action: dict[str, Any], *, fallback_id: str) -> TacticAction:
    row = dict(action)
    row.setdefault("action_id", fallback_id)
    row.setdefault("tactic", "")
    return TacticAction.from_dict(row)


def _persistent_after_state_id(rec: AuditRecord) -> str | None:
    flags = dict(rec.audit_flags or {})
    sid = flags.get("after_persistent_state_id")
    if sid:
        return str(sid)
    if rec.after_state is not None and rec.after_state.state_id:
        return str(rec.after_state.state_id)
    kernel = flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
    if kernel and kernel.get("state_id"):
        return str(kernel.get("state_id"))
    return None


def _kernel_state_from_rec(rec: AuditRecord) -> dict[str, Any] | None:
    flags = dict(rec.audit_flags or {})
    kernel = flags.get("kernel_state")
    return kernel if isinstance(kernel, dict) else None


def _kernel_is_closed(kernel: dict[str, Any] | None, rec: AuditRecord | None = None) -> bool:
    if isinstance(kernel, dict):
        if kernel.get("closed") is True or kernel.get("status") == "closed":
            return True
        goals = kernel.get("goals")
        if isinstance(goals, list) and not goals:
            return True
    return bool(rec is not None and rec.status == "success")


def _step_success(status: str) -> bool:
    return status in {"success", "partial", "dry_run"}


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


@dataclass
class CachedTransition:
    cache_key: str
    role: str
    parent_state_id: str
    action_id: str
    tactic: str
    state_id: str
    status: str
    audit: AuditRecord | None = None
    cache_hit: bool = False
    identity: bool = False

    def to_step(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "role": self.role,
            "parent_state_id": self.parent_state_id,
            "action_id": self.action_id,
            "tactic": self.tactic,
            "state_id": self.state_id,
            "status": self.status,
            "cache_hit": self.cache_hit,
            "identity": self.identity,
        }

    def to_cache_row(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_KERNEL_CONTEXT_CACHE,
            **self.to_step(),
            "canonical_status": "kernel_context_state_cache_chart_not_canonical",
        }


@dataclass
class KernelContextStateCache:
    server: LeanServerAdapter
    cache: dict[str, CachedTransition] = field(default_factory=dict)
    cache_rows: list[dict[str, Any]] = field(default_factory=list)
    hits: int = 0
    misses: int = 0
    identity_hits: int = 0

    def key_for(self, parent_state_id: str, action: dict[str, Any], role: str) -> str:
        return stable_hash(
            {
                "parent_state_id": parent_state_id,
                "action_id": action.get("action_id"),
                "tactic": action.get("tactic"),
                "role": role,
            },
            n=24,
        )

    def apply_cached(self, task: LeanTask, parent_state_id: str, action: dict[str, Any], *, role: str) -> CachedTransition:
        aid = str(action.get("action_id") or role)
        tactic = str(action.get("tactic") or "")
        if _is_identity_action(action):
            self.identity_hits += 1
            return CachedTransition(
                cache_key=f"identity:{parent_state_id}:{role}",
                role=role,
                parent_state_id=parent_state_id,
                action_id=aid or IDENTITY_CONTEXT_ID,
                tactic=tactic,
                state_id=parent_state_id,
                status="success",
                cache_hit=True,
                identity=True,
            )
        key = self.key_for(parent_state_id, action, role)
        if key in self.cache:
            self.hits += 1
            cached = self.cache[key]
            return CachedTransition(**{**cached.__dict__, "cache_hit": True})
        self.misses += 1
        rec = self.server.apply_tactic_to_state_id(
            task,
            _action_from_chart(action, fallback_id=aid),
            parent_state_id,
            create_state=False,
        )
        after_id = _persistent_after_state_id(rec) or parent_state_id
        cached = CachedTransition(
            cache_key=key,
            role=role,
            parent_state_id=parent_state_id,
            action_id=aid,
            tactic=tactic,
            state_id=after_id,
            status=rec.status,
            audit=rec,
            cache_hit=False,
        )
        self.cache[key] = cached
        self.cache_rows.append(cached.to_cache_row())
        return cached


def _combined_status(domain_status: str, final_step: CachedTransition | None) -> str:
    if domain_status == "success":
        return final_step.status if final_step is not None else "success"
    if domain_status.endswith("_closed"):
        return "fail"
    if domain_status in {"pre_failed", "premise_failed", "post_failed"}:
        return "fail"
    return "fail"


def _combine_plan_record(
    *,
    task: LeanTask,
    logical_state: ProofState,
    candidate: TacticAction,
    plan_steps: list[CachedTransition],
    domain_status: str,
    failed_step: str | None,
    elapsed_ms: float,
) -> AuditRecord:
    final_step = plan_steps[-1] if plan_steps else None
    final_audit = final_step.audit if final_step is not None else None
    final_state = final_audit.after_state if final_audit is not None and final_audit.after_state is not None else logical_state
    final_kernel = _kernel_state_from_rec(final_audit) if final_audit is not None else None
    messages: list[str] = []
    stderr_parts: list[str] = []
    for step in plan_steps:
        if step.audit is not None:
            messages.extend(step.audit.messages or [])
            if step.audit.stderr:
                stderr_parts.append(step.audit.stderr)
    flags = dict(final_audit.audit_flags or {}) if final_audit is not None else {}
    if final_kernel is not None:
        flags["kernel_state"] = final_kernel
    flags.update(
        {
            "kernel_context_cache": True,
            "execution_backend": "lean_kernel_rpc_context_cache_v1",
            "domain_status": domain_status,
            "failed_step": failed_step,
            "plan_steps": [s.to_step() for s in plan_steps],
            "logical_state_id": logical_state.state_id,
            "candidate_metadata": dict(candidate.metadata or {}),
        }
    )
    return AuditRecord(
        task_id=task.task_id,
        state_id=logical_state.state_id,
        action_id=candidate.action_id,
        status=_combined_status(domain_status, final_step),
        elapsed_ms=elapsed_ms,
        heartbeats=sum((_safe_float(s.audit.heartbeats, 0.0) for s in plan_steps if s.audit is not None), 0.0) or None,
        stdout="",
        stderr="\n".join(stderr_parts),
        messages=messages,
        after_state=final_state,
        audit_flags=flags,
    )


def _materialize_candidate(
    *,
    cache: KernelContextStateCache,
    task: LeanTask,
    root_state_id: str,
    logical_state: ProofState,
    candidate: TacticAction,
) -> AuditRecord:
    meta = dict(candidate.metadata or {})
    pre = meta.get("pre_context_action") if isinstance(meta.get("pre_context_action"), dict) else None
    post = meta.get("post_context_action") if isinstance(meta.get("post_context_action"), dict) else None
    premise = meta.get("premise_core_action") if isinstance(meta.get("premise_core_action"), dict) else None
    is_baseline = bool(meta.get("is_contextual_baseline"))
    t0 = time.time()
    steps: list[CachedTransition] = []
    domain_status = "success"
    failed_step: str | None = None

    pre_step = cache.apply_cached(task, root_state_id, pre or {"action_id": IDENTITY_CONTEXT_ID, "tactic": "skip"}, role="pre")
    steps.append(pre_step)
    if not _step_success(pre_step.status):
        domain_status = "pre_failed"
        failed_step = "pre"
        return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)

    pre_kernel = _kernel_state_from_rec(pre_step.audit) if pre_step.audit is not None else None
    pre_closed = _kernel_is_closed(pre_kernel, pre_step.audit)
    if pre_closed and not is_baseline:
        domain_status = "undefined_pre_context_closed"
        failed_step = "premise"
        return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)

    if is_baseline:
        if not pre_closed:
            post_step = cache.apply_cached(task, pre_step.state_id, post or {"action_id": IDENTITY_CONTEXT_ID, "tactic": "skip"}, role="post")
            steps.append(post_step)
            if not _step_success(post_step.status):
                domain_status = "post_failed"
                failed_step = "post"
        return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)

    if not isinstance(premise, dict):
        domain_status = "premise_missing"
        failed_step = "premise"
        return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)

    premise_step = cache.apply_cached(task, pre_step.state_id, premise, role="premise")
    steps.append(premise_step)
    if not _step_success(premise_step.status):
        domain_status = "premise_failed"
        failed_step = "premise"
        return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)

    premise_kernel = _kernel_state_from_rec(premise_step.audit) if premise_step.audit is not None else None
    if not _kernel_is_closed(premise_kernel, premise_step.audit):
        post_step = cache.apply_cached(task, premise_step.state_id, post or {"action_id": IDENTITY_CONTEXT_ID, "tactic": "skip"}, role="post")
        steps.append(post_step)
        if not _step_success(post_step.status):
            domain_status = "post_failed"
            failed_step = "post"

    return _combine_plan_record(task=task, logical_state=logical_state, candidate=candidate, plan_steps=steps, domain_status=domain_status, failed_step=failed_step, elapsed_ms=(time.time() - t0) * 1000.0)


def audit_contextual_candidates_with_kernel_cache(
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    *,
    out_dir: str | Path,
    server_config: LeanServerConfig,
    max_actions: int = 64,
    resume: bool = False,
    flush_every: int = 50,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    extractor = ProofDefectExtractor()

    existing_audits: list[dict[str, Any]] = []
    existing_responses: list[dict[str, Any]] = []
    done: set[tuple[str, str]] = set()
    if resume and (out / "responses.jsonl").exists():
        existing_responses = read_jsonl(out / "responses.jsonl")
        if (out / "micro_audit.jsonl").exists():
            existing_audits = read_jsonl(out / "micro_audit.jsonl")
        for r in existing_responses:
            sid = r.get("state_id")
            aid = r.get("action_id")
            if sid is not None and aid is not None:
                done.add((str(sid), str(aid)))

    audits = list(existing_audits)
    responses = list(existing_responses)
    structured_states: list[dict[str, Any]] = []
    goal_state_transitions: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    cache_rows: list[dict[str, Any]] = []

    def flush() -> None:
        write_jsonl(out / "micro_audit.jsonl", audits)
        write_jsonl(out / "responses.jsonl", responses)
        write_jsonl(out / "structured_states.jsonl", structured_states)
        write_jsonl(out / "goal_state_transitions.jsonl", goal_state_transitions)
        write_jsonl(out / "contextual_plan_transitions.jsonl", plan_rows)
        write_jsonl(out / "kernel_context_state_cache.jsonl", cache_rows)
        seen: set[str] = set()
        defects: list[dict[str, Any]] = []
        for r in responses:
            sid = str(r.get("state_id"))
            if sid in seen:
                continue
            seen.add(sid)
            db = r.get("defect_before", {})
            if isinstance(db, dict):
                row = dict(db)
                row["state_id"] = sid
                row["task_id"] = r.get("task_id") or db.get("task_id")
                defects.append(row)
        write_jsonl(out / "defects.jsonl", defects)

    t0 = time.time()
    completed_new = 0
    with LeanServerAdapter(server_config) as server:
        load_report = server.load_project()
        cache = KernelContextStateCache(server)
        flush_every = max(1, int(flush_every or 50))
        for task in tasks:
            logical_state = ProofState.from_task(task)
            defect_before = extractor.extract(logical_state)
            init = server.register_task(task)
            init_state = init.get("state") if isinstance(init, dict) else None
            if not isinstance(init_state, dict) or not init_state.get("state_id"):
                raise RuntimeError(f"kernel cache audit could not initialize task state: {init}")
            root_state_id = str(init_state.get("state_id"))
            k0 = init.get("kernel_state") if isinstance(init, dict) else None
            if isinstance(k0, dict):
                try:
                    structured_states.append(extract_structured_state_from_kernel_json(
                        k0,
                        task=task,
                        state=logical_state,
                        backend="kernel_json_v28",
                        metadata={"source": "kernel_context_cache_root_state"},
                    ).to_dict())
                except Exception as e:
                    structured_states.append({"state_id": logical_state.state_id, "task_id": task.task_id, "source": "kernel_context_cache_root_parse_error", "error": str(e)})

            actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
            for candidate in actions[:max_actions]:
                if (logical_state.state_id, candidate.action_id) in done:
                    continue
                rec = _materialize_candidate(cache=cache, task=task, root_state_id=root_state_id, logical_state=logical_state, candidate=candidate)
                after_state = rec.after_state or logical_state
                defect_after = extractor.extract(after_state, rec)
                resp, resp_flat, resp_keys = extractor.response(defect_before, defect_after)
                rec.defect_before = defect_before.to_dict()
                rec.defect_after = defect_after.to_dict()
                rec.response = resp
                rec.carrier_delta = {
                    k: defect_before.carrier.get(k, 0.0) - defect_after.carrier.get(k, 0.0)
                    for k in sorted(set(defect_before.carrier) | set(defect_after.carrier))
                }
                rr = {
                    "state_id": logical_state.state_id,
                    "task_id": task.task_id,
                    "action_id": candidate.action_id,
                    "target": task.statement,
                    "action": candidate.to_dict(),
                    "response": resp,
                    "response_flat": resp_flat,
                    "response_keys": resp_keys,
                    "defect_before": defect_before.to_dict(),
                    "defect_after": defect_after.to_dict(),
                    "audit_status": rec.status,
                    "carrier_delta": rec.carrier_delta,
                    "audit_flags": dict(rec.audit_flags or {}),
                }
                ad = rec.to_dict()
                ad["action"] = candidate.to_dict()
                ad["task_id"] = task.task_id
                ad["target"] = task.statement
                audits.append(ad)
                responses.append(rr)
                try:
                    structured_states.append(server.structured_state(task, after_state, rec))
                except Exception as e:
                    structured_states.append({"state_id": after_state.state_id, "task_id": task.task_id, "source": "structured_state_parse_error", "error": str(e)})
                try:
                    from .lean.goal_state_dynamics import goal_state_transition_from_audit
                    tr = goal_state_transition_from_audit(ad)
                    if tr is not None:
                        goal_state_transitions.append(tr)
                except Exception as e:
                    goal_state_transitions.append({"task_id": task.task_id, "state_id": logical_state.state_id, "action_id": candidate.action_id, "source": "goal_state_transition_parse_error", "error": str(e)})
                plan_rows.append({
                    "schema_version": SCHEMA_CONTEXTUAL_PLAN_AUDIT,
                    "task_id": task.task_id,
                    "state_id": logical_state.state_id,
                    "action_id": candidate.action_id,
                    "status": rec.status,
                    "domain_status": (rec.audit_flags or {}).get("domain_status"),
                    "plan_steps": (rec.audit_flags or {}).get("plan_steps") or [],
                    "canonical_status": "contextual_plan_audit_chart_not_canonical",
                })
                cache_rows[:] = cache.cache_rows
                completed_new += 1
                if completed_new % flush_every == 0:
                    flush()
        server_status = server.status.to_dict()
    flush()

    elapsed_ms = (time.time() - t0) * 1000.0
    response_summary = summarize_response_rows(responses).to_dict()
    server_summary = {
        "backend": server_status.get("backend"),
        "session_id": server_status.get("session_id"),
        "project_fingerprint": server_status.get("project_fingerprint"),
        "n_requests": server_status.get("n_requests", 0),
        "n_failures": server_status.get("n_failures", 0),
        "n": len(audits),
        "n_new": completed_new,
        "n_resumed": len(existing_responses),
        "elapsed_ms": elapsed_ms,
        "load_report": load_report,
        "kernel_context_cache": True,
        "context_cache_entries": len(cache_rows),
        "context_cache_hits": cache.hits,
        "context_cache_misses": cache.misses,
        "context_identity_hits": cache.identity_hits,
        "source_check_calls": 0,
        **response_summary,
    }
    server_summary.setdefault("files", {})["structured_states"] = str(out / "structured_states.jsonl")
    server_summary.setdefault("files", {})["goal_state_transitions"] = str(out / "goal_state_transitions.jsonl")
    server_summary.setdefault("files", {})["kernel_context_state_cache"] = str(out / "kernel_context_state_cache.jsonl")
    server_summary.setdefault("files", {})["contextual_plan_transitions"] = str(out / "contextual_plan_transitions.jsonl")
    (out / "server_summary.json").write_text(json.dumps(server_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(server_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    (out / "contextual_plan_audit_report.json").write_text(json.dumps(server_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return server_summary


__all__ = [
    "KernelContextStateCache",
    "audit_contextual_candidates_with_kernel_cache",
]
