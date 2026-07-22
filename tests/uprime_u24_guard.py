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
FROZEN_IDENTITY_CORE_SHA256 = "3A349B634DFF61930E7ED003843340D948763C76049E2B4CFDEB744F4B0F7BEE"
FROZEN_RUNNER_SHA256 = "D05A1E6A6C66E5ADAA6B50C26BF39634D22AFF9E40C6EE79727439B37306B498"
FROZEN_WORKFLOW_SHA256 = "7879CC590945366A356DDEAE2B38480E5434048BFBCEC7E37848D443EA528D3B"

PORTABILITY_AUTHORITY_COMMIT = "a1413bbeef03deb6eab8f2bd46ccc481bae6ea73"
PORTABILITY_AUTHORITY_PARENT = "f1df8dd5d92706d907091e6add463fb6c9ca7130"
PORTABILITY_AUTHORITY_TREE = "a3536963974528d3d22055bf62d5b49a2749c652"
PORTABILITY_AUTHORITY_REF = (
    "refs/codex-authority/uprime-upper-portability-p0-20260718"
)
PORTABILITY_ACCEPTED_REF = "codex/uprime-upper-portability-plan"
PORTABILITY_RESOURCE_REF = (
    "refs/codex-authority/uprime-upper-portability-resource-20260718"
)
PORTABILITY_AUTHORITY_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_upper_stack_portability_phase_bundle_amendment_2026-07-18.md"
)
PORTABILITY_AUTHORITY_DOCUMENT_BLOB = "7c0a5eea0df2224eed9594ee733184fba7771f66"
PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256 = (
    "DED424629CA1C8DAFB31254DCBFDA63B0F3A15B7E09773B39495322924E8312C"
)
PORTABILITY_MATRIX_PATH = (
    "docs/experiments/inputs/uprime_u24_upper_stack_portability_matrix.json"
)
PORTABILITY_MATRIX_BLOB = "845e5de894462ee12a3de1606b3bfe2d7e966d40"
PORTABILITY_MATRIX_RAW_SHA256 = (
    "81FE1695435BC11526B8752CF80C907D58D0F85A27F678BE0C519C0FEE1E69A8"
)
PORTABILITY_HISTORICAL_NONINPUT_COMMITS = (
    ("upper_stack_sidecar", "ee7a1c01dba376881d20962de664f4908acc7b0d"),
    ("upper_stack_sidecar_correction", "c1f1957a3372f80f71b85151a793a4fa0fb218fa"),
    ("l0_final", "8ec852aa3a82be237841f81bf41f3cf8a6ef4cd4"),
)
PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS = (
    "docs/experiments/inputs/uprime_u15_l0_matrix.json",
    (
        "docs/experiments/artifacts/"
        "uprime_odlrq_u15_l0_20260717/locality_cegar_result.json"
    ),
)
PORTABILITY_CORE_SOURCE_PATHS = (
    "lean_rgc/odlrq/finite_e2.py",
    "lean_rgc/odlrq/finite_maxent.py",
    "lean_rgc/odlrq/finite_similarity.py",
    "lean_rgc/odlrq/finite_upper_stack.py",
)
PORTABILITY_EVALUATOR_PATH = (
    "lean_rgc/evals/uprime_u24_upper_stack_portability.py"
)
PORTABILITY_H_ALLOWLIST = (
    "tests/test_uprime_u2_u4_development.py",
    "tests/uprime_u24_guard.py",
    "tools/run_uprime_u2_u4_development_tests.ps1",
    "tests/test_odlrq_similarity.py",
    "tests/test_uprime_u24_upper_stack_portability_identity.py",
    "tests/tier_manifest.json",
)
PORTABILITY_PURE_STDLIB_IMPORT_ROOTS = (
    "__future__",
    "collections",
    "dataclasses",
    "enum",
    "fractions",
    "functools",
    "hashlib",
    "itertools",
    "json",
    "math",
    "operator",
    "typing",
)
PORTABILITY_CORE_IMPORT_MODULES = {
    "lean_rgc/odlrq/finite_e2.py": (
        "lean_rgc.odlrq.adapters",
        "lean_rgc.odlrq.behavioral_partition",
        "lean_rgc.odlrq.contracts",
        "lean_rgc.odlrq.envelope",
        "lean_rgc.odlrq.quotient_generator",
        "lean_rgc.odlrq.rule_algebra",
    ),
    "lean_rgc/odlrq/finite_maxent.py": (
        "lean_rgc.odlrq.contracts",
        "lean_rgc.odlrq.finite_e2",
    ),
    "lean_rgc/odlrq/finite_similarity.py": (
        "lean_rgc.odlrq.contracts",
        "lean_rgc.odlrq.finite_e2",
        "lean_rgc.odlrq.finite_maxent",
    ),
    "lean_rgc/odlrq/finite_upper_stack.py": (
        "lean_rgc.odlrq.contracts",
        "lean_rgc.odlrq.envelope",
        "lean_rgc.odlrq.finite_e2",
        "lean_rgc.odlrq.finite_maxent",
        "lean_rgc.odlrq.finite_similarity",
    ),
}
PORTABILITY_EVALUATOR_IMPORT_MODULES = (
    "lean_rgc.lean.kernel_state_identity",
    "lean_rgc.odlrq.contracts",
    "lean_rgc.odlrq.finite_e2",
    "lean_rgc.odlrq.finite_maxent",
    "lean_rgc.odlrq.finite_similarity",
    "lean_rgc.odlrq.finite_upper_stack",
)
PORTABILITY_CORE_FAMILY_LABEL_SINKS = (
    "lean_rgc.odlrq.contracts.CanonicalPayload.from_value",
    "lean_rgc.odlrq.contracts.canonical_contract_bytes",
)
PORTABILITY_DELEGATED_MANIFEST_NODES = (
    "test_uprime_u24_upper_stack_portability_identity.py",
    "test_odlrq_finite_e2.py",
    "test_odlrq_finite_maxent.py",
    "test_odlrq_finite_similarity.py",
    "test_odlrq_finite_upper_stack.py",
    "test_uprime_u24_upper_stack_portability.py",
)

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
    "lean_rgc/odlrq/finite_e2.py",
    "lean_rgc/odlrq/finite_maxent.py",
    "lean_rgc/odlrq/finite_similarity.py",
    "lean_rgc/odlrq/finite_upper_stack.py",
    "lean_rgc/evals/uprime_u2_u4_development.py",
    "lean_rgc/evals/uprime_u24_upper_stack_portability.py",
    "tests/test_odlrq_quotient_generator.py",
    "tests/test_odlrq_envelope.py",
    "tests/test_odlrq_maxent.py",
    "tests/test_odlrq_similarity.py",
    "tests/test_odlrq_selection.py",
    "tests/test_uprime_u2_u4_development.py",
    "tests/test_uprime_u24_upper_stack_portability_identity.py",
    "tests/test_odlrq_finite_e2.py",
    "tests/test_odlrq_finite_maxent.py",
    "tests/test_odlrq_finite_similarity.py",
    "tests/test_odlrq_finite_upper_stack.py",
    "tests/test_uprime_u24_upper_stack_portability.py",
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
    portability_matrix: str
    portability_matrix_sha256: str
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
        if type(self.portability_matrix) is not str or not self.portability_matrix:
            raise TypeError("canonical portability matrix must be a nonempty string")
        if (
            type(self.portability_matrix_sha256) is not str
            or not re.fullmatch(r"[0-9A-F]{64}", self.portability_matrix_sha256)
        ):
            raise TypeError("portability matrix digest must be uppercase SHA-256")
        scope = {
            "canonical_repo_root": self.canonical_repo_root,
            "closeout_artifacts": list(self.closeout_artifacts),
            "denylist_sha256": self.denylist_sha256,
            "emit_root": self.emit_root,
            "repo_root_key": str(self.repo_root_key),
            "rows": [[path, prefix] for path, prefix in self.rows],
            "portability_matrix": self.portability_matrix,
            "portability_matrix_sha256": self.portability_matrix_sha256,
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
    portability_matrix, portability_matrix_prefix = _canonical_row(
        PORTABILITY_MATRIX_PATH, repo_root
    )
    matrix_candidate = Path(repo_root) / PORTABILITY_MATRIX_PATH
    try:
        matrix_raw = matrix_candidate.read_bytes()
    except OSError as exc:
        _blocked(f"portability matrix cannot be read: {exc}")
    matrix_sha256 = hashlib.sha256(matrix_raw).hexdigest().upper()
    if (
        any(not denied for denied, _prefix in rows)
        or not emit_root
        or any(not path for path in closeout_artifacts)
        or not portability_matrix
        or portability_matrix_prefix
        or matrix_sha256 != PORTABILITY_MATRIX_RAW_SHA256
    ):
        _blocked("guard paths cannot be canonicalized")

    return _CanonicalDenylistTable(
        repo_root_key=Path(repo_root),
        canonical_repo_root=canonical_repo_root,
        denylist_sha256=denylist_sha256,
        rows=rows,
        emit_root=emit_root,
        closeout_artifacts=closeout_artifacts,
        portability_matrix=portability_matrix,
        portability_matrix_sha256=matrix_sha256,
    )


def _canonical_denylist_content(table: _CanonicalDenylistTable) -> tuple[Any, ...]:
    return (
        table.repo_root_key,
        table.canonical_repo_root,
        table.denylist_sha256,
        table.rows,
        table.emit_root,
        table.closeout_artifacts,
        table.portability_matrix,
        table.portability_matrix_sha256,
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
        or table.portability_matrix != content[6]
        or table.portability_matrix_sha256 != content[7]
        or table.scope_sha256 != content[8]
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
    portability_matrix = table.portability_matrix
    portability_matrix_sha256 = table.portability_matrix_sha256
    stable = _materialize_path_operand(raw)
    path = _canonical_path(stable, repo_root)
    if (
        _active_canonical_denylist(policy) is not table
        or policy.mode is not mode
        or policy.repo_root != repo_root
        or table.rows is not rows
        or table.emit_root != emit_root
        or table.closeout_artifacts is not closeout_artifacts
        or table.portability_matrix != portability_matrix
        or table.portability_matrix_sha256 != portability_matrix_sha256
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

    if mode is GuardMode.SEMANTIC and path == portability_matrix:
        if (
            read
            and not write
            and not enumerate_directory
            and portability_matrix_sha256 == PORTABILITY_MATRIX_RAW_SHA256
        ):
            return stable
        _blocked("portability matrix authority is exact-file read-only")

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


def _strict_portability_json(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise ValueError("portability JSON must be strict bytes")

    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate portability JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite portability JSON constant: {value}")

    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_pairs,
        parse_constant=reject_constant,
    )


def _portability_matrix(repo_root: Path) -> dict[str, Any]:
    raw = (Path(repo_root) / PORTABILITY_MATRIX_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != PORTABILITY_MATRIX_RAW_SHA256:
        _blocked("portability matrix raw bytes differ from frozen A_PC")
    try:
        value = _strict_portability_json(raw)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _blocked(f"portability matrix is malformed: {exc}")
    if type(value) is not dict:
        _blocked("portability matrix root is not an exact object")
    return value


def validate_u24_portability_control(repo_root: Path) -> None:
    """Validate the frozen A_PC handoff without re-opening the old U24 epoch."""

    root = Path(repo_root)
    if not root.is_absolute() or guard_is_active():
        _blocked("portability control validation requires an unguarded absolute root")
    if _raw_parents(root, PORTABILITY_AUTHORITY_COMMIT) != [
        PORTABILITY_AUTHORITY_PARENT
    ]:
        _blocked("portability authority parent differs")
    authority_tree = (
        _git(root, "rev-parse", f"{PORTABILITY_AUTHORITY_COMMIT}^{{tree}}")
        .stdout.decode("ascii")
        .strip()
    )
    if authority_tree != PORTABILITY_AUTHORITY_TREE:
        _blocked("portability authority tree differs")
    authority_paths = {
        PORTABILITY_AUTHORITY_DOCUMENT_PATH,
        PORTABILITY_MATRIX_PATH,
    }
    if set(_changed_paths(root, PORTABILITY_AUTHORITY_COMMIT)) != authority_paths:
        _blocked("portability authority changed-path set differs")
    if (
        _tree_blob(
            root,
            PORTABILITY_AUTHORITY_COMMIT,
            PORTABILITY_AUTHORITY_DOCUMENT_PATH,
        )
        != PORTABILITY_AUTHORITY_DOCUMENT_BLOB
        or _tree_blob(root, PORTABILITY_AUTHORITY_COMMIT, PORTABILITY_MATRIX_PATH)
        != PORTABILITY_MATRIX_BLOB
    ):
        _blocked("portability authority blob binding differs")
    document_raw = (root / PORTABILITY_AUTHORITY_DOCUMENT_PATH).read_bytes()
    if (
        hashlib.sha256(document_raw).hexdigest().upper()
        != PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256
    ):
        _blocked("portability authority document bytes differ")

    matrix = _portability_matrix(root)
    if matrix.get("schema_version") != (
        "lean-rgc-uprime-u24-upper-stack-portability-matrix-v1"
    ):
        _blocked("portability matrix schema differs")
    semantic_base = matrix.get("semantic_base")
    if type(semantic_base) is not dict or semantic_base.get("commit") != (
        PORTABILITY_AUTHORITY_PARENT
    ):
        _blocked("portability matrix semantic parent differs")
    historical = matrix.get("historical_noninputs")
    expected_historical = dict(PORTABILITY_HISTORICAL_NONINPUT_COMMITS)
    if type(historical) is not dict or any(
        historical.get(key) != value for key, value in expected_historical.items()
    ):
        _blocked("portability historical non-input provenance differs")
    forbidden = historical.get("forbidden_scientific_inputs")
    if forbidden != list(PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS):
        _blocked("portability forbidden scientific inputs differ")

    ref_probe = _git(
        root, "show-ref", "--verify", "--quiet", PORTABILITY_AUTHORITY_REF,
        check=False,
    )
    if ref_probe.returncode == 0:
        authority_ref = (
            _git(root, "rev-parse", PORTABILITY_AUTHORITY_REF)
            .stdout.decode("ascii")
            .strip()
        )
        if authority_ref != PORTABILITY_AUTHORITY_COMMIT:
            _blocked("portability authority ref differs")

    head = _git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    if (
        _git(
            root,
            "merge-base",
            "--is-ancestor",
            PORTABILITY_AUTHORITY_COMMIT,
            head,
            check=False,
        ).returncode
        != 0
    ):
        _blocked("HEAD is outside the portability authority epoch")
    interval = (
        _git(
            root,
            "rev-list",
            "--first-parent",
            "--reverse",
            f"{PORTABILITY_AUTHORITY_COMMIT}..{head}",
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    if interval:
        handoff = interval[0]
        if _raw_parents(root, handoff) != [PORTABILITY_AUTHORITY_COMMIT]:
            _blocked("portability H_PC is not a direct child of A_PC")
        if set(_changed_paths(root, handoff)) != set(PORTABILITY_H_ALLOWLIST):
            _blocked("portability H_PC changed-path set differs")
        for path, expected in (
            (
                PORTABILITY_AUTHORITY_DOCUMENT_PATH,
                PORTABILITY_AUTHORITY_DOCUMENT_BLOB,
            ),
            (PORTABILITY_MATRIX_PATH, PORTABILITY_MATRIX_BLOB),
        ):
            if _tree_blob(root, handoff, path) != expected:
                _blocked("portability H_PC changed frozen A_PC bytes")


def _qualified_ast_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_ast_name(node.value)
        if prefix is not None:
            return f"{prefix}.{node.attr}"
        return node.attr
    return None


def _enclosing_function_name(tree: ast.AST, target: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and target in set(
            ast.walk(node)
        ):
            return node.name
    return None


def _literal_mentions_family_identity(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value == "family_id":
            return True
        if isinstance(child, ast.Attribute) and child.attr == "family_id":
            return True
        if (
            isinstance(child, ast.Subscript)
            and isinstance(child.slice, ast.Constant)
            and child.slice.value == "family_id"
        ):
            return True
    return False


_STATIC_CORE_VALUE_MISSING = object()


def _static_core_value(node: ast.AST, bindings: Mapping[str, object]) -> object:
    """Evaluate a deliberately small, side-effect-free constant-string language."""

    if isinstance(node, ast.Constant) and type(node.value) in {str, int}:
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id, _STATIC_CORE_VALUE_MISSING)
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [_static_core_value(value, bindings) for value in node.elts]
        if any(value is _STATIC_CORE_VALUE_MISSING for value in values):
            return _STATIC_CORE_VALUE_MISSING
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _static_core_value(node.operand, bindings)
        if type(value) is int:
            return value if isinstance(node.op, ast.UAdd) else -value
        return _STATIC_CORE_VALUE_MISSING
    if isinstance(node, ast.BinOp):
        left = _static_core_value(node.left, bindings)
        right = _static_core_value(node.right, bindings)
        if left is _STATIC_CORE_VALUE_MISSING or right is _STATIC_CORE_VALUE_MISSING:
            return _STATIC_CORE_VALUE_MISSING
        try:
            if isinstance(node.op, ast.Add) and (
                (type(left) is str and type(right) is str)
                or (type(left) is int and type(right) is int)
            ):
                return left + right
            if isinstance(node.op, ast.Mod) and type(left) is str:
                return left % right
        except (TypeError, ValueError, OverflowError):
            pass
        return _STATIC_CORE_VALUE_MISSING
    if isinstance(node, ast.FormattedValue):
        value = _static_core_value(node.value, bindings)
        if value is _STATIC_CORE_VALUE_MISSING:
            return value
        if node.conversion == ord("r"):
            value = repr(value)
        elif node.conversion == ord("a"):
            value = ascii(value)
        elif node.conversion in {-1, ord("s")}:
            value = str(value)
        else:
            return _STATIC_CORE_VALUE_MISSING
        if node.format_spec is None:
            return value
        spec = _static_core_value(node.format_spec, bindings)
        if type(spec) is not str:
            return _STATIC_CORE_VALUE_MISSING
        try:
            return format(value, spec)
        except (TypeError, ValueError):
            return _STATIC_CORE_VALUE_MISSING
    if isinstance(node, ast.JoinedStr):
        values = [_static_core_value(value, bindings) for value in node.values]
        if all(type(value) is str for value in values):
            return "".join(values)
        return _STATIC_CORE_VALUE_MISSING
    if isinstance(node, ast.Subscript):
        value = _static_core_value(node.value, bindings)
        if value is _STATIC_CORE_VALUE_MISSING:
            return value
        if isinstance(node.slice, ast.Slice):
            parts = []
            for part in (node.slice.lower, node.slice.upper, node.slice.step):
                if part is None:
                    parts.append(None)
                    continue
                resolved = _static_core_value(part, bindings)
                if type(resolved) is not int:
                    return _STATIC_CORE_VALUE_MISSING
                parts.append(resolved)
            key: object = slice(*parts)
        else:
            key = _static_core_value(node.slice, bindings)
            if type(key) not in {str, int}:
                return _STATIC_CORE_VALUE_MISSING
        try:
            return value[key]  # type: ignore[index]
        except (IndexError, KeyError, TypeError):
            return _STATIC_CORE_VALUE_MISSING
    if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        if len(node.generators) != 1:
            return _STATIC_CORE_VALUE_MISSING
        generator = node.generators[0]
        if generator.is_async or generator.ifs or not isinstance(generator.target, ast.Name):
            return _STATIC_CORE_VALUE_MISSING
        iterable = _static_core_value(generator.iter, bindings)
        if type(iterable) not in {tuple, list}:
            return _STATIC_CORE_VALUE_MISSING
        values: list[object] = []
        for item in iterable:
            local = {**bindings, generator.target.id: item}
            value = _static_core_value(node.elt, local)
            if value is _STATIC_CORE_VALUE_MISSING:
                return value
            values.append(value)
        if isinstance(node, ast.GeneratorExp):
            return tuple(values)
        if isinstance(node, ast.ListComp):
            return values
        try:
            return frozenset(values)
        except TypeError:
            return _STATIC_CORE_VALUE_MISSING
    if not isinstance(node, ast.Call) or node.keywords and any(
        keyword.arg is None for keyword in node.keywords
    ):
        return _STATIC_CORE_VALUE_MISSING
    name = _qualified_ast_name(node.func)
    if name == "map" and len(node.args) == 2 and not node.keywords:
        function_name = _qualified_ast_name(node.args[0])
        iterable = _static_core_value(node.args[1], bindings)
        if function_name not in {"chr", "str"} or type(iterable) not in {tuple, list}:
            return _STATIC_CORE_VALUE_MISSING
        try:
            function = chr if function_name == "chr" else str
            return tuple(function(value) for value in iterable)
        except (TypeError, ValueError, OverflowError):
            return _STATIC_CORE_VALUE_MISSING
    args = [_static_core_value(value, bindings) for value in node.args]
    kwargs = {
        keyword.arg: _static_core_value(keyword.value, bindings)
        for keyword in node.keywords
        if keyword.arg is not None
    }
    if any(value is _STATIC_CORE_VALUE_MISSING for value in (*args, *kwargs.values())):
        return _STATIC_CORE_VALUE_MISSING
    try:
        if name == "chr" and len(args) == 1 and not kwargs and type(args[0]) is int:
            return chr(args[0])
        if name == "str" and len(args) == 1 and not kwargs:
            return str(args[0])
        if name == "bytes" and len(args) == 1 and not kwargs:
            return bytes(args[0])
        if name in {"operator.add", "operator.concat"} and len(args) == 2 and not kwargs:
            if type(args[0]) is type(args[1]) and type(args[0]) in {str, int}:
                return args[0] + args[1]
        if isinstance(node.func, ast.Attribute):
            receiver = _static_core_value(node.func.value, bindings)
            if type(receiver) is str and node.func.attr in {
                "format",
                "join",
                "lower",
                "lstrip",
                "removeprefix",
                "removesuffix",
                "replace",
                "rstrip",
                "strip",
                "upper",
            }:
                return getattr(receiver, node.func.attr)(*args, **kwargs)
            if type(receiver) is bytes and node.func.attr == "decode":
                return receiver.decode(*args, **kwargs)
    except (IndexError, KeyError, TypeError, ValueError, OverflowError):
        pass
    return _STATIC_CORE_VALUE_MISSING


def _resolved_import_rows(
    tree: ast.AST, *, package: str
) -> list[tuple[ast.AST, str, tuple[ast.alias, ...]]]:
    rows: list[tuple[ast.AST, str, tuple[ast.alias, ...]]] = []
    package_parts = package.split(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                rows.append((node, alias.name, (alias,)))
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is None:
            _blocked("portability source may not import package re-exports")
        if node.level:
            if node.level > len(package_parts):
                _blocked("portability relative import escapes its package")
            base = package_parts[: len(package_parts) - node.level + 1]
            module = ".".join((*base, node.module))
        else:
            module = node.module
        rows.append((node, module, tuple(node.names)))
    return rows


def _assignment_target_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Subscript):
        return {
            child.id
            for child in ast.walk(node.value)
            if isinstance(child, ast.Name)
        }
    if isinstance(node, (ast.Tuple, ast.List)):
        return {
            name
            for child in node.elts
            for name in _assignment_target_names(child)
        }
    return set()


def _expression_uses_names(node: ast.AST, names: set[str]) -> bool:
    return any(
        (
            isinstance(child, ast.Name)
            and isinstance(child.ctx, ast.Load)
            and child.id in names
        )
        or (isinstance(child, ast.Attribute) and child.attr in names)
        for child in ast.walk(node)
    )


_FAMILY_SCOPE_NODES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
)
_FAMILY_MUTATION_METHODS = frozenset({"add", "append", "extend", "insert", "update"})
_CORE_MUTATION_METHODS = frozenset(
    {
        "__delitem__",
        "__delattr__",
        "__iadd__",
        "__iand__",
        "__ifloordiv__",
        "__ilshift__",
        "__imatmul__",
        "__imod__",
        "__imul__",
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__itruediv__",
        "__ixor__",
        "__setitem__",
        "__setattr__",
        "add",
        "append",
        "appendleft",
        "clear",
        "delattr",
        "delitem",
        "difference_update",
        "discard",
        "extend",
        "extendleft",
        "iadd",
        "iand",
        "iconcat",
        "ifloordiv",
        "ilshift",
        "imatmul",
        "imod",
        "imul",
        "insert",
        "intersection_update",
        "ior",
        "ipow",
        "irshift",
        "isub",
        "itruediv",
        "ixor",
        "move_to_end",
        "pop",
        "popleft",
        "popitem",
        "remove",
        "reverse",
        "rotate",
        "setdefault",
        "setattr",
        "setitem",
        "sort",
        "subtract",
        "symmetric_difference_update",
        "update",
    }
)
_CORE_MUTABLE_CONSTRUCTORS = frozenset(
    {
        "ChainMap",
        "Counter",
        "OrderedDict",
        "defaultdict",
        "deque",
        "dict",
        "list",
        "set",
    }
)
_CORE_IMMUTABLE_STATE_CALLS = frozenset(
    {
        "dataclasses.field",
        "enum.auto",
        "fractions.Fraction",
        "frozenset",
        "tuple",
        "typing.NewType",
        "typing.TypeVar",
    }
)
_FAMILY_BUILTIN_MUTATORS = frozenset(
    {
        "add", "append", "clear", "difference_update", "discard", "extend",
        "insert", "intersection_update", "pop", "popitem", "remove", "reverse",
        "setdefault", "sort", "symmetric_difference_update", "update",
    }
)


def _walk_lexical_scope(scope: ast.AST) -> list[ast.AST]:
    """Walk one scope without leaking taint through nested definitions."""

    rows: list[ast.AST] = []
    stack = list(reversed(list(ast.iter_child_nodes(scope))))
    while stack:
        node = stack.pop()
        rows.append(node)
        if isinstance(node, _FAMILY_SCOPE_NODES):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))
    return rows


def _fresh_literal_container_bindings(
    scope: ast.AST,
) -> dict[str, ast.List | ast.Dict | ast.Set]:
    """Find single-bound local containers whose allocation is visible here."""

    direct_bindings: dict[str, list[tuple[ast.AST, ast.AST | None]]] = {}
    for node in _walk_lexical_scope(scope):
        value, targets = _assignment_value_targets(node)
        for target in targets:
            if isinstance(target, ast.Name):
                direct_bindings.setdefault(target.id, []).append((node, value))
    return {
        name: value
        for name, bindings in direct_bindings.items()
        if len(bindings) == 1
        and isinstance(bindings[0][0], (ast.Assign, ast.AnnAssign))
        and isinstance((value := bindings[0][1]), (ast.List, ast.Dict, ast.Set))
    }


def _fresh_literal_container_receiver(
    node: ast.AST,
    bindings: Mapping[str, ast.List | ast.Dict | ast.Set],
) -> bool:
    """Prove that a mutation receiver is fresh down to its literal path."""

    path: list[str | int] = []
    while isinstance(node, ast.Subscript):
        key = node.slice
        if not (
            isinstance(key, ast.Constant)
            and type(key.value) in {str, int}
        ):
            return False
        path.append(key.value)
        node = node.value
    if not isinstance(node, ast.Name) or node.id not in bindings:
        return False

    current: ast.AST = bindings[node.id]
    for key in reversed(path):
        if isinstance(current, ast.List):
            if type(key) is not int or key < 0 or key >= len(current.elts):
                return False
            current = current.elts[key]
            continue
        if isinstance(current, ast.Dict):
            matches = [
                value
                for candidate, value in zip(current.keys, current.values, strict=True)
                if isinstance(candidate, ast.Constant)
                and type(candidate.value) is type(key)
                and candidate.value == key
            ]
            if len(matches) != 1:
                return False
            current = matches[0]
            continue
        return False
    return isinstance(current, (ast.List, ast.Dict, ast.Set))


def _has_mutable_module_state(
    node: ast.AST, bindings: Mapping[str, str]
) -> bool:
    """Recognize bounded mutable constructors in a module/class binding."""

    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.List,
                ast.Dict,
                ast.Set,
                ast.ListComp,
                ast.DictComp,
                ast.SetComp,
                ast.GeneratorExp,
            ),
        ):
            return True
        if not isinstance(child, ast.Call):
            continue
        qualified = _qualified_ast_name(child.func)
        if qualified is None:
            return True
        root, separator, tail = qualified.partition(".")
        resolved = bindings.get(root, root)
        if separator:
            resolved = f"{resolved}.{tail}"
        if (
            resolved not in _CORE_IMMUTABLE_STATE_CALLS
            or resolved.rsplit(".", 1)[-1] in _CORE_MUTABLE_CONSTRUCTORS
        ):
            return True
    return False


def _assignment_value_targets(
    node: ast.AST,
) -> tuple[ast.AST | None, tuple[ast.AST, ...]]:
    if isinstance(node, ast.Assign):
        return node.value, tuple(node.targets)
    if isinstance(node, ast.AnnAssign):
        return node.value, (node.target,)
    if isinstance(node, ast.NamedExpr):
        return node.value, (node.target,)
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return node.iter, (node.target,)
    if isinstance(node, ast.AugAssign):
        return node.value, (node.target,)
    return None, ()


def _static_core_bindings(scope: ast.AST) -> dict[str, object]:
    """Resolve single-bound local constant strings without executing source."""

    candidates: dict[str, list[ast.AST | None]] = {}
    for node in _walk_lexical_scope(scope):
        value, targets = _assignment_value_targets(node)
        for target in targets:
            if isinstance(target, ast.Name):
                candidates.setdefault(target.id, []).append(value)
    single = {
        name: values[0]
        for name, values in candidates.items()
        if len(values) == 1 and values[0] is not None
    }
    bindings: dict[str, object] = {}
    changed = True
    while changed:
        changed = False
        for name, value in single.items():
            if name in bindings:
                continue
            assert value is not None
            resolved = _static_core_value(value, bindings)
            if resolved is not _STATIC_CORE_VALUE_MISSING:
                bindings[name] = resolved
                changed = True
    return bindings


def _static_mentions_family_identity(
    node: ast.AST, bindings: Mapping[str, object]
) -> bool:
    return any(
        _static_core_value(child, bindings) == "family_id"
        for child in ast.walk(node)
    )


def _is_literal_index(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return type(node.value) in {str, int} or node.value is None
    if isinstance(node, ast.Slice):
        return all(
            value is None or (isinstance(value, ast.Constant) and type(value.value) is int)
            for value in (node.lower, node.upper, node.step)
        )
    if isinstance(node, ast.Tuple):
        return all(_is_literal_index(value) for value in node.elts)
    return False


def _expression_has_ambiguous_lookup(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Subscript) and not _is_literal_index(child.slice):
            return True
        if isinstance(child, ast.Call):
            name = _qualified_ast_name(child.func)
            suffix = None if name is None else name.rsplit(".", 1)[-1]
            if suffix in {"get", "pop", "setdefault", "__contains__"}:
                if not child.args or not _is_literal_index(child.args[0]):
                    return True
            if suffix in {"getitem", "itemgetter", "attrgetter", "__getitem__"}:
                return True
    return False


def _expression_is_family_source(
    node: ast.AST,
    tainted: set[str],
    tainted_return_functions: set[str],
) -> bool:
    return bool(
        _literal_mentions_family_identity(node)
        or _expression_has_ambiguous_lookup(node)
        or _expression_uses_names(node, tainted)
        or any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in tainted_return_functions
            for child in ast.walk(node)
        )
    )


def _literal_mutable_containers(scope: ast.AST) -> dict[str, frozenset[str]]:
    nodes = _walk_lexical_scope(scope)
    stores: dict[str, list[ast.Name]] = {}
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            stores.setdefault(node.id, []).append(node)
    result: dict[str, frozenset[str]] = {}
    for node in nodes:
        if not (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and (
                (isinstance(node, ast.Assign) and len(node.targets) == 1)
                or isinstance(node, ast.AnnAssign)
            )
        ):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        value = node.value
        if not isinstance(target, ast.Name) or len(stores.get(target.id, ())) != 1:
            continue
        if isinstance(value, ast.List):
            result[target.id] = frozenset({"append", "extend", "insert"})
        elif isinstance(value, ast.Dict):
            result[target.id] = frozenset({"update"})
        elif isinstance(value, ast.Set):
            result[target.id] = frozenset({"add", "update"})
    return result


def _is_literal_container_mutation(
    node: ast.Call, containers: Mapping[str, frozenset[str]]
) -> bool:
    return bool(
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in containers
        and node.func.attr in containers[node.func.value.id]
    )


def _family_derived_names(
    scope: ast.AST,
    *,
    seeds: set[str],
    tainted_return_functions: set[str],
) -> set[str]:
    tainted = {"family_id", *seeds}
    nodes = _walk_lexical_scope(scope)
    changed = True
    while changed:
        changed = False
        for node in nodes:
            value, targets = _assignment_value_targets(node)
            if value is None or not _expression_is_family_source(
                value, tainted, tainted_return_functions
            ):
                continue
            additions = {
                name
                for target in targets
                for name in _assignment_target_names(target)
                if name not in tainted
            }
            if additions:
                tainted.update(additions)
                changed = True
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            actuals = [*node.args, *(keyword.value for keyword in node.keywords)]
            receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
            if not any(
                _expression_is_family_source(
                    value, tainted, tainted_return_functions
                )
                for value in (*actuals, *((receiver,) if receiver is not None else ()))
            ):
                continue
            additions = {
                child.id
                for value in (*actuals, *((receiver,) if receiver is not None else ()))
                for child in ast.walk(value)
                if isinstance(child, ast.Name)
                and isinstance(child.ctx, ast.Load)
                and child.id not in tainted
            }
            if additions:
                tainted.update(additions)
                changed = True
    return tainted


def _exact_ordered_family_loop(
    tree: ast.Module,
) -> tuple[ast.For, str, str, str, ast.Subscript, ast.Subscript]:
    matches: list[tuple[ast.For, str, str, str, ast.Subscript, ast.Subscript]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.For)
            and isinstance(node.target, (ast.Tuple, ast.List))
            and len(node.target.elts) == 2
            and all(isinstance(value, ast.Name) for value in node.target.elts)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "zip"
            and len(node.iter.args) == 2
            and len(node.iter.keywords) == 1
            and node.iter.keywords[0].arg == "strict"
            and isinstance(node.iter.keywords[0].value, ast.Constant)
            and node.iter.keywords[0].value.value is True
            and all(isinstance(value, ast.Subscript) for value in node.iter.args)
        ):
            continue
        order_access, family_access = node.iter.args
        assert isinstance(order_access, ast.Subscript)
        assert isinstance(family_access, ast.Subscript)
        if not (
            isinstance(order_access.value, ast.Name)
            and isinstance(family_access.value, ast.Name)
            and order_access.value.id == family_access.value.id
            and isinstance(order_access.slice, ast.Constant)
            and order_access.slice.value == "family_order"
            and isinstance(family_access.slice, ast.Constant)
            and family_access.slice.value == "families"
        ):
            continue
        order_target, row_target = node.target.elts
        assert isinstance(order_target, ast.Name)
        assert isinstance(row_target, ast.Name)
        matches.append(
            (
                node,
                order_target.id,
                row_target.id,
                order_access.value.id,
                order_access,
                family_access,
            )
        )
    if len(matches) != 1:
        _blocked("evaluator must have one exact ordered family zip loop")
    loop = matches[0]
    if _enclosing_function_name(tree, loop[0]) is None:
        _blocked("ordered family zip loop must be function-local")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and node.id == "zip"
        ) or (isinstance(node, ast.arg) and node.arg == "zip") or (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == "zip"
        ) or (
            isinstance(node, ast.alias)
            and (node.asname or node.name.split(".", 1)[0]) == "zip"
        ):
            _blocked("evaluator shadows ordered zip")
    return loop


def _validate_family_row_fragment(
    tree: ast.Module,
) -> tuple[ast.FunctionDef, str, str]:
    loop, order_name, row_name, matrix_name, order_access, family_access = (
        _exact_ordered_family_loop(tree)
    )
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    loop_functions = [
        function for function in functions if loop in ast.walk(function)
    ]
    if len(loop_functions) != 1:
        _blocked("ordered family loop has no unique top-level function")
    loop_function = loop_functions[0]
    loop_nodes = _walk_lexical_scope(loop_function)
    if any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
        for node in loop_nodes
    ):
        _blocked("evaluator family loop may not contain a nested scope")

    matrix_assignments = [
        node
        for node in loop_nodes
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == matrix_name
        and isinstance(node.value, ast.Call)
        and _qualified_ast_name(node.value.func) == "json.loads"
        and len(node.value.args) == 1
        and not node.value.keywords
        and isinstance(node.value.args[0], ast.Call)
        and isinstance(node.value.args[0].func, ast.Attribute)
        and node.value.args[0].func.attr == "read_bytes"
        and not node.value.args[0].args
        and not node.value.args[0].keywords
    ]
    if len(matrix_assignments) != 1:
        _blocked("evaluator matrix must be one direct json.loads(read_bytes()) binding")
    matrix_store = matrix_assignments[0].targets[0]
    assert isinstance(matrix_store, ast.Name)
    matrix_stores = [
        node
        for node in loop_nodes
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, (ast.Store, ast.Del))
        and node.id == matrix_name
    ]
    if matrix_stores != [matrix_store] or any(
        isinstance(node, ast.arg) and node.arg == matrix_name for node in loop_nodes
    ):
        _blocked("runtime matrix binding is not single-assignment")

    path_bindings = [
        node.targets[0].id
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
        and node.value.value == PORTABILITY_MATRIX_PATH
    ]
    path_bindings.extend(
        node.target.id
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
        and node.value.value == PORTABILITY_MATRIX_PATH
    )
    matrix_read = matrix_assignments[0].value.args[0]
    assert isinstance(matrix_read, ast.Call)
    assert isinstance(matrix_read.func, ast.Attribute)
    if len(path_bindings) != 1 or not _is_exact_matrix_receiver(
        matrix_read.func.value, path_bindings[0]
    ):
        _blocked("runtime matrix parser is not bound to the exact authority path")

    parents = {
        child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    aliases = {row_name}
    allowed_alias_loads: set[ast.Name] = set()
    allowed_alias_stores: set[ast.Name] = {
        value
        for value in loop.target.elts
        if isinstance(value, ast.Name) and value.id == row_name
    }
    changed = True
    while changed:
        changed = False
        for node in loop_nodes:
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                continue
            value, targets = _assignment_value_targets(node)
            if not isinstance(value, ast.Name) or value.id not in aliases:
                continue
            if not targets or any(not isinstance(target, ast.Name) for target in targets):
                _blocked("family row may only have direct name aliases")
            names = {
                name for target in targets for name in _assignment_target_names(target)
            }
            additions = names - aliases
            if additions:
                aliases.update(additions)
                changed = True
            allowed_alias_loads.add(value)
            for target in targets:
                allowed_alias_stores.update(
                    child
                    for child in ast.walk(target)
                    if isinstance(child, ast.Name) and child.id in aliases
                )

    for node in loop_nodes:
        if isinstance(node, ast.Name) and node.id in aliases:
            if isinstance(node.ctx, ast.Load):
                parent = parents.get(node)
                exact_field_access = bool(
                    isinstance(parent, ast.Subscript)
                    and parent.value is node
                    and isinstance(parent.ctx, ast.Load)
                    and isinstance(parent.slice, ast.Constant)
                    and type(parent.slice.value) is str
                )
                if node not in allowed_alias_loads and not exact_field_access:
                    _blocked("family row escapes literal field access")
            elif isinstance(node.ctx, (ast.Store, ast.Del)) and (
                node not in allowed_alias_stores
            ):
                _blocked("family row alias is rebound")

    special_accesses = {order_access, family_access}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {"family_order", "families"}
            and node not in special_accesses
        ):
            _blocked("family authority arrays escape the ordered zip loop")
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "family_id"
            and not (isinstance(node.value, ast.Name) and node.value.id in aliases)
        ):
            _blocked("family identity must come from the ordered row")

    for node in loop_nodes:
        if not (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id == matrix_name
        ):
            continue
        parent = parents.get(node)
        if not (
            isinstance(parent, ast.Subscript)
            and parent.value is node
            and isinstance(parent.ctx, ast.Load)
            and isinstance(parent.slice, ast.Constant)
            and type(parent.slice.value) is str
        ):
            _blocked("runtime matrix escapes literal field access")
    return loop_function, order_name, row_name


def _reject_family_identity_dispatch(tree: ast.Module) -> None:
    loop_function, order_name, _row_name = _validate_family_row_fragment(tree)
    if any(isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) for node in ast.walk(tree)):
        _blocked("evaluator family fragment admits only synchronous functions")
    for function in (
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ):
        if function not in tree.body:
            _blocked("evaluator family fragment forbids nested functions")
        if function.decorator_list:
            _blocked("evaluator family fragment forbids function decorators")
        if function.args.vararg is not None or function.args.kwarg is not None:
            _blocked("evaluator family fragment forbids variadic local functions")

    json_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and len(node.names) == 1
        and node.names[0].name == "json"
        and node.names[0].asname is None
    ]
    all_json_imports = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Import)
            and any(
                alias.name == "json" or alias.name.startswith("json.")
                for alias in node.names
            )
        )
        or (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "json" or node.module.startswith("json."))
        )
    ]
    if len(json_imports) != 1 or all_json_imports != json_imports:
        _blocked("evaluator must have one exact top-level json import")
    parents = {
        child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            _blocked("evaluator family fragment forbids nonlocal state")
        if (
            isinstance(node, ast.Name)
            and node.id == "json"
            and isinstance(node.ctx, ast.Load)
        ):
            parent = parents.get(node)
            grandparent = parents.get(parent) if parent is not None else None
            if not (
                isinstance(parent, ast.Attribute)
                and parent.value is node
                and parent.attr == "loads"
                and isinstance(grandparent, ast.Call)
                and grandparent.func is parent
            ):
                _blocked("evaluator json authority escapes its exact parser call")
        if (
            isinstance(node, ast.Name)
            and node.id == "json"
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ) or (isinstance(node, ast.arg) and node.arg == "json") or (
            isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == "json"
        ):
            _blocked("evaluator rebinds its json parser authority")
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "loads"
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            _blocked("evaluator mutates its json parser authority")

    mapping_introspection = {
        "get", "items", "keys", "values", "copy", "pop", "setdefault",
        "getitem", "itemgetter", "attrgetter", "__getitem__", "__getattribute__",
    }
    loop_scope_nodes = set(_walk_lexical_scope(loop_function))
    loop_containers = _literal_mutable_containers(loop_function)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            _blocked("evaluator family fragment forbids comprehensions")
        if isinstance(node, (ast.Try, ast.TryStar, ast.Raise, ast.Yield, ast.YieldFrom)):
            _blocked("evaluator family fragment forbids exceptional or generator flow")
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            _blocked("evaluator family fragment forbids indirect mutation")
        if (
            isinstance(node, ast.Attribute)
            and node.attr.startswith("__")
            and node.attr.endswith("__")
        ):
            _blocked("evaluator family fragment forbids dunder access")
        if isinstance(node, ast.Attribute) and node.attr in mapping_introspection:
            _blocked("evaluator family fragment forbids mapping introspection")
        if isinstance(node, ast.Call):
            name = _qualified_ast_name(node.func)
            if name is not None and name.rsplit(".", 1)[-1] in {
                "map", "filter", "iter", "next", *mapping_introspection,
            }:
                _blocked("evaluator family fragment forbids opaque lookup calls")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in _FAMILY_BUILTIN_MUTATORS
                and not (
                    node in loop_scope_nodes
                    and _is_literal_container_mutation(node, loop_containers)
                )
            ):
                _blocked("evaluator may mutate only a literal local accumulator")
            if name is not None and name.rsplit(".", 1)[-1] in {
                "delitem", "iadd", "iconcat", "imul", "ior", "iand", "ixor",
                "isub", "setitem",
            }:
                _blocked("evaluator family fragment forbids indirect mutation calls")

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    function_by_name: dict[str, ast.FunctionDef] = {}
    for function in functions:
        if function.name in function_by_name:
            _blocked("evaluator has ambiguous local function names")
        function_by_name[function.name] = function
    function_names = set(function_by_name)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and node.id in function_names
        ) or (isinstance(node, ast.arg) and node.arg in function_names) or (
            isinstance(node, ast.alias)
            and (node.asname or node.name.split(".", 1)[0]) in function_names
        ):
            _blocked("evaluator rebinds a local function")
        value, _targets = _assignment_value_targets(node)
        if isinstance(value, ast.Name) and value.id in function_names:
            _blocked("evaluator aliases a local function")
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in function_names
        ):
            parent = parents.get(node)
            if not (
                isinstance(parent, ast.Call)
                and parent.func is node
            ):
                _blocked("evaluator local functions must be called directly")

    scopes: list[ast.AST] = [tree, *functions]
    seeds: dict[int, set[str]] = {id(scope): set() for scope in scopes}
    seeds[id(loop_function)].add(order_name)
    tainted_returns: set[str] = set()
    taints: dict[int, set[str]] = {}
    changed = True
    while changed:
        changed = False
        taints = {
            id(scope): _family_derived_names(
                scope,
                seeds=seeds[id(scope)],
                tainted_return_functions=tainted_returns,
            )
            for scope in scopes
        }
        for function in functions:
            function_taint = taints[id(function)]
            if any(
                isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom))
                and node.value is not None
                and _expression_is_family_source(
                    node.value, function_taint, tainted_returns
                )
                for node in _walk_lexical_scope(function)
            ) and function.name not in tainted_returns:
                tainted_returns.add(function.name)
                changed = True
        for scope in scopes:
            caller_taint = taints[id(scope)]
            for call in (
                node for node in _walk_lexical_scope(scope) if isinstance(node, ast.Call)
            ):
                if not isinstance(call.func, ast.Name):
                    continue
                callee = function_by_name.get(call.func.id)
                if callee is None:
                    continue
                positional = [*callee.args.posonlyargs, *callee.args.args]
                pairs = list(zip(positional, call.args, strict=False))
                keyword_parameters = {
                    argument.arg: argument
                    for argument in (*positional, *callee.args.kwonlyargs)
                }
                pairs.extend(
                    (keyword_parameters[keyword.arg], keyword.value)
                    for keyword in call.keywords
                    if keyword.arg in keyword_parameters
                )
                additions = {
                    argument.arg
                    for argument, actual in pairs
                    if _expression_is_family_source(
                        actual, caller_taint, tainted_returns
                    )
                }
                if any(
                    (
                        isinstance(actual, ast.Starred)
                        and _expression_is_family_source(
                            actual.value, caller_taint, tainted_returns
                        )
                    )
                    for actual in call.args
                ) or any(
                    keyword.arg is None
                    and _expression_is_family_source(
                        keyword.value, caller_taint, tainted_returns
                    )
                    for keyword in call.keywords
                ):
                    additions.update(keyword_parameters)
                new = additions - seeds[id(callee)]
                if new:
                    seeds[id(callee)].update(new)
                    changed = True

    for scope in scopes:
        tainted = taints[id(scope)]
        containers = _literal_mutable_containers(scope)

        def reject_source(node: ast.AST) -> None:
            if _expression_is_family_source(node, tainted, tainted_returns):
                _blocked("evaluator dispatches on family-derived identity")

        for node in _walk_lexical_scope(scope):
            if isinstance(node, (ast.If, ast.IfExp, ast.While, ast.Assert)):
                reject_source(node.test)
            elif isinstance(node, ast.Match):
                reject_source(node.subject)
            elif isinstance(node, ast.match_case) and node.guard is not None:
                reject_source(node.guard)
            elif isinstance(node, ast.comprehension):
                reject_source(node.iter)
                for condition in node.ifs:
                    reject_source(condition)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                reject_source(node.iter)
            elif isinstance(node, ast.BoolOp):
                reject_source(node)
            elif isinstance(node, (ast.Compare, ast.BinOp, ast.UnaryOp)):
                reject_source(node)
            elif isinstance(node, ast.Call):
                if not _is_literal_container_mutation(node, containers):
                    reject_source(node.func)
            elif isinstance(node, ast.Subscript):
                if not (
                    isinstance(node.slice, ast.Constant)
                    and node.slice.value == "family_id"
                ):
                    reject_source(node.slice)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    reject_source(item.context_expr)


def _reject_core_family_identity_dispatch(
    modules: Mapping[str, ast.Module],
    *,
    entrypoint: ast.Module | None = None,
) -> None:
    """Close family-value control flow across the four new pure-core modules."""

    definitions: dict[str, tuple[str, str | None, ast.FunctionDef]] = {}
    classes: dict[str, ast.ClassDef] = {}
    class_modules: dict[str, str] = {}
    imports: dict[str, dict[str, str]] = {}
    parents: dict[str, dict[ast.AST, ast.AST]] = {}

    for module, tree in modules.items():
        if any(isinstance(node, (ast.AsyncFunctionDef, ast.Lambda)) for node in ast.walk(tree)):
            _blocked(f"portable core has async or lambda flow: {module}")
        if any(
            isinstance(node, ast.ClassDef) and node not in tree.body
            for node in ast.walk(tree)
        ):
            _blocked(f"portable core has a nested class: {module}")
        if any(
            isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.Match,
                    ast.Try,
                    ast.TryStar,
                    ast.With,
                ),
            )
            for node in tree.body
        ):
            _blocked(f"portable core has top-level behavioral control: {module}")
        parents[module] = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        bindings: dict[str, str] = {}
        package = module.rsplit(".", 1)[0]
        for node, resolved, aliases in _resolved_import_rows(tree, package=package):
            for alias in aliases:
                if alias.name == "*":
                    _blocked(f"portable core has a star import: {module}")
                if isinstance(node, ast.ImportFrom):
                    bindings[alias.asname or alias.name] = f"{resolved}.{alias.name}"
                else:
                    binding = alias.asname or alias.name.split(".", 1)[0]
                    bindings[binding] = alias.name if alias.asname else binding
        imports[module] = bindings
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                name = f"{module}.{node.name}"
                if name in definitions or name in classes:
                    _blocked(f"portable core callable is duplicated: {name}")
                definitions[name] = (module, None, node)
            elif isinstance(node, ast.ClassDef):
                class_name = f"{module}.{node.name}"
                if class_name in classes or class_name in definitions:
                    _blocked(f"portable core class is duplicated: {class_name}")
                classes[class_name] = node
                class_modules[class_name] = module
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        name = f"{class_name}.{child.name}"
                        if name in definitions:
                            _blocked(f"portable core method is duplicated: {name}")
                        definitions[name] = (
                            module,
                            class_name,
                            child,
                        )

        storage_scopes: list[tuple[str, list[ast.stmt]]] = [(module, tree.body)]
        storage_scopes.extend(
            (f"{module}.{node.name}", node.body)
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        )
        for owner, body in storage_scopes:
            for statement in body:
                if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                    value = statement.value
                    targets = (
                        tuple(statement.targets)
                        if isinstance(statement, ast.Assign)
                        else (statement.target,)
                    )
                    if value is not None and _has_mutable_module_state(value, bindings):
                        _blocked(f"portable core has shared mutable state: {owner}")
                    if any(isinstance(target, (ast.Attribute, ast.Subscript)) for target in targets):
                        _blocked(f"portable core mutates module/class state: {owner}")
                elif isinstance(statement, (ast.AugAssign, ast.Delete)):
                    _blocked(f"portable core mutates module/class state: {owner}")
                elif (
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Call)
                    and (_qualified_ast_name(statement.value.func) or "")
                    .rsplit(".", 1)[-1]
                    in _CORE_MUTATION_METHODS
                ):
                    _blocked(f"portable core mutates module/class state: {owner}")

    def resolve(node: ast.AST, module: str, class_name: str | None) -> str | None:
        if isinstance(node, ast.Name):
            local = f"{module}.{node.id}"
            if local in definitions or local in classes:
                return local
            return imports[module].get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            if (
                class_name is not None
                and isinstance(node.value, ast.Name)
                and node.value.id in {"self", "cls"}
            ):
                return f"{class_name}.{node.attr}"
            prefix = resolve(node.value, module, class_name)
            return None if prefix is None else f"{prefix}.{node.attr}"
        return None

    def frozen_storage_class(node: ast.ClassDef) -> bool:
        module = class_modules[next(name for name, value in classes.items() if value is node)]
        frozen = len(node.decorator_list) == 1 and any(
            isinstance(decorator, ast.Call)
            and resolve(decorator.func, module, None) == "dataclasses.dataclass"
            and any(
                keyword.arg == "frozen"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in decorator.keywords
            )
            for decorator in node.decorator_list
        )
        forbidden = {"__init__", "__post_init__", "__setattr__"}
        return frozen and not node.bases and not node.keywords and not any(
            isinstance(child, ast.FunctionDef) and child.name in forbidden
            for child in node.body
        )

    frozen_classes = {
        name for name, node in classes.items() if frozen_storage_class(node)
    }
    for name, node in classes.items():
        if node.keywords or (node.decorator_list and name not in frozen_classes):
            _blocked(f"portable core class has opaque construction: {name}")
    label_sinks = set(PORTABILITY_CORE_FAMILY_LABEL_SINKS)
    call_targets: dict[int, str | None] = {}
    scopes: dict[str, tuple[str, str | None, ast.FunctionDef]] = dict(definitions)

    for name, (module, class_name, function) in scopes.items():
        if function.args.vararg is not None or function.args.kwarg is not None:
            _blocked(f"portable core family callable is variadic: {name}")
        if any(
            isinstance(node, _FAMILY_SCOPE_NODES)
            for node in _walk_lexical_scope(function)
        ):
            _blocked(f"portable core family callable has a nested scope: {name}")
        if any(
            (resolve(decorator, module, class_name) or "").rsplit(".", 1)[-1]
            not in {"classmethod", "staticmethod"}
            for decorator in function.decorator_list
        ):
            _blocked(f"portable core callable has an opaque decorator: {name}")
        scope_nodes = _walk_lexical_scope(function)
        fresh_containers = _fresh_literal_container_bindings(function)
        for node in scope_nodes:
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                _blocked(f"portable core callable uses nonlocal state: {name}")
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                _blocked(f"portable core callable mutates attribute state: {name}")
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)):
                if not _fresh_literal_container_receiver(node.value, fresh_containers):
                    _blocked(f"portable core callable mutates nonlocal indexed state: {name}")
            if isinstance(node, ast.AugAssign):
                if not _fresh_literal_container_receiver(node.target, fresh_containers):
                    _blocked(f"portable core callable augments nonlocal state: {name}")
            if isinstance(node, ast.Call):
                target = resolve(node.func, module, class_name)
                suffix = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else None if target is None else target.rsplit(".", 1)[-1]
                )
                if suffix in _CORE_MUTATION_METHODS:
                    if target in {"operator.delitem", "operator.setitem"}:
                        receiver = node.args[0] if node.args else node.func
                    else:
                        receiver = (
                            node.func.value
                            if isinstance(node.func, ast.Attribute)
                            else node.func
                        )
                    if not _fresh_literal_container_receiver(receiver, fresh_containers):
                        _blocked(f"portable core callable invokes a nonlocal mutator: {name}")
        for node in scope_nodes:
            if isinstance(node, ast.Call):
                call_targets[id(node)] = resolve(node.func, module, class_name)

        tree_parents = parents[module]
        for node in _walk_lexical_scope(function):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if isinstance(tree_parents.get(node), ast.Attribute):
                    continue
                target = resolve(node, module, class_name)
            elif isinstance(node, ast.Attribute):
                target = resolve(node, module, class_name)
            else:
                continue
            if target not in definitions:
                continue
            parent = tree_parents.get(node)
            if not (isinstance(parent, ast.Call) and parent.func is node):
                _blocked(f"portable core callable is used higher-order: {name}")

    seeds: dict[str, set[str]] = {
        name: {
            argument.arg
            for argument in (
                *function.args.posonlyargs,
                *function.args.args,
                *function.args.kwonlyargs,
            )
            if argument.arg == "family_id"
        }
        for name, (_module, _class, function) in scopes.items()
    }

    if entrypoint is not None:
        entry_module = "lean_rgc.evals.uprime_u24_upper_stack_portability"
        entry_imports: dict[str, str] = {}
        for node, resolved, aliases in _resolved_import_rows(
            entrypoint, package="lean_rgc.evals"
        ):
            for alias in aliases:
                if alias.name == "*":
                    _blocked("portability evaluator has a star import")
                if isinstance(node, ast.ImportFrom):
                    entry_imports[alias.asname or alias.name] = (
                        f"{resolved}.{alias.name}"
                    )
                else:
                    binding = alias.asname or alias.name.split(".", 1)[0]
                    entry_imports[binding] = alias.name if alias.asname else binding

        def resolve_entry(node: ast.AST) -> str | None:
            if isinstance(node, ast.Name):
                return entry_imports.get(node.id, f"{entry_module}.{node.id}")
            if isinstance(node, ast.Attribute):
                prefix = resolve_entry(node.value)
                return None if prefix is None else f"{prefix}.{node.attr}"
            return None

        loop_function, order_name, _row_name = _validate_family_row_fragment(
            entrypoint
        )
        entry_taint = _family_derived_names(
            loop_function,
            seeds={order_name},
            tainted_return_functions=set(),
        )
        entry_parents = {
            child: parent
            for parent in ast.walk(entrypoint)
            for child in ast.iter_child_nodes(parent)
        }
        for node in _walk_lexical_scope(loop_function):
            if isinstance(node, (ast.Name, ast.Attribute)):
                target = resolve_entry(node)
                if target in definitions:
                    parent = entry_parents.get(node)
                    if not (isinstance(parent, ast.Call) and parent.func is node):
                        _blocked("portability evaluator uses a core callable higher-order")
            if not isinstance(node, ast.Call):
                continue
            target = resolve_entry(node.func)
            callee = scopes.get(target or "")
            if callee is None:
                continue
            if any(
                isinstance(actual, ast.Starred)
                and _expression_is_family_source(actual.value, entry_taint, set())
                for actual in node.args
            ) or any(
                keyword.arg is None
                and _expression_is_family_source(keyword.value, entry_taint, set())
                for keyword in node.keywords
            ):
                _blocked("portability evaluator splats family identity into core")
            _callee_module, callee_class, callee_function = callee
            positional = [
                *callee_function.args.posonlyargs,
                *callee_function.args.args,
            ]
            if (
                callee_class is not None
                and positional
                and isinstance(node.func, ast.Attribute)
                and resolve_entry(node.func.value) == callee_class
                and any(
                    isinstance(decorator, ast.Name)
                    and decorator.id == "classmethod"
                    for decorator in callee_function.decorator_list
                )
            ):
                positional = positional[1:]
            pairs = list(zip(positional, node.args, strict=False))
            keyword_parameters = {
                argument.arg: argument
                for argument in (*positional, *callee_function.args.kwonlyargs)
            }
            pairs.extend(
                (keyword_parameters[keyword.arg], keyword.value)
                for keyword in node.keywords
                if keyword.arg in keyword_parameters
            )
            additions = {
                argument.arg
                for argument, actual in pairs
                if _expression_is_family_source(actual, entry_taint, set())
            }
            seeds[target].update(additions)

    tainted_returns: set[str] = set()
    taints: dict[str, set[str]] = {}
    static_bindings = {
        name: _static_core_bindings(function)
        for name, (_module, _class, function) in scopes.items()
    }

    def is_source(
        node: ast.AST, tainted: set[str], constants: Mapping[str, object]
    ) -> bool:
        return bool(
            _literal_mentions_family_identity(node)
            or _static_mentions_family_identity(node, constants)
            or _expression_uses_names(node, tainted)
            or any(
                isinstance(child, ast.Call)
                and call_targets.get(id(child)) in tainted_returns
                for child in ast.walk(node)
            )
        )

    changed = True
    while changed:
        changed = False
        for name, (_module, _class, function) in scopes.items():
            constants = static_bindings[name]
            tainted = {
                "family_id",
                *seeds[name],
                *(key for key, value in constants.items() if value == "family_id"),
            }
            nodes = _walk_lexical_scope(function)
            local_changed = True
            while local_changed:
                local_changed = False
                for node in nodes:
                    value, targets = _assignment_value_targets(node)
                    if value is not None and is_source(value, tainted, constants):
                        additions = {
                            target_name
                            for target in targets
                            for target_name in _assignment_target_names(target)
                            if target_name not in tainted
                        }
                        if additions:
                            tainted.update(additions)
                            local_changed = True
                    if not isinstance(node, ast.Call):
                        continue
                    actuals = [
                        *node.args,
                        *(keyword.value for keyword in node.keywords),
                    ]
                    receiver = (
                        node.func.value if isinstance(node.func, ast.Attribute) else None
                    )
                    values = (*actuals, *((receiver,) if receiver is not None else ()))
                    if not any(
                        is_source(value, tainted, constants) for value in values
                    ):
                        continue
                    additions = {
                        child.id
                        for value in values
                        for child in ast.walk(value)
                        if isinstance(child, ast.Name)
                        and isinstance(child.ctx, ast.Load)
                        and child.id not in tainted
                    }
                    if additions:
                        tainted.update(additions)
                        local_changed = True
            taints[name] = tainted

        for name, (module, class_name, function) in scopes.items():
            tainted = taints[name]
            constants = static_bindings[name]
            for call in (
                node
                for node in _walk_lexical_scope(function)
                if isinstance(node, ast.Call)
            ):
                actuals = [*call.args, *(keyword.value for keyword in call.keywords)]
                receiver = call.func.value if isinstance(call.func, ast.Attribute) else None
                values = (*actuals, *((receiver,) if receiver is not None else ()))
                if not any(
                    is_source(value, tainted, constants) for value in values
                ):
                    continue
                target = call_targets.get(id(call))
                if any(
                    isinstance(actual, ast.Starred)
                    and is_source(actual.value, tainted, constants)
                    for actual in call.args
                ) or any(
                    keyword.arg is None
                    and is_source(keyword.value, tainted, constants)
                    for keyword in call.keywords
                ):
                    _blocked(f"portable core splats family identity: {name}")
                if target in frozen_classes or target in label_sinks:
                    continue
                callee = scopes.get(target or "")
                if callee is None:
                    _blocked(f"portable core sends family identity to unknown call: {name}")
                _callee_module, callee_class, callee_function = callee
                positional = [
                    *callee_function.args.posonlyargs,
                    *callee_function.args.args,
                ]
                if (
                    callee_class is not None
                    and isinstance(call.func, ast.Attribute)
                    and (
                        (
                            isinstance(call.func.value, ast.Name)
                            and call.func.value.id in {"self", "cls"}
                        )
                        or (
                            resolve(call.func.value, module, class_name)
                            == callee_class
                            and any(
                                isinstance(decorator, ast.Name)
                                and decorator.id == "classmethod"
                                for decorator in callee_function.decorator_list
                            )
                        )
                    )
                    and positional
                ):
                    positional = positional[1:]
                pairs = list(zip(positional, call.args, strict=False))
                keyword_parameters = {
                    argument.arg: argument
                    for argument in (*positional, *callee_function.args.kwonlyargs)
                }
                pairs.extend(
                    (keyword_parameters[keyword.arg], keyword.value)
                    for keyword in call.keywords
                    if keyword.arg in keyword_parameters
                )
                additions = {
                    argument.arg
                    for argument, actual in pairs
                    if is_source(actual, tainted, constants)
                }
                new = additions - seeds[target]
                if new:
                    seeds[target].update(new)
                    changed = True
            if any(
                isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom))
                and node.value is not None
                and is_source(node.value, tainted, constants)
                for node in _walk_lexical_scope(function)
            ) and name not in tainted_returns:
                tainted_returns.add(name)
                changed = True

    for name, (_module, _class, function) in scopes.items():
        tainted = taints[name]
        constants = static_bindings[name]

        def reject(node: ast.AST) -> None:
            if is_source(node, tainted, constants):
                _blocked(f"portable core dispatches on family identity: {name}")

        for node in _walk_lexical_scope(function):
            if isinstance(node, (ast.If, ast.IfExp, ast.While, ast.Assert)):
                reject(node.test)
            elif isinstance(node, ast.Match):
                reject(node.subject)
            elif isinstance(node, ast.match_case) and node.guard is not None:
                reject(node.guard)
            elif isinstance(node, ast.comprehension):
                reject(node.iter)
                for condition in node.ifs:
                    reject(condition)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                reject(node.iter)
            elif isinstance(node, ast.BoolOp):
                reject(node)
            elif isinstance(node, (ast.Compare, ast.BinOp, ast.UnaryOp)):
                reject(node)
            elif isinstance(node, ast.Call):
                target = call_targets.get(id(node))
                if target not in set(definitions) | frozen_classes | label_sinks:
                    reject(node.func)
            elif isinstance(node, ast.Subscript) and not (
                isinstance(node.slice, ast.Constant)
                and node.slice.value == "family_id"
            ):
                reject(node.slice)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    reject(item.context_expr)
            elif isinstance(node, ast.Raise) and node.exc is not None:
                reject(node.exc)


def _is_exact_matrix_receiver(node: ast.AST, binding: str) -> bool:
    if not (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.right, ast.Name)
        and node.right.id == binding
    ):
        return False
    left = node.left
    return bool(
        isinstance(left, ast.Subscript)
        and isinstance(left.slice, ast.Constant)
        and left.slice.value == 2
        and isinstance(left.value, ast.Attribute)
        and left.value.attr == "parents"
        and isinstance(left.value.value, ast.Call)
        and isinstance(left.value.value.func, ast.Name)
        and left.value.value.func.id == "Path"
        and len(left.value.value.args) == 1
        and isinstance(left.value.value.args[0], ast.Name)
        and left.value.value.args[0].id == "__file__"
        and not left.value.value.keywords
    )


def verify_u24_portability_source_firewall(repo_root: Path) -> None:
    """Reject endpoint literals and ambient capabilities in the portable core."""

    root = Path(repo_root)
    matrix = _portability_matrix(root)
    family_order = matrix.get("family_order")
    families = matrix.get("families")
    if (
        type(family_order) is not list
        or not family_order
        or any(type(value) is not str for value in family_order)
        or len(family_order) != len(set(family_order))
        or type(families) is not list
    ):
        _blocked("portability family authority is malformed")
    forbidden_strings = {
        *family_order,
        *PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS,
        *(value for _name, value in PORTABILITY_HISTORICAL_NONINPUT_COMMITS),
    }
    frozen_structures: set[str] = set()
    for family in families:
        if type(family) is not dict:
            _blocked("portability family row is not an exact object")
        for key in (
            "signed_coordinate_matrix_target_row_source_column",
            "expected_positive_envelope",
            "expected_return_memory",
            "expected_maxent_probabilities",
            "expected_hard_bound",
        ):
            if key not in family:
                _blocked(f"portability family omitted frozen structure: {key}")
            frozen_structures.add(
                json.dumps(
                    family[key],
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            )

    pure_stdlib_roots = set(PORTABILITY_PURE_STDLIB_IMPORT_ROOTS)
    forbidden_identifiers = {
        "__builtins__", "__dict__", "__globals__", "__import__", "__loader__",
        "__spec__", "__subclasses__", "breakpoint", "compile", "eval",
        "delattr", "exec", "getattr", "globals", "hasattr", "input", "locals",
        "modules", "open", "print", "setattr", "vars",
    }
    forbidden_capability_calls = {
        "absolute", "chmod", "connect", "exists", "expanduser", "fork",
        "get_code", "get_data", "get_source", "glob", "group", "hardlink_to",
        "home", "is_block_device",
        "is_char_device", "is_dir", "is_fifo", "is_file", "is_mount",
        "is_socket", "is_symlink", "iterdir", "lchmod", "listdir", "lstat",
        "mkdir", "open", "owner", "popen", "read", "read_bytes",
        "read_text", "readlink", "recv", "remove", "rename", "replace",
        "request", "resolve", "rglob", "rmdir", "samefile", "scandir",
        "send", "spawn", "stat", "symlink_to", "system", "touch", "unlink",
        "urlopen", "walk", "write", "write_bytes", "write_text",
        "writelines",
    }
    parsed: dict[str, ast.Module] = {}
    for relative in (*PORTABILITY_CORE_SOURCE_PATHS, PORTABILITY_EVALUATOR_PATH):
        candidate = root / relative
        if not candidate.exists():
            continue
        if not candidate.is_file():
            _blocked(f"portability source is not a regular file: {relative}")
        try:
            parsed[relative] = ast.parse(
                candidate.read_text(encoding="utf-8"), filename=relative
            )
        except (OSError, UnicodeError, SyntaxError) as exc:
            _blocked(f"portability source cannot be parsed: {relative}: {exc}")

    for relative in PORTABILITY_CORE_SOURCE_PATHS:
        tree = parsed.get(relative)
        if tree is None:
            continue
        allowed_internal = set(PORTABILITY_CORE_IMPORT_MODULES[relative])
        for _node, module, _aliases in _resolved_import_rows(
            tree, package="lean_rgc.odlrq"
        ):
            if (
                module.split(".", 1)[0] not in pure_stdlib_roots
                and module not in allowed_internal
            ):
                _blocked(f"non-authorized portability core import: {relative}: {module}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id in forbidden_identifiers
            ):
                _blocked(f"forbidden portability core capability: {relative}: {node.id}")
            if isinstance(node, ast.Attribute) and node.attr in forbidden_identifiers:
                _blocked(f"forbidden portability core capability: {relative}: {node.attr}")
            if isinstance(node, ast.Attribute) and node.attr in forbidden_capability_calls:
                _blocked(f"forbidden portability core capability: {relative}: {node.attr}")
            if (
                isinstance(node, ast.Constant)
                and type(node.value) is str
                and node.value in forbidden_identifiers | forbidden_capability_calls
            ):
                _blocked(f"forbidden portability core capability literal: {relative}")
            if isinstance(node, ast.Call):
                name = _qualified_ast_name(node.func)
                if name is not None and name.rsplit(".", 1)[-1] in (
                    forbidden_capability_calls
                ):
                    _blocked(f"forbidden portability core call: {relative}: {name}")

    core_family_modules = {
        relative[:-3].replace("/", "."): parsed[relative]
        for relative in PORTABILITY_CORE_SOURCE_PATHS
        if relative in parsed
    }
    if core_family_modules and PORTABILITY_EVALUATOR_PATH not in parsed:
        _reject_core_family_identity_dispatch(core_family_modules)

    evaluator = parsed.get(PORTABILITY_EVALUATOR_PATH)
    if evaluator is not None:
        old_imports: list[ast.ImportFrom] = []
        pathlib_imports: list[ast.ImportFrom] = []
        allowed_evaluator = set(PORTABILITY_EVALUATOR_IMPORT_MODULES)
        old_module = "lean_rgc.evals.uprime_u2_u4_development"
        for node, module, aliases in _resolved_import_rows(
            evaluator, package="lean_rgc.evals"
        ):
            if module == old_module:
                if not isinstance(node, ast.ImportFrom) or node.level != 0:
                    _blocked("old I0 compatibility import form differs")
                old_imports.append(node)
                if (
                    tuple(alias.name for alias in aliases)
                    not in (
                        (
                            "build_u24_i0_fixture",
                            "build_u24_artifact_wires",
                        ),
                        (
                            "build_u24_artifact_wires",
                            "build_u24_i0_fixture",
                        ),
                    )
                    or any(alias.asname is not None for alias in aliases)
                ):
                    _blocked("old I0 compatibility import surface differs")
                if _enclosing_function_name(evaluator, node) is None:
                    _blocked("old I0 compatibility import is not function-local")
                continue
            if module == "pathlib":
                if (
                    not isinstance(node, ast.ImportFrom)
                    or node.level != 0
                    or tuple(alias.name for alias in aliases) != ("Path",)
                    or aliases[0].asname is not None
                ):
                    _blocked("evaluator pathlib import must expose only Path")
                pathlib_imports.append(node)
                continue
            if any(
                (alias.asname or alias.name.split(".", 1)[0])
                in {"Path", "__file__"}
                for alias in aliases
            ):
                _blocked("evaluator shadows pathlib.Path through an import")
            if (
                module.split(".", 1)[0] not in pure_stdlib_roots
                and module not in allowed_evaluator
            ):
                _blocked(f"non-authorized evaluator import: {module}")
        if len(pathlib_imports) != 1 or pathlib_imports[0] not in evaluator.body:
            _blocked("evaluator must import exactly pathlib.Path")

        for node in ast.walk(evaluator):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name in {"Path", "__file__"}
            ):
                _blocked("evaluator shadows its matrix path authority")
            if (
                isinstance(node, ast.ExceptHandler)
                and node.name in {"Path", "__file__"}
            ):
                _blocked("evaluator shadows its matrix path authority")
            if (
                isinstance(node, (ast.MatchAs, ast.MatchStar))
                and node.name in {"Path", "__file__"}
            ):
                _blocked("evaluator shadows its matrix path authority")
            if (
                isinstance(node, ast.MatchMapping)
                and node.rest in {"Path", "__file__"}
            ):
                _blocked("evaluator shadows its matrix path authority")
            if isinstance(node, ast.arg) and node.arg in {"Path", "__file__"}:
                _blocked("evaluator shadows its matrix path authority")
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Store)
                and node.id in {"Path", "__file__"}
            ):
                _blocked("evaluator rebinds its matrix path authority")
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id in forbidden_identifiers
            ):
                _blocked(f"evaluator uses forbidden capability: {node.id}")
            if isinstance(node, ast.Attribute) and node.attr in forbidden_identifiers:
                _blocked(f"evaluator uses forbidden capability: {node.attr}")
            if (
                isinstance(node, ast.Attribute)
                and node.attr in forbidden_capability_calls
                and node.attr != "read_bytes"
            ):
                _blocked(f"evaluator uses forbidden capability: {node.attr}")
            if (
                isinstance(node, ast.Constant)
                and type(node.value) is str
                and node.value in forbidden_identifiers | forbidden_capability_calls
            ):
                _blocked("evaluator embeds a forbidden capability literal")
            if isinstance(node, ast.Call):
                call_name = _qualified_ast_name(node.func)
                suffix = None if call_name is None else call_name.rsplit(".", 1)[-1]
                if suffix in forbidden_capability_calls and suffix != "read_bytes":
                    _blocked("evaluator uses a non-matrix filesystem capability")
        _reject_family_identity_dispatch(evaluator)
        if core_family_modules:
            _reject_core_family_identity_dispatch(
                core_family_modules,
                entrypoint=evaluator,
            )
        if len(old_imports) != 1:
            _blocked("evaluator must have one exact function-local old-I0 import")
        matrix_bindings: list[str] = []
        for node in evaluator.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and node.value.value == PORTABILITY_MATRIX_PATH
            ):
                matrix_bindings.append(node.targets[0].id)
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and node.value.value == PORTABILITY_MATRIX_PATH
            ):
                matrix_bindings.append(node.target.id)
        matrix_literals = [
            node for node in ast.walk(evaluator)
            if isinstance(node, ast.Constant) and node.value == PORTABILITY_MATRIX_PATH
        ]
        matrix_reads = [
            node
            for node in ast.walk(evaluator)
            if isinstance(node, ast.Call)
            and (_qualified_ast_name(node.func) or "").rsplit(".", 1)[-1]
            == "read_bytes"
        ]
        matrix_read_attributes = [
            node
            for node in ast.walk(evaluator)
            if isinstance(node, ast.Attribute) and node.attr == "read_bytes"
        ]
        matrix_stores = [
            node
            for node in ast.walk(evaluator)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Store)
            and matrix_bindings
            and node.id == matrix_bindings[0]
        ]
        matrix_shadows = [
            node
            for node in ast.walk(evaluator)
            if matrix_bindings
            and (
                (
                    isinstance(node, ast.arg)
                    and node.arg == matrix_bindings[0]
                )
                or (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == matrix_bindings[0]
                )
                or (
                    isinstance(node, ast.alias)
                    and (node.asname or node.name.split(".", 1)[0])
                    == matrix_bindings[0]
                )
            )
        ]
        if (
            len(matrix_bindings) != 1
            or len(matrix_literals) != 1
            or len(matrix_reads) != 1
            or len(matrix_read_attributes) != 1
            or not isinstance(matrix_reads[0].func, ast.Attribute)
            or matrix_read_attributes[0] is not matrix_reads[0].func
            or len(matrix_stores) != 1
            or matrix_shadows
            or matrix_reads[0].args
            or matrix_reads[0].keywords
            or not _is_exact_matrix_receiver(
                matrix_reads[0].func.value, matrix_bindings[0]
            )
        ):
            _blocked("evaluator must bind and read the exact matrix exactly once")

    for relative, tree in parsed.items():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and type(node.value) is str
                and node.value in forbidden_strings
            ):
                _blocked(f"portability source contains a forbidden literal: {relative}")
            if not isinstance(node, (ast.Dict, ast.List, ast.Tuple)):
                continue
            try:
                value = ast.literal_eval(node)
                encoded = json.dumps(
                    value,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            except (TypeError, ValueError, SyntaxError):
                continue
            if encoded in frozen_structures:
                _blocked(f"portability source embeds a frozen endpoint structure: {relative}")


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
        ("PORTABILITY_AUTHORITY_COMMIT", PORTABILITY_AUTHORITY_COMMIT),
        ("PORTABILITY_AUTHORITY_PARENT", PORTABILITY_AUTHORITY_PARENT),
        ("PORTABILITY_AUTHORITY_TREE", PORTABILITY_AUTHORITY_TREE),
        ("PORTABILITY_AUTHORITY_REF", PORTABILITY_AUTHORITY_REF),
        ("PORTABILITY_ACCEPTED_REF", PORTABILITY_ACCEPTED_REF),
        ("PORTABILITY_RESOURCE_REF", PORTABILITY_RESOURCE_REF),
        (
            "PORTABILITY_AUTHORITY_DOCUMENT_PATH",
            PORTABILITY_AUTHORITY_DOCUMENT_PATH,
        ),
        (
            "PORTABILITY_AUTHORITY_DOCUMENT_BLOB",
            PORTABILITY_AUTHORITY_DOCUMENT_BLOB,
        ),
        (
            "PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256",
            PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256,
        ),
        ("PORTABILITY_MATRIX_PATH", PORTABILITY_MATRIX_PATH),
        ("PORTABILITY_MATRIX_BLOB", PORTABILITY_MATRIX_BLOB),
        ("PORTABILITY_MATRIX_RAW_SHA256", PORTABILITY_MATRIX_RAW_SHA256),
        (
            "PORTABILITY_HISTORICAL_NONINPUT_COMMITS",
            PORTABILITY_HISTORICAL_NONINPUT_COMMITS,
        ),
        (
            "PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS",
            PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS,
        ),
        ("PORTABILITY_CORE_SOURCE_PATHS", PORTABILITY_CORE_SOURCE_PATHS),
        ("PORTABILITY_EVALUATOR_PATH", PORTABILITY_EVALUATOR_PATH),
        ("PORTABILITY_H_ALLOWLIST", PORTABILITY_H_ALLOWLIST),
        (
            "PORTABILITY_PURE_STDLIB_IMPORT_ROOTS",
            PORTABILITY_PURE_STDLIB_IMPORT_ROOTS,
        ),
        (
            "PORTABILITY_CORE_IMPORT_MODULES",
            PORTABILITY_CORE_IMPORT_MODULES,
        ),
        (
            "PORTABILITY_EVALUATOR_IMPORT_MODULES",
            PORTABILITY_EVALUATOR_IMPORT_MODULES,
        ),
        (
            "PORTABILITY_CORE_FAMILY_LABEL_SINKS",
            PORTABILITY_CORE_FAMILY_LABEL_SINKS,
        ),
        (
            "PORTABILITY_DELEGATED_MANIFEST_NODES",
            PORTABILITY_DELEGATED_MANIFEST_NODES,
        ),
    ):
        if name not in assignments or ast.literal_eval(assignments[name]) != expected:
            _blocked(f"guard frozen literal changed: {name}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "compile"}:
                _blocked(f"guard source contains forbidden dynamic code: {node.func.id}")
    enforcement_nodes = {
        id(node)
        for name in (
            "DENYLIST_ROWS",
            "CI_SETUP_ROOT",
            "CI_SETUP_PATHS",
            "EMIT_ROOT",
            "PORTABILITY_MATRIX_PATH",
            "PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS",
        )
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

        if relative == "tests/test_uprime_u24_upper_stack_portability_identity.py":
            try:
                identity_tree = ast.parse(text, filename=relative)
            except SyntaxError as exc:
                _blocked(f"portability identity source does not parse: {exc}")
            identity_tests = [
                node
                for node in identity_tree.body
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]
            if len(identity_tests) != 4 or any(
                node.decorator_list
                or node.args.posonlyargs
                or node.args.args
                or node.args.vararg is not None
                or node.args.kwonlyargs
                or node.args.kwarg is not None
                or node.args.defaults
                or node.args.kw_defaults
                for node in identity_tests
            ):
                _blocked("portability identity must expose exactly four plain tests")
            continue

        if relative in (*PORTABILITY_CORE_SOURCE_PATHS, PORTABILITY_EVALUATOR_PATH):
            verify_u24_portability_source_firewall(root)
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
    "PORTABILITY_ACCEPTED_REF",
    "PORTABILITY_AUTHORITY_COMMIT",
    "PORTABILITY_AUTHORITY_DOCUMENT_BLOB",
    "PORTABILITY_AUTHORITY_DOCUMENT_PATH",
    "PORTABILITY_AUTHORITY_DOCUMENT_RAW_SHA256",
    "PORTABILITY_AUTHORITY_PARENT",
    "PORTABILITY_AUTHORITY_REF",
    "PORTABILITY_AUTHORITY_TREE",
    "PORTABILITY_CORE_IMPORT_MODULES",
    "PORTABILITY_CORE_FAMILY_LABEL_SINKS",
    "PORTABILITY_CORE_SOURCE_PATHS",
    "PORTABILITY_DELEGATED_MANIFEST_NODES",
    "PORTABILITY_EVALUATOR_IMPORT_MODULES",
    "PORTABILITY_EVALUATOR_PATH",
    "PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS",
    "PORTABILITY_HISTORICAL_NONINPUT_COMMITS",
    "PORTABILITY_H_ALLOWLIST",
    "PORTABILITY_MATRIX_BLOB",
    "PORTABILITY_MATRIX_PATH",
    "PORTABILITY_MATRIX_RAW_SHA256",
    "PORTABILITY_PURE_STDLIB_IMPORT_ROOTS",
    "PORTABILITY_RESOURCE_REF",
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
    "validate_u24_portability_control",
    "verify_u24_portability_source_firewall",
    "verify_runner_denylist",
]
