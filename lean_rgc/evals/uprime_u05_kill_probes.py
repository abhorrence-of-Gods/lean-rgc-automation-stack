"""Development-only U'0.5 kill-probe apparatus.

The scientific core is deterministic and accepts an injected reachable chart.
The production matrix remains behind the frozen WP3 outer-receipt, matrix-open,
hosted-CI, and measurement-child guards.  Importing this module never opens a
task file or materializes the frozen task array.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
from urllib.parse import quote
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction
from itertools import combinations
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from lean_rgc.odlrq.hankel import (
    HankelCutoffReport,
    HankelProbeReport,
    evaluate_hankel_probe,
    hankel_dimensions,
)
from lean_rgc.lean.kernel_rpc_client import (
    RuntimeStateView,
    StrictKernelRPCError,
    StrictKernelRPCOracleAdapter,
    SynchronousJSONLSubprocessTransport,
)
from lean_rgc.odlrq.contracts import ActionSymbol, StrictContractError, U05TaskSpec
from lean_rgc.odlrq.reachable_chart import (
    ChartLimits,
    ChartPrerequisiteBlocked,
    ReachableChart,
    build_reachable_chart,
)
from lean_rgc.odlrq.rule_algebra import ActionWord, OracleEvent, OutcomeKind, StateView


TASK_MATRIX_SHA256 = "C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3"
ACTION_MATRIX_SHA256 = "6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D"
OPAQUE_SIMP_SHA256 = "CE264CA0DB8A2B6CD05AFAB00A3C4E3572BB83007BA043E8331ECC681400380D"
PRODUCTION_TASK_IDS = frozenset(
    {
        "u05_identity",
        "u05_pair",
        "u05_split",
        "u05_nested_split",
        "u05_nat_zero",
    }
)
FROZEN_LIMITS: Mapping[str, Any] = MappingProxyType(
    {
        "maximum_symbolic_word_depth": 3,
        "maximum_unique_states_per_task": 256,
        "maximum_unique_states_total": 1024,
        "maximum_primary_state_action_attempts": 12_288,
        "maximum_replay_reexecutions": 12_288,
        "maximum_prefix_tactic_executions": 7,
        "maximum_total_lean_tactic_executions": 24_583,
        "maximum_symbolic_word_occurrences": 15_000,
        "maximum_hankel_cells": 100_000,
        "task_prefix_max_heartbeats": 20_000,
        "per_action_max_heartbeats": 20_000,
        "episode_heartbeat_budget": "NOT_ENFORCED_DEVELOPMENT_ONLY",
        "episode_telemetry_coverage": False,
        "per_action_wall_timeout_seconds": 30,
        "whole_run_wall_limit_seconds": 1_800,
        "cache_policy": "bypass",
        "repo_root_lean_toolchain_status": "absent_by_design",
        "expected_lean_version_prefix": "Lean (version 4.31.0,",
        "executed_lean_binary_sha256": (
            "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
        ),
        "look_count": 1,
    }
)

ATTEMPT_RECEIPT_SCHEMA = "lean-rgc-uprime-u05-attempt-receipt-v1.0"
MATRIX_OPEN_SCHEMA = "lean-rgc-uprime-u05-matrix-open-v1.0"
ATTEMPT_ENVELOPE_SCHEMA = "lean-rgc-uprime-u05-attempt-envelope-v1.0"
RAW_RESULT_SCHEMA = "lean-rgc-uprime-u05-kill-probes-v1.0"
PLAN_COMMIT = "0da9ff3de91819778761fb087e85e6f83e4c9ea4"
PLAN_PATH = Path(
    "docs/experiments/"
    "uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md"
)
PLAN_BLOB = "2b2355f49aef149c1a7b5493951fa10e4a254235"
BRANCH_REF = "refs/heads/codex/uprime-odlrq-plan"
UPSTREAM_REF = "refs/remotes/origin/codex/uprime-odlrq-plan"
CI_WORKFLOW_PATH = ".github/workflows/ci.yml"
CI_WORKFLOW_NAME = "CI"
CI_JOB_NAME = "pytest"
CI_ACCEPTED_CONCLUSION = "success"
MEASUREMENT_BOOTSTRAP = """\
import json,os,runpy,socket,sys
def _u05_denied(*_args,**_kwargs):
    raise RuntimeError("U05 measurement bootstrap denied network access")
class _U05DeniedSocket(socket.socket):
    def connect(self,*_args,**_kwargs): return _u05_denied()
    def connect_ex(self,*_args,**_kwargs): return _u05_denied()
socket.socket=_U05DeniedSocket
socket.create_connection=_u05_denied
socket.getaddrinfo=_u05_denied
sys.path[:]=json.loads(os.environ["UPRIME_U05_PYTHON_IMPORT_PATHS"])
sys.argv=["lean_rgc.evals.uprime_u05_kill_probes",*sys.argv[1:]]
runpy.run_module("lean_rgc.evals.uprime_u05_kill_probes",run_name="__main__",alter_sys=True)
"""
IMPLEMENTATION_ALLOWLIST = frozenset(
    {
        "lean_rgc/native_lean/RGCKernelRPC.lean",
        "lean_rgc/lean/kernel_state_identity.py",
        "lean_rgc/lean/kernel_rpc_client.py",
        "lean_rgc/lean/native_worker.py",
        "lean_rgc/odlrq/__init__.py",
        "lean_rgc/odlrq/contracts.py",
        "lean_rgc/odlrq/rule_algebra.py",
        "lean_rgc/odlrq/reachable_chart.py",
        "lean_rgc/odlrq/hankel.py",
        "lean_rgc/evals/uprime_u05_kill_probes.py",
        "tests/test_v49_kernel_rpc_worker.py",
        "tests/test_uprime_u05_identity.py",
        "tests/test_uprime_u05_kill_probes.py",
        "tests/tier_manifest.json",
    }
)

# Exact canonical JSON bytes frozen in the registered plan.  Keep these strings
# unparsed until the complete production authorization is supplied.
_TASK_MATRIX_CANONICAL_JSON = (
    '[{"imports":["Lean"],"max_heartbeats":20000,"prefix":"intro P\\nintro h",'
    '"statement":"forall P : Prop, P -> P","task_id":"u05_identity"},'
    '{"imports":["Lean"],"max_heartbeats":20000,"prefix":"intro P\\nintro Q\\nintro hP\\nintro hQ",'
    '"statement":"forall P Q : Prop, P -> Q -> P /\\\\ Q","task_id":"u05_pair"},'
    '{"imports":["Lean"],"max_heartbeats":20000,"prefix":"",'
    '"statement":"True /\\\\ True","task_id":"u05_split"},'
    '{"imports":["Lean"],"max_heartbeats":20000,"prefix":"",'
    '"statement":"(True /\\\\ True) /\\\\ True","task_id":"u05_nested_split"},'
    '{"imports":["Lean"],"max_heartbeats":20000,"prefix":"intro n",'
    '"statement":"forall n : Nat, n + 0 = n","task_id":"u05_nat_zero"}]'
)

_ACTION_MATRIX_CANONICAL_JSON = (
    '[{"action_id":"a00_constructor_first","expected_normalized_type_signature":null,'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"constructor","premise_selector_ordinal":null,'
    '"premise_slot_rule_id":null,"target_selector":"first"},'
    '{"action_id":"a01_constructor_last","expected_normalized_type_signature":null,'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"constructor","premise_selector_ordinal":null,'
    '"premise_slot_rule_id":null,"target_selector":"last"},'
    '{"action_id":"a02_exact_h_first","expected_normalized_type_signature":"FVAR_TYPE(local:0)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":1,'
    '"premise_slot_rule_id":"local_decl_1_type_local_0","target_selector":"first"},'
    '{"action_id":"a03_exact_h_last","expected_normalized_type_signature":"FVAR_TYPE(local:0)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":1,'
    '"premise_slot_rule_id":"local_decl_1_type_local_0","target_selector":"last"},'
    '{"action_id":"a04_exact_hP_first","expected_normalized_type_signature":"FVAR_TYPE(local:0)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":2,'
    '"premise_slot_rule_id":"local_decl_2_type_local_0","target_selector":"first"},'
    '{"action_id":"a05_exact_hP_last","expected_normalized_type_signature":"FVAR_TYPE(local:0)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":2,'
    '"premise_slot_rule_id":"local_decl_2_type_local_0","target_selector":"last"},'
    '{"action_id":"a06_exact_hQ_first","expected_normalized_type_signature":"FVAR_TYPE(local:1)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":3,'
    '"premise_slot_rule_id":"local_decl_3_type_local_1","target_selector":"first"},'
    '{"action_id":"a07_exact_hQ_last","expected_normalized_type_signature":"FVAR_TYPE(local:1)",'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_local","premise_selector_ordinal":3,'
    '"premise_slot_rule_id":"local_decl_3_type_local_1","target_selector":"last"},'
    '{"action_id":"a08_exact_True_intro_first","expected_normalized_type_signature":"CONST(True)",'
    '"global_constant":"True.intro","max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_const","premise_selector_ordinal":null,'
    '"premise_slot_rule_id":null,"target_selector":"first"},'
    '{"action_id":"a09_exact_True_intro_last","expected_normalized_type_signature":"CONST(True)",'
    '"global_constant":"True.intro","max_heartbeats":20000,"opaque_hyperedge_digest":null,'
    '"opaque_hyperedge_source":null,"opcode":"exact_const","premise_selector_ordinal":null,'
    '"premise_slot_rule_id":null,"target_selector":"last"},'
    '{"action_id":"a10_simp_Nat_add_zero_first","expected_normalized_type_signature":null,'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":"'
    + OPAQUE_SIMP_SHA256
    + '","opaque_hyperedge_source":"simp only [Nat.add_zero]","opcode":"opaque_tactic",'
    '"premise_selector_ordinal":null,"premise_slot_rule_id":null,"target_selector":"first"},'
    '{"action_id":"a11_simp_Nat_add_zero_last","expected_normalized_type_signature":null,'
    '"global_constant":null,"max_heartbeats":20000,"opaque_hyperedge_digest":"'
    + OPAQUE_SIMP_SHA256
    + '","opaque_hyperedge_source":"simp only [Nat.add_zero]","opcode":"opaque_tactic",'
    '"premise_selector_ordinal":null,"premise_slot_rule_id":null,"target_selector":"last"}]'
)


@dataclass(frozen=True)
class KP1CutoffReport:
    cutoff: int
    n_occ_open: int
    n_id_open: int
    c_id_open: Fraction | None
    n_obs_open: int
    c_obs_open: Fraction | None
    p_raw_open: Fraction | None
    first_entry_closed: int
    derived_closed: int
    first_entry_sink: int
    derived_sink: int
    censored: int


@dataclass(frozen=True)
class KP1Report:
    disposition: str
    cutoffs: tuple[KP1CutoffReport, ...]
    nontrivial_identity_classes: int
    nontrivial_class_task_ids: tuple[str, ...]
    blocked_reason: str | None = None


@dataclass(frozen=True)
class KP2Report:
    disposition: str
    successful_trajectories: int
    eligible_open_steps: int
    eligible_open_blocks: int
    contractive_blocks: int
    eligible_open_blocks_by_length: tuple[int, int, int]
    contractive_blocks_by_length: tuple[int, int, int]
    terminal_close_steps: int
    one_step_noncontractive_fraction: Fraction | None
    coordinate_increase_fractions: tuple[Fraction | None, ...]
    longest_noncontractive_run: int
    blocked_reason: str | None = None


@dataclass(frozen=True)
class KillProbeReport:
    schema: str
    kp1: KP1Report
    kp2: KP2Report
    kp3: HankelProbeReport
    capability_matrix: Mapping[str, Mapping[str, Any]]
    licenses_k1_k4: bool = False
    licenses_u2_u5_claims: bool = False
    licenses_wp4_wp12_implementation: bool = False
    licenses_gpu: bool = False
    licenses_canonical_rpc_rerun: bool = False
    licenses_reserved_data_read: bool = False


class ProductionExecutionDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class ProductionAuthorization:
    """Output of the future outer pre-receipt preflight, never a CLI claim."""

    anchor: str
    full_anchor_verified: bool
    exclusive_reservation_verified: bool
    pushed_green_candidate_verified: bool
    disposable_clean_worktree_verified: bool

    def validate(self) -> None:
        if re.fullmatch(r"[0-9a-f]{40}", self.anchor) is None:
            raise ProductionExecutionDenied("anchor must be a full lowercase commit ID")
        checks = {
            "full anchor": self.full_anchor_verified,
            "exclusive reservation": self.exclusive_reservation_verified,
            "pushed green candidate": self.pushed_green_candidate_verified,
            "disposable clean worktree": self.disposable_clean_worktree_verified,
        }
        missing = [name for name, passed in checks.items() if not passed]
        if missing:
            raise ProductionExecutionDenied(
                "production preflight incomplete: " + ", ".join(missing)
            )


def frozen_matrix_digests() -> Mapping[str, str]:
    """Return literal digests without parsing/materializing production tasks."""

    return {
        "task_matrix_sha256": TASK_MATRIX_SHA256,
        "action_matrix_sha256": ACTION_MATRIX_SHA256,
    }


def verify_frozen_matrix_literals() -> bool:
    return (
        hashlib.sha256(_TASK_MATRIX_CANONICAL_JSON.encode("utf-8"))
        .hexdigest()
        .upper()
        == TASK_MATRIX_SHA256
        and hashlib.sha256(_ACTION_MATRIX_CANONICAL_JSON.encode("utf-8"))
        .hexdigest()
        .upper()
        == ACTION_MATRIX_SHA256
    )


def load_frozen_execution_matrix(
    authorization: ProductionAuthorization | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]]:
    """Materialize the frozen records only after every production guard passes."""

    env = os.environ if environ is None else environ
    if env.get("UPRIME_U05_EXECUTE") != "1":
        raise ProductionExecutionDenied("UPRIME_U05_EXECUTE=1 is required")
    if authorization is None:
        raise ProductionExecutionDenied("exclusive production authorization is absent")
    authorization.validate()
    if not verify_frozen_matrix_literals():
        raise ProductionExecutionDenied("frozen matrix literal digest mismatch")
    tasks = tuple(json.loads(_TASK_MATRIX_CANONICAL_JSON))
    actions = tuple(json.loads(_ACTION_MATRIX_CANONICAL_JSON))
    if frozenset(row["task_id"] for row in tasks) != PRODUCTION_TASK_IDS:
        raise ProductionExecutionDenied("production task ID inventory mismatch")
    if len(actions) != 12:
        raise ProductionExecutionDenied("production action alphabet is not size 12")
    return tasks, actions


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical UTF-8 JSON used by receipts, markers, raw output and envelopes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"


def _parse_canonical_json(raw: bytes, *, schema: str | None = None) -> dict[str, Any]:
    def reject_constant(value: str) -> Any:
        raise ValueError(f"nonfinite JSON constant is forbidden: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), parse_constant=reject_constant
        )
        canonical = canonical_json_bytes(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ProductionExecutionDenied("invalid canonical JSON artifact") from exc
    if type(value) is not dict or canonical != raw:
        raise ProductionExecutionDenied("artifact bytes are not canonical JSON")
    if schema is not None and value.get("schema") != schema:
        raise ProductionExecutionDenied(f"artifact schema is not {schema}")
    return value


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    git = os.environ.get("UPRIME_U05_GIT_EXECUTABLE") or shutil.which("git")
    if not git:
        raise ProductionExecutionDenied("Git executable is unavailable")
    proc = subprocess.run(
        [str(Path(git).resolve()), "--no-replace-objects", *args],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        message = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ProductionExecutionDenied(f"git {' '.join(args)} failed: {message}")
    return proc


def _git_text(repo_root: Path, *args: str) -> str:
    return _git(repo_root, *args).stdout.decode("utf-8", errors="strict").strip()


def _ensure_repo_relative(repo_root: Path, value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    root = repo_root.resolve()
    lexical = Path(os.path.abspath(root / path if not path.is_absolute() else path))
    try:
        lexical.relative_to(root)
    except ValueError as exc:
        raise ProductionExecutionDenied(f"output path escapes repository: {value}") from exc
    # Inspect the lexical chain before resolving it; otherwise a junction is
    # followed and the evidence that a reparse component existed is lost.
    _assert_plain_parent_chain(root, lexical)
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ProductionExecutionDenied(f"output path escapes repository: {value}") from exc
    return resolved


def _is_git_ignored(repo_root: Path, path: Path) -> bool:
    relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    return (
        _git(repo_root, "check-ignore", "--quiet", "--no-index", "--", relative, check=False)
        .returncode
        == 0
    )


def _assert_plain_parent_chain(repo_root: Path, path: Path) -> None:
    root = repo_root.resolve()
    current = path.parent
    checked: list[Path] = []
    while True:
        checked.append(current)
        if current == root:
            break
        if current.parent == current:
            raise ProductionExecutionDenied("output parent chain escaped repository root")
        current = current.parent
    for directory in reversed(checked):
        if not directory.exists():
            continue
        info = directory.lstat()
        attributes = getattr(info, "st_file_attributes", 0)
        if directory.is_symlink() or attributes & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ProductionExecutionDenied(
                f"output parent is a symlink/reparse point: {directory}"
            )
        if not directory.is_dir():
            raise ProductionExecutionDenied(f"output parent is not a directory: {directory}")


def _validate_frozen_output_paths(
    repo_root: Path,
    *,
    anchor: str,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
) -> tuple[Path, Path, Path, Path]:
    receipt = _ensure_repo_relative(repo_root, receipt_path)
    raw = _ensure_repo_relative(repo_root, raw_output_path)
    artifact = _ensure_repo_relative(repo_root, artifact_path)
    expected_receipt = (
        repo_root / f"runs/uprime_u05_20260711/attempt_receipt_{anchor[:12]}.json"
    ).resolve()
    expected_raw = (
        repo_root / f"runs/uprime_u05_20260711/runner_raw_{anchor[:12]}.json"
    ).resolve()
    expected_artifact = (
        repo_root
        / "docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json"
    ).resolve()
    if (receipt, raw, artifact) != (expected_receipt, expected_raw, expected_artifact):
        raise ProductionExecutionDenied("output paths differ from the frozen WP3 command")
    marker = _matrix_marker_path(receipt, anchor).resolve()
    if len({receipt, raw, artifact, marker}) != 4:
        raise ProductionExecutionDenied("receipt/raw/artifact/marker paths are not distinct")
    for path in (receipt, raw, artifact, marker):
        _assert_plain_parent_chain(repo_root, path)
    if not all(_is_git_ignored(repo_root, path) for path in (receipt, raw, marker)):
        raise ProductionExecutionDenied("runs receipt/raw/marker paths must be Git-ignored")
    if _is_git_ignored(repo_root, artifact):
        raise ProductionExecutionDenied("tracked result artifact path must not be Git-ignored")
    return receipt, raw, artifact, marker


def _exclusive_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def _lexists(path: Path) -> bool:
    return os.path.lexists(str(path))


def _atomic_write_new(path: Path, raw: bytes) -> None:
    """Publish a new file atomically without a destination-overwrite race."""

    if _lexists(path):
        raise ProductionExecutionDenied(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + f".tmp.{os.getpid()}")
    _exclusive_write(temp_path, raw)
    try:
        try:
            os.link(temp_path, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise ProductionExecutionDenied(
                f"artifact appeared during publication: {path}"
            ) from exc
        temp_path.unlink()
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if _lexists(temp_path):
            temp_path.unlink()


def _raw_commit_parents(repo_root: Path, commit: str) -> tuple[str, ...]:
    raw = _git(repo_root, "cat-file", "-p", commit).stdout.decode("utf-8")
    headers = raw.split("\n\n", 1)[0].splitlines()
    return tuple(row[7:] for row in headers if row.startswith("parent "))


def _validate_candidate_topology(repo_root: Path, anchor: str) -> Mapping[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", anchor) is None:
        raise ProductionExecutionDenied("candidate anchor must be full lowercase SHA")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    if head != anchor:
        raise ProductionExecutionDenied("candidate anchor is not HEAD")
    if _git_text(repo_root, "rev-parse", "--abbrev-ref", "HEAD") != "HEAD":
        raise ProductionExecutionDenied("U05 must run in a detached worktree")
    if _git_text(repo_root, "rev-parse", f"HEAD:{PLAN_PATH.as_posix()}") != PLAN_BLOB:
        raise ProductionExecutionDenied("frozen plan blob changed")
    if _git(repo_root, "merge-base", "--is-ancestor", PLAN_COMMIT, anchor, check=False).returncode:
        raise ProductionExecutionDenied("candidate is not a descendant of the plan anchor")
    commits = tuple(
        row
        for row in _git_text(
            repo_root, "rev-list", "--first-parent", "--reverse", f"{PLAN_COMMIT}..{anchor}"
        ).splitlines()
        if row
    )
    if not 1 <= len(commits) <= 4:
        raise ProductionExecutionDenied("implementation commit count is outside 1..4")
    previous = PLAN_COMMIT
    rows: list[Mapping[str, Any]] = []
    for commit in commits:
        if _raw_commit_parents(repo_root, commit) != (previous,):
            raise ProductionExecutionDenied("implementation interval is not single-parent contiguous")
        changed = tuple(
            sorted(
                row
                for row in _git_text(
                    repo_root,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "--no-renames",
                    "-r",
                    commit,
                ).splitlines()
                if row
            )
        )
        outside = sorted(set(changed) - IMPLEMENTATION_ALLOWLIST)
        if outside:
            raise ProductionExecutionDenied(f"implementation changed paths outside allowlist: {outside}")
        if _git_text(repo_root, "rev-parse", f"{commit}:{PLAN_PATH.as_posix()}") != PLAN_BLOB:
            raise ProductionExecutionDenied("implementation commit changed frozen plan blob")
        rows.append({"commit": commit, "parent": previous, "changed_paths": list(changed)})
        previous = commit
    return {"plan_commit": PLAN_COMMIT, "candidate": anchor, "commits": rows}


def _parse_github_origin(origin: str) -> tuple[str, str]:
    patterns = (
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        r"ssh://git@github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, origin.strip())
        if match:
            return match.group(1), match.group(2)
    raise ProductionExecutionDenied("origin is not a canonical GitHub repository URL")


def _gh_api(endpoint: str) -> Mapping[str, Any]:
    gh = shutil.which("gh")
    if gh is None:
        raise ProductionExecutionDenied("GitHub CLI is unavailable")
    try:
        proc = subprocess.run(
            [
                str(Path(gh).resolve()),
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                endpoint,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProductionExecutionDenied("read-only hosted-CI query timed out") from exc
    if proc.returncode:
        raise ProductionExecutionDenied(
            "read-only hosted-CI query failed: "
            + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    try:
        value = json.loads(proc.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductionExecutionDenied("hosted-CI query returned invalid JSON") from exc
    if type(value) is not dict:
        raise ProductionExecutionDenied("hosted-CI query did not return an object")
    return value


def _paginated_api_rows(
    api: Callable[[str], Mapping[str, Any]],
    *,
    endpoint: str,
    field_name: str,
) -> list[Any]:
    rows: list[Any] = []
    expected_total: int | None = None
    for page in range(1, 101):
        separator = "&" if "?" in endpoint else "?"
        value = api(f"{endpoint}{separator}page={page}")
        page_rows = value.get(field_name)
        if type(page_rows) is not list:
            raise ProductionExecutionDenied(f"{field_name} response is malformed")
        total = value.get("total_count")
        if type(total) is not int or isinstance(total, bool) or total < 0:
            raise ProductionExecutionDenied(f"{field_name} total_count is malformed")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise ProductionExecutionDenied(f"{field_name} total_count changed during pagination")
        rows.extend(page_rows)
        if len(rows) > total:
            raise ProductionExecutionDenied(f"{field_name} pagination exceeded total_count")
        if len(page_rows) < 100 or len(rows) == total:
            break
    else:
        raise ProductionExecutionDenied(f"{field_name} pagination exceeded 100 pages")
    if expected_total is None or len(rows) != expected_total:
        raise ProductionExecutionDenied(f"{field_name} pagination was incomplete")
    identifiers = [row.get("id") for row in rows if type(row) is dict]
    if (
        len(identifiers) != len(rows)
        or any(type(value) is not int or isinstance(value, bool) for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ProductionExecutionDenied(f"{field_name} pagination has invalid/duplicate IDs")
    return rows


def verify_ci_control_plane(
    repo_root: Path,
    *,
    anchor: str,
    upstream: str,
    workflow_path: str,
    job_name: str,
    accepted_conclusion: str,
    api: Callable[[str], Mapping[str, Any]] = _gh_api,
) -> Mapping[str, Any]:
    """Derive the unique accepted Actions run/job; caller fields are expectations only."""

    if upstream != UPSTREAM_REF:
        raise ProductionExecutionDenied("unexpected upstream ref")
    if workflow_path != CI_WORKFLOW_PATH or job_name != CI_JOB_NAME:
        raise ProductionExecutionDenied("unexpected CI workflow/job")
    if accepted_conclusion != CI_ACCEPTED_CONCLUSION:
        raise ProductionExecutionDenied("unexpected accepted CI conclusion")
    if _git_text(repo_root, "rev-parse", upstream) != anchor:
        raise ProductionExecutionDenied("upstream head does not equal candidate")
    owner, repository = _parse_github_origin(
        _git_text(repo_root, "remote", "get-url", "origin")
    )
    branch = BRANCH_REF.removeprefix("refs/heads/")
    encoded_workflow = quote(workflow_path, safe="")
    encoded_branch = quote(branch, safe="")
    runs_endpoint = (
        f"/repos/{owner}/{repository}/actions/workflows/{encoded_workflow}/runs"
        f"?branch={encoded_branch}&event=push&head_sha={anchor}&per_page=100"
    )
    runs = _paginated_api_rows(
        api, endpoint=runs_endpoint, field_name="workflow_runs"
    )
    matches = [
        row
        for row in runs
        if type(row) is dict
        and row.get("head_sha") == anchor
        and row.get("event") == "push"
        and row.get("status") == "completed"
        and row.get("conclusion") == accepted_conclusion
        and row.get("head_branch") == branch
        and row.get("name") == CI_WORKFLOW_NAME
        and row.get("path") == CI_WORKFLOW_PATH
    ]
    if len(matches) != 1:
        raise ProductionExecutionDenied("hosted CI run match is not unique")
    run = matches[0]
    run_id = run.get("id")
    if type(run_id) is not int or isinstance(run_id, bool):
        raise ProductionExecutionDenied("hosted CI run ID is invalid")
    jobs = _paginated_api_rows(
        api,
        endpoint=f"/repos/{owner}/{repository}/actions/runs/{run_id}/jobs?per_page=100",
        field_name="jobs",
    )
    job_matches = [
        row
        for row in jobs
        if type(row) is dict
        and row.get("name") == job_name
        and row.get("status") == "completed"
        and row.get("conclusion") == accepted_conclusion
        and row.get("head_sha") == anchor
    ]
    if len(job_matches) != 1:
        raise ProductionExecutionDenied("hosted CI job match is not unique")
    job = job_matches[0]
    job_id = job.get("id")
    if type(job_id) is not int or isinstance(job_id, bool):
        raise ProductionExecutionDenied("hosted CI job ID is invalid")
    workflow_blob = _git_text(repo_root, "rev-parse", f"HEAD:{workflow_path}")
    return {
        "provider": "github_actions_read_only_gh_api",
        "origin_repository": f"{owner}/{repository}",
        "branch_ref": BRANCH_REF,
        "upstream_ref": upstream,
        "workflow_path": workflow_path,
        "workflow_name": CI_WORKFLOW_NAME,
        "workflow_blob": workflow_blob,
        "run_id": run_id,
        "job_id": job_id,
        "head_sha": anchor,
        "event": "push",
        "conclusion": accepted_conclusion,
    }


def _lp(raw: bytes) -> bytes:
    return len(raw).to_bytes(8, "big") + raw


def _canonical_record_bytes(value: Sequence[Any]) -> bytes:
    return json.dumps(
        list(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def merkle_sha256(schema_tag: str, records: Iterable[Sequence[Any]]) -> str:
    canonical = sorted(_canonical_record_bytes(row) for row in records)
    if not canonical:
        raise ProductionExecutionDenied("Merkle manifest cannot be empty")
    if len(set(canonical)) != len(canonical):
        raise ProductionExecutionDenied("Merkle manifest contains duplicate records")
    parsed = [json.loads(row.decode("utf-8")) for row in canonical]
    keys = [_canonical_record_bytes(row[:-1]) for row in parsed]
    if len(set(keys)) != len(keys):
        raise ProductionExecutionDenied("Merkle manifest contains a duplicate normalized key")
    leaf_values = [hashlib.sha256(row).digest() for row in canonical]
    level = [hashlib.sha256(b"\x00" + leaf).digest() for leaf in leaf_values]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(b"\x01" + level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    root = hashlib.sha256(
        b"\x02"
        + _lp(schema_tag.encode("utf-8"))
        + _lp(level[0])
        + _lp(len(canonical).to_bytes(8, "big"))
    ).hexdigest()
    return root.upper()


def _stable_file_hash(path: Path) -> tuple[str, int]:
    try:
        before = path.stat()
        if not path.is_file() or path.is_symlink():
            raise ProductionExecutionDenied(f"manifest entry is not a regular file: {path}")
        attributes = getattr(before, "st_file_attributes", 0)
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ProductionExecutionDenied(f"manifest entry is a reparse point: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        after = path.stat()
    except OSError as exc:
        raise ProductionExecutionDenied(f"cannot hash manifest file: {path}") from exc
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ProductionExecutionDenied(f"manifest file mutated while hashing: {path}")
    return digest.hexdigest().upper(), before.st_size


def _normalized_relative(path: Path, root: Path) -> str:
    try:
        raw = path.resolve().relative_to(root.resolve()).as_posix()
        value = unicodedata.normalize("NFC", raw).casefold()
    except ValueError as exc:
        raise ProductionExecutionDenied(f"path escapes manifest root: {path}") from exc
    if not value:
        raise ProductionExecutionDenied("empty normalized manifest path")
    return value


def _pe_import_names_with_digest(path: Path) -> tuple[tuple[str, ...], str]:
    """Parse the deterministic PE import-name table without loading the image."""

    before = path.lstat()
    if path.is_symlink() or getattr(before, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
    ):
        raise ProductionExecutionDenied(f"PE image is a symlink/reparse point: {path}")
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ProductionExecutionDenied(f"PE image changed while parsing: {path}")
    try:
        if raw[:2] != b"MZ":
            raise ValueError("missing MZ")
        pe_offset = struct.unpack_from("<I", raw, 0x3C)[0]
        if raw[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        section_count = struct.unpack_from("<H", raw, pe_offset + 6)[0]
        optional_size = struct.unpack_from("<H", raw, pe_offset + 20)[0]
        optional = pe_offset + 24
        magic = struct.unpack_from("<H", raw, optional)[0]
        if magic == 0x20B:
            data_directory = optional + 112
        elif magic == 0x10B:
            data_directory = optional + 96
        else:
            raise ValueError("unknown optional-header magic")
        import_rva, _import_size = struct.unpack_from("<II", raw, data_directory + 8)
        if import_rva == 0:
            return (), _sha256_bytes(raw)
        sections_offset = optional + optional_size
        sections: list[tuple[int, int, int]] = []
        for index in range(section_count):
            offset = sections_offset + 40 * index
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", raw, offset + 8
            )
            sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

        def rva_offset(rva: int) -> int:
            for address, size, pointer in sections:
                if address <= rva < address + size:
                    return pointer + rva - address
            raise ValueError(f"unmapped RVA {rva}")

        cursor = rva_offset(import_rva)
        names: list[str] = []
        while True:
            descriptor = struct.unpack_from("<IIIII", raw, cursor)
            if not any(descriptor):
                break
            name_offset = rva_offset(descriptor[3])
            end = raw.index(b"\0", name_offset)
            name = raw[name_offset:end].decode("ascii", errors="strict").casefold()
            if not name or "/" in name or "\\" in name:
                raise ValueError("invalid import name")
            names.append(name)
            cursor += 20
    except (IndexError, struct.error, UnicodeDecodeError, ValueError) as exc:
        raise ProductionExecutionDenied(f"cannot parse PE imports: {path}") from exc
    if len(set(names)) != len(names):
        raise ProductionExecutionDenied(f"PE image repeats an import name: {path}")
    return tuple(names), _sha256_bytes(raw)


def _pe_import_names(path: Path) -> tuple[str, ...]:
    return _pe_import_names_with_digest(path)[0]


def _resolve_api_set_provider(contract_name: str, system_root: Path) -> Path:
    """Resolve one API-set contract through the Windows loader, System32 only."""

    if os.name != "nt" or not contract_name.startswith(("api-ms-win-", "ext-ms-win-")):
        raise ProductionExecutionDenied("invalid Windows API-set contract")
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    load_library = kernel32.LoadLibraryExW
    load_library.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    load_library.restype = wintypes.HMODULE
    free_library = kernel32.FreeLibrary
    free_library.argtypes = [wintypes.HMODULE]
    free_library.restype = wintypes.BOOL
    get_name = kernel32.GetModuleFileNameW
    get_name.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    get_name.restype = wintypes.DWORD
    handle = load_library(contract_name, None, 0x00000800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
    if not handle:
        raise ProductionExecutionDenied(f"cannot resolve API-set provider: {contract_name}")
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        if not get_name(handle, buffer, len(buffer)):
            raise ProductionExecutionDenied(
                f"cannot name API-set provider: {contract_name}"
            )
        provider = Path(buffer.value).resolve()
    finally:
        free_library(handle)
    try:
        provider.relative_to(system_root.resolve())
    except ValueError as exc:
        raise ProductionExecutionDenied(
            f"API-set provider escaped Windows system root: {contract_name}"
        ) from exc
    if not provider.is_file():
        raise ProductionExecutionDenied(f"API-set provider is absent: {contract_name}")
    return provider


def _windows_build_payload() -> list[str]:
    if os.name != "nt":
        raise ProductionExecutionDenied("U05 production environment must be Windows")
    import winreg

    key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    fields = (
        "ProductName",
        "DisplayVersion",
        "CurrentBuildNumber",
        "UBR",
        "InstallationType",
    )
    values: list[str] = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
        for field_name in fields:
            value, _kind = winreg.QueryValueEx(key, field_name)
            values.append(str(value))
    values.append(platform.machine())
    return values


def _read_worker_line(process: subprocess.Popen[bytes], *, timeout: float) -> bytes:
    import queue
    import threading

    result: queue.Queue[bytes | BaseException] = queue.Queue(maxsize=1)

    def read() -> None:
        try:
            assert process.stdout is not None
            result.put(process.stdout.readline())
        except BaseException as exc:  # pragma: no cover - defensive transport path
            result.put(exc)

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    try:
        value = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise ProductionExecutionDenied("native worker response timed out") from exc
    if isinstance(value, BaseException):
        raise ProductionExecutionDenied("native worker response read failed") from value
    if not value:
        stderr = b""
        if process.stderr is not None:
            stderr = process.stderr.read(4096)
        raise ProductionExecutionDenied(
            "native worker exited before response: "
            + stderr.decode("utf-8", errors="replace")
        )
    return value


def _lean_worker_environment(lean_binary: Path) -> dict[str, str]:
    system_root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT")
    comspec = os.environ.get("ComSpec") or os.environ.get("COMSPEC")
    if not system_root or not comspec:
        raise ProductionExecutionDenied("Windows environment is incomplete for Lean worker")
    root = Path(system_root).resolve()
    return {
        "COMSPEC": str(Path(comspec).resolve()),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": os.pathsep.join([str(lean_binary.parent.resolve()), str(root / "System32")]),
        "SYSTEMROOT": str(root),
        "TEMP": str(Path(tempfile.gettempdir()).resolve()),
        "TMP": str(Path(tempfile.gettempdir()).resolve()),
        "WINDIR": str(root),
    }


def _probe_worker_loaded_modules(lean_binary: Path, worker_source: Path) -> tuple[Path, ...]:
    if os.name != "nt":
        raise ProductionExecutionDenied("loaded-module attestation requires Windows")

    def mapped_modules(pid: int) -> set[Path]:
        import ctypes
        from ctypes import wintypes

        query_information = 0x0400
        vm_read = 0x0010
        list_modules_all = 0x03
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        enum_modules = psapi.EnumProcessModulesEx
        enum_modules.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.HMODULE),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.DWORD,
        ]
        enum_modules.restype = wintypes.BOOL
        module_name = psapi.GetModuleFileNameExW
        module_name.argtypes = [
            wintypes.HANDLE,
            wintypes.HMODULE,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        module_name.restype = wintypes.DWORD
        handle = open_process(query_information | vm_read, False, pid)
        if not handle:
            raise ProductionExecutionDenied("cannot open native worker for module inventory")
        try:
            capacity = 256
            while True:
                modules = (wintypes.HMODULE * capacity)()
                needed = wintypes.DWORD()
                if not enum_modules(
                    handle,
                    modules,
                    ctypes.sizeof(modules),
                    ctypes.byref(needed),
                    list_modules_all,
                ):
                    raise ProductionExecutionDenied("cannot enumerate native worker modules")
                count = needed.value // ctypes.sizeof(wintypes.HMODULE)
                if count <= capacity:
                    break
                capacity = count + 32
            result: set[Path] = set()
            for module in modules[:count]:
                buffer = ctypes.create_unicode_buffer(32768)
                if not module_name(handle, module, buffer, len(buffer)):
                    raise ProductionExecutionDenied("cannot resolve native worker module path")
                result.add(Path(buffer.value).resolve())
            return result
        finally:
            close_handle(handle)

    process = subprocess.Popen(
        [str(lean_binary), "--run", str(worker_source), "--imports", "Lean"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_lean_worker_environment(lean_binary),
    )
    try:
        request = canonical_json_bytes(
            {"id": "u05_manifest_probe", "cmd": "load_project", "imports": ["Lean"]}
        )
        assert process.stdin is not None
        process.stdin.write(request)
        process.stdin.flush()
        try:
            response = json.loads(
                _read_worker_line(process, timeout=120.0).decode("utf-8", errors="strict")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductionExecutionDenied("native worker manifest probe returned invalid JSON") from exc
        if type(response) is not dict:
            raise ProductionExecutionDenied("native worker manifest probe response is not an object")
        if response.get("ok") is not True or response.get("id") != "u05_manifest_probe":
            raise ProductionExecutionDenied("native worker manifest probe failed")
        mapped = mapped_modules(process.pid)
        shutdown = canonical_json_bytes({"id": "u05_manifest_shutdown", "cmd": "shutdown"})
        process.stdin.write(shutdown)
        process.stdin.flush()
        _read_worker_line(process, timeout=10.0)
        process.wait(timeout=10.0)
    except BaseException:
        process.kill()
        process.wait(timeout=10.0)
        raise
    return tuple(sorted(mapped, key=lambda path: str(path).casefold()))


def _regular_tree_files(root: Path) -> tuple[Path, ...]:
    root = root.resolve()
    rows: list[Path] = []
    for current_raw, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_raw)
        for name in directory_names:
            directory = current / name
            info = directory.lstat()
            if directory.is_symlink() or getattr(
                info, "st_file_attributes", 0
            ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ProductionExecutionDenied(
                    f"manifest tree contains a symlink/reparse directory: {directory}"
                )
        for name in file_names:
            path = current / name
            info = path.lstat()
            if path.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
            ):
                raise ProductionExecutionDenied(
                    f"manifest tree contains a symlink/reparse file: {path}"
                )
            if not path.is_file():
                raise ProductionExecutionDenied(
                    f"manifest tree entry is not a regular file: {path}"
                )
            rows.append(path.resolve())
    return tuple(rows)


def build_environment_manifest(repo_root: Path) -> Mapping[str, Any]:
    """Build the frozen Windows/compiler/import identity before receipt creation."""

    import site

    repo_root = repo_root.resolve()
    isolated_no_site = sys.flags.isolated == 1 and sys.flags.no_site == 1
    if os.environ.get("PYTHONNOUSERSITE") != "1" or (
        site.ENABLE_USER_SITE is not False and not isolated_no_site
    ):
        raise ProductionExecutionDenied("Python user-site isolation is not active")
    package_root = Path(__file__).resolve().parents[2]
    if package_root != repo_root:
        raise ProductionExecutionDenied("lean_rgc was not imported from the disposable worktree")
    user_site = Path(site.getusersitepackages()).resolve()
    python_prefix = Path(sys.prefix).resolve()
    for raw_entry in sys.path:
        candidate = repo_root if not raw_entry else Path(raw_entry).resolve()
        try:
            candidate.relative_to(user_site)
        except ValueError:
            pass
        else:
            raise ProductionExecutionDenied("Python user-site path remains importable")
        if candidate == repo_root:
            continue
        try:
            candidate.relative_to(python_prefix)
        except ValueError as exc:
            raise ProductionExecutionDenied(
                f"Python import path escapes worktree/runtime prefix: {candidate}"
            ) from exc
    if (repo_root / "lean-toolchain").exists():
        raise ProductionExecutionDenied("repo-root lean-toolchain must be absent by design")
    elan = os.environ.get("UPRIME_U05_ELAN_EXECUTABLE") or shutil.which("elan")
    if elan is None:
        raise ProductionExecutionDenied("elan executable is unavailable")
    which = subprocess.run(
        [elan, "which", "lean"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if which.returncode:
        raise ProductionExecutionDenied("elan could not resolve the executed Lean binary")
    lean_binary = Path(which.stdout.strip()).resolve()
    lean_hash, _lean_size = _stable_file_hash(lean_binary)
    if lean_hash != FROZEN_LIMITS["executed_lean_binary_sha256"]:
        raise ProductionExecutionDenied("executed Lean binary digest changed")
    version_proc = subprocess.run(
        [str(lean_binary), "--version"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    version_line = version_proc.stdout.strip()
    if version_proc.returncode or not version_line.startswith(
        FROZEN_LIMITS["expected_lean_version_prefix"]
    ):
        raise ProductionExecutionDenied("Lean version/build does not match the freeze")

    toolchain = lean_binary.parent.parent.resolve()
    bin_root = (toolchain / "bin").resolve()
    library_root = (toolchain / "lib" / "lean").resolve()
    worker_source = (repo_root / "lean_rgc/native_lean/RGCKernelRPC.lean").resolve()
    if not bin_root.is_dir() or not library_root.is_dir():
        raise ProductionExecutionDenied("resolved Lean toolchain tree is incomplete")
    system_root_value = os.environ.get("SystemRoot")
    if not system_root_value:
        raise ProductionExecutionDenied("SystemRoot is unavailable")
    system_root = Path(system_root_value).resolve()
    system_dir = (system_root / "System32").resolve()
    if not system_dir.is_dir():
        raise ProductionExecutionDenied("canonical Windows System32 directory is absent")

    bin_files = sorted(
        (
            path
            for path in _regular_tree_files(bin_root)
            if path.suffix.casefold() in {".exe", ".dll"}
        ),
        key=lambda path: _normalized_relative(path, toolchain),
    )
    resolution_bin_files = [path for path in bin_files if path.parent == bin_root]
    bin_by_name = {path.name.casefold(): path for path in resolution_bin_files}
    if len(bin_by_name) != len(resolution_bin_files):
        raise ProductionExecutionDenied("toolchain bin has case-folding name collision")

    static_closure: set[Path] = set()
    api_providers: dict[str, Path] = {}
    parsed_pe_digests: dict[Path, str] = {}

    def parse_imports(image: Path) -> tuple[str, ...]:
        names, digest = _pe_import_names_with_digest(image)
        prior = parsed_pe_digests.get(image)
        if prior is not None and prior != digest:
            raise ProductionExecutionDenied(f"PE image changed between parses: {image}")
        parsed_pe_digests[image] = digest
        return names

    def resolve_import(imported: str) -> Path:
        if imported.startswith(("api-ms-win-", "ext-ms-win-")):
            provider = _resolve_api_set_provider(imported, system_root)
            prior = api_providers.get(imported)
            if prior is not None and prior != provider:
                raise ProductionExecutionDenied(
                    f"API-set provider changed during preflight: {imported}"
                )
            api_providers[imported] = provider
            return provider
        toolchain_dep = bin_by_name.get(imported)
        candidate = (system_dir / imported).resolve()
        if toolchain_dep is not None and candidate.is_file():
            raise ProductionExecutionDenied(
                f"PE dependency is ambiguous across toolchain/System32: {imported}"
            )
        if toolchain_dep is not None:
            return toolchain_dep
        if not candidate.is_file():
            raise ProductionExecutionDenied(
                f"PE dependency is absent from toolchain/System32: {imported}"
            )
        return candidate

    queue = [lean_binary]
    while queue:
        image = queue.pop(0)
        if image in static_closure:
            continue
        static_closure.add(image)
        for imported in parse_imports(image):
            queue.append(resolve_import(imported))

    loaded_paths = _probe_worker_loaded_modules(lean_binary, worker_source)
    loaded_set = set(loaded_paths)
    if not static_closure.issubset(loaded_set):
        missing = sorted(str(path) for path in static_closure - loaded_set)
        raise ProductionExecutionDenied(
            f"loaded inventory omits parsed PE closure: {missing}"
        )
    # Dynamic loads are admitted only after their own concrete imports resolve
    # back into the same observed inventory. This closes the parsed/loaded sets.
    for image in loaded_paths:
        for imported in parse_imports(image):
            dependency = resolve_import(imported)
            if dependency not in loaded_set:
                raise ProductionExecutionDenied(
                    f"loaded inventory differs from parsed closure: {image.name}->{imported}"
                )
    closure = loaded_set
    toolchain_closure: set[Path] = set()
    system_dependencies: set[Path] = set()
    for path in closure:
        try:
            path.relative_to(toolchain)
            toolchain_closure.add(path)
            continue
        except ValueError:
            pass
        try:
            path.relative_to(system_root)
            system_dependencies.add(path)
        except ValueError as exc:
            raise ProductionExecutionDenied(
                f"loaded module is outside toolchain/SystemRoot: {path}"
            ) from exc
    api_rows: list[list[str]] = []
    for contract, provider in sorted(api_providers.items()):
        digest, _size = _stable_file_hash(provider)
        api_rows.append(
            [
                contract.casefold(),
                _normalized_relative(provider, system_root),
                digest,
            ]
        )

    runtime_records: list[list[str]] = []
    runtime_payloads: dict[str, Any] = {}
    seen_keys: dict[tuple[str, str, str], tuple[Path, str]] = {}

    def add_file(scope: str, path: Path, root: Path) -> None:
        relative = _normalized_relative(path, root)
        file_type = "pe_exe" if path.suffix.casefold() == ".exe" else "pe_dll"
        key = (scope, relative, file_type)
        digest, _size = _stable_file_hash(path)
        if path in parsed_pe_digests and parsed_pe_digests[path] != digest:
            raise ProductionExecutionDenied(f"PE image changed before manifest hash: {path}")
        prior = seen_keys.get(key)
        if prior is not None:
            prior_path, prior_digest = prior
            if prior_path != path or prior_digest != digest:
                raise ProductionExecutionDenied(
                    f"runtime manifest normalized-key collision: {key}"
                )
            return
        seen_keys[key] = (path, digest)
        runtime_records.append([scope, relative, file_type, digest])

    for path in bin_files:
        add_file("toolchain", path, toolchain)
    for path in sorted(system_dependencies, key=lambda item: str(item).casefold()):
        add_file("windows_system", path, system_root)

    loaded_rows: list[list[str]] = []
    for path in loaded_paths:
        try:
            relative = _normalized_relative(path, toolchain)
            scope = "toolchain"
            root = toolchain
        except ProductionExecutionDenied:
            relative = _normalized_relative(path, system_root)
            scope = "windows_system"
            root = system_root
        digest, _size = _stable_file_hash(path)
        loaded_rows.append([scope, relative, digest])
        if path.suffix.casefold() in {".exe", ".dll"}:
            add_file(scope, path, root)
    loaded_rows.sort(key=_canonical_record_bytes)

    build_payload = _windows_build_payload()
    metadata = (
        ("windows/product_build", build_payload),
        ("windows/api_set_map", api_rows),
        ("windows/loaded_module_inventory", loaded_rows),
    )
    for pseudo_path, payload in metadata:
        payload_bytes = _canonical_record_bytes(payload)
        digest = _sha256_bytes(payload_bytes)
        runtime_records.append(["metadata", pseudo_path, "canonical_json", digest])
        runtime_payloads[pseudo_path] = {"payload": payload, "sha256": digest}

    compiler_runtime_manifest_digest = merkle_sha256(
        "u05-compiler-runtime-manifest-v1", runtime_records
    )
    compiler_build_digest = _sha256_bytes(
        _lp(b"u05-compiler-build-v1")
        + _lp(version_line.encode("utf-8"))
        + _lp(bytes.fromhex(compiler_runtime_manifest_digest))
    )

    dependency_records: list[list[str]] = []
    for path in sorted(_regular_tree_files(library_root), key=lambda item: str(item).casefold()):
        relative = _normalized_relative(path, library_root)
        digest, _size = _stable_file_hash(path)
        suffix = path.suffix.casefold().removeprefix(".") or "no_suffix"
        dependency_records.append([relative, suffix, digest])
    dependency_import_digest = merkle_sha256(
        "u05-dependency-import-v1", dependency_records
    )
    python_runtime_records: list[list[str]] = []
    for path in sorted(
        _regular_tree_files(python_prefix), key=lambda item: str(item).casefold()
    ):
        relative = _normalized_relative(path, python_prefix)
        digest, _size = _stable_file_hash(path)
        suffix = path.suffix.casefold().removeprefix(".") or "no_suffix"
        python_runtime_records.append([relative, suffix, digest])
    python_runtime_digest = merkle_sha256(
        "u05-python-runtime-v1", python_runtime_records
    )
    worker_source_sha256, _worker_size = _stable_file_hash(worker_source)
    environment_content_digest = _sha256_bytes(
        _lp(b"u05-environment-content-v1")
        + _lp(bytes.fromhex(compiler_build_digest))
        + _lp(bytes.fromhex(dependency_import_digest))
        + _lp(bytes.fromhex(worker_source_sha256))
    )
    return {
        "schema": "lean-rgc-uprime-u05-environment-manifest-v1.0",
        "lean_version_line": version_line,
        "lean_binary_sha256": lean_hash,
        "toolchain_bin_file_count": len(bin_files),
        "toolchain_pe_closure": [
            _normalized_relative(path, toolchain)
            for path in sorted(toolchain_closure, key=lambda item: str(item).casefold())
        ],
        "compiler_runtime_records": sorted(runtime_records, key=_canonical_record_bytes),
        "compiler_runtime_payloads": runtime_payloads,
        "compiler_runtime_manifest_digest": compiler_runtime_manifest_digest,
        "compiler_build_digest": compiler_build_digest,
        "dependency_import_file_count": len(dependency_records),
        "dependency_import_digest": dependency_import_digest,
        "worker_source_sha256": worker_source_sha256,
        "environment_content_digest": environment_content_digest,
        "python_executable_sha256": _stable_file_hash(Path(sys.executable).resolve())[0],
        "python_runtime_file_count": len(python_runtime_records),
        "python_runtime_digest": python_runtime_digest,
        "lean_rgc_import_path": str(
            Path(__file__).resolve().parents[1].relative_to(repo_root)
        ).replace("\\", "/"),
    }


def _assert_anchor_snapshot(repo_root: Path) -> tuple[Mapping[str, Any], ...]:
    from lean_rgc.evals.uprime_rpc_litmus import ANCHOR_PATHS

    records: list[Mapping[str, Any]] = []
    for relative in ANCHOR_PATHS:
        path = repo_root / relative
        if not path.is_file() or path.is_symlink():
            raise ProductionExecutionDenied(f"anchored input is absent/nonregular: {relative}")
        head_blob = _git_text(repo_root, "rev-parse", f"HEAD:{relative.as_posix()}")
        worktree_blob = _git_text(repo_root, "hash-object", "--", relative.as_posix())
        if head_blob != worktree_blob:
            raise ProductionExecutionDenied(f"anchored input differs from HEAD: {relative}")
        raw = path.read_bytes()
        records.append(
            {
                "path": relative.as_posix(),
                "git_blob": head_blob,
                "sha256": _sha256_bytes(raw),
                "byte_length": len(raw),
            }
        )
    return tuple(records)


def _runtime_source_snapshot(repo_root: Path) -> Mapping[str, Any]:
    """Bind every tracked package source byte, independent of index filters."""

    if _git_text(repo_root, "rev-parse", "--show-object-format") != "sha1":
        raise ProductionExecutionDenied(
            "runtime source snapshot requires the frozen Git SHA-1 object format"
        )
    tracked_raw = _git(repo_root, "ls-files", "-z", "--", "lean_rgc").stdout
    tracked = tuple(
        sorted(
            row
            for row in tracked_raw.decode("utf-8", errors="strict").split("\0")
            if row
        )
    )
    if not tracked:
        raise ProductionExecutionDenied("runtime source inventory is empty")
    flags = _git_text(repo_root, "ls-files", "-v", "--", "lean_rgc").splitlines()
    if len(flags) != len(tracked) or any(not row.startswith("H ") for row in flags):
        raise ProductionExecutionDenied(
            "runtime sources use assume-unchanged/skip-worktree/index flags"
        )
    tree_raw = _git(repo_root, "ls-tree", "-r", "-z", "HEAD", "--", "lean_rgc").stdout
    tree: dict[str, tuple[str, str]] = {}
    for entry in tree_raw.decode("utf-8", errors="strict").split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, object_type, blob = metadata.split(" ", 2)
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ProductionExecutionDenied(f"runtime source is not a regular blob: {path}")
        tree[path] = (mode, blob)
    if set(tree) != set(tracked):
        raise ProductionExecutionDenied("runtime source index/tree inventories differ")
    records: list[list[Any]] = []
    payload_records: list[Mapping[str, Any]] = []
    for relative in tracked:
        path = repo_root / relative
        digest, size = _stable_file_hash(path)
        raw = path.read_bytes()
        if len(raw) != size or _sha256_bytes(raw) != digest:
            raise ProductionExecutionDenied(
                f"runtime source changed between snapshot reads: {relative}"
            )
        git_blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        mode, expected_blob = tree[relative]
        if git_blob != expected_blob:
            raise ProductionExecutionDenied(
                f"runtime source bytes differ from HEAD despite index status: {relative}"
            )
        records.append([relative, mode, expected_blob, size, digest])
        payload_records.append(
            {
                "path": relative,
                "mode": mode,
                "git_blob": expected_blob,
                "sha256": digest,
                "byte_length": size,
            }
        )
    return {
        "schema": "lean-rgc-uprime-u05-runtime-source-snapshot-v1.0",
        "file_count": len(records),
        "merkle_sha256": merkle_sha256("u05-runtime-source-v1", records),
        "records": payload_records,
    }


def _assert_empty_rerun_registry(repo_root: Path) -> Mapping[str, Any]:
    from lean_rgc.evals.uprime_rerun_license import RERUN_REGISTRY_PATH, load_rerun_registry

    registry_path = repo_root / RERUN_REGISTRY_PATH
    value = load_rerun_registry(registry_path)
    if value.get("entries") != []:
        raise ProductionExecutionDenied("formal rerun registry is not empty")
    return {
        "path": RERUN_REGISTRY_PATH.as_posix(),
        "git_blob": _git_text(repo_root, "rev-parse", f"HEAD:{RERUN_REGISTRY_PATH.as_posix()}"),
        "sha256": _sha256_bytes(registry_path.read_bytes()),
        "entry_count": 0,
    }


def _matrix_marker_path(receipt_path: Path, anchor: str) -> Path:
    return receipt_path.with_name(f"matrix_open_{anchor[:12]}.json")


def build_attempt_receipt(
    repo_root: Path,
    *,
    anchor: str,
    upstream: str,
    workflow_path: str,
    job_name: str,
    accepted_conclusion: str,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
    api: Callable[[str], Mapping[str, Any]] = _gh_api,
    environment_builder: Callable[[Path], Mapping[str, Any]] = build_environment_manifest,
) -> Mapping[str, Any]:
    """Perform every pre-receipt check. This is the sole network-capable actor."""

    repo_root = repo_root.resolve()
    if _git_text(repo_root, "status", "--porcelain=v1"):
        raise ProductionExecutionDenied("disposable candidate worktree is not clean")
    topology = _validate_candidate_topology(repo_root, anchor)
    receipt_path, raw_output_path, artifact_path, marker_path = _validate_frozen_output_paths(
        repo_root,
        anchor=anchor,
        receipt_path=receipt_path,
        raw_output_path=raw_output_path,
        artifact_path=artifact_path,
    )
    paths = (receipt_path, raw_output_path, artifact_path, marker_path)
    if any(_lexists(path) for path in paths):
        raise ProductionExecutionDenied("receipt/raw/artifact/matrix marker already exists")
    ci = verify_ci_control_plane(
        repo_root,
        anchor=anchor,
        upstream=upstream,
        workflow_path=workflow_path,
        job_name=job_name,
        accepted_conclusion=accepted_conclusion,
        api=api,
    )
    environment = environment_builder(repo_root)
    anchors = _assert_anchor_snapshot(repo_root)
    runtime_sources = _runtime_source_snapshot(repo_root)
    rerun_registry = _assert_empty_rerun_registry(repo_root)
    relative_paths = {
        "attempt_receipt": receipt_path.relative_to(repo_root).as_posix(),
        "raw_output": raw_output_path.relative_to(repo_root).as_posix(),
        "artifact": artifact_path.relative_to(repo_root).as_posix(),
        "matrix_open_marker": marker_path.relative_to(repo_root).as_posix(),
    }
    measurement_contract = _measurement_command_environment_contract(
        repo_root=repo_root, anchor=anchor
    )
    attempt_basis = canonical_json_bytes(
        {
            "anchor": anchor,
            "task_matrix_sha256": TASK_MATRIX_SHA256,
            "action_matrix_sha256": ACTION_MATRIX_SHA256,
            "environment_content_digest": environment["environment_content_digest"],
            "environment_manifest_sha256": _sha256_bytes(
                canonical_json_bytes(environment)
            ),
        }
    )
    return {
        "schema": ATTEMPT_RECEIPT_SCHEMA,
        "attempt_id": _sha256_bytes(attempt_basis),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": anchor,
        "plan_commit": PLAN_COMMIT,
        "plan_blob": PLAN_BLOB,
        "task_matrix_sha256": TASK_MATRIX_SHA256,
        "action_matrix_sha256": ACTION_MATRIX_SHA256,
        "frozen_limits": dict(FROZEN_LIMITS),
        "topology": topology,
        "ci_control_plane": ci,
        "environment": environment,
        "anchor_snapshot": list(anchors),
        "runtime_source_snapshot": runtime_sources,
        "rerun_registry": rerun_registry,
        "paths": relative_paths,
        "command_contract": {
            "module": "lean_rgc.evals.uprime_u05_kill_probes",
            "outer_network_actor": "pre_receipt_only",
            "measurement_child_network": "denied",
            "python_executable": str(Path(sys.executable).resolve()),
            "repo_root": ".",
            "measurement_argv": [
                str(Path(sys.executable).resolve()),
                "-I",
                "-S",
                "-c",
                MEASUREMENT_BOOTSTRAP,
                "--measurement-child",
                "--repo-root",
                ".",
                "--anchor",
                anchor,
                "--attempt-receipt",
                relative_paths["attempt_receipt"],
                "--raw-output",
                relative_paths["raw_output"],
                "--artifact",
                relative_paths["artifact"],
            ],
            "measurement_environment_keys": sorted(MEASUREMENT_ENV_KEYS),
            "receipt_sha256_environment_binding": "UPRIME_U05_RECEIPT_SHA256",
            "measurement_bootstrap_sha256": _sha256_bytes(
                MEASUREMENT_BOOTSTRAP.encode("utf-8")
            ),
            "isolated_home": (
                f"runs/uprime_u05_20260711/isolated_home_{anchor[:12]}"
            ),
            **measurement_contract,
        },
    }


def _exact_mapping_fields(
    value: Any, expected: set[str], where: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        actual = sorted(value) if type(value) is dict else type(value).__name__
        raise ProductionExecutionDenied(
            f"{where} fields differ; expected={sorted(expected)}, actual={actual}"
        )
    return value


def _validate_environment_manifest_value(environment: Mapping[str, Any]) -> None:
    records = environment["compiler_runtime_records"]
    if type(records) is not list or not records:
        raise ProductionExecutionDenied("environment runtime records are malformed")
    if any(
        type(row) is not list
        or len(row) != 4
        or any(type(item) is not str for item in row)
        or re.fullmatch(r"[0-9A-F]{64}", row[3]) is None
        or (
            row[0] == "metadata"
            and (
                row[1]
                not in {
                    "windows/product_build",
                    "windows/api_set_map",
                    "windows/loaded_module_inventory",
                }
                or row[2] != "canonical_json"
            )
        )
        or (
            row[0] != "metadata"
            and (
                row[0] not in {"toolchain", "windows_system"}
                or row[2] not in {"pe_exe", "pe_dll"}
                or not row[1]
            )
        )
        for row in records
    ):
        raise ProductionExecutionDenied("environment runtime record shape changed")
    if records != sorted(records, key=_canonical_record_bytes):
        raise ProductionExecutionDenied("environment runtime records are not canonical")
    runtime_digest = merkle_sha256("u05-compiler-runtime-manifest-v1", records)
    if runtime_digest != environment["compiler_runtime_manifest_digest"]:
        raise ProductionExecutionDenied("environment runtime Merkle root is inconsistent")
    payloads = _exact_mapping_fields(
        environment["compiler_runtime_payloads"],
        {
            "windows/product_build",
            "windows/api_set_map",
            "windows/loaded_module_inventory",
        },
        "environment runtime payloads",
    )
    runtime_metadata = {
        (row[0], row[1], row[2]): row[3]
        for row in records
        if row[0] == "metadata"
    }
    build_payload = payloads["windows/product_build"]
    api_payload = payloads["windows/api_set_map"]
    loaded_payload = payloads["windows/loaded_module_inventory"]
    for named_payload, expected_length in ((build_payload, 6),):
        payload_value = named_payload.get("payload") if type(named_payload) is dict else None
        if (
            type(payload_value) is not list
            or len(payload_value) != expected_length
            or any(type(item) is not str for item in payload_value)
        ):
            raise ProductionExecutionDenied("Windows build payload shape changed")
    for label, named_payload in (
        ("API-set", api_payload),
        ("loaded-module", loaded_payload),
    ):
        payload_value = named_payload.get("payload") if type(named_payload) is dict else None
        if (
            type(payload_value) is not list
            or not payload_value
            or any(
                type(row) is not list
                or len(row) != 3
                or any(type(item) is not str for item in row)
                or re.fullmatch(r"[0-9A-F]{64}", row[2]) is None
                for row in payload_value
            )
            or payload_value != sorted(payload_value, key=_canonical_record_bytes)
            or len({_canonical_record_bytes(row) for row in payload_value})
            != len(payload_value)
        ):
            raise ProductionExecutionDenied(f"{label} payload shape/order changed")
    for pseudo_path, raw_payload in payloads.items():
        payload = _exact_mapping_fields(
            raw_payload, {"payload", "sha256"}, f"environment payload {pseudo_path}"
        )
        digest = _sha256_bytes(_canonical_record_bytes(payload["payload"]))
        if payload["sha256"] != digest or runtime_metadata.get(
            ("metadata", pseudo_path, "canonical_json")
        ) != digest:
            raise ProductionExecutionDenied(
                f"environment metadata payload is inconsistent: {pseudo_path}"
            )
    compiler_build = _sha256_bytes(
        _lp(b"u05-compiler-build-v1")
        + _lp(environment["lean_version_line"].encode("utf-8"))
        + _lp(bytes.fromhex(runtime_digest))
    )
    if compiler_build != environment["compiler_build_digest"]:
        raise ProductionExecutionDenied("environment compiler-build digest is inconsistent")
    content_digest = _sha256_bytes(
        _lp(b"u05-environment-content-v1")
        + _lp(bytes.fromhex(compiler_build))
        + _lp(bytes.fromhex(environment["dependency_import_digest"]))
        + _lp(bytes.fromhex(environment["worker_source_sha256"]))
    )
    if content_digest != environment["environment_content_digest"]:
        raise ProductionExecutionDenied("environment content digest is inconsistent")
    if (
        type(environment["toolchain_bin_file_count"]) is not int
        or environment["toolchain_bin_file_count"] < 1
        or type(environment["dependency_import_file_count"]) is not int
        or environment["dependency_import_file_count"] < 1
        or type(environment["python_runtime_file_count"]) is not int
        or environment["python_runtime_file_count"] < 1
        or type(environment["toolchain_pe_closure"]) is not list
        or not environment["toolchain_pe_closure"]
        or any(
            type(item) is not str or not item
            for item in environment["toolchain_pe_closure"]
        )
        or len(set(environment["toolchain_pe_closure"]))
        != len(environment["toolchain_pe_closure"])
        or type(environment["lean_version_line"]) is not str
        or not environment["lean_version_line"].startswith(
            FROZEN_LIMITS["expected_lean_version_prefix"]
        )
        or environment["lean_binary_sha256"]
        != FROZEN_LIMITS["executed_lean_binary_sha256"]
        or environment["python_executable_sha256"]
        != _stable_file_hash(Path(sys.executable).resolve())[0]
        or environment["lean_rgc_import_path"] != "lean_rgc"
    ):
        raise ProductionExecutionDenied("environment manifest invariants changed")


def _validate_attempt_receipt_value(
    receipt: Mapping[str, Any], *, repo_root: Path, receipt_path: Path
) -> None:
    top = _exact_mapping_fields(
        receipt,
        {
            "schema",
            "attempt_id",
            "created_at_utc",
            "candidate",
            "plan_commit",
            "plan_blob",
            "task_matrix_sha256",
            "action_matrix_sha256",
            "frozen_limits",
            "topology",
            "ci_control_plane",
            "environment",
            "anchor_snapshot",
            "runtime_source_snapshot",
            "rerun_registry",
            "paths",
            "command_contract",
        },
        "attempt receipt",
    )
    candidate = top.get("candidate")
    if type(candidate) is not str or re.fullmatch(r"[0-9a-f]{40}", candidate) is None:
        raise ProductionExecutionDenied("receipt candidate is malformed")
    if (
        top.get("schema") != ATTEMPT_RECEIPT_SCHEMA
        or top.get("plan_commit") != PLAN_COMMIT
        or top.get("plan_blob") != PLAN_BLOB
        or top.get("task_matrix_sha256") != TASK_MATRIX_SHA256
        or top.get("action_matrix_sha256") != ACTION_MATRIX_SHA256
        or top.get("frozen_limits") != dict(FROZEN_LIMITS)
    ):
        raise ProductionExecutionDenied("receipt frozen constants changed")
    try:
        datetime.fromisoformat(str(top["created_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductionExecutionDenied("receipt timestamp is malformed") from exc
    environment = _exact_mapping_fields(
        top["environment"],
        {
            "schema",
            "lean_version_line",
            "lean_binary_sha256",
            "toolchain_bin_file_count",
            "toolchain_pe_closure",
            "compiler_runtime_records",
            "compiler_runtime_payloads",
            "compiler_runtime_manifest_digest",
            "compiler_build_digest",
            "dependency_import_file_count",
            "dependency_import_digest",
            "worker_source_sha256",
            "environment_content_digest",
            "python_executable_sha256",
            "python_runtime_file_count",
            "python_runtime_digest",
            "lean_rgc_import_path",
        },
        "receipt environment",
    )
    if environment["schema"] != "lean-rgc-uprime-u05-environment-manifest-v1.0":
        raise ProductionExecutionDenied("receipt environment schema changed")
    for field_name in (
        "lean_binary_sha256",
        "compiler_runtime_manifest_digest",
        "compiler_build_digest",
        "dependency_import_digest",
        "worker_source_sha256",
        "environment_content_digest",
        "python_executable_sha256",
        "python_runtime_digest",
    ):
        value = environment[field_name]
        if type(value) is not str or re.fullmatch(r"[0-9A-F]{64}", value) is None:
            raise ProductionExecutionDenied(f"receipt environment {field_name} is malformed")
    _validate_environment_manifest_value(environment)
    expected_attempt_id = _sha256_bytes(
        canonical_json_bytes(
            {
                "anchor": candidate,
                "task_matrix_sha256": TASK_MATRIX_SHA256,
                "action_matrix_sha256": ACTION_MATRIX_SHA256,
                "environment_content_digest": environment["environment_content_digest"],
                "environment_manifest_sha256": _sha256_bytes(
                    canonical_json_bytes(environment)
                ),
            }
        )
    )
    if top.get("attempt_id") != expected_attempt_id:
        raise ProductionExecutionDenied("receipt attempt ID does not bind its contents")
    paths = _exact_mapping_fields(
        top["paths"],
        {"attempt_receipt", "raw_output", "artifact", "matrix_open_marker"},
        "receipt paths",
    )
    resolved = _validate_frozen_output_paths(
        repo_root,
        anchor=candidate,
        receipt_path=_ensure_repo_relative(repo_root, paths["attempt_receipt"]),
        raw_output_path=_ensure_repo_relative(repo_root, paths["raw_output"]),
        artifact_path=_ensure_repo_relative(repo_root, paths["artifact"]),
    )
    if resolved[0] != receipt_path.resolve() or resolved[3] != _ensure_repo_relative(
        repo_root, paths["matrix_open_marker"]
    ):
        raise ProductionExecutionDenied("receipt paths do not bind the supplied receipt")
    topology = top["topology"]
    if topology != _validate_candidate_topology(repo_root, candidate):
        raise ProductionExecutionDenied("receipt topology differs from the candidate")
    ci = _exact_mapping_fields(
        top["ci_control_plane"],
        {
            "provider",
            "origin_repository",
            "branch_ref",
            "upstream_ref",
            "workflow_path",
            "workflow_name",
            "workflow_blob",
            "run_id",
            "job_id",
            "head_sha",
            "event",
            "conclusion",
        },
        "receipt CI control plane",
    )
    if (
        ci["provider"] != "github_actions_read_only_gh_api"
        or ci["branch_ref"] != BRANCH_REF
        or ci["upstream_ref"] != UPSTREAM_REF
        or ci["workflow_path"] != CI_WORKFLOW_PATH
        or ci["workflow_name"] != CI_WORKFLOW_NAME
        or ci["head_sha"] != candidate
        or ci["event"] != "push"
        or ci["conclusion"] != CI_ACCEPTED_CONCLUSION
        or ci["workflow_blob"]
        != _git_text(repo_root, "rev-parse", f"HEAD:{CI_WORKFLOW_PATH}")
        or type(ci["run_id"]) is not int
        or type(ci["job_id"]) is not int
    ):
        raise ProductionExecutionDenied("receipt CI evidence is malformed")
    command = _exact_mapping_fields(
        top["command_contract"],
        {
            "module",
            "outer_network_actor",
            "measurement_child_network",
            "python_executable",
            "repo_root",
            "measurement_argv",
            "measurement_environment_keys",
            "receipt_sha256_environment_binding",
            "measurement_bootstrap_sha256",
            "isolated_home",
            "measurement_environment",
            "tool_executables",
            "lean_worker_environment",
        },
        "receipt command contract",
    )
    expected_argv = [
        str(Path(sys.executable).resolve()),
        "-I",
        "-S",
        "-c",
        MEASUREMENT_BOOTSTRAP,
        "--measurement-child",
        "--repo-root",
        ".",
        "--anchor",
        candidate,
        "--attempt-receipt",
        paths["attempt_receipt"],
        "--raw-output",
        paths["raw_output"],
        "--artifact",
        paths["artifact"],
    ]
    expected_measurement_contract = _measurement_command_environment_contract(
        repo_root=repo_root, anchor=candidate
    )
    if (
        command["module"] != "lean_rgc.evals.uprime_u05_kill_probes"
        or command["outer_network_actor"] != "pre_receipt_only"
        or command["measurement_child_network"] != "denied"
        or command["python_executable"] != str(Path(sys.executable).resolve())
        or command["repo_root"] != "."
        or command["measurement_argv"] != expected_argv
        or command["measurement_environment_keys"] != sorted(MEASUREMENT_ENV_KEYS)
        or command["receipt_sha256_environment_binding"]
        != "UPRIME_U05_RECEIPT_SHA256"
        or command["measurement_bootstrap_sha256"]
        != _sha256_bytes(MEASUREMENT_BOOTSTRAP.encode("utf-8"))
        or command["isolated_home"]
        != f"runs/uprime_u05_20260711/isolated_home_{candidate[:12]}"
        or command["measurement_environment"]
        != expected_measurement_contract["measurement_environment"]
        or command["tool_executables"]
        != expected_measurement_contract["tool_executables"]
        or command["lean_worker_environment"]
        != expected_measurement_contract["lean_worker_environment"]
    ):
        raise ProductionExecutionDenied("receipt command contract changed")
    if top["runtime_source_snapshot"] != _runtime_source_snapshot(repo_root):
        raise ProductionExecutionDenied("receipt runtime source snapshot changed")
    if type(top["anchor_snapshot"]) is not list or type(top["rerun_registry"]) is not dict:
        raise ProductionExecutionDenied("receipt anchor/rerun evidence is malformed")


def _evidence_bytes(path: Path) -> tuple[Mapping[str, Any], bytes | None]:
    if not _lexists(path):
        return (
            {
                "present": False,
                "byte_length": 0,
                "sha256": None,
                "bytes_base64": None,
                "read_error_class": None,
                "read_error_message": None,
            },
            None,
        )
    try:
        before = path.lstat()
        attributes = getattr(before, "st_file_attributes", 0)
        if path.is_symlink() or attributes & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ProductionExecutionDenied(
                f"evidence path is a symlink/reparse point: {path}"
            )
        if not path.is_file():
            raise ProductionExecutionDenied(
                f"evidence path is not a regular file: {path}"
            )
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ProductionExecutionDenied(f"evidence file changed while reading: {path}")
        return (
            {
                "present": True,
                "byte_length": len(raw),
                "sha256": _sha256_bytes(raw),
                "bytes_base64": base64.b64encode(raw).decode("ascii"),
                "read_error_class": None,
                "read_error_message": None,
            },
            raw,
        )
    except BaseException as exc:
        return (
            {
                "present": True,
                "byte_length": 0,
                "sha256": None,
                "bytes_base64": None,
                "read_error_class": type(exc).__name__,
                "read_error_message": str(exc),
            },
            None,
        )


def _receipt_repo_root(receipt_path: Path, receipt: Mapping[str, Any]) -> Path:
    paths = receipt.get("paths")
    if type(paths) is not dict or type(paths.get("attempt_receipt")) is not str:
        raise ProductionExecutionDenied("receipt path object is malformed")
    relative = Path(paths["attempt_receipt"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ProductionExecutionDenied("receipt contains an unsafe receipt path")
    root = receipt_path.resolve()
    for _part in relative.parts:
        root = root.parent
    if (root / relative).resolve() != receipt_path.resolve():
        raise ProductionExecutionDenied("receipt path does not bind its repository root")
    return root


def _valid_matrix_marker(
    raw: bytes | None, *, receipt: Mapping[str, Any], receipt_raw: bytes
) -> bool:
    if raw is None:
        return False
    try:
        marker = _parse_canonical_json(raw, schema=MATRIX_OPEN_SCHEMA)
        _exact_mapping_fields(
            marker,
            {
                "schema",
                "opened_at_utc",
                "candidate",
                "attempt_id",
                "receipt_sha256",
                "task_matrix_sha256",
                "action_matrix_sha256",
                "look_consumed",
            },
            "matrix-open marker",
        )
        datetime.fromisoformat(str(marker["opened_at_utc"]).replace("Z", "+00:00"))
        return bool(
            marker["candidate"] == receipt["candidate"]
            and marker["attempt_id"] == receipt["attempt_id"]
            and marker["receipt_sha256"] == _sha256_bytes(receipt_raw)
            and marker["task_matrix_sha256"] == TASK_MATRIX_SHA256
            and marker["action_matrix_sha256"] == ACTION_MATRIX_SHA256
            and marker["look_consumed"] is True
        )
    except (ProductionExecutionDenied, ValueError, KeyError, TypeError):
        return False


def _payload_int(value: Any, where: str) -> int:
    if type(value) is not int or value < 0:
        raise ProductionExecutionDenied(f"{where} is not a nonnegative integer")
    return value


def _payload_float(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProductionExecutionDenied(f"{where} is not a finite number")
    return float(value)


def _payload_fraction(value: Any, where: str, *, optional: bool = False) -> Fraction | None:
    if optional and value is None:
        return None
    obj = _exact_mapping_fields(
        value, {"numerator", "denominator", "decimal"}, where
    )
    numerator = obj["numerator"]
    denominator = obj["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise ProductionExecutionDenied(f"{where} has invalid exact fraction fields")
    result = Fraction(numerator, denominator)
    if _payload_float(obj["decimal"], f"{where}.decimal") != float(result):
        raise ProductionExecutionDenied(f"{where} decimal disagrees with exact fraction")
    return result


def _decode_probe_report(value: Any) -> KillProbeReport:
    probe = _exact_mapping_fields(
        value,
        {
            "schema",
            "kp1",
            "kp2",
            "kp3",
            "capability_matrix",
            "licenses_k1_k4",
            "licenses_u2_u5_claims",
            "licenses_wp4_wp12_implementation",
            "licenses_gpu",
            "licenses_canonical_rpc_rerun",
            "licenses_reserved_data_read",
        },
        "raw probe report",
    )
    if probe["schema"] != RAW_RESULT_SCHEMA or any(
        probe[name] is not False for name in probe if name.startswith("licenses_")
    ):
        raise ProductionExecutionDenied("probe schema/licenses changed")
    kp1_raw = _exact_mapping_fields(
        probe["kp1"],
        {
            "disposition",
            "cutoffs",
            "nontrivial_identity_classes",
            "nontrivial_class_task_ids",
            "blocked_reason",
        },
        "KP1",
    )
    if kp1_raw["disposition"] not in {
        "U05_KP1_SCALE_READY",
        "U05_KP1_EXISTENCE_ONLY",
        "U05_KP1_OBSERVATION_ALIAS_ONLY",
        "U05_KP1_NO_IDENTITY_COMPRESSION",
        "U05_KP1_INCONCLUSIVE",
    } or kp1_raw["blocked_reason"] is not None:
        raise ProductionExecutionDenied("KP1 complete disposition/reason is invalid")
    kp1_rows_raw = kp1_raw["cutoffs"]
    if type(kp1_rows_raw) is not list or len(kp1_rows_raw) != 3:
        raise ProductionExecutionDenied("KP1 cutoffs are incomplete")
    kp1_rows = []
    for expected_cutoff, raw_row in enumerate(kp1_rows_raw, 1):
        row = _exact_mapping_fields(
            raw_row,
            {
                "cutoff",
                "n_occ_open",
                "n_id_open",
                "c_id_open",
                "n_obs_open",
                "c_obs_open",
                "p_raw_open",
                "first_entry_closed",
                "derived_closed",
                "first_entry_sink",
                "derived_sink",
                "censored",
            },
            "KP1 cutoff",
        )
        if row["cutoff"] != expected_cutoff:
            raise ProductionExecutionDenied("KP1 cutoff order changed")
        decoded_row = KP1CutoffReport(
                cutoff=expected_cutoff,
                n_occ_open=_payload_int(row["n_occ_open"], "KP1 n_occ_open"),
                n_id_open=_payload_int(row["n_id_open"], "KP1 n_id_open"),
                c_id_open=_payload_fraction(row["c_id_open"], "KP1 c_id", optional=True),
                n_obs_open=_payload_int(row["n_obs_open"], "KP1 n_obs_open"),
                c_obs_open=_payload_fraction(row["c_obs_open"], "KP1 c_obs", optional=True),
                p_raw_open=_payload_fraction(row["p_raw_open"], "KP1 p_raw", optional=True),
                first_entry_closed=_payload_int(row["first_entry_closed"], "KP1 closed"),
                derived_closed=_payload_int(row["derived_closed"], "KP1 derived closed"),
                first_entry_sink=_payload_int(row["first_entry_sink"], "KP1 sink"),
                derived_sink=_payload_int(row["derived_sink"], "KP1 derived sink"),
                censored=_payload_int(row["censored"], "KP1 censored"),
        )
        expected_occurrences = 5 * sum(12**depth for depth in range(1, expected_cutoff + 1))
        classified = (
            decoded_row.n_occ_open
            + decoded_row.first_entry_closed
            + decoded_row.derived_closed
            + decoded_row.first_entry_sink
            + decoded_row.derived_sink
            + decoded_row.censored
        )
        if (
            classified != expected_occurrences
            or decoded_row.n_id_open > decoded_row.n_occ_open
            or decoded_row.n_obs_open > decoded_row.n_id_open
            or decoded_row.c_id_open
            != (
                Fraction(decoded_row.n_occ_open, decoded_row.n_id_open)
                if decoded_row.n_id_open
                else None
            )
            or decoded_row.c_obs_open
            != (
                Fraction(decoded_row.n_occ_open, decoded_row.n_obs_open)
                if decoded_row.n_obs_open
                else None
            )
            or (
                decoded_row.p_raw_open is not None
                and not (Fraction(0) <= decoded_row.p_raw_open <= Fraction(1))
            )
        ):
            raise ProductionExecutionDenied("KP1 cutoff arithmetic is inconsistent")
        kp1_rows.append(decoded_row)
    if any(
        any(right < left for left, right in zip(left_row, right_row))
        for left_row, right_row in zip(
            (
                (
                    row.n_occ_open,
                    row.first_entry_closed,
                    row.derived_closed,
                    row.first_entry_sink,
                    row.derived_sink,
                    row.censored,
                )
                for row in kp1_rows
            ),
            (
                (
                    row.n_occ_open,
                    row.first_entry_closed,
                    row.derived_closed,
                    row.first_entry_sink,
                    row.derived_sink,
                    row.censored,
                )
                for row in kp1_rows[1:]
            ),
        )
    ):
        raise ProductionExecutionDenied("KP1 cumulative counts are not monotone")
    if any(
        right.n_id_open < left.n_id_open
        or right.n_obs_open < left.n_obs_open
        for left, right in zip(kp1_rows, kp1_rows[1:])
    ):
        raise ProductionExecutionDenied("KP1 quotient counts are not monotone")
    if any(
        (row.p_raw_open is None) != (row.n_occ_open == row.n_id_open)
        for row in kp1_rows
    ):
        raise ProductionExecutionDenied("KP1 response-pair denominator is inconsistent")
    for label, first_field, derived_field in (
        ("closed", "first_entry_closed", "derived_closed"),
        ("sink", "first_entry_sink", "derived_sink"),
    ):
        previous_first = previous_derived = 0
        previous_first_delta = previous_derived_delta = 0
        for index, row in enumerate(kp1_rows):
            first = getattr(row, first_field)
            derived = getattr(row, derived_field)
            first_delta = first - previous_first
            derived_delta = derived - previous_derived
            expected_derived_delta = (
                0
                if index == 0
                else 12 * (previous_first_delta + previous_derived_delta)
            )
            if derived_delta != expected_derived_delta:
                raise ProductionExecutionDenied(
                    f"KP1 {label} terminal-extension recurrence is inconsistent"
                )
            previous_first = first
            previous_derived = derived
            previous_first_delta = first_delta
            previous_derived_delta = derived_delta
    class_tasks = kp1_raw["nontrivial_class_task_ids"]
    if (
        type(class_tasks) is not list
        or any(type(item) is not str or item not in PRODUCTION_TASK_IDS for item in class_tasks)
        or class_tasks != sorted(set(class_tasks))
    ):
        raise ProductionExecutionDenied("KP1 class task IDs are invalid")
    kp1 = KP1Report(
        disposition=kp1_raw["disposition"],
        cutoffs=tuple(kp1_rows),
        nontrivial_identity_classes=_payload_int(
            kp1_raw["nontrivial_identity_classes"], "KP1 class count"
        ),
        nontrivial_class_task_ids=tuple(class_tasks),
    )
    if (
        any(row.p_raw_open not in (None, Fraction(0)) for row in kp1.cutoffs)
        or any(row.censored != 0 for row in kp1.cutoffs)
        or kp1.nontrivial_identity_classes > kp1.cutoffs[-1].n_id_open
        or kp1.nontrivial_identity_classes
        > kp1.cutoffs[-1].n_occ_open - kp1.cutoffs[-1].n_id_open
        or (kp1.nontrivial_identity_classes == 0) != (len(class_tasks) == 0)
    ):
        raise ProductionExecutionDenied("KP1 class/response evidence is inconsistent")
    last_kp1 = kp1.cutoffs[-1]
    if any(row.c_id_open is None or row.c_obs_open is None for row in kp1.cutoffs):
        expected_kp1_disposition = "U05_KP1_INCONCLUSIVE"
    elif (
        kp1.nontrivial_identity_classes >= 2
        and len(class_tasks) >= 2
        and last_kp1.c_id_open is not None
        and last_kp1.c_id_open >= Fraction(11, 10)
    ):
        expected_kp1_disposition = "U05_KP1_SCALE_READY"
    elif kp1.nontrivial_identity_classes:
        expected_kp1_disposition = "U05_KP1_EXISTENCE_ONLY"
    elif any(row.n_obs_open < row.n_id_open for row in kp1.cutoffs):
        expected_kp1_disposition = "U05_KP1_OBSERVATION_ALIAS_ONLY"
    elif all(
        row.n_occ_open > 0
        and row.n_occ_open == row.n_id_open == row.n_obs_open
        for row in kp1.cutoffs
    ):
        expected_kp1_disposition = "U05_KP1_NO_IDENTITY_COMPRESSION"
    else:
        expected_kp1_disposition = "U05_KP1_INCONCLUSIVE"
    if kp1.disposition != expected_kp1_disposition:
        raise ProductionExecutionDenied("KP1 disposition disagrees with its evidence")
    kp2_raw = _exact_mapping_fields(
        probe["kp2"],
        {
            "disposition",
            "successful_trajectories",
            "eligible_open_steps",
            "eligible_open_blocks",
            "contractive_blocks",
            "eligible_open_blocks_by_length",
            "contractive_blocks_by_length",
            "terminal_close_steps",
            "one_step_noncontractive_fraction",
            "coordinate_increase_fractions",
            "longest_noncontractive_run",
            "blocked_reason",
        },
        "KP2",
    )
    if kp2_raw["disposition"] not in {
        "U05_KP2_EVENTUAL_WINDOW",
        "U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT",
        "U05_KP2_FRAGMENT_INCONCLUSIVE",
    } or kp2_raw["blocked_reason"] is not None:
        raise ProductionExecutionDenied("KP2 complete disposition/reason is invalid")
    eligible_by_length = kp2_raw["eligible_open_blocks_by_length"]
    contractive_by_length = kp2_raw["contractive_blocks_by_length"]
    coordinates = kp2_raw["coordinate_increase_fractions"]
    if any(type(row) is not list for row in (eligible_by_length, contractive_by_length, coordinates)):
        raise ProductionExecutionDenied("KP2 vector fields are malformed")
    if len(eligible_by_length) != 3 or len(contractive_by_length) != 3 or len(coordinates) != 5:
        raise ProductionExecutionDenied("KP2 vector lengths changed")
    kp2 = KP2Report(
        disposition=kp2_raw["disposition"],
        successful_trajectories=_payload_int(kp2_raw["successful_trajectories"], "KP2 paths"),
        eligible_open_steps=_payload_int(kp2_raw["eligible_open_steps"], "KP2 steps"),
        eligible_open_blocks=_payload_int(kp2_raw["eligible_open_blocks"], "KP2 blocks"),
        contractive_blocks=_payload_int(kp2_raw["contractive_blocks"], "KP2 contractive"),
        eligible_open_blocks_by_length=tuple(
            _payload_int(item, "KP2 eligible length") for item in eligible_by_length
        ),
        contractive_blocks_by_length=tuple(
            _payload_int(item, "KP2 contractive length") for item in contractive_by_length
        ),
        terminal_close_steps=_payload_int(kp2_raw["terminal_close_steps"], "KP2 closes"),
        one_step_noncontractive_fraction=_payload_fraction(
            kp2_raw["one_step_noncontractive_fraction"], "KP2 one-step", optional=True
        ),
        coordinate_increase_fractions=tuple(
            _payload_fraction(item, "KP2 coordinate", optional=True) for item in coordinates
        ),
        longest_noncontractive_run=_payload_int(
            kp2_raw["longest_noncontractive_run"], "KP2 longest run"
        ),
    )
    if (
        kp2.eligible_open_steps != kp2.eligible_open_blocks_by_length[0]
        or kp2.eligible_open_blocks != sum(kp2.eligible_open_blocks_by_length)
        or kp2.contractive_blocks != sum(kp2.contractive_blocks_by_length)
        or any(
            contractive > eligible
            for contractive, eligible in zip(
                kp2.contractive_blocks_by_length,
                kp2.eligible_open_blocks_by_length,
            )
        )
        or kp2.contractive_blocks > kp2.eligible_open_blocks
        or kp2.terminal_close_steps != kp2.successful_trajectories
        or kp2.eligible_open_steps > 2 * kp2.successful_trajectories
        or kp2.eligible_open_blocks_by_length[1] > kp2.successful_trajectories
        or kp2.eligible_open_blocks_by_length[1] > kp2.eligible_open_steps
        or kp2.eligible_open_blocks_by_length[2] != 0
        or kp2.longest_noncontractive_run > min(2, kp2.eligible_open_steps)
    ):
        raise ProductionExecutionDenied("KP2 counts are inconsistent")
    kp2_fractions = (
        kp2.one_step_noncontractive_fraction,
        *kp2.coordinate_increase_fractions,
    )
    if kp2.eligible_open_steps == 0:
        if any(item is not None for item in kp2_fractions):
            raise ProductionExecutionDenied("KP2 empty edge set has fractions")
    elif any(
        item is None
        or not (Fraction(0) <= item <= Fraction(1))
        or kp2.eligible_open_steps % item.denominator != 0
        for item in kp2_fractions
    ):
        raise ProductionExecutionDenied("KP2 edge fractions are inconsistent")
    else:
        expected_noncontractive = Fraction(
            kp2.eligible_open_steps - kp2.contractive_blocks_by_length[0],
            kp2.eligible_open_steps,
        )
        if kp2.one_step_noncontractive_fraction != expected_noncontractive:
            raise ProductionExecutionDenied(
                "KP2 one-step fraction disagrees with contractive edge counts"
            )
        noncontractive_edges = (
            expected_noncontractive.numerator
            * kp2.eligible_open_steps
            // expected_noncontractive.denominator
        )
        if kp2.longest_noncontractive_run > noncontractive_edges:
            raise ProductionExecutionDenied(
                "KP2 longest run exceeds the noncontractive edge count"
            )
        coordinate_increases = tuple(
            item.numerator * kp2.eligible_open_steps // item.denominator
            for item in kp2.coordinate_increase_fractions
            if item is not None
        )
        if any(count > noncontractive_edges for count in coordinate_increases):
            raise ProductionExecutionDenied(
                "KP2 coordinate increases exceed noncontractive edges"
            )
        if (noncontractive_edges > 0) != (kp2.longest_noncontractive_run > 0):
            raise ProductionExecutionDenied(
                "KP2 noncontractive count/run existence disagrees"
            )
    if kp2.successful_trajectories and kp2.contractive_blocks:
        expected_kp2_disposition = "U05_KP2_EVENTUAL_WINDOW"
    elif kp2.eligible_open_blocks and kp2.contractive_blocks == 0:
        expected_kp2_disposition = "U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT"
    else:
        expected_kp2_disposition = "U05_KP2_FRAGMENT_INCONCLUSIVE"
    if kp2.disposition != expected_kp2_disposition:
        raise ProductionExecutionDenied("KP2 disposition disagrees with its evidence")
    kp3_raw = _exact_mapping_fields(
        probe["kp3"], {"disposition", "cutoffs", "blocked_reason"}, "KP3"
    )
    if kp3_raw["disposition"] not in {
        "U05_KP3_PLATEAU_AT_D3",
        "U05_KP3_NO_LOW_RANK_WINDOW_ON_FROZEN_FAMILY",
        "U05_KP3_INCONCLUSIVE",
    } or kp3_raw["blocked_reason"] is not None:
        raise ProductionExecutionDenied("KP3 complete disposition/reason is invalid")
    kp3_rows_raw = kp3_raw["cutoffs"]
    if type(kp3_rows_raw) is not list or len(kp3_rows_raw) != 3:
        raise ProductionExecutionDenied("KP3 cutoffs are incomplete")
    kp3_rows = []
    for expected_cutoff, raw_row in enumerate(kp3_rows_raw, 1):
        row = _exact_mapping_fields(
            raw_row,
            {
                "cutoff",
                "rank",
                "n_rows",
                "n_suffixes",
                "n_columns",
                "n_cells",
                "incremental_rank",
                "singular_values",
                "inverse_condition_ratio",
                "non_sink_prefix_coverage",
                "non_sink_suffix_coverage",
                "per_channel_scales",
            },
            "KP3 cutoff",
        )
        singular = row["singular_values"]
        scales = row["per_channel_scales"]
        expected_rows, expected_suffixes, expected_columns, expected_cells = hankel_dimensions(
            n_tasks=5, n_actions=12, cutoff=expected_cutoff
        )
        if (
            row["cutoff"] != expected_cutoff
            or type(singular) is not list
            or type(scales) is not list
            or len(scales) != 7
            or len(singular) != min(expected_rows, expected_columns)
        ):
            raise ProductionExecutionDenied("KP3 cutoff/vector shape changed")
        decoded_row = HankelCutoffReport(
                cutoff=expected_cutoff,
                rank=_payload_int(row["rank"], "KP3 rank"),
                n_rows=_payload_int(row["n_rows"], "KP3 rows"),
                n_suffixes=_payload_int(row["n_suffixes"], "KP3 suffixes"),
                n_columns=_payload_int(row["n_columns"], "KP3 columns"),
                n_cells=_payload_int(row["n_cells"], "KP3 cells"),
                incremental_rank=_payload_int(row["incremental_rank"], "KP3 rank increment"),
                singular_values=tuple(_payload_float(item, "KP3 singular") for item in singular),
                inverse_condition_ratio=_payload_float(row["inverse_condition_ratio"], "KP3 condition"),
                non_sink_prefix_coverage=_payload_fraction(row["non_sink_prefix_coverage"], "KP3 prefix"),  # type: ignore[arg-type]
                non_sink_suffix_coverage=_payload_fraction(row["non_sink_suffix_coverage"], "KP3 suffix"),  # type: ignore[arg-type]
                per_channel_scales=tuple(_payload_int(item, "KP3 scale") for item in scales),
        )
        if (
            decoded_row.n_rows != expected_rows
            or decoded_row.n_suffixes != expected_suffixes
            or decoded_row.n_columns != expected_columns
            or decoded_row.n_cells != expected_cells
            or decoded_row.rank > min(expected_rows, expected_columns)
            or decoded_row.incremental_rank
            != decoded_row.rank - (kp3_rows[-1].rank if kp3_rows else 0)
            or not (0.0 <= decoded_row.inverse_condition_ratio <= 1.0)
            or not (
                Fraction(0) <= decoded_row.non_sink_prefix_coverage <= Fraction(1)
                and Fraction(0) <= decoded_row.non_sink_suffix_coverage <= Fraction(1)
            )
            or any(item < 0 for item in decoded_row.singular_values)
            or decoded_row.per_channel_scales[0] not in {0, 1}
            or decoded_row.per_channel_scales[1] not in {0, 1}
            or any(
                left < right
                for left, right in zip(
                    decoded_row.singular_values,
                    decoded_row.singular_values[1:],
                )
            )
        ):
            raise ProductionExecutionDenied("KP3 cutoff arithmetic is inconsistent")
        if decoded_row.rank == 0:
            if decoded_row.inverse_condition_ratio != 0.0 or any(
                value != 0.0 for value in decoded_row.singular_values
            ) or any(decoded_row.per_channel_scales):
                raise ProductionExecutionDenied(
                    "KP3 zero rank disagrees with its floating spectrum"
                )
        else:
            if (
                not any(decoded_row.per_channel_scales)
                or decoded_row.singular_values[0] <= 0.0
                or decoded_row.inverse_condition_ratio
                != decoded_row.singular_values[decoded_row.rank - 1]
                / decoded_row.singular_values[0]
            ):
                raise ProductionExecutionDenied(
                    "KP3 rank/condition ratio disagrees with its floating spectrum"
                )
        if (
            decoded_row.n_rows % decoded_row.non_sink_prefix_coverage.denominator
            != 0
            or (
                decoded_row.n_rows * decoded_row.n_suffixes
            )
            % decoded_row.non_sink_suffix_coverage.denominator
            != 0
        ):
            raise ProductionExecutionDenied("KP3 coverage fractions are impossible")
        kp3_rows.append(decoded_row)
    kp3 = HankelProbeReport(
        disposition=kp3_raw["disposition"], cutoffs=tuple(kp3_rows)
    )
    r1, r2, r3 = kp3.cutoffs
    if not (r1.rank <= r2.rank <= r3.rank):
        raise ProductionExecutionDenied("KP3 ranks are not monotone")
    if any(
        any(right < left for left, right in zip(before, after))
        for before, after in zip(
            (row.per_channel_scales for row in kp3.cutoffs),
            (row.per_channel_scales for row in kp3.cutoffs[1:]),
        )
    ):
        raise ProductionExecutionDenied("KP3 channel scales are not monotone")
    if (
        r3.rank == r2.rank
        and r2.rank != 0
        and (r3.n_rows > r2.n_rows or r3.n_columns > r2.n_columns)
        and r3.inverse_condition_ratio >= 1e-8
    ):
        expected_kp3_disposition = "U05_KP3_PLATEAU_AT_D3"
    elif (
        r1.rank < r2.rank < r3.rank
        and Fraction(r3.rank, min(r3.n_rows, r3.n_columns)) >= Fraction(4, 5)
    ):
        expected_kp3_disposition = "U05_KP3_NO_LOW_RANK_WINDOW_ON_FROZEN_FAMILY"
    else:
        expected_kp3_disposition = "U05_KP3_INCONCLUSIVE"
    if kp3.disposition != expected_kp3_disposition:
        raise ProductionExecutionDenied("KP3 disposition disagrees with its evidence")
    for kp1_row, kp3_row in zip(kp1.cutoffs, kp3.cutoffs):
        if kp3_row.per_channel_scales[0] != int(
            kp1_row.first_entry_closed + kp1_row.derived_closed > 0
        ) or kp3_row.per_channel_scales[1] != int(
            kp1_row.first_entry_sink + kp1_row.derived_sink > 0
        ):
            raise ProductionExecutionDenied(
                "KP1 terminal counts and KP3 indicator scales disagree"
            )
    if kp2.successful_trajectories != kp1.cutoffs[-1].first_entry_closed:
        raise ProductionExecutionDenied(
            "KP1/KP2 successful-trajectory counts disagree"
        )
    decoded = KillProbeReport(
        schema=RAW_RESULT_SCHEMA,
        kp1=kp1,
        kp2=kp2,
        kp3=kp3,
        capability_matrix=capability_matrix(kp1, kp2, kp3),
    )
    if canonical_json_bytes(_json_value(decoded)) != canonical_json_bytes(probe):
        raise ProductionExecutionDenied("probe payload disagrees with typed reconstruction")
    return decoded


def _valid_raw_result(
    raw: bytes | None, *, receipt: Mapping[str, Any]
) -> tuple[bool, str | None]:
    if raw is None:
        return False, None
    try:
        value = _parse_canonical_json(raw, schema=RAW_RESULT_SCHEMA)
        status = value.get("status")
        common = {
            "schema",
            "status",
            "candidate",
            "task_matrix_sha256",
            "action_matrix_sha256",
            "look_consumed",
            "licenses_k1_k4",
            "licenses_u2_u5_claims",
            "licenses_wp4_wp12_implementation",
            "licenses_gpu",
            "licenses_canonical_rpc_rerun",
            "licenses_reserved_data_read",
        }
        if status == "U05_COMPLETE":
            expected = common | {
                "environment_content_digest",
                "prerequisites",
                "costs",
                "probe_report",
            }
        elif status in {"U05_PREREQUISITE_BLOCKED", "U05_INTERNAL_FAILURE"}:
            expected = common | {"reason_class", "reason", "elapsed_seconds"}
        else:
            return False, status if type(status) is str else None
        _exact_mapping_fields(value, expected, "raw child result")
        if (
            value["candidate"] != receipt["candidate"]
            or value["task_matrix_sha256"] != TASK_MATRIX_SHA256
            or value["action_matrix_sha256"] != ACTION_MATRIX_SHA256
            or value["look_consumed"] is not True
            or any(value[name] is not False for name in common if name.startswith("licenses_"))
        ):
            return False, status
        if status == "U05_COMPLETE":
            if value["environment_content_digest"] != receipt["environment"][
                "environment_content_digest"
            ]:
                return False, status
            prerequisites = _exact_mapping_fields(
                value["prerequisites"],
                {
                    "matrix_literal_digests_verified",
                    "strict_rpc_schema_verified",
                    "independent_replay_verified_for_all_concrete_rows",
                    "prefix_closed_chart_complete",
                    "transition_censor_count",
                    "cache_policy_bypass_verified",
                    "heartbeat_caps_verified",
                    "worker_state_cleanup_verified",
                    "fresh_worker_per_task_verified",
                },
                "raw prerequisites",
            )
            if (
                prerequisites["matrix_literal_digests_verified"] is not True
                or prerequisites["strict_rpc_schema_verified"] is not True
                or prerequisites[
                    "independent_replay_verified_for_all_concrete_rows"
                ]
                is not True
                or prerequisites["prefix_closed_chart_complete"] is not True
                or type(prerequisites["transition_censor_count"]) is not int
                or prerequisites["transition_censor_count"] != 0
                or prerequisites["cache_policy_bypass_verified"] is not True
                or prerequisites["heartbeat_caps_verified"] is not True
                or prerequisites["worker_state_cleanup_verified"] is not True
                or prerequisites["fresh_worker_per_task_verified"] is not True
            ):
                return False, status
            costs = _exact_mapping_fields(
                value["costs"],
                {
                    "task_count",
                    "action_count",
                    "unique_state_count",
                    "transition_row_count",
                    "word_occurrence_count",
                    "primary_attempts",
                    "replay_attempts",
                    "prefix_executions",
                    "total_lean_tactic_executions",
                    "syntactic_sink_rows",
                    "peak_live_state_count",
                    "chart_released_live_state_count",
                    "post_chart_frontier_discard_count",
                    "elapsed_seconds",
                    "worker_status",
                },
                "raw costs",
            )
            integer_costs = set(costs) - {"elapsed_seconds", "worker_status"}
            if any(type(costs[name]) is not int or costs[name] < 0 for name in integer_costs):
                return False, status
            if (
                costs["task_count"] != 5
                or costs["action_count"] != 12
                or not (1 <= costs["unique_state_count"] <= FROZEN_LIMITS["maximum_unique_states_total"])
                or costs["unique_state_count"] > 5 + costs["primary_attempts"]
                or not (
                    1
                    <= costs["transition_row_count"]
                    <= costs["unique_state_count"] * costs["action_count"]
                )
                or costs["transition_row_count"] % costs["action_count"] != 0
                or costs["word_occurrence_count"] != 5 * (1 + 12 + 12**2 + 12**3)
                or costs["prefix_executions"] != 7
                or costs["primary_attempts"] != costs["replay_attempts"]
                or costs["primary_attempts"]
                > FROZEN_LIMITS["maximum_primary_state_action_attempts"]
                or costs["replay_attempts"]
                > FROZEN_LIMITS["maximum_replay_reexecutions"]
                or costs["total_lean_tactic_executions"]
                != costs["prefix_executions"]
                + costs["primary_attempts"]
                + costs["replay_attempts"]
                or costs["total_lean_tactic_executions"]
                > FROZEN_LIMITS["maximum_total_lean_tactic_executions"]
                or costs["transition_row_count"]
                != costs["primary_attempts"] + costs["syntactic_sink_rows"]
                or not (
                    5
                    <= costs["chart_released_live_state_count"]
                    + costs["post_chart_frontier_discard_count"]
                    <= 5 + costs["primary_attempts"]
                )
                or costs["peak_live_state_count"]
                > FROZEN_LIMITS["maximum_unique_states_per_task"] + 1
                or type(costs["worker_status"]) is not list
                or len(costs["worker_status"]) != 5
                or isinstance(costs["elapsed_seconds"], bool)
                or not isinstance(costs["elapsed_seconds"], (int, float))
                or not math.isfinite(float(costs["elapsed_seconds"]))
                or costs["elapsed_seconds"] < 0
                or costs["elapsed_seconds"]
                > FROZEN_LIMITS["whole_run_wall_limit_seconds"]
            ):
                return False, status
            worker_rows = costs["worker_status"]
            decoded_workers: list[Mapping[str, Any]] = []
            for raw_worker in worker_rows:
                worker = _exact_mapping_fields(
                    raw_worker,
                    {
                        "task_id",
                        "n_states",
                        "n_requests",
                        "n_failures",
                        "n_primary_executions",
                        "n_replay_executions",
                        "released_by_process_abort",
                        "peak_owned_states",
                    },
                    "raw worker status",
                )
                if type(worker["task_id"]) is not str or any(
                    type(worker[name]) is not int or worker[name] < 0
                    for name in set(worker) - {"task_id"}
                ):
                    return False, status
                decoded_workers.append(worker)
            if (
                frozenset(worker["task_id"] for worker in decoded_workers)
                != PRODUCTION_TASK_IDS
                or len({worker["task_id"] for worker in decoded_workers}) != 5
                or any(
                    worker["n_states"] != 0
                    or worker["released_by_process_abort"] != 0
                    or worker["n_primary_executions"]
                    != worker["n_replay_executions"]
                    or worker["n_failures"] > worker["n_requests"]
                    or worker["n_failures"] > worker["n_primary_executions"]
                    or worker["n_requests"]
                    < worker["n_primary_executions"] + 3
                    or worker["peak_owned_states"] < 1
                    or worker["peak_owned_states"]
                    > FROZEN_LIMITS["maximum_unique_states_per_task"] + 1
                    for worker in decoded_workers
                )
                or sum(worker["n_primary_executions"] for worker in decoded_workers)
                != costs["primary_attempts"]
                or sum(worker["n_replay_executions"] for worker in decoded_workers)
                != costs["replay_attempts"]
                or max(worker["peak_owned_states"] for worker in decoded_workers)
                != costs["peak_live_state_count"]
            ):
                return False, status
            total_worker_requests = sum(
                worker["n_requests"] for worker in decoded_workers
            )
            accounted_discards = (
                costs["chart_released_live_state_count"]
                + costs["post_chart_frontier_discard_count"]
            )
            if not (
                15 + costs["primary_attempts"] + accounted_discards
                <= total_worker_requests
                <= 15 + 2 * costs["primary_attempts"] + accounted_discards
            ):
                return False, status
            decoded_probe = _decode_probe_report(value["probe_report"])
            if (
                decoded_probe.kp1.cutoffs[-1].n_id_open
                > costs["unique_state_count"]
                or decoded_probe.kp1.cutoffs[-1].n_obs_open
                > costs["unique_state_count"]
            ):
                return False, status
        else:
            if type(value["reason_class"]) is not str or type(value["reason"]) is not str:
                return False, status
            if isinstance(value["elapsed_seconds"], bool) or not isinstance(
                value["elapsed_seconds"], (int, float)
            ):
                return False, status
            if (
                not math.isfinite(float(value["elapsed_seconds"]))
                or value["elapsed_seconds"] < 0
            ):
                return False, status
        return True, status
    except (ProductionExecutionDenied, KeyError, TypeError, ValueError):
        return False, None


def publish_attempt_envelope(
    *,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
    exit_code: int | None,
    exception_class: str | None,
    exception_message: str | None,
    launcher_stdout: bytes = b"",
    launcher_stderr: bytes = b"",
    recovery: bool = False,
) -> Mapping[str, Any]:
    receipt_raw = receipt_path.read_bytes()
    receipt = _parse_canonical_json(receipt_raw, schema=ATTEMPT_RECEIPT_SCHEMA)
    repo_root = _receipt_repo_root(receipt_path, receipt)
    _validate_attempt_receipt_value(
        receipt, repo_root=repo_root, receipt_path=receipt_path
    )
    expected_raw = _ensure_repo_relative(repo_root, receipt["paths"]["raw_output"])
    expected_artifact = _ensure_repo_relative(repo_root, receipt["paths"]["artifact"])
    if expected_raw != raw_output_path.resolve() or expected_artifact != artifact_path.resolve():
        raise ProductionExecutionDenied("publisher paths do not match the immutable receipt")
    marker_path = _ensure_repo_relative(repo_root, receipt["paths"]["matrix_open_marker"])
    marker, marker_raw = _evidence_bytes(marker_path)
    raw, raw_bytes = _evidence_bytes(raw_output_path)
    look_consumed = bool(marker["present"])
    marker_valid = _valid_matrix_marker(
        marker_raw, receipt=receipt, receipt_raw=receipt_raw
    )
    raw_schema_valid, raw_status = _valid_raw_result(raw_bytes, receipt=receipt)
    if recovery:
        kind = "launcher_recovery"
    elif (
        exit_code == 0
        and marker_valid
        and raw_schema_valid
        and raw_status == "U05_COMPLETE"
    ):
        kind = "runner_complete"
    elif (not look_consumed and raw_bytes is None and exit_code != 0) or (
        exit_code == 2
        and (
            marker_valid
            and raw_schema_valid
            and raw_status == "U05_PREREQUISITE_BLOCKED"
        )
    ):
        kind = "runner_prerequisite_blocked"
    else:
        kind = "runner_partial"
    envelope = {
        "schema": ATTEMPT_ENVELOPE_SCHEMA,
        "envelope_kind": kind,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": receipt["candidate"],
        "task_matrix_sha256": receipt["task_matrix_sha256"],
        "action_matrix_sha256": receipt["action_matrix_sha256"],
        "look_consumed": look_consumed,
        "receipt": {
            "present": True,
            "byte_length": len(receipt_raw),
            "sha256": _sha256_bytes(receipt_raw),
            "bytes_base64": base64.b64encode(receipt_raw).decode("ascii"),
        },
        "matrix_open_marker": marker,
        "matrix_open_marker_valid": marker_valid,
        "raw_child_output": raw,
        "raw_child_schema_valid": raw_schema_valid,
        "raw_child_status": raw_status,
        "process": {
            "exit_code": exit_code,
            "exception_class": exception_class,
            "exception_message": exception_message,
            "stdout": {
                "byte_length": len(launcher_stdout),
                "sha256": _sha256_bytes(launcher_stdout),
                "bytes_base64": base64.b64encode(launcher_stdout).decode("ascii"),
            },
            "stderr": {
                "byte_length": len(launcher_stderr),
                "sha256": _sha256_bytes(launcher_stderr),
                "bytes_base64": base64.b64encode(launcher_stderr).decode("ascii"),
            },
        },
    }
    _atomic_write_new(artifact_path, canonical_json_bytes(envelope))
    return envelope


MEASUREMENT_ENV_KEYS = frozenset(
    {
        "COMSPEC",
        "ELAN_HOME",
        "GH_CONFIG_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_KEY_1",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_VALUE_0",
        "GIT_CONFIG_VALUE_1",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "PYTHONHASHSEED",
        "PYTHONNOUSERSITE",
        "PYTHONUTF8",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "UPRIME_U05_EXECUTE",
        "UPRIME_U05_ELAN_EXECUTABLE",
        "UPRIME_U05_GIT_EXECUTABLE",
        "UPRIME_U05_MEASUREMENT_CHILD",
        "UPRIME_U05_NETWORK_DISABLED",
        "UPRIME_U05_PYTHON_IMPORT_PATHS",
        "UPRIME_U05_RECEIPT_SHA256",
        "USERPROFILE",
        "WINDIR",
        "XDG_CONFIG_HOME",
    }
)


def _measurement_environment(
    *, repo_root: Path, anchor: str, receipt_sha256: str
) -> dict[str, str]:
    """Construct a minimal allowlisted child environment; never copy the parent."""

    if re.fullmatch(r"[0-9A-F]{64}", receipt_sha256) is None:
        raise ProductionExecutionDenied("receipt SHA-256 is malformed")
    required_tools = {
        "git": shutil.which("git"),
        "elan": shutil.which("elan"),
    }
    if any(value is None for value in required_tools.values()):
        raise ProductionExecutionDenied("git/elan are required for measurement isolation")
    system_root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT")
    comspec = os.environ.get("ComSpec") or os.environ.get("COMSPEC")
    if not system_root or not comspec:
        raise ProductionExecutionDenied("canonical Windows process environment is incomplete")
    elan_home = Path(
        os.environ.get("ELAN_HOME", str(Path.home() / ".elan"))
    ).resolve()
    if not elan_home.is_dir():
        raise ProductionExecutionDenied("ELAN_HOME is absent")
    isolated_home = Path(
        os.path.abspath(
            repo_root / f"runs/uprime_u05_20260711/isolated_home_{anchor[:12]}"
        )
    )
    try:
        isolated_home.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ProductionExecutionDenied("isolated measurement home escaped repository") from exc
    _assert_plain_parent_chain(repo_root, isolated_home / ".u05_child")
    if _lexists(isolated_home):
        info = isolated_home.lstat()
        if isolated_home.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ProductionExecutionDenied("isolated measurement home is a reparse point")
        if not isolated_home.is_dir() or any(isolated_home.iterdir()):
            raise ProductionExecutionDenied("isolated measurement home is not empty")
    else:
        isolated_home.mkdir(parents=True, exist_ok=False)
    python_prefix = Path(sys.prefix).resolve()
    import_paths: list[str] = []
    for raw_entry in sys.path:
        candidate = repo_root.resolve() if not raw_entry else Path(raw_entry).resolve()
        if candidate != repo_root.resolve():
            try:
                candidate.relative_to(python_prefix)
            except ValueError as exc:
                raise ProductionExecutionDenied(
                    f"measurement Python path escapes worktree/runtime: {candidate}"
                ) from exc
        value = str(candidate)
        if value not in import_paths:
            import_paths.append(value)
    if not import_paths or Path(import_paths[0]).resolve() != repo_root.resolve():
        raise ProductionExecutionDenied("measurement Python path does not start at worktree")
    tool_dirs = {
        str(Path(sys.executable).resolve().parent),
        str(Path(required_tools["git"]).resolve().parent),
        str(Path(required_tools["elan"]).resolve().parent),
        str((Path(system_root) / "System32").resolve()),
    }
    path_value = os.pathsep.join(sorted(tool_dirs, key=str.casefold))
    temp_root = Path(tempfile.gettempdir()).resolve()
    drive, tail = os.path.splitdrive(str(isolated_home))
    env = {
        "COMSPEC": str(Path(comspec).resolve()),
        "ELAN_HOME": str(elan_home),
        "GH_CONFIG_DIR": str(isolated_home / "gh"),
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "remote.origin.url",
        "GIT_CONFIG_VALUE_0": "disabled.invalid",
        "GIT_CONFIG_KEY_1": "credential.helper",
        "GIT_CONFIG_VALUE_1": "",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(isolated_home),
        "HOMEDRIVE": drive,
        "HOMEPATH": tail or "\\",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": path_value,
        "PATHEXT": os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD"),
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "SYSTEMROOT": str(Path(system_root).resolve()),
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
        "UPRIME_U05_EXECUTE": "1",
        "UPRIME_U05_ELAN_EXECUTABLE": str(Path(required_tools["elan"]).resolve()),
        "UPRIME_U05_GIT_EXECUTABLE": str(Path(required_tools["git"]).resolve()),
        "UPRIME_U05_MEASUREMENT_CHILD": "1",
        "UPRIME_U05_NETWORK_DISABLED": "1",
        "UPRIME_U05_PYTHON_IMPORT_PATHS": json.dumps(
            import_paths, ensure_ascii=False, separators=(",", ":")
        ),
        "UPRIME_U05_RECEIPT_SHA256": receipt_sha256,
        "USERPROFILE": str(isolated_home),
        "WINDIR": str(Path(system_root).resolve()),
        "XDG_CONFIG_HOME": str(isolated_home / "xdg"),
    }
    if set(env) != set(MEASUREMENT_ENV_KEYS):
        raise AssertionError("measurement environment allowlist drifted")
    return env


def _measurement_command_environment_contract(
    *, repo_root: Path, anchor: str
) -> Mapping[str, Any]:
    template = _measurement_environment(
        repo_root=repo_root, anchor=anchor, receipt_sha256="0" * 64
    )
    template["UPRIME_U05_RECEIPT_SHA256"] = "$RECEIPT_SHA256"
    git = Path(template["UPRIME_U05_GIT_EXECUTABLE"]).resolve()
    elan = Path(template["UPRIME_U05_ELAN_EXECUTABLE"]).resolve()
    resolved = subprocess.run(
        [str(elan), "which", "lean"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
        env=template | {"UPRIME_U05_RECEIPT_SHA256": "0" * 64},
    )
    if resolved.returncode:
        raise ProductionExecutionDenied("cannot resolve Lean for command environment")
    lean = Path(resolved.stdout.strip()).resolve()
    tools = []
    for name, path in (
        ("python", Path(sys.executable).resolve()),
        ("git", git),
        ("elan", elan),
        ("lean", lean),
    ):
        digest, size = _stable_file_hash(path)
        tools.append(
            {"name": name, "path": str(path), "sha256": digest, "byte_length": size}
        )
    return {
        "measurement_environment": template,
        "tool_executables": tools,
        "lean_worker_environment": _lean_worker_environment(lean),
    }


def _deny_python_network() -> None:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise ProductionExecutionDenied("measurement-child network access is denied")

    class DeniedSocket(socket.socket):
        def connect(self, *_args: Any, **_kwargs: Any) -> Any:
            return denied()

        def connect_ex(self, *_args: Any, **_kwargs: Any) -> Any:
            return denied()

    socket.socket = DeniedSocket  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]


@contextmanager
def _attempt_process_lock(receipt_path: Path):
    """Hold an OS-released nonblocking lock across launch or recovery."""

    lock_path = receipt_path.with_name(receipt_path.name + ".launch.lock")
    if not _lexists(lock_path):
        try:
            _exclusive_write(lock_path, b"L")
        except FileExistsError:
            pass
    info = lock_path.lstat()
    if (
        lock_path.is_symlink()
        or getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        or not lock_path.is_file()
        or info.st_size != 1
    ):
        raise ProductionExecutionDenied("attempt lock path is not a plain one-byte file")
    handle = lock_path.open("r+b", buffering=0)
    locked = False
    try:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # unit/CI parity; production is Windows-only.
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (OSError, BlockingIOError) as exc:
            raise ProductionExecutionDenied(
                "attempt launcher/recovery is already active"
            ) from exc
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        else:
            handle.close()


def recover_attempt(
    *, receipt_path: Path, raw_output_path: Path, artifact_path: Path
) -> int:
    if not receipt_path.is_file():
        raise ProductionExecutionDenied("recover-only requires an existing attempt receipt")
    if artifact_path.exists():
        raise ProductionExecutionDenied("recover-only refuses to overwrite an artifact")
    with _attempt_process_lock(receipt_path):
        envelope = publish_attempt_envelope(
            receipt_path=receipt_path,
            raw_output_path=raw_output_path,
            artifact_path=artifact_path,
            exit_code=None,
            exception_class="LauncherRecovery",
            exception_message="recovered without reopening the matrix",
            recovery=True,
        )
    return 4 if envelope["look_consumed"] else 2


def _write_raw_child_result(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write_new(path, canonical_json_bytes(value))


def _measurement_child(
    *,
    repo_root: Path,
    anchor: str,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
) -> int:
    if os.environ.get("UPRIME_U05_MEASUREMENT_CHILD") != "1":
        raise ProductionExecutionDenied("measurement-child guard is absent")
    if sys.flags.isolated != 1 or sys.flags.no_site != 1:
        raise ProductionExecutionDenied("measurement child lacks -I -S bootstrap isolation")
    if os.environ.get("UPRIME_U05_NETWORK_DISABLED") != "1":
        raise ProductionExecutionDenied("measurement-child network guard is absent")
    unexpected_env = sorted(set(os.environ) - MEASUREMENT_ENV_KEYS)
    missing_env = sorted(MEASUREMENT_ENV_KEYS - set(os.environ))
    if unexpected_env or missing_env:
        raise ProductionExecutionDenied(
            f"measurement environment differs from allowlist; "
            f"missing={missing_env}, unexpected={unexpected_env}"
        )
    _deny_python_network()
    receipt_raw = receipt_path.read_bytes()
    if os.environ.get("UPRIME_U05_RECEIPT_SHA256") != _sha256_bytes(receipt_raw):
        raise ProductionExecutionDenied("measurement receipt changed after outer handoff")
    receipt = _parse_canonical_json(receipt_raw, schema=ATTEMPT_RECEIPT_SCHEMA)
    _validate_attempt_receipt_value(
        receipt, repo_root=repo_root.resolve(), receipt_path=receipt_path
    )
    expected_child_env = dict(receipt["command_contract"]["measurement_environment"])
    expected_child_env["UPRIME_U05_RECEIPT_SHA256"] = _sha256_bytes(receipt_raw)
    if dict(os.environ) != expected_child_env:
        raise ProductionExecutionDenied("measurement environment values differ from receipt")
    if receipt.get("candidate") != anchor:
        raise ProductionExecutionDenied("measurement anchor differs from receipt")
    if receipt.get("plan_commit") != PLAN_COMMIT or receipt.get("plan_blob") != PLAN_BLOB:
        raise ProductionExecutionDenied("measurement plan anchor differs from receipt")
    if (
        receipt.get("task_matrix_sha256") != TASK_MATRIX_SHA256
        or receipt.get("action_matrix_sha256") != ACTION_MATRIX_SHA256
        or receipt.get("frozen_limits") != dict(FROZEN_LIMITS)
    ):
        raise ProductionExecutionDenied("measurement freeze differs from receipt")
    if _receipt_repo_root(receipt_path, receipt) != repo_root.resolve():
        raise ProductionExecutionDenied("measurement repo root differs from receipt")
    if _stable_file_hash(Path(sys.executable).resolve())[0] != receipt["environment"][
        "python_executable_sha256"
    ]:
        raise ProductionExecutionDenied("measurement Python executable differs from receipt")
    expected_home = (
        repo_root / receipt["command_contract"]["isolated_home"]
    ).resolve()
    if Path(os.environ["USERPROFILE"]).resolve() != expected_home:
        raise ProductionExecutionDenied("measurement isolated home differs from receipt")
    if build_environment_manifest(repo_root) != receipt["environment"]:
        raise ProductionExecutionDenied(
            "measurement environment manifest changed after pre-receipt attestation"
        )
    for key, supplied in (
        ("raw_output", raw_output_path),
        ("artifact", artifact_path),
    ):
        expected = _ensure_repo_relative(repo_root, receipt["paths"][key])
        if expected != supplied.resolve():
            raise ProductionExecutionDenied(f"measurement {key} path differs from receipt")
    marker_path = _ensure_repo_relative(repo_root, receipt["paths"]["matrix_open_marker"])
    if raw_output_path.exists() or artifact_path.exists() or marker_path.exists():
        raise ProductionExecutionDenied("measurement output/marker already exists")
    receipt_path, raw_output_path, artifact_path, expected_marker = _validate_frozen_output_paths(
        repo_root,
        anchor=anchor,
        receipt_path=receipt_path,
        raw_output_path=raw_output_path,
        artifact_path=artifact_path,
    )
    if expected_marker != marker_path:
        raise ProductionExecutionDenied("measurement marker path differs from the freeze")
    status_rows = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    actual_status = tuple(row for row in status_rows.splitlines() if row)
    # The frozen receipt/raw/marker live under the ignored runs/ tree.  Requiring
    # an untracked receipt row would therefore reject every legitimate launch.
    if actual_status:
        raise ProductionExecutionDenied(
            f"measurement worktree changed after receipt: {actual_status!r}"
        )
    if _git_text(repo_root, "rev-parse", "HEAD") != anchor:
        raise ProductionExecutionDenied("measurement HEAD changed after receipt")
    if list(_assert_anchor_snapshot(repo_root)) != receipt.get("anchor_snapshot"):
        raise ProductionExecutionDenied("anchored inputs changed after receipt")
    if _assert_empty_rerun_registry(repo_root) != receipt.get("rerun_registry"):
        raise ProductionExecutionDenied("rerun registry changed after receipt")

    marker = {
        "schema": MATRIX_OPEN_SCHEMA,
        "opened_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": anchor,
        "attempt_id": receipt["attempt_id"],
        "receipt_sha256": _sha256_bytes(receipt_raw),
        "task_matrix_sha256": TASK_MATRIX_SHA256,
        "action_matrix_sha256": ACTION_MATRIX_SHA256,
        "look_consumed": True,
    }
    _exclusive_write(marker_path, canonical_json_bytes(marker))

    authorization = ProductionAuthorization(
        anchor=anchor,
        full_anchor_verified=True,
        exclusive_reservation_verified=True,
        pushed_green_candidate_verified=True,
        disposable_clean_worktree_verified=True,
    )
    started = time.monotonic()
    try:
        tasks, actions = load_frozen_execution_matrix(authorization)
        result = _execute_production_matrix(
            repo_root=repo_root,
            receipt=receipt,
            tasks=tasks,
            actions=actions,
            started=started,
        )
        _write_raw_child_result(raw_output_path, result)
        return 0 if result.get("status") == "U05_COMPLETE" else 2
    except (ProductionExecutionDenied, ChartPrerequisiteBlocked) as exc:
        blocked = {
            "schema": RAW_RESULT_SCHEMA,
            "status": "U05_PREREQUISITE_BLOCKED",
            "candidate": anchor,
            "task_matrix_sha256": TASK_MATRIX_SHA256,
            "action_matrix_sha256": ACTION_MATRIX_SHA256,
            "reason_class": type(exc).__name__,
            "reason": str(exc),
            "look_consumed": True,
            "elapsed_seconds": time.monotonic() - started,
            "licenses_k1_k4": False,
            "licenses_u2_u5_claims": False,
            "licenses_wp4_wp12_implementation": False,
            "licenses_gpu": False,
            "licenses_canonical_rpc_rerun": False,
            "licenses_reserved_data_read": False,
        }
        _write_raw_child_result(raw_output_path, blocked)
        return 2
    except BaseException as exc:  # capture partial evidence; outer envelope owns publication
        partial = {
            "schema": RAW_RESULT_SCHEMA,
            "status": "U05_INTERNAL_FAILURE",
            "candidate": anchor,
            "task_matrix_sha256": TASK_MATRIX_SHA256,
            "action_matrix_sha256": ACTION_MATRIX_SHA256,
            "reason_class": type(exc).__name__,
            "reason": str(exc),
            "look_consumed": True,
            "elapsed_seconds": time.monotonic() - started,
            "licenses_k1_k4": False,
            "licenses_u2_u5_claims": False,
            "licenses_wp4_wp12_implementation": False,
            "licenses_gpu": False,
            "licenses_canonical_rpc_rerun": False,
            "licenses_reserved_data_read": False,
        }
        _write_raw_child_result(raw_output_path, partial)
        return 4


def _run_in_kill_on_close_job(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    """Run the measurement child in a Windows job that owns all descendants."""

    if os.name != "nt":
        raise ProductionExecutionDenied("measurement process-tree guard requires Windows")
    import ctypes
    from ctypes import wintypes

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_job = kernel32.CreateJobObjectW
    create_job.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    create_job.restype = wintypes.HANDLE
    set_job = kernel32.SetInformationJobObject
    set_job.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    set_job.restype = wintypes.BOOL
    assign_job = kernel32.AssignProcessToJobObject
    assign_job.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    assign_job.restype = wintypes.BOOL
    terminate_job = kernel32.TerminateJobObject
    terminate_job.argtypes = [wintypes.HANDLE, wintypes.UINT]
    terminate_job.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    def resume_suspended_process(pid: int) -> None:
        class THREADENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", wintypes.LONG),
                ("tpDeltaPri", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
            ]

        snapshot_fn = kernel32.CreateToolhelp32Snapshot
        snapshot_fn.argtypes = [wintypes.DWORD, wintypes.DWORD]
        snapshot_fn.restype = wintypes.HANDLE
        first = kernel32.Thread32First
        first.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
        first.restype = wintypes.BOOL
        next_thread = kernel32.Thread32Next
        next_thread.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
        next_thread.restype = wintypes.BOOL
        open_thread = kernel32.OpenThread
        open_thread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_thread.restype = wintypes.HANDLE
        resume_thread = kernel32.ResumeThread
        resume_thread.argtypes = [wintypes.HANDLE]
        resume_thread.restype = wintypes.DWORD
        snapshot = snapshot_fn(0x00000004, 0)  # TH32CS_SNAPTHREAD
        if not snapshot or snapshot == wintypes.HANDLE(-1).value:
            raise ProductionExecutionDenied("cannot snapshot suspended measurement threads")
        resumed = 0
        try:
            entry = THREADENTRY32()
            entry.dwSize = ctypes.sizeof(entry)
            ok = first(snapshot, ctypes.byref(entry))
            while ok:
                if entry.th32OwnerProcessID == pid:
                    thread = open_thread(0x0002, False, entry.th32ThreadID)  # SUSPEND_RESUME
                    if not thread:
                        raise ProductionExecutionDenied(
                            "cannot open suspended measurement thread"
                        )
                    try:
                        if resume_thread(thread) == 0xFFFFFFFF:
                            raise ProductionExecutionDenied(
                                "cannot resume suspended measurement thread"
                            )
                        resumed += 1
                    finally:
                        close_handle(thread)
                ok = next_thread(snapshot, ctypes.byref(entry))
        finally:
            close_handle(snapshot)
        if resumed < 1:
            raise ProductionExecutionDenied("suspended measurement process had no thread")

    job = create_job(None, None)
    if not job:
        raise ProductionExecutionDenied("cannot create measurement process job")
    process: subprocess.Popen[bytes] | None = None
    try:
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not set_job(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ProductionExecutionDenied("cannot configure measurement process job")
        process = subprocess.Popen(
            tuple(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
            ),
        )
        if not assign_job(job, wintypes.HANDLE(int(process._handle))):  # type: ignore[attr-defined]
            process.kill()
            process.wait(timeout=10)
            raise ProductionExecutionDenied("cannot assign measurement child to process job")
        resume_suspended_process(process.pid)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            if not terminate_job(job, 4):
                process.kill()
            try:
                stdout, stderr = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=30)
            raise subprocess.TimeoutExpired(
                command, timeout, output=stdout, stderr=stderr
            ) from exc
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        try:
            if process is not None and process.poll() is None:
                if not terminate_job(job, 4):
                    process.kill()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=30)
        finally:
            close_handle(job)


def _outer_launcher(
    *,
    repo_root: Path,
    anchor: str,
    upstream: str,
    workflow_path: str,
    job_name: str,
    accepted_conclusion: str,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
) -> int:
    receipt_path, raw_output_path, artifact_path, _marker_path = (
        _validate_frozen_output_paths(
            repo_root,
            anchor=anchor,
            receipt_path=receipt_path,
            raw_output_path=raw_output_path,
            artifact_path=artifact_path,
        )
    )
    with _attempt_process_lock(receipt_path):
        receipt = build_attempt_receipt(
            repo_root,
            anchor=anchor,
            upstream=upstream,
            workflow_path=workflow_path,
            job_name=job_name,
            accepted_conclusion=accepted_conclusion,
            receipt_path=receipt_path,
            raw_output_path=raw_output_path,
            artifact_path=artifact_path,
        )
        receipt_raw = canonical_json_bytes(receipt)
        _atomic_write_new(receipt_path, receipt_raw)
        return _run_locked_attempt(
            repo_root=repo_root,
            receipt=receipt,
            receipt_raw=receipt_raw,
            receipt_path=receipt_path,
            raw_output_path=raw_output_path,
            artifact_path=artifact_path,
        )


def _run_locked_attempt(
    *,
    repo_root: Path,
    receipt: Mapping[str, Any],
    receipt_raw: bytes,
    receipt_path: Path,
    raw_output_path: Path,
    artifact_path: Path,
) -> int:
    """Launch and publish while excluding concurrent recovery."""

    receipt_sha256 = _sha256_bytes(receipt_raw)
    command = list(receipt["command_contract"]["measurement_argv"])
    exit_code: int | None = None
    stdout = b""
    stderr = b""
    exception_class: str | None = None
    exception_message: str | None = None
    child_environment = dict(receipt["command_contract"]["measurement_environment"])
    child_environment["UPRIME_U05_RECEIPT_SHA256"] = receipt_sha256
    try:
        child = _run_in_kill_on_close_job(
            command,
            cwd=repo_root,
            env=child_environment,
            # Environment/source attestation happens before the matrix-open
            # marker and is not part of the frozen 1800-second experiment.
            timeout=FROZEN_LIMITS["whole_run_wall_limit_seconds"] + 900,
        )
        exit_code = child.returncode
        stdout = child.stdout
        stderr = child.stderr
    except subprocess.TimeoutExpired as exc:
        exception_class = type(exc).__name__
        exception_message = str(exc)
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    except BaseException as exc:
        exception_class = type(exc).__name__
        exception_message = str(exc)
    envelope = publish_attempt_envelope(
        receipt_path=receipt_path,
        raw_output_path=raw_output_path,
        artifact_path=artifact_path,
        exit_code=exit_code,
        exception_class=exception_class,
        exception_message=exception_message,
        launcher_stdout=stdout,
        launcher_stderr=stderr,
    )
    if envelope["envelope_kind"] == "runner_complete":
        return 0
    if envelope["envelope_kind"] == "runner_prerequisite_blocked":
        return 2
    return 4


def _measurement_lean_binary(
    repo_root: Path, receipt: Mapping[str, Any]
) -> tuple[Path, Path]:
    environment = receipt.get("environment")
    if type(environment) is not dict:
        raise ProductionExecutionDenied("receipt environment is malformed")
    elan = os.environ.get("UPRIME_U05_ELAN_EXECUTABLE") or shutil.which("elan")
    if elan is None:
        raise ProductionExecutionDenied("measurement child cannot resolve elan")
    resolved = subprocess.run(
        [elan, "which", "lean"],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if resolved.returncode:
        raise ProductionExecutionDenied("measurement child cannot resolve Lean")
    lean_binary = Path(resolved.stdout.strip()).resolve()
    lean_digest, _lean_size = _stable_file_hash(lean_binary)
    if lean_digest != environment.get("lean_binary_sha256"):
        raise ProductionExecutionDenied("measurement Lean binary differs from receipt")
    worker = (repo_root / "lean_rgc/native_lean/RGCKernelRPC.lean").resolve()
    worker_digest, _worker_size = _stable_file_hash(worker)
    if worker_digest != environment.get("worker_source_sha256"):
        raise ProductionExecutionDenied("measurement worker source differs from receipt")
    return lean_binary, worker


def _chart_limits_from_freeze() -> ChartLimits:
    return ChartLimits(
        max_depth=FROZEN_LIMITS["maximum_symbolic_word_depth"],
        max_states_per_task=FROZEN_LIMITS["maximum_unique_states_per_task"],
        max_states_total=FROZEN_LIMITS["maximum_unique_states_total"],
        max_primary_attempts=FROZEN_LIMITS["maximum_primary_state_action_attempts"],
        max_replay_attempts=FROZEN_LIMITS["maximum_replay_reexecutions"],
        max_word_occurrences=FROZEN_LIMITS["maximum_symbolic_word_occurrences"],
    )


def _oracle_event_semantic_bytes(event: OracleEvent) -> bytes:
    target = None
    if event.target is not None:
        target = {
            "identity_key": event.target.identity_key.hex(),
            "full_signature": event.target.full_signature.hex(),
            "debt": list(event.target.debt),
            "response_signature": base64.b64encode(
                event.target.response_signature
            ).decode("ascii"),
        }
    return canonical_json_bytes(
        {
            "source_key": event.source_key.hex(),
            "action_id": event.action_id,
            "raw_status": event.raw_status,
            "totalized_status": (
                None
                if event.totalized_status is None
                else event.totalized_status.value
            ),
            "target": target,
            "replay_verified": event.replay_verified,
            "exact_delta": event.exact_delta,
            "censor_reason": event.censor_reason,
        }
    )


def _register_global_state_fact(
    registry: dict[bytes, tuple[bytes, tuple[int, int, int, int, int]]],
    state: StateView,
    *,
    maximum_states: int,
) -> None:
    """Enforce the global identity/full-compare cap before chart admission."""

    fact = (state.full_signature, state.debt)
    existing = registry.get(state.identity_key)
    if existing is not None:
        if existing != fact:
            raise ChartPrerequisiteBlocked(
                "cross-task state identity failed full-signature/debt comparison"
            )
        return
    if len(registry) >= maximum_states:
        raise ChartPrerequisiteBlocked("maximum unique states total reached")
    registry[state.identity_key] = fact


def _derive_sealed_row_event(
    rows: Mapping[tuple[bytes, str], OracleEvent],
    source_key: bytes,
    action_id: str,
) -> OracleEvent | None:
    event = rows.get((source_key, action_id))
    if event is None:
        return None
    target = event.target
    if target is not None:
        target = replace(target, live_rpc_state_id=None)
    return replace(
        event,
        target=target,
        primary_attempts=0,
        replay_attempts=0,
        derived_from_sealed_row=True,
    )


def _merge_task_charts(charts: Sequence[ReachableChart]) -> ReachableChart:
    """Merge sequential fresh-worker task charts with exact row comparison."""

    if not charts:
        raise ChartPrerequisiteBlocked("no task chart was produced")
    action_ids = charts[0].action_ids
    limits = charts[0].limits
    merged = ReachableChart(
        action_ids=action_ids,
        limits=limits,
        state_table={},
        transition_table={},
        word_table={},
        word_censors={},
        transition_censors={},
        task_ids=tuple(sorted(task_id for chart in charts for task_id in chart.task_ids)),
        primary_attempts=0,
        replay_attempts=0,
        peak_live_state_count=0,
        released_live_state_count=0,
    )
    if len(merged.task_ids) != len(set(merged.task_ids)):
        raise ChartPrerequisiteBlocked("task charts overlap in task ID")
    for chart in charts:
        if chart.action_ids != action_ids or chart.limits != limits:
            raise ChartPrerequisiteBlocked("task chart grammar/limits differ")
        if len(chart.task_ids) != 1:
            raise ChartPrerequisiteBlocked("sequential chart must contain exactly one task")
        for key, entry in chart.state_table.items():
            existing = merged.state_table.get(key)
            if existing is None:
                merged.state_table[key] = replace(
                    entry,
                    live_rpc_state_id=None,
                    task_ids=set(entry.task_ids),
                )
                continue
            if existing.full_signature != entry.full_signature or existing.debt != entry.debt:
                raise ChartPrerequisiteBlocked(
                    "cross-task equal identity failed full-signature/debt comparison"
                )
            existing.task_ids.update(entry.task_ids)
            if entry.expansion_status == "expanded":
                existing.expansion_status = "expanded"
        for key, event in chart.transition_table.items():
            existing = merged.transition_table.get(key)
            if existing is None:
                if event.derived_from_sealed_row:
                    raise ChartPrerequisiteBlocked(
                        "sealed-row derivation has no earlier concrete row"
                    )
                merged.transition_table[key] = event
            else:
                if (
                    _oracle_event_semantic_bytes(existing)
                    != _oracle_event_semantic_bytes(event)
                    or existing.derived_from_sealed_row
                    or not event.derived_from_sealed_row
                    or event.primary_attempts != 0
                    or event.replay_attempts != 0
                ):
                    raise ChartPrerequisiteBlocked(
                        "fresh task workers produced different semantic transition rows"
                    )
        for key, censor in chart.transition_censors.items():
            existing = merged.transition_censors.get(key)
            if existing is not None and existing != censor:
                raise ChartPrerequisiteBlocked(
                    "fresh task workers produced different transition censors"
                )
            merged.transition_censors[key] = censor
        for key, outcome in chart.word_table.items():
            if key in merged.word_table or key in merged.word_censors:
                raise ChartPrerequisiteBlocked("task word table key was duplicated")
            merged.word_table[key] = outcome
        for key, censor in chart.word_censors.items():
            if key in merged.word_table or key in merged.word_censors:
                raise ChartPrerequisiteBlocked("task word censor key was duplicated")
            merged.word_censors[key] = censor
        merged.primary_attempts += chart.primary_attempts
        merged.replay_attempts += chart.replay_attempts
        merged.peak_live_state_count = max(
            merged.peak_live_state_count, chart.peak_live_state_count
        )
        merged.released_live_state_count += chart.released_live_state_count
    if len(merged.state_table) > limits.max_states_total:
        raise ChartPrerequisiteBlocked("merged chart exceeded global state cap")
    if merged.primary_attempts > limits.max_primary_attempts:
        raise ChartPrerequisiteBlocked("merged chart exceeded global primary cap")
    if merged.replay_attempts > limits.max_replay_attempts:
        raise ChartPrerequisiteBlocked("merged chart exceeded global replay cap")
    if merged.word_occurrence_count > limits.max_word_occurrences:
        raise ChartPrerequisiteBlocked("merged chart exceeded global word cap")
    return merged


def _execute_production_matrix(
    *,
    repo_root: Path,
    receipt: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
    started: float,
) -> Mapping[str, Any]:
    """Execute one task at a time, then merge exact charts deterministically."""

    if os.environ.get("UPRIME_U05_MEASUREMENT_CHILD") != "1":
        raise ProductionExecutionDenied("production matrix requires the measurement child")
    if receipt.get("frozen_limits") != dict(FROZEN_LIMITS):
        raise ProductionExecutionDenied("receipt limits differ from the frozen limits")
    environment = receipt.get("environment")
    if type(environment) is not dict:
        raise ProductionExecutionDenied("receipt environment is malformed")
    environment_digest = environment.get("environment_content_digest")
    if type(environment_digest) is not str or re.fullmatch(r"[0-9A-F]{64}", environment_digest) is None:
        raise ProductionExecutionDenied("receipt environment digest is malformed")
    task_specs = tuple(U05TaskSpec.from_frozen_record(row) for row in tasks)
    symbols = tuple(ActionSymbol.from_frozen_action_record(row) for row in actions)
    if frozenset(task.task_id for task in task_specs) != PRODUCTION_TASK_IDS:
        raise ProductionExecutionDenied("runtime task inventory differs from the freeze")
    if tuple(symbol.action_id for symbol in symbols) != tuple(
        sorted(symbol.action_id for symbol in symbols)
    ) or len(symbols) != 12 or len({symbol.action_id for symbol in symbols}) != 12:
        raise ProductionExecutionDenied("runtime action inventory/order differs from freeze")
    imports = task_specs[0].imports
    if any(task.imports != imports for task in task_specs):
        raise ProductionExecutionDenied("production tasks do not share one import closure")
    prefix_executions = sum(
        1 for task in task_specs for line in task.prefix.splitlines() if line.strip()
    )
    if prefix_executions > FROZEN_LIMITS["maximum_prefix_tactic_executions"]:
        raise ProductionExecutionDenied("prefix execution cap would be exceeded")

    lean_binary, worker_source = _measurement_lean_binary(repo_root, receipt)
    symbols_by_id = {symbol.action_id: symbol for symbol in symbols}
    request_serial = 0
    syntactic_sinks = 0
    reserved_concrete_calls = 0
    post_chart_discard_count = 0
    task_charts: list[ReachableChart] = []
    status_payload: list[Mapping[str, Any]] = []
    global_state_facts: dict[
        bytes, tuple[bytes, tuple[int, int, int, int, int]]
    ] = {}
    global_expanded_keys: set[bytes] = set()
    global_transition_rows: dict[tuple[bytes, str], OracleEvent] = {}

    def next_request_id(kind: str) -> str:
        nonlocal request_serial
        request_serial += 1
        return f"u05_{request_serial:06d}_{kind}"

    try:
        for task in task_specs:
            if time.monotonic() - started > FROZEN_LIMITS["whole_run_wall_limit_seconds"]:
                raise ChartPrerequisiteBlocked("whole-run wall limit reached during task init")
            transport = SynchronousJSONLSubprocessTransport(
                [str(lean_binary), "--run", str(worker_source), "--imports", *imports],
                cwd=repo_root,
                env=_lean_worker_environment(lean_binary),
            )
            adapter = StrictKernelRPCOracleAdapter(
                transport,
                environment_content_digest=environment_digest,
                action_timeout_seconds=FROZEN_LIMITS["per_action_wall_timeout_seconds"],
                control_timeout_seconds=120.0,
            )
            runtime_by_live_id: dict[str, RuntimeStateView] = {}
            worker_aborted = False
            released_by_abort = 0
            peak_owned_states = 0
            task_reserved_start = reserved_concrete_calls
            try:
                adapter.load_project(
                    request_id=next_request_id(f"load_{task.task_id}"), imports=imports
                )
                seed_runtime = adapter.init_state(
                    request_id=next_request_id(f"init_{task.task_id}"), task=task
                )
                _register_global_state_fact(
                    global_state_facts,
                    seed_runtime.state_view,
                    maximum_states=FROZEN_LIMITS["maximum_unique_states_total"],
                )
                runtime_by_live_id[seed_runtime.live_rpc_state_id] = seed_runtime
                peak_owned_states = len(adapter.owned_state_ids)

                def discard(_task_id: str, state_id: str) -> None:
                    if runtime_by_live_id.pop(state_id, None) is None:
                        raise ChartPrerequisiteBlocked("chart discarded an unknown runtime state")
                    if worker_aborted:
                        return
                    adapter.discard_owned(
                        request_id=next_request_id("discard"), state_id=state_id
                    )
                    if adapter.owned_state_ids != frozenset(runtime_by_live_id):
                        raise ChartPrerequisiteBlocked(
                            "discard broke worker/runtime ownership equality"
                        )

                def oracle(_task_id: str, source: StateView, action_id: str) -> OracleEvent:
                    nonlocal reserved_concrete_calls, syntactic_sinks
                    nonlocal worker_aborted, released_by_abort, peak_owned_states
                    if time.monotonic() - started > FROZEN_LIMITS["whole_run_wall_limit_seconds"]:
                        raise ChartPrerequisiteBlocked("whole-run wall limit reached")
                    cached = _derive_sealed_row_event(
                        global_transition_rows, source.identity_key, action_id
                    )
                    if cached is not None:
                        return cached
                    if source.identity_key in global_expanded_keys:
                        raise ChartPrerequisiteBlocked(
                            "sealed transition row is incomplete"
                        )
                    if source.live_rpc_state_id is None:
                        raise ChartPrerequisiteBlocked(
                            "cross_task_unsealed_row_requires_unregistered_rehydration"
                        )
                    runtime = runtime_by_live_id.get(source.live_rpc_state_id)
                    if runtime is None or runtime.identity.canonical_bytes != source.identity_key:
                        raise ChartPrerequisiteBlocked("RPC oracle source binding is stale")
                    symbol = symbols_by_id.get(action_id)
                    if symbol is None:
                        raise ChartPrerequisiteBlocked("chart requested an unknown action symbol")
                    if worker_aborted:
                        return OracleEvent.censor(
                            source.identity_key,
                            action_id,
                            "worker_aborted_after_censor",
                            primary_attempts=0,
                            replay_attempts=0,
                        )
                    try:
                        runtime.bind_action(symbol)
                    except StrictContractError:
                        syntactic_sinks += 1
                        return OracleEvent.ordinary_failure(
                            source.identity_key,
                            action_id,
                            primary_attempts=0,
                            replay_attempts=0,
                        )
                    next_reserved = reserved_concrete_calls + 1
                    if (
                        next_reserved > FROZEN_LIMITS["maximum_primary_state_action_attempts"]
                        or next_reserved > FROZEN_LIMITS["maximum_replay_reexecutions"]
                        or prefix_executions + 2 * next_reserved
                        > FROZEN_LIMITS["maximum_total_lean_tactic_executions"]
                    ):
                        raise ChartPrerequisiteBlocked(
                            "primary/replay/total execution cap reached before RPC"
                        )
                    reserved_concrete_calls = next_reserved
                    result = adapter.apply_symbol(
                        request_id=next_request_id("apply"),
                        source=runtime,
                        symbol=symbol,
                    )
                    peak_owned_states = max(peak_owned_states, len(adapter.owned_state_ids))
                    if result.target_state is not None:
                        _register_global_state_fact(
                            global_state_facts,
                            result.target_state.state_view,
                            maximum_states=FROZEN_LIMITS[
                                "maximum_unique_states_total"
                            ],
                        )
                        target_id = result.target_state.live_rpc_state_id
                        if target_id in runtime_by_live_id:
                            raise ChartPrerequisiteBlocked("worker reused a live child state ID")
                        runtime_by_live_id[target_id] = result.target_state
                    retained = result.retained_state_id
                    if retained is not None and result.target_state is None:
                        adapter.discard_owned(
                            request_id=next_request_id("discard_terminal"), state_id=retained
                        )
                    if result.event.totalized_status is OutcomeKind.SINK and retained is not None:
                        raise ChartPrerequisiteBlocked("sink transition retained a child state")
                    if result.event.is_censor:
                        worker_aborted = True
                        released_by_abort = len(adapter.owned_state_ids)
                        transport.close()
                    elif adapter.owned_state_ids != frozenset(runtime_by_live_id):
                        raise ChartPrerequisiteBlocked(
                            "apply broke worker/runtime ownership equality"
                        )
                    return result.event

                task_chart = build_reachable_chart(
                    seeds={task.task_id: seed_runtime.state_view},
                    actions=symbols,
                    oracle=oracle,
                    limits=_chart_limits_from_freeze(),
                    discard_live_state=discard,
                )
                if task_chart.has_censors or worker_aborted:
                    raise ChartPrerequisiteBlocked(
                        f"task {task.task_id} contains a censored transition"
                    )
                for state_id in tuple(sorted(adapter.owned_state_ids)):
                    if runtime_by_live_id.pop(state_id, None) is None:
                        raise ChartPrerequisiteBlocked(
                            "frontier cleanup found an untracked worker state"
                        )
                    adapter.discard_owned(
                        request_id=next_request_id("discard_frontier"), state_id=state_id
                    )
                    post_chart_discard_count += 1
                if runtime_by_live_id or adapter.owned_state_ids:
                    raise ChartPrerequisiteBlocked("task worker retained state after cleanup")
                for entry in task_chart.state_table.values():
                    entry.live_rpc_state_id = None
                status = adapter.status(
                    request_id=next_request_id(f"status_{task.task_id}")
                )
                task_reserved = reserved_concrete_calls - task_reserved_start
                if (
                    status.n_states != 0
                    or status.n_primary_executions != task_chart.primary_attempts
                    or status.n_replay_executions != task_chart.replay_attempts
                    or status.n_primary_executions != task_reserved
                    or status.n_replay_executions != task_reserved
                ):
                    raise ChartPrerequisiteBlocked(
                        "task worker/chart/reservation counters disagree"
                    )
                status_payload.append(
                    {
                        "task_id": task.task_id,
                        "n_states": status.n_states,
                        "n_requests": status.n_requests,
                        "n_failures": status.n_failures,
                        "n_primary_executions": status.n_primary_executions,
                        "n_replay_executions": status.n_replay_executions,
                        "released_by_process_abort": released_by_abort,
                        "peak_owned_states": peak_owned_states,
                    }
                )
                adapter.shutdown(
                    request_id=next_request_id(f"shutdown_{task.task_id}")
                )
                task_expanded_keys = {
                    key for key, _action_id in task_chart.transition_table
                }
                overlap = task_expanded_keys & global_expanded_keys
                for edge_key, event in task_chart.transition_table.items():
                    is_overlap = edge_key[0] in overlap
                    if is_overlap != event.derived_from_sealed_row:
                        raise ChartPrerequisiteBlocked(
                            "sealed-row reuse provenance is inconsistent"
                        )
                    if not is_overlap:
                        if edge_key in global_transition_rows:
                            raise ChartPrerequisiteBlocked(
                                "new transition row duplicated global evidence"
                            )
                        global_transition_rows[edge_key] = event
                global_expanded_keys.update(task_expanded_keys)
                task_charts.append(task_chart)
            finally:
                transport.close()
        chart = _merge_task_charts(task_charts)
    except StrictKernelRPCError as exc:
        raise ChartPrerequisiteBlocked(f"strict RPC prerequisite failed: {exc}") from exc

    if (
        chart.primary_attempts != reserved_concrete_calls
        or chart.replay_attempts != reserved_concrete_calls
        or len(status_payload) != len(task_specs)
        or set(chart.state_table) != set(global_state_facts)
        or any(
            (entry.full_signature, entry.debt) != global_state_facts[key]
            for key, entry in chart.state_table.items()
        )
        or set(key for key, _action_id in chart.transition_table)
        != global_expanded_keys
        or set(chart.transition_table) != set(global_transition_rows)
        or len(chart.transition_table) != reserved_concrete_calls + syntactic_sinks
    ):
        raise ChartPrerequisiteBlocked("merged chart/counter/status evidence disagrees")
    actual_worker_peak = max(row["peak_owned_states"] for row in status_payload)
    if not (
        chart.peak_live_state_count
        <= actual_worker_peak
        <= chart.peak_live_state_count + 1
    ):
        raise ChartPrerequisiteBlocked("chart/worker peak-state accounting disagrees")
    report = evaluate_kill_probes(chart)
    if any(
        disposition == "U05_PREREQUISITE_BLOCKED"
        for disposition in (
            report.kp1.disposition,
            report.kp2.disposition,
            report.kp3.disposition,
        )
    ):
        raise ChartPrerequisiteBlocked("one or more kill probes failed a strict prerequisite")
    elapsed = time.monotonic() - started
    if elapsed > FROZEN_LIMITS["whole_run_wall_limit_seconds"]:
        raise ChartPrerequisiteBlocked("whole-run wall limit reached after execution")
    total_executions = prefix_executions + chart.primary_attempts + chart.replay_attempts
    if total_executions > FROZEN_LIMITS["maximum_total_lean_tactic_executions"]:
        raise ChartPrerequisiteBlocked("maximum total Lean tactic executions reached")
    return {
        "schema": RAW_RESULT_SCHEMA,
        "status": "U05_COMPLETE",
        "candidate": receipt["candidate"],
        "task_matrix_sha256": TASK_MATRIX_SHA256,
        "action_matrix_sha256": ACTION_MATRIX_SHA256,
        "look_consumed": True,
        "environment_content_digest": environment_digest,
        "prerequisites": {
            "matrix_literal_digests_verified": True,
            "strict_rpc_schema_verified": True,
            "independent_replay_verified_for_all_concrete_rows": True,
            "prefix_closed_chart_complete": True,
            "transition_censor_count": 0,
            "cache_policy_bypass_verified": True,
            "heartbeat_caps_verified": True,
            "worker_state_cleanup_verified": True,
            "fresh_worker_per_task_verified": True,
        },
        "costs": {
            "task_count": len(task_specs),
            "action_count": len(symbols),
            "unique_state_count": len(chart.state_table),
            "transition_row_count": len(chart.transition_table),
            "word_occurrence_count": chart.word_occurrence_count,
            "primary_attempts": chart.primary_attempts,
            "replay_attempts": chart.replay_attempts,
            "prefix_executions": prefix_executions,
            "total_lean_tactic_executions": total_executions,
            "syntactic_sink_rows": syntactic_sinks,
            "peak_live_state_count": actual_worker_peak,
            "chart_released_live_state_count": chart.released_live_state_count,
            "post_chart_frontier_discard_count": post_chart_discard_count,
            "elapsed_seconds": elapsed,
            "worker_status": status_payload,
        },
        "probe_report": _json_value(report),
        "licenses_k1_k4": False,
        "licenses_u2_u5_claims": False,
        "licenses_wp4_wp12_implementation": False,
        "licenses_gpu": False,
        "licenses_canonical_rpc_rerun": False,
        "licenses_reserved_data_read": False,
    }


def _mismatching_pairs(values: Sequence[bytes]) -> tuple[int, int]:
    mismatch = 0
    total = 0
    for left, right in combinations(values, 2):
        total += 1
        mismatch += int(left != right)
    return mismatch, total


def evaluate_kp1(chart: ReachableChart) -> KP1Report:
    if chart.has_censors:
        return KP1Report(
            disposition="U05_PREREQUISITE_BLOCKED",
            cutoffs=(),
            nontrivial_identity_classes=0,
            nontrivial_class_task_ids=(),
            blocked_reason="identity/replay/prefix-closure censor present",
        )
    if any(
        outcome.kind is OutcomeKind.OPEN and not outcome.response_signature
        for outcome in chart.word_table.values()
    ):
        return KP1Report(
            disposition="U05_PREREQUISITE_BLOCKED",
            cutoffs=(),
            nontrivial_identity_classes=0,
            nontrivial_class_task_ids=(),
            blocked_reason="missing open response evidence",
        )

    cutoffs: list[KP1CutoffReport] = []
    groups_at_three: dict[bytes, list[tuple[str, ActionWord, bytes]]] = {}
    for cutoff in (1, 2, 3):
        occurrences: list[tuple[str, ActionWord, bytes, tuple[Any, ...]]] = []
        first_closed = derived_closed = first_sink = derived_sink = censored = 0
        for (task_id, word), outcome in sorted(
            chart.word_table.items(), key=lambda item: (len(item[0][1]), item[0])
        ):
            if not word or len(word) > cutoff:
                continue
            if outcome.kind is OutcomeKind.OPEN:
                state = chart.state_for_outcome(outcome)
                if state is None:
                    raise AssertionError("open occurrence lacks state")
                occurrences.append(
                    (
                        task_id,
                        word,
                        outcome.response_signature,
                        state.behavioral_observation,
                    )
                )
            elif outcome.kind is OutcomeKind.CLOSED:
                if outcome.derived_terminal:
                    derived_closed += 1
                else:
                    first_closed += 1
            elif outcome.derived_terminal:
                derived_sink += 1
            else:
                first_sink += 1
        censored = sum(
            1 for (_, word) in chart.word_censors if word and len(word) <= cutoff
        )
        by_identity: dict[bytes, list[tuple[str, ActionWord, bytes]]] = {}
        observations: set[tuple[Any, ...]] = set()
        for task_id, word, response, observation in occurrences:
            outcome = chart.word_table[(task_id, word)]
            if outcome.state_key is None:
                raise AssertionError("open occurrence has no identity")
            by_identity.setdefault(outcome.state_key, []).append(
                (task_id, word, response)
            )
            observations.add(observation)
        mismatch = pair_count = 0
        for group in by_identity.values():
            group_mismatch, group_pairs = _mismatching_pairs(
                [response for _, _, response in group]
            )
            mismatch += group_mismatch
            pair_count += group_pairs
        n_occ = len(occurrences)
        n_id = len(by_identity)
        n_obs = len(observations)
        cutoffs.append(
            KP1CutoffReport(
                cutoff=cutoff,
                n_occ_open=n_occ,
                n_id_open=n_id,
                c_id_open=Fraction(n_occ, n_id) if n_id else None,
                n_obs_open=n_obs,
                c_obs_open=Fraction(n_occ, n_obs) if n_obs else None,
                p_raw_open=Fraction(mismatch, pair_count) if pair_count else None,
                first_entry_closed=first_closed,
                derived_closed=derived_closed,
                first_entry_sink=first_sink,
                derived_sink=derived_sink,
                censored=censored,
            )
        )
        if cutoff == 3:
            groups_at_three = by_identity

    nontrivial = {
        key: group
        for key, group in groups_at_three.items()
        if len({word for _, word, _ in group}) >= 2
    }
    class_tasks = tuple(
        sorted({task_id for group in nontrivial.values() for task_id, _, _ in group})
    )
    last = cutoffs[-1]
    response_inconsistent = any(
        row.p_raw_open is not None and row.p_raw_open > 0 for row in cutoffs
    )
    if response_inconsistent:
        disposition = "U05_PREREQUISITE_BLOCKED"
    elif any(
        row.c_id_open is None or row.c_obs_open is None for row in cutoffs
    ):
        disposition = "U05_KP1_INCONCLUSIVE"
    elif (
        len(nontrivial) >= 2
        and len(class_tasks) >= 2
        and last.c_id_open is not None
        and last.c_id_open >= Fraction(11, 10)
    ):
        disposition = "U05_KP1_SCALE_READY"
    elif nontrivial:
        disposition = "U05_KP1_EXISTENCE_ONLY"
    elif any(row.n_obs_open < row.n_id_open for row in cutoffs):
        disposition = "U05_KP1_OBSERVATION_ALIAS_ONLY"
    elif all(
        row.n_occ_open > 0
        and row.n_occ_open == row.n_id_open == row.n_obs_open
        for row in cutoffs
    ):
        disposition = "U05_KP1_NO_IDENTITY_COMPRESSION"
    else:
        disposition = "U05_KP1_INCONCLUSIVE"
    return KP1Report(
        disposition=disposition,
        cutoffs=tuple(cutoffs),
        nontrivial_identity_classes=len(nontrivial),
        nontrivial_class_task_ids=class_tasks,
        blocked_reason=(
            "equal full identities produced different occurrence responses"
            if response_inconsistent
            else None
        ),
    )


def _componentwise_contracts(
    before: tuple[int, ...], after: tuple[int, ...]
) -> bool:
    return all(right <= left for left, right in zip(before, after)) and after != before


def evaluate_kp2(chart: ReachableChart) -> KP2Report:
    if chart.has_censors:
        return _blocked_kp2("resource/transport/replay censor present")
    if any(not event.exact_delta for event in chart.transition_table.values()):
        return _blocked_kp2("inexact before/after delta present")

    successful = [
        (task_id, word)
        for (task_id, word), outcome in chart.word_table.items()
        if word
        and outcome.kind is OutcomeKind.CLOSED
        and not outcome.derived_terminal
    ]
    successful.sort(key=lambda item: (len(item[1]), item))
    edge_keys: set[tuple[str, ActionWord]] = set()
    block_keys_by_length: dict[int, set[tuple[str, ActionWord, ActionWord]]] = {
        1: set(),
        2: set(),
        3: set(),
    }
    terminal_steps: set[tuple[str, ActionWord]] = set()
    longest_run = 0

    for task_id, word in successful:
        prefix_outcomes = [
            chart.outcome(task_id, word[:index]) for index in range(len(word) + 1)
        ]
        if any(
            outcome.kind is not OutcomeKind.OPEN
            for outcome in prefix_outcomes[:-1]
        ) or prefix_outcomes[-1].kind is not OutcomeKind.CLOSED:
            continue
        terminal_steps.add((task_id, word))
        run = 0
        for index in range(len(word) - 1):
            before_word = word[:index]
            after_word = word[: index + 1]
            before = chart.state_for_outcome(prefix_outcomes[index])
            after = chart.state_for_outcome(prefix_outcomes[index + 1])
            if before is None or after is None:
                raise AssertionError("eligible open step lacks a state")
            edge_keys.add((task_id, after_word))
            if _componentwise_contracts(before.debt, after.debt):
                run = 0
            else:
                run += 1
                longest_run = max(longest_run, run)
        for start in range(len(word) - 1):
            for stop in range(start + 1, min(len(word) - 1, start + 3) + 1):
                block_keys_by_length[stop - start].add(
                    (task_id, word[:start], word[:stop])
                )

    noncontractive = 0
    coordinate_increases = [0] * 5
    for task_id, after_word in sorted(edge_keys):
        before = chart.state_for_outcome(chart.outcome(task_id, after_word[:-1]))
        after = chart.state_for_outcome(chart.outcome(task_id, after_word))
        if before is None or after is None:
            raise AssertionError("eligible edge lacks state")
        contractive = _componentwise_contracts(before.debt, after.debt)
        noncontractive += int(not contractive)
        for index, (left, right) in enumerate(zip(before.debt, after.debt)):
            coordinate_increases[index] += int(right > left)

    contractive_by_length = [0, 0, 0]
    for length in (1, 2, 3):
        for task_id, before_word, after_word in sorted(block_keys_by_length[length]):
            before = chart.state_for_outcome(chart.outcome(task_id, before_word))
            after = chart.state_for_outcome(chart.outcome(task_id, after_word))
            if before is None or after is None:
                raise AssertionError("eligible block lacks state")
            contractive_by_length[length - 1] += int(
                _componentwise_contracts(before.debt, after.debt)
            )

    n_edges = len(edge_keys)
    eligible_by_length = tuple(
        len(block_keys_by_length[length]) for length in (1, 2, 3)
    )
    contractive_by_length_tuple = tuple(contractive_by_length)
    n_blocks = sum(eligible_by_length)
    contractive_blocks = sum(contractive_by_length_tuple)
    if successful and contractive_blocks:
        disposition = "U05_KP2_EVENTUAL_WINDOW"
    elif n_blocks and contractive_blocks == 0:
        disposition = "U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT"
    else:
        disposition = "U05_KP2_FRAGMENT_INCONCLUSIVE"
    return KP2Report(
        disposition=disposition,
        successful_trajectories=len(successful),
        eligible_open_steps=n_edges,
        eligible_open_blocks=n_blocks,
        contractive_blocks=contractive_blocks,
        eligible_open_blocks_by_length=eligible_by_length,
        contractive_blocks_by_length=contractive_by_length_tuple,
        terminal_close_steps=len(terminal_steps),
        one_step_noncontractive_fraction=(
            Fraction(noncontractive, n_edges) if n_edges else None
        ),
        coordinate_increase_fractions=tuple(
            Fraction(count, n_edges) if n_edges else None
            for count in coordinate_increases
        ),
        longest_noncontractive_run=longest_run,
    )


def _blocked_kp2(reason: str) -> KP2Report:
    return KP2Report(
        disposition="U05_PREREQUISITE_BLOCKED",
        successful_trajectories=0,
        eligible_open_steps=0,
        eligible_open_blocks=0,
        contractive_blocks=0,
        eligible_open_blocks_by_length=(0, 0, 0),
        contractive_blocks_by_length=(0, 0, 0),
        terminal_close_steps=0,
        one_step_noncontractive_fraction=None,
        coordinate_increase_fractions=(None, None, None, None, None),
        longest_noncontractive_run=0,
        blocked_reason=reason,
    )


def capability_matrix(
    kp1: KP1Report, kp2: KP2Report, kp3: HankelProbeReport
) -> Mapping[str, Mapping[str, Any]]:
    exact = kp1.disposition in {
        "U05_KP1_EXISTENCE_ONLY",
        "U05_KP1_SCALE_READY",
    }
    hankel = kp3.disposition == "U05_KP3_PLATEAU_AT_D3"
    componentwise = kp2.disposition == "U05_KP2_EVENTUAL_WINDOW"
    return {
        "candidate_exact_partition": {
            "candidate": exact,
            "scale_ready": kp1.disposition == "U05_KP1_SCALE_READY",
            "may_draft": exact,
        },
        "candidate_hankel_predictive_model": {
            "candidate": hankel,
            "may_draft": hankel,
        },
        "candidate_componentwise_window": {
            "candidate": componentwise,
            "may_draft": componentwise,
        },
        "candidate_finite_horizon_envelope": {
            "candidate": False,
            "status": "pending_later_certified_upper_witness",
            "may_draft": False,
        },
        "candidate_maxent_nominal": {
            "candidate": False,
            "status": "pending_later_hard_envelope",
            "may_draft": False,
        },
        "candidate_predictive_similarity": {
            "candidate": False,
            "status": "pending_later_predictive_residual_endpoint",
            "may_draft": False,
        },
        "candidate_positive_similarity": {
            "candidate": False,
            "status": "pending_later_hard_positive_majorant",
            "may_draft": False,
        },
    }


def evaluate_kill_probes(chart: ReachableChart) -> KillProbeReport:
    """Evaluate all three independent probes on an already-built chart."""

    kp1 = evaluate_kp1(chart)
    kp2 = evaluate_kp2(chart)
    kp3 = evaluate_hankel_probe(chart)
    return KillProbeReport(
        schema="lean-rgc-uprime-u05-kill-probes-v1.0",
        kp1=kp1,
        kp2=kp2,
        kp3=kp3,
        capability_matrix=capability_matrix(kp1, kp2, kp3),
    )


def evaluate_unit_fixture(chart: ReachableChart) -> KillProbeReport:
    """CI-safe evaluator restricted to disjoint ``unit_u05_*`` task IDs."""

    if not chart.task_ids or any(
        not task_id.startswith("unit_u05_") or task_id in PRODUCTION_TASK_IDS
        for task_id in chart.task_ids
    ):
        raise ProductionExecutionDenied(
            "unit evaluator accepts only disjoint unit_u05_* fixtures"
        )
    return evaluate_kill_probes(chart)


def _json_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {
            "numerator": value.numerator,
            "denominator": value.denominator,
            "decimal": float(value),
        }
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def canonical_result_bytes(report: KillProbeReport) -> bytes:
    return (
        json.dumps(
            _json_value(report),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root")
    parser.add_argument("--anchor")
    parser.add_argument("--upstream")
    parser.add_argument("--ci-workflow")
    parser.add_argument("--ci-job")
    parser.add_argument("--accepted-ci-conclusion")
    parser.add_argument("--attempt-receipt")
    parser.add_argument("--raw-output")
    parser.add_argument("--artifact")
    parser.add_argument("--measurement-child", action="store_true")
    parser.add_argument("--recover-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Strict three-mode WP3 entrypoint; default remains pre-access denial."""

    args = _parser().parse_args(argv)
    modes = int(args.measurement_child) + int(args.recover_only)
    if modes > 1:
        print("U05 production execution denied: execution modes are mutually exclusive", file=sys.stderr)
        return 3
    if not args.recover_only and os.environ.get("UPRIME_U05_EXECUTE") != "1":
        print("U05 production execution denied: UPRIME_U05_EXECUTE=1 is required", file=sys.stderr)
        return 3
    if args.anchor is None or re.fullmatch(r"[0-9a-f]{40}", args.anchor) is None:
        print("U05 production execution denied: full anchor is required", file=sys.stderr)
        return 3
    required_paths = {
        "repo_root": args.repo_root,
        "attempt_receipt": args.attempt_receipt,
        "raw_output": args.raw_output,
        "artifact": args.artifact,
    }
    missing = sorted(name for name, value in required_paths.items() if value is None)
    if missing:
        print(
            "U05 production execution denied: missing required arguments: "
            + ",".join(missing),
            file=sys.stderr,
        )
        return 3
    repo_root = Path(args.repo_root).resolve()
    try:
        if _git_text(repo_root, "rev-parse", "--show-toplevel") != str(repo_root).replace("\\", "/"):
            # Git on Windows may preserve drive-letter case/slashes; resolve the
            # returned path before making the equality decision.
            discovered = Path(_git_text(repo_root, "rev-parse", "--show-toplevel")).resolve()
            if discovered != repo_root:
                raise ProductionExecutionDenied("--repo-root is not the Git worktree root")
        receipt_path = _ensure_repo_relative(repo_root, args.attempt_receipt)
        raw_output_path = _ensure_repo_relative(repo_root, args.raw_output)
        artifact_path = _ensure_repo_relative(repo_root, args.artifact)
        if args.recover_only:
            if any(
                value is not None
                for value in (
                    args.upstream,
                    args.ci_workflow,
                    args.ci_job,
                    args.accepted_ci_conclusion,
                )
            ):
                raise ProductionExecutionDenied(
                    "recover-only accepts no control-plane arguments"
                )
            receipt_path, raw_output_path, artifact_path, _marker_path = (
                _validate_frozen_output_paths(
                    repo_root,
                    anchor=args.anchor,
                    receipt_path=receipt_path,
                    raw_output_path=raw_output_path,
                    artifact_path=artifact_path,
                )
            )
            recovery_receipt = _parse_canonical_json(
                receipt_path.read_bytes(), schema=ATTEMPT_RECEIPT_SCHEMA
            )
            if recovery_receipt.get("candidate") != args.anchor:
                raise ProductionExecutionDenied(
                    "recover-only anchor differs from the immutable receipt"
                )
            return recover_attempt(
                receipt_path=receipt_path,
                raw_output_path=raw_output_path,
                artifact_path=artifact_path,
            )
        if args.measurement_child:
            if any(
                value is not None
                for value in (
                    args.upstream,
                    args.ci_workflow,
                    args.ci_job,
                    args.accepted_ci_conclusion,
                )
            ):
                raise ProductionExecutionDenied(
                    "measurement child retained control-plane arguments"
                )
            return _measurement_child(
                repo_root=repo_root,
                anchor=args.anchor,
                receipt_path=receipt_path,
                raw_output_path=raw_output_path,
                artifact_path=artifact_path,
            )
        required_control = {
            "upstream": args.upstream,
            "ci_workflow": args.ci_workflow,
            "ci_job": args.ci_job,
            "accepted_ci_conclusion": args.accepted_ci_conclusion,
        }
        missing_control = sorted(
            name for name, value in required_control.items() if value is None
        )
        if missing_control:
            raise ProductionExecutionDenied(
                "missing control-plane arguments: " + ",".join(missing_control)
            )
        return _outer_launcher(
            repo_root=repo_root,
            anchor=args.anchor,
            upstream=args.upstream,
            workflow_path=args.ci_workflow,
            job_name=args.ci_job,
            accepted_conclusion=args.accepted_ci_conclusion,
            receipt_path=receipt_path,
            raw_output_path=raw_output_path,
            artifact_path=artifact_path,
        )
    except ProductionExecutionDenied as exc:
        print(f"U05 production execution denied: {exc}", file=sys.stderr)
        return 3 if args.recover_only else 2
    except BaseException as exc:
        print(f"U05 internal failure: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ACTION_MATRIX_SHA256",
    "FROZEN_LIMITS",
    "KillProbeReport",
    "KP1CutoffReport",
    "KP1Report",
    "KP2Report",
    "OPAQUE_SIMP_SHA256",
    "PRODUCTION_TASK_IDS",
    "ProductionAuthorization",
    "ProductionExecutionDenied",
    "TASK_MATRIX_SHA256",
    "canonical_result_bytes",
    "capability_matrix",
    "evaluate_kill_probes",
    "evaluate_kp1",
    "evaluate_kp2",
    "evaluate_unit_fixture",
    "frozen_matrix_digests",
    "load_frozen_execution_matrix",
    "main",
    "verify_frozen_matrix_literals",
]
