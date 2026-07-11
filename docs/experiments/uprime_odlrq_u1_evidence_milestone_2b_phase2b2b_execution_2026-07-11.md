# U'1 evidence milestone 2b phase 2b2b execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. NEGATIVE AUTHORITY ONLY. NO FORMAT
VALIDATION, ATOMIC BUNDLE SNAPSHOT, CAS, WRITE, STAGING, MARKER, RECOVERY,
WITNESS, CLAIM, REMOTE, WORKER, LEAN, NETWORK, CANONICAL-RUN, RERUN,
LATER-STAGE, OR GPU AUTHORITY.

## Registered boundary and commits

Phase 2b2b was frozen by
`uprime_odlrq_u1_evidence_milestone_2b_phase2b2b_local_artifact_observer_amendment_2026-07-11.md`
at commit `2e242fe74a4d87dcf0e452dda3ea3eb3d4837e51`. Its preregistration gate passed
in CI run `29134060136` before implementation began.

The reviewed implementation was committed and pushed as
`e5b46c7fb1822fc68557396f1875e6778b85068c`. Its implementation CI gate passed
in run `29135861593`. The exact implementation-commit Git blobs are:

| Role | Path | Git blob |
|---|---|---|
| frozen amendment | `docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2b_local_artifact_observer_amendment_2026-07-11.md` | `8c4e0d95497116b60f62acf37e544b5d75794651` |
| source | `lean_rgc/evals/uprime_rpc_local_artifact_observer.py` | `3a66fe13de7edfb93fc00a7a3302f4512e206eb1` |
| noncollectable support | `tests/uprime_rpc_local_artifact_observer_cases.py` | `ebc9cd54da6fc46ba7d86a6a35a3f20719419f80` |
| collector | `tests/test_uprime_rpc_ledger.py` | `23fcda5e5b1db55c9b6ee27d769a9d43e3bb4cda` |
| anchor registry | `lean_rgc/evals/uprime_rpc_litmus.py` | `1ef3e5e8cdc5f0e21163085a68a541513f87823f` |
| external membership/collector oracle | `tests/test_uprime_rerun_license.py` | `4e92114eab50fc01e7b0ce161f4d356327522d79` |

The default-deny rerun registry remained the exact 96-byte Git blob
`13ffca6de484effc66f0e628d2e46823277271c6`. The implementation created no
registered run, exposure marker, repository-tree artifact, or result under
`runs/`. Every Phase-2b2b artifact fixture was disposable and below a
pytest-created local temporary root.

## Implemented surface

The implementation adds exactly one positional-only public function, two
frozen/slotted validating records, and one public exception:

```text
observe_local_rpc_artifact_set_v1_0(root, claim_receipt, /)
LocalArtifactObservationV10
LocalArtifactSetObservationV10
LocalArtifactObservationV10Error
```

The root must be an exact, nonempty, lexically absolute `str`; subclasses and
`PathLike` values reject before a caller callback. The receipt must be the exact
public 13-field receipt type and is reconstructed through its public validator.
Its canonical structural digest and the first 12 lowercase hex digits of
`license_commit` derive exactly three repository paths in reservation, ledger,
and report order.

The shared parent is observed without directory enumeration. Stable parent
absence returns three parent-derived `absent` rows without a child join, stat,
or open. A stable real parent permits three sequential child observations. A
final parent error, unsafe type, or identity/type drift clears all child byte
evidence and replaces all rows with one parent `indeterminate` reason.

For each child, two direct `FileNotFoundError` observations mean only `absent`.
A candidate regular file is size-bounded, opened read-only, and read twice from
the same exact nonnegative descriptor. Each pass uses exact-length chunks,
streams directly into SHA-256, deletes the live payload before another read,
and performs one one-byte EOF probe. Exact path family `S`, descriptor family
`F`, and the single reachable initial binding comparison `B(S0)=B(F0)` detect
the frozen mutation classes. Every other enumerated filesystem, metadata,
resource, return-type, close, and race outcome becomes `indeterminate` with a
deterministic reason tuple.

Both public record constructors validate all field types, state/reason/digest
relations, receipt/path/anchor binding, parent/child relations, count and byte
derivations, resource constants, negative suffixes, and exact-false license
flags. Stable malformed bytes and empty files remain physically `present`;
there is deliberately no artifact parser or aggregate all-present verdict.

## Frozen resource accounting

The production bounds are exactly:

```text
reservation accepted bytes       <=   1,048,576
ledger accepted bytes            <= 134,217,728
report accepted bytes            <=  16,777,216
aggregate accepted bytes         <= 152,043,520
returned payload work bytes      <= 304,087,043
os.read calls                    <=       4,646
observer-owned live payload      <=      65,536 bytes
```

The payload-work formula is `2 * 152,043,520 + 3`: two successful passes plus
at most one nonempty EOF-probe byte per artifact. The call formula is
`2 * (16 + 2,048 + 256 + 3)`. These bounds use the documented
`os.read(fd, n)` contract that a successful production call returns no more
than `n` bytes. Contract-violating injected doubles are fail-closed oracle
inputs, not a production OS resource claim.

## Adversarial review and oracle repairs

The amendment was not frozen on its first draft. Independent reviews required
an explicit payload lifetime, state-dependent observation endpoints, complete
reason precedence, parent-derived absence semantics, exact EOF accounting,
strict public-record constructors, removal of algebraically unreachable later
`B` checks, and both optional open flags. Governance review then reversed a
false selector claim: a caller can freely choose the 48-bit anchor prefix by
constructing an unauthenticated structural receipt. It also removed caller
callbacks by narrowing root to exact `str`, disclosed unauthenticated backing
transport, and changed the machine-readable root scope to an unauthenticated
prefix. Three final lenses approved the exact amendment blob.

The first implementation oracle was rejected for omitting most of the
descriptor protocol. The final finite matrix covers every `D`, `S`, `F`, and
initial `B` component; all three fstat stages; both seeks; read, EOF-probe,
content-drift, close, and final-stat outcomes; Windows reparse sentinels; all 27
P/A/I vectors; every public-constructor field; resource formulas; and
continuation to later artifacts after a failed row.

An early deterministic harness produced 64 failures because Windows reused a
closed numeric file descriptor for later artifacts. The oracle, not the
source, was repaired to bind injections to an open generation; continuation
assertions remained strict. Subsequent source review found two real defects:
ordinary `Exception` subclasses could leak beyond the tri-state result, and an
exposed `st_file_attributes=None` was confused with an absent attribute. The
source now closes the ordinary exception domain and distinguishes absence with
a private sentinel.

Mutation review then showed that a narrowed exception tuple survived the
oracle, so exact `(Exception,)`, `RuntimeError`, and `ValueError` cases were
frozen. A final boundary review found no dynamic repository/exposure check; the
last oracle therefore snapshots `runs/`, exposure markers, and the temporary
root while installing raising sentinels on existing production and prior-phase
capabilities. Final source and integration reviews approved the exact blobs
with no remaining implementation-determining blocker.

## Local Windows verification

Local verification used Microsoft Windows 11 Home `10.0.26200` build `26200`
and CPython `3.13.7` at implementation commit
`e5b46c7fb1822fc68557396f1875e6778b85068c`:

1. bytecode compilation and whitespace checks succeeded;
2. the explicit support matrix completed with **408 passed** in 8.12 seconds;
3. the frozen collector selected those same 408 nodes once and completed with
   **408 passed, 1,152 deselected** in 7.55 seconds;
4. the anchor/license profile completed with **22 passed** in 1.87 seconds;
5. the full RPC ledger collector completed with **1,560 passed** in 240.86
   seconds;
6. the exact frozen four-file M2b command completed with **1,629 passed**, zero
   failures/errors/skips/xfails, in 242.41 seconds; and
7. the default repository suite completed with **1,936 passed, 3 skipped, 163
   deselected** in 430.56 seconds.

The exact frozen command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

The new source, support, and frozen profile invoked no SSH, GPU, Lean worker,
registered experiment, or canonical diagnostic. The broader default suite can
exercise pre-existing optional Lean tests when a local toolchain is present;
those tests are not Phase-2b2b evidence and grant it no Lean or worker
authority.

## Ubuntu CI verification

CI run `29135861593`, job `86499929850`, executed the exact implementation
commit. It used GitHub Actions runner `2.335.1`, Ubuntu 24.04 image
`20260705.232.1`, and CPython `3.11.15`.

- runtime boundary: `12 modules, 231 files`;
- dead candidate ledger: `8 modules`;
- default suite: **1,935 passed, 4 skipped, 163 deselected in 76.08 seconds**;
- job conclusion: **success** in 1 minute 30 seconds.

CI reported four skips versus three in the local Windows suite. This record
makes no causal inference from aggregate environment-dependent skip accounting.
The sole job annotation was the hosted-actions Node 20 deprecation; setup also
logged the Node `punycode` deprecation. Neither changed the Python result.

## Exact conclusion and remaining limits

Phase 2b2b provides a bounded, read-only, complete three-row typed observation
for one caller-chosen receipt/root slice. It distinguishes protocol-stable
physical presence, two-point absence, and enumerated indeterminacy. It discards
raw payloads after hashing, does not promote physical presence to format
validity, and maps enumerated race and resource failures to `indeterminate`.

It does **not** authenticate receipt origin, prevent favorable 48-bit selector
probing or anchor collisions, enumerate all receipts, validate any artifact
format, bind the three artifacts to each other or to an attempt manifest,
provide an atomic bundle snapshot, prove durability, or prevent a hostile
Windows reparse race. Prefix ancestry and backing-store transport remain
unauthenticated. No result is a performance sample, transition verdict,
publication fact, or safety certificate.

Only commit and push of this result record plus its anchor wiring, followed by
green CI for that result commit, completes Phase 2b2b and licenses Phase 2b2c
**preregistration only** for a pure single-process in-memory fake CAS kernel.
Until all three conditions hold, Phase 2b2c preregistration remains barred.
Phase 2b2c implementation, filesystem staging, marker/recovery, witness
issuance, real claim/publication, network/SSH, Lean, worker execution, GPU
construction, Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5 remain
barred in either case.
