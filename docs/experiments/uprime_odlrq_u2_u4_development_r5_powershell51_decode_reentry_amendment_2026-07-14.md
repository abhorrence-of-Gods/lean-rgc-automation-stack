# U-prime / ODLRQ U2--U4 R5 PowerShell 5.1 decode re-entry amendment

Date: 2026-07-14 (Asia/Tokyo)

Status: **ONE DECODE-ONLY FOUR-PATH BOOTSTRAP, THEN A FRESH EXACT E1
REQUALIFICATION**

Anchor: immutable accepted R4 failure-closeout commit
`b57ac55e823bc90a7d86f8b593249b70feeadaf1`.

R5 is a narrow control-plane re-entry.  It does not repeat the mathematical
review, alter the preserved E1 implementation, or reinterpret the stopped R4
attempt.  Its sole functional repair is to decode the already frozen E1 JSON
table with Windows PowerShell 5.1's array semantics correctly and to exercise
that decode/cardinality invariant in B0 before another E1 attempt can exist.

## 1. Immutable R4 evidence

The R5 anchor is the sole-parent child

```text
b57ac55e823bc90a7d86f8b593249b70feeadaf1
parent fbc1259dc276265a8949aad86d9e15b87e4a6dff
tree   3fbb08d6e3d496460e97ca60b83c7667ec518480
```

of the accepted R4 bootstrap.  Its sole changed path is

```text
docs/experiments/uprime_odlrq_u2_u4_development_r4_failure_closeout_2026-07-14.md
```

with Git blob
`fc1f409d2150fcfd199383d6d881549ee81984e7`.

The R4 bootstrap commit `fbc1259d...` passed candidate CI run `29309634540`,
job `87010470961`, with exactly:

```text
2590 passed, 8 skipped, 161 deselected
```

The identical SHA/tree was fast-forwarded to `codex/uprime-odlrq-plan` and
passed distinct accepted CI run `29310057446`, job `87011718613`, with the
same exact counts.

The R4 failure closeout `b57ac55e...` then passed candidate CI run
`29310803890`, job `87013941795`.  The identical SHA/tree was fast-forwarded
to the accepted branch and passed distinct accepted CI run `29311780186`, job
`87016885642`.  Both closeout checks were green.

R4 reached no E1 child, test, receipt, commit, or scientific endpoint.  Its
outer Windows PowerShell 5.1 preflight decoded the six-row constant JSON as
one `Object[]` pipeline item and then wrapped that item directly in `@(...)`.
The resulting outer array had cardinality one, so the runner failed closed
before child creation with
`E1 frozen byte table cardinality changed`.  This was a control-preflight
container-shape defect, not a changed E1 byte or mathematical failure.

### 2026-07-14 result-red-CI clarification for future readers

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run
`29166670576`, job `86580832840`.  The dated audit identifies a guard
shallow-history design omission, not a probe, prerequisite,
artifact-integrity, or scientific endpoint failure.  The exact scientific
candidate commit `3bb3408afc50a08307cff2c9b1906a299739dfb5` passed green
candidate CI run `29166073728`, job `86579287017`.  The red result badge must
not be read as a failed scientific execution.  Likewise, neither the R4
PowerShell preflight terminal nor this historical CI badge supplies evidence
against the finite-fiber envelope.

## 2. Exact supersession and inherited authority

R5 inherits, in order:

1. the original U2--U4 construction-bundle authority;
2. the R2 exact-admission integration and topology bootstrap;
3. the R3 stage-local re-entry and its immutable failure adjudication;
4. the R4 guard-canonicalization re-entry amendment at `fbc1259d...`; and
5. the immutable R4 failure closeout at `b57ac55e...`.

R5 supersedes only:

1. the R4 terminal prohibition for this exact anchor; and
2. the one-stage PowerShell expression that combined JSON pipeline decoding
   and array-subexpression wrapping before checking the frozen table count.

Every E0/E1 formula, fixture, exact rational oracle, completeness witness,
tier firewall, lane selection, wall, Job-object limit, output cap, stopwatch
boundary, three-times margin, Audit contract, test name/count, artifact
schema, protected boundary, guard behavior, stable-path policy, stage order,
and scientific stopping rule remains inherited unchanged unless this document
states the exact decode-boundary refinement below.

A different anchor, parent, tree, R4 failure blob, E1 byte, path set, decode
algorithm, runner, guard behavior, wall, selection, or endpoint is outside R5.

## 3. One composite four-path bootstrap

The R5 bootstrap changes exactly:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md
tests/test_uprime_u2_u4_development.py
tests/uprime_u24_guard.py
tools/run_uprime_u2_u4_development_tests.ps1
```

The document and three control files form one indivisible bootstrap commit.
A document-only child, control-only child, preserved exact E1 import path
change, workflow change, tier-manifest change, fixture, generated artifact,
closeout file, or fifth changed path in the bootstrap is invalid.

The control-file changes are limited to:

- re-anchoring identity/topology at exact R4 failure closeout `b57ac55e...`;
- registering this R5 document and the R5 refs/terminal paths;
- freezing the exact four bootstrap paths and inherited E1 byte table;
- replacing only the PowerShell 5.1 E1-table decode expression as specified
  in section 4;
- making B0 exercise the constant-table decode/count invariant on the real
  registered Windows PowerShell runtime; and
- refreshing the identity/guard/runner mutual hashes required by those exact
  source changes.

The guard gains no new capability, path, mode, cache, or behavioral branch.
The identity oracle gains no scientific test.  The runner gains no wall,
prewarm, test-selection, child-process, publication, or receipt shortcut.

The dirty bootstrap must pass B0 while exactly these four paths are dirty.
The clean commit must be the immediate sole-parent child of `b57ac55e...` and
must pass B0 again before push.  Both states must reject any anchor drift,
merge, duplicate bootstrap, omitted path, extra path, changed R4 failure blob,
changed E1 constant, stale R4/R5 ref, noncontiguous ancestry, or illegal
terminal row.

## 4. Sole functional repair: two-stage PowerShell 5.1 decode

The canonical E1 JSON text and all six rows remain byte-for-byte unchanged.
The R4 one-stage pipeline/array expression is replaced by exactly the
following two-stage data flow, using one intermediate variable:

```powershell
$decodedE1Frozen = $E1FrozenCanonicalJson | ConvertFrom-Json
$e1Frozen = @($decodedE1Frozen)
```

The first statement must complete before the array subexpression is formed.
No comma operator, nested wrapper, unary-array preservation, PowerShell 7
fallback, alternate JSON parser, custom enumerator, reflection, dynamic
evaluation, or version-dependent branch is permitted.

Immediately after the two-stage decode, every lane, including B0, must
unconditionally require:

```powershell
if ($e1Frozen.Count -ne 6) {
    throw "E1 frozen byte table cardinality changed"
}
```

Thus a wrong Windows PowerShell 5.1 container shape is a bootstrap/B0 defect,
not a latent E1-only defect.  JSON decoding failure and a count other than six
fail closed before lane dispatch in every lane.

This unconditional invariant operates only on the runner's frozen constant
JSON.  The runner's new exact frozen-byte preflight remains inside the exact
`if ($Lane -eq "E1")` branch.  Outside Lane E1 the runner may not invoke that
preflight's `Resolve-RegularFile`, `Get-Item` length, `Get-Sha256`,
`git hash-object`, exact row-schema, or exact path-set validation.  Within
Lane E1, those inherited regular-file, root-bound, unique-path,
positive-length, SHA-256, and Git-blob checks must operate on the six elements
produced by the two-stage decode.  The E1 child still starts only after all
exact byte checks succeed.

There is one explicit inherited exception to that lane-local rule.
`load_control_plane_attestation` continues, unchanged, to inspect the general
registered `tracked_paths` set in every lane.  Its topology/worktree
attestation may test tracked-path existence and compute working-tree Git blobs
for tracked paths, including the already existing predecessor
`quotient_generator.py`, `__init__.py`, quotient-generator test, and tier
manifest during B0.  This general control-plane observation is not the new
six-row exact frozen-byte preflight and is not moved, weakened, duplicated, or
redesigned by R5.  It performs no E1 module import, pytest collection, or
scientific endpoint execution.

The bootstrap contains no preserved exact E1 six-file import: the two new E1
paths remain absent and the four overlapping tracked paths retain their
predecessor blobs.  Therefore the inherited general attestation does not
prewarm the preserved exact six-file E1 evidence.  B0 exercises the constant
JSON decode and cardinality contract while preserving the inherited
control-plane attestation exactly as it was.

Static identity/runner checks must reject at least:

- the original R4 one-stage expression;
- moving decode or cardinality back under the E1-only branch;
- two or more intermediate decode variables;
- an added wrapper that preserves the `Object[]` as one item;
- five, seven, duplicated, reordered, or altered constant rows;
- invocation of the runner's new exact frozen-byte preflight outside Lane E1;
- a changed exception string or count; and
- any runner/guard mutual-hash mismatch.

The registered dirty and clean B0 executions are the runtime oracle for the
actual Windows PowerShell 5.1 decode shape.  A static source match alone is
not sufficient.

## 5. Preserved exact E1 source material

No mathematical or E1 source/test edit is licensed.  After the R5 bootstrap
passes both CI gates, a fresh build branch must import exactly the following
six files and no others:

| bytes | SHA-256 | Git blob | path |
|---:|---|---|---|
| 153187 | `21030E4DD3C392D5EA2A9DEA1D5A8354F57AFE1301A59CFA6B0A2CDEE199EF16` | `1e1576ad1f51ebf667bc55d159048c0ae6587524` | `lean_rgc/odlrq/quotient_generator.py` |
| 87121 | `13C4F4D97AFFB363A1EC484BDDD870AF9FB88B0C0796D6728AC774DE941D5496` | `0618f603b86eba3c61c9fb2e15c4edaacce44a14` | `lean_rgc/odlrq/envelope.py` |
| 13341 | `F968B3BC4EB945811E88553F118856658CE45D476B94860B56D7F39DBE90D752` | `f97272d5de222fb555a78639d66eb89e77e63d86` | `lean_rgc/odlrq/__init__.py` |
| 59547 | `4D1FAF8C725BB2EA9FAD01E83A330C578B1ABE01840EAD263E98D174A84CA7C0` | `400f630e10ddbd98657fd1b142c6b202a8656c7d` | `tests/test_odlrq_quotient_generator.py` |
| 32675 | `90580302C24F99B8CAF1500EF013296E214D2206F6C936D781BAA8E8A64832D5` | `66f9be1a3c5455b822b229fc2024b9c58b768fff` | `tests/test_odlrq_envelope.py` |
| 8827 | `D955F797DFA2F4C0943F5F385F9301CED0A9D592BE19D459BF5EB2BEEB657854` | `8bb7810cc49b56aff3d7b18020dab475644911a2` | `tests/tier_manifest.json` |

The set of dirty paths must equal this six-path set.  Byte length, SHA-256,
and Git blob must all match before the official dirty E1 command.  A subset,
superset, reconstructed equivalent, formatting-only edit, regenerated
fixture, changed test, or new manifest node is not the preserved import.

The E1 LaneTests tuple remains exactly, in order:

```text
tests/test_odlrq_quotient_generator.py
tests/test_odlrq_envelope.py
tests/test_uprime_u2_u4_development.py
```

E1 still requires exactly 48 passed tests, zero skip/xfail/deselection, the
inherited 120-second hard wall, and the inherited three-times cold-margin
rule.  No direct pre-run, pytest pre-collection, pycache reuse, test split,
guard bypass, or stopwatch movement is permitted.

## 6. Frozen refs and topology

The only R5 refs are:

```text
bootstrap       codex/uprime-u2-u4-development-r5-decode-bootstrap
build           codex/uprime-u2-u4-development-r5-build
closeout        codex/uprime-u2-u4-development-r5-closeout
failure-closeout codex/uprime-u2-u4-development-r5-failure-closeout
accepted        codex/uprime-odlrq-plan
```

The R5 terminal document paths are:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r5_closeout_2026-07-14.md
docs/experiments/uprime_odlrq_u2_u4_development_r5_failure_closeout_2026-07-14.md
```

The semantic stage order remains:

```text
E1 -> E2 -> ME0 -> S0 -> I0
```

E0 remains an immutable predecessor, not an R5 stage row.  R5 inherits the R4
shared correction topology: at most one correction total, consumed either by
an eligible bootstrap correction or by one later E2--I0 correction.  The
bootstrap correction path set must be one of the inherited exact sets:

```text
tests/uprime_u24_guard.py
tests/test_uprime_u2_u4_development.py + tests/uprime_u24_guard.py
tools/run_uprime_u2_u4_development_tests.ps1 + tests/uprime_u24_guard.py
tests/test_uprime_u2_u4_development.py + tests/uprime_u24_guard.py + tools/run_uprime_u2_u4_development_tests.ps1
```

The R5 amendment, anchor, E1 constants, workflow, walls, tests, Audit,
fixtures, and scientific endpoints cannot change in a correction.  If a
bootstrap correction is used, no later correction remains.

The exact E1 import is never correction-eligible.  An E1 byte mismatch, dirty
lane failure, count failure, resource/margin failure, candidate-CI failure,
or accepted-CI failure stops R5.  The E1 bytes and control files may not be
edited to turn that outcome into a pass.  If the shared quota remains unused,
one later E2--I0 correction may touch only the last stage's inherited frozen
allowlist and may not change an earlier stage, control file, or endpoint.

## 7. Mandatory execution order and CI gates

The order is fixed:

1. Start the four-path R5 bootstrap at exact anchor `b57ac55e...`.
2. Run registered B0 while exactly the four bootstrap paths are dirty.  This
   must execute the two-stage JSON decode and six-element count on Windows
   PowerShell 5.1.
3. Commit the indivisible four-path bootstrap as the immediate sole-parent
   child of `b57ac55e...` and run clean B0 on the identical files.
4. Push only the bootstrap candidate ref and require candidate CI to pass with
   exactly `2590 passed, 8 skipped, 161 deselected`.
5. Fast-forward the accepted ref to the identical bootstrap SHA/tree without
   merge, cherry-pick, omission, or rewrite, then require a distinct accepted
   CI with the same exact `2590 / 8 / 161` counts.
6. Only after both green CI gates, create a fresh R5 build branch/worktree from
   the accepted bootstrap tip.
7. Import the exact six E1 files from section 5, verify all byte/SHA/blob
   identities, and run the registered official dirty E1 lane once.
8. Only a green qualifying E1 receipt licenses the exact E1 commit.  That
   commit must pass candidate CI with exactly
   `2600 passed, 8 skipped, 161 deselected`, fast-forward identically to
   accepted, and pass a distinct accepted CI with the same `2600 / 8 / 161`
   counts before E2 source may exist.

No preserved exact E1 six-file import may exist in the bootstrap; the
inherited predecessor files and general tracked-path attestation remain as
specified in section 4.  No preserved E1 result may be read before the two
bootstrap CI gates.  A local direct diagnostic, old R3 result, R4 static
approval, cached pytest run, or green bootstrap CI is not an E1 receipt.

## 8. Stop rules

R5 stops and records one failure closeout on any of:

- wrong anchor, parent, tree, R4 failure blob, or accepted ref;
- shallow, replaced, merged, noncontiguous, duplicated, or rewritten history;
- missing, extra, mixed, or early source path;
- failure of dirty B0 or clean B0;
- one-stage decode, wrong decode container shape, JSON decode failure, or
  decoded count other than six in any lane;
- invocation of the runner's new exact frozen-byte preflight outside Lane E1;
- red bootstrap candidate CI or red distinct accepted CI;
- altered E1 byte, SHA-256, Git blob, manifest selection, test count, wall,
  margin, guard, Audit, or endpoint;
- dirty or clean E1 lane failure, missing receipt, red E1 candidate CI, or red
  distinct accepted E1 CI;
- an E1 correction, a second shared correction, an illegal correction path,
  or a correction that changes authority; or
- protected access, native Lean/RPC use, SSH, GPU, LLM, deployment, or any
  unregistered capability.

Bootstrap identity/runner failure uses
`U24_B0_IDENTITY_OR_RUNNER_BLOCKED`.  An exact E1 or E1-CI failure uses
`U24_E1_ENVELOPE_BLOCKED`.  Any path/resource/capability expansion uses
`U24_RESOURCE_OR_SCOPE_BLOCKED`.  A stopped result remains evidence and is
not deleted, rerun under weakened rules, or relabeled as scientific success.

## 9. Resource and capability boundary

All R5 bootstrap and E1 work is local Windows CPU work under the inherited
Job-object process, memory, output, and wall limits.  GitHub Actions is used
only for the registered candidate and accepted repository gates.

R5 does not license:

- protected K1--K4 reads or any protected-task evaluation;
- native Lean, Lake, Lean RPC, toolchain drift, or theorem-prover execution;
- SSH, remote CPU, GPU/CUDA, model server, or distributed execution;
- an LLM proposer, model weights, `pilot_tasks`, prompt generation, or
  knowledge distillation;
- MaxEnt fitting, global-similarity construction, locality learning, or ODLRQ
  learner training;
- artifact publication before EMIT; or
- a new runner, alternate shell, sidecar validator, workflow change, or
  deployment.

## 10. Nonclaims

Passing R5 B0 proves only that the four-path control bootstrap, including the
PowerShell 5.1 two-stage constant decode and six-row cardinality check, is
bound and executable under its registered harness.  It does not prove E1.

Passing bootstrap candidate/accepted CI proves repository regression
compatibility at the pre-E1 tree.  It does not inspect the preserved E1
mathematics.

If E1 later passes, the claim is limited to the inherited declared-synthetic
finite-fiber envelope contract and its exact registered tests.  It is not a
general theorem about arbitrary fibers, infinite cutoffs, solve-rate benefit,
MaxEnt calibration, global similarity, Lean-oracle locality, or LLM benefit.

The R4 preflight failure and the historical red CI badge are engineering and
governance evidence.  Neither is evidence against the upper-stack theory.
Conversely, this narrow decode repair supplies no new evidence for that
theory until the separately registered E1 endpoint actually runs and passes.
