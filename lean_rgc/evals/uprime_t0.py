from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Hashable


SCHEMA_UPRIME_T0 = "lean-rgc-uprime-t0-errata-v1.0"
T0_FLOAT_TOLERANCE = 1e-12
ERRATA_PATH = Path("docs/experiments/uprime_odlrq_theory_errata_2026-07-10.md")
PREREG_PATH = Path("docs/experiments/uprime_odlrq_t0_extension_preregistration.md")
SOURCE_PATH = Path("lean_rgc/evals/uprime_t0.py")
TEST_PATH = Path("tests/test_uprime_t0_errata.py")
MODEL_BOUND_FIXTURE_PATH = Path(
    "docs/experiments/fixtures/uprime_t0_model_bound_fixture.json"
)


def _fraction(value: Fraction) -> dict[str, int | float]:
    return {
        "numerator": int(value.numerator),
        "denominator": int(value.denominator),
        "float": float(value),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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
        raise RuntimeError("T0 requires an anchored Git commit")
    return commit


def _assert_anchor_inputs_clean(repo_root: Path) -> None:
    paths = (ERRATA_PATH, PREREG_PATH, SOURCE_PATH, TEST_PATH, MODEL_BOUND_FIXTURE_PATH)
    for path in paths:
        tracked = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{path.as_posix()}"],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if tracked.returncode != 0:
            raise RuntimeError(f"T0 anchor input is not committed: {path.as_posix()}")
    proc = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *(path.as_posix() for path in paths)],
        cwd=repo_root,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("T0 anchor inputs differ from the committed HEAD")


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
        raise RuntimeError("T0 anchor branch has no configured upstream")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, upstream],
        cwd=repo_root,
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("T0 anchor commit is not present on its upstream")
    return upstream


def _nonfinite_paths(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, float):
        return [] if math.isfinite(value) else [path]
    if isinstance(value, dict):
        return [
            failure
            for key, child in value.items()
            for failure in _nonfinite_paths(child, f"{path}.{key}")
        ]
    if isinstance(value, (list, tuple)):
        return [
            failure
            for index, child in enumerate(value)
            for failure in _nonfinite_paths(child, f"{path}[{index}]")
        ]
    return []


def _model_error_admissible(
    record: dict[str, Any] | None,
    artifact_path: Path | None,
) -> bool:
    if not isinstance(record, dict):
        return False
    required = ("artifact_sha256", "bound", "domain", "norm")
    if any(key not in record for key in required):
        return False
    digest = record.get("artifact_sha256")
    bound = record.get("bound")
    domain = record.get("domain")
    norm = record.get("norm")
    if not (
        isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdefABCDEF" for character in digest)
        and isinstance(bound, (int, float))
        and not isinstance(bound, bool)
        and math.isfinite(float(bound))
        and float(bound) >= 0.0
        and isinstance(domain, str)
        and bool(domain.strip())
        and isinstance(norm, str)
        and bool(norm.strip())
        and isinstance(artifact_path, Path)
    ):
        return False
    try:
        artifact_bytes = artifact_path.read_bytes()
        artifact = json.loads(artifact_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(artifact, dict):
        return False
    return (
        hashlib.sha256(artifact_bytes).hexdigest().lower() == digest.lower()
        and artifact.get("schema_version") == "lean-rgc-uprime-t0-model-bound-v1.0"
        and artifact.get("domain") == domain
        and artifact.get("norm") == norm
        and artifact.get("bound") == bound
        and bool(artifact.get("provenance"))
    )


def weighted_probe() -> dict[str, Any]:
    amplitude = Fraction(10)
    omega_source = Fraction(100)
    omega_target = Fraction(1)
    envelope = abs(amplitude) * omega_target / omega_source
    legacy_gain = amplitude
    amended_gain = omega_target * amplitude / omega_source

    positive_amplitude = Fraction(3)
    positive_envelope = abs(positive_amplitude)
    positive_gain = positive_amplitude
    return {
        "probe_id": "T0-W",
        "legacy_envelope": _fraction(envelope),
        "legacy_gain": _fraction(legacy_gain),
        "amended_gain": _fraction(amended_gain),
        "legacy_counterexample_detected": abs(legacy_gain) > envelope,
        "amended_negative_handled": abs(amended_gain) <= envelope,
        "amended_positive_fixture_passed": abs(positive_gain) <= positive_envelope,
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


def _max_gap(
    states: list[tuple[int, int]],
    left: dict[tuple[int, int], Fraction],
    right: dict[tuple[int, int], Fraction],
) -> Fraction:
    return max(abs(left[state] - right[state]) for state in states)


def _conditionally_independent(
    states: list[tuple[int, int]],
    left: Callable[[tuple[int, int]], Hashable],
    right: Callable[[tuple[int, int]], Hashable],
    given: Callable[[tuple[int, int]], Hashable],
) -> bool:
    given_values = {given(state) for state in states}
    for g in given_values:
        fiber = [state for state in states if given(state) == g]
        n = len(fiber)
        left_values = {left(state) for state in fiber}
        right_values = {right(state) for state in fiber}
        for a in left_values:
            for b in right_values:
                joint = Fraction(sum(left(s) == a and right(s) == b for s in fiber), n)
                p_left = Fraction(sum(left(s) == a for s in fiber), n)
                p_right = Fraction(sum(right(s) == b for s in fiber), n)
                if joint != p_left * p_right:
                    return False
    return True


def projection_probe() -> dict[str, Any]:
    states = [(x, y) for x in (0, 1) for y in (0, 1)]
    values = {state: Fraction(1 if state[0] else -1) for state in states}
    by_x = lambda state: state[0]
    by_y = lambda state: state[1]
    by_xy = lambda state: state
    constant = lambda _state: 0

    direct = _conditional_expectation(states, values, by_x)
    via_y = _conditional_expectation(states, values, by_y)
    adjacent = _conditional_expectation(states, via_y, by_x)
    factorization_gap = _max_gap(states, direct, adjacent)

    p_x = _conditional_expectation(states, values, by_x)
    p_y = _conditional_expectation(states, values, by_y)
    written_left = _conditional_expectation(states, p_x, by_xy)
    written_right = _conditional_expectation(states, p_y, by_xy)
    written_gap = _max_gap(states, written_left, written_right)
    tower_left_holds = _max_gap(states, written_left, p_x) == 0
    tower_right_holds = _max_gap(states, written_right, p_y) == 0

    negative_markov = _conditionally_independent(states, by_x, by_x, by_y)
    positive_direct = _conditional_expectation(states, values, constant)
    positive_mid = _conditional_expectation(states, values, by_x)
    positive_adjacent = _conditional_expectation(states, positive_mid, constant)
    positive_markov = _conditionally_independent(states, by_xy, constant, by_x)
    positive_gap = _max_gap(states, positive_direct, positive_adjacent)

    return {
        "probe_id": "T0-P",
        "factorization_gap": _fraction(factorization_gap),
        "written_contextual_gap": _fraction(written_gap),
        "negative_markov_hypothesis_holds": negative_markov,
        "nested_positive_gap": _fraction(positive_gap),
        "legacy_counterexample_detected": factorization_gap > 0 and written_gap > 0,
        "amended_negative_handled": (
            not negative_markov and tower_left_holds and tower_right_holds
        ),
        "amended_positive_fixture_passed": positive_markov and positive_gap == 0,
    }


def covariance_probe() -> dict[str, Any]:
    correlated_full = Fraction(4)
    diagonal = Fraction(2)
    cross = Fraction(2)
    independent_full = Fraction(2)
    independent_cross = Fraction(0)
    return {
        "probe_id": "T0-C",
        "correlated_full_variance": _fraction(correlated_full),
        "diagonal_only_variance": _fraction(diagonal),
        "cross_contribution": _fraction(cross),
        "legacy_counterexample_detected": correlated_full != diagonal,
        "amended_negative_handled": correlated_full == diagonal + cross,
        "amended_positive_fixture_passed": (
            independent_full == diagonal + independent_cross
        ),
    }


def similarity_probe() -> dict[str, Any]:
    true_gap = Fraction(2)
    projected_distance = Fraction(0)
    residual_left = Fraction(1)
    residual_right = Fraction(1)
    transported_bound = residual_left + projected_distance + residual_right
    positive_true_gap = Fraction(1, 2)
    positive_projected_distance = Fraction(1, 2)
    return {
        "probe_id": "T0-S",
        "true_gap": _fraction(true_gap),
        "projected_distance": _fraction(projected_distance),
        "transported_bound": _fraction(transported_bound),
        "legacy_counterexample_detected": true_gap > projected_distance,
        "amended_negative_handled": true_gap <= transported_bound,
        "amended_positive_fixture_passed": (
            positive_true_gap <= positive_projected_distance
        ),
    }


def telescoping_probe() -> dict[str, Any]:
    a1 = Fraction(1)
    ahat1 = Fraction(0)
    a2 = Fraction(10)
    ahat2 = Fraction(10)
    composite_error = abs(a2 * a1 - ahat2 * ahat1)
    untransported_sum = abs(a1 - ahat1) + abs(a2 - ahat2)
    typed_bound = abs(a2) * abs(a1 - ahat1) + abs(a2 - ahat2) * abs(ahat1)
    missing_model_record: dict[str, Any] = {}
    model_artifact_path = Path(__file__).resolve().parents[2] / MODEL_BOUND_FIXTURE_PATH
    model_artifact = json.loads(model_artifact_path.read_text(encoding="utf-8"))
    valid_model_record = {
        "artifact_sha256": _sha256(model_artifact_path),
        "bound": model_artifact["bound"],
        "domain": model_artifact["domain"],
        "norm": model_artifact["norm"],
    }
    missing_model_provenance_rejected = not _model_error_admissible(
        missing_model_record,
        None,
    )
    valid_model_provenance_accepted = _model_error_admissible(
        valid_model_record,
        model_artifact_path,
    )

    positive_a1 = Fraction(2)
    positive_ahat1 = Fraction(1)
    positive_a2 = Fraction(3)
    positive_ahat2 = Fraction(4)
    positive_lhs = positive_a2 * positive_a1 - positive_ahat2 * positive_ahat1
    positive_rhs = (
        positive_a2 * (positive_a1 - positive_ahat1)
        + (positive_a2 - positive_ahat2) * positive_ahat1
    )
    positive_bound = (
        abs(positive_a2) * abs(positive_a1 - positive_ahat1)
        + abs(positive_a2 - positive_ahat2) * abs(positive_ahat1)
    )
    return {
        "probe_id": "T0-J",
        "composite_error": _fraction(composite_error),
        "untransported_stage_sum": _fraction(untransported_sum),
        "typed_telescoping_bound": _fraction(typed_bound),
        "missing_model_provenance_rejected": missing_model_provenance_rejected,
        "valid_model_provenance_accepted": valid_model_provenance_accepted,
        "valid_model_artifact": MODEL_BOUND_FIXTURE_PATH.as_posix(),
        "valid_model_artifact_sha256": valid_model_record["artifact_sha256"],
        "legacy_counterexample_detected": composite_error > untransported_sum,
        "amended_negative_handled": (
            composite_error <= typed_bound and missing_model_provenance_rejected
        ),
        "positive_telescoping_lhs": _fraction(positive_lhs),
        "positive_telescoping_rhs": _fraction(positive_rhs),
        "positive_telescoping_bound": _fraction(positive_bound),
        "amended_positive_fixture_passed": (
            positive_lhs == positive_rhs
            and abs(positive_lhs) <= positive_bound
            and valid_model_provenance_accepted
        ),
    }


def maxent_probe() -> dict[str, Any]:
    moment_a = Fraction(0)
    moment_b = Fraction(0)
    load_a = Fraction(1)
    load_b = Fraction(0)
    operator_gap = abs(load_a - load_b)
    eta = Fraction(1, 2)
    residual_bound = 2 * eta

    supported_statistics = [Fraction(0), Fraction(1)]
    outside_moment = Fraction(2)
    outside_hull_rejected = not (
        min(supported_statistics) <= outside_moment <= max(supported_statistics)
    )
    boundary_moment = Fraction(0)
    boundary_finite_parameter_rejected = not (
        min(supported_statistics) < boundary_moment < max(supported_statistics)
    )
    duplicate_hessian = (
        (Fraction(1, 4), Fraction(1, 4)),
        (Fraction(1, 4), Fraction(1, 4)),
    )
    duplicate_determinant = (
        duplicate_hessian[0][0] * duplicate_hessian[1][1]
        - duplicate_hessian[0][1] * duplicate_hessian[1][0]
    )
    duplicate_singularity_detected = duplicate_determinant == 0

    atoms = ("a", "b")
    statistic = {"a": Fraction(1), "b": Fraction(0)}
    load = dict(statistic)
    positive_left_law = {"a": Fraction(3, 4), "b": Fraction(1, 4)}
    registered_moment = sum(positive_left_law[a] * statistic[a] for a in atoms)
    # On two atoms the indicator moment and total mass determine the law.
    positive_right_law = {"a": registered_moment, "b": 1 - registered_moment}
    positive_left_moment = sum(positive_left_law[a] * statistic[a] for a in atoms)
    positive_right_moment = sum(positive_right_law[a] * statistic[a] for a in atoms)
    positive_left_operator = sum(positive_left_law[a] * load[a] for a in atoms)
    positive_right_operator = sum(positive_right_law[a] * load[a] for a in atoms)
    positive_indicator_moment_gap = abs(positive_left_moment - positive_right_moment)
    positive_operator_gap = abs(positive_left_operator - positive_right_operator)
    positive_eta = max(abs(load[a] - statistic[a]) for a in atoms)
    return {
        "probe_id": "T0-ME",
        "constant_statistic_moment_gap": _fraction(abs(moment_a - moment_b)),
        "operator_gap": _fraction(operator_gap),
        "residual_span_bound": _fraction(residual_bound),
        "outside_hull_rejected": outside_hull_rejected,
        "boundary_finite_parameter_rejected": boundary_finite_parameter_rejected,
        "duplicate_hessian_singularity_detected": duplicate_singularity_detected,
        "positive_indicator_moment_gap": _fraction(positive_indicator_moment_gap),
        "positive_operator_gap": _fraction(positive_operator_gap),
        "positive_span_residual": _fraction(positive_eta),
        "legacy_counterexample_detected": moment_a == moment_b and operator_gap > 0,
        "amended_negative_handled": all(
            (
                operator_gap <= residual_bound,
                outside_hull_rejected,
                boundary_finite_parameter_rejected,
                duplicate_singularity_detected,
            )
        ),
        "amended_positive_fixture_passed": (
            positive_indicator_moment_gap == 0
            and positive_operator_gap <= 2 * positive_eta
        ),
    }


def finite_horizon_probe() -> dict[str, Any]:
    cosh_one = math.cosh(1.0)
    actual_error = cosh_one - 1.0
    refined_bound = cosh_one / 2.0
    finite_bound_holds = actual_error <= refined_bound + T0_FLOAT_TOLERANCE
    positive_decay_available = False  # D=0 in the registered fixture.
    infinite_horizon_refused = not positive_decay_available

    shift_edges = 4
    dimension = shift_edges + 1

    def apply_weighted_shift(vector: tuple[float, ...]) -> tuple[float, ...]:
        return (0.0, *(2.0 * vector[index] for index in range(dimension - 1)))

    shifted = (1.0, *(0.0 for _ in range(dimension - 1)))
    for _ in range(shift_edges):
        shifted = apply_weighted_shift(shifted)
    transient_gain = max(abs(value) for value in shifted)
    annihilated = apply_weighted_shift(shifted)
    nilpotent_verified = all(value == 0.0 for value in annihilated)
    spectral_radius = 0.0 if nilpotent_verified else float("nan")
    explicit_product_gain = float(math.prod([2] * shift_edges))
    spectral_shortcut_fails = spectral_radius == 0.0 and transient_gain > 1.0
    explicit_product_tracks_gain = (
        abs(transient_gain - explicit_product_gain) <= T0_FLOAT_TOLERANCE
    )
    finite_values = all(math.isfinite(x) for x in (actual_error, refined_bound, transient_gain))
    return {
        "probe_id": "T0-H",
        "absolute_tolerance": T0_FLOAT_TOLERANCE,
        "actual_error_at_T1": actual_error,
        "finite_horizon_bound_at_T1": refined_bound,
        "positive_decay_available": positive_decay_available,
        "nilpotent_shift_edges": shift_edges,
        "nilpotent_shift_dimension": dimension,
        "nilpotent_verified": nilpotent_verified,
        "nilpotent_shift_spectral_radius": spectral_radius,
        "nilpotent_shift_transient_gain": transient_gain,
        "legacy_counterexample_detected": spectral_shortcut_fails,
        "amended_negative_handled": finite_values and finite_bound_holds and infinite_horizon_refused,
        "amended_positive_fixture_passed": explicit_product_tracks_gain,
    }


PROBE_BUILDERS = (
    weighted_probe,
    projection_probe,
    covariance_probe,
    similarity_probe,
    telescoping_probe,
    maxent_probe,
    finite_horizon_probe,
)


def run_t0(repo_root: str | Path, *, anchor: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _git_commit(root)
    clean_anchor = str(anchor).strip().lower()
    if len(clean_anchor) != 12 or not commit.lower().startswith(clean_anchor):
        raise ValueError("--anchor must be the 12-character prefix of current HEAD")
    _assert_anchor_inputs_clean(root)
    upstream = _assert_anchor_pushed(root, commit)

    probes = [builder() for builder in PROBE_BUILDERS]
    required = (
        "legacy_counterexample_detected",
        "amended_negative_handled",
        "amended_positive_fixture_passed",
    )
    failures = [
        f"{probe['probe_id']}:{field}"
        for probe in probes
        for field in required
        if probe.get(field) is not True
    ]
    failures.extend(
        f"{probe['probe_id']}:non_finite:{path}"
        for probe in probes
        for path in _nonfinite_paths(probe)
    )
    return {
        "schema_version": SCHEMA_UPRIME_T0,
        "anchor_commit": commit,
        "anchor_upstream": upstream,
        "errata": {
            "path": ERRATA_PATH.as_posix(),
            "sha256": _sha256(root / ERRATA_PATH),
        },
        "preregistration": {
            "path": PREREG_PATH.as_posix(),
            "sha256": _sha256(root / PREREG_PATH),
        },
        "source": {
            "path": SOURCE_PATH.as_posix(),
            "sha256": _sha256(root / SOURCE_PATH),
            "test_path": TEST_PATH.as_posix(),
            "test_sha256": _sha256(root / TEST_PATH),
            "model_bound_fixture_path": MODEL_BOUND_FIXTURE_PATH.as_posix(),
            "model_bound_fixture_sha256": _sha256(root / MODEL_BOUND_FIXTURE_PATH),
        },
        "float_tolerance": T0_FLOAT_TOLERANCE,
        "probes": {probe["probe_id"]: probe for probe in probes},
        "failures": failures,
        "verdict": "T0_PASS" if not failures else "T0_FAIL",
        "licenses_next_repair_stage": not failures,
        "licenses_later_stage": False,
    }


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the anchored U' T0 errata probes")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    report = run_t0(args.repo_root, anchor=args.anchor)
    out = Path(args.out)
    if str(args.anchor).strip().lower() not in out.name.lower():
        raise ValueError("registered T0 artifact filename must contain --anchor")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite registered T0 artifact: {out}")
    _write_json(out, report)
    print(json.dumps({
        "out": str(out),
        "anchor_commit": report["anchor_commit"],
        "verdict": report["verdict"],
        "failures": report["failures"],
        "licenses_later_stage": report["licenses_later_stage"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
