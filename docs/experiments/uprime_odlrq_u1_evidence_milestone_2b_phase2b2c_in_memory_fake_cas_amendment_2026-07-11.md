# U'1 evidence milestone 2b phase 2b2c in-memory fake CAS amendment

Date: 2026-07-11

Status: PREREGISTERED PURE SYNTHETIC VALUE-TRANSITION KERNEL; NO FILESYSTEM,
STORE, REMOTE CAS, CONCURRENCY, STAGING, PUBLICATION, DURABILITY, MARKER,
RECOVERY, WITNESS, MANIFEST, EXECUTION, LEAN, NETWORK, WORKER, CANONICAL-RUN,
RERUN, LATER-STAGE, OR GPU AUTHORITY.

## 1. Purpose, prerequisite, and exact scope

The committed Phase-2b2b result and its green Ubuntu CI license Phase-2b2c
preregistration only. They do not license Phase-2b2c code. This amendment
freezes the smallest next transition model before any implementation begins.

Phase 2b2c is one pure function over one immutable, anonymous, caller-held
cell value. It provides a finite oracle for expected-version conflict, exact
raw-byte identity, acknowledged intended application, two acknowledgement-loss
views, and one synthetic wrong-delta view. It does not provide a mutable
object store, a process-global cell, a key namespace, an operation log, a
publisher, or recovery.

The wrong-delta branch is deliberately not described as a proposal that was
applied and then overwritten. Such a history would require two mutations,
`g -> proposed -> alternate`, plus an intermediate commitment and a causal
model. Those belong to later phases. Here the caller selects a repeatable
synthetic directive under which the proposal is not applied and one distinct
alternate payload is substituted in a single `g -> g+1` transition. The same
function call then labels the actual-versus-intended mismatch. It is not an
acknowledgement-loss-after-apply event, a competing-writer observation, a
crash, a Byzantine attribution, or independent confirmation.

The implementation may run only on local Windows CPU after this amendment is
reviewed, committed, pushed, and green in CI. No SSH, GPU, network, Lean,
worker, registered experiment, canonical diagnostic, or repository artifact
write is part of this phase.

## 2. Exact paths, public surface, and dependency boundary

The later implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_fake_cas_kernel.py
tests/uprime_rpc_fake_cas_kernel_cases.py
```

The support filename is outside pytest's default patterns. At implementation
time it will have an exact `__all__` containing only its
`test_uprime_fake_cas_*` functions and will be imported exactly once by
`tests/test_uprime_rpc_ledger.py`:

```python
from uprime_rpc_fake_cas_kernel_cases import *  # noqa: F403
```

This preregistration commit anchors only this amendment. Before a later result
commit, the amendment, source, support, collector, and execution record must
all be present in `ANCHOR_PATHS` and its independently maintained membership
test. No package initializer or tier-manifest change is required.

The prereg tree has an executable sentinel in
`tests/test_uprime_rerun_license.py`. It requires both future implementation
paths to be absent and the future collector import to occur zero times. The
sentinel may be removed only by an implementation commit whose parent contains
this preregistration commit after its green CI gate. Git ancestry and hosted-CI
conclusion remain externally observed governance facts, not facts proved by
the pure kernel or by a hash commitment.

The source begins with exactly these import statements, apart from blank lines:

```python
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
```

The future import is mandatory, so the exact raw `__annotations__` and
`dataclasses.Field.type` values are frozen strings. Tests may separately
resolve them for semantic comparison. The source may not import another
standard-library or repository module, including the ledger's canonical-JSON
helpers or any prior Phase-2b type. It may not import or dynamically reach
`os`, `pathlib`, `io`, `tempfile`, `shutil`, `subprocess`, `socket`, HTTP,
Git, time, clocks, randomness, UUIDs, async, threads, multiprocessing, Lean,
workers, scanners, archives, registered runs, or formal entrypoints.

The exact ordered production `__all__` is:

```text
InMemoryFakeCasV10Error
InMemoryFakeCasStateV10
InMemoryFakeCasTransitionV10
initial_in_memory_fake_cas_state_v1_0
step_in_memory_fake_cas_v1_0
```

There is one public exception:

```python
class InMemoryFakeCasV10Error(ValueError): ...
```

Every semantically invalid value that reaches a validator, every invalid
reconstructed record, inconsistent commitment, directive error, and generation
exhaustion raises that exception. Python call-shape violations such as missing,
extra, or keyword-supplied positional-only arguments remain `TypeError`. No
error becomes a seventh transition outcome.

The two public functions have exactly these signatures. Every step argument
is positional-only, with no defaults, variadic arguments, or keyword
acceptance:

```python
def initial_in_memory_fake_cas_state_v1_0() -> InMemoryFakeCasStateV10: ...

def step_in_memory_fake_cas_v1_0(
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    synthetic_directive: str,
    alternate_payload: bytes | None,
    /,
) -> InMemoryFakeCasTransitionV10: ...
```

The initializer always returns the one absent generation-zero state. There is
no initializer argument, store identifier, key, nonce, epoch, request token,
operation identity, or hidden registry.

## 3. Exact public records and fixed negative labels

Both records use `@dataclass(frozen=True, slots=True)`. Their normal public
constructors are validating constructors; there is no bypass constructor.
Subclasses of either record are rejected at every API boundary.

“Smallest” in this amendment means the dynamic state machine: one cell, two
records, two functions, and six outcomes. It does not mean the fewest reflected
fields. Fixed resource and negative-authority disclosures remain first-class
validated fields so that a detached record carries its scope instead of
depending on a class attribute or surrounding prose.

`InMemoryFakeCasStateV10` has exactly these 26 fields in this order:

```text
state_schema_version: str
state_scope: str
origin_status: str
generation: int
cell_state: str
cell_payload: bytes | None
cell_payload_bytes: int | None
cell_payload_sha256: str | None
state_version_sha256: str
payload_byte_limit: int
generation_upper_bound: int
version_scope: str
raw_equality_scope: str
state_provenance: str
lineage_enforcement: str
fork_handling: str
deletion_support: str
persistence_scope: str
concurrency_scope: str
remote_cas_authentication: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

Its constant fields are exactly:

```text
state_schema_version = lean-rgc-uprime-u1-in-memory-fake-cas-state-v1.0
state_scope = one_anonymous_in_memory_value_cell
origin_status = unknown_may_be_synthetic
payload_byte_limit = 1048576
generation_upper_bound = 9223372036854775807
version_scope = comparison_value_not_capability
raw_equality_scope = exact_bytes_not_digest_only
state_provenance = unauthenticated_forgeable_value_object
lineage_enforcement = caller_must_thread_returned_state_not_enforced
fork_handling = forks_allowed_no_global_linearity
deletion_support = unsupported_proposals_are_exact_bytes
persistence_scope = none_process_memory_only
concurrency_scope = none_pure_single_call_transition
remote_cas_authentication = not_performed
authority_scope = none
canonical_remote_authority = false
licenses_execution = false
licenses_publication = false
licenses_recovery = false
licenses_later_stage = false
```

`InMemoryFakeCasTransitionV10` has exactly these 66 fields in this order:

```text
transition_schema_version: str
transition_scope: str
origin_status: str
before_state: InMemoryFakeCasStateV10
after_state: InMemoryFakeCasStateV10
expected_state_version_sha256: str
proposed_payload: bytes
proposed_payload_bytes: int
proposed_payload_sha256: str
synthetic_directive: str
alternate_payload: bytes | None
alternate_payload_bytes: int | None
alternate_payload_sha256: str | None
input_sha256: str
outcome: str
reason_codes: tuple[str, ...]
expected_version_match: bool
proposed_equal_before: bool | None
directive_reached: bool
alternate_semantics_checked: bool
state_changed: bool
cell_mutation_count: int
intended_apply_status: str
intended_after_state_version_sha256: str | None
intended_delta_sha256: str | None
actual_delta_sha256: str | None
transition_sha256: str
effect_scope: str
synthetic_acknowledgement_label: str
same_kernel_confirmation_label: str
synthetic_client_observation: str
model_latent_effect: str
payload_byte_limit: int
generation_upper_bound: int
unique_retained_payload_reference_upper_bound_bytes: int
retained_payload_copy_upper_bound_bytes: int
state_hash_preimage_upper_bound_bytes: int
input_hash_preimage_upper_bound_bytes: int
delta_hash_preimage_upper_bound_bytes: int
transition_hash_preimage_upper_bound_bytes: int
hash_preimage_construction: str
directive_origin: str
outcome_selection: str
confirmation_scope: str
cause_scope: str
application_attribution: str
state_provenance: str
lineage_enforcement: str
fork_handling: str
idempotence_scope: str
exactly_once_scope: str
persistence_scope: str
concurrency_scope: str
filesystem_staging: str
remote_publication: str
durability_scope: str
marker_scope: str
recovery_scope: str
witness_scope: str
manifest_scope: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

Its fixed non-outcome fields are exactly:

```text
transition_schema_version = lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1.0
transition_scope = pure_single_call_one_cell_cas_derivation
origin_status = unknown_may_be_synthetic
payload_byte_limit = 1048576
generation_upper_bound = 9223372036854775807
unique_retained_payload_reference_upper_bound_bytes = 3145728
retained_payload_copy_upper_bound_bytes = 0
state_hash_preimage_upper_bound_bytes = 1048640
input_hash_preimage_upper_bound_bytes = 2097249
delta_hash_preimage_upper_bound_bytes = 1048695
transition_hash_preimage_upper_bound_bytes = 467
hash_preimage_construction = payloads_streamed_no_full_preimage_materialization
directive_origin = caller_supplied_repeatable_synthetic_choice
outcome_selection = input_validation_then_conflict_then_exact_identity_then_directive
confirmation_scope = same_call_same_kernel_not_independent
cause_scope = not_modeled_no_causal_fault_claim
application_attribution = not_authenticated
state_provenance = unauthenticated_forgeable_value_object
lineage_enforcement = caller_must_thread_returned_state_not_enforced
fork_handling = forks_allowed_no_global_linearity
idempotence_scope = not_provided_no_operation_identity
exactly_once_scope = not_provided
persistence_scope = none_process_memory_only
concurrency_scope = none_pure_single_call_transition
filesystem_staging = not_performed
remote_publication = not_performed
durability_scope = not_observed
marker_scope = not_created_or_observed
recovery_scope = not_performed
witness_scope = not_issued_or_verified
manifest_scope = not_read_or_written
authority_scope = none
canonical_remote_authority = false
licenses_execution = false
licenses_publication = false
licenses_recovery = false
licenses_later_stage = false
```

Every listed string has exact type `str`; every integer has exact type `int`
with booleans rejected; every flag has exact type `bool` and the listed false
value. Hash fields are exact uppercase ASCII `[0-9A-F]{64}` or exact `None`
where nullable. Payloads are exact `bytes`, never `bytearray`, `memoryview`, or
a subclass.

## 4. State space, absence, equality, and lineage

The only valid absent state is:

```text
generation = 0
cell_state = absent
cell_payload = None
cell_payload_bytes = None
cell_payload_sha256 = None
```

Every valid present state has:

```text
1 <= generation <= 9223372036854775807
cell_state = present
cell_payload = exact bytes of length 0..1048576
cell_payload_bytes = len(cell_payload)
cell_payload_sha256 = uppercase SHA256(cell_payload)
```

Thus absent `None` and present empty `b""` are distinct. An absent state with a
nonzero generation, a present state at generation zero, a partially null
payload triple, or a mismatched raw hash/count is invalid. Deletion is not an
operation because every proposal is exact bytes.

Outcome selection compares raw bytes, not hashes. Hashes are computational
commitments under the ordinary collision-resistance assumption; they are not
mathematical equality proofs, capabilities, signatures, instance identities,
or origin authentication.

The source has one exact private mutation-test seam:

```python
def _raw_payload_sha256(payload: bytes, /) -> str: ...
```

In production it returns uppercase SHA-256 of the exact payload. It is used
only to populate and revalidate `cell_payload_sha256`,
`proposed_payload_sha256`, and `alternate_payload_sha256`. It is not used by
the raw-identity branch or by STATE, INPUT, DELTA, or TRANSITION framing. The
support oracle monkeypatches this helper to return one frozen digest for two
or three distinct exact payloads while leaving raw-framed commitments intact.
Current A/proposal B under an intended directive must remain changed; current
A/proposal B/alternate C under the alternate directive must remain a valid
wrong-delta transition. These executable discriminators kill digest-only
identity and alternate-distinctness mutants without claiming or requiring a
real SHA-256 collision. The seam is private test instrumentation, not a public
dependency injection API. Records produced while the helper is monkeypatched
are mutation-oracle fixtures, are discarded inside that test, and are not
production-valid hash evidence. Separate unpatched tests enforce every raw SHA
and commitment golden.

The state object is public and forgeable. Any caller can construct another
valid value or reuse an old value. The kernel is pure and does not consume a
state. Two calls from the same `before_state` can both return successful but
divergent forks. The caller must explicitly thread the returned `after_state`;
the implementation cannot enforce global linearity. Equal values produced by
independent initializations have equal versions and are portable across those
caller-created contexts. There is intentionally no store or instance binding.

Generation prevents raw-value ABA only along a caller-threaded lineage. For
example, `A@g1 -> B@g2 -> A@g3` has three distinct state versions even though
the first and last raw payloads agree. Reusing the old `A@g1` object remains
possible and is not detected until a caller compares it against a newer
expected state value.

## 5. Exact validation and transition precedence

Each public function and each public constructor first revalidates the frozen
resource constants and their arithmetic formulas. The step then applies this
exact order:

1. require `state` to have exact public State type and reconstruct a fresh
   validated snapshot through the normal State constructor, retaining the same
   exact immutable payload object but not the caller's State object;
2. validate exact types, enums, nullability, uppercase expected hash, and all
   payload byte bounds;
3. if the expected hash differs from `snapshot.state_version_sha256`, return
   `conflict_no_change` without evaluating raw equality or directive semantics;
4. if expected matches and the snapshot is present with payload exactly
   equal to the proposal, return `existing_identical_no_change` without
   evaluating directive semantics;
5. only for the alternate directive after steps 3 and 4, require the alternate
   payload to differ exactly from the proposal and, for a present current
   state, from the current payload;
6. if a changed transition would increment the maximum generation, raise
   `InMemoryFakeCasV10Error` and return no Transition; and
7. derive the directive-specific changed transition.

The alternate field's structural contract is still checked at step 2. It must
be exact `None` for the first three directives and exact bounded `bytes` for
the fourth. Only its relational distinctness is deferred. Consequently stale
expected version dominates all four syntactically valid directives, including
an alternate equal to the proposal. Exact current payload similarly dominates
the fourth directive before relational validation. This prevents a caller's
chosen fault directive from selectively relabeling a conflict or no-op.

At maximum generation a stale expected value still returns conflict and an
exact-current proposal still returns the existing-identical no-op. A matched,
different, relationally valid changed request raises the public error. A
transition from maximum-minus-one to maximum succeeds. Generation never wraps.

Every successful step has `transition.before_state is not state` and
`transition.before_state == state` at return. For a present state, the fresh
snapshot retains `transition.before_state.cell_payload is
state.cell_payload`. All derivation uses the snapshot. A later bypass mutation
of the caller's original State object therefore cannot mutate the nested
before/after State stored by the returned Transition. This snapshotting is not
persistence, instance identity, or a global linearity mechanism.

## 6. Exact directives and six-outcome matrix

The exact directives, in tag order, are:

```text
01  apply_intended_acknowledge
02  apply_intended_lose_ack_then_confirm
03  apply_intended_lose_ack_confirmation_unavailable
04  substitute_alternate_then_confirm_wrong_delta
```

The exact outcomes, in tag order, are:

```text
01  conflict_no_change
02  existing_identical_no_change
03  intended_applied_acknowledged
04  intended_applied_ack_lost_confirmed
05  intended_applied_ack_lost_unconfirmed
06  wrong_delta_confirmed
```

Every `reason_codes` value is an exact one-element tuple. The complete outcome
matrix is:

In order, the table's last six semantic columns populate
`intended_apply_status`, `effect_scope`,
`synthetic_acknowledgement_label`, `same_kernel_confirmation_label`,
`synthetic_client_observation`, and `model_latent_effect`.

| outcome | reason code | intended apply | effect | synthetic ack | same-kernel confirmation | synthetic client observation | model latent effect |
|---|---|---|---|---|---|---|---|
| `conflict_no_change` | `expected_state_version_mismatch` | `not_attempted` | `no_change` | `not_attempted` | `not_attempted` | `conflict` | `unchanged` |
| `existing_identical_no_change` | `exact_payload_already_current` | `not_attempted_existing_identical` | `no_change_existing_identical` | `not_attempted` | `not_attempted` | `existing_identical` | `unchanged_existing_identical` |
| `intended_applied_acknowledged` | `matched_intended_apply_acknowledged` | `applied` | `intended_applied` | `delivered` | `not_attempted` | `applied` | `intended_applied` |
| `intended_applied_ack_lost_confirmed` | `matched_intended_apply_ack_lost_confirmed` | `applied` | `intended_applied` | `lost` | `same_kernel_observed_intended` | `applied_after_same_kernel_confirmation` | `intended_applied` |
| `intended_applied_ack_lost_unconfirmed` | `matched_intended_apply_ack_lost_confirmation_unavailable` | `applied` | `intended_applied` | `lost` | `unavailable` | `ambiguous` | `intended_applied` |
| `wrong_delta_confirmed` | `matched_alternate_substitution_confirmed_wrong_delta` | `not_applied_alternate_substituted` | `alternate_applied` | `not_applicable_intended_not_applied` | `same_kernel_observed_wrong_delta` | `wrong_delta` | `alternate_applied` |

The derived control fields are exactly:

| outcome | expected match | proposed equal before | directive reached | alternate semantics checked | changed | mutations |
|---|---:|---:|---:|---:|---:|---:|
| conflict | false | `None` | false | false | false | 0 |
| existing identical | true | true | false | false | false | 0 |
| acknowledged | true | false | true | false | true | 1 |
| ack lost, confirmed | true | false | true | false | true | 1 |
| ack lost, unconfirmed | true | false | true | false | true | 1 |
| wrong delta | true | false | true | true | true | 1 |

Conflict and existing-identical have `after_state == before_state` and all
three intended/actual commitment fields are `None`; the returned Transition
also retains the exact same State object as both `before_state` and
`after_state`. Every changed branch has an intended candidate at `g+1`
containing the proposal. The acknowledged, confirmed, and unconfirmed
intended branches have value-identical after states, intended deltas, and
actual deltas, and the after-state payload is the exact same bytes object as
`proposed_payload`. In particular, confirmation unavailability does not roll
back the oracle's latent changed state.

For wrong delta, the intended candidate and intended delta contain the
proposal, while the actual after state and actual delta contain the distinct
alternate. The proposal was not applied. The acknowledgement field is
therefore not applicable rather than lost. The actual after-state payload is
the exact same bytes object as `alternate_payload`.

The `synthetic_client_observation` labels are deterministic cells in this
synthetic matrix, not observations from an independent client or transport.
The public Transition is an oracle-side record that intentionally exposes both
`model_latent_effect` and the synthetic client label; it is not an
information-hiding client response type. The schema names keep acknowledgement,
confirmation, client, and latent-effect values from presenting as independently
observed events when fields are consumed out of context.

## 7. Exact hash framing and formulas

Let `H(x)` be uppercase hexadecimal SHA-256, `U16(n)` and `U64(n)` unsigned
big-endian integers, and `R(h)` the 32 raw bytes decoded from an exact uppercase
64-hex hash. Let:

```text
P(b)       = U64(len(b)) || b
O(None)    = 00
O(bytes b) = 01 || P(b)
Q(None)    = 00
Q(hash h)  = 01 || R(h)
K(s)       = U16(len(ASCII(s))) || ASCII(s)
```

Lengths are byte lengths. Every listed string is frozen ASCII. U16/U64 reject
booleans, negatives, and overflow. The exact domains and lengths are:

```text
D_STATE      = b"lean-rgc-uprime-u1-in-memory-fake-cas-state-v1\0"       # 47
D_INPUT      = b"lean-rgc-uprime-u1-in-memory-fake-cas-input-v1\0"       # 47
D_DELTA      = b"lean-rgc-uprime-u1-in-memory-fake-cas-delta-v1\0"       # 47
D_TRANSITION = b"lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1\0"  # 52
```

The state commitment is:

```text
STATE(g, payload_or_none) =
  H(D_STATE || U64(g) || O(payload_or_none))
```

The raw payload SHA field is separately `H(payload)`. Raw bytes, not that
field, are framed into STATE.

With the one-byte directive tag from Section 6:

```text
INPUT = H(
  D_INPUT ||
  R(expected_state_version_sha256) ||
  P(proposed_payload) ||
  directive_tag ||
  O(alternate_payload)
)
```

For any changed candidate:

```text
DELTA(before_version, after_version, applied_payload) = H(
  D_DELTA ||
  R(before_version) ||
  R(after_version) ||
  P(applied_payload)
)
```

For all four changed directives, `intended_after_state_version_sha256` is
`STATE(g+1, proposed_payload)` and `intended_delta_sha256` uses that state and
the proposal. For outcomes 3--5, actual equals intended. For outcome 6,
`actual_delta_sha256` uses `STATE(g+1, alternate_payload)` and the alternate.
For outcomes 1--2, intended-after and both deltas are `None`.

Let the seven strings `reason`, `intended`, `effect`, `ack`, `confirmation`,
`client`, and `latent` be the exact row entries in Section 6. Then:

```text
TRANSITION = H(
  D_TRANSITION ||
  R(INPUT) ||
  outcome_tag ||
  R(before_state.state_version_sha256) ||
  Q(intended_after_state_version_sha256) ||
  Q(intended_delta_sha256) ||
  Q(actual_delta_sha256) ||
  R(after_state.state_version_sha256) ||
  U64(cell_mutation_count) ||
  K(reason) ||
  K(intended) ||
  K(effect) ||
  K(ack) ||
  K(confirmation) ||
  K(client) ||
  K(latent)
)
```

The input commitment binds expected version, proposal, directive, and tagged
alternate even when conflict or identity prevents the directive from being
reached. The transition commitment is acyclic and binds the selected outcome,
before/after versions, nullable intended/actual commitments, mutation count,
and all outcome-specific semantic labels. Constructor validation derives all
remaining redundant fields exactly.

## 8. Frozen independent golden vectors

Define:

```text
A = bytes.fromhex("11" repeated 32 times)
B = bytes.fromhex("22" repeated 32 times)
C = bytes.fromhex("33" repeated 32 times)
```

Their raw SHA-256 values, preceded by present empty, are:

```text
H(empty) = E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
H(A)     = 02D449A31FBB267C8F352E9968A79E3E5FC95C1BBEAA502FD6454EBDE5A4BEDC
H(B)     = 9F72EA0CF49536E3C66C787F705186DF9A4378083753AE9536D65B3AD7FCDDC4
H(C)     = DEB0E38CED1E41DE6F92E70E80C418D2D356AFAAA99E26F5939DBC7D3EF4772A
```

The frozen state versions are:

| state | version |
|---|---|
| absent generation 0 | `D475431F78A252741905BD00E75E0E97A30326A91046BF9D4A827D4713BAEBB8` |
| present empty generation 1 | `BD7CC4F2F5267D91A15B465E390A1EFBD9227000A6588E90293A1E2376902A81` |
| A generation 1 | `ECD95866ABC3D55C1D204027E08BC57FB9ED65836A7996C10F51D1D723240652` |
| B generation 2 | `6B82D8C7DDAD4FA3E1A6618168EE4D37E1662B79CDB4C7A12189376FDCAC7F90` |
| C generation 2 | `1CC27CD54D0062C61AB62D0F238382D9ECF965BC624D7E8347FEC995EB5AA674` |
| A generation 3 | `77DF0F942B14680DBA5459666F99B5C6D0B37FC0648F9C2B47A9839F5315E5A0` |

The frozen changed deltas are:

```text
A@g1 -> B@g2 using B:
C9721CC95913641245C355752E2DCD70541926FADC02681BEF26920E11FD23C6

A@g1 -> C@g2 using C:
5FA97222CD85C7DCA8284AEE6314270822D45681EC32AA39094E10B8CB857B23

absent@g0 -> empty@g1 using empty:
20AD941541E39F3946D29013EFCA76B3A4BB928CB028A9AA254F60BAE1A39B76
```

The exact cases and their INPUT/TRANSITION commitments are:

| case | before / expected / proposal / directive / alternate | INPUT | TRANSITION |
|---|---|---|---|
| conflict | A@g1 / absent@g0 / B / 01 / None | `9961EFA8D1D509BF324B2C5AA9D56C664F4807B207E620332B39D06A280CFAA7` | `60D25236487695725CF5C6AAE03B8BD5426085D3B6A89DB8527843E79E3C4F3F` |
| existing precedence | A@g1 / A@g1 / A / 04 / A | `FAD02517161804E7DA055790547EA5459D8478E0AD9981F31847EBF603AC5E22` | `914C8A1F12A857E5B9ECD7ED18D3B929D0C3909CC6C794C155D5CD73E570CDA4` |
| acknowledged | A@g1 / A@g1 / B / 01 / None | `19A5C288B0BC9F9A6D363EB59260B1107345FCFFE0FA6E0CF461ADC1244F2CEF` | `029C6ECD6148EDC6736727E780DE474C7D760B63E650EA22744800547208C44C` |
| ack lost confirmed | A@g1 / A@g1 / B / 02 / None | `070021A460A0B3CE68FEA0992D70D2CCCA82A93389692B99A5C8A3119273FD02` | `AC63C584E6A0B0D852A277D7D27D529DE9A8D1699794C1FA5673ED6510A3409A` |
| ack lost unavailable | A@g1 / A@g1 / B / 03 / None | `81B5BFC1C59CA065AB32B9B8F9453A55338C70E646923C1C90D36A3CE5133BC0` | `48157FF56B4FA39161653C29F748878AABA96718EEA19698469397FA92619766` |
| wrong delta | A@g1 / A@g1 / B / 04 / C | `BC14DF5E4C800160838A55C401816DFDEC1618BA4C29D5008FC2D7E9CC06FC04` | `3D383A27D9410D3605CFDC5E0635A349CB9DF0D5AB159E1846DEE33E8B7BCAA0` |
| absent to empty acknowledged | absent@g0 / absent@g0 / empty / 01 / None | `585819082B18EAEA705AC995E9D8EADFC7333E7012096227D9AA3FFDF9A1378E` | `194FC9297D81669BDE36952C414D47F013FD0DBF4A51DA175B2649447DEE1AAF` |

The existing-precedence vector intentionally supplies alternate `A`, which
would violate distinctness if the directive were reached. Exact current raw
identity prevents that semantic check by the frozen precedence.

## 9. Resource and computation contract

The exact bounds are:

```text
MAX_PAYLOAD_BYTES = 1048576
MAX_GENERATION = 9223372036854775807
MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES = 3 * MAX_PAYLOAD_BYTES = 3145728
MAX_RETAINED_PAYLOAD_COPY_BYTES = 0
```

The unique reference bound counts at most one prior payload, one proposal, and
one alternate. The after state reuses the exact proposal or alternate object;
hashing and reconstruction must not retain another payload copy. This is not a
claim about transient internal block buffering inside the SHA-256 library or
the caller's own aliases.

Production hashing must feed fixed framing and payload objects incrementally
to SHA-256. It must not concatenate or materialize a full state, input, or
delta or transition preimage and must not encode payloads as hex, Base64,
JSON, text, lists, or integer arrays. Apart from public records and retained
payload references, the module may allocate fixed-size framing bytes, scalar
and control tuples, private fixed-size derivation results, regex match objects,
hash objects and their internal buffers, and exception objects. It may not
allocate or retain another object whose size is proportional to a payload.

The exact inclusive preimage upper bounds are independently recomputed before
input hashing:

```text
STATE:      47 + 8 + 1 + 8 + MAX_PAYLOAD_BYTES = 1048640
INPUT:      47 + 32 + (8 + MAX_PAYLOAD_BYTES) + 1
            + (1 + 8 + MAX_PAYLOAD_BYTES) = 2097249
DELTA:      47 + 32 + 32 + 8 + MAX_PAYLOAD_BYTES = 1048695
TRANSITION: maximum exact Section-7 row = 467
```

For the frozen matrix the exact transition preimage lengths are 270, 335,
373, 421, 389, and 467 bytes in outcome-tag order. An absent state preimage is
56 bytes, present empty is 64 bytes, and a 32-byte present payload is 96 bytes.

No retry, sleep, timeout, clock, random choice, callback, hidden state, memo,
deduplication table, or process-global mutation is permitted. Runtime is
linear in the total supplied payload bytes; fixed record validation is
constant outside hash feeds and raw equality comparisons.

## 10. Constructor revalidation and purity oracle

The State constructor recomputes its payload count, raw SHA, state version,
resource fields, and every fixed negative field. It rejects any mismatch.

The Transition constructor first requires exact State types for both states
and reconstructs both through the normal State constructor. It then invokes a
private, side-effect-free derivation primitive on the retained before state and
the five retained step inputs. That primitive returns the expected candidate
state and scalars. The constructor compares every one of its 66 fields to the
derived value and rejects any mismatch.

The private primitive must not call either public function. The public step
uses the same primitive and then invokes the normal Transition constructor.
This keeps validation acyclic. `dataclasses.replace`, ordinary construction,
subclassing, and an API input whose frozen record was mutated through a bypass
must not forge an outcome, after state, generation, reason, status, hash,
resource label, negative label, or authority flag.

Transition validation additionally enforces object retention: a no-change
transition has `after_state is before_state`; an intended changed transition
has `after_state.cell_payload is proposed_payload`; and a wrong-delta
transition has `after_state.cell_payload is alternate_payload`. Value equality
alone is insufficient for these retention checks. These identities are not
store identity, request identity, or authority; they only make the frozen
retained-reference bound true.

There is no separate request, token, confirmation, apply, get, put, retry,
store, map, history, deduplication, marker, recovery, or witness API. Private
names may support validation and framing only; they may not expose any of
those deferred concepts.

## 11. Threat model and nonclaims

This kernel can establish only consistency between exact caller-supplied
values and the frozen finite derivation table. It cannot establish that an
event happened, that a response was transported or lost, that another actor
exists, that an alternate has a cause, or that any result persists after the
Python objects are discarded.

In particular it provides no:

- authenticated store, namespace, state origin, writer, request, or operation;
- global CAS linearizability, atomicity between processes, mutual exclusion,
  retry safety, idempotence, or exactly-once behavior;
- filesystem path, staged byte, nonce separation, rename/link, fsync,
  publication, remote-ref, or durability fact;
- marker causality, conflict-without-marker distinction, crash/power-loss
  injection, epoch lifecycle, recovery, replay, or witness;
- manifest, artifact, claim receipt, ledger, report, canonical run, or
  registered-experiment binding; or
- execution, safety, model-quality, Lean, network, SSH, GPU, or later-phase
  authority.

The three intended directives use synthetic ack labels. The fourth directive
uses a synthetic substitution label. All are caller-selected and repeatable;
none is sampled from an environment. Same-kernel confirmation is a same-call
self-check of values produced by the same derivation, not independent evidence.

## 12. Finite Phase-2b2c acceptance matrix

Before a result commit, the explicit support, frozen four-file M2b profile,
and default collection must pass with zero failures/errors. The frozen profile
has zero skips/xfails. Required finite families are:

1. exact module imports, ordered production/support `__all__`, one exception,
   two records, two public functions, annotations, positional-only signatures,
   frozen/slots field tuples of exactly 26 and 66, collector uniqueness, and
   prereg/source/support/result anchors; prereg-tree absence of both future
   implementation paths and zero future collector imports;
2. initial absent state and every State field; present empty; known raw hashes,
   domain bytes/lengths, framing, state versions, and independent goldens;
   invalid absent/present generation/payload/count/hash/version combinations;
3. exact type rejection for every State, expected hash, proposal, directive,
   alternate, tuple, integer, nullable, and flag field; bool-as-int,
   subclasses, bytearray/memoryview, lowercase/mixed hash, and every inclusive
   N-1/N/N+1 payload/generation boundary; stale expected plus one structural
   invalid from each State/expected-hash/proposal/directive/alternate class
   still raises the public error rather than conflict, and exact-current
   proposal plus invalid directive or alternate structure still raises rather
   than no-op;
4. all six outcomes and all status/control cells; conflict for every one of
   the four structurally valid directives; stale plus exact-current remains
   conflict; exact-current for all four directives remains existing-identical;
   absent plus empty is changed, never identical;
5. the alternate relational rule only after conflict and identity; matched
   changed alternate equal proposal or present current rejects; distinct
   alternate succeeds; non-alternate requires exact `None`; no selective
   relabeling by a caller-selected directive;
6. acknowledged, ack-lost-confirmed, and ack-lost-unconfirmed produce
   value-identical after State/intended/actual deltas; unconfirmed retains the
   changed model-latent state while synthetic client observation remains
   ambiguous; wrong delta uses exactly one mutation to the alternate and
   records proposal-not-applied semantics; no-change and changed after-state
   object/payload identity obeys the exact retained-reference rules;
7. maximum generation stale conflict, maximum generation exact-identical
   no-op, maximum-minus-one changed success to maximum, maximum changed public
   error with no Transition and unchanged input, and no wrap or seventh
   outcome;
8. every INPUT/DELTA/TRANSITION formula, tag, nullable framing, status-string
   order, preimage length, and frozen golden; mutation or omission of expected,
   proposal, directive, alternate, generation, before/after, outcome, status,
   or delta changes or invalidates the corresponding commitment;
9. raw-byte outcome comparison rather than digest-only comparison; None versus
   empty; the exact private raw-SHA seam forced to one digest for distinct
   A/B/C while intended A-to-B remains changed and alternate A/B/C remains
   valid wrong-delta, plus AST assertions and exact digest-only mutants for
   both identity and alternate relational comparisons that must fail; ABA
   `A@g1 -> B@g2 -> A@g3`; old expected conflicts against the threaded newer
   state despite equal raw A; different same-generation raw forks have distinct
   state commitments under the stated hash assumption;
10. two calls from one before state can both succeed as forks; cross-applying
    an expected version from one fork to the other conflicts; equal independent
    initial values share versions; no hidden instance/nonce/linearity claim;
11. normal construction and `dataclasses.replace` reject every forged State or
    Transition field; bypass-mutated State input rejects; before/after exact
    type and reconstruction; step retains a fresh value-equal before snapshot
    with the same immutable payload object, caller-State bypass mutation after
    return cannot alter it, private derivation is acyclic, and public step is
    not called by Transition validation;
12. exact resource arithmetic, monkeypatched-invalid constants rejected before
    semantic classification, incremental hash feeds, exact retained reference
    bound, no retained payload copy, no full preimage materialization, and
    runtime linear in supplied payload bytes;
13. AST/runtime sentinels forbid repository imports, filesystem, map/store,
    operation history, callback, retry, sleep, clock, random, concurrency,
    network, Git, Lean, worker, scanner, writer, publication, marker, epoch,
    recovery, witness, manifest, and registered-run capabilities; and
14. no repository-tree, `runs/`, or exposure-marker delta; unchanged literal/
    SHA/Git-blob default-deny registry; Windows zero-skip frozen profile and
    green Ubuntu CI.

All examples are in-memory exact bytes. Tests may use deterministic generated
bytes but may not write a filesystem fixture, contact a service, start a
thread/process, invoke Lean, or consume a registered task.

## 13. Stop rule

Commit, push, and green CI of this reviewed amendment license only the exact
Phase-2b2c source, support matrix, collector import, and source/support anchor
wiring on local Windows CPU. Until that gate is green, no Phase-2b2c source or
support code may begin.

A later committed and pushed execution record with the frozen zero-skip
Windows profile and green Ubuntu CI completes Phase 2b2c and licenses only
Phase 2b2d preregistration for nonce-separated local staging and a normal fake
publisher.

Filesystem staging, actual artifact writing, a mutable/global fake store,
marker/recovery, epoch or witness issuance, integrated manifest writing, real
claim/publication, network/SSH, Lean, worker execution, GPU construction,
Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5 remain barred.
