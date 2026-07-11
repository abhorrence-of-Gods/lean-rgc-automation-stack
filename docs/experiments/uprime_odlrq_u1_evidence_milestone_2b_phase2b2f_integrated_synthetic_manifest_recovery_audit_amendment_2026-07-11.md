# U'1 evidence milestone 2b phase 2b2f amendment: integrated synthetic manifest/recovery audit

Date: 2026-07-11

Status: PREREGISTRATION ONLY. NO PHASE-2B2F SOURCE OR SUPPORT MAY EXIST AT
THIS COMMIT. SAME-PROCESS SEQUENTIAL SYNTHETIC INTEGRATION AND NEGATIVE
AUTHORITY ONLY. THE PHASE-2B1 EVENT DOES NOT PERSIST STAGE, MARKER, CAS,
TERMINAL-KIND, OR WITNESS BINDINGS. NO REAL RECOVERY, DURABILITY, CLEANUP,
PUBLICATION, EXECUTION, LEAN, NETWORK, WORKER, REGISTERED RUN, RERUN,
LATER-STAGE, OR GPU AUTHORITY.

## 1. Gate, adversarial reduction, and exact claim

Phase 2b2e completed only after its preregistration, implementation, and
separate result commits were each pushed and green. The gate-bearing result
commit is `d838d8c4873e04bc649b8551f0545af5d9944c4c`; its result record is Git blob
`ab2c417949a2da637508cc8faa8891e452bfef77`. Hosted CI run `29147513348`, job
`86531480025`, completed successfully at that exact head with runtime boundary
12 modules / 234 files, dead-candidate ledger 8 modules, and 2,188 passed,
4 skipped, 163 deselected in 78.28 seconds. That gate licenses this
preregistration and nothing more.

The first Phase-2b2f design was rejected. The exact Phase-2b1 29-field event
has no cell for a stage path, publisher operation, CAS transition, marker,
terminal kind/reason, witness purpose, or witness consumption. Every
Phase-2b2e marker profile also carries the same Phase-2b1 failure tuple
`("OTHER_HARNESS_ERROR",)`. Therefore a later chain-only reader cannot recover
or authenticate the proposed cross-binding, distinguish recovered from
permanent-block terminality, or prove that a witness was ever consumed.

This amendment adopts the smallest surviving claim:

- one caller-supplied strict canonical seed containing exactly one structural
  public receipt;
- one pre-existing exact one-event `claim_started` Phase-2b1 chain;
- one internally constructed `absent@g0` Phase-2b2c State;
- one internally owned Phase-2b2e coordinator and at most one owned publish;
- four nonnormal synthetic profiles only;
- one fixed acquire/replay driver with no release or abandonment;
- one terminal `recovery` event at index 2, whose failure tuple is copied
  exactly from the live marker;
- one separate conflict-without-marker audit which writes no manifest; and
- deterministic, forgeable returned projection hashes which bind values only
  inside the same live call.

No sidecar is introduced. No Phase-2b1 schema is changed. In particular:

```text
cross_binding_scope =
  same_call_returned_value_only_not_serialized_in_phase2b1_event

binding_persistence_scope =
  none_detached_audit_and_hashes_are_forgeable

manifest_witness_atomicity =
  not_provided_two_ordered_endpoints
```

A persistent cross-binding would require a separately preregistered sidecar or
Phase-2b1 schema amendment. It is outside this phase.

## 2. New paths, absence sentinel, collection, and imports

The preregistration path is:

```text
docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_integrated_synthetic_manifest_recovery_audit_amendment_2026-07-11.md
```

The only licensed future implementation paths are:

```text
lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py
tests/uprime_rpc_integrated_synthetic_manifest_cases.py
```

Both future paths must be absent at this preregistration commit. The collector
must contain zero occurrences of:

```python
from uprime_rpc_integrated_synthetic_manifest_cases import *  # noqa: F403
```

This amendment is added to the litmus anchor and anchor-membership test. No
result path is added. Its reserved later path is exactly:

```text
docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_execution_2026-07-11.md
```

That path must also be absent at this preregistration commit. The default-deny
rerun registry, package initializers, tier manifest, every `runs/` path, and
every exposure record remain unchanged.

The future source may import only `dataclasses`, `hashlib`, `os`, `re`, `stat`,
the public Phase-2b1 attempt-manifest API, Phase-2b2a seed/inventory API,
Phase-2b2b artifact observer, Phase-2b2c State/Transition constructors, the
Phase-2b2d public Result constructor for value validation only, and the
Phase-2b2e coordinator API. It may not import or call the Phase-2b2d publisher
function directly. It may not import private
dependency names, subprocess, socket, HTTP, Git, Lean, worker, rerun, registry,
production-litmus, scanner/archive, reservation-writer, or formal-entrypoint
code.

The exact dependency symbol allowlist is:

```text
Phase 2b1:
  AttemptManifestV10Error
  PublicClaimReceiptV10
  AttemptManifestEventV10
  AttemptManifestEventFileV10
  AttemptManifestChainInspectionV10
  AttemptManifestChainAttestationV10
  encode_attempt_manifest_event_v1_0
  parse_attempt_manifest_event_file_v1_0
  inspect_local_attempt_manifest_chain_v1_0
  verify_local_attempt_manifest_terminal_chain_v1_0

Phase 2b2a:
  SyntheticSeedInventoryV10Error
  SyntheticClaimSeedV10
  SyntheticLocalClaimAuditV10
  SyntheticSeedLocalInventoryAuditV10
  parse_synthetic_claim_seed_v1_0
  audit_synthetic_seed_local_inventory_v1_0

Phase 2b2b:
  LocalArtifactObservationV10Error
  LocalArtifactObservationV10
  LocalArtifactSetObservationV10
  observe_local_rpc_artifact_set_v1_0

Phase 2b2c:
  InMemoryFakeCasV10Error
  InMemoryFakeCasStateV10
  InMemoryFakeCasTransitionV10
  initial_in_memory_fake_cas_state_v1_0

Phase 2b2d value validation only:
  LocalStagingFakePublishResultV10

Phase 2b2e:
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
  replay_synthetic_recovery_epoch_v1_0
  consume_synthetic_recovery_witness_v1_0
```

No dependency `__slots__`, underscored validator, hash helper, constant, or
private constructor may be read. Epoch, witness, and coordinator handles are
not reconstructed; only the exact objects issued by the internal coordinator
are used.

## 3. Exact public surface and inputs

The exact future `__all__` order is:

```text
IntegratedSyntheticManifestV10Error
SyntheticManifestResidueObservationV10
SyntheticCoordinatorActionTraceV10
SyntheticTerminalManifestAppendV10
SyntheticConflictWithoutMarkerAuditV10
IntegratedSyntheticRecoveryManifestAuditV10
audit_synthetic_conflict_without_marker_v1_0
append_integrated_synthetic_recovery_manifest_v1_0
```

The public exception is
`IntegratedSyntheticManifestV10Error(RuntimeError)`. All five records use
`@dataclass(frozen=True, slots=True)`, reject subclasses, and perform complete
own-cell/type/domain/nullability/hash validation. Direct record construction
performs no I/O and remains forgeable.

The two positional-only functions are exactly:

```python
audit_synthetic_conflict_without_marker_v1_0(
    root: str,
    seed_raw: bytes,
    constructor_profile: str,
    alternate_payload: bytes | None,
    proposed_payload: bytes,
    /,
) -> SyntheticConflictWithoutMarkerAuditV10

append_integrated_synthetic_recovery_manifest_v1_0(
    root: str,
    seed_raw: bytes,
    constructor_profile: str,
    alternate_payload: bytes | None,
    proposed_payload: bytes,
    /,
) -> IntegratedSyntheticRecoveryManifestAuditV10
```

No caller may supply a receipt, State, expected-version hash, nonce, timestamp,
staging path, coordinator, Result, Action, Marker, Epoch, Witness, failure code,
verdict, artifact observation, inventory result, or chain attestation.

Both functions accept exactly four profiles:

```text
ack_loss_confirmed
ack_loss_unavailable_then_confirmed
ack_loss_unavailable_until_budget_block
wrong_delta_confirmed
```

`normal` is rejected before any dependency call or I/O. For
`wrong_delta_confirmed`, `alternate_payload` is exact `bytes`, at most
1,048,576 bytes, and raw-unequal to `proposed_payload`. For every other
profile it is exactly `None`. `proposed_payload` is exact `bytes` of at most
1,048,576 bytes; empty bytes are allowed.

`root` is exact `str`, strict UTF-8, 1..4,096 bytes, free of C0/DEL, lexically
absolute, and equal to `os.path.normpath(root)`. On Windows it has an explicit
drive root and is neither UNC nor a device path. The value is evaluated and
retained once. It is never resolved, case-normalized, or ancestry-authenticated.

`seed_raw` is exact strict canonical bytes accepted by
`parse_synthetic_claim_seed_v1_0` and contains exactly one receipt. The seed is
caller supplied, forgeable, and not a temporal or remote inventory commitment.

## 4. Exact public records

`SyntheticManifestResidueObservationV10` has exactly these 39 ordered fields:

```python
observation_schema_version: str
observation_scope: str
origin_status: str
observation_phase: str
staging_parent: str
collision_nonce: str
stage_basename: str
stage_path: str
expected_payload_bytes: int
expected_payload_sha256: str
parent_namespace_state: str
parent_reason_codes: tuple[str, ...]
observation_state: str
reason_codes: tuple[str, ...]
observed_payload_bytes: int | None
observed_payload_sha256: str | None
payload_relation: str
observation_sha256: str
payload_byte_limit: int
staging_parent_utf8_byte_limit: int
stage_path_utf8_byte_limit: int
io_chunk_bytes: int
read_call_upper_bound: int
payload_work_upper_bound_bytes: int
peak_buffer_upper_bound_bytes: int
retained_payload_copy_upper_bound_bytes: int
path_derivation_scope: str
nofollow_scope: str
ancestor_reparse_check_scope: str
backing_store_scope: str
snapshot_scope: str
stage_attribution_scope: str
cleanup_scope: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`SyntheticCoordinatorActionTraceV10` has exactly these 23 ordered fields:

```python
trace_schema_version: str
trace_scope: str
origin_status: str
operation: str
outcome: str
reason_codes: tuple[str, ...]
action_sha256: str
before_snapshot_sha256: str
after_snapshot_sha256: str
endpoint_state_changed: bool
publisher_operation_sha256: str | None
publisher_transition_sha256: str | None
marker_sha256: str | None
epoch_ordinal: int | None
replay_observation: str | None
terminal_sha256: str | None
witness_purpose: str | None
detached_record_scope: str
authority_scope: str
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

It is a scalar projection made only after the corresponding exact Phase-2b2e
Action has been reconstructed and validated. It contains no Result, Epoch,
Witness, Coordinator, State, transition payload, or other live object.

`SyntheticTerminalManifestAppendV10` has exactly these 39 ordered fields:

```python
append_schema_version: str
append_scope: str
origin_status: str
license_id: str
publisher_collision_nonce: str
manifest_nonce: str
repository_path: str
host_final_path: str
host_alias_path: str
event_sha256: str
event_bytes: int
append_status: str
write_call_count: int
read_call_count: int
file_create_count: int
hardlink_create_count: int
retained_path_alias_count: int
append_sha256: str
event_byte_limit: int
host_path_utf8_byte_limit: int
io_chunk_bytes: int
write_call_upper_bound: int
read_call_upper_bound: int
file_create_upper_bound: int
hardlink_create_upper_bound: int
retained_path_alias_upper_bound: int
payload_work_upper_bound_bytes: int
peak_buffer_upper_bound_bytes: int
writer_scope: str
hardlink_scope: str
alias_retention_scope: str
durability_scope: str
cleanup_scope: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`SyntheticConflictWithoutMarkerAuditV10` has exactly these 58 ordered fields:

```python
audit_schema_version: str
audit_scope: str
origin_status: str
outcome: str
reason_codes: tuple[str, ...]
root: str
seed_file_sha256: str
seed_identity_sha256: str
license_id: str
claim_receipt_sha256: str
constructor_profile: str
publisher_collision_nonce: str
staging_parent: str
stage_basename: str
stage_path: str
proposed_payload_bytes: int
proposed_payload_sha256: str
alternate_payload_bytes: int | None
alternate_payload_sha256: str | None
initial_state_version_sha256: str
conflict_expected_state_version_sha256: str
initial_inventory_projection_sha256: str
active_chain_projection_sha256: str
pre_stage_observation: SyntheticManifestResidueObservationV10
action_trace: SyntheticCoordinatorActionTraceV10
final_snapshot_sha256: str
final_lifecycle_state: str
artifact_projection_sha256: str
post_stage_observation: SyntheticManifestResidueObservationV10
final_inventory_projection_sha256: str
cas_binding_sha256: str
audit_sha256: str
manifest_event_delta: str
conflict_without_marker_status: str
stage_residue_classification: str
same_call_binding_scope: str
persistent_cross_binding: str
artifact_scope: str
inventory_scope: str
detached_record_scope: str
stage_residue_scope: str
root_scope: str
ancestor_link_containment: str
basename_spelling_verification: str
hostile_concurrent_reparse_prevention: str
backing_store_scope: str
durability_scope: str
cleanup_scope: str
remote_publication: str
max_inventory_audits: int
max_artifact_observations: int
max_stage_observations: int
aggregate_dependency_payload_work_upper_bound_bytes: int
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`IntegratedSyntheticRecoveryManifestAuditV10` has exactly these 88 ordered
fields:

```python
audit_schema_version: str
audit_scope: str
origin_status: str
outcome: str
reason_codes: tuple[str, ...]
root: str
seed_file_sha256: str
seed_identity_sha256: str
license_id: str
claim_receipt_sha256: str
constructor_profile: str
publisher_collision_nonce: str
manifest_nonce: str
staging_parent: str
stage_basename: str
stage_path: str
manifest_repository_path: str
manifest_host_final_path: str
manifest_host_alias_path: str
proposed_payload_bytes: int
proposed_payload_sha256: str
alternate_payload_bytes: int | None
alternate_payload_sha256: str | None
initial_state_version_sha256: str
expected_state_version_sha256: str
initial_inventory_projection_sha256: str
active_chain_projection_sha256: str
pre_stage_observation: SyntheticManifestResidueObservationV10
action_trace: tuple[SyntheticCoordinatorActionTraceV10, ...]
action_count: int
marker: SyntheticRecoveryMarkerV10
witness_purpose: str
witness_sha256: str
preconsume_snapshot_sha256: str
preconsume_lifecycle_state: str
preappend_artifact_projection_sha256: str
preappend_stage_observation: SyntheticManifestResidueObservationV10
terminal_event_sha256: str
manifest_append: SyntheticTerminalManifestAppendV10
terminal_attestation_projection_sha256: str
postappend_artifact_projection_sha256: str
postappend_stage_observation: SyntheticManifestResidueObservationV10
final_inventory_projection_sha256: str
final_snapshot_sha256: str
final_lifecycle_state: str
cas_binding_sha256: str
manifest_binding_sha256: str
audit_sha256: str
failure_code_binding: str
stage_residue_classification: str
phase2b1_event_binding: str
publisher_operation_binding: str
marker_plan_binding: str
artifact_scope: str
inventory_scope: str
same_call_binding_scope: str
persistent_cross_binding: str
manifest_witness_atomicity: str
timestamp_scope: str
detached_record_scope: str
stage_residue_scope: str
manifest_alias_scope: str
root_scope: str
ancestor_link_containment: str
basename_spelling_verification: str
hostile_concurrent_reparse_prevention: str
backing_store_scope: str
durability_scope: str
cleanup_scope: str
remote_publication: str
real_recovery_scope: str
execution_scope: str
max_seed_claims: int
max_chain_events: int
max_coordinator_actions: int
max_recovery_epochs: int
max_artifact_observations: int
max_stage_observations: int
max_inventory_audits: int
max_manifest_appends: int
aggregate_dependency_payload_work_upper_bound_bytes: int
coordinator_payload_reference_upper_bound_bytes: int
proposal_payload_copy_upper_bound_bytes: int
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

Every record's four license booleans and every canonical/authority boolean are
exact `bool` and false. Bool-as-int rejects everywhere. Every digest is exact
uppercase hex64; both nonces are exact lowercase hex32.

## 5. Frozen constants, path derivation, and negative labels

The exact record constants are:

```text
observation_schema_version = lean-rgc-uprime-u1-synthetic-manifest-residue-observation-v1.0
observation_scope = one_sequential_bounded_final_component_stage_observation
trace_schema_version = lean-rgc-uprime-u1-integrated-coordinator-action-trace-v1.0
trace_scope = scalar_projection_of_one_internally_obtained_phase2b2e_action
append_schema_version = lean-rgc-uprime-u1-synthetic-terminal-manifest-append-v1.0
append_scope = one_exclusive_temp_verified_local_hardlink_materialization
conflict audit_schema_version = lean-rgc-uprime-u1-synthetic-conflict-without-marker-audit-v1.0
conflict audit_scope = one_internal_absent_g0_stale_expected_no_manifest_call
recovery audit_schema_version = lean-rgc-uprime-u1-integrated-synthetic-recovery-manifest-audit-v1.0
recovery audit_scope = one_same_call_sequential_synthetic_terminal_append_and_consume
origin_status = unknown_may_be_synthetic
authority_scope = none
```

The retained lexical `root` determines every path. Native host paths use only
`os.path.join`; the persisted manifest repository path always uses `/`:

```text
attempt_directory =
  join(root, "docs", "experiments", "artifacts",
       "uprime_u1_rpc_attempts", license_id)

staging_parent =
  join(root, "docs", "experiments", "artifacts",
       "uprime_u1_rpc_staging", license_id)

stage_basename =
  "uprime-rpc-fake-cas-stage-v1-" + publisher_collision_nonce + ".bin"

stage_path = join(staging_parent, stage_basename)

manifest_repository_path =
  "docs/experiments/artifacts/uprime_u1_rpc_attempts/" +
  license_id + "/0002.json"

manifest_host_final_path =
  join(attempt_directory, "0002.json")

manifest_alias_basename =
  "uprime-rpc-attempt-manifest-stage-v1-" + manifest_nonce + ".json"

manifest_host_alias_path =
  join(staging_parent, manifest_alias_basename)
```

`stage_basename` is exactly 65 ASCII bytes and the manifest alias basename is
exactly 74 ASCII bytes. The derived staging parent must independently satisfy
the Phase-2b2d 4,096-byte UTF-8 limit; the derived publisher path must satisfy
4,162 bytes. The manifest alias is at most 4,171 bytes. The append record's
independent final-path cell limit is 4,221 bytes; because this API also derives
the staging parent, an admissible root is effectively at most 3,982 bytes and
the same-root final path is at most 4,107 bytes. Root, publisher-stage,
repository, and final paths are computed once and rejected before the first
dependency call or I/O if their own limits or native normalized spelling fail.
The manifest nonce and alias path are definitionally late: they are computed
once after the terminal event and marker exist, then validated before their
first stat or create. The 4,096-byte limit on `root` alone is not treated as
proof of any derived-path bound.

The initial state is exactly the public value returned by
`initial_in_memory_fake_cas_state_v1_0()`: absent value, generation zero, and
its exact public state-version digest. Recovery uses that exact version as the
expected version. Conflict uses a derived unequal version formed by changing
the first hex digit to `1` if it is `0`, and to `0` otherwise, leaving the
remaining 63 digits unchanged. No fixed magic digest or caller expected value
is accepted.

The exact negative labels are:

```text
path_derivation_scope = lexical_native_join_from_one_retained_root_no_resolution
nofollow_scope = final_component_checks_and_descriptor_binding_platform_dependent
ancestor_reparse_check_scope = not_performed
backing_store_scope = unauthenticated_may_be_remote_virtual_or_overlay
snapshot_scope = sequential_endpoint_not_atomic_or_current_after_return
stage_attribution_scope = expected_path_and_bytes_relation_not_origin_or_ownership
cleanup_scope = no_unlink_rename_replace_or_residue_cleanup

detached_record_scope = forgeable_value_projection_not_capability_or_io_attestation
same_call_binding_scope = same_live_call_sequential_transcript_only
persistent_cross_binding = not_encoded_in_phase2b1_event
manifest_witness_atomicity = not_provided_two_ordered_endpoints
artifact_scope = three_sequential_rows_only_not_atomic_bundle_or_content_validation
inventory_scope = caller_seed_vs_bounded_local_namespace_not_real_claim_completeness
stage_residue_scope = epistemic_endpoint_classification_not_owned_durable_or_safe_to_remove
manifest_alias_scope = two_names_one_observed_file_object_no_immutability_or_lifetime_claim
root_scope = one_caller_supplied_lexical_root_not_canonical_namespace_identity
ancestor_link_containment = not_authenticated
basename_spelling_verification = not_performed
hostile_concurrent_reparse_prevention = not_provided
durability_scope = fsync_not_called_crash_and_power_loss_not_observed
remote_publication = not_performed
real_recovery_scope = not_performed_synthetic_same_process_state_machine_only
execution_scope = not_performed
timestamp_scope = copied_index1_value_nondecreasing_not_wall_clock_causality
```

`canonical_remote_authority`, `licenses_execution`, `licenses_publication`,
`licenses_recovery`, and `licenses_later_stage` are exact false everywhere.

The frozen observation bounds per call are:

```text
payload_byte_limit = 1,048,576
staging_parent_utf8_byte_limit = 4,096
stage_path_utf8_byte_limit = 4,162
io_chunk_bytes = 65,536
read_call_upper_bound = 34
payload_work_upper_bound_bytes = 2,097,153
peak_buffer_upper_bound_bytes = 65,536
retained_payload_copy_upper_bound_bytes = 0
```

The frozen append-call bounds are:

```text
event_byte_limit = 1,048,576
host_path_utf8_byte_limit = 4,221
io_chunk_bytes = 65,536
write_call_upper_bound = 1,048,576
read_call_upper_bound = 17
file_create_upper_bound = 1
hardlink_create_upper_bound = 1
retained_path_alias_upper_bound = 2
payload_work_upper_bound_bytes = 2,097,153
peak_buffer_upper_bound_bytes = 65,536
```

The payload-work value charges the EOF probe one logical unit and is a
conservative whole-call bound; a successful call returns/writes at most
2,097,152 payload bytes. On a successful append, both create counts are exactly one and the retained
path-alias count is exactly two. The two aliases denote one observed file
identity. The phase makes no physical-block-count claim.

## 6. Preflight and exact active-chain endpoint

All then-derivable input, profile, size, root, publisher/final-path,
frozen-constant, seed-parse, and pure-hash validation precedes filesystem
observation. The late manifest nonce/alias follows Section 5. Both functions then
require the exact same read-only preflight:

1. `parse_synthetic_claim_seed_v1_0(seed_raw)` reconstructs an exact seed with
   `claim_count == 1`; its sole exact `PublicClaimReceiptV10` is reconstructed
   through the public constructor and supplies `license_id`;
2. `attempt_directory` and `staging_parent` already exist, are final-component
   real non-reparse directories, and have equal `st_dev`; the implementation
   never calls `mkdir`;
3. the first `audit_synthetic_seed_local_inventory_v1_0` result reconstructs
   exactly and has the endpoint below;
4. one direct `inspect_local_attempt_manifest_chain_v1_0` reconstructs an
   exact active-chain endpoint and agrees with the inventory; and
5. the publisher-stage observation is exact stable absence.

The pre-inventory endpoint is exactly:

```text
base_directory_status = present
seed_count = local_directory_count = union_claim_count = examined_claim_count = 1
unexpected_entry_count = 0
unexpected_entry_names = ()
seeded_missing_ids = local_orphan_ids = receipt_mismatch_ids = ()
terminal_ids = ()
nonterminal_ids = (license_id,)
empty_chain_ids = ()
coverage_status = mismatched
set_equality = true
all_seeded_local_present = true
all_seeded_terminal = false
all_seeded_receipts_match = true
```

Its sole claim audit is exact seed/local membership, `set_relation=seed_and_local`,
`receipt_relation=exact_match`, equal seed/local receipt hashes,
`chain_observation=valid_nonterminal`, event count/index `1/1`, nonnull last
event hash, `terminal_event=false`, and null verdict. Every negative scope and
false authority field must retain the dependency's exact frozen value.

The direct active inspection is exactly:

```text
chain_state = valid_nonterminal
event_count = 1
last_event_index = 1
last_event_type = claim_started
terminal_event = false
recorded_verdict = null
next_event_index = 2
first_event_sha256 = last_event_sha256
claim_receipt_sha256 = seed receipt digest
```

The sole file is repository path ending `/0001.json`; its event is an exact
valid `claim_started` index-1 event with the same receipt and digest, null
prior hash, empty failure tuple, and its exact canonical bytes hash. The
index-1 timestamp and event hash are retained for the terminal plan. A missing,
empty, terminal, multi-event, index-exhausted, orphaned, unexpected, or
receipt-mismatched namespace is a hard preflight failure with no coordinator
or write call.

The post-conflict inventory must reproduce the same one-event endpoint and
have a byte-identical inventory projection. The post-recovery inventory must
instead have one exact `valid_terminal` claim, two events, last index 2, no
nonterminal or empty IDs, `coverage_status=matched_terminal`, and all four
aggregate booleans true. Neither endpoint upgrades the dependency's
unauthenticated completeness labels.

## 7. Exact stage-residue observer

The observer is an internal Phase-2b2f routine; no public standalone function
is exported. It receives only the internally derived path/nonce and the exact
proposal reference. Its record is returned only as a nested forgeable value.

Every reason tuple is an exact ASCII singleton. Parent classification is
ordered and fail-closed:

```text
present       (stable_parent_directory,)
absent        (stable_parent_absence,)
indeterminate first applicable of:
  parent_initial_stat_error
  parent_metadata_invalid
  parent_reparse_entry
  parent_nondirectory
  parent_absence_changed
  parent_absence_recheck_error
  parent_final_stat_error
  parent_final_entry_invalid
  parent_drift
```

For a stable present parent, the child classification is:

```text
absent:
  (absent_at_both_points,) and payload_relation=not_present

present exact:
  (stable_bounded_regular_file_exact_payload,) and payload_relation=exact

present different:
  (stable_bounded_regular_file_different_payload,) and payload_relation=different

indeterminate, first applicable of:
  initial_stat_error
  absence_changed
  absence_recheck_error
  metadata_invalid
  reparse_entry
  nonregular_entry
  size_limit_exceeded
  open_error
  descriptor_metadata_invalid
  descriptor_nonregular
  descriptor_path_mismatch
  seek_error
  read_error
  short_read
  unexpected_eof_relation
  descriptor_drift
  close_error
  final_stat_error
  final_entry_invalid
  final_path_drift
```

A stable absent parent produces a stable-absence child with parent reason. An
indeterminate parent produces an indeterminate child with the same reason.
Parent final failure or drift clears any favorable child result and wins the
recorded reason.

For a present file the routine no-follow stats the path, opens read-only with
the platform's available no-follow/binary/noninherit flags, binds descriptor
metadata to the observed path, seeks to offset zero before each pass, and
performs two complete chunked passes plus EOF probes with a descriptor snapshot
between passes. Every returned chunk is compared byte-for-byte with the matching
slice of the expected proposal while SHA-256 is streamed. No whole-payload
copy is created. Both passes, descriptor snapshots, post-close no-follow path
snapshot, and the final parent snapshot must agree. Digest equality never
substitutes for raw equality. The `observed_*` cells are nonnull only for a
stable present row; absent and indeterminate rows use null. Direct record
construction performs no observation.

Recovery requires the exact row sequence:

```text
pre_publish    absent / not_present
pre_append     present / exact
post_append    present / exact
```

Conflict requires exact absence at `conflict_pre` and `conflict_post`.
`present`, `different`, or `indeterminate` never upgrades to absence and never
licenses a manifest append.

## 8. Recovery coordinator call order and terminal plan

The recovery function has this exact order. No later step may be moved before
an earlier gate:

1. pure input, seed, constant, hash, and path validation;
2. final-component directory and same-device preflight;
3. initial inventory audit and direct active-chain inspection;
4. `pre_publish` publisher-stage absence observation;
5. construct the exact initial absent-at-generation-zero State and one
   Phase-2b2e coordinator for the selected profile;
6. invoke `publish_with_synthetic_recovery_coordinator_v1_0` exactly once with
   the internally derived staging parent, collision nonce, initial State,
   exact initial version, and proposal;
7. validate and project the returned publish Action and exact live marker;
8. run the fixed acquire/replay sequence below, retaining only the current
   exact opaque epoch and the terminal exact witness; never release or abandon;
9. reconstruct the terminal Action, marker, witness scalars, and one
   `snapshot_synthetic_recovery_coordinator_v1_0` preconsume snapshot;
10. observe the three ordinary artifacts and require the exact all-absent
    vector;
11. perform the `pre_append` publisher-stage observation and require exact
    proposal bytes;
12. construct, encode, and pure-parse the exact terminal event; derive the
    manifest nonce and paths;
13. perform the one manifest append protocol in Section 9;
14. call `verify_local_attempt_manifest_terminal_chain_v1_0` once and validate
    the terminal attestation against the plan and append;
15. observe the ordinary artifacts again and require exact all-absent;
16. perform the `post_append` publisher-stage observation and require exact
    proposal bytes;
17. run the final inventory audit and require the exact matched-terminal
    endpoint;
18. finish every projection/binding check and preconstruct every output cell
    that does not depend on witness consumption;
19. as the last stateful/nonconstructor dependency call and last mutation,
    consume the exact same-instance witness using its exact purpose and
    terminal hash; and
20. purely reconstruct and validate the returned consume Action, append its
    trace, take final digest/lifecycle from its after-snapshot, compute the
    same-call audit hash, and construct the result. No I/O or stateful
    dependency call/mutation follows witness consumption; pure public record
    constructors, scalar projections, hashes, and output construction do.

The exact Action sequences and maxima are:

| profile | ordered operations | action count | replay count | terminal |
|---|---|---:|---:|---|
| `ack_loss_confirmed` | publish, acquire, replay, consume | 4 | 1 | recovered |
| `ack_loss_unavailable_then_confirmed` | publish, acquire, replay, acquire, replay, consume | 6 | 2 | recovered |
| `ack_loss_unavailable_until_budget_block` | publish, then four acquire/replay pairs, consume | 10 | 4 | permanent block |
| `wrong_delta_confirmed` | publish, acquire, replay, consume | 4 | 1 | permanent block |

Every acquire must return `epoch_issued`; each replay outcome must equal the
profile's frozen Phase-2b2e plan. No terminal no-op is called. The final
witness purpose is `record_recovered_terminal` for the first two profiles and
`record_permanent_block` for the latter two. A permanent-block witness records
only that synthetic block; it is never reported as recovered success.

The Action trace is reconstructed from each exact returned Phase-2b2e Action.
Its before/after hashes, state-change Boolean, operation/outcome/reasons,
publisher operation and transition when a publish Result is present, marker,
epoch, replay, terminal, and witness cells must agree with that Action. For a
nonnormal publish, the public publish Result and both publisher cells in the
trace are null, while the top-level exact marker supplies the retained
publisher operation/transition. For conflict, both publisher cells are
nonnull and the marker cell is null. Neither public function accepts a trace
argument. A returned trace is checked for exact value consistency only; a
detached value-identical dependency return is not origin-authenticated and
cannot be distinguished by this phase.

For every recovery trace index `i > 0`,
`trace[i].before_snapshot_sha256 == trace[i-1].after_snapshot_sha256`.
The preconsume snapshot equals the terminal replay's after-snapshot; the
consume before-snapshot equals that preconsume hash; and the consume
after-snapshot equals the final snapshot. The first publish before-snapshot is
only the exact scalar in the returned Action. No independent pre-publish
snapshot origin attestation is claimed.

The terminal event is exactly:

```text
schema_version = lean-rgc-uprime-u1-attempt-manifest-v1.0
event_type = recovery
event_index = 2
created_at_utc = exact index-1 created_at_utc
license_id/candidate_commit/license_commit/remote_claim_ref = exact receipt cells
claim_receipt = exact reconstructed receipt
claim_receipt_sha256 = exact receipt digest
prior_event_sha256 = exact index-1 event SHA-256
reservation_exists = ledger_exists = report_exists = false
reservation_sha256/reservation_bytes = null
ledger_sha256/ledger_bytes = null
report_sha256/report_bytes = null
ledger_inspection_status = absent
ledger_sequence_status = null
verifier_status = not_run
scanner_status = not_run
scanner_rule_ids = ()
verdict = null
failure_codes = exact marker.phase2b1_failure_codes
full_ledger_published = false
terminal_event = true
```

The marker failure tuple is copied without interpretation. In the current
Phase-2b2e contract it is exactly `("OTHER_HARNESS_ERROR",)` for all four
profiles. `POWER_LOSS`, `CLAIM_STARTED_MANIFEST_ERROR`,
`FINAL_MANIFEST_ERROR`, profile-derived substitutions, and any success verdict
are forbidden. The copied timestamp is only a deterministic nondecreasing
chain value; it is not evidence that event 2 occurred at event 1's wall-clock
time.

Successful recovery has:

```text
outcome = integrated_synthetic_terminal_manifest_appended_and_witness_spent
reason_codes = (exact terminal_reason,)
failure_code_binding = exact_phase2b2e_marker_tuple_no_inference
stage_residue_classification = absent_before_publish_exact_proposal_at_two_later_endpoints
phase2b1_event_binding = exact_index2_recovery_bytes_and_terminal_attestation
publisher_operation_binding = marker_hashes_plus_same_call_stage_byte_observations
marker_plan_binding = exact_phase2b2e_profile_plan_and_live_handle_sequence
```

These labels describe program order and deterministic value equality within
one live call only.

## 9. Exclusive manifest append protocol

`encode_attempt_manifest_event_v1_0` is the only event encoder. Its returned
bytes must be exact `bytes`, nonempty, at most 1,048,576 bytes, contain one
final LF, and pure-parse byte-identically at the exact repository path before
any create. `event_sha256` covers the complete bytes including that LF.

Immediately before create, the implementation rechecks that both alias and
final names are absent, both parent directories are stable real non-reparse
final components, and their device identifiers agree. A pre-existing alias or
final path, even with exact expected bytes, is a conflict. This phase never
adopts, reconciles, overwrites, renames, removes, or retries a preplayed name.

The exact successful protocol is:

```text
1. os.open(alias,
     O_CREAT | O_EXCL | O_RDWR | available O_BINARY/O_NOINHERIT/
     O_CLOEXEC/O_NOFOLLOW, 0o600)
2. fstat: exact empty regular descriptor
3. positive partial-write loop over the exact event bytes
4. fstat: exact final size and unchanged descriptor identity
5. lseek to zero
6. exact-sized reads in 65,536-byte chunks, byte-for-byte comparison and
   streamed SHA-256, followed by one EOF probe
7. fstat: unchanged exact descriptor endpoint
8. close exactly once
9. no-follow alias stat: regular, non-reparse, same identity and size
10. repeat the final-name no-follow absence check immediately before linking
11. os.link(alias, final, follow_symlinks=False) exactly once; require exact None
12. no-follow alias and final stats: both regular/non-reparse, same file
    identity and exact size under the frozen post-link comparator
```

Positive partial writes are accumulated; zero/negative/impossible writes fail.
Reads must return the exact requested chunk and the final probe must be empty.
The event bytes are never read through the final name by this writer; the
independent Phase-2b1 verifier performs that endpoint read. The temp alias is
intentionally retained after success. No `fsync`, `fdatasync`, directory sync,
chmod, replace, rename, or unlink occurs.

The post-link identity comparison is `(st_dev, st_ino, file type, st_size)`;
ctime and link count may change when the hardlink is created and are not
required to equal the pre-link values.

The failure-cut state advances to `hardlink_invoked_success_unconfirmed`
immediately before calling `os.link`. Any exception from that call, including
a test seam that creates the link and then raises, stays in that cut; it never
consumes the witness or upgrades to success.

The successful append record has:

```text
append_status = exclusive_temp_verified_hardlink_materialized
writer_scope = exact_temp_write_readback_then_exclusive_final_hardlink
hardlink_scope = local_same_device_two_names_one_observed_file_identity
alias_retention_scope = both_alias_and_final_retained_no_lifetime_immutability_claim
write_call_count = actual positive write calls, 1..1,048,576
read_call_count = actual exact reads including EOF, 2..17
file_create_count = 1
hardlink_create_count = 1
retained_path_alias_count = 2
```

`append_sha256` binds the exact repository/host paths, nonces, event hash and
size, status, and actual counts. It is a deterministic returned label, not a
durable publication receipt.

## 10. Conflict-without-marker endpoint

The conflict function shares pure validation and exact one-event preflight,
then performs only this sequence:

1. exact `conflict_pre` publisher-stage absence observation;
2. construct the initial absent-at-generation-zero State and a fresh internal
   coordinator;
3. call owned publish once with the internally derived unequal expected
   version;
4. require exact `cas_conflict_no_marker`, a nonnull exact no-stage publisher
   Result, null marker/epoch/witness cells, and an `OPEN` after-snapshot;
5. exact `conflict_post` publisher-stage absence observation;
6. one ordinary-artifact observation requiring exact all-absent;
7. one final inventory audit requiring the same active one-event endpoint and
   the same inventory projection; and
8. construct the negative audit. There is no manifest encoder, open, write,
   link, append, terminal verifier, replay, witness, or cleanup call.

Its exact success labels are:

```text
outcome = conflict_without_marker_confirmed
reason_codes = (expected_state_version_mismatch,)
final_lifecycle_state = OPEN
manifest_event_delta = zero
conflict_without_marker_status = exact_no_marker_no_stage_no_manifest
stage_residue_classification = exact_absent_at_two_sequential_endpoints
```

The action trace's nonnull publisher operation/transition hashes, exact
initial and unequal expected versions, unchanged final snapshot, and both
absence observations are combined in `cas_binding_sha256`. The endpoint does
not invent a Phase-2b1 failure code and cannot be upgraded by a favorable
pre-existing terminal chain because such a chain fails preflight.

## 11. Dependency reconstruction and failure cuts

Every imported result is required to have the exact public type. Dataclass
dependency values are copied field-by-field into public constructors and must
compare equal to the reconstruction before use. For a conflict publish, the
Phase-2b2c Transition is reconstructed first, then the Phase-2b2d Result, then
the Phase-2b2e Action. Opaque factory-only coordinator/epoch/witness handles
are instead checked by the dependency's same-instance operations and are never
reconstructed. Every cross-dependency identity, count, hash, path, profile,
state, and false authority cell is rechecked. A subclass, internally
inconsistent mutation, or wrong-but-well-typed record fails closed. A
value-identical detached or monkeypatched return remains indistinguishable and
is explicitly unauthenticated. The integrated result constructors themselves
perform no I/O, stateful dependency call, or current-state restat; pure public
record construction and hashing are allowed.

The public functions expose one sanitized ordinary-error surface. Every
ordinary `Exception`, including a same-class exception injected through a
dependency seam, is mapped with suppressed chaining to a fresh
`IntegratedSyntheticManifestV10Error` whose one frozen message is selected
only by the reached cut:

```text
integrated synthetic preflight failed
integrated synthetic conflict audit failed
integrated synthetic recovery failed before manifest temp create
integrated synthetic recovery failed after manifest temp create
integrated synthetic recovery failed after manifest hardlink
integrated synthetic recovery failed after witness consumption
```

No host path, dependency exception string, errno, payload, receipt, or secret
is interpolated. A non-`Exception` `BaseException` is re-raised as the exact
same object. After an fd has been obtained, close is attempted exactly once on
every exit; a primary `BaseException` is never masked by close. No residue
cleanup is attempted.

The exact failure-cut adjudication is:

| cut | possible retained filesystem effect | internal witness endpoint | permitted claim |
|---|---|---|---|
| before owned publish | none by Phase2b2f | none | preflight error only |
| owned changed publish fails | none, partial, complete, or replaced stage is unknown | none or coordinator poisoned without marker | no append; no residue ownership |
| after marker, before terminal witness | publisher stage may remain | no terminal witness | no append |
| terminal witness through before temp create | exact stage was observed at one endpoint | live witness becomes unreachable on error | no manifest |
| after temp create, before hardlink invocation | partial or complete alias may remain; final absent or concurrently present | live witness becomes unreachable | no adoption/cleanup/retry |
| hardlink invoked but success return unconfirmed | alias and final may both exist, including a perform-then-raise seam | live witness becomes unreachable | no link-success claim, adoption, cleanup, or consume |
| after hardlink, before consume | alias and terminal final may remain | live witness becomes unreachable | two sequential endpoints, not atomic |
| consume call fails | alias/final remain | dependency-determined live or spent state, no result | no retry or repair authority |
| after successful consume, result/hash fails | alias/final remain | witness spent | no returned audit; no exactly-once claim |

The coordinator is factory-owned and never returned, so a failed call cannot
be resumed through this API. Complete bytes may exist without a returned
audit, and a live or spent witness may be lost with the process object. This is
the decisive reason the phase is not real recovery or a durable transaction.

## 12. Exact digest grammar, projections, and independent goldens

All complete digests are uppercase SHA-256. Nonces are the lowercase hex of
the first 16 digest bytes. Let:

```text
U8/U16/U32/U64(n) = unsigned big-endian integer of the stated width
K(s) = U16(len(ASCII(s))) || ASCII(s)
P(s) = U32(len(strict_UTF8(s))) || strict_UTF8(s)
H(h) = 32 raw bytes represented by uppercase hex64 h
L(l) = 32 raw bytes represented by lowercase hex64 l
N(n) = 16 raw bytes represented by lowercase hex32 n
Q(h?) = 00 for null; 01 || H(h) otherwise
J(i?) = 00 for null; 01 || U64(i) otherwise
S(s?) = 00 for null; 01 || K(s) otherwise
T(xs) = U16(count) || K(xs[0]) || ... in exact tuple order
B(false) = 00; B(true) = 01
Z(null) = 00; Z(false) = 01; Z(true) = 02
```

`K` is used only for frozen ASCII labels/timestamps. `P` is used for caller or
derived path text. All nullable tags are mandatory; concatenation never relies
on a delimiter or host encoding.

The exact domains, each including its terminal NUL, are:

```text
D_PUBLISHER_NONCE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-publisher-nonce-v1\0"
D_MANIFEST_NONCE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-manifest-nonce-v1\0"
D_RESIDUE = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-residue-observation-v1\0"
D_INVENTORY = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-inventory-projection-v1\0"
D_ACTIVE_CHAIN = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-active-chain-projection-v1\0"
D_ARTIFACT = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-artifact-projection-v1\0"
D_TERMINAL_ATTESTATION = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-attestation-projection-v1\0"
D_APPEND = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-terminal-append-v1\0"
D_CAS = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-cas-binding-v1\0"
D_CONFLICT = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-conflict-audit-v1\0"
D_MANIFEST_BINDING = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-binding-v1\0"
D_RECOVERY = b"lean-rgc-uprime-u1-integrated-synthetic-manifest-recovery-audit-v1\0"
```

Their byte lengths in that order are exactly
`68/67/72/73/76/72/84/68/64/67/60/67`.

The two nonce formulas are:

```text
publisher_nonce_preimage =
  D_PUBLISHER_NONCE || H(seed_identity_sha256) || K(profile) ||
  U64(proposed_payload_bytes) || H(proposed_payload_sha256) ||
  J(alternate_payload_bytes) || Q(alternate_payload_sha256)

publisher_collision_nonce =
  lower_hex(first_16_bytes(SHA256(publisher_nonce_preimage)))

manifest_nonce_preimage =
  D_MANIFEST_NONCE || H(terminal_event_sha256) ||
  H(marker_sha256) || H(terminal_sha256)

manifest_nonce =
  lower_hex(first_16_bytes(SHA256(manifest_nonce_preimage)))
```

The observation projection is:

```text
residue = SHA256(
  D_RESIDUE || K(observation_phase) || P(staging_parent) ||
  N(collision_nonce) || K(stage_basename) || P(stage_path) ||
  U64(expected_payload_bytes) || H(expected_payload_sha256) ||
  K(parent_namespace_state) || T(parent_reason_codes) ||
  K(observation_state) || T(reason_codes) || J(observed_payload_bytes) ||
  Q(observed_payload_sha256) || K(payload_relation)
)
```

The exact one-claim inventory projection is:

```text
inventory = SHA256(
  D_INVENTORY || H(seed_file_sha256) || H(seed_identity_sha256) ||
  K(base_directory_status) || U64(seed_count) || U64(local_directory_count) ||
  U64(union_claim_count) || U64(examined_claim_count) ||
  U64(total_observed_event_bytes) || U64(unexpected_entry_count) ||
  K(coverage_status) || B(set_equality) || B(all_seeded_local_present) ||
  B(all_seeded_terminal) || B(all_seeded_receipts_match) || U16(1) ||
  L(claim.license_id) || B(claim.seed_membership) ||
  B(claim.local_membership) || K(claim.set_relation) ||
  K(claim.receipt_relation) || Q(claim.seed_receipt_sha256) ||
  Q(claim.local_receipt_sha256) || K(claim.chain_observation) ||
  J(claim.event_count) || J(claim.last_event_index) ||
  Q(claim.last_event_sha256) || Z(claim.terminal_event) ||
  S(claim.recorded_verdict)
)
```

The active-chain projection is:

```text
active_chain = SHA256(
  D_ACTIVE_CHAIN || L(license_id) || H(claim_receipt_sha256) ||
  H(first_event_sha256) || H(last_event_sha256) ||
  U64(len(index1_event_bytes)) || U64(event_count) ||
  U64(last_event_index) || K(last_event_type) || B(terminal_event) ||
  J(next_event_index) || K(index1_created_at_utc)
)
```

The artifact projection iterates exact reservation/ledger/report order:

```text
artifact = SHA256(
  D_ARTIFACT || H(claim_receipt_sha256) || K(parent_namespace_state) ||
  T(parent_reason_codes) || U16(3) ||
  each [K(artifact_kind) || P(repository_path) || K(observation_state) ||
        T(reason_codes) || Q(artifact_sha256) || J(artifact_bytes) ||
        U64(byte_limit)] ||
  U64(present_count) || U64(absent_count) || U64(indeterminate_count) ||
  U64(total_present_bytes) || K(snapshot_scope)
)
```

Only an accepted all-absent vector receives a top-level artifact projection.
The terminal-attestation projection is:

```text
terminal_attestation = SHA256(
  D_TERMINAL_ATTESTATION || L(license_id) || H(claim_receipt_sha256) ||
  U64(event_count) || H(first_event_sha256) || U64(last_event_index) ||
  H(last_event_sha256) || K(chain_state) || B(terminal_event) ||
  K(last_event_type) || S(recorded_verdict) || T(failure_codes)
)
```

For each 23-cell trace, define the un-hashed exact projection bytes:

```text
TRACE(t) =
  K(t.operation) || K(t.outcome) || T(t.reason_codes) || H(t.action_sha256) ||
  H(t.before_snapshot_sha256) || H(t.after_snapshot_sha256) ||
  B(t.endpoint_state_changed) || Q(t.publisher_operation_sha256) ||
  Q(t.publisher_transition_sha256) || Q(t.marker_sha256) ||
  J(t.epoch_ordinal) || S(t.replay_observation) || Q(t.terminal_sha256) ||
  S(t.witness_purpose)
```

The append and CAS bindings are:

```text
append = SHA256(
  D_APPEND || L(license_id) || N(publisher_collision_nonce) ||
  N(manifest_nonce) || P(repository_path) || P(host_final_path) ||
  P(host_alias_path) || H(event_sha256) || U64(event_bytes) ||
  K(append_status) || U64(write_call_count) || U64(read_call_count) ||
  U64(file_create_count) || U64(hardlink_create_count) ||
  U64(retained_path_alias_count)
)

cas = SHA256(
  D_CAS || K(endpoint_kind) || H(initial_state_version_sha256) ||
  H(expected_state_version_sha256) || U64(proposed_payload_bytes) ||
  H(proposed_payload_sha256) || J(alternate_payload_bytes) ||
  Q(alternate_payload_sha256) || Q(publisher_operation_sha256) ||
  Q(publisher_transition_sha256) || Q(synthetic_fault_transition_sha256) ||
  Q(marker_sha256)
)
```

`endpoint_kind` is exactly `conflict` for the conflict record and `recovery`
for the integrated recovery record; no other value is in the domain.

Conflict takes its publisher hashes from the nonnull public publish Result.
Recovery takes them and the synthetic-fault hash from the exact live marker.
The conflict audit is:

```text
conflict_audit = SHA256(
  D_CONFLICT || K(outcome) || T(reason_codes) || P(root) ||
  H(seed_file_sha256) || H(seed_identity_sha256) || L(license_id) ||
  H(claim_receipt_sha256) || K(constructor_profile) ||
  N(publisher_collision_nonce) || P(staging_parent) || K(stage_basename) ||
  P(stage_path) || U64(proposed_payload_bytes) || H(proposed_payload_sha256) ||
  J(alternate_payload_bytes) || Q(alternate_payload_sha256) ||
  H(initial_state_version_sha256) || H(conflict_expected_state_version_sha256) ||
  H(initial_inventory_projection_sha256) || H(active_chain_projection_sha256) ||
  H(pre_stage_observation.observation_sha256) || TRACE(action_trace) ||
  H(final_snapshot_sha256) || K(final_lifecycle_state) ||
  H(artifact_projection_sha256) ||
  H(post_stage_observation.observation_sha256) ||
  H(final_inventory_projection_sha256) || H(cas_binding_sha256) ||
  K(manifest_event_delta) || K(conflict_without_marker_status) ||
  K(stage_residue_classification)
)
```

The same-call manifest binding and recovery audit are:

```text
manifest_binding = SHA256(
  D_MANIFEST_BINDING || H(active_chain_projection_sha256) ||
  H(marker.marker_sha256) || H(cas_binding_sha256) ||
  H(terminal_event_sha256) || H(manifest_append.append_sha256) ||
  H(terminal_attestation_projection_sha256) ||
  H(preappend_artifact_projection_sha256) ||
  H(pre_stage_observation.observation_sha256) ||
  H(preappend_stage_observation.observation_sha256) ||
  H(postappend_artifact_projection_sha256) ||
  H(postappend_stage_observation.observation_sha256) ||
  H(final_inventory_projection_sha256) || H(preconsume_snapshot_sha256) ||
  H(final_snapshot_sha256) || U16(action_count) ||
  TRACE(action_trace[0]) || ... || TRACE(action_trace[action_count-1])
)

recovery_audit = SHA256(
  D_RECOVERY || K(outcome) || T(reason_codes) || P(root) ||
  H(seed_file_sha256) || H(seed_identity_sha256) || L(license_id) ||
  H(claim_receipt_sha256) || K(constructor_profile) ||
  N(publisher_collision_nonce) || N(manifest_nonce) || P(staging_parent) ||
  K(stage_basename) || P(stage_path) || P(manifest_repository_path) ||
  P(manifest_host_final_path) || P(manifest_host_alias_path) ||
  U64(proposed_payload_bytes) || H(proposed_payload_sha256) ||
  J(alternate_payload_bytes) || Q(alternate_payload_sha256) ||
  H(initial_state_version_sha256) || H(expected_state_version_sha256) ||
  H(initial_inventory_projection_sha256) || H(active_chain_projection_sha256) ||
  H(pre_stage_observation.observation_sha256) || U16(action_count) ||
  TRACE(action_trace[0]) || ... || TRACE(action_trace[action_count-1]) ||
  H(marker.marker_sha256) || K(witness_purpose) || H(witness_sha256) ||
  H(preconsume_snapshot_sha256) || K(preconsume_lifecycle_state) ||
  H(preappend_artifact_projection_sha256) ||
  H(preappend_stage_observation.observation_sha256) ||
  H(terminal_event_sha256) || H(manifest_append.append_sha256) ||
  H(terminal_attestation_projection_sha256) ||
  H(postappend_artifact_projection_sha256) ||
  H(postappend_stage_observation.observation_sha256) ||
  H(final_inventory_projection_sha256) || H(final_snapshot_sha256) ||
  K(final_lifecycle_state) || H(cas_binding_sha256) ||
  H(manifest_binding_sha256) || K(failure_code_binding) ||
  K(stage_residue_classification)
)
```

Static schema, scope, resource, and authority cells are exact constructor
invariants and are deliberately omitted from dynamic hashes. The three fixed
recovery semantic labels `phase2b1_event_binding`,
`publisher_operation_binding`, and `marker_plan_binding` are likewise exact
constructor invariants and intentionally omitted; unlike the dynamic failure
and residue classifications they have no alternate accepted value. Exact endpoint
validation precedes every projection. The reachable maximum preimage byte
lengths are:

| preimage/projection | maximum bytes |
|---|---:|
| publisher nonce | 205 |
| manifest nonce | 163 |
| residue observation | 8,623 |
| one-claim inventory | 416 |
| active chain | 282 |
| admissible all-absent artifact | 590 |
| terminal attestation | 279 |
| one Action `TRACE` | 323 |
| terminal append | 8,787 own-cell / 8,673 same-root reachable |
| CAS binding | 352 |
| conflict audit | 13,353 |
| manifest binding | 2,824 |
| recovery audit | 24,260 |

For independent grammar fixtures, let `R_n` be the byte of decimal value `n`
repeated 32 times and rendered as uppercase hex64 where a hash is required.
Use root `/tmp/uprime-2b2f`, license ID `ab` repeated 32, seed-file/identity/
receipt hashes `R_1/R_2/R_3`, profile `ack_loss_confirmed`, proposal `b"B"`,
null alternate, and initial version
`D475431F78A252741905BD00E75E0E97A30326A91046BF9D4A827D4713BAEBB8`.
The conflict expected version begins with `0` and otherwise equals it.

Grammar goldens use POSIX `/` spelling independent of the executing host; they
do not call native `os.path.join` or pass this fixture root through the public
Windows path validator. The exact staging parent is
`/tmp/uprime-2b2f/docs/experiments/artifacts/uprime_u1_rpc_staging/` followed
by the fixture license ID. The stage is that parent followed by
`/uprime-rpc-fake-cas-stage-v1-fd03ff359d185db3f748e046211c7c4a.bin`.
The final host path is `/tmp/uprime-2b2f/` followed by the repository path, and
the alias is the staging parent followed by
`/uprime-rpc-attempt-manifest-stage-v1-6a20df3130322cebadcc96df7c9d29c1.json`.
Production continues to use native joins as frozen in Section 5.

The residue fixture is `conflict_pre`, parent `present` with
`(stable_parent_directory,)`, child `absent` with
`(absent_at_both_points,)`, null observed bytes/hash, relation `not_present`,
and expected proposal `b"B"`. The active inventory uses 123 event bytes, one
`seed_and_local/exact_match/valid_nonterminal` claim, receipt hashes `R_4`,
last hash `R_5`, and the exact active aggregate from Section 6. The active
chain uses receipt `R_3`, first/last `R_5`, 123 event bytes, and timestamp
`2026-07-11T00:00:00.000000Z`.

The artifact fixture has parent `absent` with `(stable_parent_absence,)` and
three parent-derived absent rows with null hash/bytes. In reservation/ledger/
report order, their exact paths and limits are:

```text
runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.json.reservation
  1,048,576
runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.responses.jsonl
  134,217,728
runs/uprime_u1_rpc_20260710/rpc_diagnostic_aaaaaaaaaaaa.json
  16,777,216
```

Counts are present/absent/indeterminate `0/3/0`, total bytes zero, and
`snapshot_scope=sequential_per_artifact_not_atomic_bundle`. The terminal
fixture has count 2, first `R_5`, last/event `R_30`, type `recovery`, and
`("OTHER_HARNESS_ERROR",)`.

For append, use event/marker/terminal `R_30/R_40/R_50`, the derived manifest
nonce and exact Section-5 paths, event size 321, the frozen append status, and
counts `1/2/1/1/2`. Conflict TRACE is `publish / cas_conflict_no_marker /
(expected_state_version_mismatch,)`, action/before/after
`R_10/R_11/R_12`, false state change, publisher operation/transition
`R_13/R_14`, and all other optionals null; final snapshot is
`R_15`, post-stage projection `R_60`, and final inventory equals the active
inventory projection.

The standalone recovery-CAS fixture uses endpoint `recovery`, common
initial/expected version and proposal, null alternate, publisher operation/
transition `R_13/R_14`, synthetic-fault transition `R_30`, and marker `R_40`.

The four recovery traces are exactly:

```text
publish / synthetic_marker_committed_result_withheld /
  (synthetic_marker_committed,) / action-before-after R20/R21/R22 /
  changed true / publisher hashes null / marker R40 / all later optionals null

acquire_epoch / epoch_issued / (recovery_marker_pending,) /
  R23/R22/R24 / changed true / publisher hashes null / marker R40 /
  epoch 1 / replay, terminal, purpose null

replay_epoch / replay_confirmed_recovered /
  (synthetic_intended_transition_confirmed,) / R25/R24/R26 / changed true /
  publisher hashes null / marker R40 / epoch 1 /
  replay confirmed_intended / terminal R50 / purpose record_recovered_terminal

consume_witness / witness_consumed / (witness_consumed,) / R27/R26/R28 /
  changed true / publisher hashes null / marker R40 / epoch 1 / replay null /
  terminal R50 / purpose record_recovered_terminal
```

The binding fixture additionally uses CAS
projection `R_61`, witness `R_29`, pre-publish/preappend/postappend stage
projections all `R_60`, the
artifact fixture at both endpoints, the active inventory at the final slot,
and the exact success labels in Sections 8--10. The recovery audit's
pre-publish observation is the residue fixture, preconsume/final lifecycles are
`RECOVERED_WITNESS_LIVE/RECOVERED_WITNESS_SPENT`, and its initial/expected
versions are the common initial value. These combinations are framing goldens,
not claims that arbitrary `R_n` records are semantically reachable.

The independently calculated goldens are:

| fixture | preimage bytes | expected uppercase SHA-256 |
|---|---:|---|
| publisher nonce full digest | 162 | `FD03FF359D185DB3F748E046211C7C4A0BC184C9E256CF87F3A03B9D37C0492E` |
| manifest nonce full digest | 163 | `6A20DF3130322CEBADCC96DF7C9D29C19382D64DEF09D752AF43A5E3E2225CFA` |
| residue observation | 627 | `CFA7725FA3B5EE2144129C411207F2E58B25B2EED031EE2FF41A03F16C638009` |
| inventory projection | 413 | `1D233C9F36F64366BC2883C199AC7EFE05049B257B124F496A6C5A4CADDC1118` |
| active-chain projection | 282 | `4D8E3C26E565C0E74556E1F8BD9DC385696ABFD050DC5F78918FB78A23EC6B6C` |
| artifact projection | 587 | `03B14D6282B1E95BF4E8323AD3936FC5999CDBF63EA3EEC35CBAD23439CFA5F9` |
| terminal-attestation projection | 279 | `4C1DCEDEA89EB344ED49DD4306EDEE0C43C88F6EBBF0FBDE06FD37531304CC18` |
| append | 741 | `E3CDCD0A2220488C9023E645EB7B381D0EF058F877F988BAD4149359C3BA01DC` |
| conflict CAS | 248 | `43A905BC01DB88CD057FFC74BE2AA8A0B2AC87CAB3248205804F095A4C0700F7` |
| recovery CAS | 312 | `87E9D0C659F6879AAF9B0420F3D4460B25317E5A62B732A9D1697BFC5FB14AD5` |
| conflict audit | 1,412 | `053361307795DD652C20CE91D295173352CF915D1F989C902D7795E980DB5ADB` |
| manifest binding | 1,495 | `FF8D4C6F9D21C8BCFCD43FE0EA4033C44B7EFEFEC49EA2801803EE3A3CD9FFC0` |
| recovery audit | 3,077 | `9A684A837778C33892D08C3C2014C26E7CA9E7237E6F4B116511681A4963CA4F` |

The nonce labels from the first two fixtures are respectively
`fd03ff359d185db3f748e046211c7c4a` and
`6a20df3130322cebadcc96df7c9d29c1`.

## 13. Exact aggregate resource and capability boundary

The aggregate field has one narrow accounting definition. It sums dependency
declared filesystem/event payload-work bounds, twice-returned bytes plus one
logical endpoint-sentinel unit for each direct Phase-2b1 inspection, and the
Phase-2b2f observer/writer logical EOF unit. It
does not claim total CPU byte touches, hash scans, seed parsing, canonical JSON
allocation, metadata calls, Python object memory, or elapsed work.

Let:

```text
I = one Phase-2b2a inventory declared event read-work bound
  = 268,435,457

A = one Phase-2b2b artifact-observer declared payload-work bound
  = 304,087,043

C = one direct Phase-2b1 inspection/verifier maximum returned event bytes
    plus one logical endpoint-sentinel unit
  = 2 * 67,108,864 + 1
  = 134,217,729

S = one Phase-2b2f stage observation, including one logical EOF unit
  = 2 * 1,048,576 + 1
  = 2,097,153

P = the nested successful changed Phase-2b2d filesystem payload work
  = 2,097,152

M = one Phase-2b2f manifest append, including one logical EOF unit
  = 2 * 1,048,576 + 1
  = 2,097,153
```

Conflict uses two inventories, one artifact observation, one direct active
inspection, and two stage observations:

```text
2I + A + C + 2S
= 536,870,914 + 304,087,043 + 134,217,729 + 4,194,306
= 979,369,992
```

Recovery uses two inventories, two artifact observations, one direct active
inspection, one terminal verifier, three stage observations, one nested
Phase-2b2d changed publisher, and one manifest append:

```text
2I + 2A + 2C + 3S + P + M
= 536,870,914 + 608,174,086 + 268,435,458 + 6,291,459
  + 2,097,152 + 2,097,153
= 1,423,966,222
```

The corresponding public fields are exact integers:

| resource | conflict | recovery |
|---|---:|---:|
| `max_seed_claims` | implicit 1 | 1 |
| `max_chain_events` | implicit 1 | 2 |
| `max_inventory_audits` | 2 | 2 |
| `max_artifact_observations` | 1 | 2 |
| direct Phase-2b1 inspections/verifiers | 1 | 2 |
| `max_stage_observations` | 2 | 3 |
| `max_coordinator_actions` | implicit 1 | 10 |
| `max_recovery_epochs` | implicit 0 | 4 |
| `max_manifest_appends` | implicit 0 | 1 |
| aggregate payload-work field | 979,369,992 | 1,423,966,222 |

Two inventory calls advertise at most 319,968 logical Phase-2b1 event-file
admissions. Direct Phase-2b1 event admissions are at most 9,999 for conflict
and 19,998 for recovery. Stage-observer read-call bounds are 68 and 102.
Artifact-observer read-call bounds are 4,646 and 9,292. These are conservative
compositional bounds; the exact one/two-event success fixture is much smaller.

The recovery record freezes
`coordinator_payload_reference_upper_bound_bytes=3,145,728` and
`proposal_payload_copy_upper_bound_bytes=0`, inheriting Phase-2b2e's maximum
current/proposal/alternate reference accounting. This is not a global memory
peak and excludes canonical terminal-event bytes and transient 65,536-byte
read buffers. No raw payload, event bytes, Result, State, Action, Epoch,
Witness, Marker handle, Coordinator, or open descriptor is retained by either
returned top-level audit.

There is one coordinator, one marker, one live/spent witness, at most four
epochs, one Phase-2b2d owned publish, one publisher-stage create, one manifest
temp create, and one hardlink. There is no loop over an unbounded namespace,
no retry/reconcile loop, no sleep/clock/random source, no hidden registry or
journal, and no unlink. All tests create filesystem fixtures only below
`tmp_path`.

## 14. Finite acceptance matrix and explicit mutant kills

The future support module contains exactly 64 collected tests. Direct support,
the frozen four-file M2b profile, rerun-license/tier tests, and default
collection must all pass with zero failures/errors; the frozen profile has
zero skips and xfails on local Windows CPU. Hosted Ubuntu CI must also be
green.

Selective evidence is closed by this exact ordered case manifest:

```text
s01_public_surface
s02_positional_signatures
s03_record_arities
s04_constructor_type_domains
s05_false_authority_cells
s06_constructor_zero_io
s07_import_allowlist
s08_prereg_tree_absence_and_anchor
p01_root_exact_utf8
p02_windows_path_grammar
p03_derived_path_bounds
p04_parent_type_and_same_device
p05_profile_alternate_matrix
p06_payload_boundaries
p07_nonce_and_path_derivation
p08_no_caller_records_or_handles
h01_domain_lengths
h02_nonce_goldens
h03_residue_golden
h04_inventory_chain_goldens
h05_artifact_terminal_goldens
h06_append_and_cas_goldens
h07_conflict_audit_golden
h08_binding_recovery_goldens
i01_exact_one_seed_receipt
i02_active_inventory_endpoint
i03_invalid_namespace_preflight
i04_exact_index1_chain
i05_stage_stable_absence
i06_stage_stable_exact_payload
i07_stage_indeterminate_and_raw_equality
i08_artifact_all_absent_only
c01_conflict_exact_endpoint
c02_conflict_physical_zero_write
c03_conflict_projection_binding
c04_ack_loss_confirmed_trace
c05_unavailable_then_confirmed_trace
c06_unavailable_budget_trace
c07_wrong_delta_trace
c08_snapshot_continuity_and_terminal_purpose
m01_terminal_event_mapping
m02_canonical_encode_parse_lf
m03_temp_exclusive_partial_writes
m04_readback_seek_eof
m05_alias_close_and_identity
m06_final_hardlink_endpoint
m07_preplay_and_concurrent_collision
m08_terminal_attestation_inventory
w01_witness_order_last_mutation
w02_foreign_and_copied_witness
w03_block_is_not_success
w04_precreate_failure_cuts
w05_temp_residue_failure_cuts
w06_link_perform_then_raise_cut
w07_postlink_preconsume_cuts
w08_postconsume_construction_cut
g01_sanitized_errors_and_baseexception
g02_aggregate_resource_arithmetic
g03_payload_reference_and_copy_scope
g04_no_cleanup_fsync_or_retry
g05_forbidden_capability_sentinels
g06_tmp_only_and_repo_unchanged
g07_windows_real_filesystem_profiles
g08_gate_ancestry_allowed_diff_and_stop_rule
```

The exact five-cell matrix is the following pipe-delimited ASCII table. Its
header is not a case row; `none` means no mutation beyond pure local values:

```text
case_id|obligation|killed_mutant|expected_outcome|expected_side_effects
s01_public_surface|exact ordered production surface|extra_missing_or_reordered_export|surface_exact|none
s02_positional_signatures|two exact positional_only signatures|caller_control_parameter_added|signature_exact|none
s03_record_arities|ordered fields 39_23_39_58_88|field_added_removed_or_reordered|arity_exact|none
s04_constructor_type_domains|exact types nullable domains bool_not_int|coercion_or_subclass_accepted|typed_rejection|none
s05_false_authority_cells|all authority and license booleans false|authority_flag_upgraded|constructor_rejection|none
s06_constructor_zero_io|record constructors are pure|constructor_stats_or_calls_dependency|pure_construction|none
s07_import_allowlist|only exact public symbol allowlist|private_or_publisher_symbol_imported|ast_rejection|none
s08_prereg_tree_absence_and_anchor|prereg tree lacks future files and anchor occurs once|implementation_preplayed_or_anchor_duplicated|git_tree_gate_pass|read_only
p01_root_exact_utf8|root exact normalized strict_utf8 absolute|coerced_surrogate_or_relative_root|preflight_rejection|none
p02_windows_path_grammar|drive_root and no UNC_device_current_drive|unsafe_windows_spelling_accepted|preflight_rejection|none
p03_derived_path_bounds|each early and late path checks own bound|root_limit_substituted_for_derived_limit|preflight_or_precreate_rejection|none
p04_parent_type_and_same_device|attempt and staging parents real nonreparse same_device|cross_device_or_reparse_parent_accepted|preflight_rejection|read_only
p05_profile_alternate_matrix|four profiles and wrong_delta alternate only|normal_or_bad_alternate_accepted|preflight_rejection|none
p06_payload_boundaries|proposal and alternate inclusive 1MiB bounds|oversize_or_nonbytes_payload_accepted|preflight_rejection|none
p07_nonce_and_path_derivation|nonces and paths use frozen inputs once|caller_nonce_or_unbound_path_used|derivation_exact|none
p08_no_caller_records_or_handles|caller cannot supply receipt_state_action_marker_witness|authority_parameter_added|signature_rejection|none
h01_domain_lengths|twelve exact NUL domains and lengths|domain_swap_or_missing_NUL|golden_match|none
h02_nonce_goldens|publisher and manifest nonce formulas|tag_length_order_or_case_mutated|golden_match|none
h03_residue_golden|residue projection exact order|observation_cell_omitted_or_swapped|golden_match|none
h04_inventory_chain_goldens|one_claim inventory and chain projections|claim_or_timestamp_cell_unbound|golden_match|none
h05_artifact_terminal_goldens|AAA artifact and terminal projections|row_order_or_failure_tuple_unbound|golden_match|none
h06_append_and_cas_goldens|append plus conflict_recovery CAS domains|endpoint_kind_or_path_count_unbound|golden_match|none
h07_conflict_audit_golden|conflict top_level dynamic order|trace_or_stage_endpoint_omitted|golden_match|none
h08_binding_recovery_goldens|manifest binding and recovery audit order|preappend_stage_or_consume_trace_omitted|golden_match|none
i01_exact_one_seed_receipt|seed parses canonically with one receipt|zero_multiple_or_detached_receipt_accepted|preflight_rejection|read_only
i02_active_inventory_endpoint|exact one active nonterminal aggregate|matched_terminal_required_prewrite|active_endpoint_accept|read_only
i03_invalid_namespace_preflight|orphan_unexpected_mismatch_drift reject|invalid_namespace_reaches_mutation|preflight_rejection|read_only
i04_exact_index1_chain|sole canonical claim_started index1|terminal_multi_event_or_bad_prior_accepted|preflight_rejection|read_only
i05_stage_stable_absence|prepublish and conflict rows stable absent|one_point_absence_called_stable|observation_rejection|read_only
i06_stage_stable_exact_payload|two passes raw_equal and stable metadata|digest_only_or_one_pass_acceptance|exact_present_observation|read_only
i07_stage_indeterminate_and_raw_equality|seek_read_eof_drift reasons fail_closed|same_digest_distinct_bytes_or_drift_accepted|indeterminate_or_different|read_only
i08_artifact_all_absent_only|only exact AAA vector is write_admissible|present_or_indeterminate_mapped_false|append_gate_rejection|read_only
c01_conflict_exact_endpoint|stale_expected gives exact conflict action|conflict_relabelled_collision_or_poison|conflict_audit_return|read_only
c02_conflict_physical_zero_write|conflict reaches no stage or manifest writer|physical_write_on_conflict|conflict_audit_return|stage_absent_manifest_absent
c03_conflict_projection_binding|result operation_transition and OPEN bind|publisher_result_hashes_dropped|binding_exact|read_only
c04_ack_loss_confirmed_trace|exact publish_acquire_confirm_consume trace|trace_row_skipped_or_reordered|four_actions_exact|stage_and_manifest_retained
c05_unavailable_then_confirmed_trace|exact two_epoch confirmation trace|unavailable_cursor_or_ordinal_mutated|six_actions_exact|stage_and_manifest_retained
c06_unavailable_budget_trace|four unavailable epochs then block consume|fifth_epoch_or_recovered_upgrade|ten_actions_exact|stage_and_manifest_retained
c07_wrong_delta_trace|confirmed wrong_delta yields block witness|wrong_delta_called_recovered|four_actions_exact|stage_and_manifest_retained
c08_snapshot_continuity_and_terminal_purpose|adjacent snapshots and purposes chain|detached_noncontiguous_trace_accepted|continuity_exact|none
m01_terminal_event_mapping|exact index2 recovery mapping|code_timestamp_receipt_or_prior_relabelled|event_exact|none
m02_canonical_encode_parse_lf|public encoder parser and LF inclusive hash|manual_JSON_or_LF_omitted|canonical_roundtrip|none
m03_temp_exclusive_partial_writes|O_EXCL mode600 positive bounded writes|overwrite_or_zero_write_accepted|append_progress_or_error|alias_may_remain
m04_readback_seek_eof|seek0 exact chunks raw readback EOF|short_read_growth_or_no_seek_accepted|append_progress_or_error|alias_may_remain
m05_alias_close_and_identity|close then nofollow alias identity|close_error_or_alias_swap_ignored|append_progress_or_error|alias_may_remain
m06_final_hardlink_endpoint|one nooverwrite link and postlink comparator|rename_copy_or_full_ctime_equality_used|append_exact|two_aliases_retained
m07_preplay_and_concurrent_collision|existing_or_concurrent final never adopted|exact_preplay_adopted_or_overwritten|hard_failure|no_cleanup_no_consume
m08_terminal_attestation_inventory|verifier and final matched_terminal bind event2|favorable_partial_endpoint_accepted|terminal_endpoint_exact|two_aliases_retained
w01_witness_order_last_mutation|consume follows every read and mutation|consume_moved_before_endpoint|ordered_success|witness_spent_last
w02_foreign_and_copied_witness|only internal same_instance handle consumed|hash_equal_foreign_witness_consumed|hard_failure|no_consume
w03_block_is_not_success|permanent_block purpose never recovered|block_witness_upgraded|block_record_only|no_success_authority
w04_precreate_failure_cuts|failure before alias create appends nothing|precreate_failure_retried_or_appended|mapped_error|stage_may_remain
w05_temp_residue_failure_cuts|temp failures retain residue without cleanup|partial_alias_deleted_or_adopted|mapped_error|alias_may_remain_no_consume
w06_link_perform_then_raise_cut|link invoked unconfirmed never upgrades|perform_then_raise_called_success|mapped_error|final_may_remain_no_consume
w07_postlink_preconsume_cuts|postlink verification failure does not consume|terminal_or_inventory_failure_consumes|mapped_error|final_and_alias_may_remain
w08_postconsume_construction_cut|postconsume pure failure exposes no retry claim|spent_witness_rolled_back_or_retry_enabled|mapped_error|final_retained_witness_spent
g01_sanitized_errors_and_baseexception|ordinary errors sanitized and BaseException identity kept|same_class_secret_leak_or_primary_masked|exact_error_policy|no_cleanup
g02_aggregate_resource_arithmetic|exact 979369992 and 1423966222 aggregate bounds|hidden_extra_call_or_off_by_one|arithmetic_exact|none
g03_payload_reference_and_copy_scope|coordinator refs 3MiB proposal copies zero|global_memory_claim_or_payload_copy|scope_exact|none
g04_no_cleanup_fsync_or_retry|no unlink_rename_replace_fsync_retry|destructive_or_durability_call|ast_runtime_rejection|residue_retained
g05_forbidden_capability_sentinels|no network_git_lean_worker_registry_gpu|forbidden_import_or_call|ast_runtime_rejection|none
g06_tmp_only_and_repo_unchanged|fixtures only below tmp and protected trees identical|repository_artifact_or_registry_write|tree_gate_pass|repo_unchanged
g07_windows_real_filesystem_profiles|all four profiles and conflict on Windows temp fs|platform_skip_or_fake_only_evidence|zero_skip_pass|tmp_residue_only
g08_gate_ancestry_allowed_diff_and_stop_rule|exact parent_blobs_diff_CI_head_and_Phase2c_only|retroactive_prereg_or_extra_diff_or_wrong_CI_head|governance_gate_pass|no_later_authority
```

The support module must define this exact tuple as `PHASE2B2F_CASE_IDS` and
exactly one collected callable named `test_phase2b2f_<case_id>` for each row,
in the same order, with no other collected callable. Its exact ordered
`CASE_MATRIX` has one row per ID with five nonempty cells:
`(case_id, obligation, killed_mutant, expected_outcome,
expected_side_effects)`. Meta-oracles in the rerun-license tests require a
one-to-one ID/callable/matrix relation, reject a missing/duplicate/extra ID,
and close structural omission while keeping the count at 64. They do not by
themselves prove test-body adequacy. Each row must exercise its frozen mutant
seam and expected side effects; independent adversarial code review and the
recorded 64/64 mutation disposition check semantics. `s08` checks that the
source/support paths are absent from the preregistration Git tree and that its
amendment blob is anchored exactly once, not that they remain absent at the
later implementation head. The result record reports every row passed; no
aggregate-only score, deselection, skip, or xfail satisfies the gate.

The semantic requirements of those exact rows are:

1. exact imports, ordered `__all__`, one exception, records with
   39/23/39/58/88 ordered fields, two positional-only signatures, raw/resolved
   annotations, future-path anchors, and collector uniqueness;
2. every exact type, bool-as-int, nullable, string, hash, nonce, profile,
   alternate, payload, root, normalized-path, Windows UNC/device/current-drive,
   derived-path, and same-device boundary;
3. every digest domain, tag, tuple/path encoding, projection order, omitted or
   swapped cell, field mutation, and all preregistered numeric goldens;
4. exact one-receipt seed, active one-event inventory/inspection, receipt/hash
   cross-check, and rejection of missing/empty/terminal/multi-event/exhausted,
   unexpected/orphan/mismatch/drift cases before mutation;
5. parent and stage reason precedence, both read passes, EOF, raw equality,
   same-digest/different-byte seam, descriptor/path/parent drift, absent/
   present/different/indeterminate cells, and observation resource bounds;
6. conflict's unequal-version derivation, exact no-stage Result and
   operation/transition binding, OPEN state, null marker/witness, two absence
   observations, one artifact observation, unchanged inventory, and zero
   manifest/writer calls;
7. exact 4/6/10/4 profile traces, ordinals, replay outcomes, terminal kinds,
   witness purposes, no release/abandon/terminal-noop, and ten-action maximum;
8. both admissible Phase-2b2b all-absent parent rows and rejection of every
   present or indeterminate row without mapping it to false;
9. exact index-2 recovery event, copied timestamp, receipt/prior binding,
   canonical LF-inclusive bytes/hash, pure parse, exact live marker failure
   tuple, and refusal of inferred `POWER_LOSS` or manifest-error codes;
10. every manifest writer seam: exclusive flags/mode, positive partial writes,
    size and identity checks, readback/EOF, close, alias no-follow endpoint,
    one no-overwrite hardlink, final same-file identity, actual counts, and no
    fsync/rename/replace/unlink;
11. alias/final preplay, exact-existing and one-byte-different collision,
    concurrent final creation, unavailable hardlink/same-device cases, and no
    adoption, overwrite, retry, reconcile, or cleanup;
12. exact terminal attestation, postappend all-absent artifact vector, exact
    publisher stage, matched-terminal inventory, and negative completeness/
    authority scopes;
13. seam-log proof that all reads/verifications precede exact same-instance
    witness consumption, consume is the last dependency mutation, block is not
    success, and the final Action is last in the trace;
14. every failure cut in Section 11, sanitized ordinary errors, exact
    non-`Exception` preservation, close without masking, no partial result,
    and the explicit live/spent lost-witness nonclaims;
15. exact aggregate arithmetic, call/admission/action/epoch/create/link bounds,
    no payload copy or output-retained live object, and no unbounded history;
16. invalid or stale-cell record construction and `dataclasses.replace` cases
    reject unless every dependent hash/invariant is coherently recomputed;
    coherent records remain forgeable; constructor I/O is zero, detached hashes
    have no authority, and no public input accepts any receipt, State, Result,
    Action, Marker, Epoch, Witness, path plan, code, or audit;
17. AST/runtime sentinels permit only the exact Phase-2b2d Result-constructor
    import and forbid the Phase-2b2d publisher-function import/call, all private
    dependency names, time/random/PID/thread entropy, mkdir/cleanup,
    subprocess/network/Git/Lean/
    worker/registry/rerun/registered-run/SSH/GPU/later-stage capability; and
18. real Windows temp-directory hardlink/profile fixtures, unchanged repository
    artifact/runs/exposure/rerun-registry trees, zero repository writes, and
    green Ubuntu CI.

Independent review must kill at least these named attacks:

- a caller-supplied record/handle, a non-value-identical detached dependency
  return, or a foreign epoch/witness drives append; a value-identical return
  remains explicitly unauthenticated rather than claimed distinguishable;
- normal, existing-identical, conflict, or `POISONED_NO_MARKER` appends an
  event or invents a failure code;
- any present or indeterminate artifact becomes a Phase-2b1 false field;
- a favorable preplayed exact event is adopted or attributed to this call;
- a differing event is overwritten, renamed, unlinked, or retried;
- witness consumption moves before create, close, hardlink, terminal verify,
  postappend observations, or final inventory;
- a block witness is called recovered success, or a copied/foreign witness is
  accepted by hash equality;
- the event hash omits LF, timestamp changes, prior/receipt/index drifts, or
  marker failure code is relabeled;
- digest equality replaces raw stage bytes, or marker operation hash is called
  an invertible proof of stage path/origin;
- root and stage use different roots, native separators leak into repository
  path, or an ancestor/final-component race is called prevented;
- inventory `matched_terminal` becomes real completeness or seed omission
  detectability;
- hardlink becomes durability, immutability, canonical publication, or
  manifest/witness atomicity;
- cleanup masks a primary `BaseException`, postlink failure restores a clean
  prewrite claim, or postconsume construction failure enables retry;
- a dependency-injected same-class exception bypasses sanitized cut mapping;
- a hidden second artifact/inventory/inspection/publish/append/replay call
  exceeds the frozen sum; and
- implementation appears before this preregistration commit is pushed and its
  hosted CI is green.

## 15. Governance stop rule

This amendment commit contains only this document, its litmus anchor, and the
executable future-file/collector absence sentinel. It does not contain either
future implementation file. Only these three literal paths may be staged;
`git add -A`, `git add .`, and `git commit -a` are forbidden. Existing changes
to `docs/external/SHA256SUMS` and unrelated untracked external, LLM, pilot, or
smoke-task files remain unstaged and outside this phase.

Commit, push, and green hosted CI of this reviewed amendment license only the
exact Phase-2b2f source, 64-test support matrix, one collector import, and
source/support anchor wiring on local Windows CPU. The implementation commit
must have the green preregistration commit as its exact parent, preserve this
document's Git blob byte-identically, and change exactly these five paths:

```text
lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py
tests/uprime_rpc_integrated_synthetic_manifest_cases.py
tests/test_uprime_rpc_ledger.py
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

The collector change is exactly one import. The litmus change adds only the
source/support anchors. The rerun-license change converts the absence sentinel
to exact presence/anchor/one-to-one 64-row matrix enforcement. No amendment or
earlier result anchor may change. The rerun registry, package initializers,
tier manifest, complete `runs/` tree, every exposure marker, and every path
outside the five-path allowlist remain byte/tree-identical to the prereg
commit. The implementation commit must itself be pushed and green, and the
hosted run/job head SHA must equal that exact commit.

A separate execution record then freezes the prereg commit and amendment blob,
the exact implementation parent/commit, the five-path allowed diff, source and
support SHA-256/Git blobs, collector/litmus/rerun-test blobs, unchanged
registry/init/tier/runs/exposure hashes, Windows zero-skip 64-row evidence,
adversarial-review disposition, frozen-profile and default collection, and the
implementation hosted run/job/head SHA. The result commit has the green
implementation commit as its exact parent and changes only that result
document, its litmus result anchor, and rerun anchor-membership test;
it preserves prereg and implementation blobs, is pushed, and must itself have
green hosted CI at its exact head.

Only those gates complete Phase 2b2f and license **Phase-2c preregistration
only**. They do not license Phase-2c implementation. Reservation writing,
durable claims, fsync, worker order, real/canonical publication, cleanup,
registered runs, canonical diagnostic, M2c, U'0.5, U'2--U'5, network/SSH,
Lean, workers, GPU construction, real recovery, and later-stage execution
remain barred.
