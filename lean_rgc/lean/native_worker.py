from __future__ import annotations

"""Native Lean-side JSONL worker helpers.

This module packages and installs the Lean source for the experimental native
kernel worker.  The worker is a Lean program that speaks the same JSONL protocol
as :mod:`lean_rgc.persistent_lean_worker` so it can sit behind
``LeanServerAdapter``.  The default Lean source is intentionally conservative:
it provides a native Lean process, project-loaded command stream, server-side
state ids, and kernel-state-shaped JSON.  The ``kernel_rpc`` execution mode
installs ``RGCKernelRPC.lean``, which keeps real Lean elaborator/metavariable
state in memory and applies tactics directly to stored ``MVarId`` objects.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import os
import shlex
import shutil

from ..schemas import stable_hash

NATIVE_WORKER_VERSION = "lean-rgc-native-worker-v30-kernel-state-v1"
KERNEL_RPC_WORKER_VERSION = "lean-rgc-native-worker-v51-kernel-rpc-v3-u05-semantics-v1"
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class NativeWorkerInstall:
    worker_path: str
    command: str
    version: str = NATIVE_WORKER_VERSION
    source: str = "lean_rgc.native_lean.RGCKernelWorker.lean"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def packaged_worker_path() -> Path:
    return _PACKAGE_ROOT / "native_lean" / "RGCKernelWorker.lean"


def packaged_kernel_rpc_worker_path() -> Path:
    return _PACKAGE_ROOT / "native_lean" / "RGCKernelRPC.lean"


def native_worker_version(exec_mode: str = "source_check") -> str:
    return KERNEL_RPC_WORKER_VERSION if exec_mode == "kernel_rpc" else NATIVE_WORKER_VERSION


def native_worker_source_path(exec_mode: str = "source_check") -> Path:
    return packaged_kernel_rpc_worker_path() if exec_mode == "kernel_rpc" else packaged_worker_path()


def install_native_worker(
    workdir: str | Path | None = None,
    *,
    force: bool = False,
    subdir: str = ".lean_rgc",
    lean_cmd: str = "lake env lean",
    exec_mode: str = "source_check",
) -> NativeWorkerInstall:
    """Copy the packaged Lean worker into ``workdir`` and return its command.

    The installed file is intentionally under ``.lean_rgc`` so it does not
    pollute project namespaces.  The command uses ``lake env lean --run`` by
    default via :func:`native_worker_command`.
    """

    root = Path(workdir or os.getcwd()).resolve()
    src = native_worker_source_path(exec_mode)
    if not src.exists():
        raise FileNotFoundError(f"packaged native Lean worker not found: {src}")
    dst_dir = root / subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / ("RGCKernelRPC.lean" if exec_mode == "kernel_rpc" else "RGCKernelWorker.lean")
    if force or not dst.exists() or dst.read_text(encoding="utf-8", errors="ignore") != src.read_text(encoding="utf-8"):
        shutil.copyfile(src, dst)
    cmd = native_worker_command(worker_path=dst, workdir=root, lean_cmd=lean_cmd, exec_mode=exec_mode)
    return NativeWorkerInstall(
        worker_path=str(dst),
        command=cmd,
        version=native_worker_version(exec_mode),
        source=f"lean_rgc.native_lean.{src.name}",
    )


def native_worker_command(
    *,
    worker_path: str | Path | None = None,
    workdir: str | Path | None = None,
    lean_cmd: str = "lake env lean",
    exec_mode: str = "source_check",
    extra_args: list[str] | None = None,
) -> str:
    """Build a JSONL native-worker command.

    ``lean_cmd`` may be ``lake env lean`` or a direct ``lean`` binary.  The
    returned command is shell-quoted and suitable for ``server_cmd``.
    """

    if worker_path is None:
        installed = install_native_worker(workdir=workdir, lean_cmd=lean_cmd, exec_mode=exec_mode)
        worker_path = installed.worker_path
    worker_path = Path(worker_path).resolve()
    parts = shlex.split(lean_cmd) + ["--run", str(worker_path), "--exec-mode", exec_mode, "--lean-cmd", lean_cmd]
    if workdir is not None:
        parts += ["--workdir", str(Path(workdir).resolve())]
    if extra_args:
        parts += list(extra_args)
    return shlex.join(parts)


def native_worker_manifest(
    workdir: str | Path | None = None,
    *,
    lean_cmd: str = "lake env lean",
    force: bool = False,
    exec_mode: str = "source_check",
) -> dict[str, Any]:
    inst = install_native_worker(workdir=workdir, force=force, lean_cmd=lean_cmd, exec_mode=exec_mode)
    p = Path(inst.worker_path)
    data = p.read_text(encoding="utf-8")
    return {
        **inst.to_dict(),
        "lean_cmd": lean_cmd,
        "exec_mode": exec_mode,
        "workdir": str(Path(workdir or os.getcwd()).resolve()),
        "sha256_16": stable_hash({"src": data}, n=16),
        "canonical_status": "native_worker_protocol_chart_not_canonical",
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the packaged native Lean worker.

    By default this installs ``RGCKernelWorker.lean`` into ``WORKDIR/.lean_rgc``
    and executes it with ``lake env lean --run`` while forwarding stdin/stdout.
    Tests and CI can use ``--print-command`` or ``--source-out`` without having
    a Lean binary installed.
    """
    import argparse
    import subprocess
    import sys

    ap = argparse.ArgumentParser(description="Run or install the packaged Lean-RGC native Lean JSONL worker.")
    ap.add_argument("--lean-cmd", default="lake env lean")
    ap.add_argument("--exec-mode", choices=["source_check", "heuristic", "kernel_rpc"], default="source_check")
    ap.add_argument("--workdir")
    ap.add_argument("--worker-path")
    ap.add_argument("--source-out")
    ap.add_argument("--manifest-out")
    ap.add_argument("--print-source", action="store_true")
    ap.add_argument("--print-command", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-source", action="store_true")  # compatibility no-op: source is installed by default
    ap.add_argument("--fallback-backend", default="file")  # accepted for CLI compatibility; native worker does not use it
    ap.add_argument("--no-fallback", action="store_true")  # accepted for CLI compatibility
    args = ap.parse_args(argv)

    src = native_worker_source_path(args.exec_mode)
    if args.print_source:
        sys.stdout.write(src.read_text(encoding="utf-8"))
        return 0
    if args.source_out:
        out = Path(args.source_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print(str(out))
        return 0
    if args.worker_path:
        worker_path = Path(args.worker_path)
        if not worker_path.exists():
            worker_path.parent.mkdir(parents=True, exist_ok=True)
            worker_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        cmd = native_worker_command(worker_path=worker_path, workdir=args.workdir, lean_cmd=args.lean_cmd, exec_mode=args.exec_mode)
        manifest = {
            "worker_path": str(worker_path),
            "command": cmd,
            "version": native_worker_version(args.exec_mode),
            "source": "explicit_worker_path",
            "canonical_status": "native_worker_protocol_chart_not_canonical",
        }
    else:
        manifest = native_worker_manifest(workdir=args.workdir, lean_cmd=args.lean_cmd, force=args.force, exec_mode=args.exec_mode)
        cmd = manifest["command"]
    if args.manifest_out:
        p = Path(args.manifest_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.print_command:
        print(cmd)
        return 0
    return subprocess.call(shlex.split(cmd), cwd=args.workdir or os.getcwd(), stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


__all__ = [
    "KERNEL_RPC_WORKER_VERSION",
    "NATIVE_WORKER_VERSION",
    "NativeWorkerInstall",
    "install_native_worker",
    "main",
    "native_worker_command",
    "native_worker_manifest",
    "native_worker_source_path",
    "native_worker_version",
    "packaged_kernel_rpc_worker_path",
    "packaged_worker_path",
]


if __name__ == "__main__":
    raise SystemExit(main())
