"""Bounded native closure admission for the conditional KP3-D4 chart.

The closure algorithm is deliberately transport independent.  A strict facade
owns one native worker, initializes every registered task in that worker, and
returns opaque handles plus fully materialized semantic observations.  This
module never treats a native state handle as an identity: the identity is the
32-byte canonical-index digest, guarded by the complete signature, response,
and debt readout on every occurrence.

Passing this admission establishes only ``CONDITIONAL_KSTATE_MARKOV``.  The
duplicate-handle audit is a bounded falsification attempt, not a proof that the
native projection is Markov.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
import weakref

from lean_rgc.odlrq.hankel_depth4 import (
    MAX_EXACT_COEFFICIENT_BITS,
    RANK_LOWER_BOUND_SIZE,
    RANK_CERTIFICATE_SCHEMA,
    RawHankelRowKey,
    _column_coordinate_digest,
    _action_words,
    _elimination_transcript_digest,
    _fraction_verifier_scan,
    _matrix_binding_wire,
    _row_coordinate_digest,
    _sha256 as _hankel_sha256,
    ExactRankCertificate,
    ExactRankCertificateKind,
    ExactRankVerificationReport,
    ExactRawCoordinateHankel,
    build_exact_raw_coordinate_hankel,
    certify_hankel_family,
    verify_exact_rank_certificate,
)
from lean_rgc.odlrq.history_normal_form import (
    ACTION_GRAMMAR_SCHEMA,
    CONDITIONAL_KSTATE_MARKOV,
    MAX_ACTIONS,
    MAX_OPEN_STATES,
    MAX_TRANSITION_ROWS,
    CanonicalHistoryChart,
    CanonicalKStateMarkovContract,
    ExactOpenState,
    ExactOutcomeKind,
    FiniteTotalActionDomain,
    FlowVerificationReport,
    HistoryContractError,
    HISTORY_GRAMMAR_SCHEMA,
    RawNormalizedEqualityReport,
    SealedTransitionRow,
    TaskSeed,
    build_finite_total_action_domain,
    verify_flow_conservation,
    verify_generation_time_equals_batch,
    verify_raw_normalized_equality,
)
from lean_rgc.odlrq.contracts import (
    ActionSymbol,
    CensorKind,
    StrictContractError,
    U05TaskSpec,
)
from lean_rgc.odlrq.rule_algebra import OutcomeKind
from lean_rgc.lean.kernel_rpc_client import (
    KernelRPCProcessExited,
    KernelRPCTransportError,
    KernelRPCTransportTimeout,
    RuntimeStateView,
    StrictKernelRPCError,
    StrictKernelRPCOracleAdapter,
    SynchronousJSONLSubprocessTransport,
)


NATIVE_CLOSURE_SCHEMA = "lean-rgc-uprime-kp3-d4-native-closure-v1"
NATIVE_RESULT_SCHEMA = "lean-rgc-uprime-kp3-d4-native-result-v1"
MAX_DUPLICATE_OCCURRENCES = 128
MAX_NATIVE_SECONDS = 3_600
MAX_ACTION_SECONDS = 30
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_RESULT_BYTES = 64 * 1024 * 1024
REGISTERED_TASK_RAW_SHA256 = "C0B5428DCB7174CB96F469E38E229043AF47B9E9ECF684797FF45EE8AE4163A0"
REGISTERED_TASK_CANONICAL_SHA256 = "814BFBC235B6E464013637210E1C5382B0CED5AEB0C8D50C9C282E3236202D62"
REGISTERED_TASK_ROWS_SHA256 = "402410B252C71EFFF250437D9715ECA7A39F433BE056DF5D1997D9EB2FDECB95"
REGISTERED_ACTION_RAW_SHA256 = "FC9FB44E8E5D6929712CE15DC2D6F93FCCA74B81EE99C9EAF55D13B76A0CCF51"
REGISTERED_ACTION_CANONICAL_SHA256 = "BE4AC0348631D0D7E3ABCA3DD22A05240E1D86B494B21FDBB47EF7FADA99FB1A"
REGISTERED_ACTION_ROWS_SHA256 = "8A203CD2C993ABECECEE860A071C75E4C81A5E9E1D87CA37F8E7CC5AEEC879DE"
REGISTERED_TASK_PATH = Path("docs/experiments/inputs/uprime_kp3_d4_fresh_tasks.json")
REGISTERED_ACTION_PATH = Path("docs/experiments/inputs/uprime_kp3_d4_actions.json")
OFFICIAL_ARTIFACT_SCHEMA = "lean-rgc-uprime-kp3-d4-fresh-family-v1.0"
OFFICIAL_RECEIPT_SCHEMA = "lean-rgc-uprime-kp3-d4-stage-receipt-v1.0"
OFFICIAL_LEAN_SHA256 = "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
OFFICIAL_WORKER_BLOB = "305509d9b89081a3d002734e09724b98e244a24c"
OFFICIAL_RPC_CLIENT_BLOB = "ef5d81bff4c6ab4d8110fe6671f5e5b5f8bc263a"
OFFICIAL_PYTHON_SHA256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
OFFICIAL_POWERSHELL_SHA256 = "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46"
OFFICIAL_CONTROL_SCOPE = "EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER"
OFFICIAL_C2_ALLOWLIST = frozenset(
    {
        "lean_rgc/evals/uprime_kp3_d4_canonical_history.py",
        "tests/test_uprime_kp3_d4_canonical_history.py",
        "tools/run_uprime_kp3_d4_native_tests.ps1",
        "tools/run_uprime_kp3_d4_fresh_execution.ps1",
        "tests/tier_manifest.json",
    }
)


class NativeClosureError(RuntimeError):
    """The native facade or its output violated the frozen C2 contract."""


class NativeNormalizationError(NativeClosureError):
    """A canonical merge or duplicate-row equality check was unsound."""


class NativeDomainError(NativeClosureError):
    """The registered native action domain could not be sealed totally."""


class NativeResourceError(NativeClosureError):
    """A preregistered cardinality, byte, or wall envelope was exceeded."""


class NativeExecutionError(NativeClosureError):
    """The fixed execution failed outside a scientific-domain classification."""


_PRODUCTION_RESULT_PROVENANCE: dict[int, tuple[Any, ...]] = {}
_REGISTERED_INPUT_PROVENANCE: dict[tuple[int, ...], tuple[Any, ...]] = {}
_KERNEL_FACTORY_PROVENANCE: dict[int, tuple[Any, ...]] = {}
_KERNEL_SESSION_PROVENANCE: dict[int, tuple[Any, ...]] = {}


def _text(value: Any, where: str) -> str:
    if type(value) is not str or not value:
        raise NativeClosureError(f"{where} must be an exact nonempty string")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise NativeClosureError(f"{where} is not strict UTF-8") from exc
    return value


def _blob(value: Any, where: str, *, exact: int | None = None) -> bytes:
    if type(value) is not bytes or not value:
        raise NativeClosureError(f"{where} must be exact nonempty bytes")
    if exact is not None and len(value) != exact:
        raise NativeClosureError(f"{where} has the wrong byte length")
    if len(value) > 64 * 1024:
        raise NativeClosureError(f"{where} exceeds the frozen byte cap")
    return value


def _utf8(value: Any, where: str) -> bytes:
    raw = _blob(value, where)
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise NativeClosureError(f"{where} is not strict UTF-8 bytes") from exc
    return raw


def _digest(value: Any, where: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(ch not in "0123456789ABCDEF" for ch in value)
    ):
        raise NativeClosureError(f"{where} must be uppercase SHA-256")
    return value


def _integer(value: Any, where: str) -> int:
    if type(value) is not int or value < 0 or value > (1 << 63) - 1:
        raise NativeClosureError(f"{where} must be a nonnegative signed-64 integer")
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise NativeClosureError("value is outside canonical JSON") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


@dataclass(frozen=True)
class NativeTask:
    task_id: str
    payload: Mapping[str, Any]
    _payload_seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _text(self.task_id, "task_id")
        if type(self.payload) is not dict:
            raise NativeClosureError("task payload must be an exact object")
        snapshot = json.loads(_canonical_bytes(self.payload).decode("utf-8"))
        object.__setattr__(self, "payload", snapshot)
        object.__setattr__(self, "_payload_seal", _sha(snapshot))

    def validate(self) -> None:
        _text(self.task_id, "task_id")
        if type(self.payload) is not dict or _sha(self.payload) != self._payload_seal:
            raise NativeClosureError("task payload mutation detected")


@dataclass(frozen=True)
class NativeAction:
    action_id: str
    payload: Mapping[str, Any]
    _payload_seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _text(self.action_id, "action_id")
        if type(self.payload) is not dict:
            raise NativeClosureError("action payload must be an exact object")
        snapshot = json.loads(_canonical_bytes(self.payload).decode("utf-8"))
        object.__setattr__(self, "payload", snapshot)
        object.__setattr__(self, "_payload_seal", _sha(snapshot))

    def validate(self) -> None:
        _text(self.action_id, "action_id")
        if type(self.payload) is not dict or _sha(self.payload) != self._payload_seal:
            raise NativeClosureError("action payload mutation detected")


def _mint_registered_input_receipt(
    tasks: tuple[NativeTask, ...], actions: tuple[NativeAction, ...]
) -> str:
    if len(tasks) != 5 or len(actions) != 12:
        raise NativeClosureError("registered receipt requires exactly 5 tasks/12 actions")
    for row in tasks:
        row.validate()
    for row in actions:
        row.validate()
    key = tuple(id(row) for row in (*tasks, *actions))
    receipt = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-registered-input-authority-v1",
            "task_raw_sha256": REGISTERED_TASK_RAW_SHA256,
            "task_canonical_sha256": REGISTERED_TASK_CANONICAL_SHA256,
            "task_rows_sha256": REGISTERED_TASK_ROWS_SHA256,
            "action_raw_sha256": REGISTERED_ACTION_RAW_SHA256,
            "action_canonical_sha256": REGISTERED_ACTION_CANONICAL_SHA256,
            "action_rows_sha256": REGISTERED_ACTION_ROWS_SHA256,
            "tasks": [[row.task_id, row._payload_seal] for row in tasks],
            "actions": [[row.action_id, row._payload_seal] for row in actions],
        }
    )
    references = tuple(weakref.ref(row) for row in (*tasks, *actions))
    _REGISTERED_INPUT_PROVENANCE[key] = (
        references,
        tuple(row._payload_seal for row in tasks),
        tuple(row._payload_seal for row in actions),
        receipt,
    )
    return receipt


def _registered_input_receipt(
    tasks: tuple[NativeTask, ...], actions: tuple[NativeAction, ...]
) -> str | None:
    key = tuple(id(row) for row in (*tasks, *actions))
    retained = _REGISTERED_INPUT_PROVENANCE.get(key)
    if retained is None or len(retained[0]) != 17:
        return None
    current = (*tasks, *actions)
    if any(reference() is not row for reference, row in zip(retained[0], current, strict=True)):
        return None
    try:
        for row in tasks:
            row.validate()
        for row in actions:
            row.validate()
    except NativeClosureError:
        return None
    if (
        tuple(row._payload_seal for row in tasks) != retained[1]
        or tuple(row._payload_seal for row in actions) != retained[2]
    ):
        return None
    expected = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-registered-input-authority-v1",
            "task_raw_sha256": REGISTERED_TASK_RAW_SHA256,
            "task_canonical_sha256": REGISTERED_TASK_CANONICAL_SHA256,
            "task_rows_sha256": REGISTERED_TASK_ROWS_SHA256,
            "action_raw_sha256": REGISTERED_ACTION_RAW_SHA256,
            "action_canonical_sha256": REGISTERED_ACTION_CANONICAL_SHA256,
            "action_rows_sha256": REGISTERED_ACTION_ROWS_SHA256,
            "tasks": [[row.task_id, row._payload_seal] for row in tasks],
            "actions": [[row.action_id, row._payload_seal] for row in actions],
        }
    )
    return retained[3] if retained[3] == expected else None


@dataclass(frozen=True)
class NativeOpenObservation:
    handle: object
    index_sha256: bytes
    full_signature: bytes
    debt: tuple[int, int, int, int, int]
    response_signature: bytes

    def __post_init__(self) -> None:
        if self.handle is None:
            raise NativeClosureError("OPEN observation lacks an owned handle")
        _blob(self.index_sha256, "index_sha256", exact=32)
        _utf8(self.full_signature, "full_signature")
        _utf8(self.response_signature, "response_signature")
        if type(self.debt) is not tuple or len(self.debt) != 5:
            raise NativeClosureError("debt must be an exact five-tuple")
        for index, item in enumerate(self.debt):
            _integer(item, f"debt[{index}]")

    @property
    def exact_state(self) -> ExactOpenState:
        return ExactOpenState(
            self.index_sha256,
            self.full_signature,
            self.debt,
            self.response_signature,
        )


@dataclass(frozen=True)
class NativeTransition:
    kind: ExactOutcomeKind | str
    replay_verified: bool
    replay_digest: str
    semantic_signature: bytes
    target: NativeOpenObservation | None = None
    verification_mode: str = "replay_verified_success"
    elapsed_ms: int = 0
    censor_reason: str | None = None

    def __post_init__(self) -> None:
        if self.kind != "censor" and type(self.kind) is not ExactOutcomeKind:
            raise NativeClosureError("transition kind is outside the strict vocabulary")
        if type(self.replay_verified) is not bool:
            raise NativeClosureError("replay_verified must be an exact bool")
        _digest(self.replay_digest, "replay_digest")
        _utf8(self.semantic_signature, "semantic_signature")
        _text(self.verification_mode, "verification_mode")
        _integer(self.elapsed_ms, "transition elapsed_ms")
        if self.elapsed_ms > MAX_ACTION_SECONDS * 1_000:
            raise NativeResourceError("transition exceeded its 30-second wall")
        if self.censor_reason is not None:
            _text(self.censor_reason, "censor_reason")
        if self.kind is ExactOutcomeKind.OPEN:
            if type(self.target) is not NativeOpenObservation:
                raise NativeClosureError("OPEN transition lacks an exact target")
            if (
                self.verification_mode != "replay_verified_success"
                or self.censor_reason is not None
            ):
                raise NativeClosureError("OPEN transition has terminal metadata")
        elif self.target is not None:
            raise NativeClosureError("terminal/censor transition retained an OPEN handle")
        if self.kind is ExactOutcomeKind.SINK:
            if self.verification_mode not in {
                "deterministic_syntactic_sink",
                "replay_verified_failure",
            } or self.censor_reason is not None:
                raise NativeClosureError("SINK lacks an explicit verified totalization mode")
        elif self.kind is ExactOutcomeKind.CLOSED:
            if self.verification_mode != "replay_verified_success":
                raise NativeClosureError("CLOSED transition verification mode mismatch")
        elif self.kind == "censor":
            if self.verification_mode != "rpc_censor" or self.censor_reason is None:
                raise NativeClosureError("censor lacks its explicit verification mode/reason")
        if (
            not self.replay_verified
            and self.verification_mode
            not in {"deterministic_syntactic_sink", "rpc_censor"}
        ):
            raise NativeClosureError("concrete transition lacks independent replay")


class StrictNativeSession(Protocol):
    """One-owner facade; implementations must not alias/consume input handles."""

    def initialize(self, task: NativeTask) -> NativeOpenObservation: ...

    def apply(
        self, source_handle: object, action: NativeAction
    ) -> NativeTransition: ...

    def close_handle(self, handle: object) -> None: ...

    def close(self) -> None: ...


class StrictNativeFactory(Protocol):
    def open(self, tasks: tuple[NativeTask, ...]) -> StrictNativeSession: ...


def _runtime_observation(runtime: RuntimeStateView) -> NativeOpenObservation:
    if type(runtime) is not RuntimeStateView:
        raise NativeClosureError("strict RPC adapter returned an inexact runtime state")
    return NativeOpenObservation(
        handle=runtime,
        index_sha256=bytes.fromhex(runtime.identity.index_sha256),
        full_signature=runtime.identity.canonical_bytes,
        debt=runtime.debt.to_tuple(),
        response_signature=runtime.state_view.response_signature,
    )


def _production_semantic_signature(
    kind: ExactOutcomeKind, target: NativeOpenObservation | None
) -> bytes:
    return _canonical_bytes(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-path-invariant-row-v1",
            "kind": kind.value,
            "target": None if target is None else target.exact_state.to_wire(),
        }
    )


class KernelRPCNativeSession:
    """Concrete one-worker facade over the frozen strict RPC client."""

    def __init__(
        self,
        transport: SynchronousJSONLSubprocessTransport,
        adapter: StrictKernelRPCOracleAdapter,
        tasks: tuple[NativeTask, ...],
        imports: tuple[str, ...],
        factory: "KernelRPCNativeFactory | None" = None,
    ) -> None:
        self._transport = transport
        self._adapter = adapter
        self._tasks = {row.task_id: U05TaskSpec.from_frozen_record(row.payload) for row in tasks}
        self._serial = 0
        self._closed = False
        self._clean_closeout_receipt: str | None = None
        self._production_factory = factory
        self._adapter.load_project(request_id=self._request("load"), imports=imports)
        _register_kernel_session(self, factory)

    def _request(self, kind: str) -> str:
        self._serial += 1
        return f"kp3d4_{self._serial:06d}_{kind}"

    def initialize(self, task: NativeTask) -> NativeOpenObservation:
        task.validate()
        expected = self._tasks.get(task.task_id)
        if expected is None:
            raise NativeClosureError("native session received an unregistered task")
        actual = U05TaskSpec.from_frozen_record(task.payload)
        if actual != expected:
            raise NativeClosureError("native task snapshot changed after worker load")
        runtime = self._adapter.init_state(
            request_id=self._request(f"init_{task.task_id}"), task=actual
        )
        return _runtime_observation(runtime)

    def apply(
        self, source_handle: object, action: NativeAction
    ) -> NativeTransition:
        if type(source_handle) is not RuntimeStateView:
            raise NativeClosureError("production apply requires an exact RuntimeStateView")
        action.validate()
        symbol = ActionSymbol.from_frozen_action_record(action.payload)
        if symbol.action_id != action.action_id:
            raise NativeClosureError("action payload/id binding mismatch")
        try:
            source_handle.bind_action(symbol)
        except StrictContractError:
            signature = _production_semantic_signature(ExactOutcomeKind.SINK, None)
            return NativeTransition(
                kind=ExactOutcomeKind.SINK,
                replay_verified=False,
                replay_digest=_sha(
                    {
                        "schema_version": "lean-rgc-uprime-kp3-d4-syntactic-sink-v1",
                        "source": source_handle.identity.index_sha256,
                        "action_id": action.action_id,
                    }
                ),
                semantic_signature=signature,
                verification_mode="deterministic_syntactic_sink",
                elapsed_ms=0,
            )

        result = self._adapter.apply_symbol(
            request_id=self._request("apply"), source=source_handle, symbol=symbol
        )
        if result.censor is not None or result.event.is_censor:
            kind = None if result.censor is None else result.censor.kind
            if kind in {
                CensorKind.HEARTBEAT_EXHAUSTION,
                CensorKind.WALL_TIMEOUT,
                CensorKind.CAP_MISMATCH,
            }:
                raise NativeResourceError("strict RPC resource censor")
            if kind in {
                CensorKind.PROCESS_CRASH,
                CensorKind.TRANSPORT_FAILURE,
            }:
                raise NativeExecutionError("strict RPC execution transport failed")
            raise NativeDomainError("strict RPC replay/instrument/domain censor")
        if not result.event.replay_verified or not result.event.exact_delta:
            raise NativeClosureError("strict RPC event lost replay/delta evidence")

        target: NativeOpenObservation | None = None
        if result.event.totalized_status is OutcomeKind.OPEN:
            if result.target_state is None:
                raise NativeClosureError("OPEN strict RPC event lacks its retained target")
            kind = ExactOutcomeKind.OPEN
            target = _runtime_observation(result.target_state)
            mode = "replay_verified_success"
        elif result.event.totalized_status is OutcomeKind.CLOSED:
            kind = ExactOutcomeKind.CLOSED
            mode = "replay_verified_success"
        elif result.event.totalized_status is OutcomeKind.SINK:
            kind = ExactOutcomeKind.SINK
            mode = "replay_verified_failure"
        else:
            raise NativeClosureError("strict RPC event is not totalized")

        retained = result.retained_state_id
        if retained is not None and target is None:
            self._adapter.discard_owned(
                request_id=self._request("discard_terminal"), state_id=retained
            )
        response = result.response
        if response is None or not response.replay.verified:
            raise NativeClosureError("concrete strict RPC transition lacks replay evidence")
        replay_digest = _sha(
            {
                "schema_version": "lean-rgc-uprime-kp3-d4-replay-binding-v1",
                "action_id": response.action_id,
                "status": response.status,
                "primary": dict(response.replay.primary_comparable),
                "replay": (
                    None
                    if response.replay.replay_comparable is None
                    else dict(response.replay.replay_comparable)
                ),
            }
        )
        return NativeTransition(
            kind=kind,
            replay_verified=True,
            replay_digest=replay_digest,
            semantic_signature=_production_semantic_signature(kind, target),
            target=target,
            verification_mode=mode,
            elapsed_ms=response.elapsed_ms,
        )

    def close_handle(self, handle: object) -> None:
        if type(handle) is not RuntimeStateView:
            raise NativeClosureError("production close requires an exact RuntimeStateView")
        self._adapter.discard_owned(
            request_id=self._request("discard"), state_id=handle.live_rpc_state_id
        )

    def close(self) -> None:
        if self._closed:
            raise NativeClosureError("native session was closed more than once")
        try:
            status = self._adapter.status(request_id=self._request("status"))
            if (
                status.n_states != 0
                or self._adapter.owned_state_ids
                or status.n_primary_executions != status.n_replay_executions
            ):
                raise NativeClosureError("native worker ownership/replay counters disagree")
            self._adapter.shutdown(request_id=self._request("shutdown"))
            self._clean_closeout_receipt = _sha(
                {
                    "schema_version": "lean-rgc-uprime-kp3-d4-clean-rpc-closeout-v1",
                    "n_states": status.n_states,
                    "n_requests": status.n_requests,
                    "n_failures": status.n_failures,
                    "n_primary_executions": status.n_primary_executions,
                    "n_replay_executions": status.n_replay_executions,
                    "owned_state_ids": sorted(self._adapter.owned_state_ids),
                    "request_serial": self._serial,
                }
            )
        finally:
            self._closed = True
            self._transport.close()


@dataclass(frozen=True)
class KernelRPCNativeFactory:
    repo_root: Path
    lean_binary: Path
    worker_source: Path
    environment_content_digest: str
    worker_environment: Mapping[str, str]

    def __post_init__(self) -> None:
        for value, where in (
            (self.repo_root, "repo_root"),
            (self.lean_binary, "lean_binary"),
            (self.worker_source, "worker_source"),
        ):
            if not isinstance(value, Path) or not value.is_absolute():
                raise NativeClosureError(f"{where} must be an absolute Path")
        _digest(self.environment_content_digest, "environment_content_digest")
        if type(self.worker_environment) is not dict:
            raise NativeClosureError("worker environment must be an exact object")
        for key, value in self.worker_environment.items():
            _text(key, "worker environment key")
            if type(value) is not str:
                raise NativeClosureError("worker environment values must be strings")
        _register_kernel_factory(self)

    def open(self, tasks: tuple[NativeTask, ...]) -> KernelRPCNativeSession:
        specs = tuple(U05TaskSpec.from_frozen_record(row.payload) for row in tasks)
        imports = specs[0].imports
        if any(spec.imports != imports for spec in specs):
            raise NativeClosureError("registered tasks do not share one import closure")
        transport = SynchronousJSONLSubprocessTransport(
            [
                str(self.lean_binary),
                "--run",
                str(self.worker_source),
                "--imports",
                *imports,
            ],
            cwd=self.repo_root,
            env=dict(self.worker_environment),
        )
        adapter = StrictKernelRPCOracleAdapter(
            transport,
            environment_content_digest=self.environment_content_digest,
            action_timeout_seconds=MAX_ACTION_SECONDS,
            control_timeout_seconds=120.0,
        )
        try:
            return KernelRPCNativeSession(
                transport, adapter, tasks, imports, factory=self
            )
        except BaseException:
            transport.close()
            raise


def _register_kernel_factory(factory: KernelRPCNativeFactory) -> None:
    if type(factory) is not KernelRPCNativeFactory:
        raise NativeClosureError("production factory subclasses are forbidden")
    identity = id(factory)
    snapshot = (
        str(factory.repo_root),
        str(factory.lean_binary),
        str(factory.worker_source),
        factory.environment_content_digest,
        _sha(dict(factory.worker_environment)),
    )
    _KERNEL_FACTORY_PROVENANCE[identity] = (weakref.ref(factory), *snapshot)


def _kernel_factory_snapshot(factory: KernelRPCNativeFactory) -> tuple[str, ...] | None:
    retained = _KERNEL_FACTORY_PROVENANCE.get(id(factory))
    current = (
        str(factory.repo_root),
        str(factory.lean_binary),
        str(factory.worker_source),
        factory.environment_content_digest,
        _sha(dict(factory.worker_environment)),
    )
    if retained is None or retained[0]() is not factory or retained[1:] != current:
        return None
    return current


def _register_kernel_session(
    session: KernelRPCNativeSession,
    factory: KernelRPCNativeFactory | None,
) -> None:
    if factory is None:
        return
    factory_snapshot = _kernel_factory_snapshot(factory)
    if (
        type(session) is not KernelRPCNativeSession
        or type(factory) is not KernelRPCNativeFactory
        or factory_snapshot is None
    ):
        raise NativeClosureError("production session lacks factory construction authority")
    _KERNEL_SESSION_PROVENANCE[id(session)] = (
        weakref.ref(session),
        factory,
        factory_snapshot,
        session._serial,
    )


def _kernel_session_snapshot(
    session: KernelRPCNativeSession, factory: KernelRPCNativeFactory
) -> tuple[Any, ...] | None:
    retained = _KERNEL_SESSION_PROVENANCE.get(id(session))
    if (
        retained is None
        or retained[0]() is not session
        or retained[1] is not factory
        or retained[2] != _kernel_factory_snapshot(factory)
        or session._production_factory is not factory
    ):
        return None
    return retained


@dataclass(frozen=True)
class DuplicateAuditReport:
    retained_occurrences: int
    rows_checked: int
    saturated: bool
    digest: str

    def __post_init__(self) -> None:
        for value, where in (
            (self.retained_occurrences, "retained duplicate count"),
            (self.rows_checked, "duplicate row count"),
        ):
            _integer(value, where)
        if self.retained_occurrences > MAX_DUPLICATE_OCCURRENCES:
            raise NativeClosureError("duplicate audit exceeded its cap")
        if type(self.saturated) is not bool:
            raise NativeClosureError("duplicate saturation must be an exact bool")
        _digest(self.digest, "duplicate audit digest")


@dataclass(frozen=True)
class ConditionalNativeHistoryResult:
    chart: CanonicalHistoryChart
    raw_normalized_equality: RawNormalizedEqualityReport
    flow_verification: FlowVerificationReport
    hankels: tuple[ExactRawCoordinateHankel, ...]
    certificates: tuple[ExactRankCertificate, ...]
    rank_verifications: tuple[ExactRankVerificationReport, ...]
    duplicate_audit: DuplicateAuditReport
    native_semantics_digest: str
    elapsed_ms: int
    exactness_scope: str = CONDITIONAL_KSTATE_MARKOV

    def __post_init__(self) -> None:
        if type(self.chart) is not CanonicalHistoryChart:
            raise NativeClosureError("result chart has an inexact type")
        self.chart.validate()
        if self.chart.max_depth != 4:
            raise NativeClosureError("native result chart must be exactly depth four")
        if (
            self.chart.exactness_scope != CONDITIONAL_KSTATE_MARKOV
            or self.chart.domain.exactness_floor != CONDITIONAL_KSTATE_MARKOV
        ):
            raise NativeClosureError("native result attempted unconditional laundering")
        _digest(self.native_semantics_digest, "native semantics digest")
        if self.native_semantics_digest != self.chart.domain.semantics_digest:
            raise NativeClosureError("native/domain semantics digest mismatch")
        if type(self.raw_normalized_equality) is not RawNormalizedEqualityReport:
            raise NativeClosureError("result lacks exact depth-three equality evidence")
        self.raw_normalized_equality.validate()
        if type(self.flow_verification) is not FlowVerificationReport:
            raise NativeClosureError("result lacks exact flow evidence")
        self.flow_verification.validate()
        if (
            self.raw_normalized_equality.source_digest != self.chart.digest
            or self.flow_verification.source_digest != self.chart.digest
        ):
            raise NativeClosureError("history evidence source binding mismatch")
        expected_depth3 = len(self.chart.domain.task_ids) * sum(
            len(self.chart.domain.action_ids) ** depth for depth in range(4)
        )
        if (
            self.raw_normalized_equality.max_depth != 3
            or self.raw_normalized_equality.occurrence_count != expected_depth3
            or not self.raw_normalized_equality.equal
        ):
            raise NativeClosureError("depth-three equality coverage mismatch")
        expected_layer_totals = tuple(
            len(self.chart.domain.task_ids)
            * len(self.chart.domain.action_ids) ** depth
            for depth in range(5)
        )
        if (
            self.flow_verification.max_depth != 4
            or self.flow_verification.layer_totals != expected_layer_totals
            or self.flow_verification.streamed_occurrences_checked
            != sum(expected_layer_totals)
            or not self.flow_verification.exact_raw_histogram_coverage
        ):
            raise NativeClosureError("depth-four flow coverage mismatch")
        if type(self.hankels) is not tuple or len(self.hankels) != 4:
            raise NativeClosureError("result must retain exactly H1 through H4")
        if type(self.certificates) is not tuple or len(self.certificates) != 4:
            raise NativeClosureError("result must retain exactly four rank certificates")
        if type(self.rank_verifications) is not tuple or len(self.rank_verifications) != 4:
            raise NativeClosureError("result must retain exactly four rank verifications")
        for index, item in enumerate(self.hankels, start=1):
            if type(item) is not ExactRawCoordinateHankel or item.cutoff != index:
                raise NativeClosureError("Hankel family is not exact H1 through H4")
            item.validate()
            if (
                item.source_digest != self.chart.digest
                or item.exactness_scope != CONDITIONAL_KSTATE_MARKOV
            ):
                raise NativeClosureError("Hankel family source/scope mismatch")
        for cutoff, (hankel, item) in enumerate(
            zip(self.hankels, self.certificates, strict=True), start=1
        ):
            if type(item) is not ExactRankCertificate:
                raise NativeClosureError("rank certificate type mismatch")
            item.validate()
            if (
                item.cutoff != cutoff
                or item.row_coordinate_digest != hankel.row_coordinate_digest
                or item.column_coordinate_digest != hankel.column_coordinate_digest
                or item.response_coordinate_digest != hankel.response_coordinate_digest
                or item.matrix_digest != hankel.matrix_digest
                or item.source_digest != self.chart.digest
                or item.exactness_scope != CONDITIONAL_KSTATE_MARKOV
            ):
                raise NativeClosureError("rank certificate/Hankel splice mismatch")
        for hankel, certificate, item in zip(
            self.hankels,
            self.certificates,
            self.rank_verifications,
            strict=True,
        ):
            if type(item) is not ExactRankVerificationReport or not item.verified:
                raise NativeClosureError("rank verification type/status mismatch")
            item.validate()
            independently_reverified = verify_exact_rank_certificate(hankel, certificate)
            if (
                item != independently_reverified
                or item.matrix_digest != hankel.matrix_digest
                or item.source_digest != self.chart.digest
                or item.exactness_scope != CONDITIONAL_KSTATE_MARKOV
            ):
                raise NativeClosureError("rank verification/certificate splice mismatch")
        if type(self.duplicate_audit) is not DuplicateAuditReport:
            raise NativeClosureError("duplicate audit type mismatch")
        self.duplicate_audit.__post_init__()
        expected_duplicate_rows = (
            self.duplicate_audit.retained_occurrences
            * len(self.chart.domain.action_ids)
        )
        if (
            self.duplicate_audit.rows_checked != expected_duplicate_rows
            or self.chart.duplicate_row_checks != expected_duplicate_rows
        ):
            raise NativeClosureError("duplicate audit/chart row binding mismatch")
        _integer(self.elapsed_ms, "elapsed_ms")
        if self.elapsed_ms > MAX_NATIVE_SECONDS * 1_000:
            raise NativeClosureError("native result exceeded the whole-run wall")
        if self.exactness_scope != CONDITIONAL_KSTATE_MARKOV:
            raise NativeClosureError("native result scope must remain conditional")

    def to_wire(self) -> dict[str, Any]:
        self.__post_init__()
        hankel_rows = []
        for item in self.hankels:
            equality = item.equality_report
            hankel_rows.append(
                {
                    "cutoff": item.cutoff,
                    "source_digest": item.source_digest,
                    "exactness_scope": item.exactness_scope,
                    "row_keys": [key.to_wire() for key in item.row_keys],
                    "suffix_words": [list(word) for word in item.suffix_words],
                    "matrix": [list(row) for row in item.matrix],
                    "dimensions": {
                        "cutoff": item.dimensions.cutoff,
                        "prefix_depth": item.dimensions.prefix_depth,
                        "suffix_depth": item.dimensions.suffix_depth,
                        "n_rows": item.dimensions.n_rows,
                        "n_suffixes": item.dimensions.n_suffixes,
                        "n_columns": item.dimensions.n_columns,
                        "n_word_coordinates": item.dimensions.n_word_coordinates,
                        "n_cells": item.dimensions.n_cells,
                        "raw_words_through_cutoff": item.dimensions.raw_words_through_cutoff,
                    },
                    "row_coordinate_digest": item.row_coordinate_digest,
                    "column_coordinate_digest": item.column_coordinate_digest,
                    "response_coordinate_digest": item.response_coordinate_digest,
                    "matrix_digest": item.matrix_digest,
                    "equality_report": {
                        "cutoff": equality.cutoff,
                        "word_coordinates_checked": equality.word_coordinates_checked,
                        "channel_cells_checked": equality.channel_cells_checked,
                        "response_coordinate_digest": equality.response_coordinate_digest,
                        "matrix_digest": equality.matrix_digest,
                        "exact_response_records_equal": equality.exact_response_records_equal,
                    },
                    "conditioning": item.conditioning,
                    "conditioning_censor": item.conditioning_censor,
                }
            )
        return {
            "schema_version": NATIVE_RESULT_SCHEMA,
            "exactness_scope": self.exactness_scope,
            "native_semantics_digest": self.native_semantics_digest,
            "chart_digest": self.chart.digest,
            "domain_digest": self.chart.domain.digest,
            "open_states": len(self.chart.domain.open_states),
            "transition_rows": len(self.chart.domain.transition_rows),
            "elapsed_ms": self.elapsed_ms,
            "domain": self.chart.domain.to_wire(),
            "history": {
                "chart_digest": self.chart.digest,
                "max_depth": self.chart.max_depth,
                "exactness_scope": self.chart.exactness_scope,
                "markov_contract": self.chart.markov_contract.to_wire(),
                "report_preflight": self.chart.report_preflight.to_wire(),
                "duplicate_row_checks": self.chart.duplicate_row_checks,
                "layers": [
                    {
                        "depth": layer.depth,
                        "raw_multiplicity": layer.raw_multiplicity,
                        "classes": [
                            {
                                "key": row.key.to_wire(),
                                "representative_task_id": row.representative_task_id,
                                "representative_word": list(row.representative_word),
                                "raw_multiplicity": row.raw_multiplicity,
                            }
                            for row in layer.classes
                        ],
                        "incoming_edges": [
                            {
                                "source_key": edge.source_key.to_wire(),
                                "action_id": edge.action_id,
                                "target_key": edge.target_key.to_wire(),
                                "witness_digest": edge.witness_digest,
                                "flow": edge.flow,
                            }
                            for edge in layer.incoming_edges
                        ],
                    }
                    for layer in self.chart.layers
                ],
            },
            "raw_normalized_equality": {
                "max_depth": self.raw_normalized_equality.max_depth,
                "occurrence_count": self.raw_normalized_equality.occurrence_count,
                "complete_response_digest": self.raw_normalized_equality.complete_response_digest,
                "source_digest": self.raw_normalized_equality.source_digest,
                "equal": self.raw_normalized_equality.equal,
            },
            "flow_verification": {
                "max_depth": self.flow_verification.max_depth,
                "layer_totals": list(self.flow_verification.layer_totals),
                "streamed_occurrences_checked": self.flow_verification.streamed_occurrences_checked,
                "exact_raw_histogram_coverage": self.flow_verification.exact_raw_histogram_coverage,
                "streamed_histogram_digest": self.flow_verification.streamed_histogram_digest,
                "source_digest": self.flow_verification.source_digest,
            },
            "duplicate_audit": {
                "retained_occurrences": self.duplicate_audit.retained_occurrences,
                "rows_checked": self.duplicate_audit.rows_checked,
                "saturated": self.duplicate_audit.saturated,
                "digest": self.duplicate_audit.digest,
            },
            "hankels": hankel_rows,
            "certificates": [item.to_wire() for item in self.certificates],
            "rank_verifications": [
                {
                    "verified": item.verified,
                    "basis_independent": item.basis_independent,
                    "complete_span_verified": item.complete_span_verified,
                    "rows_checked": item.rows_checked,
                    "matrix_digest": item.matrix_digest,
                    "source_digest": item.source_digest,
                    "exactness_scope": item.exactness_scope,
                    "certificate_digest": item.certificate_digest,
                }
                for item in self.rank_verifications
            ],
        }

    def to_canonical_json_bytes(self) -> bytes:
        payload = _canonical_bytes(self.to_wire())
        if len(payload) >= MAX_RESULT_BYTES:
            raise NativeResourceError("native result exceeds the 64 MiB cap")
        return payload


def _register_production_result(
    result: ConditionalNativeHistoryResult,
    factory: StrictNativeFactory,
    session: StrictNativeSession,
    input_receipt: str | None,
) -> None:
    if (
        type(result) is not ConditionalNativeHistoryResult
        or type(factory) is not KernelRPCNativeFactory
        or type(session) is not KernelRPCNativeSession
    ):
        return
    if (
        input_receipt is None
        or _kernel_factory_snapshot(factory) is None
        or _kernel_session_snapshot(session, factory) is None
    ):
        raise NativeClosureError("production result lacks construction/input authority")
    _digest(input_receipt, "registered input receipt")
    closeout = session._clean_closeout_receipt
    if type(closeout) is not str:
        raise NativeClosureError("production result lacks clean RPC closeout")
    _digest(closeout, "production closeout receipt")
    identity = id(result)
    expected_frame = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-native-frame-v1",
            "environment_digest": factory.environment_content_digest,
            "task_input": REGISTERED_TASK_CANONICAL_SHA256,
            "action_input": REGISTERED_ACTION_CANONICAL_SHA256,
        }
    )
    if (
        result.chart.markov_contract is None
        or result.chart.markov_contract.frame_digest != expected_frame
    ):
        raise NativeClosureError("production result frame is not registered-input derived")
    result_wire_digest = _sha(result.to_wire())
    component_identities = (
        id(result.chart),
        id(result.raw_normalized_equality),
        id(result.flow_verification),
        id(result.duplicate_audit),
        *(id(row) for row in result.hankels),
        *(id(row) for row in result.certificates),
        *(id(row) for row in result.rank_verifications),
    )

    def remove(reference: weakref.ReferenceType[Any], *, key: int = identity) -> None:
        retained = _PRODUCTION_RESULT_PROVENANCE.get(key)
        if retained is not None and retained[0] is reference:
            _PRODUCTION_RESULT_PROVENANCE.pop(key, None)

    reference = weakref.ref(result, remove)
    receipt = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-production-result-authority-v1",
            "native_semantics_digest": result.native_semantics_digest,
            "chart_digest": result.chart.digest,
            "environment_content_digest": factory.environment_content_digest,
            "frame_digest": expected_frame,
            "registered_input_receipt": input_receipt,
            "result_wire_digest": result_wire_digest,
            "component_identities": list(component_identities),
            "lean_binary": str(factory.lean_binary),
            "worker_source": str(factory.worker_source),
            "clean_closeout_receipt": closeout,
        }
    )
    _PRODUCTION_RESULT_PROVENANCE[identity] = (
        reference,
        result.native_semantics_digest,
        result.chart.digest,
        factory.environment_content_digest,
        expected_frame,
        input_receipt,
        result_wire_digest,
        component_identities,
        factory,
        session,
        closeout,
        receipt,
    )


def _production_result_receipt(
    result: ConditionalNativeHistoryResult,
    identity: Mapping[str, Any],
) -> str | None:
    retained = _PRODUCTION_RESULT_PROVENANCE.get(id(result))
    if (
        retained is None
        or retained[0]() is not result
        or result.native_semantics_digest != retained[1]
        or result.chart.digest != retained[2]
        or identity.get("environment_digest") != retained[3]
        or result.chart.markov_contract is None
        or result.chart.markov_contract.frame_digest != retained[4]
        or _sha(result.to_wire()) != retained[6]
        or (
            id(result.chart),
            id(result.raw_normalized_equality),
            id(result.flow_verification),
            id(result.duplicate_audit),
            *(id(row) for row in result.hankels),
            *(id(row) for row in result.certificates),
            *(id(row) for row in result.rank_verifications),
        )
        != retained[7]
        or type(retained[8]) is not KernelRPCNativeFactory
        or type(retained[9]) is not KernelRPCNativeSession
        or _kernel_factory_snapshot(retained[8]) is None
        or _kernel_session_snapshot(retained[9], retained[8]) is None
        or retained[9]._clean_closeout_receipt != retained[10]
    ):
        return None
    expected = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-production-result-authority-v1",
            "native_semantics_digest": retained[1],
            "chart_digest": retained[2],
            "environment_content_digest": retained[3],
            "frame_digest": retained[4],
            "registered_input_receipt": retained[5],
            "result_wire_digest": retained[6],
            "component_identities": list(retained[7]),
            "lean_binary": str(retained[8].lean_binary),
            "worker_source": str(retained[8].worker_source),
            "clean_closeout_receipt": retained[10],
        }
    )
    return retained[11] if retained[11] == expected else None


SemanticRow = tuple[
    str,
    bytes | None,
    bytes | None,
    tuple[int, ...] | None,
    bytes | None,
    bytes,
]


def _observation_payload(value: NativeOpenObservation) -> tuple[bytes, bytes, tuple[int, ...], bytes]:
    value.__post_init__()
    return (
        value.index_sha256,
        value.full_signature,
        value.debt,
        value.response_signature,
    )


def _semantic_row(value: NativeTransition) -> SemanticRow:
    value.__post_init__()
    if value.kind == "censor":
        reason = (value.censor_reason or "").lower()
        if any(token in reason for token in ("heartbeat", "wall_timeout", "timeout", "cap")):
            raise NativeResourceError("RPC resource censor is inadmissible")
        if any(token in reason for token in ("process_crash", "transport")):
            raise NativeExecutionError("RPC execution censor is inadmissible")
        raise NativeDomainError("RPC domain censor is inadmissible")
    if (
        not value.replay_verified
        and value.verification_mode != "deterministic_syntactic_sink"
    ):
        raise NativeDomainError("unverified replay is inadmissible")
    if value.kind is ExactOutcomeKind.OPEN:
        assert value.target is not None
        target = value.target
        return (
            value.kind.value,
            target.index_sha256,
            target.full_signature,
            target.debt,
            target.response_signature,
            value.semantic_signature,
        )
    assert type(value.kind) is ExactOutcomeKind
    return (
        value.kind.value,
        None,
        None,
        None,
        None,
        value.semantic_signature,
    )


def _close(
    session: StrictNativeSession, handle: object, owned: dict[int, object]
) -> None:
    token = id(handle)
    if token not in owned or owned[token] is not handle:
        raise NativeClosureError("native handle ownership/close mismatch")
    session.close_handle(handle)
    del owned[token]


def _enforce_state_cap(count: int) -> None:
    _integer(count, "OPEN state count")
    if count > MAX_OPEN_STATES:
        raise NativeResourceError("OPEN fixed point exceeds the 1024-state cap")


def _enforce_row_cap(count: int) -> None:
    _integer(count, "transition row count")
    if count > MAX_TRANSITION_ROWS:
        raise NativeResourceError("transition closure exceeds the 12288-row cap")


def _preflight_registered_inputs(
    tasks: Sequence[NativeTask], actions: Sequence[NativeAction]
) -> tuple[tuple[NativeTask, ...], tuple[NativeAction, ...]]:
    if type(tasks) not in {tuple, list} or type(actions) not in {tuple, list}:
        raise NativeClosureError("tasks/actions must be exact bounded sequences")
    if not tasks or not actions:
        raise NativeClosureError("tasks/actions must be nonempty")
    if len(actions) > MAX_ACTIONS:
        raise NativeClosureError("action alphabet exceeds the frozen cap")
    task_rows = tuple(tasks)
    action_rows = tuple(actions)
    if any(type(item) is not NativeTask for item in task_rows):
        raise NativeClosureError("task sequence has an inexact member")
    if any(type(item) is not NativeAction for item in action_rows):
        raise NativeClosureError("action sequence has an inexact member")
    for item in task_rows:
        item.validate()
    for item in action_rows:
        item.validate()
    task_ids = tuple(item.task_id for item in task_rows)
    action_ids = tuple(item.action_id for item in action_rows)
    if len(task_ids) != len(set(task_ids)) or len(action_ids) != len(set(action_ids)):
        raise NativeClosureError("registered IDs contain duplicates")
    if len(task_rows) > 30_000:
        raise NativeClosureError("task seed count exceeds the depth-four occurrence cap")
    # Independent row preflight.  It is not folded into the state-cap check.
    if MAX_OPEN_STATES * len(action_rows) > MAX_TRANSITION_ROWS:
        raise NativeClosureError("state/action row upper exceeds the frozen cap")
    return (
        tuple(sorted(task_rows, key=lambda item: item.task_id)),
        tuple(sorted(action_rows, key=lambda item: item.action_id)),
    )


def build_conditional_native_history(
    *,
    tasks: Sequence[NativeTask],
    actions: Sequence[NativeAction],
    factory: StrictNativeFactory,
    source_authority: str,
    frame_digest: str,
    clock: Callable[[], float] = time.monotonic,
) -> ConditionalNativeHistoryResult:
    """Expand all unique native OPEN representatives to a bounded fixed point."""

    task_rows, action_rows = _preflight_registered_inputs(tasks, actions)
    input_receipt = _registered_input_receipt(task_rows, action_rows)
    if type(factory) is KernelRPCNativeFactory and (
        input_receipt is None or _kernel_factory_snapshot(factory) is None
    ):
        raise NativeDomainError(
            "production factory requires construction and registered input authority"
        )
    _text(source_authority, "source_authority")
    _digest(frame_digest, "frame_digest")
    if not callable(clock):
        raise NativeClosureError("clock must be callable")
    started = clock()
    if type(started) not in {int, float}:
        raise NativeClosureError("clock returned a nonnumeric value")
    deadline = started + MAX_NATIVE_SECONDS

    try:
        session = factory.open(task_rows)
    except KernelRPCTransportTimeout as exc:
        raise NativeResourceError("strict RPC transport exceeded its wall") from exc
    except KernelRPCProcessExited as exc:
        raise NativeExecutionError("strict RPC worker exited") from exc
    except KernelRPCTransportError as exc:
        raise NativeExecutionError("strict RPC transport failed") from exc
    except StrictKernelRPCError as exc:
        raise NativeDomainError("strict RPC response was inadmissible") from exc
    if session is None:
        raise NativeClosureError("native factory returned no session")
    completed_result: ConditionalNativeHistoryResult | None = None
    owned: dict[int, object] = {}
    representatives: dict[bytes, NativeOpenObservation] = {}
    pending: list[bytes] = []
    seeds: list[TaskSeed] = []
    duplicate_queue: list[tuple[bytes, NativeOpenObservation]] = []
    duplicate_seen = 0
    saturated = False
    sealed_rows: dict[tuple[bytes, str], SealedTransitionRow] = {}
    semantic_rows: dict[tuple[bytes, str], SemanticRow] = {}

    def check_time() -> None:
        now = clock()
        if type(now) not in {int, float} or now < started or now > deadline:
            raise NativeResourceError("native closure exceeded its frozen 3600-second wall")

    def acquire(value: NativeOpenObservation) -> None:
        if id(value.handle) in owned:
            raise NativeClosureError("native facade aliased an already-owned handle")
        owned[id(value.handle)] = value.handle

    def admit_occurrence(
        value: NativeOpenObservation, *, acquired: bool
    ) -> bytes:
        nonlocal duplicate_seen, saturated
        if type(acquired) is not bool or not acquired:
            raise NativeClosureError("OPEN occurrence was not acquired exactly once")
        if type(value) is not NativeOpenObservation:
            raise NativeClosureError("native facade returned an inexact OPEN observation")
        value.__post_init__()
        if id(value.handle) not in owned or owned[id(value.handle)] is not value.handle:
            raise NativeClosureError("OPEN occurrence lacks exact acquired ownership")
        key = value.index_sha256
        existing = representatives.get(key)
        if existing is None:
            _enforce_state_cap(len(representatives) + 1)
            representatives[key] = value
            pending.append(key)
            return key
        if _observation_payload(existing) != _observation_payload(value):
            raise NativeNormalizationError(
                "canonical-index collision changed full semantic state"
            )
        duplicate_seen += 1
        if len(duplicate_queue) < MAX_DUPLICATE_OCCURRENCES:
            duplicate_queue.append((key, value))
        else:
            saturated = True
            _close(session, value.handle, owned)
        return key

    try:
        for task in task_rows:
            check_time()
            seed = session.initialize(task)
            if type(seed) is not NativeOpenObservation:
                raise NativeClosureError("native initializer returned an inexact seed")
            acquire(seed)
            key = admit_occurrence(seed, acquired=True)
            seeds.append(TaskSeed(task.task_id, key))

        cursor = 0
        while cursor < len(pending):
            check_time()
            source_key = pending[cursor]
            cursor += 1
            source = representatives[source_key]
            for action in action_rows:
                check_time()
                _enforce_row_cap(len(sealed_rows) + 1)
                transition = session.apply(source.handle, action)
                if type(transition) is not NativeTransition:
                    raise NativeClosureError("native facade returned an inexact transition")
                if type(transition.target) is NativeOpenObservation:
                    acquire(transition.target)
                semantic = _semantic_row(transition)
                target_key: bytes | None = None
                assert type(transition.kind) is ExactOutcomeKind
                if transition.kind is ExactOutcomeKind.OPEN:
                    assert transition.target is not None
                    target_key = admit_occurrence(
                        transition.target, acquired=True
                    )
                row = SealedTransitionRow(
                    source_key,
                    action.action_id,
                    transition.kind,
                    target_key,
                    transition.replay_digest,
                )
                pair = (source_key, action.action_id)
                if pair in sealed_rows:
                    raise NativeClosureError("closure attempted a duplicate representative row")
                sealed_rows[pair] = row
                semantic_rows[pair] = semantic

        if len(sealed_rows) != len(representatives) * len(action_rows):
            raise NativeDomainError("OPEN fixed point retained an unresolved frontier")

        audit_hasher = hashlib.sha256()
        audit_rows = 0
        index = 0
        while index < len(duplicate_queue):
            check_time()
            source_key, duplicate = duplicate_queue[index]
            index += 1
            for action in action_rows:
                check_time()
                probe = session.apply(duplicate.handle, action)
                if type(probe) is not NativeTransition:
                    raise NativeClosureError("duplicate audit received an inexact transition")
                if type(probe.target) is NativeOpenObservation:
                    acquire(probe.target)
                observed = _semantic_row(probe)
                expected = semantic_rows[(source_key, action.action_id)]
                if observed != expected:
                    raise NativeNormalizationError(
                        "duplicate handle changed a full semantic row"
                    )
                if probe.kind is ExactOutcomeKind.OPEN:
                    assert probe.target is not None
                    target = probe.target
                    expected_target = representatives.get(target.index_sha256)
                    if expected_target is None or _observation_payload(expected_target) != _observation_payload(target):
                        raise NativeDomainError(
                            "duplicate audit escaped the sealed OPEN domain"
                        )
                    # This is exactly a one-step falsification audit.  The
                    # descendant is checked in the full semantic row and then
                    # released; recursively auditing it would silently turn a
                    # bounded check into a congruence claim.
                    _close(session, target.handle, owned)
                audit_hasher.update(
                    _canonical_bytes(
                        [
                            source_key.hex().upper(),
                            action.action_id,
                            observed[0],
                            None if observed[1] is None else observed[1].hex().upper(),
                            None if observed[2] is None else observed[2].hex().upper(),
                            None if observed[3] is None else list(observed[3]),
                            None if observed[4] is None else observed[4].hex().upper(),
                            observed[5].hex().upper(),
                        ]
                    )
                )
                audit_hasher.update(b"\n")
                audit_rows += 1
            _close(session, duplicate.handle, owned)

        semantics_digest = _sha(
            {
                "schema_version": NATIVE_CLOSURE_SCHEMA,
                "frame_digest": frame_digest,
                "tasks": [item.task_id for item in task_rows],
                "actions": [item.action_id for item in action_rows],
                "states": [
                    representatives[key].exact_state.to_wire()
                    for key in sorted(representatives)
                ],
                "rows": [
                    sealed_rows[key].to_wire()
                    for key in sorted(sealed_rows)
                ],
            }
        )
        domain = build_finite_total_action_domain(
            source_authority=source_authority,
            expected_source_authority=source_authority,
            semantics_digest=semantics_digest,
            exactness_floor=CONDITIONAL_KSTATE_MARKOV,
            task_seeds=tuple(seeds),
            action_ids=tuple(item.action_id for item in action_rows),
            open_states=tuple(
                representatives[key].exact_state for key in sorted(representatives)
            ),
            transition_rows=tuple(sealed_rows[key] for key in sorted(sealed_rows)),
        )
        markov = CanonicalKStateMarkovContract(
            frame_digest=frame_digest,
            transition_semantics_digest=semantics_digest,
            action_grammar_digest=domain.action_grammar_digest,
        )
        chart = CanonicalHistoryChart.build(
            domain,
            max_depth=4,
            markov_contract=markov,
            duplicate_row_checks=audit_rows,
        )
        verify_generation_time_equals_batch(chart)
        raw_normalized_equality = verify_raw_normalized_equality(chart, max_depth=3)
        flow_verification = verify_flow_conservation(chart)
        try:
            hankels = tuple(
                build_exact_raw_coordinate_hankel(chart, cutoff=cutoff)
                for cutoff in range(1, 5)
            )
            certificates = certify_hankel_family(hankels)
            rank_verifications = tuple(
                verify_exact_rank_certificate(hankel, certificate)
                for hankel, certificate in zip(hankels, certificates, strict=True)
            )
        except StrictContractError as exc:
            message = str(exc)
            if message.startswith("D4_RESOURCE_BLOCKED:"):
                raise NativeResourceError(
                    "bounded exact Hankel/rank construction was resource-blocked"
                ) from exc
            if message.startswith("D4_NORMALIZATION_UNSOUND:"):
                raise NativeNormalizationError(
                    "exact raw-coordinate normalization was unsound"
                ) from exc
            raise NativeDomainError(
                "bounded exact Hankel/rank contract was not admissible"
            ) from exc
        ended = clock()
        if type(ended) not in {int, float} or ended < started or ended > deadline:
            raise NativeResourceError("native closure exceeded its frozen 3600-second wall")
        result = ConditionalNativeHistoryResult(
            chart=chart,
            raw_normalized_equality=raw_normalized_equality,
            flow_verification=flow_verification,
            hankels=hankels,
            certificates=certificates,
            rank_verifications=rank_verifications,
            duplicate_audit=DuplicateAuditReport(
                retained_occurrences=len(duplicate_queue),
                rows_checked=audit_rows,
                saturated=saturated or duplicate_seen > len(duplicate_queue),
                digest=audit_hasher.hexdigest().upper(),
            ),
            native_semantics_digest=semantics_digest,
            elapsed_ms=int((ended - started) * 1000),
        )
        result.to_canonical_json_bytes()
        completed_result = result
        return result
    except HistoryContractError as exc:
        raise NativeNormalizationError(
            "conditional chart/history verification failed closed"
        ) from exc
    except KernelRPCTransportTimeout as exc:
        raise NativeResourceError("strict RPC transport exceeded its wall") from exc
    except KernelRPCProcessExited as exc:
        raise NativeExecutionError("strict RPC worker exited") from exc
    except KernelRPCTransportError as exc:
        raise NativeExecutionError("strict RPC transport failed") from exc
    except StrictKernelRPCError as exc:
        raise NativeDomainError("strict RPC response was inadmissible") from exc
    except StrictContractError as exc:
        raise NativeDomainError("strict native/domain contract failed") from exc
    except ValueError as exc:
        raise NativeExecutionError("conditional native construction failed") from exc
    finally:
        had_error = sys.exc_info()[0] is not None
        close_error: BaseException | None = None
        for handle in tuple(owned.values()):
            if id(handle) in owned:
                try:
                    _close(session, handle, owned)
                except BaseException as exc:  # cleanup must continue for all handles
                    close_error = close_error or exc
        # Any target created immediately before a failing validation is still
        # tracked by acquire; facade errors here are surfaced after session close.
        try:
            session.close()
        except BaseException as exc:
            close_error = close_error or exc
        if (
            close_error is None
            and not had_error
            and completed_result is not None
        ):
            _register_production_result(
                completed_result, factory, session, input_receipt
            )
        if owned and close_error is None:
            close_error = NativeClosureError("native handle leak detected")
        if close_error is not None and not had_error:
            raise NativeClosureError("native session cleanup failed") from close_error


def parse_registered_input_bytes(
    task_payload: bytes, action_payload: bytes
) -> tuple[tuple[NativeTask, ...], tuple[NativeAction, ...]]:
    """Bind exactly the two registered 5-task/12-action input byte strings."""

    raw_bindings = (
        (task_payload, REGISTERED_TASK_RAW_SHA256, "task input"),
        (action_payload, REGISTERED_ACTION_RAW_SHA256, "action input"),
    )
    for payload, expected, where in raw_bindings:
        if type(payload) is not bytes or hashlib.sha256(payload).hexdigest().upper() != expected:
            raise NativeClosureError(f"{where} raw-byte authority mismatch")
    tasks, actions, task_obj, action_obj = _parse_frozen_input_bytes(
        task_payload, action_payload
    )
    if _sha(task_obj) != REGISTERED_TASK_CANONICAL_SHA256:
        raise NativeClosureError("task input canonical authority mismatch")
    if _sha(action_obj) != REGISTERED_ACTION_CANONICAL_SHA256:
        raise NativeClosureError("action input canonical authority mismatch")
    if _sha(task_obj["tasks"]) != REGISTERED_TASK_ROWS_SHA256:
        raise NativeClosureError("task row authority mismatch")
    if _sha(action_obj["actions"]) != REGISTERED_ACTION_ROWS_SHA256:
        raise NativeClosureError("action row authority mismatch")
    if len(tasks) != 5 or len(actions) != 12:
        raise NativeClosureError("registered inventory must contain exactly 5 tasks/12 actions")
    _mint_registered_input_receipt(tasks, actions)
    return tasks, actions


def _parse_frozen_input_bytes(
    task_payload: bytes, action_payload: bytes
) -> tuple[
    tuple[NativeTask, ...],
    tuple[NativeAction, ...],
    dict[str, Any],
    dict[str, Any],
]:
    """Strict row parser; official authority is added by the public wrapper."""

    def load(payload: bytes, where: str) -> Any:
        if type(payload) is not bytes or not payload or len(payload) > MAX_INPUT_BYTES:
            raise NativeClosureError(f"{where} is empty or exceeds the input cap")
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise NativeClosureError(f"{where} is not strict UTF-8") from exc
        try:
            return json.loads(
                text,
                parse_float=lambda _x: (_ for _ in ()).throw(NativeClosureError("floats are forbidden")),
                parse_constant=lambda _x: (_ for _ in ()).throw(NativeClosureError("constants are forbidden")),
                object_pairs_hook=lambda pairs: _strict_pairs(pairs, where),
            )
        except NativeClosureError:
            raise
        except json.JSONDecodeError as exc:
            raise NativeClosureError(f"{where} is malformed JSON") from exc

    tasks_obj = load(task_payload, "task input")
    actions_obj = load(action_payload, "action input")
    if type(tasks_obj) is not dict or set(tasks_obj) != {"schema", "tasks"}:
        raise NativeClosureError("task input fields mismatch")
    if type(actions_obj) is not dict or set(actions_obj) != {"schema", "actions"}:
        raise NativeClosureError("action input fields mismatch")
    _text(tasks_obj["schema"], "task input schema")
    _text(actions_obj["schema"], "action input schema")
    raw_tasks = tasks_obj["tasks"]
    raw_actions = actions_obj["actions"]
    if type(raw_tasks) is not list or type(raw_actions) is not list:
        raise NativeClosureError("registered rows must be arrays")
    tasks: list[NativeTask] = []
    for row in raw_tasks:
        if type(row) is not dict:
            raise NativeClosureError("task row must be an exact object")
        try:
            spec = U05TaskSpec.from_frozen_record(row)
        except StrictContractError as exc:
            raise NativeClosureError("task row violates the frozen U05 contract") from exc
        tasks.append(NativeTask(spec.task_id, row))
    actions: list[NativeAction] = []
    for row in raw_actions:
        if type(row) is not dict:
            raise NativeClosureError("action row must be an exact object")
        try:
            symbol = ActionSymbol.from_frozen_action_record(row)
        except StrictContractError as exc:
            raise NativeClosureError("action row violates the frozen U05 contract") from exc
        actions.append(NativeAction(symbol.action_id, row))
    task_rows, action_rows = _preflight_registered_inputs(tasks, actions)
    return task_rows, action_rows, tasks_obj, actions_obj


def _strict_pairs(pairs: list[tuple[str, Any]], where: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise NativeClosureError(f"{where} has a duplicate/non-string key")
        result[key] = value
    return result


_OFFICIAL_IDENTITY_ENV = (
    "UPRIME_KP3_D4_C2_COMMIT",
    "UPRIME_KP3_D4_C2_TREE",
    "UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID",
    "UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID",
    "UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID",
    "UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID",
)


def _official_identity() -> dict[str, Any]:
    values: dict[str, str] = {}
    for name in _OFFICIAL_IDENTITY_ENV:
        value = os.environ.get(name)
        if type(value) is not str or not value:
            raise NativeClosureError(f"missing official identity {name}")
        values[name] = value
    for name in ("UPRIME_KP3_D4_C2_COMMIT", "UPRIME_KP3_D4_C2_TREE"):
        value = values[name]
        if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
            raise NativeClosureError(f"malformed official identity {name}")
    for name in _OFFICIAL_IDENTITY_ENV[2:]:
        if not values[name].isdigit() or values[name].startswith("0"):
            raise NativeClosureError(f"malformed official identity {name}")
    digest = _digest(
        os.environ.get("UPRIME_KP3_D4_ENVIRONMENT_DIGEST"),
        "official environment digest",
    )
    platform = _text(
        os.environ.get("UPRIME_KP3_D4_PLATFORM_RECORD"),
        "official platform record",
    )
    if os.environ.get("UPRIME_KP3_D4_C2_CONTROL_SCOPE") != OFFICIAL_CONTROL_SCOPE:
        raise NativeClosureError("official control attestation scope mismatch")
    raw_file_digests = os.environ.get("UPRIME_KP3_D4_C2_FILE_DIGESTS_JSON")
    raw_expected_file_digests = os.environ.get(
        "UPRIME_KP3_D4_C2_EXPECTED_FILE_DIGESTS_JSON"
    )
    if type(raw_file_digests) is not str:
        raise NativeClosureError("official C2 allowlist digests are absent")
    if type(raw_expected_file_digests) is not str:
        raise NativeClosureError("expected C2 allowlist digests are absent")
    try:
        file_digests = json.loads(
            raw_file_digests,
            object_pairs_hook=lambda pairs: _strict_pairs(pairs, "C2 file digests"),
            parse_float=lambda _value: (_ for _ in ()).throw(
                NativeClosureError("C2 file digests forbid floats")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                NativeClosureError("C2 file digests forbid constants")
            ),
        )
    except json.JSONDecodeError as exc:
        raise NativeClosureError("official C2 allowlist digests are malformed") from exc
    if type(file_digests) is not dict or set(file_digests) != OFFICIAL_C2_ALLOWLIST:
        raise NativeClosureError("official C2 allowlist inventory mismatch")
    for path, value in file_digests.items():
        _text(path, "C2 allowlist path")
        _digest(value, "C2 allowlist file digest")
    try:
        expected_file_digests = json.loads(
            raw_expected_file_digests,
            object_pairs_hook=lambda pairs: _strict_pairs(
                pairs, "expected C2 file digests"
            ),
        )
    except json.JSONDecodeError as exc:
        raise NativeClosureError("expected C2 allowlist digests are malformed") from exc
    if (
        expected_file_digests != file_digests
        or os.environ.get("UPRIME_KP3_D4_C2_FILE_DIGEST_MATCH") != "true"
    ):
        raise NativeClosureError("C2 external/actual file digest match is false")
    return {
        "c2_commit": values["UPRIME_KP3_D4_C2_COMMIT"],
        "c2_tree": values["UPRIME_KP3_D4_C2_TREE"],
        "c2_candidate_run_id": values["UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID"],
        "c2_candidate_job_id": values["UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID"],
        "c2_accepted_run_id": values["UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID"],
        "c2_accepted_job_id": values["UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID"],
        "environment_digest": digest,
        "platform_record": platform,
        "c2_allowlist_file_sha256": file_digests,
        "c2_control_attestation_scope": OFFICIAL_CONTROL_SCOPE,
        "c2_file_digest_match": True,
    }


def _official_base_artifact(identity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": OFFICIAL_ARTIFACT_SCHEMA,
        "run_state": "ORDINARY_RESULT_COMMITTED",
        **dict(identity),
        "powershell_executable_sha256": OFFICIAL_POWERSHELL_SHA256,
        "python_executable_sha256": OFFICIAL_PYTHON_SHA256,
        "lean_version": "4.31.0",
        "lean_commit": "68218e876d2a38b1985b8590fff244a83c321783",
        "lean_binary_sha256": OFFICIAL_LEAN_SHA256,
        "native_worker_blob": OFFICIAL_WORKER_BLOB,
        "rpc_client_blob": OFFICIAL_RPC_CLIENT_BLOB,
        "task_input_sha256": REGISTERED_TASK_RAW_SHA256,
        "task_input_canonical_sha256": REGISTERED_TASK_CANONICAL_SHA256,
        "action_input_sha256": REGISTERED_ACTION_RAW_SHA256,
        "action_input_canonical_sha256": REGISTERED_ACTION_CANONICAL_SHA256,
        "conditioning": None,
        "conditioning_censor": "NOT_ATTEMPTED_IN_THIS_PHASE",
    }


def build_official_artifact(
    identity: Mapping[str, Any],
    *,
    result: ConditionalNativeHistoryResult | None,
    failure_disposition: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Build and validate one ordinary (non-marker) E1 artifact variant."""

    artifact = _official_base_artifact(identity)
    if result is not None:
        if failure_disposition is not None or failure_reason is not None:
            raise NativeClosureError("successful artifact cannot retain failure metadata")
        result.__post_init__()
        production_receipt = _production_result_receipt(result, identity)
        if production_receipt is None:
            raise NativeClosureError(
                "successful official artifact requires exact production provenance"
            )
        result_wire = result.to_wire()
        result_wire["production_result_receipt"] = production_receipt
        above_cap = any(
            item.kind is ExactRankCertificateKind.RANK_AT_LEAST_65
            for item in result.certificates
        )
        artifact.update(
            {
                "scientific_disposition": (
                    "D4_FRESH_FAMILY_RANK_ABOVE_CAP_CONDITIONAL_KSTATE_MARKOV"
                    if above_cap
                    else "D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV"
                ),
                "failure_reason": None,
                "matrix": result_wire,
                "rank": {
                    "certificates": result_wire["certificates"],
                    "verifications": result_wire["rank_verifications"],
                },
            }
        )
    else:
        allowed = {
            "D4_NORMALIZATION_UNSOUND",
            "D4_DOMAIN_INCOMPLETE",
            "D4_RESOURCE_BLOCKED",
            "D4_EXECUTION_FAILED",
        }
        if failure_disposition not in allowed:
            raise NativeClosureError("invalid official failure disposition")
        artifact.update(
            {
                "scientific_disposition": failure_disposition,
                "failure_reason": _text(failure_reason, "failure_reason"),
                "matrix": None,
                "rank": None,
            }
        )
    validate_official_artifact(artifact)
    return artifact


def _validate_persisted_domain_wire(
    domain: Mapping[str, Any], *, expected_digest: str | None = None
) -> FiniteTotalActionDomain:
    if type(domain) is not dict:
        raise NativeClosureError("persisted domain must be an exact object")
    try:
        reconstructed = FiniteTotalActionDomain.from_json_bytes(
            _canonical_bytes(domain),
            expected_source_authority="registered-native-fresh-family",
        )
    except HistoryContractError as exc:
        raise NativeClosureError("persisted finite domain failed reconstruction") from exc
    if expected_digest is not None and reconstructed.digest != expected_digest:
        raise NativeClosureError("persisted finite domain digest mismatch")
    return reconstructed


def _validate_persisted_hankel_authority(
    hankel: Mapping[str, Any],
    certificate: Mapping[str, Any],
    verification: Mapping[str, Any],
    *,
    cutoff: int,
    source_digest: str,
    task_ids: tuple[str, ...],
    action_ids: tuple[str, ...],
) -> None:
    """Independently replay persisted coordinate, matrix, and rank authority."""

    if any(type(value) is not dict for value in (hankel, certificate, verification)):
        raise NativeClosureError("persisted H/rank evidence must be exact objects")
    try:
        row_keys = tuple(
            RawHankelRowKey(row[0], tuple(row[1])) for row in hankel["row_keys"]
        )
        suffix_words = tuple(tuple(word) for word in hankel["suffix_words"])
        retained_matrix = tuple(tuple(row) for row in hankel["matrix"])
    except (KeyError, TypeError, ValueError, StrictContractError) as exc:
        raise NativeClosureError("persisted H coordinates/matrix are malformed") from exc
    if any(
        type(row) is not list or any(type(cell) is not int for cell in row)
        for row in hankel["matrix"]
    ):
        raise NativeClosureError("persisted H matrix is not exact integer data")
    prefix_depth = cutoff // 2
    suffix_depth = (cutoff + 1) // 2
    n_tasks = len(task_ids)
    n_actions = len(action_ids)
    expected_prefixes = _action_words(action_ids, prefix_depth)
    expected_suffixes = _action_words(action_ids, suffix_depth)
    expected_row_keys = tuple(
        RawHankelRowKey(task_id, prefix)
        for task_id in task_ids
        for prefix in expected_prefixes
    )
    if row_keys != expected_row_keys or suffix_words != expected_suffixes:
        raise NativeClosureError("persisted H coordinate universe/order mismatch")
    prefix_count = sum(n_actions**depth for depth in range(prefix_depth + 1))
    suffix_count = sum(n_actions**depth for depth in range(suffix_depth + 1))
    dimensions = {
        "cutoff": cutoff,
        "prefix_depth": prefix_depth,
        "suffix_depth": suffix_depth,
        "n_rows": n_tasks * prefix_count,
        "n_suffixes": suffix_count,
        "n_columns": 7 * suffix_count,
        "n_word_coordinates": n_tasks * prefix_count * suffix_count,
        "n_cells": n_tasks * prefix_count * 7 * suffix_count,
        "raw_words_through_cutoff": n_tasks
        * sum(n_actions**depth for depth in range(cutoff + 1)),
    }
    if hankel.get("dimensions") != dimensions or len(retained_matrix) != dimensions["n_rows"]:
        raise NativeClosureError("persisted H dimensions mismatch")
    if any(
        len(row) != dimensions["n_columns"]
        or any(cell < -(1 << 63) or cell > (1 << 63) - 1 for cell in row)
        for row in retained_matrix
    ):
        raise NativeClosureError("persisted H matrix is not rectangular signed64")
    row_digest = _row_coordinate_digest(row_keys)
    column_digest = _column_coordinate_digest(suffix_words)
    response_digest = _digest(
        hankel.get("response_coordinate_digest"), "persisted response digest"
    )
    matrix_digest = _hankel_sha256(
        _matrix_binding_wire(
            cutoff=cutoff,
            source_digest=source_digest,
            exactness_scope=CONDITIONAL_KSTATE_MARKOV,
            row_keys=row_keys,
            suffix_words=suffix_words,
            matrix=retained_matrix,
            response_coordinate_digest=response_digest,
        )
    )
    equality = hankel.get("equality_report")
    if (
        hankel.get("cutoff") != cutoff
        or hankel.get("source_digest") != source_digest
        or hankel.get("exactness_scope") != CONDITIONAL_KSTATE_MARKOV
        or hankel.get("row_coordinate_digest") != row_digest
        or hankel.get("column_coordinate_digest") != column_digest
        or hankel.get("matrix_digest") != matrix_digest
        or hankel.get("conditioning") is not None
        or hankel.get("conditioning_censor") != "NOT_ATTEMPTED_IN_THIS_PHASE"
        or type(equality) is not dict
        or equality.get("word_coordinates_checked") != dimensions["n_word_coordinates"]
        or equality.get("channel_cells_checked") != dimensions["n_cells"]
        or equality.get("matrix_digest") != matrix_digest
        or equality.get("response_coordinate_digest") != response_digest
        or equality.get("exact_response_records_equal") is not True
    ):
        raise NativeClosureError("persisted H digest/equality/conditioning mismatch")
    try:
        basis, pivots, transcript, stopped = _fraction_verifier_scan(
            retained_matrix,
            stop_after=RANK_LOWER_BOUND_SIZE,
            bit_cap=MAX_EXACT_COEFFICIENT_BITS,
        )
    except StrictContractError as exc:
        raise NativeClosureError("persisted rank replay exceeded its exact cap") from exc
    kind = (
        ExactRankCertificateKind.RANK_AT_LEAST_65.value
        if stopped
        else ExactRankCertificateKind.COMPLETE_SPAN.value
    )
    rank = RANK_LOWER_BOUND_SIZE if stopped else len(basis)
    transcript_digest = _elimination_transcript_digest(matrix_digest, transcript, stopped)
    authority = _hankel_sha256(
        {
            "schema": "lean-rgc-odlrq-exact-rank-authority-v1",
            "cutoff": cutoff,
            "kind": kind,
            "rank_or_lower_bound": rank,
            "basis_row_indices": basis,
            "pivot_columns": pivots,
            "row_coordinate_digest": row_digest,
            "column_coordinate_digest": column_digest,
            "response_coordinate_digest": response_digest,
            "matrix_digest": matrix_digest,
            "source_digest": source_digest,
            "exactness_scope": CONDITIONAL_KSTATE_MARKOV,
            "elimination_transcript_digest": transcript_digest,
            "complete_span_verified": not stopped,
        }
    )
    if (
        certificate.get("kind") != kind
        or certificate.get("rank_or_lower_bound") != rank
        or certificate.get("basis_row_indices") != basis
        or certificate.get("pivot_columns") != pivots
        or certificate.get("elimination_transcript_digest") != transcript_digest
        or verification.get("certificate_digest") != authority
        or verification.get("verified") is not True
        or verification.get("basis_independent") is not True
        or verification.get("complete_span_verified") is not (not stopped)
        or verification.get("rows_checked") != len(transcript)
    ):
        raise NativeClosureError("persisted exact-rank authority mismatch")


def validate_official_artifact(value: Mapping[str, Any]) -> None:
    if type(value) is not dict:
        raise NativeClosureError("official artifact must be an exact object")
    fields = {
        "schema_version",
        "run_state",
        "c2_commit",
        "c2_tree",
        "c2_allowlist_file_sha256",
        "c2_control_attestation_scope",
        "c2_file_digest_match",
        "c2_candidate_run_id",
        "c2_candidate_job_id",
        "c2_accepted_run_id",
        "c2_accepted_job_id",
        "environment_digest",
        "platform_record",
        "powershell_executable_sha256",
        "python_executable_sha256",
        "lean_version",
        "lean_commit",
        "lean_binary_sha256",
        "native_worker_blob",
        "rpc_client_blob",
        "task_input_sha256",
        "task_input_canonical_sha256",
        "action_input_sha256",
        "action_input_canonical_sha256",
        "conditioning",
        "conditioning_censor",
        "scientific_disposition",
        "failure_reason",
        "matrix",
        "rank",
    }
    if set(value) != fields:
        raise NativeClosureError("official artifact field mismatch")
    if value["schema_version"] != OFFICIAL_ARTIFACT_SCHEMA:
        raise NativeClosureError("official artifact schema mismatch")
    if value["run_state"] != "ORDINARY_RESULT_COMMITTED":
        raise NativeClosureError("official artifact run state mismatch")
    for name in ("c2_commit", "c2_tree"):
        text = value[name]
        if type(text) is not str or len(text) != 40 or any(
            ch not in "0123456789abcdef" for ch in text
        ):
            raise NativeClosureError(f"official artifact {name} mismatch")
    file_digests = value["c2_allowlist_file_sha256"]
    if type(file_digests) is not dict or set(file_digests) != OFFICIAL_C2_ALLOWLIST:
        raise NativeClosureError("official artifact C2 allowlist mismatch")
    for digest in file_digests.values():
        _digest(digest, "official artifact C2 file digest")
    if value["c2_control_attestation_scope"] != OFFICIAL_CONTROL_SCOPE:
        raise NativeClosureError("official artifact control scope mismatch")
    if value["c2_file_digest_match"] is not True:
        raise NativeClosureError("official artifact C2 digest match is false")
    for name in (
        "c2_candidate_run_id",
        "c2_candidate_job_id",
        "c2_accepted_run_id",
        "c2_accepted_job_id",
    ):
        text = value[name]
        if type(text) is not str or not text.isdigit() or text.startswith("0"):
            raise NativeClosureError(f"official artifact {name} mismatch")
    _digest(value["environment_digest"], "artifact environment digest")
    _text(value["platform_record"], "artifact platform record")
    fixed = {
        "powershell_executable_sha256": OFFICIAL_POWERSHELL_SHA256,
        "python_executable_sha256": OFFICIAL_PYTHON_SHA256,
        "lean_version": "4.31.0",
        "lean_commit": "68218e876d2a38b1985b8590fff244a83c321783",
        "lean_binary_sha256": OFFICIAL_LEAN_SHA256,
        "native_worker_blob": OFFICIAL_WORKER_BLOB,
        "rpc_client_blob": OFFICIAL_RPC_CLIENT_BLOB,
        "task_input_sha256": REGISTERED_TASK_RAW_SHA256,
        "task_input_canonical_sha256": REGISTERED_TASK_CANONICAL_SHA256,
        "action_input_sha256": REGISTERED_ACTION_RAW_SHA256,
        "action_input_canonical_sha256": REGISTERED_ACTION_CANONICAL_SHA256,
    }
    if any(value[name] != expected for name, expected in fixed.items()):
        raise NativeClosureError("official artifact frozen identity mismatch")
    if value["conditioning"] is not None or value["conditioning_censor"] != "NOT_ATTEMPTED_IN_THIS_PHASE":
        raise NativeClosureError("official conditioning must remain censored null")
    disposition = value["scientific_disposition"]
    completed = disposition in {
        "D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV",
        "D4_FRESH_FAMILY_RANK_ABOVE_CAP_CONDITIONAL_KSTATE_MARKOV",
    }
    if completed:
        if type(value["matrix"]) is not dict or type(value["rank"]) is not dict or value["failure_reason"] is not None:
            raise NativeClosureError("completed artifact evidence shape mismatch")
        matrix = value["matrix"]
        rank = value["rank"]
        native_fields = {
            "schema_version",
            "exactness_scope",
            "native_semantics_digest",
            "chart_digest",
            "domain_digest",
            "open_states",
            "transition_rows",
            "elapsed_ms",
            "domain",
            "history",
            "raw_normalized_equality",
            "flow_verification",
            "duplicate_audit",
            "hankels",
            "certificates",
            "rank_verifications",
            "production_result_receipt",
        }
        if set(matrix) != native_fields:
            raise NativeClosureError("completed native result field mismatch")
        if (
            matrix["schema_version"] != NATIVE_RESULT_SCHEMA
            or matrix["exactness_scope"] != CONDITIONAL_KSTATE_MARKOV
        ):
            raise NativeClosureError("completed native artifact lost conditional scope")
        _digest(matrix["production_result_receipt"], "persisted production receipt")
        _digest(matrix["native_semantics_digest"], "persisted native semantics")
        _digest(matrix["chart_digest"], "persisted chart digest")
        _digest(matrix["domain_digest"], "persisted domain digest")
        _integer(matrix["elapsed_ms"], "persisted elapsed_ms")
        if matrix["elapsed_ms"] > MAX_NATIVE_SECONDS * 1_000:
            raise NativeClosureError("persisted result exceeded the whole wall")

        domain = matrix["domain"]
        domain_fields = {
            "schema_version",
            "source_authority",
            "semantics_digest",
            "exactness_floor",
            "tasks",
            "action_ids",
            "states",
            "transitions",
        }
        if type(domain) is not dict or set(domain) != domain_fields:
            raise NativeClosureError("persisted domain field mismatch")
        if (
            domain["source_authority"] != "registered-native-fresh-family"
            or domain["exactness_floor"] != CONDITIONAL_KSTATE_MARKOV
            or domain["semantics_digest"] != matrix["native_semantics_digest"]
            or _sha(domain) != matrix["domain_digest"]
            or type(domain["tasks"]) is not list
            or len(domain["tasks"]) != 5
            or type(domain["action_ids"]) is not list
            or len(domain["action_ids"]) != 12
            or domain["action_ids"] != sorted(domain["action_ids"])
            or len(set(domain["action_ids"])) != 12
            or type(domain["states"]) is not list
            or len(domain["states"]) != matrix["open_states"]
            or type(domain["transitions"]) is not list
            or len(domain["transitions"]) != matrix["transition_rows"]
            or matrix["transition_rows"] != matrix["open_states"] * 12
        ):
            raise NativeClosureError("persisted registered domain authority mismatch")
        if any(
            type(row) is not dict or set(row) != {"task_id", "source_identity_key"}
            for row in domain["tasks"]
        ) or any(
            type(row) is not dict
            or set(row) != {"identity_key", "full_signature", "debt", "response_signature"}
            for row in domain["states"]
        ) or any(
            type(row) is not dict
            or set(row)
            != {"source_identity_key", "action_id", "outcome_kind", "target_identity_key", "replay_digest"}
            for row in domain["transitions"]
        ):
            raise NativeClosureError("persisted domain nested field mismatch")
        try:
            reconstructed_domain = FiniteTotalActionDomain.from_json_bytes(
                _canonical_bytes(domain),
                expected_source_authority="registered-native-fresh-family",
            )
        except HistoryContractError as exc:
            raise NativeClosureError("persisted finite domain failed reconstruction") from exc
        if (
            reconstructed_domain.digest != matrix["domain_digest"]
            or reconstructed_domain.semantics_digest != matrix["native_semantics_digest"]
            or reconstructed_domain.exactness_floor != CONDITIONAL_KSTATE_MARKOV
        ):
            raise NativeClosureError("persisted reconstructed domain binding mismatch")

        history = matrix["history"]
        history_fields = {
            "chart_digest",
            "max_depth",
            "exactness_scope",
            "markov_contract",
            "report_preflight",
            "duplicate_row_checks",
            "layers",
        }
        if type(history) is not dict or set(history) != history_fields:
            raise NativeClosureError("persisted history field mismatch")
        markov = history["markov_contract"]
        if type(markov) is not dict or set(markov) != {
            "frame_digest",
            "transition_semantics_digest",
            "action_grammar_digest",
            "exactness_scope",
            "proof_status",
        }:
            raise NativeClosureError("persisted Markov contract field mismatch")
        expected_frame = _sha(
            {
                "schema_version": "lean-rgc-uprime-kp3-d4-native-frame-v1",
                "environment_digest": value["environment_digest"],
                "task_input": REGISTERED_TASK_CANONICAL_SHA256,
                "action_input": REGISTERED_ACTION_CANONICAL_SHA256,
            }
        )
        expected_action_grammar = _sha(
            {
                "schema_version": ACTION_GRAMMAR_SCHEMA,
                "action_ids": domain["action_ids"],
            }
        )
        if (
            history["chart_digest"] != matrix["chart_digest"]
            or history["max_depth"] != 4
            or history["exactness_scope"] != CONDITIONAL_KSTATE_MARKOV
            or markov["frame_digest"] != expected_frame
            or markov["transition_semantics_digest"] != matrix["native_semantics_digest"]
            or markov["action_grammar_digest"] != expected_action_grammar
            or markov["exactness_scope"] != CONDITIONAL_KSTATE_MARKOV
            or markov["proof_status"] != "UNPROVED_ASSUMPTION"
            or type(history["layers"]) is not list
            or [layer.get("depth") for layer in history["layers"]] != list(range(5))
        ):
            raise NativeClosureError("persisted history/Markov binding mismatch")
        for depth, layer in enumerate(history["layers"]):
            if type(layer) is not dict or set(layer) != {
                "depth", "raw_multiplicity", "classes", "incoming_edges"
            }:
                raise NativeClosureError("persisted history layer field mismatch")
            if type(layer["classes"]) is not list or type(layer["incoming_edges"]) is not list:
                raise NativeClosureError("persisted history layer arrays mismatch")
            if any(
                type(row) is not dict
                or set(row)
                != {"key", "representative_task_id", "representative_word", "raw_multiplicity"}
                for row in layer["classes"]
            ) or any(
                type(edge) is not dict
                or set(edge)
                != {"source_key", "action_id", "target_key", "witness_digest", "flow"}
                for edge in layer["incoming_edges"]
            ):
                raise NativeClosureError("persisted history nested field mismatch")
        chart_binding = {
            "schema_version": HISTORY_GRAMMAR_SCHEMA,
            "domain_digest": matrix["domain_digest"],
            "max_depth": 4,
            "exactness_scope": CONDITIONAL_KSTATE_MARKOV,
            "markov_contract": markov,
            "duplicate_row_checks": history["duplicate_row_checks"],
            "report_preflight": history["report_preflight"],
            "layers": [
                {
                    "depth": layer["depth"],
                    "classes": [
                        [
                            row["key"],
                            row["representative_task_id"],
                            row["representative_word"],
                            row["raw_multiplicity"],
                        ]
                        for row in layer["classes"]
                    ],
                    "edges": [
                        [
                            edge["source_key"],
                            edge["action_id"],
                            edge["target_key"],
                            edge["witness_digest"],
                            edge["flow"],
                        ]
                        for edge in layer["incoming_edges"]
                    ],
                }
                for layer in history["layers"]
            ],
        }
        if _sha(chart_binding) != matrix["chart_digest"]:
            raise NativeClosureError("persisted chart content digest mismatch")
        expected_semantics = _sha(
            {
                "schema_version": NATIVE_CLOSURE_SCHEMA,
                "frame_digest": expected_frame,
                "tasks": [row["task_id"] for row in domain["tasks"]],
                "actions": domain["action_ids"],
                "states": domain["states"],
                "rows": domain["transitions"],
            }
        )
        if expected_semantics != matrix["native_semantics_digest"]:
            raise NativeClosureError("persisted native semantics content mismatch")

        raw = matrix["raw_normalized_equality"]
        flow = matrix["flow_verification"]
        duplicate = matrix["duplicate_audit"]
        if (
            type(raw) is not dict
            or set(raw)
            != {"max_depth", "occurrence_count", "complete_response_digest", "source_digest", "equal"}
            or raw["max_depth"] != 3
            or raw["occurrence_count"] != 9_425
            or raw["source_digest"] != matrix["chart_digest"]
            or raw["equal"] is not True
        ):
            raise NativeClosureError("persisted depth-three equality mismatch")
        layer_totals = [5 * 12**depth for depth in range(5)]
        if (
            type(flow) is not dict
            or set(flow)
            != {"max_depth", "layer_totals", "streamed_occurrences_checked", "exact_raw_histogram_coverage", "streamed_histogram_digest", "source_digest"}
            or flow["max_depth"] != 4
            or flow["layer_totals"] != layer_totals
            or flow["streamed_occurrences_checked"] != sum(layer_totals)
            or flow["exact_raw_histogram_coverage"] is not True
            or flow["source_digest"] != matrix["chart_digest"]
        ):
            raise NativeClosureError("persisted depth-four flow mismatch")
        if (
            type(duplicate) is not dict
            or set(duplicate) != {"retained_occurrences", "rows_checked", "saturated", "digest"}
            or type(duplicate["retained_occurrences"]) is not int
            or not 0 <= duplicate["retained_occurrences"] <= MAX_DUPLICATE_OCCURRENCES
            or duplicate["rows_checked"] != duplicate["retained_occurrences"] * 12
            or history["duplicate_row_checks"] != duplicate["rows_checked"]
        ):
            raise NativeClosureError("persisted duplicate audit mismatch")

        hankels = matrix["hankels"]
        certificates = matrix["certificates"]
        verifications = matrix["rank_verifications"]
        if any(type(rows) is not list or len(rows) != 4 for rows in (hankels, certificates, verifications)):
            raise NativeClosureError("persisted H1-H4 family cardinality mismatch")
        for cutoff, (hankel, certificate, verification) in enumerate(
            zip(hankels, certificates, verifications, strict=True), start=1
        ):
            if type(hankel) is not dict or set(hankel) != {
                "cutoff", "source_digest", "exactness_scope", "row_keys",
                "suffix_words", "matrix", "dimensions", "row_coordinate_digest",
                "column_coordinate_digest", "response_coordinate_digest",
                "matrix_digest", "equality_report", "conditioning",
                "conditioning_censor",
            }:
                raise NativeClosureError("persisted Hankel field mismatch")
            if type(certificate) is not dict or set(certificate) != {
                "schema", "cutoff", "kind", "rank_or_lower_bound",
                "basis_row_indices", "pivot_columns", "row_coordinate_digest",
                "column_coordinate_digest", "response_coordinate_digest",
                "matrix_digest", "source_digest", "exactness_scope",
                "elimination_transcript_digest", "complete_span_verified",
            }:
                raise NativeClosureError("persisted certificate field mismatch")
            if type(verification) is not dict or set(verification) != {
                "verified", "basis_independent", "complete_span_verified",
                "rows_checked", "matrix_digest", "source_digest",
                "exactness_scope", "certificate_digest",
            }:
                raise NativeClosureError("persisted verification field mismatch")
            if type(hankel["dimensions"]) is not dict or set(hankel["dimensions"]) != {
                "cutoff", "prefix_depth", "suffix_depth", "n_rows", "n_suffixes",
                "n_columns", "n_word_coordinates", "n_cells",
                "raw_words_through_cutoff",
            } or type(hankel["equality_report"]) is not dict or set(hankel["equality_report"]) != {
                "cutoff", "word_coordinates_checked", "channel_cells_checked",
                "response_coordinate_digest", "matrix_digest",
                "exact_response_records_equal",
            }:
                raise NativeClosureError("persisted Hankel nested field mismatch")
            try:
                row_keys = tuple(
                    RawHankelRowKey(row[0], tuple(row[1]))
                    for row in hankel["row_keys"]
                    if type(row) is list and len(row) == 2 and type(row[1]) is list
                )
                suffix_words = tuple(
                    tuple(word) for word in hankel["suffix_words"]
                    if type(word) is list
                )
            except (TypeError, ValueError, StrictContractError) as exc:
                raise NativeClosureError("persisted Hankel coordinates are malformed") from exc
            if (
                len(row_keys) != len(hankel["row_keys"])
                or len(suffix_words) != len(hankel["suffix_words"])
                or type(hankel["matrix"]) is not list
            ):
                raise NativeClosureError("persisted Hankel coordinate coverage mismatch")
            expected_prefixes = _action_words(
                reconstructed_domain.action_ids, cutoff // 2
            )
            expected_suffixes = _action_words(
                reconstructed_domain.action_ids, (cutoff + 1) // 2
            )
            expected_row_keys = tuple(
                RawHankelRowKey(task_id, prefix)
                for task_id in reconstructed_domain.task_ids
                for prefix in expected_prefixes
            )
            if row_keys != expected_row_keys or suffix_words != expected_suffixes:
                raise NativeClosureError(
                    "persisted Hankel coordinate universe/order mismatch"
                )
            matrix_rows: list[tuple[int, ...]] = []
            width: int | None = None
            for row in hankel["matrix"]:
                if type(row) is not list:
                    raise NativeClosureError("persisted Hankel matrix row is not an array")
                if width is None:
                    width = len(row)
                if len(row) != width or any(
                    type(cell) is not int
                    or cell < -(1 << 63)
                    or cell > (1 << 63) - 1
                    for cell in row
                ):
                    raise NativeClosureError("persisted Hankel matrix is not signed64 rectangular")
                matrix_rows.append(tuple(row))
            retained_matrix = tuple(matrix_rows)
            dimensions = hankel["dimensions"]
            prefix_depth = cutoff // 2
            suffix_depth = (cutoff + 1) // 2
            prefix_count = sum(12**depth for depth in range(prefix_depth + 1))
            suffix_count = sum(12**depth for depth in range(suffix_depth + 1))
            expected_dimensions = {
                "cutoff": cutoff,
                "prefix_depth": prefix_depth,
                "suffix_depth": suffix_depth,
                "n_rows": 5 * prefix_count,
                "n_suffixes": suffix_count,
                "n_columns": 7 * suffix_count,
                "n_word_coordinates": 5 * prefix_count * suffix_count,
                "n_cells": 5 * prefix_count * 7 * suffix_count,
                "raw_words_through_cutoff": 5 * sum(12**depth for depth in range(cutoff + 1)),
            }
            if (
                dimensions != expected_dimensions
                or len(row_keys) != dimensions["n_rows"]
                or len(suffix_words) != dimensions["n_suffixes"]
                or len(retained_matrix) != dimensions["n_rows"]
                or width != dimensions["n_columns"]
            ):
                raise NativeClosureError("persisted Hankel dimension mismatch")
            expected_row_digest = _row_coordinate_digest(row_keys)
            expected_column_digest = _column_coordinate_digest(suffix_words)
            _digest(hankel["response_coordinate_digest"], "persisted response coordinate digest")
            expected_matrix_digest = _hankel_sha256(
                _matrix_binding_wire(
                    cutoff=cutoff,
                    source_digest=matrix["chart_digest"],
                    exactness_scope=CONDITIONAL_KSTATE_MARKOV,
                    row_keys=row_keys,
                    suffix_words=suffix_words,
                    matrix=retained_matrix,
                    response_coordinate_digest=hankel["response_coordinate_digest"],
                )
            )
            equality = hankel["equality_report"]
            if (
                hankel["row_coordinate_digest"] != expected_row_digest
                or hankel["column_coordinate_digest"] != expected_column_digest
                or hankel["matrix_digest"] != expected_matrix_digest
                or hankel["conditioning"] is not None
                or hankel["conditioning_censor"] != "NOT_ATTEMPTED_IN_THIS_PHASE"
                or equality["cutoff"] != cutoff
                or equality["word_coordinates_checked"] != dimensions["n_word_coordinates"]
                or equality["channel_cells_checked"] != dimensions["n_cells"]
                or equality["response_coordinate_digest"] != hankel["response_coordinate_digest"]
                or equality["matrix_digest"] != expected_matrix_digest
                or equality["exact_response_records_equal"] is not True
            ):
                raise NativeClosureError("persisted Hankel digest/equality/conditioning mismatch")
            if (
                hankel.get("cutoff") != cutoff
                or hankel.get("source_digest") != matrix["chart_digest"]
                or hankel.get("exactness_scope") != CONDITIONAL_KSTATE_MARKOV
                or certificate.get("cutoff") != cutoff
                or certificate.get("source_digest") != matrix["chart_digest"]
                or certificate.get("exactness_scope") != CONDITIONAL_KSTATE_MARKOV
                or certificate.get("matrix_digest") != hankel.get("matrix_digest")
                or certificate.get("row_coordinate_digest") != hankel.get("row_coordinate_digest")
                or certificate.get("column_coordinate_digest") != hankel.get("column_coordinate_digest")
                or certificate.get("response_coordinate_digest") != hankel.get("response_coordinate_digest")
                or verification.get("verified") is not True
                or verification.get("matrix_digest") != hankel.get("matrix_digest")
                or verification.get("source_digest") != matrix["chart_digest"]
                or verification.get("exactness_scope") != CONDITIONAL_KSTATE_MARKOV
            ):
                raise NativeClosureError("persisted H/certificate/verification splice mismatch")
            try:
                basis_indices, pivots, transcript, stopped = _fraction_verifier_scan(
                    retained_matrix,
                    stop_after=RANK_LOWER_BOUND_SIZE,
                    bit_cap=MAX_EXACT_COEFFICIENT_BITS,
                )
            except StrictContractError as exc:
                raise NativeClosureError("persisted exact-rank verifier exceeded its contract") from exc
            expected_kind = (
                ExactRankCertificateKind.RANK_AT_LEAST_65.value
                if stopped
                else ExactRankCertificateKind.COMPLETE_SPAN.value
            )
            expected_rank = RANK_LOWER_BOUND_SIZE if stopped else len(basis_indices)
            expected_transcript = _elimination_transcript_digest(
                expected_matrix_digest, transcript, stopped
            )
            expected_certificate_authority = _hankel_sha256(
                {
                    "schema": "lean-rgc-odlrq-exact-rank-authority-v1",
                    "cutoff": cutoff,
                    "kind": expected_kind,
                    "rank_or_lower_bound": expected_rank,
                    "basis_row_indices": basis_indices,
                    "pivot_columns": pivots,
                    "row_coordinate_digest": expected_row_digest,
                    "column_coordinate_digest": expected_column_digest,
                    "response_coordinate_digest": hankel["response_coordinate_digest"],
                    "matrix_digest": expected_matrix_digest,
                    "source_digest": matrix["chart_digest"],
                    "exactness_scope": CONDITIONAL_KSTATE_MARKOV,
                    "elimination_transcript_digest": expected_transcript,
                    "complete_span_verified": not stopped,
                }
            )
            if (
                certificate["schema"] != RANK_CERTIFICATE_SCHEMA
                or
                certificate["kind"] != expected_kind
                or certificate["rank_or_lower_bound"] != expected_rank
                or certificate["basis_row_indices"] != basis_indices
                or certificate["pivot_columns"] != pivots
                or certificate["elimination_transcript_digest"] != expected_transcript
                or certificate["complete_span_verified"] is not (not stopped)
                or verification["basis_independent"] is not True
                or verification["complete_span_verified"] is not (not stopped)
                or verification["rows_checked"] != len(transcript)
                or verification["certificate_digest"] != expected_certificate_authority
            ):
                raise NativeClosureError("persisted exact-rank authority mismatch")
        if (
            type(rank) is not dict
            or set(rank) != {"certificates", "verifications"}
            or rank["certificates"] != certificates
            or rank["verifications"] != verifications
        ):
            raise NativeClosureError("persisted rank copy mismatch")
        above_cap = any(
            certificate.get("kind") == ExactRankCertificateKind.RANK_AT_LEAST_65.value
            for certificate in certificates
        )
        expected_disposition = (
            "D4_FRESH_FAMILY_RANK_ABOVE_CAP_CONDITIONAL_KSTATE_MARKOV"
            if above_cap
            else "D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV"
        )
        if disposition != expected_disposition:
            raise NativeClosureError("persisted rank/disposition mismatch")
    elif (
        disposition
        not in {
            "D4_NORMALIZATION_UNSOUND",
            "D4_DOMAIN_INCOMPLETE",
            "D4_RESOURCE_BLOCKED",
            "D4_EXECUTION_FAILED",
        }
        or value["matrix"] is not None
        or value["rank"] is not None
        or type(value["failure_reason"]) is not str
        or not value["failure_reason"]
    ):
        raise NativeClosureError("failed artifact evidence shape mismatch")
    encoded = _canonical_bytes(value)
    if len(encoded) >= MAX_RESULT_BYTES:
        raise NativeResourceError("official artifact exceeds the 64 MiB cap")


def validate_run_opened_artifact(value: Mapping[str, Any]) -> None:
    """Validate the exact durable parent marker independently of a result."""

    if type(value) is not dict:
        raise NativeClosureError("RUN_OPENED marker must be an exact object")
    fields = {
        "schema_version", "run_state", "c2_commit", "c2_tree",
        "c2_candidate_run_id", "c2_candidate_job_id", "c2_accepted_run_id",
        "c2_accepted_job_id", "c2_allowlist_file_sha256",
        "c2_control_attestation_scope", "c2_file_digest_match", "environment_digest", "platform_record",
        "powershell_executable_sha256", "python_executable_sha256", "lean_version",
        "lean_commit", "lean_binary_sha256", "native_worker_blob", "rpc_client_blob",
        "task_input_sha256", "task_input_canonical_sha256", "action_input_sha256",
        "action_input_canonical_sha256", "conditioning", "conditioning_censor",
        "scientific_disposition", "failure_reason", "matrix", "rank",
    }
    if set(value) != fields:
        raise NativeClosureError("RUN_OPENED marker field mismatch")
    if (
        value["schema_version"] != OFFICIAL_ARTIFACT_SCHEMA
        or value["run_state"] != "RUN_OPENED"
        or value["scientific_disposition"] != "D4_EXECUTION_FAILED"
        or value["failure_reason"] != "process_or_os_terminated_after_open"
        or value["matrix"] is not None
        or value["rank"] is not None
        or value["conditioning"] is not None
        or value["conditioning_censor"] != "NOT_ATTEMPTED_IN_THIS_PHASE"
        or value["c2_control_attestation_scope"] != OFFICIAL_CONTROL_SCOPE
        or value["c2_file_digest_match"] is not True
    ):
        raise NativeClosureError("RUN_OPENED marker semantic mismatch")
    for name in (
        "environment_digest", "powershell_executable_sha256",
        "python_executable_sha256", "lean_binary_sha256", "task_input_sha256",
        "task_input_canonical_sha256", "action_input_sha256",
        "action_input_canonical_sha256",
    ):
        _digest(value[name], f"RUN_OPENED {name}")
    files = value["c2_allowlist_file_sha256"]
    if type(files) is not dict or set(files) != OFFICIAL_C2_ALLOWLIST:
        raise NativeClosureError("RUN_OPENED C2 allowlist mismatch")
    for digest in files.values():
        _digest(digest, "RUN_OPENED C2 file digest")


def _failure_record(exc: BaseException) -> tuple[str, str]:
    """Classify a cause chain without persisting raw exception text or paths."""

    seen: set[int] = set()
    current: BaseException | None = exc
    classification = ("D4_EXECUTION_FAILED", "EXECUTION_FAILED")
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (NativeResourceError, KernelRPCTransportTimeout)):
            classification = ("D4_RESOURCE_BLOCKED", "RESOURCE_BLOCKED")
            break
        if isinstance(current, (KernelRPCProcessExited, KernelRPCTransportError)):
            classification = ("D4_EXECUTION_FAILED", "EXECUTION_FAILED")
            break
        if isinstance(current, StrictContractError):
            message = str(current)
            if message.startswith("D4_RESOURCE_BLOCKED:"):
                classification = ("D4_RESOURCE_BLOCKED", "RESOURCE_BLOCKED")
                break
            if message.startswith("D4_NORMALIZATION_UNSOUND:"):
                classification = (
                    "D4_NORMALIZATION_UNSOUND",
                    "NORMALIZATION_UNSOUND",
                )
                break
        if isinstance(current, StrictKernelRPCError):
            classification = ("D4_DOMAIN_INCOMPLETE", "DOMAIN_INCOMPLETE")
            break
        if isinstance(current, NativeDomainError):
            classification = ("D4_DOMAIN_INCOMPLETE", "DOMAIN_INCOMPLETE")
            break
        if isinstance(current, NativeNormalizationError):
            classification = ("D4_NORMALIZATION_UNSOUND", "NORMALIZATION_UNSOUND")
            break
        current = current.__cause__ or current.__context__
    disposition, code = classification
    digest = _sha(
        {
            "schema_version": "lean-rgc-uprime-kp3-d4-failure-code-v1",
            "disposition": disposition,
            "failure_code": code,
        }
    )
    return disposition, f"{code}:{digest}"


def _write_exclusive_stage(path: Path, artifact: Mapping[str, Any]) -> None:
    validate_official_artifact(artifact)
    payload = _canonical_bytes(artifact)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_exclusive_receipt(
    path: Path,
    artifact_payload: bytes,
    artifact: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    stage_nonce: str,
    fixed_identity_digest: str,
    child_exit_code: int,
) -> None:
    receipt = {
        "schema_version": OFFICIAL_RECEIPT_SCHEMA,
        "stage_nonce": stage_nonce,
        "artifact_canonical": True,
        "artifact_sha256": hashlib.sha256(artifact_payload).hexdigest().upper(),
        "artifact_length": len(artifact_payload),
        "artifact_top_level_fields": sorted(artifact),
        "c2_allowlist_file_sha256": identity["c2_allowlist_file_sha256"],
        "c2_commit": identity["c2_commit"],
        "c2_control_attestation_scope": identity["c2_control_attestation_scope"],
        "c2_file_digest_match": identity["c2_file_digest_match"],
        "c2_tree": identity["c2_tree"],
        "child_exit_code": child_exit_code,
        "conditioning_censor": artifact["conditioning_censor"],
        "conditioning_is_null": artifact["conditioning"] is None,
        "environment_digest": identity["environment_digest"],
        "fixed_identity_digest": fixed_identity_digest,
        "run_state": artifact["run_state"],
        "scientific_disposition": artifact["scientific_disposition"],
    }
    payload = _canonical_bytes(receipt)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def run_official_from_environment() -> int:
    """Execute the fixed registered family; no scientific CLI is accepted."""

    if os.environ.get("UPRIME_KP3_D4_OFFICIAL_CHILD") != "1":
        raise NativeClosureError("official child is not armed")
    if (
        os.environ.get("UPRIME_KP3_D4_SCHEMA_VERSION") != OFFICIAL_ARTIFACT_SCHEMA
        or os.environ.get("UPRIME_KP3_D4_ROW_LIMIT") != str(MAX_TRANSITION_ROWS)
        or os.environ.get("UPRIME_KP3_D4_PER_ACTION_WALL_SECONDS") != str(MAX_ACTION_SECONDS)
        or os.environ.get("UPRIME_KP3_D4_WHOLE_WALL_SECONDS") != str(MAX_NATIVE_SECONDS)
    ):
        raise NativeClosureError("official frozen resource/schema environment mismatch")
    identity = _official_identity()
    repo_root = Path(_text(os.environ.get("UPRIME_KP3_D4_REPO_ROOT"), "repo root")).resolve()
    task_path = Path(_text(os.environ.get("UPRIME_KP3_D4_TASKS_PATH"), "task path")).resolve()
    action_path = Path(_text(os.environ.get("UPRIME_KP3_D4_ACTIONS_PATH"), "action path")).resolve()
    stage_path = Path(_text(os.environ.get("UPRIME_KP3_D4_OUTPUT_STAGE"), "stage path")).resolve()
    receipt_path = Path(_text(os.environ.get("UPRIME_KP3_D4_OUTPUT_RECEIPT"), "receipt path")).resolve()
    final_path = Path(_text(os.environ.get("UPRIME_KP3_D4_FINAL_PATH"), "final path")).resolve()
    lean_binary = Path(_text(os.environ.get("UPRIME_KP3_D4_LEAN_EXE"), "Lean path")).resolve()
    worker_source = Path(_text(os.environ.get("UPRIME_KP3_D4_NATIVE_WORKER"), "worker path")).resolve()
    expected_task = (repo_root / REGISTERED_TASK_PATH).resolve()
    expected_action = (repo_root / REGISTERED_ACTION_PATH).resolve()
    expected_final = (
        repo_root
        / "docs/experiments/artifacts/uprime_kp3_d4_20260712/fresh_family_d4.json"
    ).resolve()
    stage_nonce = _text(os.environ.get("UPRIME_KP3_D4_STAGE_NONCE"), "stage nonce")
    if len(stage_nonce) != 32 or any(ch not in "0123456789abcdef" for ch in stage_nonce):
        raise NativeClosureError("official stage nonce is malformed")
    fixed_identity_digest = _digest(
        os.environ.get("UPRIME_KP3_D4_FIXED_IDENTITY_DIGEST"),
        "fixed identity digest",
    )
    if task_path != expected_task or action_path != expected_action:
        raise NativeClosureError("official input paths are not the registered pair")
    if (
        final_path != expected_final
        or stage_path != Path(str(expected_final) + ".stage." + stage_nonce)
        or receipt_path != Path(str(expected_final) + ".receipt." + stage_nonce)
    ):
        raise NativeClosureError("official result/stage paths changed")
    if final_path.exists() is False:
        raise NativeClosureError("durable RUN_OPENED marker is absent")
    if stage_path.exists() or receipt_path.exists():
        raise NativeClosureError("official stage/receipt already exists")
    try:
        marker = json.loads(
            final_path.read_bytes().decode("utf-8", errors="strict"),
            object_pairs_hook=lambda pairs: _strict_pairs(pairs, "RUN_OPENED marker"),
            parse_float=lambda _value: (_ for _ in ()).throw(
                NativeClosureError("RUN_OPENED forbids floats")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                NativeClosureError("RUN_OPENED forbids constants")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise NativeClosureError("durable RUN_OPENED marker is malformed") from exc
    validate_run_opened_artifact(marker)
    for name, expected in identity.items():
        if name in marker and marker[name] != expected:
            raise NativeClosureError("RUN_OPENED identity differs from child identity")

    required_worker_env = {
        key: os.environ[key]
        for key in (
            "COMSPEC",
            "LANG",
            "LC_ALL",
            "PATH",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "WINDIR",
        )
    }
    exit_code = 0
    try:
        task_bytes = task_path.read_bytes()
        action_bytes = action_path.read_bytes()
        tasks, actions = parse_registered_input_bytes(task_bytes, action_bytes)
        factory = KernelRPCNativeFactory(
            repo_root=repo_root,
            lean_binary=lean_binary,
            worker_source=worker_source,
            environment_content_digest=identity["environment_digest"],
            worker_environment=required_worker_env,
        )
        result = build_conditional_native_history(
            tasks=tasks,
            actions=actions,
            factory=factory,
            source_authority="registered-native-fresh-family",
            frame_digest=_sha(
                {
                    "schema_version": "lean-rgc-uprime-kp3-d4-native-frame-v1",
                    "environment_digest": identity["environment_digest"],
                    "task_input": REGISTERED_TASK_CANONICAL_SHA256,
                    "action_input": REGISTERED_ACTION_CANONICAL_SHA256,
                }
            ),
        )
        artifact = build_official_artifact(identity, result=result)
    except BaseException as exc:
        exit_code = 1
        disposition, reason = _failure_record(exc)
        artifact = build_official_artifact(
            identity,
            result=None,
            failure_disposition=disposition,
            failure_reason=reason,
        )
    validate_official_artifact(artifact)
    artifact_payload = _canonical_bytes(artifact)
    _write_exclusive_stage(stage_path, artifact)
    _write_exclusive_receipt(
        receipt_path,
        artifact_payload,
        artifact,
        identity,
        stage_nonce=stage_nonce,
        fixed_identity_digest=fixed_identity_digest,
        child_exit_code=exit_code,
    )
    return exit_code


def official_child_main() -> int:
    return run_official_from_environment()


__all__ = [
    "ConditionalNativeHistoryResult",
    "DuplicateAuditReport",
    "MAX_DUPLICATE_OCCURRENCES",
    "MAX_NATIVE_SECONDS",
    "NATIVE_CLOSURE_SCHEMA",
    "NATIVE_RESULT_SCHEMA",
    "NativeAction",
    "NativeClosureError",
    "NativeOpenObservation",
    "NativeTask",
    "NativeTransition",
    "KernelRPCNativeFactory",
    "KernelRPCNativeSession",
    "StrictNativeFactory",
    "StrictNativeSession",
    "build_conditional_native_history",
    "build_official_artifact",
    "official_child_main",
    "parse_registered_input_bytes",
    "run_official_from_environment",
    "validate_official_artifact",
]


if __name__ == "__main__":
    raise SystemExit(official_child_main())
