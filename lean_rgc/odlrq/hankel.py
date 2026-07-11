"""Exact finite response-Hankel construction for the U'0.5 probes."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor
from typing import Sequence

import numpy as np

from .reachable_chart import ChartPrerequisiteBlocked, ReachableChart
from .rule_algebra import ActionWord, OutcomeKind, action_words, final_response_channels


RESPONSE_CHANNELS = (
    "closed_indicator",
    "sink_indicator",
    "open_goal_count",
    "open_unassigned_mvar_count",
    "pending_typeclass_count",
    "carrier_atom_count",
    "expression_node_count",
)


@dataclass(frozen=True)
class HankelCutoffReport:
    cutoff: int
    rank: int
    n_rows: int
    n_suffixes: int
    n_columns: int
    n_cells: int
    incremental_rank: int
    singular_values: tuple[float, ...]
    inverse_condition_ratio: float
    non_sink_prefix_coverage: Fraction
    non_sink_suffix_coverage: Fraction
    per_channel_scales: tuple[int, ...]


@dataclass(frozen=True)
class HankelProbeReport:
    disposition: str
    cutoffs: tuple[HankelCutoffReport, ...]
    blocked_reason: str | None = None


def exact_rational_rank(matrix: Sequence[Sequence[int | Fraction]]) -> int:
    """Compute matrix rank over Q using deterministic row echelon reduction."""

    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("matrix must be rectangular")
    if width == 0:
        return 0
    rows = [[Fraction(value) for value in row] for row in matrix]
    n_rows = len(rows)
    pivot_row = 0
    for column in range(width):
        pivot = next(
            (row for row in range(pivot_row, n_rows) if rows[row][column]),
            None,
        )
        if pivot is None:
            continue
        if pivot != pivot_row:
            rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        pivot_value = rows[pivot_row][column]
        for index in range(column, width):
            rows[pivot_row][index] /= pivot_value
        for row in range(pivot_row + 1, n_rows):
            factor = rows[row][column]
            if not factor:
                continue
            for index in range(column, width):
                rows[row][index] -= factor * rows[pivot_row][index]
        pivot_row += 1
        if pivot_row == n_rows:
            break
    return pivot_row


def _response(chart: ReachableChart, task_id: str, word: ActionWord) -> tuple[int, ...]:
    outcome = chart.outcome(task_id, word)
    state = chart.state_for_outcome(outcome)
    return final_response_channels(outcome, state)


def hankel_dimensions(
    *, n_tasks: int, n_actions: int, cutoff: int
) -> tuple[int, int, int, int]:
    """Return ``(rows, suffixes, columns, cells)`` without opening any matrix."""

    if n_tasks <= 0 or n_actions <= 0:
        raise ValueError("task and action counts must be positive")
    if cutoff not in (1, 2, 3):
        raise ValueError("U05 Hankel cutoff must be one of 1, 2, 3")
    prefix_count = sum(
        n_actions**depth for depth in range(floor(cutoff / 2) + 1)
    )
    suffix_count = sum(
        n_actions**depth for depth in range(ceil(cutoff / 2) + 1)
    )
    n_rows = n_tasks * prefix_count
    n_columns = suffix_count * len(RESPONSE_CHANNELS)
    return n_rows, suffix_count, n_columns, n_rows * n_columns


def build_hankel_cutoff(
    chart: ReachableChart,
    cutoff: int,
    *,
    cell_cap: int = 100_000,
    previous_rank: int = 0,
) -> tuple[HankelCutoffReport, list[list[int]]]:
    """Construct one frozen multi-channel Hankel matrix.

    The cap is checked from dimensions before allocating or reading response
    cells.  Any censor or missing word raises ``ChartPrerequisiteBlocked`` and
    therefore creates no partial rank result.
    """

    if cutoff not in (1, 2, 3):
        raise ValueError("U05 Hankel cutoff must be one of 1, 2, 3")
    prefixes = tuple(
        action_words(chart.action_ids, floor(cutoff / 2), include_empty=True)
    )
    suffixes = tuple(
        action_words(chart.action_ids, ceil(cutoff / 2), include_empty=True)
    )
    rows = tuple((task_id, prefix) for task_id in chart.task_ids for prefix in prefixes)
    n_rows, n_suffixes, n_columns, n_cells = hankel_dimensions(
        n_tasks=len(chart.task_ids),
        n_actions=len(chart.action_ids),
        cutoff=cutoff,
    )
    if n_rows != len(rows) or n_suffixes != len(suffixes):
        raise AssertionError("Hankel dimension arithmetic disagrees with coordinates")
    if n_cells > cell_cap:
        raise ChartPrerequisiteBlocked(
            f"Hankel cell cap exceeded before construction: {n_cells}>{cell_cap}"
        )

    matrix: list[list[int]] = []
    scales = [0] * len(RESPONSE_CHANNELS)
    non_sink_prefixes = 0
    non_sink_final_pairs = 0
    for task_id, prefix in rows:
        prefix_outcome = chart.outcome(task_id, prefix)
        if prefix_outcome.kind is not OutcomeKind.SINK:
            non_sink_prefixes += 1
        row: list[int] = []
        for suffix in suffixes:
            response = _response(chart, task_id, prefix + suffix)
            if response[1] == 0:
                non_sink_final_pairs += 1
            for index, value in enumerate(response):
                row.append(value)
                scales[index] = max(scales[index], abs(value))
        matrix.append(row)

    rank = exact_rational_rank(matrix)
    float_matrix = np.asarray(matrix, dtype=float)
    singular = np.linalg.svd(float_matrix, compute_uv=False)
    singular_values = tuple(float(value) for value in singular)
    if rank == 0 or not singular_values or singular_values[0] == 0.0:
        inverse_ratio = 0.0
    else:
        inverse_ratio = float(singular_values[rank - 1] / singular_values[0])
    report = HankelCutoffReport(
        cutoff=cutoff,
        rank=rank,
        n_rows=n_rows,
        n_suffixes=n_suffixes,
        n_columns=n_columns,
        n_cells=n_cells,
        incremental_rank=rank - previous_rank,
        singular_values=singular_values,
        inverse_condition_ratio=inverse_ratio,
        non_sink_prefix_coverage=Fraction(non_sink_prefixes, n_rows),
        non_sink_suffix_coverage=Fraction(
            non_sink_final_pairs, n_rows * n_suffixes
        ),
        per_channel_scales=tuple(scales),
    )
    return report, matrix


def evaluate_hankel_probe(
    chart: ReachableChart, *, cell_cap: int = 100_000
) -> HankelProbeReport:
    """Evaluate U05-KP3 at the three preregistered total cutoffs."""

    if chart.has_censors:
        return HankelProbeReport(
            disposition="U05_PREREQUISITE_BLOCKED",
            cutoffs=(),
            blocked_reason="resource/transport/replay censor present",
        )
    reports: list[HankelCutoffReport] = []
    try:
        previous_rank = 0
        for cutoff in (1, 2, 3):
            report, _ = build_hankel_cutoff(
                chart,
                cutoff,
                cell_cap=cell_cap,
                previous_rank=previous_rank,
            )
            reports.append(report)
            previous_rank = report.rank
    except ChartPrerequisiteBlocked as exc:
        return HankelProbeReport(
            disposition="U05_PREREQUISITE_BLOCKED",
            cutoffs=tuple(reports),
            blocked_reason=exc.reason,
        )

    r1, r2, r3 = reports
    dimensions_increased = (
        r3.n_rows > r2.n_rows or r3.n_columns > r2.n_columns
    )
    if (
        r3.rank == r2.rank
        and r2.rank != 0
        and dimensions_increased
        and r3.inverse_condition_ratio >= 1e-8
    ):
        disposition = "U05_KP3_PLATEAU_AT_D3"
    elif (
        r1.rank < r2.rank < r3.rank
        and Fraction(r3.rank, min(r3.n_rows, r3.n_columns)) >= Fraction(4, 5)
    ):
        disposition = "U05_KP3_NO_LOW_RANK_WINDOW_ON_FROZEN_FAMILY"
    else:
        disposition = "U05_KP3_INCONCLUSIVE"
    return HankelProbeReport(disposition=disposition, cutoffs=tuple(reports))


__all__ = [
    "HankelCutoffReport",
    "HankelProbeReport",
    "RESPONSE_CHANNELS",
    "build_hankel_cutoff",
    "evaluate_hankel_probe",
    "exact_rational_rank",
    "hankel_dimensions",
]
