from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import math
import os
import shlex
import subprocess
import tempfile
import time

from .executor import LeanExecutor, LeanExecutorConfig
from .schemas import LeanTask, TacticAction

try:
    import resource  # type: ignore
except Exception:  # pragma: no cover - Windows fallback
    resource = None  # type: ignore


SCHEMA_AUDIT_ENV_PROFILE = "lean-rgc-audit-env-profile-v64.0"


@dataclass
class ProfileCase:
    name: str
    command: list[str]
    status: str
    returncode: int | None
    wall_s: float
    child_user_cpu_s: float
    child_sys_cpu_s: float
    maxrss_kb: int
    stdout_tail: str = ""
    stderr_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _available_mem_kb() -> int | None:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        return None
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullAvailPhys // 1024)
        except Exception:
            return None
    return None


def _run_case(name: str, command: list[str], *, cwd: str | None, timeout_s: float) -> ProfileCase:
    before = resource.getrusage(resource.RUSAGE_CHILDREN) if resource is not None else None
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=cwd or None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(1.0, float(timeout_s or 60.0)),
        )
        status = "completed"
        returncode: int | None = int(proc.returncode)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        returncode = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    wall_s = time.perf_counter() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN) if resource is not None else None
    user_cpu = float(after.ru_utime - before.ru_utime) if before is not None and after is not None else 0.0
    sys_cpu = float(after.ru_stime - before.ru_stime) if before is not None and after is not None else 0.0
    maxrss = int(after.ru_maxrss) if after is not None else 0
    return ProfileCase(
        name=name,
        command=command,
        status=status,
        returncode=returncode,
        wall_s=round(float(wall_s), 6),
        child_user_cpu_s=round(user_cpu, 6),
        child_sys_cpu_s=round(sys_cpu, 6),
        maxrss_kb=maxrss,
        stdout_tail=(stdout or "")[-1200:],
        stderr_tail=(stderr or "")[-1200:],
    )


def _first_action(actions_by_task: dict[str, list[TacticAction]] | list[TacticAction], task_id: str) -> TacticAction:
    if isinstance(actions_by_task, dict):
        xs = actions_by_task.get(task_id) or []
    else:
        xs = actions_by_task
    return xs[0] if xs else TacticAction(action_id="profile_trivial", tactic="trivial", tactic_class="profile")


def _recommend(*, import_wall_s: float, peak_rss_kb: int, cpu_count: int, available_mem_kb: int | None) -> dict[str, Any]:
    timeout_s = int(max(30, math.ceil(max(0.0, import_wall_s) * 3.0)))
    peak_gb = max(0.0, float(peak_rss_kb or 0) / (1024.0 * 1024.0))
    avail_gb = float(available_mem_kb or 0) / (1024.0 * 1024.0)
    if peak_gb > 0 and avail_gb > 0:
        mem_workers = max(1, int(math.floor((avail_gb * 0.70) / peak_gb)))
    else:
        mem_workers = max(1, cpu_count)
    workers = max(1, min(max(1, cpu_count), mem_workers))
    return {
        "recommended_timeout_s": timeout_s,
        "recommended_workers": workers,
        "cpu_count": cpu_count,
        "available_mem_kb": int(available_mem_kb or 0),
        "peak_rss_kb": int(peak_rss_kb or 0),
        "peak_rss_gb": round(peak_gb, 3),
        "available_mem_gb": round(avail_gb, 3),
    }


def profile_audit_environment(
    *,
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    lean_cmd: str = "lake env lean",
    workdir: str | None = None,
    timeout_s: float = 120.0,
    out_json: str | Path | None = None,
    keep_files_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not tasks:
        raise ValueError("audit env profile requires at least one task")
    task = tasks[0]
    action = _first_action(actions_by_task, task.task_id)
    cmd_prefix = shlex.split(lean_cmd)
    keep_dir = Path(keep_files_dir) if keep_files_dir else None
    if keep_dir:
        keep_dir.mkdir(parents=True, exist_ok=True)
        td_cm = None
        td_path = keep_dir
    else:
        td_cm = tempfile.TemporaryDirectory(prefix="lean_rgc_audit_profile_")
        td_path = Path(td_cm.name)
    try:
        renderer = LeanExecutor(LeanExecutorConfig(lean_cmd=lean_cmd, timeout_s=timeout_s))
        fail_action = TacticAction(action_id="profile_fail", tactic="fail", tactic_class="profile")
        imports = "\n".join(f"import {imp}" for imp in task.imports)
        files = {
            "no_import_true": td_path / "no_import_true.lean",
            "imports_only": td_path / "imports_only.lean",
            "statement_fail": td_path / "statement_only_fail.lean",
            "exact_job": td_path / "exact_job.lean",
        }
        files["no_import_true"].write_text("example : True := by\n  trivial\n", encoding="utf-8")
        files["imports_only"].write_text((imports + "\n" if imports else "") + "#check Nat\n", encoding="utf-8")
        files["statement_fail"].write_text(renderer._render_file(task, fail_action), encoding="utf-8")
        files["exact_job"].write_text(renderer._render_file(task, action), encoding="utf-8")
        cases = [
            _run_case("lean_version", cmd_prefix + ["--version"], cwd=workdir, timeout_s=timeout_s),
            _run_case("no_import_true", cmd_prefix + [str(files["no_import_true"])], cwd=workdir, timeout_s=timeout_s),
            _run_case("imports_only", cmd_prefix + [str(files["imports_only"])], cwd=workdir, timeout_s=timeout_s),
            _run_case("statement_fail", cmd_prefix + [str(files["statement_fail"])], cwd=workdir, timeout_s=timeout_s),
            _run_case("exact_job", cmd_prefix + [str(files["exact_job"])], cwd=workdir, timeout_s=timeout_s),
        ]
        by_name = {c.name: c for c in cases}
        import_wall_s = float(by_name["imports_only"].wall_s)
        peak_rss_kb = max(int(c.maxrss_kb or 0) for c in cases)
        cpu_count = os.cpu_count() or 1
        available_mem_kb = _available_mem_kb()
        rec = _recommend(
            import_wall_s=import_wall_s,
            peak_rss_kb=peak_rss_kb,
            cpu_count=cpu_count,
            available_mem_kb=available_mem_kb,
        )
        report = {
            "schema_version": SCHEMA_AUDIT_ENV_PROFILE,
            "sample_task_id": task.task_id,
            "sample_action_id": action.action_id,
            "lean_cmd": lean_cmd,
            "workdir": workdir,
            "imports": list(task.imports or []),
            "import_wall_s": import_wall_s,
            "statement_fail_wall_s": float(by_name["statement_fail"].wall_s),
            "exact_job_wall_s": float(by_name["exact_job"].wall_s),
            "cases": [c.to_dict() for c in cases],
            **rec,
        }
        if keep_dir:
            report["profile_files_dir"] = str(keep_dir)
        if out_json:
            p = Path(out_json)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return report
    finally:
        if td_cm is not None:
            td_cm.cleanup()


__all__ = ["SCHEMA_AUDIT_ENV_PROFILE", "profile_audit_environment"]
