# U-prime / ODLRQ U2--U4 R6 static-scope re-entry amendment

Date: 2026-07-14 (Asia/Tokyo)

Status: **FROZEN SIX-PATH CONTROL RE-ENTRY; THEN A FRESH EXACT E1
REQUALIFICATION**

Anchor: immutable accepted R4 failure-closeout commit
`b57ac55e823bc90a7d86f8b593249b70feeadaf1`.

R6 is a narrow control-plane re-entry after the registered R5 dirty-B0
attempt failed closed.  It does not repair the stopped R5 worktree, rerun the
R5 attempt, change the PowerShell 5.1 decode repair, or execute E1.  Its sole
semantic/control correction is to make one static runner assertion aware of
the E1 branch that it is intended to audit.

The independently reported byte lengths and Git blobs in section 3 are a hard
pre-execution gate.  Both imported documents must match before mutual hashes
may be closed and before dirty B0 may run.

## 1. Immutable anchor and predecessor authority

The exact R6 anchor is

```text
commit b57ac55e823bc90a7d86f8b593249b70feeadaf1
parent fbc1259dc276265a8949aad86d9e15b87e4a6dff
tree   3fbb08d6e3d496460e97ca60b83c7667ec518480
```

It is the sole-parent R4 failure-closeout child.  Its sole changed path is

```text
docs/experiments/uprime_odlrq_u2_u4_development_r4_failure_closeout_2026-07-14.md
```

with Git blob `fc1f409d2150fcfd199383d6d881549ee81984e7`.

R6 inherits, in order:

1. the original U2--U4 construction-bundle authority;
2. the R2 exact-admission integration and topology bootstrap;
3. the R3 stage-local re-entry and its immutable failure adjudication;
4. the R4 guard-canonicalization re-entry amendment at
   `fbc1259dc276265a8949aad86d9e15b87e4a6dff`;
5. the immutable R4 failure closeout at the R6 anchor;
6. the byte-exact, uncommitted R5 PowerShell 5.1 decode amendment; and
7. the byte-exact R5 failure closeout that adjudicates its one official dirty
   B0 attempt.

The last two documents are imported as evidence in the R6 bootstrap.  They
are not edited in place and do not turn the stopped R5 worktree into a valid
R6 worktree.  R6 starts from a separate clean worktree at the exact anchor.

### 2026-07-14 result-red-CI clarification for future readers

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run
`29166670576`, job `86580832840`.  The dated audit identifies a guard
shallow-history design omission, not a probe, prerequisite,
artifact-integrity, or scientific endpoint failure.  The exact scientific
candidate commit `3bb3408afc50a08307cff2c9b1906a299739dfb5` passed green
candidate CI run `29166073728`, job `86579287017`.  The red result badge must
not be read as a failed scientific execution.  The R5 B0 terminal described
below is a separate static control-plane failure and likewise is not a failed
E1 or mathematical endpoint.

## 2. Exact R5 failure adjudication

R5 was executed once through its registered dirty-B0 runner in its own failed
worktree.  The two-stage Windows PowerShell 5.1 constant decode completed and
the unconditional six-row cardinality check passed.  Execution then reached
the identity test and exited nonzero at the new static runner assertion.

The failed assertion treated all five E1-preflight literals as if each must
occur exactly once in the entire runner.  Four literals do occur once.  The
generic literal

```text
Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative)
```

correctly occurs twice: once inside the E1 frozen-byte preflight and once in
the inherited semantic-lane tier-manifest/test-path validation.  The E1 block
contains exactly one of those two occurrences.  The R5 assertion therefore
confused global source multiplicity with E1-branch multiplicity.

R5 failed closed before any E1 child, E1 test, E1 receipt, E1 commit,
scientific endpoint, candidate CI, or accepted CI existed.  It read no
protected K1--K4 result and created no evidence about the finite-fiber
envelope.  Its disposition is `U24_B0_IDENTITY_OR_RUNNER_BLOCKED`, not an E1
or theory failure.

The failed R5 worktree is immutable evidence.  It may not be patched, cleaned,
committed, relabeled, or rerun.  Its amendment and failure closeout are copied
byte-for-byte into R6; the R5 identity, guard, and runner are reconstructed
only in the new R6 worktree under this amendment.

## 3. Frozen R5 document identities

The independent R5 closeout report freezes these exact identities:

| authority document | bytes | Git blob |
|---|---:|---|
| `docs/experiments/uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md` | 18061 | `a15d3e339d634f7dfe36e5c8b7a7595d39a2dbde` |
| `docs/experiments/uprime_odlrq_u2_u4_development_r5_failure_closeout_2026-07-14.md` | 7778 | `fca1d61127ded045275d1c40fe4a55815d389304` |

A different byte length, different Git blob, normalized copy, editorial
correction, regenerated closeout, or alternate R5 document blocks R6.  The
two documents are evidence inputs, not correction targets.

## 4. One indivisible six-path bootstrap

The R6 bootstrap changes exactly these six paths:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md
docs/experiments/uprime_odlrq_u2_u4_development_r5_failure_closeout_2026-07-14.md
docs/experiments/uprime_odlrq_u2_u4_development_r6_static_scope_reentry_amendment_2026-07-14.md
tests/test_uprime_u2_u4_development.py
tests/uprime_u24_guard.py
tools/run_uprime_u2_u4_development_tests.ps1
```

The first two paths must match section 3 byte-for-byte.  The R6 amendment and
three control files form the rest of the same indivisible bootstrap commit.
A document-only child, control-only child, omitted R5 evidence document,
workflow, tier manifest, E1 source/test, generated artifact, terminal file, or
seventh dirty path is invalid.

The identity-file changes are limited to:

- registering the two frozen R5 evidence documents and this R6 amendment;
- freezing the exact six bootstrap paths;
- registering R6 refs and R6 terminal paths;
- preserving the exact anchor, ancestry, stage, and correction topology;
- replacing only the overbroad static total-count assertion with the
  structural scope-aware assertion in section 5; and
- refreshing the identity/guard/runner bindings required by those exact
  source changes.

The guard may change only its two existing freeze values:

```text
FROZEN_IDENTITY_CORE_SHA256
FROZEN_RUNNER_SHA256
```

After masking those two values, the R6 guard must be byte-identical to the
anchor guard.  It gains no capability, mode, path, cache, branch, wrapper,
denylist row, canonicalization rule, or policy behavior.

The runner changes are limited to R6 bookkeeping paths/refs/terminal names,
the identity/guard binding values, and any exact source text required to bind
the unchanged R5 two-stage decode.  It may not change the decode data flow,
constant JSON, E1 preflight, wall, test selection, child process, receipt,
publication, capability boundary, or scientific endpoint.

## 5. Sole semantic/control correction: scope-aware static assertion

R6 preserves the exact R5 decode and cardinality data flow:

```powershell
$decodedE1Frozen = $E1FrozenCanonicalJson | ConvertFrom-Json
$e1Frozen = @($decodedE1Frozen)
if ($e1Frozen.Count -ne 6) {
    throw "E1 frozen byte table cardinality changed"
}
```

These statements remain ordered, unique, and before Lane E1 dispatch, so
every lane, including B0, executes decode and requires `Count == 6`.

The identity test must locate the E1 outer block structurally, never by line
number.  It must require exactly one start marker and one following branch
marker, with the start preceding the end:

```text
if ($Lane -eq "E1") {
if ($Lane -in @("EMIT", "CLOSEOUT"))
```

The resulting source slice is the only `e1_outer_block`.  For the generic
resolve literal

```text
Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative)
```

the frozen counts are:

```text
runner total   = 2
E1 block total = 1
```

For each of the following four literals, both the runner total and E1-block
total remain exactly one:

```text
foreach ($entry in $e1Frozen)
Get-Item -LiteralPath $candidate -Force
Get-Sha256 -LiteralPath $candidate
hash-object $relative
```

The static test must fail on a missing or duplicate branch marker, reversed
markers, a resolve total other than two, an E1-block resolve count other than
one, or any total/block count other than one for the other four literals.
Moving the exact frozen-byte preflight outside E1, adding a second E1
preflight, or weakening its root/length/SHA/Git-blob checks remains forbidden.

This is a test-oracle scope repair, not a runner behavior repair.  In
particular, R6 does not delete the second resolve call, duplicate a call to
satisfy a count, rename the frozen variables, move the all-lane count, or
alter Lane E1.

### Inherited general-attestation exception

R6 inherits verbatim the R5 P1 clarification.  The unchanged
`load_control_plane_attestation` inspects the general registered
`tracked_paths` set in every lane and may test existence or compute worktree
Git blobs for tracked paths.  That topology observation is not the runner's
six-row exact frozen-byte preflight.  It performs no E1 module import, pytest
collection, or scientific endpoint execution.

At the bootstrap anchor, the two new E1 paths are absent and the four
overlapping paths retain their predecessor blobs.  Thus dirty and clean B0 do
not contain or prewarm the preserved exact six-file E1 import.  The new exact
preflight remains inside Lane E1.

## 6. Preserved exact E1 source and endpoint

No E1 source, E1 test, formula, fixture, exact oracle, witness, or tier entry
may change in the R6 bootstrap.  Only after both bootstrap CI gates are green
may a fresh R6 build worktree import exactly these six files:

| bytes | SHA-256 | Git blob | path |
|---:|---|---|---|
| 153187 | `21030E4DD3C392D5EA2A9DEA1D5A8354F57AFE1301A59CFA6B0A2CDEE199EF16` | `1e1576ad1f51ebf667bc55d159048c0ae6587524` | `lean_rgc/odlrq/quotient_generator.py` |
| 87121 | `13C4F4D97AFFB363A1EC484BDDD870AF9FB88B0C0796D6728AC774DE941D5496` | `0618f603b86eba3c61c9fb2e15c4edaacce44a14` | `lean_rgc/odlrq/envelope.py` |
| 13341 | `F968B3BC4EB945811E88553F118856658CE45D476B94860B56D7F39DBE90D752` | `f97272d5de222fb555a78639d66eb89e77e63d86` | `lean_rgc/odlrq/__init__.py` |
| 59547 | `4D1FAF8C725BB2EA9FAD01E83A330C578B1ABE01840EAD263E98D174A84CA7C0` | `400f630e10ddbd98657fd1b142c6b202a8656c7d` | `tests/test_odlrq_quotient_generator.py` |
| 32675 | `90580302C24F99B8CAF1500EF013296E214D2206F6C936D781BAA8E8A64832D5` | `66f9be1a3c5455b822b229fc2024b9c58b768fff` | `tests/test_odlrq_envelope.py` |
| 8827 | `D955F797DFA2F4C0943F5F385F9301CED0A9D592BE19D459BF5EB2BEEB657854` | `8bb7810cc49b56aff3d7b18020dab475644911a2` | `tests/tier_manifest.json` |

The dirty path set must equal this six-path set.  A subset, superset,
reconstructed equivalent, regenerated fixture, changed test, formatting-only
edit, or altered manifest node is invalid.

The E1 LaneTests tuple remains exactly, in order:

```text
tests/test_odlrq_quotient_generator.py
tests/test_odlrq_envelope.py
tests/test_uprime_u2_u4_development.py
```

The official dirty E1 lane remains one Windows-CPU execution with exactly 48
passed tests, zero skip/xfail/deselection, a 120-second hard wall, the inherited
Job-object process/memory/output limits, and a wall at least three times its
cold single-lane calibration.  Stopwatch placement, Audit semantics, receipt
schema, and fail-closed behavior remain unchanged.

## 7. Frozen refs, stages, and correction budget

The only R6 refs are:

```text
bootstrap codex/uprime-u2-u4-development-r6-static-scope-bootstrap
build     codex/uprime-u2-u4-development-r6-build
closeout  codex/uprime-u2-u4-development-r6-closeout
failure   codex/uprime-u2-u4-development-r6-failure-closeout
accepted  codex/uprime-odlrq-plan
```

The only R6 terminal document paths are:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r6_closeout_2026-07-14.md
docs/experiments/uprime_odlrq_u2_u4_development_r6_failure_closeout_2026-07-14.md
```

The semantic stage order remains:

```text
E1 -> E2 -> ME0 -> S0 -> I0
```

E0 remains an immutable predecessor, not an R6 stage row.  E1 is exact and is
never correction-eligible.

R6 preserves one shared correction budget.  It may be consumed either by one
eligible bootstrap control correction or, if unused, by one later E2--I0
stage correction.  An eligible bootstrap correction may use only one of the
inherited control sets:

```text
tests/uprime_u24_guard.py
tests/test_uprime_u2_u4_development.py + tests/uprime_u24_guard.py
tools/run_uprime_u2_u4_development_tests.ps1 + tests/uprime_u24_guard.py
tests/test_uprime_u2_u4_development.py + tests/uprime_u24_guard.py + tools/run_uprime_u2_u4_development_tests.ps1
```

It may not change either R5 evidence document, this R6 amendment, the anchor,
decode, scope-count contract, E1 table, workflow, manifest, wall, test count,
Audit, or endpoint.  If used during bootstrap, no later correction remains.
If unused, one later E2--I0 correction may touch only the last stage's frozen
allowlist and may not change an earlier stage, control file, or endpoint.

## 8. Mandatory execution and CI order

The order is fixed:

1. Verify both exact section 3 document identities without changing their
   bytes.
2. In the clean R6 worktree at exact `b57ac55e...`, assemble exactly the six
   bootstrap paths from section 4.
3. Close the identity-core, canonical-guard, and normalized-runner hashes in
   the inherited acyclic order; guard logic must remain unchanged.
4. Run registered dirty B0 once while exactly those six paths are dirty.
5. Commit one indivisible six-path bootstrap as the immediate sole-parent
   child of `b57ac55e...`.
6. Run registered clean B0 on that exact commit.
7. Push only the R6 bootstrap candidate ref and require candidate CI to pass
   with exactly `2590 passed, 8 skipped, 161 deselected`.
8. Fast-forward the accepted ref to the identical bootstrap SHA/tree without
   merge, cherry-pick, rewrite, or omission, and require a distinct accepted
   CI with the same exact `2590 / 8 / 161` counts.
9. Only then create a fresh R6 build branch/worktree from the accepted
   bootstrap tip and import the exact six E1 files from section 6.
10. Verify all six byte lengths, SHA-256 values, and Git blobs before running
    the registered official dirty E1 lane once.
11. Only a qualifying 48-pass E1 receipt licenses the exact E1 commit.  That
    commit must pass candidate CI with exactly
    `2600 passed, 8 skipped, 161 deselected`, fast-forward identically to
    accepted, and pass a distinct accepted CI with the same exact counts
    before E2 source may exist.

The dirty and clean B0 runs are the runtime oracle for both Windows
PowerShell 5.1 decode/cardinality and the corrected identity scope assertion.
Static inspection alone is insufficient.  The stopped R5 run, a direct local
pytest invocation, parser-only check, cached run, old receipt, or green R4 CI
cannot substitute for either registered R6 B0.

## 9. Stop rules

R6 stops and records exactly one R6 failure closeout on any of:

- an R5 document byte-length or Git-blob mismatch;
- wrong anchor, parent, tree, R4 failure blob, accepted ref, or ancestry;
- missing, extra, duplicated, mixed, or early bootstrap/source path;
- a bootstrap commit that is not the immediate sole-parent six-path child;
- failure of dirty B0 or clean B0;
- one-stage decode, wrong PowerShell container shape, decoded count other than
  six, renamed decode variables, or decode moved under Lane E1;
- a resolve total other than two, E1-block resolve count other than one, or
  any wrong total/block count for the other four E1-preflight literals;
- movement, duplication, weakening, or out-of-scope execution of the exact E1
  frozen-byte preflight;
- red bootstrap candidate CI or red distinct accepted bootstrap CI;
- altered E1 byte, SHA-256, Git blob, formula, fixture, test, manifest, wall,
  margin, guard behavior, Audit, receipt, or endpoint;
- dirty or clean E1 failure, missing receipt, red E1 candidate CI, or red
  distinct accepted E1 CI;
- any E1 correction, second shared correction, illegal correction path, or
  correction that changes authority; or
- protected access, native Lean/RPC use, SSH, remote CPU, GPU, LLM, deployment,
  or any unregistered capability.

Bootstrap identity/runner failure uses
`U24_B0_IDENTITY_OR_RUNNER_BLOCKED`.  Exact E1 or E1-CI failure uses
`U24_E1_ENVELOPE_BLOCKED`.  Path/resource/capability expansion uses
`U24_RESOURCE_OR_SCOPE_BLOCKED`.  A stopped outcome remains evidence and is
not deleted, weakened, relabeled, or tuned into a pass.

## 10. Resource and capability boundary

R6 bootstrap and E1 work is local Windows CPU work under the inherited
Job-object process, memory, output, and wall limits.  GitHub Actions is used
only for the registered candidate and accepted repository gates.

R6 does not license:

- protected K1--K4 reads or protected-task evaluation;
- native Lean, Lake, Lean RPC, toolchain drift, or theorem-prover execution;
- SSH, remote CPU, GPU/CUDA, model server, or distributed execution;
- an LLM proposer, model weights, `pilot_tasks`, prompt generation, or
  knowledge distillation;
- MaxEnt fitting, global-similarity construction, locality learning, or ODLRQ
  learner training;
- artifact publication before EMIT;
- a workflow change, alternate runner, alternate shell, sidecar validator, or
  deployment; or
- any execution without both exact section 3 evidence documents.

## 11. Nonclaims

Passing R6 dirty and clean B0 proves only that the six-path control bootstrap,
including the unchanged PowerShell 5.1 two-stage decode and the corrected
scope-aware static assertion, is bound and executable under the registered
harness.  It does not prove E1.

Passing bootstrap candidate/accepted CI proves repository regression
compatibility at the pre-E1 tree.  It does not inspect the preserved E1
mathematics.

If E1 later passes, the claim is limited to the inherited
declared-synthetic finite-fiber envelope contract and its exact registered
tests.  It is not a general theorem about arbitrary fibers, infinite cutoffs,
solve-rate benefit, MaxEnt calibration, global similarity, Lean-oracle
locality, or LLM benefit.

The R5 B0 failure is useful control-plane evidence: it confirms that the
two-stage decode reached the identity oracle and that the static count was
overbroad.  It is neither positive nor negative scientific evidence about the
upper-stack theory.  R6 changes only that static assertion's scope and makes
no new mathematical claim before the separately registered E1 endpoint.
