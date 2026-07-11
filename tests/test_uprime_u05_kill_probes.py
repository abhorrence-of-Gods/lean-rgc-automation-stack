from __future__ import annotations

import builtins
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from lean_rgc.evals import uprime_u05_kill_probes as probes
from lean_rgc.odlrq.hankel import (
    build_hankel_cutoff,
    evaluate_hankel_probe,
    exact_rational_rank,
    hankel_dimensions,
)
from lean_rgc.odlrq.reachable_chart import (
    ChartLimits,
    ChartPrerequisiteBlocked,
    build_reachable_chart,
)
from lean_rgc.odlrq.rule_algebra import (
    TOTALIZATION_RULE_DIGEST,
    OracleEvent,
    OutcomeKind,
    StateView,
)


def _state(
    name: str,
    debt: tuple[int, int, int, int, int],
    live_id: str,
    *,
    response: str | None = None,
) -> StateView:
    return StateView(
        identity_key=name.encode("ascii"),
        full_signature=("signature:" + name).encode("ascii"),
        debt=debt,
        live_rpc_state_id=live_id,
        response_signature=(response or name).encode("ascii"),
    )


class _Oracle:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list[tuple[str, bytes, str]] = []

    def __call__(self, task_id: str, source: StateView, action_id: str):
        self.calls.append((task_id, source.identity_key, action_id))
        value = self.rows[(source.identity_key, action_id)]
        return value() if callable(value) else value


def _duplicate_chart():
    seed = _state("s0", (3, 3, 0, 1, 8), "live-s0")
    rows = {
        (b"s0", "a"): lambda: OracleEvent.open(
            b"s0", "a", _state("s1", (2, 2, 0, 1, 5), "live-s1-a")
        ),
        (b"s0", "b"): lambda: OracleEvent.open(
            b"s0", "b", _state("s1", (2, 2, 0, 1, 5), "live-s1-b")
        ),
        (b"s1", "a"): OracleEvent.closed(b"s1", "a"),
        (b"s1", "b"): OracleEvent.ordinary_failure(b"s1", "b"),
    }
    oracle = _Oracle(rows)
    released: list[tuple[str, str]] = []
    chart = build_reachable_chart(
        seeds={"unit_u05_duplicate": seed},
        actions=("b", "a"),
        oracle=oracle,
        limits=ChartLimits(max_depth=3),
        discard_live_state=lambda task, live: released.append((task, live)),
    )
    return chart, oracle, released


def test_three_tables_deduplicate_execution_but_retain_every_word_occurrence():
    chart, oracle, released = _duplicate_chart()

    assert chart.action_ids == ("a", "b")
    assert len(chart.state_table) == 2
    assert len(chart.transition_table) == 4
    assert len(oracle.calls) == 4
    assert all(
        event.target is None or event.target.live_rpc_state_id is None
        for event in chart.transition_table.values()
    )
    assert chart.word_occurrence_count == 1 + 2 + 4 + 8
    assert chart.word_table[("unit_u05_duplicate", ("a",))].state_key == b"s1"
    assert chart.word_table[("unit_u05_duplicate", ("b",))].state_key == b"s1"
    assert chart.word_table[("unit_u05_duplicate", ("a", "a", "b"))].kind is OutcomeKind.CLOSED
    assert chart.word_table[("unit_u05_duplicate", ("a", "a", "b"))].derived_terminal
    assert chart.word_table[("unit_u05_duplicate", ("a", "b", "a"))].kind is OutcomeKind.SINK
    assert chart.word_table[("unit_u05_duplicate", ("a", "b", "a"))].derived_terminal
    assert chart.peak_live_state_count == 3  # frontier plus one transient duplicate
    assert {live for _, live in released} >= {"live-s0", "live-s1-a", "live-s1-b"}

    closed_entry = chart.word_table[("unit_u05_duplicate", ("a", "a"))]
    closed_extension = chart.word_table[("unit_u05_duplicate", ("a", "a", "b"))]
    assert closed_entry.totalization_rule_digest == TOTALIZATION_RULE_DIGEST
    assert closed_entry.entry_task_id == "unit_u05_duplicate"
    assert closed_entry.entry_source_key == b"s1"
    assert closed_entry.entry_action_id == "a"
    assert closed_entry.entry_word == ("a", "a")
    assert closed_extension.totalization_rule_digest == closed_entry.totalization_rule_digest
    assert closed_extension.entry_word == closed_entry.entry_word
    assert closed_extension.entry_source_key == closed_entry.entry_source_key


def test_missing_open_response_evidence_blocks_before_kp1_can_report_zero_mismatch():
    seed = StateView(
        identity_key=b"missing-response",
        full_signature=b"signature:missing-response",
        debt=(1, 1, 0, 0, 2),
        live_rpc_state_id="missing-response-live",
        response_signature=b"",
    )
    with pytest.raises(ChartPrerequisiteBlocked, match="response evidence"):
        build_reachable_chart(
            seeds={"unit_u05_missing_response": seed},
            actions=("finish",),
            oracle=_Oracle(
                {
                    (b"missing-response", "finish"): OracleEvent.closed(
                        b"missing-response", "finish"
                    )
                }
            ),
            limits=ChartLimits(max_depth=1),
        )


def test_kp1_counts_only_nonempty_open_occurrences_and_not_closed_extensions():
    chart, _, _ = _duplicate_chart()
    report = probes.evaluate_kp1(chart)

    assert report.disposition == "U05_KP1_EXISTENCE_ONLY"
    assert report.nontrivial_identity_classes == 1
    assert [row.n_occ_open for row in report.cutoffs] == [2, 2, 2]
    assert [row.n_id_open for row in report.cutoffs] == [1, 1, 1]
    assert report.cutoffs[-1].c_id_open == Fraction(2)
    assert report.cutoffs[-1].derived_closed > 0
    assert report.cutoffs[-1].derived_sink > 0


def test_kp1_observation_alias_never_satisfies_exact_identity_gate():
    seed = _state("alias-root", (3, 3, 0, 1, 8), "root")
    rows = {
        (b"alias-root", "a"): lambda: OracleEvent.open(
            b"alias-root", "a", _state("alias-a", (2, 2, 0, 1, 5), "a")
        ),
        (b"alias-root", "b"): lambda: OracleEvent.open(
            b"alias-root", "b", _state("alias-b", (2, 2, 0, 1, 5), "b")
        ),
        (b"alias-a", "a"): OracleEvent.closed(b"alias-a", "a"),
        (b"alias-a", "b"): OracleEvent.closed(b"alias-a", "b"),
        (b"alias-b", "a"): OracleEvent.closed(b"alias-b", "a"),
        (b"alias-b", "b"): OracleEvent.closed(b"alias-b", "b"),
    }
    chart = build_reachable_chart(
        seeds={"unit_u05_alias": seed},
        actions=("a", "b"),
        oracle=_Oracle(rows),
        limits=ChartLimits(max_depth=3),
    )
    report = probes.evaluate_kp1(chart)
    assert report.disposition == "U05_KP1_OBSERVATION_ALIAS_ONLY"
    assert report.cutoffs[-1].n_occ_open == report.cutoffs[-1].n_id_open == 2
    assert report.cutoffs[-1].n_obs_open == 1
    assert not probes.capability_matrix(
        report, probes.evaluate_kp2(chart), evaluate_hankel_probe(chart)
    )["candidate_exact_partition"]["candidate"]


def test_kp1_blocks_when_equal_identity_has_different_occurrence_response():
    seed = _state("raw-root", (2, 2, 0, 0, 4), "raw-root")
    rows = {
        (b"raw-root", "a"): lambda: OracleEvent.open(
            b"raw-root",
            "a",
            _state("raw-shared", (1, 1, 0, 0, 2), "raw-a", response="response-a"),
        ),
        (b"raw-root", "b"): lambda: OracleEvent.open(
            b"raw-root",
            "b",
            _state("raw-shared", (1, 1, 0, 0, 2), "raw-b", response="response-b"),
        ),
        (b"raw-shared", "a"): OracleEvent.closed(b"raw-shared", "a"),
        (b"raw-shared", "b"): OracleEvent.closed(b"raw-shared", "b"),
    }
    chart = build_reachable_chart(
        seeds={"unit_u05_raw_mismatch": seed},
        actions=("a", "b"),
        oracle=_Oracle(rows),
        limits=ChartLimits(max_depth=3),
    )
    report = probes.evaluate_kp1(chart)
    assert report.disposition == "U05_PREREQUISITE_BLOCKED"
    assert report.cutoffs[-1].p_raw_open == Fraction(1)
    assert report.blocked_reason == (
        "equal full identities produced different occurrence responses"
    )


def _trajectory_chart(*, exact_delta: bool = True):
    seed = _state("t0", (3, 3, 0, 1, 8), "t0")
    rows = {
        (b"t0", "advance"): lambda: OracleEvent.open(
            b"t0",
            "advance",
            _state("t1", (4, 3, 0, 1, 9), "t1"),
            exact_delta=exact_delta,
        ),
        (b"t1", "advance"): lambda: OracleEvent.open(
            b"t1", "advance", _state("t2", (2, 2, 0, 1, 5), "t2")
        ),
        (b"t2", "advance"): OracleEvent.closed(b"t2", "advance"),
    }
    return build_reachable_chart(
        seeds={"unit_u05_trajectory": seed},
        actions=("advance",),
        oracle=_Oracle(rows),
        limits=ChartLimits(max_depth=3),
    )


def test_kp2_uses_open_to_open_blocks_on_eventually_closed_paths():
    report = probes.evaluate_kp2(_trajectory_chart())
    assert report.disposition == "U05_KP2_EVENTUAL_WINDOW"
    assert report.successful_trajectories == 1
    assert report.terminal_close_steps == 1
    assert report.eligible_open_steps == 2
    assert report.eligible_open_blocks == 3
    assert report.contractive_blocks == 2
    assert report.eligible_open_blocks_by_length == (2, 1, 0)
    assert report.contractive_blocks_by_length == (1, 1, 0)
    assert report.one_step_noncontractive_fraction == Fraction(1, 2)
    assert report.coordinate_increase_fractions[0] == Fraction(1, 2)
    assert report.longest_noncontractive_run == 1


def test_kp2_terminal_close_cannot_manufacture_a_window():
    seed = _state("close-root", (1, 1, 0, 0, 2), "close-root")
    chart = build_reachable_chart(
        seeds={"unit_u05_close": seed},
        actions=("finish",),
        oracle=_Oracle(
            {(b"close-root", "finish"): OracleEvent.closed(b"close-root", "finish")}
        ),
        limits=ChartLimits(max_depth=3),
    )
    report = probes.evaluate_kp2(chart)
    assert report.disposition == "U05_KP2_FRAGMENT_INCONCLUSIVE"
    assert report.terminal_close_steps == 1
    assert report.eligible_open_steps == report.eligible_open_blocks == 0


def test_kp2_fails_closed_on_inexact_delta():
    report = probes.evaluate_kp2(_trajectory_chart(exact_delta=False))
    assert report.disposition == "U05_PREREQUISITE_BLOCKED"
    assert report.blocked_reason == "inexact before/after delta present"


def test_censor_creates_no_transition_and_blocks_all_three_probes():
    seed = _state("censor-root", (1, 1, 0, 0, 2), "censor-root")
    chart = build_reachable_chart(
        seeds={"unit_u05_censor": seed},
        actions=("timeout",),
        oracle=_Oracle(
            {
                (b"censor-root", "timeout"): OracleEvent.censor(
                    b"censor-root", "timeout", "wall_timeout"
                )
            }
        ),
        limits=ChartLimits(max_depth=3),
    )
    assert chart.transition_table == {}
    assert chart.transition_censors
    assert len(chart.word_censors) == 3
    report = probes.evaluate_unit_fixture(chart)
    assert report.kp1.disposition == "U05_PREREQUISITE_BLOCKED"
    assert report.kp2.disposition == "U05_PREREQUISITE_BLOCKED"
    assert report.kp3.disposition == "U05_PREREQUISITE_BLOCKED"


def _loop_chart(task_id: str = "unit_u05_loop"):
    seed = _state("loop", (1, 1, 0, 0, 2), "loop-root")
    counter = iter(range(10))

    def loop():
        return OracleEvent.open(
            b"loop",
            "stay",
            _state("loop", (1, 1, 0, 0, 2), f"loop-child-{next(counter)}"),
        )

    return build_reachable_chart(
        seeds={task_id: seed},
        actions=("stay",),
        oracle=_Oracle({(b"loop", "stay"): loop}),
        limits=ChartLimits(max_depth=3),
    )


def test_sequential_merge_rejects_cross_task_attempt_counter_disagreement():
    left = _loop_chart("unit_u05_loop_left")
    right = _loop_chart("unit_u05_loop_right")
    edge = next(iter(right.transition_table))
    right.transition_table[edge] = replace(
        right.transition_table[edge], primary_attempts=0, replay_attempts=0
    )
    with pytest.raises(ChartPrerequisiteBlocked, match="semantic transition rows"):
        probes._merge_task_charts((left, right))


def test_global_state_registry_enforces_full_compare_and_online_cap():
    registry = {}
    first = _state("global-a", (1, 1, 0, 0, 2), "live-a")
    probes._register_global_state_fact(registry, first, maximum_states=1)
    probes._register_global_state_fact(
        registry, replace(first, live_rpc_state_id="live-a-duplicate"), maximum_states=1
    )
    with pytest.raises(ChartPrerequisiteBlocked, match="full-signature/debt"):
        probes._register_global_state_fact(
            registry,
            replace(first, full_signature=b"different"),
            maximum_states=1,
        )
    with pytest.raises(ChartPrerequisiteBlocked, match="maximum unique states total"):
        probes._register_global_state_fact(
            registry,
            _state("global-b", (1, 1, 0, 0, 2), "live-b"),
            maximum_states=1,
        )


def test_cross_task_sealed_row_is_derived_without_reexecution():
    concrete = OracleEvent.open(
        b"sealed",
        "stay",
        _state("target", (1, 1, 0, 0, 2), "process-local-target"),
    )
    derived = probes._derive_sealed_row_event(
        {(b"sealed", "stay"): concrete}, b"sealed", "stay"
    )
    assert derived is not None
    assert derived.derived_from_sealed_row is True
    assert derived.primary_attempts == derived.replay_attempts == 0
    assert derived.target is not None
    assert derived.target.live_rpc_state_id is None
    assert probes._derive_sealed_row_event({}, b"sealed", "stay") is None
    with pytest.raises(ValueError, match="handle-free"):
        replace(
            concrete,
            primary_attempts=0,
            replay_attempts=0,
            derived_from_sealed_row=True,
        )


def test_sequential_merge_accepts_only_provenanced_sealed_row_reuse():
    left = _loop_chart("unit_u05_reuse_left")
    right = _loop_chart("unit_u05_reuse_right")
    edge = next(iter(right.transition_table))
    derived = probes._derive_sealed_row_event(left.transition_table, *edge)
    assert derived is not None
    right.transition_table[edge] = derived
    right.primary_attempts = 0
    right.replay_attempts = 0
    merged = probes._merge_task_charts((left, right))
    assert merged.primary_attempts == merged.replay_attempts == 1
    assert len(merged.transition_table) == 1


def test_sealed_row_dp_expands_cached_target_without_live_handle():
    rows = {
        (b"cached-root", "step"): OracleEvent.open(
            b"cached-root",
            "step",
            _state("cached-target", (0, 0, 0, 0, 1), "old-worker-target"),
        ),
        (b"cached-target", "step"): OracleEvent.closed(
            b"cached-target", "step"
        ),
    }

    def cached_oracle(_task_id, source, action_id):
        event = probes._derive_sealed_row_event(rows, source.identity_key, action_id)
        if event is None:
            raise AssertionError("missing sealed test row")
        return event

    chart = build_reachable_chart(
        seeds={
            "unit_u05_cached_dp": _state(
                "cached-root", (1, 1, 0, 0, 2), "new-worker-seed"
            )
        },
        actions=("step",),
        oracle=cached_oracle,
        limits=ChartLimits(max_depth=3),
    )
    assert chart.primary_attempts == chart.replay_attempts == 0
    assert chart.outcome("unit_u05_cached_dp", ("step", "step")).kind is OutcomeKind.CLOSED


def test_hankel_uses_exact_rank_and_reports_conditioning_separately():
    chart = _loop_chart()
    report = evaluate_hankel_probe(chart)
    assert report.disposition == "U05_KP3_PLATEAU_AT_D3"
    assert [row.rank for row in report.cutoffs] == [1, 1, 1]
    assert [row.incremental_rank for row in report.cutoffs] == [1, 0, 0]
    assert report.cutoffs[-1].inverse_condition_ratio == pytest.approx(1.0)
    assert report.cutoffs[-1].n_rows == 2
    assert report.cutoffs[-1].n_suffixes == 3
    assert report.cutoffs[-1].n_columns == 21
    assert report.cutoffs[-1].n_cells == 42


def test_exact_rational_rank_is_row_and_column_permutation_invariant():
    matrix = [[1, 2, 3], [2, 4, 6], [0, 1, 1]]
    permuted = [[row[index] for index in (2, 0, 1)] for row in (matrix[2], matrix[0], matrix[1])]
    assert exact_rational_rank(matrix) == 2
    assert exact_rational_rank(permuted) == 2


def test_hankel_checks_cell_cap_before_reading_response_cells():
    with pytest.raises(ChartPrerequisiteBlocked, match="cell cap"):
        build_hankel_cutoff(_loop_chart(), 3, cell_cap=41)


def test_frozen_hankel_dimensions_fit_the_preregistered_cell_cap_without_task_read():
    assert hankel_dimensions(n_tasks=5, n_actions=12, cutoff=3) == (
        65,
        157,
        1099,
        71_435,
    )


def test_capability_matrix_does_not_collapse_independent_hypotheses():
    chart, _, _ = _duplicate_chart()
    report = probes.evaluate_unit_fixture(chart)
    capabilities = probes.capability_matrix(
        report.kp1,
        replace(
            report.kp2,
            disposition="U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT",
        ),
        report.kp3,
    )
    assert capabilities["candidate_exact_partition"]["candidate"] is True
    assert capabilities["candidate_hankel_predictive_model"]["candidate"] is True
    assert capabilities["candidate_componentwise_window"]["candidate"] is False
    assert capabilities["candidate_finite_horizon_envelope"]["candidate"] is False
    assert capabilities["candidate_maxent_nominal"]["candidate"] is False
    assert report.licenses_k1_k4 is False
    assert report.licenses_wp4_wp12_implementation is False
    assert report.licenses_gpu is False


def test_production_literals_match_frozen_digests_without_enumerating_matrix():
    assert probes.verify_frozen_matrix_literals()
    assert probes.frozen_matrix_digests() == {
        "task_matrix_sha256": probes.TASK_MATRIX_SHA256,
        "action_matrix_sha256": probes.ACTION_MATRIX_SHA256,
    }
    assert probes.FROZEN_LIMITS["maximum_symbolic_word_depth"] == 3
    assert probes.FROZEN_LIMITS["maximum_hankel_cells"] == 100_000
    assert probes.FROZEN_LIMITS["cache_policy"] == "bypass"


def test_production_entrypoint_denies_before_task_or_root_file_access(monkeypatch):
    forbidden = {
        "llm_local.json",
        "pilot_tasks.json",
        "fake_lean_smoke.py",
        "smoke_tasks_local.jsonl",
    }
    real_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        if Path(file).name in forbidden:
            raise AssertionError(f"forbidden root input opened: {file}")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.delenv("UPRIME_U05_EXECUTE", raising=False)
    monkeypatch.setattr(
        probes.json,
        "loads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("production matrix materialized")
        ),
    )
    monkeypatch.setattr(
        probes,
        "load_frozen_execution_matrix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("production matrix evaluator invoked")
        ),
    )
    assert probes.main([]) == 3
    monkeypatch.setenv("UPRIME_U05_EXECUTE", "1")
    assert probes.main(["--anchor", "a" * 40]) == 3


def test_unit_evaluator_rejects_a_production_task_id_before_probe_access():
    with pytest.raises(probes.ProductionExecutionDenied, match="unit_u05"):
        probes.evaluate_unit_fixture(SimpleNamespace(task_ids=("u05_identity",)))


def test_production_matrix_requires_env_anchor_and_exclusive_reservation():
    authorization = probes.ProductionAuthorization(
        anchor="a" * 40,
        full_anchor_verified=True,
        exclusive_reservation_verified=False,
        pushed_green_candidate_verified=True,
        disposable_clean_worktree_verified=True,
    )
    with pytest.raises(probes.ProductionExecutionDenied, match="UPRIME_U05_EXECUTE"):
        probes.load_frozen_execution_matrix(authorization, environ={})
    with pytest.raises(probes.ProductionExecutionDenied, match="exclusive reservation"):
        probes.load_frozen_execution_matrix(
            authorization, environ={"UPRIME_U05_EXECUTE": "1"}
        )


def test_canonical_result_is_deterministic_and_keeps_exact_fractions():
    report = probes.evaluate_unit_fixture(_loop_chart())
    first = probes.canonical_result_bytes(report)
    second = probes.canonical_result_bytes(report)
    assert first == second
    assert first.endswith(b"\n")
    assert b'"denominator":1' in first
    assert b'"licenses_gpu":false' in first


def test_canonical_parser_rejects_nonfinite_json_constants():
    with pytest.raises(probes.ProductionExecutionDenied, match="canonical JSON"):
        probes._parse_canonical_json(b'{"schema":"unit","value":NaN}\n')


def test_merkle_is_order_invariant_and_rejects_duplicate_normalized_key():
    rows = [
        ["scope", "b", "kind", "B" * 64],
        ["scope", "a", "kind", "A" * 64],
    ]
    digest = probes.merkle_sha256("unit-schema", rows)
    assert digest == probes.merkle_sha256("unit-schema", reversed(rows))
    assert digest == "FD62B2BD539EFE5D9BE8908D3D55C791368A1AF1838D66F11472B7FBECFC7DE9"
    with pytest.raises(probes.ProductionExecutionDenied, match="duplicate normalized key"):
        probes.merkle_sha256(
            "unit-schema",
            [
                ["scope", "same", "kind", "A" * 64],
                ["scope", "same", "kind", "B" * 64],
            ],
        )


def test_relative_normalization_uses_unicode_nfc_and_casefold(tmp_path):
    composed = tmp_path / "É.dll"
    decomposed = tmp_path / "E\u0301.DLL"
    assert probes._normalized_relative(composed, tmp_path) == probes._normalized_relative(
        decomposed, tmp_path
    )


def _ci_git_text(anchor: str):
    def fake(_root, *args):
        if args == ("rev-parse", probes.UPSTREAM_REF):
            return anchor
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/example/project.git"
        if args == ("rev-parse", f"HEAD:{probes.CI_WORKFLOW_PATH}"):
            return "workflow-blob"
        raise AssertionError(args)

    return fake


def _ci_run(anchor: str, run_id: int):
    return {
        "id": run_id,
        "head_sha": anchor,
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "head_branch": "codex/uprime-odlrq-plan",
        "name": "CI",
        "path": ".github/workflows/ci.yml",
    }


def test_ci_control_plane_paginates_and_requires_exact_run_job(monkeypatch, tmp_path):
    anchor = "a" * 40
    monkeypatch.setattr(probes, "_git_text", _ci_git_text(anchor))
    seen: list[str] = []

    def api(endpoint: str):
        seen.append(endpoint)
        if "/jobs?" in endpoint:
            return {
                "total_count": 1,
                "jobs": [
                    {
                        "id": 999,
                        "name": "pytest",
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": anchor,
                    }
                ],
            }
        page = int(endpoint.rsplit("page=", 1)[1])
        if page == 1:
            return {
                "total_count": 101,
                "workflow_runs": [
                    _ci_run(f"{index:040x}", index) for index in range(100)
                ],
            }
        return {"total_count": 101, "workflow_runs": [_ci_run(anchor, 321)]}

    receipt = probes.verify_ci_control_plane(
        tmp_path,
        anchor=anchor,
        upstream=probes.UPSTREAM_REF,
        workflow_path=probes.CI_WORKFLOW_PATH,
        job_name=probes.CI_JOB_NAME,
        accepted_conclusion="success",
        api=api,
    )
    assert receipt["run_id"] == 321
    assert receipt["job_id"] == 999
    assert any(".github%2Fworkflows%2Fci.yml" in endpoint for endpoint in seen)
    assert any("page=2" in endpoint for endpoint in seen)


@pytest.mark.parametrize("field,value", [("name", "Other"), ("path", "other.yml")])
def test_ci_control_plane_rejects_wrong_workflow_identity(
    monkeypatch, tmp_path, field, value
):
    anchor = "a" * 40
    monkeypatch.setattr(probes, "_git_text", _ci_git_text(anchor))
    run = _ci_run(anchor, 1)
    run[field] = value

    def api(endpoint: str):
        if "/jobs?" in endpoint:
            raise AssertionError("jobs must not be queried")
        return {"total_count": 1, "workflow_runs": [run]}

    with pytest.raises(probes.ProductionExecutionDenied, match="not unique"):
        probes.verify_ci_control_plane(
            tmp_path,
            anchor=anchor,
            upstream=probes.UPSTREAM_REF,
            workflow_path=probes.CI_WORKFLOW_PATH,
            job_name=probes.CI_JOB_NAME,
            accepted_conclusion="success",
            api=api,
        )


def test_measurement_environment_is_allowlist_not_parent_copy(monkeypatch, tmp_path):
    system_root = tmp_path / "windows"
    (system_root / "System32").mkdir(parents=True)
    elan_home = tmp_path / "elan-home"
    elan_home.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    git = tools / "git.exe"
    elan = tools / "elan.exe"
    comspec = tools / "cmd.exe"
    for path in (git, elan, comspec):
        path.write_bytes(b"unit tool")
    monkeypatch.setenv("SystemRoot", str(system_root))
    monkeypatch.setenv("ComSpec", str(comspec))
    monkeypatch.setenv("ELAN_HOME", str(elan_home))
    monkeypatch.setattr(
        probes.shutil,
        "which",
        lambda name: str({"git": git, "elan": elan}[name]),
    )
    monkeypatch.setattr(
        probes.sys, "path", [str(tmp_path), str(Path(probes.sys.prefix).resolve())]
    )
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setenv("PYTHONPATH", "shadow")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    env = probes._measurement_environment(
        repo_root=tmp_path,
        anchor="a" * 40,
        receipt_sha256="A" * 64,
    )
    assert set(env) == set(probes.MEASUREMENT_ENV_KEYS)
    assert "GH_TOKEN" not in env and "PYTHONPATH" not in env
    assert "OPENAI_API_KEY" not in env
    assert env["UPRIME_U05_RECEIPT_SHA256"] == "A" * 64
    assert Path(env["USERPROFILE"]).is_relative_to(tmp_path)


def test_atomic_new_publication_never_overwrites_existing_destination(tmp_path):
    destination = tmp_path / "artifact.json"
    destination.write_bytes(b"original")
    with pytest.raises(probes.ProductionExecutionDenied, match="overwrite"):
        probes._atomic_write_new(destination, b"replacement")
    assert destination.read_bytes() == b"original"


def test_attempt_process_lock_excludes_concurrent_recovery(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(b"{}\n")
    with probes._attempt_process_lock(receipt):
        reader = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from pathlib import Path; print(Path(sys.argv[1]).read_text())",
                str(receipt),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert reader.returncode == 0
        assert reader.stdout.strip() == "{}"
        contender = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from pathlib import Path; "
                    "from lean_rgc.evals.uprime_u05_kill_probes import _attempt_process_lock; "
                    "\nwith _attempt_process_lock(Path(sys.argv[1])): print('acquired')"
                ),
                str(receipt),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert contender.returncode != 0
        assert "already active" in contender.stderr
        with pytest.raises(probes.ProductionExecutionDenied, match="already active"):
            with probes._attempt_process_lock(receipt):
                raise AssertionError("concurrent lock unexpectedly acquired")


def _frozen_shape_probe_report():
    kp1 = probes.KP1Report(
        disposition="U05_KP1_SCALE_READY",
        cutoffs=tuple(
            probes.KP1CutoffReport(
                cutoff=cutoff,
                n_occ_open=5 * sum(12**depth for depth in range(1, cutoff + 1)),
                n_id_open=5,
                c_id_open=Fraction(
                    5 * sum(12**depth for depth in range(1, cutoff + 1)), 5
                ),
                n_obs_open=5,
                c_obs_open=Fraction(
                    5 * sum(12**depth for depth in range(1, cutoff + 1)), 5
                ),
                p_raw_open=Fraction(0),
                first_entry_closed=0,
                derived_closed=0,
                first_entry_sink=0,
                derived_sink=0,
                censored=0,
            )
            for cutoff in (1, 2, 3)
        ),
        nontrivial_identity_classes=5,
        nontrivial_class_task_ids=tuple(sorted(probes.PRODUCTION_TASK_IDS)),
    )
    kp2 = probes.KP2Report(
        disposition="U05_KP2_FRAGMENT_INCONCLUSIVE",
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
    )
    kp3_rows = []
    for cutoff in (1, 2, 3):
        n_rows, n_suffixes, n_columns, n_cells = hankel_dimensions(
            n_tasks=5, n_actions=12, cutoff=cutoff
        )
        kp3_rows.append(
            probes.HankelCutoffReport(
                cutoff=cutoff,
                rank=0,
                n_rows=n_rows,
                n_suffixes=n_suffixes,
                n_columns=n_columns,
                n_cells=n_cells,
                incremental_rank=0,
                singular_values=(0.0,) * min(n_rows, n_columns),
                inverse_condition_ratio=0.0,
                non_sink_prefix_coverage=Fraction(0),
                non_sink_suffix_coverage=Fraction(0),
                per_channel_scales=(0,) * 7,
            )
        )
    kp3 = probes.HankelProbeReport(
        disposition="U05_KP3_INCONCLUSIVE", cutoffs=tuple(kp3_rows)
    )
    return probes.KillProbeReport(
        schema=probes.RAW_RESULT_SCHEMA,
        kp1=kp1,
        kp2=kp2,
        kp3=kp3,
        capability_matrix=probes.capability_matrix(kp1, kp2, kp3),
    )


def _frozen_shape_probe_payload():
    return json.loads(
        probes.canonical_json_bytes(probes._json_value(_frozen_shape_probe_report()))
    )


def _set_open_count(row, value):
    row["n_occ_open"] = value
    row["c_id_open"] = probes._json_value(Fraction(value, row["n_id_open"]))
    row["c_obs_open"] = probes._json_value(Fraction(value, row["n_obs_open"]))


def _set_hankel_rank_row(row, *, rank, previous_rank, scales):
    singular = [0.0] * len(row["singular_values"])
    if rank:
        singular[0] = 1.0
    row["rank"] = rank
    row["incremental_rank"] = rank - previous_rank
    row["singular_values"] = singular
    row["inverse_condition_ratio"] = 0.0 if rank != 1 else 1.0
    row["per_channel_scales"] = list(scales)


def test_probe_decoder_rejects_nonmonotone_identity_counts():
    payload = _frozen_shape_probe_payload()
    row = payload["kp1"]["cutoffs"][1]
    row["n_id_open"] = row["n_obs_open"] = 4
    _set_open_count(row, row["n_occ_open"])
    with pytest.raises(probes.ProductionExecutionDenied, match="quotient counts"):
        probes._decode_probe_report(payload)


def test_probe_decoder_rejects_impossible_terminal_recurrence():
    payload = _frozen_shape_probe_payload()
    for row in payload["kp1"]["cutoffs"]:
        row["first_entry_closed"] = 1
        _set_open_count(row, row["n_occ_open"] - 1)
    kp2 = payload["kp2"]
    kp2["successful_trajectories"] = kp2["terminal_close_steps"] = 1
    for index, row in enumerate(payload["kp3"]["cutoffs"]):
        _set_hankel_rank_row(
            row,
            rank=1,
            previous_rank=0 if index == 0 else 1,
            scales=(1, 0, 0, 0, 0, 0, 0),
        )
    payload["kp3"]["disposition"] = "U05_KP3_PLATEAU_AT_D3"
    payload["capability_matrix"]["candidate_hankel_predictive_model"].update(
        {"candidate": True, "may_draft": True}
    )
    with pytest.raises(probes.ProductionExecutionDenied, match="terminal-extension"):
        probes._decode_probe_report(payload)


def test_probe_decoder_rejects_coordinate_increase_above_noncontractive_count():
    payload = _frozen_shape_probe_payload()
    final_kp1 = payload["kp1"]["cutoffs"][2]
    final_kp1["first_entry_closed"] = 1
    _set_open_count(final_kp1, final_kp1["n_occ_open"] - 1)
    kp2 = payload["kp2"]
    kp2.update(
        {
            "disposition": "U05_KP2_EVENTUAL_WINDOW",
            "successful_trajectories": 1,
            "eligible_open_steps": 2,
            "eligible_open_blocks": 3,
            "contractive_blocks": 1,
            "eligible_open_blocks_by_length": [2, 1, 0],
            "contractive_blocks_by_length": [1, 0, 0],
            "terminal_close_steps": 1,
            "one_step_noncontractive_fraction": probes._json_value(Fraction(1, 2)),
            "coordinate_increase_fractions": [
                probes._json_value(Fraction(1)),
                *[probes._json_value(Fraction(0)) for _ in range(4)],
            ],
            "longest_noncontractive_run": 1,
        }
    )
    payload["capability_matrix"]["candidate_componentwise_window"].update(
        {"candidate": True, "may_draft": True}
    )
    for index, row in enumerate(payload["kp3"]["cutoffs"]):
        if index == 2:
            _set_hankel_rank_row(
                row,
                rank=1,
                previous_rank=0,
                scales=(1, 0, 0, 0, 0, 0, 0),
            )
    with pytest.raises(probes.ProductionExecutionDenied, match="coordinate increases"):
        probes._decode_probe_report(payload)


def test_probe_decoder_rejects_nonmonotone_hankel_channel_scales():
    payload = _frozen_shape_probe_payload()
    scale_rows = (
        (0, 0, 1, 0, 0, 0, 0),
        (0, 0, 0, 1, 0, 0, 0),
        (0, 0, 0, 1, 0, 0, 0),
    )
    for index, (row, scales) in enumerate(zip(payload["kp3"]["cutoffs"], scale_rows)):
        _set_hankel_rank_row(
            row, rank=1, previous_rank=0 if index == 0 else 1, scales=scales
        )
    payload["kp3"]["disposition"] = "U05_KP3_PLATEAU_AT_D3"
    payload["capability_matrix"]["candidate_hankel_predictive_model"].update(
        {"candidate": True, "may_draft": True}
    )
    with pytest.raises(probes.ProductionExecutionDenied, match="channel scales"):
        probes._decode_probe_report(payload)


def test_probe_decoder_accepts_evaluator_degenerate_numeric_rank():
    payload = _frozen_shape_probe_payload()
    ranks = (1, 2, 2)
    for index, (row, rank) in enumerate(zip(payload["kp3"]["cutoffs"], ranks)):
        _set_hankel_rank_row(
            row,
            rank=rank,
            previous_rank=0 if index == 0 else ranks[index - 1],
            scales=(0, 0, 1, 0, 0, 0, 0),
        )
    decoded = probes._decode_probe_report(payload)
    assert decoded.kp3.disposition == "U05_KP3_INCONCLUSIVE"
    assert decoded.kp3.cutoffs[1].rank == 2
    assert decoded.kp3.cutoffs[1].inverse_condition_ratio == 0.0


def test_valid_marker_and_complete_raw_are_bound_to_receipt():
    receipt_raw = b"receipt-bytes\n"
    receipt = {
        "candidate": "a" * 40,
        "attempt_id": "B" * 64,
        "environment": {"environment_content_digest": "C" * 64},
    }
    marker = probes.canonical_json_bytes(
        {
            "schema": probes.MATRIX_OPEN_SCHEMA,
            "opened_at_utc": "2026-07-12T00:00:00+00:00",
            "candidate": "a" * 40,
            "attempt_id": "B" * 64,
            "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
            "task_matrix_sha256": probes.TASK_MATRIX_SHA256,
            "action_matrix_sha256": probes.ACTION_MATRIX_SHA256,
            "look_consumed": True,
        }
    )
    assert probes._valid_matrix_marker(
        marker, receipt=receipt, receipt_raw=receipt_raw
    )
    report = _frozen_shape_probe_report()
    raw = probes.canonical_json_bytes(
        {
            "schema": probes.RAW_RESULT_SCHEMA,
            "status": "U05_COMPLETE",
            "candidate": "a" * 40,
            "task_matrix_sha256": probes.TASK_MATRIX_SHA256,
            "action_matrix_sha256": probes.ACTION_MATRIX_SHA256,
            "look_consumed": True,
            "environment_content_digest": "C" * 64,
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
                "task_count": 5,
                "action_count": 12,
                "unique_state_count": 5,
                "transition_row_count": 60,
                "word_occurrence_count": 5 * (1 + 12 + 12**2 + 12**3),
                "primary_attempts": 60,
                "replay_attempts": 60,
                "prefix_executions": 7,
                "total_lean_tactic_executions": 127,
                "syntactic_sink_rows": 0,
                "peak_live_state_count": 1,
                "chart_released_live_state_count": 5,
                "post_chart_frontier_discard_count": 0,
                "elapsed_seconds": 1.0,
                "worker_status": [
                    {
                        "task_id": task_id,
                        "n_states": 0,
                        "n_requests": 16,
                        "n_failures": 0,
                        "n_primary_executions": 12,
                        "n_replay_executions": 12,
                        "released_by_process_abort": 0,
                        "peak_owned_states": 1,
                    }
                    for task_id in sorted(probes.PRODUCTION_TASK_IDS)
                ],
            },
            "probe_report": probes._json_value(report),
            "licenses_k1_k4": False,
            "licenses_u2_u5_claims": False,
            "licenses_wp4_wp12_implementation": False,
            "licenses_gpu": False,
            "licenses_canonical_rpc_rerun": False,
            "licenses_reserved_data_read": False,
        }
    )
    assert probes._valid_raw_result(raw, receipt=receipt) == (True, "U05_COMPLETE")
    mutated = json.loads(raw)
    mutated["licenses_gpu"] = True
    assert probes._valid_raw_result(
        probes.canonical_json_bytes(mutated), receipt=receipt
    ) == (False, "U05_COMPLETE")
    mutated = json.loads(raw)
    mutated["probe_report"]["kp3"]["cutoffs"][2]["n_cells"] += 1
    assert probes._valid_raw_result(
        probes.canonical_json_bytes(mutated), receipt=receipt
    ) == (False, None)
    mutated = json.loads(raw)
    mutated["costs"]["worker_status"][0]["n_requests"] = 15
    assert probes._valid_raw_result(
        probes.canonical_json_bytes(mutated), receipt=receipt
    ) == (False, "U05_COMPLETE")


def test_blocked_raw_rejects_negative_elapsed_time():
    receipt = {
        "candidate": "a" * 40,
        "environment": {"environment_content_digest": "C" * 64},
    }
    value = {
        "schema": probes.RAW_RESULT_SCHEMA,
        "status": "U05_PREREQUISITE_BLOCKED",
        "candidate": "a" * 40,
        "task_matrix_sha256": probes.TASK_MATRIX_SHA256,
        "action_matrix_sha256": probes.ACTION_MATRIX_SHA256,
        "look_consumed": True,
        "reason_class": "UnitBlocked",
        "reason": "unit",
        "elapsed_seconds": -1.0,
        "licenses_k1_k4": False,
        "licenses_u2_u5_claims": False,
        "licenses_wp4_wp12_implementation": False,
        "licenses_gpu": False,
        "licenses_canonical_rpc_rerun": False,
        "licenses_reserved_data_read": False,
    }
    assert probes._valid_raw_result(
        probes.canonical_json_bytes(value), receipt=receipt
    ) == (False, "U05_PREREQUISITE_BLOCKED")


def test_recover_only_never_materializes_matrix(monkeypatch, tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        probes,
        "publish_attempt_envelope",
        lambda **_kwargs: {"look_consumed": False},
    )
    monkeypatch.setattr(
        probes,
        "load_frozen_execution_matrix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("matrix materialized during recovery")
        ),
    )
    assert probes.recover_attempt(
        receipt_path=receipt,
        raw_output_path=tmp_path / "raw.json",
        artifact_path=tmp_path / "artifact.json",
    ) == 2
