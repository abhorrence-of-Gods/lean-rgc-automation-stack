# U'1 evidence milestone 2b phase 2b2c execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. SYNTHETIC MODEL EVIDENCE AND NEGATIVE
AUTHORITY ONLY. NO MUTABLE STORE, FILESYSTEM, CONCURRENCY, REMOTE CAS,
STAGING, PUBLICATION, DURABILITY, MARKER, RECOVERY, WITNESS, MANIFEST,
EXECUTION, LEAN, NETWORK, WORKER, CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU
AUTHORITY.

## Registered boundary and commits

Phase 2b2c was frozen by
`uprime_odlrq_u1_evidence_milestone_2b_phase2b2c_in_memory_fake_cas_amendment_2026-07-11.md`
at commit `56be625387df2c895077b3e9714d5e61ee4d46d4`. Its preregistration gate passed
in CI run `29138391122`, job `86506955522`, before either implementation path
existed.

The reviewed implementation was committed and pushed as
`49d6d9791583a50cf4c08c848d3e3405786185b7`. Its implementation CI gate passed
in run `29140353642`, job `86512134549`. The exact implementation-commit Git
blobs are:

| Role | Path | Git blob |
|---|---|---|
| frozen amendment | `docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2c_in_memory_fake_cas_amendment_2026-07-11.md` | `da2153832e31b72b352022ebf9576af7ca80c8e3` |
| source | `lean_rgc/evals/uprime_rpc_fake_cas_kernel.py` | `35c4a6a12c1ca3c4f86a2088c442705b74bf414a` |
| noncollectable support | `tests/uprime_rpc_fake_cas_kernel_cases.py` | `9c4e0d6075a6208fb76fa89826a97efe9697d28f` |
| collector | `tests/test_uprime_rpc_ledger.py` | `9387f6bf30bcd617b8bdfa93dc35a7a478fc1291` |
| anchor registry | `lean_rgc/evals/uprime_rpc_litmus.py` | `91100edab8ebfafa52037bae22bdbdbbe754a866` |
| external membership/collector oracle | `tests/test_uprime_rerun_license.py` | `409538627f3b8b65e5187271bbc38b98571cafa8` |
| frozen litmus test | `tests/test_uprime_rpc_litmus.py` | `f34cbb28f4b12790ff5a9e5d283334bef85faaf6` |
| frozen tier test | `tests/test_v74_test_tier_manifest.py` | `733c4a8fe884287ae22d567b893108a79ee9f6f7` |
| unchanged tier manifest | `tests/tier_manifest.json` | `39bb37eabbba80101e4ee6a07f2d1a8d8ecc0931` |

The default-deny rerun registry remained the exact 96-byte Git blob
`13ffca6de484effc66f0e628d2e46823277271c6`; the rerun-license source remained
blob `6b39e19d1c5f48cb7c5940ccd08def9286c0146b`. The implementation created no
registered run, exposure marker, repository-tree evidence artifact, or result
under `runs/`. Package initializers and the tier manifest were unchanged.

## Implemented surface

The module exports exactly one public exception, two frozen/slotted validating
records, and two public functions:

```text
InMemoryFakeCasV10Error
InMemoryFakeCasStateV10
InMemoryFakeCasTransitionV10
initial_in_memory_fake_cas_state_v1_0()
step_in_memory_fake_cas_v1_0(state, expected_state_version_sha256,
                             proposed_payload, synthetic_directive,
                             alternate_payload, /)
```

The initializer returns one absent generation-zero value. A valid present
State has generation 1 through `2^63-1`, an exact immutable payload of at most
1,048,576 bytes, its exact count and raw SHA-256, and a domain-separated state
version over generation plus tagged raw payload. Absent and present empty are
distinct. Deletion is unsupported.

The step reconstructs a fresh value-equal snapshot of the caller's State while
retaining the same immutable payload object. It validates every structural
input before semantic classification, then applies the exact precedence:

1. stale expected full State commitment -> conflict;
2. matched expected plus exact current raw bytes -> existing-identical no-op;
3. alternate relational validation;
4. generation exhaustion; and
5. one directive-specific changed transition.

The exact changed directives model acknowledged intended application,
acknowledgement loss plus same-kernel intended confirmation, acknowledgement
loss plus unavailable confirmation, and one caller-selected alternate
substitution. The fourth branch applies the alternate exactly once; it does
not claim that the proposal was applied first. Every directive and client/
confirmation label is deterministic synthetic model data.

The six exact outcomes are:

```text
conflict_no_change
existing_identical_no_change
intended_applied_acknowledged
intended_applied_ack_lost_confirmed
intended_applied_ack_lost_unconfirmed
wrong_delta_confirmed
```

The three intended changed branches have value-identical after States and
deltas. The unconfirmed branch retains the model-latent applied State while its
synthetic client label remains ambiguous. The wrong-delta branch records a
proposal-derived intended candidate and an alternate-derived actual candidate.

Both public record constructors reconstruct and rederive their content. They
reject wrong exact types, subclasses, bool-as-int aliases, inconsistent
nullable fields, forged outcomes or labels, invalid hashes, wrong State/payload
identity, deleted State slots, oversized reason tuples, and every authority
promotion. Transition validation uses a private acyclic derivation primitive;
it does not invoke a public function.

## Commitments and resource boundary

The implementation streams the four frozen domain-separated SHA-256 preimages
without materializing a full preimage or copying a retained payload. The domain
lengths are `47/47/47/52` bytes for State/Input/Delta/Transition. Exact maximum
preimage lengths are:

```text
STATE       1048640
INPUT       2097249
DELTA       1048695
TRANSITION  467
```

The six exact Transition preimage lengths are
`270, 335, 373, 421, 389, 467`. At most one prior payload, one proposal, and
one alternate are retained, for a 3,145,728-byte unique reference bound and a
zero retained payload-copy bound. SHA-256 internal buffers and caller aliases
are outside that zero-copy statement.

Outcome classification compares exact raw bytes. The private
`_raw_payload_sha256` seam populates only redundant raw-SHA fields and is not
used by raw identity or any framed commitment. The mutation oracle forces A,
B, and C to one synthetic digest and still requires intended A-to-B to change
and current A/proposal B/alternate C to produce wrong delta. Records created
under that monkeypatch are discarded test fixtures, not production hash
evidence.

The commitments are collision-resistant evidence under the ordinary SHA-256
assumption. They are not mathematical injectivity, signatures, capabilities,
store-instance identity, origin authentication, or a temporal claim.

## Adversarial implementation review

Three independent lenses reviewed the exact final source/support pair. The
final source blob `35c4a6a12c1ca3c4f86a2088c442705b74bf414a` and support blob
`9c4e0d6075a6208fb76fa89826a97efe9697d28f` were both approved with no remaining
blocker.

Review-driven fixes before freeze included:

- replacing tuple equality as a type oracle with exact per-field validation,
  closing bool/int and subclass-equality forgeries across both records;
- freezing all six-by-seven outcome semantic cells, not only their shape and
  resulting preimage lengths;
- mapping deleted/missing State slots to the single public exception;
- moving resource/table validation before State inspection, hashing, and
  preimage iteration on every public path;
- bounding `reason_codes` by checking exact tuple type and length one before
  inspecting its only cell;
- freezing raw runtime annotations, fresh snapshot and payload identities,
  structural-error cross precedence, and malformed constant-table behavior;
  and
- adding in-memory AST/source mutants for digest-only identity and alternate
  comparison, plus runtime/AST sentinels for forbidden capabilities,
  full-preimage construction, and later-phase leakage.

The source reviewer independently exercised 115 valid branch/hash cases and
11 relational rejections, rejected 84 equality-colliding exact-type mutations,
and confirmed that 45 frozen-constant mutations fail through the public
exception. These reviewer probes supplement, but do not replace, the committed
support matrix.

## Local Windows verification

Local verification used Windows 11 `10.0.26200` and CPython `3.13.7` on the
implementation commit:

1. bytecode compilation and whitespace checks succeeded;
2. the explicit support matrix completed with **19 passed** in 2.58 seconds;
3. the collector selected those same 19 nodes once and completed with
   **19 passed, 1,560 deselected** in 4.99 seconds;
4. the rerun-license/anchor suite completed with **23 passed** in 2.75 seconds;
5. runtime-boundary validation completed with **12 modules, 232 files**;
6. the dead-candidate ledger completed with **8 modules**;
7. the exact frozen four-file M2b profile completed with **1,649 passed**, zero
   failures/errors/skips/xfails, in 254.13 seconds; and
8. the default repository suite completed with **1,956 passed, 3 skipped, 163
   deselected** in 406.78 seconds.

The exact frozen command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

No Phase-2b2c verification invoked SSH, GPU, a network service, Lean, a worker,
a registered experiment, or a canonical diagnostic. The broader default suite
can exercise pre-existing optional Lean tests when a local toolchain is
present; those tests are not Phase-2b2c evidence and grant it no Lean authority.

## Ubuntu CI verification

The preregistration CI run `29138391122` used CPython `3.11.15`. It reported
runtime boundary `12 modules, 231 files`, dead-candidate ledger `8 modules`,
and **1,936 passed, 4 skipped, 163 deselected in 80.26 seconds**. The job
concluded successfully in 1 minute 33 seconds.

The implementation CI run `29140353642`, job `86512134549`, executed the exact
implementation commit. It used GitHub Actions runner `2.335.1`, Ubuntu 24.04
image `20260705.232.1`, and CPython `3.11.15`:

- runtime boundary: **12 modules, 232 files**;
- dead-candidate ledger: **8 modules**;
- default suite: **1,955 passed, 4 skipped, 163 deselected in 79.65 seconds**;
- job conclusion: **success** in 1 minute 33 seconds.

CI reported four skips versus three in the local Windows default suite. This
record makes no causal inference from environment-dependent aggregate skip
accounting. The sole job annotation was the hosted-actions Node 20 deprecation;
it did not alter the Python result.

## Exact conclusion and remaining limits

Phase 2b2c provides a deterministic, pure, one-cell value-transition oracle
whose records, commitments, six outcomes, resource bounds, and negative labels
match the frozen preregistration. It makes caller-visible fork/ABA behavior and
same-kernel model labels explicit.

It does **not** establish that any event occurred, any response was transported
or lost, any other actor exists, or any State persisted. It provides no mutable
store, key namespace, global linearity, concurrency, atomicity between
processes, operation identity, retry safety, idempotence, exactly-once behavior,
filesystem staging, nonce separation, fsync, publication, remote ref, marker,
causal fault, crash/power-loss model, epoch, recovery, replay, witness,
manifest, artifact, claim, ledger, report, or canonical-run binding.

Only commit and push of this result record plus its result-anchor wiring,
followed by green CI for that result commit, completes Phase 2b2c and licenses
Phase 2b2d **preregistration only** for nonce-separated local staging and a
normal fake publisher.

Until all three conditions hold, Phase 2b2d preregistration remains barred.
Phase 2b2d implementation, marker/recovery, epoch/witness issuance, integrated
manifest writing, real claim/publication, network/SSH, Lean, worker execution,
GPU construction, Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5
remain barred in either case.
