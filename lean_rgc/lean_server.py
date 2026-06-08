from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import sys

from .schemas import AuditRecord, LeanTask, ProofState, TacticAction, stable_hash, write_jsonl, read_jsonl
from .executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor
from .dataset import summarize_response_rows
from .structured_state import extract_structured_state, extract_structured_state_from_kernel_json
from .native_worker import native_worker_command, native_worker_manifest


@dataclass
class LeanServerConfig:
    """Configuration for the v21 Lean server adapter.

    The adapter exposes a persistent-worker shaped API.  In environments with a
    real JSONL Lean worker, set `server_cmd`.  Otherwise the adapter keeps the
    API and metadata stable while falling back to the existing file executor.
    This makes server-backed and file-backed audits schema-compatible.
    """

    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    dry_run: bool = False
    keep_files: bool = False
    cache_dir: str | None = None
    trace_state: bool = False
    server_cmd: str | None = None
    backend: str = "auto"  # auto | dry_run | file | file_fallback | jsonl | persistent | native
    startup_timeout_s: float = 10.0
    request_timeout_s: float | None = None
    fallback_to_file: bool = True
    session_id: str | None = None
    native_exec_mode: str = "source_check"  # source_check | heuristic | kernel_rpc, passed to native worker
    stateful_kernel_rpc: bool = True


@dataclass
class LeanServerStatus:
    session_id: str
    backend: str
    requested_backend: str
    workdir: str | None
    lean_cmd: str
    server_cmd: str | None
    project_fingerprint: str
    loaded: bool = False
    n_requests: int = 0
    n_failures: int = 0
    started_at: float = field(default_factory=time.time)
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["uptime_ms"] = (time.time() - self.started_at) * 1000.0
        return d


def _safe_read(path: Path, limit: int = 200_000) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def project_fingerprint(workdir: str | None, *, lean_cmd: str = "lake env lean") -> str:
    """Conservative project fingerprint for cache/server metadata.

    This is not a proof of environment identity.  It is a system-level guard that
    records the obvious environment files; v22/v24 can strengthen it with Lean
    environment hashes.
    """
    root = Path(workdir or os.getcwd())
    parts: dict[str, Any] = {"root": str(root.resolve()) if root.exists() else str(root), "lean_cmd": lean_cmd}
    for name in ["lean-toolchain", "lakefile.lean", "lakefile.toml", "lake-manifest.json", "lake-manifest.toml"]:
        p = root / name
        if p.exists():
            txt = _safe_read(p)
            parts[name] = stable_hash({"content": txt, "size": p.stat().st_size}, n=16)
    return stable_hash(parts, n=20)



_AUDIT_RECORD_KEYS = {
    "task_id", "state_id", "action_id", "status", "elapsed_ms", "heartbeats",
    "stdout", "stderr", "messages", "after_state", "defect_before", "defect_after",
    "response", "carrier_delta", "audit_flags", "lean_file",
}


def _audit_record_from_server_payload(rep: dict[str, Any]) -> tuple[AuditRecord, dict[str, Any] | None, dict[str, Any] | None]:
    """Parse a JSONL worker apply_tactic response.

    True kernel workers may return kernel_state / structured_state side-channel
    fields alongside an AuditRecord.  AuditRecord is intentionally stable, so
    we strip side-channel fields and return them separately.
    """
    rec_data = rep.get("audit") or rep.get("record") or rep
    rec_data = dict(rec_data or {})
    kernel_state = rep.get("kernel_state") or rec_data.pop("kernel_state", None)
    kernel_state_before = rep.get("kernel_state_before") or rec_data.pop("kernel_state_before", None)
    kernel_state_after = rep.get("kernel_state_after") or rec_data.pop("kernel_state_after", None)
    state_delta = rep.get("state_delta") or rec_data.pop("state_delta", None)
    structured_state = rep.get("structured_state") or rec_data.pop("structured_state", None)
    if kernel_state_before is not None or kernel_state_after is not None or state_delta is not None:
        flags = dict(rec_data.get("audit_flags") or {})
        if isinstance(kernel_state_before, dict): flags["kernel_state_before"] = kernel_state_before
        if isinstance(kernel_state_after, dict): flags["kernel_state_after"] = kernel_state_after
        if isinstance(state_delta, dict): flags["state_delta"] = state_delta
        if isinstance(kernel_state_after, dict) and kernel_state is None: kernel_state = kernel_state_after
        flags["goal_state_transition_api"] = True
        rec_data["audit_flags"] = flags
    # Preserve unknown server-side fields as audit_flags.extra rather than
    # breaking AuditRecord.from_dict.
    extra = {k: rec_data.pop(k) for k in list(rec_data.keys()) if k not in _AUDIT_RECORD_KEYS}
    if extra:
        flags = dict(rec_data.get("audit_flags") or {})
        flags.setdefault("server_extra", {}).update(extra)
        rec_data["audit_flags"] = flags
    rec = AuditRecord.from_dict(rec_data)
    return rec, kernel_state if isinstance(kernel_state, dict) else None, structured_state if isinstance(structured_state, dict) else None

class _JsonlServerProcess:
    """Minimal JSONL protocol wrapper for a future Lean worker.

    Expected protocol:
      request: {"id": ..., "cmd": "load_project" | "apply_tactic" | "shutdown", ...}
      response: {"id": ..., "ok": true/false, ...}

    This module does not impose a Lean-side implementation; it lets v21 callers
    use the same Python API once such a worker exists.
    """

    def __init__(self, cmd: str, *, cwd: str | None, timeout_s: float):
        self.cmd = cmd
        self.cwd = cwd
        self.timeout_s = timeout_s
        env = os.environ.copy()
        pkg_root = str(Path(__file__).resolve().parents[1])
        env["PYTHONPATH"] = pkg_root + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        if os.name == "nt":
            # ``shlex.split`` in POSIX mode drops backslashes from unquoted
            # Windows paths, while ``posix=False`` keeps quote characters from
            # commands produced by ``shlex.join``.  Dispatch on the presence of
            # quotes so both hand-written and generated commands work.
            cmd_arg = shlex.split(cmd) if ("'" in cmd or '"' in cmd) else shlex.split(cmd, posix=False)
        else:
            cmd_arg = shlex.split(cmd)
        self.proc = subprocess.Popen(
            cmd_arg,
            cwd=cwd or os.getcwd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        self._lock = threading.Lock()
        self._stderr_lines: list[str] = []
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        try:
            assert self.proc.stderr is not None
            for line in self.proc.stderr:
                self._stderr_lines.append(line.rstrip())
                if len(self._stderr_lines) > 200:
                    self._stderr_lines = self._stderr_lines[-200:]
        except Exception:
            return

    def request(self, payload: dict[str, Any], *, timeout_s: float | None = None) -> dict[str, Any]:
        timeout = max(float(timeout_s or self.timeout_s), 5.0)
        payload = dict(payload)
        payload.setdefault("id", stable_hash({"payload": payload, "t": time.time()}, n=12))
        with self._lock:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server process exited with code {self.proc.returncode}: {'; '.join(self._stderr_lines[-10:])}")
            assert self.proc.stdin is not None and self.proc.stdout is not None
            self.proc.stdin.write(json.dumps(payload, ensure_ascii=True) + "\n")
            self.proc.stdin.flush()
            out_q: queue.Queue[str] = queue.Queue(maxsize=1)

            def reader():
                try:
                    out_q.put(self.proc.stdout.readline())
                except Exception as e:
                    out_q.put(json.dumps({"ok": False, "error": str(e)}))

            deadline = time.monotonic() + timeout
            non_json_stdout: list[str] = []
            while True:
                if self.proc.poll() is not None:
                    raise RuntimeError(
                        "server process exited with code "
                        f"{self.proc.returncode}; stdout={'; '.join(non_json_stdout[-10:])}; "
                        f"stderr={'; '.join(self._stderr_lines[-20:])}"
                    )
                remaining = max(0.0, deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError(
                        f"Lean server request timed out after {timeout}s; "
                        f"stdout={'; '.join(non_json_stdout[-10:])}; "
                        f"stderr={'; '.join(self._stderr_lines[-20:])}"
                    )
                th = threading.Thread(target=reader, daemon=True)
                th.start()
                try:
                    line = out_q.get(timeout=remaining)
                except queue.Empty as e:
                    raise TimeoutError(
                        f"Lean server request timed out after {timeout}s; "
                        f"stdout={'; '.join(non_json_stdout[-10:])}; "
                        f"stderr={'; '.join(self._stderr_lines[-20:])}"
                    ) from e
                if not line:
                    raise RuntimeError(
                        f"server returned EOF; stdout={'; '.join(non_json_stdout[-10:])}; "
                        f"stderr={'; '.join(self._stderr_lines[-20:])}"
                    )
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    non_json_stdout.append(line.rstrip())
                    if len(non_json_stdout) > 200:
                        non_json_stdout = non_json_stdout[-200:]
                    continue


    def apply_tactic_to_state_id(self, task: LeanTask, action: TacticAction, state_id: str, *, create_state: bool = True) -> AuditRecord:
        """Apply an action to a server-side persistent state id.

        This is the stateful API required for branch/rollback workflows.  File
        fallback cannot support server-side state ids, so it raises unless a
        JSONL/persistent backend is active.
        """
        self.start()
        self.status.n_requests += 1
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({
                "cmd": "apply_tactic",
                "task": task.to_dict(),
                "action": action.to_dict(),
                "state_id": state_id,
                "create_state": create_state,
                "timeout_s": self.config.timeout_s,
                "trace_state": self.config.trace_state,
            }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            rec, kernel_state, structured_payload = _audit_record_from_server_payload(rep)
            if kernel_state is not None:
                rec.audit_flags = dict(rec.audit_flags or {})
                rec.audit_flags["kernel_state"] = kernel_state
                rec.audit_flags["kernel_state_hash"] = stable_hash(kernel_state, n=24)
                rec.audit_flags["structured_state_backend"] = "kernel_json_v28"
            elif structured_payload is not None:
                rec.audit_flags = dict(rec.audit_flags or {})
                rec.audit_flags["structured_state_payload"] = structured_payload
                rec.audit_flags["structured_state_backend"] = structured_payload.get("extraction_backend") or "server_structured_state"
            rec.audit_flags = dict(rec.audit_flags or {})
            rec.audit_flags.update({
                "lean_server_adapter": True,
                "server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "stateful_apply": True,
            })
            return rec
        raise RuntimeError("apply_tactic_to_state_id requires jsonl/persistent backend")

    def run_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        """Backward-compatible alias used by executor-like callers."""
        return self.apply_tactic(task, action, state)

    def structured_state(self, task: LeanTask, state: ProofState | None = None, audit: AuditRecord | None = None) -> dict[str, Any]:
        """Return v28 structured state, preferring kernel JSON when available.

        A true Lean worker may return kernel_state / structured_state through the
        JSONL protocol.  File fallback remains text-derived, but the schema is
        stable across both modes.
        """
        if state is None:
            state = audit.after_state if audit is not None and audit.after_state is not None else ProofState.from_task(task)
        flags = dict(audit.audit_flags or {}) if audit is not None else {}
        kernel_state = flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        if kernel_state is not None:
            return extract_structured_state_from_kernel_json(kernel_state, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                "lean_server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "source": "audit_flags.kernel_state",
            }).to_dict()
        structured_payload = flags.get("structured_state_payload") if isinstance(flags.get("structured_state_payload"), dict) else None
        if structured_payload is not None and isinstance(structured_payload.get("goals"), list):
            return structured_payload
        if self.status.backend == "jsonl" and self._jsonl is not None:
            try:
                rep = self._jsonl.request({
                    "cmd": "structured_state",
                    "task": task.to_dict(),
                    "state": state.to_dict(),
                    "state_id": state.state_id,
                    "audit": audit.to_dict() if audit is not None else None,
                    "kernel": True,
                }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
                if rep.get("ok", True):
                    k = rep.get("kernel_state")
                    if isinstance(k, dict):
                        return extract_structured_state_from_kernel_json(k, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                            "lean_server_session_id": self.session_id,
                            "server_backend": self.status.backend,
                            "project_fingerprint": self.status.project_fingerprint,
                            "source": "jsonl_worker.structured_state.kernel_state",
                        }).to_dict()
                    ss = rep.get("structured_state")
                    if isinstance(ss, dict):
                        if ss.get("schema_version", "").startswith("lean-rgc-structured-state"):
                            return ss
                        if ss.get("schema_version", "").startswith("lean-rgc-kernel-state") or ss.get("goals"):
                            return extract_structured_state_from_kernel_json(ss, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                                "lean_server_session_id": self.session_id,
                                "server_backend": self.status.backend,
                                "project_fingerprint": self.status.project_fingerprint,
                                "source": "jsonl_worker.structured_state.payload",
                            }).to_dict()
            except Exception:
                pass
        return extract_structured_state(
            task=task,
            state=state,
            audit=audit,
            backend=str(self.status.backend or "server_adapter_v28"),
            metadata={
                "lean_server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
            },
        ).to_dict()


    def register_task(self, task: LeanTask) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "register_task", "task": task.to_dict()}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep
        state = ProofState.from_task(task)
        return {"ok": True, "state": state.to_dict(), "status": self.status.to_dict(), "note": "file_fallback_stateless_register_task"}

    def get_state(self, state_id: str) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "get_state", "state_id": state_id}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep.get("state") or rep
        raise KeyError("state registry is available only for jsonl/persistent backend")

    def branch_state(self, state_id: str, *, new_state_id: str | None = None) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "branch_state", "state_id": state_id, "new_state_id": new_state_id}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            state = rep.get("state") or rep
            if isinstance(state, dict):
                state.setdefault("branch_of", state_id)
                meta = dict(state.get("metadata") or {})
                meta.setdefault("branched_from", state_id)
                state["metadata"] = meta
            return state
        raise RuntimeError("branch_state requires jsonl/persistent backend")

    def rollback_state(self, state_id: str, *, steps: int = 1) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "rollback_state", "state_id": state_id, "steps": steps}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep.get("state") or rep
        raise RuntimeError("rollback_state requires jsonl/persistent backend")

    @property
    def info(self) -> LeanServerStatus:
        """Backward-compatible status alias used by early v21 CLI hooks."""
        return self.status

    def run_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        """Backward-compatible alias for apply_tactic."""
        return self.apply_tactic(task, action, state)

    def structured_state(self, task: LeanTask, state: ProofState | None = None, audit: AuditRecord | None = None, record: AuditRecord | None = None) -> dict[str, Any]:
        """Return v28 structured state, preferring kernel JSON when available.

        This duplicate-compatible signature keeps older callers that passed
        `record=` working while using the v28 kernel-normalization path.
        """
        audit = audit or record
        if state is None:
            state = audit.after_state if audit is not None and audit.after_state is not None else ProofState.from_task(task)
        flags = dict(audit.audit_flags or {}) if audit is not None else {}
        kernel_state = flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        if kernel_state is not None:
            return extract_structured_state_from_kernel_json(kernel_state, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                "lean_server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "source": "audit_flags.kernel_state",
            }).to_dict()
        structured_payload = flags.get("structured_state_payload") if isinstance(flags.get("structured_state_payload"), dict) else None
        if structured_payload is not None and isinstance(structured_payload.get("goals"), list):
            return structured_payload
        if self.status.backend == "jsonl" and self._jsonl is not None:
            try:
                rep = self._jsonl.request({
                    "cmd": "structured_state",
                    "task": task.to_dict(),
                    "state": state.to_dict(),
                    "state_id": state.state_id,
                    "audit": audit.to_dict() if audit is not None else None,
                    "kernel": True,
                }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
                if rep.get("ok", True):
                    k = rep.get("kernel_state")
                    if isinstance(k, dict):
                        return extract_structured_state_from_kernel_json(k, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                            "lean_server_session_id": self.session_id,
                            "server_backend": self.status.backend,
                            "project_fingerprint": self.status.project_fingerprint,
                            "source": "jsonl_worker.structured_state.kernel_state",
                        }).to_dict()
                    ss = rep.get("structured_state")
                    if isinstance(ss, dict):
                        if ss.get("schema_version", "").startswith("lean-rgc-structured-state"):
                            return ss
                        if ss.get("schema_version", "").startswith("lean-rgc-kernel-state") or ss.get("goals"):
                            return extract_structured_state_from_kernel_json(ss, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                                "lean_server_session_id": self.session_id,
                                "server_backend": self.status.backend,
                                "project_fingerprint": self.status.project_fingerprint,
                                "source": "jsonl_worker.structured_state.payload",
                            }).to_dict()
            except Exception:
                pass
        return extract_structured_state(
            task=task,
            state=state,
            audit=audit,
            backend=str(self.status.backend or "server_adapter_v28"),
            metadata={
                "lean_server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
            },
        ).to_dict()

    def close(self) -> None:
        try:
            if self.proc.poll() is None:
                try:
                    self.request({"cmd": "shutdown"}, timeout_s=2.0)
                except Exception:
                    pass
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except Exception:
            pass


class LeanServerAdapter:
    """Persistent-worker shaped Lean adapter.

    v21 deliberately separates API from backend.  A true persistent Lean server can
    implement the JSONL protocol; until then, file fallback keeps downstream RGC
    stages schema-compatible and makes migration incremental.
    """

    def __init__(self, config: LeanServerConfig | None = None):
        self.config = config or LeanServerConfig()
        if self.config.workdir:
            self.config.workdir = str(Path(self.config.workdir).resolve())
        self.session_id = self.config.session_id or "lean_server_" + stable_hash({"t": time.time(), "pid": os.getpid()}, n=12)
        req = self.config.backend or "auto"
        if req in {"native", "persistent"} and self.config.startup_timeout_s <= 10.0:
            self.config.startup_timeout_s = max(60.0, float(self.config.timeout_s))
        if req == "auto":
            if self.config.dry_run:
                backend = "dry_run"
            elif self.config.server_cmd:
                backend = "jsonl"
            else:
                backend = "file_fallback"
        else:
            backend = req
        if backend == "file":
            backend = "file_fallback"
        if backend == "native":
            backend = "jsonl"
            if not self.config.server_cmd:
                cmd = [sys.executable, "-m", "lean_rgc.native_worker", "--lean-cmd", self.config.lean_cmd, "--exec-mode", self.config.native_exec_mode]
                if self.config.workdir:
                    cmd += ["--workdir", self.config.workdir]
                self.config.server_cmd = shlex.join(cmd)
        if backend == "persistent":
            backend = "jsonl"
            if not self.config.server_cmd:
                worker_backend = "dry_run" if self.config.dry_run else "file"
                cmd = [sys.executable, "-m", "lean_rgc.persistent_lean_worker", "--backend", worker_backend, "--lean-cmd", self.config.lean_cmd, "--timeout-s", str(self.config.timeout_s)]
                if self.config.workdir:
                    cmd += ["--workdir", self.config.workdir]
                if self.config.keep_files:
                    cmd += ["--keep-files"]
                if self.config.cache_dir:
                    cmd += ["--cache-dir", self.config.cache_dir]
                if self.config.trace_state:
                    cmd += ["--trace-state"]
                self.config.server_cmd = shlex.join(cmd)
        self.status = LeanServerStatus(
            session_id=self.session_id,
            backend=backend,
            requested_backend=req,
            workdir=self.config.workdir,
            lean_cmd=self.config.lean_cmd,
            server_cmd=self.config.server_cmd,
            project_fingerprint=project_fingerprint(self.config.workdir, lean_cmd=self.config.lean_cmd),
        )
        self._jsonl: _JsonlServerProcess | None = None
        self._executor: LeanExecutor | None = None

    def __enter__(self) -> "LeanServerAdapter":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        if self.status.loaded:
            return
        if self.status.backend == "native" and not self.config.server_cmd:
            cmd = [sys.executable, "-m", "lean_rgc.native_worker", "--lean-cmd", self.config.lean_cmd, "--exec-mode", self.config.native_exec_mode]
            if self.config.workdir:
                cmd += ["--workdir", self.config.workdir]
            self.config.server_cmd = " ".join(shlex.quote(x) for x in cmd)
            self.status.server_cmd = self.config.server_cmd
            self.status.backend = "jsonl"
        if self.status.backend == "persistent" and not self.config.server_cmd:
            worker_backend = "dry_run" if (self.config.dry_run or self.config.backend == "dry_run") else "file"
            cmd = [sys.executable, "-m", "lean_rgc.persistent_lean_worker", "--backend", worker_backend, "--lean-cmd", self.config.lean_cmd, "--timeout-s", str(self.config.timeout_s)]
            if self.config.workdir:
                cmd += ["--workdir", self.config.workdir]
            if self.config.keep_files:
                cmd += ["--keep-files"]
            if self.config.cache_dir:
                cmd += ["--cache-dir", self.config.cache_dir]
            if self.config.trace_state:
                cmd += ["--trace-state"]
            self.config.server_cmd = " ".join(shlex.quote(x) for x in cmd)
            self.status.server_cmd = self.config.server_cmd
            self.status.backend = "jsonl"
        if self.status.backend == "jsonl":
            if not self.config.server_cmd:
                if self.config.fallback_to_file:
                    self.status.backend = "file_fallback"
                else:
                    raise ValueError("backend=jsonl requires server_cmd")
            else:
                try:
                    self._jsonl = _JsonlServerProcess(self.config.server_cmd, cwd=self.config.workdir, timeout_s=self.config.startup_timeout_s)
                    rep = self._jsonl.request({"cmd": "load_project", "workdir": self.config.workdir, "lean_cmd": self.config.lean_cmd, "trace_state": self.config.trace_state, "native_exec_mode": self.config.native_exec_mode, "timeout_s": int(self.config.timeout_s)}, timeout_s=self.config.startup_timeout_s)
                    if not rep.get("ok", True):
                        raise RuntimeError(str(rep.get("error") or rep))
                except Exception as e:
                    self.status.last_error = str(e)
                    self.status.n_failures += 1
                    if not self.config.fallback_to_file:
                        raise
                    self.status.backend = "file_fallback"
                    if self._jsonl is not None:
                        self._jsonl.close()
                        self._jsonl = None
        if self.status.backend in {"dry_run", "file", "file_fallback"}:
            ex_cfg = LeanExecutorConfig(
                lean_cmd=self.config.lean_cmd,
                workdir=self.config.workdir,
                timeout_s=self.config.timeout_s,
                keep_files=self.config.keep_files,
                dry_run=(self.status.backend == "dry_run" or self.config.dry_run),
                cache_dir=self.config.cache_dir,
                trace_state=self.config.trace_state,
            )
            self._executor = LeanExecutor(ex_cfg)
        self.status.loaded = True

    def load_project(self) -> dict[str, Any]:
        self.start()
        return self.status.to_dict()

    def health(self) -> dict[str, Any]:
        self.start()
        return self.status.to_dict()

    def apply_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        self.start()
        self.status.n_requests += 1
        state = state or ProofState.from_task(task)
        t0 = time.time()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            try:
                rep = self._jsonl.request({
                    "cmd": "apply_tactic",
                    "task": task.to_dict(),
                    "action": action.to_dict(),
                    "state": state.to_dict(),
                    "timeout_s": self.config.timeout_s,
                    "trace_state": self.config.trace_state,
                }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
                if not rep.get("ok", True):
                    raise RuntimeError(str(rep.get("error") or rep))
                rec, kernel_state, structured_payload = _audit_record_from_server_payload(rep)
                if kernel_state is not None:
                    rec.audit_flags = dict(rec.audit_flags or {})
                    rec.audit_flags["kernel_state"] = kernel_state
                    rec.audit_flags["kernel_state_hash"] = stable_hash(kernel_state, n=24)
                    rec.audit_flags["structured_state_backend"] = "kernel_json_v28"
                elif structured_payload is not None:
                    rec.audit_flags = dict(rec.audit_flags or {})
                    rec.audit_flags["structured_state_payload"] = structured_payload
                    rec.audit_flags["structured_state_backend"] = structured_payload.get("extraction_backend") or "server_structured_state"
            except Exception as e:
                self.status.last_error = str(e)
                self.status.n_failures += 1
                if not self.config.fallback_to_file:
                    raise
                # Fail soft to file executor while preserving server metadata.
                if self._executor is None:
                    self.status.backend = "file_fallback"
                    self.status.loaded = False
                    self.start()
                assert self._executor is not None
                rec = self._executor.run_tactic(task, action, state)
        else:
            assert self._executor is not None
            rec = self._executor.run_tactic(task, action, state)
        rec.audit_flags = dict(rec.audit_flags or {})
        rec.audit_flags.update({
            "lean_server_adapter": True,
            "server_session_id": self.session_id,
            "server_backend": self.status.backend,
            "project_fingerprint": self.status.project_fingerprint,
        })
        # Add a stable side-channel to stdout-free successful records.
        rec.elapsed_ms = rec.elapsed_ms or ((time.time() - t0) * 1000.0)
        return rec

    def apply_tactic_to_state_id(self, task: LeanTask, action: TacticAction, state_id: str, *, create_state: bool = True) -> AuditRecord:
        """Apply an action to a server-side persistent state id.

        This is the stateful v27 API.  It requires a JSONL/persistent backend and
        returns an AuditRecord whose after_state is also registered inside the
        worker when the transition is accepted.
        """
        self.start()
        self.status.n_requests += 1
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({
                "cmd": "apply_tactic",
                "task": task.to_dict(),
                "action": action.to_dict(),
                "state_id": state_id,
                "create_state": create_state,
                "timeout_s": self.config.timeout_s,
                "trace_state": self.config.trace_state,
            }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            rec, kernel_state, structured_payload = _audit_record_from_server_payload(rep)
            rec.audit_flags = dict(rec.audit_flags or {})
            if kernel_state is not None:
                rec.audit_flags["kernel_state"] = kernel_state
                rec.audit_flags["kernel_state_hash"] = stable_hash(kernel_state, n=24)
                rec.audit_flags["structured_state_backend"] = "kernel_json_v28"
            elif structured_payload is not None:
                rec.audit_flags["structured_state_payload"] = structured_payload
                rec.audit_flags["structured_state_backend"] = structured_payload.get("extraction_backend") or "server_structured_state"
            rec.audit_flags.update({
                "lean_server_adapter": True,
                "server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "stateful_apply": True,
            })
            return rec
        raise RuntimeError("apply_tactic_to_state_id requires jsonl/persistent backend")

    def run_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        """Backward-compatible alias used by executor-like callers."""
        return self.apply_tactic(task, action, state)

    def structured_state(self, task: LeanTask, state: ProofState | None = None, audit: AuditRecord | None = None) -> dict[str, Any]:
        """Return a structured proof-state chart for v21 callers.

        The current implementation is still a chart extracted from task/state/audit
        text.  v22 should replace this with kernel/Expr-backed state data.
        """
        if state is None:
            state = audit.after_state if audit is not None and audit.after_state is not None else ProofState.from_task(task)
        return extract_structured_state(
            task=task,
            state=state,
            audit=audit,
            backend=str(self.status.backend or "server_adapter_v22"),
            metadata={
                "lean_server_session_id": self.session_id,
                "server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
            },
        ).to_dict()


    def register_task(self, task: LeanTask) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "register_task", "task": task.to_dict()}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep
        state = ProofState.from_task(task)
        return {"ok": True, "state": state.to_dict(), "status": self.status.to_dict(), "note": "file_fallback_stateless_register_task"}

    def get_state(self, state_id: str) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "get_state", "state_id": state_id}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep.get("state") or rep
        raise KeyError("state registry is available only for jsonl/persistent backend")

    def branch_state(self, state_id: str, *, new_state_id: str | None = None) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "branch_state", "state_id": state_id, "new_state_id": new_state_id}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            state = rep.get("state") or rep
            if isinstance(state, dict):
                state.setdefault("branch_of", state_id)
                meta = dict(state.get("metadata") or {})
                meta.setdefault("branched_from", state_id)
                state["metadata"] = meta
            return state
        raise RuntimeError("branch_state requires jsonl/persistent backend")

    def rollback_state(self, state_id: str, *, steps: int = 1) -> dict[str, Any]:
        self.start()
        if self.status.backend == "jsonl" and self._jsonl is not None:
            rep = self._jsonl.request({"cmd": "rollback_state", "state_id": state_id, "steps": steps}, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
            if not rep.get("ok", True):
                raise RuntimeError(str(rep.get("error") or rep))
            return rep.get("state") or rep
        raise RuntimeError("rollback_state requires jsonl/persistent backend")

    @property
    def info(self) -> LeanServerStatus:
        """Backward-compatible status alias used by early v21 CLI hooks."""
        return self.status

    def run_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        """Backward-compatible alias for apply_tactic."""
        return self.apply_tactic(task, action, state)

    def structured_state(self, task: LeanTask, state: ProofState, record: AuditRecord | None = None) -> dict[str, Any]:
        """Return a minimal structured-state envelope.

        v21 is an adapter layer: real Lean AST extraction is v22.  This method
        preserves a stable API and explicitly marks the result as a structured
        chart rather than a kernel-native AST.
        """
        return {
            "state_id": state.state_id,
            "task_id": state.task_id or task.task_id,
            "target": state.target or task.statement,
            "goals_text": state.goals_text,
            "local_context": state.local_context,
            "raw_messages": list(state.raw_messages or []),
            "features": dict(state.features or {}),
            "messages": list((record.messages if record else []) or []),
            "server_backend": self.status.backend,
            "server_session_id": self.session_id,
            "project_fingerprint": self.status.project_fingerprint,
            "canonical_status": "structured_state_chart_only_v22_ast_pending",
        }

    def close(self) -> None:
        if self._jsonl is not None:
            self._jsonl.close()
            self._jsonl = None


def audit_with_lean_server(
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    *,
    out_dir: str | Path,
    server_config: LeanServerConfig,
    max_actions: int = 64,
    resume: bool = False,
    flush_every: int = 50,
) -> dict[str, Any]:
    """Run micro-audits through the v21 LeanServerAdapter.

    This is intentionally sequential: a persistent Lean worker represents a stateful
    resource.  Horizontal scaling should use multiple workers/shards in a higher
    scheduler.
    """
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    extractor = ProofDefectExtractor()

    existing_audits: list[dict[str, Any]] = []
    existing_responses: list[dict[str, Any]] = []
    done: set[tuple[str, str]] = set()
    if resume and (out / "responses.jsonl").exists():
        existing_responses = read_jsonl(out / "responses.jsonl")
        if (out / "micro_audit.jsonl").exists():
            existing_audits = read_jsonl(out / "micro_audit.jsonl")
        for r in existing_responses:
            sid = r.get("state_id"); aid = r.get("action_id")
            if sid is not None and aid is not None:
                done.add((str(sid), str(aid)))

    audits = list(existing_audits)
    responses = list(existing_responses)
    structured_states: list[dict[str, Any]] = []
    goal_state_transitions: list[dict[str, Any]] = []

    def flush():
        write_jsonl(out / "micro_audit.jsonl", audits)
        write_jsonl(out / "responses.jsonl", responses)
        write_jsonl(out / "structured_states.jsonl", structured_states)
        write_jsonl(out / "goal_state_transitions.jsonl", goal_state_transitions)
        seen: set[str] = set(); defects: list[dict[str, Any]] = []
        for r in responses:
            sid = str(r.get("state_id"))
            if sid in seen:
                continue
            seen.add(sid)
            db = r.get("defect_before", {})
            if isinstance(db, dict):
                row = dict(db); row["state_id"] = sid; row["task_id"] = r.get("task_id") or db.get("task_id")
                defects.append(row)
        write_jsonl(out / "defects.jsonl", defects)

    t0 = time.time(); completed_new = 0
    stateful_kernel_rpc_audit = False
    stateful_kernel_rpc_tasks = 0
    stateful_kernel_rpc_actions = 0
    with LeanServerAdapter(server_config) as server:
        load_report = server.load_project()
        stateful_kernel_rpc_audit = bool(
            getattr(server_config, "stateful_kernel_rpc", True)
            and getattr(server_config, "native_exec_mode", "") == "kernel_rpc"
            and server.status.backend == "jsonl"
        )
        flush_every = max(1, int(flush_every or 50))
        for task in tasks:
            state = ProofState.from_task(task)
            defect_before = extractor.extract(state)
            actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
            base_kernel_state_id: str | None = None
            if stateful_kernel_rpc_audit:
                try:
                    init = server.register_task(task)
                    init_state = init.get("state") if isinstance(init, dict) else None
                    if isinstance(init_state, dict):
                        sid = str(init_state.get("state_id") or "")
                        base_kernel_state_id = sid or None
                    if base_kernel_state_id:
                        stateful_kernel_rpc_tasks += 1
                        k0 = init.get("kernel_state") if isinstance(init, dict) else None
                        if isinstance(k0, dict):
                            try:
                                structured_states.append(extract_structured_state_from_kernel_json(
                                    k0,
                                    task=task,
                                    state=state,
                                    backend="kernel_json_v28",
                                    metadata={
                                        "source": "stateful_kernel_rpc_initial_state",
                                        "lean_server_session_id": server.session_id,
                                        "server_backend": server.status.backend,
                                        "project_fingerprint": server.status.project_fingerprint,
                                    },
                                ).to_dict())
                            except Exception as e:
                                structured_states.append({"state_id": state.state_id, "task_id": task.task_id, "source": "stateful_kernel_rpc_initial_state_parse_error", "error": str(e)})
                except Exception as e:
                    base_kernel_state_id = None
                    server.status.last_error = str(e)
            for action in actions[:max_actions]:
                if (state.state_id, action.action_id) in done:
                    continue
                if base_kernel_state_id:
                    try:
                        branch = server.branch_state(base_kernel_state_id)
                        branch_state_id = str(branch.get("state_id") or branch.get("new_state_id") or "") if isinstance(branch, dict) else ""
                        if not branch_state_id:
                            raise RuntimeError(f"branch_state returned no state_id: {branch}")
                        rec = server.apply_tactic_to_state_id(task, action, branch_state_id, create_state=False)
                        rec.audit_flags = dict(rec.audit_flags or {})
                        rec.audit_flags.update({
                            "stateful_kernel_rpc_audit": True,
                            "root_kernel_state_id": base_kernel_state_id,
                            "branch_kernel_state_id": branch_state_id,
                            "logical_state_id": state.state_id,
                        })
                        stateful_kernel_rpc_actions += 1
                    except Exception as e:
                        if not server_config.fallback_to_file:
                            raise
                        server.status.last_error = str(e)
                        rec = server.apply_tactic(task, action, state)
                else:
                    rec = server.apply_tactic(task, action, state)
                after_state = rec.after_state or state
                defect_after = extractor.extract(after_state, rec)
                resp, resp_flat, resp_keys = extractor.response(defect_before, defect_after)
                rec.defect_before = defect_before.to_dict(); rec.defect_after = defect_after.to_dict(); rec.response = resp
                rec.carrier_delta = {k: defect_before.carrier.get(k, 0.0) - defect_after.carrier.get(k, 0.0) for k in sorted(set(defect_before.carrier) | set(defect_after.carrier))}
                rr = {
                    "state_id": state.state_id,
                    "task_id": task.task_id,
                    "action_id": action.action_id,
                    "target": task.statement,
                    "action": action.to_dict(),
                    "response": resp,
                    "response_flat": resp_flat,
                    "response_keys": resp_keys,
                    "defect_before": defect_before.to_dict(),
                    "defect_after": defect_after.to_dict(),
                    "audit_status": rec.status,
                    "carrier_delta": rec.carrier_delta,
                    "audit_flags": dict(rec.audit_flags or {}),
                }
                ad = rec.to_dict(); ad["action"] = action.to_dict(); ad["task_id"] = task.task_id; ad["target"] = task.statement
                audits.append(ad); responses.append(rr)
                try:
                    structured_states.append(server.structured_state(task, after_state, rec))
                except Exception as e:
                    structured_states.append({"state_id": after_state.state_id, "task_id": task.task_id, "source": "structured_state_parse_error", "error": str(e)})
                try:
                    from .goal_state_dynamics import goal_state_transition_from_audit
                    tr = goal_state_transition_from_audit(ad)
                    if tr is not None:
                        goal_state_transitions.append(tr)
                except Exception as e:
                    goal_state_transitions.append({"task_id": task.task_id, "state_id": state.state_id, "action_id": action.action_id, "source": "goal_state_transition_parse_error", "error": str(e)})
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
        "stateful_kernel_rpc_audit": stateful_kernel_rpc_audit,
        "stateful_kernel_rpc_tasks": stateful_kernel_rpc_tasks,
        "stateful_kernel_rpc_actions": stateful_kernel_rpc_actions,
        **response_summary,
    }
    server_summary.setdefault("files", {})["structured_states"] = str(out / "structured_states.jsonl")
    server_summary.setdefault("files", {})["goal_state_transitions"] = str(out / "goal_state_transitions.jsonl")
    (out / "server_summary.json").write_text(json.dumps(server_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(server_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return server_summary

# Backward-compatible aliases for v21 callers that use the more explicit names.
compute_project_fingerprint = project_fingerprint
run_server_micro_audit_to_files = audit_with_lean_server


# Compatibility aliases used by CLI/tests.
server_audit_to_files = audit_with_lean_server
run_server_micro_audit_to_files = audit_with_lean_server

def adapter_from_executor_args(**kwargs) -> LeanServerAdapter:
    return LeanServerAdapter(LeanServerConfig(**kwargs))

# Compatibility methods for v21 adapter consumers.
def _lean_server_health(self: LeanServerAdapter) -> dict[str, Any]:
    self.start()
    return self.status.to_dict()


def _lean_server_structured_state(self: LeanServerAdapter, task: LeanTask, state: ProofState | None = None, audit: AuditRecord | None = None) -> dict[str, Any]:
    try:
        if state is None:
            state = audit.after_state if audit is not None and audit.after_state is not None else ProofState.from_task(task)
        flags = dict(audit.audit_flags or {}) if audit is not None else {}
        kernel_state = flags.get("kernel_state") if isinstance(flags.get("kernel_state"), dict) else None
        if kernel_state is not None:
            return extract_structured_state_from_kernel_json(kernel_state, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                "lean_server_session_id": self.session_id,
                "lean_server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "source": "lean_server_adapter_compat.audit_flags.kernel_state",
            }).to_dict()
        structured_payload = flags.get("structured_state_payload") if isinstance(flags.get("structured_state_payload"), dict) else None
        if structured_payload is not None and isinstance(structured_payload.get("goals"), list):
            return structured_payload
        if self.status.backend == "jsonl" and self._jsonl is not None:
            try:
                rep = self._jsonl.request({
                    "cmd": "structured_state",
                    "task": task.to_dict(),
                    "state": state.to_dict(),
                    "state_id": state.state_id,
                    "audit": audit.to_dict() if audit is not None else None,
                    "kernel": True,
                }, timeout_s=self.config.request_timeout_s or self.config.timeout_s)
                if rep.get("ok", True):
                    k = rep.get("kernel_state")
                    if isinstance(k, dict):
                        return extract_structured_state_from_kernel_json(k, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                            "lean_server_session_id": self.session_id,
                            "lean_server_backend": self.status.backend,
                            "project_fingerprint": self.status.project_fingerprint,
                            "source": "lean_server_adapter_compat.jsonl.kernel_state",
                        }).to_dict()
                    ss = rep.get("structured_state")
                    if isinstance(ss, dict):
                        if ss.get("schema_version", "").startswith("lean-rgc-structured-state"):
                            return ss
                        if ss.get("schema_version", "").startswith("lean-rgc-kernel-state") or ss.get("goals"):
                            return extract_structured_state_from_kernel_json(ss, task=task, state=state, audit=audit, backend="kernel_json_v28", metadata={
                                "lean_server_session_id": self.session_id,
                                "lean_server_backend": self.status.backend,
                                "project_fingerprint": self.status.project_fingerprint,
                                "source": "lean_server_adapter_compat.jsonl.structured_payload",
                            }).to_dict()
            except Exception:
                pass
        return extract_structured_state(
            task=task,
            state=state,
            audit=audit,
            backend=str(self.status.backend or "server_adapter_v28"),
            metadata={
                "lean_server_session_id": self.session_id,
                "lean_server_backend": self.status.backend,
                "project_fingerprint": self.status.project_fingerprint,
                "source": "lean_server_adapter_structured_state_v28",
            },
        ).to_dict()
    except Exception as e:
        st = state or ProofState.from_task(task)
        return {"state_id": st.state_id, "task_id": st.task_id, "source": "structured_state_parse_error", "error": str(e)}




LeanServerAdapter.health = _lean_server_health  # type: ignore[attr-defined]
LeanServerAdapter.structured_state = _lean_server_structured_state  # type: ignore[attr-defined]
