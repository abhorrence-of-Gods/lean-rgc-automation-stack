# U-prime / ODLRQ KP3 depth-four canonical-history closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: **CLOSED — ONE-SHOT NATIVE EXECUTION FAILED BEFORE SCIENTIFIC
EVALUATION; C1/C2 REGISTERED UNIT AND HOSTED-CI CHECKS GREEN**

Controlling registration:
`docs/experiments/uprime_odlrq_kp3_d4_canonical_history_amendment_2026-07-12.md`.

The filename retains the date frozen by that registration.  This is the single
E1-C document permitted by the amendment.  It changes only this file, has the
accepted immutable E1-R commit
`1f68ec353dfd8b409201838cbe720db4347aab3e` as its sole parent, and closes the
phase without a repair, retry, or second protected look.

## 1. Executive disposition

The phase has two different outcomes that must not be conflated:

1. The pure finite C1 canonical-history core and the C2 native-adapter/control-
   plane fixtures were implemented, adversarially reviewed, and independently
   green on their candidate and accepted refs.
2. Contemporaneous terminal output from the exactly-once E1 execution, which
   is not retained inside the immutable artifact, reported exit code 1 and
   `ModuleNotFoundError: No module named 'numpy'` after the durable
   `RUN_OPENED` marker was installed.  The frozen `-I -S` import chain through
   `lean_rgc.__init__`, `defect_miner`, and `numpy` is consistent with that
   operator-observed diagnosis.  The artifact itself records only the durable
   failure marker.

The final scientific disposition is therefore exactly:

```text
D4_EXECUTION_FAILED
```

No depth-four matrix, rank, compression ratio, plateau, conditioning value, or
upper-stack feasibility endpoint was observed.  Green hosted CI for E1-R means
only that the immutable failure artifact was accepted by the repository's
control plane; it is not a successful scientific result.

## 2. Frozen commit and branch topology

The registered topology was followed without repair commits:

| work package | fixed ref | commit | parent | changed scientific/implementation scope |
|---|---|---|---|---|
| A0 | `codex/uprime-kp3-d4-a0` | `ece0305d424c65927073662b071e5398e5f478a1` | `5bb86a4...` | amendment, frozen inputs, identity guard, and manifest append |
| C1 | `codex/uprime-kp3-d4-c1` | `67bb1115451a69775b3788ec8d61276d6c753fdc` | `ece0305...` | pure canonical-history and exact D4 core |
| C2 | `codex/uprime-kp3-d4-c2` | `06535530ab2a3137984b4f824e4c53c0ffe73b2e` | `67bb111...` | native adapter and fixed Windows runners |
| E1-R | `codex/uprime-kp3-d4-result` | `1f68ec353dfd8b409201838cbe720db4347aab3e` | `0653553...` | immutable artifact only |
| E1-C | `codex/uprime-kp3-d4-closeout` | this one closeout commit | `1f68ec3...` | this document only |

C1 and C2 each used one semantic commit; their unused repair quotas were not
transferred.  E1-R has one immutable commit and no repair license.  No fixed ref
was deleted, restarted, or force-pushed.

## 3. C1/C2 implementation evidence

C1 established the pure finite substrate required by the imported Part 2
technique: generation-time canonical history, reconstruction witnesses, exact
raw-versus-normalized response equality, bounded exact Hankel construction,
and rank certificates.  C2 added the fresh-family fixed-point adapter, exact
handle ownership, total action expansion, duplicate-OPEN falsification audit,
typed failure dispositions, persisted-domain/matrix/rank authority, and the
fixed Windows qualification/official runners.

The following local timings and review counts are dated operator/session
governance evidence, not fields attested by the E1 artifact.  Three independent
final adversarial reviews found no P0/P1 in the C2 candidate.  The dedicated
native unit runner passed 26 tests on five consecutive invocations:

| invocation | qualification elapsed | peak working set |
|---:|---:|---:|
| 1 | 5.165 s | 57,794,560 B |
| 2 | 5.758 s | 57,434,112 B |
| 3 | 6.319 s | 57,262,080 B |
| 4 | 5.230 s | 57,462,784 B |
| 5 | 5.681 s | 57,888,768 B |

All stayed below the frozen 10-second qualification margin and 2 GiB
working-set cap.  PowerShell parsing, the embedded Python bootstrap AST, and
the Job Object C# source also passed their pre-commit checks.  These results
validate the deterministic engineering fixtures; they did not exercise the
official child's isolated package-import path.

## 4. Hosted CI adjudication

Candidate and accepted CI were distinct and green at every admitted commit:

| work package | candidate CI | accepted CI |
|---|---|---|
| A0 `ece0305...` | run `29185484248`, job `86630695060`, success | run `29185595381`, job `86630995221`, success |
| C1 `67bb111...` | run `29201488433`, job `86673525468`, success | run `29201621405`, job `86673861218`, success |
| C2 `0653553...` | run `29212316098`, job `86702006527`, success | run `29212442614`, job `86702339196`, success |
| E1-R `1f68ec3...` | run `29212767838`, job `86703166343`, success | run `29212881766`, job `86703471299`, success |

The earlier U05 red result-commit badge and green candidate run
`29166073728` are already dated and explained in the controlling amendment:
that red badge was a shallow-history guard defect, not a scientific failure.
The present E1 scientific failure is different: both publication-control CIs
are green, while the immutable artifact itself records failure.  Future readers
must use the artifact disposition, not badge color, to distinguish these cases.

## 5. Exactly-once execution record

The official execution ran once in the clean dedicated worktree on
`codex/uprime-kp3-d4-result`, after C2 candidate and accepted CI were green.
Its externally checked control-plane identity was:

```text
C2 commit                 06535530ab2a3137984b4f824e4c53c0ffe73b2e
C2 tree                   651b1f5193396dcf10fecd4959e41da57794258c
C2 candidate run/job      29212316098 / 86702006527
C2 accepted run/job       29212442614 / 86702339196
```

PowerShell, Python, Lean, the worker/client blobs, both registered input raw
digests, and all five C2 file SHA-256 values matched the frozen identities
before `RUN_OPENED`.  The parent then installed the durable marker and started
the exact isolated child.  Contemporaneous terminal output, which is not stored
in the immutable artifact, reported exit code 1 and this import failure:

```text
lean_rgc.__init__
  -> lean_rgc.defect_miner
  -> import numpy as np
  -> ModuleNotFoundError: No module named 'numpy'
```

Given that operator-observed traceback and the frozen import ordering,
`official_child_main`, task parsing, and native initialization are inferred not
to have been entered.  The immutable artifact independently establishes only
that no scientific response, matrix, or rank evidence was persisted.  No
complete nonce stage/receipt pair remained, so the runner retained the already
durable marker and reported that `RUN_OPENED` remains final.  The dated
operator/session record states that the process was not restarted.

## 6. Immutable artifact

The sole E1-R file is:

```text
docs/experiments/artifacts/uprime_kp3_d4_20260712/fresh_family_d4.json
```

Its frozen identity is:

| property | value |
|---|---|
| byte length | 2,236 |
| SHA-256 | `58DFBBF89EAEF244726655F4EF4A866990C67B7256096ED1F330A11DD3D0F83E` |
| Git blob | `cfe261b49ed7207c3011dbf10673421bdc532828` |
| E1-R commit | `1f68ec353dfd8b409201838cbe720db4347aab3e` |

Independent post-open audits verified strict UTF-8 without BOM, no duplicate or
unknown keys, canonical compact JSON, exact field order and types, exact
commit/tree/run/job/input/runtime attestations, no trailing newline, and no
remaining `.stage.*`, `.receipt.*`, or `.parent-resource.*` file.  The artifact
directory contains only this file.

The authoritative fields are:

```text
run_state               RUN_OPENED
scientific_disposition  D4_EXECUTION_FAILED
failure_reason          process_or_os_terminated_after_open
matrix                  null
rank                    null
conditioning            null
conditioning_censor     NOT_ATTEMPTED_IN_THIS_PHASE
```

The dedicated `validate_run_opened_artifact` path accepts the marker.  The
ordinary-result `validate_official_artifact` path rejects `RUN_OPENED` with a
run-state mismatch.  This split is consistent with the runner's two artifact
variants but is easy to misuse; a future unprotected control-plane phase should
expose an explicit sum-type validator rather than calling the ordinary-result
validator on a durable open marker.  It does not authorize changing this
artifact or rerunning E1.

## 7. Exposure, resource, and governance accounting

Except where a value is present in the immutable artifact, the negative-use
statements below are dated operator/session governance attestations rather than
claims recoverable from the artifact alone.

- Construction, unit qualification, and the official attempt used local
  Windows CPU only.
- Network use was limited to Git push and read-only hosted-CI inspection.
- No SSH session, remote CPU, GPU, CUDA, model server, LLM proposer, or LLM
  distillation was used.
- The parent read registered input byte streams for frozen identity hashing.
  Given the operator-observed traceback and frozen import ordering,
  `official_child_main`, task parsing, and Lean execution are inferred not to
  have been entered.  The artifact independently proves only that no scientific
  response, matrix, or rank evidence was persisted.
- Nevertheless, `RUN_OPENED` makes the registered one-shot consumed.  There is
  no same-family rerun, cap relaxation, dependency installation, import repair,
  result amendment, or replacement artifact in this phase.
- The known unrelated user-owned `docs/external` worktree changes were never
  staged or included in A0, C1, C2, E1-R, or E1-C.
- No new EvidenceLedger, CAS, fake publisher, or per-unit preregistration
  hierarchy was introduced.

## 8. Scientific interpretation and gate decision

This failure is an endpoint/integration failure, not evidence for or against
the canonical-history, worst-case-envelope, MaxEnt, global-similarity, or
locality-learning hypotheses.  In particular:

- C1's pure finite exact construction remains verified on its declared finite
  fixtures.
- C2's native adapter and evidence validators remain engineering assets, but
  the official isolated launch path is not qualified by this result.
- No `r_4`, rank-cap comparison, family-specific plateau/growth statement, or
  native compression estimate exists.
- The prerequisite for using this fresh-family D4 endpoint to license the
  large predictive/MaxEnt/similarity investment was not met.
- No hard envelope, MaxEnt law, global-similarity certificate, learner
  improvement, solve-rate claim, deployment, SSH/GPU phase, or LLM phase is
  licensed by this closeout.

The observed failure matches the 2026-07-10 adversarial verdict's surviving
risk: the theory did not die here; the implementation/runtime endpoint failed
before it could test the theory.

## 9. Registered direction after closeout

This phase cannot be extended.  A later, separately registered, unprotected
control-plane work package may repair the general execution substrate, but it
must not rerun this same fresh-family endpoint.  Before any new protected
one-shot, that work package should require all of the following on synthetic
inputs:

1. launch the exact `-I -S` child and import its real official entrypoint before
   any durable result marker or protected input path is available;
2. make the official entrypoint's dependency closure explicit, source-bound,
   and compatible with the isolated environment rather than relying on an
   ambient site package;
3. exercise the full PowerShell-to-Python-to-Lean process graph on an
   unprotected finite fixture, including nonce stage/receipt and atomic result
   replacement;
4. expose one artifact sum-type validator that accepts and distinguishes
   `RUN_OPENED`, ordinary result, and resource-failure variants;
5. freeze a new task family, endpoint, caps, and no-retry rule before a new
   scientific look.

The upper-stack order itself remains unchanged:

```text
verified exact finite domain
  -> generation-time canonical history
  -> exact behavioral quotient
  -> quotient-coordinate generator
  -> positive finite-horizon worst-case majorant
  -> MaxEnt nominal law constrained inside that majorant
  -> predictive and positive global similarities with typed transports
```

The locality learner remains a separate nominal proposal track: it retains
ghost actions, uses Lean counterexamples only to force splits, measures rather
than assumes separator correction rank, and never supplies a hard merge or
safety bound.  GPU work remains reserved for a later learned representation;
LLM proposal or knowledge distillation remains last, after the theory-driven
generator and upper pipeline independently work under a new contamination and
runtime registration.

## 10. Mandatory nonclaims

This closeout does not convert C1 fixture exactness into native production
exactness, absence of a result into rank evidence, green CI into scientific
success, or a packaging failure into a refutation of the mathematical program.
It claims no same-U05-family depth-four result, all-germ quotient, hard fiber
envelope, MaxEnt safety, global similarity, production locality, statistical
performance, or deployment readiness.  The durable failure artifact, consumed
look, and no-rerun decision are final.
