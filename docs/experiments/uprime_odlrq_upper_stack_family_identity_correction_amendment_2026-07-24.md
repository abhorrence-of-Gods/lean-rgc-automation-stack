# U'2--U'4 finite upper-stack family-identity correction amendment

Date frozen: 2026-07-24 (Asia/Tokyo)

Status: fresh pre-source authority; no scientific endpoint is executed here

Authority stage key: `A_FI`

Authority ref:
`refs/codex-authority/uprime-upper-portability-family-identity-20260724`

Parent commit:
`2d40f55748014cac531d83e45882eb9e7ebb9bd3`

Parent tree:
`889abb2417a03c472cde5964c5fd88b1231e47ef`

Selected parent authority:
`refs/codex-authority/uprime-upper-portability-guard-correction-20260723-a2`

This commit changes exactly this document.  It is pushed only to the custom
authority ref above and receives no GitHub Actions run.  It has no `-a2`
sibling.  A defect found after publication requires another genuinely fresh
pre-source authority rather than an amendment attempt under this ref.

## 1. Scope and reason

The selected guard-integrity authority is retained.  This document overrides
one under-specified identity edge and only the clauses that necessarily depend
on it.  All mathematical objects, four frozen families, matrix bytes, exact
expected values, hard and nominal dispositions, thresholds, test counts,
evidence tiers, resource rules, and protected-data prohibitions remain
unchanged.

The frozen public API contains
`build_finite_upper_stack(spec) -> FiniteUpperStackResult`.  The exact
`FiniteUpperStackResult` family-result wire requires `family_id`, but the exact
`FiniteUpperStackSpec` wire and its complete retained-authority registry contain
no source for that identity.  The missing value cannot be recovered from
`family_input_sha256`, selected by a family-dependent branch, or supplied from
ambient state without violating the selected authorities.

This is a type/wiring contradiction, not a failure of the worst-case envelope,
finite memory, MaxEnt, similarity, any family calculation, or any endpoint.
No H_GC, G1, G2, G3, or G4 source commit exists remotely when this amendment is
frozen.  The correction is therefore a pre-source schema closure, not a
post-result reinterpretation.

## 2. Frozen ancestry and precedence

The selected first-parent order is now:

```text
H -> A_GC -> A_FI -> H_GC -> G1 -> G2 -> G3 -> G4 -> A_RES -> R
```

Here:

- selected `A_GC` remains commit
  `2d40f55748014cac531d83e45882eb9e7ebb9bd3`;
- rejected primary `A_GC` commit
  `557fb03a92c37487110bab99caf98fd10436d9d1` and its immutable ref remain
  rejected historical provenance;
- `A_FI` is this document-only child of selected `A_GC`;
- H_GC is a direct child of selected `A_FI`, not directly of `A_GC`;
- G1 remains a direct child of selected accepted H_GC, and all later semantic
  ordering is unchanged.

This precedence overrides only the A_GC-a2 statements that made H_GC a direct
child of A_GC and that omitted A_FI from ancestry and closeout.  Every other
A_GC-a2 obligation remains binding.

The H_GC attempt refs, the accepted ref, G1--G4 refs, A_RES ref, and R ref keep
their frozen names.  A_FI has no candidate or accepted CI row and is not added
to the H/H_GC/G1/G2/G3/G4 stage-prefix product.

The exact identity maps gain:

```text
STAGE_ORDER includes A_FI immediately after A_GC and before H_GC
STAGE_ATTEMPT_REFS[A_FI] =
  (refs/codex-authority/uprime-upper-portability-family-identity-20260724,)
STAGE_ALLOWLISTS[A_FI] = {
  docs/experiments/uprime_odlrq_upper_stack_family_identity_correction_amendment_2026-07-24.md
}
STAGE_MANIFEST_ROWS[A_FI] = {}
```

## 3. Exact `FiniteUpperStackSpec` schema correction

The schema identity remains:

```text
odlrq.finite-upper-stack.spec.v1
```

No v1 source or wire has been published.  Its exact ordered wire fields are
closed pre-source as:

```text
schema_version
family_id
family_input_sha256
coordinate_split_sha256
restriction_sha256
safety_sha256
return_memory_sha256
maxent_problem_sha256
ordered_level_sha256
ordered_morphism_sha256
direct_quotient_residual
memory_forcing_radius
hard_threshold
object_sha256
```

`family_id` and `family_input_sha256` are actual public frozen-dataclass
identity fields.  `family_id` has exact type `str`.
Its strict identity gate is: exact `str`, strict UTF-8 encoding, and encoded
length in `1..128` bytes.  No Unicode normalization or other transformation is
performed.  This bounded validation may fail closed but may not influence a
mathematical value or disposition.  `family_input_sha256` has exact type
`str` and is exactly 64 uppercase hexadecimal characters; it is the SHA-256 of
the complete frozen family-input canonical wire, independently derived by the
evaluator.  Neither field is mathematical or structural-join data.  Both
remain identity/opaque under the A_GC-a2 three-way field registry.  There is no
private `_family_id`, private family-input digest/cache, digest-to-label table,
or additional retained typed authority.

The complete private retained-authority registry for
`FiniteUpperStackSpec` remains exactly:

```text
_coordinate_split
_restriction
_safety
_return_memory
_maxent_problem
_ordered_levels
_ordered_morphisms
_ordered_positive_distances
_ordered_predictive_distances
```

The exact `FiniteUpperStackResult` wire is unchanged.  Its existing
`family_id` field is supplied only by the typed Spec identity described below.

## 4. Two closed identity flows

The complete-row flow is:

```text
frozen matrix family_order[ordinal]
  + canonical family-input wire SHA-256
  -> FiniteUpperStackSpec(
       family_id=...,
       family_input_sha256=...
     )
  -> retained typed (Spec.family_id, Spec.family_input_sha256)
  -> FiniteUpperStackResult(
       family_id=...,
       family_input_sha256=...
     )
  -> complete registered whole-wire serialization/comparison
```

The non-complete-row flow is:

```text
frozen matrix family_order[ordinal]
  + canonical family-input wire SHA-256
  -> strict evaluator prerequisite/execution family-row constructor
       (
         expected_family_id=...,
         expected_family_input_sha256=...
       )
  -> complete registered partial-row serialization/comparison
```

`FiniteUpperStackResult` is the complete typed family result.  A prerequisite-
blocked or execution-failed family row is a strict closed evaluator variant of
the same family-row wire, with the parent-frozen nullability prefix; it is not
fabricated as a complete typed Result with missing private authorities.

The evaluator processes the raw-hash-pinned matrix in numeric family order.
It takes the label from `family_order[ordinal]` and the family data from
`families[ordinal]`.  The complete raw matrix hash and ordered family-input
wire bind their frozen relationship; there is no family-ID comparison or
lookup dispatch.  The family row's literal `family_id` remains inside the
complete family-input authority and its digest, but does not select an
algorithm.

A Spec constructor accepts the externally retained expected family label and
family-input SHA-256 as identity-only arguments and places them directly in
the same-named Spec fields.
`build_finite_upper_stack(spec)` may, after its exact Spec type guard, the
bounded identity gate above, retained-authority reconstruction, and complete
nonidentity verification, pass `spec.family_id` and
`spec.family_input_sha256` directly to the same-named Result constructor
keywords.
A single-assignment, single-use local is also permitted.  No generic
container, helper, transformation, comparison result, or digest mediates this
flow.

This is one narrow exception to the A_GC-a2 independent-fresh-origin rule:
inside one-argument core construction/reverification, supplied typed
`Spec.family_id` and `Spec.family_input_sha256` are the retained opaque input
identity pair and are not called freshly reverified or independently derived.
A fresh expected Spec may reuse only that pair after the exact Spec guard and
both bounded identity gates; every nonidentity field and every retained typed
authority is reconstructed independently.  The complete Spec comparison then
binds the retained pair to the stored wire and the fresh nonidentity content.
No other supplied semantic, structural, digest, or opaque field receives this
exception.

Core construction does not claim to infer the semantic truth of the label.
The exact matrix read and numeric evaluator position are its external identity
authority.  Core hard and nominal calculations are invariant under replacing
only this label while leaving all typed mathematical authorities unchanged.

## 5. Parsing and verification

The Spec factory is exactly
`lean_rgc.odlrq.finite_upper_stack.make_finite_upper_stack_spec` with no
positional arguments and the following exact keyword set:

```text
expected_family_id
expected_family_input_sha256
coordinate_split
restriction
safety
return_memory
maxent_problem
ordered_levels
ordered_morphisms
ordered_positive_distances
ordered_predictive_distances
direct_quotient_residual
memory_forcing_radius
hard_threshold
```

`FiniteUpperStackSpec.from_dict` has positional `value` after `cls`, no other
positional input, and the identical exact keyword-only set.  There are no
defaults, `*args`, or `**kwargs`.  Both expected identity parameters pass
their bounded gates and must be function inputs whose dataflow is independent
of the raw mapping; no local assignment, subscript, lookup, default, variadic
argument, or helper may derive either from `value`.  The parser constructs a
fresh expected Spec through the exact factory, then performs the single
complete raw-wire versus expected-wire canonical inequality-or-raise.  The raw
mapping's `family_id` and `family_input_sha256` may not construct or justify
the expected identity pair.

`FiniteUpperStackResult.from_dict` has positional `value` after `cls` and exact
keyword-only inputs `spec`, `maxent_result`, `ordered_levels`,
`ordered_morphisms`, `ordered_positive_transports`,
`ordered_predictive_transports`, and `ordered_hard_factors`, with no defaults
or variadics.  Together with the exact two-positional-argument public
`verify_finite_upper_stack(spec, result)`, it reconstructs the expected
complete Result from a freshly verified typed Spec and the freshly verified
retained G2/G3 results.  The expected Result identity pair is copied from that
separately supplied Spec under the narrow retained-identity rule in section 4.
A raw Result identity may not construct or justify itself.

The non-complete sinks are exactly four private functions in
`lean_rgc.evals.uprime_u24_upper_stack_portability`:

```text
_build_prerequisite_blocked_family_row
_verify_prerequisite_blocked_family_row
_build_execution_failed_family_row
_verify_execution_failed_family_row
```

They are not new public mathematical types.  Each has only explicit
keyword-only inputs after the verifier's single positional raw `value`.
There are no defaults, positional identity arguments, `*args`, or `**kwargs`.
H_GC freezes a complete whole-`FunctionDef` structural validator for these
future functions.  When G4 source appears, that validator requires the exact
FQN/name, signature, literal 29-field construction, variant constants,
nullability validation, expected-identity dataflow, whole comparison, return
shape, and resolved symbol provenance specified here.  H_GC does not pretend
to precompute a digest of G4 source that does not yet exist.

The prerequisite builder has exact keywords:

```text
expected_family_id
expected_family_input_sha256
reason_code
work_count
```

It emits the exact parent-ordered 29-field family-row dict literal, derives
`object_sha256` over the other fields, and fixes:

```text
last_verified_stage = NONE
hard_status = PREREQUISITE_BLOCKED
nominal_status = NOT_EVALUATED
hard_disposition = U24_HARD_PORTABILITY_PREREQUISITE_BLOCKED
nominal_disposition = U24_NOMINAL_NOT_EVALUATED
```

Only `CAP_VIOLATION`, `CARRIER_INCOMPLETE`, `COVERAGE_INCOMPLETE`, and
`MATRIX_PREREQUISITE_INCOMPLETE` are legal reason codes.  Every downstream
digest, bound, and threshold field is literal null.  The prerequisite verifier
has positional `value` plus the same four exact keywords, calls the builder
with those retained expected inputs, performs one complete canonical
inequality-or-raise, and returns the fresh expected dict.

The execution-failed builder has exact keywords:

```text
expected_family_id
expected_family_input_sha256
source_partition_sha256
target_partition_sha256
coordinate_identification_sha256
coordinate_split_sha256
signed_quotient_sha256
positive_envelope_sha256
restriction_sha256
safety_sha256
return_memory_sha256
maxent_problem_sha256
maxent_result_sha256
ordered_level_sha256
ordered_morphism_sha256
ordered_positive_transport_sha256
ordered_predictive_transport_sha256
ordered_hard_factor_sha256
work_count
last_verified_stage
reason_code
```

Each digest keyword is exact `str`/uppercase SHA-256 or literal `None`.
The exact non-null prefix by `last_verified_stage` is:

```text
NONE or PREFLIGHT: no downstream digest
PARTITION: source_partition, target_partition
COORDINATE_IDENTIFICATION:
  + coordinate_identification, coordinate_split
ENVELOPE:
  + signed_quotient, positive_envelope
RESTRICTION: + restriction
SAFETY: + safety
RETURN_MEMORY: + return_memory
MAXENT: + maxent_problem, maxent_result
SIMILARITY:
  + ordered_level, ordered_morphism,
    ordered_positive_transport, ordered_predictive_transport
COMPOSITION: + ordered_hard_factor
```

All later digest fields and both `exact_hard_bound` and `hard_threshold` are
literal null.  The builder fixes `hard_status = EXECUTION_FAILED`,
`nominal_status = NOT_EVALUATED`,
`hard_disposition = U24_HARD_PORTABILITY_EXECUTION_FAILED`, and
`nominal_disposition = U24_NOMINAL_NOT_EVALUATED`.  Its reason code is exactly
one of `MALFORMED_WIRE`, `DIGEST_MISMATCH`, `AUTHORITY_SPLICE`,
`EXPECTED_VALUE_MISMATCH`, `TIER_SUBSTITUTION`, or `INTERNAL_EXCEPTION`.
The execution verifier has positional `value` plus the identical exact keyword
list, reconstructs through the builder, performs one complete canonical
inequality-or-raise, and returns the fresh expected dict.

Both variants select their function only from independently derived
prerequisite/execution state.  Neither expected identity input nor any raw
field selects a variant.  In every function, the expected identity pair has
the same raw-independence rule as Spec parsing.  Complete field set, parent
nullability, enums, work cap, canonical bytes, and whole digest are validated.

Standalone Spec-label versus Result-label string comparison is not a
verification substitute.  A cross-Spec result splice is rejected through the
complete expected Result whole-wire comparison.

## 6. Forbidden uses

Every use below remains forbidden:

- branch, match, conditional expression, boolean control, exception
  selection, lookup, dispatch, sort, index, iteration bound, or call-target
  selection from `family_id`;
- arithmetic, dimension, cap, work count, threshold, status, disposition,
  hard factor, MaxEnt quantity, similarity quantity, or transport quantity
  derived from the label, its length, bytes, or digest;
- comparison tables between a family label and a family-input digest;
- `.lower()`, concatenation, formatting, slicing, parsing, canonicalization,
  hashing for control, or translation to another label;
- embedding a family label in an error message;
- using raw Spec or Result `family_id` as the expected reconstruction
  authority;
- using raw `family_input_sha256` as its expected reconstruction authority;
- generic tuple/list/dict/container transport, append-and-read, alias chains,
  or a generic identity helper;
- comparing family IDs to choose a family implementation;
- changing any mathematical result when two otherwise identical typed series
  differ only in family identity.

The label may occur in the complete registered Spec and Result wires, their
whole canonical bytes/digests, the direct same-name constructor transport, and
the final emitted identity field only.

## 7. H_GC implementation obligations

H_GC still changes exactly:

```text
tests/uprime_u24_guard.py
tests/test_uprime_u24_upper_stack_portability_identity.py
tools/run_uprime_u2_u4_development_tests.ps1
```

It must additionally:

1. pin A_FI commit, tree, ref, document blob, raw UTF-8 bytes, and uppercase
   raw SHA-256;
2. require H_GC to be a direct child of A_FI and preserve the complete
   `H -> A_GC -> A_FI -> H_GC` ancestry;
3. add `family_id` immediately after `schema_version` in the exact
   `FiniteUpperStackSpec` wire registry;
4. leave the Spec math, structural-join, and retained-authority registries
   unchanged so `family_id` and `family_input_sha256` remain opaque;
5. license only the direct same-name complete Spec-to-Result constructor
   transport and the direct external-expected-identity-to-non-complete-row
   transport after their exact typed/variant integrity sequences;
6. reject every forbidden use in section 6;
7. preserve exactly four zero-argument undecorated identity tests, the
   three-path H_GC allowlist, and the natural H_GC shape
   `2642 passed, 8 skipped, 161 deselected`;
8. reclose the existing acyclic guard-core/runner mutual hash after all
   source and test bytes are final.

The existing H_GC field-sensitive, projection, parser, whole-origin, and
negative-fixture requirements remain binding.

## 8. Mandatory identity-test mutations

The existing fourth identity test must contain positive and negative
fragments that establish:

- direct same-name matrix-label -> Spec -> Result transport is accepted;
- missing, extra, non-string, empty, invalid-UTF-8, or over-128-byte Spec
  `family_id` wire state is rejected;
- moving `family_id` in the frozen Spec wire-schema registry is rejected
  statically; raw JSON object insertion order is not treated as meaningful,
  and no complete dataclass declaration order is claimed here;
- a raw Spec label changed with a recomputed object digest is rejected
  against the separately retained expected identity;
- a raw Spec `family_input_sha256` changed with a recomputed object digest is
  rejected against `expected_family_input_sha256`;
- a raw Result built from Spec A whose label is rebound, including recomputed
  digests, is rejected while Spec A remains the separately supplied expected
  authority; a cross-Spec A/B splice that changes nonidentity authorities is
  likewise rejected;
- two series differing only in label have identical mathematical hard-factor
  projections/values, hard bound, work count, status, and dispositions;
  identity/provenance fields and whole-wire digests are allowed to differ;
- a non-complete row obtains its label and family-input digest only from the
  exact external expected identity pair, while its variant/nullability is
  identity-invariant;
- label branch, lookup, sort, index, length/hash control, formatting,
  transformation, error-message interpolation, or generic-container/helper
  transport is rejected;
- a Result parser that takes its expected label from the raw Result is
  rejected.
- any Spec, Result, prerequisite-row, or execution-row parser/verifier that
  derives either `expected_family_id` or `expected_family_input_sha256` from
  its raw mapping is rejected.

Stale-digest rejection alone cannot stand in for any named mutation.

## 9. Closeout and exact key count

The A_GC-a2 closeout key set remains and gains exactly:

```text
A_FI_COMMIT
A_FI_TREE
A_FI_REF
A_FI_DOCUMENT_BLOB
A_FI_DOCUMENT_RAW_UTF8_SHA256
```

The H/H_GC/G1/G2/G3/G4 stage-prefix Cartesian product remains 66 keys.
A_GC-a2 froze 51 non-stage keys after its seven A_GC/rejected-primary keys;
A_FI adds five more.  The resulting closed total is:

```text
56 non-stage keys + 66 stage keys = 122 keys
```

Every A_FI key occurs exactly once.  `A_FI_COMMIT` is this authority commit,
not H_GC.  The result's `source_commit` and `source_tree` remain the selected
G4 semantic commit/tree.

## 10. Resource, evidence, and nonclaims

A_FI performs no scientific execution, protected read, GPU/SSH/LLM action,
external capture, runner calibration, or resource observation.  It changes no
endpoint denominator, expected matrix, probability, bound, threshold,
disposition, evidence tier, test count, or resource wall.

The correction proves only that a frozen input identity has closed,
non-dispatching routes into complete and non-complete output identity fields.
It may change identity/provenance fields and their whole-wire digests, but
cannot change a mathematical hard-factor projection, bound, work count,
status, disposition, or nominal mathematical diagnostic.  It does not
establish general finite-carrier portability, solve-rate improvement,
infinite-horizon stability, learned locality, or protected-data
generalization.

## 11. Attempts and stopping rule

This authority is frozen only after pre-push document review.  Once its custom
ref is published it is immutable.  There is no A_FI repair series.  If a later
defect is merely code, serialization, guard, CI, or platform engineering, it
is repaired within the still-bounded H_GC/G-series attempts.  If this document
contains another authority contradiction and a rational repair exists before
source publication, use another clearly named fresh pre-source authority.
User direction is required only if the project-wide theory is refuted or no
rational repair remains.

## 12. Pre-freeze verdict

Verdict: **READY TO FREEZE AS A NARROW PRE-SOURCE IDENTITY CORRECTION**.

The amendment repairs one missing complete-row opaque edge and its partial-row
counterpart:

```text
Spec.family_id -> Result.family_id
external expected family_id -> non-complete family-row family_id
```

It adds no mathematical freedom.
