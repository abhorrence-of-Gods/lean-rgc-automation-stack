"""Deterministic finite rule algebra used by the U'0.5 development probes.

This module deliberately has no dependency on the native RPC contracts.  The
RPC adapter may supply contract objects, mappings, or plain action identifiers;
the measurement core reduces them to the frozen symbolic ``action_id`` only.
Concrete failures are totalized to ``SINK`` while resource/transport failures
remain censors outside the transition algebra.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from itertools import product
from typing import Any, Iterable, Iterator, Mapping, Sequence


DebtVector = tuple[int, int, int, int, int]
ActionWord = tuple[str, ...]
TOTALIZATION_RULE_DIGEST = hashlib.sha256(
    b"lean-rgc-u05-totalization-v1:closed->CLOSED;ordinary_failure->SINK;terminal_absorbing"
).hexdigest().upper()


class OutcomeKind(str, Enum):
    """Totalized state kind in the finite action algebra."""

    OPEN = "open"
    CLOSED = "closed"
    SINK = "sink"


@dataclass(frozen=True)
class StateView:
    """Minimal exact-state view consumed by the deterministic apparatus.

    ``identity_key`` and ``full_signature`` are bytes so ordering and equality
    never depend on Python object identity.  The RPC adapter is responsible for
    constructing those canonical bytes.  ``response_signature`` is occurrence
    level diagnostic material and is intentionally not used for deduplication.
    """

    identity_key: bytes
    full_signature: bytes
    debt: DebtVector
    live_rpc_state_id: str | None
    response_signature: bytes = b""

    def __post_init__(self) -> None:
        if not isinstance(self.identity_key, bytes) or not self.identity_key:
            raise ValueError("identity_key must be nonempty bytes")
        if not isinstance(self.full_signature, bytes) or not self.full_signature:
            raise ValueError("full_signature must be nonempty bytes")
        if len(self.debt) != 5 or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in self.debt
        ):
            raise ValueError("debt must contain exactly five nonnegative integers")
        if self.live_rpc_state_id is not None and not self.live_rpc_state_id:
            raise ValueError("live_rpc_state_id must be nonempty when present")
        if not isinstance(self.response_signature, bytes):
            raise ValueError("response_signature must be bytes")

    @property
    def behavioral_observation(self) -> tuple[str, int, int, int, int, int]:
        """The frozen ``u05_current_observation_v1`` projection."""

        return (OutcomeKind.OPEN.value, *self.debt)


@dataclass(frozen=True)
class CensorRecord:
    """A resource/transport/instrument failure that creates no transition."""

    reason: str
    source_key: bytes | None = None
    action_id: str | None = None
    derived_from_prefix: bool = False

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("censor reason must be nonempty")


@dataclass(frozen=True)
class OracleEvent:
    """One concrete replayed transition attempt or one censor.

    ``ordinary_failure`` is represented by ``raw_status`` together with a
    totalized ``SINK`` status.  A censor has ``totalized_status=None`` and no
    target.  Replay and exact-delta flags remain explicit so individual probes
    can fail closed rather than silently accepting a partial RPC response.
    """

    source_key: bytes
    action_id: str
    raw_status: str
    totalized_status: OutcomeKind | None
    target: StateView | None = None
    replay_verified: bool = True
    exact_delta: bool = True
    censor_reason: str | None = None
    primary_attempts: int = 1
    replay_attempts: int = 1
    derived_from_sealed_row: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_key, bytes) or not self.source_key:
            raise ValueError("source_key must be nonempty bytes")
        if not self.action_id:
            raise ValueError("action_id must be nonempty")
        if self.primary_attempts < 0 or self.replay_attempts < 0:
            raise ValueError("attempt counters must be nonnegative")
        if self.derived_from_sealed_row and (
            self.primary_attempts != 0
            or self.replay_attempts != 0
            or self.censor_reason is not None
            or not self.replay_verified
            or not self.exact_delta
            or (
                self.target is not None
                and self.target.live_rpc_state_id is not None
            )
        ):
            raise ValueError(
                "a sealed-row derivation must be exact, replayed, handle-free, and zero-attempt"
            )
        if self.censor_reason is not None:
            if self.totalized_status is not None or self.target is not None:
                raise ValueError("a censor cannot create a totalized transition")
            if not self.censor_reason:
                raise ValueError("censor reason must be nonempty")
            return
        if self.totalized_status is None:
            raise ValueError("noncensored events require a totalized status")
        if self.totalized_status is OutcomeKind.OPEN:
            if self.target is None:
                raise ValueError("an open transition requires a target state")
        elif self.target is not None:
            raise ValueError("closed and sink transitions cannot retain a target")
        if self.raw_status == "ordinary_failure" and (
            self.totalized_status is not OutcomeKind.SINK
        ):
            raise ValueError("ordinary failure must totalize to sink")

    @classmethod
    def open(
        cls,
        source_key: bytes,
        action_id: str,
        target: StateView,
        *,
        replay_verified: bool = True,
        exact_delta: bool = True,
    ) -> "OracleEvent":
        return cls(
            source_key=source_key,
            action_id=action_id,
            raw_status="open",
            totalized_status=OutcomeKind.OPEN,
            target=target,
            replay_verified=replay_verified,
            exact_delta=exact_delta,
        )

    @classmethod
    def closed(
        cls,
        source_key: bytes,
        action_id: str,
        *,
        replay_verified: bool = True,
        exact_delta: bool = True,
    ) -> "OracleEvent":
        return cls(
            source_key=source_key,
            action_id=action_id,
            raw_status="closed",
            totalized_status=OutcomeKind.CLOSED,
            replay_verified=replay_verified,
            exact_delta=exact_delta,
        )

    @classmethod
    def ordinary_failure(
        cls,
        source_key: bytes,
        action_id: str,
        *,
        replay_verified: bool = True,
        exact_delta: bool = True,
        primary_attempts: int = 1,
        replay_attempts: int = 1,
    ) -> "OracleEvent":
        return cls(
            source_key=source_key,
            action_id=action_id,
            raw_status="ordinary_failure",
            totalized_status=OutcomeKind.SINK,
            replay_verified=replay_verified,
            exact_delta=exact_delta,
            primary_attempts=primary_attempts,
            replay_attempts=replay_attempts,
        )

    @classmethod
    def censor(
        cls,
        source_key: bytes,
        action_id: str,
        reason: str,
        *,
        primary_attempts: int = 1,
        replay_attempts: int = 0,
    ) -> "OracleEvent":
        return cls(
            source_key=source_key,
            action_id=action_id,
            raw_status="censor",
            totalized_status=None,
            censor_reason=reason,
            replay_verified=False,
            exact_delta=False,
            primary_attempts=primary_attempts,
            replay_attempts=replay_attempts,
        )

    @property
    def is_censor(self) -> bool:
        return self.censor_reason is not None


@dataclass(frozen=True)
class WordOutcome:
    """Outcome of one exact task/action-word occurrence."""

    kind: OutcomeKind
    state_key: bytes | None = None
    response_signature: bytes = b""
    derived_terminal: bool = False
    totalization_rule_digest: str | None = None
    entry_task_id: str | None = None
    entry_source_key: bytes | None = None
    entry_action_id: str | None = None
    entry_word: ActionWord | None = None

    def __post_init__(self) -> None:
        if self.kind is OutcomeKind.OPEN and self.state_key is None:
            raise ValueError("open word outcome requires a state key")
        if self.kind is not OutcomeKind.OPEN and self.state_key is not None:
            raise ValueError("terminal word outcome cannot contain a state key")
        if not isinstance(self.response_signature, bytes):
            raise ValueError("response_signature must be bytes")
        provenance = (
            self.totalization_rule_digest,
            self.entry_task_id,
            self.entry_source_key,
            self.entry_action_id,
            self.entry_word,
        )
        if self.kind is OutcomeKind.OPEN:
            if not self.response_signature:
                raise ValueError("open word outcome requires nonempty response evidence")
            if self.derived_terminal or any(value is not None for value in provenance):
                raise ValueError("open word outcome cannot carry terminal provenance")
            return
        if self.response_signature:
            raise ValueError("terminal word outcome cannot carry an open response signature")
        if any(value is None for value in provenance):
            raise ValueError("terminal word outcome requires complete entry provenance")
        digest = self.totalization_rule_digest
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789ABCDEF" for ch in digest)
        ):
            raise ValueError("terminal totalization rule digest must be uppercase SHA-256")
        if digest != TOTALIZATION_RULE_DIGEST:
            raise ValueError("terminal totalization rule digest is not the frozen rule")
        if not isinstance(self.entry_task_id, str) or not self.entry_task_id:
            raise ValueError("terminal entry task ID must be nonempty")
        if not isinstance(self.entry_source_key, bytes) or not self.entry_source_key:
            raise ValueError("terminal entry source key must be nonempty bytes")
        if not isinstance(self.entry_action_id, str) or not self.entry_action_id:
            raise ValueError("terminal entry action ID must be nonempty")
        if not isinstance(self.entry_word, tuple) or not self.entry_word:
            raise ValueError("terminal entry word must be a nonempty action word")
        if self.entry_word[-1] != self.entry_action_id:
            raise ValueError("terminal entry word/action provenance mismatch")

    @classmethod
    def from_state(cls, state: StateView) -> "WordOutcome":
        return cls(
            kind=OutcomeKind.OPEN,
            state_key=state.identity_key,
            response_signature=state.response_signature,
        )

    @classmethod
    def terminal(
        cls,
        kind: OutcomeKind,
        *,
        entry_task_id: str,
        entry_source_key: bytes,
        entry_action_id: str,
        entry_word: ActionWord,
        totalization_rule_digest: str = TOTALIZATION_RULE_DIGEST,
        derived: bool = False,
    ) -> "WordOutcome":
        if kind is OutcomeKind.OPEN:
            raise ValueError("terminal outcome must be CLOSED or SINK")
        return cls(
            kind=kind,
            derived_terminal=derived,
            totalization_rule_digest=totalization_rule_digest,
            entry_task_id=entry_task_id,
            entry_source_key=entry_source_key,
            entry_action_id=entry_action_id,
            entry_word=entry_word,
        )


def action_id(action: Any) -> str:
    """Extract a fixed symbolic action ID without importing RPC contracts."""

    value: Any
    if isinstance(action, str):
        value = action
    elif isinstance(action, Mapping):
        value = action.get("action_id")
    else:
        value = getattr(action, "action_id", None)
    if not isinstance(value, str) or not value:
        raise ValueError("every action must expose a nonempty action_id")
    return value


def canonical_action_ids(actions: Iterable[Any]) -> tuple[str, ...]:
    """Return the deterministic alphabet, rejecting duplicate identities."""

    values = tuple(sorted(action_id(action) for action in actions))
    if len(set(values)) != len(values):
        raise ValueError("duplicate action_id in fixed alphabet")
    if not values:
        raise ValueError("fixed action alphabet cannot be empty")
    return values


def action_words(
    action_ids: Sequence[str], max_depth: int, *, include_empty: bool = True
) -> Iterator[ActionWord]:
    """Yield words by length and then lexicographic action ID order."""

    if max_depth < 0:
        raise ValueError("max_depth must be nonnegative")
    alphabet = tuple(action_ids)
    if tuple(sorted(alphabet)) != alphabet or len(set(alphabet)) != len(alphabet):
        raise ValueError("action_ids must be unique and lexicographically sorted")
    if include_empty:
        yield ()
    for depth in range(1, max_depth + 1):
        yield from product(alphabet, repeat=depth)


def words_at_depth(action_ids: Sequence[str], depth: int) -> Iterator[ActionWord]:
    if depth < 0:
        raise ValueError("depth must be nonnegative")
    alphabet = tuple(action_ids)
    if tuple(sorted(alphabet)) != alphabet or len(set(alphabet)) != len(alphabet):
        raise ValueError("action_ids must be unique and lexicographically sorted")
    if depth == 0:
        yield ()
        return
    yield from product(alphabet, repeat=depth)


def derived_terminal_extension(parent: WordOutcome) -> WordOutcome:
    """Apply one symbolic action to an absorbing terminal outcome."""

    if parent.kind is OutcomeKind.OPEN:
        raise ValueError("open outcomes are not terminal")
    if parent.totalization_rule_digest is None:
        raise ValueError("terminal parent lacks totalization provenance")
    return WordOutcome.terminal(
        parent.kind,
        entry_task_id=parent.entry_task_id or "",
        entry_source_key=parent.entry_source_key or b"",
        entry_action_id=parent.entry_action_id or "",
        entry_word=parent.entry_word or (),
        totalization_rule_digest=parent.totalization_rule_digest,
        derived=True,
    )


def final_response_channels(
    outcome: WordOutcome, state: StateView | None
) -> tuple[int, int, int, int, int, int, int]:
    """Return the seven frozen integer Hankel response channels."""

    if outcome.kind is OutcomeKind.CLOSED:
        return (1, 0, 0, 0, 0, 0, 0)
    if outcome.kind is OutcomeKind.SINK:
        return (0, 1, 0, 0, 0, 0, 0)
    if state is None or state.identity_key != outcome.state_key:
        raise ValueError("open response requires its exact state view")
    return (0, 0, *state.debt)


__all__ = [
    "ActionWord",
    "CensorRecord",
    "DebtVector",
    "OracleEvent",
    "OutcomeKind",
    "StateView",
    "TOTALIZATION_RULE_DIGEST",
    "WordOutcome",
    "action_id",
    "action_words",
    "canonical_action_ids",
    "derived_terminal_extension",
    "final_response_channels",
    "words_at_depth",
]
