from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Hashable

from ..audit_result_cache import workdir_fingerprint


SCHEMA_UPRIME_K0 = "lean-rgc-uprime-k0-foundation-v1.1"


def _fraction(value: Fraction) -> dict[str, int | float]:
    return {
        "numerator": int(value.numerator),
        "denominator": int(value.denominator),
        "float": float(value),
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _git_state(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        return (proc.stdout or proc.stderr or "").strip()

    status = run("status", "--short")
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "status_lines": status.splitlines(),
    }


def weighted_lifting_probe() -> dict[str, Any]:
    amplitude = Fraction(10)
    omega_source = Fraction(100)
    omega_target = Fraction(1)

    envelope = abs(amplitude) * omega_target / omega_source
    legacy_reduced_gain = amplitude
    corrected_reduced_gain = omega_target * amplitude / omega_source

    return {
        "probe_id": "K0-W",
        "inputs": {
            "amplitude": _fraction(amplitude),
            "omega_source": _fraction(omega_source),
            "omega_target": _fraction(omega_target),
            "lifting_probability": 1,
        },
        "weighted_envelope": _fraction(envelope),
        "legacy_reduced_gain": _fraction(legacy_reduced_gain),
        "legacy_claim_holds": abs(legacy_reduced_gain) <= envelope,
        "corrected_reduced_gain": _fraction(corrected_reduced_gain),
        "corrected_claim_holds": abs(corrected_reduced_gain) <= envelope,
        "legacy_counterexample_detected": abs(legacy_reduced_gain) > envelope,
    }


def _conditional_expectation(
    states: list[tuple[int, int]],
    values: dict[tuple[int, int], Fraction],
    label: Callable[[tuple[int, int]], Hashable],
) -> dict[tuple[int, int], Fraction]:
    grouped: dict[Hashable, list[Fraction]] = {}
    for state in states:
        grouped.setdefault(label(state), []).append(values[state])
    means = {
        key: sum(group, Fraction(0)) / len(group)
        for key, group in grouped.items()
    }
    return {state: means[label(state)] for state in states}


def projection_probe() -> dict[str, Any]:
    states = [(x, y) for x in (0, 1) for y in (0, 1)]
    x_value = {state: Fraction(1 if state[0] else -1) for state in states}
    by_x = lambda state: state[0]
    by_y = lambda state: state[1]
    by_xy = lambda state: state

    direct = _conditional_expectation(states, x_value, by_x)
    via_y = _conditional_expectation(states, x_value, by_y)
    chained = _conditional_expectation(states, via_y, by_x)

    p_v = _conditional_expectation(states, x_value, by_x)
    left = _conditional_expectation(states, p_v, by_xy)
    p_w = _conditional_expectation(states, x_value, by_y)
    right = _conditional_expectation(states, p_w, by_xy)

    direct_chain_gap = max(abs(direct[s] - chained[s]) for s in states)
    order_gap = max(abs(left[s] - right[s]) for s in states)
    return {
        "probe_id": "K0-P",
        "state_count": len(states),
        "direct_vs_adjacent_max_gap": _fraction(direct_chain_gap),
        "adjacent_product_identity_holds": direct_chain_gap == 0,
        "contextual_order_max_gap": _fraction(order_gap),
        "contextual_commutativity_holds": order_gap == 0,
        "legacy_counterexample_detected": direct_chain_gap > 0 and order_gap > 0,
    }


def covariance_probe() -> dict[str, Any]:
    # zeta_1 = zeta_2 = Z, with Z a centered Rademacher variable.
    full_variance = Fraction(4)
    diagonal_only_variance = Fraction(2)
    return {
        "probe_id": "K0-C",
        "full_variance": _fraction(full_variance),
        "diagonal_only_variance": _fraction(diagonal_only_variance),
        "diagonal_covariance_claim_holds": full_variance == diagonal_only_variance,
        "missing_cross_covariance": _fraction(full_variance - diagonal_only_variance),
        "legacy_counterexample_detected": full_variance != diagonal_only_variance,
    }


def environment_fingerprint_probe() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="uprime_k0_") as td:
        root = Path(td)
        (root / "lake-manifest.json").write_text('{"packages": []}', encoding="utf-8")
        (root / "lean-toolchain").write_text("leanprover/lean4:v4.31.0-rc1\n", encoding="utf-8")
        lib = root / ".lake" / "build" / "lib" / "lean"
        lib.mkdir(parents=True)
        olean = lib / "Main.olean"
        olean.write_bytes(b"semantic-content-v1")
        first = workdir_fingerprint(str(root))
        olean.write_bytes(b"semantic-content-v2")
        second = workdir_fingerprint(str(root))
    return {
        "probe_id": "K0-E",
        "mutation": "same path and module name, changed .olean bytes",
        "fingerprint_before": first,
        "fingerprint_after": second,
        "content_sensitive": first != second,
        "gate_F0a_cache_content_pass": first != second,
        "scope": "audit_result_cache local-build content litmus only; not full U'0/F0",
    }


def rpc_contract_probe(repo_root: Path) -> dict[str, Any]:
    rpc_path = repo_root / "lean_rgc" / "native_lean" / "RGCKernelRPC.lean"
    cache_path = repo_root / "lean_rgc" / "audit_result_cache.py"
    rpc = rpc_path.read_text(encoding="utf-8")
    cache = cache_path.read_text(encoding="utf-8")

    replay_pending_stub = 'if after.goals.isEmpty then "pending" else "pending"' in rpc
    heartbeat_null = '("heartbeats", Json.null)' in rpc
    assigned_cumulative = (
        "let assigned := beforeMvars.filter fun m => stepped.metaState.mctx.eAssignment.contains m"
        in rpc
    )
    tail_unswept = "let goals' := newGoalsHead ++ tail" in rpc
    runtime_action_only = 'jsonGetNat? action "max_heartbeats"' in rpc
    cache_task_fallback = 'value = task.get("max_heartbeats")' in cache

    return {
        "probe_id": "K0-R",
        "rpc_sha256": _sha256(rpc_path),
        "cache_sha256": _sha256(cache_path),
        "replay_verified_non_stub": not replay_pending_stub,
        "heartbeat_consumption_reported": not heartbeat_null,
        "assigned_mvars_is_before_after_difference": not assigned_cumulative,
        "tail_goals_swept_for_assignments": not tail_unswept,
        "budget_cache_runtime_semantics_aligned": not (
            runtime_action_only and cache_task_fallback
        ),
    }


def run_foundation_probe(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    weighted = weighted_lifting_probe()
    projection = projection_probe()
    covariance = covariance_probe()
    environment = environment_fingerprint_probe()
    rpc = rpc_contract_probe(root)

    legacy_math_counterexamples_detected = all(
        probe["legacy_counterexample_detected"]
        for probe in (weighted, projection, covariance)
    )
    current_blockers = [
        "T0_weighted_lifting_formula_unamended",
        "T0_projection_identities_unamended",
        "T0_diagonal_covariance_formula_unamended",
    ]
    if not environment["gate_F0a_cache_content_pass"]:
        current_blockers.append("F0a_audit_cache_digest_not_content_sensitive")
    for key in (
        "replay_verified_non_stub",
        "heartbeat_consumption_reported",
        "assigned_mvars_is_before_after_difference",
        "tail_goals_swept_for_assignments",
        "budget_cache_runtime_semantics_aligned",
    ):
        if not rpc[key]:
            current_blockers.append(key)

    return {
        "schema_version": SCHEMA_UPRIME_K0,
        "registration": "docs/experiments/uprime_odlrq_repair_preregistration.md",
        "repo_root": str(root),
        "git": _git_state(root),
        "probes": {
            "weighted_lifting": weighted,
            "projection": projection,
            "covariance": covariance,
            "environment_fingerprint": environment,
            "rpc_contract": rpc,
        },
        "legacy_math_counterexamples_detected": legacy_math_counterexamples_detected,
        "current_blockers": current_blockers,
        "verdict": "BLOCKED_AS_WRITTEN" if current_blockers else "K0_SOURCE_SMOKE_CLEAR",
        "licenses_later_stage": False,
        "scope_limitations": [
            "K0-R is a source-pattern smoke check, not a live RPC behavioral litmus.",
            "F1-F3 and M3-M4 are not covered by this executable.",
            "F0a covers the audit-result-cache local build only, not the shared environment/import closure.",
        ],
    }


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the registered U' K0 foundation probes")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--environment-out")
    args = parser.parse_args(argv)

    report = run_foundation_probe(args.repo_root)
    out = Path(args.out)
    _write_json(out, report)
    environment_out = (
        Path(args.environment_out)
        if args.environment_out
        else out.with_name("environment_fingerprint.json")
    )
    _write_json(environment_out, report["probes"]["environment_fingerprint"])
    print(json.dumps({
        "out": str(out),
        "environment_out": str(environment_out),
        "verdict": report["verdict"],
        "current_blockers": report["current_blockers"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
