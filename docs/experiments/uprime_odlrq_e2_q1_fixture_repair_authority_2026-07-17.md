# U-prime / ODLRQ E2 Q1 fixture-repair authority

Date: 2026-07-17 (Asia/Tokyo)

Status: **FROZEN WHEN THIS ONE DOCUMENT-ONLY SIDECAR COMMIT IS COMMITTED AND
PUSHED.**  This is a repair-definition authority, not a scientific execution
authority and not an E2 result.

## 1. Authority and scope

This document implements `FABLE-20260717-0005`, carrying the user's delegated
authority to repair implementation, runner, CI, and governance defects without
returning for per-attempt approval.  User escalation remains limited to a
theoretical refutation of the program or exhaustion of rational remedies.

Q0 remains closed at commit `0c5caa9459045d8a3dc87cca5b6e8689d82f8d4a`.
Its post-stop observation is forensic input only and is not scientific evidence.
Stage-1 reproduction independently established that semantic source B uses
synthetic fixture identifiers rejected by accepted E1's frozen namespace.

This document is the sole new path in a document-only sidecar commit whose sole
parent is Q0 closeout.  It is never merged into the E2 candidate or accepted
line.  The old E2 runner is present byte-identically in the sidecar tree and
history; Q1 forbids invoking, editing, copying, or using it as evidence.  The
separate semantic candidate tree does not contain that runner.

The freeze identity is exact:

```text
ref      codex/uprime-e2-repair-authority-q1
subject  uprime: authorize E2 Q1 fixture repair
parent   machine-resolved origin/codex/uprime-e2-qualification-closeout^{commit}
paths    this document only
push     one non-force creation; never amended, repointed, deleted, or forced
```

Its one natural push CI is a control observation, not scientific evidence.  It
must have the inherited known topology-only shape: exactly `2599 passed, 1
failed, 8 skipped, 161 deselected`, sole failed node
`tests/test_uprime_u2_u4_development.py::test_u24_b0_anchor_contiguous_budget_and_terminal_topology`,
and zero `test_odlrq_selection.py` / `::test_e2_` hits.  Exact match licenses
creation of the semantic correction.  Any other shape blocks that next step
for a rational control diagnosis; it is not a mathematical refutation.

## 2. Inherited endpoint authority

Endpoint authority A0 at `28c5a29000dddadcaf3e9ad9dd5534554dd67f32`
continues to define, without alteration:

- the source/target coordinate identification and parent-envelope restriction;
- retained/complement P/Q split and weighted-norm orientation;
- the complete pre-threshold literal three-candidate universe; and
- the binding certified-support selection, ranking, and fallback.

A0 also froze raw `u24_e2_source_*` / `u24_e2_target_*` fixture spellings.
Those spellings contradict accepted E1's synthetic-admission contract.  This
Q1 repair authority supersedes A0 only for that namespace spelling and for the
semantics-preserving serializer derivation described below.  All mathematical
and endpoint definitions above remain inherited from A0.

## 3. Exact permitted correction

The only identifier transformation is the bijection

```text
u24_e2_source_* -> unit_cpu_survivor_u24_e2_source_*
u24_e2_target_* -> unit_cpu_survivor_u24_e2_target_*
```

applied to the two action identifiers and nine state/payload identifiers in
production fixture reconstruction and its independent test.  No canonical
base-fixture identifier value may equal an unprefixed spelling.  The canonical
production and independently rederived test base-fixture sets must be equal;
deliberately invalid negative-mutation fixtures are outside that equality.

The correction may also eliminate redundant repeated serialization and exact
derivation, but only by deriving maps from an already fully validated wire,
requiring exact coverage, rejecting duplicates, preserving canonical order,
and hashing the same fresh wire.  Instance-level serializer overrides must be
rejected before invocation, and the exact class's unbound serializer must be
used.  Persistent graph/wire memoization, accepted-parser bypass, mutation
hiding, permissive parsing, schema change, and result-value change are forbidden.

The correction must preserve endpoint ID, universe ID, coordinate order, all
five matrices, exact rational coefficients, laws, weights, P/Q split, P1/P2
cocycles, return-memory horizon, candidates, threshold, ranking, dispositions,
public schemas, and the existing ten test node names.

## 4. Git topology and path budget

The correction is one local semantic commit whose sole parent is semantic B,
resolved mechanically as parent 2 of remote
`codex/uprime-e2-endpoint-runner-control`.  Against B it may modify exactly:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/selection.py
tests/test_odlrq_selection.py
```

Against machine-resolved accepted E1, its final tree must retain the original
four E2 paths, with unchanged `tests/tier_manifest.json` as the fourth path.
The B and correction manifest blobs must compare equal by `git rev-parse`.
No no-op manifest edit is permitted.

At correction finalization,
`origin/codex/uprime-odlrq-plan^{commit}` and
`origin/codex/uprime-u2-u4-development-r6-build^{commit}` must resolve equal;
that machine-derived commit is the accepted-E1 comparison base.

The correction's production and test modules must record both provenance
layers.  Existing `E2_AUTHORITY_*` constants remain A0 provenance.  The exact
module-level, non-wire additions are:

```text
E2_Q1_REPAIR_AUTHORITY_COMMIT_SHA
E2_Q1_REPAIR_AUTHORITY_TREE_SHA
E2_Q1_REPAIR_AUTHORITY_DOCUMENT_PATH
E2_Q1_REPAIR_AUTHORITY_DOCUMENT_BLOB_SHA
```

They are exported by `certificates.py` and independently repeated and asserted
for exact equality in the first existing E2 test.  They are not inserted into
any public certificate wire, schema, digest domain, endpoint ID, or candidate
row.  Their values are obtained after this commit by `git rev-parse` of the
frozen remote ref, `^{tree}`, and `commit:path`; no handwritten value is a gate.
The insertion/check script must resolve the pushed repair-authority ref and
compare all four resolved values against all four production constants and all
four independently repeated test constants.  The later qualification preflight
repeats the same three-way machine comparison and binds the exact resulting
correction commit, avoiding a circular provenance dependency.

## 5. Required pre-publication evidence

Before the correction is eligible for qualification:

1. all existing ten E2 test nodes pass on Windows CPU;
2. strict JSON round-trip, unknown-field, noncanonical-rational, returned-dict
   isolation, subclass, stale-authority, bomb, and serializer-override attacks
   remain exercised inside those same ten nodes;
3. adjacent E1 envelope/partition/generator regressions pass;
4. the full local suite is green; and
5. a read-only adversarial diff review finds no endpoint-value or trust-boundary
   drift.

These are development diagnostics.  They consume no Q1 scientific look.

## 6. Historical red-CI clarification

**Recorded 2026-07-17; events of 2026-07-16:** immutable U05 result commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run `29166670576`,
job `86580832840`, because the guard omitted shallow-history handling.  Audit
authority `628d3cc64af2531da3a527bad335d9e5158294a7` adjudicated that cause.  The
exact scientific candidate `3bb3408afc50a08307cff2c9b1906a299739dfb5` had
green candidate run `29166073728`, job `86579287017`.  The red result badge is a
control/guard design defect and must not be read as a scientific U05 failure.

## 7. Forbidden work

This repair authority licenses no scientific look, candidate/accepted ref
movement, Actions rerun, protected K1-K4 read, reserved data, GPU, SSH, LLM,
MaxEnt, similarity, integration, locality learner, or other upper-stack work.
Q1 execution requires a second document-only qualification freeze that binds
the exact correction commit and implements marker-based one-look semantics.
