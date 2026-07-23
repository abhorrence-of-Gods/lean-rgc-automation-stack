# U'2–U'4 upper-stack portability: canonical-wire integrity guard correction

**Frozen:** 2026-07-23 (JST)
**Disposition:** replacement pre-source authority A_GC-a2; documentation stage only
**Authority parent:** `39250539b252bdb55dc807d2678b91a11fb379f4`
**Authority-parent tree:** `0fb8fce29d619ab26dfc4a480ec16e7d89bfb78f`

## 1. Scope and reason

This is the sole licensed replacement of primary A_GC
`557fb03a92c37487110bab99caf98fd10436d9d1`.  That primary authority was
rejected before any H_GC source commit, push, CI, or protected endpoint read.
Two pre-source control contracts were incomplete: it omitted the runner whose
frozen hash is mutually bound to the guard, and it preserved identity taint
through verified typed objects without a closed way to erase labels while
retaining their structural and exact-numeric content.  No scientific result
informed either finding.

The accepted H handoff at
`39250539b252bdb55dc807d2678b91a11fb379f4` correctly rejects semantic
dispatch on `family_id` and every value derived from it.  The same conservative
taint rule also rejects a narrower operation that the frozen G-series contract
requires: hashing a complete canonical wire and comparing the resulting
integrity value only to fail closed on corruption, and projecting a completely
verified carrier to label-erased structural/numeric coordinates.

This amendment licenses one structural guard correction.  It does **not**
declassify a family or candidate label, trust a spelling such as `digest` or
`sha256`, or permit a label spelling or digest to select mathematics.  Taint
remains attached to labels, identity fields, payloads, canonical bytes, and
hashes from construction through every caller and return.  Only the closed
typed erasures in §3 may produce generic structural/numeric values.

The correction is control-plane engineering.  It reads no protected endpoint,
no prior L0 scientific input, no result artifact, and no external resource.
It changes neither the H scientific state nor the registered G-series
endpoints.

The accepted H evidence is pinned as follows:

| ref role | run | job | natural result |
|---|---:|---:|---|
| candidate | `29906113227` | `88877856694` | `2642 passed, 8 skipped, 161 deselected` |
| accepted | `29978820461` | `89116218789` | `2642 passed, 8 skipped, 161 deselected` |

The original 2026-07-18 authority and matrix bytes, their semantics, all
scientific endpoints, and every resource cap remain immutable.

This amendment has narrow precedence over the 2026-07-18 authority only for:
inserting the control/topology A_GC and H_GC stages immediately after accepted H;
selecting the A_GC `-a2` authority ref and the two H_GC attempt refs; freezing
the H_GC three-path diff and runner binding; replacing the affected
stage-prefix and closeout-key counts; and making this one pre-source
control-plane correction an explicit exception to the parent document's
one-bundle/no-component-amendment sentence.  Every scientific definition,
matrix byte, endpoint, test-growth count, protected-read rule, resource rule,
G1--G4 allowlist, result rule, and nonclaim in the parent remains controlling.
This precedence does not license another ledger, runner, capture, recovery, or
calibration subproject.

For avoidance of a recurrent provenance error, the following dated fact is
repeated on 2026-07-23.  The 2026-07-12 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red CI run `29166670576`
(job `86580832840`) because the identity guard omitted shallow-history
handling; the dated audit classified that as a control-plane design defect.
The scientific candidate commit
`3bb3408afc50a08307cff2c9b1906a299739dfb5` has green CI run `29166073728`
(job `86579287017`).  The red result-commit badge is not a failed scientific
endpoint.  This paragraph is provenance only and neither reopens that result
nor authorizes a rerun.

## 2. Fresh topology

The correction has two commits before G1:

1. **A_GC (this selected `-a2` replacement authority).** A
   documentation-only direct child of
   `39250539b252bdb55dc807d2678b91a11fb379f4`.  Its exact allowlist is this
   document alone.  It is anchored at
   `refs/codex-authority/uprime-upper-portability-guard-correction-20260723-a2`.
   The primary ref without `-a2` remains an auditable rejected authority and
   has no stage status.  The selected A_GC commit does not run GitHub Actions.
2. **H_GC (guard correction).** A direct child of the selected A_GC commit.
   Its primary branch is
   `codex/uprime-upper-portability-guard-correction`; at most one replacement
   attempt may use suffix `-a2`.  Its exact allowlist is:

   - `tests/uprime_u24_guard.py`
   - `tests/test_uprime_u24_upper_stack_portability_identity.py`
   - `tools/run_uprime_u2_u4_development_tests.ps1`

H_GC adds no test function and no tier-manifest row.  After a natural green
candidate run, `codex/uprime-upper-portability-plan` may fast-forward to the
byte-identical selected H_GC commit and must receive a distinct natural green
accepted-ref run.  G1 (primary or `-a2`) must then be a direct child of that
accepted H_GC commit.  The old H commit remains immutable.

The identity first-parent order is exactly:

`H -> A_GC -> H_GC -> G1 -> G2 -> G3 -> G4 -> A_RES -> R`.

`A_GC` is the canonical topology/allowlist stage key.  Its selected attempt is this `-a2`
authority commit/ref; the suffix is attempt provenance and is not a new stage
key.

`STAGE_ALLOWLISTS[A_GC]` is the singleton containing this document and
`STAGE_ALLOWLISTS[H_GC]` is the three guard/test/runner paths above.  Both stages have an
empty tier-manifest delta.  H_GC attempt refs are exactly
`codex/uprime-upper-portability-guard-correction` and
`codex/uprime-upper-portability-guard-correction-a2`.

Both H_GC runs retain the exact H natural test shape:

| stage | required natural CI shape |
|---|---|
| H_GC candidate | `2642 passed, 8 skipped, 161 deselected` |
| H_GC accepted ref | `2642 passed, 8 skipped, 161 deselected` |

Any different count, skipped count, deselected count, changed path, parent, or
tree relation is fail closed.

The guard and the development runner form a mutually pinned pair.  H_GC must
replace exactly one assignment of `FROZEN_RUNNER_SHA256` in the guard and
exactly one assignment of `$ExpectedGuardCoreSha256` in the runner.  The guard
core SHA-256 is computed from the exact guard bytes after normalizing that
unique runner binding to 64 ASCII zeroes.  The runner binding is then set to
that uppercase digest.  The runner SHA-256 is computed from its complete bytes
after CRLF-to-LF normalization, with bare carriage returns forbidden, and the
guard binding is then set to that uppercase digest.  Recomputing both
directions must reach the same two values.  No path other than the three-path
H_GC allowlist may break this finite update sequence, and no source name,
comment, copied hash, second assignment, or unnormalized byte stream may act
as a substitute.

Apart from the unique `$ExpectedGuardCoreSha256` literal, the H_GC runner must
be byte-identical to the runner at accepted H.  The three-path allowlist does
not license a self-consistent runner rewrite, command change, test selection
change, environment change, timeout change, denylist change, or normalization
change.

Final closeout provenance adds these exact single-occurrence base keys:

```text
A_GC_COMMIT
A_GC_TREE
A_GC_REF
A_GC_DOCUMENT_BLOB
A_GC_DOCUMENT_RAW_UTF8_SHA256
REJECTED_PRIMARY_A_GC_COMMIT
REJECTED_PRIMARY_A_GC_REF
```

The first five identify the selected `-a2` A_GC attempt.  The last two identify
primary commit `557fb03a92c37487110bab99caf98fd10436d9d1` and
`refs/codex-authority/uprime-upper-portability-guard-correction-20260723` as a
non-stage pre-source authority attempt; they do not enter the stage product.
The prefix list is exactly `H,H_GC,G1,G2,G3,G4`, yielding 66 stage keys.  With
the parent's 44 base keys and the seven keys above, the closed closeout set has
exactly 117 keys.  A_RES and R may not omit, add to, or reconstruct this
inserted history.

## 3. Licensed structural recognition

The guard may recognize an integrity operation only from its complete AST
shape.  Names of variables, fields, helper functions, classes, or digests have
no authority.

### 3.1 Complete canonical wire

A canonical-wire expression is exactly
`lean_rgc.odlrq.contracts.canonical_contract_bytes(X)` with one positional
argument and no keywords.  The guard treats this as a taint-preserving byte
transport, never as evidence that `X` is semantically complete.

The registered G1--G4 whole-class tuple is exactly:

```text
lean_rgc.odlrq.finite_e2.FiniteCoordinateIdentification
lean_rgc.odlrq.finite_e2.FiniteCoordinateSplit
lean_rgc.odlrq.finite_e2.FiniteEnvelopeRestriction
lean_rgc.odlrq.finite_e2.FiniteLiftingUniformSafety
lean_rgc.odlrq.finite_e2.FiniteReturnMemoryBound
lean_rgc.odlrq.finite_maxent.FiniteSupportReference
lean_rgc.odlrq.finite_maxent.FiniteMaxEntProblem
lean_rgc.odlrq.finite_maxent.FiniteMaxEntResult
lean_rgc.odlrq.finite_similarity.FiniteApproximationLevel
lean_rgc.odlrq.finite_similarity.FiniteGlobalMeasure
lean_rgc.odlrq.finite_similarity.FinitePositiveDistance
lean_rgc.odlrq.finite_similarity.FinitePredictiveDistance
lean_rgc.odlrq.finite_similarity.FinitePositiveMorphism
lean_rgc.odlrq.finite_similarity.FinitePositiveTransportCertificate
lean_rgc.odlrq.finite_similarity.FinitePredictiveTransportDiagnostic
lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec
lean_rgc.odlrq.finite_upper_stack.FiniteHardFactor
lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult
```

The registered retained-substrate whole-type tuple is exactly:

```text
lean_rgc.odlrq.behavioral_partition.VerifiedExactPartition
lean_rgc.odlrq.quotient_generator.ExactQuotientCoordinateGenerator
lean_rgc.odlrq.quotient_generator.PositiveFiberWeights
lean_rgc.odlrq.quotient_generator.ExactFiniteFiberLaw
lean_rgc.odlrq.envelope.DeclaredSyntheticTransferLayer
lean_rgc.odlrq.envelope.FiberCompletenessWitness
lean_rgc.odlrq.envelope.FiberEnvelope
```

There is no module-prefix, suffix, subclass, schema-name, or future-class
wildcard in either tuple.  The exact producer and constructor calls in §3.3 are
taint-preserving transports; `SyntheticAction`, `SyntheticTotalizedState`,
`SyntheticTransitionRow`, snapshots, admission reports/certificates, and
partition certificates are not additional whole integrity origins merely
because they lie on that chain.

The only unparsed literal whole origin is one literal dict with no `**`,
comprehension, or computed key and exactly the fields
`schema_version,matrix_id,family_id,side`.  Its `schema_version` value is the
literal `odlrq.finite-portability-environment.v1`; `side` is an already-generic
exact value in `source|target`; and `matrix_id` and `family_id` remain tainted
identity values.

The carrier field-set tests remain exact: omitting or adding a field cannot pass
the registered carrier contract.  Completeness is proved by those frozen
field-set and roundtrip tests, not by a trusted AST name.

G2 candidate labels are legal only as fields of the complete
support-reference, problem, and result wires whose exact ordered fields are
already frozen by the 2026-07-18 authority.  A candidate-label-only wire or
hash may be constructed, but it is not an integrity, equality, control, or
verification operand.  The carrier mapping above is the sole unparsed
four-field carrier-literal exception; the strict parser rule in §3.7 is
separate and narrower.  The full typed contracts still provide the carrier
chain, but transport membership is not integrity-origin membership.

### 3.2 Canonical-wire SHA-256

A canonical-wire hash is exactly:

`hashlib.sha256(canonical_contract_bytes(X)).hexdigest().upper()`

for any `X`.  Each call has the exact arity shown and no keywords.  A local helper is
recognized only when it has one parameter and its body is exactly one return of
that chain.  Salt, prefix/suffix bytes, `repr`, `str`, alternate encodings,
algorithm dispatch, an extra statement, or a trusted helper name is rejected.

Canonical bytes and their hash **remain tainted**.  Recognition is not
declassification.  The guard is a capability/dispatch firewall; complete-wire
field sets are enforced by the frozen schema tests.

### 3.3 Exact typed identity/data sinks

When, and only when, a tainted carrier is passed through the following exact
call shapes, the call is an identity/data operation.  Identity-bearing returns
and fields remain tainted; independently constructed exact numeric fields are
tracked separately under §3.6.  No unlisted position, extra keyword,
positional/keyword substitution, splat, or unknown callee is admitted.

| fully-qualified callee | exact call shape | tainted positions admitted |
|---|---|---|
| `lean_rgc.odlrq.contracts.CanonicalPayload.from_value` | one positional, no keyword | positional 0 |
| `lean_rgc.odlrq.contracts.SyntheticAction` | exact keywords `action_id,payload` | both |
| `lean_rgc.odlrq.contracts.SyntheticTotalizedState` | exact keywords `state_id,payload,totalized_kind,response_coordinates,frame_digest` | `state_id,payload,frame_digest` |
| `lean_rgc.odlrq.contracts.SyntheticTransitionRow` | exact keywords `source_state_id,action_id,target_state_id,transition_semantics_digest` | all four |
| `lean_rgc.odlrq.adapters.make_synthetic_observation_frame_id` | exact keywords `environment_digest,response_vocabulary_id` | `environment_digest` |
| `lean_rgc.odlrq.adapters.make_synthetic_transition_semantics_id` | exact keywords `actions,response_vocabulary_id` | `actions` |
| `lean_rgc.odlrq.adapters.observation_frame_digest` | one positional, no keyword | positional 0 |
| `lean_rgc.odlrq.adapters.build_synthetic_finite_snapshot` | exact keywords `environment_digest,coordinate_names,seed_state_ids,states,actions,transitions` | all except `coordinate_names` |
| `lean_rgc.odlrq.adapters.admit_synthetic_finite_snapshot` | one positional, no keyword | positional 0 |
| `lean_rgc.odlrq.behavioral_partition.refine_exact_partition` | one positional, no keyword | positional 0 |
| `lean_rgc.odlrq.behavioral_partition.verify_exact_partition` | two positional, no keyword | both |
| `lean_rgc.odlrq.quotient_generator.build_exact_quotient_coordinate_generator` | one positional, no keyword | positional 0 |
| `lean_rgc.odlrq.quotient_generator.make_positive_fiber_weights` | exactly two positional, no keyword | generator argument 0 only; numeric weights remain generic |
| `lean_rgc.odlrq.quotient_generator.make_exact_finite_fiber_law` | exactly two positional, no keyword | generator argument 0 only; numeric probabilities remain generic |
| `lean_rgc.odlrq.envelope.declare_synthetic_transfer_layer` | exactly three positional, no keyword | source/target generators 0/1 and label-bearing coefficient-locator rows 2 |
| `lean_rgc.odlrq.envelope.certify_fiber_completeness` | exactly two positional, no keyword | layer argument 0 only; role is an untainted literal |
| `lean_rgc.odlrq.envelope.build_fiber_envelope` | exactly six positional, no keyword | all six typed carrier authorities |
| `lean_rgc.odlrq.envelope.verify_fiber_envelope` | exactly one positional, no keyword | positional 0 |

There is no generic `tuple(X)` transport exception.  Fixed literal containers
and fresh numeric lists may be passed directly where the sink table permits.
An `append(X)` call is allowed only on a structurally fresh, function-local
literal container that remains tainted, has no alias, return, subscript,
iteration, sort, comparison, or other read, and is consumed exactly once and
directly by the named registered sink.  This licenses construction transport,
not label extraction.  A registered whole type may be checked only by the
exact dominating straight-line form
`if type(value) is not RegisteredType: raise
StrictContractError(<untainted literal>)`; `isinstance`, `is`, `else`, caught
errors, nonliteral messages, and unregistered types are not substitutes.  An
exact zero-argument `value.to_dict()` is admitted only after that same-function
guard (or on `self` of a registered frozen aggregate), and the exact
`json.loads(canonical_contract_bytes(X).decode("utf-8"))` roundtrip is a
taint-preserving transport.  `.lower()`, `min`, `sorted`, tainted iteration or
indexing, arithmetic, lookup, label comparison, and every semantic branch
remain forbidden.

### 3.4 Equality-or-raise

The only new family-tainted comparison is a direct, single
`left != right` test where both operands are canonical wires or
canonical-wire hashes of registered complete origins (or single-assignment
local names bound to those exact expressions), and:

- both operands have the same representation (wire/wire or hash/hash), the
  same exact registered type and schema, and independent provenance roles:
  one supplied or retained authority and one freshly reverified, rebuilt, or
  reconstructed expected authority;
- the comparison is the whole `if` test;
- the body is exactly one unconditional
  `lean_rgc.odlrq.contracts.StrictContractError(<untainted string literal>)`
  raise;
- there is no `else`, no exception handler that can swallow the raise, and no
  chained, boolean, negated, membership, order, or equality form.

Operand order may be reversed.  The result may not be returned, stored,
asserted, used for lookup, loop control, call-target selection, argument
selection, or any other semantic branch.  `==` is not licensed.
Self-comparison, alias comparison, two names bound to the same origin,
cross-type/cross-schema comparison, and supplied-versus-supplied or
expected-versus-expected comparison are vacuous and rejected.  Raw mappings
are not admitted here; they use only the stricter bytes-to-bytes rule in §3.7.

### 3.5 Closed label-erasing projections

There are exactly two structural erasures.  A helper name, a field spelling,
or a successful hash comparison does not qualify an erasure; the guard
recognizes the complete typed and control-flow shape below.

**Verified-partition projection.**  Its input has exact type
`lean_rgc.odlrq.behavioral_partition.VerifiedExactPartition` and is freshly
reverified from its retained admitted snapshot and certificate before any
projection.  The projection performs one complete join:

- every snapshot state has a unique `state_id`;
- every final block is nonempty, block indices are unique and exactly
  `0..number_of_blocks-1`, and every member ID occurs exactly once;
- the union of block members is exactly the snapshot state-ID set;
- every member in a block has one uniform pair
  `(totalized_kind, response_coordinates)`; and
- the action count and all structural counts are derived from the complete
  verified carrier, never copied from a label-bearing caller mapping.

The only private internal join row is
`(construction_block_index, member_count, totalized_kind,
response_coordinates)`, with exactly one row for every verified block.
Collection order has no authority.  The construction block index is an opaque
construction-local join key, not a number available to arithmetic, branching,
sorting, or a public wire.  All OPEN response-signature wires must be unique.
Their coordinate ordinals are derived solely by sorting
`canonical_contract_bytes` of the exact
`schema_version,totalized_kind,response_coordinates` response-signature wire.
Coordinate mathematics and the public relabel-invariant projection use only
those ordinals.  The projection may additionally return the derived action
count, block count, open-state count, and full-state count.

Member IDs are admitted only inside one bounded function-local bijective join.
An ephemeral unique state-ID map is built from the complete verified snapshot;
each block member ID performs exactly one equality lookup to select its state
record; and those maps and IDs do not escape the function.  The join may
establish only coverage, uniqueness, membership count, and a uniform response
signature.  An ID may not determine output order, a numeric value, a
construction/coordinate index, or a semantic branch other than immediate fail-closed
join validation.  No ID, map, payload, canonical wire, or digest may escape,
be explicitly hashed, parsed, minimized, sorted, or compared outside that
exhaustive join.  In particular G1 coordinate order is canonical
response-signature order, not canonical bytes of `member_state_ids` and not
the opaque construction-local block index.

**Verified-envelope projection.**  Its input has exact type
`lean_rgc.odlrq.envelope.FiberEnvelope` and passes a fresh
`verify_fiber_envelope` call before projection.  The live source and target
partitions, generators, weights, law, transfer layer, and both completeness
witnesses are rebound and compared as complete typed authorities.  Every open
target/source block pair occurs exactly once; the rectangle is exhaustive and
has no duplicate or omitted cell.  Construction indices may occur only in the
private join described above.  Each emitted output cell contains only:

```text
target_coordinate_ordinal
source_coordinate_ordinal
member_count
work_count
candidate_loads (exact numeric load values only)
majorant
compressed_coefficient
```

Source, target, candidate, and maximizer member IDs, payloads, hashes, and
canonical bytes are forbidden outputs.  A G1 restriction retains only these
label-erased cells, not the original label-bearing cell wires.  Consequently
baseline and relabelled full snapshot/partition/envelope wires may differ
while the final response-signature-ordered coordinate-majorant projection
remains identical.  Internal partition join rows need not be byte-identical
because their block indices are construction-local.  Candidate load values
are normalized to exact numerator/denominator pairs, treated as a multiset,
and emitted with multiplicity in canonical nondecreasing rational order; their
label-dependent source enumeration is never preserved.  Envelope cells use
their opaque source/target construction indices only to join the private
partition rows, then emit at the corresponding
`(target_coordinate_ordinal, source_coordinate_ordinal)` and erase both
construction indices.
The erasure does not assert a result outside the complete verified finite
carrier.

Missing or extra states, duplicated membership, an empty or nonuniform block,
a noncontiguous block index, missing or duplicated envelope cells, omitted
candidate loads, an injected number, an incomplete rectangle, or an authority
splice makes the relevant projection fail closed.

### 3.6 Registered mixed-aggregate field summaries

Whole-object taint is not used to contaminate an independent exact numeric
field merely because both fields share one frozen object.  Instead the guard
contains a closed, source-level three-way registry for exactly the fully
qualified classes in §3.1: mathematical data, structural-join-only data, and
identity/opaque data.  The following literal tuples are frozen; `()` means an
empty tuple.  Short class names resolve only to their unique §3.1 fully
qualified names.

| registered class | mathematical-data fields | structural-join-only fields |
|---|---|---|
| `FiniteCoordinateIdentification` | `(basis_convention, full_source_block_count, full_target_block_count, open_rectangle_complete, _ordered_response_signature_bytes)` | `(coordinate_ids, source_block_indices, target_block_indices, source_construction_to_target_construction_indices)` |
| `FiniteCoordinateSplit` | `(split_complete,)` | `(p_coordinate_ids, q_coordinate_ids)` |
| `FiniteEnvelopeRestriction` | `(basis_convention, matrix, _positive_matrix, _signed_matrix, _selected_cell_bytes, open_cell_count, open_rectangle_complete, verification_disposition)` | `(coordinate_ids,)` |
| `FiniteLiftingUniformSafety` | `(norm_id, weighted_l1_column_loads, weighted_l1_operator_norm, exact_cell_coverage, cancellation_free, lifting_uniform, verification_disposition)` | `()` |
| `FiniteReturnMemoryBound` | `(horizon, finite_only, m_pp, m_pq, m_qp, m_qq, qq_powers, return_terms, return_sum, memory_forcing_radius, return_sum_weighted_l1_norm, operation_count, work_units, verification_disposition)` | `(p_coordinate_ids, q_coordinate_ids)` |
| `FiniteSupportReference` | `(reference_masses, sufficient_statistics, exact_rule_columns, tier)` | `(coordinate_ids,)` |
| `FiniteMaxEntProblem` | `(normalized_reference_probabilities, sufficient_statistics, target, kl_radius, support_cap, statistic_dimension, tier)` | `()` |
| `FiniteMaxEntResult` | `(probabilities, exact_target, exact_ratio_witness, exact_moment_residual, exact_kl_certificate, geometry_status, operator_span_diagnostic, decimal_diagnostics, status, tier)` | `()` |
| `FiniteApproximationLevel` | `(radius, word_depth, granularity, dimension)` | `(coverage_ids,)` |
| `FiniteGlobalMeasure` | `(measure_kind, values, tier)` | `(coordinates,)` |
| `FinitePositiveDistance` | `(norm_id, left_vector, right_vector, difference_vector, distance, tier)` | `()` |
| `FinitePredictiveDistance` | `(norm_id, left_vector, right_vector, difference_vector, distance, tier)` | `()` |
| `FinitePositiveMorphism` | `(axis, basis_convention, matrix, nonnegative, column_sums)` | `(coverage_map,)` |
| `FinitePositiveTransportCertificate` | `(transported_left, transported_right, transport_remainder, true_target_residual, verification_disposition)` | `()` |
| `FinitePredictiveTransportDiagnostic` | `(transported_left, transported_right, diagnostic_remainder, tier)` | `()` |
| `FiniteUpperStackSpec` | `(direct_quotient_residual, memory_forcing_radius, hard_threshold)` | `()` |
| `FiniteHardFactor` | `(source_tier, norm_id, value)` | `()` |
| `FiniteUpperStackResult` | `(exact_hard_bound, hard_threshold, work_count, last_verified_stage, reason_code, hard_status, nominal_status, hard_disposition, nominal_disposition)` | `()` |

There is one fourth, non-declassifying category needed by the public
`build_finite_upper_stack(spec)`/`verify_finite_upper_stack(spec, result)`
boundary: retained typed-authority transport.  Its complete private-field
registry is:

| registered owner | exact private field and annotation |
|---|---|
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_coordinate_split: FiniteCoordinateSplit` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_restriction: FiniteEnvelopeRestriction` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_safety: FiniteLiftingUniformSafety` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_return_memory: FiniteReturnMemoryBound` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_maxent_problem: FiniteMaxEntProblem` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_ordered_levels: tuple[FiniteApproximationLevel, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_ordered_morphisms: tuple[FinitePositiveMorphism, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_ordered_positive_distances: tuple[FinitePositiveDistance, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackSpec` | `_ordered_predictive_distances: tuple[FinitePredictiveDistance, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_spec: FiniteUpperStackSpec` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_maxent_result: FiniteMaxEntResult` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_ordered_levels: tuple[FiniteApproximationLevel, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_ordered_morphisms: tuple[FinitePositiveMorphism, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_ordered_positive_transports: tuple[FinitePositiveTransportCertificate, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_ordered_predictive_transports: tuple[FinitePredictiveTransportDiagnostic, ...]` |
| `lean_rgc.odlrq.finite_upper_stack.FiniteUpperStackResult` | `_ordered_hard_factors: tuple[FiniteHardFactor, ...]` |

Each short annotation resolves to its exact §3.1 fully qualified class.  No
`Any`, union, protocol, base class, alias, generic iterable, or added private
field qualifies.  The only noncircular access sequence is:

1. exact outer-owner type guard;
2. extraction of each registered private field into a fresh verification-only
   local;
3. exact inner type guard and fresh reverify/rebuild of that local (for a
   tuple, first enforce its bound, exact tuple type, order, and every exact
   declared element type, then freshly reverify/rebuild every element);
4. reconstruction of the expected outer owner from the fresh inner values and
   one whole-canonical comparison; and
5. only after success, propagation of the existing three-way summaries of the
   **fresh inner values**, never the original extracted values.

Before step 5, an extracted local may appear only in the type,
reverification/rebuild, and outer-reconstruction operations above; none of its
semantic fields may be read.  The transport is not generic mathematical data:
it cannot expose or branch on an inner identity/opaque field, substitute a
digest, reorder a tuple, or pass through an unknown call.

Every actual dataclass field not listed in a mathematical/join tuple or the
retained typed-authority registry is identity/opaque,
including schema/family/candidate/level/factor/domain/codomain identifiers,
all digests, retained authorities, and canonical wire bytes.  The four private
G1 fields listed above are exceptions only when their actual value is the
label-erased projection produced under §3.5; otherwise they are opaque.
Opaque fields are unavailable to semantic/control computation irrespective of
an apparently generic constructor actual; they may be transported only inside
whole-object reverification/integrity operations.
`decimal_diagnostics` is mathematical only after exact finite-decimal type and
finiteness validation.  Every enum-like field in the table is mathematical
only after equality to its parent-authority closed literal set.  The
implementation uses this literal table and may not infer a category from a
field spelling, annotation, value shape, or newly added private cache.

Structural-join-only fields preserve their own taint and may be used only in a
bounded exhaustive equality join against the matching live typed authority.
They may establish uniqueness, coverage, and a coordinate ordinal already
fixed by response-signature bytes.  They may not participate in arithmetic,
ordering, sorting, a semantic branch, a public relabel projection, or an
unrelated lookup.  In particular source/target block indices and construction
bijections are never generic mathematical data.

An entry is active only when the fully qualified name resolves to the actual
`classes` entry, the class is a base-free `@dataclass(frozen=True)` with no
custom initializer or mutation hook, and the guard has recorded its exact
declared field order from the class AST.  Category membership applies only to
an actual declared field.  A listed name absent from a class is not
synthesized, and a wire-only value reconstructed by a method gains no field
summary; it remains subject to whole reverification or §3.7.
Same-name functions, aliases, subclasses, nonfrozen classes, dynamic
factories, and spelling-based inference receive no summary.

At a registered constructor the guard records taint separately for every
field from the corresponding actual argument.  A generic mathematical-data
actual remains generic; placing a tainted label in such a field taints that
field and does not launder it.  A tainted identity/opaque field remains
tainted.  The exact field map propagates through a local helper argument,
method receiver including `self`, direct name copy, registered constructor
return, and a return of the same registered object.  Reading a field observes
that field's taint only.

Interprocedural summaries are solved to a monotone fixed point over every
statically resolved local call site, unioning taint across all calls,
arguments, receivers, and returns.  Recursion, unresolved dispatch, or an
unstable summary fails closed.  Exact order-preserving typed containers of
registered elements recursively preserve each element summary; a generic,
mixed, dynamically indexed, or variadic container is whole-tainted.

A dynamic attribute or subscript, splat, unknown type/call, unregistered return
shape, mixed return, mutation, or passage of a partly tainted aggregate to an
unknown callee collapses to whole taint and fails closed at a protected sink.
Labels and digests may not determine a number, matrix entry, dimension,
iteration bound, lookup, sort, index, branch, or return value.  This is
field-sensitive provenance preservation, not declassification.

### 3.7 Raw complete mappings in strict parsers

A generic or partial mapping is never a registered whole origin.  A raw
mapping parameter of a registered G1--G4 `from_dict` parser may participate in
one raw-to-live integrity comparison only after exact straight-line,
dominating checks establish:

1. `type(value) is dict`;
2. equality of its field set to the exact frozen literal schema field set;
3. equality of its `schema_version` to the exact frozen literal; and
4. exact bounded type/strict-JSON validation of every field, while only fields
   listed as mathematical data or an exact §3.6 structural join may assist
   reconstruction; and
5. reconstruction and fresh reverification of an expected value of the exact
   registered type from retained authorities.

Each failed check has exactly one uncaught
`StrictContractError(<untainted literal>)`, with no `else`.  The sole licensed
raw comparison is the direct whole test:

```text
canonical_contract_bytes(raw) != canonical_contract_bytes(expected.to_dict())
```

The exact zero-argument `to_dict` is dominated by the registered
type/reverification checks, and the comparison has exactly that fail-closed
body.  The parser returns `expected`, never the raw mapping.  The raw mapping
and every identity/opaque member remain tainted and cannot assist
reconstruction merely because its type and JSON form were validated.
For G1 the only raw values eligible to assist reconstruction are canonical
`q{ordinal}` P/Q coordinate IDs, bounded horizon, and the exact
memory-forcing rational; family, candidate, state, member, action, payload,
wire, and digest values are never declassified.

The exact literal keyset, schema, and type-check sequence may be represented
directly in the parser; a static dict literal with that exact full keyset is
also a complete raw operand.  Computed/subset/superset keysets,
`isinstance`, caught or nonliteral errors, an `else`, a generic dict helper,
unknown fields, field-only digest comparisons, and partial or label-only wires
remain rejected.  This raw rule does not license lookup, dispatch, or returned
booleans from an identity field.

### 3.8 Reverification rather than digest authority

G1 must freshly reverify a retained `VerifiedExactPartition` and freshly
rebuild an `ExactQuotientCoordinateGenerator` from that verified partition.
It must not use their `from_dict` methods as a shortcut.  Restrictions compare
the supplied weights, law, completeness witnesses, generators, and envelope
to the corresponding complete live typed authorities; a tuple of digest-field
comparisons is not authority.  Redundant per-field `object_sha256` checks after
a whole canonical comparison are removed, and a retained/supplied split is
checked by one whole canonical comparison rather than an identity-or-digest
fallback.  Exact type guards for the six restriction authorities are written
separately; a loop over a generic tuple is not a registered type guard.

## 4. Mandatory positive and adversarial probes

The existing fourth identity test, and no new fifth test, must demonstrate:

- complete carrier and candidate wires may undergo canonical-bytes and exact
  SHA-256 inequality checks whose only consequence is an uncaught strict
  contract error;
- reversed operands and an exact one-return hash helper are accepted only for
  independent supplied/retained and freshly rebuilt/reverified origins of the
  same registered type/schema and representation; self, alias,
  cross-type/schema, and same-role comparisons are rejected;
- the exact preceding registered-type guard, registered `.to_dict()`, and
  canonical JSON roundtrip are accepted and remain tainted;
- exact SHA construction of a label-only or partial-field wire is accepted,
  while using it as an equality/control/verification operand is rejected;
- direct family/candidate label comparison, digest
  truthiness/lookup/dispatch, equality, an `else`, a returned boolean, a caught
  raise, salted or noncanonical hashing, and a tainted error message are
  rejected;
- cross-call and return propagation remains tainted, so a recognized hash
  cannot later control a branch;
- propagation follows only the exact formal/actual pair and does not taint a
  numeric sibling argument merely because both occur in one call;
- a helper called once with safe numeric data and once with a family-tainted
  actual receives the unioned fixed-point summary and cannot launder the
  second call;
- a complete family-tainted exact carrier passes partition projection,
  signature bijection, envelope projection, lifting-uniform safety, and
  return-memory construction without exposing a label;
- relabelled full carrier wires differ while the final
  response-signature-ordered coordinate-majorant projection is
  byte-identical; construction-local partition join rows are not claimed as a
  public invariant;
- a registered mixed object with tainted candidate/family identifiers and
  digests may cross at least two helpers and a method receiver while an
  independently generic exact matrix/probability/bound/work field remains
  generic, including one nested G4 aggregate whose exact retained authorities
  are freshly reverified before their existing summaries propagate;
- an added/unlisted private field, `Any`/union/base annotation, mixed or
  reordered authority tuple, unreverified nested authority, inner
  identity-field branch, and unknown authority transport are rejected;
- returning or branching on an identity field; converting its length/hash,
  sort, lookup, or index to numeric control; copying a label into a nominal
  numeric field; a mixed label-or-matrix return; dynamic `getattr`; an unknown
  factory/callee; and a fake same-name function/nonfrozen class are rejected;
- the partition erasure rejects every incomplete join and any attempt to
  return, sort, minimize, parse, branch on, or index by a member ID, payload,
  or hash outside the single exhaustive bijective join in §3.5;
- the envelope erasure rejects every incomplete rectangle, omitted candidate
  load, injected numeric value, or attempted candidate/member/maximizer
  ID/hash escape;
- a raw mapping passes only the exact type, literal field-set, schema,
  reconstruction, and whole comparison sequence; omitted/extra/computed
  fields, partial or digest-only comparisons, returning the raw wire, reading
  a family/candidate field, caught errors, and `else` branches are rejected;
- in the exact evaluator loop, the ordered family label and literal
  `row["family_id"]` are tainted while the row's numeric fields remain generic;
- unknown calls, generic `tuple(X)`, generic label containers, `.lower()`, and
  every arity, keyword, or tainted-position near miss of a registered sink are
  rejected.

The same existing tests must recompute the guard core and normalized runner
digests in both directions, prove each binding assignment is unique, and
reject a stale, duplicated, lowercase, or differently normalized binding.

The uncommitted G1 draft examined while diagnosing this guard mismatch is
pre-source engineering information only.  No G1 commit, push, CI run, protected
endpoint, or scientific result was consumed; the draft confers no attempt or
result status.

## 5. Stopping rule

H_GC stops at the first candidate whose exact three-path diff passes the four
identity tests, relevant guard tests, and the exact natural CI shape.  One
`-a2` source attempt is the maximum and may repair an implementation defect
only.  It may not widen the authority, matrix, complete-wire registry, sink
map, or semantic endpoint.  Failure after that attempt closes this authority;
it does not license source changes under this authority, endpoint reads,
GPU/SSH/LLM work, or a broader declassification rule.  Exhaustion closes only
this authority: if a rational repair remains, a concise remedy note is sent to
Fable and a genuinely fresh pre-source authority is required.  User direction
is requested only if the project-wide theory is refuted or no rational remedy
exists.
