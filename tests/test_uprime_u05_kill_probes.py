from __future__ import annotations

import builtins
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
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


def _loop_chart():
    seed = _state("loop", (1, 1, 0, 0, 2), "loop-root")
    counter = iter(range(10))

    def loop():
        return OracleEvent.open(
            b"loop",
            "stay",
            _state("loop", (1, 1, 0, 0, 2), f"loop-child-{next(counter)}"),
        )

    return build_reachable_chart(
        seeds={"unit_u05_loop": seed},
        actions=("stay",),
        oracle=_Oracle({(b"loop", "stay"): loop}),
        limits=ChartLimits(max_depth=3),
    )


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
    assert probes.main(["--anchor", "a" * 40]) == 2


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
