# U'2–U'4 upper-stack portability: canonical-wire integrity guard correction

**Frozen:** 2026-07-23 (JST)  
**Disposition:** fresh pre-source authority; documentation stage only  
**Authority parent:** `39250539b252bdb55dc807d2678b91a11fb379f4`
**Authority-parent tree:** `0fb8fce29d619ab26dfc4a480ec16e7d89bfb78f`

## 1. Scope and reason

The accepted H handoff at
`39250539b252bdb55dc807d2678b91a11fb379f4` correctly rejects semantic
dispatch on `family_id` and every value derived from it.  The same conservative
taint rule also rejects a narrower operation that the frozen G-series contract
requires: hashing a complete canonical wire and comparing the resulting
integrity value only to fail closed on corruption.

This amendment licenses one structural guard correction.  It does **not**
declassify a family or candidate label, trust a spelling such as `digest` or
`sha256`, or permit a label-derived value to select mathematics.  Taint remains
attached to canonical bytes and hashes from construction through every caller
and return.

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

## 2. Fresh topology

The correction has two commits before G1:

1. **A_GC (this authority).** A documentation-only direct child of
   `39250539b252bdb55dc807d2678b91a11fb379f4`.  Its exact allowlist is this
   document alone.  It is anchored at
   `refs/codex-authority/uprime-upper-portability-guard-correction-20260723`;
   at most one replacement authority may use the same ref with suffix `-a2`.
   A_GC does not run GitHub Actions.
2. **H_GC (guard correction).** A direct child of the selected A_GC commit.
   Its primary branch is
   `codex/uprime-upper-portability-guard-correction`; at most one replacement
   attempt may use suffix `-a2`.  Its exact allowlist is:

   - `tests/uprime_u24_guard.py`
   - `tests/test_uprime_u24_upper_stack_portability_identity.py`

H_GC adds no test function and no tier-manifest row.  After a natural green
candidate run, `codex/uprime-upper-portability-plan` may fast-forward to the
byte-identical selected H_GC commit and must receive a distinct natural green
accepted-ref run.  G1 (primary or `-a2`) must then be a direct child of that
accepted H_GC commit.  The old H commit remains immutable.

The identity first-parent order is exactly:

`H -> A_GC -> H_GC -> G1 -> G2 -> G3 -> G4 -> A_RES -> R`.

`STAGE_ALLOWLISTS[A_GC]` is the singleton containing this document and
`STAGE_ALLOWLISTS[H_GC]` is the two guard/test paths above.  Both stages have an
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

Final closeout provenance must add the selected A_GC commit, tree, ref,
document blob, and document raw SHA-256.  Its stage-prefix product must include
`H,H_GC,G1,G2,G3,G4`, yielding exactly 66 stage keys.  A_RES and R may not omit
or reconstruct this inserted history.

## 3. Licensed structural recognition

The guard may recognize an integrity operation only from its complete AST
shape.  Names of variables, fields, helper functions, classes, or digests have
no authority.

### 3.1 Complete canonical wire

A canonical-wire expression is exactly
`lean_rgc.odlrq.contracts.canonical_contract_bytes(X)` with one positional
argument and no keywords.  The guard treats this as a taint-preserving byte
transport, never as evidence that `X` is semantically complete.

Registered complete origins are the five finite-E2 aggregate types, the
G2–G4 aggregate types frozen by the 2026-07-18 authority, the closed substrate
types produced by the exact carrier chain below, and the frozen carrier
`environment_digest_material` literal mapping with exactly these four fields:

`schema_version`, `matrix_id`, `family_id`, `side`.

The carrier field-set tests remain exact: omitting or adding a field cannot pass
the registered carrier contract.  Completeness is proved by those frozen
field-set and roundtrip tests, not by a trusted AST name.

G2 candidate labels are legal only as fields of the complete
support-reference, problem, and result wires whose exact ordered fields are
already frozen by the 2026-07-18 authority.  A candidate-label-only wire or
hash may be constructed, but it is not an integrity, equality, control, or
verification operand.  The carrier mapping above is the sole raw four-field
mapping exception; the full `SyntheticAction`, `SyntheticTotalizedState`,
`SyntheticTransitionRow`, admitted snapshot, verified partition, and quotient
generator contracts provide the complete typed carrier chain.

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
call shapes, the call is an identity/data operation.  Returns remain tainted.
No unlisted position, extra keyword, positional/keyword substitution, splat,
or unknown callee is admitted.

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

An exact one-argument `tuple(X)` is allowed only when `X` itself has a
registered typed aggregate/carrier origin and the tuple is an
order-preserving direct argument to a registered constructor or transport; it
does not legalize a fresh generic container or bare-label collection.  An
`append(X)` call is allowed
only on a structurally fresh function-local literal container.  A registered
whole type may be checked only by the exact dominating straight-line form
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

- the comparison is the whole `if` test;
- the body is exactly one unconditional
  `lean_rgc.odlrq.contracts.StrictContractError(<untainted string literal>)`
  raise;
- there is no `else`, no exception handler that can swallow the raise, and no
  chained, boolean, negated, membership, order, or equality form.

Operand order may be reversed.  The result may not be returned, stored,
asserted, used for lookup, loop control, call-target selection, argument
selection, or any other semantic branch.  `==` is not licensed.

## 4. Mandatory positive and adversarial probes

The existing fourth identity test, and no new fifth test, must demonstrate:

- complete carrier and candidate wires may undergo canonical-bytes and exact
  SHA-256 inequality checks whose only consequence is an uncaught strict
  contract error;
- reversed operands and an exact one-return hash helper are accepted;
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
- in the exact evaluator loop, the ordered family label and literal
  `row["family_id"]` are tainted while the row's numeric fields remain generic;
- unknown calls, generic label tuples, `.lower()`, and every arity, keyword,
  or tainted-position near miss of a registered sink are rejected.

The uncommitted G1 draft examined while diagnosing this guard mismatch is
pre-source engineering information only.  No G1 commit, push, CI run, protected
endpoint, or scientific result was consumed; the draft confers no attempt or
result status.

## 5. Stopping rule

H_GC stops at the first candidate whose exact two-path diff passes the four
identity tests, relevant guard tests, and the exact natural CI shape.  One
`-a2` source attempt is the maximum and may repair an implementation defect
only.  It may not widen the authority, matrix, complete-wire registry, sink
map, or semantic endpoint.  Failure after that attempt closes this authority;
it does not license source changes, endpoint reads, GPU/SSH/LLM work, or a
broader declassification rule.
