"""Development-only U'0.5 kill-probe apparatus.

The scientific core is deterministic and accepts an injected reachable chart.
The production matrix remains behind an explicit authorization object and the
CLI intentionally defaults to denial until the outer receipt/reservation and
hosted-CI preflight are completed by the frozen WP3 launcher.  Importing this
module never opens a task file or materializes the frozen task array.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from itertools import combinations
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from lean_rgc.odlrq.hankel import HankelProbeReport, evaluate_hankel_probe
from lean_rgc.odlrq.reachable_chart import ReachableChart
from lean_rgc.odlrq.rule_algebra import ActionWord, OutcomeKind


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
    if any(
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
    """Default-deny WP3 entrypoint; it never materializes tasks in WP2."""

    args = _parser().parse_args(argv)
    if os.environ.get("UPRIME_U05_EXECUTE") != "1":
        print("U05 production execution denied: UPRIME_U05_EXECUTE=1 is required", file=sys.stderr)
        return 3
    if args.anchor is None or re.fullmatch(r"[0-9a-f]{40}", args.anchor) is None:
        print("U05 production execution denied: full anchor is required", file=sys.stderr)
        return 3
    # The frozen plan requires a pre-receipt hosted-CI check, immutable receipt,
    # exclusive marker, credential stripping, and measurement-child handoff.
    # Those side-effecting WP3 controls are intentionally not inferred from CLI
    # strings or environment claims by this pure WP2 implementation.
    print(
        "U05_PREREQUISITE_BLOCKED: exclusive outer reservation/receipt preflight is not present",
        file=sys.stderr,
    )
    return 2


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
