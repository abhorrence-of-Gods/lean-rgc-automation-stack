from __future__ import annotations

"""Persistent Lean worker protocol for Lean-RGC.

This module implements the first in-tree persistent-worker backend.  It is a
stateful JSONL service: it stores proof-state ids, supports branch/rollback,
and applies tactics through a pluggable execution backend.  In this v27
implementation the execution backend is either the deterministic dry-run engine
or the existing file executor; the protocol is intentionally the same one that a
future kernel/RPC-backed Lean worker can implement.

The important change versus the old file-only executor is that downstream RGC
code can now talk to a persistent state service instead of reconstructing the
state model itself.  Every response is tagged as a chart, not a canonical proof
state.
"""

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, TextIO
import argparse
import copy
import json
import os
import shlex
import subprocess
import sys
import time

from .schemas import AuditRecord, LeanTask, ProofState, TacticAction, stable_hash
from .lean.executor import LeanExecutor, LeanExecutorConfig
from .lean_server import project_fingerprint
from .structured_state import extract_structured_state, extract_structured_state_from_kernel_json
from .goal_state_dynamics import compute_goal_state_transition_delta
from .kernel_state import normalize_kernel_state_v1


@dataclass
class WorkerConfig:
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    backend: str = "dry_run"  # dry_run | file
    keep_files: bool = False
    cache_dir: str | None = None
    trace_state: bool = False
    warmup: bool = True
    session_id: str | None = None


@dataclass
class PersistentStateRecord:
    state_id: str
    task_id: str
    task: dict[str, Any]
    prefix: str = ""
    target: str = ""
    goals_text: str = ""
    local_context: str = ""
    raw_messages: list[str] = field(default_factory=list)
    parent_state_id: str | None = None
    applied_action_id: str | None = None
    applied_tactic: str | None = None
    depth: int = 0
    closed: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_proof_state(self) -> ProofState:
        return ProofState(
            state_id=self.state_id,
            task_id=self.task_id,
            goals_text=self.goals_text,
            local_context=self.local_context,
            target=self.target,
            raw_messages=list(self.raw_messages or []),
            features=dict(self.metadata.get("features") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["canonical_status"] = "persistent_worker_state_chart_only_not_canonical"
        return d


class PersistentLeanWorker:
    """Stateful proof-state worker.

    The worker stores a prefix for each proof state.  Applying a tactic to a
    state audits the theorem with `state.prefix + tactic`; if the result is a
    successful/partial/dry-run progress record, a child state is registered.
    This gives branch/rollback semantics even before a kernel-native Lean RPC
    backend is available.
    """

    def __init__(self, config: WorkerConfig | None = None):
        self.config = config or WorkerConfig()
        self.session_id = self.config.session_id or "persistent_lean_worker_" + stable_hash({"t": time.time(), "pid": os.getpid()}, n=12)
        self.project_fingerprint = project_fingerprint(self.config.workdir, lean_cmd=self.config.lean_cmd)
        self.loaded = False
        self.started_at = time.time()
        self.n_requests = 0
        self.n_failures = 0
        self.last_error: str | None = None
        self.states: dict[str, PersistentStateRecord] = {}
        self.tasks: dict[str, LeanTask] = {}
        self.executor = LeanExecutor(LeanExecutorConfig(
            lean_cmd=self.config.lean_cmd,
            workdir=self.config.workdir,
            timeout_s=self.config.timeout_s,
            keep_files=self.config.keep_files,
            dry_run=(self.config.backend == "dry_run"),
            cache_dir=self.config.cache_dir,
            trace_state=self.config.trace_state,
        ))

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "backend": "persistent_" + self.config.backend,
            "execution_backend": self.config.backend,
            "workdir": self.config.workdir,
            "lean_cmd": self.config.lean_cmd,
            "project_fingerprint": self.project_fingerprint,
            "loaded": self.loaded,
            "n_requests": self.n_requests,
            "n_failures": self.n_failures,
            "n_states": len(self.states),
            "n_tasks": len(self.tasks),
            "uptime_ms": (time.time() - self.started_at) * 1000.0,
            "last_error": self.last_error,
            "canonical_status": "persistent_worker_protocol_chart_not_kernel_canonical",
        }

    def load_project(self) -> dict[str, Any]:
        if self.loaded:
            return self.status()
        if self.config.backend == "file" and self.config.warmup:
            # A cheap environment sanity check.  This is not a persistent Lean
            # kernel load; it records project reachability and catches obvious
            # command/env failures early.
            try:
                cmd = shlex.split(self.config.lean_cmd) + ["--version"]
                proc = subprocess.run(cmd, cwd=self.config.workdir or os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=min(max(self.config.timeout_s, 1.0), 10.0))
                if proc.returncode != 0:
                    raise RuntimeError((proc.stderr or proc.stdout or "lean --version failed").strip())
            except Exception as e:
                self.last_error = str(e)
                self.n_failures += 1
                # Do not fail hard here; individual tactic calls still provide
                # authoritative failures.  The status reports the warmup issue.
        self.loaded = True
        return self.status()

    def register_task(self, task: LeanTask | dict[str, Any], *, state_id: str | None = None) -> dict[str, Any]:
        self.load_project()
        task = LeanTask.from_dict(task) if isinstance(task, dict) else task
        self.tasks[task.task_id] = task
        base = ProofState.from_task(task)
        sid = state_id or base.state_id
        rec = PersistentStateRecord(
            state_id=sid,
            task_id=task.task_id,
            task=task.to_dict(),
            prefix=task.prefix or "",
            target=task.statement,
            goals_text=base.goals_text or ("⊢ " + task.statement),
            local_context=base.local_context,
            raw_messages=list(base.raw_messages or []),
            depth=0,
            metadata={"source": "register_task", "project_fingerprint": self.project_fingerprint},
        )
        self.states[sid] = rec
        return {"state": rec.to_dict(), "status": self.status()}

    def get_state(self, state_id: str) -> dict[str, Any]:
        if state_id not in self.states:
            raise KeyError(f"unknown state_id: {state_id}")
        return self.states[state_id].to_dict()

    def list_states(self, task_id: str | None = None) -> list[dict[str, Any]]:
        rows = list(self.states.values())
        if task_id is not None:
            rows = [r for r in rows if r.task_id == task_id]
        return [r.to_dict() for r in sorted(rows, key=lambda r: (r.task_id, r.depth, r.created_at, r.state_id))]

    def branch_state(self, state_id: str, *, new_state_id: str | None = None) -> dict[str, Any]:
        src = self.states[state_id]
        dst = copy.deepcopy(src)
        dst.state_id = new_state_id or ("branch_" + stable_hash({"src": state_id, "t": time.time()}, n=12))
        dst.parent_state_id = state_id
        dst.metadata = dict(dst.metadata or {})
        dst.metadata.update({"source": "branch_state", "branched_from": state_id})
        dst.created_at = time.time()
        self.states[dst.state_id] = dst
        return dst.to_dict()

    def rollback_state(self, state_id: str, *, steps: int = 1) -> dict[str, Any]:
        cur = self.states[state_id]
        steps = max(0, int(steps or 0))
        while steps and cur.parent_state_id and cur.parent_state_id in self.states:
            cur = self.states[cur.parent_state_id]
            steps -= 1
        return cur.to_dict()

    @staticmethod
    def _join_prefix(prefix: str, tactic: str) -> str:
        prefix = (prefix or "").rstrip()
        tactic = (tactic or "").strip()
        if not prefix:
            return tactic
        if not tactic:
            return prefix
        return prefix + "\n" + tactic

    def _task_for_state(self, rec: PersistentStateRecord) -> LeanTask:
        task = LeanTask.from_dict(rec.task)
        # The state prefix is the proof prefix to replay before the new tactic.
        # In dry-run mode, simulate true persistent state by auditing the current
        # target directly; the file-backed real Lean path must keep the original
        # theorem statement and replay the prefix.
        if self.config.backend == "dry_run" and rec.target:
            task.statement = rec.target
            task.prefix = ""
        else:
            task.prefix = rec.prefix or ""
        return task

    def apply_tactic(self, *, task: LeanTask | dict[str, Any] | None = None, action: TacticAction | dict[str, Any], state_id: str | None = None, state: ProofState | dict[str, Any] | None = None, create_state: bool = True) -> dict[str, Any]:
        self.load_project()
        self.n_requests += 1
        action = TacticAction.from_dict(action) if isinstance(action, dict) else action
        if state_id is not None and state_id in self.states:
            before_rec = self.states[state_id]
        else:
            if task is None:
                if state is not None and not isinstance(state, ProofState):
                    state = ProofState.from_dict(state)
                if isinstance(state, ProofState) and state.task_id in self.tasks:
                    task = self.tasks[state.task_id]
                else:
                    raise ValueError("apply_tactic requires task or known state_id")
            before_rec = self.register_task(task if isinstance(task, LeanTask) else LeanTask.from_dict(task))["state"]
            before_rec = PersistentStateRecord(**{k: v for k, v in before_rec.items() if k in PersistentStateRecord.__dataclass_fields__})
        task_for_state = self._task_for_state(before_rec)
        before_state = before_rec.to_proof_state()
        before_kernel_state = self.kernel_state(before_rec.state_id)
        if self.config.backend == "dry_run":
            # The file-backed executor dry-run scores against task.statement.
            # For persistent states we want the current state target after prior
            # tactics, so expose that target to the dry-run chart.
            task_for_state = replace(task_for_state, statement=before_rec.target or task_for_state.statement)
        rec = self.executor.run_tactic(task_for_state, action, before_state)
        rec.audit_flags = dict(rec.audit_flags or {})
        rec.audit_flags.update({
            "persistent_lean_worker": True,
            "persistent_worker_session_id": self.session_id,
            "persistent_worker_backend": self.config.backend,
            "project_fingerprint": self.project_fingerprint,
            "before_persistent_state_id": before_rec.state_id,
        })
        after_state = rec.after_state or before_state
        new_rec: PersistentStateRecord | None = None
        if create_state and rec.status in {"success", "partial", "dry_run"}:
            new_prefix = self._join_prefix(before_rec.prefix, action.tactic)
            new_state_id = after_state.state_id or stable_hash({"parent": before_rec.state_id, "action": action.to_dict(), "prefix": new_prefix}, n=16)
            new_rec = PersistentStateRecord(
                state_id=new_state_id,
                task_id=before_rec.task_id,
                task=before_rec.task,
                prefix=new_prefix,
                target=after_state.target,
                goals_text=after_state.goals_text,
                local_context=after_state.local_context,
                raw_messages=list(after_state.raw_messages or rec.messages or []),
                parent_state_id=before_rec.state_id,
                applied_action_id=action.action_id,
                applied_tactic=action.tactic,
                depth=before_rec.depth + 1,
                closed=(rec.status == "success" and not (after_state.target or after_state.goals_text)),
                metadata={
                    "source": "apply_tactic",
                    "audit_status": rec.status,
                    "project_fingerprint": self.project_fingerprint,
                },
            )
            self.states[new_rec.state_id] = new_rec
            rec.after_state = new_rec.to_proof_state()
            rec.audit_flags["after_persistent_state_id"] = new_rec.state_id
        elif rec.status not in {"success", "partial", "dry_run"}:
            self.n_failures += 1
        kernel_state = self.kernel_state(new_rec.state_id if new_rec is not None else before_rec.state_id)
        try:
            state_delta = compute_goal_state_transition_delta(before_kernel_state, kernel_state, action=action.to_dict())
        except Exception as e:
            state_delta = {
                "schema_version": "lean-rgc-goal-state-transition-v47.0",
                "error": str(e),
                "before_state_id": before_rec.state_id,
                "after_state_id": new_rec.state_id if new_rec is not None else before_rec.state_id,
                "canonical_status": "goal_state_transition_delta_error_chart_not_canonical",
            }
        rec.audit_flags = dict(rec.audit_flags or {})
        rec.audit_flags.setdefault("kernel_state", kernel_state)
        rec.audit_flags.setdefault("kernel_state_after", kernel_state)
        rec.audit_flags.setdefault("kernel_state_before", before_kernel_state)
        rec.audit_flags.setdefault("kernel_state_hash", stable_hash(kernel_state, n=24))
        rec.audit_flags.setdefault("kernel_state_before_hash", stable_hash(before_kernel_state, n=24))
        rec.audit_flags.setdefault("state_delta", state_delta)
        rec.audit_flags.setdefault("goal_state_transition_api", True)
        return {
            "audit": rec.to_dict(),
            "before_state": before_rec.to_dict(),
            "after_state": new_rec.to_dict() if new_rec is not None else (after_state.to_dict() if hasattr(after_state, "to_dict") else None),
            "kernel_state": kernel_state,
            "kernel_state_before": before_kernel_state,
            "kernel_state_after": kernel_state,
            "state_delta": state_delta,
            "structured_state": PersistentLeanWorker.structured_state(self, new_rec.state_id if new_rec is not None else before_rec.state_id, audit=rec),
            "status": self.status(),
        }

    def kernel_state(self, state_id: str) -> dict[str, Any]:
        """Return a kernel-shaped proof-state payload.

        For the in-tree dry_run/file worker this is a faithful *protocol shape*
        backed by the worker's persistent state registry, not by Lean kernel
        memory.  A native Lean worker should implement the same command with
        Expr/fvar/mvar/typeclass JSON from the kernel.
        """
        if state_id not in self.states:
            raise KeyError(f"unknown state_id: {state_id}")
        rec = self.states[state_id]
        # Build local context entries from the current text chart while marking
        # their source as persistent-kernel-protocol fallback.
        local_nodes: list[dict[str, Any]] = []
        for i, line in enumerate((rec.local_context or rec.goals_text or "").splitlines()):
            if ":" not in line or "⊢" in line:
                continue
            left, typ = line.split(":", 1)
            name = left.strip().split()[-1] if left.strip() else f"h{i}"
            typ = typ.strip()
            if not name or not typ:
                continue
            local_nodes.append({
                "fvar_id": f"fvar_{stable_hash({'state': state_id, 'name': name}, n=10)}",
                "user_name": name,
                "name": name,
                "type": {"text": typ, "kind": "text_expr", "head": typ.split()[0] if typ.split() else "unknown"},
                "type_text": typ,
                "binder_kind": "default",
                "source": "persistent_worker_kernel_protocol_fallback",
            })
        target = "" if rec.closed else (rec.target or rec.goals_text or LeanTask.from_dict(rec.task).statement)
        goal_id = f"?m.{stable_hash({'state': state_id, 'target': target}, n=10)}"
        payload = {
            "schema_version": "lean-rgc-kernel-state-v1",
            "state_id": state_id,
            "task_id": rec.task_id,
            "env_fingerprint": self.project_fingerprint,
            "project_fingerprint": self.project_fingerprint,
            "backend": "persistent_worker_kernel_protocol_" + self.config.backend,
            "status": "closed" if rec.closed else "open",
            "closed": rec.closed,
            "goals": [] if rec.closed else [{
                "goal_id": "g0",
                "mvar_id": goal_id,
                "target": {"text": target, "kind": "text_expr", "head": "unknown"},
                "target_text": target,
                "local_deps": [n.get("fvar_id") for n in local_nodes if n.get("fvar_id")],
                "source": "persistent_worker_kernel_protocol_fallback",
            }],
            "local_context": {"nodes": local_nodes, "edges": [], "source": "persistent_worker_kernel_protocol_fallback"},
            "metavars": [] if rec.closed else [{"mvar_id": goal_id, "type_text": target, "assigned": False, "synthetic": True}],
            "typeclasses": [],
            "messages": list(rec.raw_messages or []),
            "prefix": rec.prefix or "",
            "proof_prefix": rec.prefix or "",
            "parent_state_id": rec.parent_state_id,
            "metadata": {
                "state_depth": rec.depth,
                "parent_state_id": rec.parent_state_id,
                "canonical_status": "kernel_protocol_payload_chart_not_native_kernel" if self.config.backend in {"dry_run", "file"} else "kernel_payload",
            },
            "object_coverage": {
                "expr_ast": False,
                "local_decl_graph": bool(local_nodes),
                "metavariable_graph": not rec.closed,
                "typeclass_graph": False,
                "in_memory_state_id": True,
                "tactic_transition_api": True,
                "replay_certificate": False,
                "source": "persistent_worker_kernel_protocol_" + self.config.backend,
            },
        }
        return normalize_kernel_state_v1(payload, env_fingerprint=self.project_fingerprint)

    def structured_state(self, state_id: str, *, audit: AuditRecord | dict[str, Any] | None = None) -> dict[str, Any]:
        if state_id not in self.states:
            raise KeyError(f"unknown state_id: {state_id}")
        rec = self.states[state_id]
        task = LeanTask.from_dict(rec.task)
        audit_obj = AuditRecord.from_dict(audit) if isinstance(audit, dict) else audit
        kernel = None
        if isinstance(audit, dict):
            flags = audit.get("audit_flags") or {}
            kernel = audit.get("kernel_state") if isinstance(audit.get("kernel_state"), dict) else flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        elif isinstance(audit_obj, AuditRecord):
            flags = audit_obj.audit_flags or {}
            kernel = flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        if kernel is None:
            kernel = self.kernel_state(state_id)
        return extract_structured_state_from_kernel_json(
            kernel,
            task=task,
            state=rec.to_proof_state(),
            audit=audit_obj,
            backend="persistent_worker_kernel_json_v28_" + self.config.backend,
            metadata={
                "persistent_worker_session_id": self.session_id,
                "project_fingerprint": self.project_fingerprint,
                "state_depth": rec.depth,
                "parent_state_id": rec.parent_state_id,
                "source": "persistent_worker.structured_state",
            },
        ).to_dict()

    def handle(self, req: dict[str, Any]) -> dict[str, Any]:
        cmd = req.get("cmd")
        try:
            if cmd == "load_project":
                return {"ok": True, **self.load_project()}
            if cmd in {"register_task", "init_state"}:
                return {"ok": True, **self.register_task(req.get("task") or {}, state_id=req.get("state_id"))}
            if cmd == "get_state":
                return {"ok": True, "state": self.get_state(str(req.get("state_id")))}
            if cmd == "list_states":
                return {"ok": True, "states": self.list_states(req.get("task_id"))}
            if cmd == "branch_state":
                src_id = str(req.get("state_id"))
                st = self.branch_state(src_id, new_state_id=req.get("new_state_id") or req.get("branch_id"))
                st.setdefault("branch_of", src_id)
                meta = dict(st.get("metadata") or {})
                meta.setdefault("branched_from", src_id)
                st["metadata"] = meta
                return {"ok": True, "state": st}
            if cmd == "rollback_state":
                return {"ok": True, "state": self.rollback_state(str(req.get("state_id")), steps=int(req.get("steps", 1)))}
            if cmd == "apply_tactic":
                return {"ok": True, **self.apply_tactic(task=req.get("task"), action=req.get("action") or {}, state_id=req.get("state_id") or (req.get("state") or {}).get("state_id"), state=req.get("state"), create_state=bool(req.get("create_state", True)))}
            if cmd == "structured_state":
                sid = str(req.get("state_id") or (req.get("state") or {}).get("state_id"))
                return {"ok": True, "kernel_state": self.kernel_state(sid), "structured_state": self.structured_state(sid, audit=req.get("audit"))}
            if cmd == "kernel_state":
                sid = str(req.get("state_id") or (req.get("state") or {}).get("state_id"))
                return {"ok": True, "kernel_state": self.kernel_state(sid)}
            if cmd == "status":
                return {"ok": True, **self.status()}
            if cmd == "shutdown":
                return {"ok": True, "shutdown": True, **self.status()}
            return {"ok": False, "error": f"unknown command: {cmd}"}
        except Exception as e:
            self.last_error = str(e)
            self.n_failures += 1
            return {"ok": False, "error": str(e), **self.status()}

    def serve_jsonl(self, inp: TextIO | None = None, out: TextIO | None = None) -> None:
        inp = inp or sys.stdin
        out = out or sys.stdout
        self.load_project()
        for line in inp:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception as e:
                rep = {"ok": False, "error": f"invalid json: {e}"}
            else:
                req_id = req.get("id")
                rep = self.handle(req)
                if req_id is not None:
                    rep["id"] = req_id
            out.write(json.dumps(rep, ensure_ascii=True, sort_keys=True) + "\n")
            out.flush()
            if rep.get("shutdown"):
                break


def make_worker_from_args(args: argparse.Namespace) -> PersistentLeanWorker:
    backend = args.backend
    if backend == "dry":
        backend = "dry_run"
    cfg = WorkerConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        backend=backend,
        keep_files=args.keep_files,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
        warmup=not args.no_warmup,
    )
    return PersistentLeanWorker(cfg)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lean-rgc-persistent-worker", description="Stateful JSONL Lean-RGC worker")
    p.add_argument("--backend", choices=["dry_run", "dry", "file"], default="dry_run")
    p.add_argument("--lean-cmd", default="lake env lean")
    p.add_argument("--workdir")
    p.add_argument("--timeout-s", type=float, default=20.0)
    p.add_argument("--keep-files", action="store_true")
    p.add_argument("--cache-dir")
    p.add_argument("--trace-state", action="store_true")
    p.add_argument("--no-warmup", action="store_true")
    args = p.parse_args(argv)
    worker = make_worker_from_args(args)
    worker.serve_jsonl()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
