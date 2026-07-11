# U'1 evidence milestone 2b phase 2b2e execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. SAME-PROCESS SYNTHETIC-COORDINATOR EVIDENCE
AND NEGATIVE AUTHORITY ONLY. NO REAL OR CANONICAL PUBLICATION, REMOTE CAS,
DURABLE JOURNAL, CRASH/POWER-LOSS CAUSALITY, RESTART RECOVERY, CLEANUP,
MANIFEST, EXECUTION, LEAN, NETWORK, WORKER, REGISTERED RUN, RERUN, LATER-STAGE,
OR GPU AUTHORITY.

## Gate and exact artifacts

Phase 2b2e was preregistered before implementation in commit
`0f9a590e046262ed77cfcb9869fd5be98761dae7`. That commit was pushed and its
Ubuntu CI run `29145534807`, job `86526345546`, completed successfully before
either future implementation file existed.

The implementation commit is
`d726e8120217eb731e4caf854ea1df9242270bd4`. It was pushed before this record
was drafted, and Ubuntu CI run `29147226783`, job `86530730017`, completed
successfully at that exact head.

The exact Git blobs at the implementation commit are:

| artifact | blob |
|---|---|
| Phase-2b2e amendment | `9753b3c5172b22a850d5ed9b6f40c92d9c9b1e90` |
| source | `00c2cea51ff794b9da6b3de9cbf1addf53f70c4e` |
| explicit support | `a184768faadf29671e798f66bf83a0ce6a340fff` |
| anchor source | `6b3b0903529adaf7e9b178f373cc38b1727d03f8` |
| rerun-license/anchor test | `8b5e8561c4ef5c12882d13a9b0779c837aebc94c` |
| collector | `e8ed9ccd57a3eac1700ad643ce3e433a1882efd5` |

The amendment SHA-256 is
`B377BCF96C75A708C52515CDD3F4CE4C9AEB20FE69C5C84998EA1E1D721642D0`.
The implementation SHA-256 values are:

| artifact | SHA-256 |
|---|---|
| source | `B6C83CC4BF63A0D18DD9CDDEFBE89837BA3102943F17E3C256658CE17CE20DAD` |
| explicit support | `4717493CF0FFC30187E1FA59042B420C32CBB333140691BBB785F2F6F5A9ACD4` |

The implementation paths are:

```text
lean_rgc/evals/uprime_rpc_synthetic_recovery_coordinator.py
tests/uprime_rpc_synthetic_recovery_coordinator_cases.py
```

The support module exports 56 unique ordered test functions. The collector
imports it exactly once. The amendment, source, support, collector, and this
result record are anchored; the result path is introduced only by this result
commit.

The implementation diff changed exactly the five implementation, support,
collector, anchor, and anchor-test paths listed above. The default-deny rerun
registry remained blob `13ffca6de484effc66f0e628d2e46823277271c6`;
`lean_rgc/__init__.py`, `lean_rgc/evals/__init__.py`, and
`tests/tier_manifest.json` remained blobs
`4923b84a3d3736a6a0cf9bca5191439538168141`,
`913bd40594449b454740e656e32acb42ab478ad8`, and
`39bb37eabbba80101e4ee6a07f2d1a8d8ecc0931`. No `runs/` or exposure record
changed.

## Implemented contract

The public surface is exactly one exception, six record/opaque/coordinator
types, and eight positional-only operations:

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

The constructor freezes exactly five caller-selected synthetic profiles:

```text
normal
ack_loss_confirmed
ack_loss_unavailable_then_confirmed
ack_loss_unavailable_until_budget_block
wrong_delta_confirmed
```

One exact same-process coordinator owns each Phase-2b2d call it starts, with at
most one such call in flight for that coordinator. It retains one
`threading.Lock`, one in-memory marker slot, at most one active epoch, at most
four issued epoch ordinals, and one witness identity. Its exact lifecycle
domain is:

```text
OPEN
PUBLISHING
RECOVERY_PENDING
RECOVERY_ACTIVE
RECOVERED_WITNESS_LIVE
RECOVERED_WITNESS_SPENT
BLOCKED_WITNESS_LIVE
BLOCKED_WITNESS_SPENT
POISONED_NO_MARKER
```

The coordinator reconstructs one private exact Phase-2b2c State, independently
derives the normal/profile transitions, and passes that same snapshot to the
owned Phase-2b2d call. A complete returned Phase-2b2d Result is reconstructed
before exposure. An exact normal changed result is exposed without a marker;
an exact nonnormal changed result commits one synthetic marker and withholds
the Result. Changed-call uncertainty and post-result endpoint failure are
fail-closed into `POISONED_NO_MARKER`.

The marker carries only the frozen synthetic failure tuple
`("OTHER_HARNESS_ERROR",)`. No profile emits or authenticates `POWER_LOSS`,
`CLAIM_STARTED_MANIFEST_ERROR`, `FINAL_MANIFEST_ERROR`, or a real attempt
cause. Replay is a bounded lookup in the precomputed same-kernel plan. It does
not re-enter the CAS or publisher and does not reobserve a stage or remote
state.

Release and abandonment consume epoch ordinals without advancing the replay
cursor. Ordinals 1--3 return to pending; an unresolved release, abandonment,
or unavailable replay at ordinal 4 enters the permanent-block terminal. An
intended confirmation enters the recovered terminal, and a wrong-delta
confirmation enters the permanent-block terminal. Each terminal creates one
same-instance witness, and exact identity plus expected purpose/hash permits
one transition from live to spent.

Marker, Snapshot, and Action records and all deterministic hashes remain
forgeable value data. A detached Action shallowly checks only the exact nested
Phase-2b2d Result type and its referenced operation hash; production publish
performs the full Result reconstruction. Every operation requires the exact
live Coordinator reference. Handle-bearing methods additionally require an
opaque Epoch or Witness reference the caller already received, the exact
retained object, and its issuer identity.

No filesystem cleanup, manifest write, fsync, durable journal, restart
reconstruction, stage reobservation, remote publication, network call, worker
action, registered execution, Lean invocation, or GPU construction was added.

## Adversarial review disposition

Three independent lenses approved the exact preregistration before its commit.
Implementation review then attacked reachable-state semantics, detached-record
coherence, private-state binding, resource accounting, exception windows, and
governance/collection boundaries. The following substantive gaps were found
and repaired before the implementation commit:

1. coherently rehashed terminal Snapshots could encode profile-unreachable
   replay cursors, and active/terminal epoch nonce cells accepted arbitrary
   uppercase hashes;
2. Action rows were not bound to after-snapshot lifecycle, epoch ordinal,
   replay cursor, or issued-handle digests, so a no-marker no-op could be
   relabeled as a publishing exclusion and an issued ordinal could be changed;
3. private coordinator state did not bind the retained alternate summary or
   replay rows back to the fixed config/marker plan;
4. a coherently rehashed marker could erase the required changed transition by
   setting its before-state version equal to an after-state version;
5. the four-row unavailable-until-budget profile accepted four equal but
   distinct Transition objects, violating the deliberately shared reference
   and retained-object bound; and
6. conflict versus existing-identical disagreement between preclassification
   and a fully reconstructed no-stage Result reopened the coordinator even
   though the frozen final rule permits `OPEN` only for the same no-stage row.

The repaired implementation validates exact profile/cursor terminal
reachability; derives active and terminal nonces; binds Action rows and opaque
handle scalars; checks private alternate/plan summaries; preserves one shared
unavailable Transition reference; and requires before-state version inequality
for every marker-bearing changed row.

For the section-10 tension between category-level no-stage reopening and the
narrower same-row rule, implementation adopts the stricter frozen rule: a
fully reconstructed conflict/existing-identical cross-row mismatch is poisoned.
A pre-return failure on a preclassified contractual no-stage branch still
restores `OPEN`, and postprocessing failure after an agreeing exact no-stage
Result also restores `OPEN`.

The final source/support pair passed two independent post-repair reviews at the
SHA-256 values above. The matrix lens confirmed 56 definitions and 56 ordered
exports with no duplicates, direct and collector execution, exact literals,
coupled-rehash rejection, concurrency oracles, resource bounds, and negative
capability scope. The runtime lens independently reran all 56 direct tests plus
targeted mismatch, replay-identity, fourth-replay, resource, and call-bound
probes and found no remaining blocker.

## Local Windows verification

Local verification used Windows `10.0.26200.0` and CPython `3.13.7` on the
implementation tree:

1. source/support bytecode compilation and whitespace checks succeeded;
2. direct explicit support completed with **56 passed** in 4.31 seconds;
3. collector selection completed with **56 passed, 1,754 deselected** in 7.42
   seconds, with the same nodes collected exactly once;
4. rerun-license and tier-manifest verification completed with **30 passed**
   in 17.79 seconds;
5. runtime-boundary validation completed with **12 modules, 234 files**;
6. the dead-candidate ledger completed with **8 modules**; and
7. the exact frozen four-file M2b profile completed with **1,882 passed**, zero
   failures/errors/skips/xfails, in 338.19 seconds.

The exact frozen command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

Phase-2b2e tests used only synthetic values, deterministic thread schedules,
and Phase-2b2d fixtures under pytest `tmp_path`. They contacted no network or
SSH host, used no GPU, invoked no Lean process, and consumed no registered task
or canonical-run result. A local default-suite claim is deliberately not made;
the frozen profile and explicit slices above are the complete local evidence.

## Ubuntu CI verification

The preregistration CI run `29145534807`, job `86526345546`, used GitHub
Actions runner `2.335.1`, Ubuntu 24.04 image `20260705.232.1`, and CPython
`3.11.15`. It reported runtime boundary **12 modules, 233 files**,
dead-candidate ledger **8 modules**, and **2,132 passed, 4 skipped, 163
deselected in 78.79 seconds**. The job concluded successfully.

The implementation CI run `29147226783`, job `86530730017`, used GitHub
Actions runner `2.335.1`, Ubuntu 24.04 image `20260705.232.1`, and CPython
`3.11.15`. It reported:

- runtime boundary: **12 modules, 234 files**;
- dead-candidate ledger: **8 modules**;
- default suite: **2,188 passed, 4 skipped, 163 deselected in 86.88 seconds**;
  and
- job conclusion: **success** in 1 minute 44 seconds.

The pass-count increase is exactly the 56 exported Phase-2b2e tests; hosted
skip and deselection counts were unchanged. The sole hosted-job annotation was
the Node 20 deprecation for actions forced onto Node 24; it did not alter the
Python result.

## Exact conclusion and remaining limits

Phase 2b2e establishes, under the finite Windows/Ubuntu oracle above, that one
live same-process coordinator can serialize the frozen synthetic publisher,
marker, epoch, bounded replay, terminal, and single-use witness state machine.
It establishes exact public row/hash consistency, same-instance handle checks,
fail-closed changed-result adjudication, bounded in-memory coordinator slots
and replay objects, lock-local linearization observations, and
negative-authority labels for those synthetic paths.

It does **not** establish that a profile corresponds to a real crash, power
loss, acknowledgement loss, remote state, or filesystem cause. It does not
establish that a detached Marker, Snapshot, or Action proves an operation; that
a retained stage still exists or is safe to remove; or that the in-memory slot
survives restart. It provides no authenticated identity, entropy, durable
journal, attempt completeness, artifact/archive binding, manifest, cleanup,
real recovery, global or cross-process exclusion, real/canonical publication,
reservation, worker ordering, execution, model-quality, Lean, network, SSH,
registered-run, rerun, or GPU claim.

Only commit and push of this result record plus its result-anchor wiring,
followed by green CI for that result commit, completes Phase 2b2e and licenses
Phase 2b2f **preregistration only** for the integrated synthetic manifest
writer, stage/marker/CAS/Phase-2b1-chain binding, artifact/no-follow
observations, conflict-without-marker audit, exact frozen failure-code
serialization, residue classification, and witness-consumption integration.

Until all three result-gate conditions hold, Phase 2b2f preregistration remains
barred. Phase 2b2f implementation, Phase 2c reservation writer/preflight,
fsync/durable-claim semantics, worker ordering, real/canonical publication,
registered runs, canonical diagnostic, M2c, U'0.5, U'2--U'5, SSH/network,
Lean, workers, GPU construction, real recovery, and cleanup remain barred in
either case.
