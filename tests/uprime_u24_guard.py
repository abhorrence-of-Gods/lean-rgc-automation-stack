from __future__ import annotations

import asyncio
import ast
import base64
import builtins
import ctypes
import hashlib
import importlib
import io
import json
import multiprocessing.process
import ntpath
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import zlib
from dataclasses import dataclass
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence

import pytest

try:  # Hosted CI imports the guard on POSIX; the registered lane is Windows.
    import nt as _nt
except ImportError:  # pragma: no cover - exercised by hosted POSIX CI
    _nt = None


DENIAL_DISPOSITION = "U24_RESOURCE_OR_SCOPE_BLOCKED"
CONTROL_ATTESTATION_SCHEMA = "u24-control-plane-attestation-v1"
CONTROL_ATTESTATION_ENV = "UPRIME_U24_CONTROL_ATTESTATION_B64"
PREINSTALLED_GUARD_ENV = "UPRIME_U24_GUARD_PREINSTALLED"
FROZEN_IDENTITY_CORE_SHA256 = "3B36935141917D866471446644EB7D92E286003E573DBFAA3477BAA38EFF0DD1"
FROZEN_RUNNER_SHA256 = "2255E825EF7E02AC8E38684ACB436C311A2FE720D06B97959112F71090526448"

# This is the only Python copy of the frozen forbidden rows.  The registered
# PowerShell runner carries the same compact JSON bytes between the matching
# U24_DENYLIST_BEGIN/U24_DENYLIST_END markers.
DENYLIST_ROWS = (
    "docs/experiments/inputs/",
    "docs/experiments/artifacts/",
    "runs/",
    "lean_rgc/native_lean/RGCKernelRPC.lean",
    "tools/uprime_official_transport_v2_smoke.py",
    "tools/run_uprime_official_transport_v2_smoke.ps1",
    "tools/run_uprime_official_transport_v2_tests.ps1",
    "tests/test_uprime_official_transport_v2_smoke.py",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/llm_local.json",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/pilot_tasks.json",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/fake_lean_smoke.py",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/smoke_tasks_local.jsonl",
    "C:/Users/yusei/.codex/quarantine/lean-rgc/uprime-deferred-2026-07-12/",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_live/",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_i1/",
    "C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live/",
)
DENYLIST_CANONICAL_BYTES = json.dumps(
    DENYLIST_ROWS, ensure_ascii=True, separators=(",", ":")
).encode("ascii")
DENYLIST_SHA256 = hashlib.sha256(DENYLIST_CANONICAL_BYTES).hexdigest().upper()

UNION_SOURCE_PATHS = (
    "lean_rgc/odlrq/contracts.py",
    "lean_rgc/odlrq/quotient_generator.py",
    "lean_rgc/odlrq/envelope.py",
    "lean_rgc/odlrq/maxent.py",
    "lean_rgc/odlrq/similarity.py",
    "lean_rgc/odlrq/selection.py",
    "lean_rgc/odlrq/certificates.py",
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/evals/uprime_u2_u4_development.py",
    "tests/test_odlrq_quotient_generator.py",
    "tests/test_odlrq_envelope.py",
    "tests/test_odlrq_maxent.py",
    "tests/test_odlrq_similarity.py",
    "tests/test_odlrq_selection.py",
    "tests/test_uprime_u2_u4_development.py",
    "tests/uprime_u24_guard.py",
    "tools/run_uprime_u2_u4_development_tests.ps1",
    "tests/tier_manifest.json",
)

EMIT_ROOT = "docs/experiments/artifacts/uprime_u2_u4_development_20260713"
CLOSEOUT_ARTIFACTS = tuple(
    f"{EMIT_ROOT}/{name}"
    for name in (
        "envelope_core.json",
        "maxent_fixture.json",
        "local_tower.json",
        "global_measure.json",
        "level_transport.json",
        "similarity_certificate.json",
        "integrated_certificate.json",
    )
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "lean_rgc.native_lean",
    "tools.uprime_official_transport_v2_smoke",
    "tests.test_uprime_official_transport_v2_smoke",
    "ctypes",
    "_winapi",
    "runpy",
    "torch",
    "cupy",
    "tensorflow",
    "jax",
    "transformers",
    "peft",
    "bitsandbytes",
    "accelerate",
    "openai",
    "vllm",
)
_STATIC_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "subprocess",
        "socket",
        "_socket",
        "multiprocessing",
        "asyncio",
        "ctypes",
        "_winapi",
        "importlib",
        "runpy",
        "torch",
        "cupy",
        "tensorflow",
        "jax",
        "transformers",
        "peft",
        "bitsandbytes",
        "accelerate",
        "openai",
        "vllm",
    }
)
_RUNNER_DENYLIST_RE = re.compile(
    r"(?ms)^# U24_DENYLIST_BEGIN\r?\n"
    r"\$DenylistCanonicalJson\s*=\s*@'\r?\n"
    r"(?P<json>.*?)\r?\n'@\r?\n"
    r"# U24_DENYLIST_END$"
)
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:/")


class U24ResourceOrScopeBlocked(RuntimeError):
    pass


class GuardMode(str, Enum):
    SEMANTIC = "SEMANTIC"
    EMIT = "EMIT"
    CLOSEOUT = "CLOSEOUT"


@dataclass(frozen=True)
class GuardPolicy:
    mode: GuardMode
    repo_root: Path

    def __post_init__(self) -> None:
        if type(self.mode) is not GuardMode:
            raise TypeError("guard mode must be a strict GuardMode")
        root = Path(self.repo_root)
        if not root.is_absolute():
            raise ValueError("guard repository root must be absolute")
        object.__setattr__(self, "repo_root", root)


def canonical_denylist_bytes() -> bytes:
    return DENYLIST_CANONICAL_BYTES


def verify_runner_denylist(candidate: bytes) -> None:
    if type(candidate) is not bytes or candidate != DENYLIST_CANONICAL_BYTES:
        raise U24ResourceOrScopeBlocked(
            f"{DENIAL_DISPOSITION}: runner denylist bytes differ"
        )


def _blocked(message: str) -> None:
    raise U24ResourceOrScopeBlocked(f"{DENIAL_DISPOSITION}: {message}")


def _canonical_path(raw: Any, repo_root: Path) -> str | None:
    if type(raw) is int:
        return None
    try:
        text = os.fspath(raw)
    except TypeError:
        return None
    if type(text) is bytes:
        text = os.fsdecode(text)
    if type(text) is not str or "\x00" in text:
        _blocked("path is not a strict filesystem string")
    text = text.replace("\\", "/")
    path = text if os.path.isabs(text) else os.path.abspath(text)
    # The registered Windows lane resolves junction/symlink aliases through
    # GetFinalPathNameByHandle.  Hosted POSIX CI uses lexical normalization to
    # avoid recursively re-entering its patched lstat implementation.
    resolved = os.path.realpath(path, strict=False) if _nt is not None else os.path.abspath(path)
    return resolved.replace("\\", "/").casefold()


def _canonical_row(row: str, repo_root: Path) -> tuple[str, bool]:
    prefix = row.endswith("/")
    raw = row.rstrip("/")
    if not _WINDOWS_ABSOLUTE_RE.match(raw.replace("\\", "/")):
        raw = os.path.join(str(repo_root), raw)
    return _canonical_path(raw, repo_root) or "", prefix


def _is_at_or_below(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _check_path(
    policy: GuardPolicy,
    raw: Any,
    *,
    read: bool = False,
    write: bool = False,
    enumerate_directory: bool = False,
) -> None:
    path = _canonical_path(raw, policy.repo_root)
    if path is None:
        return
    matched = False
    for row in DENYLIST_ROWS:
        denied, prefix = _canonical_row(row, policy.repo_root)
        if (prefix and _is_at_or_below(path, denied)) or (not prefix and path == denied):
            matched = True
            break
    if not matched:
        return

    emit_root = _canonical_path(EMIT_ROOT, policy.repo_root)
    assert emit_root is not None
    if policy.mode is GuardMode.EMIT and _is_at_or_below(path, emit_root):
        writable = {
            _canonical_path(item, policy.repo_root) for item in CLOSEOUT_ARTIFACTS
        }
        if (
            write
            and not read
            and not enumerate_directory
            and (path == emit_root or path in writable)
        ):
            return
        _blocked("EMIT may create its root and write only the seven exact artifacts")

    if policy.mode is GuardMode.CLOSEOUT:
        readable = {
            _canonical_path(item, policy.repo_root) for item in CLOSEOUT_ARTIFACTS
        }
        if path in readable and read and not write and not enumerate_directory:
            return
        _blocked("CLOSEOUT may read only the seven exact artifact files")

    _blocked(f"forbidden path access: {raw!s}")


def _check_import(name: Any) -> None:
    if type(name) is not str:
        _blocked("dynamic import name is not a strict string")
    if any(name == prefix or name.startswith(prefix + ".") for prefix in _FORBIDDEN_IMPORT_PREFIXES):
        _blocked(f"forbidden dynamic import: {name}")


class _PatchBook:
    def __init__(self) -> None:
        self._rows: list[tuple[object, str, Any]] = []

    def set(self, owner: object, name: str, value: Any) -> None:
        if not hasattr(owner, name):
            return
        self._rows.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def restore(self) -> None:
        while self._rows:
            owner, name, value = self._rows.pop()
            setattr(owner, name, value)


_ACTIVE_POLICY: GuardPolicy | None = None
_ACTIVE_PATCHES: _PatchBook | None = None
_AUDIT_HOOK_INSTALLED = False


@dataclass
class GuardHandle:
    policy: GuardPolicy
    _owns_installation: bool
    _closed: bool = False

    def close(self) -> None:
        global _ACTIVE_PATCHES, _ACTIVE_POLICY
        if self._closed:
            return
        self._closed = True
        if not self._owns_installation:
            return
        if _ACTIVE_POLICY != self.policy or _ACTIVE_PATCHES is None:
            raise RuntimeError("guard installation identity changed")
        _ACTIVE_PATCHES.restore()
        _ACTIVE_PATCHES = None
        _ACTIVE_POLICY = None

    def __enter__(self) -> "GuardHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    policy = _ACTIVE_POLICY
    if policy is None:
        return
    if event == "open" and args:
        mode = args[1] if len(args) > 1 else "r"
        if type(mode) is str:
            read = "r" in mode or "+" in mode
            write = any(flag in mode for flag in "wax+")
        else:
            flags = int(args[2] if mode is None and len(args) > 2 else mode)
            access = flags & getattr(os, "O_ACCMODE", 3)
            read = access != getattr(os, "O_WRONLY", 1)
            write = access != getattr(os, "O_RDONLY", 0)
        _check_path(policy, args[0], read=read, write=write)
    elif event in {"os.listdir", "os.scandir"} and args:
        _check_path(policy, args[0], read=True, enumerate_directory=True)
    elif (
        event.startswith("subprocess.")
        or event.startswith("socket.")
        or event.startswith("os.system")
        or event.startswith("os.spawn")
        or event.startswith("os.exec")
        or event.startswith("os.startfile")
        or event.startswith("ctypes.dlopen")
    ):
        _blocked(f"forbidden capability audit event: {event}")
    elif event in {"os.link", "os.symlink"} and len(args) >= 2:
        _check_path(policy, args[0], read=True, write=True)
        _check_path(policy, args[1], write=True)
    elif event == "import" and args:
        _check_import(args[0])


def _deny_capability(name: str) -> Callable[..., Any]:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        _blocked(f"forbidden capability: {name}")

    return denied


def _install_path_wrappers(policy: GuardPolicy, patches: _PatchBook) -> None:
    real_builtin_open = builtins.open
    real_io_open = io.open
    real_os_open = os.open

    def guarded_open(
        file: Any, mode: str = "r", *args: Any, **kwargs: Any
    ) -> Any:
        if type(mode) is not str:
            _blocked("file mode is not a strict string")
        _check_path(
            policy,
            file,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_builtin_open(file, mode, *args, **kwargs)

    def guarded_io_open(
        file: Any, mode: str = "r", *args: Any, **kwargs: Any
    ) -> Any:
        if type(mode) is not str:
            _blocked("file mode is not a strict string")
        _check_path(
            policy,
            file,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_io_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if type(flags) is not int:
            _blocked("os.open flags are not a strict integer")
        access = flags & getattr(os, "O_ACCMODE", 3)
        _check_path(
            policy,
            path,
            read=access != getattr(os, "O_WRONLY", 1),
            write=(
                access != getattr(os, "O_RDONLY", 0)
                or bool(
                    flags
                    & sum(
                        getattr(os, name, 0)
                        for name in ("O_CREAT", "O_TRUNC", "O_APPEND")
                    )
                )
            ),
        )
        return real_os_open(path, flags, *args, **kwargs)

    patches.set(builtins, "open", guarded_open)
    patches.set(io, "open", guarded_io_open)
    patches.set(os, "open", guarded_os_open)
    if _nt is not None:
        patches.set(_nt, "open", guarded_os_open)

    for owner, name in (
        (os, "stat"),
        (os, "lstat"),
        (os, "access"),
        (Path, "stat"),
        (Path, "exists"),
        (Path, "is_file"),
        (Path, "is_dir"),
        (Path, "read_text"),
        (Path, "read_bytes"),
    ):
        if not hasattr(owner, name):
            continue
        original = getattr(owner, name)

        def guarded_read(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            _check_path(policy, path, read=True)
            return __original(path, *args, **kwargs)

        patches.set(owner, name, guarded_read)

    real_path_open = Path.open

    def guarded_path_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        _check_path(
            policy,
            path,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_path_open(path, mode, *args, **kwargs)

    patches.set(Path, "open", guarded_path_open)

    for owner, name in (
        (os, "listdir"),
        (os, "scandir"),
        (os, "walk"),
        (Path, "iterdir"),
        (Path, "glob"),
        (Path, "rglob"),
    ):
        if not hasattr(owner, name):
            continue
        original = getattr(owner, name)

        def guarded_enumeration(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            _check_path(policy, path, read=True, enumerate_directory=True)
            return __original(path, *args, **kwargs)

        patches.set(owner, name, guarded_enumeration)

    for owner, name in (
        (os, "mkdir"),
        (os, "makedirs"),
        (os, "remove"),
        (os, "unlink"),
        (os, "rmdir"),
        (Path, "mkdir"),
        (Path, "unlink"),
        (Path, "rmdir"),
        (Path, "touch"),
        (Path, "write_text"),
        (Path, "write_bytes"),
    ):
        if not hasattr(owner, name):
            continue
        original = getattr(owner, name)

        def guarded_mutation(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            _check_path(policy, path, write=True)
            return __original(path, *args, **kwargs)

        patches.set(owner, name, guarded_mutation)

    for owner, name in (
        (os, "rename"),
        (os, "replace"),
        (Path, "rename"),
        (Path, "replace"),
    ):
        if not hasattr(owner, name):
            continue
        original = getattr(owner, name)

        def guarded_move(
            source: Any,
            target: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            **kwargs: Any,
        ) -> Any:
            _check_path(policy, source, write=True)
            _check_path(policy, target, write=True)
            return __original(source, target, *args, **kwargs)

        patches.set(owner, name, guarded_move)

    # Assigning wrappers on ``os`` does not replace the same builtin functions
    # exported by Windows' low-level ``nt`` module.  Importlib legitimately
    # uses these aliases, so mirror the path checks rather than disabling them.
    for name in ("stat", "lstat", "access"):
        if _nt is None or not hasattr(_nt, name):
            continue
        original = getattr(_nt, name)

        def guarded_nt_read(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            _check_path(policy, path, read=True)
            return __original(path, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_read)
    for name in ("listdir", "scandir"):
        if _nt is None or not hasattr(_nt, name):
            continue
        original = getattr(_nt, name)

        def guarded_nt_enumeration(
            path: Any = ".",
            *args: Any,
            __original: Callable[..., Any] = original,
            **kwargs: Any,
        ) -> Any:
            _check_path(policy, path, read=True, enumerate_directory=True)
            return __original(path, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_enumeration)
    for name in ("mkdir", "remove", "unlink", "rmdir"):
        if _nt is None or not hasattr(_nt, name):
            continue
        original = getattr(_nt, name)

        def guarded_nt_mutation(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            _check_path(policy, path, write=True)
            return __original(path, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_mutation)
    for name in ("rename", "replace", "link", "symlink"):
        if _nt is None or not hasattr(_nt, name):
            continue
        original = getattr(_nt, name)

        def guarded_nt_pair(
            source: Any,
            target: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            **kwargs: Any,
        ) -> Any:
            _check_path(policy, source, read=True, write=True)
            _check_path(policy, target, write=True)
            return __original(source, target, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_pair)
    if _nt is not None and hasattr(_nt, "chdir"):
        original_nt_chdir = _nt.chdir

        def guarded_nt_chdir(path: Any) -> None:
            current = _canonical_path(os.getcwd(), policy.repo_root)
            target = _canonical_path(path, policy.repo_root)
            if target != current:
                _blocked("changing the semantic child working directory is forbidden")
            original_nt_chdir(path)

        patches.set(_nt, "chdir", guarded_nt_chdir)


def _install_capability_wrappers(patches: _PatchBook) -> None:
    for name in (
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    ):
        patches.set(subprocess, name, _deny_capability(f"subprocess.{name}"))
    for name in (
        "system",
        "popen",
        "startfile",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "_exit",
    ):
        patches.set(os, name, _deny_capability(f"os.{name}"))
        if _nt is not None:
            patches.set(_nt, name, _deny_capability(f"nt.{name}"))
    for owner, name in (
        (os, "fchdir"),
        (os, "link"),
        (os, "symlink"),
        (Path, "hardlink_to"),
        (Path, "symlink_to"),
    ):
        patches.set(owner, name, _deny_capability(f"{owner!s}.{name}"))
    original_chdir = os.chdir

    def guarded_chdir(path: Any) -> None:
        current = _canonical_path(os.getcwd(), Path(os.getcwd()))
        target = _canonical_path(path, Path(os.getcwd()))
        if target != current:
            _blocked("changing the semantic child working directory is forbidden")
        original_chdir(path)

    patches.set(os, "chdir", guarded_chdir)
    patches.set(
        asyncio, "create_subprocess_exec", _deny_capability("asyncio subprocess")
    )
    patches.set(
        asyncio, "create_subprocess_shell", _deny_capability("asyncio subprocess")
    )
    patches.set(
        multiprocessing.process.BaseProcess,
        "start",
        _deny_capability("multiprocessing start"),
    )

    class DeniedSocket:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            _blocked("forbidden capability: socket")

    patches.set(socket, "socket", DeniedSocket)
    patches.set(socket, "SocketType", DeniedSocket)
    for name in ("create_connection", "socketpair", "fromfd"):
        patches.set(socket, name, _deny_capability(f"socket.{name}"))
    low_socket = sys.modules.get("_socket")
    if isinstance(low_socket, ModuleType):
        patches.set(low_socket, "socket", DeniedSocket)

    class DeniedLibraryLoader:
        def __getattr__(self, _name: str) -> Any:
            _blocked("forbidden capability: native library loader")

        def LoadLibrary(self, _name: str) -> Any:
            _blocked("forbidden capability: native library loader")

    for name in ("CDLL", "PyDLL", "WinDLL", "OleDLL", "LibraryLoader"):
        patches.set(ctypes, name, _deny_capability(f"ctypes.{name}"))
    for name in ("cdll", "pydll", "windll", "oledll", "pythonapi"):
        patches.set(ctypes, name, DeniedLibraryLoader())

    original_import = builtins.__import__
    original_import_module = importlib.import_module

    def guarded_import(
        name: str,
        globals: Mapping[str, Any] | None = None,
        locals: Mapping[str, Any] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> Any:
        importer = "" if globals is None else globals.get("__name__", "")
        if not (name == "ctypes" and type(importer) is str and importer.startswith("numpy.")):
            _check_import(name)
        return original_import(name, globals, locals, fromlist, level)

    def guarded_import_module(name: str, package: str | None = None) -> Any:
        _check_import(name)
        return original_import_module(name, package)

    patches.set(builtins, "__import__", guarded_import)
    patches.set(importlib, "import_module", guarded_import_module)


def install_guard(policy: GuardPolicy) -> GuardHandle:
    global _ACTIVE_PATCHES, _ACTIVE_POLICY, _AUDIT_HOOK_INSTALLED
    if type(policy) is not GuardPolicy:
        raise TypeError("guard policy must be strict")
    if _ACTIVE_POLICY is not None:
        if _ACTIVE_POLICY != policy:
            _blocked("a different guard policy is already active")
        return GuardHandle(policy, _owns_installation=False)

    patches = _PatchBook()
    _ACTIVE_POLICY = policy
    _ACTIVE_PATCHES = patches
    try:
        _install_path_wrappers(policy, patches)
        _install_capability_wrappers(patches)
        if not _AUDIT_HOOK_INSTALLED:
            sys.addaudithook(_audit_hook)
            _AUDIT_HOOK_INSTALLED = True
    except BaseException:
        patches.restore()
        _ACTIVE_POLICY = None
        _ACTIVE_PATCHES = None
        raise
    return GuardHandle(policy, _owns_installation=True)


def require_active_guard(policy: GuardPolicy) -> None:
    if _ACTIVE_POLICY != policy or _ACTIVE_PATCHES is None:
        _blocked("the required denial guard is not active")


def guard_is_active() -> bool:
    return _ACTIVE_POLICY is not None


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    if guard_is_active():
        _blocked("read-only Git is restricted to the control plane")
    return subprocess.run(
        ["git", "--no-replace-objects", *args],
        cwd=repo_root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _raw_parents(repo_root: Path, revision: str) -> list[str]:
    payload = _git(repo_root, "cat-file", "-p", revision).stdout.decode("utf-8")
    return [row[7:] for row in payload.splitlines() if row.startswith("parent ")]


def _changed_paths(repo_root: Path, revision: str) -> list[str]:
    return sorted(
        _git(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            revision,
        )
        .stdout.decode("utf-8")
        .splitlines()
    )


def _tree_blob(repo_root: Path, revision: str, path: str) -> str | None:
    result = _git(repo_root, "rev-parse", f"{revision}:{path}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.decode("ascii").strip()


def _worktree_blob(repo_root: Path, path: str) -> str | None:
    candidate = repo_root / path
    if not candidate.is_file():
        return None
    return _git(repo_root, "hash-object", path).stdout.decode("ascii").strip()


def _build_control_plane_attestation(
    repo_root: Path,
    *,
    a0_commit: str,
    identity_path: str,
    tracked_paths: Sequence[str],
    absent_at_a0: Sequence[str],
) -> dict[str, Any]:
    head = _git(repo_root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    shallow = (
        _git(repo_root, "rev-parse", "--is-shallow-repository")
        .stdout.decode("ascii")
        .strip()
        == "true"
    )
    status_rows = (
        _git(
            repo_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        .stdout.decode("utf-8")
        .splitlines()
    )
    status_paths = sorted(row[3:] for row in status_rows if len(row) >= 4)
    additions = (
        _git(repo_root, "log", "--diff-filter=A", "--format=%H", "--", identity_path)
        .stdout.decode("ascii")
        .splitlines()
    )
    interval = (
        _git(
            repo_root,
            "rev-list",
            "--first-parent",
            "--reverse",
            f"{a0_commit}..{head}",
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    revisions = [a0_commit, *interval]
    revision_rows = []
    for revision in revisions:
        revision_rows.append(
            {
                "commit": revision,
                "parents": _raw_parents(repo_root, revision),
                "changed_paths": _changed_paths(repo_root, revision),
                "tree_blobs": {
                    path: _tree_blob(repo_root, revision, path)
                    for path in tracked_paths
                },
            }
        )
    result = {
        "schema_version": CONTROL_ATTESTATION_SCHEMA,
        "head": head,
        "is_shallow": shallow,
        "status_paths": status_paths,
        "identity_additions": additions,
        "first_parent_after_a0": interval,
        "revisions": revision_rows,
        "worktree_blobs": {
            path: _worktree_blob(repo_root, path) for path in tracked_paths
        },
        "absent_at_a0": {
            path: _tree_blob(repo_root, a0_commit, path) is None
            for path in absent_at_a0
        },
        "a0_manifest": json.loads(
            _git(repo_root, "show", f"{a0_commit}:tests/tier_manifest.json").stdout
        ),
    }
    return result


def _strict_attestation(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("control-plane attestation must be an exact object")
    fields = {
        "schema_version",
        "head",
        "is_shallow",
        "status_paths",
        "identity_additions",
        "first_parent_after_a0",
        "revisions",
        "worktree_blobs",
        "absent_at_a0",
        "a0_manifest",
    }
    if set(value) != fields or value["schema_version"] != CONTROL_ATTESTATION_SCHEMA:
        raise ValueError("control-plane attestation schema/fields changed")
    return value


def load_control_plane_attestation(
    repo_root: Path,
    *,
    a0_commit: str,
    identity_path: str,
    tracked_paths: Sequence[str],
    absent_at_a0: Sequence[str],
) -> dict[str, Any]:
    encoded = os.environ.pop(CONTROL_ATTESTATION_ENV, None)
    if encoded is None:
        return _strict_attestation(
            _build_control_plane_attestation(
                repo_root,
                a0_commit=a0_commit,
                identity_path=identity_path,
                tracked_paths=tracked_paths,
                absent_at_a0=absent_at_a0,
            )
        )
    try:
        if not encoded.startswith("z1:") or len(encoded) >= 24000:
            raise ValueError("control-plane attestation encoding is not bounded z1")
        compressed = base64.b64decode(encoded[3:], validate=True)
        inflater = zlib.decompressobj()
        raw = inflater.decompress(compressed, 1_000_001)
        if len(raw) > 1_000_000 or not inflater.eof or inflater.unused_data:
            raise ValueError("control-plane attestation compression is malformed")
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("control-plane attestation encoding is malformed") from exc
    if json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii") != raw:
        raise ValueError("control-plane attestation is not canonical JSON")
    return _strict_attestation(value)


def encode_control_plane_attestation(value: Mapping[str, Any]) -> str:
    strict = _strict_attestation(dict(value))
    raw = json.dumps(strict, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    encoded = "z1:" + base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")
    if len(encoded) >= 24000:
        raise ValueError("compressed control-plane attestation exceeds its cap")
    return encoded


def _scan_guard_source(text: str) -> None:
    tree = ast.parse(text, filename="tests/uprime_u24_guard.py")
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            value = node.value
            for target in targets:
                if isinstance(target, ast.Name) and value is not None:
                    assignments[target.id] = value
    for name, expected in (
        ("DENYLIST_ROWS", DENYLIST_ROWS),
        ("UNION_SOURCE_PATHS", UNION_SOURCE_PATHS),
        ("_FORBIDDEN_IMPORT_PREFIXES", _FORBIDDEN_IMPORT_PREFIXES),
    ):
        if name not in assignments or ast.literal_eval(assignments[name]) != expected:
            _blocked(f"guard frozen literal changed: {name}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "compile"}:
                _blocked(f"guard source contains forbidden dynamic code: {node.func.id}")
    enforcement_nodes = {
        id(node)
        for name in ("DENYLIST_ROWS", "EMIT_ROOT")
        for node in ast.walk(assignments[name])
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and type(node.value) is str
            and id(node) not in enforcement_nodes
            and any(row in node.value for row in DENYLIST_ROWS)
        ):
            _blocked("guard source repeats a forbidden path outside DENYLIST_ROWS")


def static_scan_union_sources(repo_root: Path) -> None:
    root = Path(repo_root)
    for relative in UNION_SOURCE_PATHS:
        candidate = root / relative
        if not candidate.exists():
            continue
        if not candidate.is_file():
            _blocked(f"union source is not a regular file: {relative}")
        text = candidate.read_text(encoding="utf-8")

        if relative == "tests/uprime_u24_guard.py":
            _scan_guard_source(text)
            continue
        if relative == "tools/run_uprime_u2_u4_development_tests.ps1":
            runner_bytes = candidate.read_bytes()
            normalized_runner = runner_bytes.replace(b"\r\n", b"\n")
            if b"\r" in normalized_runner:
                _blocked("runner contains a bare carriage return")
            if hashlib.sha256(normalized_runner).hexdigest().upper() != FROZEN_RUNNER_SHA256:
                _blocked("runner bytes differ from the immutable B0 runner")
            matches = list(_RUNNER_DENYLIST_RE.finditer(text))
            if len(matches) != 1:
                _blocked("runner must contain exactly one marked denylist copy")
            verify_runner_denylist(matches[0].group("json").encode("ascii"))
            outside = text[: matches[0].start()] + text[matches[0].end() :]
            for row in DENYLIST_ROWS:
                if row in outside or row.replace("/", "\\") in outside:
                    _blocked("runner repeats a forbidden literal outside its denylist")
            for required in (
                "LimitFlags=0x8u|0x100u|0x200u|0x2000u",
                "ActiveProcessLimit=1",
                "guard.install_guard(policy)",
                "requested lane has not reached its frozen source marker",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD = \"1\"",
                "D6E6DEBCE5C150AE31BA0D04EAF6E59FD2D79FDC4C0D5272264574665C0242F4",
            ):
                if required not in text:
                    _blocked(f"runner lost a frozen B0 invariant: {required}")
            continue
        if relative == "tests/test_uprime_u2_u4_development.py":
            raw = candidate.read_bytes()
            begin = b"# U24_I0_TEST_EXTENSION_BEGIN\n"
            end = b"# U24_I0_TEST_EXTENSION_END"
            if raw.count(begin) != 1 or raw.count(end) != 1:
                _blocked("identity I0 extension markers changed")
            start = raw.index(begin) + len(begin)
            stop = raw.index(end, start)
            core = raw[:start] + raw[stop:]
            if hashlib.sha256(core).hexdigest().upper() != FROZEN_IDENTITY_CORE_SHA256:
                _blocked("identity core differs from immutable B0 bytes")
            try:
                extension_tree = ast.parse(raw[start:stop].decode("utf-8"))
            except (SyntaxError, UnicodeError) as exc:
                _blocked(f"identity I0 extension is malformed: {exc}")
            extension_names: list[str] = []
            for node in extension_tree.body:
                if (
                    not isinstance(node, ast.FunctionDef)
                    or not node.name.startswith("test_u24_i0_")
                    or node.decorator_list
                    or node.args.posonlyargs
                    or node.args.args
                    or node.args.vararg is not None
                    or node.args.kwonlyargs
                    or node.args.kwarg is not None
                    or node.args.defaults
                    or node.args.kw_defaults
                    or node.returns is not None
                ):
                    _blocked("identity I0 extension may contain only zero-argument undecorated tests")
                extension_names.append(node.name)
                if any(isinstance(child, (ast.Import, ast.ImportFrom)) for child in ast.walk(node)):
                    _blocked("identity I0 extension may not import capabilities")
            if len(extension_names) != len(set(extension_names)):
                _blocked("identity I0 extension test names must be unique")
            i0_source = root / "lean_rgc/evals/uprime_u2_u4_development.py"
            i0_reached = (
                i0_source.is_file()
                and "u24_integrated_certificate_v1"
                in i0_source.read_text(encoding="utf-8")
            )
            if i0_reached != bool(extension_names):
                _blocked("identity I0 extension presence must exactly match I0 source reachability")
            for required in (
                "test_u24_b0_anchor_contiguous_budget_and_terminal_topology",
                "test_u24_denylist_static_scan_and_exact_runner_copy",
                "runner.count(literal)",
                "STAGE_ALLOWLISTS",
                "MAX_BUILD_COMMITS = 8",
                "MAX_CORRECTIONS = 1",
            ):
                if required not in text:
                    _blocked(f"identity test lost a frozen B0 invariant: {required}")
            continue

        normalized = text.replace("\\", "/")
        for row in DENYLIST_ROWS:
            if row in normalized:
                _blocked(f"forbidden literal in union source: {relative}")

        if candidate.suffix == ".py":
            import ast

            try:
                tree = ast.parse(text, filename=relative)
            except SyntaxError as exc:
                _blocked(f"union Python source does not parse: {relative}: {exc}")
            for node in ast.walk(tree):
                names: Iterable[str]
                if isinstance(node, ast.Import):
                    names = (alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names = (() if node.module is None else (node.module,))
                else:
                    continue
                for name in names:
                    if name.split(".", 1)[0] in _STATIC_FORBIDDEN_IMPORT_ROOTS or any(
                        name == prefix or name.startswith(prefix + ".")
                        for prefix in _FORBIDDEN_IMPORT_PREFIXES
                    ):
                        _blocked(f"forbidden import in union source: {relative}: {name}")


@pytest.fixture(autouse=True)
def u24_semantic_denial_guard() -> Iterable[None]:
    root = Path(__file__).resolve().parents[1]
    policy = GuardPolicy(GuardMode.SEMANTIC, root)
    if os.environ.get(PREINSTALLED_GUARD_ENV) == "1":
        require_active_guard(policy)
        yield
        return
    with install_guard(policy):
        yield


__all__ = [
    "CLOSEOUT_ARTIFACTS",
    "CONTROL_ATTESTATION_ENV",
    "CONTROL_ATTESTATION_SCHEMA",
    "DENIAL_DISPOSITION",
    "DENYLIST_CANONICAL_BYTES",
    "DENYLIST_ROWS",
    "DENYLIST_SHA256",
    "FROZEN_IDENTITY_CORE_SHA256",
    "FROZEN_RUNNER_SHA256",
    "EMIT_ROOT",
    "GuardHandle",
    "GuardMode",
    "GuardPolicy",
    "PREINSTALLED_GUARD_ENV",
    "U24ResourceOrScopeBlocked",
    "UNION_SOURCE_PATHS",
    "canonical_denylist_bytes",
    "encode_control_plane_attestation",
    "guard_is_active",
    "install_guard",
    "load_control_plane_attestation",
    "require_active_guard",
    "static_scan_union_sources",
    "u24_semantic_denial_guard",
    "verify_runner_denylist",
]
