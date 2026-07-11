# U'1 evidence milestone 2b phase 2b2e synthetic recovery coordinator amendment

Date: 2026-07-11

Status: PREREGISTERED SAME-PROCESS SYNTHETIC COORDINATOR ONLY; NO DURABLE
JOURNAL, CRASH OR POWER-LOSS FACT, CROSS-PROCESS EXCLUSION, CLEANUP, MANIFEST,
REAL RECOVERY, PUBLICATION, EXECUTION, LEAN, NETWORK, WORKER, REGISTERED-RUN,
LATER-STAGE, OR GPU AUTHORITY.

## 1. Prerequisite, purpose, and reduced claim

The committed and pushed Phase-2b2d result at
`8a80f01fd26ebd63072f77ca2a4bef381ec9da45`, together with successful hosted
CI run `29144018968` and job `86522332779`, licenses Phase-2b2e
**preregistration only**. It does not license this phase's source or support
code before this amendment is reviewed, committed, pushed, and green in
hosted CI.

Phase 2b2e freezes one live-process coordinator that owns the Phase-2b2d call,
one single-slot in-memory synthetic marker, same-instance publisher/recovery
exclusion, at most one active recovery epoch, a four-epoch budget, and at most
one same-instance single-use terminal witness. It is the smallest slice that
can test the state discipline required by Phase-2b1 Section 11 without
pretending that a forgeable caller-supplied Phase-2b2d Result authenticates an
I/O event.

The rejected alternative accepted a `LocalStagingFakePublishResultV10` from
the caller. That value is deliberately forgeable, describes only successful
returns, and does not attest that its stage existed. Letting it select a marker
would make evidence and cause caller-controlled and could not enforce
publisher/recovery exclusion. The production publish entrypoint therefore
accepts the exact Phase-2b2d inputs and invokes the anchored Phase-2b2d
function itself. It never accepts a Result, marker, failure code, recovery
observation, replay schedule, token, callback, or fault directive from the
caller.

This is still a finite synthetic same-kernel model. The constructor profile is
a caller-selected test scenario, not an observed cause. A `threading.Lock`
coordinates only methods on the same live coordinator. A direct Phase-2b2d
call, another coordinator, another process, a restart, or a machine failure
bypasses it. No returned hash or record upgrades that boundary.

Implementation may begin only on local Windows CPU after the amendment gate.
No SSH, remote host contact, GPU, network service, Lean, worker, registered
experiment, canonical diagnostic, or repository/canonical artifact write is
part of Phase 2b2e.

## 2. Exact paths, collection, anchors, and preregistration sentinel

The future implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_synthetic_recovery_coordinator.py
tests/uprime_rpc_synthetic_recovery_coordinator_cases.py
```

The support filename is outside pytest's default patterns. At implementation
time it will expose only its
`test_uprime_synthetic_recovery_coordinator_*` functions and be imported
exactly once by `tests/test_uprime_rpc_ledger.py`:

```python
from uprime_rpc_synthetic_recovery_coordinator_cases import *  # noqa: F403
```

This preregistration commit anchors only this amendment. It adds
`EVIDENCE_MILESTONE_2B_PHASE2B2E_AMENDMENT_PATH` to `ANCHOR_PATHS` and to the
independent membership test. It does not add future source, support, or result
paths.

An executable sentinel in `tests/test_uprime_rerun_license.py` requires both
future implementation files to be absent and the future collector import to
occur zero times. The sentinel may be replaced only by an implementation
commit whose parent contains this pushed amendment after its hosted CI is
green. That implementation commit adds exact source/support path constants,
both anchor memberships, and exactly-once collection. The execution-record
path is added only in a later result commit.

No package initializer or tier-manifest change is required in any of those
three commits. Git ancestry, push state, and hosted-CI conclusion remain
external governance observations; no local record or digest proves them.

## 3. Exact imports and public surface

Apart from blank lines, the source begins with exactly these imports:

```python
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import threading

from lean_rgc.evals.uprime_rpc_fake_cas_kernel import (
    InMemoryFakeCasStateV10,
    InMemoryFakeCasTransitionV10,
    InMemoryFakeCasV10Error,
    step_in_memory_fake_cas_v1_0,
)
from lean_rgc.evals.uprime_rpc_local_staging_fake_publisher import (
    LocalStagingFakePublishResultV10,
    LocalStagingFakePublisherV10Error,
    stage_and_fake_publish_normal_v1_0,
)
```

There is no randomness, secret, clock, PID, thread ID, UUID, environment,
filesystem module, subprocess, socket, HTTP, Git, Lean, worker, scanner,
writer, manifest, registry, or package-private import. Phase-2b2d remains the
only filesystem-capable dependency.

The exact ordered `__all__` is:

```text
SyntheticRecoveryCoordinatorV10Error
SyntheticRecoveryMarkerV10
SyntheticRecoverySnapshotV10
SyntheticRecoveryActionV10
SyntheticRecoveryEpochV10
SyntheticRecoveryWitnessV10
SyntheticRecoveryCoordinatorV10
new_synthetic_recovery_coordinator_v1_0
snapshot_synthetic_recovery_coordinator_v1_0
publish_with_synthetic_recovery_coordinator_v1_0
acquire_synthetic_recovery_epoch_v1_0
release_synthetic_recovery_epoch_v1_0
abandon_synthetic_recovery_epoch_v1_0
replay_synthetic_recovery_epoch_v1_0
consume_synthetic_recovery_witness_v1_0
```

There is one public exception:

```python
class SyntheticRecoveryCoordinatorV10Error(RuntimeError): ...
```

The exact positional-only public signatures are:

```python
def new_synthetic_recovery_coordinator_v1_0(
    constructor_profile: str,
    alternate_payload: bytes | None,
    /,
) -> SyntheticRecoveryCoordinatorV10: ...

def snapshot_synthetic_recovery_coordinator_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    /,
) -> SyntheticRecoverySnapshotV10: ...

def publish_with_synthetic_recovery_coordinator_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    staging_parent: str,
    collision_nonce: str,
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    /,
) -> SyntheticRecoveryActionV10: ...

def acquire_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    /,
) -> SyntheticRecoveryActionV10: ...

def release_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10: ...

def abandon_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10: ...

def replay_synthetic_recovery_epoch_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    epoch: SyntheticRecoveryEpochV10,
    /,
) -> SyntheticRecoveryActionV10: ...

def consume_synthetic_recovery_witness_v1_0(
    coordinator: SyntheticRecoveryCoordinatorV10,
    witness: SyntheticRecoveryWitnessV10,
    expected_purpose: str,
    expected_terminal_sha256: str,
    /,
) -> SyntheticRecoveryActionV10: ...
```

There are no defaults, keyword-only arguments, variadics, caller callbacks,
caller schedules, or public alternate entrypoints.

## 4. Exact constructor profiles

The ordered profile domain is:

```text
01 normal
02 ack_loss_confirmed
03 ack_loss_unavailable_then_confirmed
04 ack_loss_unavailable_until_budget_block
05 wrong_delta_confirmed
```

`alternate_payload` must be exact `None` for the first four profiles. It must
be exact `bytes` of length 0 through 1,048,576 for
`wrong_delta_confirmed`. At an owned call, the frozen Phase-2b2c wrong-delta
semantics also require it to differ by raw bytes from both the proposal and a
present current payload on a reached changed branch. Conflict and
existing-identical precedence do not inspect alternate semantics.

The profile is fixed for the coordinator lifetime. No publish or recovery
operation can replace it. Every owned publish first precomputes the common
normal classification with `apply_intended_acknowledge`; the table's directive
column lists only additional profile rows. Its exact synthetic transitions and
replay rows are:

| profile | additional precomputed Phase-2b2c profile directive(s) | changed-success endpoint | replay rows |
|---|---|---|---|
| `normal` | none | expose normal Result; no marker; `OPEN` | none |
| `ack_loss_confirmed` | `apply_intended_lose_ack_then_confirm` | append confirmed-ack-loss marker; withhold normal Result | `confirmed_intended` |
| `ack_loss_unavailable_then_confirmed` | first `apply_intended_lose_ack_confirmation_unavailable`, then `apply_intended_lose_ack_then_confirm` | append unavailable marker; withhold normal Result | `unavailable`, then `confirmed_intended` |
| `ack_loss_unavailable_until_budget_block` | `apply_intended_lose_ack_confirmation_unavailable` | append unavailable marker; withhold normal Result | `unavailable` four times |
| `wrong_delta_confirmed` | `substitute_alternate_then_confirm_wrong_delta` | append wrong-delta marker; withhold normal Result | `confirmed_wrong_delta` |

All required Phase-2b2c transitions are precomputed while the lifecycle is
`PUBLISHING` and before the Phase-2b2d physical call. Replay later selects a
bounded stored same-kernel row; it does not recompute, restage, stat, scan,
contact a remote store, or observe an independent fact. The words
`confirmed_intended` and `confirmed_wrong_delta` are model labels inherited
from the same kernel, never independent confirmation.

The marker's exact replay-plan row count is 1, 2, 4, and 1 for the four
nonnormal profiles in their listed order. A plan hashes every row in order;
the four unavailable rows deliberately repeat the same unavailable Transition
hash rather than constructing four distinguishable observations.

The profile remains armed after input/profile preflight error before the
Phase-2b2d call and after an exact conflict or existing-identical no-stage
Result. Once the separately precomputed normal Phase-2b2c row is changed and
the owned Phase-2b2d call begins, any exit without an exact Result is
conservatively spent into `POISONED_NO_MARKER`: the public Phase-2b2d API
cannot distinguish a pre-create error from a post-stage/pre-Result error. A
nonnormal profile is otherwise spent by marker commit or by post-Result poison.
The `normal` profile remains reusable only after a complete normal endpoint;
consequently cumulative successful stage residue across calls is not bounded
by one coordinator.

## 5. Exact public value records and live opaque handles

The three records use `@dataclass(frozen=True, slots=True)` and reject
subclasses, missing fields, bool-as-int, non-exact bytes/strings/tuples,
non-uppercase hex64, inconsistent nullability, and every row/hash mismatch.

Those checks cover each record's own cells and the exact public type plus
referenced digest cells of nested dependency records. A directly constructed
Action does not deep-revalidate all 63 fields and payload references of an
embedded Phase-2b2d Result; doing so would contradict the record's explicit
forgeability and O(1) transcript construction. The production publish path,
before constructing an Action, independently snapshots and reconstructs the
exact returned Phase-2b2d Result outside the Lock so a bypass-mutated private
seam result fails before exposure. That production validation is linear in the
payload and belongs to owned-publish work, not Action `__post_init__`.

`SyntheticRecoveryMarkerV10` has exactly these 36 ordered fields:

```python
marker_schema_version: str
marker_scope: str
origin_status: str
constructor_profile: str
coordinator_config_sha256: str
marker_kind: str
marker_ordinal: int
phase2b1_failure_codes: tuple[str, ...]
publisher_outcome: str
publisher_operation_sha256: str
publisher_transition_sha256: str
synthetic_fault_outcome: str
synthetic_fault_transition_sha256: str
replay_plan_sha256: str
replay_plan_row_count: int
before_state_version_sha256: str
intended_after_state_version_sha256: str
actual_after_state_version_sha256: str
intended_delta_sha256: str
actual_delta_sha256: str
stage_payload_bytes: int
stage_payload_sha256: str
marker_sha256: str
caller_profile_scope: str
cause_scope: str
journal_scope: str
stage_binding_scope: str
failure_code_scope: str
cleanup_scope: str
marker_provenance: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`SyntheticRecoverySnapshotV10` has exactly these 52 ordered fields:

```python
snapshot_schema_version: str
snapshot_scope: str
origin_status: str
constructor_profile: str
profile_status: str
alternate_payload_bytes: int | None
alternate_payload_sha256: str | None
coordinator_config_sha256: str
lifecycle_state: str
marker: SyntheticRecoveryMarkerV10 | None
marker_count: int
epoch_issue_count: int
replay_attempt_count: int
active_epoch_ordinal: int | None
active_epoch_nonce_sha256: str | None
terminal_epoch_ordinal: int | None
terminal_epoch_nonce_sha256: str | None
witness_status: str
witness_purpose: str | None
witness_nonce_sha256: str | None
terminal_kind: str | None
terminal_reason: str | None
terminal_sha256: str | None
snapshot_sha256: str
marker_count_upper_bound: int
active_epoch_upper_bound: int
recovery_epoch_upper_bound: int
witness_count_upper_bound: int
retained_payload_reference_upper_bound_bytes: int
retained_payload_copy_upper_bound_bytes: int
fixed_profile_scope: str
coordinator_ownership_scope: str
concurrency_scope: str
raw_bypass_scope: str
collision_nonce_scope: str
replay_scope: str
witness_scope: str
detached_record_scope: str
tamper_scope: str
pre_marker_error_scope: str
stage_residue_scope: str
cleanup_scope: str
journal_scope: str
process_restart_scope: str
manifest_scope: str
remote_publication: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`SyntheticRecoveryActionV10` has exactly these 33 ordered fields:

```python
action_schema_version: str
action_scope: str
origin_status: str
operation: str
outcome: str
reason_codes: tuple[str, ...]
before_snapshot_sha256: str
after_snapshot: SyntheticRecoverySnapshotV10
endpoint_state_changed: bool
publish_result: LocalStagingFakePublishResultV10 | None
marker: SyntheticRecoveryMarkerV10 | None
issued_epoch: SyntheticRecoveryEpochV10 | None
issued_witness: SyntheticRecoveryWitnessV10 | None
terminal_sha256: str | None
epoch_ordinal: int | None
replay_observation: str | None
action_sha256: str
exclusion_scope: str
action_record_scope: str
opaque_handle_scope: str
hash_authority_scope: str
cleanup_scope: str
stage_residue_scope: str
journal_scope: str
process_scope: str
remote_reobservation_scope: str
manifest_scope: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

The marker, snapshot, Action scalars, and every digest are forgeable value
data. Within the unmodified public API, the only live authority carried by an
Action is an opaque object reference that the caller has already received.
Copying or replacing the Action can convey that same already-held reference,
but cannot mint a new accepted identity. The Action itself is never submitted
back to the coordinator.

`coordinator_config_sha256` is present on both marker and snapshot, and the
snapshot requires an embedded marker to carry the same value. A standalone
snapshot does not retain the raw alternate payload and therefore cannot
rederive the config digest from its payload hash; this is another deliberate
forgeability boundary, not hidden authentication. Marker self-hash,
epoch-nonce, terminal, witness-nonce, snapshot, and Action hashes are otherwise
recomputable from the public scalar cells required by their rows. A marker's
plan digest binds its internally constructed plan, while a detached marker
does not expose or authenticate the plan rows themselves.

`SyntheticRecoveryEpochV10` is not a dataclass. Its ordinary constructor,
subclass constructor, `copy`, `deepcopy`, and pickle reconstruction reject.
Its exact private slots are:

```text
_issuer
_epoch_ordinal
_epoch_nonce_sha256
_epoch_sha256
```

Its read-only properties are exactly `epoch_ordinal`,
`epoch_nonce_sha256`, and `epoch_sha256`.

`SyntheticRecoveryWitnessV10` is likewise factory-only and rejects copy,
deepcopy, and pickle reconstruction. Its exact private slots are:

```text
_issuer
_purpose
_terminal_sha256
_witness_nonce_sha256
_witness_sha256
```

Its read-only properties are exactly `purpose`, `terminal_sha256`,
`witness_nonce_sha256`, and `witness_sha256`.

Constructor restriction is defense in depth, not the authority proof. Within
the unmodified public API, the coordinator accepts a handle only when its exact
object is the reference in that same coordinator's bounded current or terminal
slot, compared with `is`. Properties, equality, hashes, type membership,
dataclass validity, issuer-looking values, and a handle from another
coordinator never suffice.

Python private slots, frozen dataclasses, and module-private factory sentinels
are not a hostile in-process security boundary. Reflection,
`object.__setattr__`, direct private-state access, debugger mutation, import
hooking, and module monkeypatching can steal or replace live references or
code. Public operations revalidate exact private-state invariants and fail
closed on detectable bypass mutations, but arbitrary same-process tampering is
outside the claim.

`SyntheticRecoveryCoordinatorV10` is factory-only, has no public mutation
method, and rejects subclasses, copy, deepcopy, and pickle reconstruction. Its
exact private slots are:

```text
_lock
_issuer
_profile
_alternate_payload
_config_sha256
_publishing_state
_poisoned_state
_state
```

`_lock` is one `threading.Lock`; the last three state slots are immutable
private references. The factory prebuilds the fixed `PUBLISHING` and
`POISONED_NO_MARKER` pointers so exceptional repair requires only one pointer
assignment and never allocates or hashes while repairing. There is no
process-global registry or history.

## 6. Frozen constants and negative labels

The record constants are:

```text
marker_schema_version = lean-rgc-uprime-u1-synthetic-recovery-marker-v1.0
marker_scope = one_live_coordinator_single_slot_synthetic_marker
snapshot_schema_version = lean-rgc-uprime-u1-synthetic-recovery-snapshot-v1.0
snapshot_scope = same_process_same_live_coordinator_value_snapshot
action_schema_version = lean-rgc-uprime-u1-synthetic-recovery-action-v1.0
action_scope = one_coordinator_operation_lock_linearization_observation
origin_status = unknown_may_be_synthetic

caller_profile_scope = caller_selected_constructor_profile_not_observed_cause
cause_scope = same_kernel_synthetic_scenario_not_environmental_causality
journal_scope = single_slot_in_memory_marker_not_durable_journal
stage_binding_scope = publisher_operation_hash_only_no_current_stage_reobservation
failure_code_scope = internal_fixed_mapping_not_caller_supplied_cause_evidence
cleanup_scope = not_performed_unsafe_without_later_artifact_archive_binding
marker_provenance = internally_derived_after_owned_exact_changed_result

fixed_profile_scope = immutable_caller_selected_five_row_synthetic_profile
coordinator_ownership_scope = same_live_coordinator_owned_phase2b2d_call_only
concurrency_scope = same_live_coordinator_exclusion_only
raw_bypass_scope = raw_phase2b2d_and_cross_process_bypass_not_prevented
collision_nonce_scope = phase2b2d_collision_nonce_not_epoch_identity
replay_scope = bounded_same_kernel_replay_no_stage_or_remote_reobservation
witness_scope = same_instance_object_identity_single_use_witness
detached_record_scope = detached_records_and_hashes_forgeable_not_capabilities
tamper_scope = private_slot_reflection_or_module_monkeypatch_tampering_not_prevented
pre_marker_error_scope = pre_marker_errors_and_outside_calls_unjournaled
stage_residue_scope = stage_residue_may_remain_not_owned_current_durable_or_safe_to_remove
process_restart_scope = no_restart_reconstruction_or_crash_recovery
manifest_scope = not_read_or_written
remote_publication = not_performed
authority_scope = none

exclusion_scope = coordinator_methods_only_no_global_or_cross_process_lock
action_record_scope = lock_linearization_value_not_return_time_history_or_attestation
opaque_handle_scope = exact_same_instance_object_reference_is_only_live_authority
hash_authority_scope = deterministic_digest_not_identity_freshness_or_capability
remote_reobservation_scope = not_performed
```

All five booleans on all three records are exact false:

```text
canonical_remote_authority
licenses_execution
licenses_publication
licenses_recovery
licenses_later_stage
```

Here `licenses_recovery=false` means no real recovery authority. The API names
describe only the frozen synthetic state machine.

## 7. Exact digest grammar and golden fixtures

All digests are uppercase SHA-256. Let:

```text
U8(n) = one unsigned big-endian byte
U16(n) = two unsigned big-endian bytes
U64(n) = eight unsigned big-endian bytes
K(s) = U16(len(ASCII(s))) || ASCII(s)
H(h) = the 32 raw bytes represented by uppercase hex64 h
Q(h?) = 00 for null; 01 || H(h) otherwise
J(n?) = 00 for null; 01 || U64(n) otherwise
S(s?) = 00 for null; 01 || K(s) otherwise
T(strings) = U16(count) || K(strings[0]) || ... in exact tuple order
N(bytes?) = 00 for null; 01 || U64(length) || exact raw bytes otherwise
```

Strings in digest preimages are exact ASCII. The domains, including their
terminal NUL, are:

```text
D_CONFIG        = b"lean-rgc-uprime-u1-synthetic-recovery-config-v1\0"
D_PLAN          = b"lean-rgc-uprime-u1-synthetic-recovery-plan-v1\0"
D_MARKER        = b"lean-rgc-uprime-u1-synthetic-recovery-marker-v1\0"
D_EPOCH_NONCE   = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-nonce-v1\0"
D_EPOCH         = b"lean-rgc-uprime-u1-synthetic-recovery-epoch-v1\0"
D_TERMINAL      = b"lean-rgc-uprime-u1-synthetic-recovery-terminal-v1\0"
D_WITNESS_NONCE = b"lean-rgc-uprime-u1-synthetic-recovery-witness-nonce-v1\0"
D_WITNESS       = b"lean-rgc-uprime-u1-synthetic-recovery-witness-v1\0"
D_SNAPSHOT      = b"lean-rgc-uprime-u1-synthetic-recovery-snapshot-v1\0"
D_ACTION        = b"lean-rgc-uprime-u1-synthetic-recovery-action-v1\0"
```

The exact dynamic formulas are:

```text
config = SHA256(
  D_CONFIG || K(profile) || N(alternate_payload)
)

plan = SHA256(
  D_PLAN || K(profile) || U16(row_count) ||
  each K(replay_observation) || H(transition_sha256)
)

marker = SHA256(
  D_MARKER || H(config) || U64(marker_ordinal) || K(marker_kind) ||
  T(phase2b1_failure_codes) || K(publisher_outcome) ||
  H(publisher_operation_sha256) || H(publisher_transition_sha256) ||
  K(synthetic_fault_outcome) || H(synthetic_fault_transition_sha256) ||
  H(replay_plan_sha256) || U16(replay_plan_row_count) ||
  H(before_state_version_sha256) ||
  H(intended_after_state_version_sha256) ||
  H(actual_after_state_version_sha256) || H(intended_delta_sha256) ||
  H(actual_delta_sha256) || U64(stage_payload_bytes) ||
  H(stage_payload_sha256)
)

epoch_nonce = SHA256(
  D_EPOCH_NONCE || H(config) || H(marker) || U64(epoch_ordinal)
)

epoch = SHA256(
  D_EPOCH || H(config) || H(marker) || U64(epoch_ordinal) || H(epoch_nonce)
)

terminal = SHA256(
  D_TERMINAL || H(config) || H(marker) || K(terminal_kind) ||
  K(terminal_reason) || U64(epoch_ordinal) || H(epoch_nonce) ||
  U64(epoch_issue_count) || U64(replay_attempt_count)
)

witness_nonce = SHA256(
  D_WITNESS_NONCE || H(config) || H(terminal) || K(witness_purpose)
)

witness = SHA256(
  D_WITNESS || H(config) || H(terminal) || K(witness_purpose) ||
  H(witness_nonce)
)

snapshot = SHA256(
  D_SNAPSHOT || K(profile) || K(profile_status) ||
  J(alternate_payload_bytes) || Q(alternate_payload_sha256) || H(config) ||
  K(lifecycle_state) || Q(marker_sha256) || U64(marker_count) ||
  U64(epoch_issue_count) || U64(replay_attempt_count) ||
  J(active_epoch_ordinal) || Q(active_epoch_nonce_sha256) ||
  J(terminal_epoch_ordinal) || Q(terminal_epoch_nonce_sha256) ||
  K(witness_status) || S(witness_purpose) || Q(witness_nonce_sha256) ||
  S(terminal_kind) || S(terminal_reason) || Q(terminal_sha256)
)

action = SHA256(
  D_ACTION || K(operation) || K(outcome) || T(reason_codes) ||
  H(before_snapshot_sha256) || H(after_snapshot_sha256) ||
  U8(endpoint_state_changed) || Q(publish_result.operation_sha256) ||
  Q(marker_sha256) || J(epoch_ordinal) || S(replay_observation) ||
  Q(terminal_sha256) || S(witness_purpose)
)
```

`U8(endpoint_state_changed)` is `00` or `01`. Opaque object identity is
deliberately absent from every digest. Static scope/authority fields are exact
constructor invariants rather than dynamic identity claims.

In the numeric fixtures, `11*32` means the raw byte `0x11` repeated 32 times,
and likewise for `AA*32`, `01*32`, and the other two-hex-digit tokens.
The wrong-delta alternate is `b"C"`, whose SHA-256 is
`6B23C0D5F35D1B11F9B683F0B0A617355DEB11277D91AE091D399C655B87940D`.
The distinct staged proposal is `b"B"`, whose SHA-256 is
`DF7E70E5021544F4834BBEE64A9E3789FEBC4BE81470DF629CAD6DDB03320A5C`.
The populated marker fixture is exactly:

```text
config = config(wrong_delta_confirmed, b"C")
marker_ordinal = 1
marker_kind = synthetic_wrong_delta_confirmed
phase2b1_failure_codes = (OTHER_HARNESS_ERROR,)
publisher_outcome = staged_intended_fake_publish_acknowledged
publisher_operation_sha256 = AA*32
publisher_transition_sha256 = BB*32
synthetic_fault_outcome = wrong_delta_confirmed
synthetic_fault_transition_sha256 = CC*32
replay_plan = plan(wrong_delta_confirmed, [(confirmed_wrong_delta, CC*32)])
replay_plan_row_count = 1
before/intended-after/actual-after/intended-delta/actual-delta =
  01*32 / 02*32 / 03*32 / 04*32 / 05*32
stage_payload_bytes = 1
stage_payload_sha256 = SHA256(b"B")
```

Its epoch is ordinal 1. Its terminal fixture has kind `permanent_block`, reason
`synthetic_wrong_delta_confirmed`, issue count 1 and replay count 1. Its
witness purpose is `record_permanent_block`. The open fixture is profile
`normal`, status `normal_no_fault_profile`, lifecycle `OPEN`, witness status
`none`, all counts zero, and every nullable dynamic cell null. The populated
blocked snapshot uses the marker/epoch/terminal/witness fixtures above,
`BLOCKED_WITNESS_LIVE`, status `spent_marker_committed`, and no active epoch.

The exact preregistered goldens are:

| fixture | uppercase SHA-256 |
|---|---|
| config: `normal`, null alternate | `0D68B8B1D6B42C8F4B997C2FE7DF5A5C20202AD122B3D14BFAECE54E25F64AF6` |
| config: `wrong_delta_confirmed`, `b"C"` | `5A34577883038E7C9DFA57FF7A9756A37AD626E826DDAB81A8C2BDF7BF5F4298` |
| plan: `unavailable`/`11*32`, `confirmed_intended`/`22*32` | `6BC4CDF9E2E901BDC799198CCC81443188C0D07C68599D34FE7584F1BB33AAE5` |
| plan: `confirmed_wrong_delta`/`CC*32` | `F754028D8E353EA09F32320B39FC651D5B20FE29A9C004456663FA0D100368E5` |
| populated marker | `541246B7A32A2FE90823D3A1E64EDE4AB4FA28A627B2CB7C989E7A8D669D8D12` |
| epoch nonce, ordinal 1 | `8A930B2031BC188FBD8AC99FF60BF5AE30DD0EDC8969035D3B2BF8C133B2402C` |
| epoch, ordinal 1 | `AF2990CD863064FAC8EF53ED47B0107DCEF499ADF99E1B7B551E3DE24B341C4A` |
| permanent-block terminal | `2F8EB9FFC70DBF4D4DDE9E6F04843DDAE6A7390F5EB846B89FD30F44CF5BFA00` |
| block witness nonce | `8101AE2086953536B63F0BEA184C90811DA249C7671BF0668812A4C8C3D0D73C` |
| block witness | `2A66126FB24A405129734382D1BA40D0B71DAF5D85236AF6E0738D3853022C55` |
| normal open snapshot | `FA9664700ABA3A3EDCDDE86F680C0F7F11F3766F10D3442DD4B98A3573B702B1` |
| populated blocked-live snapshot | `64C69993C955E87A22721ACE58BBD1E2C2DEDA0B1205B4366EEA92399E4D4ED3` |
| acquire/no-marker Action over the open snapshot, reason `marker_absent` | `15EA2F80965361634232766A22E8A38722BE0741079C3617D63A4D16F550B7D3` |
| wrong-delta block replay Action from before hash `10*32` | `080367654D63791B4796DAF54D772742306DC7F29DD8F81EB240D20B4ECFD48F` |

The maximum valid config preimage is exactly 1,048,656 bytes: only
`wrong_delta_confirmed` permits the nonnull 1,048,576-byte alternate. The fixed upper bounds
for plan, marker, epoch-nonce, epoch, terminal, witness-nonce, witness,
snapshot, and Action preimages are respectively 309, 555, 125, 151, 241, 146,
172, 530, and 480 bytes. The Action bound permits at most two reason codes;
every frozen row below uses one.

## 8. Marker kinds and exact Phase-2b1 failure-code mapping

There is one marker at most and its ordinal is exactly 1. The exact mapping is:

| initial fault outcome | marker kind | Phase-2b1 failure codes |
|---|---|---|
| `intended_applied_ack_lost_confirmed` | `synthetic_ack_loss_confirmed` | `("OTHER_HARNESS_ERROR",)` |
| `intended_applied_ack_lost_unconfirmed` | `synthetic_ack_loss_unavailable` | `("OTHER_HARNESS_ERROR",)` |
| `wrong_delta_confirmed` | `synthetic_wrong_delta_confirmed` | `("OTHER_HARNESS_ERROR",)` |

The mapping is derived internally from the frozen profile transition and
cannot be supplied or relabeled by a caller or Phase 2b2f. All three are
caller-selected synthetic harness scenarios. Although the wrong-delta model's
actual delta differs from its intended delta, inherited Phase-2b2c cause and
application attribution are unauthenticated, so this phase deliberately does
not upgrade it to `OTHER_ATTEMPT_ERROR`.

`POWER_LOSS`, `CLAIM_STARTED_MANIFEST_ERROR`, and `FINAL_MANIFEST_ERROR` are
not emitted because this phase observes no power loss and writes no manifest.
This is an intentional refusal to turn a profile name into causal evidence.
Phase 2b2f may serialize the exact tuple already carried by a marker, but may
not infer, upgrade, or substitute a failure code.

The marker binds the Phase-2b2d operation/transition hashes, the exact staged
payload scalar/hash, the synthetic fault transition and replay plan. It does
not restat the stage, authenticate its namespace, prove current existence,
establish durability, or make deletion safe.

## 9. Exact nine-state machine and invariants

The ordered lifecycle domain is exactly:

```text
01 OPEN
02 PUBLISHING
03 RECOVERY_PENDING
04 RECOVERY_ACTIVE
05 RECOVERED_WITNESS_LIVE
06 RECOVERED_WITNESS_SPENT
07 BLOCKED_WITNESS_LIVE
08 BLOCKED_WITNESS_SPENT
09 POISONED_NO_MARKER
```

There is no cross-product of hidden lifecycle flags. One immutable private
state enforces:

- `OPEN`: no marker, epoch, terminal, or witness; profile armed, except that
  `normal` is labeled `normal_no_fault_profile`;
- `PUBLISHING`: no marker, epoch, terminal, or witness; one owned call or its
  pre/postprocessing is in progress;
- `RECOVERY_PENDING`: exactly one marker; no active/terminal epoch or witness;
- `RECOVERY_ACTIVE`: one marker and one exact active epoch; no witness;
- recovered/blocked live: one marker, retained terminal epoch, terminal hash,
  exact terminal kind/reason, and one live witness of the exact purpose;
- recovered/blocked spent: the same terminal state and same retained epoch and
  witness object, with witness status `spent`;
- `POISONED_NO_MARKER`: no marker, epoch, terminal, or witness; profile spent;
  no later marker repair is allowed.

All nonterminal snapshots have null terminal kind, reason, digest, purpose and
witness nonce. Terminal kind/reason are nonnull together, recompute the exact
terminal digest with the retained epoch/count cells, and determine the sole
allowed witness purpose.

`marker_count` is 0 or 1. `epoch_issue_count` and
`replay_attempt_count` are exact integers in 0..4, with replay count no larger
than issue count. There is never more than one accepted epoch reference and
one accepted witness reference. Old nonterminal epoch references are dropped,
not retained as history, and thereafter fail identity validation.

In `RECOVERY_ACTIVE`, `active_epoch_ordinal == epoch_issue_count` and both are
in 1..4. In every recovered/blocked state,
`terminal_epoch_ordinal == epoch_issue_count` and both are in 1..4.
`RECOVERY_PENDING` has issue count 0..3; ordinal 4 can never return pending.

The exact profile/cursor reachability constraints are:

- `ack_loss_confirmed`: pending/active replay count is 0; a recovered terminal
  has replay count 1; release/abandon budget block has replay count 0;
- `ack_loss_unavailable_then_confirmed`: pending/active replay count is 0 or
  1; a recovered terminal has replay count 2; unavailable-at-budget block has
  replay count 1 and release/abandon block has count 0 or 1;
- `ack_loss_unavailable_until_budget_block`: pending replay count is 0..3;
  active replay count is at most `epoch_issue_count - 1`; unavailable-at-budget
  block has replay count 1..4 and release/abandon block has count 0..3;
- `wrong_delta_confirmed`: pending/active replay count is 0; wrong-delta block
  has replay count 1 and release/abandon block has count 0; and
- `normal` cannot reach any marker, epoch, terminal, or witness state.

The record validator enumerates the finite transition table in Sections 10--12
for ordinals 1..4 and accepts only a reachable tuple. The scalar inequalities
above are necessary summaries, not a relaxation permitting an otherwise
unreachable snapshot.

Snapshot `profile_status` is derived exactly:

```text
normal_no_fault_profile   normal + OPEN
armed                     nonnormal + OPEN
owned_call_in_progress    PUBLISHING
spent_marker_committed    marker-bearing states
spent_without_marker      POISONED_NO_MARKER
```

The exact ordered `witness_status` domain and mapping are:

```text
01 none   every nonterminal lifecycle
02 live   RECOVERED_WITNESS_LIVE or BLOCKED_WITNESS_LIVE
03 spent  RECOVERED_WITNESS_SPENT or BLOCKED_WITNESS_SPENT
```

## 10. Owned publish order, exclusion, and error adjudication

The production order is:

1. validate frozen constants and exact coordinator type;
2. acquire the coordinator Lock, require `OPEN`, retain the exact old state,
   and commit the factory-prebuilt `PUBLISHING` pointer once;
3. release the Lock;
4. read the caller State's exact 26 public fields once into a local tuple and
   reconstruct one private exact `InMemoryFakeCasStateV10`; retain the same
   immutable expected-version string and proposal bytes references;
5. derive the normal Phase-2b2c transition and every required profile
   transition outside the Lock; the normal row fixes whether the physical call
   is a proven no-stage row or a changed call, and the factory-prebuilt poison
   pointer is already available;
6. immediately before calling exact
   `stage_and_fake_publish_normal_v1_0` outside the Lock, set the local
   `changed_call_started` flag from that normal row, then pass the same private
   State snapshot, expected string, and proposal bytes to Phase 2b2d;
7. snapshot/reconstruct the exact returned Result outside the Lock and validate
   its consistency with the independently derived normal/profile transitions;
8. classify conflict, existing-identical, or exact changed success;
9. build the complete prospective marker, replay plan, snapshots, Action, and
   next immutable state outside the Lock;
10. reacquire the Lock, require the unchanged `PUBLISHING` pointer, replace it
   once with the prospective state, release, and expose the Action.

The private State reconstruction retains the same immutable payload reference
and makes no payload copy. Every direct Phase-2b2c derivation and the owned
Phase-2b2d call receives that one reconstructed object, never the caller's
mutable-by-reflection object. A caller mutation before/during the 26-field read
either fails reconstruction or selects one value-consistent private snapshot;
mutation after reconstruction cannot change classification or the physical
call. A returned no-stage/normal Result therefore contains the private
snapshot as its transition's before-State rather than promising caller-object
identity.

No filesystem operation, payload hash, Phase-2b2c transition derivation,
caller callback, or unbounded work occurs while the Lock is held. Snapshot and
excluded-action construction are fixed-size work. Other methods can acquire
the Lock while the physical call is in progress, observe `PUBLISHING`, and
return a typed no-change exclusion; they cannot start another owned publisher
or recovery operation.

The exact owned-publish endpoints are:

| starting state/result | endpoint | Result exposure | marker |
|---|---|---|---|
| `OPEN`, conflict | `OPEN`, `cas_conflict_no_marker` | exact no-stage Result | none |
| `OPEN`, existing-identical | `OPEN`, `cas_existing_identical_no_marker` | exact no-stage Result | none |
| `OPEN`, changed + `normal` | `OPEN`, `normal_staged_result_exposed_no_marker` | exact changed Result | none |
| `OPEN`, changed + nonnormal | `RECOVERY_PENDING`, `synthetic_marker_committed_result_withheld` | `None` | exact one |
| any non-`OPEN` | unchanged, `publisher_excluded_non_open` | `None` | unchanged |

The caller-selected Phase-2b2d collision nonce remains only a path collision
separator. It is neither operation nor epoch identity.

Failure adjudication has three exact zones:

- validation or Phase-2b2c profile error before the Phase-2b2d call restores
  the retained exact `OPEN` pointer, creates no marker, and keeps the profile
  armed;
- if the precomputed normal row is conflict/existing-identical, any
  Phase-2b2d failure also restores `OPEN`, because that public branch is
  contractually no-stage; an exact no-stage Result and its postprocessing do
  likewise;
- if the precomputed normal row is changed, every ordinary error or
  non-`Exception` `BaseException` after the Phase-2b2d call begins but before
  an exact Result selects the prebuilt `POISONED_NO_MARKER` pointer and spends
  the profile, because the physical effect is not observable through the
  public API;
- once an exact changed Result has returned, any failure before the complete
  normal Action or marker-bearing Action is atomically committed selects the
  prebuilt `POISONED_NO_MARKER` pointer, withholds the Result, and re-raises or
  maps the primary failure;
- conflict/identical postprocessing failure restores `OPEN` because the exact
  Result proves that the Phase-2b2d branch created no stage;
- repair/rollback never masks a primary `BaseException` because it is a
  prebuilt pointer replacement under `finally` discipline.

If the independently derived normal row and a completely reconstructed Result
disagree, the call fails closed. Poison is selected when either the precomputed
row or the valid Result is changed; `OPEN` is restored only when both are the
same no-stage row. This rule prevents a mismatch error from erasing a possible
physical effect.

After repair, an exact `SyntheticRecoveryCoordinatorV10Error` is re-raised.
Every other ordinary `Exception`, including the two imported dependency error
types and a private-seam test exception, is mapped with suppressed chaining to
one `SyntheticRecoveryCoordinatorV10Error`. Its sole argument is
`owned publish failed before changed call` before a changed call begins,
`owned changed publish failed without exact changed endpoint` after such a
call begins but before an agreeing exact changed endpoint, and
`owned publish endpoint failed after exact changed result` after the exact
Result. A
non-`Exception` `BaseException` such as the exact injected test sentinel is
re-raised unchanged. This preserves the one public ordinary-error surface
without allowing any mapped failure to alter the rollback/poison decision.

A changed Phase-2b2d call can error after a partial or complete retained stage
without returning a Result. Such residue remains explicitly unjournaled, but
the coordinator stays fail-closed in `POISONED_NO_MARKER` and never retries or
retrofits a marker. The same state is used after an exact changed Result whose
complete endpoint could not be exposed. It means only that a changed public
call began and this coordinator lacks a complete attributable endpoint. It
does not prove that a stage was created, nor mean crash, orphan, power loss,
durability, or safe cleanup.

## 11. Epoch, replay, release, abandonment, and terminal rules

An acquire in `RECOVERY_PENDING` increments `epoch_issue_count`, mints one new
opaque identity, derives its deterministic nonce/hash labels, and enters
`RECOVERY_ACTIVE`. Every acquire consumes one ordinal in 1..4. There is no
fifth epoch.

Acquire in `OPEN` is `no_marker_noop`; in `PUBLISHING` or
`RECOVERY_ACTIVE` it is a typed exclusion; in either recovered/blocked state it
is the corresponding terminal no-op; and in `POISONED_NO_MARKER` it is
`poisoned_no_marker_noop`. None issues a token.

For the exact active token:

- release at ordinal 1..3 invalidates it, preserves the replay cursor, and
  returns to `RECOVERY_PENDING`;
- abandonment at ordinal 1..3 has the same state effect with a distinct
  outcome/reason;
- release or abandonment at ordinal 4 is unresolved budget exhaustion and
  atomically enters `BLOCKED_WITNESS_LIVE` with the one block witness;
- replay increments `replay_attempt_count` and consumes the next fixed profile
  row; `unavailable` at ordinal 1..3 invalidates the epoch and returns pending;
- `unavailable` at ordinal 4 enters blocked terminal;
- `confirmed_intended` enters `RECOVERED_WITNESS_LIVE`;
- `confirmed_wrong_delta` enters `BLOCKED_WITNESS_LIVE`.

Thus release/abandon do not advance the replay cursor but do consume the
finite epoch ordinal. This closes the otherwise unbounded fifth-acquire hole.

The epoch that causes a terminal transition remains in the sole terminal
slot. Replaying that exact object in the matching recovered/blocked live or
spent state returns the matching terminal no-op and issues nothing. Every
older, released, abandoned, retry-completed, copied, forged, or foreign epoch
is a hard error without mutation. Release/abandon with a terminal or stale
epoch is also a hard error.

The fixed terminal mapping is exhaustive:

| terminal transition | `terminal_kind` | `terminal_reason` | witness purpose |
|---|---|---|---|
| replay `confirmed_intended` | `recovered_terminal` | `synthetic_intended_transition_confirmed` | `record_recovered_terminal` |
| replay `confirmed_wrong_delta` | `permanent_block` | `synthetic_wrong_delta_confirmed` | `record_permanent_block` |
| replay `unavailable` at ordinal 4 | `permanent_block` | `recovery_epoch_budget_exhausted_after_unavailable` | `record_permanent_block` |
| release at ordinal 4 | `permanent_block` | `recovery_epoch_budget_exhausted_after_release` | `record_permanent_block` |
| abandon at ordinal 4 | `permanent_block` | `recovery_epoch_budget_exhausted_after_abandon` | `record_permanent_block` |

No other terminal kind/reason/purpose tuple is valid.

A block witness authorizes only later recording of the synthetic block. It is
never success, publication, recovery, execution, or worker-order authority.

The exact ordered Action operation domain is:

```text
01 publish
02 acquire_epoch
03 release_epoch
04 abandon_epoch
05 replay_epoch
06 consume_witness
```

Each public operation emits only its same-named Action operation label. The
exact successful/no-change Action rows are:

| operation and condition | outcome | exact one-element `reason_codes` |
|---|---|---|
| publish conflict | `cas_conflict_no_marker` | `expected_state_version_mismatch` |
| publish existing-identical | `cas_existing_identical_no_marker` | `exact_payload_already_current` |
| normal changed publish | `normal_staged_result_exposed_no_marker` | `exact_stage_retained_before_exposing_synthetic_acknowledged_transition` |
| nonnormal changed publish | `synthetic_marker_committed_result_withheld` | `synthetic_marker_committed` |
| publish in any non-`OPEN` state | `publisher_excluded_non_open` | `coordinator_not_open` |
| acquire in `OPEN` | `no_marker_noop` | `marker_absent` |
| acquire in `PUBLISHING` | `publisher_active_excluded` | `owned_publisher_active` |
| acquire in `RECOVERY_PENDING` | `epoch_issued` | `recovery_marker_pending` |
| acquire in `RECOVERY_ACTIVE` | `recovery_active_excluded` | `active_epoch_exists` |
| acquire in recovered live/spent | `recovered_terminal_noop` | `recovered_terminal` |
| acquire in blocked live/spent | `blocked_terminal_noop` | `permanent_block` |
| acquire in `POISONED_NO_MARKER` | `poisoned_no_marker_noop` | `poisoned_no_marker` |
| release ordinal 1..3 | `epoch_released_retry_pending` | `epoch_released_replay_cursor_unchanged` |
| release ordinal 4 | `epoch_release_budget_permanent_block` | `recovery_epoch_budget_exhausted_after_release` |
| abandon ordinal 1..3 | `epoch_abandoned_retry_pending` | `epoch_abandoned_replay_cursor_unchanged` |
| abandon ordinal 4 | `epoch_abandon_budget_permanent_block` | `recovery_epoch_budget_exhausted_after_abandon` |
| release/abandon/replay in `PUBLISHING` | `publisher_active_excluded` | `owned_publisher_active` |
| replay unavailable at ordinal 1..3 | `replay_unavailable_retry_pending` | `same_kernel_replay_unavailable` |
| replay unavailable at ordinal 4 | `replay_unavailable_budget_permanent_block` | `recovery_epoch_budget_exhausted_after_unavailable` |
| replay confirmed intended | `replay_confirmed_recovered` | `synthetic_intended_transition_confirmed` |
| replay confirmed wrong delta | `replay_wrong_delta_permanent_block` | `synthetic_wrong_delta_confirmed` |
| replay exact terminal epoch in recovered live/spent | `recovered_terminal_noop` | `recovered_terminal` |
| replay exact terminal epoch in blocked live/spent | `blocked_terminal_noop` | `permanent_block` |
| consume exact live witness | `witness_consumed` | `witness_consumed` |
| consume exact spent witness again | `witness_already_spent_noop` | `witness_already_spent` |
| consume in `PUBLISHING` after exact outer type check | `publisher_active_excluded` | `owned_publisher_active` |

All other release/abandon/replay/consume lifecycle or identity combinations
are hard errors with no Action and no mutation. There is no catch-all no-op.

For every Action, `marker` is exactly `after_snapshot.marker`.
`publish_result` is nonnull only on the first three publish rows.
`issued_epoch` is nonnull only on `epoch_issued`; `issued_witness` is nonnull
only on a transition into a live terminal. Terminal hash/purpose are nonnull
exactly when the after-snapshot is recovered or blocked. `epoch_ordinal` is
nonnull for an issued epoch, an accepted release/abandon/replay, and terminal
witness consumption; it is null for publish and unrelated no-ops.
`replay_observation` is one of `unavailable`, `confirmed_intended`,
`confirmed_wrong_delta`, or `terminal_noop` only for a replay Action and is
otherwise null. `endpoint_state_changed` is exact equality comparison of the
before and after snapshot digests, not a claim that no transient state or
external filesystem effect occurred.

`after_snapshot` is the state at the operation's Lock-protected linearization
point. Concurrent work may advance the coordinator before the caller receives
the Action, so it is not a post-return current-state attestation.

## 12. Witness validation and single use

At a recovered or blocked transition, the coordinator constructs one witness
object and retains that exact reference. Consumption checks, in order:

1. exact coordinator and witness public types;
2. state has a live or spent witness and the object is the exact retained
   reference by `is`;
3. `expected_purpose` is the exact frozen purpose;
4. `expected_terminal_sha256` is exact uppercase hex64 equal to the retained
   terminal hash.

Wrong purpose/hash, a lookalike, copy, private-constructor bypass, or a witness
from another otherwise hash-identical coordinator is a hard error and does
not consume. The first correct consume changes only live to spent. A second
correct consume of the same exact object is the typed
`witness_already_spent_noop`. No new witness is issued.

The deterministic witness nonce/hash is a forgeable label, not freshness,
randomness, issuer authentication, or authority. Same-instance object
identity plus the private bounded slot is the only acceptance condition.

## 13. Failure precedence and sleep-free concurrency oracle

For every public function, frozen-constant and exact coordinator checks
precede Lock acquisition. Epoch/witness methods also check the outer exact
handle type first. Publish payload/path types are deliberately deferred until
after the lifecycle gate. After acquisition, a `PUBLISHING` lifecycle
exclusion precedes registry identity or state-specific argument checks.
Outside `PUBLISHING`, lifecycle eligibility precedes exact registry identity;
then purpose/hash checks occur. No failed validation mutates state.

Publish on a non-`OPEN` state returns exclusion before validating or touching
its parent, nonce, State, expected hash, proposal, Phase-2b2c, or Phase-2b2d.
Publish on `OPEN` commits `PUBLISHING` before expensive validation so every
ordinary error and `BaseException` exercises the exact rollback rule.

Concurrency tests use `threading.Barrier` and `threading.Event` in a private
monkeypatched Phase-2b2d seam. They use no sleep, clock comparison,
probabilistic race, or production callback. A bounded `Event.wait` or thread
`join` is permitted only as a deadlock guard: expiry fails the test, the first
publisher is then released in `finally`, and no elapsed duration is a semantic
or performance assertion. This makes a mutant that holds the Lock across the
blocked Phase-2b2d seam finitely killable. While the owned call is blocked
outside the Lock the oracle requires:

- snapshot reports `PUBLISHING`;
- a second publisher returns unchanged exclusion and never reaches Phase-2b2d;
- recovery acquire returns unchanged exclusion and issues no epoch;
- after release, the first publisher alone commits its endpoint;
- two simultaneous pending acquires yield exactly one epoch and one exclusion;
- a publisher is excluded while recovery is active; and
- two simultaneous correct witness consumes yield exactly one consume and one
  spent no-op.

## 14. Exact resource and capability boundary

Frozen per-coordinator bounds are:

```text
marker_count_upper_bound = 1
active_epoch_upper_bound = 1
recovery_epoch_upper_bound = 4
witness_count_upper_bound = 1
retained_payload_reference_upper_bound_bytes = 3,145,728
retained_payload_copy_upper_bound_bytes = 0
distinct stored replay Transition upper bound = 2
direct coordinator Phase-2b2c step calls per owned publish = 3
Result-reconstruction nested normal step upper bound = 1
additional Phase-2b2c step total outside the owned Phase-2b2d call = 4
additional coordinator filesystem operations = 0
additional coordinator cleanup/unlink operations = 0
```

The payload-reference bound is the Phase-2b2c maximum of one current payload,
one proposal, and one wrong-delta alternate. Transitions share exact bytes
objects; the coordinator makes no payload copy. Marker/snapshot/action
preimages other than the constructor config are fixed-size. Config hashing
streams at most the one 1,048,576-byte alternate supplied at construction.

Owned publishing has the anchored Phase-2b2d linear payload work, one linear
private State reconstruction, at most three **direct** coordinator calls to
`step_in_memory_fake_cas_v1_0` (one normal classification and two profile
rows), and one linear exact Result reconstruction/validation. That dependency
constructor may internally rederive one additional normal Phase-2b2c
transition. Thus the frozen additional bound outside the owned Phase-2b2d call
is three direct plus one nested step, not three total. Only the at-most-two
profile Transition objects are retained. Recovery, snapshot, marker, epoch,
terminal, witness, and direct Action transcript operations are O(1). The Lock
protects only bounded scalar state work. Production has no sleep, timeout, or
loop over caller data. The test-only bounded deadlock guard is not a production
operation. There is no unbounded
registry, hidden map, journal history, retry loop, random source, or process
global.

The one-file-create and retained-stage-byte bounds remain **per owned
Phase-2b2d call**, not per coordinator lifetime. Repeated `normal` calls with
distinct nonces can accumulate unbounded external residue. Nonnormal marker
commit closes that coordinator to later publishing, but does not own or clean
the stage.

Production performs no unlink. Cleanup is adjudicated as not performed and
unsafe without later artifact/archive binding. Phase 2b2f must bind and classify
residue before any different cleanup proposal; this amendment does not license
one.

## 15. Finite acceptance and adversarial mutation matrix

Before a result commit, the explicit support, frozen four-file M2b profile,
and default collection must pass with zero failures/errors. The frozen profile
has zero skips/xfails. Required families are:

1. exact source imports, ordered production/support `__all__`, one exception,
   three frozen/slotted records with 36/52/33 ordered fields, three factory-only
   live classes, eight positional-only functions, raw/resolved annotations,
   prereg/source/support/result anchor gates, and collector uniqueness;
2. all five profile and alternate type/size/equality boundaries, config/plan
   formulas and goldens, no caller directive/schedule/callback/Result, and no
   entropy-derived alternate;
3. all nine lifecycle snapshots, exact invariant/nullability table, bounds and
   negative labels; constructor and `dataclasses.replace` rejection for every
   inconsistent own scalar/hash/nullability cell, with the explicitly frozen
   exact-type-only nested Phase-2b2d Action boundary;
4. conflict, existing-identical, normal changed, and each nonnormal changed
   publish row; conflict/identical under forbidden physical seams; exact Result
   exposure/withholding and marker count; production rejection of a
   bypass-mutated exact-type seam Result; caller-State reflection/concurrent
   mutation cannot split normal preclassification from the Phase-2b2d State;
   preclassification/Result mismatch poisons if either row is changed; profile
   remains armed only on agreeing no-stage rows;
5. exact marker kind, Phase-2b1 code, publisher/stage/fault/replay-plan binding,
   refusal of `POWER_LOSS` and manifest-error codes, and raw payload equality
   inherited from Phase 2b2c/2b2d;
6. every pre-call validation/Phase-2b2c error and every proven no-stage
   Phase-2b2d error restores `OPEN`; every changed-call error without an exact
   Result and every injected post-changed-Result cut
   before endpoint commit selects `POISONED_NO_MARKER`, withholds Result, and
   maps ordinary exceptions or preserves the exact non-`Exception`
   `BaseException` according to Section 10;
7. the sleep-free publisher/recovery/acquire/consume concurrency oracle,
   bounded deadlock guard,
   exact no-I/O-under-Lock instrumentation;
8. acquire/release/abandon/replay for ordinals 1..4, release/abandon replay
   cursor invariance, fourth-ordinal block, no fifth epoch, every stale/foreign
   handle, and exact terminal replay no-op;
9. every replay row of every profile, including unavailable-then-confirmed and
   unavailable-until-fourth-block, with no Phase-2b2d/stat/hash recomputation
   during replay;
10. recovered/block witness purpose, exact same-instance identity, wrong
    purpose/hash nonconsumption, first consume, second no-op, copy/deepcopy/
    pickle rejection, cross-instance equal-hash rejection, and block witness
    never usable as recovered success;
11. every dynamic digest transcript, nullable tag, tuple order, field mutation,
    omission, domain swap, handle-independence, and the preregistered numeric
    goldens;
12. exact resource arithmetic, three direct plus one nested additional
    Phase-2b2c step, at most two stored replay Transition objects,
    no hidden history, no payload copy, O(1) recovery work, and per-call rather
    than per-coordinator filesystem-residue wording; detectable
    `object.__setattr__` private-state/issuer bypasses fail closed, alongside
    the explicit arbitrary same-process-tampering nonclaim;
13. AST/runtime sentinels forbid secrets/random/time/PID/thread identity,
    caller callbacks, caller Results/markers/codes/directives, filesystem
    imports/calls beyond the exact Phase-2b2d function, unlink/cleanup/fsync,
    manifest/writer, network/Git/Lean/worker/registered-run/later-stage
    capability; and
14. all real filesystem fixtures are test-created under `tmp_path`; no
    repository-tree, `runs/`, exposure-marker, rerun-registry, registered-task,
    network, SSH, Lean, worker, or GPU delta; unchanged default-deny registry;
    Windows zero-skip frozen profile and green Ubuntu CI.

Independent adversarial review must kill these explicit mutants:

- caller-supplied or forged Phase-2b2d Result creates a marker;
- conflict, identical, or pre-call profile error creates a marker or consumes
  the profile; a changed Phase-2b2d error incorrectly restores `OPEN` instead
  of poisoning;
- exact changed Result is exposed before nonnormal marker commit;
- post-changed-success/pre-commit failure restores `OPEN` instead of poison;
- `POWER_LOSS` or a manifest-error code is inferred from a profile label;
- Lock held across Phase-2b2d or payload hash work, or PUBLISHING not visible
  to concurrent coordinator methods;
- caller State reused directly so a reflection mutation can split normal
  preclassification from the owned Phase-2b2d call;
- raw/direct Phase-2b2d or cross-process calls are claimed to be excluded;
- collision nonce reused as epoch identity, or digest/property/equality used
  instead of exact handle identity;
- release/abandon fails to consume an ordinal, advances the replay cursor, or
  permits a fifth epoch;
- unavailable replay at ordinal 4 retries instead of blocking;
- same-kernel replay is relabeled as independent remote confirmation;
- copied/foreign witness consumes, wrong purpose/hash consumes, or second
  correct consume fails rather than no-ops;
- marker/epoch/witness history grows beyond its slots, payload bytes are
  copied, or replay touches the filesystem; and
- a stage is deleted, cleaned, promoted, called durable/current, or used as
  real/canonical publication or recovery authority.

## 16. Stop rule and later ownership

Commit, push, and green hosted CI of this reviewed amendment license only the
exact Phase-2b2e source, support matrix, collector import, and source/support
anchor wiring on local Windows CPU. Until that gate is green, both
implementation paths must remain absent.

A later implementation commit must itself be committed, pushed, and green in
hosted CI. A separate execution record must then freeze the exact Windows
zero-skip profile, implementation blobs, adversarial review disposition, and
Ubuntu CI evidence; its commit must also be pushed and green. Only all of those
conditions complete Phase 2b2e and license **Phase-2b2f preregistration only**.

Phase 2b2f alone may preregister the integrated synthetic manifest writer,
stage/marker/CAS/Phase-2b1-chain binding, artifact/no-follow observations,
conflict-without-marker audit, exact failure-code serialization, residue
classification, and witness-consumption integration. It may not relabel the
Phase-2b2e marker's frozen failure code.

Phase 2c alone owns reservation writing/preflight, fsync and durable-claim
semantics, worker ordering, and any real/canonical publication gate. Phase
2b2f implementation, Phase 2c, registered runs, canonical diagnostic, M2c,
U'0.5, U'2--U'5, SSH/network, Lean, workers, GPU construction, real recovery,
cleanup, and real/canonical publication remain barred in this phase.
