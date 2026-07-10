from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import os
import platform
import queue
import secrets
import shutil
import subprocess
import threading
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lean_rgc.audit_result_cache import _max_heartbeats, make_audit_cache_key
from lean_rgc.evals.uprime_rerun_license import (
    RERUN_REGISTRY_PATH,
    reject_canonical_rerun_bootstrap,
)


SCHEMA_UPRIME_RPC_LITMUS = "lean-rgc-uprime-rpc-diagnostic-v1.1"
SCHEMA_UPRIME_RPC_RESERVATION = "lean-rgc-uprime-rpc-reservation-v1.0"
PREREG_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_rpc_diagnostic_preregistration.md"
)
AMENDMENT_1_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_rpc_diagnostic_amendment_1.md"
)
AMENDMENT_2_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_rpc_diagnostic_amendment_2.md"
)
REPAIR_MILESTONE_1_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_repair_milestone_1_2026-07-10.md"
)
EVIDENCE_MILESTONE_2A_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_evidence_milestone_2a_rerun_gate_2026-07-10.md"
)
EVIDENCE_MILESTONE_2B_PREREG_PATH = Path(
    "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_parsed_ledger_preregistration.md"
)
EVIDENCE_MILESTONE_2B_PHASE1A_EXECUTION_PATH = Path(
    "docs/experiments/"
    "uprime_odlrq_u1_evidence_milestone_2b_phase1a_execution_2026-07-11.md"
)
EVIDENCE_MILESTONE_2B_PHASE1B1_EXECUTION_PATH = Path(
    "docs/experiments/"
    "uprime_odlrq_u1_evidence_milestone_2b_phase1b1_execution_2026-07-11.md"
)
RERUN_LICENSE_SOURCE_PATH = Path("lean_rgc/evals/uprime_rerun_license.py")
RERUN_LICENSE_TEST_PATH = Path("tests/test_uprime_rerun_license.py")
LEDGER_SOURCE_PATH = Path("lean_rgc/evals/uprime_rpc_ledger.py")
LEDGER_TEST_PATH = Path("tests/test_uprime_rpc_ledger.py")
LEDGER_SEMANTICS_SOURCE_PATH = Path(
    "lean_rgc/evals/uprime_rpc_ledger_semantics.py"
)
LEDGER_SEMANTICS_TEST_SUPPORT_PATH = Path(
    "tests/uprime_rpc_ledger_semantics_cases.py"
)
PACKAGE_INIT_PATH = Path("lean_rgc/__init__.py")
EVALS_PACKAGE_INIT_PATH = Path("lean_rgc/evals/__init__.py")
SOURCE_PATH = Path("lean_rgc/evals/uprime_rpc_litmus.py")
TEST_PATH = Path("tests/test_uprime_rpc_litmus.py")
PROTOCOL_TEST_PATH = Path("tests/test_v49_kernel_rpc_worker.py")
CACHE_TEST_PATH = Path("tests/test_v85_cache_lane_and_coverage.py")
TIER_PATH = Path("tests/tier_manifest.json")
RPC_PATH = Path("lean_rgc/native_lean/RGCKernelRPC.lean")
CACHE_PATH = Path("lean_rgc/audit_result_cache.py")
SCHEMAS_PATH = Path("lean_rgc/schemas.py")
EXECUTOR_PATH = Path("lean_rgc/lean/executor.py")
BULK_EXECUTOR_PATH = Path("lean_rgc/lean/bulk_executor.py")
SUPERVISOR_PATH = Path("lean_rgc/lean/worker_supervisor.py")
ANCHOR_PATHS = (
    PREREG_PATH,
    AMENDMENT_1_PATH,
    AMENDMENT_2_PATH,
    REPAIR_MILESTONE_1_PATH,
    EVIDENCE_MILESTONE_2A_PATH,
    EVIDENCE_MILESTONE_2B_PREREG_PATH,
    EVIDENCE_MILESTONE_2B_PHASE1A_EXECUTION_PATH,
    EVIDENCE_MILESTONE_2B_PHASE1B1_EXECUTION_PATH,
    RERUN_REGISTRY_PATH,
    RERUN_LICENSE_SOURCE_PATH,
    RERUN_LICENSE_TEST_PATH,
    LEDGER_SOURCE_PATH,
    LEDGER_TEST_PATH,
    LEDGER_SEMANTICS_SOURCE_PATH,
    LEDGER_SEMANTICS_TEST_SUPPORT_PATH,
    PACKAGE_INIT_PATH,
    EVALS_PACKAGE_INIT_PATH,
    SOURCE_PATH,
    TEST_PATH,
    PROTOCOL_TEST_PATH,
    CACHE_TEST_PATH,
    TIER_PATH,
    RPC_PATH,
    CACHE_PATH,
    SCHEMAS_PATH,
    EXECUTOR_PATH,
    BULK_EXECUTOR_PATH,
    SUPERVISOR_PATH,
)

TASK_MAX_HEARTBEATS_OPTION = 731
EPISODE_MAX_HEARTBEATS_COUNTER = 1_000_000
CONSTRUCTOR_MAX_HEARTBEATS_OPTION = 123_456
BURN_MAX_HEARTBEATS_OPTION = 200_000
BURN_COUNTER_INCREMENT = 400_000_000
RUNTIME_DEFAULT_MAX_HEARTBEATS_OPTION = 200_000
EXPECTED_LEAN_VERSION_PREFIX = "Lean (version 4.31.0,"
EXPECTED_LEAN_BINARY_SHA256 = (
    "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
)
RPC_PROTOCOL_VERSION = "lean-rgc-jsonl-rpc-v2"
REPLAY_CERTIFICATE_VERSION = "lean-rgc-kernel-replay-certificate-v1"
REPLAY_VERIFICATION_METHOD = "same_before_state_independent_reexecution"
REGISTERED_RUN_DIR = Path("runs/uprime_u1_rpc_20260710")
FROZEN_TIMEOUT_S = 900.0
POST_RESPONSE_TIMEOUT_S = 10.0
NATURAL_EXIT_GRACE_S = 5.0
FORCED_REAP_BUDGET_S = 4.0
READER_DRAIN_RESERVE_S = 1.0
TERMINATE_GRACE_S = 2.0
EXPECTED_PERSISTENT_STATE_COUNT = 13
EXPECTED_STATUS_REQUEST_COUNT = 22
TRANSPORT_CLEAR_GATE_ID = "X0_shutdown_transport_clear"
TRANSPORT_CLEAR_CHECK_IDS = (
    "stream_complete",
    "shutdown_ack_ok",
    "response_sha256_bound",
    "natural_exit_within_grace",
    "no_forced_reap",
    "returncode_zero",
    "reader_threads_drained",
    "terminal_eof_exact",
    "no_transport_overflow",
    "json_stdout_only",
    "post_response_elapsed_bounded",
    "transport_finalized",
)
EXPECTED_RESPONSE_LABELS = (
    "load",
    "primary_init",
    "primary_split",
    "primary_split_replay",
    "primary_tail_close",
    "primary_tail_close_replay",
    "primary_head_close",
    "primary_head_close_replay",
    "zero_init",
    "zero_split",
    "zero_split_replay",
    "zero_child_close",
    "zero_child_close_replay",
    "side_init",
    "side_effect_close",
    "side_effect_close_replay",
    "burn_init",
    "burn",
    "reset_init",
    "reset",
    "reset_replay",
    "status",
    "shutdown",
)

CONTRACT_IDS = (
    "R0_request_id_echo",
    "B0_task_budget_init",
    "B1_action_budget_nonsticky",
    "B2_budget_telemetry",
    "B3_enforcement_reset",
    "B4_cache_budget_semantics",
    "D0_target_routing",
    "D1_transition_delta",
    "D2_all_goal_sweep",
    "R1_independent_replay",
    "E0_episode_budget",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _stable_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _git_commit(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    commit = (proc.stdout or "").strip()
    if proc.returncode != 0 or len(commit) != 40:
        raise RuntimeError("U'1 diagnostic requires an anchored Git commit")
    return commit


def _git_bytes(repo_root: Path, args: list[str]) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"Git anchor command failed: {' '.join(args)}: {message}")
    return proc.stdout


def _anchored_input_snapshot(
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[Path, bytes]]:
    records: dict[str, dict[str, Any]] = {}
    head_blobs: dict[Path, bytes] = {}
    for path in ANCHOR_PATHS:
        path_text = path.as_posix()
        head_oid = _git_bytes(repo_root, ["rev-parse", f"HEAD:{path_text}"]).decode(
            "ascii"
        ).strip()
        working_oid = _git_bytes(
            repo_root,
            ["hash-object", f"--path={path_text}", str(repo_root / path)],
        ).decode("ascii").strip()
        if working_oid != head_oid:
            raise RuntimeError(f"anchored input differs from HEAD blob: {path_text}")
        head_bytes = _git_bytes(repo_root, ["cat-file", "blob", head_oid])
        head_blobs[path] = head_bytes
        records[path_text] = {
            "git_blob_oid": head_oid,
            "head_blob_sha256": hashlib.sha256(head_bytes).hexdigest().upper(),
            "working_raw_sha256": _sha256(repo_root / path),
        }
    return records, head_blobs


def _assert_git_top_level(repo_root: Path) -> None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise RuntimeError("U'1 diagnostic repo root is not inside a Git worktree")
    discovered = Path(proc.stdout.strip()).resolve()
    if discovered != repo_root:
        raise RuntimeError(
            "--repo-root must be the exact Git top-level; "
            f"discovered {discovered}"
        )


def _assert_anchor_inputs_clean(repo_root: Path) -> None:
    for path in ANCHOR_PATHS:
        tracked = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{path.as_posix()}"],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if tracked.returncode != 0:
            raise RuntimeError(
                f"U'1 diagnostic anchor input is not committed: {path.as_posix()}"
            )
    proc = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *(p.as_posix() for p in ANCHOR_PATHS)],
        cwd=repo_root,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("U'1 diagnostic anchor inputs differ from committed HEAD")
    # Do not rely on index flags such as assume-unchanged/skip-worktree.  Compare
    # each Git-clean-filtered working blob with HEAD before any license check.
    _anchored_input_snapshot(repo_root)


def _assert_anchor_pushed(repo_root: Path, commit: str) -> str:
    upstream_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    upstream = (upstream_proc.stdout or "").strip()
    if upstream_proc.returncode != 0 or not upstream:
        raise RuntimeError("U'1 diagnostic branch has no configured upstream")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, upstream],
        cwd=repo_root,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("U'1 diagnostic anchor commit is not present on its upstream")
    return upstream


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def state_view(kernel_state: Any) -> dict[str, Any]:
    kernel = kernel_state if isinstance(kernel_state, dict) else {}
    goal_rows = kernel.get("goals") if isinstance(kernel.get("goals"), list) else []
    mvar_rows = (
        kernel.get("metavars") if isinstance(kernel.get("metavars"), list) else []
    )
    goals = [
        row.get("mvar_id")
        for row in goal_rows
        if isinstance(row, dict) and isinstance(row.get("mvar_id"), str)
    ]
    all_mvars = [
        row.get("mvar_id")
        for row in mvar_rows
        if isinstance(row, dict) and isinstance(row.get("mvar_id"), str)
    ]
    assigned = [
        row.get("mvar_id")
        for row in mvar_rows
        if isinstance(row, dict)
        and isinstance(row.get("mvar_id"), str)
        and row.get("assigned") is True
    ]
    return {
        "goals": goals,
        "assigned": assigned,
        "all_mvars": all_mvars,
        "duplicate_goals": len(goals) != len(set(goals)),
        "duplicate_assigned": len(assigned) != len(set(assigned)),
        "duplicate_mvars": len(all_mvars) != len(set(all_mvars)),
        "assigned_open_goals": sorted(set(goals) & set(assigned)),
    }


def state_structure(kernel_state: Any) -> dict[str, Any]:
    kernel = kernel_state if isinstance(kernel_state, dict) else None
    if kernel is None:
        return {"passed": False, "checks": {"is_object": False}, "view": state_view({})}
    goals = kernel.get("goals")
    metavars = kernel.get("metavars")
    goal_rows_valid = isinstance(goals, list) and all(
        isinstance(row, dict)
        and isinstance(row.get("mvar_id"), str)
        and bool(row.get("mvar_id"))
        for row in (goals if isinstance(goals, list) else [])
    )
    mvar_rows_valid = isinstance(metavars, list) and all(
        isinstance(row, dict)
        and isinstance(row.get("mvar_id"), str)
        and bool(row.get("mvar_id"))
        and isinstance(row.get("assigned"), bool)
        for row in (metavars if isinstance(metavars, list) else [])
    )
    view = state_view(kernel)
    goal_set = set(view["goals"])
    mvar_set = set(view["all_mvars"])
    checks = {
        "is_object": True,
        "schema_version": isinstance(kernel.get("schema_version"), str)
        and bool(kernel.get("schema_version")),
        "state_id": isinstance(kernel.get("state_id"), str)
        and bool(kernel.get("state_id")),
        "state_hash_raw": isinstance(kernel.get("state_hash_raw"), str)
        and bool(kernel.get("state_hash_raw")),
        "state_hash_norm": isinstance(kernel.get("state_hash_norm"), str)
        and bool(kernel.get("state_hash_norm")),
        "goal_rows": goal_rows_valid,
        "mvar_rows": mvar_rows_valid,
        "goals_unique": not view["duplicate_goals"],
        "assigned_unique": not view["duplicate_assigned"],
        "mvars_unique": not view["duplicate_mvars"],
        "goals_are_mvars": goal_rows_valid and mvar_rows_valid and goal_set <= mvar_set,
        "open_goals_unassigned": not view["assigned_open_goals"],
    }
    return {"passed": all(checks.values()), "checks": checks, "view": view}


def independent_delta(before_kernel: Any, after_kernel: Any) -> dict[str, list[str]]:
    before = state_view(before_kernel)
    after = state_view(after_kernel)
    before_goals = set(before["goals"])
    after_goals = set(after["goals"])
    before_assigned = set(before["assigned"])
    after_assigned = set(after["assigned"])
    before_mvars = set(before["all_mvars"])
    after_mvars = set(after["all_mvars"])
    assigned = after_assigned - before_assigned
    return {
        "closed_goals": sorted(before_goals & assigned),
        "new_goals": sorted(after_goals - before_goals),
        "assigned_mvars": sorted(assigned),
        "new_mvars": sorted(after_mvars - before_mvars),
    }


def delta_evidence(response: Any) -> dict[str, Any]:
    reply = response if isinstance(response, dict) else {}
    before_kernel = reply.get("kernel_state_before")
    after_kernel = reply.get("kernel_state_after")
    before_structure = state_structure(before_kernel)
    after_structure = state_structure(after_kernel)
    expected = independent_delta(
        before_kernel, after_kernel
    )
    reported_obj = (
        reply.get("state_delta") if isinstance(reply.get("state_delta"), dict) else {}
    )
    fields = tuple(expected)
    reported: dict[str, list[str]] = {}
    well_formed: dict[str, bool] = {}
    for field in fields:
        value = reported_obj.get(field)
        valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
        items = list(value) if valid else []
        reported[field] = sorted(items)
        well_formed[field] = valid and len(items) == len(set(items))
    before = before_structure["view"]
    after = after_structure["view"]
    removed_goals = sorted(set(before["goals"]) - set(after["goals"]))
    structural_checks = {
        "before_state": before_structure["passed"],
        "after_state": after_structure["passed"],
        "before_state_id": isinstance(before_kernel, dict)
        and before_kernel.get("state_id") == reply.get("before_state_id"),
        "after_state_id": isinstance(after_kernel, dict)
        and after_kernel.get("state_id") == reply.get("after_state_id"),
        "mvars_monotone": set(before["all_mvars"]) <= set(after["all_mvars"]),
        "assignments_monotone": set(before["assigned"]) <= set(after["assigned"]),
        "removed_goals_are_newly_assigned": removed_goals == expected["closed_goals"],
    }
    matches = {
        field: well_formed[field] and reported[field] == expected[field]
        for field in fields
    }
    return {
        "passed": all(matches.values()) and all(structural_checks.values()),
        "expected": expected,
        "reported": reported,
        "well_formed": well_formed,
        "matches": matches,
        "structural_checks": structural_checks,
        "before_structure": before_structure["checks"],
        "after_structure": after_structure["checks"],
        "after_assigned_open_goals": after["assigned_open_goals"],
    }


def _audit_flags(response: dict[str, Any]) -> dict[str, Any]:
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return (
        audit.get("audit_flags")
        if isinstance(audit.get("audit_flags"), dict)
        else {}
    )


def _budget_object(response: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    top = response.get("budget") if isinstance(response.get("budget"), dict) else {}
    flags = _audit_flags(response)
    mirrored = (
        flags.get("heartbeat_telemetry")
        if isinstance(flags.get("heartbeat_telemetry"), dict)
        else {}
    )
    return top, bool(top) and top == mirrored


def budget_evidence(response: Any) -> dict[str, Any]:
    reply = response if isinstance(response, dict) else {}
    budget, mirror_match = _budget_object(reply)
    option = budget.get("effective_max_heartbeats_option")
    counter = budget.get("effective_max_heartbeats_counter")
    unlimited = budget.get("unlimited")
    consumed = budget.get("consumed_heartbeats_counter")
    episode_max = budget.get("episode_max_heartbeats_counter")
    episode_remaining = budget.get("episode_remaining_heartbeats_counter")
    source = budget.get("source")
    episode_source = budget.get("episode_source")
    measurement_scope = budget.get("measurement_scope")
    reset_scope = budget.get("reset_scope")
    if _is_int(option) and option == 0:
        cap_consistent = unlimited is True and counter is None
    else:
        cap_consistent = (
            _is_int(option)
            and option > 0
            and _is_int(counter)
            and counter == option * 1000
            and unlimited is False
        )
    audit = reply.get("audit") if isinstance(reply.get("audit"), dict) else {}
    top_heartbeats = reply.get("heartbeats")
    audit_heartbeats = audit.get("heartbeats")
    heartbeats_match = (
        _is_int(consumed)
        and consumed >= 0
        and _is_int(top_heartbeats)
        and _is_int(audit_heartbeats)
        and top_heartbeats == consumed
        and audit_heartbeats == consumed
    )
    required_strings = isinstance(source, str) and bool(source.strip())
    scope_values_valid = (
        episode_source == "task"
        and measurement_scope == "action_corem_toio_counter"
        and reset_scope == "per_corem_toio_call"
    )
    episode_valid = (
        episode_max == EPISODE_MAX_HEARTBEATS_COUNTER
        and _is_int(episode_remaining)
        and 0 <= episode_remaining <= EPISODE_MAX_HEARTBEATS_COUNTER
    )
    return {
        "passed": bool(
            mirror_match
            and cap_consistent
            and heartbeats_match
            and required_strings
            and scope_values_valid
            and episode_valid
        ),
        "mirror_match": mirror_match,
        "cap_consistent": cap_consistent,
        "heartbeats_match": heartbeats_match,
        "episode_valid": episode_valid,
        "scope_values_valid": scope_values_valid,
        "effective_max_heartbeats_option": option,
        "effective_max_heartbeats_counter": counter,
        "unlimited": unlimited,
        "source": source,
        "consumed_heartbeats_counter": consumed,
        "episode_max_heartbeats_counter": episode_max,
        "episode_remaining_heartbeats_counter": episode_remaining,
        "episode_source": episode_source,
        "measurement_scope": measurement_scope,
        "reset_scope": reset_scope,
    }


def cache_budget_probe() -> dict[str, Any]:
    base_task = {"task_id": "cache", "statement": "True", "imports": ["Lean"]}
    payloads = {
        "task_fallback": {
            "task": {**base_task, "max_heartbeats": TASK_MAX_HEARTBEATS_OPTION},
            "action": {"tactic": "trivial"},
        },
        "explicit_zero": {
            "task": {**base_task, "max_heartbeats": TASK_MAX_HEARTBEATS_OPTION},
            "action": {"tactic": "trivial", "max_heartbeats": 0},
        },
        "explicit_nonzero": {
            "task": {**base_task, "max_heartbeats": TASK_MAX_HEARTBEATS_OPTION},
            "action": {
                "tactic": "trivial",
                "max_heartbeats": CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
            },
        },
        "omitted_default": {"task": dict(base_task), "action": {"tactic": "trivial"}},
        "explicit_default": {
            "task": {**base_task, "max_heartbeats": RUNTIME_DEFAULT_MAX_HEARTBEATS_OPTION},
            "action": {"tactic": "trivial"},
        },
    }
    resolved = {name: _max_heartbeats(payload) for name, payload in payloads.items()}
    key_kwargs = {
        "lean_version": "uprime-cache-probe",
        "workdir_fingerprint_value": "uprime-cache-probe",
        "import_mode": "preserve",
        "trace_state": False,
        "lane": "kernel_rpc",
    }
    omitted_key, omitted_fields = make_audit_cache_key(
        payloads["omitted_default"], **key_kwargs
    )
    explicit_key, explicit_fields = make_audit_cache_key(
        payloads["explicit_default"], **key_kwargs
    )
    checks = {
        "task_fallback": resolved["task_fallback"] == str(TASK_MAX_HEARTBEATS_OPTION),
        "explicit_zero": resolved["explicit_zero"] == "0",
        "explicit_nonzero": resolved["explicit_nonzero"]
        == str(CONSTRUCTOR_MAX_HEARTBEATS_OPTION),
        "omitted_runtime_default": resolved["omitted_default"]
        == str(RUNTIME_DEFAULT_MAX_HEARTBEATS_OPTION),
        "omitted_equals_explicit_default_key": omitted_key == explicit_key,
        "omitted_equals_explicit_default_field": (
            omitted_fields.get("max_heartbeats")
            == explicit_fields.get("max_heartbeats")
            == str(RUNTIME_DEFAULT_MAX_HEARTBEATS_OPTION)
        ),
    }
    return {"passed": all(checks.values()), "resolved": resolved, "checks": checks}


def _new_shutdown_lifecycle() -> dict[str, Any]:
    return {
        "stream_complete": False,
        "shutdown_ack_ok": False,
        "shutdown_response_sha256": None,
        "post_response_timeout_s": POST_RESPONSE_TIMEOUT_S,
        "natural_exit_grace_s": NATURAL_EXIT_GRACE_S,
        "forced_reap_budget_s": FORCED_REAP_BUDGET_S,
        "reader_drain_reserve_s": READER_DRAIN_RESERVE_S,
        "exit_mode": None,
        "graceful_exit": None,
        "termination_signal_attempted": False,
        "kill_signal_attempted": False,
        "forced_reap": False,
        "forced_reap_succeeded": None,
        "reader_threads_drained": False,
        "stdout_eof_count": 0,
        "residual_response_count": 0,
        "residual_frame_kinds": [],
        "terminal_eof_exact": False,
        "transport_finalized": False,
        "post_response_elapsed_s": None,
    }


class _RpcProcess:
    def __init__(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout_s: float,
    ) -> None:
        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
            creationflags=creationflags,
        )
        self.deadline = time.monotonic() + max(1.0, float(timeout_s))
        self.stdout_queue: queue.Queue[
            tuple[str, Any, dict[str, Any] | None]
        ] = queue.Queue(maxsize=32)
        self.non_json_stdout: deque[str] = deque(maxlen=20)
        self.non_json_stdout_count = 0
        self.stderr_lines: deque[str] = deque(maxlen=40)
        self.stderr_count = 0
        self.transport_overflow = False
        self._cleanup_deadline: float | None = None
        self._post_response_started: float | None = None
        self._post_response_deadline: float | None = None
        self.shutdown_lifecycle = _new_shutdown_lifecycle()
        self._request_lock = threading.Lock()
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        stream = self.process.stdout
        if stream is None:
            self._queue_transport("eof", None, None)
            return
        for raw in iter(stream.readline, ""):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                self.non_json_stdout_count += 1
                self.non_json_stdout.append(line[-2000:])
                continue
            if isinstance(value, dict):
                received_monotonic_s = time.monotonic()
                self._queue_transport(
                    "response",
                    value,
                    {
                        "received_monotonic_s": received_monotonic_s,
                        "received_at_utc": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                self.non_json_stdout_count += 1
                self.non_json_stdout.append(line[-2000:])
        self._queue_transport("eof", None, None)

    def _queue_transport(
        self, kind: str, value: Any, receipt: dict[str, Any] | None
    ) -> None:
        try:
            self.stdout_queue.put_nowait((kind, value, receipt))
        except queue.Full:
            self.transport_overflow = True

    def _read_stderr(self) -> None:
        stream = self.process.stderr
        if stream is None:
            return
        for raw in iter(stream.readline, ""):
            self.stderr_count += 1
            self.stderr_lines.append(raw.rstrip("\r\n")[-2000:])

    def request(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self._request_lock:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                self._abort_for_timeout("U'1 RPC diagnostic whole-run timeout")
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"U'1 RPC worker exited before request: {self.process.returncode}"
                )
            stdin = self.process.stdin
            if stdin is None:
                raise RuntimeError("U'1 RPC worker stdin is unavailable")
            stdin.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
            stdin.flush()
            while True:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    self._abort_for_timeout("U'1 RPC diagnostic request timeout")
                try:
                    kind, value, receipt = self.stdout_queue.get(timeout=remaining)
                except queue.Empty as exc:
                    try:
                        self._abort_for_timeout("U'1 RPC diagnostic request timeout")
                    except TimeoutError as timeout_exc:
                        raise timeout_exc from exc
                if kind == "response":
                    if not isinstance(receipt, dict):
                        raise RuntimeError("U'1 RPC response receipt metadata was missing")
                    return value, receipt
                if kind == "eof":
                    raise RuntimeError(
                        "U'1 RPC worker closed stdout before returning a response"
                    )

    def _force_reap_after_shutdown(self) -> None:
        post_deadline = self._post_response_deadline
        if post_deadline is None:
            raise RuntimeError("U'1 post-response deadline was not initialized")
        now = time.monotonic()
        force_deadline = min(
            now + FORCED_REAP_BUDGET_S,
            post_deadline - READER_DRAIN_RESERVE_S,
        )
        if force_deadline <= now:
            raise TimeoutError("U'1 RPC post-response forced-reap budget was exhausted")

        lifecycle = self.shutdown_lifecycle
        lifecycle["forced_reap"] = True
        lifecycle["forced_reap_succeeded"] = False
        lifecycle["termination_signal_attempted"] = True
        try:
            self.process.terminate()
        except OSError:
            pass
        terminate_wait = min(TERMINATE_GRACE_S, force_deadline - time.monotonic())
        if terminate_wait > 0:
            try:
                self.process.wait(timeout=terminate_wait)
                lifecycle["exit_mode"] = "forced_terminate"
            except subprocess.TimeoutExpired:
                pass

        if self.process.poll() is None:
            lifecycle["kill_signal_attempted"] = True
            try:
                self.process.kill()
            except OSError:
                pass
            remaining = force_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("U'1 RPC post-response forced-reap deadline expired")
            try:
                self.process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(
                    "U'1 RPC worker survived bounded post-response forced reap"
                ) from exc
            lifecycle["exit_mode"] = "forced_kill"

        if self.process.poll() is None:
            raise TimeoutError("U'1 RPC worker remained alive after forced reap")
        lifecycle["forced_reap_succeeded"] = True

    def _join_transport_readers(self) -> None:
        post_deadline = self._post_response_deadline
        if post_deadline is None:
            raise RuntimeError("U'1 post-response deadline was not initialized")
        for thread in (self._stdout_thread, self._stderr_thread):
            remaining = post_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("U'1 RPC post-response reader deadline expired")
            thread.join(timeout=remaining)
        readers_drained = not (
            self._stdout_thread.is_alive() or self._stderr_thread.is_alive()
        )
        self.shutdown_lifecycle["reader_threads_drained"] = readers_drained
        if not readers_drained:
            raise RuntimeError("U'1 RPC transport reader did not terminate cleanly")

    def finalize_after_shutdown(
        self, response: dict[str, Any], *, received_monotonic_s: float
    ) -> None:
        if self.shutdown_lifecycle["stream_complete"]:
            raise RuntimeError("U'1 RPC shutdown lifecycle was finalized twice")
        started = float(received_monotonic_s)
        observed_now = time.monotonic()
        if not math.isfinite(started) or started > observed_now:
            raise RuntimeError("U'1 RPC shutdown receipt clock was invalid")
        self._post_response_started = started
        self._post_response_deadline = started + POST_RESPONSE_TIMEOUT_S
        self._cleanup_deadline = self._post_response_deadline
        lifecycle = self.shutdown_lifecycle
        lifecycle["stream_complete"] = True
        lifecycle["shutdown_ack_ok"] = bool(
            response.get("ok") is True
            and response.get("shutdown") is True
            and response.get("error") is None
        )
        lifecycle["shutdown_response_sha256"] = _stable_json_sha256(response)

        try:
            natural_returncode_error: int | None = None
            natural_deadline = started + NATURAL_EXIT_GRACE_S
            natural_remaining = natural_deadline - time.monotonic()
            if natural_remaining <= 0:
                returncode = self.process.poll()
                if returncode is None:
                    self._force_reap_after_shutdown()
                    returncode = self.process.poll()
                else:
                    lifecycle["exit_mode"] = "natural_after_grace"
                    lifecycle["graceful_exit"] = False
            else:
                try:
                    returncode = self.process.wait(timeout=natural_remaining)
                except subprocess.TimeoutExpired:
                    returncode = self.process.poll()
                    if returncode is None:
                        self._force_reap_after_shutdown()
                        returncode = self.process.poll()
                    else:
                        lifecycle["exit_mode"] = "natural_after_grace"
                        lifecycle["graceful_exit"] = False
                else:
                    if time.monotonic() <= natural_deadline:
                        lifecycle["exit_mode"] = "natural"
                        lifecycle["graceful_exit"] = True
                    else:
                        lifecycle["exit_mode"] = "natural_after_grace"
                        lifecycle["graceful_exit"] = False

            if lifecycle["forced_reap"] is not True and returncode != 0:
                natural_returncode_error = returncode
            if lifecycle["forced_reap"] is True:
                lifecycle["graceful_exit"] = False

            self._join_transport_readers()
            self.assert_transport_drained()
            if self.transport_overflow:
                raise RuntimeError(
                    "U'1 RPC transport produced unsolicited response overflow"
                )
            if self.non_json_stdout:
                raise RuntimeError("U'1 RPC transport emitted non-JSON stdout")
            if natural_returncode_error is not None:
                raise RuntimeError(
                    "U'1 RPC worker exited naturally with return code "
                    f"{natural_returncode_error}"
                )
            if lifecycle["forced_reap"] is True and lifecycle["shutdown_ack_ok"] is not True:
                raise RuntimeError(
                    "U'1 RPC invalid shutdown response required forced process reap"
                )
        finally:
            lifecycle["post_response_elapsed_s"] = max(
                0.0, time.monotonic() - started
            )
        if lifecycle["post_response_elapsed_s"] > POST_RESPONSE_TIMEOUT_S:
            raise TimeoutError("U'1 RPC post-response deadline expired")
        lifecycle["transport_finalized"] = True

    def abort(self) -> None:
        if self.process.poll() is not None:
            return
        if self._cleanup_deadline is None:
            self._cleanup_deadline = time.monotonic() + 5.0
        cleanup_deadline = self._cleanup_deadline
        if cleanup_deadline <= time.monotonic():
            try:
                self.process.kill()
            except OSError:
                pass
            raise TimeoutError("U'1 RPC worker cleanup deadline expired")
        try:
            self.process.terminate()
        except OSError:
            pass
        first_wait = min(2.5, cleanup_deadline - time.monotonic())
        if first_wait <= 0:
            raise TimeoutError("U'1 RPC worker cleanup deadline expired")
        try:
            self.process.wait(timeout=first_wait)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            self.process.kill()
        except OSError:
            pass
        remaining = cleanup_deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("U'1 RPC worker cleanup deadline expired")
        self.process.wait(timeout=remaining)

    def _abort_for_timeout(self, message: str) -> None:
        cleanup_message = ""
        try:
            self.abort()
        except BaseException as cleanup_exc:
            cleanup_message = (
                f"; cleanup failed with {type(cleanup_exc).__name__}: {cleanup_exc}"
            )
        raise TimeoutError(message + cleanup_message)

    def transport_summary(self) -> dict[str, Any]:
        return {
            "returncode": self.process.poll(),
            "transport_overflow": self.transport_overflow,
            "non_json_stdout_count": self.non_json_stdout_count,
            "non_json_stdout_tail": list(self.non_json_stdout),
            "stderr_count": self.stderr_count,
            "stderr_tail": list(self.stderr_lines),
            "shutdown_lifecycle": dict(self.shutdown_lifecycle),
        }

    def assert_transport_drained(self) -> None:
        residual: list[tuple[str, Any, dict[str, Any] | None]] = []
        while True:
            try:
                residual.append(self.stdout_queue.get_nowait())
            except queue.Empty:
                break
        kinds = [kind for kind, _value, _receipt in residual]
        eof_count = sum(kind == "eof" for kind in kinds)
        response_count = sum(kind == "response" for kind in kinds)
        lifecycle = self.shutdown_lifecycle
        lifecycle["stdout_eof_count"] = eof_count
        lifecycle["residual_response_count"] = response_count
        lifecycle["residual_frame_kinds"] = kinds
        lifecycle["terminal_eof_exact"] = bool(
            len(residual) == 1
            and residual[0][0] == "eof"
            and residual[0][1] is None
        )
        if lifecycle["terminal_eof_exact"] is not True:
            raise RuntimeError(
                "U'1 RPC transport had unsolicited or missing terminal frames: "
                f"{kinds}"
            )


def _find_lean_binary(explicit: str | None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            if not candidate.is_file():
                raise FileNotFoundError(f"--lean-bin is not a file: {candidate}")
            return str(candidate.resolve())
        found_explicit = shutil.which(explicit)
        if found_explicit:
            return str(Path(found_explicit).resolve())
        raise FileNotFoundError(f"--lean-bin was not found: {explicit}")
    frozen = (
        Path.home()
        / ".elan"
        / "toolchains"
        / "leanprover--lean4---v4.31.0"
        / "bin"
        / ("lean.exe" if os.name == "nt" else "lean")
    )
    if frozen.exists():
        return str(frozen.resolve())
    found = shutil.which("lean")
    if found:
        return str(Path(found).resolve())
    for candidate in (
        Path.home() / ".elan" / "bin" / "lean.exe",
        Path.home() / ".elan" / "bin" / "lean",
    ):
        if candidate.exists():
            return str(candidate.resolve())
    raise FileNotFoundError("Lean executable was not found; pass --lean-bin")


def _lean_version(lean_bin: str, repo_root: Path) -> str:
    proc = subprocess.run(
        [lean_bin, "--version"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    text = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0 or not text:
        raise RuntimeError(f"Lean --version failed with return code {proc.returncode}")
    version = text.splitlines()[0][:500]
    if not version.startswith(EXPECTED_LEAN_VERSION_PREFIX):
        raise RuntimeError(
            "U'1 diagnostic requires leanprover/lean4:v4.31.0; "
            f"observed {version!r}"
        )
    return version


def _task(task_id: str, statement: str, *, prefix: str = "") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "statement": statement,
        "imports": ["Lean"],
        "prefix": prefix,
        "max_heartbeats": TASK_MAX_HEARTBEATS_OPTION,
        "episode_max_heartbeats_counter": EPISODE_MAX_HEARTBEATS_COUNTER,
    }


def _kernel(response: dict[str, Any], which: str = "current") -> dict[str, Any]:
    field = {
        "before": "kernel_state_before",
        "after": "kernel_state_after",
        "current": "kernel_state",
    }[which]
    value = response.get(field)
    return value if isinstance(value, dict) else {}


def _state_id(response: dict[str, Any], *, after: bool = False) -> str:
    if after and isinstance(response.get("after_state_id"), str):
        return response["after_state_id"]
    state = response.get("state") if isinstance(response.get("state"), dict) else {}
    value = state.get("state_id")
    if not isinstance(value, str) or not value:
        raise RuntimeError("RPC response did not contain a usable state_id")
    return value


def _goal_ids(response: dict[str, Any], which: str = "current") -> list[str]:
    return list(state_view(_kernel(response, which))["goals"])


def select_side_effect_target(kernel_state: Any) -> str:
    goals = (
        kernel_state.get("goals")
        if isinstance(kernel_state, dict) and isinstance(kernel_state.get("goals"), list)
        else None
    )
    if not (
        isinstance(goals, list)
        and len(goals) == 2
        and all(
            isinstance(row, dict)
            and isinstance(row.get("mvar_id"), str)
            and bool(row.get("mvar_id"))
            for row in goals
        )
        and goals[0]["mvar_id"] != goals[1]["mvar_id"]
    ):
        raise RuntimeError(
            "side-effect fixture must expose exactly two distinct ordered goal rows"
        )
    return goals[1]["mvar_id"]


def _response_summary(
    response: dict[str, Any], receipt: dict[str, Any] | None = None
) -> dict[str, Any]:
    kernel = _kernel(response, "after") or _kernel(response, "current")
    flags = _audit_flags(response)
    replay = flags.get("replay") if isinstance(flags.get("replay"), dict) else {}
    budget = response.get("budget") if isinstance(response.get("budget"), dict) else None
    state_delta = (
        response.get("state_delta")
        if isinstance(response.get("state_delta"), dict)
        else None
    )
    response_sha256 = _stable_json_sha256(response)
    receipt_sha256 = receipt.get("response_sha256") if receipt else None
    return {
        "response_sha256": response_sha256,
        "receipt_response_sha256": receipt_sha256,
        "receipt_sha256_match": receipt_sha256 is not None
        and receipt_sha256 == response_sha256,
        "frame_index": receipt.get("frame_index") if receipt else None,
        "received_at_utc": receipt.get("received_at_utc") if receipt else None,
        "id": response.get("id"),
        "rpc_protocol_version": response.get("rpc_protocol_version"),
        "ok": response.get("ok"),
        "loaded": response.get("loaded"),
        "shutdown": response.get("shutdown"),
        "n_states": response.get("n_states"),
        "n_requests": response.get("n_requests"),
        "n_failures": response.get("n_failures"),
        "status": response.get("status"),
        "error": response.get("error"),
        "before_state_id": response.get("before_state_id"),
        "after_state_id": response.get("after_state_id"),
        "state_view": state_view(kernel),
        "state_option_maxHeartbeats": (
            kernel.get("options", {}).get("maxHeartbeats")
            if isinstance(kernel.get("options"), dict)
            else None
        ),
        "state_delta": state_delta,
        "replay": replay,
        "budget": budget,
        "heartbeats": response.get("heartbeats"),
    }


def shutdown_transport_clear_gate(
    shutdown_response: Any, transport: Any
) -> dict[str, Any]:
    response = shutdown_response if isinstance(shutdown_response, dict) else {}
    summary = transport if isinstance(transport, dict) else {}
    lifecycle = (
        summary.get("shutdown_lifecycle")
        if isinstance(summary.get("shutdown_lifecycle"), dict)
        else {}
    )
    elapsed = lifecycle.get("post_response_elapsed_s")
    elapsed_bound = bool(
        isinstance(elapsed, (int, float))
        and not isinstance(elapsed, bool)
        and math.isfinite(float(elapsed))
        and 0.0 <= float(elapsed) <= POST_RESPONSE_TIMEOUT_S
        and lifecycle.get("post_response_timeout_s") == POST_RESPONSE_TIMEOUT_S
    )
    checks = {
        "stream_complete": lifecycle.get("stream_complete") is True,
        "shutdown_ack_ok": lifecycle.get("shutdown_ack_ok") is True,
        "response_sha256_bound": bool(response)
        and lifecycle.get("shutdown_response_sha256")
        == _stable_json_sha256(response),
        "natural_exit_within_grace": lifecycle.get("graceful_exit") is True
        and lifecycle.get("exit_mode") == "natural",
        "no_forced_reap": lifecycle.get("forced_reap") is False,
        "returncode_zero": summary.get("returncode") == 0,
        "reader_threads_drained": lifecycle.get("reader_threads_drained") is True,
        "terminal_eof_exact": lifecycle.get("terminal_eof_exact") is True,
        "no_transport_overflow": summary.get("transport_overflow") is False,
        "json_stdout_only": summary.get("non_json_stdout_count") == 0,
        "post_response_elapsed_bounded": elapsed_bound,
        "transport_finalized": lifecycle.get("transport_finalized") is True,
    }
    if tuple(checks) != TRANSPORT_CLEAR_CHECK_IDS:
        raise AssertionError("U'1 transport clear check registry drifted")
    return {
        "gate_id": TRANSPORT_CLEAR_GATE_ID,
        "passed": all(checks.values()),
        "checks": checks,
    }


def diagnostic_disposition(
    contracts: dict[str, dict[str, Any]], transport_gate: dict[str, Any]
) -> dict[str, Any]:
    if tuple(contracts) != CONTRACT_IDS:
        raise ValueError("U'1 contract registry is incomplete, reordered, or extended")
    if not all(isinstance(row, dict) for row in contracts.values()):
        raise TypeError("U'1 contract rows must be objects")
    gate_checks = transport_gate.get("checks")
    if (
        transport_gate.get("gate_id") != TRANSPORT_CLEAR_GATE_ID
        or not isinstance(gate_checks, dict)
        or tuple(gate_checks) != TRANSPORT_CLEAR_CHECK_IDS
        or not all(isinstance(value, bool) for value in gate_checks.values())
    ):
        raise ValueError("U'1 transport clear gate registry is invalid")
    derived_gate_pass = all(value is True for value in gate_checks.values())
    if transport_gate.get("passed") is not derived_gate_pass:
        raise ValueError("U'1 transport clear gate summary contradicts its checks")
    contract_failures = [
        name for name, row in contracts.items() if row.get("passed") is not True
    ]
    failures = list(contract_failures)
    if transport_gate.get("passed") is not True:
        failures.append(TRANSPORT_CLEAR_GATE_ID)
    return {
        "contract_failures": contract_failures,
        "failures": failures,
        "verdict": "U1_DIAGNOSTIC_CLEAR" if not failures else "U1_DIAGNOSTIC_BLOCKED",
    }


def _run_sequence(
    rpc: _RpcProcess,
    responses: dict[str, dict[str, Any]],
    request_ids: dict[str, str],
    response_receipts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    requested_state_ids: dict[str, str] = {}
    replay_specs: dict[str, dict[str, Any]] = {}

    def send(label: str, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = f"uprime-{len(request_ids) + 1:02d}-{label}"
        request_ids[label] = request_id
        reply, receipt = rpc.request({"id": request_id, **payload})
        responses[label] = reply
        response_receipts[label] = {
            **receipt,
            "frame_index": len(request_ids),
            "response_sha256": _stable_json_sha256(reply),
        }
        return reply

    def send_action(
        label: str,
        *,
        state_id: str,
        action: dict[str, Any],
        target_mvar_id: str | None = None,
        replay: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "cmd": "apply_tactic",
            "state_id": state_id,
            "action": action,
        }
        if target_mvar_id is not None:
            payload["target_mvar_id"] = target_mvar_id
        requested_state_ids[label] = state_id
        reply = send(label, payload)
        if replay:
            replay_label = f"{label}_replay"
            expected_after_state_id = reply.get("after_state_id")
            replay_payload: dict[str, Any] = {
                "cmd": "replay_transition",
                "before_state_id": state_id,
                "expected_after_state_id": expected_after_state_id,
                "action": action,
            }
            if target_mvar_id is not None:
                replay_payload["target_mvar_id"] = target_mvar_id
            send(replay_label, replay_payload)
            replay_specs[label] = {
                "replay_label": replay_label,
                "before_state_id": state_id,
                "expected_after_state_id": expected_after_state_id,
                "action_id": action.get("action_id"),
                "target_mvar_id": target_mvar_id,
            }
        return reply

    send("load", {"cmd": "load_project", "imports": ["Lean"]})

    primary_init = send(
        "primary_init",
        {"cmd": "init_state", "task": _task("uprime_primary", "True ∧ True")},
    )
    primary_split = send_action(
        "primary_split",
        state_id=_state_id(primary_init),
        action={
            "action_id": "primary_constructor",
            "tactic": "constructor",
            "max_heartbeats": CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
        },
    )
    primary_goals = _goal_ids(primary_split, "after")
    if len(primary_goals) != 2:
        raise RuntimeError("constructor did not expose exactly two primary goals")
    primary_head, primary_tail = primary_goals
    primary_tail_close = send_action(
        "primary_tail_close",
        state_id=_state_id(primary_split, after=True),
        target_mvar_id=primary_tail,
        action={
            "action_id": "primary_tail_exact",
            "tactic": "exact True.intro",
        },
    )
    send_action(
        "primary_head_close",
        state_id=_state_id(primary_tail_close, after=True),
        target_mvar_id=primary_head,
        action={
            "action_id": "primary_head_exact",
            "tactic": "exact True.intro",
        },
    )

    zero_init = send(
        "zero_init",
        {"cmd": "init_state", "task": _task("uprime_zero", "True ∧ True")},
    )
    zero_split = send_action(
        "zero_split",
        state_id=_state_id(zero_init),
        action={
            "action_id": "zero_constructor",
            "tactic": "constructor",
            "max_heartbeats": 0,
        },
    )
    zero_goals = _goal_ids(zero_split, "after")
    if len(zero_goals) != 2:
        raise RuntimeError("constructor did not expose exactly two zero-chain goals")
    send_action(
        "zero_child_close",
        state_id=_state_id(zero_split, after=True),
        target_mvar_id=zero_goals[1],
        action={
            "action_id": "zero_child_exact",
            "tactic": "exact True.intro",
        },
    )

    side_init = send(
        "side_init",
        {
            "cmd": "init_state",
            "task": _task(
                "uprime_side_effect",
                "∃ n : Nat, n = 0",
                prefix="refine ⟨?_, ?_⟩",
            ),
        },
    )
    side_kernel = _kernel(side_init)
    side_goals = _goal_ids(side_init)
    side_equality_goal = select_side_effect_target(side_kernel)
    send_action(
        "side_effect_close",
        state_id=_state_id(side_init),
        target_mvar_id=side_equality_goal,
        action={"action_id": "side_effect_rfl", "tactic": "rfl"},
    )

    burn_init = send(
        "burn_init",
        {"cmd": "init_state", "task": _task("uprime_burn", "True")},
    )
    send_action(
        "burn",
        state_id=_state_id(burn_init),
        replay=False,
        action={
            "action_id": "burn",
            "tactic": (
                f'run_tac do IO.addHeartbeats {BURN_COUNTER_INCREMENT}; '
                'Lean.Core.checkMaxHeartbeats "uprime-litmus"'
            ),
            "max_heartbeats": BURN_MAX_HEARTBEATS_OPTION,
        },
    )
    reset_init = send(
        "reset_init",
        {"cmd": "init_state", "task": _task("uprime_reset", "True")},
    )
    send_action(
        "reset",
        state_id=_state_id(reset_init),
        action={
            "action_id": "reset_trivial",
            "tactic": "trivial",
            "max_heartbeats": BURN_MAX_HEARTBEATS_OPTION,
        },
    )
    send("status", {"cmd": "status"})
    shutdown_response = send("shutdown", {"cmd": "shutdown"})
    rpc.finalize_after_shutdown(
        shutdown_response,
        received_monotonic_s=response_receipts["shutdown"]["received_monotonic_s"],
    )
    return {
        "primary_head": primary_head,
        "primary_tail": primary_tail,
        "zero_goals": zero_goals,
        "side_goals": side_goals,
        "side_equality_goal": side_equality_goal,
        "side_target_selector": "refine_tuple_position_1",
        "requested_state_ids": requested_state_ids,
        "replay_specs": replay_specs,
    }


def _state_option(response: dict[str, Any], which: str = "current") -> int | None:
    kernel = _kernel(response, which)
    options = kernel.get("options") if isinstance(kernel.get("options"), dict) else {}
    value = options.get("maxHeartbeats")
    if _is_int(value):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _status_ok(response: dict[str, Any]) -> bool:
    status = response.get("status")
    after = state_structure(_kernel(response, "after"))
    goals = after["view"]["goals"]
    status_matches_goals = (status == "success" and not goals) or (
        status == "partial" and bool(goals)
    )
    return response.get("ok") is True and after["passed"] and status_matches_goals


def replay_evidence(
    primary_response: Any,
    replay_response: Any,
    *,
    before_state_id: str,
    expected_after_state_id: str,
    action_id: str,
    target_mvar_id: str | None,
) -> dict[str, Any]:
    primary = primary_response if isinstance(primary_response, dict) else {}
    replay = replay_response if isinstance(replay_response, dict) else {}
    certificate = (
        replay.get("replay_certificate")
        if isinstance(replay.get("replay_certificate"), dict)
        else {}
    )
    actual_before = primary.get("kernel_state_before")
    actual_after = primary.get("kernel_state_after")
    actual_delta = primary.get("state_delta")
    replay_before = replay.get("kernel_state_before")
    replay_expected = replay.get("kernel_state_expected")
    replay_observed = replay.get("kernel_state_observed")
    delta_expected = replay.get("state_delta_expected")
    delta_observed = replay.get("state_delta_observed")
    checks = {
        "primary_delta_valid": delta_evidence(primary)["passed"],
        "replay_response_ok": replay.get("ok") is True,
        "before_state_id": replay.get("before_state_id") == before_state_id,
        "expected_after_state_id": replay.get("expected_after_state_id")
        == expected_after_state_id,
        "action_id": replay.get("action_id") == action_id,
        "target_mvar_id": replay.get("target_mvar_id") == target_mvar_id,
        "state_table_unchanged": _is_int(replay.get("n_states_before"))
        and replay.get("n_states_before") == replay.get("n_states_after"),
        "independent_execution_measured": replay.get("reexecution_performed") is True
        and _is_int(replay.get("reexecution_heartbeats_counter"))
        and replay.get("reexecution_heartbeats_counter") > 0
        and replay.get("reexecution_scope")
        == "fresh_from_immutable_before_state",
        "before_state_bound": isinstance(actual_before, dict)
        and replay_before == actual_before,
        "expected_state_bound": isinstance(actual_after, dict)
        and replay_expected == actual_after,
        "independent_state_match": isinstance(replay_observed, dict)
        and replay_observed == actual_after,
        "expected_delta_bound": isinstance(actual_delta, dict)
        and delta_expected == actual_delta,
        "independent_delta_match": isinstance(delta_observed, dict)
        and delta_observed == actual_delta,
        "schema_version": certificate.get("schema_version")
        == REPLAY_CERTIFICATE_VERSION,
        "verification_method": certificate.get("verification_method")
        == REPLAY_VERIFICATION_METHOD,
        "replay_status": certificate.get("replay_status") == "verified",
        "state_match": certificate.get("state_match") is True,
        "delta_match": certificate.get("delta_match") is True,
        "error_is_null": certificate.get("error") is None,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "certificate": {
            key: certificate.get(key)
            for key in (
                "schema_version",
                "verification_method",
                "replay_status",
                "state_match",
                "delta_match",
                "error",
            )
        },
        "state_sha256": {
            "primary_after": (
                _stable_json_sha256(actual_after)
                if isinstance(actual_after, dict)
                else None
            ),
            "replay_expected": (
                _stable_json_sha256(replay_expected)
                if isinstance(replay_expected, dict)
                else None
            ),
            "replay_observed": (
                _stable_json_sha256(replay_observed)
                if isinstance(replay_observed, dict)
                else None
            ),
        },
        "delta_sha256": {
            "primary": (
                _stable_json_sha256(actual_delta)
                if isinstance(actual_delta, dict)
                else None
            ),
            "replay_expected": (
                _stable_json_sha256(delta_expected)
                if isinstance(delta_expected, dict)
                else None
            ),
            "replay_observed": (
                _stable_json_sha256(delta_observed)
                if isinstance(delta_observed, dict)
                else None
            ),
        },
    }


def evaluate_contracts(
    responses: dict[str, dict[str, Any]],
    request_ids: dict[str, str],
    context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    action_labels = (
        "primary_split",
        "primary_tail_close",
        "primary_head_close",
        "zero_split",
        "zero_child_close",
        "side_effect_close",
        "burn",
        "reset",
    )
    delta_labels = tuple(label for label in action_labels if label != "burn")
    init_labels = ("primary_init", "zero_init", "side_init", "burn_init", "reset_init")

    request_echo = {
        label: {
            "id_match": responses.get(label, {}).get("id") == request_id,
            "protocol_match": responses.get(label, {}).get("rpc_protocol_version")
            == RPC_PROTOCOL_VERSION,
        }
        for label, request_id in request_ids.items()
    }
    b0_rows = {
        label: {
            "ok": responses.get(label, {}).get("ok") is True,
            "state_well_formed": state_structure(
                _kernel(responses.get(label, {}), "current")
            )["passed"],
            "summary_kernel_state_id_match": (
                isinstance(responses.get(label, {}).get("state"), dict)
                and responses[label]["state"].get("state_id")
                == _kernel(responses.get(label, {}), "current").get("state_id")
            ),
            "max_heartbeats_option": _state_option(responses.get(label, {})),
        }
        for label in init_labels
    }
    budget_rows = {
        label: budget_evidence(responses.get(label, {})) for label in action_labels
    }
    expected_budgets = {
        "primary_split": (CONSTRUCTOR_MAX_HEARTBEATS_OPTION, "action"),
        "primary_tail_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "primary_head_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "zero_split": (0, "action"),
        "zero_child_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "side_effect_close": (TASK_MAX_HEARTBEATS_OPTION, "task"),
        "burn": (BURN_MAX_HEARTBEATS_OPTION, "action"),
        "reset": (BURN_MAX_HEARTBEATS_OPTION, "action"),
    }
    for label, (expected_option, expected_source) in expected_budgets.items():
        row = budget_rows[label]
        consumed = row.get("consumed_heartbeats_counter")
        effective_counter = row.get("effective_max_heartbeats_counter")
        if expected_option == 0:
            execution_bound_match = row.get("unlimited") is True
        elif label == "burn":
            execution_bound_match = _is_int(consumed) and _is_int(effective_counter)
        else:
            execution_bound_match = (
                _is_int(consumed)
                and _is_int(effective_counter)
                and consumed <= effective_counter
            )
        row["request_match"] = (
            row.get("effective_max_heartbeats_option") == expected_option
            and row.get("source") == expected_source
            and execution_bound_match
        )
        row["expected_request"] = {
            "effective_max_heartbeats_option": expected_option,
            "source": expected_source,
            "successful_consumption_within_cap": label != "burn",
        }
    delta_rows = {
        label: delta_evidence(responses.get(label, {})) for label in delta_labels
    }
    replay_specs = (
        context.get("replay_specs")
        if isinstance(context.get("replay_specs"), dict)
        else {}
    )
    replay_rows: dict[str, dict[str, Any]] = {}
    for label in delta_labels:
        spec = replay_specs.get(label) if isinstance(replay_specs.get(label), dict) else {}
        replay_rows[label] = replay_evidence(
            responses.get(label, {}),
            responses.get(str(spec.get("replay_label") or ""), {}),
            before_state_id=str(spec.get("before_state_id") or ""),
            expected_after_state_id=str(spec.get("expected_after_state_id") or ""),
            action_id=str(spec.get("action_id") or ""),
            target_mvar_id=(
                spec.get("target_mvar_id")
                if isinstance(spec.get("target_mvar_id"), str)
                else None
            ),
        )
    cache_probe = cache_budget_probe()
    requested_state_ids = (
        context.get("requested_state_ids")
        if isinstance(context.get("requested_state_ids"), dict)
        else {}
    )
    predecessor_labels = {
        "primary_split": ("primary_init", "current"),
        "primary_tail_close": ("primary_split", "after"),
        "primary_head_close": ("primary_tail_close", "after"),
        "zero_split": ("zero_init", "current"),
        "zero_child_close": ("zero_split", "after"),
        "side_effect_close": ("side_init", "current"),
        "burn": ("burn_init", "current"),
        "reset": ("reset_init", "current"),
    }
    continuity_checks = {
        label: {
            "requested_state_id_match": isinstance(requested_state_ids.get(label), str)
            and responses.get(label, {}).get("before_state_id")
            == requested_state_ids.get(label),
            "before_kernel_matches_predecessor": responses.get(label, {}).get(
                "kernel_state_before"
            )
            == _kernel(
                responses.get(predecessor_labels[label][0], {}),
                predecessor_labels[label][1],
            ),
        }
        for label in action_labels
    }

    primary_tail_after = state_view(
        _kernel(responses.get("primary_tail_close", {}), "after")
    )
    primary_head_after = state_view(
        _kernel(responses.get("primary_head_close", {}), "after")
    )
    primary_tail_delta = delta_rows.get("primary_tail_close", {}).get("expected", {})
    target_routing_checks = {
        "target_action_succeeded": _status_ok(responses.get("primary_tail_close", {})),
        "target_delta_valid": delta_rows.get("primary_tail_close", {}).get("passed")
        is True,
        "only_original_head_remains": primary_tail_after["goals"]
        == [context.get("primary_head")],
        "target_tail_newly_assigned": context.get("primary_tail")
        in primary_tail_delta.get("assigned_mvars", []),
        "target_tail_closed": context.get("primary_tail")
        in primary_tail_delta.get("closed_goals", []),
        "final_action_succeeded": _status_ok(responses.get("primary_head_close", {})),
        "final_delta_valid": delta_rows.get("primary_head_close", {}).get("passed")
        is True,
        "final_goals_empty": primary_head_after["goals"] == [],
    }
    zero_child_after = state_view(
        _kernel(responses.get("zero_child_close", {}), "after")
    )
    zero_child_delta = delta_rows.get("zero_child_close", {}).get("expected", {})
    zero_goals = context.get("zero_goals") if isinstance(context.get("zero_goals"), list) else []
    target_routing_checks.update(
        {
            "zero_target_action_succeeded": _status_ok(
                responses.get("zero_child_close", {})
            ),
            "zero_only_original_head_remains": len(zero_goals) == 2
            and zero_child_after["goals"] == [zero_goals[0]],
            "zero_target_tail_assigned": len(zero_goals) == 2
            and zero_goals[1] in zero_child_delta.get("assigned_mvars", []),
            "zero_target_tail_closed": len(zero_goals) == 2
            and zero_goals[1] in zero_child_delta.get("closed_goals", []),
        }
    )

    b1_checks = {
        "nonzero_override_effective": budget_rows["primary_split"].get(
            "effective_max_heartbeats_option"
        )
        == CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
        "nonzero_child_keeps_task_baseline": _state_option(
            responses.get("primary_split", {}), "after"
        )
        == TASK_MAX_HEARTBEATS_OPTION,
        "nonzero_descendant_returns_to_task": budget_rows["primary_tail_close"].get(
            "effective_max_heartbeats_option"
        )
        == TASK_MAX_HEARTBEATS_OPTION
        and budget_rows["primary_tail_close"].get("source") == "task",
        "zero_override_is_unlimited": budget_rows["zero_split"].get(
            "effective_max_heartbeats_option"
        )
        == 0
        and budget_rows["zero_split"].get("unlimited") is True,
        "zero_child_keeps_task_baseline": _state_option(
            responses.get("zero_split", {}), "after"
        )
        == TASK_MAX_HEARTBEATS_OPTION,
        "zero_descendant_returns_to_task": budget_rows["zero_child_close"].get(
            "effective_max_heartbeats_option"
        )
        == TASK_MAX_HEARTBEATS_OPTION
        and budget_rows["zero_child_close"].get("source") == "task",
    }

    side_response = responses.get("side_effect_close", {})
    side_after = state_view(_kernel(side_response, "after"))
    side_delta = independent_delta(
        side_response.get("kernel_state_before"), side_response.get("kernel_state_after")
    )
    side_goal_set = set(context.get("side_goals", []))
    side_checks = {
        "selector_frozen": context.get("side_target_selector")
        == "refine_tuple_position_1",
        "selected_second_goal": isinstance(context.get("side_goals"), list)
        and len(context["side_goals"]) == 2
        and context.get("side_equality_goal") == context["side_goals"][1],
        "action_succeeded": _status_ok(side_response),
        "delta_valid": delta_rows.get("side_effect_close", {}).get("passed") is True,
        "after_goals_empty": side_after["goals"] == [],
        "both_goals_newly_assigned": set(side_delta["assigned_mvars"]) == side_goal_set,
        "both_goals_closed": set(side_delta["closed_goals"]) == side_goal_set,
        "all_after_states_well_formed": all(
            state_structure(_kernel(responses.get(label, {}), "after"))["passed"]
            for label in action_labels
        ),
    }

    control_checks = {
        "frame_label_registry": len(request_ids)
        == len(responses)
        == len(EXPECTED_RESPONSE_LABELS)
        and set(request_ids) == set(responses) == set(EXPECTED_RESPONSE_LABELS),
        "request_ids_unique": len(set(request_ids.values()))
        == len(EXPECTED_RESPONSE_LABELS)
        and all(isinstance(value, str) and bool(value) for value in request_ids.values()),
        "load_ok": responses.get("load", {}).get("ok") is True
        and responses.get("load", {}).get("loaded") is True,
        "status_ok": responses.get("status", {}).get("ok") is True
        and responses.get("status", {}).get("loaded") is True
        and responses.get("status", {}).get("n_states")
        == EXPECTED_PERSISTENT_STATE_COUNT
        and responses.get("status", {}).get("n_requests")
        == EXPECTED_STATUS_REQUEST_COUNT,
        "shutdown_ok": responses.get("shutdown", {}).get("ok") is True
        and responses.get("shutdown", {}).get("shutdown") is True,
    }
    burn_response = responses.get("burn", {})
    burn_audit = (
        burn_response.get("audit")
        if isinstance(burn_response.get("audit"), dict)
        else {}
    )
    burn_before = _kernel(burn_response, "before")
    burn_after = _kernel(burn_response, "after")
    burn_consumed = budget_rows["burn"].get("consumed_heartbeats_counter")
    burn_checks = {
        "response_ok": burn_response.get("ok") is True,
        "status_timeout": burn_response.get("status") == "timeout",
        "audit_status_timeout": burn_audit.get("status") == "timeout",
        "requested_state_continuity": all(continuity_checks["burn"].values()),
        "delta_valid": delta_evidence(burn_response)["passed"],
        "semantic_state_unchanged": state_view(burn_before) == state_view(burn_after),
        "normalized_hash_unchanged": burn_before.get("state_hash_norm")
        == burn_after.get("state_hash_norm"),
        "consumption_exceeds_finite_cap": _is_int(burn_consumed)
        and burn_consumed > BURN_MAX_HEARTBEATS_OPTION * 1000,
        "budget_valid": budget_rows["burn"]["passed"]
        and budget_rows["burn"]["request_match"],
        "reset_success": _status_ok(responses.get("reset", {})),
        "reset_budget_valid": budget_rows["reset"]["passed"]
        and budget_rows["reset"]["request_match"],
    }

    episode_groups = {
        "primary": ("primary_split", "primary_tail_close", "primary_head_close"),
        "zero": ("zero_split", "zero_child_close"),
        "side": ("side_effect_close",),
        "burn": ("burn",),
        "reset": ("reset",),
    }
    episode_checks: dict[str, Any] = {}
    for group, labels in episode_groups.items():
        rows = [budget_rows[label] for label in labels]
        remaining = [row.get("episode_remaining_heartbeats_counter") for row in rows]
        consumed = [row.get("consumed_heartbeats_counter") for row in rows]
        expected_remaining: list[int] = []
        running_remaining = EPISODE_MAX_HEARTBEATS_COUNTER
        consumed_valid = all(_is_int(value) and value >= 0 for value in consumed)
        if consumed_valid:
            for value in consumed:
                running_remaining = max(0, running_remaining - value)
                expected_remaining.append(running_remaining)
        episode_checks[group] = {
            "registered_limit": all(
                row.get("episode_max_heartbeats_counter")
                == EPISODE_MAX_HEARTBEATS_COUNTER
                for row in rows
            ),
            "source_present": all(
                row.get("episode_source") == "task"
                for row in rows
            ),
            "remaining_monotone": all(_is_int(value) for value in remaining)
            and all(left >= right for left, right in zip(remaining, remaining[1:])),
            "accounting_exact": consumed_valid and remaining == expected_remaining,
            "consumed": consumed,
            "expected_remaining": expected_remaining,
            "remaining": remaining,
        }
    episode_passed = all(
        row["registered_limit"]
        and row["source_present"]
        and row["remaining_monotone"]
        and row["accounting_exact"]
        for row in episode_checks.values()
    )

    contracts = {
        "R0_request_id_echo": {
            "passed": all(all(row.values()) for row in request_echo.values())
            and all(control_checks.values()),
            "evidence": {"envelopes": request_echo, "controls": control_checks},
        },
        "B0_task_budget_init": {
            "passed": all(
                row["ok"]
                and row["state_well_formed"]
                and row["summary_kernel_state_id_match"]
                and row["max_heartbeats_option"] == TASK_MAX_HEARTBEATS_OPTION
                for row in b0_rows.values()
            ),
            "evidence": b0_rows,
        },
        "B1_action_budget_nonsticky": {
            "passed": all(b1_checks.values()),
            "evidence": b1_checks,
        },
        "B2_budget_telemetry": {
            "passed": all(
                row["passed"] and row["request_match"] for row in budget_rows.values()
            ),
            "evidence": budget_rows,
        },
        "B3_enforcement_reset": {
            "passed": all(burn_checks.values()),
            "evidence": burn_checks,
        },
        "B4_cache_budget_semantics": {
            "passed": cache_probe["passed"],
            "evidence": cache_probe,
        },
        "D0_target_routing": {
            "passed": all(target_routing_checks.values()),
            "evidence": target_routing_checks,
        },
        "D1_transition_delta": {
            "passed": all(
                _status_ok(responses.get(label, {}))
                and delta_rows[label]["passed"]
                and all(continuity_checks[label].values())
                for label in delta_labels
            ),
            "evidence": {
                "delta": delta_rows,
                "requested_state_continuity": continuity_checks,
            },
        },
        "D2_all_goal_sweep": {
            "passed": all(side_checks.values()),
            "evidence": side_checks,
        },
        "R1_independent_replay": {
            "passed": all(row["passed"] for row in replay_rows.values()),
            "evidence": replay_rows,
        },
        "E0_episode_budget": {
            "passed": episode_passed,
            "evidence": episode_checks,
        },
    }
    if tuple(contracts) != CONTRACT_IDS:
        raise AssertionError("contract registry drifted from the frozen preregistration")
    return contracts


def run_diagnostic(
    repo_root: str | Path,
    *,
    anchor: str,
    timeout_s: float = 900.0,
    lean_bin: str | None = None,
    reservation_path: str | Path | None = None,
    reservation_token: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if not math.isfinite(float(timeout_s)) or float(timeout_s) != FROZEN_TIMEOUT_S:
        raise ValueError(f"--timeout-s must equal the frozen value {FROZEN_TIMEOUT_S:g}")
    _assert_git_top_level(root)
    commit = _git_commit(root)
    clean_anchor = str(anchor).strip().lower()
    if len(clean_anchor) != 12 or not commit.lower().startswith(clean_anchor):
        raise ValueError("--anchor must be the 12-character prefix of current HEAD")
    _assert_anchor_inputs_clean(root)
    upstream = _assert_anchor_pushed(root, commit)
    reject_canonical_rerun_bootstrap(root, commit)
    if reservation_path is None or not reservation_token:
        raise RuntimeError("U'1 live diagnostic requires a preclaimed canonical artifact")
    canonical_reservation = (
        root / REGISTERED_RUN_DIR / f"rpc_diagnostic_{clean_anchor}.json"
    ).resolve()
    if Path(reservation_path).resolve() != canonical_reservation:
        raise RuntimeError(
            f"U'1 reservation must use the canonical artifact {canonical_reservation}"
        )
    reservation = _verify_reservation(
        Path(reservation_path).resolve(),
        token=reservation_token,
        anchor=clean_anchor,
        commit=commit,
    )

    responses: dict[str, dict[str, Any]] = {}
    request_ids: dict[str, str] = {}
    response_receipts: dict[str, dict[str, Any]] = {}
    context: dict[str, Any] = {}
    rpc: _RpcProcess | None = None
    worker_snapshot_dir: tempfile.TemporaryDirectory[str] | None = None
    cleanup_errors: list[dict[str, str]] = []
    started = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_UPRIME_RPC_LITMUS,
        "anchor_commit": commit,
        "anchor_upstream": upstream,
        "reservation": {
            "schema_version": reservation["schema_version"],
            "path": (
                REGISTERED_RUN_DIR
                / f"rpc_diagnostic_{clean_anchor}.json.reservation"
            ).as_posix(),
            "reserved_at_utc": reservation["reserved_at_utc"],
            "token_sha256": hashlib.sha256(reservation_token.encode("ascii")).hexdigest().upper(),
        },
        "started_at_utc": started.isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "frozen_parameters": {
            "task_max_heartbeats_option": TASK_MAX_HEARTBEATS_OPTION,
            "task_max_heartbeats_counter": TASK_MAX_HEARTBEATS_OPTION * 1000,
            "episode_max_heartbeats_counter": EPISODE_MAX_HEARTBEATS_COUNTER,
            "constructor_max_heartbeats_option": CONSTRUCTOR_MAX_HEARTBEATS_OPTION,
            "constructor_max_heartbeats_counter": CONSTRUCTOR_MAX_HEARTBEATS_OPTION
            * 1000,
            "burn_max_heartbeats_option": BURN_MAX_HEARTBEATS_OPTION,
            "burn_max_heartbeats_counter": BURN_MAX_HEARTBEATS_OPTION * 1000,
            "burn_counter_increment": BURN_COUNTER_INCREMENT,
            "rpc_protocol_version": RPC_PROTOCOL_VERSION,
            "timeout_s": float(timeout_s),
            "post_response_timeout_s": POST_RESPONSE_TIMEOUT_S,
            "natural_exit_grace_s": NATURAL_EXIT_GRACE_S,
            "forced_reap_budget_s": FORCED_REAP_BUDGET_S,
            "reader_drain_reserve_s": READER_DRAIN_RESERVE_S,
            "terminate_grace_s": TERMINATE_GRACE_S,
        },
        "licenses_later_stage": False,
    }
    try:
        if platform.system() != "Windows":
            raise RuntimeError("U'1 diagnostic is frozen to the Windows CPU lane")
        executable = _find_lean_binary(lean_bin)
        binary_sha256 = _sha256(Path(executable))
        if binary_sha256 != EXPECTED_LEAN_BINARY_SHA256:
            raise RuntimeError(
                "U'1 diagnostic Lean executable digest mismatch: "
                f"expected {EXPECTED_LEAN_BINARY_SHA256}, observed {binary_sha256}"
            )
        version = _lean_version(executable, root)
        source_records, head_blobs = _anchored_input_snapshot(root)
        worker_snapshot_dir = tempfile.TemporaryDirectory(prefix="uprime_rpc_head_")
        worker_snapshot_path = Path(worker_snapshot_dir.name) / RPC_PATH.name
        worker_snapshot_path.write_bytes(head_blobs[RPC_PATH])
        report["lean"] = {
            "binary_name": Path(executable).name,
            "binary_sha256": binary_sha256,
            "version": version,
            "command_shape": [
                "lean",
                "--run",
                f"HEAD:{RPC_PATH.as_posix()}",
                "--imports",
                "Lean",
            ],
        }
        report["anchor_inputs"] = source_records
        rpc = _RpcProcess(
            [executable, "--run", str(worker_snapshot_path), "--imports", "Lean"],
            cwd=root,
            timeout_s=timeout_s,
        )
        context = _run_sequence(rpc, responses, request_ids, response_receipts)
        post_records, _post_blobs = _anchored_input_snapshot(root)
        if _git_commit(root) != commit or post_records != source_records:
            raise RuntimeError("anchored inputs or HEAD changed during live execution")
        report["anchor_inputs_post_execution"] = post_records
        contracts = evaluate_contracts(responses, request_ids, context)
        transport_gate = shutdown_transport_clear_gate(
            responses.get("shutdown"), rpc.transport_summary()
        )
        disposition = diagnostic_disposition(contracts, transport_gate)
        report.update(
            {
                "context": context,
                "requests": request_ids,
                "response_count": len(responses),
                "responses": {
                    label: _response_summary(response, response_receipts.get(label))
                    for label, response in responses.items()
                },
                "contracts": contracts,
                "contract_failures": disposition["contract_failures"],
                "transport_clear_gate": transport_gate,
                "failures": disposition["failures"],
                "verdict": disposition["verdict"],
            }
        )
    except BaseException as exc:
        if rpc is not None:
            try:
                rpc.abort()
            except BaseException as cleanup_exc:
                cleanup_errors.append(
                    {"type": type(cleanup_exc).__name__, "message": str(cleanup_exc)[:2000]}
                )
        report.update(
            {
                "context": context,
                "requests": request_ids,
                "response_count": len(responses),
                "responses": {
                    label: _response_summary(response, response_receipts.get(label))
                    for label, response in responses.items()
                },
                "contracts": {},
                "failures": ["HARNESS_ERROR"],
                "harness_error": {
                    "type": type(exc).__name__,
                    "message": str(exc)[:4000],
                },
                "verdict": "HARNESS_ERROR",
            }
        )
    finally:
        if rpc is not None:
            if rpc.process.poll() is None:
                try:
                    rpc.abort()
                except BaseException as cleanup_exc:
                    cleanup_errors.append(
                        {
                            "type": type(cleanup_exc).__name__,
                            "message": str(cleanup_exc)[:2000],
                        }
                    )
            report["transport"] = rpc.transport_summary()
        if worker_snapshot_dir is not None:
            try:
                worker_snapshot_dir.cleanup()
            except BaseException as cleanup_exc:
                cleanup_errors.append(
                    {"type": type(cleanup_exc).__name__, "message": str(cleanup_exc)[:2000]}
                )
        if cleanup_errors:
            report["cleanup_errors"] = cleanup_errors
            if report.get("verdict") != "HARNESS_ERROR":
                report["failures"] = ["HARNESS_ERROR"]
                report["harness_error"] = {
                    "type": "CleanupError",
                    "message": "one or more cleanup operations failed",
                }
                report["verdict"] = "HARNESS_ERROR"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["elapsed_seconds"] = max(
            0.0, (datetime.now(timezone.utc) - started).total_seconds()
        )
    return report


def _reserve_output(
    path: Path,
    *,
    repo_root: Path,
    anchor: str,
    commit: str,
) -> str:
    # Defense in depth for import-level callers.  The bootstrap assertion always
    # denies; activation must replace it with validation of one claimed receipt.
    reject_canonical_rerun_bootstrap(repo_root, commit)
    path.parent.mkdir(parents=True, exist_ok=True)
    reservation_path = _reservation_file(path)
    token = secrets.token_hex(32)
    reservation = {
        "schema_version": SCHEMA_UPRIME_RPC_RESERVATION,
        "status": "LIVE_EXECUTION_RESERVED",
        "anchor": anchor,
        "anchor_commit": commit,
        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        "process_id": os.getpid(),
        "final_artifact_name": path.name,
        "token": token,
    }
    with reservation_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(reservation, indent=2, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return token


def _reservation_file(path: Path) -> Path:
    return path.with_name(f"{path.name}.reservation")


def _verify_reservation(
    path: Path,
    *,
    token: str,
    anchor: str,
    commit: str,
) -> dict[str, Any]:
    reservation_path = _reservation_file(path)
    try:
        reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("canonical artifact reservation is unreadable") from exc
    if not (
        isinstance(reservation, dict)
        and reservation.get("schema_version") == SCHEMA_UPRIME_RPC_RESERVATION
        and reservation.get("status") == "LIVE_EXECUTION_RESERVED"
        and reservation.get("anchor") == anchor
        and reservation.get("anchor_commit") == commit
        and reservation.get("final_artifact_name") == path.name
        and reservation.get("token") == token
    ):
        raise RuntimeError("canonical artifact reservation does not match this run")
    return reservation


def _publish_reserved_json(
    path: Path,
    value: dict[str, Any],
    *,
    repo_root: Path,
    token: str,
    anchor: str,
    commit: str,
) -> None:
    # A canonical path is not publication authority on its own.
    reject_canonical_rerun_bootstrap(repo_root, commit)
    _verify_reservation(path, token=token, anchor=anchor, commit=commit)
    if path.exists():
        raise FileExistsError(f"refusing to replace canonical U'1 artifact: {path}")
    serialized = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    temp_path = path.with_name(f".{path.name}.{token}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        _verify_reservation(path, token=token, anchor=anchor, commit=commit)
        os.link(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the anchored U'1 single-process native RPC diagnostic"
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout-s", type=float, default=FROZEN_TIMEOUT_S)
    parser.add_argument("--lean-bin")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    clean_anchor = str(args.anchor).strip().lower()
    expected_out = (root / REGISTERED_RUN_DIR / f"rpc_diagnostic_{clean_anchor}.json").resolve()
    if out != expected_out:
        raise ValueError(f"registered U'1 artifact path must be exactly {expected_out}")
    if out.exists() or _reservation_file(out).exists():
        raise FileExistsError(
            f"refusing to overwrite or reuse registered U'1 artifact: {out}"
        )
    if not math.isfinite(float(args.timeout_s)) or float(args.timeout_s) != FROZEN_TIMEOUT_S:
        raise ValueError(f"--timeout-s must equal the frozen value {FROZEN_TIMEOUT_S:g}")
    _assert_git_top_level(root)
    commit = _git_commit(root)
    if len(clean_anchor) != 12 or not commit.lower().startswith(clean_anchor):
        raise ValueError("--anchor must be the 12-character prefix of current HEAD")
    _assert_anchor_inputs_clean(root)
    _assert_anchor_pushed(root, commit)
    reject_canonical_rerun_bootstrap(root, commit)
    reservation_token = _reserve_output(
        out,
        repo_root=root,
        anchor=clean_anchor,
        commit=commit,
    )
    try:
        report = run_diagnostic(
            args.repo_root,
            anchor=clean_anchor,
            timeout_s=args.timeout_s,
            lean_bin=args.lean_bin,
            reservation_path=out,
            reservation_token=reservation_token,
        )
    except BaseException as exc:
        report = {
            "schema_version": SCHEMA_UPRIME_RPC_LITMUS,
            "anchor_commit": commit,
            "failures": ["HARNESS_ERROR"],
            "harness_error": {
                "type": type(exc).__name__,
                "message": str(exc)[:4000],
            },
            "verdict": "HARNESS_ERROR",
            "licenses_later_stage": False,
        }
    _publish_reserved_json(
        out,
        report,
        repo_root=root,
        token=reservation_token,
        anchor=clean_anchor,
        commit=commit,
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "anchor_commit": report["anchor_commit"],
                "verdict": report["verdict"],
                "failures": report["failures"],
                "licenses_later_stage": report["licenses_later_stage"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 2 if report["verdict"] == "HARNESS_ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
