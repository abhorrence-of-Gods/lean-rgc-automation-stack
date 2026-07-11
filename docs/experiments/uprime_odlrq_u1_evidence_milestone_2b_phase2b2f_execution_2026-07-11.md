# U'1 evidence milestone 2b phase 2b2f execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. BOUNDED SAME-CALL SYNTHETIC INTEGRATION AND
NEGATIVE AUTHORITY ONLY. NO DURABLE OR REMOTE CAS, CRASH/POWER-LOSS CAUSALITY,
RESTART RECOVERY, CLEANUP, CANONICAL PUBLICATION, REGISTERED RUN, LEAN, WORKER,
NETWORK, SSH, LATER-STAGE EXECUTION, OR GPU AUTHORITY.

## Gate and exact artifacts

Phase 2b2f was preregistered before implementation in commit
`8f1c0ba42b9c8568e802b79ee8bfc55ac3459a75`, whose sole parent is
`d838d8c4873e04bc649b8551f0545af5d9944c4c`. The preregistration commit was
pushed, and Ubuntu CI run `29149469736`, job `86536514518`, completed
successfully at that exact head before either implementation file existed.

The final implementation commit is
`0a6eb4a92edc1061773c175975f986f0c5ea5a3c`. Its sole parent is the exact
preregistration commit. It changes exactly the five frozen paths:

```text
lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py
tests/uprime_rpc_integrated_synthetic_manifest_cases.py
tests/test_uprime_rpc_ledger.py
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

The exact Git blobs at the implementation commit are:

| artifact | blob |
|---|---|
| Phase-2b2f amendment | `c72d18a17411071f1d1511581978d1b6792761e6` |
| source | `82039799ad79165b4d39bffb38e8fee58bdf3bdc` |
| explicit support | `5b84bd782713efd6815995c09ee2d8a54e9bd594` |
| collector | `69694b9d9e3f2f92c4cd19c17534b2e24f7731cc` |
| anchor source | `445e5d032cfbf178aeda74b9e4f9f2886e9bd78e` |
| rerun-license/anchor test | `d53fea74951bad131e2c2d9ef1754e278907ed05` |

The amendment SHA-256 is
`F3BEDB8019E0A8443BEF97F3DF39BE957CF1E3EC4C9E2AB577B32B36E9454369`.
The implementation SHA-256 values are:

| artifact | SHA-256 |
|---|---|
| source | `0ECFB8597F86546171613F7DA3A63531D86D7E7787F916C99C85A638DE10E812` |
| explicit support | `6BB63EDA1D32BADAD04342E26C398CC3BF95FAF98D7D65A1FDB2444BF08EBCBF` |

Both implementation files are regular Git `100644 blob` entries. The support
module contains 64 unique ordered case IDs, 64 exact five-cell matrix rows, 64
test functions, and 64 ordered `__all__` exports. Direct and collector
collection each found exactly those 64 nodes once.

The default-deny rerun registry remained blob
`13ffca6de484effc66f0e628d2e46823277271c6`; `lean_rgc/__init__.py`,
`lean_rgc/evals/__init__.py`, and `tests/tier_manifest.json` remained blobs
`4923b84a3d3736a6a0cf9bca5191439538168141`,
`913bd40594449b454740e656e32acb42ab478ad8`, and
`39bb37eabbba80101e4ee6a07f2d1a8d8ecc0931`. The exact implementation diff
contains no `runs/`, artifact, exposure-marker, registry, initializer, or tier
path. The test-frozen digest over `docs/experiments/artifacts`, complete local
`runs`, and the rerun registry was
`2F69E3E119CBED3116CAB8FDB4B3CE22DB2D7CEFA3A0970CC616378E6C8A191B`.
That digest includes entry-type tags, regular-file content hashes, and symlink
targets without following them; the before/after mutation sentinels observed
the same digest. The exact tracked exposure-marker inventories at both the
preregistration and implementation heads were empty, and the runtime
before/after inventory over `docs/experiments` and the RPC run namespace was
also empty. Therefore no per-marker hash exists to list.

Unrelated pre-existing working-tree material, including `llm_local.json`,
`pilot_tasks.json`, `fake_lean_smoke.py`, `smoke_tasks_local.jsonl`, external
review artifacts, and `docs/external/SHA256SUMS`, remained unstaged and is not
an input, authority source, or result of Phase 2b2f. Its longer-term
classification is deferred to the next scheduling amendment rather than being
silently absorbed into this evidence record.

## Implemented contract

The public surface is exactly one exception, five frozen record types, and two
positional-only endpoints:

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

The conflict endpoint reconstructs one exact synthetic seed, active one-event
chain, absent generation-zero fake-CAS state, stale expected version, two
sequential publisher-stage absence observations, one all-absent ordinary
artifact observation, and an unchanged final inventory. It returns
`conflict_without_marker_confirmed` only when there is no marker, stage,
manifest, witness, or state change. It calls no manifest encoder, writer,
hardlink, replay, witness, cleanup, registered-run, or later-stage capability.

The recovery endpoint accepts exactly the four frozen Phase-2b2e profiles:

```text
ack_loss_confirmed
ack_loss_unavailable_then_confirmed
ack_loss_unavailable_until_budget_block
wrong_delta_confirmed
```

It performs one same-call sequential transcript with exact action counts
`4/6/10/4`, epoch schedules, replay outcomes, terminal purposes, and snapshot
continuity. It binds one internally obtained marker to the top-level profile,
initial version, proposal bytes/hash, every action-trace marker cell, and three
stage observations. The stage sequence is exactly absent before publish and
exact proposal bytes at pre-append and post-append.

The terminal event is an exact canonical index-2 Phase-2b1 recovery row. One
exclusive temp file is partially written as needed, read back to EOF, and
materialized at the final name by a single no-overwrite hardlink. Both alias
names are deliberately retained. Every observation, artifact projection,
terminal verification, and final inventory check precedes consumption of the
exact same-instance witness. Witness consumption is the last dependency
mutation; only pure record construction and hashing follow it.

The returned values are detached, forgeable scalar projections. Hashes do not
authenticate the origin of an Action, Witness, filesystem object, model,
process, host, or remote state. The implementation performs no fsync, rename,
replace, unlink, cleanup, retry/reconcile loop, durable journal, restart,
network, SSH, worker, registered run, Lean invocation, or GPU construction.

## Adversarial review disposition

Independent implementation lenses attacked the source contract, all 64 matrix
rows, coherent re-hashing, Windows filesystem behavior, and Git governance.
The following defects were found and repaired before the final implementation
commit:

1. no-change fake-CAS transitions did not preserve the required identical
   before/after State object during reconstruction;
2. replay terminal trace nullability predicates were inverted;
3. the recovery audit constructor initially lacked complete exact profile
   operation/epoch/replay scheduling, terminal purpose/SHA, and marker-row
   checks;
4. nested stage observations were called through a missing binding helper, and
   therefore did not reliably bind parent, nonce, path, and proposal cells;
5. a coherently re-hashed marker could differ from the top-level initial
   version or proposal while retaining internally valid marker hashes;
6. Windows pytest paths and long case names could exceed the legacy path limit
   before a short-path alias was established;
7. the governance guard derived its allowlist from mutable litmus constants
   and checked only the first parent rather than requiring one sole parent;
8. the first hosted implementation attempt assumed full Git history even
   though `actions/checkout` supplied a depth-one repository; and
9. the repository sentinel traversed directories but did not hash a standalone
   rerun-registry file, entry types, or symlink targets, and it had no explicit
   tracked/runtime exposure-marker inventory.

The final validators require exact `4/6/10/4` schedules, adjacent snapshots,
profile-specific replay observations and reasons, one marker hash on every
recovery row, terminal replay/consume SHA and purpose equality, exact
live/spent lifecycle labels, top-level terminal reason equality, all nested
stage bindings, and marker profile/initial-version/proposal binding.

A reviewer-session, read-only coherent-mutant campaign exercised 21 re-hashed
variants of a real recovery record. Every mutant that violated a frozen direct
semantic relation was rejected, including epoch, replay, marker, nested-stage,
lifecycle, reason, terminal, manifest-nonce, append, and alias variants. Six
fully rebound scalar graphs remained constructible only where the
preregistration explicitly permits coherent detached forgeability: opaque
action/witness/snapshot hashes, projection hashes, bounded append counters, and
coherently rebound terminal event graphs. None gains authority because every
authority and license boolean remains false. The complete 21/6 exploratory
campaign is session evidence rather than a committed replay artifact; the four
highest-value coupled-rehash attacks are retained as repository regression
assertions.

Regression assertions now retain coherent epoch, trace-marker, foreign-stage,
and foreign-marker rejection inside the existing `s04` case without expanding
or selectively changing the 64-row case inventory.

## Local Windows verification

Local verification used Windows `10.0.26200.0` and CPython `3.13.7` on the
final implementation tree:

1. source/support bytecode compilation and whitespace checks succeeded;
2. direct explicit support completed with **64 passed** in 15.04 seconds;
3. collector selection completed with **64 passed, 1,810 deselected** in 12.38
   seconds, and collect-only found exactly 64 nodes in each path;
4. rerun-license and tier-manifest verification completed with **31 passed**
   in 22.86 seconds;
5. runtime-boundary validation completed with **12 modules, 235 files**;
6. the dead-candidate ledger completed with **8 modules**;
7. an actual depth-one local clone executed the three history-sensitive
   governance tests with **3 passed** in 5.68 seconds; and
8. the exact frozen four-file M2b profile completed with **1,947 passed**, zero
   failures/errors/skips/xfails, in 314.59 seconds.

The exact frozen command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

All public-endpoint fixture effects in the registered tests were confined to
pytest temporary directories; no endpoint wrote to the checked-out repository.
Local verification used no network or SSH host, no GPU, no Lean process, no
worker, no registered task, no canonical run, and no protected benchmark
result.

## Ubuntu CI verification

The preregistration CI run `29149469736`, job `86536514518`, used GitHub
Actions runner `2.335.1`, Ubuntu 24.04 image `20260705.232.1`, and CPython
`3.11.15`. It reported runtime boundary **12 modules, 234 files**, dead-candidate
ledger **8 modules**, and **2,189 passed, 4 skipped, 163 deselected in 85.71
seconds**. The job concluded successfully.

The first implementation head
`88b302a3579732922c9268b1ee4c3846c7bb7a5d` was pushed and run
`29152460184`, job `86544047614`. Three frozen governance acceptance cases
failed because they tried to resolve the preregistration parent in a depth-one
checkout. Its default suite reported **2,250 passed, 4 skipped, 163
deselected**; no non-governance functional source case failed. That head was
not accepted as the implementation milestone.

The governance tests were changed to preserve the full-history sole-parent and
exact-diff checks locally, while requiring an explicit shallow-repository
predicate, hidden-parent shape, current amendment blob, regular tree modes,
literal anchors, and exact 64-row mapping when the historical object is absent.
The implementation commit was amended rather than adding a child, preserving
the preregistration commit as its sole parent, and was updated with
force-with-lease. Intermediate head
`22cf88af14d1c98943eb8303ca303644410c28c9` then passed run `29152869545`,
job `86545122274`, with **2,253 passed, 4 skipped, 163 deselected in 81.12
seconds**. It was nevertheless superseded before the result freeze because
read-only result fact-checking found that the runtime repository sentinel did
not hash the standalone rerun-registry file and did not inventory exposure
marker entry types. It is historical green evidence, not the final gate head.

The final implementation CI run `29153784500`, job `86547466250`, used runner
`2.335.1`, Ubuntu 24.04 image `20260705.232.1`, and CPython `3.11.15`. It
reported:

- runtime boundary: **12 modules, 235 files**;
- dead-candidate ledger: **8 modules**;
- default suite: **2,253 passed, 4 skipped, 163 deselected in 93.97 seconds**;
  and
- job conclusion: **success** in 1 minute 53 seconds at exact head
  `0a6eb4a92edc1061773c175975f986f0c5ea5a3c`.

The hosted skips and deselections are unchanged from the preregistration run;
the pass increase is exactly the 64 new Phase-2b2f cases, while replacement of
the preregistration absence sentinel by the result/gate test is count-neutral.
The sole job annotation was the Node 20 deprecation for actions forced onto
Node 24; it did not alter the Python result.

Hosted CI receives a depth-one checkout and therefore cannot materialize the
parent tree for an independent three-path diff. The result gate instead parses
the raw commit object without replacement refs, requires one literal parent
equal to the final implementation commit, freezes the result-document and
litmus blobs plus every unchanged implementation blob/mode, and checks the
rerun-test mode and semantic gate. A full-history local post-commit audit is
the authority for the exact three-path result diff. The result commit cannot
freeze its own commit ID or the blob of the test that contains the guard; the
next bounded-repair amendment must seal the result commit and all three result
blobs before licensing any implementation or protected probe execution. This
is the remaining single-researcher self-adjudication limit, not remote or
cryptographic attestation.

## Exact conclusion, stop point, and remaining limits

Phase 2b2f establishes only that the finite synthetic conflict and four
synthetic recovery profiles produce the preregistered same-call sequential
records, bounded observations, one local hardlink append, terminal
verification, and last-mutation witness consumption under the Windows/Ubuntu
oracle above. It establishes deterministic record/hash grammar, exact negative
authority, fail-closed preflight and error cuts, and zero writes to the checked-
out repository during the registered local and hosted executions. It does not
claim that a caller who supplies the checkout itself as `root` has disabled the
recovery endpoint's deliberately local writer.

It does **not** establish durable append, crash/power-loss survival, remote CAS,
real acknowledgement loss, restart recovery, authenticated provenance,
manifest/witness atomicity, namespace-race prevention, cleanup safety,
canonical publication, task completeness, model quality, Lean replay,
heartbeat telemetry, assigned-mvar correctness, tail-goal sweeping, target
routing, or any K-series scientific result.

Commit and push of this result record plus its result-anchor wiring, followed
by green CI at that exact result head, completes Phase 2b2f. The frozen
preregistration would then license Phase 2c preregistration only; it licenses no
Phase 2c implementation.

That license will not be exercised next. By explicit user direction on
2026-07-11, Phase 2b2f is the stop point for synthetic evidence-ledger
expansion. The next registration is one bounded-repair scheduling amendment
that promotes the three U'0.5 kill probes -- exact compression, successful-
trajectory noncontractive-step rate, and Hankel-rank growth -- ahead of
nonessential U'1 repair. It will freeze a repair budget, the minimum Lean and
measurement prerequisites for those probes, a bundled preregistration rule for
deterministic engineering checks, and the non-authoritative status of the
currently untracked proposer/task fixtures.

Until this result commit itself is pushed and green, Phase 2b2f is not complete.
Phase 2c, U'0.5 execution, broader U'1 repair, K1--K4 protected endpoints,
registered runs, canonical diagnostics, Lean execution, network/SSH, workers,
GPU construction, U'2--U'5, real recovery, cleanup, and publication remain
barred.
