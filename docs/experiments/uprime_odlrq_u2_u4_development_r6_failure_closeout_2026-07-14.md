# U-prime / ODLRQ U2--U4 R6 failure closeout

Date: 2026-07-14 (Asia/Tokyo)

Status: `U24_E2_ENVELOPE_BLOCKED`

E1 stage disposition: `PASSED / COMMITTED / PUSHED / ACCEPTED`

E2 stage disposition: `NOT_CREATED / NOT_RUN / NOT_COMMITTED / NOT_PUSHED /
NOT_EMITTED / NOT_ACCEPTED`

Subcause: `E2_PUBLIC_ENDPOINT_SEMANTICS_NOT_UNIQUELY_FROZEN`

Scientific interpretation: `NON_MATHEMATICAL_PREIMPLEMENTATION_SPECIFICATION_BLOCKER`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_r6_static_scope_reentry_amendment_2026-07-14.md`
at accepted R6 E1 commit
`6fb35aa229fc60e2220cbb68c1e7fff2ce64f199`.

R6 closes after exact E1 succeeded and before any E2 source, test, or runner
invocation existed.  This document preserves the accepted E1 result and the
preimplementation E2 blocker without changing the E2 endpoint after seeing a
result, consuming the R6 correction, or treating a specification failure as a
theory refutation.

## 1. Immutable accepted R6 E1 result

The accepted R6 E1 commit is

```text
commit 6fb35aa229fc60e2220cbb68c1e7fff2ce64f199
parent 628d3cc64af2531da3a527bad335d9e5158294a7
tree   b3fc7f21b6420e718eb954be0c1b5affca65d263
```

Its subject is `uprime: qualify exact E1 fiber envelope`.  It changed exactly
the six registered E1 paths:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/envelope.py
lean_rgc/odlrq/quotient_generator.py
tests/test_odlrq_envelope.py
tests/test_odlrq_quotient_generator.py
tests/tier_manifest.json
```

The registered official dirty E1 lane ran once and passed exactly 48 tests,
with zero skip, xfail, or deselection.  It therefore qualified the inherited
declared-synthetic finite-fiber envelope endpoint before the E1 commit was
created.

The exact E1 commit then passed candidate CI run `29319408137`, job
`87040865525`, with exactly:

```text
2600 passed, 8 skipped, 161 deselected
```

The identical SHA and tree were fast-forwarded to the accepted ref and passed
distinct accepted CI run `29319601638`, job `87041508414`, again with exactly:

```text
2600 passed, 8 skipped, 161 deselected
```

Thus E1 is a successful accepted scientific-development result.  Nothing in
this closeout weakens, reruns, relabels, or supersedes it.  Its claim remains
limited to the complete declared finite synthetic rectangle and the exact
registered E1 tests; it is not a production Lean or all-germ certificate.

## 2. E2 was not created or executed

After the distinct accepted E1 CI passed, implementation review examined the
already frozen E2 text before source creation.  At that point:

- no E2 source file or source edit existed;
- `lean_rgc/odlrq/selection.py` and
  `lean_rgc/odlrq/certificates.py` had not been created;
- no E2 test or tier-manifest node had been added or changed;
- no E2 runner child, pytest selection, receipt, candidate commit, candidate
  CI, accepted CI, or artifact existed; and
- no E2 fixture outcome or threshold result had been observed.

The E2 execution count is therefore exactly zero.  The blocker was found at
the specification boundary, not by tuning or inspecting a failed synthetic
endpoint.

## 3. Preimplementation endpoint blocker

Section 10 of the construction-bundle authority gives the finite-horizon
cocycle inequality and the formal return-memory expression

```text
R_h = sum_(k=0)^(h-1) M_PQ (M_QQ)^k M_QP,
```

but it does not uniquely determine the public typed restriction and
return-memory contracts needed to implement that expression without choosing
new endpoint semantics in source code.  The unresolved items are:

1. **Exact envelope restriction.**  No public
   `EnvelopeRestrictionWitness` schema fixes how a restricted matrix retains
   and rederives its E1 envelope authority, row/column block identities,
   weights, coverage, canonical ordering, and digest.  A caller-supplied or
   incompletely bound submatrix could sever the E1 majorant from the E2
   certificate.
2. **Retained/memory split.**  The phrase “declared retained `P` block and
   memory `Q` block” does not state whether `P` and `Q` must be nonempty,
   disjoint, exhaustive, ordered subsets of one square domain, nor whether
   source/target block orders and weights must coincide.  A nonexhaustive
   split can omit a return path and understate the memory bound.
3. **Block orientation and weighted norm.**  Although the global convention
   is column-source, the public split contract does not explicitly type
   `M_PQ`, `M_QQ`, and `M_QP`, identify the positive weight used by each
   reported weighted `1`-norm, or freeze the exact norm formula.  Different
   admissible readings produce different certified values and pass decisions.
4. **Candidate-universe authority.**  Binding a denominator over “all
   registered candidates” does not specify a pre-gate immutable candidate
   universe.  A caller can otherwise omit a candidate before registration,
   making coverage and the binding-gate endpoint selectively vacuous even
   though the support token is internally consistent.

These are not missing test cases for an otherwise unique implementation.
They admit multiple non-equivalent public APIs and can change the numeric
bound, coverage denominator, or soundness scope.  Selecting one interpretation
inside E2 source would define a supposedly frozen endpoint after the freeze.
The appropriate fail-closed action is therefore to create no E2 source.

The review did not challenge the already registered finite-horizon formulas,
the exact E1 arithmetic, or the upper mathematical program.  It also did not
claim that no sound restriction, split, norm, or candidate-manifest design
exists.  It found only that the current authority does not select one
unambiguously enough for a public certificate endpoint.

## 4. R6 correction is unused and inapplicable

R6 preserved one shared correction budget.  It was not consumed during the
bootstrap or E1, so its recorded state at closeout is `UNUSED`.

That correction nevertheless cannot resolve this blocker.  Section 7 of the
R6 authority permits a later E2--I0 correction only within the last stage's
frozen source allowlist and expressly forbids changing an endpoint or its
authority.  Defining the public restriction witness, P/Q split, weighted norm,
and pre-gate candidate universe would change or complete the E2 endpoint
semantics rather than repair an implementation of already unique semantics.

The correction therefore remains unused and is `INAPPLICABLE_TO_ENDPOINT
CLARIFICATION`.  It is not spent on a document-only workaround, an ad hoc
fixture interpretation, or a post hoc source convention.

## 5. Frozen adjudication and capability boundary

R6 terminates at:

```text
U24_E2_ENVELOPE_BLOCKED
subcause: E2_PUBLIC_ENDPOINT_SEMANTICS_NOT_UNIQUELY_FROZEN
```

This is a preimplementation governance/specification result.  It is not an E1
failure, E2 numerical failure, counterexample to the finite-horizon theory, or
evidence that the upper-stack program is impossible.

No protected K1--K4 result or protected task was read.  No native Lean, Lake,
Lean RPC, theorem-prover execution, SSH, remote CPU, GPU/CUDA, model server,
LLM proposer, model weights, knowledge distillation, or deployment was used.
ME0, S0, I0, EMIT, and success CLOSEOUT were not created or executed.  No
MaxEnt fit, global-similarity construction, locality learner, artifact
publication, or additional evidence ledger was produced.

## 6. Sole continuation route

The only continuation is one separately dated and frozen R7 narrow
clarification/re-entry authority, anchored at the immutable commit containing
this R6 failure closeout.  Before any E2 source exists, R7 must uniquely freeze:

- the exact parent-envelope restriction authority and strict public wire;
- the P/Q domain, completeness, compatibility, and block-orientation rules;
- the positive weights and exact weighted-norm formula;
- the pre-gate immutable candidate-universe manifest, denominator, and
  per-candidate accounting; and
- the corresponding scope, stale-authority, undercoverage, selective-
  preregistration, and matrix-order kill tests.

R7 must preserve the accepted E1 commit and tests byte-for-byte, preserve the
synthetic-development and finite-domain nonclaims, and license at most a fresh
E2 attempt under the clarified endpoint.  It may retain the already frozen
contingent `ME0 -> S0 -> I0` continuation after accepted E2, but it may not
alter or broaden those later endpoint semantics or start them before distinct
green E2 candidate and accepted CI.  It may not rerun E1, import a protected
result, or multiply this blocker into additional amendments, artifacts,
ledgers, or infrastructure.  This closeout records the questions R7 must
settle; it does not itself select their answers or license implementation.
