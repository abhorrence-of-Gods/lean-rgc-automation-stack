from __future__ import annotations

"""Compatibility wrapper for the v27 persistent Lean worker.

Historically `lean_rgc.persistent_worker` exposed an early stateful worker API.
The maintained implementation now lives in `persistent_lean_worker`.  This file
keeps the old imports and direct-method return shapes stable.
"""

from typing import Any, TextIO
import sys

from .lean_server import LeanServerConfig
from .persistent_lean_worker import (
    PersistentLeanWorker as _BasePersistentLeanWorker,
    PersistentStateRecord,
    WorkerConfig,
    main as _base_main,
)


def _config_from_any(config: Any | None) -> WorkerConfig:
    if config is None:
        return WorkerConfig()
    if isinstance(config, WorkerConfig):
        return config
    # Accept the v21 LeanServerConfig for backward compatibility.
    if isinstance(config, LeanServerConfig):
        backend = "dry_run" if config.dry_run else "file"
        return WorkerConfig(
            lean_cmd=config.lean_cmd,
            workdir=config.workdir,
            timeout_s=config.timeout_s,
            backend=backend,
            keep_files=config.keep_files,
            cache_dir=config.cache_dir,
            trace_state=config.trace_state,
            session_id=config.session_id,
        )
    # Duck-type enough fields for tests and old callers.
    backend = "dry_run" if bool(getattr(config, "dry_run", False)) else str(getattr(config, "backend", "file"))
    if backend in {"auto", "file_fallback", "jsonl", "persistent"}:
        backend = "file"
    return WorkerConfig(
        lean_cmd=str(getattr(config, "lean_cmd", "lake env lean")),
        workdir=getattr(config, "workdir", None),
        timeout_s=float(getattr(config, "timeout_s", 20.0)),
        backend=backend,
        keep_files=bool(getattr(config, "keep_files", False)),
        cache_dir=getattr(config, "cache_dir", None),
        trace_state=bool(getattr(config, "trace_state", False)),
        session_id=getattr(config, "session_id", None),
    )


class PersistentLeanWorker(_BasePersistentLeanWorker):
    def __init__(self, config: Any | None = None):
        super().__init__(_config_from_any(config))

    def init_state(self, task, *, prefix=None, state=None):
        # Old API name for `register_task`.
        if prefix is not None:
            if hasattr(task, "to_dict"):
                d = task.to_dict()
            else:
                d = dict(task)
            d["prefix"] = prefix
            task = d
        rep = self.register_task(task)
        return {"ok": True, **rep}

    def branch_state(self, state_id: str, *, branch_id: str | None = None):
        return {"ok": True, "state": super().branch_state(state_id, new_state_id=branch_id)}

    def rollback_state(self, state_id: str, steps: int = 1):
        return {"ok": True, "state": super().rollback_state(state_id, steps=steps)}

    def list_states(self, task_id: str | None = None):
        rows = super().list_states(task_id)
        return {"ok": True, "states": rows, "n": len(rows)}

    def structured_state(self, task, state_id: str | None = None, audit=None):
        if state_id is None:
            init = self.init_state(task)
            state_id = init["state"]["state_id"]
        ss = super().structured_state(state_id, audit=audit)
        ss["canonical_status"] = "persistent_structured_state_chart_not_kernel_canonical"
        return {"ok": True, "structured_state": ss}

    def apply_tactic(self, task, action, *, state_id: str | None = None, state=None, commit_failures: bool = False):
        rep = super().apply_tactic(task=task, action=action, state_id=state_id, state=state, create_state=True)
        audit = rep.get("audit") or {}
        accepted = audit.get("status") in {"success", "partial", "dry_run"}
        rep.setdefault("ok", True)
        rep.setdefault("accepted_transition", bool(accepted))
        return rep

    def handle(self, req: dict[str, Any]) -> dict[str, Any]:
        rid = req.get("id")
        cmd = req.get("cmd")
        try:
            if cmd == "load_project":
                return {"id": rid, "ok": True, **self.load_project()}
            if cmd in {"init_state", "register_task"}:
                return {"id": rid, **self.init_state(req.get("task") or {}, prefix=req.get("prefix"), state=req.get("state"))}
            if cmd == "apply_tactic":
                return {"id": rid, **self.apply_tactic(req.get("task"), req.get("action") or {}, state_id=req.get("state_id") or (req.get("state") or {}).get("state_id"), state=req.get("state"), commit_failures=bool(req.get("commit_failures", False)))}
            if cmd == "get_state":
                try:
                    return {"id": rid, "ok": True, "state": super().get_state(str(req.get("state_id") or ""))}
                except Exception as e:
                    return {"id": rid, "ok": False, "error": str(e)}
            if cmd == "branch_state":
                return {"id": rid, **self.branch_state(str(req.get("state_id") or ""), branch_id=req.get("branch_id") or req.get("new_state_id"))}
            if cmd == "rollback_state":
                return {"id": rid, **self.rollback_state(str(req.get("state_id") or ""), steps=int(req.get("steps") or 1))}
            if cmd == "list_states":
                return {"id": rid, **self.list_states(req.get("task_id"))}
            if cmd == "structured_state":
                return {"id": rid, **self.structured_state(req.get("task") or {}, state_id=req.get("state_id"), audit=req.get("audit"))}
            if cmd in {"health", "status"}:
                return {"id": rid, "ok": True, "status": self.status()}
            if cmd == "shutdown":
                return {"id": rid, "ok": True, "shutdown": True, "status": self.status()}
            return {"id": rid, "ok": False, "error": f"unknown command: {cmd}"}
        except Exception as e:
            self.n_failures += 1
            self.last_error = str(e)
            return {"id": rid, "ok": False, "error": str(e), "status": self.status()}


def serve_jsonl(config: Any | None = None, *, inp: TextIO | None = None, out: TextIO | None = None) -> int:
    worker = PersistentLeanWorker(config)
    worker.serve_jsonl(inp=inp, out=out)
    return 0


def run_persistent_worker(config: Any | None = None, *, inp: TextIO | None = None, out: TextIO | None = None) -> int:
    return serve_jsonl(config, inp=inp, out=out)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Compatibility: v21/v27 adapter docs use --dry-run; the maintained
    # persistent_lean_worker CLI uses --backend dry_run.
    if "--dry-run" in argv:
        argv = [x for x in argv if x != "--dry-run"]
        if "--backend" not in argv:
            argv = ["--backend", "dry_run"] + argv
    return _base_main(argv)


__all__ = [
    "PersistentLeanWorker",
    "PersistentStateRecord",
    "WorkerConfig",
    "serve_jsonl",
    "run_persistent_worker",
    "main",
]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
