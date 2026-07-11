"""Bounded task-seeded reachable charts for the U'1.5 apparatus."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Iterable, Mapping, Protocol

from .rule_algebra import (
    ActionWord,
    CensorRecord,
    OracleEvent,
    OutcomeKind,
    StateView,
    WordOutcome,
    canonical_action_ids,
    derived_terminal_extension,
    words_at_depth,
)


class TransitionOracle(Protocol):
    def __call__(
        self, task_id: str, source: StateView, action_id: str
    ) -> OracleEvent: ...


class ChartPrerequisiteBlocked(RuntimeError):
    """A frozen cap or exactness prerequisite prevented chart completion."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ChartLimits:
    max_depth: int = 3
    max_states_per_task: int = 256
    max_states_total: int = 1024
    max_primary_attempts: int = 12_288
    max_replay_attempts: int = 12_288
    max_word_occurrences: int = 15_000

    def __post_init__(self) -> None:
        if self.max_depth < 0:
            raise ValueError("max_depth must be nonnegative")
        for name in (
            "max_states_per_task",
            "max_states_total",
            "max_primary_attempts",
            "max_replay_attempts",
            "max_word_occurrences",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass
class StateTableEntry:
    identity_key: bytes
    full_signature: bytes
    debt: tuple[int, int, int, int, int]
    expansion_status: str
    live_rpc_state_id: str | None
    first_task_id: str
    task_ids: set[str] = field(default_factory=set)

    def state_view(self, *, response_signature: bytes = b"") -> StateView:
        return StateView(
            identity_key=self.identity_key,
            full_signature=self.full_signature,
            debt=self.debt,
            live_rpc_state_id=self.live_rpc_state_id,
            response_signature=response_signature,
        )


@dataclass
class ReachableChart:
    action_ids: tuple[str, ...]
    limits: ChartLimits
    state_table: dict[bytes, StateTableEntry]
    transition_table: dict[tuple[bytes, str], OracleEvent]
    word_table: dict[tuple[str, ActionWord], WordOutcome]
    word_censors: dict[tuple[str, ActionWord], CensorRecord]
    transition_censors: dict[tuple[bytes, str], CensorRecord]
    task_ids: tuple[str, ...]
    primary_attempts: int
    replay_attempts: int
    peak_live_state_count: int
    released_live_state_count: int

    def outcome(self, task_id: str, word: ActionWord) -> WordOutcome:
        try:
            return self.word_table[(task_id, word)]
        except KeyError as exc:
            if (task_id, word) in self.word_censors:
                raise ChartPrerequisiteBlocked(
                    f"censored word {task_id}:{word!r}"
                ) from exc
            raise ChartPrerequisiteBlocked(
                f"missing prefix-closed word {task_id}:{word!r}"
            ) from exc

    def state_for_outcome(self, outcome: WordOutcome) -> StateView | None:
        if outcome.kind is not OutcomeKind.OPEN:
            return None
        if outcome.state_key not in self.state_table:
            raise ChartPrerequisiteBlocked("open word references an unknown state")
        entry = self.state_table[outcome.state_key]
        return entry.state_view(response_signature=outcome.response_signature)

    @property
    def has_censors(self) -> bool:
        return bool(self.word_censors or self.transition_censors)

    @property
    def word_occurrence_count(self) -> int:
        return len(self.word_table) + len(self.word_censors)


DiscardLiveState = Callable[[str, str], None]


class ReachableChartBuilder:
    """Build the three frozen tables over an injected transition oracle."""

    def __init__(
        self,
        *,
        actions: Iterable[object],
        oracle: TransitionOracle,
        limits: ChartLimits | None = None,
        discard_live_state: DiscardLiveState | None = None,
    ) -> None:
        self.action_ids = canonical_action_ids(actions)
        self.oracle = oracle
        self.limits = limits or ChartLimits()
        self.discard_live_state = discard_live_state
        self._released = 0
        self._live_ids: set[tuple[str, str]] = set()
        self._peak_live = 0

    def build(self, seeds: Mapping[str, StateView]) -> ReachableChart:
        if not seeds:
            raise ValueError("at least one task seed is required")
        task_ids = tuple(sorted(seeds))
        if any(not task_id for task_id in task_ids):
            raise ValueError("task IDs must be nonempty")

        expected_words = len(task_ids) * sum(
            len(self.action_ids) ** depth
            for depth in range(self.limits.max_depth + 1)
        )
        if expected_words > self.limits.max_word_occurrences:
            raise ChartPrerequisiteBlocked("maximum symbolic word occurrences reached")

        chart = ReachableChart(
            action_ids=self.action_ids,
            limits=self.limits,
            state_table={},
            transition_table={},
            word_table={},
            word_censors={},
            transition_censors={},
            task_ids=task_ids,
            primary_attempts=0,
            replay_attempts=0,
            peak_live_state_count=0,
            released_live_state_count=0,
        )
        task_state_keys: dict[str, set[bytes]] = {task_id: set() for task_id in task_ids}

        for task_id in task_ids:
            seed = seeds[task_id]
            if not seed.response_signature:
                raise ChartPrerequisiteBlocked(
                    f"missing open response evidence for seed {task_id}"
                )
            self._admit_state(chart, task_state_keys, task_id, seed)
            chart.word_table[(task_id, ())] = WordOutcome.from_state(seed)

        for depth in range(self.limits.max_depth):
            frontier_keys = {
                outcome.state_key
                for (task_id, word), outcome in chart.word_table.items()
                if len(word) == depth and outcome.kind is OutcomeKind.OPEN
            }
            for key in sorted(frontier_keys):
                if key is None:
                    raise AssertionError("open frontier state has no key")
                entry = chart.state_table[key]
                if entry.expansion_status == "queued":
                    self._expand_state(chart, task_state_keys, entry)

            for task_id in task_ids:
                for parent_word in words_at_depth(self.action_ids, depth):
                    parent_key = (task_id, parent_word)
                    parent_censor = chart.word_censors.get(parent_key)
                    parent = chart.word_table.get(parent_key)
                    for action in self.action_ids:
                        word = parent_word + (action,)
                        key = (task_id, word)
                        if parent_censor is not None:
                            chart.word_censors[key] = CensorRecord(
                                reason=parent_censor.reason,
                                source_key=parent_censor.source_key,
                                action_id=action,
                                derived_from_prefix=True,
                            )
                            continue
                        if parent is None:
                            raise ChartPrerequisiteBlocked(
                                f"missing parent word {task_id}:{parent_word!r}"
                            )
                        if parent.kind is not OutcomeKind.OPEN:
                            chart.word_table[key] = derived_terminal_extension(parent)
                            continue
                        edge_key = (parent.state_key, action)
                        censor = chart.transition_censors.get(edge_key)
                        if censor is not None:
                            chart.word_censors[key] = censor
                            continue
                        event = chart.transition_table.get(edge_key)
                        if event is None:
                            raise ChartPrerequisiteBlocked(
                                "unsealed concrete state/action row"
                            )
                        if event.totalized_status is OutcomeKind.OPEN:
                            if event.target is None:
                                raise AssertionError("open event lacks target")
                            if not event.target.response_signature:
                                raise ChartPrerequisiteBlocked(
                                    "missing open response evidence for transition target"
                                )
                            self._register_task_reach(
                                chart,
                                task_state_keys,
                                task_id,
                                event.target.identity_key,
                            )
                            chart.word_table[key] = WordOutcome.from_state(event.target)
                        else:
                            if event.totalized_status is None:
                                raise AssertionError("noncensor event lacks status")
                            chart.word_table[key] = WordOutcome.terminal(
                                event.totalized_status,
                                entry_task_id=task_id,
                                entry_source_key=event.source_key,
                                entry_action_id=event.action_id,
                                entry_word=word,
                            )

        chart.peak_live_state_count = self._peak_live
        chart.released_live_state_count = self._released
        if chart.word_occurrence_count != expected_words:
            raise ChartPrerequisiteBlocked("word table is not prefix-closed")
        return chart

    def _admit_state(
        self,
        chart: ReachableChart,
        task_state_keys: dict[str, set[bytes]],
        task_id: str,
        state: StateView,
    ) -> StateTableEntry:
        key = state.identity_key
        # A concrete open response has already allocated this child in the
        # worker.  Track it first as the single transient slot; admission either
        # promotes it to the queued frontier or immediately releases a duplicate.
        self._track_live(task_id, state.live_rpc_state_id)
        existing = chart.state_table.get(key)
        if existing is not None:
            if existing.full_signature != state.full_signature:
                self._release(task_id, state.live_rpc_state_id)
                raise ChartPrerequisiteBlocked(
                    "identity hash/key collision failed full-signature comparison"
                )
            if existing.debt != state.debt:
                self._release(task_id, state.live_rpc_state_id)
                raise ChartPrerequisiteBlocked(
                    "equal state identity produced a different debt vector"
                )
            self._release(task_id, state.live_rpc_state_id)
            existing.task_ids.add(task_id)
            task_state_keys[task_id].add(key)
            self._check_per_task_cap(task_state_keys, task_id)
            return existing

        if len(chart.state_table) >= self.limits.max_states_total:
            self._release(task_id, state.live_rpc_state_id)
            raise ChartPrerequisiteBlocked("maximum unique states total reached")
        task_state_keys[task_id].add(key)
        try:
            self._check_per_task_cap(task_state_keys, task_id)
        except ChartPrerequisiteBlocked:
            task_state_keys[task_id].remove(key)
            self._release(task_id, state.live_rpc_state_id)
            raise
        entry = StateTableEntry(
            identity_key=key,
            full_signature=state.full_signature,
            debt=state.debt,
            expansion_status="queued",
            live_rpc_state_id=state.live_rpc_state_id,
            first_task_id=task_id,
            task_ids={task_id},
        )
        chart.state_table[key] = entry
        return entry

    def _check_per_task_cap(
        self, task_state_keys: Mapping[str, set[bytes]], task_id: str
    ) -> None:
        if len(task_state_keys[task_id]) > self.limits.max_states_per_task:
            raise ChartPrerequisiteBlocked(
                f"maximum unique states reached for task {task_id}"
            )

    def _register_task_reach(
        self,
        chart: ReachableChart,
        task_state_keys: dict[str, set[bytes]],
        task_id: str,
        state_key: bytes,
    ) -> None:
        """Account for a task occurrence that reused an already sealed row."""

        if state_key not in chart.state_table:
            raise ChartPrerequisiteBlocked("transition references an unknown state")
        if state_key in task_state_keys[task_id]:
            return
        task_state_keys[task_id].add(state_key)
        try:
            self._check_per_task_cap(task_state_keys, task_id)
        except ChartPrerequisiteBlocked:
            task_state_keys[task_id].remove(state_key)
            raise
        chart.state_table[state_key].task_ids.add(task_id)

    def _expand_state(
        self,
        chart: ReachableChart,
        task_state_keys: dict[str, set[bytes]],
        entry: StateTableEntry,
    ) -> None:
        if entry.expansion_status != "queued":
            return
        if entry.live_rpc_state_id is None:
            raise ChartPrerequisiteBlocked("queued state lacks a live RPC state ID")
        source = entry.state_view()
        task_id = entry.first_task_id
        for action in self.action_ids:
            if chart.primary_attempts + 1 > self.limits.max_primary_attempts:
                raise ChartPrerequisiteBlocked("maximum primary attempts reached")
            event = self.oracle(task_id, source, action)
            if not isinstance(event, OracleEvent):
                raise ChartPrerequisiteBlocked("oracle returned a non-OracleEvent")
            if event.source_key != entry.identity_key or event.action_id != action:
                raise ChartPrerequisiteBlocked("oracle response identity mismatch")
            chart.primary_attempts += event.primary_attempts
            chart.replay_attempts += event.replay_attempts
            if chart.primary_attempts > self.limits.max_primary_attempts:
                raise ChartPrerequisiteBlocked("maximum primary attempts reached")
            if chart.replay_attempts > self.limits.max_replay_attempts:
                raise ChartPrerequisiteBlocked("maximum replay attempts reached")

            edge_key = (entry.identity_key, action)
            if event.is_censor:
                chart.transition_censors[edge_key] = CensorRecord(
                    reason=event.censor_reason or "unknown_censor",
                    source_key=entry.identity_key,
                    action_id=action,
                )
                continue
            if not event.replay_verified:
                chart.transition_censors[edge_key] = CensorRecord(
                    reason="independent_replay_not_verified",
                    source_key=entry.identity_key,
                    action_id=action,
                )
                if event.target is not None:
                    self._release(task_id, event.target.live_rpc_state_id)
                continue
            if event.totalized_status is OutcomeKind.OPEN:
                if event.target is None:
                    raise ChartPrerequisiteBlocked("open event lacks target")
                if not event.target.response_signature:
                    self._release(task_id, event.target.live_rpc_state_id)
                    raise ChartPrerequisiteBlocked(
                        "missing open response evidence for transition target"
                    )
                self._admit_state(chart, task_state_keys, task_id, event.target)
                # The worker handle belongs only to the queued state-table
                # entry.  Sealed transition rows must not retain a stale child
                # handle after deduplication or later expansion/release.
                event = replace(
                    event,
                    target=replace(event.target, live_rpc_state_id=None),
                )
            chart.transition_table[edge_key] = event

        self._release(task_id, entry.live_rpc_state_id)
        entry.live_rpc_state_id = None
        entry.expansion_status = "expanded"

    def _track_live(self, task_id: str, live_id: str | None) -> None:
        if live_id is None:
            return
        token = (task_id, live_id)
        if token in self._live_ids:
            raise ChartPrerequisiteBlocked("duplicate live RPC state ID")
        self._live_ids.add(token)
        self._peak_live = max(self._peak_live, len(self._live_ids))

    def _release(self, task_id: str, live_id: str | None) -> None:
        if live_id is None:
            return
        token = (task_id, live_id)
        if token in self._live_ids:
            self._live_ids.remove(token)
        if self.discard_live_state is not None:
            self.discard_live_state(task_id, live_id)
        self._released += 1


def build_reachable_chart(
    *,
    seeds: Mapping[str, StateView],
    actions: Iterable[object],
    oracle: TransitionOracle,
    limits: ChartLimits | None = None,
    discard_live_state: DiscardLiveState | None = None,
) -> ReachableChart:
    """Convenience wrapper around :class:`ReachableChartBuilder`."""

    return ReachableChartBuilder(
        actions=actions,
        oracle=oracle,
        limits=limits,
        discard_live_state=discard_live_state,
    ).build(seeds)


__all__ = [
    "ChartLimits",
    "ChartPrerequisiteBlocked",
    "ReachableChart",
    "ReachableChartBuilder",
    "StateTableEntry",
    "TransitionOracle",
    "build_reachable_chart",
]
