# U'1 evidence milestone 2b phase 2b2d execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. NONCANONICAL LOCAL-STAGING / PURE
FAKE-PUBLISHER EVIDENCE AND NEGATIVE AUTHORITY ONLY. NO REAL OR CANONICAL
PUBLICATION, STORE, REMOTE CAS, CLEANUP, FSYNC, DURABILITY, MARKER, RECOVERY,
EPOCH, WITNESS, MANIFEST, EXECUTION, LEAN, NETWORK, WORKER, CANONICAL-RUN,
RERUN, LATER-STAGE, OR GPU AUTHORITY.

## Gate and exact artifacts

Phase 2b2d was preregistered before implementation in commit
`6e6983c1a524e82f2aaff57c0cc10e811bab9e8c`. That commit was pushed and its
Ubuntu CI run `29141829431`, job `86516341565`, completed successfully before
either future implementation file existed.

The implementation commit is
`697b45eb77c6c9df7ee6b1e78cb07e1cebe5284b`. It was pushed before this record
was drafted, and Ubuntu CI run `29143577304`, job `86521115987`, completed
successfully at that exact head.

The exact Git blobs at the implementation commit are:

| artifact | blob |
|---|---|
| Phase-2b2d amendment | `27bd516527f96ba64129f1eda548b065043c15f4` |
| source | `3a7b78f7a66e4f53413d366192e70d039144f581` |
| explicit support | `48d6d55c4d408a1f3b97adc7df25031a7eb032d8` |
| anchor source | `41f6db737b63aed18707065e8425b7d8824ca7c8` |
| rerun-license/anchor test | `4fbd0fce2b4c2de981fd474eeab22c3f5de49c3f` |
| collector | `d02687c587b35457543913d5f0e8adcb0a68295f` |

The implementation paths are:

```text
lean_rgc/evals/uprime_rpc_local_staging_fake_publisher.py
tests/uprime_rpc_local_staging_fake_publisher_cases.py
```

The support module exports 50 unique ordered test functions. The collector
imports it exactly once. The amendment, source, support, collector, and this
result record are anchored; the result path is introduced only by this result
commit.

## Implemented contract

The public surface is exactly one exception, one frozen/slotted 63-field
Result, and one positional-only function:

```text
LocalStagingFakePublisherV10Error
LocalStagingFakePublishResultV10
stage_and_fake_publish_normal_v1_0
```

The caller supplies an exact lexical staging parent, a lowercase hex32
collision nonce, one Phase-2b2c State, an expected state version, and exact
proposal bytes. The nonce is explicitly only a caller-selected collision
separator. It is not entropy, freshness, identity, capability, epoch,
idempotence, or causal evidence.

The three successful-return outcomes are:

```text
cas_conflict_no_stage
cas_existing_identical_no_stage
staged_intended_fake_publish_acknowledged
```

Conflict and existing-identical validate lexical inputs and derive the pure
normal fake-CAS result without physical filesystem I/O. The changed branch
uses the frozen order:

```text
parent D0
-> O_EXCL open and F0
-> exact partial-write completion and F1
-> seek, exact raw readback, EOF probe and F2
-> exactly one close
-> retained no-follow path P
-> parent D1
-> expose the pure acknowledged fake-CAS Transition
```

The implementation compares readback chunks directly with the proposal and
also computes the raw digest. It streams the frozen operation commitment and
matches all four preregistered Windows/POSIX goldens. It reconstructs all 66
fields of the nested Phase-2b2c Transition before accepting a Result.

A changed success retains the nonce-separated stage. A post-create error can
also retain zero bytes, a prefix, a full payload, or an externally changed
entry. The implementation never enumerates, reuses, classifies, promotes,
renames, links, unlinks, truncates, or cleans those files. A new call with a
different nonce has a distinct candidate path, but no freshness or availability
claim is made.

No `fsync`, flush, final filename, real/canonical publication, receipt, claim,
reservation, manifest, mutable/global fake store, marker, recovery exclusion,
epoch, replay, witness, network, SSH, Lean, worker, registered execution, or
GPU action was added.

## Adversarial review disposition

Three independent preregistration lenses reviewed the exact amendment before
the preregistration commit. Review-driven corrections included:

- making all fixed machine labels branch-neutral for no-stage outcomes;
- displaying the single Windows backslash and its exact UTF-8 bytes correctly
  in the frozen goldens;
- requiring an explicit Windows drive root and exact non-bool reparse
  attributes;
- defining the initial parent as `D0`; and
- excluding `mtime_ns` from the cross-close Windows path/descriptor binding
  while retaining full `F1 = F2` inside the open descriptor family.

The first implementation attack found four substantive gaps:

1. an in-flight primary `BaseException` was masked when close simultaneously
   failed with an ordinary exception;
2. the prior 64 KiB read object remained live when the next read began,
   violating the one-buffer peak claim;
3. removing direct raw equality survived because the existing mismatch also
   changed SHA-256; and
4. explicit call-bound and native absolute dot/dot-dot/trailing path tests were
   missing.

All four were repaired before the implementation commit:

- a private fixed-size descriptor owner always attempts one close while
  preserving an in-flight non-`Exception` primary over ordinary close failure
  or a non-`None` close return;
- `raw` and `chunk` references are deleted before the next read;
- a constant-digest adversarial case now makes direct raw equality decisive;
  a source-equivalent deletion of only that equality produces one failure
  (`174 passed, 1 failed`); and
- exported tests independently reach write, data-read and EOF-read call bounds
  and reject native absolute `/.`, `/child/..`, and trailing-separator forms
  before physical I/O.

The repaired source/support blobs then passed all three review lenses. The
runtime lens observed no prior `raw`/`chunk` survivor before the second 64 KiB
read and an approximately constant tracemalloc peak delta (about 77 KiB) for
64 KiB and 1 MiB proposals. The mutation lens rejected all 63 Result-field
forgeries, enumerated/revalidated all 66 Transition fields, rejected all 21
outcome-table cell mutations, and matched all four operation goldens. The
governance lens confirmed exactly-once collection, `tmp_path`-only real test
writes, unchanged package/tier/registry/`runs/` state, and no later-phase
capability leakage.

## Local Windows verification

Local verification used Windows `10.0.26200.0` and CPython `3.13.7` on the
implementation tree:

1. source/support bytecode compilation and whitespace checks succeeded;
2. direct explicit support completed with **175 passed** in 4.85 seconds;
3. collector selection completed with **175 passed, 1,579 deselected** in 6.73
   seconds, with the same nodes collected exactly once;
4. runtime-boundary validation completed with **12 modules, 233 files**;
5. the dead-candidate ledger completed with **8 modules**;
6. the exact frozen four-file M2b profile completed with **1,825 passed**, zero
   failures/errors/skips/xfails, in 454.03 seconds; and
7. the default repository suite completed with **2,132 passed, 3 skipped, 163
   deselected** in 1,189.23 seconds.

The exact frozen command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

Every Phase-2b2d real filesystem fixture was created under pytest `tmp_path`.
No Phase-2b2d test contacted a network service, SSH host, GPU, worker,
registered task, or canonical run. The broader default suite can exercise
pre-existing optional Lean tests when a local toolchain is present; those
tests are not Phase-2b2d evidence and grant this slice no Lean authority.

## Ubuntu CI verification

The preregistration CI run `29141829431`, job `86516341565`, used CPython
`3.11.15`. It reported runtime boundary **12 modules, 232 files**,
dead-candidate ledger **8 modules**, and **1,956 passed, 4 skipped, 163
deselected in 78.60 seconds**. The job concluded successfully in 1 minute 32
seconds.

The implementation CI run `29143577304`, job `86521115987`, used GitHub
Actions runner `2.335.1`, Ubuntu 24.04 image `20260705.232.1`, and CPython
`3.11.15`. It reported:

- runtime boundary: **12 modules, 233 files**;
- dead-candidate ledger: **8 modules**;
- default suite: **2,131 passed, 4 skipped, 163 deselected in 83.38 seconds**;
  and
- job conclusion: **success** in 1 minute 40 seconds.

CI reported one additional environment-dependent skip and one fewer pass than
local Windows. This record makes no causal inference from aggregate
environment-dependent skip accounting. The sole hosted-job annotation was the
Node 20 deprecation for actions forced onto Node 24; it did not alter the
Python result.

## Exact conclusion and remaining limits

Phase 2b2d establishes that the frozen implementation can gate exposure of a
pure normal fake-CAS value Transition on one exact local nonce-stage
observation interval, under the finite Windows/Ubuntu oracle above. It
establishes exact outcome, path, resource, raw-readback, commitment, and
negative-authority consistency for successful Result values.

It does **not** establish that a detached Result proves I/O. The Result remains
an unauthenticated forgeable value object whose constructor performs no
physical filesystem operation. It provides no current file-existence,
post-return lifetime, authenticated namespace, local-disk, confidentiality,
cleanup, cumulative residue, crash/power-loss durability, request identity,
global CAS linearity, concurrency, idempotence, exactly-once, real/canonical
publication, attempt completeness, marker causality, recovery, epoch, replay,
witness, manifest, execution, safety, model-quality, Lean, network, SSH,
worker, registered-run, or GPU claim.

Only commit and push of this result record plus its result-anchor wiring,
followed by green CI for that result commit, completes Phase 2b2d and licenses
Phase 2b2e **preregistration only** for the internal one-shot synthetic marker
journal, publisher/recovery exclusion, epoch ownership/release/abandon/replay,
and private same-instance single-use witness registry.

Until all three result-gate conditions hold, Phase 2b2e preregistration remains
barred. Phase 2b2e implementation, Phase 2b2f integrated manifest/recovery
audit, Phase 2c reservation writer/preflight, real/canonical publication,
registered runs, canonical diagnostic, M2c, U'0.5, U'2--U'5, SSH/network,
Lean, workers, and GPU construction remain barred in either case.
