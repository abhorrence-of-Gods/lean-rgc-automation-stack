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
import stat
import subprocess
import sys
import zlib
from dataclasses import dataclass, field
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence

import pytest

try:  # Hosted CI imports the guard on POSIX; the registered lane is Windows.
    import nt as _nt
except ImportError:  # pragma: no cover - exercised by hosted POSIX CI
    _nt = None


DENIAL_DISPOSITION = "U24_RESOURCE_OR_SCOPE_BLOCKED"
CONTROL_ATTESTATION_SCHEMA = "u24-control-plane-attestation-v2"
CONTROL_ATTESTATION_ENV = "UPRIME_U24_CONTROL_ATTESTATION_B64"
PREINSTALLED_GUARD_ENV = "UPRIME_U24_GUARD_PREINSTALLED"
FROZEN_IDENTITY_CORE_SHA256 = "63BA64835344CA03DBBA7D50B817C5E4BE2E4159655B9CB325D2D1C5D7A2A97E"
FROZEN_RUNNER_SHA256 = "69D3F5E53FDC4ACEBC61D79AC53D4B318C35C9C2593A5B5C860205F7694F5C8E"
FROZEN_WORKFLOW_SHA256 = "7879CC590945366A356DDEAE2B38480E5434048BFBCEC7E37848D443EA528D3B"

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
    "lean_rgc.egg-info/",
)
DENYLIST_CANONICAL_BYTES = json.dumps(
    DENYLIST_ROWS, ensure_ascii=True, separators=(",", ":")
).encode("ascii")
DENYLIST_SHA256 = hashlib.sha256(DENYLIST_CANONICAL_BYTES).hexdigest().upper()

CI_SETUP_ROOT = "lean_rgc.egg-info/"
CI_SETUP_PATHS = (
    "lean_rgc.egg-info/PKG-INFO",
    "lean_rgc.egg-info/SOURCES.txt",
    "lean_rgc.egg-info/dependency_links.txt",
    "lean_rgc.egg-info/entry_points.txt",
    "lean_rgc.egg-info/requires.txt",
    "lean_rgc.egg-info/top_level.txt",
)

UNION_SOURCE_PATHS = (
    ".github/workflows/ci.yml",
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


@dataclass(frozen=True)
class _CanonicalDenylistTable:
    repo_root_key: Path
    canonical_repo_root: str
    denylist_sha256: str
    rows: tuple[tuple[str, bool], ...]
    emit_root: str
    closeout_artifacts: tuple[str, ...]
    scope_sha256: str = field(init=False)
    _installation_token: object = field(
        default_factory=object, init=False, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.repo_root_key) is not type(Path())
            or not self.repo_root_key.is_absolute()
        ):
            raise TypeError("canonical denylist root key must be an absolute strict Path")
        if type(self.canonical_repo_root) is not str or not self.canonical_repo_root:
            raise TypeError("canonical denylist root must be a nonempty string")
        if type(self.denylist_sha256) is not str or not re.fullmatch(
            r"[0-9A-F]{64}", self.denylist_sha256
        ):
            raise TypeError("canonical denylist digest must be uppercase SHA-256")
        if type(self.rows) is not tuple or len(self.rows) != len(DENYLIST_ROWS):
            raise TypeError("canonical denylist rows must be a complete tuple")
        if any(
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not str
            or not row[0]
            or type(row[1]) is not bool
            for row in self.rows
        ):
            raise TypeError("canonical denylist row shape is invalid")
        if type(self.emit_root) is not str or not self.emit_root:
            raise TypeError("canonical EMIT root must be a nonempty string")
        if (
            type(self.closeout_artifacts) is not tuple
            or len(self.closeout_artifacts) != len(CLOSEOUT_ARTIFACTS)
            or any(
                type(path) is not str or not path
                for path in self.closeout_artifacts
            )
        ):
            raise TypeError("canonical CLOSEOUT artifacts must be a complete tuple")
        scope = {
            "canonical_repo_root": self.canonical_repo_root,
            "closeout_artifacts": list(self.closeout_artifacts),
            "denylist_sha256": self.denylist_sha256,
            "emit_root": self.emit_root,
            "repo_root_key": str(self.repo_root_key),
            "rows": [[path, prefix] for path, prefix in self.rows],
            "schema_version": "u24-canonical-denylist-scope-v1",
        }
        scope_bytes = json.dumps(
            scope, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        object.__setattr__(
            self,
            "scope_sha256",
            hashlib.sha256(scope_bytes).hexdigest().upper(),
        )


def _build_canonical_denylist_table(repo_root: Path) -> _CanonicalDenylistTable:
    """Build one installation-local table before any denial patch is active."""

    canonical_bytes = json.dumps(
        DENYLIST_ROWS, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")
    if canonical_bytes != DENYLIST_CANONICAL_BYTES:
        _blocked("denylist rows no longer match the frozen canonical bytes")
    denylist_sha256 = hashlib.sha256(canonical_bytes).hexdigest().upper()
    if denylist_sha256 != DENYLIST_SHA256:
        _blocked("denylist rows no longer match the frozen digest")

    canonical_repo_root = _canonical_path(repo_root, repo_root)
    if canonical_repo_root is None:
        _blocked("repository root cannot be canonicalized")
    rows = tuple(_canonical_row(row, repo_root) for row in DENYLIST_ROWS)
    emit_root, _emit_prefix = _canonical_row(EMIT_ROOT, repo_root)
    closeout_artifacts = tuple(
        _canonical_row(item, repo_root)[0] for item in CLOSEOUT_ARTIFACTS
    )
    if (
        any(not denied for denied, _prefix in rows)
        or not emit_root
        or any(not path for path in closeout_artifacts)
    ):
        _blocked("guard paths cannot be canonicalized")

    return _CanonicalDenylistTable(
        repo_root_key=Path(repo_root),
        canonical_repo_root=canonical_repo_root,
        denylist_sha256=denylist_sha256,
        rows=rows,
        emit_root=emit_root,
        closeout_artifacts=closeout_artifacts,
    )


def _canonical_denylist_content(table: _CanonicalDenylistTable) -> tuple[Any, ...]:
    return (
        table.repo_root_key,
        table.canonical_repo_root,
        table.denylist_sha256,
        table.rows,
        table.emit_root,
        table.closeout_artifacts,
        table.scope_sha256,
    )


def _active_canonical_denylist(policy: GuardPolicy) -> _CanonicalDenylistTable:
    fingerprint = _ACTIVE_POLICY_FINGERPRINT
    active_policy = _ACTIVE_POLICY
    if (
        fingerprint is None
        or active_policy is None
        or type(active_policy) is not GuardPolicy
        or active_policy.mode is not fingerprint[0]
        or active_policy.repo_root != fingerprint[1]
    ):
        _blocked("active guard policy differs from its installation fingerprint")
    if type(policy) is not GuardPolicy or type(policy.mode) is not GuardMode:
        _blocked("path classifier policy is not strict")
    table = _ACTIVE_CANONICAL_DENYLIST
    if table is None:
        _blocked("canonical denylist table is not active")
    if (
        _ACTIVE_CANONICAL_DENYLIST_TOKEN is None
        or table._installation_token is not _ACTIVE_CANONICAL_DENYLIST_TOKEN
        or _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None
        or table.scope_sha256 != _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256
    ):
        _blocked("canonical denylist installation binding differs")
    content = _ACTIVE_CANONICAL_DENYLIST_CONTENT
    if (
        content is None
        or table.repo_root_key != content[0]
        or table.canonical_repo_root != content[1]
        or table.denylist_sha256 != content[2]
        or table.rows is not content[3]
        or table.emit_root != content[4]
        or table.closeout_artifacts is not content[5]
        or table.scope_sha256 != content[6]
    ):
        _blocked("canonical denylist content differs from its installation snapshot")
    if policy.repo_root != table.repo_root_key:
        _blocked("guard policy root differs from the active root key")
    if table.denylist_sha256 != DENYLIST_SHA256:
        _blocked("active canonical denylist digest differs")
    return table


def _materialize_path_operand(raw: Any) -> str | bytes | int:
    if type(raw) is int:
        return raw
    try:
        value = os.fspath(raw)
    except TypeError:
        _blocked("path operand is not a strict filesystem value")
    if type(value) not in (str, bytes):
        _blocked("path operand is not a strict filesystem string")
    return value


def _check_path(
    policy: GuardPolicy,
    raw: Any,
    *,
    read: bool = False,
    write: bool = False,
    enumerate_directory: bool = False,
) -> str | bytes | int:
    table = _active_canonical_denylist(policy)
    mode = policy.mode
    repo_root = policy.repo_root
    rows = table.rows
    emit_root = table.emit_root
    closeout_artifacts = table.closeout_artifacts
    stable = _materialize_path_operand(raw)
    path = _canonical_path(stable, repo_root)
    if (
        _active_canonical_denylist(policy) is not table
        or policy.mode is not mode
        or policy.repo_root != repo_root
        or table.rows is not rows
        or table.emit_root != emit_root
        or table.closeout_artifacts is not closeout_artifacts
    ):
        _blocked("guard authority changed during path materialization")
    if path is None:
        return stable
    matched = False
    for denied, prefix in rows:
        if (prefix and _is_at_or_below(path, denied)) or (not prefix and path == denied):
            matched = True
            break
    if not matched:
        return stable

    if mode is GuardMode.EMIT and _is_at_or_below(path, emit_root):
        if (
            write
            and not read
            and not enumerate_directory
            and (path == emit_root or path in closeout_artifacts)
        ):
            return stable
        _blocked("EMIT may create its root and write only the seven exact artifacts")

    if mode is GuardMode.CLOSEOUT:
        if (
            path in closeout_artifacts
            and read
            and not write
            and not enumerate_directory
        ):
            return stable
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
_ACTIVE_POLICY_FINGERPRINT: tuple[GuardMode, Path] | None = None
_ACTIVE_PATCHES: _PatchBook | None = None
_ACTIVE_CANONICAL_DENYLIST: _CanonicalDenylistTable | None = None
_ACTIVE_CANONICAL_DENYLIST_CONTENT: tuple[Any, ...] | None = None
_ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256: str | None = None
_ACTIVE_CANONICAL_DENYLIST_TOKEN: object | None = None
_AUDIT_HOOK_INSTALLED = False


@dataclass
class GuardHandle:
    policy: GuardPolicy
    _owns_installation: bool
    _closed: bool = False

    def close(self) -> None:
        global _ACTIVE_CANONICAL_DENYLIST, _ACTIVE_CANONICAL_DENYLIST_CONTENT
        global _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256
        global _ACTIVE_CANONICAL_DENYLIST_TOKEN, _ACTIVE_PATCHES, _ACTIVE_POLICY
        global _ACTIVE_POLICY_FINGERPRINT
        if self._closed:
            return
        if not self._owns_installation:
            self._closed = True
            return
        installation_changed = (
            _ACTIVE_POLICY != self.policy
            or _ACTIVE_PATCHES is None
            or _ACTIVE_CANONICAL_DENYLIST is None
            or _ACTIVE_CANONICAL_DENYLIST_CONTENT is None
            or _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None
            or _ACTIVE_CANONICAL_DENYLIST_TOKEN is None
            or _ACTIVE_POLICY_FINGERPRINT is None
        )
        if not installation_changed:
            try:
                installation_changed = (
                    _active_canonical_denylist(self.policy)
                    is not _ACTIVE_CANONICAL_DENYLIST
                )
            except U24ResourceOrScopeBlocked:
                installation_changed = True
        patches = _ACTIVE_PATCHES
        try:
            if patches is not None:
                patches.restore()
        finally:
            _ACTIVE_CANONICAL_DENYLIST = None
            _ACTIVE_CANONICAL_DENYLIST_CONTENT = None
            _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 = None
            _ACTIVE_CANONICAL_DENYLIST_TOKEN = None
            _ACTIVE_PATCHES = None
            _ACTIVE_POLICY = None
            _ACTIVE_POLICY_FINGERPRINT = None
            self._closed = True
        if installation_changed:
            raise RuntimeError("guard installation identity changed")

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
        stable = _check_path(
            policy,
            file,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_builtin_open(stable, mode, *args, **kwargs)

    def guarded_io_open(
        file: Any, mode: str = "r", *args: Any, **kwargs: Any
    ) -> Any:
        if type(mode) is not str:
            _blocked("file mode is not a strict string")
        stable = _check_path(
            policy,
            file,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_io_open(stable, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if type(flags) is not int:
            _blocked("os.open flags are not a strict integer")
        access = flags & getattr(os, "O_ACCMODE", 3)
        stable = _check_path(
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
        return real_os_open(stable, flags, *args, **kwargs)

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
        path_method = owner is Path

        def guarded_read(
            path: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            __path_method: bool = path_method,
            **kwargs: Any,
        ) -> Any:
            stable = _check_path(policy, path, read=True)
            operand = Path(stable) if __path_method else stable
            return __original(operand, *args, **kwargs)

        patches.set(owner, name, guarded_read)

    real_path_open = Path.open

    def guarded_path_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        stable = _check_path(
            policy,
            path,
            read="r" in mode or "+" in mode,
            write=any(flag in mode for flag in "wax+"),
        )
        return real_path_open(Path(stable), mode, *args, **kwargs)

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
        path_method = owner is Path

        def guarded_enumeration(
            path: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            __path_method: bool = path_method,
            **kwargs: Any,
        ) -> Any:
            stable = _check_path(
                policy, path, read=True, enumerate_directory=True
            )
            operand = Path(stable) if __path_method else stable
            return __original(operand, *args, **kwargs)

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
        path_method = owner is Path

        def guarded_mutation(
            path: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            __path_method: bool = path_method,
            **kwargs: Any,
        ) -> Any:
            stable = _check_path(policy, path, write=True)
            operand = Path(stable) if __path_method else stable
            return __original(operand, *args, **kwargs)

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
        path_method = owner is Path

        def guarded_move(
            source: Any,
            target: Any,
            *args: Any,
            __original: Callable[..., Any] = original,
            __path_method: bool = path_method,
            **kwargs: Any,
        ) -> Any:
            stable_source = _check_path(policy, source, write=True)
            stable_target = _check_path(policy, target, write=True)
            source_operand = Path(stable_source) if __path_method else stable_source
            return __original(source_operand, stable_target, *args, **kwargs)

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
            stable = _check_path(policy, path, read=True)
            return __original(stable, *args, **kwargs)

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
            stable = _check_path(
                policy, path, read=True, enumerate_directory=True
            )
            return __original(stable, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_enumeration)
    for name in ("mkdir", "remove", "unlink", "rmdir"):
        if _nt is None or not hasattr(_nt, name):
            continue
        original = getattr(_nt, name)

        def guarded_nt_mutation(
            path: Any, *args: Any, __original: Callable[..., Any] = original, **kwargs: Any
        ) -> Any:
            stable = _check_path(policy, path, write=True)
            return __original(stable, *args, **kwargs)

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
            stable_source = _check_path(policy, source, read=True, write=True)
            stable_target = _check_path(policy, target, write=True)
            return __original(stable_source, stable_target, *args, **kwargs)

        patches.set(_nt, name, guarded_nt_pair)
    if _nt is not None and hasattr(_nt, "chdir"):
        original_nt_chdir = _nt.chdir

        def guarded_nt_chdir(path: Any) -> None:
            stable = _check_path(policy, path)
            current = _canonical_path(os.getcwd(), policy.repo_root)
            target = _canonical_path(stable, policy.repo_root)
            if target != current:
                _blocked("changing the semantic child working directory is forbidden")
            original_nt_chdir(stable)

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
        policy = _ACTIVE_POLICY
        if policy is None:
            _blocked("changing directory requires an active guard")
        stable = _check_path(policy, path)
        current = _canonical_path(os.getcwd(), Path(os.getcwd()))
        target = _canonical_path(stable, Path(os.getcwd()))
        if target != current:
            _blocked("changing the semantic child working directory is forbidden")
        original_chdir(stable)

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
    global _ACTIVE_CANONICAL_DENYLIST, _ACTIVE_CANONICAL_DENYLIST_CONTENT
    global _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256
    global _ACTIVE_CANONICAL_DENYLIST_TOKEN, _ACTIVE_PATCHES, _ACTIVE_POLICY
    global _ACTIVE_POLICY_FINGERPRINT, _AUDIT_HOOK_INSTALLED
    if type(policy) is not GuardPolicy:
        raise TypeError("guard policy must be strict")
    if _ACTIVE_POLICY is not None:
        if _ACTIVE_POLICY != policy:
            _blocked("a different guard policy is already active")
        _active_canonical_denylist(policy)
        return GuardHandle(policy, _owns_installation=False)

    # Canonicalize the root, denylist, and the two mode-specific exception
    # sets exactly once for this installation.  This runs before policy state,
    # wrappers, or the process audit hook can observe an active guard.
    table = _build_canonical_denylist_table(policy.repo_root)
    patches = _PatchBook()
    _ACTIVE_POLICY = policy
    _ACTIVE_POLICY_FINGERPRINT = (policy.mode, policy.repo_root)
    _ACTIVE_PATCHES = patches
    _ACTIVE_CANONICAL_DENYLIST = table
    _ACTIVE_CANONICAL_DENYLIST_CONTENT = _canonical_denylist_content(table)
    _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 = table.scope_sha256
    _ACTIVE_CANONICAL_DENYLIST_TOKEN = table._installation_token
    try:
        _install_path_wrappers(policy, patches)
        _install_capability_wrappers(patches)
        if not _AUDIT_HOOK_INSTALLED:
            sys.addaudithook(_audit_hook)
            _AUDIT_HOOK_INSTALLED = True
    except BaseException:
        try:
            patches.restore()
        finally:
            _ACTIVE_CANONICAL_DENYLIST = None
            _ACTIVE_CANONICAL_DENYLIST_CONTENT = None
            _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 = None
            _ACTIVE_CANONICAL_DENYLIST_TOKEN = None
            _ACTIVE_PATCHES = None
            _ACTIVE_POLICY = None
            _ACTIVE_POLICY_FINGERPRINT = None
        raise
    return GuardHandle(policy, _owns_installation=True)


def require_active_guard(policy: GuardPolicy) -> None:
    if (
        _ACTIVE_POLICY != policy
        or _ACTIVE_POLICY_FINGERPRINT is None
        or _ACTIVE_PATCHES is None
        or _ACTIVE_CANONICAL_DENYLIST is None
        or _ACTIVE_CANONICAL_DENYLIST_CONTENT is None
        or _ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None
        or _ACTIVE_CANONICAL_DENYLIST_TOKEN is None
    ):
        _blocked("the required denial guard is not active")
    _active_canonical_denylist(policy)


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


_VALID_STATUS_XY = frozenset(
    {
        " M",
        " T",
        " D",
        "M ",
        "MM",
        "MT",
        "MD",
        "T ",
        "TM",
        "TT",
        "TD",
        "A ",
        "AM",
        "AT",
        "AD",
        "D ",
        "DD",
        "AU",
        "UD",
        "UA",
        "DU",
        "AA",
        "UU",
        "??",
    }
)


def _strict_status_path(value: Any) -> str:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        raise ValueError("control status path is not a canonical string")
    if (
        value.startswith("/")
        or ntpath.splitdrive(value)[0]
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("control status path is not canonical repository-relative")
    return value


def _is_setup_path(value: str) -> bool:
    folded = value.casefold()
    root = CI_SETUP_ROOT.casefold()
    return folded == root.rstrip("/") or folded.startswith(root)


def _strict_status_partition(
    status_paths: Sequence[str],
    ci_setup_paths: Sequence[str],
    *,
    require_json_lists: bool,
) -> tuple[list[str], list[str]]:
    allowed_types = (list,) if require_json_lists else (list, tuple)
    if type(status_paths) not in allowed_types or type(ci_setup_paths) not in allowed_types:
        raise ValueError("control status partitions must be strict sequences")
    status = [_strict_status_path(item) for item in status_paths]
    setup = [_strict_status_path(item) for item in ci_setup_paths]
    if status != sorted(status) or len(status) != len(set(status)):
        raise ValueError("status_paths must be sorted and duplicate-free")
    if setup != sorted(setup) or len(setup) != len(set(setup)):
        raise ValueError("ci_setup_paths must be sorted and duplicate-free")

    exact = list(CI_SETUP_PATHS)
    visible_setup = [item for item in status if _is_setup_path(item)]
    if visible_setup:
        if visible_setup != exact or setup != exact:
            raise ValueError("visible CI setup residue is not the exact admitted set")
    elif setup:
        raise ValueError("ci_setup_paths is not a visible status subset")
    if setup not in ([], exact) or any(item not in status for item in setup):
        raise ValueError("ci_setup_paths is not the empty or complete exact subset")
    return status, setup


def governed_status_paths(
    status_paths: Sequence[str], ci_setup_paths: Sequence[str]
) -> list[str]:
    """Return stage-governed dirt without hiding raw control-plane status."""

    status, setup = _strict_status_partition(
        status_paths, ci_setup_paths, require_json_lists=False
    )
    setup_set = frozenset(setup)
    return [item for item in status if item not in setup_set]


def _is_reparse(stat_result: os.stat_result) -> bool:
    return bool(
        getattr(stat_result, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ) or bool(getattr(stat_result, "st_reparse_tag", 0))


def _validate_setup_filesystem(repo_root: Path) -> bool:
    root = Path(repo_root)
    if not root.is_absolute():
        raise ValueError("control repository root must be absolute")
    setup_root = root / CI_SETUP_ROOT.rstrip("/")
    try:
        root_stat = os.lstat(setup_root)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ValueError("CI setup residue root cannot be inspected") from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or _is_reparse(root_stat)
    ):
        raise ValueError("CI setup residue root is not a real directory")

    expected_names = tuple(path[len(CI_SETUP_ROOT) :] for path in CI_SETUP_PATHS)
    try:
        with os.scandir(setup_root) as iterator:
            entries = sorted(list(iterator), key=lambda entry: entry.name)
    except OSError as exc:
        raise ValueError("CI setup residue root cannot be enumerated") from exc
    if tuple(entry.name for entry in entries) != expected_names:
        raise ValueError("CI setup residue direct enumeration differs from exact six")
    for entry in entries:
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise ValueError("CI setup residue child cannot be inspected") from exc
        if (
            entry.is_symlink()
            or not stat.S_ISREG(entry_stat.st_mode)
            or _is_reparse(entry_stat)
        ):
            raise ValueError("CI setup residue child is not a regular real file")
    return True


def _validate_status_payload(payload: bytes, repo_root: Path) -> tuple[list[str], list[str]]:
    if type(payload) is not bytes:
        raise ValueError("Git status payload must be strict bytes")
    if payload:
        if not payload.endswith(b"\x00"):
            raise ValueError("Git status payload is not NUL terminated")
        records = payload[:-1].split(b"\x00")
        if any(not record for record in records):
            raise ValueError("Git status payload contains an empty record")
    else:
        records = []

    rows: dict[str, str] = {}
    for record in records:
        if len(record) < 4 or record[2:3] != b" ":
            raise ValueError("Git status record is malformed")
        try:
            xy = record[:2].decode("ascii")
            path = record[3:].decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Git status record encoding is malformed") from exc
        if xy not in _VALID_STATUS_XY:
            raise ValueError("Git status XY code is invalid for --no-renames")
        path = _strict_status_path(path)
        if path in rows:
            raise ValueError("Git status contains a duplicate path")
        rows[path] = xy

    status_paths = sorted(rows)
    visible_setup = [path for path in status_paths if _is_setup_path(path)]
    exact = list(CI_SETUP_PATHS)
    if visible_setup and visible_setup != exact:
        raise ValueError("Git status contains partial or noncanonical CI setup residue")
    if visible_setup and any(rows[path] != "??" for path in visible_setup):
        raise ValueError("CI setup residue must have exact untracked status")

    setup_exists = _validate_setup_filesystem(Path(repo_root))
    if setup_exists != bool(visible_setup):
        raise ValueError("Git status and CI setup residue filesystem disagree")
    ci_setup_paths = exact if setup_exists else []
    return _strict_status_partition(
        status_paths, ci_setup_paths, require_json_lists=False
    )


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
    status_paths, ci_setup_paths = _validate_status_payload(
        _git(
            repo_root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--no-renames",
        ).stdout,
        repo_root,
    )
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
        "ci_setup_paths": ci_setup_paths,
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
        "ci_setup_paths",
        "identity_additions",
        "first_parent_after_a0",
        "revisions",
        "worktree_blobs",
        "absent_at_a0",
        "a0_manifest",
    }
    if set(value) != fields or value["schema_version"] != CONTROL_ATTESTATION_SCHEMA:
        raise ValueError("control-plane attestation schema/fields changed")
    _strict_status_partition(
        value["status_paths"], value["ci_setup_paths"], require_json_lists=True
    )
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
        ("CI_SETUP_ROOT", CI_SETUP_ROOT),
        ("CI_SETUP_PATHS", CI_SETUP_PATHS),
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
        for name in ("DENYLIST_ROWS", "CI_SETUP_ROOT", "CI_SETUP_PATHS", "EMIT_ROOT")
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
        if relative == ".github/workflows/ci.yml":
            workflow_bytes = candidate.read_bytes()
            if hashlib.sha256(workflow_bytes).hexdigest().upper() != FROZEN_WORKFLOW_SHA256:
                _blocked("workflow bytes differ from the immutable B0R workflow")
            if text.count('PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"') != 1:
                _blocked("workflow must contain the exact sole plugin-autoload disablement")
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
                "MAX_BUILD_COMMITS = 6",
                "MAX_CORRECTIONS = 1",
            ):
                if required not in text:
                    _blocked(f"identity test lost a frozen B0 invariant: {required}")
            normalized_identity = text.replace("\\", "/")
            for row in DENYLIST_ROWS:
                if row in normalized_identity:
                    _blocked("identity repeats a forbidden literal outside the guard")
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
    "CI_SETUP_PATHS",
    "CI_SETUP_ROOT",
    "CLOSEOUT_ARTIFACTS",
    "CONTROL_ATTESTATION_ENV",
    "CONTROL_ATTESTATION_SCHEMA",
    "DENIAL_DISPOSITION",
    "DENYLIST_CANONICAL_BYTES",
    "DENYLIST_ROWS",
    "DENYLIST_SHA256",
    "FROZEN_IDENTITY_CORE_SHA256",
    "FROZEN_RUNNER_SHA256",
    "FROZEN_WORKFLOW_SHA256",
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
    "governed_status_paths",
    "install_guard",
    "load_control_plane_attestation",
    "require_active_guard",
    "static_scan_union_sources",
    "u24_semantic_denial_guard",
    "verify_runner_denylist",
]
